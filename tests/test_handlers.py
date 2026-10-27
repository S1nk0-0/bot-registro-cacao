import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app import handlers, main, vision

FIXTURES = Path(__file__).parent / "fixtures"
GRAPH = "https://graph.facebook.com/v99.0"
SHEETS_URL = "https://script.google.com/macros/s/PRUEBA/exec"
TEL = "51999888777"


class GeminiFalso:
    def __init__(self, texto=None, error=None):
        self._texto, self._error = texto, error
        self.models = SimpleNamespace(generate_content=self._generar)

    def _generar(self, **kwargs):
        if self._error:
            raise self._error
        return SimpleNamespace(text=self._texto)


class Mundo:
    """Registra lo que el bot manda a WhatsApp y a Sheets (todo mockeado)."""

    def __init__(self):
        self.mensajes = []  # cuerpos enviados a WhatsApp
        self.sheets = []  # cuerpos enviados al Apps Script
        self.resumen = {"ok": True, "mes": "2026-10", "kg": 45.5, "soles": 364.0, "registros": 3}
        self.sheets_ok = True

    def textos(self):
        return [m["text"]["body"] for m in self.mensajes if m["type"] == "text"]

    def botones(self):
        return [m for m in self.mensajes if m["type"] == "interactive"]

    def acciones(self):
        return [s["accion"] for s in self.sheets]


@pytest.fixture
def mundo(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "PHONE123")
    monkeypatch.setenv("GRAPH_API_VERSION", "v99.0")
    monkeypatch.setenv("SHEETS_WEBAPP_URL", SHEETS_URL)
    monkeypatch.setenv("SHEETS_SECRET", "secreto")
    monkeypatch.setattr(vision, "_cliente", lambda: GeminiFalso((FIXTURES / "gemini_ok.json").read_text()))
    main._ids_vistos.clear()

    m = Mundo()

    def graph_enviar(request):
        m.mensajes.append(json.loads(request.content))
        return httpx.Response(200, json={"messages": [{"id": "x"}]})

    def apps_script(request):
        cuerpo = json.loads(request.content)
        m.sheets.append(cuerpo)
        if not m.sheets_ok:
            return httpx.Response(200, json={"ok": False, "error": "falló"})
        if cuerpo["accion"] == "resumen":
            return httpx.Response(200, json=m.resumen)
        return httpx.Response(200, json={"ok": True})

    with respx.mock:
        respx.get(f"{GRAPH}/MEDIA_1").mock(
            return_value=httpx.Response(200, json={"url": "https://cdn.test/foto"})
        )
        respx.get("https://cdn.test/foto").mock(return_value=httpx.Response(200, content=b"IMG"))
        respx.post(f"{GRAPH}/PHONE123/messages").mock(side_effect=graph_enviar)
        respx.post(SHEETS_URL).mock(side_effect=apps_script)
        yield m


def test_foto_camino_feliz(mundo):
    handlers.manejar_foto(TEL, "wamid.F1", "MEDIA_1", "image/jpeg")

    assert mundo.textos() == [handlers.MSG_ACUSE]
    assert mundo.acciones() == ["append"]
    fila = mundo.sheets[0]["registro"]
    assert fila["id_mensaje"] == "wamid.F1"
    assert fila["telefono_gestor"] == TEL
    assert fila["estado"] == "pendiente"
    assert fila["cantidad_kg"] == 20

    boton = mundo.botones()[0]
    assert boton["to"] == TEL
    assert "20 kg" in boton["interactive"]["body"]["text"]
    assert "S/ 160.00" in boton["interactive"]["body"]["text"]
    ids = [b["reply"]["id"] for b in boton["interactive"]["action"]["buttons"]]
    assert ids == ["si:wamid.F1", "no:wamid.F1"]


def test_foto_con_total_que_no_cuadra_avisa(mundo, monkeypatch):
    monkeypatch.setattr(
        vision, "_cliente", lambda: GeminiFalso('{"cantidad_kg": 10, "precio_kg": 8, "total": 90}')
    )
    handlers.manejar_foto(TEL, "wamid.F2", "MEDIA_1", "image/jpeg")

    assert mundo.sheets[0]["registro"]["confianza"] == "baja"
    assert "no cuadra" in mundo.botones()[0]["interactive"]["body"]["text"]


def test_foto_si_gemini_falla(mundo, monkeypatch):
    monkeypatch.setattr(vision, "_cliente", lambda: GeminiFalso(error=RuntimeError("caído")))
    handlers.manejar_foto(TEL, "wamid.F3", "MEDIA_1", "image/jpeg")

    assert mundo.textos() == [handlers.MSG_ACUSE, handlers.MSG_NO_LEI]
    assert mundo.sheets == []
    assert mundo.botones() == []


