"""render_vistas.py - renderiza una lista de vistas de la escena CONGELADA de revision
(03_blender/_rev/escena_rev.blend, solo lectura: no se guarda nunca).

  bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/render_vistas.py -- vistas.json carpeta_salida [ancho alto]
(SIEMPRE por la cola: como mucho 6 Blender a la vez en el equipo, ~5 GB cada uno; defecto 960x540)

vistas.json = lista de dicts, cada uno con 'nombre' y una de estas formas:
  {"nombre": "x", "loc": [x,y,z], "target": [x,y,z], "lens": 28}
  {"nombre": "x", "s": 812, "modo": "piloto"}               1.4 m sobre el asfalto mirando 80 m adelante
  {"nombre": "x", "s": 812, "modo": "piloto_atras"}         igual mirando hacia atras
  {"nombre": "x", "s": 812, "modo": "dron", "alto": 25}     90 m detras y 'alto' m arriba, mirando adelante
  {"nombre": "x", "s": 812, "modo": "lateral", "lado": 1, "dist": 120, "alto": 40}   desde un lado (+1 izq / -1 der)
  {"nombre": "x", "s": 812, "modo": "cenital", "alto": 260} vista desde arriba (lente 35)
Opcionales: "lens" (defecto 26), "adelante" (piloto, defecto 80).
Convenciones: muestras cada 2 m, n = normal IZQUIERDA de la marcha (lado +1 = izquierda).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
VISTAS = args[0]
OUT = os.path.abspath(args[1])
RES = (int(args[2]), int(args[3])) if len(args) >= 4 else (960, 540)
os.makedirs(OUT, exist_ok=True)
G = json.load(open(os.path.join(AQUI, 'geometria_rev.json'), encoding='utf-8'))
S = G['muestras']; N = G['n']; paso = G['paso_m']; L = G['largo_m']
bpy.ops.wm.open_mainfile(filepath=os.path.join(AQUI, 'escena_rev.blend'))
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100


def fr(s_m):
    return S[int(round((s_m % L) / paso)) % N]


def vista(v):
    lens = float(v.get('lens', 26))
    if 'loc' in v:
        return Vector(v['loc']), Vector(v['target']), lens
    s = float(v['s'])
    modo = v.get('modo', 'piloto')
    if modo in ('piloto', 'piloto_atras'):
        sg = 1.0 if modo == 'piloto' else -1.0
        a, b = fr(s), fr(s + sg * float(v.get('adelante', 80)))
        za = a['z'] + 1.4
        return Vector((a['x'], a['y'], za)), Vector((b['x'], b['y'], b['z'] + 1.2)), lens
    if modo == 'dron':
        a, b = fr(s - 90), fr(s + 110)
        return Vector((a['x'], a['y'], a['z'] + float(v.get('alto', 25)))), Vector((b['x'], b['y'], b['z'] + 3)), lens
    if modo == 'lateral':
        q = fr(s)
        lado = float(v.get('lado', 1)); d = float(v.get('dist', 120)); h = float(v.get('alto', 40))
        return (Vector((q['x'] + q['nx'] * lado * d, q['y'] + q['ny'] * lado * d, q['z'] + h)),
                Vector((q['x'], q['y'], q['z'] + 2)), lens)
    if modo == 'cenital':
        q = fr(s)
        h = float(v.get('alto', 260))
        return Vector((q['x'] + 0.01, q['y'] - h * 0.05, q['z'] + h)), Vector((q['x'], q['y'], q['z'])), float(v.get('lens', 35))
    raise ValueError('modo desconocido %s' % modo)


for v in json.load(open(VISTAS, encoding='utf-8')):
    loc, tgt, lens = vista(v)
    cd = bpy.data.cameras.new('REV_' + v['nombre'])
    cd.lens = lens
    cd.clip_end = 12000
    cam = bpy.data.objects.new('REV_' + v['nombre'], cd)
    cam.location = loc
    cam.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT, v['nombre'] + '.png')
    bpy.ops.render.render(write_still=True)
    print('VISTA', v['nombre'], tuple(round(c, 1) for c in loc), '->', tuple(round(c, 1) for c in tgt))
print('OK vistas')
