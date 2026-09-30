"""Contratos de dados: o que é uma nota, um pedido e o resultado da conferência."""
from typing import Literal

from pydantic import BaseModel, Field


class ItemNota(BaseModel):
    codigo: str = Field(description="Código do produto no fornecedor (cProd)")
    descricao: str = Field(description="Descrição do produto como impressa")
    quantidade: float
    valor_unitario: float
    valor_total: float


class NotaFiscal(BaseModel):
    numero: str = Field(description="Número da nota (nNF), só dígitos")
    cnpj_emitente: str = Field(description="CNPJ do emitente, só os 14 dígitos")
    razao_social_emitente: str
    data_emissao: str = Field(description="Data de emissão no formato AAAA-MM-DD")
    pedido: str | None = Field(
        default=None, description="Número do pedido de compra (xPed), se impresso"
    )
    itens: list[ItemNota]
    valor_total: float = Field(description="Valor total da nota (vNF)")


class ItemPedido(BaseModel):
    codigo: str
    descricao: str
    quantidade: float
    valor_unitario: float


class Pedido(BaseModel):
    numero: str
    cnpj_fornecedor: str
    itens: list[ItemPedido]


class Divergencia(BaseModel):
    tipo: Literal["preco_acima", "quantidade_acima", "item_fora_do_pedido"]
    codigo: str
    detalhe: str
    diferenca_rs: float


Status = Literal["aprovada", "divergente", "revisao_humana"]


class Resultado(BaseModel):
    status: Status
    origem: Literal["xml", "llm"]
    divergencias: list[Divergencia] = []
    motivos_revisao: list[str] = []
    nota: NotaFiscal | None = None
