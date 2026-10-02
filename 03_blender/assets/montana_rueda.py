"""montana_rueda.py — La MONTAÑA-RUEDA de Porto Corsa (Cars 2), Blender 5.1.

Macizo de caliza cuya CARA FRONTAL (+Y) es una PARED de acantilado en la que
está embutida A RAS una rueda de coche gigante vista de lado, como el peñón de
la rueda fósil de la película (peli_montana_rueda_tunel.png):

  * NEUMÁTICO exterior de perfil redondeado que sobresale ~5 m de la pared y
    está hundido `alto_base` m en el suelo (la base queda plana en z=0), con
    dos surcos concéntricos (capas de piedra).
  * LLANTA plana y, dentro, un HUECO circular profundo (10-13 m) con LABIO
    VOLADO de ~3.4 m y pared en talud negativo, de modo que el hueco se
    autosombrea (media luna de sombra bajo el aro); material casi negro.
  * RUEDA FÓSIL tallada en relieve dentro del hueco: buje con tetón, collarín,
    `n_radios` radios finos de piedra gris clara de sección irregular y
    ahusada, con nudillos, muescas y alguna rotura, y un aro interior.
  * PARED de roca a ambos lados de la rueda y por encima (CEJA volada de
    ~6 m sobre el neumático), con talud en el pie (la huella en z=0 es lo más
    ancho), estratos horizontales rectos con repisas, planos de fractura
    (bloques/columnas), grietas (ruido ridged) y sombreado plano facetado.
  * ESPOLÓN (contrafuerte) en el pie IZQUIERDO que avanza ~33 m por delante
    de la pared: masa a ras de suelo para que el integrador perfore un TÚNEL
    para la carretera (a lo largo de X) con un Boolean EXACT.
  * LOMO trasero: cresta quebrada de montaña (gablete, no cúpula) que baja
    hasta morir en el suelo por detrás (-Y).

MALLA ÚNICA CERRADA (2-manifold, normales coherentes, sin auto-
intersecciones): topología de esfera (polo en el buje -> anillos de la cara
-> neumático -> ranura -> anillos de la pared (campo de alturas en Y) ->
anillos del cuerpo (secciones estrelladas) -> polo trasero enterrado),
cortada por z=0 (bmesh bisect) y tapada con un fondo plano. <= 40k tris.

100%% procedural: sin bpy.ops, sin texturas de imagen; colores planos.

Piezas (kit):
  build(parent_collection, radio=55, espesor=70, alto_base=12, seed=0,
        n_radios=20, con_vegetacion=True, con_espolon=True,
        segmentos_por_radio=None)
      -> malla raíz MRUEDA_roca (única, cerrada, 32.6k tris con 20 radios x
         10 segmentos = 200 vértices por anillo; con n_radios=12 usa 16).
         Propiedades: obj["centro_buje"] (x,y,z), obj["radio"],
         obj["espesor"], obj["alto_base"], obj["y_pared"] (plano medio de la
         pared), obj["huella_x"] (min,max en z=0), obj["espolon"]
         (x_min, x_max, y_frente, z_alto) o vacío;
         mesh["mrueda_no_manifold"] (debe ser 0), mesh["mrueda_tapa_caras"].
         + hijo MRUEDA_veg (36 matas grandes r 3.5-6.5 m en 4 repisas de la
           pared + espolón + lomo, y 5 pinos de una sola cáscara; 1.9k tris,
           malla aparte para que el boolean del túnel la ignore; cada isla
           apoyada por ray-cast sobre la malla final)
  build_arco(parent_collection, luz=16, alto=13, grosor=6, seed=0,
             con_vegetacion=True)
      -> malla MRUEDA_arco (arco natural de roca facetado, 2.9k tris, una
         sola cáscara sin auto-intersecciones) + hijo MRUEDA_arco_veg (0.4k)

Convenciones (metros; cifras MEDIDAS en malla con los valores por defecto
R=55, espesor=70, alto_base=12, seed=0 — las imprime test_montana_rueda.py):
  build(): origen en el centro de la base, z=0 en el suelo, rueda mirando a
    +Y. Frente del neumático en y = +espesor/2 (= +35). Plano medio de la
    pared y_pared = espesor/2 - 0.09*R (= +30.05), con relieve de +-4 m,
    talud de 4 cm/m (avanza ~+1.7 m en el pie, retrocede ~-3 m en la cresta)
    y ceja volada de hasta +6.6 m sobre la rueda (z 95-111 m); la pared sin
    espolón llega como mucho a y = +38.7.
    Centro del buje (0, espesor/2 - 0.092*R, radio - alto_base) = (0, 29.9, 43).
    Diámetro de la rueda 2*radio (rodadura en r = radio, enterrada en la
    pared: sólo asoma el flanco, r < 0.985*radio).
    Huella en z=0: x en [-85.7, +85.3] (= +-1.56 R) y es lo MÁS ANCHO del
    macizo (max|x| global = max|x| en z=0; nada vuela sobre el pie);
    y en [-33.7, +70.6] (el +70.6 es el espolón izquierdo).
    Cumbre z = 135 m (2.46 R), justo detrás de la ceja, más alta a la derecha.
    Espolón: x en [-78, -59], frente en y = +70.6, lomo en rampa hasta ~21 m
    de alto sobre la boca. Túnel comprobado en el test: Boolean EXACT de una
    caja (56 x 14 x 9) centrada en (-68, espesor/2 + 14, 4.5) a lo largo de
    X -> resultado cerrado, 0 auto-intersecciones (con_espolon=False lo
    elimina y la huella queda en y <= +38.7).
  build_arco(): origen en el centro del hueco a nivel del suelo; la carretera
    pasa por debajo a lo largo de Y. Gálibo garantizado: caja libre de
    luz (X) x alto (Z) para todo Y (clamp de seguridad de cada vértice).
"""

import math
import random
import warnings

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# ---------------------------------------------------------------- ruido ----
try:
    from mathutils import noise as _mnoise

    def _n3(x, y, z):
        return _mnoise.noise(Vector((x, y, z)))
except Exception:  # fallback puro python (valor-ruido trilineal)
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
                    v += w * _hash01(ix + dx, iy + dy, iz + dz)
        return v * 2.0 - 1.0


def _hash01(ix, iy, iz):
    n = (ix * 374761393 + iy * 668265263 + iz * 1440662683) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def _ridged(x, y, z, so, k=1.0):
    """Ruido 'ridged' multifractal a escala de macizo (k=1: rasgos de 60,
    20 y 8 m): crestas afiladas y grietas donde el ruido cruza cero.
    Devuelve metros, aprox. en [-4, +4]."""
    r1 = 1.0 - abs(_n3(x * 0.016 * k + so, y * 0.016 * k, z * 0.016 * k))
    r2 = 1.0 - abs(_n3(x * 0.05 * k + so * 2.0, y * 0.05 * k + 7.0,
                       z * 0.05 * k))
    g = _n3(x * 0.13 * k, y * 0.13 * k + so, z * 0.13 * k + 3.0)
    return (r1 * r1 - 0.5) * 4.5 + (r2 * r2 - 0.5) * 1.8 + g * 0.5


