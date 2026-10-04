# -*- coding: utf-8 -*-
"""ajuste_captura.py - ESTIMA la configuracion de juego del amigo a partir de su captura (captura_juego.png, recorte
de captura_usuario.webp sin las bandas negras). No sabemos si usa CSP, que estilo de tiempo ni que filtro: aqui se
ajustan 4 parametros de un modelo de AC en espacio gamma con iluminacion de WeatherFX (sol de mediodia blanco) y
bruma, con las texturas ANTES (el KN5 que tiene), en la vista 'captura' (mismo encuadre aproximado):
  ambiente   multiplicador del ambiente de 3_clear (las sombras de la captura casi no se ven)
  brillo     multiplicador de la exposicion (el amigo dice que bajo el brillo: "antes era peor")
  bruma      distancia (m) de la bruma hacia el color del cielo de la captura
  saturacion la del filtro de post-proceso (0.95 en el filtro por defecto de AC)
Cifras que se igualan (zona de juego sin coche ni HUD): luminancia media, saturacion media, color medio del
asfalto (dos cajas a los lados del coche) y del cielo (caja arriba a la derecha). La geometria de la captura es
la de la version del 02/10 (la montana-coche era otra), asi que se comparan cifras por zonas, no pixeles.
  python 03_blender/_rev/color_ac/ajuste_captura.py   -> config_captura.json (lo usa simular_vistas.py)
"""
import itertools
import json
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import simular_vistas as S  # noqa: E402

C = S.C
CAJAS = {'cielo': (0.62, 0.00, 0.80, 0.07), 'asfalto_i': (0.05, 0.62, 0.33, 0.86),
         'asfalto_d': (0.67, 0.62, 0.95, 0.86), 'coche': (0.37, 0.40, 0.63, 0.92), 'hud': (0.27, 0.88, 0.73, 1.0)}


def caja(h, w, nombre):
    a0, b0, a1, b1 = CAJAS[nombre]
    m = np.zeros((h, w), bool)
    m[int(b0 * h):int(b1 * h), int(a0 * w):int(a1 * w)] = True
    return m


def zonas(img, h, w):
    """Cifras por zonas de una imagen sRGB 0..1."""
    juego = ~(caja(h, w, 'coche') | caja(h, w, 'hud'))
    x = img[juego]
    sat = (x.max(-1) - x.min(-1)) / np.maximum(x.max(-1), 1e-4)
    asf = img[caja(h, w, 'asfalto_i') | caja(h, w, 'asfalto_d')]
    return {'lum_media': float(C.luminancia(x).mean()) * 255, 'saturacion_media': float(sat.mean()),
            'asfalto': (asf.mean(0) * 255).tolist(), 'cielo': (img[caja(h, w, 'cielo')].mean(0) * 255).tolist(),
            'contraste_lum_std': float(C.luminancia(x).std()) * 255}


def simular(d, tab, ambiente, brillo, dist, cielo_obj, sat=C.PP_SAT):
    """Imagen del modelo 'captura' con el color de bruma que reproduce el cielo de la captura (3 iteraciones)."""
    cfg = {'ambiente': ambiente, 'brillo': brillo, 'distancia_bruma': dist, 'saturacion': sat, 'bruma': [3.0, 3.0, 3.0]}
    for _ in range(3):
        img, e = S.simular_modo(d, 'captura', *tab, cfg=cfg)
        hdr = C.saturar(C.tonemap_ac_inv(np.asarray(cielo_obj) / 255.0), 1.0 / sat) / e
        cfg['bruma'] = [round(float(v), 4) for v in hdr]
    img, e = S.simular_modo(d, 'captura', *tab, cfg=cfg)
    return img, e, cfg


def coste(z, obj):
    return ((z['lum_media'] - obj['lum_media']) / 6.0) ** 2 + ((z['saturacion_media'] - obj['saturacion_media']) / 0.02) ** 2 \
        + (np.linalg.norm(np.subtract(z['asfalto'], obj['asfalto'])) / 6.0) ** 2


def main():
    d = S.cargar('captura', escala=2)
    h, w = d['ref'].shape[:2]
    cap = np.asarray(Image.open(os.path.join(AQUI, 'captura_juego.png')).convert('RGB').resize((w, h), Image.LANCZOS))
    obj = zonas(cap.astype(np.float64) / 255.0, h, w)
    print('captura:', json.dumps({k: (np.round(v, 2).tolist() if isinstance(v, list) else round(v, 3)) for k, v in obj.items()}))
    tab = S.tablas('antes')
    mejor = None
    for amb, bri, dist, sat in itertools.product((1.0, 2.0, 3.0, 4.0, 6.0, 9.0), (0.25, 0.35, 0.5, 0.7, 1.0),
                                                 (100.0, 200.0, 400.0, 800.0, 1600.0, 1e6), (0.4, 0.6, 0.8, 0.95)):
        img, e, cfg = simular(d, tab, amb, bri, dist, obj['cielo'], sat)
        z = zonas(img, h, w)
        c = coste(z, obj)
        if mejor is None or c < mejor[0]:
            mejor = (c, cfg, z, e)
    c0, cfg, z, e = mejor
    for _ in range(2):          # refinado local
        for k, f in (('ambiente', (0.8, 0.9, 1.1, 1.25)), ('brillo', (0.85, 0.93, 1.07, 1.15)),
                     ('distancia_bruma', (0.6, 0.8, 1.25, 1.6)), ('saturacion', (0.85, 0.93, 1.07, 1.15))):
            for fac in f:
                prueba = dict(cfg, **{k: cfg[k] * fac})
                img, e2, cfg2 = simular(d, tab, prueba['ambiente'], prueba['brillo'], prueba['distancia_bruma'],
                                        obj['cielo'], min(prueba['saturacion'], 1.0))
                z2 = zonas(img, h, w)
                c2 = coste(z2, obj)
                if c2 < c0:
                    c0, cfg, z, e = c2, cfg2, z2, e2
    # con el brillo por defecto (antes de que el amigo lo bajara)
    img1, e1 = S.simular_modo(d, 'captura', *tab, cfg=dict(cfg, brillo=1.0))
    z1 = zonas(img1, h, w)
    r = lambda zz: {k: (np.round(v, 1).tolist() if isinstance(v, list) else round(v, 3)) for k, v in zz.items()}  # noqa: E731
    out = dict(cfg, coste=round(c0, 3), exposicion=round(e, 3), captura=r(obj), modelo_antes=r(z),
               modelo_antes_brillo_1=r(z1),
               nota='Estimacion: 4 parametros (ambiente, brillo, distancia de bruma, saturacion; el color de la bruma sale del cielo) ajustados a las cifras de UNA captura (version del 02/10). No es un dato '
                    'de la configuracion real del amigo; sirve para ver como quedaria el DESPUES con algo parecido.')
    json.dump(out, open(os.path.join(AQUI, 'config_captura.json'), 'w', encoding='utf-8'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
