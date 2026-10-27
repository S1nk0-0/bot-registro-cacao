import json

import httpx
import pytest
import respx

from app import whatsapp


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "token-de-prueba")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "PHONE123")
    monkeypatch.setenv("GRAPH_API_VERSION", "v99.0")


@respx.mock
def test_descargar_media_pide_url_y_luego_bytes():
    info = respx.get("https://graph.facebook.com/v99.0/MEDIA_1").mock(
        return_value=httpx.Response(200, json={"url": "https://cdn.test/foto"})
    )
    archivo = respx.get("https://cdn.test/foto").mock(
        return_value=httpx.Response(200, content=b"BYTES-DE-IMAGEN")
    )

    datos = whatsapp.descargar_media("MEDIA_1")

    assert datos == b"BYTES-DE-IMAGEN"
    assert info.calls[0].request.headers["authorization"] == "Bearer token-de-prueba"
    assert archivo.calls[0].request.headers["authorization"] == "Bearer token-de-prueba"


@respx.mock
def test_descargar_media_falla_si_graph_responde_error():
    respx.get("https://graph.facebook.com/v99.0/MEDIA_1").mock(
        return_value=httpx.Response(404, json={"error": {}})
    )
    with pytest.raises(httpx.HTTPStatusError):
        whatsapp.descargar_media("MEDIA_1")


@respx.mock
def test_enviar_texto():
    ruta = respx.post("https://graph.facebook.com/v99.0/PHONE123/messages").mock(
        return_value=httpx.Response(200, json={"messages": [{"id": "x"}]})
    )

    whatsapp.enviar_texto("51999888777", "Hola")

    req = ruta.calls[0].request
    assert req.headers["authorization"] == "Bearer token-de-prueba"
    assert json.loads(req.content) == {
        "messaging_product": "whatsapp",
        "to": "51999888777",
        "type": "text",
        "text": {"body": "Hola"},
    }


@respx.mock
def test_enviar_botones():
    ruta = respx.post("https://graph.facebook.com/v99.0/PHONE123/messages").mock(
        return_value=httpx.Response(200, json={})
    )

    whatsapp.enviar_botones(
        "51999888777", "¿Está bien?", [("si:abc", "Sí"), ("no:abc", "No")]
    )

    cuerpo = json.loads(ruta.calls[0].request.content)
    assert cuerpo["to"] == "51999888777"
    assert cuerpo["type"] == "interactive"
    assert cuerpo["interactive"]["type"] == "button"
    assert cuerpo["interactive"]["body"] == {"text": "¿Está bien?"}
    assert cuerpo["interactive"]["action"]["buttons"] == [
        {"type": "reply", "reply": {"id": "si:abc", "title": "Sí"}},
        {"type": "reply", "reply": {"id": "no:abc", "title": "No"}},
    ]


def test_enviar_botones_rechaza_mas_de_tres():
    botones = [(f"id{i}", f"B{i}") for i in range(4)]
    with pytest.raises(ValueError):
        whatsapp.enviar_botones("51999888777", "texto", botones)
