"""pit_kit.py — Complejo de boxes de Porto Corsa (Cars 2) para Blender 5.1.

Segun el fotograma 01_referencias/drive/pitlane_x2.png: un edificio de boxes
largo con los garajes a pie de pista, encima una planta de servicio con galeria
y, sobre ella, una GRAN GRADA de terrazas escalonadas (rampas, sin escaleras)
llena de coches-espectador, con muro trasero, techo plano AZUL sobre postes
finos con imposta clara y banderas italianas en el peto delantero. Muro de
boxes bajo con puestos de equipo, torres redondas de control/TV y pasarela
sobre la pista.

Convenciones (CONTRATO.md): metros, origen en el centro de la base, z=0 en el
suelo, FACHADA PRINCIPAL A +Y (los portones de los boxes miran a +Y = pit lane
/ pista). Mallas por codigo (from_pydata), Principled BSDF de color plano,
materiales MAT_PIT_<clave> reutilizados por nombre, objetos con prefijo PIT_.

Piezas:
- build_boxes_tribuna(parent, n=20, ancho_box=6.0, seed=0, **params)
    Edificio completo. Huella: x en [-n*ancho_box/2, n*ancho_box/2],
    y en [-6.5, 6.5] (+0.3 m de vuelo del techo por detras y por los lados),
    altura 17.5 m (losa del techo; su imposta llega a 17.58; bbox z 0..17.58,
    y -6.8..6.67 con banderas). Portones (abiertos, persiana
    enrollada) en y=+6.5. Raiz: Empty 'PIT_boxes'. Hijos: PIT_boxes_edificio,
    PIT_boxes_grada, PIT_boxes_techo, PIT_boxes_publico, PIT_boxes_numeros
    (los n numeros en una sola malla) y PIT_boxes_rotulo (si L >= 40).
    Grada: `filas` terrazas de 1.15 m de subida (pendiente ~33 grados), la
    primera pegada al peto delantero (0.65 m) para que el publico asome desde
    la pista; publico a tresbolillo, paso 1.55 m.
    params: filas=7 (terrazas), ocupacion=0.97, max_tris=60000, banderas=True.
- plazas_boxes(n=20, ancho_box=6.0) -> [(x, y, rot_z), ...]
    Plaza de aparcamiento de cada box (coords locales del edificio): centro a
    3 m del porton hacia dentro (y = 3.5), morro hacia -Y (rot_z = pi para un
    coche que a rot 0 mira a +Y, como coches_kit_v2).
- build_muro_boxes(parent, largo=12.0, seed=0, tapa_x0=False, tapa_x1=False,
    equipo=True): tramo de muro de boxes a lo largo de X: podio macizo de
    hormigon de 1.1 m de alto y 2.2 m de fondo (y en [-2.0, 0.2]) con valla
    de captura al lado de pista (+Y); encima, puestos de equipo techados
    (pupitre con monitores y pit board hacia la pista, plataforma de 1.7 m
    para el equipo, parapeto hacia el pit lane). Huella y en [-2.05, 0.30]
    (el lado del pit lane es -Y). Repetible: periodo = largo; tapa_x0/tapa_x1
    cierran los extremos (primer / ultimo tramo). Devuelve la malla
    PIT_muro_boxes; si equipo=True lleva como hijo la malla
    PIT_muro_boxes_equipo (1-2 coches-mecanico por puesto, 58 tris cada uno).
- build_torre_control(parent, alto=16.0, seed=0): torre redonda (fuste,
    tambor acristalado con balcon anular, remate y antena). Raiz Empty
    PIT_torre. Radio maximo 3.9 m (balcon).
- build_pasarela(parent, luz=22.0, alto=7.0, seed=0): pasarela cubierta sobre
    la pista: pasillo de longitud `luz` a lo largo de X a altura `alto`, entre
    dos torres de celosia con rampas en zigzag (sin escaleras, con peto
    exterior), banda de patrocinio en ambos costados. Extension total en X =
    luz + 14.8 (torres de 7.2 m + vuelo del techo 0.2). Raiz Empty PIT_pasarela.
- build(parent, seed=0, **params): escaparate (boxes + pit lane + muro +
    torres + pasarela sobre asfalto).
"""

import math
import random

import bpy

PRE = 'PIT'

# ------------------------------------------------------------------ materiales

# clave: (color, roughness, metallic, color_emision | None, fuerza_emision)
_PALETA = {
    'crema':        ((0.93, 0.85, 0.64), 0.60, 0.0, None, 0.0),
    'blanco':       ((0.92, 0.91, 0.88), 0.55, 0.0, None, 0.0),
    'ocre':         ((0.86, 0.56, 0.22), 0.65, 0.0, None, 0.0),
    'hormigon':     ((0.62, 0.62, 0.60), 0.85, 0.0, None, 0.0),
    'suelo_box':    ((0.50, 0.52, 0.55), 0.80, 0.0, None, 0.0),
    'gris_oscuro':  ((0.10, 0.10, 0.11), 0.60, 0.0, None, 0.0),
    'gris_acero':   ((0.32, 0.35, 0.38), 0.40, 0.6, None, 0.0),
    'negro':        ((0.02, 0.02, 0.02), 0.60, 0.0, None, 0.0),
    'asfalto':      ((0.13, 0.13, 0.14), 0.90, 0.0, None, 0.0),
    'piedra_clara': ((0.60, 0.54, 0.42), 0.85, 0.0, None, 0.0),
    'azul_techo':   ((0.13, 0.35, 0.75), 0.50, 0.0, None, 0.0),
    'azul_claro':   ((0.42, 0.66, 0.92), 0.50, 0.0, None, 0.0),
    'azul_oscuro':  ((0.03, 0.08, 0.30), 0.45, 0.0, None, 0.0),
    'rojo':         ((0.80, 0.08, 0.06), 0.50, 0.0, None, 0.0),
    'verde_wgp':    ((0.04, 0.58, 0.18), 0.45, 0.0, None, 0.0),
    'cristal':      ((0.22, 0.36, 0.48), 0.30, 0.0, None, 0.0),
    'pantalla_luz': ((0.04, 0.12, 0.40), 0.30, 0.0, (0.20, 0.45, 0.95), 1.1),
    'rojo_luz':     ((0.85, 0.04, 0.02), 0.40, 0.0, (1.0, 0.04, 0.02), 6.0),
    'pub_rojo':     ((0.80, 0.08, 0.06), 0.50, 0.0, None, 0.0),
    'pub_azul':     ((0.08, 0.22, 0.78), 0.50, 0.0, None, 0.0),
    'pub_amarillo': ((0.95, 0.72, 0.08), 0.50, 0.0, None, 0.0),
    'pub_verde':    ((0.10, 0.58, 0.16), 0.50, 0.0, None, 0.0),
    'pub_naranja':  ((0.90, 0.36, 0.04), 0.50, 0.0, None, 0.0),
    'pub_morado':   ((0.42, 0.09, 0.58), 0.50, 0.0, None, 0.0),
    'pub_cian':     ((0.08, 0.62, 0.68), 0.50, 0.0, None, 0.0),
    'pub_blanco':   ((0.90, 0.90, 0.88), 0.50, 0.0, None, 0.0),
    'pub_cristal':  ((0.20, 0.33, 0.45), 0.65, 0.0, None, 0.0),
}

_PUBLICO = ('pub_rojo', 'pub_azul', 'pub_amarillo', 'pub_verde',
            'pub_naranja', 'pub_morado', 'pub_cian', 'pub_blanco')
# colores de equipo de los boxes (banda sobre el porton, armario, puestos)
_EQUIPOS = ('pub_rojo', 'pub_azul', 'pub_amarillo', 'pub_verde',
            'pub_naranja', 'pub_morado', 'pub_cian', 'verde_wgp')


def _mat(clave):
    """Crea (o reutiliza) el material MAT_PIT_<clave> de la paleta."""
    nombre = 'MAT_%s_%s' % (PRE, clave)
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough, metal, emision, fuerza = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    try:
        if not m.use_nodes:
            m.use_nodes = True
    except AttributeError:
        pass
    bsdf = None
    nt = m.node_tree
    if nt is not None:
        for nd in nt.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                bsdf = nd
                break
        if bsdf is None:
            bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
            salida = None
            for nd in nt.nodes:
                if nd.type == 'OUTPUT_MATERIAL':
                    salida = nd
                    break
            if salida is None:
                salida = nt.nodes.new('ShaderNodeOutputMaterial')
            nt.links.new(bsdf.outputs['BSDF'], salida.inputs['Surface'])
    if bsdf is not None:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = rough
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metal
        if emision is not None:
            ent = bsdf.inputs.get('Emission Color') or bsdf.inputs.get('Emission')
            fue = bsdf.inputs.get('Emission Strength')
            if ent is not None:
                ent.default_value = (*emision, 1.0)
            if fue is not None:
                fue.default_value = fuerza
    m.diffuse_color = (*color, 1.0)
    return m


# ------------------------------------------------------------ utilidades malla

def _normal_newell(pts):
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1, z1 = pts[i]
        x2, y2, z2 = pts[(i + 1) % n]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return nx, ny, nz


class _MG:
    """Malla generica: poligonos arbitrarios con material y sombreado por cara.
    Cada cara se orienta segun `ref` (normal deseada) o `centro` (punto
    interior del solido)."""

    def __init__(self):
        self.v = []
        self.f = []
        self.fm = []
        self.fs = []

    def verts(self, pts):
        i0 = len(self.v)
        self.v.extend(pts)
        return i0

    def cara(self, ids, mat=0, suave=False, ref=None, centro=None):
        ids = list(ids)
        pts = [self.v[i] for i in ids]
        if ref is None and centro is not None:
            n = float(len(pts))
            ref = (sum(p[0] for p in pts) / n - centro[0],
                   sum(p[1] for p in pts) / n - centro[1],
                   sum(p[2] for p in pts) / n - centro[2])
        if ref is not None:
            nx, ny, nz = _normal_newell(pts)
            if nx * ref[0] + ny * ref[1] + nz * ref[2] < 0.0:
                ids.reverse()
        self.f.append(tuple(ids))
        self.fm.append(mat)
        self.fs.append(bool(suave))

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def obj(self, nombre, claves_mat, col, separar=False):
        v, f = self.v, self.f
        if separar:
            v, f = [], []
            for cara in self.f:
                i0 = len(v)
                v.extend(self.v[i] for i in cara)
                f.append(tuple(range(i0, i0 + len(cara))))
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(v, [], f)
        for clave in claves_mat:
            me.materials.append(_mat(clave))
        for p, mi, su in zip(me.polygons, self.fm, self.fs):
            p.material_index = mi
            p.use_smooth = su
        me.validate()
        me.update()
        ob = bpy.data.objects.new(nombre, me)
        col.objects.link(ob)
        return ob


