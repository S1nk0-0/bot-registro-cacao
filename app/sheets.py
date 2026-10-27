import httpx

from app import config
from app.schema import Registro

TIMEOUT = 30.0


class ErrorSheets(Exception):
    """Falló la comunicación con el Apps Script."""


def _llamar(accion: str, **datos) -> dict:
    cuerpo = {"secret": config.sheets_secret(), "accion": accion, **datos}
    try:
        # Apps Script responde con un redirect, por eso follow_redirects.
        r = httpx.post(
            config.sheets_webapp_url(),
            json=cuerpo,
            timeout=TIMEOUT,
            follow_redirects=True,
        )
        r.raise_for_status()
        respuesta = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise ErrorSheets(f"No se pudo hablar con Google Sheets: {e}") from e

    if not respuesta.get("ok"):
        raise ErrorSheets(respuesta.get("error", "Error desconocido en Sheets"))
    return respuesta


def agregar_registro(registro: Registro) -> None:
    _llamar("append", registro=registro.model_dump())


def actualizar_estado(id_mensaje: str, estado: str) -> None:
    _llamar("update_estado", id_mensaje=id_mensaje, estado=estado)


def resumen_mes(telefono: str) -> dict:
    """Devuelve {"kg": ..., "soles": ..., "registros": ..., "mes": "YYYY-MM"}."""
    return _llamar("resumen", telefono=telefono)
