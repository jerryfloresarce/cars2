# -*- coding: utf-8 -*-
"""
Generador de texturas tileables 1024x1024 para el mod de Porto Corsa (Cars 2).

Todas las texturas se sintetizan con ruido PERIODICO (sintesis espectral por FFT
o patrones modulares), por lo que tilean sin costuras por construccion.
Estilo Cars 2: limpio, saturado, no fotorrealista sucio.

FASE VISUAL F1 (bloque 3 punto 2, propietario 'materiales'): los tintes salen de
03_blender/paleta.json via paleta.py (UNICA fuente de color: si el usuario cambia
la carta, basta re-ejecutar este script). Tiles nuevos del terreno:
  hierba_seca_d.png (3 m)  dorado 'hierba_seca' con matas oliva     -> familia 'seca' / 'hierba' (TERRENO, ARCEN)
  matorral_d.png    (6 m)  manchas oliva_oscuro / salvia + claros   -> familia 'matorral' / 'bosque'
  caliza_d.png      (3 m)  caliza_ocre con juntas HORIZONTALES      -> familia 'caliza' (rocas, materiales_roca)
  caliza_grande_d.png (24 m) F1 r4: DERIVADO de afloramiento_d + caliza_d (dos escalas + ruido de baja frecuencia,
                           contraste 60 %) para el McLaren y rocas de > 50 m -> familia 'caliza_grande'
  cesped_d.png      (3 m)  el cesped verde de siempre, SOLO jardines -> familia 'cesped'
  teja_d.png        (2 m)  terracota de la paleta
  tierra_d.png      (6 m)  ocre 'tierra' de la paleta
hierba_d.png se sigue escribiendo (misma imagen que cesped_d.png) por compatibilidad
con blends antiguos, pero YA NO es el tile del terreno.

Cada guardado escribe/actualiza texturas/medias.json con la media LINEAL de cada
PNG y su ganancia (1/media): aplicar_texturas.py la lee para que el multiply no
oscurezca; recolorear_cc0.py (CC0 recoloreado, mismo nombre de salida) la
actualiza igual. Orden del pipeline de texturas: PIL primero, CC0 despues.

  python generar_texturas.py            todas
  python generar_texturas.py hierba_seca matorral caliza   solo esas
  python generar_texturas.py --medir    solo re-mide medias.json de los PNG presentes
"""

import datetime
import json
import os
import sys

import numpy as np
from PIL import Image

N = 1024
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
import paleta  # noqa: E402

MEDIAS_JSON = os.path.join(AQUI, 'medias.json')
TILE_M = {  # metros por tile (informativo; aplicar_texturas.FAMILIAS fija la escala real)
    'asfalto_d.png': 8.0, 'tierra_d.png': 6.0, 'teja_d.png': 2.0, 'estuco_d.png': 4.0, 'piedra_d.png': 3.0,
    'hierba_d.png': 3.0, 'cesped_d.png': 3.0, 'hierba_seca_d.png': 3.0, 'matorral_d.png': 6.0,
    'caliza_d.png': 3.0, 'caliza_grande_d.png': 24.0, 'agua_h.png': 40.0,
}


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


def srgb_a_lin(a):
    a = np.asarray(a, dtype=np.float64)
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def lin_a_srgb(a):
    a = np.clip(np.asarray(a, dtype=np.float64), 0.0, 1.0)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1.0 / 2.4) - 0.055)


def tinte(nombre):
    """Color de la paleta en sRGB 0..1 (lo que se escribe tal cual al PNG)."""
    return np.array(paleta.srgb(nombre), dtype=np.float64)


def mezcla(c1, c2, t):
    return np.asarray(c1) * (1.0 - t) + np.asarray(c2) * t


def medir(ruta):
    """Media lineal (r, g, b), luminancia media y ganancia 1/media de un PNG de color."""
    a = np.asarray(Image.open(ruta).convert('RGB'), dtype=np.float64) / 255.0
    lin = srgb_a_lin(a)
    media = lin.reshape(-1, 3).mean(axis=0)
    lum = float(0.2126 * media[0] + 0.7152 * media[1] + 0.0722 * media[2])
    return [round(float(c), 5) for c in media], round(lum, 5), round(1.0 / max(lum, 1e-4), 4)


