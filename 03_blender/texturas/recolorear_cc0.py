# -*- coding: utf-8 -*-
"""recolorear_cc0.py - texturas CC0 (texturas/cc0/<nombre>/, manifest.json) recoloreadas a la PALETA de Porto Corsa.

FASE VISUAL F1, bloque 3 punto 2 (propietario 'materiales'). Decision 3 del usuario: CC0 de Poly Haven / ambientCG
(ya descargadas en texturas/cc0/, 1K JPG; NO se descarga nada aqui).

Para cada textura del MAPA toma el albedo CC0, lo pasa a LUMINANCIA lineal y lo tinta con el color de paleta.json
conservando +-15 % de la variacion de croma original (musgo, oxido, tierra entre piedras), lo comprueba/arregla como
tile seamless (fundido de borde con envoltura si hace falta) y escribe texturas/<salida>_d.png a 1024 px (nunca 2K:
el writer recorta a 1024/512) + mosaico_3x3_<salida>.png + la media lineal en texturas/medias.json (misma clave y
misma API que generar_texturas.py: aplicar_texturas.py no nota la diferencia). Normal opcional <salida>_n.png
(OpenGL, tal cual, 1024) para el txDetailNM del multicapa (plan bloque 3.5, [W]).

Orden del pipeline de texturas: PIL primero (generar_texturas.py), CC0 despues (este script sobrescribe las salidas
con el mismo nombre). Si una textura CC0 falta, se deja el tile PIL y se avisa.

  python recolorear_cc0.py                    las 4 del terreno y despues el resto del MAPA
  python recolorear_cc0.py --terreno          solo roca_caliza, hierba_seca, tierra, matorral
  python recolorear_cc0.py --solo teja,estuco
  python recolorear_cc0.py --normales todas|terreno|no   (defecto: terreno)
  python recolorear_cc0.py --croma 0.15 --px 1024
Escribe ademas texturas/CREDITS.txt (que CC0 hay detras de cada PNG; CC0 no exige atribucion, se da igual).
"""
import argparse
import datetime
import json
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
import paleta  # noqa: E402
import generar_texturas as GT  # noqa: E402  (guardar/anotar_media/costura_max: misma API y mismo medias.json)

DIR_CC0 = os.path.join(AQUI, 'cc0')
MANIFEST = os.path.join(DIR_CC0, 'manifest.json')

# nombre_corto del manifest -> (fichero de salida, tinte de paleta o ('tintes_texturas', clave), grupo, nota)
# El tinte 'colores' se pide con paleta.rgb(nombre); los de 'tintes_texturas' se leen de paleta.cargar().
MAPA = {
    # --- las 4 capas del terreno (primero) ---
    'roca_caliza':       ('caliza_d.png',      'caliza_ocre',          'terreno', 'capa A roca; sustituye al PIL caliza_d'),
    'hierba_seca':       ('hierba_seca_d.png', 'hierba_seca',          'terreno', 'capa G hierba seca'),
    'tierra':            ('tierra_d.png',      'tierra',               'terreno', 'capa B tierra (tambien MAT_tierra, 1DIRT_)'),
    'matorral':          ('matorral_d.png',    'oliva_oscuro',         'terreno', 'capa R matorral; la variacion la da el CC0'),
    # --- despues, el resto ---
    'estuco':            ('estuco_d.png',      ('tintes_texturas', 'estuco'),  'resto', 'neutro casi blanco: multiplica el color de fachada'),
    'teja':              ('teja_d.png',        'terracota',            'resto', 'teja arabe terracota'),
    'adoquin':           ('adoquin_d.png',     ('tintes_texturas', 'adoquin'), 'resto', 'NUEVO tile (familia adoquin pendiente del bloque 5)'),
    'asfalto':           ('asfalto_d.png',     ('tintes_texturas', 'asfalto'), 'resto', 'neutro gris: el tono lo pone MAT_asfalto'),
    'piedra_seca':       ('piedra_seca_d.png', 'caliza_ocre',          'resto', 'NUEVO tile (muros de bancal, bloque 7.3)'),
    'escollera':         ('escollera_d.png',   'caliza_gris_calido',   'resto', 'NUEVO tile (escolleras, bloque 6.3)'),
    'fondo_marino':      ('fondo_marino_d.png', 'arena',               'resto', 'NUEVO tile (MAT_fondo_marino, bloque 6.1)'),
    'pista_tierra':      ('pista_tierra_d.png', 'tierra',              'extra', 'opcional: tramo de tierra conducible'),
    'roca_afloramiento': ('afloramiento_d.png', 'caliza_ocre',         'extra', 'opcional: afloramientos (bloque 2.5)'),
    'acantilado_lejano': ('acantilado_d.png',  'caliza_gris_calido',   'extra', 'opcional: acantilados lejanos'),
}
TERRENO = ('roca_caliza', 'hierba_seca', 'tierra', 'matorral')
LUM = np.array([0.2126, 0.7152, 0.0722])


