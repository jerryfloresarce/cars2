"""Monta los PNG de renders/frames en un MP4 H.264 con el ffmpeg de imageio-ffmpeg.

Se usa este y no el secuenciador de Blender porque esta compilacion de Blender no
trae salida FFMPEG. Comprueba antes que no falte ningun fotograma.

Ejecutar con el python del sistema:
    python montar_video.py
"""
import os
import subprocess
import sys

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
FRAMES = os.path.join(BASE, '03_blender', 'renders', 'frames')
SALIDA = os.path.join(BASE, '03_blender', 'renders', 'porto_corsa_flythrough.mp4')
COPIA = os.path.join(BASE, '04_export', 'porto_corsa_video.mp4')
FPS = 30

import imageio_ffmpeg

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

pngs = sorted(f for f in os.listdir(FRAMES) if f.endswith('.png'))
if not pngs:
    sys.exit('no hay fotogramas en %s' % FRAMES)
numeros = sorted(int(f[1:5]) for f in pngs)
faltan = [n for n in range(numeros[0], numeros[-1] + 1) if n not in set(numeros)]
pequenos = [f for f in pngs if os.path.getsize(os.path.join(FRAMES, f)) < 20000]
print('fotogramas: %d (de f%04d a f%04d)' % (len(pngs), numeros[0], numeros[-1]))
if faltan:
    sys.exit('FALTAN %d fotogramas, el primero es f%04d' % (len(faltan), faltan[0]))
if pequenos:
    sys.exit('fotogramas sospechosamente pequenos (render a medias): %s' % pequenos[:5])

cmd = [ffmpeg, '-y', '-framerate', str(FPS),
       '-start_number', str(numeros[0]),
       '-i', os.path.join(FRAMES, 'f%04d.png'),
       '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
       '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
       '-vf', 'scale=1920:1080:flags=lanczos',
       SALIDA]
print('codificando...')
r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
if r.returncode != 0:
    print(r.stderr[-3000:])
    sys.exit('ffmpeg fallo con codigo %d' % r.returncode)

import shutil

shutil.copy2(SALIDA, COPIA)
mb = os.path.getsize(SALIDA) / 1e6
print('OK video -> %s (%.1f MB, %.0f s)' % (SALIDA, mb, len(pngs) / FPS))
print('OK copia  -> %s' % COPIA)
