# -*- coding: utf-8 -*-
"""inspeccionar_nodos.py - imprime el arbol de nodos de unos materiales y del mundo de la escena congelada
(solo lectura). bash 03_blender/_rev/blender_cola.sh --python .../inspeccionar_nodos.py -- MAT_a MAT_b ..."""
import os
import sys

import bpy

AQUI = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(AQUI), 'escena_rev.blend'))
nombres = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def volcar(nt, titulo):
    print('=====', titulo)
    for n in nt.nodes:
        vals = []
        for s in n.inputs:
            if s.is_linked:
                l = s.links[0]
                vals.append('%s<-%s.%s' % (s.name, l.from_node.name, l.from_socket.name))
            elif hasattr(s, 'default_value'):
                try:
                    v = s.default_value
                    v = tuple(round(x, 3) for x in v) if hasattr(v, '__len__') else round(v, 3)
                except Exception:  # noqa
                    v = '?'
                if s.name in ('Base Color', 'Color', 'Color1', 'Color2', 'A', 'B', 'Factor', 'Fac', 'Strength',
                              'Roughness', 'Scale', 'Value'):
                    vals.append('%s=%s' % (s.name, v))
        extra = ''
        if n.bl_idname == 'ShaderNodeTexImage' and n.image:
            extra = ' img=%s cs=%s' % (n.image.name, n.image.colorspace_settings.name)
        if n.bl_idname == 'ShaderNodeValToRGB':
            extra = ' ramp=' + str([(round(e.position, 2), tuple(round(c, 3) for c in e.color[:3]))
                                   for e in n.color_ramp.elements])
        if n.bl_idname == 'ShaderNodeAttribute':
            extra = ' attr=%s' % n.attribute_name
        if n.bl_idname == 'ShaderNodeMix':
            extra = ' blend=%s type=%s' % (n.blend_type, n.data_type)
        print('  %-28s %-26s %s%s' % (n.name[:28], n.bl_idname[10:36], '; '.join(vals), extra))


for nm in nombres:
    m = bpy.data.materials.get(nm)
    if m and m.node_tree:
        print('diffuse_color', tuple(round(c, 3) for c in m.diffuse_color))
        volcar(m.node_tree, nm)
w = bpy.context.scene.world
if w and w.node_tree:
    volcar(w.node_tree, 'MUNDO ' + w.name)
ee = bpy.context.scene.eevee
for k in dir(ee):
    if not k.startswith('_') and any(t in k for t in ('ao', 'gtao', 'shadow', 'ray', 'gi', 'light', 'horizon')):
        try:
            print('eevee.%s = %s' % (k, getattr(ee, k)))
        except Exception:  # noqa
            pass
print('OK nodos')
