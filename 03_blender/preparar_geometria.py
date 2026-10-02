# Convierte trazado_v1.json (2D, unidades SVG) en geometria_3d.json (metros,
# con alturas, peraltes, anchos, pianos y rejilla de terreno) listo para que
# construir_pista.py lo ensamble en Blender sin calculos pesados.
import json
import math

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
SRC = BASE + r'\02_trazado\trazado_v1.json'
OUT = BASE + r'\03_blender\geometria_3d.json'

data = json.load(open(SRC, encoding='utf-8'))
S = data['muestras']
N = len(S)
m_u = data['m_por_unidad']
L = data['largo_objetivo_m']
paso = L / N  # ~2 m entre muestras

# --- a metros, y-arriba, centrado ---
xs = np.array([p['x'] for p in S])
ys = np.array([p['y'] for p in S])
cx, cy = xs.mean(), ys.mean()
X = (xs - cx) * m_u
Y = (cy - ys) * m_u  # el eje y del SVG apunta hacia abajo
sec = [p['sec'] for p in S]

# --- suavizado ligero adicional del plano (ventana ~10 m) ---
def smooth_closed(a, win):
    k = np.ones(win) / win
    return np.convolve(np.concatenate([a[-win:], a, a[:win]]), k, 'same')[win:-win]

X = smooth_closed(X, 5)
Y = smooth_closed(Y, 5)

# la seccion de tierra es continua 14->26: rellena huecos cortos (cruces del
# lazo y ribetes del mapa) clasificados como asfalto dentro del tramo de tierra
di = [i for i, s in enumerate(sec) if s == 'dirt']
if di:
    a0, b0 = min(di), max(di)
    i = a0
    while i <= b0:
        if sec[i] != 'dirt':
            j = i
            while j <= b0 and sec[j] != 'dirt':
                j += 1
            if j <= b0 and (j - i) < 60:  # hueco < ~120 m
                for k in range(i, j):
                    sec[k] = 'dirt'
            i = j
        else:
            i += 1

# los tramos de puente tambien son continuos: rellena microhuecos (<40 m)
# para que el faldon y las pilas no tengan cortes
bi = [i for i, s in enumerate(sec) if s == 'bridge']
if bi:
    for a0, b0 in [(min(bi), max(bi))]:
        i = a0
        while i <= b0:
            if sec[i] != 'bridge':
                j = i
                while j <= b0 and sec[j] != 'bridge':
                    j += 1
                if j <= b0 and (j - i) < 20 and all(sec[k] not in ('dirt',) for k in range(i, j)):
                    for k in range(i, j):
                        sec[k] = 'bridge'
                i = j
            else:
                i += 1

# --- horquilla Loews: el usuario confirma que la rotonda va en la V del
# sector del casino (curva 38, la copia de la Loews de Monaco de la peli),
# con subida antes y bajada despues ---
curvas_pre = {c['n']: c for c in data['curvas']}
# el circulo del 29 queda entre la horquilla y la recta: el 'nearest' de la
# extraccion se engancha a la recta -> reasignamos al pico de curvatura real
i28 = curvas_pre[28]['s_idx']
i30 = curvas_pre[30]['s_idx']
def curv_at(i):
    a = (i - 4) % N; c2 = (i + 4) % N
    v1 = np.array([X[i] - X[a], Y[i] - Y[a]])
    v2 = np.array([X[c2] - X[i], Y[c2] - Y[i]])
    return abs(math.atan2(v1[0] * v2[1] - v1[1] * v2[0], float(np.dot(v1, v2))))
if i30 - i28 > 10:
    i29_fix = max(range(i28 + 4, i30 - 3), key=curv_at)
    print('curva 29 reasignada: s_idx %d -> %d (apex %.1f, %.1f)'
          % (curvas_pre[29]['s_idx'], i29_fix, X[i29_fix], Y[i29_fix]))
    curvas_pre[29]['s_idx'] = i29_fix
# la horquilla-rotonda SUSTITUYE a la V grande tras la 38: pico de curvatura
# entre las curvas 38 y 40 (indicacion directa del usuario)
i38_ = curvas_pre[38]['s_idx']
i40_ = curvas_pre[40]['s_idx']
i29 = max(range(i38_ + 8, i40_ - 4), key=curv_at)
print('rotonda Loews en el apex s_idx', i29)
# RONDA 13 (peticion del usuario): la bajada de la cresta 38 a la rotonda es una
# RECTA (sin la S del mapa): desde justo despues de la cresta hasta la entrada
# de la horquilla se sustituye el eje por el segmento recto entre ambos puntos
_ia, _ib = i38_ + 2, i29 - 13
_pa, _pb = np.array([X[_ia], Y[_ia]]), np.array([X[_ib], Y[_ib]])
for _k in range(_ia, _ib + 1):
    _f = (_k - _ia) / float(_ib - _ia)
    X[_k] = _pa[0] + (_pb[0] - _pa[0]) * _f
    Y[_k] = _pa[1] + (_pb[1] - _pa[1]) * _f
for _ in range(6):   # empalmes suaves en los dos extremos de la recta
    for _k in list(range(_ia - 8, _ia + 4)) + list(range(_ib - 3, _ib + 9)):
        X[_k] = (X[_k - 1] + 2 * X[_k] + X[_k + 1]) / 4
        Y[_k] = (Y[_k - 1] + 2 * Y[_k] + Y[_k + 1]) / 4
