# -*- coding: utf-8 -*-
"""kn5_vista.py - "como lo veria AC sin CSP", leido DEL PROPIO KN5 (la prueba de verdad del writer).

    bash 03_blender/_rev/blender_cola.sh --python 04_export/kn5_vista.py -- --kn5 <fichero.kn5> --out <carpeta> \
        [--camaras 03_blender/renders/ab/_base_antes/camaras.json] [--solo 01,49,50] [--res 1600x900] [--muestras 16] \
        [--comparar 03_blender/renders/ab/f1_r4/despues_ac] [--guardar-blend <escena.blend>] [--sin-sombras]

Lee el KN5 con el MISMO formato que 04_export/kn5_check.py (sc6969 + v5; texturas; materiales {nombre, shader, blend,
alphaTested, depth, props A/B/C/D, samplers}; arbol de nodos dummy (matriz 16f) / malla (pos3 nrm3 uv2 tan3 + indices u16,
materialId, castShadows, isVisible, isTransparent, isRenderable)); a diferencia de _fisica_rev2/rev2_kn5_a_blend.py (solo
geometria) conserva UV, normales, texturas embebidas, props de shader y flags. Monta una escena de Blender que imita a AC
SIN CSP con el MISMO modelo de luz que usa 04_export/color_ac.py para calibrar (escena_ac + pantalla_ac):
  * cada material = EMISION exacta del sombreado gamma de ksPerPixel (DarkMaterial.Lighting.Simple.fx de AcTools):
        tx * (ksAmbient * AMB + ksDiffuse * SOL * N.L * sombra + ksEmissive) + ksSpecular * N.H^EXP * SOL * N.L * sombra
    con tx = textura del KN5 TAL CUAL (valores sRGB 0..1 sin linealizar: AC sombrea en espacio gamma), SOL y AMB de
    3_clear (color_ac.SOL_AC / AMB_AC), N.L * sombra medido con un Shader to RGB de un difuso blanco bajo un sol de EEVEE
    (es lo unico que pone EEVEE: sin mundo, sin GI, sin AO, sin reflejos) y la niebla de Kunos (color_ac.NIEBLA_AC);
  * sombras SOLO de las mallas con castShadows = 1 (visible_shadow = castShadows); isRenderable = 0 / isVisible = 0 no se
    crean; caras de espaldas recortadas (AC no las dibuja); alpha blend del KN5 -> BLENDED;
  * la imagen HDR (EXR) se pasa a pantalla con la exposicion fija 0.2, la saturacion 0.95 y la curva Yebis + gamma 1.2
    de ppfilters/default.ini (color_ac.pantalla_ac); el cielo es el degradado CIELO/HORIZONTE de 3_clear con la misma curva.
Camaras: loc/tgt/lens de Blender (camaras.json de capturas_ab); el KN5 se devuelve a ejes Blender: (x, y, z)_b =
(x, -z, y)_kn5 (inversa del (x, z, -y) del writer) y la UV (u, 1 - v). Sol: mascara_terreno.SOL (el de las capturas).
Salidas en --out: <toma>.png (vista AC), <toma>_par.png (si --comparar: izquierda la captura del proxy, derecha la vista
del KN5), vista.log y vista.json (cifras por toma: media de color, % cielo, materiales y mallas cargadas).
Tomas por defecto: 01, 49-54, 56, 59 (las de la tarea v1.2).
"""
import json
import math
import os
import struct
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import color_ac  # noqa: E402

TOMAS_DEF = ['01_aerea_general', '49_piloto_s300', '50_piloto_s800', '51_piloto_s1700', '52_piloto_s2900',
             '53_piloto_s3400', '54_piloto_s4150', '56_postal_cima_bahia', '59_postal_recta_puerto']
CAMARAS_DEF = os.path.join(BASE, '03_blender', 'renders', 'ab', '_base_antes', 'camaras.json')
SOL_DEF = {'elev_deg': 48.0, 'azimut_deg': 151.0, 'rot_blender_deg': (42.0, 0.0, -119.0)}   # mascara_terreno.SOL


# ============================================================================= lector KN5 (sin bpy)
class _R:
    def __init__(self, data):
        self.d, self.p = data, 0

    def raw(self, n):
        b = self.d[self.p:self.p + n]
        if len(b) != n:
            raise ValueError('KN5 truncado en %d' % self.p)
        self.p += n
        return b

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]
        self.p += 4
        return v

    def string(self):
        n = self.i32()
        return self.raw(n).decode('utf-8', errors='replace')


