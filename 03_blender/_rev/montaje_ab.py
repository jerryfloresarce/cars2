# -*- coding: utf-8 -*-
"""montaje_ab.py - pares ANTES|DESPUES y hojas de piloto/aereas a partir de dos carpetas de capturas (PIL, sin Blender).

  python 03_blender/_rev/montaje_ab.py <dir_bloque> [--antes antes] [--despues despues] [--modo normal|ac]
         [--rotulos ANTES DESPUES] [--etiqueta txt] [--ancho-piloto 1200] [--ancho-aereas 800] [--sufijo _x]
         [--diff [--tol-max N] [--tol-pct P]]
Defecto: modo normal -> <dir>/antes y <dir>/despues, salida AB_<toma>.png, hoja_<bloque>_piloto.png, hoja_<bloque>_aereas.png;
modo ac -> <dir>/antes_ac y <dir>/despues_ac, salida AB_ac_<toma>.png, hoja_<bloque>_piloto_ac.png, hoja_<bloque>_aereas_ac.png.
--antes/--despues admiten cualquier subcarpeta (p.ej. --antes normal --despues ac --rotulos BLENDER "MODO AC" para "las dos
verdades" del antes congelado, o --antes normal --despues calibracion --diff para la prueba de calibracion).
Cada par lleva rotulo: nombre de toma, rotulo A/B, modo, etiqueta y fecha; si las dos imagenes miden igual anade
"max|d|=N  px distintos=P%" (diferencia de pixel). El modo del pie se deduce de cada carpeta (ac, *_ac -> "AC"; normal,
calibracion, antes, despues -> "Blender"; otra -> --modo): un par normal-vs-AC dice "modo Blender vs AC".
--diff escribe ademas <dir>/calibracion<sufijo>.json con esas cifras y sale con codigo 3 si alguna toma supera la
tolerancia o falta en un lado. TOLERANCIA OFICIAL (decision del coordinador 04/10, criterio 1 del plan):
  modo normal: --tol-max 2 --tol-pct 0.02 por defecto (el raytracing/fast GI de EEVEE deja |d| <= 2/255 en hasta ~0.005 % de
               los pixeles entre dos pasadas identicas: ruido del motor, no de las camaras; ver ab_README.md punto 5);
  modo ac:     --tol-max 0 --tol-pct 0 por defecto (sin raytracing ni fast GI el render es determinista: 0 exacto).
Piloto = tomas con '_piloto' o '_postal' en el nombre (1200 px por defecto; --ancho-piloto 1600 = tamano completo); el resto
va a la hoja de aereas.
"""
import argparse
import datetime
import json
import os
import re
import sys

TOL_DEFECTO = {'normal': (2, 0.02), 'ac': (0, 0.0)}      # (max|d| 0-255, % de pixeles distintos) por modo


def modo_carpeta(ruta, modo_cli):
    """'AC' o 'Blender' segun el nombre de la carpeta; si no se reconoce, segun --modo."""
    b = os.path.basename(os.path.normpath(ruta)).lower()
    if re.search(r'(^|_)ac\d*$', b):
        return 'AC'
    if re.search(r'^(normal|calibracion|antes|despues)\d*$', b):
        return 'Blender'
    return 'AC' if modo_cli == 'ac' else 'Blender'

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def fuente(tam):
    for f in ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/segoeui.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default()


def es_piloto(nombre):
    return '_piloto' in nombre or '_postal' in nombre


def diferencia(a, b):
    """(max |a-b|, % de pixeles distintos) o None si no miden igual."""
    if a.size != b.size:
        return None
    x = np.asarray(a.convert('RGB'), np.int16)
    y = np.asarray(b.convert('RGB'), np.int16)
    d = np.abs(x - y).max(axis=2)
    return int(d.max()), float((d > 0).mean() * 100.0)


def par(ruta_a, ruta_b, nombre, rot_a, rot_b, modo, etiqueta, hoy, ancho, font, font_s):
    a = Image.open(ruta_a).convert('RGB') if ruta_a else None
    b = Image.open(ruta_b).convert('RGB') if ruta_b else None
    ref = a or b
    h = int(ref.height * ancho / ref.width)
    dif = diferencia(a, b) if (a is not None and b is not None) else None
    cab = 70                      # dos lineas: rotulos de cada lado y, debajo, modo/etiqueta/fecha/diferencia
    im = Image.new('RGB', (2 * ancho + 12, h + cab), (22, 22, 22))
    dr = ImageDraw.Draw(im)
    for k, (img, rot, col) in enumerate(((a, rot_a, (255, 255, 255)), (b, rot_b, (255, 220, 120)))):
        x0 = k * (ancho + 12)
        if img is not None:
            im.paste(img.resize((ancho, h), Image.LANCZOS) if img.width != ancho else img, (x0, cab))
        else:
            dr.rectangle((x0, cab, x0 + ancho, cab + h), fill=(60, 30, 30))
            dr.text((x0 + 20, cab + 20), 'FALTA %s' % nombre, font=font, fill=(255, 120, 120))
        dr.text((x0 + 8, 6), '%s  %s' % (rot, nombre), font=font, fill=col)
    pie = 'modo %s | %s | %s' % (modo, etiqueta, hoy)
    if dif is not None:
        pie += ' | diferencia de pixel: max|d|=%d, px distintos=%.3f%%' % dif
    dr.text((8, 42), pie, font=font_s, fill=(170, 170, 170))
    return im, dif


