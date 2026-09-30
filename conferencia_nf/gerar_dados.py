"""Gera dados sintéticos: pedidos, NF-e em XML, DANFE em PDF e DANFE "escaneado".

Tudo é fictício (fornecedores, CNPJs, produtos). O XML segue a estrutura da NF-e 4.00
de forma simplificada, sem assinatura: serve para o pipeline, não para a SEFAZ.

Uso: python -m conferencia_nf.gerar_dados --n 30 --saida data
"""
import argparse
import io
import json
import random
from datetime import date, timedelta
from pathlib import Path

import fitz  # PyMuPDF
from lxml import etree
from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from . import cnpj
from .modelos import ItemNota, ItemPedido, NotaFiscal, Pedido

FORNECEDORES = [
    ("Embalagens Serra Azul Ltda", "112223330001"),
    ("Tampas e Vedações Rio Claro S.A.", "445556660001"),
    ("Rótulos Pampa Indústria Gráfica Ltda", "778889990001"),
    ("Açúcar Vale do Tietê Comércio Ltda", "221133440001"),
    ("Gases Industriais Litoral Ltda", "556677880001"),
]

# (código, descrição, preço unitário, fornecedor)
CATALOGO = [
    ("PET-2000", "GARRAFA PET 2L CRISTAL PREFORMA 48G", 0.62, 0),
    ("PET-600", "GARRAFA PET 600ML CRISTAL PREFORMA 21G", 0.31, 0),
    ("CX-12UN", "CAIXA PAPELAO ONDULADO 12 UNIDADES", 2.85, 0),
    ("FILM-STR", "FILME STRETCH 500MM X 25 MICRA BOBINA", 118.40, 0),
    ("TMP-28", "TAMPA PLASTICA ROSCA 28MM PCO1881 VERMELHA", 0.07, 1),
    ("TMP-38", "TAMPA PLASTICA 38MM COM LACRE AZUL", 0.11, 1),
    ("VED-EPDM", "ANEL DE VEDACAO EPDM 54MM", 1.94, 1),
    ("ROT-2L", "ROTULO BOPP 2L IMPRESSO 6 CORES", 0.09, 2),
    ("ROT-600", "ROTULO BOPP 600ML IMPRESSO 6 CORES", 0.05, 2),
    ("ETQ-PAL", "ETIQUETA PALETE TERMICA 100X150", 0.21, 2),
    ("ACU-50", "ACUCAR CRISTAL TIPO 1 SACO 50KG", 186.00, 3),
    ("ACU-BIG", "ACUCAR CRISTAL BIG BAG 1200KG", 4310.00, 3),
    ("CO2-25", "GAS CARBONICO ALIMENTICIO CILINDRO 25KG", 212.50, 4),
    ("N2-10", "NITROGENIO ALIMENTICIO CILINDRO 10M3", 164.90, 4),
]

# Cenário → status que a conferência deve devolver para o XML.
CENARIOS = {
    "ok": "aprovada",
    "dentro_tolerancia": "aprovada",
    "preco_acima": "divergente",
    "quantidade_acima": "divergente",
    "item_fora_do_pedido": "divergente",
    "sem_pedido": "revisao_humana",
}
_SEQUENCIA = ["ok"] * 4 + ["dentro_tolerancia", "preco_acima", "quantidade_acima",
                           "item_fora_do_pedido", "sem_pedido"]


def _fornecedores():
    return [(nome, cnpj.completar(base)) for nome, base in FORNECEDORES]


def gerar_caso(i: int, rng: random.Random) -> tuple[Pedido, NotaFiscal, str]:
    cenario = _SEQUENCIA[i % len(_SEQUENCIA)]
    f = rng.randrange(len(FORNECEDORES))
    nome, cnpj_f = _fornecedores()[f]
    produtos = [p for p in CATALOGO if p[3] == f]
    escolhidos = rng.sample(produtos, k=rng.randint(1, len(produtos)))

    num_pedido = f"PC-{2026}{i + 1:04d}"
    itens_pedido = []
    for cod, desc, preco, _ in escolhidos:
        qtd = rng.choice([10, 20, 50, 100, 500, 1000, 5000]) if preco < 5 else rng.randint(2, 40)
        itens_pedido.append(ItemPedido(codigo=cod, descricao=desc, quantidade=qtd, valor_unitario=preco))
    pedido = Pedido(numero=num_pedido, cnpj_fornecedor=cnpj_f, itens=itens_pedido)

    itens_nota = [dict(codigo=p.codigo, descricao=p.descricao, quantidade=p.quantidade,
                       valor_unitario=p.valor_unitario) for p in itens_pedido]
    alvo = rng.randrange(len(itens_nota))
    p, q = itens_nota[alvo]["valor_unitario"], itens_nota[alvo]["quantidade"]
    if cenario == "dentro_tolerancia":
        # 0,3% acima: abaixo da tolerância de 0,5% sobre o valor do item.
        itens_nota[alvo]["valor_unitario"] = round(p * 1.003, 4)
    elif cenario == "preco_acima":
        # 4% acima, e pelo menos R$ 1 a mais no item, para passar do piso de R$ 0,50.
        itens_nota[alvo]["valor_unitario"] = round(p + max(0.04 * p, 1.0 / q), 4)
    elif cenario == "quantidade_acima":
        itens_nota[alvo]["quantidade"] = itens_nota[alvo]["quantidade"] * 1.2
    elif cenario == "item_fora_do_pedido":
        fora = [p for p in CATALOGO if p[3] == f and p[0] not in {x["codigo"] for x in itens_nota}]
        cod, desc, preco, _ = rng.choice(fora or [p for p in CATALOGO if p[3] != f])
        itens_nota.append(dict(codigo=cod, descricao=desc, quantidade=rng.randint(2, 20),
                               valor_unitario=preco))

    itens = []
    for it in itens_nota:
        it["quantidade"] = round(it["quantidade"], 2)
        itens.append(ItemNota(**it, valor_total=round(it["quantidade"] * it["valor_unitario"], 2)))
    nota = NotaFiscal(
        numero=str(1000 + i * 7),
        cnpj_emitente=cnpj_f,
        razao_social_emitente=nome,
        data_emissao=(date(2026, 9, 1) + timedelta(days=i % 28)).isoformat(),
        pedido=None if cenario == "sem_pedido" else num_pedido,
        itens=itens,
        valor_total=round(sum(x.valor_total for x in itens), 2),
    )
    return pedido, nota, cenario


