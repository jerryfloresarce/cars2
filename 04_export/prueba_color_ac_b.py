# -*- coding: utf-8 -*-
"""prueba_color_ac_b.py - bloques 6 y 7 de prueba_color_ac.py (roca del terreno, KN5 de prueba y simulacion de vistas).
No se ejecuta solo: lo llama prueba_color_ac.py con su funcion comprobar()."""
import copy
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import color_ac as C  # noqa: E402

REV = os.path.join(AQUI, '..', '03_blender', '_rev', 'color_ac')
MODOS_REF = ('ac', 'lcs', 'lcsy', 'captura')          # los que pueden hacer fallar la prueba
MODOS_ROB = ('nubes', 'nubes2', 'captura1')           # solo se listan
PROTAGONISTA_PX = 50000
MAX_EMPEORA_MAT = 2.3                                  # deltaE CIE76 apenas perceptible
TOL_VISTA = {'ac': 0.0, 'lcs': 0.5, 'lcsy': 0.5, 'captura': 0.5}


def bloque_roca(comprobar):
    pases = os.path.join(REV, '_pases')
    meta = os.path.join(pases, 'vistas.json')
    if not os.path.exists(meta):
        print('  (no hay pases de render_ac.py: se salta)')
        return
    mats = json.load(open(os.path.join(pases, 'materiales_vista.json'), encoding='utf-8'))['materiales']
    it = next(k for k, m in enumerate(mats) if m['name'] == C.ROCA_BASE)
    iguales = total = 0
    vistas = json.load(open(meta, encoding='utf-8'))
    for v in vistas['ajuste'] + vistas['control']:
        a = np.load(os.path.join(pases, '%s_id.npy' % v))
        k = np.load(os.path.join(pases, '%s_msk.npy' % v))
        m = (a[..., 3] > 0.5) & (np.round(a[..., 0] * 1024.0).astype(int) - 1 == it)
        w = C.mascara_roca(k[..., 2][m] * 2.0 - 1.0, k[..., 1][m])
        iguales += int((w == (k[..., 0][m] > 0.5)).sum())
        total += int(m.sum())
    comprobar(total > 0 and iguales / total >= 0.95, 'criterio del writer (N.z < %.2f o roca > %.2f con N.z < %.2f) = mascara de '
              'roca de Blender en el %.1f %% de %d pixeles de terreno' % (C.ROCA_NZ, C.ROCA_ATR, C.ROCA_NZ_LLANO,
                                                                     100.0 * iguales / max(total, 1), total))


def bloque_kn5(comprobar, infos):
    kn5 = os.path.join(AQUI, '_color_ac_prueba', 'porto_corsa_color.kn5')
    if not os.path.exists(kn5):
        print('  (no hay KN5 de prueba: se salta)')
        return
    sys.path.insert(0, os.path.join(AQUI, '_color_ac_prueba'))
    from leer_kn5_color import leer  # noqa: E402
    mats = leer(kn5)
    malos_p = [n for n, m in mats.items()
               if any(abs(m['props'].get(k, -9) - v) > 1e-4 for k, v in C.props_familia(C.familia(n)))]
    comprobar(not malos_p, '%d materiales con las props de su familia (%d distintas: %s)' % (len(mats), len(malos_p), malos_p[:5]))
    comprobar(C.ROCA_MAT in mats and C.ROCA_BASE in mats, 'el KN5 lleva %s y %s' % (C.ROCA_BASE, C.ROCA_MAT))
    planos = {n: m for n, m in mats.items() if m['tex'] and m['tex'].startswith('flat_') and m['media_srgb'] is not None}
    ref = {x['name']: x for x in copy.deepcopy(infos)}
    malos_c = [n for n, m in planos.items() if n in ref and not ref[n]['albedo_fuente'].startswith('diffuse')
               and ref[n]['albedo_fuente'] != 'color del material'
               and np.abs(m['media_srgb'] - np.array(ref[n]['tx_ac']) * 255).max() > 2.5]
    comprobar(len(malos_c) <= 0.05 * len(planos), 'texturas planas con el color calibrado (%d de %d distintas: %s)' % (
        len(malos_c), len(planos), malos_c[:5]))


