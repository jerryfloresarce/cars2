"""carrera_kit_v2.py — Kit procedural de infraestructura de carrera World Grand
Prix (Porto Corsa, Cars 2) para Blender 5.1.

v2: solo cambia build_tribuna (el resto de piezas es identico a carrera_kit.py).
El publico de la grada son ahora COCHES low-poly (carroceria redondeada +
cabina + ojos en el parabrisas + boca), las gradas son terrazas anchas con
pasillos-rampa ABIERTOS a las terrazas (mundo car-ificado, sin escaleras: la
rampa pasa a ras de cada terraza por su centro, con un diente de sierra verde
en la junta) y la estructura es una cascara limpia de sombreado plano, con
vertices propios por cara (normales partidas) y sin caras coplanares
solapadas: el defecto de "parches triangulares de dos tonos" de la v1 venia
de cajas solapadas crema/blanco en el mismo plano (z-fighting) sobre los
muros laterales. Los muros laterales son bajos (no tapan al publico) y llevan
zocalo de piedra, banda verde inclinada y pilastras; la fachada trasera lleva
zocalo, pilastras, cornisa y portones de acceso para los coches; el techo se
apoya en pilares finos de acero.

Todas las piezas crean sus objetos, los linkan a `parent_collection` y devuelven
el objeto raiz. Unidades en metros, base en z=0, fachada principal mirando a +Y.
Materiales Principled BSDF de color plano, reutilizados por nombre.

Piezas del kit:
- build_tribuna(parent, largo=40, filas=12, seed=0): grada techada llena de
  coches-espectador (ojos en el parabrisas, mirando a la pista = +Y).
  Opcionales por **params: ocupacion=0.9, max_tris=16000, banderas=True.
  Hijos: CARRERA_tribuna_estructura, CARRERA_tribuna_techo,
  CARRERA_tribuna_publico (raiz: Empty CARRERA_tribuna). Huella (bbox):
  x en [-largo/2-0.05, largo/2+0.05] (la v1 media +-(largo/2+0.8) por el
  vuelo lateral del techo), y en [-filas*0.85-0.03, filas*0.85+0.18] (como la
  v1). El semiancho largo/2+0.05 es deliberado: el zocalo que genera el
  integrador (bbox - 0.2 m) cae asi en mitad del espesor del muro lateral
  (0.30 m), sin z-fighting con su cara exterior ni hueco visible.
- build_portico_meta(parent, ancho=20): portico sobre la pista con panel
  "MONDIALE GRAND PRIX" (texto 3D), banda de cuadros y semaforo de salida.
- build_pantalla(parent): pantalla gigante ~12x7 m sobre torre.
- build_boxes(parent, n=12): edificio de pit lane con n boxes numerados,
  portones, terraza y muro de pits.
- build_muro_valla(parent, largo=10): muro bajo blanco + valla de captura
  (postes y barrotes finos), pensado para repetir a lo largo de la pista.
- build_valla_publicitaria(parent, largo=8, texto='ALLINOL'): panel
  publicitario verde/blanco con texto 3D.
- build_paca(parent): pila de balas de paja con flejes.
- build(parent_collection, seed=0): vineta completa (portico + tribuna +
  boxes + pantalla + muros + vallas + pacas sobre asfalto con linea de meta).
"""

import math
import random

import bpy

PRE = 'CARRERA'

# ------------------------------------------------------------------ materiales

# clave: (color, roughness, metallic, color_emision | None, fuerza_emision)
_PALETA = {
    'blanco':        ((0.92, 0.90, 0.86), 0.55, 0.0, None, 0.0),
    'crema':         ((0.95, 0.86, 0.62), 0.60, 0.0, None, 0.0),
    'ocre':          ((0.86, 0.54, 0.20), 0.65, 0.0, None, 0.0),
    'terracota':     ((0.62, 0.25, 0.12), 0.70, 0.0, None, 0.0),
    'verde_wgp':     ((0.04, 0.58, 0.18), 0.45, 0.0, None, 0.0),
    'verde_oscuro':  ((0.05, 0.22, 0.11), 0.50, 0.0, None, 0.0),
    'gris_acero':    ((0.30, 0.33, 0.36), 0.40, 0.6, None, 0.0),
    'gris_oscuro':   ((0.09, 0.09, 0.10), 0.60, 0.0, None, 0.0),
    'negro':         ((0.02, 0.02, 0.02), 0.60, 0.0, None, 0.0),
    'asfalto':       ((0.13, 0.13, 0.14), 0.90, 0.0, None, 0.0),
    'piedra_clara':  ((0.58, 0.52, 0.40), 0.85, 0.0, None, 0.0),
    'azul_oscuro':   ((0.02, 0.05, 0.15), 0.40, 0.0, None, 0.0),
    'paja':          ((0.85, 0.62, 0.20), 0.80, 0.0, None, 0.0),
    'paja_oscura':   ((0.48, 0.32, 0.10), 0.80, 0.0, None, 0.0),
    'rojo_luz':      ((0.85, 0.04, 0.02), 0.40, 0.0, (1.0, 0.04, 0.02), 6.0),
    'pantalla_luz':  ((0.04, 0.12, 0.40), 0.30, 0.0, (0.28, 0.55, 1.00), 2.6),
    'cabina':        ((0.28, 0.44, 0.55), 0.20, 0.0, None, 0.0),
    'pub_rojo':      ((0.80, 0.08, 0.06), 0.50, 0.0, None, 0.0),
    'pub_azul':      ((0.08, 0.22, 0.78), 0.50, 0.0, None, 0.0),
    'pub_amarillo':  ((0.95, 0.72, 0.08), 0.50, 0.0, None, 0.0),
    'pub_verde':     ((0.10, 0.58, 0.16), 0.50, 0.0, None, 0.0),
    'pub_naranja':   ((0.90, 0.36, 0.04), 0.50, 0.0, None, 0.0),
    'pub_morado':    ((0.42, 0.09, 0.58), 0.50, 0.0, None, 0.0),
    'pub_cian':      ((0.08, 0.62, 0.68), 0.50, 0.0, None, 0.0),
    'pub_blanco':    ((0.90, 0.90, 0.88), 0.50, 0.0, None, 0.0),
    # --- v2: cristal MATE de los coches-espectador (el 'cabina' de la v1, con
    # roughness 0.20, deslumbraba y borraba los ojos del parabrisas)
    'pub_cristal':   ((0.20, 0.33, 0.45), 0.65, 0.0, None, 0.0),
}

_PUBLICO = ('pub_rojo', 'pub_azul', 'pub_amarillo', 'pub_verde',
            'pub_naranja', 'pub_morado', 'pub_cian', 'pub_blanco')


def _mat(clave):
    """Crea (o reutiliza) el material MAT_CARRERA_<clave> de la paleta."""
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