def leer_kn5(ruta):
    """{'texturas': {nombre: bytes}, 'materiales': [ {nombre, shader, blend, alpha_tested, props{n: A}, samplers{n: tex}} ],
    'mallas': [ {nombre, ruta, V (n,11) f32 en LOCALES, I (m,) u16, mundo 4x4, mat, cast, visible, transparente,
    renderable} ], 'dummies': n}. Mismo orden de campos que kn5_check.leer_nodo."""
    data = open(ruta, 'rb').read()
    r = _R(data)
    if r.raw(6) != b'sc6969':
        raise ValueError('no es un KN5 (magia)')
    ver = r.i32()
    if ver > 5:
        r.i32()
    tex = {}
    for _ in range(r.i32()):
        r.i32()
        n = r.string()
        tam = r.i32()
        tex[n] = r.raw(tam)
    mats = []
    for _ in range(r.i32()):
        m = {'nombre': r.string(), 'shader': r.string(), 'blend': r.u8(), 'alpha_tested': r.u8()}
        m['depth'] = r.i32() if ver > 4 else 0
        props = {}
        for _ in range(r.i32()):
            pn = r.string()
            props[pn] = r.f32()
            r.raw(36)
        m['props'] = props
        sam = {}
        for _ in range(r.i32()):
            sn = r.string()
            r.i32()
            sam[sn] = r.string()
        m['samplers'] = sam
        mats.append(m)
    mallas = []
    cuenta = {'dummies': 0}

    def nodo(padre, ruta_p):
        tipo = r.i32()
        nombre = r.string()
        nh = r.i32()
        r.u8()
        ruta_n = (ruta_p + '/' if ruta_p else '') + nombre
        mundo = padre
        if tipo == 1:
            f = np.frombuffer(r.raw(64), dtype='<f4').astype(np.float64)
            mundo = padre @ f.reshape(4, 4).T          # = kn5_check.matriz_desde_floats
            cuenta['dummies'] += 1
        elif tipo in (2, 3):
            cast, vis, transp = r.u8(), r.u8(), r.u8()
            if tipo == 3:
                for _ in range(r.i32()):
                    r.string()
                    r.raw(64)
            nv = r.i32()
            ancho = 19 if tipo == 3 else 11
            V = np.frombuffer(r.raw(nv * ancho * 4), dtype='<f4').reshape(nv, ancho)[:, :11]
            ni = r.i32()
            I = np.frombuffer(r.raw(ni * 2), dtype='<u2')
            mid = r.i32()
            r.i32()
            r.f32()
            r.f32()
            rend = 1
            if tipo == 2:
                r.raw(16)
                rend = r.u8()
            mallas.append({'nombre': nombre, 'ruta': ruta_n, 'V': V, 'I': I, 'mundo': mundo, 'mat': mid, 'cast': cast,
                           'visible': vis, 'transparente': transp, 'renderable': rend})
        else:
            raise ValueError('tipo de nodo %d desconocido (%s)' % (tipo, nombre))
        for _ in range(nh):
            nodo(mundo, ruta_n)

    nodo(np.eye(4), '')
    if r.p != len(data):
        print('AVISO kn5_vista: sobran %d bytes tras la raiz' % (len(data) - r.p))
    return {'texturas': tex, 'materiales': mats, 'mallas': mallas, 'dummies': cuenta['dummies'], 'bytes': len(data)}


def decodificar_dds(blob):
    """(H, W, 4) float 0..1 del nivel 0 de un DDS A8R8G8B8 sin comprimir (el que escribe el writer v1.2), o None."""
    if blob[:4] != b'DDS ':
        return None
    h, w = struct.unpack_from('<2I', blob, 12)
    pf_flags, fourcc, bits = struct.unpack_from('<3I', blob, 80)
    if fourcc != 0 or bits != 32:
        return None
    n = h * w * 4
    a = np.frombuffer(blob[128:128 + n], np.uint8).reshape(h, w, 4)[..., [2, 1, 0, 3]]
    return a.astype(np.float32) / 255.0


# ============================================================================= escena de Blender
def _vec_math(nt, op, a=None, b=None, loc=(0, 0)):
    n = nt.nodes.new('ShaderNodeVectorMath')
    n.operation = op
    n.location = loc
    for k, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            n.inputs[k].default_value = v
        else:
            nt.links.new(v, n.inputs[k])
    return n


