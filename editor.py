# ─────────────────────────────────────────────────────────────
# Define la jerarquía de clases para editar imágenes.
# Cada clase agrupa operaciones relacionadas.
# La clase Editor hereda de todas y es el punto de uso externo.
#
# REUTILIZADO DE: código Colab (ImagenBase, Tono, Filtros,
# Transformaciones, Segmentacion, Editor)
# MODIFICACIONES:
#   - __init__ acepta PIL Image además de rutas
#   - Se agregan reducir_ruido() y aumentar_saturacion()
#   - Se integra con utilidades.py para conversiones
# ─────────────────────────────────────────────────────────────

import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from utilidades import pil_a_cv, cv_a_pil


# ══════════════════════════════════════════════════════════════
# CLASE BASE
# ══════════════════════════════════════════════════════════════

class ImagenBase:
    """
    Clase base que encapsula una imagen PIL.
    Todas las clases de edición heredan de esta.

    Por qué encapsulamos con _image (guión bajo):
        El guión bajo es una convención en Python que indica
        "atributo de uso interno". Obliga a usar get_image()
        para acceder, lo que evita modificaciones accidentales
        desde afuera de la clase.
    """

    def __init__(self, fuente):
        """
        Inicializa el editor con una imagen.

        Parámetros:
            fuente: puede ser:
                - str o Path: ruta a un archivo de imagen en disco
                - PIL Image: imagen ya cargada en memoria

        Por qué aceptar PIL Image directamente:
            El mejorador trabaja con imágenes en memoria.
            Evitamos el ciclo inútil de guardar → leer → procesar.
        """
        if isinstance(fuente, (str, Path)):
            # Cargamos desde disco y forzamos RGB
            # RGB porque PIL internamente puede abrir RGBA, L (gris), etc.
            # Normalizar a RGB simplifica todas las operaciones siguientes.
            self._image = Image.open(str(fuente)).convert("RGB")

        elif isinstance(fuente, Image.Image):
            # Hacemos una copia para no modificar la imagen original
            # que nos pasaron desde afuera
            self._image = fuente.copy().convert("RGB")

        else:
            raise TypeError(
                f"fuente debe ser ruta (str/Path) o PIL Image, "
                f"no {type(fuente).__name__}"
            )

    def get_image(self) -> Image.Image:
        """
        Devuelve la imagen actual.

        Por qué un getter en lugar de acceso directo a _image:
            Si en el futuro cambiamos la representación interna
            (por ejemplo, a OpenCV), solo cambiamos este método.
            El resto del código no se entera.
        """
        return self._image

    def save(self, ruta_destino: str):
        """
        Guarda la imagen actual en disco.

        Parámetros:
            ruta_destino: ruta completa donde guardar (incluye nombre y extensión)

        Retorna:
            self para permitir encadenamiento: editor.brillo(1.2).save("out.jpg")
        """
        self._image.save(str(ruta_destino))
        return self


# ══════════════════════════════════════════════════════════════
# OPERACIONES DE TONO
# ══════════════════════════════════════════════════════════════

