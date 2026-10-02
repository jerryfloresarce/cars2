# Ensambla el circuito en Blender 5.1 desde geometria_3d.json:
# pista (asfalto/tierra/puente), pianos, faldones y pilas de puente, terreno,
# mar, linea de salida, sol y camaras; guarda .blend y renderiza 4 vistas.
# Ejecutar:
#   blender --background --factory-startup --python construir_pista.py
import json
import math
import os

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
OUT_BLEND = BASE + r'\03_blender\porto_corsa.blend'
OUT_R = BASE + r'\03_blender\renders'
os.makedirs(OUT_R, exist_ok=True)

S = G['muestras']
N = G['n']

# --- limpieza de escena ---
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

col = bpy.context.scene.collection

def new_mesh_obj(name, verts, faces, mats=None, face_mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if mats:
        for m in mats:
            ob.data.materials.append(m)
        if face_mat:
            for p, mi in zip(me.polygons, face_mat):
                p.material_index = mi
    return ob

def mat(name, rgba, rough=0.8, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit:
        bsdf.inputs['Emission Color'].default_value = rgba
        bsdf.inputs['Emission Strength'].default_value = emit
    m.diffuse_color = rgba
    return m

def mat_con_ruido(nombre, c1, c2, escala, rough=0.95, bump=0.35):
    """Material con moteado procedural sutil (dos tonos + relieve)."""
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = rough
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = escala
    noise.inputs['Detail'].default_value = 6.0
    mixc = nt.nodes.new('ShaderNodeMix')
    mixc.data_type = 'RGBA'
    mixc.inputs[6].default_value = c1
    mixc.inputs[7].default_value = c2
    nt.links.new(noise.outputs['Fac'], mixc.inputs['Factor'])
    nt.links.new(mixc.outputs[2], bsdf.inputs['Base Color'])
    bmp = nt.nodes.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = bump
    nt.links.new(noise.outputs['Fac'], bmp.inputs['Height'])
    nt.links.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    m.diffuse_color = c1
    return m

M_ASF = mat_con_ruido('MAT_asfalto', (0.105, 0.102, 0.108, 1), (0.075, 0.073, 0.080, 1),
                      140.0, rough=0.85, bump=0.25)
M_TIE = mat_con_ruido('MAT_tierra', (0.60, 0.43, 0.24, 1), (0.48, 0.35, 0.19, 1),
                      60.0, rough=1.0, bump=0.5)
M_PUE = mat('MAT_puente_tablero', (0.09, 0.09, 0.10, 1), 0.85)
M_PIE = mat('MAT_piedra', (0.78, 0.72, 0.60, 1), 0.9)
M_KR = mat('MAT_piano_rojo', (0.75, 0.05, 0.05, 1), 0.6)
M_KB = mat('MAT_piano_blanco', (0.9, 0.9, 0.9, 1), 0.6)
def mat_terreno():
    m = bpy.data.materials.get('MAT_terreno')
    if m:
        return m
    m = bpy.data.materials.new('MAT_terreno')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = 1.0
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    mapr = nt.nodes.new('ShaderNodeMapRange')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
    mapr.inputs['From Min'].default_value = -4.0
    mapr.inputs['From Max'].default_value = 170.0
    e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.40, 0.48, 0.34, 1)     # fondo marino
    e[1].position = 0.023; e[1].color = (0.72, 0.66, 0.48, 1)   # arena (z~0)
    for pos, col in [(0.042, (0.22, 0.40, 0.13, 1)),            # hierba baja
                     (0.50, (0.20, 0.33, 0.12, 1)),             # monte
                     (0.97, (0.30, 0.33, 0.20, 1))]:            # cumbres
        el = ramp.color_ramp.elements.new(pos)
        el.color = col
    nt.links.new(mapr.outputs['Result'], ramp.inputs['Fac'])
    # parches naturales de pradera (variacion a gran escala, ~200 m)
    texm = nt.nodes.new('ShaderNodeTexCoord')
    noim = nt.nodes.new('ShaderNodeTexNoise')
    noim.inputs['Scale'].default_value = 0.005
    noim.inputs['Detail'].default_value = 5.0
    rampm = nt.nodes.new('ShaderNodeValToRGB')
    em = rampm.color_ramp.elements
    em[0].position = 0.3; em[0].color = (0.78, 0.85, 0.70, 1)
    em[1].position = 0.7; em[1].color = (1.15, 1.10, 0.95, 1)
    mixm = nt.nodes.new('ShaderNodeMix')
    mixm.data_type = 'RGBA'
    mixm.blend_type = 'MULTIPLY'
    mixm.inputs['Factor'].default_value = 1.0
    nt.links.new(texm.outputs['Object'], noim.inputs['Vector'])
    nt.links.new(noim.outputs['Fac'], rampm.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], mixm.inputs[6])
    nt.links.new(rampm.outputs['Color'], mixm.inputs[7])
    # ROCA en las pendientes fuertes (taludes, acantilados de la costa)
    sepn = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Normal'], sepn.inputs['Vector'])
    talud = nt.nodes.new('ShaderNodeMapRange')
    talud.clamp = True
    talud.interpolation_type = 'SMOOTHSTEP'
    talud.inputs['From Min'].default_value = 0.40
    talud.inputs['From Max'].default_value = 0.58   # ronda 14: solo paredes de > 55 grados son roca; las laderas fuertes siguen verdes
    talud.inputs['To Min'].default_value = 1.0
    talud.inputs['To Max'].default_value = 0.0
    # borde irregular: a la Z de la normal se le suma un ruido de +-0.08
    nzt = nt.nodes.new('ShaderNodeTexNoise')
    nzt.inputs['Scale'].default_value = 0.03
    nzt.inputs['Detail'].default_value = 3.0
    nt.links.new(texm.outputs['Object'], nzt.inputs['Vector'])
    esc = nt.nodes.new('ShaderNodeMath')
    esc.operation = 'MULTIPLY_ADD'
    esc.inputs[1].default_value = 0.16
    esc.inputs[2].default_value = -0.08
    nt.links.new(nzt.outputs['Fac'], esc.inputs[0])
    suma = nt.nodes.new('ShaderNodeMath')
    suma.operation = 'ADD'
    nt.links.new(sepn.outputs['Z'], suma.inputs[0])
    nt.links.new(esc.outputs['Value'], suma.inputs[1])
    nt.links.new(suma.outputs['Value'], talud.inputs['Value'])
    mixr = nt.nodes.new('ShaderNodeMix')
    mixr.data_type = 'RGBA'
    mixr.blend_type = 'MIX'
    nt.links.new(talud.outputs['Result'], mixr.inputs['Factor'])
    nt.links.new(mixm.outputs[2], mixr.inputs[6])
    mixr.inputs[7].default_value = (0.25, 0.23, 0.19, 1)   # lineal: gris caliza medio en pantalla
    nt.links.new(mixr.outputs[2], bsdf.inputs['Base Color'])
    m.diffuse_color = (0.32, 0.45, 0.2, 1)
    return m

