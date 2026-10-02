# -*- coding: utf-8 -*-
"""
Generador de texturas tileables 1024x1024 para el mod de Porto Corsa (Cars 2).

Todas las texturas se sintetizan con ruido PERIODICO (sintesis espectral por FFT
o patrones modulares), por lo que tilean sin costuras por construccion.
Estilo Cars 2: limpio, saturado, no fotorrealista sucio.

Genera:
  asfalto_d.png, tierra_d.png, teja_d.png, estuco_d.png,
  piedra_d.png, hierba_d.png, agua_h.png
y un mosaico_3x3_<nombre>.png por cada una (repetida 3x3, reescalada a 1536
para inspeccion visual del tileado).
"""

import os
import numpy as np
from PIL import Image

N = 1024
AQUI = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- utilidades

def ruido_espectral(n=N, beta=2.0, seed=0, aniso=(1.0, 1.0), kmin=0):
    """Ruido fractal periodico via sintesis espectral (1/f^beta).
    aniso=(ay, ax): valores mayores comprimen la variacion en ese eje
    (ay grande => rasgos alargados en vertical).
    kmin: suprime frecuencias por debajo de kmin ciclos/imagen (evita la
    gran mancha unica que delata la repeticion del tile)."""
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None] * aniso[0]
    fx = np.fft.fftfreq(n)[None, :] * aniso[1]
    f = np.sqrt(fy * fy + fx * fx)
    amp = np.zeros_like(f)
    nz = f > 0
    amp[nz] = f[nz] ** (-beta)
    if kmin > 0:
        amp[(f * n) < kmin] = 0.0
    fase = rng.uniform(0.0, 2.0 * np.pi, (n, n))
    esp = amp * np.exp(1j * fase)
    img = np.fft.ifft2(esp).real
    img -= img.min()
    m = img.max()
    if m > 0:
        img /= m
    return img  # [0,1]


def ruido_banda(n=N, f0=0.25, ancho=0.08, seed=0, aniso=(1.0, 1.0)):
    """Ruido periodico de banda limitada (grano fino uniforme)."""
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None] * aniso[0]
    fx = np.fft.fftfreq(n)[None, :] * aniso[1]
    f = np.sqrt(fy * fy + fx * fx)
    amp = np.exp(-((f - f0) ** 2) / (2.0 * ancho ** 2))
    fase = rng.uniform(0.0, 2.0 * np.pi, (n, n))
    img = np.fft.ifft2(amp * np.exp(1j * fase)).real
    img -= img.min()
    m = img.max()
    if m > 0:
        img /= m
    return img


def hash01(ix, iy, seed=0.0):
    """Aleatorio determinista por celda (acepta arrays)."""
    v = np.sin(ix * 127.1 + iy * 311.7 + seed * 74.7) * 43758.5453123
    return v - np.floor(v)


def desenfoque_wrap(a, radio):
    """Desenfoque gaussiano periodico via FFT."""
    n = a.shape[0]
    f = np.fft.fftfreq(n)
    fy, fx = f[:, None], f[None, :]
    g = np.exp(-2.0 * (np.pi ** 2) * (radio ** 2) * (fy ** 2 + fx ** 2))
    return np.fft.ifft2(np.fft.fft2(a) * g).real


def guardar(nombre, arr):
    """Guarda arr float [0,1] (HxWx3 o HxW) como PNG + su mosaico 3x3."""
    a8 = np.clip(np.round(arr * 255.0), 0, 255).astype(np.uint8)
    img = Image.fromarray(a8)
    ruta = os.path.join(AQUI, nombre)
    img.save(ruta)
    reps = (3, 3, 1) if a8.ndim == 3 else (3, 3)
    mosaico = Image.fromarray(np.tile(a8, reps)).resize(
        (1536, 1536), Image.LANCZOS)
    mosaico.save(os.path.join(AQUI, "mosaico_3x3_" + nombre))
    print("  ->", ruta)


def coords():
    y, x = np.mgrid[0:N, 0:N]
    return x.astype(np.float64), y.astype(np.float64)


