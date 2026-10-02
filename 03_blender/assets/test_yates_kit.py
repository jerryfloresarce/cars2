"""test_yates_kit.py - Test headless del kit de yates VIP (Porto Corsa).

Ejecutar:
& "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background
  --factory-startup --python
  "E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender/assets/test_yates_kit.py"

Renderiza (EEVEE 1280x800, sol calido + cielo azul, Standard) en previews/:
  yates_kit.png          escaparate completo visto desde la 'pista' (+Y)
  yates_yate.png         un yate de cerca con el publico (desde estribor/proa)
  yates_yate_popa.png    el mismo yate desde la aleta de babor (popa, bandera)
  yates_super.png        el superyate (helipuerto, piscina, 3 pisos)
  yates_super_popa.png   el superyate desde la aleta de babor (piscina, popa)
  yates_lancha.png       la lancha de cerca desde la amura de estribor
  yates_lancha_popa.png  la lancha desde la aleta (cockpit: consola, volante)
  yates_pantalan.png     portal 'VIP' del pantalan visto desde tierra (x<0)
  yates_coches_lujo.png  limusina, deportivo, cabrio y mayordomo de cerca
y guarda blend/yates_kit.blend. Comprueba presupuestos de tris (yate <= 9k,
superyate <= 16k, lancha <= 2k, coche de lujo <= 1.5k, sin contar coches),
que ningun vertice baja de z=-2.6 (todo flota), nombres de raices/hijos,
materiales MAT_YATE_*/MAT_COCHE_*, coches apoyados en z=0 y que los coches
de cubierta caben dentro del casco (bbox en y).
"""

import importlib.util
import math
import os
import sys
import time

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(BASE, "yates_kit.py")

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ma in list(bpy.data.materials):
    bpy.data.materials.remove(ma)

spec = importlib.util.spec_from_file_location("yates_kit", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["yates_kit"] = mod
spec.loader.exec_module(mod)

scene = bpy.context.scene
errores = []


def nueva_col(nombre):
    c = bpy.data.collections.new(nombre)
    scene.collection.children.link(c)
    return c


def tris_de(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons) if ob.type == "MESH" else 0


def descendientes(root):
    out = []
    pila = list(root.children)
    while pila:
        o = pila.pop()
        out.append(o)
        pila.extend(o.children)
    return out


def bbox_mundo(ob):
    bpy.context.view_layer.update()
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts),
            max(p.y for p in pts), min(p.z for p in pts), max(p.z for p in pts))


def comprobar_barco(root, nombre, limite, z_min=-2.6):
    """Tris sin coches, flotacion, nombres y materiales."""
    hijos = descendientes(root)
    piezas = [h for h in hijos if h.type == "MESH" and not h.name.startswith("COCHE_")]
    coches = [h for h in hijos if h.name.startswith("COCHE_")]
    t = sum(tris_de(h) for h in piezas)
    print("  %-16s %6d tris sin coches (%d piezas) + %d coches (%d tris) | %s"
          % (nombre, t, len(piezas), len(coches), sum(tris_de(c) for c in coches),
             ", ".join(h.name.split(".")[0] for h in piezas)))
    if root.name.split(".")[0] != nombre:
        errores.append("raiz %s != %s" % (root.name, nombre))
    if t > limite:
        errores.append("%s: %d tris > %d" % (nombre, t, limite))
    for h in hijos:
        if h.type != "MESH":
            continue
        z0 = bbox_mundo(h)[4] - root.matrix_world.translation.z
        if z0 < z_min - 1e-4:
            errores.append("%s/%s baja a z=%.2f" % (nombre, h.name, z0))
        for m in h.data.materials:
            if not (m.name.startswith("MAT_YATE_") or m.name.startswith("MAT_COCHE_")):
                errores.append("%s: material %s" % (h.name, m.name))
    cascos = [h for h in piezas if "casco" in h.name]
    if cascos:
        cx0, cx1, cy0, cy1, _cz0, cz1 = bbox_mundo(cascos[0])
    for c in coches:
        if c.location.z < -1e-4:
            errores.append("%s: coche %s bajo cubierta z=%.2f" % (nombre, c.name, c.location.z))
        if not c.name.startswith("COCHE_"):
            errores.append("coche mal nombrado %s" % c.name)
        if cascos:
            bx0, bx1, by0, by1, bz0, _bz1 = bbox_mundo(c)
            if bx0 < cx0 - 0.05 or bx1 > cx1 + 0.05 or by0 < cy0 - 0.05 or by1 > cy1 + 0.05:
                errores.append("%s: coche %s fuera del casco (x %.1f..%.1f y %.1f..%.1f)"
                               % (nombre, c.name, bx0, bx1, by0, by1))
    return t, len(coches)