M_TER = mat_terreno()
M_FONDO = M_TER
M_AGUA = mat('MAT_agua', (0.05, 0.42, 0.55, 1), 0.15)
M_LINEA = mat('MAT_linea_salida', (0.95, 0.95, 0.95, 1), 0.5)

MAT_IDX = {'straight': 0, 'tech': 0, 'norm': 0, 'dirt': 1, 'bridge': 0}   # pavimento NORMALIZADO: el mismo asfalto en todo el circuito (tambien en el viaducto)

# --- pista ---
def edge_pts(i):
    p = S[i]
    half = p['w'] / 2.0
    dzl = -p['lat'] * half
    L_ = (p['x'] + p['nx'] * half, p['y'] + p['ny'] * half, p['z'] + dzl)
    R_ = (p['x'] - p['nx'] * half, p['y'] - p['ny'] * half, p['z'] - dzl)
    return L_, R_

verts = []
for i in range(N):
    L_, R_ = edge_pts(i)
    verts.extend([L_, R_])
faces = []
fmat = []
for i in range(N):
    j = (i + 1) % N
    faces.append((2 * i, 2 * i + 1, 2 * j + 1, 2 * j))
    fmat.append(MAT_IDX[S[i]['sec']])
pista = new_mesh_obj('PISTA', verts, faces, [M_ASF, M_TIE, M_PUE], fmat)
pista.data.shade_smooth()

# --- utilidades de interpolacion a lo largo de la pista ---
def muestra_s(s_m):
    """Muestra interpolada en la abscisa s_m (m)."""
    f = (s_m / G['paso_m']) % N
    i = int(f)
    t = f - i
    pa, pb = S[i % N], S[(i + 1) % N]
    q = {k: pa[k] * (1 - t) + pb[k] * t for k in ('x', 'y', 'z', 'nx', 'ny', 'w', 'lat')}
    ln = math.hypot(q['nx'], q['ny']) or 1.0
    q['nx'] /= ln
    q['ny'] /= ln
    return q

def punto_s(s_m, lateral, dz):
    q = muestra_s(s_m)
    return (q['x'] + q['nx'] * lateral, q['y'] + q['ny'] * lateral,
            q['z'] - q['lat'] * lateral + dz)

_lw = G.get('loews') or {}
S_LOEWS = (_lw.get('s_idx') or 0) * G['paso_m']
# radio real de la isleta (mismo calculo que zona_loews en integrar): distancia del
# centro al borde interior del asfalto menos la acera
_R_ISLA = 6.0
if S_LOEWS:
    _ilw = int(_lw['s_idx'])
    _R_ISLA = min(math.hypot(S[j % N]['x'] - _lw['x'], S[j % N]['y'] - _lw['y']) - S[j % N]['w'] / 2
                  for j in range(_ilw - 45, _ilw + 46)) - 0.6

def _curv(i, d=3):
    pa, pb = S[(i - d) % N], S[(i + d) % N]
    return math.atan2(pa['ny'] * pb['nx'] - pa['nx'] * pb['ny'],
                      pa['nx'] * pb['nx'] + pa['ny'] * pb['ny']) / (2 * d * G['paso_m'])

