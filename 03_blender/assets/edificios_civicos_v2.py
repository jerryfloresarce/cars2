"""edificios_civicos_v2.py — Kit de edificios civicos de Porto Corsa (Cars 2).

v2 (ronda 10): corrige los MUROS CIEGOS que detectaron los revisores del
fly-through:
  - el lateral y la trasera del hotel eran una pared beige lisa frente a un
    frente muy detallado -> ahora las tres fachadas llevan el MISMO ritmo
    vertical que el frente (mismas alturas de planta, mismo tamano de hueco),
    con marco, vidrio oscuro RETRANQUEADO, contraventanas verdes y
    balconcillos en las plantas medias; banda de piedra e imposta corridas y
    cubierta con chimeneas, lucernarios y caseta (ya no es una losa pelada).
  - el testero del edificio de boxes era un rectangulo blanco liso -> ahora
    los dos testeros llevan porton de garaje / hilera de ventanas y banda de
    rotulo, y la trasera ventanas de servicio, puertas y rejillas.
  - ayuntamiento y campanile: ventanas en las cuatro caras (el campanile se ve
    desde todos los angulos en el video).

Genera PROCEDURALMENTE (solo bpy + mathutils + math) piezas del frente
maritimo de Porto Corsa, estilo Riviera italiana de la pelicula: colores
saturados y limpios, mundo de coches (sin figuras humanas, escaleras =
rampas suaves).

API PUBLICA (identica a la v1; el integrador coloca las piezas con
pos_side()/rot_facing_road() y el QA levanta un plinto desde la bbox, asi que
ni la huella ni el origen ni la orientacion cambian):

- build_ayuntamiento(parent_collection, **params)   -> Empty AYTO_root
    Municipio: palazzo salmon de 3 plantas con loggia de arcos, torre de
    reloj (~30 m) con esfera en las 4 caras, escudo dorado y bandera
    tricolor italiana. v2: ventanas en laterales y trasera y aberturas en
    las 4 caras del fuste de la torre.

- build_campanile(parent_collection, **params)      -> Empty CAMPANILE_root
    Campanario ligur esbelto (~35 m): fuste de piedra ocre-clara con
    saeteras EN LAS CUATRO CARAS, portal en la base, cuerpo de campanas con
    arcos y campanas doradas, remate piramidal verde cobre con esfera.

- build_hotel(parent_collection, **params)          -> Empty HOTEL_root
    Hotel di Porto Corsa: gran hotel crema de 6 plantas (~60 x 24 m) con
    toldos rojos, balcones corridos, pabellones de esquina con mansarda y
    rotulo 3D "HOTEL PORTO CORSA". v2: laterales, trasera y cubierta
    resueltos.

- build_boxes(parent_collection, n=12, **params)    -> Empty CARRERA_boxes
    Edificio de pit lane con n boxes numerados, terraza y muro de pits. El
    FRENTE de pit lane es identico al original; lo nuevo son los dos
    testeros y la trasera.

- build(parent_collection, seed=0, **params)        -> Empty raiz
    Muestra campanile + ayuntamiento + hotel alineados sobre el eje X
    (igual que la v1: la vineta del kit no cambia).

Unidades en metros, origen en el centro de la base, z=0 en el suelo,
fachada principal mirando a +Y.
"""

import math

import bpy
import bmesh
from mathutils import Vector

# ---------------------------------------------------------------------------
# Paleta (nombre de material -> (color sRGB, roughness, metallic))
# ---------------------------------------------------------------------------
# Colores definidos en sRGB (como se ven); se linealizan al crear el material.
# Las entradas v2 van AL FINAL para no mover los indices de la v1.
_PALETTE = (
    ("MAT_CIVICO_crema",      (0.930, 0.860, 0.680), 0.80, 0.0),
    ("MAT_CIVICO_piedra",     (0.760, 0.680, 0.530), 0.85, 0.0),
    ("MAT_CIVICO_teja",       (0.660, 0.250, 0.110), 0.75, 0.0),
    ("MAT_CIVICO_ventana",    (0.110, 0.150, 0.180), 0.25, 0.0),
    ("MAT_CIVICO_persiana",   (0.160, 0.400, 0.190), 0.60, 0.0),
    ("MAT_CIVICO_oro",        (0.930, 0.660, 0.160), 0.35, 0.85),
    ("MAT_CIVICO_blanco",     (0.955, 0.940, 0.880), 0.70, 0.0),
    ("MAT_AYTO_fachada",      (0.890, 0.430, 0.230), 0.80, 0.0),
    ("MAT_AYTO_reloj",        (0.975, 0.950, 0.850), 0.45, 0.0),
    ("MAT_CAMPANILE_piedra",  (0.900, 0.700, 0.400), 0.85, 0.0),
    ("MAT_CAMPANILE_cobre",   (0.150, 0.520, 0.410), 0.55, 0.2),
    ("MAT_HOTEL_fachada",     (0.965, 0.870, 0.620), 0.80, 0.0),
    ("MAT_HOTEL_mansarda",    (0.220, 0.290, 0.380), 0.65, 0.1),
    ("MAT_HOTEL_toldo",       (0.840, 0.100, 0.070), 0.70, 0.0),
    ("MAT_CIVICO_bandera_v",  (0.000, 0.540, 0.250), 0.70, 0.0),
    ("MAT_CIVICO_bandera_r",  (0.830, 0.090, 0.110), 0.70, 0.0),
    # --- v2 ---
    ("MAT_CIVICO_gris",       (0.175, 0.185, 0.205), 0.60, 0.0),
    ("MAT_CIVICO_acero",      (0.560, 0.585, 0.615), 0.40, 0.55),
    ("MAT_CIVICO_ocre",       (0.880, 0.560, 0.210), 0.65, 0.0),
    ("MAT_CIVICO_verde_gp",   (0.090, 0.620, 0.230), 0.50, 0.0),
    ("MAT_CIVICO_verde_osc",  (0.070, 0.270, 0.140), 0.50, 0.0),
)

# indice de cada material dentro de los slots de las mallas del kit
M = {name: i for i, (name, _c, _r, _m) in enumerate(_PALETTE)}


