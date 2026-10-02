# Renderiza las 6 camaras de la escena final (tras el pase de materiales).
import os

import bpy

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
sc = bpy.context.scene
OUT = BASE + r'\03_blender\renders'
for cam_name, fname in [('vista_aerea', 'full_aerea'), ('meta_puerto', 'full_meta'),
                        ('puerto_panoramica', 'full_puerto'), ('casino_cerca', 'full_casino'),
                        ('cima_tierra', 'full_cima'), ('bahia_casino', 'full_bahia')]:
    cam = bpy.data.objects.get(cam_name)
    if not cam:
        print('sin camara', cam_name)
        continue
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT, fname + '.png')
    bpy.ops.render.render(write_still=True)
    print('render:', fname)
print('OK stills')
