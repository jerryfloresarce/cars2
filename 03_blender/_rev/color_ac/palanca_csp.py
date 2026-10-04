# -*- coding: utf-8 -*-
"""palanca_csp.py - efecto simulado de la PALANCA de ext_config.ini ([MATERIAL_ADJUSTMENT_0], solo con CSP): mismas
texturas del KN5 calibrado, pero ksAmbient/ksDiffuse cambiados en todo el circuito. Media de las 7 vistas de ajuste
(media resolucion) en cada modo. Sin CSP la palanca no se lee, asi que el modo 'ac' solo cuenta para CSP con estilo
gamma.
  python 03_blender/_rev/color_ac/palanca_csp.py   -> palanca_csp.json
"""
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import simular_vistas as S  # noqa: E402

C = S.C
MODOS = ('ac', 'lcs', 'lcsy', 'captura', 'captura1', 'nubes2')
PRUEBAS = {'KN5 (0.45/0.60)': None, 'palanca 0.30/0.55 (la del ext_config)': (0.30, 0.55), 'palanca 0.25/0.50': (0.25, 0.50)}


def main():
    cfg = json.load(open(S.CAPTURA_CFG, encoding='utf-8'))
    datos = {v: S.cargar(v, escala=2) for v in S.META['ajuste']}
    col, pr = S.tablas('despues', S.calibrados())
    out = {}
    for nom, ks in PRUEBAS.items():
        p = pr.copy()
        if ks:
            p[:, 0], p[:, 1] = ks
        out[nom] = {m: round(float(np.mean([S.cifras(S.simular_modo(d, m, col, p, cfg=cfg)[0], d)['deltaE_con_blender']
                                            for d in datos.values()])), 2) for m in MODOS}
        print(nom, out[nom])
    json.dump(out, open(os.path.join(AQUI, 'palanca_csp.json'), 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
