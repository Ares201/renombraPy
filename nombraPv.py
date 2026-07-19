# renombrar.py
from pathlib import Path
import re
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance
import logging

# Configuración de Tesseract (en Linux se instala en /usr/bin/tesseract)
# En Render, el Dockerfile lo instalará, así que no hace falta setear la ruta.
# Si falla, puedes forzarlo: pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

def preprocesar_imagen(imagen):
    if imagen.mode != "L":
        imagen = imagen.convert("L")
    enhancer = ImageEnhance.Contrast(imagen)
    imagen = enhancer.enhance(2.0)
    return imagen

def extraer_datos(texto):
    fecha_match = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", texto)
    if fecha_match:
        dia, mes, anio = fecha_match.groups()
        fecha = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
    else:
        fecha = None

    orden_match = re.search(r"\b(PV\s*[-:]?\s*\d{5,})\b", texto, re.IGNORECASE)
    if orden_match:
        orden = re.sub(r"\s+", "", orden_match.group(1)).upper()
    else:
        orden = None
    return fecha, orden

def ya_procesado(nombre):
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}-PV\d+\.pdf$", nombre, re.IGNORECASE)) or \
           bool(re.match(r"^otro_\d+\.pdf$", nombre, re.IGNORECASE))

def renombrar_pdfs(carpeta_path: str) -> dict:
    carpeta = Path(carpeta_path)
    if not carpeta.is_dir():
        return {"error": "Carpeta no existe"}

    renombrados = 0
    omitidos = 0
    contador_otro = 1
    errores = []

    for ruta in carpeta.glob("*.pdf"):
        if ya_procesado(ruta.name):
            continue
        try:
            # Solo primera página
            pagina = convert_from_path(
                str(ruta),
                first_page=1,
                last_page=1,
                dpi=300
            )[0]

            fecha = orden = None
            for angulo in (0, 90, 180, 270):
                img = pagina.rotate(angulo, expand=True) if angulo else pagina
                img_proc = preprocesar_imagen(img)
                texto = pytesseract.image_to_string(
                    img_proc,
                    config="--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:.- "
                )
                fecha, orden = extraer_datos(texto)
                if fecha and orden:
                    break

            if fecha and orden:
                nuevo_nombre = f"{fecha}-{orden}.pdf"
                # Evitar colisiones (añadir _1, _2...)
                base = nuevo_nombre.replace(".pdf", "")
                contador = 1
                while (carpeta / nuevo_nombre).exists():
                    nuevo_nombre = f"{base}_{contador}.pdf"
                    contador += 1
                ruta.rename(carpeta / nuevo_nombre)
                renombrados += 1
            else:
                # Sin datos: otro_#
                while (carpeta / f"otro_{contador_otro}.pdf").exists():
                    contador_otro += 1
                ruta.rename(carpeta / f"otro_{contador_otro}.pdf")
                omitidos += 1
                contador_otro += 1
        except Exception as e:
            errores.append(f"{ruta.name}: {str(e)}")
            omitidos += 1

    return {
        "renombrados": renombrados,
        "omitidos": omitidos,
        "errores": errores
    }