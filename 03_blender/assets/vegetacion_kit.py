"""vegetacion_kit.py — Vegetación mediterránea low-poly estilo Cars 2 (Porto Corsa).

Kit procedural para Blender 5.1 (bpy, sin bpy.ops de modelado, sin texturas de
imagen). Estilo Riviera italiana saturada y limpia: verdes vivos, caliza
ocre-gris, flores rosa/rojo. Unidades en metros, origen en el centro de la
base (z=0 en el suelo), cara principal mirando a +Y. Cada pieza <= 2000 tris.

Piezas (cada una crea UN objeto malla linkado a parent_collection y lo devuelve):
  build_palmera(parent_collection, alto=8.0, seed=0)
      Tronco curvado con anillos + corona de 8-12 palmas planas arqueadas.
  build_cipres(parent_collection, alto=10.0, seed=0)
      Huso verde oscuro (cupressus) con tronco corto visible.
  build_pino(parent_collection, alto=12.0, seed=0)
      Pino mediterráneo (parasol): tronco inclinado, copa aparasolada ancha.
  build_adelfa(parent_collection, seed=0)
      Arbusto redondeado verde con racimos de flores rosa.
  build_jardinera(parent_collection, largo=6.0, seed=0)
      Jardinera de piedra clara con seto y flores rojas/rosas (horquilla Loews).
  build_roca(parent_collection, tam=3.0, seed=0)
      Bolo de caliza gris-ocre semienterrado.
  build_acantilado(parent_collection, largo=40.0, alto=25.0, seed=0)
      Módulo de acantilado calizo estratificado, TILEABLE en X (el perfil del
      frente usa armónicos periódicos en `largo`), con vegetación colgante.

  build(parent_collection, seed=0, **params)
      Muestrario: fila de piezas delante + acantilado de fondo. Devuelve el
      Empty raíz VEG_muestrario.
"""

import math
import random

import bpy
from mathutils import Vector

PREFIX = "VEG"
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Paleta plana estilo Cars 2 (color lineal, roughness)
# ---------------------------------------------------------------------------
_PALETA = {
    "tronco_palmera": ((0.38, 0.24, 0.11), 0.90),
    "palma":          ((0.07, 0.42, 0.10), 0.75),
    "palma_clara":    ((0.15, 0.55, 0.15), 0.75),
    "coco":           ((0.45, 0.28, 0.10), 0.85),
    "cipres":         ((0.043, 0.20, 0.065), 0.80),
    "tronco":         ((0.30, 0.17, 0.08), 0.90),
    "pino":           ((0.10, 0.35, 0.09), 0.80),
    "adelfa_hoja":    ((0.10, 0.32, 0.10), 0.80),
    "flor_rosa":      ((0.92, 0.28, 0.50), 0.60),
    "flor_rosa_clara": ((0.97, 0.55, 0.68), 0.60),
    "flor_roja":      ((0.80, 0.06, 0.08), 0.60),
    "piedra":         ((0.63, 0.53, 0.35), 0.90),
    "tierra":         ((0.28, 0.19, 0.11), 1.00),
    "roca":           ((0.48, 0.39, 0.24), 0.95),
    "caliza_clara":   ((0.72, 0.58, 0.34), 0.95),
    "caliza_ocre":    ((0.55, 0.40, 0.20), 0.95),
    "caliza_gris":    ((0.56, 0.50, 0.38), 0.95),
    "colgante":       ((0.13, 0.38, 0.12), 0.80),
}


