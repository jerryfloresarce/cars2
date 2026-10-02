"""Test de viaducto_curvo.py — Blender 5.1 headless.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_viaducto_curvo.py"

Genera una curva en S de 150 m con z variable, llama a build_desde_puntos
sobre un plano de agua, comprueba el presupuesto (<=1500 tris / 30 m) y
renderiza dos vistas EEVEE 960x720:
  previews/viaducto_curvo.png       (3/4)
  previews/viaducto_curvo_lado.png  (de lado)
Guarda blend/viaducto_curvo.blend.
"""

import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PNG_34 = os.path.join(BASE, "previews", "viaducto_curvo.png")
PNG_LADO = os.path.join(BASE, "previews", "viaducto_curvo_lado.png")
BLEND = os.path.join(BASE, "blend", "viaducto_curvo.blend")


def main():
    os.makedirs(os.path.dirname(PNG_34), exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    spec = importlib.util.spec_from_file_location(
        "viaducto_curvo", os.path.join(BASE, "viaducto_curvo.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    scene = bpy.context.scene

    coll = bpy.data.collections.new("ASSET_viaducto_curvo")
    scene.collection.children.link(coll)

    # --- curva en S de 150 m con z variable (10.8 a 14.2 m sobre el agua)
    puntos = []
    n = 21
    largo = 150.0
    for i in range(n):
        t = i / (n - 1)
        x = -largo / 2.0 + largo * t
        y = 15.0 * math.sin(t * math.pi * 1.5)
        z = 10.8 + 3.4 * math.sin(t * math.pi)
        puntos.append((x, y, z))

    raiz = mod.build_desde_puntos(coll, puntos, ancho=13.0, nivel_agua=0.0)

    # longitud en planta (aprox por cuerdas, para el presupuesto)
    L = 0.0
    for a, b in zip(puntos, puntos[1:]):
        L += math.hypot(b[0] - a[0], b[1] - a[1])

    # --- mar turquesa (solo preview)
    me = bpy.data.meshes.new("TEST_mar")
    s = 600.0
    me.from_pydata([(-s, -s, -0.03), (s, -s, -0.03),
                    (s, s, -0.03), (-s, s, -0.03)], [], [(0, 1, 2, 3)])
    me.update()
    m = bpy.data.materials.get("MAT_TEST_mar")
    if m is None:
        m = bpy.data.materials.new("MAT_TEST_mar")
        m.use_nodes = True
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Base Color'].default_value = (0.008, 0.30, 0.32, 1.0)
                nd.inputs['Roughness'].default_value = 0.10
    me.materials.append(m)
    mar = bpy.data.objects.new("TEST_mar", me)
    scene.collection.objects.link(mar)

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
    for nd in world.node_tree.nodes:
        if nd.type == 'BACKGROUND':
            nd.inputs[0].default_value = (0.40, 0.62, 0.92, 1.0)
            nd.inputs[1].default_value = 1.0
            break

    # --- bbox del asset
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
    centro.z = max(centro.z, 4.0)
    half = (maxs - mins).length / 2.0

    cam_d = bpy.data.cameras.new("TEST_cam")
    cam_d.lens = 42.0
    cam_d.clip_end = 3000.0
    cam = bpy.data.objects.new("TEST_cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    fov = 2.0 * math.atan(18.0 / cam_d.lens)

    def encuadra(direccion, margen):
        d = direccion.normalized()
        dist = half / math.tan(fov / 2.0) * margen
        cam.location = centro + d * dist
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

    # --- presupuesto: <= 1500 tris por cada 30 m
    tris = 0
    for ob in raiz.children_recursive:
        if ob.type == 'MESH':
            tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    por30 = tris / (L / 30.0)
    print("TRIS total=%d  L=%.1f m  tris/30m=%.0f" % (tris, L, por30))
    assert por30 <= 1500, "viaducto pasa de 1500 tris por 30 m (%.0f)" % por30

    encuadra(Vector((0.55, 0.78, 0.30)), 0.92)
    scene.render.filepath = PNG_34
    bpy.ops.render.render(write_still=True)

    encuadra(Vector((0.10, 1.0, 0.13)), 0.80)
    scene.render.filepath = PNG_LADO
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("TEST_OK png=%s | %s blend=%s" % (PNG_34, PNG_LADO, BLEND))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
