"""test_review_rueda.py — revisión independiente de montana_rueda.py (Blender 5.1).

No modifica el módulo. Construye la roca + arco con los valores por defecto y:
  1. Comprueba origen/bbox, manifold, coherencia de winding (is_contiguous),
     aristas vivas, materiales.
  2. Busca AUTO-INTERSECCIONES reales con BVHTree.overlap (pares de caras que
     no comparten vértice).
  3. Simula al integrador: resta un TÚNEL (caja 14 x 9 m a lo largo de Y por
     la parte inferior izquierda) con Boolean EXACT y comprueba que el
     resultado sigue siendo cerrado.
  4. Comprueba que las matas de MRUEDA_veg no flotan (distancia del centro a
     la superficie de la roca).
  5. Renderiza vistas adicionales:
       previews/mrueda_rev_pov.png    -> desde la carretera a 1.7 m (vista AC)
       previews/mrueda_rev_peli.png   -> encuadre y luz parecidos al fotograma
       previews/mrueda_rev_tunel.png  -> resultado del boolean del túnel
       previews/mrueda_rev_top.png    -> planta (silueta)
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PREV = os.path.join(BASE, "previews")


def _mat(name, color, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    return m


def _caja(nombre, centro, dim, mat, coll):
    cx, cy, cz = centro
    hx, hy, hz = dim[0] / 2.0, dim[1] / 2.0, dim[2] / 2.0
    vs = [(cx + sx * hx, cy + sy * hy, cz + sz * hz)
          for sx, sy, sz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                             (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))]
    fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
          (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(vs, [], fs)
    me.update()
    if mat is not None:
        me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    coll.objects.link(ob)
    return ob


def _bm_de(obj, evaluado=False):
    bm = bmesh.new()
    if evaluado:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        bm.from_mesh(me)
        ev.to_mesh_clear()
    else:
        bm.from_mesh(obj.data)
    return bm


def _stats(bm, nombre):
    bm.edges.ensure_lookup_table()
    nm = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bad = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    flip = sum(1 for e in bm.edges if len(e.link_faces) == 2 and not e.is_contiguous)
    sharp = sum(1 for e in bm.edges if not e.smooth)
    zmin = min(v.co.z for v in bm.verts)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    print("  %-22s tris=%6d no-manifold=%d  >2caras=%d  winding_incoherente=%d  "
          "sharp=%d  zmin=%.4f" % (nombre, tris, nm, bad, flip, sharp, zmin))
    return nm, flip


def _self_intersections(bm, nombre):
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    pares = tree.overlap(tree)
    reales = []
    for i, j in pares:
        if i >= j:
            continue
        fi, fj = bm.faces[i], bm.faces[j]
        vi = {v.index for v in fi.verts}
        if any(v.index in vi for v in fj.verts):
            continue
        reales.append((i, j))
    print("  %-22s pares BVH overlap=%d  auto-intersecciones (sin vértice común)=%d"
          % (nombre, len(pares), len(reales)))
    for i, j in reales[:12]:
        c = bm.faces[i].calc_center_median()
        print("     cara %d x cara %d  en (%.1f, %.1f, %.1f)" % (i, j, c.x, c.y, c.z))
    return reales


def _islas(bm):
    """Componentes conexas -> lista de listas de BMVert."""
    visto = set()
    islas = []
    for v0 in bm.verts:
        if v0.index in visto:
            continue
        pila, isla = [v0], []
        visto.add(v0.index)
        while pila:
            v = pila.pop()
            isla.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if o.index not in visto:
                    visto.add(o.index)
                    pila.append(o)
        islas.append(isla)
    return islas


def main():
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    spec = importlib.util.spec_from_file_location(
        "montana_rueda", os.path.join(BASE, "montana_rueda.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    coll = bpy.data.collections.new("REV_rueda")
    scene.collection.children.link(coll)
    RADIO, ESP, AB = 55.0, 70.0, 12.0
    roca = mod.build(coll, radio=RADIO, espesor=ESP, alto_base=AB, seed=0)
    veg = [c for c in roca.children if c.name.startswith("MRUEDA_veg")]
    veg = veg[0] if veg else None
    print("build ->", roca.name, "hijos", [c.name for c in roca.children])
    print("  centro_buje =", tuple(round(v, 2) for v in roca["centro_buje"]),
          " radio/esp/ab =", roca["radio"], roca["espesor"], roca["alto_base"])
    print("  materiales roca:", [m.name for m in roca.data.materials])
    print("  props mesh: no_manifold=%s tapa=%s" % (
        roca.data.get("mrueda_no_manifold"), roca.data.get("mrueda_tapa_caras")))
    # caras por material
    cnt = {}
    for p in roca.data.polygons:
        cnt[p.material_index] = cnt.get(p.material_index, 0) + 1
    print("  caras por slot:", cnt)

    coll_a = bpy.data.collections.new("REV_arco")
    scene.collection.children.link(coll_a)
    arco = mod.build_arco(coll_a, luz=16.0, alto=13.0, grosor=6.0, seed=0)
    arco.location = (300.0, 0.0, 0.0)

    # --- bbox / origen ---
    bpy.context.view_layer.update()
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for corner in roca.bound_box:
        w = roca.matrix_world @ Vector(corner)
        mins = Vector(map(min, mins, w))
        maxs = Vector(map(max, maxs, w))
    print("  bbox MRUEDA_roca min", tuple(round(v, 1) for v in mins),
          "max", tuple(round(v, 1) for v in maxs),
          "centro base XY = (%.1f, %.1f)" % ((mins.x + maxs.x) / 2, (mins.y + maxs.y) / 2))
    # anchura en el suelo
    bm = _bm_de(roca)
    bm.verts.ensure_lookup_table()
    suelo = [v.co for v in bm.verts if abs(v.co.z) < 1e-3]
    if suelo:
        print("  huella en z=0: x[%.1f, %.1f]  y[%.1f, %.1f]  (%d verts)" % (
            min(c.x for c in suelo), max(c.x for c in suelo),
            min(c.y for c in suelo), max(c.y for c in suelo), len(suelo)))
    _stats(bm, "MRUEDA_roca")
    inter_roca = _self_intersections(bm, "MRUEDA_roca")
    bvh_roca = BVHTree.FromBMesh(bm)
    bm.free()

    bma = _bm_de(arco)
    _stats(bma, "MRUEDA_arco")
    inter_arco = _self_intersections(bma, "MRUEDA_arco")
    bma.free()

    # --- vegetación: ¿flota? ---
    if veg is not None:
        bmv = _bm_de(veg)
        bmv.verts.ensure_lookup_table()
        _stats(bmv, "MRUEDA_veg")
        islas = _islas(bmv)
        flot, hund, n = 0, 0, 0
        peor = 0.0
        for isla in islas:
            c = sum((v.co for v in isla), Vector()) / len(isla)
            r = max((v.co - c).length for v in isla)
            loc, nrm, idx, dist = bvh_roca.find_nearest(c)
            n += 1
            # centro por encima de la superficie más de 0.6 r -> flota
            firmado = (c - loc).dot(nrm)
            if firmado > 0.6 * r:
                flot += 1
                peor = max(peor, firmado / r)
            if firmado < -0.9 * r:
                hund += 1
        print("  MRUEDA_veg: %d matas, flotantes=%d (peor %.2f r), enterradas=%d"
              % (n, flot, peor, hund))
        bmv.free()

    # --- túnel boolean EXACT (como hará el integrador) ---
    y_front = ESP / 2.0
    tunel = _caja("REV_tunel", (-42.0, 0.0, 4.5), (14.0, ESP + 60.0, 9.0), None,
                  scene.collection)
    tunel.hide_render = True
    tunel.display_type = "WIRE"
    md = roca.modifiers.new("REV_bool", "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.solver = "EXACT"
    md.object = tunel
    bpy.context.view_layer.update()
    bmb = _bm_de(roca, evaluado=True)
    nm_b, flip_b = _stats(bmb, "roca - tunel (EXACT)")
    inter_b = _self_intersections(bmb, "roca - tunel")
    bmb.free()

    # --- escena: suelo, carretera, luz, cámara ---
    m_suelo = _mat("REV_suelo", (0.62, 0.55, 0.40), 0.95)
    m_asf = _mat("REV_asfalto", (0.16, 0.16, 0.17), 0.85)
    me = bpy.data.meshes.new("REV_suelo")
    s = 1500.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [],
                   [(0, 1, 2, 3)])
    me.update()
    me.materials.append(m_suelo)
    suelo = bpy.data.objects.new("REV_suelo", me)
    scene.collection.objects.link(suelo)
    suelo.location = (0.0, 0.0, -0.05)
    _caja("REV_carretera", (0.0, y_front + 14.0, 0.0), (400.0, 12.0, 0.3), m_asf,
          scene.collection)
    _caja("REV_carretera_tunel", (-42.0, 0.0, 0.0), (12.0, ESP + 60.0, 0.3), m_asf,
          scene.collection)
    # coche de escala (4.5 x 1.9 x 1.4) en la carretera
    m_coche = _mat("REV_coche", (0.85, 0.08, 0.05), 0.4)
    _caja("REV_coche", (-30.0, y_front + 14.0, 0.85), (4.5, 1.9, 1.4), m_coche,
          scene.collection)

    cam_data = bpy.data.cameras.new("REV_cam")
    cam_data.clip_end = 5000.0
    cam = bpy.data.objects.new("REV_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    sun_data = bpy.data.lights.new("REV_sol", "SUN")
    sun_data.energy = 2.6
    sun_data.color = (1.0, 0.92, 0.78)
    sun_data.angle = math.radians(3.0)
    sun = bpy.data.objects.new("REV_sol", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(-55), 0.0, math.radians(-32))

    world = bpy.data.worlds.new("REV_cielo")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.50, 0.70, 0.96, 1.0)
    bg.inputs[1].default_value = 0.42
    scene.world = world

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(PREV, exist_ok=True)

    zc = RADIO - AB

    def render(png, cam_pos, objetivo, lente, sol=None):
        if sol is not None:
            sun.rotation_euler = sol
        cam_data.lens = lente
        cam.location = Vector(cam_pos)
        cam.rotation_euler = (Vector(objetivo) - cam.location).to_track_quat(
            "-Z", "Y").to_euler()
        path = os.path.join(PREV, png)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("PNG:", path, os.path.exists(path))

    # 1) resultado del túnel, desde delante-izquierda bajo
    render("mrueda_rev_tunel.png", (-150.0, y_front + 120.0, 12.0),
           (-30.0, y_front, 25.0), 35.0)
    md.show_render = False
    md.show_viewport = False
    # 2) POV desde la carretera a 1.7 m (lo que ve el jugador en AC)
    render("mrueda_rev_pov.png", (-110.0, y_front + 14.0, 1.7),
           (-5.0, y_front, zc * 0.8), 28.0)
    # 3) encuadre y luz parecidos al fotograma: desde la izquierda, alto,
    #    sol desde la izquierda-arriba-delante
    render("mrueda_rev_peli.png", (-190.0, y_front + 150.0, 75.0),
           (5.0, y_front - 10.0, 45.0), 35.0,
           sol=(math.radians(-50), 0.0, math.radians(38)))
    # 4) planta
    render("mrueda_rev_top.png", (0.0, 5.0, 420.0), (0.0, 0.0, 0.0), 40.0,
           sol=(math.radians(-55), 0.0, math.radians(-32)))

    ok = (inter_roca == [] and nm_b == 0 and inter_b == [])
    print("REVIEW_OK" if ok else "REVIEW_DEFECTOS")


try:
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
