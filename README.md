# Bot de registro de ventas por WhatsApp (PI3 – GTANW)

Bot de WhatsApp para jóvenes gestores de información de la Nación Wampís. El gestor toma una foto a una hoja de la libreta de ventas (piloto: cacao) y se la manda al bot. El bot:

1. Responde "Recibí tu foto, la estoy leyendo...".
2. Lee la hoja con Gemini y obtiene los datos.
3. Guarda una fila en Google Sheets con `estado = pendiente`.
4. Responde con un resumen y dos botones: **Sí** / **No**.
   - **Sí** → la fila pasa a `confirmado`.
   - **No** → la fila pasa a `revisar` y el bot pide la foto otra vez, más clara.
5. Si el gestor escribe **resumen**, el bot responde los kg y soles confirmados del mes.
6. Cualquier otro texto → mensaje de ayuda.

La libreta física sigue siendo el registro principal. El bot es un respaldo para cuando hay señal.

## Cómo está organizado

```
app/
  main.py        # FastAPI: GET /webhook, POST /webhook, GET /health
  config.py      # lee las variables de entorno
  schema.py      # campos del registro (si cambia la libreta, se cambia aquí)
  whatsapp.py    # descargar media, enviar texto y botones
  vision.py      # foto -> datos, con Gemini
  sheets.py      # habla con el Apps Script
  handlers.py    # la lógica del flujo
apps_script/Code.gs
tests/           # pytest, todo con mocks (no usa la red)
```

## Instalación

Necesitas Python 3.11 o más nuevo.

```bash
python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # luego llena los valores (ver abajo)
pytest                           # debe salir todo en verde
```

## Llenar el `.env`

El archivo `.env` **nunca se sube a git**. Solo `.env.example` está en el repo.

| Variable | De dónde sale |
|---|---|
| `WHATSAPP_TOKEN` | Meta for Developers → tu app → WhatsApp → configuración de la API. El token temporal dura 24 horas. |
| `WHATSAPP_PHONE_NUMBER_ID` | Misma pantalla: el ID del número de teléfono (no el número en sí). |
| `WHATSAPP_VERIFY_TOKEN` | Una clave que inventas tú (por ejemplo una frase larga). Debe ser igual a la que pongas en Meta. |
| `GRAPH_API_VERSION` | Versión de la Graph API, por ejemplo `v25.0`. Si la dejas vacía se usa la del código. |
| `GEMINI_API_KEY` | Google AI Studio → "Get API key". |
| `GEMINI_MODEL` | Nombre del modelo. Si la dejas vacía se usa `gemini-flash-latest`. |
| `SHEETS_WEBAPP_URL` | La URL que te da Google al publicar el Apps Script (ver abajo). |
| `SHEETS_SECRET` | Una clave que inventas tú. Debe ser igual a la que pongas en el Apps Script. |

## Publicar el Apps Script (Google Sheets)

1. Crea una hoja de cálculo nueva en Google Sheets.
2. Menú **Extensiones → Apps Script**.
3. Borra el contenido y pega todo `apps_script/Code.gs`. Guarda.
4. En **Configuración del proyecto** (el engranaje):
   - Zona horaria: `America/Lima`. El resumen "del mes" depende de esto.
   - En **Propiedades del script**, agrega `SHEETS_SECRET` con el mismo valor que pusiste en tu `.env`.
5. **Implementar → Nueva implementación → Tipo: Aplicación web**:
   - Ejecutar como: **Yo**.
   - Quién tiene acceso: **Cualquier usuario**.
   - Copia la URL que termina en `/exec` y ponla en `SHEETS_WEBAPP_URL`.
6. La primera vez, Google pide autorización: acéptala con tu cuenta.

Notas:
- El acceso "Cualquier usuario" es necesario para que el bot pueda llamar a la URL. Lo que protege la hoja es el `SHEETS_SECRET`: sin él, el script rechaza todo.
- Si cambias `Code.gs`, tienes que hacer **Implementar → Administrar implementaciones → editar → Nueva versión**. Si no, la URL sigue usando el código viejo.
- La hoja `Registros` y sus encabezados se crean solos con el primer mensaje.

## Correr el bot en tu computadora

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Prueba que esté vivo: abre <http://localhost:8000/health>. Debe responder `{"status":"ok"}`.

WhatsApp necesita una dirección pública para mandarte los mensajes. Para desarrollo usamos **ngrok**:

```bash
ngrok http 8000
```

