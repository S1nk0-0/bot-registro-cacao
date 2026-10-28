"""Simulador del chat de WhatsApp, para probar el bot sin Meta.

Usa la misma lógica del bot (app/handlers.py). Lo único que cambia es el canal:
en vez de WhatsApp, hay una página con un chat.

Modos:
  - Real:  usa Gemini y Google Sheets de verdad (necesita GEMINI_API_KEY,
           SHEETS_WEBAPP_URL y SHEETS_SECRET en el .env).
  - Demo:  `python simulador.py --demo`. No usa Gemini ni Sheets: lee siempre
           la hoja de ejemplo y guarda los registros en memoria.

Correr:  python simulador.py          y abrir http://localhost:8001
"""
import os
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse

from app import handlers, sheets, vision, whatsapp
from app.schema import Registro

TELEFONO = os.getenv("SIM_TELEFONO", "51900000000")

_mensajes: list[dict] = []
_fotos: dict[str, bytes] = {}
_registros_demo: list[dict] = []
_lock = threading.Lock()


# --- Canal falso: en vez de mandar a WhatsApp, guardamos para mostrar en la página.

def _agregar(de: str, texto: str, botones: list[dict] | None = None) -> None:
    with _lock:
        _mensajes.append({"i": len(_mensajes), "de": de, "texto": texto, "botones": botones or []})


def _enviar_texto(to: str, texto: str) -> None:
    _agregar("bot", texto)


def _enviar_botones(to: str, texto: str, botones: list[tuple[str, str]]) -> None:
    _agregar("bot", texto, [{"id": id_, "titulo": titulo} for id_, titulo in botones])


def _descargar_media(media_id: str) -> bytes:
    return _fotos[media_id]


# --- Modo demo: Gemini y Sheets falsos.

def _leer_hoja_demo(imagen_bytes: bytes, mime: str) -> Registro:
    time.sleep(1.5)  # para que se note que "está leyendo"
    return Registro(
        codigo_registro="CAC-001",
        fecha=date.today().isoformat(),
        codigo_productor="P-014",
        producto="cacao",
        cantidad_kg=20,
        precio_kg=8.0,
        total=160.0,
        comprador="Cooperativa X",
    )


def _agregar_registro_demo(registro: Registro) -> None:
    _registros_demo.append(registro.model_dump())


def _actualizar_estado_demo(id_mensaje: str, estado: str) -> None:
    for fila in _registros_demo:
        if fila["id_mensaje"] == id_mensaje:
            fila["estado"] = estado
            return
    raise sheets.ErrorSheets("No encontré ese registro")


def _resumen_demo(telefono: str) -> dict:
    confirmados = [
        f for f in _registros_demo
        if f["telefono_gestor"] == telefono and f["estado"] == "confirmado"
    ]
    return {
        "kg": sum(f["cantidad_kg"] or 0 for f in confirmados),
        "soles": sum(f["total"] or 0 for f in confirmados),
        "registros": len(confirmados),
        "mes": date.today().strftime("%Y-%m"),
    }


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    """Cambia el canal mientras el simulador corre y lo deja como estaba al cerrar."""
    demo = os.getenv("SIMULADOR_DEMO") == "1"
    app.state.demo = demo
    _mensajes.clear()
    _fotos.clear()
    _registros_demo.clear()

    originales = {
        (whatsapp, "enviar_texto"): whatsapp.enviar_texto,
        (whatsapp, "enviar_botones"): whatsapp.enviar_botones,
        (whatsapp, "descargar_media"): whatsapp.descargar_media,
        (vision, "leer_hoja"): vision.leer_hoja,
        (sheets, "agregar_registro"): sheets.agregar_registro,
        (sheets, "actualizar_estado"): sheets.actualizar_estado,
        (sheets, "resumen_mes"): sheets.resumen_mes,
    }
    whatsapp.enviar_texto = _enviar_texto
    whatsapp.enviar_botones = _enviar_botones
    whatsapp.descargar_media = _descargar_media
    if demo:
        vision.leer_hoja = _leer_hoja_demo
        sheets.agregar_registro = _agregar_registro_demo
        sheets.actualizar_estado = _actualizar_estado_demo
        sheets.resumen_mes = _resumen_demo
    try:
        yield
    finally:
        for (modulo, nombre), original in originales.items():
            setattr(modulo, nombre, original)


app = FastAPI(lifespan=_ciclo_de_vida)


