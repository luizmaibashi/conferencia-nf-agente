"""Decide o caminho de cada documento: XML vai por regra, PDF e imagem vão ao LLM."""
from typing import Callable, Literal

from .conferencia import conferir
from .extrator_xml import extrair_xml
from .modelos import Pedido, Resultado

Tipo = Literal["xml", "pdf", "imagem"]

_MIME = {"pdf": "application/pdf"}


def tipo_documento(conteudo: bytes) -> Tipo:
    """Pelo conteúdo, não pela extensão: nome de arquivo mente."""
    inicio = conteudo[:16].lstrip()
    if inicio.startswith(b"<"):
        return "xml"
    if conteudo.startswith(b"%PDF"):
        return "pdf"
    if conteudo.startswith(b"\x89PNG") or conteudo.startswith(b"\xff\xd8"):
        return "imagem"
    raise ValueError("formato não suportado: envie XML de NF-e, PDF ou imagem do DANFE")


def mime_imagem(conteudo: bytes) -> str:
    return "image/png" if conteudo.startswith(b"\x89PNG") else "image/jpeg"


def processar(conteudo: bytes, pedidos: dict[str, Pedido],
              extrator_llm: Callable | None = None) -> tuple[Resultado, dict]:
    tipo = tipo_documento(conteudo)
    if tipo == "xml":
        return conferir(extrair_xml(conteudo), pedidos, origem="xml"), {"tipo": "xml"}

    if extrator_llm is None:
        from .extrator_llm import extrair_documento as extrator_llm
    mime = _MIME.get(tipo) or mime_imagem(conteudo)
    ext = extrator_llm(conteudo, mime)
    meta = {"tipo": tipo, "modelo": ext.modelo, "tokens_entrada": ext.tokens_entrada,
            "tokens_saida": ext.tokens_saida, "segundos": ext.segundos}
    return conferir(ext.nota, pedidos, origem="llm"), meta
