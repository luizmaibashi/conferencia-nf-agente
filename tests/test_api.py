import importlib

from fastapi.testclient import TestClient

from conferencia_nf.gerar_dados import gerar


def test_conferir_xml_e_registrar(tmp_path, monkeypatch):
    gerar(n=9, saida=tmp_path, semente=3)
    monkeypatch.setenv("DADOS_DIR", str(tmp_path))
    import api
    importlib.reload(api)
    cliente = TestClient(api.app)

    with (tmp_path / "xml" / "nf_001.xml").open("rb") as f:
        r = cliente.post("/conferir", files={"arquivo": ("nf_001.xml", f, "application/xml")})
    assert r.status_code == 200
    assert r.json()["origem"] == "xml"

    r = cliente.post("/conferir", files={"arquivo": ("x.gif", b"GIF89a", "image/gif")})
    assert r.status_code == 422

    reg = {"arquivo": "nf_001.xml", "origem": "xml", "status": "aprovada", "fila": "automatico"}
    assert cliente.post("/registros", json=reg).status_code == 200
    assert [x["arquivo"] for x in cliente.get("/registros").json()] == ["nf_001.xml"]
