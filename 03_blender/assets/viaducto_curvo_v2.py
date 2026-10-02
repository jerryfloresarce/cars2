"""VIADUCTO_CURVO v2 — Viaducto ALTISIMO de arcos de piedra que sigue una curva
y BAJA de la montana (Porto Corsa, Cars 2).

El icono de Porto Corsa: la pista baja de la montana sobre un viaducto de
arcos romanos de caliza calida. Este modulo recibe el EJE del tablero como
lista de puntos 3D (la carretera va ENCIMA y ya existe: aqui NO se construye
calzada) y genera debajo la obra de fabrica siguiendo la curva y la pendiente.
Pensado para tableros de 6 a 100 m sobre el agua, con el RITMO MEDIDO EN EL
FOTOGRAMA de la pelicula (peli_bajada_viaducto_alto): UN SOLO orden de arcos
de medio punto altisimos y ESTRECHOS sobre pilas rectangulares esbeltas.

  - PILAS cada ~14.5 m, perpendiculares a la direccion local, que bajan hasta
    nivel_agua - 4. Con tablero alto miden ~4.8 m de ancho (luz libre ~9.7 m:
    pila = ~0.5 x hueco, hueco de proporcion 4:1 a 5.5:1); junto al mar
    (tablero < 12 m) recuperan la proporcion del viaducto original (pila de
    2.6 m, luz 11.4 m). Las pilas altas llevan TALUD (mas anchas en la base,
    a lo largo y a lo ancho), hiladas de canteria en dos tonos MUY proximos
    alineadas en cota en todo el viaducto, zocalo escalonado, imposta lisa en
    el arranque de los arcos y pilastra lisa hasta la cornisa del tablero.
    Tajamares de piedra (franja mojada oscura, remate claro) en TODAS las
    pilas bajas intermedias (fuste <= 30 m), con altura minima de 1.2 m aunque
    el arco arranque a ras de agua. Las dos pilas EXTREMAS son medias pilas
    (estribos) enrasadas con el testero del tablero: nada sobresale del final.
  - ARCOS de medio punto bajo el tablero (flecha = media luz; rebajados
    automaticamente solo si el tablero va casi a ras de agua), con boveda
    OSCURA y anillo de dovelas algo mas claras en ambas caras. En rampa cada
    arco se encaja lo mas alto posible bajo la cornisa inclinada. Sobre las
    claves queda una banda de timpano lisa de ~0.5 x luz (con el pretil).
  - UN nivel de ARRIOSTRAMIENTO discreto, solo donde el tablero pasa de
    ~55 m: arcos de medio punto entre pilas a una cota FIJA de mundo (por
    defecto automatica, ~0.47 x altura maxima de arranques => ~40 m con
    tablero a 93 m), REMETIDOS ~1.1 m respecto a la cara de las pilas para
    que estas se sigan leyendo continuas de arriba abajo. Por debajo de 55 m
    queda el orden unico puro de la pelicula. (kw `niveles` fuerza cotas.)
  - muro de timpano, cornisa corrida lisa bajo el tablero, losa PLANA a lo
    ancho (cara superior = z del eje - 0.06; la calzada va aparte encima) y
  - PRETIL macizo y BAJO de piedra a ambos lados, justo por fuera de la
    calzada (calzada = ancho - 1 m): albardilla mas clara a `alto_pretil`
    (0.82 m: el piloto ve el mar y el resto del viaducto por encima), un dado
    liso sobre cada pila (1.10 m) y pilastrillas claras cada ~3.6 m que le dan
    ritmo; sigue la pendiente con suavidad.

API (ver CONTRATO.md) — identica a viaducto_curvo.py:
  build_desde_puntos(parent_collection, puntos, ancho=13.0, nivel_agua=0.0,
                     seed=0, nombre="tramo", vano_objetivo=14.0, **kw)
      puntos = [(x, y, z), ...] eje del tablero en coordenadas de MUNDO
      (curvo y en rampa admitido). La geometria se genera en esas mismas
      coordenadas y cuelga de un Empty raiz "VIADUCTO_<nombre>" en el origen
      del mundo, sin rotacion (excepcion documentada a la regla "origen en el
      centro de la base": el asset se ancla al trazado que recibe).
      ancho = ancho de la calzada + 1 m. Escalar (como siempre) o, NUEVO y
      compatible, una SECUENCIA con un valor por punto de `puntos` (misma
      longitud): se interpola a lo largo del eje y lo siguen losa, cornisa,
      timpanos, pilas y pretil, de modo que el pretil nunca pisa una calzada
      de ancho variable. Integrador:  ancho=[S[j]['w'] + 1.0 for j in run[::2]]
      kw opcionales: alto_pretil=0.82 (cara superior de la albardilla sobre el
      eje; los dados suben 0.28 m mas), paso_pilastrillas=3.6 (0 = pretil
      liso), vano_alto=14.6 (separacion de pilas con tablero alto;
      vano_objetivo es la de tablero bajo), niveles=None (automatico: un
      nivel donde el tablero pasa de `alto_un_nivel`=55 m; o una tupla de
      cotas sobre nivel_agua, p. ej. (30.0, 58.0), para forzar varios),
      hilada=3.0, talud_long=60.0, talud_lat=22.0 (talud 1:n de las pilas),
      vanos_por_trozo=10.
      Hijos: VIADUCTO_<nombre>_cuerpo[_NN] y VIADUCTO_<nombre>_balaustrada[_NN]
      (el pretil conserva el nombre historico "balaustrada"; troceados cada
      `vanos_por_trozo` vanos para no pasar de 65k vertices por malla en
      Assetto Corsa; con un solo trozo no llevan sufijo).
      Si alguien necesitara los nombres historicos sin sufijo basta pasar
      vanos_por_trozo=10**6.
      El Empty raiz lleva las propiedades "pilas_s" (abscisas en planta de las
      pilas), "niveles_z" (cotas de arriostramiento usadas) y "ancho_min" /
      "ancho_max" (extremos del ancho aplicado).
  build(parent_collection, seed=0, **params)
      Muestra: curva en S de 240 m que baja de z=62 a z=26.

Presupuesto: viaducto de 1300 m con tablero de 93 a 6 m <= 150k tris.
Sin bpy.ops. Metros. Materiales Principled planos MAT_PUENTES_VIADUCTO_*
(el pase de texturas/materiales se engancha a 'MAT_PUENTES' / 'piedra').
"""

