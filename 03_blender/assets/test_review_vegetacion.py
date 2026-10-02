"""test_review_vegetacion.py — Revisión independiente de vegetacion_kit_v2.py.

Mide tris/alturas/base sobre muchos seeds, comprueba la API y renderiza con
BACKFACE CULLING activado (como Assetto Corsa) desde cámara a ras de pista.
No modifica el módulo. Salidas: previews/review_veg_*.png
"""

import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(BASE, "vegetacion_kit_v2.py")
PREV = os.path.join(BASE, "previews")
os.makedirs(PREV, exist_ok=True)


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


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bbox(ob):
    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


# ---------------------------------------------------------------------------
# 1) API: firmas
# ---------------------------------------------------------------------------
import inspect
for fn in ("build_palmera", "build_cipres", "build_pino", "build_adelfa", "build_jardinera",
           "build_roca", "build_acantilado", "build", "build_olivo", "build_encina",
           "build_platano", "build_arbusto", "build_arbol"):
    print("API", fn, inspect.signature(getattr(veg, fn)))

# ---------------------------------------------------------------------------
# 2) Estadísticas sobre muchos seeds
# ---------------------------------------------------------------------------
col = bpy.data.collections.new("REV")
scene.collection.children.link(col)

FAM = {
    "pino":    lambda s, a: veg.build_pino(col, alto=a, seed=s),
    "cipres":  lambda s, a: veg.build_cipres(col, alto=a, seed=s),
    "palmera": lambda s, a: veg.build_palmera(col, alto=a, seed=s),
    "olivo":   lambda s, a: veg.build_olivo(col, alto=a, seed=s),
    "encina":  lambda s, a: veg.build_encina(col, alto=a, seed=s),
    "platano": lambda s, a: veg.build_platano(col, alto=a, seed=s),
    "adelfa":  lambda s, a: veg.build_adelfa(col, seed=s),
    "arbusto": lambda s, a: veg.build_arbusto(col, tam=a, seed=s),
}
ALTO = {"pino": 12.0, "cipres": 10.0, "palmera": 8.0, "olivo": 5.0, "encina": 9.0,
        "platano": 14.0, "adelfa": 0.0, "arbusto": 1.5}
LIM = {"adelfa": 500, "arbusto": 500}
problemas = []
print("== estadisticas 40 seeds por familia ==")
for fam, fn in FAM.items():
    ts, hs, zmins, nmats, footprints, validated = [], [], [], [], [], 0
    for s in range(40):
        ob = fn(s, ALTO[fam])
        assert ob.name.startswith("VEG_" + fam), ob.name
        n = tris(ob)
        ts.append(n)
        x0, x1, y0, y1, z0, z1 = bbox(ob)
        hs.append(z1)
        zmins.append(z0)
        footprints.append(max(x1 - x0, y1 - y0))
        nmats.append(len(ob.data.materials))
        for m in ob.data.materials:
            assert m.name.startswith("MAT_VEG_"), m.name
        lim = LIM.get(fam, 1200)
        if n > lim:
            problemas.append("%s seed=%d %d tris > %d" % (fam, s, n, lim))
        if z0 > 0.05:
            problemas.append("%s seed=%d flota zmin=%.2f" % (fam, s, z0))
        # validate() devuelve True si tuvo que corregir algo (geometria invalida)
        me2 = ob.data.copy()
        if me2.validate(verbose=False):
            validated += 1
        bpy.data.meshes.remove(me2)
        bpy.data.objects.remove(ob, do_unlink=True)
    print("  %-8s tris %4d..%4d  alto %.2f..%.2f (param %.1f)  zmin %.2f..%.2f  ancho %.1f..%.1f  mats %d..%d  validate-fixes %d"
          % (fam, min(ts), max(ts), min(hs), max(hs), ALTO[fam], min(zmins), max(zmins),
             min(footprints), max(footprints), min(nmats), max(nmats), validated))

# variantes forzadas: alturas relativas
print("== altura real / alto param por variante ==")
for fam, vars_, fn in (
        ("pino", ("parasol", "carrasco", "costero", "joven"),
         lambda s, v: veg.build_pino(col, alto=10.0, seed=s, variante=v)),
        ("cipres", ("lapiz", "llama"), lambda s, v: veg.build_cipres(col, alto=10.0, seed=s, variante=v)),
        ("palmera", ("datil", "washingtonia", "abanico"),
         lambda s, v: veg.build_palmera(col, alto=10.0, seed=s, variante=v)),
        ("adelfa", ("rosa", "blanca", "roja"), lambda s, v: veg.build_adelfa(col, seed=s, variante=v)),
        ("arbusto", ("romero", "lavanda", "retama"), lambda s, v: veg.build_arbusto(col, tam=1.5, seed=s, variante=v))):
    for v in vars_:
        hs, ws, ts = [], [], []
        for s in range(12):
            ob = fn(s, v)
            x0, x1, y0, y1, z0, z1 = bbox(ob)
            hs.append(z1)
            ws.append(max(x1 - x0, y1 - y0))
            ts.append(tris(ob))
            bpy.data.objects.remove(ob, do_unlink=True)
        print("  %-8s %-12s alto %.2f..%.2f  ancho %.2f..%.2f  tris %d..%d" % (fam, v, min(hs), max(hs), min(ws), max(ws), min(ts), max(ts)))

