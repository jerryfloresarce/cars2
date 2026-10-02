"""renderizar_inspeccion.py - vistas de INSPECCION del mapa entero por baldosas:
cenital ortografica y oblicua (45 grados) de cada baldosa de 420 m con tierra o
pista, a renders/inspeccion/. Sirve para que los revisores (o yo) detecten casas
mal puestas, caminos que se salen, cosas flotando, etc. Cada PNG lleva impreso
en el nombre el centro de la baldosa en metros (para dar coordenadas).

  blender --background --factory-startup --python renderizar_inspeccion.py
  (env INSPECCION_SOLO=r3c2,r1c4 para repetir baldosas concretas)
"""
import json
import math
import os

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
OUT = BASE + r'\03_blender\renders\inspeccion'
os.makedirs(OUT, exist_ok=True)
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
S = G['muestras']
T = G['terreno']
sc = bpy.context.scene
sc.render.resolution_x = 1400
sc.render.resolution_y = 1400
sc.render.resolution_percentage = 100
sc.eevee.taa_render_samples = 16

TILE = 420.0
x0, y0 = T['x0'], T['y0']
W, H = T['nx'] * T['cell'], T['ny'] * T['cell']
ncol = int(math.ceil(W / TILE))
nrow = int(math.ceil(H / TILE))


def tiene_tierra(cx, cy):
    """baldosa con terreno emergido o pista"""
    for q in S[::4]:
        if abs(q['x'] - cx) < TILE / 2 and abs(q['y'] - cy) < TILE / 2:
            return True
    for dx in (-0.4, -0.2, 0.0, 0.2, 0.4):
        for dy in (-0.4, -0.2, 0.0, 0.2, 0.4):
            x, y = cx + dx * TILE, cy + dy * TILE
            i = int((x - x0) / T['cell'])
            j = int((y - y0) / T['cell'])
            if 0 <= i < T['nx'] and 0 <= j < T['ny'] and T['z'][j * T['nx'] + i] > 0.5:
                return True
    return False


def z_max_en(cx, cy):
    zm = 0.0
    for dx in (-0.45, -0.25, 0.0, 0.25, 0.45):
        for dy in (-0.45, -0.25, 0.0, 0.25, 0.45):
            x, y = cx + dx * TILE, cy + dy * TILE
            i = int((x - x0) / T['cell'])
            j = int((y - y0) / T['cell'])
            if 0 <= i < T['nx'] and 0 <= j < T['ny']:
                zm = max(zm, T['z'][j * T['nx'] + i])
    return zm


cam_d = bpy.data.cameras.new('INSP_cam')
cam = bpy.data.objects.new('INSP_cam', cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
solo = os.environ.get('INSPECCION_SOLO', '')
solo = set(solo.split(',')) if solo else None
n = 0
for r in range(nrow):
    for c in range(ncol):
        cx = x0 + (c + 0.5) * TILE
        cy = y0 + (r + 0.5) * TILE
        tag = 'r%dc%d' % (r, c)
        if solo and tag not in solo:
            continue
        if not tiene_tierra(cx, cy):
            continue
        zm = z_max_en(cx, cy)
        # cenital ortografica
        cam_d.type = 'ORTHO'
        cam_d.ortho_scale = TILE * 1.05
        cam_d.clip_end = 3000
        cam.location = (cx, cy, zm + 400.0)
        cam.rotation_euler = (0.0, 0.0, 0.0)
        sc.render.filepath = os.path.join(OUT, '%s_cenital_x%d_y%d.png' % (tag, int(cx), int(cy)))
        bpy.ops.render.render(write_still=True)
        # oblicua desde el sur-oeste a 45 grados
        cam_d.type = 'PERSP'
        cam_d.lens = 35
        d = TILE * 0.95
        cam.location = (cx - d * 0.55, cy - d * 0.55, zm + d * 0.75)
        dv = Vector((cx, cy, zm * 0.4)) - cam.location
        cam.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(OUT, '%s_oblicua_x%d_y%d.png' % (tag, int(cx), int(cy)))
        bpy.ops.render.render(write_still=True)
        n += 1
        print('baldosa', tag, 'centro', int(cx), int(cy))
print('OK inspeccion: %d baldosas' % n)
