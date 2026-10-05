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
v1.2 (05/10/2026, decision 16 del coordinador; PETICIONES_04_EXPORT.md P1/P2/P6/P10/X7):
  5. TERRENO por texel (TERRENO_MODO, por defecto 'detalle' = opcion (b); 'base' = opcion (a)): en (a) MAT_terreno sale
     como ksPerPixel (el mismo shader y el mismo formato PNG que v1.1) con txDiffuse = texturas/terreno_base.png a 2048 (1 m/texel: paleta x parches x AO, la roca ya
     pintada por texel) y UV PLANAR DE MUNDO u = (x - x0)/Lx, v = (y - y0)/Ly en TODAS las caras con MAT_terreno (TERRENO,
     arcenes, falda del McLaren; es la UV que pinta Blender por Geometry.Position). La textura se calibra con color_ac
     como un material cuyo albedo es la media de terreno_base en tierra firme (ganancia por canal: conserva el dibujo).
     color_ac.separar_roca_terreno(modo='base') solo separa las paredes casi verticales que no son suelo (caliza P1).
     'detalle' (b, por defecto) = (a) + grano de 3 m con ksPerPixelMultiMap/txDetail (ver material_terreno_detalle:
     nombres verificados en kn5_refs, semantica de CM cubierta con alfa 0.5); eleccion y pruebas en
     04_export/_v12_dev/medidas/comparacion_terreno.json (kn5_vista + medir_capturas de a/b/c/tile);
     'tile' = v1.1 (tile hierba seca 512 a 3 m, roca por cara; IGNORA la UV 0..1 del terreno, P10 interino);
     'caras' = opcion (c) de la tarea (4 materiales por cara segun la mascara, tiles de 3-6 m): solo para comparar.
     TERRENO_DDS=1: la textura del terreno como DDS A8R8G8B8 con mipmaps (formato del ensayo D de kn5_ensayo.py).
  6. P2: lado de las texturas tintadas por material: 1024 para familias roca/asfalto y para los materiales con
     ac_tex_max >= 1024 (MCOCHE/PPUEBLO caliza, MAT_cesped...), 512 el resto (TEX_P2=0: todo a 512 como v1.1).
  7. P6: HORIZ_ (montes del horizonte a 2-5 km) sin sombra (DECO_SIN_SOMBRA).
  8. P3 (solo lo seguro): ac_shader distinto de ksPerPixel se ignora con aviso (el multicapa NO va en v1.2); el resumen
     compara la imagen que elige analizar_material con ac_samplers['txDiffuse'] (sin cambiar nada).
Ejecutar:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup
      --python E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/kn5_writer_opt.py
Salida: 04_export/kn5/porto_corsa_opt.kn5 y 04_export/kn5/resumen_writer_opt.json
  (env BLEND / KN5 / KN5_JSON cambian la escena de entrada y las salidas: pruebas en 04_export/_fisica;
   env GEOM = geometria de la escena (rejilla del terreno para la UV planar; si falta se ajusta a la UV del TERRENO);
   env TERRENO_BASE / TERRENO_MASK = copia congelada de las texturas del terreno (hacer_zip.sh v1.2))
Importable (ensayo_f_pueblo.py): main() solo corre como script (__name__ == '__main__').
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
ROOT_NAME = os.environ.get('KN5_RAIZ') or 'porto_corsa'
TEX_SIZE = 512            # lado de las texturas tintadas embebidas (las fuentes son de 1024)
TEX_MAX = 1024            # ninguna textura embebida supera este lado (salvo la del terreno por texel: TEX_TERRENO)
# v1.2 -------------------------------------------------------------------------------------------------------------
TERRENO_MODO = os.environ.get('TERRENO_MODO', 'detalle')   # 'detalle' (v1.2, opcion b) | 'base' (a) | 'tile' (v1.1) | 'caras' (c)
TERRENO_DDS = os.environ.get('TERRENO_DDS', '0') == '1'     # textura del terreno como DDS con mipmaps
TEX_TERRENO = 2048                                          # terreno_base.png tal cual (1 m/texel)
TERRENO_MAT = 'MAT_terreno'
GEOM_JSON = os.environ.get('GEOM')
TEX_P2 = os.environ.get('TEX_P2', '1') != '0'               # P2: 1024 para roca/asfalto y ac_tex_max >= 1024
TEX_SIZE_P2 = 1024
TEX_P2_FAMILIAS = ('roca', 'asfalto')
SHADERS_V12 = ('ksPerPixel',)                               # ac_shader que se respeta en v1.2 (el multicapa espera a la foto A;
                                                            # MAT_terreno en modo 'detalle' sale como ksPerPixelMultiMap)
