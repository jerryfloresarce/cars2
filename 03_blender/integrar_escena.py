# Integra los assets procedurales en la escena base del circuito.
# Abre porto_corsa.blend, importa los modulos de 03_blender/assets, construye
# una biblioteca oculta y coloca clones por sectores del trazado.
# Ejecutar:
#   blender --background --factory-startup --python integrar_escena.py
import importlib.util
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
ASSETS = BASE + r'\03_blender\assets'
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
OUT_R = BASE + r'\03_blender\renders'

bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
scene = bpy.context.scene
root_col = scene.collection

S = G['muestras']
N = G['n']
paso = G['paso_m']
L = G['largo_m']
CURVAS = {c['n']: c for c in G['curvas']}
rnd = random.Random(42)

# --- modulos ---
# versiones v2 de los modulos (ronda 10): solo se usan las APROBADAS tras revisar
# sus previews; la lista vive en assets/v2_aprobados.txt (un nombre por linea)
_V2_OK = set()
_f_v2 = os.path.join(ASSETS, 'v2_aprobados.txt')
if os.path.exists(_f_v2):
    _V2_OK = {l.strip() for l in open(_f_v2, encoding='utf-8') if l.strip() and not l.startswith('#')}

def load_mod(name):
    fichero = name
    if name in _V2_OK and os.path.exists(os.path.join(ASSETS, name + '_v2.py')):
        fichero = name + '_v2'
        print('[integrar] modulo %s -> %s.py' % (name, fichero))
    spec = importlib.util.spec_from_file_location(name, os.path.join(ASSETS, fichero + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

M = {n: load_mod(n) for n in ['casino', 'penon_topolino', 'puentes', 'casas_kit',
                              'edificios_civicos', 'puerto_kit', 'carrera_kit',
                              'vegetacion_kit']}
for opcional in ('horquilla_loews', 'arco_roca', 'olivos', 'coches_kit',
                 'viaducto_curvo', 'acueducto', 'penon_cara', 'montanas_fondo',
                 'calle_kit', 'mirador_kit', 'camaras_kit', 'pit_kit', 'montana_rueda', 'penon_pueblo',
                 'caminos_kit', 'montana_coche', 'yates_kit', 'italiano_kit'):
    try:
        M[opcional] = load_mod(opcional)
    except Exception as e:
        M[opcional] = None
        print('[integrar] %s no disponible aun: %s' % (opcional, e))

# --- biblioteca oculta ---
LIB = bpy.data.collections.new('LIB')
root_col.children.link(LIB)
LIB.hide_render = True
LIB.hide_viewport = True

def lib_build(fn, **kw):
    obj = fn(LIB, **kw)
    return obj

def hierarchy(root):
    objs = [root]
    objs.extend(root.children_recursive)
    return objs

def _mat_simple(nombre, rgba, rough=0.9):
    m = bpy.data.materials.get(nombre)
    if m is None:
        m = bpy.data.materials.new(nombre)
        m.use_nodes = True
        bs = m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = rgba
        bs.inputs['Roughness'].default_value = rough
    return m

def clone(root, loc, rot_z=0.0, scale=1.0, pitch=0.0):
    mapping = {}
    for ob in hierarchy(root):
        nb = ob.copy()
        mapping[ob] = nb
        root_col.objects.link(nb)
    for ob, nb in mapping.items():
        if ob.parent in mapping:
            nb.parent = mapping[ob.parent]
    nr = mapping[root]
    nr.location = Vector(loc)
    nr.rotation_euler = (0, pitch, rot_z)
    if scale != 1.0:
        nr.scale = (scale, scale, scale)
    return nr

def _zocalo_global(raiz, z_fondo):
    """Zocalo de piedra bajo un edificio (hijo suyo): tapa el hueco entre su
    base y el terreno/roca en ladera."""
    m = bpy.data.materials.get('MAT_zocalo_piedra')
    if m is None:
        m = bpy.data.materials.new('MAT_zocalo_piedra')
        m.use_nodes = True
        bs = m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (0.55, 0.50, 0.40, 1)
        bs.inputs['Roughness'].default_value = 0.95
    bpy.context.view_layer.update()
    inv = raiz.matrix_world.inverted()
    xs, ys = [], []
    for ob in [raiz] + list(raiz.children_recursive):
        if ob.type != 'MESH' or ob.name.startswith('CASAS_zocalo'):
            continue
        for c in ob.bound_box:
            l = inv @ (ob.matrix_world @ Vector(c))
            xs.append(l.x)
            ys.append(l.y)
    if not xs:
        return None
    x0, x1 = min(xs) + 0.2, max(xs) - 0.2
    y0, y1 = min(ys) + 0.2, max(ys) - 0.2
    esc = raiz.scale.z or 1.0
    zb = min((max(z_fondo, -0.8) - raiz.location.z) / esc, -0.5)
    vs = [(x0, y0, zb), (x1, y0, zb), (x1, y1, zb), (x0, y1, zb),
          (x0, y0, 0.6), (x1, y0, 0.6), (x1, y1, 0.6), (x0, y1, 0.6)]
    fs = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0)]
    me = bpy.data.meshes.new('CASAS_zocalo')
    me.from_pydata(vs, [], fs)
    me.materials.append(m)
    zo = bpy.data.objects.new('CASAS_zocalo', me)
    root_col.objects.link(zo)
    zo.parent = raiz
    return zo

# --- terreno: muestreo bilineal ---
T = G['terreno']
def z_terreno(x, y):
    fx = (x - T['x0']) / T['cell']
    fy = (y - T['y0']) / T['cell']
    i0 = max(0, min(T['nx'] - 2, int(fx)))
    j0 = max(0, min(T['ny'] - 2, int(fy)))
    tx_ = min(max(fx - i0, 0), 1)
    ty_ = min(max(fy - j0, 0), 1)
    def zz(i, j):
        return T['z'][j * T['nx'] + i]
    return ((zz(i0, j0) * (1 - tx_) + zz(i0 + 1, j0) * tx_) * (1 - ty_)
            + (zz(i0, j0 + 1) * (1 - tx_) + zz(i0 + 1, j0 + 1) * tx_) * ty_)

# --- helpers de trazado ---
def idx(s_m):
    return int(round(((s_m % L) / paso))) % N

def frame(s_m):
    return S[idx(s_m)]

def tangent(s_m):
    p = frame(s_m)
    return (p['ny'], -p['nx'])  # t = rot(-90) de n

def pendiente(s_m, d=4.0):
    """Angulo (rad) de la rasante en el sentido de la marcha."""
    return math.atan2(frame(s_m + d)['z'] - frame(s_m - d)['z'], 2.0 * d)

_OCUPADO = {}
def pendiente_terreno(x, y, d=5.0):
    """Pendiente (m/m) del terreno alrededor de (x, y)."""
    gx = (z_terreno(x + d, y) - z_terreno(x - d, y)) / (2 * d)
    gy = (z_terreno(x, y + d) - z_terreno(x, y - d)) / (2 * d)
    return math.hypot(gx, gy)

def _libre(x, y, r=3.4):
    """True si no hay otro objeto de relleno a menos de r; reserva el sitio."""
    cx_, cy_ = int(x // 4), int(y // 4)
    for a_ in (-1, 0, 1):
        for b_ in (-1, 0, 1):
            for (px_, py_) in _OCUPADO.get((cx_ + a_, cy_ + b_), ()):
                if math.hypot(px_ - x, py_ - y) < r:
                    return False
    _OCUPADO.setdefault((cx_, cy_), []).append((x, y))
    return True

def pos_side(s_m, side, offset, z=None):
    p = frame(s_m)
    d = p['w'] / 2 + offset
    x = p['x'] + side * p['nx'] * d
    y = p['y'] + side * p['ny'] * d
    if z is None:
        if side == 0:
            z = p['z'] - 0.3
        elif offset <= 6.5:
            # junto a la calzada manda el arcen: plano 1.8 m y luego baja,
            # arrancando del borde PERALTADO (no del eje)
            z_borde = p['z'] - p['lat'] * side * (p['w'] / 2)
            caida = 0.05 if offset <= 1.8 else 0.05 + (offset - 1.8) * 0.33
            z = max(z_borde - caida, z_terreno(x, y)) - 0.04
        else:
            z = max(z_terreno(x, y), 0.2)
    return (x, y, z), p

def rot_facing_road(s_m, side):
    p = frame(s_m)
    return math.atan2(-side * p['ny'], -side * p['nx']) - math.pi / 2

def rot_across(s_m):
    p = frame(s_m)
    return math.atan2(p['ny'], p['nx'])

def log(msg):
    print('[integrar]', msg)

errores = []
def safe(nombre, fn):
    try:
        fn()
        log('OK ' + nombre)
    except Exception as e:
        import traceback
        errores.append((nombre, str(e)))
        log('ERROR %s: %s' % (nombre, e))
        traceback.print_exc()

# ============ BIBLIOTECA ============
lib = {}
VEG_EXTRA = []   # variantes de arbol extra (vegetacion_kit_v2)

def build_library():
    ck = M['carrera_kit']; vk = M['vegetacion_kit']; pk = M['puerto_kit']
    cv = M['edificios_civicos']
    lib['portico'] = ck.build_portico_meta(LIB, ancho=20)
    lib['tribuna'] = ck.build_tribuna(LIB, largo=45, filas=12)
    lib['pantalla'] = ck.build_pantalla(LIB)
    lib['boxes'] = ck.build_boxes(LIB, n=12)
    lib['muro'] = ck.build_muro_valla(LIB, largo=10)
    lib['valla_allinol'] = ck.build_valla_publicitaria(LIB, largo=8, texto='ALLINOL')
    lib['valla_wgp'] = ck.build_valla_publicitaria(LIB, largo=8, texto='MONDIALE GP')
    lib['paca'] = ck.build_paca(LIB)
    lib['palmera'] = vk.build_palmera(LIB, alto=8)
    lib['palmera2'] = vk.build_palmera(LIB, alto=6.5, seed=3)
    lib['cipres'] = vk.build_cipres(LIB, alto=10)
    lib['pino'] = vk.build_pino(LIB, alto=12)
    lib['pino2'] = vk.build_pino(LIB, alto=9, seed=5)
    lib['adelfa'] = vk.build_adelfa(LIB)
    for _o in [lib['adelfa']] + list(lib['adelfa'].children_recursive):
        if _o.type == 'MESH':   # su esfera tocaba el suelo en un punto: parecia flotar
            for _v in _o.data.vertices:
                _v.co.z -= 0.35
    lib['jardinera'] = vk.build_jardinera(LIB, largo=6)
    lib['roca'] = vk.build_roca(LIB, tam=3)
    lib['roca2'] = vk.build_roca(LIB, tam=5, seed=9)
    # RONDA 12: variedad de formas (vegetacion_kit_v2): mas variantes por familia
    if hasattr(vk, 'build_encina'):
        for k_, (al_, sd_) in enumerate(((13, 11), (10, 12), (14, 13), (8, 14))):
            lib['pino_v%d' % k_] = vk.build_pino(LIB, alto=al_, seed=sd_)
            VEG_EXTRA.append('pino_v%d' % k_)
        for k_, sd_ in enumerate((21, 22)):
            lib['cipres_v%d' % k_] = vk.build_cipres(LIB, alto=9 + 2 * k_, seed=sd_)
            VEG_EXTRA.append('cipres_v%d' % k_)
        for k_, sd_ in enumerate((31, 32, 33)):
            lib['palmera_v%d' % k_] = vk.build_palmera(LIB, alto=7 + 3 * k_, seed=sd_)
        for k_, sd_ in enumerate((41, 42)):
            lib['adelfa_v%d' % k_] = vk.build_adelfa(LIB, seed=sd_)
        for k_, (al_, sd_) in enumerate(((9, 51), (11, 52))):
            lib['encina_v%d' % k_] = vk.build_encina(LIB, alto=al_, seed=sd_)
            VEG_EXTRA.append('encina_v%d' % k_)
        for k_, sd_ in enumerate((61, 62)):
            lib['olivo_v%d' % k_] = vk.build_olivo(LIB, alto=5 + k_, seed=sd_)
            VEG_EXTRA.append('olivo_v%d' % k_)
        lib['platano'] = vk.build_platano(LIB, alto=14, seed=71)
        lib['platano2'] = vk.build_platano(LIB, alto=11, seed=72)
        for k_, sd_ in enumerate((81, 82, 83)):
            lib['arbusto_v%d' % k_] = vk.build_arbusto(LIB, tam=1.4 + 0.3 * k_, seed=sd_)
            VEG_EXTRA.append('arbusto_v%d' % k_)
        log('vegetacion v2: %d variantes extra' % (len(VEG_EXTRA) + 9))
    lib['yate'] = pk.build_yate(LIB, eslora=25)
    lib['yate2'] = pk.build_yate(LIB, eslora=18)
    lib['velero'] = pk.build_velero(LIB, eslora=12)
    lib['pantalan'] = pk.build_pantalan(LIB, largo=40)
    lib['hotel'] = cv.build_hotel(LIB)
    lib['ayuntamiento'] = cv.build_ayuntamiento(LIB)
    lib['campanile'] = cv.build_campanile(LIB)
safe('biblioteca', build_library)

# ============ META / PUERTO ============
def zona_meta():
    clone(lib['portico'], pos_side(6, 0, 0)[0][:2] + (frame(6)['z'],), rot_across(6))
    # (los boxes los pone zona_pit)
    # hotel detras del complejo de boxes
    (p, _) = pos_side(120, -1, 96)
    clone(lib['hotel'], p, rot_facing_road(120, -1))
    # tribunas lado mar + una interior
    for s_m in (40, 100, L - 60):
        for off in (16, 26, 36):  # nunca dentro del mar
            (p, _) = pos_side(s_m, 1, off)
            if z_terreno(p[0], p[1]) > 0.6:
                clone(lib['tribuna'], p, rot_facing_road(s_m, 1))
                break
        else:
            log('tribuna en s=%.0f omitida: solo hay mar' % s_m)
    for side, off in ((-1, 15), (-1, 25), (-1, 35), (1, 15), (1, 25)):
        (p, _) = pos_side(L - 260, side, off)
        if z_terreno(p[0], p[1]) > 0.6:  # nunca dentro del mar
            clone(lib['tribuna'], p, rot_facing_road(L - 260, side))
            break
    else:
        log('tribuna interior omitida: solo hay mar')
    # pantallas gigantes en la tribuna del mar
    for s_m in (70, L - 30):
        for off in (30, 42):
            (p, _) = pos_side(s_m, 1, off)
            if z_terreno(p[0], p[1]) > 0.6:
                clone(lib['pantalla'], p, rot_facing_road(s_m, 1))
                break
        else:
            log('pantalla en s=%.0f omitida: solo hay mar' % s_m)
    # muro+valla a ambos lados de la recta
    s_m = L - 150
    while s_m < L + 175:
        for side in ((1,) if M.get('pit_kit') else (1, -1)):
            (p, _) = pos_side(s_m, side, 2.2)
            clone(lib['muro'], p, rot_across(s_m) + math.pi / 2, pitch=pendiente(s_m))
        s_m += 10
    # palmeras
    for k in range(10):
        s_m = (L - 140 + k * 33) % L
        # nunca dentro de una tribuna (45 m de largo) ni de una pantalla
        if any(min(abs(s_m - s_t), L - abs(s_m - s_t)) < 30 for s_t in (40, 100, L - 60, 70, L - 30)):
            continue
        (p, _) = pos_side(s_m, 1, 9 if k % 2 else 8)
        clone(lib['palmera' if k % 2 else 'palmera2'], p, rnd.uniform(0, 6.28))
safe('zona_meta', zona_meta)

# ============ COMPLEJO DE BOXES (ronda 12): 20 boxes con tribuna encima ============
PIT_INFO = {}

def zona_pit():
    pk = M.get('pit_kit')
    PIT = G.get('pit_lane') or []
    if pk is None or not PIT:
        log('pit_kit no disponible: se mantienen los boxes antiguos')
        (p, _) = pos_side(100, -1, 22)
        clone(lib['boxes'], p, rot_facing_road(100, -1))
        return
    N_BOX, A_BOX = 20, 6.0
    # tramo de pit lane a ancho completo (u en 0.16..0.84 de sus 360 m)
    pit_in_s = L - 190.0
    k0, k1 = int(0.18 * (len(PIT) - 1)), int(0.82 * (len(PIT) - 1))
    s_a = (pit_in_s + 3.0 * k0) % L
    s_b = (pit_in_s + 3.0 * k1) % L
    largo_disp = (s_b - s_a) % L
    s_c = (s_a + min(largo_disp / 2.0, (largo_disp + 0.0) / 2.0)) % L
    largo = N_BOX * A_BOX
    if largo > largo_disp - 6:
        log('pit: el pit lane a ancho completo mide %.0f m, los boxes %.0f m' % (largo_disp, largo))
    q = frame(s_c)
    w_pit = max(pp['w'] for pp in PIT)
    # origen del edificio: borde exterior del pit lane + 1.6 m de acera + media
    # profundidad del edificio (su fachada esta en +6.5 local)
    d_front = 13.5 + w_pit / 2.0 + 1.6 + 6.5
    x = q['x'] - q['nx'] * d_front
    y = q['y'] - q['ny'] * d_front
    z = min(z_terreno(x + dx * q['ny'], y - dx * q['nx']) for dx in (-largo / 2, 0, largo / 2))
    z = max(z, q['z'] - 0.3)
    res = pk.build_boxes_tribuna(LIB, n=N_BOX, ancho_box=A_BOX, seed=1)
    boxes_lib = res[0] if isinstance(res, tuple) else res
    rot = rot_facing_road(s_c, -1)
    boxes = clone(boxes_lib, (x, y, z), rot)
    boxes.name = 'PIT_boxes'
    bpy.context.view_layer.update()
    # plazas de los garajes -> marcadores para exportar_ac (AC_PIT_n)
    plazas = pk.plazas_boxes(N_BOX, A_BOX)
    for j, pl in enumerate(plazas[:N_BOX]):
        lx, ly, lr = pl[0], pl[1], pl[2]
        w = boxes.matrix_world @ Vector((lx, ly, 0.0))
        e = bpy.data.objects.new('PIT_plaza_%02d' % j, None)
        e.empty_display_size = 0.5
        e.location = (w.x, w.y, w.z)
        # el coche mira HACIA el pit lane (+Y del edificio): sale del garaje de frente
        e.rotation_euler = (0.0, 0.0, rot)
        root_col.objects.link(e)
    # el terreno bajo el edificio queda plano: caja de terreno en preparar (pit)
    # muro de boxes entre el pit lane y la pista (sustituye al muro blanco de ese lado)
    n_muro = 0
    muros_lib = [pk.build_muro_boxes(LIB, largo=12.0, seed=k) for k in range(3)]
    s_m = s_a
    while s_m < s_a + largo_disp - 6:
        qq = frame(s_m % L)
        d_muro = 13.5 - w_pit / 2.0 - 0.7
        mx = qq['x'] - qq['nx'] * d_muro
        my = qq['y'] - qq['ny'] * d_muro
        m = clone(muros_lib[n_muro % 3], (mx, my, qq['z'] - 0.05),
                  rot_across(s_m % L) + math.pi / 2, pitch=pendiente(s_m % L))
        m.name = 'PIT_muro'
        n_muro += 1
        s_m += 12.0
    # torres de control en los extremos del edificio, detras
    torre = pk.build_torre_control(LIB, alto=16.0, seed=2)
    for ds in (-largo / 2 - 9.0, largo / 2 + 9.0):
        qt = frame((s_c + ds) % L)
        d_t = d_front + 14.0
        tx, ty = qt['x'] - qt['nx'] * d_t, qt['y'] - qt['ny'] * d_t
        t = clone(torre, (tx, ty, max(z_terreno(tx, ty), 0.3)), rot_facing_road((s_c + ds) % L, -1))
        t.name = 'PIT_torre'
        _zocalo_global(t, z_terreno(tx, ty) - 1.0)
    # pasarela sobre la pista un poco despues del portico de meta
    s_p = 96.0
    qp = frame(s_p)
    luz = qp['w'] + 9.0
    pas = pk.build_pasarela(LIB, luz=luz, alto=7.0, seed=3)
    pz = clone(pas, (qp['x'], qp['y'], qp['z'] - 0.05), rot_across(s_p))
    pz.name = 'PIT_pasarela'
    # marcas pintadas del pit lane (pit_kit v2): X a lo largo del pit lane, +Y hacia los garajes
    if hasattr(pk, 'build_marcas_pit_lane'):
        try:
            mk = pk.build_marcas_pit_lane(LIB, largo=largo_disp - 6.0, ancho_pit=w_pit, n=N_BOX, ancho_box=A_BOX, seed=0)
            qm = frame(s_c)
            tm = tangent(s_c)
            mkc = clone(mk, (qm['x'] - qm['nx'] * 13.5, qm['y'] - qm['ny'] * 13.5, qm['z'] + 0.03), math.atan2(-tm[1], -tm[0]))
            mkc.name = 'PIT_marcas'
            log('pit: marcas pintadas del pit lane colocadas')
        except Exception as e:
            log('pit: marcas del pit lane fallaron: %s' % e)
    PIT_INFO.update({'s_c': s_c, 'largo': largo, 'x': x, 'y': y, 'z': z, 'rot': rot})
    log('complejo de boxes: %d boxes de %.0f m centrados en s=%.0f, %d tramos de muro, 2 torres, pasarela en s=%.0f'
        % (N_BOX, A_BOX, s_c, n_muro, s_p))
safe('zona_pit', zona_pit)

def zona_puerto():
    p0 = frame(60)
    # centro de la marina: 190 m a la izquierda de la recta, pegada a la costa
    cxp = p0['x'] + p0['nx'] * 190
    cyp = p0['y'] + p0['ny'] * 190
    pk = M['puerto_kit']
    dique = pk.build_dique(LIB, radio=145, arco_grados=200)
    clone(dique, (cxp, cyp, 0.0), rot_facing_road(60, 1))
    clone(lib['pantalan'], (cxp + 40, cyp - 30, 0.0), 0.6)
    clone(lib['pantalan'], (cxp - 55, cyp + 25, 0.0), -0.4)
    faro = pk.build_faro(LIB)
    clone(faro, (cxp + p0['nx'] * 120, cyp + p0['ny'] * 120, 0.0), 0.0)
    # marina LLENA como en la pelicula: pantalanes radiales (radios de llanta)
    # con hileras de barcos amarrados a ambos lados
    barcos = 0
    for k in range(4):
        ang = rot_facing_road(60, 1) + math.pi + (k - 1.5) * 0.55
        dx_, dy_ = math.cos(ang), math.sin(ang)
        clone(lib['pantalan'], (cxp + dx_ * 55, cyp + dy_ * 55, 0.0), ang)
        clone(lib['pantalan'], (cxp + dx_ * 95, cyp + dy_ * 95, 0.0), ang)
        for m_ in range(5):
            d_ = 38 + m_ * 16
            for lado_ in (1, -1):
                bx = cxp + dx_ * d_ - dy_ * lado_ * 7.5
                by = cyp + dy_ * d_ + dx_ * lado_ * 7.5
                if z_terreno(bx, by) < -1.0:
                    tipo = ('yate2', 'velero', 'yate')[barcos % 3]
                    clone(lib[tipo], (bx, by, 0.0), ang + math.pi / 2
                          + rnd.uniform(-0.06, 0.06))
                    barcos += 1
    # veleros navegando en mar abierto
    for k in range(7):
        x = cxp + rnd.uniform(-420, 160)
        y = cyp + rnd.uniform(-380, 120)
        if z_terreno(x, y) < -2.5:
            clone(lib['velero'], (x, y, 0.0), rnd.uniform(0, 6.28))
            barcos += 1
    log('marina y bahia: %d barcos' % barcos)
safe('zona_puerto', zona_puerto)

# ============ DIRIGIBLE SOBRE LA BAHIA ============
def zona_dirigible():
    import bmesh as bm_
    me = bpy.data.meshes.new('DIRIGIBLE_globo')
    bb = bm_.new()
    bm_.ops.create_uvsphere(bb, u_segments=16, v_segments=10, radius=1.0)
    bm_.ops.scale(bb, vec=(24.0, 8.5, 8.5), verts=bb.verts)
    bb.to_mesh(me)
    bb.free()
    m_bl = bpy.data.materials.get('MAT_dirigible') or bpy.data.materials.new('MAT_dirigible')
    m_bl.use_nodes = True
    m_bl.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.92, 0.90, 0.86, 1)
    me.materials.append(m_bl)
    ob = bpy.data.objects.new('DIRIGIBLE', me)
    root_col.objects.link(ob)
    p0 = frame(30)
    ob.location = (p0['x'] + p0['nx'] * 380, p0['y'] + p0['ny'] * 380, 230.0)
    ob.rotation_euler = (0, 0, 0.7)
    # gondola y aletas sencillas
    me2 = bpy.data.meshes.new('DIRIGIBLE_gondola')
    me2.from_pydata([(-3, -1, -1.2), (3, -1, -1.2), (3, 1, -1.2), (-3, 1, -1.2),
                     (-3, -1, 0), (3, -1, 0), (3, 1, 0), (-3, 1, 0)], [],
                    [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
                     (1, 2, 6, 5), (0, 3, 7, 4)])
    m_g = bpy.data.materials.get('MAT_dirigible_rojo') or bpy.data.materials.new('MAT_dirigible_rojo')
    m_g.use_nodes = True
    m_g.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.75, 0.08, 0.06, 1)
    me2.materials.append(m_g)
    ob2 = bpy.data.objects.new('DIRIGIBLE_gondola', me2)
    ob2.parent = ob
    ob2.location = (0, 0, -8.2)
    root_col.objects.link(ob2)