import bisect
import math

import bpy
import bmesh
from mathutils import Vector

PFX = "VIADUCTO"
MAT_PFX = "MAT_PUENTES_VIADUCTO"

# si True se recalculan las normales con bmesh (las caras ya se generan con
# el sentido correcto; el test compara ambos resultados)
_RECALC_NORMALES = False

# ---------------------------------------------------------------- materiales

# Caliza crema calida medida en el fotograma (al sol ~#CDBE9F, en sombra
# ~#9C8F7A, intrados oscuro). Valores lineales. El albedo va un 10-15 % MAS
# CALIDO que el tono medido para compensar el relleno azul del cielo (con el
# albedo literal la sombra salia verde-gris y el conjunto caqui).
_PALETA = {
    "piedra":     ((0.620, 0.480, 0.270), 0.93, 0.0),  # caliza crema calida
    "piedra_b":   ((0.575, 0.440, 0.245), 0.93, 0.0),  # hilada alterna (muy sutil)
    "sillar":     ((0.765, 0.625, 0.385), 0.90, 0.0),  # impostas / cornisa / albardilla
    "intrados":   ((0.335, 0.250, 0.140), 0.90, 0.0),  # boveda OSCURA bajo el arco
    "dovela_a":   ((0.745, 0.600, 0.360), 0.90, 0.0),  # dovelas algo mas claras
    "dovela_b":   ((0.675, 0.535, 0.310), 0.90, 0.0),
    "clave":      ((0.785, 0.645, 0.400), 0.88, 0.0),
    "zocalo":     ((0.340, 0.255, 0.145), 0.95, 0.0),  # piedra mojada
    "balaustre":  ((0.680, 0.550, 0.330), 0.92, 0.0),  # pretil macizo
}
_ORDEN_CUERPO = ("piedra", "sillar", "intrados", "dovela_a", "dovela_b",
                 "clave", "zocalo", "piedra_b")
M_PIEDRA, M_SILLAR, M_INTRA, M_DOV_A, M_DOV_B, M_CLAVE, M_ZOC, M_PIEDRA_B = range(8)


