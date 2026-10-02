# -*- coding: utf-8 -*-
"""kn5_writer.py - exporta porto_corsa_export.blend a KN5 v5 (Assetto Corsa) SIN ksEditor.

Formato y convenciones tomados de codigo abierto (copias de solo lectura en 04_export/kn5_refs/):
  - blender-assetto-corsa-tools (jwl-7): exporter/kn5_writer.py, node_writer.py, material_writer.py,
    texture_writer.py, exporter_utils.py (convert_vector3 / convert_matrix / write_matrix).
  - kn5-converter (RaduMC) "kn5 converter/Program.cs" (lector independiente, C#).
  - AcTools (gro-ove/actools) Kn5Basic.cs / Kn5Writer.cs (lector+escritor de Content Manager).
Convenciones confirmadas en las tres fuentes:
  * Cabecera: los 6 bytes b'sc6969' + int32 version=5 (NO es 'sNk5').
  * Ejes: (x, y, z)_blender -> (x, z, -y)_kn5 (Y arriba, Z = -Y de Blender).
  * Winding: se conserva el orden de los loops de Blender (el addon escribe (i1, i2, i0), una
    rotacion ciclica = mismo sentido; los lectores C# vuelcan los indices tal cual a OBJ/FBX).
  * UV: (u, 1 - v)  (el addon escribe -v; kn5-converter lee v_obj = 1 - v_kn5: equivalentes).
  * Matriz del dummy: 16 floats en orden m[col][row] (fila exterior, columna interior) de la matriz
    de Blender ya convertida => traslacion en los floats 12, 13, 14 (convencion fila-vector DirectX,
    kn5-converter: translation = tmatrix[3,0..2]).
  * Material: string nombre, string shader, uint8 alphaBlendMode, uint8 alphaTested, int32 depthMode,
    int32 n_props {string, float A, vec2 B, vec3 C, vec4 D}, int32 n_samplers {string, int32 slot, string}.
  * Malla: int32 2, string, int32 0 hijos, uint8 activo, uint8 castShadows, uint8 visible,
    uint8 transparent, int32 nverts, nverts*(pos3 nrm3 uv2 tan3), int32 nidx, uint16*nidx,
    int32 materialId, int32 layer, float lodIn, float lodOut, vec3 centro, float radio, uint8 renderable.
Ejecutar:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup
      --python E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/kn5_writer.py
"""
import hashlib
import json
import math
import os
import shutil
import struct
import time
import zlib

import bpy
import numpy as np
from mathutils import Matrix, Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
BLEND = BASE + r'\04_export\porto_corsa_export.blend'
OUT_PKG = BASE + r'\04_export\paquete\content\tracks\porto_corsa\porto_corsa.kn5'
OUT_COPY = BASE + r'\04_export\kn5\porto_corsa.kn5'
OUT_JSON = BASE + r'\04_export\kn5\resumen_writer.json'
ROOT_NAME = 'porto_corsa'
TEX_SIZE = 512            # lado de las texturas tintadas embebidas (las fuentes son de 1024)
MAX_VERTS = 65000         # limite por malla (indices uint16)
GROUND_PREFIXES = ('1ROAD', '1DIRT', '1KERB', '1GRASS', '2GRASS', '1PIT', 'AGUA', 'MARCA', 'linea')
AC_LOGICAL = ('AC_START_', 'AC_PIT_', 'AC_TIME_', 'AC_HOTLAP_START_', 'AC_AUDIO_', 'AC_CREW_', 'AC_OPEN_')
DEFAULT_MAT = 'MAT_default'
# Orientacion de los objetos logicos. Regla de AC (tutorial "Build your FIRST track", assettocorsamods.net;
# en aero.ini de los coches el aleron trasero tiene Z negativa): el eje +Z LOCAL del dummy (en coordenadas
# AC, Y arriba) es hacia donde mira el coche.
#  * Escenas de export v1 (exportar_ac.py antiguo, sin scene['porto_corsa_export_v']): las mini-mallas se
#    giraron heading - pi/2, dejando su +Y local (= -Z en AC) en el sentido de la marcha, es decir,
#    miraban HACIA ATRAS, y los AC_PIT miraban al fondo del garaje (comprobado con geometria_3d.json:
#    dot(+Z, hacia pit lane) = -0.99; AC_START/HOTLAP dot(+Z, marcha) = -1.00): se giran 180 grados.
#  * Escenas v2 (exportar_ac.py actual: heading + pi/2, plazas + pi, 1 m sobre el suelo): ya vienen
#    bien orientadas y aqui NO se gira nada (main() anula el giro al leer la marca de version).
AC_GIRAR_180_V1 = {'AC_START_': True, 'AC_HOTLAP_START_': True, 'AC_PIT_': True}
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
    """Devuelve (nombre_png, bytes_png). Imagen tintada 512px o PNG plano 8x8 del color base."""
    color = np.array(info['color'], np.float32).reshape(1, 1, 3)
    alpha = info['alpha']
    lin = imagen_lineal(info['img'], TEX_SIZE) if info['img'] is not None else None
    if lin is None:
        rgb = np.broadcast_to(lin_to_srgb(color), (8, 8, 3))
        nombre = 'flat_%s.png' % info['name']
    else:
        f = info['factor']
        # Ganancia = 1/media LINEAL medida de la imagen, de modo que la media lineal de la textura
        # tintada sea exactamente el color base del material (la "ganancia" del nodo TEX_ganancia se
        # calculo en aplicar_texturas.py sobre la media sRGB, no lineal, y oscurecia ~2.6x).
        # Ganancia POR CANAL: la imagen aporta solo el patron/luminancia y el material fija el tono
        # (con hierba_d.png verde sobre MAT_terreno verde una ganancia escalar sobresaturaba).
        gain = (1.0 / np.maximum(lin.mean(axis=(0, 1)), 1e-4)).astype(np.float32).reshape(1, 1, 3)
        rgb = lin_to_srgb(color * (1.0 - f + f * lin * gain))
        nombre = 'tex_%s.png' % info['name']
    img8 = (rgb * 255.0 + 0.5).astype(np.uint8)
    if alpha < 0.999:
        a8 = np.full(img8.shape[:2] + (1,), int(round(alpha * 255)), np.uint8)
        img8 = np.concatenate([img8, a8], axis=2)
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
        w.i32(len(SHADER_PROPS))
        for pname, val in SHADER_PROPS:
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


