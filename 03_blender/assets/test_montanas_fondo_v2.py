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

FASE VISUAL F1 (seccion 5, anillo de horizonte HORIZ_):
  previews/montanas_v2_horizonte_planta.png    el anillo entero desde arriba
                                               (abertura S/SO visible)
  previews/montanas_v2_horizonte_oblicua.png   oblicua desde el S
  previews/montanas_v2_horizonte_piloto_O.png  "piloto" a 40 m mirando al O
                                               (como la toma 54): costa + pueblo
  previews/montanas_v2_horizonte_piloto_S.png  "piloto" en la cima mirando al
                                               SSO (como la 63): islotes + faro
  blend/montanas_fondo_v2_horizonte.blend
Comprueba: 4 + 5 cordilleras, 10 lomas (4 costa + 4 islotes + 2 'ventana': la
de r3 en az 208 y la FIJA de r4 en az 200, 2650 m, 100 m de alto), 3
pueblos, 1 faro; todo HORIZ_* sin padre; <= 250k tris en total; ningun vertice
dentro de la rejilla del terreno (geometria_3d.json) ni bajo z = -8; ninguna
cordillera con picos 'aguja' (r3) ni 'piramide'/'cresta' (r4: solo
domo/lomo/meseta, picos romos; CFG_ANILLO r4 usa solo domo/lomo); cordilleras fuera de la abertura de 160
grados y lomas de costa <= 13 grados dentro; islotes dentro; loma 'ventana'
dentro y a >= 30 grados del centro de la abertura (r3); cobertura angular
del arco de 200 grados >= 95 %; <= 16 materiales MAT_HORIZ_* con custom props
ac_* y diffuse_color = Base Color = paleta mezclada con el cielo (recalculado
desde paleta.json); fila cercana >= 60 % bosque, lejana >= 10 % cumbre.
"""

import importlib.util
import json
import math
import os
import sys
import time
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


def suelo(sx, sy, color=(0.30, 0.47, 0.15), z=-0.02, centro=(0.0, 0.0), nombre_mat="MAT_TEST_suelo"):
    me = bpy.data.meshes.new("TEST_suelo")
    cx, cy = centro
    me.from_pydata([(cx - sx, cy - sy, z), (cx + sx, cy - sy, z),
                    (cx + sx, cy + sy, z), (cx - sx, cy + sy, z)], [], [(0, 1, 2, 3)])
    me.update()
    me.materials.append(mat_plano(nombre_mat, color))
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


def camara(pos, objetivo, lente=35.0, clip=8000.0):
    cam_d = bpy.data.cameras.new("CAM")
    cam_d.lens = lente
    cam_d.clip_end = clip
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
# 5) Anillo de horizonte (fase visual F1, bloque 7.1): HORIZ_*, MAT_HORIZ_*
# ---------------------------------------------------------------------------
LIM_ANILLO = 250000
GEOM = os.path.normpath(os.path.join(BASE, os.pardir, "geometria_3d.json"))
try:
    _T = json.load(open(GEOM, encoding="utf-8"))["terreno"]
    T = {k: _T[k] for k in ("x0", "y0", "cell", "nx", "ny")}
    print("rejilla del terreno de", GEOM, T)
except Exception as e:                       # sin geometria: la rejilla de la ronda 15
    T = dict(x0=-932.9, y0=-907.8, cell=4.0, nx=517, ny=515)
    print("sin geometria_3d.json (%s): rejilla fija %s" % (e, T))
X0, Y0 = T["x0"], T["y0"]
X1, Y1 = X0 + (T["nx"] - 1) * T["cell"], Y0 + (T["ny"] - 1) * T["cell"]
CX, CY = (X0 + X1) * 0.5, (Y0 + Y1) * 0.5


def dang(a, b):
    """Distancia angular (grados, 0..180)."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


