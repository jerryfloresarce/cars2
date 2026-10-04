# -*- coding: utf-8 -*-
"""kn5_ensayo.py - escribe 5 KN5 v5 MINUSCULOS de ensayo (uno por hipotesis) para probarlos en el PC del amigo,
que es el unico sitio donde hay Assetto Corsa. Python del sistema (3.12 + numpy + PIL), SIN bpy.

    python 03_blender/_rev/kn5_ensayo.py                 escribe los 5, los valida con 04_export/kn5_check.py y hace el zip
    python 03_blender/_rev/kn5_ensayo.py --solo a,d      solo esos ensayos
    python 03_blender/_rev/kn5_ensayo.py --sin-check     no lanza kn5_check (solo escribe)

Salida: 03_blender/_rev/kn5_prueba/ensayos/
    content/tracks/ensayo_<x>/{ensayo_<x>.kn5, ui/ui_track.json, data/surfaces.ini, data/map.ini, map.png}  (carpeta de pista
    lista para copiar encima de assettocorsa/), texturas/ (las imagenes embebidas, para mirarlas), informes/ (kn5_check de cada
    kn5), LEEME.txt (para el amigo) y ensayos_porto_corsa.zip (todo lo anterior).
Hipotesis: (a) ksMultilayer_fresnel_nm con txMask 2048 + 4 detalles + txDetailNM; (b) ksPerPixelAT con PNG RGBA (alfa test);
(c) ksTree (planos en X, normales arriba); (d) PNG 2048 con UV de usuario + DDS 1024 con mipmaps de colores; (e) nodo ANIM_
con matriz propia + castShadows con alfa test.
Formato: EXACTAMENTE el de 04_export/kn5_writer_opt.py / kn5_check.py (sc6969 + int32 5; texturas; materiales {nombre, shader,
u8 blend, u8 alphaTested, i32 depth, props (A, B2, C3, D4), samplers (nombre, slot, textura)}; nodos dummy con matriz
16f m[col][row] por filas y mallas pos3 nrm3 uv2 tan3 + indices u16). Ejes KN5: x derecha, y arriba, z = direccion de marcha.
Cada pista: recta 1ROAD_ de 20 x 260 m, kerbs, 1GRASS_ de 1200 x 1200 m, muros de cierre invisibles (60 m: lo exige la
comprobacion 6 de kn5_check), 45 dummies AC_* (20 START + 20 PIT + 4 TIME + HOTLAP: la comprobacion 1 exige los 45) y los
planos de prueba de 4 triangulos (abanico) con el material de la hipotesis delante del box AC_PIT_0.
"""
import io
import json
import math
import os
import struct
import subprocess
import sys
import time
import zipfile
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
sys.path.insert(0, os.path.join(BASE, '03_blender'))
sys.path.insert(0, os.path.join(BASE, '04_export'))
import paleta  # noqa: E402

OUT = os.path.join(BASE, '03_blender', '_rev', 'kn5_prueba', 'ensayos')
KN5_CHECK = os.path.join(BASE, '04_export', 'kn5_check.py')
FUENTE = 'C:/Windows/Fonts/arial.ttf'
FUENTE_B = 'C:/Windows/Fonts/arialbd.ttf'

# ------------------------------------------------------------------------------------------------ geometria comun
ROAD_W, ROAD_Z0, ROAD_Z1 = 20.0, -130.0, 130.0      # recta: x in [-10, 10], z in [-130, 130], y = 0
KERB_W = 0.6
GRASS = 600.0                                         # 1GRASS_ hasta +-600 m
CIERRE_H = 60.0                                       # muro invisible de cierre (kn5_check 6: Y max de fisica 50..400)
MAT_KS = (0.45, 0.60)                                 # ksAmbient, ksDiffuse de color_ac.FAMILIAS

# ------------------------------------------------------------------------------------------------ escritura binaria


class Writer:
    def __init__(self, f):
        self.f = f

    def u8(self, v):
        self.f.write(struct.pack('<B', int(v)))

    def i32(self, v):
        self.f.write(struct.pack('<i', int(v)))

    def f32(self, v):
        self.f.write(struct.pack('<f', float(v)))

    def floats(self, vals):
        self.f.write(struct.pack('<%df' % len(vals), *[float(v) for v in vals]))

    def string(self, s):
        b = s.encode('utf-8')
        self.i32(len(b))
        self.f.write(b)

    def blob(self, b):
        self.i32(len(b))
        self.f.write(b)

    def matrix(self, M):
        """M = matriz 4x4 de vector columna (p' = M p, traslacion en M[:3, 3]); en el fichero van las columnas de M
        seguidas (= filas de M.T): kn5_check.matriz_desde_floats hace reshape(4,4).T, y kn5_writer_opt escribe
        m[col][row] con row externo, que es lo mismo."""
        self.floats(np.asarray(M, np.float64).T.reshape(-1))


def matriz(tx=0.0, ty=0.0, tz=0.0, giro_y_deg=0.0):
    """Matriz 4x4 (vector columna): giro sobre el eje vertical Y y traslacion."""
    a = math.radians(giro_y_deg)
    c, s = math.cos(a), math.sin(a)
    M = np.eye(4)
    M[0, 0], M[0, 2], M[2, 0], M[2, 2] = c, s, -s, c
    M[:3, 3] = (tx, ty, tz)
    return M


# ------------------------------------------------------------------------------------------------ mallas


def _tangente(n):
    t = np.cross(n, (0.0, 1.0, 0.0))
    ln = float(np.linalg.norm(t))
    return (1.0, 0.0, 0.0) if ln < 1e-4 else tuple(t / ln)


class Malla:
    """Una malla KN5: vertices (pos3 nrm3 uv2 tan3) + indices. Winding: cross(b-a, c-a) . normal > 0 (regla que
    kn5_check usa para 1ROAD_ y que cumple el KN5 real validado en el PC del amigo)."""

    def __init__(self, nombre, material, cast=1, renderable=1):
        self.nombre, self.material, self.cast, self.renderable = nombre, material, cast, renderable
        self.V, self.I = [], []

    def vert(self, p, n, uv):
        n = np.asarray(n, float)
        n = n / (np.linalg.norm(n) or 1.0)
        self.V.append(tuple(map(float, p)) + tuple(map(float, n)) + tuple(map(float, uv)) + _tangente(n))
        return len(self.V) - 1

    def tri(self, a, b, c, normal):
        pa, pb, pc = (np.asarray(self.V[k][:3]) for k in (a, b, c))
        if float(np.dot(np.cross(pb - pa, pc - pa), normal)) < 0:
            b, c = c, b
        self.I += [a, b, c]

    def quad(self, esquinas, uvs, normal, abanico=False, normal_vert=None):
        """esquinas: 4 puntos en orden alrededor del cuadrilatero; uvs: sus 4 uv (u, v) en convencion KN5
        (v = 0 arriba de la imagen). normal: orientacion de la cara (decide el winding). normal_vert: normal escrita
        en los vertices si es distinta de la geometrica (ksTree: (0, 1, 0)). abanico=True: vertice central -> 4 triangulos."""
        nv = normal_vert if normal_vert is not None else normal
        ids = [self.vert(p, nv, uv) for p, uv in zip(esquinas, uvs)]
        if abanico:
            c = self.vert(np.mean(np.asarray(esquinas, float), axis=0), nv, np.mean(np.asarray(uvs, float), axis=0))
            for k in range(4):
                self.tri(ids[k], ids[(k + 1) % 4], c, normal)
        else:
            self.tri(ids[0], ids[1], ids[2], normal)
            self.tri(ids[0], ids[2], ids[3], normal)
        return self

    def n_tris(self):
        return len(self.I) // 3


