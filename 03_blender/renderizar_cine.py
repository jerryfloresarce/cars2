# Renders "de cine": Cycles (iluminacion global real) + denoise + DOF suave.
# Renderiza las 6 camaras + 2 planos cinematograficos nuevos a 1600x900.
# Ejecutar:
#   blender --background --factory-startup --python renderizar_cine.py
import math
import os

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
sc = bpy.context.scene
OUT = BASE + r'\03_blender\renders\cine'
os.makedirs(OUT, exist_ok=True)

# --- Cycles con denoise ---
sc.render.engine = 'CYCLES'
sc.cycles.samples = 160
sc.cycles.use_denoising = True
try:
    sc.cycles.device = 'CPU'
except Exception:
    pass
sc.render.resolution_x = 1600
sc.render.resolution_y = 900
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = 0.1

def add_cam(name, loc, target, lens=40, dof_dist=None, fstop=2.8):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 12000
    if dof_dist:
        cd.dof.use_dof = True
        cd.dof.focus_distance = dof_dist
        cd.dof.aperture_fstop = fstop
    cam = bpy.data.objects.new(name, cd)
    cam.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(cam)
    return cam

import json
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
S = G['muestras']
lw = G.get('loews')

extra = []
if lw:
    # plano bajo de la rotonda Loews con DOF
    extra.append(add_cam('cine_loews',
                         (lw['x'] - 55, lw['y'] - 40, S[0]['z'] + 26),
                         (lw['x'], lw['y'], 20), 50,
                         dof_dist=60, fstop=2.2))
p0 = S[0]
extra.append(add_cam('cine_marina',
                     (p0['x'] + p0['nx'] * 60 - 220, p0['y'] + p0['ny'] * 60 - 160, 65),
                     (p0['x'] + p0['nx'] * 170, p0['y'] + p0['ny'] * 170, 5), 35))

CAMS = ['vista_aerea', 'meta_puerto', 'puerto_panoramica', 'casino_cerca',
        'cima_tierra', 'bahia_casino', 'cine_loews', 'cine_marina']
for cam_name in CAMS:
    cam = bpy.data.objects.get(cam_name)
    if not cam:
        print('sin camara', cam_name)
        continue
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT, 'cine_' + cam_name + '.png')
    bpy.ops.render.render(write_still=True)
    print('render cine:', cam_name)
print('OK renders de cine')