# --- pianos (rojo/blanco) PLANOS y POR DENTRO de la calzada, como en la peli:
# banda de 1.3 m cuyo borde exterior es el borde del asfalto; bloques de 1.3 m ---
PIANO_ANCHO = 1.3
PIANO_BLOQUE = 1.3
kv, kf, kfm = [], [], []
def _piano(s0, s1, sgn):
    """Banda de piano entre las abscisas s0..s1 (m) en el lado sgn (+1 izq, -1 der)."""
    n_b = max(2, int(round((s1 - s0) / PIANO_BLOQUE)))
    base = len(kv)
    for k in range(n_b + 1):
        s_k = s0 + (s1 - s0) * k / n_b
        q = muestra_s(s_k)
        half = q['w'] / 2.0
        kv.append(punto_s(s_k, sgn * (half - 0.04), 0.06))
        kv.append(punto_s(s_k, sgn * (half - 0.04 - PIANO_ANCHO), 0.05))
    for k in range(n_b):
        o = base + 2 * k
        kf.append((o, o + 1, o + 3, o + 2) if sgn < 0 else (o + 1, o, o + 2, o + 3))
        kfm.append(k % 2)

ZONAS_PIANO = []   # (s0, s1, sgn) para que el zigzag sepa donde empiezan
for strip in G['pianos']:
    a_, b_, lado = strip['a'], strip['b'], strip['lado']
    sgn = 1 if lado == 'izq' else -1
    if any(S[i % N]['sec'] == 'dirt' for i in range(a_, b_ + 1)):
        continue
    s0, s1 = a_ * G['paso_m'], b_ * G['paso_m']
    if S_LOEWS and abs((s0 + s1) / 2 - S_LOEWS) < 70:
        continue            # la horquilla lleva su propio juego completo (abajo)
    ZONAS_PIANO.append((s0, s1, sgn))
if S_LOEWS:
    # horquilla de la rotonda: anillo interior completo + exterior en entrada y salida
    _pl = S[int(S_LOEWS / G['paso_m']) % N]
    _ia = int(S_LOEWS / G['paso_m'])
    _in = 1 if _curv(_ia, 4) < 0 else -1       # interior por GEOMETRIA (_curv<0 = curva a izquierdas)
    ZONAS_PIANO.append((S_LOEWS - 56.0, S_LOEWS + 58.0, _in))
    ZONAS_PIANO.append((S_LOEWS - 56.0, S_LOEWS + 58.0, -_in))
for (s0, s1, sgn) in ZONAS_PIANO:
    _piano(s0, s1, sgn)
if kv:
    pianos = new_mesh_obj('PIANOS', kv, kf, [M_KR, M_KB], kfm)

# zonas de ZIGZAG (frenadas casi rectas antes de un piano): se calculan aqui para
# que las lineas de borde sepan donde NO pintarse
ZONAS_ZZ = []        # (s_fin, largo, nombre)
if S_LOEWS:
    ZONAS_ZZ.append((S_LOEWS - 57.0, 34.0, 'horquilla'))
_vistos = []
for (s0, s1, sgn) in ZONAS_PIANO:
    if S_LOEWS and abs(s0 - (S_LOEWS - 56.0)) < 1.0:
        continue
    if not ((3150.0 < s0 < 4350.0) or (4700.0 < s0 < 5050.0)):
        continue
    if any(abs(s0 - v) < 60.0 for v in _vistos):
        continue
    i_a = int((s0 - 30.0) / G['paso_m'])
    if max(abs(_curv(i)) for i in range(i_a - 6, i_a + 12)) > 0.010:
        continue        # la frenada tiene que ser casi recta
    if any(S[i % N]['sec'] == 'dirt' for i in range(i_a - 6, i_a + 16)):
        continue
    ZONAS_ZZ.append((s0 - 1.0, 21.0, 'c%d' % int(s0)))
    _vistos.append(s0)

def sin_linea_de_borde(i, sgn):
    """True donde el borde lo ocupa un piano (de ese lado) o un zigzag (ambos)."""
    s_i = i * G['paso_m']
    for (s0, s1, sg) in ZONAS_PIANO:
        if sg == sgn and s0 - 0.5 <= s_i <= s1 + 0.5:
            return True
    for (s_fin_, largo_, _n) in ZONAS_ZZ:
        if s_fin_ - largo_ - 3.0 <= s_i <= s_fin_ + 0.5:
            return True
    return False

# --- puentes: faldones y pilas ---
bv, bf = [], []
piers = []
run = []
for i in range(N + 1):
    is_b = S[i % N]['sec'] == 'bridge'
    if is_b:
        run.append(i % N)
    if (not is_b or i == N) and run:
        if len(run) > 4:
            for k, idx in enumerate(run):
                L_, R_ = edge_pts(idx)
                for P in (L_, R_):
                    bv.append(P)
                    bv.append((P[0], P[1], P[2] - 3.2))
            off = len(bv) - 4 * len(run)
            for k in range(len(run) - 1):
                o = off + 4 * k
                bf.append((o, o + 1, o + 5, o + 4))          # faldon izq
                bf.append((o + 2, o + 3, o + 7, o + 6))      # faldon der
            for k in range(0, len(run), 8):                  # pila cada ~16 m
                p = S[run[k]]
                piers.append((p['x'], p['y'], p['z']))
        run = []
