"""coches_kit.py — Coches-espectador aparcados del mundo de Cars (Porto Corsa).

Kit procedural para Blender 5.1 (bpy puro, sin bpy.ops de modelado, sin
texturas de imagen). Cochecitos low-poly redondeados estilo Cars 2: carrocería
de una pieza (capó y techo suaves por loft de secciones), parabrisas grande
envolvente de cristal azul oscuro que hace de fondo de la CARA: encima lleva
dos ojos grandes ovalados blancos con pupila azul oscuro (mallas finas
conformadas al cristal, no planos flotantes) y una sonrisa sutil (ranura
oscura curvada) en el parachoques delantero, como en las películas de Cars.
Expresiones alegres variadas por seed: 'abierto' (pupilas centradas o
mirando de lado), 'sonrisa' (ojos entrecerrados de medio óvalo con párpado
inferior recto) y 'guino' (un ojo cerrado = párpado arqueado). 4 ruedas con
llanta clara, sin interior. Unidades en metros, origen en el centro de la
base (z=0 en el suelo), frontal mirando a +Y. Cada coche <= 1650 tris
(<=1500 el coche + <=150 la cara).

Piezas (cada una linka a parent_collection y devuelve el objeto creado):
  build_coche(parent_collection, tipo='compacto'|'deportivo'|'furgo',
              color=(r, g, b), seed=0, expresion=None)
      Un coche aparcado (malla única). compacto ~4 m, deportivo ~4.3 m
      (bajo, con alerón), furgo ~5 m (alta, morro corto). `seed` da un
      pequeño jitter de proporciones para variar siluetas. `expresion`:
      'abierto' | 'sonrisa' | 'guino' | None (None = elegida por seed).
  build_fila_aparcada(parent_collection, n=6, seed=0)
      Fila de n coches aparcados lado a lado (mirando a +Y) con colores
      vivos variados (rojo, azul, verde, amarillo, morado, crema), pequeño
      jitter de posición/giro y expresión distinta por coche (las tres
      expresiones garantizadas en cada trío). Devuelve el Empty raíz
      COCHE_fila.

  build(parent_collection, seed=0, **params)
      Muestra: build_fila_aparcada con n=6.
"""

import math
import random

import bpy

PREFIX = "COCHE"
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Paleta plana (color lineal, roughness, metallic)
# ---------------------------------------------------------------------------
_PALETA = {
    "cristal": ((0.020, 0.075, 0.200), 0.10, 0.0),   # azul oscuro: fondo de la cara
    "ojo":     ((0.920, 0.930, 0.940), 0.20, 0.0),   # blanco del ojo
    "pupila":  ((0.008, 0.018, 0.045), 0.15, 0.0),   # azul oscuro casi negro
    "goma":    ((0.055, 0.055, 0.060), 0.92, 0.0),
    "llanta":  ((0.930, 0.900, 0.840), 0.45, 0.0),
    "cromo":   ((0.750, 0.760, 0.770), 0.30, 1.0),
}

COLORES_VIVOS = [
    ("rojo",     (0.80, 0.06, 0.04)),
    ("azul",     (0.04, 0.22, 0.72)),
    ("verde",    (0.07, 0.48, 0.12)),
    ("amarillo", (0.95, 0.70, 0.04)),
    ("morado",   (0.38, 0.09, 0.55)),
    ("crema",    (0.91, 0.86, 0.70)),
]


def _mat_nuevo(name, color, rough, metal):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


def _mat(key):
    """Material fijo MAT_COCHE_<key> (reutilizado si existe)."""
    name = "MAT_%s_%s" % (PREFIX, key)
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    color, rough, metal = _PALETA[key]
    return _mat_nuevo(name, color, rough, metal)


def _mat_cuerpo(color):
    """Material de carrocería para un color rgb dado (reutilizado por hex)."""
    r, g, b = color
    name = "MAT_%s_cuerpo_%02X%02X%02X" % (
        PREFIX, round(r * 255), round(g * 255), round(b * 255))
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    return _mat_nuevo(name, color, 0.30, 0.0)


