# Extrae la linea central EXACTA del circuito desde el SVG oficial de la wiki
# (Layout_Porto_Corsa_Grand_Prix.svg): rasteriza la cinta negra, la
# esqueletoniza, clasifica superficies por los nucleos de color y numera las
# curvas con los 50 marcadores del propio SVG.
# Salidas: trazado_v1.json, trazado_v1.js (visor), debug_extraccion.png
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from svgpathtools import parse_path
from skimage.morphology import skeletonize
from scipy import ndimage

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
SVG = BASE + r'\01_referencias\wiki\Layout_Porto_Corsa_Grand_Prix.svg'
OUT_JSON = BASE + r'\02_trazado\trazado_v1.json'
OUT_JS = BASE + r'\02_trazado\trazado_v1.js'
OUT_DBG = BASE + r'\02_trazado\debug_extraccion.png'
SCALE = 8
LARGO_M = 5200.0
SVGNS = '{http://www.w3.org/2000/svg}'

# ---------- transformaciones afines ----------
def mat_mul(A, B):
    return [A[0]*B[0]+A[2]*B[1], A[1]*B[0]+A[3]*B[1],
            A[0]*B[2]+A[2]*B[3], A[1]*B[2]+A[3]*B[3],
            A[0]*B[4]+A[2]*B[5]+A[4], A[1]*B[4]+A[3]*B[5]+A[5]]

def mat_apply(A, x, y):
    return (A[0]*x + A[2]*y + A[4], A[1]*x + A[3]*y + A[5])

def parse_transform(t):
    M = [1, 0, 0, 1, 0, 0]
    for m in re.finditer(r'(translate|rotate|scale|matrix)\(([^)]*)\)', t or ''):
        kind = m.group(1)
        args = [float(v) for v in re.split(r'[,\s]+', m.group(2).strip()) if v]
        if kind == 'translate':
            tx, ty = args[0], args[1] if len(args) > 1 else 0.0
            M = mat_mul(M, [1, 0, 0, 1, tx, ty])
        elif kind == 'scale':
            sx = args[0]; sy = args[1] if len(args) > 1 else sx
            M = mat_mul(M, [sx, 0, 0, sy, 0, 0])
        elif kind == 'rotate':
            a = math.radians(args[0])
            if len(args) == 3:
                cx, cy = args[1], args[2]
                M = mat_mul(M, [1, 0, 0, 1, cx, cy])
                M = mat_mul(M, [math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0])
                M = mat_mul(M, [1, 0, 0, 1, -cx, -cy])
            else:
                M = mat_mul(M, [math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0])
        elif kind == 'matrix':
            M = mat_mul(M, args)
    return M

tree = ET.parse(SVG)
root = tree.getroot()
items = []
def walk(el, M):
    t = el.get('transform')
    M2 = mat_mul(M, parse_transform(t)) if t else M
    if el.tag == SVGNS + 'path':
        items.append({'id': el.get('id', ''), 'd': el.get('d', ''),
                      'style': el.get('style', ''), 'M': M2})
    for ch in el:
        walk(ch, M2)
walk(root, [1, 0, 0, 1, 0, 0])
byid = {it['id']: it for it in items}
print('paths:', len(items))

def fill_of(style):
    m = re.search(r'fill:\s*(#[0-9a-fA-F]{6})', style)
    return m.group(1).lower() if m else None

def sample_subpaths(it, pts_per_seg=14):
    p = parse_path(it['d'])
    subs = []
    for sp in p.continuous_subpaths():
        pts = []
        for seg in sp:
            for i in range(pts_per_seg):
                z = seg.point(i / pts_per_seg)
                pts.append(mat_apply(it['M'], z.real, z.imag))
        z = sp[-1].point(1.0)
        pts.append(mat_apply(it['M'], z.real, z.imag))
        subs.append(pts)
    return subs

def poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return a / 2.0

W = int(500 * SCALE); H = int(math.ceil(551.673 * SCALE))