if bv:
    new_mesh_obj('PUENTE_FALDONES', bv, bf, [M_PIE], [0] * len(bf))
pv, pf = [], []
for (px, py, pz) in piers:
    w = 2.6
    z0, z1 = -4.5, pz - 0.6
    base = len(pv)
    for (dx, dy) in ((-w, -w), (w, -w), (w, w), (-w, w)):
        pv.append((px + dx, py + dy, z0))
        pv.append((px + dx, py + dy, z1))
    for k in range(4):
        a0, a1 = base + 2 * k, base + 2 * ((k + 1) % 4)
        pf.append((a0, a0 + 1, a1 + 1, a1))
if pv:
    new_mesh_obj('PUENTE_PILAS', pv, pf, [M_PIE], [0] * len(pf))

# --- marcas viales (como en la pelicula) ---
M_MB = mat('MAT_marca_blanca', (0.88, 0.88, 0.86, 1), 0.55)
M_MA = mat('MAT_marca_amarilla', (0.95, 0.78, 0.05, 1), 0.55)

def punto_lateral(i, lateral, dz):
    p = S[i % N]
    # OJO: la calzada va PERALTADA; todo lo que se apoya en ella sigue su plano
    return (p['x'] + p['nx'] * lateral, p['y'] + p['ny'] * lateral,
            p['z'] - p['lat'] * lateral + dz)

def ribbon(indices, lateral_fn, width, material, dz=0.035, name='MARCA'):
    vs, fs = [], []
    for k, i in enumerate(indices):
        lat_c = lateral_fn(k, i)
        a = punto_lateral(i, lat_c - width / 2, dz)
        b = punto_lateral(i, lat_c + width / 2, dz)
        vs.extend([a, b])
    for k in range(len(indices) - 1):
        o = 2 * k
        fs.append((o, o + 1, o + 3, o + 2))
    if fs:
        new_mesh_obj(name, vs, fs, [material], [0] * len(fs))

# lineas de borde continuas (no en tierra)
for sgn in (1, -1):
    run = []
    tramo = 0
    for i in range(N + 1):
        ok = S[i % N]['sec'] != 'dirt' and not sin_linea_de_borde(i % N, sgn)
        if ok:
            run.append(i % N)
        if (not ok or i == N) and run:
            if len(run) > 3:
                ribbon(run, lambda k, i2, s=sgn: s * (S[i2]['w'] / 2 - 0.45),
                       0.14, M_MB, name='MARCA_BORDE_%d_%d' % (sgn, tramo))
                tramo += 1
            run = []

# linea central: CONTINUA en el sector del casino (como en la pelicula), a trazos
# cortos dentro de la horquilla y discontinua normal en el resto
_bi = [i for i in range(N) if S[i]['sec'] == 'bridge']
S_CAS0 = 3180.0
S_CAS1 = (min(_bi) * G['paso_m'] + 160.0) if _bi else 3700.0
def _cinta_s(s0, s1, lat_fn, ancho, material, dz, nombre, paso_s=1.0):
    n_ = max(1, int(round((s1 - s0) / paso_s)))
    vs, fs = [], []
    for k in range(n_ + 1):
        s_k = s0 + (s1 - s0) * k / n_
        l_ = lat_fn(k, s_k)
        vs.append(punto_s(s_k, l_ + ancho / 2, dz))
        vs.append(punto_s(s_k, l_ - ancho / 2, dz))
    for k in range(n_):
        o = 2 * k
        fs.append((o, o + 1, o + 3, o + 2))
    new_mesh_obj(nombre, vs, fs, [material], [0] * len(fs))

i = 25
while i < N - 25:
    s_i = i * G['paso_m']
    if S[i]['sec'] != 'dirt' and not (S_CAS0 - 12 < s_i < S_CAS1 + 12):
        ribbon(list(range(i, i + 3)), lambda k, i2: 0.0, 0.16, M_MB,
               name='MARCA_CENTRO_%d' % i)
    i += 6
if S_LOEWS:
    _cinta_s(S_CAS0, S_LOEWS - 40.0, lambda k, s_k: 0.0, 0.20, M_MB, 0.04, 'MARCA_CENTRO_continua_a')
    _cinta_s(S_LOEWS + 40.0, S_CAS1, lambda k, s_k: 0.0, 0.20, M_MB, 0.04, 'MARCA_CENTRO_continua_b')
    s_t = S_LOEWS - 40.0
    k_t = 0
    while s_t < S_LOEWS + 40.0 - 0.8:
        _cinta_s(s_t, s_t + 0.8, lambda k, s_k: 0.0, 0.20, M_MB, 0.04,
                 'MARCA_CENTRO_horquilla_%d' % k_t, paso_s=0.4)
        s_t += 1.6
        k_t += 1