# ---------------------------------------------------------------------------
# Acumulador de malla multi-material (material único o lista por cara)
# ---------------------------------------------------------------------------
class _MB:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.fmat = []
        self.fsm = []

    def _mi(self, mat):
        for i, m in enumerate(self.mats):
            if m is mat:
                return i
        self.mats.append(mat)
        return len(self.mats) - 1

    def add(self, verts, faces, mat, smooth=False):
        base = len(self.verts)
        self.verts.extend(verts)
        if isinstance(mat, (list, tuple)):
            idxs = [self._mi(m) for m in mat]
        else:
            idxs = [self._mi(mat)] * len(faces)
        for f, mi in zip(faces, idxs):
            self.faces.append(tuple(i + base for i in f))
            self.fmat.append(mi)
            self.fsm.append(smooth)

    def build(self, name, parent_collection):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        for m in self.mats:
            me.materials.append(m)
        for p, mi, sm in zip(me.polygons, self.fmat, self.fsm):
            p.material_index = mi
            p.use_smooth = sm
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        parent_collection.objects.link(ob)
        return ob


def _box(sx, sy, sz, off=(0, 0, 0)):
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    ox, oy, oz = off
    verts = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
             (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    verts = [(a + ox, b + oy, c + oz) for (a, b, c) in verts]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]
    return verts, faces


# ---------------------------------------------------------------------------
# Definición de tipos: secciones (y, z_techo, z_cintura, semiancho, semiancho_top)
# de atrás (-Y) a delante (+Y). glass: índice de hueco -> modo de cristal.
# ---------------------------------------------------------------------------
_TIPOS = {
    "compacto": dict(
        zg=0.30,
        stations=[
            (-1.85, 0.80, 0.60, 0.72, 0.55),
            (-1.60, 1.08, 0.78, 0.88, 0.70),
            (-1.15, 1.20, 0.84, 0.98, 0.76),   # paso de rueda trasero
            (-0.70, 1.52, 0.86, 0.96, 0.70),   # techo trasero
            (0.30, 1.56, 0.86, 0.97, 0.72),    # techo delantero
            (0.85, 1.02, 0.82, 0.99, 0.82),    # base del parabrisas
            (1.25, 0.94, 0.78, 0.98, 0.80),    # capó / paso de rueda delantero
            (1.60, 0.86, 0.68, 0.88, 0.70),
            (1.85, 0.62, 0.50, 0.72, 0.55),
        ],
        glass={2: "rear", 3: "sides", 4: "full"},
        ruedas=dict(r=0.42, hw=0.18, ax=0.84, ejes=(-1.15, 1.15)),
        bumper=(1.10, 0.18, 0.14, 0.38),
        cap_off=(0.10, 0.12),
        spoiler=None,
    ),
    "deportivo": dict(
        zg=0.26,
        stations=[
            (-2.00, 0.78, 0.60, 0.80, 0.62),
            (-1.75, 1.00, 0.74, 0.96, 0.78),
            (-1.25, 1.06, 0.78, 1.04, 0.80),   # paso de rueda trasero
            (-0.60, 1.28, 0.76, 1.00, 0.66),   # techo trasero (cabina baja)
            (0.05, 1.30, 0.74, 1.02, 0.68),    # techo delantero
            (0.80, 0.88, 0.68, 1.03, 0.86),    # parabrisas tendido
            (1.30, 0.80, 0.62, 1.00, 0.82),    # capó largo
            (1.75, 0.70, 0.52, 0.88, 0.70),
            (2.05, 0.52, 0.40, 0.70, 0.54),
        ],
        glass={2: "rear", 3: "sides", 4: "full"},
        ruedas=dict(r=0.40, hw=0.18, ax=0.88, ejes=(-1.25, 1.25)),
        bumper=(1.20, 0.18, 0.13, 0.34),
        cap_off=(0.10, 0.12),
        spoiler=True,
    ),
    "furgo": dict(
        zg=0.32,
        stations=[
            (-2.40, 1.70, 0.95, 0.80, 0.68),   # trasera casi plana (portón)
            (-2.28, 2.02, 1.28, 0.94, 0.82),
            (-1.50, 2.06, 1.32, 1.00, 0.85),   # paso de rueda trasero
            (-0.20, 2.08, 1.34, 1.00, 0.86),
            (1.30, 2.04, 1.30, 1.00, 0.84),    # el techo llega muy adelante
            (1.85, 1.15, 0.88, 0.96, 0.80),    # parabrisas alto casi vertical
            (2.20, 0.95, 0.70, 0.88, 0.72),    # morro corto
            (2.42, 0.68, 0.50, 0.72, 0.58),
        ],
        glass={3: "sides", 4: "full"},
        ruedas=dict(r=0.44, hw=0.19, ax=0.86, ejes=(-1.50, 1.60)),
        bumper=(1.20, 0.20, 0.16, 0.44),
        cap_off=(0.05, 0.10),
        spoiler=None,
    ),
}