def rasterize(pids):
    polys = []
    for pid in pids:
        for sub in sample_subpaths(byid[pid]):
            if len(sub) > 2:
                polys.append(sub)
    acc = np.zeros((H, W), dtype=bool)
    for sub in polys:
        m = Image.new('1', (W, H), 0)
        ImageDraw.Draw(m).polygon([(x * SCALE, y * SCALE) for x, y in sub], fill=1)
        acc ^= np.array(m, dtype=bool)  # even-odd
    return acc

COLORES = {'path1141-0': 'dirt', 'path1141-6': 'tech', 'path1141-9': 'tech',
           'path1370': 'tech', 'path1374': 'straight', 'path1141': 'bridge'}
for it in items:  # otros rojos grandes (diagonal de meta, dlen 686)
    if it['id'] not in COLORES and it['id'] != 'path1137' and \
       fill_of(it['style']) == '#fe0000' and len(it['d']) > 400:
        COLORES[it['id']] = 'straight'
        print('rojo extra:', it['id'], len(it['d']))

print('rasterizando...')
mask_negro = rasterize(['path1137'])
masks_color = {}
for pid, tag in COLORES.items():
    m = rasterize([pid])
    masks_color.setdefault(tag, np.zeros((H, W), dtype=bool))
    masks_color[tag] |= m
    print(f'  {pid} ({tag}): {int(m.sum())} px')
mask_total = mask_negro.copy()
for m in masks_color.values():
    mask_total |= m
# rellena poros internos (islas de anti-even-odd) salvo agujeros grandes
mask_total = ndimage.binary_closing(mask_total, structure=np.ones((5, 5)))

print('esqueletonizando...')
skel = skeletonize(mask_total)
dist = ndimage.distance_transform_edt(mask_total)
ys, xs = np.nonzero(skel)
pix = set(zip(map(int, ys), map(int, xs)))
print('esqueleto:', len(pix), 'px')

def neighbors(p, S):
    y, x = p
    out = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            q = (y + dy, x + dx)
            if q in S:
                out.append(q)
    return out

def prune_tails(S, max_len):
    S = set(S)
    while True:
        endpoints = [p for p in S if len(neighbors(p, S)) <= 1]
        removed = False
        for p in endpoints:
            trail = [p]; cur, prev = p, None
            while True:
                nb = [q for q in neighbors(cur, S) if q != prev]
                if len(nb) != 1:
                    break
                prev, cur = cur, nb[0]
                trail.append(cur)
                if len(trail) > max_len:
                    break
            if len(trail) <= max_len:
                for q in trail[:-1]:
                    S.discard(q)
                removed = True
        if not removed:
            return S

pix = prune_tails(pix, 30 * SCALE)
print('tras poda:', len(pix))

# --- aristas del grafo ---
deg = {p: len(neighbors(p, pix)) for p in pix}
junc = {p for p, d in deg.items() if d >= 3}

def trace_edge(j, first, jset, S):
    path = [j, first]
    prev, cur = j, first
    while cur not in jset:
        nb = [q for q in neighbors(cur, S) if q != prev]
        if not nb:
            return path, None
        nxt = nb[0]
        prev, cur = cur, nxt
        path.append(cur)
    return path, cur

edges = []
seen_dirs = set()
for j in junc:
    for nb in neighbors(j, pix):
        if (j, nb) in seen_dirs:
            continue
        e, endj = trace_edge(j, nb, junc, pix)
        seen_dirs.add((j, nb))
        if endj is not None and len(e) > 2:
            seen_dirs.add((endj, e[-2]))
            edges.append(e)
uniq, seenk = [], set()
for e in edges:
    k = (min(e[0], e[-1]), max(e[0], e[-1]), len(e))
    if k not in seenk:
        seenk.add(k); uniq.append(e)
edges = sorted(uniq, key=len, reverse=True)

def frac_in(e, m):
    return sum(1 for (y, x) in e if m[y, x]) / max(1, len(e))

