# -*- coding: utf-8 -*-
"""REVIEW (solo lectura del modulo): carga casino_v2.py, comprueba API/mallas y
renderiza angulos extra en previews/review_casino_*.png. No toca el modulo ni
los previews del constructor ni guarda ningun .blend."""

import importlib.util
import inspect
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

ASSETS = os.path.dirname(os.path.abspath(__file__))
PREV = os.path.join(ASSETS, "previews")


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ASSETS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tri_count(ob):
    return sum(max(0, len(p.vertices) - 2) for p in ob.data.polygons)


def look_at(cam, pos, target, lens):
    cam.data.lens = lens
    cam.location = Vector(pos)
    d = Vector(target) - Vector(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def islands_report(ob):
    """Islas de la malla: cerradas con volumen negativo (invertidas) y abiertas."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    seen = set()
    inverted = 0
    open_isl = 0
    closed = 0
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-7)
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        stack = [f0]
        seen.add(f0.index)
        isl = []
        while stack:
            f = stack.pop()
            isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        is_closed = all(len(e.link_faces) == 2 for f in isl for e in f.edges)
        vol = 0.0
        for f in isl:
            vs = [v.co for v in f.verts]
            for i in range(1, len(vs) - 1):
                vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
        if is_closed:
            closed += 1
            if vol < -1e-9:
                inverted += 1
        else:
            open_isl += 1
    bm.free()
    return closed, inverted, open_isl, degenerate


def coplanar_overlaps(objs):
    """Caras coplanares con la MISMA orientacion y DISTINTO material cuyos
    bbox 2D se solapan (candidatas a z-fighting)."""
    buckets = {}
    for ob in objs:
        mw = ob.matrix_world
        rot = mw.to_3x3()
        mname = ob.data.materials[0].name if ob.data.materials else "?"
        for p in ob.data.polygons:
            n = (rot @ p.normal).normalized()
            c = mw @ p.center
            d = n.dot(c)
            key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), round(d, 2))
            pts = [mw @ ob.data.vertices[i].co for i in p.vertices]
            buckets.setdefault(key, []).append((mname, ob.name, pts, p.area))
    out = []
    for key, lst in buckets.items():
        if len(lst) < 2:
            continue
        n = Vector(key[:3])
        # base 2D
        a = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
        u = n.cross(a).normalized()
        v = n.cross(u).normalized()
        boxes = []
        for (mn, on, pts, area) in lst:
            us = [q.dot(u) for q in pts]
            vs = [q.dot(v) for q in pts]
            boxes.append((mn, on, min(us), max(us), min(vs), max(vs), area,
                          pts[0]))
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                A, B = boxes[i], boxes[j]
                if A[0] == B[0]:
                    continue
                ou = min(A[3], B[3]) - max(A[2], B[2])
                ov = min(A[5], B[5]) - max(A[4], B[4])
                if ou > 0.05 and ov > 0.05:
                    out.append((ou * ov, key, A[1], B[1], tuple(round(x, 2) for x in A[7])))
    out.sort(reverse=True)
    return out


def main():
    v1 = load("casino")
    v2 = load("casino_v2")

    # ---------- 1) firmas de la API frente a la v1
    print("=== API ===")
    for name, fn in inspect.getmembers(v1, inspect.isfunction):
        if not name.startswith("build"):
            continue
        f2 = getattr(v2, name, None)
        if f2 is None:
            print("API_MISSING", name)
            continue
        s1 = inspect.signature(fn)
        s2 = inspect.signature(f2)
        p1 = list(s1.parameters.values())
        p2 = list(s2.parameters.values())
        ok = True
        for a, b in zip(p1, p2):
            if a.name != b.name or a.default != b.default or a.kind != b.kind:
                ok = False
        if len(p2) < len(p1):
            ok = False
        extra = [p for p in p2[len(p1):]]
        extra_ok = all(p.default is not inspect.Parameter.empty
                       or p.kind == inspect.Parameter.VAR_KEYWORD for p in extra)
        print("API %-22s prefix_ok=%s extra_optional=%s  v2=%s"
              % (name, ok, extra_ok, s2))

    scene = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    coll = bpy.data.collections.new("REVIEW_assets")
    scene.collection.children.link(coll)
    root = v2.build(coll, seed=0)
    bpy.context.view_layer.update()
    print("ROOT", root.name, root.type, tuple(root.location),
          tuple(root.rotation_euler), tuple(root.scale))

    meshes = [o for o in coll.objects if o.type == 'MESH']
    empties = [o for o in coll.objects if o.type == 'EMPTY']
    tris = sum(tri_count(o) for o in meshes)
    print("OBJS meshes=%d empties=%d tris=%d" % (len(meshes), len(empties), tris))
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for ob in meshes:
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
    print("BBOX x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f" % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    bad_names = [o.name for o in coll.objects if not o.name.startswith("CASINO_")]
    print("BAD_NAMES", bad_names)
    orphans = [o.name for o in coll.objects if o is not root and o.parent is None]
    print("UNPARENTED", orphans)
    mats = sorted({m.name for o in meshes for m in o.data.materials})
    print("MATS", mats)

    # ---------- 2) sanidad de mallas
    print("=== MESH SANITY ===")
    tot_inv = tot_open = tot_deg = 0
    for ob in meshes:
        closed, inv, op, deg = islands_report(ob)
        tot_inv += inv
        tot_open += op
        tot_deg += deg
        if inv or op or deg:
            print("  %-40s closed=%d INVERTED=%d open=%d degenerate=%d"
                  % (ob.name, closed, inv, op, deg))
    print("SANITY inverted=%d open_islands=%d degenerate=%d" % (tot_inv, tot_open, tot_deg))

    # cono del abside trasero: normales hacia arriba?
    ob = bpy.data.objects.get("CASINO_central_tejado")
    if ob is not None:
        apex = None
        for v in ob.data.vertices:
            if abs(v.co.x) < 1e-4 and abs(v.co.y + 15.0) < 1e-4 and abs(v.co.z - 24.5) < 1e-4:
                apex = v.index
        ups = downs = 0
        for p in ob.data.polygons:
            if apex is not None and apex in p.vertices and len(p.vertices) == 3:
                if p.normal.z > 0:
                    ups += 1
                else:
                    downs += 1
        print("CONE apex=%s normals_up=%d normals_down=%d" % (apex, ups, downs))

    ov = coplanar_overlaps(meshes)
    print("=== COPLANAR different-material same-facing overlaps: %d ===" % len(ov))
    vistos = set()
    k = 0
    for area, key, a, b, p0 in ov:
        if key[2] == -1.0:          # caras que miran hacia abajo: no se ven
            continue
        a2 = a.replace("_L_", "_X_").replace("_R_", "_X_")
        b2 = b.replace("_L_", "_X_").replace("_R_", "_X_")
        firma = (round(area, 1), abs(key[0]), key[1], key[2], a2, b2)
        if firma in vistos or area < 0.25:
            continue
        vistos.add(firma)
        print("  area~%.2f plane n=%s d=%.2f  %s  <->  %s  at %s"
              % (area, key[:3], key[3], a, b, p0))
        k += 1
        if k >= 70:
            break

    # ---------- 3) segunda llamada: reutiliza materiales, no revienta
    n_mats_before = len([m for m in bpy.data.materials if m.name.startswith("MAT_CASINO_")])
    coll2 = bpy.data.collections.new("REVIEW_second")
    scene.collection.children.link(coll2)
    root2 = v2.build(coll2, seed=3, con_torres=False, con_relojes=False,
                     con_farolas=False, con_marquesina=False, linternas_patina=False)
    n_mats_after = len([m for m in bpy.data.materials if m.name.startswith("MAT_CASINO_")])
    tris2 = sum(tri_count(o) for o in coll2.objects if o.type == 'MESH')
    print("SECOND root=%s mats_before=%d mats_after=%d tris_variant=%d"
          % (root2.name, n_mats_before, n_mats_after, tris2))
    # piezas sueltas con llamada posicional estilo v1
    coll3 = bpy.data.collections.new("REVIEW_kit")
    scene.collection.children.link(coll3)
    r = v2.build_cupula(coll3, 5.0, (0, 0, 0), "_t", None, 12)
    print("KIT cupula ->", r.name, r.type)
    r = v2.build_balaustrada(coll3, 6.0, (0, 0, 0), "_t")
    print("KIT balaustrada ->", r.name, r.type)
    r = v2.build_columnata(coll3, 4, 5.0, 10.0)
    print("KIT columnata ->", r.name, r.type)
    r = v2.build_torre(coll3)
    print("KIT torre ->", r.name, r.type, "tris",
          sum(tri_count(o) for o in r.children if o.type == 'MESH'))
    for o in list(coll3.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    # apartar la variante 600 m para que no salga en los renders principales
    root2.location = (0.0, 0.0, -500.0)

    # ---------- 4) renders
    ground_me = bpy.data.meshes.new("TEST_ground")
    s = 1500.0
    ground_me.from_pydata([(-s, -s, -0.02), (s, -s, -0.02), (s, s, -0.02), (-s, s, -0.02)],
                          [], [(0, 1, 2, 3)])
    gmat = bpy.data.materials.new("MAT_TEST_ground")
    gmat.use_nodes = True
    b = gmat.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.42, 0.40, 0.35, 1.0)
    b.inputs["Roughness"].default_value = 0.95
    ground_me.materials.append(gmat)
    ground = bpy.data.objects.new("TEST_ground", ground_me)
    scene.collection.objects.link(ground)

    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.clip_start = 0.5
    cam_data.clip_end = 5000.0
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
    scene.render.engine = ('BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines
                           else 'BLENDER_EEVEE')
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    try:
        scene.eevee.taa_render_samples = 24
    except AttributeError:
        pass

    # backface culling: una normal invertida se ve como un agujero
    for m in bpy.data.materials:
        if m.name.startswith("MAT_CASINO_"):
            m.use_backface_culling = True

    PASADA = 2
    vistas_1 = [
        # nombre, pos camara, objetivo, focal, azimut sol
        ("review_casino_pista", (-95.0, 150.0, 1.5), (0.0, 0.0, 21.0), 35.0, 200.0),
        ("review_casino_mar_lejos", (130.0, -420.0, 4.0), (0.0, 0.0, 20.0), 50.0, 25.0),
        ("review_casino_tras34", (-85.0, -100.0, 70.0), (0.0, -5.0, 16.0), 50.0, 25.0),
        ("review_casino_torre", (52.0, 62.0, 33.0), (21.2, 3.0, 31.0), 85.0, 150.0),
        ("review_casino_oeste_bajo", (-135.0, -40.0, 2.5), (-25.0, -5.0, 17.0), 50.0, 290.0),
        ("review_casino_trasera_cerca", (14.0, -62.0, 9.0), (0.0, -25.0, 16.0), 35.0, 25.0),
    ]
    vistas_2 = [
        # trasera del fronton delantero (falso frente?) desde arriba-detras
        ("review_casino_fronton_detras", (-11.0, -16.0, 47.0), (-3.0, 10.0, 21.0), 28.0, 25.0),
        # cenital inclinada: tejados, union torre-ala-cuerpo central
        ("review_casino_cenital", (30.0, -20.0, 120.0), (5.0, 0.0, 15.0), 50.0, 150.0),
        # repisa z=20.4 de la torre (fachada/molduras coplanares) desde arriba
        ("review_casino_repisa_torre", (34.0, 17.0, 27.5), (21.2, 3.0, 20.4), 60.0, 150.0),
        # ojo de coche al pie de la rampa
        ("review_casino_ojo_coche", (10.0, 46.0, 1.2), (0.0, 8.0, 15.0), 24.0, 200.0),
        # union torre / ala / cuerpo central por delante, a media altura
        ("review_casino_union_torre", (44.0, 48.0, 14.0), (22.0, 5.0, 11.0), 50.0, 200.0),
    ]
    vistas_3 = [
        # fronton delantero visto de costado a ras de suelo y desde media altura
        ("review_casino_fronton_costado", (120.0, 34.0, 2.0), (5.0, 8.0, 19.0), 60.0, 150.0),
        ("review_casino_fronton_aereo", (-70.0, -30.0, 75.0), (0.0, 6.0, 20.0), 70.0, 25.0),
    ]
    PASADA = 3
    vistas = {1: vistas_1, 2: vistas_2, 3: vistas_3}[PASADA]
    os.makedirs(PREV, exist_ok=True)
    n = 0
    for nombre, pos, tgt, focal, az in vistas:
        look_at(cam, pos, tgt, focal)
        sun.rotation_euler = (math.radians(52.0), 0.0, math.radians(az))
        scene.render.filepath = os.path.join(PREV, nombre + ".png")
        bpy.ops.render.render(write_still=True)
        print("PNG:", scene.render.filepath)
        n += 1

    # variante sin torres / sin relojes / sin patina
    if PASADA == 1:
        root.location = (0.0, 0.0, -500.0)
        root2.location = (0.0, 0.0, 0.0)
        look_at(cam, (75.0, 120.0, 45.0), (0.0, 0.0, 14.0), 50.0)
        sun.rotation_euler = (math.radians(52.0), 0.0, math.radians(150.0))
        scene.render.filepath = os.path.join(PREV, "review_casino_variante_sin_torres.png")
        bpy.ops.render.render(write_still=True)
        print("PNG:", scene.render.filepath)
        n += 1
    print("REVIEW_CASINO_OK renders=%d" % n)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
