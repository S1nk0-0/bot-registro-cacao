from pathlib import Path

from PIL import Image

HOJA = Path(__file__).parent / "fixtures" / "hoja_ejemplo.png"


def test_hoja_de_ejemplo_es_una_imagen_valida():
    with Image.open(HOJA) as img:
        img.verify()
    with Image.open(HOJA) as img:
        assert img.format == "PNG"
        assert img.width > 0 and img.height > 0