ngrok te muestra una URL como `https://algo.ngrok-free.app`. Tu webhook es esa URL más `/webhook`. Esa URL cambia cada vez que reinicias ngrok (en el plan gratis), y entonces hay que actualizarla en Meta.

## Configurar el webhook en Meta

1. Entra a [Meta for Developers](https://developers.facebook.com/) y abre tu app (tipo "Business", con el producto **WhatsApp**).
2. En **WhatsApp → Configuración** (o *Configuration*), sección **Webhook**:
   - **URL de devolución de llamada:** `https://algo.ngrok-free.app/webhook`
   - **Token de verificación:** el mismo valor de `WHATSAPP_VERIFY_TOKEN`.
   - Pulsa **Verificar y guardar**. El bot debe estar corriendo, o Meta no podrá verificar.
3. En la misma sección, en **Campos del webhook**, suscríbete a **`messages`**.

## Probarlo con el número de prueba

1. En **WhatsApp → Configuración de la API** (*API Setup*) Meta te da un número de prueba y un token temporal.
2. En el campo **Para** (*To*), agrega tu propio WhatsApp como número de destinatario y confirma el código que te llega.
3. Manda un mensaje al número de prueba desde tu WhatsApp:
   - Escribe `hola` → debe responder la ayuda.
   - Manda una foto → usa `tests/fixtures/hoja_ejemplo.png` (pásala a tu teléfono). Debe responder con el resumen y los botones **Sí** / **No**.
   - Toca **Sí** y revisa que la fila en Google Sheets pase a `confirmado`.
   - Escribe `resumen` → debe mostrar los totales del mes.

Si algo no responde, mira la consola donde corre `uvicorn` y la interfaz de ngrok en <http://localhost:4040>, que muestra cada petición que llega.

## Pruebas

```bash
pytest
```

Ninguna prueba usa la red: WhatsApp, Gemini y el Apps Script están simulados.

Para regenerar la hoja de ejemplo: `python tests/fixtures/generar_hoja_ejemplo.py`.

## Pendientes

Cosas que no se pudieron comprobar al construir el bot y que el equipo debe verificar:

- **Nombre del modelo de Gemini.** No se pudo abrir la documentación de Google desde donde se construyó. El código usa el alias `gemini-flash-latest`, que puede cambiar sin aviso. Revisa [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) y, si quieres un modelo fijo, ponlo en `GEMINI_MODEL`.
- **Versión de la Graph API.** Tampoco se pudo abrir la documentación de Meta. El código usa `v25.0` por defecto, y hay indicios de que ya existe una `v26.0`. Revisa el [changelog de Meta](https://developers.facebook.com/docs/graph-api/changelog) y ajusta `GRAPH_API_VERSION`.
- **Nada se probó con servicios reales.** Las pruebas usan mocks. Falta una prueba de punta a punta con WhatsApp, Gemini y Google Sheets de verdad.
- **Lectura de letra a mano.** Solo se probó con una hoja generada con computadora (`hoja_ejemplo.png`). Hay que probar con fotos reales de la libreta (mala luz, letra difícil, hojas torcidas) y ajustar el prompt en `app/vision.py` si hace falta.
- **Apps Script.** Solo se probó la lógica con una simulación en Node, no en Google. Hay que comprobar en vivo el secreto, la zona horaria del resumen y el redirect de la URL `/exec`.
- **Payloads de WhatsApp.** Los ejemplos en `tests/fixtures/webhook_*.json` siguen el formato documentado por Meta, pero no son capturas de mensajes reales. Conviene reemplazarlos con payloads reales (se ven en la interfaz de ngrok).
- **Menús de Meta.** Los nombres de los menús de Meta for Developers cambian seguido; los pasos de arriba pueden no coincidir al pie de la letra.
- **Token de WhatsApp.** El token de prueba dura 24 horas. Para una demo larga o uso real hay que crear un token permanente (usuario del sistema).
- **Ids repetidos.** El bot recuerda los últimos ids de mensajes solo en memoria; si se reinicia, se olvida. El Apps Script evita filas duplicadas por `id_mensaje`, pero el bot igual volvería a contestar.
- **Campos de la libreta.** Son provisionales. Si cambian, se editan en `app/schema.py`, en `ENCABEZADOS` de `apps_script/Code.gs` y en el prompt de `app/vision.py`.
- **"Resumen del mes".** Cuenta por la fecha en que el bot recibió la foto, no por la `fecha` escrita en la hoja.