# ZIGZAG amarillo limon: una linea pegada a CADA borde, onda triangular simetrica,
# solo en la frenada previa a las curvas cerradas; termina donde empieza el piano
M_MA_Z = mat('MAT_marca_zigzag', (0.89, 0.74, 0.05, 1), 0.6)
ZZ_IN, ZZ_OUT, ZZ_PER, ZZ_W = 0.30, 1.45, 2.6, 0.14   # mas pequeno (el usuario: 'no son tan grandes')
def _zigzag(s_fin, largo, nombre):
    """Dos zigzags (izq y der) en los 'largo' m anteriores a s_fin."""
    n_per = max(3, int(largo / ZZ_PER))
    s_ini = s_fin - n_per * ZZ_PER
    for sgn in (1, -1):
        vs, fs = [], []
        for k in range(2 * n_per + 1):            # un vertice cada medio periodo
            s_k = s_ini + k * ZZ_PER / 2
            half = muestra_s(s_k)['w'] / 2.0
            d_b = ZZ_IN if k % 2 == 0 else ZZ_OUT   # empieza y acaba pegado al borde
            c = sgn * (half - d_b)
            # trazo de grosor constante: desplazamos el vertice a lo largo de la bisectriz
            vs.append(punto_s(s_k - ZZ_W * 0.72, c, 0.05))
            vs.append(punto_s(s_k + ZZ_W * 0.72, c, 0.05))
        for k in range(2 * n_per):
            o = 2 * k
            fs.append((o, o + 1, o + 3, o + 2))
        new_mesh_obj('MARCA_ZIGZAG_%s_%s' % (nombre, 'IZQ' if sgn > 0 else 'DER'), vs, fs,
                     [M_MA_Z], [0] * len(fs))

n_zz = 0
for (s_fin_, largo_, nombre_) in ZONAS_ZZ:
    _zigzag(s_fin_, largo_, nombre_)
    n_zz += 1
print('zigzags pintados:', n_zz, '| zonas de piano:', len(ZONAS_PIANO))

# --- GUARDARRAIL de acero (Armco) a ambos lados en el sector del casino ---
M_GR = mat('MAT_guardarrail', (0.30, 0.26, 0.20, 1), 0.45, 0.7)
def _guardarrail(s0, s1, sgn, nombre):
    vs, fs = [], []
    n_ = int((s1 - s0) / 2.0)
    for k in range(n_ + 1):
        s_k = s0 + (s1 - s0) * k / n_
        half = muestra_s(s_k)['w'] / 2.0
        l0, l1 = sgn * (half + 0.10), sgn * (half + 0.20)
        ze = -muestra_s(s_k)['lat'] * sgn * half      # cota del borde respecto al eje
        for (l_, dz_) in ((l0, 0.42), (l0, 0.62), (l0 + sgn * 0.05, 0.72), (l0, 0.82),
                          (l1, 0.82), (l1, 0.42)):
            q = muestra_s(s_k)
            vs.append((q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, q['z'] + ze + dz_))
    for k in range(n_):
        o = 6 * k
        for j in range(6):
            a0, a1 = o + j, o + (j + 1) % 6
            fs.append((a0, a1, a1 + 6, a0 + 6))
    # postes cada 4 m
    for k in range(0, n_ + 1, 2):
        s_k = s0 + (s1 - s0) * k / n_
        q = muestra_s(s_k)
        half = q['w'] / 2.0
        ze = -q['lat'] * sgn * half
        cx_ = q['x'] + q['nx'] * sgn * (half + 0.27)
        cy_ = q['y'] + q['ny'] * sgn * (half + 0.27)
        b0 = len(vs)
        for (dx, dy) in ((-0.06, -0.06), (0.06, -0.06), (0.06, 0.06), (-0.06, 0.06)):
            vs.append((cx_ + dx, cy_ + dy, q['z'] + ze - 0.4))
            vs.append((cx_ + dx, cy_ + dy, q['z'] + ze + 0.78))
        for j in range(4):
            a0, a1 = b0 + 2 * j, b0 + 2 * ((j + 1) % 4)
            fs.append((a0, a0 + 1, a1 + 1, a1))
    new_mesh_obj(nombre, vs, fs, [M_GR], [0] * len(fs))
if S_LOEWS and _bi:
    _in_gr = 1 if _curv(int(S_LOEWS / G['paso_m']), 4) < 0 else -1
    for sgn in (1, -1):
        _fin = min(_bi) * G['paso_m'] - 2.0
        if sgn == _in_gr:
            # por el interior de la horquilla el rail se amontonaba en el apice: alli
            # ya esta el murete de la isleta
            _guardarrail(S_CAS0 + 20.0, S_LOEWS - 30.0, sgn, 'GUARDARRAIL_%s_a' % ('IZQ' if sgn > 0 else 'DER'))
            if _fin - (S_LOEWS + 30.0) > 8.0:
                _guardarrail(S_LOEWS + 30.0, _fin, sgn, 'GUARDARRAIL_%s_b' % ('IZQ' if sgn > 0 else 'DER'))
        else:
            _guardarrail(S_CAS0 + 20.0, _fin, sgn, 'GUARDARRAIL_%s' % ('IZQ' if sgn > 0 else 'DER'))

