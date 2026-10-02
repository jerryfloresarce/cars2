"""test_montana_coche_v2.py — test headless de la Montaña-Coche fósil v2.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python este_archivo

Carga montana_coche_v2 por ruta, construye el coche-montaña (R=40, W=78,
alto_base=12, z_fondo=-45) en escena vacía con tierra (z=0, x > -1.5R), mar
(z=-4) y carretera de 12 m al pie (+Y); sol cálido + cielo; renderiza EEVEE
1280x800 (view transform Standard):
  previews/montana_coche_v2_lado.png   -> coche que llega: y=+3R, x=-1.2R,
                                          z=1.2R mirando al buje delantero
  previews/montana_coche_v2_lado_lejos.png -> silueta completa desde +Y
  previews/montana_coche_v2_34.png     -> 3/4 morro-lado
  previews/montana_coche_v2_frente.png -> de frente (faros, boca, parachoques)
  previews/montana_coche_v2_zaga.png   -> desde el mar (zaga, tapa, repisas)
  previews/montana_coche_v2_tunel.png  -> túnel Boolean EXACT del integrador
                                          (cámara baja z=0.22R, lateral; caras
                                          cortadas con material oscuro)
Guarda blend/montana_coche_v2.blend. Presupuestos: roca+coche <= 90k tris,
veg <= 3k. Comprueba: malla cerrada (0 no manifold), sin auto-intersecciones,
rayos verticales del túnel (nº PAR de impactos y roca maciza en z 0.5..9.4),
zona prohibida |y| <= W/2+2.5 para x en [-1.3R, 1.5R], túnel EXACT cerrado,
vegetación apoyada, y que los detalles existen (cristal, hueso, hueco).
"""

import importlib.util
import math
import os
import sys
import time
import traceback
import warnings

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PREV = os.path.join(BASE, "previews")
BLEND = os.path.join(BASE, "blend", "montana_coche_v2.blend")
BUDGET = {"MCOCHE_roca": 90000, "MCOCHE_veg": 3000}
RADIO, ANCHO, AB, ZF = 40.0, 78.0, 12.0, -45.0


def _mat(name, color, rough=0.9):
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
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


def _plano(nombre, x0, x1, y0, y1, z, mat, coll):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [],
                   [(0, 1, 2, 3)])
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    coll.objects.link(ob)
    return ob


def _carretera(nombre, x0, x1, y, coll, m_asf, m_lin, ancho=12.0):
    largo = x1 - x0
    cx = 0.5 * (x0 + x1)
    _caja(nombre, (cx, y, 0.0), (largo, ancho, 0.3), m_asf, coll)
    for sy in (-1, 1):
        _caja(nombre + "_l", (cx, y + sy * (ancho / 2 - 0.4), 0.16),
              (largo, 0.3, 0.02), m_lin, coll)


def _tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


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


def _manifold(bm):
    nm = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bad = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    flip = sum(1 for e in bm.edges
               if len(e.link_faces) == 2 and not e.is_contiguous)
    zmin = min(v.co.z for v in bm.verts)
    return nm, bad, flip, zmin


def _auto_intersecciones(bm):
    """Pares de caras que se cruzan (BVH overlap) sin compartir vértice."""
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    reales = []
    for i, j in tree.overlap(tree):
        if i >= j:
            continue
        vi = {v.index for v in bm.faces[i].verts}
        if any(v.index in vi for v in bm.faces[j].verts):
            continue
        reales.append((i, j))
    return reales


def _impactos_verticales(tree, x, y, z0=400.0):
    """Cotas z de TODOS los impactos de un rayo vertical descendente."""
    zs = []
    origen = Vector((x, y, z0))
    d = Vector((0.0, 0.0, -1.0))
    for _ in range(200):
        loc, nrm, _i, _dist = tree.ray_cast(origen, d, 2000.0)
        if loc is None:
            break
        zs.append(loc.z)
        origen = Vector((x, y, loc.z - 1e-3))
    return zs


