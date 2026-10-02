"""Test de viaducto_curvo_v2.py — Blender 5.1 headless.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_viaducto_curvo_v2.py"

Trazado sintetico (puntos cada 4 m): sale de (0,0,93) hacia +X, 300 m de curva
en S (radio 80 m a izquierdas y luego a derechas) bajando al 17 %, y despues un
lazo de 1000 m (radio 220 m) que baja de forma sostenida hasta z=6.
Comprueba presupuesto (<= 150k tris, < 65k vertices por malla), la planeidad
de la losa y el sentido de las normales, y renderiza EEVEE 1280x720:
  previews/viaducto_v2_lateral.png   arcos mas altos + caja-casa de 10 m
  previews/viaducto_v2_tablero.png   vista de piloto sobre el tablero
  previews/viaducto_v2_lejos.png     tres cuartos lejano de toda la obra
  previews/viaducto_v2_bajo.png      parte baja junto al mar
  previews/viaducto_v2_contrapicado.png  desde el agua mirando hacia arriba
  previews/viaducto_v2_piloto_llano.png  piloto (ojo a 1.0 m) en tramo llano
  previews/viaducto_v2_estribo.png       arranque del tablero (pila extrema)
Comprueba ademas: 'ancho' como secuencia por punto (pretil siempre fuera de la
calzada local), altura del pretil y que nada sobresale de los testeros.
Guarda blend/viaducto_curvo_v2.blend.

Opcional: anadir `-- lateral lejos ...` para renderizar solo esas vistas, y
`-- real real_alto real_piloto real_bajo` para construir ademas el tramo
'bridge' del trazado real (lee geometria_3d.json en SOLO LECTURA, con ancho POR
PUNTO, y comprueba la holgura pretil-calzada contra TODAS las muestras) y
renderizar previews/viaducto_v2_real*.png. `-- todo` = todas las vistas
(sinteticas + reales) y guarda el .blend (solo con el viaducto sintetico).
"""

import importlib.util
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
PREV = os.path.join(BASE, "previews")
BLEND = os.path.join(BASE, "blend", "viaducto_curvo_v2.blend")
SOLO = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else []


def camino():
    """Eje sintetico: S de 300 m al 17 % + lazo de 1000 m hasta z=6."""
    g1 = 0.17
    g2 = (87.0 - 0.17 * 270.0 - 60.0 * 0.17 / 2.0) / (970.0 + 30.0)
    x = y = 0.0
    z = 93.0
    ang = 0.0
    ds = 0.25
    pts = [(x, y, z)]
    n = int(round(1300.0 / ds))
    for k in range(n):
        s = (k + 0.5) * ds
        kappa = 1.0 / 80.0 if s < 150.0 else (-1.0 / 80.0 if s < 300.0 else 1.0 / 220.0)
        if s <= 270.0:
            g = g1
        elif s >= 330.0:
            g = g2
        else:
            t = (s - 270.0) / 60.0
            g = g1 + (g2 - g1) * t
        ang += kappa * ds
        x += math.cos(ang) * ds
        y += math.sin(ang) * ds
        z -= g * ds
        if (k + 1) % 16 == 0:
            pts.append((x, y, z))
    return pts


def mat_plano(nombre, color, rough=0.8):
    m = bpy.data.materials.get(nombre)
    if m is None:
        m = bpy.data.materials.new(nombre)
        m.use_nodes = True
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Base Color'].default_value = (*color, 1.0)
                nd.inputs['Roughness'].default_value = rough
    return m


def malla_simple(nombre, verts, faces, mat, coleccion):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    me.update()
    ob = bpy.data.objects.new(nombre, me)
    coleccion.objects.link(ob)
    return ob


