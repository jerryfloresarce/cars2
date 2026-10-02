#!/usr/bin/env python3
"""kn5_check.py -- lector/validador INDEPENDIENTE de ficheros KN5 (Assetto Corsa), version 5.

Sin bpy: Python 3.12 del sistema + struct + numpy (+ Pillow opcional para medir texturas).

REFERENCIA PRINCIPAL del formato (lector, distinto del addon de Blender):
  * kn5-converter, RaduMC (Chipicao), C#: "kn5 converter/Program.cs" funciones readKN5() y
    readNodes()  -> copia en 04_export/kn5_refs/kn5-converter/
  Cruzado con:
  * actools (gro-ove / x4fab, Content Manager), C#: AcTools/Kn5File/Kn5Basic.cs clase Kn5Reader
    (ReadHeader/ReadTexture/ReadMaterial/ReadNode) y Kn5Writer.cs -> 04_export/kn5_refs/actools/
  * kn5-obj-converter (MarvinSt), Python: convert.py (port directo de kn5-converter) -> 04_export/kn5_refs/
  * blender-assetto-corsa-tools (jwl-7), Python, SOLO como escritor: exporter/kn5_writer.py,
    node_writer.py, material_writer.py, texture_writer.py -> 04_export/kn5_refs/blender-assetto-corsa-tools/

DISCREPANCIAS con la hoja del encargo (las referencias coinciden entre si):
  1. La magia son 6 bytes ASCII 'sc6969' (no 'sNk5'), seguidos de int32 version (=5).
     Si version > 5 hay un int32 extra (no aplica a v5).
  2. En el material, el "int16 alphaBlendMode" son en realidad DOS bytes: uint8 alphaBlendMode
     (0 opaco, 1 alphaBlend, 2 alphaToCoverage) + uint8 alphaTested (bool). Luego int32 depthMode.
  3. La matriz del dummy son 16 float32 en orden "fila-mayor con vectores fila" (DirectX):
     la traslacion ocupa los floats 12,13,14 (tmatrix[3,0..2] en kn5-converter) y el vertice se
     transforma v' = v * M. Equivale a la matriz de vector-columna de Blender/numpy guardada en
     columna-mayor (el addon escribe matrix[col][row] con row externo). Aqui: M_numpy = f.reshape(4,4).T
  4. UV: kn5-converter aplica v_obj = 1 - v_kn5 al exportar a OBJ (la V en KN5 esta "invertida"
     estilo DirectX); el addon escribe (u, -v). Para texturas repetidas (wrap) ambas coinciden mod 1.
  5. Ejes: el addon convierte Blender (x, y, z) -> KN5 (x, z, -y) (rotacion +90 grados en X,
     determinante +1, asi que el orden de los triangulos NO se invierte: escribe (i1, i2, i0)).
     kn5-converter exporta a OBJ sin tocar ejes ni orden de indices.
  6. Tras materialId: int32 layer, float lodIn, float lodOut, vec3 centro esfera, float radio,
     uint8 isRenderable = 29 bytes (kn5-converter hace Position += 29). Malla skinned: tras layer
     solo 8 bytes (lodIn, lodOut) y sin esfera ni isRenderable (actools: "MisteryBytes").
  7. El fichero contiene UN unico arbol de nodos (una sola raiz); ambos lectores leen una raiz
     y paran. Tras la raiz no debe quedar ningun byte.

Uso:
  python kn5_check.py [ruta.kn5] [salida.json] [--json salida.json] [--wait-min 40] [--no-wait] [--quiet]
Codigos de salida: 0 todas las comprobaciones OK, 1 alguna FALLO, 2 kn5 no disponible, 3 error de lectura.
"""
from __future__ import annotations

import json
import math
import os
import struct
import sys
import time

import numpy as np

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa\04_export'
KN5_DEFAULT = os.path.join(BASE, 'kn5', 'porto_corsa.kn5')
JSON_DEFAULT = os.path.join(BASE, 'kn5', 'informe_check.json')

MAGIC = b'sc6969'
NODE_DUMMY, NODE_MESH, NODE_SKINNED = 1, 2, 3
NODE_TYPE_NAME = {1: 'dummy', 2: 'malla', 3: 'malla_skinned'}
BLEND_MODE_NAME = {0: 'Opaque', 1: 'AlphaBlend', 2: 'AlphaToCoverage'}
DEPTH_MODE_NAME = {0: 'DepthNormal', 1: 'DepthNoWrite', 2: 'DepthOff'}
MAX_VERTS = 65535          # indices uint16
PREFIJOS_FISICA = ('1ROAD_', '1KERB_', '1GRASS_', '1WALL_')
PREFIJOS_FISICA_TODOS = PREFIJOS_FISICA + ('1DIRT_', '2GRASS_', '1PIT_')   # "plano del circuito" (sin fondos: mar, cielo)
AC_REQUERIDOS = ([f'AC_START_{i}' for i in range(20)] + [f'AC_PIT_{i}' for i in range(20)]
                 + ['AC_TIME_0_L', 'AC_TIME_0_R', 'AC_TIME_1_L', 'AC_TIME_1_R', 'AC_HOTLAP_START_0'])


class KN5Error(Exception):
    pass


class Reader:
    """Lector binario little-endian sobre bytes en memoria, con control estricto de limites."""

    def __init__(self, data: bytes):
        self.d = data
        self.p = 0
        self.avisos: list[str] = []

    def need(self, n: int):
        if n < 0:
            raise KN5Error(f'longitud negativa ({n}) en offset {self.p}')
        if self.p + n > len(self.d):
            raise KN5Error(f'fin de fichero prematuro en offset {self.p}: se necesitan {n} bytes y quedan '
                           f'{len(self.d) - self.p}')

    def raw(self, n: int) -> bytes:
        self.need(n)
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def i32(self) -> int:
        return struct.unpack_from('<i', self.raw(4))[0]

    def u32(self) -> int:
        return struct.unpack_from('<I', self.raw(4))[0]

    def u16(self) -> int:
        return struct.unpack_from('<H', self.raw(2))[0]

    def u8(self) -> int:
        return self.raw(1)[0]

    def f32(self) -> float:
        return struct.unpack_from('<f', self.raw(4))[0]

    def vec(self, n: int) -> list[float]:
        return list(struct.unpack_from(f'<{n}f', self.raw(4 * n)))

    def string(self) -> str:
        # kn5-converter: ReadStr(binStream, binStream.ReadInt32()) -> UTF8
        n = self.i32()
        if n < 0 or n > 1_000_000:
            raise KN5Error(f'longitud de cadena absurda ({n}) en offset {self.p - 4}')
        b = self.raw(n)
        try:
            return b.decode('utf-8')
        except UnicodeDecodeError:
            self.avisos.append(f'cadena no UTF-8 en offset {self.p - n}')
            return b.decode('utf-8', errors='replace')


