# ─────────────────────────────────────────────────────────────
# Funciones de soporte reutilizables: lectura/escritura de
# imágenes y conversión entre formatos OpenCV ↔ PIL.
# No contiene lógica de evaluación ni de mejora.
# ─────────────────────────────────────────────────────────────

import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from configuracion import CARPETA_SALIDA


# ══════════════════════════════════════════════════════════════
# LECTURA DE IMÁGENES
# ══════════════════════════════════════════════════════════════

def leer_imagen_cv(ruta: str) -> np.ndarray:
    """
    Lee una imagen desde disco y la devuelve como array OpenCV (BGR).

    Por qué usamos cv2.imdecode en lugar de cv2.imread:
    - cv2.imread falla silenciosamente con rutas que tienen tildes,
      espacios o caracteres especiales en Windows.
    - cv2.imdecode lee los bytes crudos del archivo, lo que es más robusto.

    Parámetros:
        ruta: ruta completa al archivo de imagen (str o Path)

    Retorna:
        Array NumPy en formato BGR (como lo usa OpenCV)

    Lanza:
        FileNotFoundError si el archivo no existe
        ValueError si el archivo no es una imagen válida
    """
    ruta = Path(ruta)

    # Verificamos que el archivo exista antes de intentar leerlo
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    # Leemos los bytes crudos del archivo
    with open(str(ruta), 'rb') as f:
        data = f.read()

    # Convertimos los bytes a un array NumPy de enteros sin signo (uint8)
    # np.frombuffer interpreta los bytes como números
    file_bytes = np.frombuffer(data, np.uint8)

    # cv2.imdecode decodifica esos bytes como imagen en color (BGR)
    # IMREAD_COLOR siempre devuelve 3 canales (BGR), incluso si la imagen es gris
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError(f"El archivo no es una imagen válida: {ruta}")

    return img


def leer_imagen_pil(ruta: str) -> Image.Image:
    """
    Lee una imagen desde disco y la devuelve como objeto PIL Image.

    PIL es más conveniente para operaciones de mejora de tono
    (brillo, contraste, saturación) mientras que OpenCV es mejor
    para análisis numérico.

    Parámetros:
        ruta: ruta completa al archivo de imagen

    Retorna:
        Objeto PIL Image en modo RGB
    """
    ruta = Path(ruta)

    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    # PIL.Image.open es lazy: no carga los píxeles hasta que se necesitan.
    # .convert("RGB") fuerza la carga y garantiza 3 canales en el orden correcto.
    # Esto también maneja imágenes RGBA (con transparencia) y en escala de grises.
    return Image.open(str(ruta)).convert("RGB")


# ══════════════════════════════════════════════════════════════
# CONVERSIÓN ENTRE FORMATOS
# ══════════════════════════════════════════════════════════════

def cv_a_pil(img_cv: np.ndarray) -> Image.Image:
    """
    Convierte un array OpenCV (BGR) a objeto PIL Image (RGB).

    Por qué es necesario:
        OpenCV almacena los canales en orden BGR.
        PIL los espera en orden RGB.
        Sin esta conversión, los rojos aparecen azules y viceversa.

    Parámetros:
        img_cv: array NumPy en formato BGR (resultado de OpenCV)

    Retorna:
        Objeto PIL Image en modo RGB
    """
    # cv2.COLOR_BGR2RGB invierte el orden de los canales: BGR → RGB
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

    # Image.fromarray construye un objeto PIL desde un array NumPy
    return Image.fromarray(img_rgb)


def pil_a_cv(img_pil: Image.Image) -> np.ndarray:
    """
    Convierte un objeto PIL Image (RGB) a array OpenCV (BGR).

    Parámetros:
        img_pil: objeto PIL Image (cualquier modo; se convierte a RGB primero)

    Retorna:
        Array NumPy en formato BGR
    """
    # Nos aseguramos de que la imagen PIL esté en RGB antes de convertir
    img_rgb = np.array(img_pil.convert("RGB"))

    # cv2.COLOR_RGB2BGR invierte el orden: RGB → BGR
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


# ══════════════════════════════════════════════════════════════
# GUARDADO DE IMÁGENES
# ══════════════════════════════════════════════════════════════

def guardar_imagen(imagen, nombre_archivo: str) -> str:
    """
    Guarda una imagen en la carpeta de salida definida en configuracion.py.

    Acepta tanto arrays OpenCV como objetos PIL Image para que
    cualquier módulo pueda guardar sin preocuparse por el formato.

    Parámetros:
        imagen: array NumPy (OpenCV BGR) o PIL Image
        nombre_archivo: nombre del archivo destino (ej: "resultado.jpg")

    Retorna:
        Ruta completa donde se guardó el archivo (str)
    """
    # Creamos la carpeta de salida si no existe
    # parents=True crea carpetas intermedias si hacen falta
    # exist_ok=True no lanza error si ya existe
    carpeta = Path(CARPETA_SALIDA)
    carpeta.mkdir(parents=True, exist_ok=True)

    ruta_destino = carpeta / nombre_archivo

    # Detectamos el tipo y guardamos de la forma correcta para cada uno
    if isinstance(imagen, np.ndarray):
        # Array OpenCV: cv2.imwrite espera BGR, que es el formato nativo de OpenCV
        cv2.imwrite(str(ruta_destino), imagen)

    elif isinstance(imagen, Image.Image):
        # PIL Image: .save() maneja el formato según la extensión del nombre
        imagen.save(str(ruta_destino))

    else:
        raise TypeError(f"Tipo de imagen no soportado: {type(imagen)}")

    return str(ruta_destino)


# ══════════════════════════════════════════════════════════════
# VISUALIZACIÓN EN CONSOLA
# ══════════════════════════════════════════════════════════════

def imprimir_separador(titulo: str = ""):
    """
    Imprime una línea decorativa con título opcional.
    Mejora la legibilidad de la salida en consola.

    Ejemplo de salida:
        ══════════════════ EVALUACIÓN INICIAL ══════════════════
    """
    ancho = 55
    if titulo:
        # Centramos el título dentro de la línea
        print(f"\n{'═' * ancho}")
        print(f"  {titulo}")
        print(f"{'═' * ancho}")
    else:
        print(f"\n{'─' * ancho}")


def imprimir_resultado_evaluacion(score: float, clasificacion: str,
                                   problemas: list, iteracion: int = 0):
    """
    Muestra en consola los resultados de una evaluación de forma clara.

    Parámetros:
        score: número entre 0.0 y 1.0
        clasificacion: "Excelente", "Buena", "Regular" o "Mala"
        problemas: lista de strings describiendo los problemas encontrados
        iteracion: número de iteración actual (0 = evaluación inicial)
    """
    if iteracion == 0:
        imprimir_separador("EVALUACIÓN INICIAL")
    else:
        imprimir_separador(f"EVALUACIÓN — ITERACIÓN {iteracion}")

    # Mostramos score como porcentaje para que sea más intuitivo
    print(f"  Score       : {score:.2f} ({score * 100:.1f}%)")
    print(f"  Clasificación: {clasificacion}")

    if problemas:
        print(f"\n  Problemas detectados ({len(problemas)}):")
        for p in problemas:
            # Cada problema con sangría para diferenciarlo del resto
            print(f"    • {p}")
    else:
        print("\n  ✅ No se detectaron problemas.")

    imprimir_separador()