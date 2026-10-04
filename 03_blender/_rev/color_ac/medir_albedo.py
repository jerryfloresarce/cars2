# -*- coding: utf-8 -*-
"""medir_albedo.py - mide el ALBEDO MEDIO REAL de los materiales procedurales de la escena congelada
(Base Color enlazado a rampas/ruidos: kn5_writer_opt.analizar_material() solo ve su diffuse_color, que en
algunos, p. ej. MAT_terreno, es mucho mas palido que lo que se ve en el render).

Metodo (copia en memoria, NUNCA se guarda): para cada material con algun Principled cuyo Base Color esta
enlazado, una COPIA del material sustituye cada Principled por un Emission con el mismo color (se conserva
la estructura de MixShader); se aplica a una rejilla horizontal de 300x300 m a la altura Z y se renderiza
desde arriba (ortografica, 48x48, vista Standard, mundo negro) a EXR; la media lineal del EXR = albedo.
  bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/color_ac/medir_albedo.py
Salida: 03_blender/_rev/color_ac/albedo_medido.json  {material: {"z": [r,g,b], ...}, "_usar": {material: [r,g,b]}}
"""
import json
import os

import bpy
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.environ.get('ESCENA') or os.path.join(AQUI, 'escena_color.blend'))   # copia congelada (v3)
sc = bpy.context.scene
ALTURAS = {'MAT_terreno': (2.0, 8.0, 20.0, 45.0, 90.0)}     # rampa por altura: se mide a varias cotas
Z_DEF = 20.0
Z_USAR = {'MAT_terreno': 20.0}                                 # cota tipica de la hierba junto a la pista

usados = set()
for ob in bpy.context.view_layer.objects:
    if ob.type == 'MESH' and not ob.hide_render:
        for m in ob.data.materials:
            if m is not None:
                usados.add(m.name)


def principled_enlazados(m):
    if not m.node_tree:
        return []
    return [n for n in m.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'
            and n.inputs['Base Color'].is_linked]


def copia_emision(m):
    mc = m.copy()
    nt = mc.node_tree
    for n in [n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled']:
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Strength'].default_value = 1.0
        bc = n.inputs['Base Color']
        if bc.is_linked:
            nt.links.new(bc.links[0].from_socket, em.inputs['Color'])
        else:
            em.inputs['Color'].default_value = bc.default_value
        for l in list(n.outputs['BSDF'].links):
            nt.links.new(em.outputs['Emission'], l.to_socket)
        nt.nodes.remove(n)
    return mc


# escena de medida: se ocultan todos los objetos, mundo negro, EEVEE, vista Standard
for ob in bpy.data.objects:
    ob.hide_render = True
sc.world = bpy.data.worlds.new('NEGRO')
sc.world.use_nodes = True
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
sc.render.engine = 'BLENDER_EEVEE'
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.0
sc.view_settings.gamma = 1.0
sc.render.resolution_x = sc.render.resolution_y = 48
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'OPEN_EXR'
sc.render.image_settings.color_depth = '32'
try:
    sc.eevee.use_raytracing = False
except Exception:  # noqa
    pass
bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=60, size=300.0, location=(1234.0, -987.0, 0.0))
plano = bpy.context.active_object
plano.hide_render = False
cd = bpy.data.cameras.new('MEDIDA')
cd.type = 'ORTHO'
cd.ortho_scale = 280.0
cd.clip_end = 5000.0
cam = bpy.data.objects.new('MEDIDA', cd)
sc.collection.objects.link(cam)
sc.camera = cam
tmp = os.path.join(AQUI, '_tmp_albedo.exr')


def medir(mc, z):
    plano.location.z = z
    cam.location = (plano.location.x, plano.location.y, z + 400.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    plano.data.materials.clear()
    plano.data.materials.append(mc)
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(tmp, check_existing=False)
    px = np.empty(len(img.pixels), np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return [float(v) for v in px.reshape(-1, 4)[:, :3].mean(0)]


res = {'_usar': {}, '_diffuse_color': {}}
for nm in sorted(usados):
    m = bpy.data.materials.get(nm)
    if m is None or not principled_enlazados(m):
        continue
    mc = copia_emision(m)
    por_z = {}
    for z in ALTURAS.get(nm, (Z_DEF,)):
        por_z['%.0f' % z] = medir(mc, z)
    res[nm] = por_z
    res['_usar'][nm] = por_z['%.0f' % Z_USAR.get(nm, Z_DEF)]
    res['_diffuse_color'][nm] = [float(c) for c in m.diffuse_color[:3]]
    print('ALBEDO %-34s diffuse %s -> medido %s' % (nm, tuple(round(c, 3) for c in m.diffuse_color[:3]),
                                                   {k: tuple(round(c, 3) for c in v) for k, v in por_z.items()}))
if os.path.exists(tmp):
    os.remove(tmp)
json.dump(res, open(os.path.join(AQUI, 'albedo_medido.json'), 'w', encoding='utf-8'), indent=1)
# tabla que lee 04_export/color_ac.py (albedo + diffuse_color con el que se midio, para detectar cambios)
tabla = {'nota': 'albedo lineal medio REAL de los materiales procedurales de 03_blender/_rev/escena_rev.blend (media '
                 'de su arbol de nodos en una rejilla horizontal a z=20 m, medir_albedo.py) y el diffuse_color con el '
                 'que se midio (si cambia, color_ac ignora la medida)',
         'albedo': {k: [round(c, 4) for c in v] for k, v in res['_usar'].items()},
         'diffuse_color': {k: [round(c, 4) for c in v] for k, v in res['_diffuse_color'].items()}}
json.dump(tabla, open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(AQUI))), '04_export',
                                   'color_ac_albedo.json'), 'w', encoding='utf-8'), indent=0)
print('OK albedo medido de %d materiales procedurales (+ 04_export/color_ac_albedo.json)' % len(res['_usar']))