# build_arbol: 300 seeds, mezcla y presupuesto
mezcla = {}
for s in range(300):
    ob = veg.build_arbol(col, seed=s)
    t = ob["VEG_tipo"]
    mezcla[t] = mezcla.get(t, 0) + 1
    n = tris(ob)
    if n > LIM.get(t, 1200):
        problemas.append("arbol %s seed=%d %d tris" % (t, s, n))
    bpy.data.objects.remove(ob, do_unlink=True)
print("build_arbol mezcla 300:", mezcla)
try:
    veg.build_arbol(col, tipo="xxx")
    problemas.append("build_arbol tipo desconocido no lanza ValueError")
except ValueError:
    pass

# llamadas exactas de integrar_escena.py
print("== llamadas integrar_escena ==")
llamadas = [
    ("palmera alto=8", lambda: veg.build_palmera(col, alto=8)),
    ("palmera alto=6.5 seed=3", lambda: veg.build_palmera(col, alto=6.5, seed=3)),
    ("cipres alto=10", lambda: veg.build_cipres(col, alto=10)),
    ("pino alto=12", lambda: veg.build_pino(col, alto=12)),
    ("pino alto=9 seed=5", lambda: veg.build_pino(col, alto=9, seed=5)),
    ("adelfa", lambda: veg.build_adelfa(col)),
    ("jardinera largo=6", lambda: veg.build_jardinera(col, largo=6)),
    ("roca tam=3", lambda: veg.build_roca(col, tam=3)),
    ("roca tam=5 seed=9", lambda: veg.build_roca(col, tam=5, seed=9)),
    ("pino alto=13 seed=11", lambda: veg.build_pino(col, alto=13, seed=11)),
    ("pino alto=10 seed=12", lambda: veg.build_pino(col, alto=10, seed=12)),
    ("pino alto=14 seed=13", lambda: veg.build_pino(col, alto=14, seed=13)),
    ("pino alto=8 seed=14", lambda: veg.build_pino(col, alto=8, seed=14)),
    ("cipres 9 s21", lambda: veg.build_cipres(col, alto=9, seed=21)),
    ("cipres 11 s22", lambda: veg.build_cipres(col, alto=11, seed=22)),
    ("palmera 7 s31", lambda: veg.build_palmera(col, alto=7, seed=31)),
    ("palmera 10 s32", lambda: veg.build_palmera(col, alto=10, seed=32)),
    ("palmera 13 s33", lambda: veg.build_palmera(col, alto=13, seed=33)),
    ("adelfa s41", lambda: veg.build_adelfa(col, seed=41)),
    ("adelfa s42", lambda: veg.build_adelfa(col, seed=42)),
]
for nombre, f in llamadas:
    ob = f()
    x0, x1, y0, y1, z0, z1 = bbox(ob)
    var = ""
    if ob.name.startswith("VEG_pino"):
        var = veg._PINO_VARIANTES[(int(nombre.split("seed=")[1]) if "seed=" in nombre else (int(nombre.split("s")[-1]) if " s" in nombre else 0)) % 4]
    print("  %-24s %-14s %4d tris  alto %.1f  ancho %.1f  zmin %.2f %s" % (nombre, ob.name, tris(ob), z1, max(x1 - x0, y1 - y0), z0, var))
    bpy.data.objects.remove(ob, do_unlink=True)

# ---------------------------------------------------------------------------
# 3) Renders con backface culling (AC) desde la pista
# ---------------------------------------------------------------------------
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


def suelo(sx, sy, color, z=-0.02):
    me = bpy.data.meshes.new("suelo")
    me.from_pydata([(-sx, -sy, z), (sx, -sy, z), (sx, sy, z), (-sx, sy, z)], [], [(0, 1, 2, 3)])
    me.update()
    me.materials.append(mat_plano("MAT_TEST_suelo", color))
    ob = bpy.data.objects.new("suelo", me)
    scene.collection.objects.link(ob)
    return ob


