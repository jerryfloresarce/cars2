"""test_coches_kit_v2.py - Test headless del kit de coches-espectador v2.

Ejecutar:
& "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background
  --factory-startup --python
  "E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender/assets/test_coches_kit_v2.py"

Renderiza (EEVEE 1280x720) en previews/:
  coches_v2_tipos_frente.png  los 9 tipos, vista 3/4 frontal
  coches_v2_tipos_lado.png    los 9 tipos, vista lateral pura (ortografica)
  coches_v2_fila.png          build_fila_aparcada(n=6) como la usa el integrador
  coches_v2_detalle.png       primer plano de un coche
  coches_v2_tipos_tras.png    los 9 tipos por detras (pilotos, matricula)
  coches_v2_frente_bajo.png   frontal bajo: pasos de rueda y parpados 'feliz'
y guarda blend/coches_kit_v2.blend. Comprueba tris <= 3500, <= 10 slots de
material por coche, apoyo en z=0 y origen centrado para todos los tipos (y
alias antiguos) con varias seeds, con y sin todas las opciones forzadas.
"""

import importlib.util
import math
import os
import sys
import time

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(BASE, "coches_kit_v2.py")
LIMITE_TRIS = 3500

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ma in list(bpy.data.materials):
    bpy.data.materials.remove(ma)

