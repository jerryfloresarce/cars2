# -*- coding: utf-8 -*-
"""decisiones_v3.py - recalcula con la simulacion de vistas (media resolucion) las elecciones de color_ac v3 que no son
ksAmbient/ksDiffuse (esas: rejilla_ks.py): exposicion de los modos lineales en el ajuste (EXPO_LCS_AJUSTE), guarda de
regresion (PESO_REGRESION, MARGEN_REGRESION), suelo de croma (CROMA_MIN) y las familias del asfalto y del agua. Cada fila cambia SOLO
ese parametro, recalibra todas las texturas y mide las 7 vistas de ajuste y las 3 de control en 5 modos.
  python 03_blender/_rev/color_ac/decisiones_v3.py   -> decisiones_v3.md / decisiones_v3.json
"""
import copy
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import rejilla_ks as RK  # noqa: E402

S, C = RK.S, RK.C
RK.MODOS = ('ac', 'lcs', 'lcsy', 'captura', 'nubes')
RK.W_COSTE['nubes'] = 0.0
AGUA = copy.deepcopy(C.FAMILIAS['agua'])
ASF = copy.deepcopy(C.FAMILIAS['asfalto'])
PRUEBAS = [
    ('elegido (v3)', {}),
    ('EXPO_LCS_AJUSTE 0.59/0.92 (la v2)', {'EXPO_LCS_AJUSTE': {'lcs': 0.59, 'lcsy': 0.92}}),
    ('EXPO_LCS_AJUSTE 0.66/0.66 (autoexposicion real)', {'EXPO_LCS_AJUSTE': {'lcs': 0.66, 'lcsy': 0.66}}),
    ('EXPO_LCS_AJUSTE 0.91/1.33 (punto fijo de nivel)', {'EXPO_LCS_AJUSTE': {'lcs': 0.91, 'lcsy': 1.33}}),
    ('sin guarda de regresion', {'PESO_REGRESION': 0.0}),
    ('guarda 40 / margen 0', {'PESO_REGRESION': 40.0, 'MARGEN_REGRESION': 0.0}),
    ('suelo de croma 0.85', {'CROMA_MIN': 0.85}),
    ('asfalto sin pesos ni margen propios', {'asfalto': {k: v for k, v in ASF.items() if k not in ('pesos', 'margen')}}),
    ('asfalto con margen 3.0', {'asfalto': dict(ASF, margen=3.0)}),
    ('agua sin croma_lineal propio', {'agua': {k: v for k, v in AGUA.items() if k not in ('pesos', 'croma_lineal')}}),
    ('agua con pesos 0.7/0.15/0.15', {'agua': dict(AGUA, pesos={'ac': 0.7, 'cap': 0.0, 'lcs': 0.15, 'lcsy': 0.15})}),
    ('agua con pesos 0.8/0.1/0.1 y croma_lineal 1.6', {'agua': dict(AGUA, pesos={'ac': 0.8, 'cap': 0.0, 'lcs': 0.1,
                                                                                   'lcsy': 0.1}, croma_lineal=1.6)}),
]


def por_material(datos, tab):
    """Suma de deltaE por material y modo (bincount) y pixeles por material en `datos`."""
    n = len(S.MATS)
    sumas, pix = {m: np.zeros(n) for m in RK.MODOS}, np.zeros(n)
    for d in datos.values():
        val = d['valido']
        ref = C.lab(d['ref'])
        pix += np.bincount(d['idx'][val], minlength=n)
        for m in RK.MODOS:
            img, _ = S.simular_modo(d, m, *tab, cfg=RK.CFG)
            de = np.linalg.norm(C.lab(img) - ref, axis=-1)[val]
            sumas[m] += np.bincount(d['idx'][val], weights=de, minlength=n)
    return sumas, pix


def lastre(s_d, s_a, pix):
    """Por modo: (materiales con > 1500 px de media 2 dE peor que antes, empeoramiento medio por pixel de todos)."""
    big = pix > 1500
    return {m: (int((((s_d[m] - s_a[m]) / np.maximum(pix, 1)) > 2.0)[big].sum()),
                round(float(np.maximum(s_d[m] - s_a[m], 0)[big].sum() / pix[big].sum()), 2)) for m in RK.MODOS}


def main():
    aj = {v: S.cargar(v, escala=2) for v in S.META['ajuste']}
    co = {v: S.cargar(v, escala=2) for v in S.META['control']}
    a_aj, a_co = RK.antes_por_vista(aj), RK.antes_por_vista(co)
    iw = S.S_NOM.index('MAT_agua')
    todas = dict(aj, **co)
    s_a, pix = por_material(todas, S.tablas('antes'))
    filas = []
    for nombre, cambios in PRUEBAS:
        viejo = {k: copy.deepcopy(getattr(C, k)) for k in cambios if k not in C.FAMILIAS}
        for k, v in cambios.items():
            if k in C.FAMILIAS:
                C.FAMILIAS[k] = copy.deepcopy(v)
            else:
                setattr(C, k, v)
        C._escalas.clear()
        try:
            infos = S.calibrados()
            tab = S.tablas('despues', infos)
            r, rc = RK.medir(aj, tab, a_aj), RK.medir(co, tab, a_co)
            las = lastre(por_material(todas, tab)[0], s_a, pix)
            agua = (np.array(infos[iw]['tx_ac']) * 255).round().astype(int).tolist()
        finally:
            for k, v in viejo.items():
                setattr(C, k, v)
            C.FAMILIAS['agua'] = copy.deepcopy(AGUA)
            C.FAMILIAS['asfalto'] = copy.deepcopy(ASF)
            C._escalas.clear()
        filas.append({'prueba': nombre, 'ajuste': r, 'control': rc, 'textura_agua': agua, 'lastre': las})
        print(nombre, r['coste'], ' '.join('%s %.2f/%.2f' % (m, r[m]['deltaE'], rc[m]['deltaE']) for m in RK.MODOS),
              flush=True)
    json.dump(filas, open(os.path.join(AQUI, 'decisiones_v3.json'), 'w', encoding='utf-8'), indent=1)
    t = ['# Decisiones de color_ac v3 (simulacion de vistas, media resolucion)', '',
         'Cada fila cambia un solo parametro respecto al elegido. dE = deltaE Lab medio frente a Blender, ajuste / '
         'control; "peores" = vistas (de %d) peor que con el KN5 de antes; "mat" = materiales (de los que tienen mas de '
         '1500 px) que quedan mas de 2 dE peor que antes y, entre parentesis, el empeoramiento medio por pixel. Coste como '
         'en rejilla_ks.md (sin nubes).' % (len(aj) + len(co)), '',
         '| prueba | ' + ' | '.join('%s dE, peores, mat' % m for m in RK.MODOS) + ' | coste | textura del agua |',
         '|' + '---|' * (len(RK.MODOS) + 3)]
    for f in filas:
        a, c = f['ajuste'], f['control']
        t.append('| %s | %s | %.2f | %s |' % (f['prueba'], ' | '.join(
            '%.2f / %.2f, %d, %d (%.2f)' % (a[m]['deltaE'], c[m]['deltaE'], a[m]['peor_que_antes'] + c[m]['peor_que_antes'],
                                           f['lastre'][m][0], f['lastre'][m][1])
            for m in RK.MODOS), a['coste'], f['textura_agua']))
    open(os.path.join(AQUI, 'decisiones_v3.md'), 'w', encoding='utf-8').write('\n'.join(t) + '\n')


if __name__ == '__main__':
    main()
