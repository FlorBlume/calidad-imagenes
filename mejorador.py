# mejorador.py
# ─────────────────────────────────────────────────────────────
# Coordina el ciclo iterativo de evaluación y mejora.
# Usa Evaluador para analizar y Editor para corregir.
# No contiene lógica de análisis ni de edición directa.
#
# REUTILIZADO DE: función mejorar() del Colab
# MODIFICACIONES:
#   - Clase en lugar de función suelta
#   - Mejoras diferenciadas según severidad del problema
#   - Devuelve historial completo de iteraciones
#   - Separación entre lógica de mejora y presentación
# ─────────────────────────────────────────────────────────────

from PIL import Image
from editor import Editor
from evaluador import Evaluador
from configuracion import (
    SCORE_MINIMO_ACEPTABLE,
    MAX_ITERACIONES
)


class Mejorador:
    """
    Ejecuta el ciclo iterativo de mejora de calidad de imagen.

    Uso:
        mejorador = Mejorador()
        resultado = mejorador.procesar(imagen_pil)

        resultado["imagen_final"]   → PIL Image procesada
        resultado["score_inicial"]  → float
        resultado["score_final"]    → float
        resultado["iteraciones"]    → lista con detalle de cada paso
        resultado["exitoso"]        → True si alcanzó el score mínimo
    """

    def __init__(self):
        # Instanciamos el evaluador una sola vez y lo reutilizamos
        # en todas las iteraciones. Crearlo dentro del bucle sería
        # un desperdicio de recursos.
        self._evaluador = Evaluador()


    # ══════════════════════════════════════════════════════════
    # PUNTO DE ENTRADA PRINCIPAL
    # ══════════════════════════════════════════════════════════

    def procesar(self, imagen_original: Image.Image) -> dict:
        """
        Ejecuta el ciclo completo de evaluación y mejora.

        Parámetros:
            imagen_original: PIL Image a procesar

        Retorna:
            dict con imagen_final, scores, historial e indicador de éxito
        """
        # Guardamos la original sin tocarla para poder mostrarla al final
        imagen_actual = imagen_original.copy()

        # Evaluación inicial — antes de cualquier modificación
        evaluacion_inicial = self._evaluador.evaluar(imagen_actual)
        score_inicial = evaluacion_inicial["score"]

        # Historial: lista de dicts, uno por iteración
        # Nos permite mostrar la evolución completa al usuario
        historial = [{
            "iteracion":    0,
            "score":        score_inicial,
            "clasificacion":evaluacion_inicial["clasificacion"],
            "problemas":    evaluacion_inicial["problemas"],
            "metricas":     evaluacion_inicial["metricas"],
            "mejoras_aplicadas": [],
            "imagen":       imagen_actual.copy(),
        }]

        #solo corta si el score es bueno Y no hay problemas
        hay_problemas = len(evaluacion_inicial["problemas"]) > 0

        if score_inicial >= SCORE_MINIMO_ACEPTABLE and not hay_problemas:
            return self._armar_resultado(
            imagen_final=imagen_actual,
            score_inicial=score_inicial,
            score_final=score_inicial,
            historial=historial,
            exitoso=True
        )

        # ── BUCLE ITERATIVO ───────────────────────────────────
        imagen_anterior = imagen_actual.copy()
        score_anterior  = score_inicial

        for i in range(1, MAX_ITERACIONES + 1):

            # Determinamos qué mejorar según los problemas actuales
            problemas_actuales = historial[-1]["problemas"]
            metricas_actuales  = historial[-1]["metricas"]

            # Aplicamos las mejoras y registramos cuáles se usaron
            imagen_mejorada, mejoras_aplicadas = self._aplicar_mejoras(
                imagen_actual,
                problemas_actuales,
                metricas_actuales
            )

            # Evaluamos la imagen después de las mejoras
            evaluacion_nueva = self._evaluador.evaluar(imagen_mejorada)
            score_nuevo      = evaluacion_nueva["score"]

            # ── CONTROL DE EMPEORAMIENTO ──────────────────────
            # Si las mejoras empeoraron la imagen, restauramos
            # la versión anterior y terminamos el ciclo.
            # REUTILIZADO DE: mejorar() del Colab — misma lógica
            if score_nuevo < score_anterior:
                historial.append({
                    "iteracion":         i,
                    "score":             score_anterior,
                    "clasificacion":     historial[-1]["clasificacion"],
                    "problemas":         historial[-1]["problemas"],
                    "metricas":          historial[-1]["metricas"],
                    "mejoras_aplicadas": mejoras_aplicadas,
                    "imagen":            imagen_anterior.copy(),
                    "restaurado":        True,   # flag para que main.py lo muestre
                })
                imagen_actual = imagen_anterior.copy()
                break

            # Registramos esta iteración en el historial
            historial.append({
                "iteracion":         i,
                "score":             score_nuevo,
                "clasificacion":     evaluacion_nueva["clasificacion"],
                "problemas":         evaluacion_nueva["problemas"],
                "metricas":          evaluacion_nueva["metricas"],
                "mejoras_aplicadas": mejoras_aplicadas,
                "imagen":            imagen_mejorada.copy(),
                "restaurado":        False,
            })

            # Actualizamos para la próxima iteración
            imagen_anterior = imagen_actual.copy()
            imagen_actual   = imagen_mejorada.copy()
            score_anterior  = score_nuevo

            # Si alcanzamos la calidad mínima, terminamos antes
            if score_nuevo >= SCORE_MINIMO_ACEPTABLE:
                break

        # ── FIN DEL BUCLE ─────────────────────────────────────
        score_final = historial[-1]["score"]
        exitoso     = score_final >= SCORE_MINIMO_ACEPTABLE

        return self._armar_resultado(
            imagen_final=imagen_actual,
            score_inicial=score_inicial,
            score_final=score_final,
            historial=historial,
            exitoso=exitoso
        )


    # ══════════════════════════════════════════════════════════
    # LÓGICA DE MEJORA
    # ══════════════════════════════════════════════════════════

    def _aplicar_mejoras(self, imagen: Image.Image,
                         problemas: list,
                         metricas: dict) -> tuple:
        """
        Decide qué mejoras aplicar según los problemas detectados
        y las ejecuta en el orden correcto.

        Por qué el orden importa:
            Aplicar nitidez antes de reducir ruido puede amplificar
            el ruido. El orden correcto es:
            1. Ruido (suavizar primero)
            2. Brillo y contraste (ajustar tonos)
            3. Nitidez (realzar bordes al final)

        Parámetros:
            imagen:    PIL Image actual
            problemas: lista de strings con los problemas detectados
            metricas:  dict con los valores numéricos actuales

        Retorna:
            (imagen_mejorada, lista_de_mejoras_aplicadas)
        """
        # Editor recibe PIL Image directamente (gracias al __init__ actualizado)
        editor = Editor(imagen)
        mejoras_aplicadas = []

        # Texto de todos los problemas junto para buscar palabras clave
        # Convertimos a minúsculas para búsqueda insensible a mayúsculas
        texto_problemas = " ".join(problemas).lower()

        # ── 1. RUIDO (siempre primero) ────────────────────────
        # Si hay ruido, lo reducimos antes de cualquier otra cosa
        # porque nitidez y contraste lo amplifican
        if "ruido" in texto_problemas:
            if "ruido alto" in texto_problemas:
                # Ruido severo: bilateral más agresivo
                editor.reducir_ruido()
                mejoras_aplicadas.append("Reducción de ruido (filtro bilateral)")
            else:
                # Ruido leve: gaussiano suave
                editor.gaussiano(radio=1.0)
                mejoras_aplicadas.append("Suavizado leve (gaussiano radio 1)")

        # ── 2. BRILLO ─────────────────────────────────────────
        if "oscura" in texto_problemas or "subexpuesta" in texto_problemas:
            brillo_actual = metricas["brillo"]
            if brillo_actual < 40:
                # Muy oscura: aumento fuerte
                editor.brillo(1.5)
                mejoras_aplicadas.append("Aumento de brillo fuerte (×1.5)")
            else:
                # Levemente oscura: aumento moderado
                editor.brillo(1.25)
                mejoras_aplicadas.append("Aumento de brillo moderado (×1.25)")

        elif "sobreexpuesta" in texto_problemas:
            brillo_actual = metricas["brillo"]
            if brillo_actual > 220:
                # Muy sobreexpuesta: reducción fuerte
                editor.brillo(0.65)
                mejoras_aplicadas.append("Reducción de brillo fuerte (×0.65)")
            else:
                # Levemente sobreexpuesta: reducción suave
                editor.brillo(0.82)
                mejoras_aplicadas.append("Reducción de brillo moderada (×0.82)")

        # ── 3. CONTRASTE ──────────────────────────────────────
        if "contraste" in texto_problemas:
            contraste_actual = metricas["contraste"]
            if contraste_actual < 15:
                # Contraste muy bajo: ecualización de histograma
                # (redistribuye los píxeles en todo el rango 0-255)
                editor.ecualizar_histograma()
                mejoras_aplicadas.append("Ecualización de histograma")
            else:
                # Contraste bajo: aumento moderado
                editor.contraste(1.4)
                mejoras_aplicadas.append("Mejora de contraste (×1.4)")

        # ── 4. SATURACIÓN ─────────────────────────────────────
        if "saturación" in texto_problemas or "saturacion" in texto_problemas:
            editor.saturacion(1.3)
            mejoras_aplicadas.append("Aumento de saturación (×1.3)")

        # ── 5. NITIDEZ (siempre al final) ─────────────────────
        # Se aplica al final para no amplificar ruido previo
        if "desenfocada" in texto_problemas:
            if "muy desenfocada" in texto_problemas:
                # Doble pasada de nitidez para casos severos
                editor.nitidez()
                editor.nitidez()
                mejoras_aplicadas.append("Nitidez doble (imagen muy desenfocada)")
            else:
                editor.nitidez()
                mejoras_aplicadas.append("Nitidez simple")

        # Si no se detectó ningún problema específico pero el score
        # es bajo, aplicamos una mejora genérica conservadora
        if not mejoras_aplicadas:
            editor.contraste(1.2)
            editor.brillo(1.05)
            mejoras_aplicadas.append("Mejora genérica conservadora (contraste + brillo leve)")

        return editor.get_image(), mejoras_aplicadas


    # ══════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════

    def _armar_resultado(self, imagen_final, score_inicial,
                         score_final, historial, exitoso) -> dict:
        """
        Construye el dict de resultado final de forma consistente.

        Separar esto en su propio método garantiza que siempre
        devolvemos la misma estructura, independientemente de
        por qué terminó el ciclo (éxito, empeoramiento, max iter).
        """
        mejora_porcentual = (score_final - score_inicial) * 100

        return {
            "imagen_final":       imagen_final,
            "score_inicial":      score_inicial,
            "score_final":        score_final,
            "mejora_porcentual":  round(mejora_porcentual, 2),
            "iteraciones":        historial,
            "total_iteraciones":  len(historial) - 1,  # sin contar la inicial
            "exitoso":            exitoso,
        }