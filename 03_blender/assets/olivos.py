"""olivos.py — Vegetación extra mediterránea low-poly estilo Cars 2 (Porto Corsa).

Kit procedural para Blender 5.1 (bpy puro, sin bpy.ops de modelado, sin
texturas de imagen). Estilo Riviera italiana saturada y limpia. Unidades en
metros, origen en el centro de la base (z=0 en el suelo), cara principal
mirando a +Y. Cada pieza <= 2000 tris.

Piezas (cada una crea UN objeto malla linkado a parent_collection y lo devuelve):
  build_olivo(parent_collection, alto=5.0, seed=0)
      Olivo low-poly: tronco grueso y nudoso (con collar de raíces y nudos)
      que se abre en 2-3 ramas, copa en 3-5 masas redondeadas alternando
      verde salvia y verde plateado apagado.
  build_seto(parent_collection, largo=6.0, alto=1.2, seed=0)
      Seto rectangular recortado (jardinería formal) verde vivo con leve
      irregularidad en la superficie y algún brote asomando.
  build_matorral(parent_collection, seed=0)
      Mata baja mediterránea (0.8-1.2 m) verde oscuro, achaparrada, con
      algún brote más claro.

  build(parent_collection, seed=0, **params)
      Muestrario en fila: olivos, seto y matorrales. Devuelve el Empty raíz
      OLI_muestrario.
"""

import math
import random

import bpy
from mathutils import Vector

PREFIX = "OLI"
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Paleta plana estilo Cars 2 (color lineal, roughness)
# ---------------------------------------------------------------------------
_PALETA = {
    "tronco_olivo":   ((0.27, 0.19, 0.10), 0.95),
    "hoja_salvia":    ((0.22, 0.34, 0.14), 0.80),
    "hoja_plata":     ((0.38, 0.46, 0.27), 0.75),
    "seto":           ((0.09, 0.33, 0.10), 0.80),
    "seto_claro":     ((0.17, 0.45, 0.14), 0.78),
    "matorral":       ((0.060, 0.215, 0.075), 0.85),
    "matorral_claro": ((0.130, 0.320, 0.120), 0.82),
}


def _mat(key):
    """Devuelve (reutilizando si existe) el material plano MAT_OLI_<key>."""
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
    """Barre una sección circular por una polilínea (troncos y ramas)."""
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


