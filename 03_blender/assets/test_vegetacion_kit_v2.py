"""test_vegetacion_kit_v2.py — Test headless del kit de vegetación v2 (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python
  "E:\\Escritorio\\claude-pc\\arnau-aseto-corsa\\03_blender\\assets\\test_vegetacion_kit_v2.py"

Renderiza (EEVEE, sol + cielo suave):
  previews/vegetacion_kit_v2.png      muestrario build() (1280x720) + blend/vegetacion_kit_v2.blend
  previews/veg_v2_fam_<familia>.png   4 seeds de cada familia, vista lateral cercana (1280x720)
  previews/veg_v2_familias.png        line-up de todos los tipos x 4 seeds: 4 paneles
                                      apilados de 1280x360 (1280x1440), caja 2 m en cada uno
  previews/veg_v2_ladera.png          ladera aleatoria de ~80 árboles (build_arbol) a 60 m
Comprueba: <= 1200 tris por árbol, <= 500 por arbusto/adelfa, nada flota,
altura real vs nominal, tope de tamaño de pino joven / palmito automáticos,
ValueError con variante desconocida.
"""

import importlib.util
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(BASE, "vegetacion_kit_v2.py")
PREV = os.path.join(BASE, "previews")
os.makedirs(PREV, exist_ok=True)

LIM_ARBOL = 1200
LIM_ARBUSTO = 500
ARBUSTOS = ("adelfa", "arbusto")
TAN_H35 = 18.0 / 35.0          # tan(semi-FOV horizontal) de la lente de 35 mm (sensor 36 mm)


def limpiar():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    for cu in list(bpy.data.curves):
        bpy.data.curves.remove(cu)
    for ma in list(bpy.data.materials):
        bpy.data.materials.remove(ma)
    for co in list(bpy.data.collections):
        bpy.data.collections.remove(co)


limpiar()
spec = importlib.util.spec_from_file_location("vegetacion_kit_v2", MOD_PATH)
veg = importlib.util.module_from_spec(spec)
sys.modules["vegetacion_kit_v2"] = veg
spec.loader.exec_module(veg)

scene = bpy.context.scene


# ---------------------------------------------------------------------------
# utilidades de test
# ---------------------------------------------------------------------------
def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def mat_plano(nombre, color, rough=0.9):
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (*color, 1.0)
    bs.inputs["Roughness"].default_value = rough
    return m


def suelo(nombre, sx, sy, color, z=-0.02, centro=(0.0, 0.0)):
    me = bpy.data.meshes.new(nombre)
    cx, cy = centro
    me.from_pydata([(cx - sx, cy - sy, z), (cx + sx, cy - sy, z), (cx + sx, cy + sy, z), (cx - sx, cy + sy, z)],
                   [], [(0, 1, 2, 3)])
    me.update()
    me.materials.append(mat_plano("MAT_TEST_" + nombre, color))
    ob = bpy.data.objects.new(nombre, me)
    scene.collection.objects.link(ob)
    return ob


def caja_escala(pos, lado=2.0):
    """Caja de referencia de 2 m (blanca con tapa roja)."""
    v, f = veg._box(lado, lado, lado, off=(pos[0], pos[1], pos[2] + lado / 2.0))
    me = bpy.data.meshes.new("TEST_caja2m")
    me.from_pydata(v, [], f)
    me.update()
    me.materials.append(mat_plano("MAT_TEST_caja", (0.92, 0.92, 0.92)))
    me.materials.append(mat_plano("MAT_TEST_caja_top", (0.85, 0.10, 0.10)))
    me.polygons[1].material_index = 1
    ob = bpy.data.objects.new("TEST_caja2m", me)
    scene.collection.objects.link(ob)
    return ob


def texto(nombre, txt, tam, pos, color=(0.08, 0.08, 0.08)):
    """Cartel 3D de pie, legible desde +Y (cámara delante)."""
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


