# main.py
# ─────────────────────────────────────────────────────────────
# Punto de entrada del sistema.
# Responsabilidad única: coordinar los módulos y presentar
# los resultados. No contiene lógica de procesamiento.
#
# Uso desde terminal:
#   python main.py ruta/a/imagen.jpg
#   python main.py ruta/a/imagen.jpg --salida resultado.jpg
# ─────────────────────────────────────────────────────────────

import argparse
from pathlib import Path

from utilidades import (
    leer_imagen_pil,
    guardar_imagen,
    imprimir_separador,
    imprimir_resultado_evaluacion
)
from evaluador import Evaluador
from mejorador import Mejorador


# ══════════════════════════════════════════════════════════════
# PRESENTACIÓN DE RESULTADOS
# ══════════════════════════════════════════════════════════════

def mostrar_bienvenida(ruta_imagen: str):
    """
    Muestra el encabezado del sistema al iniciar.
    """
    print("\n" + "═" * 55)
    print("   SISTEMA DE EVALUACIÓN Y MEJORA DE IMÁGENES")
    print("═" * 55)
    print(f"  Imagen  : {ruta_imagen}")
    print("═" * 55)


def mostrar_iteracion(entrada_historial: dict):
    """
    Muestra en consola el detalle de una iteración del ciclo.

    Parámetros:
        entrada_historial: un elemento de resultado["iteraciones"]
    """
    n          = entrada_historial["iteracion"]
    score      = entrada_historial["score"]
    clasif     = entrada_historial["clasificacion"]
    problemas  = entrada_historial["problemas"]
    metricas   = entrada_historial["metricas"]
    mejoras    = entrada_historial.get("mejoras_aplicadas", [])
    restaurado = entrada_historial.get("restaurado", False)

    # Mostramos score y clasificación
    imprimir_resultado_evaluacion(score, clasif, problemas, iteracion=n)

    # Mostramos las métricas numéricas detalladas
    print("  Métricas detalladas:")
    print(f"    Brillo     : {metricas['brillo']:.1f} / 255")
    print(f"    Contraste  : {metricas['contraste']:.1f}")
    print(f"    Nitidez    : {metricas['nitidez']:.1f}")
    print(f"    Ruido      : {metricas['ruido']:.1f}")
    print(f"    Saturación : {metricas['saturacion']:.1f} / 255")

    # Si hubo mejoras aplicadas en esta iteración, las mostramos
    if mejoras:
        print(f"\n  Mejoras aplicadas ({len(mejoras)}):")
        for m in mejoras:
            print(f"    → {m}")

    # Aviso si se restauró la versión anterior por empeoramiento
    if restaurado:
        print("\n  ⚠️  Las mejoras empeoraron la imagen.")
        print("      Se restauró la versión anterior.")


def mostrar_resumen_final(resultado: dict, ruta_guardada: str):
    """
    Muestra el resumen ejecutivo al finalizar el ciclo.

    Parámetros:
        resultado:     dict devuelto por Mejorador.procesar()
        ruta_guardada: ruta donde se guardó la imagen final
    """
    imprimir_separador("RESUMEN FINAL")

    score_i    = resultado["score_inicial"]
    score_f    = resultado["score_final"]
    mejora     = resultado["mejora_porcentual"]
    total_iter = resultado["total_iteraciones"]
    exitoso    = resultado["exitoso"]

    # Score inicial
    print(f"  Score inicial  : {score_i:.2f} ({score_i * 100:.1f}%)")
    print(f"  Score final    : {score_f:.2f} ({score_f * 100:.1f}%)")

    # Mostramos la mejora con signo para dejar claro si subió o bajó
    signo = "+" if mejora >= 0 else ""
    print(f"  Mejora total   : {signo}{mejora:.1f}%")
    print(f"  Iteraciones    : {total_iter}")

    # Resultado del ciclo
    if exitoso:
        print("\n  ✅ Calidad mínima alcanzada.")
    else:
        print("\n  ⚠️  No se alcanzó la calidad mínima.")
        print("      La imagen guardada es la mejor versión obtenida.")

    print(f"\n  Imagen guardada: {ruta_guardada}")
    print("═" * 55 + "\n")


# ══════════════════════════════════════════════════════════════
# FLUJO PRINCIPAL
# ══════════════════════════════════════════════════════════════

