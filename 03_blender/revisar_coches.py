# QA especifico de coches-espectador: CADA coche (hijo de una fila COCHES_)
# debe apoyar las ruedas en el terreno bajo su propia posicion: ni enterrado
# ni flotando aunque la fila este en pendiente. Informa y corrige.
import json

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')

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
