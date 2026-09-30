"""Leitura da NF-e em XML: parser determinístico, custo zero, sem LLM."""
from lxml import etree

from .modelos import ItemNota, NotaFiscal

NS = {"n": "http://www.portalfiscal.inf.br/nfe"}

# XML vem de fora: não resolver entidades nem buscar nada na rede (evita XXE).
_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)


def extrair_xml(conteudo: bytes) -> NotaFiscal:
    raiz = etree.fromstring(conteudo, parser=_PARSER)
    inf = raiz.find(".//n:infNFe", NS)
    if inf is None:
        raise ValueError("XML sem infNFe: não parece uma NF-e")

    def txt(el, caminho):
        return el.findtext(caminho, namespaces=NS)

    itens, pedidos = [], set()
    for det in inf.findall("n:det", NS):
        prod = det.find("n:prod", NS)
        itens.append(ItemNota(
            codigo=txt(prod, "n:cProd"),
            descricao=txt(prod, "n:xProd"),
            quantidade=float(txt(prod, "n:qCom")),
            valor_unitario=float(txt(prod, "n:vUnCom")),
            valor_total=float(txt(prod, "n:vProd")),
        ))
        if xped := txt(prod, "n:xPed"):
            pedidos.add(xped)

    return NotaFiscal(
        numero=txt(inf, "n:ide/n:nNF"),
        cnpj_emitente=txt(inf, "n:emit/n:CNPJ"),
        razao_social_emitente=txt(inf, "n:emit/n:xNome"),
        data_emissao=txt(inf, "n:ide/n:dhEmi")[:10],
        # Nota com itens de mais de um pedido não tem pedido único: vai para revisão.
        pedido=pedidos.pop() if len(pedidos) == 1 else None,
        itens=itens,
        valor_total=float(txt(inf, "n:total/n:ICMSTot/n:vNF")),
    )
