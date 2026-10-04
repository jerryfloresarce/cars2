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
G = json.load(open(os.environ.get('GEOM', BASE + r'\03_blender\geometria_3d.json'), encoding='utf-8'))
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
    # RONDA 15: ademas de la pendiente, la mascara de roca del macizo (atributo 'roca',
    # umbral nitido 0.45-0.52 como sugiere terreno_montana.py)
    atr = nt.nodes.new('ShaderNodeAttribute')
    atr.attribute_name = 'roca'
    umb = nt.nodes.new('ShaderNodeMapRange')
    umb.clamp = True
    umb.interpolation_type = 'SMOOTHSTEP'
    umb.inputs['From Min'].default_value = 0.45
    umb.inputs['From Max'].default_value = 0.52
    nt.links.new(atr.outputs['Fac'], umb.inputs['Value'])
    mx_r = nt.nodes.new('ShaderNodeMath')
    mx_r.operation = 'MAXIMUM'
    nt.links.new(talud.outputs['Result'], mx_r.inputs[0])
    nt.links.new(umb.outputs['Result'], mx_r.inputs[1])
    nt.links.new(mx_r.outputs['Value'], mixr.inputs['Factor'])
    nt.links.new(mixm.outputs[2], mixr.inputs[6])
    mixr.inputs[7].default_value = (0.25, 0.23, 0.19, 1)   # lineal: gris caliza medio en pantalla
    nt.links.new(mixr.outputs[2], bsdf.inputs['Base Color'])
    m.diffuse_color = (0.32, 0.45, 0.2, 1)
    _roca_terreno(nt, bsdf, geo, sepn, texm, suma, talud, atr, umb, mx_r, mixr)
    return m

def _roca_terreno(nt, bsdf, geo, sepn, texm, suma, talud, atr, umb, mx_r, mixr):
    """v2 pista (E2-11/C2-13): la roca del terreno se leia como NIEBLA gris (queja 7 del usuario,
    'montana borrosa'): color plano sin textura, mascara blanda (normales suaves en triangulos de
    4 m y atributo desenfocado) y la hierba de aplicar_texturas pintada encima (TEX_llano 0.60-0.78).
    (1) Bordes nitidos e irregulares: talud 0.50-0.56 (antes 0.40-0.58, +-0.04 de ruido de ~2.5 m)
        y atributo 0.47-0.51 (antes 0.45-0.52, +-0.33 de ruido de ~2.5 y ~11 m): borde natural, no
        el contorno poligonal de la rejilla de 4 m.
    (2) En lo llano manda la hierba aunque el atributo diga roca (umb x (1 - smoothstep(nz,0.78,0.86))).
    (3) Caliza calida (tono de los penones, MAT_PPUEBLO_roca) con manchas suaves de ~20 m, juntas de
        estrato finas y onduladas cada ~2.6 m (oscuras y talladas con bump), meteorizacion de ~7 m y
        grano de ~2 m; llega a mixr.inputs[7] (la rama de roca).
    (4) La roca es un BSDF PROPIO mezclado por la mascara (Mix Shader): aplicar_texturas multiplica
        la hierba sobre el Base Color del PRIMER Principled (el de la hierba), asi que ya no puede
        velar la roca. El primer Principled, su Base Color y diffuse_color no cambian (kn5 igual).
    Todos los nodos nuevos se crean DESPUES de mx_r: 'Math.002' sigue siendo la mascara de roca
    (max(talud, atributo)) que usan los revisores y aplicar_texturas."""
    nodes, links = nt.nodes, nt.links
    mx_r.label = 'ROCA_mascara'
    talud.inputs['From Min'].default_value = 0.50
    talud.inputs['From Max'].default_value = 0.56
    umb.inputs['From Min'].default_value = 0.47
    umb.inputs['From Max'].default_value = 0.51
    # ruido fino (~2.5 m) y grueso (~11 m) para que el limite no siga las aristas de la rejilla
    nf = nodes.new('ShaderNodeTexNoise')
    nf.name = 'ROCA_ruido_borde'
    nf.inputs['Scale'].default_value = 0.4
    nf.inputs['Detail'].default_value = 3.0
    links.new(texm.outputs['Object'], nf.inputs['Vector'])
    ng_ = nodes.new('ShaderNodeTexNoise')
    ng_.name = 'ROCA_ruido_borde_grueso'
    ng_.inputs['Scale'].default_value = 0.09
    ng_.inputs['Detail'].default_value = 2.0
    links.new(texm.outputs['Object'], ng_.inputs['Vector'])
    def _madd(entrada, k, c, nombre):
        n_ = nodes.new('ShaderNodeMath')
        n_.name = nombre
        n_.operation = 'MULTIPLY_ADD'
        n_.inputs[1].default_value = k
        n_.inputs[2].default_value = c
        links.new(entrada, n_.inputs[0])
        return n_
    def _suma(a, b, nombre, op='ADD'):
        n_ = nodes.new('ShaderNodeMath')
        n_.name = nombre
        n_.operation = op
        links.new(a, n_.inputs[0])
        links.new(b, n_.inputs[1])
        return n_
    r_t = _madd(nf.outputs['Fac'], 0.08, -0.04, 'ROCA_ruido_talud')         # +-0.04 sobre nz
    s_t = _suma(suma.outputs['Value'], r_t.outputs['Value'], 'ROCA_nz_ruido')
    links.new(s_t.outputs['Value'], talud.inputs['Value'])
    r_a = _madd(nf.outputs['Fac'], 0.30, -0.15, 'ROCA_ruido_atributo')     # +-0.15 fino ...
    r_g = _madd(ng_.outputs['Fac'], 0.36, -0.18, 'ROCA_ruido_atributo_grueso')   # ... +-0.18 grueso
    r_ag = _suma(r_a.outputs['Value'], r_g.outputs['Value'], 'ROCA_ruido_atributo_total')
    s_a = _suma(atr.outputs['Fac'], r_ag.outputs['Value'], 'ROCA_atributo_ruido')
    links.new(s_a.outputs['Value'], umb.inputs['Value'])
    llano = nodes.new('ShaderNodeMapRange')
    llano.name = 'ROCA_llano_hierba'
    llano.clamp = True
    llano.interpolation_type = 'SMOOTHSTEP'
    llano.inputs['From Min'].default_value = 0.78
    llano.inputs['From Max'].default_value = 0.86
    llano.inputs['To Min'].default_value = 1.0
    llano.inputs['To Max'].default_value = 0.0
    links.new(sepn.outputs['Z'], llano.inputs['Value'])
    u_l = _suma(umb.outputs['Result'], llano.outputs['Result'], 'ROCA_atributo_sin_llano', 'MULTIPLY')
    links.new(u_l.outputs['Value'], mx_r.inputs[1])
    # caliza: manchas grandes + estratos + grano
    n1 = nodes.new('ShaderNodeTexNoise')
    n1.name = 'ROCA_ruido_manchas'
    n1.inputs['Scale'].default_value = 0.045
    n1.inputs['Detail'].default_value = 6.0
    n1.inputs['Roughness'].default_value = 0.6
    links.new(texm.outputs['Object'], n1.inputs['Vector'])
    rr = nodes.new('ShaderNodeValToRGB')
    rr.name = 'ROCA_rampa'
    er = rr.color_ramp.elements
    er[0].position = 0.30; er[0].color = (0.30, 0.235, 0.15, 1)     # caliza en sombra (calida)
    er[1].position = 0.72; er[1].color = (0.46, 0.37, 0.245, 1)     # caliza clara (tono de los penones)
    links.new(n1.outputs['Fac'], rr.inputs['Fac'])
    # estratos: JUNTAS finas y oscuras cada ~2.6 m (ondas con distorsion: no bandas regulares de cebra)
    wv = nodes.new('ShaderNodeTexWave')
    wv.name = 'ROCA_estratos'
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = 0.12          # periodo 0.314/0.12 = 2.6 m en z
    wv.inputs['Distortion'].default_value = 6.0
    wv.inputs['Detail'].default_value = 4.0
    wv.inputs['Detail Scale'].default_value = 0.5
    if 'Detail Roughness' in wv.inputs:
        wv.inputs['Detail Roughness'].default_value = 0.6
    links.new(texm.outputs['Object'], wv.inputs['Vector'])
    ne = nodes.new('ShaderNodeMapRange')
    ne.name = 'ROCA_estratos_tono'
    ne.clamp = True
    ne.inputs['From Min'].default_value = 0.0
    ne.inputs['From Max'].default_value = 0.07
    ne.inputs['To Min'].default_value = 0.70         # junta (fondo de la onda): 30 % mas oscura
    ne.inputs['To Max'].default_value = 1.0
    links.new(wv.outputs['Fac'], ne.inputs['Value'])
    n2 = nodes.new('ShaderNodeTexNoise')
    n2.name = 'ROCA_ruido_grano'
    n2.inputs['Scale'].default_value = 0.5
    n2.inputs['Detail'].default_value = 8.0
    n2.inputs['Roughness'].default_value = 0.65
    links.new(texm.outputs['Object'], n2.inputs['Vector'])
    ng = nodes.new('ShaderNodeMapRange')
    ng.name = 'ROCA_grano_tono'
    ng.clamp = True
    ng.inputs['From Min'].default_value = 0.3
    ng.inputs['From Max'].default_value = 0.7
    ng.inputs['To Min'].default_value = 0.90
    ng.inputs['To Max'].default_value = 1.05
    links.new(n2.outputs['Fac'], ng.inputs['Value'])
    # manchas de meteorizacion (~7 m): zonas algo mas oscuras, nada de bandas regulares
    n3 = nodes.new('ShaderNodeTexNoise')
    n3.name = 'ROCA_ruido_meteo'
    n3.inputs['Scale'].default_value = 0.15
    n3.inputs['Detail'].default_value = 4.0
    links.new(texm.outputs['Object'], n3.inputs['Vector'])
    nm3 = nodes.new('ShaderNodeMapRange')
    nm3.name = 'ROCA_meteo_tono'
    nm3.clamp = True
    nm3.inputs['From Min'].default_value = 0.40
    nm3.inputs['From Max'].default_value = 0.65
    nm3.inputs['To Min'].default_value = 0.86
    nm3.inputs['To Max'].default_value = 1.0
    links.new(n3.outputs['Fac'], nm3.inputs['Value'])
    tono0 = _suma(ne.outputs['Result'], ng.outputs['Result'], 'ROCA_tono_a', 'MULTIPLY')
    tono = _suma(tono0.outputs['Value'], nm3.outputs['Result'], 'ROCA_tono', 'MULTIPLY')
    mc = nodes.new('ShaderNodeMix')
    mc.name = 'ROCA_color'
    mc.data_type = 'RGBA'
    mc.blend_type = 'MULTIPLY'
    mc.inputs['Factor'].default_value = 1.0
    links.new(rr.outputs['Color'], mc.inputs[6])
    links.new(tono.outputs['Value'], mc.inputs[7])
    links.new(mc.outputs[2], mixr.inputs[7])
    # relieve de la roca: juntas talladas (surco) + grano
    alt = _madd(ne.outputs['Result'], 1.5, 0.0, 'ROCA_altura_juntas')
    alt = _suma(alt.outputs['Value'], n2.outputs['Fac'], 'ROCA_altura')
    bmp = nodes.new('ShaderNodeBump')
    bmp.name = 'ROCA_bump'
    bmp.inputs['Strength'].default_value = 0.40
    if 'Distance' in bmp.inputs:
        bmp.inputs['Distance'].default_value = 0.5
    links.new(alt.outputs['Value'], bmp.inputs['Height'])
    # BSDF propio de la roca (su color = salida de mixr: la rama de roca sin el velo de hierba)
    br = nodes.new('ShaderNodeBsdfPrincipled')
    br.name = 'ROCA_bsdf'
    br.inputs['Roughness'].default_value = 0.92
    links.new(mixr.outputs[2], br.inputs['Base Color'])
    links.new(bmp.outputs['Normal'], br.inputs['Normal'])
    out = next((n_ for n_ in nodes if n_.type == 'OUTPUT_MATERIAL'), None)
    if out is not None:
        ms = nodes.new('ShaderNodeMixShader')
        ms.name = 'ROCA_mezcla'
        links.new(mx_r.outputs['Value'], ms.inputs[0])          # factor (0 = hierba, 1 = roca)
        links.new(bsdf.outputs['BSDF'], ms.inputs[1])
        links.new(br.outputs['BSDF'], ms.inputs[2])
        links.new(ms.outputs['Shader'], out.inputs['Surface'])

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