def _chave(nota: NotaFiscal) -> str:
    base = f"35{nota.data_emissao[2:4]}{nota.data_emissao[5:7]}{nota.cnpj_emitente}55001"
    return (base + nota.numero.zfill(9) + "1" + "0" * 44)[:44]


def para_xml(nota: NotaFiscal) -> bytes:
    ns = "http://www.portalfiscal.inf.br/nfe"
    E = lambda tag, texto=None, **attrs: _el(ns, tag, texto, **attrs)
    proc = E("nfeProc", versao="4.00")
    nfe = etree.SubElement(proc, f"{{{ns}}}NFe")
    inf = etree.SubElement(nfe, f"{{{ns}}}infNFe", Id=f"NFe{_chave(nota)}", versao="4.00")
    ide = etree.SubElement(inf, f"{{{ns}}}ide")
    ide.append(E("nNF", nota.numero))
    ide.append(E("dhEmi", f"{nota.data_emissao}T10:00:00-03:00"))
    emit = etree.SubElement(inf, f"{{{ns}}}emit")
    emit.append(E("CNPJ", nota.cnpj_emitente))
    emit.append(E("xNome", nota.razao_social_emitente))
    for n, it in enumerate(nota.itens, start=1):
        det = etree.SubElement(inf, f"{{{ns}}}det", nItem=str(n))
        prod = etree.SubElement(det, f"{{{ns}}}prod")
        for tag, val in [("cProd", it.codigo), ("xProd", it.descricao),
                         ("qCom", f"{it.quantidade:.4f}"), ("vUnCom", f"{it.valor_unitario:.4f}"),
                         ("vProd", f"{it.valor_total:.2f}")]:
            prod.append(E(tag, val))
        if nota.pedido:
            prod.append(E("xPed", nota.pedido))
    total = etree.SubElement(etree.SubElement(inf, f"{{{ns}}}total"), f"{{{ns}}}ICMSTot")
    total.append(E("vNF", f"{nota.valor_total:.2f}"))
    return etree.tostring(proc, xml_declaration=True, encoding="UTF-8", pretty_print=True)


def _el(ns, tag, texto=None, **attrs):
    el = etree.Element(f"{{{ns}}}{tag}", **attrs)
    if texto is not None:
        el.text = texto
    return el