def _celda(x, y, z, so, cw, ch):
    """Desplazamiento constante por BLOQUE (malla 3D de celdas cw x cw x ch
    con juntas ligeramente onduladas): planos de fractura verticales y
    horizontales; con sombreado plano se leen como bloques/columnas.
    Devuelve [-1, 1]."""
    jx = 0.22 * cw * _n3(y * 0.05 + so, z * 0.05, 1.7)
    jy = 0.22 * cw * _n3(x * 0.05, z * 0.05 + so, 6.1)
    jz = 0.18 * ch * _n3(x * 0.04 + so, y * 0.04, 9.3)
    ix = math.floor((x + jx) / cw)
    iy = math.floor((y + jy) / cw)
    iz = math.floor((z + jz) / ch)
    return 2.0 * _hash01(ix + 7 * int(so), iy + 3, iz) - 1.0


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


def _sq(v, q):
    """Superelipse: signo de v con |v|^(2/q)."""
    return math.copysign(abs(v) ** (2.0 / q), v)


# ------------------------------------------------------------ materiales ----
def _mat(name, color, rough=0.93, spec=0.25):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    if m.node_tree is None:           # Blender < 5 (en 5.x ya viene con nodos
        try:                          # y use_nodes está obsoleto)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m.use_nodes = True
        except Exception:
            pass
    bsdf = None
    if m.node_tree is not None:
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf is None:
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    bsdf = n
                    break
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = spec
    m.diffuse_color = (*color, 1.0)
    return m


# índices de material en MRUEDA_roca / MRUEDA_arco
_M_CAL, _M_CLARA, _M_OSC, _M_HUECO, _M_HUESO = 0, 1, 2, 3, 4


def _mats_roca():
    """Caliza cálida gris-ocre (estratos), hueco casi negro y hueso de piedra
    gris clara (no blanco: no se quema con sol 2.6 y vista Standard)."""
    return (
        _mat("MAT_MRUEDA_caliza", (0.470, 0.405, 0.305), 0.95),
        _mat("MAT_MRUEDA_caliza_clara", (0.600, 0.535, 0.415), 0.95),
        _mat("MAT_MRUEDA_caliza_oscura", (0.300, 0.250, 0.185), 0.95),
        _mat("MAT_MRUEDA_hueco", (0.090, 0.075, 0.055), 0.97, 0.10),
        _mat("MAT_MRUEDA_hueso", (0.400, 0.360, 0.290), 0.92, 0.20),
    )


def _mats_veg():
    return (
        _mat("MAT_MRUEDA_veg", (0.062, 0.195, 0.058), 0.92),
        _mat("MAT_MRUEDA_veg_clara", (0.130, 0.310, 0.090), 0.92),
        _mat("MAT_MRUEDA_tronco", (0.230, 0.150, 0.090), 0.95),
    )


# ------------------------------------------------------------- estratos ----
_ESTRATO_PAT = (_M_CLARA, _M_OSC, _M_CAL, _M_OSC, _M_CLARA, _M_CAL,
                _M_CAL, _M_OSC)


def _fase_estrato(x, y, so):
    """Fase lenta y pequeña (+-0.5 rad) de los estratos: bandas casi rectas."""
    return 0.5 * _n3(x * 0.012 + so, y * 0.012, 4.4)


def _onda_estrato(c, band_h, ph):
    return math.cos(2.0 * math.pi * c / band_h + ph)


def _estrato_mat(c, band_h, ph):
    """Material por MEDIA banda: índice par = banda saliente (cos > 0), impar
    = entrante; el borde de color coincide con el escalón geométrico."""
    t = c / band_h + ph / (2.0 * math.pi)
    k = math.floor(t * 2.0 + 0.5)
    return _ESTRATO_PAT[k % 8]


# ===================================================== cara de la rueda ====
# Regiones de la cara frontal en u = r / radio
_HUB_U = 0.160                    # pie del buje (domo)
_COL_U0, _COL_U1 = 0.160, 0.225   # collarín (toro) alrededor del buje
_SPK_U0, _SPK_U1 = 0.090, 0.655   # radios (se funden con buje y aro)
_RING_U0, _RING_U1 = 0.610, 0.668  # aro interior donde rematan los radios
_FLOOR_U1 = 0.700                 # borde del fondo del hueco (pie del talud)
_RIM_U1 = 0.745                   # fin de la llanta plana; empieza neumático
_FLOOR_D0, _FLOOR_D1 = -0.235, -0.195  # fondo del hueco (centro / borde)
# neumático: superelipse en el plano (r, y)
_TY_RC, _TY_AR, _TY_AY, _TY_Q = 0.86, 0.14, 0.19, 2.5

# anillos de la cara: u (profundidad = fondo del hueco) o (u, d) explícito
# para la pared del hueco EN TALUD NEGATIVO (más ancha en el fondo) y el
# LABIO VOLADO de 0.062 R (~3.4 m) que sombrea el hueco, y la llanta plana
_U_RINGS = [0.035, 0.075, 0.11, 0.14, 0.16, 0.18, 0.205, 0.225, 0.245,
            0.265, 0.285, 0.305, 0.325, 0.345, 0.365, 0.385, 0.405, 0.425,
            0.445, 0.465, 0.485, 0.505, 0.525, 0.545, 0.565, 0.585, 0.60,
            0.61, 0.625, 0.64, 0.655, 0.668, 0.684, 0.700,
            (0.714, -0.160), (0.718, -0.120), (0.712, -0.092),
            (0.690, -0.080), (0.662, -0.074), (0.652, -0.064),
            (0.660, -0.054), (0.690, -0.058), (0.720, -0.062),
            (0.745, -0.062)]
_PSI_RINGS = [131.0, 121.0, 111.0, 102.0, 95.0, 89.0, 82.0, 74.0, 67.0,
              61.0, 55.0, 48.0, 41.0, 34.0, 28.0]
# anillos de la pared (f: 0 = junto al neumático, 1 = silueta exterior)
_F_RINGS = [0.02, 0.06, 0.12, 0.20, 0.30, 0.42, 0.56, 0.72, 0.87, 1.0]
# anillos del cuerpo (s: 0 = plano de la pared, 1 = polo trasero)
_S_RINGS = [0.015, 0.035, 0.06, 0.09, 0.125, 0.165, 0.21, 0.255, 0.30,
            0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80,
            0.85, 0.895, 0.935, 0.965, 0.985]
# semiancho de la base (unid. R) y cota de la cresta (unid. R) según s
_WB_PTS = [(0.0, 1.50), (0.2, 1.48), (0.4, 1.38), (0.6, 1.12), (0.75, 0.82),
           (0.88, 0.48), (0.965, 0.16), (1.0, 0.0)]
_ZT_PTS = [(0.0, 2.15), (0.12, 2.30), (0.30, 2.28), (0.50, 1.95),
           (0.65, 1.45), (0.78, 0.95), (0.88, 0.52), (0.95, 0.22),
           (1.0, -0.30)]
_Z_FLOOR = -0.30      # suelo enterrado bajo el macizo (unid. R)
_Y_WALL = -0.09       # plano de la pared respecto al frente del neumático
_LEAN = 0.04          # talud de la pared: retranqueo (m) por m de altura
_BAND_H = 0.17        # altura de estrato (unid. R)
_Q_UP = 1.7           # superelipse de la cresta (< 2: gablete)
# repisas explícitas de la pared para la vegetación: (x/R, z/R, semiancho/R)
_REPISAS = [(-1.18, 0.85, 0.20), (1.20, 0.80, 0.18), (-0.45, 1.93, 0.16),
            (0.95, 1.45, 0.14)]
