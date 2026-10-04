# -*- coding: utf-8 -*-
"""leer_kn5_color.py - lee la seccion de texturas y materiales de un KN5 (formato de kn5_writer_opt.py) y da,
por material, la media sRGB de su textura y sus props (ksAmbient, ksDiffuse...). Sirve para comprobar que el KN5
generado con color_ac lleva los colores y props esperados, y para comparar con el KN5 anterior.
  python 04_export/_color_ac_prueba/leer_kn5_color.py <a.kn5> [b.kn5] [MAT_x,MAT_y]"""
import io
import struct
import sys

import numpy as np
from PIL import Image


def leer(ruta):
    f = open(ruta, 'rb')
    assert f.read(6) == b'sc6969'
    ver = struct.unpack('<i', f.read(4))[0]
    if ver > 5:
        f.read(4)
    u32 = lambda: struct.unpack('<I', f.read(4))[0]  # noqa: E731
    i32 = lambda: struct.unpack('<i', f.read(4))[0]  # noqa: E731
    cad = lambda: f.read(u32()).decode('utf-8')  # noqa: E731
    tex = {}
    for _ in range(i32()):
        i32()
        nombre = cad()
        datos = f.read(u32())
        try:
            img = np.asarray(Image.open(io.BytesIO(datos)).convert('RGB')).astype(np.float64)
            tex[nombre] = img.reshape(-1, 3).mean(0)
        except Exception:  # noqa
            tex[nombre] = None
    mats = {}
    for _ in range(i32()):
        nombre, shader = cad(), cad()
        f.read(2)
        i32()
        props = {}
        for _ in range(i32()):
            p = cad()
            props[p] = struct.unpack('<f', f.read(4))[0]
            f.read(4 * (2 + 3 + 4))
        txs = []
        for _ in range(i32()):
            slot = cad()
            i32()
            txs.append((slot, cad()))
        mats[nombre] = {'shader': shader, 'props': props, 'tex': txs[0][1] if txs else None}
    for m in mats.values():
        m['media_srgb'] = tex.get(m['tex'])
    return mats


if __name__ == '__main__':
    a = leer(sys.argv[1])
    b = leer(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].endswith('.kn5') else None
    sel = sys.argv[-1].split(',') if not sys.argv[-1].endswith('.kn5') else None
    print('%d materiales en %s' % (len(a), sys.argv[1]))
    for n in (sel or sorted(a)):
        if n not in a:
            continue
        m = a[n]
        txt = '%-30s %s ksA %.2f ksD %.2f ksS %.2f exp %g media %s' % (
            n, m['shader'], m['props'].get('ksAmbient', -1), m['props'].get('ksDiffuse', -1),
            m['props'].get('ksSpecular', -1), m['props'].get('ksSpecularEXP', -1),
            None if m['media_srgb'] is None else m['media_srgb'].round().astype(int).tolist())
        if b and n in b:
            mb = b[n]
            txt += '  | otro: ksA %.2f ksD %.2f media %s' % (
                mb['props'].get('ksAmbient', -1), mb['props'].get('ksDiffuse', -1),
                None if mb['media_srgb'] is None else mb['media_srgb'].round().astype(int).tolist())
        print(txt)