# --- aceras con bordillo en los tramos urbanos ---
M_ACERA = mat('MAT_acera_piedra', (0.34, 0.31, 0.27, 1), 0.95)   # gris piedra: en blanco puro se clipaba
M_BORDILLO = mat('MAT_bordillo_piedra', (0.40, 0.37, 0.33, 1), 0.9)
TRAMOS_URBANOS = [(620, 1100), (1260, 1560), (2480, 2760), (4560, 4930)]
for (s0u, s1u) in TRAMOS_URBANOS:
    i0u = int(s0u / G['paso_m'])
    i1u = int(s1u / G['paso_m'])
    idxs_u = [i for i in range(i0u, i1u) if S[i]['sec'] not in ('dirt', 'bridge')]
    if len(idxs_u) < 4:
        continue
    for sgn in (1, -1):
        ribbon(idxs_u, lambda k, i2, s=sgn: s * (S[i2]['w'] / 2 + 1.35),
               2.3, M_ACERA, dz=0.055, name='ACERA_%d_%d' % (s0u, sgn))
        ribbon(idxs_u, lambda k, i2, s=sgn: s * (S[i2]['w'] / 2 + 0.12),
               0.24, M_BORDILLO, dz=0.07, name='BORDILLO_%d_%d' % (s0u, sgn))

# --- arcenes de hierba (tapan la union pista-terreno), salvo en puentes ---
M_ARCEN = mat('MAT_arcen', (0.21, 0.37, 0.125, 1), 1.0)
_TA = G['terreno']
def _zt_arcen(x, y):
    fx = (x - _TA['x0']) / _TA['cell']
    fy = (y - _TA['y0']) / _TA['cell']
    i0 = max(0, min(_TA['nx'] - 2, int(fx)))
    j0 = max(0, min(_TA['ny'] - 2, int(fy)))
    tx = min(max(fx - i0, 0), 1)
    ty = min(max(fy - j0, 0), 1)
    zz = lambda i, j: _TA['z'][j * _TA['nx'] + i]
    return ((zz(i0, j0) * (1 - tx) + zz(i0 + 1, j0) * tx) * (1 - ty)
            + (zz(i0, j0 + 1) * (1 - tx) + zz(i0 + 1, j0 + 1) * tx) * ty)
for sgn in (1, -1):
    av_, af_ = [], []
    run = []
    for i in range(N + 1):
        ok = S[i % N]['sec'] != 'bridge'
        if ok:
            run.append(i % N)
        if (not ok or i == N) and run:
            if len(run) > 2:
                base = len(av_)
                for idx in run:
                    p = S[idx]
                    half = p['w'] / 2.0
                    dz = -p['lat'] * half * sgn
                    ex = p['x'] + sgn * p['nx'] * half
                    ey = p['y'] + sgn * p['ny'] * half
                    ez = p['z'] + dz
                    # el arcen nunca cruza el centro de la horquilla ni pisa el otro
                    # ramal (era la 'cuna verde' que atravesaba el asfalto)
                    e1, e2 = 1.8, 6.5
                    if S_LOEWS:
                        dc = math.hypot(ex - _lw['x'], ey - _lw['y'])
                        if dc < 30.0:
                            hacia_c = ((_lw['x'] - ex) * sgn * p['nx'] + (_lw['y'] - ey) * sgn * p['ny']) > 0
                            if hacia_c:
                                # RONDA 13: el arcen tampoco tapa la ISLETA (su rueda de flores
                                # quedaba bajo el cesped): se queda a 0.5 m de su radio
                                e2 = max(0.4, min(6.5, dc - (_R_ISLA + 0.5)))
                                e1 = min(1.8, e2 * 0.5)
                    mx_ = p['x'] + sgn * p['nx'] * (half + e1)
                    my_ = p['y'] + sgn * p['ny'] * (half + e1)
                    ox = p['x'] + sgn * p['nx'] * (half + e2)
                    oy = p['y'] + sgn * p['ny'] * (half + e2)
                    # plano 1.8 m y luego baja; el borde exterior SIEMPRE queda
                    # bajo el terreno (nada de repisas al aire)
                    zo = min(ez - 1.6, _zt_arcen(ox, oy) - 0.35)
                    av_.append((ex, ey, ez - 0.01))
                    av_.append((mx_, my_, ez - 0.05))
                    av_.append((ox, oy, zo))
                for k in range(len(run) - 1):
                    o = base + 3 * k
                    af_.append((o, o + 1, o + 4, o + 3))
                    af_.append((o + 1, o + 2, o + 5, o + 4))
            run = []
    if av_:
        arc = new_mesh_obj('ARCEN_%s' % ('IZQ' if sgn > 0 else 'DER'),
                           av_, af_, [M_TER], [0] * len(af_))  # mismo material que el terreno: union invisible
        arc.data.shade_smooth()

# --- linea de salida ---
p0 = S[0]
h0 = p0['w'] / 2 - 0.3
lv = []
for t in (0, 1):
    q = S[t * 2]
    lv.append((q['x'] + q['nx'] * h0, q['y'] + q['ny'] * h0, q['z'] - q['lat'] * h0 + 0.04))
    lv.append((q['x'] - q['nx'] * h0, q['y'] - q['ny'] * h0, q['z'] + q['lat'] * h0 + 0.04))
new_mesh_obj('LINEA_SALIDA', lv, [(0, 1, 3, 2)], [M_LINEA], [0])

