# Capturas de RECORRIDO: camara de persecucion a pie de pista cada ~200 m,
# como lo vera el piloto (y el video). Sirven para cazar bugs de cerca:
# objetos flotando/enterrados, cosas en la calzada, huecos entre pista y
# terreno... Guarda renders/recorrido/RNN_sXXXX.png
import json
import os

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
sc = bpy.context.scene
OUT = BASE + r'\03_blender\renders\recorrido'
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith('.png'):
        os.remove(os.path.join(OUT, f))
S = G['muestras']; N = G['n']; paso = G['paso_m']; L = G['largo_m']


def fr(s_m):
    return S[int(round((s_m % L) / paso)) % N]


sc.render.resolution_x = 1280
sc.render.resolution_y = 720
PASO_S = 200.0
k = 0
s_m = 0.0
while s_m < L - 1:
    p0 = fr(s_m - 12)
    p1 = fr(s_m + 45)
    cd = bpy.data.cameras.new('REC_%02d' % k)
    cd.lens = 22
    cd.clip_start = 0.3
    cd.clip_end = 12000
    c = bpy.data.objects.new('REC_%02d' % k, cd)
    loc = Vector((p0['x'], p0['y'], p0['z'] + 3.4))
    tgt = Vector((p1['x'], p1['y'], p1['z'] + 1.6))
    c.location = loc
    c.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(c)
    sc.camera = c
    sc.render.filepath = os.path.join(OUT, 'R%02d_s%04d.png' % (k, int(s_m)))
    bpy.ops.render.render(write_still=True)
    print('recorrido: R%02d s=%d z=%.1f sec=%s' % (k, int(s_m), fr(s_m)['z'], fr(s_m)['sec']))
    k += 1
    s_m += PASO_S
print('OK recorrido', k)
