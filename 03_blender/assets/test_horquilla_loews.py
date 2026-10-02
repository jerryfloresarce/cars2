"""test_horquilla_loews.py — Test headless de la rotonda Loews (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python
  "E:\\Escritorio\\claude-pc\\arnau-aseto-corsa\\03_blender\\assets\\test_horquilla_loews.py"

Renderiza (EEVEE 960x720):
  previews/horquilla_loews.png          vista a ~30 grados (efecto rueda)
  previews/horquilla_loews_cenital.png  vista cenital ortografica
y guarda blend/horquilla_loews.blend.
"""

import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(BASE, "horquilla_loews.py")

# --- escena vacia -----------------------------------------------------------
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ma in list(bpy.data.materials):
    bpy.data.materials.remove(ma)

# --- cargar modulo por ruta -------------------------------------------------
spec = importlib.util.spec_from_file_location("horquilla_loews", MOD_PATH)
horq = importlib.util.module_from_spec(spec)
sys.modules["horquilla_loews"] = horq
spec.loader.exec_module(horq)

scene = bpy.context.scene
coll = bpy.data.collections.new("LOEWS")
scene.collection.children.link(coll)
root = horq.build(coll, radio=9.0, seed=1)
print("Raiz:", root.name)

# --- polycount (limite 6000 tris) -------------------------------------------
total = 0
for ob in coll.objects:
    if ob.type == "MESH":
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        total += tris
        print("  %-24s %5d tris" % (ob.name, tris))
print("TOTAL: %d tris (limite 6000)%s" % (total, "  <-- EXCEDE" if total > 6000 else ""))

# --- suelo de preview: asfalto de la horquilla (no es parte del asset) ------
suelo_mat = bpy.data.materials.new("MAT_TEST_asfalto")
suelo_mat.use_nodes = True
sb = next(n for n in suelo_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
sb.inputs["Base Color"].default_value = (0.24, 0.24, 0.25, 1.0)
sb.inputs["Roughness"].default_value = 1.0
suelo_me = bpy.data.meshes.new("TEST_asfalto")
S = 120.0
suelo_me.from_pydata([(-S, -S, -0.02), (S, -S, -0.02), (S, S, -0.02), (-S, S, -0.02)],
                     [], [(0, 1, 2, 3)])
suelo_me.update()
suelo_me.materials.append(suelo_mat)
suelo = bpy.data.objects.new("TEST_asfalto", suelo_me)
scene.collection.objects.link(suelo)

# --- camaras ----------------------------------------------------------------
# vista a ~30 grados de elevacion
cam30_data = bpy.data.cameras.new("CAM_30")
cam30_data.lens = 35.0
cam30 = bpy.data.objects.new("CAM_30", cam30_data)
scene.collection.objects.link(cam30)
target = Vector((0.0, 0.0, 3.2))
dist = 30.0
elev = math.radians(30.0)
az = math.radians(-70.0)
cam30.location = Vector((dist * math.cos(elev) * math.cos(az),
                         dist * math.cos(elev) * math.sin(az),
                         target.z + dist * math.sin(elev)))
d = target - cam30.location
cam30.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

# vista cenital ortografica
camtop_data = bpy.data.cameras.new("CAM_top")
camtop_data.type = "ORTHO"
camtop_data.ortho_scale = 24.0
camtop = bpy.data.objects.new("CAM_top", camtop_data)
scene.collection.objects.link(camtop)
camtop.location = Vector((0.0, 0.0, 45.0))
camtop.rotation_euler = (0.0, 0.0, 0.0)  # mira -Z

# --- sol mediterraneo + cielo uniforme --------------------------------------
sun_data = bpy.data.lights.new("SUN_loews", "SUN")
sun_data.energy = 2.8
sun_data.angle = math.radians(2.0)
sun = bpy.data.objects.new("SUN_loews", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(-52.0), 0.0, math.radians(40.0))

world = bpy.data.worlds.new("WORLD_loews")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.42, 0.65, 0.98, 1.0)
bg.inputs[1].default_value = 0.65

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

scene.camera = cam30
scene.render.filepath = os.path.join(prev_dir, "horquilla_loews.png")
bpy.ops.render.render(write_still=True)
print("PNG:", scene.render.filepath)

scene.camera = camtop
scene.render.filepath = os.path.join(prev_dir, "horquilla_loews_cenital.png")
bpy.ops.render.render(write_still=True)
print("PNG:", scene.render.filepath)

blend_dir = os.path.join(BASE, "blend")
os.makedirs(blend_dir, exist_ok=True)
blend_path = os.path.join(blend_dir, "horquilla_loews.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("BLEND:", blend_path)
print("OK test_horquilla_loews")