limpiar()
col = bpy.data.collections.new("HORIZONTE")
scene.collection.children.link(col)
t0 = time.time()
anillo = mod.build_anillo_horizonte(col, terreno=T, seed=42)
dt_anillo = time.time() - t0
objs = anillo["objetos"]
tris_anillo = anillo["tris"]
resumen["tris"]["anillo_horizonte"] = tris_anillo
resumen["anillo"] = {k: anillo[k] for k in ("tris", "materiales", "centro", "cielo", "abertura")}
resumen["anillo"]["segundos"] = round(dt_anillo, 1)
resumen["anillo"]["cordilleras"] = anillo["cordilleras"]
resumen["anillo"]["lomas"] = anillo["lomas"]
resumen["anillo"]["pueblos"] = anillo["pueblos"]
resumen["anillo"]["faros"] = anillo["faros"]
print("  anillo: %d objetos, %d tris, %d materiales, %.1f s, centro (%.0f, %.0f), cielo %s" %
      (len(objs), tris_anillo, len(anillo["materiales"]), dt_anillo, *anillo["centro"],
       tuple(round(c, 3) for c in anillo["cielo"])))
ab = anillo["abertura"]
c_mat = 90.0 - ab["centro_brujula"]
semi_ab = ab["grados"] * 0.5
print("  abertura: brujula %.1f (mat %.1f) +-%.1f -> anillo %.1f..%.1f (%.0f grados)" %
      (ab["centro_brujula"], c_mat % 360.0, semi_ab, ab["anillo_ini"], ab["anillo_fin"], ab["arco"]))
if tris_anillo > LIM_ANILLO:
    fallo("anillo: %d tris > %d" % (tris_anillo, LIM_ANILLO))
n_cord = len(anillo["cordilleras"]); n_lom = len(anillo["lomas"])
if not (7 <= n_cord <= 9):
    fallo("anillo: %d cordilleras (esperadas 7-9)" % n_cord)
if not (6 <= n_lom <= 10):                   # F1 r3: 4 costa + 4 islotes + 1-2 'ventana' (director r2, menor 7)
    fallo("anillo: %d lomas (esperadas 6-10)" % n_lom)
# F1 r3 (director r2, cosmetico 10): sin picos de aguja en el horizonte (gendarmes alto/radio ~3.5 = agujas a 3-4.5 km)
# F1 r4 (director r3, cosmetico 9): tampoco 'piramide' ni 'cresta' (triangulos de canto): solo domo / lomo / meseta
for ob in objs:
    if ob.name.startswith("HORIZ_cordillera"):
        tipos_c = [t for t in str(ob.get("mont_tipos", "")).split(",") if t]
        malos_t = sorted({t for t in tipos_c if t not in ("domo", "lomo", "meseta")})
        if malos_t:
            fallo("anillo: cordillera %s con picos de tipo %s (r4: solo domo/lomo/meseta)" % (ob.name, malos_t))
        print("  %-22s tipos %s" % (ob.name, ob.get("mont_tipos")))
# F1 r4: la loma FIJA de la acotacion 2 (az 200 = a_fin + 32.5, 2650 m, 120 m) existe y es la ultima del plan
ventanas = [lo for lo in anillo["lomas"] if lo["clase"] == "ventana"]
if len(ventanas) != 2:
    fallo("anillo: %d lomas 'ventana' (esperadas 2: r3 az 208 + r4 az 200)" % len(ventanas))
fijas = [lo for lo in ventanas if abs(lo["r"] - 2650.0) < 0.5 and abs(lo["alto"] - 100.0) < 0.5]
if len(fijas) != 1 or abs(((fijas[0]["az"] - 200.0) + 180.0) % 360.0 - 180.0) > 0.5:
    fallo("anillo: loma fija r4 (az 200, r 2650, alto 100) no encontrada: %s" % [(round(v["az"], 1), round(v["r"]), round(v["alto"])) for v in ventanas])
elif anillo["lomas"][-1]["nombre"] != fijas[0]["nombre"]:
    fallo("anillo: la loma fija r4 debe ser la ULTIMA del plan (no mover los sorteos de r3): %s" % fijas[0]["nombre"])
if not (2 <= len(anillo["pueblos"]) <= 3):
    fallo("anillo: %d pueblos (esperados 2-3)" % len(anillo["pueblos"]))
if len(anillo["faros"]) != 1:
    fallo("anillo: %d faros (esperado 1)" % len(anillo["faros"]))