def _mp(i):
    """Muestra i (indice) o muestra ya interpolada (dict de muestra_s: extremos de las aceras en las bocas, v3 B4)."""
    return i if isinstance(i, dict) else S[i % N]

def punto_lateral(i, lateral, dz):
    p = _mp(i)
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

# --- v3 pista (B4): bocas de los enlaces del plan urbano (urbanismo.json) ---
# (s, lado, semiancho del corte, u de la boca, z de la boca). pts[3] es la boca (u ~0.4 del borde, z_borde + 0.03) y
# pts[2] el final del tramo perpendicular (u 1.5, cota de la calle). La acera (alta o baja) pasaba ENTERA por delante:
# en las 22 bocas quedaba ACERA_ 0.3-1.2 m por encima de CAMINO_enlace (sectores que suben: enlace a +0.1..+0.4 bajo la
# acera a +0.5; que bajan: a -0.04..-0.9 bajo ella), donde no hay acera el ARCEN llano (1.8 m) tapaba el enlace que
# baja y en el casino el guardarrail cerraba las 7 bocas. Ahora en el ancho de cada boca no hay acera, bordillo ni
# rail (la valla CERRADO de urbanismo_escena, a 3.5 m, cierra el enlace) y el arcen se mete bajo el enlace.
_BOCAS = []
MARGEN_BOCA = 0.35        # mas alla del ancho del enlace (sus bordes caen a +-ancho/2: medido en la escena)
RAMPA_BOCA = 1.0          # la acera alta baja de +0.5 a +0.06 en >= 1 m hasta el canto de la boca (vado)
def _s_lat(x, y):
    ib = min(range(N), key=lambda i: (S[i]['x'] - x) ** 2 + (S[i]['y'] - y) ** 2)
    p = S[ib]
    t = (x - p['x']) * p['ny'] - (y - p['y']) * p['nx']
    l_ = (x - p['x']) * p['nx'] + (y - p['y']) * p['ny']
    return ib * G['paso_m'] + max(-G['paso_m'], min(G['paso_m'], t)), l_, p['w'] / 2.0
try:
    for sec_ in json.load(open(os.environ.get('URBANISMO', BASE + r'\03_blender\urbanismo.json'),
                               encoding='utf-8')).get('sectores', []):
        for e_ in sec_.get('enlaces', []):
            pts_ = e_.get('pts') or []
            if len(pts_) < 4:
                continue
            sb_, lb_, hb_ = _s_lat(pts_[3][0], pts_[3][1])
            _BOCAS.append((sb_, 1 if lb_ > 0 else -1, float(e_.get('ancho', 4.5)) / 2.0 + MARGEN_BOCA,
                           max(0.0, abs(lb_) - hb_), float(pts_[3][2])))
except Exception as _e:
    print('sin urbanismo.json: sin bocas de enlaces (aceras y rails continuos):', _e)
print('bocas de enlaces (acera, bordillo y rail cortados; arcen bajo el enlace):',
      [(round(b_[0], 1), b_[1]) for b_ in _BOCAS])
def _boca_en(s_, sgn, extra=0.0):
    for b_ in _BOCAS:
        if b_[1] == sgn and abs(s_ - b_[0]) <= b_[2] + extra:
            return b_
    return None

def _tramos_sin_bocas(s0, s1, sgn, minimo=4.0):
    """[(a, b)] de [s0, s1] sin el ancho de las bocas del lado sgn; descarta los trozos < minimo."""
    out, lo = [], s0
    for (c0, c1) in sorted((b_[0] - b_[2], b_[0] + b_[2]) for b_ in _BOCAS if b_[1] == sgn):
        if c1 <= lo or c0 >= s1:
            continue
        if c0 - lo >= minimo:
            out.append((lo, c0))
        lo = max(lo, c1)
    if s1 - lo >= minimo:
        out.append((lo, s1))
    return out