def detectar_formato(blob: bytes) -> str:
    if blob[:8] == b'\x89PNG\r\n\x1a\n':
        return 'PNG'
    if blob[:4] == b'DDS ':
        return 'DDS'
    if blob[:3] == b'\xff\xd8\xff':
        return 'JPEG'
    if blob[:2] in (b'BM',):
        return 'BMP'
    if blob[:2] in (b'II', b'MM'):
        return 'TIFF'
    return 'DESCONOCIDO(' + blob[:4].hex() + ')'


def medir_imagen(blob: bytes):
    """(ancho, alto, modo) con Pillow si esta disponible; None si no se puede."""
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(blob))
        return [im.width, im.height, im.mode]
    except Exception:
        return None


def leer_texturas(r: Reader) -> list[dict]:
    n = r.i32()
    if n < 0 or n > 100_000:
        raise KN5Error(f'numero de texturas absurdo: {n}')
    texturas = []
    for i in range(n):
        off = r.p
        activa = r.i32()          # kn5-converter: texType (1 = activa)
        nombre = r.string()
        tam = r.i32()
        blob = r.raw(tam)
        tex = {'indice': i, 'offset': off, 'activa': activa, 'nombre': nombre, 'tamano': tam,
               'formato': detectar_formato(blob) if tam else 'VACIA'}
        dims = medir_imagen(blob) if tam else None
        if dims:
            tex['ancho'], tex['alto'], tex['modo'] = dims
        texturas.append(tex)
    return texturas


def leer_materiales(r: Reader, version: int) -> list[dict]:
    n = r.i32()
    if n < 0 or n > 100_000:
        raise KN5Error(f'numero de materiales absurdo: {n}')
    mats = []
    for i in range(n):
        off = r.p
        nombre = r.string()
        shader = r.string()
        blend = r.u8()            # actools: ReadBlendMode (byte)
        alpha_tested = r.u8()     # actools: ReadBoolean
        depth = r.i32() if version > 4 else 0   # kn5-converter: if (version > 4) ReadInt32()
        n_props = r.i32()
        if n_props < 0 or n_props > 10_000:
            raise KN5Error(f'numero de propiedades absurdo ({n_props}) en material {nombre!r}')
        props = []
        for _ in range(n_props):
            pn = r.string()
            a = r.f32()
            b = r.vec(2)
            c = r.vec(3)
            d = r.vec(4)          # 4 + 8 + 12 + 16 = 36 bytes tras el nombre (kn5-converter: += 36)
            props.append({'nombre': pn, 'valor': a, 'vec2': b, 'vec3': c, 'vec4': d})
        n_samp = r.i32()
        if n_samp < 0 or n_samp > 1000:
            raise KN5Error(f'numero de samplers absurdo ({n_samp}) en material {nombre!r}')
        samplers = []
        for _ in range(n_samp):
            sn = r.string()
            slot = r.i32()
            tn = r.string()
            samplers.append({'nombre': sn, 'slot': slot, 'textura': tn})
        mats.append({'indice': i, 'offset': off, 'nombre': nombre, 'shader': shader,
                     'alphaBlendMode': blend, 'alphaBlendMode_nombre': BLEND_MODE_NAME.get(blend, '?'),
                     'alphaTested': alpha_tested, 'depthMode': depth,
                     'depthMode_nombre': DEPTH_MODE_NAME.get(depth, '?'),
                     'props': props, 'samplers': samplers})
    return mats


def matriz_desde_floats(f: np.ndarray) -> np.ndarray:
    """16 floats del fichero -> matriz 4x4 de vector-columna (p' = M @ p), traslacion en M[:3, 3].
    kn5-converter: tmatrix[i, j] = float[i*4+j]; traslacion = tmatrix[3, 0..2]; v' = v * tmatrix (vector fila).
    Transponer da la forma de vector columna."""
    return np.asarray(f, dtype=np.float64).reshape(4, 4).T


def descomponer(M: np.ndarray) -> dict:
    R = M[:3, :3]
    escala = np.linalg.norm(R, axis=0)
    out = {'traslacion': M[:3, 3].round(4).tolist(), 'escala': escala.round(4).tolist()}
    ejes = {}
    for k, nombre in enumerate(('x', 'y', 'z')):
        col = R[:, k] / (escala[k] if escala[k] > 1e-9 else 1.0)
        ejes[nombre] = col.round(4).tolist()
    out['ejes_locales_en_mundo'] = ejes
    # rumbo (grados) del eje local Z proyectado en el plano horizontal XZ de AC (atan2(x, z))
    z = R[:, 2]
    out['rumbo_eje_z_deg'] = round(math.degrees(math.atan2(z[0], z[2])), 2) if np.hypot(z[0], z[2]) > 1e-6 else None
    out['determinante'] = round(float(np.linalg.det(R)), 4)
    out['ortonormal'] = bool(np.allclose(R.T @ R, np.diag(escala ** 2), atol=1e-3))
    return out


