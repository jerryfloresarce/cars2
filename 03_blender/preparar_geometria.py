# Convierte trazado_v1.json (2D, unidades SVG) en geometria_3d.json (metros,
# con alturas, peraltes, anchos, pianos y rejilla de terreno) listo para que
# construir_pista.py lo ensamble en Blender sin calculos pesados.
import json
import math
import os

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
SRC = BASE + r'\02_trazado\trazado_v1.json'
OUT = BASE + r'\03_blender\geometria_3d.json'
# v3 (pueblo_terreno): salida y carpeta de QA desviables para probar sin pisar geometria_3d.json (env GEOM_OUT / QA_DIR)
OUT = os.environ.get('GEOM_OUT', OUT)
QA_DIR = os.environ.get('QA_DIR', BASE + '/03_blender/renders/qa')

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


# v3 (pueblo_terreno, revision E5): las horquillas de TIERRA 19 (s ~1872) y 26 (s ~2364) salian del SVG con un eje de
# R 5.5-6.8 m y 10 m de ancho (borde interior colapsado: caras de PISTA con nz 0.4-0.6 y el arcen plegado). Se abren a
# R >= HORQ_R_MIN conservando las tangentes de entrada/salida, la cota (Z va por indice) y el NUMERO de muestras del tramo:
# proyeccion de la flecha de cada terna (vecinos a 1-4 muestras) sobre la de un circulo de R_MIN (+ holgura), suavizado solo
# donde se toco (transicion sin escalon de curvatura) y remuestreo UNIFORME del tramo (paso ~1.90-1.96 m dentro, 2 fuera):
# fuera de los tramos ninguna muestra cambia (las s del resto del circuito, sectores, pretiles, Loews, siguen igual)
HORQ_R_MIN = 12.5
HORQ_TRAMOS = [(1800.0, 1940.0), (2300.0, 2440.0)]     # curvas 18-19 (cima de tierra) y 26 (bajada)


def _uniforme_tramo(P):
    seg = np.hypot(*np.diff(P, axis=0).T); sc = np.concatenate([[0.0], np.cumsum(seg)])
    sn = np.linspace(0.0, sc[-1], len(P))
    return np.column_stack([np.interp(sn, sc, P[:, 0]), np.interp(sn, sc, P[:, 1])])


def _proyectar_radio(P, R_min, fijos=3, iters=4000):
    """mueve cada muestra hacia la cuerda de sus vecinos (a 1..4 muestras) hasta que su flecha es la de un circulo de
    R_min; los 'fijos' extremos no se mueven. Devuelve (P uniforme, muestras tocadas)."""
    P = P.copy(); n = len(P); tocado = np.zeros(n, bool)
    for it in range(iters):
        peor = 0.0
        for k in (1, 2, 3, 4):
            a = P[:-2 * k]; b = P[k:-k]; c = P[2 * k:]
            v = b - 0.5 * (a + c); h = np.linalg.norm(v, axis=1); ch = np.linalg.norm(c - a, axis=1)
            exc = h - (R_min - np.sqrt(np.maximum(R_min ** 2 - (ch / 2) ** 2, 0.0)))
            idx = np.arange(k, n - k)
            mal = (exc > 1e-4) & (idx >= fijos) & (idx < n - fijos)
            if mal.any():
                peor = max(peor, float(exc[mal].max()))
                P[idx[mal]] -= (v / np.maximum(h, 1e-9)[:, None] * (0.5 * exc)[:, None])[mal]
                tocado[idx[mal]] = True
        if peor < 1e-4:
            break
        if it % 3 == 2:
            P = _uniforme_tramo(P)
    return _uniforme_tramo(P), tocado


def _radio_min(P, k=2):
    a = P[:-2 * k]; b = P[k:-k]; c = P[2 * k:]
    cr = (b - a)[:, 0] * (c - a)[:, 1] - (b - a)[:, 1] * (c - a)[:, 0]
    r = (np.linalg.norm(b - a, axis=1) * np.linalg.norm(c - b, axis=1) * np.linalg.norm(a - c, axis=1)
         / (2.0 * np.maximum(np.abs(cr), 1e-9)))
    return float(r.min())


for _s_a, _s_b in HORQ_TRAMOS:
    _ia, _ib = int(round(_s_a / paso)), int(round(_s_b / paso))
    _P0 = np.column_stack([X[_ia:_ib + 1], Y[_ia:_ib + 1]]).astype(float)
    _P, _toc = _proyectar_radio(_P0, HORQ_R_MIN + 1.5)
    if not _toc.any():
        continue
    _n = len(_P); _i0 = int(np.argmax(_toc)); _i1 = int(_n - 1 - np.argmax(_toc[::-1]))
    _w = np.array([max(0.0, 1.0 - max(_i0 - i, i - _i1, 0) / 5.0) for i in range(_n)])
    _w[:3] = 0.0; _w[-3:] = 0.0
    for _ in range(4):                  # transicion suave (sin escalon de curvatura) solo donde se toco
        _Lp = np.zeros_like(_P); _Lp[1:-1] = 0.25 * _P[:-2] + 0.25 * _P[2:] - 0.5 * _P[1:-1]
        _P = _P + _w[:, None] * _Lp
    _P, _ = _proyectar_radio(_uniforme_tramo(_P), HORQ_R_MIN)
    _dz = np.hypot(*(_P - _P0).T)
    print('v3 E5 horquilla s %.0f-%.0f: radio minimo del eje %.1f -> %.1f m | muestras movidas hasta %.2f m | paso %.3f m '
          '(largo %.1f -> %.1f m)' % (_s_a, _s_b, _radio_min(_P0), _radio_min(_P), _dz.max(),
                                      float(np.hypot(*np.diff(_P, axis=0).T).mean()),
                                      float(np.hypot(*np.diff(_P0, axis=0).T).sum()), float(np.hypot(*np.diff(_P, axis=0).T).sum())))
    X[_ia:_ib + 1] = _P[:, 0]; Y[_ia:_ib + 1] = _P[:, 1]

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
        # RONDA 15 v1 (revision B3/A-04): cota del PLANO PERALTADO de la pista prolongado hasta el eje del pit lane
        # (el pit esta en la lateral -d: z = Z - lat*(-d)); antes la cota del EJE sin peralte dejaba la losa del pit
        # 0.2-0.4 m por encima del asfalto en la salida (s 136-170, lat -0.04)
        'z': round(float(Z[i] + lat[i] * d), 3),
        'nx': round(float(nx[i]), 4),
        'ny': round(float(ny[i]), 4),
        'w': round(3.0 + 4.5 * ss, 2),
    })
