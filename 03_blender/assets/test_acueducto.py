"""Test de acueducto.py — Blender 5.1 headless.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_acueducto.py"

Construye el acueducto (build) mas una variante corta, monta camara + sol +
cielo, renderiza previews/acueducto.png (EEVEE 960x720) y guarda
blend/acueducto.blend.
"""

import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PNG = os.path.join(BASE, "previews", "acueducto.png")
BLEND = os.path.join(BASE, "blend", "acueducto.blend")


def main():
    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    # --- modulo por ruta
    spec = importlib.util.spec_from_file_location(
        "acueducto", os.path.join(BASE, "acueducto.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # --- escena limpia
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    scene = bpy.context.scene

    coll = bpy.data.collections.new("ASSET_acueducto")
    scene.collection.children.link(coll)

    raiz = mod.build(coll)
    corto = mod.build(coll, largo=90.0, alto=26.0, n_arcos=4, seed=3)
    corto.location = (-55.0, 85.0, 0.0)
    corto.rotation_euler = (0.0, 0.0, math.radians(18.0))

    # --- suelo de colina calida (solo preview)
    me = bpy.data.meshes.new("TEST_suelo")
    s = 600.0
    me.from_pydata([(-s, -s, -0.03), (s, -s, -0.03), (s, s, -0.03), (-s, s, -0.03)],
                   [], [(0, 1, 2, 3)])
    me.update()
    m = bpy.data.materials.get("MAT_TEST_suelo")
    if m is None:
        m = bpy.data.materials.new("MAT_TEST_suelo")
        m.use_nodes = True
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                n.inputs['Base Color'].default_value = (0.190, 0.170, 0.055, 1.0)
                n.inputs['Roughness'].default_value = 0.95
    me.materials.append(m)
    suelo = bpy.data.objects.new("TEST_suelo", me)
    scene.collection.objects.link(suelo)

    # --- sol + cielo
    sol_d = bpy.data.lights.new("TEST_sol", type='SUN')
    sol_d.energy = 2.6
    sol_d.color = (1.0, 0.95, 0.86)
    sol_d.angle = math.radians(2.0)
    sol = bpy.data.objects.new("TEST_sol", sol_d)
    sol.rotation_euler = Vector((-0.45, -1.0, -0.85)).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(sol)

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = None
    for n in world.node_tree.nodes:
        if n.type == 'BACKGROUND':
            bg = n
            break
    if bg is not None:
        bg.inputs[0].default_value = (0.40, 0.62, 0.92, 1.0)
        bg.inputs[1].default_value = 1.0

    # --- camara encuadrando bbox
    bpy.context.view_layer.update()
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for ob in coll.all_objects:
        if ob.type != 'MESH':
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    centro = (mins + maxs) / 2.0
    half = (maxs - mins).length / 2.0

    cam_d = bpy.data.cameras.new("TEST_cam")
    cam_d.lens = 42.0
    cam_d.clip_end = 3000.0
    cam = bpy.data.objects.new("TEST_cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    direccion = Vector((0.42, 1.0, 0.24)).normalized()
    fov = 2.0 * math.atan(18.0 / cam_d.lens)
    dist = half / math.tan(fov / 2.0) * 1.02
    cam.location = centro + direccion * dist
    cam.rotation_euler = (centro - cam.location).to_track_quat('-Z', 'Y').to_euler()

    # --- render EEVEE
    ids = {e.identifier
           for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items}
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        if cand in ids:
            scene.render.engine = cand
            break
    if hasattr(scene, 'eevee'):
        try:
            scene.eevee.taa_render_samples = 48
        except AttributeError:
            pass
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = PNG

    # --- polycount
    def tris(root):
        t = 0
        for ob in root.children_recursive:
            if ob.type == 'MESH':
                t += sum(len(p.vertices) - 2 for p in ob.data.polygons)
        return t

    t_main, t_corto = tris(raiz), tris(corto)
    print("TRIS acueducto=%d corto=%d" % (t_main, t_corto))
    assert t_main <= 8000, "acueducto pasa de 8k tris"
    assert t_corto <= 8000, "acueducto corto pasa de 8k tris"

    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("TEST_OK png=%s blend=%s" % (PNG, BLEND))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