# espolón izquierdo: centro x, semiancho (unid. R), avance en +Y (unid. R)
_ESP_XC, _ESP_HW, _ESP_AV, _ESP_Z0, _ESP_DZ = -1.25, 0.21, 0.66, 0.12, 0.32


def _perfil_base(u):
    """Profundidad (unid. radio) del fondo del hueco (ligeramente cóncavo)."""
    t = min(u / _FLOOR_U1, 1.0)
    return _FLOOR_D0 + (_FLOOR_D1 - _FLOOR_D0) * t * t


def _radios_en(u, R, n_spokes, so):
    """Para el anillo u: lista por radio j de (ángulo del eje, semiancho m,
    factor de altura). Radios finos y ahusados, cada uno con su grosor, un
    leve serpenteo, nudillos donde nacen del buje y rematan en el aro y
    bordes MELLADOS (ruido de +-28%% del semiancho a lo largo de u)."""
    P = 2.0 * math.pi / n_spokes
    t = max(0.0, min(1.0, (u - 0.14) / (_SPK_U1 - 0.14)))
    ks = (20.0 / n_spokes) ** 0.5
    out = []
    for j in range(n_spokes):
        kf = 1.0 + 0.22 * _n3(j * 7.13 + so, 2.2, 0.5)          # grosor
        hf = 1.0 + 0.15 * _n3(j * 5.31 + so * 0.7, 8.8, 1.5)    # altura
        wob = 0.012 * _n3(u * 3.0 + j * 4.7 + so, 1.1, 3.3)     # serpenteo
        w = R * (0.025 - 0.009 * t) * kf * ks
        w *= (1.0 + 0.50 * math.exp(-((u - 0.17) / 0.04) ** 2) +
              0.40 * math.exp(-((u - 0.625) / 0.04) ** 2) +
              0.30 * _n3(u * 17.0 + j * 3.3, so, 0.7))
        out.append((math.pi / 2.0 + j * P + wob, max(w, 0.15), hf))
    return out


def _spoke_hit(a, r, radios):
    """(dm, w, hf, j) del radio más cercano al ángulo a (dm = distancia de
    arco en metros al eje del radio)."""
    best = None
    for j, (ax, w, hf) in enumerate(radios):
        d = (a - ax + math.pi) % (2.0 * math.pi) - math.pi
        d = abs(d) * r
        if best is None or d < best[0]:
            best = (d, w, hf, j)
    return best


def _talla(u, x, z, R, radios, so):
    """Altura (m) de la talla sobre la superficie base: buje abombado con
    grumos y tetón central, collarín (toro), radios de sección de costilla
    (plana arriba, borde redondeado) con altura irregular y roturas, y aro
    interior. Devuelve (altura, es_radio)."""
    h = 0.0
    es_radio = False
    r = max(u * R, 1e-3)
    if u < _HUB_U:
        t = u / _HUB_U
        h = R * 0.115 * (1.0 - t ** 3.0) ** (1.0 / 2.4)
        h *= 1.0 + 0.10 * _n3(x * 0.22 + so, z * 0.22, 6.1) + \
            0.05 * _n3(x * 0.6, z * 0.6 + so, 2.4)
        if u < 0.05:
            h += R * 0.028 * (1.0 - (u / 0.05) ** 2)      # tetón
    if _COL_U0 <= u <= _COL_U1:
        h = max(h, R * 0.034 * math.sin(math.pi * (u - _COL_U0) /
                                        (_COL_U1 - _COL_U0)) ** 0.8)
    if _SPK_U0 <= u <= _SPK_U1:
        a = math.atan2(z, x)
        dm, w, hf, j = _spoke_hit(a, r, radios)
        if dm < w:
            t = max(0.0, min(1.0, (u - 0.14) / (_SPK_U1 - 0.14)))
            hs = R * (0.058 - 0.020 * t) * hf
            hs *= 1.0 + 0.25 * _n3(u * 19.0 + j * 2.1 + so, 4.4, 0.9)
            # nudillos (engrosamientos) en el nacimiento y el remate
            hs *= (1.0 + 0.30 * math.exp(-((u - 0.19) / 0.04) ** 2) +
                   0.25 * math.exp(-((u - 0.61) / 0.04) ** 2))
            brk = _n3(u * 23.0 + j * 2.9 + so, 5.5, 1.3)
            if brk > 0.42:                                  # rotura/muesca
                hs *= max(0.2, 1.0 - 2.2 * (brk - 0.42))
            if _hash01(j, int(so * 10), 3) < 0.15:          # trozo que falta
                ug = 0.30 + 0.28 * _hash01(j, 5, int(so))
                hs *= 0.15 + 0.85 * _sstep((abs(u - ug) - 0.025) / 0.02)
            hsp = hs * max(0.0, 1.0 - (dm / w) ** 2.2) ** 0.45
            if hsp > h:
                h = hsp
                es_radio = True
    if _RING_U0 <= u <= _RING_U1:
        hr = R * 0.045 * math.sin(math.pi * (u - _RING_U0) /
                                  (_RING_U1 - _RING_U0)) ** 0.75
        hr *= 1.0 + 0.12 * _n3(x * 0.15 + so, z * 0.15, 4.2)
        if hr > h:
            h = hr
            es_radio = False
    return h, es_radio


def _angulos_cara(u, R, n_spokes, m, lam, radios):
    """Ángulos (rad, crecientes desde el eje del radio 0) de los n_spokes*m
    vértices del anillo u. Con lam=1 la distribución se ciñe a los radios
    (vértices justo en el eje, +-0.45w, +-0.8w y +-1.0w del semiancho
    angular) para que la talla salga nítida; lam=0 -> uniforme."""
    P = 2.0 * math.pi / n_spokes
    r = max(u * R, 1e-3)
    ng = m - 7
    out = []
    for j in range(n_spokes):
        ax, w, _hf = radios[j]
        ax1, w1, _hf1 = radios[(j + 1) % n_spokes]
        span = (ax1 - ax) % (2.0 * math.pi)
        if span < 1e-6:
            span = 2.0 * math.pi
        wa = min(w / r, 0.36 * span)
        wa1 = min(w1 / r, 0.36 * span)
        offs = [0.0, 0.45 * wa, 0.8 * wa, wa]
        for i in range(ng):
            offs.append(wa + (span - wa - wa1) * (i + 1) / (ng + 1))
        offs += [span - wa1, span - 0.8 * wa1, span - 0.45 * wa1]
        a0u = math.pi / 2.0 + j * P
        for i in range(m):
            uni = P * i / m
            out.append(lam * (ax + offs[i]) + (1.0 - lam) * (a0u + uni))
    return out


def _tyre_pt(psi, R):
    """Punto (r, y_rel) del perfil del neumático (superelipse) para el ángulo
    psi (grados): 90 = frente del flanco, 0 = banda de rodadura."""
    p = math.radians(psi)
    r = R * (_TY_RC + _TY_AR * _sq(math.cos(p), _TY_Q))
    y = R * (-_TY_AY + _TY_AY * abs(math.sin(p)) ** (2.0 / _TY_Q))
    return r, y