print('pit lane:', len(pit_pts), 'muestras,', round(total_pit), 'm')

# --- parrilla de salida (RONDA 15 v1, revision A-15): UNA sola definicion para construir_pista (marcas pintadas) y
# exportar_ac (AC_START_0..19): 20 puestos en dos columnas tras la linea de meta, s = L - 14 - 8*(i//2), lateral
# +2.3 (pares, izquierda) / -2.3 (impares); x, y, z sobre el plano peraltado y la tangente de la marcha ---
parrilla = []
for _k in range(20):
    _s = L - 14.0 - 8.0 * (_k // 2)
    _lat = 2.3 if _k % 2 == 0 else -2.3
    _i = int(round(_s / paso)) % N
    parrilla.append({'i': _k, 's': round(_s, 2), 'lat': _lat, 'x': round(float(X[_i] + nx[_i] * _lat), 3),
                     'y': round(float(Y[_i] + ny[_i] * _lat), 3), 'z': round(float(Z[_i] - lat[_i] * _lat), 3),
                     'tx': round(float(ny[_i]), 4), 'ty': round(float(-nx[_i]), 4)})

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

# --- rejilla de terreno (RONDA 15: MACIZO DE MONTANA, ver terreno_montana.py) ---
# Antes: colina gaussiana + colinas 'ridged' + corredor/terrazas/caja del pit/
# miradores/estribos/garganta/costa, todo aqui. Ahora lo hace terreno_montana.construir
# (macizo disenado: Monte Porto Corsa, espolon del coche, lomas, promontorio del
# casino; cell = 4 m; terrazas desde urbanismo_spec.json) y devuelve ademas las
# cumbres y la mascara de roca para el material.
import terreno_montana
# PASEO-MIRADOR (ronda 10): (s0, s1, lado, ancho). RONDA 15: lado -1, que es el del
# MAR en esa recta (el +1 de la ronda 10 mira tierra adentro: el banco Z-10 tallaba
# un rectangulo de 130x160 m en las lomas). integrar_escena lee este lado del JSON.
MIRADORES = [(2990.0, 3150.0, -1, 15.0)]
_spec_urb = json.load(open(BASE + '/03_blender/urbanismo_spec.json', encoding='utf-8'))
# (coordinador, ronda 15c) las curvas van en METROS como en el JSON de salida: data['curvas']
# trae x/y en unidades del SVG y la elipse del penon del casino salia en otro sitio
_curvas_m = [{'n': c['n'], 's_idx': c['s_idx'], 'x': float((np.array(c['x']) - cx) * m_u),
              'y': float((cy - np.array(c['y'])) * m_u)} for c in data['curvas']]
# RONDA 15 v1: construir_loews_intacta = construir() con el terreno de la rotonda Loews congelado (peticion del usuario)
# v2 (revision J-N2): la referencia de la Loews es FIJA (03_blender/assets/_loews_terreno.npz, terreno entregado el 03/10)
# v2 (revision C2-01/D2-01/G2-03/E2-01/F2-11): se pasa el PERALTE (lat) para la garantia por triangulo de que la hierba no
# asoma sobre el plano peraltado de la calzada (terreno_montana.bajar_bajo_asfalto)
_res_t = terreno_montana.construir_loews_intacta(X, Y, Z, sec, Wd, nx, ny, paso, L, _curvas_m, pit_pts,
                                                loews_centro, _spec_urb, MIRADORES, cell=4.0,
                                                qa_dir=QA_DIR, lat=lat)
gx0, gy0, cell = _res_t['x0'], _res_t['y0'], _res_t['cell']
nxg, nyg = _res_t['nx'], _res_t['ny']
z_grid = _res_t['z_grid']
es_mar = _res_t['es_mar']  # para el material del terreno
_cumbres = _res_t['extras']['cumbres']
_mascara_roca = _res_t['extras']['mascara_roca']
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
    'parrilla': parrilla,
    'miradores': [{'s0': m[0], 's1': m[1], 'side': m[2], 'ancho': m[3]} for m in MIRADORES],
    'terreno': {
        'x0': round(gx0, 1), 'y0': round(gy0, 1), 'cell': cell,
        'nx': nxg, 'ny': nyg,
        'z': [round(float(v), 2) for v in z_grid],
        'mar': [int(b) for b in es_mar],
    },
    # RONDA 15: cumbres (x, y, z) y mascara de roca por celda (0..1) para el material
    'cumbres': [[round(float(c[0]), 1), round(float(c[1]), 1), round(float(c[2]), 1)] for c in _cumbres],
    'mascara_roca': [round(float(v), 2) for v in _mascara_roca],
    'nivel_mar': 0.0,
}
json.dump(out, open(OUT, 'w', encoding='utf-8'))
print('OK ->', OUT)