def anotar_media(nombre, origen='pil', extra=None):
    """Actualiza texturas/medias.json con la media lineal del PNG `nombre` (clave = nombre de fichero)."""
    ruta = os.path.join(AQUI, nombre)
    datos = {}
    if os.path.exists(MEDIAS_JSON):
        try:
            with open(MEDIAS_JSON, encoding='utf-8') as fh:
                datos = json.load(fh)
        except Exception:
            datos = {}
    if nombre.endswith('_h.png') or nombre.endswith('_n.png'):
        return datos
    media, lum, gan = medir(ruta)
    e = {'media_lineal': media, 'media_lum': lum, 'ganancia': gan, 'origen': origen,
         'tile_m': TILE_M.get(nombre), 'fecha': datetime.date.today().isoformat()}
    if extra:
        e.update(extra)
    datos.setdefault('_doc', 'media LINEAL de cada tile de texturas/ (sRGB -> lineal) y ganancia = 1/media_lum. '
                             'La escribe generar_texturas.py (PIL) o recolorear_cc0.py (CC0 recoloreado, origen cc0:<id>). '
                             'aplicar_texturas.py la lee (FAMILIAS.ganancia es el valor de respaldo).')
    datos[nombre] = e
    with open(MEDIAS_JSON, 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, indent=1, ensure_ascii=False)
    return datos


def guardar(nombre, arr, origen='pil'):
    """Guarda arr float [0,1] (HxWx3 o HxW) como PNG + su mosaico 3x3 + media en medias.json."""
    a8 = np.clip(np.round(arr * 255.0), 0, 255).astype(np.uint8)
    img = Image.fromarray(a8)
    ruta = os.path.join(AQUI, nombre)
    img.save(ruta)
    reps = (3, 3, 1) if a8.ndim == 3 else (3, 3)
    mosaico = Image.fromarray(np.tile(a8, reps)).resize(
        (1536, 1536), Image.LANCZOS)
    mosaico.save(os.path.join(AQUI, "mosaico_3x3_" + nombre))
    if a8.ndim == 3:
        d = anotar_media(nombre, origen)
        print("  -> %s  media_lineal=%s ganancia=%.3f" % (ruta, d[nombre]['media_lineal'], d[nombre]['ganancia']))
    else:
        print("  ->", ruta)


def coords():
    y, x = np.mgrid[0:N, 0:N]
    return x.astype(np.float64), y.astype(np.float64)


def costura_max(arr):
    """Costura relativa: |borde izq - borde der| (y arriba - abajo) comparada con la diferencia entre columnas (filas)
    vecinas del INTERIOR. 1.0 = el empalme se parece a cualquier otro par de pixeles vecinos (seamless);
    > 1.5 = costura visible. Comprobacion numerica del mosaico 3x3 (vale para patrones duros: teja, sillares)."""
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim == 2:
        a = a[..., None]
    vec_x = max(float(np.abs(a[:, 1:] - a[:, :-1]).mean()), 1e-6)
    vec_y = max(float(np.abs(a[1:] - a[:-1]).mean()), 1e-6)
    lr = float(np.abs(a[:, 0] - a[:, -1]).mean()) / vec_x
    tb = float(np.abs(a[0] - a[-1]).mean()) / vec_y
    return max(lr, tb)


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
    # base ocre calida con variacion amplia (sin gran mancha unica); tinte = paleta 'tierra'
    var = ruido_espectral(beta=2.3, seed=31, kmin=3) - 0.5
    var2 = ruido_espectral(beta=1.8, seed=32, kmin=4) - 0.5
    grano = ruido_banda(f0=0.20, ancho=0.08, seed=33) - 0.5
    arena = ruido_banda(f0=0.38, ancho=0.10, seed=35) - 0.5

    v = 1.0 + 0.11 * var + 0.07 * var2 + 0.13 * grano + 0.10 * arena

    c = tinte('tierra')
    r = c[0] * v
    g = c[1] * v
    b = c[2] * v

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

    # terracota de la paleta: dos tonos por teja (uno algo mas claro y otro mas tostado)
    c = tinte('terracota')
    c_a = np.clip(c * 1.10, 0, 1)
    c_b = np.clip(c * np.array([0.92, 0.86, 0.90]), 0, 1)
    mez = t2[..., None]
    color = c_a * (1 - mez) + c_b * mez
    rgb = np.clip(color * (sombreado[..., None] * 1.12), 0, 1)
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
    # sillares claros con la croma de caliza_ocre (arenisca calida); brillo como antes (v ~ 0.8)
    c = tinte('caliza_ocre')
    c = c / max(c.max(), 1e-6)
    rgb = np.clip(np.stack([v * c[0], v * c[1], v * c[2]], axis=-1), 0, 1)
    guardar("piedra_d.png", rgb)


