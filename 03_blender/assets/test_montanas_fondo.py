"""test_montanas_fondo.py — test headless de la cordillera de fondo (5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python este_archivo

Carga montanas_fondo por ruta, construye la cordillera de 5 picos en escena
vacía, añade suelo cálido de test, encuadra cámara panorámica desde +Y a
CONTRALUZ SUAVE (sol detrás de la muralla + relleno de cielo) y renderiza
previews/montanas_fondo.png (EEVEE, 960x720). Guarda
blend/montanas_fondo.blend. Presupuesto <= 9000 tris por pico.
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PNG = os.path.join(BASE, "previews", "montanas_fondo.png")
BLEND = os.path.join(BASE, "blend", "montanas_fondo.blend")
BUDGET_PICO = 9000


def main():
    scene = bpy.context.scene

    # --- escena vacía ---
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    # --- cargar módulo por ruta ---
    spec = importlib.util.spec_from_file_location(
        "montanas_fondo", os.path.join(BASE, "montanas_fondo.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    coll = bpy.data.collections.new("ASSET_montanas")
    scene.collection.children.link(coll)
    root = mod.build_cordillera(coll, largo=900.0, n_picos=5, seed=0)
    print("build_cordillera() ->", root.name)

    # --- presupuesto de tris (por pico) ---
    total = 0
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        tris = len(obj.data.loop_triangles)
        total += tris
        print("  tris %-18s %6d" % (obj.name, tris))
        if tris > BUDGET_PICO:
            raise RuntimeError(
                "Pico %s excede presupuesto (%d > %d)" %
                (obj.name, tris, BUDGET_PICO))
    print("  tris TOTAL             %6d" % total)

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

    # --- suelo cálido de test (campiña seca) ---
    gmat = bpy.data.materials.new("MAT_TEST_suelo")
    gmat.use_nodes = True
    bsdf = gmat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.24, 0.23, 0.08, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    gmesh = bpy.data.meshes.new("TEST_suelo")
    s = max(dims.x, dims.y) * 4.0
    gmesh.from_pydata(
        [(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    gmesh.update()
    gmesh.materials.append(gmat)
    gobj = bpy.data.objects.new("TEST_suelo", gmesh)
    scene.collection.objects.link(gobj)
    gobj.location = (centro.x, centro.y, -0.05)

    # --- cámara panorámica desde +Y (frente del telón) ---
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.lens = 35.0
    cam_data.clip_end = 6000.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    objetivo = Vector((centro.x, centro.y, dims.z * 0.42))
    direccion = Vector((0.08, 1.0, 0.06)).normalized()
    dist = (dims.x * 0.5) / math.tan(cam_data.angle / 2.0) * 1.04
    cam.location = objetivo + direccion * dist
    cam.rotation_euler = (objetivo - cam.location).to_track_quat(
        "-Z", "Y").to_euler()

    # --- CONTRALUZ SUAVE: sol cálido detrás de la muralla (-Y -> +Y) ---
    sun_data = bpy.data.lights.new("TEST_sol", "SUN")
    sun_data.energy = 3.2
    sun_data.color = (1.0, 0.86, 0.70)
    sun_data.angle = math.radians(4.0)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    # -Z del sol apunta hacia (+Y, abajo): la luz viene de detras de los picos
    sun.rotation_euler = (math.radians(65), 0.0, math.radians(12))

    # relleno frontal frío tenue para que las caras en sombra respiren
    fill_data = bpy.data.lights.new("TEST_relleno", "SUN")
    fill_data.energy = 0.9
    fill_data.color = (0.96, 0.89, 0.78)
    fill_data.angle = math.radians(6.0)
    fill = bpy.data.objects.new("TEST_relleno", fill_data)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(52), 0.0, math.radians(180))

    world = bpy.data.worlds.new("TEST_cielo")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.44, 0.64, 0.97, 1.0)
    bg.inputs[1].default_value = 0.42
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
