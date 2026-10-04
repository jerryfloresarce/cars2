"""test_montana_mclaren.py — test headless del McLaren de piedra (ronda 15).

Ejecutar:
"C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background
  --factory-startup --python este_archivo

Carga montana_mclaren por ruta, construye el coche-cerro (R=26, W=135,
alto_base=12, z_fondo=-45, lado_visible=-1, enterrado='zaga') en escena
vacia con suelo (z=-0.05), carretera de 12 m a lo largo de Y en x=-0.65R
(entra por la rueda delantera) y un coche rojo de escala; sol + cielo;
renderiza EEVEE 1280x800 (Standard):
  previews/montana_mclaren_tunel.png    -> tunel Boolean EXACT del integrador
  previews/montana_mclaren_pista.png    -> desde la pista: camara a 1.5 m en
                                           y = -ancho/2 - 30 mirando a la rueda
  previews/montana_mclaren_34.png       -> 3/4 delantero (lado visible)
  previews/montana_mclaren_lateral.png  -> lateral completo del lado visible
  previews/montana_mclaren_aereo.png    -> aereo
  previews/montana_mclaren_trasera.png  -> desde atras: zaga fundida en la roca
  previews/montana_mclaren_frente.png   -> de frente (faros, boca, splitter)
  previews/montana_mclaren_morro_*.png  -> variante enterrado='morro' (lateral, 3/4)
SITIO (si existe assets/_geom_snapshot_mclaren.json o ../geometria_3d.json,
via encaje_mclaren): coloca cada configuracion en el marco local que usa
integrar_escena.zona_tunel y cuenta muestras de pista bajo la huella (fuera
del tunel de la rueda), exposicion sobre el terreno T1 y mar bajo la huella.
Deben dar 0 colisiones las orientaciones A (+X local = -n, morro tierra
adentro); la orientacion B del plan (morro al mar) choca con la horquilla
(curvas 4-6) y se imprime como ESPERADO. Previews del sitio (terreno T1 +
mar + calzada reales): previews/montana_mclaren_sitio_<cfg>_<vista>.png.
Guarda blend/montana_mclaren.blend. Imprime vertices, no-manifold (0), tiempo.
Comprueba: malla cerrada, auto-intersecciones, zona prohibida, rayos del
tunel (impactos pares y roca maciza), coche macizo en x=-3R, tunel EXACT
cerrado, vegetacion apoyada, materiales de detalle, cresta > techo,
variantes (morro, largo_macizo=0, talud/ancho por lado, R=40/W=78).
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

BASE = "E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender/assets"
PREV = os.path.join(BASE, "previews")
BLEND = os.path.join(BASE, "blend", "montana_mclaren.blend")
BUDGET = {"MCOCHE_roca": 220000, "MCOCHE_veg": 3500}
RADIO, ANCHO, AB, ZF, LV = 26.0, 135.0, 12.0, -45.0, -1.0
# configuracion recomendada para el sitio (orientacion A, morro en la ladera T1)
KW_MORRO_SITIO = dict(enterrado="morro", alto_montana=65.0, largo_macizo=4.8,
                      talud_deg=(38.0, 52.0))
KW_AMBOS_SITIO = dict(enterrado="ambos", alto_montana=(83.2, 65.0), largo_macizo=(14.5, 4.8),
                      talud_deg=(38.0, 52.0))
# (nombre, sx, ds, kwargs): sx=-1 -> +X local = -n (integrador actual, lv=-1)
CFG_SITIO = [
    ("A_zaga", -1, 0.0, dict(enterrado="zaga")),
    ("A_morro", -1, 0.0, dict(KW_MORRO_SITIO)),
    ("A_ambos", -1, 0.0, dict(KW_AMBOS_SITIO)),
    ("B_zaga_plan", 1, 0.0, dict(enterrado="zaga")),
    ("B_sin_macizo", 1, 0.0, dict(largo_macizo=0.0)),
]
ESPERA_COLISION = ("B_zaga_plan", "B_sin_macizo")


def _cargar(nombre):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(BASE, nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def _carretera_y(nombre, x, y0, y1, coll, m_asf, m_lin, ancho=12.0):
    largo = abs(y1 - y0)
    cy = 0.5 * (y0 + y1)
    _caja(nombre, (x, cy, 0.0), (ancho, largo, 0.3), m_asf, coll)
    for sx in (-1, 1):
        _caja(nombre + "_l", (x + sx * (ancho / 2 - 0.4), cy, 0.16),
              (0.3, largo, 0.02), m_lin, coll)


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
    """Pares de caras que se cruzan (BVH overlap) sin compartir vertice."""
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
    return sum(1 for h in zs if h > z) % 2 == 1


def _islas_apoyadas(bmv, tree):
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


def main(mod):
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    coll = bpy.data.collections.new("ASSET_montana_mclaren")
    scene.collection.children.link(coll)
    R, W = RADIO, ANCHO
    zc = R - AB
    t0 = time.time()
    roca = mod.build(coll, radio=R, ancho=W, alto_base=AB, z_fondo=ZF, seed=0,
                     lado_visible=LV, enterrado="zaga")
    dt = time.time() - t0
    print("build() -> %s hijos: %s  (%.1f s, solver %s, no-manifold %s)" % (
        roca.name, [c.name for c in roca.children], dt,
        roca.data.get("mcoche_solver"), roca.data.get("mcoche_no_manifold")))
    print("  vertices=%d caras=%d tiempo=%.1f s" % (len(roca.data.vertices),
                                                     len(roca.data.polygons), dt))
    print("  hubs =", [tuple(round(v, 1) for v in h) for h in roca["hubs"]],
          " huella_x =", tuple(round(v, 1) for v in roca["huella_x"]))
    print("  bbox =", tuple(round(v, 1) for v in roca["bbox"]),
          " enterrado =", roca["enterrado"], " alto_montana =", roca["alto_montana"],
          " largo_macizo =", roca["largo_macizo"], " talud =", tuple(roca["talud_deg"]))

    ok = True
    for obj in coll.objects:
        if obj.type != "MESH":
            continue
        t = _tris(obj)
        b = BUDGET.get(obj.name, 99999)
        print("  tris %-14s %7d / %7d  %s" % (obj.name, t, b, "OK" if t <= b else "EXCEDIDO"))
        if t > b:
            ok = False
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
    n_osc, n_tot = uso.get(2, 0), sum(uso.values())
    print("  bandas oscuras: %.1f %% de las caras (antes ~37 %% con el patron de la v2)"
          % (100.0 * n_osc / max(n_tot, 1)))

    bm = _bm_de(roca)
    bm.verts.ensure_lookup_table()
    nm, bad, flip, zmin = _manifold(bm)
    print("  MCOCHE_roca: no-manifold=%d (>2 caras: %d) winding_incoherente=%d "
          "zmin=%.2f (z_fondo=%.1f)" % (nm, bad, flip, zmin, ZF))
    if nm != 0 or flip != 0 or zmin < ZF - 0.01:
        ok = False
        print("  ERROR: la malla no es cerrada/coherente con base en z_fondo")
    cortas = sum(1 for e in bm.edges if e.calc_length() < 1e-3)
    bm.faces.ensure_lookup_table()
    visto = set()
    comps = []
    for f0 in bm.faces:
        if f0.index in visto:
            continue
        pila, n_f = [f0], 0
        visto.add(f0.index)
        while pila:
            f = pila.pop()
            n_f += 1
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in visto:
                        visto.add(g.index)
                        pila.append(g)
        comps.append(n_f)
    print("  aristas < 1 mm: %d   cascaras: %d (caras por cascara: %s)" % (
        cortas, len(comps), sorted(comps, reverse=True)[:8]))
    if len(comps) != 1 or cortas:
        ok = False
        print("  ERROR: la malla debe ser UNA cascara sin aristas degeneradas")
    inter = _auto_intersecciones(bm)
    print("  MCOCHE_roca: auto-intersecciones (sin vertice comun) = %d" % len(inter))
    for i, j in inter[:8]:
        c = bm.faces[i].calc_center_median()
        print("     cara %d x cara %d en (%.1f, %.1f, %.1f)" % (i, j, c.x, c.y, c.z))
    if inter:
        ok = False
    inv = [v.co for v in bm.verts
           if -1.3 * R <= v.co.x <= 1.5 * R and abs(v.co.y) > 0.5 * W + 2.5]
    print("  zona prohibida (x en [-1.3R,1.5R], |y| > W/2+2.5): %d vertices (|y| max %.1f)"
          % (len(inv), max((abs(c.y) for c in inv), default=0.0)))
    if inv:
        ok = False
    tree = BVHTree.FromBMesh(bm)
    for (x, y) in ((-0.65 * R, 0.0), (-0.65 * R, 0.45 * W), (-0.65 * R, -0.45 * W)):
        zs = _impactos_verticales(tree, x, y)
        par = len(zs) % 2 == 0
        macizo = all(_dentro(zs, z) for z in (0.5, 5.0, 9.4))
        entra = max(zs) if zs else None
        print("  rayo (%.1f, %.1f): %d impactos (%s), entra en z=%s, macizo z 0.5..9.4: %s"
              % (x, y, len(zs), "par" if par else "IMPAR",
                 None if entra is None else round(entra, 1), macizo))
        if not par or not macizo or entra is None or entra < 15.0:
            ok = False
            print("  ERROR: el tunel no atravesaria roca maciza aqui")
    zs = _impactos_verticales(tree, -3.0 * R, 0.0)
    solido = all(_dentro(zs, z) for z in (0.5, 10.0, 30.0, zc + 1.8 * R))
    print("  coche macizo (x=-3R, y=0): impactos %s -> solido hasta el techo: %s"
          % ([round(z, 1) for z in zs], solido))
    if not solido:
        ok = False
    zmax = max(v.co.z for v in bm.verts)
    xmax = max(v.co.x for v in bm.verts)
    xmin = min(v.co.x for v in bm.verts)
    techo = max(v.co.z for v in bm.verts if -6.0 * R < v.co.x < -3.0 * R and abs(v.co.y) < 0.2 * W)
    cresta = max(v.co.z for v in bm.verts if v.co.x < -10.5 * R)
    print("  cumbre z=%.1f (%.2fR)  techo z=%.1f (%.2fR)  cresta tras la cola z=%.1f (%.2fR)"
          "  morro x=%.1f (%.2fR)  cola x=%.1f (%.2fR)"
          % (zmax, zmax / R, techo, techo / R, cresta, cresta / R, xmax, xmax / R, xmin, xmin / R))
    if cresta < techo + 2.0:
        ok = False
        print("  ERROR: la cresta del macizo debe superar el techo (coche que emerge del cerro)")
    # la roca cubre media rueda trasera (lame el flanco) pero no la cabina
    z_roca_rueda = max((v.co.z for v in bm.verts
                        if abs(v.co.x + 7.6 * R) < 0.3 * R and 0.5 * W + 1.0 < abs(v.co.y) < 0.5 * W + 6.0),
                       default=-1.0)
    print("  roca junto a la rueda trasera (|y| = W/2 + 1..6): z max %.1f (buje %.1f)" % (z_roca_rueda, zc))
    if not (0.6 * zc < z_roca_rueda < zc + 1.2 * R):
        ok = False
        print("  ERROR: el macizo debe lamer la rueda trasera entre media rueda y la cintura")
    bm.free()

    veg = [c for c in roca.children if c.name == "MCOCHE_veg"]
    if veg:
        bmv = _bm_de(veg[0])
        n_islas, flot, peor = _islas_apoyadas(bmv, tree)
        print("  MCOCHE_veg: %d islas, sin contacto=%d (peor %.2f m)" % (n_islas, flot, peor))
        bmv.free()
        if flot:
            ok = False
    return ok, roca, coll


def variantes(mod):
    """Pruebas de humo: morro (config del sitio), sin macizo, macizo corto
    con talud/ancho por lado y otra escala (R=40, W=78, lado +1). Devuelve
    (ok, roca_morro) (la variante morro se conserva para los previews)."""
    scene = bpy.context.scene
    R, W = RADIO, ANCHO
    ok = True
    guardado = None
    casos = [
        ("morro_sitio", dict(radio=R, ancho=W, alto_base=AB, z_fondo=ZF, seed=3, lado_visible=LV,
                             **KW_MORRO_SITIO)),
        ("sin_macizo", dict(radio=R, ancho=W, alto_base=AB, z_fondo=ZF, seed=5, lado_visible=LV,
                            largo_macizo=0.0)),
        ("zaga_corto", dict(radio=R, ancho=W, alto_base=AB, z_fondo=ZF, seed=7, lado_visible=LV,
                            enterrado="zaga", largo_macizo=11.5, talud_deg=(38.0, 55.0),
                            ancho_macizo=(1.0, 0.75), alto_montana=70.0)),
        ("R40_W78", dict(radio=40.0, ancho=78.0, alto_base=12.0, z_fondo=-50.0, seed=11,
                         lado_visible=1.0, enterrado="zaga", alto_montana=120.0)),
        ("ambos_sitio", dict(radio=R, ancho=W, alto_base=AB, z_fondo=ZF, seed=0, lado_visible=LV,
                             **KW_AMBOS_SITIO)),
    ]
    for nombre, kw in casos:
        coll2 = bpy.data.collections.new("TMP_" + nombre)
        scene.collection.children.link(coll2)
        t1 = time.time()
        r2 = mod.build(coll2, con_vegetacion=False, **kw)
        bm2 = _bm_de(r2)
        nm2, _b2, flip2, _z2 = _manifold(bm2)
        pares2 = _auto_intersecciones(bm2)
        inter2 = len(pares2)
        for i, j in pares2[:3]:
            c = bm2.faces[i].calc_center_median()
            print("     auto-interseccion en (%.1f, %.1f, %.1f) = (%.2fR, %.2fR)" % (
                c.x, c.y, c.z, c.x / kw["radio"], c.z / kw["radio"]))
        zmax2 = max(v.co.z for v in bm2.verts)
        bm2.free()
        lg = r2["largo_macizo"]
        lg = tuple(round(v, 1) for v in lg) if hasattr(lg, "__len__") else round(lg, 1)
        print("  humo %-12s R=%.0f: vertices=%d no-manifold=%d winding=%d auto-int=%d zmax=%.1f "
              "largo=%s (%.1f s) bbox x %s"
              % (nombre, kw["radio"], len(r2.data.vertices), nm2, flip2, inter2, zmax2,
                 lg, time.time() - t1,
                 tuple(round(v, 1) for v in (r2["bbox"][0], r2["bbox"][3]))))
        if nm2 != 0 or flip2 != 0 or inter2 != 0:
            ok = False
            print("  ERROR: variante no manifold o con auto-intersecciones")
        if nombre == "sin_macizo" and (r2["largo_macizo"] != 0.0 or r2["bbox"][0] < -10.3 * R):
            ok = False
            print("  ERROR: sin macizo la malla debe acabar en la cola")
        if nombre == "zaga_corto" and abs(r2["bbox"][0] + 11.5 * R) > 0.3 * R:
            ok = False
            print("  ERROR: largo_macizo=11.5 debe acabar en x=-11.5R")
        if nombre == "ambos_sitio" and (tuple(r2["largo_macizo"]) != (14.5, 4.8)
                                        or r2["bbox"][0] > -14.4 * R or r2["bbox"][3] < 4.7 * R):
            ok = False
            print("  ERROR: 'ambos' debe tener los dos macizos (largo %s, bbox x %s)"
                  % (tuple(r2["largo_macizo"]), (r2["bbox"][0], r2["bbox"][3])))
        if nombre in ("morro_sitio", "ambos_sitio"):
            guardado = guardado or {}
            guardado[nombre] = (coll2, r2)
            continue
        for o2 in list(coll2.objects):
            m2 = o2.data
            bpy.data.objects.remove(o2, do_unlink=True)
            bpy.data.meshes.remove(m2)
        scene.collection.children.unlink(coll2)
        bpy.data.collections.remove(coll2)
    return ok, guardado


def escena_tunel(roca):
    """Suelo, carreteras, coche de escala y la caja del tunel con el Boolean
    EXACT del integrador. Devuelve (ok, md, tunel, objetos_escena)."""
    scene = bpy.context.scene
    R, W = RADIO, ANCHO
    ok = True
    m_tierra = _mat("MAT_TEST_tierra", (0.52, 0.50, 0.34), 0.95)
    m_asf = _mat("MAT_TEST_asfalto", (0.16, 0.16, 0.17), 0.85)
    m_lin = _mat("MAT_TEST_linea", (0.92, 0.92, 0.88), 0.7)
    objs = [_plano("TEST_tierra", -1500.0, 1500.0, -1500.0, 1500.0, -0.05, m_tierra, scene.collection)]
    X_ROAD = -0.65 * R
    antes = set(bpy.data.objects.keys())
    _carretera_y("TEST_carretera_a", X_ROAD, -0.5 * W, -900.0, scene.collection, m_asf, m_lin)
    _carretera_y("TEST_carretera_b", X_ROAD, 0.5 * W, 900.0, scene.collection, m_asf, m_lin)
    m_coche = _mat("MAT_TEST_coche", (0.85, 0.08, 0.05), 0.4)
    _caja("TEST_coche", (X_ROAD, LV * (0.5 * W + 55.0), 0.85), (1.9, 4.5, 1.4), m_coche,
          scene.collection)
    objs += [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in antes]
    m_tun = _mat("MAT_TEST_tunel", (0.045, 0.038, 0.032), 0.95)
    tunel = _caja("TEST_tunel", (-0.65 * R, 0.0, 4.75), (21.0, W + 80.0, 9.5), m_tun,
                  scene.collection)
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
    print("  roca - tunel (EXACT): tris=%d no-manifold=%d winding=%d vertices en el tunel=%d"
          % (tris_b, nm_b, flip_b, dentro))
    bmb.free()
    if nm_b != 0 or dentro < 8:
        ok = False
        print("  ERROR: el tunel no perfora limpiamente la roca")
    return ok, md, tunel, objs


def sitio(mod, en, roca_zaga, morro_guardado):
    """Evaluacion en el sitio real (encaje_mclaren). Devuelve (ok, lista de
    (nombre, Sitio, objeto)) para los previews; None si no hay geometria."""
    G = en.cargar()
    if G is None:
        print("  SITIO: sin geometria (snapshot ni geometria_3d.json): se omite")
        return True, None
    print("  SITIO: geometria", G["_ruta"])
    scene = bpy.context.scene
    ok = True
    salida = []
    for nombre, sx, ds, kw in CFG_SITIO:
        sit = en.Sitio(G, RADIO, ANCHO, sx=sx, ds=ds)
        if nombre == "A_zaga":
            obj = roca_zaga
        elif nombre == "A_morro" and morro_guardado and "morro_sitio" in morro_guardado:
            obj = morro_guardado["morro_sitio"][1]
        elif nombre == "A_ambos" and morro_guardado and "ambos_sitio" in morro_guardado:
            obj = morro_guardado["ambos_sitio"][1]
        else:
            coll3 = bpy.data.collections.new("SITIO_" + nombre)
            scene.collection.children.link(coll3)
            obj = mod.build(coll3, radio=RADIO, ancho=ANCHO, alto_base=AB, z_fondo=ZF, seed=0,
                            lado_visible=sit.lado_visible, con_vegetacion=False, **kw)
        res = sit.evaluar(obj)
        cx, cy, z0, ang, lv = sit.colocacion()
        print("  " + en.resumen(nombre, res))
        print("     colocacion: cx=%.1f cy=%.1f z0=%.1f ang_z=%.3f rad lado_visible=%+.0f s_face=%.0f"
              % (cx, cy, z0, ang, lv, sit.s_face))
        if res["colisiones"]:
            cs = res["colisiones"]
            print("     colisiones (s, x/R, y, z_pista, z_malla):",
                  [(round(c[0]), round(c[1] / RADIO, 1), round(c[2]), round(c[3]), round(c[4]))
                   for c in cs[:3]], "...", [(round(c[0]), round(c[1] / RADIO, 1), round(c[2]))
                                              for c in cs[-2:]])
        if nombre in ESPERA_COLISION:
            print("     -> ESPERADO: la orientacion B (morro al mar) pisa la horquilla de las curvas 4-6"
                  if res["n_col"] else "     -> SORPRESA: sin colisiones")
        elif res["n_col"]:
            ok = False
            print("  ERROR: configuracion A con muestras de pista bajo la huella")
        elif res["n_tunel"] < 20:
            ok = False
            print("  ERROR: el tunel de la rueda delantera no coincide con la calzada")
        salida.append((nombre, sit, obj))
    return ok, salida


def _solo(visibles):
    """Solo renderizan los objetos de `visibles` (y sus hijos)."""
    vis = set()
    for o in visibles:
        vis.add(o.name)
        for c in o.children_recursive:
            vis.add(c.name)
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in vis


def _preparar_render():
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.clip_end = 8000.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new("TEST_sol", "SUN")
    sun_data.energy = 2.4
    sun_data.color = (1.0, 0.92, 0.78)
    sun_data.angle = math.radians(3.0)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(-52), 0.0, math.radians(-38 if LV > 0 else 142))
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
    return cam, cam_data


def _disparo(cam, cam_data, png, pos, objetivo, lente):
    scene = bpy.context.scene
    cam_data.lens = lente
    cam.location = pos
    cam.rotation_euler = (objetivo - pos).to_track_quat("-Z", "Y").to_euler()
    path = os.path.join(PREV, png)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("PNG:", path, os.path.exists(path))


def render(roca, md, tunel, morro, objs_escena):
    R, W = RADIO, ANCHO
    zc = R - AB
    cam, cam_data = _preparar_render()
    s = LV
    _solo([roca] + objs_escena)
    shots = [
        ("montana_mclaren_tunel.png", Vector((0.45 * R, s * (0.5 * W + 2.4 * R), 0.22 * R)),
         Vector((-0.65 * R, s * (0.5 * W - 0.3 * R), 0.12 * R)), 45.0),
        ("montana_mclaren_pista.png", Vector((-0.3 * R, s * (0.5 * W + 30.0), 1.5)),
         Vector((0.0, s * 0.5 * W, zc)), 18.0),
        ("montana_mclaren_34.png", Vector((6.5 * R, s * (0.5 * W + 5.0 * R), 2.4 * R)),
         Vector((-3.0 * R, s * 0.15 * W, 1.1 * R)), 35.0),
        ("montana_mclaren_lateral.png", Vector((-4.5 * R, s * (0.5 * W + 11.0 * R), 2.6 * R)),
         Vector((-4.8 * R, 0.0, 1.4 * R)), 28.0),
        ("montana_mclaren_aereo.png", Vector((-1.5 * R, s * (0.5 * W + 7.0 * R), 9.5 * R)),
         Vector((-5.5 * R, 0.0, 0.5 * R)), 26.0),
        ("montana_mclaren_trasera.png", Vector((-21.0 * R, s * (0.5 * W + 5.0 * R), 4.0 * R)),
         Vector((-9.0 * R, 0.0, 1.6 * R)), 32.0),
        ("montana_mclaren_frente.png", Vector((7.5 * R, s * 0.4 * R, 1.4 * R)),
         Vector((0.5 * R, 0.0, 1.1 * R)), 40.0),
    ]
    for png, pos, objetivo, lente in shots:
        _disparo(cam, cam_data, png, pos, objetivo, lente)
        if png == "montana_mclaren_tunel.png":
            roca.modifiers.remove(md)
            bpy.data.objects.remove(tunel, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("BLEND:", BLEND, os.path.exists(BLEND))
    if morro and "morro_sitio" in morro:
        _solo([morro["morro_sitio"][1]] + objs_escena)
        _disparo(cam, cam_data, "montana_mclaren_morro_lateral.png",
                 Vector((-1.0 * R, s * (0.5 * W + 11.0 * R), 2.6 * R)), Vector((-1.0 * R, 0.0, 1.3 * R)), 28.0)
        _disparo(cam, cam_data, "montana_mclaren_morro_34.png",
                 Vector((-14.0 * R, s * (0.5 * W + 8.0 * R), 3.2 * R)), Vector((-1.0 * R, 0.0, 1.2 * R)), 30.0)
    return cam, cam_data


def render_sitio(salida, cam, cam_data):
    """Previews en el sitio real: terreno T1 + mar + calzada en el marco
    local de cada configuracion."""
    scene = bpy.context.scene
    R = RADIO
    scene.eevee.taa_render_samples = 24
    m_terr = _mat("MAT_SITIO_terreno", (0.42, 0.47, 0.27), 0.95)
    m_mar = _mat("MAT_SITIO_mar", (0.08, 0.28, 0.52), 0.15)
    m_pista = _mat("MAT_SITIO_pista", (0.17, 0.17, 0.18), 0.8)
    vistas = {
        "A_zaga": [("mar", (-15.0 * R, -10.0 * R, 4.5 * R), (-4.0 * R, 0.0, 1.2 * R), 30.0),
                   ("tierra", (8.0 * R, 9.0 * R, 4.5 * R), (0.5 * R, 0.0, 1.2 * R), 32.0)],
        "A_morro": [("mar", (-15.0 * R, -10.0 * R, 4.5 * R), (-4.0 * R, 0.0, 1.2 * R), 30.0),
                    ("tierra", (8.0 * R, 9.0 * R, 4.5 * R), (0.5 * R, 0.0, 1.2 * R), 32.0),
                    ("piloto", None, (-1.0 * R, 0.0, 1.2 * R), 22.0)],
        "A_ambos": [("mar", (-15.0 * R, -10.0 * R, 4.5 * R), (-4.0 * R, 0.0, 1.2 * R), 30.0),
                    ("tierra", (8.0 * R, 9.0 * R, 4.5 * R), (0.5 * R, 0.0, 1.2 * R), 32.0)],
        "B_zaga_plan": [("aereo", (-16.0 * R, -11.0 * R, 7.0 * R), (-6.0 * R, 0.0, 1.0 * R), 28.0)],
    }
    for nombre, sit, obj in salida:
        if nombre not in vistas:
            continue
        coll = bpy.data.collections.new("SITIO_mallas_" + nombre)
        scene.collection.children.link(coll)
        xr, yr = (-18.0 * R, 10.0 * R), (-330.0, 330.0)
        terr = sit.malla_terreno(coll, xr, yr, 6.0, m_terr, m_mar)
        mar = sit.malla_mar(coll, (-1300.0, 500.0), (-1000.0, 1000.0), m_mar)
        pista = sit.malla_pista(coll, (-30.0 * R, 20.0 * R), (-900.0, 900.0), m_pista)
        _solo([obj, terr, mar, pista])
        for vista, pos, objetivo, lente in vistas[nombre]:
            if pos is None:
                ms = sit.muestras((-2.5 * R, 0.5 * R), (-11.0 * R, -8.0 * R))
                if not ms:
                    continue
                q = min(ms, key=lambda m: abs(m[2] + 9.5 * R))
                pos = (q[1], q[2], q[3] + 1.6)
            _disparo(cam, cam_data, "montana_mclaren_sitio_%s_%s.png" % (nombre, vista),
                     Vector(pos), Vector(objetivo), lente)
        for o in list(coll.objects):
            m = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(m)
        scene.collection.children.unlink(coll)
        bpy.data.collections.remove(coll)


try:
    mod = _cargar("montana_mclaren")
    en = _cargar("encaje_mclaren")
    ok, roca, coll = main(mod)
    ok_v, morro = variantes(mod)
    ok_t, md, tunel, objs = escena_tunel(roca)
    ok_s, salida = sitio(mod, en, roca, morro)
    cam, cam_data = render(roca, md, tunel, morro, objs)
    if salida:
        render_sitio(salida, cam, cam_data)
    ok = ok and ok_v and ok_t and ok_s
    print("TEST_OK" if ok else "TEST_FALLO")
except Exception:
    traceback.print_exc()
    sys.exit(1)
