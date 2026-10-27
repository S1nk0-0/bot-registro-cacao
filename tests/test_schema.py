import pytest
from pydantic import ValidationError

from app.schema import CamposLibreta, Registro


def test_todo_es_opcional():
    r = Registro()
    assert r.cantidad_kg is None
    assert r.estado == "pendiente"
    assert r.confianza == "alta"
    assert r.recibido_en


def test_registro_completo_cuadra():
    r = Registro(
        codigo_registro="CAC-001",
        fecha="2026-10-28",
        codigo_productor="P-014",
        producto="cacao",
        cantidad_kg=20,
        precio_kg=8.0,
        total=160.0,
        comprador="Cooperativa X",
    )
    assert r.total == 160.0
    assert r.confianza == "alta"


def test_total_se_calcula_si_falta():
    r = Registro(cantidad_kg=20, precio_kg=8.5)
    assert r.total == 170.0
    assert r.confianza == "alta"


def test_total_no_se_inventa_si_faltan_datos():
    assert Registro(cantidad_kg=20).total is None
    assert Registro(precio_kg=8).total is None


def test_total_que_no_cuadra_baja_confianza_y_no_se_corrige():
    r = Registro(cantidad_kg=20, precio_kg=8.0, total=150.0)
    assert r.total == 150.0
    assert r.confianza == "baja"


def test_total_con_diferencia_de_centavos_es_aceptable():
    r = Registro(cantidad_kg=3, precio_kg=3.333, total=10.0)
    assert r.confianza == "alta"


@pytest.mark.parametrize("campo", ["cantidad_kg", "precio_kg", "total"])
def test_numeros_negativos_se_rechazan(campo):
    with pytest.raises(ValidationError):
        Registro(**{campo: -1})


@pytest.mark.parametrize("fecha", ["28/10/2026", "2026-13-01", "ayer", "2026-10-32"])
def test_fecha_invalida_se_rechaza(fecha):
    with pytest.raises(ValidationError):
        Registro(fecha=fecha)


def test_fecha_valida_y_vacia():
    assert Registro(fecha="2026-10-28").fecha == "2026-10-28"
    assert Registro(fecha="").fecha is None


def test_texto_vacio_pasa_a_null():
    r = Registro(observaciones="   ", comprador="")
    assert r.observaciones is None
    assert r.comprador is None


def test_campos_libreta_no_incluye_metadatos():
    assert "estado" not in CamposLibreta.model_fields
    assert "telefono_gestor" not in CamposLibreta.model_fields