def leer_nodo(r: Reader, padre_mundo: np.ndarray, ruta: str, profundidad: int, acc: dict) -> dict:
    """Lee un nodo (recursivo) tal como kn5-converter readNodes(): tipo, nombre, n_hijos, activo, cuerpo, hijos."""
    off = r.p
    tipo = r.i32()
    nombre = r.string()
    n_hijos = r.i32()
    activo = r.u8()
    if tipo not in NODE_TYPE_NAME:
        raise KN5Error(f'tipo de nodo desconocido {tipo} en offset {off} (nombre {nombre!r})')
    if n_hijos < 0 or n_hijos > 1_000_000:
        raise KN5Error(f'numero de hijos absurdo ({n_hijos}) en nodo {nombre!r}')
    ruta_n = (ruta + '/' if ruta else '') + nombre
    nodo = {'tipo': tipo, 'tipo_nombre': NODE_TYPE_NAME[tipo], 'nombre': nombre, 'ruta': ruta_n,
            'offset': off, 'n_hijos': n_hijos, 'activo': activo, 'profundidad': profundidad}
    mundo = padre_mundo
    if tipo == NODE_DUMMY:
        f = np.frombuffer(r.raw(64), dtype='<f4')
        M = matriz_desde_floats(f)
        mundo = padre_mundo @ M
        nodo['matriz_16f'] = [round(float(x), 6) for x in f]
        nodo['es_identidad'] = bool(np.allclose(M, np.eye(4), atol=1e-6))
        nodo['local'] = descomponer(M)
        nodo['mundo'] = descomponer(mundo)
        acc['dummies'].append(nodo)
    else:
        nodo['castShadows'] = r.u8()
        nodo['isVisible'] = r.u8()
        nodo['isTransparent'] = r.u8()
        if tipo == NODE_SKINNED:
            n_huesos = r.i32()
            huesos = []
            for _ in range(n_huesos):
                hn = r.string()
                hm = np.frombuffer(r.raw(64), dtype='<f4')
                huesos.append({'nombre': hn, 'matriz_16f': [round(float(x), 6) for x in hm]})
            nodo['huesos'] = huesos
        nv = r.i32()
        if nv < 0 or nv > 50_000_000:
            raise KN5Error(f'numero de vertices absurdo ({nv}) en malla {nombre!r}')
        ancho = 19 if tipo == NODE_SKINNED else 11    # floats por vertice: 76 o 44 bytes
        V = np.frombuffer(r.raw(nv * ancho * 4), dtype='<f4').reshape(nv, ancho) if nv else np.zeros((0, ancho), '<f4')
        ni = r.i32()
        if ni < 0 or ni > 200_000_000:
            raise KN5Error(f'numero de indices absurdo ({ni}) en malla {nombre!r}')
        I = np.frombuffer(r.raw(ni * 2), dtype='<u2') if ni else np.zeros((0,), '<u2')
        nodo['materialId'] = r.i32()
        nodo['layer'] = r.i32()
        nodo['lodIn'] = r.f32()
        nodo['lodOut'] = r.f32()
        if tipo == NODE_MESH:
            nodo['esfera_centro'] = [round(x, 4) for x in r.vec(3)]
            nodo['esfera_radio'] = round(r.f32(), 4)
            nodo['isRenderable'] = r.u8()
        nodo['n_vertices'] = nv
        nodo['n_indices'] = ni
        nodo['n_triangulos'] = ni // 3
        pos = V[:, 0:3].astype(np.float64)
        nrm = V[:, 3:6].astype(np.float64)
        uv = V[:, 6:8].astype(np.float64)
        road_stat = None
        if nv:
            pm = pos @ mundo[:3, :3].T + mundo[:3, 3]
            nodo['bbox_local'] = {'min': pos.min(0).round(3).tolist(), 'max': pos.max(0).round(3).tolist()}
            nodo['bbox_mundo'] = {'min': pm.min(0).round(3).tolist(), 'max': pm.max(0).round(3).tolist()}
            nodo['uv_rango'] = {'min': uv.min(0).round(3).tolist(), 'max': uv.max(0).round(3).tolist()}
            nodo['normal_media'] = nrm.mean(0).round(4).tolist()
            ln_n = np.linalg.norm(nrm, axis=1)
            validas = ln_n > 0.5                      # normal nula = (0,0,0): defecto del escritor
            n_nulas = int((~validas).sum())
            nodo['n_normales_nulas'] = n_nulas
            nodo['frac_normales_arriba'] = round(float((nrm[:, 1] > 0).mean()), 4)
            nodo['frac_normales_arriba_validas'] = (round(float((nrm[validas, 1] > 0).mean()), 4)
                                                    if validas.any() else None)
            nodo['normales_unitarias'] = bool(np.allclose(ln_n[validas], 1.0, atol=0.02)) if validas.any() else False
            nodo['dist_max_origen_local'] = round(float(np.linalg.norm(pos, axis=1).max()), 3)
            acc['bbox_min'] = np.minimum(acc['bbox_min'], pm.min(0))
            acc['bbox_max'] = np.maximum(acc['bbox_max'], pm.max(0))
            if n_nulas:
                acc['normales_nulas_total'] += n_nulas
                acc['mallas_normales_nulas'].append((ruta_n, n_nulas, int(nv)))
            if pm.min(0)[[0, 2]].min() < -2500 or pm.max(0)[[0, 2]].max() > 2500:
                acc['lejanas'].append((ruta_n, int(nv), nodo['bbox_mundo']))
            if nombre.startswith(PREFIJOS_FISICA_TODOS):
                acc['fis_min'] = np.minimum(acc['fis_min'], pm.min(0))
                acc['fis_max'] = np.maximum(acc['fis_max'], pm.max(0))
            if nombre.startswith('1ROAD_'):
                acc['road_min'] = np.minimum(acc['road_min'], pm.min(0))
                acc['road_max'] = np.maximum(acc['road_max'], pm.max(0))
                road_stat = {'ruta': ruta_n, 'nv': int(nv), 'n_nulas': n_nulas,
                             'sum_ny_valid': float(nrm[validas, 1].sum()), 'n_up_valid': int((nrm[validas, 1] > 0).sum()),
                             'area': 0.0, 'area_up': 0.0, 'area_down': 0.0}
                acc['road_normales'].append(road_stat)
        if ni and nv:
            nodo['indice_max'] = int(I.max())
            nodo['indices_fuera_rango'] = int((I >= nv).sum())
            if ni % 3 == 0 and nodo['indices_fuera_rango'] == 0:
                T = I.reshape(-1, 3).astype(np.int64)
                a, b, c = pos[T[:, 0]], pos[T[:, 1]], pos[T[:, 2]]
                fn = np.cross(b - a, c - a)
                ln = np.linalg.norm(fn, axis=1)
                ok = ln > 1e-12
                nodo['triangulos_degenerados'] = int((~ok).sum())
                if ok.any():
                    nv_med = nrm[T[:, 0]] + nrm[T[:, 1]] + nrm[T[:, 2]]
                    dots = (fn[ok] * nv_med[ok]).sum(1)
                    nodo['frac_winding_coherente_con_normales'] = round(float((dots > 0).mean()), 4)
                    # orientacion GEOMETRICA ponderada por area (|cross| = 2*area): lo que ve la fisica/culling
                    area = ln[ok]
                    ny_f = fn[ok, 1] / area
                    a_tot = float(area.sum())
                    nodo['area_m2'] = round(a_tot / 2, 2)
                    nodo['frac_area_normal_arriba'] = round(float(area[ny_f > 0].sum() / a_tot), 4)
                    nodo['frac_area_normal_abajo'] = round(float(area[ny_f < -0.3].sum() / a_tot), 4)
                    if road_stat is not None:
                        road_stat.update(area=a_tot, area_up=float(area[ny_f > 0].sum()),
                                         area_down=float(area[ny_f < -0.3].sum()))
        else:
            nodo['indice_max'] = -1
            nodo['indices_fuera_rango'] = 0
        acc['mallas'].append(nodo)
        acc['total_vertices'] += nv
        acc['total_indices'] += ni
    acc['n_nodos'] += 1
    hijos = []
    for _ in range(n_hijos):
        hijos.append(leer_nodo(r, mundo, ruta_n, profundidad + 1, acc))
    nodo['hijos'] = hijos
    return nodo


