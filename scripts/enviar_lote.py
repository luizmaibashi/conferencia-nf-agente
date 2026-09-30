"""Simula o fornecedor: manda um lote de notas para o webhook do n8n e resume as filas.

Mistura fixada antes de medir: nf_001 a nf_010; nf_003, nf_006 e nf_009 vão como
DANFE escaneado, o resto como XML (7 XML + 3 escaneados).

Uso: python scripts/enviar_lote.py --url http://localhost:5678/webhook/nota
"""
import argparse
import json
import sys
import time
import urllib.request
import uuid
from collections import Counter
from pathlib import Path

ESCANEADOS = {"nf_003", "nf_006", "nf_009"}


def enviar(url: str, nome: str, conteudo: bytes, mime: str) -> dict:
    fronteira = uuid.uuid4().hex
    corpo = (f"--{fronteira}\r\nContent-Disposition: form-data; name=\"arquivo\"; "
             f"filename=\"{nome}\"\r\nContent-Type: {mime}\r\n\r\n").encode() + conteudo + \
        f"\r\n--{fronteira}--\r\n".encode()
    req = urllib.request.Request(url, data=corpo, method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={fronteira}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:5678/webhook/nota")
    ap.add_argument("--dados", type=Path, default=Path("data"))
    a = ap.parse_args()

    gabarito = json.loads((a.dados / "gabarito.json").read_text(encoding="utf-8"))
    filas = Counter()
    for i in range(1, 11):
        doc = f"nf_{i:03d}"
        if doc in ESCANEADOS:
            nome, mime = f"{doc}.jpg", "image/jpeg"
            conteudo = (a.dados / "scan" / nome).read_bytes()
        else:
            nome, mime = f"{doc}.xml", "application/xml"
            conteudo = (a.dados / "xml" / nome).read_bytes()
        t0 = time.perf_counter()
        r = enviar(a.url, nome, conteudo, mime)
        filas[r["fila"]] += 1
        print(f"{nome:12} {r['origem']:4} {r['fila']:11} esperado={gabarito[doc]['status_esperado']:15} "
              f"{time.perf_counter() - t0:5.1f}s  {r['motivo'][:70]}")
    humano = filas["comprador"] + filas["revisor"]
    print(f"\nfilas: {dict(filas)}  →  chegaram a uma pessoa: {humano} de 10")


if __name__ == "__main__":
    main()