def suelo(nombre, material, x0, x1, z0, z1, y=0.0, uv_m=None, cast=0, renderable=1, abanico=False, uv01=False):
    """Rectangulo horizontal con normal +Y. uv_m: metros por repeticion de la textura (UV = mundo / uv_m);
    uv01: UV 0..1 sobre el rectangulo, u creciendo hacia -X (derecha del que mira a +Z), v = 0 en el borde lejano (+Z)."""
    m = Malla(nombre, material, cast, renderable)
    P = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    if uv01:
        UV = [((x1 - p[0]) / (x1 - x0), (z1 - p[2]) / (z1 - z0)) for p in P]
    else:
        s = uv_m or 1.0
        UV = [(p[0] / s, p[2] / s) for p in P]
    return m.quad(P, UV, (0, 1, 0), abanico=abanico)


def panel_vertical(nombre, material, xc, y0, y1, z, ancho, cast=1, abanico=True, normal_vert=None, giro_deg=0.0):
    """Panel de pie centrado en (xc, z) mirando a -Z (hacia el coche, que arranca en z < 0 mirando a +Z).
    UV: (0,0) arriba a la derecha del que lo mira desde el coche (= +X), u crece hacia -X, v = 0 arriba.
    giro_deg: giro del panel sobre su eje vertical (para los planos en X del ksTree)."""
    m = Malla(nombre, material, cast, 1)
    a = math.radians(giro_deg)
    dx, dz = math.cos(a) * ancho / 2, -math.sin(a) * ancho / 2    # semieje del panel en el plano XZ
    nx, nz = math.sin(a), math.cos(a)                             # normal geometrica = -(giro de -Z)... se fija abajo
    normal = (-nx, 0.0, -nz) if math.cos(a) >= 0 else (nx, 0.0, nz)
    P = [(xc + dx, y1, z + dz), (xc - dx, y1, z - dz), (xc - dx, y0, z - dz), (xc + dx, y0, z + dz)]
    UV = [(0, 0), (1, 0), (1, 1), (0, 1)]
    return m.quad(P, UV, normal, abanico=abanico, normal_vert=normal_vert)


def cubo_mini(nombre, material, d=0.18):
    """Mini-malla hija de cada dummy AC_* (24 v / 36 i, isRenderable = 0), como kn5_writer_opt."""
    m = Malla(nombre, material, cast=0, renderable=0)
    V = [(-d, 0, -d), (d, 0, -d), (d, 0, d), (-d, 0, d), (-d, 2 * d, -d), (d, 2 * d, -d), (d, 2 * d, d), (-d, 2 * d, d)]
    caras = [((0, 1, 2, 3), (0, -1, 0)), ((4, 5, 6, 7), (0, 1, 0)), ((0, 1, 5, 4), (0, 0, -1)),
             ((2, 3, 7, 6), (0, 0, 1)), ((1, 2, 6, 5), (1, 0, 0)), ((0, 3, 7, 4), (-1, 0, 0))]
    for q, n in caras:
        m.quad([V[k] for k in q], [(0, 0), (1, 0), (1, 1), (0, 1)], n)
    return m