# --- GUARDARRAIL de acero (Armco) a ambos lados en el sector del casino ---
M_GR = mat('MAT_guardarrail', (0.30, 0.26, 0.20, 1), 0.45, 0.7)
def _guardarrail(s0, s1, sgn, nombre, poste_fin=False, sin_postes_extremos=False):
    """poste_fin: poste tambien en s1 (si no cae en la serie de 4 m); sin_postes_extremos: sin los
    postes de s0 y s1 (tramo que empalma con otros dos que ya los ponen)."""
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
    ks_p = list(range(0, n_ + 1, 2))
    if poste_fin and ks_p[-1] != n_:
        ks_p.append(n_)
    if sin_postes_extremos:
        ks_p = [k for k in ks_p if 0 < k < n_]
    for k in ks_p:
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
        # v1 pista (H1): el rail entra 1 m en el primer tramo de balaustrada del viaducto (s 3632):
        # antes acababa 2 m antes y quedaba un hueco entre la barrera y el pretil
        _fin = min(_bi) * G['paso_m'] + 1.0
        # v3 pista (B4): el rail del casino se abre en las 7 bocas de los enlaces de casino_ladera / casino_mar
        # (_tramos_sin_bocas): el primer trozo conserva el nombre y los siguientes llevan _2, _3...
        if sgn == _in_gr:
            # por el interior de la horquilla el rail se amontonaba en el apice: alli
            # ya esta el murete de la isleta
            _tr_gr = [(a_, b_, '_a', S_LOEWS - 30.0) for (a_, b_) in _tramos_sin_bocas(S_CAS0 + 20.0, S_LOEWS - 30.0, sgn)]
            if _fin - (S_LOEWS + 30.0) > 8.0:
                _tr_gr += [(a_, b_, '_b', _fin) for (a_, b_) in _tramos_sin_bocas(S_LOEWS + 30.0, _fin, sgn)]
        else:
            _tr_gr = [(a_, b_, '', _fin) for (a_, b_) in _tramos_sin_bocas(S_CAS0 + 20.0, _fin, sgn)]
        _n_gr = {}
        for (a_, b_, suf_, fin_) in _tr_gr:
            _n_gr[suf_] = _n_gr.get(suf_, 0) + 1
            _guardarrail(a_, b_, sgn, 'GUARDARRAIL_%s%s%s' % ('IZQ' if sgn > 0 else 'DER', suf_,
                                                             '' if _n_gr[suf_] == 1 else '_%d' % _n_gr[suf_]),
                         poste_fin=(b_ < fin_ - 1e-6))       # poste en el canto de cada boca
# v1 pista (B6, F-03): barrera tambien donde la calzada va en alto sobre el mar sin acera ni muro
# (lado +1 = mar): la subida al tunel (tras el muro+valla de meta, que acaba en s 174) y la
# salida del tunel hasta la acera del pueblo (s 620, alli sigue el pretil de piedra de abajo);
# y en el lado -1 delante del paseo-mirador (antes solo un bordillo de 0.16 m y coches a 5 m).
# v3 pista (B6): sin hueco antes y despues del tunel: la subida llega hasta el portal de entrada (s 402, cara del
# arco en 402.2-405.7) por la explanada de B8 (s 335-402, cornisa al mar a 35 m) y la horquilla arranca en el portal
# de salida (arco en 538.4-541.6) en vez de en s 560. Ninguno entra en el arco ni en la galeria.
for (_s0g, _s1g, _sgg, _nomg) in ((170.0, 402.0, 1, 'GUARDARRAIL_IZQ_subida'),
                                   (542.0, 620.0, 1, 'GUARDARRAIL_IZQ_horquilla')):
    _guardarrail(_s0g, _s1g, _sgg, _nomg)
# v2 pista (F2-05): el rail del mirador cerraba TODO el frente del paseo (sin entrada desde fuera,
# con 21 coches dentro). Se parte en tres piezas que empalman sin junta: _a (2984-2990, con poste en
# 2990), _boca (2990-2998, solo el poste central) y el resto (2998-3156). Mientras el integrador no
# ponga la boca del paseo, la barrera sigue continua (sin regresion); al ponerla (valla CERRADO a 2 m
# del borde en s 2990-2998, como las bocas de las calles) BORRA 'GUARDARRAIL_DER_mirador_boca'.
# v3 pista (F-03): el integrador no lo hizo nunca (el paseo y sus 20 coches seguian sin entrada). La boca la pone
# ahora construir_pista: hueco de 8 m entre los postes de s 2990 y 2998 (sin pieza _boca), VALLA CERRADO de
# caminos_kit a 2 m del borde sobre el pavimento del paseo (cota del borde + 0.10 = la de integrar.zona_paseo_mirador,
# que arranca a ras del borde en s0 = 2990 con un bordillo de 0.16 m: sin rampa; asentar la deja sobre MIRADOR_paseo)
# y cartel BELVEDERE / PARCHEGGIO en la berma antes de la boca. Si el kit falla o no hay mirador en s0 = 2990, el
# rail sigue continuo como en la v2 (sin regresion). N1: el rail _a arranca en s 2970 delante del final del pretil
# de la recta (MUROC_pretil_recta_mar, hasta s 2976): barrera continua desde la curva 30.
def _boca_mirador(s_b, side):
    """Valla de cierre + cartel en la boca del paseo-mirador. True si los ha puesto."""
    try:
        import sys as _sys
        _ad = BASE + r'\03_blender\assets'
        if _ad not in _sys.path:
            _sys.path.insert(0, _ad)
        import caminos_kit as _ck
        q = muestra_s(s_b)
        half = q['w'] / 2.0
        ze = q['z'] - q['lat'] * side * half
        l_ = side * (half + 2.0)
        v = _ck.build_valla_cierre(col, ancho=6.0, seed=29)
        v.location = (q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, ze + 0.10)
        v.rotation_euler = (0.0, 0.0, math.atan2(side * q['ny'], side * q['nx']) - math.pi / 2)   # +Y = hacia el paseo
        v.name = 'CAMINO_valla_mirador'
        try:
            qc = muestra_s(s_b - 7.0)
            hc = qc['w'] / 2.0
            lc = side * (hc + 1.6)
            c = _ck.build_cartel(col, texto=['BELVEDERE', 'PARCHEGGIO'], seed=31, flecha=side)   # flecha hacia la boca
            c.location = (qc['x'] + qc['nx'] * lc, qc['y'] + qc['ny'] * lc, qc['z'] - qc['lat'] * side * hc - 0.05)
            c.rotation_euler = (0.0, 0.0, math.atan2(-side * qc['ny'], -side * qc['nx']) - math.pi / 2)  # se lee desde la pista
            c.name = 'CAMINO_cartel_mirador'
        except Exception as e_:
            print('boca del mirador: cartel fallo (%s)' % e_)
        return True
    except Exception as e_:
        print('boca del mirador: valla fallo (%s): el rail sigue continuo' % e_)
        return False

_MIR_F03 = next((m_ for m_ in (G.get('miradores') or [])
                 if int(m_['side']) == -1 and abs(float(m_['s0']) - 2990.0) < 1.0), None)
_guardarrail(2970.0, 2990.0, -1, 'GUARDARRAIL_DER_mirador_a', poste_fin=True)
if _MIR_F03 is None or not _boca_mirador(2994.0, -1):
    _guardarrail(2990.0, 2998.0, -1, 'GUARDARRAIL_DER_mirador_boca', sin_postes_extremos=True)
else:
    print('boca del paseo-mirador abierta en s 2990-2998 (valla CERRADO a 2 m y cartel)')
_guardarrail(2998.0, 3156.0, -1, 'GUARDARRAIL_DER_mirador')

# --- aceras con bordillo en los tramos urbanos ---
M_ACERA = mat('MAT_acera_piedra', (0.34, 0.31, 0.27, 1), 0.95)   # gris piedra: en blanco puro se clipaba
M_BORDILLO = mat('MAT_bordillo_piedra', (0.40, 0.37, 0.33, 1), 0.9)
# v1 pista (D11): el tramo alto empieza en el primer enlace/casa (s 1284), no en el prado de 1260
TRAMOS_URBANOS = [(620, 1100), (1284, 1560), (2480, 2760), (4560, 4930)]
# RONDA 15: en los sectores de terrazas del plan urbano (urbanismo_spec.json) junto a la
# pista va un BORDILLO ALTO (+0.5 m, franja 0.06..1.5) y encima arranca la calle de
# servicio del plan; fuera de ellos sigue la acera baja de siempre
_SPEC_U = {}
try:
    _SPEC_U = json.load(open(BASE + r'\03_blender\urbanismo_spec.json', encoding='utf-8'))
except Exception as _e:
    print('sin urbanismo_spec.json:', _e)
_SECT_U = [(float(s_['s0']), float(s_['s1']), int(s_['lado'])) for s_ in _SPEC_U.get('sectores', [])]
_BORD_U = float(_SPEC_U.get('bordillo_hasta', 1.5))
def _en_terraza(i, sgn):
    s_ = i * G['paso_m']
    return any(a_ <= s_ <= b_ and sgn == l_ for (a_, b_, l_) in _SECT_U)
