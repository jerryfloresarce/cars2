# -*- coding: utf-8 -*-
"""kn5_writer_opt.py - version OPTIMIZADA de kn5_writer.py: misma escena, mismo formato KN5 v5,
muchas menos mallas (draw calls) y menos vertices. kn5_writer.py y kn5_check.py no se tocan.

Formato y convenciones: EXACTAMENTE las de kn5_writer.py (verificadas por un lector independiente):
  * Cabecera b'sc6969' + int32 5; ejes (x, y, z)_blender -> (x, z, -y)_kn5; UV (u, 1 - v);
    winding = orden de loops de Blender; matriz 16 floats m[col][row] por filas (traslacion 12..14);
    material {nombre, shader, blend, alphaTested, depth, props, samplers}; malla {tipo 2, nombre,
    0 hijos, activo, castShadows, visible, transparent, nverts, pos3 nrm3 uv2 tan3, nidx uint16,
    materialId, layer, lodIn, lodOut, centro, radio, renderable}; trozos de <= 65000 vertices.
Optimizaciones (sin cambiar el formato):
  1. SOLDADURA: dentro de cada malla los loops con misma posicion (1e-4), normal (1e-3) y uv (1e-4)
     comparten vertice (antes: un vertice por loop, unidos solo si eran bit a bit iguales).
  2. FUSION por material:
     - decoracion estatica (todo lo que NO sea AC_*, 1ROAD_/1KERB_/1GRASS_/2GRASS_/1WALL_/1DIRT_,
       PIT_LANE, PISTA, TERRENO, AGUA) -> coordenadas MUNDO (matriz del objeto aplicada antes del
       cambio de ejes), mallas 'DECO_<material>_pN' bajo un unico dummy identidad 'DECO';
     - mallas fisicas 1ROAD_/1KERB_/1GRASS_/2GRASS_/1WALL_/1DIRT_ -> coordenadas MUNDO, mallas
       '<prefijo>fusion_<material>_pN' bajo un dummy identidad '<prefijo>fusion' (AC decide la
       fisica por el prefijo del nombre de la malla, que se conserva al principio);
     - fisica SOLO de colision (nombre con 'cierre' o '_invisible': muros de cierre de cierre_ac.py, tira de la
       cuna del pit) -> grupo aparte '<prefijo>invisible' (mallas '<prefijo>invisible_<material>_pN') con
       isRenderable=0 y castShadows=0: nunca se fusiona con mallas visibles;
     - AC_START_/AC_PIT_/AC_TIME_/AC_HOTLAP_START_ (y demas AC_LOGICAL): dummy con la MISMA matriz
       que escribe kn5_writer.py (AC lee de ahi posicion y orientacion) + mini-malla hija en locales
       con isRenderable=0 y castShadows=0 (estructura ksEditor/AcTools; no se ven cubitos);
       TERRENO, AGUA, PISTA, PIT_LANE: dummy por objeto con su matriz y mallas hijas en locales,
       igual que antes (ya eran pocos nodos).
     El winding NO se toca en ningun caso: orden de loops de Blender tras la conversion (x, z, -y),
     igual que kn5_writer.py (comprobado normal-vs-winding 99.99 % por el lector).
     Dentro de cada grupo los objetos se ordenan por curva Z (Morton, celdas de 25 m) antes de
     trocear, de modo que cada malla fusionada cubra una zona compacta (mejor culling en AC).
  3. castShadows = 0 en DECO de VEG_/OLI_ (vegetacion; tambien si el material es MAT_VEG_/MAT_OLI_,
     p. ej. palmeras de HOTEL_/PUERTO_), 1 en el resto de DECO; suelo fisico 0 y 1WALL_ 1 (como
     antes). isTransparent / alphaBlendMode se mantienen por material.
  4. Ninguna textura embebida supera 1024 px: las tintadas se generan a 512 px (como antes), las
     planas son 8x8 y limitar_tamano() reduce cualquier imagen mayor de 1024 antes de embeberla.
Ejecutar:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup
      --python E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/kn5_writer_opt.py
Salida: 04_export/kn5/porto_corsa_opt.kn5 y 04_export/kn5/resumen_writer_opt.json
  (env BLEND / KN5 / KN5_JSON cambian la escena de entrada y las salidas: pruebas en 04_export/_fisica)
"""
import hashlib
import json
import math
import os
import struct
import sys
import time
import zlib

import bpy
import numpy as np
from mathutils import Matrix, Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
# color_ac.py: recalibra color y props de shader para AC (antes el circuito salia casi blanco en el juego);
# env COLOR_AC=0 lo desactiva (colores y SHADER_PROPS de siempre, para comparar)
sys.path.insert(0, os.path.join(BASE, '04_export'))
import color_ac  # noqa: E402
USAR_COLOR_AC = os.environ.get('COLOR_AC', '1') != '0'
# fisica: env BLEND (escena de export), KN5 (kn5 de salida) y KN5_JSON (resumen) para pruebas sobre copias
BLEND = os.environ.get('BLEND') or BASE + r'\04_export\porto_corsa_export.blend'
OUT_KN5 = os.environ.get('KN5') or BASE + r'\04_export\kn5\porto_corsa_opt.kn5'
OUT_JSON = (os.environ.get('KN5_JSON') or (os.path.splitext(OUT_KN5)[0] + '_resumen.json' if os.environ.get('KN5')
                                           else BASE + r'\04_export\kn5\resumen_writer_opt.json'))