def _dist(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)))


def comprobar(info: dict, acc: dict) -> list[dict]:
    """Las 8 comprobaciones de sanidad para un circuito de AC (+ extras informativas)."""
    checks: list[dict] = []

    def add(num, nombre, ok, detalle, **cifras):
        checks.append({'num': num, 'nombre': nombre, 'ok': bool(ok), 'detalle': detalle, 'cifras': cifras})

    mallas = acc['mallas']
    dummies = acc['dummies']
    n_mats = len(info['materiales'])
    hay_road = bool(np.isfinite(acc['road_min']).all())
    road_bb = {'min': acc['road_min'].round(2).tolist(), 'max': acc['road_max'].round(2).tolist()} if hay_road else None

    # (1) dummies logicos AC_*
    por_nombre: dict[str, list] = {}
    for d in dummies:
        por_nombre.setdefault(d['nombre'], []).append(d)
    mallas_nombre = {m['nombre'] for m in mallas}
    faltan, identidad, duplicados, son_malla, fuera_bbox, eje_mal, hijo_lejos = [], [], [], [], [], [], []
    posiciones = {}
    for nombre in AC_REQUERIDOS:
        ds = por_nombre.get(nombre, [])
        if not ds:
            faltan.append(nombre)
            if nombre in mallas_nombre:
                son_malla.append(nombre)
            continue
        if len(ds) > 1:
            duplicados.append(nombre)
        d = ds[0]
        if d['es_identidad']:
            identidad.append(nombre)
        p = d['mundo']['traslacion']
        posiciones[nombre] = p
        if d['mundo']['ejes_locales_en_mundo']['y'][1] < 0.9:
            eje_mal.append(nombre)
        if hay_road:
            lo, hi = acc['road_min'], acc['road_max']
            if not (lo[0] - 30 <= p[0] <= hi[0] + 30 and lo[2] - 30 <= p[2] <= hi[2] + 30
                    and lo[1] - 5 <= p[1] <= hi[1] + 5):
                fuera_bbox.append(nombre)
        for h in d['hijos']:
            if h['tipo'] != NODE_DUMMY and h.get('dist_max_origen_local', 0) > 2.0:
                hijo_lejos.append(f"{nombre} (hijo {h['nombre']} a {h['dist_max_origen_local']} m del origen local)")
    starts = [posiciones.get(f'AC_START_{i}') for i in range(20)]
    d_consec = [round(_dist(a, b), 2) for a, b in zip(starts, starts[1:]) if a is not None and b is not None]
    d_fila = [round(_dist(starts[i], starts[i + 2]), 2) for i in range(18)
              if starts[i] is not None and starts[i + 2] is not None]
    fila_ok = bool(d_fila) and all(5.0 <= x <= 12.0 for x in d_fila)
    consec_ok = bool(d_consec) and all(1.5 <= x <= 20.0 for x in d_consec)
    # orientacion: en AC el coche mira hacia +Z local del dummy (en aero.ini el aleron trasero tiene Z negativa).
    # La parrilla va de AC_START_2 (detras) a AC_START_0 (delante): ese vector es la direccion de marcha.
    angulo_z = None
    if starts[0] is not None and starts[2] is not None and 'AC_START_0' in por_nombre:
        v = np.asarray(starts[0]) - np.asarray(starts[2])
        v[1] = 0.0
        z = np.asarray(por_nombre['AC_START_0'][0]['mundo']['ejes_locales_en_mundo']['z'], float)
        z[1] = 0.0
        if np.linalg.norm(v) > 1e-6 and np.linalg.norm(z) > 1e-6:
            cosang = float(np.dot(v, z) / (np.linalg.norm(v) * np.linalg.norm(z)))
            angulo_z = round(math.degrees(math.acos(max(-1.0, min(1.0, cosang)))), 1)
    extras_ac = sorted(n for n in por_nombre if n.startswith('AC_') and n not in AC_REQUERIDOS)
    ok1 = not faltan and not identidad and not duplicados and fila_ok and consec_ok and not fuera_bbox and not eje_mal
    det = []
    det.append(f'{len(AC_REQUERIDOS) - len(faltan)}/{len(AC_REQUERIDOS)} dummies requeridos presentes')
    if faltan:
        det.append('FALTAN: ' + ', '.join(faltan))
    if son_malla:
        det.append('estan como MALLA en vez de dummy (AC no leera su posicion): ' + ', '.join(son_malla))
    if identidad:
        det.append('con matriz IDENTIDAD: ' + ', '.join(identidad))
    if duplicados:
        det.append('duplicados: ' + ', '.join(duplicados))
    if eje_mal:
        det.append('eje local Y no apunta arriba (+Y mundo): ' + ', '.join(eje_mal))
    if fuera_bbox:
        det.append('fuera de la bbox de 1ROAD (+30 m XZ, +5 m Y): ' + ', '.join(fuera_bbox))
    if hijo_lejos:
        det.append('AVISO posible doble transformacion: ' + '; '.join(hijo_lejos))
    det.append(f'AC_START i->i+2 (fila, ~8 m): {d_fila}')
    det.append(f'AC_START consecutivos: {d_consec}')
    if angulo_z is not None:
        det.append(f'angulo entre +Z local de AC_START_0 y la direccion de marcha (START_2->START_0): {angulo_z} deg '
                   + ('(coche mirando hacia la meta)' if angulo_z < 20 else
                      '(AVISO: ~180 => los coches saldrian de espaldas si AC usa +Z como frente)' if angulo_z > 160
                      else '(AVISO: no alineado)'))
    if extras_ac:
        det.append('otros AC_* presentes: ' + ', '.join(extras_ac))
    add(1, 'dummies AC_START/AC_PIT/AC_TIME/AC_HOTLAP con matriz y posiciones plausibles', ok1, ' | '.join(det),
        posiciones={k: [round(x, 2) for x in v] for k, v in posiciones.items()},
        rumbo_eje_z_deg={k: por_nombre[k][0]['mundo']['rumbo_eje_z_deg'] for k in posiciones})

    # (2) prefijos fisicos
    cuenta = {p: sum(1 for m in mallas if m['nombre'].startswith(p)) for p in PREFIJOS_FISICA}
    otros = {}
    for m in mallas:
        pre = m['nombre'].split('_')[0] + '_' if '_' in m['nombre'] else '(sin prefijo)'
        if pre not in PREFIJOS_FISICA:
            otros[pre] = otros.get(pre, 0) + 1
    ok2 = all(v > 0 for v in cuenta.values())
    add(2, 'mallas con prefijos 1ROAD_/1KERB_/1GRASS_/1WALL_', ok2,
        f'conteo por prefijo requerido: {cuenta} | otros prefijos de malla (top 12): '
        f'{dict(sorted(otros.items(), key=lambda kv: -kv[1])[:12])}', conteo=cuenta)

    # (3) indices y materialId en rango
    malos = []
    for m in mallas:
        prob = []
        if m['indices_fuera_rango']:
            prob.append(f"{m['indices_fuera_rango']} indices >= n_vertices")
        if m['n_indices'] % 3:
            prob.append('n_indices no multiplo de 3')
        if not (0 <= m['materialId'] < n_mats):
            prob.append(f"materialId {m['materialId']} fuera de [0,{n_mats})")
        if m['n_vertices'] == 0 or m['n_indices'] == 0:
            prob.append('malla vacia')
        if prob:
            malos.append(f"{m['ruta']}: " + ', '.join(prob))
    add(3, 'indices dentro de n_vertices y materialId dentro del rango de materiales', not malos,
        f'{len(mallas) - len(malos)}/{len(mallas)} mallas correctas' + (' | ' + '; '.join(malos[:10]) if malos else ''),
        n_mallas_malas=len(malos))

    # (4) limite de vertices
    grandes = [(m['ruta'], m['n_vertices']) for m in mallas if m['n_vertices'] > MAX_VERTS]
    maxv = max((m['n_vertices'] for m in mallas), default=0)
    add(4, f'ninguna malla supera {MAX_VERTS} vertices', not grandes,
        f'malla mas grande: {maxv} vertices' + (f' | exceden: {grandes[:10]}' if grandes else ''), max_vertices=maxv)

    # (5) texturas referenciadas
    nombres_tex = {t['nombre'] for t in info['texturas']}
    faltan_tex, usadas = [], set()
    for mt in info['materiales']:
        for s in mt['samplers']:
            if s['textura']:
                usadas.add(s['textura'])
                if s['textura'] not in nombres_tex:
                    faltan_tex.append(f"{mt['nombre']}.{s['nombre']} -> {s['textura']!r}")
    sin_uso = sorted(nombres_tex - usadas)
    add(5, 'todas las texturas referenciadas por samplers existen en la tabla', not faltan_tex,
        f'{len(usadas)} nombres de textura referenciados, {len(nombres_tex)} en tabla'
        + (' | FALTAN: ' + '; '.join(faltan_tex) if faltan_tex else '')
        + (f' | sin referenciar: {sin_uso}' if sin_uso else ''), faltan=faltan_tex)

    # (6) bbox del "plano del circuito" = mallas fisicas (1ROAD_/1KERB_/1GRASS_/1WALL_/1DIRT_/2GRASS_).
    #     La bbox GLOBAL incluye fondos (mar, cielo) que pueden medir decenas de km: se informa, no decide.
    if np.isfinite(acc['bbox_min']).all():
        hay_fis = bool(np.isfinite(acc['fis_min']).all())
        base = 'mallas fisicas' if hay_fis else 'todas las mallas (no hay fisicas)'
        lo, hi = (acc['fis_min'], acc['fis_max']) if hay_fis else (acc['bbox_min'], acc['bbox_max'])
        ext = hi - lo
        glo, ghi = acc['bbox_min'], acc['bbox_max']
        gext = ghi - glo
        y_ok = -30 <= lo[1] <= 30 and 50 <= hi[1] <= 400
        xz_ok = 1000 <= ext[0] <= 3200 and 1000 <= ext[2] <= 3200
        pista = ''
        if ext[1] > 800 and (ext[0] < 500 or ext[2] < 500):
            pista = ' | PARECE QUE NO SE CONVIRTIERON LOS EJES (la extension grande esta en Y)'
        lej = ', '.join(f"{r.split('/')[-1]} ({n} v)" for r, n, _ in acc['lejanas'][:8])
        add(6, 'bbox del circuito (mallas fisicas): Y (arriba) entre ~3 y ~150 m y plano XZ de ~1900 x 1800 m',
            y_ok and xz_ok,
            f'[{base}] X [{lo[0]:.1f}, {hi[0]:.1f}] ext {ext[0]:.0f} m | Y [{lo[1]:.1f}, {hi[1]:.1f}] ext {ext[1]:.0f} m | '
            f'Z [{lo[2]:.1f}, {hi[2]:.1f}] ext {ext[2]:.0f} m | bbox 1ROAD: {road_bb} | bbox GLOBAL con fondos: '
            f'X ext {gext[0]:.0f} m, Y [{glo[1]:.1f}, {ghi[1]:.1f}], Z ext {gext[2]:.0f} m'
            + (f' | mallas lejanas (> 2500 m del origen, fondos): {lej}' if lej else '') + pista,
            bbox_fisicas_min=lo.round(2).tolist(), bbox_fisicas_max=hi.round(2).tolist(),
            bbox_global_min=glo.round(2).tolist(), bbox_global_max=ghi.round(2).tolist(), bbox_1road=road_bb,
            lejanas=[r for r, _, _ in acc['lejanas']])
    else:
        add(6, 'bbox del circuito', False, 'no hay mallas con vertices')

    # (7) normales de 1ROAD hacia +Y
    #     Metrica principal: normal GEOMETRICA de cada triangulo (winding) ponderada por su AREA, que es lo que
    #     ve la fisica y el culling. Por vertice se informa tambien, pero los laterales verticales de los caminos
    #     (muchos vertices, poca area) no deben decidir.
    rn = acc['road_normales']
    if rn:
        tot = sum(s['nv'] for s in rn)
        nulas = sum(s['n_nulas'] for s in rn)
        valid = max(tot - nulas, 1)
        frac_v = sum(s['n_up_valid'] for s in rn) / valid
        media = sum(s['sum_ny_valid'] for s in rn) / valid
        A = sum(s['area'] for s in rn)
        frac_a = sum(s['area_up'] for s in rn) / A if A else 0.0
        frac_down = sum(s['area_down'] for s in rn) / A if A else 1.0
        peores = sorted((s for s in rn if s['area'] > 0), key=lambda s: s['area_up'] / s['area'])[:5]
        wind = [m.get('frac_winding_coherente_con_normales') for m in mallas if m['nombre'].startswith('1ROAD_')]
        wind = [w for w in wind if w is not None]
        ok7 = frac_a >= 0.85 and frac_down <= 0.05 and nulas <= 0.01 * tot and frac_v > 0.5 and media > 0.3
        add(7, 'normales de las mallas 1ROAD_ mayoritariamente hacia +Y (geometricas, ponderadas por area)', ok7,
            f'{len(rn)} mallas 1ROAD_, {tot} vertices, {A / 2:.0f} m2: area con normal ny>0 = {frac_a:.3f}, '
            f'area hacia ABAJO (ny<-0.3) = {frac_down:.3f} | por vertice: fraccion ny>0 = {frac_v:.3f}, ny medio = {media:.3f}, '
            f'normales nulas = {nulas} | winding coherente con normales de vertice (fraccion, min/media): '
            f'{min(wind):.3f}/{sum(wind) / len(wind):.3f} | mallas con menos area arriba (laterales verticales): '
            f"{[(s['ruta'].split('/')[-1], round(s['area_up'] / s['area'], 3)) for s in peores]}",
            frac_area_arriba=round(frac_a, 4), frac_area_abajo=round(frac_down, 4), frac_vertices_arriba=round(frac_v, 4),
            ny_medio=round(media, 4), normales_nulas=nulas, area_m2=round(A / 2, 1))
    else:
        add(7, 'normales de las mallas 1ROAD_ hacia +Y', False, 'no hay mallas 1ROAD_')

    # (8) consumo exacto de bytes
    sobran = info['bytes_fichero'] - info['bytes_leidos']
    add(8, 'la lectura consume exactamente todos los bytes del fichero', sobran == 0 and info['raices_extra'] == 0,
        f"fichero {info['bytes_fichero']} bytes, leidos {info['bytes_leidos']}, sobran {sobran}"
        + (f" | hay {info['raices_extra']} nodo(s) raiz EXTRA tras el primero (AC/CM solo leen una raiz)"
           if info['raices_extra'] else ''), bytes_sobrantes=sobran)
    return checks


