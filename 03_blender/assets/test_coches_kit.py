"""test_coches_kit.py — Test headless del kit de coches-espectador (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python
  "E:\\Escritorio\\claude-pc\\arnau-aseto-corsa\\03_blender\\assets\\test_coches_kit.py"

Renderiza previews/coches_kit.png (EEVEE 960x720) y guarda
blend/coches_kit.blend.
"""

import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(BASE, "coches_kit.py")

# --- escena vacía -----------------------------------------------------------
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ma in list(bpy.data.materials):
    bpy.data.materials.remove(ma)

# --- cargar módulo por ruta -------------------------------------------------
spec = importlib.util.spec_from_file_location("coches_kit", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["coches_kit"] = mod
spec.loader.exec_module(mod)

scene = bpy.context.scene
coll = bpy.data.collections.new("COCHES_KIT")
scene.collection.children.link(coll)

# fila de muestra (build) al fondo
root = mod.build(coll, seed=1)
print("Raiz:", root.name)

# los tres tipos sueltos en primer plano, para inspección (una expresión cada uno)
c1 = mod.build_coche(coll, tipo="compacto", color=(0.04, 0.22, 0.72), seed=7,
                     expresion="abierto")
c1.location = (-5.2, 5.4, 0.0)
c2 = mod.build_coche(coll, tipo="deportivo", color=(0.80, 0.06, 0.04), seed=8,
                     expresion="sonrisa")
c2.location = (0.0, 5.4, 0.0)
c3 = mod.build_coche(coll, tipo="furgo", color=(0.91, 0.86, 0.70), seed=9,
                     expresion="guino")
c3.location = (5.4, 5.4, 0.0)

# --- estadísticas de polycount ---------------------------------------------
print("== Triangulos por coche (limite 1650 = 1500 coche + 150 cara) ==")
excesos = 0
for ob in coll.objects:
    if ob.type == "MESH":
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        flag = ""
        if tris > 1650:
            flag = "  <-- EXCEDE 1650"
            excesos += 1
        print("  %-24s %5d tris%s" % (ob.name, tris, flag))
if excesos:
    print("AVISO: %d coches exceden el presupuesto" % excesos)

# --- suelo de preview (no forma parte del kit) ------------------------------
suelo_mat = bpy.data.materials.new("MAT_TEST_suelo")
suelo_mat.use_nodes = True
sb = next(n for n in suelo_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
sb.inputs["Base Color"].default_value = (0.52, 0.46, 0.36, 1.0)
sb.inputs["Roughness"].default_value = 1.0
suelo_me = bpy.data.meshes.new("TEST_suelo")
S = 300.0
suelo_me.from_pydata([(-S, -S, -0.02), (S, -S, -0.02), (S, S, -0.02), (-S, S, -0.02)],
                     [], [(0, 1, 2, 3)])
suelo_me.update()
suelo_me.materials.append(suelo_mat)
suelo = bpy.data.objects.new("TEST_suelo", suelo_me)
scene.collection.objects.link(suelo)

# --- cámara -----------------------------------------------------------------
cam_data = bpy.data.cameras.new("CAM_coches")
cam_data.lens = 32.0
cam = bpy.data.objects.new("CAM_coches", cam_data)
scene.collection.objects.link(cam)
cam.location = Vector((9.5, 18.5, 4.2))
target = Vector((0.0, 1.0, 0.8))
d = target - cam.location
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

# --- sol mediterráneo + cielo uniforme --------------------------------------
sun_data = bpy.data.lights.new("SUN_coches", "SUN")
sun_data.energy = 1.3
sun_data.angle = math.radians(2.0)
sun = bpy.data.objects.new("SUN_coches", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(-52.0), 0.0, math.radians(18.0))

world = bpy.data.worlds.new("WORLD_coches")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.30, 0.55, 0.95, 1.0)
bg.inputs[1].default_value = 0.35

# --- render EEVEE 960x720 ---------------------------------------------------
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
print("Engine:", scene.render.engine)
scene.render.resolution_x = 960
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"

prev_dir = os.path.join(BASE, "previews")
os.makedirs(prev_dir, exist_ok=True)
scene.render.filepath = os.path.join(prev_dir, "coches_kit.png")
bpy.ops.render.render(write_still=True)
print("PNG:", scene.render.filepath)

# vista de detalle de los tres tipos (a ras de suelo, 3/4 frontal)
cam.location = Vector((5.5, 13.5, 2.6))
target2 = Vector((0.0, 4.6, 1.0))
d2 = target2 - cam.location
cam.rotation_euler = d2.to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = os.path.join(prev_dir, "coches_kit_detalle.png")
bpy.ops.render.render(write_still=True)
print("PNG:", scene.render.filepath)

blend_dir = os.path.join(BASE, "blend")
os.makedirs(blend_dir, exist_ok=True)
blend_path = os.path.join(blend_dir, "coches_kit.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("BLEND:", blend_path)
print("OK test_coches_kit")
