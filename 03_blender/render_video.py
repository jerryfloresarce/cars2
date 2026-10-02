# Video de presentacion de Porto Corsa (v2, ronda 11). Pensado para que sea FLUIDO
# y se aprecie todo el mapa:
#   - 30 fps y una clave de camara en CADA fotograma (sin interpolaciones raras)
#   - vuelta completa a velocidad VARIABLE: rapida en rectas, lenta en curvas cerradas
#     y en los hitos (tunel, pueblo, paseo-mirador, horquilla, viaducto)
#   - trayectoria y punto de mira muy suavizados; altura adaptada (baja en el tunel,
#     alta sobre la rotonda)
#   - planos de presentacion: orbita aerea inicial y 4 planos lentos de los hitos
# Este script solo PREPARA la escena animada (porto_corsa_video.blend); los frames
# se renderizan con render_frames.py (reanudable, varios procesos en paralelo).
#   blender --background --factory-startup --python render_video.py
import json
import math

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))

bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
sc = bpy.context.scene
col = sc.collection

S = G['muestras']
N = G['n']
paso = G['paso_m']
L = G['largo_m']
CUR = {c['n']: c for c in G['curvas']}
FPS = 30


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def sample(s_m):
    i = (s_m % L) / paso
    i0 = int(i) % N
    i1 = (i0 + 1) % N
    t = i - int(i)
    a, b = S[i0], S[i1]
    return Vector((a['x'] + (b['x'] - a['x']) * t, a['y'] + (b['y'] - a['y']) * t,
                   a['z'] + (b['z'] - a['z']) * t))


def sample_suave(s_m, ventana, n=9):
    """Media ponderada (campana) de la pista en una ventana: trayectoria sin tirones."""
    acc = Vector((0, 0, 0))
    wt = 0.0
    for k in range(n):
        u = (k - (n - 1) / 2) / ((n - 1) / 2)          # -1..1
        w = 1.0 - u * u * 0.85
        acc += sample(s_m + u * ventana / 2) * w
        wt += w
    return acc / wt


def frame_s(s_m):
    return S[int(round((s_m % L) / paso)) % N]


# ---------- hitos ----------
ac = bpy.data.objects.get('TUNEL_acantilado')
S_IN = float(ac['s_in']) if ac is not None and 's_in' in ac else 470.0
S_OUT = float(ac['s_out']) if ac is not None and 's_out' in ac else 576.0
S_LOEWS = (G.get('loews') or {}).get('s_idx', CUR[39]['s_idx']) * paso
MIR = (G.get('miradores') or [{'s0': 2990.0, 's1': 3150.0, 'side': 1}])[0]


def dist_s(a, b):
    d = abs((a - b) % L)
    return min(d, L - d)


# ---------- perfil de velocidad ----------
def kappa(i, d=6):
    pa, pb = S[(i - d) % N], S[(i + d) % N]
    return abs(math.atan2(pa['ny'] * pb['nx'] - pa['nx'] * pb['ny'],
                          pa['nx'] * pb['nx'] + pa['ny'] * pb['ny'])) / (2 * d * paso)


V_MAX, V_MIN = 58.0, 17.0
v = []
for i in range(N):
    s_i = i * paso
    k = max(kappa(i), 1e-5)
    vi = min(V_MAX, max(V_MIN, math.sqrt(26.0 / k)))
    # hitos donde apetece mirar con calma
    if S_IN - 160 < s_i < S_OUT + 60:
        vi = min(vi, 34.0)
    if 640 < s_i < 1100 or 1260 < s_i < 1560:
        vi = min(vi, 40.0)                       # pueblo
    if MIR['s0'] - 60 < s_i < MIR['s1'] + 40:
        vi = min(vi, 36.0)                       # paseo-mirador y parking
    if dist_s(s_i, S_LOEWS) < 130:
        vi = min(vi, 24.0)                       # horquilla de la rotonda
    if CUR[41]['s_idx'] * paso < s_i < CUR[44]['s_idx'] * paso:
        vi = min(vi, 46.0)                       # viaducto y montana-pueblo
    if s_i > L - 200 or s_i < 120:
        vi = min(vi, 38.0)                       # recta de meta: tribunas y boxes
    v.append(vi)
