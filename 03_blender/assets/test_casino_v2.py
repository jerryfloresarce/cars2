# -*- coding: utf-8 -*-
"""Test de casino_v2.py: escena limpia, build(), sol + cielo suave, y 4 previews
EEVEE 1280x720 encuadradas al asset:
    previews/casino_v2_frente.png   (fachada principal, +Y)
    previews/casino_v2_trasera.png  (lado mar, -Y)
    previews/casino_v2_lado.png     (testero +X)
    previews/casino_v2_34.png       (tres cuartos aerea)
Guarda blend/casino_v2.blend.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_casino_v2.py"
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

ASSETS = os.path.dirname(os.path.abspath(__file__))
MAX_TRIS = 30000


def tri_count(ob):
    return sum(max(0, len(p.vertices) - 2) for p in ob.data.polygons)


def fit_camera(cam, direction, pts, lens=50.0, aspect=16.0 / 9.0,
               margin=0.04):
    """Coloca la camara mirando a lo largo de -direction (direction = vector
    desde el asset hacia la camara) lo MAS CERCA posible de forma que todos
    los puntos `pts` (vertices reales del asset) queden dentro del cuadro."""
    cam.data.lens = lens
    sensor = cam.data.sensor_width            # ajuste horizontal (36 mm)
    tan_h = (sensor / 2.0) / lens * (1.0 - margin)
    tan_v = (sensor / 2.0) / lens / aspect * (1.0 - margin)
    d = Vector(direction).normalized()
    fwd = -d
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    proj = [(p.dot(right), p.dot(up), p.dot(fwd)) for p in pts]
    cx = (min(q[0] for q in proj) + max(q[0] for q in proj)) / 2.0
    cy = (min(q[1] for q in proj) + max(q[1] for q in proj)) / 2.0
    zc = 0.0
    for _ in range(8):
        zc = min(z - max(abs(x - cx) / tan_h, abs(y - cy) / tan_v)
                 for (x, y, z) in proj)
        ax = [(x - cx) / (z - zc) for (x, y, z) in proj]
        ay = [(y - cy) / (z - zc) for (x, y, z) in proj]
        depth = sum(z - zc for (x, y, z) in proj) / len(proj)
        cx += 0.5 * (min(ax) + max(ax)) * depth
        cy += 0.5 * (min(ay) + max(ay)) * depth
    zc = min(z - max(abs(x - cx) / tan_h, abs(y - cy) / tan_v)
             for (x, y, z) in proj)
    cam.location = right * cx + up * cy + fwd * zc
    cam.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler()


def main():
    spec = importlib.util.spec_from_file_location(
        "casino_v2", os.path.join(ASSETS, "casino_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    scene = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)

    coll = bpy.data.collections.new("PortoCorsa_assets")
    scene.collection.children.link(coll)

    root = mod.build(coll, seed=0)
    assert root is not None and root.name.startswith("CASINO_root"), \
        "build() debe devolver el Empty raiz CASINO_root"
    assert root.type == 'EMPTY'
    assert tuple(round(v, 6) for v in root.location) == (0.0, 0.0, 0.0)

    # --- polycount + bbox
    bpy.context.view_layer.update()
    tris = 0
    por_pieza = {}
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in coll.objects:
        assert ob.name.startswith("CASINO_"), "prefijo: %s" % ob.name
        if ob.type != 'MESH':
            continue
        t = tri_count(ob)
        tris += t
        pieza = ob.parent.name if ob.parent else ob.name
        por_pieza[pieza] = por_pieza.get(pieza, 0) + t
        for mat in ob.data.materials:
            assert mat.name.startswith("MAT_CASINO_"), mat.name
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
    for k in sorted(por_pieza):
        print("  tris %-28s %6d" % (k, por_pieza[k]))
    print("CASINO_V2 tris:", tris)
    print("CASINO_V2 bbox: x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f"
          % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    assert tris <= MAX_TRIS, "Polycount excedido: %d" % tris
    assert abs(lo.z) < 0.05, "la base debe estar en z=0"
    assert hi.x - lo.x < 96.0 and hi.y - lo.y < 56.0, "huella fuera de ~92x52"

    # --- suelo neutro
    ground_me = bpy.data.meshes.new("TEST_ground")
    s = 600.0
    ground_me.from_pydata(
        [(-s, -s, -0.02), (s, -s, -0.02), (s, s, -0.02), (-s, s, -0.02)],
        [], [(0, 1, 2, 3)])
    gmat = bpy.data.materials.new("MAT_TEST_ground")
    gmat.use_nodes = True
    b = gmat.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.42, 0.40, 0.35, 1.0)
    b.inputs["Roughness"].default_value = 0.95
    ground_me.materials.append(gmat)
    ground = bpy.data.objects.new("TEST_ground", ground_me)
    scene.collection.objects.link(ground)

    # --- camara + sol (misma energia que la escena real: 4.6) + cielo suave
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.clip_start = 1.0
    cam_data.clip_end = 3000.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    sun_data = bpy.data.lights.new("TEST_sun", 'SUN')
    sun_data.energy = 4.6
    sun_data.color = (1.0, 0.955, 0.87)
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("TEST_sun", sun_data)
    scene.collection.objects.link(sun)

    world = bpy.data.worlds.new("TEST_world")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.40, 0.62, 0.90, 1.0)
    bg.inputs[1].default_value = 0.75
    scene.world = world

    try:
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.exposure = 0.12
    except TypeError:
        pass

    engines = [e.identifier for e in
               bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    scene.render.engine = ('BLENDER_EEVEE_NEXT'
                           if 'BLENDER_EEVEE_NEXT' in engines
                           else 'BLENDER_EEVEE')
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass

    pts = []
    for ob in coll.objects:
        if ob.type == 'MESH':
            mw = ob.matrix_world
            pts.extend(mw @ v.co for v in ob.data.vertices)

    # nombre, direccion asset->camara, azimut del sol, focal
    vistas = [
        ("casino_v2_frente", (0.10, 1.0, 0.16), 200.0, 50.0),
        ("casino_v2_trasera", (-0.12, -1.0, 0.18), 25.0, 50.0),
        ("casino_v2_lado", (1.0, 0.08, 0.14), 115.0, 85.0),
        ("casino_v2_34", (0.62, 0.78, 0.50), 150.0, 50.0),
    ]
    prev_dir = os.path.join(ASSETS, "previews")
    os.makedirs(prev_dir, exist_ok=True)
    hechos = []
    for nombre, direccion, az, focal in vistas:
        fit_camera(cam, direccion, pts, lens=focal)
        sun.rotation_euler = (math.radians(52.0), 0.0, math.radians(az))
        scene.render.filepath = os.path.join(prev_dir, nombre + ".png")
        bpy.ops.render.render(write_still=True)
        assert os.path.exists(scene.render.filepath), "No se genero el PNG"
        print("PNG:", scene.render.filepath)
        hechos.append(scene.render.filepath)

    blend_dir = os.path.join(ASSETS, "blend")
    os.makedirs(blend_dir, exist_ok=True)
    blend_path = os.path.join(blend_dir, "casino_v2.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("BLEND:", blend_path)
    print("TEST_CASINO_V2_OK tris=%d previews=%d" % (tris, len(hechos)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