def _en_segundo_plano(funcion, *args) -> None:
    """El bot tarda unos segundos; así la página puede ir mostrando cada mensaje."""

    def correr():
        try:
            funcion(*args)
        except Exception as e:  # el simulador muestra el error en vez de callarlo
            _agregar("sistema", f"Error: {e}")

    threading.Thread(target=correr, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def pagina():
    return PAGINA.replace("__DEMO__", "true" if app.state.demo else "false")


@app.get("/mensajes")
def mensajes(desde: int = 0):
    with _lock:
        return _mensajes[desde:]


@app.post("/foto")
async def foto(archivo: UploadFile = File(...)):
    id_mensaje = "sim-" + uuid.uuid4().hex[:12]
    _fotos[id_mensaje] = await archivo.read()
    mime = archivo.content_type or "image/jpeg"
    _en_segundo_plano(handlers.manejar_foto, TELEFONO, id_mensaje, id_mensaje, mime)
    return {"ok": True}


@app.post("/texto")
async def texto(request: Request):
    datos = await request.json()
    _en_segundo_plano(handlers.manejar_texto, TELEFONO, str(datos.get("texto", "")))
    return {"ok": True}


@app.post("/boton")
async def boton(request: Request):
    datos = await request.json()
    _en_segundo_plano(handlers.manejar_boton, TELEFONO, str(datos.get("id", "")))
    return {"ok": True}


PAGINA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bot de registro de ventas - simulador</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, sans-serif; background: #e5ddd5; height: 100vh; display: flex; flex-direction: column; }
  header { background: #075e54; color: #fff; padding: 12px 16px; }
  header b { font-size: 17px; }
  header small { display: block; opacity: .85; margin-top: 2px; }
  #demo { background: #fff3cd; color: #664d03; padding: 6px 16px; font-size: 13px; display: none; }
  #chat { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 8px; max-width: 720px; width: 100%; margin: 0 auto; }
  .msg { max-width: 80%; padding: 8px 12px; border-radius: 10px; white-space: pre-wrap; line-height: 1.4; box-shadow: 0 1px 1px rgba(0,0,0,.12); font-size: 15px; }
  .bot { background: #fff; align-self: flex-start; }
  .yo { background: #dcf8c6; align-self: flex-end; }
  .sistema { background: #f8d7da; color: #842029; align-self: center; font-size: 13px; }
  .msg img { max-width: 220px; border-radius: 6px; display: block; }
  .botones { display: flex; gap: 8px; margin-top: 8px; }
  .botones button { flex: 1; padding: 8px; border: 1px solid #075e54; background: #fff; color: #075e54; border-radius: 8px; font-size: 15px; cursor: pointer; }
  .botones button:disabled { opacity: .45; cursor: default; }
  footer { background: #f0f0f0; padding: 10px; display: flex; gap: 8px; max-width: 720px; width: 100%; margin: 0 auto; }
  footer input[type=text] { flex: 1; padding: 10px 12px; border: 1px solid #ccc; border-radius: 20px; font-size: 15px; }
  footer button { border: 0; background: #075e54; color: #fff; border-radius: 20px; padding: 0 16px; font-size: 15px; cursor: pointer; }
  footer button.foto { background: #fff; color: #075e54; border: 1px solid #075e54; }
</style>
</head>
<body>
<header><b>Bot de registro de ventas</b><small>Simulador del chat de WhatsApp</small></header>
<div id="demo">Modo demo: no usa Gemini ni Google Sheets. Siempre lee la hoja de ejemplo y guarda en memoria.</div>
<div id="chat"></div>
<footer>
  <input type="file" id="archivo" accept="image/*" hidden>
  <button class="foto" id="btnFoto">Foto</button>
  <input type="text" id="texto" placeholder="Escribe un mensaje (hola, resumen...)">
  <button id="btnEnviar">Enviar</button>
</footer>
<script>
const DEMO = __DEMO__;
const chat = document.getElementById('chat');
let desde = 0;

if (DEMO) document.getElementById('demo').style.display = 'block';

function esc(t) { return t.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function formato(t) { return esc(t).replace(/\\*(.+?)\\*/g, '<b>$1</b>'); }

function burbuja(clase, html) {
  const d = document.createElement('div');
  d.className = 'msg ' + clase;
  d.innerHTML = html;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

async function post(url, cuerpo) {
  await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cuerpo) });
}

function mostrarBot(m) {
  const d = burbuja(m.de === 'sistema' ? 'sistema' : 'bot', formato(m.texto));
  if (m.botones.length) {
    const fila = document.createElement('div');
    fila.className = 'botones';
    m.botones.forEach(b => {
      const btn = document.createElement('button');
      btn.textContent = b.titulo;
      btn.onclick = () => {
        fila.querySelectorAll('button').forEach(x => x.disabled = true);
        burbuja('yo', esc(b.titulo));
        post('/boton', { id: b.id });
      };
      fila.appendChild(btn);
    });
    d.appendChild(fila);
  }
}

async function sondear() {
  try {
    const r = await fetch('/mensajes?desde=' + desde);
    const nuevos = await r.json();
    nuevos.forEach(mostrarBot);
    desde += nuevos.length;
  } catch (e) {}
  setTimeout(sondear, 700);
}

document.getElementById('btnFoto').onclick = () => document.getElementById('archivo').click();
document.getElementById('archivo').onchange = async (ev) => {
  const f = ev.target.files[0];
  if (!f) return;
  burbuja('yo', '<img src="' + URL.createObjectURL(f) + '">');
  const datos = new FormData();
  datos.append('archivo', f);
  await fetch('/foto', { method: 'POST', body: datos });
  ev.target.value = '';
};

async function enviarTexto() {
  const campo = document.getElementById('texto');
  const t = campo.value.trim();
  if (!t) return;
  burbuja('yo', esc(t));
  campo.value = '';
  await post('/texto', { texto: t });
}
document.getElementById('btnEnviar').onclick = enviarTexto;
document.getElementById('texto').onkeydown = (ev) => { if (ev.key === 'Enter') enviarTexto(); };

sondear();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn

    if "--demo" in sys.argv:
        os.environ["SIMULADOR_DEMO"] = "1"
    modo = "DEMO (sin Gemini ni Sheets)" if os.getenv("SIMULADOR_DEMO") == "1" else "REAL (Gemini + Sheets)"
    print(f"Simulador en modo {modo}. Abre http://localhost:8001")
    uvicorn.run(app, host="127.0.0.1", port=8001)
