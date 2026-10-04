# -*- coding: utf-8 -*-
"""tiempos_captura.py - prueba si algun TIEMPO de Kunos (presets del SDK: tabla de newksEditor src/lighting.js, en
color_ac.TIEMPOS_AC y aqui los de niebla y nubes cubiertas) explica la captura del amigo SIN parametros inventados, con
el KN5 de antes (texturas ANTES) en la vista 'captura'. Para cada tiempo se prueba el brillo (Page Up / Page Down del
juego: multiplicador de la exposicion) y la saturacion del filtro, y se da el mejor ajuste a las cifras de la captura
(las mismas de ajuste_captura.py: luminancia media, saturacion media y color del asfalto).
Resultado (tiempos_captura.json): ningun tiempo de Kunos la reproduce con el brillo por defecto; los que mas se
acercan necesitan SUBIR el brillo, y el usuario dice que el amigo lo BAJO. La configuracion estimada de
ajuste_captura.py (estilo de WeatherFX con mucho ambiente y bruma) sigue siendo la que mejor encaja.
  python 03_blender/_rev/color_ac/tiempos_captura.py
"""
import itertools
import json
import math
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import ajuste_captura as AJ  # noqa: E402
import simular_vistas as S  # noqa: E402

C = S.C
EXTRA = {   # (angleGamma, sol LOW, sol HIGH, ambiente LOW, ambiente HIGH, niebla, blend, distancia) de lighting.js
    '1_heavy_fog': (2, (229.5, 168.3, 86.7, 0), (170, 170, 160, 0), (160, 150, 140, 10), (140, 150, 155, 10.8),
                    (4.25, 4.25, 4.25), 1.0, 2000.0),
    '6_mid_clouds': (2.8, (0, 0, 0, 0), (0, 0, 0, 0), (140, 140, 140, 9), (140, 140, 140, 11), (1.45, 1.55, 1.65), 0.8,
                     12000.0),
    '7_heavy_clouds': (2, (0, 0, 0, 0), (0, 0, 0, 0), (140, 130, 120, 6), (140, 140, 140, 8), (1.1, 1.1, 1.1), 0.8,
                       12000.0),
}


def tiempos():
    t = dict(C.TIEMPOS_AC)
    for k, (ag, sl, sh, al, ah, fog, bl, di) in EXTRA.items():
        t[k] = (C._curva_tiempo(ag, sl, sh), C._curva_tiempo(ag, al, ah), (np.array(fog), bl, di))
    return t


def simular(d, tab, luz, brillo, sat, cielo_obj):
    """Imagen sRGB 0..1 con un tiempo de Kunos (el cielo se fija al de la captura: no es nuestro material)."""
    sol, amb, nie = luz
    col, pr = tab
    tx = S.textura(d, col)
    p = pr[d['idx']]
    sky = np.full(3, 3.0)
    for _ in range(4):
        esc = C.escena_ac(tx, p[..., 0], p[..., 1], d['nl'], p[..., 2], p[..., 3], d['nh'], p[..., 4], sol=sol, amb=amb,
                          distancia=d['dist'], niebla=nie)
        esc[d['cielo']] = sky
        e = C.autoexposicion_ac(float(np.mean(C.luminancia(esc)))) * brillo
        sky = C.saturar(C.tonemap_ac_inv(np.asarray(cielo_obj) / 255.0), 1.0 / sat) / e
    return C.pantalla_ac(esc, e, sat)


def main():
    d = S.cargar('captura', escala=2)
    h, w = d['ref'].shape[:2]
    cap = np.asarray(Image.open(os.path.join(AQUI, 'captura_juego.png')).convert('RGB').resize((w, h), Image.LANCZOS))
    obj = AJ.zonas(cap.astype(np.float64) / 255.0, h, w)
    tab = S.tablas('antes')
    r = lambda z: {k: (np.round(v, 1).tolist() if isinstance(v, list) else round(v, 3)) for k, v in z.items()}  # noqa
    out = {'captura': r(obj), 'tiempos': {}}
    for nom, luz in tiempos().items():
        filas = []
        for b, s in itertools.product((0.5, 0.7, 1.0, 1.4, 2.0, 2.8), (0.95, 0.7, 0.5)):
            z = AJ.zonas(simular(d, tab, luz, b, s, obj['cielo']), h, w)
            filas.append((AJ.coste(z, obj), b, s, z))
        defecto = next(f for f in filas if f[1] == 1.0 and f[2] == 0.95)
        mejor = min(filas, key=lambda f: f[0])
        out['tiempos'][nom] = {'por_defecto': dict(r(defecto[3]), coste=round(defecto[0], 1)),
                               'mejor': dict(r(mejor[3]), coste=round(mejor[0], 1), brillo=mejor[1], saturacion=mejor[2])}
        print('%-15s defecto: lum %.0f sat %.3f asfalto %s coste %.0f | mejor: brillo x%.1f sat %.2f -> lum %.0f sat %.3f '
              'asfalto %s coste %.1f' % (nom, defecto[3]['lum_media'], defecto[3]['saturacion_media'],
                                         np.round(defecto[3]['asfalto']).astype(int), defecto[0], mejor[1], mejor[2],
                                         mejor[3]['lum_media'], mejor[3]['saturacion_media'],
                                         np.round(mejor[3]['asfalto']).astype(int), mejor[0]))
    cfg = json.load(open(S.CAPTURA_CFG, encoding='utf-8'))
    out['config_estimada'] = {'coste': cfg['coste'], 'parametros': 4, 'brillo': cfg['brillo']}
    json.dump(out, open(os.path.join(AQUI, 'tiempos_captura.json'), 'w', encoding='utf-8'), indent=1)
    print('captura:', r(obj), '| configuracion estimada (4 parametros): coste', cfg['coste'])


if __name__ == '__main__':
    main()
