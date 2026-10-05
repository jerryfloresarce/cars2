# -*- coding: utf-8 -*-
"""hoja_vista.py - hoja A/B "modo AC de Blender (proxy)" vs "como AC leido del KN5" a partir de la salida de kn5_vista.py.

    python 04_export/hoja_vista.py <carpeta_vista> [--nombre hoja_v12_como_ac] [--celda 720x405]

Lee <carpeta_vista>/vista.json (tomas, 'ref_proxy' = la captura del proxy usada por kn5_vista --comparar) y <toma>.png.
Escribe en <carpeta_vista>:
  <nombre>.png            todas las tomas, una fila por toma: izquierda el proxy, derecha la vista del KN5
  <nombre>_piloto.png     solo 49-54 (las de piloto)   y   <nombre>_postales.png   el resto (01, 56, 59...)
  <nombre>.json           cifras por toma: media sRGB8 de cada lado (todo y mitad inferior = suelo/pista), diferencia
                          media absoluta por canal (MAE), diferencia de brillo V y de saturacion S (KN5 - proxy) por tercios
                          horizontales (arriba = cielo/fondo, medio = horizonte, abajo = pista/suelo)
Solo PIL + numpy (sin Blender).
"""
import colorsys
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _fuente(t):
    for f in ('arial.ttf', 'C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, t)
        except OSError:
            pass
    return ImageFont.load_default()


def _hsv_medio(a):
    m = [float(c) for c in a.reshape(-1, 3).mean(0) / 255.0]      # float de python (json no serializa float32)
    h, s, v = colorsys.rgb_to_hsv(*m)
    return int(round(h * 360)), round(s, 3), round(v, 3)


def cifras(ref, kn5):
    r = np.asarray(ref, np.float32)
    k = np.asarray(kn5, np.float32)
    h = r.shape[0]
    out = {'media_proxy': [int(round(v)) for v in r.reshape(-1, 3).mean(0)],
           'media_kn5': [int(round(v)) for v in k.reshape(-1, 3).mean(0)],
           'mae_srgb8': round(float(np.abs(r - k).mean()), 1), 'tercios': {}}
    for nom, (a, b) in (('arriba', (0, h // 3)), ('medio', (h // 3, 2 * h // 3)), ('abajo', (2 * h // 3, h))):
        hr, sr, vr = _hsv_medio(r[a:b])
        hk, sk, vk = _hsv_medio(k[a:b])
        out['tercios'][nom] = {'proxy_hsv': [hr, sr, vr], 'kn5_hsv': [hk, sk, vk], 'dV': round(vk - vr, 3),
                               'dS': round(sk - sr, 3), 'mae': round(float(np.abs(r[a:b] - k[a:b]).mean()), 1)}
    return out


def hoja(filas, ruta, cw, ch, titulo):
    f_t, f_e = _fuente(26), _fuente(18)
    cab, sep, pie = 44, 6, 26
    W = 2 * cw + 3 * sep
    H = cab + len(filas) * (ch + pie + sep) + sep
    im = Image.new('RGB', (W, H), (24, 24, 24))
    d = ImageDraw.Draw(im)
    d.text((sep, 8), titulo, fill=(240, 240, 240), font=f_t)
    y = cab
    for nombre, ref, kn5, c, origen in filas:
        for j, (img, et) in enumerate(((ref, 'modo AC de Blender (%s)' % origen), (kn5, 'como AC leido del KN5'))):
            x = sep + j * (cw + sep)
            if img is not None:
                im.paste(img.resize((cw, ch), Image.LANCZOS), (x, y))
            else:
                d.rectangle([x, y, x + cw, y + ch], fill=(60, 30, 30))
                d.text((x + 20, y + ch // 2), 'sin captura del proxy', fill=(255, 200, 200), font=f_e)
            d.text((x + 6, y + 4), '%s  |  %s' % (nombre, et), fill=(255, 255, 80), font=f_e)
        if c:
            t = c['tercios']
            txt = ('media proxy %s  kn5 %s  MAE %.1f  |  dV arriba %+.3f medio %+.3f abajo %+.3f  |  dS abajo %+.3f' % (
                c['media_proxy'], c['media_kn5'], c['mae_srgb8'], t['arriba']['dV'], t['medio']['dV'], t['abajo']['dV'],
                t['abajo']['dS']))
        else:
            txt = 'sin comparacion'
        d.text((sep + 4, y + ch + 3), txt, fill=(220, 220, 220), font=f_e)
        y += ch + pie + sep
    im.save(ruta, optimize=True)
    return im.size


def main(argv):
    carpeta = argv[0]
    nombre = 'hoja_v12_como_ac'
    cw, ch = 720, 405
    if '--nombre' in argv:
        nombre = argv[argv.index('--nombre') + 1]
    if '--celda' in argv:
        cw, ch = [int(v) for v in argv[argv.index('--celda') + 1].split('x')]
    vj = json.load(open(os.path.join(carpeta, 'vista.json'), encoding='utf-8'))
    filas, res = [], {'kn5': vj.get('kn5'), 'tomas': {}}
    for toma, fila in vj['tomas'].items():
        kn5 = Image.open(os.path.join(carpeta, toma + '.png')).convert('RGB')
        ref_p = fila.get('ref_proxy')
        ref = Image.open(ref_p).convert('RGB') if ref_p and os.path.exists(ref_p) else None
        origen = os.path.basename(os.path.dirname(os.path.dirname(ref_p))) + '/' + os.path.basename(
            os.path.dirname(ref_p)) if ref_p else '-'
        c = cifras(ref, kn5) if ref is not None and ref.size == kn5.size else None
        if c:
            c['ref_proxy'] = ref_p
        res['tomas'][toma] = c
        filas.append((toma, ref, kn5, c, origen))
    titulo = 'Porto Corsa v1.2: modo AC de Blender (izq.) vs como AC leido del KN5 (der.)'
    tam = hoja(filas, os.path.join(carpeta, nombre + '.png'), cw, ch, titulo)
    pil = [f for f in filas if '_piloto_' in f[0]]
    otras = [f for f in filas if '_piloto_' not in f[0]]
    if pil:
        hoja(pil, os.path.join(carpeta, nombre + '_piloto.png'), cw, ch, titulo + ' - piloto')
    if otras:
        hoja(otras, os.path.join(carpeta, nombre + '_postales.png'), cw, ch, titulo + ' - aerea y postales')
    json.dump(res, open(os.path.join(carpeta, nombre + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    for toma, c in res['tomas'].items():
        if c:
            print('%-26s MAE %5.1f  dV arriba %+.3f medio %+.3f abajo %+.3f  dS abajo %+.3f' % (
                toma, c['mae_srgb8'], c['tercios']['arriba']['dV'], c['tercios']['medio']['dV'],
                c['tercios']['abajo']['dV'], c['tercios']['abajo']['dS']))
        else:
            print('%-26s sin comparacion' % toma)
    print('OK hoja -> %s (%dx%d, %d tomas)' % (os.path.join(carpeta, nombre + '.png'), tam[0], tam[1], len(filas)))


if __name__ == '__main__':
    main(sys.argv[1:])
