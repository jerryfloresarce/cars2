# -*- coding: utf-8 -*-
"""kn5_check.py - lector INDEPENDIENTE de KN5 v5 (Python 3 del sistema, sin Blender) para validar
porto_corsa.kn5: estructura, contadores, dummies AC_*, bbox global, limites de indices.
Sigue el orden de lectura de kn5-converter (RaduMC, Program.cs) y AcTools Kn5Basic.cs.
Uso: python kn5_check.py <ruta.kn5> [salida.json]
"""
import json
import struct
import sys

import numpy as np


class R:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def take(self, n):
        b = self.d[self.p:self.p + n]
        if len(b) != n:
            raise EOFError('fin de fichero inesperado en offset %d' % self.p)
        self.p += n
        return b

    def i32(self):
        return struct.unpack('<i', self.take(4))[0]

    def u8(self):
        return self.take(1)[0]

    def f32(self):
        return struct.unpack('<f', self.take(4))[0]

    def floats(self, n):
        return struct.unpack('<%df' % n, self.take(4 * n))

    def string(self):
        n = self.i32()
        if n < 0 or n > 10_000_000:
            raise ValueError('longitud de string absurda %d en offset %d' % (n, self.p - 4))
        return self.take(n).decode('utf-8')


def mat_mul_row(points, m16):
    """Aplica una matriz KN5 (16 floats, convencion fila-vector: v' = [v 1] . M) a puntos (N, 3)."""
    M = np.array(m16, np.float64).reshape(4, 4)        # M[row][col] tal como se leyo
    P = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    return (P @ M)[:, :3]


