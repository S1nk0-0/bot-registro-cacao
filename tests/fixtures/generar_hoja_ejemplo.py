"""Genera hoja_ejemplo.png: una hoja de libreta con 2 ventas de cacao.

Uso (desde la raíz del repo):  python tests/fixtures/generar_hoja_ejemplo.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SALIDA = Path(__file__).parent / "hoja_ejemplo.png"
ANCHO, ALTO = 900, 1200

PAPEL = (252, 250, 240)
LINEA = (190, 205, 225)
MARGEN = (225, 120, 120)
TINTA = (25, 45, 140)
TITULO = (40, 40, 40)

FUENTE_IMPRESA = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FUENTE_TINTA = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
]

VENTAS = [
    {
        "Código": "CAC-001",
        "Fecha": "2026-10-28",
        "Productor": "P-014",
        "Producto": "cacao",
        "Cantidad": "20 kg",
        "Precio": "S/ 8.00 por kg",
        "Total": "S/ 160.00",
        "Comprador": "Cooperativa X",
    },
    {
        "Código": "CAC-002",
        "Fecha": "2026-10-28",
        "Productor": "P-020",
        "Producto": "cacao",
        "Cantidad": "12.5 kg",
        "Precio": "S/ 8.00 por kg",
        "Total": "S/ 100.00",
        "Comprador": "Cooperativa X",
    },
]


def cargar_fuente(rutas, tamano):
    for ruta in rutas:
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            continue
    return ImageFont.load_default(size=tamano)


def main():
    img = Image.new("RGB", (ANCHO, ALTO), PAPEL)
    d = ImageDraw.Draw(img)

    # Renglones y margen, como una hoja de cuaderno.
    for y in range(120, ALTO, 40):
        d.line([(0, y), (ANCHO, y)], fill=LINEA, width=2)
    d.line([(90, 0), (90, ALTO)], fill=MARGEN, width=3)

    titulo = cargar_fuente(FUENTE_IMPRESA, 34)
    etiqueta = cargar_fuente(FUENTE_IMPRESA, 22)
    tinta = cargar_fuente(FUENTE_TINTA, 34)

    d.text((110, 50), "LIBRETA DE VENTAS - CACAO", font=titulo, fill=TITULO)

    y = 150
    for n, venta in enumerate(VENTAS, start=1):
        d.text((110, y), f"Venta {n}", font=etiqueta, fill=TITULO)
        y += 40
        for campo, valor in venta.items():
            d.text((130, y + 4), f"{campo}:", font=etiqueta, fill=TITULO)
            d.text((330, y - 2), valor, font=tinta, fill=TINTA)
            y += 40
        y += 40

    img.save(SALIDA)
    print(f"Guardado en {SALIDA}")


if __name__ == "__main__":
    main()
