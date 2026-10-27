# Tareas

Trabaja en orden. Al terminar cada una: `pytest` en verde, marca [x] y haz commit.

- [x] **1. Base del proyecto**
  `requirements.txt`, `.env.example`, `.gitignore` (incluye `.env`), `app/config.py`, `GET /health` y un test que pase.

- [x] **2. Verificación del webhook**
  `GET /webhook` devuelve `hub.challenge` si `hub.verify_token` coincide; si no, 403. Tests para los dos casos.

- [x] **3. Recepción de mensajes**
  `POST /webhook` parsea el payload de Meta, responde 200 de inmediato y manda a `handlers.py` según el tipo (image, interactive/button_reply, text). Ignora los payloads de estado (statuses) y los ids repetidos. Fixtures con payloads reales de ejemplo. Tests.

- [ ] **4. Cliente de WhatsApp (`whatsapp.py`)**
  `descargar_media(media_id)` (obtener la URL y luego bajar los bytes con el token), `enviar_texto(to, texto)` y `enviar_botones(to, texto, botones)` con reply buttons. Tests con respx que verifiquen la URL, los headers y el body.

- [ ] **5. Esquema (`schema.py`)**
  Modelo pydantic con los campos de CLAUDE.md, todos opcionales salvo los metadatos. Validación: números ≥ 0, fecha en formato válido, cálculo de `total` si falta y `confianza` baja si no cuadra. Tests.

- [ ] **6. Lectura con Gemini (`vision.py`)**
  `leer_hoja(imagen_bytes, mime) -> Registro`. Prompt en español que pida solo JSON con los campos del esquema, con `null` si un campo no se lee, sin inventar. Usa salida estructurada (JSON) del SDK. Maneja JSON inválido o un error de la API devolviendo un error claro. Tests con el cliente mockeado (caso bueno, campos faltantes, JSON roto).

- [ ] **7. Apps Script (`apps_script/Code.gs`)**
  `doPost` con acciones `append`, `update_estado` (por `id_mensaje`) y `resumen` (suma los kg y soles confirmados del mes para un teléfono). Valida el secreto. Crea los encabezados si la hoja está vacía. Responde JSON.

- [ ] **8. Cliente de Sheets (`sheets.py`)**
  Funciones para las tres acciones del Apps Script. Tests con respx.

- [ ] **9. Flujo completo (`handlers.py`)**
  - Foto: acuse → descargar → Gemini → append `pendiente` → resumen + botones Sí/No (el id del botón incluye `id_mensaje`).
  - Botón Sí → `confirmado` + "¡Listo, quedó registrado!".
  - Botón No → `revisar` + pedir la foto otra vez, más clara y con buena luz.
  - Texto "resumen" → respuesta con los totales del mes.
  - Otro texto → ayuda corta.
  - Si Gemini falla → "No pude leer la foto, ¿puedes mandarla de nuevo?".

  Tests de punta a punta de cada camino con todo mockeado.

- [ ] **10. Hoja de ejemplo**
  `tests/fixtures/hoja_ejemplo.png`: genera una imagen simple de una hoja de libreta con 1 o 2 ventas de cacao (con Pillow), para que el equipo la use en pruebas manuales.

- [ ] **11. README**
  Qué hace el bot, cómo instalarlo, cómo llenar `.env`, cómo publicar el Apps Script, cómo correrlo con ngrok, cómo configurar el webhook en Meta (URL + verify token + suscripción a `messages`) y cómo probarlo con el número de prueba. Incluye la sección "Pendientes".

- [ ] **12. Revisión final**
  `pytest` con 0 fallos, sin secretos en el repo (revisa con `git grep`), ningún TODO suelto en el código y todo commiteado.