def cargar_manifest():
    with open(MANIFEST, encoding='utf-8') as fh:
        m = json.load(fh)
    return {t['nombre_corto']: t for t in m['texturas']}


def tinte_lineal(spec):
    """Color lineal del tinte y si es 'neutro' (gris: solo luminancia)."""
    if isinstance(spec, tuple):
        sec, clave = spec
        e = paleta.cargar()[sec][clave]
        return np.array(e['rgb'], dtype=np.float64), bool(e.get('neutro', False))
    return np.array(paleta.rgb(spec), dtype=np.float64), False


def a_cuadrado(a, px):
    """Deja la imagen en px x px: si es mas ancha que alta (adoquin 1024x512) la repite (es seamless), si no reescala."""
    h, w = a.shape[:2]
    if h != w:
        if w > h and w % h == 0:
            a = np.tile(a, (w // h, 1, 1) if a.ndim == 3 else (w // h, 1))
        elif h > w and h % w == 0:
            a = np.tile(a, (1, h // w, 1) if a.ndim == 3 else (1, h // w))
    if a.shape[0] != px:
        img = Image.fromarray(np.clip(np.round(a * 255.0), 0, 255).astype(np.uint8))
        a = np.asarray(img.resize((px, px), Image.LANCZOS), dtype=np.float64) / 255.0
    return a


def fundir_bordes(a, ancho=32):
    """Fundido periodico de los bordes (si la textura no cierra bien): mezcla cada borde con el opuesto
    en una franja de `ancho` px con peso lineal. Mantiene la media."""
    out = a.copy()
    n = a.shape[0]
    w = np.linspace(0.0, 0.5, ancho)[:, None, None] if a.ndim == 3 else np.linspace(0.0, 0.5, ancho)[:, None]
    # vertical: filas 0..ancho se mezclan con las filas n-ancho..n (desplazadas)
    arriba = a[:ancho]
    abajo = a[n - ancho:]
    out[:ancho] = arriba * (1 - (0.5 - w)) + abajo[::-1] * (0.5 - w)
    out[n - ancho:] = abajo * (1 - w[::-1]) + arriba[::-1] * w[::-1]
    a2 = out
    out = a2.copy()
    wx = np.linspace(0.0, 0.5, ancho)[None, :, None] if a.ndim == 3 else np.linspace(0.0, 0.5, ancho)[None, :]
    izq = a2[:, :ancho]
    der = a2[:, n - ancho:]
    out[:, :ancho] = izq * (1 - (0.5 - wx)) + der[:, ::-1] * (0.5 - wx)
    out[:, n - ancho:] = der * (1 - wx[:, ::-1]) + izq[:, ::-1] * wx[:, ::-1]
    return out


def recolorear(lin, tinte, neutro=False, croma=0.15):
    """lin: albedo lineal HxWx3. Devuelve HxWx3 lineal: tinte x (Y / Ymedia) x (1 + croma x (desvio de croma - 1))."""
    Y = lin @ LUM
    Ym = max(float(Y.mean()), 1e-4)
    rel = (Y / Ym)[..., None]
    if neutro:
        return np.clip(tinte[None, None, :] * rel, 0, 1)
    # croma del CC0 por canal relativa a su luminancia, normalizada a su media (1 = el tono medio del CC0)
    c = lin / np.maximum(Y, 1e-4)[..., None]
    c_m = c.reshape(-1, 3).mean(axis=0)
    dev = c / np.maximum(c_m, 1e-4)[None, None, :]
    dev = np.clip(dev, 0.4, 2.5)
    out = tinte[None, None, :] * rel * (1.0 + croma * (dev - 1.0))
    # re-centra la media exactamente en el tinte (el termino de croma puede moverla un poco)
    m = out.reshape(-1, 3).mean(axis=0)
    out = out * (tinte / np.maximum(m, 1e-4))[None, None, :]
    return np.clip(out, 0, 1)


def procesar(nombre, mf, px=1024, croma=0.15, normal=False, umbral_costura=1.6):
    t = mf.get(nombre)
    if t is None:
        print('  AVISO: %s no esta en manifest.json: se deja el tile PIL' % nombre)
        return None
    salida, spec, grupo, nota = MAPA[nombre]
    ruta_dif = os.path.join(DIR_CC0, t['mapas']['diffuse'])
    if not os.path.exists(ruta_dif):
        print('  AVISO: falta %s: se deja el tile PIL' % ruta_dif)
        return None
    img = Image.open(ruta_dif).convert('RGB')
    a = np.asarray(img, dtype=np.float64) / 255.0
    a = a_cuadrado(a, px)
    lin = GT.srgb_a_lin(a)
    tinte, neutro = tinte_lineal(spec)
    out = recolorear(lin, tinte, neutro=neutro, croma=croma)
    cost = GT.costura_max(out)
    fundido = False
    if cost > umbral_costura:
        out = fundir_bordes(out, 32)
        fundido = True
        cost2 = GT.costura_max(out)
    else:
        cost2 = cost
    srgb = GT.lin_a_srgb(out)
    GT.guardar(salida, srgb, origen='cc0:%s' % t['asset_id'])
    GT.anotar_media(salida, origen='cc0:%s' % t['asset_id'],
                    extra={'cc0': t['asset_id'], 'sitio': t['sitio'], 'dimensiones_m': t.get('dimensiones_m'),
                           'tinte': spec if not isinstance(spec, tuple) else '/'.join(spec),
                           'croma': croma, 'costura': round(cost2, 4), 'fundido_bordes': fundido})
    res = {'nombre': nombre, 'salida': salida, 'asset_id': t['asset_id'], 'sitio': t['sitio'],
           'autores': t.get('autores', []), 'url': t.get('url_pagina'), 'licencia': t.get('licencia', 'CC0 1.0'),
           'costura_antes': round(cost, 4), 'costura': round(cost2, 4), 'fundido': fundido, 'nota': nota,
           'normal': None}
    if normal:
        rn = t['mapas'].get('normal_gl')
        if rn and os.path.exists(os.path.join(DIR_CC0, rn)):
            nimg = Image.open(os.path.join(DIR_CC0, rn)).convert('RGB')
            na = a_cuadrado(np.asarray(nimg, dtype=np.float64) / 255.0, px)
            ruta_n = os.path.join(AQUI, salida.replace('_d.png', '_n.png'))
            Image.fromarray(np.clip(np.round(na * 255.0), 0, 255).astype(np.uint8)).save(ruta_n)
            res['normal'] = os.path.basename(ruta_n)
            print('  -> %s (normal OpenGL, tal cual)' % ruta_n)
    print('  %s <- %s (%s): costura %.3f%s' % (salida, t['asset_id'], t['sitio'], cost2, ' (bordes fundidos)' if fundido else ''))
    return res


def escribir_credits(resultados):
    ruta = os.path.join(AQUI, 'CREDITS.txt')
    previos = {}
    if os.path.exists(ruta):
        # conserva lo ya anotado de otras ejecuciones (una linea por salida)
        with open(ruta, encoding='utf-8') as fh:
            for ln in fh:
                if ln.startswith('  ') and ' <- ' in ln:
                    previos[ln.strip().split(' <- ')[0]] = ln.rstrip('\n')
    for r in resultados:
        if r:
            previos[r['salida']] = '  %-22s <- %-22s %-11s %s  %s  (%s)' % (
                r['salida'], r['asset_id'], r['sitio'], ', '.join(r['autores']) or '-', r['url'] or '', r['licencia'])
            if r['normal']:
                previos[r['normal']] = '  %-22s <- %-22s %-11s %s  %s  (%s, normal OpenGL sin cambios)' % (
                    r['normal'], r['asset_id'], r['sitio'], ', '.join(r['autores']) or '-', r['url'] or '', r['licencia'])
    lineas = [
        'Texturas de 03_blender/texturas/ derivadas de CC0 (Poly Haven, ambientCG) - mod Porto Corsa (Cars 2) para Assetto Corsa',
        '=' * 112,
        'Generadas por texturas/recolorear_cc0.py el %s: luminancia del albedo CC0 + tinte de 03_blender/paleta.json' % datetime.date.today().isoformat(),
        '(croma del original conservada al +-15 %%), 1024 px, seamless comprobado (mosaico_3x3_*.png).',
        'Licencia de los originales: Creative Commons CC0 1.0 Universal (dominio publico; no exige atribucion, se da igualmente).',
        'Originales 1K JPG y manifest con sha256: texturas/cc0/ (CREDITS.txt, LICENSE_CC0.txt, manifest.json).',
        'Las demas texturas de esta carpeta (las que no aparecen abajo) son sintesis propia (generar_texturas.py, PIL/numpy).',
        '',
        '  salida                  <- id CC0                sitio       autor(es)  pagina  (licencia)',
    ]
    lineas += [previos[k] for k in sorted(previos)]
    with open(ruta, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lineas) + '\n')
    print('CREDITS ->', ruta)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--terreno', action='store_true', help='solo las 4 capas del terreno')
    ap.add_argument('--solo', default='', help='lista de nombres cortos del manifest')
    ap.add_argument('--normales', default='terreno', choices=('todas', 'terreno', 'no'))
    ap.add_argument('--croma', type=float, default=0.15)
    ap.add_argument('--px', type=int, default=1024)
    ap.add_argument('--extras', action='store_true', help='incluye tambien los opcionales (grupo extra)')
    a = ap.parse_args(argv)
    if a.px > 1024:
        print('AVISO: px > 1024 prohibido (plan decision 8: el writer recorta y cuadruplica el zip); se usa 1024')
        a.px = 1024
    mf = cargar_manifest()
    if a.solo:
        pedidos = [s.strip() for s in a.solo.split(',') if s.strip()]
    elif a.terreno:
        pedidos = list(TERRENO)
    else:
        pedidos = list(TERRENO) + [k for k, v in MAPA.items() if v[2] == 'resto'] + \
                  ([k for k, v in MAPA.items() if v[2] == 'extra'] if a.extras else [])
    resultados = []
    for n in pedidos:
        if n not in MAPA:
            print('AVISO: %s no esta en MAPA (validos: %s)' % (n, ', '.join(MAPA)))
            continue
        normal = (a.normales == 'todas') or (a.normales == 'terreno' and n in TERRENO)
        print(n)
        resultados.append(procesar(n, mf, px=a.px, croma=a.croma, normal=normal))
    escribir_credits(resultados)
    hechos = [r for r in resultados if r]
    print('RECOLOREAR_CC0: %d/%d texturas; costura max %.3f' % (len(hechos), len(pedidos),
                                                             max([r['costura'] for r in hechos] or [0.0])))
    # F1 r4: tile DERIVADO caliza_grande_d.png (McLaren, 24 m) = mezcla de dos escalas de afloramiento_d / caliza_d ya
    # recoloreados: se rehace siempre al final para que lea los PNG finales (orden "PIL primero, CC0 despues, derivados al final")
    if any(n in ('roca_caliza', 'roca_afloramiento') for n in pedidos) and hasattr(GT, 'caliza_grande'):
        GT.caliza_grande()
    return hechos


if __name__ == '__main__':
    main()
