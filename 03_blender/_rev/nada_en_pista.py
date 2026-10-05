"""nada_en_pista.py - comprueba que NADA invade la superficie de carrera (asfalto y tierra).

  bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/nada_en_pista.py -- [escena.blend] [geometria.json] [salida.json]

Para cada objeto MESH visible de la escena (incluidos hijos: cipreses de filas, olivos de bancales,
vegetacion de rocas...) toma los vertices de su malla evaluada en mundo y cuenta los que caen sobre la
calzada (distancia al eje < w/2 + 0.3) y a una altura entre z_calzada - 0.3 y z_calzada + 5.5 (lo que
un coche tocaria o veria como obstaculo). Superficies y elementos de la propia pista no cuentan
(PISTA, PIANOS, MARCA_, LINEA_, ARCEN_, ACERA_, BORDILLO_, TERRENO, PIT_LANE, puentes y tableros,
tunel, cierre...). Lo que este por encima de 5.5 m (portico, pasarela, guirnaldas) tampoco.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

RAIZ = r'E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
BLEND = args[0] if len(args) > 0 else os.path.join(RAIZ, '_rev', 'escena_rev.blend')
GEOM = args[1] if len(args) > 1 else os.path.join(RAIZ, '_rev', 'geometria_rev.json')
SALIDA = args[2] if len(args) > 2 else os.path.join(RAIZ, 'renders', 'qa', 'nada_en_pista.json')
bpy.ops.wm.open_mainfile(filepath=BLEND)
G = json.load(open(GEOM, encoding='utf-8'))
S = G['muestras']
N = len(S)
P = np.array([[q['x'], q['y'], q['z']] for q in S])
W = np.array([q['w'] for q in S])
SEC = [q['sec'] for q in S]

PERMITIDOS = ('PISTA', 'PIANOS', 'MARCA', 'LINEA', 'ARCEN', 'ACERA', 'BORDILLO', 'TERRENO', 'PIT_LANE', 'AGUA',
              'VIADUCTO', 'PUENTE', 'TUNEL_', 'MCOCHE', 'CARRERA_portico', 'PIT_pasarela', 'CALLE_guirnalda',
              'GUARDARRAIL', 'MUROC', '1WALL_cierre', 'cierre', 'PENON_puente_roca', 'LOEWS', 'AC_', 'CAP_', 'REV_',
              'CARRERA_parrilla', 'CAMINO_enlace', 'HORIZ_')   # HORIZ_: F1 (7.1) anillo de horizonte a >= 2185 m del centro
lib = bpy.data.collections.get('LIB')
en_lib = set(o.name for o in lib.all_objects) if lib else set()
dg = bpy.context.evaluated_depsgraph_get()

# rejilla de muestras para busqueda rapida
celda = 20.0
rej = {}
for i in range(N):
    rej.setdefault((int(P[i, 0] // celda), int(P[i, 1] // celda)), []).append(i)


def muestras_cerca(x, y):
    kx, ky = int(x // celda), int(y // celda)
    out = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            out += rej.get((kx + dx, ky + dy), [])
    return out


def raiz(o):
    while o.parent is not None:
        o = o.parent
    return o


fallos = []
for o in bpy.context.scene.objects:
    if o.type != 'MESH' or o.name in en_lib or not o.visible_get():
        continue
    if o.name.startswith(PERMITIDOS) or raiz(o).name.startswith(PERMITIDOS):
        continue
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [v.x for v in bb]
    ys = [v.y for v in bb]
    cand = set()
    for x in (min(xs), max(xs), (min(xs) + max(xs)) / 2):
        for y in (min(ys), max(ys), (min(ys) + max(ys)) / 2):
            cand.update(muestras_cerca(x, y))
    if not cand:
        continue
    cand = np.array(sorted(cand))
    oe = o.evaluated_get(dg)
    try:
        me = oe.to_mesh()
    except Exception:
        continue
    n = len(me.vertices)
    if n == 0:
        oe.to_mesh_clear()
        continue
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    oe.to_mesh_clear()
    co = co.reshape(-1, 3)
    M = np.array(o.matrix_world)
    cw = co @ M[:3, :3].T + M[:3, 3]
    if len(cw) > 4000:
        cw = cw[:: len(cw) // 4000 + 1]
    pc = P[cand]
    d = np.sqrt(((cw[:, None, :2] - pc[None, :, :2]) ** 2).sum(-1))
    j = d.argmin(1)
    dmin = d[np.arange(len(cw)), j]
    idx = cand[j]
    dentro = (dmin < W[idx] / 2 + 0.3) & (cw[:, 2] > P[idx, 2] - 0.3) & (cw[:, 2] < P[idx, 2] + 5.5)
    k = int(dentro.sum())
    if k:
        i0 = int(idx[dentro][0])
        fallos.append({'objeto': o.name, 'raiz': raiz(o).name, 'vertices_en_pista': k, 's': i0 * 2,
                       'sec': SEC[i0], 'x': round(float(cw[dentro][0, 0]), 1), 'y': round(float(cw[dentro][0, 1]), 1),
                       'altura_sobre_pista': round(float((cw[dentro][:, 2] - P[idx[dentro], 2]).min()), 2)})
fallos.sort(key=lambda f: -f['vertices_en_pista'])
os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
json.dump({'blend': BLEND, 'n': len(fallos), 'fallos': fallos}, open(SALIDA, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('NADA_EN_PISTA objetos invasores: %d (tierra: %d)' % (len(fallos), sum(1 for f in fallos if f['sec'] == 'dirt')))
for f in fallos[:40]:
    print('  %-34s raiz %-28s s=%-5d %-8s verts=%d h=%.2f (%.0f, %.0f)' % (f['objeto'], f['raiz'], f['s'], f['sec'], f['vertices_en_pista'], f['altura_sobre_pista'], f['x'], f['y']))
