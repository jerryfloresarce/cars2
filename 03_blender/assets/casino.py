# -*- coding: utf-8 -*-
"""
casino.py — Casino di Porto Corsa (Cars 2) — asset HERO procedural para Blender 5.1.

Estilo Belle Epoque / Casino de Montecarlo, "car-ificado" (sin humanos:
la escalinata es una rampa suave para coches, con alfombra roja).
Fachada principal simetrica blanco-crema con dorados, gran cuerpo central
con fronton (emblema: rueda dorada), dos alas laterales con columnatas de
pilastras y ventanales en arco, pabellones de esquina, 3 cupulas verde-cobre
(la central mayor), marquesina de entrada, balaustradas y farolas.

Huella ~92 x 55 m, altura ~35 m con la cupula central. Origen en el centro
de la base, z=0 en el suelo, fachada mirando a +Y. Solo colores planos
(Principled BSDF), sin texturas. Polycount de heroe (<= 25k tris).

API (contrato):
    build(parent_collection, seed=0, **params) -> Empty raiz "CASINO_root"
        params: con_farolas=True, con_marquesina=True

Piezas de kit (cada una linka sus objetos a parent_collection y devuelve
su raiz):
    build_cuerpo_central(parent_collection, location=(0,0,0), ...)
    build_ala(parent_collection, side=1, ...)          # side=+1 dcha / -1 izq
    build_cupula(parent_collection, radius=7.0, ...)   # tambor+cupula+remate
    build_columnata(parent_collection, n=6, spacing=6.0, ...)
    build_escalinata(parent_collection, ...)           # rampa + explanada
    build_balaustrada(parent_collection, length=8.0, ...)
    build_marquesina(parent_collection, ...)
    build_farola(parent_collection, ...)
"""

import math
import random

import bpy
import bmesh

PREFIX = "CASINO"

# ---------------------------------------------------------------- materiales

_COLORS = {
    "fachada":  ((0.95, 0.89, 0.755), 0.0, 0.65),
    "piedra":   ((0.79, 0.70, 0.565), 0.0, 0.85),
    "dorado":   ((0.91, 0.575, 0.10), 0.55, 0.35),
    "cupula":   ((0.175, 0.50, 0.415), 0.0, 0.5),
    "vidrio":   ((0.05, 0.10, 0.16), 0.4, 0.12),
    "rojo":     ((0.63, 0.05, 0.075), 0.0, 0.9),
    "farola":   ((0.055, 0.065, 0.06), 0.6, 0.4),
    "luz":      ((0.98, 0.9, 0.7), 0.0, 0.3),
}


def _mat(key):
    name = "MAT_%s_%s" % (PREFIX, key)
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    color, metallic, rough = _COLORS[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
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

    def __init__(self):
        self.verts = []
        self.faces = []
        self.smooth = False

    def add_verts_faces(self, verts, faces):
        b = len(self.verts)
        self.verts.extend(verts)
        self.faces.extend(tuple(b + i for i in f) for f in faces)

    def add_box(self, x0, x1, y0, y1, z0, z1):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
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
                  cap_bottom=True, cap_top=True):
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
                    a = 2.0 * math.pi * i / seg
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


