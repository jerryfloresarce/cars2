"""casas_kit.py — Kit modular de manzanas estilo Portofino/Vernazza (Porto Corsa, Cars 2).

Genera PROCEDURALMENTE (sin archivos externos) casas de estuco de la Riviera
italiana "car-ificada": fachadas ocre/salmón/amarillo/crema/rosa, persianas
verdes, tejados de terracota a dos aguas o planos con cornisa, balcones de
forja sencillos, bajos con puerta/escaparate y toldo a rayas opcional, y
chimeneas con forma de tubo de escape (detalle firma).

Piezas del kit (todas linkan a `parent_collection` y devuelven el objeto raíz):
  build_casa(parent_collection, plantas=4, ancho=10, fondo=12,
             color=None, seed=0, tejado='auto', name=None, **params)
      Una casa. Pivote en el CENTRO DE LA FACHADA (x=0), fachada en el plano
      y=0 mirando a +Y, cuerpo hacia -Y, base en z=0. <=4k tris.
  build_manzana(parent_collection, n=6, seed=0, **params)
      Hilera de n casas pegadas (alturas 3-6 plantas, paleta variada),
      centrada en x=0, fachadas alineadas en y=0. Devuelve un Empty raíz;
      cada casa conserva su pivote de fachada para poder pegarse en curva.
  build(parent_collection, seed=0, **params)
      = build_manzana de 6 casas.

Unidades: metros. Materiales: Principled BSDF de color plano, reutilizados.
"""

import math
import random

import bpy

# ---------------------------------------------------------------------------
# Paleta (Cars 2: saturado y limpio). Definida en sRGB y convertida a lineal
# para que el render conserve la saturación de la película.
# ---------------------------------------------------------------------------

def _srgb(r, g, b):
    """sRGB 0-1 -> lineal (aprox gamma 2.2)."""
    return tuple(c ** 2.2 for c in (r, g, b))


PALETA_FACHADA = {
    "ocre": _srgb(0.85, 0.56, 0.18),
    "salmon": _srgb(0.91, 0.48, 0.35),
    "amarillo": _srgb(0.95, 0.76, 0.22),
    "crema": _srgb(0.94, 0.83, 0.55),
    "rosa": _srgb(0.90, 0.49, 0.46),
}

COL_TEJA = _srgb(0.67, 0.27, 0.14)
COL_PERSIANA = _srgb(0.24, 0.45, 0.22)
COL_PIEDRA = _srgb(0.96, 0.93, 0.84)
COL_FORJA = (0.02, 0.02, 0.025)
COL_VIDRIO = _srgb(0.22, 0.34, 0.38)
COL_MADERA = _srgb(0.42, 0.24, 0.11)
COL_METAL = _srgb(0.52, 0.53, 0.55)
COL_CROMO = _srgb(0.85, 0.87, 0.90)
COL_TOLDO_BLANCO = _srgb(0.95, 0.93, 0.88)
COLS_TOLDO = {
    "rojo": _srgb(0.80, 0.16, 0.12),
    "verde": _srgb(0.16, 0.48, 0.22),
    "azul": _srgb(0.16, 0.32, 0.62),
}


def _get_mat(nombre, color, rough=0.85, metallic=0.0):
    """Crea (o reutiliza) un material Principled BSDF de color plano."""
    mat = bpy.data.materials.get(nombre)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = (*color, 1.0)
    return mat


# ---------------------------------------------------------------------------
# Constructor de mallas por acumulación (from_pydata, sin bpy.ops)
# ---------------------------------------------------------------------------