def construir_grupo(A, mask, info):
    """Vertices (N, 11) = pos3 nrm3 uv2 tan3 en ejes KN5 y coordenadas LOCALES del objeto, mas
    indices por loop (3 por triangulo, orden de Blender conservado)."""
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
    P = P[:, AX_SWAP] * AX_SIGN                     # (x, y, z) -> (x, z, -y)
    N = N[:, AX_SWAP] * AX_SIGN
    key = np.ascontiguousarray(np.concatenate([P, N, UV], axis=1).astype(np.float32))
    kv = key.view(np.dtype((np.void, key.dtype.itemsize * key.shape[1]))).ravel()
    _, first, inv = np.unique(kv, return_index=True, return_inverse=True)
    V = key[first]
    # tangente: perpendicular a la normal dentro del plano horizontal AC (Y arriba); (1,0,0) si degenera
    Nn = V[:, 3:6]
    T = np.cross(Nn, np.array([0.0, 1.0, 0.0], np.float32)).astype(np.float32)
    ln = np.linalg.norm(T, axis=1)
    malo = ln < 1e-4
    T[malo] = (1.0, 0.0, 0.0)
    ln[malo] = 1.0
    T /= ln[:, None]
    verts = np.concatenate([V, T], axis=1).astype(np.float32)
    return verts, np.asarray(inv).ravel().astype(np.int64)


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


def piezas_objeto(me, infos_por_nombre, default_info):
    """Lista de (verts, idx, info_material) de un objeto, separadas por material y partidas."""
    A = arrays_malla(me)
    if A is None:
        return []
    piezas = []
    for mi in np.unique(A['tmat']):
        mat = me.materials[mi] if mi < len(me.materials) else None
        info = infos_por_nombre.get(mat.name) if mat is not None else None
        if info is None:
            info = default_info
        verts, inv = construir_grupo(A, A['tmat'] == mi, info)
        for v, ix in partir(verts, inv):
            piezas.append((v, ix, info))
    return piezas


def escribir_malla(w, name, verts, idx, info, cast_shadows):
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
    w.u8(1)                       # renderable


# ----------------------------------------------------------------------------- principal

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