for (a_, b_, l_) in _SECT_U:
    if not any(a0 <= a_ and b_ <= b0 for (a0, b0) in TRAMOS_URBANOS):
        # v1 pista (F-13): sin el margen de +-10 m, que dejaba retales de acera baja de 10 m
        # (s 3185-3195 y 3445-3455) con un escalon de 0.44 m contra la acera alta
        TRAMOS_URBANOS.append((int(a_), int(b_)))

# v2 pista (D2-10): por la TIERRA la acera alta solo sigue en los sectores que SUBEN (calle de servicio a
# +0.5, la misma regla que urbanismo.sentido_terrazas) y solo entre las bocas de sus enlaces (urbanismo.json):
# en los que bajan la calle va a Z-0.5 (la acera quedaria 1 m por encima) y mas alla del ultimo enlace
# acabaria en el prado (en pueblo_alto_ladera la calle acaba en s 1504 y el sector en 1525).
def _sube_u(sec_):
    sen_ = str(sec_.get('sentido', '')).strip().lower()
    if sen_ in ('sube', 'baja'):
        return sen_ == 'sube'
    if 'sube' in sec_:
        return bool(sec_['sube'])
    return not str(sec_['id']).endswith('_mar')

def _s_cerca(x, y):
    ib = min(range(N), key=lambda i: (S[i]['x'] - x) ** 2 + (S[i]['y'] - y) ** 2)
    p = S[ib]
    t = (x - p['x']) * p['ny'] - (y - p['y']) * p['nx']      # tangente de la marcha = (ny, -nx)
    return ib * G['paso_m'] + max(-G['paso_m'], min(G['paso_m'], t))

_URB_ENL = {}
try:
    for sec_ in json.load(open(os.environ.get('URBANISMO', BASE + r'\03_blender\urbanismo.json'),
                               encoding='utf-8')).get('sectores', []):
        ss_ = [(_s_cerca(q_[0], q_[1]), float(e_.get('ancho', 4.5)))
               for e_ in sec_.get('enlaces', []) for q_ in e_.get('pts', [])]
        if ss_:
            _URB_ENL[str(sec_['id'])] = (min(s_ - a_ / 2 - 1.0 for s_, a_ in ss_), max(s_ + a_ / 2 + 1.0 for s_, a_ in ss_))
except Exception as _e:
    print('sin urbanismo.json (la acera alta sigue por la tierra en todo el sector que sube):', _e)
_TIERRA_U = []
for s_ in _SPEC_U.get('sectores', []):
    if _sube_u(s_):
        a_, b_ = _URB_ENL.get(str(s_['id']), (float(s_['s0']), float(s_['s1'])))
        _TIERRA_U.append((max(a_, float(s_['s0'])), min(b_, float(s_['s1'])), int(s_['lado'])))
print('acera alta por la tierra en:', [(round(a_, 1), round(b_, 1), l_) for (a_, b_, l_) in _TIERRA_U])
def _acera_en_tierra(i, sgn):
    s_ = i * G['paso_m']
    return any(a_ <= s_ <= b_ and sgn == l_ for (a_, b_, l_) in _TIERRA_U)

def _faja_vertical(idxs, lateral, z0_rel, z1_rel, material, name):
    """Cara vertical (bordillo alto) a `lateral` del eje, entre z+z0_rel y z+z1_rel
    (z1_rel puede ser una funcion (k) -> cota relativa, para las rampas de los extremos)."""
    vs, fs = [], []
    for k, i2 in enumerate(idxs):
        p = _mp(i2)
        lat = lateral(k, i2)
        x_ = p['x'] + p['nx'] * lat
        y_ = p['y'] + p['ny'] * lat
        zb = p['z'] - p['lat'] * lat
        vs.append((x_, y_, zb + z0_rel))
        vs.append((x_, y_, zb + (z1_rel(k) if callable(z1_rel) else z1_rel)))
    for k in range(len(idxs) - 1):
        o = 2 * k
        fs.append((o, o + 2, o + 3, o + 1))
        fs.append((o + 1, o + 3, o + 2, o))   # doble cara: se ve desde la pista y desde la calle
    if fs:
        new_mesh_obj(name, vs, fs, [material], [0] * len(fs))

def _cinta_dz(indices, lateral_fn, width, dz_fn, material, name):
    """Como ribbon() pero con altura dz_fn(k) por muestra (rampas en los extremos)."""
    vs, fs = [], []
    for k, i2 in enumerate(indices):
        lat_c = lateral_fn(k, i2)
        vs.append(punto_lateral(i2, lat_c - width / 2, dz_fn(k)))
        vs.append(punto_lateral(i2, lat_c + width / 2, dz_fn(k)))
    for k in range(len(indices) - 1):
        o = 2 * k
        fs.append((o, o + 1, o + 3, o + 2))
    if fs:
        new_mesh_obj(name, vs, fs, [material], [0] * len(fs))

ACERA_ALTA_MIN = 8.0      # v3 (B4): un trozo de acera alta mas corto (entre una boca y el final) va entero a +0.06
ACERA_BAJA_MIN = 6.0      # y uno de acera baja mas corto no se pone (retal, como en F-13)
def _s_de(p):
    return p['s'] if isinstance(p, dict) else p * G['paso_m']

def _partir_bocas(idxs, sgn, alta):
    """v3 pista (B4): trozos de una acera sin las bocas de los enlaces (_BOCAS). Cada trozo es una lista de puntos:
    indices de muestra o muestras interpoladas (dict) justo en el canto de la boca. En la acera alta se quitan las
    muestras a < RAMPA_BOCA del canto (rampa de +0.5 a +0.06 de >= 1 m); en ninguna queda un tramo < 0.3 m."""
    paso = G['paso_m']
    s_a, s_b = idxs[0] * paso, idxs[-1] * paso
    cortes = sorted((b_[0] - b_[2], b_[0] + b_[2]) for b_ in _BOCAS
                    if b_[1] == sgn and b_[0] + b_[2] > s_a and b_[0] - b_[2] < s_b)
    if not cortes:
        return [list(idxs)]
    libres, lo, lo_c = [], s_a, False
    for (c0, c1) in cortes:
        if c0 > lo:
            libres.append((lo, lo_c, c0, True))
        if c1 > lo:
            lo, lo_c = c1, True
    if lo < s_b:
        libres.append((lo, lo_c, s_b, False))
    hueco = max(RAMPA_BOCA if alta else 0.0, 0.3)
    out = []
    for (a_, a_c, b_, b_c) in libres:
        pts = [i for i in idxs if a_ + (hueco if a_c else 0.0) <= i * paso <= b_ - (hueco if b_c else 0.0)]
        for (s_c, cortado, pos) in ((a_, a_c, 0), (b_, b_c, None)):
            if cortado:
                q_ = muestra_s(s_c)
                q_['s'] = s_c
                if pos == 0:
                    pts.insert(0, q_)
                else:
                    pts.append(q_)
        if len(pts) >= 2 and _s_de(pts[-1]) - _s_de(pts[0]) >= 0.5:
            out.append(pts)
    return out