def leer(path):
    data = open(path, 'rb').read()
    r = R(data)
    out = {'fichero': path, 'bytes': len(data), 'problemas': []}
    magic = r.take(6)
    out['magic'] = magic.decode('latin1')
    if magic != b'sc6969':
        out['problemas'].append('cabecera != sc6969')
    out['version'] = r.i32()
    if out['version'] > 5:
        r.i32()
    # texturas
    n_tex = r.i32()
    texs = []
    for _ in range(n_tex):
        act = r.i32()
        name = r.string()
        size = r.i32()
        blob = r.take(size)
        kind = 'PNG' if blob[:8] == b'\x89PNG\r\n\x1a\n' else ('DDS' if blob[:3] == b'DDS' else 'otro')
        texs.append({'name': name, 'size': size, 'tipo': kind, 'activa': act})
        if kind == 'otro':
            out['problemas'].append('textura %s no es PNG/DDS' % name)
    out['n_texturas'] = n_tex
    out['texturas_MB'] = round(sum(t['size'] for t in texs) / 1e6, 2)
    out['texturas'] = texs[:12] + ([{'...': n_tex - 12}] if n_tex > 12 else [])
    tex_names = {t['name'] for t in texs}
    # materiales
    n_mat = r.i32()
    mats = []
    for _ in range(n_mat):
        m = {'name': r.string(), 'shader': r.string(), 'blend': r.u8(), 'alphaTested': r.u8(),
             'depth': r.i32(), 'props': {}, 'samplers': {}}
        for _ in range(r.i32()):
            pn = r.string()
            a = r.f32()
            r.floats(2 + 3 + 4)
            m['props'][pn] = round(a, 4)
        for _ in range(r.i32()):
            sn = r.string()
            slot = r.i32()
            tn = r.string()
            m['samplers'][sn] = (slot, tn)
            if tn not in tex_names:
                out['problemas'].append('material %s referencia textura inexistente %s' % (m['name'], tn))
        if 'txDiffuse' not in m['samplers']:
            out['problemas'].append('material %s sin txDiffuse' % m['name'])
        mats.append(m)
    out['n_materiales'] = n_mat
    out['materiales_muestra'] = mats[:3]
    out['materiales_alpha'] = [m['name'] for m in mats if m['blend'] != 0]
    # nodos (recursivo, iterativo con pila)
    stats = {'dummies': 0, 'mallas': 0, 'verts': 0, 'tris': 0, 'max_verts_malla': 0,
             'mallas_sin_tris': 0, 'skinned': 0}
    ac = {}
    bbox_min = np.array([np.inf] * 3)
    bbox_max = np.array([-np.inf] * 3)
    nombres_malla_prefijo = {}
    ident = tuple(float(x) for x in np.eye(4).ravel())

    def leer_nodo(parent_world):
        tipo = r.i32()
        name = r.string()
        n_hijos = r.i32()
        activo = r.u8()
        if tipo == 1:
            m16 = r.floats(16)
            M = np.array(m16, np.float64).reshape(4, 4)
            world = M @ parent_world            # fila-vector: local primero, luego padre
            stats['dummies'] += 1
            if name.startswith('AC_'):
                pos = mat_mul_row(np.zeros((1, 3)), world.ravel())[0]
                fwd = (np.array([[0, 0, 1.0]]) @ world[:3, :3])[0]
                ac[name] = {'pos': [round(float(v), 3) for v in pos],
                            'eje_z_local_en_mundo': [round(float(v), 3) for v in fwd], 'hijos': n_hijos}
            for _ in range(n_hijos):
                leer_nodo(world)
            return
        if tipo not in (2, 3):
            raise ValueError('tipo de nodo desconocido %d (%s) en offset %d' % (tipo, name, r.p))
        if n_hijos != 0:
            out['problemas'].append('malla %s con hijos' % name)
        cast, vis, transp = r.u8(), r.u8(), r.u8()
        if tipo == 3:
            stats['skinned'] += 1
            for _ in range(r.i32()):
                r.string()
                r.floats(16)
        nv = r.i32()
        stride = 11 if tipo == 2 else 19
        vbuf = np.frombuffer(r.take(nv * stride * 4), dtype='<f4').reshape(nv, stride)
        ni = r.i32()
        idx = np.frombuffer(r.take(ni * 2), dtype='<u2')
        mat_id = r.i32()
        layer = r.i32()
        if tipo == 2:
            lod_in, lod_out = r.f32(), r.f32()
            centro = r.floats(3)
            radio = r.f32()
            render = r.u8()
        else:
            r.f32()
            r.f32()
            r.take(8)
        stats['mallas'] += 1
        stats['verts'] += nv
        stats['tris'] += ni // 3
        stats['max_verts_malla'] = max(stats['max_verts_malla'], nv)
        if ni == 0:
            stats['mallas_sin_tris'] += 1
        if nv > 65535:
            out['problemas'].append('malla %s con %d vertices (>65535)' % (name, nv))
        if ni % 3 != 0:
            out['problemas'].append('malla %s: n_indices %d no multiplo de 3' % (name, ni))
        if ni and int(idx.max()) >= nv:
            out['problemas'].append('malla %s: indice %d >= nverts %d' % (name, int(idx.max()), nv))
        if not (0 <= mat_id < n_mat):
            out['problemas'].append('malla %s: materialId %d fuera de rango' % (name, mat_id))
        if nv:
            pw = mat_mul_row(vbuf[:, :3].astype(np.float64), parent_world.ravel())
            bbox_min[:] = np.minimum(bbox_min, pw.min(0))
            bbox_max[:] = np.maximum(bbox_max, pw.max(0))
            nl = np.linalg.norm(vbuf[:, 3:6], axis=1)
            if np.any(np.abs(nl - 1) > 0.05):
                out['problemas'].append('malla %s: normales no unitarias' % name)
            if tipo == 2 and radio <= 0 and nv > 1:
                out['problemas'].append('malla %s: radio de esfera <= 0' % name)
        pref = name.split('_')[0]
        nombres_malla_prefijo[pref] = nombres_malla_prefijo.get(pref, 0) + 1

    leer_nodo(np.eye(4))
    if r.p != len(data):
        out['problemas'].append('sobran %d bytes tras el arbol de nodos' % (len(data) - r.p))
    out['nodos'] = stats
    out['prefijos_mallas'] = dict(sorted(nombres_malla_prefijo.items(), key=lambda kv: -kv[1])[:25])
    out['n_AC'] = len(ac)
    out['AC'] = dict(sorted(ac.items()))
    out['bbox_kn5_min'] = [round(float(v), 2) for v in bbox_min]
    out['bbox_kn5_max'] = [round(float(v), 2) for v in bbox_max]
    return out


if __name__ == '__main__':
    res = leer(sys.argv[1])
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    res_print = dict(res)
    res_print['AC'] = {k: v for k, v in list(res['AC'].items())[:6]}
    print(json.dumps(res_print, indent=1, ensure_ascii=False))
    print('PROBLEMAS:', len(res['problemas']))
