from fastapi import FastAPI

app = FastAPI(title="Bot de registro de ventas")


@app.get("/health")
def health():
    return {"status": "ok"}