ROOT_NAME = 'porto_corsa'
TEX_SIZE = 512            # lado de las texturas tintadas embebidas (las fuentes son de 1024)
TEX_MAX = 1024            # ninguna textura embebida supera este lado
MAX_VERTS = 65000         # limite por malla (indices uint16)
ROUND_POS, ROUND_NRM, ROUND_UV = 1e-4, 1e-3, 1e-4   # redondeos de la soldadura
MORTON_CELL = 25.0        # celda (m) de la curva Z para ordenar espacialmente los objetos fusionados
# castShadows = 0 para objetos/prefijos de suelo (igual que kn5_writer.py)
GROUND_PREFIXES = ('1ROAD', '1DIRT', '1KERB', '1GRASS', '2GRASS', '1PIT', 'AGUA', 'MARCA', 'linea')
# clasificacion de objetos (orden de comprobacion: AC_LOGICAL > FIS_PREFIXES > KEEP_PREFIXES > deco)
AC_LOGICAL = ('AC_START_', 'AC_PIT_', 'AC_TIME_', 'AC_HOTLAP_START_', 'AC_AUDIO_', 'AC_CREW_', 'AC_OPEN_')
FIS_PREFIXES = ('1ROAD_', '1KERB_', '1GRASS_', '2GRASS_', '1WALL_', '1DIRT_', '1PIT_')
KEEP_PREFIXES = ('AC_', 'PIT_LANE', 'PISTA', 'TERRENO', 'AGUA')     # dummy por objeto, como antes
DECO_SIN_SOMBRA = ('VEG_', 'OLI_')                                   # castShadows = 0 dentro de DECO
DECO_MAT_SIN_SOMBRA = ('MAT_VEG_', 'MAT_OLI_')   # ... tambien por material (palmeras de HOTEL_/PUERTO_...)
DECO_NAME = 'DECO'
DEFAULT_MAT = 'MAT_default'
# Orientacion de los objetos logicos (ver kn5_writer.py): giro de 180 grados sobre su eje vertical,
# SOLO para escenas de export v1; con scene['porto_corsa_export_v'] >= 2 (exportar_ac.py actual, ya
# orientados) main() pone todo a False.
AC_GIRAR_180 = {'AC_START_': True, 'AC_HOTLAP_START_': True, 'AC_PIT_': True}
ROT_Z_180 = Matrix.Rotation(math.pi, 4, 'Z')
SHADER_PROPS = (('ksAmbient', 0.45), ('ksDiffuse', 0.55), ('ksSpecular', 0.15),
                ('ksSpecularEXP', 24.0), ('ksEmissive', 0.0), ('ksAlphaRef', 0.0))

# Cambio de ejes Blender (Z arriba) -> AC (Y arriba, Z adelante = -Y blender).  M_kn5 = C @ M @ C^-1
C_AXIS = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
C_AXIS_INV = C_AXIS.inverted()
AX_SWAP = [0, 2, 1]                                  # (x, y, z) -> (x, z, y)
AX_SIGN = np.array([1.0, 1.0, -1.0], dtype=np.float32)  # ... y luego z = -y


class Writer:
    """Escritura binaria little-endian (misma disposicion que KN5Writer del addon de referencia)."""

    def __init__(self, f):
        self.f = f

    def u8(self, v):
        self.f.write(struct.pack('<B', int(v)))

    def i32(self, v):
        self.f.write(struct.pack('<i', int(v)))

    def u32(self, v):
        self.f.write(struct.pack('<I', int(v)))

    def f32(self, v):
        self.f.write(struct.pack('<f', float(v)))

    def floats(self, vals):
        self.f.write(struct.pack('<%df' % len(vals), *[float(v) for v in vals]))

    def string(self, s):
        b = s.encode('utf-8')
        self.u32(len(b))
        self.f.write(b)

    def blob(self, b):
        self.u32(len(b))
        self.f.write(b)

    def matrix(self, m):
        # Igual que KN5Writer.write_matrix del addon: for row: for col: write(matrix[col][row])
        vals = []
        for row in range(4):
            for col in range(4):
                vals.append(m[col][row])
        self.floats(vals)


# ----------------------------------------------------------------------------- color / PNG
def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, np.power((c + 0.055) / 1.055, 2.4)).astype(np.float32)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float32), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055).astype(np.float32)


def png_bytes(img8):
    """Codifica un array uint8 (H, W, 3|4) como PNG (filas de arriba a abajo)."""
    h, w, ch = img8.shape
    ctype = 2 if ch == 3 else 6
    raw = np.concatenate([np.zeros((h, 1), np.uint8), img8.reshape(h, w * ch)], axis=1).tobytes()

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 6))
            + chunk(b'IEND', b''))


_tex_stats = {'reducidas': 0, 'max_lado': 0}


