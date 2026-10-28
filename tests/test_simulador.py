"""Prueba del simulador en modo demo (sin red, sin Gemini ni Sheets)."""
import time
from pathlib import Path

from fastapi.testclient import TestClient

import simulador
from app import whatsapp

HOJA = Path(__file__).parent / "fixtures" / "hoja_ejemplo.png"


def _esperar(cliente, condicion, segundos=10):
    fin = time.time() + segundos
    while time.time() < fin:
        mensajes = cliente.get("/mensajes").json()
        if condicion(mensajes):
            return mensajes
        time.sleep(0.1)
    raise AssertionError(f"No llegó lo esperado. Mensajes: {cliente.get('/mensajes').json()}")


def test_flujo_completo_en_modo_demo(monkeypatch):
    monkeypatch.setenv("SIMULADOR_DEMO", "1")
    original = whatsapp.enviar_texto
    with TestClient(simulador.app) as cliente:
        assert "Modo demo" in cliente.get("/").text

        cliente.post("/foto", files={"archivo": ("hoja.png", HOJA.read_bytes(), "image/png")})
        mensajes = _esperar(cliente, lambda ms: any(m["botones"] for m in ms))
        assert mensajes[0]["texto"] == "Recibí tu foto, la estoy leyendo..."
        resumen = next(m for m in mensajes if m["botones"])
        assert "CAC-001" in resumen["texto"]
        assert [b["titulo"] for b in resumen["botones"]] == ["Sí", "No"]

        cliente.post("/boton", json={"id": resumen["botones"][0]["id"]})
        _esperar(cliente, lambda ms: any("quedó registrado" in m["texto"] for m in ms))

        cliente.post("/texto", json={"texto": "resumen"})
        mensajes = _esperar(cliente, lambda ms: any("Ventas confirmadas: 1" in m["texto"] for m in ms))
        assert "160.00" in mensajes[-1]["texto"]

    # Al cerrar, el simulador deja whatsapp como estaba.
    assert whatsapp.enviar_texto is original


def test_texto_desconocido_da_ayuda(monkeypatch):
    monkeypatch.setenv("SIMULADOR_DEMO", "1")
    with TestClient(simulador.app) as cliente:
        cliente.post("/texto", json={"texto": "hola"})
        mensajes = _esperar(cliente, lambda ms: len(ms) >= 1)
        assert "Mándame una foto" in mensajes[0]["texto"]
