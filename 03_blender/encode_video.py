# Codifica los PNG de renders/frames en un MP4 (H.264) usando el editor de
# secuencias de Blender. Rapido (solo codificacion, sin render 3D).
# Ejecutar:
#   blender --background --factory-startup --python encode_video.py
import os

import bpy

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
FRAMES_DIR = BASE + r'\03_blender\renders\frames'
OUT = BASE + r'\03_blender\renders\porto_corsa_flythrough.mp4'

files = sorted(f for f in os.listdir(FRAMES_DIR) if f.endswith('.png'))
assert files, 'no hay frames'
print('frames a codificar:', len(files))

sc = bpy.context.scene
se = sc.sequence_editor_create()
coleccion = getattr(se, 'strips', None)
api_new = coleccion is not None and hasattr(coleccion, 'new_image')
if not api_new:
    coleccion = se.sequences
strip = coleccion.new_image('frames', os.path.join(FRAMES_DIR, files[0]),
                            channel=1, frame_start=1)
for f in files[1:]:
    strip.elements.append(f)

sc.frame_start = 1
sc.frame_end = len(files)
sc.render.fps = 24
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'MPEG4'
sc.render.ffmpeg.codec = 'H264'
sc.render.ffmpeg.constant_rate_factor = 'MEDIUM'
sc.render.ffmpeg.gopsize = 24
sc.render.filepath = OUT
bpy.ops.render.render(animation=True)
print('OK video ->', OUT)