# -------------------------------------------------------------- cesped (jardines)

def _cesped_rgb():
    """El cesped verde de siempre (tile 3 m), ahora con el tinte 'cesped_jardin' de la paleta."""
    matas = ruido_espectral(beta=2.3, seed=71, kmin=4) - 0.5   # matas amplias
    medio = ruido_banda(f0=0.045, ancho=0.02, seed=72) - 0.5   # macollas medias
    # briznas: ruido fino alargado en VERTICAL (ay > ax)
    brizna = ruido_banda(f0=0.26, ancho=0.09, seed=73, aniso=(2.6, 1.0)) - 0.5
    brizna2 = ruido_banda(f0=0.14, ancho=0.05, seed=74, aniso=(2.0, 1.0)) - 0.5

    v = 1.0 + 0.10 * matas + 0.10 * medio + 0.17 * brizna + 0.11 * brizna2

    # mezclar entre verde vivo y verde algo amarillento segun las matas
    amar = np.clip(0.5 + matas * 1.1 + medio * 0.8, 0, 1)
    c = tinte('cesped_jardin')
    c_a = np.clip(c * np.array([0.90, 1.05, 0.95]), 0, 1)        # verde vivo
    c_b = np.clip(c * np.array([1.18, 1.08, 0.85]), 0, 1)        # verde amarillento
    color = c_a * (1 - amar[..., None]) + c_b * amar[..., None]
    return np.clip(color * v[..., None], 0, 1)


def cesped():
    print("cesped_d.png (+ hierba_d.png, compatibilidad)")
    rgb = _cesped_rgb()
    guardar("cesped_d.png", rgb)
    guardar("hierba_d.png", rgb)


def hierba():
    """Compatibilidad: hierba_d.png = cesped_d.png (ya NO es el tile del terreno)."""
    cesped()


# ------------------------------------------------------------ hierba seca (terreno)

def hierba_seca():
    print("hierba_seca_d.png")
    # pradera dorada de verano (tile 3 m): matas de 20-60 cm, briznas verticales finas,
    # calvas de tierra clara y algun rodal verdoso-oliva donde queda humedad
    matas = ruido_espectral(beta=2.4, seed=81, kmin=5) - 0.5
    medio = ruido_banda(f0=0.06, ancho=0.025, seed=82) - 0.5
    brizna = ruido_banda(f0=0.30, ancho=0.10, seed=83, aniso=(3.0, 1.0)) - 0.5
    brizna2 = ruido_banda(f0=0.16, ancho=0.06, seed=84, aniso=(2.2, 1.0)) - 0.5
    calvas = ruido_espectral(beta=2.0, seed=85, kmin=3) - 0.5

    v = 1.0 + 0.12 * matas + 0.10 * medio + 0.16 * brizna + 0.10 * brizna2

    seca = tinte('hierba_seca')
    oliva = tinte('salvia')
    tierra_c = tinte('tierra')
    # rodales oliva (hierba aun verde) en las zonas de 'matas' altas
    t_oliva = np.clip(0.55 - matas * 1.6 - medio * 0.6, 0, 1) * 0.45
    # calvas de tierra en los minimos de 'calvas'
    t_tierra = np.clip(-calvas * 2.2 - 0.25, 0, 1) * 0.6
    color = seca[None, None, :] * np.ones((N, N, 1))
    color = color * (1 - t_oliva[..., None]) + oliva[None, None, :] * t_oliva[..., None]
    color = color * (1 - t_tierra[..., None]) + (tierra_c * 0.92)[None, None, :] * t_tierra[..., None]
    # las briznas al sol son algo mas claras y amarillas
    sol = np.clip(brizna * 1.4, 0, 1)
    color = color * (1.0 + 0.08 * sol[..., None] * np.array([1.0, 0.9, 0.5]))
    rgb = np.clip(color * v[..., None], 0, 1)
    guardar("hierba_seca_d.png", rgb)


