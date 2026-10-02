# -*- coding: utf-8 -*-
"""
casino_v2.py — Casino di Porto Corsa (Cars 2) — asset HERO procedural, Blender 5.1.

Version 2 (sustituye a casino.py): gran palacio barroco de la Riviera segun el
concept art "montana por dentro" y el fotograma del casino de la pelicula:

  * muros CREMA CALIDO (no blanco puro), molduras marfil, zocalo de piedra,
    dorados en cornisas, marcos y capiteles;
  * tejados y cupulas en TERRACOTA NARANJA (la patina verde-cobre solo queda
    en los cupulines de las linternas);
  * DOS TORRES ALTAS (~1.9x el bloque principal, ~48 m con la aguja) a ambos
    lados del cuerpo central, en la fachada delantera: fuste cuadrado con
    puerta en arco, ventana y reloj, cuerpo de campanas con huecos en arco en
    las 4 caras, templete octogonal con 8 arcos, cupula bulbosa con nervios,
    linterna y aguja dorada;
  * las CUATRO caras trabajadas: trasera (la que se ve desde el mar) con
    cuerpo saliente, 3 grandes arcos, fronton curvo con RELOJ, pilastras y dos
    pisos de ventanas en arco; testeros con 5 vanos, pilastras y fronton curvo
    con oculo; nada de muros ciegos.

Mundo "car-ificado": sin humanos, la escalinata es una rampa con alfombra roja.

Huella ~93 x 54 m (igual que v1), origen en el centro de la base, z=0 en el
suelo, fachada principal mirando a +Y. Solo colores planos (Principled BSDF).
Polycount objetivo <= 30k tris.

API (contrato, compatible con casino.py):
    build(parent_collection, seed=0, **params) -> Empty raiz "CASINO_root"
        params: con_farolas=True, con_marquesina=True,
                con_torres=True, con_relojes=True, linternas_patina=True

Piezas de kit (cada una linka sus objetos a parent_collection y devuelve
su raiz):
    build_cuerpo_central(parent_collection, location=(0,0,0), ...)
    build_ala(parent_collection, side=1, ...)          # side=+1 dcha / -1 izq
    build_torre(parent_collection, location=(22,3,0), ...)   # NUEVO en v2
    build_cupula(parent_collection, radius=7.0, ...)   # tambor+cupula+remate
    build_columnata(parent_collection, n=6, spacing=6.0, ...)
    build_escalinata(parent_collection, ...)           # rampa + explanada
    build_balaustrada(parent_collection, length=8.0, ...)
    build_marquesina(parent_collection, ...)
    build_farola(parent_collection, ...)

Nombres de material: MAT_CASINO_<clave>. "tejado" lleva la palabra clave que
usa aplicar_texturas.py para la familia teja; "vidrio"/"vidrio_hueco" quedan
excluidos del estuco.
"""

import math
import random

import bpy
import bmesh

PREFIX = "CASINO"

# ---------------------------------------------------------------- materiales

_COLORS = {
    # clave:        (color lineal,            metal, rugosidad)
    "fachada":      ((0.78, 0.50, 0.215), 0.0, 0.70),   # crema calido / ocre claro
    "molduras":     ((0.86, 0.72, 0.50), 0.0, 0.65),    # marfil: pilastras, frisos
    "piedra":       ((0.47, 0.405, 0.31), 0.0, 0.85),   # zocalo y explanada
    "dorado":       ((0.91, 0.575, 0.10), 0.55, 0.35),
    "tejado":       ((0.78, 0.235, 0.05), 0.0, 0.75),   # terracota naranja
    "cupula":       ((0.175, 0.50, 0.415), 0.0, 0.5),   # patina (solo linternas)
    "vidrio":       ((0.045, 0.10, 0.15), 0.4, 0.12),
    "vidrio_hueco": ((0.035, 0.04, 0.055), 0.0, 0.9),   # huecos de campanario
    "reloj":        ((0.95, 0.93, 0.84), 0.0, 0.5),
    "rojo":         ((0.63, 0.05, 0.075), 0.0, 0.9),
    "farola":       ((0.055, 0.065, 0.06), 0.6, 0.4),
    "luz":          ((0.98, 0.9, 0.7), 0.0, 0.3),
}


def _mat(key):
    name = "MAT_%s_%s" % (PREFIX, key)
    color, metallic, rough = _COLORS[key]
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    # se reutiliza el datablock, pero se refresca la paleta v2 (si quedaba un
    # MAT_CASINO_fachada blanco de la v1 en el .blend, pasa a crema)
    bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if bsdf is not None:
        if not bsdf.inputs["Base Color"].is_linked:
            bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = rough
        if key == "luz":
            try:
                bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 3.0
            except KeyError:
                pass
    m.diffuse_color = (*color, 1.0)
    return m


# ------------------------------------------------------------ mesh builder

class _MB:
    """Acumulador de geometria; cada instancia acaba en un objeto/material."""

    def __init__(self, smooth=False):
        self.verts = []
        self.faces = []
        self.smooth = smooth

    def add_verts_faces(self, verts, faces):
        b = len(self.verts)
        self.verts.extend(verts)
        self.faces.extend(tuple(b + i for i in f) for f in faces)

    def add_box(self, x0, x1, y0, y1, z0, z1):
        self.add_frustum(x0, x1, y0, y1, z0, x0, x1, y0, y1, z1)

    def add_frustum(self, x0, x1, y0, y1, z0, X0, X1, Y0, Y1, z1):
        """Tronco de piramide rectangular (base en z0, tapa en z1)."""
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (X0, Y0, z1), (X1, Y0, z1), (X1, Y1, z1), (X0, Y1, z1)]
        f = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add_verts_faces(v, f)

    def add_prism_y(self, pts, y0, y1):
        """Poligono (x,z) CCW extruido de y0 a y1."""
        n = len(pts)
        v = [(x, y0, z) for (x, z) in pts] + [(x, y1, z) for (x, z) in pts]
        f = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
        self.add_verts_faces(v, f)

    def add_prism_x(self, pts, x0, x1):
        """Poligono (y,z) extruido de x0 a x1."""
        n = len(pts)
        v = [(x0, y, z) for (y, z) in pts] + [(x1, y, z) for (y, z) in pts]
        f = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
        self.add_verts_faces(v, f)

    def add_lathe(self, profile, seg, cx=0.0, cy=0.0,
                  cap_bottom=True, cap_top=True, phase=0.0):
        """Revolucion del perfil [(radio, z_absoluta), ...] alrededor de Z."""
        rows = []
        for (r, z) in profile:
            if r < 1e-5:
                idx = len(self.verts)
                self.verts.append((cx, cy, z))
                rows.append((True, idx))
            else:
                idx = len(self.verts)
                for i in range(seg):
                    a = phase + 2.0 * math.pi * i / seg
                    self.verts.append((cx + r * math.cos(a),
                                       cy + r * math.sin(a), z))
                rows.append((False, idx))
        for (pa, ia), (pb, ib) in zip(rows, rows[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                if not pa and not pb:
                    self.faces.append((ia + i, ia + j, ib + j, ib + i))
                elif not pa and pb:
                    self.faces.append((ia + i, ia + j, ib))
                elif pa and not pb:
                    self.faces.append((ia, ib + j, ib + i))
        if cap_bottom and not rows[0][0]:
            i0 = rows[0][1]
            self.faces.append(tuple(reversed(range(i0, i0 + seg))))
        if cap_top and not rows[-1][0]:
            i0 = rows[-1][1]
            self.faces.append(tuple(range(i0, i0 + seg)))

    def add_sphere(self, cx, cy, cz, r, seg=10, rings=6):
        prof = [(r * math.sin(math.pi * k / rings),
                 cz - r * math.cos(math.pi * k / rings))
                for k in range(rings + 1)]
        self.add_lathe(prof, seg, cx, cy, cap_bottom=False, cap_top=False)

    def add_torus_y(self, cx, cy, cz, radius, r_minor, seg_u=16, seg_v=8):
        """Toro con eje a lo largo de Y (anillo en el plano XZ)."""
        b = len(self.verts)
        for i in range(seg_u):
            a = 2.0 * math.pi * i / seg_u
            px, pz = math.cos(a), math.sin(a)
            for j in range(seg_v):
                t = 2.0 * math.pi * j / seg_v
                rr = radius + r_minor * math.cos(t)
                self.verts.append((cx + rr * px,
                                   cy + r_minor * math.sin(t),
                                   cz + rr * pz))
        for i in range(seg_u):
            for j in range(seg_v):
                i2, j2 = (i + 1) % seg_u, (j + 1) % seg_v
                self.faces.append((b + i * seg_v + j, b + i2 * seg_v + j,
                                   b + i2 * seg_v + j2, b + i * seg_v + j2))

    def make(self, name, mat_key, coll, parent=None, mirror_x=False):
        if not self.faces:
            return None
        verts, faces = self.verts, self.faces
        if mirror_x:
            verts = [(-x, y, z) for (x, y, z) in verts]
            faces = [tuple(reversed(f)) for f in faces]
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], list(faces))
        me.validate()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        if self.smooth:
            me.polygons.foreach_set("use_smooth",
                                    [True] * len(me.polygons))
        me.materials.append(_mat(mat_key))
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        if parent is not None:
            ob.parent = parent
        return ob


