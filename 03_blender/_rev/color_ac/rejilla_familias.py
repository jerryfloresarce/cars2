# -*- coding: utf-8 -*-
"""rejilla_familias.py (v3) - comprueba ksAmbient/ksDiffuse POR FAMILIA (ksDiffuse de la familia fijo, 0.60;
ksAmbient = ksDiffuse x cociente) con la simulacion de las vistas de ajuste: para cada familia y cociente recalibra las
texturas y mide el deltaE Lab medio frente a Blender SOLO en los pixeles de esa familia, con los pesos del coste de
rejilla_ks.py (0.3 gamma + 0.2 lineal ACES + 0.2 lineal Yebis + 0.3 configuracion estimada del amigo).
  python 03_blender/_rev/color_ac/rejilla_familias.py   -> rejilla_familias.md / .json
"""
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import simular_vistas as S  # noqa: E402

C = S.C
RATIOS = (0.6, 0.7, 0.75, 0.8, 0.9, 1.0)
W = {'ac': 0.3, 'lcs': 0.2, 'lcsy': 0.2, 'captura': 0.3}
CFG = json.load(open(S.CAPTURA_CFG, encoding='utf-8'))


def main():
    datos = {v: S.cargar(v, escala=2) for v in S.META['ajuste']}
    fam_mat = np.array([C.familia(m['name']) for m in S.MATS])
    orig = {f: C.FAMILIAS[f]['props'] for f in C.FAMILIAS}
    res = {}
    for fam in C.FAMILIAS:
        n = sum(int((d['valido'] & (fam_mat[d['idx']] == fam)).sum()) for d in datos.values())
        if n < 2000:
            continue
        res[fam] = {'pixeles': n}
        for r in RATIOS:
            p = list(orig[fam])
            p[0], p[1] = round(orig[fam][1] * r, 3), orig[fam][1]
            C.FAMILIAS[fam]['props'] = tuple(p)
            C._escalas.clear()
            tab = S.tablas('despues', S.calibrados())
            de = {}
            for modo in W:
                acc, npx = 0.0, 0
                for d in datos.values():
                    img, _ = S.simular_modo(d, modo, *tab, cfg=CFG)
                    m = d['valido'] & (fam_mat[d['idx']] == fam)
                    acc += float(np.linalg.norm(C.lab(img[m]) - C.lab(d['ref'][m]), axis=-1).sum())
                    npx += int(m.sum())
                de[modo] = round(acc / max(npx, 1), 2)
            de['coste'] = round(sum(W[k] * de[k] for k in W), 2)
            res[fam]['%.2f' % r] = de
            print(fam, r, de)
        C.FAMILIAS[fam]['props'] = orig[fam]
        C._escalas.clear()
    json.dump(res, open(os.path.join(AQUI, 'rejilla_familias.json'), 'w', encoding='utf-8'), indent=1)
    escribir_md(res, len(datos))


def escribir_md(res, n_vistas):
    t = ['# ksAmbient/ksDiffuse por familia (ksDiffuse fijo, ksAmbient = ksDiffuse x cociente)', '',
         'deltaE Lab medio frente a Blender en los pixeles de cada familia (%d vistas de ajuste); coste = %s. '
         'Generado por rejilla_familias.py.' % (n_vistas, W), '',
         '| familia | pixeles | ' + ' | '.join('ksA/ksD %.2f (gamma/ACES/Yebis/amigo -> coste)' % r for r in RATIOS)
         + ' | mejor |', '|' + '---|' * (len(RATIOS) + 3)]
    ganancia = {}
    elegido = C.FAMILIAS['terreno']['props'][0] / C.FAMILIAS['terreno']['props'][1]
    for fam, x in res.items():
        celdas = ['%.1f/%.1f/%.1f/%.1f -> %.2f' % (x['%.2f' % r]['ac'], x['%.2f' % r]['lcs'], x['%.2f' % r]['lcsy'],
                                                    x['%.2f' % r]['captura'], x['%.2f' % r]['coste']) for r in RATIOS]
        mejor = min(RATIOS, key=lambda r: x['%.2f' % r]['coste'])
        ganancia[fam] = round(x['%.2f' % elegido]['coste'] - x['%.2f' % mejor]['coste'], 2)
        t.append('| %s | %d | %s | %.2f |' % (fam, x['pixeles'], ' | '.join(celdas), mejor))
    t += ['', 'El mejor cociente por familia va de %.2f a %.2f, pero frente al %.2f comun la ganancia es de %.2f como '
          'mucho (%s), asi que todas las familias llevan el mismo.' % (
              min(min(RATIOS, key=lambda r: x['%.2f' % r]['coste']) for x in res.values()),
              max(min(RATIOS, key=lambda r: x['%.2f' % r]['coste']) for x in res.values()), elegido,
              max(ganancia.values()), ', '.join('%s %.2f' % kv for kv in ganancia.items()))]
    open(os.path.join(AQUI, 'rejilla_familias.md'), 'w', encoding='utf-8').write('\n'.join(t) + '\n')
    print('\n'.join(t))


if __name__ == '__main__':
    if '--md' in sys.argv:
        escribir_md(json.load(open(os.path.join(AQUI, 'rejilla_familias.json'), encoding='utf-8')), len(S.META['ajuste']))
    else:
        main()