# --------------------------------------------------------------- matorral (terreno)

def matorral():
    print("matorral_d.png")
    # monte bajo mediterraneo (tile 6 m): rodales de matorral oliva oscuro de 1-3 m, matas
    # salvia mas claras, claros de tierra/hierba seca entre ellas y grano de hoja fino
    rodales = ruido_espectral(beta=2.6, seed=91, kmin=2) - 0.5      # masas de 1-3 m
    rodales2 = ruido_espectral(beta=2.2, seed=92, kmin=4) - 0.5
    hoja = ruido_banda(f0=0.22, ancho=0.08, seed=93) - 0.5          # grano de hoja ~3 cm
    hoja2 = ruido_banda(f0=0.10, ancho=0.04, seed=94) - 0.5
    # mascara de matorral: 1 donde hay mata, 0 en el claro (borde suave)
    mata = np.clip(0.5 + 2.4 * rodales + 1.2 * rodales2, 0, 1)
    mata = desenfoque_wrap(mata, 1.5)
    mata = np.clip(mata, 0, 1)

    oliva = tinte('oliva_oscuro')
    salvia = tinte('salvia')
    seca = tinte('hierba_seca')
    tierra_c = tinte('tierra')
    # dentro de la mata: oliva oscuro con copas salvia donde el rodal es mas alto
    t_salvia = np.clip(0.3 + rodales2 * 2.0, 0, 1)
    c_mata = oliva[None, None, :] * (1 - t_salvia[..., None]) + salvia[None, None, :] * t_salvia[..., None]
    c_mata = c_mata * (1.0 + 0.22 * hoja[..., None] + 0.12 * hoja2[..., None])
    # claros: hierba seca con tierra
    t_tierra = np.clip(0.35 - rodales * 1.5, 0, 1)
    c_claro = seca[None, None, :] * (1 - t_tierra[..., None]) + (tierra_c * 0.95)[None, None, :] * t_tierra[..., None]
    c_claro = c_claro * (1.0 + 0.10 * hoja2[..., None])
    color = c_mata * mata[..., None] + c_claro * (1 - mata[..., None])
    # sombra propia de la mata en su borde inferior (la mata es un bulto): ligera
    sombra = np.clip(np.roll(mata, 6, axis=0) - mata, 0, 1)
    color = color * (1.0 - 0.25 * sombra[..., None])
    rgb = np.clip(color, 0, 1)
    guardar("matorral_d.png", rgb)


# ------------------------------------------------------------------ caliza (rocas)

