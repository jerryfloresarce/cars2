"""puerto_kit.py — Kit procedural del puerto de Porto Corsa (Cars 2) para Blender 5.1.

Estilo: Riviera italiana saturada y limpia (Portofino/Montecarlo carificado).
Unidades en metros, origen en el centro de la base, z=0 al nivel del agua/suelo,
proa/fachada mirando a +Y. Sin bpy.ops: mallas via bpy.data.meshes + from_pydata.

Piezas del kit (cada una devuelve un Empty raiz con la malla como hijo):
  build_yate(parent, eslora=25)        yate blanco moderno: casco, superestructura
                                       acristalada azul oscuro, radar y radomo.
  build_velero(parent, eslora=12)      velero con mastil, botavara y velas recogidas.
  build_pantalan(parent, largo=40)     pantalan flotante de madera con norays.
  build_faro(parent)                   faro blanquirrojo ~18 m para el morro del dique.
  build_dique(parent, radio=140, arco_grados=200)
                                       dique curvo de piedra con paseo superior y
                                       morros circulares (marina-tapacubos).
  build(parent, seed=0)                vineta: agua + dique + faro + pantalan + 3 barcos.

Polycount: todas las piezas quedan muy por debajo de 5k tris.
"""

import math
import random

import bpy
import bmesh
from mathutils import Vector

PFX = "PUERTO"


# ---------------------------------------------------------------- materiales

def _mat(name, color, rough=0.7, metal=0.0, emit=None, emit_strength=2.0):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if emit is not None:
            try:
                bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
                bsdf.inputs["Emission Strength"].default_value = emit_strength
            except KeyError:
                pass
    m.diffuse_color = (*color, 1.0)
    return m


def _mats_kit():
    """Diccionario de materiales compartidos del kit."""
    return {
        "casco":    _mat("MAT_PUERTO_casco_blanco", (0.90, 0.90, 0.88), rough=0.30),
        "cristal":  _mat("MAT_PUERTO_cristal_azul", (0.010, 0.035, 0.095), rough=0.08),
        "teca":     _mat("MAT_PUERTO_cubierta_teca", (0.52, 0.35, 0.18), rough=0.65),
        "metal":    _mat("MAT_PUERTO_metal", (0.55, 0.58, 0.62), rough=0.35, metal=0.8),
        "vela":     _mat("MAT_PUERTO_vela", (0.93, 0.91, 0.85), rough=0.85),
        "mastil":   _mat("MAT_PUERTO_mastil", (0.80, 0.80, 0.82), rough=0.4, metal=0.5),
        "madera_a": _mat("MAT_PUERTO_madera_a", (0.50, 0.32, 0.16), rough=0.8),
        "madera_b": _mat("MAT_PUERTO_madera_b", (0.44, 0.27, 0.13), rough=0.8),
        "flotador": _mat("MAT_PUERTO_flotador", (0.70, 0.72, 0.74), rough=0.6),
        "noray":    _mat("MAT_PUERTO_noray", (0.12, 0.13, 0.15), rough=0.45, metal=0.6),
        "faro_b":   _mat("MAT_PUERTO_faro_blanco", (0.93, 0.91, 0.86), rough=0.55),
        "faro_r":   _mat("MAT_PUERTO_faro_rojo", (0.75, 0.06, 0.05), rough=0.5),
        "piedra":   _mat("MAT_PUERTO_piedra", (0.55, 0.47, 0.36), rough=0.9),
        "paseo":    _mat("MAT_PUERTO_paseo", (0.82, 0.72, 0.54), rough=0.85),
        "agua":     _mat("MAT_PUERTO_agua", (0.018, 0.36, 0.42), rough=0.12),
        "farol":    _mat("MAT_PUERTO_farol", (0.95, 0.85, 0.55), rough=0.3,
                         emit=(1.0, 0.85, 0.45), emit_strength=3.0),
        "azul":     _mat("MAT_PUERTO_azul_marino", (0.02, 0.09, 0.22), rough=0.4),
    }


# ---------------------------------------------------------- builder de mallas

