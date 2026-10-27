from collections import OrderedDict

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app import config, handlers

app = FastAPI(title="Bot de registro de ventas")

# Meta reintenta los webhooks: recordamos los últimos ids para no repetir.
_MAX_IDS = 1000
_ids_vistos: OrderedDict[str, None] = OrderedDict()


def _es_repetido(id_mensaje: str) -> bool:
    if id_mensaje in _ids_vistos:
        return True
    _ids_vistos[id_mensaje] = None
    if len(_ids_vistos) > _MAX_IDS:
        _ids_vistos.popitem(last=False)
    return False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/webhook", response_class=PlainTextResponse)
def verificar_webhook(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
):
    # Meta llama a este endpoint una vez, al configurar el webhook.
    esperado = config.whatsapp_verify_token()
    if mode == "subscribe" and esperado and token == esperado:
        return challenge
    raise HTTPException(status_code=403, detail="Token inválido")


def _mensajes(payload: dict):
    """Recorre el payload de Meta y devuelve solo los mensajes (no los statuses)."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for mensaje in change.get("value", {}).get("messages", []):
                yield mensaje


def _despachar(mensaje: dict, tareas: BackgroundTasks) -> None:
    id_mensaje = mensaje.get("id", "")
    telefono = mensaje.get("from", "")
    tipo = mensaje.get("type")
    if not id_mensaje or not telefono or _es_repetido(id_mensaje):
        return

    if tipo == "image":
        imagen = mensaje.get("image", {})
        tareas.add_task(
            handlers.manejar_foto,
            telefono,
            id_mensaje,
            imagen.get("id", ""),
            imagen.get("mime_type", "image/jpeg"),
        )
    elif tipo == "interactive":
        respuesta = mensaje.get("interactive", {}).get("button_reply")
        if respuesta:
            tareas.add_task(handlers.manejar_boton, telefono, respuesta.get("id", ""))
    elif tipo == "text":
        texto = mensaje.get("text", {}).get("body", "")
        tareas.add_task(handlers.manejar_texto, telefono, texto)


@app.post("/webhook")
async def recibir_webhook(request: Request, tareas: BackgroundTasks):
    # Siempre 200 y rápido: el trabajo pesado va en segundo plano.
    try:
        payload = await request.json()
    except ValueError:
        return {"status": "ignorado"}
    for mensaje in _mensajes(payload):
        _despachar(mensaje, tareas)
    return {"status": "ok"}