def ancho_texto(txt, tam):
    """Ancho aproximado de un rótulo (fuente por defecto de Blender)."""
    return 0.62 * tam * len(txt)


def luces(sol_dir=(-0.42, -0.55, -0.72)):
    sol_d = bpy.data.lights.new("SOL", type="SUN")
    sol_d.energy = 2.6
    sol_d.color = (1.0, 0.96, 0.90)
    try:
        sol_d.angle = math.radians(3.0)
    except AttributeError:
        pass
    sol = bpy.data.objects.new("SOL", sol_d)
    scene.collection.objects.link(sol)
    sol.rotation_euler = Vector(sol_dir).to_track_quat("-Z", "Y").to_euler()

    mundo = bpy.data.worlds.get("CIELO") or bpy.data.worlds.new("CIELO")
    mundo.use_nodes = True
    fondo = next((n for n in mundo.node_tree.nodes if n.type == "BACKGROUND"), None)
    if fondo is not None:
        fondo.inputs[0].default_value = (0.50, 0.72, 0.98, 1.0)
        fondo.inputs[1].default_value = 0.60
    scene.world = mundo


def camara(pos, objetivo, lente=35.0):
    cam_d = bpy.data.cameras.new("CAM_veg")
    cam_d.lens = lente
    cam_d.clip_end = 1500.0
    cam = bpy.data.objects.new("CAM_veg", cam_d)
    scene.collection.objects.link(cam)
    cam.location = Vector(pos)
    d = Vector(objetivo) - Vector(pos)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def preparar_render(res_y=720):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = 1280
    scene.render.resolution_y = res_y
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
    return png


def apilar_png(paths, out):
    """Apila verticalmente varios PNG del mismo ancho (el primero arriba)."""
    imgs = [bpy.data.images.load(p) for p in paths]
    W = imgs[0].size[0]
    H = sum(im.size[1] for im in imgs)
    res = bpy.data.images.new("VEG_STACK", W, H, alpha=True)
    buf = np.empty(W * H * 4, dtype=np.float32)
    y = H
    for im in imgs:
        assert im.size[0] == W, "anchos distintos"
        h = im.size[1]
        px = np.empty(W * h * 4, dtype=np.float32)
        im.pixels.foreach_get(px)
        y -= h
        buf[y * W * 4:(y + h) * W * 4] = px
    res.pixels.foreach_set(buf)
    res.filepath_raw = out
    res.file_format = "PNG"
    res.save()
    for im in imgs:
        bpy.data.images.remove(im)
    bpy.data.images.remove(res)
    assert os.path.isfile(out), "no se genero " + out
    print("PNG:", out, "(%dx%d)" % (W, H))
    return out


preparar_render()
print("Engine:", scene.render.engine)

# ---------------------------------------------------------------------------
# Definición de familias: (nombre, builder(col, seed), altura ref, separación)
# ---------------------------------------------------------------------------
FAMILIAS = [
    ("platano", lambda c, s: veg.build_platano(c, alto=14.0, seed=s), 14.0, 13.0),
    ("pino",    lambda c, s: veg.build_pino(c, alto=12.0, seed=s),    12.0, 14.0),
    ("encina",  lambda c, s: veg.build_encina(c, alto=9.0, seed=s),    9.0, 10.0),
    ("palmera", lambda c, s: veg.build_palmera(c, alto=8.0, seed=s),   8.0,  9.0),
    ("cipres",  lambda c, s: veg.build_cipres(c, alto=10.0, seed=s),  10.0,  5.0),
    ("olivo",   lambda c, s: veg.build_olivo(c, alto=5.0, seed=s),     5.0,  6.5),
    ("adelfa",  lambda c, s: veg.build_adelfa(c, seed=s),              2.6,  4.0),
    ("arbusto", lambda c, s: veg.build_arbusto(c, tam=1.5, seed=s),    1.3,  2.2),
]
SEEDS = (0, 1, 2, 3)
fam_map = {f[0]: f for f in FAMILIAS}

