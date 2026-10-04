"""revisar_urbanismo_plot.py - dibuja el MAPA de urbanismo por baldosas de 420 m
(misma reja que renderizar_inspeccion.py) a partir de renders/qa/huellas.json y
renders/qa/urbanismo_informe.json (los escribe revisar_urbanismo.py en Blender).

  python revisar_urbanismo_plot.py            (python del sistema, matplotlib)
  env GEOM = geometria_3d.json (relieve y costa; defecto 03_blender/geometria_3d.json)
  env PLOT_SOLO = r3c2,r1c4  para repetir baldosas concretas

Salida: renders/qa/urbanismo_mapa_<rNcM>_x<cx>_y<cy>.png por baldosa con tierra
o pista (relieve, costa, pista, pit lane, calles/caminos con su ancho, muros,
casas con la fachada marcada, arboles, props) y los FALLOS en rojo (avisos en
naranja), mas renders/qa/urbanismo_mapa_global.png con todo el mapa.
"""
import json
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon

BASE = 'E:/Escritorio/claude-pc/arnau-aseto-corsa'
DIR = BASE + '/03_blender'
OUT = DIR + '/renders/qa'
GEOM = os.environ.get('GEOM', DIR + '/geometria_3d.json')
H = json.load(open(OUT + '/huellas.json', encoding='utf-8'))
I = json.load(open(OUT + '/urbanismo_informe.json', encoding='utf-8'))
G = json.load(open(GEOM, encoding='utf-8'))
T = G['terreno']
Z = np.array(T['z'], dtype=float).reshape(T['ny'], T['nx'])
X = T['x0'] + np.arange(T['nx']) * T['cell']
Y = T['y0'] + np.arange(T['ny']) * T['cell']
S = G['muestras']
TILE = 420.0
x0, y0 = T['x0'], T['y0']
W, Hh = T['nx'] * T['cell'], T['ny'] * T['cell']
ncol, nrow = int(math.ceil(W / TILE)), int(math.ceil(Hh / TILE))
COL_CALLE = {'asfalto': '#3c3c3c', 'adoquin': '#a08c78', 'tierra': '#b8905c', 'muelle': '#8a8a7e',
             'calles': '#6e6e6e', 'travesias': '#6e6e6e', 'rampas': '#8c7a5a', 'escaleras': '#b0a090'}
ABREV = {'casa_casa': 'CC', 'casa_calle': 'Cc', 'casa_camino': 'Cm', 'casa_pista': 'CP', 'casa_pitlane': 'Cp',
         'casa_muro': 'CM', 'muro_atraviesa_casa': 'MX', 'arbol_casa': 'AC', 'arbol_calle': 'Ac',
         'arbol_camino': 'Am', 'arbol_pista': 'AP', 'arbol_pitlane': 'Ap', 'prop_casa': 'PC',
         'prop_pista': 'PP', 'prop_pitlane': 'Pp', 'prop_calle': 'Pc', 'prop_camino': 'Pm',
         'camino_sin_destino': 'SD',
         'casa_enterrada': 'EN', 'casa_flotante': 'FL', 'casa_sin_suelo': 'SS',
         'objeto_fuera_del_terreno': 'FT', 'objeto_sin_apoyo': 'SA', 'objeto_sobre_el_mar': 'OM',
         'objeto_junto_a_puente': 'JP', 'objeto_salto_grande': 'SG', 'objeto_bajo_superficie': 'BS'}


def tiene_tierra(cx, cy):
    for q in S[::4]:
        if abs(q['x'] - cx) < TILE / 2 and abs(q['y'] - cy) < TILE / 2:
            return True
    for dx in (-0.4, -0.2, 0.0, 0.2, 0.4):
        for dy in (-0.4, -0.2, 0.0, 0.2, 0.4):
            i = int((cx + dx * TILE - x0) / T['cell'])
            j = int((cy + dy * TILE - y0) / T['cell'])
            if 0 <= i < T['nx'] and 0 <= j < T['ny'] and Z[j, i] > 0.5:
                return True
    return False


