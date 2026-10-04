# QA automatico: detecta objetos FLOTANDO o ENTERRADOS respecto al terreno
# y corrige su altura. Trabaja sobre porto_corsa.blend y lo guarda.
# (v2 inspectores, A-r2-04: los objetos marinos se refieren a la obra del puerto que tienen debajo
# -dique, pantalanes, muelles- y solo al nivel del mar si no hay ninguna; PUERTO_faro exento)
# Ejecutar:
#   blender --background --factory-startup --python revisar_flotantes.py
import json
import os

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(os.environ.get('GEOM', BASE + r'\03_blender\geometria_3d.json'), encoding='utf-8'))

bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')

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

# nombres que no se tocan (infraestructura de la escena o asentados a proposito)
EXENTOS = ('PISTA', 'PIANOS', 'TERRENO', 'AGUA', 'ARCEN', 'PUENTE', 'LINEA', 'CAMINO', 'PPUEBLO', 'PENON_casa_roca', 'VEG_penon', 'ITAL', 'YATE', 'MONT_pena',
           'MARCA', 'MUROC', 'ARCO', 'PIT', 'DIRIGIBLE', 'VIADUCTO',
           'ACUEDUCTO', 'MONTANA', 'ACERA', 'BORDILLO', 'GUIRNALDA', 'RUEDA', 'TUNEL',
           'CALLE_guirnalda', 'SOL', 'CIELO', 'LIB', 'GUARDARRAIL', 'AGUA_fondo', 'MIRADOR', 'CAMARA_heli', 'CAMARA_tierra', 'CAMARA_peana', 'LOEWS',
           # (v2 inspectores, A-r2-04: integrar lo pone A PROPOSITO sobre el morro del dique, a 3.25)
           'PUERTO_faro')
MARINOS = ('yate', 'velero', 'pantalan', 'dique', 'faro', 'puerto')
SOBRE_ROCA = ('penon', 'casino')

# v2 inspectores (A-r2-04): un objeto marino puede estar APOYADO en una obra del puerto (dique,
# pantalanes, muelles): su referencia es la cara de arriba de esa obra bajo su centro, y el nivel
# del mar solo si debajo no hay nada (antes el faro del morro, a 3.25, se bajaba al mar y quedaba
# con 3.25 m metidos en el dique)
PLATAFORMAS = ('PUERTO_dique', 'PUERTO_pantalan', 'CAMINO_muelle', 'PPUEBLO_muelle', 'YATE_pantalan',
               'PENON_puente_muelle')


def _bvh_plataformas():
    from mathutils.bvhtree import BVHTree
    vs, fs, rangos = [], [], []
    for o in bpy.context.scene.collection.all_objects:
        if o.type != 'MESH' or not o.name.startswith(PLATAFORMAS) or any(c.name == 'LIB' for c in o.users_collection):
            continue
        mw = o.matrix_world
        n0, f0 = len(vs), len(fs)
        vs.extend((mw @ v.co)[:] for v in o.data.vertices)
        fs.extend([n0 + i for i in p.vertices] for p in o.data.polygons)
        rangos.append((f0, len(fs), o.name))
    if not fs:
        return None, []
    return BVHTree.FromPolygons(vs, fs), rangos


BVH_PLAT, RANGOS_PLAT = _bvh_plataformas()


def ref_marina(root, zmin):
    """Cota de apoyo de un objeto marino: la primera obra del puerto (que no sea de su propia
    jerarquia) bajo el centro de su caja, desde zmin + 0.5; 0.0 (mar) si no hay ninguna."""
    if BVH_PLAT is None:
        return 0.0
    propios = set(o.name for o in [root] + list(root.children_recursive))
    xs, ys = [], []
    for o in [root] + list(root.children_recursive):
        if o.type == 'MESH':
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                xs.append(w.x)
                ys.append(w.y)
    if not xs:
        return 0.0
    o_ = Vector(((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, zmin + 0.5))
    for _ in range(8):
        loc, _n, idx, _d = BVH_PLAT.ray_cast(o_, Vector((0.0, 0.0, -1.0)), 60.0)
        if loc is None:
            return 0.0
        nombre = next((r[2] for r in RANGOS_PLAT if r[0] <= idx < r[1]), '?')
        if nombre not in propios:
            return max(0.0, float(loc.z))
        o_ = Vector((o_.x, o_.y, loc.z - 0.02))
    return 0.0

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
        ref = ref_marina(ob, zmin)  # obra del puerto bajo su centro, o el nivel del mar (v2, A-r2-04)
        if zmin > ref + 1.0:
            d = zmin - ref
            ob.location.z -= d
            informes.append('MAR flotando %.1fm -> bajado a %.2f: %s' % (d, ref, ob.name))
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
