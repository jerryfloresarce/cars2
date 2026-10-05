"""horquilla_loews.py — Rotonda central de la horquilla tipo Loews (Porto Corsa, Cars 2).

Genera PROCEDURALMENTE (Blender 5.1, sin bpy.ops de modelado ni texturas) el
parterre circular elevado con palmeras alrededor del cual gira la horquilla de
la curva 38 del sector "Monaco", copiando el fotograma de la pelicula:

  1. Anillo exterior bajo de piedra clara (murete ~1.1 m con remate).
  2. Banda perimetral de flores AZULES justo dentro del murete.
  3. Seto verde en anillo.
  4. Parterre superior elevado ~1.4 m dividido como una RUEDA: llanta de seto,
     8 radios/cunas de seto y relleno alternando flores blancas y rojas/rosas
     (visto desde arriba parece una llanta con radios — mundo Cars).
  5. DOS palmeras altas (~9 y ~7 m) con tronco curvado saliendo del centro.

API:
  build(parent_collection, radio=9.0, seed=0, **params)
      Crea UNA malla `LOEWS_rotonda` linkada a parent_collection y la
      devuelve. Origen en el centro, z=0 en la base. <= 6000 tris.

Unidades en metros. Estilo Cars 2: saturado, limpio, low-poly.
"""

import math
import random

import bpy
from mathutils import Vector

PREFIX = "LOEWS"
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Paleta plana estilo Cars 2 (color lineal, roughness)
# ---------------------------------------------------------------------------
_PALETA = {
    "piedra":        ((0.82, 0.74, 0.56), 0.92),
    "tierra":        ((0.27, 0.18, 0.10), 1.00),
    "seto":          ((0.065, 0.36, 0.085), 0.80),
    "seto_claro":    ((0.11, 0.46, 0.12), 0.78),
    "flor_azul":     ((0.10, 0.24, 0.88), 0.60),
    "flor_azul_cl":  ((0.30, 0.50, 0.98), 0.60),
    "flor_blanca":   ((0.95, 0.93, 0.85), 0.55),
    "flor_roja":     ((0.82, 0.05, 0.07), 0.60),
    "flor_rosa":     ((0.94, 0.30, 0.52), 0.60),
    "tronco":        ((0.40, 0.25, 0.11), 0.90),
    "palma":         ((0.07, 0.42, 0.10), 0.75),
    "palma_clara":   ((0.15, 0.55, 0.15), 0.75),
    "coco":          ((0.45, 0.28, 0.10), 0.85),
}


def _mat(key):
    """Devuelve (reutilizando si existe) el material plano MAT_LOEWS_<key>."""
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
    """Acumula (verts, faces, material, smooth) y construye una malla unica."""

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
# Primitivas (verts, faces) con winding hacia fuera
# ---------------------------------------------------------------------------
def _lathe(profile, seg=48, rng=None, jit=0.0):
    """Revolucion alrededor de Z. profile = [(radio, z), ...] recorrido asi:
    pared exterior SUBIENDO, coronacion hacia DENTRO, pared interior BAJANDO
    (radio 0 = polo). Asi las normales quedan hacia fuera/arriba/dentro."""
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
        if len(a) == 1 and len(b) > 1:
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((a[0], b[k2], b[k]))
        elif len(b) == 1 and len(a) > 1:
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((b[0], a[k], a[k2]))
        elif len(a) > 1 and len(b) > 1:
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((a[k], a[k2], b[k2], b[k]))
    return verts, faces


def _sphere(r=1.0, seg=8, rings=5, scale=(1, 1, 1), off=(0, 0, 0), rng=None,
            jit=0.0, yaw=0.0):
    """Esfera UV escalada, con giro opcional en Z ANTES del offset."""
    verts = []
    faces = []

    def j():
        return 1.0 + (rng.uniform(-jit, jit) if (rng is not None and jit) else 0.0)

    verts.append((0.0, 0.0, r * j()))
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
    verts.append((0.0, 0.0, -r * j()))

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
    c, s = math.cos(yaw), math.sin(yaw)
    ox, oy, oz = off
    out = []
    for (x, y, z) in verts:
        x, y, z = x * sx, y * sy, z * sz
        out.append((x * c - y * s + ox, x * s + y * c + oy, z + oz))
    return out, faces


def _tube(points, radii, sides=6, cap_top=True):
    """Barre una seccion circular por una polilinea (tronco curvado)."""
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


def _palma_frond(L, wmax, tanp, droop, yaw, base):
    """Palma plana: tira de quads con nervio central elevado, arqueada y caida."""
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


