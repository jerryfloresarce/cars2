# -*- coding: utf-8 -*-
"""mascara_terreno.py - MASCARA DEL TERRENO POR TEXEL (fase visual, FASE_VISUAL_PLAN.md bloque 3 punto 4).

Python del sistema (numpy + scipy + PIL), SIN bpy. Va en el pipeline tras preparar_geometria.py + urbanismo.py y
ANTES de construir_pista.py (que lee los tres PNG en MAT_terreno v2):

    python 03_blender/mascara_terreno.py [--geom geometria_3d.json] [--urb urbanismo.json] [--out 03_blender/texturas]
                                         [--qa 03_blender/renders/qa] [--px 2048] [--seed 15] [--veg vegetacion_plan.json]
    (tambien GEOM= / URBANISMO= por entorno, como el resto del pipeline)

API:  generar(geom_path, urb_path, out_dir, px=2048, seed=15, veg_plan=None, qa_dir=None) -> {'mask', 'base', 'ao', 'stats'}

Escribe (todo con la MISMA UV planar del TERRENO: u = (x - x0) / (nx * cell), v = (y - y0) / (ny * cell); fila 0 del PNG = y maximo):
  texturas/terreno_mask.png  RGBA 2048 (1 texel ~ 1 m): R matorral, G hierba seca, B tierra, A roca; R+G+B+A = 1 (+-0.02 en
                             el 99 % de los texeles); bordes con ruido de 10-30 m (nunca por celda de 4 m).
  texturas/terreno_ao.png    L 2048: cavidad + oclusion de horizonte (8 direcciones, 160 m) + hillshade suave con el sol de la escena.
  texturas/terreno_base.png  RGB 2048 sRGB: paleta por canal (paleta.json, la UNICA fuente de color) x parches de pradera x AO
                             x sombra de bosque bajo las masas de vegetacion_plan.json cuando existe. Es el txDiffuse del multicapa.
  renders/qa/terreno_mask.png (falso color + base + histograma) y renders/qa/terreno_mask_stats.json.

Reglas (plan 3.4; umbrales SOLO aqui, en UMBRALES: terreno_montana los importa de este modulo, ver PARCHES_F1_mascara.md):
  A (roca)        pendiente suavizada (8 m) > 0.68-0.80 (34-39 grados, con ruido) o mascara_roca > 0.5 (incluye los _corte de los
                  desmontes), y SIEMPRE donde la pendiente real > 1.0 (45 grados; r2: tambien con extras['capas']);
                  a < 90 m de la Loews solo manda mascara_roca (terreno congelado).
  B (tierra)      banda de 6-10 m al pie (cuesta abajo) de cada mancha de roca, y a < 8 m del borde del asfalto en sec == dirt;
                  fondo marino somero (el TERRENO sigue bajo el agua).
  G (hierba seca) llanos (pendiente < 0.35) a < 60 m de la pista y z < 60, y las bandas de terrazas del pueblo (urbanismo.json).
  R (matorral)    el resto. Cesped NO (los jardines llevan MAT_cesped, material propio).
  extras['capas'] de geometria_3d.json (bloque 1.6, cuando exista: {matorral, hierba_seca, tierra, roca} por celda) sustituye a las
  reglas de A/B/G/R y solo recibe el ruido de borde (bordes desplazados +-6 m con ruido de 30 m, r2), la roca dura y las normalizaciones.
"""
import argparse
import json
import math
import os
import struct
import sys
import time
import zlib

import numpy as np
try:
    from scipy import ndimage
    from scipy.spatial import cKDTree
except ImportError:          # dentro de Blender (sin scipy) construir_pista.py solo importa las CONSTANTES de este modulo
    ndimage = cKDTree = None

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import paleta  # noqa: E402

