import httpx

from app import config

TIMEOUT = 30.0


def _base() -> str:
    return f"https://graph.facebook.com/{config.graph_api_version()}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.whatsapp_token()}"}


def descargar_media(media_id: str) -> bytes:
    """Baja una imagen de WhatsApp: primero pide la URL y luego los bytes."""
    with httpx.Client(timeout=TIMEOUT) as cliente:
        r = cliente.get(f"{_base()}/{media_id}", headers=_headers())
        r.raise_for_status()
        url = r.json()["url"]
        # La URL de descarga también exige el token.
        r = cliente.get(url, headers=_headers())
        r.raise_for_status()
        return r.content


def _enviar(cuerpo: dict) -> None:
    url = f"{_base()}/{config.whatsapp_phone_number_id()}/messages"
    r = httpx.post(url, headers=_headers(), json=cuerpo, timeout=TIMEOUT)
    r.raise_for_status()


def enviar_texto(to: str, texto: str) -> None:
    _enviar(
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": texto},
        }
    )


def enviar_botones(to: str, texto: str, botones: list[tuple[str, str]]) -> None:
    """botones: lista de (id, título). WhatsApp permite hasta 3, título de máx. 20 letras."""
    if not 1 <= len(botones) <= 3:
        raise ValueError("WhatsApp permite de 1 a 3 botones")
    _enviar(
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": texto},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": id_, "title": titulo[:20]}}
                        for id_, titulo in botones
                    ]
                },
            },
        }
    )
