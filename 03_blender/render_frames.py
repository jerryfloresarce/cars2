# Renderiza los fotogramas del video de forma REANUDABLE: recorre los frames
# que aun no existen en renders/frames/ y para limpiamente al agotar el
# presupuesto de tiempo (para relanzarlo tantas veces como haga falta).
# Ejecutar:
#   blender --background --factory-startup --python render_frames.py
import os
import time

import bpy

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
FRAMES_DIR = BASE + r'\03_blender\renders\frames'
# presupuesto por ejecucion: 480 s si lo lanza una herramienta con limite de 10 min;
# el bucle desatendido (render_loop.ps1) lo sube con la variable PRESUPUESTO_S
PRESUPUESTO_S = int(os.environ.get('PRESUPUESTO_S', '480'))
os.makedirs(FRAMES_DIR, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa_video.blend')
sc = bpy.context.scene
sc.render.image_settings.file_format = 'PNG'

t0 = time.time()
hechos = 0
pendientes = 0
# reparto opcional entre varios procesos: CHUNK_ID / CHUNK_OF (bloques de 25)
CHUNK_ID = int(os.environ.get('CHUNK_ID', '0'))
CHUNK_OF = int(os.environ.get('CHUNK_OF', '1'))
for f in range(sc.frame_start, sc.frame_end + 1):
    if CHUNK_OF > 1 and (f // 25) % CHUNK_OF != CHUNK_ID:
        continue
    ruta = os.path.join(FRAMES_DIR, 'f%04d.png' % f)
    if os.path.exists(ruta) and os.path.getsize(ruta) > 1000:
        continue
    if time.time() - t0 > PRESUPUESTO_S:
        pendientes += 1
        continue
    sc.frame_set(f)
    # respeta el cambio de camara de los marcadores
    marker_cam = None
    best = -1
    for mk in sc.timeline_markers:
        if mk.camera and mk.frame <= f and mk.frame > best:
            best = mk.frame
            marker_cam = mk.camera
    if marker_cam:
        sc.camera = marker_cam
    sc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    hechos += 1

total = sc.frame_end - sc.frame_start + 1
listos = total - pendientes if pendientes else total
print('RESUMEN: hechos_ahora=%d pendientes=%d total=%d' % (hechos, pendientes, total))
if pendientes == 0:
    print('TODOS_LOS_FRAMES_LISTOS')