def _srgb_to_linear(c):
    """Convierte un canal sRGB [0..1] a lineal (lo que espera Base Color)."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _get_materials():
    """Crea (o reutiliza) los materiales de la paleta y los devuelve en orden."""
    mats = []
    for name, color, rough, metal in _PALETTE:
        mat = bpy.data.materials.get(name)
        if mat is None:
            lin = tuple(_srgb_to_linear(c) for c in color)
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
            bsdf = None
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    bsdf = node
                    break
            if bsdf is not None:
                bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
                bsdf.inputs["Roughness"].default_value = rough
                bsdf.inputs["Metallic"].default_value = metal
            mat.diffuse_color = (*lin, 1.0)
        mats.append(mat)
    return mats


# ---------------------------------------------------------------------------
# Constructor de mallas por acumulacion de primitivas cerradas
# ---------------------------------------------------------------------------
class _MB:
    """Acumula vertices/caras con indice de material por cara."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []

    def _face(self, idxs, mat):
        self.faces.append(tuple(idxs))
        self.mats.append(mat)

    # --- caja: centro (cx, cy) y z0 = base ---
    def box(self, cx, cy, z0, sx, sy, sz, mat):
        hx, hy = sx / 2.0, sy / 2.0
        b = len(self.verts)
        for z in (z0, z0 + sz):
            self.verts += [(cx - hx, cy - hy, z), (cx + hx, cy - hy, z),
                           (cx + hx, cy + hy, z), (cx - hx, cy + hy, z)]
        self._face((b + 3, b + 2, b + 1, b + 0), mat)          # base
        self._face((b + 4, b + 5, b + 6, b + 7), mat)          # tapa
        for i in range(4):
            j = (i + 1) % 4
            self._face((b + i, b + j, b + 4 + j, b + 4 + i), mat)

    # --- tronco de piramide (tejados a 4 aguas, mansardas) ---
    def frustum(self, cx, cy, z0, sx0, sy0, sx1, sy1, h, mat):
        b = len(self.verts)
        for (sx, sy, z) in ((sx0, sy0, z0), (sx1, sy1, z0 + h)):
            hx, hy = sx / 2.0, sy / 2.0
            self.verts += [(cx - hx, cy - hy, z), (cx + hx, cy - hy, z),
                           (cx + hx, cy + hy, z), (cx - hx, cy + hy, z)]
        self._face((b + 3, b + 2, b + 1, b + 0), mat)
        self._face((b + 4, b + 5, b + 6, b + 7), mat)
        for i in range(4):
            j = (i + 1) % 4
            self._face((b + i, b + j, b + 4 + j, b + 4 + i), mat)

    # --- piramide (remates) ---
    def pyramid(self, cx, cy, z0, sx, sy, h, mat):
        hx, hy = sx / 2.0, sy / 2.0
        b = len(self.verts)
        self.verts += [(cx - hx, cy - hy, z0), (cx + hx, cy - hy, z0),
                       (cx + hx, cy + hy, z0), (cx - hx, cy + hy, z0),
                       (cx, cy, z0 + h)]
        self._face((b + 3, b + 2, b + 1, b + 0), mat)
        for i in range(4):
            j = (i + 1) % 4
            self._face((b + i, b + j, b + 4), mat)

    # --- cilindro centrado en (cx, cy, cz) a lo largo de `axis` ---
    def cylinder(self, cx, cy, cz, r, length, axis, segs, mat):
        b = len(self.verts)
        half = length / 2.0
        for side in (-half, half):
            for i in range(segs):
                a = 2.0 * math.pi * i / segs
                u, v = r * math.cos(a), r * math.sin(a)
                if axis == 'Z':
                    self.verts.append((cx + u, cy + v, cz + side))
                elif axis == 'Y':
                    self.verts.append((cx + u, cy + side, cz + v))
                else:  # 'X'
                    self.verts.append((cx + side, cy + u, cz + v))
        self._face(tuple(range(b, b + segs))[::-1], mat)
        self._face(tuple(range(b + segs, b + 2 * segs)), mat)
        for i in range(segs):
            j = (i + 1) % segs
            self._face((b + i, b + j, b + segs + j, b + segs + i), mat)

    # --- esfera uv (remates dorados, campanas) ---
    def uv_sphere(self, cx, cy, cz, r, mat, segs=8, rings=5):
        b = len(self.verts)
        self.verts.append((cx, cy, cz + r))          # polo norte
        for i in range(1, rings):
            th = math.pi * i / rings
            rz, rr = r * math.cos(th), r * math.sin(th)
            for j in range(segs):
                a = 2.0 * math.pi * j / segs
                self.verts.append((cx + rr * math.cos(a),
                                   cy + rr * math.sin(a), cz + rz))
        self.verts.append((cx, cy, cz - r))          # polo sur
        south = len(self.verts) - 1
        for j in range(segs):                        # casquete norte
            j2 = (j + 1) % segs
            self._face((b, b + 1 + j, b + 1 + j2), mat)
        for i in range(rings - 2):                   # bandas
            r0, r1 = b + 1 + i * segs, b + 1 + (i + 1) * segs
            for j in range(segs):
                j2 = (j + 1) % segs
                self._face((r0 + j, r0 + j2, r1 + j2, r1 + j), mat)
        r0 = b + 1 + (rings - 2) * segs              # casquete sur
        for j in range(segs):
            j2 = (j + 1) % segs
            self._face((r0 + j2, r0 + j, south), mat)

    # --- toldo: prisma triangular colgado de la fachada (+Y) ---
    def awning(self, cx, y_wall, z_top, w, depth, drop, mat):
        hx = w / 2.0
        b = len(self.verts)
        for x in (cx - hx, cx + hx):
            self.verts += [(x, y_wall, z_top),
                           (x, y_wall + depth, z_top - drop),
                           (x, y_wall, z_top - drop)]
        self._face((b, b + 1, b + 2), mat)
        self._face((b + 5, b + 4, b + 3), mat)
        self._face((b, b + 3, b + 4, b + 1), mat)
        self._face((b + 1, b + 4, b + 5, b + 2), mat)
        self._face((b + 2, b + 5, b + 3, b), mat)

    # --- panel con remate de arco de medio punto, extruido ---
    def arch_panel(self, cu, v0, v1, z0, w, h, mat, orient='Y', segs=8):
        """Panel plano con arco. `cu` = centro en el eje de la fachada,
        v0..v1 = extrusion (y si orient='Y', x si orient='X')."""
        r = w / 2.0
        prof = [(-r, 0.0), (r, 0.0), (r, h - r)]
        for i in range(1, segs):
            a = math.pi * i / segs
            prof.append((r * math.cos(a), h - r + r * math.sin(a)))
        prof.append((-r, h - r))
        n = len(prof)
        b = len(self.verts)
        for v in (v0, v1):
            for (u, z) in prof:
                if orient == 'Y':
                    self.verts.append((cu + u, v, z0 + z))
                else:
                    self.verts.append((v, cu + u, z0 + z))
        self._face(tuple(range(b, b + n)), mat)
        self._face(tuple(range(b + n, b + 2 * n))[::-1], mat)
        for i in range(n):
            j = (i + 1) % n
            self._face((b + i, b + j, b + n + j, b + n + i), mat)

    # --- ventana con marco y persianas verdes (fachada +Y) ---
    def window(self, cx, y_wall, z0, w, h, mat_glass, mat_shutter=None,
               frame_mat=None):
        if frame_mat is not None:
            self.box(cx, y_wall + 0.02, z0 - 0.12, w + 0.3, 0.08, h + 0.3,
                     frame_mat)
        self.box(cx, y_wall + 0.05, z0, w, 0.08, h, mat_glass)
        if mat_shutter is not None:
            sw = w * 0.45
            self.box(cx - w / 2 - sw / 2 - 0.05, y_wall + 0.04, z0,
                     sw, 0.06, h, mat_shutter)
            self.box(cx + w / 2 + sw / 2 + 0.05, y_wall + 0.04, z0,
                     sw, 0.06, h, mat_shutter)

    # ------------------------------------------------------------------
    # v2: primitivas "pegadas a una fachada" (valen para las 4 caras)
    # ------------------------------------------------------------------
    def obox(self, axis, sign, u, wall, z0, su, depth, sz, mat, off=-0.03):
        """Caja apoyada en una fachada plana.

        axis  : eje NORMAL de la fachada ('Y' o 'X')
        sign  : +1 / -1, hacia donde mira la fachada
        u     : centro sobre el eje horizontal de la fachada (x si axis='Y')
        wall  : coordenada del plano de la fachada
        z0    : base de la caja;  su = ancho;  sz = alto
        depth : espesor hacia fuera;  off = separacion desde el plano
                (negativo = empotrada, evita caras coplanares con el muro)
        """
        c = wall + sign * (off + depth / 2.0)
        if axis == 'Y':
            self.box(u, c, z0, su, depth, sz, mat)
        else:
            self.box(c, u, z0, depth, su, sz, mat)

    def facade_window(self, axis, sign, u, wall, z0, w, h, mat_glass,
                      mat_frame, mat_shutter=None, mat_rail=None,
                      t=0.16, d=0.13):
        """Ventana completa sobre cualquiera de las 4 fachadas.

        El vidrio queda RETRANQUEADO: su cara exterior sobresale solo 2 cm
        del muro y queda 8 cm por detras de la cara del marco, y su cara
        interior entra 5 cm en el muro, asi que no hay ninguna cara
        coplanar (nada de z-fighting). El marco es un anillo de 4 piezas
        (alfeizar, dintel y dos jambas), no un panel macizo.
        """
        self.obox(axis, sign, u, wall, z0, w, 0.07, h, mat_glass, off=-0.05)
        wf = w + 2.0 * t + 0.14
        self.obox(axis, sign, u, wall, z0 - t, wf, d, t, mat_frame)   # alfeizar
        self.obox(axis, sign, u, wall, z0 + h, wf, d, t, mat_frame)   # dintel
        for s in (-1, 1):                                             # jambas
            self.obox(axis, sign, u + s * (w / 2.0 + t / 2.0), wall, z0,
                      t, d, h, mat_frame)
        if mat_shutter is not None:
            sw = w * 0.46
            for s in (-1, 1):
                self.obox(axis, sign, u + s * (w / 2.0 + t + sw / 2.0 + 0.02),
                          wall, z0, sw, 0.06, h, mat_shutter, off=0.10)
        if mat_rail is not None:                       # balconcillo a la
            wb = w + 2.0 * t + 0.60                    # italiana (3 piezas)
            self.obox(axis, sign, u, wall, z0 - t - 0.17, wb, 0.30, 0.17,
                      mat_rail)
            self.obox(axis, sign, u, wall, z0 - t, wb - 0.16, 0.09, 0.62,
                      mat_rail, off=0.17)
            self.obox(axis, sign, u, wall, z0 - t + 0.62, wb, 0.16, 0.09,
                      mat_rail, off=0.13)

    def louver(self, axis, sign, u, wall, z0, w, h, mat_frame, mat_slat,
               slats=3):
        """Rejilla de ventilacion (marco + lamas) para muros de servicio."""
        self.obox(axis, sign, u, wall, z0, w + 0.14, 0.10, h + 0.14, mat_frame)
        for k in range(slats):
            zk = z0 + 0.06 + k * (h - 0.06) / slats
            self.obox(axis, sign, u, wall, zk, w, 0.06, h / slats - 0.08,
                      mat_slat, off=0.07)

    def door(self, axis, sign, u, wall, z0, w, h, mat_leaf, mat_frame):
        """Puerta de servicio con jambas y dintel (hoja retranqueada)."""
        self.obox(axis, sign, u, wall, z0, w, 0.08, h, mat_leaf, off=-0.05)
        self.obox(axis, sign, u, wall, z0 + h, w + 0.46, 0.14, 0.18, mat_frame)
        for s in (-1, 1):
            self.obox(axis, sign, u + s * (w / 2.0 + 0.12), wall, z0,
                      0.24, 0.14, h, mat_frame)

    def roll_door(self, axis, sign, u, wall, z0, w, h, mat_leaf, mat_frame,
                  mat_slat, slats=4):
        """Porton de garaje enrollable (hoja oscura + lamas claras)."""
        self.obox(axis, sign, u, wall, z0, w, 0.18, h, mat_leaf, off=-0.08)
        for k in range(slats):
            self.obox(axis, sign, u, wall, z0 + 0.45 + k * (h - 0.7) / slats,
                      w - 0.06, 0.04, 0.09, mat_slat, off=0.09)
        self.obox(axis, sign, u, wall, z0 + h, w + 0.56, 0.20, 0.26, mat_frame)
        for s in (-1, 1):
            self.obox(axis, sign, u + s * (w / 2.0 + 0.14), wall, z0,
                      0.28, 0.20, h, mat_frame)


