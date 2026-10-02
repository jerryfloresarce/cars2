"""casas_kit_v2.py - Kit modular de manzanas estilo Portofino/Vernazza (Porto Corsa, Cars 2).

V2 = AUDITORIA DE VENTANAS del kit original (casas_kit.py). Misma API publica,
mismos nombres de objetos y materiales, mismo pivote; lo que cambia:

  * TODAS las caras miran hacia fuera (cada cara se orienta con un "hint"): con
    backface culling (Assetto Corsa) la v1 se veia llena de agujeros.
  * HUECOS REALES EN EL MURO. Los muros expuestos ya no son un quad continuo con
    la carpinteria superpuesta a 3-9 cm (parpadeaba en el z-buffer a partir de
    ~400 m): cada pano se tesela alrededor de ventanas, porton y escaparates, y
    tampoco hay muro detras del zocalo, las bandas de forjado, las pilastras ni
    la cornisa. El vidrio y la hoja del porton quedan REHUNDIDOS 6 cm dentro
    del muro, con mochetas; la cruceta / montante es coplanar con el vidrio
    (rejilla sin solapes) y las contraventanas abiertas ocupan su propio hueco.
    No queda ningun plano de estuco detras de otro material. Los panos se
    solapan 1 cm entre si (mismo material, mismo plano: invisible) y entran
    1 cm por detras de marcos / bandas / pilastras para que las juntas en T no
    dejen pixeles abiertos.
  * params['lod']=1: fachada LEJANA sin relieves (celdas planas de vidrio y
    contraventana dentro de la rejilla del muro, sin marcos, bandas, barandillas
    ni oculos; ~600-1100 tris) para casas lejos de la pista.
  * Ventanas con marco de piedra EN ANILLO, vidrio rehundido y contraventanas
    verdes en las CUATRO fachadas. Contraventanas cerradas: muestreo sin
    reemplazo con tope por muro (max(1, n//6)), como mucho una por planta y
    nunca en diagonal/vertical contigua (antes podia salir un damero).
  * Laterales y trasera con el MISMO ritmo vertical que el frente; planta baja
    lateral/trasera con el alfeizar a 1.55 m (no queda enterrada en ladera).
  * Zocalo de piedra de 1 m, bandas de forjado y cornisa de dos escalones en
    TODO el perimetro; pilastras de esquina en L (0.32 m) en las 4 esquinas.
  * Hueco de balcon = puerta-ventana hasta la losa, balcon sobre mensulas.
  * Planta baja alineada: cabeza del marco del escaparate = dintel del porton
    (3.06 m); toldos (ancho escaparate + 0.3) con grosor, sin pisarse ni pisar
    el porton.
  * Hastial ajustado a la cara inferior del tejado + oculo de piedra (tambien
    con hueco real) en los hastiales expuestos.
  * Tejado plano: peto de 0.9 m con albardilla en los cuatro lados y suelo de
    terraza propio (MAT_CASAS_terraza, baldosa calida) en vez de la tapa blanca
    de la cornisa.
  * Chimeneas (tubo de escape, detalle firma) apoyadas a la cota REAL del faldon.
  * En una medianera (lateral no expuesto) ni el tejado ni la cornisa vuelan
    sobre el vecino.
  * PRESUPUESTO GARANTIZADO: build_casa cuenta los triangulos y, si pasa de
    4950, degrada por pasos (montante -> vidrio liso -> ventanas planas en
    laterales/trasera -> en todo) hasta quedar <= 5000 con cualquier tamano.

Piezas del kit (todas linkan a `parent_collection` y devuelven el objeto raiz):
  build_casa(parent_collection, plantas=4, ancho=10, fondo=12,
             color=None, seed=0, tejado='auto', name=None, **params)
      Una casa (malla unica). Pivote en el CENTRO DE LA FACHADA (x=0), fachada
      en el plano y=0 mirando a +Y, cuerpo hacia -Y, base en z=0. <=5k tris.
      tejado: 'auto' | 'dosaguas' | 'plano'.
      params['laterales'] = (izq_-X, der_+X): que muros laterales estan
          expuestos (ventanas, zocalo, pilastras...). Por defecto (True, True).
          Un lateral no expuesto (medianera) queda liso (un solo quad).
      params['lod'] = 0 (por defecto, detalle completo) | 1 (fachada lejana).
      params['auditoria'] = lista que se rellena con los rectangulos de cada
          elemento de fachada (solo para el test; no afecta a la geometria).
  build_manzana(parent_collection, n=6, seed=0, **params)
      Hilera de n casas pegadas (alturas 3-6 plantas, paleta variada),
      centrada en x=0, fachadas alineadas en y=0. Devuelve un Empty raiz;
      cada casa conserva su pivote de fachada para poder pegarse en curva.
      params['lod'] se pasa a cada casa.
  build(parent_collection, seed=0, **params)
      = build_manzana de 6 casas.

Unidades: metros. Materiales: Principled BSDF de color plano, reutilizados
(mismos nombres MAT_CASAS_* que la v1 + MAT_CASAS_carpinteria y
MAT_CASAS_terraza).
"""

import math
import random

import bpy

# ---------------------------------------------------------------------------
# Paleta (Cars 2: saturado y limpio). Definida en sRGB y convertida a lineal
# para que el render conserve la saturacion de la pelicula.
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
# piedra algo mas calida y menos blanca que en la v1: en la pelicula el
# recercado apenas destaca sobre el estuco
COL_PIEDRA = _srgb(0.91, 0.85, 0.72)
COL_FORJA = (0.02, 0.02, 0.025)
COL_VIDRIO = _srgb(0.22, 0.34, 0.38)
COL_MADERA = _srgb(0.42, 0.24, 0.11)
COL_METAL = _srgb(0.52, 0.53, 0.55)
COL_CROMO = _srgb(0.85, 0.87, 0.90)
COL_CARPINTERIA = _srgb(0.93, 0.90, 0.80)
COL_TERRAZA = _srgb(0.66, 0.50, 0.40)
COL_TOLDO_BLANCO = _srgb(0.95, 0.93, 0.88)
COLS_TOLDO = {
    "rojo": _srgb(0.80, 0.16, 0.12),
    "verde": _srgb(0.16, 0.48, 0.22),
    "azul": _srgb(0.16, 0.32, 0.62),
}

# cotas comunes a las cuatro fachadas
H_BAJA = 3.8            # altura de la planta baja
H_PLANTA = 3.0          # altura de cada planta alta
ALFEIZAR = 0.75         # alfeizar de las ventanas de planta alta sobre su forjado
H_VENTANA = 1.5
ALFEIZAR_BAJA = 1.55    # ventanas de planta baja (laterales y trasera)
H_VENTANA_BAJA = 1.45
H_ZOCALO = 1.0
MARCO = 0.10            # ancho del marco de piedra
H_PUERTA = 2.9          # luz del porton (escala coche)
H_DINTEL = 0.16
Z_ESCAPARATE = H_PUERTA + H_DINTEL - MARCO   # cabeza del marco = dintel del porton
Z_TOLDO = 3.20
# Profundidades respecto al plano del muro (d > 0 hacia fuera, d < 0 DENTRO del
# muro). Detras de cada elemento NO hay muro: el pano tiene un hueco real.
D_MARCO = 0.09          # relieve del marco sobre el muro
D_VIDRIO = -0.06        # vidrio / hoja de porton rehundidos dentro del muro
D_HOJA = 0.03           # contraventana cerrada, dentro del marco
D_PERSIANA = 0.07       # grosor de la contraventana abierta
D_LOD = -0.01           # celdas planas de la fachada lejana (lod=1)
D_ZOCALO = 0.12
D_PILASTRA = 0.10
A_PILASTRA = 0.32
D_BANDA = 0.06
SOLAPE = 0.01           # solape entre panos / entrada por detras de los recercados

