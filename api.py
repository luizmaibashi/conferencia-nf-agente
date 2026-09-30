"""API que o n8n chama: recebe o documento, confere contra o pedido e devolve a decisão.

Uso: uvicorn api:app --port 8000
"""
import csv
import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from conferencia_nf.modelos import Pedido
from conferencia_nf.roteador import processar

DADOS = Path(os.getenv("DADOS_DIR", "data"))
app = FastAPI(title="Conferência NF × Pedido")


def _pedidos() -> dict[str, Pedido]:
    bruto = json.loads((DADOS / "pedidos.json").read_text(encoding="utf-8"))
    return {k: Pedido(**v) for k, v in bruto.items()}


@app.get("/saude")
def saude():
    return {"ok": True}


@app.post("/conferir")
async def conferir(arquivo: UploadFile):
    conteudo = await arquivo.read()
    try:
        resultado, meta = processar(conteudo, _pedidos())
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))
    return {"arquivo": arquivo.filename, **resultado.model_dump(), "execucao": meta}


# "Planilha" do piloto: CSV que o n8n alimenta. Trocar por Google Sheets é trocar
# o nó de saída no n8n, sem mexer aqui.
REGISTROS = DADOS / "registros.csv"
COLUNAS = ["data_hora", "arquivo", "origem", "status", "fila", "valor_total",
           "diferenca_rs", "motivo"]


class Registro(BaseModel):
    arquivo: str
    origem: str
    status: str
    fila: str
    valor_total: float | None = None
    diferenca_rs: float = 0.0
    motivo: str = ""


@app.post("/registros")
def registrar(r: Registro):
    linha = {"data_hora": datetime.now().isoformat(timespec="seconds"), **r.model_dump()}
    novo = not REGISTROS.exists()
    with REGISTROS.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        if novo:
            w.writeheader()
        w.writerow(linha)
    return linha


@app.get("/registros")
def listar():
    if not REGISTROS.exists():
        return []
    with REGISTROS.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))