def _brl(v: float, casas: int = 2) -> str:
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def para_danfe(nota: NotaFiscal) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    x0, y = 12 * mm, h - 15 * mm
    c.setLineWidth(0.6)
    c.rect(x0, y - 28 * mm, w - 24 * mm, 28 * mm)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0 + 3 * mm, y - 7 * mm, nota.razao_social_emitente.upper())
    c.setFont("Helvetica", 8)
    c.drawString(x0 + 3 * mm, y - 12 * mm, f"CNPJ: {cnpj.formatar(nota.cnpj_emitente)}")
    c.drawString(x0 + 3 * mm, y - 16 * mm, "Rod. Fictícia, km 12 - Distrito Industrial")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(w / 2 + 10 * mm, y - 8 * mm, "DANFE")
    c.setFont("Helvetica", 7)
    c.drawString(w / 2 + 10 * mm, y - 12 * mm, "Documento Auxiliar da Nota Fiscal Eletrônica")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(w / 2 + 10 * mm, y - 18 * mm, f"Nº {nota.numero.zfill(9)}   SÉRIE 001")
    c.setFont("Helvetica", 7)
    c.drawString(w / 2 + 10 * mm, y - 23 * mm, "CHAVE DE ACESSO")
    c.setFont("Courier", 7)
    chave = _chave(nota)
    c.drawString(w / 2 + 10 * mm, y - 26.5 * mm, " ".join(chave[i:i + 4] for i in range(0, 44, 4)))

    y -= 36 * mm
    c.setFont("Helvetica", 8)
    emissao = date.fromisoformat(nota.data_emissao).strftime("%d/%m/%Y")
    c.drawString(x0, y, f"DATA DE EMISSÃO: {emissao}")
    c.drawString(x0 + 70 * mm, y, "DESTINATÁRIO: DISTRIBUIDORA DE BEBIDAS EXEMPLO LTDA")

    # Quadro de impostos: números que parecem totais e não são (distratores reais do DANFE).
    y -= 8 * mm
    base_icms = nota.valor_total
    quadro = [("BASE DE CÁLC. DO ICMS", base_icms), ("VALOR DO ICMS", base_icms * 0.18),
              ("VALOR DO FRETE", 0.0), ("VALOR TOTAL DOS PRODUTOS", nota.valor_total)]
    largura = (w - 24 * mm) / len(quadro)
    for k, (rot, val) in enumerate(quadro):
        cx = x0 + k * largura
        c.rect(cx, y - 9 * mm, largura, 9 * mm)
        c.setFont("Helvetica", 6)
        c.drawString(cx + 1.5 * mm, y - 3 * mm, rot)
        c.setFont("Helvetica", 8)
        c.drawRightString(cx + largura - 1.5 * mm, y - 7.5 * mm, _brl(val))

    y -= 16 * mm
    # (posição, rótulo, alinhamento): colunas numéricas alinham à direita, como no DANFE.
    cols = [(0, "CÓDIGO", "e"), (22, "DESCRIÇÃO DO PRODUTO", "e"), (92, "NCM", "e"),
            (108, "CFOP", "e"), (140, "QTD", "d"), (162, "V. UNIT.", "d"), (186, "V. TOTAL", "d")]
    c.setFont("Helvetica-Bold", 7)
    for pos, rot, al in cols:
        (c.drawString if al == "e" else c.drawRightString)(x0 + pos * mm, y, rot)
    c.line(x0, y - 1.5 * mm, w - 12 * mm, y - 1.5 * mm)
    c.setFont("Helvetica", 6.5)
    for it in nota.itens:
        y -= 5 * mm
        ncm = str(39233000 + sum(map(ord, it.codigo)) % 900)
        # Descrição inteira: truncar faria o gabarito divergir do que está impresso.
        valores = [it.codigo, it.descricao, ncm, "5101", _brl(it.quantidade, 2),
                   _brl(it.valor_unitario, 4), _brl(it.valor_total)]
        for (pos, _, al), val in zip(cols, valores):
            (c.drawString if al == "e" else c.drawRightString)(x0 + pos * mm, y, val)

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - 12 * mm, y, f"VALOR TOTAL DA NOTA: R$ {_brl(nota.valor_total)}")

    y -= 14 * mm
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x0, y, "DADOS ADICIONAIS")
    c.setFont("Helvetica", 7)
    extra = f"Pedido de compra: {nota.pedido}. " if nota.pedido else ""
    c.drawString(x0, y - 4 * mm, extra + "Documento fictício gerado para teste. Sem valor fiscal.")
    c.showPage()
    c.save()
    return buf.getvalue()


def escanear(pdf: bytes, rng: random.Random) -> bytes:
    """Simula cópia escaneada: resolução baixa, inclinação, desfoque, ruído e JPEG ruim."""
    pagina = fitz.open(stream=pdf, filetype="pdf")[0]
    pix = pagina.get_pixmap(dpi=90)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    img = img.rotate(rng.uniform(-3, 3), expand=True, fillcolor=235)
    img = img.filter(ImageFilter.GaussianBlur(0.9))
    ruido = Image.effect_noise(img.size, 22)
    img = Image.blend(img, ruido, 0.15)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=30)
    return out.getvalue()


def gerar(n: int, saida: Path, semente: int = 42) -> None:
    rng = random.Random(semente)
    for sub in ("xml", "danfe", "scan"):
        (saida / sub).mkdir(parents=True, exist_ok=True)
    pedidos, gabarito = {}, {}
    for i in range(n):
        pedido, nota, cenario = gerar_caso(i, rng)
        doc_id = f"nf_{i + 1:03d}"
        pedidos[pedido.numero] = pedido.model_dump()
        gabarito[doc_id] = {"cenario": cenario, "status_esperado": CENARIOS[cenario],
                            "nota": nota.model_dump()}
        (saida / "xml" / f"{doc_id}.xml").write_bytes(para_xml(nota))
        pdf = para_danfe(nota)
        (saida / "danfe" / f"{doc_id}.pdf").write_bytes(pdf)
        (saida / "scan" / f"{doc_id}.jpg").write_bytes(escanear(pdf, rng))
    (saida / "pedidos.json").write_text(json.dumps(pedidos, ensure_ascii=False, indent=1), encoding="utf-8")
    (saida / "gabarito.json").write_text(json.dumps(gabarito, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--saida", type=Path, default=Path("data"))
    ap.add_argument("--semente", type=int, default=42)
    a = ap.parse_args()
    gerar(a.n, a.saida, a.semente)
    print(f"{a.n} casos gerados em {a.saida}/")
