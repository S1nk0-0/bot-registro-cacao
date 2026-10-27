"""Lógica del flujo: foto, botón y texto."""
import httpx

from app import sheets, vision, whatsapp
from app.schema import CamposLibreta, Registro

MSG_ACUSE = "Recibí tu foto, la estoy leyendo..."
MSG_NO_LEI = "No pude leer la foto, ¿puedes mandarla de nuevo?"
MSG_NO_GUARDE = "No pude guardar el registro. Intenta de nuevo en un rato."
MSG_CONFIRMADO = "¡Listo, quedó registrado!"
MSG_REVISAR = "Entendido. Mándame la foto otra vez, más clara y con buena luz."
MSG_AYUDA = (
    "Hola. Mándame una foto de la hoja de tu libreta y yo la leo.\n"
    "Escribe *resumen* para ver tus totales del mes."
)

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre",
]


def _numero(valor) -> str:
    return f"{valor:g}"


def _soles(valor) -> str:
    return f"S/ {valor:.2f}"


def texto_resumen(r: Registro) -> str:
    """Mensaje con lo que se leyó, para que el gestor lo confirme."""
    no_leido = "no se leyó"
    lineas = [
        "Esto leí de tu hoja:",
        f"• Código: {r.codigo_registro or no_leido}",
        f"• Fecha: {r.fecha or no_leido}",
        f"• Productor: {r.codigo_productor or no_leido}",
        f"• Producto: {r.producto or no_leido}",
        f"• Cantidad: {_numero(r.cantidad_kg) + ' kg' if r.cantidad_kg is not None else no_leido}",
        f"• Precio por kg: {_soles(r.precio_kg) if r.precio_kg is not None else no_leido}",
        f"• Total: {_soles(r.total) if r.total is not None else no_leido}",
        f"• Comprador: {r.comprador or no_leido}",
    ]
    if r.observaciones:
        lineas.append(f"• Observaciones: {r.observaciones}")
    if r.confianza == "baja":
        lineas.append("\nOjo: el total no cuadra con kg × precio. Revísalo bien.")
    lineas.append("\n¿Está bien?")
    return "\n".join(lineas)


def _sin_datos(r: Registro) -> bool:
    return all(getattr(r, campo) is None for campo in CamposLibreta.model_fields)


def manejar_foto(telefono: str, id_mensaje: str, media_id: str, mime: str) -> None:
    whatsapp.enviar_texto(telefono, MSG_ACUSE)

    try:
        imagen = whatsapp.descargar_media(media_id)
        leido = vision.leer_hoja(imagen, mime)
    except (vision.ErrorLectura, httpx.HTTPError):
        whatsapp.enviar_texto(telefono, MSG_NO_LEI)
        return
    if _sin_datos(leido):
        whatsapp.enviar_texto(telefono, MSG_NO_LEI)
        return

    registro = leido.model_copy(
        update={"id_mensaje": id_mensaje, "telefono_gestor": telefono, "estado": "pendiente"}
    )
    try:
        sheets.agregar_registro(registro)
    except sheets.ErrorSheets:
        whatsapp.enviar_texto(telefono, MSG_NO_GUARDE)
        return

    whatsapp.enviar_botones(
        telefono,
        texto_resumen(registro),
        [(f"si:{id_mensaje}", "Sí"), (f"no:{id_mensaje}", "No")],
    )


def manejar_boton(telefono: str, boton_id: str) -> None:
    accion, _, id_mensaje = boton_id.partition(":")
    if accion not in ("si", "no") or not id_mensaje:
        whatsapp.enviar_texto(telefono, MSG_AYUDA)
        return

    estado = "confirmado" if accion == "si" else "revisar"
    try:
        sheets.actualizar_estado(id_mensaje, estado)
    except sheets.ErrorSheets:
        whatsapp.enviar_texto(telefono, MSG_NO_GUARDE)
        return
    whatsapp.enviar_texto(telefono, MSG_CONFIRMADO if accion == "si" else MSG_REVISAR)


def _nombre_mes(mes: str) -> str:
    """'2026-10' -> 'octubre 2026'."""
    try:
        anio, numero = mes.split("-")
        return f"{MESES[int(numero) - 1]} {anio}"
    except (ValueError, IndexError):
        return mes


def manejar_texto(telefono: str, texto: str) -> None:
    if texto.strip().lower() != "resumen":
        whatsapp.enviar_texto(telefono, MSG_AYUDA)
        return

    try:
        datos = sheets.resumen_mes(telefono)
    except sheets.ErrorSheets:
        whatsapp.enviar_texto(telefono, "No pude calcular tu resumen. Intenta de nuevo en un rato.")
        return

    mes = _nombre_mes(datos.get("mes", ""))
    if not datos.get("registros"):
        whatsapp.enviar_texto(telefono, f"En {mes} todavía no tienes ventas confirmadas.")
        return
    whatsapp.enviar_texto(
        telefono,
        f"Resumen de {mes}:\n"
        f"• Ventas confirmadas: {datos['registros']}\n"
        f"• Cantidad: {_numero(datos['kg'])} kg\n"
        f"• Total: {_soles(datos['soles'])}",
    )
