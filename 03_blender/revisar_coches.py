# QA especifico de coches-espectador: CADA coche (hijo de una fila COCHES_)
# debe apoyar las ruedas en el terreno bajo su propia posicion: ni enterrado
# ni flotando aunque la fila este en pendiente. Informa y corrige.
import json
import os

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(os.environ.get('GEOM', BASE + r'\03_blender\geometria_3d.json'), encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')

T = G['terreno']
_ter_m = bpy.data.objects.get('TERRENO')   # ronda 15: cota real = malla (explanadas del integrador)
# F1 r4 (PARCHES_F1_mascara.md R4.4 A9): '>=' y solo los nx*ny primeros: tras banda_terreno_2m.py (ultimo paso del pipeline)
# el TERRENO lleva +45 k vertices de la banda de 2 m AL FINAL; la rejilla conserva sus indices j*nx+i
if _ter_m is not None and _ter_m.type == 'MESH' and len(_ter_m.data.vertices) >= T['nx'] * T['ny']:
    _co = [0.0] * (3 * len(_ter_m.data.vertices))
    _ter_m.data.vertices.foreach_get('co', _co)
    T = dict(T)
    T['z'] = _co[2::3][:T['nx'] * T['ny']]
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

def bbox_world(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (min(p.x for p in pts), max(p.x for p in pts),
            min(p.y for p in pts), max(p.y for p in pts),
            min(p.z for p in pts))

corregidos = 0
borrados = 0
for raiz in list(bpy.context.scene.collection.objects):
    try:
        if raiz.parent is not None or not raiz.name.startswith('COCHE_'):
            continue
    except ReferenceError:
        continue
    if any(c.name == 'LIB' for c in raiz.users_collection):
        continue
    coches = [h for h in raiz.children_recursive if h.type == 'MESH']
    if not coches and raiz.type == 'MESH':
        coches = [raiz]
    for coche in coches:
        x0, x1, y0, y1, zmin = bbox_world(coche)
        cxw, cyw = (x0 + x1) / 2, (y0 + y1) / 2
        # terreno bajo las cuatro esquinas: la mas alta manda (nada enterrado)
        terr = max(z_terreno(cxw, cyw), z_terreno(x0, y0), z_terreno(x1, y0),
                   z_terreno(x0, y1), z_terreno(x1, y1))
        dz = zmin - terr
        if dz < -0.15 or dz > 0.25:
            # pendiente excesiva bajo el coche: mejor quitarlo que dejarlo colgando
            pend = max(z_terreno(x0, y0), z_terreno(x1, y0), z_terreno(x0, y1),
                       z_terreno(x1, y1)) - min(z_terreno(x0, y0), z_terreno(x1, y0),
                                               z_terreno(x0, y1), z_terreno(x1, y1))
            if pend > 1.6:
                bpy.data.objects.remove(coche, do_unlink=True)
                borrados += 1
                continue
            coche.location.z -= (zmin - (terr + 0.03))
            corregidos += 1

print('COCHES asentados: %d | en pendiente imposible (borrados): %d' % (corregidos, borrados))
if corregidos or borrados:
    bpy.ops.wm.save_as_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
    print('blend guardado')
else:
    print('todos los coches bien apoyados')