# ======================================================= geometría roca ====
def _rho_sil(ca, sa, Wb, zt, xo, zcs, zfl, R, q_up=_Q_UP):
    """Radio (m) de la SILUETA transversal (plano XZ) desde el centro polar
    (xo, zcs) en la dirección (ca, sa): mínimo de tres tapas
      - suelo enterrado z = zfl,
      - pared vertical con TALUD |x| = W(z) = Wb*(1 - 0.12*sstep(z/0.8R))
        (más ancha en el pie: la huella es lo más ancho),
      - domo superior superelíptico (q<2 = gablete) hasta la cresta zt."""
    rho_g = (zfl - zcs) / sa if sa < -1e-6 else 1e9
    if abs(ca) > 1e-6:
        lo, hi = 0.0, 4.0 * R
        for _ in range(16):
            mid = 0.5 * (lo + hi)
            x = xo + mid * ca
            z = zcs + mid * sa
            if abs(x) < Wb * (1.0 - 0.12 * _sstep(z / (0.8 * R))):
                lo = mid
            else:
                hi = mid
        rho_w = hi
    else:
        rho_w = 1e9
    if sa > 1e-6:
        A = Wb * 1.05
        B = max(zt - zcs, 0.02 * R)
        rho_d = 1.0 / ((abs(ca) / A) ** q_up + (sa / B) ** q_up) ** (1.0 / q_up)
    else:
        rho_d = 1e9
    return min(rho_g, rho_w, rho_d)