def _dentro(zs, z):
    """Dentro del sólido si hay un nº impar de impactos por encima."""
    return sum(1 for h in zs if h > z) % 2 == 1


def _islas_apoyadas(bmv, tree):
    """(nº islas, nº sin contacto, peor distancia) de la malla de vegetación."""
    bmv.verts.ensure_lookup_table()
    visto = set()
    n_islas = flot = 0
    peor = -1e9
    for v0 in bmv.verts:
        if v0.index in visto:
            continue
        n_islas += 1
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
        dmin = 1e9
        for v in isla:
            loc, nrm, _i, _d = tree.find_nearest(v.co)
            dmin = min(dmin, (v.co - loc).dot(nrm))
        peor = max(peor, dmin)
        if dmin > 0.3:
            flot += 1
    return n_islas, flot, peor


def main():
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    spec = importlib.util.spec_from_file_location(
        "montana_coche_v2", os.path.join(BASE, "montana_coche_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    coll = bpy.data.collections.new("ASSET_montana_coche_v2")
    scene.collection.children.link(coll)
    R, W = RADIO, ANCHO
    t0 = time.time()
    roca = mod.build(coll, radio=R, ancho=W, alto_base=AB, z_fondo=ZF, seed=0)
    print("build() -> %s hijos: %s  (%.1f s, solver %s, no-manifold %s)" % (
        roca.name, [c.name for c in roca.children], time.time() - t0,
        roca.data.get("mcoche_solver"), roca.data.get("mcoche_no_manifold")))
    print("  hubs =", [tuple(round(v, 1) for v in h) for h in roca["hubs"]],
          " huella_x =", tuple(round(v, 1) for v in roca["huella_x"]))
    print("  bbox =", tuple(round(v, 1) for v in roca["bbox"]))

    ok = True
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        t = _tris(obj)
        b = BUDGET.get(obj.name, 99999)
        flag = "OK" if t <= b else "EXCEDIDO"
        print("  tris %-14s %6d / %6d  %s" % (obj.name, t, b, flag))
        if t > b:
            ok = False
    # materiales presentes (detalles legibles): cristal, hueso, hueco
    me = roca.data
    uso = {}
    for p in me.polygons:
        uso[p.material_index] = uso.get(p.material_index, 0) + 1
    nombres = {i: (m.name if m else "?") for i, m in enumerate(me.materials)}
    print("  caras por material:", {nombres[i]: n for i, n in sorted(uso.items())})
    for idx, etiqueta in ((5, "cristal"), (4, "hueso"), (3, "hueco")):
        if uso.get(idx, 0) < 20:
            ok = False
            print("  ERROR: faltan caras de", etiqueta)

    bm = _bm_de(roca)
    bm.verts.ensure_lookup_table()
    nm, bad, flip, zmin = _manifold(bm)
    print("  MCOCHE_roca: no-manifold=%d (>2 caras: %d) winding_incoherente=%d "
          "zmin=%.2f (z_fondo=%.1f) caras=%d" % (nm, bad, flip, zmin, ZF,
                                                 len(bm.faces)))
    if nm != 0 or flip != 0 or zmin < ZF - 0.01:
        ok = False
        print("  ERROR: la malla no es cerrada/coherente con base en z_fondo")
    inter = _auto_intersecciones(bm)
    print("  MCOCHE_roca: auto-intersecciones (sin vértice común) = %d"
          % len(inter))
    for i, j in inter[:8]:
        c = bm.faces[i].calc_center_median()
        print("     cara %d x cara %d en (%.1f, %.1f, %.1f)" % (i, j, c.x, c.y, c.z))
    if inter:
        ok = False
    inv = [v.co for v in bm.verts
           if -1.3 * R <= v.co.x <= 1.5 * R and abs(v.co.y) > 0.5 * W + 2.5]
    ymax_p = max((abs(c.y) for c in inv), default=0.0)
    print("  zona prohibida (x en [-1.3R,1.5R], |y| > W/2+2.5): %d vértices "
          "(|y| max %.1f)" % (len(inv), ymax_p))
    if inv:
        ok = False
    tree = BVHTree.FromBMesh(bm)
    for (x, y, exigido) in ((-0.65 * R, 0.0, True), (-0.65 * R, 0.45 * W, True),
                            (-0.65 * R, -0.45 * W, True),
                            (-0.9 * R, 0.45 * W, False)):
        zs = _impactos_verticales(tree, x, y)
        par = len(zs) % 2 == 0
        macizo = all(_dentro(zs, z) for z in (0.5, 5.0, 9.4))
        entra = max(zs) if zs else None
        print("  rayo (%.1f, %.1f): %d impactos (%s), entra en z=%s, "
              "macizo z 0.5..9.4: %s" % (x, y, len(zs),
                                         "par" if par else "IMPAR",
                                         None if entra is None else round(entra, 1),
                                         macizo))
        if not par or (exigido and (not macizo or entra is None or entra < 15.0)):
            ok = False
            print("  ERROR: el túnel no atravesaría roca maciza aquí")
    zs = _impactos_verticales(tree, -1.7 * R, 0.0)
    libre = not _dentro(zs, 0.72 * R) and _dentro(zs, 0.3 * R)
    print("  arco (x=-1.7R, y=0): impactos %s -> aire en 0.72R y roca en 0.3R: %s"
          % ([round(z, 1) for z in zs], libre))
    # silueta: cumbre del techo y faros por delante del morro
    zmax = max(v.co.z for v in bm.verts)
    xmax = max(v.co.x for v in bm.verts)
    print("  cumbre z=%.1f (%.2fR)  morro x=%.1f (%.2fR)" % (zmax, zmax / R,
                                                             xmax, xmax / R))
    bm.free()

    veg = [c for c in roca.children if c.name == "MCOCHE_veg"]
    if veg:
        bmv = _bm_de(veg[0])
        n_islas, flot, peor = _islas_apoyadas(bmv, tree)
        print("  MCOCHE_veg: %d islas, sin contacto=%d (peor %.2f m)"
              % (n_islas, flot, peor))
        bmv.free()
        if flot:
            ok = False

    # --- escenario: tierra, mar, carretera, coche de escala ---
    m_tierra = _mat("MAT_TEST_tierra", (0.60, 0.53, 0.38), 0.95)
    m_mar = _mat("MAT_TEST_mar", (0.05, 0.42, 0.55), 0.25)
    m_asf = _mat("MAT_TEST_asfalto", (0.16, 0.16, 0.17), 0.85)
    m_lin = _mat("MAT_TEST_linea", (0.92, 0.92, 0.88), 0.7)
    _plano("TEST_tierra", -1.5 * R, 1500.0, -1500.0, 1500.0, -0.05, m_tierra,
           scene.collection)
    _plano("TEST_mar", -1500.0, 1500.0, -1500.0, 1500.0, -4.0, m_mar,
           scene.collection)
    Y_ROAD = 0.5 * W + 14.0
    _carretera("TEST_carretera", -1.45 * R, 500.0, Y_ROAD, scene.collection,
               m_asf, m_lin)
    m_coche = _mat("MAT_TEST_coche", (0.85, 0.08, 0.05), 0.4)
    _caja("TEST_coche", (30.0, Y_ROAD, 0.85), (4.5, 1.9, 1.4), m_coche,
          scene.collection)

    # --- túnel Boolean EXACT (integrador): caja 21 x 9.5 a lo largo de Y ---
    # el prisma lleva un material oscuro que el Boolean TRANSFIERE a las
    # caras cortadas (como el revestimiento del túnel del integrador): así la
    # boca se lee como agujero y no como caja clara iluminada por el cielo
    m_tun = _mat("MAT_TEST_tunel", (0.045, 0.038, 0.032), 0.95)
    tunel = _caja("TEST_tunel", (-0.65 * R, 0.0, 4.75), (21.0, W + 80.0, 9.5),
                  m_tun, scene.collection)
    tunel.hide_render = True
    tunel.display_type = "WIRE"
    md = roca.modifiers.new("TEST_bool", "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.solver = "EXACT"
    md.object = tunel
    md.material_mode = "TRANSFER"
    bpy.context.view_layer.update()
    bmb = _bm_de(roca, evaluado=True)
    nm_b, bad_b, flip_b, _zb = _manifold(bmb)
    tris_b = sum(len(f.verts) - 2 for f in bmb.faces)
    dentro = sum(1 for v in bmb.verts
                 if abs(v.co.x + 0.65 * R) < 10.51 and 0.0 <= v.co.z < 9.51
                 and abs(v.co.y) < 0.5 * W + 3.0)
    print("  roca - túnel (EXACT): tris=%d no-manifold=%d winding=%d "
          "vértices en el túnel=%d" % (tris_b, nm_b, flip_b, dentro))
    bmb.free()
    if nm_b != 0 or dentro < 8:
        ok = False
        print("  ERROR: el túnel no perfora limpiamente la roca")
    return ok, roca, md, tunel


def render(roca, md, tunel):
    """Cámara, sol cálido + cielo azul, EEVEE 1280x800 Standard; una toma
    por vista (la del túnel con el Boolean EXACT aplicado)."""
    scene = bpy.context.scene
    R, W = RADIO, ANCHO
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.clip_end = 6000.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new("TEST_sol", "SUN")
    sun_data.energy = 2.4
    sun_data.color = (1.0, 0.92, 0.78)
    sun_data.angle = math.radians(3.0)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(-52), 0.0, math.radians(-38))
    world = bpy.data.worlds.new("TEST_cielo")
    if world.node_tree is None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
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
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(PREV, exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    zc = R - AB
    xc = -1.7 * R
    shots = [
        # cámara BAJA (z=0.22R, objetivo 0.12R dentro de la boca) y desplazada
        # a +X para ver una pared interior en sombra: el túnel se lee como
        # agujero y no como caja clara
        ("montana_coche_v2_tunel.png", Vector((0.45 * R, 0.5 * W + 2.4 * R, 0.22 * R)),
         Vector((-0.65 * R, 0.5 * W - 0.3 * R, 0.12 * R)), 45.0),
        ("montana_coche_v2_lado.png", Vector((-1.2 * R, 3.0 * R, 1.2 * R)),
         Vector((0.0, 0.5 * W, zc)), 24.0),
        ("montana_coche_v2_lado_lejos.png", Vector((-1.5 * R, 0.5 * W + 6.5 * R, 1.6 * R)),
         Vector((xc, 0.5 * W, 1.25 * R)), 35.0),
        ("montana_coche_v2_34.png", Vector((5.2 * R, 0.5 * W + 4.6 * R, 2.4 * R)),
         Vector((xc + 0.3 * R, 0.3 * W, 1.1 * R)), 35.0),
        ("montana_coche_v2_zaga.png", Vector((-9.0 * R, -0.5 * W - 2.6 * R, 1.5 * R)),
         Vector((-4.2 * R, -0.1 * W, 1.0 * R)), 35.0),
        ("montana_coche_v2_frente.png", Vector((6.0 * R, 0.5 * W + 0.8 * R, 1.5 * R)),
         Vector((0.4 * R, 0.0, 1.2 * R)), 40.0),
    ]
    for png, pos, objetivo, lente in shots:
        cam_data.lens = lente
        cam.location = pos
        cam.rotation_euler = (objetivo - pos).to_track_quat("-Z", "Y").to_euler()
        path = os.path.join(PREV, png)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("PNG:", path, os.path.exists(path))
        if png == "montana_coche_v2_tunel.png":
            roca.modifiers.remove(md)
            bpy.data.objects.remove(tunel, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("BLEND:", BLEND, os.path.exists(BLEND))


try:
    ok, roca, md, tunel = main()
    render(roca, md, tunel)
    print("TEST_OK" if ok else "TEST_FALLO")
except Exception:
    traceback.print_exc()
    sys.exit(1)