# ---------------------------------------------------------------------------
# Utilidades de objetos
# ---------------------------------------------------------------------------
def _mk_mesh_obj(name, mb, parent_collection, parent_obj=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(mb.verts, [], mb.faces)
    mesh.validate()
    for mat in _get_materials():
        mesh.materials.append(mat)
    for poly, mi in zip(mesh.polygons, mb.mats):
        poly.material_index = mi
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    parent_collection.objects.link(obj)
    if parent_obj is not None:
        obj.parent = parent_obj
    return obj


def _mk_empty(name, parent_collection, parent_obj=None):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_size = 2.0
    parent_collection.objects.link(empty)
    if parent_obj is not None:
        empty.parent = parent_obj
    return empty


# rotaciones de texto 3D segun la cara a la que se pega el rotulo
_TXT_ROT = {
    '+Y': (math.pi / 2.0, 0.0, math.pi),
    '-Y': (math.pi / 2.0, 0.0, 0.0),
    '+X': (math.pi / 2.0, 0.0, math.pi / 2.0),
    '-X': (math.pi / 2.0, 0.0, -math.pi / 2.0),
}


def _mk_text_obj(name, body, size, extrude, mat, parent_collection,
                 parent_obj=None, facing='+Y'):
    cu = bpy.data.curves.new(name, type='FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.resolution_u = 5          # low-poly de videojuego
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.materials.append(mat)
    obj = bpy.data.objects.new(name, cu)
    parent_collection.objects.link(obj)
    if parent_obj is not None:
        obj.parent = parent_obj
    # texto en el plano vertical, legible desde fuera de la cara `facing`
    obj.rotation_euler = _TXT_ROT[facing]
    return obj


def _tricolor_flag(mb, x_pole, y_pole, z_base, pole_h):
    """Mastil + bandera italiana (tres panos hacia +X)."""
    mb.cylinder(x_pole, y_pole, z_base + pole_h / 2, 0.07, pole_h, 'Z', 6,
                M["MAT_CIVICO_blanco"])
    fz = z_base + pole_h - 1.25
    for i, mat in enumerate(("MAT_CIVICO_bandera_v", "MAT_CIVICO_blanco",
                             "MAT_CIVICO_bandera_r")):
        mb.box(x_pole + 0.42 + 0.72 * i, y_pole, fz, 0.72, 0.05, 1.15, M[mat])


# ---------------------------------------------------------------------------
# PIEZA 1 — Ayuntamiento (palazzo con torre de reloj ~30 m)
# ---------------------------------------------------------------------------
def build_ayuntamiento(parent_collection, **params):
    root = _mk_empty("AYTO_root", parent_collection)
    mb = _MB()

    FAC = M["MAT_AYTO_fachada"]
    CRE = M["MAT_CIVICO_crema"]
    TEJ = M["MAT_CIVICO_teja"]
    VEN = M["MAT_CIVICO_ventana"]
    PER = M["MAT_CIVICO_persiana"]
    ORO = M["MAT_CIVICO_oro"]
    PIE = M["MAT_CIVICO_piedra"]
    GRI = M["MAT_CIVICO_gris"]

    # cuerpo principal: 22 x 13, 3 plantas
    mb.box(0, 0, 0, 22.0, 13.0, 11.0, FAC)
    mb.box(0, 0, 0, 22.6, 13.6, 1.2, PIE)               # zocalo
    mb.box(0, 0, 10.6, 22.9, 13.9, 0.7, CRE)            # cornisa
    mb.frustum(0, 0, 11.3, 22.5, 13.5, 15.5, 7.0, 2.4, TEJ)  # tejado 4 aguas

    yf = 6.5                                            # plano de fachada +Y
    # loggia de arcos en planta baja (4 arcos + pilastras)
    for ax in (-7.4, -4.0, 4.0, 7.4):
        mb.arch_panel(ax, yf + 0.02, yf + 0.10, 0.7, 2.2, 3.8, VEN)
    for px in (-9.0, -5.7, -2.3, 2.3, 5.7, 9.0):
        mb.box(px, yf + 0.10, 0.6, 0.55, 0.22, 4.6, CRE)
    mb.box(0, yf + 0.06, 4.9, 18.6, 0.18, 0.35, CRE)    # imposta sobre arcos

    # ventanas plantas 2 y 3 con persianas verdes
    for wx in (-9.4, -7.0, -4.2, 4.2, 7.0, 9.4):
        mb.window(wx, yf, 5.5, 1.1, 2.0, VEN, PER, CRE)
        mb.window(wx, yf, 8.5, 1.1, 1.6, VEN, PER, CRE)

    # --- v2: LATERALES (x = +-11) con el mismo ritmo que el frente ---------
    for sgn in (-1, 1):
        xw = sgn * 11.0
        mb.obox('X', sgn, 0.0, xw, 1.2, 13.2, 0.12, 0.9, PIE)     # banda piedra
        mb.obox('X', sgn, 0.0, xw, 4.9, 13.2, 0.18, 0.35, CRE)    # imposta
        for wy in (-3.4, 3.4):                                    # planta baja
            mb.arch_panel(wy, xw + sgn * 0.02, xw + sgn * 0.12, 2.2, 1.8, 2.5,
                          VEN, orient='X')
        for wy in (-4.4, 0.0, 4.4):
            mb.facade_window('X', sgn, wy, xw, 5.5, 1.1, 2.0, VEN, CRE, PER,
                             CRE)
            mb.facade_window('X', sgn, wy, xw, 8.5, 1.1, 1.6, VEN, CRE, PER)

    # --- v2: TRASERA (y = -6.5) -------------------------------------------
    yb = -6.5
    mb.obox('Y', -1, 0.0, yb, 1.2, 22.2, 0.12, 0.9, PIE)
    mb.obox('Y', -1, 0.0, yb, 4.9, 22.2, 0.18, 0.35, CRE)
    mb.door('Y', -1, 0.0, yb, 1.2, 2.6, 3.3, GRI, CRE)            # acceso
    mb.obox('Y', -1, 0.0, yb, 4.55, 4.2, 0.30, 0.3, CRE)          # marquesina
    for bx in (-8.4, -4.6, 4.6, 8.4):
        mb.arch_panel(bx, yb - 0.12, yb - 0.02, 2.2, 1.8, 2.5, VEN)
    for bx in (-9.4, -6.3, -3.15, 0.0, 3.15, 6.3, 9.4):
        mb.facade_window('Y', -1, bx, yb, 5.5, 1.1, 2.0, VEN, CRE, PER, CRE)
        mb.facade_window('Y', -1, bx, yb, 8.5, 1.1, 1.6, VEN, CRE, PER)

    # --- torre del reloj (frontal, centrada) ---
    ty = 4.6                                            # centro Y de la torre
    tw = 4.6
    mb.box(0, ty, 0, tw, tw, 23.0, FAC)
    for sx in (-1, 1):                                  # esquinas crema
        for sy in (-1, 1):
            mb.box(sx * (tw / 2 - 0.25), ty + sy * (tw / 2 - 0.25), 1.2,
                   0.55, 0.55, 21.8, CRE)
    tyf = ty + tw / 2                                   # frente de la torre
    mb.arch_panel(0, tyf + 0.02, tyf + 0.12, 0.7, 2.6, 4.4, VEN)  # portal
    mb.box(0, tyf + 0.10, 5.6, 3.4, 0.25, 0.3, CRE)     # balconcito
    mb.window(0, tyf + 0.1, 6.0, 1.2, 2.0, VEN, PER, CRE)
    mb.cylinder(0, tyf + 0.10, 10.4, 0.85, 0.22, 'Y', 12, ORO)  # escudo

    # v2: el fuste ya no es liso por ningun lado (se ve desde los 4 angulos)
    for z in (14.0, 20.2):
        mb.box(0, ty, z, tw + 0.28, tw + 0.28, 0.24, CRE)         # cursos
    for (axis, sgn, wall, u) in (('Y', 1, ty + tw / 2, 0.0),
                                 ('Y', -1, ty - tw / 2, 0.0),
                                 ('X', 1, tw / 2, ty),
                                 ('X', -1, -tw / 2, ty)):
        for z0 in (15.0, 18.5):
            mb.facade_window(axis, sgn, u, wall, z0, 0.95, 1.9, VEN, CRE,
                             t=0.13, d=0.11)

    mb.box(0, ty, 22.6, tw + 0.7, tw + 0.7, 0.6, CRE)   # cornisa fuste

    # cuerpo del reloj
    cz0, cs = 23.2, 4.9
    mb.box(0, ty, cz0, cs, cs, 4.2, CRE)
    ck = cz0 + 2.1                                      # centro del reloj
    mb.cylinder(0, ty, ck, 1.55, cs + 0.25, 'Y', 16, ORO)   # bisel frontal
    mb.cylinder(0, ty, ck, 1.30, cs + 0.55, 'Y', 16, M["MAT_AYTO_reloj"])
    mb.cylinder(0, ty, ck, 1.55, cs + 0.25, 'X', 16, ORO)   # bisel lateral
    mb.cylinder(0, ty, ck, 1.30, cs + 0.55, 'X', 16, M["MAT_AYTO_reloj"])
    dv = cs / 2 + 0.31                                  # agujas (marcan las 3)
    for sgn in (1, -1):
        mb.box(0, ty + sgn * dv, ck, 0.11, 0.06, 1.65, VEN)        # minutero
        mb.box(sgn * 0.38, ty + sgn * dv, ck - 0.05, 0.75, 0.06, 0.11, VEN)
    for sgn in (1, -1):                                 # caras laterales
        mb.box(sgn * dv, ty, ck, 0.06, 0.11, 1.65, VEN)
        mb.box(sgn * dv, ty + 0.38, ck - 0.05, 0.06, 0.75, 0.11, VEN)

    mb.box(0, ty, 27.4, cs + 0.8, cs + 0.8, 0.55, CRE)  # cornisa reloj
    mb.pyramid(0, ty, 27.95, cs + 0.5, cs + 0.5, 2.6, TEJ)  # chapitel teja
    _tricolor_flag(mb, 0, ty, 30.1, 3.6)                # bandera (~33.7 m)

    # rampas de acceso (mundo de coches: sin escaleras)
    mb.frustum(0, yf + 1.3, 0, 12.0, 2.6, 11.0, 0.9, 0.9, PIE)

    # v2: chimeneas sobre el tejado (no es una faldon pelado)
    for (cx, cy) in ((-5.2, 1.4), (5.2, -1.4)):
        mb.box(cx, cy, 12.6, 0.95, 0.8, 1.7, CRE)
        mb.box(cx, cy, 14.3, 1.2, 1.05, 0.25, TEJ)

    _mk_mesh_obj("AYTO_palazzo", mb, parent_collection, root)
    return root


# ---------------------------------------------------------------------------
# PIEZA 2 — Campanile ligur (~35 m)
# ---------------------------------------------------------------------------
def build_campanile(parent_collection, **params):
    root = _mk_empty("CAMPANILE_root", parent_collection)
    mb = _MB()

    PIE = M["MAT_CAMPANILE_piedra"]
    CRE = M["MAT_CIVICO_crema"]
    COB = M["MAT_CAMPANILE_cobre"]
    VEN = M["MAT_CIVICO_ventana"]
    ORO = M["MAT_CIVICO_oro"]

    mb.box(0, 0, 0, 5.4, 5.4, 1.6, M["MAT_CIVICO_piedra"])  # plinto
    mb.box(0, 0, 0, 4.2, 4.2, 22.0, PIE)                    # fuste

    # esquinas y cursos horizontales crema
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box(sx * 1.85, sy * 1.85, 1.6, 0.5, 0.5, 20.4, CRE)
    for z in (9.5, 15.5):
        mb.box(0, 0, z, 4.5, 4.5, 0.28, CRE)

    # v2: saeteras enmarcadas EN LAS CUATRO CARAS (el campanile se ve desde
    # todos los angulos en el video; antes solo tenia hueco el frente)
    caras = (('Y', 1, 2.1, 0.0), ('Y', -1, -2.1, 0.0),
             ('X', 1, 2.1, 0.0), ('X', -1, -2.1, 0.0))
    for (axis, sgn, wall, u) in caras:
        for z0 in (7.0, 12.0, 17.0):
            mb.facade_window(axis, sgn, u, wall, z0, 0.55, 1.7, VEN, CRE,
                             t=0.14, d=0.10)

    # portal de acceso en la base (arco crema + hueco oscuro retranqueado)
    mb.arch_panel(0, 2.06, 2.24, 1.5, 2.4, 3.7, CRE)
    mb.arch_panel(0, 2.01, 2.16, 1.6, 1.9, 3.2, VEN)
    # rampa al portal (mundo de coches): cabe dentro de la huella del plinto
    mb.frustum(0, 2.45, 0, 3.4, 1.2, 3.0, 1.0, 1.6, M["MAT_CIVICO_piedra"])

    # cuerpo de campanas con arco en las 4 caras
    bz0, bs = 22.0, 5.0
    mb.box(0, 0, bz0, bs, bs, 6.5, PIE)
    hf = bs / 2
    az0, aw, ah = bz0 + 0.9, 2.3, 4.6
    mb.arch_panel(0, hf - 0.4, hf + 0.06, az0, aw, ah, VEN, orient='Y')
    mb.arch_panel(0, -hf - 0.06, -hf + 0.4, az0, aw, ah, VEN, orient='Y')
    mb.arch_panel(0, hf - 0.4, hf + 0.06, az0, aw, ah, VEN, orient='X')
    mb.arch_panel(0, -hf - 0.06, -hf + 0.4, az0, aw, ah, VEN, orient='X')
    for sx in (-1, 1):                                  # pilastras esquina
        for sy in (-1, 1):
            mb.box(sx * (hf - 0.28), sy * (hf - 0.28), bz0, 0.6, 0.6, 6.5,
                   CRE)

    # campanas doradas asomando en cada cara
    bell_z = az0 + 2.1
    for (bx, by) in ((0, hf - 0.15), (0, -hf + 0.15),
                     (hf - 0.15, 0), (-hf + 0.15, 0)):
        mb.uv_sphere(bx, by, bell_z, 0.55, ORO, segs=8, rings=4)
        mb.cylinder(bx, by, bell_z - 0.55, 0.62, 0.28, 'Z', 8, ORO)

    mb.box(0, 0, 28.5, 6.1, 6.1, 0.8, CRE)              # cornisa
    mb.pyramid(0, 0, 29.3, 5.7, 5.7, 5.2, COB)          # chapitel verde cobre
    mb.cylinder(0, 0, 34.1, 0.07, 1.6, 'Z', 6, ORO)     # aguja
    mb.uv_sphere(0, 0, 35.1, 0.34, ORO, segs=8, rings=4)  # esfera dorada

    _mk_mesh_obj("CAMPANILE_torre", mb, parent_collection, root)
    return root


# ---------------------------------------------------------------------------
# PIEZA 3 — Hotel di Porto Corsa (~60 x 24 m, 6 plantas)
# ---------------------------------------------------------------------------
def build_hotel(parent_collection, **params):
    root = _mk_empty("HOTEL_root", parent_collection)
    mb = _MB()

    FAC = M["MAT_HOTEL_fachada"]
    CRE = M["MAT_CIVICO_crema"]
    BLA = M["MAT_CIVICO_blanco"]
    PIE = M["MAT_CIVICO_piedra"]
    VEN = M["MAT_CIVICO_ventana"]
    PER = M["MAT_CIVICO_persiana"]
    TOL = M["MAT_HOTEL_toldo"]
    MAN = M["MAT_HOTEL_mansarda"]
    ORO = M["MAT_CIVICO_oro"]
    TEJ = M["MAT_CIVICO_teja"]
    GRI = M["MAT_CIVICO_gris"]
    ACE = M["MAT_CIVICO_acero"]

    body_h = 21.6
    mb.box(0, 0, 0, 60.8, 24.8, 0.9, PIE)               # plinto
    mb.box(0, 0, 0, 42.0, 22.0, body_h, FAC)            # cuerpo central
    for px in (-24.5, 24.5):                            # pabellones esquina
        mb.box(px, 0, 0, 11.0, 24.0, body_h, FAC)

    # cornisas
    mb.box(0, 0, body_h, 43.6, 23.0, 0.7, CRE)
    for px in (-24.5, 24.5):
        mb.box(px, 0, body_h, 12.4, 25.4, 0.7, CRE)

    # parapeto central con rotulo + mansardas en pabellones
    mb.box(0, 10.8, 22.3, 41.6, 0.8, 1.3, FAC)          # parapeto frontal
    mb.box(0, -10.8, 22.3, 41.6, 0.8, 1.3, FAC)
    for px in (-24.5, 24.5):
        mb.frustum(px, 0, 22.3, 11.8, 25.2, 7.6, 18.0, 2.8, MAN)
        mb.box(px, 0, 25.1, 7.9, 18.3, 0.3, CRE)
        mb.uv_sphere(px, 0, 25.75, 0.32, ORO, segs=8, rings=4)

    yf_main, yf_pav = 11.0, 12.0                        # planos de fachada

    # filas de plantas 2..6
    rows = [4.6 + i * 3.4 for i in range(5)]
    main_bays = [-17.6, -13.2, -8.8, 8.8, 13.2, 17.6]
    entry_bays = [-4.4, 0.0, 4.4]
    pav_bays = [-26.7, -22.3, 22.3, 26.7]

    for base in rows:
        wz = base + 0.35
        # balcon corrido del cuerpo central
        mb.box(0, 11.6, base, 38.0, 1.5, 0.22, BLA)
        mb.box(0, 12.28, base + 0.22, 38.0, 0.14, 0.85, BLA)
        for bx in main_bays + entry_bays:
            mb.box(bx, yf_main + 0.04, wz, 1.5, 0.10, 2.4, VEN)
            mb.awning(bx, yf_main + 0.05, wz + 2.75, 1.9, 1.0, 0.7, TOL)
        # balcones de los pabellones
        for px in (-24.5, 24.5):
            mb.box(px, 12.6, base, 9.6, 1.4, 0.22, BLA)
            mb.box(px, 13.22, base + 0.22, 9.6, 0.14, 0.85, BLA)
        for bx in pav_bays:
            mb.box(bx, yf_pav + 0.04, wz, 1.5, 0.10, 2.4, VEN)
            mb.awning(bx, yf_pav + 0.05, wz + 2.75, 1.9, 1.0, 0.7, TOL)

    # planta baja: arcos + entrada con marquesina
    for bx in main_bays:
        mb.arch_panel(bx, yf_main + 0.02, yf_main + 0.12, 0.9, 2.0, 3.6, VEN)
    for bx in pav_bays:
        mb.arch_panel(bx, yf_pav + 0.02, yf_pav + 0.12, 0.9, 2.0, 3.6, VEN)
    for bx in entry_bays:
        mb.arch_panel(bx, yf_main + 0.02, yf_main + 0.12, 0.7, 2.4, 4.0, VEN)
    for cx_col in (-4.0, 4.0):
        mb.cylinder(cx_col, 13.6, 2.1, 0.28, 4.2, 'Z', 8, CRE)
    mb.box(0, 12.6, 4.2, 10.6, 3.6, 0.45, CRE)          # marquesina
    mb.box(0, 14.35, 4.05, 10.6, 0.16, 0.75, TOL)       # cenefa roja
    mb.box(0, 0, 0, 12.0, 25.0, 0.5, PIE)               # rampa-acera entrada
    mb.frustum(0, 13.4, 0, 11.0, 3.6, 10.2, 2.4, 0.55, PIE)  # rampa suave

    # banda de imposta sobre planta baja
    mb.box(0, yf_main, 4.35, 42.2, 0.25, 0.4, CRE)
    for px in (-24.5, 24.5):
        mb.box(px, yf_pav, 4.35, 11.2, 0.25, 0.4, CRE)

    # =====================================================================
    # v2 — LATERALES Y TRASERA (antes: pared beige lisa)
    # Mismo ritmo vertical que el frente: mismas filas `rows`, mismo hueco
    # de 1.5 x 2.4 m, marco crema, vidrio oscuro retranqueado, persianas
    # verdes y balconcillo en las plantas medias.
    # =====================================================================
    side_bays = (-9.2, -4.6, 0.0, 4.6, 9.2)             # laterales x = +-30
    rear_main = (-17.0, -12.75, -8.5, -4.25, 0.0, 4.25, 8.5, 12.75, 17.0)
    rear_pav = {-1: (-27.1, -21.9), 1: (21.9, 27.1)}

    for i, base in enumerate(rows):
        wz = base + 0.35
        rail = CRE if i <= 2 else None                  # plantas medias
        for sgn in (-1, 1):
            xw = sgn * 30.0
            for by in side_bays:
                mb.facade_window('X', sgn, by, xw, wz, 1.5, 2.4, VEN, CRE,
                                 PER, rail)
        for bx in rear_main:
            mb.facade_window('Y', -1, bx, -11.0, wz, 1.5, 2.4, VEN, CRE,
                             PER, rail)
        for sgn in (-1, 1):
            for bx in rear_pav[sgn]:
                mb.facade_window('Y', -1, bx, -12.0, wz, 1.5, 2.4, VEN, CRE,
                                 PER, rail)

    # zocalo de piedra + imposta corridos por laterales y trasera
    for sgn in (-1, 1):
        xw = sgn * 30.0
        mb.obox('X', sgn, 0.0, xw, 0.9, 24.3, 0.12, 0.95, PIE)
        mb.obox('X', sgn, 0.0, xw, 4.35, 24.3, 0.22, 0.4, CRE)
        for by in (-7.0, 0.0, 7.0):                     # planta baja
            mb.arch_panel(by, xw + sgn * 0.02, xw + sgn * 0.12, 1.9, 2.0, 2.3,
                          VEN, orient='X')
    mb.obox('Y', -1, 0.0, -11.0, 0.9, 42.2, 0.12, 0.95, PIE)
    mb.obox('Y', -1, 0.0, -11.0, 4.35, 42.2, 0.22, 0.4, CRE)
    for sgn in (-1, 1):
        mb.obox('Y', -1, sgn * 24.5, -12.0, 0.9, 11.2, 0.12, 0.95, PIE)
        mb.obox('Y', -1, sgn * 24.5, -12.0, 4.35, 11.2, 0.22, 0.4, CRE)
        mb.arch_panel(sgn * 24.5, -12.12, -12.02, 1.9, 2.2, 2.4, VEN)

    # planta baja de la trasera: acceso de servicio + arcos
    mb.door('Y', -1, 0.0, -11.0, 0.9, 3.0, 3.2, GRI, CRE)
    mb.obox('Y', -1, 0.0, -11.0, 4.1, 5.6, 1.5, 0.35, CRE)     # marquesina
    for bx in (-17.0, -12.75, -8.5, 8.5, 12.75, 17.0):
        mb.arch_panel(bx, -11.12, -11.02, 1.9, 2.0, 2.3, VEN)
    for bx in (-4.25, 4.25):
        mb.louver('Y', -1, bx, -11.0, 2.2, 1.6, 1.5, CRE, ACE)

    # --- cubierta: terraza de grava, chimeneas, lucernarios y caseta ------
    mb.box(0, 0, 22.2, 40.8, 20.8, 0.18, PIE)           # terraza
    for (cx, cy) in ((-16.8, 6.2), (-16.8, -6.2), (-9.0, 7.0), (-9.0, -7.0),
                     (9.0, 7.0), (9.0, -7.0), (16.8, 6.2), (16.8, -6.2)):
        mb.box(cx, cy, 22.3, 1.05, 0.9, 1.95, CRE)      # chimenea
        mb.box(cx, cy, 24.25, 1.35, 1.2, 0.26, TEJ)     # remate
    mb.box(-3.2, -3.4, 22.3, 5.4, 3.8, 2.5, FAC)        # caseta de maquinas
    mb.box(-3.2, -3.4, 24.8, 5.9, 4.3, 0.3, CRE)
    mb.door('Y', 1, -3.2, -1.5, 22.35, 1.5, 2.0, GRI, CRE)
    for cx in (3.6, 7.2):                               # lucernarios
        mb.box(cx, -4.6, 22.35, 2.2, 2.2, 0.35, CRE)
        mb.box(cx, -4.6, 22.70, 1.9, 1.9, 0.12, VEN)
    for (cx, cy) in ((3.2, 3.6), (6.6, 3.6)):           # climatizadores
        mb.box(cx, cy, 22.38, 2.0, 1.4, 0.85, ACE)
    for (cx, cy) in ((-12.6, 0.0), (0.0, 0.0), (12.6, 0.0)):
        mb.cylinder(cx, cy, 22.95, 0.30, 1.2, 'Z', 8, ACE)   # extractores

    # mastil central con banderin rojo del GP
    mb.cylinder(0, 9.8, 25.2, 0.07, 3.2, 'Z', 6, BLA)
    mb.box(0.75, 9.8, 26.0, 1.35, 0.04, 0.55, TOL)

    _mk_mesh_obj("HOTEL_edificio", mb, parent_collection, root)

    # rotulo 3D en el parapeto de la cornisa
    txt = _mk_text_obj("HOTEL_rotulo", "HOTEL PORTO CORSA", 1.72, 0.07,
                       _get_materials()[ORO], parent_collection, root)
    txt.location = (0.0, 11.28, 22.98)
    return root


# ---------------------------------------------------------------------------
# PIEZA 4 — Edificio de boxes del pit lane
# ---------------------------------------------------------------------------
def build_boxes(parent_collection, n=12, **params):
    """Edificio de pit lane con n boxes numerados, terraza y muro de pits.

    El FRENTE de pit lane (+Y) es exactamente el del kit original: cuerpo
    crema, cornisa de terracota, balaustrada, pilastras ocres, portones
    oscuros con lamas, placas numeradas y muro de pits con franja verde.
    La v2 anade lo que faltaba: los dos TESTEROS (porton de garaje, hilera
    de ventanas y banda de rotulo) y la TRASERA (ventanas de servicio,
    puertas, rejillas y equipos en la terraza).
    """
    root = _mk_empty("CARRERA_boxes", parent_collection)
    mb = _MB()

    CRE = M["MAT_CIVICO_crema"]
    TEJ = M["MAT_CIVICO_teja"]
    BLA = M["MAT_CIVICO_blanco"]
    GRI = M["MAT_CIVICO_gris"]
    OCR = M["MAT_CIVICO_ocre"]
    VGP = M["MAT_CIVICO_verde_gp"]
    VOS = M["MAT_CIVICO_verde_osc"]
    VEN = M["MAT_CIVICO_ventana"]
    ACE = M["MAT_CIVICO_acero"]

    w = 6.0
    L = n * w
    fondo = 9.0
    h = 5.2
    yf = fondo / 2.0                                    # frente de pit lane
    yb = -fondo / 2.0                                   # trasera
    xe = L / 2.0                                        # testeros

    # --- cuerpo, cornisa y terraza (igual que el original) ---------------
    mb.box(0, 0, 0, L, fondo, h, CRE)
    mb.box(0, 0, h, L + 0.8, fondo + 0.8, 0.34, TEJ)
    mb.box(0, yf - 0.15, h + 0.34, L, 0.14, 0.7, BLA)   # balaustrada

    # --- frente de pit lane: INTACTO -------------------------------------
    for i in range(n + 1):
        mb.box(-L / 2.0 + i * w, yf - 0.05, 0, 0.5, 0.4, h, OCR)
    for i in range(n):
        cx = -L / 2.0 + (i + 0.5) * w
        mb.box(cx, yf - 0.05, 0.0, 4.6, 0.2, 3.9, GRI)          # porton
        for k in range(4):
            mb.box(cx, yf + 0.06, 0.52 + k * 0.95, 4.6, 0.03, 0.06, BLA)
        mb.box(cx, yf - 0.02, 4.05, 1.2, 0.16, 1.0, BLA)        # placa
    mb.box(0, 11.5, 0.0, L * 0.92, 0.5, 1.1, BLA)               # muro de pits
    mb.box(0, 11.5, 1.10, L * 0.92, 0.54, 0.24, VGP)

    # =====================================================================
    # v2 — TESTEROS (antes: rectangulo blanco liso) y TRASERA
    # =====================================================================
    for sgn in (1, -1):
        xw = sgn * xe
        mb.obox('X', sgn, 0.0, xw, 0.0, fondo + 0.12, 0.14, 0.55, OCR)  # zocalo
        mb.obox('X', sgn, 0.0, xw, 4.72, fondo + 0.12, 0.16, 0.22, OCR)  # friso
        # banda de rotulo verde con filete blanco
        mb.obox('X', sgn, 0.0, xw, 3.68, fondo - 0.4, 0.16, 1.0, BLA)
        mb.obox('X', sgn, 0.0, xw, 3.78, fondo - 0.8, 0.10, 0.8, VGP,
                off=0.13)
        for sl in (-1, 1):                              # focos del rotulo
            mb.obox('X', sgn, sl * 2.6, xw, 4.86, 0.5, 0.35, 0.18, ACE,
                    off=0.10)

    # testero +X: porton de garaje (el que da a la pista) + ventanas
    mb.roll_door('X', 1, 0.0, xe, 0.0, 4.0, 3.2, GRI, CRE, BLA)
    for by in (-3.3, 3.3):
        mb.facade_window('X', 1, by, xe, 1.5, 1.1, 1.5, VEN, CRE, t=0.14,
                         d=0.11)
    # testero -X: hilera de ventanas + puerta de servicio
    for by in (-2.9, 0.0, 2.9):
        mb.facade_window('X', -1, by, -xe, 1.9, 1.2, 1.8, VEN, CRE, t=0.14,
                         d=0.11)
    mb.door('X', -1, 0.0, -xe, 0.0, 1.3, 1.9, GRI, CRE)
    for by in (-3.6, 3.6):
        mb.louver('X', -1, by, -xe, 3.0, 0.8, 0.7, CRE, ACE)

    # trasera: ventanas de servicio por box, puertas y rejillas
    mb.obox('Y', -1, 0.0, yb, 0.0, L, 0.14, 0.5, OCR)           # zocalo
    mb.obox('Y', -1, 0.0, yb, 4.05, L, 0.16, 0.24, OCR)         # friso
    for i in range(n):
        cx = -L / 2.0 + (i + 0.5) * w
        if i % 5 == 2:
            mb.door('Y', -1, cx, yb, 0.0, 1.5, 2.6, GRI, CRE)
            mb.louver('Y', -1, cx, yb, 3.0, 1.1, 0.8, CRE, ACE)
        else:
            mb.facade_window('Y', -1, cx, yb, 1.7, 1.3, 1.7, VEN, CRE,
                             t=0.14, d=0.11)
            mb.obox('Y', -1, cx, yb, 3.65, 1.0, 0.10, 0.35, ACE)  # rejilla
    for i in range(n + 1):                              # lesenas verticales
        mb.obox('Y', -1, -L / 2.0 + i * w, yb, 0.5, 0.36, 0.10, 3.5, OCR)

    # equipos sobre la terraza (se ve desde arriba en el fly-through); todo
    # por debajo de la cota de la balaustrada + 20 cm para no crecer la bbox
    for i in range(0, n, 3):
        cx = -L / 2.0 + (i + 1.5) * w
        mb.box(cx, -1.6, h + 0.34, 2.4, 1.6, 0.86, ACE)
        mb.cylinder(cx + 1.6, -1.6, h + 0.75, 0.22, 0.8, 'Z', 8, ACE)
    for i in range(0, n, 2):                            # postes de camara TV
        cx = -L / 2.0 + (i + 0.5) * w
        mb.cylinder(cx, 0.6, h + 0.62, 0.06, 0.56, 'Z', 6, GRI)
        mb.box(cx, 0.6, h + 0.68, 0.34, 0.5, 0.22, GRI)

    edificio = _mk_mesh_obj("CARRERA_boxes_edificio", mb, parent_collection,
                            root)
    edificio.parent = root

    mats = _get_materials()
    for i in range(n):
        cx = -L / 2.0 + (i + 0.5) * w
        num = _mk_text_obj("CARRERA_boxes_num%02d" % (i + 1), str(i + 1),
                           0.72, 0.04, mats[VOS], parent_collection, root)
        num.location = (cx, yf + 0.08, 4.53)
    for sgn, facing in ((1, '+X'), (-1, '-X')):
        rot = _mk_text_obj("CARRERA_boxes_rotulo%s" % ('A' if sgn > 0 else 'B'),
                           "BOX", 0.62, 0.04, mats[BLA], parent_collection,
                           root, facing=facing)
        rot.location = (sgn * (xe + 0.30), 0.0, 4.18)
    return root


# ---------------------------------------------------------------------------
# Kit completo
# ---------------------------------------------------------------------------
def build(parent_collection, seed=0, **params):
    """Crea las tres piezas alineadas y devuelve el Empty raiz."""
    root = _mk_empty("EDIFICIOS_CIVICOS_root", parent_collection)

    campanile = build_campanile(parent_collection)
    campanile.parent = root
    campanile.location = (-46.0, 0.0, 0.0)

    ayto = build_ayuntamiento(parent_collection)
    ayto.parent = root
    ayto.location = (-22.0, 0.0, 0.0)

    hotel = build_hotel(parent_collection)
    hotel.parent = root
    hotel.location = (26.0, 0.0, 0.0)

    return root