def _sector_flores(r0, r1, a0, a1, zb, dome, rng, nr=3, na=5):
    """Cama de flores en sector anular, abombada, normales +Z."""
    verts = []
    grid = []
    for i in range(nr + 1):
        fr = i / float(nr)
        r = r0 + (r1 - r0) * fr
        row = []
        for k in range(na + 1):
            fa = k / float(na)
            a = a0 + (a1 - a0) * fa
            bump = math.sin(math.pi * fr) * math.sin(math.pi * fa)
            z = zb + dome * bump + rng.uniform(-0.02, 0.02)
            row.append(len(verts))
            verts.append((r * math.cos(a), r * math.sin(a), z))
        grid.append(row)
    faces = []
    for i in range(nr):
        for k in range(na):
            faces.append((grid[i][k], grid[i + 1][k],
                          grid[i + 1][k + 1], grid[i][k + 1]))
    return verts, faces


def _palmera(mb, alto, base, lean_yaw, rng):
    """Palmera estilizada dentro del acumulador: tronco curvado + corona."""
    bx, by, bz = base
    lean = rng.uniform(0.14, 0.20) * alto
    npts = 7
    pts = []
    radii = []
    for i in range(npts):
        t = i / (npts - 1.0)
        off = lean * (t ** 1.7)
        pts.append((bx + math.cos(lean_yaw) * off,
                    by + math.sin(lean_yaw) * off,
                    bz + t * alto * 0.92))
        r = (0.040 - 0.020 * t) * alto
        if i % 2 == 1:
            r *= 1.12  # anillos del tronco
        radii.append(max(r, 0.05))
    mb.add(*_tube(pts, radii, sides=6), _mat("tronco"), smooth=True)

    crown = Vector(pts[-1])
    mb.add(*_sphere(0.05 * alto + 0.12, seg=7, rings=4, off=crown),
           _mat("palma"), smooth=True)
    for _ in range(3):  # cocos
        a = rng.uniform(0.0, TAU)
        rc = 0.028 * alto + 0.06
        cc = crown + Vector((math.cos(a) * rc * 1.8, math.sin(a) * rc * 1.8, -rc * 1.2))
        mb.add(*_sphere(rc, seg=6, rings=3, off=cc), _mat("coco"), smooth=True)

    nf = rng.randint(9, 11)
    Lf = alto * 0.42
    for i in range(nf):
        yaw = TAU * i / nf + rng.uniform(-0.15, 0.15)
        if i % 2 == 0:
            tanp = rng.uniform(0.55, 0.75)
            droop = rng.uniform(0.72, 0.90)
            key = "palma"
        else:
            tanp = rng.uniform(0.22, 0.42)
            droop = rng.uniform(1.00, 1.20)
            key = "palma_clara"
        L = Lf * rng.uniform(0.85, 1.05)
        mb.add(*_palma_frond(L, Lf * 0.16, tanp, droop, yaw, crown),
               _mat(key), smooth=True)


