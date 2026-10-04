# QA: elimina decoracion que invada la calzada o el pit lane (distancia a la
# linea central a RESOLUCION COMPLETA, sin muestreo) y asienta la vegetacion
# que quede visiblemente flotando en laderas. Guarda el blend.
import json
import os
import math

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(os.environ.get('GEOM', BASE + r'\03_blender\geometria_3d.json'), encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')

S = G['muestras']
N = G['n']
PIT = G.get('pit_lane') or []

T = G['terreno']
_ter_m = bpy.data.objects.get('TERRENO')   # ronda 15: cota real = malla (explanadas del integrador)
if _ter_m is not None and _ter_m.type == 'MESH' and len(_ter_m.data.vertices) == T['nx'] * T['ny']:
    _co = [0.0] * (3 * len(_ter_m.data.vertices))
    _ter_m.data.vertices.foreach_get('co', _co)
    T = dict(T)
    T['z'] = _co[2::3]
def z_terreno(x, y):
    fx = (x - T['x0']) / T['cell']
    fy = (y - T['y0']) / T['cell']
    i0 = max(0, min(T['nx'] - 2, int(fx)))
    j0 = max(0, min(T['ny'] - 2, int(fy)))
    tx = min(max(fx - i0, 0), 1)
    ty = min(max(fy - j0, 0), 1)
    def zz(i, j):
        return T['z'][j * T['nx'] + i]
    # (v1 inspectores: la cota que SE VE. El render y el exportador -loop_triangles- parten cada
    # quad (a, a+1, a+nx+1, a+nx) del TERRENO por la diagonal a -> a+nx+1; la bilineal se
    # separaba de esa superficie en los quads no planos de las laderas)
    z00, z10, z01, z11 = zz(i0, j0), zz(i0 + 1, j0), zz(i0, j0 + 1), zz(i0 + 1, j0 + 1)
    if tx >= ty:
        return z00 + (z10 - z00) * tx + (z11 - z10) * ty
    return z00 + (z01 - z00) * ty + (z11 - z01) * tx

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

def huella_puntos(ob, paso=2.0):
    """Puntos (x, y) de la HUELLA real: contorno inferior de la caja de cada malla
    (en su orientacion) muestreado cada `paso` m, mas el centro."""
    pts = []
    for hijo in [ob] + ob.children_recursive:
        if hijo.type != 'MESH':
            continue
        bb = [hijo.matrix_world @ Vector(c) for c in hijo.bound_box]
        esq = [bb[0], bb[3], bb[7], bb[4]]          # cara z minima (orden de bound_box)
        for k in range(4):
            a, b = esq[k], esq[(k + 1) % 4]
            l_ = math.hypot(b.x - a.x, b.y - a.y)
            n_ = max(1, int(l_ / paso))
            for j in range(n_):
                f = j / float(n_)
                pts.append((a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f))
        pts.append((sum(p.x for p in esq) / 4.0, sum(p.y for p in esq) / 4.0))
    return pts

# RONDA 15: las rocas construidas en coordenadas de mundo (raiz en el origen) y que por
# diseno TOCAN la pista (roca del lazo, penon del casino) traen sus propias comprobaciones
EXCLUIR = ('VEG_penon', 'PENON_puente', 'PENON_cara')

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
    if regla is None or nombre.startswith(EXCLUIR):   # (los arboles de las rocas-pueblo van en sus repisas)
        continue
    if any(c.name == 'LIB' for c in ob.users_collection):
        continue
    if nombre.startswith('CASAS_'):
        # RONDA 15: casas del plan urbano con la fachada a 7 m del asfalto: se mide la
        # HUELLA (no el pivote + radio, que borraba toda la primera terraza)
        pts_h = huella_puntos(ob)
        d_h = min((dist_a_pista(px, py)[0] - dist_a_pista(px, py)[1] / 2.0) for (px, py) in pts_h) if pts_h else 1e9
        d_p = min(dist_a_pit(px, py) for (px, py) in pts_h[::3]) if (pts_h and PIT) else 1e9
        if d_h < regla or d_p < 5.5:
            for ch in list(ob.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(ob, do_unlink=True)
            borrados.append('%s (huella a %.1f m del asfalto, %.1f del pit)' % (nombre, d_h, d_p))
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
for b in borrados:
    print(' -', b)
bpy.ops.wm.save_as_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
print('blend guardado')