# segmentos del lazo (13 puntos) que reciben cristal según el modo
_GLASS_SEGS = {
    "full":  {4, 5, 6, 7},   # parabrisas envolvente (frente + esquinas)
    "sides": {4, 7},         # ventanillas laterales bajo techo pintado
    "rear":  {5, 6},         # luneta trasera
}


def _seccion(y, zt, zb, w, wt, zg):
    """Lazo cerrado de 13 puntos (der. abajo→arriba, centro, izq. arriba→abajo)."""
    der = [
        (0.50 * w, zg),
        (0.90 * w, zg + 0.26 * (zb - zg)),
        (1.00 * w, zg + 0.70 * (zb - zg)),
        (0.97 * w, zb),
        (wt, zb + 0.55 * (zt - zb)),
        (0.58 * wt, zt - 0.10 * (zt - zb)),
    ]
    pts = der + [(0.0, zt)] + [(-x, z) for (x, z) in reversed(der)]
    return [(x, y, z) for (x, z) in pts]


def _rueda(mb, cx, cy, r, hw, sign):
    """Rueda (eje X): neumático oscuro + tapacubos de llanta clara."""
    S = 12
    perfil = [(-hw, 0.62 * r), (-0.95 * hw, 0.90 * r), (-0.50 * hw, r),
              (0.50 * hw, r), (0.92 * hw, 0.88 * r), (hw, 0.62 * r)]
    verts = []
    for dx, rr in perfil:
        for k in range(S):
            th = TAU * k / S
            verts.append((cx + sign * dx, cy + rr * math.cos(th),
                          r + rr * math.sin(th)))
    c_in = len(verts)
    verts.append((cx - sign * hw, cy, r))
    c_out = len(verts)
    verts.append((cx + sign * hw, cy, r))

    def ring(i, k):
        return i * S + (k % S)

    m_goma = _mat("goma")
    m_llanta = _mat("llanta")
    faces = []
    mats = []
    for i in range(5):
        m = m_llanta if i == 4 else m_goma
        for k in range(S):
            faces.append((ring(i, k), ring(i, k + 1), ring(i + 1, k + 1), ring(i + 1, k)))
            mats.append(m)
    for k in range(S):  # tapa interior (goma) y tapacubos exterior (llanta)
        faces.append((c_in, ring(0, k + 1), ring(0, k)))
        mats.append(m_goma)
        faces.append((c_out, ring(5, k), ring(5, k + 1)))
        mats.append(m_llanta)

    if sign < 0:
        faces = [tuple(reversed(f)) for f in faces]
    mb.add(verts, faces, mats, smooth=True)


# ---------------------------------------------------------------------------
# CARA (ojos sobre el parabrisas, estilo Cars)
# ---------------------------------------------------------------------------
# El hueco de cristal "full" es una banda reglada entre dos lazos de sección.
# Se parametriza como superficie (u, v): u en [-1, 1] a lo ancho del cristal
# (anclas en los vértices reales del lazo -> coincide EXACTAMENTE con los
# quads renderizados), v en [0, 1] de la base del parabrisas al techo. Los
# ojos se construyen muestreando esa superficie y desplazando unos mm por la
# normal exterior: mallas finas pegadas al cristal, curvadas con él.
_U_ANCLAS = (-1.0, -0.58, 0.0, 0.58, 1.0)
_OFF_OJO = 0.022    # blanco del ojo sobre el cristal
_OFF_PUP = 0.040    # pupila/párpado sobre el blanco
_OFF_BRI = 0.055    # brillo (glint) sobre la pupila

EXPRESIONES = ("abierto", "sonrisa", "guino")


