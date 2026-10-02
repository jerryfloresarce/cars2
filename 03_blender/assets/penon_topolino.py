"""penon_topolino.py — Peñón Topolino de Porto Corsa (Cars 2), Blender 5.1.

Promontorio rocoso cuya silueta de perfil recuerda el capó de un Fiat 500
Topolino de 1948: montículo redondeado con "morro" descendente hacia el mar
(+Y) y dos "aletas" laterales (guardabarros) flanqueando el morro. Caliza
gris-ocre ESTRATIFICADA con repisas, base socavada por el mar, meseta
superior aplanada de ~70x40 m (asiento futuro del casino) y matas de
vegetación mediterránea colgante.

100%% procedural: loft de secciones transversales superelípticas a lo largo
del eje Y con perfil de silueta/planta por splines Catmull-Rom + ruido fbm +
repisas periódicas. Sin bpy.ops, sin texturas de imagen.

Piezas (kit):
  build(parent_collection, largo=160, ancho=90, alto=55, seed=0,
        con_vegetacion=True)                -> Empty raíz PENON_topolino
  build_roca(parent_collection, ...)        -> malla PENON_roca (~11k tris)
  build_vegetacion(parent_collection, ...)  -> malla PENON_vegetacion (~2k tris)

Unidades en metros, origen en el centro de la base, z=0 en el suelo,
morro mirando a +Y.
"""

import math
import random

import bpy
import bmesh
from mathutils import Vector

# ---------------------------------------------------------------- ruido ----
try:
    from mathutils import noise as _mnoise

    def _n3(x, y, z):
        return _mnoise.noise(Vector((x, y, z)))
except Exception:  # fallback puro python (valor-ruido trilineal)
    def _h(ix, iy, iz):
        n = (ix * 374761393 + iy * 668265263 + iz * 1440662683) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

    def _n3(x, y, z):
        ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
        fx, fy, fz = x - ix, y - iy, z - iz

        def s(t):
            return t * t * (3.0 - 2.0 * t)

        fx, fy, fz = s(fx), s(fy), s(fz)
        v = 0.0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = ((fx if dx else 1 - fx) * (fy if dy else 1 - fy) *
                         (fz if dz else 1 - fz))
                    v += w * _h(ix + dx, iy + dy, iz + dz)
        return v * 2.0 - 1.0


def _fbm(x, y, z, so):
    """3 octavas: bultos grandes, medianos y grano fino (metros)."""
    return (_n3(x * 0.014 + so, y * 0.014 + so * 0.7, z * 0.014) * 7.0 +
            _n3(x * 0.05 + so * 2.1, y * 0.05 + 11.3, z * 0.05) * 2.6 +
            _n3(x * 0.15 + so * 3.3, y * 0.15 + 23.7, z * 0.15 + 5.1) * 1.0)


