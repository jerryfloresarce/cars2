"""montanas_fondo_v2.py — Muralla de montañas de fondo de Porto Corsa (Cars 2), v2.

Sustituye a montanas_fondo.py (MISMA API) con picos que tienen FORMA:
cinco tipos de macizo (aguja, piramide, meseta, cresta, domo), pie de
derrubios (talud 30-35 grados) que se hunde 6 m bajo el terreno, bandas
de estratos horizontales de espesor VARIABLE (plegadas, con repisas
saltadas) y materiales alternos, aristas/espolones con ruido "ridged",
asimetria (una cara mas vertical), linea de arboles con bosque en las
laderas suaves y roca desnuda arriba; cordillera de tipos mezclados y
solapados, unida por un CORDAL (collados) en dos planos de profundidad;
penascos de bloques facetados para cimas de colinas y acantilados; y
LOMAS (redondas o alargadas) para dar altibajos alrededor del circuito.

100 % procedural (from_pydata + bmesh solo para normales; sin bpy.ops,
sin texturas de imagen). Materiales por nombre, reutilizados si existen
(el integrador los recolorea y textura por nombre):
  MAT_MONT_bosque, MAT_MONT_bosque_claro              laderas verdes
  MAT_MONT_roca, MAT_MONT_roca_clara, MAT_MONT_roca_oscura  estratos
Orden de slots en todas las mallas: 0 bosque, 1 bosque_claro, 2 roca,
3 roca_clara, 4 roca_oscura. Roca con sombreado plano (facetas), bosque
suave.

Reparto de materiales (por cara): pendiente SUAVIZADA por vecindad (2
pasos sobre el anillo de caras vecinas) + altura (linea de arboles
ondulada). Bajo la linea de arboles solo hay roca en paredes reales
(> pend_pared) y en espolones marcados (aguja/piramide/cresta); las
manchas de roca de < 40 caras bajo la linea de arboles y las islas de
< 12 caras (roca o bosque) se eliminan. El rayado claro/oscuro de
espolones y barrancos se limita a las caras con normal.z < 0.5 de
aguja/piramide/cresta y usa solo roca/roca_clara (meseta y domo sin rayas).

API (metros; origen en el centro de la base, z=0 = suelo; frente a +Y):
  build_pico(parent_collection, alto=180.0, radio=110.0, seed=0, **kw)
      -> malla 'MONT_pico' (<= 12k tris; propiedades ob['mont_tipo'],
         ob['mont_alto'], ob['mont_radio']).  kw:
         tipo='aguja'|'domo'|'meseta'|'cresta'|'piramide'|None (aleatorio
              por seed; si alto < 0.9*radio se eligen formas anchas)
         largo_cresta=float  longitud total de la cresta a lo largo de X
              local (defecto 2.6*radio); solo tipo 'cresta'
         pie=True            pie de derrubios (30-35 grados) hundido 6 m
              bajo z=0 para fundirse con el terreno; False: base en z=0
         res=1.0             factor de resolucion (anillos x segmentos)
         pend_bosque=35.0    ladera mas suave que esto: SIEMPRE bosque/prado
              (pie, hombros, repisas), salvo la cresta cimera (> 0.85 alto)
         pend_pared=None     ladera mas empinada que esto: SIEMPRE roca
              (defecto 70 grados; 74 en el domo, de base mas empinada);
              entre ambas decide la linea de arboles (bosque debajo,
              roca desnuda encima)
         estratos=True       repisas geometricas de estratos en la pared
         gendarmes=True      (solo 'aguja') 1-2 torres secundarias
         linea_arboles=None  cota de la linea de arboles como fraccion de
              alto (defecto segun tipo, 0.40-0.58); >1 = TODO verde,
              tambien la cresta cimera (colinas)
         rugosidad=1.0       amplitud del ruido fbm de las laderas
       'radio' = radio nominal de la base en z=0 (el contorno real varia
       +-25 % por espolones, canales y asimetria); el pie llega a
       ~radio+10 m en z=-6. Ningun vertice baja de z=-6.
       El domo remata en casquete romo (3 anillos de cierre, sin cresta
       dentada); la meseta tiene cima plana con 1-2 muescas en el borde.
  build_cordillera(parent_collection, largo=900.0, n_picos=5, seed=0,
                   alto=195.0, **kw)
      -> Empty 'MONT_cordillera' (hijos: n_picos mallas MONT_pico y la
         malla MONT_cordal), a lo largo de X centrada en el origen, telon
         hacia +Y: fila delantera (y>0) mas baja y boscosa, fila trasera
         (y<0) mas alta (silueta); tipos mezclados, solapados y unidos por
         el cordal (collados a media altura + banco de base). <= 60k tris.
         Propiedades: root['mont_tipos'] y root['mont_x_min'], 'mont_x_max',
         'mont_y_min', 'mont_y_max' = extension del cordal en coordenadas
         locales (la falda hundida del cordal, z=-6..+3, llega ~1.5*radio
         por delante y por detras de los picos: colocar la cadena de modo
         que esa extension quede DENTRO del terreno).
  build_pena(parent_collection, alto=30.0, radio=22.0, seed=0)
      -> malla 'MONT_pena' (<= 3k tris): creston de 5-7 bloques facetados
         (superelipsoides p=5-8, 8 segmentos x 4-5 anillos, seccion
         rectangular 1.6-2.2:1) con estratos inclinados (cizalla 12-22
         grados, bandas clara/oscura de alto/4) sobre un monticulo verde de
         derrubios (~20 grados, 0.8*radio) hundido hasta z=-6. Para cimas
         de colinas y bordes de acantilado.
  build_loma(parent_collection, alto=28.0, radio=70.0, seed=0, pena=True,
             largo=None)
      -> Empty 'MONT_loma' (hijos MONT_pico todo verde + MONT_pena en la
         cima): colina suave para dar ALTIBAJOS alrededor del circuito
         (no solo montanas al fondo). largo=None: domo redondo; largo=L:
         loma alargada (cresta de L m a lo largo de X local con 2-4
         cumbres y collados) para bordear tramos de pista.
  build(parent_collection, seed=0, **params) -> build_cordillera
"""

import bisect
import math
import random

import bpy
import bmesh
from mathutils import Vector

# ---------------------------------------------------------------- ruido ----
try:
    from mathutils import noise as _mnoise

    def _n3(x, y, z):
        return _mnoise.noise(Vector((x, y, z)))
except Exception:  # fallback puro python (valor-ruido trilineal)
    def _h(ix, iy, iz):
        n = (ix * 374761393 + iy * 668265263 + iz * 1440662683) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

    def _n3(x, y, z):
        ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
        fx, fy, fz = x - ix, y - iy, z - iz

        def s(t):
            return t * t * (3.0 - 2.0 * t)

        fx, fy, fz = s(fx), s(fy), s(fz)
        v = 0.0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = ((fx if dx else 1 - fx) * (fy if dy else 1 - fy) *
                         (fz if dz else 1 - fz))
                    v += w * _h(ix + dx, iy + dy, iz + dz)
        return v * 2.0 - 1.0


