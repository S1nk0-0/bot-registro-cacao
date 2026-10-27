from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_verificacion_correcta(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secreto-de-prueba")
    r = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "secreto-de-prueba",
            "hub.challenge": "12345",
        },
    )
    assert r.status_code == 200
    assert r.text == "12345"


def test_verificacion_token_incorrecto(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secreto-de-prueba")
    r = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "otro",
            "hub.challenge": "12345",
        },
    )
    assert r.status_code == 403


def test_verificacion_sin_token_configurado(monkeypatch):
    # Si el servidor no tiene token, nunca se debe aceptar un token vacío.
    monkeypatch.delenv("WHATSAPP_VERIFY_TOKEN", raising=False)
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.challenge": "1"})
    assert r.status_code == 403