class _MB:
    """Acumula cajas/quads/cilindros con índice de material por cara."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.fmats = []
        self.mats = []          # lista ordenada de materiales
        self._mat_idx = {}

    def _mi(self, mat):
        if mat.name not in self._mat_idx:
            self._mat_idx[mat.name] = len(self.mats)
            self.mats.append(mat)
        return self._mat_idx[mat.name]

    def quad(self, a, b, c, d, mat):
        i = len(self.verts)
        self.verts.extend([a, b, c, d])
        self.faces.append((i, i + 1, i + 2, i + 3))
        self.fmats.append(self._mi(mat))

    def tri(self, a, b, c, mat):
        i = len(self.verts)
        self.verts.extend([a, b, c])
        self.faces.append((i, i + 1, i + 2))
        self.fmats.append(self._mi(mat))

    def box(self, x0, x1, y0, y1, z0, z1, mat):
        i = len(self.verts)
        self.verts.extend([
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ])
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                  (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            self.faces.append(tuple(i + k for k in f))
            self.fmats.append(self._mi(mat))

    def prisma(self, top4, espesor, mat):
        """Placa gruesa: quad superior (4 puntos) extruido -z `espesor`."""
        bot = [(x, y, z - espesor) for (x, y, z) in top4]
        i = len(self.verts)
        self.verts.extend(top4)
        self.verts.extend(bot)
        self.faces.append((i, i + 1, i + 2, i + 3))            # top
        self.faces.append((i + 7, i + 6, i + 5, i + 4))        # bottom
        for k in range(4):
            a, b = k, (k + 1) % 4
            self.faces.append((i + b, i + a, i + 4 + a, i + 4 + b))
        for _ in range(6):
            self.fmats.append(self._mi(mat))

    def cilindro(self, cx, cy, z0, z1, r, mat, segs=8):
        i = len(self.verts)
        for z in (z0, z1):
            for s in range(segs):
                a = 2.0 * math.pi * s / segs
                self.verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
        for s in range(segs):
            s2 = (s + 1) % segs
            self.faces.append((i + s, i + s2, i + segs + s2, i + segs + s))
            self.fmats.append(self._mi(mat))
        # tapas (fan como ngon)
        self.faces.append(tuple(i + s for s in reversed(range(segs))))
        self.fmats.append(self._mi(mat))
        self.faces.append(tuple(i + segs + s for s in range(segs)))
        self.fmats.append(self._mi(mat))

    def to_object(self, name, parent_collection):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, [], self.faces)
        for mat in self.mats:
            mesh.materials.append(mat)
        for poly, mi in zip(mesh.polygons, self.fmats):
            poly.material_index = mi
        mesh.validate()
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        parent_collection.objects.link(obj)
        return obj


# ---------------------------------------------------------------------------
# Sub-piezas
# ---------------------------------------------------------------------------

def _ventana(mb, wx, z0, w=1.0, h=1.5, persianas=True):
    """Ventana con marco de piedra, vidrio y persianas verdes abiertas."""
    piedra = _get_mat("MAT_CASAS_piedra", COL_PIEDRA, rough=0.9)
    vidrio = _get_mat("MAT_CASAS_vidrio", COL_VIDRIO, rough=0.15)
    verde = _get_mat("MAT_CASAS_persiana", COL_PERSIANA, rough=0.7)
    hw = w / 2.0
    # marco
    mb.box(wx - hw - 0.09, wx + hw + 0.09, 0.0, 0.055, z0 - 0.08, z0 + h + 0.08, piedra)
    # vidrio
    mb.box(wx - hw, wx + hw, 0.0, 0.075, z0, z0 + h, vidrio)
    if persianas:
        for lado in (-1, 1):
            sx = wx + lado * (hw + 0.09 + 0.26)
            mb.box(sx - 0.24, sx + 0.24, 0.0, 0.09, z0, z0 + h, verde)


def _ventana_lateral(mb, x_pared, wy, z0, lado, w=1.0, h=1.5):
    """Ventana en un muro lateral (plano x = x_pared, mirando a lado*X)."""
    piedra = _get_mat("MAT_CASAS_piedra", COL_PIEDRA, rough=0.9)
    vidrio = _get_mat("MAT_CASAS_vidrio", COL_VIDRIO, rough=0.15)
    hw = w / 2.0
    xa, xb = sorted((x_pared, x_pared + lado * 0.055))
    mb.box(xa, xb, wy - hw - 0.09, wy + hw + 0.09, z0 - 0.08, z0 + h + 0.08, piedra)
    xa, xb = sorted((x_pared, x_pared + lado * 0.075))
    mb.box(xa, xb, wy - hw, wy + hw, z0, z0 + h, vidrio)


def _ventana_trasera(mb, wx, y_pared, z0, w=1.0, h=1.5):
    """Ventana en el muro trasero (plano y = y_pared, mirando a -Y)."""
    piedra = _get_mat("MAT_CASAS_piedra", COL_PIEDRA, rough=0.9)
    vidrio = _get_mat("MAT_CASAS_vidrio", COL_VIDRIO, rough=0.15)
    hw = w / 2.0
    mb.box(wx - hw - 0.09, wx + hw + 0.09, y_pared - 0.055, y_pared, z0 - 0.08, z0 + h + 0.08, piedra)
    mb.box(wx - hw, wx + hw, y_pared - 0.075, y_pared, z0, z0 + h, vidrio)


def _balcon(mb, wx, z_piso, w=2.0, fondo=0.62):
    """Balcón sencillo de forja: losa de piedra + barandilla de barrotes."""
    piedra = _get_mat("MAT_CASAS_piedra", COL_PIEDRA, rough=0.9)
    forja = _get_mat("MAT_CASAS_forja", COL_FORJA, rough=0.5, metallic=0.6)
    hw = w / 2.0
    z_losa = z_piso + 0.14
    mb.box(wx - hw, wx + hw, 0.0, fondo, z_piso - 0.06, z_losa, piedra)
    z_top = z_losa + 0.95
    g = 0.032  # medio grosor de barrote
    # pasamanos frontal y laterales
    mb.box(wx - hw, wx + hw, fondo - 2 * g, fondo, z_top - 0.05, z_top, forja)
    for lado in (-1, 1):
        sx = wx + lado * (hw - g)
        mb.box(sx - g, sx + g, 0.0, fondo, z_top - 0.05, z_top, forja)
        # barrote vertical de esquina
        mb.box(sx - g, sx + g, fondo - 2 * g, fondo, z_losa, z_top, forja)
    # barrotes frontales
    nb = max(4, int(w / 0.3))
    for i in range(nb + 1):
        bx = wx - hw + (w * i / nb)
        mb.box(bx - g, bx + g, fondo - 2 * g, fondo, z_losa, z_top - 0.05, forja)


def _toldo(mb, cx, w, z_alto, color_key, rng):
    """Toldo a rayas (blanco + color) sobre un escaparate, con faldón."""
    blanco = _get_mat("MAT_CASAS_toldo_blanco", COL_TOLDO_BLANCO, rough=0.9)
    col = _get_mat("MAT_CASAS_toldo_" + color_key, COLS_TOLDO[color_key], rough=0.9)
    n = max(3, int(round(w / 0.6)))
    if n % 2 == 0:
        n += 1
    x0 = cx - w / 2.0
    dx = w / n
    y_out, z_out = 1.05, z_alto - 0.58
    for i in range(n):
        mat = blanco if i % 2 == 0 else col
        xa, xb = x0 + i * dx, x0 + (i + 1) * dx
        # plano inclinado
        mb.quad((xa, 0.0, z_alto), (xb, 0.0, z_alto),
                (xb, y_out, z_out), (xa, y_out, z_out), mat)
        # faldón frontal
        mb.quad((xa, y_out, z_out), (xb, y_out, z_out),
                (xb, y_out, z_out - 0.22), (xa, y_out, z_out - 0.22), mat)


def _chimenea_escape(mb, cx, cy, z_base, alto=1.5):
    """Chimenea con forma de tubo de escape: tubo + aro cromado (firma)."""
    metal = _get_mat("MAT_CASAS_metal", COL_METAL, rough=0.45, metallic=0.8)
    cromo = _get_mat("MAT_CASAS_cromo", COL_CROMO, rough=0.2, metallic=1.0)
    mb.cilindro(cx, cy, z_base, z_base + alto, 0.19, metal, segs=8)
    mb.cilindro(cx, cy, z_base + alto - 0.55, z_base + alto + 0.10, 0.30,
                cromo, segs=8)


# ---------------------------------------------------------------------------
# Piezas del kit
# ---------------------------------------------------------------------------

def build_casa(parent_collection, plantas=4, ancho=10.0, fondo=12.0,
               color=None, seed=0, tejado="auto", name=None, **params):
    """Casa de estuco. Pivote en el centro de la fachada (y=0, mirando +Y)."""
    rng = random.Random(seed)
    if color is None:
        color_key = rng.choice(list(PALETA_FACHADA.keys()))
        color = PALETA_FACHADA[color_key]
    else:
        color_key = "custom_%02x%02x%02x" % tuple(
            min(255, max(0, int(c * 255))) for c in color)
    if tejado == "auto":
        tejado = "dosaguas" if rng.random() < 0.72 else "plano"

    estuco = _get_mat("MAT_CASAS_fachada_" + color_key, color, rough=0.9)
    piedra = _get_mat("MAT_CASAS_piedra", COL_PIEDRA, rough=0.9)
    teja = _get_mat("MAT_CASAS_teja", COL_TEJA, rough=0.85)
    madera = _get_mat("MAT_CASAS_madera", COL_MADERA, rough=0.7)
    vidrio = _get_mat("MAT_CASAS_vidrio", COL_VIDRIO, rough=0.15)

    mb = _MB()
    hx = ancho / 2.0
    h_baja = 3.8
    h_planta = 3.0
    h_muro = h_baja + (plantas - 1) * h_planta

    # cuerpo
    mb.box(-hx, hx, -fondo, 0.0, 0.0, h_muro, estuco)
    # zócalo de piedra en la base de la fachada
    mb.box(-hx, hx, 0.0, 0.06, 0.0, 0.55, piedra)
    # pilastras de esquina (quoins simplificados)
    for lado in (-1, 1):
        px = lado * (hx - 0.22)
        mb.box(px - 0.22, px + 0.22, 0.0, 0.07, 0.0, h_muro, piedra)
    # líneas de forjado entre plantas
    for p in range(1, plantas):
        z = h_baja + (p - 1) * h_planta
        mb.box(-hx, hx, 0.0, 0.05, z - 0.09, z + 0.05, piedra)
    # cornisa superior
    mb.box(-hx - 0.28, hx + 0.28, -fondo - 0.28, 0.28, h_muro, h_muro + 0.32, piedra)

    # --- ventanas de plantas altas, balcones ---
    ncols = max(2, int(round(ancho / 3.1)))
    paso = (ancho - 1.4) / ncols
    xs = [-(ancho - 1.4) / 2.0 + paso * (i + 0.5) for i in range(ncols)]
    for p in range(1, plantas):
        z_piso = h_baja + (p - 1) * h_planta
        z_v = z_piso + 0.75
        col_balcon = rng.randrange(ncols) if rng.random() < 0.75 else -1
        for ci, wx in enumerate(xs):
            _ventana(mb, wx, z_v)
            if ci == col_balcon:
                _balcon(mb, wx, z_piso)

    # --- ventanas en LATERALES expuestos y TRASERA (sin paredones ciegos) ---
    laterales = params.get('laterales', (True, True))
    n_lat = max(1, int(round(fondo / 4.5)))
    paso_l = (fondo - 2.0) / n_lat
    ys_l = [-(1.0 + paso_l * (i + 0.5)) for i in range(n_lat)]
    for p in range(0, plantas):
        z_v = (h_baja + (p - 1) * h_planta + 0.75) if p >= 1 else 1.25
        for k_l, lado in enumerate((-1, 1)):
            if laterales[k_l]:
                for wy in ys_l:
                    _ventana_lateral(mb, lado * hx, wy, z_v, lado)
        for wx in xs:
            _ventana_trasera(mb, wx, -fondo, z_v)

    # --- planta baja: puerta + escaparate + toldo ---
    if ncols >= 2:
        puerta_x = xs[0] if rng.random() < 0.5 else xs[-1]
        tienda_xs = [x for x in xs if x != puerta_x]
    else:
        puerta_x, tienda_xs = xs[0], []
    # puerta (a escala coche: ancha, con arco fingido y marco)
    pw = min(2.6, paso - 0.5)
    mb.box(puerta_x - pw / 2 - 0.12, puerta_x + pw / 2 + 0.12, 0.0, 0.06,
           0.0, 3.05, piedra)
    mb.box(puerta_x - pw / 2, puerta_x + pw / 2, 0.0, 0.075, 0.0, 2.9, madera)
    # escaparates con toldo opcional
    toldo_key = rng.choice(list(COLS_TOLDO.keys()))
    for tx in tienda_xs:
        ew = min(2.6, paso - 0.6)
        mb.box(tx - ew / 2 - 0.10, tx + ew / 2 + 0.10, 0.0, 0.055, 0.35, 2.75, madera)
        mb.box(tx - ew / 2, tx + ew / 2, 0.0, 0.07, 0.5, 2.6, vidrio)
        if rng.random() < 0.7:
            _toldo(mb, tx, ew + 0.7, 3.1, toldo_key, rng)

    # --- tejado ---
    ov = 0.4          # vuelo del alero
    z_alero = h_muro + 0.32
    if tejado == "dosaguas":
        alza = max(2.0, min(3.1, fondo * 0.25))
        z_cima = z_alero + alza
        y_c = -fondo / 2.0
        esp = 0.14
        # faldón delantero y trasero (placas con espesor)
        mb.prisma([(-hx - ov, ov, z_alero), (hx + ov, ov, z_alero),
                   (hx + ov, y_c, z_cima), (-hx - ov, y_c, z_cima)], esp, teja)
        mb.prisma([(hx + ov, -fondo - ov, z_alero), (-hx - ov, -fondo - ov, z_alero),
                   (-hx - ov, y_c, z_cima), (hx + ov, y_c, z_cima)], esp, teja)
        # caballete
        mb.box(-hx - ov, hx + ov, y_c - 0.16, y_c + 0.16, z_cima - 0.06,
               z_cima + 0.10, teja)
        # hastiales (triángulos de estuco en los laterales)
        for lado in (-1, 1):
            x = lado * hx
            if lado == 1:
                mb.tri((x, 0.0, z_alero - 0.32), (x, -fondo, z_alero - 0.32),
                       (x, y_c, z_cima), estuco)
            else:
                mb.tri((x, -fondo, z_alero - 0.32), (x, 0.0, z_alero - 0.32),
                       (x, y_c, z_cima), estuco)
        z_chim = z_alero + alza * 0.45
        chim_y = y_c + fondo * 0.16
    else:
        # plano: terraza con peto
        mb.box(-hx, hx, -fondo, 0.0, z_alero, z_alero + 0.06, piedra)
        g = 0.16
        for a, b, c, d in ((-hx, hx, -g * 2, 0.0), (-hx, hx, -fondo, -fondo + g * 2)):
            mb.box(a, b, c, d, z_alero, z_alero + 0.55, estuco)
        for lado in (-1, 1):
            x = lado * hx
            mb.box(x - g, x + g, -fondo, 0.0, z_alero, z_alero + 0.55, estuco)
        z_chim = z_alero
        chim_y = -fondo * 0.5

    # --- chimeneas tubo de escape (detalle firma) ---
    n_chim = rng.randint(1, 2)
    for i in range(n_chim):
        cx = rng.uniform(-hx * 0.6, hx * 0.6)
        cy = chim_y + (i - 0.5) * fondo * 0.18
        _chimenea_escape(mb, cx, cy, z_chim - 0.1, alto=rng.uniform(1.3, 1.8))

    obj = mb.to_object(name or "CASA_casa", parent_collection)
    return obj


def build_manzana(parent_collection, n=6, seed=0, **params):
    """Hilera de n casas pegadas, paleta variada, centrada en x=0."""
    rng = random.Random(seed)
    root = bpy.data.objects.new("CASAS_manzana", None)
    root.empty_display_size = 2.0
    parent_collection.objects.link(root)

    keys = list(PALETA_FACHADA.keys())
    anchos = [round(rng.uniform(8.0, 12.0) * 2) / 2 for _ in range(n)]
    total = sum(anchos)
    x = -total / 2.0
    prev_key = None
    for i in range(n):
        key = rng.choice([k for k in keys if k != prev_key])
        prev_key = key
        plantas = rng.randint(3, 6)
        fondo = round(rng.uniform(10.0, 13.0), 1)
        casa = build_casa(
            parent_collection,
            plantas=plantas,
            ancho=anchos[i],
            fondo=fondo,
            color=PALETA_FACHADA[key],
            seed=rng.randint(0, 999999),
            name="CASA_%02d" % i,
            laterales=(i == 0, i == n - 1),
        )
        casa.location = (x + anchos[i] / 2.0, 0.0, 0.0)
        casa.parent = root
        casa.matrix_parent_inverse = root.matrix_world.inverted()
        x += anchos[i]
    return root


def build(parent_collection, seed=0, **params):
    """Asset por defecto: manzana de 6 casas."""
    return build_manzana(parent_collection, n=params.pop("n", 6), seed=seed,
                         **params)
