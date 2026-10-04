# Construye el paquete instalable de Assetto Corsa:
#   04_export/paquete/content/tracks/porto_corsa/{data,ui,ai,map.png}
#   04_export/paquete/FUENTES/{porto_corsa.fbx, texturas}
#   04_export/porto_corsa_mod.zip
# Coordenadas AC: x = x_blender, y = z_blender (arriba), z = -y_blender.
import json
import math
import os
import shutil
import struct
import zipfile

from PIL import Image, ImageDraw

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
# env GEOM: geometria de la escena congelada que se exporto (hacer_zip.sh), para que el mapa y la IA
# coincidan con el kn5 aunque la escena viva ya haya cambiado
G = json.load(open(os.environ.get('GEOM') or BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
PKG = BASE + r'\04_export\paquete'
TRACK = os.path.join(PKG, 'content', 'tracks', 'porto_corsa')
S = G['muestras']
N = G['n']
L = G['largo_m']

for sub in ('data', 'ui', 'ai'):
    os.makedirs(os.path.join(TRACK, sub), exist_ok=True)
os.makedirs(os.path.join(PKG, 'FUENTES'), exist_ok=True)

# ---------- map.png + map.ini ----------
xs = [p['x'] for p in S]
zs = [-p['y'] for p in S]  # z de AC
x0, x1 = min(xs), max(xs)
z0, z1 = min(zs), max(zs)
MARGIN = 60.0
ancho_m = (x1 - x0) + 2 * MARGIN
alto_m = (z1 - z0) + 2 * MARGIN
PXW = 1024
scale = ancho_m / PXW
PXH = int(alto_m / scale)
X_OFF = -x0 + MARGIN
Z_OFF = -z0 + MARGIN

img = Image.new('RGBA', (PXW, PXH), (0, 0, 0, 0))
dr = ImageDraw.Draw(img)
pts = [((p['x'] + X_OFF) / scale, ((-p['y']) + Z_OFF) / scale) for p in S]
dr.line(pts + [pts[0]], fill=(255, 255, 255, 255), width=7, joint='curve')
img.save(os.path.join(TRACK, 'map.png'))
with open(os.path.join(TRACK, 'data', 'map.ini'), 'w') as f:
    f.write('[PARAMETERS]\nWIDTH=%d\nHEIGHT=%d\nX_OFFSET=%.3f\nZ_OFFSET=%.3f\n'
            'MARGIN=20\nSCALE_FACTOR=%.5f\nMAX_SIZE=1600\nDRAWING_SIZE=10\n'
            % (PXW, PXH, X_OFF, Z_OFF, scale))

# outline: version pequena
img.resize((PXW // 2, PXH // 2), Image.LANCZOS).save(os.path.join(TRACK, 'ui', 'outline.png'))
prev = os.path.join(BASE, r'03_blender\renders\full_puerto.png')
if os.path.exists(prev):
    Image.open(prev).resize((1022, 575), Image.LANCZOS).convert('RGB').save(
        os.path.join(TRACK, 'ui', 'preview.png'))

# ---------- surfaces.ini ----------
SURFACES = """[SURFACE_0]
KEY=ROAD
FRICTION=0.98
DAMPING=0
WAV=
WAV_PITCH=0
FF_EFFECT=0
DIRT_ADDITIVE=0
IS_VALID_TRACK=1
BLACK_FLAG_TIME=0
SIN_HEIGHT=0
SIN_LENGTH=0
IS_PITLANE=0
VIBRATION_GAIN=0
VIBRATION_LENGTH=0

[SURFACE_1]
KEY=KERB
FRICTION=0.92
DAMPING=0
WAV=kerb.wav
WAV_PITCH=1
FF_EFFECT=1
DIRT_ADDITIVE=0
IS_VALID_TRACK=1
BLACK_FLAG_TIME=0
SIN_HEIGHT=0.04
SIN_LENGTH=1
IS_PITLANE=0
VIBRATION_GAIN=0.6
VIBRATION_LENGTH=1.2

[SURFACE_2]
KEY=GRASS
FRICTION=0.6
DAMPING=0.02
WAV=grass.wav
WAV_PITCH=0
FF_EFFECT=0
DIRT_ADDITIVE=1
IS_VALID_TRACK=0
BLACK_FLAG_TIME=0
SIN_HEIGHT=0
SIN_LENGTH=0
IS_PITLANE=0
VIBRATION_GAIN=0.1
VIBRATION_LENGTH=0.5

[SURFACE_3]
KEY=SAND
FRICTION=0.55
DAMPING=0.15
WAV=sand.wav
WAV_PITCH=0
FF_EFFECT=0
DIRT_ADDITIVE=1
IS_VALID_TRACK=0
BLACK_FLAG_TIME=0
SIN_HEIGHT=0
SIN_LENGTH=0
IS_PITLANE=0
VIBRATION_GAIN=0.15
VIBRATION_LENGTH=0.6

[SURFACE_4]
KEY=DIRT
FRICTION=0.98
DAMPING=0
WAV=dirt.wav
WAV_PITCH=0.9
FF_EFFECT=0.5
DIRT_ADDITIVE=1
IS_VALID_TRACK=1
BLACK_FLAG_TIME=0
SIN_HEIGHT=0
SIN_LENGTH=1.6
IS_PITLANE=0
VIBRATION_GAIN=0.25
VIBRATION_LENGTH=0.5

[SURFACE_5]
KEY=WALL
FRICTION=0.75
DAMPING=0
WAV=
WAV_PITCH=0
FF_EFFECT=0
DIRT_ADDITIVE=0
IS_VALID_TRACK=0
BLACK_FLAG_TIME=0
SIN_HEIGHT=0
SIN_LENGTH=0
IS_PITLANE=0
VIBRATION_GAIN=0
VIBRATION_LENGTH=0

[SURFACE_6]
KEY=PIT
FRICTION=0.98
DAMPING=0
WAV=
WAV_PITCH=0
FF_EFFECT=0
DIRT_ADDITIVE=0
IS_VALID_TRACK=1
BLACK_FLAG_TIME=0
SIN_HEIGHT=0
SIN_LENGTH=0
IS_PITLANE=1
VIBRATION_GAIN=0
VIBRATION_LENGTH=0
"""
# PIT: pit lane (1PIT_pit) y suelo de los garajes (1PIT_boxes_suelo): IS_PITLANE=1 activa el limitador
# de velocidad de boxes y marca la zona como pit lane (sin pit_lane.ai la IA no entra en boxes).
with open(os.path.join(TRACK, 'data', 'surfaces.ini'), 'w') as f:
    f.write(SURFACES)

# ---------- ui_track.json ----------
ui = {
    'name': 'Porto Corsa',
    'description': ('Porto Corsa Street Circuit (Cars 2, World Grand Prix). '
                    'Recreacion fan del circuito de la Riviera italiana: puerto, '
                    'subida al pueblo, seccion de TIERRA en la ladera, sector '
                    'Monaco con la horquilla Loews y los puentes del casino sobre '
                    'el mar. 5,2 km, 50 curvas. Mod sin animo de lucro.'),
    'tags': ['circuit', 'street', 'italy', 'cars 2', 'fictional', 'dirt'],
    'geotags': [],
    'country': 'Italy',
    'city': 'Porto Corsa',
    'length': '5200',
    'width': '10-16',
    'pitboxes': '20',
    'run': 'anticlockwise',
    'author': 'Arnau & Claude',
    'version': '1.1',
    'year': 2026,
}
with open(os.path.join(TRACK, 'ui', 'ui_track.json'), 'w', encoding='utf-8') as f:
    json.dump(ui, f, ensure_ascii=False, indent=2)

# ---------- fast_lane.ai provisional (linea central, formato v7) ----------
paso_ai = 4  # un punto cada ~8 m
idxs = list(range(0, N, paso_ai))
pts_ai = []
dist = 0.0
prev_p = None
for i in idxs:
    p = S[i]
    x, y, z = p['x'], p['z'], -p['y']  # AC: x, y(arriba), z
    if prev_p is not None:
        dist += math.dist((x, y, z), prev_p)
    prev_p = (x, y, z)
    pts_ai.append((x, y, z, dist, p['w']))

with open(os.path.join(TRACK, 'ai', 'fast_lane.ai'), 'wb') as f:
    f.write(struct.pack('<iiii', 7, len(pts_ai), 0, 0))
    for k, (x, y, z, d, w) in enumerate(pts_ai):
        f.write(struct.pack('<ffffi', x, y, z, d, k))
    f.write(struct.pack('<i', len(pts_ai)))
    for k, (x, y, z, d, w) in enumerate(pts_ai):
        nxt = pts_ai[(k + 1) % len(pts_ai)]
        fwd = (nxt[0] - x, nxt[1] - y, nxt[2] - z)
        fl = math.sqrt(sum(v * v for v in fwd)) or 1.0
        fwd = tuple(v / fl for v in fwd)
        lado = max(2.0, w / 2 - 1.0)
        extra = [55.0, 1.0, 0.0, 0.0, 1000.0, lado, lado, 0.0, 0.0,
                 0.0, 1.0, 0.0, fl, fwd[0], fwd[1], fwd[2], 0.0, 0.0]
        f.write(struct.pack('<18f', *extra))
print('fast_lane.ai:', len(pts_ai), 'puntos')

# ---------- modelo KN5 ya generado ----------
# Candidatos, por preferencia: kn5/porto_corsa_opt.kn5 (kn5_writer_opt.py: ~570 mallas, mucho mas ligero
# para AC) y kn5/porto_corsa.kn5 (kn5_writer.py: un dummy+malla por objeto, ~19k mallas). Al zip va SOLO
# un fichero y SOLO si esta VALIDADO: su informe de kn5_check.py (informe_check[_opt].json) debe decir
# RESULTADO OK, ser posterior al kn5 y coincidir en tamano. kn5/porto_corsa_b.kn5 nunca se empaqueta.
import hashlib
KN5_DIR = BASE + r'\04_export\kn5'


def kn5_validado(nombre_kn5, nombre_informe):
    ruta = os.path.join(KN5_DIR, nombre_kn5)
    inf = os.path.join(KN5_DIR, nombre_informe)
    if not (os.path.exists(ruta) and os.path.exists(inf)):
        return None, 'no existe el kn5 o su informe'
    if os.path.getmtime(inf) < os.path.getmtime(ruta):
        return None, 'informe anterior al kn5 (sin validar)'
    try:
        d = json.load(open(inf, encoding='utf-8'))
    except Exception as e:  # noqa
        return None, 'informe ilegible: %s' % e
    if d.get('resultado') != 'OK':
        return None, 'informe con RESULTADO %s' % d.get('resultado')
    if d.get('totales', {}).get('bytes_fichero') not in (None, os.path.getsize(ruta)):
        return None, 'el informe es de otro fichero (tamano distinto)'
    return ruta, 'validado 8/8 por kn5_check.py (%s)' % nombre_informe


kn5 = None
for cand, inf in (('porto_corsa_opt.kn5', 'informe_check_opt.json'), ('porto_corsa.kn5', 'informe_check.json')):
    ruta, motivo = kn5_validado(cand, inf)
    print('candidato %-20s -> %s' % (cand, motivo))
    if ruta:
        kn5 = ruta
        break
HAY_KN5 = kn5 is not None
if HAY_KN5:
    dst_kn5 = os.path.join(TRACK, 'porto_corsa.kn5')
    shutil.copy2(kn5, dst_kn5)
    md5 = hashlib.md5(open(dst_kn5, 'rb').read()).hexdigest()
    print('kn5 incluido: %s <- %s  %d bytes  md5 %s' % (dst_kn5, os.path.basename(kn5), os.path.getsize(dst_kn5), md5))
    # con kn5 el FBX sobra en el zip (45 MB): solo quedan las texturas como fuente
    viejo = os.path.join(PKG, 'FUENTES', 'porto_corsa.fbx')
    if os.path.exists(viejo):
        os.remove(viejo)
else:
    print('AVISO: no hay kn5 en 04_export/kn5; el zip solo llevara el FBX para ksEditor')
# ---------- fuentes: fbx (solo si no hay kn5) + texturas ----------
fbx = BASE + r'\04_export\fbx\porto_corsa.fbx'
if os.path.exists(fbx) and not HAY_KN5:
    shutil.copy2(fbx, os.path.join(PKG, 'FUENTES', 'porto_corsa.fbx'))
texdir = BASE + r'\03_blender\texturas'
if os.path.isdir(texdir):
    dst = os.path.join(PKG, 'FUENTES', 'texturas')
    os.makedirs(dst, exist_ok=True)
    for fn in os.listdir(texdir):
        if fn.endswith('.png') and not fn.startswith('mosaico'):
            shutil.copy2(os.path.join(texdir, fn), dst)

# ---------- extension/ext_config.ini (Custom Shaders Patch) ----------
# se copia TAL CUAL 04_export/extension/ext_config.ini (se puede editar a mano; color_ac solo lo genera si no
# existe) a content/tracks/porto_corsa/extension/, donde lo busca CSP (sin CSP la carpeta se ignora)
import sys  # noqa: E402
sys.path.insert(0, os.path.join(BASE, '04_export'))
import color_ac  # noqa: E402
print('ext_config.ini (CSP) ->', color_ac.copiar_ext_config(TRACK))

# instrucciones al zip
ins = BASE + r'\04_export\INSTRUCCIONES.md'
if os.path.exists(ins):
    shutil.copy2(ins, os.path.join(PKG, 'INSTRUCCIONES.md'))

# ---------- zip ----------
zpath = BASE + r'\04_export\porto_corsa_mod.zip'
if os.path.exists(zpath):
    os.remove(zpath)
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PKG):
        for fn in files:
            full = os.path.join(root, fn)
            z.write(full, os.path.relpath(full, PKG))
mb = os.path.getsize(zpath) / 1e6
print('OK zip -> %s (%.1f MB)' % (zpath, mb))