def _mat(clave):
    nombre = "%s_%s" % (MAT_PFX, clave)
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough, metal = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bsdf = None
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bsdf = n
            break
    if bsdf is None:
        bsdf = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        out = m.node_tree.nodes.get('Material Output')
        if out is not None:
            m.node_tree.links.new(bsdf.outputs[0], out.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    m.diffuse_color = (*color, 1.0)
    return m


# ------------------------------------------------------------------ utiles

def _clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def _suave(t):
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _lerp(a, b, t):
    return a + (b - a) * t


class _Buf:
    """Acumulador de una malla (vertices, caras, indice de material)."""

    def __init__(self):
        self.v, self.f, self.fm = [], [], []


# ------------------------------------------------------------------- espina

def _catmull(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return (p1 * 2.0 + (p2 - p0) * t
            + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2
            + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * t3) * 0.5


class _Espina:
    """Polilinea densa (Catmull-Rom) parametrizada por longitud EN PLANTA."""

    def __init__(self, puntos, subdiv=10):
        pts = [Vector((p[0], p[1], p[2])) for p in puntos]
        if len(pts) < 2:
            raise ValueError("viaducto_curvo: hacen falta >= 2 puntos")
        dense = []      # (punto, es_nodo)
        n = len(pts)
        for i in range(n - 1):
            p0 = pts[i - 1] if i > 0 else pts[0] * 2.0 - pts[1]
            p1, p2 = pts[i], pts[i + 1]
            p3 = pts[i + 2] if i + 2 < n else pts[-1] * 2.0 - pts[-2]
            for k in range(subdiv):
                dense.append((_catmull(p0, p1, p2, p3, k / subdiv), k == 0))
        dense.append((pts[-1].copy(), True))
        self.pts = [dense[0][0]]
        idx_nodos = [0]
        idx_puntos = [0]        # uno por punto de entrada (tambien los repetidos)
        for p, es_nodo in dense[1:]:
            nuevo = (p.xy - self.pts[-1].xy).length > 1e-5
            if nuevo:
                self.pts.append(p)
            if es_nodo:
                idx_puntos.append(len(self.pts) - 1)
                if nuevo:
                    idx_nodos.append(len(self.pts) - 1)
        if len(self.pts) < 2:
            raise ValueError("viaducto_curvo: eje degenerado (sin avance en planta)")
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + (b.xy - a.xy).length)
        self.L = self.cum[-1]
        self.s_nodos = [self.cum[i] for i in idx_nodos]
        self.s_puntos = [self.cum[i] for i in idx_puntos]   # len == len(puntos)

    def _loc(self, s):
        s = min(max(s, 0.0), self.L)
        i = bisect.bisect_right(self.cum, s) - 1
        i = min(max(i, 0), len(self.pts) - 2)
        d = self.cum[i + 1] - self.cum[i]
        t = 0.0 if d <= 1e-12 else (s - self.cum[i]) / d
        return i, t

    def pos(self, s):
        i, t = self._loc(s)
        return self.pts[i].lerp(self.pts[i + 1], t)

    def z(self, s):
        """Cota del eje; fuera de [0, L] se extrapola con la pendiente extrema."""
        if s < 0.0:
            return self.pts[0].z + self.pend(0.0) * s
        if s > self.L:
            return self.pts[-1].z + self.pend(self.L) * (s - self.L)
        i, t = self._loc(s)
        return _lerp(self.pts[i].z, self.pts[i + 1].z, t)

    def pend(self, s, d=1.5):
        a = max(0.0, s - d)
        b = min(self.L, s + d)
        if b - a < 1e-6:
            return 0.0
        return (self.pos(b).z - self.pos(a).z) / (b - a)

    def frame(self, s):
        """(posicion, tangente horizontal unitaria, normal lateral unitaria)."""
        i, t = self._loc(s)
        seg = (self.pts[i + 1] - self.pts[i]).xy
        j = i
        while seg.length < 1e-9 and j > 0:
            j -= 1
            seg = (self.pts[j + 1] - self.pts[j]).xy
        seg.normalize()
        tang = Vector((seg.x, seg.y, 0.0))
        nrm = Vector((-seg.y, seg.x, 0.0))
        p = self.pts[i].lerp(self.pts[i + 1], t)
        # prolongacion recta fuera de la espina (pilas extremas, anillos)
        if s < 0.0:
            p = p + tang * s
        elif s > self.L:
            p = p + tang * (s - self.L)
        return p, tang, nrm


class _Ancho:
    """Ancho del tablero a lo largo del eje: un escalar, o una secuencia con un
    valor por punto de `puntos` que se interpola por la abscisa en planta."""

    def __init__(self, esp, ancho, n_puntos):
        self.ss = None
        try:
            vals = [float(a) for a in ancho]
        except TypeError:
            vals = [float(ancho)]
        if len(vals) == 1:
            self.vals = vals
        elif len(vals) == n_puntos and len(esp.s_puntos) == n_puntos:
            self.vals = vals
            self.ss = list(esp.s_puntos)
        else:
            raise ValueError("viaducto_curvo: 'ancho' debe ser un numero o una "
                             "secuencia con un valor por punto (%d != %d)"
                             % (len(vals), n_puntos))
        self.minimo, self.maximo = min(self.vals), max(self.vals)

    def __call__(self, s):
        if self.ss is None:
            return self.vals[0]
        ss = self.ss
        i = min(max(bisect.bisect_right(ss, s) - 1, 0), len(ss) - 2)
        d = ss[i + 1] - ss[i]
        t = 0.0 if d <= 1e-9 else _clamp((s - ss[i]) / d, 0.0, 1.0)
        return _lerp(self.vals[i], self.vals[i + 1], t)


# ---------------------------------------------------------- geometria basica
# Todas las caras se generan ya con la normal hacia fuera.

def _tubo(buf, esp, cols, mi, fondos=None, techo=True, cap0=True, cap1=True):
    """Tubo que sigue la espina.
    cols = [(s, z_bajo, z_alto, a_bajo, a_alto, b_alto, b_bajo)] con a/b los
    desplazamientos laterales del costado derecho (a) e izquierdo (b), a < b.
    fondos[j]: indice de material del fondo del tramo j, o None para omitirlo.
    Dos columnas con la misma s generan la cara vertical del escalon."""
    v, f, fm = buf.v, buf.f, buf.fm
    base = len(v)
    for (s, zb, zt, a_b, a_t, b_t, b_b) in cols:
        p, _t, nrm = esp.frame(s)
        v.append((p.x + nrm.x * a_b, p.y + nrm.y * a_b, zb))
        v.append((p.x + nrm.x * a_t, p.y + nrm.y * a_t, zt))
        v.append((p.x + nrm.x * b_t, p.y + nrm.y * b_t, zt))
        v.append((p.x + nrm.x * b_b, p.y + nrm.y * b_b, zb))
    n = len(cols)
    for j in range(n - 1):
        a = base + 4 * j
        b = a + 4
        if abs(cols[j][0] - cols[j + 1][0]) < 1e-9:
            f.append((a, a + 3, b + 3, b)); fm.append(mi)
            continue
        f.append((a, b, b + 1, a + 1)); fm.append(mi)          # costado a
        f.append((a + 2, b + 2, b + 3, a + 3)); fm.append(mi)  # costado b
        if techo:
            f.append((a + 1, b + 1, b + 2, a + 2)); fm.append(mi)
        mif = mi if fondos is None else fondos[j]
        if mif is not None:
            f.append((a + 3, b + 3, b, a)); fm.append(mif)
    if cap0:
        f.append((base, base + 1, base + 2, base + 3)); fm.append(mi)
    if cap1:
        e = base + 4 * (n - 1)
        f.append((e + 3, e + 2, e + 1, e)); fm.append(mi)


def _cols_rect(esp, ss, dz0, dz1, off0, off1):
    """Columnas de un tubo rectangular colgado del eje. off0/off1 = costados
    (desplazamiento lateral): constantes o funciones de s (ancho variable)."""
    f0 = off0 if callable(off0) else (lambda s: off0)
    f1 = off1 if callable(off1) else (lambda s: off1)
    return [(s, esp.z(s) + dz0, esp.z(s) + dz1, f0(s), f0(s), f1(s), f1(s))
            for s in ss]


def _prisma(buf, c, tang, nrm, anillos, mis, tapa_inf=None, tapa_sup=None,
            cx=0.0, cy=0.0):
    """Pila de troncos de piramide en el marco local (tang, nrm) de una pila.
    anillos = [(hx, hy, z, pend[, dx])] de abajo arriba: semiancho a lo largo
    (hx) y lateral (hy); z + pend * x permite tapas inclinadas con el tablero;
    dx (opcional) desplaza ese anillo a lo largo (pilas extremas enrasadas).
    mis[k] = material de la banda k. tapa_*: material o None."""
    v, f, fm = buf.v, buf.f, buf.fm
    base = len(v)
    for an in anillos:
        hx, hy, z, pend = an[0], an[1], an[2], an[3]
        cxk = cx + (an[4] if len(an) > 4 else 0.0)
        ox = c.x + tang.x * cxk + nrm.x * cy
        oy = c.y + tang.y * cxk + nrm.y * cy
        for (ax, ay) in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)):
            v.append((ox + tang.x * ax + nrm.x * ay,
                      oy + tang.y * ax + nrm.y * ay,
                      z + pend * (ax + cxk)))
    n = len(anillos)
    for i in range(n - 1):
        lo = base + 4 * i
        up = lo + 4
        for k in range(4):
            k2 = (k + 1) % 4
            f.append((lo + k, lo + k2, up + k2, up + k)); fm.append(mis[i])
    if tapa_inf is not None:
        f.append((base + 3, base + 2, base + 1, base)); fm.append(tapa_inf)
    if tapa_sup is not None:
        t = base + 4 * (n - 1)
        f.append((t, t + 1, t + 2, t + 3)); fm.append(tapa_sup)