N_BOCAS_CORTADAS = 0
for (s0u, s1u) in TRAMOS_URBANOS:
    i0u = int(s0u / G['paso_m'])
    i1u = int(s1u / G['paso_m'])
    for sgn in (1, -1):
        # v2 pista (D2-10): en los sectores de TERRAZA que suben la acera alta sigue tambien por la tierra
        # hasta la boca del ultimo enlace (_acera_en_tierra). pueblo_alto_ladera sigue hasta s 1525 pero la
        # acera acababa en s 1428 (donde empieza la tierra): la calle de servicio quedaba sobre la franja a
        # Z-0.4 con el faldon blanco del kit a la vista y rendijas bajo ella. Fuera de eso, sin acera en tierra.
        idxs_all = [i for i in range(i0u, i1u)
                    if S[i]['sec'] != 'bridge' and (S[i]['sec'] != 'dirt' or _acera_en_tierra(i, sgn))]
        trozos = []      # trozos consecutivos de un mismo tipo (terraza / urbano normal)
        for i in idxs_all:
            t_ = _en_terraza(i, sgn)
            if trozos and trozos[-1][0] == t_ and i == trozos[-1][1][-1] + 1:
                trozos[-1][1].append(i)
            else:
                trozos.append((t_, [i]))
        def _pegado_a_terraza(n_t):
            a_i, b_i = trozos[n_t][1][0], trozos[n_t][1][-1]
            return ((n_t > 0 and trozos[n_t - 1][0] and trozos[n_t - 1][1][-1] + 1 == a_i)
                    or (n_t + 1 < len(trozos) and trozos[n_t + 1][0] and trozos[n_t + 1][1][0] == b_i + 1))
        for n_t, (t_, idxs_u) in enumerate(trozos):
            # v1 pista (F-13/D11): nada de retales (< 12 m) ni de acera baja corta (<= 24 m)
            # pegada a una terraza: era acera en el prado, sin casas, acabando en la hierba
            if len(idxs_u) < 6 or (not t_ and len(idxs_u) < 13 and _pegado_a_terraza(n_t)):
                continue
            # v3 pista (B4): la acera se corta en el ancho de cada boca de enlace (+-ancho/2 + MARGEN_BOCA): el
            # primer trozo conserva el nombre de siempre y los siguientes llevan sufijo b, c...
            partes_u = _partir_bocas(idxs_u, sgn, t_)
            if len(partes_u) != 1 or len(partes_u[0]) != len(idxs_u):
                N_BOCAS_CORTADAS += 1
            for j_p, pts_u in enumerate(partes_u):
                suf = '' if j_p == 0 else chr(ord('a') + j_p)
                largo_p = _s_de(pts_u[-1]) - _s_de(pts_u[0])
                if t_:
                    # v1 pista (D11): los extremos de la acera alta bajan en rampa (2 m) a la cota de
                    # la acera baja en vez de acabar en un bloque cortado de 0.5 m (v3: tambien en el canto
                    # de cada boca, rampa >= 1 m = vado; un trozo < ACERA_ALTA_MIN va entero a +0.06)
                    _nk = len(pts_u)
                    _alto = 0.50 if largo_p >= ACERA_ALTA_MIN else 0.06
                    _dzf = lambda k, n_=_nk, a_=_alto: 0.06 if k in (0, n_ - 1) else a_
                    _cinta_dz(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 0.06 + _BORD_U / 2),
                              _BORD_U - 0.12, _dzf, M_ACERA, 'ACERA_%d_%d_%d%s' % (s0u, sgn, n_t, suf))
                    _faja_vertical(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 0.06), -0.05, _dzf, M_BORDILLO,
                                   'BORDILLO_%d_%d_%d%s' % (s0u, sgn, n_t, suf))
                else:
                    if j_p > 0 or len(partes_u) > 1:
                        if largo_p < ACERA_BAJA_MIN:
                            continue
                    ribbon(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 1.35),
                           2.3, M_ACERA, dz=0.055, name='ACERA_%d_%d_%d%s' % (s0u, sgn, n_t, suf))
                    ribbon(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 0.12),
                           0.24, M_BORDILLO, dz=0.07, name='BORDILLO_%d_%d_%d%s' % (s0u, sgn, n_t, suf))
                    # v1 pista (F-13): cantos de la acera baja: el exterior baja 0.35 m (no queda al
                    # aire sobre el talud del arcen) y el frente cierra la rendija bajo el bordillo
                    _faja_vertical(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 2.5), -0.30, 0.055, M_BORDILLO,
                                   'ACERA_%d_%d_%d%s_canto' % (s0u, sgn, n_t, suf))
                    _faja_vertical(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 0.005), -0.03, 0.07, M_BORDILLO,
                                   'BORDILLO_%d_%d_%d%s_frente' % (s0u, sgn, n_t, suf))
print('aceras cortadas en las bocas de los enlaces (v3 B4): %d trozos' % N_BOCAS_CORTADAS)

# --- RONDA 15 (v1 pista, A-04/A-05/F-14): datos del PIT LANE por fila, ANTES de los arcenes.
# Antes la cinta del pit iba plana a la cota del EJE de la pista: en la entrada quedaba
# 0.06-0.24 m bajo el asfalto peraltado (y tapada por el ARCEN_DER, hierba con fisica en AC)
# y en la salida 0.3 m POR ENCIMA del asfalto (repisa). Ahora, en las bifurcaciones, la cinta
# sigue el plano de la calzada (prolongado llano fuera del borde) y funde a su cota propia en
# 30 m; dentro del asfalto va siempre 1.2 cm por debajo (la pista manda en render y fisica). ---
PIT = G.get('pit_lane') or []
L_PISTA = N * G['paso_m']
NL_PIT = 7            # vertices por fila: la seccion sigue el quiebro del borde del asfalto
PITD = []
_PIT_K0 = int(0.18 * (len(PIT) - 1)) if PIT else 0   # tramo a ancho completo = integrar.zona_pit
_PIT_K1 = int(0.82 * (len(PIT) - 1)) if PIT else 0

def _smooth01(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)

def _s_proy(x, y):
    """Abscisa s (m) de la proyeccion de (x, y) sobre el eje de la pista."""
    ib = min(range(N), key=lambda i: (S[i]['x'] - x) ** 2 + (S[i]['y'] - y) ** 2)
    p = S[ib]
    t = (x - p['x']) * p['ny'] - (y - p['y']) * p['nx']      # tangente de la marcha = (ny, -nx)
    return (ib * G['paso_m'] + max(-G['paso_m'], min(G['paso_m'], t))) % L_PISTA

def _z_pit(d, x, y):
    """Cota de la superficie del pit lane en (x, y) para la fila d."""
    m = d['m']
    l = (x - m['x']) * m['nx'] + (y - m['y']) * m['ny']
    half = d['half']
    z_t = m['z'] - m['lat'] * max(-half, min(half, l))      # plano de la calzada, llano fuera
    z = d['peso'] * z_t + (1.0 - d['peso']) * d['zp']
    if abs(l) < half - 0.01:
        z = min(z, m['z'] - m['lat'] * l - 0.012)           # bajo el asfalto, nunca encima
    return z

if PIT:
    _cum = 0.0
    for k, q in enumerate(PIT):
        if k:
            _cum += math.hypot(q['x'] - PIT[k - 1]['x'], q['y'] - PIT[k - 1]['y'])
        s_k = _s_proy(q['x'], q['y'])
        m = muestra_s(s_k)
        hw = q['w'] / 2.0
        ln = math.hypot(q['nx'], q['ny']) or 1.0
        A = (q['x'] + q['nx'] / ln * hw, q['y'] + q['ny'] / ln * hw)    # borde +n (orden de siempre)
        B = (q['x'] - q['nx'] / ln * hw, q['y'] - q['ny'] / ln * hw)
        lA = (A[0] - m['x']) * m['nx'] + (A[1] - m['y']) * m['ny']
        lB = (B[0] - m['x']) * m['nx'] + (B[1] - m['y']) * m['ny']
        lc = (q['x'] - m['x']) * m['nx'] + (q['y'] - m['y']) * m['ny']
        PITD.append(dict(k=k, s=s_k, m=m, half=m['w'] / 2.0, cum=_cum, A=A, B=B,
                         a_int=abs(lA) < abs(lB), sgn=(1 if lc > 0 else -1),
                         d_in=min(abs(lA), abs(lB)), d_out=max(abs(lA), abs(lB)),
                         hueco=min(abs(lA), abs(lB)) - m['w'] / 2.0, zp=q['z'] - 0.015, peso=0.0))
    # peso 1 = sigue la calzada (bifurcacion), 0 = cota propia; fundido de 30 m desde donde el
    # borde interior del pit sale del asfalto (entrada) o vuelve a entrar (salida)
    _ke = PITD[0]['cum']
    for k in range(1, max(2, _PIT_K0)):
        h0, h1 = PITD[k - 1]['hueco'], PITD[k]['hueco']
        if h0 <= 0.0 < h1:
            _ke = PITD[k - 1]['cum'] + (-h0 / (h1 - h0)) * (PITD[k]['cum'] - PITD[k - 1]['cum'])
            break
    _kx = PITD[-1]['cum']
    for k in range(len(PITD) - 1, _PIT_K1, -1):
        h0, h1 = PITD[k]['hueco'], PITD[k - 1]['hueco']
        if h0 <= 0.0 < h1:
            _kx = PITD[k]['cum'] - (-h0 / (h1 - h0)) * (PITD[k]['cum'] - PITD[k - 1]['cum'])
            break
    _de = max(6.0, min(30.0, PITD[_PIT_K0]['cum'] - _ke - 3.0))
    _dx = max(6.0, min(30.0, _kx - PITD[_PIT_K1]['cum'] - 3.0))
    for d in PITD:
        if d['k'] <= _PIT_K0:
            d['peso'] = 1.0 - _smooth01((d['cum'] - _ke) / _de)
        elif d['k'] >= _PIT_K1:
            d['peso'] = 1.0 - _smooth01((_kx - d['cum']) / _dx)
        # borde interior efectivo: donde se separa del asfalto la cinta arranca pegada al borde
        # y abre una cuna en punta (sin rendijas de 0.1-0.5 m entre pista y pit lane)
        h = d['hueco']
        en_bif = d['k'] <= _PIT_K0 or d['k'] >= _PIT_K1
        d_eff = d['half'] - 0.05 + (h + 0.05) * _smooth01(h / 1.5) if (en_bif and 0.0 < h < 1.5) else d['d_in']
        d['gore'] = d_eff - d['half']
        P_in, P_out = (d['A'], d['B']) if d['a_int'] else (d['B'], d['A'])
        ux, uy = P_in[0] - P_out[0], P_in[1] - P_out[1]
        lu = math.hypot(ux, uy) or 1.0
        ux, uy = ux / lu, uy / lu
        mv = d['d_in'] - d_eff
        d['P_in'] = (P_in[0] + ux * mv, P_in[1] + uy * mv)
        d['P_out'] = P_out
        d['u_out'] = (-ux, -uy)
        d['zin'] = _z_pit(d, *d['P_in'])
        d['zout'] = _z_pit(d, *d['P_out'])
    print('pit lane: bifurcaciones en cum %.1f / %.1f m, fundido %.0f / %.0f m, peso fila 0 %.2f, ultima %.2f'
          % (_ke, _kx, _de, _dx, PITD[0]['peso'], PITD[-1]['peso']))