print('bajada 38 -> rotonda enderezada: %d muestras (%.0f m)' % (_ib - _ia, np.hypot(*(_pb - _pa))))
v_in = np.array([X[i29] - X[i29 - 6], Y[i29] - Y[i29 - 6]])
v_out = np.array([X[(i29 + 6) % N] - X[i29], Y[(i29 + 6) % N] - Y[i29]])
cruz = v_in[0] * v_out[1] - v_in[1] * v_out[0]
lado = 1.0 if cruz > 0 else -1.0  # giro izq -> centro a la izquierda
t_in = v_in / np.linalg.norm(v_in)
n_in = np.array([-t_in[1], t_in[0]]) * lado
R_LOEWS = 13.0
C = np.array([X[i29], Y[i29]]) + n_in * (R_LOEWS * 0.85)
VENT = 42  # muestras a cada lado (~84 m)
for di in range(-VENT, VENT + 1):
    i = (i29 + di) % N
    w = 0.5 * (1 + math.cos(math.pi * di / VENT))
    p = np.array([X[i], Y[i]])
    d = p - C
    dist = np.linalg.norm(d)
    if dist < 1e-6:
        continue
    objetivo = C + d / dist * R_LOEWS
    X[i] = p[0] * (1 - w) + objetivo[0] * w
    Y[i] = p[1] * (1 - w) + objetivo[1] * w
# re-suaviza solo la ventana para empalmes limpios
for _ in range(2):
    for di in range(-VENT + 1, VENT):
        i = (i29 + di) % N
        X[i] = (X[(i - 1) % N] + 2 * X[i] + X[(i + 1) % N]) / 4
        Y[i] = (Y[(i - 1) % N] + 2 * Y[i] + Y[(i + 1) % N]) / 4
# empalmes de entrada y salida mas largos y suaves (habia un quiebro en el eje)
for _ in range(10):
    for di in list(range(-VENT - 16, -18)) + list(range(19, VENT + 17)):
        i = (i29 + di) % N
        X[i] = (X[(i - 1) % N] + 2 * X[i] + X[(i + 1) % N]) / 4
        Y[i] = (Y[(i - 1) % N] + 2 * Y[i] + Y[(i + 1) % N]) / 4
loews_centro = (float(C[0]), float(C[1]))

# --- REMUESTREO UNIFORME (ronda 11e) ---------------------------------------------
# Todo lo que viene despues (tangentes, peralte, alturas, marcas, pianos...) supone
# muestras equiespaciadas. La horquilla imantada las dejaba a 0.5-7 m con quiebros
# de +-24 grados -> pliegue en el asfalto. Se remuestrea a paso constante, se suaviza
# la ventana de la horquilla ya con puntos uniformes y se remuestrea otra vez.
def _remuestrear(Xa, Ya, etiquetas, indices):
    P = np.column_stack([Xa, Ya])
    Pc = np.vstack([P, P[:1]])
    seg = np.hypot(np.diff(Pc[:, 0]), np.diff(Pc[:, 1]))
    s_old = np.concatenate([[0.0], np.cumsum(seg)])
    Lr = s_old[-1]
    sn = np.arange(N) * (Lr / N)
    Xn = np.interp(sn, s_old, Pc[:, 0])
    Yn = np.interp(sn, s_old, Pc[:, 1])
    viejo_de_nuevo = np.clip(np.searchsorted(s_old, sn, side='right') - 1, 0, N - 1)
    etiquetas_n = [etiquetas[int(k)] for k in viejo_de_nuevo]
    indices_n = [int(round(s_old[i] / (Lr / N))) % N for i in indices]
    return Xn, Yn, etiquetas_n, indices_n, Lr

_idx_curvas = [c['s_idx'] for c in data['curvas']]
_sep0 = np.hypot(np.diff(np.append(X, X[0])), np.diff(np.append(Y, Y[0])))
X, Y, sec, _ix, _Lr = _remuestrear(X, Y, sec, _idx_curvas + [i29, i38_, i40_])
_idx_curvas, (i29, i38_, i40_) = _ix[:-3], _ix[-3:]
for _ in range(14):                     # horquilla limpia: sin ondulaciones ni pliegues
    for di in range(-58, 59):
        i = (i29 + di) % N
        X[i] = (X[(i - 1) % N] + 2 * X[i] + X[(i + 1) % N]) / 4
        Y[i] = (Y[(i - 1) % N] + 2 * Y[i] + Y[(i + 1) % N]) / 4
X, Y, sec, _ix, _Lr = _remuestrear(X, Y, sec, _idx_curvas + [i29, i38_, i40_])
_idx_curvas, (i29, i38_, i40_) = _ix[:-3], _ix[-3:]
# RONDA 13: tras el suavizado, la bajada 38 -> rotonda vuelve a ser una RECTA
# exacta (el suavizado la ondulaba); solo la entrada a la horquilla se curva
_ia, _ib = i38_ + 2, i29 - 13
_pa, _pb = np.array([X[_ia], Y[_ia]]), np.array([X[_ib], Y[_ib]])
for _k in range(_ia, _ib + 1):
    _f = (_k - _ia) / float(_ib - _ia)
    X[_k] = _pa[0] + (_pb[0] - _pa[0]) * _f
    Y[_k] = _pa[1] + (_pb[1] - _pa[1]) * _f