def _tajamar(buf, c, tang, nrm, lado, abajo, arriba, mi, mi_remate=None,
             alto_remate=None):
    """Espolon triangular en un costado de la pila, con remate piramidal si se
    da `mi_remate` (de altura `alto_remate`, por defecto 0.75 x ancho).
    abajo/arriba = (z, y_cara, ancho, saliente)."""
    v, f, fm = buf.v, buf.f, buf.fm
    (z0, y0, w0, d0), (z1, y1, w1, d1) = abajo, arriba

    def P(ax, ay, z):
        return (c.x + tang.x * ax + nrm.x * ay * lado,
                c.y + tang.y * ax + nrm.y * ay * lado, z)

    base = len(v)
    v += [P(-w0 / 2, y0, z0), P(w0 / 2, y0, z0), P(0.0, y0 + d0, z0),
          P(-w1 / 2, y1, z1), P(w1 / 2, y1, z1), P(0.0, y1 + d1, z1)]
    caras = [((0, 2, 5, 3), mi), ((2, 1, 4, 5), mi)]
    if mi_remate is not None:
        h_r = w1 * 0.75 if alto_remate is None else alto_remate
        v.append(P(0.0, y1 + d1 * 0.35, z1 + h_r))
        caras += [((3, 5, 6), mi_remate), ((5, 4, 6), mi_remate),
                  ((4, 3, 6), mi_remate)]
    for fc, m_ in caras:
        if lado > 0:
            fc = fc[::-1]
        f.append(tuple(base + i for i in fc)); fm.append(m_)


