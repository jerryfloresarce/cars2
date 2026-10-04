"""roca_lazo.py - ROCA DEL LAZO (Porto Corsa, Cars 2) para Blender 5.1.

La U del viaducto (curvas 42 -> 43 -> 44) rodea una roca NATURAL que el
ingeniero uso de apoyo interior del tablero: la calzada va PEGADA a una pared
de caliza estratificada que arranca 0.6 m mas alla del borde interior del
tablero (a z_tablero - 0.3) con una berma de cuneta de ~3.4 m que sube 0.9 m
(asi ningun vertice de la rejilla asoma sobre la calzada), sube a 75 grados
los primeros 7 m y sigue en bancos de ~12 m con cornisas hasta la ladera
natural (perfil ondulado continuo, talud 77 / cornisa 17 grados); bajo el tablero la roca sigue
hasta el mar (el tablero apoya en la roca por dentro y en pilas/arcos por
fuera). Arriba, una PLAZA irregular empedrada con campanile, fuente, casas y
pinos (y un cerrete rocoso al lado: sin tapa plana). En la ladera abierta
(NE, hacia donde viene el viaducto largo) hay dos TERRAZAS talladas siguiendo
las curvas de nivel (frente ENDEREZADO sin horquillas y suavizado; repisa
llana >= 14 m rellenando barrancos; paredon a 75 grados detras y talud de
apoyo a 75 grados delante) con casas, escaleras de piedra que las unen con la
cumbre y con la pista (rellano con VALLA y puerta junto al tablero), y la roca
se cierra con un ESPOLON natural que baja al mar y una CALA de pescadores con
muelle, pantalan de madera, barcas y casitas (senda T1 -> muelle oblicua a lo
largo del acantilado, <= 34 grados).
CARRETERAS (H2-5, 'un coche podria ir a todos los sitios'): dos calzadas de 4 m
con pretil de piedra salen de la pista por una boca de 6.4 m con valla CERRADA
(caminos_kit.build_valla_cierre, como los enlaces del plan urbano): 'acceso_alto'
(sustituye a la escalera del paso alto) cruza el collado en desmonte hasta una
piazzola pavimentada en el extremo de la terraza alta; 'acceso_cala' sale al
final del lazo, rodea el lobulo NE como litoranea (curva de nivel de la
rasante + 1 m) y acaba en una piazzola de giro en el extremo O del muelle. La
terraza baja y la plaza siguen siendo peatonales (escaleras).

API
  build(parent_collection, muestras, z_mar, seed, casas_kit=None,
        vegetacion_kit=None, italiano_kit=None, yates_kit=None, **params)
      -> (raiz Empty 'PENON_puente', info)
  muestras: lista de dicts {x, y, z, nx, ny, w} de la pista (cada 2 m) desde
      curva 42 - 25 muestras hasta curva 44 + 10. n es la normal IZQUIERDA de
      la marcha; el lado interior (hacia la roca) se deduce del centro.
  params opcionales:
      muestras_contexto=(antes, despues): muestras de pista anteriores y
          posteriores al tramo; solo sirven para que la roca baje bajo el
          tablero mas alla del tramo (sin ellas se extrapola 40 m).
      cell=1.0 (m, rejilla), z_cumbre=106, R_cumbre=150, r_cala=150, log=print,
      talud_bajo_tablero_deg=70 (pendiente de la roca bajo el tablero hasta
          el mar; 80 si se quiere que la falda asome menos por fuera del
          borde exterior y se vean los arcos).
  info: {'centro_top': (x, y), 'z_top', 'z_cumbre', 'plaza': {...},
         'terrazas': [...], 'puertas': [...], 'cala': {...},
         'entrada': (x, y, z) (muelle de la cala), 'casas': [...],
         'tramos': [...], 'carreteras': [...], 'checks': {...}, 'n_tris'}
      puertas[k]['muestra'] es el INDICE EN LA LISTA `muestras` (0..n-1), no
      el s_idx global: el integrador suma el indice de la primera muestra.
      puertas[k]['tipo']: 'escalera' (rellano peatonal de 4.6 m con puerta) o
      'carretera' (boca de 6.4 m de una calzada, sin hoja); 'ancho' = hueco que
      hay que abrir en el pretil del viaducto (y cerrar con cancela).
      v3: en las de ESCALERA la verja ya va EN ese hueco (mitad trasera del
      pretil, postes a >= 0.41 m del asfalto) con una losa de umbral desde
      0.38 m (en PENON_puente_plaza): 'valla' = None (el integrador no la
      mueve ni pone PENON_puente_plaza_rellano), 'verja' = su segmento, 'losa'
      = su poligono. En las de CARRETERA 'valla' es la valla de cierre.
      carreteras[k]: eje [(x, y, z)], largo, pend_max, radio_min, piazzola
      (filas) o piazzola_disco (cx, cy, r), z_piazzola, terraza.
      params: caminos_kit=None (si no, sys.modules['caminos_kit']) para la valla
      de cierre; carretera_cala=True; coronacion_v3=True (v3 N2; False = el
      perfil de corte y la roca de antes, solo para comparar); debug_dump.
  Hijos de la raiz (mallas en coordenadas de mundo, raiz en el origen):
      PENON_puente_roca (malla unica, heightfield con cara de contacto),
      PENON_puente_muros, PENON_puente_escaleras, PENON_puente_plaza,
      PENON_puente_campanile, PENON_puente_vallas, PENON_puente_muelle,
      PENON_puente_barcas, PENON_puente_matas, PENON_carretera_lazo (calzadas y
      piazzolas: 1ROAD_ en el kn5; los pretiles van en PENON_puente_muros) y
      CAMINO_valla_lazo_<acceso> (vallas de cierre: 1WALL_) + objetos de los
      kits (casas CASAS_lazo_NN, VEG_*, ITAL_*, YATE_*) con parent = raiz.

URBANISMO SIN SOLAPES: las casas se colocan con su huella REAL (casas_kit_v2
anade 0.42 m de alero por lado y 1.0 m de balcones/toldos delante), a >= 1.5
m entre si (rectangulos girados, eje separador), fuera de los circulos de
escaleras/rellanos/fuente/campanile, con la trasera a >= 1.5 m del paredon
(roca comprobada a 1.5 m detras) y, en la plaza, a >= 2.5 m del parapeto.
Los muros de las terrazas y el muro trasero de la cala se abren donde los
cruza una escalera; los codos de los zigzag llevan losa de rellano. Los
arboles se asientan por ray-cast sobre la roca y no entran en las casas.

COMPROBACIONES (build las imprime y las devuelve en info['checks'];
info['checks']['ok'] exige TODAS):
  - rayos verticales sobre el tablero en cada muestra, a -(w/2+1), 0 y
    +(w/2+1) del eje, desde z=+400 hasta la cota del tablero (+0.05): 0
    impactos (bajo el tablero la roca SI sigue: lo sostiene por dentro).
  - contacto: rayo horizontal desde el borde interior a z_tablero-0.7 (dentro
    del faldon del tablero) hacia la roca: distancia < 0.8 m en > 90 %.
  - casas: ray-cast en 9 puntos de la huella + 4 esquinas reales (roca
    <= base + 0.25, >= base - 0.6) y 3 puntos a 1.5 m detras (<= base + 0.3);
    en planta 0 huellas cruzadas y 0 pares a < 1.5 m; por BVH 0 solapes
    casa-casa y casa-obra (muros, escaleras, vallas, campanile, muelle).
  - escaleras x muros/muelle: 0 pares de poligonos (BVH overlap).
  - vegetacion: roca en el pivote a [-0.6, +0.5] m de la base.
  - puertas: la hoja abierta se aleja del borde del tablero (hacia el rellano).
  - matas: 0 con mas de 0.3 m de hueco bajo algun vertice de su mitad
    inferior (rayo vertical a la roca) y 0 pares mata x obra/casas (BVH);
    cada mata va en el plano tangente de la ladera, medio enterrada, y se
    hunde, se reduce o se descarta.
  - roca: 0 aristas abiertas por encima de z_mar (anillo a z_fondo) y < 2 %
    de limites de material 'verticales' en cara empinada.
  - orientacion (H2-1, en AC hay culling de caras traseras): la roca con
    volumen con signo > 0 (respecto a z_fondo), < 1 % del techo boca abajo y
    < 1 % de normales de esquina opuestas a su cara; ninguna otra malla
    PENON_* con el techo boca abajo. La roca NO pasa por recalc_face_normals
    (malla abierta: elegia el sentido hacia dentro); si el volumen saliera
    negativo, _orientar_fuera le da la vuelta antes de _fijar_normales.
  - carreteras: pendiente <= 10 %, radio >= 10 m y 0 roca u obra (muros,
    escaleras, vallas, plaza, campanile, muelle, casas) encima de la calzada
    y de la piazzola (rayos en el eje y a +-1.8 m).
  - v3 nada junto al asfalto (como _rev/nada_en_pista.py): 0 vertices de lo
    que cuelga de la raiz (salvo la roca) a < w/2 + 0.3 m de la muestra de
    pista mas cercana y entre z - 0.3 y z + 5.5 (checks['cerca_asfalto_n'];
    'cerca_asfalto_margen' da el margen de lo que queda a < 1.5 m).

CORONACION (v3 N2): donde el corte de la pista es poco hondo (el macizo
a < 6 m sobre la cara lisa) las cornisas de los estratos se desvanecen y el
encuentro corte/macizo es un minimo suave (k 2.5 m, solo a o > o_b + 4): sin
repisas que mueren en el domo como 'cuencos'. Las cuencas cerradas de la
roca natural (o > 8, fuera de lo llano) se rellenan hasta su desague.

ESTRATOS: el material de la roca va por cara (en AC cada material es un
color plano), pero los triangulos que cruzan un limite se PARTEN por la
isolinea (marching triangles, malla cerrada): las bandas van por COTA
respecto al tablero (kz, cornisa en kz entero), asi que en las caras de 75
grados los limites son lineas horizontales, sin dientes de sierra. Fuera
del corte: manchas de ruido 2D (isolinea, no por celda) en lo tendido y
color uniforme en lo empinado. info['puertas'][k] trae 'lado' (signo del
lado de la puerta respecto a n) y 'ancho' (hueco del rellano a lo largo de
la pista) para abrir el pretil del viaducto.

Materiales: MAT_PPUEBLO_roca / _roca_clara / _roca_oscura / _repisa (familia
roca de aplicar_texturas.py), MAT_PPUEBLO_piedra_* (familia piedra),
MAT_CIVICO_campanile_lazo (estuco) / _teja (teja). Sin bpy.ops. Metros.
"""
import json
import math
import random
import sys

import numpy as np
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TAN75 = 3.732
Z_FONDO_REL = -6.0          # la roca se corta a z_mar + Z_FONDO_REL (bajo el fondo del mar)

# ----------------------------------------------------------------- materiales
_PALETA = {
    'roca':            ((0.46, 0.39, 0.28), 0.95),
    'roca_clara':      ((0.62, 0.55, 0.42), 0.95),
    'roca_oscura':     ((0.29, 0.24, 0.17), 0.96),
    'repisa':          ((0.42, 0.37, 0.27), 0.95),
    'piedra_muro':     ((0.68, 0.62, 0.50), 0.90),
    'piedra_escalera': ((0.74, 0.68, 0.56), 0.88),
    'piedra_plaza':    ((0.62, 0.57, 0.47), 0.85),
    'piedra_plaza_b':  ((0.54, 0.49, 0.40), 0.85),
    'piedra_muelle':   ((0.60, 0.56, 0.48), 0.90),
    'piedra_calzada':  ((0.36, 0.34, 0.31), 0.92),
    'hierro':          ((0.07, 0.07, 0.08), 0.55),
    'madera':          ((0.40, 0.26, 0.14), 0.75),
    'mata':            ((0.09, 0.26, 0.08), 0.92),
    'mata_clara':      ((0.18, 0.38, 0.12), 0.92),
    'barca_azul':      ((0.10, 0.30, 0.65), 0.45),
    'barca_roja':      ((0.72, 0.15, 0.10), 0.45),
    'barca_blanca':    ((0.90, 0.90, 0.85), 0.45),
    'barca_verde':     ((0.15, 0.45, 0.25), 0.45),
    'bronce':          ((0.55, 0.40, 0.18), 0.40),
    'campanile_estuco': ((0.86, 0.66, 0.50), 0.85),
    'campanile_teja':   ((0.62, 0.30, 0.18), 0.80),
    'campanile_piedra': ((0.70, 0.64, 0.52), 0.85),
}
_NOMBRES = {'campanile_estuco': 'MAT_CIVICO_campanile_lazo',
            'campanile_teja': 'MAT_CIVICO_campanile_lazo_teja',
            'campanile_piedra': 'MAT_CIVICO_campanile_lazo_piedra'}


def _mat(clave):
    nombre = _NOMBRES.get(clave, 'MAT_PPUEBLO_' + clave)
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    if bs is not None:
        bs.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
        bs.inputs['Roughness'].default_value = rough
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