def main():
    os.makedirs(PREV, exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    spec = importlib.util.spec_from_file_location(
        "viaducto_curvo_v2", os.path.join(BASE, "viaducto_curvo_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    scene = bpy.context.scene
    coll = bpy.data.collections.new("ASSET_viaducto_curvo_v2")
    scene.collection.children.link(coll)

    puntos = camino()
    ANCHO = 13.0
    print("CAMINO n=%d  z0=%.2f  z1=%.2f" % (len(puntos), puntos[0][2], puntos[-1][2]))

    raiz = mod.build_desde_puntos(coll, puntos, ancho=ANCHO, nivel_agua=0.0)
    assert raiz.type == 'EMPTY' and raiz.name.startswith("VIADUCTO_")
    assert tuple(raiz.location) == (0.0, 0.0, 0.0)

    # tambien debe funcionar la muestra build() (no se renderiza)
    coll_demo = bpy.data.collections.new("TEST_demo")
    demo = mod.build(coll_demo)
    t_demo = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
                 for o in demo.children_recursive if o.type == 'MESH')
    print("DEMO build(): tris=%d" % t_demo)
    assert t_demo <= 25000, "la muestra build() pasa de 25k tris"
    for o in list(demo.children_recursive) + [demo]:
        bpy.data.objects.remove(o, do_unlink=True)

    # robustez (no se renderiza): niveles forzados y un tramo corto y bajo
    def cuenta_y_borra(r):
        t_ = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
                 for o in r.children_recursive if o.type == 'MESH')
        info = (t_, len(r["pilas_s"]), list(r["niveles_z"]))
        for o in list(r.children_recursive) + [r]:
            bpy.data.objects.remove(o, do_unlink=True)
        return info

    info = cuenta_y_borra(mod.build_desde_puntos(
        coll_demo, puntos, ancho=ANCHO, nivel_agua=0.0, nombre="dosniveles",
        niveles=(30.0, 58.0)))
    print("NIVELES FORZADOS (30, 58): tris=%d pilas=%d niveles_z=%s" % info)
    assert info[0] <= 150000 and len(info[2]) == 2
    corto = [(4.0 * k, 0.5 * k, 7.0 - 0.1 * k) for k in range(9)]
    info = cuenta_y_borra(mod.build_desde_puntos(
        coll_demo, corto, ancho=11.0, nivel_agua=0.0, nombre="corto"))
    print("TRAMO CORTO Y BAJO (32 m, z~7): tris=%d pilas=%d niveles_z=%s" % info)
    assert info[0] > 0 and info[2] == []

    # 'ancho' como SECUENCIA por punto (calzada de ancho variable): el pretil
    # debe quedar siempre por fuera de la calzada local (ancho_i - 1 m)
    from mathutils import kdtree as _kdt
    esp_v = mod._Espina(puntos)
    anchos = [12.6 + 0.9 * math.sin(k * 0.045) for k in range(len(puntos))]
    r_var = mod.build_desde_puntos(coll_demo, puntos, ancho=anchos, nivel_agua=0.0,
                                   nombre="anchovar")
    perfil = mod._Ancho(esp_v, anchos, len(puntos))
    kd_v = _kdt.KDTree(len(esp_v.pts))
    for i_, q_ in enumerate(esp_v.pts):
        kd_v.insert((q_.x, q_.y, 0.0), i_)
    kd_v.balance()
    peor_var = 1e9
    for o in r_var.children_recursive:
        if o.type != 'MESH' or '_balaustrada' not in o.name:
            continue
        for v in o.data.vertices:
            _co, i_, dist = kd_v.find((v.co.x, v.co.y, 0.0))
            peor_var = min(peor_var, dist - (perfil(esp_v.cum[i_]) - 1.0) / 2.0)
    print("ANCHO VARIABLE %.2f..%.2f m: holgura minima pretil-calzada = %.3f m  "
          "(props raiz: %.2f..%.2f)"
          % (min(anchos), max(anchos), peor_var, r_var["ancho_min"], r_var["ancho_max"]))
    assert peor_var >= -0.02, "con ancho variable el pretil pisa la calzada"
    cuenta_y_borra(r_var)
    try:
        mod.build_desde_puntos(coll_demo, puntos, ancho=anchos[:-3], nombre="malo")
        raise AssertionError("una secuencia 'ancho' de longitud erronea debe fallar")
    except ValueError:
        pass
    for o in [o for o in bpy.data.objects if o.name.startswith("VIADUCTO_malo")]:
        bpy.data.objects.remove(o, do_unlink=True)

    # --- eje auxiliar para colocar camaras / escala
    esp = mod._Espina(puntos)
    sp = [float(s) for s in raiz["pilas_s"]]
    L = esp.L
    pasos = [b - a for a, b in zip(sp, sp[1:])]
    print("PILAS n=%d  paso min=%.2f max=%.2f  niveles_z=%s"
          % (len(sp), min(pasos), max(pasos), list(raiz["niveles_z"])))
    assert 13.0 <= min(pasos) and max(pasos) <= 15.5, "paso de pilas fuera de 14-15 m"

    def marco(s):
        p, t, n = esp.frame(s)
        return p.copy(), t.copy(), n.copy()

    # --- presupuesto, limite AC de vertices, normales
    #     Las caras se generan con el sentido correcto SIN recalc (el recalc
    #     de bmesh se equivoca con las dovelas sueltas). Se comprueba en todas
    #     las piezas convexas pequenas (dovelas, claves, cajas, zocalos,
    #     tajamares, balaustres, pedestales) que cada normal mira hacia fuera;
    #     los tubos curvos se validan a ojo con backface culling en el render.
    tris = 0
    max_v = 0
    hacia_dentro = 0
    piezas = 0
    for ob in raiz.children_recursive:
        if ob.type != 'MESH':
            continue
        t = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        tris += t
        max_v = max(max_v, len(ob.data.vertices))
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.faces.ensure_lookup_table()
        visto = set()
        malas = 0
        for f0 in bm.faces:
            if f0.index in visto:
                continue
            isla, pila = [], [f0]
            visto.add(f0.index)
            while pila:
                f = pila.pop()
                isla.append(f)
                for e in f.edges:
                    for g in e.link_faces:
                        if g.index not in visto:
                            visto.add(g.index)
                            pila.append(g)
            # los tubos curvos del pretil (no convexos) dan falsos positivos:
            # en esa malla solo se comprueban los dados (<= 6 caras)
            if len(isla) > (6 if '_balaustrada' in ob.name else 10):
                continue
            piezas += 1
            vs = {v.index: v.co for f in isla for v in f.verts}
            cen = sum(vs.values(), Vector()) / len(vs)
            malas += sum(1 for f in isla
                         if (f.calc_center_median() - cen).dot(f.normal) < -1e-5)
        hacia_dentro += malas
        bm.free()
        print("  %-36s tris=%6d verts=%6d  normales_hacia_dentro=%d"
              % (ob.name, t, len(ob.data.vertices), malas))
    print("TRIS total=%d  L=%.1f m  pilas=%d  tris/30m=%.0f  max_verts_malla=%d  "
          "piezas_convexas=%d  normales_hacia_dentro=%d"
          % (tris, L, len(sp), tris / (L / 30.0), max_v, piezas, hacia_dentro))
    assert tris <= 150000, "viaducto pasa de 150k tris (%d)" % tris
    assert max_v < 65000, "una malla pasa de 65k vertices (%d)" % max_v
    assert hacia_dentro == 0, "hay normales invertidas"

    # --- planeidad de la losa: ningun vertice del cuerpo por encima de eje-0.06
    #     dentro de la calzada, y la cara superior existe a esa cota
    from mathutils import kdtree
    kd = kdtree.KDTree(len(esp.pts))
    for i, q in enumerate(esp.pts):
        kd.insert((q.x, q.y, 0.0), i)
    kd.balance()
    peor = -1e9
    n_top = 0
    for ob in raiz.children_recursive:
        if ob.type != 'MESH' or '_cuerpo' not in ob.name:
            continue
        for v in ob.data.vertices:
            co, i, dist = kd.find((v.co.x, v.co.y, 0.0))
            if dist > ANCHO / 2.0 + 0.4:
                continue
            dz = v.co.z - (esp.pts[i].z - 0.06)
            peor = max(peor, dz)
            if abs(dz) < 0.05:
                n_top += 1
    print("LOSA: max (z_vertice - (z_eje-0.06)) bajo el tablero = %.3f m  (vertices a cota de losa: %d)"
          % (peor, n_top))
    assert peor < 0.06, "el cuerpo asoma por encima de la cara superior de la losa"
    assert n_top > 100, "no se encuentra la cara superior de la losa a z_eje-0.06"

    # --- el pretil no invade la calzada (ancho - 1 m) y no pasa de 1.4 m
    d_min = 1e9
    alto_max = -1e9
    for ob in raiz.children_recursive:
        if ob.type != 'MESH' or '_balaustrada' not in ob.name:
            continue
        for v in ob.data.vertices:
            co, i, dist = kd.find((v.co.x, v.co.y, 0.0))
            d_min = min(d_min, dist)
            alto_max = max(alto_max, v.co.z - esp.pts[i].z)
    print("PRETIL: distancia minima al eje = %.3f m (calzada = %.3f)  alto max = %.2f m"
          % (d_min, (ANCHO - 1.0) / 2.0, alto_max))
    assert d_min >= (ANCHO - 1.0) / 2.0 - 0.02, "el pretil invade la calzada"
    assert alto_max <= 1.20, "pretil/dados demasiado altos: tapan la vista del piloto"

    # --- nada sobresale de los testeros del tablero (pilas extremas enrasadas)
    fuera = 0.0
    for (s_e, signo) in ((0.0, -1.0), (L, 1.0)):
        p_e, t_e, _n = marco(s_e)
        for ob in raiz.children_recursive:
            if ob.type != 'MESH':
                continue
            for v in ob.data.vertices:
                d = Vector((v.co.x - p_e.x, v.co.y - p_e.y, 0.0))
                if d.length < 16.0:
                    fuera = max(fuera, signo * d.dot(t_e))
    print("TESTEROS: saliente maximo mas alla del final del tablero = %.3f m" % fuera)
    assert fuera <= 0.05, "algo sobresale del final del tablero"

    # --- calzada de prueba (solo preview): cinta de asfalto de ancho-1 m
    asf = mat_plano("MAT_TEST_asfalto", (0.045, 0.045, 0.05), 0.85)
    blanco = mat_plano("MAT_TEST_linea", (0.85, 0.85, 0.82), 0.6)
    def calzada(esp_, hw_, sufijo):
        """hw_ = semiancho de la calzada: numero o funcion de s."""
        vs, fs, vl, fl = [], [], [], []
        n_st = int(esp_.L / 2.0) + 1
        for k in range(n_st):
            s = esp_.L * k / (n_st - 1)
            hw = hw_(s) if callable(hw_) else hw_
            p, t, n = esp_.frame(s)
            vs += [(p.x - n.x * hw, p.y - n.y * hw, p.z), (p.x + n.x * hw, p.y + n.y * hw, p.z)]
            for lat in (-hw + 0.35, hw - 0.35):
                vl += [(p.x + n.x * (lat - 0.08), p.y + n.y * (lat - 0.08), p.z + 0.02),
                       (p.x + n.x * (lat + 0.08), p.y + n.y * (lat + 0.08), p.z + 0.02)]
        for k in range(n_st - 1):
            o = 2 * k
            fs.append((o, o + 2, o + 3, o + 1))
            o = 4 * k
            fl.append((o, o + 4, o + 5, o + 1))
            fl.append((o + 2, o + 6, o + 7, o + 3))
        return [malla_simple("TEST_calzada" + sufijo, vs, fs, asf, scene.collection),
                malla_simple("TEST_lineas" + sufijo, vl, fl, blanco, scene.collection)]

    calzada(esp, (ANCHO - 1.0) / 2.0, "")

    # --- mar turquesa (solo preview)
    mar_m = mat_plano("MAT_TEST_mar", (0.008, 0.30, 0.34), 0.12)
    sz = 4000.0
    malla_simple("TEST_mar", [(-sz, -sz, -0.03), (sz, -sz, -0.03), (sz, sz, -0.03),
                              (-sz, sz, -0.03)], [(0, 1, 2, 3)], mar_m, scene.collection)

    # --- caja-casa de 10 m junto a la pila mas cercana a s=66 (escala)
    j_ref = min(range(len(sp)), key=lambda j: abs(sp[j] - 66.0))
    p, t, n = marco(sp[j_ref])
    c = Vector((p.x, p.y, 0.0)) - n * 19.0 + t * 7.2
    casa_m = mat_plano("MAT_TEST_casa", (0.80, 0.30, 0.16), 0.8)
    teja_m = mat_plano("MAT_TEST_teja", (0.55, 0.12, 0.05), 0.8)
    vb = []
    for zz in (0.0, 10.0):
        for (ax, ay) in ((-5, -5), (5, -5), (5, 5), (-5, 5)):
            q = c + t * ax + n * ay
            vb.append((q.x, q.y, zz))
    fb = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    malla_simple("TEST_casa_10m", vb, fb, casa_m, scene.collection)
    vt = []
    for (ax, ay) in ((-5.5, -5.5), (5.5, -5.5), (5.5, 5.5), (-5.5, 5.5)):
        q = c + t * ax + n * ay
        vt.append((q.x, q.y, 10.0))
    q = c
    vt.append((q.x, q.y, 12.6))
    malla_simple("TEST_casa_tejado", vt, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)],
                 teja_m, scene.collection)

    # --- sol + cielo suave
    sol_d = bpy.data.lights.new("TEST_sol", type='SUN')
    sol_d.energy = 2.7
    sol_d.color = (1.0, 0.95, 0.86)
    sol_d.angle = math.radians(2.0)
    sol = bpy.data.objects.new("TEST_sol", sol_d)
    scene.collection.objects.link(sol)

    def sol_desde(hacia_el_sol):
        """Orienta el sol: `hacia_el_sol` apunta de la escena al sol."""
        viaje = -Vector(hacia_el_sol).normalized()
        sol.rotation_euler = viaje.to_track_quat('-Z', 'Y').to_euler()

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    for nd in world.node_tree.nodes:
        if nd.type == 'BACKGROUND':
            nd.inputs[0].default_value = (0.46, 0.66, 0.95, 1.0)
            nd.inputs[1].default_value = 0.8
            break

    # culling de caras traseras en el preview: una normal invertida se veria
    for m in bpy.data.materials:
        if m.name.startswith("MAT_PUENTES_VIADUCTO"):
            m.use_backface_culling = True

    cam_d = bpy.data.cameras.new("TEST_cam")
    cam_d.clip_start = 0.3
    cam_d.clip_end = 6000.0
    cam_d.sensor_width = 36.0
    cam = bpy.data.objects.new("TEST_cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def mira(pos, objetivo, lente):
        cam_d.lens = lente
        cam.location = pos
        cam.rotation_euler = (Vector(objetivo) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()

    # --- render EEVEE
    ids = {e.identifier
           for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items}
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        if cand in ids:
            scene.render.engine = cand
            break
    if hasattr(scene, 'eevee'):
        try:
            scene.eevee.taa_render_samples = 32
        except AttributeError:
            pass
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'

    TODO = "todo" in SOLO

    def render(nombre):
        if SOLO and not TODO and nombre not in SOLO:
            return
        scene.render.filepath = os.path.join(PREV, "viaducto_v2_%s.png" % nombre)
        bpy.ops.render.render(write_still=True)
        print("PNG %s" % scene.render.filepath)

    # 1) lateral: los arcos mas altos, desde fuera de la primera curva
    p, t, n = marco(sp[j_ref])
    sol_desde(-n * 0.75 - t * 0.55 + Vector((0, 0, 0.62)))
    mira(Vector((p.x, p.y, 40.0)) - n * 185.0 + t * 8.0,
         Vector((p.x, p.y, 46.0)) + t * 8.0, 30.0)
    render("lateral")

    # 2) tablero: vista de piloto bajando por la S
    p, t, n = marco(118.0)
    q, _t, _n = marco(176.0)
    sol_desde(-t * 0.5 - n * 0.6 + Vector((0, 0, 0.7)))
    mira(p + n * -1.8 + Vector((0, 0, 1.25)), q + Vector((0, 0, 0.3)), 20.0)
    render("tablero")

    # 3) lejos: tres cuartos de toda la obra (distancia ajustada al encuadre)
    from bpy_extras.object_utils import world_to_camera_view

    def encuadra(pts_eje, direccion, lente, z_obj, margen=0.05):
        """Camara en `direccion` desde el centro, a la minima distancia que
        deja todo el eje (a cota de tablero y de agua) dentro del cuadro."""
        xs = [q[0] for q in pts_eje]
        ys = [q[1] for q in pts_eje]
        centro = Vector(((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, z_obj))
        d = Vector(direccion).normalized()
        muestras = []
        for q in pts_eje[::6]:
            muestras.append(Vector((q[0], q[1], q[2] + 1.5)))
            muestras.append(Vector((q[0], q[1], 0.0)))
        dist = 150.0
        while dist < 4000.0:
            mira(centro + d * dist, centro, lente)
            bpy.context.view_layer.update()
            ok = True
            for w in muestras:
                co = world_to_camera_view(scene, cam, w)
                if not (margen < co.x < 1.0 - margen and margen < co.y < 1.0 - margen
                        and co.z > 0.0):
                    ok = False
                    break
            if ok:
                break
            dist += 20.0
        return dist

    if not SOLO or TODO or "lejos" in SOLO:
        sol_desde(Vector((0.30, -0.78, 0.55)))
        dist = encuadra(puntos, (0.80, -0.56, 0.20), 35.0, 30.0)
        print("LEJOS: distancia de camara = %.0f m" % dist)
    render("lejos")

    # 4) bajo: parte baja junto al mar, desde fuera del lazo
    p, t, n = marco(L - 62.0)
    sol_desde(-n * 0.70 + t * 0.45 + Vector((0, 0, 0.60)))
    mira(Vector((p.x, p.y, 3.2)) - n * 52.0 - t * 18.0,
         Vector((p.x, p.y, 4.6)) + t * 4.0, 30.0)
    render("bajo")

    # 4b) contrapicado: desde el agua, por DENTRO de la primera curva, mirando
    #     hacia arriba (intrados, arriostramiento remetido, bajos del tablero)
    j_c = min(range(len(sp)), key=lambda j: abs(sp[j] - 96.0))
    p, t, n = marco(sp[j_c])
    sol_desde(n * 0.70 - t * 0.35 + Vector((0, 0, 0.62)))
    mira(Vector((p.x, p.y, 2.5)) + n * 46.0 - t * 30.0,
         Vector((p.x, p.y, 47.0)) + t * 6.0, 20.0)
    render("contrapicado")

    # 4c) piloto en tramo casi LLANO del lazo (ojo a 1.0 m): el pretil bajo debe
    #     dejar ver el mar y el resto del viaducto por encima
    p, t, n = marco(700.0)
    q, _t, _n = marco(760.0)
    sol_desde(-t * 0.45 - n * 0.65 + Vector((0, 0, 0.62)))
    mira(p + n * -1.5 + Vector((0, 0, 1.0)), q + Vector((0, 0, 0.9)), 20.0)
    render("piloto_llano")

    # 4d) estribo: el arranque del tablero desde fuera y por debajo, con
    #     backface culling (la media pila extrema enrasada, sin cajas huecas)
    p, t, n = marco(0.0)
    sol_desde(-t * 0.60 - n * 0.50 + Vector((0, 0, 0.60)))
    mira(Vector((p.x, p.y, 80.0)) - t * 34.0 - n * 30.0,
         Vector((p.x, p.y, 84.0)) + t * 8.0, 28.0)
    render("estribo")

    # 5) OPCIONAL (`-- real`): el tramo 'bridge' del trazado real, SOLO LECTURA
    #    de geometria_3d.json, con la misma llamada que hace el integrador.
    # el .blend se guarda ANTES del tramo real (solo contiene el sintetico)
    if not SOLO or TODO:
        bpy.ops.wm.save_as_mainfile(filepath=BLEND)

    if TODO or any(a.startswith("real") for a in SOLO):
        import json
        ruta = os.path.join(os.path.dirname(BASE), "geometria_3d.json")
        with open(ruta, "r", encoding="utf-8") as fh:
            S = json.load(fh)["muestras"]
        N = len(S)
        run, mejor = [], []
        for i in range(N + 1):
            es_b = S[i % N]['sec'] == 'bridge'
            if es_b:
                run.append(i % N)
            if (not es_b or i == N) and run:
                if len(run) > len(mejor):
                    mejor = run
                run = []
        pts_r = [(S[j]['x'], S[j]['y'], S[j]['z']) for j in mejor[::2]]
        # ancho POR PUNTO (calzada real de ancho variable): asi debe llamarlo
        # el integrador para que el pretil no pise la calzada
        ancho_r = [S[j]['w'] + 1.0 for j in mejor[::2]]
        for ob in list(scene.objects):
            if ob.name.startswith(("VIADUCTO_", "TEST_calzada", "TEST_lineas", "TEST_casa")):
                ob.hide_render = True
        coll_r = bpy.data.collections.new("TEST_real")
        scene.collection.children.link(coll_r)
        raiz_r = mod.build_desde_puntos(coll_r, pts_r, ancho=ancho_r, nivel_agua=0.0,
                                        nombre="real")
        tris_r = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
                     for o in raiz_r.children_recursive if o.type == 'MESH')
        esp_r = mod._Espina(pts_r)
        # la calzada de prueba usa el ancho REAL de TODAS las muestras (tambien
        # las impares que el integrador se salta)
        esp_w = mod._Espina([(S[j]['x'], S[j]['y'], S[j]['z']) for j in mejor])
        perfil_w = mod._Ancho(esp_w, [S[j]['w'] for j in mejor], len(mejor))
        calzada(esp_w, lambda s: perfil_w(s) / 2.0, "_real")
        # holgura pretil-calzada real: distancia de cada vertice del pretil a
        # la polilinea de muestras menos el semiancho real interpolado
        from mathutils import geometry as _geo
        P2 = [Vector((S[j]['x'], S[j]['y'])) for j in mejor]
        W2 = [S[j]['w'] for j in mejor]
        kd_r = kdtree.KDTree(len(mejor))
        for i_, q_ in enumerate(P2):
            kd_r.insert((q_.x, q_.y, 0.0), i_)
        kd_r.balance()
        holg = 1e9
        for o in raiz_r.children_recursive:
            if o.type != 'MESH' or '_balaustrada' not in o.name:
                continue
            for v in o.data.vertices:
                _co, i_, dist = kd_r.find((v.co.x, v.co.y, 0.0))
                pv = Vector((v.co.x, v.co.y))
                for a_ in (i_ - 1, i_):
                    if a_ < 0 or a_ + 1 >= len(P2):
                        continue
                    _pt, u_ = _geo.intersect_point_line(pv, P2[a_], P2[a_ + 1])
                    u_ = min(max(u_, 0.0), 1.0)
                    d_ = (pv - P2[a_].lerp(P2[a_ + 1], u_)).length
                    w_ = W2[a_] + (W2[a_ + 1] - W2[a_]) * u_
                    holg = min(holg, d_ - w_ / 2.0)
        print("REAL: n=%d  L=%.0f m  z %.1f..%.1f  ancho=%.2f..%.2f  tris=%d  pilas=%d  "
              "niveles_z=%s  holgura pretil-calzada=%.3f m"
              % (len(pts_r), esp_r.L, pts_r[0][2], pts_r[-1][2], min(ancho_r),
                 max(ancho_r), tris_r, len(raiz_r["pilas_s"]),
                 list(raiz_r["niveles_z"]), holg))
        assert tris_r <= 150000
        assert holg >= -0.03, "el pretil pisa la calzada real"
        # tres cuartos lejano desde el lado del mar (sur-oeste)
        sol_desde(Vector((-0.35, -0.75, 0.55)))
        encuadra(pts_r, (-0.45, -0.86, 0.22), 35.0, 28.0)
        render("real")
        # lateral del tramo mas alto
        p, t, n = esp_r.frame(45.0)
        lado = 1.0
        sol_desde(n * lado * 0.75 - t * 0.5 + Vector((0, 0, 0.62)))
        mira(Vector((p.x, p.y, 36.0)) + n * lado * 165.0 + t * 25.0,
             Vector((p.x, p.y, 42.0)) + t * 25.0, 30.0)
        render("real_alto")
        # piloto (ojo a 1.0 m) en la parte baja y mas llana del tramo real
        s_p = esp_r.L * 0.80
        p, t, n = esp_r.frame(s_p)
        q, _t, _n = esp_r.frame(min(esp_r.L, s_p + 45.0))
        sol_desde(-t * 0.45 - n * 0.65 + Vector((0, 0, 0.62)))
        mira(p + Vector((0, 0, 1.0)), q + Vector((0, 0, 0.8)), 20.0)
        render("real_piloto")
        # parte baja del tramo real desde fuera de la curva, a ras de agua
        # (tajamares coherentes en todas las pilas, pretil con pilastrillas)
        s_b = esp_r.L * 0.90
        p, t, n = esp_r.frame(s_b)
        _p2, t2, _n2 = esp_r.frame(min(esp_r.L, s_b + 12.0))
        fuera_curva = -n if t.cross(t2).z > 0.0 else n
        sol_desde(fuera_curva * 0.70 + t * 0.40 + Vector((0, 0, 0.60)))
        mira(Vector((p.x, p.y, 2.6)) + fuera_curva * 44.0 - t * 14.0,
             Vector((p.x, p.y, p.z * 0.55)) + t * 3.0, 30.0)
        render("real_bajo")

    print("TEST_OK viaducto_curvo_v2 tris=%d previews=%s blend=%s" % (tris, PREV, BLEND))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