def _mat(key):
    """Devuelve (reutilizando si existe) el material plano MAT_VEG_<key>."""
    name = "MAT_%s_%s" % (PREFIX, key)
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    color, rough = _PALETA[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


# ---------------------------------------------------------------------------
# Acumulador de malla multi-material
# ---------------------------------------------------------------------------
class _MB:
    """Acumula (verts, faces, material, smooth) y construye una malla única."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.fmat = []
        self.fsm = []

    def add(self, verts, faces, mat, smooth=False):
        base = len(self.verts)
        if mat in self.mats:
            mi = self.mats.index(mat)
        else:
            self.mats.append(mat)
            mi = len(self.mats) - 1
        self.verts.extend(verts)
        for f in faces:
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


# ---------------------------------------------------------------------------
# Primitivas procedurales (verts, faces) con winding hacia fuera
# ---------------------------------------------------------------------------
def _sphere(r=1.0, seg=8, rings=5, scale=(1, 1, 1), off=(0, 0, 0), rng=None, jit=0.0):
    verts = []
    faces = []

    def j():
        return 1.0 + (rng.uniform(-jit, jit) if (rng is not None and jit) else 0.0)

    verts.append((0.0, 0.0, r * j()))  # polo superior
    ring_rows = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        row = []
        for k in range(seg):
            th = TAU * k / seg
            f = j()
            row.append(len(verts))
            verts.append((r * math.sin(phi) * math.cos(th) * f,
                          r * math.sin(phi) * math.sin(th) * f,
                          r * math.cos(phi) * f))
        ring_rows.append(row)
    bot = len(verts)
    verts.append((0.0, 0.0, -r * j()))  # polo inferior

    r0 = ring_rows[0]
    for k in range(seg):
        faces.append((0, r0[k], r0[(k + 1) % seg]))
    for i in range(len(ring_rows) - 1):
        up = ring_rows[i]
        lo = ring_rows[i + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((up[k], lo[k], lo[k2], up[k2]))
    rl = ring_rows[-1]
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((bot, rl[k2], rl[k]))

    sx, sy, sz = scale
    ox, oy, oz = off
    verts = [(x * sx + ox, y * sy + oy, z * sz + oz) for (x, y, z) in verts]
    return verts, faces


def _lathe(profile, seg=8, off=(0, 0, 0), rng=None, jit=0.0):
    """Revolución alrededor de Z. profile = [(radio, z), ...] de abajo a arriba;
    radio 0 en extremos = polo."""
    verts = []
    faces = []
    rows = []
    for (r, z) in profile:
        if r <= 1e-6:
            rows.append((len(verts),))
            verts.append((0.0, 0.0, z))
        else:
            row = []
            for k in range(seg):
                th = TAU * k / seg
                f = 1.0 + (rng.uniform(-jit, jit) if (rng is not None and jit) else 0.0)
                row.append(len(verts))
                verts.append((r * f * math.cos(th), r * f * math.sin(th), z))
            rows.append(tuple(row))
    for i in range(len(rows) - 1):
        a = rows[i]
        b = rows[i + 1]
        if len(a) == 1 and len(b) > 1:      # polo inferior
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((a[0], b[k2], b[k]))
        elif len(b) == 1 and len(a) > 1:    # polo superior
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((b[0], a[k], a[k2]))
        elif len(a) > 1 and len(b) > 1:
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((a[k], a[k2], b[k2], b[k]))
    ox, oy, oz = off
    verts = [(x + ox, y + oy, z + oz) for (x, y, z) in verts]
    return verts, faces


def _tube(points, radii, sides=7, cap_top=True):
    """Barre una sección circular por una polilínea (tronco curvado)."""
    verts = []
    faces = []
    rings = []
    n = len(points)
    for i, p in enumerate(points):
        if i == 0:
            t = Vector(points[1]) - Vector(points[0])
        elif i == n - 1:
            t = Vector(points[-1]) - Vector(points[-2])
        else:
            t = Vector(points[i + 1]) - Vector(points[i - 1])
        t.normalize()
        ref = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
        u = t.cross(ref)
        u.normalize()
        v = t.cross(u)
        row = []
        for k in range(sides):
            th = TAU * k / sides
            q = Vector(p) + (u * math.cos(th) + v * math.sin(th)) * radii[i]
            row.append(len(verts))
            verts.append((q.x, q.y, q.z))
        rings.append(row)
    for i in range(n - 1):
        a = rings[i]
        b = rings[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((a[k], a[k2], b[k2], b[k]))
    if cap_top:
        c = len(verts)
        verts.append(tuple(points[-1]))
        b = rings[-1]
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c, b[k], b[k2]))
    return verts, faces


def _box(sx, sy, sz, off=(0, 0, 0)):
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    ox, oy, oz = off
    verts = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
             (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    verts = [(a + ox, b + oy, c + oz) for (a, b, c) in verts]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]
    return verts, faces


def _palma_frond(L, wmax, tanp, droop, yaw, base):
    """Palma plana: tira de quads con nervio central elevado, arqueada y caída."""
    ts = (0.0, 0.18, 0.40, 0.62, 0.82, 1.0)
    ws = (0.10, 0.58, 0.78, 0.62, 0.34, 0.02)
    cy, sy_ = math.cos(yaw), math.sin(yaw)
    bx, by, bz = base
    verts = []
    faces = []
    rows = []
    for t, wr in zip(ts, ws):
        x = t * L
        z = L * (tanp * t - droop * t * t)
        w = wmax * wr
        ridge = 0.22 * wmax * wr
        station = ((x, -w, z), (x, 0.0, z + ridge), (x, w, z))
        row = []
        for (lx, ly, lz) in station:
            gx = lx * cy - ly * sy_ + bx
            gy = lx * sy_ + ly * cy + by
            row.append(len(verts))
            verts.append((gx, gy, lz + bz))
        rows.append(row)
    for i in range(len(rows) - 1):
        l0, c0, r0 = rows[i]
        l1, c1, r1 = rows[i + 1]
        faces.append((l0, l1, c1, c0))
        faces.append((c0, c1, r1, r0))
    return verts, faces


# ---------------------------------------------------------------------------
# PIEZAS
# ---------------------------------------------------------------------------
def build_palmera(parent_collection, alto=8.0, seed=0):
    """Palmera estilizada: tronco curvado anillado + corona de 8-12 palmas."""
    rng = random.Random(7919 * seed + 11)
    mb = _MB()

    lean_yaw = rng.uniform(0.0, TAU)
    lean = rng.uniform(0.10, 0.22) * alto
    npts = 7
    pts = []
    radii = []
    for i in range(npts):
        t = i / (npts - 1.0)
        off = lean * (t ** 1.7)
        pts.append((math.cos(lean_yaw) * off, math.sin(lean_yaw) * off, t * alto * 0.92))
        r = (0.040 - 0.020 * t) * alto
        if i % 2 == 1:
            r *= 1.12  # anillos del tronco
        radii.append(r)
    mb.add(*_tube(pts, radii, sides=7), _mat("tronco_palmera"), smooth=True)

    crown = Vector(pts[-1])
    mb.add(*_sphere(0.05 * alto + 0.12, seg=7, rings=4, off=crown), _mat("palma"), smooth=True)

    for _ in range(3):  # cocos
        a = rng.uniform(0.0, TAU)
        rc = 0.028 * alto + 0.06
        cc = crown + Vector((math.cos(a) * rc * 1.8, math.sin(a) * rc * 1.8, -rc * 1.2))
        mb.add(*_sphere(rc, seg=6, rings=3, off=cc), _mat("coco"), smooth=True)

    nf = rng.randint(8, 12)
    Lf = alto * 0.42
    for i in range(nf):
        yaw = TAU * i / nf + rng.uniform(-0.15, 0.15)
        if i % 2 == 0:  # palmas altas
            tanp = rng.uniform(0.55, 0.75)
            droop = rng.uniform(0.72, 0.90)
            key = "palma"
        else:           # palmas bajas, más caídas y claras
            tanp = rng.uniform(0.22, 0.42)
            droop = rng.uniform(1.00, 1.20)
            key = "palma_clara"
        L = Lf * rng.uniform(0.85, 1.05)
        mb.add(*_palma_frond(L, Lf * 0.16, tanp, droop, yaw, crown), _mat(key), smooth=True)

    return mb.build("%s_palmera" % PREFIX, parent_collection)


def build_cipres(parent_collection, alto=10.0, seed=0):
    """Ciprés: huso verde oscuro con tronco corto."""
    rng = random.Random(7919 * seed + 23)
    mb = _MB()
    rt = 0.012 * alto + 0.05
    mb.add(*_lathe([(0.0, 0.0), (rt, 0.0), (rt, 0.10 * alto), (0.0, 0.11 * alto)], seg=7),
           _mat("tronco"), smooth=True)
    perfil = [
        (0.0, 0.055 * alto),
        (0.062 * alto, 0.10 * alto),
        (0.100 * alto, 0.24 * alto),
        (0.106 * alto, 0.38 * alto),
        (0.086 * alto, 0.55 * alto),
        (0.058 * alto, 0.72 * alto),
        (0.030 * alto, 0.87 * alto),
        (0.010 * alto, 0.96 * alto),
        (0.0, alto),
    ]
    mb.add(*_lathe(perfil, seg=9, rng=rng, jit=0.05), _mat("cipres"), smooth=True)
    return mb.build("%s_cipres" % PREFIX, parent_collection)


def build_pino(parent_collection, alto=12.0, seed=0):
    """Pino parasol: tronco esbelto inclinado, copa ancha y plana."""
    rng = random.Random(7919 * seed + 37)
    mb = _MB()

    lean_yaw = rng.uniform(0.0, TAU)
    lean = rng.uniform(0.05, 0.10) * alto
    npts = 5
    pts = []
    radii = []
    for i in range(npts):
        t = i / (npts - 1.0)
        off = lean * (t ** 1.5)
        pts.append((math.cos(lean_yaw) * off, math.sin(lean_yaw) * off, t * alto * 0.74))
        radii.append((0.030 - 0.015 * t) * alto)
    mb.add(*_tube(pts, radii, sides=7), _mat("tronco"), smooth=True)

    top = Vector(pts[-1])
    for sgn in (1.0, -1.0):  # dos ramas hacia el borde de la copa
        a = lean_yaw + sgn * rng.uniform(1.2, 1.9)
        p0 = Vector(pts[3])
        p2 = top + Vector((math.cos(a) * 0.22 * alto, math.sin(a) * 0.22 * alto, 0.10 * alto))
        p1 = (p0 + p2) / 2 + Vector((0, 0, 0.02 * alto))
        mb.add(*_tube([p0, p1, p2], [0.014 * alto, 0.011 * alto, 0.007 * alto], sides=5),
               _mat("tronco"), smooth=True)

    z0 = 0.66 * alto
    R = 0.42 * alto
    copa = [
        (0.0, z0 - 0.02 * alto),
        (0.62 * R, z0 + 0.005 * alto),
        (R, z0 + 0.065 * alto),
        (0.80 * R, z0 + 0.135 * alto),
        (0.45 * R, z0 + 0.205 * alto),
        (0.0, z0 + 0.26 * alto),
    ]
    cx = top.x * 0.6
    cy = top.y * 0.6
    mb.add(*_lathe(copa, seg=10, off=(cx, cy, 0), rng=rng, jit=0.06), _mat("pino"), smooth=True)
    for sgn in (1.0, -1.0):  # bultos superiores para romper la silueta
        mb.add(*_sphere(0.11 * alto, seg=7, rings=4, scale=(1, 1, 0.55),
                        off=(cx + sgn * 0.11 * alto, cy + sgn * 0.04 * alto, z0 + 0.185 * alto),
                        rng=rng, jit=0.07),
               _mat("pino"), smooth=True)
    return mb.build("%s_pino" % PREFIX, parent_collection)


def build_adelfa(parent_collection, seed=0):
    """Adelfa: arbusto redondeado (~1.8 m) con racimos de flores rosa."""
    rng = random.Random(7919 * seed + 53)
    mb = _MB()
    blobs = [
        (0.95, (0.0, 0.0, 0.85)),
        (0.72, (0.62, 0.30, 0.62)),
        (0.70, (-0.58, -0.28, 0.66)),
        (0.60, (0.10, -0.55, 0.72)),
    ]
    for r, c in blobs:
        mb.add(*_sphere(r, seg=8, rings=5, scale=(1.0, 1.0, 0.88), off=c, rng=rng, jit=0.10),
               _mat("adelfa_hoja"), smooth=True)
    for i in range(13):
        a = TAU * i / 13.0 + rng.uniform(-0.2, 0.2)
        rr = rng.uniform(0.15, 0.85)
        z = 0.85 + math.sqrt(max(0.0, 1.0 - (rr / 0.95) ** 2)) * 0.80
        key = "flor_rosa" if i % 3 else "flor_rosa_clara"
        mb.add(*_sphere(rng.uniform(0.18, 0.26), seg=6, rings=3,
                        off=(math.cos(a) * rr, math.sin(a) * rr, z)),
               _mat(key), smooth=True)
    return mb.build("%s_adelfa" % PREFIX, parent_collection)


def build_jardinera(parent_collection, largo=6.0, seed=0):
    """Jardinera de piedra con seto y flores rojas/rosas (horquilla Loews)."""
    rng = random.Random(7919 * seed + 71)
    mb = _MB()
    W = 1.5
    H = 0.75
    mb.add(*_box(largo, W, H, off=(0, 0, H / 2)), _mat("piedra"))
    mb.add(*_box(largo + 0.18, W + 0.18, 0.14, off=(0, 0, H - 0.07)), _mat("piedra"))
    mb.add(*_box(largo + 0.14, W + 0.14, 0.12, off=(0, 0, 0.06)), _mat("piedra"))
    mb.add(*_sphere(1.0, seg=10, rings=5, scale=(largo * 0.47, W * 0.44, 0.42),
                    off=(0, 0, H + 0.06), rng=rng, jit=0.06),
           _mat("adelfa_hoja"), smooth=True)
    n = max(5, int(largo * 2.2))
    for i in range(n):
        t = (i + 0.5) / n
        x = (t - 0.5) * (largo - 0.8)
        y = 0.28 if i % 2 == 0 else -0.28
        key = "flor_roja" if i % 2 == 0 else "flor_rosa"
        mb.add(*_sphere(rng.uniform(0.20, 0.26), seg=6, rings=3,
                        off=(x, y + rng.uniform(-0.08, 0.08),
                             H + 0.34 + rng.uniform(-0.04, 0.06))),
               _mat(key), smooth=True)
    return mb.build("%s_jardinera" % PREFIX, parent_collection)


def build_roca(parent_collection, tam=3.0, seed=0):
    """Bolo calizo irregular, semienterrado (parte de la geometría bajo z=0)."""
    rng = random.Random(7919 * seed + 89)
    mb = _MB()
    mb.add(*_sphere(tam / 2.0, seg=8, rings=5,
                    scale=(rng.uniform(0.95, 1.15), rng.uniform(0.80, 0.95), 0.62),
                    off=(0, 0, tam * 0.24), rng=rng, jit=0.16),
           _mat("roca"))
    return mb.build("%s_roca" % PREFIX, parent_collection)


def build_acantilado(parent_collection, largo=40.0, alto=25.0, seed=0):
    """Acantilado calizo estratificado, tileable en X (frente hacia +Y).

    El perfil del frente y la ondulación de los bordes de estrato usan solo
    armónicos de periodo `largo`, así que dos módulos contiguos casan.
    """
    rng = random.Random(7919 * seed + 101)
    mb = _MB()

    nstr = max(4, int(round(alto / 3.6)))
    pesos = [rng.uniform(0.7, 1.35) for _ in range(nstr)]
    total = sum(pesos)
    zs = [0.0]
    for w in pesos:
        zs.append(zs[-1] + alto * w / total)
    zs[-1] = alto

    slope = 0.32 * alto
    ns = max(16, int(largo / 1.8))
    xs = [(-largo / 2.0) + largo * j / ns for j in range(ns + 1)]

    def _armonicos(a1r, a2r):
        return (rng.randint(1, 3), rng.uniform(*a1r), rng.uniform(0.0, TAU),
                rng.randint(3, 7), rng.uniform(*a2r), rng.uniform(0.0, TAU))

    # perfil Y por estrato (saliente/entrante) + retranqueo del techo (lean)
    par_y = []
    lean = []
    for i in range(nstr):
        zmid = (zs[i] + zs[i + 1]) / 2.0
        base = -slope * (zmid / alto)
        par_y.append((base,) + _armonicos((0.55, 0.95), (0.25, 0.50)))
        lean.append(rng.uniform(0.12, 0.45))  # la cara se inclina hacia atras
    # ondulación Z de cada borde interior de estrato
    par_z = [None] + [_armonicos((0.18, 0.40), (0.08, 0.20)) for _ in range(nstr - 1)] + [None]

    def yfun(x, i):
        base, k1, a1, p1, k2, a2, p2 = par_y[i]
        return (base + a1 * math.sin(TAU * k1 * x / largo + p1)
                + a2 * math.sin(TAU * k2 * x / largo + p2))

    def zfun(x, i):
        if i <= 0:
            return 0.0
        if i >= nstr:
            return alto
        k1, a1, p1, k2, a2, p2 = par_z[i]
        return (zs[i] + a1 * math.sin(TAU * k1 * x / largo + p1)
                + a2 * math.sin(TAU * k2 * x / largo + p2))

    mats = [_mat("caliza_clara"), _mat("caliza_ocre"), _mat("caliza_gris")]
    orden = []
    for i in range(nstr):
        if i % 2 == 0:
            orden.append(mats[0])
        else:
            orden.append(mats[1] if rng.random() < 0.7 else mats[2])

    for i in range(nstr):
        vs = []
        for j in range(ns + 1):  # fila inferior (borde i)
            vs.append((xs[j], yfun(xs[j], i), zfun(xs[j], i)))
        for j in range(ns + 1):  # fila superior (borde i+1, retranqueada)
            vs.append((xs[j], yfun(xs[j], i) - lean[i], zfun(xs[j], i + 1)))
        fs = []
        for j in range(ns):
            b0, b1 = j, j + 1
            t0, t1 = ns + 1 + j, ns + 2 + j
            fs.append((b0, t0, t1, b1))  # normal ~ +Y
        mb.add(vs, fs, orden[i])

        if i < nstr - 1:  # repisa entre estrato i y i+1 (normal ~ +Z)
            vs2 = []
            for j in range(ns + 1):
                vs2.append((xs[j], yfun(xs[j], i) - lean[i], zfun(xs[j], i + 1)))
            for j in range(ns + 1):
                vs2.append((xs[j], yfun(xs[j], i + 1), zfun(xs[j], i + 1)))
            fs2 = []
            for j in range(ns):
                f0, f1 = j, j + 1
                k0, k1_ = ns + 1 + j, ns + 2 + j
                fs2.append((f1, f0, k0, k1_))
            mb.add(vs2, fs2, orden[i + 1])

    yback = -(slope + 0.18 * alto)  # tapa superior plana (para casar con terreno)
    vs3 = []
    for j in range(ns + 1):
        vs3.append((xs[j], yfun(xs[j], nstr - 1) - lean[nstr - 1], alto))
    for j in range(ns + 1):
        vs3.append((xs[j], yback, alto))
    fs3 = []
    for j in range(ns):
        f0, f1 = j, j + 1
        k0, k1_ = ns + 1 + j, ns + 2 + j
        fs3.append((f1, f0, k0, k1_))
    mb.add(vs3, fs3, _mat("caliza_clara"))

    nveg = int(largo / 5.0) + 3  # vegetación colgante en las repisas
    for _ in range(nveg):
        li = rng.randint(1, nstr - 1)
        xr = rng.uniform(-0.45, 0.45) * largo
        ymid = (yfun(xr, li - 1) - lean[li - 1] + yfun(xr, li)) / 2.0
        r = rng.uniform(0.6, 1.3)
        mb.add(*_sphere(r, seg=7, rings=4, scale=(1.4, 0.9, 0.55),
                        off=(xr, ymid, zfun(xr, li) + r * 0.2), rng=rng, jit=0.15),
               _mat("colgante"), smooth=True)

    return mb.build("%s_acantilado" % PREFIX, parent_collection)


# ---------------------------------------------------------------------------
# MUESTRARIO
# ---------------------------------------------------------------------------
def build(parent_collection, seed=0, **params):
    """Muestrario en fila: piezas delante, acantilado de fondo. Devuelve Empty raíz."""
    root = bpy.data.objects.new("%s_muestrario" % PREFIX, None)
    root.empty_display_size = 2.0
    parent_collection.objects.link(root)

    def place(ob, x, y=0.0, rz=0.0):
        ob.parent = root
        ob.location = (x, y, 0.0)
        ob.rotation_euler = (0.0, 0.0, rz)
        return ob

    place(build_acantilado(parent_collection, largo=64.0, alto=20.0, seed=seed + 5), 0.0, -17.0)
    place(build_palmera(parent_collection, alto=8.0, seed=seed + 1), -21.0)
    place(build_palmera(parent_collection, alto=6.5, seed=seed + 2), -17.5)
    place(build_cipres(parent_collection, alto=10.0, seed=seed), -13.0)
    place(build_pino(parent_collection, alto=12.0, seed=seed), -6.0)
    place(build_adelfa(parent_collection, seed=seed), 0.5)
    place(build_jardinera(parent_collection, largo=6.0, seed=seed), 6.5)
    place(build_roca(parent_collection, tam=3.0, seed=seed + 3), 12.5)
    place(build_roca(parent_collection, tam=1.6, seed=seed + 4), 15.5)
    place(build_palmera(parent_collection, alto=7.0, seed=seed + 9), 19.0)
    return root