# --- pit lane ---
PIT = G.get('pit_lane') or []
if PIT:
    pvts, pfcs = [], []
    for q in PIT:
        h = q['w'] / 2
        pvts.append((q['x'] + q['nx'] * h, q['y'] + q['ny'] * h, q['z'] - 0.015))
        pvts.append((q['x'] - q['nx'] * h, q['y'] - q['ny'] * h, q['z'] - 0.015))
    for k in range(len(PIT) - 1):
        o = 2 * k
        pfcs.append((o, o + 1, o + 3, o + 2))
    new_mesh_obj('PIT_LANE', pvts, pfcs, [M_ASF], [0] * len(pfcs))
    print('pit lane construido:', len(PIT), 'muestras')

# --- terreno ---
T = G['terreno']
nx_, ny_ = T['nx'], T['ny']
tz = T['z']
tmar = T['mar']
tv = []
for j in range(ny_):
    for i in range(nx_):
        tv.append((T['x0'] + i * T['cell'], T['y0'] + j * T['cell'], tz[j * nx_ + i]))
tf, tfm = [], []
for j in range(ny_ - 1):
    for i in range(nx_ - 1):
        a = j * nx_ + i
        tf.append((a, a + 1, a + nx_ + 1, a + nx_))
        tfm.append(0)
terreno = new_mesh_obj('TERRENO', tv, tf, [M_TER, M_FONDO], tfm)
terreno.data.shade_smooth()

# --- mar ---
ext = 9000.0  # el mar llega al horizonte tambien en las tomas aereas
av = [(T['x0'] - ext, T['y0'] - ext, 0.0),
      (T['x0'] + nx_ * T['cell'] + ext, T['y0'] - ext, 0.0),
      (T['x0'] + nx_ * T['cell'] + ext, T['y0'] + ny_ * T['cell'] + ext, 0.0),
      (T['x0'] - ext, T['y0'] + ny_ * T['cell'] + ext, 0.0)]
agua = new_mesh_obj('AGUA', av, [(0, 1, 2, 3)], [M_AGUA], [0])
# fondo marino bajo TODO el mar (el agua es translucida: sin fondo se veia el
# borde recto del terreno como un rectangulo claro en el agua)
new_mesh_obj('AGUA_fondo', [(x_, y_, -4.05) for (x_, y_, z_) in av], [(0, 1, 2, 3)], [M_TER], [0])
M_AGUA.blend_method = 'BLEND'
bsdf = M_AGUA.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Alpha'].default_value = 0.84
bsdf.inputs['Roughness'].default_value = 0.04
# mar con profundidad: turquesa costero -> azul profundo por parches grandes
ntw0 = M_AGUA.node_tree
txw = ntw0.nodes.new('ShaderNodeTexCoord')
nzw = ntw0.nodes.new('ShaderNodeTexNoise')
nzw.inputs['Scale'].default_value = 0.004
nzw.inputs['Detail'].default_value = 4.0
mixw = ntw0.nodes.new('ShaderNodeMix')
mixw.data_type = 'RGBA'
mixw.inputs[6].default_value = (0.015, 0.28, 0.44, 1)   # profundo
mixw.inputs[7].default_value = (0.04, 0.44, 0.54, 1)    # turquesa
ntw0.links.new(txw.outputs['Object'], nzw.inputs['Vector'])
ntw0.links.new(nzw.outputs['Fac'], mixw.inputs['Factor'])
ntw0.links.new(mixw.outputs[2], bsdf.inputs['Base Color'])
# olas suaves por normal procedural
ntw = M_AGUA.node_tree
tco = ntw.nodes.new('ShaderNodeTexCoord')
nzo = ntw.nodes.new('ShaderNodeTexNoise')
nzo.inputs['Scale'].default_value = 0.02
nzo.inputs['Detail'].default_value = 5.0
bmpw = ntw.nodes.new('ShaderNodeBump')
bmpw.inputs['Strength'].default_value = 0.12
ntw.links.new(tco.outputs['Object'], nzo.inputs['Vector'])
ntw.links.new(nzo.outputs['Fac'], bmpw.inputs['Height'])
ntw.links.new(bmpw.outputs['Normal'], bsdf.inputs['Normal'])

# --- muros de contencion de piedra donde la pista queda en alto ---
M_MUROC = mat('MAT_muro_contencion_piedra', (0.63, 0.58, 0.47, 1), 0.95)

def z_terreno_b(x, y):
    fx = (x - T['x0']) / T['cell']
    fy = (y - T['y0']) / T['cell']
    i0 = max(0, min(nx_ - 2, int(fx)))
    j0 = max(0, min(ny_ - 2, int(fy)))
    tx2 = min(max(fx - i0, 0), 1)
    ty2 = min(max(fy - j0, 0), 1)
    def zz(i, j):
        return tz[j * nx_ + i]
    return ((zz(i0, j0) * (1 - tx2) + zz(i0 + 1, j0) * tx2) * (1 - ty2)
            + (zz(i0, j0 + 1) * (1 - tx2) + zz(i0 + 1, j0 + 1) * tx2) * ty2)

