"""test_caminos_kit.py - construye el escaparate de caminos_kit sobre un
terreno de prueba (z_demo aplanado junto a los trazados), cuatro tramos
rectos de cada tipo de cerca, comprueba presupuestos/normales/hijos y
renderiza previews/caminos_kit.png, caminos_tipos.png, caminos_valla.png,
caminos_puente.png, caminos_muro.png y los empalmes de cerca
(caminos_muelle.png, caminos_adoquin.png, caminos_empalme.png). Comprueba
ademas que los vados de la principal bajan solo el bordillo del lado que
empalma, que los laterales arrancan a la cota real del borde, que la valla
del muelle cabe entre los pretiles, que el tablero del puente queda a z=0
con las pilastras fuera de la calzada y los caminos de tierra empalmando a
ras, que el poste del cartel no asoma sobre el panel y que los conos no
tienen tapa inferior coplanar con su base.

  blender --background --factory-startup --python test_caminos_kit.py
"""
import importlib.util
import math
import os
import sys

import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('caminos_kit', os.path.join(AQUI, 'caminos_kit.py'))
ck = importlib.util.module_from_spec(spec)
sys.modules['caminos_kit'] = ck
spec.loader.exec_module(ck)

sc = bpy.context.scene
for ob in list(sc.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
col = bpy.data.collections.new('CAMINOS')
sc.collection.children.link(col)
col_t = bpy.data.collections.new('TIPOS')
sc.collection.children.link(col_t)

raiz = ck.build(col, seed=1)

# --- muestrario de tipos: 4 tramos rectos de 24 m (x 290..314), planos
X0, LARGO = 290.0, 24.0
muestras = {}
for k, (tipo, y, z, extra) in enumerate((('asfalto', 0.0, 0.0, {}), ('tierra', 9.0, 0.0, {}),
                                          ('adoquin', 18.0, 0.0, {}),
                                          ('muelle', 29.0, 0.6, {'canto': 1.5, 'nivel_agua': -0.5}))):
    pts = [(X0 + LARGO * i / 8.0, y + 0.8 * math.sin(i * 0.9), z) for i in range(9)]
    muestras[tipo] = ck.build_camino(col_t, pts, ancho=5.0, tipo=tipo, seed=k, **extra)
bpy.context.view_layer.update()


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons) if ob.type == 'MESH' else 0


def tris_arbol(raiz_ob):
    return tris(raiz_ob) + sum(tris(o) for o in raiz_ob.children_recursive)