def material_ac(bpy, m, img, sol_dir, cfg):
    """Material de Blender = emision del sombreado gamma de ksPerPixel (ver docstring)."""
    p = m['props']
    ka, kd = p.get('ksAmbient', 0.45), p.get('ksDiffuse', 0.55)
    ks, kexp, kem = p.get('ksSpecular', 0.0), max(p.get('ksSpecularEXP', 1.0), 1.0), p.get('ksEmissive', 0.0)
    mat = bpy.data.materials.new(m['nombre'])
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (1600, 0)
    # tx (valores del fichero tal cual: imagen Non-Color) y alfa
    if img is not None:
        uvn = nt.nodes.new('ShaderNodeUVMap')
        uvn.location = (-900, 200)
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.location = (-700, 200)
        tn.image = img
        tn.interpolation = 'Linear'
        tn.extension = 'REPEAT'
        nt.links.new(uvn.outputs['UV'], tn.inputs['Vector'])
        tx, alfa = tn.outputs['Color'], tn.outputs['Alpha']
        det = cfg.get('imgs', {}).get(m['samplers'].get('txDetail'))
        if m['shader'].startswith('ksPerPixelMultiMap') and p.get('useDetail', 0) > 0 and det is not None:
            # ksPerPixelMultiMap con detalle (semantica de AcTools DarkMaterial.Unpack.fx Unpack_Maps l.92-106):
            # color = diffuse.rgb * lerp(detail.rgb, 1, diffuse.a), detalle con UV * detailUVMultiplier
            esc = _vec_math(nt, 'SCALE', uvn.outputs['UV'], None, (-900, 450))
            esc.inputs['Scale'].default_value = float(p.get('detailUVMultiplier', 1.0))
            td = nt.nodes.new('ShaderNodeTexImage')
            td.location = (-700, 450)
            td.image = det
            td.interpolation = 'Linear'
            td.extension = 'REPEAT'
            nt.links.new(esc.outputs[0], td.inputs['Vector'])
            uno = _vec_math(nt, 'SUBTRACT', (1.0, 1.0, 1.0), td.outputs['Color'], (-500, 450))
            sa = _vec_math(nt, 'SCALE', uno.outputs[0], None, (-350, 450))
            nt.links.new(alfa, sa.inputs['Scale'])
            fac = _vec_math(nt, 'ADD', td.outputs['Color'], sa.outputs[0], (-200, 450))
            txd = _vec_math(nt, 'MULTIPLY', tx, fac.outputs[0], (-50, 300))
            tx = txd.outputs[0]
            cfg.setdefault('multimap_detalle', []).append(m['nombre'])
        if m['blend'] != 1:
            alfa = None
    else:
        rgb = nt.nodes.new('ShaderNodeRGB')
        rgb.outputs[0].default_value = (0.5, 0.5, 0.5, 1.0)
        tx, alfa = rgb.outputs[0], None
    # D = SOL * N.L * sombra: difuso blanco bajo el sol (fuerza pi -> radiancia = N.L * sombra) por Shader to RGB
    dif = nt.nodes.new('ShaderNodeBsdfDiffuse')
    dif.location = (-700, -200)
    dif.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new('ShaderNodeShaderToRGB')
    s2r.location = (-500, -200)
    nt.links.new(dif.outputs['BSDF'], s2r.inputs['Shader'])
    D = _vec_math(nt, 'MULTIPLY', s2r.outputs['Color'], tuple(cfg['sol']), (-300, -200))
    # luz = ka * AMB + kd * D + kem
    luz = _vec_math(nt, 'MULTIPLY_ADD', D.outputs[0], (kd, kd, kd), (-100, -100))
    luz.inputs[2].default_value = tuple(ka * c + kem for c in cfg['amb'])
    col = _vec_math(nt, 'MULTIPLY', tx, luz.outputs[0], (100, 0))
    res = col
    if ks > 1e-6:
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        geo.location = (-700, -500)
        h = _vec_math(nt, 'ADD', geo.outputs['Incoming'], tuple(sol_dir), (-500, -500))
        h = _vec_math(nt, 'NORMALIZE', h.outputs[0], None, (-350, -500))
        nh = _vec_math(nt, 'DOT_PRODUCT', geo.outputs['Normal'], h.outputs[0], (-200, -500))
        mx = nt.nodes.new('ShaderNodeMath')
        mx.operation = 'MAXIMUM'
        mx.location = (-50, -500)
        nt.links.new(nh.outputs['Value'], mx.inputs[0])
        mx.inputs[1].default_value = 0.0
        pw = nt.nodes.new('ShaderNodeMath')
        pw.operation = 'POWER'
        pw.location = (100, -500)
        nt.links.new(mx.outputs[0], pw.inputs[0])
        pw.inputs[1].default_value = kexp
        km = nt.nodes.new('ShaderNodeMath')
        km.operation = 'MULTIPLY'
        km.location = (250, -500)
        nt.links.new(pw.outputs[0], km.inputs[0])
        km.inputs[1].default_value = ks
        sp = _vec_math(nt, 'SCALE', D.outputs[0], None, (400, -400))
        nt.links.new(km.outputs[0], sp.inputs['Scale'])
        res = _vec_math(nt, 'ADD', col.outputs[0], sp.outputs[0], (550, -100))
    # niebla de Kunos: lerp(color, FOG, blend * (1 - exp(-d / dist)))
    fcol, fbl, fdist = cfg['niebla']
    cam = nt.nodes.new('ShaderNodeCameraData')
    cam.location = (300, 300)
    e1 = nt.nodes.new('ShaderNodeMath')
    e1.operation = 'MULTIPLY'
    e1.location = (450, 300)
    nt.links.new(cam.outputs['View Distance'], e1.inputs[0])
    e1.inputs[1].default_value = -1.0 / fdist
    e2 = nt.nodes.new('ShaderNodeMath')
    e2.operation = 'EXPONENT'
    e2.location = (600, 300)
    nt.links.new(e1.outputs[0], e2.inputs[0])
    e3 = nt.nodes.new('ShaderNodeMath')
    e3.operation = 'MULTIPLY_ADD'
    e3.location = (750, 300)
    nt.links.new(e2.outputs[0], e3.inputs[0])
    e3.inputs[1].default_value = -fbl
    e3.inputs[2].default_value = fbl                      # f = blend - blend * exp(-d/dist)
    dfog = _vec_math(nt, 'SUBTRACT', tuple(fcol), res.outputs[0], (900, 150))      # FOG - color
    sfog = _vec_math(nt, 'SCALE', dfog.outputs[0], None, (1000, 150))
    nt.links.new(e3.outputs[0], sfog.inputs['Scale'])
    fin = _vec_math(nt, 'ADD', res.outputs[0], sfog.outputs[0], (1050, 50))       # color + (FOG - color) * f
    em = nt.nodes.new('ShaderNodeEmission')
    em.location = (1150, 100)
    nt.links.new(fin.outputs[0], em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.0
    sh = em.outputs['Emission']
    if m['blend'] == 1 and alfa is not None:      # alpha blend del KN5
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        tr.location = (1150, -100)
        mx2 = nt.nodes.new('ShaderNodeMixShader')
        mx2.location = (1350, 0)
        nt.links.new(alfa, mx2.inputs['Fac'])
        nt.links.new(tr.outputs['BSDF'], mx2.inputs[1])
        nt.links.new(sh, mx2.inputs[2])
        sh = mx2.outputs['Shader']
        try:
            mat.surface_render_method = 'BLENDED'
        except Exception:  # noqa
            pass
    nt.links.new(sh, out.inputs['Surface'])
    return mat


def montar_escena(bpy, kn5, dir_tex, cfg, log):
    """Crea imagenes, materiales y objetos (coordenadas Blender, mundo). Devuelve cifras."""
    os.makedirs(dir_tex, exist_ok=True)
    imgs, st = {}, {'png': 0, 'dds': 0, 'otras': 0, 'lados': {}}
    for n, blob in kn5['texturas'].items():
        if blob[:8] == b'\x89PNG\r\n\x1a\n':
            ruta = os.path.join(dir_tex, n if n.lower().endswith('.png') else n + '.png')
            with open(ruta, 'wb') as fh:
                fh.write(blob)
            img = bpy.data.images.load(ruta, check_existing=False)
            st['png'] += 1
        else:
            a = decodificar_dds(blob)
            if a is None:
                st['otras'] += 1
                log('AVISO textura %s en formato no soportado por kn5_vista (%r): gris' % (n, blob[:4]))
                continue
            h, w = a.shape[:2]
            img = bpy.data.images.new(n, w, h, alpha=True, float_buffer=False)
            img.pixels.foreach_set(np.ascontiguousarray(a[::-1]).ravel())
            img.pack()
            st['dds'] += 1
        img.colorspace_settings.name = 'Non-Color'     # AC usa los valores del fichero tal cual (espacio gamma)
        try:
            img.alpha_mode = 'CHANNEL_PACKED'             # RGB y A independientes (el alfa del MultiMap es la mascara)
        except Exception:  # noqa
            pass
        imgs[n] = img
        lado = str(max(img.size))
        st['lados'][lado] = st['lados'].get(lado, 0) + 1
    sol_dir = cfg['sol_dir']
    cfg['imgs'] = imgs
    mats = []
    for m in kn5['materiales']:
        img = imgs.get(m['samplers'].get('txDiffuse'))
        mats.append(material_ac(bpy, m, img, sol_dir, cfg))
    sc = bpy.context.scene
    n_ob, n_tris, sin_sombra, omitidas = 0, 0, 0, 0
    C = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], np.float64)     # kn5 -> blender: (x, y, z)_b = (x, -z, y)_k
    for mm in kn5['mallas']:
        if not mm['renderable'] or not mm['visible'] or len(mm['I']) < 3:
            omitidas += 1
            continue
        V = mm['V']
        M = mm['mundo']
        P = V[:, 0:3].astype(np.float64) @ M[:3, :3].T + M[:3, 3]
        N = V[:, 3:6].astype(np.float64) @ M[:3, :3].T
        P = P @ C.T
        N = N @ C.T
        ln = np.linalg.norm(N, axis=1)
        ln[ln < 1e-9] = 1.0
        N /= ln[:, None]
        T = mm['I'].astype(np.int32).reshape(-1, 3)
        me = bpy.data.meshes.new(mm['nombre'])
        me.vertices.add(len(P))
        me.vertices.foreach_set('co', P.astype(np.float32).ravel())
        me.loops.add(T.size)
        me.loops.foreach_set('vertex_index', T.ravel())
        me.polygons.add(len(T))
        me.polygons.foreach_set('loop_start', np.arange(0, T.size, 3, dtype=np.int32))
        me.polygons.foreach_set('loop_total', np.full(len(T), 3, np.int32))
        uvl = me.uv_layers.new(name='UV')
        uv = V[:, 6:8].astype(np.float32)[T.ravel()].copy()
        uv[:, 1] = 1.0 - uv[:, 1]
        uvl.data.foreach_set('uv', uv.ravel())
        me.update(calc_edges=True)
        try:
            me.shade_smooth()
        except AttributeError:
            me.polygons.foreach_set('use_smooth', np.ones(len(T), bool))
        try:
            me.normals_split_custom_set_from_vertices(N.astype(np.float32))
        except Exception as e:  # noqa
            log('AVISO normales %s: %s' % (mm['nombre'], e))
        mid = mm['mat'] if 0 <= mm['mat'] < len(mats) else 0
        me.materials.append(mats[mid])
        ob = bpy.data.objects.new(mm['nombre'], me)
        ob.visible_shadow = bool(mm['cast'])
        if not mm['cast']:
            sin_sombra += 1
        sc.collection.objects.link(ob)
        n_ob += 1
        n_tris += len(T)
    return {'mallas': n_ob, 'triangulos': n_tris, 'mallas_sin_sombra': sin_sombra, 'omitidas_no_renderables': omitidas,
            'texturas': st, 'materiales': len(mats), 'multimap_con_detalle': cfg.get('multimap_detalle', [])}


