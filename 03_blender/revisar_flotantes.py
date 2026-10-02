# QA automatico: detecta objetos FLOTANDO o ENTERRADOS respecto al terreno
# y corrige su altura. Trabaja sobre porto_corsa.blend y lo guarda.
# Ejecutar:
#   blender --background --factory-startup --python revisar_flotantes.py
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

# nombres que no se tocan (infraestructura de la escena o asentados a proposito)
EXENTOS = ('PISTA', 'PIANOS', 'TERRENO', 'AGUA', 'ARCEN', 'PUENTE', 'LINEA', 'CAMINO', 'PPUEBLO', 'PENON_casa_roca', 'VEG_penon', 'ITAL', 'YATE', 'MONT_pena',
           'MARCA', 'MUROC', 'ARCO', 'PIT', 'DIRIGIBLE', 'VIADUCTO',
           'ACUEDUCTO', 'MONTANA', 'ACERA', 'BORDILLO', 'GUIRNALDA', 'RUEDA', 'TUNEL',
           'CALLE_guirnalda', 'SOL', 'CIELO', 'LIB', 'GUARDARRAIL', 'AGUA_fondo', 'MIRADOR', 'CAMARA_heli', 'CAMARA_tierra', 'CAMARA_peana', 'LOEWS')
MARINOS = ('yate', 'velero', 'pantalan', 'dique', 'faro', 'puerto')
SOBRE_ROCA = ('penon', 'casino')

def es(nombre, claves):
    n = nombre.lower()
    return any(k.lower() in n for k in claves)

def bbox_hierarquia(root):
    zmin, zmax = 1e9, -1e9
    for ob in [root] + root.children_recursive:
        if ob.type != 'MESH':
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            zmin = min(zmin, w.z)
            zmax = max(zmax, w.z)
    return zmin, zmax

informes = []
arreglados = 0
for ob in list(bpy.context.scene.collection.objects):
    if ob.parent is not None or ob.type not in ('MESH', 'EMPTY'):
        continue
    if es(ob.name, EXENTOS) or ob.type == 'CAMERA':
        continue
    # ignora lo que cuelga de la biblioteca oculta
    if any(col.name == 'LIB' for col in ob.users_collection):
        continue
    zmin, zmax = bbox_hierarquia(ob)
    if zmin > 1e8:
        continue
    x, y = ob.location.x, ob.location.y
    if es(ob.name, SOBRE_ROCA) or es(ob.name, ('acantilado', 'roca')):
        continue
    if es(ob.name, MARINOS) and 'farola' not in ob.name.lower():
        ref = 0.0  # nivel del mar
        if zmin > ref + 1.0:
            d = zmin - ref
            ob.location.z -= d
            informes.append('MAR flotando %.1fm -> bajado: %s' % (d, ob.name))
            arreglados += 1
        continue
    terr = z_terreno(x, y)
    if zmin > terr + 1.2:
        d = zmin - (terr - 0.2)
        ob.location.z -= d
        informes.append('FLOTANDO %.1fm -> bajado: %s (en %.0f,%.0f)' % (zmin - terr, ob.name, x, y))
        arreglados += 1
    elif zmax < terr - 0.5:
        d = (terr - 0.3) - zmin
        ob.location.z += d
        informes.append('ENTERRADO -> subido: %s (en %.0f,%.0f)' % (ob.name, x, y))
        arreglados += 1

print('==== INFORME QA (%d objetos corregidos) ====' % arreglados)
for i in informes:
    print(' -', i)
if arreglados:
    bpy.ops.wm.save_as_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
    print('blend guardado con correcciones')
else:
    print('escena limpia, sin cambios')
