# -*- coding: utf-8 -*-
"""vegetacion.py - PLAN DE VEGETACION por mascaras de Porto Corsa (fase visual, bloque 4.1, F1).

Python del SISTEMA (3.12: numpy, scipy, PIL). NO usa bpy. Determinista: dos ejecuciones con los mismos ficheros
de entrada y la misma semilla escriben el MISMO JSON byte a byte (RandomState(seed), sin fechas en el JSON).

Lee   : 03_blender/geometria_3d.json (muestras de pista, rejilla 'terreno' z/mar cell 4 m, mascara_roca, cumbres,
        loews, pit_lane) + 03_blender/urbanismo.json (solares, calles, travesias, rampas, escaleras, enlaces, muros,
        plazas) + 03_blender/urbanismo_spec.json (zonas_excluidas: huella del McLaren).
        OPCIONALES (si existen): renders/qa/huellas.json (huellas 2D del ultimo revisar_urbanismo: edificios no urbanos,
        caminos de malla, muros, props, celdas de las rocas PENON_roca/TUNEL_acantilado, arboles que SE QUEDAN:
        ITAL_/MIRADOR_/VEG_plazoleta), renders/ab/_base_antes/camaras.json (6 camaras de piloto + 5 postales: densidad
        extra en la banda 20-120 m y claro de 40 m en la postal 56), texturas/terreno_mask.png (RGBA 2048 de
        mascara_terreno.py: canal A roca y B tierra como exclusion extra), bancales_spec.json (olivos en bancales).
Escribe: 03_blender/vegetacion_plan.json  {"version", "seed", "cfg", "especies", "masas", "stats", "plantas": [...]}
            plantas[i] = {especie, variante, x, y, z, rot, escala_xy, escala_z, tono, masa_id, lod}
            (x, y, z en metros de mundo Blender; z = terreno bilineal SIN hundir; rot en radianes (rotation_euler.z);
             escala_* relativas a especies[e]['alto_nominal_m']; tono 'a'|'b'|'c' = MAT_VEG_<especie>_a/b/c;
             masa_id -1 = suelto / lineal; lod 0 (< 150 m de la pista), 1 (< 400 m), 2 (resto))
         renders/qa/vegetacion_mapa.png (QA: habitats + exclusiones | plan por especie)
Uso   : python vegetacion.py [--geom g.json] [--urb u.json] [--salida plan.json] [--qa-dir dir] [--seed 42] [--sin-qa]
                             [--huellas h.json] [--camaras c.json] [--mask terreno_mask.png] [--bancales b.json]
                             [--cfg ajustes.json]   (claves de CFG a sobreescribir, p. ej. coberturas o radios)
        QA_DIR=<dir> como variable de entorno equivale a --qa-dir. Salida 1 si la verificacion final encuentra fallos.

HABITATS (plan seccion 7 punto 1): pinar en crestas/collados 60-180 m; encinar en umbrias > 25 grados; olivar 20-90 m
junto al pueblo (bancales); cipreses en caminos/ermita (y acentos del olivar y del casino); palmeras < 20 m junto al mar,
al paseo y en los jardines del casino; adelfas y arbustos con flor en bordes de calle y jardines; matorral > 30 grados y
bajo las masas (sotobosque); nada donde mascara_roca > 0.6 salvo pinos en repisas (pendiente < 0.30).
Masas por semillas (disco de Poisson de radio R_masa entre centros, forma eliptica a lo largo de la curva de nivel con
borde ondulado) + relleno con disco de Poisson por especie (pinar 4.2 m, olivar 8 m, ...) + claros explicitos.
EXCLUSIONES (las de los inspectores): pista w/2 + 12 m (distancia exacta a la polilinea), pit lane w/2 + 8, calles/
travesias/rampas/escaleras/enlaces/caminos + margen por especie (1.0 + 0.7 x radio de copa), edificios/solares/plazas +
margen, muros + 1.2 m, props (pacas, vallas...), rocas (celdas de PENON_roca y TUNEL_acantilado), Loews r 40 m,
zonas_excluidas del spec + margen, mascara_roca > 0.6, mar, los arboles que se quedan (ITAL_/MIRADOR_/VEG_plazoleta) r 3 m.

CONVENCIONES (RONDA15_PLAN.md): muestras cada 2 m con x,y,z,nx,ny,w,sec; n = normal IZQUIERDA; rejilla terreno
x = x0 + i*cell, y = y0 + j*cell, indice j*nx + i; mascara_roca misma rejilla. Colores: SOLO nombres de paleta.json
(paleta.py); el JSON guarda nombres y factores de luminancia, nunca RGB copiados.
"""
import hashlib
import json
import math
import os
import sys
import time

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import paleta  # noqa: E402  (unica fuente de color)

RUTA_GEOM = os.path.join(AQUI, 'geometria_3d.json')
RUTA_URB = os.path.join(AQUI, 'urbanismo.json')
RUTA_SPEC = os.path.join(AQUI, 'urbanismo_spec.json')
RUTA_SALIDA = os.path.join(AQUI, 'vegetacion_plan.json')
RUTA_HUELLAS = os.path.join(AQUI, 'renders', 'qa', 'huellas.json')
RUTA_CAMARAS = os.path.join(AQUI, 'renders', 'ab', '_base_antes', 'camaras.json')
RUTA_MASK = os.path.join(AQUI, 'texturas', 'terreno_mask.png')
RUTA_BANCALES = os.path.join(AQUI, 'bancales_spec.json')
DIR_QA = os.path.join(AQUI, 'renders', 'qa')
SEED = 42
VERSION = 1

# ------------------------------------------------------------------------------------------------ configuracion
# Todo lo ajustable esta aqui (se vuelca en el JSON como 'cfg'). Alturas en m, pendientes en m/m (0.577 = 30 grados).
CFG = {
    'margen_pista': 12.0,          # distancia minima del tronco al BORDE del asfalto (regla de los inspectores)
    'margen_pit': 8.0,             # idem al borde del pit lane
    'margen_loews': 40.0,          # nada del plan a < 40 m del centro de la rotonda Loews (intocable, tiene LOEWS_*)
    'margen_excluida': 4.0,        # zonas_excluidas del spec (McLaren) + margen (si el spec no trae 'margen')
    'margen_muro': 1.2,            # tronco a >= 1.2 m de un muro (asentar.dentro_de_muro)
    'margen_prop': 1.0,            # pacas, vallas, postes...
    'margen_edificio_base': 1.0,   # + 0.7 x radio de copa (despeje_final: copa a 0.7 r, margen 0.3; asentar copa_calzada)
    'roca_max': 0.6,               # nada donde mascara_roca > 0.6 ...
    'repisa_pend_max': 0.30,       # ... salvo pinos en repisas (pendiente < 0.30 con roca > 0.6)
    'camaras_banda': [20.0, 120.0],
    'camaras_factor_r': 0.80,      # radio de Poisson x0.8 (= densidad x1.56) en la banda de las camaras
    'postal_cima_r_libre': 40.0,   # postal 56 (cima): nada a < 40 m de la camara (plan bloque 1.5)
    'lod_d': [150.0, 400.0],
    'tono_prob_cambio': 0.30,      # prob. de que un arbol no lleve el tono base de su masa
    'variante_prob_base': 0.70,    # prob. de la variante dominante de la masa
    'especies': {
        # clase: arbol | mata.  alto: rango exagerado del kit v3 (plan 4.2).  copa: radio de copa (m) a escala 1.
        # r: radio de Poisson (distancia minima entre dos de la misma especie).  paleta: color base (paleta.json).
        # tonos: factor de luminancia por tono (a = base; se aplica con paleta.variante(nombre, factor)).
        'pino': dict(clase='arbol', alto=[16.0, 24.0], alto_nominal=18.0, copa=5.5, r=4.0, paleta='oliva_oscuro',
                     variantes=['parasol', 'parasol', 'carrasco', 'costero'], tonos={'a': 1.0, 'b': 0.85, 'c': 1.15}),
        'encina': dict(clase='arbol', alto=[9.0, 12.0], alto_nominal=10.0, copa=4.5, r=4.6, paleta='oliva_oscuro',
                       variantes=['v0', 'v1'], tonos={'a': 0.9, 'b': 0.78, 'c': 1.05}),
        'olivo': dict(clase='arbol', alto=[5.0, 7.0], alto_nominal=6.0, copa=3.5, r=7.5, paleta='salvia',
                      variantes=['v0', 'v1'], tonos={'a': 1.0, 'b': 0.88, 'c': 1.12}),
        'cipres': dict(clase='arbol', alto=[10.0, 16.0], alto_nominal=12.0, copa=1.6, r=3.5, paleta='oliva_oscuro',
                       variantes=['lapiz', 'lapiz', 'llama'], tonos={'a': 0.8, 'b': 0.7, 'c': 0.92}),
        'palmera': dict(clase='arbol', alto=[12.0, 20.0], alto_nominal=14.0, copa=3.5, r=6.5, paleta='salvia',
                        variantes=['datil', 'washingtonia', 'abanico'], tonos={'a': 1.0, 'b': 0.9, 'c': 1.15}),
        'adelfa': dict(clase='mata', alto=[2.5, 3.5], alto_nominal=3.0, copa=1.6, r=3.0, paleta='salvia',
                       variantes=['rosa', 'blanca', 'roja'], tonos={'a': 1.0, 'b': 0.9, 'c': 1.1}),
        'arbusto': dict(clase='mata', alto=[1.0, 1.8], alto_nominal=1.5, copa=1.0, r=2.6, paleta='salvia',
                        variantes=['romero', 'lavanda', 'retama'], tonos={'a': 1.0, 'b': 0.85, 'c': 1.1}),
        'matorral': dict(clase='mata', alto=[0.8, 1.6], alto_nominal=1.2, copa=1.2, r=2.8, paleta='oliva_oscuro',
                         variantes=['a', 'b'], tonos={'a': 1.0, 'b': 0.85, 'c': 1.2}),
    },
    'zonas': {
        # R_masa: distancia minima entre centros de masa; cobertura: fraccion de la zona cubierta por masas (se para al
        # llegar); claros_por_ha: claros aleatorios (6-14 m) dentro de cada masa; sueltos_por_ha: arboles aislados fuera.
        'pinar': dict(especie='pino', z=[60.0, 180.0], pend_max=0.70, valle_min=-6.0, R_masa=62.0, cobertura=0.46,
                      claros_por_ha=0.6, sueltos_por_ha=0.35, sotobosque_r=3.7),
        'encinar': dict(especie='encina', z=[15.0, 160.0], pend=[0.466, 0.90], umbria_min=0.25, R_masa=52.0,
                        cobertura=0.42, claros_por_ha=0.4, sueltos_por_ha=0.3, sotobosque_r=3.6),
        'olivar': dict(especie='olivo', z=[20.0, 90.0], pend_max=0.45, d_pueblo=[12.0, 90.0], R_masa=58.0,
                       cobertura=0.60, claros_por_ha=0.2, sueltos_por_ha=0.5, cipreses_acento=3),
        'palmeral': dict(especie='palmera', z=[1.5, 20.0], d_mar_max=60.0, pend_max=0.40, R_masa=42.0, cobertura=0.26,
                         claros_por_ha=0.3, sueltos_por_ha=0.4),
        'matorral': dict(especie='matorral', z_min=2.0, pend_min=0.577, pend_max=1.6, R_masa=46.0, cobertura=0.75,
                         claros_por_ha=0.3, sueltos_por_ha=0.0),
        'cipreses': dict(paso=[9.0, 14.0], lado=[4.6, 6.2], ermita_n=8, ermita_d=[5.0, 7.5]),
        'jardin_casino': dict(curvas=[33, 35, 39], semilado=60.0, r=9.0,
                              especies=['adelfa', 'palmera', 'cipres', 'adelfa', 'palmera', 'olivo', 'arbusto']),
        'jardin_hotel': dict(anillo=[10.0, 26.0], r=8.0, especies=['palmera', 'adelfa', 'palmera', 'arbusto']),
        'borde_calle': dict(paso=[6.0, 9.0], lado=[2.3, 3.2], especies=['adelfa', 'arbusto', 'adelfa']),
        'plazas': dict(paso=[4.0, 6.0], fuera=[2.6, 4.0], especies=['adelfa', 'arbusto']),
    },
}

