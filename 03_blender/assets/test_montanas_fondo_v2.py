"""test_montanas_fondo_v2.py — test headless de montanas_fondo_v2 (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python
  "E:\\Escritorio\\claude-pc\\arnau-aseto-corsa\\03_blender\\assets\\test_montanas_fondo_v2.py"

Renderiza (EEVEE, sol cálido + cielo azul, 1280x800, view_transform Standard):
  previews/montanas_v2_tipos.png        los 5 tipos en fila + caja de 100 m
  previews/montanas_v2_tipo_<tipo>.png  cada tipo de cerca (caja de 100 m)
  previews/montanas_v2_cordillera.png   cordillera (largo 900, 5 picos) desde
                                        el frente (+Y) a media altura
  previews/montanas_v2_cordillera_oblicua.png  la misma, alta y oblicua
  previews/montanas_v2_cordillera_b.png cordillera de 4 picos (seed 7)
  previews/montanas_v2_pena.png         3 peñascos (seeds 0-2) + caja de 10 m
                                        en (-45,-25) (dentro del encuadre)
  previews/montanas_v2_loma.png         colina redonda con peñasco + loma
                                        alargada (build_loma largo=260)
Guarda blend/montanas_fondo_v2.blend (escena de la cordillera).
Comprueba: pico <= 12k tris, cordillera <= 60k, peña <= 3k; ningún vértice
por debajo de z=-8; el pie cubre el hueco (rayo vertical 4 m por fuera del
contorno de z=0 -> impacta en el pie, z <= 0.8); tipos mezclados y alturas
variadas en la cordillera; cordal presente; ValueError con tipo desconocido;
sin manchas de roca sueltas (< 12 caras) en los picos; el domo remata en
casquete (normal.z media > 0.7 a 0.15 R del ápice); las lomas son TODO
verdes (0 caras de roca en el pico) y la loma larga es una cresta >= 220 m.
"""

import importlib.util
import json
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(BASE, "montanas_fondo_v2.py")
PREV = os.path.join(BASE, "previews")
BLEND = os.path.join(BASE, "blend", "montanas_fondo_v2.blend")
os.makedirs(PREV, exist_ok=True)
os.makedirs(os.path.dirname(BLEND), exist_ok=True)

LIM_PICO, LIM_CORD, LIM_PENA = 12000, 60000, 3000
Z_MIN_OK = -8.0
TAN_H35 = 18.0 / 35.0

scene = bpy.context.scene
resumen = {"tris": {}, "previews": [], "fallos": []}