class Tono(ImagenBase):
    """
    Operaciones que modifican los valores de intensidad y color:
    brillo, contraste, saturación, escala de grises, ecualización.

    Por qué usamos ImageEnhance en lugar de OpenCV para esto:
        ImageEnhance de PIL aplica las operaciones de forma
        perceptualmente uniforme (basada en cómo el ojo humano
        percibe los cambios). OpenCV requiere más código manual
        para el mismo resultado.
    """

    def brillo(self, factor: float = 1.0):
        """
        Ajusta el brillo de la imagen.

        factor < 1.0 → más oscura  (ej: 0.7)
        factor = 1.0 → sin cambio
        factor > 1.0 → más clara   (ej: 1.3)

        Retorna self para encadenamiento.
        """
        self._image = ImageEnhance.Brightness(self._image).enhance(factor)
        return self

    def contraste(self, factor: float = 1.0):
        """
        Ajusta el contraste de la imagen.

        factor < 1.0 → menos contraste (imagen más plana)
        factor > 1.0 → más contraste   (diferencias más marcadas)
        """
        self._image = ImageEnhance.Contrast(self._image).enhance(factor)
        return self

    def saturacion(self, factor: float = 1.0):
        """
        Ajusta la saturación (viveza de los colores).

        factor = 0.0 → escala de grises total
        factor = 1.0 → sin cambio
        factor > 1.0 → colores más intensos
        """
        self._image = ImageEnhance.Color(self._image).enhance(factor)
        return self

    def escala_grises(self):
        """
        Convierte la imagen a escala de grises (modo "L" en PIL).
        "L" significa Luminance (luminancia).
        """
        self._image = self._image.convert("L")
        return self

    def ecualizar_histograma(self):
        """
        Redistribuye los valores de píxeles para maximizar el contraste.

        Cómo funciona: estira el histograma para que ocupe todo el rango 0-255.
        Es útil cuando la imagen tiene bajo contraste global.

        Limitación: puede sobreexponer si la imagen ya tiene buen contraste.
        Por eso en mejorador.py solo se aplica cuando el contraste es bajo.
        """
        self._image = ImageOps.equalize(self._image)
        return self


# ══════════════════════════════════════════════════════════════
# FILTROS
# ══════════════════════════════════════════════════════════════

class Filtros(ImagenBase):
    """
    Filtros espaciales que modifican la imagen basándose en
    la relación entre píxeles vecinos.
    """

    def desenfoque(self):
        """
        Aplica un desenfoque simple (promedia píxeles vecinos).
        Más agresivo que el gaussiano.
        """
        self._image = self._image.filter(ImageFilter.BLUR)
        return self

    def gaussiano(self, radio: float = 2.0):
        """
        Aplica desenfoque gaussiano (más suave y natural que el simple).

        radio: cuántos píxeles de radio abarca el desenfoque.
        Radio mayor = más desenfoque.
        """
        self._image = self._image.filter(ImageFilter.GaussianBlur(radio))
        return self

    def nitidez(self):
        """
        Aplica un filtro de nitidez (realza los bordes).

        Internamente PIL usa un kernel que resta el desenfoque
        de la imagen original (Unsharp Mask simplificado).
        """
        self._image = self._image.filter(ImageFilter.SHARPEN)
        return self

    def bordes(self):
        """
        Detecta y resalta los bordes de la imagen.
        El resultado es una imagen que muestra solo los contornos.
        """
        self._image = self._image.filter(ImageFilter.FIND_EDGES)
        return self

    def relieve(self):
        """
        Aplica efecto de relieve (emboss): simula iluminación lateral.
        Útil para visualizar texturas.
        """
        self._image = self._image.filter(ImageFilter.EMBOSS)
        return self

    def reducir_ruido(self):
        """
        Aplica filtro bilateral para reducir ruido preservando bordes.

        Por qué bilateral en lugar de gaussiano:
            El gaussiano desenfoca todo por igual (bordes incluidos).
            El bilateral desenfoca solo las zonas uniformes,
            preservando los bordes nítidos. Es más costoso
            computacionalmente pero da mejores resultados.

        Implementación con OpenCV porque PIL no tiene filtro bilateral.
        Usamos utilidades para la conversión PIL ↔ OpenCV.
        """
        # Convertimos PIL → OpenCV para usar cv2.bilateralFilter
        img_cv = pil_a_cv(self._image)

        # Parámetros: d=9 (diámetro del vecindario),
        # sigmaColor=75 (rango de color), sigmaSpace=75 (rango espacial)
        # Valores más altos = más suavizado
        filtrada = cv2.bilateralFilter(img_cv, 9, 75, 75)

        # Volvemos a PIL
        self._image = cv_a_pil(filtrada)
        return self


# ══════════════════════════════════════════════════════════════
# TRANSFORMACIONES GEOMÉTRICAS
# ══════════════════════════════════════════════════════════════