ESPECIES = list(CFG['especies'].keys())
HAB = {'nada': 0, 'pinar': 1, 'encinar': 2, 'olivar': 3, 'palmeral': 4, 'matorral': 5, 'jardin': 7}


def log(*a):
    print('[vegetacion]', *a)
    sys.stdout.flush()


# ------------------------------------------------------------------------------------------------ geometria base
class Geom:
    """Rejilla del terreno + pista en numpy. Mismo indexado que preparar_geometria (j*nx + i)."""

    def __init__(self, g):
        T = g['terreno']
        self.x0, self.y0, self.cell = float(T['x0']), float(T['y0']), float(T['cell'])
        self.nx, self.ny = int(T['nx']), int(T['ny'])
        self.z = np.array(T['z'], dtype=np.float64).reshape(self.ny, self.nx)
        self.mar = np.array(T['mar'], dtype=np.uint8).reshape(self.ny, self.nx).astype(bool)
        mr = g.get('mascara_roca')
        self.roca = (np.array(mr, dtype=np.float64).reshape(self.ny, self.nx) if mr is not None
                     else np.zeros_like(self.z))
        self.cumbres = [tuple(c) for c in g.get('cumbres', [])]
        self.loews = g.get('loews')
        S = g['muestras']
        self.N = len(S)
        self.paso = float(g.get('paso_m', 2.0))
        self.P = np.array([[m['x'], m['y']] for m in S], dtype=np.float64)
        self.Pz = np.array([m['z'] for m in S], dtype=np.float64)
        self.W = np.array([m['w'] for m in S], dtype=np.float64)
        self.sec = [m['sec'] for m in S]
        self.curvas = {int(c['n']): c for c in g.get('curvas', [])}
        self.pit = np.array([[m['x'], m['y']] for m in g.get('pit_lane', [])], dtype=np.float64)
        self.pit_w = np.array([m['w'] for m in g.get('pit_lane', [])], dtype=np.float64)
        self.tree = cKDTree(self.P)
        self.tree_pit = cKDTree(self.pit) if len(self.pit) else None
        self.X = self.x0 + self.cell * np.arange(self.nx)
        self.Y = self.y0 + self.cell * np.arange(self.ny)
        self.x1 = self.x0 + self.cell * (self.nx - 1)
        self.y1 = self.y0 + self.cell * (self.ny - 1)

    # --- muestreo de campos de rejilla en puntos (x, y) ---
    def ij(self, x, y):
        i = np.clip(np.rint((np.asarray(x) - self.x0) / self.cell).astype(int), 0, self.nx - 1)
        j = np.clip(np.rint((np.asarray(y) - self.y0) / self.cell).astype(int), 0, self.ny - 1)
        return i, j

    def muestrear(self, campo, x, y):
        i, j = self.ij(x, y)
        return campo[j, i]

    def z_bilineal(self, x, y):
        fx = (np.asarray(x, dtype=np.float64) - self.x0) / self.cell
        fy = (np.asarray(y, dtype=np.float64) - self.y0) / self.cell
        return ndimage.map_coordinates(self.z, [fy, fx], order=1, mode='nearest')

    # --- distancia EXACTA al eje de la pista (polilinea de muestras) y holgura al borde ---
    def dist_eje(self, x, y, tree=None, P=None, W=None, cerrada=True):
        tree = tree or self.tree
        P = self.P if P is None else P
        W = self.W if W is None else W
        Q = np.column_stack([np.asarray(x, dtype=np.float64).ravel(), np.asarray(y, dtype=np.float64).ravel()])
        _, idx = tree.query(Q)
        n = len(P)
        best = np.full(len(Q), np.inf)
        for di in (-1, 0):
            a = (idx + di) % n if cerrada else np.clip(idx + di, 0, n - 2)
            b = (a + 1) % n if cerrada else a + 1
            A, B = P[a], P[b]
            AB = B - A
            l2 = np.maximum((AB ** 2).sum(1), 1e-9)
            t = np.clip(((Q - A) * AB).sum(1) / l2, 0.0, 1.0)
            C = A + AB * t[:, None]
            d = np.hypot(*(Q - C).T)
            best = np.minimum(best, d)
        return best, W[idx]

    def holgura_pista(self, x, y):
        """distancia al eje - w/2 (positivo = fuera del asfalto)."""
        d, w = self.dist_eje(x, y)
        return d - w / 2.0

    def holgura_pit(self, x, y):
        if self.tree_pit is None:
            return np.full(np.asarray(x).size, np.inf)
        d, w = self.dist_eje(x, y, self.tree_pit, self.pit, self.pit_w, cerrada=False)
        return d - w / 2.0


# ------------------------------------------------------------------------------------------------ carga de entradas
def cargar_json(ruta, obligatorio=True):
    if ruta and os.path.isfile(ruta):
        with open(ruta, encoding='utf-8') as fh:
            return json.load(fh)
    if obligatorio:
        raise SystemExit('falta %s' % ruta)
    return None


def camaras_plan(cams):
    """(piloto+postales [(x, y)], claros [(x, y, r)]) a partir de camaras.json del set BASE."""
    pts, claros = [], []
    if not cams:
        return pts, claros
    for nombre in sorted(cams):
        if nombre.startswith('_'):
            continue
        pref = nombre.split('_')[0]
        if not pref[:2].isdigit():
            continue
        n = int(pref[:2])
        if 49 <= n <= 59:                    # 49-54 piloto, 55-59 (+59b) postales
            loc = cams[nombre]['loc']
            pts.append((float(loc[0]), float(loc[1])))
            if n == 56:
                claros.append((float(loc[0]), float(loc[1]), float(CFG['postal_cima_r_libre'])))
    return pts, claros