PLANAR = {}                                                 # x0, y0, Lx, Ly de la UV planar del terreno (main)
MAX_VERTS = 65000         # limite por malla (indices uint16)
ROUND_POS, ROUND_NRM, ROUND_UV = 1e-4, 1e-3, 1e-4   # redondeos de la soldadura
MORTON_CELL = 25.0        # celda (m) de la curva Z para ordenar espacialmente los objetos fusionados
# castShadows = 0 para objetos/prefijos de suelo (igual que kn5_writer.py)
GROUND_PREFIXES = ('1ROAD', '1DIRT', '1KERB', '1GRASS', '2GRASS', '1PIT', 'AGUA', 'MARCA', 'linea')
# clasificacion de objetos (orden de comprobacion: AC_LOGICAL > FIS_PREFIXES > KEEP_PREFIXES > deco)
AC_LOGICAL = ('AC_START_', 'AC_PIT_', 'AC_TIME_', 'AC_HOTLAP_START_', 'AC_AUDIO_', 'AC_CREW_', 'AC_OPEN_')
FIS_PREFIXES = ('1ROAD_', '1KERB_', '1GRASS_', '2GRASS_', '1WALL_', '1DIRT_', '1PIT_')
KEEP_PREFIXES = ('AC_', 'PIT_LANE', 'PISTA', 'TERRENO', 'AGUA')     # dummy por objeto, como antes
DECO_SIN_SOMBRA = ('VEG_', 'OLI_', 'HORIZ_')                         # castShadows = 0 dentro de DECO (v1.2: + HORIZ_, P6)
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