tramo_m = 0
for sgn in (1, -1):
    run = []
    for i in range(N + 1):
        p = S[i % N]
        ok = p['sec'] not in ('dirt', 'bridge')
        if ok:
            half = p['w'] / 2
            tx3 = p['x'] + sgn * p['nx'] * (half + 3.5)
            ty3 = p['y'] + sgn * p['ny'] * (half + 3.5)
            ok = (p['z'] - z_terreno_b(tx3, ty3)) > 3.0
        if ok:
            run.append(i % N)
        if (not ok or i == N) and run:
            if len(run) > 6:
                mv, mf = [], []
                for idx in run:
                    q = S[idx]
                    h2 = q['w'] / 2
                    ax = q['x'] + sgn * q['nx'] * (h2 + 0.05)
                    ay = q['y'] + sgn * q['ny'] * (h2 + 0.05)
                    bx = q['x'] + sgn * q['nx'] * (h2 + 0.75)
                    by = q['y'] + sgn * q['ny'] * (h2 + 0.75)
                    zb = z_terreno_b(bx, by) - 1.5
                    mv.extend([(ax, ay, q['z'] + 0.85), (bx, by, q['z'] + 0.85),
                               (bx, by, zb)])
                for k in range(len(run) - 1):
                    o = 3 * k
                    mf.append((o, o + 1, o + 4, o + 3))       # remate
                    mf.append((o + 1, o + 2, o + 5, o + 4))   # cara exterior
                new_mesh_obj('MUROC_%d_%d' % (sgn, tramo_m), mv, mf,
                             [M_MUROC], [0] * len(mf))
                tramo_m += 1
            run = []
print('muros de contencion:', tramo_m)

# --- sol calido de tarde mediterranea ---
sun_data = bpy.data.lights.new('SOL', 'SUN')
sun_data.energy = 4.6
sun_data.color = (1.0, 0.96, 0.88)
sun_data.angle = math.radians(3.0)
sun = bpy.data.objects.new('SOL', sun_data)
sun.rotation_euler = (math.radians(34), 0, math.radians(-140))
col.objects.link(sun)
# el mapa es enorme: sin esto EEVEE agota el buffer de sombras ('Shadow buffer full')
# y deja recuadros oscuros (teselas de sombra rotas) sobre el mar
for _attr, _val in (('shadow_maximum_resolution', 0.12), ('shadow_filter_radius', 1.5)):
    try:
        setattr(sun_data, _attr, _val)
    except Exception:
        pass
try:
    bpy.context.scene.eevee.shadow_pool_size = '1024'
except Exception:
    pass

# --- cielo azul saturado estilo Cars 2 (gradiente cenit -> horizonte) ---
world = bpy.data.worlds.new('CIELO')
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes.get('Background')
tco = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
mapr = nt.nodes.new('ShaderNodeMapRange')
mapr.inputs['From Min'].default_value = -0.05
mapr.inputs['From Max'].default_value = 0.9
rampc = nt.nodes.new('ShaderNodeValToRGB')
ec = rampc.color_ramp.elements
ec[0].position = 0.0; ec[0].color = (0.70, 0.84, 0.98, 1)   # horizonte claro
ec[1].position = 1.0; ec[1].color = (0.12, 0.34, 0.86, 1)   # cenit azul intenso
em = rampc.color_ramp.elements.new(0.3)
em.color = (0.36, 0.60, 0.95, 1)
nt.links.new(tco.outputs['Generated'], sep.inputs['Vector'])
nt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
nt.links.new(mapr.outputs['Result'], rampc.inputs['Fac'])
nt.links.new(rampc.outputs['Color'], bg.inputs['Color'])
bg.inputs[1].default_value = 1.0
bpy.context.scene.world = world

# --- calidad de render (AO y transformacion de vista saturada) ---
sc0 = bpy.context.scene
sc0.view_settings.view_transform = 'Standard'
sc0.view_settings.exposure = 0.12
for attr, val in [('use_gtao', True), ('gtao_distance', 12.0),
                  ('use_shadows', True)]:
    try:
        setattr(sc0.eevee, attr, val)
    except Exception:
        pass

# --- camaras ---
def add_cam(name, loc, target, lens=35):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 10000
    cam = bpy.data.objects.new(name, cd)
    cam.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    col.objects.link(cam)
    return cam

xs = [p['x'] for p in S]; ys = [p['y'] for p in S]
cxm, cym = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
i18 = next(c['s_idx'] for c in G['curvas'] if c['n'] == 18)
p18 = S[i18 % N]
i34 = next(c['s_idx'] for c in G['curvas'] if c['n'] == 34)
p34 = S[i34 % N]

cams = [
    ('vista_aerea', (cxm - 300, cym - 1500, 1250), (cxm, cym, 30), 32),
    ('meta_puerto', (p0['x'] - 120, p0['y'] - 160, 55), (p0['x'], p0['y'], p0['z'] + 4), 40),
    ('cima_tierra', (p18['x'] - 220, p18['y'] - 260, p18['z'] + 130), (p18['x'], p18['y'], p18['z']), 45),
    ('bahia_casino', (p34['x'] - 380, p34['y'] - 320, 190), (p34['x'], p34['y'], 10), 40),
]
cam_objs = [add_cam(*c) for c in cams]

# --- render ---
sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
for cam, spec in zip(cam_objs, cams):
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT_R, spec[0] + '.png')
    bpy.ops.render.render(write_still=True)
    print('render:', spec[0])

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print('OK blend ->', OUT_BLEND)