_PIT_S0 = PITD[0]['s'] if PITD else 0.0
def _s_unw(s_):
    return s_ if s_ >= _PIT_S0 - 1.0 else s_ + L_PISTA
_PIT_SU = [_s_unw(d['s']) for d in PITD]

def _pit_en_s(s_):
    """(k, f) fila fraccional del pit lane a la altura de la abscisa s de la pista, o None."""
    if not PITD:
        return None
    su = _s_unw(s_)
    if su < _PIT_SU[0] or su > _PIT_SU[-1]:
        return None
    for k in range(len(PITD) - 1):
        if _PIT_SU[k] <= su <= _PIT_SU[k + 1]:
            ds = _PIT_SU[k + 1] - _PIT_SU[k]
            return k, ((su - _PIT_SU[k]) / ds if ds > 1e-6 else 0.0)
    return None

def _arcen_pit(idx, sgn, half, ez):
    """(e1, e2, z_e, z_m, z_o) del arcen de la pista en las bifurcaciones del pit, o None.
    Pit pegado al borde: arcen ESCONDIDO bajo la cinta (no tapa el carril). Cuna: hierba
    desde el borde del asfalto hasta justo bajo el bordillo interior del pit lane."""
    if not PITD or sgn != PITD[0]['sgn']:
        return None
    r = _pit_en_s(idx * G['paso_m'])
    if r is None:
        return None
    k, f = r
    if not (k + f <= _PIT_K0 - 3 or k + f >= _PIT_K1 + 2):
        return None                 # tramo del muro de boxes: arcen de siempre (el muro apoya en el)
    d0, d1 = PITD[k], PITD[min(k + 1, len(PITD) - 1)]
    g = d0['gore'] * (1 - f) + d1['gore'] * f
    d_out = d0['d_out'] * (1 - f) + d1['d_out'] * f
    zin = d0['zin'] * (1 - f) + d1['zin'] * f
    if g <= 0.04:
        if d_out - half < 0.3:
            return None
        return 0.05, max(0.12, min(6.5, d_out - half - 0.3)), ez - 0.07, ez - 0.30, ez - 0.80
    if g < 6.5:
        e2 = g + 0.02               # se mete 2 cm bajo el borde del pit (8 cm mas bajo): sin rendija
        z_o = zin - 0.08
        return e2 * 0.5, e2, ez - 0.01, 0.5 * (ez - 0.01) + 0.5 * z_o - 0.01, z_o
    return None

# v1 pista (C-13): pretil de piedra del lado del mar en la tecnica del pueblo bajo, detras de la
# acera (las macetas y postes de guirnalda llegan a 3.45 m del borde): (s0, s1, lado, cara a, nombre, pie)
# v2 pista (F2-02): y en el lado -1 de la bajada (s 2440-2618), que no tenia NINGUNA barrera: terraplen de
# 0.55 y debajo el desmonte de CARRERA_tribuna.004 (17-29 m de caida sobre su tejado o la recta de meta).
# Cara a 3.70 m, detras de farolas (hasta 1.56), macetas (hasta 3.41) y postes de guirnalda (su caja llega a
# 3.63 en s 2596): ninguno lo toca. Acaba en s 2618, antes de la boca de CAMINO_enlace.012 (desde s 2619.6;
# entre 2614 y 2618 el arcen quedaba 0.4-0.5 m al aire a 4 m del borde). pie = None: cara
# exterior hasta min(ze-0.6, zt-0.4) y arcen llano
# hasta 3.75 que baja hasta 7 m (C-13, sin cambios). pie = (dz_borde, dz_terreno): cara exterior hasta
# min(ze-dz_borde, zt-dz_terreno) (el integrador rebaja el terreno al pie con el desmonte de la tribuna) y
# el arcen acaba DENTRO del pretil: detras no asoma ninguna lamina de hierba al aire (s 2570-2610).
# v3 pista (F-08): el mismo pretil en el lado +1 de la frenada (s 2440-2636; talud del 40 %, hasta -6.9 m a 20 m),
# detras de la acera baja, farolas (1.3), macetas (2.8) y postes de guirnalda (3.5): en esa banda no hay ninguna boca
# ni ramal (CAMARA_tierra.001/.002 son gruas a 16-24 m, sin camino). N1: y en el lado -1 (mar) de la recta 30-31 que
# sube al casino (s 2770-2976, terraplen de -6.8 m a 20 m), detras de las vallas CARRERA_valla_pub (u 2.6-3.35); acaba
# 6 m despues de donde arranca GUARDARRAIL_DER_mirador_a (s 2970), que sigue hasta la boca del paseo.
PRETILES = [(616.0, 820.0, 1, 3.62, 'MUROC_pretil_mar_616', None),
            (2440.0, 2618.0, -1, 3.70, 'MUROC_pretil_bajada_2440', (2.5, 1.5)),
            (2440.0, 2636.0, 1, 3.70, 'MUROC_pretil_bajada_izq_2440', (2.5, 1.5)),
            (2770.0, 2976.0, -1, 3.70, 'MUROC_pretil_recta_mar', (2.5, 1.5))]
PRETIL_GRUESO, PRETIL_ALTO = 0.40, 0.90
def _pretil_de(idx, sgn):
    s_ = idx * G['paso_m']
    for pr_ in PRETILES:
        if pr_[0] <= s_ <= pr_[1] and sgn == pr_[2]:
            return pr_
    return None
