# evaluador.py
# ─────────────────────────────────────────────────────────────
# Analiza la calidad de una imagen PIL y devuelve:
#   - score numérico (0.0 a 1.0)
#   - clasificación textual (Excelente / Buena / Regular / Mala)
#   - lista de problemas encontrados
#   - diccionario de métricas detalladas
#
# REUTILIZADO DE:
#   - Evaluador (Colab): lógica de score normalizado
#   - diagnosticar_imagen (VSCode): 7 métricas de análisis
# MODIFICACIONES:
#   - Score ponderado con 5 métricas (antes solo 3)
#   - Separación clara entre métricas, score, clasificación y problemas
#   - No imprime por sí solo: devuelve datos para que main.py decida
# ─────────────────────────────────────────────────────────────

import cv2
import numpy as np
from PIL import Image, ImageStat
from configuracion import (
    BRILLO_MIN, BRILLO_MAX,
    CONTRASTE_MIN,
    NITIDEZ_MIN,
    RUIDO_MAX,
    SATURACION_MIN,
    SCORE_EXCELENTE, SCORE_BUENA, SCORE_REGULAR,
    PESOS
)


# ══════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ══════════════════════════════════════════════════════════════

class Evaluador:
    """
    Analiza la calidad técnica de una imagen PIL.

    Uso:
        evaluador = Evaluador()
        resultado = evaluador.evaluar(imagen_pil)

        resultado["score"]          → float entre 0.0 y 1.0
        resultado["clasificacion"]  → "Excelente" / "Buena" / etc.
        resultado["problemas"]      → lista de strings
        resultado["metricas"]       → dict con valores numéricos
    """

    def evaluar(self, img_pil: Image.Image) -> dict:
        """
        Punto de entrada principal. Orquesta todo el análisis.

        Parámetros:
            img_pil: imagen PIL en cualquier modo (se convierte internamente)

        Retorna:
            dict con score, clasificacion, problemas y metricas
        """
        # Preparamos las versiones de la imagen que necesitamos
        # Una sola vez acá, para no repetir conversiones en cada método
        img_pil_rgb = img_pil.convert("RGB")
        img_gris_pil = img_pil.convert("L")           # PIL en grises
        img_gris_cv = np.array(img_gris_pil)          # OpenCV en grises
        img_hsv = cv2.cvtColor(                        # HSV para saturación
            np.array(img_pil_rgb),
            cv2.COLOR_RGB2HSV
        )

        # Calculamos cada métrica por separado
        # Cada función devuelve (valor_numerico, sub_score, problema_o_None)
        val_brillo,    score_brillo,    prob_brillo    = self._analizar_brillo(img_gris_pil)
        val_contraste, score_contraste, prob_contraste = self._analizar_contraste(img_gris_pil)
        val_nitidez,   score_nitidez,   prob_nitidez   = self._analizar_nitidez(img_gris_cv)
        val_ruido,     score_ruido,     prob_ruido     = self._analizar_ruido(img_gris_cv)
        val_saturacion,score_saturacion,prob_saturacion= self._analizar_saturacion(img_hsv)

        # Armamos la lista de problemas (solo los que no son None)
        problemas = [p for p in [
            prob_brillo,
            prob_contraste,
            prob_nitidez,
            prob_ruido,
            prob_saturacion
        ] if p is not None]

        # Score final: promedio ponderado de los sub-scores
        score = self._calcular_score(
            score_brillo, score_contraste,
            score_nitidez, score_ruido, score_saturacion
        )

        # Clasificación basada en el score
        clasificacion = self._clasificar(score)

        # Métricas numéricas para mostrar en consola / guardar
        metricas = {
            "brillo":     round(val_brillo, 2),
            "contraste":  round(val_contraste, 2),
            "nitidez":    round(val_nitidez, 2),
            "ruido":      round(val_ruido, 2),
            "saturacion": round(val_saturacion, 2),
        }

        return {
            "score":         round(score, 4),
            "clasificacion": clasificacion,
            "problemas":     problemas,
            "metricas":      metricas,
        }


    # ══════════════════════════════════════════════════════════
    # MÉTODOS DE ANÁLISIS INDIVIDUALES
    # ══════════════════════════════════════════════════════════
    #
    # Cada método sigue el mismo contrato:
    #   Entrada: versión de la imagen que necesita
    #   Salida:  (valor_numerico, sub_score_0_a_1, problema_o_None)
    #
    # sub_score = 1.0 → esa métrica está perfecta
    # sub_score = 0.0 → esa métrica está en su peor estado posible
    # problema  = None → no hay problema en esa métrica
    # problema  = str  → descripción del problema encontrado
    # ══════════════════════════════════════════════════════════

    def _analizar_brillo(self, img_gris_pil: Image.Image):
        """
        Mide el brillo como el promedio de intensidad en escala de grises.

        0   = negro absoluto
        127 = gris medio (ideal teórico)
        255 = blanco absoluto

        Rango saludable definido en configuracion.py: BRILLO_MIN a BRILLO_MAX

        REUTILIZADO DE: Evaluador (Colab) + analizar_brillo (VSCode)
        """
        # ImageStat.Stat calcula estadísticas de la imagen
        # .mean[0] es el promedio del primer (y único) canal en grises
        stat = ImageStat.Stat(img_gris_pil)
        brillo = stat.mean[0]

        problema = None

        if brillo < BRILLO_MIN:
            # Calculamos cuán lejos está del mínimo aceptable
            # Cuanto más lejos, menor el sub-score
            sub_score = brillo / BRILLO_MIN
            if brillo < 40:
                problema = f"Imagen muy oscura (brillo: {brillo:.1f}/255)"
            else:
                problema = f"Imagen subexpuesta (brillo: {brillo:.1f}/255)"

        elif brillo > BRILLO_MAX:
            # Mismo criterio pero para sobreexposición
            # Calculamos cuánto se pasó del máximo
            exceso = brillo - BRILLO_MAX
            rango_maximo = 255 - BRILLO_MAX   # cuánto espacio hay para pasarse
            sub_score = max(0.0, 1.0 - (exceso / rango_maximo))
            if brillo > 220:
                problema = f"Imagen muy sobreexpuesta (brillo: {brillo:.1f}/255)"
            else:
                problema = f"Imagen sobreexpuesta (brillo: {brillo:.1f}/255)"

        else:
            # Está dentro del rango: sub-score perfecto
            sub_score = 1.0

        return brillo, sub_score, problema


    def _analizar_contraste(self, img_gris_pil: Image.Image):
        """
        Mide el contraste como la desviación estándar de los píxeles en grises.

        Desvío bajo → los píxeles tienen valores similares → imagen plana/gris
        Desvío alto → hay gran variedad de tonos → imagen con contraste

        REUTILIZADO DE: analizar_contraste (VSCode) + Evaluador (Colab)
        """
        stat = ImageStat.Stat(img_gris_pil)
        # stddev[0] = desviación estándar del canal de grises
        contraste = stat.stddev[0]

        problema = None

        if contraste < CONTRASTE_MIN:
            # Normalizamos: 0 cuando es 0, 1.0 cuando llega al mínimo
            sub_score = contraste / CONTRASTE_MIN
            if contraste < 15:
                problema = f"Contraste muy bajo, imagen casi plana (std: {contraste:.1f})"
            else:
                problema = f"Bajo contraste (std: {contraste:.1f})"
        else:
            sub_score = 1.0

        return contraste, sub_score, problema


    def _analizar_nitidez(self, img_gris_cv: np.ndarray):
        """
        Mide la nitidez usando la varianza del operador Laplaciano.

        El Laplaciano detecta cambios bruscos de intensidad (bordes).
        Varianza alta → muchos bordes nítidos → imagen enfocada
        Varianza baja → pocos bordes → imagen desenfocada

        Por qué normalizamos por megapíxeles:
            Una imagen 4K tiene más píxeles que una 640x480.
            La varianza absoluta siempre es mayor en imágenes más grandes,
            aunque ambas estén igual de desenfocadas.
            Dividir por megapíxeles hace el valor comparable entre resoluciones.

        REUTILIZADO DE: Evaluador (Colab) con la normalización por megapíxeles
        """
        alto, ancho = img_gris_cv.shape
        megapixeles = (alto * ancho) / 1_000_000

        # cv2.CV_64F: usamos float64 para no perder precisión en el cálculo
        varianza_cruda = cv2.Laplacian(img_gris_cv, cv2.CV_64F).var()

        # Normalizamos por tamaño de imagen
        nitidez = varianza_cruda / megapixeles if megapixeles > 0 else varianza_cruda

        problema = None

        if nitidez < NITIDEZ_MIN:
            sub_score = nitidez / NITIDEZ_MIN
            if nitidez < 30:
                problema = f"Imagen muy desenfocada (nitidez: {nitidez:.1f})"
            else:
                problema = f"Imagen ligeramente desenfocada (nitidez: {nitidez:.1f})"
        else:
            sub_score = 1.0

        return nitidez, sub_score, problema


    def _analizar_ruido(self, img_gris_cv: np.ndarray):
        """
        Estima el ruido midiendo la variación en una zona central pequeña.

        La lógica es: una zona central de la imagen debería ser
        relativamente uniforme. Si hay mucha variación ahí, es ruido
        y no detalle real de la imagen.

        Por qué la zona central:
            Los bordes de la imagen suelen tener más variación natural
            (objetos, fondo, etc.). El centro es más representativo de
            una zona "plana" para medir ruido.

        REUTILIZADO DE: analizar_ruido (VSCode) — misma lógica exacta
        """
        h, w = img_gris_cv.shape

        # Tomamos un parche de 40x40 píxeles en el centro
        # Si la imagen es muy pequeña, tomamos lo que haya
        margen_h = min(20, h // 4)
        margen_w = min(20, w // 4)
        zona = img_gris_cv[
            h // 2 - margen_h : h // 2 + margen_h,
            w // 2 - margen_w : w // 2 + margen_w
        ]

        # std de la zona central: cuánto varían los píxeles entre sí
        ruido = float(zona.std())

        problema = None

        if ruido > RUIDO_MAX:
            # Invertimos: más ruido → menor sub_score
            # Limitamos a 0.0 mínimo con max()
            sub_score = max(0.0, 1.0 - ((ruido - RUIDO_MAX) / RUIDO_MAX))
            if ruido > 35:
                problema = f"Ruido alto en zonas uniformes (std central: {ruido:.1f})"
            else:
                problema = f"Ruido moderado (std central: {ruido:.1f})"
        else:
            sub_score = 1.0

        return ruido, sub_score, problema


    def _analizar_saturacion(self, img_hsv: np.ndarray):
        """
        Mide la saturación promedio usando el canal S del espacio HSV.

        HSV = Hue (tono), Saturation (saturación), Value (brillo)
        Canal S: 0 = gris puro, 255 = color puro y vivo

        Por qué HSV y no RGB para medir saturación:
            En RGB no hay una forma directa de medir viveza del color.
            En HSV, el canal S lo mide explícitamente.

        REUTILIZADO DE: analizar_saturacion (VSCode)
        """
        # img_hsv[:, :, 1] → todos los píxeles, canal S (índice 1)
        saturacion = float(img_hsv[:, :, 1].mean())

        problema = None

        if saturacion < SATURACION_MIN:
            sub_score = saturacion / SATURACION_MIN
            problema = f"Imagen con poca saturación/colores apagados (sat: {saturacion:.1f}/255)"
        else:
            sub_score = 1.0

        return saturacion, sub_score, problema


    # ══════════════════════════════════════════════════════════
    # SCORE Y CLASIFICACIÓN
    # ══════════════════════════════════════════════════════════

    def _calcular_score(self, s_brillo, s_contraste,
                        s_nitidez, s_ruido, s_saturacion) -> float:
        """
        Calcula el score final como promedio ponderado de los sub-scores.

        Por qué ponderado y no promedio simple:
            No todos los defectos son igual de molestos visualmente.
            El desenfoque y el mal brillo son más obvios que el ruido leve.
            Los pesos están en configuracion.py para poder ajustarlos fácilmente.
        """
        score = (
            s_brillo     * PESOS["brillo"]     +
            s_contraste  * PESOS["contraste"]  +
            s_nitidez    * PESOS["nitidez"]    +
            s_ruido      * PESOS["ruido"]      +
            s_saturacion * PESOS["saturacion"]
        )

        # Nos aseguramos de que el resultado esté siempre entre 0.0 y 1.0
        return max(0.0, min(1.0, score))


    def _clasificar(self, score: float) -> str:
        """
        Convierte el score numérico en una etiqueta legible.

        Los umbrales vienen de configuracion.py.
        Separar esto en su propio método permite cambiarlo
        sin tocar la lógica de cálculo.
        """
        if score >= SCORE_EXCELENTE:
            return "Excelente"
        elif score >= SCORE_BUENA:
            return "Buena"
        elif score >= SCORE_REGULAR:
            return "Regular"
        else:
            return "Mala"