def _parabrisas_uv(loops, i_full):
    """Función punto(u, v, off) -> vértice 3D sobre el cristal frontal."""
    arc_top = [loops[i_full][k] for k in (8, 7, 6, 5, 4)]
    arc_bot = [loops[i_full + 1][k] for k in (8, 7, 6, 5, 4)]

    def borde(arc, u):
        u = max(-1.0, min(1.0, u))
        for k in range(4):
            if u <= _U_ANCLAS[k + 1] or k == 3:
                t = (u - _U_ANCLAS[k]) / (_U_ANCLAS[k + 1] - _U_ANCLAS[k])
                a, b = arc[k], arc[k + 1]
                return (a[0] + (b[0] - a[0]) * t,
                        a[1] + (b[1] - a[1]) * t,
                        a[2] + (b[2] - a[2]) * t)

    def surf(u, v):
        p0 = borde(arc_bot, u)
        p1 = borde(arc_top, u)
        return (p0[0] + (p1[0] - p0[0]) * v,
                p0[1] + (p1[1] - p0[1]) * v,
                p0[2] + (p1[2] - p0[2]) * v)

    def punto(u, v, off):
        p = surf(u, v)
        e = 0.02
        pa, pb = surf(u + e, v), surf(u - e, v)
        pc, pd = surf(u, v + e), surf(u, v - e)
        tu = (pa[0] - pb[0], pa[1] - pb[1], pa[2] - pb[2])
        tv = (pc[0] - pd[0], pc[1] - pd[1], pc[2] - pd[2])
        n = (tu[1] * tv[2] - tu[2] * tv[1],
             tu[2] * tv[0] - tu[0] * tv[2],
             tu[0] * tv[1] - tu[1] * tv[0])
        ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) or 1.0
        s = (1.0 if n[1] >= 0.0 else -1.0) / ln   # exterior = hacia +Y
        return (p[0] + n[0] * s * off, p[1] + n[1] * s * off,
                p[2] + n[2] * s * off)

    return punto


def _abanico(mb, punto, uc, vc, ru, rv, off, mat, nseg, th0=0.0, th1=TAU):
    """Óvalo (o medio óvalo si th1-th0 < TAU) conformado al cristal."""
    full = abs((th1 - th0) - TAU) < 1e-6
    npts = nseg if full else nseg + 1
    verts = [punto(uc, vc, off)]
    for k in range(npts):
        th = th0 + (th1 - th0) * (k / float(nseg))
        verts.append(punto(uc + ru * math.cos(th), vc + rv * math.sin(th), off))
    faces = []
    for k in range(nseg):
        a = 1 + k
        b = 1 + ((k + 1) % npts if full else k + 1)
        faces.append((0, b, a))
    mb.add(verts, faces, mat, smooth=True)


def _tira_uv(mb, punto, us, vs, half, off, mat):
    """Tira curvada (párpado del guiño) siguiendo (us[i], vs[i]) +- half en v."""
    K = len(us) - 1
    bot = [punto(us[k], vs[k] - half, off) for k in range(K + 1)]
    top = [punto(us[k], vs[k] + half, off) for k in range(K + 1)]
    faces = [(k, K + 1 + k, K + 2 + k, k + 1) for k in range(K)]
    mb.add(bot + top, faces, mat, smooth=True)