def test_foto_si_json_de_gemini_esta_roto(mundo, monkeypatch):
    monkeypatch.setattr(vision, "_cliente", lambda: GeminiFalso("{roto"))
    handlers.manejar_foto(TEL, "wamid.F4", "MEDIA_1", "image/jpeg")

    assert mundo.textos()[-1] == handlers.MSG_NO_LEI
    assert mundo.sheets == []


def test_foto_si_no_se_pudo_descargar(mundo):
    respx.get(f"{GRAPH}/MEDIA_X").mock(return_value=httpx.Response(404, json={}))
    handlers.manejar_foto(TEL, "wamid.F5", "MEDIA_X", "image/jpeg")

    assert mundo.textos()[-1] == handlers.MSG_NO_LEI
    assert mundo.sheets == []


def test_foto_sin_ningun_dato_se_trata_como_no_leida(mundo, monkeypatch):
    monkeypatch.setattr(vision, "_cliente", lambda: GeminiFalso("{}"))
    handlers.manejar_foto(TEL, "wamid.F6", "MEDIA_1", "image/jpeg")

    assert mundo.textos()[-1] == handlers.MSG_NO_LEI
    assert mundo.sheets == []


def test_foto_si_sheets_falla_no_manda_botones(mundo):
    mundo.sheets_ok = False
    handlers.manejar_foto(TEL, "wamid.F7", "MEDIA_1", "image/jpeg")

    assert mundo.textos()[-1] == handlers.MSG_NO_GUARDE
    assert mundo.botones() == []


def test_boton_si_confirma(mundo):
    handlers.manejar_boton(TEL, "si:wamid.F1")

    assert mundo.sheets == [
        {"secret": "secreto", "accion": "update_estado", "id_mensaje": "wamid.F1", "estado": "confirmado"}
    ]
    assert mundo.textos() == ["¡Listo, quedó registrado!"]


def test_boton_no_pide_otra_foto(mundo):
    handlers.manejar_boton(TEL, "no:wamid.F1")

    assert mundo.sheets[0]["estado"] == "revisar"
    assert mundo.sheets[0]["id_mensaje"] == "wamid.F1"
    assert "otra vez" in mundo.textos()[0]
    assert "luz" in mundo.textos()[0]


def test_boton_desconocido_manda_ayuda(mundo):
    handlers.manejar_boton(TEL, "cualquier-cosa")

    assert mundo.sheets == []
    assert mundo.textos() == [handlers.MSG_AYUDA]


def test_boton_si_sheets_falla(mundo):
    mundo.sheets_ok = False
    handlers.manejar_boton(TEL, "si:wamid.F1")

    assert mundo.textos() == [handlers.MSG_NO_GUARDE]


def test_texto_resumen(mundo):
    handlers.manejar_texto(TEL, "  Resumen ")

    assert mundo.sheets[0]["accion"] == "resumen"
    assert mundo.sheets[0]["telefono"] == TEL
    texto = mundo.textos()[0]
    assert "octubre 2026" in texto
    assert "45.5 kg" in texto
    assert "S/ 364.00" in texto


def test_texto_resumen_sin_ventas(mundo):
    mundo.resumen = {"ok": True, "mes": "2026-10", "kg": 0, "soles": 0, "registros": 0}
    handlers.manejar_texto(TEL, "resumen")

    assert "todavía no tienes ventas" in mundo.textos()[0]


def test_texto_resumen_si_sheets_falla(mundo):
    mundo.sheets_ok = False
    handlers.manejar_texto(TEL, "resumen")

    assert "No pude calcular" in mundo.textos()[0]


def test_otro_texto_manda_ayuda(mundo):
    handlers.manejar_texto(TEL, "hola, buenas")

    assert mundo.sheets == []
    assert mundo.textos() == [handlers.MSG_AYUDA]


def test_punta_a_punta_desde_el_webhook(mundo):
    """POST /webhook con una foto -> acuse, Gemini, Sheets y botones."""
    payload = json.loads((FIXTURES / "webhook_imagen.json").read_text(encoding="utf-8"))
    payload["entry"][0]["changes"][0]["value"]["messages"][0]["image"]["id"] = "MEDIA_1"

    r = TestClient(main.app).post("/webhook", json=payload)

    assert r.status_code == 200
    assert mundo.acciones() == ["append"]
    assert mundo.sheets[0]["registro"]["id_mensaje"] == "wamid.IMAGEN001"
    assert len(mundo.botones()) == 1