def _prisma_x(mg, x0, x1, perfil, mat, omitir=(), mats=None, tf=None):
    """Extruye a lo largo de X el poligono CONVEXO `perfil` = [(y, z), ...].
    Caras: 'x0', 'x1' (tapas) + una por arista k (perfil[k] -> perfil[k+1])."""
    n = len(perfil)
    cy = sum(p[0] for p in perfil) / float(n)
    cz = sum(p[1] for p in perfil) / float(n)
    centro = (0.5 * (x0 + x1), cy, cz)
    pts = [(x0, p[0], p[1]) for p in perfil] + [(x1, p[0], p[1]) for p in perfil]
    if tf is not None:
        pts = [tf(p) for p in pts]
        centro = tf(centro)
    i0 = mg.verts(pts)
    mats = mats or {}
    if 'x0' not in omitir:
        mg.cara([i0 + k for k in range(n)], mats.get('x0', mat), centro=centro)
    if 'x1' not in omitir:
        mg.cara([i0 + n + k for k in range(n)], mats.get('x1', mat), centro=centro)
    for k in range(n):
        if k in omitir:
            continue
        k2 = (k + 1) % n
        mg.cara([i0 + k, i0 + k2, i0 + n + k2, i0 + n + k], mats.get(k, mat),
                centro=centro)


def _caja_g(mg, x0, x1, y0, y1, z0, z1, mat, omitir=(), mats=None, tf=None):
    """Caja alineada a ejes. Aristas: 0 = suelo (z0), 1 = cara +Y (y1),
    2 = techo (z1), 3 = cara -Y (y0); tapas 'x0' / 'x1'."""
    _prisma_x(mg, x0, x1, [(y0, z0), (y1, z0), (y1, z1), (y0, z1)], mat,
              omitir=omitir, mats=mats, tf=tf)


def _quad(mg, pts, mat, ref):
    i = mg.verts(pts)
    mg.cara((i, i + 1, i + 2, i + 3), mat, False, ref=ref)


def _cilindro(mg, cx, cy, z0, z1, r0, mat, r1=None, seg=16, tapa0=False,
              tapa1=True, suave=True, mat_tapas=None, fase=0.0):
    """Tronco de cono vertical (radio r0 abajo, r1 arriba) de `seg` lados."""
    r1 = r0 if r1 is None else r1
    a = [fase + 2.0 * math.pi * k / seg for k in range(seg)]
    i0 = mg.verts([(cx + r0 * math.cos(t), cy + r0 * math.sin(t), z0) for t in a])
    i1 = mg.verts([(cx + r1 * math.cos(t), cy + r1 * math.sin(t), z1) for t in a])
    c = (cx, cy, 0.5 * (z0 + z1))
    mt = mat if mat_tapas is None else mat_tapas
    for k in range(seg):
        k2 = (k + 1) % seg
        mg.cara((i0 + k, i0 + k2, i1 + k2, i1 + k), mat, suave, centro=c)
    if tapa0:
        mg.cara(range(i0, i0 + seg), mt, False, ref=(0, 0, -1))
    if tapa1:
        mg.cara(range(i1, i1 + seg), mt, False, ref=(0, 0, 1))


def _cono(mg, cx, cy, z0, z1, r, mat, seg=16, suave=True):
    a = [2.0 * math.pi * k / seg for k in range(seg)]
    i0 = mg.verts([(cx + r * math.cos(t), cy + r * math.sin(t), z0) for t in a])
    ip = mg.verts([(cx, cy, z1)])
    c = (cx, cy, z0 - 0.5)
    for k in range(seg):
        mg.cara((i0 + k, i0 + (k + 1) % seg, ip), mat, suave, centro=c)


def _losa(mg, x0, x1, y0, y1, za, zb, esp, mat, omitir=()):
    """Losa inclinada a lo largo de X: cara superior de z=za (en x0) a z=zb
    (en x1), espesor `esp`. Caras: 0 suelo, 1 +Y, 2 arriba, 3 -Y, 'x0', 'x1'."""
    p = [(x0, y0, za - esp), (x1, y0, zb - esp), (x1, y1, zb - esp), (x0, y1, za - esp),
         (x0, y0, za), (x1, y0, zb), (x1, y1, zb), (x0, y1, za)]
    i = mg.verts(p)
    c = (0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (za + zb) - 0.5 * esp)
    caras = {0: (0, 1, 2, 3), 1: (3, 2, 6, 7), 2: (4, 5, 6, 7), 3: (0, 1, 5, 4),
             'x0': (0, 3, 7, 4), 'x1': (1, 2, 6, 5)}
    for k, q in caras.items():
        if k in omitir:
            continue
        mg.cara([i + j for j in q], mat, False, centro=c)


def _raiz(nombre, col):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_size = 0.5
    col.objects.link(e)
    return e


def _textos_malla(nombre, items, clave_mat, col, extrude=0.05):
    """Varios textos 3D en UNA malla `nombre`: items = [(texto, tam, (x, y, z),
    rot_z), ...]. Cada texto se centra en (x, y, z), de pie y legible desde +Y
    (rot_z = 0) o girado rot_z sobre Z (pi: legible desde -Y). La curva FONT
    se convierte con meshes.new_from_object sobre un objeto temporal SIN
    enlazar ni evaluar (no toca el depsgraph): las transformaciones se hornean
    en los vertices y el objeto queda con transform identidad."""
    vs, fs = [], []
    for texto, tam, (x, y, z), rot_z in items:
        cu = bpy.data.curves.new(nombre + '_cu', type='FONT')
        cu.body = texto
        cu.size = tam
        cu.extrude = extrude
        cu.align_x = 'CENTER'
        cu.align_y = 'CENTER'
        cu.resolution_u = 3
        tmp = bpy.data.objects.new(nombre + '_tmp', cu)
        me_t = bpy.data.meshes.new_from_object(tmp)
        bpy.data.objects.remove(tmp)
        bpy.data.curves.remove(cu)
        # Rx(90): (x, y, z) -> (x, -z, y); luego Rz(pi + rot_z) y traslacion
        co, si = math.cos(math.pi + rot_z), math.sin(math.pi + rot_z)
        i0 = len(vs)
        for v in me_t.vertices:
            px, py, pz = v.co.x, -v.co.z, v.co.y
            vs.append((x + px * co - py * si, y + px * si + py * co, z + pz))
        for p in me_t.polygons:
            fs.append(tuple(i0 + i for i in p.vertices))
        bpy.data.meshes.remove(me_t)
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(vs, [], fs)
    me.materials.append(_mat(clave_mat))
    me.validate()
    me.update()
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    return ob


def _texto_3d(nombre, texto, tam, clave_mat, col, extrude=0.05, pos=(0.0, 0.0, 0.0),
              rot_z=0.0):
    """Texto 3D suelto (malla `nombre`), centrado en `pos`, de pie y legible
    desde +Y (rot_z = pi: desde -Y). Transform horneada en los vertices."""
    return _textos_malla(nombre, [(texto, tam, pos, rot_z)], clave_mat, col,
                         extrude=extrude)


# ------------------------------------------------ coches-espectador (publico)

_PUB_MATS = ('pub_cristal',) + _PUBLICO + ('negro', 'crema')
_PM_CRISTAL = 0
_PM_PILOTO = 1 + _PUBLICO.index('pub_rojo')
_PM_OJO = 1 + _PUBLICO.index('pub_blanco')
_PM_NEGRO = 1 + len(_PUBLICO)
_PM_FARO = 2 + len(_PUBLICO)
_PUB_TRIS = 58          # triangulos exactos por coche-espectador (<= 60)
_PUB_PESOS_COLOR = (5, 4, 4, 3, 3, 2, 2, 3)
_ANG6 = tuple(k * math.pi / 3.0 for k in range(6))
_ANG4 = tuple(math.pi / 4.0 + k * math.pi / 2.0 for k in range(4))


