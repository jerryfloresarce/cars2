# -*- coding: utf-8 -*-
"""rejilla_ks.py (v3) - elige ksAmbient/ksDiffuse y el peso de cada modo en el ajuste de las texturas con la simulacion
de VISTAS (simular_vistas.py). Para cada combinacion (ksDiffuse, cociente ksAmbient/ksDiffuse, pesos del ajuste)
recalibra TODAS las texturas (color_ac.calibrar_todos) y simula las 6 vistas de ajuste (a media resolucion) en los
modos gamma (ac), lineal ACES (lcs), lineal sRGB + Yebis (lcsy) y la configuracion estimada del amigo (captura).
v3 (revisor): el coste incluye la configuracion estimada de la captura, la unica anclada a datos reales, y el modo
gamma de Kunos ya no pesa 0.6. Coste = suma con pesos W_COSTE de [dE + 25*(croma fuera de [0.9, 1.15]) +
25*(contraste fuera de [0.9, 1.2])]; las vistas de control se calculan aparte y no deciden nada.
  python 03_blender/_rev/color_ac/rejilla_ks.py [--rapido]      -> rejilla_ks.md / rejilla_ks.json
"""
import itertools
import json
import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import simular_vistas as S  # noqa: E402

C = S.C
DIFUSAS = ('asfalto', 'pintura_vial', 'terreno', 'roca', 'edificio', 'pintado', 'vegetacion', 'metal', 'agua', 'luz')
KD = (0.45, 0.50, 0.55, 0.60)
RATIO = (0.7, 0.75, 0.8, 0.9, 1.0, 1.25)
PESOS_AJUSTE = {'A': {'ac': 0.6, 'cap': 0.0, 'lcs': 0.2, 'lcsy': 0.2},
                'B': {'ac': 0.4, 'cap': 0.2, 'lcs': 0.2, 'lcsy': 0.2}}
MODOS = ('ac', 'lcs', 'lcsy', 'captura')
W_COSTE = {'ac': 0.3, 'captura': 0.3, 'lcs': 0.2, 'lcsy': 0.2}
CFG = json.load(open(S.CAPTURA_CFG, encoding='utf-8'))


def fuera(x, lo, hi):
    return max(0.0, lo - x) + max(0.0, x - hi)


def con_parametros(kd, ratio, pesos, fn):
    """Ejecuta fn() con las props de las familias difusas y los pesos del ajuste cambiados (y los restaura)."""
    orig = {f: C.FAMILIAS[f]['props'] for f in C.FAMILIAS}
    orig_pm = dict(C.PESO_MODOS)
    try:
        for f in DIFUSAS:
            p = list(C.FAMILIAS[f]['props'])
            p[0], p[1] = round(kd * ratio, 3), kd
            C.FAMILIAS[f]['props'] = tuple(p)
        C.PESO_MODOS.clear()
        C.PESO_MODOS.update(pesos)
        C._escalas.clear()
        return fn()
    finally:
        for f, p in orig.items():
            C.FAMILIAS[f]['props'] = p
        C.PESO_MODOS.clear()
        C.PESO_MODOS.update(orig_pm)
        C._escalas.clear()


def medir(datos, tab, antes=None):
    """{modo: {'deltaE', 'croma', 'contraste', 'peor_que_antes'}} medias sobre las vistas de `datos`."""
    r = {}
    for modo in MODOS:
        de, cr, st, peor = [], [], [], 0
        for v, d in datos.items():
            img, _ = S.simular_modo(d, modo, *tab, cfg=CFG)
            c, cb = S.cifras(img, d), S.cifras(d['ref'], d)
            de.append(c['deltaE_con_blender'])
            cr.append(c['croma_media'] / cb['croma_media'])
            st.append(c['contraste_lum_std'] / cb['contraste_lum_std'])
            if antes is not None and c['deltaE_con_blender'] > antes[modo][v] + 0.05:
                peor += 1
        r[modo] = {'deltaE': round(float(np.mean(de)), 2), 'croma': round(float(np.mean(cr)), 3),
                   'contraste': round(float(np.mean(st)), 3), 'vistas': dict(zip(datos, [round(x, 2) for x in de])),
                   'peor_que_antes': peor}
    r['coste'] = round(sum(W_COSTE[m] * r[m]['deltaE'] for m in MODOS) + 25 * sum(
        W_COSTE[m] * (fuera(r[m]['croma'], 0.9, 1.15) + fuera(r[m]['contraste'], 0.9, 1.2)) for m in MODOS), 2)
    return r


def antes_por_vista(datos):
    tab = S.tablas('antes')
    return {m: {v: S.cifras(S.simular_modo(d, m, *tab, cfg=CFG)[0], d)['deltaE_con_blender'] for v, d in datos.items()}
            for m in MODOS}