def cielo_hdr(cam_loc, cam_tgt, lens, rx, ry):
    """Cielo de 3_clear por pixel (HDR gamma): HORIZONTE en la linea del horizonte -> CIELO hacia el cenit (pow 0.5 de la
    elevacion), mismo encuadre que la camara de Blender (sensor 36 mm, ajuste AUTO al lado mayor)."""
    f = np.asarray(cam_tgt, np.float64) - np.asarray(cam_loc, np.float64)
    f /= np.linalg.norm(f)
    up = np.array([0.0, 0.0, 1.0])
    rgt = np.cross(f, up)
    rgt /= max(np.linalg.norm(rgt), 1e-9)
    upc = np.cross(rgt, f)
    half_w = 18.0 / lens if rx >= ry else 18.0 / lens * rx / ry
    half_h = half_w * ry / rx
    xs = (np.arange(rx) + 0.5) / rx * 2 - 1
    ys = 1 - (np.arange(ry) + 0.5) / ry * 2
    d = f[None, None] + xs[None, :, None] * half_w * rgt[None, None] + ys[:, None, None] * half_h * upc[None, None]
    d /= np.linalg.norm(d, axis=2, keepdims=True)
    e = np.clip(d[..., 2], 0.0, 1.0) ** 0.5
    return color_ac.HORIZONTE_AC[None, None] * (1 - e[..., None]) + color_ac.CIELO_AC[None, None] * e[..., None]


