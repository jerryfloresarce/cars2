"""test_roca_lazo.py - construye la ROCA DEL LAZO sobre las muestras reales
(curva 42 - 25 hasta curva 44 + 10) con un TABLERO DE PRUEBA gris, carga los
kits (casas_kit_v2, vegetacion_kit_v2, italiano_kit, yates_kit), imprime las
comprobaciones (rayos del tablero, contacto, casas, matas apoyadas, bordes de
la roca sobre el agua, limites de material verticales) y renderiza previews a
previews/roca_lazo_*.png: 4 vistas aereas (N, S, E, O), 1 cenital, 2 desde
1.5 m sobre el tablero (paso alto y paso bajo), terrazas, plaza, cala, 2 de la
cara de corte desde el tablero (estratos), matas de cerca y linea de agua;
por cada CARRETERA de acceso (H2-5): boca desde la pista, dron, tramo,
llegada y piazzola; y 2 vistas con culling de caras traseras (como AC: la roca
debe verse maciza, H2-1). Exige ademas roca orientada hacia fuera, 0 mallas
boca abajo y carreteras sin nada encima. Usa el mismo talud bajo el tablero que
integrar_escena (80 grados). '-- sincala': sin la carretera de la cala.

  bash 03_blender/_rev/blender_cola.sh --python test_roca_lazo.py [-- rapido] [sinrender] [talud70] [sincala]
      [sin_n2] [dump <ruta>] [muestreo <ruta>]   (env PREVIEWS=<carpeta>: previews en otra carpeta)
  v3: vistas del revisor (piloto s 3760/3800/3860, cuenco_tele_3760, cuenco_alto) y de la puerta peatonal
  (verja en el hueco del pretil, losa de umbral); exige 0 vertices a < w/2 + 0.3 del asfalto (como
  _rev/nada_en_pista.py) y que las puertas de escalera lleven valla=None (el integrador no la mueve).
"""
import importlib.util
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
RAPIDO = '--' in sys.argv and 'rapido' in sys.argv[sys.argv.index('--') + 1:]
SIN_RENDER = '--' in sys.argv and 'sinrender' in sys.argv[sys.argv.index('--') + 1:]


