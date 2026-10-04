# -*- coding: utf-8 -*-
"""paleta.py - acceso a la PALETA UNICA de la fase visual (03_blender/paleta.json).

Uso desde cualquier script (python del sistema o bpy):
    import sys; sys.path.insert(0, r'E:\\Escritorio\\claude-pc\\arnau-aseto-corsa\\03_blender')
    import paleta
    paleta.rgb('hierba_seca')          -> (0.55, 0.45, 0.20)       RGB lineal: para diffuse_color / Base Color
    paleta.rgba('hierba_seca')         -> (0.55, 0.45, 0.20, 1.0)
    paleta.srgb('hierba_seca')         -> (0.769, 0.702, 0.486)    sRGB 0..1 (para PIL: paleta.srgb8 -> (196, 179, 124))
    paleta.srgb_hex('hierba_seca')     -> '#C4B37C'
    paleta.familia_ac('hierba_seca')   -> 'terreno'                familia de 04_export/color_ac.py
    paleta.variante('salvia', 0.85)    -> salvia al 85 % de luminancia (matices _clara/_oscura de los kits)
    paleta.nombres()                   -> los 12 nombres; paleta.cargar() -> el JSON entero (cacheado)
Las fachadas propuestas se piden como 'fachada_<nombre>' (p. ej. rgb('fachada_rojo_pompeya')) y las actuales
de casas_kit_v2 como 'fachada_actual_<nombre>'.
Linea de ordenes:  python paleta.py            lista la paleta y comprueba que srgb_hex == sRGB(rgb)
                   python paleta.py --png out.png   dibuja las muestras planas (PIL) para el README
REGLA: diffuse_color / Base Color sin enlazar = media lineal deseada (es lo que lee kn5_writer_opt.py).
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA_JSON = os.path.join(AQUI, 'paleta.json')
_CACHE = {}


def cargar(ruta=None):
    """Devuelve el dict completo de paleta.json (cacheado por ruta)."""
    ruta = ruta or RUTA_JSON
    if ruta not in _CACHE:
        with open(ruta, encoding='utf-8') as fh:
            _CACHE[ruta] = json.load(fh)
    return _CACHE[ruta]


def _todas(ruta=None):
    """Espacio de nombres plano: colores + fachada_<propuesta> + fachada_actual_<actual>."""
    P = cargar(ruta)
    t = {}
    for k, v in P['colores'].items():
        t[k] = v
    for k, v in P.get('fachadas_propuesta', {}).items():
        if not k.startswith('_'):
            t['fachada_' + k] = v
    for k, v in P.get('fachadas_actual', {}).items():
        if not k.startswith('_'):
            t['fachada_actual_' + k] = dict(v, familia_ac='edificio')
    return t


def _entrada(nombre, ruta=None):
    t = _todas(ruta)
    if nombre not in t:
        raise KeyError('color %r no esta en paleta.json; validos: %s' % (nombre, ', '.join(sorted(t))))
    return t[nombre]


def nombres(ruta=None):
    """Los 12 nombres de la paleta (sin fachadas), en el orden del JSON."""
    return list(cargar(ruta)['colores'].keys())


def rgb(nombre, ruta=None):
    """RGB lineal 0..1 (tupla de 3 floats)."""
    return tuple(float(c) for c in _entrada(nombre, ruta)['rgb'])


def rgba(nombre, alpha=1.0, ruta=None):
    return rgb(nombre, ruta) + (float(alpha),)


def familia_ac(nombre, ruta=None):
    """Familia de color_ac.FAMILIAS (asfalto, terreno, agua, roca, edificio, pintado, metal, cristal, vegetacion, luz)."""
    return _entrada(nombre, ruta)['familia_ac']


def uso(nombre, ruta=None):
    return _entrada(nombre, ruta).get('uso', '')


# ---------------------------------------------------------------- conversiones (sRGB IEC 61966-2-1, no gamma 2.2)
def lin_a_srgb(c):
    c = min(1.0, max(0.0, float(c)))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1.0 / 2.4) - 0.055


def srgb_a_lin(c):
    c = float(c)
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def srgb(nombre, ruta=None):
    """sRGB 0..1 calculado desde el rgb lineal (coincide con srgb_hex salvo redondeo)."""
    return tuple(lin_a_srgb(c) for c in rgb(nombre, ruta))


def srgb8(nombre, ruta=None):
    return tuple(int(round(c * 255)) for c in srgb(nombre, ruta))


def srgb_hex(nombre, ruta=None):
    """'#RRGGBB' tal como esta escrito en el JSON (referencia para el usuario)."""
    return _entrada(nombre, ruta)['srgb_hex']


def hex_desde_rgb(rgb_lin):
    return '#' + ''.join('%02X' % int(round(lin_a_srgb(c) * 255)) for c in rgb_lin)


def variante(nombre, lum=1.0, ruta=None):
    """El color escalado en luminancia lineal (0.85 = version oscura, 1.15 = clara), recortado a 1."""
    return tuple(min(1.0, c * float(lum)) for c in rgb(nombre, ruta))


# ---------------------------------------------------------------- linea de ordenes
def verificar(ruta=None):
    """Comprueba que cada srgb_hex del JSON es el sRGB de su rgb (tolerancia 1/255). Devuelve lista de fallos."""
    fallos = []
    for n, e in _todas(ruta).items():
        h = hex_desde_rgb(e['rgb'])
        if h.upper() != e['srgb_hex'].upper():
            fallos.append('%s: srgb_hex %s pero sRGB(rgb) = %s' % (n, e['srgb_hex'], h))
        if 'familia_ac' in e and e['familia_ac'] not in ('asfalto', 'pintura_vial', 'terreno', 'agua', 'roca', 'edificio',
                                                          'pintado', 'metal', 'cristal', 'vegetacion', 'luz'):
            fallos.append('%s: familia_ac %r no existe en color_ac.FAMILIAS' % (n, e['familia_ac']))
    return fallos


def muestras_png(salida, ruta=None):
    """Hoja plana de muestras (sin luz: el sRGB tal cual) con PIL; util para el README, no sustituye a la carta."""
    from PIL import Image, ImageDraw, ImageFont
    todas = _todas(ruta)
    grupos = [('paleta (12)', nombres(ruta)),
              ('fachadas actuales (casas_kit_v2)', [k for k in todas if k.startswith('fachada_actual_')]),
              ('fachadas propuesta', [k for k in todas if k.startswith('fachada_') and not k.startswith('fachada_actual_')])]
    W, celda, alto_fila = 1600, 130, 190
    img = Image.new('RGB', (W, 40 + alto_fila * len(grupos)), (235, 235, 235))
    dr = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
        fb = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 18)
    except Exception:
        f = fb = ImageFont.load_default()
    y = 10
    for titulo, lista in grupos:
        dr.text((10, y), titulo, fill=(30, 30, 30), font=fb)
        y += 26
        for i, n in enumerate(lista):
            x = 10 + i * celda
            e = todas[n]
            col = tuple(int(round(lin_a_srgb(c) * 255)) for c in e['rgb'])
            dr.rectangle([x, y, x + celda - 10, y + 90], fill=col, outline=(60, 60, 60))
            dr.text((x, y + 95), n.replace('fachada_actual_', 'act. ').replace('fachada_', ''), fill=(20, 20, 20), font=f)
            dr.text((x, y + 113), e['srgb_hex'], fill=(20, 20, 20), font=f)
        y += alto_fila - 26
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    img.save(salida)
    return salida


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--png' in args:
        out = muestras_png(args[args.index('--png') + 1])
        print('muestras ->', out)
    print('%-26s %-22s %-8s %-11s uso' % ('nombre', 'rgb lineal', 'sRGB', 'familia'))
    for n in nombres():
        print('%-26s %-22s %-8s %-11s %s' % (n, rgb(n), srgb_hex(n), familia_ac(n), uso(n)[:70]))
    for n in sorted(k for k in _todas() if k.startswith('fachada_')):
        print('%-26s %-22s %-8s' % (n, tuple(round(c, 4) for c in rgb(n)), srgb_hex(n)))
    fallos = verificar()
    print('verificacion:', 'OK (%d entradas)' % len(_todas()) if not fallos else 'FALLOS: ' + '; '.join(fallos))
    sys.exit(1 if fallos else 0)