class _MB:
    """Acumulador de geometria: verts + caras + indice de material por cara."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []

    def add(self, verts, faces, mi=0):
        base = len(self.verts)
        self.verts.extend(tuple(v) for v in verts)
        for f in faces:
            self.faces.append(tuple(base + i for i in f))
            self.mats.append(mi)

    # caja con base en z (c = centro de la base)
    def box(self, c, s, mi=0):
        x, y, z = c
        hx, hy = s[0] * 0.5, s[1] * 0.5
        zt = z + s[2]
        v = [(x - hx, y - hy, z), (x + hx, y - hy, z),
             (x + hx, y + hy, z), (x - hx, y + hy, z),
             (x - hx, y - hy, zt), (x + hx, y - hy, zt),
             (x + hx, y + hy, zt), (x - hx, y + hy, zt)]
        f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(v, f, mi)

    # caja con la cara frontal (+Y) inclinada: el borde superior delantero
    # retrocede 'slant' (parabrisas, rampas...)
    def wedge(self, c, s, slant, mi=0):
        x, y, z = c
        hx, hy = s[0] * 0.5, s[1] * 0.5
        zt = z + s[2]
        v = [(x - hx, y - hy, z), (x + hx, y - hy, z),
             (x + hx, y + hy, z), (x - hx, y + hy, z),
             (x - hx, y - hy, zt), (x + hx, y - hy, zt),
             (x + hx, y + hy - slant, zt), (x - hx, y + hy - slant, zt)]
        f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(v, f, mi)

    def cyl_between(self, p1, p2, r1, r2, seg=12, mi=0, caps=True):
        p1 = Vector(p1)
        p2 = Vector(p2)
        w = p2 - p1
        w.normalize()
        u = w.cross(Vector((0.0, 0.0, 1.0)))
        if u.length < 1e-5:
            u = Vector((1.0, 0.0, 0.0))
        else:
            u.normalize()
        vv = w.cross(u)
        verts = []
        for p, r in ((p1, r1), (p2, r2)):
            for i in range(seg):
                a = 2.0 * math.pi * i / seg
                d = u * math.cos(a) + vv * math.sin(a)
                verts.append(p + d * r)
        faces = []
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((i, j, seg + j, seg + i))
        if caps:
            faces.append(tuple(range(seg)))
            faces.append(tuple(seg + i for i in range(seg)))
        self.add(verts, faces, mi)

    def cyl(self, c, r1, r2, h, seg=12, mi=0, caps=True):
        self.cyl_between(c, (c[0], c[1], c[2] + h), r1, r2, seg=seg, mi=mi, caps=caps)

    def disc(self, c, r, seg=24, mi=0):
        verts = [(c[0] + r * math.cos(2 * math.pi * i / seg),
                  c[1] + r * math.sin(2 * math.pi * i / seg), c[2])
                 for i in range(seg)]
        self.add(verts, [tuple(range(seg))], mi)

    def sphere(self, c, r, seg=12, rings=8, mi=0):
        verts = []
        for j in range(1, rings):
            phi = math.pi * j / rings
            for i in range(seg):
                th = 2.0 * math.pi * i / seg
                verts.append((c[0] + r * math.sin(phi) * math.cos(th),
                              c[1] + r * math.sin(phi) * math.sin(th),
                              c[2] + r * math.cos(phi)))
        top = len(verts)
        verts.append((c[0], c[1], c[2] + r))
        bot = len(verts)
        verts.append((c[0], c[1], c[2] - r))
        faces = []
        rows = rings - 1
        for j in range(rows - 1):
            for i in range(seg):
                k = (i + 1) % seg
                faces.append((j * seg + i, j * seg + k,
                              (j + 1) * seg + k, (j + 1) * seg + i))
        for i in range(seg):
            k = (i + 1) % seg
            faces.append((top, k, i))
            faces.append((bot, (rows - 1) * seg + i, (rows - 1) * seg + k))
        self.add(verts, faces, mi)

    # anillo de seccion cuadrada (pasamanos)
    def torus_ring(self, c, R, s, seg=20, mi=0):
        hs = s * 0.5
        prof = [(-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs)]
        verts = []
        for i in range(seg):
            a = 2.0 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            for dr, dz in prof:
                rr = R + dr
                verts.append((c[0] + rr * ca, c[1] + rr * sa, c[2] + dz))
        faces = []
        for i in range(seg):
            j = (i + 1) % seg
            for k in range(4):
                k2 = (k + 1) % 4
                faces.append((i * 4 + k, i * 4 + k2, j * 4 + k2, j * 4 + k))
        self.add(verts, faces, mi)

    # loft de secciones abiertas (mismo numero de puntos por seccion)
    def loft(self, sections, strip_mats=None, mi=0, cap_start=True,
             cap_end=True, cap_mi=None):
        n = len(sections[0])
        verts = [p for sec in sections for p in sec]
        faces = []
        fmats = []
        for s in range(len(sections) - 1):
            for k in range(n - 1):
                faces.append((s * n + k, s * n + k + 1,
                              (s + 1) * n + k + 1, (s + 1) * n + k))
                fmats.append(strip_mats[k] if strip_mats else mi)
        if cap_start:
            faces.append(tuple(range(n)))
            fmats.append(cap_mi if cap_mi is not None else mi)
        if cap_end:
            base = (len(sections) - 1) * n
            faces.append(tuple(base + i for i in range(n)))
            fmats.append(cap_mi if cap_mi is not None else mi)
        base = len(self.verts)
        self.verts.extend(tuple(v) for v in verts)
        for f, fm in zip(faces, fmats):
            self.faces.append(tuple(base + i for i in f))
            self.mats.append(fm)

    def to_object(self, name, coll, materials):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        for m in materials:
            me.materials.append(m)
        for p, mi in zip(me.polygons, self.mats):
            p.material_index = mi
        me.validate()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob


def _empty(name, coll):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = 2.0
    coll.objects.link(ob)
    return ob


# ------------------------------------------------------------------- cascos

def _casco(mb, L, manga, alto, mi_casco, mi_cubierta):
    """Casco por loft de secciones. Proa en +Y, quilla en z=0."""
    ts = [0.00, 0.10, 0.28, 0.50, 0.72, 0.88, 1.00]
    wf = [0.60, 0.86, 1.00, 0.97, 0.80, 0.48, 0.045]
    fd = [1.00, 0.96, 0.94, 0.94, 1.00, 1.10, 1.24]
    fb = [0.30, 0.07, 0.00, 0.00, 0.05, 0.32, 0.92]
    sections = []
    deck = []  # (y, halfw, zdeck)
    for t, w_, d_, b_ in zip(ts, wf, fd, fb):
        y = -L * 0.5 + t * L
        w = w_ * manga * 0.5
        zd = d_ * alto
        zb = b_ * alto
        zm = zb + (zd - zb) * 0.5
        zl = zb + (zd - zb) * 0.16
        sec = [(w, y, zd), (w * 0.99, y, zm), (w * 0.80, y, zl),
               (0.0, y, zb), (-w * 0.80, y, zl), (-w * 0.99, y, zm),
               (-w, y, zd)]
        sections.append(sec)
        deck.append((y, w, zd))
    mb.loft(sections, mi=mi_casco, cap_start=True, cap_end=True)
    # cubierta (tira de quads ligeramente elevada)
    dverts = []
    for y, w, zd in deck:
        dverts.append((w, y, zd + 0.015))
        dverts.append((-w, y, zd + 0.015))
    dfaces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2)
              for i in range(len(deck) - 1)]
    mb.add(dverts, dfaces, mi_cubierta)
    return alto


# ------------------------------------------------------------------- piezas

def build_yate(parent, eslora=25.0, **params):
    """Yate blanco moderno con superestructura acristalada azul oscuro y radar."""
    M = _mats_kit()
    L = float(eslora)
    s = L / 25.0
    manga = 0.23 * L
    alto = 0.10 * L
    root = _empty("PUERTO_yate", parent)
    mb = _MB()
    mats = [M["casco"], M["cristal"], M["teca"], M["metal"], M["azul"]]
    _casco(mb, L, manga, alto, mi_casco=0, mi_cubierta=2)
    z0 = alto * 1.02
    # cabina principal + banda de cristal envolvente
    mb.box((0, -0.06 * L, z0), (0.72 * manga, 0.50 * L, 2.1 * s), mi=0)
    mb.box((0, -0.06 * L, z0 + 0.75 * s), (0.72 * manga + 0.12 * s, 0.46 * L, 0.95 * s), mi=1)
    # parabrisas inclinado en proa de la cabina
    mb.wedge((0, 0.215 * L, z0), (0.60 * manga, 0.09 * L, 2.1 * s),
             slant=0.075 * L, mi=1)
    # segunda cubierta + cristal
    mb.box((0, -0.12 * L, z0 + 2.1 * s), (0.55 * manga, 0.32 * L, 1.7 * s), mi=0)
    mb.box((0, -0.12 * L, z0 + 2.65 * s), (0.55 * manga + 0.12 * s, 0.29 * L, 0.8 * s), mi=1)
    # techo volado
    mb.box((0, -0.11 * L, z0 + 3.8 * s), (0.62 * manga, 0.36 * L, 0.22 * s), mi=0)
    zroof = z0 + 4.02 * s
    # mastil de radar + barra giratoria + radomo + antenas
    mb.cyl((0, -0.185 * L, zroof), 0.12 * s, 0.09 * s, 1.5 * s, seg=10, mi=3)
    mb.cyl_between((-0.75 * s, -0.185 * L, zroof + 1.5 * s),
                   (0.75 * s, -0.185 * L, zroof + 1.5 * s),
                   0.07 * s, 0.07 * s, seg=8, mi=3)
    mb.sphere((0, -0.05 * L, zroof + 0.38 * s), 0.38 * s, seg=12, rings=7, mi=0)
    mb.cyl((0.5 * s, -0.14 * L, zroof), 0.025 * s, 0.02 * s, 1.9 * s, seg=6, mi=3)
    mb.cyl((-0.5 * s, -0.16 * L, zroof), 0.025 * s, 0.02 * s, 1.4 * s, seg=6, mi=3)
    # plataforma de bano en popa + franja azul de flotacion en popa
    mb.box((0, -0.5 * L - 0.4 * s, alto * 0.52), (0.52 * manga, 0.95 * s, 0.12 * s), mi=0)
    ob = mb.to_object("PUERTO_yate_malla", parent, mats)
    ob.parent = root
    return root


def build_velero(parent, eslora=12.0, **params):
    """Velero blanco con mastil, botavara y velas recogidas (mayor y genova)."""
    M = _mats_kit()
    L = float(eslora)
    s = L / 12.0
    manga = 0.27 * L
    alto = 0.115 * L
    root = _empty("PUERTO_velero", parent)
    mb = _MB()
    mats = [M["casco"], M["cristal"], M["teca"], M["mastil"], M["vela"]]
    _casco(mb, L, manga, alto, mi_casco=0, mi_cubierta=2)
    # cabina baja con ojos de buey en banda
    mb.box((0, -0.02 * L, alto), (0.55 * manga, 0.28 * L, 0.55 * s), mi=0)
    mb.box((0, -0.02 * L, alto + 0.2 * s), (0.55 * manga + 0.07 * s, 0.24 * L, 0.22 * s), mi=1)
    y_m = 0.08 * L
    h_m = 1.32 * L
    # mastil, cruceta, botavara
    mb.cyl_between((0, y_m, alto * 0.9), (0, y_m, h_m), 0.09 * s, 0.045 * s, seg=8, mi=3)
    mb.cyl_between((-0.55 * s, y_m, h_m * 0.62), (0.55 * s, y_m, h_m * 0.62),
                   0.03 * s, 0.03 * s, seg=6, mi=3)
    mb.cyl_between((0, y_m - 0.005 * L, alto + 0.9 * s),
                   (0, y_m - 0.37 * L, alto + 0.9 * s), 0.06 * s, 0.05 * s, seg=8, mi=3)
    # vela mayor recogida sobre la botavara
    mb.cyl_between((0, y_m - 0.02 * L, alto + 1.08 * s),
                   (0, y_m - 0.35 * L, alto + 1.04 * s), 0.17 * s, 0.10 * s, seg=9, mi=4)
    # genova enrollado en el estay de proa
    mb.cyl_between((0, 0.47 * L, alto * 1.15), (0, y_m + 0.015 * L, h_m * 0.97),
                   0.10 * s, 0.035 * s, seg=8, mi=4)
    # estay de popa
    mb.cyl_between((0, -0.46 * L, alto * 1.05), (0, y_m, h_m * 0.985),
                   0.015 * s, 0.015 * s, seg=5, mi=3)
    ob = mb.to_object("PUERTO_velero_malla", parent, mats)
    ob.parent = root
    return root


def build_pantalan(parent, largo=40.0, **params):
    """Pantalan flotante de madera: flotadores, bastidor, tablazon y norays."""
    M = _mats_kit()
    Lg = float(largo)
    W = 3.6
    root = _empty("PUERTO_pantalan", parent)
    mb = _MB()
    mats = [M["madera_a"], M["madera_b"], M["flotador"], M["noray"]]
    # flotadores
    n_f = max(2, int(Lg / 6.0))
    for i in range(n_f):
        y = -Lg * 0.5 + (i + 0.5) * Lg / n_f
        mb.box((0, y, 0.0), (W - 0.5, 2.4, 0.55), mi=2)
    # bastidor perimetral
    mb.box((0, 0, 0.55), (W, Lg, 0.28), mi=1)
    # tablazon transversal (dos tonos alternos)
    pitch = 0.52
    n_p = int(Lg / pitch)
    for i in range(n_p):
        y = -Lg * 0.5 + (i + 0.5) * pitch
        mb.box((0, y, 0.83), (W + 0.15, 0.44, 0.07), mi=(i % 2))
    # norays de fundicion en ambos bordes
    n_n = max(2, int(Lg / 5.5))
    for i in range(n_n):
        y = -Lg * 0.5 + (i + 0.5) * Lg / n_n
        for sx in (-1, 1):
            x = sx * (W * 0.5 - 0.28)
            mb.cyl((x, y, 0.90), 0.10, 0.09, 0.30, seg=10, mi=3)
            mb.cyl((x, y, 1.20), 0.16, 0.13, 0.10, seg=10, mi=3)
    ob = mb.to_object("PUERTO_pantalan_malla", parent, mats)
    ob.parent = root
    return root


def build_faro(parent, **params):
    """Faro blanquirrojo de ~18 m: zocalo de piedra, fuste a bandas, galeria,
    linterna calida y cupula roja."""
    M = _mats_kit()
    root = _empty("PUERTO_faro", parent)
    mb = _MB()
    mats = [M["faro_b"], M["faro_r"], M["piedra"], M["farol"], M["metal"], M["azul"]]
    # zocalo + cornisa
    mb.cyl((0, 0, 0.0), 3.4, 3.2, 1.6, seg=20, mi=2)
    mb.cyl((0, 0, 1.6), 3.55, 3.55, 0.2, seg=20, mi=2)
    # puerta (rampa-porton, mundo de coches) en +Y
    mb.box((0, 2.8, 0.0), (1.9, 1.0, 1.6), mi=5)
    # fuste en 4 bandas rojo/blanco
    z = 1.8
    n_b = 4
    hb = 3.3
    for i in range(n_b):
        r1 = 2.30 + (1.45 - 2.30) * (i / n_b)
        r2 = 2.30 + (1.45 - 2.30) * ((i + 1) / n_b)
        mb.cyl((0, 0, z), r1, r2, hb, seg=18, mi=(1 if i % 2 == 0 else 0))
        z += hb
    # galeria con barandilla
    mb.cyl((0, 0, z), 2.25, 2.25, 0.32, seg=18, mi=0)
    z += 0.32
    for i in range(12):
        a = 2.0 * math.pi * i / 12.0
        mb.cyl((1.95 * math.cos(a), 1.95 * math.sin(a), z),
               0.04, 0.04, 1.0, seg=6, mi=4)
    mb.torus_ring((0, 0, z + 1.0), 1.95, 0.09, seg=20, mi=4)
    # linterna emisiva + cupula roja + remate
    mb.cyl((0, 0, z), 1.20, 1.12, 1.55, seg=14, mi=3)
    z += 1.55
    mb.cyl((0, 0, z), 1.50, 0.14, 1.40, seg=14, mi=1)
    z += 1.40
    mb.sphere((0, 0, z + 0.12), 0.20, seg=10, rings=6, mi=1)
    ob = mb.to_object("PUERTO_faro_malla", parent, mats)
    ob.parent = root
    return root


def build_dique(parent, radio=140.0, arco_grados=200.0, **params):
    """Dique curvo de escollera con paseo superior y parapeto; morros circulares
    en ambos extremos. El arco se centra en -Y (la bocana mira a +Y)."""
    M = _mats_kit()
    R = float(radio)
    arco = float(arco_grados)
    root = _empty("PUERTO_dique", parent)
    mb = _MB()
    mats = [M["piedra"], M["paseo"], M["metal"], M["farol"]]
    # perfil (offset radial desde el eje del dique, z): interior -> exterior
    prof = [(-7.0, 0.0), (-5.2, 2.6), (-4.9, 3.05), (2.8, 3.05),
            (2.8, 4.35), (3.9, 4.35), (4.1, 2.6), (9.0, 0.0)]
    strip_mats = [0, 0, 1, 0, 0, 0, 0]  # el paseo es la tira p2->p3
    a0 = math.radians(270.0 - arco * 0.5)
    a1 = math.radians(270.0 + arco * 0.5)
    n = max(16, int(round(arco / 5.0)))
    sections = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        ca, sa = math.cos(a), math.sin(a)
        sec = []
        for d, zz in prof:
            rr = R + d
            sec.append((rr * ca, rr * sa, zz))
        sections.append(sec)
    mb.loft(sections, strip_mats=strip_mats, cap_start=True, cap_end=True, cap_mi=0)
    # farolas del paseo (lado interior de la darsena)
    n_l = 9
    for i in range(n_l):
        a = a0 + (a1 - a0) * (i + 0.5) / n_l
        lx = (R - 4.2) * math.cos(a)
        ly = (R - 4.2) * math.sin(a)
        mb.cyl((lx, ly, 3.05), 0.10, 0.07, 3.0, seg=8, mi=2)
        mb.sphere((lx, ly, 6.35), 0.32, seg=8, rings=5, mi=3)
    # morros circulares en los extremos (plataforma para el faro)
    for a in (a0, a1):
        cx, cy = R * math.cos(a), R * math.sin(a)
        mb.cyl((cx, cy, 0.0), 8.0, 7.6, 3.05, seg=20, mi=0)
        mb.cyl((cx, cy, 3.05), 8.3, 8.3, 0.2, seg=20, mi=1)
    ob = mb.to_object("PUERTO_dique_malla", parent, mats)
    ob.parent = root
    return root


# ------------------------------------------------------------------- vineta

def build(parent, seed=0, **params):
    """Vineta del puerto: agua turquesa, dique con faro en el morro, pantalan
    de madera y 3 barcos (2 yates + 1 velero)."""
    rnd = random.Random(seed)
    M = _mats_kit()
    root = _empty("PUERTO_marina", parent)

    # agua
    mb = _MB()
    mb.disc((0, 0, 0), 320.0, seg=48, mi=0)
    agua = mb.to_object("PUERTO_agua", parent, [M["agua"]])
    agua.location = (0, 0, -0.22)
    agua.parent = root

    # dique (hundido levemente para ocultar la base) + faro en el morro este
    dique = build_dique(parent)
    dique.parent = root
    dique.location = (0, 0, -0.55)

    faro = build_faro(parent)
    faro.parent = root
    a_morro = math.radians(270.0 + 200.0 * 0.5)  # morro este
    faro.location = (140.0 * math.cos(a_morro), 140.0 * math.sin(a_morro),
                     -0.55 + 3.25)

    # pantalan diagonal dentro de la darsena
    pantalan = build_pantalan(parent, largo=40.0)
    pantalan.parent = root
    pantalan.location = (-52.0, -30.0, -0.35)
    pantalan.rotation_euler = (0, 0, math.radians(38.0))

    # barcos
    y1 = build_yate(parent, eslora=25.0)
    y1.parent = root
    y1.location = (48.0, -28.0, -0.60)
    y1.rotation_euler = (0, 0, math.radians(30.0 + rnd.uniform(-6, 6)))

    y2 = build_yate(parent, eslora=19.0)
    y2.parent = root
    y2.location = (0.0, -62.0, -0.50)
    y2.rotation_euler = (0, 0, math.radians(-95.0 + rnd.uniform(-8, 8)))

    v1 = build_velero(parent, eslora=12.0)
    v1.parent = root
    v1.location = (-34.5, -13.0, -0.38)
    v1.rotation_euler = (0, 0, math.radians(38.0 + rnd.uniform(-4, 4)))

    return root