class _MB:
    """Acumulador de cajas/quads que produce una unica malla multi-material."""

    def __init__(self):
        self.v = []
        self.f = []
        self.fm = []

    def caja(self, centro, dim, mat=0, rz=0.0):
        cx, cy, cz = centro
        hx, hy, hz = dim[0] / 2.0, dim[1] / 2.0, dim[2] / 2.0
        base = len(self.v)
        c, s = math.cos(rz), math.sin(rz)
        for dx, dy, dz in ((-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz),
                           (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz),
                           (hx, hy, hz), (-hx, hy, hz)):
            self.v.append((cx + dx * c - dy * s, cy + dx * s + dy * c, cz + dz))
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f.append((base + q[0], base + q[1], base + q[2], base + q[3]))
            self.fm.append(mat)

    def obj(self, nombre, claves_mat, col):
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(self.v, [], self.f)
        for clave in claves_mat:
            me.materials.append(_mat(clave))
        for p, mi in zip(me.polygons, self.fm):
            p.material_index = mi
        me.validate()
        ob = bpy.data.objects.new(nombre, me)
        col.objects.link(ob)
        return ob


def _raiz(nombre, col):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_size = 0.5
    col.objects.link(e)
    return e


def _texto_3d(nombre, texto, tam, clave_mat, col, extrude=0.05):
    """Texto 3D via curva FONT convertida a malla, centrado en su origen y
    puesto de pie mirando a +Y (legible desde +Y). Solo falta ubicarlo."""
    cu = bpy.data.curves.new(nombre + '_cu', type='FONT')
    cu.body = texto
    cu.size = tam
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.resolution_u = 3
    tmp = bpy.data.objects.new(nombre + '_tmp', cu)
    col.objects.link(tmp)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(deps))
    me.name = nombre
    me.materials.clear()
    me.materials.append(_mat(clave_mat))
    ob = bpy.data.objects.new(nombre, me)
    # de pie y legible desde +Y (girar el cartel, no espejarlo)
    ob.rotation_euler = (math.radians(90), 0.0, math.pi)
    col.objects.link(ob)
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    return ob


# ------------------------------------------- v2: malla generica para la tribuna