# ------------------------------------------------------------------------------------------------ exclusiones (raster 1 m)
class Exclusiones:
    """Rasters de 1 m/px (origen x0, y0 del terreno, fila = y creciente) con las huellas que los inspectores protegen.
    core_urb  : calles/travesias/rampas/escaleras/enlaces/caminos + edificios/solares/plazas + muros + props + rocas
    d_urb     : distancia (m) al core_urb -> por especie se exige d_urb >= margen_edificio_base + 0.7 x copa
    d_calle   : distancia solo a calles y caminos (para 'bordes de calle')
    duro      : exclusion dura independiente de la especie (mar, Loews, zonas excluidas, rocas, arboles que se quedan)
    """

    def __init__(self, G, urb, spec, huellas, cams_claros):
        from PIL import Image, ImageDraw
        self.G = G
        self.W = int(math.ceil(G.cell * (G.nx - 1))) + 1
        self.H = int(math.ceil(G.cell * (G.ny - 1))) + 1
        im_urb = Image.new('L', (self.W, self.H), 0)
        im_calle = Image.new('L', (self.W, self.H), 0)
        im_duro = Image.new('L', (self.W, self.H), 0)
        im_pueblo = Image.new('L', (self.W, self.H), 0)   # SOLO solares/plazas del plan + casas (para d_pueblo del olivar)
        d_urb, d_calle, d_duro = ImageDraw.Draw(im_urb), ImageDraw.Draw(im_calle), ImageDraw.Draw(im_duro)
        d_pueblo = ImageDraw.Draw(im_pueblo)
        self.n = {'calles': 0, 'poligonos': 0, 'muros': 0, 'props': 0, 'rocas_celdas': 0, 'arboles_quedan': 0}

        def px(p):
            return (float(p[0]) - G.x0, float(p[1]) - G.y0)

        def linea(dr, pts, ancho, extra=0.0):
            w = max(1, int(round(ancho + 2 * extra)))
            q = [px(p) for p in pts]
            if len(q) < 2:
                return
            dr.line(q, fill=255, width=w)
            if w >= 4:
                r = w / 2.0
                for (a, b) in q:
                    dr.ellipse([a - r, b - r, a + r, b + r], fill=255)

        def poligono(dr, pts, extra=0.0):
            q = [px(p) for p in pts]
            if len(q) >= 3:
                dr.polygon(q, fill=255)
                if extra > 0:
                    linea(dr, q + [q[0]], 2 * extra)   # engorde aproximado del contorno

        # --- plan urbano (urbanismo.json) ---
        for S in urb.get('sectores', []):
            for c in S.get('calles', []) + S.get('travesias', []) + S.get('enlaces', []):
                linea(d_urb, c['pts'], float(c.get('ancho', 4.5))); linea(d_calle, c['pts'], float(c.get('ancho', 4.5)))
                self.n['calles'] += 1
            for r in S.get('rampas', []):
                linea(d_urb, r['pts'], float(r.get('ancho', 5.5))); linea(d_calle, r['pts'], float(r.get('ancho', 5.5)))
                if r.get('relleno'):
                    poligono(d_urb, r['relleno'])
                self.n['calles'] += 1
            for e in S.get('escaleras', []):
                for t in e.get('tramos', []):
                    linea(d_urb, t['pts'], float(e.get('ancho', 1.6)) + 1.0)
                if e.get('pasarela'):
                    linea(d_urb, e['pasarela'], float(e.get('ancho', 1.6)) + 1.0)
                if e.get('descansillo'):
                    poligono(d_urb, e['descansillo'])
                self.n['calles'] += 1
            for s in S.get('solares', []):
                poligono(d_urb, s['poligono']); poligono(d_pueblo, s['poligono']); self.n['poligonos'] += 1
            for p in S.get('plazas', []):
                poligono(d_urb, p['poligono']); poligono(d_pueblo, p['poligono']); self.n['poligonos'] += 1
            for m in S.get('muros', []):
                linea(d_urb, [(q[0], q[1]) for q in m['pts']], 2 * CFG['margen_muro']); self.n['muros'] += 1
        # --- huellas del ultimo revisar_urbanismo (opcional): edificios no urbanos, caminos de malla, muros, props, rocas ---
        self.senderos, self.caminos, self.ermitas, self.hotel, self.arboles_quedan = [], [], [], None, []
        if huellas:
            for c in huellas.get('casas', []):
                poligono(d_urb, c['esq']); self.n['poligonos'] += 1
                if c['nombre'].startswith(('CASAS_', 'AYTO_', 'CAMPANILE_')):
                    poligono(d_pueblo, c['esq'])
                if c['nombre'].startswith('ITAL_ermita'):
                    self.ermitas.append(c)
                if c['nombre'].startswith('HOTEL_'):
                    self.hotel = c
            for c in huellas.get('calles', []):
                eje = [(p[0], p[1]) for p in c['eje']]
                linea(d_urb, eje, float(c['ancho'])); linea(d_calle, eje, float(c['ancho'])); self.n['calles'] += 1
                if c.get('fuente') == 'malla':
                    (self.senderos if c.get('tipo') == 'tierra' else self.caminos).append(c)
            for m in huellas.get('muros', []):
                linea(d_urb, [(p[0], p[1]) for p in m['eje']], 2 * CFG['margen_muro']); self.n['muros'] += 1
            for p in huellas.get('props', []):
                if p.get('esq'):
                    poligono(d_urb, p['esq'], CFG['margen_prop']); self.n['props'] += 1
            for r in huellas.get('rocas', []):
                cm = float(r.get('celda_m', G.cell))
                for (cx, cy) in r['celdas']:
                    a, b = px((cx - cm / 2 - 1.0, cy - cm / 2 - 1.0)); c2, d2 = px((cx + cm / 2 + 1.0, cy + cm / 2 + 1.0))
                    d_duro.rectangle([a, b, c2, d2], fill=255)
                    self.n['rocas_celdas'] += 1
            for a in huellas.get('arboles', []):
                if a['nombre'].startswith(('ITAL_', 'MIRADOR_', 'VEG_plazoleta', 'VEG_penon')):
                    cx, cy = px((a['x'], a['y']))
                    d_duro.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=255)
                    self.arboles_quedan.append((a['x'], a['y']))
                    self.n['arboles_quedan'] += 1
        # --- duras: zonas excluidas del spec, Loews, claros de camara ---
        for zx in (spec or {}).get('zonas_excluidas', []):
            if len(zx.get('poligono', [])) >= 3:
                poligono(d_duro, zx['poligono'], float(zx.get('margen', CFG['margen_excluida'])))
        if G.loews:
            cx, cy = px((G.loews['x'], G.loews['y'])); r = CFG['margen_loews']
            d_duro.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        for (x, y, r) in cams_claros:
            cx, cy = px((x, y))
            d_duro.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        core_urb = np.array(im_urb, dtype=bool)
        core_calle = np.array(im_calle, dtype=bool)
        self.core_pueblo = np.array(im_pueblo, dtype=bool)
        self.duro = np.array(im_duro, dtype=bool)
        self.d_urb = ndimage.distance_transform_edt(~core_urb).astype(np.float32)
        self.d_calle = ndimage.distance_transform_edt(~core_calle).astype(np.float32)
        self.core_urb = core_urb

    def _idx(self, x, y):
        i = np.clip(np.rint(np.asarray(x, dtype=np.float64) - self.G.x0).astype(int), 0, self.W - 1)
        j = np.clip(np.rint(np.asarray(y, dtype=np.float64) - self.G.y0).astype(int), 0, self.H - 1)
        return i, j

    def d_urbano(self, x, y):
        i, j = self._idx(x, y)
        return self.d_urb[j, i]

    def d_via(self, x, y):
        i, j = self._idx(x, y)
        return self.d_calle[j, i]

    def dura(self, x, y):
        i, j = self._idx(x, y)
        return self.duro[j, i]


# ------------------------------------------------------------------------------------------------ zonas (habitats)
def zonas(geom, exc=None, cams_pts=(), mask_png=None):
    """Campos a 4 m (rejilla del terreno) y mascaras booleanas de habitat.
    Devuelve dict Z con: z, pend, umbria (componente norte de la bajada), roca, mar, d_pista (al borde), d_mar,
    d_pueblo, valle (z - z suavizada 40 m: < 0 en vaguadas, > 0 en crestas), apto (bool: candidato a vegetacion),
    repisa (bool), hab (int8 codigo HAB), cam (bool: banda 20-120 m de las camaras), tierra_tex (bool, opcional)."""
    G = geom if isinstance(geom, Geom) else Geom(geom)
    z, cell = G.z, G.cell
    gy, gx = np.gradient(ndimage.gaussian_filter(z, 1.0), cell)
    pend = np.hypot(gx, gy)
    umbria = -gy / (pend + 1e-9)              # +1 = la ladera baja hacia +y (mira al norte)
    tierra = ~G.mar
    d_mar = ndimage.distance_transform_edt(tierra) * cell
    XX, YY = np.meshgrid(G.X, G.Y)
    holg = G.holgura_pista(XX.ravel(), YY.ravel()).reshape(G.ny, G.nx)
    valle = z - ndimage.gaussian_filter(z, 10.0)
    roca = G.roca
    roca_tex = None
    tierra_tex = np.zeros_like(tierra)
    if mask_png is not None:
        roca_tex, tierra_tex = mask_png
    Z = dict(G=G, z=z, pend=pend, umbria=umbria, roca=roca, mar=G.mar, d_pista=holg, d_mar=d_mar, valle=valle)
    # exclusion dura a 4 m: mar, corredor de la pista, roca (salvo repisas), pit, duras del raster de 1 m
    repisa = (roca > CFG['roca_max']) & (pend < CFG['repisa_pend_max']) & tierra
    apto = tierra & (holg >= CFG['margen_pista'] + 1.0) & ((roca <= CFG['roca_max']) | repisa) & (z > 1.0)
    if roca_tex is not None:
        apto &= (roca_tex <= CFG['roca_max']) | repisa
        apto &= ~tierra_tex
    if G.tree_pit is not None:
        hp = G.holgura_pit(XX.ravel(), YY.ravel()).reshape(G.ny, G.nx)
        apto &= hp >= CFG['margen_pit']
    if exc is not None:
        apto &= ~exc.dura(XX.ravel(), YY.ravel()).reshape(G.ny, G.nx)
        d_pueblo_src = exc.core_pueblo
    else:
        d_pueblo_src = None
    # distancia al pueblo (solares/plazas/casas, NO pacas ni vallas) a 4 m: desde el raster de 1 m remuestreado
    if d_pueblo_src is not None:
        urb4 = d_pueblo_src[::int(cell), ::int(cell)][:G.ny, :G.nx]
        pad = np.zeros_like(tierra); pad[:urb4.shape[0], :urb4.shape[1]] = urb4
        d_pueblo = ndimage.distance_transform_edt(~pad) * cell
    else:
        d_pueblo = np.full_like(z, 1e4)
    Z.update(apto=apto, repisa=repisa, d_pueblo=d_pueblo, tierra_tex=tierra_tex)
    # banda de camaras
    cam = np.zeros_like(tierra)
    if cams_pts:
        dc = np.full_like(z, 1e9)
        for (cx, cy) in cams_pts:
            dc = np.minimum(dc, np.hypot(XX - cx, YY - cy))
        b0, b1 = CFG['camaras_banda']
        cam = (dc >= b0) & (dc <= b1)
    Z['cam'] = cam
    # habitats (prioridad: jardines se tratan aparte; encinar > olivar > palmeral > pinar; matorral donde nada mas)
    cz = CFG['zonas']
    hab = np.zeros(z.shape, dtype=np.int8)
    p = cz['pinar']
    m_pinar = apto & (z >= p['z'][0]) & (z <= p['z'][1]) & (pend <= p['pend_max']) & (valle >= p['valle_min'])
    m_pinar &= (roca <= CFG['roca_max']) | repisa
    e = cz['encinar']
    m_enc = apto & ~repisa & (z >= e['z'][0]) & (z <= e['z'][1]) & (pend >= e['pend'][0]) & (pend <= e['pend'][1]) \
        & (umbria >= e['umbria_min'])
    o = cz['olivar']
    m_oli = apto & ~repisa & (z >= o['z'][0]) & (z <= o['z'][1]) & (pend <= o['pend_max']) \
        & (d_pueblo >= o['d_pueblo'][0]) & (d_pueblo <= o['d_pueblo'][1])
    pa = cz['palmeral']
    m_pal = apto & ~repisa & (z >= pa['z'][0]) & (z <= pa['z'][1]) & (d_mar <= pa['d_mar_max']) & (pend <= pa['pend_max'])
    ma = cz['matorral']
    m_mat = apto & ~repisa & (z >= ma['z_min']) & (pend >= ma['pend_min']) & (pend <= ma['pend_max'])
    hab[m_mat] = HAB['matorral']
    hab[m_pinar] = HAB['pinar']
    hab[m_pal] = HAB['palmeral']
    hab[m_oli] = HAB['olivar']
    hab[m_enc] = HAB['encinar']
    Z['hab'] = hab
    Z['masc'] = {'pinar': hab == HAB['pinar'], 'encinar': hab == HAB['encinar'], 'olivar': hab == HAB['olivar'],
                 'palmeral': hab == HAB['palmeral'], 'matorral': m_mat & (hab != HAB['encinar'])}
    return Z