print('aristas grandes:')
for e in edges[:12]:
    print(f'  len={len(e)} ini={e[0]} fin={e[-1]}')

# --- bucle principal: no hay pit en el mapa; las uniones son autocruces ---
pit_edge = None
S2 = set(pix)
S2 = prune_tails(S2, 40 * SCALE)
deg2 = {p: len(neighbors(p, S2)) for p in S2}
bad = [p for p, d in deg2.items() if d != 2]
print('ciclo: px=', len(S2), ' pix con grado!=2:', len(bad))

# recorre el ciclo tolerando pequenos grumos (elige vecino no visitado mas lejano al previo)
start = next(iter(S2))
loop = [start]
visited = {start}
prev, cur = None, start
while True:
    nb = [q for q in neighbors(cur, S2) if q != prev and q not in visited]
    if not nb:
        nb_all = [q for q in neighbors(cur, S2) if q != prev]
        if start in nb_all and len(loop) > 100:
            break
        if not nb_all:
            break
        nb = nb_all
    if prev is not None:
        nxt = max(nb, key=lambda q: (q[0]-prev[0])**2 + (q[1]-prev[1])**2)
    else:
        nxt = nb[0]
    prev, cur = cur, nxt
    if cur == start and len(loop) > 100:
        break
    loop.append(cur)
    visited.add(cur)
print('bucle recorrido:', len(loop), 'px de', len(S2))

def to_svg(p):
    return (p[1] / SCALE, p[0] / SCALE)

loop_svg = [to_svg(p) for p in loop]

def resample_closed(pts, n):
    L = [0.0]
    for i in range(1, len(pts) + 1):
        a = pts[i - 1]; b = pts[i % len(pts)]
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = L[-1]
    out, j = [], 0
    for k in range(n):
        s = total * k / n
        while L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        a = pts[j % len(pts)]; b = pts[(j + 1) % len(pts)]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out, total

def smooth_closed(pts, win=15, passes=2):
    n = len(pts)
    h = win // 2
    for _ in range(passes):
        out = []
        for i in range(n):
            sx = sy = 0.0
            for k in range(-h, h + 1):
                p = pts[(i + k) % n]
                sx += p[0]; sy += p[1]
            out.append((sx / win, sy / win))
        pts = out
    return pts

N = 2600
loop_rs, _ = resample_closed(loop_svg, 6000)
loop_sm = smooth_closed(loop_rs)
loop_fin, total_svg = resample_closed(loop_sm, N)
m_u = LARGO_M / total_svg
print(f'longitud: {total_svg:.1f} u svg -> {m_u:.4f} m/u')

prio = ['dirt', 'tech', 'straight', 'bridge']
def surface_at(x, y):
    xi = min(max(int(round(x * SCALE)), 0), W - 1)
    yi = min(max(int(round(y * SCALE)), 0), H - 1)
    for tag in prio:
        if masks_color.get(tag) is not None and masks_color[tag][yi, xi]:
            return tag
    return 'norm'

def width_at(x, y):
    xi = min(max(int(round(x * SCALE)), 0), W - 1)
    yi = min(max(int(round(y * SCALE)), 0), H - 1)
    return 2.0 * dist[yi, xi] / SCALE

samples = [{'x': round(x, 2), 'y': round(y, 2), 'sec': surface_at(x, y),
            'w': round(width_at(x, y), 2)} for (x, y) in loop_fin]

# --- circulos de curva: por geometria (radio ~8.33), por SUBTRAZADO ---
circles = []
for it in items:
    if 'a 8.33' not in it['d'] and 'A 8.33' not in it['d']:
        continue
    p = parse_path(it['d'])
    for sp in p.continuous_subpaths():
        try:
            xmin, xmax, ymin, ymax = sp.bbox()
        except Exception:
            continue
        w_ = xmax - xmin; h_ = ymax - ymin
        if 14 < w_ < 20 and 14 < h_ < 20:  # circulo de diametro ~16.7
            cx, cy = mat_apply(it['M'], (xmin + xmax) / 2, (ymin + ymax) / 2)
            circles.append((cx, cy))
