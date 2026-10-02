# Elimina decoracion que haya quedado bajo el nivel del mar (colocaciones
# invalidas junto a tramos de puente). Guarda el blend.
import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')

PREFIJOS = ('VEG_', 'CASAS_', 'CARRERA_paca', 'CARRERA_muro', 'CARRERA_valla')
EXENTOS_QA = ('acantilado', 'roca')  # los acantilados y rocas costeras nacen bajo el mar

def bbox_z(root):
    zmin, zmax = 1e9, -1e9
    for ob in [root] + root.children_recursive:
        if ob.type != 'MESH':
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            zmin = min(zmin, w.z)
            zmax = max(zmax, w.z)
    return zmin, zmax

borrados = []
for ob in list(bpy.context.scene.collection.objects):
    try:
        if ob.parent is not None:
            continue
    except ReferenceError:
        continue  # ya borrado como hijo de un root anterior
    if not any(ob.name.startswith(p) for p in PREFIJOS) or ob.name.startswith('VEG_penon'):
        continue
    if any(k in ob.name.lower() for k in EXENTOS_QA):
        continue
    if any(col.name == 'LIB' for col in ob.users_collection):
        continue
    zmin, zmax = bbox_z(ob)
    if zmin > 1e8:
        continue
    if zmax < 0.9 or zmin < -1.0:  # sumergido o con la base bajo el mar
        borrados.append(ob.name)
        for ch in list(ob.children_recursive):
            bpy.data.objects.remove(ch, do_unlink=True)
        bpy.data.objects.remove(ob, do_unlink=True)

print('SUMERGIDOS BORRADOS:', len(borrados))
for b in borrados:
    print(' -', b)
bpy.ops.wm.save_as_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
print('blend guardado')