for _ in range(4):
    for _k in list(range(_ia - 6, _ia + 3)) + list(range(_ib - 2, _ib + 6)):
        X[_k] = (X[_k - 1] + 2 * X[_k] + X[_k + 1]) / 4
        Y[_k] = (Y[_k - 1] + 2 * Y[_k] + Y[_k + 1]) / 4
# RONDA 12: el suavizado encoge la horquilla (9.5 m): se vuelve a imantar a un
# circulo de R_OBJ alrededor del centro ajustado y se remuestrea otra vez
R_OBJ = 13.5
i29 = max(range(i29 - 12, i29 + 13), key=curv_at)
_pa = np.array([[X[(i29 + di) % N], Y[(i29 + di) % N]] for di in range(-6, 7)])
_Aa = np.column_stack([2 * _pa[:, 0], 2 * _pa[:, 1], np.ones(len(_pa))])
_sa = np.linalg.lstsq(_Aa, (_pa ** 2).sum(1), rcond=None)[0]
_Ca = np.array([_sa[0], _sa[1]])
_VENT2 = 24
for di in range(-_VENT2, _VENT2 + 1):
    i = (i29 + di) % N
    w = 0.5 * (1 + math.cos(math.pi * di / _VENT2))
    p = np.array([X[i], Y[i]])
    d = p - _Ca
    dist = np.linalg.norm(d)
    if dist < 1e-6:
        continue
    objetivo = _Ca + d / dist * R_OBJ
    X[i] = p[0] * (1 - w) + objetivo[0] * w
    Y[i] = p[1] * (1 - w) + objetivo[1] * w
for _ in range(3):
    for di in list(range(-_VENT2 - 14, -_VENT2 + 6)) + list(range(_VENT2 - 5, _VENT2 + 15)):
        i = (i29 + di) % N
        X[i] = (X[(i - 1) % N] + 2 * X[i] + X[(i + 1) % N]) / 4
        Y[i] = (Y[(i - 1) % N] + 2 * Y[i] + Y[(i + 1) % N]) / 4
X, Y, sec, _ix, _Lr = _remuestrear(X, Y, sec, _idx_curvas + [i29, i38_, i40_])
_idx_curvas, (i29, i38_, i40_) = _ix[:-3], _ix[-3:]
for c, k in zip(data['curvas'], _idx_curvas):
    c['s_idx'] = int(k)
# el apice real de la horquilla tras el suavizado y su centro/radio efectivos
i29 = max(range(i29 - 12, i29 + 13), key=curv_at)
_ang = []
for di in range(-6, 7):
    i = (i29 + di) % N
    _ang.append([X[i], Y[i]])
_ang = np.array(_ang)
_A = np.column_stack([2 * _ang[:, 0], 2 * _ang[:, 1], np.ones(len(_ang))])
_sol = np.linalg.lstsq(_A, (_ang ** 2).sum(1), rcond=None)[0]
C = np.array([_sol[0], _sol[1]])
R_LOEWS = float(np.sqrt(_sol[2] + _sol[0] ** 2 + _sol[1] ** 2))
loews_centro = (float(C[0]), float(C[1]))
_sep1 = np.hypot(np.diff(np.append(X, X[0])), np.diff(np.append(Y, Y[0])))
print('remuestreo uniforme: separacion antes %.2f..%.2f m -> ahora %.2f..%.2f m | longitud real %.0f m | '
      'horquilla: radio efectivo %.1f m' % (_sep0.min(), _sep0.max(), _sep1.min(), _sep1.max(), _Lr, R_LOEWS))
print('horquilla Loews remodelada en curva 29; centro',
      round(loews_centro[0], 1), round(loews_centro[1], 1))

# RONDA 8b: el viaducto arranca nada mas salir de la rotonda (antes la pista
# iba 40 m sobre el agua encima de un muro) y muere ya dentro de tierra
_bi = [i for i, s_ in enumerate(sec) if s_ == 'bridge']
if _bi:
    for _k in range(i29 + 34, min(_bi)):
        sec[_k] = 'bridge'
    for _k in range(max(_bi), min(N, max(_bi) + 14)):
        sec[_k] = 'bridge'
    print('puente ampliado: s=%d..%d' % ((i29 + 34) * paso, (max(_bi) + 14) * paso))

# --- tangentes y normales ---
Xn = np.roll(X, -1); Xp = np.roll(X, 1)
Yn = np.roll(Y, -1); Yp = np.roll(Y, 1)
tx = Xn - Xp; ty = Yn - Yp
tlen = np.hypot(tx, ty); tx /= tlen; ty /= tlen
nx = -ty; ny = tx  # normal a la izquierda de la marcha

# --- curvatura con signo (rad/m), suavizada ---
ang = np.arctan2(ty, tx)
dang = np.diff(np.unwrap(np.concatenate([ang, ang[:1]])))
kappa = dang / paso
kappa = smooth_closed(kappa, 15)