safe('zona_dirigible', zona_dirigible)

# ============ YATES VIP (ronda 14): los ricos ven la carrera desde el mar ============
def zona_yates():
    yk = M.get('yates_kit')
    if yk is None:
        log('yates_kit no disponible')
        return
    n_y = 0
    def _agua(x, y):
        return z_terreno(x, y) < -1.8
    def _amarrar(s_m, side, off, tipo, seed):
        nonlocal n_y
        q = frame(s_m)
        t = tangent(s_m)
        x = q['x'] + side * q['nx'] * (q['w'] / 2 + off)
        y = q['y'] + side * q['ny'] * (q['w'] / 2 + off)
        if not _agua(x, y):
            return None
        # proa a lo largo de la pista y ESTRIBOR (+Y) hacia la carrera
        rot = math.atan2(-t[1], -t[0]) if side > 0 else math.atan2(t[1], t[0])
        if tipo == 'super':
            ob_ = yk.build_superyate(LIB, eslora=70.0, seed=seed)
        elif tipo == 'lancha':
            ob_ = yk.build_lancha(LIB, eslora=9.0, seed=seed)
        else:
            ob_ = yk.build_yate(LIB, eslora=32.0 if seed % 2 else 26.0, seed=seed)
        y_ = clone(ob_, (x, y, 0.0), rot)
        y_.name = 'YATE_' + tipo
        n_y += 1
        return y_
    # marina VIP frente a la recta de meta (lado del mar): pantalan + yates en fila
    s_a = L - 130.0
    for k, s_m in enumerate(range(int(s_a), int(s_a) + 120, 40)):
        _amarrar(s_m, 1, 62.0, 'yate', k)
    _amarrar(s_a + 60, 1, 118.0, 'super', 5)
    for k, s_m in enumerate(range(int(s_a) - 30, int(s_a) + 150, 45)):
        _amarrar(s_m, 1, 92.0, 'lancha', 10 + k)
    if hasattr(yk, 'build_pantalan_vip'):
        q = frame(s_a + 60)
        t = tangent(s_a + 60)
        px, py = q['x'] + q['nx'] * (q['w'] / 2 + 52.0) - t[0] * 45.0, q['y'] + q['ny'] * (q['w'] / 2 + 52.0) - t[1] * 45.0
        if _agua(px, py):
            pv = yk.build_pantalan_vip(LIB, largo=100.0, seed=1)
            p_ = clone(pv, (px, py, 0.0), math.atan2(t[1], t[0]))
            p_.name = 'YATE_pantalan'
    # y dos yates frente al paseo-mirador (sector casino) y el retorno costero
    for (s_m, off, sd) in ((3060, 70.0, 1), (3120, 110.0, 1), (4700, 80.0, 1), (4780, 120.0, 1)):
        _amarrar(s_m, sd, off, 'yate', int(s_m) % 4)
    log('yates VIP: %d embarcaciones viendo la carrera' % n_y)
safe('zona_yates', zona_yates)

# ============ ACANTILADO 01-03 ============
def zona_acantilado():
    # (losas y rocas sueltas fuera: el muro de contencion ya da el caracter;
    # las rocas solo tienen sentido en la montana y en la costa del penon)
    pass
safe('zona_acantilado', zona_acantilado)

# ============ PUEBLO ============
def zona_pueblo():
    ck = M['casas_kit']
    _VAR = ((3, 9.0, 11), (4, 10.0, 12), (5, 9.5, 11), (4, 11.5, 12), (3, 12.0, 11),
            (5, 10.5, 12), (6, 10.0, 12), (4, 9.0, 10), (3, 10.5, 12), (5, 12.0, 12))
    casas_var = [ck.build_casa(LIB, plantas=pl, ancho=an, fondo=fo, seed=300 + k_)
                 for k_, (pl, an, fo) in enumerate(_VAR)]
    anchos_var = [v_[1] for v_ in _VAR]
    puestos = []
    mat_zoc = bpy.data.materials.get('MAT_zocalo_piedra')
    if mat_zoc is None:
        mat_zoc = bpy.data.materials.new('MAT_zocalo_piedra')
        mat_zoc.use_nodes = True
        bs = mat_zoc.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (0.55, 0.50, 0.40, 1)
        bs.inputs['Roughness'].default_value = 0.95
    def zocalo(casa, z_fondo):
        """Zocalo de piedra bajo la manzana: en ladera ninguna esquina flota."""
        bpy.context.view_layer.update()
        inv = casa.matrix_world.inverted()
        xs, ys = [], []
        for ob in [casa] + list(casa.children_recursive):
            if ob.type != 'MESH':
                continue
            for c in ob.bound_box:
                l = inv @ (ob.matrix_world @ Vector(c))
                xs.append(l.x)
                ys.append(l.y)
        if not xs:
            return
        x0, x1 = min(xs) + 0.2, max(xs) - 0.2
        y0, y1 = min(ys) + 0.2, max(ys) - 0.2
        zb = min(z_fondo - casa.location.z, -0.5)
        vs = [(x0, y0, zb), (x1, y0, zb), (x1, y1, zb), (x0, y1, zb),
              (x0, y0, 0.85), (x1, y0, 0.85), (x1, y1, 0.85), (x0, y1, 0.85)]
        fs = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0)]
        me = bpy.data.meshes.new('CASAS_zocalo')
        me.from_pydata(vs, [], fs)
        me.materials.append(mat_zoc)
        zo = bpy.data.objects.new('CASAS_zocalo', me)
        root_col.objects.link(zo)
        zo.parent = casa
    def fila(s0, s1, paso_s, side, offset):
        s_m = s0
        k = 0
        while s_m < s1:
            # una 'manzana' = 4-5 casas ESCALONADAS: cada una a su altura y
            # siguiendo la curva de la calle (antes era una hilera rigida de 50 m)
            n_c = 4 + (k + int(s_m)) % 2
            s_c = s_m - 22.0
            for j in range(n_c):
                v = (k * 3 + j * 7 + int(s_m)) % len(casas_var)
                an = anchos_var[v]
                pa, pb = frame(s_c - 5), frame(s_c + 5)
                kap = math.atan2(pa['ny'] * pb['nx'] - pa['nx'] * pb['ny'],
                                 pa['nx'] * pb['nx'] + pa['ny'] * pb['ny']) / 10.0
                (p, fr) = pos_side(s_c, side, offset)
                fac = max(0.4, 1.0 + side * kap * (fr['w'] / 2 + offset))   # kap<0 = curva a izquierdas
                s_c += (an / 2.0) / fac
                (p, fr) = pos_side(s_c, side, offset)
                t = tangent(s_c)
                def zt_(dx, dy):
                    return z_terreno(p[0] + dx * t[0] + side * dy * fr['nx'],
                                     p[1] + dx * t[1] + side * dy * fr['ny'])
                z_f = [zt_(-an / 2, 0.0), zt_(an / 2, 0.0), zt_(0.0, 0.0)]
                z_b = [zt_(-an / 2, 6.5), zt_(an / 2, 6.5)]   # trasera real (origen de la casa = centro de la base)
                todos = z_f + z_b
                s_c += (an / 2.0) / fac
                if min(todos) < 0.4 or max(todos) - min(todos) > 6.5:
                    continue
                z_casa = max(z_f) - 0.45      # la fachada nunca queda enterrada
                if max(z_b) - z_casa > 2.2:   # ni la trasera bajo tierra (max 2.2 m empotrada)
                    continue
                casa = clone(casas_var[v], (p[0], p[1], z_casa), rot_facing_road(s_c - (an / 2.0) / fac, side))
                casa.name = 'CASAS_casa'
                if z_casa - min(todos) > 0.2:
                    zocalo(casa, min(todos) - 1.0)
            puestos.append(s_m)
            s_m += paso_s
            k += 1
    # RONDA 14: pueblo DENSO (manzanas casi seguidas, 56 m) sobre las TERRAZAS que
    # preparar_geometria talla en cada sector (offsets 16 / 36 / 56 desde el borde)
    fila(660, 1080, 56, -1, 17)       # subida del pueblo, lado interior
    fila(820, 1090, 56, 1, 17)        # lado mar a partir del final del acantilado
    fila(1280, 1530, 56, -1, 17)
    fila(1300, 1500, 56, 1, 17)
    fila(2520, 2730, 56, -1, 17)
    fila(640, 1100, 56, -1, 37)
    fila(700, 1060, 56, -1, 57)
    fila(1270, 1540, 56, -1, 37)
    fila(1280, 1530, 56, -1, 57)
    fila(2500, 2750, 56, -1, 37)
    fila(870, 1080, 56, 1, 37)
    fila(3190, 3450, 56, -1, 17)
    fila(3190, 3450, 56, 1, 17)
    fila(3200, 3440, 56, -1, 37)
    fila(3200, 3440, 56, 1, 37)
    # civicos
    (p, _) = pos_side(1160, -1, 30)
    clone(lib['ayuntamiento'], p, rot_facing_road(1160, -1))
    (p, _) = pos_side(700, -1, 34)
    clone(lib['campanile'], p, rot_facing_road(700, -1))
    # cipreses sueltos entre casas
    for k in range(14):
        s_m = 660 + k * 62
        (p, _) = pos_side(s_m, 1 if k % 3 else -1, 11)
        clone(lib['cipres'], p, rnd.uniform(0, 6.28))
safe('zona_pueblo', zona_pueblo)

# ============ LADERA DE TIERRA ============
def zona_tierra():
    s_m = 1570
    k = 0
    while s_m < 2370:
        tipo = ('pino', 'cipres', 'pino2')[k % 3]
        side = 1 if k % 2 else -1
        (p, _) = pos_side(s_m, side, 15 + (k % 3) * 6)
        clone(lib[tipo], p, rnd.uniform(0, 6.28))
        s_m += 52
        k += 1
    # pacas de paja en el exterior de las curvas de tierra
    for n in (15, 16, 17, 18, 19, 20, 22, 24, 25):
        s_c = CURVAS[n]['s_idx'] * paso
        p = frame(s_c)
        outside = -1 if p['lat'] > 0 else 1
        for ds in (-7, 0, 7):
            (pp, _) = pos_side(s_c + ds, outside, 2.5)
            clone(lib['paca'], pp, rot_facing_road(s_c + ds, outside))
    # rocas de cima
    for k in range(10):
        s_m = 1700 + k * 68
        (p, _) = pos_side(s_m, 1 if k % 2 else -1, 26 + (k % 4) * 5)
        clone(lib['roca' if k % 3 else 'roca2'], p, rnd.uniform(0, 6.28))
safe('zona_tierra', zona_tierra)

# ============ RECTA RAPIDA Y VALLAS ============
def zona_vallas():
    # vallas publicitarias en la bajada 30->31 y en la diagonal
    k = 0
    s_m = 2760
    while s_m < 3180:
        side = 1 if k % 2 else -1
        if any(mm['side'] == side and mm['s0'] - 8 <= s_m <= mm['s1'] + 8 for mm in (G.get('miradores') or [])):
            s_m += 70
            k += 1
            continue
        (p, _) = pos_side(s_m, side, 3.0)
        clone(lib['valla_allinol' if k % 3 else 'valla_wgp'], p,
              rot_across(s_m) + side * math.pi / 2, pitch=side * pendiente(s_m))  # cara hacia la pista
        s_m += 70
        k += 1
    s_m = 260
    while s_m < 580:
        (p, _) = pos_side(s_m, -1, 3.0)
        clone(lib['valla_allinol' if k % 2 else 'valla_wgp'], p,
              rot_across(s_m) - math.pi / 2, pitch=-pendiente(s_m))  # cara hacia la pista
        s_m += 84
        k += 1
    # muro+valla en el sector casino (31-38, lado exterior)
    s_m = 3200
    while s_m < 3200:   # RONDA 10: en el sector del casino va guardarrail de acero (construir_pista)
        p = frame(s_m)
        outside = -1 if p['lat'] > 0 else 1
        (pp, _) = pos_side(s_m, outside, 2.0)
        clone(lib['muro'], pp, rot_across(s_m) + math.pi / 2, pitch=pendiente(s_m))  # sigue la cuesta
        s_m += 10
safe('zona_vallas', zona_vallas)

# ============ CASINO Y PENON ============
CASINO_INFO = {}

