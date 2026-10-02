# -*- coding: utf-8 -*-
"""Test de edificios_civicos_v2.py.

Comprueba la API (identica a la v1), el polycount, la huella/origen de cada
pieza y renderiza en EEVEE 1280x720:

    previews/civicos_v2_hotel_4lados.png      hoja de contacto 2x2:
    previews/civicos_v2_boxes_4lados.png          FRENTE(+Y) | TRASERA(-Y)
    previews/civicos_v2_ayto_4lados.png           IZQ(-X)    | DCHA(+X)
    previews/civicos_v2_campanile_4lados.png
    previews/civicos_v2_conjunto.png          tres cuartos de las 4 piezas

Cada celda de la hoja de contacto es un render de 640x360 con el nombre de
la vista rotulado (stamp). Guarda blend/edificios_civicos_v2.blend.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_edificios_civicos_v2.py"
"""

import importlib.util
import inspect
import math
import os
import sys
import tempfile
import traceback

import bpy
import numpy as np
from mathutils import Vector

ASSETS = os.path.dirname(os.path.abspath(__file__))
CELL_W, CELL_H = 640, 360
SHEET_W, SHEET_H = 1280, 720

# pieza -> (constructor, nombre de raiz, max tris, limites de bbox
#           (xmin, xmax, ymin, ymax, zmax) heredados de la v1: la v2 NO puede
#           crecer la huella porque el integrador levanta un plinto con ella)
PIEZAS = (
    ("hotel",     "build_hotel",        "HOTEL_root",      20000,
     (-30.75, 30.75, -12.75, 15.25, 26.85)),
    ("boxes",     "build_boxes",        "CARRERA_boxes",   12000,
     (-36.50, 36.50, -4.95, 11.80, 6.45)),
    ("ayto",      "build_ayuntamiento", "AYTO_root",       10000,
     (-11.50, 11.50, -7.00, 9.15, 33.75)),
    ("campanile", "build_campanile",    "CAMPANILE_root",   6000,
     (-3.10, 3.10, -3.10, 3.10, 35.50)),
)

VISTAS = (                       # etiqueta, direccion asset->camara, azimut sol
    ("FRENTE  +Y", (0.10, 1.00, 0.16), 200.0),
    ("TRASERA -Y", (-0.10, -1.00, 0.16), 25.0),
    ("IZQUIERDA -X", (-1.00, 0.12, 0.16), 290.0),
    ("DERECHA +X", (1.00, -0.12, 0.16), 115.0),
)

MAT_OK = ("MAT_CIVICO_", "MAT_AYTO_", "MAT_CAMPANILE_", "MAT_HOTEL_")


def tri_count(ob):
    return sum(max(0, len(p.vertices) - 2) for p in ob.data.polygons)


def fit_camera(cam, direction, pts, lens=50.0, aspect=16.0 / 9.0,
               margin=0.05):
    """Camara mirando a lo largo de -direction, lo mas cerca posible de forma
    que todos los puntos `pts` queden dentro del cuadro."""
    cam.data.lens = lens
    sensor = cam.data.sensor_width
    tan_h = (sensor / 2.0) / lens * (1.0 - margin)
    tan_v = (sensor / 2.0) / lens / aspect * (1.0 - margin)
    d = Vector(direction).normalized()
    fwd = -d
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    proj = [(p.dot(right), p.dot(up), p.dot(fwd)) for p in pts]
    cx = (min(q[0] for q in proj) + max(q[0] for q in proj)) / 2.0
    cy = (min(q[1] for q in proj) + max(q[1] for q in proj)) / 2.0
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


def puntos(objs):
    pts = []
    for ob in objs:
        if ob.type == 'MESH':
            mw = ob.matrix_world
            pts.extend(mw @ v.co for v in ob.data.vertices)
    return pts