for _ in range(4):                               # suavizado fuerte: acelera y frena sin tirones
    v = [sum(v[(i + j) % N] for j in range(-30, 31)) / 61.0 for i in range(N)]

# tiempo acumulado a lo largo de la vuelta -> s(t)
S_INICIO = L - 140.0                             # arranca llegando a la meta
LARGO_VUELTA = L + 170.0
ds = 1.0
ts, ss = [0.0], [0.0]
s_rec = 0.0
while s_rec < LARGO_VUELTA:
    vi = v[int(((S_INICIO + s_rec) % L) / paso) % N]
    ts.append(ts[-1] + ds / vi)
    s_rec += ds
    ss.append(s_rec)
T_VUELTA = ts[-1]
F_VUELTA = int(T_VUELTA * FPS)


def s_en_t(t):
    lo, hi = 0, len(ts) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ts[mid] <= t:
            lo = mid
        else:
            hi = mid
    u = (t - ts[lo]) / max(1e-9, ts[hi] - ts[lo])
    return S_INICIO + ss[lo] + (ss[hi] - ss[lo]) * u


# ---------- altura de la camara sobre la calzada ----------
def altura(s_m):
    s_m = s_m % L
    h = 10.5
    # tunel: baja hasta meterse dentro de la galeria (boveda a 8 m)
    if S_IN - 110 < s_m < S_OUT + 90:
        if s_m < S_IN - 30:
            h = 10.5 - 7.0 * smoothstep((s_m - (S_IN - 110)) / 80.0)
        elif s_m > S_OUT + 20:
            h = 3.5 + 7.0 * smoothstep((s_m - (S_OUT + 20)) / 70.0)
        else:
            h = 3.5
    # porticos de meta (llegan a 12.7 m): la camara pasa limpia por encima
    dp = dist_s(s_m, 6.0)
    if dp < 90.0:
        h = max(h, 10.5 + 7.5 * smoothstep(1.0 - dp / 90.0))
    # rotonda: mas alto para ver la horquilla entera y librar las palmeras de la isleta
    d = dist_s(s_m, S_LOEWS)
    if d < 150:
        h += 8.0 * smoothstep(1.0 - d / 150.0)
    return h


# ---------- camaras ----------
def new_cam(name, lens):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 0.5
    cd.clip_end = 20000
    cam = bpy.data.objects.new(name, cd)
    col.objects.link(cam)
    return cam


def clave(cam, f, loc, tgt):
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_euler', frame=f)


xs_all = [p['x'] for p in S]
ys_all = [p['y'] for p in S]
cxm, cym = (min(xs_all) + max(xs_all)) / 2, (min(ys_all) + max(ys_all)) / 2

tomas = []          # (nombre, camara, f_ini, f_fin)
f = 1

# --- toma 1: orbita aerea descendente (8 s) ---
F_ORB = 8 * FPS
cam = new_cam('CAM_orbita', 30)
for k in range(F_ORB):
    t = smoothstep(k / (F_ORB - 1)) * 0.92 + 0.08 * k / (F_ORB - 1)
    ang = math.radians(205) + t * math.radians(95)
    radio = 1650 - 650 * t
    alt = 1050 - 620 * t
    clave(cam, f + k, (cxm + radio * math.cos(ang), cym + radio * math.sin(ang), alt), (cxm, cym, 40))
tomas.append(('orbita', cam, f, f + F_ORB - 1))
f += F_ORB

# --- toma 2: la vuelta completa ---
cam = new_cam('CAM_vuelta', 25)
avisos = 0
for k in range(F_VUELTA):
    s_m = s_en_t(k / FPS)
    vel = v[int((s_m % L) / paso) % N]
    p = sample_suave(s_m, 46.0)
    mira = 42.0 + vel * 0.75
    tg = sample_suave(s_m + mira, 60.0)
    h = altura(s_m)
    loc = (p.x, p.y, p.z + h)
    clave(cam, f + k, loc, (tg.x, tg.y, tg.z + 2.5 + (h - 3.5) * 0.12))
tomas.append(('vuelta', cam, f, f + F_VUELTA - 1))
f += F_VUELTA


