#!/usr/bin/env python3
"""Autotest de kn5_check.py: escribe un KN5 v5 sintetico siguiendo byte a byte el escritor de
actools (AcTools/Kn5File/Kn5Writer.cs) y la convencion de matriz del addon de Blender
(kn5_writer.py write_matrix: matrix[col][row] con row externo), lo lee con kn5_check y comprueba
que recupera lo escrito y consume todos los bytes. No necesita Blender ni AC.
Uso: python kn5_check_selftest.py  (escribe kn5_refs/selftest/_selftest.kn5 y _selftest.json)
"""
import io
import math
import os
import struct
import sys

import numpy as np

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa\04_export'
sys.path.insert(0, BASE)
import kn5_check as kc  # noqa: E402


class W:
    def __init__(self):
        self.b = io.BytesIO()

    def s(self, t: str):
        d = t.encode('utf-8')
        self.i(len(d))
        self.b.write(d)

    def i(self, v):
        self.b.write(struct.pack('<i', v))

    def h(self, v):
        self.b.write(struct.pack('<H', v))

    def u8(self, v):
        self.b.write(struct.pack('<B', v))

    def f(self, *vs):
        self.b.write(struct.pack('<%df' % len(vs), *vs))

    def matrix(self, M):
        # addon kn5_writer.write_matrix: for row: for col: write(matrix[col][row])
        for row in range(4):
            for col in range(4):
                self.f(float(M[col][row]))


def blender_a_kn5(v):
    return (v[0], v[2], -v[1])