stats = {}      # familia -> lista de (seed, tris)
fallos = []


def registrar(fam, seed, ob):
    n = tris(ob)
    lim = LIM_ARBUSTO if fam in ARBUSTOS else LIM_ARBOL
    stats.setdefault(fam, []).append((seed, n))
    if n > lim:
        fallos.append("%s seed=%d: %d tris > %d" % (fam, seed, n, lim))
    # pieza en el suelo (nada flotando): el punto más bajo debe estar <= 0.05
    zmin = min(v.co.z for v in ob.data.vertices)
    zmax = max(v.co.z for v in ob.data.vertices)
    if zmin > 0.05:
        fallos.append("%s seed=%d: zmin=%.2f (flota)" % (fam, seed, zmin))
    return n, zmin, zmax


# ---------------------------------------------------------------------------
# 0) Muestrario del contrato: build() -> previews/vegetacion_kit_v2.png + .blend
# ---------------------------------------------------------------------------
limpiar()
col = bpy.data.collections.new("VEG_KIT")
scene.collection.children.link(col)
root = veg.build(col, seed=1)
assert root.name == "VEG_muestrario", root.name
n_obj = sum(1 for o in col.objects if o.type == "MESH")
print("Muestrario: raiz %s, %d mallas" % (root.name, n_obj))
for ob in col.objects:
    if ob.type == "MESH":
        n = tris(ob)
        assert n <= 2000 or ob.name.startswith("VEG_acantilado"), (ob.name, n)
suelo("suelo", 400.0, 400.0, (0.55, 0.42, 0.24))
luces()
camara((0.0, 99.0, 16.0), (0.0, -8.0, 8.0), lente=30.0)   # semiancho visible en y=0: ~59 m
render("vegetacion_kit_v2")