def limpiar():
    """Escena vacía (conserva materiales: se reutilizan por nombre)."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    for cu in list(bpy.data.curves):
        bpy.data.curves.remove(cu)
    for co in list(bpy.data.collections):
        bpy.data.collections.remove(co)


def cargar():
    spec = importlib.util.spec_from_file_location("montanas_fondo_v2", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["montanas_fondo_v2"] = mod
    spec.loader.exec_module(mod)
    return mod


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def mallas(root):
    return [o for o in [root] + list(root.children_recursive) if o.type == "MESH"]


def z_min_mundo(ob):
    mw = ob.matrix_world
    return min((mw @ v.co).z for v in ob.data.vertices)


def z_max_mundo(ob):
    mw = ob.matrix_world
    return max((mw @ v.co).z for v in ob.data.vertices)


def mat_plano(nombre, color, rough=0.9):
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    if m.node_tree is None:        # solo Blender < 5 (use_nodes obsoleto)
        m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (*color, 1.0)
    bs.inputs["Roughness"].default_value = rough
    return m


def suelo(sx, sy, color=(0.30, 0.47, 0.15), z=-0.02, centro=(0.0, 0.0)):
    me = bpy.data.meshes.new("TEST_suelo")
    cx, cy = centro
    me.from_pydata([(cx - sx, cy - sy, z), (cx + sx, cy - sy, z),
                    (cx + sx, cy + sy, z), (cx - sx, cy + sy, z)], [], [(0, 1, 2, 3)])
    me.update()
    me.materials.append(mat_plano("MAT_TEST_suelo", color))
    ob = bpy.data.objects.new("TEST_suelo", me)
    scene.collection.objects.link(ob)
    return ob


def caja(pos, lado):
    """Caja de referencia (blanca, tapa roja) de 'lado' m apoyada en pos."""
    x, y, z = pos
    h = lado * 0.5
    v = [(x - h, y - h, z), (x + h, y - h, z), (x + h, y + h, z), (x - h, y + h, z),
         (x - h, y - h, z + lado), (x + h, y - h, z + lado),
         (x + h, y + h, z + lado), (x - h, y + h, z + lado)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new("TEST_caja")
    me.from_pydata(v, [], f)
    me.update()
    me.materials.append(mat_plano("MAT_TEST_caja", (0.92, 0.92, 0.92)))
    me.materials.append(mat_plano("MAT_TEST_caja_top", (0.85, 0.10, 0.10)))
    me.polygons[1].material_index = 1
    ob = bpy.data.objects.new("TEST_caja", me)
    scene.collection.objects.link(ob)
    return ob


def texto(nombre, txt, tam, pos, color=(0.06, 0.06, 0.06)):
    """Rótulo 3D de pie, legible desde +Y (cámara delante)."""
    cu = bpy.data.curves.new(nombre + "_cu", type="FONT")
    cu.body = txt
    cu.size = tam
    cu.extrude = tam * 0.04
    cu.align_x = "CENTER"
    cu.align_y = "BOTTOM"
    cu.resolution_u = 3
    tmp = bpy.data.objects.new(nombre + "_tmp", cu)
    scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(deps))
    me.name = nombre
    me.materials.clear()
    me.materials.append(mat_plano("MAT_TEST_texto", color, 0.6))
    ob = bpy.data.objects.new(nombre, me)
    ob.rotation_euler = (math.radians(90), 0.0, math.pi)
    ob.location = pos
    scene.collection.objects.link(ob)
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    return ob


def luces(sol_dir=(-0.45, -0.62, -0.64)):
    """Sol cálido desde delante-izquierda-arriba + cielo azul uniforme."""
    sol_d = bpy.data.lights.new("SOL", type="SUN")
    sol_d.energy = 2.8
    sol_d.color = (1.0, 0.94, 0.84)
    try:
        sol_d.angle = math.radians(3.0)
    except AttributeError:
        pass
    sol = bpy.data.objects.new("SOL", sol_d)
    scene.collection.objects.link(sol)
    sol.rotation_euler = Vector(sol_dir).to_track_quat("-Z", "Y").to_euler()
    mundo = bpy.data.worlds.get("CIELO") or bpy.data.worlds.new("CIELO")
    if mundo.node_tree is None:    # solo Blender < 5 (use_nodes obsoleto)
        mundo.use_nodes = True
    fondo = next((n for n in mundo.node_tree.nodes if n.type == "BACKGROUND"), None)
    if fondo is not None:
        fondo.inputs[0].default_value = (0.48, 0.70, 0.98, 1.0)
        fondo.inputs[1].default_value = 0.65
    scene.world = mundo


def camara(pos, objetivo, lente=35.0):
    cam_d = bpy.data.cameras.new("CAM")
    cam_d.lens = lente
    cam_d.clip_end = 8000.0
    cam = bpy.data.objects.new("CAM", cam_d)
    scene.collection.objects.link(cam)
    cam.location = Vector(pos)
    cam.rotation_euler = (Vector(objetivo) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def preparar_render():
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    try:
        scene.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass


def render(nombre):
    png = os.path.join(PREV, nombre + ".png")
    scene.render.filepath = png
    bpy.ops.render.render(write_still=True)
    assert os.path.isfile(png), "no se genero " + png
    print("PNG:", png)
    resumen["previews"].append(png)
    return png


def fallo(msg):
    print("FALLO:", msg)
    resumen["fallos"].append(msg)


def comprobar_pie(ob, radio, es_cresta=False, n=24):
    """El pie cubre el hueco: para n direcciones, rayo horizontal a z=0.3
    hacia el centro -> contorno; rayo vertical 4 m por fuera del contorno
    -> debe impactar en el pico con z en [-8, 0.8]. Devuelve (ok, d_min,
    d_max) con las distancias del contorno relativas a radio."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    mw = ob.matrix_world
    centro = mw.to_translation()
    lejos = radio * (4.0 if es_cresta else 3.0)
    ok = True
    ds = []
    for k in range(n):
        th = 2.0 * math.pi * k / n
        o = mw @ Vector((math.cos(th) * lejos, math.sin(th) * lejos, 0.3))
        d = (Vector((centro.x, centro.y, 0.3)) - o).normalized()
        hit, loc, _n, _i, hob, _m = scene.ray_cast(dg, o, d, distance=lejos * 2.0)
        if not hit or hob != ob:
            fallo("%s: sin contorno z=0.3 en th=%.0f" % (ob.name, math.degrees(th)))
            ok = False
            continue
        ds.append((loc - centro).xy.length / radio)
        fuera = (loc - centro).xy.normalized() * 4.0
        o2 = Vector((loc.x + fuera.x, loc.y + fuera.y, 80.0))
        hit2, loc2, _n, _i, hob2, _m = scene.ray_cast(dg, o2, Vector((0, 0, -1)), distance=200.0)
        if not hit2 or hob2 != ob:
            fallo("%s: hueco en el pie th=%.0f (rayo vertical no impacta)" %
                  (ob.name, math.degrees(th)))
            ok = False
        elif not (Z_MIN_OK <= loc2.z <= 0.8):
            fallo("%s: pie th=%.0f impacta a z=%.2f (fuera de [-8, 0.8])" %
                  (ob.name, math.degrees(th), loc2.z))
            ok = False
    return ok, (min(ds) if ds else 0.0), (max(ds) if ds else 0.0)