# objetos: nombre, sin padre, mallas, z, fuera de la rejilla, distancia al centro
d_min_centro = 1e9
for ob in objs:
    if not ob.name.startswith("HORIZ_") or ob.type != "MESH" or ob.parent is not None:
        fallo("anillo: objeto %s (%s, padre %s)" % (ob.name, ob.type, ob.parent))
    mw = mod.matriz_mundo(ob)
    zmin, zmax, dmin = 1e9, -1e9, 1e9
    for v in ob.data.vertices:
        w = mw @ v.co
        zmin = min(zmin, w.z); zmax = max(zmax, w.z)
        dmin = min(dmin, math.hypot(w.x - CX, w.y - CY))
    d_min_centro = min(d_min_centro, dmin)
    if zmin < Z_MIN_OK:
        fallo("anillo/%s: zmin=%.2f < %.1f" % (ob.name, zmin, Z_MIN_OK))
    print("  %-22s %-12s az=%6.1f r=%5.0f tris=%6d z=[%.1f, %.1f] d_centro_min=%.0f" %
          (ob.name, ob.get("horiz_fila", "?"), ob.get("horiz_az", -1), ob.get("horiz_r", -1),
           tris(ob), zmin, zmax, dmin))
malos = mod._fuera_de_rejilla(objs, T)
if malos:
    fallo("anillo: vertices dentro de la rejilla del terreno: %s" % malos)
if d_min_centro < math.hypot(X1 - X0, Y1 - Y0) * 0.5 + 200.0:
    fallo("anillo: pieza a %.0f m del centro (< semidiagonal de la rejilla + 200)" % d_min_centro)
resumen["anillo"]["d_min_centro"] = round(d_min_centro)
# abertura: cordilleras fuera (todo su arco), lomas de costa <= 13 grados dentro, islotes dentro
intervalos = []
for c in anillo["cordilleras"]:
    semi = math.degrees(0.5 * c["largo"] / c["r"])
    if dang(c["az"], c_mat) - semi < semi_ab - 3.0:
        fallo("anillo: cordillera %s (az %.1f +-%.1f) invade la abertura" % (c["nombre"], c["az"], semi))
    intervalos.append((c["az"] - semi, c["az"] + semi))
for lo in anillo["lomas"]:
    d = dang(lo["az"], c_mat)
    if lo["clase"] == "islote" and d > semi_ab - 15.0:
        fallo("anillo: islote %s (az %.1f) fuera de la abertura" % (lo["nombre"], lo["az"]))
    if lo["clase"] == "ventana":
        # F1 r3: dentro de la abertura pero a >= 30 grados de su centro (63/56 siguen mirando a mar abierto)
        if not (30.0 <= d <= semi_ab - 5.0):
            fallo("anillo: loma ventana %s (az %.1f) a %.1f grados del centro de la abertura (debe estar en 30..%.0f)" %
                  (lo["nombre"], lo["az"], d, semi_ab - 5.0))
    elif lo["clase"] != "islote" and d < semi_ab - 13.0:
        fallo("anillo: loma %s (az %.1f) entra %.1f grados en la abertura (> 13)" %
              (lo["nombre"], lo["az"], semi_ab - d))
    if lo["clase"] not in ("islote", "ventana"):
        semi = math.degrees(0.5 * (lo["largo"] or 2 * lo["radio"]) / lo["r"])
        intervalos.append((lo["az"] - semi, lo["az"] + semi))
# cobertura angular del arco [anillo_ini, anillo_fin] por cordilleras + lomas (muestreo de 1 grado)
a0 = ab["anillo_ini"]
cubiertos = 0
for k in range(int(ab["arco"])):
    a = a0 + k + 0.5
    if any(dang(a, (i0 + i1) * 0.5) <= (i1 - i0) * 0.5 for (i0, i1) in intervalos):
        cubiertos += 1
cobertura = cubiertos / max(int(ab["arco"]), 1)
resumen["anillo"]["cobertura_arco"] = round(cobertura, 3)
print("  cobertura angular del arco: %.1f %%" % (cobertura * 100.0))
if cobertura < 0.95:
    fallo("anillo: cobertura angular %.1f %% < 95 %%" % (cobertura * 100.0))
# materiales: nombre, cantidad, props ac_*, diffuse = base color = paleta mezclada con el cielo
mats = [bpy.data.materials[n] for n in anillo["materiales"]]
if len(mats) > 16:
    fallo("anillo: %d materiales MAT_HORIZ_* (> 16)" % len(mats))
