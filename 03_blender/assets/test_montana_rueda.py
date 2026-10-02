"""test_montana_rueda.py — test headless de la Montaña-Rueda (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python este_archivo

Carga montana_rueda por ruta, construye el macizo-rueda y el arco en escena
vacía (suelo arenoso + carretera de 12 m de ancho para escala), sol cálido +
cielo suave, y renderiza 7 vistas EEVEE 1280x720:
  previews/mrueda_frente.png   -> frontal a ~250 m (la rueda se lee)
  previews/mrueda_34.png       -> 3/4 mostrando pared, ceja y lomo
  previews/mrueda_trasera.png  -> la espalda del macizo (cresta)
  previews/mrueda_detalle.png  -> primer plano de buje y radios
  previews/mrueda_pov.png      -> desde la carretera a 1.7 m (vista AC)
  previews/mrueda_tunel.png    -> túnel Boolean EXACT por el espolón
  previews/mrueda_arco.png     -> el arco con carretera de 12 m por debajo
Guarda blend/montana_rueda.blend. Presupuestos: roca <= 40k tris, veg <= 2k,
arco <= 6k. Comprueba: MRUEDA_roca cerrada (0 aristas no manifold), sin
auto-intersecciones (BVH), HUELLA en z=0 = lo más ancho (sin socavar), túnel
Boolean EXACT cerrado, gálibo del arco libre, arco sin auto-intersecciones.
"""

import importlib.util
import math
import os
import sys
import traceback
import warnings

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PREV = os.path.join(BASE, "previews")
BLEND = os.path.join(BASE, "blend", "montana_rueda.blend")
BUDGET = {"MRUEDA_roca": 40000, "MRUEDA_veg": 2000, "MRUEDA_arco": 6000,
          "MRUEDA_arco_veg": 1000}


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