# ------------------------------------------------------------------ UN SOLO SITIO DE VERDAD para los umbrales (plan 3.4 / 2.2)
UMBRALES = {
    # r2 (director_f1_r1.md 6, B1 de PARCHES_F1_terreno.md): 0.70-0.84 / 10 m daban roca en el 73.3 % de las celdas de tierra
    # > 35 grados (objetivo >= 80 %); con 0.68-0.80 / 8 m terreno_montana (que importa este dict) sube a ~81 %.
    'PEND_ROCA': (0.68, 0.80),     # |grad z| suavizado a partir del cual la ladera natural es roca: 0.68 (ruido -1) .. 0.80 (ruido +1) = 34-39 grados
    'PEND_ROCA_ANCHO': 0.12,       # anchura de la transicion (en pendiente) alrededor del umbral
    'PEND_SUAVIZADO_M': 8.0,       # sigma (m) del suavizado de la pendiente antes de umbralizar (quita el ruido de celda)
    # r2: 1.25 (51 grados) dejaba verde en el 5.9 % de los texeles con nz < 0.7 (= pendiente real > 1.02, 45.6 grados; KPI del plan
    # 3: 0 %). 1.0 +- PEND_ROCA_DURA_ANCHO/2 => toda cara real > 45 grados es roca (tambien con extras['capas']).
    'PEND_ROCA_DURA': 1.0,         # |grad z| SIN suavizar a partir del cual una cara es roca pase lo que pase (45 grados: nunca hierba estirada)
    'PEND_ROCA_DURA_ANCHO': 0.30,  # transicion de la roca dura: 0.85 .. 1.15 (smoothstep)
    'WARP_BORDE_M': (6.0, 30.0),   # r2 (director cosmetico 12): bordes de las capas desplazados +-6 m con ruido de 30 m (nunca por celda)
    'ROCA_MIN_CELDAS': 12,         # manchas de roca (o huecos de hierba dentro de la roca) de menos de 12 celdas de 4 m (192 m2) se quitan
    'ROCA_ATR': 0.50,              # mascara_roca de geometria_3d.json > 0.5 -> roca (mismo umbral que color_ac ROCA_ATR 0.49 y los revisores)
    # r4 (ACOTACIONES_COORDINADOR_F1.md 4, director r3 n.º 3): 0.08 -> 0.20. En la via de capas el ruido (10 m) va en la FRONTERA del
    # canal A (x 4c(1-c): maximo donde la capa vale 0.5, 0.08 en roca o hierba puras) para romper las rectas del umbral que la
    # roca por cara del modo AC convierte en sierra (36, 50, 21, 01); los vertices de la cresta del desmonte (A ~ 0.5) oscilan
    # +-0.2 y la frontera por cara serpentea en vez de seguir la recta de la arista.
    'ROCA_ATR_RUIDO': 0.20,        # +- ruido sobre ROCA_ATR (via de reglas) y sobre la frontera del canal A (via de capas)
    'TIERRA_RUIDO': 0.20,          # r4 (cosmetico 10 del director r3, toma 36): ruido propio de 10-30 m en la frontera del canal B (tierra)
    # r4 (acotacion 4): en la cima de la postal 56 y en las laderas a < 150 m de las camaras 51 y 07 (renders/ab/_base_antes/camaras.json)
    # la roca POR CARA del modo AC (atributo 'roca' del TERRENO, lo que lee color_ac.separar_roca_terreno) exige nz < ROCA_NZ_ZONA
    # (52 grados) en vez del nz < 0.82 general, y se limpian los triangulos aislados (< ROCA_ZONA_MIN_CARAS caras): sin 'dientes'.
    # La mascara por texel (este fichero) NO cambia en esas zonas: lo aplica construir_pista.roca_zonas_nz sobre el atributo.
    'ROCA_NZ_ZONA': 0.62,          # nz maximo de una cara de roca por atributo dentro de las zonas (umbral de terreno fuera: umbrales_roca()['nz'])
    'ROCA_ZONA_MIN_CARAS': 6,      # componentes de roca (o huecos) de menos de 6 caras dentro de las zonas se quitan (se rellenan)
    'ROCA_ZONA_FUNDIDO_M': 12.0,   # anillo de fundido del borde de cada zona (m; con 30 m el anillo concentraba 1/3 de los dientes que quedaban)
    'ROCA_NZ_ZONAS': {             # nombre de la toma: (x, y, radio m) = loc de la camara congelada en renders/ab/_base_antes/camaras.json
        '56_postal_cima_bahia': (47.972, 567.543, 150.0),
        '51_piloto_s1700': (15.023, 426.256, 150.0),
        '07_tierra_subida': (-12.016, 294.887, 150.0),
    },
    'BANDA_2M_M': 25.0,            # r4 (acotacion 4): banda junto al asfalto donde el TERRENO se subdivide a 2 m (construir_pista.subdividir_banda_terreno).
                                   # 25 y no 20 m: la cresta del desmonte de la tierra tallada esta a 4.5-25 m del borde (ahi esta la sierra de 51) y
                                   # +45.3 k vertices siguen dentro del tope de +40-50 k del coordinador (20 m: +38.3 k; 30 m: +52.1 k)
    'PIE_M': (6.0, 10.0),          # banda de tierra al pie de cada roca (m): 6 (ruido -1) .. 10 (ruido +1)
    'DIRT_BORDE_M': 8.0,           # tierra a < 8 m del borde del asfalto donde sec == dirt
    'LLANO_PEND': 0.35,            # llano: pendiente < 0.35
    'LLANO_DIST_M': 60.0,          # hierba seca en llanos a < 60 m del borde de la pista ...
    'LLANO_Z': 60.0,               # ... y con z < 60 m
    'RUIDO_M': (10.0, 30.0),       # longitudes de onda del ruido de borde (m)
    'LOEWS_R_INTACTA': 90.0,       # a < 90 m de la rotonda Loews no se aplica la regla de pendiente (terreno congelado, terreno_montana.R_LOEWS_INTACTA)
}
# canal -> (nombre de capa, color de paleta.json). El orden R, G, B, A es el de txMask / txDetailR..A del multicapa.
CANALES = (('R', 'matorral', 'oliva_oscuro'), ('G', 'hierba_seca', 'hierba_seca'),
           ('B', 'tierra', 'tierra'), ('A', 'roca', 'caliza_ocre'))
# sol de la escena (construir_pista.py lo importa de aqui para que el hillshade de la AO y el sol de EEVEE coincidan):
# elevacion 48 grados (rotacion X 42), azimut 151 grados desde +x hacia +y = rasante a la ladera del tramo de tierra
# (su cuesta abajo media mira a 241 grados; medido sobre geometria_3d.json el 04/10). Rotacion de Blender: rz = azimut + 90.
SOL = {'elev_deg': 48.0, 'azimut_deg': 151.0, 'rot_blender_deg': (42.0, 0.0, -119.0)}
FICHEROS = {'mask': 'terreno_mask.png', 'base': 'terreno_base.png', 'ao': 'terreno_ao.png',
            'qa': 'terreno_mask.png', 'stats': 'terreno_mask_stats.json'}
DEF_GEOM = os.path.join(AQUI, 'geometria_3d.json')
DEF_URB = os.path.join(AQUI, 'urbanismo.json')
DEF_OUT = os.path.join(AQUI, 'texturas')
DEF_QA = os.path.join(AQUI, 'renders', 'qa')


# ------------------------------------------------------------------ utilidades numericas
def _smooth01(x, a, b):
    """0 en x <= a, 1 en x >= b, smoothstep entre medias (a < b; si a > b, invertido). a y b pueden ser arrays."""
    a = np.asarray(a, np.float32)
    b = np.asarray(b, np.float32)
    inv = a > b
    lo = np.where(inv, b, a)
    hi = np.where(inv, a, b)
    t = np.clip((x - lo) / np.maximum(hi - lo, 1e-9), 0.0, 1.0)
    s = t * t * (3.0 - 2.0 * t)
    return np.where(inv, 1.0 - s, s).astype(np.float32)


def _ruido(rng, shape, lam_px, octavas=2):
    """Ruido de valor suave en [-1, 1] con longitud de onda ~lam_px texeles (octavas a lam, lam/2 ...)."""
    out = np.zeros(shape, np.float32)
    for k in range(octavas):
        lam = max(2.0, float(lam_px) / (2 ** k))
        nyc, nxc = int(math.ceil(shape[0] / lam)) + 3, int(math.ceil(shape[1] / lam)) + 3
        g = rng.standard_normal((nyc, nxc)).astype(np.float32)
        z = ndimage.zoom(g, lam, order=3, prefilter=True)
        out += z[:shape[0], :shape[1]] * (0.5 ** k)
    out /= max(float(out.std()), 1e-6) * 2.0
    return np.clip(out, -1.0, 1.0)