def largo_pl(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


fallos = []
# presupuesto de los caminos (<= 40 tris/m) y normales hacia arriba
trazados = {n: (p, s) for n, p, s in ck.DEMO_TRAZADOS}
mapa = {'CAMINO_asfalto': 'principal', 'CAMINO_asfalto.001': 'lateral', 'CAMINO_tierra': 'tierra1',
        'CAMINO_tierra.001': 'tierra2', 'CAMINO_adoquin': 'adoquin', 'CAMINO_muelle': 'muelle'}
caminos = [(o, largo_pl(trazados[mapa[o.name]][0])) for o in raiz.children if o.name in mapa]
caminos += [(o, LARGO) for o in muestras.values()]
for o, L in caminos:
    t = tris(o) + sum(tris(h) for h in o.children)
    ratio = t / max(1.0, L)
    hacia_abajo = sum(1 for p in o.data.polygons if p.normal.z < -0.2)
    print('%-22s %6.1f m  %6d tris  %5.1f tris/m  normales hacia abajo: %d' % (o.name, L, t, ratio, hacia_abajo))
    if ratio > 40.0:
        fallos.append('%s: %.1f tris/m (> 40)' % (o.name, ratio))
    if hacia_abajo:
        fallos.append('%s: %d caras mirando hacia abajo' % (o.name, hacia_abajo))
    if o.name.startswith('CAMINO_asfalto') and not any(h.name.startswith('CAMINO_marcas') for h in o.children):
        fallos.append('%s: sin hija CAMINO_marcas' % o.name)
# presupuestos de piezas sueltas
limites = {'CAMINO_valla': 3000, 'CAMINO_cartel': 1500, 'CAMINO_puente': 3000, 'CAMINO_muro': 5000}
for o in raiz.children:
    base = o.name.split('.')[0]
    if base in limites:
        t = tris_arbol(o)
        print('%-22s %6d tris (limite %d)' % (o.name, t, limites[base]))
        if t > limites[base]:
            fallos.append('%s: %d tris (> %d)' % (o.name, t, limites[base]))
        if base in ('CAMINO_valla', 'CAMINO_cartel'):
            txt = [h for h in o.children if h.name.startswith(base + '_texto')]
            if not txt or not txt[0].data.polygons:
                fallos.append('%s: texto 3D vacio' % o.name)
print('total escaparate: %d tris, %d objetos' % (tris_arbol(raiz), len(raiz.children_recursive)))

# --- empalmes: vados POR LADO en la principal, laterales a la cota del borde,
#     valla del muelle entre los pretiles
ppal_ob = bpy.data.objects['CAMINO_asfalto']


def cota_bordillo(x, lado):
    """z maxima de la malla de la principal sobre el bordillo de ese lado en x."""
    return max(v.co.z for v in ppal_ob.data.vertices
               if abs(v.co.x - x) < 0.4 and abs(v.co.y - lado * 5.125) < 0.2)


for x, lado, vado in ((-36.0, 1, True), (-36.0, -1, False), (18.0, 1, True), (18.0, -1, False),
                      (30.0, -1, True), (30.0, 1, False), (-60.0, 1, False), (-60.0, -1, False)):
    z_ref = ck.z_demo(x, 0.0) - 0.1 + (0.0 if vado else 0.12)
    z = cota_bordillo(x, lado)
    print('bordillo principal x=%5.1f lado %+d: z=%.3f (esperado %.3f, %s)' % (x, lado, z, z_ref, 'vado' if vado else 'entero'))
    if abs(z - z_ref) > 0.02:
        fallos.append('vado principal x=%.1f lado %+d: z=%.3f != %.3f' % (x, lado, z, z_ref))
for nombre, x in (('lateral', -35.0), ('adoquin', 18.0), ('muelle', 30.0)):
    p0 = trazados[nombre][0][0]
    z_ref = ck.z_demo(x, 0.0) - 0.1
    print('arranque %-8s (%.1f, %.2f, %.3f)  borde principal %.3f' % (nombre, p0[0], p0[1], p0[2], z_ref))
    if abs(p0[2] - z_ref) > 0.01 or abs(abs(p0[1]) - 5.2) > 0.01:
        fallos.append('%s arranca en (%.2f, %.3f), esperado (|5.20|, %.3f)' % (nombre, p0[1], p0[2], z_ref))
vallas = sorted((o for o in raiz.children if o.name.startswith('CAMINO_valla')), key=lambda o: o.name)
for v, libre in zip(vallas, (5.0, 4.5, 5.0)):
    cuerpo = [h for h in v.children if h.name.startswith('CAMINO_valla_cuerpo')][0]
    semi = max(abs(vv.co.x) for vv in cuerpo.data.vertices)
    print('%s: semiancho %.2f (calzada libre %.1f)  z=%.3f' % (v.name, semi, libre, v.location.z))
    if semi > libre / 2.0:
        fallos.append('%s: %.2f m de semiancho no cabe en %.1f m de calzada' % (v.name, semi, libre))
    if v.name == 'CAMINO_valla.002' and abs(v.location.z - (ck.z_demo(30.0, 0.0) - 0.1)) > 0.25:
        fallos.append('valla del muelle no esta sobre la calzada del muelle (z=%.3f)' % v.location.z)
    # conos: sin tapa inferior coplanar con la base negra (z=0.03 mirando abajo)
    copl = [p for p in cuerpo.data.polygons if p.normal.z < -0.9 and 0.02 < p.center.z < 0.04]
    if copl:
        fallos.append('%s: %d tapas de cono coplanares con la base' % (v.name, len(copl)))

# --- puente: tablero a z=0 exacto, pilastras fuera de la calzada libre
pu = [o for o in raiz.children if o.name.startswith('CAMINO_puente')][0]
pu_cuerpo = [h for h in pu.children if h.name.startswith('CAMINO_puente_cuerpo')][0]
ANCHO_PU, L_PU = 5.0, 12.0
# tablero: la cara mas alta mirando arriba cuyo centro cae en la calzada
# (las cajas solo tienen vertices en las esquinas: se mira por caras)
z_tab = max(p.center.z for p in pu_cuerpo.data.polygons
            if p.normal.z > 0.9 and abs(p.center.y) < ANCHO_PU / 2.0 - 0.1 and abs(p.center.x) < L_PU / 2.0 - 1.0)
# pilastras: caras laterales (normal +-Y) en los ultimos 1.0 m de cada
# extremo y por debajo de la albardilla; la mas interior debe quedar en
# |y| >= ancho/2 (la albardilla de 0.70 vuela 5 cm mas arriba, se excluye)
y_pil = min(abs(p.center.y) for p in pu_cuerpo.data.polygons
            if abs(p.normal.y) > 0.9 and abs(p.center.x) > L_PU / 2.0 - 1.0 and p.center.z < 0.9)
print('puente: tablero z max %.3f (esperado 0.000), pilastras/pretil |y| min %.3f (calzada libre %.2f)'
      % (z_tab, y_pil, ANCHO_PU))
if abs(z_tab) > 0.002:
    fallos.append('puente: superficie transitable en z=%.3f, no en 0' % z_tab)
if y_pil < ANCHO_PU / 2.0 - 0.002:
    fallos.append('puente: pilastras invaden la calzada (|y| min %.3f < %.3f)' % (y_pil, ANCHO_PU / 2.0))
# los caminos de tierra llegan al puente con la anchura exacta (sin bermas)
for nombre, extremo in (('tierra1', -1), ('tierra2', 0)):
    ob_t = bpy.data.objects['CAMINO_tierra' if nombre == 'tierra1' else 'CAMINO_tierra.001']
    px, py, pz = trazados[nombre][0][extremo]
    cerca = [v.co for v in ob_t.data.vertices if math.hypot(v.co.x - px, v.co.y - py) < 3.0 and v.co.z > pz - 0.2]
    semi = max(math.hypot(c.x - px, c.y - py) for c in cerca)
    z_max = max(c.z for c in cerca)
    print('%s en el puente: semiancho %.2f (esperado 2.50), z max %+.3f sobre el tablero' % (nombre, semi, z_max - pz))
    if semi > 2.55 or z_max > pz + 0.005:
        fallos.append('%s no empalma limpio con el puente (semi %.2f, dz %+.3f)' % (nombre, semi, z_max - pz))

# --- cartel: el poste no asoma por encima del panel (canto superior 2.45)
for c in (o for o in raiz.children if o.name.startswith('CAMINO_cartel')):
    cu = [h for h in c.children if h.name.startswith('CAMINO_cartel_cuerpo')][0]
    z_max = max(v.co.z for v in cu.data.vertices)
    z_poste = max(v.co.z for v in cu.data.vertices if v.co.y < -0.06 and abs(v.co.x) < 0.05)
    print('%s: z max cuerpo %.3f, cima del poste %.3f' % (c.name, z_max, z_poste))
    if z_max > 2.451 or z_poste > 2.44:
        fallos.append('%s: el poste asoma (cima %.3f, panel 2.45)' % (c.name, z_poste))

# --- terreno de prueba: rejilla 1 m aplanada junto a los trazados
NX, NY, PASO = 181, 141, 1.0
ORX, ORY = -85.0, -45.0
# la ladera tras el muro (cara trasera en lat 3.85) se realza a partir de
# lat 5.4: una celda + diagonal mas alla, para que ningun triangulo de la
# rejilla que arranque delante del muro suba y asome por su cara vista
LAT_MURO = 3.85 + PASO * 1.5
segs = []
for nombre, pts, semi in ck.DEMO_TRAZADOS:
    if semi <= 0.0:
        continue
    for a, b in zip(pts, pts[1:]):
        segs.append((a, b, semi + 0.6, nombre))


def z_terreno(x, y):
    """z_demo un pelin por debajo de las calzadas, aplanado junto a los
    trazados; el torrente no se aplana (lo salva el puente) y la ladera de
    detras del muro de contencion se realza 1.2 m (desde LAT_MURO) en vez
    de aplanarse."""
    z = ck.z_demo(x, y) - 0.07
    if abs(x - 46.0) < 6.5 and y > 30.0:
        return z
    mejor_w, mejor_z = 0.0, z
    z_plano = None  # el mas bajo de los trazados que aplanan del todo aqui
    detras_muro = 0.0
    for a, b, margen, nombre in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dy * dy
        u = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / l2))
        px, py = a[0] + dx * u, a[1] + dy * u
        d = math.hypot(x - px, y - py)
        if d > margen + 6.0:
            continue
        lat = ((x - px) * (-dy) + (y - py) * dx) / max(1e-9, math.sqrt(l2))  # > 0: izquierda (+n)
        if nombre == 'tierra1' and lat > LAT_MURO:
            detras_muro = max(detras_muro, min(1.0, (lat - LAT_MURO) / 4.0))  # rampa suave (sin cresta en sierra)
            continue
        if nombre == 'muro' and lat > 0.3:
            continue
        w = 1.0 if d <= margen else 1.0 - (d - margen) / 6.0
        zr = a[2] + (b[2] - a[2]) * u - 0.18
        if w >= 0.999:
            z_plano = zr if z_plano is None else min(z_plano, zr)
        if w > mejor_w:
            mejor_w, mejor_z = w, zr
    if z_plano is not None:
        mejor_z = z_plano
    return mejor_z * mejor_w + z * (1.0 - mejor_w) + 1.2 * detras_muro