class Transformaciones(ImagenBase):
    """
    Operaciones que cambian la geometría de la imagen:
    rotación, escala, recorte, volteo.
    """

    def rotar(self, grados: int):
        """
        Rota la imagen en sentido antihorario.
        grados=90 → rota 90° a la izquierda.
        """
        self._image = self._image.rotate(grados)
        return self

    def redimensionar(self, size: tuple):
        """
        Cambia el tamaño de la imagen.

        Parámetros:
            size: tupla (ancho, alto) en píxeles. Ej: (800, 600)

        Nota: PIL no preserva proporción automáticamente.
        Si necesitás mantener el aspect ratio, calculá las
        dimensiones antes de llamar esta función.
        """
        self._image = self._image.resize(size)
        return self

    def recortar(self, box: tuple):
        """
        Recorta un área rectangular de la imagen.

        Parámetros:
            box: tupla (izquierda, arriba, derecha, abajo) en píxeles
            Ej: (100, 50, 400, 300) recorta desde (100,50) hasta (400,300)
        """
        self._image = self._image.crop(box)
        return self

    def flip_horizontal(self):
        """Espeja la imagen horizontalmente (izquierda ↔ derecha)."""
        self._image = self._image.transpose(Image.FLIP_LEFT_RIGHT)
        return self

    def flip_vertical(self):
        """Espeja la imagen verticalmente (arriba ↔ abajo)."""
        self._image = self._image.transpose(Image.FLIP_TOP_BOTTOM)
        return self


# ══════════════════════════════════════════════════════════════
# SEGMENTACIÓN
# ══════════════════════════════════════════════════════════════

class Segmentacion(ImagenBase):
    """
    Operaciones de segmentación: separar regiones de la imagen
    según criterios de intensidad o bordes.
    """

    def umbral(self, valor: int = 128):
        """
        Binariza la imagen: cada píxel queda en blanco o negro
        según si supera el valor umbral.

        valor=128: punto medio del rango 0-255.
        Útil para separar objetos del fondo en imágenes con
        buen contraste entre ambos.
        """
        # Primero convertimos a grises porque el umbral trabaja
        # con un solo canal de intensidad
        gray = self._image.convert("L")
        # lambda aplica la condición píxel por píxel
        self._image = gray.point(lambda p: 255 if p > valor else 0)
        return self

    def contornos(self):
        """
        Detecta y dibuja los contornos de los objetos en la imagen.

        Por qué OpenCV para esto y no PIL:
            cv2.Canny y cv2.findContours no tienen equivalente
            en PIL. Son algoritmos específicos de visión por computadora.

        Proceso:
            1. Convertir a grises
            2. Canny: detecta bordes (gradientes fuertes)
            3. findContours: encuentra las curvas cerradas
            4. drawContours: las dibuja sobre la imagen
        """
        img_np = np.array(self._image)

        # Manejamos el caso en que la imagen ya esté en grises
        # (si se llamó escala_grises() antes que contornos())
        if self._image.mode != 'L':
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            img_cv = img_np

        # Canny detecta bordes: umbral bajo=50, umbral alto=150
        edges = cv2.Canny(img_cv, 50, 150)

        # Encontramos los contornos externos (RETR_EXTERNAL)
        # CHAIN_APPROX_SIMPLE comprime segmentos rectos para ahorrar memoria
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Creamos imagen en color para dibujar los contornos en verde
        img_contour = cv2.cvtColor(img_cv, cv2.COLOR_GRAY2BGR)
        # -1 significa "todos los contornos", (0,255,0) es verde, 2 es grosor
        cv2.drawContours(img_contour, contours, -1, (0, 255, 0), 2)

        # Convertimos de vuelta a PIL usando nuestra utilidad
        self._image = cv_a_pil(img_contour)
        return self


# ══════════════════════════════════════════════════════════════
# EDITOR — CLASE PRINCIPAL
# ══════════════════════════════════════════════════════════════

class Editor(Tono, Filtros, Transformaciones, Segmentacion):
    """
    Clase principal de edición.

    Hereda de todas las clases anteriores mediante herencia múltiple.
    Esto significa que un objeto Editor puede hacer todo:
        editor.brillo(1.2).nitidez().ecualizar_histograma()


    El encadenamiento de métodos (method chaining) funciona porque
    cada método retorna 'self'.
    """
    pass