# --- alturas: puntos de control por curva ---
curvas = {c['n']: c for c in data['curvas']}
Z_CTRL = {  # curva -> altura (m). Perfil segun la pelicula:
    # puerto -> subida acantilado -> pueblo -> ladera de tierra (cima 18) ->
    # descenso -> recta cuesta abajo -> sector casino EN ALTO (cresta en la
    # 38, bajada a la rotonda 39) -> PUENTE ALTO descendiendo 40->44 -> puerto
    # RONDA 8: mucha mas altura y ALTIBAJOS en la propia carretera (crestas
    # y vaguadas en el pueblo, la bajada y la recta), subida fuerte al casino
    # (cresta en 37-38) y bajada MUY exagerada a la rotonda 39.
    1: 5, 2: 18, 3: 28, 4: 40, 5: 36, 6: 44, 7: 54, 8: 50,
    9: 56, 10: 64, 11: 60, 12: 67, 13: 72, 14: 77, 15: 86, 16: 98,
    17: 104, 18: 122, 19: 112, 20: 102, 21: 112, 22: 102, 23: 84, 24: 70,
    25: 66, 26: 52, 27: 32, 28: 34, 29: 27, 30: 30,
    # RONDA 10: la recta 30-31 ya SUBE hacia la montana del casino (~125 m);
    # rotonda a 94 m y viaducto bajando desde ahi hasta el mar
    # RONDA 11: rampas UNIFORMES (sin picos): +13.5% de la 30 a la cresta y
    # -12.5% desde la cresta, por la rotonda y el viaducto, hasta casi el mar
    31: 89.9, 32: 96.6, 33: 103.6, 34: 111.2, 35: 113.4, 36: 118.5, 37: 122.6, 38: 124.0,
    39: 110.0, 40: 97.7, 41: 85.7, 42: 57.5, 43: 25.2, 44: 8.0, 45: 6, 46: 5.5,
    47: 5.5, 48: 5, 49: 4, 50: 3.5,
}
_s39 = curvas[39]['s_idx'] * paso
EXTRA_CTRL = [  # controles intermedios (s en m, z en m)
    (1180.0, 60.0),                       # cresta entre la 8 y la 9
    (2445.0, 43.0),                       # escalon de la bajada 26-27
    (2850.0, 43.2), (2960.0, 58.0), (3080.0, 74.2),  # la recta 30-31: rampa constante
    (4100.0, 43.2), (4380.0, 14.0),                   # viaducto: misma pendiente hasta abajo
    (_s39 - 30.0, 110.6), (_s39 + 30.0, 109.4),      # la horquilla va casi LLANA (2% en 60 m)
]
# los circulos 17-20 estan pegados al cruce del lazo y algunos se asignan a la
# rama equivocada -> recolocamos la zona de la cima con anclas geometricas:
# la 18 (cima) es el punto mas al norte del lazo de tierra
dirt_mask = np.array([s == 'dirt' for s in sec])
i_cima = int(np.argmax(np.where(dirt_mask, Y, -1e9)))
s_cima = i_cima * paso
s_fix = {17: s_cima - 110, 18: s_cima, 19: s_cima + 90, 20: s_cima + 150}
ctrl_raw = [(0.0, 3.0)] + sorted(
    [(s_fix.get(n, curvas[n]['s_idx'] * paso), z) for n, z in Z_CTRL.items()]
    + EXTRA_CTRL)
# fusiona controles a menos de 16 m (evita picos de pendiente)
ctrl = []
for s_c, z_c in ctrl_raw:
    if ctrl and s_c - ctrl[-1][0] < 16.0:
        ctrl[-1] = ((ctrl[-1][0] + s_c) / 2, (ctrl[-1][1] + z_c) / 2)
    else:
        ctrl.append((s_c, z_c))
s_ctrl = np.array([c[0] for c in ctrl])
z_ctrl = np.array([c[1] for c in ctrl])
# padding periodico para continuidad en la meta
s_pad = np.concatenate([s_ctrl[-4:] - L, s_ctrl, s_ctrl[:4] + L])
z_pad = np.concatenate([z_ctrl[-4:], z_ctrl, z_ctrl[:4]])
interp = PchipInterpolator(s_pad, z_pad)
s_samples = np.arange(N) * paso
Z = interp(s_samples)
Z = smooth_closed(Z, 25)  # acuerdos verticales largos (~50 m): nada de cambios bruscos
# limitador de pendiente de seguridad (12,5%): pasadas adelante/atras
MAXG = 0.165 * paso  # 16.5% maximo: empinado pero SIN picos cortos
for _ in range(4):
    for i in range(1, N):
        Z[i] = min(Z[i], Z[i - 1] + MAXG)
    for i in range(N - 2, -1, -1):
        Z[i] = min(Z[i], Z[i + 1] + MAXG)
    Z[0] = min(Z[0], Z[-1] + MAXG)
Z = smooth_closed(Z, 15)
grad = np.abs(np.diff(np.concatenate([Z, Z[:1]]))) / paso
print(f'alturas: min {Z.min():.1f} max {Z.max():.1f} | pendiente max {100*grad.max():.1f}%')