def hoja(pares, titulo, font):
    if not pares:
        return None
    w = max(p.width for p in pares)
    H = sum(p.height for p in pares) + 60
    out = Image.new('RGB', (w, H), (22, 22, 22))
    ImageDraw.Draw(out).text((10, 14), titulo, font=font, fill=(255, 255, 255))
    y = 60
    for p in pares:
        out.paste(p, (0, y))
        y += p.height
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--antes')
    ap.add_argument('--despues')
    ap.add_argument('--modo', default='normal', choices=('normal', 'ac'))
    ap.add_argument('--rotulos', nargs=2, default=('ANTES', 'DESPUES'))
    ap.add_argument('--etiqueta', default=None)
    ap.add_argument('--ancho-piloto', type=int, default=1200, help='ancho de cada lado en las tomas piloto/postal (1600 = tamano completo)')
    ap.add_argument('--ancho-aereas', type=int, default=800)
    ap.add_argument('--sufijo', default='')
    ap.add_argument('--diff', action='store_true')
    ap.add_argument('--tol-max', type=int, default=None, help='calibracion: max|d| (0-255) tolerado por toma (defecto: 2 en modo normal, 0 en modo ac)')
    ap.add_argument('--tol-pct', type=float, default=None, help='calibracion: %% de pixeles distintos tolerado por toma (defecto: 0.02 normal, 0 ac)')
    A = ap.parse_args()
    tol_def = TOL_DEFECTO[A.modo]
    if A.tol_max is None:
        A.tol_max = tol_def[0]
    if A.tol_pct is None:
        A.tol_pct = tol_def[1]
    D = os.path.abspath(A.dir)
    bloque = os.path.basename(D).strip('_')
    ac = '_ac' if A.modo == 'ac' else ''
    da = os.path.join(D, A.antes or ('antes' + ac))
    db = os.path.join(D, A.despues or ('despues' + ac))
    if not os.path.isdir(da) or not os.path.isdir(db):
        sys.exit('ERROR: faltan carpetas %s / %s' % (da, db))
    ma, mb = modo_carpeta(da, A.modo), modo_carpeta(db, A.modo)
    modo_txt = ma if ma == mb else '%s vs %s' % (ma, mb)
    etiqueta = A.etiqueta or bloque
    hoy = datetime.date.today().isoformat()
    font, font_s = fuente(26), fuente(20)
    na = {n for n in os.listdir(da) if n.endswith('.png')}
    nb = {n for n in os.listdir(db) if n.endswith('.png')}
    nombres = sorted(na | nb)
    pil, aer, difs = [], [], {}
    for n in nombres:
        toma = n[:-4]
        ra = os.path.join(da, n) if n in na else None
        rb = os.path.join(db, n) if n in nb else None
        ancho = A.ancho_piloto if es_piloto(toma) else A.ancho_aereas
        im, dif = par(ra, rb, toma, A.rotulos[0], A.rotulos[1], modo_txt, etiqueta, hoy, ancho, font, font_s)
        pref = 'AB_ac_' if A.modo == 'ac' else 'AB_'
        im.save(os.path.join(D, pref + toma + A.sufijo + '.png'))
        (pil if es_piloto(toma) else aer).append(im)
        difs[toma] = {'max_abs': dif[0], 'pct_px_distintos': round(dif[1], 4)} if dif else {'falta': [k for k, r in (('antes', ra), ('despues', rb)) if r is None]}
    for grupo, nom in ((pil, 'piloto'), (aer, 'aereas')):
        h = hoja(grupo, 'Porto Corsa - %s - %s (%s vs %s, modo %s, %s)' % (bloque, nom, A.rotulos[0], A.rotulos[1], modo_txt, hoy), font)
        if h is not None:
            h.save(os.path.join(D, 'hoja_%s_%s%s%s.png' % (bloque, nom, ac, A.sufijo)))
    print('OK montaje: %d pares (%d piloto, %d aereas) en %s' % (len(nombres), len(pil), len(aer), D))
    if A.diff:
        con = {k: v for k, v in difs.items() if 'max_abs' in v}
        mx = max((v['max_abs'] for v in con.values()), default=None)
        fuera = sorted(k for k, v in con.items() if v['max_abs'] > A.tol_max or v['pct_px_distintos'] > A.tol_pct)
        res = {'fecha': hoy, 'antes': da, 'despues': db, 'n_pares': len(con), 'max_abs_global': mx,
               'max_pct_px_distintos': max((v['pct_px_distintos'] for v in con.values()), default=None),
               'modo': A.modo, 'modo_carpetas': modo_txt,
               'tolerancia': {'max_abs': A.tol_max, 'pct_px_distintos': A.tol_pct,
                              'origen': 'defecto oficial modo %s (coordinador 04/10)' % A.modo if (A.tol_max, A.tol_pct) == tol_def else 'linea de ordenes'},
               'tomas_con_diferencia': sorted(k for k, v in con.items() if v['max_abs'] > 0),
               'tomas_fuera_de_tolerancia': fuera, 'faltan': sorted(k for k, v in difs.items() if 'falta' in v), 'por_toma': difs}
        json.dump(res, open(os.path.join(D, 'calibracion%s.json' % A.sufijo), 'w', encoding='utf-8'), indent=1)
        print('DIFF: %d pares, max|d| global = %s, tomas con diferencia: %d %s, fuera de tolerancia (max|d| > %d o px > %g%%, %s): %d%s' % (
            len(con), mx, len(res['tomas_con_diferencia']), res['tomas_con_diferencia'][:10], A.tol_max, A.tol_pct,
            res['tolerancia']['origen'], len(fuera), (' -> ' + str(fuera[:10])) if fuera else ''))
        if res['faltan']:
            print('DIFF: faltan en un lado: %s' % res['faltan'][:20])
        if fuera or res['faltan']:
            sys.exit(3)


if __name__ == '__main__':
    main()