def leer_mask_png(ruta, G):
    """terreno_mask.png RGBA (R matorral, G hierba seca, B tierra, A roca) -> (roca a 4 m, tierra a 4 m) o None.
    Supone la imagen con v = 0 abajo (fila 0 del PNG = y maximo), UV planar u = (x-x0)/(nx*cell)."""
    if not ruta or not os.path.isfile(ruta):
        return None
    from PIL import Image
    im = Image.open(ruta).convert('RGBA')
    a = np.flipud(np.array(im, dtype=np.float32) / 255.0)
    H, W = a.shape[:2]
    jj = np.clip(np.rint(np.arange(G.ny) / max(G.ny - 1, 1) * (H - 1)).astype(int), 0, H - 1)
    ii = np.clip(np.rint(np.arange(G.nx) / max(G.nx - 1, 1) * (W - 1)).astype(int), 0, W - 1)
    sub = a[jj][:, ii]
    return sub[:, :, 3], sub[:, :, 2] > 0.6

# ------------------------------------------------------------------------------------------------ ocupacion y plan
class Ocupacion:
    """Hash espacial de lo ya plantado. Distancia minima: misma clase -> (r_a + r_b)/2; arbol-mata -> 1.2 m."""
    CELDA = 8.0
    CRUZADA = 1.2

    def __init__(self):
        self.h = {}

    def libre(self, x, y, r, clase):
        cx, cy = int(math.floor(x / self.CELDA)), int(math.floor(y / self.CELDA))
        for a in (cx - 1, cx, cx + 1):
            for b in (cy - 1, cy, cy + 1):
                for (px_, py_, pr, pc) in self.h.get((a, b), ()):
                    dmin = 0.5 * (r + pr) if pc == clase else self.CRUZADA
                    if (px_ - x) ** 2 + (py_ - y) ** 2 < dmin * dmin:
                        return False
        return True

    def ocupar(self, x, y, r, clase):
        self.h.setdefault((int(math.floor(x / self.CELDA)), int(math.floor(y / self.CELDA))), []).append((x, y, r, clase))


class Plan:
    """Acumula plantas y masas; aplica las exclusiones por especie; decide variante/escala/tono/lod."""

    def __init__(self, Z, exc, rng):
        self.Z, self.G, self.exc, self.rng = Z, Z['G'], exc, rng
        self.ocu = Ocupacion()
        self.plantas = []
        self.masas = []
        self.n_masa = 0

    def margen_urb(self, especie):
        return CFG['margen_edificio_base'] + 0.7 * CFG['especies'][especie]['copa']

    def filtrar(self, x, y, especie, zona_mask=None, en_repisa_ok=False):
        """Mascara booleana vectorizada de candidatos admisibles (sin la prueba de ocupacion).
        Se filtra con las coordenadas YA redondeadas a 0.01 m (las que van al JSON): sin casos de borde de celda."""
        x = np.round(np.asarray(x, dtype=np.float64), 2); y = np.round(np.asarray(y, dtype=np.float64), 2)
        G, Z = self.G, self.Z
        ok = (x > G.x0 + 2) & (x < G.x1 - 2) & (y > G.y0 + 2) & (y < G.y1 - 2)
        ok &= G.muestrear(Z['apto'], x, y)
        if zona_mask is not None:
            ok &= G.muestrear(zona_mask, x, y)
        if not en_repisa_ok:
            ok &= ~G.muestrear(Z['repisa'], x, y)
        # pista y pit: distancia exacta a la polilinea
        ok &= G.holgura_pista(x, y) >= CFG['margen_pista']
        if G.tree_pit is not None:
            ok &= G.holgura_pit(x, y) >= CFG['margen_pit']
        if self.exc is not None:
            ok &= ~self.exc.dura(x, y)
            ok &= self.exc.d_urbano(x, y) >= self.margen_urb(especie)
        return ok

    def r_local(self, especie, x, y):
        r = CFG['especies'][especie]['r']
        return r * CFG['camaras_factor_r'] if self.G.muestrear(self.Z['cam'], x, y) else r

    def nueva_masa(self, zona, especie, cx, cy, ra, rb):
        self.n_masa += 1
        m = dict(id=self.n_masa, zona=zona, especie=especie, cx=round(float(cx), 1), cy=round(float(cy), 1),
                 r=round(float(max(ra, rb)), 1), n=0, tono=self.rng.choice(['a', 'b', 'c']),
                 variante=CFG['especies'][especie]['variantes'][self.rng.randint(len(CFG['especies'][especie]['variantes']))])
        self.masas.append(m)
        return m

    def plantar(self, especie, x, y, masa=None, variante=None, tono=None, r_min=0.0, clase=None):
        """Anade una planta (ya filtrada) si el sitio esta libre. Devuelve True si se planta.
        r_min / clase: en jardines todas las especies se espacian a >= r_min como una sola clase."""
        E = CFG['especies'][especie]
        x, y = round(float(x), 2), round(float(y), 2)
        r = max(self.r_local(especie, x, y), r_min)
        clase = clase or E['clase']
        if not self.ocu.libre(x, y, r, clase):
            return False
        self.ocu.ocupar(x, y, r, clase)
        rng = self.rng
        if masa is not None:
            if variante is None:
                variante = masa['variante'] if rng.rand() < CFG['variante_prob_base'] else E['variantes'][rng.randint(len(E['variantes']))]
            if tono is None:
                tono = masa['tono']
                if rng.rand() < CFG['tono_prob_cambio']:
                    tono = 'abc'[(('abc'.index(tono)) + rng.randint(1, 3)) % 3]
            masa['n'] += 1
            mid = masa['id']
        else:
            variante = variante or E['variantes'][rng.randint(len(E['variantes']))]
            tono = tono or 'abc'[rng.randint(3)]
            mid = -1
        alto = rng.uniform(E['alto'][0], E['alto'][1])
        ez = alto / E['alto_nominal']
        exy = ez * rng.uniform(0.85, 1.15)
        d = float(self.G.muestrear(self.Z['d_pista'], x, y))
        lod = 0 if d < CFG['lod_d'][0] else (1 if d < CFG['lod_d'][1] else 2)
        z = float(self.G.z_bilineal([x], [y])[0])
        self.plantas.append(dict(especie=especie, variante=variante, x=round(float(x), 2), y=round(float(y), 2),
                                 z=round(z, 2), rot=round(float(rng.uniform(0, 2 * math.pi)), 3),
                                 escala_xy=round(float(exy), 3), escala_z=round(float(ez), 3), tono=tono,
                                 masa_id=mid, lod=lod))
        return True

    def poisson(self, especie, pts_ok, masa=None, probs=None, r_min=0.0, clase=None):
        """Relleno por dardos: recorre candidatos admisibles en orden y acepta los libres. pts_ok: (n, 2)."""
        n = 0
        for k in range(len(pts_ok)):
            if probs is not None and self.rng.rand() > probs[k]:
                continue
            if self.plantar(especie, float(pts_ok[k, 0]), float(pts_ok[k, 1]), masa, r_min=r_min, clase=clase):
                n += 1
        return n


# ------------------------------------------------------------------------------------------------ masas
def _forma(rng, ra, rb):
    """Borde ondulado: factor radial f(theta) = 1 + sum a_k sin(k theta + fase_k)."""
    a = (rng.uniform(0.10, 0.28), rng.uniform(0.06, 0.18), rng.uniform(0.03, 0.10))
    f = (rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi))

    def rho_max(theta):
        return 1.0 + a[0] * np.sin(2 * theta + f[0]) + a[1] * np.sin(3 * theta + f[1]) + a[2] * np.sin(5 * theta + f[2])
    return rho_max