# --- peralte como pendiente lateral (fraccion), hacia el interior ---
lat = np.clip(kappa * 140.0, -0.04, 0.04)   # peralte suave: con 8.5% la calzada se veia 'de lado'
lat = smooth_closed(lat, 21)
lat[np.array([s == 'dirt' for s in sec])] *= 0.6  # menos peralte en tierra
# SIN peralte en la horquilla de la rotonda (pendiente fuerte + peralte = carretera torcida)
_dl = np.abs(np.arange(N) - i29)
_dl = np.minimum(_dl, N - _dl) * paso
_ml = np.clip((_dl - 70.0) / 40.0, 0.0, 1.0)
lat = lat * (_ml * _ml * (3 - 2 * _ml))
# SIN peralte en el viaducto (su losa es plana): rampa de 30 m en los estribos
_es_b = np.array([s == 'bridge' for s in sec])
if _es_b.any():
    _ib = np.where(_es_b)[0]
    _idx = np.arange(N)
    _d = np.min(np.abs(_idx[:, None] - _ib[None, :]), axis=1)
    _d = np.minimum(_d, N - _d) * paso
    _m = np.clip(_d / 30.0, 0.0, 1.0)
    lat = lat * (_m * _m * (3 - 2 * _m))

# --- anchos ---
W_SEC = {'straight': 13.0, 'tech': 11.0, 'norm': 12.0, 'dirt': 10.0, 'bridge': 12.0}
Wd = np.array([W_SEC[s] for s in sec])
en_meta = (s_samples < 170) | (s_samples > L - 120)
Wd[en_meta] = 16.0  # recta de boxes mas ancha
Wd = smooth_closed(Wd, 25)

# --- pit lane paralelo a la recta de meta (lado de los boxes) ---
PIT_IN = L - 190.0   # entrada tras la chicane
PIT_OUT = 170.0      # salida antes de la curva 1
total_pit = (L - PIT_IN) + PIT_OUT
pit_step = 3.0
pit_pts = []
kmax = int(total_pit / pit_step)
for k in range(kmax + 1):
    sm = (PIT_IN + k * pit_step) % L
    i = int(sm / paso) % N
    u = k * pit_step / total_pit
    ramp = min(1.0, min(u, 1.0 - u) / 0.16)
    ss = 3 * ramp**2 - 2 * ramp**3
    half_i = Wd[i] / 2
    d = (half_i - 1.0) * (1 - ss) + 13.5 * ss
    pit_pts.append({
        'x': round(float(X[i] - nx[i] * d), 3),
        'y': round(float(Y[i] - ny[i] * d), 3),
        'z': round(float(Z[i]), 3),
        'nx': round(float(nx[i]), 4),
        'ny': round(float(ny[i]), 4),
        'w': round(3.0 + 4.5 * ss, 2),
    })
print('pit lane:', len(pit_pts), 'muestras,', round(total_pit), 'm')

# --- pianos: tramos con curvatura fuerte en asfalto ---
fuerte = (np.abs(kappa) > 0.012) & np.array([s != 'dirt' for s in sec])  # tambien en el viaducto: van POR DENTRO
strips = []
i = 0
while i < N:
    if fuerte[i]:
        j = i
        while j < N and fuerte[j]:
            j += 1
        if (j - i) * paso >= 12:  # pianos solo en curvas de 12 m o mas
            a, b = max(0, i - 5), min(N - 1, j + 5)
            interior = 'izq' if kappa[i:j].mean() > 0 else 'der'
            strips.append({'a': int(a), 'b': int(b), 'lado': interior})
        i = j
    else:
        i += 1
print('pianos:', len(strips))

# --- rejilla de terreno ---
margen = 260.0
gx0, gx1 = X.min() - margen, X.max() + margen
gy0, gy1 = Y.min() - margen, Y.max() + margen
cell = 8.0
nxg = int((gx1 - gx0) / cell) + 1
nyg = int((gy1 - gy0) / cell) + 1
gx = gx0 + np.arange(nxg) * cell
gy = gy0 + np.arange(nyg) * cell
GX, GY = np.meshgrid(gx, gy)
gpts = np.column_stack([GX.ravel(), GY.ravel()])

no_bridge = np.array([s != 'bridge' for s in sec])
tree_all = cKDTree(np.column_stack([X, Y]))
tree_land = cKDTree(np.column_stack([X[no_bridge], Y[no_bridge]]))
tree_bridge = cKDTree(np.column_stack([X[~no_bridge], Y[~no_bridge]])) if (~no_bridge).any() else None
Z_land = Z[no_bridge]

d_all, i_all = tree_all.query(gpts)
d_land, i_land = tree_land.query(gpts)
if tree_bridge is not None:
    d_bri, i_bri = tree_bridge.query(gpts)
else:
    d_bri, i_bri = np.full(len(gpts), 1e9), np.zeros(len(gpts), dtype=int)

# lado del mar respecto a la recta de meta (el puerto queda a la izquierda de
# la marcha); verifica la orientacion con el propio trazado
t0 = np.array([tx[0], ty[0]])
p0 = np.array([X[0], Y[0]])
v = gpts - p0
side = t0[0] * v[:, 1] - t0[1] * v[:, 0]  # >0 = izquierda de la marcha
v_tr = np.column_stack([X, Y]) - p0
side_tr = t0[0] * v_tr[:, 1] - t0[1] * v_tr[:, 0]
if np.mean(side_tr > 0) > 0.5:  # el circuito deberia quedar a la derecha
    side = -side
    print('orientacion del mar invertida')