def _geometria_roca(R, espesor, alto_base, seed, n_spokes, m, con_espolon):
    """Construye el bmesh cerrado del macizo. Devuelve (bm, info)."""
    so = seed * 17.37 + 3.1
    N = n_spokes * m
    zc = R - alto_base
    y_front = 0.5 * espesor
    y_back = -0.5 * espesor
    y_wall0 = y_front + _Y_WALL * R
    z_floor = _Z_FLOOR * R
    band_h = _BAND_H * R
    cw, ch = 0.22 * R, 0.50 * R          # bloques de fractura (m)

    bm = bmesh.new()
    rings = []          # lista de listas de BMVert
    ring_info = []      # ("cara", (u,d)) | ("neu", psi) | ("ranura", 0)
    #                   # | ("pared", f) | ("cuerpo", s)

    # ---------- polo del buje ----------
    radios0 = _radios_en(0.0, R, n_spokes, so)
    h0, _ = _talla(0.0, 0.0, 0.0, R, radios0, so)
    v_hub = bm.verts.new((0.0, y_front + R * _perfil_base(0.0) + h0, zc))

    # ---------- anillos de la cara (campo de alturas polar en Y) ----------
    for item in _U_RINGS:
        if isinstance(item, tuple):
            u, dbase = item
        else:
            u, dbase = item, _perfil_base(item)
        lam = 1.0 - _sstep((u - _RING_U1) / (_RIM_U1 - _RING_U1))
        radios = _radios_en(u, R, n_spokes, so)
        angs = _angulos_cara(u, R, n_spokes, m, lam, radios)
        r = u * R
        ring = []
        for a in angs:
            xr, zr = r * math.cos(a), r * math.sin(a)
            h, _es = _talla(u, xr, zr, R, radios, so)
            d = R * dbase + h
            # grano de piedra: suave en el hueco, algo más en la llanta
            if u > _FLOOR_U1 and dbase > -0.07:
                d += 0.30 * _n3(xr * 0.09 + so, zr * 0.09, 1.7) + \
                    0.10 * _n3(xr * 0.3, zr * 0.3 + so, 4.4)
            else:
                d += 0.10 * _n3(xr * 0.12 + so, zr * 0.12, 2.9)
            ring.append(bm.verts.new((xr, y_front + d, zc + zr)))
        rings.append(ring)
        ring_info.append(("cara", (u, dbase)))

    # ---------- anillos del neumático (superelipse r-y) ----------
    angs_uni = _angulos_cara(1.0, R, n_spokes, m, 0.0, radios0)
    for psi in _PSI_RINGS:
        r0, y0 = _tyre_pt(psi, R)
        r1, y1 = _tyre_pt(psi + 0.5, R)
        r2, y2 = _tyre_pt(psi - 0.5, R)
        tr, ty = r2 - r1, y2 - y1           # tangente hacia la rodadura
        tl = math.hypot(tr, ty) or 1.0
        nr, ny = -ty / tl, tr / tl          # normal hacia fuera (r+, y+)
        ring = []
        for a in angs_uni:
            ca, sa = math.cos(a), math.sin(a)
            x, z = r0 * ca, zc + r0 * sa
            yy = y_front + y0
            # ruido de piedra a lo largo de la normal del perfil
            dn = (0.45 * _n3(x * 0.07 + so, yy * 0.07, z * 0.07) +
                  0.18 * _n3(x * 0.22, yy * 0.22 + so, z * 0.22 + 2.0))
            # surcos CONCÉNTRICOS (capas de piedra del neumático)
            dn -= 1.5 * math.exp(-((psi - 102.0) / 4.0) ** 2)
            dn -= 1.3 * math.exp(-((psi - 74.0) / 4.0) ** 2)
            dn -= 1.0 * math.exp(-((psi - 48.0) / 4.0) ** 2)
            rr = r0 + nr * dn
            yy = yy + ny * dn
            ring.append(bm.verts.new((rr * ca, yy, zc + rr * sa)))
        rings.append(ring)
        ring_info.append(("neu", psi))

    # ---------- ranura entre neumático y pared ----------
    ring = []
    for a in angs_uni:
        ca, sa = math.cos(a), math.sin(a)
        z = zc + R * sa
        ring.append(bm.verts.new((R * ca, y_wall0 - _LEAN * (z - zc) - 1.2, z)))
    rings.append(ring)
    ring_info.append(("ranura", 0.0))

    # ---------- relieve de la pared frontal ----------
    def cresta(a, y):
        """Ruido de cresta (+-10%%) en función del ángulo y la profundidad;
        la mitad IZQUIERDA (hacia el arco y el mar) queda más baja."""
        cn = (1.0 - abs(_n3(a * 1.9 + so, y * 0.035, 2.2))) ** 2 - 0.4
        return (1.0 + 0.10 * cn) * (1.0 - 0.13 * max(0.0, -math.cos(a)))

    def ceja(x, z):
        return (0.12 * R * _sstep((z - 1.72 * R) / (0.18 * R)) *
                (1.0 - _sstep((z - 2.02 * R) / (0.14 * R))) *
                _sstep((0.95 * R - abs(x)) / (0.30 * R)))

    def espolon(x, z):
        """Contrafuerte izquierdo: planta redondeada e irregular, frente
        vertical hasta ~6.6 m y lomo que sube en rampa hacia la pared."""
        if not con_espolon:
            return 0.0
        xs = (x - _ESP_XC * R) / (_ESP_HW * R)
        xs += 0.12 * _n3(z * 0.08 + so, x * 0.03, 5.5)
        wx = _sstep((1.0 - abs(xs)) / 0.55)
        z0 = _ESP_Z0 * R * (1.0 - 0.30 * abs(xs)) + 3.0 * _n3(x * 0.05, so, 7.7)
        wz = 1.0 - _sstep((z - z0) / (_ESP_DZ * R))
        return _ESP_AV * R * wx * wz

    def repisas(x, z):
        d = 0.0
        for xc, zl, hw in _REPISAS:
            wx = _sstep((hw * R - abs(x - xc * R)) / (0.4 * hw * R))
            wz = _sstep((z - (zl * R - 6.0)) / 4.0) * \
                (1.0 - _sstep((z - zl * R) / 1.5))
            d += 3.2 * wx * wz
        return d

    def y_campo(x, z):
        """Cota Y geométrica de la pared (sin ruido de roca)."""
        return (y_wall0 - _LEAN * (z - zc) + ceja(x, z) + espolon(x, z) +
                repisas(x, z))

    def normal_pared(x, z):
        """Normal (unitaria) del campo y = y_campo(x, z)."""
        e = 0.6
        dx = (y_campo(x + e, z) - y_campo(x - e, z)) / (2.0 * e)
        dz = (y_campo(x, z + e) - y_campo(x, z - e)) / (2.0 * e)
        n = Vector((-dx, 1.0, -dz))
        n.normalize()
        return n

    def collar(rho):
        if rho > 1.16 * R:
            return 0.0
        c = (rho - R) / (0.07 * R)
        return 1.1 * math.tanh(3.0 * math.cos(2.0 * math.pi * c)) * \
            (1.0 - _sstep((rho - 1.10 * R) / (0.06 * R)))

    def roca(x, y, zq, amp):
        return amp * (_ridged(x, y, zq, so) +
                      2.2 * _celda(x, y, zq, so, cw, ch))

    def escalon(x, y, zq):
        ph = _fase_estrato(x, y, so)
        return 1.3 * math.tanh(2.5 * _onda_estrato(zq, band_h, ph))

    # ---------- anillos de la pared (campo de alturas en Y) ----------
    Wb0 = R * _spline(_WB_PTS, 0.0)
    zt0 = R * _spline(_ZT_PTS, 0.0)
    for f in _F_RINGS:
        amp_f = _sstep((f - 0.03) / 0.30)
        amp_s = _sstep((f - 0.03) / 0.12)
        w = f ** 4
        ring = []
        for a in angs_uni:
            ca, sa = math.cos(a), math.sin(a)
            rho_s = _rho_sil(ca, sa, Wb0, zt0 * cresta(a, y_wall0), 0.0, zc,
                             z_floor, R)
            rho_s = max(rho_s, 1.02 * R)
            rho = 1.005 * R + (rho_s - 1.005 * R) * f
            x, z = rho * ca, zc + rho * sa
            zq = max(z, 8.0)
            D = roca(x, y_wall0, zq, amp_f) + amp_s * escalon(x, y_wall0, zq) \
                + collar(rho)
            D = 4.0 * math.tanh(D / 4.0)     # limita el relieve (sin pliegues)
            y_geo = y_campo(x, z)
            g = _sstep((z - 2.0) / 10.0)
            # desplazamiento a lo largo de la normal REAL del campo (así el
            # espolón, la ceja y las repisas tienen relieve también en sus
            # flancos y lomos), mezclado con la radial en el borde exterior
            nw = normal_pared(x, zq)
            dv = Vector((ca * w + nw.x * (1.0 - w), nw.y * (1.0 - w),
                         sa * g * w + nw.z * g * (1.0 - w)))
            dv.normalize()
            ring.append(bm.verts.new((x + dv.x * D, y_geo + dv.y * D,
                                      z + dv.z * D)))
        rings.append(ring)
        ring_info.append(("pared", f))

    # ---------- anillos del cuerpo (secciones estrelladas + roca) ----------
    for s in _S_RINGS:
        y = y_wall0 + (y_back - y_wall0) * s
        Wb = R * max(_spline(_WB_PTS, s), 0.03)
        ztb = R * _spline(_ZT_PTS, s)
        xo = R * 0.12 * _n3(s * 2.7 + so, 3.3, 1.1) * \
            _sstep((s - 0.05) / 0.3) * (1.0 - _sstep((s - 0.85) / 0.15))
        zcs = min(zc, max(0.42 * ztb, z_floor + 0.05 * R))
        amp = min(1.0, Wb / (0.35 * R))
        lean_f = 1.0 - _sstep(s / 0.10)
        ring = []
        for a in angs_uni:
            ca, sa = math.cos(a), math.sin(a)
            zt = ztb * cresta(a, y) if sa > 0.0 else ztb
            rho_s = _rho_sil(ca, sa, Wb, zt, xo, zcs, z_floor, R)
            x, z = xo + rho_s * ca, zcs + rho_s * sa
            zq = max(z, 8.0)
            D = roca(x, y, zq, amp) + amp * escalon(x, y, zq)
            g = _sstep((z - 2.0) / 10.0)
            dv = Vector((ca, 0.0, sa * g))
            dv.normalize()
            yv = y - _LEAN * (z - zc) * lean_f
            ring.append(bm.verts.new((x + dv.x * D, yv, z + dv.z * D)))
        rings.append(ring)
        ring_info.append(("cuerpo", s))

    # ---------- polo trasero enterrado ----------
    v_back = bm.verts.new((0.0, y_back, z_floor))

    # ---------- caras (con material) ----------
    def add_face(vs, mi, smooth):
        try:
            fce = bm.faces.new(vs)
        except ValueError:
            return
        fce.material_index = mi
        fce.smooth = smooth

    spoke_k = (0, 1, 2, m - 3, m - 2, m - 1)

    def mat_cara(ua, ub, k):
        u_mid = 0.5 * (ua[0] + ub[0])
        d_mid = 0.5 * (ua[1] + ub[1])
        if u_mid < _HUB_U or _COL_U0 <= u_mid <= _COL_U1:
            return _M_HUESO
        if _RING_U0 <= u_mid <= _RING_U1:
            return _M_HUESO
        if _SPK_U0 <= u_mid <= _SPK_U1 and (k % m) in spoke_k:
            return _M_HUESO
        if u_mid < _FLOOR_U1 - 0.003 or d_mid < -0.0705:
            return _M_HUECO              # fondo, talud y cara inferior del labio
        if u_mid > 0.685:
            return _M_CLARA              # llanta plana
        return _M_CAL                    # frente del labio

    def mat_neu(pa, pb):
        """Capas CONCÉNTRICAS del neumático (por psi), separadas por surcos."""
        p = 0.5 * (pa + pb)
        if p > 128.0:
            return _M_CLARA              # borde de la llanta
        if p > 102.0:
            return _M_CAL
        if p > 89.0:
            return _M_CLARA
        if p > 74.0:
            return _M_CAL
        if p > 61.0:
            return _M_OSC
        if p > 48.0:
            return _M_CAL
        return _M_OSC                    # banda exterior, junto a la pared

    def mat_roca(c):
        rho_c = math.hypot(c.x, c.z - zc)
        if c.z < 2.5:
            return _M_OSC
        if rho_c < 1.10 * R and c.y > y_wall0 - 6.0:
            return _M_CAL                # collar concéntrico junto al neumático
        return _estrato_mat(c.z, band_h, _fase_estrato(c.x, c.y, so))

    # abanico del buje (talla de piedra: sombreado plano facetado)
    r0 = rings[0]
    for k in range(N):
        add_face((v_hub, r0[k], r0[(k + 1) % N]), _M_HUESO, False)
    # bandas entre anillos
    for i in range(len(rings) - 1):
        ra, rb = rings[i], rings[i + 1]
        ta, ua = ring_info[i]
        tb, ub = ring_info[i + 1]
        for k in range(N):
            k2 = (k + 1) % N
            vs = (ra[k], ra[k2], rb[k2], rb[k])
            if ta == "cara" and tb == "cara":
                mi = mat_cara(ua, ub, k)
                add_face(vs, mi, mi != _M_HUESO)
            elif ta == "cara" or (ta == "neu" and tb == "neu"):
                add_face(vs, mat_neu(ua if ta == "neu" else 131.0,
                                     ub if tb == "neu" else 131.0), True)
            elif ta == "neu":            # neumático -> ranura
                add_face(vs, _M_OSC, False)
            elif ta == "ranura":         # ranura -> pared
                add_face(vs, _M_CAL, False)
            else:
                c = (ra[k].co + ra[k2].co + rb[k2].co + rb[k].co) * 0.25
                add_face(vs, mat_roca(c), False)
    # abanico del polo trasero
    rl = rings[-1]
    for k in range(N):
        add_face((v_back, rl[(k + 1) % N], rl[k]), _M_OSC, False)

    info = dict(zc=zc, y_front=y_front, y_back=y_back, y_wall0=y_wall0,
                y_hub=v_hub.co.y)
    return bm, info


