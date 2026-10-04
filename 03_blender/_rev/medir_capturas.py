# -*- coding: utf-8 -*-
"""medir_capturas.py - medidas automaticas sobre las capturas PNG (plan C 0.5 / FASE_VISUAL_PLAN secc. 1), sin Blender.

  python 03_blender/_rev/medir_capturas.py <dir_capturas> [<dir2> ...] [--camaras camaras.json] [--arboles arboles.json]
         [--out medidas.json] [--solo 49,50]
Escribe medidas.json (defecto: en la carpeta padre del primer dir) con, por carpeta y toma:
  pct_cesped      % de pixeles con HSV H 95-135 grados, S > 0.45, V > 0.5 (el verde cesped del tile actual). Objetivo < 8 % en piloto.
  riqueza         entropia de color local (bits): imagen cuantizada a 4 bits/canal, bloques de 16x16 px con >= 50 % de
                  "terreno" (ni cielo/mar azul, ni gris S < 0.12, ni casi negro), entropia de Shannon del histograma de
                  colores del bloque, media de bloques. Max teorico 8 bits. Objetivo x2 en terreno.
  varianza_local  desviacion tipica de V en ventana 9x9, media sobre los pixeles de terreno (la version "varianza" del plan C).
  bandas_blancas  n. de componentes conexas (8-vecinos) de pixeles claros (V > 0.75, S < 0.15) de >= 40 px cuyo anillo
                  exterior (dilatacion 3 px) es >= 50 % verde (H 70-150, S > 0.25): los dientes de sierra de 07/08. Objetivo 0.
  pared_lisa      % de pixeles de roca (S < 0.35, 0.45 < V < 0.9, H 15-60 u S < 0.12, no claros, no azules) con desviacion
                  local de V (9x9) < 0.02. Objetivo < 30 %. Se da tambien pct_roca para saber cuanta roca hay en el cuadro.
  siluetas_20_120 n. de arboles (VEG_pino/cipres/olivo/encina/palmera, OLI_olivo, *_penon_*, MIRADOR_palmera) a 20-120 m de la
                  camara dentro de un cono de 60 grados (+-30) alrededor de la direccion de la vista, solo tomas piloto/postal;
                  necesita camaras.json (loc/tgt) y arboles.json (los escribe capturas_ab.py). Objetivo x3.
Con exactamente 2 carpetas anade "_delta" (segunda - primera) por toma; "_resumen" da medias por carpeta (piloto / aereas).
"""
import argparse
import datetime
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ARBOLES = ('VEG_pino', 'VEG_cipres', 'VEG_olivo', 'VEG_encina', 'VEG_palmera', 'OLI_olivo',
           'VEG_penon_pino', 'VEG_penon_palmera', 'VEG_penon_cipres', 'MIRADOR_palmera')
METRICAS = ('pct_cesped', 'riqueza', 'varianza_local', 'bandas_blancas', 'pared_lisa', 'pct_roca', 'pct_azul', 'siluetas_20_120')


def hsv(rgb8):
    x = rgb8.astype(np.float32) / 255.0
    mx = x.max(axis=2); mn = x.min(axis=2); d = mx - mn
    V = mx
    S = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    H = np.zeros_like(mx)
    m = d > 1e-6
    dd = np.where(m, d, 1.0)
    rc = (mx == r) & m
    gc = (mx == g) & m & ~rc
    bc = m & ~rc & ~gc
    H[rc] = (60.0 * ((g - b) / dd))[rc] % 360.0
    H[gc] = (60.0 * ((b - r) / dd) + 120.0)[gc]
    H[bc] = (60.0 * ((r - g) / dd) + 240.0)[bc]
    return H, S, V


def std_local(V, k=9):
    m1 = ndimage.uniform_filter(V, k, mode='reflect')
    m2 = ndimage.uniform_filter(V * V, k, mode='reflect')
    return np.sqrt(np.maximum(m2 - m1 * m1, 0.0))


def entropia_bloques(rgb8, terreno, bloque=16):
    q = (rgb8 >> 4).astype(np.int32)
    idx = (q[..., 0] << 8) | (q[..., 1] << 4) | q[..., 2]
    h, w = idx.shape
    vals = []
    for y in range(0, h - bloque + 1, bloque):
        for x in range(0, w - bloque + 1, bloque):
            tm = terreno[y:y + bloque, x:x + bloque]
            if tm.mean() < 0.5:
                continue
            c = np.bincount(idx[y:y + bloque, x:x + bloque][tm], minlength=4096).astype(np.float64)
            p = c[c > 0] / c.sum()
            vals.append(float(-(p * np.log2(p)).sum()))
    return (float(np.mean(vals)) if vals else None), len(vals)


def bandas_blancas(claro, verde, min_px=40):
    lab, n = ndimage.label(claro, structure=np.ones((3, 3), bool))
    if n == 0:
        return 0
    tam = np.bincount(lab.ravel(), minlength=n + 1)
    lab_dil = ndimage.grey_dilation(lab, size=(7, 7))
    anillo = (lab == 0) & (lab_dil > 0)
    tot = np.bincount(lab_dil[anillo], minlength=n + 1)
    ver = np.bincount(lab_dil[anillo & verde], minlength=n + 1)
    ok = (tam[1:] >= min_px) & (tot[1:] > 0) & (ver[1:] >= 0.5 * tot[1:])
    return int(ok.sum())