bridge_flag = ~no_bridge
# cuanto mas ALTA va la pista, mas lejos queda la orilla: laderas, no muros
# TIERRA PROTEGIDA alrededor de cada tramo en tierra, por bandas de altura
_XY_land = np.column_stack([X[no_bridge], Y[no_bridge]])
protegido = d_land <= 30.0
for _zb in range(10, 140, 10):
    _sel = Z_land >= _zb
    if not _sel.any():
        break
    _d_b = cKDTree(_XY_land[_sel]).query(gpts)[0]
    protegido |= _d_b <= 30.0 + 1.7 * (_zb - 4.0)
cerca_de_puente = bridge_flag[i_all] & (d_all <= 18)  # bajo el puente: agua
# GARGANTA DE MAR bajo el viaducto (salvo los 40 m de cada estribo): aunque la
# montana del casino 'proteja' esa tierra, el tablero sale de un acantilado y
# vuela sobre el agua -> arcos altisimos como en la pelicula
_nb = int((~no_bridge).sum())
_estribo = (i_bri * paso < 40.0) | ((_nb - 1 - i_bri) * paso < 40.0)
mar_forzado = (d_bri <= 40.0) & bridge_flag[i_all] & ~_estribo
es_mar = ((((side > 0) & (d_all > 45))
           | ((d_bri < 90) & (bridge_flag[i_all] | (side > 0)))
           | cerca_de_puente) & ~protegido) | mar_forzado
# la colina: bump gaussiano centrado en el lazo de tierra
dirt_idx = np.array([s == 'dirt' for s in sec])
hc = np.array([X[dirt_idx].mean(), Y[dirt_idx].mean() + 60])
dh = np.hypot(gpts[:, 0] - hc[0], gpts[:, 1] - hc[1])
rng = np.random.default_rng(7)
ruido = rng.normal(0, 1, (nyg, nxg))
for _ in range(3):  # ruido suave
    ruido = (ruido + np.roll(ruido, 1, 0) + np.roll(ruido, -1, 0)
             + np.roll(ruido, 1, 1) + np.roll(ruido, -1, 1)) / 5
ruido = (ruido * 2.5).ravel()

z_hill = 24.0 + 120.0 * np.exp(-(dh / 360.0) ** 2) + ruido
# promontorio del casino: el sector Monaco (33-38) va en alto sobre el mar
cs_idx = [c['s_idx'] for c in data['curvas'] if c['n'] in (33, 34, 35, 36, 37, 38)]
hc2 = np.array([X[cs_idx].mean(), Y[cs_idx].mean()])
dh2 = np.hypot(gpts[:, 0] - hc2[0], gpts[:, 1] - hc2[1])
z_hill = z_hill + 150.0 * np.exp(-(dh2 / 300.0) ** 2)
# RONDA 14: COLINAS por todo el mapa (peticion: 'mas altibajos, las montanas no
# solo atras'): ruido de valor multi-octava 'ridged' (crestas) de hasta 62 m,
# atenuado junto a la pista (30..110 m), en los sectores de pueblo y en el pit
from scipy.ndimage import zoom as _zoom
_rng_h = np.random.default_rng(2024)
_H = np.zeros((nyg, nxg))
for _lam, _amp in ((340.0, 1.0), (170.0, 0.5), (85.0, 0.25), (42.0, 0.12)):
    _ncx = max(4, int(round(nxg * cell / _lam)) + 2)
    _ncy = max(4, int(round(nyg * cell / _lam)) + 2)
    _g = _rng_h.uniform(-1.0, 1.0, (_ncy, _ncx))
    _up = _zoom(_g, (nyg / float(_ncy), nxg / float(_ncx)), order=3)
    _H += _amp * (1.0 - np.abs(_up[:nyg, :nxg]))
_H = _H / 1.87                                   # ~0..1
_H = np.clip(_H, 0.0, 1.0) ** 1.7
_colinas = 62.0 * _H.ravel()
_m1 = np.clip((d_land - 30.0) / 80.0, 0.0, 1.0)   # nada junto a la calzada
_XY_pueblo = np.array([[X[i], Y[i]] for i in range(N)
                       if any(a_ <= i * paso <= b_ for (a_, b_) in ((620, 1120), (1250, 1560), (2480, 2770), (3170, 3470), (4570, 4920)))])
_d_pueblo = cKDTree(_XY_pueblo).query(gpts)[0] if len(_XY_pueblo) else np.full(len(gpts), 1e9)
_m2 = 0.25 + 0.75 * np.clip((_d_pueblo - 90.0) / 120.0, 0.0, 1.0)
_XY_pit = np.array([[q['x'], q['y']] for q in pit_pts]) if pit_pts else None
_m3 = np.clip((cKDTree(_XY_pit).query(gpts)[0] - 140.0) / 150.0, 0.0, 1.0) if _XY_pit is not None else 1.0
z_hill = z_hill + _colinas * _m1 * _m2 * _m3
print('colinas: amplitud max %.0f m, media en tierra %.1f m' % (float((_colinas * _m1 * _m2 * _m3).max()), float((_colinas * _m1 * _m2 * _m3).mean())))
z_cerca = Z_land[i_land] - 0.5 - d_land * 0.045
w_tr = np.exp(-(d_land / 90.0) ** 2)
z_land = w_tr * z_cerca + (1 - w_tr) * z_hill
z_land = np.maximum(z_land, 1.0)
# costa como campo continuo: suaviza la mascara de mar -> linea de costa curva
coast = es_mar.astype(float).reshape(nyg, nxg)
for _ in range(6):
    coast = (coast + np.roll(coast, 1, 0) + np.roll(coast, -1, 0)
             + np.roll(coast, 1, 1) + np.roll(coast, -1, 1)) / 5