spec = importlib.util.spec_from_file_location("coches_kit_v2", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["coches_kit_v2"] = mod
spec.loader.exec_module(mod)

scene = bpy.context.scene


def nueva_col(nombre):
    c = bpy.data.collections.new(nombre)
    scene.collection.children.link(c)
    return c


def tris_de(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bbox_local(ob):
    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


# ---------------------------------------------------------------------------
# 1) QA: todos los tipos (nuevos + alias v1) x varias seeds
# ---------------------------------------------------------------------------
errores = []
t0 = time.time()
col_qa = nueva_col("QA_tmp")
LIMITE_SLOTS = 10
print("== QA tipos x seeds (limite %d tris, %d slots de material) =="
      % (LIMITE_TRIS, LIMITE_SLOTS))
for tipo in list(mod.TIPOS) + ["furgo"]:
    peor, dims, peor_slots, suma, cuenta = 0, None, 0, 0, 0
    for seed in range(6):
        for forzado in (False, True):
            kw = (dict(baca=True, bitono=True, franjas=True, carga=True,
                       boca="abierta") if forzado else {})
            ob = mod.build_coche(col_qa, tipo=tipo, seed=seed, **kw)
            t = tris_de(ob)
            x0, x1, y0, y1, z0, z1 = bbox_local(ob)
            peor = max(peor, t)
            if not forzado:             # media de los coches 'por seed'
                suma += t
                cuenta += 1
            peor_slots = max(peor_slots, len(ob.data.materials))
            if not forzado:
                dims = (x1 - x0, y1 - y0, z1)
            if t > LIMITE_TRIS:
                errores.append("%s seed %d: %d tris" % (tipo, seed, t))
            if len(ob.data.materials) > LIMITE_SLOTS:
                errores.append("%s seed %d: %d slots de material"
                               % (tipo, seed, len(ob.data.materials)))
            if abs(z0) > 1e-5:
                errores.append("%s seed %d: z min = %.5f" % (tipo, seed, z0))
            if abs(x0 + x1) > 1e-4 or abs(y0 + y1) > 1e-4:
                errores.append("%s seed %d: origen descentrado" % (tipo, seed))
            if tuple(ob.location) != (0.0, 0.0, 0.0):
                errores.append("%s seed %d: location != 0" % (tipo, seed))
            if ob.name.split(".")[0] != "COCHE_%s" % tipo:
                errores.append("nombre %s" % ob.name)
            for m in ob.data.materials:
                if not m.name.startswith("MAT_COCHE_"):
                    errores.append("material %s" % m.name)
    print("  %-12s max %4d tris (media %4d) | max %2d slots | ancho %.2f largo %.2f alto %.2f"
          % (tipo, peor, suma // cuenta, peor_slots, dims[0], dims[1], dims[2]))
# expresiones antiguas y nuevas, bocas, llamada posicional estilo v1
for e in mod.EXPRESIONES_ACEPTADAS:
    mod.build_coche(col_qa, tipo="compacto", seed=3, expresion=e)
for b in mod.BOCAS:
    mod.build_coche(col_qa, tipo="sedan", seed=4, boca=b)
mod.build_coche(col_qa, "deportivo", (0.9, 0.1, 0.1), 8, "guino")
for malo in (dict(tipo="tractor"), dict(expresion="triste"), dict(boca="pico")):
    try:
        mod.build_coche(col_qa, **malo)
        errores.append("no lanza ValueError con %s" % malo)
    except ValueError:
        pass
try:
    mod.build_coche(col_qa, tipo="sedan", bacca=True)
    errores.append("una opcion desconocida (bacca) no lanza TypeError")
except TypeError:
    pass
# filas como las pide el integrador: recuento de materiales en escena
for s in (1, 2, 3, 4, 5):
    fila = mod.build_fila_aparcada(col_qa, n=6, seed=s)
    if fila.name.split(".")[0] != "COCHE_fila" or len(fila.children) != 6:
        errores.append("fila seed %d: raiz %s con %d hijos"
                       % (s, fila.name, len(fila.children)))
    bpy.context.view_layer.update()
    for h in fila.children:
        bb = [h.matrix_world @ Vector(c) for c in h.bound_box]
        if abs(min(p.z for p in bb)) > 1e-4:
            errores.append("fila seed %d: %s no apoya en z=0" % (s, h.name))
mats_coche = sorted(m.name for m in bpy.data.materials if m.name.startswith("MAT_COCHE_"))
n_cuerpo = sum(1 for n in mats_coche if n.startswith("MAT_COCHE_cuerpo_"))
print("  materiales MAT_COCHE_* en escena: %d (%d de carroceria + %d fijos)"
      % (len(mats_coche), n_cuerpo, len(mats_coche) - n_cuerpo))
print("   fijos:", ", ".join(n[10:] for n in mats_coche if not n.startswith("MAT_COCHE_cuerpo_")))
print("  QA en %.1f s" % (time.time() - t0))
for ob in list(col_qa.objects):
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)
bpy.data.collections.remove(col_qa)

# ---------------------------------------------------------------------------
# 2) Escenas de preview
# ---------------------------------------------------------------------------
COL = dict((n, c) for n, c in mod.COLORES_VIVOS)

# --- A: los 9 tipos en dos filas, 3/4 frontal
col_a = nueva_col("PREV_tipos_frente")
fila_del = [("topolino", "amarillo", "feliz", "abierta"),
            ("ape", "celeste", "abierto", "sonrisa"),
            ("deportivo", "rojo", "abierto", "dientes"),
            ("compacto", "azul", "feliz", "sonrisa")]
fila_tras = [("sedan", "morado", "abierto", "rejilla"),
             ("familiar", "verde", "feliz", "dientes"),
             ("furgoneta", "turquesa", "feliz", "abierta"),
             ("pickup", "naranja", "sorpresa", "abierta"),
             ("todoterreno", "crema", "abierto", "rejilla")]
PASO = 2.75
for i, (tipo, c, e, b) in enumerate(fila_del):
    ob = mod.build_coche(col_a, tipo=tipo, color=COL[c], seed=10 + i, expresion=e, boca=b)
    ob.location = ((i - 1.5) * PASO, 2.6, 0.0)
for i, (tipo, c, e, b) in enumerate(fila_tras):
    ob = mod.build_coche(col_a, tipo=tipo, color=COL[c], seed=20 + i, expresion=e, boca=b)
    ob.location = ((i - 2.0) * PASO, -3.2, 0.0)

# --- B: los 9 tipos en rejilla 3x3 sobre baldas, vista lateral pura
col_b = nueva_col("PREV_tipos_lado")
orden = ["topolino", "ape", "compacto", "deportivo", "sedan", "familiar",
         "furgoneta", "pickup", "todoterreno"]
colores_b = ["amarillo", "celeste", "azul", "rojo", "morado", "verde",
             "turquesa", "naranja", "crema"]
ALTO_B, PASO_B = 2.75, 5.6
m_balda = bpy.data.materials.new("MAT_TEST_balda")
m_balda.diffuse_color = (0.75, 0.72, 0.66, 1.0)
for k, tipo in enumerate(orden):
    fila, colu = 2 - k // 3, k % 3
    ob = mod.build_coche(col_b, tipo=tipo, color=COL[colores_b[k]], seed=30 + k,
                         baca=(tipo in ("familiar", "todoterreno")))
    ob.location = (0.0, (colu - 1) * PASO_B, fila * ALTO_B)
for fila in range(3):
    z = fila * ALTO_B
    me = bpy.data.meshes.new("TEST_balda")
    X, Y = 1.25, 8.7
    me.from_pydata([(-X, -Y, z - 0.06), (X, -Y, z - 0.06), (X, Y, z - 0.06), (-X, Y, z - 0.06),
                    (-X, -Y, z), (X, -Y, z), (X, Y, z), (-X, Y, z)], [],
                   [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)])
    me.materials.append(m_balda)
    me.update()
    bo = bpy.data.objects.new("TEST_balda", me)
    bo.location = (-400.0, 0.0, 0.0)
    col_b.objects.link(bo)
for ob in col_b.objects:
    if not ob.name.startswith("TEST_balda"):
        ob.location.x -= 400.0

# --- C: la fila aparcada tal y como la usa el integrador
col_c = nueva_col("PREV_fila")
root = mod.build(col_c, seed=1)
root.location = (0.0, -400.0, 0.0)
print("Raiz:", root.name, "| hijos:", len(root.children))
if root.name != "COCHE_fila":
    errores.append("la raiz no se llama COCHE_fila: %s" % root.name)
for h in root.children:
    t = tris_de(h)
    print("  %-22s %5d tris  x=%.2f" % (h.name, t, h.location.x))
    if t > LIMITE_TRIS:
        errores.append("%s: %d tris" % (h.name, t))

# --- D: primer plano
col_d = nueva_col("PREV_detalle")
hero = mod.build_coche(col_d, tipo="topolino", color=COL["amarillo"], seed=10,
                       expresion="feliz", boca="abierta", bitono=False, baca=True)
hero.location = (400.0, 0.0, 0.0)
hero.rotation_euler = (0.0, 0.0, math.radians(8.0))
h2 = mod.build_coche(col_d, tipo="compacto", color=COL["azul"], seed=13,
                     expresion="abierto", boca="dientes")
h2.location = (402.7, -1.9, 0.0)
h2.rotation_euler = (0.0, 0.0, math.radians(-4.0))

# --- E: frontal bajo (pasos de rueda que siguen el morro + parpados 'feliz')
col_e = nueva_col("PREV_frente_bajo")
for i, (tipo, c, e, b) in enumerate([("topolino", "amarillo", "feliz", "abierta"),
                                     ("deportivo", "rojo", "abierto", "dientes"),
                                     ("furgoneta", "rosa", "feliz", "sonrisa"),
                                     ("todoterreno", "morado", "feliz", "rejilla")]):
    ob = mod.build_coche(col_e, tipo=tipo, color=COL[c], seed=50 + i, expresion=e, boca=b)
    ob.location = ((1.5 - i) * 2.3, 400.0, 0.0)

# Render a UNA cara, como el motor de Assetto Corsa: cualquier cara invertida
# o lamina vista por detras apareceria como un agujero en las previews.
for m in bpy.data.materials:
    if m.name.startswith("MAT_COCHE_"):
        m.use_backface_culling = True

# suelo
suelo_mat = bpy.data.materials.new("MAT_TEST_suelo")
suelo_mat.use_nodes = True
sb = next(n for n in suelo_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
sb.inputs["Base Color"].default_value = (0.42, 0.40, 0.37, 1.0)
sb.inputs["Roughness"].default_value = 1.0
suelo_me = bpy.data.meshes.new("TEST_suelo")
S = 900.0
suelo_me.from_pydata([(-S, -S, -0.002), (S, -S, -0.002), (S, S, -0.002), (-S, S, -0.002)],
                     [], [(0, 1, 2, 3)])
suelo_me.update()
suelo_me.materials.append(suelo_mat)
suelo = bpy.data.objects.new("TEST_suelo", suelo_me)
scene.collection.objects.link(suelo)

# camara, sol, cielo
cam_data = bpy.data.cameras.new("CAM_coches")
cam = bpy.data.objects.new("CAM_coches", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
sun_data = bpy.data.lights.new("SUN_coches", "SUN")
sun_data.energy = 3.2
sun_data.angle = math.radians(3.0)
sun = bpy.data.objects.new("SUN_coches", sun_data)
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("WORLD_coches")
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
grupos = [col_a, col_b, col_c, col_d, col_e]


def toma(nombre, col, cam_loc, target, lens=50.0, ortho=None, luz=(-0.35, -0.60, -0.72),
         con_suelo=True):
    for g in grupos:
        g.hide_render = g is not col
    suelo.hide_render = not con_suelo
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    else:
        cam_data.type = "PERSP"
        cam_data.lens = lens
    cam.location = Vector(cam_loc)
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sun.rotation_euler = Vector(luz).normalized().to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(prev_dir, nombre)
    bpy.ops.render.render(write_still=True)
    print("PNG:", scene.render.filepath, os.path.exists(scene.render.filepath))


toma("coches_v2_tipos_frente.png", col_a, (5.4, 17.0, 6.2), (0.0, -0.5, 0.45), lens=47.0)
toma("coches_v2_tipos_tras.png", col_a, (-4.2, -20.0, 7.0), (0.35, -0.6, 0.45), lens=45.0,
     luz=(0.35, 0.60, -0.72))
toma("coches_v2_frente_bajo.png", col_e, (0.0, 412.4, 0.95), (0.0, 400.0, 0.85), lens=42.0,
     luz=(0.30, -0.65, -0.62))
toma("coches_v2_tipos_lado.png", col_b, (-360.0, 0.0, 3.55), (-400.0, 0.0, 3.55),
     ortho=17.6, luz=(-0.70, -0.30, -0.62), con_suelo=False)
toma("coches_v2_fila.png", col_c, (5.5, -383.6, 4.4), (1.0, -400.0, 0.35), lens=38.0)
toma("coches_v2_detalle.png", col_d, (398.5, 5.7, 1.35), (400.85, -0.2, 0.68), lens=50.0,
     luz=(0.30, -0.65, -0.62))
toma("coches_v2_paso_rueda.png", col_d, (401.9, 3.3, 0.42), (400.45, 0.95, 0.36), lens=50.0,
     luz=(0.45, -0.60, -0.62))

for g in grupos:
    g.hide_render = False
suelo.hide_render = False
blend_dir = os.path.join(BASE, "blend")
os.makedirs(blend_dir, exist_ok=True)
blend_path = os.path.join(blend_dir, "coches_kit_v2.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("BLEND:", blend_path)

if errores:
    print("ERRORES (%d):" % len(errores))
    for e in errores:
        print("  -", e)
    print("FALLO test_coches_kit_v2")
else:
    print("OK test_coches_kit_v2")