def _carretera(nombre, centro, largo, eje, coll, m_asf, m_lin, ancho=12.0):
    """Losa de asfalto de `ancho` m con dos líneas blancas de borde."""
    if eje == "y":
        _caja(nombre, centro, (ancho, largo, 0.3), m_asf, coll)
        for sx in (-1, 1):
            _caja(nombre + "_l", (centro[0] + sx * (ancho / 2 - 0.4), centro[1],
                                  centro[2] + 0.16), (0.3, largo, 0.02), m_lin, coll)
    else:
        _caja(nombre, centro, (largo, ancho, 0.3), m_asf, coll)
        for sy in (-1, 1):
            _caja(nombre + "_l", (centro[0], centro[1] + sy * (ancho / 2 - 0.4),
                                  centro[2] + 0.16), (largo, 0.3, 0.02), m_lin, coll)


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

    coll = bpy.data.collections.new("ASSET_montana_rueda")
    scene.collection.children.link(coll)
    RADIO, ESP, AB = 55.0, 70.0, 12.0
    roca = mod.build(coll, radio=RADIO, espesor=ESP, alto_base=AB, seed=0)
    print("build() ->", roca.name, "hijos:", [c.name for c in roca.children])
    print("  centro_buje =", tuple(round(v, 2) for v in roca["centro_buje"]),
          " y_pared = %.2f" % roca["y_pared"],
          " huella_x =", tuple(round(v, 1) for v in roca["huella_x"]),
          " espolon =", tuple(round(v, 1) for v in roca["espolon"]))

    coll_a = bpy.data.collections.new("ASSET_mrueda_arco")
    scene.collection.children.link(coll_a)
    ARCO_X = 420.0
    arco = mod.build_arco(coll_a, luz=16.0, alto=13.0, grosor=6.0, seed=0)
    arco.location = (ARCO_X, 0.0, 0.0)
    print("build_arco() ->", arco.name, "hijos:", [c.name for c in arco.children])

    # --- presupuesto de tris ---
    ok = True
    for obj in list(coll.objects) + list(coll_a.objects):
        if obj.type != "MESH":
            continue
        t = _tris(obj)
        b = BUDGET.get(obj.name, 99999)
        flag = "OK" if t <= b else "EXCEDIDO"
        print("  tris %-18s %6d / %6d  %s" % (obj.name, t, b, flag))
        if t > b:
            ok = False

    # --- manifold, winding, auto-intersecciones, huella ---
    bm = _bm_de(roca)
    bm.verts.ensure_lookup_table()
    nm, bad, flip, zmin = _manifold(bm)
    print("  MRUEDA_roca: no-manifold=%d (>2 caras: %d) winding_incoherente=%d "
          "zmin=%.4f tapa=%s" % (nm, bad, flip, zmin,
                                 roca.data.get("mrueda_tapa_caras")))
    if nm != 0 or zmin < -1e-3 or flip != 0:
        ok = False
        print("  ERROR: la roca no es una malla cerrada coherente apoyada en z=0")
    inter = _auto_intersecciones(bm)
    print("  MRUEDA_roca: auto-intersecciones (sin vértice común) = %d" % len(inter))
    for i, j in inter[:8]:
        c = bm.faces[i].calc_center_median()
        print("     cara %d x cara %d en (%.1f, %.1f, %.1f)" % (i, j, c.x, c.y, c.z))
    if inter:
        ok = False
    suelo = [v.co for v in bm.verts if abs(v.co.z) < 1e-3]
    bajo10 = [v.co for v in bm.verts if v.co.z < 10.0]
    x_suelo = max(abs(c.x) for c in suelo)
    x_bajo10 = max(abs(c.x) for c in bajo10)
    vmax = max(bm.verts, key=lambda v: abs(v.co.x))
    print("  huella z=0: x[%.1f, %.1f] y[%.1f, %.1f]; max|x| z<10 = %.1f; "
          "max|x| global = %.1f en z=%.1f" % (
              min(c.x for c in suelo), max(c.x for c in suelo),
              min(c.y for c in suelo), max(c.y for c in suelo),
              x_bajo10, abs(vmax.co.x), vmax.co.z))
    if x_bajo10 - x_suelo > 2.5:
        ok = False
        print("  ERROR: base socavada (max|x| bajo 10 m excede la huella en "
              "%.1f m)" % (x_bajo10 - x_suelo))
    if abs(vmax.co.x) - x_suelo > 2.5:
        ok = False
        print("  ERROR: el macizo vuela %.1f m sobre su huella (z=%.1f)"
              % (abs(vmax.co.x) - x_suelo, vmax.co.z))
    y_pared_max = max(v.co.y for v in bm.verts if v.co.x > -0.9 * RADIO)
    z_max = max(v.co.z for v in bm.verts)
    print("  pared (sin espolón): y max = %.1f; cumbre z = %.1f (%.2f R)"
          % (y_pared_max, z_max, z_max / RADIO))
    tree_roca = BVHTree.FromBMesh(bm)
    bm.free()

    # --- vegetación: cada isla (mata o pino) apoyada en la roca ---
    veg = [c for c in roca.children if c.name == "MRUEDA_veg"]
    if veg:
        bmv = _bm_de(veg[0])
        bmv.verts.ensure_lookup_table()
        islas = _islas(bmv)
        flot = 0
        peor = -1e9
        peor_c = -1e9
        for isla in islas:
            # contacto: algún vértice de la isla toca o se hunde en la roca
            dmin = 1e9
            for v in isla:
                loc, nrm, _i, _d = tree_roca.find_nearest(v.co)
                dmin = min(dmin, (v.co - loc).dot(nrm))
            peor = max(peor, dmin)
            if dmin > 0.3:
                flot += 1
            # y el centroide no se aleja más de 0.6 r (criterio del revisor)
            c = sum((v.co for v in isla), Vector()) / len(isla)
            r = max((v.co - c).length for v in isla)
            loc, nrm, _i, _d = tree_roca.find_nearest(c)
            peor_c = max(peor_c, (c - loc).dot(nrm) / r)
        print("  MRUEDA_veg: %d islas (matas+pinos), sin contacto=%d (peor %.2f m); "
              "centroide peor %.2f r" % (len(islas), flot, peor, peor_c))
        bmv.free()
        if flot or peor_c > 0.6:
            ok = False

    bma = _bm_de(arco)
    nm_a, bad_a, flip_a, _z = _manifold(bma)
    inter_a = _auto_intersecciones(bma)
    print("  MRUEDA_arco: no-manifold=%d winding_incoherente=%d "
          "auto-intersecciones=%d" % (nm_a, flip_a, len(inter_a)))
    bma.free()
    if nm_a != 0 or inter_a:
        ok = False

    # --- gálibo del arco: ningún vértice dentro de la caja libre ---
    inv = 0
    for v in arco.data.vertices:
        if abs(v.co.x) < 8.0 - 1e-3 and 0.0 < v.co.z < 13.0 - 1e-3:
            inv += 1
    print("  gálibo arco 16x13: vértices invasores = %d" % inv)
    if inv:
        ok = False

    # --- bbox del macizo ---
    bpy.context.view_layer.update()
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
    centro = (mins + maxs) / 2.0
    dims = maxs - mins
    print("bbox roca+veg: min", tuple(round(v, 1) for v in mins),
          "max", tuple(round(v, 1) for v in maxs),
          "dims", tuple(round(v, 1) for v in dims))
    zc = RADIO - AB
    y_front = ESP / 2.0
    y_hub = roca["centro_buje"][1]

    # --- suelo + carreteras de escala ---
    m_suelo = _mat("MAT_TEST_suelo", (0.62, 0.55, 0.40), 0.95)
    m_asf = _mat("MAT_TEST_asfalto", (0.16, 0.16, 0.17), 0.85)
    m_lin = _mat("MAT_TEST_linea", (0.92, 0.92, 0.88), 0.7)
    me = bpy.data.meshes.new("TEST_suelo")
    s = 1500.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [],
                   [(0, 1, 2, 3)])
    me.update()
    me.materials.append(m_suelo)
    suelo_ob = bpy.data.objects.new("TEST_suelo", me)
    scene.collection.objects.link(suelo_ob)
    suelo_ob.location = (0.0, 0.0, -0.05)
    # carretera al pie de la rueda (a lo largo de X, atraviesa el espolón por
    # el túnel) y bajo el arco (Y)
    Y_ROAD = y_front + 14.0
    _carretera("TEST_carretera", (0.0, Y_ROAD, 0.0), 400.0, "x",
               scene.collection, m_asf, m_lin)
    _carretera("TEST_carretera_arco", (ARCO_X, 0.0, 0.0), 120.0, "y",
               scene.collection, m_asf, m_lin)
    # coche de escala (4.5 x 1.9 x 1.4) en la carretera
    m_coche = _mat("MAT_TEST_coche", (0.85, 0.08, 0.05), 0.4)
    _caja("TEST_coche", (-30.0, Y_ROAD, 0.85), (4.5, 1.9, 1.4), m_coche,
          scene.collection)

    # --- túnel Boolean EXACT por el espolón (simula al integrador) ---
    tunel = _caja("TEST_tunel", (-68.0, Y_ROAD, 4.5), (56.0, 14.0, 9.0), None,
                  scene.collection)
    tunel.hide_render = True
    tunel.display_type = "WIRE"
    md = roca.modifiers.new("TEST_bool", "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.solver = "EXACT"
    md.object = tunel
    bpy.context.view_layer.update()
    bmb = _bm_de(roca, evaluado=True)
    nm_b, bad_b, flip_b, _zb = _manifold(bmb)
    inter_b = _auto_intersecciones(bmb)
    tris_b = sum(len(f.verts) - 2 for f in bmb.faces)
    # ¿el túnel realmente atraviesa roca? vértices nuevos dentro de la caja
    dentro = sum(1 for v in bmb.verts
                 if -96.0 < v.co.x < -40.0 and abs(v.co.y - Y_ROAD) < 7.01
                 and 0.0 < v.co.z < 9.01)
    print("  roca - túnel (EXACT): tris=%d no-manifold=%d winding=%d "
          "auto-intersecciones=%d vértices en el túnel=%d" % (
              tris_b, nm_b, flip_b, len(inter_b), dentro))
    bmb.free()
    if nm_b != 0 or inter_b or dentro < 8:
        ok = False
        print("  ERROR: el túnel no perfora limpiamente el espolón")

    # --- cámara ---
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.clip_end = 5000.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    # --- sol cálido desde delante-derecha-arriba + cielo suave ---
    sun_data = bpy.data.lights.new("TEST_sol", "SUN")
    sun_data.energy = 2.4
    sun_data.color = (1.0, 0.92, 0.78)
    sun_data.angle = math.radians(3.0)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(-55), 0.0, math.radians(-32))

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
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(PREV, exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    # (png, dirección cámara->objetivo invertida, lente, distancia, objetivo)
    shots = [
        ("mrueda_tunel.png", Vector((-0.95, 1.0, 0.16)), 35.0, 150.0,
         Vector((-58.0, Y_ROAD, 14.0))),
        ("mrueda_frente.png", Vector((0.10, 1.0, 0.07)), 42.0, 250.0,
         Vector((0.0, y_front, zc + 14.0))),
        ("mrueda_34.png", Vector((1.0, 0.62, 0.26)), 40.0, None,
         Vector((centro.x, centro.y, centro.z * 0.92))),
        ("mrueda_trasera.png", Vector((-0.55, -1.0, 0.30)), 40.0, None,
         Vector((centro.x, centro.y, centro.z * 0.85))),
        ("mrueda_detalle.png", Vector((0.30, 1.0, 0.22)), 50.0, 78.0,
         Vector((0.0, y_hub, zc))),
        ("mrueda_pov.png", None, 28.0, None, None),
        ("mrueda_arco.png", Vector((0.85, 1.0, 0.42)), 40.0, 66.0,
         Vector((ARCO_X, 0.0, 7.5))),
    ]
    for png, direccion, lente, dist, objetivo in shots:
        cam_data.lens = lente
        if png == "mrueda_pov.png":
            # desde la carretera, a la altura de un coche (vista de AC)
            cam.location = Vector((118.0, Y_ROAD, 1.7))
            objetivo = Vector((-5.0, y_front, zc * 0.85))
        else:
            direccion = direccion.normalized()
            if dist is None:
                hfov = 2.0 * math.atan(cam_data.sensor_width / 2.0 / lente)
                vfov = 2.0 * math.atan(cam_data.sensor_width * 720.0 / 1280.0 /
                                       2.0 / lente)
                dist = max(dims.z * 0.66 / math.tan(vfov / 2.0),
                           max(dims.x, dims.y) * 0.62 / math.tan(hfov / 2.0))
            cam.location = objetivo + direccion * dist
        cam.rotation_euler = (objetivo - cam.location).to_track_quat(
            "-Z", "Y").to_euler()
        path = os.path.join(PREV, png)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("PNG:", path, os.path.exists(path))
        if png == "mrueda_tunel.png":
            # el resto de vistas muestran el asset puro (sin boolean)
            roca.modifiers.remove(md)
            bpy.data.objects.remove(tunel, do_unlink=True)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("BLEND:", BLEND, os.path.exists(BLEND))
    print("TEST_OK" if ok else "TEST_FALLO")


try:
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