def main():
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    print('blend abierto en %.1fs' % (time.time() - t0))
    export_v = int(bpy.context.scene.get('porto_corsa_export_v', 1))
    girar = tuple(p for p, g in AC_GIRAR_180_V1.items() if g) if export_v < 2 else ()
    print('escena de export v%d: giro de 180 grados de AC_* %s' % (
        export_v, 'APLICADO (escena antigua)' if girar else 'NO necesario (ya orientados en exportar_ac.py)'))
    os.makedirs(os.path.dirname(OUT_PKG), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_COPY), exist_ok=True)
    objs = objetos_exportables()
    infos = recopilar_materiales(objs)
    por_nombre = {i['name']: i for i in infos}
    default_info = por_nombre[DEFAULT_MAT]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    stats = {'n_dummies': 1, 'n_mallas': 0, 'n_verts': 0, 'n_tris': 0, 'n_ac': 0,
             'objetos_sin_geometria': 0, 'objetos_partidos': 0}
    bb_min = np.array([np.inf] * 3)
    bb_max = np.array([-np.inf] * 3)
    ac_nodes = {}
    with open(OUT_PKG, 'wb', buffering=1 << 22) as f:
        w = Writer(f)
        f.write(b'sc6969')
        w.i32(5)
        texturas = escribir_texturas_y_materiales(w, infos)
        print('texturas: %d (%.1f MB), materiales: %d, objetos: %d  [%.1fs]' % (
            len(texturas), sum(len(d) for _, d in texturas) / 1e6, len(infos), len(objs), time.time() - t0))
        # raiz: dummy identidad con un dummy hijo por objeto
        w.i32(1)
        w.string(ROOT_NAME)
        w.i32(len(objs))
        w.u8(1)
        w.matrix(Matrix.Identity(4))
        for k, ob in enumerate(objs):
            MW = ob.matrix_world
            if girar and ob.name.startswith(girar):
                MW = MW @ ROT_Z_180        # giro de 180 grados sobre el eje local vertical (solo escenas v1)
            M = C_AXIS @ MW @ C_AXIS_INV
            if ob.name.startswith(AC_LOGICAL):
                # objeto logico: solo el dummy con su matriz (AC lee posicion/orientacion de aqui)
                w.i32(1)
                w.string(ob.name)
                w.i32(0)
                w.u8(1)
                w.matrix(M)
                stats['n_dummies'] += 1
                stats['n_ac'] += 1
                # eje +Z local del dummy en mundo AC (hacia donde mira el coche) = columna 2 de M
                ac_nodes[ob.name] = {'pos_kn5': [round(v, 3) for v in M.translation],
                                     'rot_z_blender_deg': round(math.degrees(ob.rotation_euler.z), 2),
                                     'eje_z_kn5': [round(M[0][2], 3), round(M[1][2], 3), round(M[2][2], 3)]}
                continue
            me, ev = obtener_malla(ob, depsgraph)
            piezas = piezas_objeto(me, por_nombre, default_info)
            w.i32(1)
            w.string(ob.name)
            w.i32(len(piezas))
            w.u8(1)
            w.matrix(M)
            stats['n_dummies'] += 1
            cast = not ob.name.startswith(GROUND_PREFIXES)
            for j, (verts, idx, info) in enumerate(piezas):
                name = ob.name if len(piezas) == 1 else '%s_p%d' % (ob.name, j + 1)
                escribir_malla(w, name, verts, idx, info, cast)
                stats['n_mallas'] += 1
                stats['n_verts'] += len(verts)
                stats['n_tris'] += len(idx) // 3
            if len(piezas) > 1:
                stats['objetos_partidos'] += 1
            if piezas:
                for corner in ob.bound_box:
                    wc = ob.matrix_world @ Vector(corner)
                    p = np.array((wc.x, wc.z, -wc.y))
                    bb_min = np.minimum(bb_min, p)
                    bb_max = np.maximum(bb_max, p)
            else:
                stats['objetos_sin_geometria'] += 1
            if ev is not None:
                ev.to_mesh_clear()
            if k % 500 == 0:
                print('  %d/%d objetos, %d mallas, %d verts [%.0fs]' % (
                    k, len(objs), stats['n_mallas'], stats['n_verts'], time.time() - t0))
    size_mb = os.path.getsize(OUT_PKG) / 1e6
    shutil.copyfile(OUT_PKG, OUT_COPY)
    resumen = {
        'kn5': OUT_PKG, 'copia': OUT_COPY, 'tamano_MB': round(size_mb, 1),
        'n_texturas': len(texturas), 'texturas_MB': round(sum(len(d) for _, d in texturas) / 1e6, 1),
        'n_materiales': len(infos),
        'materiales_transparentes': [i['name'] for i in infos if i['transparent']],
        'materiales_con_imagen': sum(1 for i in infos if i['img'] is not None),
        'n_nodos_dummy': stats['n_dummies'], 'n_mallas': stats['n_mallas'],
        'n_vertices': stats['n_verts'], 'n_triangulos': stats['n_tris'],
        'objetos_partidos': stats['objetos_partidos'], 'objetos_sin_geometria': stats['objetos_sin_geometria'],
        'n_nodos_AC': stats['n_ac'], 'nodos_AC': ac_nodes,
        'escena_export_v': export_v, 'giro_180_aplicado_a': list(girar),
        'bbox_kn5_min': [round(float(v), 2) for v in bb_min], 'bbox_kn5_max': [round(float(v), 2) for v in bb_max],
        'convenciones': {'cabecera': 'sc6969 + int32 5', 'ejes': '(x,y,z)_blender -> (x,z,-y)_kn5',
                         'winding': 'orden de loops de Blender conservado', 'uv': '(u, 1-v)',
                         'matriz': 'm[col][row] por filas (traslacion en floats 12..14)',
                         'nodos': 'raiz identidad > dummy por objeto (matriz mundo) > malla(s) en locales',
                         'orientacion_AC': '+Z local del dummy = frente del coche (ya orientado en exportar_ac.py v2)',
                         'fisica': 'prefijos 1ROAD_/1KERB_/1GRASS_/2GRASS_/1WALL_/1DIRT_/1PIT_ (PIT: IS_PITLANE=1)',
                         'tex_size': TEX_SIZE, 'max_verts': MAX_VERTS},
        'segundos': round(time.time() - t0, 1),
    }
    json.dump(resumen, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    r2 = dict(resumen)
    r2['nodos_AC'] = '%d nodos (ver json)' % len(ac_nodes)
    print('RESUMEN:', json.dumps(r2, indent=1, ensure_ascii=False))
    print('OK KN5 -> %s (%.1f MB)' % (OUT_PKG, size_mb))


main()