coastF = np.clip((coast.ravel() - 0.35) / 0.3, 0, 1)  # 0 tierra, 1 mar
# las laderas bajan al mar con pendiente limitada (60%): nada de paredes
# verticales de hierba en la orilla
from scipy.ndimage import distance_transform_edt
_dist_mar = distance_transform_edt(coastF.reshape(nyg, nxg) < 0.5) * cell
# junto al viaducto se admiten ACANTILADOS (300%); lejos de el, laderas del 60%
_pend = 0.60 + 2.40 * np.clip((200.0 - d_bri) / 120.0, 0.0, 1.0)
z_land = np.minimum(z_land, 1.0 + _dist_mar.ravel() * _pend)
z_grid = z_land * (1 - coastF) + (-4.0) * coastF
Zg = z_grid.reshape(nyg, nxg)
for _ in range(2):
    Zg = (Zg + np.roll(Zg, 1, 0) + np.roll(Zg, -1, 0)
          + np.roll(Zg, 1, 1) + np.roll(Zg, -1, 1)) / 5
z_grid = Zg.ravel()
z_grid = np.where(coastF > 0.5, np.minimum(z_grid, -3.0), z_grid)  # el mar siempre bajo el agua
# el terreno nunca atraviesa ni oculta la pista: corredor rebajado con berma
w_near = Wd[no_bridge][i_land]
half = w_near / 2
# RONDA 12: dentro de horquillas y lazos la muestra MAS CERCANA puede ser el lado
# alto mientras el otro ramal pasa mucho mas bajo -> el triangulo de terreno
# atravesaba el asfalto. Cota de referencia = MINIMO de las muestras en 16 m.
_zmin_r = Z_land[i_land].copy()
_cerca = np.where(d_land < half + 18)[0]
_vec = tree_land.query_ball_point(gpts[_cerca], 28.0)
_idx_land = np.where(no_bridge)[0]          # indice de muestra de cada punto de tree_land
_n_dobles = 0
for _k, _lst in zip(_cerca, _vec):
    if len(_lst) < 2:
        continue
    _ii = np.sort(_idx_land[_lst])
    _gap = np.diff(np.concatenate([_ii, [_ii[0] + N]])).max()
    # solo donde la pista VUELVE sobre si misma (dos ramales distintos a <28 m):
    # en una recta o curva normal las muestras son consecutivas (gap ~ N)
    if (N - _gap) > 40 and d_land[_k] < half[_k] + 4.0:   # solo la banda pegada al asfalto
        _zmin_r[_k] = min(_zmin_r[_k], Z_land[_lst].min())
        _n_dobles += 1
print('corredor: %d celdas rebajadas al minimo de dos ramales (horquillas/lazos)' % _n_dobles)
techo = np.where(d_land < half + 6,
                 _zmin_r - 0.7,
                 _zmin_r - 0.7 + (d_land - half - 6) * 0.35)
aplicar = (d_land < half + 18) & (coastF < 0.5)
z_grid = np.where(aplicar, np.minimum(z_grid, techo), z_grid)
# RONDA 14: TERRAZAS DEL PUEBLO. Cada sector de casas lleva bandas de terreno
# LLANO escalonadas respecto a la calzada (0.5 / 6 / 12 m por terraza, 4 m de
# transicion), medidas desde el borde del asfalto: filas de casas enteras
# apoyadas, calles traseras llanas y muros de bancal entre niveles.
TERRAZAS = [  # (s0, s1, lado, [(offset_ini, offset_fin, altura)])
    (640, 1100, -1, [(6, 28, 0.5), (28, 48, 6.0), (48, 68, 12.0)]),
    (1270, 1540, -1, [(6, 28, 0.5), (28, 48, 6.0), (48, 68, 12.0)]),
    (2500, 2750, -1, [(6, 28, 0.5), (28, 48, 6.0)]),
    (3190, 3450, -1, [(6, 28, 0.5), (28, 48, 6.0)]),
    (3190, 3450, 1, [(6, 28, -0.5), (28, 48, -6.0)]),
    (820, 1090, 1, [(6, 28, -0.5), (28, 48, -6.0)]),
    (1300, 1500, 1, [(6, 28, -0.5)]),
]
_gi = _idx_land[i_land]                       # muestra (global) mas cercana de cada celda
_s_cell = _gi * paso
_off = d_land - half                          # distancia al BORDE del asfalto
_vx = gpts[:, 0] - X[_gi]
_vy = gpts[:, 1] - Y[_gi]
_lado_cell = np.where(_vx * nx[_gi] + _vy * ny[_gi] > 0, 1, -1)
_n_terr = 0
for (_s0, _s1, _lado, _bandas) in TERRAZAS:
    _en_s = (_s_cell >= _s0 - 10) & (_s_cell <= _s1 + 10) & (_lado_cell == _lado) & (coastF < 0.5) & (d_bri > 30.0)
    _o_ini = _bandas[0][0]
    _o_fin = _bandas[-1][1]
    _sel = _en_s & (_off >= _o_ini) & (_off < _o_fin + 45.0)
    if not _sel.any():
        continue
    _xp = [_o_ini]
    _fp = [_bandas[0][2]]
    for _k, (_a, _b, _h) in enumerate(_bandas):
        if _k > 0:
            _xp.append(_a + 4.0)
            _fp.append(_h)
        _xp.append(_b)
        _fp.append(_h)
    _hcel = np.interp(_off[_sel], _xp, _fp)
    _z_t = Z[_gi[_sel]] + _hcel
    # fundido con el terreno natural mas alla de la ultima terraza (26 m) y en los extremos del sector
    _w_o = np.clip((_off[_sel] - _o_fin) / 45.0, 0.0, 1.0)
    _w_s = np.clip(np.minimum(_s_cell[_sel] - (_s0 - 10), (_s1 + 10) - _s_cell[_sel]) / 30.0, 0.0, 1.0)
    _w = (1.0 - _w_o) * _w_s
    z_grid[_sel] = z_grid[_sel] * (1.0 - _w) + _z_t * _w
    _n_terr += int(_sel.sum())
