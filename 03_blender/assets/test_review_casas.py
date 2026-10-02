"""test_review_casas.py - revision independiente de casas_kit_v2 (NO modifica el modulo).

Comprobaciones numericas propias + renders desde angulos que el test del
constructor no cubre. Los PNG van a la carpeta scratch del revisor.
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
OUT = os.environ.get(
    "REVIEW_OUT",
    r"C:\Users\arcej\AppData\Local\Temp\claude\E--Escritorio-claude-pc-arnau-aseto-corsa"
    r"\1a7b6c0c-72d8-44ab-af11-95e782d87886\scratchpad")
DO_RENDER = os.environ.get("REVIEW_RENDER", "1") == "1"

VAR_PUEBLO = ((3, 9.0, 11), (4, 10.0, 12), (5, 9.5, 11), (4, 11.5, 12), (3, 12.0, 11),
              (5, 10.5, 12), (6, 10.0, 12), (4, 9.0, 10), (3, 10.5, 12), (5, 12.0, 12))
VAR_ROCA = ((3, 10, 10), (4, 11, 10), (5, 9, 9), (4, 13, 11), (3, 12, 10), (5, 11, 10))
VAR_VIAD = ((3, 9, 9), (4, 10, 9), (5, 9, 9), (4, 11, 10), (3, 10, 9), (6, 10, 10))
FAMILIAS = (("P", VAR_PUEBLO, 300), ("R", VAR_ROCA, 70), ("V", VAR_VIAD, 170))


def cargar(nombre):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(BASE, nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bbox(ob):
    vs = [Vector(c) for c in ob.bound_box]
    return (min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs),
            max(v.y for v in vs), min(v.z for v in vs), max(v.z for v in vs))


def caras_que_ven_dorso(ob):
    """Para cada cara: rayo desde su centro hacia fuera (normal). Si lo primero que
    toca es el DORSO de otra cara, o bien esta cara esta invertida / enterrada
    dentro de un solido, o la otra esta invertida. Devuelve dict material -> n."""
    me = ob.data
    verts = [v.co.copy() for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons(verts, polys)
    nombres = [m.name.replace("MAT_CASAS_", "") for m in me.materials]
    res = {}
    ejemplos = []
    for p in me.polygons:
        n = p.normal
        o = p.center + n * 0.002
        loc, nrm, idx, dist = bvh.ray_cast(o, n, 200.0)
        if idx is None:
            continue
        n2 = me.polygons[idx].normal
        if n2.dot(n) > 0.2:
            k = nombres[p.material_index]
            res[k] = res.get(k, 0) + 1
            if len(ejemplos) < 400:
                ejemplos.append((k, tuple(round(c, 2) for c in p.center),
                                 tuple(round(c, 2) for c in n), round(dist, 3),
                                 nombres[me.polygons[idx].material_index], round(p.area, 3)))
    return res, ejemplos


def casi_coplanares(ob, tol=0.029, area_min=0.02):
    me = ob.data
    nombres = [m.name.replace("MAT_CASAS_", "") for m in me.materials]
    grupos = {}
    for p in me.polygons:
        n = p.normal
        for ax in range(3):
            if abs(n[ax]) > 0.9999:
                vs = [me.vertices[i].co for i in p.vertices]
                o = sum(v[ax] for v in vs) / len(vs)
                u, w = [k for k in range(3) if k != ax]
                rect = (min(v[u] for v in vs), max(v[u] for v in vs),
                        min(v[w] for v in vs), max(v[w] for v in vs))
                grupos.setdefault((ax, n[ax] > 0), []).append((o, rect, p.material_index))
    out = {}
    for (ax, pos), lst in grupos.items():
        lst.sort(key=lambda t: t[0])
        for i in range(len(lst)):
            oi, ri, mi = lst[i]
            j = i + 1
            while j < len(lst) and lst[j][0] - oi < tol:
                oj, rj, mj = lst[j]
                j += 1
                if mi == mj:
                    continue
                du = min(ri[1], rj[1]) - max(ri[0], rj[0])
                dw = min(ri[3], rj[3]) - max(ri[2], rj[2])
                if du <= 0.004 or dw <= 0.004 or du * dw < area_min:
                    continue
                key = (tuple(sorted((nombres[mi], nombres[mj]))), round(oj - oi, 3), "XYZ"[ax])
                out[key] = out.get(key, 0) + 1
    return out


def apuntar(obj, desde, hacia):
    obj.location = desde
    obj.rotation_euler = (Vector(hacia) - Vector(desde)).to_track_quat("-Z", "Y").to_euler()


def main():
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    v2 = cargar("casas_kit_v2")
    v1 = cargar("casas_kit")

    col2 = bpy.data.collections.new("REV_v2")
    scene.collection.children.link(col2)
    col1 = bpy.data.collections.new("REV_v1")
    scene.collection.children.link(col1)

    # ------------------------------------------------------------ API
    import inspect
    for fn in ("build_casa", "build_manzana", "build"):
        s1 = str(inspect.signature(getattr(v1, fn)))
        s2 = str(inspect.signature(getattr(v2, fn)))
        print("API %-14s v1%s  v2%s  %s" % (fn, s1, s2, "IGUAL" if s1 == s2 else "DISTINTA"))

    # ------------------------------------------------------------ variantes
    casas = {}
    print("=== VARIANTES: tris, bbox v1 vs v2, caras que ven dorso, casi coplanares ===")
    tot_dorso = {}
    tot_cop = {}
    for fam, variantes, seed0 in FAMILIAS:
        for k, (pl, an, fo) in enumerate(variantes):
            et = "%s%02d" % (fam, k)
            o2 = v2.build_casa(col2, plantas=pl, ancho=an, fondo=fo, seed=seed0 + k, name="CASA_" + et)
            o1 = v1.build_casa(col1, plantas=pl, ancho=an, fondo=fo, seed=seed0 + k, name="V1_" + et)
            o2.data.calc_loop_triangles()
            o1.data.calc_loop_triangles()
            t2, t1 = len(o2.data.loop_triangles), len(o1.data.loop_triangles)
            b1, b2 = bbox(o1), bbox(o2)
            dmax = max(abs(a - b) for a, b in zip(b1[:4], b2[:4]))
            mats1 = sorted(m.name for m in o1.data.materials)
            mats2 = sorted(m.name for m in o2.data.materials)
            fach1 = [m for m in mats1 if "fachada" in m]
            fach2 = [m for m in mats2 if "fachada" in m]
            teja1 = any("teja" in m for m in mats1)
            teja2 = any("teja" in m for m in mats2)
            dorso, ej = caras_que_ven_dorso(o2)
            cop = casi_coplanares(o2)
            for kk, vv in dorso.items():
                tot_dorso[kk] = tot_dorso.get(kk, 0) + vv
            for kk, vv in cop.items():
                tot_cop[kk] = tot_cop.get(kk, 0) + vv
            print("  %s pl=%d an=%.1f fo=%.1f tris v1=%d v2=%d  dbbox_xy=%.2f  fachada %s/%s %s  "
                  "tejado(dosaguas) v1=%s v2=%s %s  name=%s type=%s loc=%s" % (
                      et, pl, an, fo, t1, t2, dmax, fach1, fach2,
                      "OK" if fach1 == fach2 else "COLOR_DISTINTO",
                      teja1, teja2, "OK" if teja1 == teja2 else "TEJADO_DISTINTO",
                      o2.name, o2.type, tuple(o2.location)))
            print("      bbox v2 x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]  dorso=%s" % (*b2, dorso))
            if et in ("P09",):
                for e in ej[:60]:
                    print("      DORSO", e)
            casas[et] = (o2, pl, an, fo)
            o1.hide_render = True
    print("=== TOTAL caras que ven dorso por material:", tot_dorso)
    print("=== TOTAL pares casi coplanares (<2.9cm, distinto material, >0.02 m2):")
    for kk, vv in sorted(tot_cop.items(), key=lambda t: -t[1]):
        print("     ", kk, vv)

    # pivote / orientacion: la fachada (puerta = madera) debe estar en y>0
    o2 = casas["P01"][0]
    me = o2.data
    idx_mad = [i for i, m in enumerate(me.materials) if m.name == "MAT_CASAS_madera"][0]
    ys = [p.center.y for p in me.polygons if p.material_index == idx_mad]
    print("PIVOTE P01: caras de madera (puerta/escaparate) y en [%.2f, %.2f] (esperado > 0)" % (
        min(ys), max(ys)))

    # manzana
    colm = bpy.data.collections.new("REV_manz")
    scene.collection.children.link(colm)
    root = v2.build(colm, seed=7)
    print("MANZANA root name=%s type=%s hijos=%s" % (
        root.name, root.type, [c.name for c in root.children]))
    hijos = sorted(root.children, key=lambda c: c.name)
    for c in hijos:
        bb = bbox(c)
        print("   %s loc.x=%.2f ancho_bbox=[%.2f,%.2f] y[%.2f,%.2f] z_max=%.2f" % (
            c.name, c.location.x, bb[0], bb[1], bb[2], bb[3], bb[5]))

    if not DO_RENDER:
        print("REVIEW_OK (sin render)")
        return

    # ------------------------------------------------------------ render
    for m in bpy.data.materials:
        if m.name.startswith("MAT_CASAS_"):
            m.use_backface_culling = True
    mat_suelo = bpy.data.materials.new("REV_suelo")
    mat_suelo.use_nodes = True
    mat_suelo.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.35, 0.35, 0.36, 1)

    def suelo(z=0.0, cy=0.0):
        me_ = bpy.data.meshes.new("REV_suelo")
        s = 400.0
        me_.from_pydata([(-s, cy - s, z), (s, cy - s, z), (s, cy + s, z), (-s, cy + s, z)], [], [(0, 1, 2, 3)])
        me_.materials.append(mat_suelo)
        ob = bpy.data.objects.new("REV_suelo", me_)
        scene.collection.objects.link(ob)
        return ob

    piso = suelo()

    cam_data = bpy.data.cameras.new("REV_cam")
    cam_data.clip_start = 0.2
    cam_data.clip_end = 2000.0
    cam = bpy.data.objects.new("REV_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new("REV_sol", "SUN")
    sun_data.energy = 3.0
    sun_data.angle = math.radians(1.5)
    sun = bpy.data.objects.new("REV_sol", sun_data)
    scene.collection.objects.link(sun)
    apuntar(sun, (0, 0, 0), (0.55, -1.0, -0.85))
    world = bpy.data.worlds.new("REV_cielo")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.45, 0.68, 0.95, 1.0)
    bg.inputs[1].default_value = 0.9
    scene.world = world
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    try:
        scene.eevee.taa_render_samples = 16
    except Exception:
        pass
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"

    todos = [c[0] for c in casas.values()] + list(hijos)

    def solo(objs):
        for o in todos:
            o.hide_render = o not in objs

    def render(nombre):
        ruta = os.path.join(OUT, "rev_%s.png" % nombre)
        scene.render.filepath = ruta
        bpy.ops.render.render(write_still=True)
        print("PNG:", ruta, os.path.exists(ruta))

    # colocar todas lejos
    for i, (et, (o, pl, an, fo)) in enumerate(casas.items()):
        o.location = (i * 40.0, 600.0, 0.0)
    root.location = (0.0, -500.0, 0.0)

    # R1: P09 a ras de calle, vista rasante de la fachada (ojo del piloto)
    o, pl, an, fo = casas["P09"]
    o.location = (0, 0, 0)
    solo([o])
    cam_data.type = "PERSP"
    cam_data.lens = 28.0
    apuntar(cam, (-an / 2 - 7.0, 4.5, 1.3), (an / 2, 0.3, 7.0))
    render("1_P09_rasante")
    # R2: bajo balcon y alero, mirando hacia arriba
    cam_data.lens = 22.0
    apuntar(cam, (1.5, 2.6, 0.9), (0.0, 0.0, 3.8 + (pl - 1) * 3.0))
    render("2_P09_contrapicado")
    # R2b: planta baja de cerca (porton, escaparates, toldos, zocalo)
    cam_data.lens = 30.0
    apuntar(cam, (2.0, 9.0, 1.5), (0.0, 0.0, 2.0))
    render("2b_P09_planta_baja")
    # R3: cubierta desde arriba
    cam_data.lens = 35.0
    apuntar(cam, (14.0, 12.0, 3.8 + (pl - 1) * 3.0 + 14.0), (0.0, -fo / 2, 3.8 + (pl - 1) * 3.0 + 1.0))
    render("3_P09_cubierta")
    o.location = (0, 600, 0)
    # R3b: cubierta plana P06
    o, pl, an, fo = casas["P06"]
    o.location = (0, 0, 0)
    solo([o])
    apuntar(cam, (12.0, 10.0, 3.8 + (pl - 1) * 3.0 + 9.0), (0.0, -fo / 2, 3.8 + (pl - 1) * 3.0 + 0.5))
    render("3b_P06_terraza")
    o.location = (0, 600, 0)

    # R4/R5: manzana, juntas entre casas
    solo(list(hijos))
    piso.location = (0, -500, 0)
    cam_data.lens = 40.0
    apuntar(cam, (2.0, -500.0 + 26.0, 9.0), (2.0, -500.0, 10.5))
    render("4_manzana_juntas_frente")
    apuntar(sun, (0, 0, 0), (-0.55, 1.0, -0.85))
    apuntar(cam, (-4.0, -500.0 - 40.0, 12.0), (0.0, -512.0, 8.0))
    render("5_manzana_juntas_tras")
    apuntar(sun, (0, 0, 0), (0.55, -1.0, -0.85))
    piso.location = (0, 0, 0)

    # R6: como en la escena: casas sueltas adosadas, hundidas 0.45 m
    fila = ["P01", "P03", "P06", "P00"]
    x = 0.0
    objs = []
    for et in fila:
        o, pl, an, fo = casas[et]
        o.location = (x + an / 2.0, 0.0, -0.45)
        x += an
        objs.append(o)
    solo(objs)
    cam_data.lens = 32.0
    apuntar(cam, (x / 2 + 6.0, 30.0, 1.6), (x / 2 - 2.0, 0.0, 7.5))
    render("6_fila_escena_frente")
    cam_data.lens = 45.0
    apuntar(cam, (casas["P01"][2] + 1.0, 14.0, 1.4), (casas["P01"][2], 0.0, 3.0))
    render("6b_fila_escena_junta_baja")
    apuntar(cam, (casas["P01"][2] + 3.0, 16.0, 20.0), (casas["P01"][2], -2.0, 14.5))
    render("6c_fila_escena_junta_alta")
    # R8: legibilidad a distancia de pista
    cam_data.lens = 35.0
    apuntar(cam, (x / 2 - 60.0, 110.0, 3.0), (x / 2, 0.0, 8.0))
    render("8_lejos")
    for o in objs:
        o.location = (0, 600, 0)

    # R7: roca R02 (5,9,9) 3/4 trasera izquierda
    o, pl, an, fo = casas["R02"]
    o.location = (0, 0, 0)
    solo([o])
    apuntar(sun, (0, 0, 0), (-0.55, 1.0, -0.85))
    cam_data.lens = 30.0
    apuntar(cam, (-an / 2 - 14.0, -fo - 16.0, 6.0), (0.0, -fo / 2, 8.0))
    render("7_R02_tras_izq")
    print("REVIEW_OK")


try:
    main()
except Exception:
    traceback.print_exc()
    print("REVIEW_FALLO")
    sys.exit(1)