blend_dir = os.path.join(BASE, "blend")
os.makedirs(blend_dir, exist_ok=True)
blend_path = os.path.join(blend_dir, "vegetacion_kit_v2.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("BLEND:", blend_path)

# ---------------------------------------------------------------------------
# 1) Primeros planos por familia (4 seeds, vista lateral, 1280x720)
# ---------------------------------------------------------------------------
for fam, fn, href, sep in FAMILIAS:
    limpiar()
    col = bpy.data.collections.new("VEG_FAM_" + fam)
    scene.collection.children.link(col)
    xs = [(i - 1.5) * sep for i in range(4)]
    for i, s in enumerate(SEEDS):
        ob = fn(col, s)
        ob.location = (xs[i], 0.0, 0.0)
        n, zmin, zmax = registrar(fam, s, ob)
        print("  %-8s seed=%d  %4d tris  z=[%.2f, %.2f]  %-12s %s"
              % (fam, s, n, zmin, zmax, ob.get("VEG_variante", "-"), ob.name))
    ancho = xs[-1] - xs[0] + sep * 1.6
    suelo("suelo", 400.0, 400.0, (0.42, 0.50, 0.24))
    luces()
    # cámara a media altura; distancia para abarcar la fila Y para que el
    # rótulo (izquierda en imagen = +X) y la caja de 2 m (derecha = -X)
    # queden dentro del semiancho visible (dist * tan(FOV/2) con lente 35)
    tam_txt = max(0.5, href * 0.07)
    w_txt = ancho_texto(fam.upper(), tam_txt)
    dist = max(ancho, href * 1.9) * 1.02
    necesario = max(xs[-1] + sep * 0.55 + 1.0 + w_txt, -(xs[0] - sep * 0.55 - 1.0) + 2.4)
    dist = max(dist, necesario / (TAN_H35 * 0.93))
    half_vis = TAN_H35 * dist * 0.93
    caja_escala((-(half_vis - 1.3), 0.0, 0.0))
    texto("rotulo", fam.upper(), tam_txt, (half_vis - w_txt / 2.0 - 0.3, 0.0, 0.0))
    camara((0.0, dist, href * 0.45 + 0.5), (0.0, 0.0, href * 0.45), lente=35.0)
    render("veg_v2_fam_" + fam)

# ---------------------------------------------------------------------------
# 2) Line-up general: 4 paneles de 1280x360 (una fila cada uno, lateral),
#    apilados en previews/veg_v2_familias.png (1280x1440)
# ---------------------------------------------------------------------------
PANELES = (
    ("altos1", ["platano", "pino"], ()),
    ("altos2", ["encina", "palmera", "cipres"], ()),
    ("medios", ["olivo", "adelfa"], ()),
    ("bajos",  ["arbusto"], (("jardinera", lambda c: veg.build_jardinera(c, largo=6.0, seed=0), 8.0),
                             ("roca 3 m", lambda c: veg.build_roca(c, tam=3.0, seed=0), 4.5),
                             ("roca 5 m", lambda c: veg.build_roca(c, tam=5.0, seed=9), 6.5))),
)
CAJA_W = 3.5
FSEP = 0.82                    # separación de la fila relativa a la del primer plano
TAN_V360 = (36.0 * 360.0 / 1280.0 / 2.0) / 35.0   # tan(semi-FOV vertical) del panel 1280x360


def panel(nombre, fams, extras):
    limpiar()
    col = bpy.data.collections.new("VEG_PANEL_" + nombre)
    scene.collection.children.link(col)
    ancho = sum(4.0 * fam_map[f][3] * FSEP + 3.0 for f in fams) + sum(w for (_, _, w) in extras) + CAJA_W
    href = max([fam_map[f][2] for f in fams] + [2.0])
    dist = (ancho / 2.0 + 1.5) / (TAN_H35 * 0.97)
    tam_rot = 0.02 * dist      # ~7 % de la altura visible del panel
    x = -ancho / 2.0
    rotulos = []
    for fam in fams:
        _, fn, _, sep = fam_map[fam]
        sep *= FSEP
        for i, s in enumerate(SEEDS):
            ob = fn(col, s)
            ob.location = (x + sep * (i + 0.5), 0.0, 0.0)
        rotulos.append((fam, x + 2.0 * sep))
        x += 4.0 * sep + 3.0
    for (etq, fn_extra, w) in extras:
        ob = fn_extra(col)
        ob.location = (x + w / 2.0, 0.0, 0.0)
        rotulos.append((etq, x + w / 2.0))
        x += w
    caja_escala((x + CAJA_W / 2.0, 0.0, 0.0))
    rotulos.append(("2 m", x + CAJA_W / 2.0))   # rótulo corto: no desborda el encuadre
    # rótulos de pie delante de cada bloque
    for k, (etq, cx) in enumerate(rotulos):
        texto("rot_%d" % k, etq, tam_rot, (cx, 3.0 + tam_rot * 0.6, 0.0))
    suelo("suelo", 600.0, 600.0, (0.42, 0.50, 0.24))
    luces()
    # cámara casi horizontal; altura tal que la base de la fila quede al
    # ~72 % de la altura del panel (menos suelo vacío)
    hc = 0.55 * TAN_V360 * dist
    camara((0.0, dist, hc), (0.0, 0.0, hc - 0.02 * dist), lente=35.0)
    print("Panel %s: ancho %.0f m, dist %.0f m" % (nombre, ancho, dist))
    return render("veg_v2_panel_" + nombre)


preparar_render(res_y=360)
paneles_png = [panel(n, f, e) for (n, f, e) in PANELES]
preparar_render(res_y=720)
apilar_png(paneles_png, os.path.join(PREV, "veg_v2_familias.png"))
for p in paneles_png:
    os.remove(p)

# ---------------------------------------------------------------------------
# 3) Ladera aleatoria con build_arbol (~80 piezas) vista a 60 m
# ---------------------------------------------------------------------------
limpiar()
col = bpy.data.collections.new("VEG_V2_LADERA")
scene.collection.children.link(col)


def z_terreno(x, y):
    # ladera que sube al alejarse de la cámara (+Y hacia la cámara) con lomas
    return (0.16 * (30.0 - y) + 3.0 * math.sin(x * 0.045 + 0.8) * math.cos(y * 0.06)
            + 1.5 * math.sin(x * 0.11 - y * 0.07))


# malla de terreno 2 m
NX, NY = 110, 70
X0, Y0 = -110.0, -90.0
verts = []
for j in range(NY + 1):
    for i in range(NX + 1):
        xx, yy = X0 + i * 2.0, Y0 + j * 2.0
        verts.append((xx, yy, z_terreno(xx, yy) - 0.05))
faces = []
for j in range(NY):
    for i in range(NX):
        a = j * (NX + 1) + i
        faces.append((a, a + 1, a + NX + 2, a + NX + 1))
me = bpy.data.meshes.new("TEST_ladera")
me.from_pydata(verts, [], faces)
me.update()
me.materials.append(mat_plano("MAT_TEST_ladera", (0.40, 0.48, 0.22)))
for p in me.polygons:
    p.use_smooth = True
ter = bpy.data.objects.new("TEST_ladera", me)
scene.collection.objects.link(ter)

rng = random.Random(2024)
puntos = []
N_ARB = 80
intentos = 0
tipos_ladera = {}
while len(puntos) < N_ARB and intentos < 4000:
    intentos += 1
    px, py = rng.uniform(-75.0, 75.0), rng.uniform(-70.0, 28.0)
    if any((px - qx) ** 2 + (py - qy) ** 2 < 5.5 ** 2 for (qx, qy) in puntos):
        continue
    puntos.append((px, py))
    i = len(puntos) - 1
    ob = veg.build_arbol(col, seed=100 + i)
    tipo = ob["VEG_tipo"]
    tipos_ladera[tipo] = tipos_ladera.get(tipo, 0) + 1
    n = tris(ob)
    lim = LIM_ARBUSTO if tipo in ARBUSTOS else LIM_ARBOL
    if n > lim:
        fallos.append("ladera %s seed=%d: %d tris > %d" % (tipo, 100 + i, n, lim))
    ob.location = (px, py, z_terreno(px, py) - 0.12)
    ob.rotation_euler = (0.0, 0.0, rng.uniform(0.0, math.tau))
print("Ladera: %d piezas, mezcla: %s" % (len(puntos), tipos_ladera))
print("Ladera: tris totales = %d" % sum(tris(o) for o in col.objects))

luces(sol_dir=(-0.35, -0.60, -0.62))
camara((0.0, 90.0, z_terreno(0.0, 90.0) + 20.0), (0.0, -12.0, z_terreno(0.0, -12.0) + 5.0), lente=38.0)
render("veg_v2_ladera")

# ---------------------------------------------------------------------------
# 4) Comprobaciones numéricas (sin render)
# ---------------------------------------------------------------------------
limpiar()
col = bpy.data.collections.new("VEG_CHECK")
scene.collection.children.link(col)


def dims(ob):
    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs))