def componentes_roca(me):
    """Tamaños de las componentes conexas (por arista) de caras de roca
    (slots >= 2): detecta manchas/píxeles sueltos de roca."""
    edge_faces = {}
    for p in me.polygons:
        for ek in p.edge_keys:
            edge_faces.setdefault(ek, []).append(p.index)
    vec = [[] for _ in me.polygons]
    for fs in edge_faces.values():
        for a in fs:
            for b in fs:
                if a != b:
                    vec[a].append(b)
    pend = set(p.index for p in me.polygons if p.material_index >= 2)
    tam = []
    while pend:
        s = pend.pop()
        pila, n = [s], 1
        while pila:
            a = pila.pop()
            for b in vec[a]:
                if b in pend:
                    pend.discard(b)
                    pila.append(b)
                    n += 1
        tam.append(n)
    return sorted(tam)


def comprobar_casquete(ob, radio):
    """Domo: alrededor del ápice (0.15*radio) la pendiente debe ser suave
    (normal.z media > 0.7): casquete romo, no cono."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    mw = ob.matrix_world
    apex = max((mw @ v.co for v in ob.data.vertices), key=lambda c: c.z)
    nzs = []
    for k in range(8):
        th = 2.0 * math.pi * k / 8
        o = Vector((apex.x + math.cos(th) * 0.15 * radio,
                    apex.y + math.sin(th) * 0.15 * radio, apex.z + 50.0))
        hit, loc, nrm, _i, hob, _m = scene.ray_cast(dg, o, Vector((0, 0, -1)), distance=400.0)
        if hit and hob == ob:
            nzs.append(nrm.z)
    nz_med = sum(nzs) / len(nzs) if nzs else 0.0
    print("  casquete %s: nz medio a 0.15R del apice = %.2f (%d rayos)" % (ob.name, nz_med, len(nzs)))
    if len(nzs) < 6 or nz_med < 0.7:
        fallo("%s: la cima es un cono (nz medio %.2f < 0.7)" % (ob.name, nz_med))


def comprobar_pico(ob, alto, radio, es_cresta=False):
    n = tris(ob)
    comps = componentes_roca(ob.data)
    print("  componentes de roca %s: %s" % (ob.name, comps))
    if comps and comps[0] < 12:
        fallo("%s: mancha de roca suelta de %d caras" % (ob.name, comps[0]))
    if ob.get("mont_tipo") == "domo":
        comprobar_casquete(ob, radio)
    resumen["tris"][ob.name + "@" + str(ob.get("mont_tipo"))] = n
    if n > LIM_PICO:
        fallo("%s: %d tris > %d" % (ob.name, n, LIM_PICO))
    zmin, zmax = z_min_mundo(ob), z_max_mundo(ob)
    if zmin < Z_MIN_OK:
        fallo("%s: zmin=%.2f < %.1f" % (ob.name, zmin, Z_MIN_OK))
    if not (0.9 * alto <= zmax - ob.matrix_world.translation.z <= 1.25 * alto):
        fallo("%s: altura real %.1f vs nominal %.1f" % (ob.name, zmax, alto))
    ok, dmin, dmax = comprobar_pie(ob, radio, es_cresta)
    if not es_cresta and not (0.5 <= dmin and dmax <= 1.6):
        fallo("%s: contorno z=0 fuera de [0.5, 1.6]*radio (%.2f..%.2f)" %
              (ob.name, dmin, dmax))
    print("  %-14s tipo=%-9s %5d tris  z=[%.1f, %.1f]  contorno=%.2f..%.2f R  pie=%s"
          % (ob.name, ob.get("mont_tipo"), n, zmin, zmax, dmin, dmax, ok))
    return n


mod = cargar()
preparar_render()
print("Engine:", scene.render.engine)

# ---------------------------------------------------------------------------
# 0) API: ValueError con tipo desconocido; tipo aleatorio por seed
# ---------------------------------------------------------------------------
limpiar()
col = bpy.data.collections.new("MONT_API")
scene.collection.children.link(col)
try:
    mod.build_pico(col, alto=100, radio=60, seed=0, tipo="volcan")
    fallo("tipo desconocido no lanza ValueError")
except ValueError as e:
    print("ValueError OK:", e)
tipos_auto = set()
for s in range(8):
    ob = mod.build_pico(col, alto=150, radio=90, seed=s, res=0.4)
    tipos_auto.add(ob["mont_tipo"])
print("tipos aleatorios por seed:", sorted(tipos_auto))
if len(tipos_auto) < 3:
    fallo("poca variedad de tipos aleatorios: %s" % sorted(tipos_auto))
ob = mod.build_pico(col, alto=50, radio=100, seed=2, res=0.4)
if ob["mont_tipo"] not in ("domo", "meseta", "cresta"):
    fallo("pico bajo y ancho deberia ser domo/meseta/cresta, es %s" % ob["mont_tipo"])
ob = mod.build_pico(col, alto=120, radio=80, seed=4, pie=False, res=0.5)
if z_min_mundo(ob) < -0.01:
    fallo("pie=False deberia dejar la base en z=0 (zmin=%.2f)" % z_min_mundo(ob))

# ---------------------------------------------------------------------------
# 1) Los 5 tipos en fila + cerca uno a uno (caja de 100 m)
# ---------------------------------------------------------------------------
TIPOS = [  # (tipo, alto, radio, largo_cresta, x)
    ("aguja", 200.0, 90.0, None, -720.0),
    ("piramide", 180.0, 120.0, None, -430.0),
    ("meseta", 170.0, 135.0, None, -100.0),
    ("cresta", 175.0, 80.0, 300.0, 240.0),
    ("domo", 165.0, 125.0, None, 580.0),
]
limpiar()
col = bpy.data.collections.new("MONT_TIPOS")
scene.collection.children.link(col)
for i, (tipo, alto, radio, largo_c, x) in enumerate(TIPOS):
    ob = mod.build_pico(col, alto=alto, radio=radio, seed=i + 1, tipo=tipo,
                        largo_cresta=largo_c)
    ob.location = (x, 0.0, 0.0)
    if ob["mont_tipo"] != tipo:
        fallo("tipo pedido %s, obtenido %s" % (tipo, ob["mont_tipo"]))
    n = tris(ob)
    if n > LIM_PICO:
        fallo("%s (%s): %d tris > %d" % (ob.name, tipo, n, LIM_PICO))
    texto("rot_" + tipo, tipo.upper(), 26.0, (x, 175.0, 0.5))
suelo(4000.0, 4000.0)
caja((-1000.0, 60.0, 0.0), 100.0)
texto("rot_caja", "100 m", 20.0, (-1000.0, 130.0, 0.5))
luces()
camara((-120.0, 1900.0, 250.0), (-120.0, 0.0, 70.0), lente=35.0)
render("montanas_v2_tipos")

for i, (tipo, alto, radio, largo_c, x) in enumerate(TIPOS):
    limpiar()
    col = bpy.data.collections.new("MONT_TIPO_" + tipo)
    scene.collection.children.link(col)
    ob = mod.build_pico(col, alto=alto, radio=radio, seed=i + 1, tipo=tipo,
                        largo_cresta=largo_c)
    # comprobaciones con el pico SOLO en escena (los rayos no chocan con
    # vecinos ni con el suelo de test)
    comprobar_pico(ob, alto, radio, es_cresta=(tipo == "cresta"))
    ancho = max(radio * 1.3, (largo_c or 0.0) * 0.55)
    suelo(3000.0, 3000.0)
    caja((-(ancho + 70.0), ancho * 0.6, 0.0), 100.0)
    luces()
    dist = max(ancho * 2.0, alto * 1.15) / TAN_H35 * 0.85
    camara((dist * 0.28, dist, alto * 0.42), (0.0, 0.0, alto * 0.40), lente=35.0)
    render("montanas_v2_tipo_" + tipo)

# ---------------------------------------------------------------------------
# 2) Cordillera: tipos mezclados, cordal, <= 60k tris, dos vistas
# ---------------------------------------------------------------------------
def probar_cordillera(nombre, largo, n_picos, seed, vistas):
    limpiar()
    col = bpy.data.collections.new("MONT_CORD_" + nombre)
    scene.collection.children.link(col)
    root = mod.build_cordillera(col, largo=largo, n_picos=n_picos, seed=seed)
    if root.name != "MONT_cordillera" or root.type != "EMPTY":
        fallo("raiz de cordillera: %s (%s)" % (root.name, root.type))
    picos = [o for o in root.children if o.type == "MESH" and o.name.startswith("MONT_pico")]
    cordal = [o for o in root.children if o.name.startswith("MONT_cordal")]
    if len(picos) != n_picos:
        fallo("cordillera %s: %d picos (esperados %d)" % (nombre, len(picos), n_picos))
    if not cordal:
        fallo("cordillera %s: sin malla MONT_cordal" % nombre)
    total = 0
    alturas = []
    for o in mallas(root):
        n = tris(o)
        total += n
        zmin = z_min_mundo(o)
        if zmin < Z_MIN_OK:
            fallo("%s/%s: zmin=%.2f" % (nombre, o.name, zmin))
        if o.name.startswith("MONT_pico"):
            if n > LIM_PICO:
                fallo("%s/%s: %d tris > %d" % (nombre, o.name, n, LIM_PICO))
            alturas.append(o["mont_alto"])
        print("  %-16s %-9s %5d tris  zmin=%.1f  y=%.0f  alto=%.0f" %
              (o.name, o.get("mont_tipo", "cordal"), n, zmin, o.location.y,
               o.get("mont_alto", 0.0)))
    print("  cordillera %s: %d tris en total, tipos=%s" % (nombre, total, root["mont_tipos"]))
    if cordal:
        me_c = cordal[0].data
        cuenta = [0] * len(me_c.materials)
        for pg in me_c.polygons:
            cuenta[pg.material_index] += 1
        nz_med = sum(pg.normal.z for pg in me_c.polygons) / max(len(me_c.polygons), 1)
        print("  cordal: caras por material %s, nz medio=%.2f" % (cuenta, nz_med))
        if nz_med < 0.5:
            fallo("cordillera %s: normales del cordal hacia abajo (nz=%.2f)" % (nombre, nz_med))
        if cuenta[0] + cuenta[1] < 0.5 * len(me_c.polygons):
            fallo("cordillera %s: el cordal deberia ser mayormente verde %s" % (nombre, cuenta))
    resumen["tris"]["cordillera_" + nombre] = total
    if total > LIM_CORD:
        fallo("cordillera %s: %d tris > %d" % (nombre, total, LIM_CORD))
    tipos_c = set(root["mont_tipos"].split(","))
    if len(tipos_c) < min(3, n_picos):
        fallo("cordillera %s: tipos poco mezclados %s" % (nombre, tipos_c))
    if alturas and max(alturas) / min(alturas) < 1.25:
        fallo("cordillera %s: silueta plana (alturas %s)" % (nombre, alturas))
    # el cordal une los picos: a media distancia entre picos vecinos hay
    # terreno del cordal por encima de 0.2*min(alto)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ps = sorted(picos, key=lambda o: o.location.x)
    for a, b in zip(ps, ps[1:]):
        mx = (a.location.x + b.location.x) * 0.5
        my = (a.location.y + b.location.y) * 0.5
        hit, loc, _n, _i, hob, _m = scene.ray_cast(dg, Vector((mx, my, 600.0)),
                                                   Vector((0, 0, -1)), distance=700.0)
        h_min = min(a["mont_alto"], b["mont_alto"])
        if not hit or loc.z < 0.2 * h_min:
            fallo("cordillera %s: collado entre %s y %s a z=%.1f (< %.1f)" %
                  (nombre, a.name, b.name, loc.z if hit else -99, 0.2 * h_min))
        else:
            print("  collado %s-%s: z=%.1f (%s)" % (a.name, b.name, loc.z, hob.name))
    alto_max = max(alturas) if alturas else 200.0
    suelo(6000.0, 6000.0)
    luces()
    for (sufijo, pos, obj, lente) in vistas:
        camara(pos, obj, lente)
        render("montanas_v2_cordillera" + sufijo)
    return root, alto_max


root, alto_max = probar_cordillera(
    "a", 900.0, 5, 0,
    [("", (60.0, 1350.0, 95.0), (0.0, -60.0, 75.0), 35.0),
     ("_oblicua", (-1000.0, 950.0, 420.0), (0.0, -40.0, 60.0), 35.0)])
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("BLEND:", BLEND)
probar_cordillera("b", 900.0, 4, 7,
                  [("_b", (-40.0, 1300.0, 90.0), (0.0, -60.0, 70.0), 35.0)])

# ---------------------------------------------------------------------------
# 3) Peñascos: 3 seeds, <= 3k tris, base hundida, caja de 10 m
# ---------------------------------------------------------------------------
limpiar()
col = bpy.data.collections.new("MONT_PENA")
scene.collection.children.link(col)
for s, x in ((0, -62.0), (1, 0.0), (2, 62.0)):
    ob = mod.build_pena(col, alto=30.0, radio=22.0, seed=s)
    ob.location = (x, 0.0, 0.0)
    if ob.name.split(".")[0] != "MONT_pena":
        fallo("nombre de pena: %s" % ob.name)
    n = tris(ob)
    resumen["tris"]["pena_seed%d" % s] = n
    if n > LIM_PENA:
        fallo("pena seed %d: %d tris > %d" % (s, n, LIM_PENA))
    zmin, zmax = z_min_mundo(ob), z_max_mundo(ob)
    if zmin < Z_MIN_OK:
        fallo("pena seed %d: zmin=%.2f" % (s, zmin))
    if zmin > -2.5:
        fallo("pena seed %d: base no hundida (zmin=%.2f)" % (s, zmin))
    if not (0.75 * 30.0 <= zmax <= 1.35 * 30.0):
        fallo("pena seed %d: altura %.1f vs 30" % (s, zmax))
    print("  pena seed %d: %4d tris  z=[%.1f, %.1f]" % (s, n, zmin, zmax))
suelo(600.0, 600.0)
caja((-45.0, -25.0, 0.0), 10.0)      # dentro del encuadre (hueco entre peñas)
luces()
camara((28.0, 150.0, 30.0), (0.0, 0.0, 13.0), lente=40.0)
render("montanas_v2_pena")

# ---------------------------------------------------------------------------
# 4) Loma: colina verde con peñasco (altibajos junto al circuito)
# ---------------------------------------------------------------------------
limpiar()
col = bpy.data.collections.new("MONT_LOMA")
scene.collection.children.link(col)
root = mod.build_loma(col, alto=28.0, radio=70.0, seed=1)
if root.name != "MONT_loma":
    fallo("raiz de loma: %s" % root.name)
n_loma = sum(tris(o) for o in mallas(root))
resumen["tris"]["loma"] = n_loma
for o in mallas(root):
    if z_min_mundo(o) < Z_MIN_OK:
        fallo("loma/%s: zmin=%.2f" % (o.name, z_min_mundo(o)))
    if o.name.startswith("MONT_pico"):
        # colina TODO verde: ninguna cara de roca en el pico (la cima no
        # debe salir calva alrededor del peñasco)
        n_roca = sum(1 for p in o.data.polygons if p.material_index >= 2)
        if n_roca:
            fallo("loma/%s: %d caras de roca en una colina todo verde" % (o.name, n_roca))
        print("  loma pico: %d caras, %d de roca" % (len(o.data.polygons), n_roca))
print("  loma: %d tris (%s)" % (n_loma, ", ".join(o.name for o in mallas(root))))
# loma ALARGADA (cresta verde con varias cumbres) para bordear la pista
root2 = mod.build_loma(col, alto=22.0, radio=45.0, seed=4, largo=260.0)
root2.location = (-150.0, -130.0, 0.0)
root2.rotation_euler = (0.0, 0.0, math.radians(25.0))
n_loma2 = sum(tris(o) for o in mallas(root2))
resumen["tris"]["loma_larga"] = n_loma2
for o in mallas(root2):
    if z_min_mundo(o) < Z_MIN_OK:
        fallo("loma_larga/%s: zmin=%.2f" % (o.name, z_min_mundo(o)))
    if o.name.startswith("MONT_pico"):
        if o["mont_tipo"] != "cresta":
            fallo("loma larga deberia ser cresta, es %s" % o["mont_tipo"])
        n_roca = sum(1 for p in o.data.polygons if p.material_index >= 2)
        if n_roca:
            fallo("loma_larga/%s: %d caras de roca" % (o.name, n_roca))
        dims = o.dimensions
        if dims.x < 220.0:
            fallo("loma larga: largo %.0f < 220" % dims.x)
        print("  loma larga: %s dims=(%.0f, %.0f, %.0f)" % (o["mont_tipo"], dims.x, dims.y, dims.z))
print("  loma larga: %d tris" % n_loma2)
suelo(1500.0, 1500.0)
caja((-130.0, 40.0, 0.0), 10.0)
luces()
camara((120.0, 300.0, 62.0), (-45.0, -45.0, 12.0), lente=35.0)
render("montanas_v2_loma")

# ---------------------------------------------------------------------------
print("RESUMEN_JSON " + json.dumps(resumen))
if resumen["fallos"]:
    print("TEST_FALLOS: %d" % len(resumen["fallos"]))
    for f in resumen["fallos"]:
        print("  -", f)
    sys.exit(1)
print("TEST_OK")