MAX_TRIS = 5000
TRIS_OBJETIVO = 4950
# carpinteria (frente, resto) por nivel de degradacion del presupuesto
#   cruz     = rejilla 3x3 coplanar (4 vidrios + cruceta)        18 tris
#   montante = 2 vidrios + montante vertical, coplanares           6 tris
#   lisa     = vidrio liso                                         2 tris
#   sinmarco = vidrio liso rehundido con mochetas de estuco, sin marco de
#              piedra (30 tris por ventana en vez de 42)
#   plano    = ventana plana sin relieve (como lod=1)              6 tris en total
NIVELES = (("cruz", "montante"), ("cruz", "lisa"), ("montante", "lisa"),
           ("lisa", "lisa"), ("lisa", "sinmarco"), ("sinmarco", "sinmarco"),
           ("lisa", "plano"), ("plano", "plano"))


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


def _materiales(color_key, color):
    return {
        "estuco": _get_mat("MAT_CASAS_fachada_" + color_key, color, rough=0.9),
        "piedra": _get_mat("MAT_CASAS_piedra", COL_PIEDRA, rough=0.9),
        "teja": _get_mat("MAT_CASAS_teja", COL_TEJA, rough=0.85),
        "madera": _get_mat("MAT_CASAS_madera", COL_MADERA, rough=0.7),
        "vidrio": _get_mat("MAT_CASAS_vidrio", COL_VIDRIO, rough=0.15),
        "persiana": _get_mat("MAT_CASAS_persiana", COL_PERSIANA, rough=0.7),
        "forja": _get_mat("MAT_CASAS_forja", COL_FORJA, rough=0.5, metallic=0.6),
        "metal": _get_mat("MAT_CASAS_metal", COL_METAL, rough=0.45, metallic=0.8),
        "cromo": _get_mat("MAT_CASAS_cromo", COL_CROMO, rough=0.2, metallic=1.0),
        "carpinteria": _get_mat("MAT_CASAS_carpinteria", COL_CARPINTERIA, rough=0.6),
        "terraza": _get_mat("MAT_CASAS_terraza", COL_TERRAZA, rough=0.9),
        "toldo_blanco": _get_mat("MAT_CASAS_toldo_blanco", COL_TOLDO_BLANCO, rough=0.9),
    }


# ---------------------------------------------------------------------------
# Constructor de mallas por acumulacion (from_pydata, sin bpy.ops).
# Cada cara se orienta con un "hint": vector hacia el EXTERIOR del solido.
# ---------------------------------------------------------------------------

