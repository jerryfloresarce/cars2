# -*- coding: utf-8 -*-
"""expo_lcs.py - mide la exposicion de los modos LINEALES de CSP que usa color_ac.py en su ajuste (EXPO_LCS_AJUSTE).
En los estilos lineales la autoexposicion del juego fija el nivel global (cualquier factor comun de las texturas se
compensa), asi que el ajuste NO debe decidir el nivel con esos modos: solo los colores y brillos relativos. Para eso
se usa, en cada modo lineal, la exposicion a la que el nivel medio de las vistas coincide con el de Blender con las
texturas calibradas (luminancia Lab media; media geometrica de las 6 vistas de ajuste). Tambien da la exposicion que
la autoexposicion produce de verdad (simular_vistas.py), antes y despues, para el informe.
  python 03_blender/_rev/color_ac/expo_lcs.py   (repetir hasta que no cambie: el ajuste depende de ella)
"""
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import simular_vistas as S  # noqa: E402

C = S.C


def lin_vista(d, col, pr):
    tx = S.textura(d, col)
    p = pr[d['idx']]
    lin = C.escena_lcs(tx, p[..., 0], p[..., 1], d['nl'], d['nz'], p[..., 2], p[..., 3], d['nh'], p[..., 4])
    lin[d['cielo']] = C.srgb_a_lineal(d['ref'][d['cielo']]) * 2 ** -S.META['exposicion_blender']
    return lin


def main():
    infos = S.calibrados()
    tabs = {'antes': S.tablas('antes'), 'despues': S.tablas('despues', infos)}
    out = {}
    for et, tab in tabs.items():
        for modo, fn in (('lcs', C.pantalla_lcs), ('lcsy', C.pantalla_lcs_yebis)):
            reales, iguales = [], []
            for v in S.META['ajuste']:
                d = S.cargar(v, escala=2)
                lin = lin_vista(d, *tab)
                e_real = C.autoexposicion_lcs(C.luminancia(lin))
                l_b = float(C.lab(d['ref'][d['valido']])[:, 0].mean())
                lo, hi = np.log(0.05), np.log(5.0)
                for _ in range(40):                      # biseccion: L* medio de la vista = el de Blender
                    mid = 0.5 * (lo + hi)
                    l_s = float(C.lab(fn(lin[d['valido']], np.exp(mid)))[:, 0].mean())
                    lo, hi = (mid, hi) if l_s < l_b else (lo, mid)
                reales.append(e_real)
                iguales.append(float(np.exp(0.5 * (lo + hi))))
            out['%s_%s' % (modo, et)] = {'autoexposicion': round(float(np.exp(np.mean(np.log(reales)))), 3),
                                         'igual_a_blender': round(float(np.exp(np.mean(np.log(iguales)))), 3),
                                         'por_vista_igual': [round(x, 3) for x in iguales]}
    out['en_color_ac'] = {'EXPO_LCS_AJUSTE': C.EXPO_LCS_AJUSTE}
    json.dump(out, open(os.path.join(AQUI, 'expo_lcs.json'), 'w', encoding='utf-8'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