# ---------------------------------------------------------------------------
# PIEZAS
# ---------------------------------------------------------------------------
def build_olivo(parent_collection, alto=5.0, seed=0):
    """Olivo low-poly: tronco grueso nudoso, 2-3 ramas, copa en 3-5 masas
    redondeadas verde salvia / verde plateado apagado."""
    rng = random.Random(104729 * seed + 13)
    mb = _MB()

    a = alto
    ht = a * rng.uniform(0.40, 0.48)  # altura del tronco principal

    # --- tronco: polilínea con deriva aleatoria + radios con bultos (nudos)
    npts = 6
    pts = [(0.0, 0.0, 0.0)]
    dx = dy = 0.0
    for i in range(1, npts):
        t = i / (npts - 1.0)
        dx += rng.uniform(-1.0, 1.0) * 0.045 * a
        dy += rng.uniform(-1.0, 1.0) * 0.045 * a
        pts.append((dx, dy, t * ht))
    radii = []
    for i in range(npts):
        t = i / (npts - 1.0)
        r = a * (0.080 - 0.042 * t)
        if i % 2 == 1:
            r *= 1.24  # anillos nudosos
        radii.append(r)
    mb.add(*_tube(pts, radii, sides=8), _mat("tronco_olivo"), smooth=True)

    # --- collar de raíces en la base (se abre hacia el suelo)
    collar = [
        (0.150 * a, 0.0),
        (0.104 * a, 0.055 * a),
        (0.076 * a, 0.115 * a),
    ]
    mb.add(*_lathe(collar, seg=8, rng=rng, jit=0.12), _mat("tronco_olivo"), smooth=True)

    # --- nudos: bultos pegados al tronco
    for _ in range(3):
        i = rng.randint(1, npts - 2)
        px, py, pz = pts[i]
        th = rng.uniform(0.0, TAU)
        rr = radii[i] * 0.72
        mb.add(*_sphere(rr, seg=6, rings=3,
                        off=(px + math.cos(th) * radii[i] * 0.8,
                             py + math.sin(th) * radii[i] * 0.8, pz),
                        rng=rng, jit=0.15),
               _mat("tronco_olivo"), smooth=True)

    # --- ramas (2-3) desde lo alto del tronco hacia los centros de copa
    top = Vector(pts[-1])
    nb = rng.randint(2, 3)
    yaw0 = rng.uniform(0.0, TAU)
    centros = []
    for i in range(nb):
        yaw = yaw0 + TAU * i / nb + rng.uniform(-0.35, 0.35)
        d = a * rng.uniform(0.10, 0.20)
        cz = a * rng.uniform(0.58, 0.68)
        c = Vector((top.x + math.cos(yaw) * d, top.y + math.sin(yaw) * d, cz))
        centros.append(c)
        p0 = Vector(pts[npts - 2])
        p2 = c - Vector((0, 0, 0.06 * a))
        p1 = (p0 + p2) / 2 + Vector((0, 0, 0.035 * a))
        mb.add(*_tube([p0, p1, p2],
                      [0.040 * a, 0.028 * a, 0.016 * a], sides=6),
               _mat("tronco_olivo"), smooth=True)

    # --- copa: 3-5 masas redondeadas (salvia / plata alternadas)
    nm = rng.randint(4, 5)
    masas = list(centros)
    # masa central alta para coronar hasta ~alto
    masas.append(Vector((top.x * 0.6, top.y * 0.6, a * 0.73)))
    while len(masas) < nm:
        yaw = rng.uniform(0.0, TAU)
        d = a * rng.uniform(0.08, 0.17)
        masas.append(Vector((top.x + math.cos(yaw) * d,
                             top.y + math.sin(yaw) * d,
                             a * rng.uniform(0.60, 0.70))))
    masas = masas[:max(nm, 3)]
    for i, c in enumerate(masas):
        r = a * rng.uniform(0.215, 0.275)
        key = "hoja_salvia" if i % 2 == 0 else "hoja_plata"
        mb.add(*_sphere(r, seg=9, rings=5,
                        scale=(rng.uniform(1.00, 1.18), rng.uniform(1.00, 1.18), 0.82),
                        off=c, rng=rng, jit=0.09),
               _mat(key), smooth=True)

    return mb.build("%s_olivo" % PREFIX, parent_collection)


def build_seto(parent_collection, largo=6.0, alto=1.2, seed=0):
    """Seto rectangular recortado verde, con leve irregularidad y brotes."""
    rng = random.Random(104729 * seed + 31)
    mb = _MB()

    W = min(0.85, alto * 0.75)   # anchura del seto
    ch = min(0.16, W * 0.22, alto * 0.18)  # chaflán superior "recortado"

    # sección (y, z) de abajo-izquierda a abajo-derecha pasando por arriba
    cs = [
        (-W / 2.0, 0.0),
        (-W / 2.0, alto - ch),
        (-W / 2.0 + ch, alto),
        (0.0, alto + 0.02),
        (W / 2.0 - ch, alto),
        (W / 2.0, alto - ch),
        (W / 2.0, 0.0),
    ]

    ns = max(5, int(round(largo * 1.6)))
    verts = []
    rows = []
    for i in range(ns + 1):
        t = i / float(ns)
        x = (t - 0.5) * largo
        fy = 1.0 + rng.uniform(-0.030, 0.045)  # leve irregularidad por estación
        fz = 1.0 + rng.uniform(-0.025, 0.040)
        row = []
        for (y, z) in cs:
            jy = rng.uniform(-0.02, 0.02) if z > 0.01 else 0.0
            jz = rng.uniform(-0.02, 0.02) if z > 0.01 else 0.0
            row.append(len(verts))
            verts.append((x, y * fy + jy, z * fz + jz if z > 0.01 else 0.0))
        rows.append(row)

    faces = []
    m = len(cs)
    for i in range(ns):
        A = rows[i]
        B = rows[i + 1]
        for k in range(m - 1):
            faces.append((A[k], B[k], B[k + 1], A[k + 1]))
    faces.append(tuple(rows[0]))            # tapa -X
    faces.append(tuple(reversed(rows[-1])))  # tapa +X
    mb.add(verts, faces, _mat("seto"), smooth=False)

    # brotes claros asomando del plano superior (leve irregularidad viva)
    nbr = max(3, int(largo * 0.9))
    for _ in range(nbr):
        x = rng.uniform(-0.44, 0.44) * largo
        y = rng.uniform(-0.30, 0.30) * W
        r = rng.uniform(0.07, 0.12)
        mb.add(*_sphere(r, seg=6, rings=3, scale=(1.2, 1.2, 0.8),
                        off=(x, y, alto + r * 0.25), rng=rng, jit=0.15),
               _mat("seto_claro"), smooth=True)

    return mb.build("%s_seto" % PREFIX, parent_collection)