# dedupe (algunos vienen duplicados con relleno distinto)
dedup = []
for c in circles:
    if not any((c[0]-d[0])**2 + (c[1]-d[1])**2 < 9 for d in dedup):
        dedup.append(c)
circles = dedup
print('marcadores de curva:', len(circles))

# --- bandera ---
flag_pts = []
for it in items:
    if it['id'].startswith('rect1149'):
        m = re.match(r'\s*m\s+([-0-9.e]+),([-0-9.e]+)', it['d'])
        if m:
            flag_pts.append(mat_apply(it['M'], float(m.group(1)), float(m.group(2))))
flag = (sum(p[0] for p in flag_pts) / len(flag_pts),
        sum(p[1] for p in flag_pts) / len(flag_pts)) if flag_pts else None
print('bandera:', flag)

def nearest_idx(pt):
    return min(range(N), key=lambda i: (samples[i]['x'] - pt[0])**2 + (samples[i]['y'] - pt[1])**2)

i_flag = nearest_idx(flag)
circ_idx = [(nearest_idx(c), c) for c in circles]

def order_for(direction):
    lst = []
    for idx, c in circ_idx:
        rel = (idx - i_flag) % N if direction > 0 else (i_flag - idx) % N
        lst.append((rel, c, idx))
    lst.sort()
    return lst

# El SVG oficial solo dibuja 46 circulos: faltan las curvas 12, 13, 34 y 37
# (confirmado con zoom sobre el render). Con 46 marcadores las anclas son:
# izquierda=3 (03), arriba=16 (18 oficial), abajo=39 (43 oficial).
VIRTUALES = [12, 13, 34, 37]
best = None
for direction in (+1, -1):
    lst = order_for(direction)
    xs_ = [c[1][0] for c in lst]; ys_ = [c[1][1] for c in lst]
    pos_left = xs_.index(min(xs_)) + 1
    pos_top = ys_.index(min(ys_)) + 1
    pos_bot = ys_.index(max(ys_)) + 1
    print(f'sentido {direction}: izq->{pos_left} (esp 3), arriba->{pos_top} (esp 16), abajo->{pos_bot} (esp 39)')
    if pos_left == 3 and pos_top == 16 and pos_bot == 39:
        best = (direction, lst)
