"""test_review_coches.py - Revision independiente de coches_kit_v2, ronda 2
(NO modifica el modulo). Angulos extra con backface culling (como AC).
"""

import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ma in list(bpy.data.materials):
    bpy.data.materials.remove(ma)


def carga(nombre):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(BASE, nombre + ".py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = m
    spec.loader.exec_module(m)
    return m


mod = carga("coches_kit_v2")
v1 = carga("coches_kit")

scene = bpy.context.scene
grupos = []


def grupo(nombre):
    c = bpy.data.collections.new(nombre)
    scene.collection.children.link(c)
    grupos.append(c)
    return c


def bbox_local(ob):
    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


COL = dict((n, c) for n, c in mod.COLORES_VIVOS)

# A1 / A2: bocas en los tipos de morro estrecho
gA1 = grupo("REV_A1")
for k, (tipo, c, e, b) in enumerate((("furgoneta", "rojo", "abierto", "rejilla"),
                                     ("pickup", "verde", "feliz", "dientes"),
                                     ("todoterreno", "amarillo", "sorpresa", "abierta"))):
    ob = mod.build_coche(gA1, tipo=tipo, color=COL[c], seed=90 + k, expresion=e, boca=b)
    ob.location = ((k - 1) * 2.7, 1000.0, 0.0)
gA2 = grupo("REV_A2")
for k, (tipo, c, e, b) in enumerate((("ape", "naranja", "sorpresa", "abierta"),
                                     ("deportivo", "morado", "feliz", "rejilla"),
                                     ("topolino", "celeste", "sorpresa", "abierta"))):
    ob = mod.build_coche(gA2, tipo=tipo, color=COL[c], seed=95 + k, expresion=e, boca=b)
    ob.location = ((k - 1) * 2.7, 2000.0, 0.0)

# B: 3/4 lateral a la altura de los ojos
gB = grupo("REV_B")
ob = mod.build_coche(gB, tipo="compacto", color=COL["rojo"], seed=2, expresion="abierto",
                     boca="sonrisa", bitono=False, baca=False, franjas=False)
ob.location = (0.0, 3000.0, 0.0)
ob = mod.build_coche(gB, tipo="sedan", color=COL["turquesa"], seed=6, expresion="feliz",
                     boca="dientes", bitono=True)
ob.location = (-2.7, 3000.0, 0.0)

# C: ojos en rasante
gC = grupo("REV_C")
ob = mod.build_coche(gC, tipo="compacto", color=COL["verde"], seed=2, expresion="feliz",
                     boca="sonrisa", bitono=False, baca=False, franjas=False)
ob.location = (0.0, 4000.0, 0.0)

# D: vista de helicoptero de dos filas
gD = grupo("REV_D")
for k, s in enumerate((1, 4, 5)):
    rf = mod.build_fila_aparcada(gD, n=6, seed=s)
    rf.location = ((k - 1) * 17.0, 5000.0, 0.0)

# E: v1 frente a v2 (misma escala)
gE = grupo("REV_E")
pares = [(v1, "compacto", -4.2), (mod, "compacto", -1.4), (v1, "furgo", 1.4), (mod, "furgo", 4.2)]
for (m_, tipo, x) in pares:
    ob = m_.build_coche(gE, tipo=tipo, color=(0.04, 0.22, 0.72), seed=7)
    ob.location = (x, 6000.0, 0.0)
    x0, x1, y0, y1, z0, z1 = bbox_local(ob)
    print("  %s %-9s ancho %.2f largo %.2f alto %.2f | centro bbox y=%.3f zmin=%.4f"
          % ("v1" if m_ is v1 else "v2", tipo, x1 - x0, y1 - y0, z1, 0.5 * (y0 + y1), z0))

for m in bpy.data.materials:
    if m.name.startswith("MAT_COCHE_"):
        m.use_backface_culling = True

suelo_mat = bpy.data.materials.new("MAT_TEST_suelo")
suelo_mat.use_nodes = True
sb = next(n for n in suelo_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
sb.inputs["Base Color"].default_value = (0.30, 0.30, 0.31, 1.0)
sb.inputs["Roughness"].default_value = 1.0
suelo_me = bpy.data.meshes.new("TEST_suelo")
S = 9000.0
suelo_me.from_pydata([(-S, -S, -0.002), (S, -S, -0.002), (S, S, -0.002), (-S, S, -0.002)],
                     [], [(0, 1, 2, 3)])
suelo_me.update()
suelo_me.materials.append(suelo_mat)
suelo = bpy.data.objects.new("TEST_suelo", suelo_me)
scene.collection.objects.link(suelo)

cam_data = bpy.data.cameras.new("CAM_rev")
cam_data.clip_end = 500.0
cam = bpy.data.objects.new("CAM_rev", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
sun_data = bpy.data.lights.new("SUN_rev", "SUN")
sun_data.energy = 2.6
sun_data.angle = math.radians(3.0)
sun = bpy.data.objects.new("SUN_rev", sun_data)
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("WORLD_rev")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.50, 0.72, 1.0, 1.0)
bg.inputs[1].default_value = 0.8

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
try:
    scene.eevee.taa_render_samples = 16
except AttributeError:
    pass
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"

prev_dir = os.path.join(BASE, "previews")


def toma(nombre, col, cam_loc, target, lens=50.0, luz=(0.30, -0.65, -0.62)):
    for g in grupos:
        g.hide_render = g is not col
    cam_data.type = "PERSP"
    cam_data.lens = lens
    cam.location = Vector(cam_loc)
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sun.rotation_euler = Vector(luz).normalized().to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(prev_dir, nombre)
    bpy.ops.render.render(write_still=True)
    print("PNG:", scene.render.filepath, os.path.exists(scene.render.filepath))


toma("review_coches_v2_bocas_a.png", gA1, (0.8, 1000.0 + 12.5, 1.6), (0.0, 1000.0, 0.85), lens=50.0)
toma("review_coches_v2_bocas_b.png", gA2, (0.8, 2000.0 + 12.0, 1.4), (0.0, 2000.0, 0.70), lens=50.0)
toma("review_coches_v2_lateral34.png", gB, (4.6, 3000.0 + 3.6, 1.15), (-1.0, 3000.0, 0.62), lens=40.0,
     luz=(-0.55, -0.45, -0.70))
toma("review_coches_v2_ojos_rasante.png", gC, (2.3, 4000.0 + 1.1, 1.55), (0.0, 4000.0 + 0.75, 1.15),
     lens=60.0)
toma("review_coches_v2_helicoptero.png", gD, (6.0, 5000.0 + 38.0, 24.0), (0.0, 5000.0, 0.5), lens=45.0)
toma("review_coches_v2_v1_vs_v2.png", gE, (3.0, 6000.0 + 13.0, 3.2), (0.0, 6000.0, 0.8), lens=50.0)
print("OK test_review_coches")