def build_matorral(parent_collection, seed=0):
    """Mata baja mediterránea (0.8-1.2 m), verde oscuro, achaparrada."""
    rng = random.Random(104729 * seed + 57)
    mb = _MB()
    h = rng.uniform(0.8, 1.2)

    # masa principal aplastada + lóbulos laterales
    mb.add(*_sphere(h * 0.52, seg=8, rings=5,
                    scale=(1.35, 1.15, 0.80), off=(0, 0, h * 0.42),
                    rng=rng, jit=0.13),
           _mat("matorral"), smooth=True)
    nl = rng.randint(2, 4)
    yaw0 = rng.uniform(0.0, TAU)
    for i in range(nl):
        yaw = yaw0 + TAU * i / nl + rng.uniform(-0.4, 0.4)
        d = h * rng.uniform(0.42, 0.62)
        r = h * rng.uniform(0.26, 0.36)
        mb.add(*_sphere(r, seg=7, rings=4,
                        scale=(1.2, 1.1, 0.72),
                        off=(math.cos(yaw) * d, math.sin(yaw) * d, r * 0.55),
                        rng=rng, jit=0.14),
               _mat("matorral"), smooth=True)

    # brotes claros arriba
    for _ in range(rng.randint(2, 3)):
        x = rng.uniform(-0.35, 0.35) * h
        y = rng.uniform(-0.30, 0.30) * h
        r = rng.uniform(0.10, 0.16) * h
        mb.add(*_sphere(r, seg=6, rings=3,
                        off=(x, y, h * 0.72 + rng.uniform(0.0, 0.08)),
                        rng=rng, jit=0.15),
               _mat("matorral_claro"), smooth=True)

    return mb.build("%s_matorral" % PREFIX, parent_collection)


# ---------------------------------------------------------------------------
# MUESTRARIO
# ---------------------------------------------------------------------------
def build(parent_collection, seed=0, **params):
    """Muestrario en fila: olivos, seto y matorrales. Devuelve Empty raíz."""
    root = bpy.data.objects.new("%s_muestrario" % PREFIX, None)
    root.empty_display_size = 2.0
    parent_collection.objects.link(root)

    def place(ob, x, y=0.0, rz=0.0):
        ob.parent = root
        ob.location = (x, y, 0.0)
        ob.rotation_euler = (0.0, 0.0, rz)
        return ob

    place(build_olivo(parent_collection, alto=5.5, seed=seed), -7.5)
    place(build_olivo(parent_collection, alto=4.5, seed=seed + 1), -3.0)
    place(build_olivo(parent_collection, alto=6.0, seed=seed + 2), 1.5, -1.0)
    place(build_seto(parent_collection, largo=6.0, alto=1.2, seed=seed), 7.0, 0.5)
    place(build_matorral(parent_collection, seed=seed), 11.5)
    place(build_matorral(parent_collection, seed=seed + 1), 13.2, -1.2)
    place(build_matorral(parent_collection, seed=seed + 2), 12.4, 1.4)
    return root