# ------------------------------------------------------------------- asfalto

def asfalto():
    print("asfalto_d.png")
    base = 0.46  # gris medio
    # grano fino de arido
    grano = ruido_banda(f0=0.30, ancho=0.10, seed=11) - 0.5
    grano2 = ruido_banda(f0=0.14, ancho=0.05, seed=12) - 0.5
    # manchas amplias de desgaste (mas claras) y parches (mas oscuros)
    desgaste = ruido_espectral(beta=2.5, seed=13, kmin=2) - 0.5
    parches = ruido_espectral(beta=2.9, seed=14, kmin=3) - 0.5

    v = base + 0.065 * grano + 0.04 * grano2 + 0.055 * desgaste + 0.04 * parches

    # grietas sutiles: trazos casi rectos con leve serpenteo (con envoltura)
    rng = np.random.default_rng(23)
    mapa_grietas = np.zeros((N, N))
    for _ in range(4):
        x = rng.uniform(0, N)
        y = rng.uniform(0, N)
        ang = rng.uniform(0, 2 * np.pi)
        pasos = int(rng.integers(500, 800))
        for i in range(pasos):
            ang += rng.normal(0.0, 0.055)     # serpenteo suave, sin bucles
            if rng.random() < 0.008:
                ang += rng.choice([-1.0, 1.0]) * rng.uniform(0.3, 0.6)  # quiebro
            x = (x + np.cos(ang) * 1.6) % N
            y = (y + np.sin(ang) * 1.6) % N
            xi, yi = int(x), int(y)
            peso = 0.55 + 0.45 * np.sin(np.pi * i / pasos)  # se desvanece en puntas
            mapa_grietas[yi, xi] = max(mapa_grietas[yi, xi], peso)
    mapa_grietas = desenfoque_wrap(mapa_grietas, 0.9)
    mapa_grietas = np.clip(mapa_grietas / max(mapa_grietas.max(), 1e-6), 0, 1)
    v -= 0.085 * mapa_grietas

    v = np.clip(v, 0, 1)
    # gris ligeramente frio
    rgb = np.stack([v * 0.985, v * 0.99, v], axis=-1)
    guardar("asfalto_d.png", rgb)


# -------------------------------------------------------------------- tierra

def tierra():
    print("tierra_d.png")
    # base ocre calida con variacion amplia (sin gran mancha unica)
    var = ruido_espectral(beta=2.3, seed=31, kmin=3) - 0.5
    var2 = ruido_espectral(beta=1.8, seed=32, kmin=4) - 0.5
    grano = ruido_banda(f0=0.20, ancho=0.08, seed=33) - 0.5
    arena = ruido_banda(f0=0.38, ancho=0.10, seed=35) - 0.5

    v = 1.0 + 0.11 * var + 0.07 * var2 + 0.13 * grano + 0.10 * arena

    r = 0.74 * v
    g = 0.60 * v
    b = 0.43 * v

    # pedregal fino: guijarros dispersos con envoltura
    rng = np.random.default_rng(34)
    npied = 5200
    for _ in range(npied):
        cx = rng.uniform(0, N)
        cy = rng.uniform(0, N)
        rad = rng.uniform(1.4, 4.2)
        sombra = rng.uniform(-0.22, 0.24)  # unas claras, otras oscuras
        calidez = rng.uniform(0.85, 1.05)
        w = int(np.ceil(rad)) + 1
        xs = (np.arange(int(cx) - w, int(cx) + w + 1)) % N
        ys = (np.arange(int(cy) - w, int(cy) + w + 1)) % N
        gx, gy = np.meshgrid(xs, ys)
        dx = (np.arange(int(cx) - w, int(cx) + w + 1) - cx)
        dy = (np.arange(int(cy) - w, int(cy) + w + 1) - cy)
        DX, DY = np.meshgrid(dx, dy)
        d = np.sqrt(DX * DX + DY * DY * rng.uniform(1.0, 1.8))
        m = np.clip(1.0 - d / rad, 0, 1) ** 0.7
        r[gy, gx] += sombra * m
        g[gy, gx] += sombra * m * 0.92 * calidez
        b[gy, gx] += sombra * m * 0.80 * calidez

    rgb = np.clip(np.stack([r, g, b], axis=-1), 0, 1)
    guardar("tierra_d.png", rgb)


