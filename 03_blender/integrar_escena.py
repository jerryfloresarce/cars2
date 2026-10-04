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
G = json.load(open(os.environ.get('GEOM', BASE + r'\03_blender\geometria_3d.json'), encoding='utf-8'))
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
                 'caminos_kit', 'montana_coche', 'yates_kit', 'italiano_kit',
                 'roca_lazo', 'roca_casino', 'montana_mclaren'):          # ronda 15
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

def marco_interp(s_m):
    """v2 integrador: muestra INTERPOLADA entre las dos de 2 m que rodean s (frame() redondea a la mas cercana:
    para colocar piezas por cuerdas a s arbitraria el redondeo daba cuerdas de 4 a 8 m)."""
    s_m = s_m % L
    i0 = int(s_m // paso) % N
    i1 = (i0 + 1) % N
    f = (s_m - (s_m // paso) * paso) / paso
    a, b = S[i0], S[i1]
    q = {k: a[k] + (b[k] - a[k]) * f for k in ('x', 'y', 'z', 'nx', 'ny', 'w', 'lat')}
    ln = math.hypot(q['nx'], q['ny']) or 1.0
    q['nx'] /= ln
    q['ny'] /= ln
    q['sec'] = a['sec']
    return q

def borde_interp(s_m, side, off=0.0):
    """(x, y, z_borde) del punto a `off` m fuera del borde del asfalto del lado `side` (muestra interpolada)."""
    q = marco_interp(s_m)
    d = q['w'] / 2.0 + off
    return (q['x'] + side * q['nx'] * d, q['y'] + side * q['ny'] * d, q['z'] - q['lat'] * side * q['w'] / 2.0)

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
    lib['portico'] = ck.build_portico_meta(LIB, ancho=20.2)     # v1 integrador (A-02): pilares a 10.1 del centro
    lib['tribuna'] = ck.build_tribuna(LIB, largo=45, filas=12)
    lib['pantalla'] = ck.build_pantalla(LIB)
    lib['boxes'] = ck.build_boxes(LIB, n=12)
    lib['muro'] = ck.build_muro_valla(LIB, largo=10)
    lib['muro_corto'] = ck.build_muro_valla(LIB, largo=2.1)   # v2 integrador (I-R2-01): cierre del extremo del pretil
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
def _pedestal(raiz, lx, ly, hx, hy, z_fondo, z_top=0.05, nombre='CARRERA_portico_zocalo'):
    """Zocalo de piedra (hijo de `raiz`) bajo un pie: caja 2hx x 2hy centrada en (lx, ly) del marco
    local, desde z_fondo (cota de mundo) hasta z_top (local). Para pies que quedaban en el aire."""
    bpy.context.view_layer.update()
    zb = z_fondo - raiz.matrix_world.translation.z
    if zb > z_top - 0.05:
        return None
    m = bpy.data.materials.get('MAT_zocalo_piedra') or _mat_simple('MAT_zocalo_piedra', (0.55, 0.50, 0.40, 1), 0.95)
    vs = [(lx - hx, ly - hy, zb), (lx + hx, ly - hy, zb), (lx + hx, ly + hy, zb), (lx - hx, ly + hy, zb),
          (lx - hx, ly - hy, z_top), (lx + hx, ly - hy, z_top), (lx + hx, ly + hy, z_top), (lx - hx, ly + hy, z_top)]
    fs = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0), (4, 5, 6, 7)]
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(vs, [], fs)
    me.materials.append(m)
    ob = bpy.data.objects.new(nombre, me)
    root_col.objects.link(ob)
    ob.parent = raiz
    return ob

def zona_meta():
    # v1 integrador (A-02): portico de 20.2 m desplazado 1.2 m hacia el mar: el pilar de boxes queda en
    # lat -8.9 (sobre el podio del muro de boxes, fuera de la pista de 16 m y del pit lane, que empieza
    # en 9.75) y el del mar en +11.3 (detras del muro+valla y antes de la tribuna); su zocalo baja al terreno
    q6 = frame(6)
    pc = clone(lib['portico'], (q6['x'] + q6['nx'] * 1.2, q6['y'] + q6['ny'] * 1.2, q6['z']), rot_across(6))
    # v3 integrador (remate "nada encima del circuito"): el zocalo de 1.6 x 1.6 m del pilar de boxes iba de borde+0.1 a
    # borde+1.7 (0.05 m del pit lane); se estrecha en X (a traves de la pista) a +-0.57 m del eje del pilar (1.14 m, el
    # pilar mide 1.1): queda dentro de la franja del muro de boxes (borde+0.33 .. pit-0.15)
    try:
        for h_ in hierarchy(pc):
            if h_.type != 'MESH' or not h_.name.startswith('CARRERA_portico_estructura'):
                continue
            for v_ in h_.data.vertices:
                if v_.co.z < 0.61 and -10.1 - 0.9 < v_.co.x < -10.1 + 0.9:
                    v_.co.x = max(-10.1 - 0.57, min(-10.1 + 0.57, v_.co.x))
            h_.data.update()
    except Exception as e:
        log('meta: zocalo del pilar de boxes sin estrechar: %s' % e)
    xm_, ym_ = q6['x'] + q6['nx'] * 11.3, q6['y'] + q6['ny'] * 11.3
    zt_m = min(z_terreno(xm_ + a_, ym_ + b_) for a_ in (-0.8, 0.8) for b_ in (-0.8, 0.8))
    if zt_m < q6['z'] - 0.1:
        _pedestal(pc, 10.1, 0.0, 0.8, 0.8, zt_m - 0.3)
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
    # v1 integrador (I2/A-17): tribuna interior en s = L-226 (s 4951-4997, todo en tierra entre el estribo del
    # viaducto y la entrada del pit lane en s 5010), frente a 7.6 m del borde y a la cota de la PISTA (+0.25):
    # la ladera de detras se recorta 1:1 (grada encajada) y delante no hay relleno, escalon ni dientes
    S_TRI = L - 226
    for side, off in ((-1, 18), (-1, 26)):
        (p, q_t) = pos_side(S_TRI, side, off)
        if z_terreno(p[0], p[1]) > 0.6:  # nunca dentro del mar
            clone(lib['tribuna'], (p[0], p[1], q_t['z'] + 0.25), rot_facing_road(S_TRI, side))
            break
    else:
        log('tribuna interior omitida: solo hay mar')
    # pantallas gigantes en la tribuna del mar; v1 integrador (N6): base a la cota MAS BAJA de sus 4 patas
    # (en ladera 6 de las 8 bases quedaban 0.3-0.8 m en el aire)
    for s_m in (70, L - 30):
        for off in (30, 42):
            (p, _) = pos_side(s_m, 1, off)
            if z_terreno(p[0], p[1]) > 0.6:
                rp_ = rot_facing_road(s_m, 1)
                ca_, sa_ = math.cos(rp_), math.sin(rp_)
                zp_ = min(z_terreno(p[0] + lx_ * ca_ - ly_ * sa_, p[1] + lx_ * sa_ + ly_ * ca_)
                          for lx_ in (-2.8, 2.8) for ly_ in (-0.35, 0.35)) - 0.05
                clone(lib['pantalla'], (p[0], p[1], zp_), rp_)
                break
        else:
            log('pantalla en s=%.0f omitida: solo hay mar' % s_m)
    # muro+valla a ambos lados de la recta; v1 integrador (A-08): en el lado del mar sigue por la curva 1
    # y la subida al tunel hasta s 345 (antes acababa en s 175 y quedaban 165 m sin barrera con el mar
    # a 34-40 m del borde y 6-15 m mas abajo). La boca del puerto la abre _despejar_camino.
    # v2 integrador (I-R2-01/A-r2-02): la barrera arranca YA en el extremo del pretil del viaducto (ultima muestra
    # 'bridge', s 4936), no en s 5050: entre medias no habia nada a ningun lado (108 m de cesped con el mar a 22 m
    # en el +1 y la tribuna interior llena de publico a 7.6 m en el -1). En el lado -1 acaba en s <= 5008 (la
    # entrada del pit lane, ARCEN_PIT_entrada, queda libre); donde el terreno queda bajo la base, zocalo de piedra
    # (CARRERA_muro_zocalo -> 1WALL). Un solo bucle: la cadena del lado del mar sigue sin solapes hasta s 345.
    i_br = [i for i in range(int(4600 / paso), N) if S[i]['sec'] == 'bridge']
    S_FIN_PRETIL = (max(i_br) * paso) if i_br else (L - 150 - 5.5)
    PIT_IN_S = L - 190.0
    s_m = S_FIN_PRETIL + 5.5
    while s_m < L + 345:
        if s_m < L - 150:
            lados_m = (1, -1) if s_m + 5.0 <= PIT_IN_S - 2.0 else (1,)
        else:
            lados_m = (1,) if (M.get('pit_kit') or s_m >= L + 175) else (1, -1)
        for side in lados_m:
            (p, _) = pos_side(s_m, side, 2.2)
            m_ = clone(lib['muro'], p, rot_across(s_m) + math.pi / 2, pitch=pendiente(s_m))
            if s_m < L - 150:
                zmin_ = min(z_terreno(*pos_side(s_m + ds_, side, 2.2)[0][:2]) for ds_ in (-4.8, 0.0, 4.8))
                if zmin_ < p[2] - 0.05:
                    _pedestal(m_, 0.0, 0.0, 5.0, 0.24, zmin_ - 0.3, z_top=0.02, nombre='CARRERA_muro_zocalo')
        # paso en s tal que los tramos de 10 m se toquen tambien por fuera de las curvas
        (p0_, _) = pos_side(s_m, 1, 2.2)
        (p1_, _) = pos_side(s_m + 10, 1, 2.2)
        s_m += 10 * min(1.0, 9.8 / max(1.0, math.hypot(p1_[0] - p0_[0], p1_[1] - p0_[1])))
    # cierre transversal en el extremo del pretil (eje del pretil w/2+0.32 -> eje del muro w/2+2.2): sin el, el
    # escalon lateral de 1.9 m quedaba abierto; mira hacia delante, asi que no hay morro de cara al trafico.
    # v3 integrador (remate "nada encima del circuito"): el cierre iba de w/2+0.21 a w/2+2.31 y su canto interior y
    # el zocalo asomaban 0.1 m en la franja del borde (CARRERA_muro_valla.071/.072, s 4936). Ahora va de w/2+0.40
    # (aun solapa la testa del pretil, que llega a ~w/2+0.57) a w/2+2.31 (dentro del muro): pieza de 2.1 m encogida
    # en X (su eje va por la normal) con el zocalo, que es hijo, encogido con ella
    E_IN_C, E_OUT_C = 0.40, 2.31
    if i_br and 'muro_corto' in lib:
        for side in (1, -1):
            (p, q_) = pos_side(S_FIN_PRETIL + 0.35, side, (E_IN_C + E_OUT_C) / 2.0)
            c_ = clone(lib['muro_corto'], (p[0], p[1], q_['z'] - 0.06), rot_across(S_FIN_PRETIL))
            c_.scale = ((E_OUT_C - E_IN_C) / 2.1, 1.0, 1.0)
            zc_ = min(z_terreno(*pos_side(S_FIN_PRETIL + 0.35, side, o_)[0][:2]) for o_ in (E_IN_C, (E_IN_C + E_OUT_C) / 2.0, 2.1))
            _pedestal(c_, 0.0, 0.0, 1.05, 0.24, zc_ - 0.3, z_top=0.02, nombre='CARRERA_muro_zocalo')
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
    # v1 integrador (A-03/N1): el muro de boxes iba girado 180 grados (el +Y del kit, lado de la pista, miraba
    # al pit lane) y su podio de 2.35 m invadia 1 m de calzada. Ahora +Y mira a la pista (rot_across - pi/2,
    # pitch = -pendiente), la cara de pista queda en w/2 + 0.05 y el fondo es 1.30 m (parametro 'fondo' del
    # kit): la cara del pit lane queda en w/2 + 1.70, antes del borde del pit (9.75 con la pista de 16 m).
    # v3 integrador (remate "nada encima del circuito"): la franja libre entre el borde de la pista y el borde
    # interior del pit lane mide 1.75 m (16 m de pista, pit lane en 13.5 +- 3.75); el muro iba de w/2+0.05 a w/2+1.70
    # con el kit (podio, valla de captura, pupitres, pit board, sombrillas) encogido en Y x0.71: la valla y los
    # pupitres quedaban a < 0.3 m del asfalto (nada_en_pista: 41 tramos). Ahora TODO el kit va entre el borde + OFF_M
    # y el borde interior del pit lane - HOLG_PIT, con el fondo medido sobre la franja real de todo el muro (minimo
    # de _pit_interior cada metro) y, por tramo, lo que pida la flecha de su cuerda.
    OFF_M, HOLG_PIT = 0.33, 0.15
    PITL = G.get('pit_lane') or []
    def _z_pit(x_, y_):
        if not PITL:
            return None
        pq_ = min(PITL, key=lambda pp: (pp['x'] - x_) ** 2 + (pp['y'] - y_) ** 2)
        return pq_['z'] if math.hypot(pq_['x'] - x_, pq_['y'] - y_) < 12.0 else None
    def _pit_interior(s_):
        """distancia del borde de la pista (lado -1) al borde interior del pit lane (1e9 si no hay pit cerca)."""
        q_ = marco_interp(s_)
        xq_, yq_ = q_['x'] - q_['nx'] * (q_['w'] / 2.0 + 2.0), q_['y'] - q_['ny'] * (q_['w'] / 2.0 + 2.0)
        mejor_ = 1e9
        for pp in PITL:
            if abs(pp['x'] - xq_) > 25.0 or abs(pp['y'] - yq_) > 25.0:
                continue
            dxp, dyp = pp['x'] - q_['x'], pp['y'] - q_['y']
            if abs(dxp * q_['ny'] - dyp * q_['nx']) > 3.0:       # solo las muestras del pit a la altura de s
                continue
            lat_pp = -(dxp * q_['nx'] + dyp * q_['ny'])
            mejor_ = min(mejor_, lat_pp - pp['w'] / 2.0 - q_['w'] / 2.0)
        return mejor_
    # v2 integrador (A-N1/I-N2): cada tramo va por la CUERDA entre los puntos de cara (borde + OFF_M) de sus dos
    # extremos (muestras interpoladas), desplazada hacia el pit lo que haga falta para que ningun punto del borde
    # intermedio quede por fuera (flecha de la curva y ensanche de 13.6 a 16 m), con 0.4 m de solape entre tramos
    # (sin rendijas en las juntas). Antes: tramos de 12 m girados con la muestra del centro, extremos 1-3 cm dentro
    # de la calzada, escalones de 0.2 m y huecos de 1-1.5 m en s 5078, 5090, 5126, 5162 y 5174.
    k_ult = max(0, int(math.ceil((largo_disp - 6.0) / 12.0)) - 1)
    S_INI_M, S_FIN_M = s_a - 6.0, s_a + 12.0 * k_ult + 6.0
    gaps_m = [_pit_interior(S_INI_M + k_) for k_ in range(int(S_FIN_M - S_INI_M) + 1)]
    gaps_m = [g_ for g_ in gaps_m if g_ < 1e8]
    ESP_DISP = (min(gaps_m) if gaps_m else 1.75) - HOLG_PIT - OFF_M - 0.02
    FONDO_M = max(0.6, min(1.30, ESP_DISP))
    LP_M = 6.0      # v2 integrador (N1/N2): tramos de 6 m (antes 12): menos flecha en la curva y en el ensanche
    muros_lib = [pk.build_muro_boxes(LIB, largo=LP_M, seed=k, fondo=FONDO_M) for k in range(3)]
    def _ext_y(raiz):
        ys_ = [c[1] for h in hierarchy(raiz) if h.type == 'MESH' for c in h.bound_box]
        return (min(ys_), max(ys_)) if ys_ else (-2.05, 0.30)
    y0_m, y1_m = _ext_y(muros_lib[0])
    esc_y = 1.0
    if y1_m - y0_m > FONDO_M + 0.6:
        # el kit aun no admite 'fondo': sin coches-mecanico (se aplastarian) y encogido en Y (aviso para pit_kit_v2)
        muros_lib = [pk.build_muro_boxes(LIB, largo=LP_M, seed=k, equipo=False) for k in range(3)]
        y0_m, y1_m = _ext_y(muros_lib[0])
    if y1_m - y0_m > ESP_DISP:
        esc_y = ESP_DISP / max(0.3, y1_m - y0_m)
        log('pit: muro de boxes de %.2f m de fondo en una franja de %.2f m: tramos encogidos en Y x%.2f (cara a borde+%.2f)'
            % (y1_m - y0_m, ESP_DISP, esc_y, OFF_M))
    ESP_M = (y1_m - y0_m) * esc_y           # fondo real del muro (cara de pista -> cara del pit lane)

    def _z_base_muro(s_):
        xb_, yb_, zb_ = borde_interp(s_, -1, 2.0)
        zp_ = _z_pit(xb_, yb_)
        return min(zb_, zp_ if zp_ is not None else zb_) - 0.05

    s0_m = S_INI_M
    esc_min = esc_y
    while s0_m < S_FIN_M - 0.5:
        P0 = borde_interp(s0_m, -1, OFF_M)
        s1_m = s0_m + LP_M - 0.4
        for _it in range(4):
            P1 = borde_interp(s1_m, -1, OFF_M)
            c_ = math.hypot(P1[0] - P0[0], P1[1] - P0[1]) or 1.0
            s1_m = s0_m + (s1_m - s0_m) * (LP_M - 0.4) / c_
        P1 = borde_interp(s1_m, -1, OFF_M)
        cx_, cy_ = P1[0] - P0[0], P1[1] - P0[1]
        lc_ = math.hypot(cx_, cy_) or 1.0
        cx_, cy_ = cx_ / lc_, cy_ / lc_
        rx_, ry_ = cy_, -cx_                 # derecha de la cuerda = hacia el pit (lado -1)
        sh_ = 0.0
        proy_ = []
        k_ = 0
        while k_ <= 10:
            s_k_ = s0_m + (s1_m - s0_m) * k_ / 10.0
            Fs = borde_interp(s_k_, -1, OFF_M)
            pr_ = (Fs[0] - P0[0]) * rx_ + (Fs[1] - P0[1]) * ry_
            sh_ = max(sh_, pr_)
            proy_.append((s_k_, pr_))
            k_ += 1
        # v3: la cara del pit lane del tramo (cara de pista + fondo) en cada punto de la cuerda, a <= borde interior del
        # pit lane - HOLG_PIT (la flecha empuja la cuerda hacia el pit: en ese tramo se encoge un poco mas)
        esc_k = esc_y
        for (s_k_, pr_) in proy_:
            g_k = _pit_interior(s_k_)
            if g_k < 1e8:
                esc_k = min(esc_k, (g_k - HOLG_PIT - OFF_M - (sh_ - pr_)) / max(0.3, y1_m - y0_m))
        esc_k = max(0.25, esc_k)
        esc_min = min(esc_min, esc_k)
        s_c_ = (s0_m + s1_m) / 2.0
        mx = (P0[0] + P1[0]) / 2.0 + rx_ * (sh_ + y1_m * esc_k)
        my = (P0[1] + P1[1]) / 2.0 + ry_ * (sh_ + y1_m * esc_k)
        m = clone(muros_lib[n_muro % 3], (mx, my, _z_base_muro(s_c_)), math.atan2(cy_, cx_), pitch=-pendiente(s_c_ % L))
        if esc_k != 1.0:
            m.scale = (1.0, esc_k, 1.0)
        m.name = 'PIT_muro'
        n_muro += 1
        s0_m = s1_m
    if esc_min < esc_y - 1e-3:
        log('pit: algun tramo del muro de boxes encogido hasta x%.2f por la flecha de su cuerda' % esc_min)
    # MORRO del muro de boxes (N1): antes arrancaba con un canto recto de 1.8 m a 0.29 m del asfalto, de cara a la
    # marcha al final del viaducto. Cuna de hormigon de ~9 m (1:5.5) en la isleta entre la pista y el pit lane:
    # la cara de pista va de la punta (junto a la cara del pit) a w/2+OFF_M en el arranque del muro (v3: antes
    # w/2+0.05); la cara del pit nunca pasa del borde interior del pit lane - 0.15. 1WALL_ (PIT_muro*); neumaticos
    # delante si caben.
    try:
        L_MORRO = 9.0
        e_out = lambda s_: min(OFF_M + ESP_M, _pit_interior(s_) - HOLG_PIT)
        s_t = S_INI_M - L_MORRO
        while s_t < S_INI_M - 4.0 and e_out(s_t) < OFF_M + 0.25:
            s_t += 1.0
        e_tip = max(OFF_M + 0.05, e_out(s_t) - 0.05)
        n_k = max(2, int(round(S_INI_M - s_t)))
        vs_m, fs_m = [], []
        for k_ in range(n_k + 1):
            s_ = s_t + (S_INI_M - s_t) * k_ / float(n_k)
            f_ = k_ / float(n_k)
            eo_ = e_out(s_) if k_ < n_k else OFF_M + ESP_M
            ei_ = max(OFF_M, min(eo_ - 0.03, e_tip + (OFF_M - e_tip) * f_))
            eo_ = max(eo_, ei_ + 0.03)
            zb_ = _z_base_muro(s_)
            for e_ in (ei_, eo_):
                xq_, yq_, _zq = borde_interp(s_, -1, e_)
                vs_m.append((xq_, yq_, zb_ - 0.3))
                vs_m.append((xq_, yq_, zb_ + 1.1))
        for k_ in range(n_k):
            o = 4 * k_
            fs_m += [(o, o + 4, o + 5, o + 1), (o + 2, o + 3, o + 7, o + 6), (o + 1, o + 5, o + 7, o + 3)]
        fs_m += [(0, 1, 3, 2), (4 * n_k, 4 * n_k + 2, 4 * n_k + 3, 4 * n_k + 1)]
        me_m = bpy.data.meshes.new('PIT_muro_morro')
        me_m.from_pydata(vs_m, [], fs_m)
        mats_m = [mt for mt in (hierarchy(muros_lib[0])[0].data.materials if hierarchy(muros_lib[0])[0].type == 'MESH' else []) if mt is not None]
        me_m.materials.append(mats_m[0] if mats_m else _mat_simple('MAT_PIT_hormigon_morro', (0.62, 0.62, 0.60, 1), 0.8))
        import bmesh as _bmm
        _bq = _bmm.new()
        _bq.from_mesh(me_m)
        _bmm.ops.recalc_face_normals(_bq, faces=_bq.faces)
        _bq.to_mesh(me_m)
        _bq.free()
        root_col.objects.link(bpy.data.objects.new('PIT_muro_morro', me_m))
        # amortiguador de neumaticos delante de la punta (solo si la isleta deja >= 0.9 m); v3: cada pila (r 0.36)
        # entre el borde + OFF_M y el borde interior del pit lane - HOLG_PIT
        n_neu = 0
        if min(e_out(s_t - 0.45), e_out(s_t - 1.2)) >= OFF_M + 0.76:
            m_goma = _mat_simple('MAT_PIT_neumatico', (0.03, 0.03, 0.03, 1), 0.85)
            for j_ in range(2):
                s_n = s_t - 0.45 - 0.75 * j_
                xn_, yn_, _zn = borde_interp(s_n, -1, max(OFF_M + 0.38, min(e_tip, e_out(s_n) - 0.38)))
                zn_ = _z_base_muro(s_n)
                vs_n, fs_n = [], []
                for zz_ in (zn_ - 0.05, zn_ + 1.0):
                    for a_ in range(10):
                        vs_n.append((xn_ + 0.36 * math.cos(2 * math.pi * a_ / 10), yn_ + 0.36 * math.sin(2 * math.pi * a_ / 10), zz_))
                fs_n = [(a_, (a_ + 1) % 10, 10 + (a_ + 1) % 10, 10 + a_) for a_ in range(10)] + [tuple(range(19, 9, -1)), tuple(range(10))]
                me_n = bpy.data.meshes.new('PIT_amortiguador')
                me_n.from_pydata(vs_n, [], fs_n)
                me_n.materials.append(m_goma)
                root_col.objects.link(bpy.data.objects.new('PIT_amortiguador', me_n))
                n_neu += 1
        log('pit: morro del muro de boxes de s=%.1f a %.1f (punta a %.2f m del borde), %d pilas de neumaticos'
            % (s_t, S_INI_M, e_tip, n_neu))
    except Exception as e:
        log('pit: morro del muro de boxes fallo: %s' % e)
    # torres de control en los extremos del edificio, detras; v1 integrador (A-16): 6 m mas atras
    # (lat d_front+20): en d_front+14 su zocalo invadia 1.35-1.5 m el paddock en el quiebro
    torre = pk.build_torre_control(LIB, alto=16.0, seed=2)
    for ds in (-largo / 2 - 9.0, largo / 2 + 9.0):
        qt = frame((s_c + ds) % L)
        d_t = d_front + 20.0
        tx, ty = qt['x'] - qt['nx'] * d_t, qt['y'] - qt['ny'] * d_t
        t = clone(torre, (tx, ty, max(z_terreno(tx, ty), 0.3)), rot_facing_road((s_c + ds) % L, -1))
        t.name = 'PIT_torre'
        # v3 integrador (N4): sin _zocalo_global (caja SIN tapa hasta 0.6 m sobre la base: 'corral' de piedra con
        # hierba dentro); la explanada y el pedestal con tapa los pone zona_torres_pit (explanar va despues)
        PIT_INFO.setdefault('torres', []).append(t.name)
    # pasarela sobre la pista; v1 integrador (A-01): en s 96 su torre de boxes ocupaba 5.5 de los 7.5 m del
    # pit lane y la del mar estaba dentro de la tribuna .002 (s 77.5-122.7). En s 126 solo hay terreno a
    # los dos lados: la torre del mar arranca 0.5 m detras del muro+valla y la de boxes 1.3 m pasado el
    # borde exterior del pit lane; luz asimetrica (origen desplazado por la normal), raiz a la cota mas
    # baja del terreno bajo las torres y alto = 7 m libres sobre la PISTA
    s_p = 126.0
    qp = frame(s_p)
    lat_mar = qp['w'] / 2.0 + 2.2 + 0.23 + 0.5
    lat_box = qp['w'] / 2.0 + 2.93
    for pp in PITL:
        dxp, dyp = pp['x'] - qp['x'], pp['y'] - qp['y']
        if abs(dxp * qp['ny'] - dyp * qp['nx']) < 6.0:
            lat_box = max(lat_box, abs(dxp * qp['nx'] + dyp * qp['ny']) + pp['w'] / 2.0 + 1.3)
    luz = lat_mar + lat_box
    c_p = (lat_mar - lat_box) / 2.0
    tp_ = tangent(s_p)
    zs_t = []
    for sg in (1.0, -1.0):
        for u_ in (luz / 2 + 0.3, luz / 2 + 3.6, luz / 2 + 6.9):
            for v_ in (-1.5, 0.0, 1.5):
                l_ = c_p + sg * u_
                zs_t.append(z_terreno(qp['x'] + qp['nx'] * l_ + tp_[0] * v_, qp['y'] + qp['ny'] * l_ + tp_[1] * v_))
    z_b = min(min(zs_t), qp['z'] - 0.05)
    pas = pk.build_pasarela(LIB, luz=luz, alto=7.0 + (qp['z'] - z_b), seed=3)
    pz = clone(pas, (qp['x'] + qp['nx'] * c_p, qp['y'] + qp['ny'] * c_p, z_b), rot_across(s_p))
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

# ============ RONDA 15: EXPLANADAS bajo edificios grandes ============
# El terreno nuevo es un macizo: tribunas, hotel, ayuntamiento... quedaban con la trasera
# enterrada 2-10 m en la ladera. Como haria un ingeniero, se talla una EXPLANADA: el
# terreno bajo la huella (+margen) a la cota de la base, desmonte 1:1 por detras y
# terraplen 0.6 por delante. Se edita a la vez la malla TERRENO y la rejilla T['z']
# (z_terreno), asi todo lo que se coloque despues ya ve la explanada.
def _rect_local(ob):
    """(inv, x0, x1, y0, y1): caja en planta de toda la jerarquia en el marco del objeto."""
    bpy.context.view_layer.update()
    inv = ob.matrix_world.inverted()
    xs, ys = [], []
    for h in [ob] + list(ob.children_recursive):
        if h.type != 'MESH' or h.name.startswith(('VEG_', 'OLI_', 'CASAS_zocalo')):
            continue
        for c in h.bound_box:
            l_ = inv @ (h.matrix_world @ Vector(c))
            xs.append(l_.x)
            ys.append(l_.y)
    if not xs:
        return None
    return inv, min(xs), max(xs), min(ys), max(ys)

EXPLANADAS = {'n': 0, 'celdas': 0, 'alcance_max': 0.0}

def _proteger_pista(x, y, z, z_new):
    """Junto a la pista: nunca se rellena a menos de 3 m del borde y nunca se excava por debajo del pasillo
    de la pista (cota del eje - 0.6, y un talud 0.55 mas alla de 6 m): un desmonte largo no puede dejar
    la calzada ni su arcen en el aire (v1 integrador, al alargar los desmontes de explanar)."""
    q = S[_muestra_cerca(x, y)]
    d = math.hypot(x - q['x'], y - q['y']) - q['w'] / 2.0
    if d < 3.0:
        z_new = min(z_new, z)
    if d < 12.0:
        z_lim = q['z'] - 0.6 - max(0.0, d - 6.0) * 0.55
        if z_new < z_lim:
            z_new = max(z_new, min(z, z_lim))
    return z_new

def _poner_celda(ter, k, z, z_new, roca=True):
    """Escribe la cota de una celda en la rejilla T y en la malla TERRENO; los desmontes de mas de 2 m
    pasan a roca caliza (atributo 'roca' del TERRENO): se leen como un tajo en la roca, no como hierba."""
    T['z'][k] = z_new
    if ter is None:
        return
    ter.data.vertices[k].co.z = z_new
    if roca and z - z_new > 2.0:
        at = ter.data.attributes.get('roca')
        if at is not None:
            try:
                at.data[k].value = max(at.data[k].value, min(1.0, (z - z_new - 1.0) / 2.0))
            except Exception:
                pass

def _zmax_alrededor(cx0, cx1, cy0, cy1, r=150.0):
    i0 = max(0, int((cx0 - r - T['x0']) / T['cell'])); i1 = min(T['nx'] - 1, int((cx1 + r - T['x0']) / T['cell']) + 1)
    j0 = max(0, int((cy0 - r - T['y0']) / T['cell'])); j1 = min(T['ny'] - 1, int((cy1 + r - T['y0']) / T['cell']) + 1)
    zm = -1e9
    for j in range(j0, j1 + 1, 2):
        fila = T['z'][j * T['nx'] + i0: j * T['nx'] + i1 + 1: 2]
        if fila:
            zm = max(zm, max(fila))
    return zm

def explanar(ob, margen=3.0, alcance=28.0, desmonte=1.0, terraplen=0.6, zb=None, roca=True):
    """Explanada bajo un edificio: el terreno bajo la huella (+margen) a la cota zb, desmonte 1:desmonte
    por detras y terraplen 1:terraplen por delante. v1 integrador (C-02/N1/D5): el desmonte ya no se corta
    en seco en margen+alcance (dejaba paredes verticales de 25-45 m detras del ayuntamiento y del hotel):
    sigue hasta encontrar la ladera natural (como mucho 150 m); el terraplen sigue limitado a 0.6*alcance."""
    rl = _rect_local(ob)
    if rl is None:
        return 0
    inv, x0, x1, y0, y1 = rl
    if zb is None:
        zb = ob.matrix_world.translation.z - 0.05
    mw = ob.matrix_world
    esq = [mw @ Vector((a, b, 0.0)) for (a, b) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    ex0, ex1 = min(p_.x for p_ in esq), max(p_.x for p_ in esq)
    ey0, ey1 = min(p_.y for p_ in esq), max(p_.y for p_ in esq)
    zmax = _zmax_alrededor(ex0, ex1, ey0, ey1)
    alcance_d = min(150.0, max(alcance, (zmax - zb) / max(desmonte, 0.2) + 2 * T['cell']))
    EXPLANADAS['alcance_max'] = max(EXPLANADAS['alcance_max'], alcance_d)
    gx0, gx1 = ex0 - margen - alcance_d, ex1 + margen + alcance_d
    gy0, gy1 = ey0 - margen - alcance_d, ey1 + margen + alcance_d
    ter = bpy.data.objects.get('TERRENO')
    i0 = max(0, int((gx0 - T['x0']) / T['cell'])); i1 = min(T['nx'] - 1, int((gx1 - T['x0']) / T['cell']) + 1)
    j0 = max(0, int((gy0 - T['y0']) / T['cell'])); j1 = min(T['ny'] - 1, int((gy1 - T['y0']) / T['cell']) + 1)
    n_c = 0
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            k = j * T['nx'] + i
            x = T['x0'] + i * T['cell']
            y = T['y0'] + j * T['cell']
            l_ = inv @ Vector((x, y, 0.0))
            dx = max(x0 - l_.x, 0.0, l_.x - x1)
            dy = max(y0 - l_.y, 0.0, l_.y - y1)
            d = math.hypot(dx, dy)
            if d > margen + alcance_d:
                continue
            z = T['z'][k]
            if T['mar'][k] and z < 0.5:
                continue
            e = max(0.0, d - margen)
            z_new = min(z, zb + e * desmonte)                 # desmonte (hasta la ladera natural)
            if d < margen + alcance * 0.6:
                z_new = max(z_new, zb - e * terraplen)        # terraplen (solo cerca)
            z_new = _proteger_pista(x, y, z, z_new)
            if abs(z_new - z) > 0.02:
                _poner_celda(ter, k, z, z_new, roca)
                n_c += 1
    EXPLANADAS['n'] += 1
    EXPLANADAS['celdas'] += n_c
    return n_c

_REJ_M = {}
for _i in range(0, N):
    _REJ_M.setdefault((int(S[_i]['x'] // 30), int(S[_i]['y'] // 30)), []).append(_i)
def _muestra_cerca(x, y):
    kx, ky = int(x // 30), int(y // 30)
    best, bi = 1e18, 0
    for ddx in (-1, 0, 1):
        for ddy in (-1, 0, 1):
            for _i in _REJ_M.get((kx + ddx, ky + ddy), ()):
                d2 = (x - S[_i]['x']) ** 2 + (y - S[_i]['y']) ** 2
                if d2 < best:
                    best, bi = d2, _i
    return bi

def explanar_edificios(prefijos):
    hechos = []
    for ob in list(root_col.objects):
        try:
            if ob.parent is not None or not ob.name.startswith(prefijos):
                continue
        except ReferenceError:
            continue
        if ob.name.startswith('CARRERA_tribuna'):
            rl = _rect_local(ob)
            if rl is not None:
                _inv, x0, x1, y0, y1 = rl
                fr_ = [ob.matrix_world @ Vector((a_, y1, 0.0)) for a_ in (x0, (x0 + x1) / 2, x1)]   # +Y = frente a la pista
                z_fr = max(z_terreno(p_.x, p_.y) for p_ in fr_)
                # v1 integrador (I2): nunca por encima de la pista + 0.6 (la grada se encaja en la ladera)
                z_fr = min(z_fr, S[_muestra_cerca(ob.location.x, ob.location.y)]['z'] + 0.6)
                if z_fr > ob.location.z + 0.3:
                    ob.location.z = z_fr - 0.05
                    bpy.context.view_layer.update()
        # el hotel queda en una ladera del 115 %: desmonte 1:1.2 (v1, N1 de C), el tajo se lee como roca
        n_c = explanar(ob, desmonte=1.2) if ob.name.startswith('HOTEL_') else explanar(ob)
        hechos.append('%s:%d' % (ob.name, n_c))
    if bpy.data.objects.get('TERRENO') is not None:
        bpy.data.objects['TERRENO'].data.update()
    log('explanadas: %s' % ', '.join(hechos))
safe('explanar_meta', lambda: explanar_edificios(('CARRERA_tribuna', 'HOTEL_root')))

def zona_torres_pit():
    """v3 integrador (N4): las torres de control apoyan en una EXPLANADA a su cota (margen 1.5 m) y, solo si aun queda
    terreno por debajo de la base, un pedestal CON tapa a ras de la base (+0.02) a la medida del plinto (r 2.7): antes
    el zocalo de casa (caja sin tapa hasta 0.6 m sobre la base, a la medida del balcon de 3.9 m) dejaba un 'corral' de
    piedra con hierba dentro y una cuna de terreno cortando el muro en el lado bajo."""
    n_p = 0
    for nm in PIT_INFO.get('torres', []):
        t = bpy.data.objects.get(nm)
        if t is None:
            continue
        explanar(t, margen=1.5, alcance=12.0)
        tx, ty = t.location.x, t.location.y
        zt_t = min(z_terreno(tx + a_, ty + b_) for a_ in (-2.7, 0.0, 2.7) for b_ in (-2.7, 0.0, 2.7))
        if zt_t < t.location.z - 0.15:
            _pedestal(t, 0.0, 0.0, 2.7, 2.7, zt_t - 0.3, z_top=0.02, nombre='PIT_torre_zocalo')
            n_p += 1
    if bpy.data.objects.get('TERRENO') is not None:
        bpy.data.objects['TERRENO'].data.update()
    log('pit: %d torres de control sobre explanada (%d con pedestal)' % (len(PIT_INFO.get('torres', [])), n_p))
safe('torres_pit', zona_torres_pit)

def tallar_circulo(cx, cy, r, zb, desmonte=1.0, alcance=18.0):
    """Explanada circular a la cota zb (desmonte 1:1 alrededor): plazuelas al pie de la ladera.
    v1 integrador (G9): mas alla de `alcance` el talud sigue (1:2) hasta 2.5*alcance para cerrar contra la
    ladera; si aun asi el ultimo anillo exige cortar mas de 0.3 m (ladera de > 100 %), NO se talla nada y
    devuelve -1 (el que llama descarta la plazuela): antes quedaba un escalon vertical de 10-13 m."""
    ter = bpy.data.objects.get('TERRENO')
    ext = 2.5 * alcance
    i0 = max(0, int((cx - r - ext - T['x0']) / T['cell'])); i1 = min(T['nx'] - 1, int((cx + r + ext - T['x0']) / T['cell']) + 1)
    j0 = max(0, int((cy - r - ext - T['y0']) / T['cell'])); j1 = min(T['ny'] - 1, int((cy + r + ext - T['y0']) / T['cell']) + 1)
    cambios = []
    peor_borde = 0.0
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            k = j * T['nx'] + i
            x = T['x0'] + i * T['cell']
            y = T['y0'] + j * T['cell']
            e = max(0.0, math.hypot(x - cx, y - cy) - (r + 1.0))
            if e > ext:
                continue
            z = T['z'][k]
            if e <= alcance:
                z_tope = zb - 0.05 + e * desmonte
            else:
                z_tope = zb - 0.05 + alcance * desmonte + (e - alcance) * 2.0
            z_new = min(z, z_tope)
            if e <= T['cell']:
                # la losa nunca queda en el aire; v2 integrador (C2-12): el relleno sigue una celda mas (1:1), asi
                # ningun triangulo de fuera deja aire bajo el borde (antes solo hasta e = 0: hasta 1.3 m de aire)
                z_new = max(z_new, zb - 0.6 - e)
            if e > ext - T['cell'] * 1.5:
                peor_borde = max(peor_borde, z - z_new)
            z_new = _proteger_pista(x, y, z, z_new)
            if abs(z_new - z) > 0.02:
                cambios.append((k, z, z_new))
    if peor_borde > 0.3:
        return -1
    for (k, z, z_new) in cambios:
        _poner_celda(ter, k, z, z_new)
    return len(cambios)

def tallar_cinta(pts3, semiancho, desmonte=1.0, terraplen=0.7, alcance=6.0, dz=-0.15, evitar=None, roca=False, modo=None):
    """v1 integrador (E4/C-06/F-11): BANQUETA a lo largo de una polilinea 3D. Celdas a menos de `semiancho`
    del eje -> cota del eje + dz (con terraplen=None solo se rebaja); fuera, desmonte 1:desmonte por arriba
    y relleno 1:terraplen por abajo hasta `alcance`. Cada celda toma el tramo mas cercano (en una horquilla
    cada rama talla su lado). evitar(x, y) -> True deja la celda como esta (huellas de casas).
    v2 integrador (E2-03/D2-09): modo='sendero' -> _tallar_sendero (varias ramas, taludes segun la ladera y
    pase de garantia sobre la triangulacion real)."""
    if modo == 'sendero':
        return _tallar_sendero(pts3, semiancho, dz=dz, evitar=evitar)
    ter = bpy.data.objects.get('TERRENO')
    reach = semiancho + alcance
    mejor = {}
    for a, b in zip(pts3[:-1], pts3[1:]):
        vx, vy = b[0] - a[0], b[1] - a[1]
        l2 = vx * vx + vy * vy
        i0 = max(0, int((min(a[0], b[0]) - reach - T['x0']) / T['cell'])); i1 = min(T['nx'] - 1, int((max(a[0], b[0]) + reach - T['x0']) / T['cell']) + 1)
        j0 = max(0, int((min(a[1], b[1]) - reach - T['y0']) / T['cell'])); j1 = min(T['ny'] - 1, int((max(a[1], b[1]) + reach - T['y0']) / T['cell']) + 1)
        for j in range(j0, j1 + 1):
            y = T['y0'] + j * T['cell']
            for i in range(i0, i1 + 1):
                x = T['x0'] + i * T['cell']
                f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a[0]) * vx + (y - a[1]) * vy) / l2))
                d = math.hypot(x - a[0] - vx * f, y - a[1] - vy * f)
                if d > reach:
                    continue
                k = j * T['nx'] + i
                if k not in mejor or d < mejor[k][0]:
                    mejor[k] = (d, a[2] + (b[2] - a[2]) * f)
    n_c = 0
    for k, (d, z_e) in mejor.items():
        x = T['x0'] + (k % T['nx']) * T['cell']
        y = T['y0'] + (k // T['nx']) * T['cell']
        if evitar is not None and evitar(x, y):
            continue
        z = T['z'][k]
        if T['mar'][k] and z < 0.5:
            continue
        zc = z_e + dz
        e = d - semiancho
        if e <= 0.0:
            z_new = zc if terraplen is not None else min(z, zc)
        else:
            z_new = min(z, zc + e * desmonte)
            if terraplen is not None:
                z_new = max(z_new, zc - e * terraplen)
        z_new = _proteger_pista(x, y, z, z_new)
        if abs(z_new - z) > 0.02:
            _poner_celda(ter, k, z, z_new, roca)
            n_c += 1
    if ter is not None and n_c:
        ter.data.update()
    return n_c

def _z_tri(x, y):
    """Cota del TERRENO con la triangulacion REAL de la malla (diagonal a -> a+nx+1, la del render y del kn5) y
    los indices de los 3 nodos del triangulo que contiene (x, y)."""
    nx_, c_ = T['nx'], T['cell']
    fx, fy = (x - T['x0']) / c_, (y - T['y0']) / c_
    i = max(0, min(nx_ - 2, int(math.floor(fx))))
    j = max(0, min(T['ny'] - 2, int(math.floor(fy))))
    u, v = min(1.0, max(0.0, fx - i)), min(1.0, max(0.0, fy - j))
    a = j * nx_ + i
    Z = T['z']
    if u >= v:
        return Z[a] + u * (Z[a + 1] - Z[a]) + v * (Z[a + nx_ + 1] - Z[a + 1]), (a, a + 1, a + nx_ + 1)
    return Z[a] + v * (Z[a + nx_] - Z[a]) + u * (Z[a + nx_ + 1] - Z[a + nx_]), (a, a + nx_ + 1, a + nx_)

def _puntos_disco(cx, cy, r, paso_d=1.0):
    """Puntos de muestreo (planta) de un disco de radio r: centro + anillos cada ~paso_d m."""
    pts = [(cx, cy)]
    n_r = max(1, int(math.ceil(r / paso_d)))
    for a in range(1, n_r + 1):
        ra = r * a / float(n_r)
        n_a = max(6, int(math.ceil(2 * math.pi * ra / paso_d)))
        pts += [(cx + ra * math.cos(2 * math.pi * k / n_a), cy + ra * math.sin(2 * math.pi * k / n_a)) for k in range(n_a)]
    return pts

def _garantia_losa(puntos, z_top, holgura=0.05):
    """v2 integrador (C2-12): ninguna hierba por encima de una losa. Con la triangulacion REAL del TERRENO, si en
    algun punto de la losa el terreno queda por encima de z_top - holgura, se bajan los 3 nodos de su triangulo
    (solo lo justo; nunca bajo el pasillo de la pista). -> nodos tocados."""
    ter = bpy.data.objects.get('TERRENO')
    nx_, c_ = T['nx'], T['cell']
    n_ = 0
    for _it in range(2):
        mods = {}
        for (x, y) in puntos:
            zt, nodos = _z_tri(x, y)
            if zt > z_top - holgura:
                for kk in nodos:
                    if T['z'][kk] > z_top - holgura - 0.02:
                        mods[kk] = z_top - holgura - 0.02
        for kk, zn in mods.items():
            if T['mar'][kk] and T['z'][kk] < 0.5:
                continue
            xk, yk = T['x0'] + (kk % nx_) * c_, T['y0'] + (kk // nx_) * c_
            zn = _proteger_pista(xk, yk, T['z'][kk], zn)
            if zn < T['z'][kk] - 0.005:
                _poner_celda(ter, kk, T['z'][kk], zn, False)
                n_ += 1
    if ter is not None and n_:
        ter.data.update()
    return n_

def _garantia_cinta(pts3, semiancho, holgura=0.05, paso_l=1.0, paso_u=0.5):
    """v3 integrador (G1/N2): pase de GARANTIA para calzadas con rasante propia (como el (a) de _tallar_sendero y
    _garantia_losa): tallar_cinta solo mueve NODOS de la rejilla de 4 m y el triangulo (diagonal a->a+nx+1) que va de
    un nodo a 5 m del eje a otro ya bajado subia por encima del borde de la calzada (espolon del casino: 116 puntos con
    hasta 0.76 m de hierba; paseo de la tribuna: 1.37 m). Cada paso_l m a lo largo y cada paso_u m a lo ancho
    (+-semiancho), con la triangulacion REAL: si el terreno queda por encima de la rasante - holgura se bajan los 3
    nodos del triangulo a rasante - holgura - 0.02 (solo hacia abajo, nunca bajo el pasillo de la pista). -> nodos."""
    ter = bpy.data.objects.get('TERRENO')
    nx_, c_ = T['nx'], T['cell']
    puntos = []
    for a, b in zip(pts3[:-1], pts3[1:]):
        vx, vy = b[0] - a[0], b[1] - a[1]
        ls = math.hypot(vx, vy)
        if ls < 1e-6:
            continue
        nxp, nyp = -vy / ls, vx / ls
        n_s = max(1, int(math.ceil(ls / paso_l)))
        n_u = max(1, int(math.ceil(semiancho / paso_u)))
        for t_ in range(n_s + 1):
            f = t_ / float(n_s)
            px_, py_, pz_ = a[0] + vx * f, a[1] + vy * f, a[2] + (b[2] - a[2]) * f
            for m_ in range(-n_u, n_u + 1):
                lat_ = semiancho * m_ / float(n_u)
                puntos.append((px_ + nxp * lat_, py_ + nyp * lat_, pz_))
    tocados = set()
    for _it in range(2):
        mods = {}
        for (x, y, zp) in puntos:
            zt, nodos = _z_tri(x, y)
            if zt > zp - holgura:
                for kk in nodos:
                    if T['z'][kk] > zp - holgura - 0.02:
                        mods[kk] = min(mods.get(kk, T['z'][kk]), zp - holgura - 0.02)
        if not mods:
            break
        for kk, zn in mods.items():
            if T['mar'][kk] and T['z'][kk] < 0.5:
                continue
            xk, yk = T['x0'] + (kk % nx_) * c_, T['y0'] + (kk // nx_) * c_
            zn = _proteger_pista(xk, yk, T['z'][kk], zn)
            if zn < T['z'][kk] - 0.005:
                _poner_celda(ter, kk, T['z'][kk], zn, T['z'][kk] - zn > 2.0)
                tocados.add(kk)
    if ter is not None and tocados:
        ter.data.update()
    return len(tocados)

def _tallar_sendero(pts3, semiancho, dz=-0.15, evitar=None, alcance=25.0, sep_rama=15.0, pisada=2.0):
    """v2 integrador (E2-03/D2-09): banqueta de un SENDERO de montana. (b) Cada celda mira la rama mas cercana de
    CADA rama del sendero (tramos separados > sep_rama m por la polilinea): fuera de la zona llana de la mas
    cercana, z = clamp(z, max_k(zc_k - e_k*terr), min_k(zc_k + e_k*desm)) (y la media si se cruzan): sin el muro de
    terreno de una celda entre las dos ramas de cada horquilla. (c) Taludes segun la pendiente natural g de la celda
    (desm = clip(g+0.5, 1, 2), terr = clip(g+0.4, 0.7, 1.4), alcance 25 m): el corte cierra solo contra la ladera.
    (d) Roca solo en cortes > 2.5 m. (a) Pase de GARANTIA sobre la triangulacion real (cada 1 m y en lat -2..2 cada
    0.5 m): si el terreno asoma sobre la pisada - 0.05 se bajan los 3 nodos del triangulo; si en el borde la pisada
    vuela > 0.4 m, se suben (el canto de 0.35 tapa el resto). Antes: 25 % de la pisada bajo la hierba (hasta 1.7 m)
    y 5.7 % volando > 0.6 m con la rejilla de 4 m y un camino de 4 m."""
    ter = bpy.data.objects.get('TERRENO')
    nx_, c_ = T['nx'], T['cell']
    reach = semiancho + alcance
    acc = [0.0]
    for k in range(1, len(pts3)):
        acc.append(acc[-1] + math.hypot(pts3[k][0] - pts3[k - 1][0], pts3[k][1] - pts3[k - 1][1]))
    cand = {}
    for kseg, (a, b) in enumerate(zip(pts3[:-1], pts3[1:])):
        vx, vy = b[0] - a[0], b[1] - a[1]
        l2 = vx * vx + vy * vy
        ls = math.sqrt(l2)
        i0 = max(0, int((min(a[0], b[0]) - reach - T['x0']) / c_)); i1 = min(nx_ - 1, int((max(a[0], b[0]) + reach - T['x0']) / c_) + 1)
        j0 = max(0, int((min(a[1], b[1]) - reach - T['y0']) / c_)); j1 = min(T['ny'] - 1, int((max(a[1], b[1]) + reach - T['y0']) / c_) + 1)
        for j in range(j0, j1 + 1):
            y = T['y0'] + j * c_
            for i in range(i0, i1 + 1):
                x = T['x0'] + i * c_
                f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a[0]) * vx + (y - a[1]) * vy) / l2))
                d = math.hypot(x - a[0] - vx * f, y - a[1] - vy * f)
                if d > reach:
                    continue
                cand.setdefault(j * nx_ + i, []).append((d, a[2] + (b[2] - a[2]) * f, acc[kseg] + ls * f))
    cambios = {}
    for k, lst in cand.items():
        x = T['x0'] + (k % nx_) * c_
        y = T['y0'] + (k // nx_) * c_
        if evitar is not None and evitar(x, y):
            continue
        z = T['z'][k]
        if T['mar'][k] and z < 0.5:
            continue
        lst.sort()
        ramas = []
        for cn in lst:
            if all(abs(cn[2] - r_[2]) > sep_rama for r_ in ramas):
                ramas.append(cn)
                if len(ramas) >= 4:
                    break
        if ramas[0][0] - semiancho <= 0.0:
            z_new = ramas[0][1] + dz
        else:
            i, j = k % nx_, k // nx_
            ia, ib = max(0, i - 1), min(nx_ - 1, i + 1)
            ja, jb = max(0, j - 1), min(T['ny'] - 1, j + 1)
            gx = (T['z'][j * nx_ + ib] - T['z'][j * nx_ + ia]) / (max(1, ib - ia) * c_)
            gy = (T['z'][jb * nx_ + i] - T['z'][ja * nx_ + i]) / (max(1, jb - ja) * c_)
            g = math.hypot(gx, gy)
            desm, terr = min(2.0, max(1.0, g + 0.5)), min(1.4, max(0.7, g + 0.4))
            lo, hi = -1e9, 1e9
            for (d_, ze_, _s) in ramas:
                e_ = max(0.0, d_ - semiancho)
                lo = max(lo, ze_ + dz - e_ * terr)
                hi = min(hi, ze_ + dz + e_ * desm)
            z_new = (lo + hi) / 2.0 if lo > hi else min(max(z, lo), hi)
        z_new = _proteger_pista(x, y, z, z_new)
        if abs(z_new - z) > 0.02:
            cambios[k] = z_new
    n_c = 0
    for k, z_new in cambios.items():
        z = T['z'][k]
        _poner_celda(ter, k, z, z_new, z - z_new > 2.5)
        n_c += 1
    # (a) pase de garantia sobre la pisada
    puntos = []
    for a, b in zip(pts3[:-1], pts3[1:]):
        vx, vy = b[0] - a[0], b[1] - a[1]
        ls = math.hypot(vx, vy)
        if ls < 1e-6:
            continue
        nxp, nyp = -vy / ls, vx / ls
        n_s = max(1, int(math.ceil(ls / 1.0)))
        for t_ in range(n_s):
            f = t_ / float(n_s)
            px_, py_, pz_ = a[0] + vx * f, a[1] + vy * f, a[2] + (b[2] - a[2]) * f
            for m_ in range(-4, 5):
                lat_ = pisada * m_ / 4.0
                puntos.append((px_ + nxp * lat_, py_ + nyp * lat_, pz_ - 0.02 * abs(lat_), abs(m_) == 4))
    def _nodo_ok(kk):
        xk, yk = T['x0'] + (kk % nx_) * c_, T['y0'] + (kk // nx_) * c_
        if T['mar'][kk] and T['z'][kk] < 0.5:
            return False
        return evitar is None or not evitar(xk, yk)
    tocados = set()
    # subir: los 3 nodos hasta pisada - 0.35 (el canto de la cinta tapa el resto); bajar: los nodos que pasan de
    # pisada - 0.07. La ultima pasada siempre baja (nunca hierba sobre el camino). (Probado tambien con deltas
    # minimos por triangulo: peor, 2x bordes volados.)
    for it in range(3):
        if it < 2:
            mods = {}
            for (x, y, zp, borde) in puntos:
                if not borde:
                    continue
                zt, nodos = _z_tri(x, y)
                if zt < zp - 0.4:
                    for kk in nodos:
                        mods[kk] = max(mods.get(kk, T['z'][kk]), zp - 0.35)
            for kk, zn in mods.items():
                if zn > T['z'][kk] + 0.02 and _nodo_ok(kk):
                    _poner_celda(ter, kk, T['z'][kk], zn, False)
                    tocados.add(kk)
        mods = {}
        for (x, y, zp, borde) in puntos:
            zt, nodos = _z_tri(x, y)
            if zt > zp - 0.05:
                for kk in nodos:
                    if T['z'][kk] > zp - 0.07:
                        mods[kk] = min(mods.get(kk, T['z'][kk]), zp - 0.07)
        for kk, zn in mods.items():
            if not _nodo_ok(kk):
                continue
            xk, yk = T['x0'] + (kk % nx_) * c_, T['y0'] + (kk // nx_) * c_
            zn = _proteger_pista(xk, yk, T['z'][kk], zn)
            if zn < T['z'][kk] - 0.005:
                _poner_celda(ter, kk, T['z'][kk], zn, False)
                tocados.add(kk)
    n_g = len(tocados)
    asoma = sum(1 for (x, y, zp, b_) in puntos if _z_tri(x, y)[0] > zp - 0.05)
    vuela = sum(1 for (x, y, zp, b_) in puntos if b_ and _z_tri(x, y)[0] < zp - 0.6)
    vuela1 = sum(1 for (x, y, zp, b_) in puntos if b_ and _z_tri(x, y)[0] < zp - 1.0)
    if ter is not None:
        ter.data.update()
    log('sendero: banqueta %d celdas, garantia %d nodos; de %d puntos de la pisada (%d de borde) asoman %d; bordes con '
        'el terreno > 0.6 m por debajo %d y > 1.0 m (mas que el canto de la cinta) %d'
        % (n_c, n_g, len(puntos), sum(1 for p_ in puntos if p_[3]), asoma, vuela, vuela1))
    return n_c

def zona_edicolas():
    """RONDA 15: cada calle o travesia del plan que muere contra la ladera (sin sitio para
    plazoleta) y cada salida de la ultima terraza que no usa un sendero termina en una
    PLAZUELA tallada en el talud con una EDICOLA (capillita votiva) al fondo."""
    ik = M.get('italiano_kit')
    puntos = [(float(a), float(b), float(c), float(d), float(e)) for (a, b, c, d, e) in PUEBLO_INFO.get('sin_destino', [])]
    usadas = PUEBLO_INFO.get('salidas_usadas', set())
    for s_ in PUEBLO_INFO.get('salidas', []):
        if s_.get('id') in usadas:
            continue
        puntos.append((float(s_['x']), float(s_['y']), float(s_['z']), float(s_['dx']), float(s_['dy'])))
    m_ad = _mat_simple('MAT_CAMINO_adoquin_plaza', (0.55, 0.50, 0.46, 1), 0.9)
    bpy.context.view_layer.update()
    rocas_t = [o for o in root_col.all_objects if o.type == 'MESH' and o.name.startswith(('TUNEL_acantilado', 'PENON_puente_roca', 'PENON_roca'))]
    def _bajo_roca(x_, y_, z_):
        for ro in rocas_t:
            inv = ro.matrix_world.inverted()
            a = inv @ Vector((x_, y_, z_ + 1.0))
            b = inv @ Vector((x_, y_, z_ + 250.0))
            d = b - a
            if ro.ray_cast(a, d.normalized(), distance=d.length)[0]:
                return True
        return False
    # v3 integrador (N2 de (-552, 595) y (-427, 521)): ningun muro (CAMINO_muro: terrazas del plan, rellenos, pretiles)
    # por encima de la losa de la plazuela: CAMINO_muro.055 cruzaba CALLE_plaza_fondo.003 y .039/.041 la .002 (el
    # extremo del muro en mitad del disco). Se prueba el radio 4.5 / 3.8 y adelantar el disco 1.5-3 m; si ninguna
    # variante queda libre se usa la de siempre (y se avisa)
    muros_v = {}
    for o in root_col.objects:
        if o.type == 'MESH' and o.name.startswith('CAMINO_muro'):
            mw_o = o.matrix_world
            for v_o in o.data.vertices:
                w_o = mw_o @ v_o.co
                muros_v.setdefault((int(w_o.x // 8), int(w_o.y // 8)), []).append((w_o.x, w_o.y, w_o.z))
    def _muro_en_disco(cx_, cy_, r_, z_):
        for i_ in range(int((cx_ - r_ - 1.0) // 8), int((cx_ + r_ + 1.0) // 8) + 1):
            for j_ in range(int((cy_ - r_ - 1.0) // 8), int((cy_ + r_ + 1.0) // 8) + 1):
                for (a_, b_, c_) in muros_v.get((i_, j_), ()):
                    if c_ > z_ + 0.1 and math.hypot(a_ - cx_, b_ - cy_) < r_ + 0.4:
                        return True
        return False
    n_ = 0
    n_muro_av = 0
    hechos = []
    for (x, y, z, dx, dy) in puntos:
        if any(math.hypot(x - a, y - b) < 14.0 for (a, b) in hechos):
            continue
        if _bajo_roca(x, y, z):
            continue          # nunca bajo un saliente de roca (el morro del McLaren)
        variantes = [(4.5, 0.0), (4.5, 1.5), (3.8, 0.0), (3.8, 1.5), (4.5, 3.0)]
        elegida = None
        for (r_v, sh_v) in variantes:
            cxv, cyv = x + dx * (r_v - 0.8 + sh_v), y + dy * (r_v - 0.8 + sh_v)
            if not _muro_en_disco(cxv, cyv, r_v, z):
                elegida = (r_v, cxv, cyv)
                break
        if elegida is None:
            n_muro_av += 1
            elegida = (4.5, x + dx * 3.7, y + dy * 3.7)
            log('edicolas: AVISO plazuela en (%.0f, %.0f) con un muro cruzando (sin variante libre)' % (x, y))
        r, cx_, cy_ = elegida
        if _bajo_roca(cx_, cy_, z):
            continue          # nunca bajo un saliente de roca (el morro del McLaren)
        if any(math.hypot(cx_ - o.location.x, cy_ - o.location.y) < r + 4.0 for o in root_col.objects
               if o.parent is None and o.name.startswith('CASAS_')):
            continue
        if pendiente_terreno(cx_, cy_) > 0.8 or tallar_circulo(cx_, cy_, r, z) < 0:
            continue          # v1 (G9): ladera demasiado fuerte para tallar la plazuela sin dejar un escalon
        circ = [(r * math.cos(2 * math.pi * k / 18), r * math.sin(2 * math.pi * k / 18)) for k in range(18)]
        # v2 integrador (C2-12): sin hierba por encima de la losa (garantia sobre la malla real) y canto VARIABLE
        # hasta el terreno mas bajo del borde (r y r+0.5) + 0.3 (antes 0.7 fijo: hasta 1.3 m de aire bajo el borde)
        _garantia_losa(_puntos_disco(cx_, cy_, r + 0.2), z + 0.06)
        z_min_b = min(_z_tri(cx_ + rr_ * math.cos(2 * math.pi * k / 24), cy_ + rr_ * math.sin(2 * math.pi * k / 24))[0]
                      for k in range(24) for rr_ in (r, r + 0.5))
        canto_p = max(0.7, (z + 0.06) - z_min_b + 0.3)
        vs = [(a, b, 0.0) for (a, b) in circ] + [(a, b, -canto_p) for (a, b) in circ]
        fs = [tuple(range(18)), tuple(range(35, 17, -1))] + [(k, 18 + k, 18 + (k + 1) % 18, (k + 1) % 18) for k in range(18)]
        me = bpy.data.meshes.new('CALLE_plaza_fondo')
        me.from_pydata(vs, [], fs)
        me.materials.append(m_ad)
        ob = bpy.data.objects.new('CALLE_plaza_fondo', me)
        root_col.objects.link(ob)
        ob.location = (cx_, cy_, z + 0.06)
        PLAZAS_POLY.append([(cx_ + a, cy_ + b) for (a, b) in circ])
        if ik is not None and hasattr(ik, 'build_capitella'):
            ed = clone(ik.build_capitella(LIB, seed=40 + n_), (cx_ + dx * (r - 1.0), cy_ + dy * (r - 1.0), z + 0.06),
                       math.atan2(-dy, -dx) - math.pi / 2)        # mirando a la calle
            ed.name = 'ITAL_capitella'
        if 'cipres' in lib:
            for sg in (1.0, -1.0):
                c_ = clone(lib['cipres'], (cx_ + dx * (r - 1.6) - dy * sg * 2.6, cy_ + dy * (r - 1.6) + dx * sg * 2.6, z + 0.06), rnd.uniform(0, 6.28))
                c_.name = 'VEG_plazoleta'
        hechos.append((x, y))
        n_ += 1
    if bpy.data.objects.get('TERRENO') is not None:
        bpy.data.objects['TERRENO'].data.update()
    log('edicolas: %d plazuelas con capillita al final de calles/salidas sin destino (%d con muro cruzando)' % (n_, n_muro_av))

PUERTO_INFO = {}
def zona_puerto():
    p0 = frame(60)
    # centro de la marina: 190 m a la izquierda de la recta, pegada a la costa
    cxp = p0['x'] + p0['nx'] * 190
    cyp = p0['y'] + p0['ny'] * 190
    pk = M['puerto_kit']
    R_DQ, ARCO_DQ = 145.0, 200.0
    dique = pk.build_dique(LIB, radio=R_DQ, arco_grados=ARCO_DQ)
    rot_dq = rot_facing_road(60, 1)
    dq = clone(dique, (cxp, cyp, 0.0), rot_dq)
    bpy.context.view_layer.update()
    PUERTO_INFO.update({'centro': (cxp, cyp), 'rot': rot_dq, 'R': R_DQ,
                        'a0': math.radians(270.0 - ARCO_DQ / 2), 'a1': math.radians(270.0 + ARCO_DQ / 2)})
    # v1 integrador (A-13): el faro va en el MORRO libre del dique (extremo a1; la escollera llega al a0),
    # sobre su plataforma (z 3.25); antes estaba en el agua, dentro de la darsena, con un velero al lado
    faro = pk.build_faro(LIB)
    a1_ = PUERTO_INFO['a1']
    wf = dq.matrix_world @ Vector((R_DQ * math.cos(a1_), R_DQ * math.sin(a1_), 3.25))
    clone(faro, (wf.x, wf.y, wf.z), 0.0)
    # marina LLENA como en la pelicula; v1 integrador (A-13/N4): 3 pantalanes RADIALES de 60 m que arrancan en
    # la cara interior del dique (R-7) y apuntan al centro, con los barcos amarrados PERPENDICULARES a la
    # espina (proa al pantalan, 1 m de holgura) cada 9 m; antes los pantalanes iban sueltos en el agua y los
    # barcos en fila proa-popa se atravesaban entre si y con los pantalanes
    pan60 = pk.build_pantalan(LIB, largo=60.0)
    barcos = 0
    tipos_b = (('yate2', 18.0), ('velero', 12.0), ('yate', 25.0))
    for phi_ in (225.0, 270.0, 315.0):
        ang = rot_dq + math.radians(phi_)            # direccion radial (centro -> dique) en mundo
        dx_, dy_ = math.cos(ang), math.sin(ang)
        r_c = R_DQ - 7.0 - 30.0
        p_ = clone(pan60, (cxp + dx_ * r_c, cyp + dy_ * r_c, 0.0), ang - math.pi / 2)
        p_.name = 'PUERTO_pantalan'
        for m_ in range(6):
            d_ = R_DQ - 7.0 - 6.0 - m_ * 9.0
            for lado_ in (1, -1):
                tipo, esl = tipos_b[(barcos + m_) % 3]
                off_ = 1.8 + esl / 2.0 + 1.0
                bx = cxp + dx_ * d_ - dy_ * lado_ * off_
                by = cyp + dy_ * d_ + dx_ * lado_ * off_
                # todo el casco en agua profunda (proa, popa y centro)
                if all(z_terreno(bx - dy_ * lado_ * f_ * esl / 2, by + dx_ * lado_ * f_ * esl / 2) < -1.0 for f_ in (-1.0, 0.0, 1.0)):
                    # eslora (+Y del kit) perpendicular a la espina, proa hacia el pantalan
                    clone(lib[tipo], (bx, by, 0.0), ang + (math.pi if lado_ > 0 else 0.0) + rnd.uniform(-0.03, 0.03))
                    barcos += 1
    # veleros navegando en mar abierto
    for k in range(7):
        x = cxp + rnd.uniform(-420, 160)
        y = cyp + rnd.uniform(-380, 120)
        if z_terreno(x, y) < -2.5 and math.hypot(x - cxp, y - cyp) > R_DQ + 25.0:   # fuera de la darsena
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
    def _amarrar(s_m, side, off, tipo, seed, **kw_y):
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
            try:
                ob_ = yk.build_yate(LIB, eslora=32.0 if seed % 2 else 26.0, seed=seed, **kw_y)
            except TypeError:
                ob_ = yk.build_yate(LIB, eslora=32.0 if seed % 2 else 26.0, seed=seed)
        y_ = clone(ob_, (x, y, 0.0), rot)
        y_.name = 'YATE_' + tipo
        n_y += 1
        return y_
    # marina VIP frente a la recta de meta (lado del mar): pantalan + yates en fila
    s_a = L - 130.0
    # v1 integrador (A-13): el pantalan VIP quedaba a 12 m de la orilla en toda su longitud. Se busca la
    # orilla (terreno < 0.3) por la normal en 5 puntos de sus 100 m y su borde interior va a 0.5 m de la
    # orilla mas saliente; los yates que lo acompanan se desplazan lo mismo
    q_v = frame(s_a + 60)
    t_v = tangent(s_a + 60)
    off_v = 52.0
    d_or = []
    for xv in (0.0, 25.0, 50.0, 75.0, 100.0):
        bx_, by_ = q_v['x'] + t_v[0] * (xv - 45.0), q_v['y'] + t_v[1] * (xv - 45.0)
        for o_ in range(14, 90):
            dd_ = q_v['w'] / 2 + o_ * 1.0
            if z_terreno(bx_ + q_v['nx'] * dd_, by_ + q_v['ny'] * dd_) < 0.3:
                d_or.append(o_ * 1.0)
                break
    if d_or:
        off_v = max(d_or) + 0.5 + 2.05
    dv = off_v - 52.0
    for k, s_m in enumerate(range(int(s_a), int(s_a) + 120, 40)):
        _amarrar(s_m, 1, 62.0 + dv, 'yate', k)
    _amarrar(s_a + 60, 1, 118.0 + dv, 'super', 5)
    for k, s_m in enumerate(range(int(s_a) - 30, int(s_a) + 150, 45)):
        _amarrar(s_m, 1, 92.0 + dv, 'lancha', 10 + k)
    if hasattr(yk, 'build_pantalan_vip'):
        q = q_v
        t = t_v
        px, py = q['x'] + q['nx'] * (q['w'] / 2 + off_v) - t[0] * 45.0, q['y'] + q['ny'] * (q['w'] / 2 + off_v) - t[1] * 45.0
        if _agua(px, py) or z_terreno(px, py) < 0.0:
            pv = yk.build_pantalan_vip(LIB, largo=100.0, seed=1)
            p_ = clone(pv, (px, py, 0.0), math.atan2(t[1], t[0]))
            p_.name = 'YATE_pantalan'
    # y dos yates frente al paseo-mirador (sector casino) y el retorno costero
    _sd_mir = int(G['miradores'][0]['side']) if G.get('miradores') else 1    # ronda 15: el mirador esta en el lado del mar real
    # v2 integrador (I-R2-06): fondeados en mar abierto -> sin pasarela de alfombra roja bajando al agua, y cada
    # uno con su semilla (antes int(s) % 4 = 0 en los cuatro: clones identicos). Las defensas colgadas siguen
    # (build_yate aun no tiene parametro para quitarlas: yates_kit)
    for k_y, (s_m, off, sd) in enumerate(((3060, 70.0, _sd_mir), (3120, 110.0, _sd_mir), (4700, 80.0, 1), (4780, 120.0, 1))):
        _amarrar(s_m, sd, off, 'yate', 21 + k_y, pasarela=False)
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

# RONDA 15: el pueblo sale del PLAN URBANO (urbanismo.py -> urbanismo.json): calles por
# terrazas, enlaces con valla, travesias, rampas, escaleras, muros, casas en solares sin
# solapes, plazoletas y plazas. zona_pueblo() antigua queda de reserva si falta el plan.
PUEBLO_INFO = {'urbanismo': False, 'salidas': []}
PLAZAS_POLY = []      # v1 (N2 de D): poligonos de plazas/plazoletas/fondos de saco: sin arboles dentro (despeje_final)
def zona_pueblo_urbanismo():
    ruta_u = os.environ.get('URBANISMO', BASE + r'\03_blender\urbanismo.json')
    if not os.path.exists(ruta_u):
        log('urbanismo.json no existe: pueblo antiguo (fila)')
        return zona_pueblo()
    spec_u = importlib.util.spec_from_file_location('urbanismo_escena', BASE + r'\03_blender\urbanismo_escena.py')
    ue = importlib.util.module_from_spec(spec_u)
    spec_u.loader.exec_module(ue)
    _rej = {}
    for _i in range(N):
        _rej.setdefault((int(S[_i]['x'] // 30), int(S[_i]['y'] // 30)), []).append(_i)
    def _dist_pista(x, y):
        """distancia al BORDE del asfalto (muestra mas cercana; 1e9 si lejos de todo)."""
        kx, ky = int(x // 30), int(y // 30)
        best = 1e9
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                for _i in _rej.get((kx + ddx, ky + ddy), ()):
                    q = S[_i]
                    best = min(best, math.hypot(x - q['x'], y - q['y']) - q['w'] / 2)
        return best
    ctx = {'clone': clone, 'root_col': root_col, 'LIB': LIB, 'M': M, 'lib': lib, 'log': log,
           'z_terreno': z_terreno, 'rnd': rnd, 'zocalo_global': _zocalo_global, 'mat_simple': _mat_simple,
           'dist_pista': _dist_pista}
    info_u = ue.construir(ctx, ruta_u)
    PUEBLO_INFO.update({'urbanismo': True, 'salidas': info_u.get('salidas', []), 'casas': info_u.get('casas', 0),
                        'ejes': info_u.get('ejes', []), 'huellas': info_u.get('huellas', []),
                        'sin_destino': info_u.get('sin_destino', []),
                        'fuentes': info_u.get('fuentes', [])})
    PLAZAS_POLY.extend(info_u.get('plazas_poly', []))
    # plaza del AYUNTAMIENTO entre los dos barrios (s 1160, fuera de los sectores del plan).
    # v1 integrador (D5/C-02/N1 de B): en el lado -1 la plaza quedaba 29 m por debajo de una ladera del 75 %
    # y la explanada dejaba un tajo vertical de 30-45 m. Pasa al lado +1, donde el terreno esta a -0.8..-7 m
    # de la pista hasta 45 m (una hondonada): plaza LLANA a la cota de la calle, sobre relleno, con la losa
    # del mercado delante de la fachada (C-09), campanile al lado y acceso con valla desde la pista
    LADO_AY, S_AY = 1, 1160
    q_a = frame(S_AY)
    z_pl = q_a['z'] - q_a['lat'] * LADO_AY * q_a['w'] / 2.0 + 0.15      # borde peraltado de ese lado + 0.15
    (p_a, _) = pos_side(S_AY, LADO_AY, 26)
    rot_a = rot_facing_road(S_AY, LADO_AY)
    ay = clone(lib['ayuntamiento'], (p_a[0], p_a[1], z_pl), rot_a)
    explanar(ay, margen=4.0)
    (p_c, _) = pos_side(1130, LADO_AY, 22)
    ca = clone(lib['campanile'], (p_c[0], p_c[1], z_pl), rot_facing_road(1130, LADO_AY))
    explanar(ca, margen=3.0)
    rl_a = _rect_local(ay)
    if rl_a is not None:
        _inv_a, ax0, ax1, ay0, ay1 = rl_a
        mw_a = ay.matrix_world
        # losa de la plaza: 26 m a lo largo de la fachada, de 0.5 m delante de ella hasta 4.5 m del asfalto
        prof_l = max(6.0, 26.0 - ay1 - 0.5 - 4.5)
        y_l0, y_l1 = ay1 + 0.5, ay1 + 0.5 + prof_l
        esq_l = [mw_a @ Vector((a_, b_, 0.0)) for (a_, b_) in ((-13.0, y_l0), (13.0, y_l0), (13.0, y_l1), (-13.0, y_l1))]
        z_min_l = min(z_terreno(p_.x, p_.y) for p_ in esq_l)
        cxl, cyl = sum(p_.x for p_ in esq_l) / 4.0, sum(p_.y for p_ in esq_l) / 4.0
        # v2 integrador (C2-12): canto como mucho 1.3 m (era un tambor de 2.12 m); el relleno lo pone explanar
        # (terraplen 0.66) y la garantia de abajo quita la hierba que asomaba por una esquina
        gro = min(1.3, max(0.4, z_pl - z_min_l + 0.5))
        vs_l = [(p_.x - cxl, p_.y - cyl, 0.0) for p_ in esq_l] + [(p_.x - cxl, p_.y - cyl, -gro) for p_ in esq_l]
        me_l = bpy.data.meshes.new('CALLE_plaza_ayto')
        me_l.from_pydata(vs_l, [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
        me_l.materials.append(_mat_simple('MAT_CAMINO_adoquin_plaza', (0.55, 0.50, 0.46, 1), 0.9))
        import bmesh as _bml
        _bb = _bml.new()
        _bb.from_mesh(me_l)
        _bml.ops.recalc_face_normals(_bb, faces=_bb.faces)
        _bb.to_mesh(me_l)
        _bb.free()
        losa = bpy.data.objects.new('CALLE_plaza_ayto', me_l)
        root_col.objects.link(losa)
        losa.location = (cxl, cyl, z_pl + 0.06)
        explanar(losa, margen=1.0, alcance=12.0, desmonte=1.0, terraplen=0.66)
        _garantia_losa([tuple(mw_a @ Vector((a_, b_, 0.0)))[:2] for a_ in [-13.0 + 1.0 * k_ for k_ in range(27)]
                        for b_ in [y_l0 + (y_l1 - y_l0) * j_ / 8.0 for j_ in range(9)]], z_pl + 0.06)
        toldos =[tuple(mw_a @ Vector((a_, ay1 + 6.5, 0.0)))[:2] for a_ in (-9.0, 0.0, 9.0)]
        PUEBLO_INFO['plaza_ayto_losa'] = {'poly': [(p_.x, p_.y) for p_ in esq_l], 'z': z_pl + 0.06, 'rot': rot_a,
                                          'toldos': toldos, 's0': S_AY - 13.0, 's1': S_AY + 13.0, 'lado': LADO_AY}
        PLAZAS_POLY.append([(p_.x, p_.y) for p_ in esq_l])
    if bpy.data.objects.get('TERRENO') is not None:
        bpy.data.objects['TERRENO'].data.update()
    PUEBLO_INFO['plaza_ayto'] = (p_a[0], p_a[1], z_pl)
    log('pueblo: plaza del ayuntamiento en s=%.0f lado %+d (z=%.1f)' % (S_AY, LADO_AY, z_pl))
safe('zona_pueblo', zona_pueblo_urbanismo)

# ============ LADERA DE TIERRA ============
def _d_borde_cualquiera(x, y):
    """Distancia al borde del asfalto de CUALQUIER tramo de pista (rejilla de 30 m: exacta hasta 30 m)."""
    kx, ky = int(x // 30), int(y // 30)
    best = 1e9
    for ddx in (-1, 0, 1):
        for ddy in (-1, 0, 1):
            for _i in _REJ_M.get((kx + ddx, ky + ddy), ()):
                best = min(best, math.hypot(x - S[_i]['x'], y - S[_i]['y']) - S[_i]['w'] / 2.0)
    return best

def _sitio_lejos_pista(s_m, side, off, d_min=12.0):
    """v2 integrador (E2-05): sitio a `off` m del borde que este a >= d_min del borde de TODOS los tramos (en los
    lazos de tierra otro tramo vuelve a pasar cerca: VEG_roca.004 quedaba a 4.3 m de la trazada de s 1898). Prueba
    off+8, off+16 y luego el otro lado. -> (p, side) o None."""
    for sd_ in (side, -side):
        for o_ in (off, off + 8.0, off + 16.0):
            (p, _) = pos_side(s_m, sd_, o_)
            if _d_borde_cualquiera(p[0], p[1]) >= d_min:
                return p, sd_
    return None

def zona_tierra():
    s_m = 1570
    k = 0
    n_fuera = 0
    while s_m < 2370:
        tipo = ('pino', 'cipres', 'pino2')[k % 3]
        side = 1 if k % 2 else -1
        res_ = _sitio_lejos_pista(s_m, side, 15 + (k % 3) * 6)
        if res_ is not None:
            clone(lib[tipo], res_[0], rnd.uniform(0, 6.28))
        else:
            n_fuera += 1
        s_m += 52
        k += 1
    # v3 integrador (E6): las filas continuas de pacas sobre los terraplenes y las pacas de las curvas 15-25 van en
    # pacas_tierra(), DESPUES de los senderos y de las camaras: la banqueta del sendero CIMA rebajaba la ladera de
    # s 1706-1734 (+1) cuando las filas ya estaban decididas con el terreno de antes (caida de 2.4-16 m sin barrera)
    log('tierra: %d arboles sin sitio a >= 12 m de la pista' % n_fuera)
    # v1 integrador (N1 de E): la curva 26 es la horquilla mas cerrada (R 6.3 m) al final de la bajada del
    # 16.5 %: fila CONTINUA de pacas en su exterior (signo de la curvatura) de s_c-20 a s_c+20, a 2.5 m del
    # borde. Se llaman CARRERA_paca_tierra: exportar_ac las hace 1WALL_ (frenan al que se pasa de frenada)
    if 26 in CURVAS:
        s_c = CURVAS[26]['s_idx'] * paso
        pa_, pb_ = frame(s_c - 8), frame(s_c + 8)
        outside = 1 if (pa_['ny'] * pb_['nx'] - pa_['nx'] * pb_['ny']) > 0 else -1
        s_m = s_c - 20.0
        n_p26 = 0
        while s_m <= s_c + 20.0:
            (pp, _) = pos_side(s_m, outside, 2.5)
            pk_ = clone(lib['paca'], pp, rot_facing_road(s_m, outside))
            pk_.name = 'CARRERA_paca_tierra'
            n_p26 += 1
            ds_ = 1.0
            while ds_ < 6.0:
                (pq_, _) = pos_side(s_m + ds_, outside, 2.5)
                if math.hypot(pq_[0] - pp[0], pq_[1] - pp[1]) >= 2.9:
                    break
                ds_ += 0.5
            s_m += ds_
        log('tierra: %d pacas continuas en el exterior de la curva 26 (lado %+d)' % (n_p26, outside))
    # rocas de cima; v2 integrador (E2-05): a >= 12 m del borde de CUALQUIER tramo (el lazo vuelve a pasar cerca)
    for k in range(10):
        s_m = 1700 + k * 68
        res_ = _sitio_lejos_pista(s_m, 1 if k % 2 else -1, 26 + (k % 4) * 5)
        if res_ is not None:
            clone(lib['roca' if k % 3 else 'roca2'], res_[0], rnd.uniform(0, 6.28))
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
    if M.get('roca_casino') is not None or M.get('penon_pueblo') is not None:
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
        if M.get('roca_casino') is not None:
            # ronda 15: el terreno nuevo deja la ladera del contorno a la cota de la cresta
            # (tope ~121): la meseta va 12 m sobre la plaza, no 26 m sobre la base
            z_top_c = max(z_plaza + 12.2, z_base_c + 8.0)
        else:
            z_top_c = max(z_plaza + 12.2, z_base_c + 26.0)
        if M.get('roca_casino') is not None:
            # RONDA 15: penon NATURAL con carretera de bajada VISIBLE (assets/roca_casino.py);
            # se construye en la coleccion visible (usa ray-casts)
            r_c, info_c = M['roca_casino'].build(root_col, pts, z_base_c, z_top_c, (ent[0], ent[1], q37_['z'] + 0.1),
                                                 float(G.get('nivel_mar', 0.0)), seed=2,
                                                 casas_kit=M['casas_kit'], vegetacion_kit=M['vegetacion_kit'],
                                                 italiano_kit=M.get('italiano_kit'), yates_kit=M.get('yates_kit'),
                                                 terreno_fn=z_terreno, z_entrada=q37_['z'] + 0.1, log=log)
            bpy.context.view_layer.update()
            roca_c = next((o for o in [r_c] + list(r_c.children_recursive) if o.type == 'MESH' and o.name.startswith('PENON_roca')), None)
            if roca_c is None:
                roca_c = max((o for o in r_c.children_recursive if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
            nb_c = _limpiar_bajo_roca(roca_c)
            if info_c.get('centro_top'):
                cxc, cyc = float(info_c['centro_top'][0]), float(info_c['centro_top'][1])
            log('casino: roca_casino base z=%.0f -> meseta z=%.0f (radio %.0f), bajada %.0f m (pend. max %.1f%%, %d horquillas), %d objetos retirados'
                % (z_base_c, float(info_c.get('z_top', z_top_c)), float(info_c.get('radio_meseta', 0.0)), float(info_c.get('longitud_carretera', 0.0)),
                   100.0 * float(info_c.get('pendiente_max', 0.0)), int(info_c.get('n_horquillas', 0)), nb_c))
        else:
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
# pianos de la geometria en metros: (s_a, s_b, lado) con lado +1 = 'izq', -1 = 'der'
PIANOS_S = [(float(p_['a']) * paso, float(p_['b']) * paso, 1 if p_.get('lado') == 'izq' else -1) for p_ in (G.get('pianos') or [])]
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
        # tunel, sus bocas y la repisa de B8 entre la pista y el cortado al mar; v2 integrador (B2-04): s 300-660
        # (antes 402-642: la fila COCHE_fila.005 quedaba en s 360 sin ningun acceso, a 186 m del camino mas cercano)
        if min(abs(s_m - 480.0), L - abs(s_m - 480.0)) < 180.0:
            return None
        # v1 integrador (A-14/F-09/I5): nada de filas en la recta de meta ni en su frenada, a ningun lado
        # (estaban en el cesped del lado del mar en s 5016-5032, a 4 m del asfalto y sin barrera)
        if s_m > L - 300 or s_m < 230:
            return None
        # ni en los 80 m antes / 20 m despues de un piano del mismo lado (frenada y escapatoria)
        for pz_ in PIANOS_S:
            if pz_[2] == side and pz_[0] - 80.0 <= s_m <= pz_[1] + 20.0:
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
        if abs(z_borde - sum(zs) / len(zs)) > 1.6 + 0.25 * max(0.0, offset - 6.5):
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
    # preferencia 2: cualquier sitio valido a lo largo del circuito; v1 (F-09): el origen de la fila a
    # 14.5 m (los coches empiezan a 12 m del borde), no a 6.5 (la carroceria quedaba a 4 m del asfalto)
    # (si no cabe, a 9.5 m: carrocerias a 7 m, solo en rectas sin piano cerca)
    s_m = 30.0
    while s_m < L - 30:
        for side in (-1, 1):
            r = sitio_ok(s_m, side, 14.5) or sitio_ok(s_m, side, 9.5)
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
    if G.get('cumbres'):
        # RONDA 15: el terreno YA es un macizo con cumbres (terreno_montana.py): fuera las
        # cordilleras postizas y los penascos-cilindro de las cimas
        log('montanas de fondo: el macizo va en el terreno (%d cumbres), sin cordilleras ni penascos' % len(G['cumbres']))
        return
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
try:
    _SPEC_URB = json.load(open(BASE + r'\03_blender\urbanismo_spec.json', encoding='utf-8'))
except Exception:
    _SPEC_URB = {}
def _en_terraza_u(s_m, side):
    """True si en esa s y ese lado hay terrazas del plan urbano (bordillo alto + calle)."""
    s_m = s_m % L
    return any(float(c['s0']) <= s_m <= float(c['s1']) and int(c['lado']) == side for c in _SPEC_URB.get('sectores', []))

def zona_calle():
    ck = M.get('calle_kit')
    if not ck:
        return
    TRAMOS = [(630, 1090), (1270, 1550), (2490, 2750), (3190, 3450)]
    # v3 integrador (D11): farolas y macetas solo donde SU lado tiene acera (rango real de los vertices de cada ACERA_
    # de construir_pista) o terraza del plan: CALLE_farola.012 (s 1270, -1) y CALLE_maceta.009 (s 1284, +1) quedaban
    # sueltas en el prado antes de las aceras de s 1300 / 1286 (la secuencia aleatoria no cambia)
    acera_ok = []          # (lado, s0, s1) de cada ACERA_ (rango real de sus vertices)
    for ob_a in root_col.objects:
        if ob_a.type != 'MESH' or not ob_a.name.startswith('ACERA_'):
            continue
        mw_a = ob_a.matrix_world
        ss_a = {1: [], -1: []}
        for v_a in ob_a.data.vertices:
            w_a = mw_a @ v_a.co
            i_a = _muestra_cerca(w_a.x, w_a.y)
            q_a = S[i_a]
            d_a = (w_a.x - q_a['x']) * q_a['nx'] + (w_a.y - q_a['y']) * q_a['ny']
            if abs(d_a) < q_a['w'] / 2.0 + 8.0:
                ss_a[1 if d_a > 0 else -1].append(i_a * paso)
        for sg_a, l_a in ss_a.items():
            if len(l_a) >= 4 and max(l_a) - min(l_a) < L / 2:
                acera_ok.append((sg_a, min(l_a), max(l_a)))
    def _con_acera_lado(s_m, sg):
        s_m = s_m % L
        return _en_terraza_u(s_m, sg) or any(sg_a == sg and s0_a - 1.0 <= s_m <= s1_a + 1.0 for (sg_a, s0_a, s1_a) in acera_ok)
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
    n_sin_acera = [0]
    for (s0u, s1u) in TRAMOS:
        # farolas alternando aceras
        s_m = s0u
        k = 0
        while s_m < s1u:
            side = 1 if k % 2 else -1
            p = frame(s_m)
            if p['sec'] not in ('dirt', 'bridge') and (not acera_ok or _con_acera_lado(s_m, side)):
                (pp, _) = pos_side(s_m, side, 1.3)
                clone(lib['farola_c'], (pp[0], pp[1], p['z'] - 0.2),
                      rot_facing_road(s_m, side))
                n_far += 1
            elif p['sec'] not in ('dirt', 'bridge'):
                n_sin_acera[0] += 1
            s_m += 44
            k += 1
        # guirnaldas de banderines cruzando la calle
        s_m = s0u + 30
        while s_m < s1u:
            p = frame(s_m)
            if p['sec'] not in ('dirt', 'bridge'):
                # RONDA 15: junto a las terrazas del plan el poste va en el BORDILLO ALTO
                # (0.75 m del asfalto), no en la calle de servicio (antes a 3.5 m)
                # v1 integrador (D6): en las terrazas el poste va a 1.2 m del asfalto (dentro de la acera, que
                # va de 0.12 a 1.5 m) y en su sitio exacto: el redondeo de la luz lo acercaba hasta 0.25 m
                off = {sg: (1.2 if _en_terraza_u(s_m, sg) else 3.5) for sg in (1, -1)}
                luz_r = p['w'] + off[1] + off[-1]
                luz = round(luz_r * 2) / 2.0          # (solo como clave de la malla de la guirnalda)
                c_n = (off[1] - off[-1]) / 2.0
                if luz not in guirnaldas_cache:
                    guirnaldas_cache[luz] = ck.build_guirnalda(LIB, luz=luz)
                clone(guirnaldas_cache[luz], (p['x'] + p['nx'] * c_n, p['y'] + p['ny'] * c_n, p['z'] + 6.4),
                      rot_across(s_m))
                # postes en los dos extremos: la guirnalda ya no cuelga del aire
                for sg in (1, -1):
                    lt = sg * (p['w'] / 2.0 + off[sg])
                    z_p = p['z'] - p['lat'] * lt - (0.4 if off[sg] < 1.5 else 0.9)
                    clone(lib['poste_guirnalda'],
                          (p['x'] + p['nx'] * lt, p['y'] + p['ny'] * lt, z_p), 0.0)
                n_gui += 1
            s_m += 76
        # macetas junto a los bajos
        s_m = s0u + 15
        k = 0
        while s_m < s1u:
            side = -1 if k % 2 else 1
            p = frame(s_m)
            if p['sec'] not in ('dirt', 'bridge') and acera_ok and not _con_acera_lado(s_m, side):
                n_sin_acera[0] += 1
                rnd.uniform(0, 6.28)            # (misma secuencia aleatoria para lo que viene despues)
            elif p['sec'] not in ('dirt', 'bridge'):
                en_t = _en_terraza_u(s_m, side)
                # final (nada_en_pista): la maceta del kit mide 0.53 m de radio con las flores colgando; en la
                # acera alta (0.12-1.5 m) su centro va a 0.9 m: borde a >= 0.37 del asfalto (a 0.8 una flor
                # quedaba a 0.27 m segun el giro aleatorio: CALLE_maceta.021 en s 3436)
                (pp, _) = pos_side(s_m, side, 0.9 if en_t else 2.8)
                clone(lib['maceta'], (pp[0], pp[1], p['z'] + (0.32 if en_t else -0.18)),
                      rnd.uniform(0, 6.28))
                n_mac += 1
            s_m += 58
            k += 1
    # puestecillos de mercado en la plaza del ayuntamiento; v1 integrador (C-09): en fila SOBRE la losa de la
    # plaza, a 6 m de la fachada y a su cota (antes iban en el talud: una pata a 2.35 m del suelo)
    pl_ = PUEBLO_INFO.get('plaza_ayto_losa')
    if pl_:
        for k_, (tx_, ty_) in enumerate(pl_['toldos']):
            clone(ck.build_toldo_mercado(LIB, seed=k_ * 9 - 14), (tx_, ty_, pl_['z']), pl_['rot'])
    log('calle: %d farolas, %d guirnaldas, %d macetas (%d farolas/macetas sin acera ni terraza en su lado: no se ponen)'
        % (n_far, n_gui, n_mac, n_sin_acera[0]))
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
    # v3 (N2 de s 405): en el McLaren (sin materiales 'roca') la pared del taladro es su caliza oscura de grieta (antes
    # MAT_piedra, el ladrillo de portales y galerias)
    candidatos = [k for k, n in enumerate(mats) if 'roca_oscura' in n] or \
                 [k for k, n in enumerate(mats) if 'roca' in n] or \
                 [k for k, n in enumerate(mats) if 'caliza_grieta' in n] or \
                 [k for k, n in enumerate(mats) if 'caliza' in n and 'monte' not in n]
    if not candidatos:
        m = bpy.data.materials.get('MAT_piedra')
        if not m:
            return 0
        ob.data.materials.append(m)
        candidatos = [len(ob.data.materials) - 1]
    slot = candidatos[0]
    corr = [S[i % N] for i in range(i0, i1 + 1, 2)]
    # v3 integrador (N2 de s 405): la caja (lat < 12.5, z hasta +11) era mayor que el taladro (10.5 x 8 m) y cogia la
    # CARA de la rueda del McLaren en las dos bocas (275 caras mirando a lo largo de la pista y 119 hacia fuera del eje
    # con el ladrillo de los portales). Ahora lat < 11, z < pista + 8.5 y solo paredes paralelas a la pista que miran
    # al eje (|n.t| < 0.5) o el techo (n hacia abajo)
    m_n = ob.matrix_world.to_3x3().inverted().transposed()
    n = 0
    for f in ob.data.polygons:
        w = ob.matrix_world @ f.center
        nw = m_n @ f.normal
        if nw.length < 1e-9:
            continue
        nw.normalize()
        for q in corr:
            dx = w.x - q['x']; dy = w.y - q['y']
            lat = abs(dx * q['nx'] + dy * q['ny'])
            lon = abs(dx * q['ny'] - dy * q['nx'])
            if lat < 11.0 and lon < 2.5 and (q['z'] - 2.5) < w.z < (q['z'] + 8.5):
                if nw.z > -0.5:
                    if abs(nw.x * q['ny'] - nw.y * q['nx']) > 0.5:
                        break                       # mira a lo largo de la pista: cara de la rueda
                    if (-dx) * nw.x + (-dy) * nw.y <= 0.0:
                        break                       # mira hacia fuera del eje
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

def _galeria(i0, i1, half, alto, nombre, grosor=1.7):
    """v1 integrador (B1): boveda de piedra (galeria artificial) que sigue la pista entre los indices i0 e
    i1, con el perfil del taladro un poco mas estrecho (half/alto) y `grosor` de pared; tapa la roca que
    falta entre el arco de la boca y la seccion cerrada del tunel (y los huecos de la llanta del McLaren)."""
    perfil = [(-1.0, -0.15), (-1.0, 0.55), (-0.7, 0.85), (0.0, 1.0),
              (0.7, 0.85), (1.0, 0.55), (1.0, -0.15)]
    npf = len(perfil)
    esc = 1.0 + grosor / half
    verts, faces = [], []
    idxs = list(range(i0, i1 + 1))
    if len(idxs) < 2:
        return None
    for i in idxs:
        q = S[i % N]
        for (u, v) in perfil:                       # cara interior
            verts.append((q['x'] + q['nx'] * u * half, q['y'] + q['ny'] * u * half, q['z'] - 1.5 + v * alto))
        for (u, v) in perfil:                       # cara exterior
            verts.append((q['x'] + q['nx'] * u * half * esc, q['y'] + q['ny'] * u * half * esc,
                          q['z'] - 1.5 + v * alto * (esc if v > 0 else 1.0)))
    def vi(k, cara, j):
        return k * 2 * npf + cara * npf + j
    for k in range(len(idxs) - 1):
        for j in range(npf - 1):
            faces.append((vi(k, 0, j), vi(k + 1, 0, j), vi(k + 1, 0, j + 1), vi(k, 0, j + 1)))
            faces.append((vi(k, 1, j), vi(k, 1, j + 1), vi(k + 1, 1, j + 1), vi(k + 1, 1, j)))
        for j in (0, npf - 1):                      # pies (entre cara interior y exterior)
            faces.append((vi(k, 0, j), vi(k, 1, j), vi(k + 1, 1, j), vi(k + 1, 0, j)))
    for k in (0, len(idxs) - 1):                    # testeros
        for j in range(npf - 1):
            faces.append((vi(k, 0, j), vi(k, 0, j + 1), vi(k, 1, j + 1), vi(k, 1, j)))
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    me.validate()
    import bmesh as bm_
    bb = bm_.new()
    bb.from_mesh(me)
    bm_.ops.recalc_face_normals(bb, faces=bb.faces)
    bb.to_mesh(me)
    bb.free()
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
    mc = M.get('montana_mclaren') or M.get('montana_coche')
    es_mclaren = M.get('montana_mclaren') is not None
    if mc is not None:
        # RONDA 13: la rueda es la de un COCHE FOSIL COMPLETO (montana_coche). Origen
        # = centro de la rueda delantera, 26 m a la derecha de la calzada; el coche
        # queda con el morro tierra adentro (-n) y la zaga hacia el mar (+n); su lado
        # -Y mira a los coches que llegan (ambos lados llevan ruedas talladas).
        # RONDA 15: McLAREN de piedra (montana_mclaren): misma orientacion (comprobada
        # con encaje_mclaren: 'morro al mar' pisaria la horquilla 4-6), R=26, via 135,
        # zaga fundida en un penon sobre el mar y afloramiento rocoso en el morro.
        R_C, ANCHO_C = (26.0, 135.0) if es_mclaren else (40.0, 78.0)
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
        if es_mclaren:
            res_c = mc.build(col_tmp, radio=R_C, ancho=ANCHO_C, z_fondo=-(pf['z'] + 8.0), seed=11, lado_visible=-1,
                             enterrado='ambos', alto_montana=(83.2, 65.0), largo_macizo=(14.5, 4.8), talud_deg=(38.0, 52.0))
        else:
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
        _xs, _ys = [], []
        for _o in [r] + list(r.children_recursive):
            if _o.type == 'MESH':
                for _c in _o.bound_box:
                    _w = _o.matrix_world @ Vector(_c)
                    _xs.append(_w.x)
                    _ys.append(_w.y)
        _n_h = 0
        # v2 integrador (C2-06): la HUELLA REAL de la roca, no un rectangulo hasta 4.9R (127 m) que borraba 5 casas
        # del plan que no la tocan (solar004-007 y solar025, al pie del McLaren) y la losa de un fondo de saco
        # dejando su fuente sola en el cesped. Se quita una raiz si: (a) su caja (marco propio, con los hijos) cruza
        # la malla de roca (BVH overlap); (b) un rayo hacia arriba desde sus 4 esquinas y el centro (zmin + 0.5) da
        # en la roca (voladizo del morro o caja enterrada dentro); (c) su origen cae en spec['zonas_excluidas'] +
        # margen. Con una losa CALLE_plaza_fondo/plazoleta se van tambien su fuente, sus arboles y su pergola.
        from mathutils.bvhtree import BVHTree as _BVH
        bpy.context.view_layer.update()
        _dg_c = bpy.context.evaluated_depsgraph_get()
        _rocas_c = [o_ for o_ in [r] + list(r.children_recursive) if o_.type == 'MESH' and not o_.name.startswith('MCOCHE_veg')]
        _bvh_c = []
        for o_ in _rocas_c:
            try:
                _bvh_c.append((o_, o_.matrix_world.inverted(), _BVH.FromObject(o_, _dg_c)))
            except Exception as e_:
                log('tunel: sin BVH de %s (%s)' % (o_.name, e_))
        _zex = []
        for z_ in (_SPEC_URB.get('zonas_excluidas') or []):
            if z_.get('poligono'):
                _zex.append(([tuple(p_[:2]) for p_ in z_['poligono']], float(z_.get('margen', 0.0))))
        def _dentro_pol_t(px_, py_, pol_):
            # (_dentro_poly se define mas abajo en el fichero: aqui aun no existe)
            d_ = False
            for k_ in range(len(pol_)):
                (x1_, y1_), (x2_, y2_) = pol_[k_], pol_[(k_ + 1) % len(pol_)]
                if (y1_ > py_) != (y2_ > py_) and px_ < x1_ + (py_ - y1_) * (x2_ - x1_) / ((y2_ - y1_) or 1e-9):
                    d_ = not d_
            return d_
        def _en_zona_ex(x_, y_):
            for (pol_, mg_) in _zex:
                if _dentro_pol_t(x_, y_, pol_):
                    return True
                for k_ in range(len(pol_)):
                    (ax_, ay_), (bx_, by_) = pol_[k_], pol_[(k_ + 1) % len(pol_)]
                    vx_, vy_ = bx_ - ax_, by_ - ay_
                    l2_ = vx_ * vx_ + vy_ * vy_
                    f_ = 0.0 if l2_ < 1e-9 else max(0.0, min(1.0, ((x_ - ax_) * vx_ + (y_ - ay_) * vy_) / l2_))
                    if math.hypot(x_ - ax_ - vx_ * f_, y_ - ay_ - vy_ * f_) < mg_:
                        return True
            return False
        _CARAS_BOX = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        def _toca_roca(ob_):
            inv_o = ob_.matrix_world.inverted()
            xs_o, ys_o, zs_o = [], [], []
            for h_ in [ob_] + list(ob_.children_recursive):
                if h_.type != 'MESH' or h_.name.startswith('CASAS_zocalo'):
                    continue
                for c_ in h_.bound_box:
                    l_ = inv_o @ (h_.matrix_world @ Vector(c_))
                    xs_o.append(l_.x); ys_o.append(l_.y); zs_o.append(l_.z)
            if not xs_o:
                return False
            mw_o = ob_.matrix_world
            esq_o = [mw_o @ Vector((a_, b_, c_)) for c_ in (min(zs_o), max(zs_o))
                     for (a_, b_) in ((min(xs_o), min(ys_o)), (max(xs_o), min(ys_o)), (max(xs_o), max(ys_o)), (min(xs_o), max(ys_o)))]
            z_bajo = min(p_.z for p_ in esq_o)
            ptos_r = [Vector((p_.x, p_.y, z_bajo + 0.5)) for p_ in esq_o[:4]] + [Vector((sum(p_.x for p_ in esq_o[:4]) / 4.0, sum(p_.y for p_ in esq_o[:4]) / 4.0, z_bajo + 0.5))]
            for (ro_, inv_r, bvh_r) in _bvh_c:
                try:
                    bvh_b = _BVH.FromPolygons([tuple(inv_r @ p_) for p_ in esq_o], _CARAS_BOX)
                    if bvh_r.overlap(bvh_b):
                        return True
                except Exception:
                    pass
                for p_ in ptos_r:
                    a_ = inv_r @ p_
                    b_ = inv_r @ (p_ + Vector((0.0, 0.0, 300.0)))
                    d_ = b_ - a_
                    if bvh_r.ray_cast(a_, d_.normalized(), d_.length)[0] is not None:
                        return True
            return False
        _plazas_q = []
        for _ob in list(root_col.objects):
            try:
                if _ob.parent is not None or not _ob.name.startswith(('CASAS_', 'VEG_', 'OLI_', 'CALLE_', 'COCHE_', 'ITAL_', 'CAMINO_cartel')):
                    continue
                _lx, _ly = _ob.location.x, _ob.location.y
            except ReferenceError:
                continue
            if not (min(_xs) - 4 < _lx < max(_xs) + 4 and min(_ys) - 4 < _ly < max(_ys) + 4):
                continue
            if _en_zona_ex(_lx, _ly) or _toca_roca(_ob):
                if _ob.name.startswith(('CALLE_plaza_fondo', 'CALLE_plazoleta')):
                    rl_q = _rect_local(_ob)
                    if rl_q is not None:
                        _plazas_q.append(rl_q)
                for _ch in list(_ob.children_recursive):
                    bpy.data.objects.remove(_ch, do_unlink=True)
                bpy.data.objects.remove(_ob, do_unlink=True)
                _n_h += 1
        if _plazas_q:
            for _ob in list(root_col.objects):
                try:
                    if _ob.parent is not None or not _ob.name.startswith(('ITAL_fuente', 'VEG_plazoleta', 'ITAL_pergola')):
                        continue
                    _w = _ob.matrix_world.translation
                except ReferenceError:
                    continue
                for (inv_q, x0_, x1_, y0_, y1_) in _plazas_q:
                    l_ = inv_q @ Vector((_w.x, _w.y, 0.0))
                    if x0_ - 0.5 < l_.x < x1_ + 0.5 and y0_ - 0.5 < l_.y < y1_ + 0.5:
                        for _ch in list(_ob.children_recursive):
                            bpy.data.objects.remove(_ch, do_unlink=True)
                        bpy.data.objects.remove(_ob, do_unlink=True)
                        _n_h += 1
                        break
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
    if mc is not None and es_mclaren:
        # ronda 15: el McLaren solo se taladra a lo ancho del coche (+25 m por lado): un
        # tubo de 320 m cruzaba tambien el afloramiento del morro y el penon de la zaga
        i0t, i1t = idx(s_face - ANCHO_C / 2 - 25.0), idx(s_face + ANCHO_C / 2 + 25.0)
    tal = _taladro(i0t, i1t, 10.5, 9.5, 'TUNEL_taladro')  # seccion unica: la variable rompia el booleano
    # normales coherentes tambien en la roca (el loft puede venir mezclado)
    import bmesh as bm_
    bb = bm_.new()
    bb.from_mesh(roca.data)
    bm_.ops.recalc_face_normals(bb, faces=bb.faces)
    bb.to_mesh(roca.data)
    bb.free()
    cortado = False
    # ronda 15: cada solver parte de la malla ORIGINAL y un resultado que pierde mas de la
    # mitad de los vertices se rechaza (MANIFOLD dejaba el McLaren en 590 vertices y el
    # tunel 'abierto' porque ya no habia roca: solo quedaba su vegetacion flotando)
    _orig = roca.data.copy()
    _nv0 = len(_orig.vertices)
    for solver in ('EXACT', 'MANIFOLD', 'FAST'):
        if len(roca.data.vertices) != _nv0 or cortado is None:
            _viejo = roca.data
            roca.data = _orig.copy()
            if _viejo.users == 0:
                bpy.data.meshes.remove(_viejo)
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
        _ratio = len(roca.data.vertices) / float(max(1, _nv0))
        log('tunel: solver %s -> rayos bloqueados %d/9, malla %d -> %d vertices (%.0f %%)'
            % (solver, choques, _nv0, len(roca.data.vertices), 100.0 * _ratio))
        if abierto and _ratio >= 0.5:
            cortado = True
            break
        cortado = None          # intento fallido: el siguiente vuelve a la malla original
    if not cortado:
        cortado = False
        if len(roca.data.vertices) != _nv0:
            roca.data = _orig.copy()
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
        # (el McLaren trae su propio pedestal y bajos: no se le remete la falda)
        for v in ([] if es_mclaren else roca.data.vertices):
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
    if _mt is not None and not es_mclaren:
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
    # v1 integrador (B1): con un solo rayo en el eje el portal quedaba 4 m FUERA del ultimo indice con roca
    # y las bocas abiertas al cielo entre el arco y la roca (y entre los radios de la llanta, que es
    # concava). Prueba de SECCION: 7 rayos verticales (|u| <= 9.5, techo a <= 8.5 m) y 6 horizontales
    # (paredes a <= 11 m a 0.5/2/4.5 m) -> i_cerrado; hacia fuera, i_cara = primer indice sin ningun
    # contacto con la roca. Arco en i_cara y GALERIA artificial de piedra entre los dos en cada boca.
    _inv_r = roca.matrix_world.inverted()
    def _rayo_r(a_w, b_w):
        a_ = _inv_r @ a_w
        b_ = _inv_r @ b_w
        d_ = b_ - a_
        return d_.length > 1e-6 and roca.ray_cast(a_, d_.normalized(), distance=d_.length)[0]
    def _seccion(i):
        q = S[i % N]
        n_ok = n_hit = n_tot = 0
        for u in (-9.5, -6.0, -3.0, 0.0, 3.0, 6.0, 9.5):
            p0 = Vector((q['x'] + q['nx'] * u, q['y'] + q['ny'] * u, q['z'] + 0.3))
            h_ = _rayo_r(p0, p0 + Vector((0.0, 0.0, 8.2)))
            n_tot += 1
            n_ok += 1 if h_ else 0
            n_hit += 1 if (h_ or _rayo_r(p0, p0 + Vector((0.0, 0.0, 80.0)))) else 0
        for sg in (1.0, -1.0):
            for dz in (0.5, 2.0, 4.5):
                p0 = Vector((q['x'], q['y'], q['z'] + dz))
                h_ = _rayo_r(p0, p0 + Vector((q['nx'] * sg * 11.0, q['ny'] * sg * 11.0, 0.0)))
                n_tot += 1
                n_ok += 1 if h_ else 0
                n_hit += 1 if h_ else 0
        return n_ok == n_tot, n_hit > 0
    i_c0 = idx(s_mid)
    gal_ok = _seccion(i_c0)[0]
    bocas = []
    if gal_ok:
        for paso_i in (-1, 1):
            i_cer = i_c0
            for k in range(1, 120):
                if not _seccion(i_c0 + k * paso_i)[0]:
                    break
                i_cer = i_c0 + k * paso_i
            i_car = i_cer + paso_i
            for k in range(1, 16):            # galeria de 30 m como mucho
                i_car = i_cer + k * paso_i
                if not _seccion(i_car)[1]:
                    break
            bocas.append((i_cer, i_car))
    if len(bocas) == 2:
        (i_cer_in, i_in), (i_cer_out, i_out) = bocas
        for (i_cer, i_car, sg) in ((i_cer_in, i_in, -1), (i_cer_out, i_out, 1)):
            _galeria(min(i_cer - 2 * sg, i_car), max(i_cer - 2 * sg, i_car), 10.4, 9.4, 'TUNEL_portal_galeria')
            _portal(i_car % N, 10.5, 9.5, 'TUNEL_portal')
        log('tunel: galerias artificiales en las bocas: s %.0f-%.0f y %.0f-%.0f (seccion cerrada %.0f-%.0f)'
            % (i_in * paso, (i_cer_in + 2) * paso, (i_cer_out - 2) * paso, i_out * paso, i_cer_in * paso, i_cer_out * paso))
    else:
        i_in = _borde_roca(idx(s_mid), -1) - 2
        i_out = _borde_roca(idx(s_mid), 1) + 2
        for i_boca in (i_in, i_out):
            _portal(i_boca % N, 10.5, 9.5, 'TUNEL_portal')
    s_in, s_out = (i_in % N) * paso, (i_out % N) * paso
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
    # bien DENTRO de la galeria (asomaba por las bocas); con las galerias artificiales llega hasta los arcos
    rango = list(range(i_in + 1, i_out)) if len(bocas) == 2 else list(range(i_in + 5, i_out - 4))
    for i in rango:
        q = S[i % N]
        half = q['w'] / 2.0
        for sg in (1, -1):
            # del borde hacia la pared el suelo va PLANO a la cota del borde
            # (si siguiera el plano peraltado, el arcen asomaba por encima)
            z_b = q['z'] - q['lat'] * sg * half
            # v2 integrador (B-N1): el suelo es FISICO en AC (1ROAD_tunel_suelo): arranca a ras del borde del asfalto
            # (antes 8 cm dentro y 5 cm por encima: un escalon fisico sobre la calzada)
            for l_, z_ in ((half, z_b), (10.7, z_b + 0.14)):
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

def _abrir_pretil_puertas(info, ia, raiz):
    """v2 integrador (H2-4): las puertas con valla de las escaleras de la roca (info['puertas']: lado, ancho 4.6)
    quedaban DETRAS del pretil continuo del viaducto: verjas que no daban a ningun sitio. Para cada puerta se
    borran las caras del pretil (VIADUCTO_tramo_balaustrada_*) de su lado a |s - s_p| < ancho/2, se cierran los
    cortes con dos pilastras de piedra (VIADUCTO_pilastra, 1WALL), la verja se trae al hueco a ras del pretil
    (el borde de la pista sigue cerrado: vallas -> 1WALL) y una losa une el hueco con el rellano. -> huecos."""
    import bmesh as _bmh
    puertas = info.get('puertas') or []
    if not puertas:
        return 0
    bals = [o for o in root_col.objects if o.type == 'MESH' and o.name.startswith('VIADUCTO_tramo_balaustrada')]
    vallas = next((o for o in [raiz] + list(raiz.children_recursive) if o.type == 'MESH' and o.name.startswith('PENON_puente_vallas')), None)
    m_pil = bpy.data.materials.get('MAT_zocalo_piedra') or _mat_simple('MAT_zocalo_piedra', (0.55, 0.50, 0.40, 1), 0.95)
    n_h = 0
    for p in puertas:
        try:
            s_p = ((ia + int(p['muestra'])) * paso) % L
            lado = 1 if int(p.get('lado', -1)) > 0 else -1
            an = float(p.get('ancho', 4.6))
        except Exception:
            continue
        q = marco_interp(s_p)
        tx_, ty_ = q['ny'], -q['nx']
        def _ls(w_):
            dx_, dy_ = w_.x - q['x'], w_.y - q['y']
            return dx_ * tx_ + dy_ * ty_, dx_ * q['nx'] + dy_ * q['ny']
        lats, zs_b, pts_b = [], [], []
        n_caras = 0
        # v3 integrador (N1 de s 3967): CORTE EXACTO del pretil en los planos al = +-an/2 (bisect) antes de borrar: se
        # borraban las caras por su CENTRO y las largas que cruzaban el corte seguian 0.5-1.2 m dentro del hueco (pretil
        # hueco abierto en U a la vista desde la pista)
        for ob in bals:
            mw = ob.matrix_world
            cerca = []
            for f in ob.data.polygons:
                c_w = mw @ f.center
                if abs(c_w.z - q['z']) > 3.0:
                    continue
                al_, lt_ = _ls(c_w)
                if abs(al_) < an / 2.0 + 4.0 and lt_ * lado > 0 and abs(lt_) < q['w'] / 2.0 + 3.0:
                    cerca.append(f.index)
            if not cerca:
                continue
            bm = _bmh.new()
            bm.from_mesh(ob.data)
            bm.faces.ensure_lookup_table()
            geom = set()
            for i_f in cerca:
                f_ = bm.faces[i_f]
                geom.add(f_)
                geom.update(f_.edges)
                geom.update(f_.verts)
            imw = mw.inverted()
            n_l = (mw.to_3x3().transposed() @ Vector((tx_, ty_, 0.0))).normalized()
            for sg in (-1.0, 1.0):
                p_w = Vector((q['x'] + tx_ * sg * an / 2.0, q['y'] + ty_ * sg * an / 2.0, q['z']))
                try:
                    res_b = _bmh.ops.bisect_plane(bm, geom=[e_ for e_ in geom if e_.is_valid], dist=1e-4,
                                                  plane_co=imw @ p_w, plane_no=n_l)
                    geom = set(e_ for e_ in res_b['geom'] if e_.is_valid)
                except Exception as e:
                    log('pretil: corte exacto de %s fallo (%s): se borra por centros' % (ob.name, e))
            malas = []
            for f_ in [e_ for e_ in geom if isinstance(e_, _bmh.types.BMFace) and e_.is_valid]:
                c_w = mw @ f_.calc_center_median()
                if abs(c_w.z - q['z']) > 3.0:
                    continue
                al_, lt_ = _ls(c_w)
                if abs(al_) < an / 2.0 and lt_ * lado > 0 and abs(lt_) < q['w'] / 2.0 + 3.0:
                    malas.append(f_)
            if not malas:
                bm.free()
                continue
            if len(malas) > 900:
                log('pretil: puerta en s=%.0f: %d caras en %s, demasiadas: no se abre' % (s_p, len(malas), ob.name))
                bm.free()
                continue
            for f_ in malas:
                for v_ in f_.verts:
                    w_ = mw @ v_.co
                    a_v, l_v = _ls(w_)
                    lats.append(abs(l_v))
                    zs_b.append(w_.z)
                    pts_b.append((a_v, w_.z))
            _bmh.ops.delete(bm, geom=malas, context='FACES')
            bm.to_mesh(ob.data)
            ob.data.update()
            bm.free()
            n_caras += len(malas)
        if not n_caras:
            log('pretil: puerta en s=%.0f lado %+d sin caras de pretil delante' % (s_p, lado))
            continue
        lat_c = sum(lats) / len(lats)
        z_b0 = min(zs_b)
        # pilastras de piedra en los dos cortes; v3 (N1 de s 3967): UNA COTA POR PILASTRA (la del pretil en su corte):
        # con la cota mas baja de todo el hueco, en el paso alto del 12 % la de arriba quedaba 0.30 m sobre el tablero
        for sg in (-1.0, 1.0):
            zc_ = [z_ for (a_v, z_) in pts_b if abs(a_v - sg * an / 2.0) < 0.8]
            if zc_:
                z_bs = min(zc_)
            else:
                z_bs = z_b0 + (marco_interp(s_p + sg * (an / 2.0 + 0.25))['z'] - q['z'])
            cxp = q['x'] + tx_ * sg * (an / 2.0 + 0.25) + q['nx'] * lado * lat_c
            cyp = q['y'] + ty_ * sg * (an / 2.0 + 0.25) + q['ny'] * lado * lat_c
            vs_, fs_ = [], []
            for zz_ in (z_bs - 0.05, z_bs + 1.1):
                for (a_, b_) in ((-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25)):
                    vs_.append((cxp + tx_ * a_ + q['nx'] * b_, cyp + ty_ * a_ + q['ny'] * b_, zz_))
            fs_ = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
            me_ = bpy.data.meshes.new('VIADUCTO_pilastra')
            me_.from_pydata(vs_, [], fs_)
            me_.materials.append(m_pil)
            bq = _bmh.new()
            bq.from_mesh(me_)
            _bmh.ops.recalc_face_normals(bq, faces=bq.faces)
            bq.to_mesh(me_)
            bq.free()
            root_col.objects.link(bpy.data.objects.new('VIADUCTO_pilastra', me_))
        # la verja (con su puerta) al hueco, a ras del pretil; losa del hueco al rellano. (Las bocas de CARRETERA,
        # tipo 'carretera' de roca_lazo, llevan su calzada hasta el tablero y la valla de cierre a 6 m: solo hueco)
        z_r = float(p.get('z', z_b0))
        lat_v = None
        if p.get('tipo', 'escalera') != 'carretera' and vallas is not None and p.get('valla'):
            (v0, v1) = p['valla'][0], p['valla'][1]
            gx_, gy_ = (float(v0[0]) + float(v1[0])) / 2.0, (float(v0[1]) + float(v1[1])) / 2.0
            lat_v = (gx_ - q['x']) * q['nx'] + (gy_ - q['y']) * q['ny']
            # v3 (remate "nada encima del circuito"): la verja en el hueco, pero a >= 0.45 m del borde del asfalto
            # (a ras del pretil quedaba a 0.1-0.3 m: PENON_puente_vallas en la franja del borde, s 4548)
            d_lat = lado * max(lat_c, q['w'] / 2.0 + 0.45) - lat_v
            dz_ = max(-0.3, min(0.3, z_b0 - z_r))
            if 0.2 < abs(d_lat) < 4.0:
                n_v = 0
                for v in vallas.data.vertices:
                    w_ = vallas.matrix_world @ v.co
                    if math.hypot(w_.x - gx_, w_.y - gy_) < max(3.5, an / 2.0 + 1.0) and abs(w_.z - z_r) < 2.5:
                        v.co.x += q['nx'] * d_lat
                        v.co.y += q['ny'] * d_lat
                        v.co.z += dz_
                        n_v += 1
                vallas.data.update()
                log('pretil: verja de la puerta de s=%.0f traida %.2f m al hueco (%d vertices)' % (s_p, abs(d_lat), n_v))
        if lat_v is not None:
            l_in, l_out = max(lat_c - 0.05, q['w'] / 2.0 + 0.35), abs(lat_v) + 0.4
            if l_out > l_in + 0.3:
                vs_, fs_ = [], []
                for zz_ in (max(z_b0, z_r) + 0.02, max(z_b0, z_r) - 0.6):
                    for (a_, b_) in ((-an / 2.0, l_in), (an / 2.0, l_in), (an / 2.0, l_out), (-an / 2.0, l_out)):
                        vs_.append((q['x'] + tx_ * a_ + q['nx'] * lado * b_, q['y'] + ty_ * a_ + q['ny'] * lado * b_, zz_))
                fs_ = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
                me_ = bpy.data.meshes.new('PENON_puente_plaza_rellano')
                me_.from_pydata(vs_, [], fs_)
                me_.materials.append(_mat_simple('MAT_CAMINO_adoquin_plaza', (0.55, 0.50, 0.46, 1), 0.9))
                bq = _bmh.new()
                bq.from_mesh(me_)
                _bmh.ops.recalc_face_normals(bq, faces=bq.faces)
                bq.to_mesh(me_)
                bq.free()
                root_col.objects.link(bpy.data.objects.new('PENON_puente_plaza_rellano', me_))
        n_h += 1
        log('pretil: hueco de %.1f m en s=%.0f lado %+d (%d caras borradas, pretil a %.2f m del eje)' % (an, s_p, lado, n_caras, lat_c))
    return n_h

def zona_rocas_pueblo_lazo():
    """RONDA 15: roca NATURAL del lazo (assets/roca_lazo.py): la calzada va pegada a la
    pared de roca, terrazas con casas sin meterse en la roca, cumbre con plaza y
    campanile, cala de pescadores en el lado abierto."""
    rl = M.get('roca_lazo')
    if rl is None:
        log('roca_lazo no disponible: roca antigua (penon_pueblo)')
        return zona_rocas_pueblo()
    ia, ib = CURVAS[42]['s_idx'] - 25, CURVAS[44]['s_idx'] + 10
    def _m(i):
        q = S[i % N]
        return {k: float(q[k]) for k in ('x', 'y', 'z', 'nx', 'ny', 'w')}
    muestras = [_m(i) for i in range(ia, ib + 1)]
    contexto = ([_m(i) for i in range(ia - 45, ia)], [_m(i) for i in range(ib + 1, ib + 46)])
    z_mar = float(G.get('nivel_mar', 0.0))
    # el modulo lanza ray-casts contra lo que construye: va en la coleccion VISIBLE
    raiz, info = rl.build(root_col, muestras, z_mar, 9, casas_kit=M['casas_kit'], vegetacion_kit=M['vegetacion_kit'],
                          italiano_kit=M.get('italiano_kit'), yates_kit=M.get('yates_kit'),
                          muestras_contexto=contexto, talud_bajo_tablero_deg=80.0, log=log)
    bpy.context.view_layer.update()
    roca = next((o for o in [raiz] + list(raiz.children_recursive) if o.type == 'MESH' and o.name.startswith('PENON_puente_roca')), None)
    if roca is None:
        roca = max((o for o in raiz.children_recursive if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    PUENTE_INFO.update({'cx': info['centro_top'][0], 'cy': info['centro_top'][1], 'roca': roca, 'info': info,
                        'ia': ia, 'ib': ib})
    nb = _limpiar_bajo_roca(roca)
    try:
        n_hp = _abrir_pretil_puertas(info, ia, raiz)
        log('roca del lazo: %d huecos abiertos en el pretil del viaducto para las puertas de las escaleras' % n_hp)
    except Exception as e:
        log('roca del lazo: no se pudo abrir el pretil en las puertas: %s' % e)
    chk = info.get('checks', {}) or {}
    log('roca del lazo (roca_lazo): checks ok=%s, cumbre z=%.0f, %d casas, %d objetos retirados de debajo'
        % (chk.get('ok'), float(info.get('z_cumbre', info.get('z_top', 0.0))), len(info.get('casas', [])), nb))
safe('zona_rocas_pueblo', zona_rocas_pueblo_lazo)

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
            # v3 integrador (remate "nada encima del circuito"): el bordillo del paseo arrancaba a 0.05 m del asfalto (la
            # franja de 0.3 m del borde es del arcen y del guardarrail, a 0.10-0.27 m): ahora a 0.35 m
            return {'kb': P(0.35, -0.06), 'kt': P(0.35, 0.10), 'dt': P(ancho - 0.5, 0.10),
                    'pi': P(ancho - 0.5, 1.05), 'po': P(ancho + 0.05, 1.05), 'pb': P(ancho + 0.05, 0.10),
                    'ob': P(ancho + 0.05, -3.4), 'n': Vector((q['nx'] * side, q['ny'] * side, 0.0)),
                    'ze': ze, 's': s_m}

        def quad(pts, want, mi):
            a, b, c, d = pts
            if (b - a).cross(d - a).dot(want) < 0:
                pts = [a, d, c, b]
            base = len(vs)
            vs.extend([tuple(p) for p in pts])
            fs.append(tuple(range(base, base + len(pts))))
            fm.append(mi)

        # v1 integrador (F-04): el palazzo de la azotea-parking no tenia acceso. Donde el paseo pasa a la
        # cota de la azotea (+-0.6 m) se abre el pretil 6 m y una PASARELA de piedra cruza los 7 m de hueco
        ANCHO_P, FONDO_P = 40.0, 18.0
        s_k = (s0 + s1) / 2.0 + 12.0
        s_open, z_techo = None, None
        if mk is not None:
            qk_, tk_ = frame(s_k), tangent(s_k)
            lk_ = side * (qk_['w'] / 2.0 + ancho + 7.0 + FONDO_P / 2.0)
            pxk_, pyk_ = qk_['x'] + qk_['nx'] * lk_, qk_['y'] + qk_['ny'] * lk_
            esq_k = [z_terreno(pxk_ + tk_[0] * a_ + qk_['nx'] * side * b_, pyk_ + tk_[1] * a_ + qk_['ny'] * side * b_)
                     for a_ in (-ANCHO_P / 2, ANCHO_P / 2) for b_ in (-FONDO_P / 2, FONDO_P / 2)]
            zb_k = sum(esq_k) / 4.0 - 1.0
            alto_k = max(10.0, min(24.0, seccion(s_k)['ze'] - 2.0 - zb_k))
            try:
                z_techo = zb_k + float(mk.plazas_parking(ANCHO_P, FONDO_P, alto_k)[0][2])
            except Exception:
                z_techo = zb_k + alto_k
            mejor_o = None
            for s_t in range(int(s_k - 16), int(s_k + 17)):
                d_o = abs(seccion(s_t)['ze'] + 0.10 - z_techo)
                if mejor_o is None or d_o < mejor_o[0]:
                    mejor_o = (d_o, float(s_t))
            if mejor_o is not None and mejor_o[0] < 0.6:
                s_open = mejor_o[1]

        def abierto(A, B):
            return s_open is not None and abs(A['s'] - s_open) <= 3.01 and abs(B['s'] - s_open) <= 3.01

        n_seg = int((s1 - s0) / 2.0)
        secs = [seccion(s0 + (s1 - s0) * k / n_seg) for k in range(n_seg + 1)]
        up = Vector((0, 0, 1))
        for k in range(n_seg):
            A, B = secs[k], secs[k + 1]
            quad([A['kb'], A['kt'], B['kt'], B['kb']], -A['n'], 1)     # bordillo
            quad([A['kt'], A['dt'], B['dt'], B['kt']], up, 0)          # pavimento
            if abierto(A, B):
                quad([A['dt'], A['pb'], B['pb'], B['dt']], up, 0)      # hueco del pretil: pavimento hasta el borde
                quad([A['pb'], A['ob'], B['ob'], B['pb']], A['n'], 1)
                for (C, D) in ((A, secs[k - 1] if k > 0 else None), (B, secs[k + 2] if k + 2 <= n_seg else None)):
                    if D is not None and not abierto(C, D) and not abierto(D, C):
                        base = len(vs)          # testero del pretil cortado
                        vs.extend([tuple(C['dt']), tuple(C['pi']), tuple(C['po']), tuple(C['pb'])])
                        fs.append((base, base + 1, base + 2, base + 3))
                        fm.append(1)
                continue
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
            # v1 integrador (F-11): piezas de 6 m con un arco (antes 12 m horizontales sobre una rampa del 13 %:
            # saltos de 1.7 m entre piezas); ahora el escalon es de ~0.8 m y la coronacion sigue al paseo
            L_P = 6.0
            pieza = mk.build_muro_arcadas(LIB, largo=L_P, alto=13.0, n_arcos=1, seed=1)
            bpy.context.view_layer.update()
            ymax, zmax = -1e9, -1e9
            for ob in hierarchy(pieza):
                if ob.type == 'MESH':
                    for c in ob.bound_box:
                        w = ob.matrix_world @ Vector(c)
                        ymax = max(ymax, w.y)
                        zmax = max(zmax, w.z)
            pie_m = []
            s_c = s0 + L_P / 2
            while s_c <= s1 - L_P / 2 + 0.01:
                q = frame(s_c)
                half = q['w'] / 2.0
                z_low = min(seccion(s_c - L_P / 2)['ze'], seccion(s_c + L_P / 2)['ze'])
                l_ = side * (half + ancho + 0.05 + 0.12 - ymax)
                r = clone(pieza, (q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, z_low - 0.10 - zmax),
                          rot_facing_road(s_c, side) + math.pi)
                r.name = 'MIRADOR_muro_arcadas'
                n_muro += 1
                lp_ = side * (half + ancho + 1.7)
                pie_m.append((q['x'] + q['nx'] * lp_, q['y'] + q['ny'] * lp_, seccion(s_c)['ze'] - 10.4))
                s_c += L_P
            # el pie del muro se despeja (la hierba tapaba el arranque de los arcos en el lado alto)
            if len(pie_m) >= 2:
                tallar_cinta(pie_m, 1.6, desmonte=1.0, terraplen=None, alcance=8.0, dz=0.0)

        # --- coches-espectador y palmeras sobre el paseo ---
        n_filas = 0
        if ck is not None:
            filas_m = [ck.build_fila_aparcada(LIB, n=5, seed=20 + k) for k in range(3)]
            s_f = s0 + 24.0
            while s_f < s1 - 16.0:
                if s_open is not None and abs(s_f - s_open) < 16.0:
                    s_f += 40.0
                    continue                      # el acceso a la pasarela queda libre
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
            if s_open is not None and abs(s_p - s_open) < 5.0:
                s_p += 20.0
                continue
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
        aterriza = None
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
            # v2 integrador (F2-06): media vuelta: la fachada principal (+Y, la de los toldos) miraba al muro de
            # arcadas a 4.5-6 m, en una zanja; ahora mira al mar, sobre su plaza. Las plazas de la azotea van en
            # local y siguen al edificio; la pasarela se calcula en mundo desde el paseo
            pk = clone(pk_lib, (px_, py_, z_base), rot_facing_road(s_k, side) + math.pi)
            pk.name = 'MIRADOR_parking'
            explanar(pk, margen=2.0)       # ronda 15: en la ladera nueva quedaba enterrado 4 m por detras
            # plaza delante de la nueva fachada (40 x 8 m, a la planta baja - 0.05) con su explanada (como la del
            # ayuntamiento): el terreno ahi bajaba 2 m en un extremo y subia 2.4 m en el otro
            try:
                bpy.context.view_layer.update()
                mw_pk = pk.matrix_world
                y_f0, y_f1 = FONDO_P / 2.0 + 0.4, FONDO_P / 2.0 + 8.4
                esq_pp = [mw_pk @ Vector((a_, b_, 0.0)) for (a_, b_) in ((-ANCHO_P / 2, y_f0), (ANCHO_P / 2, y_f0), (ANCHO_P / 2, y_f1), (-ANCHO_P / 2, y_f1))]
                z_pp = z_base - 0.05
                cxp_, cyp_ = sum(p_.x for p_ in esq_pp) / 4.0, sum(p_.y for p_ in esq_pp) / 4.0
                gro_p = min(1.3, max(0.4, z_pp - min(z_terreno(p_.x, p_.y) for p_ in esq_pp) + 0.5))
                vs_pp = [(p_.x - cxp_, p_.y - cyp_, 0.0) for p_ in esq_pp] + [(p_.x - cxp_, p_.y - cyp_, -gro_p) for p_ in esq_pp]
                me_pp = bpy.data.meshes.new('CALLE_plaza_palazzo')
                me_pp.from_pydata(vs_pp, [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
                me_pp.materials.append(_mat_simple('MAT_CAMINO_adoquin_plaza', (0.55, 0.50, 0.46, 1), 0.9))
                import bmesh as _bmpz
                _bz = _bmpz.new()
                _bz.from_mesh(me_pp)
                _bmpz.ops.recalc_face_normals(_bz, faces=_bz.faces)
                _bz.to_mesh(me_pp)
                _bz.free()
                ob_pp = bpy.data.objects.new('CALLE_plaza_palazzo', me_pp)
                root_col.objects.link(ob_pp)
                ob_pp.location = (cxp_, cyp_, z_pp)
                explanar(ob_pp, margen=1.0, alcance=12.0, desmonte=1.0, terraplen=0.66)
                _garantia_losa([tuple(mw_pk @ Vector((a_, b_, 0.0)))[:2] for a_ in [-ANCHO_P / 2 + 1.0 * k_ for k_ in range(int(ANCHO_P) + 1)]
                                for b_ in [y_f0 + (y_f1 - y_f0) * j_ / 6.0 for j_ in range(7)]], z_pp)
                PLAZAS_POLY.append([(p_.x, p_.y) for p_ in esq_pp])
            except Exception as e:
                log('paseo-mirador: plaza del palazzo fallo: %s' % e)
            if bpy.data.objects.get('TERRENO') is not None:
                bpy.data.objects['TERRENO'].data.update()
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
            if s_open is not None:
                # pasarela de piedra (F-04): del borde exterior del paseo (hueco del pretil) a la azotea
                qo_, to_ = frame(s_open), tangent(s_open)
                ho_ = qo_['w'] / 2.0
                z_t = pk.matrix_world.translation.z + float(mk.plazas_parking(ANCHO_P, FONDO_P, alto_p)[0][2])
                zA_ = seccion(s_open)['ze'] + 0.10
                def Pp(ds_, off_, dz_):
                    l_p = side * (ho_ + off_)
                    zz_ = zA_ + (z_t - zA_) * (off_ - (ancho + 0.05)) / 7.55
                    return (qo_['x'] + qo_['nx'] * l_p + to_[0] * ds_, qo_['y'] + qo_['ny'] * l_p + to_[1] * ds_, zz_ + dz_)
                vs_p, fs_p = [], []
                def caja_p(ds0, ds1, of0, of1, dz0, dz1):
                    o = len(vs_p)
                    for dz_ in (dz0, dz1):
                        vs_p.extend([Pp(ds0, of0, dz_), Pp(ds1, of0, dz_), Pp(ds1, of1, dz_), Pp(ds0, of1, dz_)])
                    fs_p.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7)] +
                                [(o + k_, o + (k_ + 1) % 4, o + 4 + (k_ + 1) % 4, o + 4 + k_) for k_ in range(4)])
                caja_p(-3.0, 3.0, ancho + 0.05, ancho + 7.6, -0.6, 0.0)          # tablero
                aterriza = Pp(0.0, ancho + 7.6, 0.0)
                for ds_ in (-3.0, 2.7):
                    caja_p(ds_, ds_ + 0.3, ancho + 0.05, ancho + 7.6, 0.0, 0.95)   # pretiles
                me_p = bpy.data.meshes.new('MIRADOR_pasarela')
                me_p.from_pydata(vs_p, [], fs_p)
                me_p.materials.append(m_pie)
                import bmesh as _bmpp
                _bq = _bmpp.new()
                _bq.from_mesh(me_p)
                _bmpp.ops.recalc_face_normals(_bq, faces=_bq.faces)
                _bq.to_mesh(me_p)
                _bq.free()
                root_col.objects.link(bpy.data.objects.new('MIRADOR_pasarela', me_p))
                log('paseo-mirador: pasarela a la azotea del palazzo en s=%.0f (paseo %.1f -> azotea %.1f)' % (s_open, zA_, z_t))
            if ck is not None and s_open is not None:      # sin acceso no hay coches en la azotea
                unos = [ck.build_fila_aparcada(LIB, n=1, seed=40 + k) for k in range(8)]
                for k, (bx, by, bz, brz) in enumerate(mk.plazas_parking(ANCHO_P, FONDO_P, alto_p)):
                    if k % 7 == 5:
                        continue                     # alguna plaza libre
                    w = pk.matrix_world @ Vector((bx, by, bz + 0.02))
                    if aterriza is not None and math.hypot(w.x - aterriza[0], w.y - aterriza[1]) < 4.0:
                        continue                     # v2 (F2-06): la llegada de la pasarela queda libre
                    r = clone(unos[k % len(unos)], (w.x, w.y, w.z), pk.rotation_euler.z + brz)
                    r.name = 'MIRADOR_coche_azotea'
                    n_azotea += 1
        log('paseo-mirador s=%d..%d: %d piezas de muro de arcadas, %d filas de coches, %d palmeras, '
            '%d coches en la azotea del parking' % (s0, s1, n_muro, n_filas, n_pal, n_azotea))
safe('zona_paseo_mirador', zona_paseo_mirador)

# ============ RED DE CAMINOS (ronda 13): "mini ciudad funcional" ============
# Carreteras secundarias, calles del pueblo, paddock, muelle, senderos de montana;
# cada empalme con la pista lleva VALLA DE CIERRE (peticion del usuario) y cartel.
CAMINOS_INFO = {'caminos': 0, 'vallas': 0, 'carteles': 0, 'despejados': 0, 'tramos': [], 'ejes': []}


def _densificar(pts, paso_c=3.0, z_extra=0.28, suavizar=3, z_ini=None, z_fin=None, fundir=None):
    """[(x, y)] -> [(x, y, z)] cada paso_c m; z = terreno + z_extra (suavizado).
    Con z_ini/z_fin la cota se interpola linealmente (rampas cortas entre dos cotas).
    v1 integrador (A-10): con fundir=m (y z_ini/z_fin) la cota solo se fuerza en los primeros/ultimos m
    metros (empalme a nivel con el pit lane o con otra calzada) y en medio sigue al terreno."""
    out = []
    for k in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[k][:2], pts[k + 1][:2]
        l_ = math.hypot(x1 - x0, y1 - y0)
        n_ = max(1, int(l_ / paso_c))
        for j in range(n_):
            f = j / float(n_)
            out.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
    out.append(tuple(pts[-1][:2]))
    if z_ini is not None and z_fin is not None and not fundir:
        n_ = len(out)
        zs = [z_ini + (z_fin - z_ini) * (k / float(max(1, n_ - 1))) for k in range(n_)]
        return [(x, y, z) for (x, y), z in zip(out, zs)]
    zs = [z_terreno(x, y) + z_extra for (x, y) in out]
    for _ in range(suavizar):
        zs = [zs[0]] + [(zs[i - 1] + 2 * zs[i] + zs[i + 1]) / 4.0 for i in range(1, len(zs) - 1)] + [zs[-1]]
    zs = [max(z, z_terreno(x, y) + 0.12) for (x, y), z in zip(out, zs)]
    if fundir and z_ini is not None and z_fin is not None:
        acum = [0.0]
        for k in range(1, len(out)):
            acum.append(acum[-1] + math.hypot(out[k][0] - out[k - 1][0], out[k][1] - out[k - 1][1]))
        tot = acum[-1]
        for k in range(len(out)):
            for (s_f, z_f) in ((acum[k], z_ini), (tot - acum[k], z_fin)):
                if s_f < fundir:
                    w_ = 1.0 - s_f / fundir
                    w_ = w_ * w_ * (3 - 2 * w_)
                    zs[k] = z_f * w_ + zs[k] * (1.0 - w_)
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


def _despejar_camino(pts3, ancho, muros=True):
    """Quita arboles, casas, coches y farolas que pisaria el camino. v3 integrador (N3 de s 145): muros=False deja los
    muro+valla de la pista (el que llama los recorta por su eje: boca PORTO, antes se borraba un tramo entero de 10 m
    y quedaban 4.7 m sin barrera junto a la boca)."""
    prefijos = ('VEG_', 'OLI_', 'CASAS_', 'COCHE_', 'CALLE_', 'CARRERA_paca', 'PUEBLO_', 'CARRERA_muro', 'CARRERA_valla_pub')
    if not muros:
        prefijos = tuple(p_ for p_ in prefijos if p_ != 'CARRERA_muro')
    n_ = 0
    xs = [p[0] for p in pts3]
    ys = [p[1] for p in pts3]
    for ob in list(root_col.objects):
        try:
            if ob.parent is not None or not ob.name.startswith(prefijos) or ob.name.startswith(('CALLE_plaza', 'CASAS_zocalo')):
                continue          # (las plazas y plazoletas son DESTINO de los caminos: no se despejan)
            x, y = ob.location.x, ob.location.y
        except ReferenceError:
            continue
        if PUEBLO_INFO.get('urbanismo') and ob.name.startswith('CASAS_'):
            continue          # ronda 15: las casas del plan urbano ya estan fuera de las calles
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


def _terraplen(pts3, ancho, omitir=None):
    """Relleno de piedra (talud 1:1) desde los bordes del camino hasta el terreno: un
    camino en rampa entre dos cotas ya no flota como una losa. v2 integrador (A-r2-06/G2-07): omitir = {lado:
    indices} -> sin talud en ese lado entre dos indices seguidos del conjunto (alli va un muro de mamposteria)."""
    omitir = omitir or {}
    om_i, om_d = omitir.get(1, set()), omitir.get(-1, set())
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
            if k in (om_i if sg > 0 else om_d):
                # v3 integrador (N2 de s 3496): lado con muro de mamposteria: el vertice de abajo va BAJO el muro (antes
                # seguia en el pie del talud y el fondo salia por fuera del muro en la vaguada: faldones grises dentados)
                vs.append((xa, ya, z - 0.05))
                vs.append((xa, ya, z_terreno(xa, ya) - 0.8))
                continue
            h = max(0.0, z - 0.05 - z_terreno(xa, ya))
            d_t = h * 0.9 + 0.4
            xb, yb = xa + sg * nx_ * d_t, ya + sg * ny_ * d_t
            # v3 (N2): el pie del talud a la cota MAS BAJA del terreno entre el borde y el pie (cada 1 m) - 0.8: el fondo
            # nunca asoma sobre una vaguada que cruce por debajo
            n_t = max(1, int(math.ceil(d_t)))
            z_pie = min(z_terreno(xa + sg * nx_ * d_t * j_ / n_t, ya + sg * ny_ * d_t * j_ / n_t) for j_ in range(n_t + 1))
            vs.append((xa, ya, z - 0.05))
            vs.append((xb, yb, z_pie - 0.8))
        # 4 vertices por muestra: [der_arriba, der_abajo, izq_arriba, izq_abajo]
    for k in range(len(pts3) - 1):
        o = 4 * k
        if not (k in om_i and k + 1 in om_i):
            fs.append((o, o + 4, o + 5, o + 1))          # talud del lado +n (izquierda de la marcha del camino)
        if not (k in om_d and k + 1 in om_d):
            fs.append((o + 2, o + 3, o + 7, o + 6))      # talud del lado -n
        if not (k in om_i and k + 1 in om_i and k in om_d and k + 1 in om_d):
            fs.append((o + 1, o + 5, o + 7, o + 3))  # fondo (bajo el terreno; v3: no entre dos muros)
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


def _segmentos_muro(pts3, ancho):
    """v1 integrador (N5): tramos de muro de contencion SOLO donde hay desmonte (el terreno del lado alto
    supera la calzada en > 0.5 m), en el lado alto, con el lado suavizado (mediana de 7) y cortados donde
    cambia de lado, a menos de 4 m de otra calle/camino o sobre una plaza: antes el muro saltaba de borde a
    borde cruzando la calzada (19 % de sus vertices dentro de ella). -> [(puntos, alto)]"""
    ejes_o = list(PUEBLO_INFO.get('ejes', [])) + list(CAMINOS_INFO.get('ejes', []))
    def cerca_otro(x, y):
        for (pts_o, an_o) in ejes_o:
            for k_ in range(0, len(pts_o) - 1):
                a, b = pts_o[k_], pts_o[k_ + 1]
                if abs(a[0] - x) > 40 or abs(a[1] - y) > 40:
                    continue
                vx, vy = b[0] - a[0], b[1] - a[1]
                l2 = vx * vx + vy * vy
                f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a[0]) * vx + (y - a[1]) * vy) / l2))
                if math.hypot(x - a[0] - vx * f, y - a[1] - vy * f) < an_o / 2.0 + 4.0:
                    return True
        return any(_dentro_poly(x, y, pol) for pol in PLAZAS_POLY)
    info_p = []
    for k, (x, y, z) in enumerate(pts3):
        k2, k1 = min(k + 1, len(pts3) - 1), max(k - 1, 0)
        tx, ty = pts3[k2][0] - pts3[k1][0], pts3[k2][1] - pts3[k1][1]
        l_ = math.hypot(tx, ty) or 1.0
        nx_, ny_ = -ty / l_, tx / l_
        za = z_terreno(x + nx_ * (ancho / 2 + 0.8), y + ny_ * (ancho / 2 + 0.8))
        zb = z_terreno(x - nx_ * (ancho / 2 + 0.8), y - ny_ * (ancho / 2 + 0.8))
        info_p.append((1.0 if za > zb else -1.0, max(za, zb) - z, nx_, ny_))
    sgs = []
    for k in range(len(info_p)):
        ven = sorted(info_p[j][0] for j in range(max(0, k - 3), min(len(info_p), k + 4)))
        sgs.append(ven[len(ven) // 2])
    tramos, act, lado_act = [], [], None
    for k, (x, y, z) in enumerate(pts3):
        sg, h_, nx_, ny_ = sgs[k], info_p[k][1], info_p[k][2], info_p[k][3]
        ok = h_ > 0.5 and not cerca_otro(x, y)
        if not ok or (lado_act is not None and sg != lado_act):
            if len(act) >= 3:
                tramos.append(act)
            act, lado_act = [], None
            if not ok:
                continue
        lado_act = sg
        act.append((x + sg * nx_ * (ancho / 2 + 0.3), y + sg * ny_ * (ancho / 2 + 0.3), z - 0.05, h_))
    if len(act) >= 3:
        tramos.append(act)
    out = []
    for t_ in tramos:
        if math.hypot(t_[-1][0] - t_[0][0], t_[-1][1] - t_[0][1]) < 6.0:
            continue
        hs = sorted(p_[3] for p_ in t_)
        out.append(([p_[:3] for p_ in t_], max(0.8, min(3.0, hs[len(hs) // 2] + 0.3))))
    return out

_ROCA_SOPORTE = ('PENON_roca', 'PENON_puente_roca', 'MCOCHE_roca', 'PPUEBLO_roca')

def _muros_relleno(pts3, ancho, tipo='asfalto', h_min=1.0, pieza=4.0, seed=0):
    """v2 integrador (A-r2-06/G2-07): donde la calzada va mas de h_min por encima de su apoyo (TERRENO o la roca de
    un penon, por rayo) en un lado, MURO DE MAMPOSTERIA (caminos_kit.build_muro_contencion, sillares, CAMINO_muro
    -> 1WALL) desde 0.65 m bajo el apoyo hasta un pretil de 0.9 m sobre la calzada, por fuera del bordillo. El kit
    solo admite alto constante: piezas de <= `pieza` m con la coronacion siguiendo la rasante (los escalones del pie
    quedan enterrados). Sustituye a la cara lisa del terraplen (que ya no se dibuja en esos tramos).
    -> {lado: indices de pts3 cubiertos por muro} (para _terraplen(omitir=...))."""
    ck = M.get('caminos_kit')
    out = {1: set(), -1: set()}
    if ck is None or not hasattr(ck, 'build_muro_contencion') or len(pts3) < 2:
        return out
    off = ancho / 2.0 + {'asfalto': 0.5, 'adoquin': 1.05, 'tierra': 0.6, 'muelle': 0.6}.get(tipo, 0.5)
    rocas = []
    for o_ in root_col.objects:          # (root_col.all_objects incluiria la LIB oculta: sin malla evaluada)
        if o_.type == 'MESH' and o_.name.startswith(_ROCA_SOPORTE):
            ws_ = [o_.matrix_world @ Vector(c_) for c_ in o_.bound_box]
            rocas.append((o_, o_.matrix_world.inverted(), (min(w_.x for w_ in ws_), max(w_.x for w_ in ws_),
                                                         min(w_.y for w_ in ws_), max(w_.y for w_ in ws_))))
    def z_apoyo(x, y, z_desde):
        z_s = z_terreno(x, y)
        for (o_, inv_, (x0_, x1_, y0_, y1_)) in rocas:
            if not (x0_ <= x <= x1_ and y0_ <= y <= y1_):
                continue
            a_ = inv_ @ Vector((x, y, z_desde))
            b_ = inv_ @ Vector((x, y, z_desde - 250.0))
            d_ = b_ - a_
            try:
                hit = o_.ray_cast(a_, d_.normalized(), distance=d_.length)
            except Exception:
                continue
            if hit[0]:
                z_s = max(z_s, (o_.matrix_world @ hit[1]).z)
        return z_s
    n_m = 0
    for sg in (1, -1):
        W, mask, lejos = [], [], []
        for k, (x, y, z) in enumerate(pts3):
            k2, k1 = min(k + 1, len(pts3) - 1), max(k - 1, 0)
            tx, ty = pts3[k2][0] - pts3[k1][0], pts3[k2][1] - pts3[k1][1]
            l_ = math.hypot(tx, ty) or 1.0
            wx, wy = x - ty / l_ * sg * off, y + tx / l_ * sg * off
            zs_ = z_apoyo(wx, wy, z - 0.2)
            W.append((wx, wy, z + 0.85, zs_))
            mask.append(z - zs_ > h_min)
            # v3 integrador (remate "nada encima del circuito"): ningun muro a < 1.2 m del borde de la pista (el de la
            # calle del ayuntamiento arrancaba junto a la boca, CAMINO_muro.113 en s 1080 a 0.2 m del asfalto)
            lejos.append(_d_borde_cualquiera(wx, wy) > 1.2)
        dil = [lejos[k] and any(mask[j] for j in range(max(0, k - 1), min(len(mask), k + 2))) for k in range(len(mask))]
        grupos, act = [], []
        for k in range(len(dil)):
            if dil[k]:
                act.append(k)
            elif act:
                grupos.append(act)
                act = []
        if act:
            grupos.append(act)
        for g_ in grupos:
            lg_ = sum(math.hypot(W[g_[j]][0] - W[g_[j - 1]][0], W[g_[j]][1] - W[g_[j - 1]][1]) for j in range(1, len(g_)))
            if len(g_) < 2 or lg_ < 3.0:
                continue
            # piezas de <= pieza m (puntos del grupo, cortando donde se acumula el largo)
            piezas, act_p, acc_p = [], [g_[0]], 0.0
            for j in range(1, len(g_)):
                acc_p += math.hypot(W[g_[j]][0] - W[g_[j - 1]][0], W[g_[j]][1] - W[g_[j - 1]][1])
                act_p.append(g_[j])
                if acc_p >= pieza and j < len(g_) - 1:
                    piezas.append(act_p)
                    act_p, acc_p = [g_[j]], 0.0
            if len(act_p) >= 2:
                piezas.append(act_p)
            vs, fs, fm, mats = [], [], [], None
            for pz_ in piezas:
                alto = max(0.9, max(W[k][2] - W[k][3] for k in pz_) + 0.3)
                p3 = [(W[k][0], W[k][1], W[k][2] - alto) for k in pz_]
                try:
                    mw_ = ck.build_muro_contencion(LIB, p3, alto=alto, seed=seed + n_m, relieve=('izq' if sg > 0 else 'der'), canto=0.35)
                except Exception as e:
                    log('muro de relleno fallo: %s' % e)
                    continue
                me_ = mw_.data
                if mats is None:
                    mats = list(me_.materials)
                o = len(vs)
                vs.extend(tuple(mw_.matrix_world @ v.co) for v in me_.vertices)
                for pl in me_.polygons:
                    fs.append(tuple(o + i for i in pl.vertices))
                    fm.append(pl.material_index)
                bpy.data.objects.remove(mw_, do_unlink=True)
                if me_.users == 0:
                    bpy.data.meshes.remove(me_)
            if not fs:
                continue
            me_g = bpy.data.meshes.new('CAMINO_muro')
            me_g.from_pydata(vs, [], fs)
            for m_ in (mats or []):
                me_g.materials.append(m_)
            me_g.polygons.foreach_set('material_index', fm)
            me_g.update()
            root_col.objects.link(bpy.data.objects.new('CAMINO_muro', me_g))
            out[sg].update(g_)
            n_m += 1
    if n_m:
        log('caminos: %d muros de mamposteria con pretil donde la calzada va en relleno (> %.1f m)' % (n_m, h_min))
    return out

def _d_pit_lane(x, y):
    """v3 integrador: distancia en planta de (x, y) al borde del PIT LANE (cinta de G['pit_lane'] con su ancho
    interpolado; negativa dentro; 1e9 sin pit lane)."""
    best = 1e9
    pl_ = G.get('pit_lane') or []
    for a, b in zip(pl_[:-1], pl_[1:]):
        if abs(a['x'] - x) > 40.0 or abs(a['y'] - y) > 40.0:
            continue
        vx, vy = b['x'] - a['x'], b['y'] - a['y']
        l2 = vx * vx + vy * vy
        f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a['x']) * vx + (y - a['y']) * vy) / l2))
        w_ = a['w'] + (b['w'] - a['w']) * f
        best = min(best, math.hypot(x - a['x'] - vx * f, y - a['y'] - vy * f) - w_ / 2.0)
    return best

def _dentro_poly(px, py, poly):
    d = False
    n_ = len(poly)
    for k in range(n_):
        (x1, y1), (x2, y2) = poly[k][:2], poly[(k + 1) % n_][:2]
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / ((y2 - y1) or 1e-9):
            d = not d
    return d

def _camino(pts, ancho=5.0, tipo='asfalto', despejar=True, z_fijo=None, z_ini=None, z_fin=None, muro=False, terraplen=False,
            pts3=None, fundir=None, pretil_relleno=False, h_min_relleno=1.0, despejar_muros=True, **kw):
    """Camino secundario. pts3 (v1): polilinea 3D ya calculada (senderos con rasante de proyecto).
    v2 integrador: **kw pasa a caminos_kit.build_camino (canto, nivel_agua, lineas...: A-r2-03); con
    pretil_relleno=True (y terraplen), muro de mamposteria con pretil donde la calzada va en relleno > 1 m
    (A-r2-06/G2-07) en vez de la cara lisa del terraplen. v3 (N1 de s 1120): h_min_relleno = altura de relleno a
    partir de la cual va muro (1.0; 0.3 en la calle del ayuntamiento, a 3.3 m de la pista)."""
    explicito = pts3 is not None
    if explicito:
        pts3 = [tuple(p_) for p_ in pts3]
    elif z_fijo is not None:
        pts3 = _densificar(pts, z_ini=z_fijo, z_fin=z_fijo)
    else:
        pts3 = _densificar(pts, z_ini=z_ini, z_fin=z_fin, fundir=fundir)
    if len(pts3) < 2:
        return pts3, None
    if despejar:
        _despejar_camino(pts3, ancho, muros=despejar_muros)
    ck = M.get('caminos_kit')
    segs_m = _segmentos_muro(pts3, ancho) if (muro and ck is not None and hasattr(ck, 'build_muro_contencion')) else []
    if despejar and z_fijo is None and not explicito and (z_ini is not None or z_fin is not None or muro):
        # v1 integrador (C-09/A-06): una calzada con rasante propia ya no queda bajo la hierba: se talla su
        # lecho (solo desmonte); con muro, el corte va casi vertical detras del muro (que lo contiene)
        tallar_cinta(pts3, ancho / 2.0 + (0.3 if segs_m else 1.0), desmonte=(3.0 if segs_m else 1.0),
                     terraplen=None, alcance=10.0, dz=-0.15)
        # v3 integrador (G1/N2): garantia sobre la triangulacion real (los nodos de 4 m dejaban hierba sobre el borde)
        n_g_ = _garantia_cinta(pts3, ancho / 2.0 + {'adoquin': 0.85, 'muelle': 0.4}.get(tipo, 0.3))   # + bordillo/acera del kit
        if n_g_:
            log('caminos: garantia de la calzada (%s, %.1f m): %d nodos bajados' % (tipo, ancho, n_g_))
    omit_t = None
    if terraplen and pretil_relleno:
        omit_t = _muros_relleno(pts3, ancho, tipo=tipo, h_min=h_min_relleno, seed=CAMINOS_INFO['caminos'])
    r = None
    if ck is not None and hasattr(ck, 'build_camino'):
        try:
            ob = ck.build_camino(LIB, pts3, ancho=ancho, tipo=tipo, seed=CAMINOS_INFO['caminos'], **kw)
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
            for (t_m, alto_m) in segs_m:
                mw = ck.build_muro_contencion(LIB, t_m, alto=alto_m, seed=CAMINOS_INFO['caminos'])
                mm = clone(mw, (0.0, 0.0, 0.0), 0.0)
                mm.name = 'CAMINO_muro'
        except Exception as e:
            log('muro de contencion fallo: %s' % e)
    if terraplen:
        _terraplen(pts3, ancho, omitir=omit_t)
    CAMINOS_INFO['ejes'].append(([(p_[0], p_[1]) for p_ in pts3], float(ancho)))
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
    # v1 integrador (G2): el camino arranca 1 m FUERA del borde (detras del guardarrail) y a la cota del
    # borde - 0.03; el que llama anade un primer tramo perpendicular (_perp): la tapa del camino ya no
    # entra en la calzada (antes una losa de 6 m oblicua invadia 2.4 m el asfalto)
    d_ini = q['w'] / 2 + 1.0
    px, py = q['x'] + side * q['nx'] * d_ini, q['y'] + side * q['ny'] * d_ini
    tx, ty = q['ny'], -q['nx']
    rot_valla = math.atan2(side * q['ny'], side * q['nx']) - math.pi / 2    # +Y = hacia el camino lateral
    if con_valla:
        vx, vy = q['x'] + side * q['nx'] * (d0 + 3.2), q['y'] + side * q['ny'] * (d0 + 3.2)
        _valla_cierre(vx, vy, max(z_terreno(vx, vy), z_b - 0.4), rot_valla, texto)
    if texto:
        # v3 integrador (G1, cartel CASINO): el cartel va 6 m ANTES de la boca (se lee antes del desvio y su flecha,
        # que apunta en el sentido de la marcha, senala el ramal); antes estaba 5 m despues y apuntaba a la pista
        cx_, cy_ = q['x'] + side * q['nx'] * (d0 + 4.0) - tx * 6.0, q['y'] + side * q['ny'] * (d0 + 4.0) - ty * 6.0
        _cartel(cx_, cy_, max(z_terreno(cx_, cy_), z_b - 0.4), math.atan2(-side * q['ny'], -side * q['nx']) - math.pi / 2, texto)
    return (px, py), z_b - 0.03


def _perp(s_j, side, pb, largo=6.0):
    """Punto a `largo` m de pb hacia fuera de la pista, en perpendicular (primer tramo de una boca)."""
    q = frame(s_j)
    return (pb[0] + side * q['nx'] * largo, pb[1] + side * q['ny'] * largo)


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


# ============ v1 integrador: SENDEROS DE MONTANA con rasante de proyecto (C-06/D9/E4/C-07/E3/J9/E2/J3) ============
# Antes: zigzag de 3 rectas hacia el mirador que seguia el terreno (tramos del 43-76 %, cinta flotando y metida
# en la ladera, atravesando la casa 065), mirador y ermita en plena ladera y bancales rigidos de 30 m cuesta
# arriba. Ahora: A* en reticula (rumbos de 22.5 grados, rectos/arcos de 5 m y HORQUILLAS de radio 6.5 m) con
# rasante de proyecto <= 15 % (desmonte/terraplen <= 2.5 m, 4 m en horquillas), guiado por un campo de coste
# a la meta (Dijkstra en rejilla de 4 m); banqueta tallada en el terreno; mirador en un sitio llano y alto con
# explanada; ermita, cipreses y bancales asentados uno a uno.
import heapq as _hq

def _campo_guia(zf, proh, meta, caja, celda=4.0, pend_max=0.15, libres=()):
    x0, x1, y0, y1 = caja
    nx_, ny_ = int((x1 - x0) / celda) + 1, int((y1 - y0) / celda) + 1
    zc, bl = {}, set()
    for j in range(ny_):
        for i in range(nx_):
            x, y = x0 + i * celda, y0 + j * celda
            zc[(i, j)] = zf(x, y)
            if proh(x, y) and not any(math.hypot(x - a, y - b) < 2.5 * celda for (a, b) in libres):
                bl.add((i, j))
    gi = (int(round((meta[0] - x0) / celda)), int(round((meta[1] - y0) / celda)))
    dist = {gi: 0.0}
    pq = [(0.0, gi)]
    vec = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
    while pq:
        d, c = _hq.heappop(pq)
        if d > dist.get(c, 1e18):
            continue
        for (a, b) in vec:
            n_ = (c[0] + a, c[1] + b)
            if not (0 <= n_[0] < nx_ and 0 <= n_[1] < ny_) or n_ in bl:
                continue
            c_ = max(celda * math.hypot(a, b), abs(zc[n_] - zc[c]) / pend_max)
            if d + c_ < dist.get(n_, 1e18):
                dist[n_] = d + c_
                _hq.heappush(pq, (d + c_, n_))

    def h(x, y):
        i, j = int(round((x - x0) / celda)), int(round((y - y0) / celda))
        best = 1e18
        for (a, b) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            v = dist.get((i + a, j + b))
            if v is not None:
                best = min(best, v + (0.0 if (a, b) == (0, 0) else celda))
        return best
    return h

def _planificar_sendero(ini, h0, meta, z_meta, prohibido, pend_max=0.15, paso_p=5.0, R_h=6.5, max_exp=120000,
                        peso=2.5, tol_meta=8.0, tol_z=3.0, nh=16, celda_k=2.5, mis_max=2.5, mis_h=4.0):
    """A* con estados (celda, rumbo, cota de proyecto). Devuelve ([(x, y, z_proyecto)] densa, n_exp) o (None, n)."""
    dh = 2 * math.pi / nh
    memo_z, memo_p = {}, {}
    def zf(x, y):
        k = (int(round(x * 2)), int(round(y * 2)))
        v = memo_z.get(k)
        if v is None:
            v = memo_z[k] = z_terreno(x, y)
        return v
    def proh(x, y):
        k = (int(round(x)), int(round(y)))
        v = memo_p.get(k)
        if v is None:
            v = memo_p[k] = prohibido(x, y)
        return v
    caja = (min(ini[0], meta[0]) - 200, max(ini[0], meta[0]) + 200, min(ini[1], meta[1]) - 200, max(ini[1], meta[1]) + 200)
    guia = _campo_guia(zf, proh, meta, caja, pend_max=pend_max, libres=(ini, meta))
    z0 = zf(*ini)
    def heur(x, y, z):
        return max(guia(x, y), math.hypot(meta[0] - x, meta[1] - y) - tol_meta, (abs(z_meta - z) - tol_z) / pend_max)
    prims = {}
    def prim(hi):
        if hi in prims:
            return prims[hi]
        out = []
        a = hi * dh
        for k in (0, 1, -1, 2, -2):
            pts = [(math.cos(a + k * dh * f / 2.0) * paso_p * f, math.sin(a + k * dh * f / 2.0) * paso_p * f) for f in (0.5, 1.0)]
            out.append((pts[-1][0], pts[-1][1], (hi + k) % nh, pts, paso_p, 0.8 * abs(k), False))
        for sg in (1, -1):
            cx, cy = -math.sin(a) * R_h * sg, math.cos(a) * R_h * sg
            a_c = math.atan2(-cy, -cx)
            pts = [(cx + math.cos(a_c + sg * math.pi * j / 8.0) * R_h, cy + math.sin(a_c + sg * math.pi * j / 8.0) * R_h) for j in range(1, 9)]
            out.append((pts[-1][0], pts[-1][1], (hi + nh // 2) % nh, pts, math.pi * R_h, 16.0, True))
        prims[hi] = out
        return out
    abiertos = [(peso * heur(ini[0], ini[1], z0), 0.0, ini[0], ini[1], int(round(h0 / dh)) % nh, z0, -1, ())]
    nodos, cerrados = [], set()
    n_exp = 0
    while abiertos and n_exp < max_exp:
        f, g, x, y, hi, z, padre, sub = _hq.heappop(abiertos)
        key = (int(round(x / celda_k)), int(round(y / celda_k)), hi, int(round(z / 1.5)))
        if key in cerrados:
            continue
        cerrados.add(key)
        nodos.append((x, y, z, padre, sub))
        yo = len(nodos) - 1
        n_exp += 1
        if math.hypot(meta[0] - x, meta[1] - y) < tol_meta and abs(z - z_meta) < tol_z:
            cadena = []
            k = yo
            while k >= 0:
                x_, y_, z_, p_, sub_ = nodos[k]
                cadena.append((x_, y_, z_, sub_))
                k = p_
            cadena.reverse()
            out = [(cadena[0][0], cadena[0][1], cadena[0][2])]
            for (x_, y_, z_, sub_) in cadena[1:]:
                out.extend(sub_)
            return out, n_exp
        for (dx1, dy1, h1, pts, largo, extra, es_h) in prim(hi):
            ok = True
            zp, px, py = z, x, y
            pen = 0.0
            sub_n = []
            lim_m = mis_h if es_h else mis_max
            for (qx, qy) in pts:
                qx += x
                qy += y
                if proh(qx, qy):
                    ok = False
                    break
                zt_ = zf(qx, qy)
                ds = math.hypot(qx - px, qy - py)
                zq = max(zp - pend_max * ds, min(zp + pend_max * ds, zt_))
                m_ = abs(zt_ - zq)
                if m_ > lim_m:
                    ok = False
                    break
                pen += ds * (1.5 * m_ + 3.0 * max(0.0, abs(zq - zp) / max(ds, 1e-6) - 0.10))
                sub_n.append((qx, qy, zq))
                zp, px, py = zq, qx, qy
            if not ok:
                continue
            x1, y1 = x + dx1, y + dy1
            if (int(round(x1 / celda_k)), int(round(y1 / celda_k)), h1, int(round(zp / 1.5))) in cerrados:
                continue
            hh = heur(x1, y1, zp)
            if hh >= 1e17:
                continue
            g1 = g + largo + pen + extra
            _hq.heappush(abiertos, (g1 + peso * hh, g1, x1, y1, h1, zp, yo, tuple(sub_n)))
    return None, n_exp

SENDEROS_INFO = {'rutas': [], 'miradores': []}

def _contexto_senderos():
    """Obstaculos para senderos y miradores: huellas de casas y edificios, calles del plan, rocas (rayo)."""
    huellas = [list(h_) for h_ in PUEBLO_INFO.get('huellas', [])]
    for ob in root_col.objects:
        try:
            if ob.parent is not None or not ob.name.startswith(('AYTO_', 'CAMPANILE_', 'HOTEL_', 'CASINO_', 'PIT_boxes',
                                                               'CARRERA_tribuna', 'ITAL_ermita', 'MIRADOR_parking', 'CASAS_')):
                continue
        except ReferenceError:
            continue
        rl = _rect_local(ob)
        if rl is None:
            continue
        _inv, x0, x1, y0, y1 = rl
        mw = ob.matrix_world
        huellas.append([tuple((mw @ Vector((a_, b_, 0.0)))[:2]) for (a_, b_) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])
    hh = {}
    for k, pol in enumerate(huellas):
        cx = sum(p_[0] for p_ in pol) / len(pol)
        cy = sum(p_[1] for p_ in pol) / len(pol)
        hh.setdefault((int(cx // 40), int(cy // 40)), []).append(k)
    def d_casa(x, y):
        best = 1e9
        kx, ky = int(x // 40), int(y // 40)
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for k in hh.get((kx + a, ky + b), ()):
                    pol = huellas[k]
                    if _dentro_poly(x, y, pol):
                        return 0.0
                    for j in range(len(pol)):
                        p1, p2 = pol[j], pol[(j + 1) % len(pol)]
                        vx, vy = p2[0] - p1[0], p2[1] - p1[1]
                        l2 = vx * vx + vy * vy
                        f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - p1[0]) * vx + (y - p1[1]) * vy) / l2))
                        best = min(best, math.hypot(x - p1[0] - vx * f, y - p1[1] - vy * f))
        return best
    segs = {}
    for (pts_e, an_e) in list(PUEBLO_INFO.get('ejes', [])) + list(CAMINOS_INFO.get('ejes', [])):
        for k in range(len(pts_e) - 1):
            a, b = pts_e[k], pts_e[k + 1]
            segs.setdefault((int(a[0] // 30), int(a[1] // 30)), []).append((a, b, an_e))
    def d_calle(x, y):
        best = 1e9
        kx, ky = int(x // 30), int(y // 30)
        for a_ in (-1, 0, 1):
            for b_ in (-1, 0, 1):
                for (a, b, an_e) in segs.get((kx + a_, ky + b_), ()):
                    vx, vy = b[0] - a[0], b[1] - a[1]
                    l2 = vx * vx + vy * vy
                    f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a[0]) * vx + (y - a[1]) * vy) / l2))
                    best = min(best, math.hypot(x - a[0] - vx * f, y - a[1] - vy * f) - an_e / 2.0)
        return best
    bpy.context.view_layer.update()
    rocas = []
    for ob in root_col.objects:
        if ob.type == 'MESH' and ob.name.startswith(('MONT', 'PENON', 'TUNEL_acantilado', 'MRUEDA', 'MCOCHE', 'PPUEBLO')):
            ws = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            rocas.append((min(w.x for w in ws), max(w.x for w in ws), min(w.y for w in ws), max(w.y for w in ws)))
    dg = bpy.context.evaluated_depsgraph_get()
    def bajo_roca(x, y):
        if not any(a0 <= x <= a1 and b0 <= y <= b1 for (a0, a1, b0, b1) in rocas):
            return False
        hit, loc, nrm, i_, ob_, mt_ = bpy.context.scene.ray_cast(dg, Vector((x, y, 600.0)), Vector((0, 0, -1)), distance=900.0)
        return bool(hit and ob_ is not None and ob_.name.startswith(('MONT', 'PENON', 'TUNEL', 'MRUEDA', 'MCOCHE', 'PPUEBLO')))
    return {'d_casa': d_casa, 'd_calle': d_calle, 'bajo_roca': bajo_roca}

def _d_pista_borde(x, y, anillo=1):
    """Distancia al borde del asfalto con la rejilla de 30 m de muestras (anillo 1: exacta hasta 30 m;
    anillo 2: hasta 60 m); 1e9 si no hay pista cerca."""
    kx, ky = int(x // 30), int(y // 30)
    best = 1e9
    for ddx in range(-anillo, anillo + 1):
        for ddy in range(-anillo, anillo + 1):
            for _i in _REJ_M.get((kx + ddx, ky + ddy), ()):
                best = min(best, math.hypot(x - S[_i]['x'], y - S[_i]['y']) - S[_i]['w'] / 2.0)
    return best

def _prohibido_sendero(ctx, ini, meta, otras):
    """Celda prohibida para el sendero: mar, pista (< 10 m), casas (< 5 m), calles (< 4 m), roca encima,
    laderas > 100 % y otros senderos (< 10 m); cerca del arranque (16 m) solo mar, pista y roca."""
    oh = {}
    for pts_o in otras:
        for (px, py, _pz) in pts_o[::2]:
            oh.setdefault((int(px // 10), int(py // 10)), []).append((px, py))
    otras = []
    def cerca_otra(x, y):
        kx, ky = int(x // 10), int(y // 10)
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for (px, py) in oh.get((kx + a, ky + b), ()):
                    if math.hypot(px - x, py - y) < 10.0:
                        return True
        return False
    def f(x, y):
        if z_terreno(x, y) < 1.5:
            return True
        if _d_pista_borde(x, y) < 10.0:
            return True
        cerca_ini = math.hypot(x - ini[0], y - ini[1]) < 16.0
        if ctx['bajo_roca'](x, y):
            return True
        if cerca_ini:
            return False
        if ctx['d_casa'](x, y) < 5.0 or ctx['d_calle'](x, y) < 4.0:
            return True
        if pendiente_terreno(x, y) > 1.0:
            return True
        if math.hypot(x - meta[0], y - meta[1]) > 25.0 and cerca_otra(x, y):
            return True
        return False
    return f

def _miradores_cand(ctx, x0, y0, dx, dy, excluir, d_min=100.0, d_max=420.0, abanico=80, rp=12.0):
    """Sitios altos y LLANOS para un mirador (pendiente <= 0.3, desnivel <= 6 m en un anillo de 14 m), a >= 40 m
    de la pista y de las casas, sin roca encima y a >= 100 m de otros miradores. -> [(z, x, y)] (alto primero)."""
    c = []
    a0 = math.atan2(dy, dx)
    puntos = []
    d = d_min
    while d <= d_max:                      # muestreo cada ~6 m tambien en los anillos lejanos
        paso_a = max(math.radians(0.5), 6.0 / d)
        a = -math.radians(abanico)
        while a <= math.radians(abanico):
            puntos.append((x0 + math.cos(a0 + a) * d, y0 + math.sin(a0 + a) * d))
            a += paso_a
        d += 6.0
    for (x, y) in puntos:
        z = z_terreno(x, y)
        if z < 3.0 or pendiente_terreno(x, y) > 0.3:
            continue
        anillo = [z_terreno(x + 14.0 * math.cos(2 * math.pi * k / 16), y + 14.0 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
        if max(anillo) - min(anillo) > 6.0:
            continue
        if any(math.hypot(x - ex, y - ey) < 100.0 for (ex, ey) in excluir):
            continue
        if _d_pista_borde(x, y, 2) < 40.0 or ctx['d_casa'](x, y) < 35.0 or ctx['bajo_roca'](x, y):
            continue
        c.append((z, x, y))
    c.sort(reverse=True)
    out = []
    for cc in c:
        if all(math.hypot(cc[1] - o[1], cc[2] - o[2]) > 30.0 for o in out):
            out.append(cc)
    return out

def _z_plaza(x, y, rp):
    an = sorted(z_terreno(x + rp * math.cos(2 * math.pi * k / 16), y + rp * math.sin(2 * math.pi * k / 16)) for k in range(16))
    return an[len(an) // 2]

def _explanar_circulo(cx, cy, r, zb, alcance_t=12.0, terraplen=0.6, desmonte=1.0):
    """Explanada circular a zb (corta Y rellena): dentro de r+1 el terreno queda a zb - 0.05; fuera, desmonte
    hasta la ladera natural (como mucho 80 m) y terraplen 1:terraplen hasta alcance_t."""
    ter = bpy.data.objects.get('TERRENO')
    zmax = _zmax_alrededor(cx - r, cx + r, cy - r, cy + r, r=80.0)
    alc = min(80.0, max(alcance_t, (zmax - zb) / desmonte + 8.0))
    ext = r + 1.0 + alc
    i0 = max(0, int((cx - ext - T['x0']) / T['cell'])); i1 = min(T['nx'] - 1, int((cx + ext - T['x0']) / T['cell']) + 1)
    j0 = max(0, int((cy - ext - T['y0']) / T['cell'])); j1 = min(T['ny'] - 1, int((cy + ext - T['y0']) / T['cell']) + 1)
    n_c = 0
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            k = j * T['nx'] + i
            x = T['x0'] + i * T['cell']
            y = T['y0'] + j * T['cell']
            e = max(0.0, math.hypot(x - cx, y - cy) - (r + 1.0))
            if e > alc:
                continue
            z = T['z'][k]
            if T['mar'][k] and z < 0.5:
                continue
            if e <= 0.0:
                z_new = zb - 0.05
            else:
                z_new = min(z, zb - 0.05 + e * desmonte)
                if e <= alcance_t:
                    z_new = max(z_new, zb - 0.05 - e * terraplen)
            z_new = _proteger_pista(x, y, z, z_new)
            if abs(z_new - z) > 0.02:
                _poner_celda(ter, k, z, z_new, False)     # el mirador queda de hierba (no tajo de roca)
                n_c += 1
    if ter is not None:
        ter.data.update()
    return n_c

def _rasante_final(pts3, z_fin, g=0.15, pasadas=2):
    """Rasante de proyecto: ultimo punto a z_fin y pendiente <= g en todo el camino (pasada hacia atras),
    suavizada sin perder la condicion."""
    zs = [p_[2] for p_ in pts3]
    ds = [0.0] + [math.hypot(pts3[k][0] - pts3[k - 1][0], pts3[k][1] - pts3[k - 1][1]) for k in range(1, len(pts3))]
    def limitar():
        zs[-1] = z_fin
        for k in range(len(zs) - 2, -1, -1):
            zs[k] = max(zs[k + 1] - g * ds[k + 1], min(zs[k + 1] + g * ds[k + 1], zs[k]))
        for k in range(1, len(zs)):
            zs[k] = max(zs[k - 1] - g * ds[k], min(zs[k - 1] + g * ds[k], zs[k]))
    limitar()
    for _ in range(pasadas):
        zs[1:-1] = [(zs[k - 1] + 2 * zs[k] + zs[k + 1]) / 4.0 for k in range(1, len(zs) - 1)]
        limitar()
    return [(p_[0], p_[1], z_) for p_, z_ in zip(pts3, zs)]

def _construir_sendero(texto, pts3, meta, zb, ctx, ik, seed=0):
    """Banqueta + cinta de tierra + plaza del mirador con fuente, ERMITA en un lado llano, cipreses sueltos
    junto al tramo final, bancales de olivos por la curva de nivel y capitella en el arranque."""
    mx, my = meta
    RP = 11.0
    ANCHO = 4.0
    # v3 integrador (N4 de s 1345): el sendero arranca en la salida del plan, DENTRO de la losa del fondo de saco
    # (cinta de tierra y losa a la misma cota: z-fighting y una cuna dentada sobre la losa): se recorta su arranque
    # mientras la CINTA (eje a < ANCHO/2 + 0.8) pise la plaza y arranca en su borde + 0.3 m, en radial
    pol_ini = [pol for pol in PLAZAS_POLY if len(pol) >= 3 and min(math.hypot(a_[0] - pts3[0][0], a_[1] - pts3[0][1]) for a_ in pol) < 30.0]
    def _en_pol(x_, y_):
        for pol in pol_ini:
            if _dentro_poly(x_, y_, pol):
                return True
            for j_ in range(len(pol)):
                a_, b_ = pol[j_], pol[(j_ + 1) % len(pol)]
                vx_, vy_ = b_[0] - a_[0], b_[1] - a_[1]
                l2_ = vx_ * vx_ + vy_ * vy_
                f_ = 0.0 if l2_ < 1e-9 else max(0.0, min(1.0, ((x_ - a_[0]) * vx_ + (y_ - a_[1]) * vy_) / l2_))
                if math.hypot(x_ - a_[0] - vx_ * f_, y_ - a_[1] - vy_ * f_) < 0.8 + ANCHO / 2.0:
                    return True
        return False
    k0_ = 0
    while pol_ini and k0_ < len(pts3) - 8 and _en_pol(pts3[k0_][0], pts3[k0_][1]):
        k0_ += 1
    if k0_:
        # la cinta (con su borde de piedras, ~ANCHO/2 + 0.6) ya no pisa la plaza; el nuevo primer punto va en el BORDE
        # de la plaza (+0.3 m) en el punto mas cercano al primero que queda: el primer tramo sale en radial (los
        # extremos de la cinta quedan fuera del disco)
        x1_, y1_, z1_ = pts3[k0_]
        mejor_e = None
        for pol in pol_ini:
            for j_ in range(len(pol)):
                a_, b_ = pol[j_], pol[(j_ + 1) % len(pol)]
                vx_, vy_ = b_[0] - a_[0], b_[1] - a_[1]
                l2_ = vx_ * vx_ + vy_ * vy_
                f_ = 0.0 if l2_ < 1e-9 else max(0.0, min(1.0, ((x1_ - a_[0]) * vx_ + (y1_ - a_[1]) * vy_) / l2_))
                px_, py_ = a_[0] + vx_ * f_, a_[1] + vy_ * f_
                d_ = math.hypot(x1_ - px_, y1_ - py_)
                if mejor_e is None or d_ < mejor_e[0]:
                    mejor_e = (d_, px_, py_)
        pts3 = pts3[k0_:]
        if mejor_e is not None and mejor_e[0] > 0.6:
            ux_, uy_ = (x1_ - mejor_e[1]) / mejor_e[0], (y1_ - mejor_e[2]) / mejor_e[0]
            pts3 = [(mejor_e[1] + ux_ * 0.3, mejor_e[2] + uy_ * 0.3, z1_)] + pts3
        log('caminos: sendero %s recortado %d puntos en su arranque (la cinta pisaba la plaza de la salida)' % (texto, k0_))
    tramo = []
    for p_ in pts3:
        if math.hypot(p_[0] - mx, p_[1] - my) < RP + 0.5:
            break
        tramo.append(p_)
    if len(tramo) < 4:
        return None
    a_lleg = math.atan2(tramo[-1][1] - my, tramo[-1][0] - mx)
    tramo.append((mx + (RP - 0.8) * math.cos(a_lleg), my + (RP - 0.8) * math.sin(a_lleg), zb))
    pts3 = _rasante_final(tramo, zb + 0.02)
    _explanar_circulo(mx, my, RP + 1.0, zb)
    SENDEROS_INFO['rutas'].append(pts3)
    SENDEROS_INFO['miradores'].append((mx, my))
    # plaza empedrada del mirador (losa con canto) y fuente en el centro
    circ = [(mx + RP * math.cos(2 * math.pi * k / 24), my + RP * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    gro = max(0.4, zb - min(z_terreno(a, b) for (a, b) in circ) + 0.5)
    vs_c = [(a - mx, b - my, 0.0) for (a, b) in circ] + [(a - mx, b - my, -gro) for (a, b) in circ]
    fs_c = [tuple(range(24)), tuple(range(47, 23, -1))] + [(k, 24 + k, 24 + (k + 1) % 24, (k + 1) % 24) for k in range(24)]
    me_c = bpy.data.meshes.new('CALLE_plaza_mirador')
    me_c.from_pydata(vs_c, [], fs_c)
    me_c.materials.append(_mat_simple('MAT_CAMINO_adoquin_plaza', (0.55, 0.50, 0.46, 1), 0.9))
    ob_c = bpy.data.objects.new('CALLE_plaza_mirador', me_c)
    root_col.objects.link(ob_c)
    ob_c.location = (mx, my, zb + 0.06)
    PLAZAS_POLY.append(circ)
    rect_e = None
    if ik is not None:
        f_ = clone(ik.build_fuente(LIB, seed=1 + seed), (mx, my, zb + 0.06), 0.0)
        f_.name = 'ITAL_fuente'
        # ERMITA a 19 m del centro, en el acimut de menos desnivel (fuera de la llegada), puerta a la fuente
        mejor = None
        for k in range(12):
            a = 2 * math.pi * k / 12
            if abs((a - a_lleg + math.pi) % (2 * math.pi) - math.pi) < math.radians(55):
                continue
            ox, oy = mx + 19.0 * math.cos(a), my + 19.0 * math.sin(a)
            rot = math.atan2(-math.sin(a), -math.cos(a)) - math.pi / 2
            ca, sa = math.cos(rot), math.sin(rot)
            esq = [(ox + lx * ca - ly * sa, oy + lx * sa + ly * ca) for (lx, ly) in ((-7.4, -7.4), (7.4, -7.4), (7.4, 10.4), (-7.4, 10.4))]
            if any(z_terreno(a_, b_) < 1.5 or _d_pista_borde(a_, b_) < 15.0 or ctx['d_casa'](a_, b_) < 3.0 or ctx['bajo_roca'](a_, b_)
                   for (a_, b_) in esq):
                continue
            # el sendero no puede pasar por la huella de la ermita (+ su ancho y 2.5 m)
            pisa = False
            for p_ in pts3:
                dxp, dyp = p_[0] - ox, p_[1] - oy
                if abs(dxp) > 30.0 or abs(dyp) > 30.0 or math.hypot(p_[0] - mx, p_[1] - my) < RP + 2.0:
                    continue
                lx_, ly_ = dxp * ca + dyp * sa, -dxp * sa + dyp * ca
                if math.hypot(max(-7.4 - lx_, 0.0, lx_ - 7.4), max(-7.4 - ly_, 0.0, ly_ - 10.4)) < ANCHO / 2.0 + 2.5:
                    pisa = True
                    break
            if pisa:
                continue
            zc = [z_terreno(a_, b_) for (a_, b_) in esq]
            rel = max(zc) - min(zc)
            if rel > 9.0:
                continue
            sc_ = rel + 0.3 * max(abs(z_ - zb) for z_ in zc)
            if mejor is None or sc_ < mejor[0]:
                mejor = (sc_, ox, oy, rot, esq)
        if mejor is not None:
            _, ox, oy, rot, esq = mejor
            e_ = clone(ik.build_ermita(LIB, seed=seed % 7), (ox, oy, zb + 0.05), rot)
            e_.name = 'ITAL_ermita'
            explanar(e_, margen=2.0, desmonte=1.2, roca=False)
            z_min_e = min(z_terreno(a_, b_) for (a_, b_) in esq)
            if z_min_e < zb - 0.3:
                _zocalo_global(e_, z_min_e - 0.5)
            rect_e = esq
        else:
            log('caminos: mirador %s sin sitio llano para la ermita (solo plaza y fuente)' % texto)
    # banqueta y cinta DESPUES de las explanadas del mirador y de la ermita (no las entierra ninguna)
    # v2 integrador (E2-03/D2-09): modo 'sendero' (ramas, taludes segun la ladera, garantia sobre la malla real)
    tallar_cinta(pts3, ANCHO / 2.0 + 0.8, desmonte=1.0, terraplen=0.7, alcance=6.0, dz=-0.15, modo='sendero',
                 evitar=lambda x_, y_: ctx['d_casa'](x_, y_) < 1.5 or (rect_e is not None and _dentro_poly(x_, y_, rect_e)))
    # v2 (E2-03): canto de 1.0 m: donde el borde de la rejilla de 4 m queda mas bajo que la pisada (entre las ramas
    # o en el relleno), se ve el costado de tierra de la cinta, no un hueco bajo ella
    _camino(None, ancho=ANCHO, tipo='tierra', despejar=True, pts3=pts3, canto=1.0)
    # v3 integrador (E4): donde la pisada va > 1 m sobre su apoyo (horquillas con el ramal bajo a 9-11 m, rellenos
    # entre ramas) MURO DE PIEDRA SECA con pretil (mulattiera italiana, _muros_relleno: sillares, CAMINO_muro -> 1WALL)
    # en vez de una losa al aire con el canto de tierra de 1 m a la vista; el resto lo sigue tapando el canto
    try:
        om_ = _muros_relleno(pts3, ANCHO, tipo='tierra', seed=CAMINOS_INFO['caminos'] + 50)
        log('caminos: sendero %s: muro de piedra en %d puntos de la pisada (relleno > 1 m)' % (texto, len(om_[1]) + len(om_[-1])))
    except Exception as e:
        log('caminos: muros del sendero %s fallaron: %s' % (texto, e))
    return pts3, rect_e

def _adornos_sendero(texto, pts3, meta, rect_e, ctx, ik, seed=0):
    """Cipreses SUELTOS junto al tramo final (cada uno a la cota de su suelo), bancales de olivos por la curva
    de nivel con alto y fondo adaptados a la pendiente (solo donde caben) y capitella en el arranque."""
    if ik is None:
        return
    mx, my = meta
    n_p = len(pts3)
    def d_eje(x_, y_, k_excl=None):
        b_ = 1e9
        for k_, p_ in enumerate(pts3[::2]):
            b_ = min(b_, math.hypot(p_[0] - x_, p_[1] - y_))
        return b_
    def libre(x_, y_, m_=2.5):
        if math.hypot(x_ - mx, y_ - my) < 13.5 or z_terreno(x_, y_) < 1.5:
            return False
        if rect_e is not None and _dentro_poly(x_, y_, rect_e):
            return False
        return (d_eje(x_, y_) > m_ and ctx['d_casa'](x_, y_) > 2.0 and ctx['d_calle'](x_, y_) > 1.5
                and _d_pista_borde(x_, y_) > 6.0 and not ctx['bajo_roca'](x_, y_))
    cip = [ik.build_cipres(LIB, alto=8.5 + 1.5 * k, seed=60 + seed * 3 + k) for k in range(3)]
    acc, n_c = 0.0, 0
    for k in range(n_p - 1, 0, -1):
        acc += math.hypot(pts3[k][0] - pts3[k - 1][0], pts3[k][1] - pts3[k - 1][1])
        if acc > 60.0:
            break
        if int(acc // 7.0) != int((acc - math.hypot(pts3[k][0] - pts3[k - 1][0], pts3[k][1] - pts3[k - 1][1])) // 7.0):
            tx, ty = pts3[k][0] - pts3[k - 1][0], pts3[k][1] - pts3[k - 1][1]
            l_ = math.hypot(tx, ty) or 1.0
            for sg in (1.0, -1.0):
                cx_, cy_ = pts3[k][0] - ty / l_ * sg * 4.4, pts3[k][1] + tx / l_ * sg * 4.4
                if libre(cx_, cy_, 3.4):
                    c_ = clone(cip[n_c % 3], (cx_, cy_, z_terreno(cx_, cy_) - 0.05), rnd.uniform(0, 6.28))
                    c_.name = 'ITAL_cipres'
                    n_c += 1
    # bancales de olivos: cara vista cuesta abajo, eje X por la curva de nivel, alto segun la pendiente
    n_b = 0
    # v3 integrador (E2): cara y fondo con la triangulacion REAL (_z_tri) y la fila de atras tambien casi llana
    # (<= 0.5 m): la corona va a la MEDIANA del fondo + 0.05 (antes al punto mas alto + 0.1 con la linea de atras
    # libre: el relleno sobresalia 0.6-1.5 m de la ladera, una jardinera encima del monte). Mas sitios de prueba.
    for frac in (0.3, 0.36, 0.42, 0.48, 0.54, 0.6, 0.66, 0.72, 0.78):
        if n_b >= 3:
            break
        k = int(n_p * frac)
        p_ = pts3[k]
        tx, ty = pts3[min(k + 1, n_p - 1)][0] - pts3[max(k - 1, 0)][0], pts3[min(k + 1, n_p - 1)][1] - pts3[max(k - 1, 0)][1]
        l_ = math.hypot(tx, ty) or 1.0
        hecho = False
        for sg in (1.0, -1.0):
            for off in (11.0, 15.0, 19.0):
                bx, by = p_[0] - ty / l_ * sg * off, p_[1] + tx / l_ * sg * off
                gx = (z_terreno(bx + 3, by) - z_terreno(bx - 3, by)) / 6.0
                gy = (z_terreno(bx, by + 3) - z_terreno(bx, by - 3)) / 6.0
                gm = math.hypot(gx, gy)
                if not 0.15 <= gm <= 0.85:
                    continue
                dx_, dy_ = -gx / gm, -gy / gm                     # cuesta abajo
                rot = math.atan2(dy_, dx_) - math.pi / 2           # +Y local (cara vista) cuesta abajo
                ca, sa = math.cos(rot), math.sin(rot)
                def W(lx, ly):
                    return (bx + lx * ca - ly * sa, by + lx * sa + ly * ca)
                cara = [_z_tri(*W(lx, 0.0))[0] for lx in (-7.0, -3.5, 0.0, 3.5, 7.0)]
                fondo = [_z_tri(*W(lx, -3.5))[0] for lx in (-7.0, -5.25, -3.5, -1.75, 0.0, 1.75, 3.5, 5.25, 7.0)]
                if max(cara) - min(cara) > 0.8 or max(fondo) - min(fondo) > 0.5:
                    continue
                z_pie = min(cara) - 0.3
                alto = sorted(fondo)[len(fondo) // 2] - z_pie + 0.05
                if not 0.8 <= alto <= 3.2:
                    continue
                if not all(libre(*W(lx, ly)) for lx in (-7.0, 7.0) for ly in (0.0, -3.5)):
                    continue
                b_ = clone(ik.build_bancal(LIB, largo=14.0, alto=alto, fondo=3.5, seed=4 + n_b + seed * 5), (bx, by, z_pie), rot)
                b_.name = 'ITAL_bancal'
                n_b += 1
                hecho = True
                break
            if hecho:
                break
    # capitella votiva al arranque del sendero
    if n_p > 6:
        p_ = pts3[4]
        tx, ty = pts3[5][0] - pts3[3][0], pts3[5][1] - pts3[3][1]
        l_ = math.hypot(tx, ty) or 1.0
        for sg in (1.0, -1.0):
            px_, py_ = p_[0] - ty / l_ * sg * 3.6, p_[1] + tx / l_ * sg * 3.6
            if ctx['d_casa'](px_, py_) > 1.5 and ctx['d_calle'](px_, py_) > 1.0:
                c2 = clone(ik.build_capitella(LIB, seed=3 + seed), (px_, py_, z_terreno(px_, py_)), math.atan2(ty, tx) + (math.pi if sg > 0 else 0.0))   # mirando al sendero
                c2.name = 'ITAL_capitella'
                break
    log('caminos: sendero %s: %d cipreses sueltos, %d bancales por la curva de nivel' % (texto, n_c, n_b))

def _ramales_juntos(pts3, d_min=12.0, s_min=25.0, k_pend=0.35):
    """v3 integrador (E4): True si dos tramos del sendero separados > s_min m por el camino pasan a < d_min m en planta
    con un desnivel > k_pend * distancia (el ramal bajo de una horquilla del CIMA iba a 8.6-11 m del alto con 5 m de
    desnivel: 55 %, imposible de tallar en la rejilla de 4 m y el ramal alto quedaba 1.3-3.4 m en el aire)."""
    acc = [0.0]
    for k in range(1, len(pts3)):
        acc.append(acc[-1] + math.hypot(pts3[k][0] - pts3[k - 1][0], pts3[k][1] - pts3[k - 1][1]))
    sub = list(range(0, len(pts3), 2))
    for a_ in range(len(sub)):
        i = sub[a_]
        for b_ in range(a_ + 1, len(sub)):
            j = sub[b_]
            if acc[j] - acc[i] < s_min:
                continue
            dxy = math.hypot(pts3[j][0] - pts3[i][0], pts3[j][1] - pts3[i][1])
            if dxy < d_min and abs(pts3[j][2] - pts3[i][2]) > k_pend * max(dxy, 1.0):
                return True
    return False

def _senderos_montana():
    """CIMA (desde el pueblo alto) y ERMITA (desde el pueblo bajo): cada uno prueba las salidas del plan urbano
    cercanas (y, en ultimo caso, una boca con valla en la pista) y los miradores llanos mas altos de su abanico
    hasta encontrar una ruta con rasante <= 15 %. Si ninguna sirve, no se hace (mejor nada que una cicatriz).
    v3 integrador (E4): cada plan se prueba primero con horquillas de R 9.5 m (ramas a ~19 m) y luego con R 6.5; una
    ruta cuyas ramas vuelven a juntarse en planta con mucho desnivel (_ramales_juntos) queda de reserva y se prueba
    el siguiente mirador o salida; la reserva solo se usa si no hay ninguna limpia."""
    import time as _t
    ik = M.get('italiano_kit')
    ctx = _contexto_senderos()
    defs = [('CIMA', CURVAS[15]['s_idx'] * paso, None), ('ERMITA', 1180.0, -1.0)]
    usadas = PUEBLO_INFO.setdefault('salidas_usadas', set())
    for n_s, (texto, s_s, side) in enumerate(defs):
        t0 = _t.time()
        q = frame(s_s)
        if side is None:
            side = -(-1.0 if q['lat'] < 0 else 1.0)          # interior de la curva (como antes)
        inicios = []
        for sal in sorted(PUEBLO_INFO.get('salidas', []), key=lambda s_: math.hypot(s_['x'] - q['x'], s_['y'] - q['y'])):
            if sal.get('id') in usadas or math.hypot(sal['x'] - q['x'], sal['y'] - q['y']) > 260.0:
                continue
            inicios.append(('salida', sal, (float(sal['x']), float(sal['y'])), float(sal['dx']), float(sal['dy'])))
            if len(inicios) >= 3:
                break
        (p12, _) = pos_side(s_s, side, 12.0)
        inicios.append(('boca', None, (p12[0], p12[1]), side * q['nx'], side * q['ny']))
        def _hacer(tipo_i, sal, ini, dx, dy, pts3, mx, my, zb):
            res = _construir_sendero(texto, pts3, (mx, my), zb, ctx, ik, seed=n_s)
            if res is None:
                return False
            pts_f, rect_e = res
            try:
                _adornos_sendero(texto, pts_f, (mx, my), rect_e, ctx, ik, seed=n_s)
            except Exception as e:
                log('caminos: adornos del sendero %s fallaron: %s' % (texto, e))
            if tipo_i == 'salida':
                usadas.add(sal.get('id'))
                # v2 integrador (C2-09): el cartel iba a 3.5 m fijos a un lado de la salida, encajada entre dos
                # solares, y atravesaba la esquina de CASAS_casa.085. Se prueba a cada lado, a 3.5/2.8/2.2 m y de
                # 0 a 4 m a lo largo: el primero a > 1.6 m de cualquier casa y > 0.8 m de las calles; si no hay
                # ninguno, en el eje del sendero a 4 m de la salida, mirando a ella
                sitio_c = None
                for lado_c in (1.0, -1.0):
                    for lat_c in (3.5, 2.8, 2.2):
                        for al_c in (0.0, 1.0, 2.0, 3.0, 4.0):
                            cxs_, cys_ = ini[0] - dy * lado_c * lat_c + dx * al_c, ini[1] + dx * lado_c * lat_c + dy * al_c
                            if ctx['d_casa'](cxs_, cys_) > 1.6 and ctx['d_calle'](cxs_, cys_) > 0.8:
                                sitio_c = (cxs_, cys_, math.atan2(dy, dx) + math.pi / 2)
                                break
                        if sitio_c:
                            break
                    if sitio_c:
                        break
                if sitio_c is None:
                    sitio_c = (ini[0] + dx * 4.0, ini[1] + dy * 4.0, math.atan2(-dy, -dx) - math.pi / 2)
                _cartel(sitio_c[0], sitio_c[1], z_terreno(sitio_c[0], sitio_c[1]), sitio_c[2], texto)
            else:
                (pb, z_b) = _empalme(s_s, side, texto)
                _camino([pb, _perp(s_s, side, pb), ini], ancho=4.0, tipo='tierra', despejar=True,
                        z_ini=z_b, z_fin=pts_f[0][2], terraplen=True)
            a_c = math.atan2(pts_f[-1][1] - my, pts_f[-1][0] - mx) + 0.5
            cx_, cy_ = mx + 12.5 * math.cos(a_c), my + 12.5 * math.sin(a_c)
            _cartel(cx_, cy_, z_terreno(cx_, cy_), a_c - math.pi / 2, texto)
            largo_s = sum(math.hypot(pts_f[k + 1][0] - pts_f[k][0], pts_f[k + 1][1] - pts_f[k][1]) for k in range(len(pts_f) - 1))
            pend_s = max(abs(pts_f[k + 1][2] - pts_f[k][2]) / max(0.1, math.hypot(pts_f[k + 1][0] - pts_f[k][0], pts_f[k + 1][1] - pts_f[k][1]))
                         for k in range(len(pts_f) - 1))
            log('caminos: sendero %s: %.0f m, z %.0f -> %.0f, rasante max %.0f %%, mirador (%.0f, %.0f) [%.0f s]'
                % (texto, largo_s, pts_f[0][2], pts_f[-1][2], 100.0 * pend_s, mx, my, _t.time() - t0))
            return True

        n_plan, hecho = 0, False
        reserva = None
        for (tipo_i, sal, ini, dx, dy) in inicios:
            if n_plan >= 7 or hecho:
                break
            mirs = _miradores_cand(ctx, ini[0], ini[1], dx, dy, SENDEROS_INFO['miradores'])
            for (zm, mx, my) in mirs[:3]:
                if n_plan >= 7:
                    break
                zb = _z_plaza(mx, my, 11.0)
                proh = _prohibido_sendero(ctx, ini, (mx, my), SENDEROS_INFO['rutas'])
                n_plan += 1
                pts3 = None
                for R_h_ in (9.5, 6.5):
                    p_, n_exp = _planificar_sendero(ini, math.atan2(dy, dx), (mx, my), zb, proh, tol_meta=13.0, R_h=R_h_)
                    juntos_ = bool(p_) and _ramales_juntos(p_)
                    log('caminos: sendero %s desde %s (%.0f, %.0f) a (%.0f, %.0f, z %.0f), horquillas R %.1f: %s tras %d estados'
                        % (texto, (sal or {}).get('id', 'boca'), ini[0], ini[1], mx, my, zb, R_h_,
                           ('RUTA con ramas juntas (reserva)' if juntos_ else 'RUTA') if p_ else 'sin ruta', n_exp))
                    if not p_:
                        continue
                    if juntos_:
                        if reserva is None:
                            reserva = (tipo_i, sal, ini, dx, dy, p_, mx, my, zb)
                        continue
                    pts3 = p_
                    break
                if not pts3:
                    continue
                if _hacer(tipo_i, sal, ini, dx, dy, pts3, mx, my, zb):
                    hecho = True
                    break
        if not hecho and reserva is not None:
            log('caminos: sendero %s: solo rutas con ramas juntas, se usa la primera (muros de piedra donde vuela)' % texto)
            hecho = _hacer(*reserva)
        if not hecho:
            log('caminos: sendero %s sin ruta viable (%d intentos): no se construye' % (texto, n_plan))

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
        # v1 integrador (G2): primer tramo de 6 m en perpendicular desde 1 m fuera del borde
        # v2 integrador (G2-07): donde el espolon va en relleno > 1 m sobre el terreno (y no sobre la roca del penon),
        # muro de mamposteria con pretil en vez del talud liso de 2-21 m que se leia como una presa de hormigon
        _camino([pb, _perp(i_j * paso, side, pb), (ent[0], ent[1])], ancho=6.0, tipo='asfalto', z_ini=z_b,
                z_fin=float(ent[2]) + 0.1, terraplen=True, pretil_relleno=True)
        log('caminos: espolon del casino en s=%d (%.0f m)' % (i_j * paso, d_j))
    # RONDA 15: del pie del penon del casino (plazoleta donde acaba la bajada) a la pista, con valla
    pie_c = (CASINO_INFO.get('info') or {}).get('camino_pie')
    if pie_c and len(pie_c) >= 2:
        fx_, fy_ = float(pie_c[-1][0]), float(pie_c[-1][1])
        i_p = min(range(0, N, 2), key=lambda i: (S[i]['x'] - fx_) ** 2 + (S[i]['y'] - fy_) ** 2)
        side_p = _lado_de(fx_, fy_, i_p)
        (pb_p, z_bp) = _empalme(i_p * paso, side_p, 'CASINO')
        _camino([pb_p, _perp(i_p * paso, side_p, pb_p, 4.0)] + [(float(p_[0]), float(p_[1])) for p_ in pie_c[::-1]],
                ancho=4.0, tipo='asfalto', despejar=True, terraplen=True)
        log('caminos: camino del pie del casino a la pista en s=%d' % (i_p * paso))
    # ---------- 2) roca del lazo: muelle con pantalan + puente a la carretera de la roca desde el viaducto
    pinfo = PUENTE_INFO.get('info')
    if pinfo and pinfo.get('entrada') and not pinfo.get('cala'):   # roca_lazo (ronda 15) trae su propia cala
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
        # v1 integrador (A-10): el paddock termina en el borde EXTERIOR del pit lane (lat 17.25, antes se
        # metia 2.6 m dentro) y empalma a su cota (fundido en 8 m): sin escalon de 0.26-0.33 m
        PITL_ = G.get('pit_lane') or []
        def _zpit(p_):
            if not PITL_:
                return None
            pq_ = min(PITL_, key=lambda pp: (pp['x'] - p_[0]) ** 2 + (pp['y'] - p_[1]) ** 2)
            return pq_['z'] - 0.01 if math.hypot(pq_['x'] - p_[0], pq_['y'] - p_[1]) < 15.0 else None
        pad = [_ps(s_c - largo / 2 - 34, 17.25), _ps(s_c - largo / 2 - 18, 24.0), _ps(s_c - largo / 2 - 1, 37.0),
               _ps(s_c, 37.0), _ps(s_c + largo / 2 + 1, 37.0), _ps(s_c + largo / 2 + 18, 24.0), _ps(s_c + largo / 2 + 34, 17.25)]
        z_p0, z_p1 = _zpit(pad[0]), _zpit(pad[-1])
        # v3 integrador (remate): el paddock empalma con el borde exterior del pit lane a su cota (-0.01) y su bordillo de
        # 0.12 m quedaba 7 cm por encima del carril del pit en las dos uniones: vado (bordillo a ras) en los 9 m de cada extremo
        pad3, _ = _camino(pad, ancho=6.0, tipo='asfalto', despejar=True, z_ini=z_p0, z_fin=z_p1,
                          fundir=(8.0 if (z_p0 is not None and z_p1 is not None) else None), terraplen=True,
                          rebajes=[(0.0, 9.0), (-9.0, 0.0)])
        q0 = frame((s_c - largo / 2 - 34) % L)
        _cartel(*_ps(s_c - largo / 2 - 30, 20.5), z_terreno(*_ps(s_c - largo / 2 - 30, 20.5)), math.atan2(q0['ny'], q0['nx']), 'PADDOCK')
        # v2 integrador (I-R2-04/A-r2-09): la tribuna interior (s 4951-4997) estaba en un nicho sin ningun acceso.
        # PASEO peatonal adoquinado de 3 m desde su extremo N hasta el arranque del paddock, por fuera del pit lane
        # (>= 0.75 m de su borde exterior), rasante 4.2 -> paddock (~1 %), lecho tallado con muro donde corta la
        # ladera y PRETIL de piedra del lado del pit lane y de la pista en s 5004-5066 (el publico no sale a la
        # entrada del pit). d = distancia al borde de la pista (lado -1)
        try:
            def _pit_exterior(s_):
                q_ = frame(s_ % L)
                best_ = -1e9
                for pp in PITL_:
                    dxp, dyp = pp['x'] - q_['x'], pp['y'] - q_['y']
                    if abs(dxp * q_['ny'] - dyp * q_['nx']) > 3.5:
                        continue
                    best_ = max(best_, -(dxp * q_['nx'] + dyp * q_['ny']) + pp['w'] / 2.0 - q_['w'] / 2.0)
                return best_
            # v3 integrador (N1/N2 de s 5024-5056, remate "nada encima del circuito"): con 6 puntos de control la cuerda
            # 5046 -> 5066 cortaba la panza del pit lane (su borde exterior pasa de 8.2 a 10.5 m del borde de la pista):
            # el eje del paseo quedaba a 1.2 m del pit lane y su PRETIL (CAMINO_muro.108, 1WALL) dentro del carril en
            # s 5048-5062. Ahora un punto cada 2 m con d >= borde exterior del pit lane + 3.6 (paseo 1.5 + acera 0.8 +
            # pretil 2.6 +- 0.36 con 0.3 de holgura) y el paseo acaba en el primer punto del paddock a >= 3.6 m del pit
            # lane (antes en su arranque, ENCIMA del borde exterior del pit lane: bordillo 0.1 m sobre el carril)
            ctl = [(5000.0, 24.0), (5004.0, 16.0), (5020.0, 12.5), (5046.0, 13.0), (5066.0, 13.5), (5090.0, 12.0)]
            def _d_ctl(s_):
                for (sa_, da_), (sb_, db_) in zip(ctl[:-1], ctl[1:]):
                    if sa_ <= s_ <= sb_:
                        return da_ + (db_ - da_) * (s_ - sa_) / max(1e-6, sb_ - sa_)
                return ctl[-1][1]
            pts_t = []
            for s_k_ in range(5000, 5091, 2):
                s_t_ = L - (5200.0 - s_k_) if abs(L - 5200.0) > 1.0 else float(s_k_)
                d_t_ = max(_d_ctl(float(s_k_)), _pit_exterior(s_t_) + 3.6)
                pts_t.append(pos_side(s_t_, -1, d_t_)[0][:2])
            pts_t = _sin_pliegues(pts_t, 1.5)
            fin_t = tuple(pad3[0][:2]) if pad3 else _ps(s_c - largo / 2 - 34, 17.25)
            z_fin_t = pad3[0][2] if pad3 else z_terreno(*fin_t) + 0.1
            for p_pd in (pad3 or [])[:12]:
                if _d_pit_lane(p_pd[0], p_pd[1]) >= 3.6:
                    fin_t, z_fin_t = tuple(p_pd[:2]), p_pd[2]
                    break
            pts_t.append(fin_t)
            z_ini_t = z_terreno(*pts_t[0]) + 0.05
            pas3, _rp = _camino(pts_t, ancho=3.0, tipo='adoquin', despejar=True, muro=True, z_ini=z_ini_t, z_fin=z_fin_t)
            ck_t = M.get('caminos_kit')
            if pas3 and ck_t is not None and hasattr(ck_t, 'build_muro_contencion'):
                # pretil por tramos: fuera los puntos cuya cara (eje +- 0.36) quede a < 0.3 m del pit lane
                tramos_p, pret = [], []
                for k_, (x_, y_, z_) in enumerate(pas3):
                    i_t, _dd = _muestra_mas_cercana(x_, y_)
                    s_q = i_t * paso
                    k2_, k1_ = min(k_ + 1, len(pas3) - 1), max(k_ - 1, 0)
                    tx_, ty_ = pas3[k2_][0] - pas3[k1_][0], pas3[k2_][1] - pas3[k1_][1]
                    lt_ = math.hypot(tx_, ty_) or 1.0
                    nxl, nyl = -ty_ / lt_, tx_ / lt_          # izquierda del paseo = hacia la pista
                    pq_ = (x_ + nxl * (1.5 + 0.8 + 0.3), y_ + nyl * (1.5 + 0.8 + 0.3), z_ - 0.05)
                    if not (L - 196.0 <= s_q <= L - 134.0) or _d_pit_lane(pq_[0], pq_[1]) < 0.36 + 0.3:
                        if len(pret) >= 2:
                            tramos_p.append(pret)
                        pret = []
                        continue
                    pret.append(pq_)
                if len(pret) >= 2:
                    tramos_p.append(pret)
                for k_p, pret in enumerate(tramos_p):
                    if math.hypot(pret[-1][0] - pret[0][0], pret[-1][1] - pret[0][1]) < 3.0:
                        continue
                    mw_t = ck_t.build_muro_contencion(LIB, pret, alto=1.0, seed=77 + k_p, relieve='ambos')
                    mm_t = clone(mw_t, (0.0, 0.0, 0.0), 0.0)
                    mm_t.name = 'CAMINO_muro'
            log('caminos: paseo de la tribuna interior al paddock (%d puntos)' % (len(pas3) if pas3 else 0))
        except Exception as e:
            log('caminos: paseo de la tribuna interior fallo: %s' % e)
        # RONDA 15: la subida termina en un APARCAMIENTO delante de la fachada del hotel.
        # v1 integrador (A-07): losa a la cota del hotel (- 0.05), pegada a la fachada (de y1+0.5 a y1+13.5),
        # con explanada debajo (antes 1.2 m de canto a cota fija: enterrada 3 m por un lado, volando 2.3 por otro)
        _ho = next((o for o in root_col.objects if o.parent is None and o.name.startswith('HOTEL_root')), None)
        fin_h, z_fin_h = _ps(120, 79.0), None
        if _ho is not None:
            _rl = _rect_local(_ho)
            if _rl is not None:
                _inv, _x0, _x1, _y0, _y1 = _rl
                _mw = _ho.matrix_world
                z_l = _mw.translation.z - 0.05
                _pk = [_mw @ Vector((a_, b_, 0.0)) for (a_, b_) in ((_x0 + 2, _y1 + 0.5), (_x1 - 2, _y1 + 0.5), (_x1 - 2, _y1 + 13.5), (_x0 + 2, _y1 + 13.5))]
                _cs = sum(p_.x for p_ in _pk) / 4.0, sum(p_.y for p_ in _pk) / 4.0
                gro_h = max(1.2, z_l - min(z_terreno(p_.x, p_.y) for p_ in _pk) + 0.5)
                _vs = [(p_.x - _cs[0], p_.y - _cs[1], 0.0) for p_ in _pk] + [(p_.x - _cs[0], p_.y - _cs[1], -gro_h) for p_ in _pk]
                _me = bpy.data.meshes.new('CALLE_plaza_hotel')
                _me.from_pydata(_vs, [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
                _me.materials.append(_mat_simple('MAT_CAMINO_asfalto_parking', (0.22, 0.22, 0.23, 1), 0.9))
                _obp = bpy.data.objects.new('CALLE_plaza_hotel', _me)
                root_col.objects.link(_obp)
                _obp.location = (_cs[0], _cs[1], z_l)
                explanar(_obp, margen=1.0, alcance=20.0, desmonte=1.0, terraplen=0.66)
                PLAZAS_POLY.append([(p_.x, p_.y) for p_ in _pk])
                # v1 integrador (A-14): los coches-espectador que estaban en el cesped de la recta van AQUI,
                # aparcados en el aparcamiento del hotel (dos filas de cara a la fachada; el centro queda libre)
                ck_c = M.get('coches_kit')
                if ck_c is not None and hasattr(ck_c, 'build_fila_aparcada'):
                    for k_f, xf_ in enumerate((-12.0, 12.0)):
                        if abs(xf_) + 14.0 > (_x1 - _x0) / 2.0 - 2.0:
                            continue
                        wf_ = _mw @ Vector(((_x0 + _x1) / 2.0 + xf_, _y1 + 3.6, 0.0))
                        cf_ = clone(ck_c.build_fila_aparcada(LIB, n=6, seed=7 + k_f), (wf_.x, wf_.y, z_l + 0.02),
                                    _ho.rotation_euler.z + math.pi)
                        cf_.name = 'COCHE_fila_hotel'
                # la subida entra por el extremo de la losa mas cercano a los boxes
                ext_h = [_mw @ Vector((a_, _y1 + 7.0, 0.0)) for a_ in (_x0 + 3.0, _x1 - 3.0)]
                ref_h = Vector(_ps(s_c + 6.5, 68.0) + (0.0,))
                e_h = min(ext_h, key=lambda v_: (v_ - ref_h).length)
                fin_h, z_fin_h = (e_h.x, e_h.y), z_l
        # v1 integrador (A-06/N5): subida con UNA horquilla de radio 9 m (antes dos giros en punta de 150 y 173
        # grados, 37 m encima del paddock y ramas solapadas): salida perpendicular desde el borde exterior del
        # paddock, rama 1, horquilla en arco, rama 2 hasta la losa; ~8 %; muro solo donde hay desmonte
        tq_ = tangent((s_c + 6.5) % L)
        C_h = _ps(s_c + 6.5, 59.0)
        A_h, B_h = _ps(s_c + 6.5, 50.0), _ps(s_c + 6.5, 68.0)
        a_A = math.atan2(A_h[1] - C_h[1], A_h[0] - C_h[0])
        # el arco pasa por el lado de s decreciente (C - t * 9)
        a_m = math.atan2(-tq_[1], -tq_[0])
        d_a = (a_m - a_A + math.pi) % (2 * math.pi) - math.pi
        arco_h = [(C_h[0] + 9.0 * math.cos(a_A + 2.0 * d_a * j / 8.0), C_h[1] + 9.0 * math.sin(a_A + 2.0 * d_a * j / 8.0)) for j in range(9)]
        hotel = [_ps(s_c + 56.5, 39.5), _ps(s_c + 56.5, 44.0)] + arco_h + [fin_h]
        z_ini_h = z_terreno(*hotel[0]) + 0.28
        if pad3:
            z_ini_h = min(pad3, key=lambda p_: (p_[0] - hotel[0][0]) ** 2 + (p_[1] - hotel[0][1]) ** 2)[2]
        # v2 integrador (A-r2-06): en el lado de relleno (342 de 530 celdas de borde con > 1 m de caida, hasta 3.9 m,
        # sin ninguna barrera) muro de mamposteria con pretil de 0.9 m en vez de la cara lisa gris del terraplen
        _camino(hotel, ancho=5.0, tipo='asfalto', despejar=True, muro=True, terraplen=True, pretil_relleno=True,
                z_ini=z_ini_h, z_fin=(z_fin_h if z_fin_h is not None else z_terreno(*fin_h) + 0.2))
        _cartel(*_ps(s_c + 20, 41.0), z_terreno(*_ps(s_c + 20, 41.0)), math.atan2(q0['ny'], q0['nx']), 'HOTEL')
        log('caminos: paddock (%.0f m) y subida al hotel con una horquilla (%.0f m de rama 2)'
            % (largo + 68, math.hypot(fin_h[0] - arco_h[-1][0], fin_h[1] - arco_h[-1][1])))
    # ---------- 4) calles del pueblo: calle trasera entre filas + travesias a la pista
    sectores = [(660, 1085, -1, (25.5, 45.5, 65.5)), (1285, 1525, -1, (25.5, 45.5, 65.5)), (2515, 2735, -1, (25.5, 45.5)),
                (3195, 3445, -1, (25.5, 45.5)), (3195, 3445, 1, (25.5, 45.5)), (830, 1080, 1, (25.5, 45.5))]
    if PUEBLO_INFO.get('urbanismo'):
        sectores = []          # ronda 15: calles, travesias y muros vienen del plan urbano
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
        if PUEBLO_INFO.get('urbanismo'):
            TERR = []
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
        # RONDA 15: la boca se elige donde el camino al dique NO cruza tribunas, pantallas
        # ni edificios del puerto (en s=40 atravesaba la tribuna del lado del mar)
        _obst = [(_o.name,) + _rect_local(_o) for _o in root_col.objects
                 if _o.parent is None and _o.name.startswith(('CARRERA_tribuna', 'CARRERA_pantalla', 'CARRERA_boxes', 'PIT_', 'PUERTO_', 'HOTEL_'))
                 and math.hypot(_o.location.x - p0['x'], _o.location.y - p0['y']) < 260 and _rect_local(_o) is not None]
        def _choca(s_):
            q_ = frame(s_)
            ax_, ay_ = q_['x'] + q_['nx'] * (q_['w'] / 2 + 0.25), q_['y'] + q_['ny'] * (q_['w'] / 2 + 0.25)
            ux_, uy_ = cxp - ax_, cyp - ay_
            l2_ = math.hypot(ux_, uy_) or 1.0
            for f_ in range(0, int(l2_ - 140.0), 2):
                x_, y_ = ax_ + ux_ / l2_ * f_, ay_ + uy_ / l2_ * f_
                for (_n, _inv, _x0, _x1, _y0, _y1) in _obst:
                    l_ = _inv @ Vector((x_, y_, 0.0))
                    if _x0 - 3.5 < l_.x < _x1 + 3.5 and _y0 - 3.5 < l_.y < _y1 + 3.5:
                        return True
            return False
        s_puerto = next((s_ for s_ in (40, 30, 50, 20, 60, 70, 10, 80, 90, 120, 140, 160) if not _choca(s_)), 40)
        log('caminos: boca del puerto en s=%d' % s_puerto)
        (pb, z_b) = _empalme(s_puerto, 1, 'PORTO')
        pb2 = _perp(s_puerto, 1, pb)
        # por tierra hasta la orilla, luego escollera hasta el dique (radio 145)
        ux, uy = cxp - pb2[0], cyp - pb2[1]
        l_ = math.hypot(ux, uy) or 1.0
        ux, uy = ux / l_, uy / l_
        d_or = 0.0
        while d_or < l_ - 150 and z_terreno(pb2[0] + ux * d_or, pb2[1] + uy * d_or) > 0.6:
            d_or += 3.0
        orilla = (pb2[0] + ux * d_or, pb2[1] + uy * d_or)
        # v1 integrador (A-11/N3): UNA cota para la escollera = plataforma del morro del dique (nivel del mar
        # + 3.25); la carretera de tierra llega a esa cota (antes escalon de 0.5 m en la union) y la
        # escollera entra hasta el CENTRO del morro a0 (antes moria 1.65 m por debajo, contra su pared)
        z_esc = float(G.get('nivel_mar', 0.0)) + 3.25
        _camino([pb, pb2, orilla], ancho=5.5, tipo='asfalto', despejar=True, z_ini=z_b, z_fin=z_esc, terraplen=True,
                despejar_muros=False)
        # v2 integrador (A-r2-08): _despejar_camino quita los muros+valla con el CENTRO cerca de la boca, pero el
        # vecino (de 10 m) metia 1.75 m de su extremo en la calzada de la boca PORTO, hasta la valla CERRADO. Se
        # acorta por su eje (scale.x) dejando el canto a 0.3 m del bordillo, sin abrir un hueco nuevo. v3 (N3 de s 145):
        # _despejar_camino ya no borra los muro+valla de esta boca: se recortan TODOS aqui (el tramo que borraba entero
        # dejaba s 143-147.6 sin barrera entre la valla CERRADO y el siguiente muro)
        lim_b = 5.5 / 2.0 + 0.25 + 0.3
        pol_b = [pb, pb2, orilla]
        def _d_boca(x_, y_):
            best_ = 1e9
            for a_, b_ in zip(pol_b[:-1], pol_b[1:]):
                vx_, vy_ = b_[0] - a_[0], b_[1] - a_[1]
                l2_ = vx_ * vx_ + vy_ * vy_
                f_ = 0.0 if l2_ < 1e-9 else max(0.0, min(1.0, ((x_ - a_[0]) * vx_ + (y_ - a_[1]) * vy_) / l2_))
                best_ = min(best_, math.hypot(x_ - a_[0] - vx_ * f_, y_ - a_[1] - vy_ * f_))
            return best_
        bpy.context.view_layer.update()
        for mv_ in [o for o in root_col.objects if o.parent is None and o.name.startswith('CARRERA_muro_valla')
                    and math.hypot(o.location.x - pb[0], o.location.y - pb[1]) < 15.0]:
            mw_v = mv_.matrix_world.copy()
            xs_v = [-5.0 + 0.1 * k_ for k_ in range(101)]
            fuera = [_d_boca(*(mw_v @ Vector((x_, 0.0, 0.0)))[:2]) >= lim_b for x_ in xs_v]
            if all(fuera):
                continue
            runs, a_r = [], None
            for k_, ok_ in enumerate(fuera + [False]):
                if ok_ and a_r is None:
                    a_r = k_
                elif not ok_ and a_r is not None:
                    runs.append((xs_v[a_r], xs_v[k_ - 1]))
                    a_r = None
            xa_, xb_ = max(runs, key=lambda r_: r_[1] - r_[0]) if runs else (0.0, 0.0)
            if xb_ - xa_ < 1.0:
                for ch_ in list(mv_.children_recursive):
                    bpy.data.objects.remove(ch_, do_unlink=True)
                bpy.data.objects.remove(mv_, do_unlink=True)
                continue
            d_w = mw_v.to_3x3() @ Vector(((xa_ + xb_) / 2.0, 0.0, 0.0))
            mv_.location = mv_.location + d_w
            mv_.scale = (mv_.scale.x * (xb_ - xa_) / 10.0, mv_.scale.y, mv_.scale.z)
            log('caminos: %s acortado a %.1f m junto a la boca PORTO' % (mv_.name, xb_ - xa_))
        fin_d = (cxp - ux * 139.0, cyp - uy * 139.0)
        _dq = next((o for o in root_col.objects if o.parent is None and o.name.startswith('PUERTO_dique')), None)
        if _dq is not None and PUERTO_INFO.get('a0') is not None:
            a0_ = PUERTO_INFO['a0']
            wm_ = _dq.matrix_world @ Vector((PUERTO_INFO['R'] * math.cos(a0_), PUERTO_INFO['R'] * math.sin(a0_), 0.0))
            fin_d = (wm_.x, wm_.y)
        elif _dq is not None:
            _vs = [h.matrix_world @ h.data.vertices[i_].co for h in [_dq] + list(_dq.children_recursive) if h.type == 'MESH'
                   for i_ in range(0, len(h.data.vertices), 7)]
            if _vs:
                _vn = min(_vs, key=lambda v: (v.x - orilla[0]) ** 2 + (v.y - orilla[1]) ** 2)
                fin_d = (_vn.x, _vn.y)
        # v2 integrador (A-r2-03): la escollera era una losa de 1 m con 2.25 m de aire hasta el agua en 100 m: su
        # faldon baja ahora hasta el fondo (cota minima del terreno bajo el eje - 0.5) con la banda de linea de agua
        n_e = max(2, int(math.hypot(fin_d[0] - orilla[0], fin_d[1] - orilla[1]) / 3.0))
        z_f = min(z_terreno(orilla[0] + (fin_d[0] - orilla[0]) * k_ / n_e, orilla[1] + (fin_d[1] - orilla[1]) * k_ / n_e)
                  for k_ in range(n_e + 1))
        _camino([orilla, fin_d], ancho=5.5, tipo='muelle', despejar=False, z_fijo=z_esc,
                canto=max(1.0, z_esc - min(z_f, float(G.get('nivel_mar', 0.0))) + 0.5), nivel_agua=float(G.get('nivel_mar', 0.0)))
        log('caminos: carretera del puerto %.0f m por tierra + %.0f m de escollera' % (d_or, math.hypot(fin_d[0] - orilla[0], fin_d[1] - orilla[1])))
    except Exception as e:
        log('caminos: puerto fallo: %s' % e)
    # ---------- 6) senderos de montana (tierra) hacia miradores
    # ---------- RONDA 15: acceso a la plaza del ayuntamiento (s 1160) desde la pista, con valla
    # v1 integrador (C-09): la plaza (lado +1) tiene su losa; el acceso con valla entra donde la cota del borde
    # coincide con la de la losa, y una CALLE adoquinada la une con la red del pueblo (antes solo se llegaba
    # desde la pista, cerrada con valla: un coche del pueblo no podia ir al ayuntamiento)
    pl_ = PUEBLO_INFO.get('plaza_ayto_losa')
    if pl_ is not None:
        lado_a = pl_['lado']
        def _z_borde_s(s_):
            q_ = frame(s_)
            return q_['z'] - q_['lat'] * lado_a * q_['w'] / 2.0
        s_acc = min(range(int(pl_['s0']) + 4, int(pl_['s1']) - 3), key=lambda s_: abs(_z_borde_s(s_) - pl_['z']))
        (pb_a, z_ba) = _empalme(s_acc, lado_a, 'MUNICIPIO')
        (dest_a, _) = pos_side(s_acc, lado_a, 5.5)
        # v2 integrador (C2-12): el empedrado llega hasta 0.4 m del borde del asfalto (antes 0.98 m, con arcen y
        # hierba en medio), con el ultimo tramo perpendicular; la valla se queda donde estaba
        q_ac = frame(s_acc)
        p04 = (q_ac['x'] + lado_a * q_ac['nx'] * (q_ac['w'] / 2 + 0.4), q_ac['y'] + lado_a * q_ac['ny'] * (q_ac['w'] / 2 + 0.4))
        _camino([p04, pb_a, dest_a[:2]], ancho=5.0, tipo='adoquin', despejar=True, z_ini=z_ba, z_fin=pl_['z'])
        # calle al barrio: del extremo de calle del plan mas cercano (mismo lado, < 120 m) al costado de la losa
        q0_ = pos_side(pl_['s0'], lado_a, 6.5)[0]
        cands_e = []
        for (pts_e, an_e) in PUEBLO_INFO.get('ejes', []):
            if an_e < 3.0 or len(pts_e) < 2:
                continue
            for pe_ in (pts_e[0], pts_e[-1]):
                d_e = math.hypot(pe_[0] - q0_[0], pe_[1] - q0_[1])
                i_e, dp_e = _muestra_mas_cercana(pe_[0], pe_[1])
                # v3 integrador (N1 de s 1120): nunca desde la boca de un enlace (a 0.4-1.5 m del asfalto): la cinta de 4.5 m
                # montaba 4-5 cm sobre la calzada en s 1088; se arranca en el extremo de la calle de servicio (eje a 3.7 m)
                if d_e < 120.0 and _lado_de(pe_[0], pe_[1], i_e) == lado_a and 3.0 <= dp_e - S[i_e]['w'] / 2 < 12.0:
                    cands_e.append((d_e, pe_, i_e))
        if cands_e:
            d_e, pe_, i_e = min(cands_e)
            s_e = i_e * paso
            pts_c = [tuple(pe_[:2])] + [pos_side(s_, lado_a, 6.5)[0][:2] for s_ in range(int(s_e) + 10, int(pl_['s0']) - 2, 8)] \
                    + [pos_side(pl_['s0'] + 2.0, lado_a, 6.5)[0][:2]]
            z_e = z_terreno(pe_[0], pe_[1]) + 0.05
            largo_c = sum(math.hypot(pts_c[k + 1][0] - pts_c[k][0], pts_c[k + 1][1] - pts_c[k][1]) for k in range(len(pts_c) - 1))
            if len(pts_c) >= 3 and abs(pl_['z'] - z_e) / max(1.0, largo_c) <= 0.15:
                # v3 (N1 de s 1120): con la rasante LINEAL (11 %) la calle iba hasta 1.8 m por encima del borde de la
                # pista (que sube en curva concava) y su relleno daba a la pista una cara gris lisa de 55 m a 3.3-3.7 m
                # del borde (s 1094-1145). Ahora la calle va a la cota del borde + 0.15 (a ras de la acera) y solo se
                # separa donde lo piden sus extremos con <= 14 %; el relleno que quede (> 0.3 m) es muro de sillares
                # con pretil (_muros_relleno). Si la rasante no cabe en el 15 %, la lineal de antes.
                G_A = 0.14
                den_a = _densificar(pts_c, paso_c=3.0, z_ini=0.0, z_fin=0.0)
                acc_a = [0.0]
                for k_ in range(1, len(den_a)):
                    acc_a.append(acc_a[-1] + math.hypot(den_a[k_][0] - den_a[k_ - 1][0], den_a[k_][1] - den_a[k_ - 1][1]))
                D_a = acc_a[-1]
                zs_a = []
                for k_, (x_, y_, _z) in enumerate(den_a):
                    q_k = S[_muestra_cerca(x_, y_)]
                    zb_k = q_k['z'] - q_k['lat'] * lado_a * q_k['w'] / 2.0 + 0.15
                    lo_ = max(zb_k, z_e - G_A * acc_a[k_], pl_['z'] - G_A * (D_a - acc_a[k_]))
                    hi_ = min(z_e + G_A * acc_a[k_], pl_['z'] + G_A * (D_a - acc_a[k_]))
                    zs_a.append(lo_ if lo_ <= hi_ else (lo_ + hi_) / 2.0)
                zs_a[0], zs_a[-1] = z_e, pl_['z']
                for _ in range(2):
                    zs_a = [zs_a[0]] + [(zs_a[k_ - 1] + 2 * zs_a[k_] + zs_a[k_ + 1]) / 4.0 for k_ in range(1, len(zs_a) - 1)] + [zs_a[-1]]
                pend_a = max(abs(zs_a[k_] - zs_a[k_ - 1]) / max(0.1, acc_a[k_] - acc_a[k_ - 1]) for k_ in range(1, len(zs_a)))
                if pend_a <= 0.155:
                    pts3_a = [(x_, y_, z_) for (x_, y_, _z), z_ in zip(den_a, zs_a)]
                    tallar_cinta(pts3_a, 4.5 / 2.0 + 1.0, desmonte=1.0, terraplen=None, alcance=10.0, dz=-0.15)
                    _garantia_cinta(pts3_a, 4.5 / 2.0 + 0.85)
                    _camino(None, ancho=4.5, tipo='adoquin', despejar=True, pts3=pts3_a, terraplen=True,
                            pretil_relleno=True, h_min_relleno=0.3)
                    log('caminos: calle al ayuntamiento a la cota del borde de la pista + 0.15 (rasante max %.0f %%)' % (100.0 * pend_a))
                else:
                    _camino(pts_c, ancho=4.5, tipo='adoquin', despejar=True, z_ini=z_e, z_fin=pl_['z'], terraplen=True,
                            pretil_relleno=True, h_min_relleno=0.3)
                log('caminos: calle del barrio a la plaza del ayuntamiento (%.0f m, %.0f %%)'
                    % (largo_c, 100.0 * abs(pl_['z'] - z_e) / max(1.0, largo_c)))
            else:
                log('caminos: sin calle a la plaza del ayuntamiento (pendiente %.0f %%)' % (100.0 * abs(pl_['z'] - z_e) / max(1.0, largo_c)))
        log('caminos: acceso a la plaza del ayuntamiento en s=%d' % s_acc)
    # ---------- 6) senderos de montana hacia miradores (v1 integrador: rasante de proyecto, ver arriba)
    try:
        _senderos_montana()
    except Exception as e:
        import traceback
        traceback.print_exc()
        log('caminos: senderos fallaron: %s' % e)
    # v1 integrador (A-16): las torres de control a >= 2 m de cualquier camino (su zocalo pisaba el paddock)
    for t_ in [o for o in root_col.objects if o.parent is None and o.name.startswith('PIT_torre')]:
        rl_t = _rect_local(t_)
        if rl_t is None:
            continue
        for _it in range(6):
            mw_t = t_.matrix_world
            esq_t = [mw_t @ Vector((a_, b_, 0.0)) for a_ in (rl_t[1], 0.0, rl_t[2]) for b_ in (rl_t[3], 0.0, rl_t[4])]
            peor = 1e9
            for (pts_e, an_e) in CAMINOS_INFO['ejes']:
                for k_ in range(len(pts_e) - 1):
                    a, b = pts_e[k_], pts_e[k_ + 1]
                    if abs(a[0] - mw_t.translation.x) > 60 or abs(a[1] - mw_t.translation.y) > 60:
                        continue
                    vx, vy = b[0] - a[0], b[1] - a[1]
                    l2 = vx * vx + vy * vy
                    for e_ in esq_t:
                        f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((e_.x - a[0]) * vx + (e_.y - a[1]) * vy) / l2))
                        peor = min(peor, math.hypot(e_.x - a[0] - vx * f, e_.y - a[1] - vy * f) - an_e / 2.0)
            if peor >= 2.0:
                break
            i_t, _dt = _muestra_mas_cercana(mw_t.translation.x, mw_t.translation.y)
            q_t = S[i_t]
            sg_t = _lado_de(mw_t.translation.x, mw_t.translation.y, i_t)
            t_.location.x += sg_t * q_t['nx'] * (2.0 - peor + 0.5)
            t_.location.y += sg_t * q_t['ny'] * (2.0 - peor + 0.5)
            t_.location.z = max(z_terreno(t_.location.x, t_.location.y), 0.3)
            bpy.context.view_layer.update()
            log('caminos: torre %s apartada %.1f m de un camino' % (t_.name, 2.0 - peor + 0.5))
    log('caminos: %d tramos (%s), %d vallas de cierre, %d carteles, %d objetos despejados'
        % (CAMINOS_INFO['caminos'], ', '.join(sorted(set(t_[0] for t_ in CAMINOS_INFO['tramos']))),
           CAMINOS_INFO['vallas'], CAMINOS_INFO['carteles'], CAMINOS_INFO['despejados']))
safe('zona_caminos', zona_caminos)
safe('zona_edicolas', zona_edicolas)

# ============ RONDA 15 / v2: indices comunes de calles, edificios y plazas (zona_camaras y despeje_final) ============
EDIF_PREF = ('CASAS_', 'HOTEL_', 'AYTO_', 'CAMPANILE_', 'CIVICO_', 'CARRERA_tribuna', 'CARRERA_boxes', 'PIT_boxes',
             'PIT_torre', 'ITAL_ermita', 'MIRADOR_parking', 'CASINO_', 'PUEBLO_')
DESPEJE_ARBOL = ('VEG_', 'OLI_', 'ITAL_cipres', 'ITAL_olivo')
DESPEJE_PROP = ('CALLE_maceta', 'CALLE_farola', 'VEG_roca', 'CAMARA_tierra', 'COCHE_', 'CARRERA_paca', 'ITAL_capitella')

def _crear_d_eje(ejes):
    """d_eje(x, y, excl=()) -> (distancia al borde del eje mas cercano, punto del eje, vector del tramo); excl =
    indices de `ejes` que no cuentan (el ramal propio de un coche-camara)."""
    segs = {}
    for ie, (pts, an) in enumerate(ejes):
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            for cx_ in range(int(min(a[0], b[0]) // 20) - 1, int(max(a[0], b[0]) // 20) + 2):
                for cy_ in range(int(min(a[1], b[1]) // 20) - 1, int(max(a[1], b[1]) // 20) + 2):
                    segs.setdefault((cx_, cy_), []).append((a, b, an, ie))
    def d_eje(x, y, excl=()):
        best = (1e9, None, None)
        for (a, b, an, ie) in segs.get((int(x // 20), int(y // 20)), ()):
            if ie in excl:
                continue
            vx, vy = b[0] - a[0], b[1] - a[1]
            l2 = vx * vx + vy * vy
            f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a[0]) * vx + (y - a[1]) * vy) / l2))
            px, py = a[0] + vx * f, a[1] + vy * f
            d = math.hypot(x - px, y - py) - an / 2.0
            if d < best[0]:
                best = (d, (px, py), (vx, vy))
        return best
    return d_eje

def _crear_en_edificio():
    """(en_edificio(x, y, margen) -> nombre o None, rects): huellas de edificios (rectangulo en el marco de cada raiz)."""
    rects = []
    for ob in root_col.objects:
        if ob.parent is not None or not ob.name.startswith(EDIF_PREF):     # (LIB no esta en root_col.objects)
            continue
        rl = _rect_local(ob)
        if rl is not None:
            rects.append((ob.name, ob.matrix_world.translation.x, ob.matrix_world.translation.y) + rl)
    def en_edificio(x, y, margen):
        for (nm, ox, oy, inv, x0, x1, y0, y1) in rects:
            if abs(x - ox) > 90 or abs(y - oy) > 90:
                continue
            l_ = inv @ Vector((x, y, 0.0))
            if x0 - margen < l_.x < x1 + margen and y0 - margen < l_.y < y1 + margen:
                return nm
        return None
    return en_edificio, rects

def _crear_en_plaza():
    """en_plaza(x, y): dentro (o a < 0.5 m del borde) de una plaza, plazoleta o fondo de saco (PLAZAS_POLY)."""
    ph = {}
    for k_p, pol in enumerate(PLAZAS_POLY):
        if len(pol) < 3:
            continue
        xs_, ys_ = [p_[0] for p_ in pol], [p_[1] for p_ in pol]
        for cx_ in range(int((min(xs_) - 1) // 20), int((max(xs_) + 1) // 20) + 1):
            for cy_ in range(int((min(ys_) - 1) // 20), int((max(ys_) + 1) // 20) + 1):
                ph.setdefault((cx_, cy_), []).append(k_p)
    def en_plaza(x, y):
        for k_p in ph.get((int(x // 20), int(y // 20)), ()):
            pol = PLAZAS_POLY[k_p]
            if _dentro_poly(x, y, pol):
                return True
            for j_ in range(len(pol)):
                a_, b_ = pol[j_], pol[(j_ + 1) % len(pol)]
                vx, vy = b_[0] - a_[0], b_[1] - a_[1]
                l2 = vx * vx + vy * vy
                f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a_[0]) * vx + (y - a_[1]) * vy) / l2))
                if math.hypot(x - a_[0] - vx * f, y - a_[1] - vy * f) < 0.5:
                    return True
        return False
    return en_plaza

def _r_pieza(raiz):
    """Radio en planta de una pieza (distancia maxima del origen a las esquinas de su caja, con los hijos)."""
    r_ = 0.0
    x0, y0 = raiz.matrix_world.translation.x, raiz.matrix_world.translation.y
    for h in [raiz] + list(raiz.children_recursive):
        if h.type == 'MESH':
            for c in h.bound_box:
                w_ = h.matrix_world @ Vector(c)
                r_ = max(r_, math.hypot(w_.x - x0, w_.y - y0))
    return r_

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
    # v2 integrador (C2-07/D2-06/E2-04/E-N2/F2-04/F-N1/G-N1): 5 de las 7 peanas quedaban VACIAS: despeje_final
    # quitaba la camara (su propio ramal o una calle a < 0.5 + r, o dentro de un edificio) y dejaba la peana, el
    # ramal y la valla; 4 de las 5 peanas pisaban una calle, un camino o una casa. Ahora el sitio se valida con el
    # MISMO criterio que despeje_final (ejes de calles y caminos, que ya existen: zona_pueblo y zona_caminos van
    # antes; huellas de edificios; plazas) y con la huella de la peana; el ramal propio no cuenta en el despeje y,
    # si aun asi se quita la camara, se van con ella su peana y su ramal (nombres guardados en la raiz).
    d_eje = _crear_d_eje(list(PUEBLO_INFO.get('ejes', [])) + list(CAMINOS_INFO.get('ejes', [])))
    en_edificio, _rects = _crear_en_edificio()
    en_plaza = _crear_en_plaza()
    R_CAM = max(0.8 * min(_r_pieza(p_), 6.0) for p_ in piezas)
    UMBRAL_EJE = max(0.5 + R_CAM + 1.0, 4.4 + 1.5)          # centro de la peana a > esto del borde de cualquier calle
    MARGEN_EDIF = max(4.4 + 0.5, 0.5 + R_CAM)
    PEANA = ((-3.4, -2.6), (3.4, -2.6), (3.4, 2.8), (-3.4, 2.8))
    n_rech = {'calle': 0, 'edificio': 0, 'plaza': 0}

    def sitio_valido(x, y, ang):
        if d_eje(x, y)[0] < UMBRAL_EJE:
            n_rech['calle'] += 1
            return False
        if en_edificio(x, y, MARGEN_EDIF) is not None:
            n_rech['edificio'] += 1
            return False
        ca_, sa_ = math.cos(ang), math.sin(ang)
        for (lx_, ly_) in PEANA + ((0.0, 0.0),):
            wx_, wy_ = x + lx_ * ca_ - ly_ * sa_, y + lx_ * sa_ + ly_ * ca_
            if en_plaza(wx_, wy_):
                n_rech['plaza'] += 1
                return False
            if d_eje(wx_, wy_)[0] < 1.5:
                n_rech['calle'] += 1
                return False
        return True

    def kappa(i, d=4):
        pa, pb = S[(i - d) % N], S[(i + d) % N]
        return math.atan2(pa['ny'] * pb['nx'] - pa['nx'] * pb['ny'],
                          pa['nx'] * pb['nx'] + pa['ny'] * pb['ny']) / (2 * d * paso)

    def _ramal_camara(s_a, ok_sitio):
        """(s_r, lado, fin) del ramal de tierra de un coche-camara (boca con valla 12 m antes, mismo lado) o None.
        v2 (C2-07): en un sector de terrazas (acera alta + calle de servicio en u 1.5-6) no se saca un ramal del borde
        del asfalto cruzando la calle (valla a lo largo de la calle)."""
        lado_c = ok_sitio[3]
        s_r = s_a - 12.0
        if _en_terraza_u(s_r, lado_c) or _en_terraza_u(s_a, lado_c):
            return None
        q_r = frame(s_r)
        d_r = q_r['w'] / 2 + 1.0
        pb_r = (q_r['x'] + lado_c * q_r['nx'] * d_r, q_r['y'] + lado_c * q_r['ny'] * d_r)
        pb2_r = _perp(s_r, lado_c, pb_r)
        ux_r, uy_r = ok_sitio[0] - pb2_r[0], ok_sitio[1] - pb2_r[1]
        l_r = math.hypot(ux_r, uy_r)
        z_br = q_r['z'] - q_r['lat'] * lado_c * q_r['w'] / 2
        if l_r <= 4.5:
            return None
        fin_r = (ok_sitio[0] - ux_r / l_r * 3.6, ok_sitio[1] - uy_r / l_r * 3.6)
        largo_r = 6.0 + max(0.1, l_r - 3.6)
        libre_r = all(not any(math.hypot(pb2_r[0] + ux_r * f_ - ox, pb2_r[1] + uy_r * f_ - oy) < r_ * 0.5 for (ox, oy, r_) in obst)
                      for f_ in (0.0, 0.33, 0.66, 1.0))
        # el ramal no puede cruzar calles ni edificios (lo veria despeje_final como un eje mas)
        libre_r = libre_r and all(d_eje(pb2_r[0] + ux_r * f_, pb2_r[1] + uy_r * f_)[0] > 1.0
                                  and en_edificio(pb2_r[0] + ux_r * f_, pb2_r[1] + uy_r * f_, 2.0) is None
                                  for f_ in (0.0, 0.25, 0.5, 0.75, 1.0))
        if libre_r and abs(ok_sitio[2] - z_br) / largo_r <= 0.15:
            return (s_r, lado_c, fin_r)
        return None

    def poner(s_a, ok_sitio, i_pz, ramal):
        """Crea ramal (furgoneta), peana y camara; guarda en la raiz los nombres de peana y ramal."""
        antes = set(o.name for o in root_col.objects)
        ie_ramal = -1
        if ramal is not None:
            (pb_c, z_bc) = _empalme(ramal[0], ramal[1], None, con_valla=True)
            _camino([pb_c, _perp(ramal[0], ramal[1], pb_c), ramal[2]], ancho=3.5, tipo='tierra', despejar=True,
                    z_ini=z_bc, z_fin=ok_sitio[2] + 0.05, terraplen=True)
            ie_ramal = len(CAMINOS_INFO['ejes']) - 1
        nombres_ramal = sorted(set(o.name for o in root_col.objects) - antes) if ramal is not None else []
        # peana de piedra: la cara del personaje queda por encima de la barrera (origen en su centro)
        H_PEANA = 0.7
        m_pe = _mat_simple('MAT_CAMARA_peana_piedra', (0.34, 0.33, 0.31, 1), 0.95)
        ang_p = rot_facing_road(s_a, ok_sitio[3])
        ca_, sa_ = math.cos(ang_p), math.sin(ang_p)
        vs_p, fs_p = [], []
        for (lx_, ly_) in PEANA:
            vs_p.append((lx_ * ca_ - ly_ * sa_, lx_ * sa_ + ly_ * ca_, -0.6 - H_PEANA))
            vs_p.append((lx_ * ca_ - ly_ * sa_, lx_ * sa_ + ly_ * ca_, 0.0))
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
        peana = bpy.data.objects.new('CAMARA_peana', me_p)
        root_col.objects.link(peana)
        peana.location = (ok_sitio[0], ok_sitio[1], ok_sitio[2] + H_PEANA)
        # ningun arbol plantado en la peana (su tronco dentro de la huella + 1 m)
        for o_ in [o for o in root_col.objects if o.parent is None and o.name.startswith(('VEG_', 'OLI_', 'ITAL_cipres', 'ITAL_olivo'))
                   and abs(o.location.x - ok_sitio[0]) < 6.0 and abs(o.location.y - ok_sitio[1]) < 6.0]:
            dxo, dyo = o_.location.x - ok_sitio[0], o_.location.y - ok_sitio[1]
            lxo, lyo = dxo * ca_ + dyo * sa_, -dxo * sa_ + dyo * ca_
            if abs(lxo) < 3.4 + 1.0 and -2.6 - 1.0 < lyo < 2.8 + 1.0:
                for ch in list(o_.children_recursive):
                    bpy.data.objects.remove(ch, do_unlink=True)
                bpy.data.objects.remove(o_, do_unlink=True)
        r = clone(piezas[i_pz], (ok_sitio[0], ok_sitio[1], ok_sitio[2] + H_PEANA - 0.02), ang_p)
        r.name = 'CAMARA_tierra'
        r['peana'] = peana.name
        r['ramal'] = '|'.join(nombres_ramal)
        r['eje_ramal'] = ie_ramal
        return r

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
        if any(min(abs(s_a - sp), L - abs(s_a - sp)) < 120 for sp in puestos):
            continue
        ok_sitio = None
        sitios_c = ((outside, 8.5), (outside, 11.0), (outside, 14.0), (outside, 18.0), (-outside, 9.0), (-outside, 12.5))
        # v1 integrador (N1 de E): en las curvas de tierra o al final de una bajada, la escapatoria exterior es
        # donde llegan los que se pasan de frenada: primero el INTERIOR y, por fuera, a 22 m o mas
        if q['sec'] == 'dirt' or pendiente(s_a - 40) < -0.08:
            sitios_c = ((-outside, 9.0), (-outside, 12.5), (outside, 22.0), (outside, 26.0))
        for (lado_c, off) in sitios_c:
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
            if not sitio_valido(pp[0], pp[1], rot_facing_road(s_a, lado_c)):
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
        i_pz = len(puestos) % len(piezas)
        ramal = None
        if i_pz in (0, 1, 3, 4):
            # v1 integrador (E9): una FURGONETA tiene que haber llegado por algun sitio: ramal de tierra desde
            # una boca con valla 12 m antes del vertice, mismo lado. v3 integrador (N1 de s 2502): la GRUA tambien es
            # un camion (CAMARA_tierra.001 en mitad del prado de s 2502 sin camino): tambien lleva ramal y, si no cabe
            # (casas, calles, terrazas o > 15 %), va una TORRE fija sobre su peana (antes una grua sin acceso)
            ramal = _ramal_camara(s_a, ok_sitio)
            if ramal is None:
                i_pz = 2
        poner(s_a, ok_sitio, i_pz, ramal)
        puestos.append(s_a)
    # v2 integrador (G2-08): grua FIJA de la rotonda Loews (la peticion: ver desde ahi la bajada recta). Puestos
    # medidos por el revisor: cresta s 3440 lado -1 a 10 m (bajada 100 %, Loews 94 %, cresta 100 %) o s 3500 lado +1;
    # se exige >= 80 % de s 3440-3600 visible (rayos) y el mismo criterio de sitio que el resto
    try:
        dg_c = bpy.context.evaluated_depsgraph_get()
        hecho_g = False
        ya_g = [sp for sp in puestos if 3420.0 <= sp <= 3520.0]
        if ya_g:
            log('camaras: ya hay un coche-camara en la cresta/bajada de la rotonda (s=%.0f): sin grua extra' % ya_g[0])
            hecho_g = True
        for (s_g, lado_g, off_g) in ((3440.0, -1, 10.0), (3500.0, 1, 10.0), (3440.0, -1, 14.0), (3500.0, 1, 14.0)):
            if hecho_g:
                break
            if s_g > L or any(min(abs(s_g - sp), L - abs(s_g - sp)) < 60 for sp in puestos):
                continue
            (pg, qg) = pos_side(s_g, lado_g, off_g)
            if not sitio_valido(pg[0], pg[1], rot_facing_road(s_g, lado_g)):
                continue
            if any(math.hypot(pg[0] - ox, pg[1] - oy) < r_ for (ox, oy, r_) in obst):
                continue
            zs_g = [z_terreno(pg[0] + dx, pg[1] + dy) for dx in (-3, 3) for dy in (-3, 3)]
            if max(zs_g) - min(zs_g) > 1.5:
                continue
            ojo = Vector((pg[0], pg[1], min(zs_g) + 0.7 + 8.5))
            vis = tot = 0
            s_v = 3440.0
            while s_v <= 3600.0:
                qv = frame(s_v)
                obj_v = Vector((qv['x'], qv['y'], qv['z'] + 1.0))
                dv = obj_v - ojo
                hit_v = bpy.context.scene.ray_cast(dg_c, ojo, dv.normalized(), distance=dv.length)
                tot += 1
                if (not hit_v[0]) or (hit_v[1] - obj_v).length < 3.0 or (hit_v[4] is not None and hit_v[4].name.startswith(('PISTA', 'PIANOS', 'MARCA'))):
                    vis += 1
                s_v += 10.0
            log('camaras: grua de la rotonda en s=%.0f lado %+d: %d/%d de la bajada visibles' % (s_g, lado_g, vis, tot))
            if tot and vis >= 0.8 * tot:
                # v3 (N1 de s 2502): la grua es un camion: con ramal si cabe; si no, torre fija
                sit_g = (pg[0], pg[1], min(zs_g), lado_g)
                ram_g = _ramal_camara(s_g, sit_g)
                poner(s_g, sit_g, 4 if ram_g is not None else 2, ram_g)
                puestos.append(s_g)
                hecho_g = True
                break
        if not hecho_g:
            log('camaras: AVISO sin sitio valido para la grua de la rotonda Loews')
    except Exception as e:
        log('camaras: grua de la rotonda fallo: %s' % e)
    log('camaras: sitios rechazados por calle %d, edificio %d, plaza %d (umbral %.1f m del eje, r camara %.1f m)'
        % (n_rech['calle'], n_rech['edificio'], n_rech['plaza'], UMBRAL_EJE, R_CAM))
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

def pacas_tierra():
    """Pacas de paja en el exterior de las curvas de tierra. v2 integrador (E2-06): todas se llaman CARRERA_paca_tierra
    (exportar_ac -> 1WALL_: antes el coche las atravesaba) y, donde el terraplen cae, FILA CONTINUA de pacas a 2.5 m
    del borde (como en la curva 26). v3 integrador (E6): sale de zona_tierra y va DESPUES de senderos, edicolas y
    camaras (la banqueta del sendero CIMA rebajaba la ladera de s 1706-1734 lado +1 hasta 2.4-3.0 m a 10 m y 12-16 m a
    40 m cuando las filas ya estaban decididas), mide con la triangulacion REAL (_z_tri) y salta si a 10 m cae > 2.5,
    a 15 m > 3.5 o a 25 m > 6.0; las bocas de las calles del plan Y de los caminos (ramales, senderos) quedan libres."""
    ocupado = []           # (lado, s0, s1) con fila continua
    segs_u = {}            # calles/enlaces del plan y caminos ya construidos: sus bocas quedan libres (8 m)
    for (pts_u, an_u) in list(PUEBLO_INFO.get('ejes', [])) + list(CAMINOS_INFO.get('ejes', [])):
        for a_u, b_u in zip(pts_u[:-1], pts_u[1:]):
            for cx_ in range(int(min(a_u[0], b_u[0]) // 20), int(max(a_u[0], b_u[0]) // 20) + 1):
                for cy_ in range(int(min(a_u[1], b_u[1]) // 20), int(max(a_u[1], b_u[1]) // 20) + 1):
                    segs_u.setdefault((cx_, cy_), []).append((a_u, b_u, an_u))
    def _cerca_calle(x, y, m_=8.0):
        kx, ky = int(x // 20), int(y // 20)
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                for (a_u, b_u, an_u) in segs_u.get((kx + ddx, ky + ddy), ()):
                    vx, vy = b_u[0] - a_u[0], b_u[1] - a_u[1]
                    l2 = vx * vx + vy * vy
                    f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a_u[0]) * vx + (y - a_u[1]) * vy) / l2))
                    if math.hypot(x - a_u[0] - vx * f, y - a_u[1] - vy * f) < an_u / 2.0 + m_:
                        return True
        return False
    def _fila_pacas(s0_, s1_, lado_):
        n_ = 0
        s_ = s0_
        while s_ <= s1_:
            (pp, _) = pos_side(s_, lado_, 2.5)
            if not _cerca_calle(pp[0], pp[1]):
                pk_ = clone(lib['paca'], pp, rot_facing_road(s_, lado_))
                pk_.name = 'CARRERA_paca_tierra'
                n_ += 1
            ds_ = 1.0
            while ds_ < 6.0:
                (pq_, _) = pos_side(s_ + ds_, lado_, 2.5)
                if math.hypot(pq_[0] - pp[0], pq_[1] - pp[1]) >= 2.9:
                    break
                ds_ += 0.5
            s_ += ds_
        ocupado.append((lado_, s0_, s1_))
        return n_
    s_c26 = CURVAS[26]['s_idx'] * paso if 26 in CURVAS else None
    n_filas, n_pf = 0, 0
    for lado_ in (1, -1):
        caida = []
        for i in range(N):
            q = S[i]
            if q['sec'] != 'dirt':
                continue
            s_ = i * paso
            if s_c26 is not None and abs(s_ - s_c26) < 24.0:
                continue                      # la 26 ya lleva su fila (zona_tierra)
            z_b = q['z'] - q['lat'] * lado_ * q['w'] / 2.0
            for (off_, caida_) in ((10.0, 2.5), (15.0, 3.5), (25.0, 6.0)):
                (p_o, _) = pos_side(s_, lado_, off_)
                if _z_tri(p_o[0], p_o[1])[0] < z_b - caida_:
                    caida.append(s_)
                    break
        tramos_c = []
        for s_ in caida:
            if tramos_c and s_ - tramos_c[-1][1] <= 10.0:
                tramos_c[-1][1] = s_
            else:
                tramos_c.append([s_, s_])
        for (a_, b_) in tramos_c:
            if b_ - a_ < 12.0:
                continue
            n_pf += _fila_pacas(a_ - 6.0, b_ + 6.0, lado_)
            n_filas += 1
    n_cv = 0
    for n in (15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25):      # v1 (N1 de E): tambien la 21 y la 23
        if n not in CURVAS:
            continue
        s_c = CURVAS[n]['s_idx'] * paso
        p = frame(s_c)
        outside = -1 if p['lat'] > 0 else 1
        for ds in (-7, 0, 7):
            if any(sd_ == outside and s0_ - 1.5 <= s_c + ds <= s1_ + 1.5 for (sd_, s0_, s1_) in ocupado):
                continue                      # ya hay fila continua en ese lado
            (pp, _) = pos_side(s_c + ds, outside, 2.5)
            if _cerca_calle(pp[0], pp[1], 3.0):
                continue                      # v3: ni sobre la boca de un camino
            pk_ = clone(lib['paca'], pp, rot_facing_road(s_c + ds, outside))
            pk_.name = 'CARRERA_paca_tierra'
            n_cv += 1
    log('tierra: %d filas continuas de pacas sobre terraplenes (%d pacas) + %d pacas de curva' % (n_filas, n_pf, n_cv))
safe('pacas_tierra', pacas_tierra)

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

# ============ RONDA 15: DESPEJE FINAL (urbanismo sin cosas sin sentido) ============
# Arboles y mobiliario colocados por zonas antiguas que no conocen el plan urbano: fuera
# los que caen sobre una calle/camino/escalera o dentro de un edificio; los carteles se
# apartan al borde del camino. (asentar_objetos.py los apoya luego en el suelo real.)
def despeje_final():
    ejes = list(PUEBLO_INFO.get('ejes', [])) + list(CAMINOS_INFO.get('ejes', []))
    d_eje = _crear_d_eje(ejes)                 # v2 integrador: comun con zona_camaras
    en_edificio, rects = _crear_en_edificio()
    # v1 integrador (N2 de D): poligonos de plazas (plan urbano + plazas del integrador) y fuentes
    fuentes = [(o.location.x, o.location.y) for o in root_col.objects if o.parent is None and o.name.startswith('ITAL_fuente')]
    en_plaza = _crear_en_plaza()
    n_a = n_p = n_c = 0
    n_cam_q = [0]
    for ob in list(root_col.objects):
        try:
            if ob.parent is None or not ob.parent.name.startswith(('ITAL_cipreses', 'ITAL_bancal')):
                continue
            if not ob.name.startswith(('ITAL_cipres', 'ITAL_olivo')):
                continue
            w_ = ob.matrix_world.translation
        except ReferenceError:
            continue
        if d_eje(w_.x, w_.y)[0] < 0.8 or en_edificio(w_.x, w_.y, 1.0) is not None:
            for ch in list(ob.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(ob, do_unlink=True)
            n_a += 1
    for ob in list(root_col.objects):
        try:
            if ob.parent is not None:
                continue
            nm = ob.name
        except ReferenceError:
            continue
        x, y = ob.location.x, ob.location.y
        if nm.startswith('CAMINO_cartel'):
            d, pp, v = d_eje(x, y)
            if pp is not None and d < 0.8:
                lv = math.hypot(*v) or 1.0
                nx_, ny_ = -v[1] / lv, v[0] / lv
                sg = 1.0 if ((x - pp[0]) * nx_ + (y - pp[1]) * ny_) >= 0 else -1.0
                emp = 0.8 - d + 0.4
                ob.location.x += sg * nx_ * emp
                ob.location.y += sg * ny_ * emp
                ob.location.z = z_terreno(ob.location.x, ob.location.y)
                n_c += 1
            # v2 integrador (C2-09): tampoco dentro de un edificio (el panel atravesaba la esquina de una casa): se
            # desplaza por el eje del camino mas cercano hasta que quede fuera (y a >= 0.8 m de las calles)
            x, y = ob.location.x, ob.location.y
            if en_edificio(x, y, 1.3) is not None:
                d, pp, v = d_eje(x, y)
                lv = math.hypot(*v) if v is not None else 0.0
                if lv > 1e-6:
                    tx_, ty_ = v[0] / lv, v[1] / lv
                    for t_ in (1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0, 5.0, -5.0, 6.0, -6.0):
                        xn_, yn_ = x + tx_ * t_, y + ty_ * t_
                        if en_edificio(xn_, yn_, 1.3) is None and d_eje(xn_, yn_)[0] >= 0.8:
                            ob.location.x, ob.location.y = xn_, yn_
                            ob.location.z = z_terreno(xn_, yn_)
                            n_c += 1
                            break
            continue
        if nm.startswith('COCHE_fila_hotel'):
            continue          # aparcados en la losa del hotel a proposito
        es_plazoleta = nm.startswith('VEG_plazoleta')
        es_arbol = nm.startswith(DESPEJE_ARBOL) and not nm.startswith(('VEG_penon', 'VEG_roca'))
        es_prop = nm.startswith(DESPEJE_PROP)
        if not (es_arbol or es_prop):
            continue
        r_p = 0.0
        for h in [ob] + list(ob.children_recursive):
            if h.type == 'MESH':
                for c in h.bound_box:
                    w_ = h.matrix_world @ Vector(c)
                    r_p = max(r_p, math.hypot(w_.x - x, w_.y - y))
        if es_arbol:
            # v1 integrador (C-11): cuenta la COPA (la caja de la jerarquia; ~0.7 de su semidiagonal), no solo el
            # tronco: los pinos parasol atravesaban tejados con el tronco a 1-2 m de la fachada
            r_c = min(r_p, 9.0) * 0.7
            quitar = (en_edificio(x, y, 1.0) is not None
                      or any(en_edificio(x + r_c * math.cos(a_), y + r_c * math.sin(a_), 0.3) is not None
                             for a_ in (0.0, 0.785, 1.571, 2.356, 3.142, 3.927, 4.712, 5.498)))
            if not es_plazoleta:
                # (N2 de D) ni dentro de plazas, plazoletas y fondos de saco ni en el vaso de una fuente
                quitar = quitar or d_eje(x, y)[0] < 0.8 or en_plaza(x, y) or any(
                    abs(fx_ - x) < 3.5 and abs(fy_ - y) < 3.5 and math.hypot(fx_ - x, fy_ - y) < 3.5 for (fx_, fy_) in fuentes)
        else:
            r_p = min(r_p, 6.0) * 0.8
            # v2 integrador (F2-04): el ramal propio de un coche-camara no cuenta (era el que la borraba)
            excl = ()
            if nm.startswith('CAMARA_tierra'):
                try:
                    excl = (int(ob.get('eje_ramal', -1)),)
                except Exception:
                    excl = ()
            quitar = d_eje(x, y, excl)[0] < 0.5 + r_p or en_edificio(x, y, 0.5 + r_p) is not None
            if nm.startswith('VEG_roca') and not quitar:
                # v3 integrador (N3 de s 1345): un pedrusco de 5 m (VEG_roca.047) en mitad de la plaza del pueblo alto,
                # junto a la fuente: ninguna roca suelta con el pie (o su contorno) en una plaza, plazoleta o fondo de saco
                quitar = en_plaza(x, y) or any(en_plaza(x + r_p * 0.7 * math.cos(a_), y + r_p * 0.7 * math.sin(a_))
                                               for a_ in (0.0, 1.571, 3.142, 4.712)) or any(
                    abs(fx_ - x) < 3.5 + r_p and abs(fy_ - y) < 3.5 + r_p for (fx_, fy_) in fuentes)
        if quitar:
            asociados = []
            if nm.startswith('CAMARA_tierra'):
                # v2 integrador (F2-04/N1): con la camara se van su peana y su ramal (camino, terraplen y valla)
                asociados = [str(ob.get('peana', ''))] + [n_ for n_ in str(ob.get('ramal', '')).split('|') if n_]
                n_cam_q[0] += 1
            for ch in list(ob.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(ob, do_unlink=True)
            for n_ in asociados:
                o_ = bpy.data.objects.get(n_) if n_ else None
                if o_ is not None:
                    for ch in list(o_.children_recursive):
                        bpy.data.objects.remove(ch, do_unlink=True)
                    bpy.data.objects.remove(o_, do_unlink=True)
            if es_arbol:
                n_a += 1
            else:
                n_p += 1
    # v2 integrador (D2-06/G-N1): ninguna peana sin su camara (a < 1 m de su centro)
    cams = [o.matrix_world.translation for o in root_col.objects if o.parent is None and o.name.startswith('CAMARA_tierra')]
    n_pe = 0
    for o in [o for o in root_col.objects if o.parent is None and o.type == 'MESH' and o.name.startswith('CAMARA_peana')]:
        ws_ = [o.matrix_world @ Vector(c) for c in o.bound_box]
        cx_, cy_ = sum(w_.x for w_ in ws_) / 8.0, sum(w_.y for w_ in ws_) / 8.0
        if not any(math.hypot(c_.x - cx_, c_.y - cy_) < 1.0 for c_ in cams):
            bpy.data.objects.remove(o, do_unlink=True)
            n_pe += 1
    log('despeje final: %d ejes de calle/camino, %d edificios; quitados %d arboles y %d props (%d coches-camara con su peana '
        'y ramal), %d carteles apartados, %d peanas sin camara retiradas; quedan %d coches-camara'
        % (len(ejes), len(rects), n_a, n_p, n_cam_q[0], n_c, n_pe, len(cams)))

safe('despeje_final', despeje_final)

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
