"""test_edificios_civicos.py — Test headless del kit de edificios civicos.

Ejecutar con:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python
  "E:\\Escritorio\\claude-pc\\arnau-aseto-corsa\\03_blender\\assets\\test_edificios_civicos.py"

Carga el modulo por ruta, construye el kit en una escena vacia, encuadra
camara con sol + cielo uniforme, renderiza el preview PNG (EEVEE, 960x720)
y guarda el .blend. Imprime el recuento de triangulos por pieza.
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
MOD_PATH = os.path.join(BASE, "edificios_civicos.py")
PREVIEW = os.path.join(BASE, "previews", "edificios_civicos.png")
BLEND = os.path.join(BASE, "blend", "edificios_civicos.blend")


def main():
    scene = bpy.context.scene

    # --- escena vacia ---
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    # --- cargar modulo por ruta ---
    spec = importlib.util.spec_from_file_location("edificios_civicos",
                                                  MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    col = bpy.data.collections.new("PORTO_CORSA_civicos")
    scene.collection.children.link(col)
    root = mod.build(col)
    print(f"== BUILD OK: raiz {root.name} ==")

    bpy.context.view_layer.update()

    # --- recuento de triangulos por pieza ---
    dg = bpy.context.evaluated_depsgraph_get()
    totals = {}
    for ob in col.objects:
        if ob.type not in {'MESH', 'FONT'}:
            continue
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        tris = len(me.loop_triangles)
        key = ob.name.split("_")[0]
        totals[key] = totals.get(key, 0) + tris
        print(f"== TRIS {ob.name}: {tris}")
        ob.evaluated_get(dg).to_mesh_clear()
    for key, tris in sorted(totals.items()):
        print(f"== TOTAL {key}: {tris} tris")
        if tris > 10000:
            print(f"== AVISO: {key} supera 10k tris")

    # --- suelo de contexto (solo test) ---
    gmesh = bpy.data.meshes.new("TEST_suelo")
    gmesh.from_pydata([(-400, -400, -0.02), (400, -400, -0.02),
                       (400, 400, -0.02), (-400, 400, -0.02)],
                      [], [(0, 1, 2, 3)])
    gmat = bpy.data.materials.get("MAT_TEST_suelo")
    if gmat is None:
        gmat = bpy.data.materials.new("MAT_TEST_suelo")
        gmat.use_nodes = True
        for node in gmat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs["Base Color"].default_value = (0.30, 0.26, 0.19, 1)
                node.inputs["Roughness"].default_value = 0.9
    gmesh.materials.append(gmat)
    gobj = bpy.data.objects.new("TEST_suelo", gmesh)
    scene.collection.objects.link(gobj)

    # --- sol mediterraneo ---
    sun_data = bpy.data.lights.new("TEST_sol", 'SUN')
    sun_data.energy = 3.4
    sun_data.angle = math.radians(1.5)
    sun_data.color = (1.0, 0.965, 0.89)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(48), math.radians(-12),
                          math.radians(148))

    # --- cielo uniforme ---
    world = bpy.data.worlds.new("TEST_mundo")
    world.use_nodes = True
    bg = None
    for node in world.node_tree.nodes:
        if node.type == 'BACKGROUND':
            bg = node
            break
    if bg is not None:
        bg.inputs[0].default_value = (0.30, 0.56, 0.92, 1.0)
        bg.inputs[1].default_value = 0.85
    scene.world = world

    # --- bounding box del kit ---
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bbmin = Vector((1e9, 1e9, 1e9))
    bbmax = Vector((-1e9, -1e9, -1e9))
    for ob in col.objects:
        if ob.type not in {'MESH', 'FONT'}:
            continue
        eob = ob.evaluated_get(dg)
        for corner in eob.bound_box:
            w = eob.matrix_world @ Vector(corner)
            bbmin = Vector(map(min, bbmin, w))
            bbmax = Vector(map(max, bbmax, w))
    center = (bbmin + bbmax) / 2.0
    span = bbmax - bbmin
    print(f"== BBOX min {tuple(round(v, 1) for v in bbmin)} "
          f"max {tuple(round(v, 1) for v in bbmax)}")

    # --- camara 3/4 desde el frente (+Y) ---
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.lens = 42.0
    cam_data.clip_end = 3000.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    direction = Vector((0.42, 1.0, 0.26)).normalized()
    dist = max(span.x, span.y, span.z * 2.5) * 1.22 + 12.0
    target = Vector((center.x, center.y, center.z * 0.85))
    cam.location = target + direction * dist
    cam.rotation_euler = (target - cam.location).to_track_quat(
        '-Z', 'Y').to_euler()
    scene.camera = cam

    # --- render EEVEE 960x720 ---
    for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    print(f"== ENGINE: {scene.render.engine}")
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    try:
        scene.view_settings.view_transform = 'Standard'
    except TypeError:
        pass

    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    print(f"== RENDER OK: {PREVIEW}")

    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"== BLEND OK: {BLEND}")
    print("== TEST OK ==")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
