"""Mede a leitura do Gemini campo a campo contra o gabarito, em DANFE limpo e escaneado.

Também mede o que importa para o negócio: das notas lidas com erro, quantas as
checagens automáticas (aritmética e CNPJ) mandaram para revisão humana?

Uso: python scripts/avaliar_extracao.py --dados data --n 15
"""
import argparse
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.genai.errors import ClientError  # noqa: E402

from conferencia_nf.conferencia import checar_leitura, conferir  # noqa: E402
from conferencia_nf.extrator_llm import extrair_documento  # noqa: E402
from conferencia_nf.modelos import NotaFiscal, Pedido  # noqa: E402

CAMPOS_NOTA = ["numero", "cnpj_emitente", "data_emissao", "pedido", "valor_total"]
CAMPOS_ITEM = ["codigo", "descricao", "quantidade", "valor_unitario", "valor_total"]


def wilson(acertos: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = acertos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centro - margem, centro + margem)


def igual(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < 0.005
        except (TypeError, ValueError):
            return False
    norm = lambda s: " ".join(str(s).upper().split()) if s is not None else None
    return norm(a) == norm(b)


def comparar(verdade: NotaFiscal, lida: NotaFiscal) -> dict[str, list[bool]]:
    res = defaultdict(list)
    for c in CAMPOS_NOTA:
        a, b = getattr(verdade, c), getattr(lida, c)
        if c == "numero":  # o DANFE imprime com zeros à esquerda (000001000 = 1000)
            a, b = str(a).lstrip("0"), str(b or "").lstrip("0")
        res[c].append(igual(a, b))
    for i, it in enumerate(verdade.itens):
        outro = lida.itens[i] if i < len(lida.itens) else None
        for c in CAMPOS_ITEM:
            res[f"item.{c}"].append(outro is not None and igual(getattr(it, c), getattr(outro, c)))
    return res


def extrair_com_retentativa(conteudo, mime, modelo):
    for tentativa in range(3):
        try:
            return extrair_documento(conteudo, mime, modelo=modelo)
        except ClientError as erro:
            if erro.code == 429 and "PerDay" in str(erro):
                raise CotaDiaria(str(erro)) from erro
            if tentativa == 2:
                raise
            print(f"  {erro.code}; tentando de novo em 35 s", file=sys.stderr)
            time.sleep(35)


class CotaDiaria(Exception):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", type=Path, default=Path("data"))
    ap.add_argument("--n", type=int, default=15, help="documentos por condição")
    ap.add_argument("--modelo", default=None, help="padrão: GEMINI_MODEL ou gemini-2.5-flash")
    a = ap.parse_args()

    gabarito = json.loads((a.dados / "gabarito.json").read_text(encoding="utf-8"))
    pedidos = {k: Pedido(**v) for k, v in
               json.loads((a.dados / "pedidos.json").read_text(encoding="utf-8")).items()}
    ids = sorted(gabarito)[: a.n]
    condicoes = {"limpo": ("danfe", "pdf", "application/pdf"),
                 "escaneado": ("scan", "jpg", "image/jpeg")}
    relatorio = {}
    interrompido = None
    for nome, (pasta, ext, mime) in condicoes.items():
        por_campo = defaultdict(list)
        notas_com_erro = pegas = 0
        tokens_in = tokens_out = 0
        segundos, erros = [], []
        decisoes = {"mesma": 0, "conservadora": 0, "perigosa": 0}
        modelo_usado = None
        for doc_id in ids:
            verdade = NotaFiscal(**gabarito[doc_id]["nota"])
            conteudo = (a.dados / pasta / f"{doc_id}.{ext}").read_bytes()
            try:
                ext_ = extrair_com_retentativa(conteudo, mime, a.modelo)
            except CotaDiaria as erro:
                interrompido = f"cota diária esgotada em {nome}/{doc_id}"
                print(interrompido, file=sys.stderr)
                break
            modelo_usado = ext_.modelo
            tokens_in += ext_.tokens_entrada
            tokens_out += ext_.tokens_saida
            segundos.append(ext_.segundos)
            cmp_ = comparar(verdade, ext_.nota)
            for campo, oks in cmp_.items():
                por_campo[campo].extend(oks)
            # O que importa para o negócio: a decisão com a leitura do LLM é a mesma
            # que com a nota verdadeira? Se não, errou para o lado seguro ou perigoso?
            status_llm = conferir(ext_.nota, pedidos, origem="llm").status
            status_ok = gabarito[doc_id]["status_esperado"]
            if status_llm == status_ok:
                decisoes["mesma"] += 1
            elif status_llm == "aprovada":
                decisoes["perigosa"] += 1
            else:
                decisoes["conservadora"] += 1
            errados = [c for c, oks in cmp_.items() if not all(oks)]
            if errados:
                notas_com_erro += 1
                pego = bool(checar_leitura(ext_.nota))
                pegas += pego
                erros.append({"doc": doc_id, "campos": errados, "pego_pela_checagem": pego,
                              "verdade": verdade.model_dump(), "lida": ext_.nota.model_dump()})
            print(f"{nome} {doc_id}: {'ok' if not errados else 'ERRO ' + ','.join(errados)}")

        todos = [ok for oks in por_campo.values() for ok in oks]
        relatorio[nome] = {
            "modelo": modelo_usado,
            "documentos": len(segundos),
            "campos": {"acertos": sum(todos), "n": len(todos),
                       "ic95": [round(x, 3) for x in wilson(sum(todos), len(todos))]},
            "por_campo": {c: {"acertos": sum(v), "n": len(v)} for c, v in por_campo.items()},
            "decisao_vs_gabarito": decisoes,
            "notas_com_algum_erro": notas_com_erro,
            "erros_pegos_pelas_checagens": pegas,
            "tokens_entrada": tokens_in, "tokens_saida": tokens_out,
            "segundos_mediana": sorted(segundos)[len(segundos) // 2] if segundos else None,
            "erros": erros,
        }
        if interrompido:
            break
    relatorio["interrompido"] = interrompido

    saida = Path("reports")
    saida.mkdir(exist_ok=True)
    (saida / "avaliacao_extracao.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(relatorio, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