def _cara_ojos(mb, loops, glass, rng, expresion):
    """Dos ojos grandes ovalados blancos con pupila sobre el cristal 'full'."""
    i_full = next((i for i in sorted(glass) if glass[i] == "full"), None)
    if i_full is None:
        return
    if expresion is None:
        expresion = rng.choice(("abierto", "abierto", "sonrisa", "sonrisa",
                                "guino"))
    if expresion == "guino":
        expresion = "abierto"  # el guino parecia un ojo que faltaba
    if expresion not in EXPRESIONES:
        raise ValueError("expresion debe ser 'abierto', 'sonrisa' o 'guino'")
    punto = _parabrisas_uv(loops, i_full)
    m_ojo = _mat("ojo")
    m_pup = _mat("pupila")

    UC, VC, RU, RV = 0.36, 0.52, 0.31, 0.34
    mirada = rng.choice((-1, 0, 0, 1))       # ambos ojos miran al mismo lado
    lado_guino = rng.choice((-1, 1))
    for s in (-1, 1):
        uc = s * UC
        if expresion == "guino" and s == lado_guino:
            # ojo cerrado: párpado = arco alegre hacia arriba
            K = 6
            us = [uc - RU + 2.0 * RU * k / K for k in range(K + 1)]
            vs = [VC + 0.38 * RV * math.sin(math.pi * k / K)
                  for k in range(K + 1)]
            _tira_uv(mb, punto, us, vs, 0.18 * RV, _OFF_PUP, m_pup)
        elif expresion == "sonrisa":
            # ojo entrecerrado de sonrisa: medio óvalo con párpado inf. recto
            v0 = VC - 0.10
            up = uc + mirada * 0.18 * RU
            _abanico(mb, punto, uc, v0, RU, RV, _OFF_OJO, m_ojo,
                     8, 0.0, math.pi)
            _abanico(mb, punto, up, v0, 0.48 * RU, 0.55 * RV,
                     _OFF_PUP, m_pup, 6, 0.0, math.pi)
            _abanico(mb, punto, up - 0.12 * RU, v0 + 0.22 * RV,
                     0.09 * RU, 0.09 * RV, _OFF_BRI, m_ojo, 6)
        else:
            # ojo bien abierto (también el ojo abierto del guiño)
            _abanico(mb, punto, uc, VC, RU, RV, _OFF_OJO, m_ojo, 14)
            du = (0 if expresion == "guino" else mirada) * 0.28 * RU
            _abanico(mb, punto, uc + du, VC + 0.02, 0.45 * RU, 0.42 * RV,
                     _OFF_PUP, m_pup, 10)
            _abanico(mb, punto, uc + du - 0.15 * RU, VC + 0.02 + 0.15 * RV,
                     0.10 * RU, 0.10 * RV, _OFF_BRI, m_ojo, 6)


# ---------------------------------------------------------------------------
# PIEZAS
# ---------------------------------------------------------------------------
def build_coche(parent_collection, tipo="compacto", color=(0.80, 0.06, 0.04),
                seed=0, expresion=None):
    """Coche-espectador aparcado estilo Cars: malla única, frontal a +Y.

    `expresion`: 'abierto' | 'sonrisa' | 'guino' | None (elegida por seed).
    """
    if tipo not in _TIPOS:
        raise ValueError("tipo debe ser 'compacto', 'deportivo' o 'furgo'")
    d = _TIPOS[tipo]
    rng = random.Random(7919 * seed + hash(tipo) % 1000)
    fy = rng.uniform(0.97, 1.04)   # jitter de proporciones
    fz = rng.uniform(0.96, 1.05)
    fw = rng.uniform(0.97, 1.04)

    zg = d["zg"]
    st = [(y * fy, zg + (zt - zg) * fz, zg + (zb - zg) * fz, w * fw, wt * fw)
          for (y, zt, zb, w, wt) in d["stations"]]

    mb = _MB()
    m_cuerpo = _mat_cuerpo(color)
    m_cristal = _mat("cristal")

    # --- loft de la carrocería (verts compartidos: sombreado suave continuo)
    loops = [_seccion(y, zt, zb, w, wt, zg) for (y, zt, zb, w, wt) in st]
    P = 13
    verts = [v for lp in loops for v in lp]
    faces = []
    mats = []
    for i in range(len(loops) - 1):
        segs_cristal = _GLASS_SEGS.get(d["glass"].get(i, ""), set())
        a, b = i * P, (i + 1) * P
        for j in range(P):
            j2 = (j + 1) % P
            faces.append((a + j2, a + j, b + j, b + j2))
            mats.append(m_cristal if j in segs_cristal else m_cuerpo)

    # tapas redondeadas (parachoques integrados en la forma)
    off_re, off_fr = d["cap_off"]
    y0, zt0, zb0 = st[0][0], st[0][1], st[0][2]
    yN, ztN, zbN = st[-1][0], st[-1][1], st[-1][2]
    c_re = len(verts)
    verts.append((0.0, y0 - off_re, (zg + zt0) * 0.5))
    c_fr = len(verts)
    verts.append((0.0, yN + off_fr, (zg + ztN) * 0.5))
    last = (len(loops) - 1) * P
    for j in range(P):
        j2 = (j + 1) % P
        faces.append((c_re, j, j2))
        mats.append(m_cuerpo)
        faces.append((c_fr, last + j2, last + j))
        mats.append(m_cuerpo)
    mb.add(verts, faces, mats, smooth=True)

    # --- ojos sobre el parabrisas (cara alegre estilo Cars)
    _cara_ojos(mb, loops, d["glass"], rng, expresion)

    # --- parachoques cromados
    bx, by, bz, bzc = d["bumper"]
    y_fr = yN + off_fr
    y_re = y0 - off_re
    mb.add(*_box(bx * fw, by, bz, off=(0.0, y_fr - 0.10, bzc * fz)), _mat("cromo"))
    mb.add(*_box(bx * fw, by, bz, off=(0.0, y_re + 0.10, bzc * fz)), _mat("cromo"))

    # --- sonrisa sutil: ranura oscura curvada en el parachoques delantero
    y_boca = y_fr - 0.10 + by / 2.0 + 0.008
    zc_boca = bzc * fz + 0.010
    xh = 0.34 * bx * fw
    K = 6
    bot, top = [], []
    for k in range(K + 1):
        x = -xh + 2.0 * xh * k / K
        z = zc_boca + 0.050 * (x / xh) ** 2 - 0.025
        bot.append((x, y_boca, z - 0.018))
        top.append((x, y_boca, z + 0.018))
    caras_boca = [(k, K + 1 + k, K + 2 + k, k + 1) for k in range(K)]
    mb.add(bot + top, caras_boca, _mat("pupila"), smooth=True)

    # --- alerón (deportivo)
    if d["spoiler"]:
        yb = -1.80 * fy
        ztrunk = zg + (0.90 - zg) * fz
        for sx in (-0.40, 0.40):
            mb.add(*_box(0.14, 0.18, 0.30, off=(sx * fw, yb, ztrunk - 0.04)),
                   m_cuerpo)
        mb.add(*_box(1.30 * fw, 0.36, 0.08, off=(0.0, yb, ztrunk + 0.13)),
               m_cuerpo)

    # --- 4 ruedas
    rd = d["ruedas"]
    ax = rd["ax"] * fw
    for ye in rd["ejes"]:
        for sign in (1.0, -1.0):
            _rueda(mb, sign * ax, ye * fy, rd["r"], rd["hw"], sign)

    return mb.build("%s_%s" % (PREFIX, tipo), parent_collection)


