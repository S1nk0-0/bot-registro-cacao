// Apps Script publicado como aplicación web. Recibe POST con JSON:
//   { "secret": "...", "accion": "append" | "update_estado" | "resumen", ... }
// El secreto se guarda en Propiedades del script (SHEETS_SECRET), no en el código.

var NOMBRE_HOJA = 'Registros';

// Mismo orden que app/schema.py (campos de la libreta + columnas del bot).
var ENCABEZADOS = [
  'codigo_registro', 'fecha', 'codigo_productor', 'producto', 'cantidad_kg',
  'precio_kg', 'total', 'comprador', 'observaciones',
  'id_mensaje', 'telefono_gestor', 'recibido_en', 'estado', 'confianza'
];

// Columnas que deben quedar como texto para que Sheets no las convierta en número.
var COLUMNAS_TEXTO = ['codigo_registro', 'codigo_productor', 'id_mensaje', 'telefono_gestor'];

function doGet() {
  return responder({ ok: true, mensaje: 'Bot de registro activo' });
}

function doPost(e) {
  var datos;
  try {
    datos = JSON.parse(e.postData.contents);
  } catch (err) {
    return responder({ ok: false, error: 'JSON inválido' });
  }

  var secreto = PropertiesService.getScriptProperties().getProperty('SHEETS_SECRET');
  if (!secreto || datos.secret !== secreto) {
    return responder({ ok: false, error: 'No autorizado' });
  }

  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var hoja = obtenerHoja();
    if (datos.accion === 'append') return responder(accionAppend(hoja, datos.registro));
    if (datos.accion === 'update_estado') {
      return responder(accionUpdateEstado(hoja, datos.id_mensaje, datos.estado));
    }
    if (datos.accion === 'resumen') return responder(accionResumen(hoja, datos.telefono));
    return responder({ ok: false, error: 'Acción desconocida' });
  } catch (err) {
    return responder({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

function responder(objeto) {
  return ContentService.createTextOutput(JSON.stringify(objeto))
    .setMimeType(ContentService.MimeType.JSON);
}

function obtenerHoja() {
  var libro = SpreadsheetApp.getActiveSpreadsheet();
  var hoja = libro.getSheetByName(NOMBRE_HOJA) || libro.insertSheet(NOMBRE_HOJA);
  if (hoja.getLastRow() === 0) {
    hoja.getRange(1, 1, 1, ENCABEZADOS.length).setValues([ENCABEZADOS]);
    hoja.setFrozenRows(1);
    COLUMNAS_TEXTO.forEach(function (nombre) {
      var col = ENCABEZADOS.indexOf(nombre) + 1;
      hoja.getRange(2, col, hoja.getMaxRows() - 1, 1).setNumberFormat('@');
    });
  }
  return hoja;
}

// Devuelve el número de fila (empezando en 2) del id_mensaje, o 0 si no existe.
function buscarFila(hoja, idMensaje) {
  var ultima = hoja.getLastRow();
  if (ultima < 2 || !idMensaje) return 0;
  var col = ENCABEZADOS.indexOf('id_mensaje') + 1;
  var ids = hoja.getRange(2, col, ultima - 1, 1).getValues();
  for (var i = 0; i < ids.length; i++) {
    if (String(ids[i][0]) === String(idMensaje)) return i + 2;
  }
  return 0;
}

function accionAppend(hoja, registro) {
  if (!registro || !registro.id_mensaje) {
    return { ok: false, error: 'Falta id_mensaje' };
  }
  // Si Meta reintenta un mensaje, no duplicamos la fila.
  if (buscarFila(hoja, registro.id_mensaje)) {
    return { ok: true, duplicado: true };
  }
  var fila = ENCABEZADOS.map(function (nombre) {
    var valor = registro[nombre];
    return valor === undefined || valor === null ? '' : valor;
  });
  hoja.appendRow(fila);
  return { ok: true };
}

function accionUpdateEstado(hoja, idMensaje, estado) {
  if (['pendiente', 'confirmado', 'revisar'].indexOf(estado) === -1) {
    return { ok: false, error: 'Estado inválido' };
  }
  var fila = buscarFila(hoja, idMensaje);
  if (!fila) return { ok: false, error: 'No existe ese id_mensaje' };
  hoja.getRange(fila, ENCABEZADOS.indexOf('estado') + 1).setValue(estado);
  return { ok: true };
}

// Suma kg y soles confirmados del mes actual para un teléfono (según recibido_en).
function accionResumen(hoja, telefono) {
  var ultima = hoja.getLastRow();
  var zona = Session.getScriptTimeZone();
  var mesActual = Utilities.formatDate(new Date(), zona, 'yyyy-MM');
  var kg = 0, soles = 0, registros = 0;

  if (ultima >= 2) {
    var valores = hoja.getRange(2, 1, ultima - 1, ENCABEZADOS.length).getValues();
    var iTel = ENCABEZADOS.indexOf('telefono_gestor');
    var iEstado = ENCABEZADOS.indexOf('estado');
    var iFecha = ENCABEZADOS.indexOf('recibido_en');
    var iKg = ENCABEZADOS.indexOf('cantidad_kg');
    var iTotal = ENCABEZADOS.indexOf('total');

    valores.forEach(function (f) {
      if (String(f[iTel]) !== String(telefono)) return;
      if (f[iEstado] !== 'confirmado') return;
      var recibido = new Date(f[iFecha]);
      if (isNaN(recibido.getTime())) return;
      if (Utilities.formatDate(recibido, zona, 'yyyy-MM') !== mesActual) return;
      kg += Number(f[iKg]) || 0;
      soles += Number(f[iTotal]) || 0;
      registros += 1;
    });
  }
  return { ok: true, mes: mesActual, kg: kg, soles: soles, registros: registros };
}
