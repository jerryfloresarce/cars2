"""test_penon_pueblo.py - construye dos rocas-pueblo (elipse grande y lazo
pequeno), comprueba que la roca es cerrada (rayos desde arriba la atraviesan
dos veces), que los solares quedan sobre la repisa y no sobre la carretera, y
renderiza previews/penon_pueblo*.png.

  blender --background --factory-startup --python test_penon_pueblo.py
"""
import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('penon_pueblo', os.path.join(AQUI, 'penon_pueblo.py'))
pp = importlib.util.module_from_spec(spec)
sys.modules['penon_pueblo'] = pp
spec.loader.exec_module(pp)

sc = bpy.context.scene
for ob in list(sc.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
col = bpy.data.collections.new('PP')
sc.collection.children.link(col)

# --- 1) elipse 118x78 como la del casino
pts_e = [(118 * math.cos(2 * math.pi * k / 96), 78 * math.sin(2 * math.pi * k / 96)) for k in range(96)]
raiz_e, info_e = pp.build_desde_contorno(col, pts_e, altura=125.0, z_base=-5.0, n_terrazas=4, seed=2,
                                         entrada_xy=(118.0, 0.0), ancho_repisa=16.5, bulto_pared=1.5)
# --- 2) lazo: semicirculo r=38 cerrado por una cuerda metida 6 m, desplazado
pts_l = [(600 + 57 * math.cos(math.pi * 0.1 + math.pi * 1.8 * k / 60), 57 * math.sin(math.pi * 0.1 + math.pi * 1.8 * k / 60))
         for k in range(61)]
# la abertura del lazo (angulo 0, lado +X) se cierra con una cuerda metida 6 m
pts_l += [(600 + 47, -13.0), (600 + 45, 0.0), (600 + 47, 13.0)]
raiz_l, info_l = pp.build_desde_contorno(col, pts_l, altura=90.0, z_base=2.5, n_terrazas=4, seed=9,
                                         entrada_xy=(600.0 + 47, 0.0), ancho_repisa=12.5, ancho_carretera=4.5, bulto_pared=0.3)
bpy.context.view_layer.update()

fallos = []
for raiz, info, nombre in ((raiz_e, info_e, 'elipse'), (raiz_l, info_l, 'lazo')):
    roca = next(o for o in raiz.children_recursive if o.name.startswith('PPUEBLO_roca'))
    tris = sum(len(p.vertices) - 2 for p in roca.data.polygons)
    tot = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in raiz.children_recursive if o.type == 'MESH')
    # malla cerrada: rayo vertical por el centro entra y sale
    cx, cy = info['centro_top']
    hits = 0
    orig = Vector((cx, cy, 400.0))
    d = Vector((0, 0, -1))
    dist = 0.0
    while True:
        h, loc, n, i = roca.ray_cast(orig, d, distance=500.0)
        if not h:
            break
        hits += 1
        orig = loc + d * 0.05
        if hits > 10:
            break
    z_hit = None
    h, loc, n, i = roca.ray_cast(Vector((cx, cy, 400.0)), d, distance=500.0)
    if h:
        z_hit = loc.z
    # solares: sobre la repisa (roca justo debajo, a la cota del solar)
    malos = 0
    for lot in info['plazas_casas']:
        # la mitad trasera de la casa va dentro de la roca: se comprueba el frente (fachada +Y girada rot_z)
        # (x,y) = linea de fachada; el fondo de la casa (fondo_max) debe seguir sobre la repisa
        fx, fy = -math.sin(lot['rot_z']), math.cos(lot['rot_z'])
        px, py = lot['x'] - fx * (lot['fondo_max'] - 0.4), lot['y'] - fy * (lot['fondo_max'] - 0.4)
        h, loc, n, i = roca.ray_cast(Vector((px, py, lot['z'] + 60.0)), d, distance=200.0)
        if not h or abs(loc.z - lot['z']) > 1.5:
            malos += 1
    print('%s: roca %d tris (total %d), rayos por el centro: %d (par => cerrada), cima z=%.1f (esperada %.1f), '
          'solares mal apoyados %d/%d, %d vueltas, pend %.1f%%'
          % (nombre, tris, tot, hits, z_hit if z_hit is not None else -1, info['z_top'], malos, len(info['plazas_casas']),
             info['n_terrazas'], info['pendiente'] * 100))
    if hits % 2 != 0 or hits == 0:
        fallos.append('%s: malla de roca no cerrada (%d impactos)' % (nombre, hits))
    if z_hit is None or abs(z_hit - info['z_top']) > 0.5:
        fallos.append('%s: la cima no esta a z_top' % nombre)
    if malos > len(info['plazas_casas']) * 0.1:
        fallos.append('%s: %d solares mal apoyados' % (nombre, malos))
    if tot > 60000:
        fallos.append('%s: %d tris (> 60k)' % (nombre, tot))

# --- escena de render
world = bpy.data.worlds.new('W')
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs[0].default_value = (0.55, 0.72, 0.95, 1)
bg.inputs[1].default_value = 1.0
sun = bpy.data.objects.new('Sol', bpy.data.lights.new('Sol', 'SUN'))
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
sc.collection.objects.link(sun)
suelo = bpy.data.meshes.new('suelo')
suelo.from_pydata([(-400, -400, -5.2), (900, -400, -5.2), (900, 400, -5.2), (-400, 400, -5.2)], [], [(0, 1, 2, 3)])
ms = bpy.data.materials.new('MAT_suelo_test')
ms.use_nodes = True
ms.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.25, 0.45, 0.20, 1)
suelo.materials.append(ms)
sc.collection.objects.link(bpy.data.objects.new('suelo', suelo))
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 35
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1280, 900
sc.eevee.taa_render_samples = 24
os.makedirs(os.path.join(AQUI, 'previews'), exist_ok=True)
os.makedirs(os.path.join(AQUI, 'blend'), exist_ok=True)


def mirar(cam, pos, obj):
    cam.location = Vector(pos)
    dv = Vector(obj) - cam.location
    cam.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()


for nombre, pos, obj in (('penon_pueblo', (330, -300, 150), (0, 0, 55)),
                         ('penon_pueblo_entrada', (215, -60, 22), (60, 0, 40)),
                         ('penon_pueblo_cima', (60, -240, 220), (0, 0, 110)),
                         ('penon_pueblo_lazo', (600 + 150, -170, 110), (600, 0, 45)),
                         ('penon_pueblo_lazo_calle', (600 + 62, -48, 26), (600 + 20, 10, 40))):
    mirar(cam, pos, obj)
    sc.render.filepath = os.path.join(AQUI, 'previews', nombre + '.png')
    bpy.ops.render.render(write_still=True)
    print('render:', nombre)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, 'blend', 'penon_pueblo.blend'))
if fallos:
    for f in fallos:
        print('FALLO:', f)
    sys.exit(1)
print('OK test_penon_pueblo')