def _en_pretil(idx, sgn):
    return _pretil_de(idx, sgn) is not None

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
                    if _en_terraza(idx, sgn):
                        e1, e2 = 0.3, 0.8      # ronda 15: bajo el bordillo alto de la calle de servicio
                    if S_LOEWS:
                        dc = math.hypot(ex - _lw['x'], ey - _lw['y'])
                        if dc < 30.0:
                            hacia_c = ((_lw['x'] - ex) * sgn * p['nx'] + (_lw['y'] - ey) * sgn * p['ny']) > 0
                            if hacia_c:
                                # RONDA 13: el arcen tampoco tapa la ISLETA (su rueda de flores
                                # quedaba bajo el cesped): se queda a 0.5 m de su radio
                                e2 = max(0.4, min(6.5, dc - (_R_ISLA + 0.5)))
                                e1 = min(1.8, e2 * 0.5)
                    pr_ = _pretil_de(idx, sgn)
                    if pr_ is not None:
                        e1, e2 = 3.75, 7.0     # v1 (C-13): llano bajo la acera hasta el pie del pretil
                        if pr_[5] is not None:
                            e2 = pr_[3] + PRETIL_GRUESO - 0.05   # v2 (F2-02): acaba dentro del pretil
                    z_e, z_m, zo = ez - 0.01, ez - 0.05, None
                    # v3 pista (B4): en la boca de un enlace el arcen va llano solo hasta la boca (u ~0.35) y no
                    # sube por encima de ella (la boca es horizontal y la pista tiene pendiente: en la mitad de
                    # arriba queda bajo el borde); despues se mete bajo el enlace (el llano de 1.8 m tapaba los
                    # que bajan, p. ej. casino_mar_enlace_fin y pueblo_subida_mar_enlace_fin). Una muestra mas a cada
                    # lado (paso_m) para que el cuadrilatero de transicion no deje una lengua de hierba sobre el canto.
                    bo_ = _boca_en(idx * G['paso_m'], sgn, G['paso_m']) if pr_ is None else None
                    if bo_ is not None:
                        e1 = min(e1, max(0.05, bo_[3] - 0.05))
                        e2 = min(e2, max(e1 + 0.3, 0.8))
                        if abs(idx * G['paso_m'] - bo_[0]) <= bo_[2]:
                            z_m = min(z_m, bo_[4] - 0.04)
                    ap = _arcen_pit(idx, sgn, half, ez)
                    if ap is not None:
                        e1, e2, z_e, z_m, zo = ap      # v1 (A-05/F-14): bifurcaciones del pit lane
                    mx_ = p['x'] + sgn * p['nx'] * (half + e1)
                    my_ = p['y'] + sgn * p['ny'] * (half + e1)
                    ox = p['x'] + sgn * p['nx'] * (half + e2)
                    oy = p['y'] + sgn * p['ny'] * (half + e2)
                    # plano 1.8 m y luego baja; el borde exterior SIEMPRE queda
                    # bajo el terreno (nada de repisas al aire)
                    if zo is None:
                        zo = min(ez - 1.6, _zt_arcen(ox, oy) - 0.35)
                    av_.append((ex, ey, z_e))
                    av_.append((mx_, my_, z_m))
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

