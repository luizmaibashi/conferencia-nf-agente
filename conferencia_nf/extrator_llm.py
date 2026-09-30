"""Leitura de DANFE em PDF ou imagem com Gemini, saída estruturada no schema NotaFiscal.

Formato válido não significa conteúdo certo: quem decide se a leitura é confiável
é `conferencia.checar_leitura`, não o modelo.
"""
import os
import time
from dataclasses import dataclass

from google import genai
from google.genai import types

from .modelos import NotaFiscal

MODELO_PADRAO = "gemini-2.5-flash"

PROMPT = """Você recebe o DANFE (representação impressa de uma NF-e brasileira).
Transcreva os campos pedidos exatamente como estão impressos.

Regras:
- cnpj_emitente: só os 14 dígitos do CNPJ do emitente, sem pontos, barra ou traço.
- data_emissao: AAAA-MM-DD.
- Valores: número com ponto decimal e sem separador de milhar (impresso "1.234,50" vira 1234.5).
- pedido: o número do pedido de compra, se estiver impresso; se não estiver, null.
- Não calcule nem corrija nada. Se um valor impresso parecer errado, copie mesmo assim.
- Um item por linha da tabela de produtos, na ordem em que aparecem.
"""


@dataclass
class Extracao:
    nota: NotaFiscal
    modelo: str
    tokens_entrada: int
    tokens_saida: int  # inclui tokens de raciocínio, que o custo cobra e é fácil esquecer
    segundos: float


def extrair_documento(conteudo: bytes, mime: str, modelo: str | None = None,
                      cliente: genai.Client | None = None) -> Extracao:
    cliente = cliente or genai.Client()  # lê GEMINI_API_KEY do ambiente
    modelo = modelo or os.getenv("GEMINI_MODEL", MODELO_PADRAO)
    inicio = time.perf_counter()
    resposta = cliente.models.generate_content(
        model=modelo,
        contents=[types.Part.from_bytes(data=conteudo, mime_type=mime), PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=NotaFiscal,
            temperature=0,
        ),
    )
    segundos = time.perf_counter() - inicio
    nota = resposta.parsed
    if not isinstance(nota, NotaFiscal):
        nota = NotaFiscal.model_validate_json(resposta.text)
    uso = resposta.usage_metadata
    return Extracao(
        nota=nota,
        modelo=modelo,
        tokens_entrada=uso.prompt_token_count or 0,
        tokens_saida=(uso.candidates_token_count or 0) + (uso.thoughts_token_count or 0),
        segundos=round(segundos, 2),
    )