def medir(objs, etiqueta):
    tris = 0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        if ob.type != 'MESH':
            continue
        tris += tri_count(ob)
        for mat in ob.data.materials:
            assert mat.name.startswith(MAT_OK), "material raro: %s" % mat.name
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
    print("  %-10s tris=%6d  bbox x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f"
          % (etiqueta, tris, lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    return tris, lo, hi


def render_celda(scene, ruta, nota):
    scene.render.resolution_x = CELL_W
    scene.render.resolution_y = CELL_H
    scene.render.stamp_note_text = nota
    scene.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    assert os.path.exists(ruta), "no se genero %s" % ruta


def hoja_contacto(rutas, salida):
    """Monta 4 celdas 640x360 en una hoja 1280x720 (orden: arriba izq/dcha,
    abajo izq/dcha). Las imagenes de Blender van de abajo a arriba."""
    big = np.zeros((SHEET_H, SHEET_W, 4), dtype=np.float32)
    big[:, :, 3] = 1.0
    for idx, ruta in enumerate(rutas):
        img = bpy.data.images.load(ruta)
        iw, ih = img.size
        arr = np.empty(iw * ih * 4, dtype=np.float32)
        img.pixels.foreach_get(arr)
        arr = arr.reshape(ih, iw, 4)
        fila, col = idx // 2, idx % 2
        y0 = (1 - fila) * CELL_H
        x0 = col * CELL_W
        big[y0:y0 + ih, x0:x0 + iw] = arr
        bpy.data.images.remove(img)
    big[SHEET_H // 2 - 1:SHEET_H // 2 + 1, :, :3] = 0.0     # cruz separadora
    big[:, SHEET_W // 2 - 1:SHEET_W // 2 + 1, :3] = 0.0
    out = bpy.data.images.new("HOJA", SHEET_W, SHEET_H, alpha=False,
                              float_buffer=False)
    out.pixels.foreach_set(big.ravel())
    out.filepath_raw = salida
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)
    assert os.path.exists(salida), "no se genero %s" % salida
    print("PNG:", salida)


def limpiar(coll):
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for cu in list(bpy.data.curves):
        if cu.users == 0:
            bpy.data.curves.remove(cu)


def main():
    spec = importlib.util.spec_from_file_location(
        "edificios_civicos_v2", os.path.join(ASSETS, "edificios_civicos_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # --- API byte-compatible con la v1 -----------------------------------
    firmas = {
        "build_hotel": ["parent_collection", "params"],
        "build_boxes": ["parent_collection", "n", "params"],
        "build_ayuntamiento": ["parent_collection", "params"],
        "build_campanile": ["parent_collection", "params"],
        "build": ["parent_collection", "seed", "params"],
    }
    for fn, esperado in firmas.items():
        par = inspect.signature(getattr(mod, fn)).parameters
        assert list(par) == esperado, "firma de %s: %s" % (fn, list(par))
    assert inspect.signature(mod.build_boxes).parameters["n"].default == 12
    assert inspect.signature(mod.build).parameters["seed"].default == 0
    print("API OK:", ", ".join(sorted(firmas)))

    scene = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    coll = bpy.data.collections.new("PortoCorsa_assets")
    scene.collection.children.link(coll)

    # --- suelo neutro -----------------------------------------------------
    ground_me = bpy.data.meshes.new("TEST_ground")
    s = 900.0
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

    # --- camara, sol y cielo (misma luz que la escena real) ---------------
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.clip_start = 0.5
    cam_data.clip_end = 4000.0
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
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass

    # rotulo de vista quemado en cada celda
    r = scene.render
    r.use_stamp = True
    r.use_stamp_note = True
    for prop in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time",
                 "use_stamp_frame", "use_stamp_frame_range", "use_stamp_scene",
                 "use_stamp_camera", "use_stamp_lens", "use_stamp_filename",
                 "use_stamp_marker", "use_stamp_sequencer_strip",
                 "use_stamp_memory", "use_stamp_hostname", "use_stamp_labels"):
        try:
            setattr(r, prop, False)
        except AttributeError:
            pass
    r.stamp_font_size = 26
    r.stamp_foreground = (1.0, 1.0, 1.0, 1.0)
    r.stamp_background = (0.0, 0.0, 0.0, 0.65)

    prev_dir = os.path.join(ASSETS, "previews")
    os.makedirs(prev_dir, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix="civicos_v2_")
    hechos = []
    resumen = []

    # --- una hoja de contacto por pieza -----------------------------------
    for clave, fn_name, raiz_name, max_tris, lim in PIEZAS:
        limpiar(coll)
        root = getattr(mod, fn_name)(coll)
        assert root is not None, "%s no devolvio raiz" % fn_name
        assert root.type == 'EMPTY', "%s: la raiz debe ser un Empty" % fn_name
        assert root.name == raiz_name, "raiz %s != %s" % (root.name, raiz_name)
        assert tuple(round(v, 6) for v in root.location) == (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()

        objs = [root] + list(root.children_recursive)
        assert len(objs) == len(list(coll.objects)), "objetos sueltos"
        tris, lo, hi = medir(objs, clave)
        assert tris <= max_tris, "%s: polycount %d > %d" % (clave, tris,
                                                            max_tris)
        assert abs(lo.z) < 0.06, "%s: la base debe estar en z=0 (%.3f)" % (
            clave, lo.z)
        assert lim[0] <= lo.x and hi.x <= lim[1], "%s: huella X %.2f..%.2f" % (
            clave, lo.x, hi.x)
        assert lim[2] <= lo.y and hi.y <= lim[3], "%s: huella Y %.2f..%.2f" % (
            clave, lo.y, hi.y)
        assert hi.z <= lim[4], "%s: altura %.2f > %.2f" % (clave, hi.z, lim[4])
        resumen.append((clave, tris, hi.x - lo.x, hi.y - lo.y, hi.z))

        pts = puntos(objs)
        celdas = []
        for i, (etiqueta, direccion, az) in enumerate(VISTAS):
            fit_camera(cam, direccion, pts, lens=50.0)
            sun.rotation_euler = (math.radians(52.0), 0.0, math.radians(az))
            ruta = os.path.join(tmp_dir, "%s_%d.png" % (clave, i))
            render_celda(scene, ruta, "%s  -  %s" % (clave.upper(), etiqueta))
            celdas.append(ruta)
        salida = os.path.join(prev_dir, "civicos_v2_%s_4lados.png" % clave)
        hoja_contacto(celdas, salida)
        hechos.append(salida)

    # --- conjunto: las cuatro piezas en tres cuartos ----------------------
    limpiar(coll)
    colocacion = (
        ("build_campanile", (-58.0, 16.0), 0.0),
        ("build_ayuntamiento", (-30.0, -2.0), math.radians(-8.0)),
        ("build_hotel", (36.0, 4.0), math.radians(6.0)),
        ("build_boxes", (-6.0, -48.0), math.radians(-14.0)),
    )
    for fn_name, (px, py), rz in colocacion:
        ob = getattr(mod, fn_name)(coll)
        ob.location = (px, py, 0.0)
        ob.rotation_euler = (0.0, 0.0, rz)
    bpy.context.view_layer.update()
    pts = puntos(list(coll.objects))
    fit_camera(cam, (0.62, 0.74, 0.40), pts, lens=32.0)
    sun.rotation_euler = (math.radians(52.0), 0.0, math.radians(150.0))
    centro = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)
    dist = (cam.location - centro).length
    cerca = min((cam.location - p).length for p in pts)
    scene.render.resolution_x = SHEET_W
    scene.render.resolution_y = SHEET_H
    scene.render.stamp_note_text = ("CONJUNTO 3/4  -  camara a %.0f m del "
                                    "grupo (%.0f m del edificio mas cercano)"
                                    % (dist, cerca))
    salida = os.path.join(prev_dir, "civicos_v2_conjunto.png")
    scene.render.filepath = salida
    bpy.ops.render.render(write_still=True)
    assert os.path.exists(salida), "no se genero el conjunto"
    print("PNG:", salida)
    print("CONJUNTO camara: %.1f m al centro, %.1f m al edificio mas cercano"
          % (dist, cerca))
    hechos.append(salida)

    # --- build() del kit: sigue devolviendo las tres piezas de la v1 ------
    limpiar(coll)
    root = mod.build(coll, seed=0)
    assert root.name == "EDIFICIOS_CIVICOS_root", root.name
    hijos = sorted(c.name for c in root.children)
    assert hijos == ["AYTO_root", "CAMPANILE_root", "HOTEL_root"], hijos
    print("build() OK ->", root.name, hijos)

    blend_dir = os.path.join(ASSETS, "blend")
    os.makedirs(blend_dir, exist_ok=True)
    blend_path = os.path.join(blend_dir, "edificios_civicos_v2.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("BLEND:", blend_path)

    for clave, tris, sx, sy, hz in resumen:
        print("RESUMEN %-10s tris=%6d  huella %.1f x %.1f m  alto %.1f m"
              % (clave, tris, sx, sy, hz))
    print("TEST_EDIFICIOS_CIVICOS_V2_OK previews=%d" % len(hechos))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
