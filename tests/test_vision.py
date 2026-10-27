from pathlib import Path
from types import SimpleNamespace

import pytest

from app import vision

FIXTURES = Path(__file__).parent / "fixtures"


class ClienteFalso:
    """Imita client.models.generate_content sin tocar la red."""

    def __init__(self, texto=None, error=None):
        self.llamadas = []
        self._texto = texto
        self._error = error
        self.models = SimpleNamespace(generate_content=self._generar)

    def _generar(self, **kwargs):
        self.llamadas.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(text=self._texto)


@pytest.fixture
def usar_cliente(monkeypatch):
    def _usar(cliente):
        monkeypatch.setattr(vision, "_cliente", lambda: cliente)
        return cliente

    return _usar


def test_hoja_completa(usar_cliente):
    cliente = usar_cliente(ClienteFalso((FIXTURES / "gemini_ok.json").read_text()))

    r = vision.leer_hoja(b"imagen", "image/jpeg")

    assert r.codigo_registro == "CAC-001"
    assert r.cantidad_kg == 20
    assert r.total == 160.0
    assert r.confianza == "alta"
    assert r.estado == "pendiente"
    # Se pidió salida JSON con esquema y se mandó la imagen.
    config = cliente.llamadas[0]["config"]
    assert config.response_mime_type == "application/json"
    assert cliente.llamadas[0]["contents"][0].inline_data.data == b"imagen"


def test_campos_faltantes_quedan_null_y_total_se_calcula(usar_cliente):
    usar_cliente(ClienteFalso((FIXTURES / "gemini_incompleto.json").read_text()))

    r = vision.leer_hoja(b"imagen", "image/png")

    assert r.fecha is None
    assert r.comprador is None
    assert r.total == 100.0


def test_total_que_no_cuadra_baja_confianza(usar_cliente):
    usar_cliente(ClienteFalso('{"cantidad_kg": 10, "precio_kg": 8, "total": 90}'))
    assert vision.leer_hoja(b"x", "image/jpeg").confianza == "baja"


def test_json_roto(usar_cliente):
    usar_cliente(ClienteFalso("esto no es json {"))
    with pytest.raises(vision.ErrorLectura, match="JSON inválido"):
        vision.leer_hoja(b"x", "image/jpeg")


def test_json_con_valor_invalido(usar_cliente):
    usar_cliente(ClienteFalso('{"cantidad_kg": -5}'))
    with pytest.raises(vision.ErrorLectura, match="JSON inválido"):
        vision.leer_hoja(b"x", "image/jpeg")


def test_respuesta_vacia(usar_cliente):
    usar_cliente(ClienteFalso(None))
    with pytest.raises(vision.ErrorLectura, match="no devolvió texto"):
        vision.leer_hoja(b"x", "image/jpeg")


def test_error_de_la_api(usar_cliente):
    usar_cliente(ClienteFalso(error=RuntimeError("503 sin servicio")))
    with pytest.raises(vision.ErrorLectura, match="Falló la llamada a Gemini"):
        vision.leer_hoja(b"x", "image/jpeg")