REFERENCIA = ('kn5-converter (RaduMC/Chipicao, C#, Program.cs readKN5/readNodes) como lector principal; cruzado con '
              'actools Kn5Basic.cs::Kn5Reader + Kn5Writer.cs (gro-ove, Content Manager), kn5-obj-converter (MarvinSt, '
              'Python) y con el escritor del addon blender-assetto-corsa-tools (jwl-7). Magia 6 bytes "sc6969" + int32 version.')


def _acc_nuevo() -> dict:
    return {'dummies': [], 'mallas': [], 'n_nodos': 0, 'total_vertices': 0, 'total_indices': 0,
            'bbox_min': np.full(3, np.inf), 'bbox_max': np.full(3, -np.inf),
            'fis_min': np.full(3, np.inf), 'fis_max': np.full(3, -np.inf),
            'road_min': np.full(3, np.inf), 'road_max': np.full(3, -np.inf), 'road_normales': [],
            'normales_nulas_total': 0, 'mallas_normales_nulas': [], 'lejanas': []}


def leer_kn5(data: bytes) -> dict:
    """Lee el fichero completo. Devuelve dict con cabecera, texturas, materiales, raiz (arbol crudo), listas planas."""
    r = Reader(data)
    magia = r.raw(6)
    if magia != MAGIC:
        raise KN5Error(f'magia incorrecta: {magia!r}; se esperaba {MAGIC!r} (kn5-converter/actools/addon coinciden)')
    version = r.i32()
    extra = r.i32() if version > 5 else None   # kn5-converter: if (version > 5) ReadInt32()
    if version != 5:
        r.avisos.append(f'version {version} distinta de 5 (AC usa 5; se sigue leyendo)')
    texturas = leer_texturas(r)
    materiales = leer_materiales(r, version)
    acc = _acc_nuevo()
    raiz = leer_nodo(r, np.eye(4), '', 0, acc)
    bytes_leidos = r.p
    raices_extra, nodos_extra = 0, []
    while r.p < len(data):            # NO deberia haber nada: AC/CM leen una sola raiz
        try:
            nodos_extra.append(leer_nodo(r, np.eye(4), '', 0, _acc_nuevo()))
            raices_extra += 1
        except KN5Error as e:
            r.avisos.append(f'bytes sobrantes tras la raiz no parsean como nodo: {e}')
            break
    return {'version': version, 'extra_cabecera': extra, 'texturas': texturas, 'materiales': materiales,
            'raiz': raiz, 'nodos_extra': nodos_extra, 'raices_extra': raices_extra,
            'dummies': acc['dummies'], 'mallas': acc['mallas'], 'avisos': r.avisos,
            'bytes_fichero': len(data), 'bytes_leidos': bytes_leidos, '_acc': acc}


