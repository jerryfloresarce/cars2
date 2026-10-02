"""Revision independiente de viaducto_curvo_v2.py (NO modifica el modulo).

Renderiza angulos extra en el scratchpad y hace comprobaciones de API /
geometria con la MISMA llamada que el integrador (geometria_3d.json en solo
lectura).
"""

import importlib.util
import json
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
OUT = r"C:\Users\arcej\AppData\Local\Temp\claude\E--Escritorio-claude-pc-arnau-aseto-corsa\1a7b6c0c-72d8-44ab-af11-95e782d87886\scratchpad\review_viaducto"
SOLO = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else []


def camino():
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
    os.makedirs(OUT, exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "viaducto_curvo_v2", os.path.join(BASE, "viaducto_curvo_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    scene = bpy.context.scene

    # ------------------------------------------------------------ sintetico
    coll = bpy.data.collections.new("REV_sint")
    scene.collection.children.link(coll)
    puntos = camino()
    raiz = mod.build_desde_puntos(coll, puntos, ancho=13.0, nivel_agua=0.0)
    print("REV raiz=%s type=%s loc=%s rot=%s hijos=%d"
          % (raiz.name, raiz.type, tuple(raiz.location), tuple(raiz.rotation_euler),
             len(raiz.children)))
    print("REV hijos:", sorted(o.name for o in raiz.children)[:6], "...")
    esp = mod._Espina(puntos)
    sp = [float(s) for s in raiz["pilas_s"]]

    # ------------------------------------------------------------ real
    ruta = os.path.join(os.path.dirname(BASE), "geometria_3d.json")
    with open(ruta, "r", encoding="utf-8") as fh:
        G = json.load(fh)
    S = G["muestras"]
    N = len(S)
    print("REV paso_m=%s N=%d" % (G.get("paso_m"), N))
    runs, run = [], []
    for i in range(N + 1):
        es_b = S[i % N]['sec'] == 'bridge'
        if es_b:
            run.append(i % N)
        if (not es_b or i == N) and run:
            runs.append(run)
            run = []
    print("REV tramos bridge:", [(r[0], r[-1], len(r)) for r in runs])
    LIB = bpy.data.collections.new("LIB")
    scene.collection.children.link(LIB)
    LIB.hide_render = True
    reales = []
    for r in runs:
        if len(r) > 6:
            pts = [(S[j]['x'], S[j]['y'], S[j]['z']) for j in r[::2]]
            # MISMA llamada que integrar_escena.py
            v = mod.build_desde_puntos(LIB, pts, ancho=S[r[0]]['w'] + 1.0, nivel_agua=0.0)
            reales.append((r, pts, v))
            print("REV real raiz=%s hijos=%s ..." % (v.name, sorted(o.name for o in v.children)[:3]))
    # clonado como el integrador
    clones = []
    for (r, pts, v) in reales:
        mapping = {}
        for ob in [v] + list(v.children_recursive):
            nb = ob.copy()
            mapping[ob] = nb
            scene.collection.objects.link(nb)
        for ob, nb in mapping.items():
            if ob.parent in mapping:
                nb.parent = mapping[ob.parent]
        nr = mapping[v]
        nr.location = Vector((0, 0, 0))
        nr.rotation_euler = (0, 0, 0.0)
        clones.append(nr)
        print("REV clon=%s hijos=%d props=%s" % (nr.name, len(nr.children), list(nr.keys())))

    # --- desviacion eje spline vs TODAS las muestras reales (incluidas las impares)
    r, pts_r, v_r = max(reales, key=lambda q: len(q[0]))
    esp_r = mod._Espina(pts_r)
    from mathutils import kdtree
    kd = kdtree.KDTree(len(esp_r.pts))
    for i, q in enumerate(esp_r.pts):
        kd.insert((q.x, q.y, 0.0), i)
    kd.balance()
    peor_z = 0.0
    peor_xy = 0.0
    bank = 0.0
    for j in r:
        co, i, dist = kd.find((S[j]['x'], S[j]['y'], 0.0))
        peor_xy = max(peor_xy, dist)
        peor_z = max(peor_z, abs(esp_r.pts[i].z - S[j]['z']))
        for k in ('peralte', 'bank', 'roll'):
            if k in S[j]:
                bank = max(bank, abs(S[j][k]))
    print("REV real: desviacion max eje-spline vs muestras: dz=%.3f m dxy=%.3f m  peralte max=%.4f  claves=%s"
          % (peor_z, peor_xy, bank, sorted(S[r[0]].keys())))
    zs = [S[j]['z'] for j in r]
    print("REV real: z %.1f..%.1f  w=%s" % (max(zs), min(zs), sorted(set(round(S[j]['w'], 2) for j in r))))

    # --- caras degeneradas / estadistica
    for root in [raiz, v_r]:
        tris = 0
        deg = 0
        for ob in root.children_recursive:
            if ob.type != 'MESH':
                continue
            for p in ob.data.polygons:
                tris += len(p.vertices) - 2
                if p.area < 1e-6:
                    deg += 1
        print("REV %s tris=%d caras_degeneradas=%d" % (root.name, tris, deg))

    # --- huella de bases de pila (real): solapes entre pilas consecutivas
    sp_r = [float(s) for s in v_r["pilas_s"]]
    print("REV real pilas=%d niveles_z=%s" % (len(sp_r), list(v_r["niveles_z"])))

    # ------------------------------------------------------------ decorado
    asf = mat_plano("MAT_TEST_asfalto", (0.045, 0.045, 0.05), 0.85)

    def calzada(esp_, hw, sufijo):
        vs, fs = [], []
        n_st = int(esp_.L / 2.0) + 1
        for k in range(n_st):
            s = esp_.L * k / (n_st - 1)
            p, t, n = esp_.frame(s)
            vs += [(p.x - n.x * hw, p.y - n.y * hw, p.z), (p.x + n.x * hw, p.y + n.y * hw, p.z)]
        for k in range(n_st - 1):
            o = 2 * k
            fs.append((o, o + 2, o + 3, o + 1))
        return malla_simple("TEST_calzada" + sufijo, vs, fs, asf, scene.collection)

    cal_s = calzada(esp, 6.0, "_s")
    cal_r = calzada(esp_r, (S[r[0]]['w']) / 2.0, "_r")
    mar_m = mat_plano("MAT_TEST_mar", (0.008, 0.30, 0.34), 0.12)
    sz = 5000.0
    malla_simple("TEST_mar", [(-sz, -sz, -0.03), (sz, -sz, -0.03), (sz, sz, -0.03),
                              (-sz, sz, -0.03)], [(0, 1, 2, 3)], mar_m, scene.collection)

    sol_d = bpy.data.lights.new("TEST_sol", type='SUN')
    sol_d.energy = 2.7
    sol_d.color = (1.0, 0.95, 0.86)
    sol_d.angle = math.radians(2.0)
    sol = bpy.data.objects.new("TEST_sol", sol_d)
    scene.collection.objects.link(sol)
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    for nd in world.node_tree.nodes:
        if nd.type == 'BACKGROUND':
            nd.inputs[0].default_value = (0.46, 0.66, 0.95, 1.0)
            nd.inputs[1].default_value = 0.8
            break
    for m in bpy.data.materials:
        if m.name.startswith("MAT_PUENTES_VIADUCTO"):
            m.use_backface_culling = True

    cam_d = bpy.data.cameras.new("TEST_cam")
    cam_d.clip_start = 0.3
    cam_d.clip_end = 8000.0
    cam = bpy.data.objects.new("TEST_cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def mira(pos, objetivo, lente, giro_sol=40.0):
        pos = Vector(pos)
        objetivo = Vector(objetivo)
        cam_d.lens = lente
        cam.location = pos
        cam.rotation_euler = (objetivo - pos).to_track_quat('-Z', 'Y').to_euler()
        h = (pos - objetivo)
        h.z = 0.0
        if h.length < 1e-6:
            h = Vector((1, 0, 0))
        h.normalize()
        a = math.radians(giro_sol)
        hr = Vector((h.x * math.cos(a) - h.y * math.sin(a),
                     h.x * math.sin(a) + h.y * math.cos(a), 0.0))
        hacia = hr * 0.8 + Vector((0, 0, 0.62))
        sol.rotation_euler = (-hacia.normalized()).to_track_quat('-Z', 'Y').to_euler()

    ids = {e.identifier
           for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items}
    for cand in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        if cand in ids:
            scene.render.engine = cand
            break
    try:
        scene.eevee.taa_render_samples = 16
    except Exception:
        pass
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'

    def visibles(sint):
        for ob in scene.objects:
            if ob.name.startswith("TEST_calzada"):
                ob.hide_render = (ob.name.endswith("_s") != sint)
        for ob in [raiz] + list(raiz.children_recursive):
            ob.hide_render = not sint
        for c in clones:
            for ob in [c] + list(c.children_recursive):
                ob.hide_render = sint

    def render(nombre):
        if SOLO and nombre not in SOLO:
            return
        scene.render.filepath = os.path.join(OUT, "rev_%s.png" % nombre)
        bpy.ops.render.render(write_still=True)
        print("PNG %s" % scene.render.filepath)

    def marco(e, s):
        p, t, n = e.frame(s)
        return p.copy(), t.copy(), n.copy()

    # 1) FILM: distancia de circuito, teleobjetivo, desde abajo
    visibles(True)
    p, t, n = marco(esp, 60.0)
    mira(Vector((p.x, p.y, 8.0)) - n * 430.0 - t * 120.0, Vector((p.x, p.y, 50.0)) + t * 30.0, 55.0)
    render("film")

    # 2) ESTRIBO: arranque del viaducto desde arriba/atras
    p, t, n = marco(esp, 0.0)
    mira(p - t * 26.0 + n * 12.0 + Vector((0, 0, 11.0)), p + t * 4.0 + Vector((0, 0, -2.0)), 28.0)
    render("estribo")

    # 3) DETALLE: cabezas de pila en rampa del 17 %
    j = min(range(len(sp)), key=lambda k: abs(sp[k] - 110.0))
    p, t, n = marco(esp, sp[j])
    mira(Vector((p.x, p.y, p.z - 4.0)) - n * 46.0 - t * 10.0, Vector((p.x, p.y, p.z - 9.0)), 30.0)
    render("detalle")

    # 4) FIN DEL NIVEL de arriostramiento (tablero ~55 m)
    p, t, n = marco(esp, 225.0)
    mira(Vector((p.x, p.y, 30.0)) + n * 95.0 - t * 55.0, Vector((p.x, p.y, 36.0)), 30.0)
    render("fin_nivel")

    # 4b) base de pilas altas (zocalos) a ras de agua
    j = min(range(len(sp)), key=lambda k: abs(sp[k] - 45.0))
    p, t, n = marco(esp, sp[j])
    mira(Vector((p.x, p.y, 3.0)) - n * 40.0 - t * 22.0, Vector((p.x, p.y, 9.0)), 24.0)
    render("base")

    # 5) REAL, parte baja con curvas cerradas: tres cuartos desde arriba
    visibles(False)
    Lr = esp_r.L
    cola = [esp_r.pos(Lr - d) for d in range(0, 260, 10)]
    cx = sum(q.x for q in cola) / len(cola)
    cy = sum(q.y for q in cola) / len(cola)
    mira(Vector((cx, cy, 0.0)) + Vector((-0.45, -0.75, 0.0)).normalized() * 190.0 + Vector((0, 0, 95.0)),
         Vector((cx, cy, 4.0)), 35.0)
    render("real_bajo")

    # 6) REAL, transicion de proporciones (tablero ~25 m): lateral
    s25 = min(range(0, int(Lr), 2), key=lambda s: abs(esp_r.z(float(s)) - 25.0))
    p, t, n = marco(esp_r, float(s25))
    mejor = None
    for lado in (-1.0, 1.0):
        c = Vector((p.x, p.y, 0.0)) + n * lado * 130.0
        dmin = min((Vector((q.x, q.y, 0.0)) - c).length for q in esp_r.pts[::20])
        if mejor is None or dmin > mejor[0]:
            mejor = (dmin, lado)
    lado = mejor[1]
    print("REV real s(z=25)=%d lado=%+.0f holgura=%.0f" % (s25, lado, mejor[0]))
    mira(Vector((p.x, p.y, 14.0)) + n * lado * 130.0, Vector((p.x, p.y, 14.0)), 24.0)
    render("real_transicion")

    # 7) REAL, vista de piloto en la parte baja y cerrada (ojo a 1.0 m)
    p, t, n = marco(esp_r, Lr - 210.0)
    q, _t, _n = marco(esp_r, Lr - 175.0)
    mira(p + Vector((0, 0, 1.0)), q + Vector((0, 0, 0.6)), 20.0)
    render("real_piloto")

    # 8) REAL, vista de piloto arriba (rampa fuerte)
    p, t, n = marco(esp_r, 60.0)
    q, _t, _n = marco(esp_r, 110.0)
    mira(p + Vector((0, 0, 1.0)), q + Vector((0, 0, 0.6)), 20.0)
    render("real_piloto_alto")

    print("REVIEW_OK")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
