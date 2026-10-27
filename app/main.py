from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app import config

app = FastAPI(title="Bot de registro de ventas")


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
