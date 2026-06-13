# ─────────────────────────────────────────────────────────────
# Centraliza todos los parámetros del sistema.
# Ventaja: cambiar un valor aquí lo cambia en todo el proyecto.
# ─────────────────────────────────────────────────────────────

# ── UMBRALES DE EVALUACIÓN ────────────────────────────────────

# Brillo: promedio de píxeles en escala de grises (0=negro, 255=blanco)
# Rango saludable elegido: entre 60 y 190
BRILLO_MIN = 60       # Por debajo: imagen oscura
BRILLO_MAX = 190      # Por encima: imagen sobreexpuesta

# Contraste: desviación estándar de los píxeles en gris
# Valor bajo = imagen "plana", sin diferencia entre zonas claras y oscuras
CONTRASTE_MIN = 35    # Por debajo: bajo contraste

# Nitidez: varianza del operador Laplaciano (detecta bordes)
# Valor bajo = imagen borrosa (pocos cambios bruscos de intensidad)
NITIDEZ_MIN = 80      # Por debajo: imagen desenfocada

# Ruido: desviación estándar en zona central de la imagen
# Zona uniforme con alta variación = ruido
RUIDO_MAX = 20        # Por encima: ruido visible

# Saturación: canal S del espacio HSV (0=gris, 255=color puro)
SATURACION_MIN = 25   # Por debajo: imagen casi sin color

# ── SCORE Y CLASIFICACIÓN ─────────────────────────────────────

# El score es un número entre 0.0 y 1.0
# Se calcula como promedio de sub-scores de cada métrica

SCORE_EXCELENTE = 0.85   # >= 0.85 → "Excelente"
SCORE_BUENA     = 0.65   # >= 0.65 → "Buena"
SCORE_REGULAR   = 0.45   # >= 0.45 → "Regular"
# < 0.45              → "Mala"

# Umbral mínimo para que el ciclo de mejora se detenga
SCORE_MINIMO_ACEPTABLE = 0.65

# ── CICLO DE MEJORA ───────────────────────────────────────────

# Máximo de iteraciones para evitar bucles infinitos
MAX_ITERACIONES = 5

# ── RUTAS DE SALIDA ───────────────────────────────────────────

CARPETA_SALIDA = "img_output"
CARPETA_ENTRADA = "img_input"

# ── PESOS DEL SCORE ───────────────────────────────────────────
# Cuánto contribuye cada métrica al score final.
# Deben sumar 1.0
# Brillo y nitidez pesan más porque son los defectos más visibles.
PESOS = {
    "brillo":     0.25,
    "contraste":  0.20,
    "nitidez":    0.25,
    "ruido":      0.15,
    "saturacion": 0.15,
}