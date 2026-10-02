"""test_penon_cara.py — test headless del Peñón "cara de coche" (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python este_archivo

Carga penon_cara por ruta, construye el peñón en escena vacía, añade un
"mar" turquesa de test, sol mediterráneo rasante + cielo uniforme y renderiza
DOS vistas EEVEE 960x720:
  previews/penon_cara.png      -> frontal desde el mar (la cara tallada)
  previews/penon_cara_34.png   -> 3/4 (morro + perfil de capó)
Guarda blend/penon_cara.blend. Presupuesto <= 22000 tris en total.
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PNG_F = os.path.join(BASE, "previews", "penon_cara.png")
PNG_34 = os.path.join(BASE, "previews", "penon_cara_34.png")
BLEND = os.path.join(BASE, "blend", "penon_cara.blend")
BUDGET = 22000


def main():
    scene = bpy.context.scene

    # --- escena vacía ---
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    # --- cargar módulo por ruta ---
    spec = importlib.util.spec_from_file_location(
        "penon_cara", os.path.join(BASE, "penon_cara.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    coll = bpy.data.collections.new("ASSET_penon_cara")
    scene.collection.children.link(coll)
    root = mod.build(coll, seed=0)
    print("build() ->", root.name)

    # --- presupuesto de tris ---
    total = 0
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        tris = len(obj.data.loop_triangles)
        total += tris
        print("  tris %-22s %6d" % (obj.name, tris))
    print("  tris TOTAL                 %6d  (presupuesto %d)" % (total, BUDGET))
    if total > BUDGET:
        raise RuntimeError("Presupuesto de tris excedido (>%d)" % BUDGET)

    # --- bounding box global ---
    bpy.context.view_layer.update()
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    centro = (mins + maxs) / 2.0
    dims = maxs - mins
    print("bbox dims:", tuple(round(v, 1) for v in dims))

    # --- "mar" turquesa de test alrededor del peñón ---
    mmat = bpy.data.materials.new("MAT_TEST_mar")
    mmat.use_nodes = True
    bsdf = mmat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.05, 0.42, 0.46, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.15
    mmesh = bpy.data.meshes.new("TEST_mar")
    s = max(dims.x, dims.y) * 4.0
    mmesh.from_pydata(
        [(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    mmesh.update()
    mmesh.materials.append(mmat)
    mobj = bpy.data.objects.new("TEST_mar", mmesh)
    scene.collection.objects.link(mobj)
    mobj.location = (centro.x, centro.y, -0.02)

    # --- cámara ---
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.clip_end = 4000.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    # --- sol mediterráneo rasante desde el mar (ilumina la cara +Y) ---
    sun_data = bpy.data.lights.new("TEST_sol", "SUN")
    sun_data.energy = 2.2
    sun_data.color = (1.0, 0.88, 0.70)
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(-52), 0.0, math.radians(-38))

    world = bpy.data.worlds.new("TEST_cielo")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.45, 0.68, 0.95, 1.0)
    bg.inputs[1].default_value = 0.34
    scene.world = world

    # --- render EEVEE 960x720 ---
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"

    os.makedirs(os.path.dirname(PNG_F), exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    # (png, direccion de camara, lente, radio de encuadre, objetivo)
    shots = [
        (PNG_F, Vector((0.12, 1.0, 0.20)), 45.0,
         max(dims.x, dims.z) * 0.62,
         Vector((centro.x, centro.y + dims.y * 0.14, dims.z * 0.34))),
        (PNG_34, Vector((0.9, 1.0, 0.46)), 40.0,
         max(dims.x, dims.y, dims.z) * 0.58,
         Vector((centro.x, centro.y, centro.z * 0.85))),
    ]
    for png, direccion, lente, radio, objetivo in shots:
        cam_data.lens = lente
        direccion = direccion.normalized()
        dist = radio / math.tan(cam_data.angle / 2.0) * 1.06
        cam.location = objetivo + direccion * dist
        cam.rotation_euler = (objetivo - cam.location).to_track_quat(
            "-Z", "Y").to_euler()
        scene.render.filepath = png
        bpy.ops.render.render(write_still=True)
        print("PNG:", png, os.path.exists(png))

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("BLEND:", BLEND, os.path.exists(BLEND))
    print("TEST_OK")


try:
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