def masas(zona, especie, radio_poisson, claros, plan, nombre='masa', cz=None, cobertura_raster=None):
    """Masas de una especie dentro de la mascara `zona` (bool a 4 m): centros por disco de Poisson (R_masa), forma
    eliptica a lo largo de la curva de nivel con borde ondulado, relleno por disco de Poisson `radio_poisson`
    (x0.8 en la banda de las camaras), claros aleatorios + `claros` explicitos [(x, y, r)]. Para al cubrir cz['cobertura']
    de la zona. Devuelve (n_plantas, n_masas). Pinta las huellas en cobertura_raster (uint8 a 4 m) si se pasa."""
    Z, G, rng = plan.Z, plan.G, plan.rng
    cz = cz or CFG['zonas'][nombre]
    E = CFG['especies'][especie]
    cells = np.argwhere(zona)
    if len(cells) == 0:
        return 0, 0
    area_zona = len(cells) * G.cell ** 2
    orden = rng.permutation(len(cells))
    R_masa = float(cz['R_masa'])
    centros = []
    cub = np.zeros(zona.shape, dtype=bool)
    objetivo = float(cz['cobertura']) * len(cells)
    n_pl = n_ma = 0
    gy, gx = np.gradient(ndimage.gaussian_filter(G.z, 2.0), G.cell)
    for k in orden:
        if cub.sum() >= objetivo:
            break
        j, i = cells[k]
        cx = G.X[i] + rng.uniform(-G.cell / 2, G.cell / 2); cy = G.Y[j] + rng.uniform(-G.cell / 2, G.cell / 2)
        if any((cx - a) ** 2 + (cy - b) ** 2 < R_masa * R_masa for (a, b) in centros):
            continue
        centros.append((cx, cy))
        # ejes: a lo largo de la curva de nivel (perpendicular al gradiente) la masa es mas larga
        g = (gx[j, i], gy[j, i]); gn = math.hypot(*g)
        if gn > 0.05:
            ub = (g[0] / gn, g[1] / gn); ua = (-ub[1], ub[0])
        else:
            th = rng.uniform(0, math.pi); ua = (math.cos(th), math.sin(th)); ub = (-ua[1], ua[0])
        ra = R_masa * rng.uniform(0.55, 0.85)
        rb = ra * rng.uniform(0.55, 0.9)
        rho_max = _forma(rng, ra, rb)
        masa = plan.nueva_masa(nombre, especie, cx, cy, ra, rb)
        # claros
        area_m = math.pi * ra * rb
        cl = [(cx + rng.uniform(-ra, ra), cy + rng.uniform(-rb, rb), rng.uniform(6.0, 14.0))
              for _ in range(int(round(area_m / 1e4 * cz.get('claros_por_ha', 0.0))))] + list(claros)
        # candidatos (dardos) en la caja de la masa
        rmax = max(ra, rb) * 1.3
        r_eff = radio_poisson * (CFG['camaras_factor_r'] if G.muestrear(Z['cam'], cx, cy) else 1.0)
        n_cand = int(6.0 * (2 * rmax) ** 2 / (r_eff * r_eff))
        px_ = cx + rng.uniform(-rmax, rmax, n_cand); py_ = cy + rng.uniform(-rmax, rmax, n_cand)
        u = ((px_ - cx) * ua[0] + (py_ - cy) * ua[1]) / ra
        v = ((px_ - cx) * ub[0] + (py_ - cy) * ub[1]) / rb
        rho = np.hypot(u, v); th = np.arctan2(v, u)
        fm = rho_max(th)
        dentro = rho < fm
        # borde deshilachado: menos probabilidad de aceptacion en el 30 % exterior
        prob = np.clip((fm - rho) / (0.30 * fm), 0.25, 1.0)
        for (qx, qy, qr) in cl:
            dentro &= (px_ - qx) ** 2 + (py_ - qy) ** 2 > qr * qr
        ok = dentro & plan.filtrar(px_, py_, especie, zona, en_repisa_ok=(especie == 'pino'))
        pts = np.column_stack([px_[ok], py_[ok]])
        n = plan.poisson(especie, pts, masa, probs=prob[ok])
        n_pl += n
        n_ma += 1
        # huella (a 4 m) para la cobertura y el sotobosque
        i0, i1 = max(0, int((cx - rmax - G.x0) / G.cell)), min(G.nx - 1, int((cx + rmax - G.x0) / G.cell) + 1)
        j0, j1 = max(0, int((cy - rmax - G.y0) / G.cell)), min(G.ny - 1, int((cy + rmax - G.y0) / G.cell) + 1)
        if i1 > i0 and j1 > j0:
            XX, YY = np.meshgrid(G.X[i0:i1 + 1], G.Y[j0:j1 + 1])
            uu = ((XX - cx) * ua[0] + (YY - cy) * ua[1]) / ra; vv = ((XX - cx) * ub[0] + (YY - cy) * ub[1]) / rb
            hu = np.hypot(uu, vv) < rho_max(np.arctan2(vv, uu))
            cub[j0:j1 + 1, i0:i1 + 1] |= hu & zona[j0:j1 + 1, i0:i1 + 1]
            if cobertura_raster is not None:
                cobertura_raster[j0:j1 + 1, i0:i1 + 1] = np.where(hu & zona[j0:j1 + 1, i0:i1 + 1], masa['id'] % 250 + 1,
                                                                  cobertura_raster[j0:j1 + 1, i0:i1 + 1])
    # sueltos fuera de las masas
    n_su = int(round(area_zona / 1e4 * cz.get('sueltos_por_ha', 0.0)))
    if n_su > 0:
        libres = np.argwhere(zona & ~cub)
        if len(libres):
            sel = libres[rng.randint(len(libres), size=n_su * 3)]
            px_ = G.X[sel[:, 1]] + rng.uniform(-G.cell / 2, G.cell / 2, len(sel))
            py_ = G.Y[sel[:, 0]] + rng.uniform(-G.cell / 2, G.cell / 2, len(sel))
            ok = plan.filtrar(px_, py_, especie, zona, en_repisa_ok=(especie == 'pino'))
            pts = np.column_stack([px_[ok], py_[ok]])[:n_su]
            # un suelto necesita 2.5 radios de aire: radio temporal mayor
            r0 = CFG['especies'][especie]['r']
            CFG['especies'][especie]['r'] = r0 * 2.5
            n_pl += plan.poisson(especie, pts, None)
            CFG['especies'][especie]['r'] = r0
    log('  %-9s %-8s %5d masas %6d plantas  cobertura %.0f %% de %.1f ha' % (nombre, especie, n_ma, n_pl,
        100.0 * cub.sum() / max(1, len(cells)), area_zona / 1e4))
    return n_pl, n_ma

# ------------------------------------------------------------------------------------------------ lineales y jardines
def _puntos_a_lo_largo(pts, paso_rng, lados, rng):
    """Puntos a ambos lados de una polilinea cada paso (aleatorio en paso_rng) a un offset aleatorio en `lados`."""
    out = []
    P = np.array([(p[0], p[1]) for p in pts], dtype=np.float64)
    if len(P) < 2:
        return out
    seg = np.hypot(*np.diff(P, axis=0).T)
    acum = np.concatenate([[0.0], np.cumsum(seg)])
    s = rng.uniform(0, paso_rng[1])
    lado = 1
    while s < acum[-1]:
        k = int(np.searchsorted(acum, s, side='right') - 1)
        k = min(max(k, 0), len(P) - 2)
        t = (s - acum[k]) / max(seg[k], 1e-9)
        p = P[k] + (P[k + 1] - P[k]) * t
        d = (P[k + 1] - P[k]) / max(seg[k], 1e-9)
        n = (-d[1], d[0])
        off = rng.uniform(lados[0], lados[1]) * lado
        out.append((p[0] + n[0] * off, p[1] + n[1] * off))
        lado = -lado
        s += rng.uniform(paso_rng[0], paso_rng[1])
    return out


def _anillo_rect(c, dist_rng, paso_rng, rng):
    """Puntos alrededor de un rectangulo de huellas.json (cx, cy, ux, uy, vx, vy, hu, hv) a `dist` del borde."""
    out = []
    hu, hv = c['hu'] / 2.0, c['hv'] / 2.0
    per = 4 * (hu + hv)
    s = rng.uniform(0, paso_rng[1])
    while s < per:
        d = rng.uniform(dist_rng[0], dist_rng[1])
        t = s
        if t < 2 * hu:
            lu, lv = -hu + t, -(hv + d)
        elif t < 2 * hu + 2 * hv:
            lu, lv = hu + d, -hv + (t - 2 * hu)
        elif t < 4 * hu + 2 * hv:
            lu, lv = hu - (t - 2 * hu - 2 * hv), hv + d
        else:
            lu, lv = -(hu + d), hv - (t - 4 * hu - 2 * hv)
        out.append((c['cx'] + c['ux'] * lu + c['vx'] * lv, c['cy'] + c['uy'] * lu + c['vy'] * lv))
        s += rng.uniform(paso_rng[0], paso_rng[1])
    return out


def _plantar_lista(plan, especies, pts, masa=None, r_min=0.0, clase=None):
    n = 0
    if not pts:
        return 0
    P = np.array(pts, dtype=np.float64)
    for k in range(len(P)):
        e = especies[k % len(especies)]
        if plan.filtrar(P[k:k + 1, 0], P[k:k + 1, 1], e)[0] and plan.plantar(e, float(P[k, 0]), float(P[k, 1]), masa,
                                                                            r_min=r_min, clase=clase):
            n += 1
    return n


