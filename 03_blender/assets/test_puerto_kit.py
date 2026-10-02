"""test_puerto_kit.py — Test headless del kit del puerto (Porto Corsa).

Ejecutar con:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_puerto_kit.py"

Carga puerto_kit.py por ruta, construye la vineta build(), encuadra camara con
sol + cielo uniforme, renderiza previews/puerto_kit.png (EEVEE 960x720) y
guarda blend/puerto_kit.blend. Imprime el recuento de tris por pieza.
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"


def _tris_de(ob):
    total = 0
    for child in [ob] + list(ob.children_recursive):
        if child.type == 'MESH':
            total += sum(len(p.vertices) - 2 for p in child.data.polygons)
    return total


def main():
    scene = bpy.context.scene

    # escena limpia (factory startup trae cubo/luz/camara)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    # cargar modulo por ruta
    spec = importlib.util.spec_from_file_location(
        "puerto_kit", os.path.join(BASE, "puerto_kit.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    coll = bpy.data.collections.new("ASSETS")
    scene.collection.children.link(coll)

    root = mod.build(coll, seed=1)
    bpy.context.view_layer.update()

    # recuento de tris por pieza (contrato: <= 5000 por pieza de kit)
    print("--- Tris por pieza ---")
    for ob in coll.objects:
        if ob.parent is root or ob is root:
            n = _tris_de(ob)
            print(f"  {ob.name}: {n} tris")
            if ob is not root and n > 5000:
                raise RuntimeError(f"{ob.name} supera 5k tris ({n})")
    print(f"  TOTAL escena: {_tris_de(root)} tris")

    # sol mediterraneo (luz frontal-izquierda alta) + cielo uniforme
    sun = bpy.data.lights.new("SOL", 'SUN')
    sun.energy = 4.5
    sun.angle = math.radians(2.0)
    sun_ob = bpy.data.objects.new("SOL", sun)
    scene.collection.objects.link(sun_ob)
    sun_ob.rotation_euler = (math.radians(55), 0, math.radians(-140))

    world = bpy.data.worlds.new("CIELO")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = (0.50, 0.70, 0.92, 1.0)
        bg.inputs[1].default_value = 0.75
    scene.world = world

    # camara cinematica: faro en primer termino, darsena y dique detras
    cam = bpy.data.cameras.new("CAM")
    cam.lens = 30
    cam.clip_start = 0.5
    cam.clip_end = 4000
    cam_ob = bpy.data.objects.new("CAM", cam)
    scene.collection.objects.link(cam_ob)
    scene.camera = cam_ob
    cam_ob.location = Vector((166.0, 142.0, 55.0))
    target = Vector((24.0, -16.0, 2.0))
    look = (target - cam_ob.location).normalized()
    cam_ob.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()

    # render EEVEE
    for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    try:
        scene.eevee.taa_render_samples = 48
    except AttributeError:
        pass
    try:
        scene.view_settings.view_transform = 'Standard'
    except TypeError:
        pass
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'

    os.makedirs(os.path.join(BASE, "previews"), exist_ok=True)
    os.makedirs(os.path.join(BASE, "blend"), exist_ok=True)

    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(BASE, "blend", "puerto_kit.blend"))

    scene.render.filepath = os.path.join(BASE, "previews", "puerto_kit.png")
    bpy.ops.render.render(write_still=True)
    print("TEST_OK")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
