"""Campos del registro. Si la libreta cambia, se cambia solo este archivo."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Confianza = Literal["alta", "media", "baja"]
Estado = Literal["pendiente", "confirmado", "revisar"]


class CamposLibreta(BaseModel):
    """Lo que dice la hoja. También es el esquema que se le pide a Gemini."""

    codigo_registro: str | None = None
    fecha: str | None = Field(default=None, description="YYYY-MM-DD")
    codigo_productor: str | None = None
    producto: str | None = None
    cantidad_kg: float | None = Field(default=None, ge=0)
    precio_kg: float | None = Field(default=None, ge=0)
    total: float | None = Field(default=None, ge=0)
    comprador: str | None = None
    observaciones: str | None = None

    @field_validator(
        "codigo_registro", "codigo_productor", "producto", "comprador", "observaciones"
    )
    @classmethod
    def _texto_vacio_es_null(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("fecha")
    @classmethod
    def _fecha_valida(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        try:
            datetime.strptime(v.strip(), "%Y-%m-%d")
        except ValueError:
            raise ValueError("La fecha debe tener formato YYYY-MM-DD")
        return v.strip()


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Registro(CamposLibreta):
    """Campos de la libreta + columnas extra que agrega el bot."""

    id_mensaje: str = ""
    telefono_gestor: str = ""
    recibido_en: str = Field(default_factory=_ahora)
    estado: Estado = "pendiente"
    confianza: Confianza = "alta"

    @model_validator(mode="after")
    def _calcular_total(self):
        kg, precio = self.cantidad_kg, self.precio_kg
        if kg is None or precio is None:
            return self
        esperado = round(kg * precio, 2)
        if self.total is None:
            self.total = esperado
        elif abs(self.total - esperado) > 0.01:
            # No corregimos el total de la hoja: solo avisamos con confianza baja.
            self.confianza = "baja"
        return self