def caliza():
    print("caliza_d.png")
    # caliza calida con JUNTAS HORIZONTALES (tile 3 m): 6 estratos de 0.5 m con juntas
    # onduladas (ciclos enteros en x: envuelven), cornisa clara sobre la junta y sombra bajo
    # ella, tono alterno por estrato (+-8 %), grano de 2-5 cm y manchas de meteorizacion
    x, y = coords()
    n_estr = 6                      # PAR: la alternancia de tono por estrato cierra en el empalme del tile
    h = N / n_estr
    # ondulacion periodica de la junta (dos armonicos con ciclos enteros en x) + ruido periodico
    ond = (6.0 * np.sin(2 * np.pi * 3 * x / N) + 3.5 * np.sin(2 * np.pi * 7 * x / N + 1.3)
           + 10.0 * (ruido_espectral(beta=2.4, seed=101, kmin=2, aniso=(0.6, 1.0)) - 0.5))
    yy = (y + ond) % N
    estr = np.floor(yy / h).astype(int) % n_estr
    yl = yy - estr * h               # 0 .. h dentro del estrato (0 = justo bajo la junta superior)
    # junta: surco oscuro de ~5 px con borde suave; cornisa (labio claro) 4-12 px por encima
    d_junta = np.minimum(yl, h - yl)
    junta = np.clip(1.0 - d_junta / 4.5, 0, 1) ** 1.2
    # el grosor de la junta varia a lo largo (algunas casi cerradas)
    var_j = 0.55 + 0.45 * (ruido_banda(f0=0.02, ancho=0.01, seed=102, aniso=(0.3, 1.0)))
    junta = junta * var_j
    cornisa = np.clip(1.0 - (h - yl) / 10.0, 0, 1) * (1.0 - junta)          # labio claro justo encima de la junta
    sombra = np.clip(1.0 - yl / 14.0, 0, 1) * (1.0 - junta)                  # sombra bajo la junta (saliente)
    # tono alterno por estrato (+-8 %) con variacion lateral lenta
    alt = np.where(estr % 2 == 0, 1.0, -1.0)
    lateral = ruido_espectral(beta=2.6, seed=103, kmin=1) - 0.5
    tono = 1.0 + 0.08 * alt + 0.08 * lateral
    # grano fino 2-5 cm y manchas 0.3-1 m (+-10 %)
    grano = ruido_banda(f0=0.24, ancho=0.09, seed=104) - 0.5
    grano2 = ruido_banda(f0=0.11, ancho=0.05, seed=105) - 0.5
    manchas = ruido_espectral(beta=2.3, seed=106, kmin=3) - 0.5
    # fisuras verticales cortas (1-2 por estrato): lineas finas oscuras que no cruzan la junta
    fis = np.zeros((N, N))
    rng = np.random.default_rng(107)
    for k in range(n_estr):
        for _ in range(int(rng.integers(3, 6))):
            x0 = rng.uniform(0, N)
            l0 = rng.uniform(0.35, 0.8) * h
            y0 = k * h + rng.uniform(0.1, 0.9 - l0 / h) * h
            for t in np.arange(0, l0, 0.8):
                xi = int((x0 + 2.0 * np.sin(t / 9.0)) % N)
                yi = int((y0 + t) % N)
                fis[yi, xi] = max(fis[yi, xi], 1.0)
    fis = np.clip(desenfoque_wrap(fis, 0.8) * 3.0, 0, 1)
    # el mapa de fisuras esta en coordenadas 'yy' (sin ondular): se lee con la ondulacion para que sigan al estrato
    fis = fis[np.clip(yy.astype(int), 0, N - 1), x.astype(int)]

    v = (tono * (1.0 + 0.10 * grano + 0.07 * grano2 + 0.10 * manchas)
         * (1.0 + 0.09 * cornisa) * (1.0 - 0.14 * sombra) * (1.0 - 0.45 * junta) * (1.0 - 0.28 * fis))
    c = tinte('caliza_ocre')
    c_j = tinte('caliza_sombra')
    # el color de la junta tira a caliza_sombra (mas parda y menos saturada)
    color = c[None, None, :] * (1 - 0.6 * junta[..., None]) + c_j[None, None, :] * (0.6 * junta[..., None])
    # brillo medio = el de caliza_ocre (v ~ 1): la ganancia de aplicar_texturas lo compensa igual
    rgb = np.clip(color * (v[..., None] * 1.06), 0, 1)
    guardar("caliza_d.png", rgb)