def cipreses(plan, exc):
    """Cipreses a lo largo de los senderos (CAMINO_tierra), alrededor de las ermitas y en los caminos del casino/puerto."""
    cz = CFG['zonas']['cipreses']
    rng = plan.rng
    n = 0
    if exc is None:
        return 0
    for c in sorted(exc.senderos, key=lambda c: c['nombre']):
        pts = _puntos_a_lo_largo(c['eje'], cz['paso'], cz['lado'], rng)
        n += _plantar_lista(plan, ['cipres'], pts)
    for c in sorted(exc.caminos, key=lambda c: c['nombre']):
        if c.get('tipo') in ('asfalto', 'adoquin'):
            pts = _puntos_a_lo_largo(c['eje'], [cz['paso'][0] + 4, cz['paso'][1] + 6], [cz['lado'][0] + 0.6, cz['lado'][1] + 1.0], rng)
            n += _plantar_lista(plan, ['cipres', 'palmera', 'cipres'], pts)
    for e in sorted(exc.ermitas, key=lambda c: c['nombre']):
        pts = _anillo_rect(e, cz['ermita_d'], [5.0, 7.0], rng)
        n += _plantar_lista(plan, ['cipres'], pts[:cz['ermita_n'] * 2])
    log('  cipreses lineales (senderos/caminos/ermitas): %d' % n)
    return n


def bordes_de_calle(plan, urb, exc):
    """Adelfas y arbustos con flor a 2.3-3.2 m del borde de calles/travesias del plan y de los caminos de malla."""
    cz = CFG['zonas']['borde_calle']
    rng = plan.rng
    n = 0
    vias = []
    for S in urb.get('sectores', []):
        for c in S.get('calles', []) + S.get('travesias', []):
            vias.append((c['id'], c['pts'], float(c.get('ancho', 4.5))))
    if exc is not None:
        for c in exc.caminos:
            vias.append((c['nombre'], c['eje'], float(c['ancho'])))
    for (_id, pts, ancho) in sorted(vias, key=lambda v: v[0]):
        q = _puntos_a_lo_largo(pts, cz['paso'], [ancho / 2 + cz['lado'][0], ancho / 2 + cz['lado'][1]], rng)
        n += _plantar_lista(plan, cz['especies'], q)
    log('  bordes de calle (adelfa/arbusto): %d' % n)
    return n


def plazas(plan, urb):
    """Anillo de adelfas/arbustos fuera de las plazas y plazoletas (despeje_final quita lo de dentro del poligono)."""
    cz = CFG['zonas']['plazas']
    rng = plan.rng
    n = 0
    polys = []
    for S in urb.get('sectores', []):
        polys += [(p['id'], p['poligono']) for p in S.get('plazas', [])]
        polys += [(s['id'], s['poligono']) for s in S.get('solares', []) if s.get('tipo') == 'plazoleta']
    for (_id, poly) in sorted(polys, key=lambda p: p[0]):
        P = np.array(poly, dtype=np.float64)
        c = P.mean(0)
        pts = []
        for k in range(len(P)):
            a, b = P[k], P[(k + 1) % len(P)]
            L = max(np.hypot(*(b - a)), 1e-6)
            nrm = np.array([(b - a)[1], -(b - a)[0]]) / L
            if np.dot(nrm, a - c) < 0:
                nrm = -nrm
            s = rng.uniform(0, cz['paso'][1])
            while s < L:
                p = a + (b - a) * (s / L) + nrm * rng.uniform(cz['fuera'][0], cz['fuera'][1])
                pts.append((p[0], p[1]))
                s += rng.uniform(cz['paso'][0], cz['paso'][1])
        n += _plantar_lista(plan, cz['especies'], pts)
    log('  anillos de plazas/plazoletas: %d' % n)
    return n


def jardines(plan, exc):
    """Jardines del casino (interior del lazo 31-41) y del hotel: adelfas, palmeras, cipreses, olivos, arbustos."""
    G, rng = plan.G, plan.rng
    n = 0
    cz = CFG['zonas']['jardin_casino']
    cs = [G.curvas[c] for c in cz['curvas'] if c in G.curvas]
    if cs:
        gx = sum(c['x'] for c in cs) / len(cs); gy = sum(c['y'] for c in cs) / len(cs)
        masa = plan.nueva_masa('jardin_casino', 'adelfa', gx, gy, cz['semilado'], cz['semilado'])
        m_cand = int(8 * (2 * cz['semilado']) ** 2 / cz['r'] ** 2)
        px_ = gx + rng.uniform(-cz['semilado'], cz['semilado'], m_cand)
        py_ = gy + rng.uniform(-cz['semilado'], cz['semilado'], m_cand)
        for k, e in enumerate(cz['especies']):
            sel = slice(k, None, len(cz['especies']))
            ok = plan.filtrar(px_[sel], py_[sel], e)
            pts = np.column_stack([px_[sel][ok], py_[sel][ok]])
            n += plan.poisson(e, pts, masa, r_min=cz['r'], clase='jardin')
        masa['especie'] = 'mixto'
    if exc is not None and exc.hotel is not None:
        cz = CFG['zonas']['jardin_hotel']
        h = exc.hotel
        masa = plan.nueva_masa('jardin_hotel', 'palmera', h['cx'], h['cy'], h['hu'] / 2 + cz['anillo'][1], h['hv'] / 2 + cz['anillo'][1])
        pts = []
        for d in np.arange(cz['anillo'][0], cz['anillo'][1], 5.0):
            pts += _anillo_rect(h, [d, d + 4.0], [cz['r'], cz['r'] + 3], rng)
        rng.shuffle(pts)
        n += _plantar_lista(plan, cz['especies'], pts, masa, r_min=cz['r'], clase='jardin')
        masa['especie'] = 'mixto'
    log('  jardines (casino/hotel): %d' % n)
    return n


def sotobosque(plan, cobertura, especie_base, r):
    """Matorral bajo las masas de pinar/encinar (sombra de bosque + 'monte' en vez de 'arboles puestos')."""
    G, rng = plan.G, plan.rng
    cells = np.argwhere(cobertura > 0)
    if len(cells) == 0:
        return 0
    n_cand = int(len(cells) * G.cell ** 2 * 3.0 / (r * r))
    sel = cells[rng.randint(len(cells), size=n_cand)]
    px_ = G.X[sel[:, 1]] + rng.uniform(-G.cell / 2, G.cell / 2, n_cand)
    py_ = G.Y[sel[:, 0]] + rng.uniform(-G.cell / 2, G.cell / 2, n_cand)
    ok = plan.filtrar(px_, py_, 'matorral')
    pts = np.column_stack([px_[ok], py_[ok]])
    r0 = CFG['especies']['matorral']['r']
    CFG['especies']['matorral']['r'] = r
    masa = plan.nueva_masa('sotobosque_' + especie_base, 'matorral', 0.0, 0.0, 0.0, 0.0)
    n = plan.poisson('matorral', pts, masa)
    CFG['especies']['matorral']['r'] = r0
    log('  sotobosque bajo %s: %d matas (r %.1f)' % (especie_base, n, r))
    return n


def bancales(plan, spec_b):
    """Olivos en bancales (bancales_spec.json, formato supuesto: {'bancales': [{'lineas': [[[x,y],...],...]} | {'poligono': [...]}]})."""
    if not spec_b:
        return 0
    rng = plan.rng
    n = 0
    for b in spec_b.get('bancales', []):
        lineas = b.get('lineas') or ([b['poligono']] if b.get('poligono') else [])
        for ln in lineas:
            pts = _puntos_a_lo_largo(ln, [7.0, 9.0], [1.5, 2.5], rng)
            n += _plantar_lista(plan, ['olivo'], pts)
    log('  olivos en bancales: %d' % n)
    return n