cielo = anillo["cielo"]
for m in mats:
    if not m.name.startswith("MAT_HORIZ_"):
        fallo("anillo: material %s sin prefijo MAT_HORIZ_" % m.name)
    for k in ("ac_shader", "ac_props", "ac_samplers", "ac_tex_max", "ac_alpha_test", "ac_raw"):
        if k not in m.keys():
            fallo("anillo: material %s sin custom prop %s" % (m.name, k))
    bs = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    bc = tuple(bs.inputs["Base Color"].default_value[:3]) if bs else None
    dc = tuple(m.diffuse_color[:3])
    if bc is None or bs.inputs["Base Color"].is_linked or max(abs(a - b) for a, b in zip(bc, dc)) > 1e-4:
        fallo("anillo: material %s: Base Color %s != diffuse_color %s (o enlazado)" % (m.name, bc, dc))
    esperado = mod.mezcla_cielo(tuple(m["horiz_base_rgb"]), float(m["horiz_dist_m"]), cielo)
    if max(abs(a - b) for a, b in zip(esperado, dc)) > 1e-4:
        fallo("anillo: material %s: color %s != paleta mezclada %s" % (m.name, dc, esperado))
    print("  %-32s diffuse=%s base=%s d=%.0f shader=%s" %
          (m.name, tuple(round(c, 3) for c in dc), tuple(round(c, 3) for c in m["horiz_base_rgb"]),
           m["horiz_dist_m"], m["ac_shader"]))
# reparto bosque / cumbre por fila
for fila, minimo, es_bosque in (("cerca", 0.60, True), ("lejos", 0.10, False)):
    n_b = n_t = 0
    for ob in objs:
        if ob.get("horiz_fila") != fila:
            continue
        for p in ob.data.polygons:
            n_t += 1
            if "bosque" in ob.data.materials[p.material_index].name:
                n_b += 1
    frac = (n_b if es_bosque else n_t - n_b) / max(n_t, 1)
    print("  fila %s: %.1f %% de caras de %s" % (fila, frac * 100.0, "bosque" if es_bosque else "cumbre"))
    if frac < minimo:
        fallo("anillo: fila %s con solo %.1f %% de %s (< %.0f %%)" %
              (fila, frac * 100.0, "bosque" if es_bosque else "cumbre", minimo * 100.0))
for pu in anillo["pueblos"]:
    if pu["tris"] > 300:
        fallo("anillo: pueblo %s con %d tris (> 300)" % (pu["nombre"], pu["tris"]))
for fa in anillo["faros"]:
    if fa["tris"] > 200 or fa["z"] < 30.0:
        fallo("anillo: faro %s con %d tris o z=%.1f (debe estar en la cima del islote)" %
              (fa["nombre"], fa["tris"], fa["z"]))
# previews: mar + sol + cielo
suelo(12000.0, 12000.0, color=(0.03, 0.18, 0.38), z=-0.02, centro=(CX, CY), nombre_mat="MAT_TEST_mar")
caja((CX, CY, 0.0), 100.0)
luces()
camara((CX, CY - 1.0, 7000.0), (CX, CY, 0.0), lente=20.0, clip=20000.0)
render("montanas_v2_horizonte_planta")
camara((CX + 300.0, CY - 6500.0, 2600.0), (CX, CY + 800.0, 0.0), lente=24.0, clip=20000.0)
render("montanas_v2_horizonte_oblicua")
az54 = math.radians(190.0)
camara((CX + 20.0, CY - 790.0, 40.0), (CX + 20.0 + math.cos(az54) * 100.0, CY - 790.0 + math.sin(az54) * 100.0, 30.0),
       lente=24.0, clip=12000.0)
render("montanas_v2_horizonte_piloto_O")
az63 = math.radians(240.0)
camara((CX - 20.0, CY + 180.0, 120.0), (CX - 20.0 + math.cos(az63) * 100.0, CY + 180.0 + math.sin(az63) * 100.0, 108.0),
       lente=20.0, clip=12000.0)
render("montanas_v2_horizonte_piloto_S")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BASE, "blend", "montanas_fondo_v2_horizonte.blend"))
print("BLEND:", os.path.join(BASE, "blend", "montanas_fondo_v2_horizonte.blend"))

# ---------------------------------------------------------------------------
print("RESUMEN_JSON " + json.dumps(resumen))
if resumen["fallos"]:
    print("TEST_FALLOS: %d" % len(resumen["fallos"]))
    for f in resumen["fallos"]:
        print("  -", f)
    sys.exit(1)
print("TEST_OK")