def _pub_coche(mg, pos, rz, W, L, e, mi, mirada, boca_abierta, tipo=0):
    """Coche-espectador de 58 tris con el morro a +Y local: carroceria en
    tronco octogonal (faros/pilotos en los chaflanes), cabina con parabrisas y
    luneta mates, dos ojos con pupila, boca y dos ejes de ruedas.
    pos = (x, y, z suelo); mirada = (du, dv) en [-1, 1] (pupilas)."""
    x, y, z = pos
    co, si = math.cos(rz), math.sin(rz)
    # tipo 0 berlina, 1 deportivo (bajo), 2 furgoneta (alta)
    H = (1.00, 0.86, 1.18)[tipo] * e
    yb_f, yt_f = (0.20, 0.13, 0.33)[tipo] * L, (0.03, -0.08, 0.24)[tipo] * L
    yt_r, yb_r = (-0.30, -0.30, -0.40)[tipo] * L, (-0.43, -0.44, -0.45)[tipo] * L
    zc_f, zc_r = (0.52, 0.47, 0.56)[tipo] * e, (0.58, 0.55, 0.60)[tipo] * e

    def T(p):
        return (x + p[0] * co - p[1] * si, y + p[0] * si + p[1] * co, z + p[2])

    def R(v):
        return (v[0] * co - v[1] * si, v[0] * si + v[1] * co, v[2])

    def anillo(hw, yf, yr, ch, zf, zr):
        plan = ((hw, yf - ch), (hw - ch, yf), (-(hw - ch), yf), (-hw, yf - ch),
                (-hw, yr + ch), (-(hw - ch), yr), (hw - ch, yr), (hw, yr + ch))
        return [(px, py, zr + (zf - zr) * (py - yr) / (yf - yr)) for px, py in plan]

    # carroceria: faldon -> borde del capo (8 quads) + capo/maletero plano
    r0 = anillo(0.45 * W, 0.46 * L, -0.46 * L, 0.12 * W, 0.13 * e, 0.13 * e)
    r1 = anillo(0.50 * W, 0.50 * L, -0.50 * L, 0.17 * W, zc_f, zc_r)
    i0 = mg.verts([T(p) for p in r0 + r1])
    cb = T((0.0, 0.0, 0.30 * e))
    for j in range(8):
        j2 = (j + 1) % 8
        m = mi
        if j in (0, 2):
            m = _PM_FARO
        elif j in (4, 6):
            m = _PM_PILOTO
        mg.cara((i0 + j, i0 + j2, i0 + 8 + j2, i0 + 8 + j), m, True, centro=cb)
    mg.cara([i0 + 8 + j for j in range(8)], mi, False, ref=(0.0, 0.0, 1.0))

    # cabina (hundida 4 cm en el capo)
    z_cb = min(zc_f, zc_r) - 0.04 * e
    hb, ht = 0.41 * W, 0.31 * W
    cab = [(hb, yb_f, z_cb), (-hb, yb_f, z_cb), (-hb, yb_r, z_cb), (hb, yb_r, z_cb),
           (ht, yt_f, H), (-ht, yt_f, H), (-ht, yt_r, H), (ht, yt_r, H)]
    i1 = mg.verts([T(p) for p in cab])
    cc = T((0.0, 0.5 * (yb_f + yb_r), 0.5 * (z_cb + H)))
    for a, b, m in ((0, 1, _PM_CRISTAL), (1, 2, mi), (2, 3, _PM_CRISTAL), (3, 0, mi)):
        mg.cara((i1 + a, i1 + b, i1 + 4 + b, i1 + 4 + a), m, False, centro=cc)
    mg.cara((i1 + 4, i1 + 5, i1 + 6, i1 + 7), mi, False, ref=(0.0, 0.0, 1.0))

    # ojos sobre el parabrisas (hexagono blanco + pupila cuadrada)
    ty, tz = yt_f - yb_f, H - z_cb
    sl = math.hypot(ty, tz)
    ty, tz = ty / sl, tz / sl
    nl = (0.0, tz, -ty)
    nw = R(nl)
    v_c = 0.56 * sl
    hw_v = hb + (ht - hb) * 0.56
    u_c = 0.5 * (hw_v - 0.01)
    ru = min(0.21 * e, u_c - 0.015)
    rv = min(0.21 * e, 0.36 * sl)
    rp = 0.46 * min(ru, rv)

    def P(u, v, off):
        return T((u, yb_f + ty * v + nl[1] * off, z_cb + tz * v + nl[2] * off))

    du = max(-1.0, min(1.0, mirada[0]))
    dv = max(-1.0, min(1.0, mirada[1]))
    for sx in (-1.0, 1.0):
        ue = sx * u_c
        ie = mg.verts([P(ue + ru * math.cos(a), v_c + rv * math.sin(a), 0.04)
                       for a in _ANG6])
        mg.cara(range(ie, ie + 6), _PM_OJO, False, ref=nw)
        pu = ue + du * (ru - rp - 0.012)
        pv = v_c + dv * (rv - rp - 0.012)
        ip = mg.verts([P(pu + rp * math.cos(a), pv + rp * math.sin(a), 0.07)
                       for a in _ANG4])
        mg.cara(range(ip, ip + 4), _PM_NEGRO, False, ref=nw)

    # boca sobre el morro (cara frontal del tronco), 4 cm por delante
    ym0, zm0 = 0.46 * L, 0.13 * e
    ym1, zm1 = 0.50 * L, zc_f
    ml = math.hypot(ym1 - ym0, zm1 - zm0)
    nb = ((zm1 - zm0) / ml, -(ym1 - ym0) / ml)

    def B(u, w):
        return T((u, ym0 + (ym1 - ym0) * w + nb[0] * 0.04,
                  zm0 + (zm1 - zm0) * w + nb[1] * 0.04))

    m_ = 0.27 * W
    if boca_abierta:
        pts = [B(-m_, 0.80), B(m_, 0.80), B(0.55 * m_, 0.35), B(-0.55 * m_, 0.35)]
    else:
        pts = [B(-m_, 0.72), B(m_, 0.72), B(0.75 * m_, 0.55), B(-0.75 * m_, 0.55)]
    ib = mg.verts(pts)
    mg.cara(range(ib, ib + 4), _PM_NEGRO, False, ref=R((0.0, 1.0, 0.0)))

    # ruedas: dos ejes-caja bajo el faldon (costados + cara exterior del eje)
    hwr = 0.5 * W + 0.03
    rr = 0.17 * e
    zr_ = 0.32 * e
    for ya, delante in ((0.28 * L, True), (-0.28 * L, False)):
        ia = mg.verts([T(p) for p in (
            (-hwr, ya - rr, 0.0), (hwr, ya - rr, 0.0), (hwr, ya + rr, 0.0),
            (-hwr, ya + rr, 0.0), (-hwr, ya - rr, zr_), (hwr, ya - rr, zr_),
            (hwr, ya + rr, zr_), (-hwr, ya + rr, zr_))])
        mg.cara((ia, ia + 3, ia + 7, ia + 4), _PM_NEGRO, False, ref=R((-1.0, 0.0, 0.0)))
        mg.cara((ia + 1, ia + 2, ia + 6, ia + 5), _PM_NEGRO, False, ref=R((1.0, 0.0, 0.0)))
        if delante:
            mg.cara((ia + 3, ia + 2, ia + 6, ia + 7), _PM_NEGRO, False,
                    ref=R((0.0, 1.0, 0.0)))
        else:
            mg.cara((ia, ia + 1, ia + 5, ia + 4), _PM_NEGRO, False,
                    ref=R((0.0, -1.0, 0.0)))


# ------------------------------------------------------------- geometria comun

_FONDO = 13.0        # fondo total del edificio (y en [-6.5, 6.5])
_H_GARAJE = 4.5      # altura libre de los garajes
_Z_GALERIA = 5.0     # suelo de la planta de servicio (galeria)
_Z_GRADA = 8.4       # suelo de la grada (cara superior de su losa)
_Z_TECHO = 17.2      # cara inferior del techo azul (vigas de 0.35 por debajo)
_RISE = 1.15         # subida por terraza (grada empinada: el publico asoma
                     # sobre el peto desde la pista a la altura de un piloto)
_H_PETO = 0.65       # altura del peto delantero de la grada
_PASO_PUB = 1.55     # paso del publico en X (coches pegados, a tresbolillo)


def plazas_boxes(n=20, ancho_box=6.0):
    """Plazas de aparcamiento de los n boxes en coordenadas locales del
    edificio: lista de (x, y, rot_z). Centro a 3 m del porton (y = 6.5 - 3.0),
    morro hacia -Y (rot_z = pi para un coche que sin girar mira a +Y)."""
    n = max(1, int(n))
    w = float(ancho_box)
    a2 = 0.5 * n * w
    y = 0.5 * _FONDO - 3.0
    return [(-a2 + (i + 0.5) * w, y, math.pi) for i in range(n)]


# ---------------------------------------------------------- edificio de boxes