def _sin_hijos(n: dict) -> dict:
    return {k: v for k, v in n.items() if k != 'hijos'}


_CAMPOS_MALLA = ('ruta', 'tipo_nombre', 'offset', 'n_vertices', 'n_indices', 'n_triangulos', 'materialId', 'layer',
                 'lodIn', 'lodOut', 'esfera_centro', 'esfera_radio', 'isRenderable', 'isVisible', 'isTransparent',
                 'castShadows', 'bbox_mundo', 'dist_max_origen_local', 'indices_fuera_rango', 'n_normales_nulas',
                 'frac_normales_arriba', 'frac_area_normal_arriba', 'frac_area_normal_abajo', 'area_m2',
                 'frac_winding_coherente_con_normales', 'triangulos_degenerados')


def _malla_compacta(m: dict) -> dict:
    return {k: m[k] for k in _CAMPOS_MALLA if k in m}


def _arbol_compacto(n: dict) -> dict:
    c = {'tipo': n['tipo_nombre'], 'nombre': n['nombre'], 'n_hijos': n['n_hijos']}
    if n['tipo'] == NODE_DUMMY:
        c['traslacion_local'] = n['local']['traslacion']
        c['identidad'] = n['es_identidad']
    else:
        c['n_vertices'] = n['n_vertices']
        c['n_indices'] = n['n_indices']
        c['materialId'] = n['materialId']
        c['isRenderable'] = n.get('isRenderable')
    if n['hijos']:
        c['hijos'] = [_arbol_compacto(h) for h in n['hijos']]
    return c


