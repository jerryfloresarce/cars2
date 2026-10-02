"""montanas_fondo.py — Muralla de montañas de fondo de Porto Corsa (Cars 2).

Telón panorámico de montañas mediterráneas verdes y rocosas: picos
escarpados con paredes de caliza gris-ocre casi verticales en lo alto,
crestas dentadas y faldas bajas cubiertas de bosque verde saturado
(estilo Riviera de Cars 2: cálido, limpio, low-poly con presencia).

100%% procedural (sin bpy.ops de modelado, sin texturas de imagen):
loft radial de anillos con ruido fbm + crestas "ridged" para espolones
y contrafuertes. El material se asigna POR CARA mezclando PENDIENTE y
ALTURA: verde bosque en laderas suaves y bajas, roca clara en paredes
verticales y crestas altas, con estratos de caliza en las paredes.

Piezas (kit):
  build(parent_collection, seed=0, **params)  -> alias de build_cordillera
  build_pico(parent_collection, alto=180, radio=140, seed=0)
      -> malla MONT_pico (~5.5k tris, presupuesto <= 9k)
  build_cordillera(parent_collection, largo=900, n_picos=5, seed=0,
                   alto=180)
      -> Empty raíz MONT_cordillera con n_picos solapados de alturas
         variadas formando la muralla de fondo.

Unidades en metros, origen en el centro de la base, z=0 en el suelo,
cara principal (frente del telón) mirando a +Y.
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
    """3 octavas a escala de montaña (metros): masas, lomas y grano."""
    return (_n3(x * 0.008 + so, y * 0.008 + so * 0.7, z * 0.008) * 11.0 +
            _n3(x * 0.030 + so * 2.1, y * 0.030 + 11.3, z * 0.030) * 4.2 +
            _n3(x * 0.090 + so * 3.3, y * 0.090 + 23.7, z * 0.090 + 5.1) * 1.6)


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


# Perfil radial (t=0 base -> t=1 cima): falda ancha de bosque, hombro,
# pared casi vertical en el tercio alto y cresta estrecha. Los anillos
# solo suben hasta ~0.92*alto: la punta la pone el vértice ápice.
_PERFIL = [(0.00, 1.00), (0.16, 0.80), (0.34, 0.60), (0.50, 0.47),
           (0.66, 0.40), (0.82, 0.30), (0.93, 0.22), (1.00, 0.07)]

_NZ, _NARC = 48, 56  # anillos x segmentos  (~5.5k tris por pico)


# ------------------------------------------------------------ materiales ----
def _mat(name, color, rough=0.95):
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


# ------------------------------------------------------------- geometría ----
def _pico_geometry(alto, radio, seed):
    """Vértices y caras de un pico: loft radial con espolones y crestas."""
    so = seed * 23.71 + 7.3
    rngp = random.Random(int(seed) * 977 + 13)
    amp_sp = rngp.uniform(0.28, 0.42)        # fuerza de espolones
    amp_rid = rngp.uniform(0.24, 0.38)       # fuerza de crestas
    crown = rngp.uniform(0.11, 0.18)         # corona de subpicos
    warp = rngp.uniform(0.88, 1.18)          # desplaza el hombro del perfil
    lean = rngp.uniform(0.05, 0.18) * radio  # inclinación del macizo
    lth = rngp.uniform(0.0, 2.0 * math.pi)
    lx, ly = math.cos(lth) * lean, math.sin(lth) * lean

    verts, faces = [], []
    rings = []
    for i in range(_NZ):
        t = i / (_NZ - 1.0)
        z0 = alto * (t * 0.95 - 0.03)        # anillo 0 hundido bajo el suelo
        r0 = radio * _spline(_PERFIL, max(t, 0.0) ** warp)
        wall = _sstep((t - 0.52) / 0.20)     # zona de pared caliza
        ox, oy = lx * t * t, ly * t * t      # el pico se inclina levemente
        ring = []
        for k in range(_NARC):
            th = 2.0 * math.pi * k / _NARC
            cx, sx = math.cos(th), math.sin(th)
            # espolones/contrafuertes: lóbulos angulares, más anchos abajo
            sp = _n3(cx * 1.7 + so, sx * 1.7 + so * 0.3, z0 * 0.004)
            # crestas "ridged" que bajan por los flancos (afiladas)
            rid = 1.0 - abs(_n3(cx * 3.1 + so * 1.9, sx * 3.1, 3.3))
            rid *= rid
            r = r0 * (1.0 + amp_sp * sp * (0.30 + 0.70 * (1.0 - t)) +
                      amp_rid * rid * t)
            px, py = cx * r, sx * r
            r = r + _fbm(px, py, z0, so)
            # repisas/estratos de caliza en la pared alta
            ph = 2.5 * _n3(px * 0.015 + so, py * 0.015, 4.4)
            led = max(0.0, math.cos(2.0 * math.pi * z0 / 16.0 + ph)) ** 3 * \
                2.6 * wall
            r = max(r + led, radio * 0.02)
            px, py = ox + cx * r, oy + sx * r
            z = z0 - led * 0.35
            # corona de subpicos: la cresta levanta el borde alto
            if t > 0.55:
                z += alto * crown * rid * ((t - 0.55) / 0.45) ** 2
            # lomas de dosel de bosque en la falda (pendiente suave)
            fade = _sstep((0.46 - t) / 0.32) * _sstep((t + 0.02) / 0.10)
            if fade > 0.0:
                z += fade * (_n3(px * 0.05, py * 0.05, so + 9.2) * 4.5 +
                             _n3(px * 0.13, py * 0.13, so + 4.4) * 1.8)
            # jitter vertical fino para romper los anillos
            z += _n3(px * 0.02 + so * 1.7, py * 0.02, 2.2) * 3.0 * \
                math.sin(math.pi * t)
            z = max(z, -alto * 0.06)
            ring.append(len(verts))
            verts.append((px, py, z))
        rings.append(ring)

    apex = len(verts)
    ax = lx + _n3(so, 1.1, 2.2) * radio * 0.05
    ay = ly + _n3(so, 5.7, 8.8) * radio * 0.05
    verts.append((ax, ay, alto))
    base = len(verts)
    verts.append((0.0, 0.0, -alto * 0.07))

    for a, b in zip(rings, rings[1:]):
        for k in range(_NARC):
            k2 = (k + 1) % _NARC
            faces.append((a[k], a[k2], b[k2], b[k]))
    for k in range(_NARC):
        k2 = (k + 1) % _NARC
        faces.append((apex, rings[-1][k2], rings[-1][k]))
        faces.append((base, rings[0][k], rings[0][k2]))
    return verts, faces


def _asignar_materiales(me, alto, seed):
    """Mezcla por cara: PENDIENTE + ALTURA -> bosque o roca con estratos.

    Roca donde la cara es casi vertical (farallones) o por encima de una
    línea de árboles ondulada (ruido angular, coherente espacialmente);
    verde bosque en el resto. Sin moteado: la frontera sigue la ladera.
    """
    so = seed * 23.71 + 7.3
    band_h = 16.0
    patron_roca = (2, 3, 2, 4)
    me.update()
    for p in me.polygons:
        c = p.center
        nz = p.normal.z
        # línea de árboles ondulada alrededor del pico (por PENDIENTE del
        # perfil: coincide con el arranque de la pared) + ruido angular
        th = math.atan2(c.y, c.x)
        tl = alto * (0.52 + 0.11 * _n3(math.cos(th) * 1.4 + so,
                                       math.sin(th) * 1.4, 1.1))
        es_roca = (
            (nz < 0.30 and c.z > alto * 0.28) or   # farallón casi vertical
            (c.z > tl and nz < 0.75) or            # pared sobre los árboles
            c.z > alto * 0.85)                     # cresta siempre pelada
        if c.z < 1.0:
            p.material_index = 0             # falda que muere en el suelo
        elif es_roca:
            ph = 2.5 * _n3(c.x * 0.015 + so, c.y * 0.015, 4.4)
            b = math.floor(c.z / band_h + ph / (2.0 * math.pi))
            p.material_index = patron_roca[b % 4]
        else:                                # BOSQUE: laderas suaves
            pn = _n3(c.x * 0.018 + so * 1.3, c.y * 0.018, c.z * 0.018 + 6.6)
            p.material_index = 1 if pn > 0.28 else 0


# ----------------------------------------------------------------- piezas ----
def build_pico(parent_collection, alto=180.0, radio=110.0, seed=0, **kw):
    """Pico rocoso individual MONT_pico (<= 9k tris)."""
    verts, faces = _pico_geometry(alto, radio, seed)
    me = bpy.data.meshes.new("MONT_pico")
    me.from_pydata(verts, [], faces)
    me.validate()
    _recalc_and_smooth(me)

    for m in (
        _mat("MAT_MONT_bosque", (0.058, 0.170, 0.040), 0.95),
        _mat("MAT_MONT_bosque_claro", (0.110, 0.265, 0.058), 0.95),
        _mat("MAT_MONT_roca", (0.470, 0.365, 0.235), 0.95),
        _mat("MAT_MONT_roca_clara", (0.600, 0.480, 0.320), 0.95),
        _mat("MAT_MONT_roca_oscura", (0.330, 0.245, 0.150), 0.95),
    ):
        me.materials.append(m)
    _asignar_materiales(me, alto, seed)

    obj = bpy.data.objects.new("MONT_pico", me)
    parent_collection.objects.link(obj)
    return obj


def build_cordillera(parent_collection, largo=900.0, n_picos=5, seed=0,
                     alto=195.0, **kw):
    """Fila de picos solapados de alturas variadas (telón de fondo)."""
    root = bpy.data.objects.new("MONT_cordillera", None)
    root.empty_display_size = 10.0
    parent_collection.objects.link(root)

    rng = random.Random(seed * 31 + 7)
    spacing = largo / max(n_picos, 1)
    for i in range(n_picos):
        # perfil de muralla: más altos hacia el centro, con variación
        factor = (0.60 + 0.52 * math.sin(math.pi * (i + 0.5) / n_picos) +
                  rng.uniform(-0.16, 0.16))
        alto_i = alto * factor
        radio_i = spacing * (0.48 + 0.30 * factor) * rng.uniform(0.92, 1.08)
        x = -largo * 0.5 + (i + 0.5) * spacing + \
            rng.uniform(-0.15, 0.15) * spacing
        # zigzag en profundidad: pares delante, impares detrás (telón +Y)
        if i % 2 == 0:
            y = rng.uniform(0.00, 0.15) * radio_i
        else:
            y = -rng.uniform(0.25, 0.55) * radio_i
        pico = build_pico(parent_collection, alto=alto_i, radio=radio_i,
                          seed=seed * 13 + i * 101 + 5)
        pico.location = (x, y, 0.0)
        pico.rotation_euler = (0.0, 0.0, rng.uniform(0.0, 2.0 * math.pi))
        pico.parent = root
    return root


def build(parent_collection, seed=0, **params):
    """Cordillera de fondo completa. Devuelve el Empty MONT_cordillera."""
    return build_cordillera(parent_collection, seed=seed, **params)