# ---------------------------------------------------------------------------
# 1) QA por piezas y seeds
# ---------------------------------------------------------------------------
t0 = time.time()
col_qa = nueva_col("QA_tmp")
print("== QA yates ==")
n_pub = []
for s in range(3):
    r = mod.build_yate(col_qa, eslora=32.0, seed=s)
    t, n = comprobar_barco(r, "YATE_root", 9000)
    n_pub.append(n)
    casco = next(h for h in r.children if h.name.startswith("YATE_casco"))
    zmin = min(v.co.z for v in casco.data.vertices)
    if zmin < -2.6:
        errores.append("casco seed %d: z min %.2f" % (s, zmin))
    print("     casco z min %.2f | publico %d coches (con mayordomo)" % (zmin, n))
    if not (5 <= n <= 9):
        errores.append("yate seed %d: %d coches (esperado 4-8 + mayordomo)" % (s, n))
r = mod.build_yate(col_qa, eslora=26.0, seed=7, con_publico=False, n_coches=4, pasarela=False)
comprobar_barco(r, "YATE_root", 9000)
if any(h.name.startswith("COCHE_") for h in r.children):
    errores.append("con_publico=False aun crea coches")
for s in range(2):
    r = mod.build_superyate(col_qa, eslora=70.0, seed=s)
    t, n = comprobar_barco(r, "YATE_super", 16000)
    if not (10 <= n <= 13):
        errores.append("superyate seed %d: %d coches" % (s, n))
    if not any(h.name.startswith("YATE_super_helicoptero") for h in r.children):
        errores.append("superyate sin helicoptero")
for s in range(3):
    r = mod.build_lancha(col_qa, eslora=9.0, seed=s)
    t, n = comprobar_barco(r, "YATE_lancha", 2000)
    if not (1 <= n <= 2):
        errores.append("lancha seed %d: %d coches" % (s, n))
r = mod.build_pantalan_vip(col_qa, largo=60.0, seed=0)
comprobar_barco(r, "YATE_pantalan", 12000, z_min=-2.6)
x0, x1, y0, y1, z0, z1 = bbox_mundo(next(h for h in r.children if h.name.startswith("YATE_pantalan_cuerpo")))
print("  pantalan bbox x %.1f..%.1f y %.1f..%.1f z %.2f..%.2f" % (x0, x1, y0, y1, z0, z1))
if abs(x0) > 0.05 or abs(x1 - 60.0) > 0.05 or abs(z1 - 0.924) > 0.02:
    errores.append("pantalan: bbox x %.2f..%.2f z top %.3f" % (x0, x1, z1))
print("== QA coches de lujo ==")
for tipo in mod.TIPOS_LUJO:
    for s in range(3):
        ob = mod.build_coche_lujo(col_qa, tipo=tipo, seed=s)
        t = tris_de(ob)
        xs = [v.co.x for v in ob.data.vertices]
        ys = [v.co.y for v in ob.data.vertices]
        zs = [v.co.z for v in ob.data.vertices]
        if s == 0:
            print("  %-10s %5d tris | ancho %.2f largo %.2f alto %.2f | %d slots"
                  % (tipo, t, max(xs) - min(xs), max(ys) - min(ys), max(zs), len(ob.data.materials)))
        limite = 3500 if tipo == "deportivo" else 1500      # deportivo = coches_kit_v2
        if t > limite:
            errores.append("%s seed %d: %d tris > %d" % (tipo, s, t, limite))
        if abs(min(zs)) > 1e-4:
            errores.append("%s seed %d: z min %.4f" % (tipo, s, min(zs)))
        if abs(min(xs) + max(xs)) > 0.02 or abs(min(ys) + max(ys)) > 0.02:
            errores.append("%s seed %d: origen descentrado" % (tipo, s))
        if ob.name.split(".")[0] != "COCHE_lujo_%s" % tipo:
            errores.append("nombre %s" % ob.name)
