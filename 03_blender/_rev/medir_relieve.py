# -*- coding: utf-8 -*-
"""medir_relieve.py - medidas del relieve de Porto Corsa sobre geometria_3d.json (numpy/scipy; sin Blender, ~3 s).

Fase visual F1 (FASE_VISUAL_PLAN.md secc. 5 'objetivo medible' y secc. 16; propietario 'terreno'). Mide de forma
INDEPENDIENTE (solo lee el JSON) lo mismo que los checks de terreno_montana.construir():
  * tramo de tierra (s 1430-2440 por defecto): 'pared' = terreno > Z+8 a 25 m del borde del asfalto en un lado y 'caida' =
    terreno < Z-8 a 25 m en el otro -> pared_y_caida_25m_pct (objetivo >= 40; tambien a 15, 20 y 50 m: a 15-20 m es lo que ve el
    piloto; a 50 m el objetivo es >= 60),
    pared_25m_pct, caida_25m_pct, pct_pista_con_pared_roca_tierra (objetivo >= 50), una tabla por 100 m y (r3) la ESTRUCTURA por
    filas de 10 m: cuantas filas tienen PyC y cuantas son imposibles por la geometria de la pista (terrazas a ambos lados, horquilla o
    trinchera con pared a ambos lados, cresta con caida a ambos lados).
  * pct_pista_con_pared_roca: toda la pista en tierra (misma definicion que construir: > Z+8 a 25 m en algun lado).
  * terreno a 120 m del borde tras cada sector de terrazas (lado del sector): media / min / max / % >= 110 m
    (objetivo del plan para pueblo_subida_ladera: >= 110 m de media; hoy ~83; es del macizo = F2).
  * orilla con z > 10 m (informativo, acantilados = F2): % de celdas de orilla (tierra tocando mar) en los tramos del plan
    (lado +1 de s 170-402 y 616-820, lado -1 de 2770-2976, costa N/NE = orilla a > 120 m de la pista con y > 450).
  * roca por pendiente: % de celdas de tierra con pendiente > 0.70 (35 grados) con mascara_roca > 0.49 (objetivo >= 80).
  * capas (si el JSON trae extras['capas']): media % por capa en tierra.
  * postal 56 (r2, informativo): vista sintetica desde la camara congelada 56_postal_cima_bahia (renders/ab/_base_antes/camaras.json
    o la de abajo) sobre la rejilla (sin arboles ni objetos): % del cuadro que es mar / tierra / cielo (objetivo del plan: bahia
    >= 25 %; con la isla de la horquilla C18-19 a 14-23 m de la camara es 1 % en la base y en F1: ver PARCHES_F1_terreno.md r2).
  * cupula de la cima de 56 (r4, ACOTACIONES_COORDINADOR_F1.md 1: 'pendiente <= 30 grados en los 20 m superiores, sin dientes ni
    arista recta'): isla = interior de la horquilla C18-19 (eje de la pista s_apex +- 120 m, apex = cota maxima del tramo de tierra),
    celdas a > 4.5 m del asfalto; cumbre = celda mas alta; pendiente POR CARA (2 triangulos por celda, diagonal a-c = la malla de
    construir_pista) a < 20 m de la cumbre: (a) caras VISTAS desde la camara 56 (rayos 320x180 a < 150 m) = la cupula que se ve, y
    (b) todas (incluye el flanco de la rama baja, cara trasera desde 56 = la pared del KPI de la rama alta); angulo de la cumbre
    sobre el ojo de la camara (r3: cono de +10.7 grados) y roca por cara con la regla del writer (nz < 0.50 o atributo > 0.49 y
    nz < 0.82; atributo = extras.capas.roca) en las caras vistas, con los 'dientes' (cara de roca cuyo gemelo no lo es).
  * invariantes: celdas_invaden_pista (celdas a < w/2 del eje por encima de Z; 'sobre Z-0.3' como referencia de construir),
    hierba_asfalto (proxy BILINEAL a 1 m x 0.5 m contra el plano peraltado z = Z - lat*l; construir usa los triangulos de la
    malla), fosos tras la ultima terraza (PROXY 1D: agua atrapada en el perfil o_fin-3..o_fin+40 m cortado en mar/otra rama;
    mas severo que la QA de construir, que es la referencia de la puerta: aqui solo avisa si > 1.5 m) y loews_ref_dz_max contra
    assets/_loews_terreno.npz (objetivo 0.000).
  * con --antes <geometria anterior, MISMA rejilla>: dz = despues - antes -> erosion_corredor_dz_max (|dz| a < 15 m del borde
    del asfalto; 0.000 mientras no haya erosion), dz_mclaren_max (huella del McLaren de urbanismo_spec + 25 m; encaje
    intacto = 0.000), dz_loews_max (< 40 m), dz max global y celdas con |dz| > 0.5; y los KPIs del 'antes' (tabla).
Uso: python 03_blender/_rev/medir_relieve.py [--geom <geometria.json>] [--antes <geometria_antes.json>] [--spec <spec.json>]
     [--out <medidas.json>] [--tramo 1430 2440] [--estricto]
--estricto: exit 1 si falla un invariante (invaden > 0, hierba_asfalto > 0, loews_ref_dz_max > 0.001).
Por defecto lee 03_blender/geometria_3d.json y escribe 03_blender/renders/qa/medir_relieve.json.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from scipy.ndimage import map_coordinates, binary_dilation, distance_transform_edt
from scipy.spatial import cKDTree

AQUI = os.path.dirname(os.path.abspath(__file__))
D03 = os.path.dirname(AQUI)
DEF_GEOM = os.path.join(D03, 'geometria_3d.json')
DEF_SPEC = os.path.join(D03, 'urbanismo_spec.json')
DEF_OUT = os.path.join(D03, 'renders', 'qa', 'medir_relieve.json')
LOEWS_NPZ = os.path.join(D03, 'assets', '_loews_terreno.npz')
TRAMOS_ORILLA = [('mar_170_402_lado+1', 170.0, 402.0, 1), ('mar_616_820_lado+1', 616.0, 820.0, 1),
                 ('recta_2770_2976_lado-1', 2770.0, 2976.0, -1)]
PARED_M = 8.0          # 'pared' = terreno > Z + 8 m; 'caida' = terreno < Z - 8 m
R_LOEWS = 40.0
R_MCL = 25.0
UMBRAL_ROCA_ATR = 0.49  # mismo que color_ac.ROCA_ATR y los revisores
CAM56 = {'loc': [47.972, 567.543, 121.922], 'tgt': [-108.3114, -318.784, 0.0], 'lens': 20.0}   # 56_postal_cima_bahia (BASE congelada)
CAMARAS_BASE = os.path.join(D03, 'renders', 'ab', '_base_antes', 'camaras.json')


def pct(m):
    m = np.asarray(m, bool)
    return round(100.0 * float(m.mean()), 1) if m.size else 0.0


def cargar(ruta):
    d = json.load(open(ruta, encoding='utf-8'))
    M = d['muestras']; T = d['terreno']
    nxg, nyg = int(T['nx']), int(T['ny'])
    g = dict(ruta=ruta, paso=float(d['paso_m']), N=len(M),
             X=np.array([m['x'] for m in M], float), Y=np.array([m['y'] for m in M], float),
             Z=np.array([m['z'] for m in M], float), nx=np.array([m['nx'] for m in M], float),
             ny=np.array([m['ny'] for m in M], float), W=np.array([m['w'] for m in M], float),
             lat=np.array([m.get('lat', 0.0) for m in M], float), sec=[m['sec'] for m in M],
             x0=float(T['x0']), y0=float(T['y0']), cell=float(T['cell']), nxg=nxg, nyg=nyg,
             zg=np.array(T['z'], float).reshape(nyg, nxg), mar=np.array(T['mar'], bool).reshape(nyg, nxg),
             loews=(float(d['loews']['x']), float(d['loews']['y'])))
    r = np.array(d.get('mascara_roca', []), float)
    g['roca'] = r.reshape(nyg, nxg) if r.size == nyg * nxg else None
    cap = (d.get('extras') or {}).get('capas')
    g['capas'] = {k: np.array(v, float).reshape(nyg, nxg) for k, v in cap.items()} if cap else None
    g['s'] = np.arange(g['N']) * g['paso']
    g['land'] = np.array([s_ != 'bridge' for s_ in g['sec']])
    g['dirt'] = np.array([s_ == 'dirt' for s_ in g['sec']])
    g['GX'] = g['x0'] + np.arange(nxg) * g['cell']
    g['GY'] = g['y0'] + np.arange(nyg) * g['cell']
    return g


def z_en(g, x, y):
    x = np.atleast_1d(np.asarray(x, float)); y = np.atleast_1d(np.asarray(y, float))
    return map_coordinates(g['zg'], [(y - g['y0']) / g['cell'], (x - g['x0']) / g['cell']], order=1, mode='nearest')


def lateral(g, idx, off):
    """punto a 'off' m (con signo: + = lado +1 = normal izquierda) de las muestras idx."""
    return g['X'][idx] + g['nx'][idx] * off, g['Y'][idx] + g['ny'][idx] * off


def misma_rejilla(g, h):
    return (g['nxg'] == h['nxg'] and g['nyg'] == h['nyg'] and abs(g['cell'] - h['cell']) < 1e-6
            and abs(g['x0'] - h['x0']) < 1e-3 and abs(g['y0'] - h['y0']) < 1e-3)


# ----------------------------------------------------------------------------------------------- tramo de tierra
def medir_tierra(g, s0, s1, spec=None):
    li = np.where(g['land'])[0]
    Z = g['Z'][li]; W = g['W'][li]; s = g['s'][li]
    en = (s >= s0) & (s <= s1)
    out = {'tramo': [s0, s1], 'n_muestras_tramo': int(en.sum())}
    dz = {}
    for dd in (15.0, 20.0, 25.0, 50.0):
        zp = z_en(g, *lateral(g, li, W / 2.0 + dd)) - Z
        zm = z_en(g, *lateral(g, li, -(W / 2.0 + dd))) - Z
        dz[dd] = (zp, zm)
        pyc = ((zp > PARED_M) & (zm < -PARED_M)) | ((zm > PARED_M) & (zp < -PARED_M))
        pared = (zp > PARED_M) | (zm > PARED_M)
        caida = (zp < -PARED_M) | (zm < -PARED_M)
        k = '%dm' % int(dd)
        out['pared_y_caida_%s_pct' % k] = pct(pyc[en])
        out['pared_%s_pct' % k] = pct(pared[en])
        out['caida_%s_pct' % k] = pct(caida[en])
        if dd == 25.0:
            out['pct_pista_con_pared_roca'] = pct(pared)
            out['pct_pista_con_pared_roca_tierra'] = pct(pared[en])
            out['pct_pared_lado_mas1_tierra'] = pct((zp > PARED_M)[en])
            out['pct_pared_lado_menos1_tierra'] = pct((zm > PARED_M)[en])
            pyc25 = pyc
    zp, zm = dz[25.0]
    filas = []
    for a in range(int(s0), int(s1), 100):
        m = en & (s >= a) & (s < a + 100)
        if m.any():
            filas.append({'s': a, 'dz25_mas1': round(float(zp[m].mean()), 1), 'dz25_menos1': round(float(zm[m].mean()), 1),
                          'pared_y_caida_pct': pct(pyc25[m])})
    out['por_100m'] = filas
    # r3: ESTRUCTURA por filas de 10 m (la muestra de cada s multiplo de 10): donde el KPI es imposible por geometria de la pista
    # (terrazas a ambos lados, horquilla/trinchera con pared a ambos lados, cresta con caida a ambos lados) y donde falta solo un lado
    bandas = []
    for sc in (spec or {}).get('sectores', []):
        if int(sc.get('n_terrazas', 0)) >= 1:
            bandas.append((float(sc['s0']), float(sc['s1']), int(sc['lado'])))
    est = {'pyc': 0, 'terrazas': 0, 'pared_ambos': 0, 'caida_ambos': 0, 'solo_pared': 0, 'solo_caida': 0, 'ninguno': 0}
    filas10 = []
    for a in range(int(math.ceil(s0 / 10.0)) * 10, int(s1) + 1, 10):
        k = np.where(en & (np.abs(s - a) < 1e-6))[0]
        if len(k) == 0:
            continue
        k = int(k[0]); p_, m_ = float(zp[k]), float(zm[k])
        terr = {ld for (a0, a1, ld) in bandas if a0 <= a <= a1}
        if (p_ > PARED_M and m_ < -PARED_M) or (m_ > PARED_M and p_ < -PARED_M):
            cl = 'pyc'
        elif {1, -1} <= terr:
            cl = 'terrazas'
        elif p_ > 5.0 and m_ > 5.0:
            cl = 'pared_ambos'
        elif p_ < -5.0 and m_ < -5.0:
            cl = 'caida_ambos'
        elif p_ > PARED_M or m_ > PARED_M:
            cl = 'solo_pared'
        elif p_ < -PARED_M or m_ < -PARED_M:
            cl = 'solo_caida'
        else:
            cl = 'ninguno'
        est[cl] += 1
        filas10.append({'s': a, 'dz25_mas1': round(p_, 1), 'dz25_menos1': round(m_, 1), 'clase': cl})
    out['estructura_10m'] = {'filas': len(filas10), 'clases': est, 'tabla': filas10}
    return out


# ----------------------------------------------------------------------------------------------- macizo tras las terrazas
def medir_120m(g, spec):
    out = {}
    for sc in spec.get('sectores', []):
        if int(sc.get('n_terrazas', 0)) < 1:
            continue
        lado = int(sc['lado'])
        li = np.where(g['land'] & (g['s'] >= float(sc['s0'])) & (g['s'] <= float(sc['s1'])))[0][::5]
        if len(li) == 0:
            continue
        z120 = z_en(g, *lateral(g, li, lado * (g['W'][li] / 2.0 + 120.0)))
        out[sc['id']] = {'lado': lado, 'n': int(len(li)), 'media': round(float(z120.mean()), 1),
                         'min': round(float(z120.min()), 1), 'max': round(float(z120.max()), 1),
                         'pct_ge_110': pct(z120 >= 110.0), 'z_pista_media': round(float(g['Z'][li].mean()), 1)}
    return out


# ----------------------------------------------------------------------------------------------- orilla (informativo)
def medir_orilla(g):
    mar = g['mar']
    orilla = ~mar & binary_dilation(mar, iterations=1)
    jj, ii = np.where(orilla)
    xs = g['GX'][ii]; ys = g['GY'][jj]; zs = g['zg'][jj, ii]
    tree = cKDTree(np.column_stack([g['X'], g['Y']]))
    d, k = tree.query(np.column_stack([xs, ys]))
    lado = np.where((xs - g['X'][k]) * g['nx'][k] + (ys - g['Y'][k]) * g['ny'][k] > 0, 1, -1)
    sk = g['s'][k]
    out = {'orilla_celdas': int(orilla.sum()), 'z_gt_10_pct_total': pct(zs > 10.0)}
    for nom, a, b, side in TRAMOS_ORILLA:
        m = (sk >= a) & (sk <= b) & (lado == side) & (d < 250.0)
        out[nom] = {'n': int(m.sum()), 'z_gt_10_pct': pct(zs[m] > 10.0), 'z_media': round(float(zs[m].mean()), 1) if m.any() else 0.0}
    m = (d > 120.0) & (ys > 450.0)
    out['costa_N_NE'] = {'n': int(m.sum()), 'z_gt_10_pct': pct(zs[m] > 10.0), 'z_media': round(float(zs[m].mean()), 1) if m.any() else 0.0}
    return out


# ----------------------------------------------------------------------------------------------- roca y capas
def medir_roca(g):
    gy, gx = np.gradient(g['zg'], g['cell'])
    pend = np.hypot(gx, gy)
    tierra = ~g['mar'] & (g['zg'] > 0.5)
    t35 = tierra & (pend > 0.70)
    out = {'celdas_35_pct_tierra': pct(t35[tierra]) if tierra.any() else 0.0, 'celdas_35': int(t35.sum())}
    if g['roca'] is not None:
        out['celdas_35_roca_pct'] = pct(g['roca'][t35] > UMBRAL_ROCA_ATR) if t35.any() else 0.0
        out['roca_pct_tierra'] = pct(g['roca'][tierra] > UMBRAL_ROCA_ATR)
        t40 = tierra & (pend > 0.84)
        out['celdas_40_roca_pct'] = pct(g['roca'][t40] > UMBRAL_ROCA_ATR) if t40.any() else 0.0
    else:
        out['celdas_35_roca_pct'] = None
    if g['capas'] is not None:
        out['capas_media_pct'] = {k: round(100.0 * float(v[tierra].mean()), 1) for k, v in g['capas'].items()}
        suma = sum(g['capas'].values())
        out['capas_suma_1_pct'] = pct(np.abs(suma[tierra] - 1.0) < 0.02)
    else:
        out['capas_media_pct'] = None
    return out


# ----------------------------------------------------------------------------------------------- postal 56 (informativo)
def medir_postal56(g, w=200, h=108, tmax=3000.0, dt=3.0):
    """% del cuadro (mar / tierra / cielo) de la postal 56 sobre la rejilla: rayos desde la camara congelada (lente 20, sensor 36 mm,
    cuadro 1.85:1), primer corte con el terreno (mar = celda 'mar' a z 0). Sin arboles, pacas ni casas: es el techo de lo que puede
    verse. Devuelve ademas la fila del horizonte de terreno en el centro del cuadro (0 = arriba)."""
    cam = dict(CAM56)
    try:
        c = json.load(open(CAMARAS_BASE, encoding='utf-8')).get('56_postal_cima_bahia')
        if c and 'loc' in c and 'tgt' in c:
            cam = {'loc': c['loc'], 'tgt': c['tgt'], 'lens': float(c.get('lens', 20.0))}
    except Exception:  # noqa: BLE001
        pass
    loc = np.array(cam['loc'], float); tgt = np.array(cam['tgt'], float)
    f = tgt - loc; f /= np.linalg.norm(f)
    r = np.cross(f, [0.0, 0.0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    fx = cam['lens'] / 18.0
    px = (np.arange(w) + 0.5) / w * 2 - 1; py = -((np.arange(h) + 0.5) / h * 2 - 1) * (h / w)
    PX, PY = np.meshgrid(px, py)
    dirs = f[None, None, :] * fx + r[None, None, :] * PX[:, :, None] + u[None, None, :] * PY[:, :, None]
    dirs /= np.linalg.norm(dirs, axis=2, keepdims=True)
    zz = np.where(g['mar'], 0.0, g['zg']); marf = g['mar'].astype(float)
    kind = np.zeros((h, w), int)
    for t in np.arange(dt, tmax, dt):
        p = loc[None, None, :] + dirs * t
        cj = (p[:, :, 1] - g['y0']) / g['cell']; ci = (p[:, :, 0] - g['x0']) / g['cell']
        zt = map_coordinates(zz, [cj, ci], order=1, mode='nearest')
        mt = map_coordinates(marf, [cj, ci], order=0, mode='nearest') > 0.5
        new = (kind == 0) & (p[:, :, 2] < zt)
        kind[new] = np.where(mt[new], 2, 1)
        if (kind > 0).all():
            break
    col = kind[:, w // 2]
    fila = int(np.where(col == 1)[0][0]) if (col == 1).any() else -1
    return {'camara': cam, 'mar_pct': pct(kind == 2), 'tierra_pct': pct(kind == 1), 'cielo_pct': pct(kind == 0),
            'horizonte_terreno_fila_centro': fila, 'filas': h}


# ----------------------------------------------------------------------------------------------- cupula de 56 (r4)
def _caras(g):
    """pendiente y nz por triangulo [ny-1, nx-1, 2] (0 = abc, 1 = acd; diagonal a-c como construir_pista)."""
    z = g['zg']; c = g['cell']
    za = z[:-1, :-1]; zb = z[:-1, 1:]; zc = z[1:, 1:]; zd = z[1:, :-1]
    pend = np.stack([np.hypot(zb - za, zc - zb) / c, np.hypot(zd - za, zc - zd) / c], -1)
    return pend, 1.0 / np.sqrt(1.0 + pend ** 2)


def _caras_vistas(g, cam, w=320, h=180, dmax=150.0, dt=0.5):
    """caras (j, i, k) golpeadas por los rayos de la camara a < dmax (marcha de dt m; cara por la posicion del primer corte)."""
    loc = np.array(cam['loc'], float); tgt = np.array(cam['tgt'], float)
    f = tgt - loc; f /= np.linalg.norm(f)
    r = np.cross(f, [0.0, 0.0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    fx = float(cam.get('lens', 20.0)) / 18.0
    px = (np.arange(w) + 0.5) / w * 2 - 1; py = -((np.arange(h) + 0.5) / h * 2 - 1) * (h / w)
    PX, PY = np.meshgrid(px, py)
    d = f[None, None, :] * fx + r[None, None, :] * PX[:, :, None] + u[None, None, :] * PY[:, :, None]
    d = (d / np.linalg.norm(d, axis=2, keepdims=True)).reshape(-1, 3)
    zz = np.where(g['mar'], 0.0, g['zg'])
    vivo = np.ones(len(d), bool); caras = set()
    for t in np.arange(dt, dmax, dt):
        if not vivo.any():
            break
        p = loc[None, :] + d[vivo] * t
        fxg = (p[:, 0] - g['x0']) / g['cell']; fyg = (p[:, 1] - g['y0']) / g['cell']
        i = np.clip(np.floor(fxg).astype(int), 0, g['nxg'] - 2); j = np.clip(np.floor(fyg).astype(int), 0, g['nyg'] - 2)
        tx = np.clip(fxg - i, 0, 1); ty = np.clip(fyg - j, 0, 1); k = (ty > tx).astype(int)
        za = zz[j, i]; zb = zz[j, i + 1]; zc = zz[j + 1, i + 1]; zd = zz[j + 1, i]
        zt = np.where(k == 0, za + tx * (zb - za) + ty * (zc - zb), za + ty * (zd - za) + tx * (zc - zd))
        bajo = p[:, 2] < zt
        if bajo.any():
            caras.update(zip(j[bajo].tolist(), i[bajo].tolist(), k[bajo].tolist()))
            idx = np.where(vivo)[0][bajo]
            vivo[idx] = False
    return caras


def medir_cupula56(g, ds=120.0, r_cumbre=20.0):
    cam = dict(CAM56)
    try:
        c = json.load(open(CAMARAS_BASE, encoding='utf-8')).get('56_postal_cima_bahia')
        if c and 'loc' in c and 'tgt' in c:
            cam = {'loc': c['loc'], 'tgt': c['tgt'], 'lens': float(c.get('lens', 20.0))}
    except Exception:  # noqa: BLE001
        pass
    sel = (g['s'] >= 1430.0) & (g['s'] <= 2440.0)
    ia = int(np.where(sel)[0][np.argmax(g['Z'][sel])])
    i0 = max(0, int((g['s'][ia] - ds) / g['paso'])); i1 = min(g['N'] - 1, int((g['s'][ia] + ds) / g['paso']))
    P = np.c_[g['X'][i0:i1 + 1], g['Y'][i0:i1 + 1]]
    GX, GY = np.meshgrid(g['GX'], g['GY'])
    ins = np.zeros(GX.shape, bool)
    for a in range(len(P)):
        x1, y1 = P[a]; x2, y2 = P[(a + 1) % len(P)]
        ins ^= ((y1 > GY) != (y2 > GY)) & (GX < (x2 - x1) * (GY - y1) / (y2 - y1 + 1e-12) + x1)
    dq, kq = cKDTree(np.c_[g['X'], g['Y']]).query(np.c_[GX.ravel(), GY.ravel()])
    isla = ins & ((dq - g['W'][kq] / 2.0) > 4.5).reshape(GX.shape) & ~g['mar']
    if not isla.any():
        return None
    zi = np.where(isla, g['zg'], -1e9); jm, im = np.unravel_index(np.argmax(zi), zi.shape)
    cx, cy, cz = float(GX[jm, im]), float(GY[jm, im]), float(g['zg'][jm, im])
    pend, nz = _caras(g)
    xc = g['x0'] + (np.arange(g['nxg'] - 1) + 0.5) * g['cell']; yc = g['y0'] + (np.arange(g['nyg'] - 1) + 0.5) * g['cell']
    XC, YC = np.meshgrid(xc, yc)
    isla_f = np.repeat((isla[:-1, :-1] & isla[1:, 1:])[:, :, None], 2, axis=2)
    cerca = np.repeat((np.hypot(XC - cx, YC - cy) <= r_cumbre)[:, :, None], 2, axis=2) & isla_f
    vis = np.zeros(pend.shape, bool)
    for (fj, fi, fk) in _caras_vistas(g, cam):
        vis[fj, fi, fk] = True
    if g['capas'] is not None:
        rv = g['capas']['roca']
    else:
        rv = g['roca'] if g['roca'] is not None else np.zeros_like(g['zg'])
    ra, rb, rc, rd = rv[:-1, :-1], rv[:-1, 1:], rv[1:, 1:], rv[1:, :-1]
    rf = np.stack([(ra + rb + rc) / 3.0, (ra + rc + rd) / 3.0], -1)
    roca = (nz < 0.50) | ((rf > UMBRAL_ROCA_ATR) & (nz < 0.82))
    diente = roca & ~roca[:, :, ::-1]
    t30 = math.tan(math.radians(30.0))

    def est(m):
        p = pend[m]
        if not p.size:
            return {'n': 0}
        return {'n': int(p.size), 'max_grados': round(math.degrees(math.atan(float(p.max()))), 1),
                'p95_grados': round(math.degrees(math.atan(float(np.percentile(p, 95)))), 1), 'pct_gt_30': pct(p > t30)}
    v20 = est(cerca & vis)
    return {'apex_s': round(float(g['s'][ia]), 1), 'cumbre': [round(cx, 1), round(cy, 1), round(cz, 2)], 'ojo_z': cam['loc'][2],
            'cumbre_sobre_ojo_grados': round(math.degrees(math.atan2(cz - cam['loc'][2], math.hypot(cx - cam['loc'][0], cy - cam['loc'][1]))), 2),
            'celdas_isla': int(isla.sum()), 'r_cumbre_m': r_cumbre,
            'vistas_lt20m': v20, 'todas_lt20m': est(cerca), 'vistas_isla': est(isla_f & vis),
            'roca_caras_vistas_isla': int((roca & vis & isla_f).sum()), 'dientes_vistos_isla': int((diente & vis & isla_f).sum()),
            'dientes_vistos_cuadro_lt150m': int((diente & vis).sum()),
            'cumple_acotacion_1': bool(v20.get('pct_gt_30', 100.0) == 0.0 and int((diente & vis & isla_f).sum()) == 0)}


# ----------------------------------------------------------------------------------------------- invariantes
def _celdas_pista(g):
    """muestra de tierra mas cercana a cada celda y su offset lateral/longitudinal."""
    li = np.where(g['land'])[0]
    tree = cKDTree(np.column_stack([g['X'][li], g['Y'][li]]))
    CX, CY = np.meshgrid(g['GX'], g['GY'])
    pts = np.column_stack([CX.ravel(), CY.ravel()])
    d, k = tree.query(pts)
    k = li[k]
    u = (pts[:, 0] - g['X'][k]) * g['nx'][k] + (pts[:, 1] - g['Y'][k]) * g['ny'][k]
    lon = np.abs((pts[:, 0] - g['X'][k]) * g['ny'][k] - (pts[:, 1] - g['Y'][k]) * g['nx'][k])
    return d, k, u, lon


def medir_invariantes(g, spec):
    out = {}
    d, k, u, lon = _celdas_pista(g)
    z = g['zg'].ravel()
    bajo_asf = (d < g['W'][k] / 2.0) & ~g['mar'].ravel()
    # invasion = celda bajo la calzada por ENCIMA de la rasante (el asfalto no la tapa); construir cuenta ademas las que
    # pasan de Z-0.3 (corredor a Z-0.5 con tolerancia): se informa como referencia
    out['celdas_invaden_pista'] = int((bajo_asf & (z > g['Z'][k])).sum())
    out['celdas_bajo_asfalto_sobre_Zm0p3'] = int((bajo_asf & (z > g['Z'][k] - 0.3)).sum())
    # hierba sobre el asfalto (proxy bilineal): puntos cada 1 m en s y 0.5 m a lo ancho, plano peraltado z = Z - lat*l
    li = np.where(g['land'] & g['land'][(np.arange(g['N']) + 1) % g['N']])[0]
    jj = (li + 1) % g['N']
    PX, PY, PZ = [], [], []
    for t in (0.0, 0.5):
        x = g['X'][li] * (1 - t) + g['X'][jj] * t; y = g['Y'][li] * (1 - t) + g['Y'][jj] * t
        zz = g['Z'][li] * (1 - t) + g['Z'][jj] * t
        vx = g['nx'][li] * (1 - t) + g['nx'][jj] * t; vy = g['ny'][li] * (1 - t) + g['ny'][jj] * t
        nn = np.hypot(vx, vy); vx /= nn; vy /= nn
        w = g['W'][li] * (1 - t) + g['W'][jj] * t; la = g['lat'][li] * (1 - t) + g['lat'][jj] * t
        for f in np.linspace(-0.5, 0.5, int(math.ceil(float(w.max()) / 0.5)) + 1):
            l = f * (w - 0.5)
            PX.append(x + vx * l); PY.append(y + vy * l); PZ.append(zz - la * l)
    PX = np.concatenate(PX); PY = np.concatenate(PY); PZ = np.concatenate(PZ)
    zt = z_en(g, PX, PY)
    exc = zt - PZ
    out['hierba_asfalto_puntos_gt_2cm_proxy'] = int((exc > 0.02).sum())
    out['hierba_asfalto_max_m_proxy'] = round(float(exc.max()), 3)
    # fosos tras la ultima terraza: agua atrapada en el perfil o_fin-3 .. o_fin+40 m (1D, cada 1 m), cortado (como
    # construir) donde el punto cae en el mar, en otra rama (muestra mas cercana fuera del sector) o al otro lado de la pista
    AT = float(spec.get('ancho_terraza', 21.0))
    fosos = {}
    offs = np.arange(-3.0, 40.01, 1.0)
    li_all = np.where(g['land'])[0]
    tree_l = cKDTree(np.column_stack([g['X'][li_all], g['Y'][li_all]]))
    for sc in spec.get('sectores', []):
        nt = int(sc.get('n_terrazas', 0))
        if nt < 1:
            continue
        lado = int(sc['lado']); o_fin = AT * nt
        lj = np.where(g['land'] & (g['s'] >= float(sc['s0'])) & (g['s'] <= float(sc['s1'])))[0]
        if len(lj) == 0:
            continue
        off = lado * (g['W'][lj][:, None] / 2.0 + o_fin + offs[None, :])
        px = g['X'][lj][:, None] + g['nx'][lj][:, None] * off
        py = g['Y'][lj][:, None] + g['ny'][lj][:, None] * off
        zz = z_en(g, px.ravel(), py.ravel()).reshape(px.shape)
        dq, kq = tree_l.query(np.column_stack([px.ravel(), py.ravel()]))
        kq = li_all[kq]
        sq = g['s'][kq].reshape(px.shape)
        lado_q = np.where((px.ravel() - g['X'][kq]) * g['nx'][kq] + (py.ravel() - g['Y'][kq]) * g['ny'][kq] > 0, 1, -1).reshape(px.shape)
        mar_q = map_coordinates(g['mar'].astype(float), [(py.ravel() - g['y0']) / g['cell'], (px.ravel() - g['x0']) / g['cell']],
                                order=0, mode='nearest').reshape(px.shape) > 0.5
        # otra RAMA del mismo sector (zigzag del casino, horquillas): muestra mas cercana a > 40 m por la pista y a < 70 % de
        # esa distancia en linea recta (MISMO_RAMAL de terreno_montana): el perfil se corta ahi, como en construir
        dl_q = np.abs(sq - g['s'][lj][:, None]); dl_q = np.minimum(dl_q, g['s'][-1] + g['paso'] - dl_q)
        dij_q = np.hypot(g['X'][kq].reshape(px.shape) - g['X'][lj][:, None], g['Y'][kq].reshape(px.shape) - g['Y'][lj][:, None])
        otra_q = (dl_q > 40.0) & (dij_q < 0.7 * dl_q)
        val = ~mar_q & ~otra_q & (sq >= float(sc['s0']) - 10.0) & (sq <= float(sc['s1']) + 10.0) & (lado_q == lado)
        val = np.logical_and.accumulate(val, axis=1)          # el perfil se corta en el primer punto no valido
        zz = np.where(val, zz, -1e9)
        izq = np.maximum.accumulate(zz, axis=1)
        der = np.maximum.accumulate(np.where(val, zz, -1e9)[:, ::-1], axis=1)[:, ::-1]
        agua = np.where(val, np.minimum(izq, der) - zz, 0.0)
        peor = agua.max(axis=1)
        i_p = int(np.argmax(peor))
        fosos[sc['id']] = {'agua_max_m': round(float(peor.max()), 2), 's_peor': int(g['s'][lj][i_p]),
                           'muestras_gt_1p5': int((peor > 1.5).sum())}
    out['fosos'] = fosos
    out['foso_max_m'] = round(max([v['agua_max_m'] for v in fosos.values()] + [0.0]), 2)
    # Loews: referencia fija
    out['loews_ref_dz_max'] = None
    if os.path.exists(LOEWS_NPZ):
        ref = np.load(LOEWS_NPZ)
        if (int(ref['nx']) == g['nxg'] and int(ref['ny']) == g['nyg'] and abs(float(ref['x0']) - g['x0']) < 1e-3
                and abs(float(ref['y0']) - g['y0']) < 1e-3):
            idx = ref['idx']; cx, cy = float(ref['cx']), float(ref['cy'])
            px = g['GX'][idx % g['nxg']]; py = g['GY'][idx // g['nxg']]
            cerca = np.hypot(px - cx, py - cy) < R_LOEWS
            out['loews_ref_dz_max'] = round(float(np.abs(z[idx][cerca] - ref['z'][cerca]).max()), 3) if cerca.any() else 0.0
        else:
            out['loews_ref_dz_max'] = 'rejilla distinta'
    # el foso es un PROXY 1D mas severo que la QA de construir (que corta ademas en las terrazas de otro sector y usa su
    # perfil real): construir es la referencia de la puerta; aqui solo avisa
    out['foso_aviso'] = bool(out['foso_max_m'] > 1.5)
    ok = (out['celdas_invaden_pista'] == 0 and out['hierba_asfalto_puntos_gt_2cm_proxy'] == 0
          and (not isinstance(out['loews_ref_dz_max'], float) or out['loews_ref_dz_max'] <= 0.001))
    out['ok'] = bool(ok)
    return out


# ----------------------------------------------------------------------------------------------- antes / despues
def medir_dz(g, ga, spec):
    if not misma_rejilla(g, ga):
        return {'error': 'rejillas distintas: no se compara'}
    dz = (g['zg'] - ga['zg']).ravel()
    d, k, u, lon = _celdas_pista(g)
    dedge = d - g['W'][k] / 2.0
    out = {'dz_max_abs': round(float(np.abs(dz).max()), 2), 'celdas_gt_0p5': int((np.abs(dz) > 0.5).sum()),
           'celdas_gt_2': int((np.abs(dz) > 2.0).sum()), 'subidas_max': round(float(dz.max()), 2), 'bajadas_max': round(float(-dz.min()), 2)}
    i = int(np.argmax(np.abs(dz)))
    out['dz_max_xy'] = [round(float(g['GX'][i % g['nxg']]), 1), round(float(g['GY'][i // g['nxg']]), 1)]
    # corredor (llano a Z-0.5 hasta 4.5 m del borde): no debe cambiar nunca; < 15 m cambia con el desmonte/berma de F1
    # (informativo); erosion_corredor_dz_max se medira sobre el delta de erosion.py (F4): hoy no hay erosion -> 0.000
    out['dz_corredor_4p5m_max'] = round(float(np.abs(dz[dedge < 4.5]).max()), 3)
    out['dz_lt_15m_max'] = round(float(np.abs(dz[dedge < 15.0]).max()), 3)
    out['erosion_corredor_dz_max'] = 0.0
    out['dz_max_lt_40m'] = round(float(np.abs(dz[dedge < 40.0]).max()), 2)
    cx, cy = g['loews']
    CX, CY = np.meshgrid(g['GX'], g['GY'])
    dl = np.hypot(CX.ravel() - cx, CY.ravel() - cy)
    out['dz_loews_max'] = round(float(np.abs(dz[dl < R_LOEWS]).max()), 3)
    out['dz_loews_65_max'] = round(float(np.abs(dz[dl < 65.0]).max()), 3)
    # huella del McLaren + 25 m (urbanismo_spec zonas_excluidas)
    try:
        from matplotlib.path import Path
        polys = [z_ for z_ in spec.get('zonas_excluidas', []) if z_.get('poligono')]
        if polys:
            dentro = np.zeros(len(dz), bool)
            for z_ in polys:
                dentro |= Path(np.array(z_['poligono'], float)).contains_points(np.column_stack([CX.ravel(), CY.ravel()]))
            dmc = (distance_transform_edt(~dentro.reshape(g['nyg'], g['nxg'])) * g['cell']).ravel()
            m = dmc < R_MCL
            out['dz_mclaren_max'] = round(float(np.abs(dz[m]).max()), 3) if m.any() else 0.0
            out['dz_mclaren_celdas'] = int(m.sum())
            out['dz_mclaren_por_banda'] = {'0m': round(float(np.abs(dz[dentro]).max()), 3) if dentro.any() else 0.0,
                                           'lt_10m': round(float(np.abs(dz[dmc < 10.0]).max()), 3),
                                           'lt_25m': out['dz_mclaren_max'],
                                           'lt_40m': round(float(np.abs(dz[dmc < 40.0]).max()), 3)}
    except Exception as e:  # noqa: BLE001
        out['dz_mclaren_max'] = 'no medido (%s)' % e
    # dz por tramo de 200 m de la muestra mas cercana (solo celdas a < 120 m del borde)
    filas = []
    s_k = g['s'][k]
    for a in range(0, int(g['s'][-1]) + 1, 200):
        m = (s_k >= a) & (s_k < a + 200) & (dedge < 120.0)
        if m.any() and np.abs(dz[m]).max() > 0.05:
            filas.append({'s': a, 'dz_max': round(float(np.abs(dz[m]).max()), 1), 'subida_media_gt_0p5': round(float(dz[m][dz[m] > 0.5].mean()), 1) if (dz[m] > 0.5).any() else 0.0,
                          'bajada_media_lt_m0p5': round(float(dz[m][dz[m] < -0.5].mean()), 1) if (dz[m] < -0.5).any() else 0.0})
    out['por_200m'] = filas
    return out


# ----------------------------------------------------------------------------------------------- main
def medir_todo(g, spec, s0, s1):
    return {'geom': g['ruta'], 'tierra': medir_tierra(g, s0, s1, spec), 'tras_terrazas_120m': medir_120m(g, spec),
            'orilla': medir_orilla(g), 'roca': medir_roca(g), 'invariantes': medir_invariantes(g, spec), 'postal56': medir_postal56(g),
            'cupula56': medir_cupula56(g)}


def imprimir(res, etiqueta):
    t = res['tierra']; r = res['roca']; inv = res['invariantes']
    print('[%s] %s' % (etiqueta, res['geom']))
    print('  tierra s %d-%d (%d muestras): pared Y caida a 25 m %.1f %% (obj >= 40) | a 50 m %.1f %% (obj >= 60) | pared en algun lado %.1f %% '
          '(lado +1 %.1f, -1 %.1f) | caida en algun lado %.1f %% | pct_pista_con_pared_roca: tierra %.1f %% (obj >= 50), toda la pista %.1f %%'
          % (t['tramo'][0], t['tramo'][1], t['n_muestras_tramo'], t['pared_y_caida_25m_pct'], t['pared_y_caida_50m_pct'], t['pared_25m_pct'],
             t['pct_pared_lado_mas1_tierra'], t['pct_pared_lado_menos1_tierra'], t['caida_25m_pct'], t['pct_pista_con_pared_roca_tierra'],
             t['pct_pista_con_pared_roca']))
    print('    pared Y caida a 15 m %.1f %% | a 20 m %.1f %% (lo que ve el piloto; las ramas del zigzag van a ~50 m: a 25 m solo una de cada par '
          'puede tener pared y caida)' % (t['pared_y_caida_15m_pct'], t['pared_y_caida_20m_pct']))
    print('    por 100 m (s: dz25 lado+1 / lado-1 / pared_y_caida %%): ' + ', '.join(
        '%d: %+.0f/%+.0f/%.0f' % (f['s'], f['dz25_mas1'], f['dz25_menos1'], f['pared_y_caida_pct']) for f in t['por_100m']))
    e = t.get('estructura_10m')
    if e:
        c = e['clases']; n = max(e['filas'], 1)
        print('    estructura (filas de 10 m, %d): PyC %d (%.0f %%) | imposibles por la pista: terrazas a ambos lados %d, pared a ambos lados '
              '(horquilla/trinchera) %d, caida a ambos lados (cresta) %d = %d (%.0f %%) | solo pared %d, solo caida %d, ninguno %d'
              % (n, c['pyc'], 100.0 * c['pyc'] / n, c['terrazas'], c['pared_ambos'], c['caida_ambos'],
                 c['terrazas'] + c['pared_ambos'] + c['caida_ambos'], 100.0 * (c['terrazas'] + c['pared_ambos'] + c['caida_ambos']) / n,
                 c['solo_pared'], c['solo_caida'], c['ninguno']))
    for sid, v in res['tras_terrazas_120m'].items():
        if sid == 'pueblo_subida_ladera':
            print('  terreno a 120 m tras %s (lado %+d): media %.1f m (obj >= 110; pista %.1f), min %.1f, max %.1f, >= 110 en %.1f %%'
                  % (sid, v['lado'], v['media'], v['z_pista_media'], v['min'], v['max'], v['pct_ge_110']))
    p56 = res.get('postal56')
    if p56:
        print('  postal 56 (vista sintetica, camara congelada %s): mar %.1f %% del cuadro (obj >= 25) | tierra %.1f %% | cielo %.1f %% | horizonte '
              'de terreno en el centro: fila %d de %d' % (p56['camara']['loc'], p56['mar_pct'], p56['tierra_pct'], p56['cielo_pct'],
                                                     p56['horizonte_terreno_fila_centro'], p56['filas']))
    cu = res.get('cupula56')
    if cu:
        v, t_, vi = cu['vistas_lt20m'], cu['todas_lt20m'], cu['vistas_isla']
        print('  cupula 56 (acotacion 1: <= 30 grados en los 20 m superiores, sin dientes): cumbre %s (apex s %.0f), %+.1f grados sobre el ojo '
              '(z %.1f) | caras a < %.0f m de la cumbre VISTAS desde 56: %d, max %s grados, > 30 grados %s %% | TODAS: %d, max %s, > 30 grados %s %% '
              '(flanco de la rama baja: cara trasera = pared del KPI) | isla vista: %d caras, max %s grados | roca por cara vista en la isla %d, '
              'dientes %d (cuadro < 150 m: %d) -> %s'
              % (cu['cumbre'], cu['apex_s'], cu['cumbre_sobre_ojo_grados'], cu['ojo_z'], cu['r_cumbre_m'], v.get('n', 0), v.get('max_grados'),
                 v.get('pct_gt_30'), t_.get('n', 0), t_.get('max_grados'), t_.get('pct_gt_30'), vi.get('n', 0), vi.get('max_grados'),
                 cu['roca_caras_vistas_isla'], cu['dientes_vistos_isla'], cu['dientes_vistos_cuadro_lt150m'],
                 'CUMPLE' if cu['cumple_acotacion_1'] else 'NO cumple'))
    o = res['orilla']
    print('  orilla z > 10 m (informativo): total %.1f %% | ' % o['z_gt_10_pct_total'] + ' | '.join(
        '%s %.1f %% (n %d)' % (k, v['z_gt_10_pct'], v['n']) for k, v in o.items() if isinstance(v, dict)))
    print('  roca: celdas > 35 grados = %.1f %% de la tierra; con roca %s %% (obj >= 80); > 40 grados con roca %s %%; roca en %s %% de la tierra'
          % (r['celdas_35_pct_tierra'], r['celdas_35_roca_pct'], r.get('celdas_40_roca_pct'), r.get('roca_pct_tierra')))
    print('  capas (media %% en tierra): %s%s' % (r['capas_media_pct'], (' | suma = 1 en %.1f %% de las celdas' % r['capas_suma_1_pct']) if r.get('capas_suma_1_pct') is not None else ''))
    print('  invariantes: celdas_invaden_pista %d (sobre Z-0.3: %d) | hierba_asfalto (proxy) %d puntos (max %+.3f m) | loews_ref_dz_max %s -> %s | '
          'foso (proxy 1D, aviso; la referencia es la QA de construir) max %.2f m %s%s'
          % (inv['celdas_invaden_pista'], inv['celdas_bajo_asfalto_sobre_Zm0p3'], inv['hierba_asfalto_puntos_gt_2cm_proxy'], inv['hierba_asfalto_max_m_proxy'],
             inv['loews_ref_dz_max'], 'ok' if inv['ok'] else 'FALLO', inv['foso_max_m'], {k: v['agua_max_m'] for k, v in inv['fosos'].items()},
             ' AVISO > 1.5' if inv['foso_aviso'] else ''))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--geom', default=os.environ.get('GEOM', DEF_GEOM))
    ap.add_argument('--antes', default=None)
    ap.add_argument('--spec', default=DEF_SPEC)
    ap.add_argument('--out', default=DEF_OUT)
    ap.add_argument('--tramo', nargs=2, type=float, default=(1430.0, 2440.0))
    ap.add_argument('--estricto', action='store_true')
    a = ap.parse_args(argv)
    spec = json.load(open(a.spec, encoding='utf-8'))
    g = cargar(a.geom)
    res = {'despues': medir_todo(g, spec, a.tramo[0], a.tramo[1])}
    if a.antes:
        ga = cargar(a.antes)
        res['antes'] = medir_todo(ga, spec, a.tramo[0], a.tramo[1])
        res['dz'] = medir_dz(g, ga, spec)
        imprimir(res['antes'], 'ANTES')
    imprimir(res['despues'], 'DESPUES' if a.antes else 'MEDIDAS')
    if a.antes:
        d = res['dz']
        if 'error' in d:
            print('  dz: ' + d['error'])
        else:
            print('  dz despues-antes: max |dz| %.2f m en %s | celdas > 0.5: %d, > 2: %d (subidas hasta %.1f, bajadas hasta %.1f) | '
                  'corredor < 4.5 m del asfalto %.3f (obj 0.000) | < 15 m %.3f (desmonte/berma) | < 40 m %.2f | McLaren por banda %s (obj 0.000 a < 25 m) | '
                  'Loews < 40 m %.3f (< 65 m %.3f) | erosion_corredor_dz_max %.3f (F4)'
                  % (d['dz_max_abs'], d['dz_max_xy'], d['celdas_gt_0p5'], d['celdas_gt_2'], d['subidas_max'], d['bajadas_max'],
                     d['dz_corredor_4p5m_max'], d['dz_lt_15m_max'], d['dz_max_lt_40m'], d.get('dz_mclaren_por_banda', d.get('dz_mclaren_max')),
                     d['dz_loews_max'], d['dz_loews_65_max'], d['erosion_corredor_dz_max']))
            print('    por 200 m de s (celdas a < 120 m del borde): ' + ', '.join('%d: %.1f' % (f['s'], f['dz_max']) for f in d['por_200m']))
        ta, td = res['antes']['tierra'], res['despues']['tierra']
        print('  KPI antes -> despues: pared_y_caida_25m %.1f -> %.1f %% | 50 m %.1f -> %.1f %% | pared_roca tierra %.1f -> %.1f %% | '
              'roca > 35 grados %s -> %s %% | 120 m tras pueblo_subida_ladera %.1f -> %.1f m'
              % (ta['pared_y_caida_25m_pct'], td['pared_y_caida_25m_pct'], ta['pared_y_caida_50m_pct'], td['pared_y_caida_50m_pct'],
                 ta['pct_pista_con_pared_roca_tierra'], td['pct_pista_con_pared_roca_tierra'], res['antes']['roca']['celdas_35_roca_pct'],
                 res['despues']['roca']['celdas_35_roca_pct'],
                 res['antes']['tras_terrazas_120m'].get('pueblo_subida_ladera', {}).get('media', 0.0),
                 res['despues']['tras_terrazas_120m'].get('pueblo_subida_ladera', {}).get('media', 0.0)))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(res, open(a.out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print('  -> ' + a.out)
    if a.estricto and not res['despues']['invariantes']['ok']:
        print('INVARIANTES: FALLO')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