# ============ ROCAS-PUEBLO (ronda 12): penon_pueblo con carretera y solares ============
def _contorno_libre(pts, margen):
    """Aleja los puntos del contorno de cualquier tramo de pista (borde + margen)."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for (x, y) in pts:
        for _ in range(60):
            j = min(range(0, N, 2), key=lambda j: (x - S[j]['x']) ** 2 + (y - S[j]['y']) ** 2)
            d = math.hypot(x - S[j]['x'], y - S[j]['y']) - S[j]['w'] / 2
            if d >= margen:
                break
            dx, dy = cx - x, cy - y
            l_ = math.hypot(dx, dy) or 1.0
            x += dx / l_ * 2.0
            y += dy / l_ * 2.0
        out.append((x, y))
    return out


def _limpiar_bajo_roca(roca, prefijos=('VEG_', 'OLI_', 'CALLE_', 'CASAS_',
                                       'CARRERA_valla', 'CARRERA_paca', 'PUEBLO_'),
                       margen=0.5):
    """Borra los objetos sueltos que quedarian dentro o debajo de una roca:
    rayo vertical desde arriba; si la roca queda por encima del objeto, fuera."""
    bpy.context.view_layer.update()
    inv = roca.matrix_world.inverted()
    borrados = 0
    for ob in list(root_col.objects):
        try:
            if ob.parent is not None or not ob.name.startswith(prefijos):
                continue
        except ReferenceError:
            continue
        w = ob.matrix_world.translation
        a = inv @ Vector((w.x, w.y, w.z + 400.0))
        b = inv @ Vector((w.x, w.y, w.z - 60.0))
        d = b - a
        hit, loc, nrm, fi = roca.ray_cast(a, d.normalized(), distance=d.length)
        if hit and (roca.matrix_world @ loc).z > w.z + margen:
            for ch in list(ob.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(ob, do_unlink=True)
            borrados += 1
    return borrados

def _construir_roca_pueblo(nombre, contorno, altura, z_base, entrada_xy, seed, seed_casas, con_palazzo, **params):
    pp = M['penon_pueblo']
    n_terr = params.pop('n_terrazas', 4)
    flares = params.pop('flares', (params.pop('flare', 0.3),))
    cxg = sum(p_[0] for p_ in contorno) / len(contorno)
    cyg = sum(p_[1] for p_ in contorno) / len(contorno)
    r_max = max(math.hypot(p_[0] - cxg, p_[1] - cyg) for p_ in contorno)
    for k_f, flare in enumerate(flares):
        res = pp.build_desde_contorno(LIB, contorno, altura=altura, z_base=z_base,
                                      n_terrazas=n_terr, seed=seed, entrada_xy=entrada_xy, flare=flare, **params)
        if isinstance(res, tuple):
            raiz_lib, info = res
        else:
            raiz_lib = res
            info = json.loads(raiz_lib['casas']) if 'casas' in raiz_lib else {}
        # la falda ensanchada no puede pisar la pista (ni sus bordes): si lo hace, menos falda
        # (el rayo se lanza contra el CLON en escena: los objetos de LIB no se evaluan)
        r = clone(raiz_lib, (0.0, 0.0, 0.0), 0.0)
        r.name = nombre
        bpy.context.view_layer.update()
        roca_lib = next((o for o in [r] + r.children_recursive if o.type == 'MESH' and 'roca' in o.name.lower()), None)
        pisa = 0
        if roca_lib is not None:
            inv_l = roca_lib.matrix_world.inverted()
            for i in range(0, N, 2):
                q = S[i]
                if math.hypot(q['x'] - cxg, q['y'] - cyg) > r_max + 70:
                    continue
                for lt in (-(q['w'] / 2 + 2.0), 0.0, q['w'] / 2 + 2.0):
                    a2 = inv_l @ Vector((q['x'] + q['nx'] * lt, q['y'] + q['ny'] * lt, q['z'] + 400.0))
                    b2 = inv_l @ Vector((q['x'] + q['nx'] * lt, q['y'] + q['ny'] * lt, q['z'] - 2.5))
                    d2 = b2 - a2
                    if roca_lib.ray_cast(a2, d2.normalized(), distance=d2.length)[0]:
                        pisa += 1
        if pisa == 0 or k_f == len(flares) - 1:
            if pisa:
                log('%s: AVISO la roca pisa %d muestras de pista aun con falda %.2f' % (nombre, pisa, flare))
            break
        log('%s: con falda %.2f la roca pisaba %d muestras de pista -> menos falda' % (nombre, flare, pisa))
        for raiz_ in (r, raiz_lib):
            for ch in list(raiz_.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(raiz_, do_unlink=True)
    bpy.context.view_layer.update()
    roca = next((o for o in [r] + r.children_recursive if o.type == 'MESH' and 'roca' in o.name.lower()), None)
    if roca is None:
        roca = max((o for o in [r] + r.children_recursive if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    nb = _limpiar_bajo_roca(roca)
    # casas en los solares de las terrazas, mirando a la carretera (la mitad
    # trasera queda dentro de la roca); nunca mas altas que el paredon de detras
    ck_ = M['casas_kit']
    variantes = []
    for k, (pl, an, fo) in enumerate(((3, 9, 9), (4, 10, 9), (5, 9, 9), (4, 11, 10), (3, 8, 8), (5, 11, 10), (4, 12, 10), (2, 8, 8),
                                      (3, 8, 6), (4, 9, 6), (3, 7, 6), (2, 8, 6), (4, 10, 7), (3, 9, 7), (5, 8, 6),
                                      (3, 7, 5), (2, 6, 5), (4, 8, 5), (3, 8, 5))):
        variantes.append((an, fo, pl * 3.3 + 2.5, ck_.build_casa(LIB, plantas=pl, ancho=an, fondo=fo, seed=seed_casas + k)))
    n_c = 0
    for k, lot in enumerate(info.get('plazas_casas', [])):
        an_max = float(lot.get('ancho_max', 10.0))
        fo_max = float(lot.get('fondo_max', 10.0))
        al_max = float(lot.get('alto_max', 99.0))
        cands = [v for v in variantes if v[0] <= an_max + 0.3 and v[1] <= fo_max + 0.3 and v[2] <= al_max]
        if not cands:
            continue
        an, fo, _al, casa_lib = cands[(k * 7 + seed_casas) % len(cands)]
        # (x, y) del solar = centro de la linea de fachada; la casa ENTERA queda sobre la
        # repisa: su centro va fondo/2 hacia dentro (contra la fachada, +Y girada rot_z)
        fx_, fy_ = -math.sin(float(lot['rot_z'])), math.cos(float(lot['rot_z']))
        cx_c = float(lot['x']) - fx_ * (fo / 2.0 + 0.15)
        cy_c = float(lot['y']) - fy_ * (fo / 2.0 + 0.15)
        casa = clone(casa_lib, (cx_c, cy_c, float(lot['z']) + 0.02), float(lot['rot_z']))
        casa.name = 'PENON_casa_roca'
        _zocalo_global(casa, float(lot['z']) - 2.5)
        n_c += 1
    # arboles y matas en los solares que quedan libres (junto al parapeto de la carretera)
    tipos_v = [t_ for t_ in ('cipres', 'pino', 'olivo', 'palmera', 'adelfa', 'cipres_v0', 'pino_v1', 'olivo_v1', 'palmera_v1', 'arbusto_v0') if t_ in lib]
    n_v = 0
    for k, lot in enumerate(info.get('plazas_libres', [])):
        if not tipos_v:
            break
        for j_ in range(2):
            t_ = tipos_v[(k * 3 + j_ * 5 + seed_casas) % len(tipos_v)]
            fx, fy = -math.sin(float(lot['rot_z'])), math.cos(float(lot['rot_z']))
            dx_ = (j_ - 0.5) * 4.0
            v_ = clone(lib[t_], (float(lot['x']) + fy * dx_, float(lot['y']) - fx * dx_, float(lot['z']) + 0.02), rnd.uniform(0, 6.28),
                       scale=rnd.uniform(0.8, 1.15))
            v_.name = 'VEG_penon'
            n_v += 1
    z_top = float(info.get('z_top', z_base + altura))
    ct = info.get('centro_top') or (sum(p[0] for p in contorno) / len(contorno), sum(p[1] for p in contorno) / len(contorno))
    r_top = float(info.get('r_top', 30.0))
    if con_palazzo:
        rot_p = rnd.uniform(0, 6.28)
        if r_top >= 18.0:
            pal = clone(lib['ayuntamiento'], (float(ct[0]), float(ct[1]), z_top - 0.3), rot_p, scale=0.85)
            pal.name = 'PENON_palazzo'
            cam = clone(lib['campanile'], (float(ct[0]) + math.cos(rot_p) * 17.0, float(ct[1]) + math.sin(rot_p) * 17.0, z_top - 0.3),
                        rot_p, scale=0.9)
            cam.name = 'PENON_campanile'
        else:
            cam = clone(lib['campanile'], (float(ct[0]), float(ct[1]), z_top - 0.3), rot_p, scale=0.9)
            cam.name = 'PENON_campanile'
            for k in range(3 if r_top >= 10.0 else 0):
                a_ = rot_p + 2.1 * k + 1.0
                d_ = max(6.0, r_top - 5.0)
                casa = clone(variantes[(k + 4) % len(variantes)][3],
                             (float(ct[0]) + math.cos(a_) * d_, float(ct[1]) + math.sin(a_) * d_, z_top - 0.28), a_ + math.pi / 2)
                casa.name = 'PENON_casa_roca'
                n_c += 1
    log('%s: %d casas en solares de terraza, %d arboles, plaza a z=%.0f, r_top %.0f m (%d objetos retirados de debajo)' % (nombre, n_c, n_v, z_top, r_top, nb))
    return r, roca, info



def _a_meseta(raiz, alto, fuerza=0.5):
    """Ensancha las cotas medias/altas del penon: paredes casi verticales y
    cima ancha (meseta), como la roca del casino de la pelicula."""
    bpy.context.view_layer.update()
    inv = raiz.matrix_world.inverted()
    hechos = set()
    for ob in [raiz] + list(raiz.children_recursive):
        if ob.type != 'MESH' or ob.data.name in hechos:
            continue
        hechos.add(ob.data.name)
        m = inv @ ob.matrix_world
        mi = m.inverted()
        for v in ob.data.vertices:
            q = m @ v.co
            t = max(0.0, min(0.9, q.z / alto))
            s_ = 1.0 + fuerza * 1.5 * t * t      # la cupula se estrecha ~t^2: esto lo compensa
            v.co = mi @ Vector((q.x * s_, q.y * s_, q.z))
        ob.data.update()

def zona_casino():
    # el penon con el casino va FUERA del circuito, mar adentro (como en la
    # pelicula): desde el lobulo 36-38, alejado de la pista
    cs = [CURVAS[n] for n in (36, 37, 38)]
    cxc = sum(c['x'] for c in cs) / len(cs)
    cyc = sum(c['y'] for c in cs) / len(cs)
    mx = sum(S[i]['x'] for i in range(0, N, 20)) / len(range(0, N, 20))
    my = sum(S[i]['y'] for i in range(0, N, 20)) / len(range(0, N, 20))
    dx, dy = cxc - mx, cyc - my
    dl = math.hypot(dx, dy) or 1.0
    pt = M.get('penon_cara') or M['penon_topolino']  # con cara de coche si existe
    if M.get('penon_pueblo') is not None:
        z_plaza = max(S[CURVAS[n]['s_idx']]['z'] for n in (36, 37, 38)) - 2.0
        cxc = cxc + dx / dl * 190.0
        cyc = cyc + dy / dl * 190.0
        ang0 = 0.5
        pts = []
        for k_ in range(64):
            a_ = 2 * math.pi * k_ / 64
            ex_, ey_ = 118.0 * math.cos(a_), 78.0 * math.sin(a_)
            pts.append((cxc + ex_ * math.cos(ang0) - ey_ * math.sin(ang0), cyc + ex_ * math.sin(ang0) + ey_ * math.cos(ang0)))
        pts = _contorno_libre(pts, 8.0)
        # entrada de la carretera del penon: el punto del contorno mas cercano a la
        # cresta (curva 37): ahi la pista esta a la cota de la base de la roca y el
        # espolon de empalme (zona_caminos) sale casi llano
        q37_ = S[CURVAS[36]['s_idx']]
        ent = min(pts, key=lambda p_: (p_[0] - q37_['x']) ** 2 + (p_[1] - q37_['y']) ** 2)
        # cota base = terreno mas alto del contorno (la carretera de la roca nunca
        # queda enterrada); la plaza del casino por encima de la cresta 36-38
        z_ter_c = [z_terreno(x_, y_) for (x_, y_) in pts]
        z_base_c = max(z_ter_c) + 0.3
        z_top_c = max(z_plaza + 12.2, z_base_c + 26.0)
        r_c, roca_c, info_c = _construir_roca_pueblo('PENON_cara', pts, altura=z_top_c - z_base_c, z_base=z_base_c,
                                                     entrada_xy=ent, seed=2, seed_casas=70, con_palazzo=False,
                                                     profundidad=z_base_c - min(z_ter_c) + 8.0, ancho_lote=12.5, ocupacion=0.7,
                                                     flares=(0.45, 0.3, 0.15), bulto_fuera=5.0, bulto_pared=1.5, ancho_repisa=16.5, ancho_carretera=6.0,
                                                     z_entrada=q37_['z'] + 0.1)
        log('casino: roca-pueblo base z=%.0f (terreno %.0f..%.0f) -> plaza z=%.0f' % (z_base_c, min(z_ter_c), max(z_ter_c), z_top_c))
        z_meseta = float(info_c.get('z_top', z_plaza + 2.2)) - 0.2
        hacia_meta = math.atan2(frame(0)['y'] - cyc, frame(0)['x'] - cxc)
        cas = M['casino'].build(LIB, seed=0)
        clone(cas, (cxc, cyc, max(z_meseta, 8.0)), hacia_meta - math.pi / 2, scale=0.9)
        CASINO_INFO.update({'cx': cxc, 'cy': cyc, 'roca': roca_c, 'z_plaza': z_plaza, 'z_meseta': z_meseta,
                            'entrada': info_c.get('entrada'), 'info': info_c})
        log('casino sobre penon_pueblo: plaza a z=%.0f' % z_meseta)
    else:
        # el casino va ARRIBA, a la altura de la plaza (cresta 36-38), sobre un
        # penon alto como en la pelicula; nunca por debajo de la carretera
        z_plaza = max(S[CURVAS[n]['s_idx']]['z'] for n in (36, 37, 38)) - 2.0
        HUNDIDO = -5.0  # los escalones inferiores quedan bajo tierra/agua
        penon = pt.build(LIB, largo=235, ancho=155, alto=z_plaza + 7.2, seed=2, con_vegetacion=False)
        _a_meseta(penon, z_plaza + 7.2)
        cx0, cy0 = cxc, cyc
        pen_clon = None
        for lejos in (150, 170, 190, 215, 240, 270, 300):
            cxc = cx0 + dx / dl * lejos
            cyc = cy0 + dy / dl * lejos
            pen_clon = clone(penon, (cxc, cyc, HUNDIDO), 0.5)
            bpy.context.view_layer.update()
            roca_c = max((o for o in [pen_clon] + pen_clon.children_recursive if o.type == 'MESH'),
                         key=lambda o: len(o.data.vertices))
            inv_c = roca_c.matrix_world.inverted()
            pisa = False
            for i in range(0, N, 2):
                q = S[i]
                if math.hypot(q['x'] - cxc, q['y'] - cyc) > 170:
                    continue
                # ni el eje ni los bordes (calzada + pianos + guardarrail + 6 m de respiro)
                for lt_ in (-(q['w'] / 2 + 6.0), 0.0, q['w'] / 2 + 6.0):
                    a_ = inv_c @ Vector((q['x'] + q['nx'] * lt_, q['y'] + q['ny'] * lt_, q['z'] + 400.0))
                    b_ = inv_c @ Vector((q['x'] + q['nx'] * lt_, q['y'] + q['ny'] * lt_, q['z'] - 3.0))
                    d_ = b_ - a_
                    if roca_c.ray_cast(a_, d_.normalized(), distance=d_.length)[0]:
                        pisa = True
                        break
                if pisa:
                    break
            if not pisa or lejos == 300:
                break
            for ch in list(pen_clon.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(pen_clon, do_unlink=True)
            pen_clon = None
        log('casino: penon de %.0f m de alto a %d m del lobulo 36-38 (plaza a %.0f m)'
            % (z_plaza + 7.2, lejos, z_plaza))
        # altura de la meseta del penon (bbox real de sus mallas)
        zmax = 0.0
        for ob in hierarchy(penon):
            if ob.type == 'MESH':
                for v in ob.bound_box:
                    w = ob.matrix_world @ Vector(v)
                    zmax = max(zmax, w.z)
        z_meseta = zmax + HUNDIDO - 2.2  # bbox local + hundimiento, bajo la copa
        hacia_meta = math.atan2(frame(0)['y'] - cyc, frame(0)['x'] - cxc)
        # el casino se encoge para caber DENTRO de la meseta (~72x46 m)
        cas = M['casino'].build(LIB, seed=0)
        clone(cas, (cxc, cyc, max(z_meseta, 8.0)), hacia_meta - math.pi / 2, scale=0.9)
        CASINO_INFO.update({'cx': cxc, 'cy': cyc, 'roca': roca_c, 'z_plaza': z_plaza,
                            'z_meseta': z_meseta})
    # el interior del lazo 31-41 (donde antes estaba la roca) pasa a ser
    # jardines estilo Montecarlo: setos, olivos, adelfas y palmeras
    gs = [CURVAS[n] for n in (33, 35, 39)]
    gx = sum(c['x'] for c in gs) / len(gs)
    gy = sum(c['y'] for c in gs) / len(gs)
    puestos = 0
    intentos = 0
    while puestos < 26 and intentos < 300:
        intentos += 1
        x = gx + rnd.uniform(-70, 70)
        y = gy + rnd.uniform(-70, 70)
        z = z_terreno(x, y)
        if z < 0.8:
            continue
        d2 = min((x - S[i]['x'])**2 + (y - S[i]['y'])**2 for i in range(0, N, 6))
        if d2 < 11**2:
            continue
        tipo = ('adelfa', 'palmera', 'cipres', 'adelfa', 'palmera2')[puestos % 5]
        if M.get('olivos') and puestos % 3 == 0:
            tipo = 'olivo' if 'olivo' in lib else tipo
        clone(lib[tipo], (x, y, z - 0.1), rnd.uniform(0, 6.28))
        puestos += 1
    log('jardines del casino: %d elementos' % puestos)
safe('zona_casino', zona_casino)

# ============ HORQUILLAS CON JARDINERAS ============
def zona_loews():
    """Horquilla Loews en la curva 38 (V del casino): rotonda + anuncios."""
    if not M['horquilla_loews']:
        return
    lw = G.get('loews')
    s_c = (lw.get('s_idx') if lw and lw.get('s_idx') is not None
           else CURVAS[38]['s_idx']) * paso
    p = frame(s_c)
    _pa, _pb = frame(s_c - 8), frame(s_c + 8)      # interior por GEOMETRIA (alli el peralte es 0)
    inside = 1 if (_pa['ny'] * _pb['nx'] - _pa['nx'] * _pb['ny']) < 0 else -1
    if lw:  # centro exacto de la horquilla remodelada
        cx_, cy_ = lw['x'], lw['y']
        RADIO = lw['radio_calzada'] - p['w'] / 2 - 0.5
    else:
        RADIO = 6.5
        d = p['w'] / 2 + RADIO + 0.3
        cx_ = p['x'] + inside * p['nx'] * d
        cy_ = p['y'] + inside * p['ny'] * d
    # RONDA 12: la isleta se dimensiona MIDIENDO. Radio disponible = distancia del
    # centro al borde interior del asfalto - 0.6 m de acera; el kit ocupa mas que
    # su parametro 'radio', asi que se mide y se escala si hace falta
    i_lw = int(round(s_c / paso)) % N
    d_disp = min(math.hypot(S[j % N]['x'] - cx_, S[j % N]['y'] - cy_) - S[j % N]['w'] / 2
                 for j in range(i_lw - 45, i_lw + 46)) - 0.6
    # RONDA 13: el kit es como SIEMPRE fue (radio 5+, rueda de flores completa); el
    # radio real se mide solo con los vertices bajos (las palmeras ensanchaban la
    # caja y la isleta salia de 3 m: solo se veia la fuente)
    rot_ = M['horquilla_loews'].build(LIB, radio=max(5.0, min(RADIO + 1.5, d_disp - 0.4)), seed=1)
    bpy.context.view_layer.update()
    r_real = 0.0
    for _o in hierarchy(rot_):
        if _o.type == 'MESH':
            for _v in _o.data.vertices:
                if _v.co.z < 1.6:
                    r_real = max(r_real, math.hypot(_v.co.x, _v.co.y))
    esc_isla = min(1.0, d_disp / max(r_real, 0.1))
    # cota: la MEDIA de la calzada alrededor (la horquilla ya va casi llana)
    z_isla = sum(S[j % N]['z'] for j in range(i_lw - 12, i_lw + 13)) / 25.0
    # (sin plaza pavimentada: la rueda de flores del kit va a ras de la calzada)
    isla = clone(rot_, (cx_, cy_, z_isla - 0.08), rnd.uniform(0, 6.28), scale=esc_isla)
    log('isleta: radio disponible %.1f m, radio real del kit %.1f m -> escala %.2f' % (d_disp, r_real, esc_isla))
    # la horquilla va en plena cuesta: la isleta se apoya en un TAMBOR de piedra
    # (por el lado bajo quedaria en el aire; el inspector de flotantes la hundia)
    rt_ = r_real * esc_isla + 0.12
    vs_ = []
    for k_ in range(24):
        a_ = 2 * math.pi * k_ / 24
        vs_.append((rt_ * math.cos(a_), rt_ * math.sin(a_), 0.05))
        vs_.append((rt_ * math.cos(a_), rt_ * math.sin(a_), -7.0))
    fs_ = [(2 * k_, 2 * k_ + 1, (2 * k_ + 3) % 48, (2 * k_ + 2) % 48) for k_ in range(24)]
    me_t = bpy.data.meshes.new('LOEWS_tambor')
    me_t.from_pydata(vs_, [], fs_)
    import bmesh as _bmt
    _b = _bmt.new()
    _b.from_mesh(me_t)
    _bmt.ops.recalc_face_normals(_b, faces=_b.faces)
    _b.to_mesh(me_t)
    _b.free()
    mt_ = bpy.data.materials.get('MAT_zocalo_piedra') or bpy.data.materials.get('MAT_piedra')
    if mt_ is not None:
        me_t.materials.append(mt_)
    tambor = bpy.data.objects.new('LOEWS_tambor', me_t)
    root_col.objects.link(tambor)
    tambor.parent = isla
    # vallas publicitarias por el exterior de la horquilla
    ck = M['carrera_kit']
    textos = ['REVIOLI', 'CARBONARA', 'FORZA', 'ALLINOL', 'MONDIALE GP']
    for k, ds in enumerate((-24, -12, 0, 12, 24)):
        v = ck.build_valla_publicitaria(LIB, largo=8, texto=textos[k % len(textos)])
        (pp, fq) = pos_side(s_c + ds, -inside, 5.0)
        # ningun extremo del panel (8 m) puede pisar asfalto de NINGUN tramo
        tq = tangent(s_c + ds)
        libre = True
        for e in (-4.2, 0.0, 4.2):
            ex_, ey_ = pp[0] + tq[0] * e, pp[1] + tq[1] * e
            if min(math.hypot(ex_ - S[i]['x'], ey_ - S[i]['y']) - S[i]['w'] / 2
                   for i in range(0, N, 2)) < 1.6:
                libre = False
        if libre:
            clone(v, pp, rot_across(s_c + ds) + (-inside) * math.pi / 2,
                  pitch=(-inside) * pendiente(s_c + ds))
safe('zona_loews', zona_loews)

def zona_horquillas():
    for n, cuantos in ((43, 3), (3, 2)):
        s_c = CURVAS[n]['s_idx'] * paso
        p = frame(s_c)
        if p['sec'] == 'bridge':
            continue  # nada se planta junto a un puente sobre el mar
        inside = 1 if p['lat'] > 0 else -1
        for k in range(cuantos):
            (pp, _) = pos_side(s_c + (k - cuantos // 2) * 9, inside, 3.5)
            if z_terreno(pp[0], pp[1]) < 0.5:
                continue
            clone(lib['jardinera'], pp, rot_across(s_c) + math.pi / 2)
            (pa, _) = pos_side(s_c + (k - cuantos // 2) * 9, inside, 6.0)
            clone(lib['adelfa'], pa, rnd.uniform(0, 6.28))
safe('zona_horquillas', zona_horquillas)

# ============ MONTANA VESTIDA ============
def zona_montana():
    tipos = ['pino', 'pino2', 'cipres', 'adelfa', 'roca', 'roca2']
    tipos += [t_ for t_ in VEG_EXTRA if t_ in lib] * 2       # las formas nuevas pesan el doble
    if M.get('olivos'):
        lib['olivo'] = M['olivos'].build_olivo(LIB, alto=5)
        lib['matorral'] = M['olivos'].build_matorral(LIB)
        tipos += ['olivo', 'olivo', 'matorral', 'matorral']
    x0 = T['x0']; y0 = T['y0']
    x1 = x0 + T['nx'] * T['cell']; y1 = y0 + T['ny'] * T['cell']
    # bosque en MASAS: semillas de arboleda y 4-8 arboles alrededor de cada una
    puestos = 0
    semillas = 0
    intentos = 0
    while semillas < 480 and intentos < 24000:
        intentos += 1
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(y0, y1)
        z = z_terreno(x, y)
        if z < 3.5 or z > 80:
            continue
        d2 = min((x - S[i]['x'])**2 + (y - S[i]['y'])**2 for i in range(0, N, 8))
        if d2 < 26**2:
            continue
        semillas += 1
        if z < 16:
            bajos = ['palmera', 'palmera2', 'adelfa'] + (['olivo', 'matorral'] if 'olivo' in lib else [])
            bajos += [t_ for t_ in ('palmera_v0', 'palmera_v1', 'palmera_v2', 'adelfa_v0', 'adelfa_v1',
                                    'olivo_v0', 'olivo_v1', 'arbusto_v0', 'arbusto_v1') if t_ in lib]
            t_base = bajos[semillas % len(bajos)]
        else:
            t_base = tipos[semillas % len(tipos)]
        for _ in range(rnd.randint(4, 8)):
            xa = x + rnd.uniform(-26, 26)
            ya = y + rnd.uniform(-26, 26)
            za = z_terreno(xa, ya)
            if za < 3.0 or za > 82:
                continue
            d2a = min((xa - S[i]['x'])**2 + (ya - S[i]['y'])**2 for i in range(0, N, 8))
            if d2a < 24**2:
                continue
            t = t_base if rnd.random() < 0.7 else tipos[rnd.randint(0, len(tipos) - 1)]
            if not _libre(xa, ya):   # nada de arboles saliendo de rocas
                continue
            if pendiente_terreno(xa, ya) > 0.62:   # ni plantados en paredes de roca
                continue
            clone(lib[t], (xa, ya, za - 0.15), rnd.uniform(0, 6.28),
                  scale=rnd.uniform(0.75, 1.4))
            puestos += 1
    # segunda capa: masas DENSAS cerca de la pista (30-230 m), que es lo
    # que se ve al conducir: laderas, sector casino, bajadas
    # muestras con peso extra en el sector casino (31-39), la bajada (21-30)
    # y la subida al pueblo (3-6), que son las laderas peladas
    pool = list(range(N))
    for (ca, cb, peso) in ((31, 39, 8), (21, 30, 4), (3, 6, 4)):
        pool += list(range(CURVAS[ca]['s_idx'], CURVAS[cb]['s_idx'])) * peso
    semillas2 = 0
    intentos = 0
    while semillas2 < 420 and intentos < 60000:
        intentos += 1
        q = S[pool[rnd.randint(0, len(pool) - 1)]]
        lado = 1 if rnd.random() < 0.5 else -1
        off = rnd.uniform(30, 230)
        x = q['x'] + lado * q['nx'] * off
        y = q['y'] + lado * q['ny'] * off
        z = z_terreno(x, y)
        if z < 3.5 or z > 80:
            continue
        d2 = min((x - S[i]['x'])**2 + (y - S[i]['y'])**2 for i in range(0, N, 8))
        if d2 < 28**2:
            continue
        semillas2 += 1
        if z < 16:
            bajos = ['palmera', 'palmera2', 'adelfa'] + (['olivo', 'matorral'] if 'olivo' in lib else [])
            bajos += [t_ for t_ in ('palmera_v0', 'palmera_v1', 'palmera_v2', 'adelfa_v0', 'adelfa_v1',
                                    'olivo_v0', 'olivo_v1', 'arbusto_v0', 'arbusto_v1') if t_ in lib]
            t_base = bajos[semillas2 % len(bajos)]
        else:
            t_base = tipos[semillas2 % len(tipos)]
        for _ in range(rnd.randint(4, 7)):
            xa = x + rnd.uniform(-22, 22)
            ya = y + rnd.uniform(-22, 22)
            za = z_terreno(xa, ya)
            if za < 3.0 or za > 82:
                continue
            d2a = min((xa - S[i]['x'])**2 + (ya - S[i]['y'])**2 for i in range(0, N, 8))
            if d2a < 24**2:
                continue
            t = t_base if rnd.random() < 0.7 else tipos[rnd.randint(0, len(tipos) - 1)]
            if not _libre(xa, ya):   # nada de arboles saliendo de rocas
                continue
            if pendiente_terreno(xa, ya) > 0.62:   # ni plantados en paredes de roca
                continue
            clone(lib[t], (xa, ya, za - 0.15), rnd.uniform(0, 6.28),
                  scale=rnd.uniform(0.75, 1.4))
            puestos += 1
    log('bosque: %d arboles en %d + %d masas' % (puestos, semillas, semillas2))
safe('zona_montana', zona_montana)

# ============ ARCO DE ROCA (DESACTIVADO: el usuario confirma que en la
# pelicula no hay ninguna roca sobre el camino) ============
def zona_arco():
    return
    if not M.get('arco_roca'):
        return
    s_a = 340.0
    p = frame(s_a)
    arco = M['arco_roca'].build(LIB, luz=max(18.0, p['w'] + 5), alto_libre=9.5, seed=3)
    rot = math.atan2(p['ny'], p['nx']) - math.pi / 2  # hueco (+Y local) al tangente
    t = tangent(s_a)
    rot = math.atan2(t[1], t[0]) - math.pi / 2
    clone(arco, (p['x'], p['y'], p['z'] - 0.2), rot)
safe('zona_arco', zona_arco)

# ============ COCHES-ESPECTADOR APARCADOS ============
def zona_coches():
    if not M.get('coches_kit'):
        return
    ck = M['coches_kit']
    filas = [ck.build_fila_aparcada(LIB, n=6, seed=s) for s in (1, 2, 3, 4, 5)]
    # obstaculos: casas (origen = centro de fachada, cuerpo 12 m hacia atras) y
    # edificios grandes
    obst = []
    for ob in root_col.objects:
        if ob.parent is not None:
            continue
        if ob.name.startswith('CASAS_'):
            obst.append((ob.location.x, ob.location.y, 11.0))
        elif ob.name.startswith(('CARRERA_tribuna', 'CARRERA_boxes', 'CARRERA_pantalla',
                                 'HOTEL_root', 'AYTO_root', 'CAMPANILE_root', 'CASINO_root',
                                 'LOEWS_', 'CARRERA_portico')):
            obst.append((ob.location.x, ob.location.y, 30.0))
    lw = G.get('loews') or {}
    s_lw = (lw.get('s_idx') or CURVAS[39]['s_idx']) * paso

    def sitio_ok(s_m, side, offset):
        q = frame(s_m)
        if q['sec'] in ('bridge', 'dirt'):
            return None
        if min(abs(s_m - 522.0), L - abs(s_m - 522.0)) < 120:      # tunel y sus bocas
            return None
        if side == -1 and (s_m > L - 230 or s_m < 210):             # pit lane y boxes
            return None
        # tramo casi recto: la fila es una recta de ~28 m
        qa, qb = frame(s_m - 14), frame(s_m + 14)
        giro = abs(math.atan2(qa['ny'] * qb['nx'] - qa['nx'] * qb['ny'],
                              qa['nx'] * qb['nx'] + qa['ny'] * qb['ny']))
        if giro > 0.22:
            return None
        (pp, _q) = pos_side(s_m, side, offset)
        t = tangent(s_m)
        zs = [z_terreno(pp[0] + dx * t[0] + side * dy * q['nx'], pp[1] + dx * t[1] + side * dy * q['ny'])
              for dx in (-13, -6, 0, 6, 13) for dy in (-2.6, 2.6)]
        if min(zs) < 0.6 or max(zs) - min(zs) > 1.8:
            return None
        z_borde = q['z'] - q['lat'] * side * (q['w'] / 2)
        if abs(z_borde - sum(zs) / len(zs)) > 1.6:
            return None
        # holgura a casas/edificios en toda la longitud de la fila
        for dx in (-13, -6, 0, 6, 13):
            x_, y_ = pp[0] + dx * t[0], pp[1] + dx * t[1]
            for (ox, oy, r_) in obst:
                if math.hypot(x_ - ox, y_ - oy) < r_:
                    return None
        # ningun otro tramo de pista cerca (horquillas, cruces)
        for dx in (-13, 0, 13):
            x_, y_ = pp[0] + dx * t[0], pp[1] + dx * t[1]
            for i in range(0, N, 3):
                if min(abs(i * paso - s_m), L - abs(i * paso - s_m)) < 60:
                    continue
                if math.hypot(x_ - S[i]['x'], y_ - S[i]['y']) < S[i]['w'] / 2 + 6.0:
                    return None
        return (pp[0], pp[1], sum(zs) / len(zs))

    candidatos = []
    # preferencia 1: pradera interior junto a la rotonda (como en la pelicula)
    for ds in (-70, -45, 45, 70, 95):
        for side in (1, -1):
            r = sitio_ok(s_lw + ds, side, 7.5)
            if r:
                candidatos.append((0, s_lw + ds, side, r))
    # preferencia 2: cualquier sitio valido a lo largo del circuito
    s_m = 30.0
    while s_m < L - 30:
        for side in (-1, 1):
            r = sitio_ok(s_m, side, 6.5)
            if r:
                candidatos.append((1, s_m, side, r))
        s_m += 22.0
    puestas = []
    for pref, s_c, side, (x, y, z) in sorted(candidatos, key=lambda c: (c[0], c[1])):
        if len(puestas) >= 11:
            break
        if any(min(abs(s_c - sp), L - abs(s_c - sp)) < (70 if sd != side else 170) for (sp, sd) in puestas):
            continue
        clone(filas[len(puestas) % len(filas)], (x, y, z), rot_facing_road(s_c, side))
        puestas.append((s_c, side))
    log('coches-espectador: %d filas junto a la pista en s=%s (de %d sitios validos)'
        % (len(puestas), [int(sp) for sp, _ in puestas], len(candidatos)))
safe('zona_coches', zona_coches)

# ============ VIADUCTOS DE ARCOS BAJO LOS TRAMOS DE PUENTE ============
def zona_viaductos():
    if not M.get('viaducto_curvo'):
        return
    # fuera los faldones/pilas simples: los sustituye la obra de arcos
    for nombre in list(bpy.data.objects.keys()):
        if nombre.startswith('PUENTE_FALDONES') or nombre.startswith('PUENTE_PILAS'):
            bpy.data.objects.remove(bpy.data.objects[nombre], do_unlink=True)
    tramos = 0
    run = []
    for i in range(N + 1):
        es_b = S[i % N]['sec'] == 'bridge'
        if es_b:
            run.append(i % N)
        if (not es_b or i == N) and run:
            if len(run) > 6:
                pts = [(S[j]['x'], S[j]['y'], S[j]['z']) for j in run[::2]]
                # el viaducto v2 admite el ancho REAL punto a punto: asi el pretil
                # nunca pisa la calzada (con un ancho unico tapaba ~0.4 m por lado)
                anchos = [S[j]['w'] + 1.0 for j in run[::2]]
                try:
                    v = M['viaducto_curvo'].build_desde_puntos(LIB, pts, ancho=anchos, nivel_agua=0.0)
                except TypeError:
                    v = M['viaducto_curvo'].build_desde_puntos(LIB, pts, ancho=max(anchos), nivel_agua=0.0)
                clone(v, (0, 0, 0), 0.0)
                tramos += 1
            run = []
    log('viaductos de arcos: %d tramos' % tramos)
safe('zona_viaductos', zona_viaductos)

# ============ ACUEDUCTO SOBRE EL PUEBLO ============
def zona_acueducto():
    """Acueducto decorativo SIN cruzar la carretera: busca sitio con holgura."""
    if not M.get('acueducto'):
        return
    ac = M['acueducto'].build(LIB, largo=200, alto=40, n_arcos=8, seed=1)
    for s_m, off in ((880, 300), (760, 340), (1000, 330), (880, 400), (700, 380)):
        p = frame(s_m)
        x = p['x'] - p['nx'] * off
        y = p['y'] - p['ny'] * off
        d2 = min((x - S[i]['x'])**2 + (y - S[i]['y'])**2 for i in range(0, N, 2))
        zt = z_terreno(x, y)
        if d2 > 125**2 and zt > 1.0:
            t = tangent(s_m)
            clone(ac, (x, y, zt - 1.0), math.atan2(t[1], t[0]))
            log('acueducto colocado en s=%d, %d m tierra adentro' % (s_m, off))
            return
    log('acueducto: sin sitio con holgura, omitido')
safe('zona_acueducto', zona_acueducto)

# ============ MONTANAS DE FONDO ============
def zona_montanas_fondo():
    """Cordilleras completas: el circuito sube y baja entre montanas altas."""
    if not M.get('montanas_fondo'):
        return
    mf = M['montanas_fondo']
    x1 = T['x0'] + T['nx'] * T['cell']
    y1 = T['y0'] + T['ny'] * T['cell']
    cadena1 = mf.build_cordillera(LIB, largo=1100, n_picos=5, seed=3)
    clone(cadena1, ((T['x0'] + x1) / 2 + 120, y1 - 90, 0.0), 0.0)
    cadena2 = mf.build_cordillera(LIB, largo=900, n_picos=4, seed=7)
    clone(cadena2, (x1 - 80, (T['y0'] + y1) / 2 + 160, 0.0), math.pi / 2)
    # RONDA 14: penascos en las cimas de las colinas del interior (maximos locales
    # del terreno, lejos de la pista y del pueblo)
    if hasattr(mf, 'build_pena'):
        import numpy as _np
        Zg = _np.array(T['z']).reshape(T['ny'], T['nx'])
        cands = []
        for j in range(3, T['ny'] - 3, 2):
            for i in range(3, T['nx'] - 3, 2):
                z = Zg[j, i]
                if z < 45.0 or z < Zg[j - 3:j + 4, i - 3:i + 4].max() - 0.01:
                    continue
                x = T['x0'] + i * T['cell']
                y = T['y0'] + j * T['cell']
                dp = min(math.hypot(S[i_]['x'] - x, S[i_]['y'] - y) for i_ in range(0, N, 3))
                if dp < 110.0:
                    continue
                cands.append((z, x, y))
        cands.sort(reverse=True)
        puestos = []
        n_p = 0
        for (z, x, y) in cands:
            if any(math.hypot(x - a, y - b) < 160.0 for (a, b) in puestos):
                continue
            pena = mf.build_pena(LIB, alto=18.0 + 14.0 * rnd.random(), radio=16.0 + 10.0 * rnd.random(), seed=n_p)
            pc = clone(pena, (x, y, z - 2.5), rnd.uniform(0, 6.28))
            pc.name = 'MONT_pena'
            puestos.append((x, y))
            n_p += 1
            if n_p >= 9:
                break
        log('penascos en cimas: %d' % n_p)
safe('zona_montanas_fondo', zona_montanas_fondo)

# ============ MOBILIARIO URBANO: farolas, guirnaldas, macetas ============
def zona_calle():
    ck = M.get('calle_kit')
    if not ck:
        return
    TRAMOS = [(630, 1090), (1270, 1550), (2490, 2750), (3190, 3450)]
    lib['farola_c'] = ck.build_farola(LIB, alto=5.2)
    # poste de guirnalda: fuste verde de 7.5 m
    _mp = bpy.data.materials.get('MAT_CALLE_poste') or bpy.data.materials.new('MAT_CALLE_poste')
    _mp.use_nodes = True
    _mp.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0.05, 0.16, 0.10, 1)
    _me = bpy.data.meshes.new('CALLE_poste_guirnalda')
    _r = 0.09
    _me.from_pydata([(-_r, -_r, 0), (_r, -_r, 0), (_r, _r, 0), (-_r, _r, 0),
                     (-_r, -_r, 7.5), (_r, -_r, 7.5), (_r, _r, 7.5), (-_r, _r, 7.5)], [],
                    [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)])
    _me.materials.append(_mp)
    lib['poste_guirnalda'] = bpy.data.objects.new('CALLE_poste_guirnalda', _me)
    LIB.objects.link(lib['poste_guirnalda'])
    lib['maceta'] = ck.build_maceta(LIB)
    guirnaldas_cache = {}
    n_far = n_gui = n_mac = 0
    for (s0u, s1u) in TRAMOS:
        # farolas alternando aceras
        s_m = s0u
        k = 0
        while s_m < s1u:
            side = 1 if k % 2 else -1
            p = frame(s_m)
            if p['sec'] not in ('dirt', 'bridge'):
                (pp, _) = pos_side(s_m, side, 1.3)
                clone(lib['farola_c'], (pp[0], pp[1], p['z'] - 0.2),
                      rot_facing_road(s_m, side))
                n_far += 1
            s_m += 44
            k += 1
        # guirnaldas de banderines cruzando la calle
        s_m = s0u + 30
        while s_m < s1u:
            p = frame(s_m)
            if p['sec'] not in ('dirt', 'bridge'):
                luz = round((p['w'] + 7) / 2) * 2
                if luz not in guirnaldas_cache:
                    guirnaldas_cache[luz] = ck.build_guirnalda(LIB, luz=luz)
                clone(guirnaldas_cache[luz], (p['x'], p['y'], p['z'] + 6.4),
                      rot_across(s_m))
                # postes en los dos extremos: la guirnalda ya no cuelga del aire
                for sg in (1, -1):
                    lt = sg * luz / 2.0
                    clone(lib['poste_guirnalda'],
                          (p['x'] + p['nx'] * lt, p['y'] + p['ny'] * lt,
                           p['z'] - p['lat'] * lt - 0.9), 0.0)
                n_gui += 1
            s_m += 76
        # macetas junto a los bajos
        s_m = s0u + 15
        k = 0
        while s_m < s1u:
            side = -1 if k % 2 else 1
            p = frame(s_m)
            if p['sec'] not in ('dirt', 'bridge'):
                (pp, _) = pos_side(s_m, side, 2.8)
                clone(lib['maceta'], (pp[0], pp[1], p['z'] - 0.18),
                      rnd.uniform(0, 6.28))
                n_mac += 1
            s_m += 58
            k += 1
    # puestecillos de mercado en la plaza del ayuntamiento
    for ds in (-14, 4, 22):
        (pp, _) = pos_side(1150 + ds, -1, 24)
        if z_terreno(pp[0], pp[1]) > 0.5:
            clone(ck.build_toldo_mercado(LIB, seed=ds), pp,
                  rot_facing_road(1150 + ds, -1))
    log('calle: %d farolas, %d guirnaldas, %d macetas' % (n_far, n_gui, n_mac))
safe('zona_calle', zona_calle)

# ============ TUNEL POR LA MONTANA-COCHE (curvas 2 -> 3) ============
def _taladro(i0, i1, half, alto, nombre, gal=None):
    """Tubo con seccion de arco siguiendo la pista entre dos indices."""
    perfil = [(-1.0, 0.0), (-1.0, 0.55), (-0.7, 0.85), (0.0, 1.0),
              (0.7, 0.85), (1.0, 0.55), (1.0, 0.0)]
    idxs = list(range(i0, i1 + 1))
    verts, faces = [], []
    for i in idxs:
        q = S[i % N]
        # dentro de la galeria: arco de tunel; FUERA: corte a cielo abierto,
        # mas ancho y hondo, para que no quede ningun banco de roca junto a la pista
        dentro = gal is None or (gal[0] <= i <= gal[1])
        h_, a_, b_ = (half, alto, 1.5) if dentro else (17.0, 110.0, 7.0)
        for (u, v) in perfil:
            verts.append((q['x'] + q['nx'] * u * h_, q['y'] + q['ny'] * u * h_,
                          q['z'] - b_ + v * a_))
    npf = len(perfil)
    for k in range(len(idxs) - 1):
        for j in range(npf - 1):
            a = k * npf + j
            faces.append((a, a + 1, a + npf + 1, a + npf))
        a = k * npf
        b = a + npf - 1
        faces.append((b, a, a + npf, b + npf))
    faces.append(tuple(range(0, npf))[::-1])
    faces.append(tuple(range((len(idxs) - 1) * npf, len(idxs) * npf)))
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    me.validate()
    import bmesh as bm_
    bb = bm_.new()
    bb.from_mesh(me)
    bm_.ops.remove_doubles(bb, verts=bb.verts, dist=0.01)
    bm_.ops.recalc_face_normals(bb, faces=bb.faces)
    bb.to_mesh(me)
    bb.free()
    me.update()
    ob = bpy.data.objects.new(nombre, me)
    root_col.objects.link(ob)
    return ob

def _tunel_abierto(ob, i0, i1, tramo=4):
    """Lanza rayos por el corredor siguiendo su curva (tramos de ~8 m), a
    varias alturas y laterales: abierto si ninguno choca con la roca."""
    inv = ob.matrix_world.inverted()
    choques = 0
    for lat in (-5.0, 0.0, 5.0):
        for h in (1.5, 4.0, 6.5):
            for i in range(i0, i1 - tramo, tramo):
                q0 = S[i % N]; q1 = S[(i + tramo) % N]
                a = inv @ Vector((q0['x'] + q0['nx'] * lat, q0['y'] + q0['ny'] * lat, q0['z'] + h))
                b = inv @ Vector((q1['x'] + q1['nx'] * lat, q1['y'] + q1['ny'] * lat, q1['z'] + h))
                d = b - a
                if d.length < 1e-6:
                    continue
                hit, loc, nrm, idx_f = ob.ray_cast(a, d.normalized(), distance=d.length)
                if hit:
                    choques += 1
                    break
    return choques == 0, choques

def _paredes_de_roca(ob, i0, i1):
    """Las caras de la roca dentro del corredor del tunel pasan al material
    de roca mas oscuro del objeto (el corte hereda el verde del monte)."""
    mats = [m.name if m else '' for m in ob.data.materials]
    candidatos = [k for k, n in enumerate(mats) if 'roca_oscura' in n] or \
                 [k for k, n in enumerate(mats) if 'roca' in n]
    if not candidatos:
        m = bpy.data.materials.get('MAT_piedra')
        if not m:
            return 0
        ob.data.materials.append(m)
        candidatos = [len(ob.data.materials) - 1]
    slot = candidatos[0]
    corr = [S[i % N] for i in range(i0, i1 + 1, 2)]
    n = 0
    for f in ob.data.polygons:
        w = ob.matrix_world @ f.center
        for q in corr:
            dx = w.x - q['x']; dy = w.y - q['y']
            lat = abs(dx * q['nx'] + dy * q['ny'])
            lon = abs(dx * q['ny'] - dy * q['nx'])
            if lat < 12.5 and lon < 2.5 and (q['z'] - 2.5) < w.z < (q['z'] + 11.0):
                f.material_index = slot
                n += 1
                break
    return n

def _portal(i, half, alto, nombre, grosor=1.7, prof=1.6):
    """Arco de piedra en una boca de tunel (anillo entre el hueco y +grosor)."""
    perfil = [(-1.0, -0.15), (-1.0, 0.55), (-0.7, 0.85), (0.0, 1.0),
              (0.7, 0.85), (1.0, 0.55), (1.0, -0.15)]
    q = S[i % N]
    t = (q['ny'], -q['nx'])
    verts, faces = [], []
    for lado_t in (-1, 1):
        for (u, v) in perfil:
            for esc in (1.0, 1.0 + grosor / half):
                verts.append((q['x'] + q['nx'] * u * half * esc + t[0] * lado_t * prof,
                              q['y'] + q['ny'] * u * half * esc + t[1] * lado_t * prof,
                              q['z'] - 1.5 + v * alto * (esc if v > 0 else 1.0)))
    npf = len(perfil)
    def vi(lado, j, k):
        return lado * npf * 2 + j * 2 + k
    for lado in (0, 1):
        for j in range(npf - 1):
            a, b, c, d = vi(lado, j, 0), vi(lado, j, 1), vi(lado, j + 1, 1), vi(lado, j + 1, 0)
            faces.append((a, b, c, d) if lado else (d, c, b, a))
    for j in range(npf - 1):  # banda exterior e interior entre las dos caras
        faces.append((vi(0, j, 1), vi(1, j, 1), vi(1, j + 1, 1), vi(0, j + 1, 1)))
        faces.append((vi(1, j, 0), vi(0, j, 0), vi(0, j + 1, 0), vi(1, j + 1, 0)))
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    m_pie = bpy.data.materials.get('MAT_piedra')
    if m_pie:
        me.materials.append(m_pie)
    ob = bpy.data.objects.new(nombre, me)
    root_col.objects.link(ob)
    return ob

TUNEL_INFO = {}

def zona_tunel():
    """Entre las curvas 2 y 3 la pista atraviesa un ACANTILADO por un tunel
    corto; la montana-coche va aparte, a la DERECHA de la carretera."""
    s_a = CURVAS[2]['s_idx'] * paso
    s_b = CURVAS[3]['s_idx'] * paso
    s_mid = (s_a + s_b) / 2 + 20
    p = frame(s_mid)
    t = tangent(s_mid)
    mf = M.get('montanas_fondo')
    mr = M.get('montana_rueda')
    mc = M.get('montana_coche')
    if mc is not None:
        # RONDA 13: la rueda es la de un COCHE FOSIL COMPLETO (montana_coche). Origen
        # = centro de la rueda delantera, 26 m a la derecha de la calzada; el coche
        # queda con el morro tierra adentro (-n) y la zaga hacia el mar (+n); su lado
        # -Y mira a los coches que llegan (ambos lados llevan ruedas talladas).
        R_C, ANCHO_C = 40.0, 78.0
        s_face = s_mid - ANCHO_C * 0.42
        pf = frame(s_face)
        tf = tangent(s_face)
        cx_, cy_ = pf['x'] - pf['nx'] * (0.65 * R_C), pf['y'] - pf['ny'] * (0.65 * R_C)
        radio = R_C * 1.3
        ang_c = math.atan2(-pf['ny'], -pf['nx'])          # +X local = -n (tierra adentro)
        # el coche se monta con booleanos evaluados por el depsgraph: hay que construirlo
        # en una coleccion VISIBLE (los objetos de LIB no se evaluan) y pasarlo a LIB despues
        col_tmp = bpy.data.collections.new('TMP_MCOCHE')
        root_col.children.link(col_tmp)
        try:
            res_c = mc.build(col_tmp, radio=R_C, ancho=ANCHO_C, z_fondo=-(pf['z'] + 8.0), seed=11, lado_visible=-1)   # v2: los coches llegan por -Y
        except TypeError:
            res_c = mc.build(col_tmp, radio=R_C, ancho=ANCHO_C, z_fondo=-(pf['z'] + 8.0), seed=11)
        raiz_c = res_c[0] if isinstance(res_c, tuple) else res_c
        bpy.context.view_layer.update()
        for ob_ in list(col_tmp.objects):
            col_tmp.objects.unlink(ob_)
            LIB.objects.link(ob_)
        root_col.children.unlink(col_tmp)
        bpy.data.collections.remove(col_tmp)
        r = clone(raiz_c, (cx_, cy_, pf['z'] - 1.4), ang_c)
        r.name = 'TUNEL_acantilado'
        mf = None
        mr = None
        s_mid, p, t = s_face, pf, tf
        # nada de casas ni arboles bajo la huella del coche (el morro vuela sobre el
        # pueblo y el rayo vertical del limpiador no pilla las casas de la orilla)
        bpy.context.view_layer.update()
        _mw_c = r.matrix_world
        _xs, _ys = [], []
        for _o in [r] + list(r.children_recursive):
            if _o.type == 'MESH':
                for _c in _o.bound_box:
                    _w = _o.matrix_world @ Vector(_c)
                    _xs.append(_w.x)
                    _ys.append(_w.y)
        _n_h = 0
        _inv_c = _mw_c.inverted()
        for _ob in list(root_col.objects):
            try:
                if _ob.parent is not None or not _ob.name.startswith(('CASAS_', 'VEG_', 'OLI_', 'CALLE_', 'COCHE_')):
                    continue
                _lx, _ly = _ob.location.x, _ob.location.y
            except ReferenceError:
                continue
            if not (min(_xs) - 4 < _lx < max(_xs) + 4 and min(_ys) - 4 < _ly < max(_ys) + 4):
                continue
            _l = _inv_c @ Vector((_lx, _ly, 0.0))
            # huella del coche en local: x en [-4.4R, 1.5R], |y| <= ancho/2 + 4 (y no la calzada)
            if -4.4 * R_C < _l.x < 1.5 * R_C and abs(_l.y) < ANCHO_C / 2 + 4.0:
                for _ch in list(_ob.children_recursive):
                    bpy.data.objects.remove(_ch, do_unlink=True)
                bpy.data.objects.remove(_ob, do_unlink=True)
                _n_h += 1
        log('montana-COCHE fosil colocada en s=%.0f (rueda delantera R=%.0f m a %.0f m de la calzada); %d objetos retirados de su huella' % (s_face, R_C, 0.65 * R_C, _n_h))
    if mr is not None:
        # RONDA 12: la montana ES una rueda de coche (pelicula). La cara de la rueda
        # (+Y local) mira hacia los coches que llegan; el tunel entra por su base y
        # sale por la ladera rocosa de atras.
        RAD_R, ESP_R = 56.0, 78.0
        s_face = s_mid - ESP_R * 0.42
        pf = frame(s_face)
        tf = tangent(s_face)
        cx_, cy_ = pf['x'] - pf['nx'] * 26.0, pf['y'] - pf['ny'] * 26.0   # la rueda queda a la DERECHA; el tunel entra por su parte baja-izquierda
        radio = RAD_R
        ang_cara = math.atan2(-tf[1], -tf[0]) - math.pi / 2     # +Y local = hacia atras
        res_r = mr.build(LIB, radio=RAD_R, espesor=ESP_R, seed=11)
        raiz_r = res_r[0] if isinstance(res_r, tuple) else res_r
        r = clone(raiz_r, (cx_, cy_, pf['z'] - 1.4), ang_cara)
        r.name = 'TUNEL_acantilado'
        mf = None      # el resto del bloque no debe reconstruir el acantilado antiguo
        # el macizo esta centrado en s_face: el taladro, la medida de la galeria y
        # los portales se centran ahi (si no, la medida arrancaba fuera de la roca)
        s_mid, p, t = s_face, pf, tf
        log('montana-rueda colocada en s=%.0f (cara mirando a la llegada, radio %.0f m)' % (s_face, RAD_R))
    if mf:
        # radio grande, pero sin invadir otros tramos de la pista
        cx_, cy_ = p['x'] - p['nx'] * 4, p['y'] - p['ny'] * 4
        i_a, i_b = idx(s_mid - 190), idx(s_mid + 190)
        fuera = [i for i in range(0, N, 3) if not (i_a <= i <= i_b)]
        d_otro = min(math.hypot(cx_ - S[i]['x'], cy_ - S[i]['y']) for i in fuera)
        radio = max(90.0, min(118.0, d_otro - 14.0))
        cliff = mf.build_pico(LIB, alto=58, radio=radio, seed=11)
        r = clone(cliff, (cx_, cy_, p['z'] - 14.0), math.atan2(t[1], t[0]))
        log('acantilado del tunel: radio %.0f m (otro tramo de pista a %.0f m)' % (radio, d_otro))
    elif mr is None and mc is None:
        pt = M.get('penon_topolino')
        cliff = pt.build(LIB, largo=180, ancho=110, alto=36, seed=5, con_vegetacion=False)
        r = clone(cliff, (p['x'], p['y'], p['z'] - 9.0), math.atan2(t[1], t[0]))
    r.name = 'TUNEL_acantilado'
    if mr is not None:
        roca = next((o for o in [r] + r.children_recursive if o.type == 'MESH' and 'MRUEDA_roca' in o.name), None)
        if roca is None:
            roca = max((o for o in [r] + r.children_recursive if o.type == 'MESH'),
                       key=lambda o: len(o.data.vertices))
    else:
        roca = max((o for o in [r] + r.children_recursive if o.type == 'MESH'),
                   key=lambda o: len(o.data.vertices))
    roca.data = roca.data.copy()  # malla propia para poder taladrar
    i0t, i1t = idx(s_mid - 160), idx(s_mid + 160)
    # extension de la galeria medida sobre la roca SIN cortar (techo >= 11 m)
    bpy.context.view_layer.update()
    _inv0 = roca.matrix_world.inverted()
    def _techo0(i):
        q = S[i % N]
        a = _inv0 @ Vector((q['x'], q['y'], q['z'] + 11.0))
        b = _inv0 @ Vector((q['x'], q['y'], q['z'] + 260.0))
        d = b - a
        return roca.ray_cast(a, d.normalized(), distance=d.length)[0]
    i_ga = i_gb = idx(s_mid)
    while idx(s_mid) - i_ga < 90 and _techo0(i_ga - 1):
        i_ga -= 1
    while i_gb - idx(s_mid) < 90 and _techo0(i_gb + 1):
        i_gb += 1
    tal = _taladro(i0t, i1t, 10.5, 9.5, 'TUNEL_taladro')  # seccion unica: la variable rompia el booleano
    # normales coherentes tambien en la roca (el loft puede venir mezclado)
    import bmesh as bm_
    bb = bm_.new()
    bb.from_mesh(roca.data)
    bm_.ops.recalc_face_normals(bb, faces=bb.faces)
    bb.to_mesh(roca.data)
    bb.free()
    cortado = False
    for solver in ('EXACT', 'MANIFOLD', 'FAST'):
        mod = roca.modifiers.new('TUNEL', 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = tal
        try:
            mod.solver = solver
        except Exception:
            roca.modifiers.remove(mod)
            continue
        try:
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = roca
            roca.select_set(True)
            bpy.ops.object.modifier_apply(modifier='TUNEL')
        except Exception as e:
            log('tunel: solver %s fallo (%s)' % (solver, e))
            if roca.modifiers.get('TUNEL'):
                roca.modifiers.remove(roca.modifiers['TUNEL'])
            continue
        abierto, choques = _tunel_abierto(roca, i0t + 4, i1t - 4)
        log('tunel: solver %s -> rayos bloqueados %d/9' % (solver, choques))
        if abierto:
            cortado = True
            break
    if cortado:
        bpy.data.objects.remove(tal, do_unlink=True)
        n_par = _paredes_de_roca(roca, i0t, i1t)
        log('tunel taladrado en el acantilado (curvas 2-3); %d caras de pared en roca' % n_par)
        # FALDA: todo vertice de roca que asome menos de 3.5 m sobre el terreno se
        # remete 1 m bajo el. Desplazamiento pequeno (<= 4.5 m): no crea cortinas
        # en las bocas (hundir el corredor entero SI las tapaba) y quita los bancos
        # planos de roca junto a la calzada
        _mw2 = roca.matrix_world
        _iw2 = _mw2.inverted()
        _nh = 0
        for v in roca.data.vertices:
            w = _mw2 @ v.co
            t_ = z_terreno(w.x, w.y)
            lim_ = 3.5
            # junto a la pista y FUERA de la galeria (a mas de 16 m de las bocas) se
            # remete mas: nada de losas de roca asomando a pie de calzada
            jn = min(range(0, N, 4), key=lambda j: (w.x - S[j]['x']) ** 2 + (w.y - S[j]['y']) ** 2)
            if math.hypot(w.x - S[jn]['x'], w.y - S[jn]['y']) < 34.0 and not (i_ga - 8 <= jn <= i_gb + 8):
                lim_ = 9.0
            if t_ - 1.0 < w.z < t_ + lim_:
                v.co = _iw2 @ Vector((w.x, w.y, t_ - 1.0))
                _nh += 1
        roca.data.update()
        log('tunel: %d vertices de la falda remetidos bajo el terreno' % _nh)
    else:
        # ultimo recurso: solo los vertices DENTRO del tubo bajan al suelo
        log('tunel: booleanos sin exito, se vacia el tubo a mano')
        for v in roca.data.vertices:
            w = roca.matrix_world @ v.co
            for q in [S[i % N] for i in range(i0t, i1t + 1, 2)]:
                dx = w.x - q['x']; dy = w.y - q['y']
                lat = abs(dx * q['nx'] + dy * q['ny'])
                lon = abs(dx * q['ny'] - dy * q['nx'])
                if lat < 10.5 and lon < 2.5 and (q['z'] - 1.5) < w.z < (q['z'] + 9.5):
                    v.co = roca.matrix_world.inverted() @ Vector((w.x, w.y, q['z'] - 2.0))
                    break
        bpy.data.objects.remove(tal, do_unlink=True)
    # la falda baja y tendida del acantilado toma el material del TERRENO:
    # ya no asoma como una cuna gris en el cesped
    _mt = bpy.data.materials.get('MAT_terreno')
    if _mt is not None:
        roca.data.materials.append(_mt)
        _slot = len(roca.data.materials) - 1
        _mw = roca.matrix_world
        _r3 = _mw.to_3x3()
        _nf = 0
        for f in roca.data.polygons:
            w_ = _mw @ f.center
            if (_r3 @ f.normal).normalized().z > 0.70 and w_.z - z_terreno(w_.x, w_.y) < 4.0:
                f.material_index = _slot
                _nf += 1
        log('tunel: %d caras de falda con material de terreno' % _nf)
    # portales donde de verdad termina la roca (techo >= 11 m sobre la calzada)
    def _borde_roca(i_from, paso_i):
        inv = roca.matrix_world.inverted()
        ultimo = i_from
        for k in range(0, 90):
            i = i_from + k * paso_i
            q = S[i % N]
            a = inv @ Vector((q['x'], q['y'], q['z'] + 11.0))
            b = inv @ Vector((q['x'], q['y'], q['z'] + 260.0))
            d = b - a
            hit, loc, nrm, fi = roca.ray_cast(a, d.normalized(), distance=d.length)
            if not hit:
                break
            ultimo = i
        return ultimo
    i_in = _borde_roca(idx(s_mid), -1) - 2
    i_out = _borde_roca(idx(s_mid), 1) + 2
    s_in, s_out = (i_in % N) * paso, (i_out % N) * paso
    for i_boca in (i_in, i_out):
        _portal(i_boca % N, 10.5, 9.5, 'TUNEL_portal')
    r['s_in'] = float(s_in)
    r['s_out'] = float(s_out)
    TUNEL_INFO['s_in'] = s_in
    TUNEL_INFO['s_out'] = s_out
    log('tunel: entrada en s=%.0f, salida en s=%.0f (%.0f m de galeria)' % (s_in, s_out, s_out - s_in))
    nb = _limpiar_bajo_roca(roca)
    log('tunel: %d objetos retirados de dentro/debajo del acantilado' % nb)
    # las casas no pueden pisar la falda del acantilado (asomaba una cuna gris)
    if mf:
        n_c = 0
        for ob in list(root_col.objects):
            try:
                cerca = (ob.parent is None and ob.name.startswith('CASAS_')
                         and math.hypot(ob.location.x - cx_, ob.location.y - cy_) < radio + 16)
            except ReferenceError:
                continue
            if cerca:
                for ch in list(ob.children_recursive):
                    bpy.data.objects.remove(ch, do_unlink=True)
                bpy.data.objects.remove(ob, do_unlink=True)
                n_c += 1
        log('tunel: %d casas retiradas de la falda del acantilado' % n_c)
    # suelo de piedra de pared a pared dentro de la galeria (tapa hierba y arcen)
    ms = bpy.data.materials.get('MAT_tunel_suelo')
    if ms is None:
        ms = bpy.data.materials.new('MAT_tunel_suelo')
        ms.use_nodes = True
        bs_ = ms.node_tree.nodes.get('Principled BSDF')
        bs_.inputs['Base Color'].default_value = (0.20, 0.20, 0.21, 1)
        bs_.inputs['Roughness'].default_value = 0.9
    vs_, fs_ = [], []
    rango = list(range(i_in + 5, i_out - 4))  # bien DENTRO de la galeria: asomaba por las bocas
    for i in rango:
        q = S[i % N]
        half = q['w'] / 2.0
        for sg in (1, -1):
            # del borde hacia la pared el suelo va PLANO a la cota del borde
            # (si siguiera el plano peraltado, el arcen asomaba por encima)
            z_b = q['z'] - q['lat'] * sg * half
            for l_, z_ in ((half - 0.08, z_b + 0.05), (10.7, z_b + 0.14)):
                lt = sg * l_
                vs_.append((q['x'] + q['nx'] * lt, q['y'] + q['ny'] * lt, z_))
    for k in range(len(rango) - 1):
        o = 4 * k
        fs_.append((o + 1, o, o + 4, o + 5))
        fs_.append((o + 2, o + 3, o + 7, o + 6))
    me_s = bpy.data.meshes.new('TUNEL_suelo')
    me_s.from_pydata(vs_, [], fs_)
    me_s.materials.append(ms)
    root_col.objects.link(bpy.data.objects.new('TUNEL_suelo', me_s))
    # montana-coche a la DERECHA: busca un sitio cerca de la boca que no pise
    # ni la pista ni el pueblo (la montana mide 150 x 95 m)
    pt = M.get('penon_cara') or M['penon_topolino']
    if mc is not None:
        pt = None      # con el coche fosil completo sobra la segunda montana-coche
    fijos = [o for o in root_col.objects if o.parent is None and o.name.startswith(
        ('CASAS_', 'CARRERA_boxes', 'CARRERA_hotel', 'CARRERA_tribuna', 'CIVICO_',
         'PUEBLO_', 'HOTEL_', 'CASINO', 'LOEWS', 'PUERTO_', 'CALLE_toldo'))]
    boca = frame(s_mid - 72)
    mejor = None
    for s_c in range(int(s_mid) - 320, int(s_mid) + 180, 20):
        for off in range(105, 300, 15):
            (pp, _) = pos_side(s_c, -1, off)
            x, y = pp[0], pp[1]
            if z_terreno(x, y) < 1.0:
                continue
            d_pista = min(math.hypot(x - S[i]['x'], y - S[i]['y']) for i in range(0, N, 4))
            if d_pista < 92:
                continue
            d_fijo = min([math.hypot(x - o.location.x, y - o.location.y) for o in fijos] or [1e9])
            if d_fijo < 95:
                continue
            coste = math.hypot(x - boca['x'], y - boca['y'])
            if mejor is None or coste < mejor[0]:
                mejor = (coste, x, y, s_c)
    if pt is None:
        log('montana-coche lateral omitida (el coche fosil completo ya esta en el tunel)')
    elif mejor is None:
        log('montana-coche: sin sitio libre a la derecha del tunel, omitida')
    else:
        coste, x, y, s_c = mejor
        # base al minimo del terreno bajo la huella (no flota en la ladera)
        zt = min(z_terreno(x + dx, y + dy) for dx in (-55, 0, 55) for dy in (-40, 0, 40))
        rock = pt.build(LIB, largo=150, ancho=95, alto=30, seed=13)
        r2 = clone(rock, (x, y, max(zt, 0.5) - 4.0), rot_facing_road(s_c, -1))
        r2.name = 'PENON_lado_derecho'
        bpy.context.view_layer.update()
        mesh2 = max((o for o in [r2] + r2.children_recursive if o.type == 'MESH'),
                    key=lambda o: len(o.data.vertices))
        nb2 = _limpiar_bajo_roca(mesh2)
        log('montana-coche a la derecha del tunel en (%.0f, %.0f), a %.0f m de la boca; '
            '%d objetos retirados de debajo' % (x, y, coste, nb2))
safe('zona_tunel', zona_tunel)

# ============ RUEDA FOSIL GIGANTE EN EL ACANTILADO (como en la peli) ============
def zona_rueda_fosil():
    """Rueda de piedra tallada en la pared del acantilado, sobre la boca de
    entrada del tunel, a la derecha de la carretera (Portocorsacircuit2)."""
    s_a = CURVAS[2]['s_idx'] * paso
    s_b = CURVAS[3]['s_idx'] * paso
    s_mid = (s_a + s_b) / 2 + 20
    s_w = TUNEL_INFO.get('s_in', s_mid - 72) + 2  # justo sobre el portal de entrada
    p = frame(s_w)
    t = tangent(s_w)
    n = (p['nx'], p['ny'])
    cx_ = p['x'] - n[0] * 15.0
    cy_ = p['y'] - n[1] * 15.0
    cz_ = p['z'] + 21.0
    R, r = 12.0, 2.0
    # ejes del plano de la rueda: horizontal = normal de la pista, vertical = z
    ex = (n[0], n[1], 0.0)
    ez = (0.0, 0.0, 1.0)
    ax = (t[0], t[1], 0.0)  # eje de la rueda (mira a los coches que llegan)
    verts, faces = [], []
    NA, NB = 32, 8
    for i in range(NA):
        a = 2 * math.pi * i / NA
        ccx = cx_ + (ex[0] * math.cos(a) + ez[0] * math.sin(a)) * R
        ccy = cy_ + (ex[1] * math.cos(a) + ez[1] * math.sin(a)) * R
        ccz = cz_ + (ex[2] * math.cos(a) + ez[2] * math.sin(a)) * R
        rad = (ex[0] * math.cos(a) + ez[0] * math.sin(a),
               ex[1] * math.cos(a) + ez[1] * math.sin(a),
               ex[2] * math.cos(a) + ez[2] * math.sin(a))
        for j in range(NB):
            b = 2 * math.pi * j / NB
            verts.append((ccx + (rad[0] * math.cos(b) + ax[0] * math.sin(b)) * r,
                          ccy + (rad[1] * math.cos(b) + ax[1] * math.sin(b)) * r,
                          ccz + (rad[2] * math.cos(b) + ax[2] * math.sin(b)) * r))
    for i in range(NA):
        for j in range(NB):
            a0 = i * NB + j
            a1 = i * NB + (j + 1) % NB
            b0 = ((i + 1) % NA) * NB + j
            b1 = ((i + 1) % NA) * NB + (j + 1) % NB
            faces.append((a0, a1, b1, b0))
    # radios (cajas) y buje
    def caja(c, u, v, w, lu, lv, lw):
        base = len(verts)
        for su in (-1, 1):
            for sv in (-1, 1):
                for sw in (-1, 1):
                    verts.append((c[0] + u[0] * su * lu + v[0] * sv * lv + w[0] * sw * lw,
                                  c[1] + u[1] * su * lu + v[1] * sv * lv + w[1] * sw * lw,
                                  c[2] + u[2] * su * lu + v[2] * sv * lv + w[2] * sw * lw))
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            faces.append(tuple(base + k for k in f))
    for i in range(10):
        a = 2 * math.pi * i / 10
        rad = (ex[0] * math.cos(a) + ez[0] * math.sin(a),
               ex[1] * math.cos(a) + ez[1] * math.sin(a),
               ex[2] * math.cos(a) + ez[2] * math.sin(a))
        perp = (ax[1] * rad[2] - ax[2] * rad[1], ax[2] * rad[0] - ax[0] * rad[2],
                ax[0] * rad[1] - ax[1] * rad[0])
        c = (cx_ + rad[0] * R * 0.5, cy_ + rad[1] * R * 0.5, cz_ + rad[2] * R * 0.5)
        caja(c, rad, perp, ax, R * 0.5, 0.7, 1.4)
    caja((cx_, cy_, cz_), ex, ez, ax, 3.2, 3.2, 2.2)
    me = bpy.data.meshes.new('RUEDA_fosil')
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    m_pie = bpy.data.materials.get('MAT_piedra')
    if m_pie:
        me.materials.append(m_pie)
    ob = bpy.data.objects.new('RUEDA_fosil', me)
    root_col.objects.link(ob)
    log('rueda fosil tallada sobre la boca del tunel')
if M.get('montana_rueda') is None:
    safe('zona_rueda_fosil', zona_rueda_fosil)   # con la montana-rueda la rueda va tallada en ella

# ============ MONTANA-COCHE AL FINAL DEL PUENTE (42-44) ============
PUENTE_INFO = {}

def zona_penon_puente():
    """La montana-pueblo va DENTRO del gran lazo del viaducto (curvas 42-44): el
    circuito la rodea, como en la ilustracion de la pelicula."""
    import numpy as _np
    pt = M.get('penon_cara') or M['penon_topolino']
    i42, i44 = CURVAS[42]['s_idx'], CURVAS[44]['s_idx']
    P = _np.array([[S[i]['x'], S[i]['y']] for i in range(i42, i44, 2)])
    A = _np.column_stack([2 * P[:, 0], 2 * P[:, 1], _np.ones(len(P))])
    a_, b_, c_ = _np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)[0]
    cx, cy = float(a_), float(b_)
    # el centro que maximiza la holgura a la pista (busqueda local)
    def holgura(x, y):
        return min(math.hypot(x - S[i]['x'], y - S[i]['y']) for i in range(0, N, 2))
    mejor = (holgura(cx, cy), cx, cy)
    for _ in range(3):
        for dx in (-12, 0, 12):
            for dy in (-12, 0, 12):
                h = holgura(mejor[1] + dx, mejor[2] + dy)
                if h > mejor[0] + 0.5:
                    mejor = (h, mejor[1] + dx, mejor[2] + dy)
    d_min, cx, cy = mejor
    fuerza = 0.35
    z_tab = max(S[i]['z'] for i in range(i42, i44))
    alto = max(72.0, z_tab + 36.0)
    # eje largo de la roca hacia la ABERTURA del lazo (por donde entran y salen
    # los dos ramales): es donde mas sitio hay
    ax_ = (S[i42]['x'] + S[i44]['x']) / 2 - cx
    ay_ = (S[i42]['y'] + S[i44]['y']) / 2 - cy
    hacia = math.atan2(ay_, ax_) + math.pi / 2   # rot = hacia - pi/2 -> eje X local = eje de la abertura
    semi = max(28.0, (d_min - 20.0) / 1.45)
    for intento in range(5):
        rock = pt.build(LIB, largo=2 * semi * 1.55, ancho=2 * semi * 0.98, alto=alto, seed=9, con_vegetacion=False)
        _a_meseta(rock, alto, fuerza=fuerza)
        r = clone(rock, (cx, cy, -5.0), hacia - math.pi / 2)
        bpy.context.view_layer.update()
        roca_m = max((o for o in [r] + list(r.children_recursive) if o.type == 'MESH'),
                     key=lambda o: len(o.data.vertices))
        # seguridad: la roca no puede tocar el tablero ni sus pilas (eje y +-9 m)
        inv_ = roca_m.matrix_world.inverted()
        pisa = 0
        for i in range(0, N, 2):
            q = S[i]
            if math.hypot(q['x'] - cx, q['y'] - cy) > d_min + 60:
                continue
            for lt in (-16.0, -9.0, 0.0, 9.0, 16.0):   # las pilas altas del viaducto se ensanchan en la base
                a2 = inv_ @ Vector((q['x'] + q['nx'] * lt, q['y'] + q['ny'] * lt, 400.0))
                b2 = inv_ @ Vector((q['x'] + q['nx'] * lt, q['y'] + q['ny'] * lt, -30.0))
                d2 = b2 - a2
                if roca_m.ray_cast(a2, d2.normalized(), distance=d2.length)[0]:
                    pisa += 1
        if pisa == 0:
            break
        for ch in list(r.children_recursive):
            bpy.data.objects.remove(ch, do_unlink=True)
        bpy.data.objects.remove(r, do_unlink=True)
        semi *= 0.86
    r.name = 'PENON_puente'
    PUENTE_INFO.update({'cx': cx, 'cy': cy, 'roca': roca_m, 'semi': semi, 'alto': alto,
                        'rot': hacia - math.pi / 2})
    log('montana-pueblo DENTRO del lazo del viaducto en (%.0f, %.0f): holgura %.0f m, '
        'semieje %.0f m, alto %.0f m, muestras de pista pisadas: %d' % (cx, cy, d_min, semi, alto, pisa))
if M.get('penon_pueblo') is None:
    safe('zona_penon_puente', zona_penon_puente)

# ============ ZOCALOS, CASAS DEL PENON Y ACUEDUCTO (ronda 8c) ============
def zona_zocalos():
    n = 0
    for ob in list(root_col.objects):
        if ob.parent is not None or not ob.name.startswith(
                ('AYTO_root', 'CAMPANILE_root', 'HOTEL_root', 'CARRERA_boxes', 'PIT_boxes',
                 'CARRERA_tribuna', 'CARRERA_pantalla')):
            continue
        bpy.context.view_layer.update()
        inv = ob.matrix_world.inverted()
        xs, ys = [], []
        for o2 in [ob] + list(ob.children_recursive):
            if o2.type != 'MESH':
                continue
            for c in o2.bound_box:
                l = inv @ (o2.matrix_world @ Vector(c))
                xs.append(l.x)
                ys.append(l.y)
        if not xs:
            continue
        esq = [ob.matrix_world @ Vector((x, y, 0.0))
               for x in (min(xs), max(xs)) for y in (min(ys), max(ys))]
        zmin_t = min(z_terreno(e.x, e.y) for e in esq)
        if ob.location.z - zmin_t > 0.3:
            _zocalo_global(ob, zmin_t - 1.0)
            n += 1
    log('zocalos bajo edificios grandes: %d' % n)
safe('zona_zocalos', zona_zocalos)

def zona_casas_penon():
    """Foto 'montana por dentro': el penon del casino va cubierto de casas en
    terrazas alrededor del casino, con zocalos altos clavados en la roca."""
    info = CASINO_INFO
    if not info:
        return
    roca_c = info['roca']
    cxc, cyc = info['cx'], info['cy']
    nb = _limpiar_bajo_roca(roca_c)
    ck_ = M['casas_kit']
    variantes = [ck_.build_casa(LIB, plantas=pl, ancho=an, fondo=fo, seed=70 + k)
                 for k, (pl, an, fo) in enumerate(((3, 10, 10), (4, 11, 10), (5, 9, 9),
                                                   (4, 13, 11), (3, 12, 10), (5, 11, 10)))]
    bpy.context.view_layer.update()
    inv_r = roca_c.matrix_world.inverted()
    rot_m = roca_c.matrix_world.to_3x3()
    puestas = []
    for anillo, (r0, r1, n_a) in enumerate(((50, 56, 22), (60, 68, 28), (72, 80, 34),
                                            (84, 94, 40), (98, 110, 44), (114, 126, 48))):
        for k in range(n_a):
            ang = 2 * math.pi * k / n_a + anillo * 0.37 + rnd.uniform(-0.06, 0.06)
            rr = rnd.uniform(r0, r1)
            lx, ly = rr * 1.4 * math.cos(ang), rr * math.sin(ang)
            wx = cxc + lx * math.cos(0.5) - ly * math.sin(0.5)
            wy = cyc + lx * math.sin(0.5) + ly * math.cos(0.5)
            a_ = inv_r @ Vector((wx, wy, 500.0))
            b_ = inv_r @ Vector((wx, wy, -20.0))
            d_ = b_ - a_
            hit, loc, nrm, fi = roca_c.ray_cast(a_, d_.normalized(), distance=d_.length)
            if not hit:
                continue
            wl = roca_c.matrix_world @ loc
            wn = (rot_m @ nrm).normalized()
            if wl.z < 9.0 or abs(wn.z) < 0.28:
                continue
            if min(math.hypot(wx - S[i]['x'], wy - S[i]['y']) for i in range(0, N, 3)) < 24:
                continue
            if any(math.hypot(wx - px, wy - py) < 11.0 for (px, py) in puestas):
                continue
            th = math.atan2(wy - cyc, wx - cxc)
            # la fachada se apoya en el punto MAS BAJO de su frente: nada de
            # casas sobre estacas; el resto del cuerpo queda empotrado en la roca
            zs_f = [wl.z]
            for e in (-5.5, 5.5):
                fx_, fy_ = wx - math.sin(th) * e, wy + math.cos(th) * e
                a2 = inv_r @ Vector((fx_, fy_, 500.0))
                b2 = inv_r @ Vector((fx_, fy_, -20.0))
                d2 = b2 - a2
                h2, l2, n2, f2 = roca_c.ray_cast(a2, d2.normalized(), distance=d2.length)
                zs_f.append((roca_c.matrix_world @ l2).z if h2 else wl.z - 6.0)
            if max(zs_f) - min(zs_f) > 6.0:
                continue
            # la roca no puede tragarse la casa: cota de la roca en el centro y en la
            # trasera del cuerpo (la casa mira hacia fuera; el cuerpo va hacia dentro)
            enterrada = False
            for (dist_, lim_) in ((5.0, 2.4), (9.5, 4.0)):   # casas de roca: max 2.4 m empotradas
                bx_, by_ = wx - math.cos(th) * dist_, wy - math.sin(th) * dist_
                a3 = inv_r @ Vector((bx_, by_, 500.0))
                b3 = inv_r @ Vector((bx_, by_, -20.0))
                d3 = b3 - a3
                h3, l3, n3, f3 = roca_c.ray_cast(a3, d3.normalized(), distance=d3.length)
                if h3 and (roca_c.matrix_world @ l3).z - min(zs_f) > lim_:
                    enterrada = True
            if enterrada:
                continue
            casa = clone(variantes[len(puestas) % len(variantes)], (wx, wy, min(zs_f) - 0.3),
                         th - math.pi / 2)
            casa.name = 'PENON_casa_roca'
            _zocalo_global(casa, min(zs_f) - 3.0)
            puestas.append((wx, wy))
    log('penon del casino: %d casas en terrazas (%d objetos retirados de debajo de la roca)'
        % (len(puestas), nb))
if M.get('penon_pueblo') is None:
    safe('zona_casas_penon', zona_casas_penon)

def zona_pueblo_penon_puente():
    """Casas en terrazas y un palazzo con campanile en la cima de la montana que
    rodea el viaducto (ilustracion 'montana por dentro')."""
    info = PUENTE_INFO
    if not info:
        return
    roca_c = info['roca']
    cx, cy, semi, rot = info['cx'], info['cy'], info['semi'], info['rot']
    ck_ = M['casas_kit']
    variantes = [ck_.build_casa(LIB, plantas=pl, ancho=an, fondo=fo, seed=170 + k)
                 for k, (pl, an, fo) in enumerate(((3, 9, 9), (4, 10, 9), (5, 9, 9),
                                                   (4, 11, 10), (3, 10, 9), (6, 10, 10)))]
    bpy.context.view_layer.update()
    inv_r = roca_c.matrix_world.inverted()
    rot_m = roca_c.matrix_world.to_3x3()

    def rayo(x, y):
        a_ = inv_r @ Vector((x, y, 600.0))
        b_ = inv_r @ Vector((x, y, -20.0))
        d_ = b_ - a_
        hit, loc, nrm, fi = roca_c.ray_cast(a_, d_.normalized(), distance=d_.length)
        if not hit:
            return None, None
        return (roca_c.matrix_world @ loc), (rot_m @ nrm).normalized()

    # hito en la cima: palazzo + campanile (la silueta que corona la roca)
    cima, _n = rayo(cx, cy)
    z_cima = cima.z if cima is not None else info['alto'] - 8.0
    pal = clone(lib['ayuntamiento'], (cx, cy, z_cima - 0.8), rot, scale=0.85)
    pal.name = 'PENON_palazzo'
    cam = clone(lib['campanile'], (cx + math.cos(rot) * 17.0, cy + math.sin(rot) * 17.0, z_cima - 1.0),
                rot, scale=0.9)
    cam.name = 'PENON_campanile'
    _zocalo_global(pal, z_cima - 4.0)
    puestas = []
    anillos = []
    r_ = 20.0
    while r_ < semi * 1.5:
        anillos.append((r_, r_ + 6.0, max(8, int(2 * math.pi * r_ / 12.5))))
        r_ += 11.0
    for anillo, (r0, r1, n_a) in enumerate(anillos):
        for k in range(n_a):
            ang = 2 * math.pi * k / n_a + anillo * 0.41 + rnd.uniform(-0.05, 0.05)
            rr = rnd.uniform(r0, r1)
            lx, ly = rr * 1.55 * math.cos(ang), rr * 0.98 * math.sin(ang)
            wx = cx + lx * math.cos(rot) - ly * math.sin(rot)
            wy = cy + lx * math.sin(rot) + ly * math.cos(rot)
            wl, wn = rayo(wx, wy)
            if wl is None or wl.z < 7.0 or abs(wn.z) < 0.30:
                continue
            if min(math.hypot(wx - S[i]['x'], wy - S[i]['y']) for i in range(0, N, 3)) < 20:
                continue
            if any(math.hypot(wx - px, wy - py) < 10.5 for (px, py) in puestas):
                continue
            th = math.atan2(wy - cy, wx - cx)
            zs_f = [wl.z]
            for e in (-5.0, 5.0):
                pl_, _nn = rayo(wx - math.sin(th) * e, wy + math.cos(th) * e)
                zs_f.append(pl_.z if pl_ is not None else wl.z - 6.0)
            if max(zs_f) - min(zs_f) > 6.0:
                continue
            enterrada = False
            for (dist_, lim_) in ((5.0, 2.4), (9.5, 4.0)):   # casas de roca: max 2.4 m empotradas
                pb_, _nb = rayo(wx - math.cos(th) * dist_, wy - math.sin(th) * dist_)
                if pb_ is not None and pb_.z - min(zs_f) > lim_:
                    enterrada = True
            if enterrada:
                continue
            casa = clone(variantes[len(puestas) % len(variantes)], (wx, wy, min(zs_f) - 0.3),
                         th - math.pi / 2)
            casa.name = 'PENON_casa_roca'
            _zocalo_global(casa, min(zs_f) - 3.0)
            puestas.append((wx, wy))
    log('montana del viaducto: palazzo + campanile en la cima (z=%.0f) y %d casas en terrazas'
        % (z_cima, len(puestas)))
if M.get('penon_pueblo') is None:
    safe('zona_pueblo_penon_puente', zona_pueblo_penon_puente)

def zona_rocas_pueblo():
    """Roca-pueblo DENTRO de la U del viaducto (curvas 42 -> 43 -> 44): contorno pegado
    al borde interior de la pista (6 m), cerrado por el lado abierto de la U;
    carretera en espiral, casas en las terrazas y palazzo/campanile arriba."""
    if M.get('penon_pueblo') is None:
        log('penon_pueblo no disponible: rocas antiguas')
        return
    i41, i42, i43 = CURVAS[42]['s_idx'], CURVAS[43]['s_idx'], CURVAS[44]['s_idx']   # (numeros de curva, no indices)
    ia, ib = i41 + 25, i43 - 70
    cxm = sum(S[i % N]['x'] for i in range(ia, ib + 1)) / float(ib - ia + 1)
    cym = sum(S[i % N]['y'] for i in range(ia, ib + 1)) / float(ib - ia + 1)
    pts = []
    for i in range(ia, ib + 1, 3):
        q = S[i % N]
        lado = 1.0 if ((cxm - q['x']) * q['nx'] + (cym - q['y']) * q['ny']) > 0 else -1.0
        d = q['w'] / 2 + 6.0
        pts.append((q['x'] + lado * q['nx'] * d, q['y'] + lado * q['ny'] * d))
    # cierre por el lado abierto: cuerda entre los extremos, metida hacia dentro
    (xa, ya), (xb, yb) = pts[0], pts[-1]
    mx_, my_ = (xa + xb) / 2, (ya + yb) / 2
    ux, uy = cxm - mx_, cym - my_
    l_ = math.hypot(ux, uy) or 1.0
    ux, uy = ux / l_, uy / l_
    pts = pts + [(xb + ux * 8, yb + uy * 8), (mx_ * 0.5 + xb * 0.5 + ux * 14, my_ * 0.5 + yb * 0.5 + uy * 14),
                 (mx_ + ux * 16, my_ + uy * 16), (mx_ * 0.5 + xa * 0.5 + ux * 14, my_ * 0.5 + ya * 0.5 + uy * 14),
                 (xa + ux * 8, ya + uy * 8)]
    area = sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
    if area < 0:
        pts = pts[::-1]
    pts = _contorno_libre(pts, 4.0)
    z_ter = [z_terreno(x, y) for (x, y) in pts]
    z_base = max(max(z_ter) + 0.3, float(G.get('nivel_mar', 0.0)) + 1.5)   # nunca bajo el mar
    z_tab = max(S[i % N]['z'] for i in range(i41, i43))
    z_top = max(z_tab + 34.0, z_base + 60.0)
    r, roca, info = _construir_roca_pueblo('PENON_puente', pts, altura=z_top - z_base, z_base=z_base,
                                           entrada_xy=(mx_ + ux * 4, my_ + uy * 4), seed=9, seed_casas=170, con_palazzo=True,
                                           profundidad=z_base - min(z_ter) + 8.0, ancho_lote=11.0, ocupacion=0.85,
                                           flares=(0.12, 0.05), bulto_fuera=3.0, bulto_pared=0.3, ancho_repisa=12.5, ancho_carretera=4.5,
                                           z_entrada=float(G.get('nivel_mar', 0.0)) + 1.6)
    PUENTE_INFO.update({'cx': info['centro_top'][0], 'cy': info['centro_top'][1], 'roca': roca, 'info': info})
    # seguridad: la roca no puede tocar el tablero ni el eje de las pilas
    inv_ = roca.matrix_world.inverted()
    pisa = 0
    for i in range(i41 - 10, i43 + 11, 2):
        q = S[i % N]
        for lt in (-(q['w'] / 2 + 1.0), 0.0, q['w'] / 2 + 1.0):
            a2 = inv_ @ Vector((q['x'] + q['nx'] * lt, q['y'] + q['ny'] * lt, 400.0))
            b2 = inv_ @ Vector((q['x'] + q['nx'] * lt, q['y'] + q['ny'] * lt, q['z'] - 2.0))
            d2 = b2 - a2
            if roca.ray_cast(a2, d2.normalized(), distance=d2.length)[0]:
                pisa += 1
    log('roca del lazo: base z=%.0f (terreno %.0f..%.0f), cima z=%.0f, %d vueltas, muestras de tablero pisadas: %d (debe ser 0)'
        % (z_base, min(z_ter), max(z_ter), z_top, info.get('n_terrazas', 0), pisa))
safe('zona_rocas_pueblo', zona_rocas_pueblo)

# ============ PASEO-MIRADOR Y PARKING EN LA AZOTEA ('las vistas') ============
def en_mirador(s_m, side):
    for m in (G.get('miradores') or []):
        if m['side'] == side and m['s0'] - 8 <= (s_m % L) <= m['s1'] + 8:
            return True
    return False


def zona_paseo_mirador():
    mirs = G.get('miradores') or []
    if not mirs:
        return
    mk = M.get('mirador_kit')
    ck = M.get('coches_kit')
    m_pav = _mat_simple('MAT_MIRADOR_pavimento_piedra', (0.40, 0.35, 0.28, 1))
    m_pie = _mat_simple('MAT_MIRADOR_piedra_paseo', (0.60, 0.54, 0.43, 1), 0.95)
    for m in mirs:
        s0, s1, side, ancho = m['s0'], m['s1'], m['side'], m['ancho']
        vs, fs, fm = [], [], []

        def seccion(s_m):
            q = frame(s_m)
            half = q['w'] / 2.0
            ze = q['z'] - q['lat'] * side * half
            def P(off, dz):
                l_ = side * (half + off)
                return Vector((q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, ze + dz))
            return {'kb': P(0.05, -0.06), 'kt': P(0.05, 0.10), 'dt': P(ancho - 0.5, 0.10),
                    'pi': P(ancho - 0.5, 1.05), 'po': P(ancho + 0.05, 1.05),
                    'ob': P(ancho + 0.05, -3.4), 'n': Vector((q['nx'] * side, q['ny'] * side, 0.0)),
                    'ze': ze}

        def quad(pts, want, mi):
            a, b, c, d = pts
            if (b - a).cross(d - a).dot(want) < 0:
                pts = [a, d, c, b]
            base = len(vs)
            vs.extend([tuple(p) for p in pts])
            fs.append(tuple(range(base, base + len(pts))))
            fm.append(mi)

        n_seg = int((s1 - s0) / 2.0)
        secs = [seccion(s0 + (s1 - s0) * k / n_seg) for k in range(n_seg + 1)]
        up = Vector((0, 0, 1))
        for k in range(n_seg):
            A, B = secs[k], secs[k + 1]
            quad([A['kb'], A['kt'], B['kt'], B['kb']], -A['n'], 1)     # bordillo
            quad([A['kt'], A['dt'], B['dt'], B['kt']], up, 0)          # pavimento
            quad([A['dt'], A['pi'], B['pi'], B['dt']], -A['n'], 1)     # pretil, cara interior
            quad([A['pi'], A['po'], B['po'], B['pi']], up, 1)          # pretil, coronacion
            quad([A['po'], A['ob'], B['ob'], B['po']], A['n'], 1)      # cara exterior + faldon
        for (A, sent) in ((secs[0], -1.0), (secs[-1], 1.0)):           # testeros
            t_ = Vector((A['n'].y, -A['n'].x, 0.0)) * (side * sent)
            base = len(vs)
            loop = [A['kb'], A['kt'], A['dt'], A['pi'], A['po'], A['ob']]
            nrm = (loop[1] - loop[0]).cross(loop[5] - loop[0])
            if nrm.dot(t_) < 0:
                loop = loop[::-1]
            vs.extend([tuple(p) for p in loop])
            fs.append(tuple(range(base, base + 6)))
            fm.append(1)
        me = bpy.data.meshes.new('MIRADOR_paseo')
        me.from_pydata(vs, [], fs)
        me.materials.append(m_pav)
        me.materials.append(m_pie)
        for poly, mi in zip(me.polygons, fm):
            poly.material_index = mi
        paseo = bpy.data.objects.new('MIRADOR_paseo', me)
        root_col.objects.link(paseo)

        # --- muro de arcadas bajo el borde exterior (piezas de 12 m, escalonadas) ---
        n_muro = 0
        if mk is not None:
            pieza = mk.build_muro_arcadas(LIB, largo=12.0, alto=13.0, n_arcos=2, seed=1)
            bpy.context.view_layer.update()
            ymax, zmax = -1e9, -1e9
            for ob in hierarchy(pieza):
                if ob.type == 'MESH':
                    for c in ob.bound_box:
                        w = ob.matrix_world @ Vector(c)
                        ymax = max(ymax, w.y)
                        zmax = max(zmax, w.z)
            s_c = s0 + 6.0
            while s_c <= s1 - 6.0 + 0.01:
                q = frame(s_c)
                half = q['w'] / 2.0
                z_low = min(seccion(s_c - 6.0)['ze'], seccion(s_c + 6.0)['ze'])
                l_ = side * (half + ancho + 0.05 + 0.12 - ymax)
                r = clone(pieza, (q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, z_low - 0.10 - zmax),
                          rot_facing_road(s_c, side) + math.pi)
                r.name = 'MIRADOR_muro_arcadas'
                n_muro += 1
                s_c += 12.0

        # --- coches-espectador y palmeras sobre el paseo ---
        n_filas = 0
        if ck is not None:
            filas_m = [ck.build_fila_aparcada(LIB, n=5, seed=20 + k) for k in range(3)]
            s_f = s0 + 24.0
            while s_f < s1 - 16.0:
                A = seccion(s_f)
                q = frame(s_f)
                l_ = side * (q['w'] / 2.0 + 7.5)
                r = clone(filas_m[n_filas % 3], (q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, A['ze'] + 0.11),
                          rot_facing_road(s_f, side), pitch=side * pendiente(s_f))
                r.name = 'MIRADOR_coches'
                n_filas += 1
                s_f += 40.0
        s_p = s0 + 5.0
        n_pal = 0
        while s_p < s1 - 3.0:
            A = seccion(s_p)
            q = frame(s_p)
            l_ = side * (q['w'] / 2.0 + ancho - 2.4)
            r = clone(lib['palmera' if n_pal % 2 else 'palmera2'],
                      (q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, A['ze'] + 0.08), rnd.uniform(0, 6.28))
            r.name = 'MIRADOR_palmera'
            n_pal += 1
            s_p += 20.0

        # --- palazzo con parking en la azotea, en la terraza inferior ---
        n_azotea = 0
        if mk is not None:
            s_k = (s0 + s1) / 2.0 + 12.0
            q = frame(s_k)
            half = q['w'] / 2.0
            ANCHO_P, FONDO_P = 40.0, 18.0
            l_ = side * (half + ancho + 7.0 + FONDO_P / 2.0)
            px_, py_ = q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_
            t = tangent(s_k)
            esq = [z_terreno(px_ + t[0] * a_ + q['nx'] * side * b_, py_ + t[1] * a_ + q['ny'] * side * b_)
                   for a_ in (-ANCHO_P / 2, ANCHO_P / 2) for b_ in (-FONDO_P / 2, FONDO_P / 2)]
            z_base = sum(esq) / 4.0 - 1.0
            z_azotea = seccion(s_k)['ze'] - 2.0          # la azotea queda 2 m bajo el paseo
            alto_p = max(10.0, min(24.0, z_azotea - z_base))
            pk_lib = mk.build_parking_terraza(LIB, ancho=ANCHO_P, fondo=FONDO_P, alto=alto_p, seed=3)
            pk = clone(pk_lib, (px_, py_, z_base), rot_facing_road(s_k, side))
            pk.name = 'MIRADOR_parking'
            _zocalo_global(pk, min(esq) - 1.0)
            bpy.context.view_layer.update()
            # fuera la vegetacion que quede dentro de la huella del palazzo
            inv_p = pk.matrix_world.inverted()
            for ob in list(root_col.objects):
                try:
                    if ob.parent is not None or not ob.name.startswith(('VEG_', 'OLI_')):
                        continue
                except ReferenceError:
                    continue
                lp = inv_p @ ob.matrix_world.translation
                if abs(lp.x) < ANCHO_P / 2 + 3 and abs(lp.y) < FONDO_P / 2 + 3:
                    for ch in list(ob.children_recursive):
                        bpy.data.objects.remove(ch, do_unlink=True)
                    bpy.data.objects.remove(ob, do_unlink=True)
            if ck is not None:
                unos = [ck.build_fila_aparcada(LIB, n=1, seed=40 + k) for k in range(8)]
                for k, (bx, by, bz, brz) in enumerate(mk.plazas_parking(ANCHO_P, FONDO_P, alto_p)):
                    if k % 7 == 5:
                        continue                     # alguna plaza libre
                    w = pk.matrix_world @ Vector((bx, by, bz + 0.02))
                    r = clone(unos[k % len(unos)], (w.x, w.y, w.z), pk.rotation_euler.z + brz)
                    r.name = 'MIRADOR_coche_azotea'
                    n_azotea += 1
        log('paseo-mirador s=%d..%d: %d piezas de muro de arcadas, %d filas de coches, %d palmeras, '
            '%d coches en la azotea del parking' % (s0, s1, n_muro, n_filas, n_pal, n_azotea))
safe('zona_paseo_mirador', zona_paseo_mirador)

# ============ RED DE CAMINOS (ronda 13): "mini ciudad funcional" ============
# Carreteras secundarias, calles del pueblo, paddock, muelle, senderos de montana;
# cada empalme con la pista lleva VALLA DE CIERRE (peticion del usuario) y cartel.
CAMINOS_INFO = {'caminos': 0, 'vallas': 0, 'carteles': 0, 'despejados': 0, 'tramos': []}


def _densificar(pts, paso_c=3.0, z_extra=0.28, suavizar=3, z_ini=None, z_fin=None):
    """[(x, y)] -> [(x, y, z)] cada paso_c m; z = terreno + z_extra (suavizado).
    Con z_ini/z_fin la cota se interpola linealmente (rampas cortas entre dos cotas)."""
    out = []
    for k in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[k][:2], pts[k + 1][:2]
        l_ = math.hypot(x1 - x0, y1 - y0)
        n_ = max(1, int(l_ / paso_c))
        for j in range(n_):
            f = j / float(n_)
            out.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
    out.append(tuple(pts[-1][:2]))
    if z_ini is not None and z_fin is not None:
        n_ = len(out)
        zs = [z_ini + (z_fin - z_ini) * (k / float(max(1, n_ - 1))) for k in range(n_)]
        return [(x, y, z) for (x, y), z in zip(out, zs)]
    zs = [z_terreno(x, y) + z_extra for (x, y) in out]
    for _ in range(suavizar):
        zs = [zs[0]] + [(zs[i - 1] + 2 * zs[i] + zs[i + 1]) / 4.0 for i in range(1, len(zs) - 1)] + [zs[-1]]
    zs = [max(z, z_terreno(x, y) + 0.12) for (x, y), z in zip(out, zs)]
    return [(x, y, z) for (x, y), z in zip(out, zs)]


def _sin_pliegues(pts, d_min=3.0):
    """Quita los puntos de una polilinea desplazada que retroceden (interior de una
    curva cerrada: la calle o el muro se plegaban en 'aletas')."""
    out = []
    for p_ in pts:
        if not out:
            out.append(p_)
            continue
        dx, dy = p_[0] - out[-1][0], p_[1] - out[-1][1]
        d = math.hypot(dx, dy)
        if d < d_min:
            continue
        if len(out) >= 2:
            ex, ey = out[-1][0] - out[-2][0], out[-1][1] - out[-2][1]
            e = math.hypot(ex, ey) or 1.0
            if (dx * ex + dy * ey) / (d * e) < 0.25:
                continue
        out.append(p_)
    return out


def _despejar_camino(pts3, ancho):
    """Quita arboles, casas, coches y farolas que pisaria el camino."""
    prefijos = ('VEG_', 'OLI_', 'CASAS_', 'COCHE_', 'CALLE_', 'CARRERA_paca', 'PUEBLO_')
    n_ = 0
    xs = [p[0] for p in pts3]
    ys = [p[1] for p in pts3]
    for ob in list(root_col.objects):
        try:
            if ob.parent is not None or not ob.name.startswith(prefijos):
                continue
            x, y = ob.location.x, ob.location.y
        except ReferenceError:
            continue
        margen = 4.5 if ob.name.startswith('CASAS_') else 2.6   # (las filas van a 7.5 m del eje de la calle trasera)
        lim = ancho / 2.0 + margen
        cerca = False
        for k in range(len(xs)):
            if abs(xs[k] - x) < lim and abs(ys[k] - y) < lim and math.hypot(xs[k] - x, ys[k] - y) < lim:
                cerca = True
                break
        if cerca:
            for ch in list(ob.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(ob, do_unlink=True)
            n_ += 1
    CAMINOS_INFO['despejados'] += n_
    return n_


def _cinta_simple(nombre, pts3, ancho, rgba):
    """Cinta plana (reserva por si falta caminos_kit)."""
    m = _mat_simple('MAT_CAMINO_' + nombre.lower(), rgba, 0.9)
    vs, fs = [], []
    for k, (x, y, z) in enumerate(pts3):
        k2 = min(k + 1, len(pts3) - 1)
        k1 = max(k - 1, 0)
        tx, ty = pts3[k2][0] - pts3[k1][0], pts3[k2][1] - pts3[k1][1]
        l_ = math.hypot(tx, ty) or 1.0
        nx_, ny_ = -ty / l_, tx / l_
        vs.append((x + nx_ * ancho / 2, y + ny_ * ancho / 2, z))
        vs.append((x - nx_ * ancho / 2, y - ny_ * ancho / 2, z))
    for k in range(len(pts3) - 1):
        o = 2 * k
        fs.append((o, o + 2, o + 3, o + 1))
    me = bpy.data.meshes.new('CAMINO_' + nombre)
    me.from_pydata(vs, [], fs)
    me.materials.append(m)
    ob = bpy.data.objects.new('CAMINO_' + nombre, me)
    root_col.objects.link(ob)
    return ob


def _terraplen(pts3, ancho):
    """Relleno de piedra (talud 1:1) desde los bordes del camino hasta el terreno: un
    camino en rampa entre dos cotas ya no flota como una losa."""
    m = _mat_simple('MAT_CAMINO_terraplen', (0.46, 0.42, 0.35, 1), 0.95)
    vs, fs = [], []
    n_ = 0
    for k, (x, y, z) in enumerate(pts3):
        k2 = min(k + 1, len(pts3) - 1)
        k1 = max(k - 1, 0)
        tx, ty = pts3[k2][0] - pts3[k1][0], pts3[k2][1] - pts3[k1][1]
        l_ = math.hypot(tx, ty) or 1.0
        nx_, ny_ = -ty / l_, tx / l_
        for sg in (1.0, -1.0):
            xa, ya = x + sg * nx_ * ancho / 2, y + sg * ny_ * ancho / 2
            h = max(0.0, z - 0.05 - z_terreno(xa, ya))
            xb, yb = xa + sg * nx_ * (h * 0.9 + 0.4), ya + sg * ny_ * (h * 0.9 + 0.4)
            vs.append((xa, ya, z - 0.05))
            vs.append((xb, yb, z_terreno(xb, yb) - 0.8))
        # 4 vertices por muestra: [der_arriba, der_abajo, izq_arriba, izq_abajo]
    for k in range(len(pts3) - 1):
        o = 4 * k
        fs.append((o, o + 4, o + 5, o + 1))          # talud derecho
        fs.append((o + 2, o + 3, o + 7, o + 6))      # talud izquierdo
        fs.append((o + 1, o + 5, o + 7, o + 3))      # fondo (bajo el terreno)
    o0, o1 = 0, 4 * (len(pts3) - 1)
    fs.append((o0, o0 + 1, o0 + 3, o0 + 2))
    fs.append((o1, o1 + 2, o1 + 3, o1 + 1))
    me = bpy.data.meshes.new('CAMINO_terraplen')
    me.from_pydata(vs, [], fs)
    me.materials.append(m)
    import bmesh as _bm
    bb = _bm.new()
    bb.from_mesh(me)
    _bm.ops.recalc_face_normals(bb, faces=bb.faces)
    bb.to_mesh(me)
    bb.free()
    ob = bpy.data.objects.new('CAMINO_terraplen', me)
    root_col.objects.link(ob)
    return ob


def _camino(pts, ancho=5.0, tipo='asfalto', despejar=True, z_fijo=None, z_ini=None, z_fin=None, muro=False, terraplen=False):
    if z_fijo is not None:
        pts3 = _densificar(pts, z_ini=z_fijo, z_fin=z_fijo)
    else:
        pts3 = _densificar(pts, z_ini=z_ini, z_fin=z_fin)
    if len(pts3) < 2:
        return pts3, None
    if despejar:
        _despejar_camino(pts3, ancho)
    ck = M.get('caminos_kit')
    r = None
    if ck is not None and hasattr(ck, 'build_camino'):
        try:
            ob = ck.build_camino(LIB, pts3, ancho=ancho, tipo=tipo, seed=CAMINOS_INFO['caminos'])
            r = clone(ob, (0.0, 0.0, 0.0), 0.0)
            r.name = 'CAMINO_' + tipo
        except Exception as e:
            log('caminos_kit.build_camino fallo (%s): cinta simple' % e)
            r = None
    if r is None:
        col_ = {'asfalto': (0.22, 0.22, 0.23, 1), 'tierra': (0.62, 0.50, 0.32, 1),
                'adoquin': (0.55, 0.50, 0.48, 1), 'muelle': (0.60, 0.57, 0.50, 1)}[tipo]
        r = _cinta_simple(tipo, pts3, ancho, col_)
    if muro and ck is not None and hasattr(ck, 'build_muro_contencion'):
        try:
            # muro en el borde de aguas abajo (lado con terreno mas bajo)
            lado_b = []
            for k, (x, y, z) in enumerate(pts3):
                k2 = min(k + 1, len(pts3) - 1)
                k1 = max(k - 1, 0)
                tx, ty = pts3[k2][0] - pts3[k1][0], pts3[k2][1] - pts3[k1][1]
                l_ = math.hypot(tx, ty) or 1.0
                nx_, ny_ = -ty / l_, tx / l_
                za = z_terreno(x + nx_ * ancho * 0.6, y + ny_ * ancho * 0.6)
                zb = z_terreno(x - nx_ * ancho * 0.6, y - ny_ * ancho * 0.6)
                sg = 1.0 if za < zb else -1.0
                lado_b.append((x + sg * nx_ * (ancho / 2 + 0.3), y + sg * ny_ * (ancho / 2 + 0.3), z - 0.05))
            mw = ck.build_muro_contencion(LIB, lado_b, alto=1.4, seed=CAMINOS_INFO['caminos'])
            mm = clone(mw, (0.0, 0.0, 0.0), 0.0)
            mm.name = 'CAMINO_muro'
        except Exception as e:
            log('muro de contencion fallo: %s' % e)
    if terraplen:
        _terraplen(pts3, ancho)
    CAMINOS_INFO['caminos'] += 1
    CAMINOS_INFO['tramos'].append((tipo, len(pts3)))
    return pts3, r


def _valla_cierre(px, py, z, rot, texto=None):
    ck = M.get('caminos_kit')
    if ck is None or not hasattr(ck, 'build_valla_cierre'):
        # reserva: valla del kit de carrera si existe
        if 'valla' in lib:
            v = clone(lib['valla'], (px, py, z), rot)
            v.name = 'CAMINO_valla'
        return
    v = ck.build_valla_cierre(LIB, ancho=6.0, seed=CAMINOS_INFO['vallas'])
    vv = clone(v, (px, py, z), rot)
    vv.name = 'CAMINO_valla'
    CAMINOS_INFO['vallas'] += 1


def _cartel(px, py, z, rot, texto):
    ck = M.get('caminos_kit')
    if ck is None or not hasattr(ck, 'build_cartel'):
        return
    try:
        c = ck.build_cartel(LIB, texto=texto, seed=CAMINOS_INFO['carteles'])
        cc = clone(c, (px, py, z), rot)
        cc.name = 'CAMINO_cartel'
        CAMINOS_INFO['carteles'] += 1
    except Exception as e:
        log('cartel %s fallo: %s' % (texto, e))


def _empalme(s_j, side, texto=None, con_valla=True):
    """Boca de un camino lateral en la pista: punto del borde (peraltado), valla
    de cierre cruzando la boca a 3.2 m del borde y cartel direccional."""
    q = frame(s_j)
    d0 = q['w'] / 2 + 0.25
    z_b = q['z'] - q['lat'] * side * (q['w'] / 2)
    px, py = q['x'] + side * q['nx'] * d0, q['y'] + side * q['ny'] * d0
    tx, ty = q['ny'], -q['nx']
    rot_valla = math.atan2(side * q['ny'], side * q['nx']) - math.pi / 2    # +Y = hacia el camino lateral
    if con_valla:
        vx, vy = q['x'] + side * q['nx'] * (d0 + 3.2), q['y'] + side * q['ny'] * (d0 + 3.2)
        _valla_cierre(vx, vy, max(z_terreno(vx, vy), z_b - 0.4), rot_valla, texto)
    if texto:
        cx_, cy_ = q['x'] + side * q['nx'] * (d0 + 4.0) + tx * 5.0, q['y'] + side * q['ny'] * (d0 + 4.0) + ty * 5.0
        _cartel(cx_, cy_, max(z_terreno(cx_, cy_), z_b - 0.4), math.atan2(-side * q['ny'], -side * q['nx']) - math.pi / 2, texto)
    return (px, py), z_b


def _muestra_mas_cercana(x, y, solo_tierra=False):
    mejor, ib = 1e18, 0
    for i in range(0, N, 2):
        q = S[i]
        if solo_tierra and q.get('sec') == 'bridge':
            continue
        d = (q['x'] - x) ** 2 + (q['y'] - y) ** 2
        if d < mejor:
            mejor, ib = d, i
    return ib, math.sqrt(mejor)


def _lado_de(x, y, i):
    q = S[i]
    return 1.0 if ((x - q['x']) * q['nx'] + (y - q['y']) * q['ny']) > 0 else -1.0


def _mejor_mirador(x0, y0, dx, dy, d_min=150.0, d_max=340.0, abanico=60.0):
    """Punto de terreno mas alto en un abanico desde (x0,y0) en la direccion (dx,dy),
    a >= 40 m de la pista y fuera de las montanas de fondo (rayo contra MONT_*)."""
    import numpy as _np
    dg = bpy.context.evaluated_depsgraph_get()
    mejor = None
    a0 = math.atan2(dy, dx)
    # lejos del pueblo (la ermita acababa metida entre las casas de las terrazas)
    casas_xy = [(o.location.x, o.location.y) for o in root_col.objects if o.name.startswith('CASAS_casa') and o.parent is None]
    for da in range(-int(abanico), int(abanico) + 1, 5):
        a_ = a0 + math.radians(da)
        for d in range(int(d_min), int(d_max) + 1, 12):
            x, y = x0 + math.cos(a_) * d, y0 + math.sin(a_) * d
            z = z_terreno(x, y)
            if z < 3.0:
                continue
            i_, dp = _muestra_mas_cercana(x, y)
            if dp < 40.0:
                continue
            if any(abs(cx_ - x) < 40 and abs(cy_ - y) < 40 and math.hypot(cx_ - x, cy_ - y) < 40.0 for (cx_, cy_) in casas_xy):
                continue
            hit, loc, nrm, idx_, ob, mat = bpy.context.scene.ray_cast(dg, Vector((x, y, 500.0)), Vector((0, 0, -1)), distance=600.0)
            if hit and ob is not None and ob.name.startswith(('MONT', 'PENON', 'TUNEL', 'MRUEDA', 'MCOCHE', 'PPUEBLO')):
                continue
            if pendiente_terreno(x, y) > 0.55:
                continue
            if mejor is None or z > mejor[2]:
                mejor = (x, y, z)
    return mejor


def zona_caminos():
    ck = M.get('caminos_kit')
    log('caminos: kit %s' % ('caminos_kit' if ck is not None else 'NO disponible (cintas simples)'))
    # ---------- 1) espolon del casino: cresta 37 <-> carretera de la roca del casino
    ent = CASINO_INFO.get('entrada')
    if ent is not None:
        # el empalme va en la CRESTA (curvas 36-38), nunca en la bajada recta a la rotonda
        i_36, i_38 = CURVAS[36]['s_idx'], CURVAS[38]['s_idx']
        i_j = min(range(i_36 - 30, i_38 + 4, 2), key=lambda i: (S[i % N]['x'] - ent[0]) ** 2 + (S[i % N]['y'] - ent[1]) ** 2) % N
        d_j = math.hypot(S[i_j]['x'] - ent[0], S[i_j]['y'] - ent[1])
        side = _lado_de(ent[0], ent[1], i_j)
        (pb, z_b) = _empalme(i_j * paso, side, 'CASINO')
        _camino([pb, (ent[0], ent[1])], ancho=6.0, tipo='asfalto', z_ini=z_b, z_fin=float(ent[2]) + 0.1, terraplen=True)
        log('caminos: espolon del casino en s=%d (%.0f m)' % (i_j * paso, d_j))
    # ---------- 2) roca del lazo: muelle con pantalan + puente a la carretera de la roca desde el viaducto
    pinfo = PUENTE_INFO.get('info')
    if pinfo and pinfo.get('entrada'):
        ex, ey, ez = pinfo['entrada']
        ctx_, cty_ = pinfo['centro_top']
        ux, uy = ex - ctx_, ey - cty_
        l_ = math.hypot(ux, uy) or 1.0
        ux, uy = ux / l_, uy / l_
        zm = float(G.get('nivel_mar', 0.0)) + 1.6
        fin = (ex + ux * 46.0, ey + uy * 46.0)
        _camino([(ex, ey), fin], ancho=6.0, tipo='muelle', despejar=False, z_fijo=zm)
        if 'pantalan' in lib:
            pt_ = clone(lib['pantalan'], (fin[0] + ux * 19.0, fin[1] + uy * 19.0, 0.0), math.atan2(uy, ux) + math.pi / 2)
            pt_.name = 'PUERTO_pantalan_roca'
        if 'velero' in lib:
            for k in range(3):
                b_ = clone(lib['velero'], (fin[0] + ux * (12.0 + 12.0 * k) - uy * 9.0 * (1 if k % 2 else -1), fin[1] + uy * (12.0 + 12.0 * k) + ux * 9.0 * (1 if k % 2 else -1), 0.0),
                           math.atan2(uy, ux) + rnd.uniform(-0.3, 0.3))
                b_.name = 'PUERTO_velero_roca'
        _cartel(ex + ux * 3.0 - uy * 4.5, ey + uy * 3.0 + ux * 4.5, zm, math.atan2(-uy, -ux) - math.pi / 2, 'PUERTO')
        # puente corto al tablero del viaducto donde coinciden las cotas
        mejor = None
        deck = [i for i in range(0, N, 2) if S[i].get('sec') == 'bridge']
        for (mx_, my_, mz_) in pinfo.get('muestras_carretera', [])[::3]:
            for i in deck:
                q = S[i]
                dxy = math.hypot(q['x'] - mx_, q['y'] - my_)
                if 9.0 < dxy < 26.0 and abs(q['z'] - mz_) < 1.6:
                    sc_ = dxy + 6.0 * abs(q['z'] - mz_)
                    if mejor is None or sc_ < mejor[0]:
                        mejor = (sc_, i, (mx_, my_, mz_))
        if mejor is not None:
            _, i_d, (mx_, my_, mz_) = mejor
            side = _lado_de(mx_, my_, i_d)
            (pb, z_b) = _empalme(i_d * paso, side, 'PUEBLO', con_valla=True)
            _camino([pb, (mx_, my_)], ancho=5.0, tipo='asfalto', despejar=False, z_ini=z_b, z_fin=mz_ + 0.05, terraplen=True)
            log('caminos: puente de la roca del lazo al viaducto en s=%d' % (i_d * paso))
        else:
            log('caminos: sin punto de empalme roca-viaducto (cotas no coinciden)')
    # ---------- 3) paddock detras de los boxes + subida al hotel
    if PIT_INFO.get('s_c') is not None:
        s_c, largo = PIT_INFO['s_c'], PIT_INFO['largo']
        def _ps(s_, lat_):
            q = frame(s_ % L)
            return (q['x'] - q['nx'] * lat_, q['y'] - q['ny'] * lat_)
        pad = [_ps(s_c - largo / 2 - 34, 17.6), _ps(s_c - largo / 2 - 18, 24.0), _ps(s_c - largo / 2 - 1, 37.0),
               _ps(s_c, 37.0), _ps(s_c + largo / 2 + 1, 37.0), _ps(s_c + largo / 2 + 18, 24.0), _ps(s_c + largo / 2 + 34, 17.6)]
        _camino(pad, ancho=6.0, tipo='asfalto', despejar=True)
        q0 = frame((s_c - largo / 2 - 34) % L)
        _cartel(*_ps(s_c - largo / 2 - 30, 20.5), z_terreno(*_ps(s_c - largo / 2 - 30, 20.5)), math.atan2(q0['ny'], q0['nx']), 'PADDOCK')
        # zigzag al hotel (queda ladera arriba, detras del complejo)
        hotel = [_ps(s_c + 8, 37.0), _ps(s_c + 95, 50.0), _ps(s_c + 60, 64.0), _ps(s_c - 30, 70.0), _ps(120, 79.0)]
        _camino(hotel, ancho=5.0, tipo='asfalto', despejar=True, muro=True)
        _cartel(*_ps(s_c + 20, 41.0), z_terreno(*_ps(s_c + 20, 41.0)), math.atan2(q0['ny'], q0['nx']), 'HOTEL')
        log('caminos: paddock (%.0f m) y subida al hotel' % (largo + 68))
    # ---------- 4) calles del pueblo: calle trasera entre filas + travesias a la pista
    sectores = [(660, 1085, -1, (25.5, 45.5, 65.5)), (1285, 1525, -1, (25.5, 45.5, 65.5)), (2515, 2735, -1, (25.5, 45.5)),
                (3195, 3445, -1, (25.5, 45.5)), (3195, 3445, 1, (25.5, 45.5)), (830, 1080, 1, (25.5, 45.5))]
    n_trav = 0
    for (s0, s1, side, offs) in sectores:
        travesias = list(range(int(s0) + 20, int(s1) - 20, 150))
        for off in offs:
            pts = _sin_pliegues([pos_side(s_, side, off)[0][:2] for s_ in range(int(s0) + 20, int(s1) - 18, 8)], 4.0)
            if len(pts) > 3:
                _camino(pts, ancho=4.4, tipo='adoquin', despejar=True)
        for s_t in travesias:
            (pb, z_b) = _empalme(s_t, side, 'CENTRO' if s_t == travesias[0] else None)
            pts = [pb] + [pos_side(s_t, side, off)[0][:2] for off in offs]
            _camino(pts, ancho=4.0, tipo='adoquin', despejar=True, z_ini=z_b, z_fin=z_terreno(*pts[-1]) + 0.25)
            n_trav += 1
    log('caminos: calles del pueblo en %d sectores, %d travesias con valla' % (len(sectores), n_trav))
    # muros de piedra en el borde de cada terraza (la ciudad de ladera se lee como bancales)
    n_mur = 0
    if ck is not None and hasattr(ck, 'build_muro_contencion'):
        # (mismos s0/s1 que 'sectores' para que los cortes coincidan con las travesias)
        TERR = [(660, 1085, -1, (28.0, 48.0, 68.0)), (1285, 1525, -1, (28.0, 48.0, 68.0)), (2515, 2735, -1, (28.0, 48.0)),
                (3195, 3445, -1, (28.0, 48.0)), (3195, 3445, 1, (28.0, 48.0)), (830, 1080, 1, (28.0, 48.0))]
        for (s0, s1, side, bordes) in TERR:
            # las travesias (cada 150 m desde s0+30) cortan el muro: tramos entre ellas
            cortes = [s_t for s_t in range(int(s0) + 20, int(s1) - 20, 150)]
            for off in bordes:
                tramos_m = []
                pts = []
                for s_ in range(int(s0), int(s1) + 1, 5):
                    if any(abs(s_ - s_t) < 5.0 for s_t in cortes):
                        if len(pts) > 2:
                            tramos_m.append(pts)
                        pts = []
                        continue
                    (pp_, _) = pos_side(s_, side, off + 2.6)
                    pts.append((pp_[0], pp_[1], z_terreno(pp_[0], pp_[1]) - 0.1))
                if len(pts) > 2:
                    tramos_m.append(pts)
                tramos_m = [_sin_pliegues(t_, 3.0) for t_ in tramos_m]
                for pts in tramos_m:
                    if len(pts) < 3:
                        continue
                    try:
                        mw = ck.build_muro_contencion(LIB, pts, alto=6.4, seed=n_mur)
                        mm = clone(mw, (0.0, 0.0, 0.0), 0.0)
                        mm.name = 'CAMINO_muro'
                        n_mur += 1
                    except Exception as e:
                        log('muro de terraza fallo: %s' % e)
    log('caminos: %d muros de terraza' % n_mur)
    # ---------- 5) carretera del puerto (recta de meta -> dique-tapacubos)
    try:
        p0 = frame(60)
        cxp, cyp = p0['x'] + p0['nx'] * 190, p0['y'] + p0['ny'] * 190
        (pb, z_b) = _empalme(40, 1, 'PORTO')
        # por tierra hasta la orilla, luego escollera hasta el dique (radio 145)
        ux, uy = cxp - pb[0], cyp - pb[1]
        l_ = math.hypot(ux, uy) or 1.0
        ux, uy = ux / l_, uy / l_
        d_or = 0.0
        while d_or < l_ - 150 and z_terreno(pb[0] + ux * d_or, pb[1] + uy * d_or) > 0.6:
            d_or += 3.0
        orilla = (pb[0] + ux * d_or, pb[1] + uy * d_or)
        _camino([pb, orilla], ancho=5.5, tipo='asfalto', despejar=True, z_ini=z_b, z_fin=max(z_terreno(*orilla), 0.9) + 0.2)
        fin_d = (cxp - ux * 139.0, cyp - uy * 139.0)
        _camino([orilla, fin_d], ancho=5.5, tipo='muelle', despejar=False, z_fijo=float(G.get('nivel_mar', 0.0)) + 1.6)
        log('caminos: carretera del puerto %.0f m por tierra + %.0f m de escollera' % (d_or, math.hypot(fin_d[0] - orilla[0], fin_d[1] - orilla[1])))
    except Exception as e:
        log('caminos: puerto fallo: %s' % e)
    # ---------- 6) senderos de montana (tierra) hacia miradores
    senderos = [(1180, -1, 'ERMITA'), (CURVAS[15]['s_idx'] * paso, None, 'CIMA')]
    for (s_s, side, texto) in senderos:
        q = frame(s_s)
        if side is None:
            side = -1.0 if q['lat'] < 0 else 1.0    # exterior de la curva
            side = -side
        (pb, z_b) = _empalme(s_s, side, texto)
        dx, dy = side * q['nx'], side * q['ny']
        mir = _mejor_mirador(pb[0], pb[1], dx, dy)
        if mir is None:
            log('caminos: sin mirador para el sendero de s=%d' % s_s)
            continue
        # zigzag de 3 tramos hacia el mirador
        mx_, my_ = mir[0], mir[1]
        tx, ty = -dy, dx
        pts = [pb, (pb[0] + dx * 30 + tx * 25, pb[1] + dy * 30 + ty * 25),
               (pb[0] + (mx_ - pb[0]) * 0.45 - tx * 30, pb[1] + (my_ - pb[1]) * 0.45 - ty * 30),
               (pb[0] + (mx_ - pb[0]) * 0.75 + tx * 28, pb[1] + (my_ - pb[1]) * 0.75 + ty * 28), (mx_, my_)]
        pts3_s, _ = _camino(pts, ancho=4.5, tipo='tierra', despejar=True)
        # explanada del mirador: rodal adoquinado + ERMITA + fuente + cipreses (italiano_kit)
        ang = [2 * math.pi * k / 10 for k in range(11)]
        rod = [(mx_ + 8.0 * math.cos(a_), my_ + 8.0 * math.sin(a_)) for a_ in ang]
        _camino(rod, ancho=6.0, tipo='adoquin', despejar=True)
        ik = M.get('italiano_kit')
        # direccion de llegada del sendero (ultimo tramo)
        ax_, ay_ = pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]
        al_ = math.hypot(ax_, ay_) or 1.0
        ax_, ay_ = ax_ / al_, ay_ / al_
        if ik is not None:
            try:
                er = ik.build_ermita(LIB, seed=int(s_s) % 7)
                ex_, ey_ = mx_ + ax_ * 16.0, my_ + ay_ * 16.0
                e_ = clone(er, (ex_, ey_, z_terreno(ex_, ey_) + 0.05), math.atan2(-ay_, -ax_) - math.pi / 2)
                e_.name = 'ITAL_ermita'
                _zocalo_global(e_, z_terreno(ex_, ey_) - 3.0)
                fu = ik.build_fuente(LIB, seed=1)
                f_ = clone(fu, (mx_, my_, z_terreno(mx_, my_) + 0.1), 0.0)
                f_.name = 'ITAL_fuente'
                # cipreses a ambos lados de los ultimos 60 m del sendero y una capitella al inicio
                fc = ik.build_fila_cipreses(LIB, largo=60.0, paso=7.0, seed=2)
                for sg in (1.0, -1.0):
                    cx_, cy_ = mx_ - ax_ * 36.0 + sg * (-ay_) * 4.2, my_ - ay_ * 36.0 + sg * ax_ * 4.2
                    c_ = clone(fc, (cx_, cy_, z_terreno(cx_, cy_)), math.atan2(ay_, ax_))
                    c_.name = 'ITAL_cipreses'
                cp = ik.build_capitella(LIB, seed=3)
                px_, py_ = pts[1][0] + (-ay_) * 4.0, pts[1][1] + ax_ * 4.0
                c2 = clone(cp, (px_, py_, z_terreno(px_, py_)), math.atan2(-ay_, -ax_) - math.pi / 2)
                c2.name = 'ITAL_capitella'
                # bancales de olivos en la ladera junto al tramo medio del sendero
                bc = ik.build_bancal(LIB, largo=30.0, alto=1.6, seed=4)
                for k in range(3):
                    q_ = pts3_s[min(len(pts3_s) - 1, int(len(pts3_s) * (0.35 + 0.12 * k)))]
                    bx_, by_ = q_[0] + (-ay_) * (14.0 + 9.0 * k), q_[1] + ax_ * (14.0 + 9.0 * k)
                    if pendiente_terreno(bx_, by_) > 0.12:
                        b_ = clone(bc, (bx_, by_, z_terreno(bx_, by_) - 0.2), math.atan2(ay_, ax_))
                        b_.name = 'ITAL_bancal'
            except Exception as e:
                log('italiano_kit en el mirador fallo: %s' % e)
        _cartel(mx_ - (-ay_) * 9.5, my_ - ax_ * 9.5, z_terreno(mx_ - (-ay_) * 9.5, my_ - ax_ * 9.5), math.atan2(ay_, ax_) + math.pi / 2, texto)
        log('caminos: sendero %s desde s=%d hasta (%.0f, %.0f) z=%.0f' % (texto, s_s, mx_, my_, mir[2]))
    log('caminos: %d tramos (%s), %d vallas de cierre, %d carteles, %d objetos despejados'
        % (CAMINOS_INFO['caminos'], ', '.join(sorted(set(t_[0] for t_ in CAMINOS_INFO['tramos']))),
           CAMINOS_INFO['vallas'], CAMINOS_INFO['carteles'], CAMINOS_INFO['despejados']))
safe('zona_caminos', zona_caminos)

# ============ COCHES-CAMARA QUE GRABAN LA CARRERA (en las curvas) ============
def zona_camaras():
    kk = M.get('camaras_kit')
    if kk is None:
        log('camaras_kit no disponible: sin coches-camara')
        return
    piezas = [kk.build_furgoneta_tv(LIB, seed=1), kk.build_grua_camara(LIB, alto=7.0, seed=2),
              kk.build_torre_camara(LIB, alto=6.0, seed=3), kk.build_furgoneta_tv(LIB, seed=4),
              kk.build_grua_camara(LIB, alto=8.5, seed=5)]
    obst = []
    for ob in root_col.objects:
        if ob.parent is not None:
            continue
        if ob.name.startswith(('CASAS_', 'COCHE_', 'MIRADOR_coches')):
            obst.append((ob.location.x, ob.location.y, 10.0))
        elif ob.name.startswith(('CARRERA_tribuna', 'CARRERA_boxes', 'CARRERA_pantalla', 'HOTEL_root',
                                 'AYTO_root', 'CAMPANILE_root', 'CASINO_root', 'MIRADOR_parking')):
            obst.append((ob.location.x, ob.location.y, 28.0))

    def kappa(i, d=4):
        pa, pb = S[(i - d) % N], S[(i + d) % N]
        return math.atan2(pa['ny'] * pb['nx'] - pa['nx'] * pb['ny'],
                          pa['nx'] * pb['nx'] + pa['ny'] * pb['ny']) / (2 * d * paso)
    # apices: maximos locales de curvatura
    ks = [kappa(i) for i in range(N)]
    apices = []
    for i in range(N):
        k = abs(ks[i])
        if k > 0.009 and all(k >= abs(ks[(i + j) % N]) for j in range(-12, 13)):
            apices.append(i)
    puestos = []
    for i in apices:
        s_a = i * paso
        q = S[i]
        if q['sec'] == 'bridge':
            continue
        if min(abs(s_a - 522.0), L - abs(s_a - 522.0)) < 110:        # tunel
            continue
        outside = 1 if ks[i] > 0 else -1          # ks>0 = curva a DERECHAS -> exterior a la izquierda (+1)
        if outside == -1 and (s_a > L - 230 or s_a < 210):           # pit lane
            continue
        if en_mirador(s_a, outside):
            continue
        ok_sitio = None
        for (lado_c, off) in ((outside, 8.5), (outside, 11.0), (outside, 14.0), (outside, 18.0),
                              (-outside, 9.0), (-outside, 12.5)):
            if lado_c == -1 and (s_a > L - 230 or s_a < 210):
                continue
            if en_mirador(s_a, lado_c):
                continue
            (pp, _q) = pos_side(s_a, lado_c, off)
            zt = z_terreno(pp[0], pp[1])
            z_borde = q['z'] - q['lat'] * lado_c * (q['w'] / 2)
            if zt < 0.8 or abs(zt - z_borde) > 2.6:
                continue
            zs = [z_terreno(pp[0] + dx, pp[1] + dy) for dx in (-3, 3) for dy in (-3, 3)]
            if max(zs) - min(zs) > 1.2:
                continue
            if any(math.hypot(pp[0] - ox, pp[1] - oy) < r_ for (ox, oy, r_) in obst):
                continue
            libre = True
            for j in range(0, N, 3):                  # ningun otro tramo de pista cerca
                if min(abs(j - i), N - abs(j - i)) * paso < 50:
                    continue
                if math.hypot(pp[0] - S[j]['x'], pp[1] - S[j]['y']) < S[j]['w'] / 2 + 7.0:
                    libre = False
                    break
            if libre:
                ok_sitio = (pp[0], pp[1], min(zs), lado_c)
                break
        if ok_sitio is None:
            continue
        if any(min(abs(s_a - sp), L - abs(s_a - sp)) < 120 for sp in puestos):
            continue
        # peana de hormigon: la cara del personaje queda por encima de la barrera
        H_PEANA = 0.7
        m_pe = _mat_simple('MAT_CAMARA_peana_piedra', (0.34, 0.33, 0.31, 1), 0.95)
        ang_p = rot_facing_road(s_a, ok_sitio[3])
        ca_, sa_ = math.cos(ang_p), math.sin(ang_p)
        vs_p, fs_p = [], []
        for (lx_, ly_) in ((-3.4, -2.6), (3.4, -2.6), (3.4, 2.8), (-3.4, 2.8)):
            wx_ = ok_sitio[0] + lx_ * ca_ - ly_ * sa_
            wy_ = ok_sitio[1] + lx_ * sa_ + ly_ * ca_
            vs_p.append((wx_, wy_, ok_sitio[2] - 0.6))
            vs_p.append((wx_, wy_, ok_sitio[2] + H_PEANA))
        for k_ in range(4):
            a0_, a1_ = 2 * k_, 2 * ((k_ + 1) % 4)
            fs_p.append((a0_, a1_, a1_ + 1, a0_ + 1))
        fs_p.append((1, 3, 5, 7))
        me_p = bpy.data.meshes.new('CAMARA_peana')
        me_p.from_pydata(vs_p, [], fs_p)
        me_p.materials.append(m_pe)
        import bmesh as _bmp
        _bp = _bmp.new()
        _bp.from_mesh(me_p)
        _bmp.ops.recalc_face_normals(_bp, faces=_bp.faces)
        _bp.to_mesh(me_p)
        _bp.free()
        root_col.objects.link(bpy.data.objects.new('CAMARA_peana', me_p))
        r = clone(piezas[len(puestos) % len(piezas)], (ok_sitio[0], ok_sitio[1], ok_sitio[2] + H_PEANA - 0.02),
                  ang_p)
        r.name = 'CAMARA_tierra'
        puestos.append(s_a)
    # helicopteros-camara sobre la meta, la horquilla de la rotonda y el lazo del viaducto
    heli = kk.build_helicoptero_camara(LIB, seed=7)
    lw = G.get('loews') or {}
    s_lw = (lw.get('s_idx') or CURVAS[39]['s_idx']) * paso
    n_h = 0
    for (s_h, alto_h, lado_h) in ((60.0, 38.0, 1), (s_lw - 30.0, 34.0, -1),
                                  (CURVAS[43]['s_idx'] * paso, 42.0, 1), (1840.0, 36.0, -1)):
        q = frame(s_h)
        l_ = lado_h * (q['w'] / 2 + 26.0)
        r = clone(heli, (q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, q['z'] + alto_h),
                  rot_facing_road(s_h, lado_h), pitch=0.0)
        r.rotation_euler = (math.radians(-14), 0.0, r.rotation_euler.z)   # morro hacia abajo, mirando la pista
        r.name = 'CAMARA_heli'
        n_h += 1
    log('coches-camara: %d en el exterior de las curvas (s=%s) + %d helicopteros'
        % (len(puestos), [int(sp) for sp in puestos], n_h))
safe('zona_camaras', zona_camaras)

def zona_acueducto_casino():
    """El puente alto de arcos de la foto, entre tierra y el penon, SOLO si el
    vano no pasa cerca de la pista (nada de puentes en medio de la carretera)."""
    info = CASINO_INFO
    if not info or not M.get('acueducto'):
        return
    cxc, cyc, zp = info['cx'], info['cy'], info['z_plaza']
    mejor = None
    for k in range(60):
        ang = 2 * math.pi * k / 60
        for dist in range(120, 320, 20):
            x = cxc + math.cos(ang) * dist
            y = cyc + math.sin(ang) * dist
            zt = z_terreno(x, y)
            if zt < zp * 0.5:
                continue
            ax, ay = cxc + math.cos(ang) * 50, cyc + math.sin(ang) * 50
            l2 = (x - ax) ** 2 + (y - ay) ** 2
            hol = 1e9
            for i in range(0, N, 2):
                px, py = S[i]['x'], S[i]['y']
                t_ = max(0.0, min(1.0, ((px - ax) * (x - ax) + (py - ay) * (y - ay)) / l2))
                hol = min(hol, math.hypot(px - (ax + t_ * (x - ax)), py - (ay + t_ * (y - ay))))
            if hol >= 35 and (mejor is None or dist < mejor[0]):
                mejor = (dist, ax, ay, x, y, zt, hol)
            break
    if mejor is None:
        log('acueducto del casino: cualquier vano cruzaria la pista, omitido')
        return
    dist, ax, ay, x, y, zt, hol = mejor
    largo = math.hypot(x - ax, y - ay) + 16.0
    alto = min(zp - 2.0, zt + 1.0) + 2.0
    ac = M['acueducto'].build(LIB, largo=largo, alto=alto, n_arcos=max(4, int(largo / 24)), seed=4)
    clone(ac, ((ax + x) / 2, (ay + y) / 2, -2.0), math.atan2(y - ay, x - ax))
    log('acueducto del casino: %.0f m de largo, %.0f m de alto, a %.0f m de la pista'
        % (largo, alto, hol))
# (desactivado en la ronda 11: con la montana del casino tan alta el arco quedaba
#  enterrado en la ladera; el gran viaducto ya hace ese papel)
# safe('zona_acueducto_casino', zona_acueducto_casino)

# ============ MONTANAS: CALIZA GRIS-BLANCA (como la referencia) ============
def ajustar_montanas():
    colores = {
        # valores LINEALES (0.35 lineal ~ gris medio en pantalla)
        'MAT_MONT_roca_clara': (0.40, 0.37, 0.31, 1),
        'MAT_MONT_roca': (0.34, 0.31, 0.26, 1),
        'MAT_MONT_roca_oscura': (0.28, 0.26, 0.22, 1),
        'MAT_MONT_bosque': (0.16, 0.33, 0.10, 1),
        'MAT_MONT_bosque_claro': (0.25, 0.44, 0.14, 1),
        'MAT_PENON_caliza': (0.36, 0.33, 0.27, 1),
        'MAT_PENON_caliza_clara': (0.41, 0.38, 0.31, 1),
        'MAT_PENON_caliza_oscura': (0.31, 0.28, 0.23, 1),
        'MAT_PENON_meseta': (0.48, 0.44, 0.36, 1),
        'MAT_PENON_caliza_faro': (0.52, 0.49, 0.41, 1),   # los 'faros' de la cara: caliza clara, no blanco puro
    }
    n = 0
    for m in bpy.data.materials:
        if m.name in colores and m.use_nodes and m.node_tree:
            bsdf = m.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Base Color'].default_value = colores[m.name]
                bsdf.inputs['Roughness'].default_value = 0.95
                m.diffuse_color = colores[m.name]
                n += 1
    log('montanas recoloreadas a caliza: %d materiales' % n)
    # filtro de mayoria: fuera quads verdes sueltos en plena roca (y al reves)
    import bmesh as _bm
    hechos = set()
    flips = 0
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.data.name in hechos:
            continue
        nombres = [m.name if m else '' for m in ob.data.materials]
        if not any(nm.startswith('MAT_MONT_') for nm in nombres):
            continue
        hechos.add(ob.data.name)
        es_roca = [nm.startswith('MAT_MONT_roca') for nm in nombres]
        bm = _bm.new()
        bm.from_mesh(ob.data)
        bm.faces.ensure_lookup_table()
        for _ in range(3):
            cambios = []
            for f in bm.faces:
                vec = [g for e in f.edges for g in e.link_faces if g is not f]
                if len(vec) < 2:
                    continue
                n_r = sum(1 for g in vec if es_roca[g.material_index])
                mia = es_roca[f.material_index]
                if mia and n_r <= len(vec) * 0.34:
                    otros = [g.material_index for g in vec if not es_roca[g.material_index]]
                    cambios.append((f, max(set(otros), key=otros.count)))
                elif (not mia) and n_r >= len(vec) * 0.66:
                    otros = [g.material_index for g in vec if es_roca[g.material_index]]
                    cambios.append((f, max(set(otros), key=otros.count)))
            for f, mi in cambios:
                f.material_index = mi
            flips += len(cambios)
        bm.to_mesh(ob.data)
        bm.free()
    log('montanas: %d caras sueltas reasignadas (filtro de mayoria)' % flips)
safe('ajustar_montanas', ajustar_montanas)

# ============ VARIACION DE COLOR EN LA VEGETACION ============
def enriquecer_vegetacion():
    tocados = 0
    for m in bpy.data.materials:
        n = m.name
        if not (n.startswith('MAT_VEG_') or n.startswith('MAT_OLI_')
                or 'PENON_veg' in n or 'LOEWS_seto' in n or 'LOEWS_hoja' in n):
            continue
        if not m.use_nodes or m.node_tree is None:
            continue
        if any(nd.name == 'VARIADO' for nd in m.node_tree.nodes):
            continue
        nt = m.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        if not bsdf:
            continue
        base = tuple(bsdf.inputs['Base Color'].default_value)
        tex = nt.nodes.new('ShaderNodeTexCoord')
        tex.name = 'VARIADO'
        noi = nt.nodes.new('ShaderNodeTexNoise')
        noi.inputs['Scale'].default_value = 0.08   # ~12 m: varia por instancia
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        e = ramp.color_ramp.elements
        e[0].position = 0.25
        e[0].color = (base[0] * 0.72, base[1] * 0.80, base[2] * 0.62, 1)
        e[1].position = 0.75
        e[1].color = (min(1, base[0] * 1.25), min(1, base[1] * 1.12),
                      base[2] * 0.85, 1)
        nt.links.new(tex.outputs['Object'], noi.inputs['Vector'])
        nt.links.new(noi.outputs['Fac'], ramp.inputs['Fac'])
        nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.9
        tocados += 1
    log('vegetacion variada: %d materiales' % tocados)
safe('enriquecer_vegetacion', enriquecer_vegetacion)

# ============ CAMARAS EXTRA Y RENDER ============
def add_cam(name, loc, target, lens=35):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 12000
    cam = bpy.data.objects.new(name, cd)
    cam.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    root_col.objects.link(cam)
    return cam

# camara a pie de pista mirando la recta de meta (tribunas de frente)
p_a = frame(L - 70)
p_b = frame(180)
cam_puerto = add_cam('puerto_panoramica',
                     (p_a['x'], p_a['y'], p_a['z'] + 7),
                     (p_b['x'], p_b['y'], p_b['z'] + 3), 32)
# recoloca la camara meta_puerto: desde tierra adentro, alto, mirando al mar
p_m = frame(90)
old = bpy.data.objects.get('meta_puerto')
if old:
    old.location = Vector((p_m['x'] - p_m['nx'] * 260, p_m['y'] - p_m['ny'] * 260, 95))
    d = Vector((p_m['x'] + p_m['nx'] * 120, p_m['y'] + p_m['ny'] * 120, 0)) - old.location
    old.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
c35 = CURVAS[35]
cam_casino = add_cam('casino_cerca',
                     (c35['x'] - 240, c35['y'] - 170, 60),
                     (c35['x'] + 20, c35['y'] + 20, 24), 40)

sc = bpy.context.scene
for cam_name, fname in [('vista_aerea', 'full_aerea'), ('meta_puerto', 'full_meta'),
                        ('puerto_panoramica', 'full_puerto'), ('casino_cerca', 'full_casino'),
                        ('cima_tierra', 'full_cima'), ('bahia_casino', 'full_bahia')]:
    cam = bpy.data.objects.get(cam_name)
    if not cam:
        continue
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT_R, fname + '.png')
    bpy.ops.render.render(write_still=True)
    print('render:', fname)

bpy.ops.wm.save_as_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
print('ERRORES:', errores if errores else 'ninguno')
print('OK escena integrada')