def _normal_newell(pts):
    """Normal (sin normalizar) de un poligono 3D por el metodo de Newell."""
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
    """Malla generica (v2): poligonos arbitrarios con material y sombreado
    plano/suave POR CARA. Cada cara se orienta hacia fuera segun `ref`
    (direccion deseada de la normal) o `centro` (punto interior del solido)."""

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
            # vertices propios por cara (normales partidas "de fabrica"): aunque
            # aguas abajo alguien active el suavizado, los planos grandes no
            # pueden interpolar normales con sus vecinos
            v, f = [], []
            for cara in self.f:
                i0 = len(v)
                v.extend(self.v[i] for i in cara)
                f.append(tuple(range(i0, i0 + len(cara))))
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(v, [], f)
        for clave in claves_mat:
            me.materials.append(_mat(clave))
        # sombreado explicito por cara: plano en estructura, suave solo donde
        # se pide (carrocerias). Nada de normales personalizadas.
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
    Caras: 'x0' y 'x1' (tapas) + una por arista k (perfil[k] -> perfil[k+1]).
    `omitir`: tapas/aristas que no se generan (caras ocultas); `mats`: material
    por tapa/arista; `tf`: transformacion opcional de cada punto (x, y, z)."""
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
    """Caja alineada a ejes via _prisma_x. Aristas: 0 = suelo (z0), 1 = cara
    +Y (y1), 2 = techo (z1), 3 = cara -Y (y0); tapas 'x0' / 'x1'."""
    _prisma_x(mg, x0, x1, [(y0, z0), (y1, z0), (y1, z1), (y0, z1)], mat,
              omitir=omitir, mats=mats, tf=tf)


# ------------------------------------------------ v2: coches-espectador (publico)

# (peso, f_ancho, f_largo, alto, parabrisas_base, parabrisas_techo, techo_tras,
#  luneta_base [fracciones de L, +Y = morro], z_capo_delante, z_maletero)
_PUB_TIPOS = (
    (5, 1.00, 1.00, 1.00, 0.20, 0.03, -0.30, -0.43, 0.52, 0.60),   # berlina
    (3, 1.07, 1.03, 0.86, 0.12, -0.10, -0.30, -0.44, 0.47, 0.56),  # deportivo
    (2, 0.95, 1.00, 1.20, 0.35, 0.24, -0.40, -0.45, 0.56, 0.62),   # furgoneta
    (3, 0.92, 0.92, 1.04, 0.17, 0.02, -0.26, -0.42, 0.54, 0.57),   # utilitario
)
_PUB_PESOS_TIPO = tuple(t[0] for t in _PUB_TIPOS)
# pesos de color en el orden de _PUBLICO (rojo, azul, amarillo, verde, naranja,
# morado, cian, blanco)
_PUB_PESOS_COLOR = (5, 4, 4, 3, 3, 2, 2, 3)

# indices de material de la malla de publico (11 materiales: el blanco del ojo
# reutiliza 'pub_blanco' y los faros 'crema' para ahorrar draw calls)
_PUB_MATS = ('pub_cristal',) + _PUBLICO + ('negro', 'crema')
_PM_CRISTAL = 0
_PM_PILOTO = 1 + _PUBLICO.index('pub_rojo')
_PM_OJO = 1 + _PUBLICO.index('pub_blanco')
_PM_NEGRO = 1 + len(_PUBLICO)
_PM_FARO = 2 + len(_PUBLICO)
_PUB_TRIS_MAX = 90   # cota superior de triangulos por coche-espectador

_ANG8 = tuple(math.pi / 8.0 + k * math.pi / 4.0 for k in range(8))
_ANG6 = tuple(k * math.pi / 3.0 for k in range(6))


def _pub_coche(mg, pos, rz, W, L, e, tipo, mi, mirada, boca_abierta):
    """Anade a `mg` un coche-espectador low-poly (~89 tris) con el morro hacia
    +Y local: carroceria redondeada (3 anillos octogonales, sombreado suave),
    cabina del color del coche con parabrisas y luneta de cristal mate, dos
    ojos blancos con pupila en el parabrisas, faros, pilotos, boca y dos ejes
    de ruedas cerrados por arriba.
    pos = (x, y, z del suelo); rz = giro; W, L = ancho y largo; e = escala de
    alturas; mirada = (du, dv) en [-1, 1] desplazamiento de las pupilas."""
    x, y, z = pos
    H = tipo[3] * e
    yb_f, yt_f, yt_r, yb_r = tipo[4] * L, tipo[5] * L, tipo[6] * L, tipo[7] * L
    zc_f, zc_r = tipo[8] * e, tipo[9] * e
    co, si = math.cos(rz), math.sin(rz)

    def T(p):
        return (x + p[0] * co - p[1] * si, y + p[0] * si + p[1] * co, z + p[2])

    def R(v):
        return (v[0] * co - v[1] * si, v[0] * si + v[1] * co, v[2])

    def anillo(hw, yf, yr, ch, zf, zr):
        plan = ((hw, yf - ch), (hw - ch, yf), (-(hw - ch), yf), (-hw, yf - ch),
                (-hw, yr + ch), (-(hw - ch), yr), (hw - ch, yr), (hw, yr + ch))
        return [(px, py, zr + (zf - zr) * (py - yr) / (yf - yr)) for px, py in plan]

    # --- carroceria: faldon, cintura y borde de capo/maletero
    r0 = anillo(0.46 * W, 0.465 * L, -0.465 * L, 0.10 * e, 0.14 * e, 0.14 * e)
    r1 = anillo(0.50 * W, 0.500 * L, -0.500 * L, 0.21 * e, 0.37 * e, 0.43 * e)
    r2 = anillo(0.43 * W, 0.440 * L, -0.450 * L, 0.17 * e, zc_f, zc_r)
    i0 = mg.verts([T(p) for p in r0 + r1 + r2])
    cb = T((0.0, 0.0, 0.33 * e))
    for k in (0, 1):
        for j in range(8):
            j2 = (j + 1) % 8
            m = mi
            if k == 1 and j in (0, 2):
                m = _PM_FARO          # chaflanes delanteros = faros
            elif k == 1 and j in (4, 6):
                m = _PM_PILOTO        # chaflanes traseros = pilotos
            mg.cara((i0 + 8 * k + j, i0 + 8 * k + j2,
                     i0 + 8 * (k + 1) + j2, i0 + 8 * (k + 1) + j),
                    m, True, centro=cb)
    # capo + maletero: plano (un n-gono suavizado daria parches triangulares)
    mg.cara([i0 + 16 + j for j in range(8)], mi, False, ref=(0.0, 0.0, 1.0))

    # --- cabina (hundida 5 cm en la carroceria)
    z_cb = min(zc_f, zc_r) - 0.05 * e
    hb, ht = 0.41 * W, 0.31 * W
    cab = [(hb, yb_f, z_cb), (-hb, yb_f, z_cb), (-hb, yb_r, z_cb), (hb, yb_r, z_cb),
           (ht, yt_f, H), (-ht, yt_f, H), (-ht, yt_r, H), (ht, yt_r, H)]
    i1 = mg.verts([T(p) for p in cab])
    cc = T((0.0, 0.5 * (yb_f + yb_r), 0.5 * (z_cb + H)))
    # parabrisas y luneta de cristal; los costados van del color del coche para
    # que desde la pista (vista oblicua) domine el color saturado, no el gris
    for a, b, m in ((0, 1, _PM_CRISTAL), (1, 2, mi), (2, 3, _PM_CRISTAL), (3, 0, mi)):
        mg.cara((i1 + a, i1 + b, i1 + 4 + b, i1 + 4 + a), m, False, centro=cc)
    mg.cara((i1 + 4, i1 + 5, i1 + 6, i1 + 7), mi, False, ref=(0.0, 0.0, 1.0))

    # --- ojos sobre el parabrisas (plano u = X, v = a lo largo de la pendiente)
    ty, tz = yt_f - yb_f, H - z_cb
    sl = math.hypot(ty, tz)
    ty, tz = ty / sl, tz / sl
    nl = (0.0, tz, -ty)                 # normal exterior del parabrisas
    nw = R(nl)
    v_c = 0.57 * sl
    hw_v = hb + (ht - hb) * 0.57
    u_c = 0.5 * (hw_v - 0.01)
    ru = min(0.215 * e, u_c - 0.015)
    rv = min(0.215 * e, 0.36 * sl)
    rp = 0.47 * min(ru, rv)

    def P(u, v, off):
        return T((u, yb_f + ty * v + nl[1] * off, z_cb + tz * v + nl[2] * off))

    du = max(-1.0, min(1.0, mirada[0]))
    dv = max(-1.0, min(1.0, mirada[1]))
    for sx in (-1.0, 1.0):
        ue = sx * u_c
        # calcomanias a 4 / 7 cm del cristal: sin titileo de profundidad a >150 m
        ie = mg.verts([P(ue + ru * math.cos(a), v_c + rv * math.sin(a), 0.04)
                       for a in _ANG8])
        mg.cara(range(ie, ie + 8), _PM_OJO, False, ref=nw)
        pu = ue + du * (ru - rp - 0.012)
        pv = v_c + dv * (rv - rp - 0.012)
        ip = mg.verts([P(pu + rp * math.cos(a), pv + rp * math.sin(a), 0.07)
                       for a in _ANG6])
        mg.cara(range(ip, ip + 6), _PM_NEGRO, False, ref=nw)

    # --- boca en el morro (entre faldon y cintura), 4 cm por delante
    ym0, zm0 = 0.465 * L, 0.14 * e
    ym1, zm1 = 0.500 * L, 0.37 * e
    ml = math.hypot(ym1 - ym0, zm1 - zm0)
    nb = ((zm1 - zm0) / ml, -(ym1 - ym0) / ml)      # normal (y, z) del morro

    def B(u, w):
        return T((u, ym0 + (ym1 - ym0) * w + nb[0] * 0.04,
                  zm0 + (zm1 - zm0) * w + nb[1] * 0.04))

    refb = R((0.0, 1.0, 0.0))
    m_ = 0.27 * W
    if boca_abierta:
        ib = mg.verts([B(-m_, 0.84), B(m_, 0.84), B(0.82 * m_, 0.50),
                       B(0.42 * m_, 0.20), B(-0.42 * m_, 0.20), B(-0.82 * m_, 0.50)])
        mg.cara(range(ib, ib + 6), _PM_NEGRO, False, ref=refb)
    else:
        ib = mg.verts([B(-m_, 0.86), B(-0.5 * m_, 0.52), B(0.5 * m_, 0.52), B(m_, 0.86),
                       B(-m_, 0.64), B(-0.5 * m_, 0.28), B(0.5 * m_, 0.28), B(m_, 0.64)])
        for a in range(3):
            mg.cara((ib + a, ib + a + 1, ib + a + 5, ib + a + 4), _PM_NEGRO,
                    False, ref=refb)

    # --- ruedas: dos ejes-caja que asoman por los bajos, cerrados por arriba
    # (con backface culling, sin tapa se veian como aletas de papel desde
    # camaras altas). Solo faltan el suelo y las caras que miran al otro eje.
    hwr = 0.5 * W + 0.03
    rr = 0.18 * e
    zr_ = 0.37 * e
    for ya, delante in ((0.29 * L, True), (-0.29 * L, False)):
        ia = mg.verts([T(p) for p in (
            (-hwr, ya - rr, 0.0), (hwr, ya - rr, 0.0), (hwr, ya + rr, 0.0),
            (-hwr, ya + rr, 0.0), (-hwr, ya - rr, zr_), (hwr, ya - rr, zr_),
            (hwr, ya + rr, zr_), (-hwr, ya + rr, zr_))])
        mg.cara((ia, ia + 3, ia + 7, ia + 4), _PM_NEGRO, False, ref=R((-1.0, 0.0, 0.0)))
        mg.cara((ia + 1, ia + 2, ia + 6, ia + 5), _PM_NEGRO, False, ref=R((1.0, 0.0, 0.0)))
        mg.cara((ia + 4, ia + 5, ia + 6, ia + 7), _PM_NEGRO, False, ref=(0.0, 0.0, 1.0))
        if delante:
            mg.cara((ia + 3, ia + 2, ia + 6, ia + 7), _PM_NEGRO, False,
                    ref=R((0.0, 1.0, 0.0)))
        else:
            mg.cara((ia, ia + 1, ia + 5, ia + 4), _PM_NEGRO, False,
                    ref=R((0.0, -1.0, 0.0)))


# ------------------------------------------------------------------ las piezas

def build_tribuna(parent_collection, largo=40, filas=12, seed=0, **params):
    """Grada techada llena de coches-espectador (v2).

    Terrazas anchas (una por fila) con pasillos-rampa laterales y centrales
    abiertos a las terrazas (junta en diente de sierra verde), muros laterales
    bajos con albardilla verde, zocalo, banda y pilastras, muro trasero con
    bocas de acceso, techo con vigas, pilares finos de acero y banderas. El
    publico son coches low-poly con ojos en el parabrisas mirando a la pista
    (+Y).
    **params opcionales: ocupacion (0..1, def. 0.9), max_tris (def. 16000),
    banderas (def. True)."""
    col = parent_collection
    raiz = _raiz('%s_tribuna' % PRE, col)
    rng = random.Random(seed)

    largo = float(largo)
    filas = max(1, int(filas))
    ocupacion = float(params.get('ocupacion', 0.9))
    max_tris = int(params.get('max_tris', 16000))
    banderas = bool(params.get('banderas', True))

    alto = 0.75                      # subida por fila
    base = 0.6                       # altura de la primera terraza
    fondo = filas * 1.7              # misma huella que la v1
    a2 = largo / 2.0
    y_b = -fondo / 2.0               # trasera
    y_0 = fondo / 2.0 + 0.18         # frente del faldon (como la v1)
    y_t0 = y_0 - 0.14                # frente de la primera terraza
    y_w = y_b + 0.45                 # cara delantera del muro trasero
    prof = (y_t0 - y_w) / filas      # fondo de cada terraza (~1.67 m)
    h_top = base + (filas - 1) * alto
    z_r0 = h_top + 2.4               # arranque trasero del techo
    z_wt = z_r0 + 0.08               # coronacion del muro trasero (dentro del techo)

    # ---- reparto en X: muros laterales, rampas y bloques de grada. g_div es la
    # franja de terraza libre entre cada bloque de publico y su pasillo (en la
    # primera v2 era un tabique; ahora la junta es abierta)
    g_lat, g_div, w_rampa, w_pas = 0.30, 0.22, 2.3, 2.4
    hay_rampas = largo >= 16.0
    bloques, calles = [], []
    if hay_rampas:
        n_bl = max(1, int(round(largo / 22.0)))
        x_in = a2 - g_lat - w_rampa - g_div
        wb = (2.0 * x_in - (n_bl - 1) * (w_pas + 2.0 * g_div)) / n_bl
        calles.append((-a2 + g_lat, -a2 + g_lat + w_rampa))
        for k in range(n_bl):
            xa = -x_in + k * (wb + w_pas + 2.0 * g_div)
            xb = xa + wb
            bloques.append((xa, xb))
            if k < n_bl - 1:
                calles.append((xb + g_div, xb + g_div + w_pas))
        calles.append((a2 - g_lat - w_rampa, a2 - g_lat))
    else:
        bloques.append((-a2 + g_lat, a2 - g_lat))

    # ================================================================ estructura
    # Cascara limpia: sin caras coplanares solapadas y toda de sombreado plano.
    C_CREMA, C_VERDE, C_BLANCO, C_RAMPA, C_OSCURO = 0, 1, 2, 3, 4
    me = _MG()

    # faldon frontal verde continuo (su cara trasera hace de tope de la 1a fila).
    # Sus testeros van 1 cm metidos para no ser coplanares con la cara exterior
    # de los muros laterales (que arrancan 5 cm dentro del faldon).
    _caja_g(me, -a2 + 0.01, a2 - 0.01, y_t0, y_0, 0.0, base + 0.2, C_VERDE,
            omitir=(0,))
    # remate blanco del faldon
    _caja_g(me, -a2 + 0.02, a2 - 0.02, y_t0, y_0 - 0.04,
            base + 0.2, base + 0.27, C_BLANCO, omitir=(0,))

    # terrazas (huella crema + contrahuella blanca), una tira por bloque. Con
    # pasillos-rampa la tira llega justo hasta el borde del pasillo (junta
    # abierta, sin tabique: los coches pasan de la rampa a su terraza); sin
    # pasillos entra 5 cm en los muros laterales.
    ext = g_div if hay_rampas else 0.05
    for xa, xb in bloques:
        x0, x1 = xa - ext, xb + ext
        for i in range(filas):
            zf = base + i * alto
            yf = y_t0 - i * prof
            yr = yf - prof
            iv = me.verts([(x0, yr, zf), (x1, yr, zf), (x1, yf, zf), (x0, yf, zf)])
            me.cara((iv, iv + 1, iv + 2, iv + 3), C_CREMA, False, ref=(0, 0, 1))
            if i > 0:
                iv = me.verts([(x0, yf, zf - alto), (x1, yf, zf - alto),
                               (x1, yf, zf), (x0, yf, zf)])
                me.cara((iv, iv + 1, iv + 2, iv + 3), C_BLANCO, False, ref=(0, 1, 0))

    # pasillos-rampa: rellano delantero, rampa por el centro de cada terraza
    # y rellano superior hasta las bocas del muro trasero
    yc0 = y_t0 - 0.5 * prof
    ycl = y_w + 0.5 * prof
    for k, (xa, xb) in enumerate(calles):
        # contra un muro lateral entra 5 cm en el; contra un bloque acaba
        # exactamente en la junta con las terrazas
        x0 = xa - 0.05 if k == 0 else xa
        x1 = xb + 0.05 if k == len(calles) - 1 else xb
        tramos = [((y_t0, base), (yc0, base))]
        if filas > 1:
            tramos.append(((yc0, base), (ycl, h_top)))
        tramos.append(((ycl, h_top), (y_w, h_top)))
        for (ya_, za_), (yb_, zb_) in tramos:
            iv = me.verts([(x0, ya_, za_), (x1, ya_, za_), (x1, yb_, zb_), (x0, yb_, zb_)])
            me.cara((iv, iv + 1, iv + 2, iv + 3), C_RAMPA, False, ref=(0, 0, 1))
        # boca de acceso (vomitorio) al fondo de cada pasillo
        _caja_g(me, xa + 0.25, xb - 0.25, y_w - 0.05, y_w + 0.14,
                h_top - 0.05, h_top + 1.5, C_BLANCO, omitir=(0, 3),
                mats={1: C_OSCURO})

    # junta abierta rampa / terrazas (sin tabiques: no tapan al publico y cada
    # fila es accesible). La rampa pasa a ras de cada terraza por su centro;
    # delante queda por debajo y detras por encima: dos triangulos verdes por
    # terraza cierran el escalon (diente de sierra decorativo).
    if hay_rampas and filas > 1:
        for xa, xb in bloques:
            for xj, sg in ((xa - g_div, -1.0), (xb + g_div, 1.0)):
                for i in range(filas):
                    zf = base + i * alto
                    yf = y_t0 - i * prof
                    yr = yf - prof
                    ym = 0.5 * (yf + yr)
                    if i > 0:            # terraza por encima de la rampa: mira al pasillo
                        iv = me.verts([(xj, yf, zf - 0.5 * alto), (xj, yf, zf),
                                       (xj, ym, zf)])
                        me.cara((iv, iv + 1, iv + 2), C_VERDE, False,
                                ref=(sg, 0.0, 0.0))
                    if i < filas - 1:    # rampa por encima de la terraza: mira al bloque
                        iv = me.verts([(xj, ym, zf), (xj, yr, zf + 0.5 * alto),
                                       (xj, yr, zf)])
                        me.cara((iv, iv + 1, iv + 2), C_VERDE, False,
                                ref=(-sg, 0.0, 0.0))

    # muros laterales inclinados (trapecio convexo) con albardilla verde. BAJOS:
    # su coronacion sigue la linea de narices de las terrazas + c (antes subian
    # 1.3 m y desde la pista tapaban al publico).
    y_d0 = y_t0 + 0.05               # arrancan 5 cm dentro del faldon
    pend = alto / prof if filas > 1 else 0.0
    c_ext, cop = 0.26, 0.12
    z_zoc = 0.7                      # zocalo de piedra (laterales y trasera)

    def z_linea(yy, c):
        return base + c + (y_t0 - yy) * pend

    def muro_inclinado(x0, x1, c, vuelo_izq, vuelo_der):
        zf, zb = z_linea(y_d0, c), z_linea(y_w, c)
        # cuerpo: sin suelo, sin trasera (contra el muro) y sin coronacion
        # (la tapa la albardilla)
        _prisma_x(me, x0, x1, [(y_w, 0.0), (y_d0, 0.0), (y_d0, zf), (y_w, zb)],
                  C_BLANCO, omitir=(0, 2, 3))
        _prisma_x(me, x0 - vuelo_izq, x1 + vuelo_der,
                  [(y_w, zb), (y_d0, zf), (y_d0, zf + cop), (y_w, zb + cop)],
                  C_VERDE, omitir=(3,))

    muro_inclinado(-a2, -a2 + g_lat, c_ext, 0.0, 0.08)
    muro_inclinado(a2 - g_lat, a2, c_ext, 0.08, 0.0)

    # detalle de los panos laterales exteriores (lo que mas se ve al acercarse
    # por la recta): zocalo de piedra, banda verde paralela a la albardilla y
    # pilastras de piedra. Todo en relieve (5 / 4 / 2.5 cm) sobre la cara del
    # muro, sin caras interiores y sin solapes coplanares.
    d_b0, d_b1 = 0.30, 0.65          # la banda va de 0.30 a 0.65 m bajo la coronacion

    def z_blo(yy):
        return z_linea(yy, c_ext - d_b1)

    for sx in (-1.0, 1.0):
        def tramo_x(d, sx=sx):
            if sx > 0:
                return a2, a2 + d, 'x0'
            return -a2 - d, -a2, 'x1'

        xq0, xq1, tapa = tramo_x(0.05)
        _caja_g(me, xq0, xq1, y_b, y_d0, 0.0, z_zoc, C_RAMPA, omitir=(0, tapa))
        if pend <= 0.0 or z_blo(y_b) < z_zoc + 1.0:
            continue
        # banda verde recortada contra el zocalo (nace de el)
        y_a = y_t0 - (z_zoc - base - (c_ext - d_b1)) / pend
        y_p = y_t0 - (z_zoc - base - (c_ext - d_b0)) / pend
        xq0, xq1, tapa = tramo_x(0.04)
        y_r = y_b + 0.05             # plano de la cara trasera del muro
        _prisma_x(me, xq0, xq1,
                  [(y_r, z_blo(y_r)), (y_a, z_zoc), (y_p, z_zoc),
                   (y_r, z_linea(y_r, c_ext - d_b0))],
                  C_VERDE, omitir=(1, tapa))
        # pilastras: esquina trasera + tres repartidas, del zocalo a la banda
        xq0, xq1, tapa = tramo_x(0.025)
        tramos_p = [(y_r, y_r + 0.55)]
        for f in (0.25, 0.5, 0.75):
            yc_ = y_w + f * (y_d0 - y_w)
            tramos_p.append((yc_ - 0.3, yc_ + 0.3))
        for ya_, yb_ in tramos_p:
            if z_blo(yb_) - z_zoc < 0.6:
                continue
            _prisma_x(me, xq0, xq1,
                      [(ya_, z_zoc), (yb_, z_zoc), (yb_, z_blo(yb_)), (ya_, z_blo(ya_))],
                      C_RAMPA, omitir=(0, 2, tapa))

    # muro trasero hasta el techo + banda verde por detras
    _caja_g(me, -a2, a2, y_b + 0.05, y_w, 0.0, z_wt, C_BLANCO, omitir=(0,))
    # posiciones de las vigas del techo (tambien marcan las pilastras traseras)
    n_v = max(2, int(round(largo / 7.5)) + 1)
    xs_v = [-(a2 - 0.6) + k * (2.0 * (a2 - 0.6)) / (n_v - 1) for k in range(n_v)]
    if largo > 3.0:
        _caja_g(me, -a2 + 0.5, a2 - 0.5, y_b, y_b + 0.10,
                z_wt - 2.3, z_wt - 1.2, C_VERDE, omitir=(1,))
        # fachada trasera: portones oscuros de acceso (uno por pasillo-rampa),
        # zocalo de piedra entre portones, pilastras de piedra (esquinas + una
        # bajo cada viga interior) y cornisa de piedra bajo la banda verde.
        # Todo sobresale 5 cm del muro (y_b) y nunca se solapa en el mismo plano.
        z_por = min(2.7, z_wt - 2.6)
        portones = [(xa + 0.2, xb - 0.2) for xa, xb in calles] if z_por > 1.2 else []
        hay_pilas = z_wt - 2.5 > z_por + 0.5
        for k, (xp0, xp1) in enumerate(portones):
            om = [0, 1]
            # jamba exterior de los portones extremos: pegada a la pilastra de
            # esquina (oculta y coplanar con su testero) -> no se genera
            if hay_pilas and k == 0 and abs(xp0 - (-a2 + 0.5)) < 0.005:
                om.append('x0')
            if hay_pilas and k == len(portones) - 1 and abs(xp1 - (a2 - 0.5)) < 0.005:
                om.append('x1')
            _caja_g(me, xp0, xp1, y_b, y_b + 0.05, 0.0, z_por, C_BLANCO,
                    omitir=tuple(om), mats={3: C_OSCURO})
        cortes = [-a2] + [x for par in portones for x in par] + [a2]
        for k in range(0, len(cortes), 2):
            om = [0, 1]
            if k > 0:
                om.append('x0')          # testero pegado a un porton: oculto
            if k + 2 < len(cortes):
                om.append('x1')
            _caja_g(me, cortes[k], cortes[k + 1], y_b, y_b + 0.05, 0.0, z_zoc,
                    C_RAMPA, omitir=tuple(om))
        if hay_pilas:
            # cornisa: las pilastras mueren 1 cm dentro de ella
            _caja_g(me, -a2, a2, y_b - 0.03, y_b + 0.05, z_wt - 2.50, z_wt - 2.32,
                    C_RAMPA, omitir=(1,))
            pilas = [(-a2, -a2 + 0.5), (a2 - 0.5, a2)]       # esquinas
            pilas += [(xv - 0.3, xv + 0.3) for xv in xs_v[1:-1]]
            for xq0, xq1 in pilas:
                z_p0 = z_zoc
                solapes = [(xp0, xp1) for xp0, xp1 in portones
                           if min(xq1, xp1) - max(xq0, xp0) > 0.01]
                if solapes:
                    xp0, xp1 = solapes[0]
                    if xq0 < xp0 - 0.01 or xq1 > xp1 + 0.01:
                        continue         # pisa una jamba a medias: se omite
                    z_p0 = z_por         # entera sobre el porton: nace del dintel
                _caja_g(me, xq0, xq1, y_b, y_b + 0.05, z_p0, z_wt - 2.49,
                        C_RAMPA, omitir=(0, 1, 2))

    estructura = me.obj('%s_tribuna_estructura' % PRE,
                        ('crema', 'verde_wgp', 'blanco', 'piedra_clara',
                         'gris_oscuro'), col, separar=True)
    estructura.parent = raiz

    # ===================================================================== techo
    # Voladizo inclinado 7 grados (borde delantero alto). Se construye ya girado
    # (objeto sin rotacion) pivotando en la arista trasera inferior.
    T_VERDE, T_BLANCO, T_ACERO, T_ROJO = 0, 1, 2, 3
    mt = _MG()
    ang = math.radians(7.0)
    ca, sa = math.cos(ang), math.sin(ang)

    def giro(p):
        dy, dz = p[1] - y_b, p[2] - z_r0
        return (p[0], y_b + dy * ca - dz * sa, z_r0 + dy * sa + dz * ca)

    d_r = fondo * 0.87
    # semiancho total = a2 + 0.05 (frontis), igual que el relieve de los panos
    # laterales: el zocalo del integrador (bbox - 0.2) queda en a2 - 0.15, en
    # mitad del espesor del muro lateral. NO ensanchar sin revisar eso.
    xr = a2 + 0.02
    _caja_g(mt, -xr, xr, y_b, y_b + d_r, z_r0, z_r0 + 0.22, T_VERDE, tf=giro)
    # frontis blanco (tapa el canto delantero de la losa)
    _caja_g(mt, -xr - 0.03, xr + 0.03, y_b + d_r - 0.22, y_b + d_r + 0.08,
            z_r0 - 0.42, z_r0 + 0.34, T_BLANCO, tf=giro)
    # vigas de canto variable bajo la losa (nacen dentro del muro trasero)
    for xv in xs_v:
        _prisma_x(mt, xv - 0.16, xv + 0.16,
                  [(y_b + 0.2, z_r0 - 0.85), (y_b + d_r - 0.5, z_r0 - 0.20),
                   (y_b + d_r - 0.5, z_r0 + 0.06), (y_b + 0.2, z_r0 + 0.06)],
                  T_BLANCO, omitir=(2,), tf=giro)
    # banderas tricolores sobre el frontis (paneles con grosor: sin caras
    # coplanares opuestas)
    if banderas:
        for k, xv in enumerate(xs_v):
            if k % 2 == 1 and n_v > 3:
                continue
            # mastil desplazado para que la bandera (1.38 m) quede centrada en
            # la viga, y acotado para que mastil y bandera no se salgan de la
            # losa en los extremos
            x_m = max(-a2 + 0.10, min(a2 - 1.42, xv - 0.73))
            pie = giro((x_m, y_b + d_r - 0.07, z_r0 + 0.30))
            xp, yp, zp = pie
            zt = zp + 2.5
            _caja_g(mt, xp - 0.04, xp + 0.04, yp - 0.04, yp + 0.04, zp, zt,
                    T_ACERO, omitir=(0,))
            for s_, cm in enumerate((T_VERDE, T_BLANCO, T_ROJO)):
                xa_ = xp + 0.04 + s_ * 0.46
                om = [] if s_ == 2 else ['x1']
                om.append('x0')
                _caja_g(mt, xa_, xa_ + 0.46, yp - 0.015, yp + 0.015,
                        zt - 0.95, zt - 0.05, cm, omitir=tuple(om))
    # pilares finos de acero bajo el borde delantero del techo (que no se lea
    # como una tapa flotando): uno sobre cada muro lateral y uno junto a cada
    # junta pasillo/bloque, en el centro de una terraza. No tapan publico.
    y_obj = y_b + (d_r - 1.1) * ca
    i_col = int(math.ceil((y_t0 - y_obj) / prof - 0.5))
    i_col = max(0, min(filas - 1, i_col))
    y_col = y_t0 - (i_col + 0.5) * prof
    if y_w + 0.8 < y_col < y_b + (d_r - 0.5) * ca:
        z_c1 = z_r0 + (y_col - y_b) * sa / ca + 0.06     # 6 cm dentro de la losa
        pies = [(-a2 + 0.5 * g_lat, z_linea(y_col, c_ext) + 0.02),
                (a2 - 0.5 * g_lat, z_linea(y_col, c_ext) + 0.02)]
        if hay_rampas:
            z_t = base + i_col * alto - 0.05
            for xa, xb in bloques:
                pies.append((xa + 0.06, z_t))
                pies.append((xb - 0.06, z_t))
        for xc_, zc_ in pies:
            _caja_g(mt, xc_ - 0.14, xc_ + 0.14, y_col - 0.14, y_col + 0.14,
                    zc_, z_c1, T_ACERO, omitir=(0, 2))
    techo = mt.obj('%s_tribuna_techo' % PRE,
                   ('verde_wgp', 'blanco', 'gris_acero', 'pub_rojo'), col,
                   separar=True)
    techo.parent = raiz

    # =================================================================== publico
    mp = _MG()
    paso = 2.05
    l_max = prof - 0.14
    plazas = []
    for xa, xb in bloques:
        n = int((xb - xa - 0.45) // paso)
        if n < 1:
            continue
        x_ini = 0.5 * (xa + xb) - (n - 1) * paso / 2.0
        for i in range(filas):
            for p in range(n):
                plazas.append((i, x_ini + p * paso))
    ocupadas = [pl for pl in plazas if rng.random() < ocupacion]
    n_max = max(0, (max_tris - me.tris() - mt.tris()) // _PUB_TRIS_MAX)
    if len(ocupadas) > n_max:
        rng.shuffle(ocupadas)
        ocupadas = sorted(ocupadas[:n_max])

    # todos siguen con la mirada al mismo coche de carreras que pasa
    obj_x = rng.uniform(-0.45, 0.45) * largo
    obj_y = y_0 + 14.0
    obj_z = 0.7
    mi_prev = -1
    for i, xc in ocupadas:
        tipo = rng.choices(_PUB_TIPOS, weights=_PUB_PESOS_TIPO)[0]
        e = rng.uniform(0.90, 1.06)
        W = 1.30 * tipo[1] * e * rng.uniform(0.97, 1.03)
        L = min(1.50 * tipo[2] * e, l_max)
        mi = 1 + rng.choices(range(len(_PUBLICO)), weights=_PUB_PESOS_COLOR)[0]
        if mi == mi_prev:
            mi = 1 + rng.choices(range(len(_PUBLICO)), weights=_PUB_PESOS_COLOR)[0]
        mi_prev = mi
        x = xc + rng.uniform(-0.13, 0.13)
        z = base + i * alto
        y = y_t0 - (i + 0.5) * prof + rng.uniform(-0.03, 0.03)
        ddx, ddy, ddz = obj_x - x, obj_y - y, obj_z - (z + 0.8)
        dd = math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz)
        if rng.random() < 0.12:       # algun despistado
            mirada = (rng.uniform(-1.0, 1.0), rng.uniform(-0.5, 0.6))
        else:
            mirada = (1.9 * ddx / dd + rng.uniform(-0.12, 0.12),
                      1.5 * ddz / dd - 0.05 + rng.uniform(-0.1, 0.1))
        rz = rng.uniform(-0.06, 0.06) - 0.05 * max(-1.0, min(1.0, mirada[0]))
        _pub_coche(mp, (x, y, z), rz, W, L, e, tipo, mi, mirada,
                   rng.random() < 0.45)
    publico = mp.obj('%s_tribuna_publico' % PRE, _PUB_MATS, col)
    publico.parent = raiz
    return raiz


def build_portico_meta(parent_collection, ancho=20, **params):
    """Portico de meta con panel MONDIALE GRAND PRIX y semaforo de salida."""
    col = parent_collection
    raiz = _raiz('%s_portico' % PRE, col)
    a2 = ancho / 2.0

    mb = _MB()  # 0 crema, 1 verde_oscuro, 2 blanco, 3 negro, 4 terracota,
                # 5 verde_wgp, 6 gris_acero, 7 gris_oscuro, 8 rojo_luz
    for sx in (-1, 1):
        mb.caja((sx * a2, 0, 0.30), (1.6, 1.6, 0.6), mat=1)     # zocalo
        mb.caja((sx * a2, 0, 3.70), (1.1, 1.1, 6.2), mat=0)     # pilar
        mb.caja((sx * a2, 0, 6.95), (1.4, 1.4, 0.3), mat=1)     # capitel
        # banderola vertical verde con ribete blanco en cada pilar
        mb.caja((sx * a2, 0.58, 4.10), (0.95, 0.05, 4.3), mat=2)
        mb.caja((sx * a2, 0.62, 4.10), (0.80, 0.05, 4.1), mat=5)
    # dintel
    mb.caja((0, 0, 8.10), (ancho + 2.2, 1.4, 2.6), mat=0)
    # cornisa terracota
    mb.caja((0, 0, 9.55), (ancho + 2.6, 1.7, 0.3), mat=4)
    # banda de cuadros (blanco + fichas negras)
    mb.caja((0, 0.68, 7.20), (ancho + 2.2, 0.08, 0.8), mat=2)
    n = int((ancho + 2.2) / 0.4)
    x0 = -(n * 0.4) / 2.0 + 0.2
    for c in range(n):
        for r in range(2):
            if (c + r) % 2 == 0:
                mb.caja((x0 + c * 0.4, 0.70, 7.00 + r * 0.4),
                        (0.4, 0.08, 0.4), mat=3)
    # panel del patrocinio (marco blanco + fondo verde)
    mb.caja((0, 0.73, 8.55), (ancho * 0.8 + 0.3, 0.10, 1.74), mat=2)
    mb.caja((0, 0.78, 8.55), (ancho * 0.8, 0.14, 1.5), mat=5)
    # semaforo de salida colgado del dintel
    mb.caja((0, 0, 6.55), (0.18, 0.18, 0.5), mat=6)
    mb.caja((0, 0, 5.95), (2.6, 0.4, 0.9), mat=7)
    for k in range(5):
        mb.caja((-1.0 + k * 0.5, 0.20, 5.95), (0.30, 0.12, 0.30), mat=8)
    estructura = mb.obj('%s_portico_estructura' % PRE,
                        ('crema', 'verde_oscuro', 'blanco', 'negro', 'terracota',
                         'verde_wgp', 'gris_acero', 'gris_oscuro', 'rojo_luz'), col)
    estructura.parent = raiz

    texto = _texto_3d('%s_portico_texto' % PRE, 'MONDIALE GRAND PRIX',
                      1.0, 'blanco', col, extrude=0.06)
    texto.location = (0, 0.90, 8.52)
    texto.parent = raiz
    return raiz


def build_pantalla(parent_collection, **params):
    """Pantalla gigante ~12x7 m sobre torre de celosia."""
    col = parent_collection
    raiz = _raiz('%s_pantalla' % PRE, col)

    mb = _MB()  # 0 gris_acero, 1 gris_oscuro, 2 pantalla_luz
    for sx in (-1, 1):
        mb.caja((sx * 2.8, 0, 4.25), (0.7, 0.7, 8.5), mat=0)
    mb.caja((0, 0, 2.80), (6.3, 0.45, 0.45), mat=0)
    mb.caja((0, 0, 5.60), (6.3, 0.45, 0.45), mat=0)
    mb.caja((0, 0, 12.15), (12.6, 0.7, 7.6), mat=1)             # marco
    mb.caja((0, 0.38, 12.15), (11.9, 0.08, 6.9), mat=2)         # pantalla
    estructura = mb.obj('%s_pantalla_estructura' % PRE,
                        ('gris_acero', 'gris_oscuro', 'pantalla_luz'), col)
    estructura.parent = raiz

    texto = _texto_3d('%s_pantalla_texto' % PRE, 'MONDIALE GP',
                      1.5, 'azul_oscuro', col, extrude=0.04)
    texto.location = (0, 0.48, 12.9)
    texto.parent = raiz

    vivo = _texto_3d('%s_pantalla_texto2' % PRE, 'PORTO CORSA  -  GIRO 42/60',
                     0.8, 'azul_oscuro', col, extrude=0.04)
    vivo.location = (0, 0.48, 10.8)
    vivo.parent = raiz
    return raiz


def build_boxes(parent_collection, n=12, **params):
    """Edificio de pit lane con n boxes numerados, terraza y muro de pits."""
    col = parent_collection
    raiz = _raiz('%s_boxes' % PRE, col)

    w = 6.0
    L = n * w
    fondo = 9.0
    h = 5.2

    mb = _MB()  # 0 crema, 1 terracota, 2 blanco, 3 gris_oscuro, 4 ocre, 5 verde_wgp
    mb.caja((0, 0, h / 2.0), (L, fondo, h), mat=0)                       # cuerpo
    mb.caja((0, 0, h + 0.17), (L + 0.8, fondo + 0.8, 0.34), mat=1)       # cornisa
    mb.caja((0, fondo / 2.0 - 0.15, h + 0.34 + 0.35), (L, 0.14, 0.7), mat=2)  # balaustrada
    for i in range(n + 1):
        mb.caja((-L / 2.0 + i * w, fondo / 2.0 - 0.05, h / 2.0),
                (0.5, 0.4, h), mat=4)                                    # pilastras
    for i in range(n):
        cx = -L / 2.0 + (i + 0.5) * w
        mb.caja((cx, fondo / 2.0 - 0.05, 1.95), (4.6, 0.2, 3.9), mat=3)  # porton
        for k in range(4):
            mb.caja((cx, fondo / 2.0 + 0.06, 0.55 + k * 0.95),
                    (4.6, 0.03, 0.06), mat=2)                            # lamas
        mb.caja((cx, fondo / 2.0 - 0.02, 4.55), (1.2, 0.16, 1.0), mat=2) # placa
    # muro de pits con franja verde
    mb.caja((0, 11.5, 0.55), (L * 0.92, 0.5, 1.1), mat=2)
    mb.caja((0, 11.5, 1.22), (L * 0.92, 0.54, 0.24), mat=5)
    edificio = mb.obj('%s_boxes_edificio' % PRE,
                      ('crema', 'terracota', 'blanco', 'gris_oscuro',
                       'ocre', 'verde_wgp'), col)
    edificio.parent = raiz

    for i in range(n):
        cx = -L / 2.0 + (i + 0.5) * w
        num = _texto_3d('%s_boxes_num%02d' % (PRE, i + 1), str(i + 1),
                        0.72, 'verde_oscuro', col, extrude=0.04)
        num.location = (cx, fondo / 2.0 + 0.08, 4.53)
        num.parent = raiz
    return raiz


def build_muro_valla(parent_collection, largo=10, **params):
    """Muro bajo blanco + valla de captura de barrotes finos (repetible)."""
    col = parent_collection
    mb = _MB()  # 0 blanco, 1 gris_acero
    mb.caja((0, 0, 0.5), (largo, 0.45, 1.0), mat=0)
    postes = max(2, int(largo // 2) + 1)
    for k in range(postes):
        x = -largo / 2.0 + 0.15 + k * (largo - 0.3) / (postes - 1)
        mb.caja((x, 0, 2.15), (0.09, 0.09, 2.3), mat=1)
    for z in (1.45, 2.0, 2.55, 3.1):
        mb.caja((0, 0.10, z), (largo, 0.035, 0.035), mat=1)
    ob = mb.obj('%s_muro_valla' % PRE, ('blanco', 'gris_acero'), col)
    return ob


def build_valla_publicitaria(parent_collection, largo=8, texto='ALLINOL', **params):
    """Panel publicitario verde/blanco con texto 3D (fachada a +Y)."""
    col = parent_collection
    mb = _MB()  # 0 blanco, 1 verde_wgp, 2 gris_acero
    for sx in (-1, 1):
        mb.caja((sx * (largo / 2.0 - 0.6), 0, 0.14), (0.4, 0.7, 0.28), mat=2)
    mb.caja((0, 0, 1.05), (largo, 0.16, 1.5), mat=0)
    mb.caja((0, 0.06, 1.05), (largo - 0.3, 0.10, 1.24), mat=1)
    mb.caja((0, -0.06, 1.05), (largo - 0.3, 0.10, 1.24), mat=1)   # dorso: tambien verde
    panel = mb.obj('%s_valla_pub' % PRE, ('blanco', 'verde_wgp', 'gris_acero'), col)

    tam = min(0.85, (largo - 0.9) / max(1, len(texto)) / 0.62)
    tx = _texto_3d('%s_valla_pub_texto' % PRE, texto, tam, 'blanco', col,
                   extrude=0.04)
    tx.location = (0, 0.14, 1.03)
    tx.parent = panel
    # el mismo rotulo por detras (girado 180 grados): nada de dorsos en blanco
    tx2 = _texto_3d('%s_valla_pub_texto_dorso' % PRE, texto, tam, 'blanco', col,
                    extrude=0.04)
    tx2.rotation_euler = (tx2.rotation_euler[0], tx2.rotation_euler[1], tx2.rotation_euler[2] + math.pi)
    tx2.location = (0, -0.14, 1.03)
    tx2.parent = panel
    return panel


def build_paca(parent_collection, **params):
    """Pila de balas de paja (2 abajo + 1 arriba) con flejes."""
    col = parent_collection
    mb = _MB()  # 0 paja, 1 paja_oscura
    balas = (((-0.72, 0.00, 0.30), 0.05),
             ((0.72, 0.05, 0.30), -0.07),
             ((0.02, 0.02, 0.90), 0.16))
    for (cx, cy, cz), rz in balas:
        mb.caja((cx, cy, cz), (1.4, 0.75, 0.6), mat=0, rz=rz)
        c, s = math.cos(rz), math.sin(rz)
        for off in (-0.38, 0.38):
            mb.caja((cx + off * c, cy + off * s, cz),
                    (0.06, 0.78, 0.63), mat=1, rz=rz)
    ob = mb.obj('%s_paca' % PRE, ('paja', 'paja_oscura'), col)
    return ob


# ------------------------------------------------------------------- la vineta

def build(parent_collection, seed=0, **params):
    """Vineta World Grand Prix: portico de meta, tribuna, boxes, pantalla,
    muros con valla, vallas publicitarias y pacas, sobre asfalto con linea
    de meta. La pista corre a lo largo de +Y, de ancho 16 m (x en [-8, 8])."""
    col = parent_collection
    raiz = _raiz('%s_kit' % PRE, col)

    # suelo: asfalto de pista + aceras de piedra clara
    mb = _MB()  # 0 asfalto, 1 piedra_clara, 2 blanco, 3 negro
    mb.caja((0, 0, -0.05), (46, 120, 0.10), mat=0)
    mb.caja((-22.0, 0, -0.02), (28, 120, 0.12), mat=1)
    mb.caja((22.5, 0, -0.02), (29, 120, 0.12), mat=1)
    # lineas blancas de borde de pista
    for sx in (-1, 1):
        mb.caja((sx * 7.8, 0, 0.02), (0.18, 120, 0.05), mat=2)
    # linea de meta a cuadros
    mb.caja((0, 2.5, 0.045), (16, 1.7, 0.05), mat=2)
    for c in range(20):
        for r in range(2):
            if (c + r) % 2 == 0:
                mb.caja((-7.6 + c * 0.8, 2.1 + r * 0.8, 0.075),
                        (0.8, 0.8, 0.055), mat=3)
    suelo = mb.obj('%s_suelo' % PRE, ('asfalto', 'piedra_clara',
                                      'blanco', 'negro'), col)
    suelo.parent = raiz

    portico = build_portico_meta(col, ancho=20)
    portico.parent = raiz

    tribuna = build_tribuna(col, largo=40, filas=12, seed=seed)
    tribuna.location = (-29, -4, 0)
    tribuna.rotation_euler = (0, 0, -math.pi / 2)
    tribuna.parent = raiz

    boxes = build_boxes(col, n=12)
    boxes.location = (21, -8, 0)
    boxes.rotation_euler = (0, 0, math.pi / 2)
    boxes.parent = raiz

    pantalla = build_pantalla(col)
    pantalla.location = (-31, -34, 0)
    pantalla.rotation_euler = (0, 0, math.radians(-25))
    pantalla.parent = raiz

    for y in (-32, -21.5, -11, 11, 21.5, 32):
        muro = build_muro_valla(col, largo=10)
        muro.location = (-9, y, 0)
        muro.rotation_euler = (0, 0, -math.pi / 2)
        muro.parent = raiz

    valla1 = build_valla_publicitaria(col, largo=8, texto='ALLINOL')
    valla1.location = (-13.2, -14, 0)
    valla1.rotation_euler = (0, 0, -math.pi / 2)
    valla1.parent = raiz

    valla2 = build_valla_publicitaria(col, largo=8, texto='MONDIALE GRAND PRIX')
    valla2.location = (-13.2, 4, 0)
    valla2.rotation_euler = (0, 0, -math.pi / 2)
    valla2.parent = raiz

    valla3 = build_valla_publicitaria(col, largo=8, texto='ALLINOL')
    valla3.location = (12.8, 30, 0)
    valla3.rotation_euler = (0, 0, math.pi / 2)
    valla3.parent = raiz

    paca1 = build_paca(col)
    paca1.location = (-7.2, 36, 0)
    paca1.rotation_euler = (0, 0, 0.35)
    paca1.parent = raiz

    paca2 = build_paca(col)
    paca2.location = (11.8, 22, 0)
    paca2.rotation_euler = (0, 0, -0.7)
    paca2.parent = raiz

    return raiz