def _up(a_grid, shape, warp=None):
    """Rejilla de celdas (ny, nx) -> texeles (shape): interpolacion bilineal en los centros de texel.
    warp = (dJ, dI) en CELDAS por texel (shape): desplaza el muestreo (ruido de borde de 10-30 m sin tocar la rejilla)."""
    ny, nx = a_grid.shape
    jj = (np.arange(shape[0], dtype=np.float32) + 0.5) * (ny / shape[0])
    ii = (np.arange(shape[1], dtype=np.float32) + 0.5) * (nx / shape[1])
    J, I = np.meshgrid(jj, ii, indexing='ij')
    if warp is not None:
        J = J + warp[0]
        I = I + warp[1]
    return ndimage.map_coordinates(a_grid.astype(np.float32), [J, I], order=1, mode='nearest')


def _forzar_roca(w, wA):
    """Sube el canal A a max(A, wA) y reparte el resto proporcionalmente entre R, G y B (la suma se normaliza despues)."""
    A_new = np.maximum(w['A'], wA)
    resto = w['R'] + w['G'] + w['B']
    f = np.where(resto > 1e-6, (1.0 - A_new) / np.maximum(resto, 1e-6), 0.0)
    for k in ('R', 'G', 'B'):
        w[k] = (w[k] * f).astype(np.float32)
    w['A'] = A_new.astype(np.float32)
    return w


def _forzar_tierra(w, wB):
    """Sube el canal B a max(B, wB x (1 - A)) sin tocar la roca: solo R y G ceden (banda de tierra junto al asfalto en 'dirt')."""
    B_new = np.maximum(w['B'], wB * (1.0 - w['A']))
    rg = w['R'] + w['G']
    f = np.where(rg > 1e-6, np.clip(1.0 - w['A'] - B_new, 0.0, 1.0) / np.maximum(rg, 1e-6), 0.0)
    w['R'] = (w['R'] * f).astype(np.float32)
    w['G'] = (w['G'] * f).astype(np.float32)
    w['B'] = B_new.astype(np.float32)
    return w


def _poligonos_a_mascara(polys, shape, x0, y0, Lx, Ly):
    """Rasteriza poligonos (listas de (x, y) en metros) a una mascara float (shape) en coordenadas de texel (fila = y creciente)."""
    m = np.zeros(shape, np.float32)
    if not polys:
        return m
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return m
    img = Image.new('L', (shape[1], shape[0]), 0)
    dr = ImageDraw.Draw(img)
    for poly in polys:
        pts = [((px - x0) / Lx * shape[1], (py - y0) / Ly * shape[0]) for (px, py) in poly]
        if len(pts) >= 3:
            dr.polygon(pts, fill=255)
    return np.asarray(img, dtype=np.float32) / 255.0