def _newell(pts):
    nx = ny = nz = 0.0
    n = len(pts)
    for k in range(n):
        x0, y0, z0 = pts[k]
        x1, y1, z1 = pts[(k + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return nx, ny, nz


class _MB:
    """Acumula caras con indice de material; winding garantizado por hint."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.fmats = []
        self.mats = []          # lista ordenada de materiales
        self._mat_idx = {}

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def _mi(self, mat):
        if mat.name not in self._mat_idx:
            self._mat_idx[mat.name] = len(self.mats)
            self.mats.append(mat)
        return self._mat_idx[mat.name]

    def cara(self, pts, mat, hint):
        """Poligono plano cuya normal mira hacia `hint`."""
        n = _newell(pts)
        if n[0] * hint[0] + n[1] * hint[1] + n[2] * hint[2] < 0.0:
            pts = pts[::-1]
        i = len(self.verts)
        self.verts.extend(pts)
        self.faces.append(tuple(range(i, i + len(pts))))
        self.fmats.append(self._mi(mat))

    def box(self, x0, x1, y0, y1, z0, z1, mat, omit=""):
        """Caja alineada a ejes. omit: letras de caras a NO generar
        ('x' = cara -X, 'X' = +X, 'y', 'Y', 'z' = inferior, 'Z' = superior)."""
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        if z0 > z1:
            z0, z1 = z1, z0
        if "x" not in omit:
            self.cara([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], mat, (-1, 0, 0))
        if "X" not in omit:
            self.cara([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], mat, (1, 0, 0))
        if "y" not in omit:
            self.cara([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], mat, (0, -1, 0))
        if "Y" not in omit:
            self.cara([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], mat, (0, 1, 0))
        if "z" not in omit:
            self.cara([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], mat, (0, 0, -1))
        if "Z" not in omit:
            self.cara([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], mat, (0, 0, 1))

    def pbox(self, pa, a0, a1, d0, d1, z0, z1, mat, omit="b"):
        """Caja en coordenadas de muro (a, d, z). omit: 'f' frente (d1),
        'b' trasera (d0, pegada al muro), 'l' (a0), 'r' (a1), 't' tapa, 'u' base."""
        P, n, u = pa.P, pa.n3, pa.u3
        nn = (-n[0], -n[1], 0.0)
        nu = (-u[0], -u[1], 0.0)
        if "f" not in omit:
            self.cara([P(a0, d1, z0), P(a1, d1, z0), P(a1, d1, z1), P(a0, d1, z1)], mat, n)
        if "b" not in omit:
            self.cara([P(a0, d0, z0), P(a1, d0, z0), P(a1, d0, z1), P(a0, d0, z1)], mat, nn)
        if "l" not in omit:
            self.cara([P(a0, d0, z0), P(a0, d1, z0), P(a0, d1, z1), P(a0, d0, z1)], mat, nu)
        if "r" not in omit:
            self.cara([P(a1, d0, z0), P(a1, d1, z0), P(a1, d1, z1), P(a1, d0, z1)], mat, u)
        if "t" not in omit:
            self.cara([P(a0, d0, z1), P(a1, d0, z1), P(a1, d1, z1), P(a0, d1, z1)], mat, (0, 0, 1))
        if "u" not in omit:
            self.cara([P(a0, d0, z0), P(a1, d0, z0), P(a1, d1, z0), P(a0, d1, z0)], mat, (0, 0, -1))

    def cilindro(self, cx, cy, z0, z1, r, mat, segs=8, base=True, tapa=True, mat_tapa=None):
        i = len(self.verts)
        for z in (z0, z1):
            for s in range(segs):
                a = 2.0 * math.pi * s / segs
                self.verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
        for s in range(segs):
            s2 = (s + 1) % segs
            self.faces.append((i + s, i + s2, i + segs + s2, i + segs + s))
            self.fmats.append(self._mi(mat))
        if base:        # mira a -Z
            self.faces.append(tuple(i + s for s in reversed(range(segs))))
            self.fmats.append(self._mi(mat))
        if tapa:        # mira a +Z
            self.faces.append(tuple(i + segs + s for s in range(segs)))
            self.fmats.append(self._mi(mat_tapa or mat))

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


class _Pared:
    """Coordenadas locales de un muro: a = horizontal a lo largo del muro
    (0 en su centro), d = distancia hacia FUERA, z = altura."""

    def __init__(self, nombre, ox, oy, nx, ny, largo):
        self.nombre = nombre
        self.ox, self.oy = ox, oy
        self.n3 = (float(nx), float(ny), 0.0)
        self.u3 = (-float(ny), float(nx), 0.0)
        self.largo = largo

    def P(self, a, d, z):
        return (self.ox + self.u3[0] * a + self.n3[0] * d,
                self.oy + self.u3[1] * a + self.n3[1] * d, z)


def _reg(aud, pared, tipo, a0, a1, z0, z1, **extra):
    if aud is None:
        return
    r = {"pared": pared, "tipo": tipo, "a0": min(a0, a1), "a1": max(a0, a1),
         "z0": min(z0, z1), "z1": max(z0, z1)}
    r.update(extra)
    aud.append(r)


def _columnas(largo, paso_min):
    """Centros (coordenada a) de las columnas de huecos de un muro y su paso.
    Deja 0.70 m a cada extremo (pilastra + respiro)."""
    util = largo - 1.4
    n = int(util / paso_min + 1e-9)
    if n < 2 and util / 2.0 >= 2.3:
        n = 2
    n = max(1, n)
    paso = util / n
    return [-util / 2.0 + paso * (i + 0.5) for i in range(n)], paso


# ---------------------------------------------------------------------------
# Sub-piezas (todas en coordenadas de muro: valen para las 4 fachadas).
# Cada una anota en `huecos` el rectangulo (a0, a1, z0, z1) que ocupa: el muro
# se tesela despues alrededor de esos rectangulos (no queda estuco detras).
# ---------------------------------------------------------------------------

def _plano(mb, pa, a0, a1, z0, z1, d, mat):
    P = pa.P
    mb.cara([P(a0, d, z0), P(a1, d, z0), P(a1, d, z1), P(a0, d, z1)], mat, pa.n3)


def _rejilla(mb, pa, cols, filas, d, mats):
    """Celdas coplanares SIN solapes ni juntas en T: cols/filas son las cotas
    de la rejilla y mats[fila][col] el material de cada celda."""
    for k in range(len(filas) - 1):
        for i in range(len(cols) - 1):
            _plano(mb, pa, cols[i], cols[i + 1], filas[k], filas[k + 1], d, mats[k][i])


def _muro(mb, pa, a_lo, a_hi, z_lo, z_hi, huecos, cortes, mat):
    """Pano de muro (d=0) con HUECOS REALES. `huecos` = rectangulos ocupados por
    ventanas/porton/escaparates; `cortes` = franjas (z0, z1) a todo lo ancho
    ocupadas por las bandas de forjado. Por fuera de [a_lo, a_hi] x [z_lo, z_hi]
    estan las pilastras, el zocalo y la cornisa.
    Teselado por filas de huecos: tiras horizontales completas entre filas y
    machones entre huecos. Las piezas se solapan SOLAPE entre si (mismo
    material y plano: invisible) y entran SOLAPE por detras de los recercados,
    asi ninguna junta en T queda abierta."""
    o = SOLAPE
    P, n = pa.P, pa.n3

    def quad(a0, a1, z0, z1):
        if a1 - a0 > 1e-4 and z1 - z0 > 1e-4:
            mb.cara([P(a0, 0.0, z0), P(a1, 0.0, z0), P(a1, 0.0, z1), P(a0, 0.0, z1)], mat, n)

    hs = []
    for (a0, a1, z0, z1) in huecos:
        a0, a1 = max(a0, a_lo), min(a1, a_hi)
        z0, z1 = max(z0, z_lo), min(z1, z_hi)
        if a1 - a0 > 1e-4 and z1 - z0 > 1e-4:
            hs.append((a0, a1, z0, z1))
    hs.sort(key=lambda h: (h[2], h[0]))
    filas = []                      # [z0, z1, [huecos]]
    for h in hs:
        if filas and h[2] < filas[-1][1] - 1e-4:
            filas[-1][1] = max(filas[-1][1], h[3])
            filas[-1][2].append(h)
        else:
            filas.append([h[2], h[3], [h]])
    cortes = sorted(cortes)

    # tiras completas entre filas (partidas por las bandas de forjado)
    cur = z_lo
    for (r0, r1) in [(f[0], f[1]) for f in filas] + [(z_hi, z_hi)]:
        s0 = cur
        for (c0, c1) in cortes:
            if c1 <= s0 or c0 >= r0:
                continue
            if c0 - s0 > 1e-4:
                quad(a_lo - o, a_hi + o, s0 - o, c0 + o)
            s0 = max(s0, c1)
        if r0 - s0 > 1e-4:
            quad(a_lo - o, a_hi + o, s0 - o, r0 + o)
        cur = max(cur, r1)

    # machones entre huecos + antepechos / dinteles de los huecos mas cortos
    for (r0, r1, lista) in filas:
        lista.sort()
        a = a_lo - o
        for (h0, h1, hz0, hz1) in lista:
            quad(a, h0 + o, r0 - o, r1 + o)
            if hz0 - r0 > 1e-4:
                quad(h0 - o, h1 + o, r0 - o, hz0 + o)
            if r1 - hz1 > 1e-4:
                quad(h0 - o, h1 + o, hz1 - o, r1 + o)
            a = h1 - o
        quad(a, a_hi + o, r0 - o, r1 + o)


def _marco(mb, pa, a0, a1, z0, z1, m, df, dg, mat):
    """Marco en anillo alrededor de la luz [a0,a1]x[z0,z1]: frente, cantos
    exteriores (del plano del muro al frente) y mochetas interiores hasta 1 cm
    por detras del plano del vidrio (dg)."""
    P, n, u = pa.P, pa.n3, pa.u3
    nu = (-u[0], -u[1], 0.0)
    A0, A1, Z0, Z1 = a0 - m, a1 + m, z0 - m, z1 + m
    db = dg - SOLAPE
    # frente (4 trapecios a inglete)
    mb.cara([P(A0, df, Z0), P(A1, df, Z0), P(a1, df, z0), P(a0, df, z0)], mat, n)
    mb.cara([P(A1, df, Z0), P(A1, df, Z1), P(a1, df, z1), P(a1, df, z0)], mat, n)
    mb.cara([P(A1, df, Z1), P(A0, df, Z1), P(a0, df, z1), P(a1, df, z1)], mat, n)
    mb.cara([P(A0, df, Z1), P(A0, df, Z0), P(a0, df, z0), P(a0, df, z1)], mat, n)
    # cantos exteriores
    mb.cara([P(A0, 0, Z0), P(A1, 0, Z0), P(A1, df, Z0), P(A0, df, Z0)], mat, (0, 0, -1))
    mb.cara([P(A0, 0, Z1), P(A1, 0, Z1), P(A1, df, Z1), P(A0, df, Z1)], mat, (0, 0, 1))
    mb.cara([P(A0, 0, Z0), P(A0, 0, Z1), P(A0, df, Z1), P(A0, df, Z0)], mat, nu)
    mb.cara([P(A1, 0, Z0), P(A1, 0, Z1), P(A1, df, Z1), P(A1, df, Z0)], mat, u)
    # mochetas (miran hacia el centro del hueco)
    mb.cara([P(a0, db, z0), P(a1, db, z0), P(a1, df, z0), P(a0, df, z0)], mat, (0, 0, 1))
    mb.cara([P(a0, db, z1), P(a1, db, z1), P(a1, df, z1), P(a0, df, z1)], mat, (0, 0, -1))
    mb.cara([P(a0, db, z0), P(a0, db, z1), P(a0, df, z1), P(a0, df, z0)], mat, u)
    mb.cara([P(a1, db, z0), P(a1, db, z1), P(a1, df, z1), P(a1, df, z0)], mat, nu)


def _ventana(mb, pa, a, z0, h, M, aud, planta, huecos, w=1.0, modo="abierta",
             carp="cruz", grupo=None):
    """Ventana: marco de piedra en anillo + vidrio rehundido con carpinteria
    coplanar + contraventanas verdes. modo: 'abierta' (hojas abatidas a los
    lados, en su propio hueco del muro), 'cerrada' (hojas cerradas dentro del
    marco) o 'sin'. carp: 'cruz' | 'montante' | 'lisa' | 'plano' (sin relieve)."""
    hw = w / 2.0
    a0, a1, z1 = a - hw, a + hw, z0 + h
    vid, per = M["vidrio"], M["persiana"]

    if carp == "sinmarco":
        # nivel de presupuesto: hueco con mochetas de estuco, sin marco de piedra
        ext = hw + (hw if modo == "abierta" else 0.0)
        huecos.append((a - ext, a + ext, z0, z1))
        # (en el registro se anota con el mismo margen vertical que una ventana
        # con marco, para que la auditoria compare cotas homogeneas)
        _reg(aud, pa.nombre, "ventana", a - ext, a + ext, z0 - MARCO, z1 + MARCO,
             planta=planta, grupo=grupo, modo=modo)
        P, u = pa.P, pa.u3
        nu = (-u[0], -u[1], 0.0)
        dg = -0.02 if modo == "cerrada" else D_VIDRIO
        db, est = dg - SOLAPE, M["estuco"]
        mb.cara([P(a0, db, z0), P(a1, db, z0), P(a1, 0, z0), P(a0, 0, z0)], est, (0, 0, 1))
        mb.cara([P(a0, db, z1), P(a1, db, z1), P(a1, 0, z1), P(a0, 0, z1)], est, (0, 0, -1))
        mb.cara([P(a0, db, z0), P(a0, db, z1), P(a0, 0, z1), P(a0, 0, z0)], est, u)
        mb.cara([P(a1, db, z0), P(a1, db, z1), P(a1, 0, z1), P(a1, 0, z0)], est, nu)
        if modo == "cerrada":
            _rejilla(mb, pa, [a0, a - 0.02, a + 0.02, a1], [z0, z1], dg,
                     [[per, M["forja"], per]])
            return
        _plano(mb, pa, a0, a1, z0, z1, dg, vid)
        if modo == "abierta":
            mb.pbox(pa, a - ext, a0, 0.0, D_PERSIANA, z0, z1, per, omit="b")
            mb.pbox(pa, a1, a + ext, 0.0, D_PERSIANA, z0, z1, per, omit="b")
        return

    A0, A1, Z0, Z1 = a0 - MARCO, a1 + MARCO, z0 - MARCO, z1 + MARCO
    ext = hw + MARCO + (hw if modo == "abierta" else 0.0)
    huecos.append((a - ext, a + ext, Z0, Z1))
    _reg(aud, pa.nombre, "ventana", a - ext, a + ext, Z0, Z1,
         planta=planta, grupo=grupo, modo=modo)

    if carp == "plano":
        e = SOLAPE
        if modo == "cerrada":
            _plano(mb, pa, A0 - e, A1 + e, Z0 - e, Z1 + e, D_LOD, per)
        elif modo == "abierta":
            # el vidrio conserva su ancho real; las hojas absorben el del marco
            _rejilla(mb, pa, [a - ext - e, a0, a1, a + ext + e], [Z0 - e, Z1 + e], D_LOD,
                     [[per, vid, per]])
        else:
            _plano(mb, pa, A0 - e, A1 + e, Z0 - e, Z1 + e, D_LOD, vid)
        return

    if modo == "cerrada":
        _marco(mb, pa, a0, a1, z0, z1, MARCO, D_MARCO, D_HOJA, M["piedra"])
        _rejilla(mb, pa, [a0, a - 0.02, a + 0.02, a1], [z0, z1], D_HOJA,
                 [[per, M["forja"], per]])
        return

    _marco(mb, pa, a0, a1, z0, z1, MARCO, D_MARCO, D_VIDRIO, M["piedra"])
    car = M["carpinteria"]
    if carp == "cruz":
        zt = z0 + h * 0.64
        _rejilla(mb, pa, [a0, a - 0.03, a + 0.03, a1], [z0, zt - 0.025, zt + 0.025, z1],
                 D_VIDRIO, [[vid, car, vid], [car, car, car], [vid, car, vid]])
    elif carp == "montante":
        _rejilla(mb, pa, [a0, a - 0.03, a + 0.03, a1], [z0, z1], D_VIDRIO, [[vid, car, vid]])
    else:
        _plano(mb, pa, a0, a1, z0, z1, D_VIDRIO, vid)
    if modo == "abierta":
        # hojas de la misma altura que el marco: ventana + hojas = UN rectangulo
        # (5 mm mas cortas: su tapa muere contra el canto del marco y bajo el
        # solape del muro, no canto con canto)
        c = 0.005
        mb.pbox(pa, a - ext, A0, 0.0, D_PERSIANA, Z0 + c, Z1 - c, per, omit="br")
        mb.pbox(pa, A1, a + ext, 0.0, D_PERSIANA, Z0 + c, Z1 - c, per, omit="bl")


def _mensula(mb, pa, am, z_top, mat, ancho=0.16, vuelo=0.50, alto=0.38):
    """Mensula de piedra en cuna bajo la losa del balcon."""
    P, n, u = pa.P, pa.n3, pa.u3
    a0, a1 = am - ancho / 2.0, am + ancho / 2.0
    mb.cara([P(a0, 0, z_top), P(a0, vuelo, z_top), P(a0, 0, z_top - alto)], mat, (-u[0], -u[1], 0))
    mb.cara([P(a1, 0, z_top), P(a1, vuelo, z_top), P(a1, 0, z_top - alto)], mat, u)
    mb.cara([P(a0, 0, z_top - alto), P(a1, 0, z_top - alto), P(a1, vuelo, z_top), P(a0, vuelo, z_top)],
            mat, (n[0] * alto, n[1] * alto, -vuelo))


def _balcon(mb, pa, ac, z_piso, bw, M, aud, grupo, simple=False):
    """Balcon de forja: losa de piedra sobre mensulas + barandilla de barrotes."""
    piedra, forja = M["piedra"], M["forja"]
    vuelo = 0.70
    z0, z1 = z_piso - 0.06, z_piso + 0.14
    zt = z1 + 1.0
    mb.pbox(pa, ac - bw, ac + bw, 0.0, vuelo, z0, z1, piedra, omit="b")
    _reg(aud, pa.nombre, "balcon", ac - bw, ac + bw, z0 - 0.38, zt, grupo=grupo)
    if simple:
        return
    for s in (-1, 1):
        _mensula(mb, pa, ac + s * (bw - 0.32), z0, piedra)
    # pasamanos: frontal completo + dos laterales hasta el muro
    mb.pbox(pa, ac - bw, ac + bw, vuelo - 0.06, vuelo, zt - 0.05, zt, forja, omit="")
    mb.pbox(pa, ac - bw, ac - bw + 0.06, 0.0, vuelo - 0.06, zt - 0.05, zt, forja, omit="bf")
    mb.pbox(pa, ac + bw - 0.06, ac + bw, 0.0, vuelo - 0.06, zt - 0.05, zt, forja, omit="bf")
    # barrotes frontales (incluye los de esquina) y uno intermedio por lateral
    nb = max(4, int(round(2.0 * bw / 0.31)))
    g = 0.018
    for i in range(nb + 1):
        ab = ac - bw + 0.03 + (2.0 * bw - 0.06) * i / nb
        mb.pbox(pa, ab - g, ab + g, vuelo - 0.03 - g, vuelo - 0.03 + g, z1, zt - 0.05,
                forja, omit="tu")
    for s in (-1, 1):
        ab = ac + s * (bw - 0.03)
        mb.pbox(pa, ab - g, ab + g, 0.32 - g, 0.32 + g, z1, zt - 0.05, forja, omit="tu")


def _toldo(mb, pa, ac, w, z_alto, color_key, M, aud, simple=False):
    """Toldo a rayas (blanco + color) con grosor y faldon, sobre un escaparate."""
    blanco = M["toldo_blanco"]
    col = _get_mat("MAT_CASAS_toldo_" + color_key, COLS_TOLDO[color_key], rough=0.9)
    P, n, u = pa.P, pa.n3, pa.u3
    nn = (-n[0], -n[1], 0.0)
    nst = max(3, int(round(w / 0.6)))
    if nst % 2 == 0:
        nst += 1
    a0 = ac - w / 2.0
    da = w / nst
    d_out, caida, esp, falda = 1.0, 0.55, 0.04, 0.22
    z_out = z_alto - caida
    arriba = (n[0] * caida, n[1] * caida, d_out)
    abajo = (-arriba[0], -arriba[1], -arriba[2])
    for i in range(nst):
        mat = blanco if i % 2 == 0 else col
        aa, ab = a0 + i * da, a0 + (i + 1) * da
        mb.cara([P(aa, 0, z_alto), P(ab, 0, z_alto), P(ab, d_out, z_out), P(aa, d_out, z_out)],
                mat, arriba)
        mb.cara([P(aa, d_out, z_out), P(ab, d_out, z_out),
                 P(ab, d_out, z_out - falda), P(aa, d_out, z_out - falda)], mat, n)
        if simple:
            continue
        mb.cara([P(aa, 0, z_alto - esp), P(ab, 0, z_alto - esp),
                 P(ab, d_out - 0.03, z_out - esp), P(aa, d_out - 0.03, z_out - esp)], mat, abajo)
        mb.cara([P(aa, d_out - 0.03, z_out - esp), P(ab, d_out - 0.03, z_out - esp),
                 P(ab, d_out - 0.03, z_out - falda), P(aa, d_out - 0.03, z_out - falda)], mat, nn)
    if not simple:
        for ae, hint in ((a0, (-u[0], -u[1], 0.0)), (a0 + w, u)):
            mb.cara([P(ae, 0, z_alto), P(ae, d_out, z_out), P(ae, d_out, z_out - falda),
                     P(ae, d_out - 0.03, z_out - falda), P(ae, d_out - 0.03, z_out - esp),
                     P(ae, 0, z_alto - esp)], blanco, hint)
    _reg(aud, pa.nombre, "toldo", a0, a0 + w, z_out - falda, z_alto)


def _puerta(mb, pa, ac, pw, M, aud, huecos, simple=False):
    """Porton a escala coche: jambas y dintel de piedra con clave; hojas de
    madera REHUNDIDAS en el muro con junta central, travesano y montante
    acristalado (rejilla coplanar, sin planos superpuestos)."""
    piedra, mad, vid = M["piedra"], M["madera"], M["vidrio"]
    alto, j, dj = H_PUERTA, 0.14, 0.10
    top = alto + H_DINTEL
    a0, a1 = ac - pw / 2.0, ac + pw / 2.0
    huecos.append((a0 - j, a1 + j, 0.0, top))
    _reg(aud, pa.nombre, "puerta", a0 - j, a1 + j, 0.0, top)
    if simple:
        e = SOLAPE
        _rejilla(mb, pa, [a0 - j - e, a0, a1, a1 + j + e], [0.0, alto, top + e], D_LOD,
                 [[piedra, mad, piedra], [piedra, piedra, piedra]])
        return a0 - j, a1 + j
    dg = D_VIDRIO
    db = dg - SOLAPE
    mb.pbox(pa, a0 - j, a0, db, dj, 0.0, top, piedra, omit="bu")
    mb.pbox(pa, a1, a1 + j, db, dj, 0.0, top, piedra, omit="bu")
    # (el dintel entra 1 cm en cada jamba: frentes coplanares del mismo material
    # solapados, sin junta en T abierta)
    mb.pbox(pa, a0 - SOLAPE, a1 + SOLAPE, db, dj, alto, top, piedra, omit="blr")
    # clave: sobre el dintel (piedra sobre piedra), sin asomar por encima
    mb.pbox(pa, ac - 0.15, ac + 0.15, 0.0, 0.13, alto - 0.08, top, piedra, omit="b")
    _rejilla(mb, pa, [a0, ac - 0.025, ac + 0.025, a1], [0.0, 2.30, 2.42, alto], dg,
             [[mad, M["forja"], mad], [mad, mad, mad], [vid, mad, vid]])
    return a0 - j, a1 + j


def _escaparate(mb, pa, ac, ew, M, aud, huecos, simple=False):
    """Escaparate de madera apoyado SOBRE el zocalo; cabeza del marco a la
    altura del dintel del porton."""
    a0, a1 = ac - ew / 2.0, ac + ew / 2.0
    z0, z1 = H_ZOCALO + MARCO, Z_ESCAPARATE
    huecos.append((a0 - MARCO, a1 + MARCO, z0 - MARCO, z1 + MARCO))
    _reg(aud, pa.nombre, "escaparate", a0 - MARCO, a1 + MARCO, z0 - MARCO, z1 + MARCO)
    if simple:
        e = SOLAPE
        _plano(mb, pa, a0 - MARCO - e, a1 + MARCO + e, z0 - MARCO - e, z1 + MARCO + e,
               D_LOD, M["vidrio"])
        return
    _marco(mb, pa, a0, a1, z0, z1, MARCO, D_MARCO, D_VIDRIO, M["madera"])
    _rejilla(mb, pa, [a0, ac - 0.035, ac + 0.035, a1], [z0, z1], D_VIDRIO,
             [[M["vidrio"], M["madera"], M["vidrio"]]])


def _hastial(mb, pa, z_alero, zb_alero, zb_cima, M, aud, info, oculo, R=0.55, r=0.37):
    """Hastial (pentagono bajo el faldon) de un muro lateral. Con `oculo`, el
    estuco se tesela ALREDEDOR de un oculo octogonal de piedra con el vidrio
    rehundido (hueco real: 13 triangulos sin juntas en T)."""
    P, n, u = pa.P, pa.n3, pa.u3
    L2 = pa.largo / 2.0
    estuco = M["estuco"]
    BL, BR = (-L2, z_alero), (L2, z_alero)
    RE, AP, LE = (L2, zb_alero), (0.0, zb_cima), (-L2, zb_alero)
    if not oculo:
        mb.cara([P(a, 0.0, z) for (a, z) in (BL, BR, RE, AP, LE)], estuco, n)
        return
    zc = info["zc"]
    N = 8
    ang = [2.0 * math.pi * k / N + math.pi / N for k in range(N)]
    ext = [(R * math.cos(t), zc + R * math.sin(t)) for t in ang]
    inte = [(r * math.cos(t), zc + r * math.sin(t)) for t in ang]
    e = ext
    for tri in ((RE, AP, e[1]), (RE, e[1], e[0]), (RE, e[0], e[7]), (BR, RE, e[7]),
                (AP, e[2], e[1]),
                (AP, LE, e[2]), (LE, e[3], e[2]), (LE, e[4], e[3]), (LE, BL, e[4]),
                (BL, e[5], e[4]), (BL, BR, e[5]), (BR, e[6], e[5]), (BR, e[7], e[6])):
        mb.cara([P(a, 0.0, z) for (a, z) in tri], estuco, n)
    df, dg = D_MARCO, D_VIDRIO
    db = dg - SOLAPE
    piedra = M["piedra"]
    for k in range(N):
        k2 = (k + 1) % N
        tm = ang[k] + math.pi / N
        rad = (u[0] * math.cos(tm), u[1] * math.cos(tm), math.sin(tm))
        nrad = (-rad[0], -rad[1], -rad[2])
        (ao, zo), (ao2, zo2) = ext[k], ext[k2]
        (ai, zi), (ai2, zi2) = inte[k], inte[k2]
        mb.cara([P(ao, df, zo), P(ao2, df, zo2), P(ai2, df, zi2), P(ai, df, zi)], piedra, n)
        mb.cara([P(ao, 0, zo), P(ao2, 0, zo2), P(ao2, df, zo2), P(ao, df, zo)], piedra, rad)
        mb.cara([P(ai, db, zi), P(ai2, db, zi2), P(ai2, df, zi2), P(ai, df, zi)], piedra, nrad)
    mb.cara([P(a, dg, z) for (a, z) in inte], M["vidrio"], n)
    if aud is not None:
        aud.append(dict(tipo="oculo", lado=pa.nombre, puntos=ext,
                        z_cima_inf=info["z_cima_inf"], pendiente=info["pendiente"],
                        z_min=info["z_min"]))


def _anillo(mb, hx, fondo, d, z0, z1, mat, exp_i, exp_d, frente=True, omit=""):
    """Anillo perimetral de relieve `d` entre z0 y z1 hecho de TIRAS pegadas por
    fuera a los muros: ninguna cara queda dentro del edificio ni coplanar con
    una medianera (en un lateral no expuesto el anillo muere a ras del muro,
    con su testa fuera del pano de la medianera). omit: 'z' sin cara inferior,
    'Z' sin cara superior. frente=False: la tira de la fachada principal la
    pone el llamador (zocalo partido por el porton), con el mismo relieve."""
    x0 = -hx - (d if exp_i else 0.0)
    x1 = hx + (d if exp_d else 0.0)
    if frente:
        mb.box(x0, x1, 0.0, d, z0, z1, mat, omit="y" + omit)
    mb.box(x0, x1, -fondo - d, -fondo, z0, z1, mat, omit="Y" + omit)
    # laterales encajados entre la tira frontal y la trasera (entran 1 cm en
    # ellas: mismo material y mismos planos, sin junta en T en las esquinas)
    s = SOLAPE
    if exp_i:
        mb.box(-hx - d, -hx, -fondo - s, s, z0, z1, mat, omit="XyY" + omit)
    if exp_d:
        mb.box(hx, hx + d, -fondo - s, s, z0, z1, mat, omit="xyY" + omit)


def _chimenea_escape(mb, cx, cy, z_base, z_apoyo, alto, M, plana=False):
    """Chimenea firma: fuste de obra con albardilla + tubo de escape cromado.
    z_base queda por DEBAJO del faldon; z_apoyo = cota del tejado en su centro."""
    z_obra = z_apoyo + 0.55
    mb.box(cx - 0.31, cx + 0.31, cy - 0.31, cy + 0.31, z_base, z_obra, M["estuco"], omit="zZ")
    mb.box(cx - 0.38, cx + 0.38, cy - 0.38, cy + 0.38, z_obra, z_obra + 0.10, M["piedra"])
    z_tubo = z_obra + 0.10
    z_top = z_tubo + alto * 0.72
    mb.cilindro(cx, cy, z_tubo, z_top - 0.30, 0.16, M["metal"], segs=8, base=False, tapa=False)
    mb.cilindro(cx, cy, z_top - 0.45, z_top, 0.235, M["cromo"], segs=8,
                base=True, tapa=True, mat_tapa=M["forja"])
    return z_top


def _elegir_cerradas(rng_d, candidatos, plantas):
    """Contraventanas cerradas de un muro: muestreo sin reemplazo con tope
    max(1, n//6), como mucho una por planta y nunca pegada (vertical o
    diagonal) a otra cerrada, para que no parezca un patron ni un fallo."""
    n = len(candidatos)
    if n < 4:
        return set()
    tope = min(max(1, n // 6), plantas)
    k = max(0, min(tope, int(round(n * 0.12 + rng_d.uniform(-0.6, 0.6)))))
    orden = list(candidatos)
    rng_d.shuffle(orden)
    elegidas = []
    for (p, c) in orden:
        if len(elegidas) >= k:
            break
        if any(p == q or (abs(p - q) == 1 and abs(c - e) <= 1) for (q, e) in elegidas):
            continue
        elegidas.append((p, c))
    return set(elegidas)


# ---------------------------------------------------------------------------
# Generacion de una casa a un nivel de detalle dado
# ---------------------------------------------------------------------------

def _generar(plantas, ancho, fondo, M, tejado, rng, rng_d, exp_i, exp_d, nivel, lod, aud):
    estuco, piedra, teja = M["estuco"], M["piedra"], M["teja"]
    simple = lod >= 1
    carp_f, carp_r = ("plano", "plano") if simple else NIVELES[nivel]
    mb = _MB()
    hx = ancho / 2.0
    h_muro = H_BAJA + (plantas - 1) * H_PLANTA

    pa_f = _Pared("frente", 0.0, 0.0, 0, 1, ancho)
    pa_t = _Pared("trasera", 0.0, -fondo, 0, -1, ancho)
    pa_i = _Pared("izq", -hx, -fondo / 2.0, -1, 0, fondo)
    pa_d = _Pared("der", hx, -fondo / 2.0, 1, 0, fondo)
    paredes = [pa_f, pa_t] + ([pa_i] if exp_i else []) + ([pa_d] if exp_d else [])
    huecos = {pa.nombre: [] for pa in paredes}

    # x exterior de un elemento con relieve d: en un lateral expuesto dobla la
    # esquina; en una medianera muere a ras del muro
    def xl(d):
        return -hx - d if exp_i else -hx

    def xr(d):
        return hx + d if exp_d else hx

    # --------------------------------------------- columnas de huecos por muro
    xs, paso = _columnas(ancho, 2.5)          # frente y trasera
    ys, paso_l = _columnas(fondo, 3.0)        # laterales
    persianas_f = paso >= 2.3
    persianas_l = paso_l >= 2.3

    # -------------------------------------------------------- planta baja (frente)
    # (misma secuencia aleatoria que la v1: balcones -> puerta -> toldos)
    balcones = []
    for p in range(1, plantas):
        balcones.append(rng.randrange(len(xs)) if rng.random() < 0.75 else -1)
    if len(xs) >= 2:
        puerta_x = xs[0] if rng.random() < 0.5 else xs[-1]
        tienda_xs = [x for x in xs if x != puerta_x]
    else:
        puerta_x, tienda_xs = xs[0], []
    # en el muro frontal u = -X, asi que a = -x
    pw = max(1.6, min(2.6, paso - 0.5))
    pj0, pj1 = _puerta(mb, pa_f, -puerta_x, pw, M, aud, huecos["frente"], simple=simple)
    toldo_key = rng.choice(list(COLS_TOLDO.keys()))
    ew = max(1.2, min(2.6, paso - 0.6))
    for tx in tienda_xs:
        _escaparate(mb, pa_f, -tx, ew, M, aud, huecos["frente"], simple=simple)
        if rng.random() < 0.7:
            _toldo(mb, pa_f, -tx, ew + 0.3, Z_TOLDO, toldo_key, M, aud, simple=simple)

    # ------------------------------------------------ plantas altas del frente
    bw = max(1.12, min(1.25, paso - 1.25))
    con_balcon = paso >= 2.3
    cand = [(p, ci) for p in range(1, plantas) for ci in range(len(xs))
            if not (con_balcon and ci == balcones[p - 1])]
    cerradas = _elegir_cerradas(rng_d, cand, plantas)
    for p in range(1, plantas):
        z_piso = H_BAJA + (p - 1) * H_PLANTA
        for ci, wx in enumerate(xs):
            modo = "abierta" if persianas_f else "sin"
            if con_balcon and ci == balcones[p - 1]:
                grupo = "b%d" % p
                z0 = z_piso + 0.16
                _ventana(mb, pa_f, -wx, z0, z_piso + ALFEIZAR + H_VENTANA - z0, M, aud, p,
                         huecos["frente"], modo=modo, carp=carp_f, grupo=grupo)
                _balcon(mb, pa_f, -wx, z_piso, bw, M, aud, grupo, simple=simple)
            else:
                if (p, ci) in cerradas:
                    modo = "cerrada"
                _ventana(mb, pa_f, -wx, z_piso + ALFEIZAR, H_VENTANA, M, aud, p,
                         huecos["frente"], modo=modo, carp=carp_f)

    # ------------------------- trasera y laterales expuestos: mismo ritmo vertical
    for pa, cols, con_pers in ((pa_t, xs, persianas_f), (pa_i, ys, persianas_l),
                               (pa_d, ys, persianas_l)):
        if pa not in paredes:
            continue
        cand = [(p, ci) for p in range(plantas) for ci in range(len(cols))]
        cerradas = _elegir_cerradas(rng_d, cand, plantas)
        for p in range(plantas):
            if p == 0:
                z0, h = ALFEIZAR_BAJA, H_VENTANA_BAJA
            else:
                z0, h = H_BAJA + (p - 1) * H_PLANTA + ALFEIZAR, H_VENTANA
            for ci, a in enumerate(cols):
                modo = "abierta" if con_pers else "sin"
                if (p, ci) in cerradas:
                    modo = "cerrada"
                _ventana(mb, pa, a, z0, h, M, aud, p, huecos[pa.nombre], modo=modo, carp=carp_r)

    # ------------------------------------------------ muros con huecos reales
    cortes = []
    if not simple:
        cortes = [(H_BAJA + (p - 1) * H_PLANTA - 0.10, H_BAJA + (p - 1) * H_PLANTA + 0.06)
                  for p in range(1, plantas)]
    for pa in paredes:
        L2 = pa.largo / 2.0
        _muro(mb, pa, -L2 + A_PILASTRA, L2 - A_PILASTRA, H_ZOCALO, h_muro - 0.20,
              huecos[pa.nombre], cortes, estuco)
    # medianeras: un solo quad liso
    for sx, expuesto in ((-1, exp_i), (1, exp_d)):
        if not expuesto:
            x = sx * hx
            mb.cara([(x, 0.0, 0.0), (x, -fondo, 0.0), (x, -fondo, h_muro), (x, 0.0, h_muro)],
                    estuco, (sx, 0, 0))

    # ------------------------------------------------------- zocalo perimetral
    # U trasera + laterales expuestos (tiras por fuera del muro)
    _anillo(mb, hx, fondo, D_ZOCALO, 0.0, H_ZOCALO, piedra, exp_i, exp_d,
            frente=False, omit="z")
    # frente en dos tramos, cortado en el porton (a = -x)
    # (cada tramo entra 1 cm en la jamba para que su testa no quede coplanar
    # con el canto de la jamba; en el registro se anota el tramo visible)
    px0, px1 = -pj1, -pj0
    for (x0, x1, e0, e1) in ((xl(D_ZOCALO), px0, 0.0, 0.01), (px1, xr(D_ZOCALO), -0.01, 0.0)):
        if x1 - x0 > 0.05:
            mb.box(x0 + e0, x1 + e1, 0.0, D_ZOCALO, 0.0, H_ZOCALO, piedra, omit="zy")
            _reg(aud, "frente", "zocalo", -x1, -x0, 0.0, H_ZOCALO)
    for pa in (pa_t, pa_i, pa_d):
        _reg(aud, pa.nombre, "zocalo", -pa.largo / 2.0, pa.largo / 2.0, 0.0, H_ZOCALO)

    # ---------------------------------- pilastras de esquina en L (4 esquinas)
    z_pil = h_muro - 0.20
    for sx, expuesto in ((-1, exp_i), (1, exp_d)):
        x_in = sx * (hx - A_PILASTRA)
        x_out = sx * (hx + (D_PILASTRA if expuesto else 0.0))
        mb.box(x_in, x_out, 0.0, D_PILASTRA, 0.0, z_pil, piedra, omit="yzZ")
        mb.box(x_in, x_out, -fondo - D_PILASTRA, -fondo, 0.0, z_pil, piedra, omit="YzZ")
        if expuesto:
            cara_muro = "x" if sx > 0 else "X"
            mb.box(sx * hx, x_out, -A_PILASTRA, 0.0, 0.0, z_pil, piedra,
                   omit=cara_muro + "YzZ")
            mb.box(sx * hx, x_out, -fondo, -fondo + A_PILASTRA, 0.0, z_pil, piedra,
                   omit=cara_muro + "yzZ")
    for pa in (pa_f, pa_t, pa_i, pa_d):
        L2 = pa.largo / 2.0
        _reg(aud, pa.nombre, "pilastra", -L2, -L2 + A_PILASTRA, 0.0, z_pil)
        _reg(aud, pa.nombre, "pilastra", L2 - A_PILASTRA, L2, 0.0, z_pil)

    # --------------------------------------- bandas de forjado (todo el perimetro)
    for (c0, c1) in cortes:
        _anillo(mb, hx, fondo, D_BANDA, c0, c1, piedra, exp_i, exp_d)
        for pa in (pa_f, pa_t, pa_i, pa_d):
            _reg(aud, pa.nombre, "banda", -pa.largo / 2.0, pa.largo / 2.0, c0, c1)

    # ------------------------------------------------ cornisa de dos escalones
    _anillo(mb, hx, fondo, 0.12, h_muro - 0.20, h_muro, piedra, exp_i, exp_d, omit="Z")
    # (en una medianera la cornisa y el tejado no vuelan sobre el vecino: si las
    # dos casas tienen la misma altura sus faldones se pisarian casi coplanares)
    # (3 cm y 6 cm de resalte: canto de cornisa, testero del faldon y hastial
    # quedan en tres planos distintos, sin coplanares)
    cx0 = -hx - (0.28 if exp_i else 0.03)
    cx1 = hx + (0.28 if exp_d else 0.03)
    z_alero = h_muro + 0.32
    mb.box(cx0, cx1, -fondo - 0.28, 0.28, h_muro, z_alero, piedra,
           omit="Z" if tejado != "dosaguas" else "")
    for pa in (pa_f, pa_t, pa_i, pa_d):
        _reg(aud, pa.nombre, "cornisa", -pa.largo / 2.0, pa.largo / 2.0, h_muro - 0.20, z_alero)

    # ------------------------------------------------------------------ tejado
    ov = 0.4          # vuelo del alero
    n_chim = rng.randint(1, 2)
    if tejado == "dosaguas":
        alza = max(2.0, min(3.1, fondo * 0.25))
        z_cima = z_alero + alza
        y_c = -fondo / 2.0
        esp = 0.14
        pend = alza / (ov + fondo / 2.0)
        xa = -hx - (ov if exp_i else 0.06)
        xb = hx + (ov if exp_d else 0.06)
        for sy in (1, -1):                      # faldon delantero / trasero
            y_al = ov if sy > 0 else -fondo - ov
            top = [(xa, y_al, z_alero), (xb, y_al, z_alero), (xb, y_c, z_cima), (xa, y_c, z_cima)]
            bot = [(x, y, z - esp) for (x, y, z) in top]
            mb.cara(top, teja, (0.0, sy * pend, 1.0))
            mb.cara(bot, teja, (0.0, -sy * pend, -1.0))
            mb.cara([top[0], top[1], bot[1], bot[0]], teja, (0, sy, 0))          # canto del alero
            mb.cara([top[0], top[3], bot[3], bot[0]], teja, (-1, 0, 0))          # testeros
            mb.cara([top[1], top[2], bot[2], bot[1]], teja, (1, 0, 0))
        # caballete (2 cm mas largo que los faldones: sin caras coplanares)
        mb.box(xa - 0.02, xb + 0.02, y_c - 0.17, y_c + 0.17, z_cima - 0.12, z_cima + 0.10,
               teja, omit="z")
        # hastiales ajustados a la cara inferior del faldon
        # (arrancan en la tapa de la cornisa: no comparten plano con su canto)
        zb_alero = max(z_alero + 0.005, z_alero + pend * ov - esp + 0.03)
        zb_cima = z_cima - esp + 0.03
        for pa, expuesto in ((pa_i, exp_i), (pa_d, exp_d)):
            info = dict(zc=z_alero + (alza - 0.25) / 2.0, z_cima_inf=z_cima - esp,
                        pendiente=pend, z_min=z_alero)
            _hastial(mb, pa, z_alero, zb_alero, zb_cima, M, aud, info,
                     oculo=expuesto and not simple and fondo >= 7.0)

        def z_tejado(y):
            return z_cima - pend * abs(y - y_c)

        for i in range(n_chim):
            cx = rng.uniform(-hx * 0.6, hx * 0.6)
            alto = rng.uniform(1.3, 1.8)
            t = fondo * (0.12 + 0.17 * i)
            cy = y_c + t if i == 0 else y_c - t         # una por faldon
            z_lo = z_tejado(cy + (0.38 if cy > y_c else -0.38))
            z_hi = z_tejado(cy - (0.38 if cy > y_c else -0.38))
            z_top = _chimenea_escape(mb, cx, cy, z_lo - 0.15, z_hi, alto, M)
            if aud is not None:
                aud.append(dict(tipo="chimenea", cx=cx, cy=cy, r=0.38, z_base=z_lo - 0.15,
                                z_top=z_top, z_tejado_min=z_lo, z_tejado_max=z_hi))
    else:
        # plano: terraza con peto y albardilla en los 4 lados. La cornisa no
        # tiene tapa: repisa de piedra por fuera del peto + suelo de terraza
        # propio por dentro (ambos entran 1 cm bajo el peto).
        # La repisa son 4 trapecios a inglete cuyos bordes exteriores coinciden
        # vertice a vertice con los cantos de la cornisa (sin juntas en T en la
        # arista viva) y que cierran tambien el hueco del peto por debajo.
        g, hp, s = 0.30, 0.90, SOLAPE
        z0, z1 = z_alero, z_alero + hp
        up = (0, 0, 1)
        oy0, oy1 = -fondo - 0.28, 0.28
        ix0, ix1, iy0, iy1 = -hx + g - s, hx - g + s, -fondo + g - s, -g + s
        O = ((cx0, oy1), (cx1, oy1), (cx1, oy0), (cx0, oy0))
        I = ((ix0, iy1), (ix1, iy1), (ix1, iy0), (ix0, iy0))
        for k in range(4):
            k2 = (k + 1) % 4
            mb.cara([(O[k][0], O[k][1], z0), (O[k2][0], O[k2][1], z0),
                     (I[k2][0], I[k2][1], z0), (I[k][0], I[k][1], z0)], piedra, up)
        mb.cara([(x, y, z0) for (x, y) in I], M["terraza"], up)
        mb.box(-hx, hx, -g, 0.0, z0, z1, estuco, omit="zZ")
        mb.box(-hx, hx, -fondo, -fondo + g, z0, z1, estuco, omit="zZ")
        mb.box(-hx, -hx + g, -fondo + g, -g, z0, z1, estuco, omit="zZyY")
        mb.box(hx - g, hx, -fondo + g, -g, z0, z1, estuco, omit="zZyY")
        e = 0.06
        mb.box(-hx - e, hx + e, -g - e, e, z1, z1 + 0.10, piedra)
        mb.box(-hx - e, hx + e, -fondo - e, -fondo + g + e, z1, z1 + 0.10, piedra)
        mb.box(-hx - e, -hx + g + e, -fondo + g + e, -g - e, z1, z1 + 0.10, piedra, omit="yY")
        mb.box(hx - g - e, hx + e, -fondo + g + e, -g - e, z1, z1 + 0.10, piedra, omit="yY")
        for i in range(n_chim):
            cx = rng.uniform(-hx * 0.6, hx * 0.6)
            alto = rng.uniform(1.3, 1.8)
            cy = -fondo * 0.5 + (i - 0.5) * fondo * 0.22
            z_top = _chimenea_escape(mb, cx, cy, z0 - 0.05, z0, alto, M)
            if aud is not None:
                aud.append(dict(tipo="chimenea", cx=cx, cy=cy, r=0.38, z_base=z0 - 0.05,
                                z_top=z_top, z_tejado_min=z0, z_tejado_max=z0))
    return mb


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
    estado = rng.getstate()     # a partir de aqui, misma secuencia que la v1

    laterales = tuple(params.get("laterales", (True, True)))
    exp_i, exp_d = bool(laterales[0]), bool(laterales[1])
    aud = params.get("auditoria")
    lod = int(params.get("lod", 0) or 0)

    M = _materiales(color_key, color)
    plantas = max(1, int(plantas))
    ancho = max(3.0, float(ancho))
    fondo = max(3.0, float(fondo))

    # presupuesto: se degrada la carpinteria por pasos hasta caber en 5000 tris
    niveles = [0] if lod >= 1 else list(range(len(NIVELES)))
    mb, reg = None, None
    for nivel in niveles:
        rng.setstate(estado)
        # detalles propios de la v2 con su generador: no altera la secuencia
        # de `rng`, asi color/tejado/puerta/toldos salen igual que en la v1
        rng_d = random.Random(seed * 7919 + 17)
        reg = [] if aud is not None else None
        mb = _generar(plantas, ancho, fondo, M, tejado, rng, rng_d, exp_i, exp_d,
                      nivel, lod, reg)
        if mb.tris() <= TRIS_OBJETIVO:
            break
    if aud is not None:
        aud.extend(reg)
        aud.append(dict(tipo="info", nivel=nivel, lod=lod, tris=mb.tris()))

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
            lod=params.get("lod", 0),
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