# 4a) altura real / nominal por familia y variante (12 seeds)
print("== Altura real / nominal (12 seeds) ==")
ALTOS = {"platano": (veg.build_platano, 14.0), "pino": (veg.build_pino, 12.0),
         "encina": (veg.build_encina, 9.0), "palmera": (veg.build_palmera, 8.0),
         "cipres": (veg.build_cipres, 10.0), "olivo": (veg.build_olivo, 5.0)}
for fam, (fn, alto) in ALTOS.items():
    ratios = {}
    for s in range(12):
        ob = fn(col, alto=alto, seed=s)
        var = ob.get("VEG_variante", "-")
        ratios.setdefault(var, []).append(dims(ob)[2] / alto)
        bpy.data.objects.remove(ob, do_unlink=True)
    for var, rs in ratios.items():
        # las variantes pequeñas por naturaleza (joven/abanico) se limitan a
        # 7 / 5 m con reparto automático: su ratio se mide contra ese tope
        tope = {"joven": 7.0, "abanico": 5.0}.get(var, alto)
        real = [r * alto / tope for r in rs]
        print("  %-8s %-13s real/nominal %.2f .. %.2f (nominal efectivo %.0f m)"
              % (fam, var, min(real), max(real), tope))
        if min(real) < 0.88 or max(real) > 1.08:
            fallos.append("%s %s: altura real/nominal fuera de 0.88..1.08 (%.2f..%.2f)"
                          % (fam, var, min(real), max(real)))

