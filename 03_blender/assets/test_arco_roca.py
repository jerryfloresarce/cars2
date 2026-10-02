"""test_arco_roca.py — test headless del arco de roca natural (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python este_archivo

Carga arco_roca por ruta, construye el arco en escena vacia, anyade una
CALZADA gris de mentira pasando por debajo (direccion Y) y un terreno ocre,
verifica el galibo (ningun vertice dentro de la caja luz x alto_libre),
encuadra camara 3/4 con sol + cielo uniforme y renderiza
previews/arco_roca.png (EEVEE, 960x720) + una vista a pie de pista
previews/arco_roca_paso.png. Guarda blend/arco_roca.blend.
Presupuesto <= 8000 tris.
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PNG = os.path.join(BASE, "previews", "arco_roca.png")
PNG_PASO = os.path.join(BASE, "previews", "arco_roca_paso.png")
BLEND = os.path.join(BASE, "blend", "arco_roca.blend")
BUDGET = 8000
LUZ, ALTO_LIBRE, GROSOR = 18.0, 9.0, 10.0


def _mat_simple(name, color, rough=0.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*color, 1.0)
    return m


def _quad(scene, name, mat, pts, z):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, y, z) for x, y in pts], [], [(0, 1, 2, 3)])
    me.update()
    me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    return obj


def main():
    scene = bpy.context.scene

    # --- escena vacia ---
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    # --- cargar modulo por ruta ---
    spec = importlib.util.spec_from_file_location(
        "arco_roca", os.path.join(BASE, "arco_roca.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    coll = bpy.data.collections.new("ASSET_arco")
    scene.collection.children.link(coll)
    root = mod.build(coll, luz=LUZ, alto_libre=ALTO_LIBRE, grosor=GROSOR,
                     seed=0)
    print("build() ->", root.name)

    # --- presupuesto de tris ---
    total = 0
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        tris = len(obj.data.loop_triangles)
        total += tris
        print("  tris %-18s %6d" % (obj.name, tris))
    print("  tris TOTAL             %6d  (presupuesto %d)" % (total, BUDGET))
    if total > BUDGET:
        raise RuntimeError("Presupuesto de tris excedido (>%d)" % BUDGET)

    # --- verificacion de galibo: nada dentro de la caja luz x alto_libre ---
    bpy.context.view_layer.update()
    hw, hh = LUZ * 0.5, ALTO_LIBRE
    peor = 1e9
    violaciones = 0
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        mw = obj.matrix_world
        for v in obj.data.vertices:
            w = mw @ v.co
            if 1e-4 < w.z < hh - 1e-4 and abs(w.x) < hw - 1e-4:
                violaciones += 1
            if abs(w.x) < hw:
                peor = min(peor, w.z if w.z > hh * 0.5 else 1e9)
    print("galibo: hueco %g x %g, violaciones=%d, techo min sobre pista=%s"
          % (LUZ, ALTO_LIBRE, violaciones,
             "%.2f" % peor if peor < 1e9 else "n/a"))
    if violaciones:
        raise RuntimeError("GALIBO VIOLADO: %d vertices dentro del hueco"
                           % violaciones)

    # --- bounding box global ---
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

    # --- terreno ocre de test ---
    tmat = _mat_simple("MAT_TEST_terreno", (0.430, 0.345, 0.225), 0.95)
    _quad(scene, "TEST_terreno", tmat,
          [(-200, -200), (200, -200), (200, 200), (-200, 200)], -0.05)

    # --- calzada gris de mentira pasando por debajo (direccion Y) ---
    rmat = _mat_simple("MAT_TEST_calzada", (0.165, 0.165, 0.175), 0.75)
    _quad(scene, "TEST_calzada", rmat,
          [(-5.5, -90), (5.5, -90), (5.5, 90), (-5.5, 90)], 0.02)
    lmat = _mat_simple("MAT_TEST_linea", (0.85, 0.83, 0.78), 0.6)
    for x0 in (-5.2, 5.0):
        _quad(scene, "TEST_linea", lmat,
              [(x0, -90), (x0 + 0.22, -90), (x0 + 0.22, 90), (x0, 90)], 0.03)
    # linea central discontinua
    y = -88.0
    while y < 88.0:
        _quad(scene, "TEST_raya", lmat,
              [(-0.12, y), (0.12, y), (0.12, y + 3.0), (-0.12, y + 3.0)],
              0.03)
        y += 8.0

    # --- camara principal 3/4 desde +Y ---
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.lens = 38.0
    cam_data.clip_end = 2000.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    objetivo = Vector((0.0, 0.0, dims.z * 0.42))
    direccion = Vector((0.72, 1.0, 0.30)).normalized()
    radio = max(dims.x, dims.z) * 0.60
    dist = radio / math.tan(cam_data.angle / 2.0) * 1.12
    cam.location = objetivo + direccion * dist
    cam.rotation_euler = (objetivo - cam.location).to_track_quat(
        "-Z", "Y").to_euler()

    # --- sol mediterraneo + cielo uniforme ---
    sun_data = bpy.data.lights.new("TEST_sol", "SUN")
    sun_data.energy = 3.0
    sun_data.color = (1.0, 0.93, 0.80)
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(-30))

    world = bpy.data.worlds.new("TEST_cielo")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.45, 0.68, 0.95, 1.0)
    bg.inputs[1].default_value = 0.45
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

    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)

    scene.render.filepath = PNG
    bpy.ops.render.render(write_still=True)
    print("PNG:", PNG, os.path.exists(PNG))

    # --- vista a pie de pista: verificar visualmente el paso libre ---
    cam.location = Vector((3.2, 52.0, 2.4))
    objetivo2 = Vector((0.0, 0.0, 5.5))
    cam.rotation_euler = (objetivo2 - cam.location).to_track_quat(
        "-Z", "Y").to_euler()
    cam_data.lens = 30.0
    scene.render.filepath = PNG_PASO
    bpy.ops.render.render(write_still=True)
    print("PNG_PASO:", PNG_PASO, os.path.exists(PNG_PASO))

    print("BLEND:", BLEND, os.path.exists(BLEND))
    print("TEST_OK")


try:
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
