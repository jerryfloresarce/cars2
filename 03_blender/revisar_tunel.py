# QA del tunel: lanza 9 rayos (3 laterales x 3 alturas) por tramos de 4 m a lo largo
# de la galeria y 40 m mas alla de cada boca. Si alguno choca con la roca, el tunel
# esta tapado (paso dos veces: booleano fallido y 'cortinas' al deformar la falda).
# Ejecutar SIEMPRE tras integrar_escena.py:
#   blender --background --factory-startup --python revisar_tunel.py
import json
import os
import bpy
from mathutils import Vector
BASE = 'E:/Escritorio/claude-pc/arnau-aseto-corsa'
G = json.load(open(os.environ.get('GEOM', BASE + '/03_blender/geometria_3d.json'), encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=BASE + '/03_blender/porto_corsa.blend')
S = G['muestras']; N = G['n']; paso = G['paso_m']
ob = bpy.data.objects['TUNEL_acantilado']
roca = max((o for o in [ob] + list(ob.children_recursive) if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
inv = roca.matrix_world.inverted()
i_in = int(float(ob['s_in']) / paso); i_out = int(float(ob['s_out']) / paso)
print('RAYOS galeria %d..%d' % (i_in * paso, i_out * paso))
TOTAL = []
for lat in (-5.0, 0.0, 5.0):
    for h in (1.5, 4.0, 6.5):
        bloqueos = []
        for i in range(i_in - 20, i_out + 20, 2):
            q0 = S[i % N]; q1 = S[(i + 2) % N]
            a = inv @ Vector((q0['x'] + q0['nx'] * lat, q0['y'] + q0['ny'] * lat, q0['z'] + h))
            b = inv @ Vector((q1['x'] + q1['nx'] * lat, q1['y'] + q1['ny'] * lat, q1['z'] + h))
            d = b - a
            if roca.ray_cast(a, d.normalized(), distance=d.length)[0]:
                bloqueos.append(i * paso)
        print('RAYOS lat=%+.0f h=%.1f bloqueado en s=%s' % (lat, h, bloqueos))
        TOTAL.extend(bloqueos)
print('TUNEL ABIERTO' if not TOTAL else 'TUNEL BLOQUEADO en s=%s' % sorted(set(TOTAL)))