# 4b) llamadas exactas de integrar_escena.py con variantes pequeñas
ob = veg.build_pino(col, alto=13.0, seed=11)
w, d, h = dims(ob)
print("  build_pino(alto=13, seed=11) -> %s %.1f m alto x %.1f m ancho" % (ob["VEG_variante"], h, w))
if ob["VEG_variante"] == "joven" and h > 7.3:
    fallos.append("pino joven automático no limitado: %.1f m" % h)
bpy.data.objects.remove(ob, do_unlink=True)
ob = veg.build_palmera(col, alto=10.0, seed=32)
w, d, h = dims(ob)
print("  build_palmera(alto=10, seed=32) -> %s %.1f m alto x %.1f m ancho" % (ob["VEG_variante"], h, w))
if ob["VEG_variante"] == "abanico" and (h > 5.3 or w > 7.5):
    fallos.append("palmito automático no limitado: %.1f x %.1f m" % (h, w))
bpy.data.objects.remove(ob, do_unlink=True)
# variante explícita: se respeta el alto pedido
ob = veg.build_pino(col, alto=13.0, seed=11, variante="joven")
h = dims(ob)[2]
print("  build_pino(alto=13, seed=11, variante='joven') -> %.1f m (explícito, sin tope)" % h)
if h < 11.5:
    fallos.append("pino joven explícito no respeta alto: %.1f" % h)
bpy.data.objects.remove(ob, do_unlink=True)

# 4c) variante desconocida -> ValueError en cada builder
for fn, kw in ((veg.build_pino, {"alto": 10.0}), (veg.build_palmera, {"alto": 8.0}),
               (veg.build_cipres, {"alto": 8.0}), (veg.build_adelfa, {}),
               (veg.build_arbusto, {"tam": 1.5})):
    try:
        fn(col, seed=0, variante="zzz", **kw)
    except ValueError:
        pass
    else:
        fallos.append("%s acepta variante desconocida" % fn.__name__)
print("  variante desconocida -> ValueError: OK")

# 4d) cada árbol: tronco cerrado por abajo (ninguna arista de borde a z<=0.02
#     del tronco); comprobación de mallas cerradas en troncos via caras
#     cuyo centro está bajo 0.02 m con normal hacia -Z
for fam, (fn, alto) in ALTOS.items():
    ob = fn(col, alto=alto, seed=3)
    me = ob.data
    tapa = any(p.normal.z < -0.5 and p.center.z < 0.02 for p in me.polygons)
    if not tapa:
        fallos.append("%s: sin tapa inferior en el tronco" % fam)
    bpy.data.objects.remove(ob, do_unlink=True)
print("  tapas inferiores de tronco: OK")

# ---------------------------------------------------------------------------
# resumen
# ---------------------------------------------------------------------------
print("== Triangulos por familia (arbol <= %d, arbusto <= %d) ==" % (LIM_ARBOL, LIM_ARBUSTO))
for fam, _, _, _ in FAMILIAS:
    ns = [n for (_, n) in stats[fam]]
    print("  %-8s min %4d  max %4d  (seeds %s)" % (fam, min(ns), max(ns), [n for n in ns]))
if fallos:
    print("FALLOS:")
    for f in fallos:
        print("  - " + f)
    raise SystemExit("test_vegetacion_kit_v2: %d fallos" % len(fallos))
print("OK test_vegetacion_kit_v2")
