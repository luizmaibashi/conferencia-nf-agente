"""API que o n8n chama: recebe o documento, confere contra o pedido e devolve a decisão.

Uso: uvicorn api:app --port 8000
"""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

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