def main():
    rapido = '--rapido' in sys.argv
    aj = {v: S.cargar(v, escala=2) for v in S.META['ajuste']}
    co = {v: S.cargar(v, escala=2) for v in S.META['control']}
    a_aj, a_co = antes_por_vista(aj), antes_por_vista(co)
    filas = []
    kds, ratios = ((0.45, 0.50), (0.9, 1.0, 1.25)) if rapido else (KD, RATIO)
    t0 = time.time()
    for kd, ratio, pk in itertools.product(kds, ratios, PESOS_AJUSTE):
        def fn():
            infos = S.calibrados()
            tab = S.tablas('despues', infos)
            return medir(aj, tab, a_aj), medir(co, tab, a_co)
        r, rc = con_parametros(kd, ratio, PESOS_AJUSTE[pk], fn)
        filas.append({'ksDiffuse': kd, 'ksAmbient': round(kd * ratio, 3), 'cociente': ratio, 'pesos_ajuste': pk,
                      'ajuste': r, 'control': rc})
        print('%.2f %.3f %s coste %.2f (control %.2f) | %s [%.0fs]' % (
            kd, kd * ratio, pk, r['coste'], rc['coste'],
            ' '.join('%s %.2f/%.2f' % (m, r[m]['deltaE'], rc[m]['deltaE']) for m in MODOS), time.time() - t0))
    filas.sort(key=lambda f: f['ajuste']['coste'])
    d = {'antes_ajuste': a_aj, 'antes_control': a_co, 'filas': filas, 'n_ajuste': len(aj), 'n_control': len(co)}
    json.dump(d, open(os.path.join(AQUI, 'rejilla_ks.json'), 'w', encoding='utf-8'), indent=1)
    escribir_md(d)
    print('mejor:', {k: v for k, v in filas[0].items() if k not in ('ajuste', 'control')}, filas[0]['ajuste']['coste'])


def escribir_md(d):
    """rejilla_ks.md desde rejilla_ks.json (python rejilla_ks.py --md lo rehace sin recalcular)."""
    a_aj, a_co, filas = d['antes_ajuste'], d['antes_control'], d['filas']
    na, nc = d.get('n_ajuste', len(a_aj['ac'])), d.get('n_control', len(a_co['ac']))
    t = ['# Rejilla de ksAmbient / ksDiffuse y pesos del ajuste (color_ac v3)', '',
         'Cada fila recalibra todas las texturas y simula las %d vistas de ajuste y las %d de control a media resolucion. '
         'dE = deltaE Lab medio frente a Blender (ajuste / control). Coste (solo vistas de ajuste) = %s x [dE + 25 x '
         '(croma fuera de 0.9-1.15) + 25 x (contraste fuera de 0.9-1.2)]. Pesos del ajuste de texturas: %s. '
         '"peores" = vistas (de %d) que quedan peor que con el KN5 de antes.' % (na, nc, W_COSTE, PESOS_AJUSTE, na + nc), '',
         'ANTES (dE ajuste / control): ' + ', '.join('%s %.2f / %.2f' % (m, np.mean(list(a_aj[m].values())),
                                                                      np.mean(list(a_co[m].values()))) for m in MODOS),
         '', '| ksDiffuse | ksAmbient | cociente | pesos | ' + ' | '.join('%s dE aj/ctrl, peores' % m for m in MODOS)
         + ' | coste aj / ctrl |', '|' + '---|' * (5 + len(MODOS))]
    for f in filas:
        a, c = f['ajuste'], f['control']
        t.append('| %.2f | %.3f | %.2f | %s | %s | %.2f / %.2f |' % (
            f['ksDiffuse'], f['ksAmbient'], f['cociente'], f['pesos_ajuste'],
            ' | '.join('%.2f / %.2f, %d' % (a[m]['deltaE'], c[m]['deltaE'], a[m]['peor_que_antes'] + c[m]['peor_que_antes'])
                       for m in MODOS), a['coste'], c['coste']))
    coste = lambda kd, ka, pk='A': next((f['ajuste']['coste'] for f in filas if abs(f['ksDiffuse'] - kd) < 1e-6  # noqa
                                         and abs(f['ksAmbient'] - ka) < 2e-3 and f['pesos_ajuste'] == pk), float('nan'))
    r125 = [f['ajuste']['coste'] for f in filas if abs(f['cociente'] - 1.25) < 1e-6 and f['pesos_ajuste'] == 'A']
    elegido = C.FAMILIAS['terreno']['props'][:2]
    t += ['', 'Eleccion: ksAmbient %.2f / ksDiffuse %.2f (cociente %.2f), coste %.2f. Mejor fila: %.2f / %.2f, coste %.2f. '
          'El minimo es plano y esta en cociente < 1: con la configuracion estimada del amigo en el coste, un ksAmbient bajo '
          'es lo que da volumen. Cociente 1, como propuso el revisor: 0.50 / 0.50 %.2f y 0.60 / 0.60 %.2f; cociente 1.25 '
          '(v2): %.2f-%.2f. Pesos B (meter la configuracion estimada en el ajuste de las texturas, coste %.2f con 0.45/0.60): '
          'peor en todos los modos, tambien en ella, porque su bruma no cabe en las caras de referencia. ksDiffuse 0.60 es '
          'el tope del 0.4-0.6 de CSP y ksAmbient 0.45 queda entre el 0.40 de AcTools/ksEditor y el minimo.' % (
              elegido[0], elegido[1], elegido[0] / elegido[1], coste(elegido[1], elegido[0]), filas[0]['ksAmbient'],
              filas[0]['ksDiffuse'], filas[0]['ajuste']['coste'], coste(0.50, 0.50), coste(0.60, 0.60), min(r125),
              max(r125), coste(0.60, 0.45, 'B')),
          '', 'Las demas elecciones (exposicion de los modos lineales en el ajuste, guarda de regresion, suelo de croma, '
          'familias del asfalto y del agua) estan en decisiones_v3.md, con la misma simulacion.']
    open(os.path.join(AQUI, 'rejilla_ks.md'), 'w', encoding='utf-8').write('\n'.join(t) + '\n')


if __name__ == '__main__':
    if '--md' in sys.argv:
        escribir_md(json.load(open(os.path.join(AQUI, 'rejilla_ks.json'), encoding='utf-8')))
    else:
        main()