class _Malla:
    """Acumulador de vertices/caras con indice de material por cara."""

    def __init__(self, nombre, claves):
        self.nombre = nombre
        self.v = []
        self.f = []
        self.mi = []
        self.claves = list(claves)

    def vert(self, p):
        self.v.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.v) - 1

    def cara(self, idx, clave):
        idx = [i for k, i in enumerate(idx) if i != idx[k - 1]]
        if len(idx) < 3:
            return
        self.f.append(tuple(idx))
        self.mi.append(self.claves.index(clave))

    def caja(self, c, s, clave, rz=0.0):
        """caja centrada en c (centro de la BASE), tamano s, girada rz."""
        cx, cy, cz = c
        sx, sy, sz = s
        cr, sr = math.cos(rz), math.sin(rz)
        pts = []
        for (dx, dy, dz) in ((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
            lx, ly = dx * sx / 2.0, dy * sy / 2.0
            pts.append(self.vert((cx + lx * cr - ly * sr, cy + lx * sr + ly * cr, cz + dz * sz)))
        a, b, c_, d, e, f, g, h = pts
        for q in ((d, c_, b, a), (e, f, g, h), (a, b, f, e), (b, c_, g, f), (c_, d, h, g), (d, a, e, h)):
            self.cara(q, clave)

    def objeto(self, parent_collection, parent_obj=None, recalc=True, suave=False, orientar=True):
        """recalc: une vertices dobles y (si orientar) recalcula el sentido de las caras. Con
        orientar=False se conserva el sentido de construccion (la roca: el campo de alturas va
        siempre en sentido antihorario visto desde arriba; recalc_face_normals sobre una malla
        ABIERTA lo daba la vuelta, H2-1)."""
        me = bpy.data.meshes.new(self.nombre)
        me.from_pydata(self.v, [], self.f)
        for clave in self.claves:
            me.materials.append(_mat(clave))
        for p, mi in zip(me.polygons, self.mi):
            p.material_index = mi
        me.validate(verbose=False)
        me.update()
        if recalc:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)
            if orientar:
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
            me.update()
        if suave:
            for p in me.polygons:
                p.use_smooth = True
        ob = bpy.data.objects.new(self.nombre, me)
        parent_collection.objects.link(ob)
        if parent_obj is not None:
            ob.parent = parent_obj
        return ob

    def n_tris(self):
        return sum(len(f) - 2 for f in self.f)


# ----------------------------------------------------------------- ruido numpy
def _hash2(ix, iy, seed):
    sd = np.asarray(seed, dtype=np.int64)
    h = (ix * 374761393 + iy * 668265263 + sd * 1442695041) & 0x7fffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0x7fffffff
    return ((h ^ (h >> 16)) & 0xffff) / 65535.0


def _vnoise2(x, y, esc, seed):
    """ruido de valor suave en [-1, 1] con escala esc (m)."""
    fx = np.asarray(x, dtype=np.float64) / esc
    fy = np.asarray(y, dtype=np.float64) / esc
    ix = np.floor(fx).astype(np.int64)
    iy = np.floor(fy).astype(np.int64)
    tx = fx - ix
    ty = fy - iy
    tx = tx * tx * (3.0 - 2.0 * tx)
    ty = ty * ty * (3.0 - 2.0 * ty)
    a = _hash2(ix, iy, seed)
    b = _hash2(ix + 1, iy, seed)
    c = _hash2(ix, iy + 1, seed)
    d = _hash2(ix + 1, iy + 1, seed)
    v = (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty
    return v * 2.0 - 1.0


def _fbm2(x, y, esc, seed, octavas=3, gain=0.5):
    out = 0.0
    amp = 1.0
    tot = 0.0
    e = float(esc)
    for k in range(octavas):
        out = out + amp * _vnoise2(x, y, e, seed + 17 * k)
        tot += amp
        amp *= gain
        e *= 0.5
    return out / tot


def _vnoise3(x, y, z, esc, seed):
    """ruido de valor 3D en [-1, 1] (interpola dos capas 2D en z)."""
    fz = np.asarray(z, dtype=np.float64) / esc
    iz = np.floor(fz).astype(np.int64)
    tz = fz - iz
    tz = tz * tz * (3.0 - 2.0 * tz)
    a = _vnoise2(x, y, esc, seed + 101 * iz)
    b = _vnoise2(x, y, esc, seed + 101 * (iz + 1))
    return a * (1 - tz) + b * tz


# ----------------------------------------------------------------- campo de borde
def _campo_borde(X, Y, B, Zb, Rb, side):
    """Distancia con signo de cada punto a la polilinea del borde interior.
    B: (K,2) puntos del borde; Zb: cota del tablero; Rb: rampa (0 dentro del
    tramo, > 0 mas alla de los extremos). side: +1/-1 (lado de la roca).
    Devuelve o (+ hacia la roca), zt, rampa, dirx/diry (normal hacia la roca
    del tramo mas cercano) y s (abscisa), con la forma de X."""
    px_ = X.ravel()
    py_ = Y.ravel()
    n = len(px_)
    best = np.full(n, 1e18)
    o = np.zeros(n)
    zt = np.zeros(n)
    ra = np.zeros(n)
    dx_ = np.zeros(n)
    dy_ = np.zeros(n)
    ss = np.zeros(n)
    s_acum = 0.0
    for k in range(len(B) - 1):
        ax, ay = B[k]
        bx, by = B[k + 1]
        ddx, ddy = bx - ax, by - ay
        L2 = ddx * ddx + ddy * ddy
        if L2 < 1e-9:
            continue
        L = math.sqrt(L2)
        t = np.clip(((px_ - ax) * ddx + (py_ - ay) * ddy) / L2, 0.0, 1.0)
        ex = px_ - (ax + t * ddx)
        ey = py_ - (ay + t * ddy)
        d2 = ex * ex + ey * ey
        m = d2 < best
        if m.any():
            nx_, ny_ = -ddy / L * side, ddx / L * side
            sgn = np.where(ex * nx_ + ey * ny_ >= 0.0, 1.0, -1.0)
            best[m] = d2[m]
            o[m] = (np.sqrt(d2) * sgn)[m]
            zt[m] = (Zb[k] + t * (Zb[k + 1] - Zb[k]))[m]
            ra[m] = (Rb[k] + t * (Rb[k + 1] - Rb[k]))[m]
            dx_[m] = nx_
            dy_[m] = ny_
            ss[m] = (s_acum + t * L)[m]
        s_acum += L
    shp = X.shape
    return {'o': o.reshape(shp), 'zt': zt.reshape(shp), 'rampa': ra.reshape(shp),
            'dirx': dx_.reshape(shp), 'diry': dy_.reshape(shp), 's': ss.reshape(shp)}


# ----------------------------------------------------------------- macizo
class _Macizo:
    """Suma blanda (norma p) de domos (1 - rho^a)^b * z."""

    def __init__(self, p=8.0):
        self.domos = []
        self.p = p

    def domo(self, cx, cy, z, R, a=2.0, b=2.0):
        self.domos.append((float(cx), float(cy), float(z), float(R), float(a), float(b)))

    def eval(self, X, Y):
        acc = np.zeros(np.shape(X), dtype=np.float64)
        for (cx, cy, z, R, a, b) in self.domos:
            rho = np.clip(np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / R, 0.0, 1.0)
            f = np.clip(1.0 - rho ** a, 0.0, 1.0) ** b * z
            acc += np.maximum(f, 0.0) ** self.p
        return acc ** (1.0 / self.p)


# ----------------------------------------------------------------- rasgos llanos
def _poligono_campo(X, Y, poly):
    """dentro (bool) y distancia al contorno (0 dentro) de un poligono."""
    px_ = X.ravel()
    py_ = Y.ravel()
    n = len(px_)
    dentro = np.zeros(n, dtype=bool)
    best = np.full(n, 1e18)
    K = len(poly)
    for k in range(K):
        ax, ay = poly[k]
        bx, by = poly[(k + 1) % K]
        # cruce par/impar
        cond = (ay > py_) != (by > py_)
        with np.errstate(divide='ignore', invalid='ignore'):
            xi = ax + (py_ - ay) * (bx - ax) / ((by - ay) if by != ay else 1e-12)
        dentro ^= cond & (px_ < xi)
        ddx, ddy = bx - ax, by - ay
        L2 = ddx * ddx + ddy * ddy
        if L2 < 1e-9:
            continue
        t = np.clip(((px_ - ax) * ddx + (py_ - ay) * ddy) / L2, 0.0, 1.0)
        ex = px_ - (ax + t * ddx)
        ey = py_ - (ay + t * ddy)
        best = np.minimum(best, ex * ex + ey * ey)
    d = np.sqrt(best)
    d[dentro] = 0.0
    return dentro.reshape(X.shape), d.reshape(X.shape)


class _Rasgo:
    """Zona llana (o rampa) tallada en la roca: dentro del poligono la cota es
    `nivel` (o nivel_fn(X, Y)); fuera, la roca no puede subir mas de 75 grados
    desde `nivel_corte` (por defecto el nivel) -> paredon tallado."""

    def __init__(self, nombre, poly, nivel, nivel_fn=None, nivel_corte=None, relleno=True, tipo='llano'):
        self.nombre = nombre
        self.poly = [(float(p[0]), float(p[1])) for p in poly]
        self.nivel = float(nivel)
        self.nivel_fn = nivel_fn
        self.nivel_corte = nivel_corte
        self.relleno = relleno
        self.tipo = tipo

    def aplicar(self, X, Y, H):
        dentro, d = _poligono_campo(X, Y, self.poly)
        lvl = self.nivel_fn(X, Y) if self.nivel_fn is not None else np.full(X.shape, self.nivel)
        lc = np.full(X.shape, float(self.nivel_corte)) if self.nivel_corte is not None else lvl
        if self.relleno:
            H = np.where(dentro, lvl, np.minimum(H, lc + TAN75 * d))
        else:
            H = np.where(dentro, np.minimum(H, lvl), np.minimum(H, lc + TAN75 * d))
        return H, dentro


# ----------------------------------------------------------------- perfil de corte
def _bancos(o, ns, o_b):
    """Estratos del perfil de corte: devuelve (k, fr_t, hs) = indice del
    banco, fraccion [0, 1) dentro del banco (cornisa en fr_t ~ 0 / 1, talud
    en 0.5) y altura del banco. Lo usa _perfil_corte (y kb / frb de
    _campo_alturas, informativos). El coloreado por estratos de _malla_roca
    va por COTA (kz = z_e / hs: cornisa en kz entero), no por banco."""
    oo = np.maximum(o - o_b, 0.0)
    hs = 12.0 * (1.0 + 0.25 * ns)
    talud = 4.7                               # 78 grados
    per = hs / talud + 2.4
    u = np.maximum(oo - 1.88, 0.0) + (ns + 1.0) * 1.4
    k = np.floor(u / per)
    fr_t = (u - k * per) / per
    return k, fr_t, hs


def _perfil_corte(o, zt, ns, o_b=3.84, tan_bajo=2.75, rizo=1.0):
    """Cota maxima de la roca a distancia o del borde interior (tablero a zt):
    bajo el tablero (o < 0.6) acantilado de pendiente tan_bajo (70 grados por
    defecto; 5.67 = 80 grados si se quieren ver los arcos); BERMA de contacto
    de 0.6 a o_b (sube solo 0.9 m: el rayo a +1.0 m queda bajo el tablero
    aunque el siguiente vertice de la rejilla caiga en la cara); cara a 75
    grados los primeros 7 m y luego ESTRATOS (talud 78 grados + cornisa)
    desfasados por ns en [-1, 1]. Los estratos son una cara lineal (pendiente
    media ~2.4) + un RIZO senoidal de +-0.14 hs; `rizo` (escalar o campo 0..1)
    lo escala: con 0, cara lisa sin cornisas (v3 N2: cerca de la coronacion)."""
    z_u = zt - 0.3 - (0.6 - o) * tan_bajo
    z_l = zt - 0.3 + 0.9 * (o - 0.6) / (o_b - 0.6)
    oo = np.maximum(o - o_b, 0.0)
    k, fr_t, hs = _bancos(o, ns, o_b)
    # perfil ondulado continuo: pendiente entre 0.3 (cornisa) y 4.5 (talud), sin aristas de celda
    z_e = k * hs + hs * (fr_t - rizo * 0.14 * np.sin(2.0 * math.pi * fr_t))
    z_f = zt + 0.6 + np.where(oo < 1.88, oo * TAN75, 7.0 + z_e)
    return np.where(o < 0.6, z_u, np.where(o < o_b, z_l, z_f))


class _Rejilla:
    def __init__(self, x0, y0, x1, y1, cell):
        self.cell = float(cell)
        self.nx = int(math.ceil((x1 - x0) / cell)) + 1
        self.ny = int(math.ceil((y1 - y0) / cell)) + 1
        self.x0, self.y0 = float(x0), float(y0)
        xs = x0 + np.arange(self.nx) * cell
        ys = y0 + np.arange(self.ny) * cell
        self.X, self.Y = np.meshgrid(xs, ys)          # forma (ny, nx)

    def muestrear(self, F, x, y):
        """interpolacion bilineal de un campo F (ny, nx) en (x, y) escalares o arrays."""
        fx = (np.asarray(x, dtype=np.float64) - self.x0) / self.cell
        fy = (np.asarray(y, dtype=np.float64) - self.y0) / self.cell
        i = np.clip(np.floor(fx).astype(np.int64), 0, self.nx - 2)
        j = np.clip(np.floor(fy).astype(np.int64), 0, self.ny - 2)
        tx = np.clip(fx - i, 0.0, 1.0)
        ty = np.clip(fy - j, 0.0, 1.0)
        return ((F[j, i] * (1 - tx) + F[j, i + 1] * tx) * (1 - ty)
                + (F[j + 1, i] * (1 - tx) + F[j + 1, i + 1] * tx) * ty)


D_RIZO = 6.0          # v3 N2: el rizo de las cornisas crece de 0 a 1 cuando el macizo esta de 0 a D_RIZO m sobre la cara lisa
K_CORONA = 2.5        # v3 N2: radio (m) del minimo suave macizo / corte en la coronacion (lejos del tablero)


def _rellenar_cuencas(H, salida, max_it=4000):
    """cota de agua de cada celda (relleno de depresiones por reconstruccion por erosion, 8 vecinos): W >= H, W = H en
    las celdas de `salida` y en todo lo que desagua; en una cuenca cerrada, la cota de su desague."""
    ny, nx = H.shape
    W = np.where(salida, H, float(H.max()) + 1.0)
    for _ in range(max_it):
        p = np.pad(W, 1, mode='edge')
        e = W.copy()
        for dj in (0, 1, 2):
            for di in (0, 1, 2):
                if dj == 1 and di == 1:
                    continue
                np.minimum(e, p[dj:dj + ny, di:di + nx], out=e)
        nuevo = np.where(salida, H, np.maximum(H, e))
        if np.array_equal(nuevo, W):
            break
        W = nuevo
    return W


def _campo_alturas(G, cb, M, rasgos, z_mar, seed, tan_bajo=2.75, coronacion_v3=True):
    """H = min(macizo, corte de la pista) + rasgos llanos; ajuste de los
    vertices al contacto (o = 0.6) y desplazamiento rocoso enmascarado.
    Devuelve dict con Xd, Yd, H (desplazados), H0 (sin desplazar), llano,
    valido, o, kb (banco del estrato por vertice: >= 0 en la cara de corte,
    -1 en la berma, -2 roca natural / bajo el tablero), frb (fraccion
    dentro del banco), zt (cota del tablero mas cercano), ns (desfase de los
    bancos), corte (cota del perfil de corte) y relleno (v3 N2: cuencas
    rellenas, m)."""
    X, Y, cell = G.X, G.Y, G.cell
    o, zt, ra = cb['o'], cb['zt'], cb['rampa']
    ns = _fbm2(cb['s'], np.zeros_like(X) + 7.0, 30.0, seed + 9, 2)
    o_b = 1.2 + 2.2 * cell
    rec = np.clip(_fbm2(X, Y, 22.0, seed + 11, 2), 0.0, 1.0) * 1.0 * np.clip((o - o_b - 1.5) / 8.0, 0.0, 1.0)
    corte_esc = _perfil_corte(o - rec, zt, ns, o_b, tan_bajo) - ra

    def _rasgos(Hin):
        lla_ = np.zeros(X.shape, dtype=bool)
        for r in rasgos:
            if isinstance(r, _RasgoNivel):
                Hin, dentro = r.aplicar(X, Y, Hin, o, llano_prev=lla_)
            else:
                Hin, dentro = r.aplicar(X, Y, Hin)
            lla_ |= dentro
        return Hin, lla_

    # v3 (N2, 'cuencos' en la ladera alta): donde el corte es POCO HONDO (coronacion: macizo < D_RIZO sobre la cara
    # lisa) las cornisas se desvanecen (rizo -> 0, smoothstep): ya no quedan repisas casi llanas que mueren en el domo
    # como rebajes con labio. Donde el corte es hondo (el acantilado de verdad) los estratos no cambian, y en los
    # primeros o_b + 1.88 m (berma y cara de 7 m, contacto con el tablero) el perfil no tiene rizo: identico.
    corte_lin = _perfil_corte(o - rec, zt, ns, o_b, tan_bajo, rizo=0.0) - ra
    t_r = np.clip((M - corte_lin) / D_RIZO, 0.0, 1.0) if coronacion_v3 else np.ones_like(M)
    corte = corte_lin + t_r * t_r * (3.0 - 2.0 * t_r) * (corte_esc - corte_lin)
    kb, frb, _hs = _bancos(o - rec, ns, o_b)
    en_corte = (corte <= M + 0.05) & (ra <= 0.5)
    kb = np.where(en_corte & (o - rec > o_b + 1.88), kb, -2.0)
    kb = np.where(en_corte & (o > 0.6) & (o - rec <= o_b + 1.88), -1.0, kb)
    # coronacion redondeada: minimo SUAVE (k = K_CORONA) entre macizo y corte, solo lejos del tablero (peso 0 a
    # o < o_b + 4, 1 desde o_b + 8): el contacto y la berma siguen siendo min() exacto
    H = np.minimum(M, corte)
    w_s = np.clip((o - o_b - 4.0) / 4.0, 0.0, 1.0) * (1.0 if coronacion_v3 else 0.0)
    suave = -K_CORONA * np.logaddexp(-M / K_CORONA, -corte / K_CORONA)
    H = H - w_s * (H - suave)
    H, llano = _rasgos(H)
    z_fondo = z_mar + Z_FONDO_REL
    # vertices pegados al contacto: exactamente a o = 0.6 y z = zt - 0.3
    snap = (np.abs(o - 0.6) <= cell * 0.5) & (ra <= 0.0) & (~llano)
    Xd = np.where(snap, X - (o - 0.6) * cb['dirx'], X)
    Yd = np.where(snap, Y - (o - 0.6) * cb['diry'], Y)
    H = np.where(snap, zt - 0.3, H)
    H0 = H.copy()
    # desplazamiento rocoso a lo largo de la normal, lejos del tablero y de lo llano
    lla = llano.copy()
    for _ in range(2):
        lla = lla | np.roll(lla, 1, 0) | np.roll(lla, -1, 0) | np.roll(lla, 1, 1) | np.roll(lla, -1, 1)
    gy, gx = np.gradient(H, cell)
    nrm = np.sqrt(gx * gx + gy * gy + 1.0)
    nx_, ny_, nz_ = -gx / nrm, -gy / nrm, 1.0 / nrm
    masc = np.clip((o - o_b - 1.0) / 6.0, 0.0, 1.0) * (~lla) * (~snap) * (H > z_mar - 1.0) * (0.35 + 0.65 * nz_)
    d = (1.1 * _vnoise3(X, Y, H, 9.0, seed + 21) + 0.45 * _vnoise3(X, Y, H, 3.5, seed + 23)) * masc
    Xd = Xd + nx_ * d
    Yd = Yd + ny_ * d
    H = H + nz_ * d
    H = np.maximum(H, z_fondo)
    H0 = np.maximum(H0, z_fondo)
    # v3 (N2): ninguna CUENCA cerrada en la roca natural (hoyos del ruido del macizo y del desplazamiento, 'crateres
    # sin sentido'): se rellenan hasta su desague (borde de la rejilla y el mar), solo lejos del tablero (o > 8) y
    # fuera de lo llano (dilatado 3 celdas: plaza, terrazas, rellanos, escaleras y carreteras no cambian)
    lla_c = llano.copy()
    for _ in range(3):
        lla_c = _dilatar(lla_c)
    salida = H <= z_mar + 0.3
    salida[0, :] = True
    salida[-1, :] = True
    salida[:, 0] = True
    salida[:, -1] = True
    W_c = _rellenar_cuencas(H, salida)
    dz_c = np.where((~lla_c) & (o > 8.0) & coronacion_v3, np.maximum(W_c - H, 0.0), 0.0)
    H = H + dz_c
    en_c = (corte <= M + 0.05) & (o > o_b + 1.88)
    info_n2 = {'celdas_rellenas': int((dz_c > 0.01).sum()), 'relleno_max': round(float(dz_c.max()), 2),
               'cuencas_en_llano_0.5': int(((W_c - H) > 0.5).sum()),
               'corte_con_rizo_reducido_pct': round(100.0 * float((t_r[en_c] < 1.0).mean()) if en_c.any() else 0.0, 1),
               'corona_suave_max': round(float((w_s * (np.minimum(M, corte) - suave)).max()), 2)}
    valido = H > z_fondo + 0.02
    # zt / ns / corte: para el coloreado por estratos de _malla_roca (coordenada de COTA kz)
    return {'Xd': Xd, 'Yd': Yd, 'H': H, 'H0': H0, 'llano': llano, 'valido': valido, 'o': o,
            'nz': nz_, 'snap': snap, 'M': M, 'kb': kb, 'frb': frb, 'zt': zt, 'ns': ns, 'corte': corte,
            'n2': info_n2, 'relleno': dz_c}


D_CORNISA = 0.042     # semiancho de la banda de cornisa en la coordenada kz (fr = 0.16 del banco)
_F_Z, _F_CORTE, _F_KZ, _F_NAT = 0, 1, 2, 3


def _clave_estrato(kz):
    """material de la cara de corte en la coordenada de estrato kz (por COTA):
    cornisa (kz a +-D_CORNISA de un entero) -> repisa; banco k >= 0 -> roca /
    roca_clara por paridad; por debajo de la primera cornisa (cara de 7 m,
    berma y bajo el tablero) -> roca. Solo cambia en los umbrales de
    _umbrales_estrato (por debajo de -D_CORNISA no hay mas cornisas)."""
    if kz < -D_CORNISA:
        return 'roca'
    k = math.floor(kz)
    q = kz - k
    if q < D_CORNISA or q > 1.0 - D_CORNISA:
        return 'repisa'
    return 'roca' if int(k) % 2 == 0 else 'roca_clara'


def _umbrales_estrato(lo, hi):
    """umbrales de kz donde cambia el material (k +- D_CORNISA, k >= 0) en (lo, hi]."""
    out = []
    for k in range(max(0, int(math.floor(lo)) - 1), int(math.floor(hi)) + 2):
        for t in (float(k) - D_CORNISA, float(k) + D_CORNISA):
            if lo < t <= hi:
                out.append(t)
    return out


def _dilatar(m):
    """dilatacion 3 x 3 (8 vecinos) de una mascara booleana, sin dar la vuelta en los bordes."""
    ny, nx = m.shape
    p = np.pad(m, 1)
    out = np.zeros_like(m)
    for dj in (0, 1, 2):
        for di in (0, 1, 2):
            out |= p[dj:dj + ny, di:di + nx]
    return out


def _normales_rejilla(Xd, Yd, H, val):
    """normales SUAVES por vertice de la rejilla sin partir (media de las normales de cara
    ponderada por el angulo de esquina, como Blender), con la misma diagonal por celda que
    _malla_roca. Forma (ny, nx, 3)."""
    ny, nx = H.shape
    P = np.stack([Xd, Yd, H], -1).reshape(-1, 3)
    J, I = np.meshgrid(np.arange(ny - 1), np.arange(nx - 1), indexing='ij')
    A = J * nx + I
    B, Cc, Dd = A + 1, A + nx + 1, A + nx
    ok = val[:-1, :-1] & val[:-1, 1:] & val[1:, 1:] & val[1:, :-1]
    d1 = (np.abs(H[:-1, :-1] - H[1:, 1:]) <= np.abs(H[:-1, 1:] - H[1:, :-1]))[..., None]
    t1 = np.where(d1, np.stack([A, B, Cc], -1), np.stack([A, B, Dd], -1))[ok]
    t2 = np.where(d1, np.stack([A, Cc, Dd], -1), np.stack([B, Cc, Dd], -1))[ok]
    T = np.concatenate([t1, t2])
    acc = np.zeros_like(P)
    if len(T):
        fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
        fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-12)[:, None]
        for (k0, k1, k2) in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
            e1 = P[T[:, k1]] - P[T[:, k0]]
            e2 = P[T[:, k2]] - P[T[:, k0]]
            e1 /= np.maximum(np.linalg.norm(e1, axis=1), 1e-12)[:, None]
            e2 /= np.maximum(np.linalg.norm(e2, axis=1), 1e-12)[:, None]
            ang = np.arccos(np.clip((e1 * e2).sum(axis=1), -1.0, 1.0))
            np.add.at(acc, T[:, k0], fn * ang[:, None])
    ln = np.linalg.norm(acc, axis=1)
    malo = ln < 1e-12
    acc[malo] = (0.0, 0.0, 1.0)
    ln[malo] = 1.0
    acc /= ln[:, None]
    return acc.reshape(ny, nx, 3)


def _fijar_normales(ob, mr):
    """normales personalizadas de la roca: las suaves de la rejilla sin partir, interpoladas en
    los vertices nuevos de la particion de materiales (asi partir un triangulo no cambia el
    sombreado: sin las muescas oscuras en las lineas de corte). Devuelve los vertices sin
    normal (0 esperado)."""
    nr = getattr(mr, 'normales', None)
    me = ob.data
    if not nr or not len(me.vertices):
        return -1
    from mathutils import kdtree
    kd = kdtree.KDTree(len(mr.v))
    for k, p in enumerate(mr.v):
        kd.insert(p, k)
    kd.balance()
    mw = ob.matrix_world
    m3t = mw.to_3x3().transposed()          # normal de mundo -> objeto (rotacion / escala uniforme)
    out, falta = [], 0
    for v in me.vertices:
        co, k, dist = kd.find(mw @ v.co)
        if k is None or dist > 0.01:
            falta += 1
            out.append(tuple(v.normal))
            continue
        n = m3t @ Vector(nr[k])
        n.normalize()
        if n.dot(v.normal) < 0.0:
            n = -n
        out.append(tuple(n))
    me.normals_split_custom_set_from_vertices(out)
    me.update()
    return falta


def _orientacion(ob, z_ref=0.0, celda=2.0):
    """Orientacion de una malla (coordenadas de mundo, triangulos de loop_triangles como el render
    y el kn5): volumen con signo respecto al plano z = z_ref (la roca esta abierta solo por abajo,
    en el anillo a z_fondo: con z_ref = z_fondo ese hueco no suma), nz medio por area y '% de
    techo boca abajo' (cara mas alta de cada celda de `celda` m con |nz| > 0.3, como verif_h)."""
    me = ob.data
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    if nt == 0:
        return None
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get('co', co)
    mw = np.array(ob.matrix_world, dtype=np.float64)
    cw = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    tv = np.empty(nt * 3, dtype=np.int64)
    me.loop_triangles.foreach_get('vertices', tv)
    tv = tv.reshape(-1, 3)
    a, b, c = cw[tv[:, 0]], cw[tv[:, 1]], cw[tv[:, 2]]
    n = np.cross(b - a, c - a)
    ar = np.linalg.norm(n, axis=1) + 1e-12
    off = np.array([0.0, 0.0, float(z_ref)])
    vol = float(np.einsum('ij,ij->i', a - off, np.cross(b - off, c - off)).sum() / 6.0)
    cen = (a + b + c) / 3.0
    key = np.floor(cen[:, :2] / celda).astype(np.int64)
    k1 = key[:, 0] * 100003 + key[:, 1]
    orden = np.lexsort((-cen[:, 2], k1))
    _u, prim = np.unique(k1[orden], return_index=True)
    top = orden[prim]
    top = top[np.abs(n[top, 2] / ar[top]) > 0.3]
    # normales de esquina (las que escribe el kn5) contra la normal de su cara: % opuestas
    n_inv = -1.0
    try:
        nl = len(me.loops)
        cn = np.empty(nl * 3, dtype=np.float64)
        me.corner_normals.foreach_get('vector', cn)
        pn = np.empty(len(me.polygons) * 3, dtype=np.float64)
        me.polygons.foreach_get('normal', pn)
        lt = np.empty(len(me.polygons), dtype=np.int64)
        me.polygons.foreach_get('loop_total', lt)
        cara = np.repeat(np.arange(len(me.polygons)), lt)
        dots = (cn.reshape(-1, 3) * pn.reshape(-1, 3)[cara]).sum(axis=1)
        n_inv = round(100.0 * float((dots < 0.0).mean()), 3) if nl else 0.0
    except Exception:                    # pragma: no cover (API sin corner_normals)
        pass
    return {'tris': int(nt), 'vol': round(vol, 1), 'nz_area': round(float(n[:, 2].sum() / ar.sum()), 3),
            'techo_n': int(len(top)), 'techo_abajo_pct': round(100.0 * float((n[top, 2] < 0).mean()) if len(top) else 0.0, 2),
            'normales_esquina_opuestas_pct': n_inv}


def _orientar_fuera(ob, z_ref=0.0):
    """H2-1: la roca es un campo de alturas ABIERTO por abajo (anillo a z_fondo) y
    recalc_face_normals elegia el sentido hacia DENTRO (en AC, con culling de caras traseras, la
    roca salia como una cascara hueca). Si el volumen con signo (respecto a z_ref) es negativo se
    da la vuelta a todas las caras. Devuelve True si se invirtio."""
    o = _orientacion(ob, z_ref)
    if o is None or o['vol'] >= 0.0:
        return False
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()
    return True


def _malla_roca(G, C, z_mar, seed, nombre='PENON_puente_roca'):
    """Triangulos de la rejilla (diagonal alterna) con material por cara, y
    los triangulos que cruzan un LIMITE DE MATERIAL partidos por la isolinea
    (marching triangles): ningun limite sigue las aristas de la rejilla, asi
    que no hay dientes de sierra ni manchas en escalera (en AC cada material
    es un color plano: el limite por cara es exactamente lo que se ve).
    Campos por vertice, interpolados linealmente en cada triangulo:
      z      -> bajo z_mar - 0.4: roca_oscura;
      corte  = M + 0.05 - perfil de corte (>= 0: cara de corte de la pista);
      kz     = (H0 - zt - 7.6) / hs: coordenada de ESTRATO por COTA respecto
               al tablero (los bancos del perfil tienen la cornisa en kz
               entero) -> _clave_estrato. Al ir por cota, en las caras de
               75-78 grados los limites son lineas horizontales;
      nat    = min(nz - 0.75, 2 (manchas - 0.2)), nz de la superficie
               desplazada (roca natural: >= 0 -> roca_clara, mancha en lo
               tendido; si no, roca).
    La particion es la misma para todas las piezas y depende solo de los
    valores en los extremos de cada arista (vertices nuevos cacheados por
    arista + campo + umbral): la malla sigue cerrada y sin juntas en T. kz
    solo varia cerca de la cara de corte y nat cerca de la roca natural
    (fuera, constantes), para no partir triangulos sin necesidad. Lo llano
    (los 3 vertices) va de repisa. Ademas, un anillo de vertices a z_fondo
    rodea lo valido (8 vecinos): el borde abierto de la malla queda bajo el
    fondo del mar, nunca colgando sobre el agua. mr.normales: normal suave de
    la rejilla sin partir por vertice (interpolada en los nuevos), que
    _fijar_normales pone como normales personalizadas."""
    Xd, Yd, H = C['Xd'], C['Yd'], C['H']
    val = _dilatar(C['valido'])
    ny, nx = H.shape
    idx = -np.ones(H.shape, dtype=np.int64)
    idx[val] = np.arange(int(val.sum()))
    mr = _Malla(nombre, ('roca', 'roca_clara', 'roca_oscura', 'repisa'))
    mr.v = [(float(a), float(b), float(c)) for (a, b, c) in zip(Xd[val], Yd[val], H[val])]
    z_agua = z_mar - 0.4
    hs = 12.0 * (1.0 + 0.25 * C['ns'])
    fcorte = C['M'] + 0.05 - C['corte']
    en_corte = fcorte >= 0.0
    kz = np.where(_dilatar(en_corte), (C['H0'] - C['zt'] - 7.6) / hs, -0.5)
    manchas = _vnoise2(G.X, G.Y, 26.0, seed + 31)
    # pendiente de la superficie VISIBLE (desplazada), no la del campo sin desplazar: la isolinea
    # nz = 0.75 de las manchas no debe bajar por caras que en la malla son empinadas
    xj, xi = np.gradient(Xd)
    yj, yi = np.gradient(Yd)
    hj, hi_ = np.gradient(H)
    cx_, cy_, cz_ = yi * hj - hi_ * yj, hi_ * xj - xi * hj, xi * yj - yi * xj
    nzd = np.abs(cz_) / np.maximum(np.sqrt(cx_ * cx_ + cy_ * cy_ + cz_ * cz_), 1e-9)
    fnat = np.where(_dilatar(~en_corte), np.minimum(nzd - 0.75, 2.0 * (manchas - 0.2)), -1.0)
    nr = _normales_rejilla(Xd, Yd, H, val)[val]
    # campos 4-6: normal suave de la rejilla sin partir (se interpola en los vertices nuevos)
    F = [[float(q) for q in H[val]], [float(q) for q in fcorte[val]], [float(q) for q in kz[val]],
         [float(q) for q in fnat[val]], [float(q) for q in nr[:, 0]], [float(q) for q in nr[:, 1]],
         [float(q) for q in nr[:, 2]]]
    nkz = np.maximum(0.0, np.floor(kz + D_CORNISA) + 1.0) + np.maximum(0.0, np.floor(kz - D_CORNISA) + 1.0)
    cod = ((H >= z_agua).astype(np.int64) + 2 * en_corte.astype(np.int64) + 4 * (fnat >= 0.0).astype(np.int64)
           + 8 * nkz.astype(np.int64))
    cod = [int(q) for q in cod[val]]
    lla = [bool(q) for q in C['llano'][val]]
    V = mr.v
    cache = {}
    n_part = [0, 0]

    def cruce(a, b, f, t):
        i, j = (a, b) if a < b else (b, a)
        key = (i, j, f, t)
        r = cache.get(key)
        if r is not None:
            return r
        fi, fj = F[f][i], F[f][j]
        s = (t - fi) / (fj - fi)
        pi, pj = V[i], V[j]
        ln = math.sqrt((pj[0] - pi[0]) ** 2 + (pj[1] - pi[1]) ** 2 + (pj[2] - pi[2]) ** 2)
        if s * ln < 0.02:
            r = i
        elif (1.0 - s) * ln < 0.02:
            r = j
        else:
            V.append((pi[0] + s * (pj[0] - pi[0]), pi[1] + s * (pj[1] - pi[1]), pi[2] + s * (pj[2] - pi[2])))
            for g in F:
                g.append(g[i] + s * (g[j] - g[i]))
            r = len(V) - 1
        cache[key] = r
        return r

    def limpia(p):
        q = [v for k, v in enumerate(p) if v != p[k - 1]]
        return q if len(q) >= 3 else None

    def partir(piezas, f, t):
        out = []
        for p in piezas:
            vals = [F[f][v] for v in p]
            if not (min(vals) < t <= max(vals)):
                out.append(p)
                continue
            lo, hi = [], []
            m = len(p)
            for k in range(m):
                a, b = p[k], p[(k + 1) % m]
                sa, sb = F[f][a] >= t, F[f][b] >= t
                (hi if sa else lo).append(a)
                if sa != sb:
                    c = cruce(a, b, f, t)
                    lo.append(c)
                    hi.append(c)
            for q in (limpia(lo), limpia(hi)):
                if q is not None:
                    out.append(q)
        return out

    def clave_de(p):
        n_ = float(len(p))
        if sum(F[_F_Z][v] for v in p) / n_ < z_agua:
            return 'roca_oscura'
        if sum(F[_F_CORTE][v] for v in p) / n_ >= 0.0:
            return _clave_estrato(sum(F[_F_KZ][v] for v in p) / n_)
        return 'roca_clara' if sum(F[_F_NAT][v] for v in p) / n_ >= 0.0 else 'roca'

    for j in range(ny - 1):
        for i in range(nx - 1):
            a, b, c, d = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
            if a < 0 or b < 0 or c < 0 or d < 0:
                continue
            if abs(H[j, i] - H[j + 1, i + 1]) <= abs(H[j, i + 1] - H[j + 1, i]):
                tris = ((a, b, c), (a, c, d))
            else:
                tris = ((a, b, d), (b, c, d))
            for t in tris:
                t = [int(t[0]), int(t[1]), int(t[2])]
                llano = lla[t[0]] and lla[t[1]] and lla[t[2]]
                if cod[t[0]] == cod[t[1]] == cod[t[2]]:
                    mr.cara(t, 'repisa' if llano else clave_de(t))
                    continue
                n_part[0] += 1
                piezas = partir([t], _F_Z, z_agua)
                piezas = partir(piezas, _F_CORTE, 0.0)
                kv = [F[_F_KZ][v] for v in t]
                for u in _umbrales_estrato(min(kv), max(kv)):
                    piezas = partir(piezas, _F_KZ, u)
                piezas = partir(piezas, _F_NAT, 0.0)
                for p in piezas:
                    clave = 'repisa' if llano else clave_de(p)
                    for k in range(1, len(p) - 1):
                        mr.cara((p[0], p[k], p[k + 1]), clave)
                        n_part[1] += 1
    mr.info_particion = {'triangulos_partidos': n_part[0], 'trozos': n_part[1], 'vertices_nuevos': len(V) - int(val.sum())}
    mr.normales = list(zip(F[4], F[5], F[6]))
    return mr


# ----------------------------------------------------------------- muros / escaleras / vallas
def _normales_polilinea(pts, cerrada=False):
    n = len(pts)
    out = []
    for i in range(n):
        if cerrada:
            a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        else:
            a, b = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        l_ = math.hypot(dx, dy) or 1.0
        out.append((-dy / l_, dx / l_))
    return out


def _muro(mm, pts, z_top, z_bot, grosor, clave, lado=1.0, cerrada=False):
    """Muro vertical a lo largo de pts [(x, y)] (z_top/z_bot: escalar o lista
    por punto); grosor hacia la izquierda de la marcha * lado. Caras hacia
    fuera (recalc en objeto())."""
    n = len(pts)
    if n < 2:
        return
    nr = _normales_polilinea(pts, cerrada)
    zt = [float(z_top)] * n if not isinstance(z_top, (list, tuple)) else list(z_top)
    zb = [float(z_bot)] * n if not isinstance(z_bot, (list, tuple)) else list(z_bot)
    filas = []
    for i in range(n):
        x, y = pts[i]
        ox, oy = nr[i][0] * grosor * lado, nr[i][1] * grosor * lado
        filas.append((mm.vert((x, y, zb[i])), mm.vert((x, y, zt[i])),
                      mm.vert((x + ox, y + oy, zt[i])), mm.vert((x + ox, y + oy, zb[i]))))
    m = n if cerrada else n - 1
    for i in range(m):
        a, b = filas[i], filas[(i + 1) % n]
        mm.cara((a[0], b[0], b[1], a[1]), clave)
        mm.cara((a[1], b[1], b[2], a[2]), clave)
        mm.cara((a[2], b[2], b[3], a[3]), clave)
    if not cerrada:
        mm.cara((filas[0][0], filas[0][1], filas[0][2], filas[0][3]), clave)
        mm.cara((filas[-1][3], filas[-1][2], filas[-1][1], filas[-1][0]), clave)


def _escalera(me, p0, p1, z0, z1, ancho, clave='piedra_escalera', contra=0.17, huella=0.30):
    """Tramo recto de escalera (dientes de sierra + faldones laterales de 1.2 m)
    entre p0 (z0) y p1 (z1). Si la pendiente es < 12 % es una rampa empedrada.
    Devuelve el numero de peldanos (0 = rampa)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    lx, ly = -uy * ancho / 2.0, ux * ancho / 2.0
    dz = z1 - z0
    if abs(dz) / L < 0.12:
        a = (me.vert((p0[0] + lx, p0[1] + ly, z0 + 0.06)), me.vert((p0[0] - lx, p0[1] - ly, z0 + 0.06)),
             me.vert((p1[0] - lx, p1[1] - ly, z1 + 0.06)), me.vert((p1[0] + lx, p1[1] + ly, z1 + 0.06)))
        me.cara(a, 'piedra_plaza')
        return 0
    n = max(1, int(round(abs(dz) / contra)))
    n = max(1, min(n, int(L / 0.26)))
    izq, der = [], []
    for k in range(n + 1):
        t = k / float(n)
        x, y = p0[0] + ux * L * t, p0[1] + uy * L * t
        z_lo = z0 + dz * (k / float(n))
        z_hi = z0 + dz * ((k + 1) / float(n)) if k < n else z1
        if dz < 0:
            z_lo, z_hi = z_hi, z_lo
        izq.append((me.vert((x + lx, y + ly, z_lo)), me.vert((x + lx, y + ly, z_hi))))
        der.append((me.vert((x - lx, y - ly, z_lo)), me.vert((x - lx, y - ly, z_hi))))
    for k in range(n):
        # tabica (en t_k) y huella (t_k -> t_k+1), a la cota del peldano k+1 (subiendo)
        me.cara((izq[k][0], der[k][0], der[k][1], izq[k][1]), clave)
        me.cara((izq[k][1], der[k][1], der[k + 1][0], izq[k + 1][0]), clave)
    # faldones laterales: desde la huella hasta 1.2 m por debajo
    for lado, fila in ((1, izq), (-1, der)):
        for k in range(n):
            x0_, y0_, zt0 = me.v[fila[k][1]]
            x1_, y1_, zt1 = me.v[fila[k + 1][0]]
            a = me.vert((x0_, y0_, zt0 - 1.2))
            b = me.vert((x1_, y1_, zt1 - 1.2))
            me.cara((fila[k][1], fila[k + 1][0], b, a), clave)
    return n


def _valla(mv, p0, p1, z, alto=1.1, paso=1.2, puerta=True, hacia=None):
    """Valla de hierro de p0 a p1 (misma z): postes + dos barras; puerta de
    1.2 m abierta en el centro, con la hoja girada 70 grados hacia el lado
    `hacia` (vector (x, y) hacia el rellano / la roca; por defecto la
    izquierda de p0 -> p1). Devuelve (bisagra, extremo de la hoja) o None."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    rz = math.atan2(uy, ux)
    sgn = 1.0
    if hacia is not None and (-uy * hacia[0] + ux * hacia[1]) < 0.0:
        sgn = -1.0
    n = max(2, int(round(L / paso)))
    t_p = (L / 2.0 - 0.6, L / 2.0 + 0.6) if puerta and L > 3.0 else None
    for k in range(n + 1):
        t = L * k / n
        if t_p and t_p[0] - 0.3 < t < t_p[1] + 0.3:
            continue
        mv.caja((p0[0] + ux * t, p0[1] + uy * t, z), (0.07, 0.07, alto), 'hierro', rz)
    tramos = [(0.0, t_p[0]), (t_p[1], L)] if t_p else [(0.0, L)]
    for (ta, tb) in tramos:
        if tb - ta < 0.2:
            continue
        cx, cy = p0[0] + ux * (ta + tb) / 2.0, p0[1] + uy * (ta + tb) / 2.0
        for zb in (0.42, alto - 0.06):
            mv.caja((cx, cy, z + zb - 0.025), (tb - ta, 0.045, 0.05), 'hierro', rz)
    if t_p:
        for t in t_p:
            mv.caja((p0[0] + ux * t, p0[1] + uy * t, z), (0.14, 0.14, alto + 0.35), 'hierro', rz)
        cx, cy = p0[0] + ux * L / 2.0, p0[1] + uy * L / 2.0
        mv.caja((cx, cy, z + alto + 0.25), (1.34, 0.08, 0.1), 'hierro', rz)
        # hoja abierta 70 grados hacia el rellano (lado `hacia`), nunca hacia la pista
        ang = rz + sgn * math.radians(70)
        hx, hy = p0[0] + ux * t_p[0], p0[1] + uy * t_p[0]
        mv.caja((hx + math.cos(ang) * 0.55, hy + math.sin(ang) * 0.55, z + 0.05), (1.1, 0.04, alto - 0.15), 'hierro', ang)
        return ((hx, hy), (hx + math.cos(ang) * 1.1, hy + math.sin(ang) * 1.1))
    return None


def _campanile(mc, cx, cy, z0, rz, lado=4.4, alto=22.0):
    """Torre campanario: zocalo de piedra, fuste de estuco, cornisas, cuerpo de
    campanas con 4 pilares (huecos reales), reloj, campana y chapitel de teja."""
    mc.caja((cx, cy, z0 - 1.5), (lado + 0.5, lado + 0.5, 2.7), 'campanile_piedra', rz)
    h_f = alto * 0.70
    mc.caja((cx, cy, z0 + 1.2), (lado, lado, h_f - 1.2), 'campanile_estuco', rz)
    for zc in (z0 + h_f * 0.45, z0 + h_f):
        mc.caja((cx, cy, zc - 0.35), (lado + 0.6, lado + 0.6, 0.35), 'campanile_piedra', rz)
    # saeteras oscuras en las 4 caras (dos alturas)
    for k in range(4):
        a = rz + k * math.pi / 2.0
        fx, fy = math.cos(a), math.sin(a)
        for zs in (z0 + h_f * 0.25, z0 + h_f * 0.62):
            mc.caja((cx + fx * (lado / 2.0 - 0.02), cy + fy * (lado / 2.0 - 0.02), zs), (0.12, 0.5, 1.6), 'hierro', a)
    # reloj en la cara frontal (+X local)
    fx, fy = math.cos(rz), math.sin(rz)
    mc.caja((cx + fx * (lado / 2.0 + 0.04), cy + fy * (lado / 2.0 + 0.04), z0 + h_f * 0.80), (0.12, 2.0, 2.0), 'campanile_piedra', rz)
    mc.caja((cx + fx * (lado / 2.0 + 0.10), cy + fy * (lado / 2.0 + 0.10), z0 + h_f * 0.80 + 0.2), (0.06, 1.5, 1.5), 'hierro', rz)
    # cuerpo de campanas: 4 pilares + losa superior
    hc = alto * 0.22
    for (dx, dy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lx, ly = dx * (lado / 2.0 - 0.4), dy * (lado / 2.0 - 0.4)
        px = cx + lx * math.cos(rz) - ly * math.sin(rz)
        py = cy + lx * math.sin(rz) + ly * math.cos(rz)
        mc.caja((px, py, z0 + h_f), (0.8, 0.8, hc), 'campanile_estuco', rz)
    mc.caja((cx, cy, z0 + h_f + hc), (lado + 0.4, lado + 0.4, 0.5), 'campanile_piedra', rz)
    # campana de bronce colgada
    mc.caja((cx, cy, z0 + h_f + hc * 0.35), (1.1, 1.1, 1.0), 'bronce', rz + math.pi / 4)
    mc.caja((cx, cy, z0 + h_f + hc * 0.35 + 1.0), (0.5, 0.5, 0.5), 'bronce', rz)
    # chapitel piramidal con alero
    zb = z0 + h_f + hc + 0.5
    base = []
    for (dx, dy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lx, ly = dx * (lado / 2.0 + 0.5), dy * (lado / 2.0 + 0.5)
        base.append(mc.vert((cx + lx * math.cos(rz) - ly * math.sin(rz), cy + lx * math.sin(rz) + ly * math.cos(rz), zb)))
    apex = mc.vert((cx, cy, zb + alto * 0.20))
    for k in range(4):
        mc.cara((base[k], base[(k + 1) % 4], apex), 'campanile_teja')
    mc.cara((base[3], base[2], base[1], base[0]), 'campanile_piedra')
    mc.caja((cx, cy, zb + alto * 0.20 - 0.1), (0.25, 0.25, 1.4), 'bronce', rz)
    mc.caja((cx, cy, zb + alto * 0.20 + 0.8), (0.9, 0.12, 0.12), 'bronce', rz)


# ----------------------------------------------------------------- cala: pantalan, barcas, matas
def _pantalan(mp, p0, ux, uy, largo, z_mar, ancho=2.4):
    """Pantalan de madera desde p0 hacia (ux, uy): tablero a z_mar + 0.9 sobre
    pilotes, con vigas laterales."""
    lx, ly = -uy * ancho / 2.0, ux * ancho / 2.0
    zt = z_mar + 0.9
    n = max(2, int(largo / 1.0))
    fila = []
    for k in range(n + 1):
        t = largo * k / n
        x, y = p0[0] + ux * t, p0[1] + uy * t
        fila.append((mp.vert((x + lx, y + ly, zt)), mp.vert((x - lx, y - ly, zt)),
                     mp.vert((x - lx, y - ly, zt - 0.22)), mp.vert((x + lx, y + ly, zt - 0.22))))
    for k in range(n):
        a, b = fila[k], fila[k + 1]
        mp.cara((a[0], a[1], b[1], b[0]), 'madera')
        mp.cara((a[3], b[3], b[2], a[2]), 'madera')
        mp.cara((a[1], a[2], b[2], b[1]), 'madera')
        mp.cara((a[0], b[0], b[3], a[3]), 'madera')
    mp.cara((fila[-1][0], fila[-1][1], fila[-1][2], fila[-1][3]), 'madera')
    for k in range(0, n + 1, 3):
        t = largo * k / n
        for sgn in (1, -1):
            x, y = p0[0] + ux * t + sgn * lx * 0.8, p0[1] + uy * t + sgn * ly * 0.8
            mp.caja((x, y, z_mar - 2.6), (0.26, 0.26, 3.9), 'madera', math.atan2(uy, ux))


def _barca(mb, cx, cy, z, rz, clave, L=5.2, B=1.9, D=0.55, F=0.62):
    """Barca de pescadores (gozzo): casco por secciones, regala, bancos."""
    cr, sr = math.cos(rz), math.sin(rz)

    def P(lx, ly, lz):
        return (cx + lx * cr - ly * sr, cy + lx * sr + ly * cr, z + lz)

    n = 8
    anillos = []
    for k in range(n + 1):
        t = k / float(n)
        x = -L / 2.0 + L * t
        w = (B / 2.0) * (math.sin(math.pi * (0.08 + 0.92 * t)) ** 0.55) * (1.0 - 0.35 * max(0.0, t - 0.85) / 0.15)
        w = max(0.06, w)
        d = D * (0.55 + 0.45 * math.sin(math.pi * t) ** 0.5)
        f = F * (1.0 + 0.25 * (abs(t - 0.5) * 2) ** 2)
        anillos.append([mb.vert(P(x, 0.0, -d)), mb.vert(P(x, w * 0.82, -d * 0.35)), mb.vert(P(x, w, f)),
                        mb.vert(P(x, w * 0.86, f)), mb.vert(P(x, -w * 0.86, f)), mb.vert(P(x, -w, f)),
                        mb.vert(P(x, -w * 0.82, -d * 0.35))])
    for k in range(n):
        a, b = anillos[k], anillos[k + 1]
        mb.cara((a[0], b[0], b[1], a[1]), clave)
        mb.cara((a[1], b[1], b[2], a[2]), clave)
        mb.cara((a[2], b[2], b[3], a[3]), 'madera')
        mb.cara((a[5], b[5], b[4], a[4]), 'madera')
        mb.cara((a[6], b[6], b[5], a[5]), clave)
        mb.cara((a[0], a[6], b[6], b[0]), clave)
    # suelo interior y espejo de popa
    a = anillos[0]
    mb.cara((a[1], a[2], a[3], a[4], a[5], a[6]), 'madera')
    for k in range(n):
        a, b = anillos[k], anillos[k + 1]
        mb.cara((a[3], b[3], b[4], a[4]), 'madera')
    b = anillos[-1]
    mb.cara((b[6], b[5], b[4], b[3], b[2], b[1]), 'madera')
    for t in (0.3, 0.62):
        mb.caja(P(-L / 2.0 + L * t, 0.0, 0.18), (0.3, B * 0.72, 0.06), 'madera', rz)


_PHI = (1 + 5 ** 0.5) / 2
_ICO_V = [(-1, _PHI, 0), (1, _PHI, 0), (-1, -_PHI, 0), (1, -_PHI, 0), (0, -1, _PHI), (0, 1, _PHI),
          (0, -1, -_PHI), (0, 1, -_PHI), (_PHI, 0, -1), (_PHI, 0, 1), (-_PHI, 0, -1), (-_PHI, 0, 1)]
_ICO_F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
          (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
          (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
VERTS_MATA = len(_ICO_V)
_OBRA_MATAS = ('PENON_puente_muros', 'PENON_puente_escaleras', 'PENON_puente_vallas', 'PENON_puente_plaza',
               'PENON_puente_campanile', 'PENON_puente_muelle', 'PENON_carretera')


def _mata_verts(x, y, z, nrm, sx, sy, sz, rz):
    """12 vertices de una mata (icosaedro achatado) en el marco TANGENTE de la
    ladera: centro en (x, y, z) SOBRE el suelo (media mata enterrada) y eje
    corto por la normal nrm. Devuelve [(x, y, z, w)], w = altura local por la
    normal (w <= 0: mitad inferior)."""
    nx_, ny_, nz_ = nrm
    ex, ey = math.cos(rz), math.sin(rz)
    dot = ex * nx_ + ey * ny_
    t1 = (ex - dot * nx_, ey - dot * ny_, -dot * nz_)
    l1 = math.sqrt(t1[0] ** 2 + t1[1] ** 2 + t1[2] ** 2) or 1.0
    t1 = (t1[0] / l1, t1[1] / l1, t1[2] / l1)
    t2 = (ny_ * t1[2] - nz_ * t1[1], nz_ * t1[0] - nx_ * t1[2], nx_ * t1[1] - ny_ * t1[0])
    k = 1.0 / (1 + _PHI * _PHI) ** 0.5
    out = []
    for (bx, by, bz) in _ICO_V:
        lu, lv, lw = bx * k * sx, by * k * sy, bz * k * sz * 0.85
        out.append((x + lu * t1[0] + lv * t2[0] + lw * nx_, y + lu * t1[1] + lv * t2[1] + lw * ny_,
                    z + lu * t1[2] + lv * t2[2] + lw * nz_, lw))
    return out


def _matas(mv, matas, clave_a='mata', clave_b='mata_clara'):
    """anade las matas ya colocadas (listas de 12 vertices de _mata_verts)."""
    for n_, vs in enumerate(matas):
        i0 = len(mv.v)
        for p in vs:
            mv.v.append((p[0], p[1], p[2]))
        clave = clave_a if n_ % 3 else clave_b
        for (a_, b_, c_) in _ICO_F:
            mv.cara((i0 + a_, i0 + b_, i0 + c_), clave)


# ----------------------------------------------------------------- trazado (diseno en planta)
def _unit(x, y):
    l_ = math.hypot(x, y) or 1.0
    return (x / l_, y / l_)


def _ang_norm(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


class _Polar:
    """Coordenadas polares alrededor de la cumbre S0 con el sector abierto
    parametrizado por f in [0, 1] (f=0 lado de la entrada, f=1 lado de la salida)."""

    def __init__(self, S0, th_a, span):
        self.S0 = (float(S0[0]), float(S0[1]))
        self.th_a = th_a
        self.span = span

    def th(self, f):
        return self.th_a + f * self.span

    def xy(self, r, th):
        return (self.S0[0] + r * math.cos(th), self.S0[1] + r * math.sin(th))

    def xyf(self, r, f):
        return self.xy(r, self.th(f))

    def r_donde(self, G, M, th, nivel, r0=8.0, r1=300.0, paso=1.0):
        """primer radio (hacia fuera desde r0) donde M < nivel; r1 si no baja."""
        rs = np.arange(r0, r1, paso)
        xs = self.S0[0] + rs * math.cos(th)
        ys = self.S0[1] + rs * math.sin(th)
        vals = G.muestrear(M, xs, ys)
        idx = np.where(vals < nivel)[0]
        if len(idx) == 0:
            return float(r1)
        k = int(idx[0])
        if k == 0:
            return float(r0)
        # interpolacion lineal entre k-1 y k
        v0, v1 = vals[k - 1], vals[k]
        t = (v0 - nivel) / ((v0 - v1) if abs(v0 - v1) > 1e-9 else 1e-9)
        return float(rs[k - 1] + paso * max(0.0, min(1.0, t)))


def _suavizar_lista(vals, pasadas=2):
    v = list(vals)
    for _ in range(pasadas):
        v = [v[0]] + [(v[i - 1] + 2 * v[i] + v[i + 1]) / 4.0 for i in range(1, len(v) - 1)] + [v[-1]]
    return v


def _banda_polar(pol, fs, r_front, ancho):
    """poligono (lista xy) de una banda entre r_front(f) - ancho y r_front(f)."""
    front = [pol.xyf(r_front[i], fs[i]) for i in range(len(fs))]
    back = [pol.xyf(r_front[i] - ancho, fs[i]) for i in range(len(fs))]
    return front + back[::-1], front, back


def _rect_tramo(p0, p1, semi):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    lx, ly = -uy * semi, ux * semi
    ex, ey = ux * 0.6, uy * 0.6
    return [(p0[0] + lx - ex, p0[1] + ly - ey), (p0[0] - lx - ex, p0[1] - ly - ey),
            (p1[0] - lx + ex, p1[1] - ly + ey), (p1[0] + lx + ex, p1[1] + ly + ey)]


def _rasgo_tramo(nombre, p0, p1, z0, z1, ancho):
    """rasgo de un tramo de escalera/rampa: cota lineal a lo largo del eje."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L2 = dx * dx + dy * dy or 1.0

    def nivel_fn(X, Y):
        t = np.clip(((X - p0[0]) * dx + (Y - p0[1]) * dy) / L2, 0.0, 1.0)
        return z0 + (z1 - z0) * t - 0.04

    # fuera del rectangulo la roca se corta a 75 grados desde el nivel LOCAL del peldano
    # (nivel_corte=None): la zanja tiene paredes de 75 grados en toda su longitud
    return _Rasgo(nombre, _rect_tramo(p0, p1, ancho / 2.0 + 0.35), min(z0, z1), nivel_fn=nivel_fn,
                  nivel_corte=None, relleno=True, tipo='escalera')


def _rasgo_codo(nombre, p_prev, p, p_next, z):
    """rasgo llano (cuadrado) bajo la losa de rellano del codo p entre los
    tramos p_prev -> p -> p_next: lado = 2 * (radio de la losa + 0.9), con el
    radio que _construir_obra usara (_codo_params)."""
    d1 = _unit(p_prev[0] - p[0], p_prev[1] - p[1])
    d2 = _unit(p_next[0] - p[0], p_next[1] - p[1])
    _a, r_losa = _codo_params([d1, d2])
    r = r_losa + 0.9
    return _Rasgo(nombre, _rect_tramo((p[0] - r + 0.6, p[1]), (p[0] + r - 0.6, p[1]), r), z, nivel_corte=z + 0.3)


def _dentro_poligono(poly, x, y):
    dentro = False
    K = len(poly)
    for k in range(K):
        ax, ay = poly[k]
        bx, by = poly[(k + 1) % K]
        if (ay > y) != (by > y):
            xi = ax + (y - ay) * (bx - ax) / ((by - ay) if by != ay else 1e-12)
            if x < xi:
                dentro = not dentro
    return dentro


# ----------------------------------------------------------------- terrazas por curvas de nivel
class _RasgoNivel:
    """Terraza tallada siguiendo las CURVAS DE NIVEL del macizo M: llana a z_k
    entre las curvas M = z_k - 1 (frente, murete) y M = z_k + alto_p (paredon),
    dentro de un sector angular desde S0 (con los extremos afilados) y lejos
    del tablero (o > 12). Detras, la roca no sube mas de 75 grados desde
    z_k + 2 (distancia al paredon estimada con el gradiente de M)."""

    def __init__(self, nombre, M, G, pol, z_k, f0, f1, alto_p=10.5, taper=0.06):
        self.nombre = nombre
        self.z = float(z_k)
        self.tipo = 'llano'
        X, Y = G.X, G.Y
        th = np.arctan2(Y - pol.S0[1], X - pol.S0[0])
        self.f = ((th - pol.th_a + math.pi) % (2 * math.pi) - math.pi) / pol.span
        self.alto_p = alto_p
        self.taper = taper
        self.recortar_sector(f0, f1)
        gy, gx = np.gradient(M, G.cell)
        self.g = np.maximum(np.sqrt(gx * gx + gy * gy), 0.25)
        self.M = M
        self.G = G
        self.pol_S0 = (float(pol.S0[0]), float(pol.S0[1]))
        self.ancho_min = 14.0
        self.d_front = None          # distancia al frente trazado (se fija con fijar_frente)
        self.lado_up = None          # celdas cuesta arriba del frente (r <= r_frente(f))

    def recortar_sector(self, f0, f1):
        f = self.f
        margen = np.clip(np.minimum(f - f0, f1 - f) / self.taper, 0.0, 1.0)
        self.tope = self.z - 1.0 + (self.alto_p + 1.0) * margen
        self.sector = (f > f0) & (f < f1)
        self.f0, self.f1 = f0, f1

    def fijar_frente(self, front, margen, fs=None, rs=None):
        """distancia de cada celda al frente trazado (para el ancho minimo),
        con los extremos afilados: margen(i) in [0, 1] por punto del frente.
        Con fs/rs (angulo f y radio desde S0 de cada punto, f monotono) se
        fija ademas el lado de cuesta arriba: r <= r_frente(f) + 0.3."""
        X, Y = self.G.X, self.G.Y
        S0x, S0y = self.pol_S0
        d = np.full(X.shape, 1e9)
        best = np.full(X.shape, 1e18)
        sgn = np.zeros(X.shape)
        wloc = np.zeros(X.shape)
        for k in range(len(front) - 1):
            ax, ay = front[k]
            bx, by = front[k + 1]
            ddx, ddy = bx - ax, by - ay
            L2 = ddx * ddx + ddy * ddy
            if L2 < 1e-9:
                continue
            L = math.sqrt(L2)
            t = np.clip(((X - ax) * ddx + (Y - ay) * ddy) / L2, 0.0, 1.0)
            w = self.ancho_min * (margen[k] * (1 - t) + margen[k + 1] * t)
            d2 = (X - ax - t * ddx) ** 2 + (Y - ay - t * ddy) ** 2
            d = np.minimum(d, np.sqrt(d2) - w)
            # lado de cuesta arriba: desplazamiento con signo respecto al segmento mas cercano
            # (normal perpendicular orientada hacia la cumbre S0)
            nx_, ny_ = -ddy / L, ddx / L
            if nx_ * (S0x - ax) + ny_ * (S0y - ay) < 0.0:
                nx_, ny_ = -nx_, -ny_
            m = d2 < best
            best[m] = d2[m]
            sgn[m] = ((X - ax) * nx_ + (Y - ay) * ny_)[m]
            wloc[m] = w[m]
        self.d_front = d          # <= 0 dentro de la banda de ancho minimo
        self.lado_up = sgn > -0.3
        self.sgn = sgn
        self.d_lin = np.sqrt(best)
        self.wloc = wloc

    def aplicar(self, X, Y, H, o=None, llano_prev=None):
        M = self.M
        arriba = M > self.z - 1.0
        dentro = self.sector & arriba & (M <= self.tope)
        d_back = np.where(self.sector & (M > self.tope), (M - self.tope) / self.g, 1e9)
        if self.lado_up is not None:
            # repisa de diseno: cuesta arriba del frente enderezado se rellena todo lo que no
            # sea paredon (M <= tope, hasta 24 m) o este dentro del ancho minimo (barrancos incluidos)
            dentro = self.sector & self.lado_up & (((M <= self.tope) & (self.d_front <= 24.0 - self.ancho_min)) | (self.d_front <= 0.0))
            d_back = np.minimum(d_back, np.where(self.lado_up & (self.d_front < 40.0), np.maximum(0.0, self.d_front), 1e9))
        elif self.d_front is not None:
            dentro |= arriba & (self.d_front <= 0.0)
            d_back = np.minimum(d_back, np.where(arriba & (self.d_front < 40.0), np.maximum(0.0, self.d_front), 1e9))
        if o is not None:
            dentro &= o > 12.0
        corte = np.where(d_back < 40.0, self.z + 2.0 + TAN75 * d_back, 1e9)
        H = np.where(dentro, self.z, np.minimum(H, corte))
        if self.lado_up is not None:
            # cuesta abajo del frente la roca baja a 75 grados desde z - 1 (talud de apoyo) en vez
            # de caer en vertical en una celda donde el frente enderezado cruza un hueco (las
            # celdas torcidas daban facetas en diente de sierra); nunca sobre lo llano de otro rasgo
            emb = (~dentro) & (self.sgn < -0.3) & (self.d_lin < 10.0) & (self.wloc > 7.0)
            if llano_prev is not None:
                emb &= ~llano_prev
            H = np.where(emb, np.maximum(H, self.z - 1.0 - TAN75 * self.d_lin), H)
        return H, dentro


def _trazar_contorno(G, F, p0, nivel, dentro_fn, paso=2.0, max_pts=500):
    """Sigue la curva F = nivel desde p0 en los dos sentidos (predictor por la
    tangente + correccion de Newton) mientras dentro_fn(x, y). Devuelve
    (puntos, normales hacia arriba del gradiente)."""
    e = 0.6

    def grad(x, y):
        gx = (float(G.muestrear(F, x + e, y)) - float(G.muestrear(F, x - e, y))) / (2 * e)
        gy = (float(G.muestrear(F, x, y + e)) - float(G.muestrear(F, x, y - e))) / (2 * e)
        return gx, gy

    def corregir(x, y):
        for _ in range(6):
            v = float(G.muestrear(F, x, y)) - nivel
            gx, gy = grad(x, y)
            g2 = gx * gx + gy * gy
            if g2 < 1e-4 or abs(v) < 0.02:
                break
            x -= v * gx / g2
            y -= v * gy / g2
        return x, y

    def residuo(x, y):
        return abs(float(G.muestrear(F, x, y)) - nivel)

    p0 = corregir(p0[0], p0[1])
    ramas = []
    for sentido in (1.0, -1.0):
        x, y = p0
        pts = []
        for _ in range(max_pts):
            gx, gy = grad(x, y)
            g = math.hypot(gx, gy) or 1e-6
            x2, y2 = corregir(x - gy / g * paso * sentido, y + gx / g * paso * sentido)
            if not dentro_fn(x2, y2) or math.hypot(x2 - x, y2 - y) > 3.0 * paso or residuo(x2, y2) > 0.4 or g < 0.15:
                break
            pts.append((x2, y2))
            x, y = x2, y2
            if len(pts) > 4 and math.hypot(x - p0[0], y - p0[1]) < paso * 0.6:
                break
        ramas.append(pts)
    pts = ramas[1][::-1] + [p0] + ramas[0]
    nrm = []
    for (x, y) in pts:
        gx, gy = grad(x, y)
        g = math.hypot(gx, gy) or 1e-6
        nrm.append((gx / g, gy / g))
    return pts, nrm


def _dist_polilinea(pts, x, y):
    best = 1e18
    for k in range(len(pts) - 1):
        ax, ay = pts[k]
        bx, by = pts[k + 1]
        ddx, ddy = bx - ax, by - ay
        L2 = ddx * ddx + ddy * ddy or 1e-9
        t = max(0.0, min(1.0, ((x - ax) * ddx + (y - ay) * ddy) / L2))
        best = min(best, (x - ax - t * ddx) ** 2 + (y - ay - t * ddy) ** 2)
    return math.sqrt(best)


def _o_asfalto(prep, x, y):
    """(o, k): distancia con signo (+ hacia la roca) del punto (x, y) a la polilinea del borde interior del
    asfalto prep['B'] y segmento mas cercano k."""
    B, inward = prep['B'], prep['inward']
    best, kb, sg = 1e18, 0, 1.0
    for k in range(len(B) - 1):
        ax, ay = float(B[k][0]), float(B[k][1])
        ddx, ddy = float(B[k + 1][0]) - ax, float(B[k + 1][1]) - ay
        L2 = ddx * ddx + ddy * ddy or 1e-9
        t = max(0.0, min(1.0, ((x - ax) * ddx + (y - ay) * ddy) / L2))
        ex, ey = x - ax - t * ddx, y - ay - t * ddy
        d2 = ex * ex + ey * ey
        if d2 < best:
            best, kb = d2, k
            sg = 1.0 if ex * float(inward[k][0]) + ey * float(inward[k][1]) >= 0.0 else -1.0
    return sg * math.sqrt(best), kb


def _retranquear(prep, p, o_min):
    """v3: empuja el punto p hacia la roca (normal interior del tramo mas cercano) hasta que quede a >= o_min del
    borde del asfalto MEDIDO SOBRE LA POLILINEA (en curva, la esquina de una pieza recta queda mas cerca que su
    centro)."""
    x, y = float(p[0]), float(p[1])
    for _ in range(4):
        o, k = _o_asfalto(prep, x, y)
        if o >= o_min - 1e-4:
            break
        x += float(prep['inward'][k][0]) * (o_min - o + 0.005)
        y += float(prep['inward'][k][1]) * (o_min - o + 0.005)
    return (x, y)


def _terraza_nivel(nombre, G, M, pol, cb, z_k, f0, f1, log, lejos_de=None, d_min=20.5):
    """Crea el rasgo de nivel + traza el frente (M = z_k - 1) y el fondo.
    lejos_de: polilinea (frente de otra terraza) de la que hay que quedar a
    >= d_min (para que las dos bandas y sus paredones quepan)."""
    r = _RasgoNivel(nombre, M, G, pol, z_k, f0, f1)

    def dentro_fn(x, y):
        th = math.atan2(y - pol.S0[1], x - pol.S0[0])
        f = _ang_norm(th - pol.th_a) / pol.span
        o = float(G.muestrear(cb['o'], x, y))
        if not (f0 + 0.015 < f < f1 - 0.015 and o > 13.0):
            return False
        if lejos_de is not None and _dist_polilinea(lejos_de, x, y) < d_min:
            return False
        e = 0.8
        gx = float(G.muestrear(M, x + e, y)) - float(G.muestrear(M, x - e, y))
        gy = float(G.muestrear(M, x, y + e)) - float(G.muestrear(M, x, y - e))
        g = math.hypot(gx, gy) or 1e-6
        # detras tiene que haber loma de verdad (no una cresta fina que cae al otro lado)
        return float(G.muestrear(M, x + gx / g * 18.0, y + gy / g * 18.0)) >= z_k + 7.0

    # punto de arranque: el primer angulo (desde el centro del sector hacia fuera) donde cabe la terraza
    f_m = (f0 + f1) / 2.0
    front, nrm = [], []
    for k in range(0, 40):
        for sg in ((1.0,) if k == 0 else (1.0, -1.0)):
            f_t = f_m + sg * k * 0.012
            if not (f0 + 0.03 < f_t < f1 - 0.03):
                continue
            th_t = pol.th(f_t)
            p0 = pol.xy(pol.r_donde(G, M, th_t, z_k - 1.0, r0=20.0), th_t)
            if dentro_fn(p0[0], p0[1]):
                fr_, nr_ = _trazar_contorno(G, M, p0, z_k - 1.0, dentro_fn)
                if len(fr_) > len(front):
                    front, nrm = fr_, nr_
        if len(front) >= 12:
            break
    if len(front) < 4:
        log('%s: frente demasiado corto (%d puntos)' % (nombre, len(front)))
        if len(front) == 0:
            th_t = pol.th(f_m)
            p0 = pol.xy(pol.r_donde(G, M, th_t, z_k - 1.0, r0=20.0), th_t)
            front, nrm = _trazar_contorno(G, M, p0, z_k - 1.0, lambda x, y: False)
    # frente ENDEREZADO: sin horquillas (f monotono: los barrancos se cruzan con una cuerda
    # y se rellenan), remuestreado a <= 2 m y suavizado
    front, n_quitados = _enderezar_frente(front, pol)
    front = _suavizar_polilinea(_remuestrear(front, 2.0), 2)
    fsf, rsf = [], []
    for (x, y) in front:
        th = math.atan2(y - pol.S0[1], x - pol.S0[0])
        fsf.append(_ang_norm(th - pol.th_a) / pol.span)
        rsf.append(math.hypot(x - pol.S0[0], y - pol.S0[1]))
    f0, f1 = min(fsf) - 0.01, max(fsf) + 0.01
    r.recortar_sector(f0, f1)
    # normal perpendicular al frente, hacia la cumbre (cuesta arriba)
    tn = _normales_polilinea(front)
    nrm = []
    for i, (x, y) in enumerate(front):
        s_ = 1.0 if (tn[i][0] * (pol.S0[0] - x) + tn[i][1] * (pol.S0[1] - y)) >= 0.0 else -1.0
        nrm.append((tn[i][0] * s_, tn[i][1] * s_))
    xs_ = np.array([p[0] for p in front])
    ys_ = np.array([p[1] for p in front])
    g = np.maximum(G.muestrear(r.g, xs_, ys_), 0.25)
    m_f = G.muestrear(M, xs_, ys_)
    margen = [max(0.0, min(1.0, min(f - f0, f1 - f) / 0.06)) for f in fsf]
    r.fijar_frente(front, margen, fsf, rsf)
    # ancho de la repisa: el natural (hasta M = z + 10.5) donde el frente va por el contorno,
    # solo el minimo (14 m) donde es cuerda o suavizado (lejos del contorno M = z - 1)
    anchos = [float(min(24.0, max(r.ancho_min * margen[i], 11.5 / g[i] if abs(m_f[i] - (z_k - 1.0)) < 1.0 else 0.0)))
              for i in range(len(front))]
    back = [(front[i][0] + nrm[i][0] * anchos[i], front[i][1] + nrm[i][1] * anchos[i]) for i in range(len(front))]
    poly = front + back[::-1]
    info = {'nombre': nombre, 'z': z_k, 'front': front, 'back': back, 'nrm': nrm, 'anchos': anchos, 'poly': poly,
            'f0': f0, 'f1': f1, 'fs': fsf, 'rs': rsf, 'ocupados': [], 'rasgo': r}
    log('%s: z=%.0f, frente de %.0f m (%d puntos, %d de horquilla quitados), ancho de repisa %.0f..%.0f m'
        % (nombre, z_k, sum(math.hypot(front[i + 1][0] - front[i][0], front[i + 1][1] - front[i][1]) for i in range(len(front) - 1)),
           len(front), n_quitados, min(anchos), max(anchos)))
    return r, info


def _r_frente(T, pol, th):
    """radio desde S0 del frente enderezado de la terraza T en el angulo th
    (interpolado en f); None fuera del frente."""
    f = _ang_norm(th - pol.th_a) / pol.span
    fs, rs = T.get('fs', []), T.get('rs', [])
    if len(fs) < 2:
        return None
    pares = sorted(zip(fs, rs))
    fa = [p[0] for p in pares]
    ra = [p[1] for p in pares]
    if f < fa[0] or f > fa[-1]:
        return None
    return float(np.interp(f, fa, ra))


def _enderezar_frente(front, pol):
    """Quita las horquillas de un frente trazado: conserva solo los puntos
    que avanzan en f (angulo alrededor de S0) respecto al extremo ya
    alcanzado, en el sentido global del trazado."""
    if len(front) < 3:
        return list(front), 0
    fs = []
    for (x, y) in front:
        th = math.atan2(y - pol.S0[1], x - pol.S0[0])
        fs.append(_ang_norm(th - pol.th_a) / pol.span)
    sg = 1.0 if fs[-1] >= fs[0] else -1.0
    out = [front[0]]
    f_ext = fs[0]
    for k in range(1, len(front)):
        if (fs[k] - f_ext) * sg > 0.0015:
            out.append(front[k])
            f_ext = fs[k]
    return out, len(front) - len(out)


def _remuestrear(pts, paso):
    """polilinea remuestreada con puntos a <= paso (conserva los vertices)."""
    out = [pts[0]]
    for k in range(1, len(pts)):
        a, b = pts[k - 1], pts[k]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(math.ceil(L / paso)))
        for j in range(1, n + 1):
            t = j / float(n)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def _suavizar_polilinea(pts, pasadas=2):
    xs = _suavizar_lista([p[0] for p in pts], pasadas)
    ys = _suavizar_lista([p[1] for p in pts], pasadas)
    return [(xs[i], ys[i]) for i in range(len(pts))]


# ----------------------------------------------------------------- carreteras de acceso (H2-5)
ANCHO_CARR = 4.0          # calzada de un carril (como las calles del pueblo: coche de Cars + acera minima)
PRETIL_CARR = 0.45        # pretil de piedra a cada lado (encima de la losa)
HOMBRO_CARR = 0.35        # berma de roca entre el pretil y la pared tallada
SEMI_RELLANO_CARR = 3.2   # semiancho del rellano-boca junto al tablero (hueco del pretil del viaducto: 6.4 m)
# v3 (remate, nada_en_pista.py): NADA de la roca ni de su obra (salvo la propia roca) a < RETRANQUEO_ASFALTO del
# asfalto entre z - 0.3 y z + 5.5. La puerta peatonal (escalera) lleva su verja EN el hueco que el integrador abre en
# el pretil del viaducto (pretil a 0.04-0.48 m del asfalto), en su mitad trasera: linea de la verja a O_VERJA
# (postes de 0.14 -> a >= 0.41 m), y la losa del umbral (del hueco al rellano de roca) desde O_LOSA_PUERTA. Antes la
# verja iba en Cl + 0.9 y el integrador la traia a ras del pretil (0.26 m) con su propia losa desde 0.21 m.
RETRANQUEO_ASFALTO = 0.3
O_VERJA = 0.48
O_LOSA_PUERTA = 0.38
RADIO_PIAZZOLA_CALA = 6.5  # piazzola de giro de la carretera de la cala (extremo O del muelle)


def _bezier(p0, p1, p2, p3, n=200):
    out = []
    for k in range(n + 1):
        t = k / float(n)
        u = 1.0 - t
        a, b, c, d = u * u * u, 3.0 * u * u * t, 3.0 * u * t * t, t * t * t
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _remuestrear_arco(pts, paso):
    """polilinea 2D remuestreada a paso CONSTANTE por longitud de arco (incluye los extremos)."""
    acum = [0.0]
    for k in range(1, len(pts)):
        acum.append(acum[-1] + math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]))
    L = acum[-1]
    n = max(1, int(round(L / paso)))
    out, i = [], 0
    for q in range(n + 1):
        s_ = L * q / n
        while i < len(pts) - 2 and acum[i + 1] < s_:
            i += 1
        t = (s_ - acum[i]) / max(1e-9, acum[i + 1] - acum[i])
        out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
    return out


def _radio_min(pts):
    """radio de curvatura minimo (m) de una polilinea de paso ~constante."""
    r = 1e9
    for k in range(1, len(pts) - 1):
        a, b, c = pts[k - 1], pts[k], pts[k + 1]
        d1 = _unit(b[0] - a[0], b[1] - a[1])
        d2 = _unit(c[0] - b[0], c[1] - b[1])
        ang = abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1]))
        if ang > 1e-6:
            r = min(r, 0.5 * (math.hypot(b[0] - a[0], b[1] - a[1]) + math.hypot(c[0] - b[0], c[1] - b[1])) / ang)
    return r


class _RasgoCinta:
    """Calzada tallada en la roca a lo largo de una polilinea 3D [(x, y, z)]: dentro de la banda
    (distancia al eje <= semi) la cota es la rasante del punto mas cercano - 0.04 (relleno); fuera,
    la roca no sube mas de 75 grados desde la rasante + dz_corte (pared de desmonte). La banda NO
    tiene tapa redonda en el ARRANQUE (no rellena hacia el tablero), solo en el final. Con un
    4o valor por punto (pendiente transversal hacia la IZQUIERDA de la marcha, m/m) la rasante se
    inclina de lado: la boca sigue la pendiente longitudinal de la pista (sin escalon)."""

    def __init__(self, nombre, pts3, semi, dz_corte=0.3):
        self.nombre = nombre
        self.tipo = 'carretera'
        self.relleno = True
        self.pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts3]
        self.plat = [float(p[3]) if len(p) > 3 else 0.0 for p in pts3]
        self.semi = float(semi)
        self.dz_corte = float(dz_corte)
        nr = _normales_polilinea([(p[0], p[1]) for p in self.pts])
        izq = [(p[0] + n_[0] * semi, p[1] + n_[1] * semi) for p, n_ in zip(self.pts, nr)]
        der = [(p[0] - n_[0] * semi, p[1] - n_[1] * semi) for p, n_ in zip(self.pts, nr)]
        self.poly = izq + der[::-1]

    def aplicar(self, X, Y, H):
        best = np.full(X.shape, 1e18)
        zl = np.zeros(X.shape)
        antes = np.zeros(X.shape, dtype=bool)
        P_, PL = self.pts, self.plat
        for k in range(len(P_) - 1):
            (ax, ay, az), (bx, by, bz) = P_[k], P_[k + 1]
            ddx, ddy = bx - ax, by - ay
            L2 = ddx * ddx + ddy * ddy
            if L2 < 1e-9:
                continue
            tr = ((X - ax) * ddx + (Y - ay) * ddy) / L2
            t = np.clip(tr, 0.0, 1.0)
            d2 = (X - ax - t * ddx) ** 2 + (Y - ay - t * ddy) ** 2
            m = d2 < best
            best[m] = d2[m]
            z_k = az + t * (bz - az)
            if PL[k] != 0.0 or PL[k + 1] != 0.0:
                lat = ((X - ax) * (-ddy) + (Y - ay) * ddx) / math.sqrt(L2)
                lat = np.clip(lat, -self.semi, self.semi)
                z_k = z_k + (PL[k] + t * (PL[k + 1] - PL[k])) * lat
            zl[m] = z_k[m]
            antes[m] = (tr < 0.0)[m] if k == 0 else False
        d = np.sqrt(best)
        lvl = zl - 0.04
        dentro = (d <= self.semi) & (~antes)
        H = np.where(dentro, lvl, np.minimum(H, lvl + self.dz_corte + TAN75 * np.maximum(d - self.semi, 0.0)))
        return H, dentro


def _losa_disco(mc, cx, cy, r, z, clave, dz_top=0.03, dz_bot=-0.5, n=24):
    """Losa circular cerrada (piazzola de giro): n-gono a z + dz_top, fondo a z + dz_bot y canto."""
    top = [mc.vert((cx + r * math.cos(2.0 * math.pi * k / n), cy + r * math.sin(2.0 * math.pi * k / n), z + dz_top)) for k in range(n)]
    bot = [mc.vert((cx + r * math.cos(2.0 * math.pi * k / n), cy + r * math.sin(2.0 * math.pi * k / n), z + dz_bot)) for k in range(n)]
    mc.cara(tuple(top), clave)
    mc.cara(tuple(bot[::-1]), clave)
    for k in range(n):
        mc.cara((top[k], bot[k], bot[(k + 1) % n], top[(k + 1) % n]), clave)


def _losa_filas(mc, filas, clave, dz_top=0.06, dz_bot=-0.6):
    """Losa cerrada (calzada / piazzola) por filas [((xl, yl, zl), (xr, yr, zr))]: cara superior a
    z + dz_top, inferior a z + dz_bot, laterales y tapas (objeto con recalc: normales hacia fuera)."""
    vs = []
    for (l_, r_) in filas:
        vs.append((mc.vert((l_[0], l_[1], l_[2] + dz_top)), mc.vert((r_[0], r_[1], r_[2] + dz_top)),
                   mc.vert((r_[0], r_[1], r_[2] + dz_bot)), mc.vert((l_[0], l_[1], l_[2] + dz_bot))))
    for k in range(len(vs) - 1):
        a, b = vs[k], vs[k + 1]
        mc.cara((a[0], a[1], b[1], b[0]), clave)
        mc.cara((a[3], b[3], b[2], a[2]), clave)
        mc.cara((a[1], a[2], b[2], b[1]), clave)
        mc.cara((a[0], b[0], b[3], a[3]), clave)
    if len(vs) >= 2:
        mc.cara((vs[0][3], vs[0][2], vs[0][1], vs[0][0]), clave)
        mc.cara((vs[-1][0], vs[-1][1], vs[-1][2], vs[-1][3]), clave)


# ----------------------------------------------------------------- preparacion de muestras
def _preparar(muestras, contexto):
    P = np.array([[float(m['x']), float(m['y'])] for m in muestras])
    Z = np.array([float(m['z']) for m in muestras])
    Nn = np.array([[float(m['nx']), float(m['ny'])] for m in muestras])
    W = np.array([float(m['w']) for m in muestras])
    C = P.mean(axis=0)
    dots = ((C[None, :] - P) * Nn).sum(axis=1)
    side = 1.0 if (dots > 0).sum() >= len(P) / 2.0 else -1.0
    inward = side * Nn
    B = P + inward * (W / 2.0)[:, None]
    Cl = B + inward * 0.6
    n = len(P)

    def borde_de(lista):
        out = []
        for m in lista:
            nx_, ny_ = float(m['nx']) * side, float(m['ny']) * side
            out.append(((float(m['x']) + nx_ * float(m['w']) / 2.0, float(m['y']) + ny_ * float(m['w']) / 2.0), float(m['z'])))
        return out

    antes, despues = (contexto or (None, None))
    ext_a, ext_d = [], []
    if antes:
        lst = borde_de(antes)[-25:]
        for k, (pt, z) in enumerate(lst):
            d = 2.0 * (len(lst) - k)
            ext_a.append((pt, z, 0.85 * max(0.0, d - 5.0)))
    else:
        ux, uy = _unit(B[0][0] - B[3][0], B[0][1] - B[3][1])
        dz = max(-0.2, min(0.2, (Z[0] - Z[3]) / 3.0))
        for k in range(20, 0, -1):
            ext_a.append(((B[0][0] + ux * 2.0 * k, B[0][1] + uy * 2.0 * k), Z[0] + dz * k, 0.85 * max(0.0, 2.0 * k - 5.0)))
    if despues:
        lst = borde_de(despues)[:25]
        for k, (pt, z) in enumerate(lst):
            d = 2.0 * (k + 1)
            ext_d.append((pt, z, 0.85 * max(0.0, d - 5.0)))
    else:
        ux, uy = _unit(B[-1][0] - B[-4][0], B[-1][1] - B[-4][1])
        dz = max(-0.2, min(0.2, (Z[-1] - Z[-4]) / 3.0))
        for k in range(1, 21):
            ext_d.append(((B[-1][0] + ux * 2.0 * k, B[-1][1] + uy * 2.0 * k), Z[-1] + dz * k, 0.85 * max(0.0, 2.0 * k - 5.0)))
    Bx = np.array([e[0] for e in ext_a] + [tuple(b) for b in B] + [e[0] for e in ext_d])
    Zb = np.array([e[1] for e in ext_a] + list(Z) + [e[1] for e in ext_d])
    Rb = np.array([e[2] for e in ext_a] + [0.0] * n + [e[2] for e in ext_d])
    return {'P': P, 'Z': Z, 'N': Nn, 'W': W, 'C': C, 'side': side, 'inward': inward, 'B': B, 'Cl': Cl,
            'Bx': Bx, 'Zb': Zb, 'Rb': Rb, 'n': n}


def _disenar_macizo(prep, params):
    P, Z, B, Cl, inward, C = prep['P'], prep['Z'], prep['B'], prep['Cl'], prep['inward'], prep['C']
    n = prep['n']
    ua = _unit(B[0][0] - C[0], B[0][1] - C[1])
    ub = _unit(B[-1][0] - C[0], B[-1][1] - C[1])
    u_open = _unit(ua[0] + ub[0], ua[1] + ub[1])
    desp = float(params.get('desplaza_cumbre', 24.0))
    S0 = (C[0] + u_open[0] * desp, C[1] + u_open[1] * desp)
    z_c = float(params.get('z_cumbre', 106.0))
    mac = _Macizo(p=8.0)
    mac.domo(S0[0], S0[1], z_c, float(params.get('R_cumbre', 150.0)), 2.0, 2.0)
    u_in = _unit(B[0][0] - B[20][0], B[0][1] - B[20][1])
    K1 = (Cl[24][0] + inward[24][0] * 28.0, Cl[24][1] + inward[24][1] * 28.0)
    K2 = (Cl[2][0] + inward[2][0] * 28.0, Cl[2][1] + inward[2][1] * 28.0)
    mac.domo(K1[0], K1[1], Z[24] + 36.0, 95.0, 2.0, 1.4)
    mac.domo(K2[0], K2[1], Z[2] + 24.0, 78.0, 2.0, 1.4)
    mac.domo(K2[0] + u_in[0] * 26.0, K2[1] + u_in[1] * 26.0, 0.72 * (Z[2] + 24.0), 52.0, 2.0, 1.4)
    mac.domo(K2[0] + u_in[0] * 46.0, K2[1] + u_in[1] * 46.0, 0.40 * (Z[2] + 24.0), 36.0, 2.0, 1.4)
    mac.domo(K2[0] + u_in[0] * 62.0, K2[1] + u_in[1] * 62.0, 0.14 * (Z[2] + 24.0), 24.0, 2.0, 1.4)
    K5 = (Cl[-30][0] + inward[-30][0] * 30.0, Cl[-30][1] + inward[-30][1] * 30.0)
    mac.domo(K5[0], K5[1], Z[-30] + 40.0, 70.0, 2.0, 1.4)
    for i in range(0, n, 18):
        c = (Cl[i][0] + inward[i][0] * 30.0, Cl[i][1] + inward[i][1] * 30.0)
        if 16 <= i <= n - 17:
            mac.domo(c[0], c[1], Z[i] + 34.0, 54.0, 2.2, 0.9)
        else:
            mac.domo(c[0], c[1], Z[i] + 26.0, 56.0, 2.0, 1.4)
    th_a = math.atan2(B[0][1] - S0[1], B[0][0] - S0[0])
    th_b = math.atan2(B[-1][1] - S0[1], B[-1][0] - S0[0])
    pol = _Polar(S0, th_a, _ang_norm(th_b - th_a))
    return mac, pol, u_open, z_c


def _disenar_rasgos(prep, G, M, pol, u_open, z_c, z_mar, params, seed, cb, log):
    """Plaza, terrazas (curvas de nivel) y escaleras en zigzag. Devuelve dict D."""
    rnd = random.Random(seed * 31 + 7)
    S0 = pol.S0
    D = {'rasgos': [], 'tramos': [], 'rellanos': [], 'terrazas': []}
    # --- plaza irregular en la cumbre (deja un cerrete rocoso hacia el lazo)
    z_pl = z_c - 9.0
    Pz = (S0[0] + u_open[0] * 20.0, S0[1] + u_open[1] * 20.0)
    poly = []
    for k in range(20):
        a = 2 * math.pi * k / 20.0
        rr = 20.0 + 3.0 * _vnoise2(np.array([k * 7.3]), np.array([seed * 1.0]), 2.5, seed + 41)[0] + rnd.uniform(-0.8, 0.8)
        rr = max(17.0, min(23.5, rr))
        poly.append((Pz[0] + rr * math.cos(a), Pz[1] + rr * math.sin(a)))
    D['rasgos'].append(_Rasgo('plaza', poly, z_pl, nivel_corte=z_pl + 0.6))
    D['plaza'] = {'centro': Pz, 'z': z_pl, 'poligono': poly}
    # --- terrazas talladas siguiendo las curvas de nivel del macizo
    r2, T2 = _terraza_nivel('terraza_alta', G, M, pol, cb, z_c - 50.0, 0.30, 0.80, log)
    r1, T1 = _terraza_nivel('terraza_baja', G, M, pol, cb, z_c - 78.0, 0.34, 0.77, log, lejos_de=T2['front'], d_min=15.5)
    D['rasgos'] += [r1, r2]
    D['terrazas'] = [T2, T1]

    def r_front(T, th):
        v = _r_frente(T, pol, th)
        return v if v is not None else pol.r_donde(G, M, th, T['z'] - 1.0, r0=20.0)

    def r_back(T, th):
        return pol.r_donde(G, M, th, T['z'] + 10.5, r0=20.0)

    def rim(th):
        return _rim_desde(poly, S0, th)

    def zigzag(nombre, pts, z0, z1, ancho=1.8):
        n_tr = len(pts) - 1
        L = [math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(n_tr)]
        tot = sum(L) or 1.0
        z = z0
        for k in range(n_tr):
            z_n = z0 + (z1 - z0) * sum(L[:k + 1]) / tot
            D['tramos'].append({'nombre': '%s_%d' % (nombre, k), 'p0': pts[k], 'p1': pts[k + 1], 'z0': z, 'z1': z_n, 'ancho': ancho})
            D['rasgos'].append(_rasgo_tramo('%s_%d' % (nombre, k), pts[k], pts[k + 1], z, z_n, ancho))
            if k > 0:
                D['rasgos'].append(_rasgo_codo('rellano_%s_%d' % (nombre, k), pts[k - 1], pts[k], pts[k + 1], z))
            z = z_n

    # E1: plaza -> T2, 4 tramos a +-8 grados (empieza y acaba en th_s + dth)
    th_s = pol.th(0.52)
    dth = math.radians(8.0)
    r_a = rim(th_s + dth) - 0.6
    r_b = r_back(T2, th_s + dth) + 2.2
    pts = [pol.xy(r_a + (r_b - r_a) * k / 4.0, th_s + dth * (1.0 if k % 2 == 0 else -1.0)) for k in range(5)]
    zigzag('esc_plaza', pts, z_pl, T2['z'])
    T2['ocupados'].append((pts[-1][0], pts[-1][1], 4.5))
    D['plaza']['r_rim_escalera'] = rim(th_s + dth)
    D['plaza']['th_escalera'] = th_s + dth
    # E2: T2 -> T1, 2 tramos a +-9 grados (empieza y acaba en th_2 - dth2)
    th_2 = pol.th(0.66)
    dth2 = math.radians(9.0)
    r_a = r_front(T2, th_2 - dth2) - 2.2
    r_b = r_back(T1, th_2 - dth2) + 2.2
    pts = [pol.xy(r_a + (r_b - r_a) * k / 2.0, th_2 + dth2 * (-1.0 if k % 2 == 0 else 1.0)) for k in range(3)]
    zigzag('esc_t2_t1', pts, T2['z'], T1['z'])
    T2['ocupados'].append((pts[0][0], pts[0][1], 4.5))
    T1['ocupados'].append((pts[-1][0], pts[-1][1], 4.5))
    return D, T1, T2, z_pl


def _carretera_desde_pista(nombre, prep, D, j, xy_resto, z_fin, llano_fin, log, pretil_fin=1.6):
    """Parte comun de las carreteras de acceso en coche (H2-5). RELLANO-boca de 6.4 m junto al
    tablero en la muestra j (o = 0.62..3.9), inclinado con la pendiente LONGITUDINAL de la pista (en
    el paso alto, 12 %: sin escalon en la boca); calzada desde o = 0.65 con un tramo perpendicular de
    9 m y despues la polilinea xy_resto (ya tangente en R1); rasante con la cota del rellano los
    primeros 10 m, z_fin los ultimos llano_fin m y transiciones parabolicas (media movil de 9 m);
    pendiente transversal de la boca que se anula a los 10 m; banda tallada en la roca (_RasgoCinta) y
    valla de cierre a 6 m de la boca; pretiles de piedra hasta pretil_fin m antes del final (donde
    empieza la piazzola). Anade el rellano (tipo 'carretera') y la carretera a D y devuelve el dict
    de la carretera."""
    Cl, inward, P, Z = prep['Cl'], prep['inward'], prep['P'], prep['Z']
    tx, ty = _unit(P[j + 1][0] - P[j - 1][0], P[j + 1][1] - P[j - 1][1])
    ix, iy = inward[j]
    sr = SEMI_RELLANO_CARR
    c0 = (Cl[j][0] + ix * 0.02, Cl[j][1] + iy * 0.02)
    c1 = (Cl[j][0] + ix * 3.3, Cl[j][1] + iy * 3.3)
    poly = [(c0[0] - tx * sr, c0[1] - ty * sr), (c0[0] + tx * sr, c0[1] + ty * sr),
            (c1[0] + tx * sr, c1[1] + ty * sr), (c1[0] - tx * sr, c1[1] - ty * sr)]
    z_r = float(Z[j]) - 0.1
    g_t = (float(Z[j + 1]) - float(Z[j - 1])) / max(1e-6, math.hypot(P[j + 1][0] - P[j - 1][0], P[j + 1][1] - P[j - 1][1]))
    cx_, cy_ = float(Cl[j][0]), float(Cl[j][1])

    def nivel_rellano(X, Y, cx_=cx_, cy_=cy_, tx=tx, ty=ty, g_t=g_t, z_r=z_r):
        return z_r + g_t * ((X - cx_) * tx + (Y - cy_) * ty)

    D['rasgos'].append(_Rasgo('rellano_' + nombre, poly, z_r, nivel_fn=nivel_rellano))
    pl0 = g_t * (tx * (-iy) + ty * ix)          # pendiente hacia la izquierda de la marcha de la carretera
    R0 = (Cl[j][0] + ix * 0.05, Cl[j][1] + iy * 0.05)
    R1 = (Cl[j][0] + ix * 9.0, Cl[j][1] + iy * 9.0)
    xy = _remuestrear_arco([R0, R1] + list(xy_resto), 1.0)
    acum = [0.0]
    for k in range(1, len(xy)):
        acum.append(acum[-1] + math.hypot(xy[k][0] - xy[k - 1][0], xy[k][1] - xy[k - 1][1]))
    L = acum[-1]
    s_m, s_e = 10.0, max(12.0, L - llano_fin)
    z_lin = [z_r + (z_fin - z_r) * max(0.0, min(1.0, (s_ - s_m) / (s_e - s_m))) for s_ in acum]
    zs = [sum(z_lin[max(0, k - 4):k + 5]) / float(len(z_lin[max(0, k - 4):k + 5])) for k in range(len(z_lin))]
    zs[0], zs[-1] = z_r, z_fin
    pend = max(abs(zs[k + 1] - zs[k]) / max(1e-6, acum[k + 1] - acum[k]) for k in range(len(zs) - 1))
    pls = [pl0 * max(0.0, 1.0 - s_ / s_m) for s_ in acum]
    pts3 = [(p[0], p[1], z, q) for p, z, q in zip(xy, zs, pls)]
    semi = ANCHO_CARR / 2.0 + PRETIL_CARR + HOMBRO_CARR
    D['rasgos'].append(_RasgoCinta('carretera_' + nombre, pts3, semi))
    # valla CERRADA de lado a lado de la calzada a 6 m de la boca (pendiente transversal ya al 40 %)
    valla = None
    k_v = min(range(len(acum)), key=lambda k: abs(acum[k] - 6.0))
    if 0 < k_v < len(xy) - 1:
        vx, vy = _unit(xy[k_v + 1][0] - xy[k_v - 1][0], xy[k_v + 1][1] - xy[k_v - 1][1])
        a2 = ANCHO_CARR / 2.0 - 0.05
        valla = ((xy[k_v][0] + vy * a2, xy[k_v][1] - vx * a2), (xy[k_v][0] - vy * a2, xy[k_v][1] + vx * a2))
    D['rellanos'].append({'nombre': nombre, 'j': int(j), 'x': float(Cl[j][0] + ix * 1.6), 'y': float(Cl[j][1] + iy * 1.6),
                          'z': z_r, 'valla': valla, 'poly': poly, 'tx': (tx, ty), 'inward': (float(ix), float(iy)),
                          'tipo': 'carretera', 'ancho': 2.0 * sr, 'z_valla': zs[k_v] + 0.06, 'pl_valla': pls[k_v]})
    c = {'nombre': nombre, 'pts': pts3, 'ancho': ANCHO_CARR, 'semi': semi, 'largo': L, 'pend_max': pend,
         'radio_min': _radio_min(xy[1:-1]), 'piazzola': [], 'z_piazzola': z_fin, 'terraza': None, 'j': int(j),
         's_pretil': (1.2, L - pretil_fin), 's_valla': acum[k_v], 'piazzola_min': 0}
    D.setdefault('carreteras', []).append(c)
    return c


def _disenar_carretera_cala(prep, D, pol, G, M, cb, log, radio_min=11.0):
    """H2-5 (2): carretera de la CALA para coches. Boca en la pista al final del lazo (lado del
    lobulo), LITORANEA alrededor del lobulo y PIAZZOLA de giro (r 6.5 m, pavimentada) en el extremo O
    del muelle, tallada en el pie del lobulo; el muelle (delante de las casas de pescadores, que miran
    al mar en abanico) queda peatonal: entre las casas y el noray solo hay 2.3-2.9 m. La
    litoranea sigue la curva de nivel M = z_rasante + 1 (z_rasante baja con el angulo f de la cota
    del tablero a la del muelle) con el eje 2.5 m tierra adentro: por el lado del mar la banda
    queda a ras del terreno (sin muro de roca que tape el mar ni relleno colgado) y por el de tierra
    va en desmonte. Uniones boca -> litoranea y litoranea -> piazzola por Bezier de radio >= radio_min.
    Devuelve la carretera o None (y lo explica en el log)."""
    cala = D.get('cala')
    if not cala:
        return None
    Cl, inward, Z, n = prep['Cl'], prep['inward'], prep['Z'], prep['n']
    fs, R, z_q = cala['fs'], cala['R'], float(cala['z'])
    f_w = max(fs)                                 # extremo del muelle hacia el final del lazo (f -> 1)
    if f_w > 0.9:
        log('carretera de la cala: el muelle llega a f %.2f, sin sitio para la litoranea' % f_w)
        return None
    z_boca = float(Z[n - 8]) - 0.1
    f_b = 0.97
    F_ = (np.arctan2(G.Y - pol.S0[1], G.X - pol.S0[0]) - pol.th_a + math.pi) % (2.0 * math.pi) - math.pi
    F_ = F_ / pol.span
    z_t = z_q + (z_boca - z_q) * np.clip((F_ - f_w) / (f_b - f_w), 0.0, 1.0)
    campo = M - z_t
    o_f = cb['o']

    def f_de(p):
        return _ang_norm(math.atan2(p[1] - pol.S0[1], p[0] - pol.S0[0]) - pol.th_a) / pol.span

    def dentro(x, y):
        f = f_de((x, y))
        return f_w - 0.03 < f < 1.08 and float(G.muestrear(o_f, x, y)) > 8.0

    f_m = (f_w + 1.0) / 2.0
    th_m = pol.th(f_m)
    p0 = pol.xy(pol.r_donde(G, campo, th_m, 1.0, r0=60.0), th_m)
    if not dentro(*p0):
        log('carretera de la cala: sin orilla del lobulo en f %.2f' % f_m)
        return None
    pts, nrm = _trazar_contorno(G, campo, p0, 1.0, dentro, paso=2.0, max_pts=400)
    if len(pts) < 25:
        log('carretera de la cala: curva de nivel demasiado corta (%d puntos)' % len(pts))
        return None
    eje = [(p[0] + u[0] * 2.5, p[1] + u[1] * 2.5) for p, u in zip(pts, nrm)]
    if f_de(eje[0]) < f_de(eje[-1]):
        eje = eje[::-1]                           # del final del lazo hacia la cala
    eje = _remuestrear_arco(eje, 2.0)
    for _ in range(60):
        if _radio_min(_remuestrear_arco(eje, 1.0)) >= radio_min + 3.0:
            break
        eje = _suavizar_polilinea(eje, 2)
    eje = _remuestrear_arco(eje, 1.0)
    # PIAZZOLA de llegada (giro) en el extremo O del muelle, tallada en el pie del lobulo a la cota del
    # muelle: centro a mitad del fondo del muelle y pasado su extremo lo justo para dejar 1.5 m a la casa
    # mas al O posible (f = f_c + 0.08, ancho real 4.17 m a cada lado); el muelle sigue siendo peatonal
    f_casa = cala['f'] + 0.08
    R_c = float(np.interp(f_casa, fs, R))
    r_pz = (float(np.interp(f_w, fs, R)) + float(np.interp(f_w, fs, cala['rb']))) / 2.0
    f_pz = f_casa + (4.17 / max(1.0, R_c - 10.4) + (RADIO_PIAZZOLA_CALA + 1.5) / r_pz) / abs(pol.span)
    Cpz = pol.xyf(r_pz, f_pz)

    def union(a, ta, b, tb):
        k_ = 0.4 * math.hypot(b[0] - a[0], b[1] - a[1])
        return _bezier(a, (a[0] + ta[0] * k_, a[1] + ta[1] * k_), (b[0] - tb[0] * k_, b[1] - tb[1] * k_), b, 240)

    def tang(lst, k):
        a, b = lst[max(0, k - 2)], lst[min(len(lst) - 1, k + 2)]
        return _unit(b[0] - a[0], b[1] - a[1])

    # boca: muestra j del final del lazo y punto k de la litoranea con la union mas corta de radio >= radio_min
    mejor = None
    for j in range(n - 3, max(2, n - 46), -2):
        ix, iy = inward[j]
        R1 = (Cl[j][0] + ix * 9.0, Cl[j][1] + iy * 9.0)
        for k in range(0, len(eje) - 40, 2):
            if float(G.muestrear(o_f, eje[k][0], eje[k][1])) < 16.0:
                continue
            bz = _remuestrear_arco(union(R1, (ix, iy), eje[k], tang(eje, k)), 1.0)
            if _radio_min(bz) < radio_min:
                continue
            Lb = len(bz) + k
            if mejor is None or Lb < mejor[0]:
                mejor = (Lb, j, k, bz)
            break
    if mejor is None:
        log('carretera de la cala: no cabe la union de la boca con la litoranea (radio >= %.0f m)' % radio_min)
        return None
    _Lb, j, k_a, bz_a = mejor
    # llegada: ultimo punto de la litoranea a >= 12 m de la piazzola desde el que la union (que entra
    # hacia su centro) tiene radio >= radio_min
    k_b, bz_b = None, None
    for k in range(len(eje) - 1, k_a + 20, -1):
        d_ = math.hypot(Cpz[0] - eje[k][0], Cpz[1] - eje[k][1])
        if d_ < 12.0:
            continue
        bz = _remuestrear_arco(union(eje[k], tang(eje, k), Cpz, _unit(Cpz[0] - eje[k][0], Cpz[1] - eje[k][1])), 1.0)
        if _radio_min(bz) >= radio_min:
            k_b, bz_b = k, bz
            break
    if k_b is None:
        log('carretera de la cala: no cabe la union de la litoranea con la piazzola del muelle')
        return None
    cuerpo = bz_a + eje[k_a + 1:k_b] + bz_b
    c = _carretera_desde_pista('acceso_cala', prep, D, j, cuerpo, z_q, RADIO_PIAZZOLA_CALA + 2.0, log,
                               pretil_fin=RADIO_PIAZZOLA_CALA + 1.0)
    c.update({'terraza': 'cala', 'z_piazzola': z_q, 'piazzola_disco': (Cpz[0], Cpz[1], RADIO_PIAZZOLA_CALA)})
    poly_pz = [(Cpz[0] + (RADIO_PIAZZOLA_CALA + 0.4) * math.cos(a_), Cpz[1] + (RADIO_PIAZZOLA_CALA + 0.4) * math.sin(a_))
               for a_ in np.linspace(0.0, 2.0 * math.pi, 25)[:-1]]
    D['rasgos'].append(_Rasgo('piazzola_cala', poly_pz, z_q - 0.04, nivel_corte=z_q + 0.3))
    log('carretera acceso_cala: %d m desde el tablero (muestra %d, z %.2f): union %d m, litoranea %d m y union %d m hasta una '
        'piazzola de r %.1f m en el extremo O del muelle (z %.1f, f %.3f); pendiente max %.1f %%, radio min %.0f m'
        % (c['largo'], j, c['pts'][0][2], len(bz_a), k_b - k_a, len(bz_b), RADIO_PIAZZOLA_CALA, z_q, f_pz,
           100.0 * c['pend_max'], c['radio_min']))
    return c


def _disenar_accesos(prep, D, pol, T1, T2, G, M, log=print):
    """Accesos desde el tablero: T2 -> paso alto (entrada) por una CARRETERA de coche (H2-5:
    rellano-boca de 6.4 m con valla cerrada y piazzola en el extremo de T2); T1 -> paso bajo
    (salida) por escalera hasta un RELLANO junto al tablero (o = 0.6..3.3, 4.6 m de largo) con
    valla y puerta."""
    Cl, inward, P, Z, n = prep['Cl'], prep['inward'], prep['P'], prep['Z'], prep['n']

    def acceso(nombre, T, f, rango, lado):
        th = pol.th(f)
        r_f = _r_frente(T, pol, th)
        if r_f is None:
            r_f = pol.r_donde(G, M, th, T['z'] - 1.0, r0=20.0)
        ini = pol.xy(r_f - 2.4, th)
        T['ocupados'].append((ini[0], ini[1], 4.5))
        j = min(rango, key=lambda i: (Cl[i][0] - ini[0]) ** 2 + (Cl[i][1] - ini[1]) ** 2)
        j = max(2, min(n - 3, j))
        tx, ty = _unit(P[j + 1][0] - P[j - 1][0], P[j + 1][1] - P[j - 1][1])
        ix, iy = inward[j]
        c0 = (Cl[j][0] + ix * 0.02, Cl[j][1] + iy * 0.02)
        c1 = (Cl[j][0] + ix * 3.3, Cl[j][1] + iy * 3.3)
        poly = [(c0[0] - tx * 2.3, c0[1] - ty * 2.3), (c0[0] + tx * 2.3, c0[1] + ty * 2.3),
                (c1[0] + tx * 2.3, c1[1] + ty * 2.3), (c1[0] - tx * 2.3, c1[1] - ty * 2.3)]
        z_r = float(Z[j]) - 0.1
        D['rasgos'].append(_Rasgo('rellano_' + nombre, poly, z_r, nivel_corte=z_r))
        fin = (Cl[j][0] + ix * 3.6, Cl[j][1] + iy * 3.6)
        # tramo (uno o dos, con codo) desde la terraza hasta el rellano
        L = math.hypot(fin[0] - ini[0], fin[1] - ini[1])
        if L > 48.0:
            mx, my = (ini[0] + fin[0]) / 2.0, (ini[1] + fin[1]) / 2.0
            px, py = -(fin[1] - ini[1]) / L, (fin[0] - ini[0]) / L
            mid = (mx + px * 5.0 * lado, my + py * 5.0 * lado)
            z_m = T['z'] + (z_r - T['z']) * 0.5
            puntos = [(ini, mid, T['z'], z_m), (mid, fin, z_m, z_r)]
        else:
            puntos = [(ini, fin, T['z'], z_r)]
        for k, (a, b, za, zb) in enumerate(puntos):
            D['tramos'].append({'nombre': '%s_%d' % (nombre, k), 'p0': a, 'p1': b, 'z0': za, 'z1': zb, 'ancho': 1.8})
            D['rasgos'].append(_rasgo_tramo('%s_%d' % (nombre, k), a, b, za, zb, 1.8))
            if k > 0:
                D['rasgos'].append(_rasgo_codo('rellano_%s_%d' % (nombre, k), puntos[k - 1][0], a, b, za))
        # v3 (remate): verja EN el hueco del pretil del viaducto (mitad trasera, a O_VERJA del asfalto medido sobre
        # el borde curvo) y LOSA de umbral desde O_LOSA_PUERTA hasta Cl + 1.3 (tapa el escalon roca-rellano y el
        # canto del tablero). El integrador ya no la mueve ni pone la suya (info['puertas'][k]['valla'] = None).
        Bj = prep['B'][j]
        valla = tuple(_retranquear(prep, (Bj[0] + ix * O_VERJA + tx * sg_ * 2.3, Bj[1] + iy * O_VERJA + ty * sg_ * 2.3), O_VERJA)
                      for sg_ in (-1.0, 1.0))
        losa = [_retranquear(prep, (Bj[0] + ix * O_LOSA_PUERTA - tx * 2.3, Bj[1] + iy * O_LOSA_PUERTA - ty * 2.3), O_LOSA_PUERTA),
                _retranquear(prep, (Bj[0] + ix * O_LOSA_PUERTA + tx * 2.3, Bj[1] + iy * O_LOSA_PUERTA + ty * 2.3), O_LOSA_PUERTA),
                (Cl[j][0] + ix * 1.3 + tx * 2.3, Cl[j][1] + iy * 1.3 + ty * 2.3),
                (Cl[j][0] + ix * 1.3 - tx * 2.3, Cl[j][1] + iy * 1.3 - ty * 2.3)]
        D['rellanos'].append({'nombre': nombre, 'j': int(j), 'x': float(Cl[j][0] + ix * 1.6), 'y': float(Cl[j][1] + iy * 1.6),
                              'z': z_r, 'valla': valla, 'poly': poly, 'tx': (tx, ty), 'inward': (float(ix), float(iy)),
                              'losa': losa, 'verja_en_hueco': True})
        return j

    def carretera(nombre, T, f, rango):
        """H2-5: CARRETERA de acceso en coche (sustituye a la escalera de ese acceso) que entra por
        detras en la repisa de la terraza T hasta una PIAZZOLA pavimentada en su extremo (sin casas).
        Boca, rasante y valla: _carretera_desde_pista."""
        fs_T = T['fs']
        i_f = max(1, min(len(fs_T) - 2, min(range(len(fs_T)), key=lambda k: abs(fs_T[k] - f))))
        P_f, n_up = T['front'][i_f], T['nrm'][i_f]
        marg = [max(0.0, min(1.0, min(q - T['f0'], T['f1'] - q) / 0.06)) for q in fs_T]
        prof = [min(float(T['anchos'][i]), 14.0 * marg[i]) - 1.0 for i in range(len(fs_T))]
        dp = max(6.0, min(prof[i_f], 11.0))
        E = (P_f[0] + n_up[0] * dp, P_f[1] + n_up[1] * dp)
        j = min(rango, key=lambda i: (Cl[i][0] - P_f[0]) ** 2 + (Cl[i][1] - P_f[1]) ** 2)
        j = max(2, min(n - 3, j))
        ix, iy = inward[j]
        R1 = (Cl[j][0] + ix * 9.0, Cl[j][1] + iy * 9.0)
        k_ = 0.4 * math.hypot(E[0] - R1[0], E[1] - R1[1])
        crv = _bezier(R1, (R1[0] + ix * k_, R1[1] + iy * k_), (E[0] + n_up[0] * k_, E[1] + n_up[1] * k_), E, 240)
        fin = (E[0] - n_up[0] * 0.4, E[1] - n_up[1] * 0.4)          # 0.4 m dentro de la piazzola
        # piazzola: filas del frente desde la llegada hacia el extremo de la terraza (alli no hay casas)
        dir_e = 1 if fs_T[-1] < fs_T[0] else -1
        if f > (T['f0'] + T['f1']) / 2.0:
            dir_e = -dir_e
        filas = []
        for i in range(i_f - 2 * dir_e, i_f + 7 * dir_e, dir_e):
            if 0 <= i < len(fs_T) and prof[i] >= 3.0:
                pf, nu = T['front'][i], T['nrm'][i]
                d_i = min(dp, prof[i])
                filas.append(((pf[0] + nu[0] * 0.6, pf[1] + nu[1] * 0.6, T['z']), (pf[0] + nu[0] * d_i, pf[1] + nu[1] * d_i, T['z'])))
        c = _carretera_desde_pista(nombre, prep, D, j, crv + [fin], T['z'], 3.0, log)
        c.update({'piazzola': filas, 'z_piazzola': T['z'], 'terraza': T['nombre'], 'piazzola_min': 3})
        T['ocupados'].append((E[0], E[1], 4.5))
        log('carretera %s: %d m desde el tablero (muestra %d, z %.2f) hasta la piazzola de %s (z %.1f, %d filas, fondo %.1f m); '
            'pendiente max %.1f %%, radio min %.0f m' % (nombre, c['largo'], j, c['pts'][0][2], T['nombre'], T['z'], len(filas), dp,
                                                       100.0 * c['pend_max'], c['radio_min']))
        return j

    carretera('acceso_alto', T2, T2['f0'] + 0.06, range(0, min(n, 90)))
    acceso('acceso_bajo', T1, T1['f1'] - 0.06, range(max(0, n - 110), n), 1.0)


def _disenar_cala(prep, D, pol, T1, G, M, z_mar, log):
    """Cala de pescadores en el lado abierto: banda de muelle a z_mar + 2
    (relleno hacia el mar, tallado hacia la roca) cuyo fondo se queda a
    >= 8.5 m del frente de T1, y senda T1 -> muelle (tramo corto a 45 grados
    del borde + tramo oblicuo a lo largo del acantilado, <= ~34 grados)."""
    f_c = 0.53
    m = 14
    fs = [f_c - 0.13 + 0.26 * k / float(m) for k in range(m + 1)]
    R = [pol.r_donde(G, M, pol.th(f), z_mar + 0.6, r0=40.0) for f in fs]
    log('cala: orilla por f: %s' % ' '.join('%.2f:%.0f' % (f, r) for f, r in zip(fs[::2], R[::2])))
    if max(R) > 280.0:
        D['cala'] = None
        return
    R = _suavizar_lista(R, 3)
    z_q = z_mar + 2.0
    r1 = []
    for f in fs:
        v = _r_frente(T1, pol, pol.th(f))
        r1.append(v if v is not None else pol.r_donde(G, M, pol.th(f), T1['z'] - 1.0, r0=20.0))
    rf = [r + 4.0 for r in R]
    rb = [min(max(R[i] - 22.0, r1[i] + 8.5), R[i] - 12.0) for i in range(len(fs))]
    rb = _suavizar_lista(rb, 2)
    front = [pol.xyf(rf[i], fs[i]) for i in range(len(fs))]
    back = [pol.xyf(rb[i], fs[i]) for i in range(len(fs))]
    poly = front + back[::-1]
    i_c = m // 2
    th_c = pol.th(f_c)
    log('cala: muelle de %.0f..%.0f m de fondo (frente de T1 a %.0f..%.0f m de la orilla)'
        % (min(rf[i] - rb[i] for i in range(len(fs))), max(rf[i] - rb[i] for i in range(len(fs))),
           min(R[i] - r1[i] for i in range(len(fs))), max(R[i] - r1[i] for i in range(len(fs)))))

    def interp(lista, f):
        i = min(range(len(fs)), key=lambda k: abs(fs[k] - f))
        return lista[i]

    # senda: arranca donde mas sitio radial hay entre el frente de T1 y el fondo del muelle
    cand = [(rb[i] - r1[i], fs[i]) for i in range(1, len(fs) - 1) if T1['f0'] + 0.04 < fs[i] < T1['f1'] - 0.04]
    if cand:
        sitio, f_p = max(cand)
        dz_tot = T1['z'] - z_q
        L_req = dz_tot / math.tan(math.radians(34.0))
        # El acantilado entre T1 y el muelle es corto (~10 m) y alto (26 m): la escalera no
        # zigzaguea a traves de el (cada rellano seria una muesca en el borde de la repisa)
        # sino que se SEPARA del borde 7.5 m a 45 grados (tramo A) y baja en un solo tramo
        # OBLICUO a lo largo de la pared hasta el fondo del muelle (tramo B), con la
        # pendiente limitada a ~34 grados.
        i_f = min(range(len(T1['fs'])), key=lambda k: abs(T1['fs'][k] - f_p))
        P_f = T1['front'][i_f]
        n_up = T1['nrm'][i_f]
        u = (-n_up[0], -n_up[1])
        P_s = (P_f[0] + n_up[0] * 1.0, P_f[1] + n_up[1] * 1.0)
        up = T1['rasgo'].lado_up.astype(np.float64)
        back_fino = _remuestrear(back, 1.0)
        mejor = None
        for sg_t in (1.0, -1.0):
            tt = (-u[1] * sg_t, u[0] * sg_t)
            dA = _unit(u[0] + tt[0], u[1] + tt[1])
            pA = (P_s[0] + dA[0] * 7.5, P_s[1] + dA[1] * 7.5)
            opciones = []
            for q in back_fino:
                th_q = math.atan2(q[1] - pol.S0[1], q[0] - pol.S0[0])
                E = (q[0] + math.cos(th_q) * 2.2, q[1] + math.sin(th_q) * 2.2)
                if (E[0] - pA[0]) * tt[0] + (E[1] - pA[1]) * tt[1] < 4.0 or not _dentro_poligono(poly, E[0], E[1]):
                    continue
                LB = math.hypot(E[0] - pA[0], E[1] - pA[1])
                opciones.append((abs(7.5 + LB - L_req), LB, E))
            if not opciones:
                continue
            opciones.sort()
            _d, LB, E = opciones[0]
            pts_B = [(pA[0] + (E[0] - pA[0]) * t, pA[1] + (E[1] - pA[1]) * t) for t in np.linspace(0.0, 1.0, max(2, int(LB / 2.0)))]
            malo = sum(1 for p in pts_B if float(G.muestrear(up, p[0], p[1])) > 0.5 and _dist_polilinea(T1['front'], p[0], p[1]) > 1.0)
            ang = math.degrees(math.atan2(dz_tot, 7.5 + LB))
            if mejor is None or (malo, ang) < (mejor[0], mejor[1]):
                mejor = (malo, ang, pA, E, LB)
        if mejor is None:
            E = pol.xyf(interp(rb, f_p) + 2.2, f_p)
            pA = (P_s[0] + u[0] * 7.5, P_s[1] + u[1] * 7.5)
            mejor = (0, 0.0, pA, E, math.hypot(E[0] - pA[0], E[1] - pA[1]))
        malo, ang, pA, E, LB = mejor
        pts = [P_s, pA, E]
        n_tr = 2
        L = [math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(n_tr)]
        tot = sum(L) or 1.0
        if malo:
            log('cala: AVISO %d puntos del tramo oblicuo caen sobre la repisa de T1' % malo)
        z = T1['z']
        for k in range(n_tr):
            z_n = T1['z'] + (z_q - T1['z']) * sum(L[:k + 1]) / tot
            D['tramos'].append({'nombre': 'esc_cala_%d' % k, 'p0': pts[k], 'p1': pts[k + 1], 'z0': z, 'z1': z_n, 'ancho': 1.8})
            D['rasgos'].append(_rasgo_tramo('esc_cala_%d' % k, pts[k], pts[k + 1], z, z_n, 1.8))
            if k > 0:
                D['rasgos'].append(_rasgo_codo('rellano_cala_%d' % k, pts[k - 1], pts[k], pts[k + 1], z))
            z = z_n
        T1['ocupados'].append((pts[0][0], pts[0][1], 4.5))
        ocup = [(pts[-1][0], pts[-1][1], 5.0)]
        log('cala: senda desde f=%.2f: tramo A de %.0f m (45 grados del borde) + tramo B oblicuo de %.0f m (sitio radial %.0f m; %.0f m para %.0f m de desnivel: %.0f grados)'
            % (f_p, L[0], L[1], sitio, tot, dz_tot, math.degrees(math.atan2(dz_tot, tot))))
    else:
        ocup = []
        log('cala: sin sitio para la senda desde T1')
    D['rasgos'].append(_Rasgo('muelle', poly, z_q, nivel_corte=z_q + 1.0))
    D['cala'] = {'f': f_c, 'th': th_c, 'fs': fs, 'R': R, 'rf': rf, 'rb': rb, 'front': front, 'back': back, 'z': z_q,
                 'poly': poly, 'centro': pol.xy(R[i_c] - 10.0, th_c), 'ocupados': ocup}


# ----------------------------------------------------------------- casas y comprobaciones
ALERO = 0.42        # casas_kit_v2 construye 0.42 m mas ancho por cada lado (aleros)
FRENTE = 1.0        # ... y 1.0 m por delante de la fachada (balcones / toldos)
SEP_CASAS = 1.5     # distancia minima entre huellas REALES de dos casas


def _huella(x, y, rot, ancho, fondo):
    """9 puntos de la huella nominal de una casa (pivote en el centro de la
    fachada, cuerpo hacia -Y local)."""
    cr, sr = math.cos(rot), math.sin(rot)
    pts = []
    for ex in (-0.5, 0.0, 0.5):
        for ey in (0.0, -0.5, -1.0):
            lx, ly = ex * ancho * 0.96, ey * fondo * 0.96 - 0.1
            pts.append((x + lx * cr - ly * sr, y + lx * sr + ly * cr))
    return pts


def _rect_casa(x, y, rot, ancho, fondo, margen=0.0):
    """4 esquinas (mundo) de la huella REAL de una casa del kit (aleros y
    balcones incluidos), inflada `margen`: fachada-izq, fachada-der,
    trasera-der, trasera-izq."""
    cr, sr = math.cos(rot), math.sin(rot)
    hx = ancho / 2.0 + ALERO + margen
    y0 = -fondo - ALERO - margen
    y1 = FRENTE + margen
    return [(x + lx * cr - ly * sr, y + lx * sr + ly * cr) for (lx, ly) in ((-hx, y1), (hx, y1), (hx, y0), (-hx, y0))]


def _detras_casa(x, y, rot, ancho, fondo, d=1.5):
    """3 puntos a d m por detras de la trasera real."""
    cr, sr = math.cos(rot), math.sin(rot)
    ly = -fondo - ALERO - d
    return [(x + lx * cr - ly * sr, y + lx * sr + ly * cr) for lx in (-ancho / 2.0, 0.0, ancho / 2.0)]


def _cuadrado(cx, cy, semi, rz):
    cr, sr = math.cos(rz), math.sin(rz)
    return [(cx + lx * cr - ly * sr, cy + lx * sr + ly * cr) for (lx, ly) in ((-semi, -semi), (semi, -semi), (semi, semi), (-semi, semi))]


def _convexos_separados(A, B):
    """True si dos poligonos convexos NO se tocan (teorema del eje separador)."""
    for poly in (A, B):
        n = len(poly)
        for k in range(n):
            ax, ay = poly[k]
            bx, by = poly[(k + 1) % n]
            nx_, ny_ = ay - by, bx - ax
            pa = [p[0] * nx_ + p[1] * ny_ for p in A]
            pb = [p[0] * nx_ + p[1] * ny_ for p in B]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return True
    return False


def _dist_borde(poly, x, y):
    """distancia al contorno de un poligono cerrado."""
    return _dist_polilinea(list(poly) + [poly[0]], x, y)


def _circulo_toca(rect, cx, cy, r):
    return _dentro_poligono(rect, cx, cy) or _dist_borde(rect, cx, cy) < r


def _motivo_casa(c, aceptadas, circulos, poly_ok, margenes, G, H0):
    """None si la casa cabe; si no, el motivo: 'fuera' (huella real fuera
    del poligono), 'borde' (esquinas a menos de margenes=(fachada, trasera)
    del contorno), 'roca' (roca por encima de la base + 0.25 en la huella o
    + 0.3 a 1.5 m detras de la trasera), 'flota' (roca a mas de 0.6 m bajo
    la huella), 'casa' (a menos de SEP_CASAS de otra casa aceptada, huellas
    reales) o 'bloqueo' (toca un circulo de escalera / rellano / fuente)."""
    x, y, z, rot, an, fo = c['x'], c['y'], c['z'], c['rot'], c['ancho'], c['fondo']
    R = _rect_casa(x, y, rot, an, fo)
    if poly_ok is not None:
        for k, (px, py) in enumerate(R):
            if not _dentro_poligono(poly_ok, px, py):
                return 'fuera'
            m = margenes[1] if k >= 2 else margenes[0]
            if m > 0.0 and _dist_borde(poly_ok, px, py) < m:
                return 'borde'
    pts = _huella(x, y, rot, an, fo) + R
    hs = G.muestrear(H0, np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
    if float(hs.max()) > z + 0.25:
        return 'roca'
    if float(hs.min()) < z - 0.6:
        return 'flota'
    det = _detras_casa(x, y, rot, an, fo)
    hd = G.muestrear(H0, np.array([p[0] for p in det]), np.array([p[1] for p in det]))
    if float(hd.max()) > z + 0.3:
        return 'roca'
    Ri = _rect_casa(x, y, rot, an, fo, SEP_CASAS / 2.0)
    for a in aceptadas:
        if math.hypot(a['x'] - x, a['y'] - y) < 40.0 and not _convexos_separados(
                Ri, _rect_casa(a['x'], a['y'], a['rot'], a['ancho'], a['fondo'], SEP_CASAS / 2.0)):
            return 'casa'
    for (cx, cy, r) in circulos:
        if _circulo_toca(R, cx, cy, r):
            return 'bloqueo'
    return None


def _colocar_casa(c, aceptadas, circulos, poly_ok, margenes, G, H0, avance_max=1.2, fondos=None, cuenta=None):
    """Prueba la casa tal cual y, si no cabe, adelantada (hacia la fachada)
    de 0.4 en 0.4 m hasta avance_max y con los fondos de `fondos` (de mayor
    a menor). Devuelve la copia aceptada o None; apunta los motivos de
    rechazo en `cuenta`."""
    fx, fy = -math.sin(c['rot']), math.cos(c['rot'])
    for fondo in (fondos or (c['fondo'],)):
        for paso in range(0, int(round(avance_max / 0.4)) + 1):
            c2 = dict(c)
            c2['fondo'] = fondo
            c2['x'], c2['y'] = c['x'] + fx * 0.4 * paso, c['y'] + fy * 0.4 * paso
            m = _motivo_casa(c2, aceptadas, circulos, poly_ok, margenes, G, H0)
            if m is None:
                return c2
            if cuenta is not None:
                cuenta[m] = cuenta.get(m, 0) + 1
    return None


def _muro_con_huecos(mm, pts, huecos, z_top, z_bot, grosor, clave, lado, cerrada=True, segmentos=()):
    """Muro a lo largo de pts (anillo cerrado o polilinea abierta) menos los
    tramos con algun punto (extremos o medio) a < r de un hueco circular
    (x, y, r) o de un segmento-hueco ((ax, ay), (bx, by), r): el eje de una
    escalera que lo cruza. z_top / z_bot escalares."""
    K = len(pts)
    if K < 2:
        return

    def libre(a, b):
        for (px, py) in (a, b, ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)):
            for (hx, hy, hr) in huecos:
                if math.hypot(px - hx, py - hy) < hr:
                    return False
            for (sa, sb, hr) in segmentos:
                if _dist_polilinea([sa, sb], px, py) < hr:
                    return False
        return True

    runs, cur = [], []
    for k in range(K if cerrada else K - 1):
        a, b = pts[k], pts[(k + 1) % K]
        if libre(a, b):
            if not cur:
                cur.append(a)
            cur.append(b)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if cerrada and len(runs) == 1 and len(runs[0]) == K + 1:
        _muro(mm, pts, z_top, z_bot, grosor, clave, lado=lado, cerrada=True)
        return
    if cerrada and len(runs) >= 2 and runs[0][0] == pts[0] and runs[-1][-1] == pts[0]:
        runs = [runs[-1] + runs[0][1:]] + runs[1:-1]
    for r in runs:
        if len(r) >= 2:
            _muro(mm, r, z_top, z_bot, grosor, clave, lado=lado)


def _rim_desde(poly, c, th, paso=0.25):
    r = 0.0
    for k in range(4, 400):
        x, y = c[0] + k * paso * math.cos(th), c[1] + k * paso * math.sin(th)
        if _dentro_poligono(poly, x, y):
            r = k * paso
        elif r > 0.0:
            break
    return r


RECORTE_PELDANOS = 1.4      # los peldanos paran a 1.4 m del codo (la losa r=1.8 los cubre)
RECORTE_MURETES = 1.9       # los muretes laterales empiezan 0.5 m despues (no tocan la losa)


def _rellano_codo(me, mm, p, z, dirs, r=1.8, n=16):
    """Losa poligonal (16 lados, radio r, cara superior a z + 0.03) en el codo
    de un zigzag, con parapeto de 0.9 m (0.3 m hacia dentro) en los lados a
    mas de 62 grados de todo tramo que entra (dirs: direcciones unitarias de
    los tramos desde el codo): asi no toca peldanos ni muretes."""
    top, bot = [], []
    for k in range(n):
        a = math.pi / n + k * 2.0 * math.pi / n
        x, y = p[0] + r * math.cos(a), p[1] + r * math.sin(a)
        top.append(me.vert((x, y, z + 0.03)))
        bot.append(me.vert((x, y, z - 1.3)))
    me.cara(tuple(top), 'piedra_escalera')
    me.cara(tuple(bot[::-1]), 'piedra_escalera')
    for k in range(n):
        me.cara((top[k], bot[k], bot[(k + 1) % n], top[(k + 1) % n]), 'piedra_escalera')
    lim = math.cos(math.radians(62.0))
    for k in range(n):
        a0 = math.pi / n + k * 2.0 * math.pi / n
        a1 = a0 + 2.0 * math.pi / n
        am = (a0 + a1) / 2.0
        if any(math.cos(am) * d[0] + math.sin(am) * d[1] > lim for d in dirs):
            continue
        pts = [(p[0] + r * math.cos(a0), p[1] + r * math.sin(a0)), (p[0] + r * math.cos(a1), p[1] + r * math.sin(a1))]
        _muro(mm, pts, z + 0.9, z + 0.04, 0.3, 'piedra_muro', lado=1.0)


def _codo_params(dirs):
    """Con el angulo minimo entre los tramos que entran en el codo: a =
    recorte de los peldanos (sus esquinas interiores no se cruzan) y r =
    radio de la losa (cubre los extremos de los peldanos)."""
    th = math.pi
    for i in range(len(dirs)):
        for j in range(i + 1, len(dirs)):
            d = max(-1.0, min(1.0, dirs[i][0] * dirs[j][0] + dirs[i][1] * dirs[j][1]))
            th = min(th, math.acos(d))
    a = max(RECORTE_PELDANOS, min(2.5, 0.9 / math.tan(max(th, 0.35) / 2.0)))
    r = max(1.8, min(2.7, math.sqrt(a * a + 0.81) + 0.1))
    return a, r


def _recorte_murete(d, lat, otros, a_otros, r_losa):
    """Distancia desde el codo a la que puede empezar el murete lateral del
    lado `lat` (+-1) de un tramo de direccion d sin tocar la losa (r_losa)
    ni los peldanos de los otros tramos (rectangulo inflado 0.3 m)."""
    b = max(RECORTE_MURETES, math.sqrt(max(0.0, (r_losa + 0.05) ** 2 - 1.12 ** 2)))
    nx_, ny_ = -d[1], d[0]
    for _ in range(40):
        ok = True
        for (ox, oy) in otros:
            for l_ in (1.12, 1.42):
                px, py = d[0] * b + nx_ * lat * l_, d[1] * b + ny_ * lat * l_
                along = px * ox + py * oy
                perp = abs(-px * oy + py * ox)
                if along >= a_otros - 0.3 and perp <= 1.2:
                    ok = False
        if ok:
            return b
        b += 0.25
    return b


def _construir_obra(parent_collection, raiz, D, T1, T2, pol, prep, z_mar, seed, log, caminos_kit=None):
    """Muros, escaleras (con losa de rellano en los codos del zigzag), vallas,
    plaza empedrada, campanile y cala (mallas propias). Los muros de las
    terrazas y el muro trasero de la cala llevan HUECOS donde los cruza una
    escalera (segmentos de 5 m desde cada extremo de tramo, r = 1.8)."""
    sg = 1.0 if pol.span > 0 else -1.0
    tris = {}
    segs = [(t['p0'], t['p1'], 1.8) for t in D['tramos']]      # ejes de escalera: huecos en los muros
    carrs = D.get('carreteras') or []
    # la carretera entra en la repisa por DETRAS: hueco solo en el muro trasero (nunca en el murete del frente)
    segs_carr = [((c['pts'][k][0], c['pts'][k][1]), (c['pts'][k + 1][0], c['pts'][k + 1][1]), c['semi'] + 0.6)
                 for c in carrs for k in range(len(c['pts']) - 1)]
    mm = _Malla('PENON_puente_muros', ('piedra_muro',))
    for T in (T1, T2):
        if len(T['front']) < 3:
            continue
        k = len(T['front']) // 2
        p0, p1 = T['front'][k], T['front'][k + 1]
        cr = (p1[0] - p0[0]) * (pol.S0[1] - p0[1]) - (p1[1] - p0[1]) * (pol.S0[0] - p0[0])
        lado_t = 1.0 if cr > 0 else -1.0
        _muro_con_huecos(mm, T['front'], [], T['z'] + 0.95, T['z'] - 4.5, 0.5, 'piedra_muro', lado_t, cerrada=False, segmentos=segs)
        _muro_con_huecos(mm, T['back'], [], T['z'] + 2.1, T['z'] - 1.2, 0.5, 'piedra_muro', -lado_t, cerrada=False,
                         segmentos=segs + segs_carr)
    # H2-5: carreteras de acceso en coche (losa de calzada + piazzola, 1ROAD_ en el kn5) con pretil de
    # piedra a los dos lados (en PENON_puente_muros: 1WALL_)
    if carrs:
        mcar = _Malla('PENON_carretera_lazo', ('piedra_calzada',))
        semi_l = ANCHO_CARR / 2.0 + PRETIL_CARR
        for c in carrs:
            pts = c['pts']
            nr = _normales_polilinea([(p[0], p[1]) for p in pts])
            filas = [((x + nx_ * semi_l, y + ny_ * semi_l, z + pl * semi_l), (x - nx_ * semi_l, y - ny_ * semi_l, z - pl * semi_l))
                     for (x, y, z, pl), (nx_, ny_) in zip(pts, nr)]
            _losa_filas(mcar, filas, 'piedra_calzada', 0.06, -0.6)
            if len(c['piazzola']) >= 2:
                _losa_filas(mcar, c['piazzola'], 'piedra_calzada', 0.03, -0.5)
            if c.get('piazzola_disco'):
                _losa_disco(mcar, c['piazzola_disco'][0], c['piazzola_disco'][1], c['piazzola_disco'][2], c['z_piazzola'], 'piedra_calzada')
            acum = [0.0]
            for k in range(1, len(pts)):
                acum.append(acum[-1] + math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]))
            s_a, s_b = c['s_pretil']
            idx = [k for k in range(len(pts)) if s_a <= acum[k] <= s_b]
            if len(idx) >= 2:
                for sg_l in (1.0, -1.0):
                    q = [(pts[k][0] + sg_l * nr[k][0] * semi_l, pts[k][1] + sg_l * nr[k][1] * semi_l) for k in idx]
                    zc = [pts[k][2] + sg_l * pts[k][3] * semi_l for k in idx]
                    _muro(mm, q, [z + 0.06 + 0.85 for z in zc], [z - 0.5 for z in zc], PRETIL_CARR, 'piedra_muro', lado=-sg_l)
        objs_carr = mcar
    else:
        objs_carr = None
    pz = D['plaza']
    th_s = pz['th_escalera']
    hueco = pol.xy(pz['r_rim_escalera'], th_s)
    _muro_con_huecos(mm, pz['poligono'], [(hueco[0], hueco[1], 2.6)], pz['z'] + 1.0, pz['z'] - 6.0, 0.45, 'piedra_muro', 1.0)
    # escaleras: en los codos cada tramo se acorta 1.3 m y se pone la losa octogonal
    me = _Malla('PENON_puente_escaleras', ('piedra_escalera', 'piedra_plaza'))
    extremos = []
    for t in D['tramos']:
        extremos += [t['p0'], t['p1']]

    def es_codo(p):
        return sum(1 for q in extremos if math.hypot(p[0] - q[0], p[1] - q[1]) < 0.3) >= 2

    def key(p):
        return (round(p[0], 1), round(p[1], 1))

    codos = {}
    for t in D['tramos']:
        ux, uy = _unit(t['p1'][0] - t['p0'][0], t['p1'][1] - t['p0'][1])
        for (p, z, d) in ((t['p0'], t['z0'], (ux, uy)), (t['p1'], t['z1'], (-ux, -uy))):
            if es_codo(p):
                codos.setdefault(key(p), {'p': p, 'z': z, 'dirs': []})['dirs'].append(d)
    for c in codos.values():
        c['a'], c['r'] = _codo_params(c['dirs'])
    n_pel = 0
    for t in D['tramos']:
        p0, p1 = t['p0'], t['p1']
        ux, uy = _unit(p1[0] - p0[0], p1[1] - p0[1])
        c0, c1 = codos.get(key(p0)), codos.get(key(p1))
        a0 = c0['a'] if c0 else 0.0
        a1 = c1['a'] if c1 else 0.0
        q0 = (p0[0] + ux * a0, p0[1] + uy * a0)
        q1 = (p1[0] - ux * a1, p1[1] - uy * a1)
        n_pel += _escalera(me, q0, q1, t['z0'], t['z1'], t['ancho'])
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1.0
        lx, ly = -uy * (t['ancho'] / 2.0 + 0.22), ux * (t['ancho'] / 2.0 + 0.22)
        for s_ in (1.0, -1.0):
            b0 = _recorte_murete((ux, uy), s_, [d for d in c0['dirs'] if d != (ux, uy)], c0['a'], c0['r']) if c0 else 0.0
            b1 = _recorte_murete((-ux, -uy), -s_, [d for d in c1['dirs'] if d != (-ux, -uy)], c1['a'], c1['r']) if c1 else 0.0
            if b0 + b1 > L - 1.0:
                continue
            w0 = (p0[0] + ux * b0, p0[1] + uy * b0)
            w1 = (p1[0] - ux * b1, p1[1] - uy * b1)
            zw0 = t['z0'] + (t['z1'] - t['z0']) * b0 / L
            zw1 = t['z1'] - (t['z1'] - t['z0']) * b1 / L
            pts = [(w0[0] + s_ * lx, w0[1] + s_ * ly), (w1[0] + s_ * lx, w1[1] + s_ * ly)]
            _muro(mm, pts, [zw0 + 0.9, zw1 + 0.9], [zw0 - 1.6, zw1 - 1.6], 0.3, 'piedra_muro', lado=s_)
    for c in codos.values():
        _rellano_codo(me, mm, c['p'], c['z'], c['dirs'], r=c['r'])
    mv = _Malla('PENON_puente_vallas', ('hierro',))
    objs = {}
    for r in D['rellanos']:
        if r.get('tipo') == 'carretera':
            # boca de carretera: valla de cierre de lado a lado (la del plan urbano, caminos_kit: barreras
            # rojiblancas, conos hacia la pista y senal de prohibido con placa CERRADO); sin hoja abierta
            r['hoja'] = None
            if r.get('valla') is None:
                continue
            (ax, ay), (bx, by) = r['valla']
            ck = caminos_kit
            if ck is not None and hasattr(ck, 'build_valla_cierre'):
                v = ck.build_valla_cierre(parent_collection, ancho=math.hypot(bx - ax, by - ay), seed=seed + 3)
                v.location = ((ax + bx) / 2.0, (ay + by) / 2.0, r['z_valla'])
                # X local a lo largo de la valla (de b hacia a: +Y local = hacia la carretera que se cierra)
                v.rotation_euler = (0.0, math.atan(r.get('pl_valla', 0.0)), math.atan2(ay - by, ax - bx))
                v.parent = raiz
                v.name = 'CAMINO_valla_lazo_' + r['nombre']
                D.setdefault('vallas_cierre', []).append(v)
                for k_h, h in enumerate(o_ for o_ in v.children_recursive if o_.type == 'MESH'):
                    objs['valla_cierre_%s_%d' % (r['nombre'], k_h)] = h
            else:
                _valla(mv, r['valla'][0], r['valla'][1], r['z_valla'], alto=1.1, puerta=False)
            continue
        r['hoja'] = _valla(mv, r['valla'][0], r['valla'][1], r['z'], alto=1.1, puerta=True, hacia=r['inward'])
        # muretes laterales del rellano (piedra) hacia la roca
        tx, ty = r['tx']
        ix, iy = r['inward']
        for s_ in (1.0, -1.0):
            a = (r['x'] - ix * 1.0 + s_ * tx * 2.3, r['y'] - iy * 1.0 + s_ * ty * 2.3)
            b = (r['x'] + ix * 1.7 + s_ * tx * 2.3, r['y'] + iy * 1.7 + s_ * ty * 2.3)
            _muro(mm, [a, b], r['z'] + 0.8, r['z'] - 1.5, 0.3, 'piedra_muro', lado=-s_)
    # plaza empedrada (abanico desde el centro) y campanile mirando al lazo
    mp = _Malla('PENON_puente_plaza', ('piedra_plaza', 'piedra_plaza_b'))
    poly = pz['poligono']
    c = mp.vert((pz['centro'][0], pz['centro'][1], pz['z'] + 0.05))
    anillo = [mp.vert((p[0], p[1], pz['z'] + 0.05)) for p in poly]
    for k in range(len(poly)):
        mp.cara((c, anillo[k], anillo[(k + 1) % len(poly)]), 'piedra_plaza' if (k // 2) % 2 == 0 else 'piedra_plaza_b')
    # v3 (remate): losa de umbral de cada puerta peatonal (del hueco del pretil al rellano), cara superior a
    # z_rellano + 0.02 (8 cm bajo la pista, como la que ponia el integrador) y canto hasta - 0.6. Filas en el sentido
    # hacia la roca con el lado izquierdo primero: caras hacia fuera sin recalc (la plaza se crea con recalc=False).
    for r in D['rellanos']:
        if r.get('tipo') == 'carretera' or not r.get('losa'):
            continue
        ix, iy = r['inward']
        fa, fb, bb, ba = r['losa']
        if (fb[0] - fa[0]) * (-iy) + (fb[1] - fa[1]) * ix > 0.0:
            fa, fb, bb, ba = fb, fa, ba, bb
        _losa_filas(mp, [((fa[0], fa[1], r['z']), (fb[0], fb[1], r['z'])), ((ba[0], ba[1], r['z']), (bb[0], bb[1], r['z']))],
                    'piedra_plaza', 0.02, -0.6)
    C = prep['C']
    th_cmp = math.atan2(C[1] - pz['centro'][1], C[0] - pz['centro'][0])
    r_c = _rim_desde(poly, pz['centro'], th_cmp) - 4.9
    camp = (pz['centro'][0] + r_c * math.cos(th_cmp), pz['centro'][1] + r_c * math.sin(th_cmp))
    mc = _Malla('PENON_puente_campanile', ('campanile_estuco', 'campanile_teja', 'campanile_piedra', 'hierro', 'bronce'))
    _campanile(mc, camp[0], camp[1], pz['z'], th_cmp + math.pi, lado=4.4, alto=22.0)
    D['plaza']['campanile'] = {'x': camp[0], 'y': camp[1], 'z': pz['z'], 'th': th_cmp}
    # cala: muelle de piedra, noray, pantalan de madera y barcas
    cala = D.get('cala')
    if cala:
        mq = _Malla('PENON_puente_muelle', ('piedra_muelle', 'madera', 'hierro'))
        _muro(mq, cala['front'], cala['z'] + 0.35, z_mar - 3.0, 0.6, 'piedra_muelle', lado=sg)
        _muro_con_huecos(mq, cala['back'], [], cala['z'] + 1.8, cala['z'] - 1.0, 0.5, 'piedra_muelle', -sg, cerrada=False, segmentos=segs)
        cala['norays'] = []
        for k in range(0, len(cala['front']), 2):
            p = cala['front'][k]
            th = math.atan2(p[1] - pol.S0[1], p[0] - pol.S0[0])
            mq.caja((p[0] - math.cos(th) * 0.8, p[1] - math.sin(th) * 0.8, cala['z']), (0.32, 0.32, 0.6), 'hierro', th)
            cala['norays'].append((p[0] - math.cos(th) * 0.8, p[1] - math.sin(th) * 0.8))
        i_c = len(cala['fs']) // 2
        p0 = pol.xy(cala['rf'][i_c] - 0.2, cala['th'])
        ux, uy = math.cos(cala['th']), math.sin(cala['th'])
        _pantalan(mq, p0, ux, uy, 14.0, z_mar)
        cala['pantalan_ini'] = p0
        cala['pantalan_fin'] = (p0[0] + ux * 14.0, p0[1] + uy * 14.0)
        objs['muelle'] = mq.objeto(parent_collection, raiz, recalc=True)
        tris['muelle'] = mq.n_tris()
        mb = _Malla('PENON_puente_barcas', ('barca_azul', 'barca_roja', 'barca_blanca', 'barca_verde', 'madera'))
        rnd = random.Random(seed + 77)
        colores = ('barca_azul', 'barca_roja', 'barca_blanca', 'barca_verde')
        for k, df in enumerate((-0.075, -0.04, 0.045, 0.08)):
            th = pol.th(cala['f'] + df)
            i_k = min(range(len(cala['fs'])), key=lambda q: abs(cala['fs'][q] - (cala['f'] + df)))
            p = pol.xy(cala['R'][i_k] + 6.8, th)
            _barca(mb, p[0], p[1], z_mar, th + math.pi / 2.0 + rnd.uniform(-0.25, 0.25), colores[k % 4])
        p = pol.xy(cala['R'][i_c] + 19.0, pol.th(cala['f'] - 0.02))
        _barca(mb, p[0], p[1], z_mar, rnd.uniform(0, 6.28), colores[1])
        objs['barcas'] = mb.objeto(parent_collection, raiz, recalc=True, suave=True)
        tris['barcas'] = mb.n_tris()
    objs['muros'] = mm.objeto(parent_collection, raiz, recalc=True)
    objs['escaleras'] = me.objeto(parent_collection, raiz, recalc=True)
    objs['vallas'] = mv.objeto(parent_collection, raiz, recalc=True)
    objs['plaza'] = mp.objeto(parent_collection, raiz, recalc=False)
    objs['campanile'] = mc.objeto(parent_collection, raiz, recalc=True)
    for k, m_ in (('muros', mm), ('escaleras', me), ('vallas', mv), ('plaza', mp), ('campanile', mc)):
        tris[k] = m_.n_tris()
    if objs_carr is not None:
        objs['carretera'] = objs_carr.objeto(parent_collection, raiz, recalc=True)
        tris['carretera'] = objs_carr.n_tris()
    log('obra: %d peldanos en %d tramos (%d codos con losa), %d rellanos (%d con valla y puerta, %d boca de carretera con valla '
        'cerrada), %d carreteras, campanile en (%.0f, %.0f)'
        % (n_pel, len(D['tramos']), len(codos), len(D['rellanos']), sum(1 for r in D['rellanos'] if r.get('tipo') != 'carretera'),
           sum(1 for r in D['rellanos'] if r.get('tipo') == 'carretera'), len(carrs), camp[0], camp[1]))
    return objs, tris


def _poblar(parent_collection, raiz, D, T1, T2, pol, prep, G, Cf, roca, z_mar, casas_kit, vegetacion_kit,
            italiano_kit, yates_kit, seed, log):
    """Casas (kit v2) en terrazas, plaza y cala SIN solapes: huellas reales
    (aleros 0.42 m, balcones 1.0 m), >= 1.5 m entre casas (rectangulos
    girados, eje separador), lejos de muros y escaleras, trasera comprobada
    contra la roca a 1.5 m. Pinos, palmeras, cipreses, fuente y lancha se
    asientan por ray-cast sobre la roca y se descartan si su copa entra en
    una casa. Matas colgadas de los paredones."""
    bpy.context.view_layer.update()
    rnd = random.Random(seed + 5)
    H0 = Cf['H0']
    pz = D['plaza']
    Pz, z_pl, poly = pz['centro'], pz['z'], pz['poligono']
    abajo = Vector((0.0, 0.0, -1.0))

    def z_roca(x, y, z_ref):
        hit, loc, _n, _f = roca.ray_cast(Vector((x, y, z_ref + 120.0)), abajo, distance=400.0)
        return float(loc.z) if hit else None

    # toda escalera/rampa bloquea casas a su alrededor (puntos cada 3 m)
    bloqueo = []
    for t in D['tramos']:
        dx, dy = t['p1'][0] - t['p0'][0], t['p1'][1] - t['p0'][1]
        L = math.hypot(dx, dy) or 1.0
        for k in range(int(L / 3.0) + 2):
            u = min(1.0, 3.0 * k / L)
            bloqueo.append((t['p0'][0] + dx * u, t['p0'][1] + dy * u, 2.0))
    for r in D['rellanos']:
        bloqueo.append((r['x'], r['y'], 4.0))
    # H2-5: la carretera (cada 3 m) y su piazzola tampoco admiten casas ni arboles
    for c in D.get('carreteras') or []:
        for k in range(0, len(c['pts']), 3):
            bloqueo.append((c['pts'][k][0], c['pts'][k][1], c['semi'] + 1.0))
        if c.get('piazzola_disco'):
            bloqueo.append((c['piazzola_disco'][0], c['piazzola_disco'][1], c['piazzola_disco'][2] + 0.5))
        for (l_, r_) in c['piazzola']:
            bloqueo.append(((l_[0] + r_[0]) / 2.0, (l_[1] + r_[1]) / 2.0, 0.5 * math.hypot(r_[0] - l_[0], r_[1] - l_[1]) + 1.0))
    casas = []
    cuenta = {}
    # --- terrazas: fachada hacia fuera (mar), trasera a >= 1.5 m del paredon.
    #     La orientacion sale de la CUERDA del frente bajo la fachada (no del gradiente,
    #     que en los codos del contorno apunta fuera de la repisa); donde el frente se
    #     curva mas de 1 m dentro del ancho de la casa no se construye.
    for T in (T2, T1):
        n0 = len(casas)
        front, anchos = T['front'], T['anchos']
        acum = [0.0]
        for i in range(1, len(front)):
            acum.append(acum[-1] + math.hypot(front[i][0] - front[i - 1][0], front[i][1] - front[i - 1][1]))
        nrm = T['nrm']                      # perpendicular al frente, hacia la cumbre
        T['nrm_suave'] = nrm
        S0x, S0y = pol.S0

        def punto(s_):
            i = max(0, min(len(front) - 2, int(np.searchsorted(np.array(acum), s_)) - 1))
            t = (s_ - acum[i]) / max(1e-6, acum[i + 1] - acum[i])
            return (front[i][0] + (front[i + 1][0] - front[i][0]) * t, front[i][1] + (front[i + 1][1] - front[i][1]) * t, i, t)

        ocup = list(T['ocupados']) + bloqueo
        # perfil de la repisa: H0 - z a 2..14 m del frente (por la normal suavizada), cada 6 m de frente
        filas = []
        for d in (2.0, 5.0, 8.0, 11.0, 14.0):
            vals = []
            for s_ in np.arange(3.0, acum[-1] - 3.0, 6.0):
                i = max(0, min(len(front) - 2, int(np.searchsorted(np.array(acum), s_)) - 1))
                x = front[i][0] + nrm[i][0] * d
                y = front[i][1] + nrm[i][1] * d
                dz_ = float(G.muestrear(H0, x, y)) - T['z']
                quien = ''
                if dz_ < -1.0 or dz_ > 0.5:
                    en = [q.nombre for q in D['rasgos'] if not isinstance(q, _RasgoNivel) and _dentro_poligono(q.poly, x, y)]
                    quien = '[%s]' % ','.join(en) if en else ''
                vals.append('%+.1f%s' % (dz_, quien))
            filas.append('d=%2.0f: %s' % (d, ' '.join(vals)))
        log('%s: perfil H0 - z por el frente (cada 6 m; entre corchetes, escalera/rellano que lo ocupa)\n    %s'
            % (T['nombre'], '\n    '.join(filas)))
        s_pos = 4.0
        diag = []
        while s_pos < acum[-1] - 4.0:
            ancho = rnd.choice((9.0, 10.0, 11.0))
            sc = s_pos + ancho / 2.0 + ALERO
            ax, ay, i, t = punto(sc - ancho / 2.0)
            bx, by, _i2, _t2 = punto(sc + ancho / 2.0)
            ux, uy = _unit(bx - ax, by - ay)
            px, py = (ax + bx) / 2.0, (ay + by) / 2.0
            nx_, ny_ = -uy, ux
            if nx_ * (S0x - px) + ny_ * (S0y - py) < 0.0:
                nx_, ny_ = -nx_, -ny_
            # curvatura del frente bajo la fachada: desviacion de la cuerda
            desv = max(abs((q[0] - ax) * nx_ + (q[1] - ay) * ny_) for q in front[i:min(len(front), _i2 + 2)])
            an_loc = anchos[i] * (1 - t) + anchos[i + 1] * t
            fondos = [f for f in (9.0, 8.0, 7.0, 6.0, 5.0) if f <= an_loc - 5.6]
            if not fondos or desv > 1.0 or float(G.muestrear(Cf['M'], px + nx_ * 8.0, py + ny_ * 8.0)) < float(G.muestrear(Cf['M'], px, py)):
                cuenta['sitio'] = cuenta.get('sitio', 0) + 1
                diag.append('%.0f:%s(%.0f)' % (s_pos, 'curva' if desv > 1.0 else 'sitio', an_loc if desv <= 1.0 else desv))
                s_pos += 1.5
                continue
            c = {'x': px + nx_ * 3.2, 'y': py + ny_ * 3.2, 'z': T['z'], 'rot': math.atan2(-ny_, -nx_) - math.pi / 2.0,
                 'ancho': ancho, 'fondo': fondos[0], 'plantas': rnd.choice((3, 3, 4, 4, 5)), 'grupo': T['nombre']}
            c2 = _colocar_casa(c, casas, ocup, T['poly'], (0.9, 1.0), G, H0, avance_max=1.2, fondos=fondos, cuenta=cuenta)
            if c2 is None:
                diag.append('%.0f:%s' % (s_pos, _motivo_casa(c, casas, ocup, T['poly'], (0.9, 1.0), G, H0)))
                s_pos += 1.0
                continue
            casas.append(c2)
            diag.append('%.0f:CASA(%.0fx%.0f)' % (s_pos, c2['ancho'], c2['fondo']))
            s_pos += ancho + 2.0 * ALERO + SEP_CASAS + 0.3
        log('%s: %d casas en %.0f m de frente; candidatas (s:resultado): %s' % (T['nombre'], len(casas) - n0, acum[-1], ' '.join(diag)))
    # --- plaza: anillo de casas mirando al centro (fuente); libres el campanile y la
    #     escalera; trasera (esquinas reales) a >= 2.5 m del parapeto
    cmp_ = pz['campanile']
    hue = pol.xy(pz['r_rim_escalera'], pz['th_escalera'])
    a_esc = math.atan2(hue[1] - Pz[1], hue[0] - Pz[0])
    circ_pl = bloqueo + [(Pz[0], Pz[1], 4.0), (cmp_['x'], cmp_['y'], 6.0), (hue[0], hue[1], 3.0)]
    n0 = len(casas)
    a = a_esc + 0.5
    while a < a_esc + 2 * math.pi - 0.4 and len(casas) - n0 < 6:
        ancho, fondo = rnd.choice((8.0, 8.0, 9.0)), 6.0
        rim = min(_rim_desde(poly, Pz, a + da_) for da_ in (-0.35, 0.0, 0.35))
        r_p = rim - 2.5 - fondo - ALERO
        puesta = None
        while r_p >= 6.0 and puesta is None:
            x, y = Pz[0] + r_p * math.cos(a), Pz[1] + r_p * math.sin(a)
            c = {'x': x, 'y': y, 'z': z_pl + 0.06, 'rot': math.atan2(-math.sin(a), -math.cos(a)) - math.pi / 2.0,
                 'ancho': ancho, 'fondo': fondo, 'plantas': rnd.choice((3, 4, 4)), 'grupo': 'plaza'}
            puesta = _colocar_casa(c, casas, circ_pl, poly, (1.0, 2.5), G, H0, avance_max=0.0, cuenta=cuenta)
            r_p -= 0.5
        if puesta is None:
            a += 0.06
            continue
        casas.append(puesta)
        a += (ancho + 2.0 * ALERO + SEP_CASAS + 0.4) / max(7.0, r_p + 0.5)
    log('plaza: %d casas en el anillo' % (len(casas) - n0))
    cala = D.get('cala')
    if cala:
        n0 = len(casas)
        diag_c = []
        circ_c = bloqueo + list(cala['ocupados'])
        for df in (-0.10, -0.055, -0.01, 0.035, 0.08):
            f = cala['f'] + df
            th = pol.th(f)
            # orilla R y fondo rb INTERPOLADOS en f (antes, los de la muestra mas cercana: hasta 2 m de error
            # radial: con el R interpolado caben 4 casas en vez de 3)
            R_f, rb_f = float(np.interp(f, cala['fs'], cala['R'])), float(np.interp(f, cala['fs'], cala['rb']))
            if R_f - 4.0 - 6.0 - 1.2 < rb_f:
                continue
            x, y = pol.xy(R_f - 4.0, th)
            c = {'x': x, 'y': y, 'z': cala['z'], 'rot': math.atan2(math.sin(th), math.cos(th)) - math.pi / 2.0,
                 'ancho': 7.5, 'fondo': 6.0, 'plantas': 2, 'grupo': 'cala'}
            c2 = _colocar_casa(c, casas, circ_c, cala['poly'], (0.5, 1.0), G, H0, avance_max=1.2, fondos=(6.0, 5.0), cuenta=cuenta)
            if c2 is not None:
                casas.append(c2)
                diag_c.append('%.3f:CASA' % f)
            else:
                mot = _motivo_casa(c, casas, circ_c, cala['poly'], (0.5, 1.0), G, H0)
                if mot == 'bloqueo':
                    Rr = _rect_casa(c['x'], c['y'], c['rot'], c['ancho'], c['fondo'])
                    q = next(((round(cx, 1), round(cy, 1), round(r, 1)) for (cx, cy, r) in circ_c if _circulo_toca(Rr, cx, cy, r)), None)
                    mot = 'bloqueo%s' % (q,)
                diag_c.append('%.3f:%s' % (f, mot))
        log('cala: %d casas de pescadores (f:resultado %s)' % (len(casas) - n0, ' '.join(diag_c)))
    log('casas: %d colocadas; intentos rechazados por motivo: %s'
        % (len(casas), ', '.join('%s %d' % kv for kv in sorted(cuenta.items()))))
    objs = []
    for k, c in enumerate(casas):
        if casas_kit is None:
            break
        ob = casas_kit.build_casa(parent_collection, plantas=c['plantas'], ancho=c['ancho'], fondo=c['fondo'],
                                  seed=seed * 100 + k, lod=0, name='CASAS_lazo_%02d' % k)
        ob.location = (c['x'], c['y'], c['z'])
        ob.rotation_euler = (0.0, 0.0, c['rot'])
        ob.parent = raiz
        c['obj'] = ob
        c['nombre'] = ob.name
        objs.append(ob)
    # --- vegetacion: cada planta se asienta por ray-cast sobre la roca (tronco a <= 0.3 m de
    #     la cota prevista en lo llano) y se descarta si su copa entra en una casa / campanile
    veg = []
    rects = [_rect_casa(c['x'], c['y'], c['rot'], c['ancho'], c['fondo']) for c in casas]
    rects.append(_cuadrado(cmp_['x'], cmp_['y'], 2.5, cmp_['th']))

    def libre_copa(x, y, r):
        return not any(_circulo_toca(R, x, y, r) for R in rects)

    def planta(fn, x, y, z, copa, **kw):
        if not libre_copa(x, y, copa):
            cuenta['arbol_casa'] = cuenta.get('arbol_casa', 0) + 1
            return None
        try:
            ob = fn(parent_collection, **kw)
        except Exception as e:  # pragma: no cover
            log('vegetacion: %s' % e)
            return None
        ob.location = (x, y, z)
        ob.rotation_euler = (0.0, 0.0, rnd.uniform(0, 6.28))
        ob.parent = raiz
        veg.append(ob)
        return ob

    S0 = pol.S0
    a_k = math.atan2(S0[1] - Pz[1], S0[0] - Pz[0])      # hacia el cerrete
    if vegetacion_kit is not None:
        for k in range(5):
            aa = a_k + (k - 2) * 0.55
            r = 24.0 + 4.0 * (k % 2) + rnd.uniform(0, 3)
            x, y = Pz[0] + r * math.cos(aa), Pz[1] + r * math.sin(aa)
            if _dentro_poligono(poly, x, y):
                continue
            z = z_roca(x, y, z_pl)
            if z is None:
                continue
            planta(vegetacion_kit.build_pino, x, y, z + 0.02, 3.5, alto=rnd.uniform(9.0, 13.0), seed=seed + k)
        for T in (T2, T1):
            nrm = T.get('nrm_suave', T['nrm'])
            for i in (2, len(T['front']) - 3):
                if i < 0 or i >= len(T['front']):
                    continue
                for d in (5.5, 4.0, 7.0):
                    x = T['front'][i][0] + nrm[i][0] * d
                    y = T['front'][i][1] + nrm[i][1] * d
                    z = z_roca(x, y, T['z'])
                    if (z is not None and abs(z - T['z']) <= 0.3 and _dentro_poligono(T['poly'], x, y)
                            and not any(math.hypot(x - ox, y - oy) < orad + 3.0 for (ox, oy, orad) in T['ocupados'] + bloqueo)):
                        if planta(vegetacion_kit.build_pino, x, y, z + 0.02, 3.5, alto=rnd.uniform(7.0, 10.0), seed=seed + 11 + i) is not None:
                            break
        if cala:
            # palmeras en el muelle, delante de las casas (entre balcones y borde del muelle)
            pant = cala.get('pantalan_ini')
            for df in (-0.078, -0.033, 0.012, 0.057):
                i = min(range(len(cala['fs'])), key=lambda k: abs(cala['fs'][k] - (cala['f'] + df)))
                x, y = pol.xy(cala['R'][i] + 0.5, pol.th(cala['f'] + df))
                z = z_roca(x, y, cala['z'])
                if z is None or abs(z - cala['z']) > 0.3 or any(math.hypot(x - ox, y - oy) < orad + 2.0 for (ox, oy, orad) in cala['ocupados']):
                    continue
                if pant is not None and _dist_polilinea([pant, cala['pantalan_fin']], x, y) < 3.0:
                    continue
                planta(vegetacion_kit.build_palmera, x, y, z + 0.02, 2.5, alto=rnd.uniform(6.5, 9.0), seed=seed + 21 + i)
    if italiano_kit is not None:
        for s_ in (1.0, -1.0):
            x = cmp_['x'] + math.cos(cmp_['th'] + math.pi / 2.0) * 4.6 * s_
            y = cmp_['y'] + math.sin(cmp_['th'] + math.pi / 2.0) * 4.6 * s_
            if _dentro_poligono(poly, x, y):
                planta(italiano_kit.build_cipres, x, y, z_pl, 1.5, alto=rnd.uniform(8.0, 10.0), seed=seed + 3)
        try:
            fu = italiano_kit.build_fuente(parent_collection, seed=seed)
            fu.location = (Pz[0], Pz[1], z_pl + 0.05)
            fu.parent = raiz
            veg.append(fu)
        except Exception as e:  # pragma: no cover
            log('fuente: %s' % e)
    if yates_kit is not None and cala:
        try:
            fin = cala['pantalan_fin']
            ux, uy = math.cos(cala['th']), math.sin(cala['th'])
            la = yates_kit.build_lancha(parent_collection, eslora=9.0, seed=seed)
            la.location = (fin[0] + ux * 4.0 - uy * 4.0, fin[1] + uy * 4.0 + ux * 4.0, z_mar)
            la.rotation_euler = (0.0, 0.0, cala['th'] + math.pi / 2.0)
            la.parent = raiz
            veg.append(la)
        except Exception as e:  # pragma: no cover
            log('lancha: %s' % e)
    # --- matas en cornisas y laderas (no en lo llano ni junto al tablero). Cada mata se
    #     construye en el plano TANGENTE de la ladera (plano ajustado por rayos a la roca bajo
    #     su huella) con media mata enterrada, y se APOYA: rayo vertical a la roca bajo cada
    #     vertice de la mitad inferior; si alguno queda a > 0.25 m del suelo se hunde (hasta
    #     0.3 x alto), si no basta se prueba con r = 0.6 y si tampoco, se descarta.
    nz, o, H, llano, val = Cf['nz'], Cf['o'], Cf['H'], Cf['llano'], Cf['valido']
    masc = val & (~llano) & (o > 5.0) & (nz > 0.6) & (nz < 0.9) & (H > z_mar + 1.5)
    ruido = _vnoise2(G.X, G.Y, 4.0, seed + 51)
    masc &= ruido > 0.55
    idx = np.argwhere(masc)
    idx = [tuple(q) for q in idx]
    rnd.shuffle(idx)
    me_r = roca.data
    bvh_r = BVHTree.FromPolygons([tuple(roca.matrix_world @ v.co) for v in me_r.vertices], [tuple(p.vertices) for p in me_r.polygons])

    def suelo(x, y, z):
        loc, _n, _i, _d = bvh_r.ray_cast(Vector((x, y, z + 60.0)), abajo, 400.0)
        return None if loc is None else float(loc.z)

    # obra y casas: ninguna mata las corta (BVH overlap)
    bpy.context.view_layer.update()
    obra_m = [o for o in raiz.children if o.type == 'MESH' and o.name.startswith(_OBRA_MATAS)]
    for v in D.get('vallas_cierre') or []:
        obra_m += [h for h in v.children_recursive if h.type == 'MESH']
    for ob in objs:
        obra_m += [ob] + [h for h in ob.children_recursive if h.type == 'MESH']
    bvh_obra = _bvh_mundo(obra_m)
    matas, n_cand, n_peq, n_hund, n_obra = [], 0, 0, 0, 0
    for (j, i) in idx:
        if len(matas) >= 420:
            break
        n_cand += 1
        x0, y0 = float(Cf['Xd'][j, i]), float(Cf['Yd'][j, i])
        r0 = rnd.uniform(0.8, 1.9)
        fx, fy, fz, rz = rnd.uniform(0.8, 1.3), rnd.uniform(0.8, 1.3), rnd.uniform(0.7, 1.05), rnd.uniform(0.0, 6.28)
        puesta = None
        for r in (r0, 0.6):
            sx, sy, sz = r * fx, r * fy, r * fz
            rp = 0.85 * max(sx, sy)
            pts_p = [(x0, y0)] + [(x0 + rp * math.cos(a_), y0 + rp * math.sin(a_)) for a_ in np.linspace(0.0, 2 * math.pi, 7)[:-1]]
            zs = [suelo(px, py, float(H[j, i])) for (px, py) in pts_p]
            if any(zq is None for zq in zs):
                break
            A = np.array([[px, py, 1.0] for (px, py) in pts_p])
            (ga, gb, gc), *_r = np.linalg.lstsq(A, np.array(zs), rcond=None)
            ln = math.sqrt(ga * ga + gb * gb + 1.0)
            nrm = (-ga / ln, -gb / ln, 1.0 / ln)
            if nrm[2] < 0.55:
                break
            vs = _mata_verts(x0, y0, zs[0], nrm, sx, sy, sz, rz)
            zc = sum(p[2] for p in vs) / len(vs)
            huecos = []
            for p in vs:
                if p[3] <= 1e-6 or p[2] <= zc:
                    zg = suelo(p[0], p[1], p[2])
                    huecos.append(99.0 if zg is None else p[2] - zg)
            hueco = max(huecos)
            if hueco <= 0.25:
                puesta = vs
            elif hueco - 0.15 <= 0.3 * sz:
                puesta = [(p[0], p[1], p[2] - (hueco - 0.15), p[3]) for p in vs]
                n_hund += 1
            if puesta is not None and bvh_obra is not None:
                if BVHTree.FromPolygons([p[:3] for p in puesta], _ICO_F).overlap(bvh_obra):
                    puesta = None
                    n_obra += 1
            if puesta is not None:
                n_peq += 1 if r != r0 else 0
                break
        if puesta is not None:
            matas.append(puesta)
    mt = _Malla('PENON_puente_matas', ('mata', 'mata_clara'))
    _matas(mt, matas)
    ob_m = mt.objeto(parent_collection, raiz, recalc=False, suave=True) if mt.f else None
    log('matas: %d puestas de %d candidatas (%d reducidas a r 0.6, %d hundidas para apoyar, %d intentos que cortaban obra/casas)'
        % (len(matas), n_cand, n_peq, n_hund, n_obra))
    log('poblado: %d casas (%s), %d plantas/props (arboles descartados por copa en casa: %d), %d matas'
        % (len(objs), ', '.join('%s %d' % (g, sum(1 for c in casas if c['grupo'] == g)) for g in ('terraza_alta', 'terraza_baja', 'plaza', 'cala')),
           len(veg), cuenta.get('arbol_casa', 0), len(matas)))
    return casas, objs, veg, ob_m


def _geom_mundo(obs):
    """(BVH, vertices, poligonos) de varios objetos malla en coordenadas de
    mundo (BVH None si no hay caras)."""
    verts, polys = [], []
    for ob in obs:
        if ob is None or ob.type != 'MESH':
            continue
        mw = ob.matrix_world
        base = len(verts)
        verts += [tuple(mw @ v.co) for v in ob.data.vertices]
        polys += [tuple(base + i for i in p.vertices) for p in ob.data.polygons]
    if not polys:
        return None, verts, polys
    return BVHTree.FromPolygons(verts, polys, all_triangles=False), verts, polys


def _bvh_mundo(obs):
    return _geom_mundo(obs)[0]


def _agrupar_solapes(pares, verts, polys, celda=3.0):
    """agrupa los poligonos (indice en pares[k][0]) por celdas de `celda` m:
    [(n_pares, (x, y, z))] de mayor a menor."""
    celdas = {}
    for (ka, kb) in pares:
        ps = [verts[i] for i in polys[ka]]
        c = tuple(sum(p[j] for p in ps) / len(ps) for j in range(3))
        key = (int(c[0] // celda), int(c[1] // celda))
        if key not in celdas:
            celdas[key] = [0, c]
        celdas[key][0] += 1
    return sorted(((v[0], tuple(round(q, 1) for q in v[1])) for v in celdas.values()), reverse=True)


def _comprobar(roca, objs, prep, contexto, casas, veg, rellanos, log, matas=None, z_mar=0.0, carreteras=None):
    """Rayos verticales sobre el tablero (0 impactos), contacto con el borde
    interior (< 0.8 m en > 90 %), casas (esquinas reales sin roca dentro ni
    flotando, 1.5 m detras libre, >= 1.5 m entre casas, 0 solapes BVH con
    muros / escaleras / vallas / campanile / muelle y entre casas),
    escaleras sin cortar muros (BVH), arboles asentados en la roca, puertas
    abriendo hacia el rellano, matas apoyadas (0 con > 0.3 m de hueco bajo
    su mitad inferior), roca sin bordes abiertos sobre el agua y limites de
    material 'verticales' (|dz| > 0.7 x largo en cara con nz < 0.5) < 2 %."""
    bpy.context.view_layer.update()
    P, Z, Nn, W, B, inward, n = prep['P'], prep['Z'], prep['N'], prep['W'], prep['B'], prep['inward'], prep['n']
    abajo = Vector((0.0, 0.0, -1.0))

    def rayo_v(ob, x, y, z_fin):
        return ob.ray_cast(Vector((x, y, 400.0)), abajo, distance=400.0 - z_fin)

    otros = [o for o in objs.values() if o is not None]
    muestras = [(float(P[i][0]), float(P[i][1]), float(Z[i]), float(Nn[i][0]), float(Nn[i][1]), float(W[i])) for i in range(n)]
    antes, despues = (contexto or (None, None))
    extra = []
    for lst in (antes or [], despues or []):
        extra += [(float(m['x']), float(m['y']), float(m['z']), float(m['nx']), float(m['ny']), float(m['w'])) for m in lst]
    res = {'rayos_roca': 0, 'rayos_obra': 0, 'rayos_contexto': 0, 'rayos_total': 0}
    for (lista, clave) in ((muestras, 'rayos_roca'), (extra, 'rayos_contexto')):
        for i_m, (x, y, z, nx_, ny_, w) in enumerate(lista):
            for lt in (-(w / 2.0 + 1.0), 0.0, w / 2.0 + 1.0):
                px, py = x + nx_ * lt, y + ny_ * lt
                res['rayos_total'] += 1
                h_, loc_, n_, f_ = rayo_v(roca, px, py, z + 0.05)
                if h_:
                    res[clave] += 1
                    res.setdefault('rayos_detalle', []).append((clave, i_m, round(lt, 1), round(loc_.z - z, 2)))
                if clave == 'rayos_roca':
                    for ob in otros:
                        if rayo_v(ob, px, py, z + 0.05)[0]:
                            res['rayos_obra'] += 1
                            break
    toca = 0
    dists = []
    for i in range(n):
        orig = Vector((float(B[i][0]), float(B[i][1]), float(Z[i]) - 0.7))
        d = Vector((float(inward[i][0]), float(inward[i][1]), 0.0))
        hit, loc, nrm, fi = roca.ray_cast(orig, d, distance=3.0)
        dist = (loc - orig).length if hit else 3.0
        dists.append(dist)
        if dist < 0.8:
            toca += 1
    res['contacto_pct'] = 100.0 * toca / float(n)
    res['contacto_dist_media'] = float(sum(dists) / len(dists))
    res['contacto_fallos'] = [i for i in range(n) if dists[i] >= 0.8]
    log('contacto fallos (i:dist): %s' % ' '.join('%d:%.2f' % (i, dists[i]) for i in res['contacto_fallos'][:60]))
    log('rayos detalle (clave, i, lt, dz): %s' % str(res.get('rayos_detalle', [])[:40]))
    # --- casas: huella nominal + esquinas reales (roca dentro / flotando) y 1.5 m detras
    malas, flotan, traseras = 0, 0, 0
    for c in casas:
        pts = _huella(c['x'], c['y'], c['rot'], c['ancho'], c['fondo']) + _rect_casa(c['x'], c['y'], c['rot'], c['ancho'], c['fondo'])
        det = _detras_casa(c['x'], c['y'], c['rot'], c['ancho'], c['fondo'])
        zs, zd = [], []
        for (lista, out) in ((pts, zs), (det, zd)):
            for (px, py) in lista:
                hit, loc, nrm, fi = roca.ray_cast(Vector((px, py, c['z'] + 80.0)), abajo, distance=200.0)
                out.append(loc.z if hit else c['z'] - 50.0)
        c['dz_huella'] = (round(min(zs) - c['z'], 2), round(max(zs) - c['z'], 2))
        if max(zs) > c['z'] + 0.25:
            malas += 1
        if min(zs) < c['z'] - 0.6:
            flotan += 1
        if max(zd) > c['z'] + 0.3:
            traseras += 1
    res['casas_intersectando'] = malas
    res['casas_flotantes'] = flotan
    res['casas_trasera_en_roca'] = traseras
    res['casas'] = len(casas)
    # --- casa-casa en planta (huellas reales): cruces y pares a menos de 1.5 m
    cruces, cerca = 0, 0
    for a in range(len(casas)):
        ca = casas[a]
        Ra = _rect_casa(ca['x'], ca['y'], ca['rot'], ca['ancho'], ca['fondo'])
        Ra2 = _rect_casa(ca['x'], ca['y'], ca['rot'], ca['ancho'], ca['fondo'], SEP_CASAS / 2.0)
        for b in range(a + 1, len(casas)):
            cb = casas[b]
            if math.hypot(ca['x'] - cb['x'], ca['y'] - cb['y']) > 40.0:
                continue
            if not _convexos_separados(Ra, _rect_casa(cb['x'], cb['y'], cb['rot'], cb['ancho'], cb['fondo'])):
                cruces += 1
            elif not _convexos_separados(Ra2, _rect_casa(cb['x'], cb['y'], cb['rot'], cb['ancho'], cb['fondo'], SEP_CASAS / 2.0)):
                cerca += 1
    res['casas_cruzadas'] = cruces
    res['casas_a_menos_de_1_5m'] = cerca
    # --- solapes por BVH: casa x obra, casa x casa, escaleras x muros/muelle
    ob_casas = [c['obj'] for c in casas if c.get('obj') is not None]
    bvh_c = [(_bvh_mundo([ob]), ob.name) for ob in ob_casas]
    obra = [objs.get(k) for k in ('muros', 'escaleras', 'vallas', 'campanile', 'muelle', 'carretera')]
    bvh_obra = _bvh_mundo(obra)
    sol_obra, sol_cc, det_obra = 0, 0, []
    for k, (bv, nm) in enumerate(bvh_c):
        if bv is None:
            continue
        if bvh_obra is not None:
            pares = bv.overlap(bvh_obra)
            if pares:
                sol_obra += 1
                det_obra.append((nm, len(pares)))
        for (bv2, nm2) in bvh_c[k + 1:]:
            if bv2 is not None and bv.overlap(bv2):
                sol_cc += 1
    bvh_e, ve, pe = _geom_mundo([objs.get('escaleras')])
    bvh_m = _bvh_mundo([objs.get('muros'), objs.get('muelle')])
    esc_m, esc_m_donde = 0, []
    if bvh_e is not None and bvh_m is not None:
        pares = bvh_e.overlap(bvh_m)
        esc_m = len(pares)
        esc_m_donde = _agrupar_solapes(pares, ve, pe)[:8]
    res['solapes_escaleras_muros_donde'] = esc_m_donde
    res['solapes_casa_obra'] = sol_obra
    res['solapes_casa_casa_bvh'] = sol_cc
    res['solapes_escaleras_muros'] = esc_m
    # --- arboles / props en la roca (pivote): dz = roca - z en [-0.6, 0.5]
    veg_mal = []
    for ob in veg:
        nm = ob.name.split('.')[0]
        if nm.startswith(('YATE', 'COCHE')):
            continue
        x, y, z = ob.matrix_world.translation
        hit, loc, nrm, fi = roca.ray_cast(Vector((x, y, z + 150.0)), abajo, distance=400.0)
        dz = (loc.z - z) if hit else None
        if dz is None or dz > 0.5 or dz < -0.6:
            veg_mal.append((ob.name, round(x, 1), round(y, 1), None if dz is None else round(dz, 2)))
    res['vegetacion_mal_asentada'] = len(veg_mal)
    # --- puertas: la hoja abierta debe alejarse del borde del tablero (o crece hacia la roca)

    def o_borde(x, y):
        j = min(range(n), key=lambda i: (B[i][0] - x) ** 2 + (B[i][1] - y) ** 2)
        return (x - B[j][0]) * inward[j][0] + (y - B[j][1]) * inward[j][1]

    puertas_mal = 0
    for r in rellanos:
        h = r.get('hoja')
        if h is None:
            continue
        o_b, o_e = o_borde(*h[0]), o_borde(*h[1])
        r['o_hoja'] = (round(o_b, 2), round(o_e, 2))
        if o_e < o_b + 0.5:
            puertas_mal += 1
    res['puertas_hacia_pista'] = puertas_mal
    # --- matas: rayo vertical a la roca bajo cada vertice de su mitad inferior (z <= centro)
    flotan_m, hueco_max, peores_m = 0, 0.0, []
    if matas is not None and matas.type == 'MESH':
        mwm = matas.matrix_world
        vm = [mwm @ v.co for v in matas.data.vertices]
        for k0 in range(0, len(vm) - VERTS_MATA + 1, VERTS_MATA):
            grupo = vm[k0:k0 + VERTS_MATA]
            zc = sum(p.z for p in grupo) / len(grupo)
            h_m = 0.0
            for p in grupo:
                if p.z > zc:
                    continue
                hit, loc, _n, _f = roca.ray_cast(Vector((p.x, p.y, p.z + 60.0)), abajo, distance=400.0)
                h_m = max(h_m, (p.z - loc.z) if hit else 99.0)
            hueco_max = max(hueco_max, h_m)
            if h_m > 0.3:
                flotan_m += 1
                peores_m.append((round(grupo[0].x, 1), round(grupo[0].y, 1), round(h_m, 2)))
    res['matas_flotando'] = flotan_m
    res['matas_hueco_max'] = round(hueco_max, 3)
    # --- matas x obra / casas (BVH overlap): 0 pares
    matas_obra = 0
    if matas is not None and matas.type == 'MESH':
        obs_o = [objs.get(k) for k in ('muros', 'escaleras', 'vallas', 'plaza', 'campanile', 'muelle')]
        for c in casas:
            if c.get('obj') is not None:
                obs_o += [c['obj']] + [h for h in c['obj'].children_recursive if h.type == 'MESH']
        bv_o, bv_m = _bvh_mundo(obs_o), _bvh_mundo([matas])
        if bv_o is not None and bv_m is not None:
            matas_obra = len(bv_m.overlap(bv_o))
    res['matas_cortan_obra'] = matas_obra
    # --- roca: bordes abiertos sobre el agua y limites de material 'verticales' (dientes)
    bm = bmesh.new()
    bm.from_mesh(roca.data)
    bm.normal_update()
    mwr = roca.matrix_world
    bordes_agua, n_lim, n_lim_v = 0, 0, 0
    for e in bm.edges:
        a, b = mwr @ e.verts[0].co, mwr @ e.verts[1].co
        if len(e.link_faces) < 2:
            if max(a.z, b.z) > z_mar:
                bordes_agua += 1
            continue
        fa, fb = e.link_faces[0], e.link_faces[1]
        if fa.material_index == fb.material_index:
            continue
        n_lim += 1
        if abs(a.z - b.z) > 0.7 * (a - b).length and (fa.normal.z + fb.normal.z) / 2.0 < 0.5:
            n_lim_v += 1
    bm.free()
    res['roca_bordes_sobre_agua'] = bordes_agua
    res['limites_material'] = n_lim
    res['limites_verticales_empinados'] = n_lim_v
    res['limites_verticales_pct'] = round(100.0 * n_lim_v / max(1, n_lim), 2)
    # --- H2-1 / N1: orientacion (en AC hay culling de caras traseras y se sombrea con la normal del
    #     vertice): la roca con volumen > 0 y < 1 % del techo boca abajo; el resto de mallas propias
    #     (obra, carreteras, matas) sin techo boca abajo (> 50 % con >= 10 caras de techo)
    ori = _orientacion(roca, z_mar + Z_FONDO_REL)
    res['roca_orientacion'] = ori
    res['roca_orientada_fuera'] = bool(ori is not None and ori['vol'] > 0.0 and ori['techo_abajo_pct'] < 1.0
                                       and 0.0 <= ori['normales_esquina_opuestas_pct'] < 1.0)
    boca_abajo = []
    for ob in otros + ([matas] if matas is not None else []):
        if ob.type != 'MESH' or not ob.name.startswith('PENON_'):
            continue
        o_ = _orientacion(ob, z_mar + Z_FONDO_REL)
        if o_ is not None and o_['techo_n'] >= 10 and o_['techo_abajo_pct'] > 50.0:
            boca_abajo.append((ob.name, o_['techo_abajo_pct']))
    res['mallas_boca_abajo'] = boca_abajo
    log('CHECK orientacion: roca %s -> %s; otras mallas boca abajo: %s'
        % (ori, 'OK (hacia fuera)' if res['roca_orientada_fuera'] else 'HACIA DENTRO', boca_abajo))
    # --- H2-5: carreteras: rasante (pendiente <= 10 %, radio >= 10 m) y NADA encima de la calzada ni de
    #     la piazzola (roca ni obra: rayos verticales en el eje y a +-(ancho/2 - 0.2) hasta 0.25 m sobre
    #     la losa; la valla de cierre, que cruza la calzada a proposito, no cuenta)
    obra_c = [o for o in (objs.get(k) for k in ('muros', 'escaleras', 'vallas', 'plaza', 'campanile', 'muelle')) if o is not None]
    obra_c += [c['obj'] for c in casas if c.get('obj') is not None]
    obra_c += [h for c in casas if c.get('obj') is not None for h in c['obj'].children_recursive if h.type == 'MESH']
    bvh_oc = _bvh_mundo([o for o in obra_c if o.type == 'MESH']) if carreteras else None   # mundo (casas giradas)
    carr_res, carr_ok = [], True
    for c in carreteras or []:
        pts = c['pts']
        nr = _normales_polilinea([(p[0], p[1]) for p in pts])
        acum = [0.0]
        for k in range(1, len(pts)):
            acum.append(acum[-1] + math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]))
        sondas = []
        for k, (x, y, z, pl) in enumerate(pts):
            if abs(acum[k] - c.get('s_valla', -99.0)) < 1.5:
                continue
            for lt in (-(c['ancho'] / 2.0 - 0.2), 0.0, c['ancho'] / 2.0 - 0.2):
                sondas.append((x + nr[k][0] * lt, y + nr[k][1] * lt, z + pl * lt + 0.31))
        for (l_, r_) in c['piazzola']:
            for t_ in (0.2, 0.5, 0.8):
                sondas.append((l_[0] + (r_[0] - l_[0]) * t_, l_[1] + (r_[1] - l_[1]) * t_, c['z_piazzola'] + 0.28))
        if c.get('piazzola_disco'):
            qx, qy, qr = c['piazzola_disco']
            sondas.append((qx, qy, c['z_piazzola'] + 0.28))
            for a_ in np.linspace(0.0, 2.0 * math.pi, 9)[:-1]:
                for f_r in (0.5, 0.85):
                    sondas.append((qx + qr * f_r * math.cos(a_), qy + qr * f_r * math.sin(a_), c['z_piazzola'] + 0.28))
        enc_r, enc_o, donde = 0, 0, []
        for (px, py, pz) in sondas:
            if rayo_v(roca, px, py, pz)[0]:
                enc_r += 1
                donde.append((round(px, 1), round(py, 1)))
            if bvh_oc is not None and bvh_oc.ray_cast(Vector((px, py, 400.0)), abajo, 400.0 - pz)[0] is not None:
                enc_o += 1
                donde.append((round(px, 1), round(py, 1)))
        cr_ = {'nombre': c['nombre'], 'largo': round(c['largo'], 1), 'pend_max_pct': round(100.0 * c['pend_max'], 2),
               'radio_min': round(c['radio_min'], 1), 'sondas': len(sondas), 'roca_encima': enc_r, 'obra_encima': enc_o,
               'donde': donde[:8], 'terraza': c['terraza'], 'filas_piazzola': len(c['piazzola']),
               'piazzola_disco': c.get('piazzola_disco')}
        carr_res.append(cr_)
        carr_ok = (carr_ok and enc_r == 0 and enc_o == 0 and c['pend_max'] <= 0.10 and c['radio_min'] >= 10.0
                   and len(c['piazzola']) >= c.get('piazzola_min', 0))
    res['carreteras'] = carr_res
    res['carreteras_ok'] = carr_ok
    log('CHECK carreteras (pendiente <= 10 %%, radio >= 10 m, 0 roca/obra encima, piazzola si la lleva): %s -> %s'
        % (carr_res, 'OK' if carr_ok else 'FALLO'))
    log('CHECK matas: %d flotando (> 0.3 m bajo algun vertice inferior; hueco max %.2f m) %s, %d pares cortando obra/casas; '
        'roca: %d bordes abiertos sobre el agua; limites de material %d, verticales en cara empinada %d (%.2f %%, debe ser < 2 %%)'
        % (flotan_m, hueco_max, peores_m[:6], matas_obra, bordes_agua, n_lim, n_lim_v, res['limites_verticales_pct']))
    log('CHECK rayos del tablero (%d rayos, hasta la cota del tablero): roca %d, obra %d, tramo de contexto %d (todo debe ser 0)'
        % (res['rayos_total'], res['rayos_roca'], res['rayos_obra'], res['rayos_contexto']))
    log('CHECK contacto: roca a < 0.8 m del borde interior en %.1f %% de las muestras (media %.2f m; fallos %d)'
        % (res['contacto_pct'], res['contacto_dist_media'], len(res['contacto_fallos'])))
    log('CHECK casas: %d colocadas, %d con roca dentro, %d flotantes, %d con roca a 1.5 m detras; en planta %d cruzadas, %d a < 1.5 m; '
        'BVH: %d cortan obra %s, %d pares casa-casa (todo debe ser 0)'
        % (len(casas), malas, flotan, traseras, cruces, cerca, sol_obra, det_obra[:6], sol_cc))
    log('CHECK escaleras x muros/muelle (pares BVH): %d %s; vegetacion mal asentada: %d %s; puertas hacia la pista: %d (todo 0)'
        % (esc_m, esc_m_donde, len(veg_mal), veg_mal[:8], puertas_mal))
    # --- v3 (remate, como _rev/nada_en_pista.py): ningun vertice de lo que cuelga de la raiz (obra, verjas, losas,
    #     vallas de cierre, casas, arboles, matas; la roca no cuenta) a < w/2 + RETRANQUEO_ASFALTO de la muestra de
    #     pista mas cercana (tramo + contexto) y entre z - 0.3 y z + 5.5
    from mathutils import kdtree as _kdt
    pista = muestras + extra
    kd_p = _kdt.KDTree(len(pista))
    for k, q in enumerate(pista):
        kd_p.insert((q[0], q[1], 0.0), k)
    kd_p.balance()
    w_max = max(q[5] for q in pista)
    raiz_ = roca.parent
    obs_j = [o for o in (raiz_.children_recursive if raiz_ is not None else otros) if o.type == 'MESH' and o != roca]
    junto, margen = {}, {}
    for ob in obs_j:
        mw = ob.matrix_world
        bb = [mw @ Vector(c_) for c_ in ob.bound_box]
        cxb = sum(v.x for v in bb) / 8.0
        cyb = sum(v.y for v in bb) / 8.0
        rb = max(math.hypot(v.x - cxb, v.y - cyb) for v in bb)
        if kd_p.find((cxb, cyb, 0.0))[2] > rb + w_max / 2.0 + RETRANQUEO_ASFALTO + 2.5:
            continue
        n_j, peor, m_min = 0, None, 99.0
        for v in ob.data.vertices:
            w_ = mw @ v.co
            _c, k, d = kd_p.find((w_.x, w_.y, 0.0))
            q = pista[k]
            if not (q[2] - 0.3 < w_.z < q[2] + 5.5):
                continue
            m_min = min(m_min, d - q[5] / 2.0)
            if d < q[5] / 2.0 + RETRANQUEO_ASFALTO:
                n_j += 1
                if peor is None or d - q[5] / 2.0 < peor[0]:
                    peor = (round(d - q[5] / 2.0, 3), round(w_.x, 1), round(w_.y, 1), round(w_.z - q[2], 2))
        if n_j:
            junto[ob.name] = (n_j, peor)
        if m_min < 1.5:
            margen[ob.name] = round(m_min, 3)
    res['cerca_asfalto'] = junto
    res['cerca_asfalto_n'] = sum(v[0] for v in junto.values())
    res['cerca_asfalto_margen'] = margen
    log('CHECK nada junto al asfalto (< w/2 + %.1f m, z-0.3..z+5.5, %d mallas): %d vertices %s (debe ser 0); '
        'margen minimo (m) de lo que queda a < 1.5 m: %s' % (RETRANQUEO_ASFALTO, len(obs_j), res['cerca_asfalto_n'], junto, margen))
    res['ok'] = (res['cerca_asfalto_n'] == 0
                 and res['rayos_roca'] == 0 and res['rayos_obra'] == 0 and res['contacto_pct'] > 90.0 and malas == 0 and flotan == 0
                 and traseras == 0 and cruces == 0 and cerca == 0 and sol_obra == 0 and sol_cc == 0 and esc_m == 0
                 and len(veg_mal) == 0 and puertas_mal == 0 and flotan_m == 0 and matas_obra == 0 and bordes_agua == 0
                 and res['limites_verticales_pct'] < 2.0 and res['roca_orientada_fuera'] and not boca_abajo
                 and carr_ok)
    return res


def build(parent_collection, muestras, z_mar, seed, casas_kit=None, vegetacion_kit=None, italiano_kit=None,
          yates_kit=None, **params):
    """Roca del lazo. Ver docstring del modulo."""
    log_fn = params.get('log', print)

    def log(msg):
        log_fn('[roca_lazo] ' + msg)

    z_mar = float(z_mar)
    contexto = params.get('muestras_contexto')
    prep = _preparar(muestras, contexto)
    mac, pol, u_open, z_c = _disenar_macizo(prep, params)
    cell = float(params.get('cell', 1.0))
    tan_bajo = math.tan(math.radians(float(params.get('talud_bajo_tablero_deg', 70.0))))
    xs = [d[0] - d[3] for d in mac.domos] + [d[0] + d[3] for d in mac.domos] + list(prep['Bx'][:, 0] - 45.0) + list(prep['Bx'][:, 0] + 45.0)
    ys = [d[1] - d[3] for d in mac.domos] + [d[1] + d[3] for d in mac.domos] + list(prep['Bx'][:, 1] - 45.0) + list(prep['Bx'][:, 1] + 45.0)
    G = _Rejilla(min(xs), min(ys), max(xs), max(ys), cell)
    log('lado interior %+d, %d muestras, centro (%.0f, %.0f), cumbre S0 (%.0f, %.0f) z=%.0f, sector abierto %.0f grados, rejilla %d x %d (cell %.2f)'
        % (int(prep['side']), prep['n'], prep['C'][0], prep['C'][1], pol.S0[0], pol.S0[1], z_c, math.degrees(abs(pol.span)), G.nx, G.ny, cell))
    cb = _campo_borde(G.X, G.Y, prep['Bx'], prep['Zb'], prep['Rb'], prep['side'])
    M = mac.eval(G.X, G.Y)
    lejos = np.clip((cb['o'] - 14.0) / 20.0, 0.0, 1.0) * np.clip(M / 30.0, 0.0, 1.0)
    M = M + (6.5 * _fbm2(G.X, G.Y, 55.0, seed + 3) + 2.4 * np.abs(_fbm2(G.X, G.Y, 22.0, seed + 5, 2)) - 1.2) * lejos
    M = M + 1.0 * _fbm2(G.X, G.Y, 9.0, seed + 7, 2) * np.clip(M / 20.0, 0.0, 1.0)
    # cala: cuenco suave que mete la orilla hacia dentro (bahia concava)
    V = pol.xy(float(params.get('r_cala', 150.0)), pol.th(0.53))
    dV = np.sqrt((G.X - V[0]) ** 2 + (G.Y - V[1]) ** 2)
    M = M - 9.0 * np.clip(1.0 - (dV / 60.0) ** 2, 0.0, 1.0) ** 1.5
    # pie del macizo bajo el fondo del mar: donde no hay domo la roca no existe (nada a z=0)
    M = M - (abs(Z_FONDO_REL) + 2.0) * (1.0 - np.clip(M / 6.0, 0.0, 1.0)) ** 2
    D, T1, T2, z_pl = _disenar_rasgos(prep, G, M, pol, u_open, z_c, z_mar, params, seed, cb, log)
    _disenar_accesos(prep, D, pol, T1, T2, G, M, log)
    _disenar_cala(prep, D, pol, T1, G, M, z_mar, log)
    if params.get('carretera_cala', True):
        _disenar_carretera_cala(prep, D, pol, G, M, cb, log)
    Cf = _campo_alturas(G, cb, M, D['rasgos'], z_mar, seed, tan_bajo, coronacion_v3=bool(params.get('coronacion_v3', True)))
    log('roca: coronacion del corte sin cornisas y suave, y cuencas rellenas (v3 N2): %s' % Cf.get('n2'))
    raiz = bpy.data.objects.new('PENON_puente', None)
    raiz.empty_display_size = 2.0
    parent_collection.objects.link(raiz)
    mr = _malla_roca(G, Cf, z_mar, seed)
    # H2-1: sin recalc_face_normals (malla abierta: elegia el sentido hacia dentro) y, por si acaso,
    # vuelta completa si el volumen con signo sale negativo; ANTES de las normales personalizadas
    roca = mr.objeto(parent_collection, raiz, recalc=True, suave=True, orientar=False)
    invertida = _orientar_fuera(roca, z_mar + Z_FONDO_REL)
    sin_normal = _fijar_normales(roca, mr)
    log('roca: normales suaves de la rejilla en %d vertices (%d sin normal propia); particion de materiales %s; '
        'orientacion %s%s' % (len(roca.data.vertices), sin_normal, getattr(mr, 'info_particion', None),
                              _orientacion(roca, z_mar + Z_FONDO_REL), ' (invertida)' if invertida else ''))
    tris = {'roca': mr.n_tris()}
    log('roca: %d vertices, %d triangulos; cota maxima %.1f' % (len(mr.v), tris['roca'], float(Cf['H'].max())))
    ck = params.get('caminos_kit') or sys.modules.get('caminos_kit')
    objs, t2 = _construir_obra(parent_collection, raiz, D, T1, T2, pol, prep, z_mar, seed, log, caminos_kit=ck)
    tris.update(t2)
    casas, ob_casas, veg, ob_m = _poblar(parent_collection, raiz, D, T1, T2, pol, prep, G, Cf, roca, z_mar, casas_kit,
                                         vegetacion_kit, italiano_kit, yates_kit, seed, log)
    checks = _comprobar(roca, objs, prep, contexto, casas, veg, D['rellanos'], log, matas=ob_m, z_mar=z_mar,
                        carreteras=D.get('carreteras'))
    checks['particion_materiales'] = getattr(mr, 'info_particion', None)
    checks['coronacion_n2'] = Cf.get('n2')
    cala = D.get('cala')
    dump = params.get('debug_dump')
    if dump:
        # volcado para QA externa (matplotlib): campo H0 y trazado en planta
        np.savez(dump + '.npz', H0=Cf['H0'], M=Cf['M'], H=Cf['H'], corte=Cf['corte'], o=Cf['o'],
                 zt=Cf['zt'], llano=Cf['llano'], relleno=Cf.get('relleno', np.zeros_like(Cf['H'])), x0=G.x0, y0=G.y0, cell=G.cell)
        json.dump({'terrazas': [{'nombre': T['nombre'], 'z': T['z'], 'front': T['front'], 'back': T['back'], 'nrm': T['nrm'],
                                 'anchos': T['anchos'], 'fs': T['fs'], 'rs': T['rs']} for T in (T2, T1)],
                   'tramos': [{'nombre': t['nombre'], 'p0': t['p0'], 'p1': t['p1'], 'z0': t['z0'], 'z1': t['z1']} for t in D['tramos']],
                   'cala': ({'front': cala['front'], 'back': cala['back'], 'z': cala['z']} if cala else None),
                   'plaza': D['plaza']['poligono'], 'casas': [{k: c.get(k) for k in ('x', 'y', 'z', 'rot', 'ancho', 'fondo', 'grupo')} for c in casas],
                   'B': prep['B'].tolist(), 'S0': list(pol.S0), 'rellanos': [r['poly'] for r in D['rellanos']]},
                  open(dump + '.json', 'w'), default=str)
    info = {
        'centro_top': (round(D['plaza']['centro'][0], 2), round(D['plaza']['centro'][1], 2)),
        'z_top': round(z_pl, 2),
        'z_cumbre': round(float(Cf['H'].max()), 2),
        'cumbre': (round(pol.S0[0], 2), round(pol.S0[1], 2)),
        'plaza': {'centro': D['plaza']['centro'], 'z': z_pl, 'poligono': D['plaza']['poligono'],
                  'campanile': D['plaza']['campanile']},
        'terrazas': [{'nombre': T['nombre'], 'z': T['z'], 'front': T['front'], 'back': T['back']} for T in (T2, T1)],
        # 'muestra' es el INDICE EN LA LISTA `muestras` pasada a build (0..n-1), no el s_idx global:
        # el integrador debe sumar el indice de la primera muestra del tramo.
        # 'lado': signo respecto a la normal IZQUIERDA n del lado de la puerta (el de la roca);
        # 'ancho': ancho del rellano a lo largo de la pista (hueco que hay que abrir en el pretil)
        # 'tipo': 'escalera' (rellano peatonal con puerta) o 'carretera' (H2-5: boca de 6.4 m de una calzada
        # para coches, con valla de cierre a 6 m del tablero; el pretil del viaducto se abre 'ancho' y se
        # cierra con cancela como los enlaces del plan urbano)
        # v3 (remate): en las de ESCALERA la verja ya esta EN el hueco del pretil, retranqueada (O_VERJA) y con su
        # losa de umbral (en PENON_puente_plaza): 'valla' = None para que integrar_escena._abrir_pretil_puertas no la
        # traiga a ras del pretil (0.26 m del asfalto) ni ponga PENON_puente_plaza_rellano (desde 0.21 m); su
        # segmento va en 'verja' y la losa en 'losa'. En las de CARRETERA 'valla' sigue siendo la valla de cierre.
        'puertas': [{'nombre': r['nombre'], 'x': r['x'], 'y': r['y'], 'z': r['z'], 'muestra': r['j'],
                     'valla': (None if r.get('verja_en_hueco') else r['valla']), 'verja': r['valla'],
                     'losa': r.get('losa'), 'verja_en_hueco': bool(r.get('verja_en_hueco')),
                     'hoja': r.get('hoja'), 'o_hoja': r.get('o_hoja'),
                     'lado': int(prep['side']), 'ancho': float(r.get('ancho', 4.6)), 'tx': r['tx'],
                     'tipo': r.get('tipo', 'escalera')} for r in D['rellanos']],
        'carreteras': [{'nombre': c['nombre'], 'terraza': c['terraza'], 'largo': round(c['largo'], 1),
                        'pend_max': round(c['pend_max'], 4), 'radio_min': round(c['radio_min'], 1), 'ancho': c['ancho'],
                        'eje': [(round(p[0], 2), round(p[1], 2), round(p[2], 2)) for p in c['pts']],
                        'piazzola': [((round(l_[0], 2), round(l_[1], 2)), (round(r_[0], 2), round(r_[1], 2))) for (l_, r_) in c['piazzola']],
                        'piazzola_disco': c.get('piazzola_disco'), 'z_piazzola': c['z_piazzola']}
                       for c in (D.get('carreteras') or [])],
        'cala': ({'centro': cala['centro'], 'z_muelle': cala['z'], 'pantalan_fin': cala.get('pantalan_fin'),
                  'front': cala['front']} if cala else None),
        'entrada': ((cala['centro'][0], cala['centro'][1], cala['z']) if cala else (D['plaza']['centro'][0], D['plaza']['centro'][1], z_pl)),
        'casas': [{k: c.get(k) for k in ('nombre', 'x', 'y', 'z', 'rot', 'ancho', 'fondo', 'plantas', 'grupo', 'dz_huella')} for c in casas],
        'tramos': [{'nombre': t['nombre'], 'p0': t['p0'], 'p1': t['p1'], 'z0': t['z0'], 'z1': t['z1']} for t in D['tramos']],
        'checks': checks,
        'n_tris': tris,
    }
    raiz['info'] = json.dumps({k: v for k, v in info.items() if k not in ('casas', 'tramos')}, default=str)
    log('resumen: plaza z=%.0f en (%.0f, %.0f); cumbre z=%.0f; %d casas; tris roca %d, obra %d; checks %s'
        % (z_pl, info['centro_top'][0], info['centro_top'][1], info['z_cumbre'], len(casas), tris['roca'],
           sum(v for k, v in tris.items() if k != 'roca'), 'OK' if checks['ok'] else 'CON FALLOS'))
    return raiz, info
