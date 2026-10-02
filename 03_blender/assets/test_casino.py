# -*- coding: utf-8 -*-
"""Test de casino.py: escena limpia, build(), camara + sol + cielo uniforme,
render EEVEE 960x720 a previews/casino.png y guardado de blend/casino.blend.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_casino.py"
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

ASSETS = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"


def main():
    # --- cargar modulo por ruta
    spec = importlib.util.spec_from_file_location(
        "casino", os.path.join(ASSETS, "casino.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    scene = bpy.context.scene

    # --- escena vacia
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)

    coll = bpy.data.collections.new("PortoCorsa_assets")
    scene.collection.children.link(coll)

    root = mod.build(coll, seed=0)
    assert root is not None and root.name.startswith("CASINO"), \
        "build() debe devolver el objeto raiz"

    # --- polycount
    tris = 0
    for ob in coll.objects:
        if ob.type == 'MESH':
            tris += sum(max(0, len(p.vertices) - 2)
                        for p in ob.data.polygons)
    print("CASINO tris:", tris)
    assert tris <= 25000, "Polycount excedido: %d" % tris

    # --- suelo neutro para sombras
    ground_me = bpy.data.meshes.new("TEST_ground")
    s = 400.0
    ground_me.from_pydata(
        [(-s, -s, -0.02), (s, -s, -0.02), (s, s, -0.02), (-s, s, -0.02)],
        [], [(0, 1, 2, 3)])
    gmat = bpy.data.materials.new("MAT_TEST_ground")
    gmat.use_nodes = True
    b = gmat.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.55, 0.52, 0.46, 1.0)
    b.inputs["Roughness"].default_value = 0.95
    ground_me.materials.append(gmat)
    ground = bpy.data.objects.new("TEST_ground", ground_me)
    scene.collection.objects.link(ground)

    # --- camara (3/4 frontal, fachada mira a +Y)
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.lens = 32.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = Vector((64.0, 103.0, 30.0))
    target = Vector((0.0, -3.0, 13.0))
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam

    # --- sol mediterraneo
    sun_data = bpy.data.lights.new("TEST_sun", 'SUN')
    sun_data.energy = 4.5
    sun_data.color = (1.0, 0.955, 0.87)
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("TEST_sun", sun_data)
    sun.rotation_euler = (math.radians(55.0), 0.0, math.radians(215.0))
    scene.collection.objects.link(sun)

    # --- cielo uniforme
    world = bpy.data.worlds.new("TEST_world")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.36, 0.62, 0.92, 1.0)
    bg.inputs[1].default_value = 0.5
    scene.world = world

    # --- estilo Cars 2 saturado: transformada de vista sin desaturar
    try:
        scene.view_settings.view_transform = 'Standard'
    except TypeError:
        pass

    # --- render EEVEE 960x720
    engines = [e.identifier for e in
               bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    scene.render.engine = ('BLENDER_EEVEE_NEXT'
                           if 'BLENDER_EEVEE_NEXT' in engines
                           else 'BLENDER_EEVEE')
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass

    prev_dir = os.path.join(ASSETS, "previews")
    os.makedirs(prev_dir, exist_ok=True)
    scene.render.filepath = os.path.join(prev_dir, "casino.png")
    bpy.ops.render.render(write_still=True)
    assert os.path.exists(scene.render.filepath), "No se genero el PNG"
    print("PNG:", scene.render.filepath)

    blend_dir = os.path.join(ASSETS, "blend")
    os.makedirs(blend_dir, exist_ok=True)
    blend_path = os.path.join(blend_dir, "casino.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("BLEND:", blend_path)
    print("TEST_CASINO_OK")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