# ------------------------------------------------------------------ caliza GRANDE (McLaren y rocas de > 50 m)
# pesos de las capas (24 m / 12 m / 8 m) y contraste final. Medido (F1 r4): con (0.5, 0.3, 0.2) y contraste 0.6 el tile no
# se repetia pero el McLaren salia PLANO en el proxy AC (pared_lisa de 49: 6 -> 53 %); con mas peso en la capa de 8 m y
# contraste 1.0 (+ factor 0.5 en aplicar_texturas) conserva grano a 100-200 m sin que las manchas grandes se repitan
CALIZA_GRANDE_PESOS = (0.40, 0.25, 0.35)
CALIZA_GRANDE_CONTRASTE = 1.0
# grano de BANDA MEDIA (ruido periodico de ~0.7 m y ~0.26 m sobre 24 m, +-12 % / +-7 %): es lo que da varianza local a
# 100-200 m (medir_capturas.pared_lisa: std de V en 9x9 px > 0.02) sin anadir manchas grandes que se repitan
CALIZA_GRANDE_GRANO = (0.24, 0.14)
# PIEDRAS: el contenido de 10-50 cm de caliza_d.png (rock_06) estirado a los 24 m del tile (1 repeticion: sin sub-periodo
# de 12 m) y PASO-ALTO: se le resta su desenfoque periodico de sigma_m metros, asi entran las piedras (varianza local a
# 100-200 m, como en r3) pero NO las manchas claras de 1-3 m que se repetian. (sigma_m, peso, repeticiones): medido con el
# estimador de pared_lisa de _rev/_tmp_materiales/r4 (r3 0.047 <-> 6 %)
CALIZA_GRANDE_PIEDRAS = (1.5, 0.8, 1)

def caliza_grande():
    """caliza_grande_d.png (24 m): tile DERIVADO para superficies de roca enormes vistas de lejos (el McLaren mide ~80 m).
    F1 r4 (director r3 n.4): con caliza_d.png (rock_06, manchas claras de baja frecuencia: std a 24 px 0.075) el tile se
    leia repetido en 49 incluso a 12 m. Aqui se MEZCLAN DOS ESCALAS de los tiles ya tintados (afloramiento_d.png, el de
    menor saliencia de baja frecuencia (0.040), como capa grande de 24 m; caliza_d.png girado 90 grados a 12 m como capa
    media; afloramiento a 8 m como grano: pesos CALIZA_GRANDE_PESOS) + ruido espectral periodico de baja frecuencia
    (+-6 %) que rompe los sub-periodos; contraste CALIZA_GRANDE_CONTRASTE. Media lineal = caliza_ocre (tinte de la paleta); el writer/--modo-ac
    normalizan por canal igual que con cualquier tile. Seamless por construccion (capas seamless con repeticiones enteras).
    Se ejecuta DESPUES de recolorear_cc0.py (lee los PNG finales); si falta afloramiento_d.png usa caliza_d.png."""
    print("caliza_grande_d.png")
    ruta_a = os.path.join(AQUI, 'afloramiento_d.png')
    ruta_c = os.path.join(AQUI, 'caliza_d.png')
    if not os.path.exists(ruta_c):
        print('  AVISO: falta caliza_d.png: no se genera caliza_grande_d.png')
        return
    if not os.path.exists(ruta_a):
        print('  AVISO: falta afloramiento_d.png: capa grande desde caliza_d.png')
        ruta_a = ruta_c

    def capa(ruta, reps, giro=0):
        im = Image.open(ruta).convert('RGB')
        if giro:
            im = im.rotate(giro, expand=True)
        im = im.resize((N, N), Image.LANCZOS)
        a = np.asarray(im, dtype=np.float64) / 255.0
        if reps > 1:
            a = np.tile(a, (reps, reps, 1))
            a = np.asarray(Image.fromarray(np.clip(np.round(a * 255.0), 0, 255).astype(np.uint8)).resize((N, N), Image.LANCZOS),
                           dtype=np.float64) / 255.0
        lin = srgb_a_lin(a)
        return lin / np.maximum(lin.reshape(-1, 3).mean(axis=0), 1e-4)[None, None, :]      # media 1 por canal

    l1 = capa(ruta_a, 1)              # 24 m: rasgos grandes
    l2 = capa(ruta_c, 2, giro=90)     # 12 m: estructura media (girada: no correlaciona con la de 3 m del terreno)
    l3 = capa(ruta_a, 3)              # 8 m: grano
    p1, p2, p3 = CALIZA_GRANDE_PESOS
    v = p1 * l1 + p2 * l2 + p3 * l3
    v = 1.0 + CALIZA_GRANDE_CONTRASTE * (v - 1.0)
    baja = (ruido_espectral(beta=2.5, seed=404, kmin=1) - 0.5) * 0.12           # +-6 %, rompe los sub-periodos de 12 / 8 m
    g1 = (ruido_banda(f0=0.035, ancho=0.015, seed=405) - 0.5) * CALIZA_GRANDE_GRANO[0]   # ~0.7 m
    g2 = (ruido_banda(f0=0.09, ancho=0.03, seed=406) - 0.5) * CALIZA_GRANDE_GRANO[1]     # ~0.26 m
    v = v * (1.0 + baja + g1 + g2)[..., None]
    sigma_m, k_p, reps_p = CALIZA_GRANDE_PIEDRAS
    if k_p > 0:
        lp = capa(ruta_c, reps_p)                                                # caliza_d a 24 m (reps 1), media 1 por canal
        lum_p = 0.2126 * lp[..., 0] + 0.7152 * lp[..., 1] + 0.0722 * lp[..., 2]
        hp = lum_p - desenfoque_wrap(lum_p, sigma_m / 24.0 * N)                  # paso-alto: sin manchas > sigma_m
        v = v * np.clip(1.0 + k_p * hp, 0.05, None)[..., None]
    c = np.array(paleta.rgb('caliza_ocre'), dtype=np.float64)                  # media lineal = caliza clara de la paleta
    lin = np.clip(c[None, None, :] * v, 0.0, 1.0)
    guardar("caliza_grande_d.png", lin_a_srgb(lin))


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