# ---------------------------------------------------------------------- teja

def teja():
    print("teja_d.png")
    x, y = coords()
    th, tw = 128, 128            # 8 hiladas x 8 tejas
    fila = (y // th).astype(int)
    xoff = (fila % 2) * (tw // 2)  # media teja de escalonado
    xl = (x + xoff) % tw
    yl = y % th
    col = (((x + xoff) // tw) % (N // tw)).astype(int)

    # perfil curvo (teja arabe): claro en el lomo, oscuro en el canal
    curva = np.sin(np.pi * xl / tw) ** 0.85
    sombreado = 0.72 + 0.38 * curva

    # junta vertical oscura entre tejas
    dj = np.minimum(xl, tw - xl)
    junta_v = np.clip(1.0 - dj / 5.0, 0, 1)
    sombreado *= 1.0 - 0.38 * junta_v

    # sombra de la hilada superior (festoneada: mas profunda en el canal)
    prof = 10.0 + 16.0 * (1.0 - np.sin(np.pi * xl / tw))
    sombra_sup = np.clip(1.0 - yl / prof, 0, 1) ** 1.1
    sombreado *= 1.0 - 0.30 * sombra_sup

    # borde inferior: fina linea clara (canto de la teja) y junta oscura
    borde = np.clip((yl - (th - 7)) / 4.0, 0, 1) * np.clip((th - 2 - yl) / 2.0, 0, 1)
    sombreado *= 1.0 + 0.10 * borde
    junta_h = np.clip((yl - (th - 2)) / 2.0, 0, 1)
    sombreado *= 1.0 - 0.30 * junta_h

    # variacion de tono por teja
    t1 = hash01(col, fila, 5.0)
    t2 = hash01(col, fila, 9.0)
    tono = 0.90 + 0.18 * t1

    # superficie: ruido suave
    sup = ruido_banda(f0=0.10, ancho=0.05, seed=41) - 0.5
    sombreado *= tono * (1.0 + 0.08 * sup)

    # terracota: mezcla entre dos tonos por teja
    c_a = np.array([0.80, 0.42, 0.28])
    c_b = np.array([0.72, 0.35, 0.24])
    mez = t2[..., None]
    color = c_a * (1 - mez) + c_b * mez
    rgb = np.clip(color * sombreado[..., None], 0, 1)
    guardar("teja_d.png", rgb)


# -------------------------------------------------------------------- estuco

def estuco():
    print("estuco_d.png")
    # casi blanco, neutro (se multiplica sobre el color de fachada: no tine)
    base = 0.955
    suave = ruido_espectral(beta=2.8, seed=51) - 0.5
    # patina vertical: rasgos alargados en vertical
    veta = ruido_espectral(beta=2.2, seed=52, aniso=(6.0, 1.0)) - 0.5
    fino = ruido_banda(f0=0.16, ancho=0.06, seed=53) - 0.5

    v = base + 0.030 * suave + 0.030 * veta + 0.018 * fino
    v = np.clip(v, 0.88, 1.0)
    rgb = np.stack([v, v, v], axis=-1)
    guardar("estuco_d.png", rgb)


# -------------------------------------------------------------------- piedra

def piedra():
    print("piedra_d.png")
    x, y = coords()
    bh, bw = 128, 256            # 8 hiladas de sillares
    fila = (y // bh).astype(int)
    # desplazamiento por hilada (multiplos que envuelven)
    offs = np.array([0, 96, 192, 64, 160, 32, 128, 224])
    xoff = offs[fila % 8]
    xl = (x + xoff) % bw
    yl = y % bh
    col = (((x + xoff) // bw) % (N // bw)).astype(int)

    # junta de mortero
    djx = np.minimum(xl, bw - xl)
    djy = np.minimum(yl, bh - yl)
    dj = np.minimum(djx, djy)
    junta = np.clip(1.0 - dj / 7.0, 0, 1) ** 1.3

    # bisel: luz desde arriba-izquierda
    bisel = (np.clip(1.0 - yl / 14.0, 0, 1) * 0.10
             - np.clip((yl - (bh - 14)) / 14.0, 0, 1) * 0.08
             + np.clip(1.0 - xl / 12.0, 0, 1) * 0.05
             - np.clip((xl - (bw - 12)) / 12.0, 0, 1) * 0.05)

    # variacion por bloque + textura interior
    t = hash01(col, fila, 3.0)
    tono = 0.90 + 0.17 * t
    interior = ruido_espectral(beta=2.2, seed=61) - 0.5
    grano = ruido_banda(f0=0.20, ancho=0.08, seed=62) - 0.5

    v = 0.80 * tono * (1.0 + 0.10 * interior + 0.05 * grano) + bisel
    v *= 1.0 - 0.34 * junta

    v = np.clip(v, 0, 1)
    # piedra clara calida (arenisca suave)
    rgb = np.stack([v, v * 0.955, v * 0.875], axis=-1)
    guardar("piedra_d.png", rgb)


# -------------------------------------------------------------------- hierba

def hierba():
    print("hierba_d.png")
    # cesped verde saturado estilo Cars
    matas = ruido_espectral(beta=2.3, seed=71, kmin=4) - 0.5   # matas amplias
    medio = ruido_banda(f0=0.045, ancho=0.02, seed=72) - 0.5   # macollas medias
    # briznas: ruido fino alargado en VERTICAL (ay > ax)
    brizna = ruido_banda(f0=0.26, ancho=0.09, seed=73, aniso=(2.6, 1.0)) - 0.5
    brizna2 = ruido_banda(f0=0.14, ancho=0.05, seed=74, aniso=(2.0, 1.0)) - 0.5

    v = 1.0 + 0.10 * matas + 0.10 * medio + 0.17 * brizna + 0.11 * brizna2

    # mezclar entre verde vivo y verde algo amarillento segun las matas
    amar = np.clip(0.5 + matas * 1.1 + medio * 0.8, 0, 1)
    c_a = np.array([0.28, 0.60, 0.15])   # verde saturado
    c_b = np.array([0.42, 0.65, 0.14])   # verde amarillento
    color = c_a * (1 - amar[..., None]) + c_b * amar[..., None]
    rgb = np.clip(color * v[..., None], 0, 1)
    guardar("hierba_d.png", rgb)


# --------------------------------------------------------------------- agua

def agua():
    print("agua_h.png")
    x, y = coords()
    rng = np.random.default_rng(86)
    # pocos trenes de olas amplias + deformacion de fase periodica suave
    # (mantiene el tileado y da un vaiven organico, sin blobs ni caos)
    w1 = (ruido_espectral(beta=3.0, seed=88, kmin=1) - 0.5) * 2.0
    w2 = (ruido_espectral(beta=3.0, seed=89, kmin=1) - 0.5) * 2.0
    trenes = [((3, 1), 1.00, w1),
              ((1, 2), 0.50, w2),
              ((2, -2), 0.22, w1 * 0.5)]
    h = np.zeros((N, N))
    for (kx, ky), a, w in trenes:
        fase = rng.uniform(0, 2 * np.pi)
        h += a * np.sin(2 * np.pi * (kx * x + ky * y) / N + fase + w)
    # contraste bajo, grises medios dominantes (olas suaves)
    h = (h - h.mean()) / h.std()
    h = 0.5 + 0.13 * h
    h = np.clip(h, 0, 1)
    guardar("agua_h.png", h)


if __name__ == "__main__":
    asfalto()
    tierra()
    teja()
    estuco()
    piedra()
    hierba()
    agua()
    print("Listo.")