def _sstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _spline(pts, x):
    """Interpolación Catmull-Rom (hermite) sobre puntos (x, y) crecientes."""
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if x0 <= x <= x1:
            xm, ym = pts[max(i - 1, 0)]
            x2, y2 = pts[min(i + 2, len(pts) - 1)]
            t = (x - x0) / (x1 - x0)
            m0 = (y1 - ym) / (x1 - xm) * (x1 - x0)
            m1 = (y2 - y0) / (x2 - x0) * (x1 - x0)
            t2, t3 = t * t, t * t * t
            return ((2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 +
                    (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * m1)
    return pts[-1][1]


# ---------------------------------------------------- perfiles del peñón ----
# Silueta de perfil (capó Topolino): alto y redondeado atrás (-Y, tierra),
# meseta, pendiente convexa del capó y morro romo cayendo al mar (+Y).
_SIL_MAIN = [(-1.0, 0.0), (-0.86, 0.62), (-0.66, 0.90), (-0.38, 1.0),
             (0.05, 0.99), (0.38, 0.82), (0.62, 0.50), (0.80, 0.42),
             (0.90, 0.37), (0.97, 0.26), (1.0, 0.0)]
# planta: ancha en el domo, estrechándose hacia el morro para que las
# aletas laterales sobresalgan como guardabarros
_PLAN_MAIN = [(-1.0, 0.0), (-0.90, 0.52), (-0.62, 0.86), (-0.22, 1.0),
              (0.22, 0.90), (0.52, 0.66), (0.78, 0.42), (0.94, 0.24),
              (1.0, 0.0)]
# Aletas (guardabarros): montículo alargado con lomo redondeado.
_SIL_ALETA = [(-1.0, 0.0), (-0.65, 0.72), (-0.25, 1.0), (0.25, 0.92),
              (0.60, 0.66), (0.85, 0.40), (1.0, 0.0)]
_PLAN_ALETA = [(-1.0, 0.0), (-0.70, 0.62), (-0.20, 1.0), (0.30, 0.92),
               (0.70, 0.62), (1.0, 0.0)]


def _loft_rock(verts, faces, sil, plan, L, W, H, n_st, n_arc,
               origin, yaw, so, opts, collect=None):
    """Loft de anillos transversales cerrados a lo largo de Y local.

    Cada anillo: arco superelíptico (base dcha -> cima -> base izda) + 2
    puntos de faldón bajo z=0. Tapa con vértices polo en ambos extremos.
    """
    R = n_arc + 2
    ca, sa = math.cos(yaw), math.sin(yaw)
    ox, oy, oz = origin
    mes = opts.get("meseta")
    q = opts.get("q", 2.6)
    band_h = opts.get("band_h", 6.8)
    ledge_amp = opts.get("ledge_amp", 1.6)
    ero_h = opts.get("ero_h", 8.0)
    ero_amp = opts.get("ero_amp", 5.0)

    def to_world(px, ly, pz):
        return (px * ca - ly * sa + ox, px * sa + ly * ca + oy, pz + oz)

    rings = []
    for j in range(1, n_st - 1):
        ny = -math.cos(math.pi * j / (n_st - 1))  # denso en los extremos
        jy = math.sin(math.pi * j / (n_st - 1))   # atenúa jitter en extremos
        h = max(H * _spline(sil, ny), 0.6)
        w = max(W * 0.5 * _spline(plan, ny), 0.6)
        ly = ny * L * 0.5
        ring = []
        for k in range(n_arc):
            t = k / (n_arc - 1.0)
            th = math.pi * t
            c, s = math.cos(th), math.sin(th)
            xs = math.copysign(abs(c) ** (2.0 / q), c)
            zs = abs(s) ** (2.0 / q)
            px, pz = xs * w, zs * h
            dl = math.hypot(xs, zs) or 1.0
            dx, dz = xs / dl, zs / dl  # normal aprox. en el plano del anillo
            # --- meseta: aplanar la cima dentro de la elipse (borde neto) ---
            mf = 0.0
            if mes:
                ex = px / mes["rx"]
                ey = (ly - mes["cy"]) / mes["ry"]
                d2 = ex * ex + ey * ey
                if d2 < 1.0:
                    top_w = _sstep((pz - 0.5 * mes["h"]) / (0.5 * mes["h"]))
                    mf = _sstep((1.0 - d2) * 2.4) * top_w
                    pz = pz * (1.0 - mf) + mes["h"] * mf
            # --- ruido orgánico (amortiguado en la meseta) ---
            nz = _fbm(px, ly, pz, so) * (1.0 - 0.92 * mf)
            # --- repisas/estratos: cornisa periódica en laderas ---
            steep = 1.0 - zs
            ph = 2.5 * _n3(px * 0.02 + so, ly * 0.02, 4.4)
            ledge = max(0.0, math.cos(2.0 * math.pi * pz / band_h + ph)) ** 3
            bul = ledge_amp * ledge * steep * (1.0 - mf)
            px += dx * (nz + bul)
            pz += dz * (nz * 0.55 - bul * 0.35)
            pz = max(pz, 0.0)
            # --- jitter longitudinal para romper los anillos ---
            lyv = ly + _n3(px * 0.03 + so * 1.7, pz * 0.03, 2.2) * 3.2 * \
                jy * (1.0 - mf)
            # --- socavado marino en la base (muesca corta y profunda) ---
            if pz < ero_h:
                f = 1.0 - pz / ero_h
                f = f * f * f * (0.6 + 0.4 * (0.5 + 0.5 * _n3(
                    px * 0.05, ly * 0.05 + so, 9.1)))
                px -= math.copysign(min(abs(px) * 0.8, ero_amp * f), px)
            wx, wy, wz = to_world(px, lyv, pz)
            ring.append(len(verts))
            verts.append((wx, wy, wz))
            if collect is not None and 0.06 < t < 0.94:
                collect.append((Vector((wx, wy, wz)),
                                Vector((dx * ca, dx * sa, dz)).normalized(),
                                mf))
        # faldón bajo el nivel del suelo (se hunde en el terreno, tucked)
        wb = w * 0.55
        for bx in (-wb, wb):
            wx, wy, wz = to_world(bx, ly, -2.4)
            ring.append(len(verts))
            verts.append((wx, wy, wz))
        rings.append(ring)

    # polos en los extremos
    pole_a = len(verts)
    verts.append(to_world(0.0, -L * 0.5, -0.9))
    pole_b = len(verts)
    verts.append(to_world(0.0, L * 0.5, -0.9))

    for a, b in zip(rings, rings[1:]):
        for k in range(R):
            k2 = (k + 1) % R
            faces.append((a[k], a[k2], b[k2], b[k]))
    for k in range(R):
        k2 = (k + 1) % R
        faces.append((pole_a, rings[0][k], rings[0][k2]))
        faces.append((pole_b, rings[-1][k2], rings[-1][k]))


def _rock_geometry(largo, ancho, alto, seed):
    """Geometría completa (cuerpo + 2 aletas) y candidatos de vegetación."""
    verts, faces, collect = [], [], []
    so = seed * 17.37 + 3.1
    meseta = {"rx": ancho * 0.235, "ry": largo * 0.22,
              "cy": -largo * 0.06, "h": alto * 0.96}
    opts_main = {"q": 2.7, "band_h": 9.5, "ledge_amp": 2.4,
                 "ero_h": 5.5, "ero_amp": 5.0, "meseta": meseta}
    _loft_rock(verts, faces, _SIL_MAIN, _PLAN_MAIN, largo, ancho, alto,
               88, 64, (0.0, 0.0, 0.0), 0.0, so, opts_main, collect)

    # aletas laterales sobresaliendo como guardabarros junto al morro
    opts_al = {"q": 2.4, "band_h": 9.5, "ledge_amp": 1.6,
               "ero_h": 4.5, "ero_amp": 3.0, "meseta": None}
    la, wa, ha = largo * 0.50, ancho * 0.30, alto * 0.42
    for side, dseed in ((1.0, 5.0), (-1.0, 11.0)):
        _loft_rock(verts, faces, _SIL_ALETA, _PLAN_ALETA, la, wa, ha,
                   30, 26,
                   (side * ancho * 0.40, largo * 0.21, 0.0),
                   side * 0.16, so + dseed, opts_al, collect)
    return verts, faces, collect, meseta


# ------------------------------------------------------------ materiales ----
def _mat(name, color, rough=0.92):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                bsdf = n
                break
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*color, 1.0)
    return m


def _recalc_and_smooth(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True


# ----------------------------------------------------------------- piezas ----
def build_roca(parent_collection, largo=160.0, ancho=90.0, alto=55.0,
               seed=0, _shared=None, **kw):
    """Cuerpo rocoso PENON_roca: caliza estratificada con meseta y aletas."""
    verts, faces, collect, meseta = _rock_geometry(largo, ancho, alto, seed)
    if _shared is not None:
        _shared["candidates"] = collect
        _shared["meseta"] = meseta

    me = bpy.data.meshes.new("PENON_roca")
    me.from_pydata(verts, [], faces)
    me.validate()
    _recalc_and_smooth(me)

    mats = (
        _mat("MAT_PENON_caliza", (0.520, 0.400, 0.240), 0.95),
        _mat("MAT_PENON_caliza_clara", (0.700, 0.575, 0.360), 0.95),
        _mat("MAT_PENON_caliza_oscura", (0.340, 0.260, 0.165), 0.95),
        _mat("MAT_PENON_meseta", (0.720, 0.600, 0.380), 0.93),
    )
    for m in mats:
        me.materials.append(m)

    # bandas alineadas con la fase de las cornisas: el cambio de color
    # cae justo en la repisa y el borde dentado queda disimulado
    so = seed * 17.37 + 3.1
    band_h = 9.5
    patron = (0, 1, 0, 2)
    for p in me.polygons:
        c = p.center
        ex = c.x / meseta["rx"]
        ey = (c.y - meseta["cy"]) / meseta["ry"]
        if ex * ex + ey * ey < 1.05 and c.z > 0.88 * meseta["h"]:
            p.material_index = 3
        elif c.z < 3.5:
            p.material_index = 2  # zócalo oscuro lamido por el mar
        else:
            ph = 2.5 * _n3(c.x * 0.02 + so, c.y * 0.02, 4.4)
            b = math.floor(c.z / band_h + ph / (2.0 * math.pi))
            p.material_index = patron[b % 4]

    obj = bpy.data.objects.new("PENON_roca", me)
    parent_collection.objects.link(obj)
    return obj


def build_vegetacion(parent_collection, largo=160.0, ancho=90.0, alto=55.0,
                     seed=0, candidates=None, **kw):
    """Matas mediterráneas PENON_vegetacion: asentadas en repisas y colgantes."""
    if candidates is None:
        _v, _f, candidates, _m = _rock_geometry(largo, ancho, alto, seed)
    rng = random.Random(seed * 91 + 101)

    sits = [c for c in candidates
            if c[1].z > 0.5 and 4.0 < c[0].z < alto * 1.05 and c[2] < 0.6]
    hangs = [c for c in candidates
             if 0.0 <= c[1].z < 0.5 and c[0].z > 11.0]
    rng.shuffle(sits)
    rng.shuffle(hangs)

    placed = []

    def pick(pool, count):
        out = []
        for pos, nrm, _mf in pool:
            if len(out) >= count:
                break
            if all((pos - p).length > 6.0 for p in placed):
                placed.append(pos)
                out.append((pos, nrm))
        return out

    verts, faces, face_mat = [], [], []

    def blob(center, r, sz):
        u, v = 7, 4
        rings_i = []
        for i in range(1, v):
            phi = math.pi * i / v
            zc, rc = math.cos(phi), math.sin(phi)
            row = []
            for k in range(u):
                th = 2.0 * math.pi * k / u + rng.random() * 0.5
                rr = r * (0.72 + 0.55 * rng.random())
                row.append(len(verts))
                verts.append((center.x + rc * rr * math.cos(th),
                              center.y + rc * rr * math.sin(th),
                              center.z + zc * r * sz *
                              (0.8 + 0.4 * rng.random())))
            rings_i.append(row)
        top = len(verts)
        verts.append((center.x, center.y, center.z + r * sz))
        bot = len(verts)
        verts.append((center.x, center.y, center.z - r * sz * 0.75))
        mi = 0 if rng.random() < 0.65 else 1
        for k in range(u):
            k2 = (k + 1) % u
            faces.append((top, rings_i[0][k], rings_i[0][k2]))
            face_mat.append(mi)
            for i in range(len(rings_i) - 1):
                faces.append((rings_i[i][k], rings_i[i + 1][k],
                              rings_i[i + 1][k2], rings_i[i][k2]))
                face_mat.append(mi)
            faces.append((bot, rings_i[-1][k2], rings_i[-1][k]))
            face_mat.append(mi)

    for pos, nrm in pick(sits, 34):  # matas asentadas en repisas
        r = rng.uniform(2.0, 4.2)
        blob(pos + nrm * 0.4 - Vector((0, 0, 0.3)), r, 0.55)
    for pos, nrm in pick(hangs, 20):  # matas colgantes en la pared
        r = rng.uniform(1.8, 3.2)
        blob(pos + nrm * 0.3 - Vector((0, 0, r * 0.6)), r, 1.5)

    me = bpy.data.meshes.new("PENON_vegetacion")
    me.from_pydata(verts, [], faces)
    me.validate()
    _recalc_and_smooth(me)
    me.materials.append(_mat("MAT_PENON_vegetacion", (0.062, 0.190, 0.058), 0.9))
    me.materials.append(_mat("MAT_PENON_vegetacion_clara",
                             (0.128, 0.300, 0.085), 0.9))
    for p, mi in zip(me.polygons, face_mat):
        p.material_index = mi

    obj = bpy.data.objects.new("PENON_vegetacion", me)
    parent_collection.objects.link(obj)
    return obj


def build(parent_collection, largo=160.0, ancho=90.0, alto=55.0, seed=0,
          con_vegetacion=True, **params):
    """Peñón completo. Devuelve el Empty raíz PENON_topolino."""
    root = bpy.data.objects.new("PENON_topolino", None)
    root.empty_display_size = 5.0
    parent_collection.objects.link(root)

    shared = {}
    roca = build_roca(parent_collection, largo=largo, ancho=ancho, alto=alto,
                      seed=seed, _shared=shared)
    roca.parent = root
    if con_vegetacion:
        veg = build_vegetacion(parent_collection, largo=largo, ancho=ancho,
                               alto=alto, seed=seed,
                               candidates=shared.get("candidates"))
        veg.parent = root
    return root