def bloque_vistas(comprobar):
    vc = os.path.join(REV, 'vistas_cifras.json')
    if not os.path.exists(vc):
        print('  (no hay vistas_cifras.json: se salta)')
        return
    d = json.load(open(vc, encoding='utf-8'))
    vis, res = d['vistas'], d['resumen']
    for modo in MODOS_REF:
        a, b = res['ajuste'][modo + '_antes']['deltaE'], res['ajuste'][modo + '_despues']['deltaE']
        ca, cb = res['control'][modo + '_antes']['deltaE'], res['control'][modo + '_despues']['deltaE']
        pe = {v: (x[modo + '_antes']['deltaE_con_blender'], x[modo + '_despues']['deltaE_con_blender']) for v, x in vis.items()
              if x[modo + '_despues']['deltaE_con_blender'] > x[modo + '_antes']['deltaE_con_blender'] + TOL_VISTA[modo]}
        comprobar(b < a and cb < ca and not pe, 'modo %s: deltaE ajuste %.1f -> %.1f, control %.1f -> %.1f; vistas peor (+%.1f): %s'
                  % (modo, a, b, ca, cb, TOL_VISTA[modo], pe or 'ninguna'))
    for modo in MODOS_ROB:
        if modo + '_antes' in res['ajuste']:
            pe = [v for v, x in vis.items() if x[modo + '_despues']['deltaE_con_blender'] > x[modo + '_antes']['deltaE_con_blender']]
            print('  INFO  %s: deltaE ajuste %.1f -> %.1f, control %.1f -> %.1f; vistas peor: %s' % (
                modo, res['ajuste'][modo + '_antes']['deltaE'], res['ajuste'][modo + '_despues']['deltaE'],
                res['control'][modo + '_antes']['deltaE'], res['control'][modo + '_despues']['deltaE'], pe or 'ninguna'))
    for k, lo, hi in (('croma/blender', 0.85, 1.2), ('std/blender', 0.85, 1.2)):
        x = res['ajuste']['ac_despues'][k]
        comprobar(lo <= x <= hi, 'modo gamma: %s = %.2f (entre %.2f y %.2f)' % (k, x, lo, hi))
    pm = os.path.join(REV, 'materiales_dE.json')
    if os.path.exists(pm):
        acc = {}
        for mats in json.load(open(pm, encoding='utf-8')).values():
            for n, x in mats.items():
                a = acc.setdefault(n, {'pixeles': 0})
                a['pixeles'] += x['pixeles']
                for k, val in x.items():
                    if k != 'pixeles':
                        a[k] = a.get(k, 0.0) + val * x['pixeles']
        prot = {n: a for n, a in acc.items() if a['pixeles'] >= PROTAGONISTA_PX}
        for modo in MODOS_REF:
            pe = {n: (round(a[modo + '_antes'] / a['pixeles'], 1), round(a[modo + '_despues'] / a['pixeles'], 1))
                  for n, a in prot.items() if (a[modo + '_despues'] - a[modo + '_antes']) / a['pixeles'] > MAX_EMPEORA_MAT}
            comprobar(not pe, 'modo %s: ninguno de los %d materiales protagonistas (>= %d px) empeora mas de %.1f: %s' % (
                modo, len(prot), PROTAGONISTA_PX, MAX_EMPEORA_MAT, pe or 'ninguno'))


def bloques(comprobar, infos):
    print('6. roca del terreno y KN5 del writer parcheado')
    bloque_roca(comprobar)
    bloque_kn5(comprobar, infos)
    print('7. simulacion de vistas')
    bloque_vistas(comprobar)