_KEYS = ("fachada", "molduras", "piedra", "dorado", "tejado", "vidrio",
         "vidrio_hueco", "reloj", "farola")


def _mbs():
    return {k: _MB() for k in _KEYS}


def _make_all(mbs, base_name, coll, root, mirror=False):
    for key in _KEYS:
        mbs[key].make("%s_%s" % (base_name, key), key, coll, root, mirror)


def _piece_root(coll, name, location=(0.0, 0.0, 0.0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 2.0
    e.location = location
    coll.objects.link(e)
    if parent is not None:
        e.parent = parent
    return e


# ---------------------------------------------- marco local de una fachada

class _Wall:
    """Marco local de un muro: u a lo largo del muro, d hacia fuera, z arriba.

    (ox, oy) es un punto del plano del muro, (nx, ny) la normal exterior y
    (tx, ty) la direccion de u. Las normales de las caras se recalculan en
    _MB.make(), asi que el sentido de giro no importa.
    """

    def __init__(self, ox, oy, nx, ny, tx=None, ty=None):
        self.ox, self.oy, self.nx, self.ny = ox, oy, nx, ny
        if tx is None:
            tx, ty = -ny, nx
        self.tx, self.ty = tx, ty

    def P(self, u, d, z):
        return (self.ox + u * self.tx + d * self.nx,
                self.oy + u * self.ty + d * self.ny, z)

    def prism(self, mb, pts, d0, d1):
        n = len(pts)
        v = ([self.P(u, d0, z) for (u, z) in pts] +
             [self.P(u, d1, z) for (u, z) in pts])
        f = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
        mb.add_verts_faces(v, f)

    def box(self, mb, u0, u1, z0, z1, d0, d1):
        self.prism(mb, [(u0, z0), (u1, z0), (u1, z1), (u0, z1)], d0, d1)

    def arc_band(self, mb, cu, cz, r0, r1, a0, a1, n, d0, d1):
        """Banda de arco (angulos desde la vertical, + hacia +u) en n tramos
        convexos."""
        for i in range(n):
            aa = a0 + (a1 - a0) * i / n
            ab = a0 + (a1 - a0) * (i + 1) / n
            sa, ca, sb, cb = math.sin(aa), math.cos(aa), math.sin(ab), math.cos(ab)
            self.prism(mb, [(cu + r0 * sa, cz + r0 * ca),
                            (cu + r1 * sa, cz + r1 * ca),
                            (cu + r1 * sb, cz + r1 * cb),
                            (cu + r0 * sb, cz + r0 * cb)], d0, d1)


WALL_FRONT = lambda y: _Wall(0.0, y, 0.0, 1.0, 1.0, 0.0)     # noqa: E731
WALL_REAR = lambda y: _Wall(0.0, y, 0.0, -1.0, 1.0, 0.0)     # noqa: E731
WALL_EAST = lambda x: _Wall(x, 0.0, 1.0, 0.0, 0.0, 1.0)      # noqa: E731
WALL_WEST = lambda x: _Wall(x, 0.0, -1.0, 0.0, 0.0, 1.0)     # noqa: E731


# ------------------------------------------------------- detalles reusables

def _arch_pts(cx, z0, w, h, seg=8):
    """Rectangulo + arco de medio punto, CCW en el plano (u, z)."""
    r = w / 2.0
    spring = z0 + h - r
    pts = [(cx - r, z0), (cx + r, z0), (cx + r, spring)]
    for i in range(1, seg):
        a = math.pi * i / seg
        pts.append((cx + r * math.cos(a), spring + r * math.sin(a)))
    pts.append((cx - r, spring))
    return pts


def _circle_pts(cu, cz, r, seg):
    return [(cu + r * math.cos(2.0 * math.pi * i / seg),
             cz + r * math.sin(2.0 * math.pi * i / seg)) for i in range(seg)]


def _segment_pts(cu, z_chord, half_w, rise, n=12):
    """Segmento circular (fronton curvo) sobre una cuerda horizontal."""
    R = (half_w * half_w + rise * rise) / (2.0 * rise)
    cz = z_chord + rise - R
    amax = math.asin(min(1.0, half_w / R))
    pts = []
    for i in range(n + 1):
        a = amax - 2.0 * amax * i / n
        pts.append((cu + R * math.sin(a), cz + R * math.cos(a)))
    return pts, R, cz, amax


def _arch_window(mb_gold, mb_glass, cx, wall_y, z0, w, h,
                 frame=0.38, proud_frame=0.22, proud_glass=0.32):
    """(API v1) Ventanal en arco sobre un muro que mira a +Y."""
    mb_gold.add_prism_y(
        _arch_pts(cx, z0 - 0.12, w + 2.0 * frame, h + frame + 0.12),
        wall_y - 0.05, wall_y + proud_frame)
    mb_glass.add_prism_y(_arch_pts(cx, z0, w, h),
                         wall_y - 0.05, wall_y + proud_glass)


def _w_arch(wall, mbs, u, z0, w, h, frame=0.32, seg=6, frame_key="dorado",
            glass_key="vidrio", sill=True, d0=0.0):
    """Ventanal en arco: marco + vidrio oscuro en relieve + alfeizar marfil."""
    wall.prism(mbs[frame_key],
               _arch_pts(u, z0 - 0.10, w + 2.0 * frame, h + frame + 0.10, seg),
               d0 - 0.05, d0 + 0.20)
    wall.prism(mbs[glass_key], _arch_pts(u, z0, w, h, seg),
               d0 - 0.05, d0 + 0.28)
    if sill:
        wall.box(mbs["molduras"], u - w / 2.0 - frame - 0.22,
                 u + w / 2.0 + frame + 0.22, z0 - 0.42, z0 - 0.10,
                 d0 - 0.05, d0 + 0.42)


def _w_rect(wall, mbs, u, z0, w, h, frame=0.24, frame_key="molduras"):
    """Ventana rectangular pequena (entresuelo) con marco."""
    wall.box(mbs[frame_key], u - w / 2.0 - frame, u + w / 2.0 + frame,
             z0 - frame, z0 + h + frame, -0.05, 0.18)
    wall.box(mbs["vidrio"], u - w / 2.0, u + w / 2.0, z0, z0 + h,
             -0.05, 0.26)


def _w_oculus(wall, mbs, u, z, r, seg=10, d0=0.0):
    wall.prism(mbs["dorado"], _circle_pts(u, z, r * 1.3, seg),
               d0 - 0.05, d0 + 0.20)
    wall.prism(mbs["vidrio"], _circle_pts(u, z, r, seg),
               d0 - 0.05, d0 + 0.28)


def _w_pilaster(wall, mbs, u, z0, z1, w=0.9, proud=0.34):
    """Pilastra marfil con plinto y capitel dorado."""
    m = mbs["molduras"]
    wall.box(m, u - w / 2.0, u + w / 2.0, z0, z1, -0.05, proud)
    wall.box(m, u - w / 2.0 - 0.16, u + w / 2.0 + 0.16, z0, z0 + 0.75,
             -0.05, proud + 0.13)
    wall.box(mbs["dorado"], u - w / 2.0 - 0.18, u + w / 2.0 + 0.18,
             z1 - 0.6, z1, -0.05, proud + 0.16)


def _w_bays(wall, mbs, u0, u1, n, z_pil0, z_pil1, storeys,
            pil_ends=(True, True), pil_w=0.9):
    """n vanos entre u0 y u1: pilastras en los limites + ventanas centradas.

    storeys: lista de ('arch', z0, w, h[, kwargs]) | ('rect', z0, w, h) |
             ('oculus', z, r).
    """
    bw = (u1 - u0) / n
    for i in range(n + 1):
        if (i == 0 and not pil_ends[0]) or (i == n and not pil_ends[1]):
            continue
        _w_pilaster(wall, mbs, u0 + i * bw, z_pil0, z_pil1, pil_w)
    for i in range(n):
        uc = u0 + (i + 0.5) * bw
        for st in storeys:
            if st[0] == 'arch':
                kw = st[4] if len(st) > 4 else {}
                _w_arch(wall, mbs, uc, st[1], st[2], st[3], **kw)
            elif st[0] == 'rect':
                _w_rect(wall, mbs, uc, st[1], st[2], st[3])
            elif st[0] == 'oculus':
                _w_oculus(wall, mbs, uc, st[1], st[2])


def _w_dormer(wall, mbs, u, z0, w=1.5, h=1.4, depth=3.0):
    """Buhardilla sobre un faldon: cuerpo marfil que se hunde `depth` en el
    tejado, ventanita en arco y tejadillo a dos aguas de terracota."""
    wall.box(mbs["molduras"], u - w / 2.0, u + w / 2.0, z0, z0 + h,
             -depth, 0.0)
    wall.prism(mbs["vidrio"],
               _arch_pts(u, z0 + 0.22, w * 0.56, h * 0.74, 4), -0.05, 0.08)
    wall.prism(mbs["tejado"], [(u - w / 2.0 - 0.22, z0 + h - 0.05),
                               (u + w / 2.0 + 0.22, z0 + h - 0.05),
                               (u, z0 + h + 0.60)], -depth, 0.20)


def _w_clock(wall, mbs, u, z, r, d0=0.0, seg=16):
    """Reloj: aro dorado, esfera marfil, 4 marcas y agujas a las 10:10."""
    wall.prism(mbs["dorado"], _circle_pts(u, z, r * 1.17, seg),
               d0 - 0.05, d0 + 0.30)
    wall.prism(mbs["reloj"], _circle_pts(u, z, r, seg), d0 - 0.05, d0 + 0.40)
    dark = mbs["farola"]
    for k in range(4):
        a = k * math.pi / 2.0
        cu, cz = u + 0.80 * r * math.cos(a), z + 0.80 * r * math.sin(a)
        if k % 2 == 0:
            hu, hz = 0.13 * r, 0.045 * r
        else:
            hu, hz = 0.045 * r, 0.13 * r
        wall.box(dark, cu - hu, cu + hu, cz - hz, cz + hz,
                 d0 + 0.38, d0 + 0.46)
    for ang, length, width in ((150.0, 0.50, 0.060), (35.0, 0.76, 0.042)):
        a = math.radians(ang)
        du, dz = math.cos(a), math.sin(a)
        pu, pz = -dz, du
        L, W, B = length * r, width * r, 0.12 * r
        pts = [(u - B * du - W * pu, z - B * dz - W * pz),
               (u + L * du - W * pu, z + L * dz - W * pz),
               (u + L * du + W * pu, z + L * dz + W * pz),
               (u - B * du + W * pu, z - B * dz + W * pz)]
        wall.prism(dark, pts, d0 + 0.38, d0 + 0.48)
    wall.prism(mbs["dorado"], _circle_pts(u, z, 0.09 * r, 6),
               d0 + 0.38, d0 + 0.54)


def _column(mb_fach, mb_gold, cx, cy, z0, h, r=0.62, seg=12):
    """Columna clasica: plinto + fuste + capitel dorado."""
    mb_fach.add_box(cx - 1.5 * r, cx + 1.5 * r,
                    cy - 1.5 * r, cy + 1.5 * r, z0, z0 + 0.5)
    mb_fach.add_lathe([(r * 1.15, z0 + 0.5), (r, z0 + 0.95),
                       (r * 0.86, z0 + h - 0.9), (r * 0.95, z0 + h - 0.5)],
                      seg, cx, cy)
    mb_gold.add_box(cx - 1.35 * r, cx + 1.35 * r,
                    cy - 1.35 * r, cy + 1.35 * r, z0 + h - 0.5, z0 + h)


def _baluster(mb, x, y, z):
    """Balaustre de bajo poligonaje (pirindolo cuadrado girado 45 grados)."""
    mb.add_lathe([(0.10, z + 0.12), (0.16, z + 0.40), (0.09, z + 0.79)],
                 4, x, y, cap_bottom=False, cap_top=False)


def _balustrade_x(mb, x0, x1, y, z, spacing=0.9):
    """Balaustrada horizontal a lo largo de X, base en z."""
    mb.add_box(x0, x1, y - 0.16, y + 0.16, z, z + 0.13)
    mb.add_box(x0 - 0.08, x1 + 0.08, y - 0.20, y + 0.20, z + 0.78, z + 0.98)
    mb.add_box(x0 - 0.20, x0 + 0.20, y - 0.22, y + 0.22, z, z + 1.02)
    mb.add_box(x1 - 0.20, x1 + 0.20, y - 0.22, y + 0.22, z, z + 1.02)
    n = max(2, int(round((x1 - x0 - 0.7) / spacing)))
    for i in range(1, n):
        _baluster(mb, x0 + 0.35 + (x1 - x0 - 0.7) * i / n, y, z)


def _balustrade_y(mb, y0, y1, x, z, spacing=0.9):
    """Balaustrada horizontal a lo largo de Y, base en z."""
    mb.add_box(x - 0.16, x + 0.16, y0, y1, z, z + 0.13)
    mb.add_box(x - 0.20, x + 0.20, y0 - 0.08, y1 + 0.08, z + 0.78, z + 0.98)
    mb.add_box(x - 0.22, x + 0.22, y0 - 0.20, y0 + 0.20, z, z + 1.02)
    mb.add_box(x - 0.22, x + 0.22, y1 - 0.20, y1 + 0.20, z, z + 1.02)
    n = max(2, int(round((y1 - y0 - 0.7) / spacing)))
    for i in range(1, n):
        _baluster(mb, x, y0 + 0.35 + (y1 - y0 - 0.7) * i / n, z)


def _dome_ribs(mb, profile, n, cx=0.0, cy=0.0, thick=0.16, proud=0.16,
               phase=0.0):
    """Nervios radiales siguiendo el perfil [(r, z), ...] de una cupula."""
    for k in range(n):
        a = phase + 2.0 * math.pi * k / n
        wall = _Wall(cx, cy, -math.sin(a), math.cos(a),
                     math.cos(a), math.sin(a))
        for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
            wall.prism(mb, [(r0 - 0.10, z0), (r0 + proud, z0),
                            (r1 + proud, z1), (r1 - 0.10, z1)],
                       -thick / 2.0, thick / 2.0)


def _lantern(mold, gold, dark, cap, gold_smooth, z0, r, h, cx=0.0, cy=0.0,
             spire=2.6):
    """Linterna: anillo dorado, tambor octogonal marfil con 4 huecos en arco,
    cupulin (patina o terracota), bola y aguja doradas. Devuelve z de la punta."""
    seg = 8
    gold.add_lathe([(r * 1.30, z0), (r * 1.30, z0 + 0.12 * h)], seg, cx, cy,
                   phase=math.pi / seg)
    mold.add_lathe([(r, z0 + 0.12 * h), (r, z0 + h)], seg, cx, cy,
                   phase=math.pi / seg)
    ap = r * math.cos(math.pi / seg)
    for k in range(4):
        a = k * math.pi / 2.0
        wall = _Wall(cx + ap * math.cos(a), cy + ap * math.sin(a),
                     math.cos(a), math.sin(a))
        wall.prism(dark, _arch_pts(0.0, z0 + 0.26 * h, r * 0.50, h * 0.60, 4),
                   -0.05, 0.05)
    gold.add_lathe([(r * 1.25, z0 + h), (r * 1.25, z0 + 1.10 * h)], seg,
                   cx, cy, phase=math.pi / seg)
    cap.add_lathe([(r * 1.16, z0 + 1.10 * h), (r * 1.04, z0 + 1.36 * h),
                   (r * 0.56, z0 + 1.66 * h), (0.0, z0 + 1.82 * h)],
                  12, cx, cy)
    zb = z0 + 1.82 * h + r * 0.30
    gold_smooth.add_sphere(cx, cy, zb, r * 0.40, 8, 5)
    tip = zb + r * spire
    gold.add_lathe([(r * 0.13, zb + r * 0.30), (0.0, tip)], 6, cx, cy)
    return tip


# ------------------------------------------------------------------- piezas

def build_cupula(parent_collection, radius=7.0, location=(0.0, 0.0, 0.0),
                 name_suffix="", parent=None, seg=None, drum_h=None,
                 ribs=0, lantern=False, patina=True, drum_windows=True):
    """Tambor crema con pilastras y ventanitas + banda dorada + cupula
    TERRACOTA (v2) con nervios dorados opcionales y linterna opcional.

    La base del tambor queda en z=0 del root de la pieza. drum_h por defecto
    radius*0.5. Altura: drum_h + radius*1.13 (+ linterna).
    """
    if seg is None:
        seg = 20 if radius >= 5.0 else 14
    root = _piece_root(parent_collection, "%s_cupula%s" % (PREFIX, name_suffix),
                       location, parent)
    dh = radius * 0.5 if drum_h is None else drum_h
    base = "%s_cupula%s" % (PREFIX, name_suffix)
    fach, mold, glass = _MB(), _MB(), _MB()
    fach.add_lathe([(radius * 0.93, 0.0), (radius * 0.93, dh)], seg)
    # pilastras del tambor + ventanitas entre ellas (solo la parte alta)
    npil = seg // 2
    zw0 = max(0.3, dh - radius * 0.42)
    for i in range(npil):
        a = 2.0 * math.pi * (i + 0.5) / npil
        px, py = math.cos(a), math.sin(a)
        w = radius * 0.085
        mold.add_box(radius * 0.97 * px - w, radius * 0.97 * px + w,
                     radius * 0.97 * py - w, radius * 0.97 * py + w,
                     0.15, dh - 0.10)
        if drum_windows:
            a2 = 2.0 * math.pi * i / npil
            ap = radius * 0.93          # sobre la arista: no se hunde
            wall = _Wall(ap * math.cos(a2), ap * math.sin(a2),
                         math.cos(a2), math.sin(a2))
            ww = radius * 0.17
            wall.prism(glass, _arch_pts(0.0, zw0, ww, dh - 0.35 - zw0, 4),
                       -0.05, 0.10)
    fach.make(base + "_tambor", "fachada", parent_collection, root)
    mold.make(base + "_molduras", "molduras", parent_collection, root)
    glass.make(base + "_vidrio", "vidrio", parent_collection, root)

    gold, gold_s = _MB(), _MB(True)
    gold.add_lathe([(radius * 1.04, dh - 0.05), (radius * 1.04, dh + 0.30)],
                   seg)
    prof = [(radius * 1.00, dh + 0.25),
            (radius * 1.06, dh + radius * 0.24),
            (radius * 0.92, dh + radius * 0.62),
            (radius * 0.56, dh + radius * 0.92),
            (radius * 0.20, dh + radius * 1.08)]
    if ribs:
        _dome_ribs(gold, prof, ribs, thick=radius * 0.045,
                   proud=radius * 0.03)
    dome = _MB(True)
    dome.add_lathe(prof + [(0.0, dh + radius * 1.13)], seg)
    dome.make(base + "_casquete", "tejado", parent_collection, root)

    if lantern:
        lmold, ldark, lcap = _MB(), _MB(), _MB(True)
        _lantern(lmold, gold, ldark, lcap, gold_s,
                 dh + radius * 1.04, radius * 0.16, radius * 0.33, spire=1.7)
        lmold.make(base + "_linterna", "molduras", parent_collection, root)
        ldark.make(base + "_linterna_hueco", "vidrio_hueco",
                   parent_collection, root)
        lcap.make(base + "_linterna_cupulin",
                  "cupula" if patina else "tejado", parent_collection, root)
    else:
        gold_s.add_sphere(0, 0, dh + radius * 1.16, radius * 0.11, 8, 5)
        gold.add_lathe([(radius * 0.055, dh + radius * 1.16),
                        (0.0, dh + radius * 1.46)], 8)
    gold.make(base + "_dorado", "dorado", parent_collection, root)
    gold_s.make(base + "_dorado_liso", "dorado", parent_collection, root)
    return root


def build_torre(parent_collection, location=(21.2, 3.0, 0.0), name_suffix="",
                parent=None, con_reloj=True, patina=True, caras_fuste=("N",),
                caras_oculo=()):
    """Torre-campanario barroca de ~48 m (coordenadas locales al eje).

    Fuste cuadrado 9.2 m (0-20.4) con cornisa alineada con el cuerpo central,
    cuerpo de campanas cuadrado 8.1 m (20.4-28.2) con hueco en arco en las 4
    caras y pinaculos dorados, templete octogonal (28.2-34.9) con 8 arcos,
    cupula bulbosa terracota con nervios marfil (hasta 40.4 = ~1.9x el bloque
    principal), linterna con cupulin de patina y aguja dorada.
    caras_fuste: caras del fuste con puerta/ventana/reloj ("N"=+Y, "S", "E", "W").
    caras_oculo: caras del fuste que solo asoman sobre los tejados de las alas
                 (z 16.3-18.2) y llevan un oculo dorado para no quedar ciegas.
    """
    base = "%s_torre%s" % (PREFIX, name_suffix)
    root = _piece_root(parent_collection, base, location, parent)
    mbs = _mbs()
    fach, mold, stone, gold = (mbs["fachada"], mbs["molduras"],
                               mbs["piedra"], mbs["dorado"])
    dark = mbs["vidrio_hueco"]

    # --- fuste
    hw = 4.6
    fach.add_box(-hw, hw, -hw, hw, 0.0, 20.4)
    stone.add_box(-hw - 0.3, hw + 0.3, -hw - 0.3, hw + 0.3, 0.0, 2.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (hw - 0.45), sy * (hw - 0.45)
            mold.add_box(cx - 0.70, cx + 0.70, cy - 0.70, cy + 0.70, 2.5, 18.2)
    e = hw + 0.18
    mold.add_box(-e, e, -e, e, 10.0, 10.45)                       # imposta
    e = hw + 0.27
    mold.add_box(-e, e, -e, e, 18.2, 19.0)                        # friso
    e = hw + 0.48
    gold.add_box(-e, e, -e, e, 19.0, 19.6)                        # cornisa
    e = hw + 0.10
    mold.add_box(-e, e, -e, e, 19.6, 20.4)                        # zocalo alto

    walls = {"N": _Wall(0.0, hw, 0.0, 1.0, 1.0, 0.0),
             "S": _Wall(0.0, -hw, 0.0, -1.0, 1.0, 0.0),
             "E": _Wall(hw, 0.0, 1.0, 0.0, 0.0, 1.0),
             "W": _Wall(-hw, 0.0, -1.0, 0.0, 0.0, 1.0)}
    for c in caras_fuste:
        wall = walls[c]
        _w_arch(wall, mbs, 0.0, 2.5, 3.3, 6.7, frame=0.36, seg=8,
                sill=False)                                         # puerta
        _w_arch(wall, mbs, 0.0, 11.2, 2.4, 3.4)                     # ventana
        if con_reloj:
            _w_clock(wall, mbs, 0.0, 16.6, 1.30)
        else:
            _w_oculus(wall, mbs, 0.0, 16.6, 0.95)
    for c in caras_oculo:
        if c not in caras_fuste:
            _w_oculus(walls[c], mbs, 0.0, 17.3, 0.60)

    # --- cuerpo de campanas (cuadrado)
    ha = 4.05
    fach.add_box(-ha, ha, -ha, ha, 20.4, 27.9)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (ha - 0.35), sy * (ha - 0.35)
            mold.add_box(cx - 0.60, cx + 0.60, cy - 0.60, cy + 0.60,
                         20.4, 26.7)
            # pinaculo: pedestal marfil + remate dorado
            px, py = sx * (ha + 0.05), sy * (ha + 0.05)
            mold.add_box(px - 0.46, px + 0.46, py - 0.46, py + 0.46,
                         28.2, 29.5)
            gold.add_lathe([(0.0, 29.5), (0.46, 29.95), (0.32, 30.45),
                            (0.0, 31.3)], 6, px, py)
    e = ha + 0.22
    mold.add_box(-e, e, -e, e, 26.7, 27.5)
    e = ha + 0.47
    gold.add_box(-e, e, -e, e, 27.5, 28.2)
    belfry_walls = (_Wall(0.0, ha, 0.0, 1.0, 1.0, 0.0),
                    _Wall(0.0, -ha, 0.0, -1.0, 1.0, 0.0),
                    _Wall(ha, 0.0, 1.0, 0.0, 0.0, 1.0),
                    _Wall(-ha, 0.0, -1.0, 0.0, 0.0, 1.0))
    for wall in belfry_walls:
        _w_arch(wall, mbs, 0.0, 21.3, 3.0, 4.9, frame=0.36, seg=8,
                frame_key="molduras", glass_key="vidrio_hueco", sill=False)
        wall.box(gold, -2.15, 2.15, 20.95, 21.3, -0.05, 0.50)     # balconcillo
        wall.box(gold, -0.32, 0.32, 26.35, 27.05, -0.05, 0.36)    # clave

    # --- templete octogonal
    rb = 3.55
    ph = math.pi / 8.0
    ap = rb * math.cos(ph)
    mold.add_lathe([(rb + 0.34, 28.2), (rb + 0.34, 28.8)], 8, phase=ph)
    fach.add_lathe([(rb, 28.8), (rb, 34.4)], 8, phase=ph)
    for k in range(8):
        a = ph + k * math.pi / 4.0
        cx, cy = (rb + 0.02) * math.cos(a), (rb + 0.02) * math.sin(a)
        mold.add_lathe([(0.40, 28.8), (0.33, 29.2), (0.29, 33.4),
                        (0.40, 33.8)], 6, cx, cy)
        b = k * math.pi / 4.0
        wall = _Wall(ap * math.cos(b), ap * math.sin(b),
                     math.cos(b), math.sin(b))
        _w_arch(wall, mbs, 0.0, 29.4, 1.42, 3.9, frame=0.21, seg=6,
                frame_key="molduras", glass_key="vidrio_hueco", sill=False)
    mold.add_lathe([(rb + 0.22, 33.8), (rb + 0.22, 34.4)], 8, phase=ph)
    gold.add_lathe([(rb + 0.52, 34.4), (rb + 0.52, 34.9)], 8, phase=ph)

    # --- cupula bulbosa + nervios
    prof = [(3.05, 34.9), (3.42, 35.85), (3.30, 37.1), (2.68, 38.5),
            (1.70, 39.7), (1.02, 40.35)]
    dome = _MB(True)
    dome.add_lathe(prof, 16)
    _dome_ribs(mold, prof, 8, thick=0.26, proud=0.15, phase=ph)

    # --- linterna
    lcap, gold_s = _MB(True), _MB(True)
    _lantern(mold, gold, dark, lcap, gold_s, 40.25, 1.02, 2.6)

    _make_all(mbs, base, parent_collection, root)
    dome.make(base + "_cupula", "tejado", parent_collection, root)
    lcap.make(base + "_cupulin", "cupula" if patina else "tejado",
              parent_collection, root)
    gold_s.make(base + "_dorado_liso", "dorado", parent_collection, root)
    return root


def build_columnata(parent_collection, n=6, spacing=6.0, col_h=12.0,
                    location=(0.0, 0.0, 0.0), name_suffix="", parent=None):
    """Fila de n columnas a lo largo de X + entablamento con filete dorado."""
    root = _piece_root(parent_collection,
                       "%s_columnata%s" % (PREFIX, name_suffix),
                       location, parent)
    fach, gold = _MB(), _MB()
    half = (n - 1) * spacing / 2.0
    for i in range(n):
        _column(fach, gold, -half + i * spacing, 0.0, 0.0, col_h)
    fach.add_box(-half - 1.6, half + 1.6, -1.9, 1.9, col_h, col_h + 2.2)
    gold.add_box(-half - 1.8, half + 1.8, -2.05, 2.05,
                 col_h + 1.6, col_h + 2.1)
    fach.make("%s_columnata%s_piedra" % (PREFIX, name_suffix),
              "molduras", parent_collection, root)
    gold.make("%s_columnata%s_dorado" % (PREFIX, name_suffix),
              "dorado", parent_collection, root)
    return root


def build_balaustrada(parent_collection, length=8.0,
                      location=(0.0, 0.0, 0.0), name_suffix="", parent=None):
    """Segmento de balaustrada marfil a lo largo de X, centrado en el origen."""
    root_mb = _MB()
    _balustrade_x(root_mb, -length / 2.0, length / 2.0, 0.0, 0.0, 0.6)
    ob = root_mb.make("%s_balaustrada%s" % (PREFIX, name_suffix),
                      "molduras", parent_collection, parent)
    if ob is not None:
        ob.location = location
    return ob


def build_farola(parent_collection, location=(0.0, 0.0, 0.0),
                 name_suffix="", parent=None):
    """Farola de fundicion con globo calido y remate dorado (h ~4.3 m)."""
    root = _piece_root(parent_collection, "%s_farola%s" % (PREFIX, name_suffix),
                       location, parent)
    post = _MB()
    post.add_lathe([(0.42, 0.0), (0.30, 0.14), (0.13, 0.55),
                    (0.085, 3.0), (0.16, 3.2), (0.12, 3.38)], 8)
    post.make("%s_farola%s_poste" % (PREFIX, name_suffix),
              "farola", parent_collection, root)
    globe = _MB(True)
    globe.add_sphere(0, 0, 3.72, 0.34, 8, 5)
    globe.make("%s_farola%s_globo" % (PREFIX, name_suffix),
               "luz", parent_collection, root)
    tip = _MB()
    tip.add_sphere(0, 0, 4.18, 0.10, 6, 3)
    tip.make("%s_farola%s_remate" % (PREFIX, name_suffix),
             "dorado", parent_collection, root)
    return root


def build_marquesina(parent_collection, location=(0.0, 0.0, 0.0),
                     name_suffix="", parent=None):
    """Marquesina de entrada: vidrio sobre estructura dorada (galibo ~5 m)."""
    root = _piece_root(parent_collection,
                       "%s_marquesina%s" % (PREFIX, name_suffix),
                       location, parent)
    glass = _MB()
    glass.add_prism_x([(14.2, 5.85), (18.7, 5.35), (18.7, 5.55),
                       (14.2, 6.05)], -6.6, 6.6)
    glass.make("%s_marquesina%s_vidrio" % (PREFIX, name_suffix),
               "vidrio", parent_collection, root)
    gold = _MB()
    gold.add_box(-6.9, 6.9, 18.55, 18.95, 5.05, 5.75)            # fleco front
    gold.add_prism_x([(14.2, 5.55), (18.8, 5.05), (18.8, 5.75),
                      (14.2, 6.25)], -6.9, -6.55)                # fleco lados
    gold.add_prism_x([(14.2, 5.55), (18.8, 5.05), (18.8, 5.75),
                      (14.2, 6.25)], 6.55, 6.9)
    for sx in (-6.1, 6.1):
        gold.add_lathe([(0.30, 2.0), (0.19, 2.35), (0.16, 5.0),
                        (0.24, 5.2), (0.20, 5.45)], 8, sx, 18.1)
        gold.add_sphere(sx, 18.1, 5.85, 0.26, 8, 4)              # remates
    gold.make("%s_marquesina%s_dorado" % (PREFIX, name_suffix),
              "dorado", parent_collection, root)
    return root


def build_escalinata(parent_collection, location=(0.0, 0.0, 0.0),
                     name_suffix="", parent=None):
    """Explanada + plataforma de entrada + rampa suave con alfombra roja.

    Mundo de coches: sin peldanos, la "escalinata" es una rampa del 13%.
    """
    root = _piece_root(parent_collection,
                       "%s_escalinata%s" % (PREFIX, name_suffix),
                       location, parent)
    st = _MB()
    st.add_box(-46.5, 46.5, -26.0, 18.0, 0.0, 0.30)              # zocalo
    st.add_box(-47.0, 47.0, 18.0, 28.0, 0.0, 0.15)               # explanada
    st.add_box(-22.0, 22.0, 10.0, 18.5, 0.0, 2.0)                # plataforma
    st.add_prism_x([(18.5, 0.0), (27.0, 0.0), (18.5, 2.0)],
                   -14.0, 14.0)                                   # rampa
    for sx in (1.0, -1.0):
        st.add_prism_x([(18.3, 2.0), (18.3, 2.9), (27.2, 0.9), (27.2, 0.0)],
                       sx * 13.9, sx * 14.9)                      # pretiles
    st.make("%s_escalinata%s_piedra" % (PREFIX, name_suffix),
            "piedra", parent_collection, root)

    carpet = _MB()
    carpet.add_prism_x([(18.45, 2.04), (27.0, 0.16), (27.0, 0.28),
                        (18.45, 2.16)], -5.0, 5.0)
    carpet.add_box(-5.0, 5.0, 12.5, 18.5, 2.0, 2.12)
    carpet.make("%s_escalinata%s_alfombra" % (PREFIX, name_suffix),
                "rojo", parent_collection, root)

    gold = _MB()
    for sx in (-14.4, 14.4):
        gold.add_sphere(sx, 26.8, 1.25, 0.38, 8, 5)
        gold.add_sphere(sx, 18.7, 3.25, 0.38, 8, 5)
    gold.make("%s_escalinata%s_dorado" % (PREFIX, name_suffix),
              "dorado", parent_collection, root)

    bal = _MB()
    _balustrade_x(bal, -21.6, -15.0, 18.1, 2.0, 0.7)
    _balustrade_x(bal, 15.0, 21.6, 18.1, 2.0, 0.7)
    _balustrade_y(bal, 10.6, 18.1, -21.6, 2.0, 0.7)
    _balustrade_y(bal, 10.6, 18.1, 21.6, 2.0, 0.7)
    bal.make("%s_escalinata%s_balaustrada" % (PREFIX, name_suffix),
             "molduras", parent_collection, root)
    return root


def build_cuerpo_central(parent_collection, location=(0.0, 0.0, 0.0),
                         name_suffix="", parent=None, con_reloj=True):
    """Cuerpo central: bloque crema, portico de 6 columnas, fronton con rueda
    dorada, atico, tejado terracota a cuatro aguas, balaustrada perimetral y
    TRASERA monumental (cuerpo saliente + fronton curvo con reloj). La cupula
    grande va aparte (build_cupula), apoyada en z=24.4."""
    root = _piece_root(parent_collection,
                       "%s_cuerpo_central%s" % (PREFIX, name_suffix),
                       location, parent)
    mbs = _mbs()
    fach, mold, stone, gold, glass, roof = (
        mbs["fachada"], mbs["molduras"], mbs["piedra"], mbs["dorado"],
        mbs["vidrio"], mbs["tejado"])

    fach.add_box(-18.0, 18.0, -24.0, 10.0, 0.0, 20.0)            # bloque
    stone.add_box(-18.3, 18.3, -24.3, 10.3, 0.0, 2.5)            # base
    mold.add_box(-18.25, 18.25, -24.25, 10.25, 18.2, 19.0)       # friso
    gold.add_box(-18.45, 18.45, -24.45, 10.45, 19.0, 19.6)       # cornisa
    fach.add_box(-16.0, 16.0, -22.0, 8.0, 20.0, 21.6)            # atico
    gold.add_box(-16.15, 16.15, -22.15, 8.15, 21.3, 21.6)        # filete atico
    roof.add_frustum(-16.5, 16.5, -22.5, 8.5, 21.6,
                     -8.0, 8.0, -15.0, 1.0, 24.4)                # tejado
    mold.add_box(-8.2, 8.2, -15.2, 1.2, 24.35, 24.6)             # anillo cupula

    # portico
    for cx in (-15.0, -9.0, -3.0, 3.0, 9.0, 15.0):
        _column(mold, gold, cx, 12.5, 2.0, 12.0)
    mold.add_box(-16.6, 16.6, 10.3, 14.6, 14.0, 16.6)            # entablamento
    gold.add_box(-16.8, 16.8, 10.2, 14.7, 15.8, 16.3)

    # fronton + timpano + emblema rueda + faldones de teja
    fach.add_prism_y([(-16.0, 16.6), (16.0, 16.6), (0.0, 23.9)], 10.6, 13.9)
    gold.add_prism_y([(-15.9, 16.55), (15.9, 16.55), (0.0, 24.1)],
                     13.9, 14.15)
    mold.add_prism_y([(-13.4, 16.9), (13.4, 16.9), (0.0, 22.9)], 14.0, 14.3)
    for sx in (-1.0, 1.0):
        roof.add_prism_y([(sx * 17.1, 16.30), (0.0, 24.20),
                          (0.0, 24.62), (sx * 17.1, 16.72)], 10.0, 14.45)
    gold.add_torus_y(0.0, 14.4, 19.3, 1.7, 0.30, 16, 6)
    for k in range(4):                                            # radios
        a = math.pi * k / 4.0
        dx, dz = math.cos(a), math.sin(a)
        length, w = 1.55, 0.12
        pts = [(-length * dx - w * dz, 19.3 - length * dz + w * dx),
               (length * dx - w * dz, 19.3 + length * dz + w * dx),
               (length * dx + w * dz, 19.3 + length * dz - w * dx),
               (-length * dx + w * dz, 19.3 - length * dz - w * dx)]
        gold.add_prism_y(pts, 14.28, 14.52)

    # ventanales del portico
    front = WALL_FRONT(10.0)
    for cx in (-12.0, -6.0, 0.0, 6.0, 12.0):
        _w_arch(front, mbs, cx, 2.0, 3.8, 9.5, frame=0.38, seg=8, sill=False)

    # balaustrada perimetral de cubierta + jarrones dorados de esquina
    _balustrade_x(mold, -15.5, 15.5, 9.4, 20.0, 1.0)
    _balustrade_x(mold, -17.4, -10.9, -23.4, 20.0, 1.0)
    _balustrade_x(mold, 10.9, 17.4, -23.4, 20.0, 1.0)
    # buhardillas del tejado: 2 al frente (a los lados del fronton) y 3 por costado
    for u in (-9.0, 9.0):
        _w_dormer(WALL_FRONT(7.0), mbs, u, 22.0, 1.6, 1.5, 3.6)
    for wall in (WALL_EAST(15.0), WALL_WEST(-15.0)):
        for cy in (-14.5, -7.0, 0.5):
            _w_dormer(wall, mbs, cy, 21.95, 1.6, 1.5, 4.1)

    for sx in (-1.0, 1.0):
        _balustrade_y(mold, -23.0, -2.2, sx * 17.4, 20.0, 1.0)
        for sy in (9.2, -23.2):
            gold.add_lathe([(0.0, 20.0), (0.50, 20.35), (0.34, 20.9),
                            (0.0, 21.7)], 6, sx * 17.2, sy)

    # ---- TRASERA (mira al mar): cuerpo saliente + 3 arcos + fronton con reloj
    fach.add_box(-10.0, 10.0, -25.6, -24.0, 0.0, 20.0)
    stone.add_box(-10.3, 10.3, -25.9, -24.0, 0.0, 2.5)
    mold.add_box(-10.25, 10.25, -25.85, -24.0, 18.2, 19.0)
    gold.add_box(-10.45, 10.45, -25.98, -24.0, 19.0, 19.6)
    rear_c = WALL_REAR(-25.6)
    _w_bays(rear_c, mbs, -9.3, 9.3, 3, 2.5, 18.2,
            [('arch', 3.0, 3.4, 8.4), ('arch', 12.9, 2.6, 4.3)], pil_w=1.0)
    rear_c.box(mold, -9.3, 9.3, 11.75, 12.15, -0.05, 0.22)       # imposta
    pts, R, cz, amax = _segment_pts(0.0, 19.6, 10.3, 5.4, 14)
    rear_c.prism(fach, pts, -1.5, 0.10)                          # fronton
    rear_c.arc_band(gold, 0.0, cz, R - 0.75, R - 0.05, -amax, amax, 14,
                    0.10, 0.34)
    rear_c.box(gold, -10.0, 10.0, 19.6, 20.05, 0.10, 0.34)
    rear_c.arc_band(roof, 0.0, cz, R - 0.05, R + 0.36, -amax, amax, 14,
                    -1.6, 0.55)
    # tejado de medio cono tras el fronton (como el de un abside): une el
    # fronton con el tejado a cuatro aguas para que de lado no sea una losa
    # exenta. Nace dentro de la banda de teja y muere bajo el anillo de la
    # cupula; los bordes laterales quedan enterrados en el atico/tejado.
    rc = R + 0.30
    cone_v = [rear_c.P(rc * math.sin(-amax + 2.0 * amax * i / 14),
                       -1.55,
                       cz + rc * math.cos(-amax + 2.0 * amax * i / 14))
              for i in range(15)]
    cone_v.append((0.0, -15.0, 24.5))
    roof.add_verts_faces(cone_v, [(i, i + 1, 15) for i in range(14)])
    if con_reloj:
        _w_clock(rear_c, mbs, 0.0, 22.15, 1.62, d0=0.10)
    else:
        _w_oculus(rear_c, mbs, 0.0, 22.15, 1.3, d0=0.10)
    gold.add_lathe([(0.0, 25.3), (0.5, 25.7), (0.32, 26.3), (0.0, 27.3)],
                   6, 0.0, -24.9)                                 # acrotera

    # flancos de la trasera: 2 vanos x 2 pisos a cada lado
    rear = WALL_REAR(-24.0)
    for sx in (-1.0, 1.0):
        ua, ub = sorted((sx * 10.3, sx * 17.6))
        ends = (False, True) if sx > 0 else (True, False)
        _w_bays(rear, mbs, ua, ub, 2, 2.5, 18.2,
                [('arch', 3.4, 1.8, 6.0, {'frame': 0.30}),
                 ('arch', 11.9, 1.8, 5.0, {'frame': 0.30})],
                pil_ends=ends, pil_w=0.8)
        rear.box(mold, ua, ub, 10.35, 10.75, -0.05, 0.22)

    # laterales altos (sobre los tejados de las alas): oculos
    for wall in (WALL_EAST(18.0), WALL_WEST(-18.0)):
        for cy in (-21.0, -16.2, -11.4, -6.6):
            _w_oculus(wall, mbs, cy, 17.2, 0.62)

    _make_all(mbs, "%s_central%s" % (PREFIX, name_suffix),
              parent_collection, root)
    return root


def build_ala(parent_collection, side=1, location=(0.0, 0.0, 0.0),
              name_suffix=None, parent=None, con_torre=True):
    """Ala lateral + pabellon de esquina (side=+1 derecha, -1 izquierda).

    con_torre=True deja libre el tramo de fachada que ocupa la torre.

    Geometria definida para +X y espejada para el lado izquierdo. Las 3
    caras vistas (delantera, trasera y testero) llevan pilastras, ventanales
    en arco, entresuelo y cornisa; tejados de terracota. La cupula del
    pabellon va aparte (build_cupula en (42, -5, 17)).
    """
    if name_suffix is None:
        name_suffix = "_R" if side >= 0 else "_L"
    root = _piece_root(parent_collection, "%s_ala%s" % (PREFIX, name_suffix),
                       location, parent)
    mirror = side < 0
    mbs = _mbs()
    fach, mold, stone, gold, roof = (mbs["fachada"], mbs["molduras"],
                                     mbs["piedra"], mbs["dorado"],
                                     mbs["tejado"])

    # ---- cuerpo del ala
    fach.add_box(18.0, 38.0, -20.0, 6.0, 0.0, 14.5)
    stone.add_box(18.0, 38.2, -20.25, 6.25, 0.0, 2.5)
    mold.add_box(18.0, 38.0, -20.2, 6.2, 12.3, 13.1)             # friso
    gold.add_box(17.9, 38.3, -20.42, 6.42, 13.1, 13.7)           # cornisa
    roof.add_frustum(18.0, 38.0, -19.0, 5.0, 14.5,
                     18.0, 38.0, -15.2, 1.2, 16.3)               # mansarda

    # delantera: la torre (x 16.6..25.8) tapa los 8 primeros metros del ala
    front = WALL_FRONT(6.0)
    fu0, fn = (26.0, 3) if con_torre else (18.0, 5)
    _w_bays(front, mbs, fu0, 38.0, fn, 2.5, 12.3,
            [('arch', 3.0, 2.2, 6.3, {'frame': 0.30}),
             ('rect', 10.35, 1.6, 1.35)],
            pil_ends=(False, False), pil_w=0.8)
    _balustrade_x(mold, fu0 + 0.5, 37.6, 5.5, 14.5, 1.0)
    fbw = (38.0 - fu0) / fn
    for i in range(fn):                                           # buhardillas
        _w_dormer(WALL_FRONT(4.4), mbs, fu0 + fbw * (i + 0.5), 14.6,
                  1.5, 1.3, 2.35)

    rear = WALL_REAR(-20.0)
    _w_bays(rear, mbs, 18.5, 37.5, 4, 2.5, 12.3,
            [('arch', 3.0, 2.4, 6.4), ('rect', 10.35, 1.7, 1.35)])
    _balustrade_x(mold, 18.5, 37.5, -19.5, 14.5, 1.0)
    for i in range(4):
        _w_dormer(WALL_REAR(-18.4), mbs, 18.5 + 4.75 * (i + 0.5), 14.6,
                  1.5, 1.3, 2.35)

    # ---- pabellon de esquina
    fach.add_box(38.0, 46.0, -18.0, 8.0, 0.0, 17.0)
    stone.add_box(37.9, 46.25, -18.25, 8.25, 0.0, 2.5)
    mold.add_box(37.95, 46.22, -18.22, 8.22, 14.8, 15.6)         # friso
    gold.add_box(37.8, 46.42, -18.42, 8.42, 15.6, 16.2)          # cornisa
    roof.add_frustum(39.0, 45.0, -17.0, 7.0, 17.0,
                     41.3, 42.7, -13.6, 3.6, 19.5)               # 4 aguas

    pf = WALL_FRONT(8.0)
    _w_pilaster(pf, mbs, 39.0, 2.5, 14.8, 1.0)
    _w_pilaster(pf, mbs, 45.0, 2.5, 14.8, 1.0)
    _w_arch(pf, mbs, 42.0, 2.6, 3.8, 8.6, frame=0.36, seg=8)
    _w_oculus(pf, mbs, 42.0, 13.3, 0.70)
    pr = WALL_REAR(-18.0)
    _w_pilaster(pr, mbs, 39.0, 2.5, 14.8, 1.0)
    _w_pilaster(pr, mbs, 45.0, 2.5, 14.8, 1.0)
    _w_arch(pr, mbs, 42.0, 2.6, 3.8, 8.6, frame=0.36, seg=8)
    _w_oculus(pr, mbs, 42.0, 13.3, 0.70)

    # testero (x=46): 5 vanos + fronton curvo con oculo
    end = WALL_EAST(46.0)
    _w_bays(end, mbs, -17.45, 7.45, 5, 2.5, 14.8,
            [('arch', 3.0, 2.6, 6.6), ('rect', 11.5, 1.8, 1.7)])
    pts, R, cz, amax = _segment_pts(-5.0, 16.2, 5.3, 3.3, 10)
    end.prism(fach, pts, -1.0, 0.08)
    end.arc_band(gold, -5.0, cz, R - 0.55, R - 0.04, -amax, amax, 10,
                 0.08, 0.30)
    end.arc_band(roof, -5.0, cz, R - 0.04, R + 0.30, -amax, amax, 10,
                 -1.1, 0.48)
    _w_oculus(end, mbs, -5.0, 17.75, 0.80, d0=0.08)

    _balustrade_x(mold, 38.4, 45.6, 7.5, 17.0, 1.0)
    _balustrade_x(mold, 38.4, 45.6, -17.5, 17.0, 1.0)
    _balustrade_y(mold, -17.5, -10.6, 45.5, 17.0, 1.0)
    _balustrade_y(mold, 0.6, 7.5, 45.5, 17.0, 1.0)
    for sy in (-17.4, 7.4):                                       # jarrones
        gold.add_lathe([(0.0, 17.0), (0.46, 17.35), (0.30, 17.85),
                        (0.0, 18.6)], 6, 45.4, sy)

    _make_all(mbs, "%s_ala%s" % (PREFIX, name_suffix),
              parent_collection, root, mirror)
    return root


# --------------------------------------------------------------- ensamblaje

def build(parent_collection, seed=0, **params):
    """Construye el Casino di Porto Corsa completo y devuelve el Empty raiz."""
    rnd = random.Random(seed)
    con_farolas = params.get("con_farolas", True)
    con_marquesina = params.get("con_marquesina", True)
    con_torres = params.get("con_torres", True)
    con_relojes = params.get("con_relojes", True)
    patina = params.get("linternas_patina", True)

    root = _piece_root(parent_collection, "%s_root" % PREFIX)

    build_escalinata(parent_collection, parent=root)
    build_cuerpo_central(parent_collection, parent=root,
                         con_reloj=con_relojes)
    build_ala(parent_collection, side=1, parent=root, con_torre=con_torres)
    build_ala(parent_collection, side=-1, parent=root, con_torre=con_torres)

    if con_torres:
        build_torre(parent_collection, location=(21.2, 3.0, 0.0),
                    name_suffix="_R", parent=root, con_reloj=con_relojes,
                    patina=patina, caras_oculo=("S", "E"))
        build_torre(parent_collection, location=(-21.2, 3.0, 0.0),
                    name_suffix="_L", parent=root, con_reloj=con_relojes,
                    patina=patina, caras_oculo=("S", "W"))

    build_cupula(parent_collection, radius=6.6, drum_h=3.2,
                 location=(0.0, -7.0, 24.4), name_suffix="_C", parent=root,
                 ribs=10, lantern=True, patina=patina)
    build_cupula(parent_collection, radius=3.4, drum_h=4.3,
                 location=(42.0, -5.0, 17.0), name_suffix="_R", parent=root)
    build_cupula(parent_collection, radius=3.4, drum_h=4.3,
                 location=(-42.0, -5.0, 17.0), name_suffix="_L", parent=root)

    if con_marquesina:
        build_marquesina(parent_collection, parent=root)

    if con_farolas:
        i = 0
        for sx in (-43.0, -31.0, -19.0, 19.0, 31.0, 43.0):
            jitter = (rnd.random() - 0.5) * 0.4
            build_farola(parent_collection,
                         location=(sx, 24.5 + jitter, 0.15),
                         name_suffix="_%d" % i, parent=root)
            i += 1
    return root