def luces(sol_dir=(-0.42, -0.55, -0.72)):
    sol_d = bpy.data.lights.new("SOL", type="SUN")
    sol_d.energy = 2.6
    sol_d.color = (1.0, 0.96, 0.90)
    sol_d.angle = math.radians(3.0)
    sol = bpy.data.objects.new("SOL", sol_d)
    scene.collection.objects.link(sol)
    sol.rotation_euler = Vector(sol_dir).to_track_quat("-Z", "Y").to_euler()
    mundo = bpy.data.worlds.get("CIELO") or bpy.data.worlds.new("CIELO")
    mundo.use_nodes = True
    fondo = next((n for n in mundo.node_tree.nodes if n.type == "BACKGROUND"), None)
    fondo.inputs[0].default_value = (0.50, 0.72, 0.98, 1.0)
    fondo.inputs[1].default_value = 0.60
    scene.world = mundo


def camara(pos, objetivo, lente=35.0):
    cam_d = bpy.data.cameras.new("CAM")
    cam_d.lens = lente
    cam_d.clip_end = 1500.0
    cam = bpy.data.objects.new("CAM", cam_d)
    scene.collection.objects.link(cam)
    cam.location = Vector(pos)
    d = Vector(objetivo) - Vector(pos)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
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
    scene.render.resolution_y = 720
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


def culling_on():
    for m in bpy.data.materials:
        if m.name.startswith("MAT_VEG_"):
            m.use_backface_culling = True
            try:
                m.use_backface_culling_shadow = True
            except AttributeError:
                pass


def render(nombre):
    png = os.path.join(PREV, nombre + ".png")
    scene.render.filepath = png
    bpy.ops.render.render(write_still=True)
    assert os.path.isfile(png)
    print("PNG:", png)


preparar_render()

# A) a ras de pista, culling ON: fila de variantes problemáticas de cerca
limpiar()
col = bpy.data.collections.new("REV_A")
scene.collection.children.link(col)
piezas = [
    (veg.build_palmera(col, alto=10.0, seed=1, variante="washingtonia"), -18.0),
    (veg.build_palmera(col, alto=6.0, seed=2, variante="abanico"), -11.0),
    (veg.build_pino(col, alto=12.0, seed=3, variante="joven"), -3.0),
    (veg.build_pino(col, alto=12.0, seed=5, variante="carrasco"), 5.0),
    (veg.build_olivo(col, alto=5.0, seed=2), 12.0),
    (veg.build_arbusto(col, tam=1.8, seed=2, variante="retama"), 17.0),
    (veg.build_adelfa(col, seed=1, variante="blanca"), 21.0),
]
for ob, x in piezas:
    ob.location = (x, 0.0, 0.0)
suelo(300, 300, (0.42, 0.50, 0.24))
luces()
culling_on()
camara((0.0, 30.0, 1.4), (0.0, 0.0, 4.5), lente=24.0)
render("review_veg_pista_culling")

# B) desde arriba/atrás (culling ON) para ver tapas abiertas y ramas
camara((10.0, -22.0, 22.0), (0.0, 0.0, 4.0), lente=28.0)
render("review_veg_arriba_culling")

# C) primer plano washingtonia + palmito + datil, culling ON, contraluz suave
limpiar()
col = bpy.data.collections.new("REV_C")
scene.collection.children.link(col)
for i, (v, a) in enumerate((("datil", 8.0), ("washingtonia", 10.0), ("abanico", 5.0))):
    ob = veg.build_palmera(col, alto=a, seed=4 + i, variante=v)
    ob.location = ((i - 1) * 7.0, 0.0, 0.0)
suelo(300, 300, (0.42, 0.50, 0.24))
luces(sol_dir=(0.3, -0.7, -0.6))
culling_on()
camara((4.0, 22.0, 3.0), (0.0, 0.0, 5.0), lente=35.0)
render("review_veg_palmeras_culling")

# D) ladera en pendiente fuerte (30%) para ver bases de troncos sin enterrar
limpiar()
col = bpy.data.collections.new("REV_D")
scene.collection.children.link(col)
me = bpy.data.meshes.new("rampa")
me.from_pydata([(-60, -40, -12), (60, -40, -12), (60, 40, 12), (-60, 40, 12)], [], [(0, 1, 2, 3)])
me.update()
me.materials.append(mat_plano("MAT_TEST_suelo", (0.42, 0.50, 0.24)))
ramp = bpy.data.objects.new("rampa", me)
scene.collection.objects.link(ramp)
import random as _r
rr = _r.Random(7)
for i in range(24):
    x = rr.uniform(-24, 24)
    y = rr.uniform(-10, 14)
    ob = veg.build_arbol(col, seed=500 + i)
    ob.location = (x, y, y * 0.3 - 0.12)
    ob.rotation_euler = (0, 0, rr.uniform(0, 6.28))
luces()
culling_on()
camara((0.0, -30.0, -6.0), (0.0, 4.0, 4.0), lente=30.0)
render("review_veg_pendiente_culling")

print("== PROBLEMAS ==")
for p in problemas:
    print("  -", p)
print("OK test_review_vegetacion (%d problemas)" % len(problemas))
