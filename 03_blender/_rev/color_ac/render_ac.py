# -*- coding: utf-8 -*-
"""render_ac.py (v3) - pases de render de la escena CONGELADA (03_blender/_rev/color_ac/escena_color.blend: copia de
escena_rev.blend de las 13:00, md5 en escena_color.md5; se abre en memoria y nunca se guarda) para simular Assetto
Corsa sin el juego. Por cada vista:
  ref   render normal de Blender (lo que queremos ver en AC)                        -> <vista>_blender.png
  clay  misma luz con todo blanco 0.8 (luz de Blender por pixel y canal, con GI)      -> pase
  sol   solo el sol: N.L * sombra (mundo negro, sin GI ni oclusion, como AC)          -> pase
  geo   (N.H con H = sol + camara, N.z*0.5+0.5, distancia a la camara / 1000)        -> pase
  id    indice de material (R = (i+1)/1024, G = control, B = 1)                       -> pase
  pat   patron lineal de la textura del writer: mezcla(factor; 1, imagen*ganancia)  -> pase
  alb   Base Color del Principled (albedo de Blender por pixel, procedural incluido)  -> pase
  msk   en MAT_terreno: R = mascara de roca de Blender (nodo ROCA_mascara), G y B = atributo 'roca' y N.z de la cara
        (con ellos color_ac.mascara_roca() da las caras que el writer pasa a MAT_terreno_roca) -> pase
Con id + pat, simular_vistas.py reconstruye la textura de AC de CUALQUIER calibracion sin volver a renderizar.
Pases en _pases/<vista>_<pase>.npy (float16; id en float32) y _pases/materiales_vista.json (indice -> material).
  bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/color_ac/render_ac.py [-- vista1,vista2]
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Euler, Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
REV = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
from analisis_mat import analizar, srgb_to_lin  # noqa: E402
sys.path.insert(0, os.path.abspath(os.path.join(REV, '..', '..', '04_export')))
import color_ac  # noqa: E402

PASES = os.path.join(AQUI, '_pases')
os.makedirs(PASES, exist_ok=True)
RES = (960, 540)
t0 = time.time()
ESCENA = os.environ.get('ESCENA') or os.path.join(AQUI, 'escena_color.blend')
bpy.ops.wm.open_mainfile(filepath=ESCENA)
print('escena:', ESCENA)
sc = bpy.context.scene
G = json.load(open(os.path.join(REV, 'geometria_rev.json'), encoding='utf-8'))
S, N, paso, L = G['muestras'], G['n'], G['paso_m'], G['largo_m']
CUR = {c['n']: c for c in G['curvas']}


def fr(s_m):
    return S[int(round((s_m % L) / paso)) % N]


def tras(s_m, atras, alto, adelante=110.0, lens=30):
    p0, p1 = fr(s_m - atras), fr(s_m + adelante)
    return (p0['x'], p0['y'], p0['z'] + alto), (p1['x'], p1['y'], p1['z'] + 3.0), lens


def piloto(s_m, lens=24):
    p0, p1 = fr(s_m), fr(s_m + 80)
    return (p0['x'], p0['y'], p0['z'] + 1.4), (p1['x'], p1['y'], p1['z'] + 1.2), lens


def s_curva(n):
    return CUR[n]['s_idx'] * paso


_pa, _pb = fr(L - 95), fr(L + 60)
VISTAS = {
    # AJUSTE (con ellas se eligen los parametros de color_ac)
    'meta_tunel': ((_pa['x'], _pa['y'], _pa['z'] + 2.4), (_pb['x'], _pb['y'], _pb['z'] + 3.0), 22),
    # encuadre de la captura del usuario: camara de persecucion (3.2 m, 9 grados hacia abajo) en s = 40 m,
    # tribuna con techo a la izquierda, portico WORLD GRAND PRIX y montana-coche al fondo, ladera con palmeras
    'captura': ('pitch', 40.0, 3.2, -9.0, 26),
    'pueblo': tras(880, 100, 14, lens=28),
    'tierra': tras(s_curva(15), 100, 20),
    'casino': tras(s_curva(34), 90, 24),
    'piloto_s300': piloto(300),
    # v3: recta de meta con el puerto y el mar a la izquierda (como 02_meta_y_puerto de capturas_avance): la unica vista
    # de ajuste con agua (antes el mar solo salia en 'puente', de control, y su objetivo era un color fijo)
    'meta_puerto': tras(0, 80, 14, lens=28),
    # CONTROL (no se usan para elegir nada: comprueban que el resultado generaliza)
    'bajada': tras(s_curva(30), 80, 16),
    'puente': tras(s_curva(41), 80, 24),
    'piloto_s2900': piloto(2900),
}
sel = sys.argv[sys.argv.index('--') + 1].split(',') if '--' in sys.argv else list(VISTAS)
sol = next(o for o in bpy.data.objects if o.type == 'LIGHT' and o.data.type == 'SUN')
HACIA_SOL = -(sol.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
mundo0 = sc.world
negro = bpy.data.worlds.new('NEGRO')
negro.use_nodes = True
negro.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
ajustes0 = (sc.view_settings.view_transform, sc.view_settings.look, sc.view_settings.exposure,
            getattr(sc.eevee, 'use_raytracing', None), sc.render.filter_size)
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100

# ----------------------------------------------------------------------------- nodos por material
_gan = {}


def ganancia(img):
    """1 / media lineal por canal (igual que construir_textura del writer)."""
    if img.name not in _gan:
        px = np.empty(len(img.pixels), np.float32)
        img.pixels.foreach_get(px)
        lin = srgb_to_lin(px.reshape(-1, img.channels)[:, :3])
        _gan[img.name] = 1.0 / np.maximum(lin.mean(0), 1e-4)
    return _gan[img.name]


def _e(nodo, ident):
    return next(x for x in nodo.inputs if x.identifier == ident)


def _s(nodo, ident):
    return next(x for x in nodo.outputs if x.identifier == ident)


def emision(nt, color=None, desde=None):
    e = nt.nodes.new('ShaderNodeEmission')
    if desde is not None:
        nt.links.new(desde, e.inputs['Color'])
    elif color is not None:
        e.inputs['Color'].default_value = (float(color[0]), float(color[1]), float(color[2]), 1.0)
    return e.outputs[0]


def preparar(m, idx):
    """Crea en el material los nodos de cada pase y devuelve (salida, {pase: socket}, info del writer)."""
    nt = m.node_tree
    nod = nt.nodes.new
    out = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output), None) \
        or nod('ShaderNodeOutputMaterial')
    info = analizar(m, medias=False)
    sk = {'ref': out.inputs['Surface'].links[0].from_socket if out.inputs['Surface'].is_linked else None}
    clay = nod('ShaderNodeBsdfDiffuse')
    clay.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1.0)
    sk['clay'] = clay.outputs[0]
    dif = nod('ShaderNodeBsdfDiffuse')
    dif.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    s2r = nod('ShaderNodeShaderToRGB')
    nt.links.new(dif.outputs[0], s2r.inputs[0])
    sk['sol'] = emision(nt, desde=s2r.outputs['Color'])
    sk['id'] = emision(nt, color=((idx + 1) / 1024.0, ((idx + 1) * 37 % 101) / 101.0, 1.0))
    # patron de la textura (como construir_textura: color * (1 - f + f * imagen * ganancia))
    tex = nt.nodes.get('TEX_imagen')
    if info['img'] is not None and tex is not None and tex.bl_idname == 'ShaderNodeTexImage' and tex.image:
        g = ganancia(tex.image)
        it = nod('ShaderNodeTexImage')
        it.image = tex.image
        if tex.inputs['Vector'].is_linked:
            nt.links.new(tex.inputs['Vector'].links[0].from_socket, it.inputs['Vector'])
        mg = nod('ShaderNodeMix')
        mg.data_type, mg.blend_type = 'RGBA', 'MULTIPLY'
        _e(mg, 'Factor_Float').default_value = 1.0
        nt.links.new(it.outputs['Color'], _e(mg, 'A_Color'))
        _e(mg, 'B_Color').default_value = (float(g[0]), float(g[1]), float(g[2]), 1.0)
        mf = nod('ShaderNodeMix')
        mf.data_type = 'RGBA'
        _e(mf, 'Factor_Float').default_value = float(info['factor'])
        _e(mf, 'A_Color').default_value = (1.0, 1.0, 1.0, 1.0)
        nt.links.new(_s(mg, 'Result_Color'), _e(mf, 'B_Color'))
        sk['pat'] = emision(nt, desde=_s(mf, 'Result_Color'))
        info['pat_ganancia'] = [float(v) for v in g]
    else:
        sk['pat'] = emision(nt, color=(1.0, 1.0, 1.0))
    # albedo de Blender: Base Color del primer Principled (enlazado a rampas/ruidos o valor)
    pr = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if pr is not None and pr.inputs['Base Color'].is_linked:
        sk['alb'] = emision(nt, desde=pr.inputs['Base Color'].links[0].from_socket)
    elif pr is not None:
        sk['alb'] = emision(nt, color=pr.inputs['Base Color'].default_value)
    else:
        sk['alb'] = emision(nt, color=m.diffuse_color)
    # geo: N.H (H = normalizado(hacia el sol + hacia la camara)), N.z, distancia
    geo = nod('ShaderNodeNewGeometry')
    hv = nod('ShaderNodeVectorMath')
    hv.operation = 'ADD'
    nt.links.new(geo.outputs['Incoming'], hv.inputs[0])
    hv.inputs[1].default_value = tuple(HACIA_SOL)
    hn = nod('ShaderNodeVectorMath')
    hn.operation = 'NORMALIZE'
    nt.links.new(hv.outputs[0], hn.inputs[0])
    dot = nod('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    nt.links.new(hn.outputs[0], dot.inputs[0])
    nt.links.new(geo.outputs['Normal'], dot.inputs[1])
    mx = nod('ShaderNodeMath')
    mx.operation = 'MAXIMUM'
    nt.links.new(dot.outputs['Value'], mx.inputs[0])
    mx.inputs[1].default_value = 0.0
    sep = nod('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Normal'], sep.inputs[0])
    nz = nod('ShaderNodeMapRange')
    nt.links.new(sep.outputs['Z'], nz.inputs['Value'])
    nz.inputs['From Min'].default_value, nz.inputs['From Max'].default_value = -1.0, 1.0
    cam = nod('ShaderNodeCameraData')
    dk = nod('ShaderNodeMath')
    dk.operation = 'MULTIPLY'
    nt.links.new(cam.outputs['View Distance'], dk.inputs[0])
    dk.inputs[1].default_value = 0.001
    cc = nod('ShaderNodeCombineColor')
    nt.links.new(mx.outputs[0], cc.inputs[0])
    nt.links.new(nz.outputs['Result'], cc.inputs[1])
    nt.links.new(dk.outputs[0], cc.inputs[2])
    sk['geo'] = emision(nt, desde=cc.outputs[0])
    return out, sk, info


# caras de roca segun el criterio del writer: atributo de cara 'roca_ac' (lo lee el pase msk)
ROCA = {}
for ob in bpy.data.objects:
    if ob.type == 'MESH' and ob.data.library is None and any(
            m is not None and m.name == color_ac.ROCA_BASE for m in ob.data.materials):
        es_ter, nz, roca = color_ac.datos_caras(ob)
        mk = es_ter & color_ac.mascara_roca(nz, roca)
        for nom, val in (('roca_med', roca if roca is not None else np.zeros(len(nz))), ('nz_cara', nz * 0.5 + 0.5)):
            at = ob.data.attributes.get(nom) or ob.data.attributes.new(nom, 'FLOAT', 'FACE')
            at.data.foreach_set('value', np.asarray(val, np.float32))
        ROCA[ob.name] = [int(mk.sum()), len(mk)]
print('caras de roca (criterio del writer):', ROCA)


def pase_mascara(m):
    """msk (solo MAT_terreno; negro en el resto): R = mascara de roca de Blender, G = media del atributo 'roca' de la
    cara y B = N.z de la cara * 0.5 + 0.5 (con el volteo de exportar_ac): con G y B, color_ac.mascara_roca() da la cara
    de roca del writer."""
    nt = m.node_tree
    if m.name != color_ac.ROCA_BASE:
        return emision(nt, color=(0.0, 0.0, 0.0))
    nodo = next((n for n in nt.nodes if n.label == 'ROCA_mascara'), None)
    cc = nt.nodes.new('ShaderNodeCombineColor')
    if nodo is not None:
        nt.links.new(nodo.outputs['Value'], cc.inputs[0])
    for k, nom in ((1, 'roca_med'), (2, 'nz_cara')):
        atr = nt.nodes.new('ShaderNodeAttribute')
        atr.attribute_name = nom
        nt.links.new(atr.outputs['Fac'], cc.inputs[k])
    return emision(nt, desde=cc.outputs[0])


MATS, INFOS = {}, []
usados = [m for m in bpy.data.materials if m.users and not m.is_grease_pencil]   # todos (tambien instancias de LIB)
for i, m in enumerate(usados):
    if not m.use_nodes:
        m.use_nodes = True
    out, sk, info = preparar(m, i)
    sk['msk'] = pase_mascara(m)
    MATS[m.name] = (out, sk)
    INFOS.append(info)
json.dump({'materiales': INFOS}, open(os.path.join(PASES, 'materiales_vista.json'), 'w', encoding='utf-8'),
          indent=0, ensure_ascii=False)
print('nodos de %d materiales listos [%.0fs]' % (len(MATS), time.time() - t0))


def poner(pase):
    for out, sk in MATS.values():
        if sk.get(pase) is not None:
            out.id_data.links.new(sk[pase], out.inputs['Surface'])


def modo(emision_pura):
    sc.world = negro if emision_pura else mundo0
    sc.render.film_transparent = emision_pura
    sc.view_settings.view_transform = 'Standard' if emision_pura else ajustes0[0]
    sc.view_settings.look = 'None' if emision_pura else ajustes0[1]
    sc.view_settings.exposure = 0.0 if emision_pura else ajustes0[2]
    if ajustes0[3] is not None:
        sc.eevee.use_raytracing = False if emision_pura else ajustes0[3]


def render(nombre, exr, preciso=False):
    sc.render.image_settings.file_format = 'OPEN_EXR' if exr else 'PNG'
    if exr:
        sc.render.image_settings.color_depth = '32'
    sc.render.filter_size = 0.01 if preciso else ajustes0[4]      # id: sin mezclar materiales en los bordes
    ruta = os.path.join(PASES if exr else AQUI, nombre + ('.exr' if exr else '.png'))
    sc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    if exr:
        img = bpy.data.images.load(ruta, check_existing=False)
        px = np.empty(len(img.pixels), np.float32)
        img.pixels.foreach_get(px)
        a = px.reshape(img.size[1], img.size[0], 4)[::-1]
        np.save(ruta[:-4] + '.npy', a if preciso else a.astype(np.float16))
        bpy.data.images.remove(img)
        os.remove(ruta)


def camara(v):
    d = VISTAS[v]
    cd = bpy.data.cameras.new('AC_' + v)
    cd.clip_end = 12000
    cam = bpy.data.objects.new('AC_' + v, cd)
    if d[0] == 'pitch':
        _, s_m, alto, pitch, lens = d
        p0, p1 = fr(s_m), fr(s_m + 20)
        yaw = math.atan2(p1['y'] - p0['y'], p1['x'] - p0['x'])
        cam.location = Vector((p0['x'], p0['y'], p0['z'] + alto))
        cam.rotation_euler = Euler((math.radians(90 + pitch), 0.0, yaw - math.pi / 2), 'XYZ')
        tgt = cam.location + cam.matrix_world.to_3x3() @ Vector((0.0, 0.0, -100.0))
    else:
        loc, tgt, lens = d
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    sc.collection.objects.link(cam)
    bpy.context.view_layer.update()
    m3 = cam.matrix_world.to_3x3()
    return cam, {'loc': list(cam.location), 'adelante': list(m3 @ Vector((0, 0, -1))),
                 'arriba': list(m3 @ Vector((0, 1, 0))), 'lens': lens}


_rv = os.path.join(PASES, 'vistas.json')
meta = json.load(open(_rv, encoding='utf-8')) if os.path.exists(_rv) else {}
camaras = meta.get('camaras', {})
for v in sel:
    cam, info_cam = camara(v)
    sc.camera = cam
    camaras[v] = info_cam
    for pase in ('ref', 'clay', 'sol', 'geo', 'id', 'pat', 'alb', 'msk'):
        poner(pase)
        modo(pase not in ('ref', 'clay'))
        render('%s_blender' % v if pase == 'ref' else '%s_%s' % (v, pase), exr=(pase != 'ref'), preciso=(pase in ('id', 'msk')))
        print('VISTA %s pase %s [%.0fs]' % (v, pase, time.time() - t0))
json.dump({'escena': ESCENA, 'roca_caras': ROCA, 'hacia_sol': list(HACIA_SOL), 'sol_energia': sol.data.energy, 'sol_color': list(sol.data.color),
           'exposicion_blender': ajustes0[2], 'vista_blender': ajustes0[0], 'look_blender': ajustes0[1],
           'camaras': camaras, 'ajuste': ['meta_tunel', 'captura', 'pueblo', 'tierra', 'casino', 'piloto_s300', 'meta_puerto'],
           'control': ['bajada', 'puente', 'piloto_s2900']},
          open(_rv, 'w', encoding='utf-8'), indent=1)
print('OK render_ac [%.0fs]' % (time.time() - t0))