def _fbm(x, y, z, so):
    """3 octavas a escala de montaña (metros): masas, lomas y grano."""
    return (_n3(x * 0.008 + so, y * 0.008 + so * 0.7, z * 0.008) * 10.0 +
            _n3(x * 0.030 + so * 2.1, y * 0.030 + 11.3, z * 0.030) * 3.8 +
            _n3(x * 0.090 + so * 3.3, y * 0.090 + 23.7, z * 0.090 + 5.1) * 1.4)


def _sstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def _wrap(a):
    """Ángulo a (-pi, pi]."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _ondula(x, y, so, amp):
    """Plegamiento de los estratos: desplazamiento vertical (m) de baja
    frecuencia (longitud de onda ~250 m) y amplitud amp, con un poco de
    detalle. La MISMA función desplaza las repisas geométricas y las
    bandas de material, para que coincidan."""
    return amp * (_n3(x * 0.004 + so, y * 0.004, 4.4) +
                  0.35 * _n3(x * 0.011 + so * 1.9, y * 0.011, 9.1))


def _pchip(pts, x):
    """Interpolación cúbica MONÓTONA (Hermite, pendientes armónicas) sobre
    puntos (x, y) con x creciente: sin rebotes en los hombros/escalones."""
    n = len(pts)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0.0:
            m[i] = 0.0
        else:
            m[i] = 2.0 * d[i - 1] * d[i] / (d[i - 1] + d[i])
    for i in range(n - 1):
        if xs[i] <= x <= xs[i + 1]:
            h = xs[i + 1] - xs[i]
            t = (x - xs[i]) / h
            t2, t3 = t * t, t * t * t
            return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i] +
                    (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1])
    return pts[-1][1]


def _poly(th, n):
    """Factor [0..1] de un polígono regular de n lados en polares: 0 en el
    centro de cada cara, 1 en las aristas (esquinas vivas)."""
    sec = 2.0 * math.pi / n
    a = (th % sec) - sec * 0.5
    c = math.cos(math.pi / n)
    return (c / math.cos(a) - c) / (1.0 - c)


def _phis_elipse(esc_x, n):
    """n ángulos paramétricos (simétricos respecto a 0) que reparten los
    vértices de forma uniforme en longitud de arco sobre la elipse de
    semiejes (esc_x, 1). Para el círculo son los n ángulos uniformes."""
    if abs(esc_x - 1.0) < 1e-6:
        return [2.0 * math.pi * k / n for k in range(n)]
    m = 720
    acc = [0.0]
    for i in range(1, m + 1):
        p0, p1 = math.pi * (i - 1) / m, math.pi * i / m
        dx = esc_x * (math.cos(p1) - math.cos(p0))
        dy = math.sin(p1) - math.sin(p0)
        acc.append(acc[-1] + math.hypot(dx, dy))
    half = n // 2
    mitad = [0.0]
    for k in range(1, half):
        objetivo = acc[-1] * k / half
        j = 1
        while acc[j] < objetivo:
            j += 1
        f = (objetivo - acc[j - 1]) / max(acc[j] - acc[j - 1], 1e-9)
        mitad.append(math.pi * (j - 1 + f) / m)
    mitad.append(math.pi)
    return mitad + [2.0 * math.pi - p for p in reversed(mitad[1:-1])]


# ------------------------------------------------------------ materiales ----
def _mat(name, color, rough=0.95):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    if m.node_tree is None:            # Blender < 5: activar el arbol de nodos
        m.use_nodes = True             # (en 5.x ya viene creado; use_nodes
    bsdf = None                        # esta obsoleto y se elimina en 6.0)
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            bsdf = n
            break
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*color, 1.0)
    return m


def _materiales_mont():
    """Los 5 materiales del kit, en el orden de slots del contrato."""
    return (
        _mat("MAT_MONT_bosque", (0.085, 0.235, 0.050), 0.95),
        _mat("MAT_MONT_bosque_claro", (0.150, 0.340, 0.080), 0.95),
        _mat("MAT_MONT_roca", (0.480, 0.380, 0.250), 0.95),
        _mat("MAT_MONT_roca_clara", (0.620, 0.510, 0.350), 0.95),
        _mat("MAT_MONT_roca_oscura", (0.330, 0.250, 0.155), 0.95),
    )


def _malla(nombre, verts, faces, parent_collection, recalc=True):
    """Crea la malla + objeto, normales coherentes (bmesh), 5 slots.
    recalc=False para campos de altura abiertos (ya orientados a +Z)."""
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    me.validate()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    for m in _materiales_mont():
        me.materials.append(m)
    ob = bpy.data.objects.new(nombre, me)
    parent_collection.objects.link(ob)
    return ob


# ----------------------------------------------------------- tipos de pico --
# perfil: radio normalizado del CUERPO (1 en la base del cuerpo, sobre el
# pie) frente a u = altura normalizada 0..1 (anillo superior).
# lados/arista/twist: sección poligonal (aristas vivas) y su giro con u.
# canal: profundidad de los canales (barrancos) que bajan por los flancos.
# ridged: espolones/contrafuertes de ruido "ridged". estr: relieve (m) de
# las repisas de estratos. crown: cresta cimera dentada (0 = lisa).
# asym: una cara mas vertical (radio menor en esa cara). lean: la cima se
# desplaza hacia la cara vertical. cap: remate ('apex' punta, 'flat' cima
# plana con muescas, 'strip' linea de cumbres, 'domo' casquete romo con
# anillos de cierre). tl: linea de arboles (fraccion de alto). rayas:
# espolones claros / barrancos oscuros en la roca. pared: pend_pared propia.
_TIPOS = {
    "aguja": dict(
        perfil=[(0.0, 1.0), (0.12, 0.72), (0.25, 0.52), (0.45, 0.40),
                (0.65, 0.30), (0.82, 0.21), (0.94, 0.13), (1.0, 0.07)],
        lados=3, arista=0.36, twist=0.35, canal=0.16, ridged=0.40, estr=0.8,
        crown=0.05, asym=0.14, lean=0.10, cap="apex", tl=0.40, rug=0.8,
        rayas=True),
    "piramide": dict(
        perfil=[(0.0, 1.0), (0.22, 0.76), (0.45, 0.53), (0.66, 0.34),
                (0.84, 0.18), (0.95, 0.08), (1.0, 0.04)],
        lados=4, arista=0.50, twist=0.12, canal=0.28, ridged=0.22, estr=1.2,
        crown=0.04, asym=0.22, lean=0.12, cap="apex", tl=0.50, rug=0.9,
        rayas=True),
    "meseta": dict(
        perfil=[(0.0, 1.0), (0.22, 0.76), (0.42, 0.66), (0.55, 0.63),
                (0.66, 0.625), (0.80, 0.62), (0.92, 0.615), (1.0, 0.60)],
        lados=5, arista=0.26, twist=0.0, canal=0.30, ridged=0.16, estr=3.2,
        crown=0.0, asym=0.16, lean=0.03, cap="flat", tl=0.58, rug=0.8,
        rayas=False, n_bandas=6.0),
    # n_bandas: numero nominal de estratos en 'alto' (defecto 9; la meseta
    # menos y mas gruesos, para no leerse como pila de tortitas)
    "cresta": dict(
        perfil=[(0.0, 1.0), (0.22, 0.76), (0.45, 0.55), (0.66, 0.38),
                (0.84, 0.24), (0.95, 0.14), (1.0, 0.08)],
        lados=0, arista=0.0, twist=0.0, canal=0.20, ridged=0.36, estr=1.5,
        crown=0.05, asym=0.18, lean=0.06, cap="strip", tl=0.50, rug=1.0,
        rayas=True),
    # domo: perfil convexo (pendiente que decrece hacia arriba) rematado en
    # casquete romo (_CAP_DOMO); base mas empinada -> pared propia de 74
    "domo": dict(
        perfil=[(0.0, 1.0), (0.10, 0.955), (0.24, 0.90), (0.44, 0.80),
                (0.62, 0.70), (0.77, 0.60), (0.89, 0.50), (1.0, 0.40)],
        lados=0, arista=0.0, twist=0.0, canal=0.14, ridged=0.16, estr=2.4,
        crown=0.0, asym=0.16, lean=0.05, cap="domo", tl=0.50, rug=1.1,
        rayas=False, pared=76.0, tl_var=0.16),
    # tl_var: amplitud (fraccion de alto) de la ondulacion en planta de la
    # linea de arboles (defecto 0.10; el domo mas, para que la roca cimera
    # no sea un casquete cortado en horizontal)
}
TIPOS = tuple(_TIPOS)                      # orden canónico
_TIPOS_ANCHOS = ("domo", "meseta", "cresta")
_Z_PIE = -6.0                              # cota del borde del pie hundido
_PATRON_ROCA = (2, 2, 3, 2, 4, 2)          # estratos: roca, clara, roca, oscura
_Z_TOP = {"apex": 0.95, "domo": 0.85}      # cota del ultimo anillo / alto
# anillos de cierre del domo: (factor de radio, fraccion de la subida hasta
# el apice) -> pendientes 34, 26, 16 y 9 grados: casquete redondeado
_CAP_DOMO = ((0.75, 0.39), (0.50, 0.69), (0.25, 0.90))


def _ridged(th, u, so):
    """Ruido 'ridged' angular (espolones que bajan por los flancos): 1 en
    la arista del espolón, 0 en el barranco; varía despacio con la altura
    para que los espolones sean verticales."""
    cx, sx = math.cos(th), math.sin(th)
    r = 1.0 - abs(_n3(cx * 3.6 + so, sx * 3.6, u * 0.9 + 3.3))
    return r * r


def _cumbres_cresta(rng):
    """Línea de cumbres de una cresta: H(s) en [0.45..1] con s en [-1, 1]
    (2-4 cumbres separadas por collados)."""
    n_c = rng.randint(2, 4)
    cumbres = []
    for j in range(n_c):
        s_j = -0.70 + 1.40 * (j + 0.5) / n_c + rng.uniform(-0.08, 0.08)
        a_j = 1.0 if j == rng.randrange(n_c) else rng.uniform(0.70, 0.92)
        w_j = rng.uniform(0.14, 0.24)
        cumbres.append((s_j, a_j, w_j))
    # una de ellas es la principal
    j_max = max(range(n_c), key=lambda j: cumbres[j][1])
    cumbres[j_max] = (cumbres[j_max][0], 1.0, cumbres[j_max][2])

    def H(s):
        b = 0.0
        for (s_j, a_j, w_j) in cumbres:
            b = max(b, a_j * math.exp(-((s - s_j) / w_j) ** 2))
        return 0.45 + 0.55 * b
    return H


def _bandas_estratos(rng, z_f, z_top, band_h):
    """Cotas de los estratos: espesor variable (+-30 %) y alguna repisa
    saltada (amplitud 0: cambia el material pero no hay repisa). Lista de
    (z, amplitud) creciente en z."""
    bandas = []
    z = z_f + band_h * rng.uniform(0.6, 1.1)
    while z < z_top + band_h:
        amp = 0.0 if rng.random() < 0.22 else rng.uniform(0.7, 1.3)
        bandas.append((z, amp))
        z += band_h * rng.uniform(0.7, 1.3)
    return bandas


def _pico_geometry(alto, radio, seed, tipo, cfg, largo_cresta, pie, nz, narc,
                   rug):
    """Vértices y caras de un pico: loft radial de anillos (pie + cuerpo)
    con sección poligonal, canales, espolones ridged, asimetría, estratos
    plegados y remate según el tipo. Devuelve (verts, faces, info)."""
    so = seed * 23.71 + 7.3
    rng = random.Random(int(seed) * 977 + 13)
    tan_pie = math.tan(math.radians(rng.uniform(30.0, 35.0)))
    z_bot = _Z_PIE if pie else 0.0
    z_f = max(6.0, 0.08 * alto)                 # cota donde acaba el pie
    r_f = max(radio - z_f / tan_pie, radio * 0.55)   # radio del cuerpo en z_f
    cap = cfg["cap"]
    z_top = alto * _Z_TOP.get(cap, 1.0)
    esc_x = 1.0
    a_x = radio
    H = None
    if tipo == "cresta":
        a_x = 0.5 * (largo_cresta if largo_cresta else 2.6 * radio)
        esc_x = max(a_x / radio, 1.0)
        H = _cumbres_cresta(rng)
    th_a = rng.uniform(0.0, 2.0 * math.pi)      # dirección de la cara vertical
    asym = cfg["asym"] * rng.uniform(0.8, 1.2)
    lean = cfg["lean"] * radio * rng.uniform(0.7, 1.3)
    lx, ly = math.cos(th_a) * lean, math.sin(th_a) * lean
    th_poly = rng.uniform(0.0, 2.0 * math.pi)
    canales = [(rng.uniform(0.0, 2.0 * math.pi), rng.uniform(0.08, 0.18),
                rng.uniform(0.6, 1.0)) for _ in range(rng.randint(3, 5))]
    crown = cfg["crown"] * rng.uniform(0.7, 1.3)
    band_h = max(9.0, alto / cfg.get("n_bandas", 9.0))
    esc_rel = _clamp(alto / 140.0, 0.3, 1.0)    # picos bajos: relieve menor
    rug *= esc_rel
    estr = cfg["estr"] * esc_rel
    bandas = _bandas_estratos(rng, z_f, z_top, band_h)
    amp_pl = 0.5 * band_h                       # amplitud del plegamiento
    muescas = []                                # (angulo, anchura, prof/alto)
    if cap == "flat":
        muescas = [(rng.uniform(0.0, 2.0 * math.pi), rng.uniform(0.16, 0.28),
                    rng.uniform(0.05, 0.09)) for _ in range(rng.randint(1, 2))]
    phis = _phis_elipse(esc_x, narc)

    verts, faces, rings = [], [], []
    for i in range(nz):
        t = i / (nz - 1.0)
        z0 = z_bot + (z_top - z_bot) * t
        if z0 < z_f:                              # PIE de derrubios
            u, en_pie = 0.0, True
            r_perfil = r_f + (z_f - z0) / tan_pie   # se ensancha hacia abajo
        else:
            u, en_pie = _clamp((z0 - z_f) / (z_top - z_f), 0.0, 1.0), False
            r_perfil = r_f * _pchip(cfg["perfil"], u)
        wall = _sstep((u - 0.28) / 0.25)          # zona de pared con estratos
        ox, oy = lx * u ** 1.5, ly * u ** 1.5      # la cima se inclina
        ring = []
        for k in range(narc):
            th = phis[k]
            cx, sx = math.cos(th), math.sin(th)
            # --- modulación angular (aditiva y acotada: contorno ~ radio)
            d = 0.0
            if cfg["lados"]:
                d += cfg["arista"] * (_poly(th - th_poly - cfg["twist"] * u,
                                            cfg["lados"]) - 0.5)
            for (thc, wc, dc) in canales:
                dth = _wrap(th - thc)
                d -= cfg["canal"] * dc * math.exp(-(dth / wc) ** 2) * \
                    (1.0 - u) ** 0.5
            rid = _ridged(th, u, so)
            d += cfg["ridged"] * (rid - 0.35) * (0.6 + 0.4 * u)
            d -= asym * math.cos(th - th_a) * (1.0 - u) ** 1.3
            r = r_perfil * _clamp(1.0 + d, 0.66, 1.40)
            px, py = cx * r * esc_x, sx * r
            r += _fbm(px, py, z0, so) * rug * (0.45 if en_pie else 1.0)
            # --- repisas de estratos plegados en la pared (espesor variable)
            led = 0.0
            if estr > 0.0 and wall > 0.0 and not (cap == "flat" and u > 0.96):
                zp = z0 - _ondula(px, py, so, amp_pl)
                for (zk, ak) in bandas:
                    tk = (zp - zk) / (0.30 * band_h)
                    if -1.0 < tk < 1.0:
                        led += ak * (1.0 - tk * tk) ** 2
                led *= estr * wall
                if cap == "domo":                 # sin repisa en el hombro
                    led *= 1.0 - _sstep((u - 0.78) / 0.22)   # del casquete
            r = max(r + led, radio * 0.03)
            px, py = ox + cx * r * esc_x, oy + sx * r
            z = z0 - led * 0.35
            if H is not None:                     # cumbres y collados
                z = z_bot + (z - z_bot) * (1.0 - u * u * (1.0 - H(px / a_x)))
            if crown > 0.0 and cap in ("apex", "strip"):   # cresta dentada
                z += alto * min(crown, 0.05) * rid * u ** 3
            z += _n3(px * 0.02 + so * 1.7, py * 0.02, 2.2) * 2.5 * esc_rel * \
                math.sin(math.pi * t)
            if cap == "flat":
                if i == nz - 1:
                    z = alto
                for (thm, wm, dm) in muescas:     # muescas en el borde cimero
                    z -= alto * dm * math.exp(-(_wrap(th - thm) / wm) ** 2) * \
                        _sstep((u - 0.78) / 0.22)
            ring.append(len(verts))
            verts.append((px, py, max(z, z_bot)))
        rings.append(ring)

    cxc, cyc = lx, ly
    if cap == "domo":                             # casquete romo: 3 anillos
        last = rings[-1]                          # de cierre hacia el apice
        cxc = sum(verts[j][0] for j in last) / narc
        cyc = sum(verts[j][1] for j in last) / narc
        for (f, zf) in _CAP_DOMO:
            ring = []
            for j in last:
                x, y, z = verts[j]
                fj = f * (1.0 + 0.06 * _n3(x * 0.03 + so, y * 0.03, zf * 4.0))
                ring.append(len(verts))
                verts.append((cxc + (x - cxc) * fj, cyc + (y - cyc) * fj,
                              z_top + (alto - z_top) * zf + (z - z_top) * f * 0.5
                              + 0.8 * esc_rel * _n3(x * 0.05, y * 0.05 + so, zf)))
            rings.append(ring)

    # --- caras laterales
    for a, b in zip(rings, rings[1:]):
        for k in range(narc):
            k2 = (k + 1) % narc
            faces.append((a[k], a[k2], b[k2], b[k]))
    top = rings[-1]
    if cap == "strip":                            # línea de cumbres (cremallera)
        half = narc // 2
        for k in range(half):
            q = (top[k], top[k + 1], top[(narc - k - 1) % narc],
                 top[(narc - k) % narc])
            q = tuple(dict.fromkeys(q))            # quita repetidos (extremos)
            if len(q) >= 3:
                faces.append(q)
        z_cima = max(verts[j][2] for j in top)
    else:                                         # punta / cima plana / domo
        apex = len(verts)
        z_ap = alto + (0.8 if cap == "flat" else 0.0)
        if cap == "domo":
            verts.append((cxc, cyc, z_ap))
        else:
            verts.append((lx + _n3(so, 1.1, 2.2) * radio * 0.04,
                          ly + _n3(so, 5.7, 8.8) * radio * 0.04, z_ap))
        for k in range(narc):
            faces.append((apex, top[(k + 1) % narc], top[k]))
        z_cima = z_ap
    base = len(verts)
    verts.append((0.0, 0.0, z_bot))
    for k in range(narc):
        faces.append((base, rings[0][k], rings[0][(k + 1) % narc]))
    info = dict(tipo=tipo, z_cima=z_cima, th_cara=th_a, band_h=band_h,
                z_bot=z_bot, bandas=bandas, amp_pl=amp_pl)
    return verts, faces, info


# ------------------------------------------------------------ materiales ----
def _vecinos_caras(me):
    """Caras vecinas por arista de cada cara (lista de listas)."""
    edge_faces = {}
    for p in me.polygons:
        for ek in p.edge_keys:
            edge_faces.setdefault(ek, []).append(p.index)
    vecinos = [[] for _ in me.polygons]
    for fs in edge_faces.values():
        for a in fs:
            for b in fs:
                if a != b:
                    vecinos[a].append(b)
    return vecinos


def _componentes(indices, vecinos):
    """Componentes conexas (por arista) del conjunto de caras dado."""
    pend = set(indices)
    comps = []
    while pend:
        s = pend.pop()
        comp, pila = [s], [s]
        while pila:
            a = pila.pop()
            for b in vecinos[a]:
                if b in pend:
                    pend.discard(b)
                    pila.append(b)
                    comp.append(b)
        comps.append(comp)
    return comps


def _mayoria(roca, vecinos, forz, pasos=2):
    """Filtro de mayoría por adyacencia: quita caras de roca sueltas en el
    bosque (y al revés) para que las fronteras sigan la ladera."""
    for _ in range(pasos):
        nuevo = list(roca)
        for i, vs in enumerate(vecinos):
            if len(vs) < 3 or forz[i]:
                continue
            n_r = sum(1 for v in vs if roca[v])
            if roca[i] and n_r <= len(vs) * 0.34:
                nuevo[i] = False
            elif not roca[i] and n_r >= len(vs) * 0.66:
                nuevo[i] = True
        roca = nuevo
    return roca


def _asignar_materiales(me, alto, seed, tl_frac, pend_bosque, bandas,
                        z_bot=_Z_PIE, roca_extra=None, espolones=0.0,
                        pend_pared=70.0, amp_pl=0.0, tl_var=0.10):
    """Material POR CARA: pendiente SUAVIZADA + altura (línea de árboles).

    La pendiente de cada cara es la media de normal.z sobre su anillo de
    vecinas (2 pasos), para que las fronteras no sigan la rejilla.
    - pie y falda baja (< 1.5 m sobre el suelo, no vertical): bosque
    - ladera suave (< pend_bosque, 35 grados): siempre bosque/prado
      (repisas, hombros, collados), salvo la cresta cimera (> 0.85 alto;
      no si tl_frac > 1: colinas todo verdes)
    - pared (> pend_pared): roca; por debajo de la línea de árboles solo
      si es una pared de verdad (> pend_pared + 6 grados)
    - línea de árboles ondulada en planta y acoplada al relieve: baja en
      los espolones (la roca desciende por las aristas) y sube en los
      barrancos (el bosque trepa por las canales) -> frontera diagonal,
      no escalones horizontales de la rejilla
    - laderas medias: roca por encima de la línea de árboles; por debajo
      solo en espolones marcados (si espolones > 0), que se estrechan y
      desaparecen hacia el pie (umbral de rid creciente hacia abajo)
    - limpieza: mayoría por vecindad, manchas de roca < 40 caras bajo la
      línea de árboles -> bosque, islas < 12 caras (roca o bosque) fuera
    - roca en bandas de estratos ('bandas': cotas, plegadas con _ondula)
      con materiales alternos roca / clara / roca / oscura; con
      espolones > 0 y normal.z < 0.5, espolón = clara y barranco = roca
    - roca: sombreado plano (facetas); bosque: suave
    roca_extra: lista opcional (por índice de cara) de bool que fuerza roca.
    """
    so = seed * 23.71 + 7.3
    cos_b = math.cos(math.radians(pend_bosque))      # siempre bosque
    cos_p = math.cos(math.radians(pend_pared))       # siempre roca (pared)
    cos_p2 = math.cos(math.radians(min(pend_pared + 6.0, 86.0)))  # bajo la tl
    todo_verde = tl_frac > 1.0
    zs_b = [b[0] for b in bandas]
    me.update()
    polys = me.polygons
    n_f = len(polys)
    vecinos = _vecinos_caras(me)
    nzs = [p.normal.z for p in polys]
    for _ in range(2):                               # pendiente suavizada
        nzs = [(nzs[i] + sum(nzs[j] for j in vs)) / (1.0 + len(vs))
               for i, vs in enumerate(vecinos)]
    roca = [False] * n_f
    bajo_tl = [False] * n_f
    forz = [False] * n_f
    for p in polys:
        i = p.index
        c = p.center
        nz = nzs[i]
        th = math.atan2(c.y, c.x)
        rid = _ridged(th, _clamp(c.z / alto, 0.0, 1.0), so)
        cth, sth = math.cos(th), math.sin(th)
        tl = alto * (tl_frac + tl_var * (_n3(cth * 1.4 + so, sth * 1.4, 1.1) +
                                         0.5 * _n3(cth * 3.1 + so * 2.0, sth * 3.1, 2.2))
                     + 0.08 * (0.5 - rid))      # baja en espolones, sube en canales
        forzada = bool(roca_extra and roca_extra[i])
        forz[i] = forzada
        if c.z < z_bot + 0.6:                  # tapa inferior (enterrada)
            r = False
        elif forzada:
            r = True
        elif c.z < 1.5 and nz > 0.45:          # falda que muere en el suelo
            r = False
        elif nz < cos_p:                       # pared / farallón
            r = c.z > tl or nz < cos_p2        # bajo la tl: solo pared real
        elif nz > cos_b:                       # ladera suave (< pend_bosque)
            r = c.z > 0.85 * alto and not todo_verde   # ...salvo cresta cimera
        elif c.z > tl:                         # ladera media sobre la línea
            r = True
        else:                                  # ...y debajo: solo espolones,
            r = (espolones > 0.0 and nz < 0.5 and   # que se estrechan al bajar
                 rid > 0.62 + 0.30 * (1.0 - _clamp(c.z / max(tl, 1.0), 0.0, 1.0)))
        roca[i] = r
        bajo_tl[i] = c.z < tl
    roca = _mayoria(roca, vecinos, forz)
    for comp in _componentes([i for i in range(n_f) if roca[i] and not forz[i]],
                             vecinos):
        n = len(comp)
        if n < 12 or (n < 40 and all(bajo_tl[i] for i in comp)):
            for i in comp:
                roca[i] = False
    for comp in _componentes([i for i in range(n_f) if not roca[i]], vecinos):
        if len(comp) < 12:
            for i in comp:
                roca[i] = True
    for p in polys:
        i = p.index
        c = p.center
        if roca[i]:
            zp = c.z - _ondula(c.x, c.y, so, amp_pl)
            b = bisect.bisect_right(zs_b, zp)
            idx = _PATRON_ROCA[b % len(_PATRON_ROCA)]
            if espolones > 0.0 and nzs[i] < 0.5:   # espolón claro / barranco
                rid = _ridged(math.atan2(c.y, c.x),
                              _clamp(c.z / alto, 0.0, 1.0), so)
                if rid > 0.62:
                    idx = 3
                elif rid < 0.10:
                    idx = 2
            if p.normal.z < -0.25:             # techos de repisa: sombra
                idx = 4
            p.material_index = idx
            p.use_smooth = False
        else:
            pn = _n3(c.x * 0.012 + so * 1.3, c.y * 0.012, c.z * 0.012 + 6.6)
            p.material_index = 1 if pn > 0.22 else 0
            p.use_smooth = True


# ----------------------------------------------------------------- piezas ----
def _elegir_tipo(alto, radio, seed):
    rng = random.Random(int(seed) * 7919 + 3)
    opciones = _TIPOS_ANCHOS if alto < 0.9 * radio else TIPOS
    return opciones[rng.randrange(len(opciones))]


def _res_pico(tipo, res):
    """(anillos, segmentos) para un factor de resolución; segmentos par."""
    if tipo == "cresta":
        nz, narc = 48, 104
    elif tipo == "aguja":                       # deja sitio a los gendarmes
        nz, narc = 48, 76
    elif tipo == "domo":                        # 3 anillos de cierre extra
        nz, narc = 53, 88
    else:
        nz, narc = 56, 88
    nz = max(12, int(round(nz * res)))
    narc = max(16, int(round(narc * res)) // 2 * 2)
    return nz, narc


def build_pico(parent_collection, alto=180.0, radio=110.0, seed=0, **kw):
    """Pico rocoso individual MONT_pico (<= 12k tris). Ver docstring."""
    tipo = kw.get("tipo")
    if tipo is None:
        tipo = _elegir_tipo(alto, radio, seed)
    if tipo not in _TIPOS:
        raise ValueError("tipo de pico desconocido: %r (validos: %s)" %
                         (tipo, ", ".join(TIPOS)))
    cfg = _TIPOS[tipo]
    nz, narc = _res_pico(tipo, float(kw.get("res", 1.0)))
    pie = bool(kw.get("pie", True))
    rug = float(kw.get("rugosidad", 1.0))
    if not kw.get("estratos", True):
        cfg = dict(cfg, estr=0.0)
    verts, faces, info = _pico_geometry(
        alto, radio, seed, tipo, cfg, kw.get("largo_cresta"), pie, nz, narc, rug)
    if tipo == "aguja" and kw.get("gendarmes", True):
        # torres secundarias (gendarmes) pegadas a la aguja principal:
        # lofts cerrados más pequeños fundidos en la misma malla
        rng = random.Random(int(seed) * 53 + 11)
        th0 = rng.uniform(0.0, 2.0 * math.pi)
        for j in range(rng.randint(1, 2)):
            th = th0 + j * rng.uniform(1.6, 2.6)
            dist = radio * rng.uniform(0.42, 0.58)
            v2, f2, _ = _pico_geometry(
                alto * rng.uniform(0.52, 0.72), radio * rng.uniform(0.40, 0.50),
                seed * 7 + j + 1, "aguja", cfg, None, pie,
                max(12, nz // 2), max(16, (narc * 2 // 5) // 2 * 2), rug)
            off = len(verts)
            dx, dy = math.cos(th) * dist, math.sin(th) * dist
            verts.extend((x + dx, y + dy, z) for (x, y, z) in v2)
            faces.extend(tuple(i + off for i in f) for f in f2)
    ob = _malla("MONT_pico", verts, faces, parent_collection)
    tl = kw.get("linea_arboles")
    pared = kw.get("pend_pared")
    _asignar_materiales(ob.data, alto, seed,
                        cfg["tl"] if tl is None else float(tl),
                        float(kw.get("pend_bosque", 35.0)), info["bandas"],
                        z_bot=info["z_bot"],
                        espolones=1.0 if cfg.get("rayas") else 0.0,
                        pend_pared=(cfg.get("pared", 70.0) if pared is None
                                    else float(pared)),
                        amp_pl=info["amp_pl"], tl_var=cfg.get("tl_var", 0.10))
    ob["mont_tipo"] = tipo
    ob["mont_alto"] = float(alto)
    ob["mont_radio"] = float(radio)
    return ob


# ---------------------------------------------------------------- cordal ----
def _cordal_dims(picos):
    """Rejilla del cordal: (x0, y0, cell, nx, ny) cubriendo 1.5 radios
    alrededor de cada pico (el borde queda hundido a z=-6)."""
    x0 = min(p["x"] - p["r"] * 1.5 for p in picos)
    x1 = max(p["x"] + p["r"] * 1.5 for p in picos)
    y0 = min(p["y"] - p["r"] * 1.5 for p in picos)
    y1 = max(p["y"] + p["r"] * 1.5 for p in picos)
    cell = max(7.0, (x1 - x0) / 118.0)
    nx = int(math.ceil((x1 - x0) / cell)) + 1
    ny = int(math.ceil((y1 - y0) / cell)) + 1
    return x0, y0, cell, nx, ny


def _cordal_geometry(picos, seed):
    """Campo de alturas que une los picos: banco de base (lomas verdes
    alrededor de los pies) + collados a media altura entre picos vecinos
    (cresta redondeada de anchura ~radio). Devuelve (verts, faces, cresta)
    con cresta[i] en [0..1] = cercanía del vértice a la línea de cumbres."""
    so = seed * 5.31 + 1.7
    x0, y0, cell, nx, ny = _cordal_dims(picos)
    segs = list(zip(picos, picos[1:]))
    verts, cresta = [], []
    for j in range(ny):
        y = y0 + j * cell
        for i in range(nx):
            x = x0 + i * cell
            z_r, hs_best = 0.0, 1.0
            for (p, q) in segs:
                dx, dy = q["x"] - p["x"], q["y"] - p["y"]
                L2 = dx * dx + dy * dy
                s = _clamp(((x - p["x"]) * dx + (y - p["y"]) * dy) / L2, 0.0, 1.0)
                d = math.hypot(x - p["x"] - s * dx, y - p["y"] - s * dy)
                w = (p["r"] + (q["r"] - p["r"]) * s) * 0.95
                if d >= w:
                    continue
                h_col = 0.34 * min(p["h"], q["h"])
                h_end = 0.60 * (p["h"] if s < 0.5 else q["h"])
                hs = h_col + (h_end - h_col) * (abs(s - 0.5) * 2.0) ** 1.6
                hs *= 1.0 + 0.10 * _n3(s * 5.0 + so, p["x"] * 0.01, 1.5)
                zc = hs * (1.0 - (d / w) ** 2) ** 1.3
                if zc > z_r:
                    z_r, hs_best = zc, hs
            fade = 0.0
            irr = 1.0 + 0.16 * _n3(x * 0.006 + so, y * 0.006, 7.7)   # borde irregular
            for p in picos:
                dist = math.hypot(x - p["x"], y - p["y"])
                fade = max(fade, 1.0 - _sstep((dist / (p["r"] * irr) - 0.95) / 0.32))
            banco = (3.0 + 6.0 * _n3(x * 0.008 + so, y * 0.008, 1.0) +
                     2.5 * _n3(x * 0.030, y * 0.030 + so, 2.0))
            z = max(z_r, banco) + 3.0 * _n3(x * 0.02 + so * 2.0, y * 0.02, 3.3)
            z = _Z_PIE + (z - _Z_PIE) * fade
            verts.append((x, y, z))
            cresta.append((z_r / hs_best) * fade)
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    return verts, faces, cresta


def build_cordillera(parent_collection, largo=900.0, n_picos=5, seed=0,
                     alto=195.0, **kw):
    """Fila de picos de tipos mezclados, solapados y unidos por un cordal
    (Empty MONT_cordillera). Ver docstring del módulo. kw:
      tipos=lista   secuencia de tipos a usar (cíclica) en vez de mezcla
      pend_bosque, pend_pared, linea_arboles, rugosidad -> a cada pico."""
    root = bpy.data.objects.new("MONT_cordillera", None)
    root.empty_display_size = 10.0
    parent_collection.objects.link(root)

    rng = random.Random(seed * 31 + 7)
    n = max(1, int(n_picos))
    spacing = largo / n
    orden = list(TIPOS)
    rng.shuffle(orden)
    tipos = list(kw.get("tipos") or orden)
    picos = []
    for i in range(n):
        atras = (i % 2 == 1)
        tipo = tipos[i % len(tipos)]
        x = -largo * 0.5 + (i + 0.5) * spacing + rng.uniform(-0.10, 0.10) * spacing
        if atras:                                   # fila trasera: silueta alta
            factor = rng.uniform(0.88, 1.08)
            r = spacing * rng.uniform(0.66, 0.78)
            y = -rng.uniform(0.45, 0.65) * r
        else:                                       # fila delantera: baja, boscosa
            factor = rng.uniform(0.58, 0.78)
            r = spacing * rng.uniform(0.70, 0.84)
            y = rng.uniform(0.0, 0.15) * r
        largo_c = None
        rot = rng.uniform(0.0, 2.0 * math.pi)
        if tipo == "cresta":                        # alargada a lo largo de X
            r = spacing * rng.uniform(0.40, 0.48)
            largo_c = spacing * rng.uniform(1.4, 1.7)
            rot = rng.uniform(-0.30, 0.30) + (math.pi if rng.random() < 0.5 else 0.0)
        picos.append(dict(i=i, tipo=tipo, x=x, y=y, h=alto * factor, r=r,
                          largo_c=largo_c, rot=rot))
    # el pico trasero más central manda en la silueta
    dom = min((p for p in picos if p["i"] % 2 == 1 or n == 1),
              key=lambda p: abs(p["x"]), default=picos[0])
    dom["h"] = max(dom["h"], alto * 1.06)
    # radio efectivo para el cordal (la cresta es alargada)
    for p in picos:
        p["r_c"] = p["r"] if p["largo_c"] is None else 0.5 * (p["r"] + 0.5 * p["largo_c"])
    cord_in = [dict(x=p["x"], y=p["y"], h=p["h"], r=p["r_c"]) for p in picos]

    # presupuesto: <= 60k en total (cordal + picos)
    x0, y0, cell, nx, ny = _cordal_dims(cord_in)
    tris_cordal = (nx - 1) * (ny - 1) * 2
    objetivo = min(7400.0, (60000.0 - tris_cordal) / n)
    res = _clamp(math.sqrt(objetivo / 9900.0), 0.35, 1.0)

    extra = {k: kw[k] for k in ("pend_bosque", "pend_pared", "linea_arboles",
                                "rugosidad") if k in kw}
    for p in picos:
        pico = build_pico(parent_collection, alto=p["h"], radio=p["r"],
                          seed=seed * 13 + p["i"] * 101 + 5, tipo=p["tipo"],
                          res=res, largo_cresta=p["largo_c"], pie=True, **extra)
        pico.location = (p["x"], p["y"], 0.0)
        pico.rotation_euler = (0.0, 0.0, p["rot"])
        pico.parent = root

    verts, faces, cresta = _cordal_geometry(cord_in, seed)
    cordal = _malla("MONT_cordal", verts, faces, parent_collection, recalc=False)
    me = cordal.data
    alto_max = max(p["h"] for p in picos)
    band_h = max(9.0, alto_max / 9.0)
    roca_extra = [False] * len(me.polygons)
    for pg in me.polygons:
        cr = sum(cresta[v] for v in pg.vertices) / len(pg.vertices)
        roca_extra[pg.index] = cr > 0.86 and pg.center.z > 0.16 * alto_max
    bandas = [(k * band_h, 1.0) for k in range(1, int(alto_max / band_h) + 2)]
    _asignar_materiales(me, alto_max, seed + 7, 0.62,
                        float(kw.get("pend_bosque", 35.0)), bandas,
                        roca_extra=roca_extra,
                        pend_pared=float(kw.get("pend_pared", 70.0)),
                        amp_pl=0.4 * band_h)
    cordal.parent = root
    root["mont_tipos"] = ",".join(p["tipo"] for p in picos)
    root["mont_x_min"], root["mont_x_max"] = float(x0), float(x0 + (nx - 1) * cell)
    root["mont_y_min"], root["mont_y_max"] = float(y0), float(y0 + (ny - 1) * cell)
    return root


# ----------------------------------------------------------------- pena -----
def _bloque(verts, faces, ax, ay, h_half, p, nzb, narcb, so, rug, centro, yaw,
            pitch=0.0, jit=0.0):
    """Bloque de roca low-poly: superelipsoide (exponente p: 2 = elipsoide,
    5-8 = caja con aristas vivas y esquinas achaflanadas) como loft de
    pocos anillos + polos, con ruido de aristas y 'jitter' por vértice
    (facetas irregulares), cabeceo (pitch, bloque volcado) y giro (yaw).
    Añade a verts/faces y devuelve el rango de índices de cara (a, b)."""
    f0 = len(faces)
    e = 2.0 / p
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    rngj = random.Random(int(abs(so) * 1000.0) & 0xFFFFFF)

    def colocar(fx, fy, fz):
        if jit > 0.0:
            fx += rngj.uniform(-jit, jit) * ax
            fy += rngj.uniform(-jit, jit) * ay
            fz += rngj.uniform(-jit, jit) * h_half
        fx, fz = fx * cp + fz * sp, -fx * sp + fz * cp
        return [centro[0] + cy_ * fx - sy_ * fy,
                centro[1] + sy_ * fx + cy_ * fy, centro[2] + fz]

    rings = []
    for i in range(1, nzb + 1):
        v = -math.pi * 0.5 + math.pi * i / (nzb + 1)
        cv, sv = math.cos(v), math.sin(v)
        rz = math.copysign(abs(sv) ** e, sv) * h_half
        rf = abs(cv) ** e
        ring = []
        for k in range(narcb):
            u = 2.0 * math.pi * k / narcb
            cu, su = math.cos(u), math.sin(u)
            m = 1.0 + rug * (0.12 * _n3(cu * 1.5 + so, su * 1.5, v * 1.2) +
                             0.06 * _n3(cu * 4.0 + so * 2.0, su * 4.0, v * 3.0 + 1.0))
            fx = math.copysign(abs(cu) ** e, cu) * rf * ax * m
            fy = math.copysign(abs(su) ** e, su) * rf * ay * m
            ring.append(len(verts))
            verts.append(colocar(fx, fy, rz))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(narcb):
            k2 = (k + 1) % narcb
            faces.append((a[k], a[k2], b[k2], b[k]))
    top = len(verts)
    verts.append(colocar(0.0, 0.0, h_half))
    bot = len(verts)
    verts.append(colocar(0.0, 0.0, -h_half))
    for k in range(narcb):
        k2 = (k + 1) % narcb
        faces.append((top, rings[-1][k2], rings[-1][k]))
        faces.append((bot, rings[0][k], rings[0][k2]))
    return f0, len(faces)


def _falda(verts, faces, radio, so, rng, narcf=14):
    """Montículo verde de derrubios bajo el peñasco: cono bajo (~20 grados
    sobre el suelo, 0.8*radio) de borde irregular, hundido hasta z=-6 (no
    asoma como un disco). Devuelve el rango de caras (a, b)."""
    f0 = len(faces)
    perfil = ((-6.0, 1.00), (-3.6, 0.93), (-1.0, 0.80), (0.8, 0.58), (2.2, 0.32))
    ax, ay = 0.82 * radio, 0.70 * radio
    yaw = rng.uniform(0.0, 2.0 * math.pi)
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    rings = []
    for (z, f) in perfil:
        ring = []
        for k in range(narcf):
            u = 2.0 * math.pi * k / narcf
            cu, su = math.cos(u), math.sin(u)
            m = 1.0 + 0.14 * _n3(cu * 2.2 + so, su * 2.2, z * 0.25 + 3.0)
            fx, fy = cu * ax * f * m, su * ay * f * m
            dz = 0.5 * _n3(fx * 0.1 + so, fy * 0.1, 1.0) if z > -5.0 else 0.0
            ring.append(len(verts))
            verts.append([cy_ * fx - sy_ * fy, sy_ * fx + cy_ * fy, z + dz])
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(narcf):
            k2 = (k + 1) % narcf
            faces.append((a[k], a[k2], b[k2], b[k]))
    top = len(verts)
    verts.append([0.0, 0.0, 3.0])
    bot = len(verts)
    verts.append([0.0, 0.0, _Z_PIE])
    for k in range(narcf):
        k2 = (k + 1) % narcf
        faces.append((top, rings[-1][k2], rings[-1][k]))
        faces.append((bot, rings[0][k], rings[0][k2]))
    return f0, len(faces)


_PATRON_PENA = (3, 4)                       # estratos del peñasco: clara/oscura


def build_pena(parent_collection, alto=30.0, radio=22.0, seed=0, **kw):
    """Peñasco/afloramiento MONT_pena (<= 3k tris): crestón de bloques
    facetados (bloque principal + 4-6 bloques menores escalonados a lo
    largo de un eje, algunos volcados; superelipsoides p=5-8 de sección
    rectangular) sobre un montículo verde; estratos inclinados (cizalla
    12-22 grados aplicada a los bloques, cada uno hundido lo que la
    cizalla lo levantaría); base hundida (z min = -6)."""
    rng = random.Random(int(seed) * 4441 + 9)
    so = seed * 17.3 + 2.2
    verts, faces = [], []
    tilt = math.tan(math.radians(rng.uniform(12.0, 22.0)))
    tdir = rng.uniform(0.0, 2.0 * math.pi)
    tx, ty = tilt * math.cos(tdir), tilt * math.sin(tdir)
    eje = rng.uniform(0.0, 2.0 * math.pi)          # eje del crestón
    ex, ey = math.cos(eje), math.sin(eje)
    rangos = [("falda",) + _falda(verts, faces, radio, so, rng)]
    n_falda = len(verts)                            # la falda no se cizalla

    def bloque(ax, ay, hh, p, nzb, narcb, so_b, centro, yaw, pitch, jit):
        bx, by, bz = centro
        lift = bx * tx + by * ty                    # compensa la cizalla
        return _bloque(verts, faces, ax, ay, hh, p, nzb, narcb, so_b, 1.0,
                       (bx, by, bz - lift), yaw, pitch, jit)

    # bloque principal (ligeramente descentrado sobre el eje)
    hh = alto * 0.5 + 2.0
    d0 = radio * rng.uniform(-0.15, 0.15)
    ax = radio * rng.uniform(0.55, 0.65)
    rangos.append(("bloque",) + bloque(
        ax, ax / rng.uniform(1.6, 2.2), hh, rng.uniform(5.0, 8.0), 5, 8, so,
        (ex * d0, ey * d0, alto - hh), eje + rng.uniform(-0.3, 0.3),
        rng.uniform(-0.12, 0.12), 0.04))
    # bloques menores a lo largo del eje, escalonados hacia fuera
    n_b = rng.randint(4, 6)
    for j in range(n_b):
        lado = 1.0 if j % 2 == 0 else -1.0
        t = lado * radio * rng.uniform(0.40, 0.95)
        lat = radio * rng.uniform(-0.32, 0.32)
        h = alto * rng.uniform(0.32, 0.64) * (1.0 - 0.3 * abs(t) / radio)
        hh = h * 0.5 + 2.5
        ax = radio * rng.uniform(0.28, 0.42)
        rangos.append(("bloque",) + bloque(
            ax, ax / rng.uniform(1.5, 2.1), hh, rng.uniform(5.0, 7.5), 4, 8,
            so + j * 3.1, (ex * t - ey * lat, ey * t + ex * lat, h - hh),
            eje + rng.uniform(-0.5, 0.5), rng.uniform(-0.25, 0.25), 0.05))
    # estratos inclinados (cizalla de los bloques) y base plana hundida
    for v in verts[n_falda:]:
        v[2] = v[2] + v[0] * tx + v[1] * ty
    for v in verts:
        v[2] = max(v[2], _Z_PIE)
    ob = _malla("MONT_pena", [tuple(v) for v in verts], faces, parent_collection)
    me = ob.data
    me.update()
    band_h = max(3.0, alto / 4.0)
    tipo_cara = ["bloque"] * len(me.polygons)
    for (nombre, a, b) in rangos:
        for f in range(a, b):
            tipo_cara[f] = nombre
    for p in me.polygons:
        c = p.center
        nz = p.normal.z
        if tipo_cara[p.index] == "falda":
            if nz > 0.30 and c.z > _Z_PIE + 0.5:
                pn = _n3(c.x * 0.08 + so, c.y * 0.08, 1.0)
                p.material_index = 1 if pn > 0.15 else 0
                p.use_smooth = True
            else:
                p.material_index = 4 if c.z > _Z_PIE + 0.5 else 0
                p.use_smooth = False
            continue
        z_loc = c.z - c.x * tx - c.y * ty            # cota pre-cizalla
        if nz > 0.85:                                # cima plana: caliza clara
            idx = 3
        elif nz < -0.25:
            idx = 4
        else:
            ph = 0.25 * _n3(c.x * 0.05 + so, c.y * 0.05, 2.0)
            idx = _PATRON_PENA[math.floor(z_loc / band_h + ph) % len(_PATRON_PENA)]
        p.material_index = idx
        p.use_smooth = False
    ob["mont_alto"] = float(alto)
    ob["mont_radio"] = float(radio)
    return ob


def build_loma(parent_collection, alto=28.0, radio=70.0, seed=0, pena=True,
               largo=None, **kw):
    """Colina verde suave (todo bosque, sin cresta cimera de roca) con un
    peñasco en la cima: para dar altibajos alrededor del circuito.
    largo=None: domo redondo; largo=L: loma alargada (cresta de L m a lo
    largo de X local, 2-4 cumbres con collados). Empty MONT_loma."""
    root = bpy.data.objects.new("MONT_loma", None)
    root.empty_display_size = 5.0
    parent_collection.objects.link(root)
    comunes = dict(linea_arboles=2.0, rugosidad=0.6, pend_bosque=60.0,
                   pend_pared=80.0, estratos=False,
                   res=float(kw.get("res", 0.7)))
    if largo is None:
        pico = build_pico(parent_collection, alto=alto, radio=radio, seed=seed,
                          tipo="domo", **comunes)
    else:
        pico = build_pico(parent_collection, alto=alto, radio=radio, seed=seed,
                          tipo="cresta", largo_cresta=float(largo), **comunes)
    pico.parent = root
    if pena:
        cima = max(pico.data.vertices, key=lambda v: v.co.z).co
        pn = build_pena(parent_collection, alto=alto * 0.45, radio=radio * 0.22,
                        seed=seed + 3)
        pn.location = (cima.x, cima.y, cima.z - alto * 0.08)
        pn.parent = root
    root["mont_alto"] = float(alto)
    root["mont_radio"] = float(radio)
    return root


def build(parent_collection, seed=0, **params):
    """Cordillera de fondo completa. Devuelve el Empty MONT_cordillera."""
    return build_cordillera(parent_collection, seed=seed, **params)
