# QA: elimina decoracion que invada la calzada o el pit lane (distancia a la
# linea central a RESOLUCION COMPLETA, sin muestreo) y asienta la vegetacion
# que quede visiblemente flotando en laderas. Guarda el blend.
import json
import math

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')

S = G['muestras']
N = G['n']
PIT = G.get('pit_lane') or []

T = G['terreno']
def z_terreno(x, y):
    fx = (x - T['x0']) / T['cell']
    fy = (y - T['y0']) / T['cell']
    i0 = max(0, min(T['nx'] - 2, int(fx)))
    j0 = max(0, min(T['ny'] - 2, int(fy)))
    tx = min(max(fx - i0, 0), 1)
    ty = min(max(fy - j0, 0), 1)
    def zz(i, j):
        return T['z'][j * T['nx'] + i]
    return ((zz(i0, j0) * (1 - tx) + zz(i0 + 1, j0) * tx) * (1 - ty)
            + (zz(i0, j0 + 1) * (1 - tx) + zz(i0 + 1, j0 + 1) * tx) * ty)

# celdas espaciales para consultar distancia a la pista rapido
CELDA = 40.0
grid = {}
for i in range(N):
    p = S[i]
    k = (int(p['x'] // CELDA), int(p['y'] // CELDA))
    grid.setdefault(k, []).append(i)

def dist_a_pista(x, y):
    kx, ky = int(x // CELDA), int(y // CELDA)
    best = 1e9
    idx = -1
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for i in grid.get((kx + dx, ky + dy), ()):
                d2 = (x - S[i]['x'])**2 + (y - S[i]['y'])**2
                if d2 < best:
                    best = d2
                    idx = i
    if idx < 0:  # lejos de toda celda: seguro
        return 1e9, 12.0
    return math.sqrt(best), S[idx]['w']

def dist_a_pit(x, y):
    if not PIT:
        return 1e9
    return min(math.hypot(x - q['x'], y - q['y']) for q in PIT[::2])

# prefijos de decoracion que NO puede pisar la calzada (margen extra en m)
REGLAS = [('VEG_', 2.0), ('OLI_', 2.0), ('CASAS_', 2.5), ('COCHE_', 1.5), ('CAMARA_tierra', 1.5), ('CAMARA_peana', 1.5),
          ('PENON', 4.0), ('MONTANA', 4.0), ('ACUEDUCTO', -3.0)]
# (ACUEDUCTO margen negativo: puede acercarse, sus arcos salvan la via)

borrados = []
asentados = 0
for ob in list(bpy.context.scene.collection.objects):
    try:
        if ob.parent is not None:
            continue
    except ReferenceError:
        continue
    nombre = ob.name
    regla = next((m for pref, m in REGLAS if nombre.startswith(pref)), None)
    if regla is None or nombre.startswith('VEG_penon'):   # (los arboles de las rocas-pueblo van en sus repisas)
        continue
    if any(c.name == 'LIB' for c in ob.users_collection):
        continue
    x, y = ob.location.x, ob.location.y
    d, w_cerca = dist_a_pista(x, y)
    limite = w_cerca / 2 + regla
    # radio aproximado del objeto (XY) para objetos grandes
    rad = 0.0
    for hijo in [ob] + ob.children_recursive:
        if hijo.type != 'MESH':
            continue
        for c in hijo.bound_box:
            wpt = hijo.matrix_world @ Vector(c)
            rad = max(rad, math.hypot(wpt.x - x, wpt.y - y))
    rad = min(rad, 90.0)  # las cordilleras no cuentan entero
    if nombre.startswith('COCHE_'):
        # una fila de coches es una banda estrecha PARALELA a la pista: lo que
        # cuenta es medio coche (2.6 m), no el radio de la fila entera (14 m)
        rad = 2.6
    if d < limite + min(rad, 8.0) or dist_a_pit(x, y) < 5.5 + min(rad, 8.0):
        for ch in list(ob.children_recursive):
            bpy.data.objects.remove(ch, do_unlink=True)
        bpy.data.objects.remove(ob, do_unlink=True)
        borrados.append(nombre)
        continue
    # vegetacion flotante en ladera: asienta la base al terreno
    if nombre.startswith(('VEG_', 'OLI_')):
        zmin = 1e9
        for hijo in [ob] + ob.children_recursive:
            if hijo.type != 'MESH':
                continue
            for c in hijo.bound_box:
                zmin = min(zmin, (hijo.matrix_world @ Vector(c)).z)
        terr = z_terreno(x, y)
        if zmin > terr + 0.45:
            ob.location.z -= (zmin - (terr - 0.3))
            asentados += 1

print('INVASORES BORRADOS: %d | vegetacion asentada: %d' % (len(borrados), asentados))
for b in borrados[:25]:
    print(' -', b)
bpy.ops.wm.save_as_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
print('blend guardado')