def informe_desde_bytes(data: bytes, ruta: str) -> dict:
    info = leer_kn5(data)
    checks = comprobar(info, info['_acc'])
    acc = info['_acc']
    tex_bytes = sum(t['tamano'] for t in info['texturas'])
    informe = {
        'fichero': ruta, 'generado': time.strftime('%Y-%m-%d %H:%M:%S'), 'referencia_formato': REFERENCIA,
        'cabecera': {'magia': MAGIC.decode(), 'version': info['version'], 'extra': info['extra_cabecera']},
        'totales': {'bytes_fichero': info['bytes_fichero'], 'bytes_texturas': tex_bytes,
                    'n_texturas': len(info['texturas']), 'n_materiales': len(info['materiales']),
                    'n_nodos': acc['n_nodos'], 'n_dummies': len(acc['dummies']), 'n_mallas': len(acc['mallas']),
                    'n_mallas_skinned': sum(1 for m in acc['mallas'] if m['tipo'] == NODE_SKINNED),
                    'total_vertices': acc['total_vertices'], 'total_indices': acc['total_indices'],
                    'total_triangulos': acc['total_indices'] // 3,
                    'profundidad_max': max((n['profundidad'] for n in acc['dummies'] + acc['mallas']), default=0)},
        'texturas': info['texturas'], 'materiales': info['materiales'],
        'arbol': _arbol_compacto(info['raiz']),
        'dummies': [_sin_hijos(d) for d in acc['dummies']],
        'mallas': [_malla_compacta(m) for m in acc['mallas']],
        'extras': {
            'normales_nulas_total': acc['normales_nulas_total'],
            'mallas_con_normales_nulas': len(acc['mallas_normales_nulas']),
            'mallas_con_normales_nulas_top': sorted(acc['mallas_normales_nulas'], key=lambda t: -t[1])[:15],
            'mallas_lejanas_mas_de_2500m': [{'ruta': r, 'n_vertices': n, 'bbox_mundo': b} for r, n, b in acc['lejanas']],
            'mallas_no_renderables': sum(1 for m in acc['mallas'] if m.get('isRenderable') == 0),
            'mallas_transparentes': sum(1 for m in acc['mallas'] if m.get('isTransparent')),
            'nota_mallas': 'cada entrada de "mallas" es compacta; bbox_local/uv/normales por malla se obtienen con '
                           'leer_kn5() desde Python',
        },
        'comprobaciones': checks,
        'resultado': 'OK' if all(c['ok'] for c in checks) else 'FALLO',
        'avisos': info['avisos'],
    }
    if info['nodos_extra']:
        informe['nodos_raiz_extra'] = [_arbol_compacto(n) for n in info['nodos_extra']]
    return informe


def _print_arbol(n: dict, nivel: int, lineas: list[str]):
    if n['tipo'] == 'dummy':
        t = n['traslacion_local']
        lineas.append('  ' * nivel + f"[dummy] {n['nombre']}  hijos={n['n_hijos']}  "
                      + ('identidad' if n['identidad'] else f't=({t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f})'))
    else:
        lineas.append('  ' * nivel + f"[{n['tipo']}] {n['nombre']}  v={n['n_vertices']} i={n['n_indices']} "
                      f"mat={n['materialId']} render={n['isRenderable']}")
    for h in n.get('hijos', []):
        _print_arbol(h, nivel + 1, lineas)


