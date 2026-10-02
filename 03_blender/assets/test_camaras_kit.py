"""test_camaras_kit.py - Test headless del kit de vehiculos-camara de TV.

Ejecutar:
& "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background
  --factory-startup --python
  "E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender/assets/test_camaras_kit.py"

Renderiza (EEVEE 1280x720, sol + cielo suave) en previews/:
  camaras_kit.png          muestrario build(): las 4 piezas, 3/4 frontal
  camaras_furgoneta.png    primer plano frontal-izquierdo de la furgoneta TV
  camaras_grua.png         camion-grua con el brazo completo
  camaras_torre.png        torre de andamio con el mini coche-camara
  camaras_helicoptero.png  helicoptero (posado, para juzgar cara y bola)
  camaras_lejos.png        las 4 piezas vistas a ~55 m a ras de pista
y guarda blend/camaras_kit.blend. Comprueba tris, apoyo en z=0, prefijos,
simetria del origen y que la lente queda hacia +Y, con varias seeds.
"""

import importlib.util
import math
import os
import sys
import time

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(BASE, "camaras_kit.py")
LIMITES = {"furgoneta_tv": 4500, "grua": 5000, "torre": 4500, "helicoptero": 5000}

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ma in list(bpy.data.materials):
    bpy.data.materials.remove(ma)

spec = importlib.util.spec_from_file_location("camaras_kit", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["camaras_kit"] = mod
spec.loader.exec_module(mod)

scene = bpy.context.scene
errores = []


def nueva_col(nombre):
    c = bpy.data.collections.new(nombre)
    scene.collection.children.link(c)
    return c


def mallas_de(ob):
    """La pieza es una malla unica o (helicoptero) un Empty con mallas hijas."""
    return [o for o in [ob] + list(ob.children) if o.type == "MESH"]


def tris_de(ob):
    return sum(len(p.vertices) - 2 for o in mallas_de(ob) for p in o.data.polygons)


def bbox_local(ob, solo_opaco=False):
    vs = []
    for o in mallas_de(ob):
        if solo_opaco and o.name.endswith("_discos"):
            continue
        vs += [v.co for v in o.data.vertices]
    xs, ys, zs = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def centro_lente(ob):
    """Centro de las caras con material de lente (para comprobar que mira a +Y)."""
    c, n, k = Vector((0, 0, 0)), Vector((0, 0, 0)), 0
    for o in mallas_de(ob):
        idx = [i for i, m in enumerate(o.data.materials) if m.name == "MAT_CAMARA_cam_lente"]
        for p in o.data.polygons:
            if p.material_index in idx:
                c += p.center
                n += p.normal
                k += 1
    if k == 0:
        return None, None
    return c / k, n / k


# ---------------------------------------------------------------------------
# 1) QA: cada pieza con varias seeds / parametros
# ---------------------------------------------------------------------------
t0 = time.time()
col_qa = nueva_col("QA_tmp")
casos = []
for seed in range(4):
    casos.append(("furgoneta_tv", lambda s=seed: mod.build_furgoneta_tv(col_qa, seed=s)))
    casos.append(("grua", lambda s=seed: mod.build_grua_camara(col_qa, alto=5.0 + s, seed=s)))
    casos.append(("torre", lambda s=seed: mod.build_torre_camara(col_qa, alto=4.0 + s, seed=s)))
    casos.append(("helicoptero", lambda s=seed: mod.build_helicoptero_camara(col_qa, seed=s)))
casos.append(("furgoneta_tv", lambda: mod.build_furgoneta_tv(col_qa, color=(0.1, 0.5, 0.2), seed=9)))
print("== QA piezas x seeds ==")
peor = {}
for pieza, fn in casos:
    ob = fn()
    t = tris_de(ob)
    x0, x1, y0, y1, z0, z1 = bbox_local(ob)
    peor[pieza] = max(peor.get(pieza, 0), t)
    if t > LIMITES[pieza]:
        errores.append("%s: %d tris > %d" % (ob.name, t, LIMITES[pieza]))
    if abs(z0) > 1e-4:
        errores.append("%s: z min = %.5f" % (ob.name, z0))
    if abs(x0 + x1) > 0.35 and pieza != "helicoptero":
        errores.append("%s: descentrado en X (%.2f..%.2f)" % (ob.name, x0, x1))
    if not ob.name.startswith("CAMARA_"):
        errores.append("nombre %s" % ob.name)
    for o in mallas_de(ob):
        if not o.name.startswith("CAMARA_"):
            errores.append("nombre %s" % o.name)
        for m in o.data.materials:
            if not m.name.startswith("MAT_CAMARA_"):
                errores.append("material %s" % m.name)
    c, n = centro_lente(ob)
    if c is None or n.y <= 0.3:
        errores.append("%s: la lente no mira a +Y (%s)" % (ob.name, n))
    print("  %-24s %5d tris | x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f | lente y=%.2f z=%.2f"
          % (ob.name, t, x0, x1, y0, y1, z0, z1, c.y if c else 0, c.z if c else 0))
print("  peores:", peor, "| QA en %.1f s" % (time.time() - t0))
for ob in list(col_qa.objects):
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)
bpy.data.collections.remove(col_qa)

# ---------------------------------------------------------------------------
# 2) Escenas de preview (separadas 300 m entre si)
# ---------------------------------------------------------------------------
col_kit = nueva_col("PREV_kit")
root = mod.build(col_kit, seed=0)
print("Raiz:", root.name, "| hijos:", len(root.children))
if root.name != "CAMARA_kit" or len(root.children) != 4:
    errores.append("build(): raiz %s con %d hijos" % (root.name, len(root.children)))