def matriz_blender_rotz(loc, ang):
    c, s = math.cos(ang), math.sin(ang)
    M = np.eye(4)
    M[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    M[:3, 3] = loc
    return M


def convertir_matriz(Mb):
    """Equivalente a exporter_utils.convert_matrix: C @ M @ C^-1 con C = cambio de ejes (x,z,-y)."""
    C = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
    return C @ Mb @ np.linalg.inv(C)


def cubo(d=0.18):
    V = [(-d, -d, 0), (d, -d, 0), (d, d, 0), (-d, d, 0), (-d, -d, 2 * d), (d, -d, 2 * d), (d, d, 2 * d), (-d, d, 2 * d)]
    F = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (2, 6, 7, 3), (1, 5, 6, 2), (0, 3, 7, 4)]
    verts, idx = [], []
    for q in F:
        p = [np.array(V[k], float) for k in q]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        n /= np.linalg.norm(n)
        base = len(verts)
        for k, pp in enumerate(p):
            verts.append((blender_a_kn5(pp), blender_a_kn5(n), (k % 2, -(k // 2)), (1, 0, 0)))
        idx += [base + 1, base + 2, base + 0, base + 2, base + 3, base + 0]   # addon: (1,2,0),(2,3,0)
    return verts, idx


def quad_suelo(x0, z0, x1, z1, y):
    """Suelo horizontal en KN5 (plano XZ a altura y) con normal +Y y winding del addon."""
    P = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]   # equivalente Blender CCW visto desde +Z(up)
    # en Blender: (x0,-z0,y)... construimos directamente en Blender y convertimos para respetar el winding
    Pb = [(x0, -z0, y), (x1, -z0, y), (x1, -z1, y), (x0, -z1, y)]
    nb = np.cross(np.subtract(Pb[1], Pb[0]), np.subtract(Pb[2], Pb[0]))
    nb = nb / np.linalg.norm(nb)
    if nb[2] < 0:   # asegurar normal Blender +Z (arriba)
        Pb = Pb[::-1]
        nb = -nb
    verts = [(blender_a_kn5(p), blender_a_kn5(nb), (p[0] / 10, -p[1] / 10), (1, 0, 0)) for p in Pb]
    idx = [1, 2, 0, 2, 3, 0]
    return verts, idx


def write_mesh(w, nombre, verts, idx, mat, renderable=True):
    w.i(2); w.s(nombre); w.i(0); w.u8(1)            # tipo, nombre, hijos, activo
    w.u8(1); w.u8(1); w.u8(0)                        # castShadows, isVisible, isTransparent
    w.i(len(verts))
    for p, n, uv, t in verts:
        w.f(*p); w.f(*n); w.f(*uv); w.f(*t)
    w.i(len(idx))
    for k in idx:
        w.h(k)
    w.i(mat); w.i(0); w.f(0.0); w.f(1000.0)          # materialId, layer, lodIn, lodOut
    P = np.array([v[0] for v in verts])
    c = (P.min(0) + P.max(0)) / 2
    w.f(*c); w.f(float(np.linalg.norm(P - c, axis=1).max()))
    w.u8(1 if renderable else 0)


def write_dummy(w, nombre, M, n_hijos):
    w.i(1); w.s(nombre); w.i(n_hijos); w.u8(1)
    w.matrix(M)


def construir() -> bytes:
    w = W()
    w.b.write(b'sc6969'); w.i(5)
    # texturas: un PNG real (Pillow) y un DDS falso con cabecera 'DDS '
    from PIL import Image
    buf = io.BytesIO(); Image.new('RGB', (8, 4), (200, 30, 30)).save(buf, 'PNG'); png = buf.getvalue()
    dds = b'DDS ' + bytes(124) + b'\x00' * 64
    w.i(2)
    for nombre, blob in (('asfalto_d.png', png), ('hierba_d.dds', dds)):
        w.i(1); w.s(nombre); w.i(len(blob)); w.b.write(blob)
    # materiales
    w.i(2)
    for nombre, tex in (('asfalto', 'asfalto_d.png'), ('hierba', 'hierba_d.dds')):
        w.s(nombre); w.s('ksPerPixel'); w.u8(0); w.u8(0); w.i(0)
        w.i(2)
        for pn, val in (('ksDiffuse', 0.4), ('ksAmbient', 0.4)):
            w.s(pn); w.f(val); w.f(0, 0); w.f(0, 0, 0); w.f(0, 0, 0, 0)
        w.i(1); w.s('txDiffuse'); w.i(0); w.s(tex)
    # nodos: raiz BlenderFile con 3 hijos
    write_dummy(w, 'BlenderFile', np.eye(4), 3)
    Mb = matriz_blender_rotz((100.0, 200.0, 5.0), math.radians(30))
    Mk = convertir_matriz(Mb)
    write_dummy(w, 'AC_START_0', Mk, 1)
    v, i = cubo()
    write_mesh(w, 'AC_START_0', v, i, 0, renderable=False)
    v, i = quad_suelo(0, 0, 1900, 1800, 5.0)
    write_mesh(w, '1ROAD_pista', v, i, 0)
    v, i = quad_suelo(-10, -10, 0, 0, 3.0)
    write_mesh(w, '1GRASS_terreno', v, i, 1)
    return w.b.getvalue(), Mk


def main():
    data, Mk = construir()
    out = os.path.join(BASE, 'kn5_refs', 'selftest', '_selftest.kn5')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as fh:
        fh.write(data)
    info = kc.leer_kn5(data)
    fallos = []

    def check(cond, msg):
        print(('OK   ' if cond else 'FALLO') + ' ' + msg)
        if not cond:
            fallos.append(msg)

    check(info['version'] == 5, 'version 5')
    check(info['bytes_leidos'] == len(data) and info['raices_extra'] == 0, 'consumo exacto de bytes')
    check([t['formato'] for t in info['texturas']] == ['PNG', 'DDS'], 'formatos de textura PNG/DDS detectados')
    check(info['texturas'][0].get('ancho') == 8, 'Pillow mide el PNG (8x4)')
    check(info['materiales'][1]['samplers'][0]['textura'] == 'hierba_d.dds', 'sampler txDiffuse leido')
    check(info['materiales'][0]['props'][0]['valor'] == np.float32(0.4), 'prop ksDiffuse=0.4')
    d = [n for n in info['dummies'] if n['nombre'] == 'AC_START_0'][0]
    tr = d['mundo']['traslacion']
    check(np.allclose(tr, [100.0, 5.0, -200.0], atol=1e-3), f'traslacion dummy recuperada (x,z,-y): {tr}')
    check(abs(d['mundo']['ejes_locales_en_mundo']['y'][1] - 1) < 1e-3, 'eje local Y del dummy apunta a +Y mundo')
    check(d['local']['ortonormal'] and abs(d['local']['determinante'] - 1) < 1e-3, 'rotacion ortonormal det +1')
    road = [m for m in info['mallas'] if m['nombre'] == '1ROAD_pista'][0]
    check(road['frac_normales_arriba'] == 1.0, 'normales 1ROAD +Y')
    check(road['frac_winding_coherente_con_normales'] == 1.0, 'winding del addon coherente con las normales')
    check(road['bbox_mundo']['max'][0] == 1900 and road['bbox_mundo']['max'][2] == 1800, 'bbox mundo 1ROAD')
    hijo = d['hijos'][0]
    check(hijo['tipo'] == 2 and hijo['n_vertices'] == 24 and hijo['n_indices'] == 36, 'hijo malla del dummy 24v/36i')
    check(abs(hijo['bbox_mundo']['min'][0] - 100) < 0.5, 'bbox mundo del hijo usa la matriz del dummy padre')
    # informe completo + comprobaciones (deben fallar las de circuito completo, pero no romper)
    inf = kc.informe_desde_bytes(data, out)
    check(len(inf['comprobaciones']) == 8, '8 comprobaciones generadas')
    check(inf['comprobaciones'][7]['ok'], 'check 8 (bytes) OK en el sintetico')
    check(inf['comprobaciones'][6]['ok'], 'check 7 (normales 1ROAD) OK en el sintetico')
    with open(os.path.join(BASE, 'kn5_refs', 'selftest', '_selftest.json'), 'w', encoding='utf-8') as fh:
        import json
        json.dump(inf, fh, ensure_ascii=False, indent=1)
    # robustez: fichero truncado y magia erronea
    try:
        kc.leer_kn5(data[:-10]); check(False, 'truncado debe lanzar KN5Error')
    except kc.KN5Error as e:
        check('prematuro' in str(e), f'truncado detectado: {e}')
    try:
        kc.leer_kn5(b'sNk5' + data[6:]); check(False, 'magia mala debe lanzar KN5Error')
    except kc.KN5Error as e:
        check('magia' in str(e).lower(), f'magia erronea detectada: {e}')
    print('\nAUTOTEST', 'OK' if not fallos else f'con {len(fallos)} fallos')
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