def build_boxes_tribuna(parent_collection, n=20, ancho_box=6.0, seed=0, **params):
    """Edificio de boxes con grada encima (ver docstring del modulo).
    params: filas=7, ocupacion=0.97, max_tris=60000, banderas=True."""
    col = parent_collection
    raiz = _raiz('%s_boxes' % PRE, col)
    rng = random.Random(seed)

    n = max(1, int(n))
    w = float(ancho_box)
    L = n * w
    a2 = L / 2.0
    filas = max(1, int(params.get('filas', 7)))
    ocupacion = float(params.get('ocupacion', 0.97))
    max_tris = int(params.get('max_tris', 60000))
    banderas = bool(params.get('banderas', True))

    y_f = 0.5 * _FONDO            # fachada de los portones (+Y)
    y_b = -0.5 * _FONDO           # fachada trasera (paddock)
    y_g = y_f - 6.0               # cara interior del fondo de los garajes
    y_s = 5.0                     # fachada de la planta de servicio (galeria)
    y_w = y_b + 0.4               # cara interior del muro trasero de la grada
    e_m = 0.3                     # espesor de muros
    z_g = _H_GARAJE               # techo libre garaje
    z_gal = _Z_GALERIA
    z_l0 = _Z_GRADA - 0.4         # cara inferior de la losa de la grada
    z_gr = _Z_GRADA
    z_r = _Z_TECHO
    j_w = min(0.6, 0.12 * w)      # semiancho de la jamba (pilastra) del porton
    h_p = 4.0                     # altura del hueco del porton
    xs_b = [-a2 + i * w for i in range(n + 1)]     # limites de los boxes
    cxs = [-a2 + (i + 0.5) * w for i in range(n)]

    # ============================================================ edificio
    # 0 crema, 1 blanco, 2 gris_oscuro, 3 suelo_box, 4 rojo, 5 cristal,
    # 6 gris_acero, 7 negro, 8 hormigon, 9.. equipos
    (E_CREMA, E_BLANCO, E_OSCURO, E_SUELO, E_ROJO, E_CRISTAL, E_ACERO, E_NEGRO,
     E_HORM, E_OCRE) = range(10)
    E_EQ0 = 10
    me = _MG()
    xi0, xi1 = -a2 + e_m, a2 - e_m           # interior entre muros de testero

    # --- garajes: suelo, techo, fondo, tabiques (interior gris: que el hueco
    # del porton se lea como hueco frente a la fachada crema)
    _quad(me, [(xi0, y_g, 0.02), (xi1, y_g, 0.02), (xi1, y_f, 0.02), (xi0, y_f, 0.02)],
          E_SUELO, (0, 0, 1))
    _quad(me, [(xi0, y_g, z_g), (xi1, y_g, z_g), (xi1, y_f - e_m, z_g), (xi0, y_f - e_m, z_g)],
          E_HORM, (0, 0, -1))
    _quad(me, [(xi0, y_g, 0.0), (xi1, y_g, 0.0), (xi1, y_g, z_g), (xi0, y_g, z_g)],
          E_HORM, (0, 1, 0))
    for i in range(1, n):
        xb = xs_b[i]
        _caja_g(me, xb - 0.15, xb + 0.15, y_g, y_f - e_m, 0.0, z_g, E_HORM,
                omitir=(0, 1, 2, 3))
    # zocalo gris del interior (banda en el fondo y tabiques): solo fondo
    for i in range(n):
        cx = cxs[i]
        eq = E_EQ0 + i % len(_EQUIPOS)
        # banda de color de equipo en el fondo del garaje
        _caja_g(me, cx - 0.5 * w + 0.5, cx + 0.5 * w - 0.5, y_g, y_g + 0.03,
                2.0, 2.5, eq, omitir=(3,))
        # armario de herramientas (color de equipo) y mesa de trabajo
        _caja_g(me, cx + 0.5 * w - 1.6, cx + 0.5 * w - 0.5, y_g + 0.03, y_g + 0.7,
                0.0, 1.9, eq, omitir=(0, 3))
        _caja_g(me, cx - 0.5 * w + 0.4, cx - 0.5 * w + 2.2, y_g + 0.03, y_g + 0.8,
                0.0, 0.95, E_ACERO, omitir=(0, 3))
        # pila de 3 neumaticos junto al tabique
        tx, ty_ = cx - 0.5 * w + 0.85, y_g + 1.7
        _cilindro(me, tx, ty_, 0.0, 0.45, 0.36, E_NEGRO, seg=8, tapa1=False, suave=False)
        _cilindro(me, tx, ty_, 0.45, 0.90, 0.36, E_NEGRO, seg=8, tapa1=False, suave=False)
        _cilindro(me, tx, ty_, 0.90, 1.35, 0.36, E_NEGRO, seg=8, tapa1=True, suave=False,
                  mat_tapas=E_ACERO)
        # persiana enrollable: tambor tras el dintel + faldon de lamas colgando
        yd = y_f - e_m - 0.30
        _prisma_x(me, cx - 0.5 * w + j_w, cx + 0.5 * w - j_w,
                  [(yd + 0.26 * math.cos(t), h_p + 0.24 + 0.26 * math.sin(t))
                   for t in (k * math.pi / 4.0 for k in range(8))], E_ACERO,
                  omitir=('x0', 'x1'))
        _caja_g(me, cx - 0.5 * w + j_w + 0.02, cx + 0.5 * w - j_w - 0.02,
                yd - 0.03, yd + 0.03, h_p - 0.55, h_p + 0.05, E_OSCURO,
                omitir=(2,))
        for k in range(2):
            zl = h_p - 0.42 + k * 0.22
            _caja_g(me, cx - 0.5 * w + j_w + 0.03, cx + 0.5 * w - j_w - 0.03,
                    yd + 0.03, yd + 0.05, zl, zl + 0.06, E_BLANCO, omitir=(3,))
        # fachada: banda de equipo y placa del numero sobre el dintel
        _caja_g(me, cx - 0.5 * w + j_w + 0.05, cx + 0.5 * w - j_w - 0.05, y_f, y_f + 0.03,
                h_p + 0.05, h_p + 0.22, eq, omitir=(3,))
        _caja_g(me, cx - 0.7, cx + 0.7, y_f, y_f + 0.06, h_p + 0.26,
                h_p + 0.98, E_BLANCO, omitir=(3,))
    # jambas (pilastras ocre, 12 cm en relieve) y dintel corrido de los portones
    for i in range(n + 1):
        xb = xs_b[i]
        x0, x1 = max(-a2 + e_m, xb - j_w), min(a2 - e_m, xb + j_w)
        # mocheta (jamba dentro del hueco) + pilastra en relieve hasta la cornisa
        _caja_g(me, x0, x1, y_f - e_m, y_f, 0.0, h_p, E_OCRE, omitir=(0, 1, 2))
        _caja_g(me, x0, x1, y_f, y_f + 0.12, 0.0, z_gal - 0.18, E_OCRE, omitir=(0, 2, 3))
        # zocalo de piedra de la pilastra
        _caja_g(me, x0 - 0.02, x1 + 0.02, y_f, y_f + 0.17, 0.0, 0.6, E_HORM,
                omitir=(0, 3))
    _caja_g(me, -a2 + e_m, a2 - e_m, y_f - e_m, y_f, h_p, z_gal, E_CREMA,
            omitir=(2, 'x0', 'x1'))
    # cornisa fina sobre el dintel
    _caja_g(me, -a2, a2, y_f, y_f + 0.12, z_gal - 0.18, z_gal, E_BLANCO,
            omitir=(3,))

    # --- planta de servicio: galeria cubierta con columnas y peto
    _quad(me, [(xi0, y_s, z_gal), (xi1, y_s, z_gal), (xi1, y_f - 0.15, z_gal),
               (xi0, y_f - 0.15, z_gal)], E_HORM, (0, 0, 1))
    _quad(me, [(xi0, y_s, z_l0), (xi1, y_s, z_l0), (xi1, y_f, z_l0), (xi0, y_f, z_l0)],
          E_BLANCO, (0, 0, -1))
    _caja_g(me, xi0, xi1, y_f - 0.15, y_f, z_gal, z_gal + 1.0, E_BLANCO,
            omitir=(0, 'x0', 'x1'))
    _caja_g(me, -a2, a2, y_f, y_f + 0.03, z_gal + 0.45, z_gal + 0.75, E_ROJO,
            omitir=(3,))
    for i in range(1, n):          # en los extremos la columna es el testero
        xb = xs_b[i]
        _caja_g(me, xb - 0.15, xb + 0.15, y_f - e_m, y_f, z_gal + 1.0, z_l0, E_CREMA,
                omitir=(0, 2))
    # pared del fondo de la galeria con ventanales
    _caja_g(me, xi0, xi1, y_s - 0.15, y_s, z_gal, z_l0, E_CREMA,
            omitir=(0, 2, 3, 'x0', 'x1'))
    for cx in cxs:
        hv = min(1.5, 0.25 * w)
        xv0, xv1 = cx - hv + 0.9, cx + hv + 0.9        # ventanal a la derecha
        _caja_g(me, xv0, xv1, y_s, y_s + 0.06, z_gal + 0.9, z_gal + 2.3,
                E_BLANCO, omitir=(3,))
        _caja_g(me, xv0 + 0.1, xv1 - 0.1, y_s + 0.06, y_s + 0.09,
                z_gal + 1.0, z_gal + 2.2, E_CRISTAL, omitir=(3,))
        # puerta (para coches) a la izquierda
        _caja_g(me, xv0 - 2.0, xv0 - 0.2, y_s, y_s + 0.04, z_gal,
                z_gal + 2.3, E_OSCURO, omitir=(0, 3))

    # --- losa de la grada (fascia delantera) y muros de testero
    _caja_g(me, -a2, a2, y_w, y_f, z_l0, z_gr, E_BLANCO, omitir=(0, 3, 2))
    _caja_g(me, -a2, a2, y_f, y_f + 0.05, z_l0 + 0.05, z_gr - 0.05, E_ROJO,
            omitir=(3,))
    for sx in (-1.0, 1.0):
        x0, x1 = (-a2, -a2 + e_m) if sx < 0 else (a2 - e_m, a2)
        om = (0, 'x1' if sx < 0 else 'x0')
        _caja_g(me, x0, x1, y_b, y_f, 0.0, z_l0, E_CREMA, omitir=om)
        # cara interior del testero: solo el tramo visible del garaje extremo
        xi = x1 if sx < 0 else x0
        _quad(me, [(xi, y_g, 0.0), (xi, y_f - e_m, 0.0), (xi, y_f - e_m, z_g),
                   (xi, y_g, z_g)], E_HORM, (-sx, 0, 0))
        _quad(me, [(xi, y_s, z_gal), (xi, y_f - e_m, z_gal), (xi, y_f - e_m, z_l0),
                   (xi, y_s, z_l0)], E_CREMA, (-sx, 0, 0))
        # pilar de esquina trasero hasta el techo
        _caja_g(me, x0, x1, y_b, y_w, z_l0, z_r, E_CREMA, omitir=om)
        # porton de servicio (rampa interior) en el testero, sobre el zocalo
        xo = x0 - 0.05 if sx < 0 else x1
        _caja_g(me, xo, xo + 0.05, -2.0, 2.0, 0.6, 3.6, E_OSCURO, omitir=om)
        _caja_g(me, xo - 0.02 if sx < 0 else xo, (xo + 0.05) if sx < 0 else xo + 0.07,
                -5.5, 5.5, 0.0, 0.6, E_HORM, omitir=om)
    # --- muro trasero (paddock) hasta el techo, con zocalo, portones y ventanas.
    # Su cara interior (+Y) la pone la grada por encima de la losa; por debajo
    # queda dentro del volumen macizo: no se genera.
    _caja_g(me, -a2 + e_m, a2 - e_m, y_b, y_w, 0.0, z_r, E_CREMA,
            omitir=(0, 1, 2, 'x0', 'x1'))
    _caja_g(me, -a2, a2, y_b - 0.05, y_b, 0.0, 0.6, E_HORM, omitir=(0, 1))
    _caja_g(me, -a2, a2, y_b - 0.10, y_b, z_l0, z_l0 + 0.3, E_BLANCO, omitir=(1,))
    _caja_g(me, -a2, a2, y_b - 0.10, y_b, z_r - 0.5, z_r, E_BLANCO, omitir=(1, 2))
    for i in range(n):
        cx = cxs[i]
        if i % 4 == 1:
            _caja_g(me, cx - 2.2, cx + 2.2, y_b - 0.05, y_b, 0.6, 3.8, E_OSCURO,
                    omitir=(0, 1))
        hv = min(1.5, 0.5 * w - 0.7)
        _caja_g(me, cx - hv, cx + hv, y_b - 0.04, y_b, z_gal + 0.9, z_gal + 2.3,
                E_BLANCO, omitir=(1,))
        _caja_g(me, cx - hv + 0.1, cx + hv - 0.1, y_b - 0.06, y_b - 0.04,
                z_gal + 1.0, z_gal + 2.2, E_CRISTAL, omitir=(1,))
    # ritmo de la fachada trasera: pilastras blancas cada 2 boxes (fuera de la
    # zona del rotulo central) y banda blanca a media altura de la grada
    tam_rot = 2.0 if L >= 40.0 else 0.0
    semi_rot = 0.5 * 11 * tam_rot * 0.62 + 1.5
    for i in range(0, n + 1, 2):
        xb = xs_b[i]
        if abs(xb) < semi_rot or abs(xb) > a2 - 0.6:
            continue
        _caja_g(me, xb - 0.25, xb + 0.25, y_b - 0.12, y_b, 0.6, z_r - 0.5, E_BLANCO,
                omitir=(0, 1, 2))
    _caja_g(me, -a2, a2, y_b - 0.06, y_b, z_l0 + 4.0, z_l0 + 4.5, E_BLANCO, omitir=(1,))
    edificio = me.obj('%s_boxes_edificio' % PRE,
                      ('crema', 'blanco', 'gris_oscuro', 'suelo_box', 'rojo',
                       'cristal', 'gris_acero', 'negro', 'hormigon', 'ocre') + _EQUIPOS,
                      col, separar=True)
    edificio.parent = raiz

    # numeros de los boxes (una sola malla, legibles desde el pit lane)
    numeros = _textos_malla('%s_boxes_numeros' % PRE,
                            [(str(i + 1), 0.62, (cxs[i], y_f + 0.08, h_p + 0.60), 0.0)
                             for i in range(n)], 'gris_oscuro', col, extrude=0.03)
    numeros.parent = raiz
    # rotulo PORTO CORSA en la fachada trasera (legible desde -Y)
    if tam_rot > 0.0:
        rot = _texto_3d('%s_boxes_rotulo' % PRE, 'PORTO CORSA', tam_rot, 'azul_techo',
                        col, extrude=0.04, pos=(0.0, y_b - 0.09, z_l0 + 5.9),
                        rot_z=math.pi)
        rot.parent = raiz

    # ============================================================== grada
    # 0 crema, 1 blanco, 2 verde_wgp, 3 piedra_clara, 4 gris_oscuro, 5 rojo
    G_CREMA, G_BLANCO, G_VERDE, G_PIEDRA, G_OSCURO, G_ROJO = range(6)
    mg = _MG()
    y_par0, y_par1 = y_f - 0.3, y_f             # peto delantero (0.65 m)
    y_t0 = y_par0                                # primera terraza pegada al peto
    prof = (y_t0 - y_w) / filas                  # ~1.76 m con 7 filas
    z_top = z_gr + (filas - 1) * _RISE
    h_peto = _H_PETO

    # reparto en X: muros laterales, rampas y bloques
    g_lat, g_div, w_rampa, w_pas = e_m, 0.22, 2.3, 2.4
    hay_rampas = L >= 16.0
    bloques, calles = [], []
    if hay_rampas:
        n_bl = max(1, int(round(L / 30.0)))
        x_in = a2 - g_lat - w_rampa - g_div
        wb = (2.0 * x_in - (n_bl - 1) * (w_pas + 2.0 * g_div)) / n_bl
        calles.append((-a2 + g_lat, -a2 + g_lat + w_rampa))
        for k in range(n_bl):
            xa = -x_in + k * (wb + w_pas + 2.0 * g_div)
            bloques.append((xa, xa + wb))
            if k < n_bl - 1:
                calles.append((xa + wb + g_div, xa + wb + g_div + w_pas))
        calles.append((a2 - g_lat - w_rampa, a2 - g_lat))
    else:
        bloques.append((-a2 + g_lat, a2 - g_lat))

    # peto delantero bajo (blanco con banda roja): la primera terraza arranca
    # justo detras, sin pasillo, para que el publico asome por encima
    _caja_g(mg, -a2 + g_lat, a2 - g_lat, y_par0, y_par1, z_gr, z_gr + h_peto, G_BLANCO,
            omitir=(0, 'x0', 'x1'))
    _caja_g(mg, -a2, a2, y_par1, y_par1 + 0.03, z_gr + 0.25, z_gr + 0.45, G_ROJO,
            omitir=(3,))
    # terrazas (huella crema + contrahuella blanca)
    ext = g_div if hay_rampas else 0.05
    for xa, xb in bloques:
        x0, x1 = xa - ext, xb + ext
        for i in range(filas):
            zf = z_gr + i * _RISE
            yf = y_t0 - i * prof
            yr = yf - prof
            _quad(mg, [(x0, yr, zf), (x1, yr, zf), (x1, yf, zf), (x0, yf, zf)],
                  G_CREMA, (0, 0, 1))
            if i > 0:
                _quad(mg, [(x0, yf, zf - _RISE), (x1, yf, zf - _RISE), (x1, yf, zf),
                           (x0, yf, zf)], G_BLANCO, (0, 1, 0))
    # pasillos-rampa
    yc0 = y_t0 - 0.5 * prof
    ycl = y_w + 0.5 * prof
    for k, (xa, xb) in enumerate(calles):
        x0 = xa - 0.05 if k == 0 else xa
        x1 = xb + 0.05 if k == len(calles) - 1 else xb
        tramos = [((y_t0, z_gr), (yc0, z_gr))]
        if filas > 1:
            tramos.append(((yc0, z_gr), (ycl, z_top)))
        tramos.append(((ycl, z_top), (y_w, z_top)))
        for (ya_, za_), (yb_, zb_) in tramos:
            _quad(mg, [(x0, ya_, za_), (x1, ya_, za_), (x1, yb_, zb_), (x0, yb_, zb_)],
                  G_PIEDRA, (0, 0, 1))
        _caja_g(mg, xa + 0.25, xb - 0.25, y_w - 0.05, y_w + 0.14, z_top - 0.05,
                min(z_top + 1.6, z_r - 0.45), G_BLANCO, omitir=(0, 3), mats={1: G_OSCURO})
    if hay_rampas and filas > 1:
        for xa, xb in bloques:
            for xj, sg in ((xa - g_div, -1.0), (xb + g_div, 1.0)):
                for i in range(filas):
                    zf = z_gr + i * _RISE
                    yf = y_t0 - i * prof
                    yr = yf - prof
                    ym = 0.5 * (yf + yr)
                    if i > 0:
                        iv = mg.verts([(xj, yf, zf - 0.5 * _RISE), (xj, yf, zf), (xj, ym, zf)])
                        mg.cara((iv, iv + 1, iv + 2), G_VERDE, False, ref=(sg, 0.0, 0.0))
                    if i < filas - 1:
                        iv = mg.verts([(xj, ym, zf), (xj, yr, zf + 0.5 * _RISE), (xj, yr, zf)])
                        mg.cara((iv, iv + 1, iv + 2), G_VERDE, False, ref=(-sg, 0.0, 0.0))
    # muros laterales (siguen la pendiente, coronacion 1.15 m sobre la nariz de
    # las terrazas: por encima del peto, que muere contra ellos; la coronacion
    # se recorta en horizontal 0.45 m bajo el techo para no cruzar las vigas)
    # con albardilla verde
    pend = _RISE / prof if filas > 1 else 0.0
    c_ext, cop = 1.15, 0.12
    y_d0 = y_f
    z_cap = z_r - 0.45 - cop

    def z_linea(yy):
        return min(z_cap, z_gr + c_ext + (y_t0 - yy) * pend)

    zf, zb = z_linea(y_d0), z_linea(y_w)
    perfil_cor = [(y_d0, zf)]                    # coronacion de delante atras
    if zb >= z_cap - 1e-6 and pend > 1e-9:
        y_k = y_t0 - (z_cap - z_gr - c_ext) / pend
        if y_w + 0.05 < y_k < y_d0 - 0.05:
            perfil_cor.append((y_k, z_cap))
    perfil_cor.append((y_w, zb))
    for x0, x1 in ((-a2, -a2 + g_lat), (a2 - g_lat, a2)):
        # muro: perfil convexo (hipografo de la coronacion), sin suelo, sin
        # las aristas de coronacion (las cubre la albardilla) ni la trasera
        _prisma_x(mg, x0, x1, [(y_w, z_gr), (y_d0, z_gr)] + perfil_cor,
                  G_BLANCO, omitir=(0,) + tuple(range(2, 2 + len(perfil_cor))))
        # albardilla: un prisma por tramo de coronacion; caras internas entre
        # tramos, apoyo y trasera omitidas
        for k in range(len(perfil_cor) - 1):
            (ya_, za_), (yb_, zb_) = perfil_cor[k], perfil_cor[k + 1]
            # 0 apoyo; 1 cara trasera del tramo (junta o dentro del muro
            # trasero); 3 cara delantera (solo visible en el primer tramo)
            om = (0, 1) if k == 0 else (0, 1, 3)
            _prisma_x(mg, x0, x1, [(ya_, za_), (yb_, zb_), (yb_, zb_ + cop), (ya_, za_ + cop)],
                      G_VERDE, omitir=om)
    # cara interior del muro trasero sobre la grada + banda verde bajo el techo
    _caja_g(mg, -a2 + e_m, a2 - e_m, y_w - 0.1, y_w, z_gr, z_r, G_BLANCO,
            omitir=(0, 2, 3, 'x0', 'x1'))
    _caja_g(mg, -a2 + e_m + 0.4, a2 - e_m - 0.4, y_w, y_w + 0.08, z_r - 1.05,
            z_r - 0.5, G_VERDE, omitir=(3,))
    grada = mg.obj('%s_boxes_grada' % PRE,
                   ('crema', 'blanco', 'verde_wgp', 'piedra_clara', 'gris_oscuro',
                    'rojo'), col, separar=True)
    grada.parent = raiz

    # ============================================================== techo
    # 0 azul_techo, 1 azul_claro, 2 gris_acero, 3 verde_wgp, 4 blanco, 5 rojo
    T_AZUL, T_CLARO, T_ACERO, T_VERDE, T_BLANCO, T_ROJO = range(6)
    mt = _MG()
    v = 0.3
    y_r1 = y_t0 - 0.2                     # borde delantero del techo
    _caja_g(mt, -a2 - v, a2 + v, y_b - v, y_r1, z_r, z_r + 0.3, T_AZUL, omitir=(1,))
    # imposta clara en el borde delantero
    _caja_g(mt, -a2 - v, a2 + v, y_r1, y_r1 + 0.08, z_r - 0.35, z_r + 0.38, T_CLARO,
            omitir=(3,))
    # postes finos (en la 2a terraza y sobre los muros laterales) que suben
    # hasta la cara inferior de las vigas; las vigas transversales (canto
    # 0.35, bajo la losa) se colocan EXACTAMENTE en la x de cada poste, con
    # vigas intermedias cada <= 7 m para que ningun poste quede en el aire
    i_col = min(filas - 1, 1)
    y_col = y_t0 - (i_col + 0.5) * prof - 0.35
    z_c0 = z_gr + i_col * _RISE
    pies_ext = [-a2 + 0.5 * g_lat, a2 - 0.5 * g_lat]
    pies = []
    for xa, xb in bloques:
        pies += [xa + 0.45, xb - 0.45]
        if xb - xa > 14.0:
            pies.append(0.5 * (xa + xb))
    z_vig = z_r - 0.35
    for xc_ in pies_ext + pies:
        zc_ = z_linea(y_col) + cop if xc_ in pies_ext else z_c0
        _caja_g(mt, xc_ - 0.11, xc_ + 0.11, y_col - 0.11, y_col + 0.11, zc_,
                z_vig, T_ACERO, omitir=(0, 2))
    xs_p = sorted(pies_ext + pies)
    xs_v = [xs_p[0]]
    for xa_, xb_ in zip(xs_p, xs_p[1:]):
        k_ = max(1, int(round((xb_ - xa_) / 7.0)))
        xs_v += [xa_ + (xb_ - xa_) * j / k_ for j in range(1, k_ + 1)]
    for xv in xs_v:
        _caja_g(mt, xv - 0.12, xv + 0.12, y_w, y_r1 - 0.1, z_vig, z_r, T_BLANCO,
                omitir=(2, 3))
    # banderas italianas sobre el peto delantero (una por box)
    if banderas:
        for i in range(n):
            xp = cxs[i] - 0.72
            yp = y_par0 + 0.15
            zp, zt = z_gr + h_peto, z_gr + h_peto + 2.4
            _caja_g(mt, xp - 0.035, xp + 0.035, yp - 0.035, yp + 0.035, zp, zt,
                    T_ACERO, omitir=(0,))
            for s_, cm in enumerate((T_VERDE, T_BLANCO, T_ROJO)):
                xa_ = xp + 0.035 + s_ * 0.44
                om = ['x0'] + ([] if s_ == 2 else ['x1'])
                _caja_g(mt, xa_, xa_ + 0.44, yp - 0.012, yp + 0.012, zt - 0.95,
                        zt - 0.05, cm, omitir=tuple(om))
    techo = mt.obj('%s_boxes_techo' % PRE,
                   ('azul_techo', 'azul_claro', 'gris_acero', 'verde_wgp', 'blanco',
                    'rojo'), col, separar=True)
    techo.parent = raiz

    # ============================================================ publico
    mp = _MG()
    paso = _PASO_PUB          # coches pegados (ancho max 1.46 con ruedas)
    l_max = prof - 0.14
    plazas = []
    for xa, xb in bloques:
        k = int((xb - xa - 0.45) // paso)
        if k < 1:
            continue
        x_ini = 0.5 * (xa + xb) - (k - 1) * paso / 2.0
        for i in range(filas):
            # tresbolillo: las filas impares van desplazadas medio paso (y
            # tienen una plaza menos) para que se vean entre los de delante
            des = 0.5 * paso if (i % 2 == 1 and k > 1) else 0.0
            k_i = k - 1 if des > 0.0 else k
            for p in range(k_i):
                xp_ = x_ini + des + p * paso
                # plaza ocupada por un poste del techo: se deja libre
                if i == i_col and any(abs(xp_ - xq) < 0.95 for xq in pies):
                    continue
                plazas.append((i, xp_))
    ocupadas = [pl for pl in plazas if rng.random() < ocupacion]
    n_max = max(0, (max_tris - me.tris() - mg.tris() - mt.tris() - 220 * n) // _PUB_TRIS)
    if len(ocupadas) > n_max:
        rng.shuffle(ocupadas)
        ocupadas = sorted(ocupadas[:n_max])
    obj_x = rng.uniform(-0.4, 0.4) * L
    obj_y = y_f + 18.0
    mi_prev = -1
    for i, xc in ocupadas:
        tipo = rng.choices((0, 1, 2), weights=(5, 3, 2))[0]
        e = rng.uniform(0.90, 1.06)
        W = 1.28 * e * rng.uniform(0.96, 1.03)      # <= 1.40 (+0.06 ruedas)
        Lc = min(1.50 * e, l_max)
        mi = 1 + rng.choices(range(len(_PUBLICO)), weights=_PUB_PESOS_COLOR)[0]
        if mi == mi_prev:
            mi = 1 + rng.choices(range(len(_PUBLICO)), weights=_PUB_PESOS_COLOR)[0]
        mi_prev = mi
        x = xc + rng.uniform(-0.03, 0.03)
        z = z_gr + i * _RISE
        y = y_t0 - (i + 0.5) * prof + rng.uniform(-0.03, 0.03)
        ddx, ddy = obj_x - x, obj_y - y
        dd = math.hypot(ddx, ddy)
        if rng.random() < 0.12:
            mirada = (rng.uniform(-1.0, 1.0), rng.uniform(-0.5, 0.6))
        else:
            mirada = (1.9 * ddx / dd + rng.uniform(-0.12, 0.12),
                      -0.35 + rng.uniform(-0.15, 0.15))
        rz = rng.uniform(-0.06, 0.06) - 0.05 * max(-1.0, min(1.0, mirada[0]))
        _pub_coche(mp, (x, y, z), rz, W, Lc, e, mi, mirada, rng.random() < 0.45, tipo)
    publico = mp.obj('%s_boxes_publico' % PRE, _PUB_MATS, col)
    publico.parent = raiz
    return raiz


# -------------------------------------------------------------- muro de boxes

def build_muro_boxes(parent_collection, largo=12.0, seed=0, **params):
    """Tramo de muro de boxes a lo largo de X (repetible, periodo = largo):
    podio macizo de hormigon de 1.1 m de alto y 2.2 m de fondo con remate
    blanco (la coronacion es la plataforma del equipo), valla de captura al
    lado de la pista (+Y) y puestos de equipo techados (pupitre con monitores
    y pit board hacia la pista, sitio para 1-2 coches-mecanico, parapeto
    hacia el pit lane). Huella y en [-2.05, 0.30].
    params: tapa_x0 / tapa_x1 = False (cierran los extremos del podio, para el
    primer y el ultimo tramo), equipo = True (coches-mecanico en la malla hija
    PIT_muro_boxes_equipo). Devuelve la malla PIT_muro_boxes."""
    col = parent_collection
    rng = random.Random(seed)
    largo = float(largo)
    a2 = largo / 2.0
    tapas = tuple(t for t, quiere in (('x0', params.get('tapa_x0', False)),
                                      ('x1', params.get('tapa_x1', False))) if not quiere)
    con_equipo = bool(params.get('equipo', True))
    # 0 hormigon, 1 blanco, 2 gris_acero, 3 gris_oscuro, 4 pantalla_luz,
    # 5 negro, 6 verde_wgp, 7.. equipos
    M_HORM, M_BLANCO, M_ACERO, M_OSCURO, M_PANT, M_NEGRO, M_VERDE = range(7)
    M_EQ0 = 7
    mg = _MG()
    h_m = 1.1
    y_pl = -2.0                # borde del podio hacia el pit lane
    # podio macizo con remate blanco. Tapas x0/x1 omitidas salvo tapa_x0/x1.
    _caja_g(mg, -a2, a2, y_pl, 0.2, 0.0, h_m - 0.12, M_HORM, omitir=(0, 2) + tapas)
    _caja_g(mg, -a2, a2, y_pl - 0.05, 0.22, h_m - 0.12, h_m, M_BLANCO, omitir=tapas)
    # banda verde WGP a lo largo del lado del pit lane
    _caja_g(mg, -a2, a2, y_pl - 0.02, y_pl, 0.35, 0.65, M_VERDE, omitir=(1,) + tapas)
    # valla de captura (postes cada 2 m + 3 largueros) al lado de pista
    n_p = max(1, int(round(largo / 2.0)))
    for k in range(n_p):
        x = -a2 + (k + 0.5) * largo / n_p
        _caja_g(mg, x - 0.04, x + 0.04, 0.10, 0.18, h_m, h_m + 1.3, M_ACERO, omitir=(0,))
    for z in (h_m + 0.45, h_m + 0.85, h_m + 1.25):
        _caja_g(mg, -a2, a2, 0.185, 0.215, z - 0.02, z + 0.02, M_ACERO, omitir=tapas)
    # puestos de equipo sobre la plataforma: uno cada ~6 m, 4.2 m de ancho
    n_b = max(1, int(round(largo / 6.0)))
    wb = min(4.2, largo / n_b - 1.2)
    z_p = h_m
    mq = _MG()                 # coches-mecanico (materiales del publico)
    y_par = y_pl + 0.12        # cara interior del parapeto trasero
    for k in range(n_b):
        cx = -a2 + (k + 0.5) * largo / n_b
        i_eq = rng.randrange(len(_EQUIPOS))
        eq = M_EQ0 + i_eq
        x0, x1 = cx - 0.5 * wb, cx + 0.5 * wb
        # pupitre bajo (0.7 m, frente a la pista) con monitores y pit board:
        # el equipo, sobre una tarima de 0.35, asoma por encima desde la pista
        _caja_g(mg, x0 + 0.1, x1 - 0.1, -0.15, 0.2, z_p, z_p + 0.70, M_OSCURO, omitir=(0, 2))
        _caja_g(mg, x0 + 0.08, x1 - 0.08, -0.17, 0.22, z_p + 0.70, z_p + 0.80, eq, omitir=(0,))
        nm = max(1, int(wb / 1.2))
        for j in range(nm):
            xm = x0 + 0.1 + (j + 0.5) * (wb - 0.2) / nm
            # monitores mirando al equipo (que trabaja en el lado del pit lane)
            _caja_g(mg, xm - 0.36, xm + 0.36, -0.10, -0.06, z_p + 0.80, z_p + 1.25,
                    M_OSCURO, omitir=(0,))
            _caja_g(mg, xm - 0.32, xm + 0.32, -0.12, -0.10, z_p + 0.84, z_p + 1.21,
                    M_PANT, omitir=(1,))
        # pit board volado sobre el frente del pupitre (panel blanco cerrado
        # por todas sus caras + banda de color hacia la pista)
        _caja_g(mg, x1 - 0.95, x1 - 0.15, 0.22, 0.26, z_p + 0.80, z_p + 1.60, M_BLANCO)
        _caja_g(mg, x1 - 0.9, x1 - 0.2, 0.26, 0.28, z_p + 1.20, z_p + 1.50, eq, omitir=(3,))
        # techo del puesto (color de equipo) sobre 4 postes finos
        for xp in (x0 + 0.08, x1 - 0.08):
            for yp in (y_par + 0.06, 0.05):
                _caja_g(mg, xp - 0.04, xp + 0.04, yp - 0.04, yp + 0.04, z_p, z_p + 2.45,
                        M_ACERO, omitir=(0, 2))
        _caja_g(mg, x0 - 0.05, x1 + 0.05, y_pl - 0.03, 0.15, z_p + 2.45, z_p + 2.55, eq)
        _caja_g(mg, x0 - 0.05, x1 + 0.05, 0.15, 0.18, z_p + 2.30, z_p + 2.60, M_BLANCO,
                omitir=(3,))
        # parapeto trasero bajo (0.5 m, hacia el pit lane) con banda verde
        _caja_g(mg, x0 + 0.08, x1 - 0.08, y_pl + 0.05, y_par, z_p, z_p + 0.5, M_BLANCO,
                omitir=(0,))
        _caja_g(mg, x0 + 0.08, x1 - 0.08, y_pl + 0.04, y_pl + 0.05, z_p + 0.18, z_p + 0.36,
                M_VERDE, omitir=(1,))
        # tarima del equipo entre el parapeto y el pupitre
        z_tar = z_p + 0.35
        _caja_g(mg, x0 + 0.15, x1 - 0.15, y_par + 0.02, -0.22, z_p, z_tar, M_HORM,
                omitir=(0,))
        # 1-2 coches-mecanico del equipo mirando a la pista (+Y) sobre la
        # tarima, con hueco libre para los postes del techo
        if con_equipo:
            n_c = 2 if (wb >= 3.6 and rng.random() < 0.7) else 1
            y_c = 0.5 * ((y_par + 0.12) + (-0.22 - 0.1))
            for j in range(n_c):
                xc_ = cx + (0.0 if n_c == 1 else (j - 0.5) * 1.75) + rng.uniform(-0.06, 0.06)
                e = rng.uniform(0.92, 1.02)
                mi = 1 + _PUBLICO.index(_EQUIPOS[i_eq]) if _EQUIPOS[i_eq] in _PUBLICO \
                    else 1 + _PUBLICO.index('pub_verde')
                mirada = (rng.uniform(-0.5, 0.5), rng.uniform(0.2, 0.7))
                _pub_coche(mq, (xc_, y_c + rng.uniform(-0.04, 0.04), z_tar),
                           rng.uniform(-0.08, 0.08), 1.28 * e, min(1.48 * e, 1.5), e, mi,
                           mirada, rng.random() < 0.4, rng.choice((0, 0, 1)))
    ob = mg.obj('%s_muro_boxes' % PRE,
                ('hormigon', 'blanco', 'gris_acero', 'gris_oscuro', 'pantalla_luz',
                 'negro', 'verde_wgp') + _EQUIPOS, col, separar=True)
    if con_equipo and mq.f:
        equipo = mq.obj('%s_muro_boxes_equipo' % PRE, _PUB_MATS, col)
        equipo.parent = ob
    return ob


# ------------------------------------------------------------ torre de control

def build_torre_control(parent_collection, alto=16.0, seed=0, **params):
    """Torre redonda de control / TV: plinto, fuste cilindrico de piedra clara
    con bandas, balcon anular con barandilla, tambor acristalado, remate
    conico y antena. `alto` = altura del alero del tambor. Raiz PIT_torre."""
    col = parent_collection
    raiz = _raiz('%s_torre' % PRE, col)
    alto = max(8.0, float(alto))
    # 0 piedra_clara, 1 blanco, 2 cristal, 3 gris_acero, 4 azul_techo,
    # 5 gris_oscuro, 6 rojo_luz, 7 crema
    K_PIEDRA, K_BLANCO, K_CRISTAL, K_ACERO, K_AZUL, K_OSCURO, K_LUZ, K_CREMA = range(8)
    mg = _MG()
    seg = 20
    r_f = 2.0
    z_b = alto - 3.8                 # suelo del balcon / base del tambor
    _cilindro(mg, 0, 0, 0.0, 0.5, 2.7, K_PIEDRA, seg=seg, suave=False, tapa1=True)
    _cilindro(mg, 0, 0, 0.5, z_b - 0.35, r_f, K_CREMA, seg=seg, tapa1=False)
    # bandas de piedra en el fuste y puerta a pie de calle (mirando a +Y)
    for zz in (0.5 + (z_b - 1.0) / 3.0, 0.5 + 2.0 * (z_b - 1.0) / 3.0):
        _cilindro(mg, 0, 0, zz, zz + 0.3, r_f + 0.12, K_PIEDRA, seg=seg, tapa0=True,
                  tapa1=True, suave=False)
    _caja_g(mg, -1.1, 1.1, r_f - 0.4, r_f + 0.05, 0.5, 3.4, K_OSCURO, omitir=(0, 3))
    # balcon anular con barandilla
    _cilindro(mg, 0, 0, z_b - 0.35, z_b, 3.9, K_BLANCO, seg=seg, tapa0=True, tapa1=True,
              suave=False)
    for k in range(seg):
        t = 2.0 * math.pi * (k + 0.5) / seg
        xq, yq = 3.72 * math.cos(t), 3.72 * math.sin(t)
        _caja_g(mg, xq - 0.035, xq + 0.035, yq - 0.035, yq + 0.035, z_b, z_b + 1.0,
                K_ACERO, omitir=(0,))
    _cilindro(mg, 0, 0, z_b + 0.96, z_b + 1.02, 3.78, K_ACERO, seg=seg, tapa0=True,
              tapa1=True, suave=False)
    # tambor: antepecho blanco, cristalera A RAS (mismo radio: sin ranura
    # abierta en las juntas) con columnillas por fuera, dintel, alero y remate
    r_t = 3.0
    _cilindro(mg, 0, 0, z_b, z_b + 0.9, r_t, K_BLANCO, seg=seg, tapa1=False)
    _cilindro(mg, 0, 0, z_b + 0.9, z_b + 2.9, r_t, K_CRISTAL, seg=seg, tapa1=False)
    for k in range(seg):
        t = 2.0 * math.pi * k / seg
        xq, yq = (r_t + 0.03) * math.cos(t), (r_t + 0.03) * math.sin(t)
        _cilindro(mg, xq, yq, z_b + 0.9, z_b + 2.9, 0.06, K_BLANCO, seg=4, tapa1=False,
                  suave=False, fase=t)
    _cilindro(mg, 0, 0, z_b + 2.9, alto, r_t, K_BLANCO, seg=seg, tapa1=False)
    _cilindro(mg, 0, 0, alto, alto + 0.25, r_t + 0.35, K_AZUL, seg=seg, tapa0=True,
              tapa1=False, suave=False)
    _cono(mg, 0, 0, alto + 0.25, alto + 1.6, r_t + 0.35, K_AZUL, seg=seg)
    # antena con baliza roja
    _caja_g(mg, -0.06, 0.06, -0.06, 0.06, alto + 1.4, alto + 5.0, K_ACERO, omitir=(0,))
    _caja_g(mg, -0.12, 0.12, -0.12, 0.12, alto + 5.0, alto + 5.25, K_LUZ)
    for zz in (alto + 3.0, alto + 4.0):
        _caja_g(mg, -0.5, 0.5, -0.02, 0.02, zz, zz + 0.04, K_ACERO)
    ob = mg.obj('%s_torre_cuerpo' % PRE,
                ('piedra_clara', 'blanco', 'cristal', 'gris_acero', 'azul_techo',
                 'gris_oscuro', 'rojo_luz', 'crema'), col)
    ob.parent = raiz
    return raiz


# -------------------------------------------------------------------- pasarela

def build_pasarela(parent_collection, luz=22.0, alto=7.0, seed=0, **params):
    """Pasarela cubierta sobre la pista: pasillo de longitud `luz` (a lo largo
    de X, x en [-luz/2, luz/2]) a altura `alto`, entre dos torres de celosia
    de 7.2 x 3.4 m con rampas en zigzag (4 tramos con peto exterior; sin
    escaleras; losas cerradas por debajo, visibles desde la pista). Bandas de
    patrocinio 'WORLD GRAND PRIX' en ambos costados. Extension en X:
    +-(luz/2 + 7.4) (torre 7.2 + vuelo del techo 0.2). Raiz PIT_pasarela."""
    col = parent_collection
    raiz = _raiz('%s_pasarela' % PRE, col)
    luz = max(6.0, float(luz))
    alto = max(4.0, float(alto))
    a2 = luz / 2.0
    # 0 gris_acero, 1 blanco, 2 azul_oscuro, 3 piedra_clara, 4 azul_techo,
    # 5 gris_oscuro, 6 verde_wgp
    P_ACERO, P_BLANCO, P_AZUL, P_RAMPA, P_TECHO, P_OSCURO, P_VERDE = range(7)
    mg = _MG()
    wt, dt = 7.2, 3.4               # torre: largo (X) y fondo (Y)
    h_t = alto + 3.3                # coronacion de la torre
    n_r = 4                         # tramos de rampa
    for sx in (-1.0, 1.0):
        xc = sx * (a2 + 0.5 * wt)
        x0, x1 = xc - 0.5 * wt, xc + 0.5 * wt
        # 4 postes de esquina + largueros horizontales por nivel + diagonales
        for xp in (x0 + 0.15, x1 - 0.15):
            for yp in (-0.5 * dt + 0.15, 0.5 * dt - 0.15):
                _caja_g(mg, xp - 0.15, xp + 0.15, yp - 0.15, yp + 0.15, 0.0, h_t, P_ACERO,
                        omitir=(0, 2))
        niveles = [alto * k / n_r for k in range(1, n_r + 1)] + [h_t - 0.15]
        for zn in niveles:
            for yp in (-0.5 * dt + 0.15, 0.5 * dt - 0.15):
                _caja_g(mg, x0 + 0.3, x1 - 0.3, yp - 0.06, yp + 0.06, zn - 0.12, zn,
                        P_ACERO, omitir=('x0', 'x1'))
            if abs(zn - alto) < 1e-6:
                continue        # a la altura del pasillo su losa hace de larguero
            # travesanos cortos bajo los rellanos (0.18 m por debajo de su cara)
            for xp in (x0 + 0.15, x1 - 0.15):
                _caja_g(mg, xp - 0.06, xp + 0.06, -0.5 * dt + 0.3, 0.5 * dt - 0.3,
                        zn - 0.30, zn - 0.18, P_ACERO, omitir=(1, 3))
        # diagonales en los costados largos (una por nivel, alternando),
        # recortadas 0.15 m en cada extremo para no solaparse en las esquinas
        z_prev = 0.0
        for k, zn in enumerate(niveles):
            for yp in (-0.5 * dt + 0.15, 0.5 * dt - 0.15):
                xa, xb = (x0 + 0.3, x1 - 0.3) if k % 2 == 0 else (x1 - 0.3, x0 + 0.3)
                za_, zb_ = z_prev + 0.15, zn - 0.12 - 0.15
                dx, dz = xb - xa, zb_ - za_
                ln = math.hypot(dx, dz)
                ux, uz = dx / ln, dz / ln
                px, pz = -uz * 0.05, ux * 0.05
                pts = [(xa + px, yp - 0.04, za_ + pz), (xb + px, yp - 0.04, zb_ + pz),
                       (xb - px, yp - 0.04, zb_ - pz), (xa - px, yp - 0.04, za_ - pz)]
                pts2 = [(p[0], yp + 0.04, p[2]) for p in pts]
                i = mg.verts(pts + pts2)
                c = (0.5 * (xa + xb), yp, 0.5 * (z_prev + zn))
                for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6)):
                    mg.cara([i + j for j in q], P_ACERO, False, centro=c)
            z_prev = zn - 0.12
        # rampas en zigzag: 4 tramos de 5.6 m (subida alto/4 cada uno) en dos
        # carriles (y<0 / y>0) con rellanos de giro en los extremos. El primer
        # tramo arranca en el lado del pasillo (interior) y el ultimo muere en
        # el; ahi el rellano superior es la propia losa del pasillo.
        lr = wt - 1.6
        for k in range(n_r):
            za, zb = alto * k / n_r, alto * (k + 1) / n_r
            lane = -1.0 if k % 2 == 0 else 1.0
            y0r, y1r = (lane * 0.5 * dt - lane * 0.35, lane * 0.1)
            y0r, y1r = min(y0r, y1r), max(y0r, y1r)
            sube_x = (k % 2 == 0) == (sx > 0)
            xa, xb = (x0 + 0.8, x0 + 0.8 + lr) if sube_x else (x1 - 0.8 - lr, x1 - 0.8)
            zA, zB = (za, zb) if sube_x else (zb, za)
            # losa con cara inferior (se ve desde la pista); tapas x0/x1
            # dentro de los rellanos
            _losa(mg, xa, xb, y0r, y1r, zA, zB, 0.12, P_RAMPA, omitir=('x0', 'x1'))
            # peto exterior de 0.55 m (borde hacia fuera de la torre), sigue
            # la pendiente; apoyado en la losa (sin cara inferior) y 2 cm mas
            # corto en cada extremo para no solapar los cantos de rellanos
            # y del peto del pasillo
            yp0, yp1 = (y0r, y0r + 0.06) if lane < 0 else (y1r - 0.06, y1r)
            dz_ = 0.02 * (zB - zA) / (xb - xa)
            _losa(mg, xa + 0.02, xb - 0.02, yp0, yp1, zA + 0.55 + dz_, zB + 0.55 - dz_,
                  0.55, P_BLANCO, omitir=(0,))
            if k == n_r - 1:
                continue
            xl0, xl1 = (xb, xb + 0.8) if sube_x else (xa - 0.8, xa)
            _losa(mg, xl0, xl1, -0.5 * dt + 0.35, 0.5 * dt - 0.35, zb, zb, 0.12, P_RAMPA)
            # peto del rellano en el testero exterior de la torre
            xe0, xe1 = (xl1 - 0.06, xl1) if sube_x else (xl0, xl0 + 0.06)
            _caja_g(mg, xe0, xe1, -0.5 * dt + 0.35, 0.5 * dt - 0.35, zb, zb + 0.55,
                    P_BLANCO, omitir=(0,))
        # rellano de arranque a pie de calle (lado del pasillo)
        xl0, xl1 = (x1 - 0.8, x1 + 0.8) if sx < 0 else (x0 - 0.8, x0 + 0.8)
        _caja_g(mg, xl0, xl1, -0.5 * dt + 0.35, 0.5 * dt - 0.35, 0.0, 0.05, P_RAMPA,
                omitir=(0,))
        # techo de la torre
        _caja_g(mg, x0 - 0.2, x1 + 0.2, -0.5 * dt - 0.2, 0.5 * dt + 0.2, h_t, h_t + 0.2,
                P_TECHO)
    # pasillo: losa, petos, postes, techo
    y0p, y1p = -1.35, 1.35
    _caja_g(mg, -a2 - 0.8, a2 + 0.8, y0p, y1p, alto - 0.3, alto, P_BLANCO)
    for yp0, yp1 in ((y0p, y0p + 0.1), (y1p - 0.1, y1p)):
        _caja_g(mg, -a2 - 0.8, a2 + 0.8, yp0, yp1, alto, alto + 1.05, P_BLANCO, omitir=(0,))
    n_pp = max(2, int(round(luz / 3.6)) + 1)
    for k in range(n_pp):
        xp = -a2 + k * luz / (n_pp - 1)
        for yp in (y0p + 0.08, y1p - 0.08):
            _caja_g(mg, xp - 0.06, xp + 0.06, yp - 0.06, yp + 0.06, alto + 1.05, alto + 2.9,
                    P_ACERO, omitir=(0,))
    _caja_g(mg, -a2 - 0.9, a2 + 0.9, y0p - 0.15, y1p + 0.15, alto + 2.9, alto + 3.05, P_TECHO)
    # bandas de patrocinio a ambos costados (azul con ribete blanco)
    for sy in (-1.0, 1.0):
        yb0 = y1p + 0.12 if sy > 0 else y0p - 0.12
        yb1 = yb0 + 0.06 * sy
        ya, yb = min(yb0, yb1), max(yb0, yb1)
        _caja_g(mg, -a2 + 0.3, a2 - 0.3, ya, yb, alto + 1.25, alto + 2.55, P_BLANCO,
                omitir=(3 if sy > 0 else 1,))
        ya2, yb2 = (yb, yb + 0.03) if sy > 0 else (ya - 0.03, ya)
        _caja_g(mg, -a2 + 0.4, a2 - 0.4, ya2, yb2, alto + 1.35, alto + 2.45, P_AZUL,
                omitir=(3 if sy > 0 else 1,))
    # banderines verdes en las esquinas del techo
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            xq, yq = sx * (a2 + 0.6), sy * 1.3
            _caja_g(mg, xq - 0.03, xq + 0.03, yq - 0.03, yq + 0.03, alto + 3.05,
                    alto + 4.4, P_ACERO, omitir=(0,))
            _caja_g(mg, xq + 0.03, xq + 0.83, yq - 0.01, yq + 0.01, alto + 3.8,
                    alto + 4.35, P_VERDE, omitir=('x0',))
    ob = mg.obj('%s_pasarela_cuerpo' % PRE,
                ('gris_acero', 'blanco', 'azul_oscuro', 'piedra_clara', 'azul_techo',
                 'gris_oscuro', 'verde_wgp'), col, separar=True)
    ob.parent = raiz
    tam = min(0.8, (luz - 2.0) / 16.0 / 0.62)
    y_txt = y1p + 0.12 + 0.06 + 0.03 + 0.02
    tx = _texto_3d('%s_pasarela_texto' % PRE, 'WORLD GRAND PRIX', tam, 'blanco', col,
                   extrude=0.03, pos=(0.0, y_txt, alto + 1.9))
    tx.parent = raiz
    tx2 = _texto_3d('%s_pasarela_texto_dorso' % PRE, 'WORLD GRAND PRIX', tam, 'blanco',
                    col, extrude=0.03, pos=(0.0, -y_txt, alto + 1.9), rot_z=math.pi)
    tx2.parent = raiz
    return raiz


