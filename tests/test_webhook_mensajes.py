import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import handlers, main

FIXTURES = Path(__file__).parent / "fixtures"
client = TestClient(main.app)


def cargar(nombre: str) -> dict:
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    main._ids_vistos.clear()
    llamadas = []
    monkeypatch.setattr(handlers, "manejar_foto", lambda *a: llamadas.append(("foto", *a)))
    monkeypatch.setattr(handlers, "manejar_boton", lambda *a: llamadas.append(("boton", *a)))
    monkeypatch.setattr(handlers, "manejar_texto", lambda *a: llamadas.append(("texto", *a)))
    return llamadas


def test_imagen_va_a_manejar_foto(limpio):
    r = client.post("/webhook", json=cargar("webhook_imagen.json"))
    assert r.status_code == 200
    assert limpio == [("foto", "51999888777", "wamid.IMAGEN001", "MEDIA_001", "image/jpeg")]


def test_boton_va_a_manejar_boton(limpio):
    r = client.post("/webhook", json=cargar("webhook_boton.json"))
    assert r.status_code == 200
    assert limpio == [("boton", "51999888777", "si:wamid.IMAGEN001")]


def test_texto_va_a_manejar_texto(limpio):
    r = client.post("/webhook", json=cargar("webhook_texto.json"))
    assert r.status_code == 200
    assert limpio == [("texto", "51999888777", "resumen")]


def test_status_se_ignora(limpio):
    r = client.post("/webhook", json=cargar("webhook_status.json"))
    assert r.status_code == 200
    assert limpio == []


def test_id_repetido_se_ignora(limpio):
    payload = cargar("webhook_imagen.json")
    client.post("/webhook", json=payload)
    r = client.post("/webhook", json=payload)
    assert r.status_code == 200
    assert len(limpio) == 1


def test_cuerpo_invalido_devuelve_200(limpio):
    r = client.post("/webhook", content=b"no es json")
    assert r.status_code == 200
    assert limpio == []


def test_tipo_no_soportado_se_ignora(limpio):
    payload = cargar("webhook_texto.json")
    mensaje = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    mensaje["type"] = "audio"
    r = client.post("/webhook", json=payload)
    assert r.status_code == 200
    assert limpio == []