def build_fila_aparcada(parent_collection, n=6, seed=0):
    """Fila de n coches aparcados lado a lado, mirando a +Y, colores vivos
    y expresión alegre distinta por coche (trío garantizado de expresiones)."""
    rng = random.Random(7919 * seed + 331)
    root = bpy.data.objects.new("%s_fila" % PREFIX, None)
    root.empty_display_size = 1.5
    parent_collection.objects.link(root)

    colores = list(COLORES_VIVOS)
    rng.shuffle(colores)

    # expresiones variadas: las tres presentes en cada trío consecutivo
    expresiones = (list(EXPRESIONES) * ((n + 2) // 3))[:n]
    rng.shuffle(expresiones)

    semianchos = {"compacto": 1.00, "deportivo": 1.05, "furgo": 1.03}
    cursor = 0.0
    xs = []
    datos = []
    for i in range(n):
        u = rng.random()
        tipo = "compacto" if u < 0.50 else ("deportivo" if u < 0.80 else "furgo")
        half = semianchos[tipo]
        cursor += half
        xs.append(cursor)
        cursor += half + rng.uniform(0.55, 0.85)
        datos.append((tipo, colores[i % len(colores)][1]))

    centro = (xs[0] + xs[-1]) / 2.0
    for i, ((tipo, color), x) in enumerate(zip(datos, xs)):
        ob = build_coche(parent_collection, tipo=tipo, color=color,
                         seed=seed * 100 + i, expresion=expresiones[i])
        ob.parent = root
        ob.location = (x - centro + rng.uniform(-0.08, 0.08),
                       rng.uniform(-0.30, 0.30), 0.0)
        ob.rotation_euler = (0.0, 0.0, math.radians(rng.uniform(-6.0, 6.0)))
    return root


def build(parent_collection, seed=0, **params):
    """Muestra: fila de 6 coches-espectador aparcados. Devuelve el Empty raíz."""
    return build_fila_aparcada(parent_collection, n=params.get("n", 6), seed=seed)