def dds_bytes(img8):
    """DDS sin comprimir A8R8G8B8 (BGRA en memoria) con la cadena COMPLETA de mipmaps (media 2x2 de los valores tal cual:
    AC sombrea en espacio gamma y la textura es UNORM). Mismo formato y cabecera que kn5_ensayo.dds_mips (ensayo D).
    img8 (H, W, 3|4) uint8, lados potencia de 2. Devuelve (bytes, n_niveles)."""
    h, w = img8.shape[:2]
    rgba = img8 if img8.shape[2] == 4 else np.concatenate([img8, np.full((h, w, 1), 255, np.uint8)], axis=2)
    x = rgba.astype(np.float32)
    niveles = []
    while True:
        q = np.clip(x + 0.5, 0, 255).astype(np.uint8)
        niveles.append(np.ascontiguousarray(q[..., [2, 1, 0, 3]]).tobytes())
        if x.shape[0] == 1 and x.shape[1] == 1:
            break
        hh, ww = max(1, x.shape[0] // 2), max(1, x.shape[1] // 2)
        x = x[:hh * 2 if x.shape[0] > 1 else 1, :ww * 2 if x.shape[1] > 1 else 1]
        x = x.reshape(hh, x.shape[0] // hh, ww, x.shape[1] // ww, 4).mean(axis=(1, 3))
    flags = 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000          # CAPS HEIGHT WIDTH PITCH PIXELFORMAT MIPMAPCOUNT
    pf = struct.pack('<8I', 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)   # RGB + ALPHAPIXELS
    caps = 0x8 | 0x1000 | 0x400000                               # COMPLEX TEXTURE MIPMAP
    cab = (struct.pack('<7I', 124, flags, h, w, w * 4, 0, len(niveles)) + bytes(44) + pf
           + struct.pack('<5I', caps, 0, 0, 0, 0))
    return b'DDS ' + cab + b''.join(niveles), len(niveles)


_tex_stats = {'reducidas': 0, 'max_lado': 0, 'por_lado': {}}


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
    clave = (img.name, int(size))          # v1.2: el lado depende del material (P2), no solo de la imagen
    if clave in _img_cache:
        return _img_cache[clave]
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
    _img_cache[clave] = res
    return res


# ----------------------------------------------------------------------------- materiales
def _socket(node, identifier):
    for s in node.inputs:
        if s.identifier == identifier:
            return s
    return None


def _cargar_imagen(ruta):
    """bpy.types.Image de un fichero (sRGB), o None si no existe."""
    if not ruta or not os.path.exists(ruta):
        print('AVISO: no existe la imagen', ruta)
        return None
    img = bpy.data.images.load(ruta, check_existing=True)
    img.colorspace_settings.name = 'sRGB'
    return img


def _ac_prop(m, clave, defecto=None):
    """Custom prop ac_* de un material como tipo python (los IDPropertyGroup a dict)."""
    v = m.get(clave, defecto)
    try:
        return v.to_dict()
    except AttributeError:
        return v


def _tex_max_material(m):
    """ac_tex_max del material para txDiffuse (int o dict por sampler) o None."""
    v = _ac_prop(m, 'ac_tex_max')
    if isinstance(v, dict):
        v = v.get('txDiffuse')
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def analizar_material(m):
    """Resume un material de Blender: color base lineal, alpha, imagen de color y su mapping.
    En esta escena el color plano original queda en material.diffuse_color (color de viewport) y la
    cadena de textura es TEX_imagen -> TEX_ganancia(x gain) -> TEX_multiplicar(factor) -> Base Color.
    v1.2: MAT_terreno segun TERRENO_MODO, 'ac_tile' (MAT_terreno_roca y los del reparto por caras) y ac_tex_max."""
    info = _analizar_material_v11(m)
    info['tex_max_ac'] = _tex_max_material(m)
    sh = _ac_prop(m, 'ac_shader')
    info['ac_shader_pedido'] = str(sh) if sh else None
    st = _ac_prop(m, 'ac_samplers') or {}
    info['ac_txdiffuse'] = os.path.basename(str(st.get('txDiffuse'))) if isinstance(st, dict) and st.get('txDiffuse') else None
    tile = _ac_prop(m, 'ac_tile')
    if isinstance(tile, dict) and tile.get('imagen'):
        img = _cargar_imagen(tile['imagen'])
        if img is not None:
            info.update(img=img, scale=float(tile.get('escala', 1.0 / 3.0)), proj=str(tile.get('proj', 'FLAT')),
                        factor=1.0, gain=1.0, ignorar_uv=True, tile_ac=os.path.basename(tile['imagen']))
    if m.name == TERRENO_MAT:
        if TERRENO_MODO in ('base', 'detalle'):
            ruta = os.environ.get('TERRENO_BASE')
            if not ruta and isinstance(st, dict) and st.get('txDiffuse'):
                ruta = str(st['txDiffuse'])
            img = _cargar_imagen(ruta) if ruta else None
            if img is None:                      # la imagen del nodo TERRENO_base del material
                n = m.node_tree.nodes.get('TERRENO_base') if m.node_tree else None
                img = n.image if (n is not None and n.bl_idname == 'ShaderNodeTexImage') else None
            if img is not None:
                info.update(img=img, modo_terreno=TERRENO_MODO, proj='PLANAR_MUNDO', factor=1.0, gain=1.0, scale=1.0,
                            ruta_terreno_base=bpy.path.abspath(img.filepath))
            else:
                print('AVISO: MAT_terreno sin terreno_base.png: se exporta como en v1.1 (tile)')
                info['ignorar_uv'] = True
        else:                                    # 'tile' / 'caras': la UV 0..1 de la mascara NO vale para el tile
            info['ignorar_uv'] = True
            info['modo_terreno'] = TERRENO_MODO
    return info


def _analizar_material_v11(m):
    """analizar_material de v1.1 (sin cambios)."""
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


def lado_textura(info):
    """Lado de la textura tintada del material (v1.2, P2): 1024 para las familias TEX_P2_FAMILIAS y para los materiales
    con ac_tex_max >= 1024; TEX_SIZE (512) el resto, o todos si TEX_P2 = 0."""
    if not TEX_P2:
        return TEX_SIZE
    fam = info.get('familia') or color_ac.familia(info['name'])
    tmax = info.get('tex_max_ac')
    if fam in TEX_P2_FAMILIAS or (tmax is not None and tmax >= TEX_SIZE_P2):
        return TEX_SIZE_P2
    return TEX_SIZE


def media_tierra(lin):
    """Media lineal (3,) de la textura del terreno en tierra firme: celdas de la rejilla con mar = 0 (GEOM) llevadas a
    los texeles (fila 0 = y maximo, como el PNG). Sin GEOM: media de toda la imagen."""
    try:
        if GEOM_JSON and os.path.exists(GEOM_JSON):
            T = json.load(open(GEOM_JSON, encoding='utf-8'))['terreno']
            nx, ny = int(T['nx']), int(T['ny'])
            mar = np.asarray(T['mar'], np.float32).reshape(ny, nx)[::-1] > 0.5
            h, w = lin.shape[:2]
            ri = np.minimum((np.arange(h) * ny / h).astype(int), ny - 1)
            ci = np.minimum((np.arange(w) * nx / w).astype(int), nx - 1)
            tierra = ~mar[ri][:, ci]
            if tierra.sum() > 1000:
                return lin[tierra].mean(axis=0), 'tierra firme (%.0f %% de los texeles, rejilla de GEOM)' % (
                    100.0 * tierra.mean())
    except Exception as e:  # noqa
        print('AVISO: media_tierra sin GEOM (%s)' % e)
    return lin.reshape(-1, 3).mean(axis=0), 'imagen entera (sin GEOM)'


_terreno_info = {}


def textura_terreno_base(info):
    """(nombre, bytes) de la textura del terreno por texel: terreno_base.png a TEX_TERRENO (2048) SIN reducir, con la
    ganancia por canal que lleva su media de tierra firme al color calibrado por color_ac (info['color'], lineal):
    conserva paleta, parches y AO de la mascara. PNG (por defecto) o DDS con mipmaps (TERRENO_DDS=1)."""
    lin = imagen_lineal(info['img'], TEX_TERRENO)
    media = np.asarray(info.get('media_base', lin.reshape(-1, 3).mean(axis=0)), np.float32)
    gain = (np.asarray(info['color'], np.float32) / np.maximum(media, 1e-4)).reshape(1, 1, 3)
    rgb = lin_to_srgb(lin * gain)
    if info.get('modo_terreno') == 'detalle':       # opcion (b): RGBA, alfa = DET_ALFA y el factor medio del detalle
        rgb = np.clip(rgb / factor_medio_detalle(), 0.0, 1.0)   # compensado EN ESPACIO GAMMA (AC multiplica tal cual)
        rgb = np.concatenate([rgb, np.full(rgb.shape[:2] + (1,), DET_ALFA, np.float32)], axis=2)
    img8 = np.ascontiguousarray((rgb * 255.0 + 0.5).astype(np.uint8))
    _tex_stats['max_lado'] = max(_tex_stats['max_lado'], *img8.shape[:2])
    _terreno_info.update({'lado': int(img8.shape[0]), 'ganancia_lineal': [round(float(g), 4) for g in gain.ravel()],
                          'media_srgb8_salida': [int(round(c)) for c in img8[..., :3].reshape(-1, 3).mean(axis=0)],
                          'recortados_255_pct': round(float((img8[..., :3] == 255).mean() * 100), 3),
                          'canales': int(img8.shape[2])})
    if TERRENO_DDS:
        data, n = dds_bytes(img8)
        _terreno_info.update(formato='DDS A8R8G8B8 con %d mipmaps' % n, bytes=len(data))
        return 'terreno_base_%d.dds' % img8.shape[0], data
    data = png_bytes(img8)
    _terreno_info.update(formato='PNG %s sin mipmaps propios' % ('RGBA' if img8.shape[2] == 4 else 'RGB'), bytes=len(data))
    return 'terreno_base_%d.png' % img8.shape[0], data


def construir_textura(info):
    """Devuelve (nombre_png, bytes_png). Imagen tintada 512px o PNG plano 8x8 del color base.
    Antes de codificar, limitar_tamano() garantiza que ningun lado supere TEX_MAX (1024).
    v1.2: lado por material (lado_textura, P2) y textura del terreno por texel (textura_terreno_base)."""
    if info.get('modo_terreno') in ('base', 'detalle') and info['img'] is not None:
        return textura_terreno_base(info)
    color = np.array(info['color'], np.float32).reshape(1, 1, 3)
    alpha = info['alpha']
    lado = lado_textura(info)
    lin = imagen_lineal(info['img'], lado) if info['img'] is not None else None
    if lin is not None:
        _tex_stats['por_lado'][str(lin.shape[0])] = _tex_stats['por_lado'].get(str(lin.shape[0]), 0) + 1
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
    for i in infos:
        # v1.2: el albedo del terreno por texel = media de terreno_base en tierra firme (no el diffuse_color de viewport);
        # color_ac calibra esa media y textura_terreno_base() lleva la imagen a ella con una ganancia por canal
        if i.get('modo_terreno') in ('base', 'detalle') and i['img'] is not None:
            media, fuente = media_tierra(imagen_lineal(i['img'], TEX_TERRENO))
            _terreno_info.update(media_lineal_tierra=[round(float(c), 4) for c in media], media_fuente=fuente,
                                 diffuse_color_viewport=[round(float(c), 4) for c in i['color']])
            i['media_base'] = tuple(float(c) for c in media)
            i['color'] = i['media_base']
        if i.get('ac_shader_pedido') and i['ac_shader_pedido'] not in SHADERS_V12:
            print('AVISO: %s pide ac_shader %s: se ignora en v1.2 (multicapa pendiente de la foto del ensayo A); sale como %s'
                  % (i['name'], i['ac_shader_pedido'],
                     'ksPerPixelMultiMap' if i.get('modo_terreno') == 'detalle' else 'ksPerPixel'))
    if USAR_COLOR_AC:       # color para AC (aspecto medido en Blender + modelos de luz de AC) y props por familia
        infos = color_ac.calibrar_todos(infos)
    return infos


# ----------------------------------------------------------------------------- v1.2 opcion (b): detalle sobre la base
# TERRENO_MODO='detalle': (a) + grano cercano con ksPerPixelMultiMap (shader de Kunos; nombres VERIFICADOS en kn5_refs:
# AcTools.Render MaterialsProviderDark.cs l.83 'ksPerPixelMultiMap'; Kn5MaterialDarkMaps.cs l.26-29 samplers txNormal,
# txMaps, txDetail y l.43/56 props useDetail, detailUVMultiplier; kn5-converter Program.cs l.261-290 useDetail /
# detailUVMultiplier / txDetail leidos de los KN5 de Kunos; slots txDiffuse 0, txNormal 1, txMaps 2, txDetail 3 del
# exportador de referencia material_writer.py l.23-27). Semantica (AcTools DarkMaterial.Unpack.fx Unpack_Maps l.92-106,
# reimplementacion de CM, NO comprobada en AC): color = txDiffuse.rgb * lerp(txDetail.rgb, 1, txDiffuse.a), detalle con
# UV * detailUVMultiplier. Para no depender de esa semantica: alfa del diffuse = 0.5 (lerp(d, 1, 0.5) = lerp(1, d, 0.5): da
# lo mismo si AC lo hiciera al reves) y el diffuse va dividido por la media del factor (si AC ignorase el detalle, el
# terreno saldria un 1/factor_medio_detalle() ~ +14 % mas claro, sin grano: es decir, la opcion (a) algo mas clara). txNormal plano (128,128,255,128: plano tambien si AC
# leyera la normal de los canales A/G) y txMaps negro (sin especular ni reflejo). Detalle = grano de luminancia de
# hierba_seca_d + caliza_d (neutro, sin tono). Riesgo: shader nuevo en el mod (R4) -> ver la decision en el informe.
DET_PERIODO_M = 3.0          # periodo del grano (m), el del tile de hierba seca de v1.1
DET_LADO = 512
DET_AMP = 0.25               # amplitud (desv. tipica) del grano en la textura de detalle (se reduce a la mitad con alfa 0.5)
DET_MEDIA = 0.75             # media de la textura de detalle (la real, tras recortar a 0..1, la mide textura_detalle)
DET_ALFA = 0.5
_detalle = {}


def factor_medio_detalle():
    """Media real de lerp(d, 1, DET_ALFA) con la textura de detalle (~0.875): el diffuse va dividido por ella."""
    textura_detalle()
    return DET_ALFA + (1 - DET_ALFA) * _detalle['media']


def _textura_pequena(rgba, lado=4):
    return png_bytes(np.ascontiguousarray(np.broadcast_to(np.asarray(rgba, np.uint8), (lado, lado, len(rgba)))))


def textura_detalle():
    """Grano neutro (gris) para txDetail: luminancia de hierba_seca_d y caliza_d (texturas/) normalizada a media DET_MEDIA y
    desviacion DET_AMP, DET_LADO px, sin tono (RGB iguales). Alfa 255. Cacheada (bytes y media real en _detalle)."""
    if 'png' in _detalle:
        return _detalle['png']
    capas = []
    for fichero in ('hierba_seca_d.png', 'caliza_d.png'):
        img = _cargar_imagen(os.path.join(BASE, '03_blender', 'texturas', fichero))
        if img is None:
            continue
        lin = imagen_lineal(img, DET_LADO)
        L = lin_to_srgb(lin) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        capas.append((L - L.mean()) / max(float(L.std()), 1e-4))
    g = np.mean(capas, axis=0) if capas else np.zeros((DET_LADO, DET_LADO), np.float32)
    g = g / max(float(g.std()), 1e-4)
    d = np.clip(DET_MEDIA + DET_AMP * g, 0.0, 1.0)
    d8 = (d * 255.0 + 0.5).astype(np.uint8)
    rgba = np.stack([d8, d8, d8, np.full_like(d8, 255)], axis=-1)
    _detalle['media'] = float(d8.mean()) / 255.0
    _terreno_info['detalle'] = {'lado': DET_LADO, 'media': round(_detalle['media'], 3), 'desv': round(float(d.std()), 3),
                                'recortado_pct': round(float(((d <= 0) | (d >= 1)).mean() * 100), 2),
                                'fuentes': ['hierba_seca_d.png', 'caliza_d.png'][:len(capas)]}
    _detalle['png'] = png_bytes(np.ascontiguousarray(rgba))
    return _detalle['png']


def material_terreno_detalle(info, nombre_base):
    """(shader, props extra, [(sampler, slot, nombre, bytes)]) del MAT_terreno en modo 'detalle'."""
    mult = PLANAR['Lx'] / DET_PERIODO_M
    extra = [('isAdditive', 0.0), ('useDetail', 1.0), ('detailUVMultiplier', mult), ('fresnelC', 0.0),
             ('fresnelEXP', 1.0), ('fresnelMaxLevel', 0.0), ('nmObjectSpace', 0.0), ('sunSpecular', 0.0),
             ('sunSpecularEXP', 1.0)]
    tex = [('txNormal', 1, 'terreno_normal_plana.png', _textura_pequena((128, 128, 255, 128))),
           ('txMaps', 2, 'terreno_maps_negro.png', _textura_pequena((0, 0, 0))),
           ('txDetail', 3, 'terreno_detalle_%d.png' % DET_LADO, textura_detalle())]
    _terreno_info['multimap'] = {'detailUVMultiplier': round(mult, 3), 'periodo_m': DET_PERIODO_M, 'alfa_diffuse': DET_ALFA,
                                 'factor_medio': round(factor_medio_detalle(), 4)}
    return 'ksPerPixelMultiMap', extra, tex


def escribir_texturas_y_materiales(w, infos):
    """Escribe la seccion de texturas y la de materiales; anota en cada info su id y textura.
    v1.2: un material puede llevar shader y samplers extra (MAT_terreno en modo 'detalle'); el resto, como v1.1."""
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
        if info.get('modo_terreno') == 'detalle' and info['img'] is not None:
            sh, extra, tex = material_terreno_detalle(info, nombre)
            info['shader_kn5'], info['props_extra'] = sh, extra
            info['samplers_extra'] = [(s, slot, n) for s, slot, n, _ in tex]
            texturas += [(n, b) for _, _, n, b in tex]
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
        w.string(info.get('shader_kn5', 'ksPerPixel'))
        w.u8(1 if info['transparent'] else 0)     # alphaBlendMode: 0 opaco, 1 alpha blend
        w.u8(0)                                   # alphaTested
        w.i32(0)                                  # depthMode: DepthNormal
        props = list(info.get('props_ac', SHADER_PROPS)) + list(info.get('props_extra', ()))   # color_ac.FAMILIAS
        w.i32(len(props))
        for pname, val in props:
            w.string(pname)
            w.f32(val)                            # A
            w.floats((0.0, 0.0))                  # B
            w.floats((val, val, val) if pname == 'ksEmissive' else (0.0, 0.0, 0.0))  # C
            w.floats((0.0, 0.0, 0.0, 0.0))        # D
        samplers = [('txDiffuse', 0, info['tex'])] + list(info.get('samplers_extra', ()))
        w.i32(len(samplers))
        for sname, slot, tname in samplers:
            w.string(sname)
            w.i32(slot)
            w.string(tname)
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


def loops_grupo(A, mask, info, MW=None):
    """Por loop del grupo de triangulos `mask`: posicion y normal LOCALES en ejes Blender y UV con la
    v ya invertida. Las UV generadas (material con imagen sin uv_layer) se calculan en locales, igual
    que kn5_writer.py, ANTES de cualquier paso a coordenadas mundo.
    v1.2: proj 'PLANAR_MUNDO' (terreno por texel) = UV planar de MUNDO de la rejilla del terreno (PLANAR) con la matriz
    MW del objeto; info['ignorar_uv'] (tiles del terreno) = UV generada aunque la malla tenga uv_layers (P10 interino)."""
    loops = A['tl'][mask].reshape(-1)
    P = A['co'][A['lv'][loops]]
    N = A['nr'][loops]
    if info.get('proj') == 'PLANAR_MUNDO':
        if MW is not None:
            M = np.array(MW, np.float64).reshape(4, 4)
            Pw = P.astype(np.float64) @ M[:3, :3].T + M[:3, 3]
        else:
            Pw = P.astype(np.float64)
        UV = np.stack([(Pw[:, 0] - PLANAR['x0']) / PLANAR['Lx'], (Pw[:, 1] - PLANAR['y0']) / PLANAR['Ly']],
                      axis=1).astype(np.float32)
    elif A['uv'] is not None and not info.get('ignorar_uv'):
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


def piezas_objeto(me, infos_por_nombre, default_info, MW=None):
    """Objeto suelto (dummy propio con matriz): lista de (verts, idx, info) en coordenadas LOCALES,
    separadas por material, soldadas y partidas. MW (v1.2): solo para la UV planar de mundo del terreno."""
    A = arrays_malla(me)
    if A is None:
        return []
    piezas = []
    for mi in np.unique(A['tmat']):
        info = info_material(me, mi, infos_por_nombre, default_info)
        P, N, UV = loops_grupo(A, A['tmat'] == mi, info, MW)
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
        P, N, UV = loops_grupo(A, A['tmat'] == mi, info, MW)
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
    piezas = piezas_objeto(me, por_nombre, default_info, ob.matrix_world)
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


# ----------------------------------------------------------------------------- v1.2: terreno
def params_planar(objs):
    """x0, y0, Lx, Ly de la UV planar del terreno: la rejilla de GEOM ('terreno': x0, y0, nx*cell, ny*cell, el contrato de
    mascara_terreno / construir_pista) y, como comprobacion (o si no hay GEOM), el ajuste lineal u = (x - x0)/Lx a la
    uv_layers[0] del TERRENO. Devuelve el dict (y lo deja en PLANAR) con la fuente y el error del ajuste en metros."""
    out = {}
    if GEOM_JSON and os.path.exists(GEOM_JSON):
        T = json.load(open(GEOM_JSON, encoding='utf-8'))['terreno']
        out = {'x0': float(T['x0']), 'y0': float(T['y0']), 'Lx': float(T['nx']) * float(T['cell']),
               'Ly': float(T['ny']) * float(T['cell']), 'fuente': 'GEOM %s' % os.path.basename(GEOM_JSON)}
    ter = next((o for o in objs if o.name in ('1GRASS_terreno', 'TERRENO') and o.data.uv_layers), None)
    if ter is not None:
        me = ter.data
        n = len(me.loops)
        uv = np.empty(n * 2, np.float32)
        me.uv_layers[0].data.foreach_get('uv', uv)
        lv = np.empty(n, np.int32)
        me.loops.foreach_get('vertex_index', lv)
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        M = np.array(ter.matrix_world, np.float64)
        P = co.reshape(-1, 3)[lv].astype(np.float64) @ M[:3, :3].T + M[:3, 3]
        uv = uv.reshape(-1, 2).astype(np.float64)
        sel = slice(None, None, max(1, n // 200000))
        ax, bx = np.polyfit(P[sel, 0], uv[sel, 0], 1)
        ay, by = np.polyfit(P[sel, 1], uv[sel, 1], 1)
        ajuste = {'x0': -bx / ax, 'y0': -by / ay, 'Lx': 1.0 / ax, 'Ly': 1.0 / ay}
        if not out:
            out = dict(ajuste, fuente='ajuste a la UV de %s' % ter.name)
        u = (P[:, 0] - out['x0']) / out['Lx']
        v = (P[:, 1] - out['y0']) / out['Ly']
        out['error_uv_m'] = round(float(max(np.abs(u - uv[:, 0]).max() * out['Lx'], np.abs(v - uv[:, 1]).max() * out['Ly'])), 3)
        out['ajuste_uv'] = {k: round(float(v_), 3) for k, v_ in ajuste.items()}
    if not out:
        raise RuntimeError('TERRENO_MODO=base sin GEOM ni TERRENO con UV: no se puede calcular la UV planar')
    PLANAR.update(out)
    return out


def repartir_terreno_caras(objs):
    """Opcion (c) de la tarea v1.2 (P10 via A), SOLO para comparar con kn5_vista: cada cara con MAT_terreno toma el canal
    dominante de terreno_mask.png en su centro (UV planar de mundo): R matorral (matorral_d a 6 m), G hierba seca (MAT_terreno,
    hierba_seca_d a 3 m), B tierra (tierra_d a 6 m), A roca (MAT_terreno_roca, caliza_d a 3 m BOX). Color = paleta x AO media
    (como terreno_base). Bordes por cara (2 m en la banda, 4 m en el resto). No guarda el .blend. Devuelve {material: caras}."""
    sys.path.insert(0, os.path.join(BASE, '03_blender'))
    import paleta
    base = bpy.data.materials.get(TERRENO_MAT)
    ruta_m = os.environ.get('TERRENO_MASK') or os.path.join(BASE, '03_blender', 'texturas', 'terreno_mask.png')
    ruta_ao = os.path.join(os.path.dirname(ruta_m), 'terreno_ao.png')
    img = bpy.data.images.load(ruta_m, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w_, h_ = img.size
    buf = np.empty(w_ * h_ * 4, np.float32)
    img.pixels.foreach_get(buf)
    mask = buf.reshape(h_, w_, 4)                       # fila 0 = abajo (y minimo), como la UV de Blender
    ao_m = 0.757
    if os.path.exists(ruta_ao):
        ia = bpy.data.images.load(ruta_ao, check_existing=False)
        ia.colorspace_settings.name = 'Non-Color'
        b2 = np.empty(ia.size[0] * ia.size[1] * 4, np.float32)
        ia.pixels.foreach_get(b2)
        ao_m = float(b2.reshape(-1, 4)[:, 0].mean())
    tex = os.path.join(BASE, '03_blender', 'texturas')
    defs = {0: ('MAT_terreno_c_matorral', 'oliva_oscuro', 'matorral_d.png', 1 / 6.0, 'FLAT'),
            2: ('MAT_terreno_c_tierra', 'tierra', 'tierra_d.png', 1 / 6.0, 'FLAT'),
            3: (color_ac.ROCA_MAT, 'caliza_ocre', 'caliza_d.png', 1 / 3.0, 'BOX')}
    mats = {}
    for k, (nombre, col, fichero, esc, proj) in defs.items():
        m = bpy.data.materials.get(nombre) or base.copy()
        m.name = nombre
        for key in [key for key in m.keys() if key.startswith('ac_')]:
            del m[key]
        c = np.asarray(paleta.rgb(col), np.float64) * ao_m
        m.diffuse_color = (c[0], c[1], c[2], 1.0)
        m['ac_tile'] = {'imagen': os.path.join(tex, fichero), 'escala': esc, 'proj': proj}
        mats[k] = m
    cG = np.asarray(paleta.rgb('hierba_seca'), np.float64) * ao_m
    base.diffuse_color = (cG[0], cG[1], cG[2], 1.0)
    cuenta = {TERRENO_MAT: 0}
    for ob in objs:
        me = ob.data
        if not any(m is not None and m.name == TERRENO_MAT for m in me.materials) or me.library is not None:
            continue
        n = len(me.polygons)
        pm = np.empty(n, np.int32)
        me.polygons.foreach_get('material_index', pm)
        kb = [i for i, m in enumerate(me.materials) if m is not None and m.name == TERRENO_MAT]
        sel = np.isin(pm, kb)
        cen = np.empty(n * 3, np.float32)
        me.polygons.foreach_get('center', cen)
        M = np.array(ob.matrix_world, np.float64)
        Pw = cen.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
        u = np.clip((Pw[:, 0] - PLANAR['x0']) / PLANAR['Lx'], 0, 1 - 1e-6)
        v = np.clip((Pw[:, 1] - PLANAR['y0']) / PLANAR['Ly'], 0, 1 - 1e-6)
        dom = mask[(v * h_).astype(int), (u * w_).astype(int)].argmax(axis=1)
        for k, m in mats.items():
            if not any(x is not None and x.name == m.name for x in me.materials):
                me.materials.append(m)
            idx = next(i for i, x in enumerate(me.materials) if x is not None and x.name == m.name)
            caras = sel & (dom == k)
            pm[caras] = idx
            cuenta[m.name] = cuenta.get(m.name, 0) + int(caras.sum())
        cuenta[TERRENO_MAT] += int((sel & (dom == 1)).sum())
        me.polygons.foreach_set('material_index', pm)
        me.update()
    return cuenta


def comprobar_p3(infos):
    """P3 sin cambiar nada: materiales cuya ac_samplers['txDiffuse'] no es la imagen que elige analizar_material."""
    out = []
    for i in infos:
        pedida = i.get('ac_txdiffuse')
        if not pedida or i.get('modo_terreno') or i.get('tile_ac'):
            continue
        elegida = os.path.basename(bpy.path.abspath(i['img'].filepath)) if i.get('img') is not None else None
        if elegida != pedida:
            out.append({'material': i['name'], 'ac_samplers_txDiffuse': pedida, 'writer': elegida})
    return out


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
    objs = objetos_exportables()
    # v1.2: UV planar del terreno (rejilla de GEOM, comprobada contra la UV del TERRENO)
    planar = params_planar(objs) if TERRENO_MODO in ('base', 'detalle', 'caras') else None
    print('terreno: modo %s%s; UV planar %s' % (TERRENO_MODO, ' (DDS con mipmaps)' if TERRENO_DDS else '', planar))
    # color_ac: las caras de roca de MAT_terreno (mismo criterio que el nodo de Blender) pasan a MAT_terreno_roca,
    # solo en memoria (el .blend no se guarda). v1.2 'base': solo paredes casi verticales que no son suelo (caliza P1);
    # 'caras': reparto por caras de la opcion (c) (repartir_terreno_caras, incluye la roca)
    if TERRENO_MODO == 'caras':
        roca_ac = repartir_terreno_caras(objs)
        print('terreno por caras (opcion c): %s' % roca_ac)
    else:
        roca_ac = (color_ac.separar_roca_terreno(modo='base' if TERRENO_MODO in ('base', 'detalle') else 'tile')
                   if USAR_COLOR_AC else {})
        print('color_ac: %d caras de roca -> %s %s' % (sum(roca_ac.values()), color_ac.ROCA_MAT, roca_ac))
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
        'v12': {
            'terreno_modo': TERRENO_MODO, 'terreno_dds': TERRENO_DDS, 'uv_planar': planar,
            'terreno_textura': dict(_terreno_info),
            'terreno_info_material': {k: (list(v) if isinstance(v, tuple) else v) for k, v in
                                      (next((i for i in infos if i['name'] == TERRENO_MAT), {}) or {}).items()
                                      if k in ('modo_terreno', 'proj', 'familia', 'tx_ac', 'albedo_fuente',
                                               'ruta_terreno_base', 'media_base')},
            'tex_p2': TEX_P2, 'texturas_por_lado': dict(_tex_stats['por_lado']),
            'deco_sin_sombra': list(DECO_SIN_SOMBRA),
            'ac_shader_ignorados': sorted({i['name']: i['ac_shader_pedido'] for i in infos
                                           if i.get('ac_shader_pedido') and i['ac_shader_pedido'] not in SHADERS_V12}.items()),
            'p3_txdiffuse_distinta': comprobar_p3(infos),
            'materiales_tile_ac': {i['name']: i['tile_ac'] for i in infos if i.get('tile_ac')},
        },
    }
    json.dump(resumen, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    r2 = dict(resumen)
    r2['nodos_AC'] = '%d nodos (ver json)' % len(E.ac_nodes)
    print('RESUMEN:', json.dumps(r2, indent=1, ensure_ascii=False))
    print('OK KN5 -> %s (%.1f MB)' % (OUT_KN5, size_mb))


if __name__ == '__main__':      # Blender --python ejecuta el script como __main__; ensayo_f_pueblo.py lo importa
    main()