# ------------------------------------------------------------------ escaparate

def build(parent_collection, seed=0, **params):
    """Escaparate del complejo: edificio de boxes (n=20) en el origen, pit
    lane de 12 m delante, muro de boxes (tramos con tapas en los extremos),
    pista de 16 m, torres de control junto a la entrada y la salida del pit
    lane (fuera de el, tras la linea del muro) y pasarela cruzando la pista
    mas alla del final de los boxes, con su torre cercana en el lado del pit
    lane pero fuera de la zona de trabajo. Todo sobre asfalto."""
    col = parent_collection
    raiz = _raiz('%s_kit' % PRE, col)
    n = int(params.get('n', 20))
    w = float(params.get('ancho_box', 6.0))
    L = n * w
    y_f = 0.5 * _FONDO
    y_muro = y_f + 12.0
    y_pista0, y_pista1 = y_muro + 0.5, y_muro + 16.5

    mg = _MG()   # 0 asfalto, 1 blanco, 2 piedra_clara
    _quad(mg, [(-L / 2 - 30, -20, -0.02), (L / 2 + 30, -20, -0.02),
               (L / 2 + 30, y_pista1 + 16, -0.02), (-L / 2 - 30, y_pista1 + 16, -0.02)],
          0, (0, 0, 1))
    _quad(mg, [(-L / 2 - 30, y_pista1, 0.0), (L / 2 + 30, y_pista1, 0.0),
               (L / 2 + 30, y_pista1 + 16, 0.0), (-L / 2 - 30, y_pista1 + 16, 0.0)],
          2, (0, 0, 1))
    for yy in (y_f + 0.5, y_muro - 2.3, y_pista0 + 0.4, y_pista1 - 0.4):
        _quad(mg, [(-L / 2 - 20, yy - 0.08, 0.005), (L / 2 + 20, yy - 0.08, 0.005),
                   (L / 2 + 20, yy + 0.08, 0.005), (-L / 2 - 20, yy + 0.08, 0.005)],
              1, (0, 0, 1))
    for i in range(n):
        cx = -L / 2 + (i + 0.5) * w
        _quad(mg, [(cx - 1.5, y_f + 1.5, 0.005), (cx + 1.5, y_f + 1.5, 0.005),
                   (cx + 1.5, y_f + 1.65, 0.005), (cx - 1.5, y_f + 1.65, 0.005)],
              1, (0, 0, 1))
    suelo = mg.obj('%s_suelo' % PRE, ('asfalto', 'blanco', 'piedra_clara'), col)
    suelo.parent = raiz

    boxes = build_boxes_tribuna(col, n=n, ancho_box=w, seed=seed)
    boxes.parent = raiz

    n_m = max(1, int(round(L / 12.0)))
    for k in range(n_m):
        muro = build_muro_boxes(col, largo=12.0, seed=seed + k, tapa_x0=(k == 0),
                                tapa_x1=(k == n_m - 1))
        muro.location = (-L / 2 + (k + 0.5) * 12.0, y_muro, 0.0)
        muro.parent = raiz

    # torres de control: tras la linea del muro, fuera del pit lane y mas
    # alla de los testeros del edificio (radio 3.9)
    for sx in (-1.0, 1.0):
        torre = build_torre_control(col, alto=16.0, seed=seed)
        torre.location = (sx * (L / 2 + 7.0), y_muro - 4.6, 0.0)
        torre.parent = raiz

    # pasarela (girada 90: su X local es el eje Y del mundo) mas alla de la
    # torre del lado de salida; la torre de celosia cercana queda pegada a la
    # prolongacion del muro (y en [y_muro - 9.5, y_muro - 2.3]), la lejana al
    # otro lado de la pista
    luz_p = 24.0
    pasarela = build_pasarela(col, luz=luz_p, alto=7.0, seed=seed)
    pasarela.location = (L / 2 + 14.0, y_muro - 2.3 + 0.5 * luz_p, 0.0)
    pasarela.rotation_euler = (0.0, 0.0, math.pi / 2)
    pasarela.parent = raiz
    return raiz