print('terrazas del pueblo: %d celdas escalonadas' % _n_terr)
# el terreno tampoco toca el tablero del viaducto donde este arranca en tierra
if tree_bridge is not None:
    _techo_b = Z[~no_bridge][i_bri] - 3.0
    z_grid = np.where((d_bri < 15.0) & (coastF < 0.5), np.minimum(z_grid, _techo_b), z_grid)
# el pit lane tambien lleva su caja en el terreno (antes la ladera lo cortaba)
if pit_pts:
    _pxy = np.array([[q['x'], q['y']] for q in pit_pts])
    _pz = np.array([q['z'] for q in pit_pts])
    _pw = np.array([q['w'] for q in pit_pts])
    _dp, _ip = cKDTree(_pxy).query(gpts)
    # explanada LLANA de 22 m tras el pit lane (edificio de boxes + tribuna) y luego talud
    # RONDA 13: explanada de 28 m (boxes + paddock) y ladera SUAVE (22%) hasta 220 m:
    # el talud del 45% salia como una pared gris detras de los boxes
    _caja = (_dp < _pw[_ip] / 2 + 220.0) & (coastF < 0.5)
    _techo_p = _pz[_ip] - 0.6 + np.maximum(_dp - _pw[_ip] / 2 - 28.0, 0.0) * 0.22
    z_grid = np.where(_caja, np.minimum(z_grid, _techo_p), z_grid)
# --- PASEO-MIRADOR (ronda 10, 'las vistas'): terraza de 15 m a nivel de la calzada
# sobre un muro de arcadas; del lado del mar el terreno baja 10 m a partir de su borde ---
MIRADORES = [(2990.0, 3150.0, 1, 15.0)]   # (s0, s1, lado, ancho)
for (_s0m, _s1m, _sd, _an) in MIRADORES:
    _en = (i_all >= int(_s0m / paso)) & (i_all <= int(_s1m / paso))
    _latg = (gpts[:, 0] - X[i_all]) * nx[i_all] + (gpts[:, 1] - Y[i_all]) * ny[i_all]
    _dl = _sd * _latg - Wd[i_all] / 2          # distancia lateral desde el borde
    _zona = _en & (_dl > 8.0) & (_dl < 130.0) & (coastF < 0.5)
    _techo_m = np.maximum(Z[i_all] - 10.0 - np.maximum(_dl - 8.0, 0.0) * 0.05, 1.0)
    z_grid = np.where(_zona, np.minimum(z_grid, _techo_m), z_grid)
es_mar = coastF > 0.5  # para el material del terreno
print(f'terreno: {nxg}x{nyg} celdas de {cell} m | mar: {100*es_mar.mean():.0f}%')

out = {
    'paso_m': paso,
    'n': N,
    'largo_m': L,
    'transform': {'cx': cx, 'cy': cy, 'm_por_unidad': m_u},
    'muestras': [{
        'x': round(float(X[i]), 3), 'y': round(float(Y[i]), 3), 'z': round(float(Z[i]), 3),
        'nx': round(float(nx[i]), 4), 'ny': round(float(ny[i]), 4),
        'w': round(float(Wd[i]), 2), 'lat': round(float(lat[i]), 4),
        'sec': sec[i],
    } for i in range(N)],
    'curvas': [{'n': c['n'], 's_idx': c['s_idx'],
                'x': round(float((np.array(c['x']) - cx) * m_u), 2),
                'y': round(float((cy - np.array(c['y'])) * m_u), 2)}
               for c in data['curvas']],
    'pianos': strips,
    'loews': {'x': round(loews_centro[0], 2), 'y': round(loews_centro[1], 2),
              'radio_calzada': R_LOEWS, 's_idx': int(i29)},
    'pit_lane': pit_pts,
    'miradores': [{'s0': m[0], 's1': m[1], 'side': m[2], 'ancho': m[3]} for m in MIRADORES],
    'terreno': {
        'x0': round(gx0, 1), 'y0': round(gy0, 1), 'cell': cell,
        'nx': nxg, 'ny': nyg,
        'z': [round(float(v), 2) for v in z_grid],
        'mar': [int(b) for b in es_mar],
    },
    'nivel_mar': 0.0,
}
json.dump(out, open(OUT, 'w', encoding='utf-8'))
print('OK ->', OUT)