col_f = nueva_col("PREV_furgoneta")
f1 = mod.build_furgoneta_tv(col_f, seed=0)
f1.location = (300.0, 0.0, 0.0)
f2 = mod.build_furgoneta_tv(col_f, seed=1)
f2.location = (308.2, -2.2, 0.0)
f2.rotation_euler = (0.0, 0.0, math.radians(-6.0))
f3 = mod.build_furgoneta_tv(col_f, seed=2)
f3.location = (296.4, -8.2, 0.0)
f3.rotation_euler = (0.0, 0.0, math.radians(10.0))

col_g = nueva_col("PREV_grua")
g1 = mod.build_grua_camara(col_g, alto=7.0, seed=0)
g1.location = (600.0, 0.0, 0.0)

col_t = nueva_col("PREV_torre")
t1 = mod.build_torre_camara(col_t, alto=6.0, seed=0)
t1.location = (900.0, 0.0, 0.0)

col_h = nueva_col("PREV_heli")
h1 = mod.build_helicoptero_camara(col_h, seed=0)
h1.location = (1200.0, 0.0, 0.0)
h2 = mod.build_helicoptero_camara(col_h, seed=1)          # en vuelo, visto desde la pista
h2.location = (1260.0, 0.0, 14.0)
h2.rotation_euler = (math.radians(6.0), 0.0, math.radians(12.0))

# suelo + banda de 'pista' delante (+Y) para orientarse
def plano(nombre, x0, x1, y0, y1, z, rgb):
    ma = bpy.data.materials.new("MAT_TEST_" + nombre)
    ma.use_nodes = True
    sb = next(n for n in ma.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    sb.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    sb.inputs["Roughness"].default_value = 1.0
    me = bpy.data.meshes.new("TEST_" + nombre)
    me.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [], [(0, 1, 2, 3)])
    me.update()
    me.materials.append(ma)
    ob = bpy.data.objects.new("TEST_" + nombre, me)
    scene.collection.objects.link(ob)
    return ob


plano("suelo", -200.0, 1500.0, -300.0, 300.0, -0.004, (0.50, 0.47, 0.42))
plano("pista", -200.0, 1500.0, 9.0, 21.0, -0.002, (0.13, 0.13, 0.14))
plano("piano", -200.0, 1500.0, 8.4, 9.0, -0.001, (0.80, 0.08, 0.06))

cam_data = bpy.data.cameras.new("CAM_camaras")
cam = bpy.data.objects.new("CAM_camaras", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
sun_data = bpy.data.lights.new("SUN_camaras", "SUN")
sun_data.energy = 3.2
sun_data.angle = math.radians(3.0)
sun = bpy.data.objects.new("SUN_camaras", sun_data)
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("WORLD_camaras")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.50, 0.72, 1.0, 1.0)
bg.inputs[1].default_value = 0.9

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
print("Engine:", scene.render.engine)
try:
    scene.eevee.taa_render_samples = 24
except AttributeError:
    pass
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"

prev_dir = os.path.join(BASE, "previews")
os.makedirs(prev_dir, exist_ok=True)
grupos = [col_kit, col_f, col_g, col_t, col_h]
pngs = []


def toma(nombre, col, cam_loc, target, lens=40.0, luz=(0.40, -0.55, -0.72)):
    for g in grupos:
        g.hide_render = g is not col
    cam_data.type = "PERSP"
    cam_data.lens = lens
    cam_data.clip_end = 2000.0
    cam.location = Vector(cam_loc)
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sun.rotation_euler = Vector(luz).normalized().to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(prev_dir, nombre)
    bpy.ops.render.render(write_still=True)
    ok = os.path.exists(scene.render.filepath)
    pngs.append((nombre, ok))
    print("PNG:", scene.render.filepath, ok)


# frontal-izquierdo = camara en (-X, +Y) respecto a la pieza
toma("camaras_kit.png", col_kit, (-17.0, 33.0, 10.0), (0.5, 0.0, 3.6), lens=40.0)
toma("camaras_furgoneta.png", col_f, (300.0 - 5.2, 8.6, 3.0), (300.3, -0.6, 1.75), lens=38.0)
toma("camaras_grua.png", col_g, (600.0 - 11.5, 15.0, 4.6), (600.0, 1.4, 4.3), lens=34.0)
toma("camaras_torre.png", col_t, (900.0 - 9.5, 16.0, 5.4), (900.0, -0.2, 4.2), lens=34.0)
toma("camaras_torre_detalle.png", col_t, (900.0 - 4.2, 7.6, 7.4), (900.0, 0.5, 7.0), lens=40.0)
toma("camaras_helicoptero.png", col_h, (1200.0 - 7.2, 10.5, 3.3), (1200.0, -1.6, 1.75), lens=34.0)
toma("camaras_helicoptero_vuelo.png", col_h, (1260.0 - 7.0, 24.0, 1.2), (1260.0, -0.5, 15.2),
     lens=60.0)
# a distancia de carrera: ~55 m, ojo de piloto a 1.1 m
toma("camaras_lejos.png", col_kit, (-2.0, 58.0, 1.1), (0.0, 0.0, 4.2), lens=50.0)

for g in grupos:
    g.hide_render = False
blend_dir = os.path.join(BASE, "blend")
os.makedirs(blend_dir, exist_ok=True)
blend_path = os.path.join(blend_dir, "camaras_kit.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("BLEND:", blend_path)

for nombre, ok in pngs:
    if not ok:
        errores.append("no se genero %s" % nombre)
if errores:
    print("ERRORES (%d):" % len(errores))
    for e in errores:
        print("  -", e)
    print("FALLO test_camaras_kit")
else:
    print("OK test_camaras_kit")
