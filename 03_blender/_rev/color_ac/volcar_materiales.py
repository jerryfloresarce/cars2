# -*- coding: utf-8 -*-
"""volcar_materiales.py - vuelca los materiales de la escena CONGELADA (03_blender/_rev/escena_rev.blend,
solo lectura, NUNCA se guarda) tal y como los ve kn5_writer_opt.analizar_material(): color base lineal,
alpha, imagen de color, factor de la mezcla, media lineal de la imagen, numero de objetos/caras que lo usan
y prefijos de los objetos. Tambien la iluminacion del render (sol, mundo, vista, exposicion, motor).

  bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/color_ac/volcar_materiales.py
Salida: 03_blender/_rev/color_ac/materiales.json
"""
import json
import os
from collections import Counter, defaultdict

import bpy
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
REV = os.path.dirname(AQUI)
bpy.ops.wm.open_mainfile(filepath=os.environ.get('ESCENA') or os.path.join(AQUI, 'escena_color.blend'))   # copia congelada (v3)
sc = bpy.context.scene


import sys
sys.path.insert(0, AQUI)
from analisis_mat import analizar  # noqa: E402


usos = defaultdict(lambda: {'objetos': 0, 'caras': 0, 'prefijos': Counter()})
for ob in bpy.context.view_layer.objects:
    if ob.type != 'MESH' or ob.hide_render or ob.hide_viewport:
        continue
    try:
        if not ob.visible_get():
            continue
    except Exception:  # noqa
        pass
    me = ob.data
    nmat = len(me.materials)
    if nmat == 0:
        continue
    idx = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('material_index', idx)
    cnt = np.bincount(np.clip(idx, 0, nmat - 1), minlength=nmat)
    pref = ob.name.split('_')[0] if '_' in ob.name else ob.name.split('.')[0]
    for i, m in enumerate(me.materials):
        if m is None or cnt[i] == 0:
            continue
        u = usos[m.name]
        u['objetos'] += 1
        u['caras'] += int(cnt[i])
        u['prefijos'][pref] += 1

mats = []
for name, u in usos.items():
    m = bpy.data.materials.get(name)
    if m is None:
        continue
    info = analizar(m)
    info['objetos'] = u['objetos']
    info['caras'] = u['caras']
    info['prefijos'] = dict(u['prefijos'].most_common(6))
    mats.append(info)
mats.sort(key=lambda i: -i['caras'])

luz = {'motor': sc.render.engine, 'vista': sc.view_settings.view_transform, 'look': sc.view_settings.look,
       'exposicion': sc.view_settings.exposure, 'gamma': sc.view_settings.gamma, 'soles': []}
for ob in bpy.data.objects:
    if ob.type == 'LIGHT':
        d = ob.data
        luz['soles'].append({'nombre': ob.name, 'tipo': d.type, 'energia': d.energy, 'color': list(d.color),
                             'angulo': getattr(d, 'angle', None), 'rot': list(ob.rotation_euler),
                             'dir': list((ob.matrix_world.to_3x3() @ __import__('mathutils').Vector((0, 0, -1)))),
                             'sombras': getattr(d, 'use_shadow', None)})
w = sc.world
if w and w.node_tree:
    for n in w.node_tree.nodes:
        if n.bl_idname == 'ShaderNodeBackground':
            luz['mundo'] = {'color': list(n.inputs['Color'].default_value)[:3],
                            'fuerza': float(n.inputs['Strength'].default_value),
                            'color_enlazado': n.inputs['Color'].is_linked}
        if n.bl_idname == 'ShaderNodeTexSky':
            luz['cielo'] = {'tipo': n.sky_type}
try:
    ee = sc.eevee
    luz['eevee'] = {k: getattr(ee, k) for k in ('use_gtao', 'gtao_distance', 'use_shadows', 'use_raytracing',
                                                'fast_gi_method') if hasattr(ee, k)}
except Exception:  # noqa
    pass
json.dump({'luz': luz, 'materiales': mats}, open(os.path.join(AQUI, 'materiales.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False, default=str)
print('OK materiales:', len(mats), 'luz:', json.dumps(luz, default=str)[:800])