def medir_imagen(ruta):
    rgb8 = np.asarray(Image.open(ruta).convert('RGB'))
    H, S, V = hsv(rgb8)
    cesped = (H >= 95) & (H <= 135) & (S > 0.45) & (V > 0.5)
    azul = (H >= 185) & (H <= 250) & (S > 0.2) & (V > 0.35)
    gris = S < 0.12
    claro = (V > 0.75) & (S < 0.15)
    verde = (H >= 70) & (H <= 150) & (S > 0.25) & (V > 0.2)
    terreno = ~azul & ~gris & (V > 0.08)
    roca = (S < 0.35) & (V > 0.45) & (V < 0.9) & (((H >= 15) & (H <= 60)) | gris) & ~claro & ~azul
    sd = std_local(V, 9)
    riq, nb = entropia_bloques(rgb8, terreno)
    n_roca = int(roca.sum())
    return {
        'pct_cesped': round(float(cesped.mean() * 100.0), 2),
        'riqueza': None if riq is None else round(riq, 3),
        'bloques_terreno': nb,
        'varianza_local': round(float(sd[terreno].mean()), 4) if terreno.any() else None,
        'bandas_blancas': bandas_blancas(claro, verde),
        'pared_lisa': round(float((sd[roca] < 0.02).mean() * 100.0), 1) if n_roca else None,
        'pct_roca': round(n_roca * 100.0 / roca.size, 2),
        'pct_azul': round(float(azul.mean() * 100.0), 2),
    }


def siluetas(cam, arboles, d0=20.0, d1=120.0, semiangulo=30.0):
    loc = np.array(cam['loc'][:2], float); tgt = np.array(cam['tgt'][:2], float)
    d = tgt - loc
    if np.linalg.norm(d) < 1e-6:
        return None
    d /= np.linalg.norm(d)
    cos_min = math.cos(math.radians(semiangulo))
    n = 0
    for a in arboles:
        if a['tipo'] not in ARBOLES:
            continue
        v = np.array(a['xyz'][:2], float) - loc
        dist = np.linalg.norm(v)
        if dist < d0 or dist > d1:
            continue
        if float(v.dot(d)) / dist >= cos_min:
            n += 1
    return n


def es_piloto(nombre):
    return '_piloto' in nombre or '_postal' in nombre


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dirs', nargs='+')
    ap.add_argument('--camaras')
    ap.add_argument('--arboles')
    ap.add_argument('--out')
    ap.add_argument('--solo', default='')
    A = ap.parse_args()
    dirs = [os.path.abspath(d) for d in A.dirs]
    padre = os.path.dirname(dirs[0])
    out = A.out or os.path.join(padre, 'medidas.json')
    cams_path = A.camaras or (os.path.join(padre, 'camaras.json') if os.path.exists(os.path.join(padre, 'camaras.json')) else None)
    cams = {k: v for k, v in json.load(open(cams_path, encoding='utf-8')).items() if not k.startswith('_')} if cams_path else {}
    solo = [p for p in A.solo.split(',') if p]
    R = {'_meta': {'fecha': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'dirs': dirs, 'camaras': cams_path, 'arboles': {}},
         '_doc': {l.split()[0]: l.strip() for l in __doc__.splitlines() if l.startswith('  ') and l.split() and l.split()[0] in METRICAS}}
    for d in dirs:
        clave = os.path.basename(d)
        arb_path = A.arboles or (os.path.join(d, 'arboles.json') if os.path.exists(os.path.join(d, 'arboles.json')) else None)
        arboles = json.load(open(arb_path, encoding='utf-8')) if arb_path else None
        R['_meta']['arboles'][clave] = arb_path
        res = {}
        for f in sorted(os.listdir(d)):
            if not f.endswith('.png') or f.startswith(('AB_', 'hoja_')):
                continue
            toma = f[:-4]
            if solo and not toma.startswith(tuple(solo)):
                continue
            m = medir_imagen(os.path.join(d, f))
            m['siluetas_20_120'] = siluetas(cams[toma], arboles) if (arboles is not None and toma in cams and es_piloto(toma)) else None
            res[toma] = m
            print('%-14s %-32s cesped %5.1f%%  riqueza %s  var %s  bandas %d  pared_lisa %s (roca %4.1f%%)  azul %4.1f%%  siluetas %s' % (
                clave[:14], toma, m['pct_cesped'], m['riqueza'], m['varianza_local'], m['bandas_blancas'], m['pared_lisa'],
                m['pct_roca'], m['pct_azul'], m['siluetas_20_120']))
        R[clave] = res
    claves = [os.path.basename(d) for d in dirs]
    R['_resumen'] = {}
    for c in claves:
        for grupo, sel in (('piloto', es_piloto), ('aereas', lambda n: not es_piloto(n))):
            tomas = [t for t in R[c] if sel(t)]
            med = {}
            for k in METRICAS:
                vals = [R[c][t][k] for t in tomas if R[c][t].get(k) is not None]
                med[k] = round(float(np.mean(vals)), 3) if vals else None
            med['n_tomas'] = len(tomas)
            R['_resumen'].setdefault(c, {})[grupo] = med
    if len(claves) == 2:
        a, b = claves
        R['_delta'] = {}
        for t in sorted(set(R[a]) & set(R[b])):
            R['_delta'][t] = {k: (round(R[b][t][k] - R[a][t][k], 3) if (R[a][t].get(k) is not None and R[b][t].get(k) is not None) else None)
                              for k in METRICAS}
    json.dump(R, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('OK medidas ->', out, '| resumen:', json.dumps(R['_resumen'], ensure_ascii=False))


if __name__ == '__main__':
    main()
