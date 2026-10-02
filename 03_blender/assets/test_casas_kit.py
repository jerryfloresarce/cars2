"""test_casas_kit.py — test headless del kit de manzanas (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python este_archivo

Carga casas_kit por ruta, construye la manzana en escena vacía, encuadra
cámara con sol + cielo uniforme y renderiza previews/casas_kit.png (EEVEE,
960x720). Guarda blend/casas_kit.blend. Imprime tris por casa (presupuesto
<= 4000 por casa).
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PNG = os.path.join(BASE, "previews", "casas_kit.png")
BLEND = os.path.join(BASE, "blend", "casas_kit.blend")


def main():
    scene = bpy.context.scene

    # --- escena vacía ---
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    # --- cargar módulo por ruta ---
    spec = importlib.util.spec_from_file_location(
        "casas_kit", os.path.join(BASE, "casas_kit.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    coll = bpy.data.collections.new("ASSET_casas")
    scene.collection.children.link(coll)
    root = mod.build(coll, seed=7)
    print("build() ->", root.name)

    # --- presupuesto de tris ---
    ok_budget = True
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        tris = len(obj.data.loop_triangles)
        flag = "OK" if tris <= 4000 else "EXCEDIDO"
        if tris > 4000:
            ok_budget = False
        print("  tris %-12s %5d  %s" % (obj.name, tris, flag))
    if not ok_budget:
        raise RuntimeError("Presupuesto de tris excedido (>4000 por casa)")

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

    # --- suelo de test ---
    gmat = bpy.data.materials.new("MAT_TEST_suelo")
    gmat.use_nodes = True
    bsdf = gmat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.55, 0.52, 0.47, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    gmesh = bpy.data.meshes.new("TEST_suelo")
    s = max(dims.x, dims.y) * 3.0
    gmesh.from_pydata(
        [(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    gmesh.update()
    gmesh.materials.append(gmat)
    gobj = bpy.data.objects.new("TEST_suelo", gmesh)
    scene.collection.objects.link(gobj)
    gobj.location = (centro.x, centro.y, -0.01)

    # --- cámara 3/4 desde el lado de la fachada (+Y) ---
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.lens = 42.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    objetivo = Vector((centro.x, centro.y, centro.z * 0.9))
    direccion = Vector((0.55, 1.0, 0.42)).normalized()
    radio = max(dims.x, dims.y, dims.z) * 0.56
    dist = radio / math.tan(cam_data.angle / 2.0) * 1.03
    cam.location = objetivo + direccion * dist
    cam.rotation_euler = (objetivo - cam.location).to_track_quat(
        "-Z", "Y").to_euler()

    # --- sol mediterráneo + cielo uniforme ---
    sun_data = bpy.data.lights.new("TEST_sol", "SUN")
    sun_data.energy = 2.4
    sun_data.color = (1.0, 0.96, 0.88)
    sun_data.angle = math.radians(1.5)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(28))

    world = bpy.data.worlds.new("TEST_cielo")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.45, 0.68, 0.95, 1.0)
    bg.inputs[1].default_value = 0.85
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
    scene.render.filepath = PNG

    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    bpy.ops.render.render(write_still=True)
    print("PNG:", PNG, os.path.exists(PNG))
    print("BLEND:", BLEND, os.path.exists(BLEND))
    print("TEST_OK")


try:
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