def main():
    """
    Orquesta el flujo completo del sistema.

    Flujo:
        1. Parsear argumentos CLI
        2. Cargar imagen
        3. Evaluación inicial
        4. Ciclo de mejora
        5. Mostrar resultados
        6. Guardar imagen final
    """

    # ── 1. ARGUMENTOS CLI ─────────────────────────────────────
    # argparse genera automáticamente --help con las descripciones
    # REUTILIZADO DE: main.py del VSCode — misma estructura
    parser = argparse.ArgumentParser(
        description="Sistema de evaluación y mejora automática de calidad de imágenes"
    )
    parser.add_argument(
        "imagen",
        help="Ruta a la imagen a procesar (ej: img_input/foto.jpg)"
    )
    parser.add_argument(
        "--salida",
        default="imagen_mejorada.jpg",
        help="Nombre del archivo de salida (default: imagen_mejorada.jpg)"
    )

    args = parser.parse_args()

    # Limpiamos comillas que Windows a veces agrega al arrastrar archivos
    ruta_imagen = args.imagen.strip('"').strip("'")

    # ── 2. CARGA DE IMAGEN ────────────────────────────────────
    mostrar_bienvenida(ruta_imagen)

    try:
        imagen_original = leer_imagen_pil(ruta_imagen)
    except FileNotFoundError as e:
        print(f"\n  ❌ Error: {e}")
        print("  Verificá que la ruta sea correcta.\n")
        return
    except ValueError as e:
        print(f"\n  ❌ Error: {e}")
        print("  El archivo no es una imagen válida.\n")
        return

    print(f"\n  Imagen cargada: {imagen_original.size[0]}×{imagen_original.size[1]} px")

    # ── 3. GUARDADO DE IMAGEN ORIGINAL ───────────────────────
    # Guardamos la original para poder compararla con el resultado
    nombre_original = Path(ruta_imagen).stem + "_original.jpg"
    ruta_original_guardada = guardar_imagen(imagen_original, nombre_original)
    print(f"  Original guardada en: {ruta_original_guardada}")

    # ── 4. EVALUACIÓN INICIAL ─────────────────────────────────
    evaluador = Evaluador()
    eval_inicial = evaluador.evaluar(imagen_original)

    imprimir_resultado_evaluacion(
        score=eval_inicial["score"],
        clasificacion=eval_inicial["clasificacion"],
        problemas=eval_inicial["problemas"],
        iteracion=0
    )

    print("  Métricas detalladas:")
    for nombre, valor in eval_inicial["metricas"].items():
        print(f"    {nombre.capitalize():<12}: {valor:.1f}")

    # ── 5. ¿NECESITA MEJORAS? ─────────────────────────────────
    from configuracion import SCORE_MINIMO_ACEPTABLE

    hay_problemas = len(eval_inicial["problemas"]) > 0
    score_ok      = eval_inicial["score"] >= SCORE_MINIMO_ACEPTABLE

    if score_ok and not hay_problemas:
    # Score bueno + sin problemas → terminamos
        imprimir_separador("RESULTADO")
        print("     La imagen ya cumple los estándares mínimos de calidad.")
        print("     No se aplicaron mejoras.")
        ruta_final = guardar_imagen(imagen_original, args.salida)
        print(f"  Imagen guardada: {ruta_final}\n")
        return

# Si hay problemas aunque el score sea bueno, igual mejoramos
    if score_ok and hay_problemas:
        print("     Score aceptable, pero se encontraron problemas.")
        print("     Se intentará mejorar de todas formas.\n")

    # ── 6. CICLO DE MEJORA ────────────────────────────────────
    imprimir_separador("INICIANDO CICLO DE MEJORA")
    print(f"  Score mínimo requerido : {SCORE_MINIMO_ACEPTABLE:.2f}")
    print(f"  Máximo de iteraciones  : ", end="")

    from configuracion import MAX_ITERACIONES
    print(MAX_ITERACIONES)

    mejorador = Mejorador()
    resultado = mejorador.procesar(imagen_original)

    # Mostramos el detalle de cada iteración (saltamos la 0, ya mostrada)
    for entrada in resultado["iteraciones"][1:]:
        mostrar_iteracion(entrada)

    # ── 7. GUARDADO Y RESUMEN ─────────────────────────────────
    ruta_final = guardar_imagen(resultado["imagen_final"], args.salida)
    mostrar_resumen_final(resultado, ruta_final)


# ── PUNTO DE ENTRADA ──────────────────────────────────────────
# Este bloque garantiza que main() solo se ejecuta cuando
# corremos el archivo directamente (python main.py),
# no cuando otro módulo lo importa.
if __name__ == "__main__":
    main()