# ---------------------------------------------------------------------------
# BUILD
# ---------------------------------------------------------------------------
def build(parent_collection, radio=9.0, seed=0, **params):
    """Rotonda de la horquilla Loews. Devuelve la malla LOEWS_rotonda."""
    rng = random.Random(7919 * seed + 137)
    mb = _MB()
    R = float(radio)
    SEG = 48

    # --- suelo de tierra bajo todo el interior ------------------------------
    # fase visual F1 (3.5, PARCHES_F1_mascara.md A3.a, aplicado por el integrador): cesped en la isleta; _mat("tierra") como respaldo
    mb.add(*_lathe([(R - 0.35, 0.03), (0.0, 0.03)], seg=SEG), bpy.data.materials.get('MAT_cesped') or _mat("tierra"))

    # --- 1. murete exterior de piedra clara (~1.1 m con remate) -------------
    perfil_murete = [
        (R - 0.02, 0.00),
        (R, 0.45),
        (R - 0.01, 0.90),          # pared exterior, ligero talud
        (R + 0.10, 0.93),          # vuelo del remate
        (R + 0.10, 1.10),
        (R - 0.52, 1.10),          # cara superior del remate
        (R - 0.52, 0.93),
        (R - 0.42, 0.90),          # bajo el vuelo interior
        (R - 0.41, 0.45),
        (R - 0.42, 0.00),          # pared interior
    ]
    mb.add(*_lathe(perfil_murete, seg=SEG), _mat("piedra"))

    # --- 2. banda perimetral de flores azules --------------------------------
    ro_b, ri_b = R - 0.45, R - 1.60
    rm_b = (ro_b + ri_b) / 2.0
    perfil_azul = [
        (ro_b, 0.00),
        (ro_b - 0.06, 0.42),
        (rm_b, 0.62),
        (ri_b + 0.06, 0.42),
        (ri_b, 0.00),
    ]
    mb.add(*_lathe(perfil_azul, seg=SEG, rng=rng, jit=0.030),
           _mat("flor_azul"), smooth=True)
    for i in range(26):  # matas azul claro medio hundidas en la banda
        a = TAU * (i + rng.uniform(-0.3, 0.3)) / 26.0
        rr = rm_b + rng.uniform(-0.30, 0.30)
        mb.add(*_sphere(rng.uniform(0.13, 0.19), seg=5, rings=3,
                        scale=(1.25, 1.25, 0.75),
                        off=(rr * math.cos(a), rr * math.sin(a),
                             0.52 + rng.uniform(-0.04, 0.03))),
               _mat("flor_azul_cl"), smooth=True)

    # --- 3. seto verde en anillo --------------------------------------------
    ro_s, ri_s = R - 1.70, R - 2.60
    rm_s = (ro_s + ri_s) / 2.0
    perfil_seto = [
        (ro_s - 0.06, 0.00),
        (ro_s + 0.05, 0.48),
        (ro_s - 0.08, 1.00),
        (rm_s, 1.16),
        (ri_s + 0.08, 1.00),
        (ri_s - 0.05, 0.48),
        (ri_s + 0.06, 0.00),
    ]
    mb.add(*_lathe(perfil_seto, seg=SEG, rng=rng, jit=0.020),
           _mat("seto"), smooth=True)

    # --- 4. parterre superior elevado (~1.4 m) tipo RUEDA -------------------
    rp = R - 2.75
    ztop = 1.40
    perfil_parterre = [
        (rp - 0.02, 0.00),
        (rp, 0.70),
        (rp - 0.01, 1.22),         # muro de piedra (base oculta tras el seto)
        (rp + 0.09, 1.25),
        (rp + 0.09, 1.38),
        (rp - 0.34, ztop),         # remate
    ]
    mb.add(*_lathe(perfil_parterre, seg=SEG), _mat("piedra"))
    mb.add(*_lathe([(rp - 0.30, ztop), (0.0, ztop)], seg=SEG), bpy.data.materials.get('MAT_cesped') or _mat("tierra"))

    # llanta: seto anular en el borde superior
    ro_l, ri_l = rp - 0.12, rp - 0.72
    rm_l = (ro_l + ri_l) / 2.0
    perfil_llanta = [
        (ro_l - 0.04, ztop),
        (ro_l + 0.03, ztop + 0.28),
        (rm_l, ztop + 0.52),
        (ri_l - 0.03, ztop + 0.28),
        (ri_l + 0.04, ztop),
    ]
    mb.add(*_lathe(perfil_llanta, seg=SEG, rng=rng, jit=0.018),
           _mat("seto_claro"), smooth=True)

    # buje central de seto alrededor de las palmeras
    perfil_buje = [
        (1.30, ztop),
        (1.38, ztop + 0.30),
        (0.95, ztop + 0.58),
        (0.55, ztop + 0.30),
        (0.50, ztop),
    ]
    mb.add(*_lathe(perfil_buje, seg=24, rng=rng, jit=0.05),
           _mat("seto_claro"), smooth=True)

    # 8 radios de seto (rollos alargados) entre buje y llanta
    r_in_radio, r_out_radio = 1.15, ri_l + 0.20
    L_radio = r_out_radio - r_in_radio
    for k in range(8):
        a = TAU * k / 8.0
        rc = (r_in_radio + r_out_radio) / 2.0
        mb.add(*_sphere(1.0, seg=8, rings=4,
                        scale=(L_radio * 0.56, 0.34, 0.30), yaw=a,
                        off=(rc * math.cos(a), rc * math.sin(a), ztop + 0.16),
                        rng=rng, jit=0.05),
               _mat("seto"), smooth=True)

    # 8 cunas de flores alternando blancas y rojas/rosas
    r0f, r1f = 1.30, ri_l + 0.06
    half_gap = 0.115  # hueco angular para el radio de seto
    for k in range(8):
        a0 = TAU * k / 8.0 + half_gap
        a1 = TAU * (k + 1) / 8.0 - half_gap
        if k % 2 == 0:
            key = "flor_blanca"
        else:
            key = "flor_roja" if (k // 2) % 2 == 0 else "flor_rosa"
        mb.add(*_sector_flores(r0f, r1f, a0, a1, ztop + 0.04, 0.26, rng),
               _mat(key), smooth=True)

    # --- 5. dos palmeras saliendo del centro --------------------------------
    _palmera(mb, alto=9.0, base=(0.42, 0.22, ztop), lean_yaw=0.55, rng=rng)
    _palmera(mb, alto=7.0, base=(-0.45, -0.28, ztop),
             lean_yaw=math.pi + 0.9, rng=rng)

    return mb.build("%s_rotonda" % PREFIX, parent_collection)