def png8(bpy, arr, ruta):
    """Guarda un array (H, W, 3) 0..1 (fila 0 arriba) como PNG con la API de imagenes de Blender."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new('_tmp_png', w, h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    rgba = np.concatenate([arr[::-1], np.ones((h, w, 1), np.float32)], axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = ruta
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def leer_png(bpy, ruta):
    img = bpy.data.images.load(ruta, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    buf = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(h, w, 4)[::-1, :, :3]


def main(argv):
    import bpy
    from mathutils import Euler, Vector
    args = {'--kn5': None, '--out': None, '--camaras': CAMARAS_DEF, '--solo': '', '--res': '1600x900', '--muestras': '16',
            '--comparar': '', '--guardar-blend': ''}
    flags = set()
    i = 0
    while i < len(argv):
        if argv[i] in args:
            args[argv[i]] = argv[i + 1]
            i += 2
        else:
            flags.add(argv[i])
            i += 1
    out = args['--out']
    os.makedirs(out, exist_ok=True)
    flog = open(os.path.join(out, 'vista.log'), 'w', encoding='utf-8')

    def log(s):
        print(s)
        flog.write(s + '\n')
        flog.flush()
    t0 = time.time()
    kn5 = leer_kn5(args['--kn5'])
    log('KN5 %s: %.1f MB, %d texturas, %d materiales, %d mallas, %d dummies [%.1fs]' % (
        args['--kn5'], kn5['bytes'] / 1e6, len(kn5['texturas']), len(kn5['materiales']), len(kn5['mallas']),
        kn5['dummies'], time.time() - t0))
    shaders = sorted({m['shader'] for m in kn5['materiales']})
    log('shaders en el KN5: %s' % shaders)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sol = SOL_DEF
    try:
        sys.path.insert(0, os.path.join(BASE, '03_blender'))
        import mascara_terreno
        sol = dict(mascara_terreno.SOL)
    except Exception as e:  # noqa
        log('AVISO: mascara_terreno.SOL no disponible (%s): sol por defecto %s' % (e, SOL_DEF))
    rot = Euler([math.radians(a) for a in sol['rot_blender_deg']], 'XYZ')
    sol_dir = tuple((rot.to_matrix() @ Vector((0.0, 0.0, 1.0))).normalized())        # hacia el sol
    cfg = {'sol': tuple(float(c) for c in color_ac.SOL_AC), 'amb': tuple(float(c) for c in color_ac.AMB_AC),
           'niebla': (tuple(float(c) for c in color_ac.NIEBLA_AC[0]), float(color_ac.NIEBLA_AC[1]),
                      float(color_ac.NIEBLA_AC[2])), 'sol_dir': sol_dir}
    st = montar_escena(bpy, kn5, os.path.join(out, '_texturas_kn5'), cfg, log)
    log('escena: %s [%.1fs]' % (json.dumps(st), time.time() - t0))
    ld = bpy.data.lights.new('SOL_AC', 'SUN')
    ld.energy = math.pi                     # difuso blanco: radiancia = E cos / pi -> N.L exacto
    ld.angle = math.radians(0.6)
    ld.use_shadow = '--sin-sombras' not in flags
    if hasattr(ld, 'shadow_maximum_resolution'):
        ld.shadow_maximum_resolution = 0.02     # 2 cm: el mapa de sombras de AC es mucho mas basto; evita llenar el pool
    lo = bpy.data.objects.new('SOL_AC', ld)
    lo.rotation_euler = rot
    sc.collection.objects.link(lo)
    w = bpy.data.worlds.new('negro')
    w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0, 0, 0, 1)
    bg.inputs['Strength'].default_value = 0.0
    sc.world = w
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in
                                                               bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
    ee = sc.eevee
    for attr, val in (('use_raytracing', False), ('use_fast_gi', False), ('use_gtao', False), ('use_bloom', False),
                      ('use_ssr', False), ('taa_render_samples', int(args['--muestras'])),
                      ('use_shadows', '--sin-sombras' not in flags), ('shadow_ray_count', 1), ('shadow_step_count', 6),
                      ('shadow_pool_size', '1024')):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except Exception:  # noqa
                pass
    rx, ry = [int(v) for v in args['--res'].split('x')]
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = rx, ry, 100
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    sc.render.image_settings.color_mode = 'RGBA'
    if args['--guardar-blend']:
        bpy.ops.wm.save_as_mainfile(filepath=args['--guardar-blend'])
        log('escena guardada en %s' % args['--guardar-blend'])
    cams = json.load(open(args['--camaras'], encoding='utf-8'))
    solo = [s for s in args['--solo'].split(',') if s]
    tomas = [t for t in TOMAS_DEF if (not solo or t.startswith(tuple(solo)))]
    if solo:
        tomas += [n for n in cams if not n.startswith('_') and n.startswith(tuple(solo)) and n not in tomas]
    res = {'kn5': args['--kn5'], 'escena': st, 'shaders': shaders, 'sol': sol, 'tomas': {}}
    for nombre in tomas:
        c = cams.get(nombre)
        if not c:
            log('AVISO: %s no esta en %s' % (nombre, args['--camaras']))
            continue
        cd = bpy.data.cameras.new('V_' + nombre)
        cd.lens = float(c['lens'])
        cd.clip_start = 0.1
        cd.clip_end = 12000
        co = bpy.data.objects.new('V_' + nombre, cd)
        co.location = Vector(c['loc'])
        co.rotation_euler = (Vector(c['tgt']) - Vector(c['loc'])).to_track_quat('-Z', 'Y').to_euler()
        sc.collection.objects.link(co)
        sc.camera = co
        exr = os.path.join(out, '_' + nombre + '.exr')
        sc.render.filepath = exr
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(exr, check_existing=False)
        buf = np.empty(rx * ry * 4, np.float32)
        img.pixels.foreach_get(buf)
        bpy.data.images.remove(img)
        hdr = buf.reshape(ry, rx, 4)[::-1].astype(np.float64)
        a = np.clip(hdr[..., 3:4], 0, 1)
        cielo = cielo_hdr(c['loc'], c['tgt'], float(c['lens']), rx, ry)
        esc = hdr[..., :3] + cielo * (1 - a)          # emision premultiplicada por alfa + cielo detras
        pan = color_ac.pantalla_ac(esc).astype(np.float32)
        ruta = os.path.join(out, nombre + '.png')
        png8(bpy, pan, ruta)
        try:
            os.remove(exr)
        except OSError:
            pass
        fila = {'segundos': round(time.time() - t1, 1), 'pct_cielo': round(float((a < 0.5).mean() * 100), 1),
                'media_srgb8': [int(round(v)) for v in (pan.reshape(-1, 3).mean(0) * 255)],
                'media_srgb8_no_cielo': [int(round(v)) for v in (pan[a[..., 0] >= 0.5].mean(0) * 255)] if (a >= 0.5).any() else None}
        if args['--comparar']:
            # varias carpetas separadas por coma, en orden de preferencia (v1.2: f1_final/despues_ac no tiene la 01,
            # que se toma de f1_r4/despues_ac); la que se usa queda en vista.json ('ref_proxy')
            refs = [os.path.join(d, nombre + '.png') for d in args['--comparar'].split(',') if d]
            ref = next((r for r in refs if os.path.exists(r)), refs[0] if refs else '')
            if os.path.exists(ref):
                fila['ref_proxy'] = ref
                r8 = leer_png(bpy, ref).astype(np.float32)
                if r8.shape[:2] == pan.shape[:2]:
                    sep = np.ones((ry, 8, 3), np.float32)
                    png8(bpy, np.concatenate([r8, sep, pan], axis=1), os.path.join(out, nombre + '_par.png'))
                    fila['media_srgb8_proxy'] = [int(round(v)) for v in (r8.reshape(-1, 3).mean(0) * 255)]
        res['tomas'][nombre] = fila
        log('%s %.1fs cielo %.1f %% media %s' % (nombre, fila['segundos'], fila['pct_cielo'], fila['media_srgb8']))
    res['segundos'] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(out, 'vista.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    log('OK kn5_vista -> %s (%d tomas, %.0fs)' % (out, len(res['tomas']), time.time() - t0))
    flog.close()


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