vs = [(ORX + i * PASO, ORY + j * PASO, z_terreno(ORX + i * PASO, ORY + j * PASO))
      for j in range(NY) for i in range(NX)]
fs = [(j * NX + i, j * NX + i + 1, (j + 1) * NX + i + 1, (j + 1) * NX + i)
      for j in range(NY - 1) for i in range(NX - 1)]


def mat_plano(nombre, color, rough=0.9):
    m = bpy.data.materials.get(nombre)
    if m is None:
        m = bpy.data.materials.new(nombre)
        m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*color, 1)
        b.inputs['Roughness'].default_value = rough
    return m


def malla_plana(nombre, verts, caras, mat, col_dest):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], caras)
    me.materials.append(mat)
    me.validate()
    ob = bpy.data.objects.new(nombre, me)
    col_dest.objects.link(ob)
    return ob


terreno = malla_plana('terreno', vs, fs, mat_plano('MAT_test_hierba', (0.20, 0.38, 0.13)), sc.collection)
for p in terreno.data.polygons:
    p.use_smooth = True
malla_plana('mar', [(-120, -130, -0.4), (160, -130, -0.4), (160, -8, -0.4), (-120, -8, -0.4)], [(0, 1, 2, 3)],
            mat_plano('MAT_test_mar', (0.05, 0.42, 0.55), 0.15), sc.collection)