def caja_vertical(nombre, material, x0, x1, z0, z1, y0, y1, cast=1, renderable=1):
    """Cuatro paredes verticales (normales hacia dentro de la caja) sin tapa: muros de cierre o barreras."""
    m = Malla(nombre, material, cast, renderable)
    uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    m.quad([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], uv, (0, 0, 1))      # pared z0 mira a +Z
    m.quad([(x1, y1, z1), (x0, y1, z1), (x0, y0, z1), (x1, y0, z1)], uv, (0, 0, -1))     # pared z1 mira a -Z
    m.quad([(x0, y1, z1), (x0, y1, z0), (x0, y0, z0), (x0, y0, z1)], uv, (1, 0, 0))      # pared x0 mira a +X
    m.quad([(x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (x1, y0, z0)], uv, (-1, 0, 0))     # pared x1 mira a -X
    return m


# ------------------------------------------------------------------------------------------------ texturas (PIL)


def _font(tam, negrita=True):
    try:
        return ImageFont.truetype(FUENTE_B if negrita else FUENTE, tam)
    except Exception:
        return ImageFont.load_default()


def png(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def tex_plana(color_srgb8, alpha=None, lado=8):
    im = Image.new('RGBA' if alpha is not None else 'RGB', (lado, lado), tuple(color_srgb8) + ((alpha,) if alpha is not None else ()))
    return png(im)


def tex_kerb():
    im = Image.new('RGB', (64, 16), (230, 230, 225))
    ImageDraw.Draw(im).rectangle([32, 0, 63, 15], fill=(200, 40, 35))
    return png(im)


def tex_hierba():
    a = paleta.srgb8('hierba_seca')
    b = tuple(min(255, int(c * 1.08)) for c in a)
    im = Image.new('RGB', (16, 16), a)
    d = ImageDraw.Draw(im)
    d.rectangle([8, 0, 15, 7], fill=b)
    d.rectangle([0, 8, 7, 15], fill=b)
    return png(im)


def _ruido(rng, h, w, amp):
    return 1.0 + amp * (rng.random((h, w, 1)) - 0.5) * 2


def tex_detalle(letra, nombre_color, lado=512, seed=0):
    """Tile de detalle del multicapa: color de la paleta con grano, letra del canal (R/G/B/A) en el centro y marco fino
    (para contar repeticiones en la foto). Alfa oscuro = nivel especular bajo (LilSki)."""
    rng = np.random.default_rng(seed)
    base = np.asarray(paleta.srgb8(nombre_color), float)
    arr = np.clip(base * _ruido(rng, lado, lado, 0.07), 0, 255).astype(np.uint8)
    im = Image.fromarray(arr, 'RGB').convert('RGBA')
    d = ImageDraw.Draw(im)
    claro = tuple(min(255, int(c * 1.45 + 30)) for c in paleta.srgb8(nombre_color))
    f = _font(int(lado * 0.62))
    bb = d.textbbox((0, 0), letra, font=f)
    d.text(((lado - bb[2] - bb[0]) / 2, (lado - bb[3] - bb[1]) / 2 - bb[1] * 0.1), letra, fill=claro, font=f)
    d.rectangle([0, 0, lado - 1, lado - 1], outline=tuple(int(c * 0.6) for c in base.astype(int)), width=4)
    a = np.array(im)          # copia escribible (np.asarray sobre una Image es de solo lectura)
    a[..., 3] = 25
    return png(Image.fromarray(a, 'RGBA'))


def tex_diffuse_multicapa(lado=1024):
    """txDiffuse del multicapa: gris neutro sRGB 150 con rejilla 8x8 fina (se ve si AC lee el diffuse y su UV), alfa 25."""
    im = Image.new('RGBA', (lado, lado), (150, 150, 150, 25))
    d = ImageDraw.Draw(im)
    for k in range(9):
        p = min(lado - 1, k * lado // 8)
        d.line([(p, 0), (p, lado)], fill=(110, 110, 110, 25), width=3)
        d.line([(0, p), (lado, p)], fill=(110, 110, 110, 25), width=3)
    d.text((lado * 0.36, lado * 0.02), 'DIFFUSE', fill=(90, 90, 90, 25), font=_font(lado // 14))
    return png(im)


def tex_mask(lado=2048):
    """txMask RGBA 2048 'sin tintar': cuadrantes R (arriba-izq), G (arriba-der), B (abajo-izq), A (abajo-der) con
    transicion suave de 48 texeles, disco central con los 4 canales al 25 % y rayas de B de 2 texeles cada 16 en el
    cuadrante R (si AC reduce la mascara a 1024/512 las rayas desaparecen). Suma por texel = 255."""
    v, u = np.mgrid[0:lado, 0:lado].astype(np.float32) / (lado - 1)
    t = 48.0 / lado

    def paso(x, borde):      # smoothstep de anchura 2t centrado en borde
        s = np.clip((x - (borde - t)) / (2 * t), 0, 1)
        return s * s * (3 - 2 * s)
    der, aba = paso(u, 0.5), paso(v, 0.5)
    R = (1 - der) * (1 - aba)
    G = der * (1 - aba)
    B = (1 - der) * aba
    A = der * aba
    # rayas finas de 'tierra' (B) en el cuadrante R: 2 texeles cada 16, en una banda de 160 texeles
    yy, xx = np.mgrid[0:lado, 0:lado]
    rayas = (yy % 16 < 2) & (yy > lado * 0.30) & (yy < lado * 0.30 + 160) & (xx > lado * 0.08) & (xx < lado * 0.42)
    B = np.where(rayas, 1.0, B)
    R = np.where(rayas, 0.0, R)
    # disco central: mezcla de los cuatro
    disco = paso(-np.hypot(u - 0.5, v - 0.5), -0.14)     # 1 dentro de r < 0.14, suave fuera
    for c in (R, G, B, A):
        np.copyto(c, c * (1 - disco) + 0.25 * disco)
    S = R + G + B + A
    S[S == 0] = 1.0
    arr = np.stack([R, G, B, A], axis=-1) / S[..., None]
    return png(Image.fromarray(np.clip(np.round(arr * 255), 0, 255).astype(np.uint8), 'RGBA'))


def tex_normal_plana(lado=256):
    """txDetailNM: normal plana (128,128,255) con 4 hoyuelos esfericos (si AC usa la normal se ven como boton)."""
    y, x = np.mgrid[0:lado, 0:lado].astype(np.float32)
    n = np.zeros((lado, lado, 3), np.float32)
    n[..., 2] = 1.0
    for cx, cy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
        dx, dy = (x / lado - cx) / 0.12, (y / lado - cy) / 0.12
        r2 = dx * dx + dy * dy
        dentro = r2 < 1.0
        nz = np.sqrt(np.clip(1 - r2, 0, 1))
        n[dentro, 0] = -dx[dentro] * 0.8
        n[dentro, 1] = dy[dentro] * 0.8
        n[dentro, 2] = nz[dentro]
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return png(Image.fromarray(np.clip(np.round((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8), 'RGB'))


def tex_hojas(lado=1024):
    """PNG RGBA de arbol estilizado para alfa test: tronco + copa de 5 lobulos (oliva/salvia), bordes con alfa en rampa
    de 14 px (ksAlphaRef 0.5 decide), un HALO de alfa 90/255 (= 0.35: invisible si el alfa test funciona, visible si AC
    mezcla) y 3 agujeros nitidos. El RGB de las zonas transparentes es salvia (bleed: sin bordes negros)."""
    y, x = np.mgrid[0:lado, 0:lado].astype(np.float32) / lado
    alpha = np.zeros((lado, lado), np.float32)
    rgb = np.zeros((lado, lado, 3), np.float32)
    rgb[:] = paleta.srgb8('salvia')
    lob = ((0.50, 0.42, 0.26), (0.32, 0.52, 0.19), (0.68, 0.52, 0.19), (0.40, 0.30, 0.17), (0.60, 0.30, 0.17))
    oliva, salv = np.asarray(paleta.srgb8('oliva_oscuro'), float), np.asarray(paleta.srgb8('salvia'), float)
    for i, (cx, cy, r) in enumerate(lob):
        d = np.hypot(x - cx, y - cy)
        a = np.clip((r - d) / (14.0 / lado), 0, 1)
        col = oliva if i % 2 == 0 else salv * 0.92
        rgb = np.where((a > alpha)[..., None], col, rgb)
        alpha = np.maximum(alpha, a)
    # halo translucido (alfa 0.35) alrededor de la copa
    dh = np.hypot(x - 0.5, y - 0.42)
    halo = (dh < 0.40) & (alpha < 0.05)
    alpha[halo] = 90 / 255.0
    rgb[halo] = (235, 235, 120)          # amarillo claro: si se ve, AC esta mezclando en vez de recortar
    # tronco
    tronco = (np.abs(x - 0.5) < 0.045) & (y > 0.55) & (y < 0.985)
    alpha[tronco] = 1.0
    rgb[tronco] = paleta.srgb8('caliza_sombra')
    # agujeros nitidos
    for cx, cy in ((0.44, 0.40), (0.58, 0.47), (0.50, 0.26)):
        d = np.hypot(x - cx, y - cy)
        alpha[d < 0.025] = 0.0
    arr = np.concatenate([rgb, alpha[..., None] * 255], axis=-1)
    return png(Image.fromarray(np.clip(np.round(arr), 0, 255).astype(np.uint8), 'RGBA'))


def tex_uv_2048(lado=2048):
    """PNG RGB 2048 para UV de usuario y mipmaps: rejilla 8x8 rotulada (A-H / 1-8), flecha y texto ARRIBA/ABAJO/IZQ/DER
    (orientacion de la UV y espejo), tablero de 1 px, de 2 px y anillos de 1 px (sin mipmaps parpadean de lejos)."""
    im = Image.new('RGB', (lado, lado), (232, 230, 220))
    d = ImageDraw.Draw(im)
    c = lado // 8
    for k in range(9):
        p = min(lado - 1, k * c)
        d.line([(p, 0), (p, lado)], fill=(70, 70, 70), width=4)
        d.line([(0, p), (lado, p)], fill=(70, 70, 70), width=4)
    f = _font(c // 4)
    for i in range(8):
        d.text((i * c + c * 0.08, c * 0.04), 'ABCDEFGH'[i], fill=(60, 60, 60), font=f)
        d.text((c * 0.08, i * c + c * 0.5), str(i + 1), fill=(60, 60, 60), font=f)
    fg = _font(c * 3 // 4)
    for txt, pos in (('ARRIBA', (lado * 0.33, c * 0.18)), ('ABAJO', (lado * 0.35, lado - c * 0.95))):
        d.text(pos, txt, fill=(180, 40, 30), font=fg)
    d.text((c * 0.15, lado * 0.46), 'IZQ', fill=(30, 60, 170), font=fg)
    d.text((lado - c * 1.9, lado * 0.46), 'DER', fill=(30, 60, 170), font=fg)
    # flecha hacia arriba en el centro
    cx, w = lado // 2, c * 0.55
    d.polygon([(cx, c * 1.3), (cx - w, c * 2.6), (cx - w / 2, c * 2.6), (cx - w / 2, c * 5.6),
               (cx + w / 2, c * 5.6), (cx + w / 2, c * 2.6), (cx + w, c * 2.6)], fill=(200, 60, 40))
    # celda B2: tablero de 1 px; C2: tablero de 2 px; F2: anillos de 1 px; G7: tablero de 1 px
    def tablero(cx0, cy0, paso):
        yy, xx = np.mgrid[0:c, 0:c]
        t = (((xx // paso) + (yy // paso)) % 2) * 255
        im.paste(Image.fromarray(np.stack([t, t, t], -1).astype(np.uint8), 'RGB'), (cx0 + 2, cy0 + 2))
    tablero(1 * c, 1 * c, 1)
    tablero(2 * c, 1 * c, 2)
    tablero(6 * c, 6 * c, 1)
    yy, xx = np.mgrid[0:c, 0:c]
    r = np.hypot(xx - c / 2, yy - c / 2)
    an = ((r.astype(int) % 2) * 255).astype(np.uint8)
    im.paste(Image.fromarray(np.stack([an, an, an], -1), 'RGB'), (5 * c + 2, 1 * c + 2))
    d.text((1 * c + 8, 2 * c - c * 0.22), 'tablero 1px', fill=(200, 30, 30), font=_font(c // 8))
    d.text((5 * c + 8, 2 * c - c * 0.22), 'anillos 1px', fill=(200, 30, 30), font=_font(c // 8))
    d.text((lado * 0.22, lado * 0.84), 'PNG 2048  ensayo D', fill=(40, 40, 40), font=_font(c // 3))
    return png(im)


MIP_COLORES = [(255, 255, 255), (230, 40, 40), (240, 140, 30), (240, 220, 40), (60, 190, 60), (40, 200, 210),
               (40, 80, 230), (150, 50, 200), (230, 60, 200), (128, 128, 128), (0, 0, 0)]


def dds_mips(lado=1024):
    """DDS sin comprimir (A8R8G8B8) con la cadena completa de mipmaps, cada nivel de un color distinto: nivel 0 =
    tablero de 4 px blanco/negro, 1 rojo, 2 naranja, 3 amarillo, 4 verde, 5 cian, 6 azul, 7 violeta, 8 magenta, 9 gris,
    10 negro. En la foto, las bandas de color sobre el plano dicen que nivel usa AC a cada distancia (y si usa alguno)."""
    niveles = []
    w = lado
    k = 0
    while True:
        if k == 0:
            yy, xx = np.mgrid[0:w, 0:w]
            t = ((((xx // 4) + (yy // 4)) % 2) * 255).astype(np.uint8)
            rgb = np.stack([t, t, t], -1)
        else:
            rgb = np.empty((w, w, 3), np.uint8)
            rgb[:] = MIP_COLORES[min(k, len(MIP_COLORES) - 1)]
        bgra = np.concatenate([rgb[..., 2:3], rgb[..., 1:2], rgb[..., 0:1], np.full((w, w, 1), 255, np.uint8)], -1)
        niveles.append(bgra.tobytes())
        if w == 1:
            break
        w //= 2
        k += 1
    flags = 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000          # CAPS HEIGHT WIDTH PITCH PIXELFORMAT MIPMAPCOUNT
    pf = struct.pack('<8I', 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)   # RGB + ALPHAPIXELS
    caps = 0x8 | 0x1000 | 0x400000                               # COMPLEX TEXTURE MIPMAP
    cab = struct.pack('<7I', 124, flags, lado, lado, lado * 4, 0, len(niveles)) + bytes(44) + pf + struct.pack('<5I', caps, 0, 0, 0, 0)
    assert len(cab) == 124
    return b'DDS ' + cab + b''.join(niveles), len(niveles)


# ------------------------------------------------------------------------------------------------ materiales


def props_ks(amb=MAT_KS[0], dif=MAT_KS[1], spec=0.0, exp=1.0, emis=0.0, aref=0.0, extra=()):
    """Las 6 props de siempre (como kn5_writer_opt: A = valor; ksEmissive tambien en C) + extras (nombre, A, B, C, D)."""
    base = [('ksAmbient', amb), ('ksDiffuse', dif), ('ksSpecular', spec), ('ksSpecularEXP', exp),
            ('ksEmissive', emis), ('ksAlphaRef', aref)]
    out = []
    for n, v in base:
        out.append((n, v, (0.0, 0.0), (v, v, v) if n == 'ksEmissive' else (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)))
    out += list(extra)
    return out


def material(nombre, shader='ksPerPixel', blend=0, alpha_tested=0, depth=0, props=None, samplers=None):
    return {'name': nombre, 'shader': shader, 'blend': blend, 'alpha_tested': alpha_tested, 'depth': depth,
            'props': props if props is not None else props_ks(spec=0.05, exp=10.0),
            'samplers': samplers or []}


def P(nombre, a, b=(0.0, 0.0), c=(0.0, 0.0, 0.0), d=(0.0, 0.0, 0.0, 0.0)):
    return (nombre, a, b, c, d)


# ------------------------------------------------------------------------------------------------ escena de ensayo


class Ensayo:
    def __init__(self, letra, titulo, descripcion):
        self.letra, self.titulo, self.descripcion = letra, titulo, descripcion
        self.nombre = 'ensayo_' + letra
        self.texturas = []          # (nombre, bytes)
        self.materiales = []        # dicts de material()
        self.deco = []              # mallas bajo el dummy DECO (coordenadas mundo)
        self.dummies_extra = []     # (nombre, matriz, [mallas hijas en locales])
        self.notas = []
        self._comunes()

    # -- utilidades
    def tex(self, nombre, data):
        self.texturas.append((nombre, data))
        return nombre

    def mat(self, m):
        self.materiales.append(m)
        return m['name']

    def mat_plano(self, nombre, color_srgb8, cast_props=None):
        t = self.tex('flat_%s.png' % nombre, tex_plana(color_srgb8))
        return self.mat(material(nombre, props=cast_props or props_ks(spec=0.05, exp=10.0), samplers=[('txDiffuse', 0, t)]))

    def _comunes(self):
        self.m_default = self.mat_plano('MAT_default', (128, 128, 128))
        self.m_asfalto = self.mat_plano('MAT_asfalto', (88, 88, 90), props_ks(spec=0.08, exp=20.0))
        self.m_muro = self.mat_plano('MAT_muro', paleta.srgb8('caliza_gris_calido'), props_ks(spec=0.02, exp=8.0))
        t = self.tex('kerb_d.png', tex_kerb())
        self.m_kerb = self.mat(material('MAT_kerb', props=props_ks(spec=0.06, exp=20.0), samplers=[('txDiffuse', 0, t)]))
        t = self.tex('hierba_seca_d.png', tex_hierba())
        self.m_hierba = self.mat(material('MAT_hierba_seca', props=props_ks(spec=0.0, exp=1.0), samplers=[('txDiffuse', 0, t)]))
        x0, x1 = -ROAD_W / 2, ROAD_W / 2
        self.fisica = [
            suelo('1ROAD_recta', self.m_asfalto, x0, x1, ROAD_Z0, ROAD_Z1, uv_m=10.0),
            suelo('1KERB_izq', self.m_kerb, x1, x1 + KERB_W, ROAD_Z0, ROAD_Z1, uv_m=2.0),
            suelo('1KERB_der', self.m_kerb, x0 - KERB_W, x0, ROAD_Z0, ROAD_Z1, uv_m=2.0),
            suelo('1GRASS_izq', self.m_hierba, x1 + KERB_W, GRASS, -GRASS, GRASS, uv_m=40.0),
            suelo('1GRASS_der', self.m_hierba, -GRASS, x0 - KERB_W, -GRASS, GRASS, uv_m=40.0),
            suelo('1GRASS_frente', self.m_hierba, x0 - KERB_W, x1 + KERB_W, ROAD_Z1, GRASS, uv_m=40.0),
            suelo('1GRASS_atras', self.m_hierba, x0 - KERB_W, x1 + KERB_W, -GRASS, ROAD_Z0, uv_m=40.0),
            caja_vertical('1WALL_tope_frente', self.m_muro, x0 - 2, x1 + 2, ROAD_Z1 + 4, ROAD_Z1 + 5, 0.0, 1.0),
            caja_vertical('1WALL_tope_atras', self.m_muro, x0 - 2, x1 + 2, ROAD_Z0 - 5, ROAD_Z0 - 4, 0.0, 1.0),
            caja_vertical('1WALL_cierre_invisible', self.m_default, -GRASS, GRASS, -GRASS, GRASS, 0.0, CIERRE_H,
                          cast=0, renderable=0),
        ]
        # 45 dummies AC_*: parrilla de 2 columnas (x = +-3) cada 5 m, pits en x = +7 cada 6 m, meta en z = +10
        self.ac = []
        for i in range(20):
            self.ac.append(('AC_START_%d' % i, matriz(3.0 if i % 2 == 0 else -3.0, 0.0, -5.0 - 5.0 * i)))
        for i in range(20):
            self.ac.append(('AC_PIT_%d' % i, matriz(7.0, 0.0, -5.0 - 6.0 * i)))
        self.ac += [('AC_TIME_0_L', matriz(11.0, 0.0, 10.0)), ('AC_TIME_0_R', matriz(-11.0, 0.0, 10.0)),
                    ('AC_TIME_1_L', matriz(11.0, 0.0, -125.0)), ('AC_TIME_1_R', matriz(-11.0, 0.0, -125.0)),
                    ('AC_HOTLAP_START_0', matriz(0.0, 0.0, -120.0))]

    # -- escritura
    def escribir(self, ruta):
        with open(ruta, 'wb') as f:
            w = Writer(f)
            f.write(b'sc6969')
            w.i32(5)
            w.i32(len(self.texturas))
            for nombre, data in self.texturas:
                w.i32(1)
                w.string(nombre)
                w.blob(data)
            ids = {}
            w.i32(len(self.materiales))
            for k, m in enumerate(self.materiales):
                ids[m['name']] = k
                w.string(m['name'])
                w.string(m['shader'])
                w.u8(m['blend'])
                w.u8(m['alpha_tested'])
                w.i32(m['depth'])
                w.i32(len(m['props']))
                for (pn, a, b, c, d) in m['props']:
                    w.string(pn)
                    w.f32(a)
                    w.floats(b)
                    w.floats(c)
                    w.floats(d)
                w.i32(len(m['samplers']))
                for (sn, slot, tn) in m['samplers']:
                    w.string(sn)
                    w.i32(slot)
                    w.string(tn)

            def dummy(nombre, n_hijos, M):
                w.i32(1)
                w.string(nombre)
                w.i32(n_hijos)
                w.u8(1)
                w.matrix(M)

            def malla(m):
                V = np.asarray(m.V, '<f4')
                w.i32(2)
                w.string(m.nombre)
                w.i32(0)
                w.u8(1)                      # activo
                w.u8(1 if m.cast else 0)     # castShadows
                w.u8(1)                      # isVisible
                w.u8(0)                      # isTransparent (alfa test NO es transparente)
                w.i32(len(V))
                f.write(np.ascontiguousarray(V).tobytes())
                w.i32(len(m.I))
                f.write(np.asarray(m.I, '<u2').tobytes())
                w.i32(ids[m.material])
                w.i32(0)                     # layer
                w.f32(0.0)                   # lodIn
                w.f32(0.0)                   # lodOut
                Pp = V[:, :3].astype(np.float64)
                c = (Pp.min(0) + Pp.max(0)) / 2
                w.floats(c)
                w.f32(float(np.sqrt(((Pp - c) ** 2).sum(1).max())))
                w.u8(1 if m.renderable else 0)

            n_raiz = len(self.ac) + 1 + 1 + len(self.dummies_extra)
            dummy(self.nombre, n_raiz, np.eye(4))
            for nombre, M in self.ac:
                dummy(nombre, 1, M)
                malla(cubo_mini(nombre, self.m_default))
            dummy('FISICA', len(self.fisica), np.eye(4))
            for m in self.fisica:
                malla(m)
            dummy('DECO', len(self.deco), np.eye(4))
            for m in self.deco:
                malla(m)
            for nombre, M, hijas in self.dummies_extra:
                dummy(nombre, len(hijas), M)
                for m in hijas:
                    malla(m)
        return os.path.getsize(ruta)


# ------------------------------------------------------------------------------------------------ los 5 ensayos


def ensayo_a():
    e = Ensayo('a', 'Ensayo A - multicapa (ksMultilayer_fresnel_nm)',
               'Suelo de 4 texturas mezcladas por mascara 2048: letras R, G, B, A por cuadrante y rayas finas.')
    txd = e.tex('ensayo_a_diffuse.png', tex_diffuse_multicapa())
    txm = e.tex('ensayo_a_mask_2048.png', tex_mask())
    det = [e.tex('ensayo_a_detalle_%s.png' % c, tex_detalle(c, n, seed=k))
           for k, (c, n) in enumerate((('R', 'oliva_oscuro'), ('G', 'hierba_seca'), ('B', 'tierra'), ('A', 'caliza_ocre')))]
    txn = e.tex('ensayo_a_detalle_nm.png', tex_normal_plana())
    # El plano mide 40 m y su UV es 0..1: mult = 8 -> cada detalle se repite 8 veces (tiles de 5 m).
    extra = [P('multR', 8.0), P('multG', 8.0), P('multB', 8.0), P('multA', 8.0),
             P('detailNMMult', 8.0, (8.0, 8.0)),        # [S] el campo exacto (A o B) no esta verificado: van los dos
             P('magicMult', 1.0),                        # [S] citado en foros; CM da 0 a las props ausentes -> se escribe 1
             P('fresnelC', 0.02), P('fresnelEXP', 3.0), P('fresnelMaxLevel', 0.1)]
    m = e.mat(material('MAT_ensayo_multicapa', shader='ksMultilayer_fresnel_nm',
                       props=props_ks(spec=0.05, exp=10.0, extra=extra),
                       samplers=[('txDiffuse', 0, txd), ('txMask', 1, txm), ('txDetailR', 2, det[0]), ('txDetailG', 3, det[1]),
                                 ('txDetailB', 4, det[2]), ('txDetailA', 5, det[3]), ('txDetailNM', 6, txn)]))
    e.deco.append(suelo('ENSAYO_a_suelo_multicapa', m, 12.0, 52.0, 5.0, 45.0, y=0.05, uv01=True, abanico=True))
    e.deco.append(panel_vertical('ENSAYO_a_panel_multicapa', m, 0.0, 0.0, 10.0, 60.0, 16.0))
    e.notas += ['samplers txDiffuse/txMask/txDetailR/G/B/A/txDetailNM [V] (overtake 126166, kn5-obj-converter); slots 0..6 [S]',
                'props multR/G/B/A, detailNMMult, fresnelC/EXP/MaxLevel [V nombres, S valores]; magicMult [S]']
    return e


def _mat_alfa(e, nombre, shader, props, tex_nombre='ensayo_hojas_rgba.png'):
    t = e.tex(tex_nombre, tex_hojas())
    return e.mat(material(nombre, shader=shader, blend=0, alpha_tested=1, depth=0, props=props, samplers=[('txDiffuse', 0, t)]))


def ensayo_b():
    e = Ensayo('b', 'Ensayo B - alfa test (ksPerPixelAT, PNG RGBA)',
               'Arbol recortado de pie: bordes limpios, agujeros nitidos y SIN halo amarillo alrededor de la copa.')
    m = _mat_alfa(e, 'MAT_ensayo_alfa_test', 'ksPerPixelAT', props_ks(spec=0.0, exp=1.0, aref=0.5))
    e.deco.append(panel_vertical('ENSAYO_b_arbol_alfa', m, 0.0, 0.0, 14.0, 50.0, 12.0, cast=0))
    e.notas += ['ksPerPixelAT + alphaTested 1 + ksAlphaRef 0.5 [V: AcTools.Render MaterialsProviderDark l.64, ShadowsRendererBase l.279]',
                'castShadows = 0 a proposito (la sombra se prueba en el ensayo E)']
    return e


def ensayo_c():
    e = Ensayo('c', 'Ensayo C - ksTree (planos en X, normales arriba)',
               'Arbol en X con el shader de arbol de Kunos: se ve desde los dos lados y se ilumina plano.')
    m = _mat_alfa(e, 'MAT_ensayo_kstree', 'ksTree', props_ks(amb=0.4, dif=0.25, spec=0.0, exp=1.0, aref=0.5))
    # dos paneles girados +-45 grados = 4 triangulos (2 por panel), normales de vertice (0, 1, 0) como LilSki/ksEditor
    for k, g in enumerate((45.0, -45.0)):
        e.deco.append(panel_vertical('ENSAYO_c_kstree_%d' % k, m, 0.0, 0.0, 14.0, 50.0, 12.0, cast=0, abanico=False,
                                     normal_vert=(0.0, 1.0, 0.0), giro_deg=g))
    e.notas += ['ksTree [V nombre: AcTools.Render]; props de LilSki (0.4/0.25/0/1/0/0.5) [V foro]; normales (0,1,0) [S: sin ksEditor]',
                'con el giro de 45 grados un panel se ve de frente y el otro de espaldas: dice si AC recorta las caras traseras']
    return e


def ensayo_d():
    e = Ensayo('d', 'Ensayo D - PNG 2048 con UV de usuario + DDS con mipmaps',
               'Panel con rejilla A-H/1-8, flecha y ARRIBA/ABAJO/IZQ/DER; alfombras: la misma rejilla y una de bandas de color.')
    t = e.tex('ensayo_d_uv_2048.png', tex_uv_2048())
    m = e.mat(material('MAT_ensayo_png2048', props=props_ks(spec=0.0, exp=1.0), samplers=[('txDiffuse', 0, t)]))
    e.deco.append(panel_vertical('ENSAYO_d_panel_uv', m, 0.0, 0.0, 10.0, 60.0, 16.0))
    e.deco.append(suelo('ENSAYO_d_suelo_uv', m, 12.0, 52.0, 5.0, 45.0, y=0.05, uv01=True, abanico=True))
    dds, n_mips = dds_mips()
    t2 = e.tex('ensayo_d_mips_1024.dds', dds)
    m2 = e.mat(material('MAT_ensayo_dds_mips', props=props_ks(spec=0.0, exp=1.0), samplers=[('txDiffuse', 0, t2)]))
    e.deco.append(suelo('ENSAYO_d_suelo_mips', m2, -52.0, -12.0, 5.0, 85.0, y=0.05, uv01=True, abanico=True))
    e.notas += ['PNG RGB 2048 embebido tal cual (sin mipmaps propios): se mira si parpadea de lejos y si el texto sale derecho/espejo',
                'DDS A8R8G8B8 sin comprimir con %d niveles de color distinto: las bandas dicen que mip usa AC a cada distancia' % n_mips]
    return e


def ensayo_e():
    e = Ensayo('e', 'Ensayo E - nodo ANIM_ con matriz + castShadows con alfa',
               'Tapa cuadrada flotando a 6 m (girada 30 grados) y arbol de pie: los dos deben proyectar sombra recortada en el suelo.')
    m = _mat_alfa(e, 'MAT_ensayo_alfa_sombra', 'ksPerPixelAT', props_ks(spec=0.0, exp=1.0, aref=0.5))
    # tapa horizontal de 14 x 14 m en coordenadas LOCALES del dummy ANIM_ (dos caras: arriba y abajo, 4 triangulos)
    tapa = Malla('ANIM_rotor_ensayo', m, cast=1, renderable=1)
    h = 7.0
    tapa.quad([(-h, 0, -h), (h, 0, -h), (h, 0, h), (-h, 0, h)], [(0, 1), (1, 1), (1, 0), (0, 0)], (0, 1, 0))
    tapa.quad([(-h, 0, -h), (h, 0, -h), (h, 0, h), (-h, 0, h)], [(0, 1), (1, 1), (1, 0), (0, 0)], (0, -1, 0))
    e.dummies_extra.append(('ANIM_rotor_ensayo', matriz(0.0, 6.0, 55.0, giro_y_deg=30.0), [tapa]))
    e.deco.append(panel_vertical('ENSAYO_e_arbol_sombra', m, -22.0, 0.0, 14.0, 45.0, 12.0, cast=1))
    e.notas += ['dummy ANIM_rotor_ensayo con traslacion (0, 6, 55) y giro de 30 grados sobre Y; malla hija en locales (como TERRENO/AGUA en el writer)',
                'castShadows = 1 con alfa test: sombra recortada [V en el renderizador de CM (ShadowsRendererBase l.274-283); en AC: S]']
    return e


ENSAYOS = {'a': ensayo_a, 'b': ensayo_b, 'c': ensayo_c, 'd': ensayo_d, 'e': ensayo_e}

# ------------------------------------------------------------------------------------------------ carpeta de pista

SURFACES_INI = """[SURFACE_0]
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
"""


def carpeta_pista(e, dir_tracks):
    d = os.path.join(dir_tracks, e.nombre)
    for sub in ('ui', 'data'):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    kn5 = os.path.join(d, e.nombre + '.kn5')
    tam = e.escribir(kn5)
    with open(os.path.join(d, 'data', 'surfaces.ini'), 'w', encoding='ascii') as fh:
        fh.write(SURFACES_INI)
    ui = {'name': e.titulo, 'description': e.descripcion + ' Pista de ENSAYO de Porto Corsa: una recta de 260 m con paneles '
          'de prueba delante del box. Mandar foto desde el coche.', 'tags': ['ensayo', 'test'], 'geotags': [], 'country': 'Italy',
          'city': 'Porto Corsa', 'length': '260', 'width': '20', 'pitboxes': '20', 'run': 'clockwise',
          'author': 'Arnau & Claude', 'version': '0.1', 'year': 2026}
    with open(os.path.join(d, 'ui', 'ui_track.json'), 'w', encoding='utf-8') as fh:
        json.dump(ui, fh, ensure_ascii=False, indent=2)
    # mapa 512 px de +-160 m con la recta y los paneles
    px, ext = 512, 320.0
    esc = ext / px
    im = Image.new('RGBA', (px, px), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)

    def xy(x, z):
        return ((x + ext / 2) / esc, (z + ext / 2) / esc)
    dr.rectangle([xy(-ROAD_W / 2, ROAD_Z0), xy(ROAD_W / 2, ROAD_Z1)], fill=(255, 255, 255, 255))
    for m in e.deco:
        Pp = np.asarray(m.V)[:, [0, 2]]
        dr.rectangle([xy(*Pp.min(0)), xy(*Pp.max(0))], outline=(255, 200, 80, 255), width=2)
    im.save(os.path.join(d, 'map.png'))
    with open(os.path.join(d, 'data', 'map.ini'), 'w') as fh:
        fh.write('[PARAMETERS]\nWIDTH=%d\nHEIGHT=%d\nX_OFFSET=%.3f\nZ_OFFSET=%.3f\nMARGIN=20\nSCALE_FACTOR=%.5f\n'
                 'MAX_SIZE=1600\nDRAWING_SIZE=10\n' % (px, px, ext / 2, ext / 2, esc))
    return kn5, tam


LEEME = """ENSAYOS PORTO CORSA: 5 pistas de prueba minusculas (una recta con paneles), una por cosa que necesitamos ver en TU Assetto Corsa.
1. Instala igual que el circuito: arrastra ensayos_porto_corsa.zip a Content Manager, o copia la carpeta "content" encima de assettocorsa/ (quedan content/tracks/ensayo_a ... ensayo_e).
2. Entra en Practice con cualquier coche en la pista "Ensayo A", a las 13:00 y con cielo despejado. Sales en el box mirando hacia los paneles de prueba.
3. Haz una foto de frente a los paneles desde el coche sin moverte y otra acercandote a unos 10 m (F8 guarda la captura en Documents/Assetto Corsa/screens). Si algo sale negro, blanco, invisible o parpadea, foto tambien.
4. Repite con Ensayo B, C, D y E: cinco pistas, unas diez fotos en total. Las alfombras del suelo estan a los lados de la recta, pisa la hierba para verlas de cerca.
5. Que miramos: A) suelo con letras R, G, B y A por cuadrantes y rayas finas (texturas mezcladas); B) arbol recortado sin halo amarillo; C) arbol en X (se ve por los dos lados?); D) panel con flecha y ARRIBA/ABAJO/IZQ/DER (se lee derecho o en espejo? parpadea de lejos?) y alfombra de bandas de colores (que colores ves de cerca a lejos?); E) tapa cuadrada flotando a 6 m y un arbol: miran si su sombra en el suelo tiene la forma recortada.
6. Dinos tambien si tienes Custom Shaders Patch (CSP) activado y su version (Content Manager > Settings > CSP), y los FPS que marca en cada ensayo.
7. Si una pista no carga o AC se cierra, dinos cual y el mensaje exacto (o foto del error): tambien es un resultado util.
8. No hace falta dar vueltas ni que el cronometro funcione: son pistas de laboratorio.
9. Manda las fotos por donde siempre, con el nombre del ensayo en cada una. Gracias!
10. Generado el {fecha} por 03_blender/_rev/kn5_ensayo.py; los 5 kn5 pasan 8/8 comprobaciones de kn5_check.py aqui, pero AC solo lo hay en tu PC.

----- Para el equipo (tecnico; el amigo puede ignorarlo) -----
Verificado [V] / supuesto [S] en los materiales de ensayo (fuentes: _rev/fase_visual/web_multilayer_vao_erosion.md 1.1-1.3,
web_treefx.md 7.1-7.2 y la copia local de AcTools.Render en 04_export/kn5_refs/actools_b):
{notas}
Convenciones comunes a los 5: cabecera sc6969 + v5; mallas en coordenadas mundo bajo dummies identidad FISICA/DECO, salvo las mini-mallas
de los AC_* y la tapa ANIM_ (locales); UV con v = 0 en la fila de arriba de la imagen (u, 1 - v del writer); winding = regla de kn5_check.
Si en la foto D el texto sale en espejo, el eje X de AC crece hacia la derecha del que mira a +Z (y no hacia la izquierda como supone este
script y como implica el cambio de ejes (x, z, -y) del writer): habria que revisarlo antes de pintar textos en pantallas o carteles.
"""


# ------------------------------------------------------------------------------------------------ validacion


def validar(kn5, informe):
    """Lanza 04_export/kn5_check.py (solo se EJECUTA, no se toca) y devuelve (resultado, resumen)."""
    cmd = [sys.executable, KN5_CHECK, kn5, informe, '--no-wait', '--quiet']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    res = 'OK' if 'RESULTADO: OK' in r.stdout else 'FALLO'
    fallos = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith('(') and 'FALLO' in ln]
    return res, fallos, r.returncode


def comprobar_contenido(e, kn5):
    """Autotest: relee el KN5 con kn5_check.leer_kn5 y comprueba lo que la hipotesis necesita (shader, samplers, tamanos,
    flags, matriz del ANIM_). Devuelve lista de fallos."""
    import kn5_check as kc
    info = kc.leer_kn5(open(kn5, 'rb').read())
    f = []
    mats = {m['nombre']: m for m in info['materiales']}
    texs = {t['nombre']: t for t in info['texturas']}
    mallas = {m['nombre']: m for m in info['mallas']}
    if info['bytes_leidos'] != info['bytes_fichero'] or info['raices_extra']:
        f.append('bytes sobrantes o raices extra')
    if len([d for d in info['dummies'] if d['nombre'].startswith('AC_')]) != 45:
        f.append('no hay 45 dummies AC_*')
    for m in e.deco:
        if m.nombre not in mallas:
            f.append('falta la malla %s' % m.nombre)
        elif mallas[m.nombre]['n_triangulos'] != m.n_tris():
            f.append('%s: %d triangulos (esperados %d)' % (m.nombre, mallas[m.nombre]['n_triangulos'], m.n_tris()))
    if e.letra == 'a':
        m = mats['MAT_ensayo_multicapa']
        if m['shader'] != 'ksMultilayer_fresnel_nm' or [s['nombre'] for s in m['samplers']] != \
                ['txDiffuse', 'txMask', 'txDetailR', 'txDetailG', 'txDetailB', 'txDetailA', 'txDetailNM']:
            f.append('multicapa: shader o samplers incorrectos')
        t = texs.get('ensayo_a_mask_2048.png', {})
        if (t.get('ancho'), t.get('alto'), t.get('modo')) != (2048, 2048, 'RGBA'):
            f.append('mascara no es RGBA 2048: %s' % t)
        props = {p['nombre']: p for p in m['props']}
        for pn in ('multR', 'multG', 'multB', 'multA', 'detailNMMult', 'magicMult', 'fresnelC', 'fresnelEXP', 'fresnelMaxLevel'):
            if pn not in props:
                f.append('multicapa: falta la prop ' + pn)
        if mallas['ENSAYO_a_suelo_multicapa']['n_triangulos'] != 4:
            f.append('el plano multicapa no tiene 4 triangulos')
    if e.letra in 'bce':
        nombre = {'b': 'MAT_ensayo_alfa_test', 'c': 'MAT_ensayo_kstree', 'e': 'MAT_ensayo_alfa_sombra'}[e.letra]
        m = mats[nombre]
        if not (m['alphaBlendMode'] == 0 and m['alphaTested'] == 1 and m['depthMode'] == 0):
            f.append('%s: blend/alphaTested/depth = %s/%s/%s' % (nombre, m['alphaBlendMode'], m['alphaTested'], m['depthMode']))
        if abs([p for p in m['props'] if p['nombre'] == 'ksAlphaRef'][0]['valor'] - 0.5) > 1e-6:
            f.append('%s: ksAlphaRef != 0.5' % nombre)
        t = texs['ensayo_hojas_rgba.png']
        if t.get('modo') != 'RGBA' or t.get('ancho') != 1024:
            f.append('hojas: no es PNG RGBA 1024')
    if e.letra == 'c':
        if mats['MAT_ensayo_kstree']['shader'] != 'ksTree':
            f.append('shader != ksTree')
        for k in (0, 1):
            mm = mallas['ENSAYO_c_kstree_%d' % k]
            if mm['frac_normales_arriba'] != 1.0:
                f.append('ksTree_%d: normales no son (0,1,0)' % k)
    if e.letra == 'd':
        t = texs['ensayo_d_uv_2048.png']
        if (t.get('ancho'), t.get('alto')) != (2048, 2048):
            f.append('uv_2048 no mide 2048')
        t2 = texs['ensayo_d_mips_1024.dds']
        if t2['formato'] != 'DDS' or t2['tamano'] != 128 + sum((1024 >> k) ** 2 * 4 for k in range(11)):
            f.append('dds: formato o tamano incorrecto (%s, %d B)' % (t2['formato'], t2['tamano']))
        rango = [m for m in info['mallas'] if m['nombre'] == 'ENSAYO_d_panel_uv'][0]['uv_rango']
        if rango['min'] != [0.0, 0.0] or rango['max'] != [1.0, 1.0]:
            f.append('panel_uv: rango UV %s' % rango)
    if e.letra == 'e':
        d = [x for x in info['dummies'] if x['nombre'] == 'ANIM_rotor_ensayo'][0]
        tr = d['mundo']['traslacion']
        if not np.allclose(tr, [0.0, 6.0, 55.0], atol=1e-3) or abs(d['mundo']['rumbo_eje_z_deg'] - 30.0) > 0.1:
            f.append('ANIM_: traslacion %s rumbo %s' % (tr, d['mundo']['rumbo_eje_z_deg']))
        hijo = d['hijos'][0]
        if not (hijo['castShadows'] == 1 and hijo['isRenderable'] == 1 and hijo['n_triangulos'] == 4):
            f.append('ANIM_ hija: cast %s render %s tris %s' % (hijo['castShadows'], hijo['isRenderable'], hijo['n_triangulos']))
        bb = hijo['bbox_mundo']
        if abs(bb['min'][1] - 6.0) > 1e-3 or abs(bb['max'][0] - (7 * math.cos(math.radians(30)) + 7 * math.sin(math.radians(30)))) > 0.01:
            f.append('ANIM_ hija: bbox mundo %s (la matriz del dummy no se aplica como se esperaba)' % bb)
        if mallas['ENSAYO_e_arbol_sombra']['castShadows'] != 1:
            f.append('arbol_sombra sin castShadows')
    return f


def main(argv):
    solo = argv[argv.index('--solo') + 1].split(',') if '--solo' in argv else list('abcde')
    out = argv[argv.index('--out') + 1] if '--out' in argv else OUT
    con_check = '--sin-check' not in argv
    t0 = time.time()
    tracks = os.path.join(out, 'content', 'tracks')
    for sub in (tracks, os.path.join(out, 'texturas'), os.path.join(out, 'informes')):
        os.makedirs(sub, exist_ok=True)
    resumen, notas = {}, []
    for letra in solo:
        e = ENSAYOS[letra]()
        kn5, tam = carpeta_pista(e, tracks)
        for nombre, data in e.texturas:
            if not nombre.startswith('flat_'):
                with open(os.path.join(out, 'texturas', nombre), 'wb') as fh:
                    fh.write(data)
        fila = {'kn5': kn5, 'bytes': tam, 'texturas': len(e.texturas), 'materiales': len(e.materiales),
                'mallas': len(e.fisica) + len(e.deco) + len(e.ac) + sum(len(h) for _, _, h in e.dummies_extra),
                'triangulos_prueba': sum(m.n_tris() for m in e.deco) + sum(m.n_tris() for _, _, h in e.dummies_extra for m in h)}
        if con_check:
            informe = os.path.join(out, 'informes', e.nombre + '_check.json')
            res, fallos, rc = validar(kn5, informe)
            fila.update(kn5_check=res, kn5_check_fallos=fallos, informe=informe)
            fila['autotest'] = comprobar_contenido(e, kn5)
        resumen[e.nombre] = fila
        notas.append('(%s) %s\n    - ' % (letra, e.titulo) + '\n    - '.join(e.notas))
        print('%s: %.2f MB, %d texturas, %d materiales, %d mallas, %d triangulos de prueba, kn5_check %s%s' % (
            e.nombre, tam / 1e6, fila['texturas'], fila['materiales'], fila['mallas'], fila['triangulos_prueba'],
            fila.get('kn5_check', '(no lanzado)'),
            '' if not fila.get('autotest') else ' AUTOTEST FALLA: ' + '; '.join(fila['autotest'])))
    with open(os.path.join(out, 'LEEME.txt'), 'w', encoding='utf-8') as fh:
        fh.write(LEEME.format(fecha=time.strftime('%d/%m/%Y'), notas='\n'.join(notas)))
    with open(os.path.join(out, 'resumen_ensayos.json'), 'w', encoding='utf-8') as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=1)
    if len(solo) == 5:
        zp = os.path.join(out, 'ensayos_porto_corsa.zip')
        with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(os.path.join(out, 'LEEME.txt'), 'LEEME.txt')
            for raiz, _, fs in os.walk(os.path.join(out, 'content')):
                for fn in fs:
                    p = os.path.join(raiz, fn)
                    z.write(p, os.path.relpath(p, out))
        print('zip -> %s (%.1f MB)' % (zp, os.path.getsize(zp) / 1e6))
    ok = all(r.get('kn5_check', 'OK') == 'OK' and not r.get('autotest') for r in resumen.values())
    print('TOTAL: %d ensayos en %.1f s -> %s' % (len(resumen), time.time() - t0, 'TODO OK' if ok else 'HAY FALLOS'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