# ------------------------------------------------------------------------------------------------ planificar
def planificar(geom, urb, seed=SEED, cfg=None, spec=None, huellas=None, camaras=None, mask_png=None, bancales_spec=None):
    """Plan completo. geom/urb: dicts ya cargados. Devuelve el dict que se escribe en vegetacion_plan.json."""
    t0 = time.time()
    if cfg:
        _actualizar(CFG, cfg)
    rng = np.random.RandomState(int(seed))
    G = Geom(geom)
    cams_pts, cams_claros = camaras_plan(camaras)
    exc = Exclusiones(G, urb, spec, huellas, cams_claros)
    log('exclusiones: %s  (raster %dx%d a 1 m, %.1f s)' % (exc.n, exc.W, exc.H, time.time() - t0))
    Z = zonas(G, exc, cams_pts, leer_mask_png(mask_png, G) if isinstance(mask_png, str) else mask_png)
    ha = {k: float(v.sum()) * G.cell ** 2 / 1e4 for k, v in Z['masc'].items()}
    log('habitats (ha): ' + ', '.join('%s %.1f' % kv for kv in sorted(ha.items())) + '  apto %.1f ha' % (Z['apto'].sum() * 16 / 1e4))
    plan = Plan(Z, exc, rng)
    cob_pinar = np.zeros(G.z.shape, dtype=np.uint8)
    cob_enc = np.zeros(G.z.shape, dtype=np.uint8)
    cob_oli = np.zeros(G.z.shape, dtype=np.uint8)
    res = {}
    # orden fijo: primero lo lineal y los jardines (sitios escasos), luego las masas, al final matorral y sotobosque
    res['cipreses'] = cipreses(plan, exc)
    res['jardines'] = jardines(plan, exc)
    res['plazas'] = plazas(plan, urb)
    res['bordes_calle'] = bordes_de_calle(plan, urb, exc)
    res['bancales'] = bancales(plan, bancales_spec)
    cz = CFG['zonas']
    res['olivar'] = masas(Z['masc']['olivar'], 'olivo', CFG['especies']['olivo']['r'], cams_claros, plan, 'olivar',
                          cobertura_raster=cob_oli)
    res['palmeral'] = masas(Z['masc']['palmeral'], 'palmera', CFG['especies']['palmera']['r'], cams_claros, plan, 'palmeral')
    res['encinar'] = masas(Z['masc']['encinar'], 'encina', CFG['especies']['encina']['r'], cams_claros, plan, 'encinar',
                           cobertura_raster=cob_enc)
    res['pinar'] = masas(Z['masc']['pinar'], 'pino', CFG['especies']['pino']['r'], cams_claros, plan, 'pinar',
                         cobertura_raster=cob_pinar)
    # acentos de cipreses en el borde de las masas de olivar (Riviera)
    n_ac = 0
    for m in [m for m in plan.masas if m['zona'] == 'olivar' and m['n'] > 0]:
        for _ in range(cz['olivar'].get('cipreses_acento', 0)):
            th = rng.uniform(0, 2 * math.pi)
            x = m['cx'] + math.cos(th) * m['r'] * 0.9; y = m['cy'] + math.sin(th) * m['r'] * 0.9
            if plan.filtrar([x], [y], 'cipres', Z['masc']['olivar'])[0] and plan.plantar('cipres', x, y, m):
                n_ac += 1
    res['cipreses_olivar'] = n_ac
    res['matorral'] = masas(Z['masc']['matorral'], 'matorral', CFG['especies']['matorral']['r'], cams_claros, plan, 'matorral')
    res['sotobosque_pinar'] = sotobosque(plan, cob_pinar, 'pinar', cz['pinar']['sotobosque_r'])
    res['sotobosque_encinar'] = sotobosque(plan, cob_enc, 'encinar', cz['encinar']['sotobosque_r'])
    stats = estadisticas(plan, Z, res)
    plan.tiempo_s = round(time.time() - t0, 1)      # NUNCA en el JSON (rompia el determinismo byte a byte): solo log y mapa
    especies = {}
    for e, E in CFG['especies'].items():
        especies[e] = dict(clase=E['clase'], alto_m=E['alto'], alto_nominal_m=E['alto_nominal'], radio_copa_m=E['copa'],
                           radio_poisson_m=E['r'], paleta=E['paleta'], tonos=E['tonos'], variantes=sorted(set(E['variantes'])),
                           paleta_rgb_lineal={t: [round(c, 4) for c in paleta.variante(E['paleta'], f)] for t, f in E['tonos'].items()})
    datos = dict(version=VERSION, seed=int(seed), generador='03_blender/vegetacion.py',
                 notas=['x, y, z metros de mundo Blender; z = terreno bilineal (cell 4 m) SIN hundimiento (asentar aplica el suyo)',
                        'rot = rotation_euler.z en radianes; escala_xy / escala_z relativas a especies[e].alto_nominal_m',
                        'tono a|b|c = MAT_VEG_<especie>_a/b/c; factor de luminancia en especies[e].tonos sobre paleta.json (paleta_rgb_lineal se recalcula al ejecutar)',
                        'masa_id = indice en masas (-1 = suelto o lineal); lod 0 < %.0f m de la pista, 1 < %.0f m, 2 resto' % tuple(CFG['lod_d']),
                        'AC (trees.txt): pos = (x, z, -y); angle = grados(rot)'],
                 cfg=CFG, especies=especies, masas=plan.masas, stats=stats, plantas=plan.plantas)
    return datos, plan, Z, exc