def limitar_tamano(img8, limite=TEX_MAX):
    """Reduce un array (H, W, C) uint8 hasta que ningun lado supere `limite`: media 2x2 mientras los
    lados sean pares y, si aun sobra (lados impares), remuestreo por indices. Las 8x8 no se tocan."""
    h, w = img8.shape[:2]
    _tex_stats['max_lado'] = max(_tex_stats['max_lado'], h, w)
    if max(h, w) <= limite:
        return img8
    x = img8.astype(np.float32)
    while max(x.shape[0], x.shape[1]) > limite and x.shape[0] % 2 == 0 and x.shape[1] % 2 == 0:
        x = x.reshape(x.shape[0] // 2, 2, x.shape[1] // 2, 2, x.shape[2]).mean(axis=(1, 3))
    if max(x.shape[0], x.shape[1]) > limite:
        f = limite / float(max(x.shape[0], x.shape[1]))
        nh, nw = max(1, int(x.shape[0] * f)), max(1, int(x.shape[1] * f))
        ri = (np.arange(nh) * x.shape[0] / nh).astype(int)
        ci = (np.arange(nw) * x.shape[1] / nw).astype(int)
        x = x[ri][:, ci]
    _tex_stats['reducidas'] += 1
    return np.ascontiguousarray((x + 0.5).astype(np.uint8))


_img_cache = {}


def imagen_lineal(img, size):
    """Pixeles RGB lineales (H, W, 3) de una bpy.types.Image, filas arriba->abajo, reducida a `size`."""
    if img.name in _img_cache:
        return _img_cache[img.name]
    res = None
    try:
        n = len(img.pixels)
        w, h = img.size
        if n and w and h:
            buf = np.empty(n, np.float32)
            img.pixels.foreach_get(buf)
            rgb = buf.reshape(h, w, -1)[::-1, :, :3]          # Blender guarda la fila 0 abajo
            lin = srgb_to_lin(rgb)
            while lin.shape[0] > size and lin.shape[0] % 2 == 0 and lin.shape[1] % 2 == 0:
                lin = lin.reshape(lin.shape[0] // 2, 2, lin.shape[1] // 2, 2, 3).mean(axis=(1, 3))
            res = lin.astype(np.float32)
    except Exception as e:  # noqa
        print('AVISO: no se pudo leer la imagen', img.name, e)
    _img_cache[img.name] = res
    return res


# ----------------------------------------------------------------------------- materiales
def _socket(node, identifier):
    for s in node.inputs:
        if s.identifier == identifier:
            return s
    return None


def analizar_material(m):
    """Resume un material de Blender: color base lineal, alpha, imagen de color y su mapping.
    En esta escena el color plano original queda en material.diffuse_color (color de viewport) y la
    cadena de textura es TEX_imagen -> TEX_ganancia(x gain) -> TEX_multiplicar(factor) -> Base Color."""
    info = {'name': m.name, 'color': tuple(float(c) for c in m.diffuse_color[:3]), 'alpha': 1.0,
            'img': None, 'gain': 1.0, 'factor': 1.0, 'scale': 1.0, 'proj': 'FLAT'}
    nt = m.node_tree
    if not nt:
        return info
    principled = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if principled:
        a = principled.inputs['Alpha']
        if not a.is_linked:
            info['alpha'] = float(a.default_value)
        bc = principled.inputs['Base Color']
        if not bc.is_linked:
            info['color'] = tuple(float(c) for c in bc.default_value[:3])
    tex = None
    for n in nt.nodes:
        if (n.bl_idname == 'ShaderNodeTexImage' and n.image
                and n.image.colorspace_settings.name != 'Non-Color' and n.outputs['Color'].is_linked):
            tex = n
            break
    if tex is None:
        return info
    info['img'] = tex.image
    info['proj'] = tex.projection
    gan = nt.nodes.get('TEX_ganancia')
    if gan and gan.bl_idname == 'ShaderNodeMix':
        sb = _socket(gan, 'B_Color')
        if sb is not None and not sb.is_linked:
            info['gain'] = float(sb.default_value[0])
    mul = nt.nodes.get('TEX_multiplicar')
    if mul and mul.bl_idname == 'ShaderNodeMix':
        sf = _socket(mul, 'Factor_Float')
        info['factor'] = float(sf.default_value) if (sf is not None and not sf.is_linked) else 0.6
    mp = nt.nodes.get('TEX_mapping')
    if not (mp and mp.bl_idname == 'ShaderNodeMapping'):
        vin = tex.inputs['Vector']
        if vin.is_linked and vin.links[0].from_node.bl_idname == 'ShaderNodeMapping':
            mp = vin.links[0].from_node
    if mp and mp.bl_idname == 'ShaderNodeMapping':
        info['scale'] = float(mp.inputs['Scale'].default_value[0])
    return info


def construir_textura(info):
    """Devuelve (nombre_png, bytes_png). Imagen tintada 512px o PNG plano 8x8 del color base.
    Antes de codificar, limitar_tamano() garantiza que ningun lado supere TEX_MAX (1024)."""
    color = np.array(info['color'], np.float32).reshape(1, 1, 3)
    alpha = info['alpha']
    lin = imagen_lineal(info['img'], TEX_SIZE) if info['img'] is not None else None
    if lin is None:
        rgb = np.broadcast_to(lin_to_srgb(color), (8, 8, 3))
        nombre = 'flat_%s.png' % info['name']
    else:
        f = info['factor']
        # Ganancia = 1/media LINEAL medida de la imagen, de modo que la media lineal de la textura
        # tintada sea exactamente el color base del material. Ganancia POR CANAL (igual que la version
        # actual de kn5_writer.py): la imagen aporta solo el patron/luminancia y el material fija el tono.
        gain = (1.0 / np.maximum(lin.mean(axis=(0, 1)), 1e-4)).astype(np.float32).reshape(1, 1, 3)
        rgb = lin_to_srgb(color * (1.0 - f + f * lin * gain))
        nombre = 'tex_%s.png' % info['name']
    img8 = (rgb * 255.0 + 0.5).astype(np.uint8)
    if alpha < 0.999:
        a8 = np.full(img8.shape[:2] + (1,), int(round(alpha * 255)), np.uint8)
        img8 = np.concatenate([img8, a8], axis=2)
    img8 = limitar_tamano(np.ascontiguousarray(img8))
    return nombre, png_bytes(np.ascontiguousarray(img8))


def recopilar_materiales(objs):
    """Orden de materiales = orden de primera aparicion; MAT_default siempre presente (slots vacios)."""
    orden = []
    vistos = set()
    for ob in objs:
        for m in ob.data.materials:
            if m is not None and m.name not in vistos:
                vistos.add(m.name)
                orden.append(m)
    infos = [analizar_material(m) for m in orden]
    infos.append({'name': DEFAULT_MAT, 'color': (0.5, 0.5, 0.5), 'alpha': 1.0, 'img': None,
                  'gain': 1.0, 'factor': 1.0, 'scale': 1.0, 'proj': 'FLAT'})
    if USAR_COLOR_AC:       # color para AC (aspecto medido en Blender + modelos de luz de AC) y props por familia
        infos = color_ac.calibrar_todos(infos)
    return infos


def escribir_texturas_y_materiales(w, infos):
    """Escribe la seccion de texturas y la de materiales; anota en cada info su id y textura."""
    texturas = []            # [(nombre, bytes)]
    por_hash = {}
    for info in infos:
        nombre, data = construir_textura(info)
        h = hashlib.md5(data).hexdigest()
        if info['img'] is not None and h in por_hash:
            info['tex'] = por_hash[h]             # misma textura tintada ya embebida
        else:
            por_hash[h] = nombre
            texturas.append((nombre, data))
            info['tex'] = nombre
    w.i32(len(texturas))
    for nombre, data in texturas:
        w.i32(1)                 # activa
        w.string(nombre)
        w.blob(data)
    w.i32(len(infos))
    for mid, info in enumerate(infos):
        info['id'] = mid
        info['transparent'] = info['alpha'] < 0.999
        w.string(info['name'])
        w.string('ksPerPixel')
        w.u8(1 if info['transparent'] else 0)     # alphaBlendMode: 0 opaco, 1 alpha blend
        w.u8(0)                                   # alphaTested
        w.i32(0)                                  # depthMode: DepthNormal
        props = info.get('props_ac', SHADER_PROPS)   # por familia de material (color_ac.FAMILIAS)
        w.i32(len(props))
        for pname, val in props:
            w.string(pname)
            w.f32(val)                            # A
            w.floats((0.0, 0.0))                  # B
            w.floats((val, val, val) if pname == 'ksEmissive' else (0.0, 0.0, 0.0))  # C
            w.floats((0.0, 0.0, 0.0, 0.0))        # D
        w.i32(1)
        w.string('txDiffuse')
        w.i32(0)
        w.string(info['tex'])
    return texturas


# ----------------------------------------------------------------------------- geometria
def arrays_malla(me):
    """Arrays numpy de una malla: triangulos de loops, material y normal por triangulo, posiciones,
    normales de esquina (split normals) y UV del primer uv_layer (o None)."""
    if hasattr(me, 'calc_loop_triangles'):
        me.calc_loop_triangles()
    tris = me.loop_triangles
    nt = len(tris)
    if nt == 0:
        return None
    tl = np.empty(nt * 3, np.int32)
    tris.foreach_get('loops', tl)
    tp = np.empty(nt, np.int32)
    tris.foreach_get('polygon_index', tp)
    npoly = len(me.polygons)
    pm = np.empty(npoly, np.int32)
    me.polygons.foreach_get('material_index', pm)
    pn = np.empty(npoly * 3, np.float32)
    me.polygons.foreach_get('normal', pn)
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    nr = np.empty(len(me.loops) * 3, np.float32)
    me.corner_normals.foreach_get('vector', nr)
    uv = None
    if me.uv_layers:
        uv = np.empty(len(me.loops) * 2, np.float32)
        try:
            me.uv_layers[0].data.foreach_get('uv', uv)
        except (AttributeError, TypeError):
            me.uv_layers[0].uv.foreach_get('vector', uv)
        uv = uv.reshape(-1, 2)
    nmat = max(1, len(me.materials))
    tmat = np.clip(pm[tp], 0, nmat - 1)
    return {'tl': tl.reshape(-1, 3), 'tmat': tmat, 'tnorm': pn.reshape(-1, 3)[tp], 'lv': lv,
            'co': co.reshape(-1, 3), 'nr': nr.reshape(-1, 3), 'uv': uv}


def info_material(me, mi, infos_por_nombre, default_info):
    mat = me.materials[mi] if mi < len(me.materials) else None
    info = infos_por_nombre.get(mat.name) if mat is not None else None
    return info if info is not None else default_info


def loops_grupo(A, mask, info):
    """Por loop del grupo de triangulos `mask`: posicion y normal LOCALES en ejes Blender y UV con la
    v ya invertida. Las UV generadas (material con imagen sin uv_layer) se calculan en locales, igual
    que kn5_writer.py, ANTES de cualquier paso a coordenadas mundo."""
    loops = A['tl'][mask].reshape(-1)
    P = A['co'][A['lv'][loops]]
    N = A['nr'][loops]
    if A['uv'] is not None:
        UV = A['uv'][loops].astype(np.float32)
    elif info['img'] is not None:
        # Reproduce el mapping del material: coordenadas Object * Scale, proyeccion FLAT o BOX
        V = P * np.float32(info['scale'])
        if info['proj'] == 'BOX':
            ax = np.abs(np.repeat(A['tnorm'][mask], 3, axis=0)).argmax(axis=1)[:, None]
            UV = np.where(ax == 2, V[:, [0, 1]], np.where(ax == 0, V[:, [1, 2]], V[:, [0, 2]]))
        else:
            UV = V[:, [0, 1]]
        UV = UV.astype(np.float32)
    else:
        UV = np.zeros((len(loops), 2), np.float32)
    UV[:, 1] = 1.0 - UV[:, 1]                       # v invertida (DirectX)
    return P, N, UV


def a_ejes_kn5(P, N, MW=None):
    """Pasa posiciones y normales a ejes KN5 (x, z, -y). Si se da MW (matriz mundo 4x4 de Blender)
    se aplica antes a P (puntos) y a N (inversa traspuesta, renormalizadas). Devuelve (P, N, espejo),
    espejo=True si det(MW) < 0 (solo informativo: el winding NO se toca, se conserva el orden de loops
    de Blender igual que kn5_writer.py)."""
    espejo = False
    if MW is not None:
        M = np.array(MW, np.float64).reshape(4, 4)
        M3 = M[:3, :3]
        P = P.astype(np.float64) @ M3.T + M[:3, 3]
        try:
            N = N.astype(np.float64) @ np.linalg.inv(M3)      # fila-vector: n' = n . M^-1
        except np.linalg.LinAlgError:
            N = N.astype(np.float64) @ M3.T
        ln = np.linalg.norm(N, axis=1)
        ln[ln < 1e-12] = 1.0
        N = N / ln[:, None]
        espejo = bool(np.linalg.det(M3) < 0)
    P = (P[:, AX_SWAP] * AX_SIGN).astype(np.float32)   # (x, y, z) -> (x, z, -y)
    N = (N[:, AX_SWAP] * AX_SIGN).astype(np.float32)
    return P, N, espejo


def soldar(P, N, UV):
    """SOLDADURA: loops con misma posicion (ROUND_POS), normal (ROUND_NRM) y uv (ROUND_UV) tras
    redondear comparten vertice. Devuelve V (n, 8) = pos3 nrm3 uv2 (valores del primer loop de cada
    clase, sin redondear) e indices por loop (3 por triangulo, orden de Blender conservado)."""
    key = np.concatenate([np.round(P.astype(np.float64) / ROUND_POS),
                          np.round(N.astype(np.float64) / ROUND_NRM),
                          np.round(UV.astype(np.float64) / ROUND_UV)], axis=1).astype(np.int64)
    key = np.ascontiguousarray(key)
    kv = key.view(np.dtype((np.void, key.dtype.itemsize * key.shape[1]))).ravel()
    _, first, inv = np.unique(kv, return_index=True, return_inverse=True)
    V = np.concatenate([P, N, UV], axis=1).astype(np.float32)[first]
    return V, np.asarray(inv).ravel().astype(np.int64)


def con_tangentes(V):
    """Anade la tangente: perpendicular a la normal dentro del plano horizontal AC (Y arriba);
    (1,0,0) si degenera. Igual que kn5_writer.py."""
    Nn = V[:, 3:6]
    T = np.cross(Nn, np.array([0.0, 1.0, 0.0], np.float32)).astype(np.float32)
    ln = np.linalg.norm(T, axis=1)
    malo = ln < 1e-4
    T[malo] = (1.0, 0.0, 0.0)
    ln[malo] = 1.0
    T /= ln[:, None]
    return np.concatenate([V, T], axis=1).astype(np.float32)


def partir(verts, inv):
    """Parte (verts, indices) en trozos de <= MAX_VERTS vertices (bloques de triangulos seguidos)."""
    n = len(verts)
    if n <= MAX_VERTS:
        return [(verts, inv)]
    tri = inv.reshape(-1, 3)
    nt = len(tri)
    out = []
    start = 0
    seen = np.zeros(n, bool)
    BLOCK = 1024
    while start < nt:
        seen[:] = False
        count = 0
        end = start
        while end < nt:
            blk = tri[end:end + BLOCK].ravel()
            nuevos = np.unique(blk[~seen[blk]])
            if count + len(nuevos) > MAX_VERTS and end > start:
                break
            seen[nuevos] = True
            count += len(nuevos)
            end += BLOCK
        chunk = tri[start:end].ravel()
        u, local = np.unique(chunk, return_inverse=True)
        out.append((verts[u], np.asarray(local).ravel().astype(np.int64)))
        start = end
    return out


def clave_espacial(centro):
    """Codigo Morton (curva Z) de la celda XZ (ejes KN5) del centro: ordena espacialmente los objetos
    de un grupo para que cada trozo de <= MAX_VERTS cubra una zona compacta."""
    ix = int((float(centro[0]) + 20000.0) / MORTON_CELL) & 0xFFFF
    iz = int((float(centro[2]) + 20000.0) / MORTON_CELL) & 0xFFFF
    code = 0
    for b in range(16):
        code |= ((ix >> b) & 1) << (2 * b) | ((iz >> b) & 1) << (2 * b + 1)
    return code


def piezas_objeto(me, infos_por_nombre, default_info):
    """Objeto suelto (dummy propio con matriz): lista de (verts, idx, info) en coordenadas LOCALES,
    separadas por material, soldadas y partidas."""
    A = arrays_malla(me)
    if A is None:
        return []
    piezas = []
    for mi in np.unique(A['tmat']):
        info = info_material(me, mi, infos_por_nombre, default_info)
        P, N, UV = loops_grupo(A, A['tmat'] == mi, info)
        P, N, _ = a_ejes_kn5(P, N)
        V, inv = soldar(P, N, UV)
        for v, ix in partir(con_tangentes(V), inv):
            piezas.append((v, ix, info))
    return piezas


def aportar_fusion(me, MW, cast, grupos, infos_por_nombre, default_info, mats_sin_sombra=()):
    """Anade la geometria de un objeto, en coordenadas MUNDO (ejes KN5) y soldada, a los grupos de
    fusion {(cast, material): {'info', 'piezas': [(V8, idx, clave_espacial)]}}. Los materiales cuyo
    nombre empiece por `mats_sin_sombra` fuerzan cast=0. Devuelve (tiene_geometria, espejo)."""
    A = arrays_malla(me)
    if A is None:
        return False, False
    espejo_ob = False
    for mi in np.unique(A['tmat']):
        info = info_material(me, mi, infos_por_nombre, default_info)
        cast_g = 0 if (mats_sin_sombra and info['name'].startswith(mats_sin_sombra)) else cast
        P, N, UV = loops_grupo(A, A['tmat'] == mi, info)
        P, N, espejo = a_ejes_kn5(P, N, MW)
        V, inv = soldar(P, N, UV)                    # winding: orden de loops de Blender, sin tocar
        espejo_ob = espejo_ob or espejo              # (solo se cuenta; ningun objeto lo tiene)
        centro = (V[:, :3].min(0) + V[:, :3].max(0)) / 2.0
        g = grupos.setdefault((cast_g, info['name']), {'info': info, 'piezas': []})
        g['piezas'].append((V, inv.astype(np.int32), clave_espacial(centro)))
    return True, espejo_ob


def fusionar_grupo(g):
    """Concatena las piezas de un grupo en orden espacial, vuelve a soldar entre objetos y parte en
    trozos de <= MAX_VERTS. Devuelve [(verts11, idx)]."""
    piezas = sorted(g['piezas'], key=lambda p: p[2])
    offs = np.cumsum([0] + [len(p[0]) for p in piezas[:-1]])
    V = np.concatenate([p[0] for p in piezas], axis=0)
    idx = np.concatenate([p[1].astype(np.int64) + int(o) for p, o in zip(piezas, offs)])
    V2, inv2 = soldar(V[:, :3], V[:, 3:6], V[:, 6:8])
    return partir(con_tangentes(V2), inv2[idx])


def escribir_malla(w, name, verts, idx, info, cast_shadows, renderable=1):
    w.i32(2)                      # tipo malla
    w.string(name)
    w.i32(0)                      # hijos
    w.u8(1)                       # activo
    w.u8(1 if cast_shadows else 0)
    w.u8(1)                       # visible
    w.u8(1 if info['transparent'] else 0)
    w.i32(len(verts))
    w.f.write(np.ascontiguousarray(verts, dtype='<f4').tobytes())
    w.i32(len(idx))
    w.f.write(np.ascontiguousarray(idx, dtype='<u2').tobytes())
    w.i32(info['id'])
    w.i32(0)                      # layer
    w.f32(0.0)                    # lodIn
    w.f32(0.0)                    # lodOut
    P = verts[:, :3].astype(np.float64)
    c = (P.min(0) + P.max(0)) / 2.0
    r = float(np.sqrt(((P - c) ** 2).sum(1).max())) if len(P) else 0.0
    w.floats((c[0], c[1], c[2]))
    w.f32(r)
    w.u8(1 if renderable else 0)  # renderable (0 en las mini-mallas de los AC_*: no se ven cubitos)


# ----------------------------------------------------------------------------- nodos
def objetos_exportables():
    """Mallas de la view layer (colecciones no excluidas), visibles y renderizables. Las AC_* primero."""
    objs = []
    for ob in bpy.context.view_layer.objects:
        if ob.type != 'MESH' or ob.hide_render or ob.hide_viewport:
            continue
        try:
            if not ob.visible_get():
                continue
        except Exception:  # noqa
            pass
        objs.append(ob)
    objs.sort(key=lambda o: (0 if o.name.startswith(AC_LOGICAL) else 1, o.name))
    return objs


def obtener_malla(ob, depsgraph):
    if ob.modifiers:
        ev = ob.evaluated_get(depsgraph)
        return ev.to_mesh(), ev
    return ob.data, None


def es_invisible(name):
    """Mallas SOLO de colision (cierre_ac.py: muros de cierre, tira de la cuna del pit): nombre con 'cierre' o
    '_invisible'. Se escriben con isRenderable=0 y castShadows=0 y nunca se fusionan con mallas visibles."""
    n = name.lower()
    return 'cierre' in n or '_invisible' in n


def categoria(name):
    """'ac' (dummy logico sin hijos), 'invisible' (fisica solo de colision, fusion aparte), 'fisica' (fusion
    por prefijo), 'suelto' (dummy por objeto, como antes) o 'deco' (fusion por material bajo DECO). Solo una malla
    FISICA puede ser invisible: un decorado con 'cierre' o '_invisible' en el nombre se escribe normal (visible) y
    main() avisa (antes se omitia sin decir nada)."""
    if name.startswith(AC_LOGICAL):
        return 'ac'
    if es_invisible(name) and name.startswith(FIS_PREFIXES):
        return 'invisible'
    if name.startswith(FIS_PREFIXES):
        return 'fisica'
    if name.startswith(KEEP_PREFIXES):
        return 'suelto'
    return 'deco'


def matriz_objeto(ob):
    """Matriz mundo del objeto en ejes KN5 (con el giro de 180 grados de los AC_*), como kn5_writer."""
    MW = ob.matrix_world
    if ob.name.startswith(tuple(p for p, g in AC_GIRAR_180.items() if g)):
        MW = MW @ ROT_Z_180        # giro de 180 grados sobre el eje local vertical
    return C_AXIS @ MW @ C_AXIS_INV


def escribir_dummy(w, name, n_hijos, M):
    w.i32(1)
    w.string(name)
    w.i32(n_hijos)
    w.u8(1)
    w.matrix(M)


class Estado:
    """Contadores y bbox compartidos por los escritores de nodos."""

    def __init__(self):
        self.s = {'n_dummies': 1, 'n_mallas': 0, 'n_verts': 0, 'n_tris': 0, 'n_ac': 0,
                  'mallas_invisible': 0, 'grupos_invisible': 0,
                  'objetos_sin_geometria': 0, 'objetos_partidos': 0, 'objetos_espejo': 0,
                  'mallas_sueltas': 0, 'mallas_fisica': 0, 'mallas_deco': 0, 'mallas_ac': 0,
                  'grupos_fisica': 0, 'grupos_deco': 0, 'grupos_partidos': 0}
        self.bb_min = np.array([np.inf] * 3)
        self.bb_max = np.array([-np.inf] * 3)
        self.ac_nodes = {}

    def malla(self, verts, idx, clase):
        self.s['n_mallas'] += 1
        self.s[clase] += 1
        self.s['n_verts'] += len(verts)
        self.s['n_tris'] += len(idx) // 3

    def bbox(self, P):
        if len(P):
            self.bb_min = np.minimum(self.bb_min, P.min(0))
            self.bb_max = np.maximum(self.bb_max, P.max(0))


def escribir_objeto_suelto(w, ob, depsgraph, por_nombre, default_info, E):
    """Dummy con la matriz mundo del objeto + mallas hijas en locales (igual que kn5_writer.py)."""
    me, ev = obtener_malla(ob, depsgraph)
    piezas = piezas_objeto(me, por_nombre, default_info)
    escribir_dummy(w, ob.name, len(piezas), matriz_objeto(ob))
    E.s['n_dummies'] += 1
    cast = not ob.name.startswith(GROUND_PREFIXES)
    for j, (verts, idx, info) in enumerate(piezas):
        name = ob.name if len(piezas) == 1 else '%s_p%d' % (ob.name, j + 1)
        escribir_malla(w, name, verts, idx, info, cast)
        E.malla(verts, idx, 'mallas_sueltas')
    if len(piezas) > 1:
        E.s['objetos_partidos'] += 1
    if piezas:
        for corner in ob.bound_box:
            wc = ob.matrix_world @ Vector(corner)
            E.bbox(np.array([(wc.x, wc.z, -wc.y)]))
    else:
        E.s['objetos_sin_geometria'] += 1
    if ev is not None:
        ev.to_mesh_clear()


def acumular_fusion(obs, cast_fn, depsgraph, por_nombre, default_info, E, t0, etiqueta, mats_sin_sombra=()):
    """Recorre objetos y devuelve los grupos {(cast, material): {...}} en coordenadas mundo."""
    grupos = {}
    for k, ob in enumerate(obs):
        me, ev = obtener_malla(ob, depsgraph)
        ok, espejo = aportar_fusion(me, ob.matrix_world, cast_fn(ob.name), grupos, por_nombre, default_info,
                                    mats_sin_sombra)
        if ev is not None:
            ev.to_mesh_clear()
        if not ok:
            E.s['objetos_sin_geometria'] += 1
        if espejo:
            E.s['objetos_espejo'] += 1
        if k % 1000 == 0:
            print('  %s: %d/%d objetos acumulados, %d grupos [%.0fs]' % (
                etiqueta, k, len(obs), len(grupos), time.time() - t0))
    return grupos


def escribir_dummy_fusion(w, nombre_dummy, grupos, nombre_fn, clase, E, t0, renderable=1):
    """Dummy identidad con una malla por (material, trozo): '<nombre_fn(material)>_pN'. Con renderable=0
    (mallas solo de colision) se escriben con isRenderable=0 y castShadows=0."""
    claves = sorted(grupos)                                   # (cast, material)
    dobles = {m for c, m in claves if (1 - c, m) in grupos}   # mismo material con y sin sombra
    trozos = []
    for cast, mat in claves:
        base = nombre_fn(mat) + ('_sinsombra' if (mat in dobles and cast == 0) else '')
        g = grupos.pop((cast, mat))
        partes = fusionar_grupo(g)
        for j, (verts, idx) in enumerate(partes):
            trozos.append(('%s_p%d' % (base, j + 1), verts, idx, g['info'], cast))
        E.s['grupos_' + clase] += 1
        if len(partes) > 1:
            E.s['grupos_partidos'] += 1
    escribir_dummy(w, nombre_dummy, len(trozos), Matrix.Identity(4))
    E.s['n_dummies'] += 1
    for name, verts, idx, info, cast in trozos:
        escribir_malla(w, name, verts, idx, info, cast if renderable else 0, renderable)
        E.malla(verts, idx, 'mallas_' + clase)
        E.bbox(verts[:, :3])
    print('  %s: %d grupos -> %d mallas, %d verts [%.0fs]' % (
        nombre_dummy, len(claves), len(trozos), sum(len(t[1]) for t in trozos), time.time() - t0))


# ----------------------------------------------------------------------------- principal
def main():
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    print('blend abierto en %.1fs' % (time.time() - t0))
    export_v = int(bpy.context.scene.get('porto_corsa_export_v', 1))
    if export_v >= 2:
        for _k in AC_GIRAR_180:
            AC_GIRAR_180[_k] = False
    print('escena de export v%d: giro de 180 grados de AC_* %s' % (
        export_v, 'APLICADO (escena antigua)' if any(AC_GIRAR_180.values()) else 'NO necesario'))
    os.makedirs(os.path.dirname(OUT_KN5), exist_ok=True)
    # color_ac: las caras de roca de MAT_terreno (mismo criterio que el nodo de Blender) pasan a MAT_terreno_roca,
    # solo en memoria (el .blend no se guarda)
    roca_ac = color_ac.separar_roca_terreno() if USAR_COLOR_AC else {}
    print('color_ac: %d caras de roca -> %s %s' % (sum(roca_ac.values()), color_ac.ROCA_MAT, roca_ac))
    objs = objetos_exportables()
    infos = recopilar_materiales(objs)
    por_nombre = {i['name']: i for i in infos}
    default_info = por_nombre[DEFAULT_MAT]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cats = {'ac': [], 'fisica': [], 'suelto': [], 'deco': [], 'invisible': [], 'omitir': []}
    for ob in objs:
        cats[categoria(ob.name)].append(ob)
    marcados_visibles = sorted(o.name for o in objs if es_invisible(o.name) and categoria(o.name) != 'invisible')
    if marcados_visibles:
        print('AVISO: %d objetos NO fisicos con "cierre"/"_invisible" en el nombre se escriben VISIBLES (solo una '
              'malla fisica puede ser invisible): %s' % (len(marcados_visibles), marcados_visibles[:20]))
    fis_prefijos = [p for p in FIS_PREFIXES if any(o.name.startswith(p) for o in cats['fisica'])]
    inv_prefijos = [p for p in FIS_PREFIXES if any(o.name.startswith(p) for o in cats['invisible'])]
    E = Estado()
    with open(OUT_KN5, 'wb', buffering=1 << 22) as f:
        w = Writer(f)
        f.write(b'sc6969')
        w.i32(5)
        texturas = escribir_texturas_y_materiales(w, infos)
        print('texturas: %d (%.1f MB, lado max %d), materiales: %d, objetos: %d (AC %d, sueltos %d, '
              'fisica %d, deco %d) [%.1fs]' % (
                  len(texturas), sum(len(d) for _, d in texturas) / 1e6, _tex_stats['max_lado'],
                  len(infos), len(objs), len(cats['ac']), len(cats['suelto']), len(cats['fisica']),
                  len(cats['deco']), time.time() - t0))
        # raiz: dummy identidad > [AC_* | sueltos | <prefijo>fusion... | DECO]
        n_raiz = (len(cats['ac']) + len(cats['suelto']) + len(fis_prefijos) + len(inv_prefijos)
                  + (1 if cats['deco'] else 0))
        escribir_dummy(w, ROOT_NAME, n_raiz, Matrix.Identity(4))
        # 1) objetos logicos AC_*: dummy con su matriz (AC lee de ahi posicion y orientacion; identica
        #    a la de kn5_writer.py) + mini-malla hija en locales con isRenderable=0 y castShadows=0
        #    (misma estructura que ksEditor / el escritor basado en AcTools; sin cubitos visibles).
        for ob in cats['ac']:
            M = matriz_objeto(ob)
            me, ev = obtener_malla(ob, depsgraph)
            piezas = piezas_objeto(me, por_nombre, default_info)
            escribir_dummy(w, ob.name, len(piezas), M)
            E.s['n_dummies'] += 1
            E.s['n_ac'] += 1
            for j, (verts, idx, info) in enumerate(piezas):
                name = ob.name if len(piezas) == 1 else '%s_p%d' % (ob.name, j + 1)
                escribir_malla(w, name, verts, idx, info, cast_shadows=0, renderable=0)
                E.malla(verts, idx, 'mallas_ac')
            if ev is not None:
                ev.to_mesh_clear()
            E.ac_nodes[ob.name] = {'pos_kn5': [round(v, 3) for v in M.translation],
                                   'rot_z_blender_deg': round(math.degrees(ob.rotation_euler.z), 2),
                                   'mini_mallas_no_renderables': len(piezas)}
        # 2) objetos sueltos (TERRENO, AGUA, PISTA, PIT_LANE, otros AC_): dummy por objeto, como antes
        for ob in cats['suelto']:
            escribir_objeto_suelto(w, ob, depsgraph, por_nombre, default_info, E)
        print('  AC %d + sueltos %d escritos (%d mallas) [%.0fs]' % (
            len(cats['ac']), len(cats['suelto']), E.s['mallas_sueltas'], time.time() - t0))
        # 3) fisica: un dummy identidad por prefijo, mallas '<prefijo>fusion_<material>_pN'
        for pref in fis_prefijos:
            obs = [o for o in cats['fisica'] if o.name.startswith(pref)]
            cast = 0 if pref.startswith(GROUND_PREFIXES) else 1
            grupos = acumular_fusion(obs, lambda n, c=cast: c, depsgraph, por_nombre, default_info, E, t0, pref)
            escribir_dummy_fusion(w, pref + 'fusion', grupos,
                                  lambda m, p=pref: '%sfusion_%s' % (p, m), 'fisica', E, t0)
        # 3b) fisica SOLO de colision (cierre_ac.py): dummy '<prefijo>invisible', mallas
        #     '<prefijo>invisible_<material>_pN' con isRenderable=0 y castShadows=0, nunca junto a mallas visibles
        for pref in inv_prefijos:
            obs = [o for o in cats['invisible'] if o.name.startswith(pref)]
            grupos = acumular_fusion(obs, lambda n: 0, depsgraph, por_nombre, default_info, E, t0, pref + 'invisible')
            escribir_dummy_fusion(w, pref + 'invisible', grupos,
                                  lambda m, p=pref: '%sinvisible_%s' % (p, m), 'invisible', E, t0, renderable=0)
        # 4) decoracion estatica: un unico dummy identidad DECO, mallas 'DECO_<material>_pN'
        if cats['deco']:
            grupos = acumular_fusion(cats['deco'], lambda n: 0 if n.startswith(DECO_SIN_SOMBRA) else 1,
                                     depsgraph, por_nombre, default_info, E, t0, DECO_NAME, DECO_MAT_SIN_SOMBRA)
            escribir_dummy_fusion(w, DECO_NAME, grupos, lambda m: '%s_%s' % (DECO_NAME, m), 'deco', E, t0)
    size_mb = os.path.getsize(OUT_KN5) / 1e6
    s = E.s
    resumen = {
        'kn5': OUT_KN5, 'copia': None, 'tamano_MB': round(size_mb, 1),
        'n_texturas': len(texturas), 'texturas_MB': round(sum(len(d) for _, d in texturas) / 1e6, 1),
        'n_materiales': len(infos),
        'materiales_transparentes': [i['name'] for i in infos if i['transparent']],
        'materiales_con_imagen': sum(1 for i in infos if i['img'] is not None),
        'n_nodos_dummy': s['n_dummies'], 'n_mallas': s['n_mallas'],
        'n_vertices': s['n_verts'], 'n_triangulos': s['n_tris'],
        'objetos_partidos': s['objetos_partidos'], 'objetos_sin_geometria': s['objetos_sin_geometria'],
        'n_nodos_AC': s['n_ac'], 'nodos_AC': E.ac_nodes,
        'bbox_kn5_min': [round(float(v), 2) for v in E.bb_min],
        'bbox_kn5_max': [round(float(v), 2) for v in E.bb_max],
        'convenciones': {'cabecera': 'sc6969 + int32 5', 'ejes': '(x,y,z)_blender -> (x,z,-y)_kn5',
                         'winding': 'orden de loops de Blender conservado',
                         'uv': '(u, 1-v)', 'matriz': 'm[col][row] por filas (traslacion en floats 12..14)',
                         'nodos': 'raiz identidad > [AC_* dummy (matriz) > mini-malla isRenderable=0 | dummy por '
                                  'objeto (matriz mundo) > mallas en locales | <prefijo>fusion / DECO identidad > '
                                  'mallas en mundo]',
                         'tex_size': TEX_SIZE, 'tex_max': TEX_MAX, 'max_verts': MAX_VERTS,
                         'soldadura': {'pos': ROUND_POS, 'normal': ROUND_NRM, 'uv': ROUND_UV}},
        'optimizacion': {
            'objetos': {'AC': len(cats['ac']), 'sueltos': len(cats['suelto']),
                        'fisica': len(cats['fisica']), 'deco': len(cats['deco']),
                        'invisible': len(cats['invisible']), 'omitidos': len(cats['omitir'])},
            'mallas_invisibles_solo_colision': s['mallas_invisible'],
            'objetos_invisibles': sorted(o.name for o in cats['invisible']),
            'no_fisicos_con_marca_invisible_escritos_visibles': marcados_visibles,
            'prefijos_fisica': fis_prefijos, 'deco_sin_sombra': list(DECO_SIN_SOMBRA),
            'deco_mat_sin_sombra': list(DECO_MAT_SIN_SOMBRA),
            'mallas_ac_no_renderables': s['mallas_ac'],
            'mallas_sueltas': s['mallas_sueltas'], 'mallas_fisica': s['mallas_fisica'],
            'mallas_deco': s['mallas_deco'], 'grupos_fisica': s['grupos_fisica'],
            'grupos_deco': s['grupos_deco'], 'grupos_partidos': s['grupos_partidos'],
            'objetos_con_det_negativo_(winding_no_tocado)': s['objetos_espejo'],
            'texturas_reducidas_a_%d' % TEX_MAX: _tex_stats['reducidas'],
            'n_nodos_total': s['n_dummies'] + s['n_mallas'], 'orden_espacial_celda_m': MORTON_CELL},
        'segundos': round(time.time() - t0, 1),
        'color_ac': color_ac.informe(infos) if USAR_COLOR_AC else 'desactivado (COLOR_AC=0)',
        'color_ac_roca_terreno': roca_ac,
    }
    json.dump(resumen, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    r2 = dict(resumen)
    r2['nodos_AC'] = '%d nodos (ver json)' % len(E.ac_nodes)
    print('RESUMEN:', json.dumps(r2, indent=1, ensure_ascii=False))
    print('OK KN5 -> %s (%.1f MB)' % (OUT_KN5, size_mb))


main()
