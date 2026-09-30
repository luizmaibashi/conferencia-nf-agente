import json
from pathlib import Path

import pytest

from conferencia_nf import cnpj
from conferencia_nf.conferencia import checar_leitura, conferir
from conferencia_nf.extrator_xml import extrair_xml
from conferencia_nf.gerar_dados import gerar
from conferencia_nf.modelos import NotaFiscal, Pedido
from conferencia_nf.roteador import processar, tipo_documento


@pytest.fixture(scope="module")
def dados(tmp_path_factory) -> Path:
    pasta = tmp_path_factory.mktemp("dados")
    gerar(n=27, saida=pasta, semente=7)
    return pasta


def _carregar(pasta: Path):
    pedidos = {k: Pedido(**v) for k, v in
               json.loads((pasta / "pedidos.json").read_text(encoding="utf-8")).items()}
    gabarito = json.loads((pasta / "gabarito.json").read_text(encoding="utf-8"))
    return pedidos, gabarito


def test_cnpj_gerado_valido_e_um_digito_trocado_invalida():
    c = cnpj.completar("112223330001")
    assert cnpj.valido(c)
    trocado = c[:5] + str((int(c[5]) + 1) % 10) + c[6:]
    assert not cnpj.valido(trocado)


def test_xml_ida_e_volta_preserva_a_nota(dados):
    _, gabarito = _carregar(dados)
    for doc_id, g in gabarito.items():
        lida = extrair_xml((dados / "xml" / f"{doc_id}.xml").read_bytes())
        assert lida == NotaFiscal(**g["nota"]), doc_id


def test_cada_cenario_chega_no_status_esperado_pelo_caminho_xml(dados):
    pedidos, gabarito = _carregar(dados)
    vistos = set()
    for doc_id, g in gabarito.items():
        resultado, meta = processar((dados / "xml" / f"{doc_id}.xml").read_bytes(), pedidos)
        assert meta["tipo"] == "xml"
        assert resultado.status == g["status_esperado"], (doc_id, g["cenario"], resultado)
        vistos.add(g["cenario"])
    assert len(vistos) == 6  # todos os cenários exercitados


def test_leitura_com_total_errado_vai_para_revisao(dados):
    pedidos, gabarito = _carregar(dados)
    nota = NotaFiscal(**next(g["nota"] for g in gabarito.values() if g["cenario"] == "ok"))
    nota.valor_total += 10
    assert checar_leitura(nota)
    assert conferir(nota, pedidos, origem="llm").status == "revisao_humana"


def test_fornecedor_diferente_do_pedido_vai_para_revisao(dados):
    pedidos, gabarito = _carregar(dados)
    nota = NotaFiscal(**next(g["nota"] for g in gabarito.values() if g["cenario"] == "ok"))
    nota.cnpj_emitente = cnpj.completar("999999990001")
    assert conferir(nota, pedidos, origem="llm").status == "revisao_humana"


def test_pdf_e_imagem_vao_para_o_llm_sem_chamar_api(dados):
    pedidos, gabarito = _carregar(dados)
    doc_id = sorted(gabarito)[0]

    class Falso:
        modelo, tokens_entrada, tokens_saida, segundos = "falso", 1, 1, 0.0
        nota = NotaFiscal(**gabarito[doc_id]["nota"])

    chamadas = []

    def extrator(conteudo, mime):
        chamadas.append(mime)
        return Falso()

    for pasta, ext in [("danfe", "pdf"), ("scan", "jpg")]:
        resultado, meta = processar((dados / pasta / f"{doc_id}.{ext}").read_bytes(),
                                    pedidos, extrator_llm=extrator)
        assert resultado.origem == "llm"
    assert chamadas == ["application/pdf", "image/jpeg"]


def test_tipo_desconhecido_falha_alto():
    with pytest.raises(ValueError):
        tipo_documento(b"GIF89a...")


def test_xml_com_entidade_externa_nao_e_resolvida(tmp_path):
    segredo = tmp_path / "segredo.txt"
    segredo.write_text("SEGREDO-DO-SERVIDOR")
    malicioso = f"""<?xml version="1.0"?>
<!DOCTYPE x [<!ENTITY xxe SYSTEM "{segredo.as_uri()}">]>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe>
<ide><nNF>&xxe;</nNF><dhEmi>2026-09-01T10:00:00-03:00</dhEmi></ide>
<emit><CNPJ>11222333000181</CNPJ><xNome>X</xNome></emit>
<total><ICMSTot><vNF>0.00</vNF></ICMSTot></total></infNFe></NFe></nfeProc>""".encode()
    nota = extrair_xml(malicioso)
    assert "SEGREDO" not in nota.numero