def save_debug(corners_list, ordered_list, pit_pts):
    dbg = Image.new('RGB', (W // 4, H // 4), (250, 250, 250))
    def blit(img, mask, color):
        arr = np.array(img)
        small = mask[::4, ::4][:arr.shape[0], :arr.shape[1]]
        arr[:small.shape[0], :small.shape[1]][small] = color
        return Image.fromarray(arr)
    dbg = blit(dbg, mask_total, (205, 205, 205))
    tints = {'tech': (0, 163, 221), 'dirt': (232, 184, 0),
             'straight': (232, 17, 45), 'bridge': (255, 255, 255)}
    for tag, m in masks_color.items():
        dbg = blit(dbg, m, tints[tag])
    dp = ImageDraw.Draw(dbg)
    for i, s in enumerate(ordered_list):
        dp.point((s['x'] * SCALE / 4, s['y'] * SCALE / 4), fill=(0, 150, 0))
    for (x, y) in pit_pts:
        dp.point((x * SCALE / 4, y * SCALE / 4), fill=(160, 0, 160))
    for c in corners_list:
        dp.ellipse([c['x'] * 2 - 7, c['y'] * 2 - 7, c['x'] * 2 + 7, c['y'] * 2 + 7],
                   outline=(0, 0, 0))
        dp.text((c['x'] * 2, c['y'] * 2), str(c['n']), fill=(0, 0, 0), anchor='mm')
    dp.ellipse([flag[0] * 2 - 4, flag[1] * 2 - 4, flag[0] * 2 + 4, flag[1] * 2 + 4],
               fill=(255, 0, 255))
    dbg.save(OUT_DBG)
    print('debug ->', OUT_DBG)

if best is None:
    save_debug([{'n': i, 'x': c[0], 'y': c[1]} for i, (rel, c, idx) in enumerate(order_for(-1), 1)],
               samples, [])
    raise SystemExit('ANCLAS NO COINCIDEN - revisar debug_extraccion.png')

direction, lst = best

if direction > 0:
    ordered = samples[i_flag:] + samples[:i_flag]
else:
    ordered = [samples[i_flag]] + samples[:i_flag][::-1] + samples[i_flag + 1:][::-1]

# numeracion oficial: 1..50 saltando las virtuales para los 46 circulos reales
oficiales_reales = [n for n in range(1, 51) if n not in VIRTUALES]
corners = []
for i, (rel, c, idx) in enumerate(lst):
    corners.append({'n': oficiales_reales[i], 'x': round(c[0], 2),
                    'y': round(c[1], 2), 's_idx': rel})

# curvas virtuales en los picos de curvatura de su intervalo
def curvature(i, w=4):
    a = ordered[(i - w) % N]; b = ordered[i]; c2 = ordered[(i + w) % N]
    v1 = (b['x'] - a['x'], b['y'] - a['y'])
    v2 = (c2['x'] - b['x'], c2['y'] - b['y'])
    ang = math.atan2(v1[0]*v2[1] - v1[1]*v2[0], v1[0]*v2[0] + v1[1]*v2[1])
    return abs(ang)

s_of = {c['n']: c['s_idx'] for c in corners}
def peaks_between(n_a, n_b, k):
    ia, ib = s_of[n_a], s_of[n_b]
    idxs = list(range(ia + 8, ib - 7))
    if not idxs:
        idxs = list(range(ia + 1, ib))
    scored = sorted(idxs, key=curvature, reverse=True)
    chosen = []
    for i in scored:
        if all(abs(i - j) > 10 for j in chosen):
            chosen.append(i)
        if len(chosen) == k:
            break
    return sorted(chosen)

for n_a, n_b, virt in [(11, 14, [12, 13]), (33, 35, [34]), (36, 38, [37])]:
    pk = peaks_between(n_a, n_b, len(virt))
    for n_v, i_v in zip(virt, pk):
        corners.append({'n': n_v, 'x': ordered[i_v]['x'], 'y': ordered[i_v]['y'],
                        's_idx': i_v, 'virtual': True})
corners.sort(key=lambda c: c['n'])
seq_ok = all(corners[i]['s_idx'] <= corners[i + 1]['s_idx'] for i in range(len(corners) - 1))
print('50 curvas numeradas; s_idx monotono:', seq_ok)

# pit lane
pit_svg = []
if pit_edge:
    pit_svg = [to_svg(p) for p in pit_edge]
    if direction < 0:
        pit_svg = pit_svg[::-1]
    pit_svg = [(round(x, 2), round(y, 2)) for x, y in pit_svg[::4]]

data = {
    'version': '1.0-svg-exacto',
    'fuente': 'Layout_Porto_Corsa_Grand_Prix.svg (wiki, esqueleto raster 8x)',
    'viewBox': [500.0, 551.673],
    'largo_objetivo_m': LARGO_M,
    'largo_svg': round(total_svg, 2),
    'm_por_unidad': round(m_u, 5),
    'meta': {'x': round(flag[0], 2), 'y': round(flag[1], 2)},
    'n_muestras': N,
    'muestras': ordered,
    'curvas': corners,
    'pit_lane': pit_svg,
}
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
with open(OUT_JS, 'w', encoding='utf-8') as f:
    f.write('const TRAZADO = ')
    json.dump(data, f, ensure_ascii=False)
    f.write(';\n')

print('secciones:', dict(Counter(s['sec'] for s in ordered)))

# --- imagen de depuracion ---
save_debug(corners, ordered, pit_svg)
print('OK ->', OUT_JSON)
