# -*- coding: utf-8 -*-
"""comparar_kn5.py - compara el KN5 del writer parcheado con color_ac (COLOR_AC=1) con el de siempre (COLOR_AC=0) sobre
la MISMA escena de export: lo unico que debe cambiar son las props, las texturas y el reparto de las caras de
MAT_terreno en MAT_terreno + MAT_terreno_roca (mismos triangulos). Python del sistema (struct + numpy).
  python 04_export/_color_ac_prueba/comparar_kn5.py con_color.kn5 sin_color.kn5
Comprueba: dummies (nombre, hijos y matriz) iguales; cada malla que no es de MAT_terreno igual byte a byte (vertices,
indices, flags); por grupo de terreno, los triangulos de MAT_terreno + MAT_terreno_roca = los de MAT_terreno; mismo
orden y flags de los materiales comunes; MAT_terreno_roca con los flags de MAT_terreno. Sale con 1 si algo falla."""
import hashlib
import re
import struct
import sys
from collections import defaultdict


def leer(ruta):
    f = open(ruta, 'rb')
    assert f.read(6) == b'sc6969'
    struct.unpack('<i', f.read(4))
    u32 = lambda: struct.unpack('<I', f.read(4))[0]  # noqa: E731
    i32 = lambda: struct.unpack('<i', f.read(4))[0]  # noqa: E731
    cad = lambda: f.read(u32()).decode('utf-8')  # noqa: E731
    for _ in range(i32()):
        i32(); cad(); f.read(u32())
    mats = []
    for _ in range(i32()):
        n, sh = cad(), cad()
        ab, at = f.read(1)[0], f.read(1)[0]
        dm = i32()
        props = {}
        for _ in range(i32()):
            p = cad()
            props[p] = struct.unpack('<f', f.read(4))[0]
            f.read(36)
        for _ in range(i32()):
            cad(); i32(); cad()
        mats.append({'name': n, 'flags': (sh, ab, at, dm), 'props': props})
    nodos = []

    def nodo():
        tipo, n, nh = i32(), cad(), i32()
        act = f.read(1)[0]
        if tipo == 1:
            nodos.append({'tipo': 1, 'name': n, 'hijos': nh, 'act': act, 'md5': hashlib.md5(f.read(64)).hexdigest()})
        else:
            cs, vis, tr = f.read(3)
            nv = i32()
            vb = f.read(nv * 44)
            ni = i32()
            ib = f.read(ni * 2)
            mid, lay = i32(), i32()
            resto = f.read(8 + 16)
            ren = f.read(1)[0]
            nodos.append({'tipo': 2, 'name': n, 'mat': mats[mid]['name'], 'tris': ni // 3,
                          'flags': (act, cs, vis, tr, lay, ren),
                          'md5': hashlib.md5(vb + ib + struct.pack('<i', lay) + resto).hexdigest()})
        for _ in range(nh):
            nodo()
    nodo()
    assert f.read() == b''
    return mats, nodos


def grupo(nombre):
    """Grupo de fusion / objeto de una malla de terreno (sin material ni _pN)."""
    return re.sub(r'(_?MAT_terreno(_roca)?)(_sinsombra)?_p\d+$', '', nombre)


def main(a, b):
    ma, na = leer(a)
    mb, nb = leer(b)
    fallos = []
    def ok(cond, txt):
        print(('  OK    ' if cond else '  FALLO ') + txt)
        if not cond:
            fallos.append(txt)
    da = [(n['name'], n['hijos'], n['md5']) for n in na if n['tipo'] == 1]
    db = [(n['name'], n['hijos'], n['md5']) for n in nb if n['tipo'] == 1]
    ok([x[0] for x in da] == [x[0] for x in db] and [x[2] for x in da] == [x[2] for x in db],
       'dummies: %d y %d, mismos nombres, orden y matrices (hijos distintos solo en los grupos con terreno: %s)' % (
           len(da), len(db), sorted({x[0] for x, y in zip(da, db) if x[1] != y[1]})))
    ter = ('MAT_terreno', 'MAT_terreno_roca')
    ra = {n['name']: n for n in na if n['tipo'] == 2 and n['mat'] not in ter}
    rb = {n['name']: n for n in nb if n['tipo'] == 2 and n['mat'] not in ter}
    distintas = [k for k in set(ra) | set(rb) if k not in ra or k not in rb or (ra[k]['md5'], ra[k]['flags']) != (rb[k]['md5'], rb[k]['flags'])]
    ok(not distintas, '%d mallas que no son de terreno: iguales byte a byte (vertices, indices, flags)%s' % (
        len(ra), '' if not distintas else ' -> distintas: %s' % distintas[:6]))
    ta, tb = defaultdict(int), defaultdict(int)
    for n in na:
        if n['tipo'] == 2 and n['mat'] in ter:
            ta[grupo(n['name'])] += n['tris']
    for n in nb:
        if n['tipo'] == 2 and n['mat'] in ter:
            tb[grupo(n['name'])] += n['tris']
    roca = sum(n['tris'] for n in na if n['tipo'] == 2 and n['mat'] == 'MAT_terreno_roca')
    ok(dict(ta) == dict(tb), 'terreno: triangulos de MAT_terreno + MAT_terreno_roca = los de MAT_terreno por grupo (%s); '
       'de ellos roca %d' % (dict(ta), roca))
    pa = {m['name']: m for m in ma}
    pb = {m['name']: m for m in mb}
    comunes = [m['name'] for m in ma if m['name'] in pb]
    ok(comunes == [m['name'] for m in mb] and set(pa) - set(pb) == {'MAT_terreno_roca'},
       'materiales: los %d de antes en el mismo orden + %s' % (len(mb), sorted(set(pa) - set(pb))))
    ok(all(pa[n]['flags'] == pb[n]['flags'] for n in comunes) and pa['MAT_terreno_roca']['flags'] == pa['MAT_terreno']['flags'],
       'shader, alphaBlend, alphaTested y depthMode iguales (MAT_terreno_roca como MAT_terreno)')
    ok(set(pb['MAT_terreno']['props']) == set(pa['MAT_terreno']['props']), 'mismas props: %s' % list(pa['MAT_terreno']['props']))
    print('RESULTADO:', 'OK' if not fallos else 'FALLOS: %d' % len(fallos))
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