try:
    mod.build_coche_lujo(col_qa, tipo="tractor")
    errores.append("tipo invalido no lanza ValueError")
except ValueError:
    pass
print("  QA en %.1f s" % (time.time() - t0))
for ob in list(col_qa.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
bpy.data.collections.remove(col_qa)

# ---------------------------------------------------------------------------
# 2) Escenas de preview
# ---------------------------------------------------------------------------
col_a = nueva_col("PREV_escaparate")
esc = mod.build(col_a, seed=0)
print("Escaparate:", esc.name, "| hijos directos:", len(esc.children))
if esc.name != "YATE_escaparate":
    errores.append("build() raiz %s" % esc.name)
col_b = nueva_col("PREV_yate")
yate = mod.build_yate(col_b, eslora=32.0, seed=3)
mod.build_agua(col_b, nombre="TEST_agua_b")
col_c = nueva_col("PREV_super")
sup = mod.build_superyate(col_c, eslora=70.0, seed=1)
mod.build_agua(col_c, nombre="TEST_agua_c")
col_d = nueva_col("PREV_lujo")
for i, (tipo, x) in enumerate((("limusina", -5.5), ("deportivo", 0.0), ("cabrio", 4.0))):
    ob = mod.build_coche_lujo(col_d, tipo=tipo, seed=i + 2)
    ob.location = (x, 0.0, 0.0)
    ob.rotation_euler = (0.0, 0.0, math.radians((-6.0, 4.0, -3.0)[i]))
raiz_d = bpy.data.objects.new("TEST_raiz_lujo", None)
col_d.objects.link(raiz_d)
mb_d = mod._MB()
mod._mayordomo(col_d, raiz_d, mb_d, (7.4, -1.6, 0.0), 9, mod.random.Random(3), giro=math.radians(-25.0))
mb_d.build("TEST_bandeja", col_d)
col_e = nueva_col("PREV_lancha")
lancha = mod.build_lancha(col_e, eslora=9.0, seed=1)
mod.build_agua(col_e, nombre="TEST_agua_e")
suelo_mat = bpy.data.materials.new("MAT_TEST_suelo")
if getattr(suelo_mat, "node_tree", None) is None:     # Blender 5.1: use_nodes deprecado
    suelo_mat.use_nodes = True
sb = next(n for n in suelo_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
sb.inputs["Base Color"].default_value = (0.36, 0.34, 0.32, 1.0)
sb.inputs["Roughness"].default_value = 1.0
suelo_me = bpy.data.meshes.new("TEST_suelo")
S = 200.0
suelo_me.from_pydata([(-S, -S, -0.002), (S, -S, -0.002), (S, S, -0.002), (-S, S, -0.002)], [], [(0, 1, 2, 3)])
suelo_me.update()
suelo_me.materials.append(suelo_mat)
suelo = bpy.data.objects.new("TEST_suelo", suelo_me)
col_d.objects.link(suelo)

# camara, sol calido, cielo azul
cam_data = bpy.data.cameras.new("CAM_yates")
cam_data.clip_end = 2000.0
cam = bpy.data.objects.new("CAM_yates", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
sun_data = bpy.data.lights.new("SUN_yates", "SUN")
sun_data.energy = 4.0
sun_data.color = (1.0, 0.94, 0.84)
for attr, val in (("angle", math.radians(1.5)), ("use_shadow", True)):
    try:
        setattr(sun_data, attr, val)
    except (AttributeError, TypeError):
        pass
sun = bpy.data.objects.new("SUN_yates", sun_data)
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("WORLD_yates")
scene.world = world
nt_w = getattr(world, "node_tree", None)
if nt_w is None:
    world.use_nodes = True
    nt_w = world.node_tree
salida = next((n for n in nt_w.nodes if n.type == "OUTPUT_WORLD"), None) or nt_w.nodes.new("ShaderNodeOutputWorld")
amb = nt_w.nodes.new("ShaderNodeBackground")
amb.inputs[0].default_value = (0.70, 0.80, 0.95, 1.0)
amb.inputs[1].default_value = 0.6
cielo = nt_w.nodes.new("ShaderNodeBackground")
cielo.inputs[0].default_value = (0.38, 0.62, 0.96, 1.0)
cielo.inputs[1].default_value = 1.0
ruta = nt_w.nodes.new("ShaderNodeLightPath")
mezcla = nt_w.nodes.new("ShaderNodeMixShader")
nt_w.links.new(ruta.outputs["Is Camera Ray"], mezcla.inputs[0])
nt_w.links.new(amb.outputs[0], mezcla.inputs[1])
nt_w.links.new(cielo.outputs[0], mezcla.inputs[2])
nt_w.links.new(mezcla.outputs[0], salida.inputs["Surface"])

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
print("Engine:", scene.render.engine)
for attr, val in (("use_raytracing", True), ("use_shadows", True), ("taa_render_samples", 40),
                  ("shadow_ray_count", 2), ("shadow_step_count", 4)):
    try:
        setattr(scene.eevee, attr, val)
    except (AttributeError, TypeError):
        pass
scene.render.resolution_x = 1280
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"

prev_dir = os.path.join(BASE, "previews")
os.makedirs(prev_dir, exist_ok=True)
grupos = [col_a, col_b, col_c, col_d, col_e]


def toma(nombre, col, cam_loc, target, lens=40.0, luz=(0.45, -0.55, -0.72)):
    for g in grupos:
        g.hide_render = g is not col
    cam_data.lens = lens
    cam.location = Vector(cam_loc)
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sun.rotation_euler = Vector(luz).normalized().to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(prev_dir, nombre)
    bpy.ops.render.render(write_still=True)
    print("PNG:", scene.render.filepath, os.path.exists(scene.render.filepath))


toma("yates_kit.png", col_a, (50.0, 64.0, 17.0), (72.0, -7.0, 3.0), lens=30.0, luz=(0.35, 0.55, -0.72))
toma("yates_yate.png", col_b, (19.0, 25.0, 8.5), (-1.5, 0.0, 2.6), lens=40.0, luz=(0.35, 0.55, -0.72))
toma("yates_yate_popa.png", col_b, (-26.0, -15.0, 7.5), (-5.0, 0.5, 2.2), lens=40.0, luz=(-0.35, -0.55, -0.72))
toma("yates_super.png", col_c, (50.0, 56.0, 27.0), (0.0, -1.0, 4.0), lens=35.0, luz=(0.35, 0.55, -0.72))
toma("yates_super_popa.png", col_c, (-64.0, -34.0, 22.0), (-14.0, 0.0, 5.0), lens=40.0, luz=(-0.35, -0.55, -0.72))
toma("yates_lancha.png", col_e, (8.5, 9.0, 3.6), (0.3, 0.0, 0.6), lens=42.0, luz=(-0.45, -0.50, -0.72))
toma("yates_lancha_popa.png", col_e, (-7.5, 7.5, 3.4), (0.6, 0.0, 0.6), lens=42.0, luz=(0.45, -0.50, -0.72))
toma("yates_pantalan.png", col_a, (-8.5, 7.0, 3.4), (3.5, -0.5, 2.3), lens=32.0, luz=(0.55, -0.45, -0.70))
toma("yates_coches_lujo.png", col_d, (2.5, 15.0, 4.0), (0.8, 0.0, 0.8), lens=32.0, luz=(0.30, 0.60, -0.70))

for g in grupos:
    g.hide_render = False
blend_dir = os.path.join(BASE, "blend")
os.makedirs(blend_dir, exist_ok=True)
blend_path = os.path.join(blend_dir, "yates_kit.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("BLEND:", blend_path)

if errores:
    print("ERRORES (%d):" % len(errores))
    for e in errores:
        print("  -", e)
    print("FALLO test_yates_kit")
else:
    print("OK test_yates_kit")
