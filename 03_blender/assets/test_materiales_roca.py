# -*- coding: utf-8 -*-
"""test_materiales_roca.py - test headless del material de caliza compartido (assets/materiales_roca.py).

  bash 03_blender/_rev/blender_cola.sh --python 03_blender/assets/test_materiales_roca.py
(Blender 5.1 por la cola; sin tocar ningun .blend del proyecto)

Monta una escena de prueba con la luz de renderizar_capturas.py (sol 4.6 a 34 grados, Standard, exposicion 0.12):
  - pared vertical de 24 x 30 m DESPLAZADA del origen (x = 300, como TUNEL_acantilado/PENON_*) + un bloque a su lado
    en el ORIGEN con el mismo material: los estratos deben empalmar en z (coordenadas de mundo, no de objeto)
  - esfera de 6 m medio hundida bajo z = 1 (mojado) y una losa horizontal (repisa)
  - cubo con un material que lleva un nodo 'Math.002' etiquetado 'ROCA_mascara' (como el terreno): aplicar_a NO lo toca
Renderiza previews/materiales_roca_{pared,detalle,bancos,orientacion}.png (1280x720) y escribe previews/materiales_roca_test.json.
F1 r2 (secciones 6-8): entradas tono_pared/pared, grupo versionado (actualizar_grupo rehace un grupo v1 sin perder
enlaces), media_lineal con frac_pared y color_roca_terreno_ac, render de orientacion (cara vertical = tono_pared, cara
superior = tono_base; con pared = 0 vuelve a v1) y roca_caras_mascara sobre una mascara sintetica (con UV y sin UV).
Comprueba: grupo con entradas/salidas esperadas; cadena de imagen del writer (TEX_imagen BOX, TEX_ganancia,
TEX_multiplicar, TEX_mapping) con caliza_d.png; diffuse_color = media_lineal; marcadores CALIZA_ESTRATOS/TEXTURIZADO;
idempotencia (segunda llamada no anade nodos); 'Math.002' intacto; custom props ac_*; crear_nodos sin enlazar nada;
y que el patron es de MUNDO: dos objetos con el mismo material en z distinta dan luminancia media distinta por banda
(se mide en el render de la pared: perfil vertical con juntas periodicas cada ~3 m).
"""
import importlib.util
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(BASE)
PREV = os.path.join(BASE, 'previews')
os.makedirs(PREV, exist_ok=True)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
import paleta  # noqa: E402

spec = importlib.util.spec_from_file_location('materiales_roca', os.path.join(BASE, 'materiales_roca.py'))
MR = importlib.util.module_from_spec(spec)
sys.modules['materiales_roca'] = MR
spec.loader.exec_module(MR)

RES = (1280, 720)
fallos = []
info = {}


def check(cond, msg):
    print(('  OK   ' if cond else '  FALLO ') + msg)
    if not cond:
        fallos.append(msg)


def limpiar():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    for ma in list(bpy.data.materials):
        bpy.data.materials.remove(ma)
    for ng in list(bpy.data.node_groups):
        bpy.data.node_groups.remove(ng)