# suelo y agua del muestrario de tipos
malla_plana('suelo_tipos', [(270, -8, -0.03), (340, -8, -0.03), (340, 23.5, -0.03), (270, 23.5, -0.03)],
            [(0, 1, 2, 3)], mat_plano('MAT_test_hierba', (0.20, 0.38, 0.13)), sc.collection)
malla_plana('mar_tipos', [(270, 23.5, -0.5), (340, 23.5, -0.5), (340, 40, -0.5), (270, 40, -0.5)],
            [(0, 1, 2, 3)], mat_plano('MAT_test_mar', (0.05, 0.42, 0.55), 0.15), sc.collection)

# --- escena de render
world = bpy.data.worlds.new('W')
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs[0].default_value = (0.55, 0.72, 0.95, 1)
bg.inputs[1].default_value = 1.0
sun = bpy.data.objects.new('Sol', bpy.data.lights.new('Sol', 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(48), 0, math.radians(30))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1280, 800
sc.eevee.taa_render_samples = 24
try:
    sc.view_settings.view_transform = 'Standard'
except Exception:
    pass
try:
    sc.eevee.use_shadows = True
except AttributeError:
    pass
os.makedirs(os.path.join(AQUI, 'previews'), exist_ok=True)
os.makedirs(os.path.join(AQUI, 'blend'), exist_ok=True)


def mirar(pos, obj, lente=35):
    cam.location = Vector(pos)
    dv = Vector(obj) - cam.location
    cam.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lente


for nombre, pos, obj, lente in (('caminos_kit', (-12, -118, 78), (12, 28, 4), 35),
                                ('caminos_tipos', (292, -13, 12), (302, 13, 0.0), 30),
                                ('caminos_valla', (-27, -4.5, 2.6), (-37, 7.5, 1.3), 32),
                                ('caminos_puente', (38, 48, 10), (46, 63.5, 5.5), 35),
                                ('caminos_muro', (6, 38, 12), (18, 56, 7.5), 35),
                                ('caminos_muelle', (39.5, 0.5, 3.2), (31, -10, 0.4), 32),
                                ('caminos_adoquin', (10.5, -2.5, 3.0), (18.5, 8.5, 0.9), 32),
                                ('caminos_empalme', (-22, 36, 5.5), (-9, 47.5, 4.6), 32)):
    mirar(pos, obj, lente)
    sc.render.filepath = os.path.join(AQUI, 'previews', nombre + '.png')
    bpy.ops.render.render(write_still=True)
    print('render:', nombre)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, 'blend', 'caminos_kit.blend'))
if fallos:
    for f in fallos:
        print('FALLO:', f)
    sys.exit(1)
print('OK test_caminos_kit')