# --- tomas 3..6: planos lentos de los hitos (4.5 s cada uno, con entrada/salida suaves) ---
def plano(nombre, a, b, tg_a, tg_b, lens, seg=4.5):
    global f
    nf = int(seg * FPS)
    c = new_cam('CAM_' + nombre, lens)
    for k in range(nf):
        t = smoothstep(k / (nf - 1))
        loc = Vector(a).lerp(Vector(b), t)
        tg = Vector(tg_a).lerp(Vector(tg_b), t)
        clave(c, f + k, loc, tg)
    tomas.append((nombre, c, f, f + nf - 1))
    f += nf


cas = next((o for o in bpy.data.objects if o.name.startswith('CASINO_root') and o.parent is None
            and not any(cc.name == 'LIB' for cc in o.users_collection)), None)
if cas is not None:
    u = Vector((cas.location.x - cxm, cas.location.y - cym, 0)).normalized()
    pr = Vector((-u.y, u.x, 0))
    c0 = cas.location
    plano('casino', c0 + u * 300 - pr * 230 + Vector((0, 0, -30)), c0 + u * 270 - pr * 40 + Vector((0, 0, 25)),
          c0 + Vector((0, 0, -35)), c0 + Vector((0, 0, -15)), 32)
pp = bpy.data.objects.get('PENON_puente')
if pp is not None:
    c0 = pp.location
    plano('viaducto', Vector((c0.x - 420, c0.y - 300, 45)), Vector((c0.x - 260, c0.y - 400, 150)),
          Vector((c0.x, c0.y, 40)), Vector((c0.x + 20, c0.y, 30)), 30)
qb = frame_s((MIR['s0'] + MIR['s1']) / 2)
sd = MIR['side']
nb = Vector((qb['nx'] * sd, qb['ny'] * sd, 0))
tb = Vector((qb['ny'], -qb['nx'], 0))
pb = Vector((qb['x'], qb['y'], qb['z']))
plano('mirador', pb + nb * 150 - tb * 120 + Vector((0, 0, 2)), pb + nb * 125 + tb * 30 + Vector((0, 0, 24)),
      pb + nb * 22 + Vector((0, 0, -6)), pb + nb * 18 + Vector((0, 0, -3)), 30)
q0 = frame_s(60)
n0 = Vector((q0['nx'], q0['ny'], 0))
p0 = Vector((q0['x'], q0['y'], q0['z']))
plano('final', p0 + n0 * 130 + Vector((0, 0, 22)), p0 + n0 * 420 + Vector((0, 0, 260)),
      p0 + Vector((0, 0, 6)), Vector((cxm, cym, 30)).lerp(p0, 0.5), 30, seg=7.0)

F_TOTAL = f - 1

# --- marcadores de cambio de camara ---
for (nombre, c, fa, fb) in tomas:
    mk = sc.timeline_markers.new(nombre, frame=fa)
    mk.camera = c
sc.camera = tomas[0][1]

# --- comprobacion de holgura de la camara de la vuelta (solo informa) ---
dg = bpy.context.evaluated_depsgraph_get()
cv = tomas[1][1]
cerca = []
for fr_ in range(tomas[1][2], tomas[1][3] + 1, 3):
    sc.frame_set(fr_)
    o = cv.matrix_world.translation
    fw = cv.matrix_world.to_3x3() @ Vector((0, 0, -1))
    for d, lim in ((fw, 9.0), (Vector((0, 0, 1)), 2.0), (Vector((0, 0, -1)), 2.2)):
        hit, loc, nrm, idx, ob, mtx = sc.ray_cast(dg, o, d, distance=lim)
        if hit:
            cerca.append((fr_, ob.name, round((loc - o).length, 1)))
            break
print('AVISOS de holgura de camara:', len(cerca), cerca[:25])

sc.frame_start = 1
sc.frame_end = F_TOTAL
sc.render.fps = FPS
sc.render.resolution_x = 1920   # RTX 5080 de 16 GB: Full HD
sc.render.resolution_y = 1080
sc.render.resolution_percentage = 100
try:
    sc.eevee.taa_render_samples = 32
except Exception:
    pass
bpy.ops.wm.save_as_mainfile(filepath=BASE + r'\03_blender\porto_corsa_video.blend')
print('TOMAS:', [(n_, fa, fb) for (n_, c, fa, fb) in tomas])
print('OK escena de video guardada: %d frames a %d fps = %.0f s (vuelta %.0f s)' % (F_TOTAL, FPS, F_TOTAL / FPS, T_VUELTA))