GENERADORES = {
    'asfalto': asfalto, 'tierra': tierra, 'teja': teja, 'estuco': estuco, 'piedra': piedra,
    'cesped': cesped, 'hierba': hierba, 'hierba_seca': hierba_seca, 'matorral': matorral,
    'caliza': caliza, 'caliza_grande': caliza_grande, 'agua': agua,
}
# caliza_grande va DESPUES de caliza (lee caliza_d.png / afloramiento_d.png); recolorear_cc0.py la vuelve a generar al final
ORDEN = ('asfalto', 'tierra', 'teja', 'estuco', 'piedra', 'cesped', 'hierba_seca', 'matorral', 'caliza', 'caliza_grande', 'agua')


def comprobar_mosaicos(nombres=None):
    """Costura relativa de cada PNG de color (0 = seamless). Devuelve dict nombre -> costura."""
    res = {}
    for n in (nombres or sorted(TILE_M)):
        ruta = os.path.join(AQUI, n)
        if not os.path.exists(ruta):
            continue
        a = np.asarray(Image.open(ruta).convert('RGB'), dtype=np.float64) / 255.0
        res[n] = round(costura_max(a), 4)
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if '--medir' in args:
        for n in sorted(TILE_M):
            if os.path.exists(os.path.join(AQUI, n)) and not n.endswith('_h.png'):
                d = anotar_media(n, origen='(re-medido)')
                print('%-20s media=%s ganancia=%.3f' % (n, d[n]['media_lineal'], d[n]['ganancia']))
        sys.exit(0)
    pedidos = [a for a in args if not a.startswith('--')] or list(ORDEN)
    for k in pedidos:
        if k not in GENERADORES:
            print('AVISO: generador desconocido', k, '; validos:', ', '.join(ORDEN))
            continue
        GENERADORES[k]()
    cost = comprobar_mosaicos()
    print('costura relativa (1.0 = seamless; > 1.5 costura visible):', cost)
    print("Listo.")