def _piece_root(coll, name, location=(0.0, 0.0, 0.0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 2.0
    e.location = location
    coll.objects.link(e)
    if parent is not None:
        e.parent = parent
    return e


# ------------------------------------------------------- detalles reusables

def _arch_pts(cx, z0, w, h, seg=8):
    """Rectangulo + arco de medio punto, CCW en el plano XZ."""
    r = w / 2.0
    spring = z0 + h - r
    pts = [(cx - r, z0), (cx + r, z0), (cx + r, spring)]
    for i in range(1, seg):
        a = math.pi * i / seg
        pts.append((cx + r * math.cos(a), spring + r * math.sin(a)))
    pts.append((cx - r, spring))
    return pts


def _arch_window(mb_gold, mb_glass, cx, wall_y, z0, w, h,
                 frame=0.38, proud_frame=0.22, proud_glass=0.32):
    """Ventanal en arco: marco dorado + panel de vidrio oscuro (en relieve)."""
    mb_gold.add_prism_y(
        _arch_pts(cx, z0 - 0.12, w + 2.0 * frame, h + frame + 0.12),
        wall_y - 0.05, wall_y + proud_frame)
    mb_glass.add_prism_y(_arch_pts(cx, z0, w, h),
                         wall_y - 0.05, wall_y + proud_glass)


def _column(mb_fach, mb_gold, cx, cy, z0, h, r=0.62, seg=12):
    """Columna clasica: plinto + fuste + capitel dorado."""
    mb_fach.add_box(cx - 1.5 * r, cx + 1.5 * r,
                    cy - 1.5 * r, cy + 1.5 * r, z0, z0 + 0.5)
    mb_fach.add_lathe([(r * 1.15, z0 + 0.5), (r, z0 + 0.95),
                       (r * 0.86, z0 + h - 0.9), (r * 0.95, z0 + h - 0.5)],
                      seg, cx, cy)
    mb_gold.add_box(cx - 1.35 * r, cx + 1.35 * r,
                    cy - 1.35 * r, cy + 1.35 * r, z0 + h - 0.5, z0 + h)


def _balusters_x(mb, x0, x1, y, z, spacing=0.6):
    n = max(2, int(round((x1 - x0) / spacing)))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        mb.add_lathe([(0.0, z + 0.10), (0.105, z + 0.16),
                      (0.105, z + 0.72), (0.0, z + 0.78)], 6, x, y)


def _balustrade_x(mb, x0, x1, y, z, spacing=0.6):
    """Balaustrada horizontal a lo largo de X, base en z."""
    mb.add_box(x0, x1, y - 0.16, y + 0.16, z, z + 0.13)
    mb.add_box(x0 - 0.08, x1 + 0.08, y - 0.20, y + 0.20, z + 0.78, z + 0.98)
    mb.add_box(x0 - 0.20, x0 + 0.20, y - 0.22, y + 0.22, z, z + 1.02)
    mb.add_box(x1 - 0.20, x1 + 0.20, y - 0.22, y + 0.22, z, z + 1.02)
    _balusters_x(mb, x0 + 0.35, x1 - 0.35, y, z, spacing)


def _balustrade_y(mb, y0, y1, x, z, spacing=0.6):
    """Balaustrada horizontal a lo largo de Y, base en z."""
    mb.add_box(x - 0.16, x + 0.16, y0, y1, z, z + 0.13)
    mb.add_box(x - 0.20, x + 0.20, y0 - 0.08, y1 + 0.08, z + 0.78, z + 0.98)
    mb.add_box(x - 0.22, x + 0.22, y0 - 0.20, y0 + 0.20, z, z + 1.02)
    mb.add_box(x - 0.22, x + 0.22, y1 - 0.20, y1 + 0.20, z, z + 1.02)
    n = max(2, int(round((y1 - y0 - 0.7) / spacing)))
    for i in range(n + 1):
        y = y0 + 0.35 + (y1 - y0 - 0.7) * i / n
        mb.add_lathe([(0.0, z + 0.10), (0.105, z + 0.16),
                      (0.105, z + 0.72), (0.0, z + 0.78)], 6, x, y)


# ------------------------------------------------------------------- piezas

def build_cupula(parent_collection, radius=7.0, location=(0.0, 0.0, 0.0),
                 name_suffix="", parent=None, seg=None):
    """Tambor crema + banda y remate dorados + cupula verde-cobre.

    Altura total ~ radius * 1.6 + drum. La base del tambor queda en z=0
    del root de la pieza.
    """
    if seg is None:
        seg = 20 if radius >= 5.0 else 14
    root = _piece_root(parent_collection, "%s_cupula%s" % (PREFIX, name_suffix),
                       location, parent)
    dh = radius * 0.5
    fach = _MB()
    fach.add_lathe([(radius * 0.93, 0.0), (radius * 0.93, dh)], seg)
    # pilastras del tambor
    npil = seg // 2
    for i in range(npil):
        a = 2.0 * math.pi * (i + 0.5) / npil
        px, py = math.cos(a), math.sin(a)
        w = radius * 0.09
        fach.add_box(radius * 0.97 * px - w, radius * 0.97 * px + w,
                     radius * 0.97 * py - w, radius * 0.97 * py + w,
                     0.15, dh - 0.15)
    fach.make("%s_cupula%s_tambor" % (PREFIX, name_suffix),
              "fachada", parent_collection, root)

    gold = _MB()
    gold.add_lathe([(radius * 1.04, dh - 0.05), (radius * 1.04, dh + 0.30)],
                   seg)
    gold.add_sphere(0, 0, dh + radius * 1.16, radius * 0.11, 8, 5)
    gold.add_lathe([(radius * 0.055, dh + radius * 1.16),
                    (0.0, dh + radius * 1.42)], 8)
    gold.make("%s_cupula%s_dorado" % (PREFIX, name_suffix),
              "dorado", parent_collection, root)

    dome = _MB()
    dome.smooth = True
    dome.add_lathe([(radius * 1.00, dh + 0.25),
                    (radius * 1.06, dh + radius * 0.24),
                    (radius * 0.92, dh + radius * 0.62),
                    (radius * 0.56, dh + radius * 0.92),
                    (radius * 0.20, dh + radius * 1.08),
                    (0.0, dh + radius * 1.13)], seg)
    dome.make("%s_cupula%s_casquete" % (PREFIX, name_suffix),
              "cupula", parent_collection, root)
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
              "fachada", parent_collection, root)
    gold.make("%s_columnata%s_dorado" % (PREFIX, name_suffix),
              "dorado", parent_collection, root)
    return root


def build_balaustrada(parent_collection, length=8.0,
                      location=(0.0, 0.0, 0.0), name_suffix="", parent=None):
    """Segmento de balaustrada crema a lo largo de X, centrado en el origen."""
    root_mb = _MB()
    _balustrade_x(root_mb, -length / 2.0, length / 2.0, 0.0, 0.0)
    ob = root_mb.make("%s_balaustrada%s" % (PREFIX, name_suffix),
                      "fachada", parent_collection, parent)
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
    globe = _MB()
    globe.smooth = True
    globe.add_sphere(0, 0, 3.72, 0.34, 10, 6)
    globe.make("%s_farola%s_globo" % (PREFIX, name_suffix),
               "luz", parent_collection, root)
    tip = _MB()
    tip.add_sphere(0, 0, 4.18, 0.10, 6, 4)
    tip.make("%s_farola%s_remate" % (PREFIX, name_suffix),
             "dorado", parent_collection, root)
    return root


def build_marquesina(parent_collection, location=(0.0, 0.0, 0.0),
                     name_suffix="", parent=None):
    """Marquesina de entrada: vidrio sobre estructura dorada (gala ~5.4 m)."""
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
    _balustrade_x(bal, -21.6, -15.0, 18.1, 2.0)
    _balustrade_x(bal, 15.0, 21.6, 18.1, 2.0)
    _balustrade_y(bal, 10.6, 18.1, -21.6, 2.0)
    _balustrade_y(bal, 10.6, 18.1, 21.6, 2.0)
    bal.make("%s_escalinata%s_balaustrada" % (PREFIX, name_suffix),
             "fachada", parent_collection, root)
    return root


def build_cuerpo_central(parent_collection, location=(0.0, 0.0, 0.0),
                         name_suffix="", parent=None):
    """Cuerpo central: bloque, portico de 6 columnas, fronton con rueda
    dorada, atico y balaustrada de cubierta. La cupula grande va aparte."""
    root = _piece_root(parent_collection,
                       "%s_cuerpo_central%s" % (PREFIX, name_suffix),
                       location, parent)
    fach, stone, gold, glass = _MB(), _MB(), _MB(), _MB()

    fach.add_box(-18.0, 18.0, -24.0, 10.0, 0.0, 20.0)            # bloque
    stone.add_box(-18.3, 18.3, -24.3, 10.3, 0.0, 2.5)            # base
    gold.add_box(-18.4, 18.4, -24.4, 10.4, 19.0, 19.6)           # cornisa
    fach.add_box(-16.0, 16.0, -22.0, 8.0, 20.0, 22.3)            # atico
    gold.add_box(-16.15, 16.15, -22.15, 8.15, 21.95, 22.3)       # filete atico

    # portico
    for cx in (-15.0, -9.0, -3.0, 3.0, 9.0, 15.0):
        _column(fach, gold, cx, 12.5, 2.0, 12.0)
    fach.add_box(-16.6, 16.6, 10.3, 14.6, 14.0, 16.6)            # entablamento
    gold.add_box(-16.8, 16.8, 10.2, 14.7, 15.8, 16.3)

    # fronton + timpano + emblema rueda
    fach.add_prism_y([(-16.0, 16.6), (16.0, 16.6), (0.0, 23.9)], 10.6, 13.9)
    gold.add_prism_y([(-15.9, 16.55), (15.9, 16.55), (0.0, 24.1)],
                     13.9, 14.15)
    fach.add_prism_y([(-13.4, 16.9), (13.4, 16.9), (0.0, 22.9)], 14.0, 14.3)
    gold.add_torus_y(0.0, 14.4, 19.3, 1.7, 0.30, 16, 8)
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
    for cx in (-12.0, -6.0, 0.0, 6.0, 12.0):
        _arch_window(gold, glass, cx, 10.0, 2.0, 3.8, 9.5)

    # balaustrada de cubierta + jarrones dorados de esquina
    _balustrade_x(fach, -15.5, 15.5, 9.4, 20.0)
    for sx in (-17.2, 17.2):
        for sy in (9.2, -23.2):
            gold.add_sphere(sx, sy, 20.45, 0.55, 8, 5)

    # trasera y laterales altos: nada de muros ciegos (se ven desde el mar)
    for cx in (-13.5, -8.1, -2.7, 2.7, 8.1, 13.5):
        for z0, h in ((3.4, 5.4), (11.2, 5.4)):
            gold.add_box(cx - 1.6, cx + 1.6, -24.24, -23.95, z0 - 0.3, z0 + h + 0.3)
            glass.add_box(cx - 1.25, cx + 1.25, -24.34, -23.95, z0, z0 + h)
    for sx in (-1, 1):
        for cy in (-19.0, -12.5, -6.0, 0.5):
            xa, xb = sorted((sx * 17.95, sx * 18.24))
            gold.add_box(xa, xb, cy - 1.5, cy + 1.5, 14.9, 18.6)
            xa, xb = sorted((sx * 17.95, sx * 18.34))
            glass.add_box(xa, xb, cy - 1.15, cy + 1.15, 15.2, 18.3)

    fach.make("%s_central%s_fachada" % (PREFIX, name_suffix),
              "fachada", parent_collection, root)
    stone.make("%s_central%s_piedra" % (PREFIX, name_suffix),
               "piedra", parent_collection, root)
    gold.make("%s_central%s_dorado" % (PREFIX, name_suffix),
              "dorado", parent_collection, root)
    glass.make("%s_central%s_vidrio" % (PREFIX, name_suffix),
               "vidrio", parent_collection, root)
    return root


def build_ala(parent_collection, side=1, location=(0.0, 0.0, 0.0),
              name_suffix=None, parent=None):
    """Ala lateral + pabellon de esquina (side=+1 derecha, -1 izquierda).

    Geometria definida para +X y espejada para el lado izquierdo.
    """
    if name_suffix is None:
        name_suffix = "_R" if side >= 0 else "_L"
    root = _piece_root(parent_collection, "%s_ala%s" % (PREFIX, name_suffix),
                       location, parent)
    mirror = side < 0
    fach, stone, gold, glass = _MB(), _MB(), _MB(), _MB()

    # cuerpo del ala
    fach.add_box(18.0, 38.0, -20.0, 6.0, 0.0, 14.0)
    stone.add_box(18.0, 38.2, -20.2, 6.25, 0.0, 2.5)
    gold.add_box(17.9, 38.3, -20.4, 6.45, 13.1, 13.7)
    fach.add_box(18.0, 38.0, -20.0, 6.0, 14.0, 14.5)             # cubierta

    # pilastras + ventanales en arco
    for px in (19.0, 24.0, 29.0, 34.0):
        fach.add_box(px - 0.6, px + 0.6, 6.0, 6.45, 2.5, 12.6)
    for cx in (21.5, 26.5, 31.5, 36.5):
        _arch_window(gold, glass, cx, 6.0, 3.0, 2.7, 7.5)
    _balustrade_x(fach, 18.6, 37.4, 5.4, 14.5)

    # pabellon de esquina
    fach.add_box(38.0, 46.0, -18.0, 8.0, 0.0, 16.5)
    stone.add_box(37.9, 46.2, -18.2, 8.3, 0.0, 2.5)
    gold.add_box(37.8, 46.3, -18.4, 8.5, 15.6, 16.2)
    fach.add_box(38.0, 46.0, -18.0, 8.0, 16.5, 17.0)             # cubierta
    fach.add_box(38.6, 39.6, 8.0, 8.4, 2.5, 15.1)                # pilastras
    fach.add_box(44.4, 45.4, 8.0, 8.4, 2.5, 15.1)
    _arch_window(gold, glass, 42.0, 8.0, 2.5, 4.0, 9.0)
    _balustrade_x(fach, 38.4, 45.6, 7.5, 17.0)
    _balustrade_y(fach, -17.5, 7.5, 45.5, 17.0)
    gold.add_sphere(45.4, -17.4, 17.45, 0.5, 8, 5)               # jarron

    # trasera del ala y del pabellon + costado exterior del pabellon
    for cx in (21.5, 26.5, 31.5, 36.5):
        gold.add_box(cx - 1.7, cx + 1.7, -20.24, -19.95, 2.7, 10.9)
        glass.add_box(cx - 1.35, cx + 1.35, -20.34, -19.95, 3.0, 10.6)
    gold.add_box(42.0 - 2.3, 42.0 + 2.3, -18.24, -17.95, 2.3, 11.8)
    glass.add_box(42.0 - 1.95, 42.0 + 1.95, -18.34, -17.95, 2.6, 11.5)
    for cy in (-13.5, -7.0, -0.5, 5.0):
        gold.add_box(45.95, 46.24, cy - 1.6, cy + 1.6, 2.7, 11.3)
        glass.add_box(45.95, 46.34, cy - 1.25, cy + 1.25, 3.0, 11.0)

    fach.make("%s_ala%s_fachada" % (PREFIX, name_suffix),
              "fachada", parent_collection, root, mirror)
    stone.make("%s_ala%s_piedra" % (PREFIX, name_suffix),
               "piedra", parent_collection, root, mirror)
    gold.make("%s_ala%s_dorado" % (PREFIX, name_suffix),
              "dorado", parent_collection, root, mirror)
    glass.make("%s_ala%s_vidrio" % (PREFIX, name_suffix),
               "vidrio", parent_collection, root, mirror)
    return root


# --------------------------------------------------------------- ensamblaje

def build(parent_collection, seed=0, **params):
    """Construye el Casino di Porto Corsa completo y devuelve el Empty raiz."""
    rnd = random.Random(seed)
    con_farolas = params.get("con_farolas", True)
    con_marquesina = params.get("con_marquesina", True)

    root = _piece_root(parent_collection, "%s_root" % PREFIX)

    build_escalinata(parent_collection, parent=root)
    build_cuerpo_central(parent_collection, parent=root)
    build_ala(parent_collection, side=1, parent=root)
    build_ala(parent_collection, side=-1, parent=root)

    build_cupula(parent_collection, radius=7.6,
                 location=(0.0, -7.0, 22.3), name_suffix="_C", parent=root)
    build_cupula(parent_collection, radius=3.4,
                 location=(42.0, -5.0, 17.0), name_suffix="_R", parent=root)
    build_cupula(parent_collection, radius=3.4,
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