def cargar(nombre):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(AQUI, nombre + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


rl = cargar('roca_lazo')
kits = {}
for nombre in ('casas_kit_v2', 'vegetacion_kit_v2', 'italiano_kit', 'yates_kit', 'caminos_kit'):
    try:
        kits[nombre] = cargar(nombre)
        print('kit cargado:', nombre)
    except Exception as e:
        print('kit NO disponible:', nombre, e)
        kits[nombre] = None

# --- geometria: copia local del snapshot (otro agente reescribe geometria_3d.json)
ruta = os.path.join(AQUI, '_geom_snapshot_roca_lazo.json')
if not os.path.exists(ruta):
    import shutil
    shutil.copy(os.path.join(AQUI, '..', 'geometria_3d.json'), ruta)
G = json.load(open(ruta, encoding='utf-8'))
S = G['muestras']
N = len(S)
CUR = {c['n']: c for c in G['curvas']}
ia, ib = CUR[42]['s_idx'] - 25, CUR[44]['s_idx'] + 10
campos = ('x', 'y', 'z', 'nx', 'ny', 'w')
muestras = [{k: S[i % N][k] for k in campos} for i in range(ia, ib + 1)]
antes = [{k: S[i % N][k] for k in campos} for i in range(ia - 45, ia)]
despues = [{k: S[i % N][k] for k in campos} for i in range(ib + 1, ib + 46)]
z_mar = float(G.get('nivel_mar', 0.0))
print('muestras %d..%d (%d), z %.1f -> %.1f, z_mar %.1f' % (ia, ib, len(muestras), muestras[0]['z'], muestras[-1]['z'], z_mar))

sc = bpy.context.scene
for ob in list(sc.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
col = bpy.data.collections.new('ROCA_LAZO')
sc.collection.children.link(col)


def mat_simple(nombre, color, rough=0.8):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
    bs.inputs['Roughness'].default_value = rough
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


# --- tablero de prueba: cinta de ancho w a la cota de cada muestra + faldones de 3.2 m
def tablero(lista, nombre, color):
    vs, fs = [], []
    for m in lista:
        h = m['w'] / 2.0
        for sgn in (1.0, -1.0):
            vs.append((m['x'] + m['nx'] * h * sgn, m['y'] + m['ny'] * h * sgn, m['z']))
            vs.append((m['x'] + m['nx'] * h * sgn, m['y'] + m['ny'] * h * sgn, m['z'] - 3.2))
    for k in range(len(lista) - 1):
        o = 4 * k
        fs.append((o, o + 2, o + 6, o + 4))          # calzada
        fs.append((o, o + 4, o + 5, o + 1))          # faldon izq
        fs.append((o + 2, o + 3, o + 7, o + 6))      # faldon der
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(vs, [], fs)
    me.materials.append(mat_simple('MAT_TEST_' + nombre, color))
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    return ob


tablero(muestras, 'TEST_tablero', (0.30, 0.30, 0.32))
tablero(antes + [muestras[0]], 'TEST_tablero_antes', (0.42, 0.42, 0.44))
tablero([muestras[-1]] + despues, 'TEST_tablero_despues', (0.42, 0.42, 0.44))
# linea central blanca para leer la calzada
vs, fs = [], []
for m in muestras:
    for sgn in (0.15, -0.15):
        vs.append((m['x'] + m['nx'] * sgn, m['y'] + m['ny'] * sgn, m['z'] + 0.03))
for k in range(len(muestras) - 1):
    fs.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
me = bpy.data.meshes.new('TEST_linea')
me.from_pydata(vs, [], fs)
me.materials.append(mat_simple('MAT_TEST_linea', (0.9, 0.9, 0.9)))
col.objects.link(bpy.data.objects.new('TEST_linea', me))

t0 = time.time()
DUMP = None
if '--' in sys.argv:
    extra = sys.argv[sys.argv.index('--') + 1:]
    if 'dump' in extra:
        DUMP = extra[extra.index('dump') + 1] if len(extra) > extra.index('dump') + 1 else os.path.join(AQUI, '_lazo_dump')
# mismo talud bajo el tablero que integrar_escena.zona_rocas_pueblo_lazo (80 grados); '-- talud70' para el defecto
TALUD = 70.0 if ('--' in sys.argv and 'talud70' in sys.argv[sys.argv.index('--') + 1:]) else 80.0
raiz, info = rl.build(col, muestras, z_mar, seed=9, casas_kit=kits['casas_kit_v2'], vegetacion_kit=kits['vegetacion_kit_v2'],
                      italiano_kit=kits['italiano_kit'], yates_kit=kits['yates_kit'], caminos_kit=kits['caminos_kit'],
                      muestras_contexto=(antes, despues),
                      cell=(1.8 if RAPIDO else 1.0), debug_dump=DUMP, talud_bajo_tablero_deg=TALUD,
                      carretera_cala=not ('--' in sys.argv and 'sincala' in sys.argv[sys.argv.index('--') + 1:]),
                      coronacion_v3=not ('--' in sys.argv and 'sin_n2' in sys.argv[sys.argv.index('--') + 1:]))
print('build en %.1f s' % (time.time() - t0))
ck = info['checks']
tot = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in raiz.children_recursive if o.type == 'MESH')
print('TRIS totales bajo PENON_puente: %d' % tot)
# v3 (N2): '-- muestreo <ruta>' -> cota de PENON_puente_roca (primer impacto desde arriba) en rejilla de 1 m
# (<ruta>.npy + <ruta>.json) para buscar 'cuencos' con el python del sistema (como verif/actual/cuencos.py)
if '--' in sys.argv and 'muestreo' in sys.argv[sys.argv.index('--') + 1:]:
    import numpy as np
    ex_ = sys.argv[sys.argv.index('--') + 1:]
    ruta_m = ex_[ex_.index('muestreo') + 1]
    roca_ = bpy.data.objects.get('PENON_puente_roca')
    bpy.context.view_layer.update()
    xs_ = [v.co.x for v in roca_.data.vertices]
    ys_ = [v.co.y for v in roca_.data.vertices]
    X0_, Y0_ = math.floor(min(xs_)), math.floor(min(ys_))
    nx_, ny_ = int(max(xs_) - X0_) + 2, int(max(ys_) - Y0_) + 2
    Hs = np.full((ny_, nx_), np.nan)
    for jy in range(ny_):
        for ix_ in range(nx_):
            ok_, loc_, _n, _f = roca_.ray_cast(Vector((X0_ + ix_, Y0_ + jy, 400.0)), Vector((0, 0, -1)), distance=500.0)
            if ok_:
                Hs[jy, ix_] = loc_.z
    np.save(ruta_m + '.npy', Hs)
    json.dump({'x0': X0_, 'y0': Y0_, 'cell': 1.0, 'nx': nx_, 'ny': ny_,
               'plaza': info['plaza']['poligono'], 'centro_top': info['centro_top']}, open(ruta_m + '.json', 'w'), default=str)
    print('MUESTREO roca: %d x %d -> %s.npy' % (nx_, ny_, ruta_m))

# v3 (solo para las vistas, despues de los checks): ala del tablero hasta w/2 + 0.5 (viaducto_curvo usa ancho w + 1)
# y pretil de prueba como VIADUCTO_tramo_balaustrada (0.04..0.48 m del borde, 1.0 m) abierto 'ancho' en cada puerta,
# como integrar_escena._abrir_pretil_puertas
huecos = [(p['muestra'] * 2.0, p['ancho']) for p in info['puertas']]
lado_p = info['puertas'][0]['lado'] if info['puertas'] else -1
vs, fs = [], []
for i in range(len(muestras) - 1):
    a, b = muestras[i], muestras[i + 1]
    for q in range(4):
        f0, f1 = q / 4.0, (q + 1) / 4.0
        s_m = (i + (f0 + f1) / 2.0) * 2.0
        con_pretil = not any(abs(s_m - s_h) < an_ / 2.0 for (s_h, an_) in huecos)
        for (l0, l1, z0, z1, ok_) in ((0.0, 0.5, -0.25, 0.0, True), (0.04, 0.48, 0.0, 1.0, con_pretil)):
            if not ok_:
                continue
            base = len(vs)
            for f in (f0, f1):
                m = {k: a[k] + (b[k] - a[k]) * f for k in ('x', 'y', 'z', 'nx', 'ny', 'w')}
                for l_ in (l0, l1):
                    lt = lado_p * (m['w'] / 2.0 + l_)
                    for z_ in (z0, z1):
                        vs.append((m['x'] + m['nx'] * lt, m['y'] + m['ny'] * lt, m['z'] + z_))
            # 8 vertices: (f, l, z) -> indice base + 4*f + 2*l + z
            def V(f, l, z):
                return base + 4 * f + 2 * l + z
            fs += [(V(0, 0, 1), V(1, 0, 1), V(1, 1, 1), V(0, 1, 1)), (V(0, 0, 0), V(0, 1, 0), V(1, 1, 0), V(1, 0, 0)),
                   (V(0, 0, 0), V(1, 0, 0), V(1, 0, 1), V(0, 0, 1)), (V(0, 1, 0), V(0, 1, 1), V(1, 1, 1), V(1, 1, 0)),
                   (V(0, 0, 0), V(0, 0, 1), V(0, 1, 1), V(0, 1, 0)), (V(1, 0, 0), V(1, 1, 0), V(1, 1, 1), V(1, 0, 1))]
me = bpy.data.meshes.new('TEST_pretil')
me.from_pydata(vs, [], fs)
import bmesh
bm_ = bmesh.new()
bm_.from_mesh(me)
bmesh.ops.recalc_face_normals(bm_, faces=bm_.faces)
bm_.to_mesh(me)
bm_.free()
me.materials.append(mat_simple('MAT_TEST_pretil', (0.78, 0.72, 0.58)))
col.objects.link(bpy.data.objects.new('TEST_pretil', me))

# --- mar y escena
cx, cy = info['centro_top']
mar = bpy.data.meshes.new('TEST_mar')
mar.from_pydata([(cx - 700, cy - 700, z_mar), (cx + 700, cy - 700, z_mar), (cx + 700, cy + 700, z_mar), (cx - 700, cy + 700, z_mar)], [], [(0, 1, 2, 3)])
mar.materials.append(mat_simple('MAT_TEST_mar', (0.05, 0.30, 0.45), 0.2))
col.objects.link(bpy.data.objects.new('TEST_mar', mar))
world = bpy.data.worlds.new('W')
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs[0].default_value = (0.60, 0.75, 0.95, 1)
bg.inputs[1].default_value = 0.55
sun = bpy.data.objects.new('Sol', bpy.data.lights.new('Sol', 'SUN'))
sun.data.energy = 1.7
sun.rotation_euler = (math.radians(48), 0, math.radians(-35))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 32
cam.data.clip_end = 3000
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = (960, 640) if RAPIDO else (1400, 900)
sc.eevee.taa_render_samples = 8 if RAPIDO else 24
# env PREVIEWS: otra carpeta para las previews (comparaciones antes/despues sin pisar las de assets/previews)
PREV = os.environ.get('PREVIEWS') or os.path.join(AQUI, 'previews')
os.makedirs(PREV, exist_ok=True)


def mirar(pos, obj):
    cam.location = Vector(pos)
    dv = Vector(obj) - cam.location
    cam.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()


def render(nombre):
    if SIN_RENDER:
        return
    sc.render.filepath = os.path.join(PREV, nombre + '.png')
    bpy.ops.render.render(write_still=True)
    print('render:', sc.render.filepath)


z_c = info['z_cumbre']
objetivo = (cx, cy, 45.0)
for nombre, (dx, dy) in (('N', (0, 1)), ('S', (0, -1)), ('E', (1, 0)), ('O', (-1, 0))):
    mirar((cx + dx * 420, cy + dy * 420, 230), objetivo)
    render('roca_lazo_aerea_' + nombre)
mirar((cx + 0.01, cy + 0.01, 620), (cx, cy, 0.0))
render('roca_lazo_cenital')
# desde el tablero (1.5 m), hacia la roca: en el paso alto y en el bajo (donde estan las puertas)
cam.data.lens = 24
for p in info['puertas']:
    j = p['muestra']
    k = max(0, j - 30) if p['nombre'].endswith('alto') else min(len(muestras) - 1, j + 30)
    m = muestras[k]
    ojo = (m['x'] + m['nx'] * 2.0, m['y'] + m['ny'] * 2.0, m['z'] + 1.5)
    mirar(ojo, (p['x'], p['y'], p['z'] + 2.5))
    render('roca_lazo_tablero_' + p['nombre'].split('_')[-1])
    if p.get('tipo') != 'carretera' and p.get('verja'):
        # v3: la puerta peatonal de cerca (verja en el hueco del pretil, retranqueada, y losa de umbral)
        mq = muestras[max(0, j - 7)]
        cam.data.lens = 30
        mirar((mq['x'] - p['lado'] * mq['nx'] * 3.0, mq['y'] - p['lado'] * mq['ny'] * 3.0, mq['z'] + 1.6), (p['x'], p['y'], p['z'] + 0.6))
        render('roca_lazo_puerta_' + p['nombre'].split('_')[-1])
        mirar((p['x'] - p['lado'] * muestras[j]['nx'] * 7.0, p['y'] - p['lado'] * muestras[j]['ny'] * 7.0, p['z'] + 9.0),
              (p['x'], p['y'], p['z']))
        render('roca_lazo_puerta_%s_alto' % p['nombre'].split('_')[-1])
# terrazas de cerca, plaza y cala (donde estan las casas, escaleras y muros)
S0 = info['cumbre']
T2, T1 = info['terrazas'][0], info['terrazas'][1]
m2 = T2['front'][len(T2['front']) // 2]
m1 = T1['front'][len(T1['front']) // 2]
dv = Vector((m2[0] - S0[0], m2[1] - S0[1], 0.0)).normalized()
cam.data.lens = 30
mirar((m1[0] + dv.x * 50, m1[1] + dv.y * 50, T1['z'] + 14), (m2[0], m2[1], T2['z'] - 6))
render('roca_lazo_terrazas')
dp = Vector((m2[0] - cx, m2[1] - cy, 0.0)).normalized()
mirar((cx - dp.y * 70, cy + dp.x * 70, info['z_top'] + 32), (cx, cy, info['z_top'] + 2))
render('roca_lazo_plaza')
if info['cala']:
    cc = info['cala']['centro']
    dc = Vector((cc[0] - S0[0], cc[1] - S0[1], 0.0)).normalized()
    mirar((cc[0] + dc.x * 120, cc[1] + dc.y * 120, 24), (cc[0], cc[1], 5))
    render('roca_lazo_cala')
# cara de corte desde el tablero (estratos: limites horizontales, sin dientes), como v_h4_cara_4060/4250
lado = info['puertas'][0]['lado'] if info['puertas'] else -1
for nombre, (j0, j1, lat_o, dz_o) in (('roca_lazo_cara_corte_a', (57, 67, 18.0, 10.0)), ('roca_lazo_cara_corte_b', (157, 157, 20.0, 14.0))):
    if j1 >= len(muestras):
        continue
    m0, m1 = muestras[j0], muestras[j1]
    cam.data.lens = 30
    mirar((m0['x'] - lado * m0['nx'] * 4.0, m0['y'] - lado * m0['ny'] * 4.0, m0['z'] + 1.5),
          (m1['x'] + lado * m1['nx'] * lat_o, m1['y'] + lado * m1['ny'] * lat_o, m1['z'] + dz_o))
    render(nombre)
# matas de cerca (apoyadas en la ladera) y linea de agua por fuera del tablero (roca cerrada hasta el mar)
mt = bpy.data.objects.get('PENON_puente_matas')
if mt is not None and len(mt.data.vertices) >= 12:
    vs = mt.data.vertices
    k = (len(vs) // 12 // 3) * 12
    c = sum((vs[k + q].co for q in range(12)), Vector()) / 12.0
    d = Vector((c.x - cx, c.y - cy, 0.0)).normalized()
    cam.data.lens = 40
    mirar((c.x + d.x * 11.0, c.y + d.y * 11.0, c.z + 2.0), (c.x, c.y, c.z))
    render('roca_lazo_matas')
j_ag = min(len(muestras) - 1, 122)
m = muestras[j_ag]
C_ = Vector((sum(q['x'] for q in muestras) / len(muestras), sum(q['y'] for q in muestras) / len(muestras), 0.0))
o_ = Vector((m['x'] - C_.x, m['y'] - C_.y, 0.0)).normalized()
base = Vector((m['x'], m['y'], 0.0))
cam.data.lens = 30
mirar(base + o_ * (m['w'] / 2.0 + 16.0) + Vector((0, 0, 1.0)), base - o_ * 3.0 + Vector((0, 0, 1.0)))
render('roca_lazo_agua')
# v3 (N2/H7): las vistas del revisor (verif/actual/hueco_pix.py, gen_vistas.py): piloto en el viaducto largo
# (s 3760/3800/3860, 1.4 m, mirando 80 m adelante) y teleobjetivo / de cerca al 'cuenco' de (129.3, -592.1, 85.8)


def fr_s(s_m):
    return S[int(round(s_m / 2.0)) % N]


for s_v in (3760, 3800, 3860):
    a_, b_ = fr_s(s_v), fr_s(s_v + 80)
    cam.data.lens = 26
    mirar((a_['x'], a_['y'], a_['z'] + 1.4), (b_['x'], b_['y'], b_['z'] + 1.2))
    render('roca_lazo_piloto_%d' % s_v)
a_ = fr_s(3760)
h_c = Vector((129.3, -592.1, 85.8))
cam.data.lens = 80
mirar((a_['x'], a_['y'], a_['z'] + 1.4), h_c)
render('roca_lazo_cuenco_tele_3760')
cam.data.lens = 30
mirar(h_c + Vector((25, -25, 30)), h_c)
render('roca_lazo_cuenco_alto')
# env VISTAS_EXTRA='[["nombre", [x, y, z], [tx, ty, tz], lens], ...]': vistas de QA a medida
for nom_, loc_, tgt_, lens_ in json.loads(os.environ.get('VISTAS_EXTRA') or '[]'):
    cam.data.lens = float(lens_)
    mirar(tuple(loc_), tuple(tgt_))
    render('roca_lazo_x_' + nom_)
# H2-5: carretera de acceso en coche (boca desde la pista, vista de dron y llegada a la piazzola)
for c in info.get('carreteras') or []:
    eje = c['eje']
    p_d = next((p for p in info['puertas'] if p['nombre'] == c['nombre']), None)
    if p_d is not None:
        j = p_d['muestra']
        m = muestras[max(0, min(len(muestras) - 1, j - 12))]
        cam.data.lens = 26
        mirar((m['x'] + m['nx'] * 1.0, m['y'] + m['ny'] * 1.0, m['z'] + 1.5), (eje[8][0], eje[8][1], eje[8][2] + 1.5))
        render('roca_lazo_carretera_%s_boca' % c['nombre'])
    mid = eje[len(eje) // 2]
    d0 = Vector((eje[-1][0] - eje[0][0], eje[-1][1] - eje[0][1], 0.0)).normalized()
    cam.data.lens = 24
    mirar((mid[0] - d0.y * 30.0 - d0.x * 40.0, mid[1] + d0.x * 30.0 - d0.y * 40.0, mid[2] + 120.0), (mid[0], mid[1], mid[2]))
    render('roca_lazo_carretera_%s_dron' % c['nombre'])
    # piazzola de llegada vista desde arriba (a 45 grados), con la terraza / el muelle alrededor
    if c.get('piazzola_disco'):
        qx, qy, _qr = c['piazzola_disco']
    else:
        pz_ = c['piazzola'][len(c['piazzola']) // 2]
        qx, qy = (pz_[0][0] + pz_[1][0]) / 2.0, (pz_[0][1] + pz_[1][1]) / 2.0
    dq = Vector((qx - eje[-12][0], qy - eje[-12][1], 0.0)).normalized()
    cam.data.lens = 26
    mirar((qx - dq.x * 22.0, qy - dq.y * 22.0, c['z_piazzola'] + 20.0), (qx, qy, c['z_piazzola']))
    render('roca_lazo_carretera_%s_piazzola' % c['nombre'])
    for frac, tag in ((0.35, 'tramo'), (0.75, 'llegada')):
        k = int(frac * (len(eje) - 1))
        k2 = min(len(eje) - 1, k + 25)
        mirar((eje[k][0], eje[k][1], eje[k][2] + 1.6), (eje[k2][0], eje[k2][1], eje[k2][2] + 1.2))
        render('roca_lazo_carretera_%s_%s' % (c['nombre'], tag))
# H2-1: con culling de caras traseras (como AC) la roca debe verse MACIZA, no una cascara hueca
if not SIN_RENDER:
    for mt_ in bpy.data.materials:
        mt_.use_backface_culling = True
    cam.data.lens = 30
    mirar((cx + 380, cy - 60, 40), (cx, cy, 30.0))
    render('roca_lazo_culling_lateral')
    mirar((cx - 60, cy + 420, 160), (cx, cy, 30.0))
    render('roca_lazo_culling_norte')
    for mt_ in bpy.data.materials:
        mt_.use_backface_culling = False
if not RAPIDO and not SIN_RENDER and not os.environ.get('PREVIEWS'):
    os.makedirs(os.path.join(AQUI, 'blend'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, 'blend', 'roca_lazo.blend'))
fallos = []
if ck['rayos_roca'] or ck['rayos_obra']:
    fallos.append('rayos del tablero atraviesan la roca/obra: %d/%d' % (ck['rayos_roca'], ck['rayos_obra']))
if ck['contacto_pct'] <= 90.0:
    fallos.append('contacto insuficiente: %.1f %%' % ck['contacto_pct'])
for clave, texto in (('casas_intersectando', 'casas con roca dentro'), ('casas_flotantes', 'casas flotantes'),
                     ('casas_trasera_en_roca', 'casas con roca a 1.5 m detras'), ('casas_cruzadas', 'casas cruzadas en planta'),
                     ('casas_a_menos_de_1_5m', 'pares de casas a < 1.5 m'), ('solapes_casa_obra', 'casas que cortan muros/escaleras/obra'),
                     ('solapes_casa_casa_bvh', 'pares casa-casa (BVH)'), ('solapes_escaleras_muros', 'pares escalera-muro (BVH)'),
                     ('vegetacion_mal_asentada', 'arboles mal asentados'), ('puertas_hacia_pista', 'puertas que abren hacia la pista'),
                     ('matas_flotando', 'matas flotando (> 0.3 m)'), ('matas_cortan_obra', 'pares mata-obra/casa (BVH)'),
                     ('roca_bordes_sobre_agua', 'aristas abiertas de la roca sobre el agua')):
    if ck.get(clave):
        fallos.append('%d %s' % (ck[clave], texto))
if not ck.get('roca_orientada_fuera'):
    fallos.append('PENON_puente_roca con las caras hacia DENTRO: %s' % ck.get('roca_orientacion'))
if ck.get('mallas_boca_abajo'):
    fallos.append('mallas con el techo boca abajo: %s' % ck['mallas_boca_abajo'])
if not ck.get('carreteras'):
    fallos.append('sin carretera de acceso en coche (H2-5)')
elif not ck.get('carreteras_ok'):
    fallos.append('carretera de acceso con fallos: %s' % ck['carreteras'])
if ck.get('cerca_asfalto_n', 1):
    fallos.append('vertices a < w/2 + 0.3 m del asfalto (nada_en_pista): %d %s' % (ck.get('cerca_asfalto_n', -1), ck.get('cerca_asfalto')))
for p in info['puertas']:
    # v3: integrar_escena._abrir_pretil_puertas solo mueve la verja / pone su losa si p['valla'] (tipo escalera):
    # la de roca_lazo ya va en el hueco, retranqueada, con su losa
    if p.get('tipo') != 'carretera' and (p.get('valla') or not p.get('verja') or not p.get('losa')):
        fallos.append('puerta %s: valla=%s (debe ser None), verja=%s, losa=%s' % (p['nombre'], p.get('valla'), p.get('verja'), p.get('losa')))
if ck.get('limites_verticales_pct', 0.0) >= 2.0:
    fallos.append('limites de material verticales en cara empinada: %.2f %% (>= 2 %%)' % ck['limites_verticales_pct'])
print('CHECKS', {k: ck.get(k) for k in ('rayos_roca', 'rayos_obra', 'contacto_pct', 'casas', 'matas_flotando', 'matas_hueco_max', 'matas_cortan_obra',
                                         'roca_bordes_sobre_agua', 'limites_material', 'limites_verticales_empinados',
                                         'limites_verticales_pct', 'particion_materiales', 'roca_orientacion',
                                         'roca_orientada_fuera', 'mallas_boca_abajo', 'carreteras', 'cerca_asfalto_n',
                                         'cerca_asfalto_margen', 'coronacion_n2')})
print('PUERTAS', [{k: p.get(k) for k in ('nombre', 'tipo', 'muestra', 'lado', 'ancho', 'x', 'y', 'z')} for p in info['puertas']])
if not ck.get('ok'):
    fallos.append('info[checks][ok] es False')
for f in fallos:
    print('FALLO:', f)
print('OK test_roca_lazo' if not fallos else 'test_roca_lazo con fallos')