def banda(pts, cerrada=False):
    """Poligono de una cinta: pts = [[x, y, w, ...]] -> borde izq + borde der invertido."""
    n = len(pts)
    izq, der = [], []
    for k in range(n):
        a = pts[(k - 1) % n] if cerrada else pts[max(k - 1, 0)]
        b = pts[(k + 1) % n] if cerrada else pts[min(k + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / l, tx / l
        h = pts[k][2] / 2.0
        izq.append((pts[k][0] + nx * h, pts[k][1] + ny * h))
        der.append((pts[k][0] - nx * h, pts[k][1] - ny * h))
    return izq + der[::-1]


def en_caja(x, y, caja, m=0.0):
    return caja[0] - m <= x <= caja[2] + m and caja[1] - m <= y <= caja[3] + m


def dibujar(ax, caja, detalle=True):
    bx0, by0, bx1, by1 = caja
    ax.contourf(X, Y, Z, levels=[-1000, 0.3], colors=['#d4e6f5'], zorder=0)
    if detalle:
        ax.contour(X, Y, Z, levels=np.arange(10, 300, 10), colors='#cdbfa5', linewidths=0.35, zorder=1)
    ax.contour(X, Y, Z, levels=[0.3], colors='#3f7fc4', linewidths=0.9, zorder=2)
    for rc in H.get('rocas', []):
        rx = [p[0] for p in rc['celdas'] if en_caja(p[0], p[1], caja, 5)]
        ry = [p[1] for p in rc['celdas'] if en_caja(p[0], p[1], caja, 5)]
        if rx:
            ax.scatter(rx, ry, s=PX_M2 * rc['celda_m'] ** 2, marker='s', c='#b9b2a6', lw=0, alpha=0.75, zorder=2.5)
    ax.add_patch(Polygon(banda(H['pista'], cerrada=True), closed=True, fc='#505050', ec='none', zorder=3))
    if H['pit_lane']:
        ax.add_patch(Polygon(banda(H['pit_lane']), closed=True, fc='#6a6a6a', ec='none', zorder=3))
    for c in H['calles']:
        if not any(en_caja(p[0], p[1], caja, 20) for p in c['eje'][::5]):
            continue
        poly = banda([[p[0], p[1], c['ancho']] for p in c['eje']])
        ax.add_patch(Polygon(poly, closed=True, fc=COL_CALLE.get(c['tipo'], '#777777'), ec='#2a2a2a', lw=0.3, zorder=4))
    if detalle:
        cx, cy = [], []
        for m in H['muros']:
            for p in m['celdas']:
                if en_caja(p[0], p[1], caja, 5):
                    cx.append(p[0])
                    cy.append(p[1])
            if m.get('eje') and len(m['eje']) > 1 and any(en_caja(p[0], p[1], caja, 20) for p in m['eje'][::5]):
                ax.plot([p[0] for p in m['eje']], [p[1] for p in m['eje']], color='#5a2d1a', lw=1.1, zorder=6)
        if cx:
            ax.scatter(cx, cy, s=PX_M2, marker='s', c='#7a3b22', lw=0, zorder=5)
    for c in H['casas']:
        if not en_caja(c['cx'], c['cy'], caja, 30):
            continue
        es_casa = c['tipo'] == 'casa'
        ax.add_patch(Polygon(c['esq'], closed=True, fc='#f3d7a8' if es_casa else '#dcb98e', ec='#6b4a1e',
                             lw=0.5 if detalle else 0.2, zorder=7))
        if detalle and c.get('fachada_fiable'):
            e = c['esq']
            ax.plot([e[2][0], e[3][0]], [e[2][1], e[3][1]], color='#1f4fa0', lw=1.6, zorder=8)
    if detalle:
        for a in H['arboles']:
            if en_caja(a['x'], a['y'], caja, 15):
                ax.add_patch(Circle((a['x'], a['y']), max(a['r'], 0.6), fc='#4f9a3f', ec='none', alpha=0.45, zorder=6))
        px = [p['x'] for p in H['props'] if en_caja(p['x'], p['y'], caja, 5)]
        py = [p['y'] for p in H['props'] if en_caja(p['x'], p['y'], caja, 5)]
        ax.scatter(px, py, s=PX_M2 * 2.5, marker='D', c='#2b2b2b', lw=0, zorder=9)
    n_f = {}
    for f in I['fallos']:
        if en_caja(f['x'], f['y'], caja):
            n_f[f['tipo']] = n_f.get(f['tipo'], 0) + 1
            ax.plot(f['x'], f['y'], marker='x', ms=7 if detalle else 4, mew=1.6 if detalle else 0.8, color='#e01010', zorder=20)
            if detalle:
                ax.text(f['x'] + 2.0, f['y'] + 2.0, ABREV.get(f['tipo'], f['tipo'][:3]), color='#b00000', fontsize=5.5, zorder=21)
    if detalle:
        ax.scatter([a['x'] for a in I['avisos'] if en_caja(a['x'], a['y'], caja)],
                   [a['y'] for a in I['avisos'] if en_caja(a['x'], a['y'], caja)],
                   s=22, marker='o', fc='none', ec='#f08a00', lw=1.0, zorder=19)
    ax.set_xlim(bx0, bx1)
    ax.set_ylim(by0, by1)
    ax.set_aspect('equal')
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.grid(True, color='#bbbbbb', lw=0.3, alpha=0.6)
    return n_f


solo = os.environ.get('PLOT_SOLO', '')
solo = set(solo.split(',')) if solo else None
FIG_IN, DPI = 11.0, 140
salidas = []
for r in range(nrow):
    for c in range(ncol):
        cx = x0 + (c + 0.5) * TILE
        cy = y0 + (r + 0.5) * TILE
        tag = 'r%dc%d' % (r, c)
        if (solo and tag not in solo) or not tiene_tierra(cx, cy):
            continue
        caja = (cx - TILE * 0.525, cy - TILE * 0.525, cx + TILE * 0.525, cy + TILE * 0.525)
        PX_M2 = (FIG_IN * 0.8 * 72.0 / (TILE * 1.05)) ** 2       # 1 m2 en puntos^2 (scatter s)
        fig, ax = plt.subplots(figsize=(FIG_IN, FIG_IN), dpi=DPI)
        n_f = dibujar(ax, caja, detalle=True)
        tot = sum(n_f.values())
        titulo = 'URBANISMO %s centro (%d, %d) - %d fallos' % (tag, int(cx), int(cy), tot)
        if n_f:
            titulo += ': ' + ', '.join('%s %d' % (ABREV.get(k, k), v) for k, v in sorted(n_f.items(), key=lambda kv: -kv[1]))
        ax.set_title(titulo, fontsize=9)
        leyenda = ' | '.join('%s=%s' % (v, k) for k, v in ABREV.items() if k in n_f)
        if leyenda:
            fig.text(0.5, 0.012, leyenda, ha='center', fontsize=6.5, color='#b00000')
        fig.text(0.5, 0.03, 'gris=pista/pit, cintas=calles y caminos (ancho real), marron=muros, beige=casas (azul=fachada), verde=arboles, rombos=props, X roja=fallo, o naranja=aviso', ha='center', fontsize=6.5)
        fn = OUT + '/urbanismo_mapa_%s_x%d_y%d.png' % (tag, int(cx), int(cy))
        fig.savefig(fn, bbox_inches='tight')
        plt.close(fig)
        salidas.append(fn)
        print('baldosa %s centro (%d, %d): %d fallos' % (tag, int(cx), int(cy), tot))

# mapa global (limites = reja de baldosas, para que se vea lo que cae FUERA del terreno)
PX_M2 = 0.6
GW, GH = ncol * TILE, nrow * TILE
fig, ax = plt.subplots(figsize=(14, 14 * GH / GW), dpi=120)
n_f = dibujar(ax, (x0, y0, x0 + GW, y0 + GH), detalle=False)
ax.plot([x0, x0 + W, x0 + W, x0, x0], [y0, y0, y0 + Hh, y0 + Hh, y0], color='#c04000', lw=0.8, ls='--', zorder=14)
ax.text(x0 + 10, y0 + Hh + 8, 'borde del TERRENO (fuera no hay suelo)', fontsize=7, color='#c04000')
for r in range(nrow):
    for c in range(ncol):
        cx, cy = x0 + (c + 0.5) * TILE, y0 + (r + 0.5) * TILE
        ax.plot([cx - TILE / 2, cx + TILE / 2, cx + TILE / 2, cx - TILE / 2, cx - TILE / 2],
                [cy - TILE / 2, cy - TILE / 2, cy + TILE / 2, cy + TILE / 2, cy - TILE / 2], color='#888888', lw=0.4, zorder=15)
        ax.text(cx - TILE / 2 + 8, cy + TILE / 2 - 22, 'r%dc%d' % (r, c), fontsize=7, color='#444444', zorder=16)
partes = ['%s %d' % (k, v) for k, v in sorted(I['resumen'].items(), key=lambda kv: -kv[1])]
lineas = ['URBANISMO mapa global - %d fallos' % I['total_fallos']]
for k in range(0, len(partes), 7):
    lineas.append(', '.join(partes[k:k + 7]))
ax.set_title(chr(10).join(lineas), fontsize=8)
fn = OUT + '/urbanismo_mapa_global.png'
fig.savefig(fn, bbox_inches='tight')
plt.close(fig)
salidas.append(fn)
print('OK %d mapas' % len(salidas))