def _anillo(buf, esp, arco, off_fn, lado, n_seg, resalte=0.13):
    """Anillo de dovelas (tonos claros alternos, clave apenas marcada) en una
    cara. off_fn(s, z) = semiancho del paramento en ese punto (admite talud)."""
    v, f, fm = buf.v, buf.f, buf.fm
    s_c, R, zc, a0, a1 = arco["s_c"], arco["R"], arco["zc"], arco["a0"], arco["a1"]
    t_ring = arco["t_ring"]
    for k in range(n_seg):
        th0 = a0 + (a1 - a0) * (k / n_seg)
        th1 = a0 + (a1 - a0) * ((k + 1) / n_seg)
        clave = (n_seg % 2 == 1 and k == n_seg // 2)
        mi = M_CLAVE if clave else (M_DOV_A if k % 2 == 0 else M_DOV_B)
        r0 = R - 0.10
        r1 = R + t_ring + (0.14 if clave else 0.0)
        sal = resalte + (0.05 if clave else 0.0)
        base = len(v)
        for th in (th0, th1):
            cs, sn = math.cos(th), math.sin(th)
            for (r, dout) in ((r0, -0.06), (r1, -0.06), (r1, sal), (r0, sal)):
                s = s_c + r * cs
                z = zc + r * sn
                p, _t, nrm = esp.frame(s)
                off = lado * (off_fn(s, z) + dout)
                v.append((p.x + nrm.x * off, p.y + nrm.y * off, z))
        a, b = base, base + 4
        caras = [(a + 1, b + 1, b + 2, a + 2),   # trasdos
                 (a, a + 3, b + 3, b),           # intrados
                 (a + 2, b + 2, b + 3, a + 3)]   # frente
        if k == 0 or clave:
            caras.append((a, a + 1, a + 2, a + 3))
        if k == n_seg - 1 or clave:
            caras.append((b + 3, b + 2, b + 1, b))
        for fc in caras:
            if lado < 0:
                fc = fc[::-1]
            f.append(fc); fm.append(mi)


def _malla(nombre, buf, mats, parent_obj, coleccion):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(buf.v, [], buf.f)
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", buf.fm)
    if _RECALC_NORMALES:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    me.update()
    ob = bpy.data.objects.new(nombre, me)
    ob.parent = parent_obj
    coleccion.objects.link(ob)
    return ob


# ------------------------------------------------------------------- pilas

class _Pila:
    """Pila en su marco local recto (perpendicular a la direccion local)."""

    def __init__(self, esp, s, hp_top, hl_top, k_long, k_lat):
        self.s = s
        p, self.tang, self.nrm = esp.frame(s)
        self.c = Vector((p.x, p.y, 0.0))
        self.z_d = p.z                    # cota del eje del tablero
        self.pend = esp.pend(s)
        self.hp_top = hp_top              # semiancho a lo largo, en cabeza
        self.hl_top = hl_top              # semiancho lateral, en cabeza
        self.k_long, self.k_lat = k_long, k_lat
        self.z_sh = p.z                   # arranque del fuste (se fija luego)
        self.cotas_cornisa = []           # cotas Z de niveles adyacentes
        self.cotas_imposta = []           # arranques de arcos de nivel

    def hp(self, z):
        return self.hp_top + max(0.0, self.z_sh - z) / self.k_long

    def hl(self, z):
        return self.hl_top + max(0.0, self.z_sh - z) / self.k_lat


def _estaciones_pilas(esp, nivel_agua, vano_bajo, vano_alto):
    """Posiciones s de las pilas: separacion ~vano_bajo con tablero bajo y
    ~vano_alto con tablero alto, variando con suavidad y ajustada a L."""
    L = esp.L

    def vano_local(h):
        return _lerp(vano_bajo, vano_alto, _suave((h - 11.0) / 21.0))

    n_m = max(2, int(L) + 1)
    ss = [L * k / (n_m - 1) for k in range(n_m)]
    acum = [0.0]
    for a, b in zip(ss, ss[1:]):
        h = esp.z((a + b) / 2.0) - nivel_agua
        acum.append(acum[-1] + (b - a) / vano_local(h))
    total = acum[-1]
    n_vanos = max(1, int(round(total)))
    while n_vanos > 1 and L / n_vanos - 2.6 < 4.0:
        n_vanos -= 1
    sp = []
    for j in range(n_vanos + 1):
        obj = total * j / n_vanos
        i = min(max(bisect.bisect_right(acum, obj) - 1, 0), n_m - 2)
        d = acum[i + 1] - acum[i]
        t = 0.0 if d <= 1e-12 else (obj - acum[i]) / d
        sp.append(_lerp(ss[i], ss[i + 1], _clamp(t, 0.0, 1.0)))
    sp[0], sp[-1] = 0.0, L
    return sp


def _arco_superior(esp, s_l, s_r, nivel_agua):
    """Arco bajo el tablero entre las caras de pila s_l y s_r."""
    luz = s_r - s_l
    s_c = (s_l + s_r) / 2.0
    R = luz / 2.0
    t_ring = _clamp(0.45 + 0.065 * R, 0.80, 1.15)
    z_min = min(esp.z(s_l + luz * k / 8.0) for k in range(9))
    h = z_min - nivel_agua
    # holgura entre el trasdos del anillo y la cota del eje del tablero:
    # 0.73 reproduce el viaducto original (tablero bajo); con tablero alto
    # queda la banda lisa de timpano del fotograma (clave -> calzada ~3.5 m,
    # que con el pretil suma ~0.5 x luz).
    holg = _lerp(0.73, 2.70, _suave((h - 12.0) / 14.0))
    Rr = R + t_ring
    # medio punto lo mas alto posible bajo la rasante inclinada
    zc = min(esp.z(s_c + Rr * math.cos(math.pi * k / 24.0)) - holg
             - Rr * math.sin(math.pi * k / 24.0) for k in range(25))
    if zc >= nivel_agua + 0.35:
        a0, a1 = math.pi, 0.0
        z_arr = zc
    else:                                 # rebajado (tablero casi a ras de agua)
        z_clave = z_min - (holg + t_ring)
        flecha = max(z_clave - (nivel_agua + 0.35), luz * 0.15)
        z_arr = z_clave - flecha
        R = flecha / 2.0 + luz * luz / (8.0 * flecha)
        zc = z_arr + flecha - R
        half = math.asin(_clamp((luz / 2.0) / R, -1.0, 1.0))
        a0, a1 = math.pi / 2.0 + half, math.pi / 2.0 - half
    n_dov = int(round(luz * 1.2))
    if n_dov % 2 == 0:
        n_dov += 1
    n_dov = max(11, min(17, n_dov))
    return dict(s_l=s_l, s_r=s_r, s_c=s_c, R=R, zc=zc, a0=a0, a1=a1,
                z_arr=z_arr, t_ring=t_ring, n_seg=n_dov)


def _arco_nivel(pj, pk, Z, t_c):
    """Arco de arriostramiento de medio punto entre dos pilas con talud,
    con la cara superior del nivel a la cota Z."""
    z_s = Z - t_c - 8.0
    s_a = s_b = R = 0.0
    for _ in range(5):
        s_a = pj.s + pj.hp(z_s)
        s_b = pk.s - pk.hp(z_s)
        R = (s_b - s_a) / 2.0
        z_s = Z - t_c - R
    if R < 2.5:
        return None
    n_dov = int(round(2.0 * R * 0.85))
    if n_dov % 2 == 0:
        n_dov += 1
    n_dov = max(9, min(15, n_dov))
    return dict(s_l=s_a, s_r=s_b, s_c=(s_a + s_b) / 2.0, R=R, zc=z_s,
                a0=math.pi, a1=0.0, z_arr=z_s, Z=Z,
                t_ring=_clamp(0.35 + 0.065 * R, 0.62, 0.95), n_seg=n_dov)


def _puntos_arco(arco):
    """[(s, z)] del intrados, de s_l a s_r (ambos incluidos)."""
    n = arco["n_seg"]
    pts = []
    for k in range(n + 1):
        th = arco["a0"] + (arco["a1"] - arco["a0"]) * (k / n)
        pts.append((arco["s_c"] + arco["R"] * math.cos(th),
                    arco["zc"] + arco["R"] * math.sin(th)))
    pts[0] = (arco["s_l"], arco["z_arr"])
    pts[-1] = (arco["s_r"], arco["z_arr"])
    return pts


# --------------------------------------------------------------- constructor

def build_desde_puntos(parent_collection, puntos, ancho=13.0, nivel_agua=0.0,
                       seed=0, nombre="tramo", vano_objetivo=14.0,
                       vano_alto=14.6, niveles=None, alto_un_nivel=55.0,
                       hilada=3.0, talud_long=60.0, talud_lat=22.0,
                       vanos_por_trozo=10, alto_pretil=0.82,
                       paso_pilastrillas=3.6, **params):
    """Genera la obra de fabrica del viaducto bajo el eje `puntos`.
    `ancho`: escalar o secuencia con un valor por punto (ver docstring)."""
    del seed, params  # determinista; se aceptan por contrato
    puntos = list(puntos)
    esp = _Espina(puntos)
    L = esp.L
    anc = _Ancho(esp, ancho, len(puntos))
    coleccion = parent_collection
    raiz = bpy.data.objects.new("%s_%s" % (PFX, nombre), None)
    raiz.empty_display_size = 2.0
    coleccion.objects.link(raiz)
    raiz["ancho_min"] = float(anc.minimo)
    raiz["ancho_max"] = float(anc.maximo)

    def hw_muro(s):                   # muro de timpano
        return anc(s) / 2.0 - 0.45

    def hw_losa(s):                   # losa del tablero (estructura, no calzada)
        return anc(s) / 2.0 + 0.08    # cubre por debajo pretil y pilastrillas

    def hw_corn(s):                   # cornisa corrida lisa
        return anc(s) / 2.0 + 0.28

    def y_bal(s):
        # eje del pretil. La calzada mide ancho - 1: el rodapie queda a 4.5 cm
        # de su borde, holgura que absorbe la desviacion en planta (<= 4.6 cm
        # medidos en el trazado real) entre este eje suavizado y la malla de
        # la calzada, que pasa por TODAS las muestras.
        return anc(s) / 2.0 - 0.18

    alto_pretil = _clamp(float(alto_pretil), 0.50, 1.40)
    resalte = 0.25                    # pilastra sobre el paramento
    remetido = 0.85                   # arriostramiento remetido tras el paramento
    base_z = nivel_agua - 4.0
    vano_alto = max(vano_alto, vano_objetivo)

    # ------------------------------------------------ reparto de pilas
    sp = _estaciones_pilas(esp, nivel_agua, vano_objetivo, vano_alto)
    n_vanos = len(sp) - 1
    pilas = []
    for j, s in enumerate(sp):
        vs = []
        if j > 0:
            vs.append(sp[j] - sp[j - 1])
        if j < n_vanos:
            vs.append(sp[j + 1] - sp[j])
        v_med = sum(vs) / len(vs)
        # tablero bajo: pila del viaducto original (2.6 m); tablero alto:
        # pila del fotograma, ~0.5 x hueco (4.8 m con paso de 14.5 m)
        hp_bajo = _clamp(1.3 + (v_med - 14.0) * 0.06, 1.1, 1.9)
        hp_alto = max(hp_bajo, v_med * 0.166)
        h_d = esp.z(s) - nivel_agua
        hp_top = _lerp(hp_bajo, hp_alto, _suave((h_d - 10.0) / 16.0))
        hp_top = min(hp_top, min(vs) * 0.22)
        pilas.append(_Pila(esp, s, hp_top, hw_muro(s) + resalte,
                           talud_long, talud_lat))
    raiz["pilas_s"] = [float(s) for s in sp]

    # ------------------------------------------------ arcos superiores
    arcos = []
    for i in range(n_vanos):
        arcos.append(_arco_superior(esp, sp[i] + pilas[i].hp_top,
                                    sp[i + 1] - pilas[i + 1].hp_top, nivel_agua))
    for j, pl in enumerate(pilas):
        zs = []
        if j > 0:
            zs.append(arcos[j - 1]["z_arr"])
        if j < n_vanos:
            zs.append(arcos[j]["z_arr"])
        pl.z_sh = min(zs)
        pl.z_arr_max = max(zs)
        pl.lado_alto = 0
        if len(zs) == 2 and abs(zs[0] - zs[1]) > 1e-6:
            pl.lado_alto = -1 if zs[0] > zs[1] else 1

    def z_sh_en(s):
        j = min(max(bisect.bisect_right(sp, s) - 1, 0), n_vanos - 1)
        t = _clamp((s - sp[j]) / max(sp[j + 1] - sp[j], 1e-9), 0.0, 1.0)
        return _lerp(pilas[j].z_sh, pilas[j + 1].z_sh, t)

    def off_muro(s, z):
        """Semiancho del paramento (timpanos y niveles) con el talud lateral."""
        return hw_muro(s) + max(0.0, z_sh_en(s) - z) / talud_lat

    # ------------------------------------------------ niveles de arriostramiento
    T_C = 1.55                          # de la clave del arco a la cara superior
    auto = niveles is None
    if auto:
        # UN nivel a ~media altura de los arranques mas altos, solo si algun
        # punto del tablero pasa de `alto_un_nivel`
        h_sh = max(pl.z_sh for pl in pilas) - nivel_agua
        h_dk = max(pl.z_d for pl in pilas) - nivel_agua
        cotas = []
        if h_dk > alto_un_nivel:
            cotas = [nivel_agua + float(round(0.47 * h_sh))]
    else:
        cotas = sorted(nivel_agua + float(zr) for zr in niveles)
    raiz["niveles_z"] = [float(c) for c in cotas]
    arcos_nivel = [[] for _ in range(n_vanos)]
    for i in range(n_vanos):
        pj, pk = pilas[i], pilas[i + 1]
        z_inf = nivel_agua + 1.0
        if auto and min(pj.z_d, pk.z_d) - nivel_agua < alto_un_nivel:
            continue
        for Z in cotas:
            if min(pj.z_sh, pk.z_sh) - Z < 7.0:
                break
            an = _arco_nivel(pj, pk, Z, T_C)
            if an is None or an["z_arr"] < z_inf + 3.0:
                break
            arcos_nivel[i].append(an)
            for pl in (pj, pk):
                if all(abs(Z - c) > 0.01 for c in pl.cotas_cornisa):
                    pl.cotas_cornisa.append(Z)
                if all(abs(an["z_arr"] - c) > 0.35 for c in pl.cotas_imposta):
                    pl.cotas_imposta.append(an["z_arr"])
            z_inf = Z

    # ------------------------------------------------ estaciones del tablero
    ks = []
    for a, b in zip(esp.s_nodos, esp.s_nodos[1:]):
        m = max(1, int(math.ceil((b - a) / 2.7)))
        for q in range(m):
            ks.append(a + (b - a) * q / m)
    ks.append(L)

    def estaciones(s0, s1, margen=0.5, extra=()):
        """Estaciones del tablero en [s0, s1]; `extra` fuerza estaciones (las
        pilastrillas del pretil caen asi sobre un vertice exacto del muro)."""
        i0 = bisect.bisect_right(ks, s0 + margen)
        i1 = bisect.bisect_left(ks, s1 - margen)
        if not extra:
            return [s0] + ks[i0:i1] + [s1]
        mid = [s for s in ks[i0:i1] if all(abs(s - q) > 0.6 for q in extra)]
        return [s0] + sorted(mid + list(extra)) + [s1]

    n_trozos = max(1, int(math.ceil(n_vanos / float(max(1, vanos_por_trozo)))))
    cuerpos = [_Buf() for _ in range(n_trozos)]
    barandas = [_Buf() for _ in range(n_trozos)]

    def trozo(i_vano):
        return min(max(i_vano, 0), n_vanos - 1) // max(1, vanos_por_trozo)

    # =============================== vanos ================================
    for i in range(n_vanos):
        buf = cuerpos[trozo(i)]
        arco = arcos[i]
        s0, s1 = sp[i], sp[i + 1]
        primero, ultimo = (i == 0), (i == n_vanos - 1)

        # ---- timpano + boveda del arco superior (los testeros extremos los
        #      cierran la media pila-estribo, la cornisa y la losa)
        pts_t = ([(s0, arco["z_arr"])] + _puntos_arco(arco)
                 + [(s1, arco["z_arr"])])
        cols = []
        for (s, z) in pts_t:
            hm = hw_muro(s)
            cols.append((s, z, esp.z(s) - 0.92, -hm, -hm, hm, hm))
        fondos = [None] + [M_INTRA] * arco["n_seg"] + [None]
        _tubo(buf, esp, cols, M_PIEDRA, fondos=fondos, techo=False,
              cap0=False, cap1=False)
        for lado in (-1, 1):
            _anillo(buf, esp, arco, off_muro, lado, arco["n_seg"])

        # ---- nivel(es) de arriostramiento de este vano: muro REMETIDO tras el
        #      paramento para que las pilas se sigan leyendo continuas
        for an in arcos_nivel[i]:
            Z = an["Z"]
            pj, pk = pilas[i], pilas[i + 1]
            s_ia = pj.s + max(0.2, pj.hp(Z) - 0.5)
            s_ib = pk.s - max(0.2, pk.hp(Z) - 0.5)
            zt = Z - 0.28

            def off_niv(s, z):
                return off_muro(s, z) - remetido

            pts = [(s_ia, an["z_arr"])] + _puntos_arco(an) + [(s_ib, an["z_arr"])]
            cols = []
            for (s, z) in pts:
                ob, ot = off_niv(s, z), off_niv(s, zt)
                cols.append((s, z, zt, -ob, -ot, ot, ob))
            fondos = [None] + [M_INTRA] * an["n_seg"] + [None]
            _tubo(buf, esp, cols, M_PIEDRA, fondos=fondos, techo=False,
                  cap0=False, cap1=False)
            for lado in (-1, 1):
                _anillo(buf, esp, an, off_niv, lado, an["n_seg"], resalte=0.10)
            # albardilla lisa del nivel
            n_c = max(2, int(math.ceil((s_ib - s_ia) / 4.5)))
            cols = []
            for q in range(n_c + 1):
                s = _lerp(s_ia, s_ib, q / n_c)
                o = off_niv(s, Z - 0.2) + 0.16
                cols.append((s, Z - 0.32, Z, -o, -o, o, o))
            _tubo(buf, esp, cols, M_SILLAR, cap0=False, cap1=False)

        # ---- cornisa corrida lisa + losa del tablero (calzada aparte, ENCIMA)
        ss = estaciones(s0, s1)
        _tubo(buf, esp, _cols_rect(esp, ss, -1.34, -0.98,
                                   lambda s: -hw_corn(s), hw_corn),
              M_SILLAR, cap0=primero, cap1=ultimo)
        _tubo(buf, esp, _cols_rect(esp, ss, -1.02, -0.06,
                                   lambda s: -hw_losa(s), hw_losa),
              M_PIEDRA, fondos=[None] * (len(ss) - 1),
              cap0=primero, cap1=ultimo)

        # ---- pretil macizo BAJO con albardilla clara (objeto "_balaustrada")
        bb = barandas[trozo(i)]
        sa = max(s0, 0.25)
        sb = min(s1, L - 0.25)
        if sb - sa > 0.6:
            # pilastrillas claras que dan ritmo al muro entre dado y dado
            s_pil = []
            if paso_pilastrillas and paso_pilastrillas > 0.5:
                n_div = max(1, int(round((s1 - s0) / paso_pilastrillas)))
                s_pil = [s0 + (s1 - s0) * q / n_div for q in range(1, n_div)]
                s_pil = [s for s in s_pil if sa + 1.2 < s < sb - 1.2]
            ssb = estaciones(sa, sb, extra=s_pil)
            sin_fondo = [None] * (len(ssb) - 1)
            h_alb = alto_pretil               # cara superior de la albardilla
            for lado in (-1, 1):
                def yc(s, _l=lado):
                    return _l * y_bal(s)

                _tubo(bb, esp, _cols_rect(esp, ssb, -0.10, h_alb - 0.21,
                                          lambda s: yc(s) - 0.20,
                                          lambda s: yc(s) + 0.20),
                      0, fondos=sin_fondo, techo=False,
                      cap0=primero, cap1=ultimo)
                # albardilla clara
                _tubo(bb, esp, _cols_rect(esp, ssb, h_alb - 0.22, h_alb,
                                          lambda s: yc(s) - 0.27,
                                          lambda s: yc(s) + 0.27),
                      1, cap0=primero, cap1=ultimo)
                # rodapie de piedra mas oscura por la cara de la calzada
                _tubo(bb, esp, _cols_rect(esp, ssb, -0.08, 0.24,
                                          lambda s: yc(s) - lado * 0.23 - 0.045,
                                          lambda s: yc(s) - lado * 0.23 + 0.045),
                      2, fondos=sin_fondo, cap0=primero, cap1=ultimo)
                # pilastrillas: resaltan 4.5 cm por ambas caras (sin invadir la
                # calzada: quedan por detras de la cara del rodapie)
                for s_p in s_pil:
                    p, tg, nr = esp.frame(s_p)
                    pd = esp.pend(s_p)
                    _prisma(bb, Vector((p.x, p.y, 0.0)), tg, nr,
                            [(0.24, 0.245, p.z - 0.08, pd),
                             (0.24, 0.245, p.z + h_alb - 0.215, pd)], [1],
                            cy=yc(s_p))
                # dado liso sobre cada pila (el de la ultima lo pone el ultimo vano)
                for (s_ped, poner) in ((s0, True), (s1, ultimo)):
                    if not poner:
                        continue
                    s_ped = _clamp(s_ped, 0.95, L - 0.95)
                    p, tg, nr = esp.frame(s_ped)
                    c = Vector((p.x, p.y, 0.0))
                    pd = esp.pend(s_ped)
                    yd = yc(s_ped) + lado * 0.06     # nunca invade la calzada
                    _prisma(bb, c, tg, nr,
                            [(0.46, 0.29, p.z - 0.08, pd),
                             (0.46, 0.29, p.z + h_alb + 0.12, pd)], [0],
                            tapa_inf=0, cy=yd)   # vuela sobre el canto de la losa
                    _prisma(bb, c, tg, nr,
                            [(0.53, 0.34, p.z + h_alb + 0.12, pd),
                             (0.53, 0.34, p.z + h_alb + 0.28, pd)], [1],
                            tapa_inf=1, tapa_sup=1, cy=yd)

    # =============================== pilas ================================
    for j, pl in enumerate(pilas):
        buf = cuerpos[trozo(j if j < n_vanos else n_vanos - 1)]
        c, tg, nr = pl.c, pl.tang, pl.nrm
        H = pl.z_sh - base_z
        esc = 1.0 + 0.45 * _suave((H - 15.0) / 40.0)  # molduras mayores si alta

        # Las dos pilas EXTREMAS son medias pilas (estribos): su cara exterior
        # queda a ras del testero del tablero (1 cm por dentro; las molduras
        # vuelven 3 cm) y solo crecen hacia el interior del viaducto.
        ext = -1 if j == 0 else (1 if j == n_vanos else 0)

        def ani(hx, hy, z, pend=0.0, fuera=-0.01, _e=ext):
            if _e == 0:
                return (hx, hy, z, pend)
            return ((hx + fuera) / 2.0, hy, z, pend, -_e * (hx - fuera) / 2.0)

        # zocalo(s) mojado(s)
        z_zoc = nivel_agua + 0.85 * esc
        if pl.z_sh - 0.5 < z_zoc:
            z_zoc = max(nivel_agua + 0.3, pl.z_sh - 0.5)
        v1 = 0.40 * esc
        _prisma(buf, c, tg, nr,
                [ani(pl.hp(base_z) + v1, pl.hl(base_z) + v1, base_z, 0.0, 0.03),
                 ani(pl.hp(z_zoc) + v1, pl.hl(z_zoc) + v1, z_zoc, 0.0, 0.03)],
                [M_ZOC], tapa_sup=M_ZOC)
        z_fuste0 = z_zoc - 0.05
        if H > 30.0:
            z_zoc2 = z_zoc + 1.9
            v2 = 0.20 * esc
            _prisma(buf, c, tg, nr,
                    [ani(pl.hp(z_zoc) + v2, pl.hl(z_zoc) + v2, z_zoc - 0.05,
                         0.0, 0.02),
                     ani(pl.hp(z_zoc2) + v2, pl.hl(z_zoc2) + v2, z_zoc2,
                         0.0, 0.02)],
                    [M_SILLAR], tapa_sup=M_SILLAR)
            z_fuste0 = z_zoc2 - 0.05

        # fuste con talud e hiladas alternas alineadas en cota + pilastra
        anillos, mis = [], []
        if pl.z_sh - z_fuste0 > 0.3:
            cortes = [z_fuste0]
            k0 = int(math.floor((z_fuste0 - nivel_agua) / hilada)) + 1
            zc_ = nivel_agua + k0 * hilada
            while zc_ < pl.z_sh - 0.7:
                if zc_ > cortes[-1] + 0.7:
                    cortes.append(zc_)
                zc_ += hilada
            cortes.append(pl.z_sh)
            for a, b in zip(cortes, cortes[1:]):
                anillos.append(ani(pl.hp(a), pl.hl(a), a))
                par = int(math.floor(((a + b) / 2.0 - nivel_agua) / hilada)) % 2
                mis.append(M_PIEDRA if par == 0 else M_PIEDRA_B)
        anillos.append(ani(pl.hp_top, pl.hl_top, pl.z_sh))
        anillos.append(ani(pl.hp_top, pl.hl_top, pl.z_d - 1.30, pl.pend))
        mis.append(M_PIEDRA)
        # (la cabeza queda dentro de la cornisa; en las extremas se tapa ademas
        #  para que nunca se vea una caja hueca con backface culling)
        _prisma(buf, c, tg, nr, anillos, mis,
                tapa_sup=(M_PIEDRA if ext != 0 else None))

        # imposta lisa en el arranque de los arcos superiores
        vi = 0.22 * esc
        hi = 0.42 * esc
        _prisma(buf, c, tg, nr,
                [ani(pl.hp_top + vi, pl.hl_top + vi - 0.06, pl.z_sh - hi,
                     0.0, 0.03),
                 ani(pl.hp_top + vi, pl.hl_top + vi - 0.06, pl.z_sh - 0.02,
                     0.0, 0.03)],
                [M_SILLAR], tapa_inf=M_SILLAR, tapa_sup=M_SILLAR)
        if pl.lado_alto != 0 and pl.z_arr_max - pl.z_sh > 0.9:
            hx = (pl.hp_top + vi) / 2.0
            _prisma(buf, c, tg, nr,
                    [(hx, pl.hl_top + vi - 0.06, pl.z_arr_max - hi, 0.0),
                     (hx, pl.hl_top + vi - 0.06, pl.z_arr_max - 0.02, 0.0)],
                    [M_SILLAR], tapa_inf=M_SILLAR, tapa_sup=M_SILLAR,
                    cx=pl.lado_alto * hx)

        # (los niveles de arriostramiento van remetidos y NO abrazan la pila:
        #  el fuste se lee continuo de la base al tablero, como en la pelicula)

        # tajamares a ambos costados en TODAS las pilas bajas intermedias (las
        # que pueden pisar el agua): de piedra, con la franja mojada oscura y el
        # remate claro. Altura minima 1.2 m aunque el arco arranque a ras de
        # agua (el remate se funde entonces con la pilastra), para que no
        # aparezcan y desaparezcan de una pila a la siguiente.
        if H <= 30.0 and ext == 0:
            z_taj = max(nivel_agua + 1.2,
                        min(nivel_agua + _clamp(2.5 + (H - 15.0) * 0.05, 2.5, 5.5),
                            pl.z_sh - 0.55 * esc))
            w0 = 2.0 * pl.hp(base_z) * 0.85
            wz = 2.0 * pl.hp(z_zoc) * 0.85
            w1 = 2.0 * pl.hp(z_taj) * 0.85
            h_rem = min(w1 * 0.75, (pl.z_d - 1.50) - z_taj)
            if h_rem >= 0.35:
                for lado in (-1, 1):
                    _tajamar(buf, c, tg, nr, lado,
                             (base_z, pl.hl(base_z) + 0.02, w0, 0.48 * w0),
                             (z_zoc, pl.hl(z_zoc) + 0.02, wz, 0.48 * wz), M_ZOC)
                    _tajamar(buf, c, tg, nr, lado,
                             (z_zoc, pl.hl(z_zoc) + 0.02, wz, 0.48 * wz),
                             (z_taj, pl.hl(z_taj) + 0.02, w1, 0.48 * w1),
                             M_PIEDRA, mi_remate=M_SILLAR, alto_remate=h_rem)

    # =============================== mallas ===============================
    mats_c = [_mat(k) for k in _ORDEN_CUERPO]
    mats_b = [_mat("balaustre"), _mat("sillar"), _mat("piedra")]
    for t in range(n_trozos):
        suf = "" if n_trozos == 1 else "_%02d" % t
        if cuerpos[t].f:
            _malla("%s_%s_cuerpo%s" % (PFX, nombre, suf), cuerpos[t],
                   mats_c, raiz, coleccion)
        if barandas[t].f:
            _malla("%s_%s_balaustrada%s" % (PFX, nombre, suf), barandas[t],
                   mats_b, raiz, coleccion)
    return raiz


# ----------------------------------------------------------------- API kit

def _curva_s_demo(largo=240.0, z0=62.0, z1=26.0):
    """Curva en S de `largo` m que baja de z0 a z1 (muestra)."""
    pts = []
    n = int(largo / 4.0) + 1
    for i in range(n):
        t = i / (n - 1)
        x = -largo / 2.0 + largo * t
        y = 26.0 * math.sin(t * math.pi * 1.5)
        z = _lerp(z0, z1, _suave(t * 0.9 + 0.05))
        pts.append((x, y, z))
    return pts


def build(parent_collection, seed=0, **params):
    """Muestra: tramo en S de 240 m que baja de 62 a 26 m sobre agua a z=0."""
    return build_desde_puntos(parent_collection, _curva_s_demo(),
                              seed=seed, **params)
