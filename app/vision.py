from google import genai
from google.genai import types
from pydantic import ValidationError

from app import config
from app.schema import CamposLibreta, Registro

PROMPT = """Eres un asistente que lee una hoja de una libreta de ventas de cacao escrita a mano.
Mira la foto y extrae los datos de la venta.

Reglas:
- Responde SOLO con un JSON con los campos pedidos, sin texto adicional.
- Si un campo no está en la hoja o no se lee bien, pon null. NUNCA inventes ni adivines un valor.
- Si la hoja tiene más de una venta, usa solo la primera.
- fecha: formato YYYY-MM-DD. Si falta el año o el día, pon null.
- cantidad_kg, precio_kg y total: solo números con punto decimal, sin "S/" ni "kg".
- Copia los códigos (codigo_registro, codigo_productor) tal como están escritos.
- producto en minúsculas (por ejemplo "cacao").
- observaciones: solo lo que esté escrito en la hoja, si no hay nada pon null.
"""


class ErrorLectura(Exception):
    """No se pudo leer la hoja. El mensaje explica la causa."""


def _cliente() -> genai.Client:
    return genai.Client(api_key=config.gemini_api_key())


def leer_hoja(imagen_bytes: bytes, mime: str) -> Registro:
    """Manda la foto a Gemini y devuelve el registro leído (o ErrorLectura)."""
    try:
        respuesta = _cliente().models.generate_content(
            model=config.gemini_model(),
            contents=[types.Part.from_bytes(data=imagen_bytes, mime_type=mime), PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CamposLibreta,
                temperature=0,
            ),
        )
        texto = respuesta.text
    except Exception as e:
        raise ErrorLectura(f"Falló la llamada a Gemini: {e}") from e

    if not texto:
        raise ErrorLectura("Gemini no devolvió texto")

    try:
        campos = CamposLibreta.model_validate_json(texto)
    except ValidationError as e:
        raise ErrorLectura(f"Gemini devolvió un JSON inválido: {e}") from e

    # Pasar por Registro calcula el total si falta y marca la confianza.
    return Registro(**campos.model_dump())
