from utilidades import leer_imagen_pil
from evaluador import Evaluador

img = leer_imagen_pil('img_input/navidad.jpg')

ev = Evaluador()
r = ev.evaluar(img)

print(r['score'], r['clasificacion'])
print(r['problemas'])
print(r['metricas'])