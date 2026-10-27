# Bot de registro de ventas por WhatsApp (PI3 – GTANW)

## Qué es
Un bot de WhatsApp para jóvenes gestores de información de la Nación Wampís. El gestor toma foto a una hoja de la libreta de ventas (piloto: cacao) y la manda al bot. El bot lee la hoja con Gemini, guarda los datos en Google Sheets y le pide al gestor que confirme.

La libreta física sigue siendo el registro principal. El bot es una capa de respaldo y consolidación para cuando hay señal. Es un proyecto universitario (UTEC) y el MVP es para una demo.

## Flujo
1. El gestor manda una foto → el bot responde "Recibí tu foto, la estoy leyendo...".
2. El bot descarga la imagen de WhatsApp, la manda a Gemini y obtiene un JSON con los campos.
3. El bot guarda una fila en Google Sheets con `estado = pendiente`.
4. El bot responde con un resumen y dos botones: **Sí** / **No**.
   - Sí → la fila pasa a `estado = confirmado`.
   - No → la fila pasa a `estado = revisar` y el bot le pide mandar la foto otra vez, más clara.
5. Si el gestor escribe "resumen", el bot responde los kg y soles confirmados del mes para ese número.
6. Cualquier otro texto → mensaje de ayuda corto.

## Campos de la libreta (provisionales, pueden cambiar)
| Campo | Tipo | Ejemplo |
|---|---|---|
| codigo_registro | texto | CAC-001 |
| fecha | YYYY-MM-DD | 2026-10-28 |
| codigo_productor | texto | P-014 |
| producto | texto | cacao |
| cantidad_kg | número | 20 |
| precio_kg | número (S/) | 8.0 |
| total | número (S/) | 160.0 |
| comprador | texto | Cooperativa X |
| observaciones | texto | |

Columnas extra que agrega el bot: `id_mensaje`, `telefono_gestor`, `recibido_en`, `estado`, `confianza`.

Mantén los campos en un solo lugar (`app/schema.py`) para que cambiarlos sea fácil.
Si un campo no se lee bien, va como `null`. Nunca se inventa un valor.
Si `total` no viene en la hoja, se calcula `cantidad_kg * precio_kg`. Si viene y no cuadra, se pone `confianza = baja`.

## Stack
- Python 3.11+, FastAPI, uvicorn, httpx, pydantic, python-dotenv
- Gemini con el SDK `google-genai`. El modelo va en `GEMINI_MODEL`, con un modelo flash como default. Verifica en la documentación de Google cuál es el nombre vigente.
- WhatsApp Cloud API (Graph API). La versión va en `GRAPH_API_VERSION`. Verifica la versión vigente en la documentación de Meta.
- Google Sheets mediante un Apps Script publicado como aplicación web (`apps_script/Code.gs`). No se usan cuentas de servicio.
- Tests: pytest + respx (mock de httpx) + mocks del cliente de Gemini.

## Estructura esperada
```
app/
  main.py        # FastAPI: GET /webhook (verificación), POST /webhook (mensajes), GET /health
  config.py      # lee variables de entorno
  schema.py      # modelo pydantic del registro
  whatsapp.py    # descargar media, enviar texto, enviar botones
  vision.py      # foto -> JSON validado con Gemini
  sheets.py      # cliente del Apps Script (append, update estado, resumen)
  handlers.py    # lógica del flujo (foto, botón, texto)
apps_script/Code.gs
tests/
  fixtures/      # payloads de ejemplo de WhatsApp y respuestas de Gemini
.env.example
requirements.txt
README.md
```

## Variables de entorno (.env, nunca se commitea)
```
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
GRAPH_API_VERSION=
GEMINI_API_KEY=
GEMINI_MODEL=
SHEETS_WEBAPP_URL=
SHEETS_SECRET=
```

## Reglas
- Nunca escribas tokens ni llaves reales en el código, los tests o los commits. Solo `.env.example` con valores vacíos.
- Los tests no hacen llamadas de red reales. Todo lo externo (Graph API, Gemini, Apps Script) va con mocks.
- El POST /webhook responde 200 rápido y procesa en segundo plano (BackgroundTasks).
- Ignora mensajes repetidos usando el `id` del mensaje (Meta reintenta los webhooks).
- Verifica `SHEETS_SECRET` en el Apps Script para que nadie más pueda escribir en la hoja.
- Mensajes al usuario en español simple, cortos y sin tecnicismos.
- Código simple y legible, pensado para un equipo de estudiantes. No agregues capas ni dependencias que no hagan falta.
- Después de cada tarea de TAREAS.md: corre `pytest`, marca la tarea con [x] y haz un commit con un mensaje claro.
- Si algo de la documentación de Meta o de Google no está claro, déjalo anotado en el README en una sección "Pendientes" y sigue con lo demás.
