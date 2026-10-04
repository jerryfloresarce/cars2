# -*- coding: utf-8 -*-
"""carta_color.py - CARTA DE COLOR de la paleta (bpy, SOLO por la cola de Blender):

    bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/carta_color.py [-- salida.png [ancho alto]]

Escena minima desde cero (no abre ninguna escena del proyecto, no guarda nada): 12 esferas rotuladas con los 12 colores de
03_blender/paleta.json (Base Color = rgb lineal, que es lo que lee el writer) + 10 cubos de fachada (5 tonos ACTUALES de
casas_kit_v2.PALETA_FACHADA y 5 PROPUESTOS), con la MISMA luz y transformacion de vista que las capturas del circuito
(construir_pista.py l.1566-1618 / renderizar_capturas.py: sol 4.6 W (1, 0.96, 0.88) a 34 grados y azimut -140, cielo en
gradiente, view_transform Standard, exposicion 0.12, GTAO 12 m, EEVEE). Salida por defecto:
03_blender/renders/qa/carta_color.png (1600 x 900). El usuario valida la paleta con esta imagen (plan, pregunta 15).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
sys.path.insert(0, os.path.join(BASE, '03_blender'))
import paleta  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SALIDA = args[0] if args else os.path.join(BASE, '03_blender', 'renders', 'qa', 'carta_color.png')
RES = (int(args[1]), int(args[2])) if len(args) >= 3 else (1600, 900)

sc = bpy.context.scene
for ob in list(bpy.data.objects):                   # factory startup: cubo (en la coleccion hija), luz y camara fuera
    bpy.data.objects.remove(ob, do_unlink=True)
col = sc.collection


def mat_plano(nombre, rgb, rough=0.75):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = tuple(rgb) + (1.0,)
    bsdf.inputs['Roughness'].default_value = rough
    m.diffuse_color = tuple(rgb) + (1.0,)          # regla del plan: diffuse_color = media lineal deseada
    return m


def esfera(nombre, loc, r, m):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=48, ring_count=24)
    ob = bpy.context.object
    ob.name = nombre
    ob.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return ob


def cubo(nombre, loc, lado, m):
    bpy.ops.mesh.primitive_cube_add(size=lado, location=loc)
    ob = bpy.context.object
    ob.name = nombre
    ob.data.materials.append(m)
    return ob


def texto(nombre, s, loc, tam, m, rot_x=math.radians(90)):
    cu = bpy.data.curves.new(nombre, 'FONT')
    cu.body = s
    cu.size = tam
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new(nombre, cu)
    ob.location = loc
    ob.rotation_euler = (rot_x, 0, 0)
    ob.data.materials.append(m)
    col.objects.link(ob)
    return ob


M_SUELO = mat_plano('CARTA_suelo', (0.18, 0.18, 0.18), 0.9)
M_TEXTO = mat_plano('CARTA_texto', (0.02, 0.02, 0.02), 0.6)
M_BLANCO = mat_plano('CARTA_texto_blanco', (0.9, 0.9, 0.9), 0.6)
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
bpy.context.object.data.materials.append(M_SUELO)
bpy.context.object.name = 'CARTA_suelo'

# -- filas: 2 x 6 esferas de la paleta, 1 x 5 fachadas actuales, 1 x 5 fachadas propuesta
PASO = 2.0
R = 0.5
FILA = 2.7
nombres = paleta.nombres()
filas = [('PALETA 1/2', nombres[:6]), ('PALETA 2/2', nombres[6:])]
P = paleta.cargar()
act = [k for k in P['fachadas_actual'] if not k.startswith('_')]
pro = [k for k in P['fachadas_propuesta'] if not k.startswith('_')]
filas.append(('FACHADAS HOY (casas_kit_v2)', ['fachada_actual_' + k for k in act]))
filas.append(('FACHADAS PROPUESTA', ['fachada_' + k for k in pro]))
y0 = 1.5 * FILA
for fi, (titulo, lista) in enumerate(filas):
    y = y0 - fi * FILA
    n = len(lista)
    x_ini = -(6 - 1) * PASO / 2                      # las 4 filas alineadas a la izquierda (6 columnas como maximo)
    texto('CARTA_titulo_%d' % fi, titulo, (x_ini - 0.85, y - 0.35, 0.02), 0.2, M_BLANCO, rot_x=math.radians(50))
    bpy.data.objects['CARTA_titulo_%d' % fi].data.align_x = 'RIGHT'     # a la izquierda de la fila, sin tapar nada
    for i, nombre in enumerate(lista):
        x = x_ini + i * PASO
        rgb = paleta.rgb(nombre)
        m = mat_plano('CARTA_' + nombre, rgb)
        if nombre.startswith('fachada_'):
            cubo('C_' + nombre, (x, y, R * 0.9), 2 * R * 0.9, m)
        else:
            esfera('E_' + nombre, (x, y, R), R, m)
        etiqueta = nombre.replace('fachada_actual_', '').replace('fachada_', '')
        texto('CARTA_t_%s' % nombre, etiqueta, (x, y - 0.85, 0.02), 0.19, M_TEXTO, rot_x=math.radians(50))
        texto('CARTA_h_%s' % nombre, paleta.srgb_hex(nombre), (x, y - 1.15, 0.02), 0.16, M_TEXTO, rot_x=math.radians(50))
texto('CARTA_cab', 'Porto Corsa - carta de color paleta.json v%s (Base Color = rgb lineal; sol, cielo y vista de renderizar_capturas)'
      % P['version'], (0, y0 + 1.75, 0.02), 0.26, M_BLANCO, rot_x=math.radians(50))

# -- sol calido de tarde (construir_pista.py l.1566-1583)
sun_data = bpy.data.lights.new('SOL', 'SUN')
sun_data.energy = 4.6
sun_data.color = (1.0, 0.96, 0.88)
sun_data.angle = math.radians(3.0)
sun = bpy.data.objects.new('SOL', sun_data)
sun.rotation_euler = (math.radians(34), 0, math.radians(-140))
col.objects.link(sun)
for _attr, _val in (('shadow_maximum_resolution', 0.005), ('shadow_filter_radius', 1.5)):
    try:
        setattr(sun_data, _attr, _val)
    except Exception:
        pass

# -- cielo en gradiente estilo Cars 2 (construir_pista.py l.1585-1606)
world = bpy.data.worlds.new('CIELO')
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes.get('Background')
tco = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
mapr = nt.nodes.new('ShaderNodeMapRange')
mapr.inputs['From Min'].default_value = -0.05
mapr.inputs['From Max'].default_value = 0.9
rampc = nt.nodes.new('ShaderNodeValToRGB')
ec = rampc.color_ramp.elements
ec[0].position = 0.0; ec[0].color = (0.70, 0.84, 0.98, 1)
ec[1].position = 1.0; ec[1].color = (0.12, 0.34, 0.86, 1)
em = rampc.color_ramp.elements.new(0.3)
em.color = (0.36, 0.60, 0.95, 1)
nt.links.new(tco.outputs['Generated'], sep.inputs['Vector'])
nt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
nt.links.new(mapr.outputs['Result'], rampc.inputs['Fac'])
nt.links.new(rampc.outputs['Color'], bg.inputs['Color'])
bg.inputs[1].default_value = 1.0
sc.world = world

# -- vista y render (construir_pista.py l.1609-1618 y 1650-1652)
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.12
for attr, val in [('use_gtao', True), ('gtao_distance', 12.0), ('use_shadows', True), ('taa_render_samples', 48)]:
    try:
        setattr(sc.eevee, attr, val)
    except Exception:
        pass
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.film_transparent = False

cd = bpy.data.cameras.new('CAM')
cd.lens = 40
cam = bpy.data.objects.new('CAM', cd)
cam.location = Vector((0.0, -13.5, 13.0))
tgt = Vector((0.0, 0.3, 0.0))
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
col.objects.link(cam)
sc.camera = cam

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
sc.render.filepath = SALIDA
bpy.ops.render.render(write_still=True)
print('OK carta de color -> %s (%dx%d, engine %s, %d esferas + %d cubos)' % (
    SALIDA, RES[0], RES[1], sc.render.engine, len(nombres), len(act) + len(pro)))