def _cerrar_en_suelo(bm):
    """Corta la malla por z=0, elimina lo enterrado y tapa el fondo con un
    n-gon triangulado. Devuelve (n_caras_tapa, n_aristas_no_manifold)."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=(0.0, 0.0, 0.0),
                           plane_no=(0.0, 0.0, 1.0), use_snap_center=False,
                           clear_outer=False, clear_inner=False)
    # borrar explícitamente lo enterrado (independiente de la convención
    # inner/outer del bisect); el corte ya dejó aristas exactas en z=0
    bajo = [v for v in bm.verts if v.co.z < -1e-4]
    if bajo:
        bmesh.ops.delete(bm, geom=bajo, context="VERTS")
    borde = [e for e in bm.edges if e.is_boundary]
    res = bmesh.ops.holes_fill(bm, edges=borde, sides=0)
    tapa = res.get("faces", [])
    for fce in tapa:
        fce.material_index = _M_OSC
        fce.smooth = False
    if tapa:
        bmesh.ops.triangulate(bm, faces=tapa, quad_method="BEAUTY",
                              ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # aristas vivas donde el ángulo entre caras es grande (pared del hueco,
    # pie de los radios, ranura neumático/roca): normales partidas sin
    # modificadores (atributo sharp_edge nativo de Blender 4.1+)
    lim = math.radians(30.0)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    nm = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    return len(tapa), nm


# ============================================================ vegetación ====
def _blob(bm, center, r, sz, rng, mi):
    """Mata low-poly (7x4, 42 tris) en el bmesh dado."""
    u_res, v_res = 7, 4
    rows = []
    for i in range(1, v_res):
        phi = math.pi * i / v_res
        zc_, rc = math.cos(phi), math.sin(phi)
        row = []
        for k in range(u_res):
            th = 2.0 * math.pi * k / u_res + rng.random() * 0.5
            rr = r * (0.72 + 0.55 * rng.random())
            row.append(bm.verts.new((center.x + rc * rr * math.cos(th),
                                     center.y + rc * rr * math.sin(th),
                                     center.z + zc_ * r * sz *
                                     (0.8 + 0.4 * rng.random()))))
        rows.append(row)
    top = bm.verts.new((center.x, center.y, center.z + r * sz))
    bot = bm.verts.new((center.x, center.y, center.z - r * sz * 0.75))
    faces = []
    for k in range(u_res):
        k2 = (k + 1) % u_res
        faces.append(bm.faces.new((top, rows[0][k], rows[0][k2])))
        for i in range(len(rows) - 1):
            faces.append(bm.faces.new((rows[i][k], rows[i + 1][k],
                                       rows[i + 1][k2], rows[i][k2])))
        faces.append(bm.faces.new((bot, rows[-1][k2], rows[-1][k])))
    for fce in faces:
        fce.material_index = mi
        fce.smooth = True


def _pino(bm, base, h, rng, mi_hoja, mi_tronco):
    """Pino mediterráneo low-poly (78 tris) en UNA sola cáscara cerrada:
    tronco octogonal -> copa inferior -> copa superior -> ápice (anillos de
    8 vértices puenteados). `base` en el suelo (el tronco se hunde 0.4 m)."""
    def anillo(r, z, ph=0.0):
        return [bm.verts.new((base.x + r * math.cos(2 * math.pi * k / 8 + ph),
                              base.y + r * math.sin(2 * math.pi * k / 8 + ph),
                              z)) for k in range(8)]

    def puente(ra, rb, mi):
        for k in range(8):
            fce = bm.faces.new((ra[k], ra[(k + 1) % 8], rb[(k + 1) % 8], rb[k]))
            fce.material_index = mi
            fce.smooth = False

    rt = 0.055 * h
    r1 = 0.30 * h * (0.9 + 0.2 * rng.random())
    r2 = 0.22 * h * (0.9 + 0.2 * rng.random())
    a0 = anillo(rt, base.z - 0.4)                    # pie del tronco
    a1 = anillo(rt * 0.8, base.z + 0.34 * h)         # cuello del tronco
    a2 = anillo(r1, base.z + 0.28 * h, 0.2)          # base copa inferior
    a3 = anillo(0.38 * r1, base.z + 0.55 * h, 0.2)   # cintura
    a4 = anillo(r2, base.z + 0.53 * h, 0.6)          # base copa superior
    apex = bm.verts.new((base.x + 0.03 * h * rng.uniform(-1, 1),
                         base.y + 0.03 * h * rng.uniform(-1, 1), base.z + h))
    cap = bm.faces.new(a0[::-1])
    cap.material_index = mi_tronco
    cap.smooth = False
    puente(a0, a1, mi_tronco)
    puente(a1, a2, mi_hoja)
    puente(a2, a3, mi_hoja)
    puente(a3, a4, mi_hoja)
    for k in range(8):
        fce = bm.faces.new((a4[k], a4[(k + 1) % 8], apex))
        fce.material_index = mi_hoja
        fce.smooth = False


def _malla_veg(nombre, bm_veg, parent_collection, parent_obj):
    bmesh.ops.recalc_face_normals(bm_veg, faces=bm_veg.faces)
    me = bpy.data.meshes.new(nombre)
    bm_veg.to_mesh(me)
    bm_veg.free()
    me.validate()
    for mt in _mats_veg():
        me.materials.append(mt)
    obj = bpy.data.objects.new(nombre, me)
    parent_collection.objects.link(obj)
    obj.parent = parent_obj
    return obj


def _vegetacion_roca(parent_collection, roca_obj, R, info, tree, seed,
                     n_max=40):
    """Matas GRANDES (r 3.5-6.5 m) agrupadas en repisas de la pared, en el
    espolón y en el lomo, más unos pinos en lo alto, como en el fotograma.
    Cada mata se apoya por ray-cast vertical sobre la malla final (nunca
    flota). Malla aparte MRUEDA_veg."""
    rng = random.Random(seed * 91 + 101)
    zc = info["zc"]
    y_wall0 = info["y_wall0"]
    bm = bmesh.new()
    placed = []
    cnt = [0]

    def sonda(x, y, z_desde):
        loc, nrm, _i, _d = tree.ray_cast(Vector((x, y, z_desde)),
                                         Vector((0.0, 0.0, -1.0)), 6.0 * R)
        return loc, nrm

    def mata(loc, nrm, r):
        if any((loc - p).length < 4.0 for p in placed):
            return False
        placed.append(loc.copy())
        c = loc + nrm * (0.15 * r)
        _blob(bm, c, r, 0.55, rng, 0 if rng.random() < 0.65 else 1)
        cnt[0] += 1
        return True

    def grupo(xc, yc, zl, hw, n_here, r_rng, z_desde, min_nz=0.35, pinos=0):
        n = 0
        for _ in range(30):
            if n >= n_here or cnt[0] >= n_max:
                break
            x = xc + rng.uniform(-hw, hw)
            y = yc + rng.uniform(-2.0, 5.0)
            loc, nrm = sonda(x, y, z_desde)
            if loc is None or nrm.z < min_nz or loc.z < zl - 9.0 or loc.z < 3.0:
                continue
            if mata(loc, nrm, rng.uniform(*r_rng)):
                n += 1
        for _ in range(pinos):
            for _t in range(10):
                x = xc + rng.uniform(-hw, hw)
                y = yc + rng.uniform(-3.0, 3.0)
                loc, nrm = sonda(x, y, z_desde)
                if loc is not None and nrm.z > 0.55 and loc.z > 3.0 and \
                        loc.z > zl - 9.0:
                    _pino(bm, loc, rng.uniform(14.0, 20.0), rng,
                          0 if rng.random() < 0.5 else 1, 2)
                    break

    # repisas explícitas de la pared (frente de la repisa ~ y_pared + 3 m)
    for xc, zl, hw in _REPISAS:
        yc = y_wall0 - _LEAN * (zl * R - zc) + 1.6
        grupo(xc * R, yc, zl * R, 0.8 * hw * R, 7, (3.5, 6.0), zl * R + 25.0,
              pinos=1 if zl > 1.5 else 0)
    # espolón izquierdo (lomo inclinado)
    grupo(_ESP_XC * R, y_wall0 + 0.30 * R, 0.20 * R, 0.55 * _ESP_HW * R, 6,
          (3.5, 5.5), 1.2 * R)
    # lomo/cresta trasera
    for _ in range(3):
        xc = rng.uniform(-0.55, 0.55) * R
        yc = rng.uniform(y_wall0 - 12.0, y_wall0 - 45.0)
        grupo(xc, yc, 0.5 * R, 9.0, 4, (4.0, 6.5), 3.0 * R, min_nz=0.55,
              pinos=1)
    return _malla_veg("MRUEDA_veg", bm, parent_collection, roca_obj)


# ================================================================= build ====
def build(parent_collection, radio=55.0, espesor=70.0, alto_base=12.0,
          seed=0, n_radios=20, con_vegetacion=True, con_espolon=True,
          **params):
    """Montaña-rueda completa. Devuelve la malla raíz MRUEDA_roca (única y
    cerrada); la vegetación va en el hijo MRUEDA_veg."""
    R = float(radio)
    n_radios = int(n_radios)
    m = params.get("segmentos_por_radio")
    if m is None:
        m = max(8, int(round(200.0 / n_radios)))
    m = max(8, int(m))
    bm, info = _geometria_roca(R, float(espesor), float(alto_base), seed,
                               n_radios, m, bool(con_espolon))
    n_tapa, n_nm = _cerrar_en_suelo(bm)
    tree = BVHTree.FromBMesh(bm) if con_vegetacion else None
    me = bpy.data.meshes.new("MRUEDA_roca")
    bm.to_mesh(me)
    bm.free()
    me.validate()
    for mt in _mats_roca():
        me.materials.append(mt)
    me["mrueda_tapa_caras"] = n_tapa
    me["mrueda_no_manifold"] = n_nm
    obj = bpy.data.objects.new("MRUEDA_roca", me)
    obj["radio"] = R
    obj["espesor"] = float(espesor)
    obj["alto_base"] = float(alto_base)
    obj["centro_buje"] = (0.0, info["y_hub"], info["zc"])
    obj["y_pared"] = info["y_wall0"]
    suelo = [v.co.x for v in me.vertices if abs(v.co.z) < 1e-3]
    obj["huella_x"] = (min(suelo), max(suelo)) if suelo else (0.0, 0.0)
    esp = [v.co for v in me.vertices
           if v.co.x < -0.9 * R and v.co.y > info["y_wall0"] + 8.0]
    if esp:
        obj["espolon"] = (min(c.x for c in esp), max(c.x for c in esp),
                          max(c.y for c in esp), max(c.z for c in esp))
    else:
        obj["espolon"] = ()
    parent_collection.objects.link(obj)

    if con_vegetacion:
        _vegetacion_roca(parent_collection, obj, R, info, tree, seed)
    return obj


# ============================================================ arco de roca ==
_UW = 0.24        # fracción del recorrido que es pata (cada lado)
_Z_BASE = -2.6    # faldón enterrado bajo el suelo


def _perfil_arco(u, w_in, z_spring, h_top, lean):
    """Punto (x, z) del borde interior del hueco. u=0 base izq, 1 base dcha."""
    if u < _UW:
        t = u / _UW
        return -(w_in + lean * (1.0 - t) ** 1.5), \
            _Z_BASE + (z_spring - _Z_BASE) * t
    if u > 1.0 - _UW:
        t = (1.0 - u) / _UW
        return (w_in + lean * (1.0 - t) ** 1.5), \
            _Z_BASE + (z_spring - _Z_BASE) * t
    s = (u - _UW) / (1.0 - 2.0 * _UW)
    return -w_in * math.cos(math.pi * s), \
        z_spring + (h_top - z_spring) * math.sin(math.pi * s)


def _clamp_galibo(x, z, hw, hh):
    """Proyecta fuera de la caja de gálibo [-hw,hw] x [0,hh] (todo Y)."""
    if 0.0 < z < hh and abs(x) < hw:
        if (hw - abs(x)) <= (hh - z):
            x = math.copysign(hw, x if x != 0.0 else 1.0)
        else:
            z = hh
    return x, z


def _geometria_arco(luz, alto, grosor, seed):
    """bmesh del arco: tubo loft de sección superelíptica IRREGULAR (exponente
    por anillo) barrido por el perfil pata-arco-pata; patas que se ensanchan
    hacia fuera de forma continua (sin escalón), clave gruesa con cresta
    rota, relieve de roca (ridged + bloques + estratos) y sombreado plano.
    Sin bolos: una sola cáscara sin auto-intersecciones. Devuelve
    (bm, cands, (hw, hh))."""
    so = seed * 11.91 + 5.3
    w_in = luz * 0.5 + 1.2
    z_spring = alto * 0.55
    h_top = alto + 2.5
    lean = 0.5
    hw, hh = luz * 0.5 + 0.3, alto + 0.3
    a_crown = max(3.5, 0.44 * alto)          # semiespesor radial en clave
    a_base = max(a_crown * 1.35, luz * 0.45)  # ... en las patas (macizas)
    b_crown = grosor * 0.5                    # semianchura en Y en clave
    b_base = grosor * 0.5 * 1.5               # patas más profundas
    band_h = 4.6                              # > tamaño de quad (sin damero)
    n_st, n_ring = 52, 28
    eps = 0.004

    bm = bmesh.new()
    rings, cands = [], []
    for j in range(n_st):
        u = j / (n_st - 1.0)
        px, pz = _perfil_arco(u, w_in, z_spring, h_top, lean)
        x2, z2 = _perfil_arco(min(u + eps, 1.0), w_in, z_spring, h_top, lean)
        x1, z1 = _perfil_arco(max(u - eps, 0.0), w_in, z_spring, h_top, lean)
        tx, tz = x2 - x1, z2 - z1
        tl = math.hypot(tx, tz) or 1.0
        tx, tz = tx / tl, tz / tl
        nx, nz = -tz, tx                     # normal hacia FUERA del hueco
        pn = max(0.0, 1.0 * _n3(u * 3.1 + so * 1.3, 0.0, 3.3))
        px += nx * pn
        pz += nz * pn
        d_end = min(u, 1.0 - u)
        f = _sstep((0.40 - d_end) / 0.40)
        flare = 1.0 + 0.18 * _sstep((0.22 - d_end) / 0.22) ** 1.5
        a = (a_crown + (a_base - a_crown) * f ** 1.2) * flare * \
            (1.0 + 0.10 * _n3(u * 4.1 + so, 1.3, 7.7))
        b = (b_crown + (b_base - b_crown) * f ** 1.2) * \
            (1.0 + 0.15 * _n3(u * 3.3 + so * 2.2, 5.1, 2.9))
        qr = max(2.3, 3.3 + 1.3 * _n3(u * 5.0 + so, 2.0, 6.0))
        cx, cz = px + nx * a, pz + nz * a
        ring = []
        for k in range(n_ring):
            ph = 2.0 * math.pi * (k + 0.5) / n_ring
            cs, sn = _sq(math.cos(ph), qr), _sq(math.sin(ph), qr)
            wx = cx + nx * a * cs
            wz = cz + nz * a * cs
            wy = b * sn
            nrm = Vector((nx * cs, sn, nz * cs))
            if nrm.length < 1e-6:
                nrm = Vector((nx, 0.0, nz))
            nrm.normalize()
            ampf = 0.30 + 0.70 * _sstep((cs + 0.95) / 0.9)   # cara interior lisa
            zq = max(wz, 0.8)
            d = (0.28 * _ridged(wx, wy, zq, so, k=3.0) +
                 0.60 * _celda(wx, wy, zq, so, 4.5, 6.0)) * ampf
            d += 0.60 * math.tanh(2.5 * _onda_estrato(
                zq, band_h, 0.6 * _n3(wx * 0.05 + so, wy * 0.05, 4.4))) * ampf
            wx += nrm.x * d
            wy += nrm.y * d
            wz += nrm.z * d
            if nrm.z > 0.3 and 0.26 < u < 0.74:            # cresta rota en clave
                cr = 1.0 - abs(_n3(wx * 0.22 + so * 4.7, wy * 0.22, 8.8))
                wz += 2.2 * cr * cr * nrm.z * _sstep((wz - hh - 2.0) / 3.0)
            wx, wz = _clamp_galibo(wx, wz, hw, hh)
            wz = max(wz, _Z_BASE)
            v = bm.verts.new((wx, wy, wz))
            ring.append(v)
            if wz > 2.0:
                cands.append((Vector((wx, wy, wz)), nrm.copy(), cs, sn))
        rings.append(ring)

    def add_face(vs):
        try:
            fce = bm.faces.new(vs)
        except ValueError:
            return
        c = Vector((0.0, 0.0, 0.0))
        for v in vs:
            c += v.co
        c /= len(vs)
        if c.z < 1.0:
            fce.material_index = _M_OSC
        else:
            fce.material_index = _estrato_mat(
                c.z, band_h, 0.6 * _n3(c.x * 0.05 + so, c.y * 0.05, 4.4))
        fce.smooth = False

    for ra, rb in zip(rings, rings[1:]):
        for k in range(n_ring):
            k2 = (k + 1) % n_ring
            add_face((ra[k], ra[k2], rb[k2], rb[k]))
    for ring, uu in ((rings[0], 0.0), (rings[-1], 1.0)):
        px, pz = _perfil_arco(uu, w_in, z_spring, h_top, lean)
        pole = bm.verts.new((px + math.copysign(a_base * 1.3, px), 0.0,
                             _Z_BASE - 1.2))
        for k in range(n_ring):
            k2 = (k + 1) % n_ring
            if uu == 0.0:
                add_face((pole, ring[k], ring[k2]))
            else:
                add_face((pole, ring[k2], ring[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, cands, (hw, hh)


def build_arco(parent_collection, luz=16.0, alto=13.0, grosor=6.0, seed=0,
               con_vegetacion=True, **kw):
    """Arco natural de roca MRUEDA_arco (<= 6k tris). Origen en el centro
    del hueco a nivel de suelo; la carretera pasa por debajo a lo largo de Y
    con gálibo libre garantizado luz x alto."""
    bm, cands, (hw, hh) = _geometria_arco(float(luz), float(alto),
                                          float(grosor), seed)
    me = bpy.data.meshes.new("MRUEDA_arco")
    bm.to_mesh(me)
    bm.free()
    me.validate()
    for mt in _mats_roca():
        me.materials.append(mt)
    obj = bpy.data.objects.new("MRUEDA_arco", me)
    obj["luz"] = float(luz)
    obj["alto"] = float(alto)
    parent_collection.objects.link(obj)

    if con_vegetacion:
        rng = random.Random(seed * 91 + 7)
        hangs = [c for c in cands
                 if abs(c[3]) > 0.6 and c[1].z > -0.2 and c[0].z > alto + 1.5]
        sits = [c for c in cands if c[1].z > 0.55 and c[0].z > 3.0]
        rng.shuffle(hangs)
        rng.shuffle(sits)
        bmv = bmesh.new()
        placed = []

        def ok(center, r, sz):
            zmin = center.z - r * sz * 0.95 - 0.3
            return not (abs(center.x) - 1.4 * r < hw and zmin < hh + 0.3)

        def place(pool, count, offset_fn, r_rng, sz):
            n = 0
            for pos, nrm, _cs, _sn in pool:
                if n >= count:
                    break
                r = rng.uniform(*r_rng)
                center = offset_fn(pos, nrm, r)
                if not ok(center, r, sz):
                    continue
                if any((center - p).length < 4.5 for p in placed):
                    continue
                placed.append(center)
                _blob(bmv, center, r, sz, rng, 0 if rng.random() < 0.6 else 1)
                n += 1

        place(hangs, 5,
              lambda p, nm, r: p - nm * (0.35 * r) - Vector((0, 0, r * 0.45)),
              (1.2, 2.0), 1.3)
        place(sits, 5,
              lambda p, nm, r: p + nm * 0.05 - Vector((0, 0, r * 0.38)),
              (1.4, 2.4), 0.62)
        _malla_veg("MRUEDA_arco_veg", bmv, parent_collection, obj)
    return obj