def _orientar_arriba(vs, fs):
    """Da la vuelta a todas las caras si la normal media apunta hacia abajo."""
    nz = 0.0
    for f_ in fs:
        a, b, c = vs[f_[0]], vs[f_[1]], vs[f_[2]]
        nz += (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return fs if nz >= 0 else [tuple(reversed(f_)) for f_ in fs]

def _pretil(s0, s1, sgn, off0, grueso, alto, nombre, pie=None):
    """Pretil de piedra macizo: cara a la pista a off0 m del borde del asfalto, 'grueso' de
    ancho, coronacion a 'alto' sobre la acera; el pie siempre bajo el arcen y el terreno
    (pie = (dz_borde, dz_terreno): hasta min(ze - dz_borde, zt - dz_terreno))."""
    dzb, dzt = pie if pie is not None else (0.6, 0.4)
    vs, fs = [], []
    n_ = max(1, int((s1 - s0) / 2.0))
    for k in range(n_ + 1):
        q = muestra_s(s0 + (s1 - s0) * k / n_)
        half = q['w'] / 2.0
        ze = q['z'] - q['lat'] * sgn * half
        for off in (off0, off0 + grueso):
            x_ = q['x'] + q['nx'] * sgn * (half + off)
            y_ = q['y'] + q['ny'] * sgn * (half + off)
            vs.append((x_, y_, min(ze - dzb, _zt_arcen(x_, y_) - dzt)))
            vs.append((x_, y_, ze + 0.055 + alto))
    for k in range(n_):          # por fila: 0 pie int, 1 cima int, 2 pie ext, 3 cima ext
        o = 4 * k
        fs += [(o, o + 4, o + 5, o + 1), (o + 1, o + 5, o + 7, o + 3), (o + 3, o + 7, o + 6, o + 2)]
    fs += [(0, 1, 3, 2), (4 * n_, 4 * n_ + 2, 4 * n_ + 3, 4 * n_ + 1)]
    if sgn < 0:                  # normales hacia fuera (AC descarta las caras de espaldas)
        fs = [tuple(reversed(f_)) for f_ in fs]
    new_mesh_obj(nombre, vs, fs, [M_MUROC], [0] * len(fs))

M_MUROC = mat('MAT_muro_contencion_piedra', (0.63, 0.58, 0.47, 1), 0.95)
for (_a, _b, _l, _o, _nom, _pie) in PRETILES:
    _pretil(_a, _b, _l, _o, PRETIL_GRUESO, PRETIL_ALTO, _nom, pie=_pie)   # MUROC -> 1WALL en el kn5

# --- linea de salida ---
p0 = S[0]
h0 = p0['w'] / 2 - 0.3
lv = []
for t in (0, 1):
    q = S[t * 2]
    lv.append((q['x'] + q['nx'] * h0, q['y'] + q['ny'] * h0, q['z'] - q['lat'] * h0 + 0.04))
    lv.append((q['x'] - q['nx'] * h0, q['y'] - q['ny'] * h0, q['z'] + q['lat'] * h0 + 0.04))
new_mesh_obj('LINEA_SALIDA', lv, [(0, 1, 3, 2)], [M_LINEA], [0])

# --- pit lane (v1 pista: cota de _z_pit, seccion de NL_PIT vertices, borde interior efectivo) ---
if PITD:
    pvts, pfcs = [], []
    def _fila_pit_virtual(idx, d_ref):
        """Fila extra 2 m antes/despues del pit: la cinta se cierra en punta contra el BORDE del
        asfalto (tapa el triangulo que quedaba entre la pista, el pit y su hombro)."""
        p = S[idx % N]
        half = p['w'] / 2.0
        sg = d_ref['sgn']
        dv = dict(m=p, half=half, peso=1.0, zp=p['z'])
        ancho = d_ref['d_out'] - min(d_ref['d_in'], d_ref['half'] + d_ref['gore'])
        ls = [sg * (half - ancho), sg * half]
        if not d_ref['a_int']:
            ls.reverse()
        fila = []
        for j in range(NL_PIT):
            t = j / (NL_PIT - 1)
            l_ = ls[0] * (1 - t) + ls[1] * t
            x_, y_ = p['x'] + p['nx'] * l_, p['y'] + p['ny'] * l_
            fila.append((x_, y_, _z_pit(dv, x_, y_)))
        return fila
    filas_pit = []
    for d in PITD:
        A_ = d['P_in'] if d['a_int'] else d['A']
        B_ = d['B'] if d['a_int'] else d['P_in']
        fila = []
        for j in range(NL_PIT):
            t = j / (NL_PIT - 1)
            x_, y_ = A_[0] * (1 - t) + B_[0] * t, A_[1] * (1 - t) + B_[1] * t
            fila.append((x_, y_, _z_pit(d, x_, y_)))
        filas_pit.append(fila)
    if PITD[0]['hueco'] < 0.0:
        filas_pit.insert(0, _fila_pit_virtual(int((PITD[0]['s'] - 0.01) / G['paso_m']), PITD[0]))
    if PITD[-1]['hueco'] < 0.0:
        filas_pit.append(_fila_pit_virtual(int(math.ceil((PITD[-1]['s'] + 0.01) / G['paso_m'])), PITD[-1]))
    for fila in filas_pit:
        pvts.extend(fila)
    for k in range(len(filas_pit) - 1):
        o = NL_PIT * k
        for j in range(NL_PIT - 1):
            pfcs.append((o + j, o + j + 1, o + NL_PIT + j + 1, o + NL_PIT + j))
    new_mesh_obj('PIT_LANE', pvts, pfcs, [M_ASF], [0] * len(pfcs))
    _bif = [d for d in PITD if d['k'] <= _PIT_K0 - 2 or d['k'] >= _PIT_K1 + 2]
    _gore = [d for d in _bif if d['gore'] > 0.04]

    def _mayor_tramo(sel):
        """Filas consecutivas (k seguidos) mas largas de la seleccion."""
        tramos = []
        for d in sel:
            if tramos and d['k'] == tramos[-1][-1]['k'] + 1:
                tramos[-1].append(d)
            else:
                tramos.append([d])
        return max(tramos, key=len) if tramos else []
    # bordillo interior en la cuna (tapa la rendija entre la hierba y el borde de la cinta)
    for nombre_, sel in (('entrada', _mayor_tramo([d for d in _gore if d['k'] < _PIT_K0])),
                         ('salida', _mayor_tramo([d for d in _gore if d['k'] > _PIT_K1]))):
        if len(sel) < 2:
            continue
        bv, bf = [], []
        for d in sel:
            bv.append((d['P_in'][0], d['P_in'][1], d['zin'] + 0.005))
            bv.append((d['P_in'][0], d['P_in'][1], d['zin'] - 0.30))
        for m_ in range(len(sel) - 1):
            o = 2 * m_
            bf += [(o, o + 2, o + 3, o + 1), (o + 1, o + 3, o + 2, o)]
        new_mesh_obj('BORDILLO_pit_%s' % nombre_, bv, bf, [M_BORDILLO], [0] * len(bf))
    # linea blanca (MARCA_PIT) en el borde interior desde que los carriles se separan 0.3 m
    # hasta las marcas del pit_kit (filas K0+1 / K1-1)
    for nombre_, sel in (('entrada', _mayor_tramo([d for d in PITD if d['k'] <= _PIT_K0 + 1 and d['gore'] >= 0.3])),
                         ('salida', _mayor_tramo([d for d in PITD if d['k'] >= _PIT_K1 - 1 and d['gore'] >= 0.3]))):
        if len(sel) < 2:
            continue
        mv_, mf_ = [], []
        for d in sel:
            for off in (0.10, 0.25):
                x_ = d['P_in'][0] + d['u_out'][0] * off
                y_ = d['P_in'][1] + d['u_out'][1] * off
                mv_.append((x_, y_, _z_pit(d, x_, y_) + 0.02))
        for m_ in range(len(sel) - 1):
            o = 2 * m_
            mf_.append((o, o + 1, o + 3, o + 2))
        new_mesh_obj('MARCA_PIT_%s' % nombre_, mv_, _orientar_arriba(mv_, mf_), [M_MB], [0] * len(mf_))
    # ARCEN_PIT: hombro de hierba en el borde exterior (la cinta quedaba 0.6 m al aire sobre la
    # caja del terreno y su sombra hacia 'dientes'); no bajo el edificio de boxes (alli va su acera)
    _kc = 0.5 * (_PIT_K0 + _PIT_K1)
    for nombre_, sel in (('entrada', [d for d in PITD if d['k'] < _kc - 22]),
                         ('salida', [d for d in PITD if d['k'] > _kc + 22])):
        if len(sel) < 2:
            continue
        hv, hf = [], []
        filas = []
        for d in sel:
            (px, py), (ux, uy), zo_ = d['P_out'], d['u_out'], d['zout']
            x2, y2 = px + ux * 4.0, py + uy * 4.0
            filas.append([(px, py, zo_ - 0.01), (px + ux * 1.2, py + uy * 1.2, zo_ - 0.06),
                          (x2, y2, min(zo_ - 1.2, _zt_arcen(x2, y2) - 0.35))])
        # donde nace / muere el pit lane el hombro arranca de la ULTIMA fila del arcen normal de la
        # pista (mismos vertices): sin escalon ni cuna entre los dos arcenes
        def _fila_arcen_def(idx, sg):
            p = S[idx % N]
            half = p['w'] / 2.0
            ez = p['z'] - p['lat'] * half * sg
            pt = lambda e: (p['x'] + sg * p['nx'] * (half + e), p['y'] + sg * p['ny'] * (half + e))
            (ex, ey), (mx, my), (ox, oy) = pt(0.0), pt(1.8), pt(6.5)
            return [(ex, ey, ez - 0.01), (mx, my, ez - 0.05), (ox, oy, min(ez - 1.6, _zt_arcen(ox, oy) - 0.35))]
        if sel[0]['k'] == 0:
            filas.insert(0, _fila_arcen_def(int((PITD[0]['s'] - 0.01) / G['paso_m']), PITD[0]['sgn']))
        if sel[-1]['k'] == len(PITD) - 1:
            filas.append(_fila_arcen_def(int(math.ceil((PITD[-1]['s'] + 0.01) / G['paso_m'])), PITD[0]['sgn']))
        for f_ in filas:
            hv.extend(f_)
        for m_ in range(len(filas) - 1):
            o = 3 * m_
            hf += [(o, o + 1, o + 4, o + 3), (o + 1, o + 2, o + 5, o + 4)]
        hp = new_mesh_obj('ARCEN_PIT_%s' % nombre_, hv, _orientar_arriba(hv, hf), [M_TER], [0] * len(hf))
        hp.data.shade_smooth()
    print('pit lane construido: %d filas x %d, cuna en %d filas, peso>0 en %d filas'
          % (len(PITD), NL_PIT, len(_gore), sum(1 for d in PITD if d['peso'] > 0.0)))

# --- terreno ---
T = G['terreno']
nx_, ny_ = T['nx'], T['ny']
tz = T['z']
tmar = T['mar']
# v1 pista (F-14): el terreno nunca asoma por encima de la cinta del pit lane (+0.6 m alrededor);
# solo BAJA vertices (los que quedaban a menos de 0.12 m bajo la cinta)
_n_baj = 0
for k in range(len(PITD) - 1):
    d0, d1 = PITD[k], PITD[k + 1]
    c0 = ((d0['P_in'][0] + d0['P_out'][0]) / 2, (d0['P_in'][1] + d0['P_out'][1]) / 2)
    c1 = ((d1['P_in'][0] + d1['P_out'][0]) / 2, (d1['P_in'][1] + d1['P_out'][1]) / 2)
    hw = max(math.hypot(d['P_in'][0] - d['P_out'][0], d['P_in'][1] - d['P_out'][1]) for d in (d0, d1)) / 2 + 0.6
    zs = min(d0['zin'], d0['zout'], d1['zin'], d1['zout']) - 0.12
    sx, sy = c1[0] - c0[0], c1[1] - c0[1]
    ls2 = sx * sx + sy * sy or 1e-9
    ii0 = max(0, int((min(c0[0], c1[0]) - hw - T['x0']) / T['cell']))
    ii1 = min(nx_ - 1, int((max(c0[0], c1[0]) + hw - T['x0']) / T['cell']) + 1)
    jj0 = max(0, int((min(c0[1], c1[1]) - hw - T['y0']) / T['cell']))
    jj1 = min(ny_ - 1, int((max(c0[1], c1[1]) + hw - T['y0']) / T['cell']) + 1)
    for jj in range(jj0, jj1 + 1):
        for ii in range(ii0, ii1 + 1):
            x_, y_ = T['x0'] + ii * T['cell'], T['y0'] + jj * T['cell']
            t_ = max(0.0, min(1.0, ((x_ - c0[0]) * sx + (y_ - c0[1]) * sy) / ls2))
            if math.hypot(x_ - c0[0] - sx * t_, y_ - c0[1] - sy * t_) <= hw and tz[jj * nx_ + ii] > zs:
                tz[jj * nx_ + ii] = zs
                _n_baj += 1
if PITD:
    print('terreno bajo el pit lane: %d vertices rebajados' % _n_baj)
tv = []
for j in range(ny_):
    for i in range(nx_):
        tv.append((T['x0'] + i * T['cell'], T['y0'] + j * T['cell'], tz[j * nx_ + i]))
tf, tfm = [], []
# RONDA 15 (v1 pista, N2): la malla va YA TRIANGULADA, dos triangulos por celda con diagonal
# FIJA (a-c, la que usaba Blender al triangular estos quads para el render y el kn5). Con quads,
# el BVH de asentar_objetos / inspectores (FromPolygons) cortaba por otra diagonal en el 18 % de
# las celdas (p99 7 m en laderas): arboles 'asentados' que flotaban. Ahora render, kn5, asentar e
# inspectores ven LA MISMA superficie. (La diagonal de envolvente inferior se probo: dientes de
# sierra en la costa y en las coronaciones convexas.) Los vertices no cambian (j*nx+i): las
# explanadas del integrador y la lectura de cota de los inspectores siguen funcionando.
for j in range(ny_ - 1):
    for i in range(nx_ - 1):
        a = j * nx_ + i
        b, c, d = a + 1, a + nx_ + 1, a + nx_
        tf.append((a, b, c))
        tf.append((a, c, d))
        tfm.extend((0, 0))
terreno = new_mesh_obj('TERRENO', tv, tf, [M_TER, M_FONDO], tfm)
terreno.data.shade_smooth()
# RONDA 15: mascara de roca del macizo (terreno_montana.py: pendiente > 50 % o cota alta)
# como atributo por vertice 'roca'; el material la mezcla con la pendiente real
if G.get('mascara_roca') and len(G['mascara_roca']) == len(tv):
    _at = terreno.data.attributes.new('roca', 'FLOAT', 'POINT')
    _at.data.foreach_set('value', [float(v) for v in G['mascara_roca']])
    print('terreno: atributo roca (media %.2f) en %d vertices' % (sum(G['mascara_roca']) / len(tv), len(tv)))

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