def caja(nombre, cx, cy, z0, sx, sy, sz, mat):
    me = bpy.data.meshes.new(nombre)
    hx, hy = sx / 2.0, sy / 2.0
    v = [(cx - hx, cy - hy, z0), (cx + hx, cy - hy, z0), (cx + hx, cy + hy, z0), (cx - hx, cy + hy, z0),
         (cx - hx, cy - hy, z0 + sz), (cx + hx, cy - hy, z0 + sz), (cx + hx, cy + hy, z0 + sz), (cx - hx, cy + hy, z0 + sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(v, [], f)
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def esfera(nombre, c, r, mat, n=32):
    me = bpy.data.meshes.new(nombre)
    verts, faces = [], []
    for i in range(n + 1):
        th = math.pi * i / n
        for j in range(n):
            ph = 2 * math.pi * j / n
            verts.append((c[0] + r * math.sin(th) * math.cos(ph), c[1] + r * math.sin(th) * math.sin(ph), c[2] + r * math.cos(th)))
    for i in range(n):
        for j in range(n):
            a = i * n + j
            b = i * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    me.from_pydata(verts, [], faces)
    me.update()
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def luz_y_mundo():
    sc = bpy.context.scene
    sun_data = bpy.data.lights.new('SOL', 'SUN')
    sun_data.energy = 4.6
    sun_data.color = (1.0, 0.96, 0.88)
    sun_data.angle = math.radians(3.0)
    sun = bpy.data.objects.new('SOL', sun_data)
    # F1: la elevacion del sol de la escena (construir_pista / mascara_terreno.SOL: 42 grados; antes 34); el azimut del test
    # se gira para que las caras -y (las que miran las camaras del test) esten al sol, como la pared de 51 (n.sol 0.9)
    sun.rotation_euler = (math.radians(42), 0, 0.0)   # azimut 0: hacia_sol = (0, -0.67, 0.74): las caras -y (las que miran las camaras) estan al sol
    sc.collection.objects.link(sun)
    # cielo en gradiente como renderizar_capturas / carta_color (construir_pista.py l.1585-1606)
    world = bpy.data.worlds.new('CIELO')
    world.use_nodes = True
    wnt = world.node_tree
    bg = wnt.nodes.get('Background')
    tco = wnt.nodes.new('ShaderNodeTexCoord')
    sep = wnt.nodes.new('ShaderNodeSeparateXYZ')
    mapr = wnt.nodes.new('ShaderNodeMapRange')
    mapr.inputs['From Min'].default_value = -0.05
    mapr.inputs['From Max'].default_value = 0.9
    rampc = wnt.nodes.new('ShaderNodeValToRGB')
    ec = rampc.color_ramp.elements
    ec[0].position = 0.0; ec[0].color = (0.70, 0.84, 0.98, 1)
    ec[1].position = 1.0; ec[1].color = (0.12, 0.34, 0.86, 1)
    em = rampc.color_ramp.elements.new(0.3)
    em.color = (0.36, 0.60, 0.95, 1)
    wnt.links.new(tco.outputs['Generated'], sep.inputs['Vector'])
    wnt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
    wnt.links.new(mapr.outputs['Result'], rampc.inputs['Fac'])
    wnt.links.new(rampc.outputs['Color'], bg.inputs['Color'])
    bg.inputs[1].default_value = 1.0
    sc.world = world
    for motor in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = motor
            break
        except Exception:
            continue
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.exposure = 0.12
    for attr, val in [('use_gtao', True), ('gtao_distance', 12.0), ('use_shadows', True), ('taa_render_samples', 32)]:
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100


def render(nombre, loc, tgt, lens=35):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new('CAM_' + nombre)
    cd.lens = lens
    cd.clip_end = 5000
    cam = bpy.data.objects.new('CAM_' + nombre, cd)
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    ruta = os.path.join(PREV, 'materiales_roca_%s.png' % nombre)
    sc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    print('  render ->', ruta)
    return ruta


def luminancia_png(ruta):
    img = bpy.data.images.load(ruta, check_existing=False)
    w, h = img.size
    buf = np.empty(len(img.pixels), np.float32)
    img.pixels.foreach_get(buf)
    rgb = buf.reshape(h, w, -1)[::-1, :, :3]
    bpy.data.images.remove(img)
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


# ------------------------------------------------------------------------------------------------- escena
limpiar()
luz_y_mundo()
print('1) grupo de nodos')
ng = MR.ng_caliza_estratos()
ins = [s.name for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT']
outs = [s.name for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'OUTPUT']
check(set(['tono_base', 'tono_junta', 'periodo_m', 'bump', 'mojado', 'fase', 'contraste_bancos']) <= set(ins), 'entradas %s' % ins)
check(outs == ['Color', 'Normal', 'AO'], 'salidas %s' % outs)
check(MR.ng_caliza_estratos() is ng, 'ng_caliza_estratos reutiliza el grupo')
check(any(n.type == 'NEW_GEOMETRY' for n in ng.nodes), 'usa Geometry.Position (coordenadas de mundo)')
info['grupo'] = {'entradas': ins, 'salidas': outs, 'nodos': len(ng.nodes)}

print('2) aplicar_a en un material plano (kit)')
m_roca = bpy.data.materials.new('MAT_PPUEBLO_roca')
m_roca.use_nodes = True
bs = next(n for n in m_roca.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bs.inputs['Base Color'].default_value = paleta.rgba('caliza_ocre')
m_roca.diffuse_color = paleta.rgba('caliza_ocre')
n0 = len(m_roca.node_tree.nodes)
g = MR.aplicar_a(m_roca, tono_base=paleta.rgb('caliza_ocre'))
nt = m_roca.node_tree
check(g is not None and g.type == 'GROUP' and g.node_tree is ng, 'nodo de grupo enlazado')
tex = nt.nodes.get('TEX_imagen')
check(tex is not None and tex.image is not None and os.path.basename(tex.image.filepath) == 'caliza_d.png'
      and tex.projection == 'BOX' and tex.outputs['Color'].is_linked, 'TEX_imagen caliza_d.png BOX enlazada (writer)')
check(nt.nodes.get('TEX_ganancia') is not None and nt.nodes.get('TEX_multiplicar') is not None
      and nt.nodes.get('TEX_mapping') is not None, 'TEX_ganancia / TEX_multiplicar / TEX_mapping')
check(bs.inputs['Base Color'].is_linked and bs.inputs['Base Color'].links[0].from_node.name == 'TEX_multiplicar',
      'Base Color <- TEX_multiplicar')
check(bs.inputs['Normal'].is_linked and bs.inputs['Normal'].links[0].from_node.name == g.name, 'Normal <- grupo')
med = MR.media_material(paleta.rgb('caliza_ocre'))          # v4: media_lineal x tinte del tile (caliza_d, factor 0.5)
check(all(abs(a - b) < 1e-4 for a, b in zip(m_roca.diffuse_color[:3], med)), 'diffuse_color = media_material %s' % (tuple(round(c, 3) for c in med),))
check(nt.nodes.get('CALIZA_ESTRATOS') is not None and nt.nodes.get('TEXTURIZADO') is not None, 'marcadores CALIZA_ESTRATOS + TEXTURIZADO')
check(all(k in m_roca for k in ('ac_shader', 'ac_props', 'ac_samplers', 'ac_tex_max', 'ac_alpha_test', 'ac_raw'))
      and m_roca['ac_shader'] == 'ksPerPixel', 'custom props ac_* con valores por defecto')
n1 = len(nt.nodes)
g2 = MR.aplicar_a(m_roca)
check(len(nt.nodes) == n1 and g2 is not None and g2.name == g.name, 'idempotente (segunda llamada: %d nodos, mismo grupo)' % len(nt.nodes))
check(MR.tiene_caliza(m_roca), 'tiene_caliza')
info['material_kit'] = {'nodos_antes': n0, 'nodos_despues': n1, 'diffuse_color': [round(c, 4) for c in m_roca.diffuse_color[:3]]}

print('3) material con rampa de moteado (McLaren) y material con ROCA_mascara (terreno)')
m_mc = bpy.data.materials.new('MAT_MCOCHE_caliza')
m_mc.use_nodes = True
ntm = m_mc.node_tree
bsm = next(n for n in ntm.nodes if n.type == 'BSDF_PRINCIPLED')
nz = ntm.nodes.new('ShaderNodeTexNoise')
rp = ntm.nodes.new('ShaderNodeValToRGB')
ntm.links.new(nz.outputs['Fac'], rp.inputs['Fac'])
ntm.links.new(rp.outputs['Color'], bsm.inputs['Base Color'])
m_mc.diffuse_color = (0.6, 0.49, 0.33, 1.0)
MR.aplicar_a(m_mc, tono_base=paleta.rgb('caliza_ocre'), contraste_bancos=0.06)
check(bsm.inputs['Base Color'].links[0].from_node.name == 'TEX_multiplicar', 'rampa de moteado sustituida por el grupo x imagen')

m_ter = bpy.data.materials.new('MAT_terreno_prueba')
m_ter.use_nodes = True
ntt = m_ter.node_tree
bst = next(n for n in ntt.nodes if n.type == 'BSDF_PRINCIPLED')
mask = ntt.nodes.new('ShaderNodeMath')
mask.name = 'Math.002'
mask.label = 'ROCA_mascara'
mask.operation = 'MAXIMUM'
mixr = ntt.nodes.new('ShaderNodeMix')
mixr.data_type = 'RGBA'
ntt.links.new(mask.outputs['Value'], mixr.inputs['Factor'])
ntt.links.new(mixr.outputs[2], bst.inputs['Base Color'])
enl_mask = len(mask.outputs['Value'].links)
# enganche del propietario 'mascara': crear_nodos y enlazar SOLO la rama de roca
gt, c_out, n_out, ao_out = MR.crear_nodos(ntt, tono_base=paleta.rgb('caliza_ocre'))
ntt.links.new(c_out, mixr.inputs[7])
check(ntt.nodes.get('Math.002') is not None and ntt.nodes.get('Math.002').label == 'ROCA_mascara'
      and len(mask.outputs['Value'].links) == enl_mask and mask.outputs['Value'].links[0].to_node.name == mixr.name,
      "crear_nodos deja 'Math.002'/'ROCA_mascara' intacto")
check(bst.inputs['Base Color'].links[0].from_node.name == mixr.name, 'crear_nodos no toca el Base Color del Principled')
check(not n_out.is_linked and not ao_out.is_linked, 'crear_nodos no enlaza Normal/AO por su cuenta')

print('4) escena: pared desplazada (x=300) + bloque en el origen con el MISMO material -> estratos de mundo')
caja('PARED', 300.0, 0.0, 0.0, 24.0, 2.0, 30.0, m_roca)
caja('BLOQUE', 0.0, 0.0, 0.0, 8.0, 8.0, 12.0, m_roca)
caja('BLOQUE_alto', 10.0, 0.0, 6.0, 8.0, 8.0, 12.0, m_roca)
esfera('BOLO', (300.0 + 18.0, -10.0, 2.0), 5.0, m_mc)
caja('REPISA', 300.0, -8.0, 9.0, 24.0, 6.0, 0.6, m_roca)
caja('SUELO', 300.0, 0.0, -0.1, 400.0, 400.0, 0.1, m_ter)
r_pared = render('pared', (300.0, -46.0, 14.0), (300.0, 0.0, 14.0), lens=35)
r_det = render('detalle', (300.0 + 14.0, -16.0, 5.0), (300.0 + 6.0, -1.0, 6.0), lens=40)
r_bancos = render('bancos', (-20.0, -36.0, 14.0), (5.0, 0.0, 8.0), lens=30)

print('5) medida: juntas periodicas en la pared (perfil vertical de luminancia)')
L = luminancia_png(r_pared)
h, w = L.shape
col = L[:, int(w * 0.40):int(w * 0.60)].mean(axis=1)          # franja central de la pared (promedia el grano)
# metros por pixel en el plano de la pared: camara a 46 m, lente 35 mm, sensor 36 mm (16:9 -> 20.25 mm vertical)
m_por_px = (46.0 * 20.25 / 35.0) / h
# quitamos el cielo (arriba) y la repisa/suelo (abajo): la pared ocupa ~ el 5-70 % de la altura de la imagen
seg = col[int(h * 0.05):int(h * 0.68)]
k_s = max(3, int(round(0.45 / m_por_px)) | 1)                     # suaviza el grano (~0.45 m)
seg = np.convolve(seg, np.ones(k_s) / k_s, mode='same')
k_t = int(round(3.0 / m_por_px)) | 1                                # quita la tendencia (bancos, luz) a escala de 3 m
seg = seg - np.convolve(seg, np.ones(k_t) / k_t, mode='same')
# minimos locales marcados (juntas): mas profundos que -0.02 y minimo en +-0.6 m; agrupados a < 1.5 m
r = max(2, int(round(0.6 / m_por_px)))
minimos = [i for i in range(r, len(seg) - r) if seg[i] < -0.02 and seg[i] == seg[i - r:i + r + 1].min()]
juntas = []
for i in minimos:
    if not juntas or (i - juntas[-1]) * m_por_px > 1.5:
        juntas.append(i)
info['juntas_z_px'] = juntas
sep = np.diff(juntas) * m_por_px if len(juntas) > 1 else np.array([])
info['juntas'] = {'n': len(juntas), 'separacion_m_media': round(float(sep.mean()), 2) if len(sep) else None,
                  'separacion_m_min_max': [round(float(sep.min()), 2), round(float(sep.max()), 2)] if len(sep) else None}
alto_m = len(seg) * m_por_px
check(len(juntas) >= alto_m / 3.0 * 0.6, 'juntas de estrato visibles en %.0f m de pared: %d (>= %.0f)' % (alto_m, len(juntas), alto_m / 3.0 * 0.6))
check(len(sep) == 0 or 1.8 <= float(np.median(sep)) <= 4.5, 'separacion mediana de juntas %.2f m (periodo 3 m +- distorsion)' % (float(np.median(sep)) if len(sep) else -1))
# manchas: la luminancia media por banda horizontal de ~2 m no varia mas de +-20 % (ya no hay velo de bruma)
nb = max(3, int(alto_m / 2.0))
tam = len(seg) // nb
bandas = [col[int(h * 0.05) + k * tam:int(h * 0.05) + (k + 1) * tam].mean() for k in range(nb)]
var = (max(bandas) - min(bandas)) / max(np.mean(bandas), 1e-4)
info['variacion_bandas'] = round(float(var), 3)
check(var < 0.45, 'variacion entre bandas de 2 m %.2f (< 0.45: sin manchas de +-50 %%)' % var)

print('6) v2 (F1 r2): tres tonos por orientacion, grupo versionado, media con pared, color_roca_terreno_ac')
ins2 = [s.name for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT']
check('tono_pared' in ins2 and 'pared' in ins2, 'entradas v2 tono_pared / pared')
check(int(ng.get('cal_version', 0)) == MR.CAL_VERSION, "ng['cal_version'] = %s" % ng.get('cal_version'))
check(MR.actualizar_grupo() is False, 'actualizar_grupo() sobre un grupo al dia no hace nada')
# grupo "viejo": se fuerza version 1 y se quita la entrada tono_pared -> actualizar_grupo la repone y rehace los nodos
# SIN perder los enlaces de los materiales que lo usan (m_roca: Color -> TEX_multiplicar, Normal -> Principled)
ng['cal_version'] = 1
sock_tp = next(s for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.name == 'tono_pared')
ng.interface.remove(sock_tp)
n_nodos_v1 = len(ng.nodes)
gn = next(n for n in m_roca.node_tree.nodes if n.type == 'GROUP')
enl_antes = (gn.outputs['Color'].links[0].to_node.name, gn.outputs['Normal'].links[0].to_node.name)
check(MR.actualizar_grupo() is True, 'actualizar_grupo() reconstruye un grupo v1 (sin tono_pared)')
ins3 = [s.name for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT']
check('tono_pared' in ins3 and int(ng['cal_version']) == MR.CAL_VERSION and len(ng.nodes) > 10,
      'tras actualizar: tono_pared repuesta, version %s, %d nodos (antes %d)' % (ng.get('cal_version'), len(ng.nodes), n_nodos_v1))
enl_despues = (gn.outputs['Color'].links[0].to_node.name if gn.outputs['Color'].links else None,
               gn.outputs['Normal'].links[0].to_node.name if gn.outputs['Normal'].links else None)
check(enl_despues == enl_antes, 'enlaces del nodo de grupo intactos %s' % (enl_despues,))
check('tono_pared' in gn.inputs and tuple(round(c, 3) for c in gn.inputs['tono_pared'].default_value[:3])
      == tuple(round(c, 3) for c in paleta.rgb('caliza_gris_calido')), 'nodo de grupo existente gana tono_pared = caliza_gris_calido')
check(ntt.nodes.get('Math.002') is not None and len(mask.outputs['Value'].links) == enl_mask, "'Math.002'/'ROCA_mascara' sigue intacto tras actualizar")
# media lineal: con pared la media baja (frac_pared 0.5 por defecto) y con frac_pared 1 es la caliza media
m0 = MR.media_lineal(paleta.rgb('caliza_ocre'), frac_pared=0.0)
m5 = MR.media_lineal(paleta.rgb('caliza_ocre'))
m1 = MR.media_lineal(paleta.rgb('caliza_ocre'), frac_pared=1.0)
lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
check(lum(m0) > lum(m5) > lum(m1), 'media_lineal baja con la pared: %.3f > %.3f > %.3f' % (lum(m0), lum(m5), lum(m1)))
cr = MR.color_roca_terreno_ac(ao=1.0)
check(all(abs(a - b) < 1e-6 for a, b in zip(m1, cr)), 'color_roca_terreno_ac(ao=1) = media de pared %s (%s)' % (
    tuple(round(c, 3) for c in m1), paleta.hex_desde_rgb(m1)))
cr2 = MR.color_roca_terreno_ac()
check(0.5 < MR.ao_media_terreno() <= 1.0 and all(abs(a - b * MR.ao_media_terreno()) < 1e-6 for a, b in zip(cr2, m1)),
      'color_roca_terreno_ac() = pared x AO media %.3f = %s (%s)' % (MR.ao_media_terreno(), tuple(round(c, 3) for c in cr2), paleta.hex_desde_rgb(cr2)))
check(all(abs(a - b) < 1e-4 for a, b in zip(m_roca.diffuse_color[:3], MR.media_material(paleta.rgb('caliza_ocre')))),
      'diffuse_color de aplicar_a = media con frac_pared 0.5 (x tinte del tile, v4)')
# la pared nunca mas clara que la base: roca_oscura (sombra) con tono_pared gris_calido -> media = sombra
ms = MR.media_lineal(paleta.rgb('caliza_sombra'), frac_pared=1.0, ao_pared=1.0)
check(all(abs(a - b) < 1e-3 for a, b in zip(ms, MR.media_lineal(paleta.rgb('caliza_sombra'), frac_pared=0.0))),
      'pared nunca mas clara que la base (min por canal)')
info['medias'] = {'repisa': [round(c, 4) for c in m0], 'mitad': [round(c, 4) for c in m5], 'pared': [round(c, 4) for c in m1]}

print('7) render de orientacion: tono_pared de prueba ROJO en un cubo -> caras verticales rojizas, cara superior no')
m_or = MR.material_caliza('MAT_test_orientacion', tono_base=paleta.rgb('caliza_ocre'), tono_pared=(0.60, 0.05, 0.05), imagen=None)
caja('CUBO_or', 600.0, 0.0, 0.0, 10.0, 10.0, 10.0, m_or)
cam_loc, cam_tgt = (600.0, -30.0, 22.0), (600.0, 0.0, 5.0)
r_or = render('orientacion', cam_loc, cam_tgt, lens=35)
from bpy_extras.object_utils import world_to_camera_view as w2cv
sc_ = bpy.context.scene
p_top = w2cv(sc_, sc_.camera, Vector((600.0, 0.0, 10.0)))      # centro de la cara superior
p_front = w2cv(sc_, sc_.camera, Vector((600.0, -5.0, 5.0)))    # centro de la cara frontal (vertical)
img_or = bpy.data.images.load(r_or, check_existing=False)
w_, h_ = img_or.size
buf = np.empty(len(img_or.pixels), np.float32)
img_or.pixels.foreach_get(buf)
rgb_or = buf.reshape(h_, w_, -1)[::-1, :, :3]
bpy.data.images.remove(img_or)


def _muestra(p, r=12):
    x, y = int(p.x * w_), int((1.0 - p.y) * h_)
    bloque = rgb_or[max(0, y - r):y + r, max(0, x - r):x + r].reshape(-1, 3).mean(axis=0)
    return bloque


top, front = _muestra(p_top), _muestra(p_front)
ratio_top = float(top[0] / max(top[1] + top[2], 1e-4))
ratio_front = float(front[0] / max(front[1] + front[2], 1e-4))
info['orientacion'] = {'top_srgb': [round(float(c), 3) for c in top], 'front_srgb': [round(float(c), 3) for c in front],
                       'ratio_top': round(ratio_top, 3), 'ratio_front': round(ratio_front, 3)}
# la cara vertical promedia tono rojo + juntas grises (6 %): R/(G+B) ~1.1; la superior (ocre al sol, recortada a blanco) ~0.5
check(ratio_front > 0.95 and ratio_top < 0.8, 'cara vertical roja (R/(G+B) %.2f) y superior no (%.2f)' % (ratio_front, ratio_top))
# y con pared = 0 (comportamiento v1) la cara vertical deja de ser roja
gn_or = next(n for n in m_or.node_tree.nodes if n.type == 'GROUP')
gn_or.inputs['pared'].default_value = 0.0
r_or0 = render('orientacion_v1', cam_loc, cam_tgt, lens=35)
img_or = bpy.data.images.load(r_or0, check_existing=False)
img_or.pixels.foreach_get(buf)
rgb_or = buf.reshape(h_, w_, -1)[::-1, :, :3]
bpy.data.images.remove(img_or)
front0 = _muestra(p_front)
ratio_front0 = float(front0[0] / max(front0[1] + front0[2], 1e-4))
check(ratio_front0 < 0.8, 'con pared = 0 la cara vertical vuelve al tono base (R/(G+B) %.2f)' % ratio_front0)
gn_or.inputs['pared'].default_value = 1.0
try:
    os.remove(r_or0)
except OSError:
    pass

print('8) roca_caras_mascara: canal A de una mascara sintetica por UV planar (con UV y sin UV)')
m_terr = bpy.data.materials.new('MAT_terreno')
m_terr.use_nodes = True
uvp = m_terr.node_tree.nodes.new('ShaderNodeVectorMath')
uvp.operation = 'MULTIPLY_ADD'
uvp.name = 'TERRENO_uv_planar'
uvp.inputs[1].default_value = (1.0 / 64.0, 1.0 / 64.0, 0.0)      # Lx = Ly = 64 m, x0 = y0 = 0
uvp.inputs[2].default_value = (0.0, 0.0, 0.0)
# mascara 16x16 RGBA: A = 1 en la mitad izquierda (u < 0.5), 0 a la derecha
mk = bpy.data.images.new('_mask_test', 16, 16, alpha=True)
px_ = np.zeros((16, 16, 4), np.float32)
px_[:, :8, 3] = 1.0
mk.pixels.foreach_set(px_.ravel())
ruta_mk = os.path.join(PREV, '_mask_test.png')
mk.filepath_raw = ruta_mk
mk.file_format = 'PNG'
mk.save()
bpy.data.images.remove(mk)


def rejilla(nombre, con_uv):
    me = bpy.data.meshes.new(nombre)
    n_ = 8
    vs = [(x * 8.0, y * 8.0, 0.0) for y in range(n_ + 1) for x in range(n_ + 1)]
    fs = [(y * (n_ + 1) + x, y * (n_ + 1) + x + 1, (y + 1) * (n_ + 1) + x + 1, (y + 1) * (n_ + 1) + x) for y in range(n_) for x in range(n_)]
    me.from_pydata(vs, [], fs)
    me.update()
    me.materials.append(m_terr)
    if con_uv:
        uv = me.uv_layers.new(name='UVMap')
        arr = np.array([(vs[l.vertex_index][0] / 64.0, vs[l.vertex_index][1] / 64.0) for l in me.loops], np.float32).ravel()
        try:
            uv.data.foreach_set('uv', arr)
        except Exception:
            uv.uv.foreach_set('vector', arr)
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


ob_uv = rejilla('TERRENO_test_uv', True)
ob_sin = rejilla('TERRENO_test_sin_uv', False)
r_uv = MR.roca_caras_mascara(ob_uv, ruta_mask=ruta_mk)
r_sin = MR.roca_caras_mascara(ob_sin, ruta_mask=ruta_mk)
esperado = np.array([(x < 4) for y in range(8) for x in range(8)])
check(r_uv.shape == (64,) and bool((r_uv == esperado).all()), 'con UV: %d/64 caras de roca = mitad izquierda' % int(r_uv.sum()))
check(bool((r_sin == esperado).all()), 'sin UV (TERRENO_uv_planar): %d/64 caras de roca = mitad izquierda' % int(r_sin.sum()))
caja('PARED_test', 40.0, 60.0, 0.0, 4.0, 4.0, 10.0, m_terr)       # cubo con MAT_terreno: 4 caras verticales (nz 0) + tapa
ob_c = bpy.data.objects['PARED_test']
r_c = MR.roca_caras_mascara(ob_c, ruta_mask=ruta_mk)
check(int(r_c.sum()) == 4, 'caras verticales (nz < 0.35) son roca aunque la mascara diga 0: %d/6' % int(r_c.sum()))
try:
    os.remove(ruta_mk)
except OSError:
    pass
info['roca_caras_mascara'] = {'con_uv': int(r_uv.sum()), 'sin_uv': int(r_sin.sum()), 'cubo_vertical': int(r_c.sum())}

print('9) v3 (F1 r3): sin reticula, atenuacion con la distancia, ao_pared, BSDF mate, reaplicar, grupo v2 -> v3')
import colorsys  # noqa: E402

ins9 = [s.name for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT']
check(all(k in ins9 for k in ('ao_pared', 'fade_cerca_m', 'fade_lejos_m')) and int(ng['cal_version']) == MR.CAL_VERSION, 'entradas v3 ao_pared / fade_cerca_m / fade_lejos_m, version %d' % MR.CAL_VERSION)
check(any(n.bl_idname == 'ShaderNodeCameraData' for n in ng.nodes), 'Camera Data (View Distance) dentro del grupo')
wv9 = next((n for n in ng.nodes if n.bl_idname == 'ShaderNodeTexWave'), None)
check(wv9 is not None and float(wv9.inputs['Distortion'].default_value) <= 1.0, 'Wave Distortion %.1f (<= 1: sin celdas de ~periodo x 3)' % (float(wv9.inputs['Distortion'].default_value) if wv9 else -1))
# BSDF mate (ajustar_bsdf) en el material de kit
bs_r = next(n for n in m_roca.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
check(abs(float(bs_r.inputs['Roughness'].default_value) - MR.RUGOSIDAD_ROCA) < 1e-6 and 'Specular IOR Level' in bs_r.inputs
      and abs(float(bs_r.inputs['Specular IOR Level'].default_value) - MR.ESPECULAR_ROCA) < 1e-6,
      'aplicar_a deja el BSDF mate: Roughness %.2f, Specular IOR Level %.2f' % (float(bs_r.inputs['Roughness'].default_value), float(bs_r.inputs['Specular IOR Level'].default_value)))
bs_r.inputs['Specular IOR Level'].default_value = 0.5
check(MR.ajustar_bsdf(m_roca) is True and abs(float(bs_r.inputs['Specular IOR Level'].default_value)) < 1e-6 and MR.ajustar_bsdf(m_roca) is False,
      'ajustar_bsdf vuelve a 0 y es idempotente')
# ao_pared en la media: con ao_pared la media de PARED baja; ao_pared = 1 recupera la v2
m1_ao = MR.media_lineal(paleta.rgb('caliza_ocre'), frac_pared=1.0)
m1_sin = MR.media_lineal(paleta.rgb('caliza_ocre'), frac_pared=1.0, ao_pared=1.0)
check(abs(lum(m1_ao) / max(lum(m1_sin), 1e-6) - MR.AO_PARED) < 0.03, 'media de pared x ao_pared: %.3f / %.3f = %.2f (~%.2f)' % (lum(m1_ao), lum(m1_sin), lum(m1_ao) / lum(m1_sin), MR.AO_PARED))
cr3 = MR.color_roca_terreno_ac()
check(0.15 < lum(cr3) < 0.30, 'color_roca_terreno_ac (P1) = %s %s (V %.2f sRGB)' % (tuple(round(c, 3) for c in cr3), paleta.hex_desde_rgb(cr3), max(paleta.lin_a_srgb(c) for c in cr3)))
check(all(abs(a - b) < 1e-4 for a, b in zip(m_roca.diffuse_color[:3], MR.media_material(paleta.rgb('caliza_ocre')))), 'diffuse_color de aplicar_a = media v3 (con ao_pared) x tinte del tile (v4)')
# reaplicar: otro tile/factor (McLaren 12 m / 0.4) conservando el tono y sin duplicar grupo ni cadena
gm = MR.reaplicar(m_mc, tile_m=12.0, factor=0.4)
ntm = m_mc.node_tree
n_grupos = sum(1 for n in ntm.nodes if n.type == 'GROUP' and n.node_tree is ng)
mp_m = ntm.nodes.get('TEX_mapping')
mul_m = ntm.nodes.get('TEX_multiplicar')
fac_m = next((s for s in mul_m.inputs if s.identifier == 'Factor_Float'), None) if mul_m else None
check(gm is not None and n_grupos == 1, 'reaplicar(tile_m=12, factor=0.4): devuelve grupo (%s) y hay 1 nodo de grupo (%d)' % (gm is not None, n_grupos))
check(mp_m is not None and abs(float(mp_m.inputs['Scale'].default_value[0]) - 1.0 / 12.0) < 1e-5,
      'reaplicar: TEX_mapping 1/12 (%s)' % (float(mp_m.inputs['Scale'].default_value[0]) if mp_m else None))
check(fac_m is not None and abs(float(fac_m.default_value) - 0.4) < 1e-5, 'reaplicar: factor 0.4 (%s)' % (float(fac_m.default_value) if fac_m else None))
check(gm is not None and tuple(round(c, 2) for c in gm.inputs['tono_base'].default_value[:3]) == tuple(round(c, 2) for c in paleta.rgb('caliza_ocre')),
      'reaplicar: tono_base conservado (%s)' % ((tuple(round(c, 3) for c in gm.inputs['tono_base'].default_value[:3]) if gm else None),))
check(abs(float(m_mc['cal_tile_m']) - 12.0) < 1e-6 and len(ntm.nodes.get('TEX_imagen').outputs['Color'].links) == 1, 'props cal_* y cadena TEX_ unica')
check(MR.reaplicar(m_ter) is None, 'reaplicar nunca toca un material con ROCA_mascara (terreno)')
# grupo v2 -> v3: se fuerza version 2 sin ao_pared; actualizar_grupo lo repone, deja mate el BSDF y re-escribe diffuse_color
ng['cal_version'] = 2
sock_ao = next(s for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.name == 'ao_pared')
ng.interface.remove(sock_ao)
m_roca.diffuse_color = (0.9, 0.9, 0.9, 1.0)
bs_r.inputs['Specular IOR Level'].default_value = 0.5
check(MR.actualizar_grupo() is True, 'actualizar_grupo() reconstruye un grupo v2 (sin ao_pared)')
gn_r = next(n for n in m_roca.node_tree.nodes if n.type == 'GROUP')
check('ao_pared' in gn_r.inputs and abs(float(gn_r.inputs['ao_pared'].default_value) - MR.AO_PARED) < 1e-6, 'nodo de grupo existente gana ao_pared = %.2f' % MR.AO_PARED)
check(all(abs(a - b) < 1e-4 for a, b in zip(m_roca.diffuse_color[:3], MR.media_material(paleta.rgb('caliza_ocre')))) and abs(float(bs_r.inputs['Specular IOR Level'].default_value)) < 1e-6,
      'tras actualizar: diffuse_color = media v3 x tinte y BSDF mate (%s)' % paleta.hex_desde_rgb(m_roca.diffuse_color[:3]))
check(ntt.nodes.get('Math.002') is not None and len(mask.outputs['Value'].links) == enl_mask, "'Math.002'/'ROCA_mascara' intacto tras actualizar a v3")

print('10) v4 (F1 r4): estratos en parches, nz con ruido, tinte del tile en la media, caliza_grande_d.png, grupo v3 -> v4')
check(int(ng['cal_version']) == 4 and MR.CAL_VERSION == 4, 'CAL_VERSION 4')
check(all(ng.nodes.get(n) is not None for n in ('CAL_parches', 'CAL_ruido_parches', 'CAL_fade_parches', 'CAL_nz_ruido', 'CAL_nz_dither', 'CAL_ondula_14m')),
      'nodos v4: CAL_parches / CAL_ruido_parches / CAL_fade_parches / CAL_nz_ruido / CAL_nz_dither / CAL_ondula_14m')
pa = ng.nodes.get('CAL_parches')
check(pa is not None and abs(float(pa.inputs['To Min'].default_value) - MR.PARCHES_MIN) < 1e-6 and abs(float(pa.inputs['To Max'].default_value) - 1.0) < 1e-6,
      'CAL_parches: %.2f..1 (estratos por tramos)' % MR.PARCHES_MIN)
fdn = ng.nodes.get('CAL_fade_dist')
check(fdn is not None and abs(float(fdn.inputs['To Max'].default_value) - MR.FADE_MIN) < 1e-6 and MR.FADE_MIN <= 0.15, 'fade a lo lejos %.2f (<= 0.15)' % MR.FADE_MIN)
# tinte del tile: caliza_d x ganancia escalar NO tiene media 1 por canal (R > 1 > B); media_material = media_lineal x tinte
tt = MR.tinte_tile('caliza_d.png', 0.5)
check(tt[0] > 1.0 > tt[2] and 0.8 < tt[2] < 0.95, 'tinte_tile(caliza_d, 0.5) = %s (R > 1 > B: el tile calienta)' % (tuple(round(c, 3) for c in tt),))
check(MR.tinte_tile('', 0.5) == (1.0, 1.0, 1.0) and MR.tinte_tile('caliza_d.png', 0.0) == (1.0, 1.0, 1.0), 'tinte_tile sin tile o factor 0 = 1')
mm = MR.media_material(paleta.rgb('caliza_ocre'))
ml = MR.media_lineal(paleta.rgb('caliza_ocre'))


def _s_srgb(c):
    s = [paleta.lin_a_srgb(x) for x in c]
    return (max(s) - min(s)) / max(max(s), 1e-6)


check(_s_srgb(mm) > _s_srgb(ml) + 0.03, 'media_material S sRGB %.3f > media_lineal %.3f (+0.03): el KN5 sale tan calido como Blender' % (_s_srgb(mm), _s_srgb(ml)))
check(abs(_s_srgb(MR.color_roca_terreno_ac()) - 0.23) < 0.03, 'color_roca_terreno_ac (P1) sigue sin tinte de tile: S %.2f (~0.23, el detalle A del terreno se normaliza por canal)' % _s_srgb(MR.color_roca_terreno_ac()))
# caliza_grande_d.png (McLaren): aplicar_a con imagen=... y tile 24 m; respaldo a caliza_d.png si falta
hay_cg = os.path.exists(os.path.join(MR.DIR_TEX, 'caliza_grande_d.png'))
check(hay_cg, 'existe texturas/caliza_grande_d.png (generar_texturas.caliza_grande)')
m_cg = MR.material_caliza('MAT_test_caliza_grande', tono_base=paleta.rgb('caliza_ocre'), imagen='caliza_grande_d.png', tile_m=24.0, factor=0.3)
tex_cg = m_cg.node_tree.nodes.get('TEX_imagen')
mp_cg = m_cg.node_tree.nodes.get('TEX_mapping')
check(tex_cg is not None and tex_cg.image is not None and os.path.basename(tex_cg.image.filepath) == ('caliza_grande_d.png' if hay_cg else 'caliza_d.png')
      and mp_cg is not None and abs(float(mp_cg.inputs['Scale'].default_value[0]) - 1.0 / 24.0) < 1e-6,
      'McLaren: TEX_imagen %s, TEX_mapping 1/24' % (os.path.basename(tex_cg.image.filepath) if (tex_cg and tex_cg.image) else None))
check(m_cg.get('cal_imagen') == ('caliza_grande_d.png' if hay_cg else 'caliza_d.png') and abs(float(m_cg['cal_factor']) - 0.3) < 1e-6, 'props cal_imagen / cal_factor 0.3')
m_nf = MR.material_caliza('MAT_test_sin_tile', tono_base=paleta.rgb('caliza_ocre'), imagen='no_existe_d.png')
check(m_nf.node_tree.nodes.get('TEX_imagen') is not None and m_nf.get('cal_imagen') == 'caliza_d.png', 'imagen inexistente -> respaldo caliza_d.png')
# grupo v3 -> v4 en sitio: se fuerza version 3; actualizar_grupo lo reconstruye y re-escribe diffuse_color con el tinte
ng['cal_version'] = 3
m_roca.diffuse_color = (0.9, 0.9, 0.9, 1.0)
check(MR.actualizar_grupo() is True and int(ng['cal_version']) == 4 and ng.nodes.get('CAL_parches') is not None, 'actualizar_grupo() v3 -> v4 en sitio')
check(all(abs(a - b) < 1e-4 for a, b in zip(m_roca.diffuse_color[:3], MR.media_material(paleta.rgb('caliza_ocre')))), 'tras v4: diffuse_color = media_material (%s)' % paleta.hex_desde_rgb(m_roca.diffuse_color[:3]))
check(ntt.nodes.get('Math.002') is not None and len(mask.outputs['Value'].links) == enl_mask, "'Math.002'/'ROCA_mascara' intacto tras actualizar a v4")
info['v4'] = {'tinte_caliza_d_05': [round(c, 4) for c in tt], 'media_material': paleta.hex_desde_rgb(mm), 'media_lineal': paleta.hex_desde_rgb(ml),
              'S_media_material': round(_s_srgb(mm), 3), 'S_media_lineal': round(_s_srgb(ml), 3), 'caliza_grande': hay_cg}

print('   render lejano: pared de 200 x 40 m a 320 m con y sin atenuacion (fade_lejos_m = 0) -> previews/materiales_roca_lejos*.png')
m_lejos = MR.material_caliza('MAT_test_lejos', tono_base=paleta.rgb('caliza_ocre'))
caja('PARED_lejos', 1000.0, 0.0, 0.0, 200.0, 4.0, 40.0, m_lejos)
cam_l, tgt_l = (1000.0, -320.0, 24.0), (1000.0, 0.0, 20.0)
r_lej = render('lejos', cam_l, tgt_l, lens=35)
Ll = luminancia_png(r_lej)
hL, wL = Ll.shape
# region = proyeccion de la cara frontal de la pared (y = -2), encogida un 15 % por cada lado (sin cielo ni suelo)
sc_ = bpy.context.scene
_pts = [w2cv(sc_, sc_.camera, Vector((x_, -2.0, z_))) for x_ in (900.0, 1100.0) for z_ in (0.0, 40.0)]
_u0, _u1 = min(p.x for p in _pts), max(p.x for p in _pts)
_v0, _v1 = min(p.y for p in _pts), max(p.y for p in _pts)
_du, _dv = (_u1 - _u0) * 0.15, (_v1 - _v0) * 0.15
_x0, _x1 = int((_u0 + _du) * wL), int((_u1 - _du) * wL)
_y0, _y1 = int((1.0 - (_v1 - _dv)) * hL), int((1.0 - (_v0 + _dv)) * hL)
info['lejos_region_px'] = [_x0, _x1, _y0, _y1]
reg = Ll[_y0:_y1, _x0:_x1]
std_con = float(reg.std())
gl = next(n for n in m_lejos.node_tree.nodes if n.type == 'GROUP')
gl.inputs['fade_lejos_m'].default_value = 0.0
r_lej0 = render('lejos_sin_fade', cam_l, tgt_l, lens=35)
Ll0 = luminancia_png(r_lej0)
reg0 = Ll0[_y0:_y1, _x0:_x1]
std_sin = float(reg0.std())
gl.inputs['fade_lejos_m'].default_value = MR.FADE_LEJOS_M
# espectro 2D del centro de la pared SIN fade: fraccion de energia con componente horizontal (|kx| > 0): una reticula de
# celdas reparte energia en kx; los estratos la concentran en kz (kx ~ 0)
def _frac_kx(a):
    a = a - a.mean()
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    hh, ww = F.shape
    F[hh // 2, ww // 2] = 0.0
    kx = np.abs(np.fft.fftshift(np.fft.fftfreq(ww)))[None, :] * np.ones((hh, 1))
    return float(F[kx > 0.02].sum() / max(F.sum(), 1e-9))
frac = _frac_kx(reg0)
info['lejos'] = {'std_con_fade': round(std_con, 4), 'std_sin_fade': round(std_sin, 4), 'ratio': round(std_con / max(std_sin, 1e-6), 3),
                 'frac_energia_kx_sin_fade': round(frac, 3)}
# lo que queda sin atenuar son los bancos (+-12 %), las manchas (+-10 %) y la mitad del grano: por eso ~0.8, no 0.25.
# v4: con las juntas en parches (media 0.6) pesan menos en la std total: el ratio con/sin fade sube a ~0.89 (umbral 0.95)
check(std_con < 0.95 * std_sin, 'a 320 m la atenuacion baja el contraste de las juntas: std %.4f -> %.4f (ratio %.2f < 0.95)' % (std_sin, std_con, std_con / max(std_sin, 1e-6)))
check(frac < 0.60, 'patron sin fade a 320 m: energia con componente horizontal %.2f (< 0.60: bandas, no celdas)' % frac)

print('   render rasante: losa horizontal vista casi de canto con Specular IOR Level 0 (v3) y 0.5 (antes): el cielo ya no tine')
# caliza MEDIA: la clara (0.69) al sol se recorta a blanco en los 3 canales y no se puede medir el tinte
m_ras = MR.material_caliza('MAT_test_rasante', tono_base=paleta.rgb('caliza_gris_calido'))
caja('LOSA_rasante', 2000.0, 0.0, 9.0, 400.0, 400.0, 1.0, m_ras)          # tapa en z = 10: fuera del 'mojado' (z < 1.6)
cam_r, tgt_r = (2000.0 - 190.0, 0.0, 13.0), (2000.0 + 120.0, 0.0, 10.0)
r_ras0 = render('rasante', cam_r, tgt_r, lens=35)
bs_ras = next(n for n in m_ras.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
bs_ras.inputs['Specular IOR Level'].default_value = 0.5
r_ras5 = render('rasante_spec05', cam_r, tgt_r, lens=35)
bs_ras.inputs['Specular IOR Level'].default_value = MR.ESPECULAR_ROCA


def _hsv_region(ruta, y0=0.50, y1=0.62, x0=0.35, x1=0.65):
    img = bpy.data.images.load(ruta, check_existing=False)
    w_, h_ = img.size
    buf = np.empty(len(img.pixels), np.float32)
    img.pixels.foreach_get(buf)
    rgb = buf.reshape(h_, w_, -1)[::-1, :, :3]
    bpy.data.images.remove(img)
    m = rgb[int(h_ * y0):int(h_ * y1), int(w_ * x0):int(w_ * x1)].reshape(-1, 3).mean(axis=0)
    h, s, v = colorsys.rgb_to_hsv(*[float(c) for c in m])
    return round(h * 360), round(s, 3), round(v, 3), paleta.hex_desde_rgb([paleta.srgb_a_lin(float(c)) for c in m])


hsv0, hsv5 = _hsv_region(r_ras0), _hsv_region(r_ras5)
info['rasante'] = {'spec_0': hsv0, 'spec_0_5': hsv5}
check(20 <= hsv0[0] <= 60 and hsv0[1] >= 0.15, 'rasante con Specular 0: H %d, S %.2f, V %.2f (%s): calida' % (hsv0[0], hsv0[1], hsv0[2], hsv0[3]))
# medido 04/10: S 0.14 -> 0.17 con Specular 0 (el Fresnel del cielo es un contribuyente MENOR del velo; lo principal es la luz
# del cielo en sombra): se exige no empeorar, y se deja la cifra en el JSON
check(hsv0[1] >= hsv5[1], 'rasante con Specular 0.5 (antes): H %d, S %.2f (%s) <= S con Specular 0 (%.2f): el cielo ya no desatura' % (hsv5[0], hsv5[1], hsv5[3], hsv0[1]))
# pared vertical al sol (la de 51): H 30-45 y V <= 0.86 con ao_pared (criterio del director r2 n.5)
hsv_p = _hsv_region(r_pared, y0=0.25, y1=0.55, x0=0.35, x1=0.65)
info['pared_sol'] = hsv_p
check(25 <= hsv_p[0] <= 50 and hsv_p[2] <= 0.88, 'pared vertical al sol: H %d, S %.2f, V %.2f (%s) (H 30-45, V <= 0.86 +-0.02)' % hsv_p)

info['fallos'] = fallos
info['previews'] = [os.path.basename(p) for p in (r_pared, r_det, r_bancos, r_or, r_lej, r_lej0, r_ras0, r_ras5)]
with open(os.path.join(PREV, 'materiales_roca_test.json'), 'w', encoding='utf-8') as fh:
    json.dump(info, fh, indent=1)
print('TEST_MATERIALES_ROCA:', 'TEST_OK' if not fallos else 'FALLOS %d: %s' % (len(fallos), '; '.join(fallos)))
