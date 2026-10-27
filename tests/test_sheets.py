import json

import httpx
import pytest
import respx

from app import sheets
from app.schema import Registro

URL = "https://script.google.com/macros/s/PRUEBA/exec"


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("SHEETS_WEBAPP_URL", URL)
    monkeypatch.setenv("SHEETS_SECRET", "secreto-de-prueba")


@respx.mock
def test_agregar_registro_manda_secreto_y_datos():
    ruta = respx.post(URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    registro = Registro(
        id_mensaje="wamid.1", telefono_gestor="51999", cantidad_kg=20, precio_kg=8
    )

    sheets.agregar_registro(registro)

    cuerpo = json.loads(ruta.calls[0].request.content)
    assert cuerpo["secret"] == "secreto-de-prueba"
    assert cuerpo["accion"] == "append"
    assert cuerpo["registro"]["id_mensaje"] == "wamid.1"
    assert cuerpo["registro"]["total"] == 160.0
    assert cuerpo["registro"]["estado"] == "pendiente"


@respx.mock
def test_actualizar_estado():
    ruta = respx.post(URL).mock(return_value=httpx.Response(200, json={"ok": True}))

    sheets.actualizar_estado("wamid.1", "confirmado")

    cuerpo = json.loads(ruta.calls[0].request.content)
    assert cuerpo["accion"] == "update_estado"
    assert cuerpo["id_mensaje"] == "wamid.1"
    assert cuerpo["estado"] == "confirmado"


@respx.mock
def test_resumen_mes():
    ruta = respx.post(URL).mock(
        return_value=httpx.Response(
            200, json={"ok": True, "mes": "2026-10", "kg": 45.5, "soles": 364.0, "registros": 3}
        )
    )

    r = sheets.resumen_mes("51999")

    assert json.loads(ruta.calls[0].request.content)["telefono"] == "51999"
    assert r["kg"] == 45.5
    assert r["soles"] == 364.0
    assert r["registros"] == 3


@respx.mock
def test_sigue_el_redirect_de_apps_script():
    respx.post(URL).mock(
        return_value=httpx.Response(302, headers={"location": "https://eco.test/resultado"})
    )
    respx.get("https://eco.test/resultado").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    sheets.actualizar_estado("wamid.1", "revisar")


@respx.mock
def test_error_de_sheets_se_convierte_en_error_claro():
    respx.post(URL).mock(
        return_value=httpx.Response(200, json={"ok": False, "error": "No autorizado"})
    )
    with pytest.raises(sheets.ErrorSheets, match="No autorizado"):
        sheets.actualizar_estado("wamid.1", "confirmado")


@respx.mock
def test_error_http_se_convierte_en_error_claro():
    respx.post(URL).mock(return_value=httpx.Response(500))
    with pytest.raises(sheets.ErrorSheets):
        sheets.resumen_mes("51999")


@respx.mock
def test_respuesta_que_no_es_json():
    respx.post(URL).mock(return_value=httpx.Response(200, text="<html>login</html>"))
    with pytest.raises(sheets.ErrorSheets):
        sheets.resumen_mes("51999")


@respx.mock
def test_falla_de_red():
    respx.post(URL).mock(side_effect=httpx.ConnectError("sin señal"))
    with pytest.raises(sheets.ErrorSheets, match="sin señal"):
        sheets.resumen_mes("51999")