def imprimir(inf: dict, quiet: bool = False):
    p = print
    p(f"== KN5 {inf['fichero']}  ({inf['totales']['bytes_fichero']} bytes)  version {inf['cabecera']['version']}")
    p('   referencia:', inf['referencia_formato'])
    if not quiet:
        p(f"\n-- TEXTURAS ({inf['totales']['n_texturas']}, {inf['totales']['bytes_texturas']} bytes)")
        for t in inf['texturas']:
            dims = f" {t.get('ancho')}x{t.get('alto')} {t.get('modo', '')}" if 'ancho' in t else ''
            p(f"   [{t['indice']}] {t['nombre']}  {t['tamano']} B  {t['formato']}{dims}  activa={t['activa']}")
        p(f"\n-- MATERIALES ({inf['totales']['n_materiales']})")
        for m in inf['materiales']:
            props = ', '.join(f"{q['nombre']}={q['valor']:.3g}" for q in m['props'])
            samp = ', '.join(f"{s['nombre']}[{s['slot']}]={s['textura']}" for s in m['samplers'])
            p(f"   [{m['indice']}] {m['nombre']}  shader={m['shader']}  blend={m['alphaBlendMode_nombre']} "
              f"alphaTested={m['alphaTested']} depth={m['depthMode_nombre']}\n        props: {props}\n        samplers: {samp}")
        lineas: list[str] = []
        _print_arbol(inf['arbol'], 0, lineas)
        p(f"\n-- ARBOL DE NODOS ({inf['totales']['n_nodos']} nodos, {inf['totales']['n_dummies']} dummies, "
          f"{inf['totales']['n_mallas']} mallas, profundidad max {inf['totales']['profundidad_max']})")
        for ln in lineas[:700]:
            p('   ' + ln)
        if len(lineas) > 700:
            p(f'   ... ({len(lineas) - 700} lineas mas en el JSON)')
        p('\n-- MALLAS (detalle)')
        for m in inf['mallas'][:400]:
            bb = m.get('bbox_mundo')
            bbs = f"bbox_mundo=[{bb['min']} .. {bb['max']}]" if bb else 'sin vertices'
            p(f"   {m['ruta']}: v={m['n_vertices']} i={m['n_indices']} mat={m['materialId']} "
              f"r_esfera={m.get('esfera_radio')} render={m.get('isRenderable')} {bbs}")
        if len(inf['mallas']) > 400:
            p(f"   ... ({len(inf['mallas']) - 400} mallas mas en el JSON)")
    ac = [d for d in inf.get('dummies', []) if d['nombre'].startswith('AC_')]
    if ac:
        p(f'\n-- DUMMIES AC_* ({len(ac)}): posicion mundo (x, y, z) KN5 y rumbo del eje Z local (grados, atan2(x, z))')
        for d in ac:
            t = d['mundo']['traslacion']
            ey = d['mundo']['ejes_locales_en_mundo']['y']
            p(f"   {d['nombre']:<18} t=({t[0]:9.2f}, {t[1]:7.2f}, {t[2]:9.2f})  rumbo_z={d['mundo']['rumbo_eje_z_deg']}"
              f"  ejeY_local->mundo=({ey[0]:.2f}, {ey[1]:.2f}, {ey[2]:.2f})  escala={d['local']['escala']}"
              + ('  IDENTIDAD' if d['es_identidad'] else ''))
    p('\n-- TOTALES', json.dumps(inf['totales']))
    if inf.get('extras'):
        ex = inf['extras']
        p(f"-- EXTRAS: normales nulas = {ex['normales_nulas_total']} (en {ex['mallas_con_normales_nulas']} mallas) | "
          f"mallas lejanas (>2500 m): {[d['ruta'].split('/')[-1] for d in ex['mallas_lejanas_mas_de_2500m']]} | "
          f"no renderables: {ex['mallas_no_renderables']} | transparentes: {ex['mallas_transparentes']}")
    p('\n-- COMPROBACIONES')
    for c in inf['comprobaciones']:
        p(f"   ({c['num']}) {'OK   ' if c['ok'] else 'FALLO'} {c['nombre']}\n        {c['detalle']}")
    for a in inf['avisos']:
        p('   AVISO:', a)
    p('\nRESULTADO:', inf['resultado'])


def guardar_json(inf: dict, ruta_json: str):
    if os.path.dirname(ruta_json):
        os.makedirs(os.path.dirname(ruta_json), exist_ok=True)
    with open(ruta_json, 'w', encoding='utf-8') as fh:
        json.dump(inf, fh, ensure_ascii=False, indent=1,
                  default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))


def esperar_fichero(ruta: str, max_min: float) -> bool:
    t0 = time.time()
    while not os.path.exists(ruta):
        if time.time() - t0 >= max_min * 60:
            return False
        print(f"[{time.strftime('%H:%M:%S')}] esperando {ruta} ... ({(time.time() - t0) / 60:.0f}/{max_min:.0f} min)",
              flush=True)
        time.sleep(60)
    # esperar a que el tamano se estabilice (otro agente puede estar escribiendo)
    prev, t1 = -1, time.time()
    while time.time() - t1 < 600:
        s = os.path.getsize(ruta)
        if s == prev and s > 0:
            break
        prev = s
        time.sleep(10)
    return True


def informe_error(ruta: str, err: str) -> dict:
    checks = [{'num': i, 'nombre': 'no evaluado (error de lectura)', 'ok': False, 'detalle': err, 'cifras': {}}
              for i in range(1, 9)]
    return {'fichero': ruta, 'generado': time.strftime('%Y-%m-%d %H:%M:%S'), 'referencia_formato': REFERENCIA,
            'error': err, 'comprobaciones': checks, 'resultado': 'FALLO', 'avisos': [],
            'totales': {'bytes_fichero': os.path.getsize(ruta) if os.path.exists(ruta) else 0}}


def main(argv: list[str]) -> int:
    args, i = [], 0
    while i < len(argv):                 # posicionales = lo que no es opcion ni valor de --json/--wait-min
        if argv[i] in ('--json', '--wait-min'):
            i += 2
            continue
        if not argv[i].startswith('--'):
            args.append(argv[i])
        i += 1
    ruta = args[0] if args else KN5_DEFAULT
    ruta_json = argv[argv.index('--json') + 1] if '--json' in argv else (args[1] if len(args) > 1 else JSON_DEFAULT)
    wait_min = float(argv[argv.index('--wait-min') + 1]) if '--wait-min' in argv else 40.0
    if '--no-wait' in argv:
        wait_min = 0.0
    quiet = '--quiet' in argv
    t0 = time.time()
    if not esperar_fichero(ruta, wait_min):
        print('kn5 no disponible:', ruta)
        return 2
    while True:
        with open(ruta, 'rb') as fh:
            data = fh.read()
        try:
            inf = informe_desde_bytes(data, ruta)
            break
        except KN5Error as e:
            restante = wait_min * 60 - (time.time() - t0)
            if 'prematuro' in str(e) and restante > 0:
                print(f"[{time.strftime('%H:%M:%S')}] fichero incompleto ({e}); reintento en 30 s", flush=True)
                time.sleep(30)
                continue
            inf = informe_error(ruta, f'{type(e).__name__}: {e}')
            guardar_json(inf, ruta_json)
            print('ERROR DE LECTURA:', e)
            print('RESULTADO: FALLO  (informe en', ruta_json + ')')
            return 3
    guardar_json(inf, ruta_json)
    imprimir(inf, quiet)
    print('informe JSON ->', ruta_json)
    return 0 if inf['resultado'] == 'OK' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