def _png(ruta, arr8):
    """Guarda un uint8 (H, W) | (H, W, 3) | (H, W, 4) como PNG. PIL si existe; si no, escritor minimo con zlib."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    try:
        from PIL import Image
        Image.fromarray(arr8).save(ruta, optimize=False)
        return ruta
    except Exception:
        pass
    h, w = arr8.shape[:2]
    canales = 1 if arr8.ndim == 2 else arr8.shape[2]
    tipo = {1: 0, 3: 2, 4: 6}[canales]
    raw = b''.join(b'\x00' + arr8[j].tobytes() for j in range(h))

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    with open(ruta, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, tipo, 0, 0, 0))
                 + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
    return ruta


def _lin_a_srgb8(lin):
    c = np.clip(lin, 0.0, 1.0)
    s = np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055)
    return np.clip(np.round(s * 255.0), 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ AO desde el heightmap (rejilla de 4 m, luego a texeles)
def _sky_view(z, cell, n_dir=8, r_max=160.0, n_r=16):
    """Factor de cielo visible: 1 - media sobre 8 direcciones del seno del angulo de horizonte a < r_max."""
    ny, nx = z.shape
    J, I = np.mgrid[0:ny, 0:nx].astype(np.float32)
    rs = np.linspace(cell, r_max, n_r)
    svf = np.zeros_like(z, dtype=np.float32)
    for k in range(n_dir):
        a = 2.0 * math.pi * k / n_dir
        dx, dy = math.cos(a), math.sin(a)
        hmax = np.zeros_like(z, dtype=np.float32)
        for r in rs:
            zr = ndimage.map_coordinates(z, [J + dy * r / cell, I + dx * r / cell], order=1, mode='nearest')
            hmax = np.maximum(hmax, (zr - z) / r)
        svf += 1.0 - np.sin(np.arctan(np.maximum(hmax, 0.0)))
    return svf / n_dir


def _hillshade(z, cell, elev_deg, az_deg):
    gy, gx = np.gradient(z, cell)
    nrm = np.sqrt(gx * gx + gy * gy + 1.0)
    e, a = math.radians(elev_deg), math.radians(az_deg)
    lx, ly, lz = math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)
    hs = (-gx * lx - gy * ly + lz) / nrm
    return np.clip(hs, 0.0, 1.0)


def calcular_ao(z, cell, sol=SOL):
    """AO [0, 1] por celda: cavidad (laplaciano) + horizonte 8 direcciones + hillshade suave. Devuelve (ao, partes)."""
    zs = ndimage.gaussian_filter(z, 1.0)
    lap = ndimage.laplace(zs) / (cell * cell)          # > 0 en vaguadas (concavo), < 0 en crestas
    cav = np.clip(lap * 6.0, 0.0, 1.0)
    conv = np.clip(-lap * 6.0, 0.0, 1.0)
    svf = _sky_view(zs, cell)
    hs = ndimage.gaussian_filter(_hillshade(zs, cell, sol['elev_deg'], sol['azimut_deg']), 1.0)
    ao = (0.30 + 0.70 * np.power(np.clip(svf, 0.0, 1.0), 1.6)) * (1.0 - 0.35 * cav) * (0.85 + 0.15 * hs) * (1.0 + 0.08 * conv)
    return np.clip(ao, 0.0, 1.0).astype(np.float32), {'svf': svf, 'cavidad': cav, 'hillshade': hs}


# ------------------------------------------------------------------ vegetacion_plan.json (sombra de bosque), formato tolerante
def _sombra_bosque(veg_plan, shape, x0, y0, Lx, Ly):
    """0..1 por texel bajo las copas: 'sombra de bosque' de terreno_base.png (el TERRENO no recibe sombra de los arboles en AC).
    Lee vegetacion_plan.json (contrato de PARCHES_F1_vegetacion_plan.md A3): d['plantas'] con especie de clase 'arbol' y radio
    1.2 x d['especies'][e]['radio_copa_m'] x p['escala_xy']; si no hay plantas, d['masas'] (cx, cy, r); tambien acepta
    'arboles' [{x, y}|{xyz}] o una lista de puntos. Discos difuminados 3 m; 1 = sombra plena."""
    if veg_plan is None:
        return None
    if isinstance(veg_plan, str):
        if not os.path.exists(veg_plan):
            return None
        veg_plan = json.load(open(veg_plan, encoding='utf-8'))
    s = np.zeros(shape, np.float32)
    sx, sy = shape[1] / Lx, shape[0] / Ly
    plantas = veg_plan.get('plantas') if isinstance(veg_plan, dict) else None
    masas = veg_plan.get('masas') if isinstance(veg_plan, dict) else None
    arboles = veg_plan.get('arboles') if isinstance(veg_plan, dict) else (veg_plan if isinstance(veg_plan, list) else None)
    discos = []                                   # (x, y, radio_m)
    if plantas:
        esp = veg_plan.get('especies') or {}
        for p in plantas:
            e = esp.get(p.get('especie'), {})
            if e.get('clase', 'arbol') != 'arbol':
                continue
            discos.append((float(p['x']), float(p['y']), 1.2 * float(e.get('radio_copa_m', 3.0)) * float(p.get('escala_xy', 1.0))))
    elif masas:
        for m in masas:
            discos.append((float(m.get('cx', m.get('x', 0.0))), float(m.get('cy', m.get('y', 0.0))),
                           float(m.get('r', m.get('radio', 15.0)))))
    if discos:
        try:
            from PIL import Image, ImageDraw
            img = Image.new('L', (shape[1], shape[0]), 0)
            dr = ImageDraw.Draw(img)
            for (px_, py_, r) in discos:
                cx, cy = (px_ - x0) * sx, (py_ - y0) * sy
                dr.ellipse([cx - r * sx, cy - r * sy, cx + r * sx, cy + r * sy], fill=255)
            s = np.maximum(s, np.asarray(img, np.float32) / 255.0)
        except Exception as e:
            print('AVISO: sombra de bosque sin PIL (%s)' % e)
    if arboles:
        dens = np.zeros(shape, np.float32)
        for a in arboles:
            xy = a.get('xyz', [a.get('x'), a.get('y')]) if isinstance(a, dict) else a
            if xy is None or xy[0] is None:
                continue
            i, j = int((float(xy[0]) - x0) * sx), int((float(xy[1]) - y0) * sy)
            if 0 <= i < shape[1] and 0 <= j < shape[0]:
                dens[j, i] += 1.0
        dens = ndimage.gaussian_filter(dens, 8.0 * sx)        # radio de copa ~8 m
        s = np.maximum(s, np.clip(dens / max(float(dens.max()), 1e-6) * 2.0, 0.0, 1.0))
    s = ndimage.gaussian_filter(s, 3.0 * sx)
    return s if s.any() else None


# ------------------------------------------------------------------ calculo principal
def calcular(G, U=None, px=2048, seed=15, veg_plan=None, sol=SOL):
    """Devuelve dict con 'mask' (px, px, 4) float, 'base' (px, px, 3) lineal, 'ao' (px, px), 'stats' y los campos auxiliares."""
    t0 = time.time()
    T = G['terreno']
    nx, ny, cell = int(T['nx']), int(T['ny']), float(T['cell'])
    x0, y0 = float(T['x0']), float(T['y0'])
    Lx, Ly = nx * cell, ny * cell
    shape = (px, px)
    rng = np.random.default_rng(int(seed) + 101)
    z = np.asarray(T['z'], np.float32).reshape(ny, nx)
    mar = np.asarray(T['mar'], np.float32).reshape(ny, nx) > 0.5
    mroca = np.asarray(G.get('mascara_roca') or np.zeros(nx * ny), np.float32).reshape(ny, nx)

    # --- campos por celda (4 m) ---
    gy, gx = np.gradient(z, cell)
    pend = np.hypot(gx, gy).astype(np.float32)
    pend_s = ndimage.gaussian_filter(pend, UMBRALES['PEND_SUAVIZADO_M'] / cell)
    S = G['muestras']
    P = np.array([[m['x'], m['y']] for m in S], np.float64)
    W = np.array([m['w'] for m in S], np.float32)
    es_dirt = np.array([m['sec'] == 'dirt' for m in S])
    X = x0 + np.arange(nx) * cell
    Y = y0 + np.arange(ny) * cell
    XX, YY = np.meshgrid(X, Y)
    d_eje, i_near = cKDTree(P).query(np.c_[XX.ravel(), YY.ravel()])
    d_borde = (d_eje.reshape(ny, nx) - W[i_near].reshape(ny, nx) / 2.0).astype(np.float32)
    dirt_g = es_dirt[i_near].reshape(ny, nx).astype(np.float32)
    lw = G.get('loews') or {}
    d_loews = np.hypot(XX - float(lw.get('x', 1e9)), YY - float(lw.get('y', 1e9))).astype(np.float32)
    ao_g, partes_ao = calcular_ao(z, cell, sol)
    # convexidad (crestas y espolones > 0, vaguadas < 0): la roca aflora en las crestas, no al azar ('camuflaje' de la v3)
    conv_g = np.clip(-ndimage.laplace(ndimage.gaussian_filter(z, 2.0)) / (cell * cell) * 25.0, -1.0, 1.0).astype(np.float32)

    # --- a texeles ---
    z_t = _up(z, shape)
    mar_t = _up(mar.astype(np.float32), shape) > 0.5
    pend_t = _up(pend, shape)
    pend_s_t = _up(pend_s, shape)
    mroca_t = _up(mroca, shape)
    d_borde_t = _up(d_borde, shape)
    dirt_t = _up(dirt_g, shape) > 0.5
    loews_t = _up(d_loews, shape) < UMBRALES['LOEWS_R_INTACTA']
    ao_t = np.clip(_up(ndimage.gaussian_filter(ao_g, 0.6), shape), 0.0, 1.0)
    m_por_texel = Lx / px
    lam0, lam1 = UMBRALES['RUIDO_M']
    n_a = np.clip(0.6 * _ruido(rng, shape, lam1 / m_por_texel) - 0.6 * _up(conv_g, shape), -1.0, 1.0)   # 30 m + crestas (umbral mas bajo en las convexas)
    n_b = _ruido(rng, shape, lam0 / m_por_texel)        # 10 m: umbral del atributo
    n_c = _ruido(rng, shape, 20.0 / m_por_texel)        # 20 m: pie, borde de tierra
    n_d = _ruido(rng, shape, lam1 / m_por_texel)        # 30 m: alcance de la hierba seca

    # caras muy empinadas (pendiente REAL, sin suavizar): roca siempre, venga de donde venga la capa (es la 'hierba estirada' de
    # las capturas y el KPI '0 % verde en nz < 0.7' del plan 3). r2: tambien sobre extras['capas'], que se umbralizan con la
    # pendiente suavizada y dejaban verde en el 5.9 % de esas caras. A < LOEWS_R_INTACTA no se toca (terreno congelado).
    _dura_lo = UMBRALES['PEND_ROCA_DURA'] - UMBRALES['PEND_ROCA_DURA_ANCHO'] / 2
    _dura_hi = UMBRALES['PEND_ROCA_DURA'] + UMBRALES['PEND_ROCA_DURA_ANCHO'] / 2
    wA_dura = np.where(loews_t, 0.0, _smooth01(pend_t, _dura_lo, _dura_hi)).astype(np.float32)
    # banda de tierra a < DIRT_BORDE_M del asfalto en sec == dirt (regla B del plan): ligada a la pista, no a la rejilla, asi que
    # se impone igual en las dos vias (r2: con el desplazamiento de bordes de las capas la banda perdia un 4 % de sus texeles)
    borde_dirt = (_smooth01(d_borde_t, UMBRALES['DIRT_BORDE_M'] + 1.5 * n_c + 1.5, UMBRALES['DIRT_BORDE_M'] + 1.5 * n_c - 1.5)
                  * dirt_t).astype(np.float32)
    capas = (G.get('extras') or {}).get('capas') if isinstance(G.get('extras'), dict) else None
    if capas and all(k in capas for k in ('matorral', 'hierba_seca', 'tierra', 'roca')):
        # bloque 1.6: las capas del terreno mandan. Aqui: (a) bordes desplazados +-WARP_BORDE_M con ruido de 30 m al muestrear la
        # rejilla (r2, cosmetico 12 del director: la frontera dorado/tierra del penon en 36 era dura; nunca por celda), (b) ruido
        # fino de 10 m, (c) roca dura por pendiente real (abajo, comun), (d) normalizacion
        amp_m, lam_m = UMBRALES['WARP_BORDE_M']
        amp_c = (amp_m / cell) * (1.0 - loews_t.astype(np.float32))          # en celdas; 0 a < 90 m de la Loews
        warp = (_ruido(rng, shape, lam_m / m_por_texel) * amp_c, _ruido(rng, shape, lam_m / m_por_texel) * amp_c)
        w = {}
        # r4 (acotacion 4 del coordinador; director r3 n.º 3 y cosmetico 10): canal A con ruido ROCA_ATR_RUIDO (0.20) de 10 m
        # concentrado en la FRONTERA (x 4c(1-c)) y canal B con ruido propio TIERRA_RUIDO de 10-30 m (junto a los cortes
        # someros _corte_suave de terreno_montana); R y G siguen con 0.08. En roca o hierba puras el ruido sigue siendo 0.08:
        # nada motea las praderas.
        n_bB = 0.5 * (n_b + n_d)
        for k, nombre in (('R', 'matorral'), ('G', 'hierba_seca'), ('B', 'tierra'), ('A', 'roca')):
            c_k = _up(np.asarray(capas[nombre], np.float32).reshape(ny, nx), shape, warp)
            if k in ('A', 'B'):
                amp_k = UMBRALES['ROCA_ATR_RUIDO' if k == 'A' else 'TIERRA_RUIDO']
                amp = 0.08 + (amp_k - 0.08) * np.clip(4.0 * c_k * (1.0 - c_k), 0.0, 1.0)
                w[k] = np.clip(c_k + amp * (n_b if k == 'A' else n_bB), 0.0, 1.0)
            else:
                w[k] = np.clip(c_k + 0.08 * n_b, 0.0, 1.0)
            del c_k
        origen = 'extras.capas de geometria_3d.json (+ bordes +-%g m, ruido A %.2f / B %.2f en la frontera, roca dura > %.2f)' % (
            amp_m, UMBRALES['ROCA_ATR_RUIDO'], UMBRALES['TIERRA_RUIDO'], UMBRALES['PEND_ROCA_DURA'])
    else:
        p_lo, p_hi = UMBRALES['PEND_ROCA']
        umbral = 0.5 * (p_lo + p_hi) + 0.5 * (p_hi - p_lo) * n_a
        wA_pend = _smooth01(pend_s_t, umbral - UMBRALES['PEND_ROCA_ANCHO'] / 2, umbral + UMBRALES['PEND_ROCA_ANCHO'] / 2)
        wA_pend = np.where(loews_t, 0.0, wA_pend)
        u_atr = UMBRALES['ROCA_ATR'] + UMBRALES['ROCA_ATR_RUIDO'] * n_b
        wA_atr = _smooth01(mroca_t, u_atr - 0.06, u_atr + 0.06)
        A = np.maximum(np.maximum(wA_pend, wA_atr), wA_dura)
        # limpieza morfologica (como terreno_montana v3): ni manchas ni huecos de menos de ROCA_MIN_CELDAS celdas
        min_tex = int(UMBRALES['ROCA_MIN_CELDAS'] * (cell / m_por_texel) ** 2)
        A_bin = A > 0.5
        lab, n_lab = ndimage.label(A_bin)
        if n_lab:
            tam = np.bincount(lab.ravel())
            peq = tam < min_tex
            peq[0] = False
            A = np.where(peq[lab], A * 0.3, A)
        lab, n_lab = ndimage.label(~(A > 0.5))
        if n_lab:
            tam = np.bincount(lab.ravel())
            peq = tam < min_tex
            peq[0] = False
            A = np.where(peq[lab], np.maximum(A, 0.85), A)
        A = ndimage.gaussian_filter(A.astype(np.float32), 1.0)
        # pie de la roca (cuesta abajo): distancia a la roca y cota de la roca mas cercana
        A_bin = A > 0.5
        if A_bin.any():
            dist_px, idx = ndimage.distance_transform_edt(~A_bin, return_indices=True)
            z_roca_cercana = z_t[idx[0], idx[1]]
            dist_m = dist_px * m_por_texel
            pie_m = 0.5 * sum(UMBRALES['PIE_M']) + 0.5 * (UMBRALES['PIE_M'][1] - UMBRALES['PIE_M'][0]) * n_c
            debajo = _smooth01(z_roca_cercana - z_t, 0.0, 1.5)
            pie = _smooth01(dist_m, pie_m + 1.5, pie_m - 1.5) * (dist_m > 0.0) * debajo
        else:
            pie = np.zeros(shape, np.float32)
        B = np.maximum(pie, borde_dirt) * (1.0 - A)
        w_llano = _smooth01(pend_s_t, UMBRALES['LLANO_PEND'] + 0.06, UMBRALES['LLANO_PEND'] - 0.06)
        w_dist = _smooth01(d_borde_t, UMBRALES['LLANO_DIST_M'] + 10.0 * n_d + 8.0, UMBRALES['LLANO_DIST_M'] + 10.0 * n_d - 8.0)
        w_z = _smooth01(z_t, UMBRALES['LLANO_Z'] + 6.0 * n_d + 6.0, UMBRALES['LLANO_Z'] + 6.0 * n_d - 6.0)
        G_ = w_llano * w_dist * w_z
        # terrazas del pueblo: entre casas hierba seca (nunca matorral ni cesped)
        bandas = []
        if U:
            for sec in U.get('sectores', []):
                for tz in sec.get('terrazas', []):
                    for poly in tz.get('banda', []):
                        if isinstance(poly, list) and len(poly) >= 3 and isinstance(poly[0], (list, tuple)):
                            bandas.append([(float(p[0]), float(p[1])) for p in poly])
        if bandas:
            m_b = _poligonos_a_mascara(bandas, shape, x0, y0, Lx, Ly)
            m_b = ndimage.gaussian_filter(m_b, 3.0 / m_por_texel)
            G_ = np.maximum(G_, np.clip(m_b * 1.2, 0.0, 1.0) * w_llano)
        G_ = G_ * (1.0 - A) * (1.0 - B)
        R = np.clip(1.0 - A - B - G_, 0.0, 1.0)
        w = {'R': R, 'G': G_, 'B': B, 'A': A}
        origen = 'reglas 3.4 (pendiente, mascara_roca, distancia a la pista, z, terrazas)'
    # roca dura por pendiente real y banda de tierra del tramo de tierra (comunes a las dos vias; en la de reglas ya iban dentro
    # de A y B: idempotentes)
    w = _forzar_roca(w, wA_dura)
    w = _forzar_tierra(w, borde_dirt)
    # fondo marino: el terreno continua bajo el agua -> tierra (arena en la base), sin matorral ni hierba
    fondo = mar_t & (z_t < 0.3)
    w['R'] = np.where(fondo, 0.0, w['R'])
    w['G'] = np.where(fondo, 0.0, w['G'])
    w['B'] = np.where(fondo, np.maximum(w['B'], 1.0 - w['A']), w['B'])
    suma = w['R'] + w['G'] + w['B'] + w['A']
    vacio = suma < 1e-4
    w['R'] = np.where(vacio, 1.0, w['R'])
    suma = np.where(vacio, 1.0, suma)
    for k in w:
        w[k] = (w[k] / suma).astype(np.float32)
    mask = np.stack([w['R'], w['G'], w['B'], w['A']], axis=2)

    # --- base: paleta por canal x parches x AO x sombra de bosque ---
    C = {n: np.array(paleta.rgb(n), np.float32) for n in
         ('oliva_oscuro', 'salvia', 'hierba_seca', 'tierra', 'caliza_ocre', 'caliza_gris_calido', 'arena')}
    n_parche = _ruido(rng, shape, 150.0 / m_por_texel, 2)
    n_60 = _ruido(rng, shape, 60.0 / m_por_texel, 2)
    n_25 = _ruido(rng, shape, 25.0 / m_por_texel, 2)
    parches = (1.0 + 0.15 * n_parche)[..., None]
    t60 = (0.5 + 0.5 * n_60)[..., None]
    t25 = (0.5 + 0.5 * n_25)[..., None]
    col_R = C['oliva_oscuro'] * (1.0 - 0.35 * t60) + C['salvia'] * (0.35 * t60)
    col_G = C['hierba_seca'] * parches
    col_B = C['tierra'] * (1.0 + 0.10 * n_25)[..., None]
    col_A = C['caliza_ocre'] * (1.0 - 0.5 * t25) + C['caliza_gris_calido'] * (0.5 * t25)
    base = (w['R'][..., None] * col_R + w['G'][..., None] * col_G + w['B'][..., None] * col_B + w['A'][..., None] * col_A)
    alto = (np.clip((z_t - 150.0) / 40.0, 0.0, 1.0) * 0.25)[..., None]      # cumbres: algo mas gris
    base = base * (1.0 - alto) + C['caliza_gris_calido'] * alto
    # fondo somero: arena apagada (bajo el agua translucida; NUNCA una banda blanquecina de playa, KPI del bloque 6) y mas
    # oscura con la profundidad
    prof = np.clip(-z_t / 4.0, 0.0, 1.0)
    col_fondo = C['arena'][None, None, :] * (0.62 - 0.25 * prof)[..., None]
    base = np.where(fondo[..., None], col_fondo, base)
    base = base * ao_t[..., None]
    sombra = _sombra_bosque(veg_plan, shape, x0, y0, Lx, Ly)
    if sombra is not None:
        s3 = (sombra * (1.0 - w['A']) * (~fondo))[..., None]
        base = base * (1.0 - 0.40 * s3) * (1.0 - 0.3 * s3) + (C['oliva_oscuro'] * 0.6) * (0.3 * s3)

    # --- stats ---
    m8 = np.clip(np.round(mask * 255.0), 0, 255).astype(np.uint8)
    suma8 = m8.astype(np.int32).sum(axis=2)
    tierra = ~fondo
    dom = np.argmax(mask, axis=2)
    nombres = [c[1] for c in CANALES]
    nz_lt = tierra & (pend_t > math.tan(math.acos(0.7)))
    emp = tierra & (pend_t > 0.84)          # KPI fijo (40 grados), independiente de UMBRALES para comparar rondas
    verdeRG = (mask[..., 0] + mask[..., 1]) > 0.5
    dirt8 = tierra & dirt_t & (d_borde_t > -0.5) & (d_borde_t < UMBRALES['DIRT_BORDE_M'])
    stats = {
        'px': px, 'texel_m': [round(Lx / px, 4), round(Ly / px, 4)], 'seed': int(seed), 'origen_pesos': origen,
        'umbrales': UMBRALES, 'sol': sol, 'veg_plan': sombra is not None,
        'pct_texeles_tierra': round(float(tierra.mean() * 100.0), 2),
        'area_pct_tierra_dominante': {nombres[k]: round(float((dom[tierra] == k).mean() * 100.0), 2) for k in range(4)},
        'media_canal_tierra': {nombres[k]: round(float(mask[..., k][tierra].mean()), 4) for k in range(4)},
        'histograma_8_bins_pct_tierra': {nombres[k]: [round(float(v) * 100.0, 2) for v in
                                                      np.histogram(mask[..., k][tierra], bins=8, range=(0.0, 1.0))[0] / max(int(tierra.sum()), 1)]
                                         for k in range(4)},
        'suma_ok_pct': round(float((np.abs(suma8 - 255) <= 5).mean() * 100.0), 3),
        'suma_desvio_max_8bit': int(np.abs(suma8 - 255).max()),
        'nz_lt_0_7': {'pct_texeles_tierra': round(float(nz_lt.sum() / max(int(tierra.sum()), 1) * 100.0), 2),
                      'pct_roca_A_gt_0_5': round(float((mask[..., 3][nz_lt] > 0.5).mean() * 100.0), 2) if nz_lt.any() else None,
                      'pct_verde_RG_gt_0_5': round(float(verdeRG[nz_lt].mean() * 100.0), 2) if nz_lt.any() else None},
        'pend_gt_0_84': {'pct_texeles_tierra': round(float(emp.sum() / max(int(tierra.sum()), 1) * 100.0), 2),
                         'pct_roca_A_gt_0_5': round(float((mask[..., 3][emp] > 0.5).mean() * 100.0), 2) if emp.any() else None,
                         'pct_verde_RG_gt_0_5': round(float(verdeRG[emp].mean() * 100.0), 2) if emp.any() else None},
        'dirt_borde_lt_8m': {'texeles': int(dirt8.sum()),
                             'pct_tierra_B_gt_0_5': round(float((mask[..., 2][dirt8] > 0.5).mean() * 100.0), 2) if dirt8.any() else None},
        'ao': {'media_tierra': round(float(ao_t[tierra].mean()), 4), 'p05': round(float(np.percentile(ao_t[tierra], 5)), 4),
               'p95': round(float(np.percentile(ao_t[tierra], 95)), 4)},
        'base_media_lineal_tierra': [round(float(v), 4) for v in base[tierra].mean(axis=0)],
        'tiempo_s': round(time.time() - t0, 1),
    }
    return {'mask': mask, 'mask8': m8, 'base': base, 'ao': ao_t, 'stats': stats, 'fondo': fondo, 'pend_t': pend_t,
            'z_t': z_t, 'hillshade': partes_ao['hillshade'], 'x0': x0, 'y0': y0, 'Lx': Lx, 'Ly': Ly, 'muestras': P}


# ------------------------------------------------------------------ QA (PIL)
def _qa_figura(res, ruta):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:
        print('AVISO: sin PIL, no hay figura QA (%s)' % e)
        return None
    mask, base, fondo = res['mask'], res['base'], res['fondo']
    px = mask.shape[0]
    # falso color: cada canal con su color de paleta (sRGB) x hillshade de la AO
    cols = np.array([paleta.srgb(c[2]) for c in CANALES], np.float32)          # R G B A
    fc = np.tensordot(mask, cols, axes=([2], [0]))
    hs = _up(res['hillshade'], (px, px))
    fc = fc * (0.55 + 0.45 * hs)[..., None]
    azul = np.array(paleta.srgb('mar_orilla'), np.float32) * 0.6
    fc = np.where(fondo[..., None], fc * 0.5 + azul * 0.5, fc)
    fc8 = np.clip(fc * 255.0, 0, 255).astype(np.uint8)[::-1]                   # fila 0 = y max
    base8 = _lin_a_srgb8(base)[::-1]
    W = 900
    pan1 = Image.fromarray(fc8).resize((W, W), Image.LANCZOS)
    pan2 = Image.fromarray(base8).resize((W, W), Image.LANCZOS)
    # pista
    P = res['muestras']
    def xy(p):
        return ((p[0] - res['x0']) / res['Lx'] * W, (1.0 - (p[1] - res['y0']) / res['Ly']) * W)
    for pan in (pan1, pan2):
        dr = ImageDraw.Draw(pan)
        pts = [xy(p) for p in P[::2]]
        dr.line(pts + [pts[0]], fill=(40, 10, 10), width=2)
    try:
        f = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
        fb = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 18)
    except Exception:
        f = fb = ImageFont.load_default()
    st = res['stats']
    img = Image.new('RGB', (2 * W + 60, W + 230), (235, 235, 235))
    img.paste(pan1, (20, 60)); img.paste(pan2, (W + 40, 60))
    dr = ImageDraw.Draw(img)
    dr.text((20, 15), 'terreno_mask.png (falso color: R matorral oliva, G hierba seca, B tierra, A roca caliza; mar azulado) x hillshade',
            fill=(20, 20, 20), font=fb)
    dr.text((W + 40, 15), 'terreno_base.png (paleta x parches x AO%s)' % (' x sombra de bosque' if st['veg_plan'] else ''),
            fill=(20, 20, 20), font=fb)
    y = W + 70
    lin = ['area dominante (tierra): ' + ', '.join('%s %.1f %%' % (k, v) for k, v in st['area_pct_tierra_dominante'].items()),
           'suma R+G+B+A = 1 +- 0.02 en %.2f %% de los texeles (desvio max %d/255) | origen: %s' % (
               st['suma_ok_pct'], st['suma_desvio_max_8bit'], st['origen_pesos']),
           'nz < 0.7 (%.1f %% de la tierra): roca %.1f %%, verde R+G %.1f %% | pendiente > 0.84: roca %.1f %%, verde %.1f %%' % (
               st['nz_lt_0_7']['pct_texeles_tierra'], st['nz_lt_0_7']['pct_roca_A_gt_0_5'] or 0, st['nz_lt_0_7']['pct_verde_RG_gt_0_5'] or 0,
               st['pend_gt_0_84']['pct_roca_A_gt_0_5'] or 0, st['pend_gt_0_84']['pct_verde_RG_gt_0_5'] or 0),
           'borde dirt < 8 m: tierra %.1f %% | AO media %.3f (p05 %.3f, p95 %.3f) | %s texel/m | seed %d | %.1f s' % (
               st['dirt_borde_lt_8m']['pct_tierra_B_gt_0_5'] or 0, st['ao']['media_tierra'], st['ao']['p05'], st['ao']['p95'],
               st['texel_m'][0], st['seed'], st['tiempo_s'])]
    for l_ in lin:
        dr.text((20, y), l_, fill=(20, 20, 20), font=f)
        y += 22
    # histograma por canal (8 bins)
    x = 20
    for k, (c, nombre, _) in enumerate(CANALES):
        h = st['histograma_8_bins_pct_tierra'][nombre]
        dr.text((x, y + 2), nombre, fill=(20, 20, 20), font=f)
        for b, v in enumerate(h):
            alt = int(min(1.0, v / 60.0) * 40)
            dr.rectangle([x + 90 + b * 14, y + 44 - alt, x + 90 + b * 14 + 11, y + 44], fill=tuple(int(q * 255) for q in cols[k]))
        x += 260
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    img.save(ruta)
    return ruta


# ------------------------------------------------------------------ API
def generar(geom_path, urb_path=None, out_dir=None, px=2048, seed=15, veg_plan=None, qa_dir=None, solo_base=False):
    """Genera terreno_mask.png / terreno_base.png / terreno_ao.png en out_dir (+ QA). Devuelve rutas y stats.
    solo_base=True: mismo calculo (determinista) pero solo reescribe terreno_base.png: es la segunda pasada del pipeline
    tras vegetacion.py (la sombra de bosque necesita vegetacion_plan.json, que a su vez lee la mascara)."""
    out_dir = out_dir or DEF_OUT
    G = json.load(open(geom_path, encoding='utf-8'))
    U = None
    if urb_path and os.path.exists(urb_path):
        try:
            U = json.load(open(urb_path, encoding='utf-8'))
        except Exception as e:
            print('AVISO: urbanismo.json ilegible (%s): sin bandas de terrazas' % e)
    res = calcular(G, U, px=px, seed=seed, veg_plan=veg_plan)
    os.makedirs(out_dir, exist_ok=True)
    r_mask, r_ao = os.path.join(out_dir, FICHEROS['mask']), os.path.join(out_dir, FICHEROS['ao'])
    if not solo_base:
        _png(r_mask, res['mask8'][::-1])                                                        # fila 0 del PNG = y maximo
        _png(r_ao, np.clip(np.round(res['ao'] * 255.0), 0, 255).astype(np.uint8)[::-1])
    r_base = _png(os.path.join(out_dir, FICHEROS['base']), _lin_a_srgb8(res['base'])[::-1])
    st = dict(res['stats'])
    st['ficheros'] = {'mask': r_mask, 'base': r_base, 'ao': r_ao, 'geom': os.path.abspath(geom_path),
                      'urb': os.path.abspath(urb_path) if urb_path else None}
    st['bytes'] = {k: os.path.getsize(v) for k, v in (('mask', r_mask), ('base', r_base), ('ao', r_ao))}
    if qa_dir:
        os.makedirs(qa_dir, exist_ok=True)
        # la figura QA se llama igual que la mascara (renders/qa/terreno_mask.png vs texturas/terreno_mask.png, plan 3.4): si
        # alguien pasa --qa == --out (pruebas), la figura NO debe pisar la textura
        nombre_qa = FICHEROS['qa']
        if os.path.normcase(os.path.abspath(qa_dir)) == os.path.normcase(os.path.abspath(out_dir)) and nombre_qa == FICHEROS['mask']:
            nombre_qa = os.path.splitext(FICHEROS['qa'])[0] + '_qa.png'
        st['qa'] = _qa_figura(res, os.path.join(qa_dir, nombre_qa))
        json.dump(st, open(os.path.join(qa_dir, FICHEROS['stats']), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    return {'mask': r_mask, 'base': r_base, 'ao': r_ao, 'stats': st}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--geom', default=os.environ.get('GEOM', DEF_GEOM))
    ap.add_argument('--urb', default=os.environ.get('URBANISMO', DEF_URB))
    ap.add_argument('--out', default=DEF_OUT)
    ap.add_argument('--qa', default=DEF_QA)
    ap.add_argument('--px', type=int, default=2048)
    ap.add_argument('--seed', type=int, default=15)
    ap.add_argument('--veg', default=os.path.join(AQUI, 'vegetacion_plan.json'))
    ap.add_argument('--solo-base', action='store_true', help='solo reescribe terreno_base.png (2a pasada, tras vegetacion.py)')
    A = ap.parse_args(argv)
    veg = A.veg if (A.veg and os.path.exists(A.veg)) else None
    r = generar(A.geom, A.urb, A.out, px=A.px, seed=A.seed, veg_plan=veg, qa_dir=A.qa, solo_base=A.solo_base)
    st = r['stats']
    print('MASCARA_TERRENO: %dx%d | area tierra %s | suma ok %.2f %% | nz<0.7: roca %.1f %% verde %.1f %% | '
          'pend>0.84: roca %.1f %% | borde dirt tierra %.1f %% | AO %.3f | %s | %.1f s' % (
              st['px'], st['px'], json.dumps(st['area_pct_tierra_dominante']), st['suma_ok_pct'],
              st['nz_lt_0_7']['pct_roca_A_gt_0_5'] or 0, st['nz_lt_0_7']['pct_verde_RG_gt_0_5'] or 0,
              st['pend_gt_0_84']['pct_roca_A_gt_0_5'] or 0, st['dirt_borde_lt_8m']['pct_tierra_B_gt_0_5'] or 0,
              st['ao']['media_tierra'], 'veg_plan' if st['veg_plan'] else 'sin veg_plan', st['tiempo_s']))
    print('  ->', r['mask'], '(%d KB)' % (st['bytes']['mask'] // 1024), '|', r['base'], '(%d KB)' % (st['bytes']['base'] // 1024),
          '|', r['ao'], '(%d KB)' % (st['bytes']['ao'] // 1024), '| QA', st.get('qa'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