def _actualizar(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _actualizar(base[k], v)
        else:
            base[k] = v


def estadisticas(plan, Z, res):
    P = plan.plantas
    G = plan.G
    por_esp = {}
    for p in P:
        por_esp[p['especie']] = por_esp.get(p['especie'], 0) + 1
    arb = [p for p in P if CFG['especies'][p['especie']]['clase'] == 'arbol']
    mat = [p for p in P if CFG['especies'][p['especie']]['clase'] == 'mata']
    st = dict(total=len(P), arboles=len(arb), matas=len(mat), por_especie=dict(sorted(por_esp.items())),
              por_zona={k: (v if isinstance(v, int) else {'plantas': v[0], 'masas': v[1]}) for k, v in res.items()},
              masas=len([m for m in plan.masas if m['n'] > 0]))
    if arb:
        A = np.array([(p['x'], p['y']) for p in arb])
        d, _ = cKDTree(A).query(A, k=2)
        st['arboles_con_vecino_lt_6m_pct'] = round(100.0 * float((d[:, 1] < 6.0).mean()), 1)
        zs = np.array([p['z'] for p in arb])
        st['arboles_z_gt_80_pct'] = round(100.0 * float((zs > 80.0).mean()), 1)
        st['arboles_z_gt_80'] = int((zs > 80.0).sum())
        st['z_arboles_min_max'] = [round(float(zs.min()), 1), round(float(zs.max()), 1)]
    if P:
        X = np.array([(p['x'], p['y']) for p in P])
        holg = G.holgura_pista(X[:, 0], X[:, 1])
        st['holgura_pista_min_m'] = round(float(holg.min()), 2)
        st['holgura_pista_lt_12_n'] = int((holg < CFG['margen_pista'] - 1e-6).sum())
        if G.tree_pit is not None:
            st['holgura_pit_min_m'] = round(float(G.holgura_pit(X[:, 0], X[:, 1]).min()), 2)
        if plan.exc is not None:
            du = plan.exc.d_urbano(X[:, 0], X[:, 1])
            st['d_urbano_min_m'] = round(float(du.min()), 2)
            st['dentro_core_urbano_n'] = int((du <= 0.0).sum())
            st['en_exclusion_dura_n'] = int(plan.exc.dura(X[:, 0], X[:, 1]).sum())
        st['roca_gt_0_6_no_pino_n'] = int(sum(1 for p in P if p['especie'] != 'pino'
                                              and G.muestrear(G.roca, p['x'], p['y']) > CFG['roca_max']))
        st['en_mar_n'] = int(sum(1 for p in P if G.muestrear(G.mar, p['x'], p['y'])))
        st['lod'] = {k: int(sum(1 for p in P if p['lod'] == k)) for k in (0, 1, 2)}
        st['en_banda_camaras_pct'] = round(100.0 * float(G.muestrear(Z['cam'], X[:, 0], X[:, 1]).mean()), 1)
    return st


def verificar(datos, geom, urb, huellas=None):
    """Comprobacion independiente del plan escrito (lo que pedira la puerta): exclusiones de pista y de solares."""
    G = Geom(geom)
    P = datos['plantas'] if isinstance(datos, dict) else datos
    X = np.array([(p['x'], p['y']) for p in P], dtype=np.float64)
    holg = G.holgura_pista(X[:, 0], X[:, 1])
    fallos = {'pista_lt_w2_mas_12': int((holg < CFG['margen_pista'] - 1e-6).sum())}
    # dentro de un solar / edificio (prueba punto-en-poligono por producto vectorial, rectangulos)
    polys = []
    for S in urb.get('sectores', []):
        polys += [np.array(s['poligono'], dtype=np.float64) for s in S.get('solares', [])]
        polys += [np.array(p['poligono'], dtype=np.float64) for p in S.get('plazas', [])]
    if huellas:
        polys += [np.array(c['esq'], dtype=np.float64) for c in huellas.get('casas', [])]
    dentro = 0
    if polys:
        tree = cKDTree(X)
        for Q in polys:
            c = Q.mean(0); r = float(np.hypot(*(Q - c).T).max()) + 0.1
            for k in tree.query_ball_point(c, r):
                px_, py_ = X[k]
                sgn = 0
                ins = True
                for a in range(len(Q)):
                    b = (a + 1) % len(Q)
                    cr = (Q[b, 0] - Q[a, 0]) * (py_ - Q[a, 1]) - (Q[b, 1] - Q[a, 1]) * (px_ - Q[a, 0])
                    if sgn == 0 and abs(cr) > 1e-9:
                        sgn = 1 if cr > 0 else -1
                    elif cr * sgn < 0:
                        ins = False
                        break
                dentro += ins
    fallos['dentro_de_solar_o_edificio'] = int(dentro)
    fallos['en_mar'] = int(G.muestrear(G.mar, X[:, 0], X[:, 1]).sum())
    return fallos


# ------------------------------------------------------------------------------------------------ mapa QA (PIL)
COLORES_QA = {   # colores de DIAGNOSTICO del mapa (no son colores de la escena; los de escena salen de paleta.json)
    'pino': (20, 90, 40), 'encina': (0, 50, 25), 'olivo': (150, 170, 110), 'cipres': (10, 30, 20),
    'palmera': (220, 200, 40), 'adelfa': (235, 90, 160), 'arbusto': (150, 80, 220), 'matorral': (160, 130, 70),
}
COLORES_HAB = {1: (120, 170, 120), 2: (60, 110, 80), 3: (190, 200, 150), 4: (240, 225, 140), 5: (200, 180, 140)}


def mapa_qa(datos, Z, exc, ruta, escala_px_m=0.5):
    from PIL import Image, ImageDraw, ImageFont
    G = Z['G']
    W = int(G.cell * (G.nx - 1) * escala_px_m); H = int(G.cell * (G.ny - 1) * escala_px_m)

    def fondo():
        zs = ndimage.gaussian_filter(G.z, 1.0)
        gy, gx = np.gradient(zs, G.cell)
        sh = np.clip(0.55 + 0.45 * (-gx * 0.6 + gy * 0.4 + 0.5) / 0.9, 0.3, 1.0)
        base = np.zeros(G.z.shape + (3,), dtype=np.float32)
        hs = np.array(paleta.srgb8('hierba_seca'), dtype=np.float32)
        base[:] = hs * sh[..., None] * 1.05
        mar_c = np.array(paleta.srgb8('mar_orilla'), dtype=np.float32) * 0.9
        base[G.mar] = mar_c
        base[(G.roca > CFG['roca_max']) & ~G.mar] = np.array(paleta.srgb8('caliza_gris_calido'), dtype=np.float32) * sh[(G.roca > CFG['roca_max']) & ~G.mar][:, None]
        im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
        return im

    def px(x, y):
        return ((x - G.x0) * escala_px_m, (y - G.y0) * escala_px_m)

    def pista(dr):
        pts = [px(x, y) for (x, y) in G.P] + [px(G.P[0, 0], G.P[0, 1])]
        dr.line(pts, fill=(40, 40, 40), width=max(2, int(14 * escala_px_m)))

    # panel 1: habitats + exclusiones
    im1 = fondo()
    hab = Z['hab']
    ov = np.zeros((G.ny, G.nx, 4), dtype=np.uint8)
    for code, col in COLORES_HAB.items():
        ov[hab == code] = col + (170,)
    ov[~Z['apto'] & ~G.mar] = (220, 60, 60, 90)
    ovi = Image.fromarray(ov).resize((W, H), Image.NEAREST)
    im1 = Image.alpha_composite(im1.convert('RGBA'), ovi).convert('RGB')
    d1 = ImageDraw.Draw(im1)
    if exc is not None:
        core = Image.fromarray((exc.core_urb.astype(np.uint8) * 255)).resize((W, H), Image.NEAREST)
        im1.paste((70, 70, 70), (0, 0), core)
    pista(d1)
    # panel 2: plan por especie
    im2 = fondo()
    d2 = ImageDraw.Draw(im2)
    if exc is not None:
        core = Image.fromarray((exc.core_urb.astype(np.uint8) * 255)).resize((W, H), Image.NEAREST)
        im2.paste((90, 90, 90), (0, 0), core)
    pista(d2)
    r_pt = {'arbol': max(1.0, 1.6 * escala_px_m * 1.6), 'mata': max(0.6, 1.1 * escala_px_m)}
    for p in sorted(datos['plantas'], key=lambda p: CFG['especies'][p['especie']]['clase'] != 'mata'):   # matas debajo
        c = COLORES_QA[p['especie']]; r = r_pt[CFG['especies'][p['especie']]['clase']]
        a, b = px(p['x'], p['y'])
        d2.ellipse([a - r, b - r, a + r, b + r], fill=c)
    for m in datos['masas']:
        if m['n'] > 0 and m['r'] > 0:
            a, b = px(m['cx'], m['cy']); r = m['r'] * escala_px_m
            d2.ellipse([a - r, b - r, a + r, b + r], outline=(255, 255, 255), width=1)
    # camaras
    cams = datos.get('_camaras', [])
    for (cx, cy) in cams:
        a, b = px(cx, cy)
        for d in (d1, d2):
            d.polygon([(a, b - 6), (a - 5, b + 4), (a + 5, b + 4)], fill=(255, 40, 40), outline=(0, 0, 0))
    # montaje (norte arriba) + leyenda
    im1 = im1.transpose(Image.FLIP_TOP_BOTTOM); im2 = im2.transpose(Image.FLIP_TOP_BOTTOM)
    ley = 150
    out = Image.new('RGB', (W * 2 + 30, H + ley), (245, 245, 240))
    out.paste(im1, (10, 10)); out.paste(im2, (W + 20, 10))
    dr = ImageDraw.Draw(out)
    try:
        f = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 14); fb = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 16)
    except Exception:
        f = fb = ImageFont.load_default()
    st = datos['stats']
    dr.text((12, H + 16), 'HABITATS (4 m): pinar / encinar / olivar / palmeral / matorral; rojo = no apto (mar, pista+12, roca>0.6, duras); gris = calles/edificios/muros/props', fill=(20, 20, 20), font=fb)
    y = H + 40
    for k, (code, col) in enumerate(sorted(COLORES_HAB.items())):
        nombre = [n for n, c in HAB.items() if c == code][0]
        x = 12 + k * 150
        dr.rectangle([x, y, x + 18, y + 14], fill=col, outline=(0, 0, 0))
        dr.text((x + 24, y - 1), nombre, fill=(20, 20, 20), font=f)
    dr.text((W + 22, H + 16), 'PLAN %d plantas: %d arboles + %d matas, %d masas (circulos blancos), %d plantas/zona de camara (triangulos rojos)' % (
        st['total'], st['arboles'], st['matas'], st['masas'], len(cams)), fill=(20, 20, 20), font=fb)
    y = H + 40
    for k, e in enumerate(ESPECIES):
        x = W + 22 + (k % 4) * 240; yy = y + (k // 4) * 22
        dr.rectangle([x, yy, x + 18, yy + 14], fill=COLORES_QA[e], outline=(0, 0, 0))
        dr.text((x + 24, yy - 1), '%s %d' % (e, st['por_especie'].get(e, 0)), fill=(20, 20, 20), font=f)
    kp = 'KPI: vecino < 6 m %.0f %% (>= 70) | z > 80 m %.0f %% (>= 30) | holgura pista min %.1f m (>= 12) | en core urbano %d | dura %d | tiempo %.1f s' % (
        st.get('arboles_con_vecino_lt_6m_pct', 0), st.get('arboles_z_gt_80_pct', 0), st.get('holgura_pista_min_m', 0),
        st.get('dentro_core_urbano_n', 0), st.get('en_exclusion_dura_n', 0), datos.get('_tiempo_s', 0))
    dr.text((W + 22, H + 96), kp, fill=(20, 20, 20), font=f)
    dr.text((12, H + 96), 'seed %d  |  %s' % (datos['seed'], os.path.basename(ruta)), fill=(20, 20, 20), font=f)
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    out.save(ruta)
    return ruta


# ------------------------------------------------------------------------------------------------ main
def main(argv):
    rutas = dict(geom=RUTA_GEOM, urb=RUTA_URB, spec=RUTA_SPEC, salida=RUTA_SALIDA, huellas=RUTA_HUELLAS, camaras=RUTA_CAMARAS,
                 mask=RUTA_MASK, bancales=RUTA_BANCALES)
    qa_dir = os.environ.get('QA_DIR') or DIR_QA
    seed, con_qa, cfg = SEED, True, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--geom', '--urb', '--spec', '--salida', '--huellas', '--camaras', '--mask', '--bancales'):
            rutas[a[2:]] = argv[i + 1]; i += 1
        elif a == '--qa-dir':
            qa_dir = argv[i + 1]; i += 1
        elif a == '--seed':
            seed = int(argv[i + 1]); i += 1
        elif a == '--cfg':             # JSON con claves de CFG a sobreescribir (p. ej. {"zonas": {"pinar": {"cobertura": 0.3}}})
            cfg = cargar_json(argv[i + 1]); i += 1
        elif a == '--sin-qa':
            con_qa = False
        else:
            raise SystemExit('argumento desconocido %r (ver docstring)' % a)
        i += 1
    geom = cargar_json(rutas['geom']); urb = cargar_json(rutas['urb'])
    spec = cargar_json(rutas['spec'], obligatorio=False)
    huellas = cargar_json(rutas['huellas'], obligatorio=False)
    camaras = cargar_json(rutas['camaras'], obligatorio=False)
    bsp = cargar_json(rutas['bancales'], obligatorio=False)
    for k in ('huellas', 'camaras', 'bancales'):
        log('%-8s %s' % (k, rutas[k] if os.path.isfile(rutas[k]) else '(no existe: se sigue sin el)'))
    log('mask     %s' % (rutas['mask'] if os.path.isfile(rutas['mask']) else '(no existe: roca solo de mascara_roca)'))
    datos, plan, Z, exc = planificar(geom, urb, seed, cfg, spec, huellas, camaras, rutas['mask'], bsp)
    cams_pts, _ = camaras_plan(camaras)
    # el JSON no lleva fecha ni rutas absolutas: determinista
    datos['entradas'] = {k: os.path.relpath(rutas[k], AQUI).replace('\\', '/') for k in ('geom', 'urb', 'spec', 'huellas', 'camaras', 'mask', 'bancales')
                         if os.path.isfile(rutas[k])}
    os.makedirs(os.path.dirname(os.path.abspath(rutas['salida'])), exist_ok=True)
    with open(rutas['salida'], 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, separators=(',', ':'), ensure_ascii=False)
    md5 = hashlib.md5(open(rutas['salida'], 'rb').read()).hexdigest()
    st = datos['stats']
    log('escrito %s (%.1f MB, md5 %s)' % (rutas['salida'], os.path.getsize(rutas['salida']) / 1e6, md5))
    log('TOTAL %d plantas: %d arboles (objetivo 6-9 k) + %d matas (15-20 k) en %d masas | vecino < 6 m %.1f %% | z > 80 m %.1f %% | %.1f s'
        % (st['total'], st['arboles'], st['matas'], st['masas'], st.get('arboles_con_vecino_lt_6m_pct', 0),
           st.get('arboles_z_gt_80_pct', 0), plan.tiempo_s))
    fallos = verificar(datos, geom, urb, huellas)
    log('VERIFICACION %s' % json.dumps(fallos))
    if con_qa:
        datos['_camaras'] = cams_pts          # solo para el mapa (ya se ha escrito el JSON)
        datos['_tiempo_s'] = plan.tiempo_s
        ruta_png = os.path.join(qa_dir, 'vegetacion_mapa.png')
        mapa_qa(datos, Z, exc, ruta_png)
        log('QA png ' + ruta_png)
    if sum(fallos.values()):
        log('AVISO: la verificacion encontro %s' % fallos)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
