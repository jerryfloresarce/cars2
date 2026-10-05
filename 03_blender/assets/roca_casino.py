"""roca_casino.py - PENON DEL CASINO de Porto Corsa (Cars 2) para Blender 5.1 (ronda 15c).

Roca NATURAL que se levanta del mar como la Roca de Monaco y se apoya en el espolon de
tierra por el lado de la entrada. Malla radial por columnas (perfil (r, z) de abajo arriba,
cremallera entre columnas anclada en las repisas, malla cerrada PENON_roca):
  * cara natural F(phi, z): meseta de borde irregular (contiene el circulo llano de 34 m y la
    huella del casino orientada hacia meta, como lo coloca integrar_escena) -> acantilado de
    talud variable 45-80 grados (concavidad y pie variables por columna = contrafuertes y
    vaguadas de baja frecuencia), bultos, costillas y bancos de estrato irregulares con
    cornisa; en las columnas de tierra la roca se EMPOTRA en el terreno (r_terreno(z) + 1.5 m,
    sin fosos ni huecos) y no sale del contorno mas de 2.5 m (la pista esta cerca); hacia el
    mar el pie se abre en talud.
  * CARRETERA de 5 m tallada como repisa (6.2 m) con parapeto (solo donde hay caida, medido
    con rayos) y farolas sobre la albardilla: ENTRADA (plataforma de 10 m en el contorno, a
    z_entrada) -> rama corta de SUBIDA a la meseta por el lado de tierra y BAJADA (<= 11 %)
    por la cara libre: pasadas alrededor de la roca y, donde el terreno corta el paso,
    HORQUILLAS (<= 2; 3 en modo 'roca') sobre un contrafuerte (plataforma de 21.2 m, lazo de radio 7.5 m e isla
    con pino) hasta una CALA al nivel del mar: muelle de 26 m con pantalan, 3 lanchas, 4-6
    casas con fachada al mar, palmeras y fuente. Si el arco libre se acaba antes del mar, la
    bajada sale de la roca por un ESPIGON (dique con calzada, variantes de giro, cara tallada
    en la salida) hasta el muelle en la ensenada libre.
  * apilado de ARRIBA abajo: ninguna roca ni repisa queda encima de otra repisa (0
    voladizos), ejes suaves (|dR| <= 0.25 m por m), lazos orientados (0 quads cruzados).
  * ronda 15 v1: el trazado elegido se AJUSTA antes de aceptarlo (cala con los radios
    definitivos, pendiente <= 11 % con los empalmes, sin quiebros ni calzada oblicua que no
    quepa en su repisa); tope radial de la calzada con pendiente limitada (R_cap_v) en la
    muesca de la rotonda; bajo las repisas, talud de roca hasta la ladera y bastiones de roca.
  * ronda 15 v2: si ninguna forma sale limpia con espigon, modo 'roca' (sin espigon, una
    horquilla mas: la bajada llega al mar por la cara y acaba en la CALA al pie de la roca, con
    casas, fuente, pantalan, lanchas, bolardos y palmeras); NUNCA una calzada muerta: sin cala,
    plataforma final con lazo para dar la vuelta (mirador). Segunda diferencia del eje limitada
    (quiebro <= 0.2 en los empalmes con las plataformas). RELLENO de roca bajo la repisa mas baja
    donde el terreno hace una V entre la roca y la pista (grieta junto a la rotonda Loews: banda
    de 5-22 m del borde a la cota de la pista - 1, cara en talud con relieve), orilla de rocas
    donde queda un canal de mar < 15 m entre el pie y la costa y, opcional, un foso cerrado.

API
  build(parent_collection, contorno, z_base, z_plaza, entrada, z_mar, seed=0,
        casas_kit=None, vegetacion_kit=None, italiano_kit=None, yates_kit=None,
        **params) -> (Empty 'PENON_cara', info)
    contorno: [(x, y), ...] ('pts' de zona_casino); z_base: terreno maximo del contorno + 0.3
    (solo informativo); z_plaza: cota de la MESETA (z_top_c del integrador); entrada: (x, y[, z])
    (sin z: params['z_entrada']); z_mar: nivel del mar.
    params: terreno_fn(x, y) -> z (bilineal de la rejilla; sin el, todo mar), columnas (256),
      pendiente_bajada (0.1095 nominal, reparto uniforme con los empalmes: max <= 0.11; si se
      pasa se reintenta con -0.004 y -0.008), pendiente_subida (0.085), horquillas_max (2),
      espigon_z_max (18), candidatos (10 formas ajustadas), meta_xy (-176.07, 112.18) y
      casino_huella (84.6, 48.6) para la huella llana del casino, radio_llano (34),
      altura_muelle (1.5), horquillas_extra (1, modo 'roca'), pista (muestras de la pista: dicts
      x, y, z, w; sin ella se lee la geometria del integrador: env GEOM o geometria_3d.json),
      relleno_fosos (True desde v3: foso cerrado de tierra > 8 m entre la roca y la ladera; la orilla de rocas en el
      agua va siempre), curvas (curvas de la geometria, para el eje del espolon del integrador; sin ellas se leen
      del mismo fichero que pista), log.
    info: entrada (x, y, z) [hueco del parapeto donde llega el espolon], z_top, centro_top,
      radio_meseta, meseta_poligono, casino_rect (4 esquinas llanas), muestras_carretera
      [(x, y, z)] (meseta -> entrada -> cala), cintas [subida, bajada], plazas_casas
      [{x, y, z, rot_z, ancho, fondo, plantas, tipo}], cala (x, y, z), cala_huella [(x, y)],
      camino_pie [] (la bajada acaba en el mar: la cala se conecta por la propia bajada, que sube a la
      entrada y al espolon de la pista; conexion_cala = 'bajada'), tipo_fin ('espigon' | 'cala_roca' |
      'mirador' (plataforma final con lazo) | 'cala_corta' | 'sin_cala' | 'sin_salida'), modo, fin_carretera,
      relleno_pista, relleno_fosos (columnas de agua + fosos), relleno_foso_tierra, espolon_eje [(x, y, z)] (eje
      del espolon de integrar_escena.zona_caminos, pista -> entrada: sin arboles a < 9.5 m ni matas a < 4.5 m),
      n_horquillas (incluida la plataforma final), vueltas_bajada,
      longitud_bajada, pendiente_max_bajada, longitud_subida, pendiente_max_subida,
      longitud_carretera, pendiente_max, casas_malas, farolas, n_farolas, n_veg, n_matas,
      quiebro_max, n_voladizos_apilado, sentido, llega_cala, avisos, tris_roca.
    Hijos: PENON_roca (malla cerrada), PENON_carretera, PENON_parapeto, PENON_farolas,
      PENON_balaustrada, PENON_plazas, PENON_casa_*, VEG_penon_*, ITAL_penon_*, YATE_*.
Convenciones: metros; sin bpy.ops; materiales MAT_PPUEBLO_* / MAT_PENON_*; casas de
casas_kit_v2.build_casa (pivote en el centro de la fachada, fachada +Y local:
rot_z = atan2(fy, fx) - pi/2). El trazado (clase _Penon hasta el apilado) no usa bpy: se
puede probar con el python del sistema.
"""
import importlib.util
import json
import math
import os
import random
import sys

try:
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils import noise as _mnoise

    def _ruido(x, y, z):
        return _mnoise.noise(Vector((x, y, z)))
except ImportError:  # python del sistema: solo trazado y perfiles
    bpy = None
    Vector = BVHTree = None

    def _ruido(x, y, z):
        return (math.sin(x * 1.7 + y * 0.9 + z * 0.3) * math.cos(z * 1.3 + x * 0.4 - y * 0.7)) * 0.6

TAU = 2.0 * math.pi
_ultimo = None

# ----------------------------------------------------------------- materiales
# FASE VISUAL F1 (bloque 3.1 / 2.1): la caliza sale de 03_blender/paleta.json con los MISMOS valores que
# roca_lazo (antes MAT_PPUEBLO_roca tenia dos valores segun que kit se construyera primero) y los 4 materiales
# de roca llevan el grupo compartido NG_caliza_estratos (assets/materiales_roca.aplicar_a).
# Paleta v2 (usuario 04/10): caliza_ocre = caliza CLARA #D8CCB0, caliza_gris_calido = MEDIA #B3A68A (repisa),
# caliza_sombra = roca OSCURA #7F766A; sin gris azulado (las claves no cambian, cambian los valores en paleta.json).
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import paleta as _paleta  # noqa: E402

_PALETA = {
    'MAT_PPUEBLO_roca':        (_paleta.rgb('caliza_ocre'), 0.95, 0.0),
    'MAT_PPUEBLO_roca_clara':  (_paleta.variante('caliza_ocre', 1.15), 0.95, 0.0),
    'MAT_PPUEBLO_roca_oscura': (_paleta.rgb('caliza_sombra'), 0.96, 0.0),
    'MAT_PPUEBLO_repisa':      (_paleta.rgb('caliza_gris_calido'), 0.95, 0.0),
    'MAT_PPUEBLO_carretera':   ((0.19, 0.19, 0.20), 0.90, 0.0),
    'MAT_PPUEBLO_borde':       ((0.86, 0.83, 0.74), 0.70, 0.0),
    'MAT_PPUEBLO_muro':        ((0.75, 0.67, 0.51), 0.85, 0.0),
    'MAT_PPUEBLO_plaza':       ((0.64, 0.58, 0.45), 0.80, 0.0),
    'MAT_PPUEBLO_plaza_dibujo': ((0.54, 0.48, 0.37), 0.80, 0.0),
    'MAT_PENON_balaustrada':   ((0.90, 0.87, 0.80), 0.60, 0.0),
    'MAT_PENON_poste':         ((0.12, 0.12, 0.13), 0.50, 0.3),
    'MAT_PENON_farol':         ((1.00, 0.86, 0.55), 0.30, 0.0),
    'MAT_PENON_muelle':        ((0.60, 0.56, 0.47), 0.85, 0.0),
    'MAT_PENON_bolardo':       ((0.20, 0.20, 0.22), 0.60, 0.2),
}
_CLAVE = {
    'roca': 'MAT_PPUEBLO_roca', 'roca_clara': 'MAT_PPUEBLO_roca_clara',
    'roca_oscura': 'MAT_PPUEBLO_roca_oscura', 'repisa': 'MAT_PPUEBLO_repisa',
    'carretera': 'MAT_PPUEBLO_carretera', 'borde': 'MAT_PPUEBLO_borde',
    'muro': 'MAT_PPUEBLO_muro', 'plaza': 'MAT_PPUEBLO_plaza', 'plaza_dibujo': 'MAT_PPUEBLO_plaza_dibujo',
    'balaustrada': 'MAT_PENON_balaustrada', 'poste': 'MAT_PENON_poste', 'farol': 'MAT_PENON_farol',
    'muelle': 'MAT_PENON_muelle', 'bolardo': 'MAT_PENON_bolardo',
}
_ROCAS = ('roca', 'roca_clara', 'roca_oscura')
_CLAVES_CALIZA = ('roca', 'roca_clara', 'roca_oscura', 'repisa')


def _materiales_roca():
    """assets/materiales_roca (grupo de caliza compartido) o None si no se puede importar."""
    if 'materiales_roca' in sys.modules:
        return sys.modules['materiales_roca']
    try:
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'materiales_roca.py')
        spec = importlib.util.spec_from_file_location('materiales_roca', ruta)
        mod = importlib.util.module_from_spec(spec)
        sys.modules['materiales_roca'] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:  # noqa
        print('roca_casino: AVISO materiales_roca no disponible (%s): roca de color plano' % e)
        return None


def _mat(clave):
    nombre = _CLAVE[clave]
    m = bpy.data.materials.get(nombre)
    if m is not None:
        if clave in _CLAVES_CALIZA:
            mr = _materiales_roca()
            if mr is not None and not mr.tiene_caliza(m):
                mr.aplicar_a(m, tono_base=_PALETA[nombre][0])
        return m
    color, rough, metal = _PALETA[nombre]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    if bs is not None:
        bs.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
        bs.inputs['Roughness'].default_value = rough
        bs.inputs['Metallic'].default_value = metal
        if clave == 'farol':
            try:
                bs.inputs['Emission Color'].default_value = (1.0, 0.80, 0.45, 1.0)
                bs.inputs['Emission Strength'].default_value = 1.0
            except KeyError:
                pass
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    if clave in _CLAVES_CALIZA:
        mr = _materiales_roca()
        if mr is not None:
            # caliza compartida con estratos en coordenadas de mundo (misma que roca_lazo y el terreno)
            mr.aplicar_a(m, tono_base=color, contraste_bancos=0.0 if clave == 'roca_oscura' else 0.12)
    return m


class _Malla:
    """Acumulador de vertices/caras con clave de material por cara."""

    def __init__(self, nombre, claves):
        self.nombre = nombre
        self.v = []
        self.f = []
        self.mi = []
        self.claves = list(claves)

    def vert(self, p):
        self.v.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.v) - 1

    def cara(self, idx, clave):
        idx = [i for k, i in enumerate(idx) if i != idx[k - 1]]
        if len(idx) < 3:
            return
        self.f.append(tuple(idx))
        if clave not in self.claves:
            self.claves.append(clave)
        self.mi.append(self.claves.index(clave))

    def quad(self, p0, p1, p2, p3, clave):
        self.cara((self.vert(p0), self.vert(p1), self.vert(p2), self.vert(p3)), clave)

    def quad_hacia(self, p0, p1, p2, p3, hacia, clave):
        """Quad orientado para que su normal apunte hacia `hacia`."""
        ax, ay, az = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        bx, by, bz = p3[0] - p0[0], p3[1] - p0[1], p3[2] - p0[2]
        nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
        if nx * hacia[0] + ny * hacia[1] + nz * hacia[2] < 0:
            p1, p3 = p3, p1
        self.quad(p0, p1, p2, p3, clave)

    def caja(self, c, dx, dy, dz, clave, rot=0.0):
        """Caja centrada en (c.x, c.y), base en c.z, girada rot (rad) sobre Z."""
        ca, sa = math.cos(rot), math.sin(rot)
        hx, hy = dx / 2.0, dy / 2.0
        esq = []
        for (u, v) in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)):
            esq.append((c[0] + u * ca - v * sa, c[1] + u * sa + v * ca))
        b = [self.vert((e[0], e[1], c[2])) for e in esq]
        t = [self.vert((e[0], e[1], c[2] + dz)) for e in esq]
        self.cara((b[3], b[2], b[1], b[0]), clave)
        self.cara((t[0], t[1], t[2], t[3]), clave)
        for k in range(4):
            self.cara((b[k], b[(k + 1) % 4], t[(k + 1) % 4], t[k]), clave)

    def objeto(self, parent_collection, parent_obj=None):
        me = bpy.data.meshes.new(self.nombre)
        me.from_pydata(self.v, [], self.f)
        for clave in self.claves:
            me.materials.append(_mat(clave))
        for p, mi in zip(me.polygons, self.mi):
            p.material_index = mi
        me.validate(verbose=False)
        me.update()
        ob = bpy.data.objects.new(self.nombre, me)
        parent_collection.objects.link(ob)
        if parent_obj is not None:
            ob.parent = parent_obj
        return ob

    def tris(self):
        return sum(len(f) - 2 for f in self.f)


def _suavizar_ciclico(vals, k):
    n = len(vals)
    out = []
    for i in range(n):
        s = w = 0.0
        for j in range(-k, k + 1):
            pw = 1.0 - abs(j) / float(k + 1)
            s += vals[(i + j) % n] * pw
            w += pw
        out.append(s / w)
    return out


def _smooth01(f):
    f = max(0.0, min(1.0, f))
    return f * f * (3.0 - 2.0 * f)


def _dang(a, b):
    """Diferencia angular a - b en (-pi, pi]."""
    return (a - b + math.pi) % TAU - math.pi


# ----------------------------------------------------------------- geometria base
class _Penon:
    """Roca radial: la columna i (angulo phi_i desde el centro del contorno) tiene un perfil
    (r, z) de abajo arriba; cada paso de carretera es un 'cruce' (repisa) en una columna.
    Los cruces se crean en orden de paso, que en cada columna es tambien de ARRIBA abajo:
    cada repisa nueva queda fuera de las que tiene encima (sin voladizos)."""

    W_CARRIL = 6.2      # repisa de un carril de 5 m (arcen de 0.6 m a cada lado)
    W_ENTRADA = 10.0
    RHO = 6.5           # radio del eje en el lazo de las horquillas (bordes a 4 y 9 m)
    W_PLAT = 3.1 + 2 * 6.5 + 3.1
    W_CALA = 26.0
    PEND_EJE = 0.45     # |dR/ds| maximo del eje (polar; una elipse 118x78 llega a ~0.4)
    PEND_TOPE = 0.5     # |dR/ds| maximo del tope radial de la carretera (R_cap_v)
    D_SALIDA = 16.0     # metros de espigon en los que la cara natural se talla para dejar salir el dique

    def __init__(self, contorno, z_base, z_top, entrada, z_mar, seed, params):
        self.seed = int(seed)
        self.rnd = random.Random(seed)
        self.params = params
        self.M = int(params.get('columnas', 256))
        self.dphi = TAU / self.M
        self.z_base = float(z_base)
        self.z_top = float(z_top)
        self.z_mar = float(z_mar)
        self.terreno_fn = params.get('terreno_fn')
        self.g_baj = float(params.get('pendiente_bajada', 0.1095))
        self.g_sub = float(params.get('pendiente_subida', 0.085))
        self.n_horq_max = int(params.get('horquillas_max', 2))
        self.n_horq_base = self.n_horq_max
        self.con_espigon = True
        self.modo = 'espigon'
        self.z_cala = self.z_mar + float(params.get('altura_muelle', 1.5))
        self.avisos = []
        pts = [(float(p[0]), float(p[1])) for p in contorno]
        self.cx = sum(p[0] for p in pts) / len(pts)
        self.cy = sum(p[1] for p in pts) / len(pts)
        self.geom_pista, self.geom_curvas = _leer_geom(params)
        self.pista = _muestras_pista(self.geom_pista, self.cx, self.cy)
        self.espolon_eje = None
        self.entrada_xy = None
        self.n_foso_tierra = 0
        self.n_veg_espolon = 0
        self.relleno = {}
        self.n_relleno = (0, 0)
        self.phi = [i * self.dphi for i in range(self.M)]
        self.Rc = self._radio_contorno(pts)
        self._terreno_columnas()
        self._meseta()
        self._estratos()
        ex, ey = float(entrada[0]), float(entrada[1])
        z_e = entrada[2] if len(entrada) > 2 else params.get('z_entrada')
        self.z_ent = float(z_e if z_e is not None else z_base)
        self.i_pedida = int(round((math.atan2(ey - self.cy, ex - self.cx) % TAU) / self.dphi)) % self.M
        self._forma(1.30, 0.0)
        self._reset_trazado()

    # ------------------------------------------------------------------ utilidades
    def xy(self, i, r):
        p = self.phi[i % self.M]
        return (self.cx + r * math.cos(p), self.cy + r * math.sin(p))

    def xy_ang(self, phi, r):
        return (self.cx + r * math.cos(phi), self.cy + r * math.sin(phi))

    def dcol(self, i, j):
        """Distancia (en columnas, con signo) de j a i por el camino corto."""
        return ((i - j + self.M // 2) % self.M) - self.M // 2

    def _radio_contorno(self, pts):
        """Contorno -> radio polar por columna; las muescas (junto a la pista) se ensanchan
        hacia dentro y se redondean; nunca sale del contorno mas de 0.2 m."""
        ar = sorted(((math.atan2(y - self.cy, x - self.cx) % TAU, math.hypot(x - self.cx, y - self.cy)) for (x, y) in pts))
        ar = [(ar[-1][0] - TAU, ar[-1][1])] + ar + [(ar[0][0] + TAU, ar[0][1])]
        base = []
        k = 0
        for i in range(self.M):
            phi = self.phi[i]
            while ar[k + 1][0] < phi:
                k += 1
            a0, r0 = ar[k]
            a1, r1 = ar[k + 1]
            f = (phi - a0) / (a1 - a0) if a1 > a0 else 0.0
            base.append(r0 + (r1 - r0) * f)
        ero = [min(base[(i + j) % self.M] for j in range(-3, 4)) for i in range(self.M)]
        sua = _suavizar_ciclico(ero, 2)
        return [min(sua[i], base[i] + 0.2) for i in range(self.M)]

    def _terreno_columnas(self):
        """Terreno muestreado cada metro a lo largo de cada columna; columnas de tierra (el
        contorno pisa tierra) y tope radial (junto a tierra la roca no sale > 2.5 m)."""
        M = self.M
        self.t_r, self.z_rim, self.tierra = [], [], []
        z_min = self.z_mar
        for i in range(M):
            n = int(self.Rc[i] * 1.9) + 6
            if self.terreno_fn is None:
                zs = [self.z_mar - 4.0] * (n + 1)
            else:
                zs = [float(self.terreno_fn(*self.xy(i, float(r)))) for r in range(n + 1)]
            self.t_r.append(zs)
            z_min = min(z_min, min(zs[:int(self.Rc[i] * 1.3)]))
        for i in range(M):
            zr = self.t(i, self.Rc[i])
            self.z_rim.append(zr)
            self.tierra.append(zr > self.z_mar + 1.5)
        self.z_fondo = min(self.z_mar - 12.0, z_min - 6.0)
        # muescas del contorno (_contorno_libre lo empuja hacia dentro donde pasa la pista):
        # radio de la envolvente convexa - radio del contorno
        xy = [self.xy(i, self.Rc[i]) for i in range(M)]
        hull = []
        for i in range(M):
            p = self.phi[i]
            ux, uy = math.cos(p), math.sin(p)
            h = self.Rc[i]
            for j in range(1, 40):
                for (a_, b_) in (((i - j) % M, (i + j) % M),):
                    for k in range(1, 40):
                        b2 = (i + k) % M
                        ax, ay = xy[a_][0] - self.cx, xy[a_][1] - self.cy
                        bx, by = xy[b2][0] - self.cx, xy[b2][1] - self.cy
                        den = ux * (by - ay) - uy * (bx - ax)
                        if abs(den) < 1e-9:
                            continue
                        t_ = (ax * (by - ay) - ay * (bx - ax)) / den
                        if t_ > h:
                            h = t_
            hull.append(h)
        self.muesca = [hull[i] - self.Rc[i] for i in range(M)]
        d_p = []
        for i in range(M):
            d_p.append(min((abs(j) for j in range(-M // 2, M // 2) if self.muesca[(i + j) % M] > 1.0), default=M))
        self.d_muesca = d_p
        d_t = []
        for i in range(M):
            d_t.append(min((abs(j) for j in range(-M // 2, M // 2) if self.tierra[(i + j) % M]), default=M))
        # tope radial: junto a la pista (muesca) la roca no sale > 2.5 m del contorno; en tierra
        # sin pista hasta 18 m (pie empotrado en la ladera); hacia el mar 1.65 Rc
        self.R_cap = []
        for i in range(M):
            w_p = _smooth01((d_p[i] - 3.0) / 8.0)
            w_t = _smooth01((d_t[i] - 2.0) / 8.0)
            c_t = self.Rc[i] + 2.5 + w_p * 15.5
            self.R_cap.append(c_t + w_t * max(0.0, 1.65 * self.Rc[i] - c_t))
        # tope de la CARRETERA: el mismo con la pendiente radial limitada (|dR/ds| <= PEND_TOPE). En la
        # muesca de la rotonda Loews el contorno hace una Z (6 m de radio por columna) y la calzada,
        # pegada al tope, iba casi radial: el paredon tapaba el borde interior y las farolas caian en el
        # asfalto. La roca (F_libre, empotrado, malla) sigue usando R_cap.
        self.R_cap_v = self._limitar_pendiente(self.R_cap, self.PEND_TOPE)
        self._cache_rt = {}

    def _limitar_pendiente(self, vals, g, ventana=48):
        """Envolvente inferior con pendiente radial limitada: out[i] = min_j(vals[j] + g * arco(i, j))
        (solo baja los valores; los valles se abren en rampa a g m por m de arco)."""
        M = self.M
        out = []
        for i in range(M):
            best = vals[i]
            for j in range(1, ventana + 1):
                for jj in ((i - j) % M, (i + j) % M):
                    v = vals[jj] + g * j * self.dphi * vals[jj]
                    if v < best:
                        best = v
            out.append(best)
        return out

    def t(self, i, r):
        """Terreno en la columna i a la distancia r del centro."""
        zs = self.t_r[i % self.M]
        if r <= 0.0:
            return zs[0]
        k = int(r)
        if k >= len(zs) - 1:
            return zs[-1]
        f = r - k
        return zs[k] * (1.0 - f) + zs[k + 1] * f

    def r_terreno(self, i, z):
        """Primer radio (desde dentro) en el que el terreno alcanza la cota z (None si no
        lo hace antes de Rc + 25 m)."""
        i %= self.M
        key = (i, int(round(z * 4.0)))
        if key in self._cache_rt:
            return self._cache_rt[key]
        zs = self.t_r[i]
        r0 = int(0.35 * self.Rc[i])
        r1 = min(len(zs) - 1, int(self.Rc[i] + 25.0))
        res = None
        if zs[r0] >= z:
            res = float(r0)
        else:
            for r in range(r0 + 1, r1 + 1):
                if zs[r] >= z:
                    a, b = zs[r - 1], zs[r]
                    res = (r - 1) + ((z - a) / (b - a) if b > a else 1.0)
                    break
        self._cache_rt[key] = res
        return res

    def libre(self, i, z, r0, r1, tol, zanja=None):
        """True si el terreno queda por debajo de z + tol entre los radios r0 y r1 y, con
        zanja = (dz, d), si el terreno no alcanza z + dz a menos de d m por fuera de r1 (la
        repisa no queda metida en una zanja detras del espolon)."""
        r = r0
        while r <= r1 + 1e-6:
            if self.t(i, r) > z + tol:
                return False
            r += 1.0
        if zanja is not None:
            rt = self.r_terreno(i, z + zanja[0])
            if rt is not None and rt < r1 + zanja[1]:
                return False
        return True

    # ------------------------------------------------------------------ meseta y forma
    def _meseta(self):
        """Radio del borde de la meseta por columna: contiene el circulo llano (radio_llano)
        y la huella del casino girada como en integrar_escena (hacia_meta - pi/2), borde
        irregular de baja frecuencia; mas ancha por el lado de tierra (la cara es baja)."""
        M, P = self.M, self.params
        mx, my = P.get('meta_xy', (-176.07, 112.18))
        self.hacia_meta = math.atan2(my - self.cy, mx - self.cx)
        self.theta_casino = self.hacia_meta - math.pi / 2.0
        hu = P.get('casino_huella', (84.6, 48.6))
        hx, hy = hu[0] / 2.0 + 3.0, hu[1] / 2.0 + 3.0
        r_ll = float(P.get('radio_llano', 34.0)) + 2.0
        rb = random.Random(self.seed * 13 + 7)
        a1, a2, a3 = rb.uniform(0, TAU), rb.uniform(0, TAU), rb.uniform(0, TAU)
        self.R_req, self.n_top = [], []
        for i in range(M):
            d = self.phi[i] - self.theta_casino
            c, s_ = abs(math.cos(d)), abs(math.sin(d))
            r_rect = min(hx / c if c > 1e-6 else 1e9, hy / s_ if s_ > 1e-6 else 1e9)
            self.R_req.append(max(r_rect, r_ll) + 2.0)
            self.n_top.append(0.5 * math.sin(3.0 * self.phi[i] + a1) + 0.3 * math.sin(5.0 * self.phi[i] + a2)
                              + 0.2 * math.sin(8.0 * self.phi[i] + a3))
        malos = sum(1 for i in range(M) if self.R_req[i] > self.Rc[i] - 7.0)
        if malos:
            self.avisos.append('meseta: la huella del casino casi toca el contorno en %d columnas' % malos)
        self.centro_top = (self.cx, self.cy)
        hx0, hy0 = hu[0] / 2.0, hu[1] / 2.0
        ca, sa = math.cos(self.theta_casino), math.sin(self.theta_casino)
        self.casino_rect = [(self.cx + u * ca - v * sa, self.cy + u * sa + v * ca)
                            for (u, v) in ((-hx0, -hy0), (hx0, -hy0), (hx0, hy0), (-hx0, hy0))]

    def _forma(self, f_bot, a_med, k_top=0.66, apoyo=0.0):
        """Borde de la meseta (k_top * Rc, irregular; mas ancha donde la cara es baja), pie (radio
        a nivel del mar, f_bot * Rc con contrafuertes y vaguadas de baja frecuencia) y forma del
        talud por columna: a < 0 hombro que se abre arriba y acantilado casi vertical al mar,
        a > 0 cara vertical arriba y talud abajo."""
        M = self.M
        R = []
        for i in range(M):
            rd = k_top * self.Rc[i] + 5.0 * self.n_top[i]
            if self.tierra[i] and self.z_rim[i] > self.z_top - 30.0:     # cara baja (espolon)
                rd = max(rd, self.Rc[i] - 17.0)
            elif self.tierra[i] and self.z_rim[i] > self.z_ent - 40.0 and self.d_muesca[i] < 10:
                rd = max(rd, self.Rc[i] - 11.0)                              # junto a la pista: meseta ancha
            # deja sitio a la carretera entre la meseta y el tope suavizado (repisa de 6.2 m + talla)
            R.append(min(max(self.R_req[i], rd), self.Rc[i] - 9.0, self.R_cap_v[i] - 9.5))
        R = _suavizar_ciclico(R, 3)
        self.R_top = [max(self.R_req[i], R[i]) for i in range(M)]
        rb = random.Random(self.seed * 17 + 5)
        b1, b2, b3, b4 = [rb.uniform(0, TAU) for _ in range(4)]
        self.f_bot, self.a_med, self.k_top = f_bot, a_med, k_top
        self.a, self.R_bot, self.mod = [], [], []
        # lejos de tierra la roca se abre en el mar (pie ancho, hombro); junto al espolon el pie
        # queda en el contorno y la cara es vertical arriba (ahi caben las horquillas)
        d_t = []
        for i in range(self.M):
            d_t.append(min((abs(j) for j in range(-self.M // 2, self.M // 2) if self.tierra[(i + j) % self.M]), default=self.M))
        self.w_mar = [1.0 - apoyo * (1.0 - _smooth01((d - 3.0) / 16.0)) for d in d_t]
        for i in range(self.M):
            p = self.phi[i]
            w = self.w_mar[i]
            mod = 0.55 * math.sin(3.0 * p + b1) + 0.45 * math.sin(2.0 * p + b2)
            self.mod.append(mod)
            a_i = a_med * w + 0.45 * (1.0 - w) + 0.25 * math.sin(4.0 * p + b3) + 0.10 * math.sin(7.0 * p + b4)
            self.a.append(max(-0.8, min(0.9, a_i)))
            f_i = 1.05 + (f_bot - 1.05) * w
            self.R_bot.append(max(self.Rc[i] * f_i * (1.0 + 0.13 * mod), self.R_top[i] + 30.0))
        self.R_bot = _suavizar_ciclico(self.R_bot, 2)
        self._cache_F = {}

    def _estratos(self):
        rb = random.Random(self.seed * 23 + 11)
        self.bordes = [self.z_fondo - 30.0]
        while self.bordes[-1] < self.z_top + 30.0:
            self.bordes.append(self.bordes[-1] + rb.uniform(7.0, 15.0))
        self.amp_estr = [0.35 + 0.65 * rb.random() for _ in self.bordes]
        self.fase = [3.0 * math.sin(self.phi[i] + 0.7 * self.seed) + 1.5 * math.sin(3.0 * self.phi[i] + 2.0)
                     for i in range(self.M)]

    def estrato(self, i, z):
        """(banco, desplazamiento radial del estrato) en la columna i a la cota z: cornisa
        (labio) arriba de cada banco y entrante abajo."""
        u = z - self.fase[i % self.M]
        k = 0
        while k + 1 < len(self.bordes) - 1 and self.bordes[k + 1] <= u:
            k += 1
        f = max(0.0, min(1.0, (u - self.bordes[k]) / (self.bordes[k + 1] - self.bordes[k])))
        a = self.amp_estr[k]
        if f < 0.12:
            d = -0.7 * a * (1.0 - f / 0.12) - 0.1 * a
        elif f > 0.86:
            d = 0.9 * a * ((f - 0.86) / 0.14)
        else:
            d = -0.1 * a + 0.2 * a * math.sin(f * math.pi)
        return k, d

    # ------------------------------------------------------------------ cara natural
    def F_libre(self, i, z):
        """Cara natural SUAVE (sin textura ni empotrado) de la columna i a la cota z, con los
        contrafuertes de las horquillas y el tope radial."""
        i %= self.M
        H = self.z_top - self.z_mar
        t = (self.z_top - z) / H
        a = self.a[i]
        if t <= 0.0:
            sh = 0.0
        elif t <= 1.0:
            sh = (1.0 - a) * t + a * t * t
        else:
            sh = 1.0 + (1.0 + a) * (t - 1.0)
        R = self.R_top[i] + (self.R_bot[i] - self.R_top[i]) * sh
        for cf in self.contrafuertes:
            R = self._contrafuerte(cf, i, z, R)
        return min(R, self.R_cap[i])

    def empotrado(self, i, z):
        """Radio minimo para que la roca entre 1.5 m en el terreno a la cota z (None si el
        terreno no llega a z junto al contorno)."""
        rt = self.r_terreno(i, z)
        if rt is None or rt > self.R_cap[i % self.M] + 2.0:
            return None
        # sobre un rellano casi llano el pie no se extiende como una lengua de roca sobre la hierba:
        # como mucho 1.5 m mas alla de donde el terreno llega a z - 1.5 (el test veia 'huecos')
        rt2 = self.r_terreno(i, z - 1.5)
        if rt2 is not None:
            rt = min(rt, rt2 + 1.5)
        return min(rt + 1.5, self.R_cap[i % self.M])

    def F(self, i, z):
        R = self.F_libre(i, z)
        e = self.empotrado(i, z)
        return R if e is None else max(R, e)

    def _contrafuerte(self, cf, i, z, R):
        """Contrafuerte bajo la plataforma de una horquilla: cara a ~73 grados que nace en el
        borde exterior de la plataforma y se funde con la roca a los lados (gaussiana)."""
        if z > cf['z'] - 0.2:
            return R
        ref = cf['ref'].get(i % self.M)
        if ref is None:
            return R
        c, w = ref
        R_b = c['R_out'] + 0.5 + 0.30 * (cf['z'] - z)
        return R + max(0.0, R_b - R) * w

    def textura(self, i, z):
        """Relieve de la cara para la malla: bultos (2 escalas), costillas verticales y
        bancos de estrato. Devuelve (desplazamiento, banco)."""
        p = self.phi[i % self.M]
        cp, sp = math.cos(p), math.sin(p)
        n2 = _ruido(cp * 6.0 + 3.0 + self.seed, sp * 6.0, z * 0.06)
        n3 = _ruido(cp * 14.0 + 9.0, sp * 14.0 + self.seed, z * 0.012)
        rib = _ruido(cp * 30.0 + 1.0, sp * 30.0 - 4.0, z * 0.008)
        k, d = self.estrato(i, z)
        amp = 1.0 if z > self.z_mar - 0.5 else 0.4
        return amp * (2.0 * n2 + 1.1 * n3 + 1.2 * rib + d), k

    # ------------------------------------------------------------------ trazado: cruces
    def _reset_trazado(self):
        self.cruces = [[] for _ in range(self.M)]
        self.cadenas = {}
        self.horquillas = []
        self.contrafuertes = []
        self.fin = None
        self.orden = []
        self.cala = []
        self.espigon = None
        self.largo_cala = 0.0
        self.avisos_t = []

    def _ref(self, i, z, excluir=()):
        """Radio exterior mayor de lo que hay ENCIMA de la cota z en la columna i (repisas
        de pasadas anteriores y borde de la meseta)."""
        R = self.R_top[i]
        for c in self.cruces[i]:
            if c['z'] > z - 0.01 and c['leg'] not in excluir and c['R_out'] > R:
                R = c['R_out']
        return R

    def _cruce(self, i, z, W, kind, leg, hacia='fuera', lado='out', excluir=(), dentro=0.0):
        """Repisa de anchura W en (i, z): su borde exterior natural esta en la cara (F + 0.3);
        las anchas crecen hacia fuera (plataforma, muelle) o hacia dentro (entrada); nunca
        bajo lo que hay encima (R_in >= borde exterior de las repisas superiores)."""
        i %= self.M
        R_ref = self._ref(i, z, excluir)
        R_nat = self.F_libre(i, z) + 0.3
        R_in = R_nat - (W if hacia == 'dentro' else self.W_CARRIL) - dentro
        if kind == 'carretera':           # la calzada no pasa del tope suavizado (se talla hacia dentro)
            R_in = min(R_in, self.R_cap_v[i] - W)
        R_in = max(R_in, R_ref)
        return {'i': i, 'z': float(z), 'W': float(W), 'kind': kind, 'leg': leg,
                'R_in': R_in, 'R_out': R_in + W, 'lado': lado}

    def _registrar(self, c):
        self.n_reg = getattr(self, 'n_reg', 0) + 1
        c['orden'] = self.n_reg
        self.cruces[c['i']].append(c)
        self.cadenas.setdefault(c['leg'], []).append(c)

    def _quitar(self, c):
        self.cruces[c['i']] = [x for x in self.cruces[c['i']] if x is not c]

    def r_eje(self, c, lado=None):
        """Radio del eje del carril en el cruce: por dentro ('in') o por fuera ('out')."""
        lado = lado or c['lado']
        return c['R_in'] + 3.1 if lado == 'in' else c['R_out'] - c.get('d_out', 3.1)

    def ds(self, c, lado=None):
        return max(4.0, self.r_eje(c, lado)) * self.dphi

    def _marchar(self, leg, i0, z0, s, g, z_lim, tol, r_fuera, max_cols=None, registrar=True, zanja=(0.3, 15.0, 0.0),
                 desfase=None):
        """Avanza columna a columna (sentido s) con pendiente g (> 0 baja) hasta z_lim o hasta
        que el terreno (o el tope radial) bloquea la repisa: terreno sobre la repisa o, pasados
        zanja[2] m, terreno por encima de z + zanja[0] a menos de zanja[1] m del borde
        exterior (la carretera iria en zanja detras del espolon). Devuelve (cruces, motivo)."""
        M = self.M
        out = []
        i, z = i0 % M, z0
        arc = 0.0
        while len(out) < (max_cols or M):
            dentro = 0.0 if desfase is None else desfase[0] * (1.0 - _smooth01(arc / desfase[1]))
            c = self._cruce(i, z, self.W_CARRIL, 'carretera', leg, dentro=dentro)
            bloq = None
            if c['R_out'] > self.R_cap[i] + 0.3:
                bloq = 'tope'
            elif not self.libre(i, z, c['R_in'] + 0.5, c['R_out'] + r_fuera, tol):
                bloq = 'terreno'
            elif arc >= zanja[2]:
                rt = self.r_terreno(i, z + zanja[0])
                if rt is not None and rt < c['R_out'] + zanja[1]:
                    bloq = 'zanja'
            if bloq:
                self.bloqueo = (leg, i, round(z, 1), bloq, round(c['R_out'], 1))
                return out, 'bloqueo'
            arc += self.ds(c)
            if registrar:
                self._registrar(c)
            out.append(c)
            if (g > 0 and z <= z_lim + 1e-6) or (g < 0 and z >= z_lim - 1e-6):
                return out, 'fin'
            z = z - g * self.ds(c)
            z = max(z, z_lim) if g > 0 else min(z, z_lim)
            i = (i + s) % M
        return out, 'vuelta'

    # ------------------------------------------------------------------ trazado: entrada y subida
    def _trazar_entrada(self):
        """Plataforma de 10 m (crece hacia dentro de la cara) centrada en la columna de la
        entrada pedida o, si alli el terreno la entierra, en la libre mas cercana."""
        M = self.M

        def plataforma(i0):
            ds0 = max(4.0, self.F_libre(i0, self.z_ent) - 3.0) * self.dphi
            n_e = max(3, int(math.ceil(9.0 / ds0)))
            cs = [self._cruce(i0 + k, self.z_ent, self.W_ENTRADA, 'entrada', 'ent', hacia='dentro') for k in range(-n_e, n_e + 1)]
            ok = all(self.libre(c['i'], c['z'], c['R_in'] + 0.5, c['R_out'] - 0.5, 2.5) for c in cs)
            return cs, ok, n_e
        hit = None
        for d in range(0, M // 4):
            for i0 in ([self.i_pedida] if d == 0 else [(self.i_pedida + d) % M, (self.i_pedida - d) % M]):
                cs, ok, n_e = plataforma(i0)
                if ok:
                    hit = (i0, cs, n_e, d)
                    break
            if hit:
                break
        if hit is None:
            cs, ok, n_e = plataforma(self.i_pedida)
            hit = (self.i_pedida, cs, n_e, 0)
            self.avisos_t.append('entrada: el terreno entierra la plataforma en todas las columnas cercanas')
        self.i_ent, cs, self.n_ent, d = hit
        if d:
            self.avisos_t.append('entrada movida %d columnas (terreno sobre z_entrada en la pedida)' % d)
        for c in cs:
            self._registrar(c)

    def _elegir_sentido(self, subida='opuesto'):
        """La bajada va hacia el lado con mas columnas libres bajando; la subida al otro lado
        ('opuesto') o por dentro de la bajada en el mismo sentido ('mismo')."""
        mejor = None
        for s in (1, -1):
            i0 = (self.i_ent + s * (self.n_ent + 1)) % self.M
            cb, _mb = self._marchar('tmp', i0, self.z_ent, s, self.g_baj, self.z_cala, -0.3, 4.0, registrar=False, zanja=(0.3, 15.0, 20.0))
            i1 = (self.i_ent - s * (self.n_ent + 1)) % self.M
            cs_, ms = self._marchar('tmp', i1, self.z_ent, -s, -self.g_sub, self.z_top, 1.2, 0.5, registrar=False, zanja=(1.5, 1.0, 30.0))
            pts = len(cb) + (200 if ms == 'fin' else len(cs_))
            if mejor is None or pts > mejor[0]:
                mejor = (pts, s)
        self.s_baj = mejor[1]
        self.s_sub = -mejor[1] if subida == 'opuesto' else mejor[1]

    def _trazar_subida(self):
        """Rama corta: de la plataforma de entrada a la meseta por el otro lado (<= g_sub);
        las 4 ultimas columnas a z_top pegadas a la meseta (hueco de la balaustrada)."""
        M, s = self.M, self.s_sub
        i0 = (self.i_ent + s * (self.n_ent + 1)) % M
        # si comparte cara con la bajada, sale por el carril interior de la plataforma de entrada
        des = (self.W_ENTRADA - self.W_CARRIL, 40.0) if s == self.s_baj else None
        cs, mot = self._marchar('sub', i0, self.z_ent, s, -self.g_sub, self.z_top, 1.2, 0.5, zanja=(1.5, 1.0, 30.0), desfase=des)
        if mot != 'fin':
            self.avisos_t.append('subida bloqueada por el terreno a z %.1f (%d columnas)' % (cs[-1]['z'] if cs else self.z_ent, len(cs)))
        i = ((cs[-1]['i'] if cs else i0) + s) % M
        for _k in range(4):
            self._registrar(self._cruce(i, self.z_top, self.W_CARRIL, 'plaza_entrada', 'sub'))
            i = (i + s) % M

    # ------------------------------------------------------------------ trazado: bajada
    def _trazar_bajada(self):
        """Bajada desde la plataforma de entrada: pasadas a g_baj por la cara libre; donde el
        terreno corta el paso, horquilla (<= n_horq_max) y vuelta en sentido contrario; al
        llegar a z_cala, muelle de la cala."""
        M = self.M
        s = self.s_baj
        i = (self.i_ent + s * (self.n_ent + 1)) % M
        z = self.z_ent
        n_leg = 0
        while True:
            leg = 'b%d' % n_leg
            zanja = (0.3, 15.0, 20.0) if n_leg == 0 else (0.3, 3.0, 0.0)     # al final del arco libre la repisa
            cs, mot = self._marchar(leg, i, z, s, self.g_baj, self.z_cala, -0.3, 4.0, zanja=zanja)   # puede ir en trinchera corta
            self.orden.append((leg, s))
            if mot == 'fin':
                if self._trazar_cala(leg, s):
                    self.fin = 'cala'
                    return
                if self.largo_cala >= 20.0:
                    self.fin = 'cala_corta'
                    return
                # v2: muelle imposible (la tierra lo corta a < 20 m): se quita; espigon o plataforma final (abajo)
                for c in self.cala:
                    self._quitar(c)
                self.cala = []
                self.cadenas.pop('cala', None)
                self.largo_cala = 0.0
            if self.con_espigon and self._espigon(leg, s):
                self.fin = 'cala'
                return
            if mot == 'bloqueo' and len(self.horquillas) < self.n_horq_max and self._horquilla(leg, s, n_leg):
                h = self.horquillas[-1]
                s = -s
                i, z = h['i_sig'], h['z_sig']
                n_leg += 1
                continue
            # v2 (G2-01): la calzada NUNCA muere contra la roca: plataforma de fin como la de las horquillas
            # (lazo con isla y pino para dar la vuelta, parapeto) = mirador; sin sitio para ella, 'sin_salida'
            z_f = cs[-1]['z'] if cs else z
            if self._horquilla(leg, s, n_leg):
                self.horquillas[-1]['final'] = True
                self.fin = 'mirador'
            else:
                self.fin = 'sin_salida'
            self.avisos_t.append('bajada: sin cala a z %.1f tras %d horquillas (fin %s)' % (z_f, len(self.horquillas), self.fin))
            return

    def _horquilla(self, leg, s, n):
        """Horquilla al final de la pasada `leg` (sentido s): se busca hacia atras la ultima
        columna donde cabe la plataforma (W_PLAT, llana, n_b columnas antes del lazo y n_f
        despues) sin que la entierre el terreno; primero volada hacia fuera sobre un
        contrafuerte, si no cabe medio tallada y si no tallada hacia dentro (entonces el
        carril que llega se mete suavemente en la talla). El carril que llega (A) va por
        dentro de la plataforma y el que sale (B) por fuera."""
        M = self.M
        cad = self.cadenas.get(leg, [])
        tag = 'pl%d' % n
        W = self.W_PLAT
        for k_h in range(len(cad) - 1, max(3, len(cad) - 80), -1):
            c_h = cad[k_h]
            ds_h = self.ds(c_h)
            n_b = max(2, int(math.ceil(8.0 / ds_h)))
            n_f = int(math.ceil((self.RHO + 2.5 + 1.2) / max(1.0, (self.r_eje(c_h) + self.RHO) * self.dphi))) + 1
            if k_h - n_b < 3:
                return False
            z_h = cad[k_h - n_b]['z']
            cols = [cad[k]['i'] for k in range(k_h - n_b, k_h + 1)] + [(c_h['i'] + s * j) % M for j in range(1, n_f + 1)]
            prev = cad[:k_h - n_b]
            for w_dentro in (0.0, (W - self.W_CARRIL) / 2.0, W - self.W_CARRIL):
                plat = []
                for col in cols:
                    c = self._cruce(col, z_h, W, 'plataforma', tag, excluir=(leg,))
                    R_in = max(c['R_in'] - w_dentro, self._ref(col, z_h, (leg,)))
                    c['R_in'], c['R_out'] = R_in, R_in + W
                    plat.append(c)
                R_u = max(c['R_in'] for c in plat)
                for c in plat:
                    c['R_in'], c['R_out'] = R_u, R_u + W
                if any(c['R_out'] > self.R_cap[c['i']] + 0.3 or
                       not self.libre(c['i'], z_h, c['R_in'] + 0.5, c['R_out'] + 1.5, -0.3, (0.3, 3.0)) for c in plat):
                    continue
                # v2: la pasada siguiente arranca en la columna de antes de la plataforma y como mucho llega al tope de
                # la calzada (R_cap_v): una plataforma volada mas alla dejaba su carril exterior hasta 30 m por fuera
                # del primer cruce (salto en la cinta, quads cruzados). Se prueba entonces la tallada.
                i_sig0 = (cols[0] - s) % M
                if R_u + W - 3.1 > min(self.R_cap_v[i_sig0], self.R_cap[i_sig0] + 0.3) - 3.1 + 2.0:
                    continue
                # el carril que llega se mete en la talla (rampa suave) si la plataforma va dentro
                tir = []
                delta0 = prev[-1]['R_in'] - R_u
                if delta0 > 0.05:
                    L = max(14.0, delta0 / 0.32)
                    d = 0.0
                    for c in reversed(prev):
                        d += self.ds(c)
                        if d > L:
                            break
                        obj = R_u + (c['R_in'] - R_u) * _smooth01(d / L)
                        if obj < self._ref(c['i'], c['z'], (leg,)) - 1e-6:
                            tir = None
                            break
                        tir.append((c, obj))
                    if tir is None:
                        continue
                for (c, obj) in tir:
                    c['R_in'], c['R_out'] = obj, obj + self.W_CARRIL
                    c['fijo'] = True
                for c in cad[k_h - n_b:]:
                    self._quitar(c)
                del cad[k_h - n_b:]
                # v2: si la pasada siguiente tiene que arrancar por fuera del carril exterior de la plataforma (la
                # pasada que llega va encima), la plataforma se ensancha hacia fuera (<= 4 m): sin escalon lateral
                i_sig = (cols[0] - s) % M
                c_sig = self._cruce(i_sig, z_h - self.g_baj * self.ds(plat[0], 'out'), self.W_CARRIL, 'carretera', 'tmp')
                extra = min(4.0, (c_sig['R_out'] - 3.1) - (R_u + W - 3.1))
                if extra > 0.3 and all(R_u + W + extra <= self.R_cap[c['i']] + 0.3 and
                                       self.libre(c['i'], z_h, c['R_out'], c['R_out'] + extra + 1.5, -0.3) for c in plat):
                    for c in plat:
                        c['W'] = W + extra
                        c['R_out'] = R_u + W + extra
                for c in plat:
                    self._registrar(c)
                ref = {}
                for dc in range(-26, 27):
                    col = (cols[0] + dc) % M
                    if col in cols:
                        ref[col] = (plat[cols.index(col)], 1.0)
                        continue
                    k_c = min(range(len(cols)), key=lambda q: abs(self.dcol(col, cols[q])))
                    d_m = abs(self.dcol(col, cols[k_c])) * self.dphi * plat[k_c]['R_out']
                    w = math.exp(-(d_m / 11.0) ** 2)
                    if w > 0.02:
                        ref[col] = (plat[k_c], w)
                self.contrafuertes.append({'z': z_h, 'ref': ref})
                h = {'i': c_h['i'], 'z': z_h, 's': s, 'cols': cols, 'plat': plat, 'leg_in': leg, 'tag': tag,
                     'n_b': n_b, 'n_f': n_f, 'leg_out': 'b%d' % (n + 1), 'w_dentro': w_dentro}
                h['i_sig'] = (cols[0] - s) % M
                h['z_sig'] = z_h - self.g_baj * self.ds(plat[0], 'out')
                self.horquillas.append(h)
                return True
        return False

    def _espigon(self, leg, s):
        """Si la pasada baja de espigon_z_max (11 m) pero el arco libre se acaba antes del nivel
        del mar, la carretera deja la roca por un ESPIGON (dique con calzada) que se abre hacia
        el mar bajando a g_baj hasta el muelle de la cala (26 x 62 m) con pantalan. Se elige la
        primera columna en la que espigon y muelle caben en el mar sin tocar el pie de la roca."""
        z_max = float(self.params.get('espigon_z_max', 18.0))
        cad = self.cadenas.get(leg, [])
        for k, c in enumerate(cad):
            if c['z'] > z_max or k < 4:
                continue
            r = self._ruta_espigon(c, s)
            if r is None:
                continue
            for c2 in cad[k + 1:]:
                self._quitar(c2)
            del cad[k + 1:]
            self.espigon = r
            self.largo_cala = r['L_q']
            self.s_cala = s
            return True
        return False

    def _fuera_de_roca(self, x, y, margen):
        """True si (x, y) esta en el mar y a > margen del pie de la roca."""
        ang = math.atan2(y - self.cy, x - self.cx) % TAU
        i = int(round(ang / self.dphi)) % self.M
        if math.hypot(x - self.cx, y - self.cy) < self.F(i, self.z_mar) + margen:
            return False
        return self.terreno_fn is None or self.terreno_fn(x, y) <= self.z_mar + 0.3

    # variantes del espigon (radio de giro, metros de giro, largo del muelle): la primera es la
    # original; las otras giran mas o menos para entrar en la ensenada libre (ronda 15, v1: con los
    # radios definitivos la original topaba con la ladera N y la bajada se quedaba sin cala)
    VARIANTES_ESPIGON = ((42.0, 36.0, 72.0), (30.0, 36.0, 72.0), (30.0, 54.0, 72.0), (24.0, 66.0, 72.0),
                         (42.0, 20.0, 72.0), (60.0, 36.0, 72.0), (24.0, 90.0, 72.0), (42.0, 36.0, 58.0),
                         (30.0, 54.0, 58.0), (24.0, 66.0, 58.0), (30.0, 80.0, 58.0), (60.0, 20.0, 58.0))

    def _roca_encima_xy(self, x, y, z, margen=3.0):
        """True si la cara de la roca (perfil SIN textura, con los recortes de las repisas de esa
        columna y un margen para el relieve) pasa por encima de (x, y) a mas de z + 0.8."""
        r = math.hypot(x - self.cx, y - self.cy)
        f = (math.atan2(y - self.cy, x - self.cx) % TAU) / self.dphi
        for i in (int(math.floor(f)) % self.M, int(math.ceil(f)) % self.M):
            zz = z + 0.8
            while zz < self.z_top:
                R = self.F(i, zz) + margen
                cortes = [c['R_in'] for c in self.cruces[i] if c['z'] < zz - 0.005]
                if cortes and min(cortes) + 0.3 < R:          # recorte de la repisa: sin relieve
                    R = min(cortes) + 0.3
                if R > r:
                    return True
                zz += 2.0 if zz < z + 10.0 else 6.0
        return False

    def _ruta_espigon(self, c, s):
        """Primera variante de espigon + muelle que cabe en el mar desde el cruce c (None si ninguna)."""
        for (R_g, d_g, L_q) in self.VARIANTES_ESPIGON:
            r = self._ruta_espigon_v(c, s, R_g, d_g, L_q)
            if r is not None:
                return r
        return None

    def _ruta_espigon_v(self, c, s, R_g, d_g, L_q):
        phi = self.phi[c['i']]
        x, y = self.xy(c['i'], self.r_eje(c))
        z = c['z']
        h = phi + s * math.pi / 2.0
        cad = self.cadenas.get(c['leg'], [])
        k = next((q for q, cc in enumerate(cad) if cc is c), None)
        if k is not None and k >= 1:
            xa, ya = self.xy(cad[k - 1]['i'], self.r_eje(cad[k - 1]))
            h = math.atan2(y - ya, x - xa)
        pts = [(x, y, z)]
        paso, d = 2.5, 0.0
        while z > self.z_cala + 1e-6 or d < max(30.0, d_g):
            if d < d_g:
                h -= s * paso / R_g                      # se abre hacia fuera de la roca
            x += paso * math.cos(h)
            y += paso * math.sin(h)
            d += paso
            z = max(self.z_cala, z - self.g_baj * paso)
            pts.append((x, y, z))
            if d > 170.0:
                return None
        for k, (px, py, _pz) in enumerate(pts):
            if k * paso >= 10.0 and not self._fuera_de_roca(px, py, 4.5):
                return None
        # nada ENCIMA del dique: ni repisas de pasadas superiores, ni la meseta, ni contrafuertes de
        # horquillas en talud; en los primeros D_SALIDA m la cara natural se talla (cruces 'salida')
        propias = set(cc['i'] for cc in cad)
        salida = {}
        for k in range(1, len(pts)):
            px, py, pz = pts[k]
            hx, hy = pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]
            lh = math.hypot(hx, hy) or 1.0
            for v in (-2.5, 0.0, 2.5):
                qx, qy = px - hy / lh * v, py + hx / lh * v
                rq = math.hypot(qx - self.cx, qy - self.cy)
                f = (math.atan2(qy - self.cy, qx - self.cx) % TAU) / self.dphi
                cols = (int(math.floor(f)) % self.M, int(math.ceil(f)) % self.M)
                if any(rq - 0.3 < self._ref(i, pz, (c['leg'],)) for i in cols):
                    return None
                if k * paso <= self.D_SALIDA:
                    for i in cols:
                        if i not in propias:
                            salida.setdefault(i, []).append((pz, rq))
                elif self._roca_encima_xy(qx, qy, pz):
                    return None
        A_q, L_p = 26.0, 30.0
        ux, uy = math.cos(h), math.sin(h)
        vx, vy = -uy, ux
        ex, ey = pts[-1][0], pts[-1][1]
        for u in [u_ for u_ in (0.0, 15.0, 31.0, 46.0, 60.0) if u_ < L_q] + [L_q, L_q + L_p / 2.0, L_q + L_p]:
            for v in ((-A_q / 2.0, 0.0, A_q / 2.0) if u <= L_q else (-5.0, 0.0, 5.0)):
                if not self._fuera_de_roca(ex + ux * u + vx * v, ey + uy * u + vy * v, 4.0):
                    return None
        lado_roca = 1.0 if ((self.cx - ex) * vx + (self.cy - ey) * vy) > 0 else -1.0
        return {'pts': pts, 'u': (ux, uy), 'v': (vx, vy), 'o': (ex, ey), 'L_q': L_q, 'A_q': A_q, 'L_p': L_p,
                'lado_roca': lado_roca, 'i0': c['i'], 'z0': c['z'], 'salida': salida}

    def _aplicar_salida(self, e):
        """Talla de la salida del espigon: en las columnas que el dique cruza al dejar la roca
        (primeros D_SALIDA m) una repisa 'salida' bajo el dique recorta la cara de encima."""
        for i, lst in e.get('salida', {}).items():
            R_in = min(p[1] for p in lst) - 1.1
            R_out = max(p[1] for p in lst) + 1.1
            z = min(p[0] for p in lst) - 0.05
            self._registrar({'i': i, 'z': z, 'W': R_out - R_in, 'kind': 'salida', 'leg': 'esp',
                             'R_in': R_in, 'R_out': R_out, 'lado': 'out'})

    def _trazar_cala(self, leg, s):
        """Muelle de la cala a z_cala (26 m, crece hacia el mar) desde donde la bajada llega al
        nivel del muelle, hasta largo_muelle o hasta que topa con tierra."""
        M = self.M
        cad = self.cadenas[leg]
        c0 = cad.pop()
        self._quitar(c0)
        i = c0['i']
        L_max = float(self.params.get('largo_muelle', 72.0))
        L = 0.0
        quay = []
        while L < L_max and len(quay) < M // 3:
            c = self._cruce(i, self.z_cala, self.W_CALA, 'cala', 'cala')
            if c['R_out'] > self.R_cap[i] + 0.3 or not self.libre(i, self.z_cala, c['R_in'] + 1.0, c['R_out'] + 3.0, -1.0):
                break
            quay.append(c)
            L += (c['R_in'] + 6.0) * self.dphi
            i = (i + s) % M
        for c in quay:
            self._registrar(c)
        self.cala = quay
        self.largo_cala = L
        self.s_cala = s
        if L < 45.0:
            self.avisos_t.append('cala: muelle de solo %.0f m (topa con tierra)' % L)
        return L >= 45.0

    # ------------------------------------------------------------------ trazado: busqueda y ajuste
    def vueltas(self):
        """Recorrido angular de la bajada (suma de |dphi| de entrada a muelle) en vueltas."""
        n = sum(len(self.cadenas.get(leg, [])) for (leg, _s) in self.orden)
        n += sum(len(h['cols']) - h['n_f'] - 1 for h in self.horquillas) * 2
        n += self.n_ent + len(self.cala) // 3
        return n * self.dphi / TAU

    def _intento(self, op):
        """Traza entrada, subida y bajada con la forma op = (f_bot, a_med, k_top, subida, apoyo)."""
        f, a, k, sub, ap = op
        self._forma(f, a, k, ap)
        self._reset_trazado()
        self._trazar_entrada()
        self._elegir_sentido(sub)
        self._trazar_subida()
        self._trazar_bajada()

    def _nota_traza(self):
        """Nota del trazado SIN ajustar (menor = mejor): llegar a la cala, pocas vueltas."""
        v = self.vueltas()
        z_fin = min((c['z'] for leg, _s in self.orden for c in self.cadenas.get(leg, [])), default=self.z_ent)
        nota = (0.0 if self.fin == 'cala' else 1000.0 + 10.0 * z_fin) + 100.0 * v + 8.0 * (self.f_bot - 1.2)
        return nota + (0.0 if self.largo_cala >= 55.0 else 20.0)

    def _rehacer_espigon(self):
        """Con los radios definitivos el espigon se vuelve a trazar desde el carril YA ajustado: el
        primer cruce de la ultima pasada (bajo espigon_z_max) desde el que cabe alguna variante; los
        cruces que siguen se quitan. Si no cabe ninguna la pasada NO se vacia (antes se borraba entera
        y la bajada moria en la horquilla a 47 m sobre el mar): queda sin espigon y la nota lo castiga."""
        if self.espigon is None or not self.orden:
            return
        leg, s = self.orden[-1]
        cad = self.cadenas.get(leg, [])
        z_max = float(self.params.get('espigon_z_max', 18.0))
        for k, c in enumerate(cad):
            if c['z'] > z_max + 0.6 or k < 4:
                continue
            r = self._ruta_espigon(c, s)
            if r is None:
                continue
            for c2 in cad[k + 1:]:
                self._quitar(c2)
            del cad[k + 1:]
            self.espigon = r
            self.largo_cala = r['L_q']
            self._aplicar_salida(r)
            return
        self.espigon = None
        self.fin = 'sin_cala'
        self.avisos_t.append('espigon: no cabe con los radios definitivos')

    def _calidad(self):
        """Defectos del trazado ya ajustado (0 = ninguno) y nota: sin cala, pendiente > 11 %,
        quiebros laterales > 0.3 m/m, voladizos del apilado; desempata por vueltas."""
        sub, baj = self._cintas()
        pend = max(_pendiente_max(sub), _pendiente_max(baj))
        q = max(_quiebro_max(sub), _quiebro_max(baj, self._idx_lazos(baj)))
        # v2 (G2-01): sin cala pero con plataforma para dar la vuelta (mirador) o muelle corto: 1000; calzada que
        # muere contra la roca (espigon que no cabe con los radios definitivos, sin plataforma): 1500
        fin_m = 0 if self.fin == 'cala' else (1000 if self.fin in ('mirador', 'cala_corta') else 1500)
        malo = fin_m + (100 if pend > 0.1100 else 0) + (50 if q > 0.3 else 0)
        malo += 10 * self.n_voladizos + 5 * self.n_estrechos
        return malo, malo + 100.0 * self.vueltas() + 300.0 * max(0.0, pend - 0.105)

    def _idx_lazos(self, baj):
        """Indices de la bajada en los lazos de las horquillas (giros cerrados que no son quiebros)."""
        lazos = set()
        for h in self.horquillas:
            c0 = h.get('centro')
            if not c0:
                continue
            for kk, p in enumerate(baj):
                if math.hypot(p[0] - c0[0], p[1] - c0[1]) < h.get('rho', self.RHO) + 1.0:
                    lazos.update((kk - 1, kk, kk + 1))
        return lazos

    def trazar(self):
        """Prueba varias formas del pie (apertura hacia el mar, concavidad) y sentidos de la subida;
        las ordena por la nota del trazado y, en ese orden, AJUSTA cada una (apilado, ejes suaves,
        cotas) y rehace el espigon con los radios definitivos: se queda con la primera sin defectos
        (cala, pendiente <= 11 %, sin quiebros ni voladizos) o, si ninguna lo consigue, con la mejor.
        Si la pendiente ajustada pasa del 11 % se repite con la pendiente nominal un poco menor."""
        opciones = self.params.get('formas') or [(f, a, k, ap) for f in (1.35, 1.5, 1.65) for a in (-0.7, -0.4)
                                                 for k in (0.62, 0.72, 0.8) for ap in (0.0, 0.6)]
        self.g_nom = self.g_baj
        mejor = self._buscar(opciones, 'espigon')
        # v2 (G2-01): si ninguna forma sale limpia (p. ej. el espigon no cabe con los radios definitivos y la
        # bajada moria a z 15.8 contra la roca), modo 'roca': sin espigon y con una horquilla mas, la bajada
        # sigue por la cara libre hasta el nivel del mar y acaba en la CALA al pie de la roca (muelle con
        # casas, pantalan y lanchas). Se queda la mejor de las dos busquedas.
        if mejor[0][0] and int(self.params.get('horquillas_extra', 1)) > 0:
            otro = self._buscar(opciones, 'roca')
            if otro[0] < mejor[0]:
                mejor = otro
        (malo, _nota), g, op, modo = mejor
        self._modo(modo)
        self.g_baj = g
        self._intento(op)
        self._ajustar()
        self._rehacer_espigon()
        if self.fin == 'sin_cala':
            # red de seguridad: el mismo trazado sin espigon acaba en una plataforma para dar la vuelta
            self._modo('mirador')
            self._intento(op)
            self._ajustar()
            malo, _nota = self._calidad()
        if malo:
            self.avisos_t.append('trazado con defectos (nota %d): fin %s, modo %s' % (malo, self.fin, self.modo))
        self.avisos.extend(self.avisos_t)

    def _modo(self, modo):
        """'espigon': horquillas_max y espigon cuando se acaba la cara; 'roca': sin espigon y horquillas_extra
        horquillas mas (cala al pie de la roca); 'mirador': sin espigon con horquillas_max (plataforma final)."""
        self.modo = modo
        self.con_espigon = modo == 'espigon'
        self.n_horq_max = self.n_horq_base + (int(self.params.get('horquillas_extra', 1)) if modo == 'roca' else 0)

    def _buscar(self, opciones, modo):
        """Busqueda del trazado en un modo: todas las formas, ordenadas por la nota del trazado sin ajustar; se
        AJUSTAN las mejores y se queda la primera sin defectos (o la mejor). Devuelve ((malo, nota), g, op, modo)."""
        self._modo(modo)
        mejor = None
        for g in (self.g_nom, self.g_nom - 0.004, self.g_nom - 0.008):
            self.g_baj = g
            notas = []
            for sub in ('opuesto', 'mismo'):
                for (f, a, k, ap) in opciones:
                    op = (f, a, k, sub, ap)
                    self._intento(op)
                    notas.append((self._nota_traza(), len(notas), op))
            notas.sort()
            for (_n, _k, op) in notas[:int(self.params.get('candidatos', 10))]:
                self._intento(op)
                self._ajustar()
                self._rehacer_espigon()
                malo, nota = self._calidad()
                if mejor is None or (malo, nota) < mejor[0]:
                    mejor = ((malo, nota), g, op, modo)
                if malo == 0:
                    break
            if mejor[0][0] == 0:
                break
        return mejor

    def _grupo(self, c):
        """Grupos rigidos: la plataforma de cada horquilla (se mueve entera) y la entrada
        (fija: alli llega el espolon)."""
        if c['kind'] == 'plataforma':
            return c['leg']
        if c['kind'] == 'entrada':
            return 'ent'
        return None

    def _desplazar(self, c, d):
        c['R_in'] += d
        c['R_out'] += d

    def _secuencias(self):
        """Secuencias (cruce, lado del carril) en orden de paso, con los extremos de las
        plataformas vecinas como anclas, para suavizar los ejes."""
        ent = self.cadenas['ent']
        extremo = {1: ent[-1], -1: ent[0]}
        seqs = [[(extremo[self.s_sub], 'out')] + [(c, 'out') for c in self.cadenas.get('sub', [])]]
        prev = (extremo[self.s_baj], 'out')
        for n, (leg, _s) in enumerate(self.orden):
            seq = [prev] + [(c, c['lado']) for c in self.cadenas.get(leg, [])]
            if n < len(self.horquillas):
                p0 = self.horquillas[n]['plat'][0]
                seq.append((p0, 'in'))
                prev = (p0, 'out')
            elif self.cala:
                seq += [(c, 'in') for c in self.cala[:4]]
            seqs.append(seq)
        return seqs

    def _envolvente(self, seq, r, fijos=None):
        """Envolvente SUAVE por encima de r (sin quiebros): dilatacion (+-2 muestras) y media
        movil triangular (+-3); nunca baja de r. No limita dR/ds: el eje puede seguir el
        contorno (una elipse cambia de radio hasta ~0.8 m por m junto a las muescas). Las muestras
        fijas (rampa hacia una plataforma tallada) no se dilatan sobre sus vecinas: en pendiente
        la dilatacion desplaza la curva 2 muestras y dejaba un escalon de 1.5 m en la union."""
        n = len(r)
        fijos = fijos or [False] * n
        dil = [max(r[j] for j in range(max(0, k - 2), min(n, k + 3)) if j == k or not fijos[j]) for k in range(n)]
        sua = []
        for k in range(n):
            s_ = w_ = 0.0
            for j in range(-3, 4):
                if 0 <= k + j < n:
                    pw = 4.0 - abs(j)
                    s_ += dil[k + j] * pw
                    w_ += pw
            sua.append(max(r[k], s_ / w_))
        return sua

    def _ajustar(self, n_iter=16):
        """Ejes suaves y apilado sin voladizos. Cada iteracion parte de los radios del
        trazado (R_in0) y de lo que exige el apilado con los valores actuales; la envolvente
        suave se calcula sobre esos minimos (no sobre la iteracion anterior: no se infla).
        Las plataformas y la entrada son rigidas (solo las mueve el apilado)."""
        todos = [c for cs in self.cruces for c in cs]
        for c in todos:
            c['R_in0'] = c['R_in']
        for _it in range(n_iter):
            # 1) minimo por apilado (de arriba abajo con los valores actuales)
            req = {}
            for i in range(self.M):
                R_ref = self.R_top[i]
                for c in sorted(self.cruces[i], key=lambda c: (-round(c['z'], 3), c.get('orden', 0))):
                    req[id(c)] = max(c['R_in0'], R_ref)
                    R_ref = max(R_ref, req[id(c)] + c['W'], c['R_out'])
            nuevo_R = {}
            # 2) grupos rigidos: desplazamiento comun = el mayor que pida un miembro
            grupos = {}
            for c in todos:
                g = self._grupo(c)
                if g is not None:
                    grupos[g] = max(grupos.get(g, 0.0), req[id(c)] - c['R_in0'])
            for c in todos:
                g = self._grupo(c)
                if g is not None:
                    nuevo_R[id(c)] = c['R_in0'] + grupos[g]
                elif c.get('fijo'):
                    nuevo_R[id(c)] = req[id(c)]
            # 3) envolvente suave de cada secuencia sobre los minimos
            for seq in self._secuencias():
                r = []
                for (c, l) in seq:
                    R_in = nuevo_R.get(id(c), req[id(c)])
                    r.append(R_in + 3.1 if l == 'in' else R_in + c['W'] - 3.1)
                env = self._envolvente(seq, r, [bool(c.get('fijo')) for (c, _l) in seq])
                for k, (c, l) in enumerate(seq):
                    if id(c) in nuevo_R and (self._grupo(c) is not None or c.get('fijo')):
                        continue
                    R_in = env[k] - (3.1 if l == 'in' else c['W'] - 3.1)
                    R_in = min(R_in, (self.R_cap_v if c['kind'] == 'carretera' else self.R_cap)[c['i']] - c['W'])
                    nuevo_R[id(c)] = max(nuevo_R.get(id(c), 0.0), R_in, req[id(c)])
            cambio = 0.0
            for c in todos:
                R_in = nuevo_R.get(id(c), req[id(c)])
                cambio = max(cambio, abs(R_in - c['R_in']))
                c['R_in'], c['R_out'] = R_in, R_in + c['W']
            if cambio < 0.01:
                break
        self._limitar_quiebros()
        self._ensanchar()
        self._reapilar()
        self._repartir_cotas()
        self._medir()

    def _limitar_quiebros(self, q_obj=0.2, n_iter=80):
        """v2: segunda diferencia del eje limitada en cada secuencia (|r[k-1] + r[k+1] - 2 r[k]| <= 2 q_obj ds:
        quiebro lateral <= q_obj). La dilatacion de la envolvente desplaza 2 muestras la curva donde el eje baja
        deprisa y, al llegar a la rampa fija de una plataforma tallada, dejaba un escalon lateral (quiebro 0.34
        en la entrada de la primera horquilla). Los valles suben y los picos bajan sin salir de [lo que hay
        encima (apilado), tope radial]; si un pico no puede bajar suben sus vecinas. Grupos rigidos fijos."""
        for _rep in range(3):
            lo = {}
            for i in range(self.M):
                R_ref = self.R_top[i]
                for c in sorted(self.cruces[i], key=lambda c: (-round(c['z'], 3), c.get('orden', 0))):
                    lo[id(c)] = R_ref
                    R_ref = max(R_ref, c['R_out'])
            movido = 0.0
            for seq in self._secuencias():
                n = len(seq)
                if n < 3:
                    continue
                # un ancla rigida (plataforma, entrada) sigue a radio constante por fuera de la secuencia: punto
                # virtual fijo antes/despues (el escalon entre la plataforma y la primera muestra cuenta)
                seq = list(seq)
                v0 = self._grupo(seq[0][0]) is not None
                v1 = self._grupo(seq[-1][0]) is not None
                seq = ([seq[0]] if v0 else []) + seq + ([seq[-1]] if v1 else [])
                n = len(seq)
                off = [(3.1 if l == 'in' else c['W'] - 3.1) for (c, l) in seq]
                r = [c['R_in'] + o for (c, l), o in zip(seq, off)]
                mov = [self._grupo(c) is None for (c, l) in seq]
                rlo = [lo.get(id(c), c['R_in']) + o for (c, l), o in zip(seq, off)]
                rhi = []
                for k, (c, l) in enumerate(seq):
                    cap = (self.R_cap_v if c['kind'] == 'carretera' else self.R_cap)[c['i']]
                    rhi.append(max(r[k], cap - c['W'] + off[k]))
                ds = [max(4.0, r[k]) * self.dphi for k in range(n)]
                r0 = list(r)
                for _it in range(n_iter):
                    cambio = 0.0
                    for k in range(1, n - 1):
                        lim = 2.0 * q_obj * ds[k]
                        D = r[k - 1] + r[k + 1] - 2.0 * r[k]
                        if D > lim:                                  # valle: sube, o bajan las vecinas
                            ex = (D - lim) / 2.0
                            d_ = min(ex, rhi[k] - r[k]) if mov[k] else 0.0
                            if d_ > 1e-4:
                                r[k] += d_
                                cambio = max(cambio, d_)
                            resto = ex - max(0.0, d_)
                            if resto > 1e-4:
                                for kk in (k - 1, k + 1):
                                    if mov[kk]:
                                        u = min(resto, r[kk] - rlo[kk])
                                        if u > 1e-4:
                                            r[kk] -= u
                                            cambio = max(cambio, u)
                        elif D < -lim:                               # pico: baja, o suben las vecinas
                            ex = (-D - lim) / 2.0
                            d_ = min(ex, r[k] - rlo[k]) if mov[k] else 0.0
                            if d_ > 1e-4:
                                r[k] -= d_
                                cambio = max(cambio, d_)
                            resto = ex - max(0.0, d_)
                            if resto > 1e-4:
                                for kk in (k - 1, k + 1):
                                    if mov[kk]:
                                        u = min(resto, rhi[kk] - r[kk])
                                        if u > 1e-4:
                                            r[kk] += u
                                            cambio = max(cambio, u)
                    if cambio < 1e-3:
                        break
                for k, (c, l) in enumerate(seq):
                    if mov[k] and abs(r[k] - r0[k]) > 1e-4:
                        c['R_in'] = r[k] - off[k]
                        c['R_out'] = c['R_in'] + c['W']
                        movido = max(movido, abs(r[k] - r0[k]))
            self._reapilar()
            if movido < 0.01:
                break

    def _ensanchar(self):
        """Donde el eje cambia de radio (tan t = dR/ds; muescas del contorno) la cinta de 5 m va
        oblicua a la repisa radial: sin mover el eje, la repisa se ensancha HACIA DENTRO (talla:
        3.1/cos t + 0.2 m, el paredon no toca el borde interior del asfalto) y HACIA FUERA (2.6/cos t
        + 0.65 m: parapeto y farolas fuera del asfalto). Hacia dentro no pasa de lo que hay encima;
        hacia fuera no pasa del tope radial de la roca (R_cap)."""
        self.n_estrechos = 0
        for seq in self._secuencias():
            r = [self.r_eje(c, l) for (c, l) in seq]
            for k, (c, l) in enumerate(seq):
                # v2: tambien la rampa fija hacia una plataforma tallada (va oblicua: su borde interior quedaba bajo
                # la cara de la columna vecina, 1 voladizo en la llegada a la tercera horquilla)
                if c['kind'] != 'carretera' or l != 'out':
                    continue
                k0, k1 = max(0, k - 1), min(len(seq) - 1, k + 1)
                ds = sum(self.ds(seq[q][0], seq[q][1]) for q in (k0, k1)) / 2.0 * max(1, k1 - k0)
                pend = abs(r[k1] - r[k0]) / max(0.5, ds)
                if pend < 0.08:
                    continue
                sec = math.sqrt(1.0 + pend * pend)
                e = r[k]
                R_in = max(min(c['R_in'], e - 3.1 * sec - 0.2), self._ref(c['i'], c['z'], (c['leg'],)))
                R_out = max(c['R_out'], min(e + 2.6 * sec + 0.65, self.R_cap[c['i']] + 0.3))
                if R_in > e - 3.1 * sec + 0.1 or R_out < e + 2.6 * sec + 0.45:
                    self.n_estrechos += 1             # la calzada oblicua no cabe en la repisa
                c['R_in'], c['R_out'] = R_in, R_out
                c['W'] = R_out - R_in
                c['d_out'] = R_out - e

    def _repartir_cotas(self):
        """Con los radios definitivos, cada pasada reparte su desnivel entre sus ANCLAS, que no se
        mueven (plataforma de entrada o de la horquilla anterior -> plataforma de la horquilla
        siguiente, meseta o ultimo cruce), proporcional a la longitud real del eje INCLUIDOS los
        empalmes con las anclas: pendiente uniforme (antes el empalme con la plataforma quedaba
        fuera del reparto y subia al 11.2-11.9 %)."""
        ent = self.cadenas['ent']
        extremo = {1: ent[-1], -1: ent[0]}
        tramos = []
        sub = self.cadenas.get('sub', [])
        pe = [c for c in sub if c['kind'] == 'plaza_entrada']
        tramos.append(((extremo[self.s_sub], 'in' if self.s_sub == self.s_baj else 'out'),
                       [c for c in sub if c['kind'] == 'carretera'], (pe[0], 'out') if pe else None))
        prev = (extremo[self.s_baj], 'out')
        for n, (leg, _s) in enumerate(self.orden):
            sig = (self.horquillas[n]['plat'][0], 'in') if n < len(self.horquillas) else None
            tramos.append((prev, [c for c in self.cadenas.get(leg, []) if c['kind'] == 'carretera'], sig))
            if sig is not None:
                prev = (sig[0], 'out')
        for (ancla, cs, sig) in tramos:
            if len(cs) < 3:
                continue
            pts = [self._lane(ancla[0], ancla[1])] + [self._lane(c) for c in cs]
            if sig is not None:
                pts.append(self._lane(sig[0], sig[1]))
            L = [0.0]
            for a, b in zip(pts, pts[1:]):
                L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
            z0 = ancla[0]['z']
            z1, L1 = (sig[0]['z'], L[-1]) if sig is not None else (cs[-1]['z'], L[len(cs)])
            for c, l in zip(cs, L[1:len(cs) + 1]):
                c['z'] = z0 + (z1 - z0) * l / max(1e-6, L1)

    def _reapilar(self):
        """Seguridad final: cada repisa queda fuera (R_in >= R_out) de todo lo que tiene encima
        (los grupos rigidos se mueven enteros)."""
        cambio = 0.0
        for _rep in range(8):
            grupos = {}
            movido = 0.0
            for i in range(self.M):
                R_ref = self.R_top[i]
                for c in sorted(self.cruces[i], key=lambda c: (-round(c['z'], 3), c.get('orden', 0))):
                    d = R_ref - c['R_in']
                    if d > 1e-4:
                        g = self._grupo(c)
                        if g is None or g == 'ent':
                            self._desplazar(c, d)
                            movido = max(movido, d)
                        else:
                            grupos[g] = max(grupos.get(g, 0.0), d)
                    R_ref = max(R_ref, c['R_out'])
            for g, d in grupos.items():
                for c in self.cadenas[g]:
                    self._desplazar(c, d)
                movido = max(movido, d)
            cambio = max(cambio, movido)
            if movido < 1e-3:
                break
        return cambio

    def _medir(self):
        """Quiebro maximo del eje (m/m), repisas apiladas mal y fuera del tope radial."""
        q = 0.0
        for seq in self._secuencias():
            for (a, la), (b, lb) in zip(seq, seq[1:]):
                q = max(q, abs(self.r_eje(b, lb) - self.r_eje(a, la)) / max(0.5, self.ds(b, lb)))
        self.quiebro_max = q
        malos = fuera = 0
        for i in range(self.M):
            R_ref = self.R_top[i]
            for c in sorted(self.cruces[i], key=lambda c: (-round(c['z'], 3), c.get('orden', 0))):
                if c['R_in'] < R_ref - 0.01:
                    malos += 1
                R_ref = max(R_ref, c['R_out'])
                if c['R_out'] > self.R_cap[i] + 0.5:
                    fuera += 1
        self.n_voladizos = malos
        if malos:
            self.avisos_t.append('apilado: %d repisas bajo otra' % malos)
        if fuera:
            self.avisos_t.append('tope radial: %d repisas salen mas de 0.5 m (junto a tierra)' % fuera)

    # ------------------------------------------------------------------ relleno de grietas y fosos (v2)
    D_RELLENO = 5.0     # el relleno de roca llega como mucho a 5 m del borde del asfalto (cubre la banda de 6 m)
    D_MAX_RELLENO = 22.0
    L_RELLENO = 45.0    # largo radial maximo del arcen de relleno desde la repisa
    # v3 (N3): foso cerrado de tierra (barranco en V entre el penon y la ladera del promontorio)
    FOSO_HONDO = 8.0    # solo si el fondo queda > 8 m bajo el arcen de relleno (una vaguada suave no se toca)
    FOSO_HONDO_VECINA = 2.5   # en los extremos sigue por las vecinas con una hondonada de > 2.5 m (sin pared al final)
    FOSO_ANCHO = 40.0   # la ladera de fuera tiene que volver a la cota del arcen a < 40 m del fondo
    FOSO_LARGO = 55.0   # largo radial maximo del relleno desde la repisa
    FOSO_DZ_COL = 0.25  # pendiente maxima de la cota del arcen de una columna a la siguiente (solo baja: no rebosa)
    FOSO_DR_COL = 1.5   # el largo del relleno no cae mas de 1.5 m por columna (sin dientes radiales en el borde)
    FOSO_SOBRE_LOMA = 1.0   # el arcen puede tapar como mucho 1 m la loma de terreno pegada a la roca

    def _d_pista(self, x, y, cand):
        """(distancia al borde del asfalto, cota de la pista) de la muestra mas cercana de cand."""
        best, zq = 1e9, None
        for (qx, qy, qz, w2) in cand:
            d = math.hypot(x - qx, y - qy) - w2
            if d < best:
                best, zq = d, qz
        return best, zq

    def _preparar_relleno(self):
        """v2 (G2-05 / G2-02 SO): {columna: (r_lim, z_f)}: bajo la repisa mas baja de la columna la roca llena
        hasta r_lim a la cota z_f (arcen de roca), donde entre la roca y lo que hay delante el terreno hace una V:
          * junto a la pista (rotonda Loews: el terreno congelado cae al 400 % y deja una grieta de 25 m): la
            roca llena la banda de 5 a 22 m del borde del asfalto que toca (hasta 5 m del borde, poco mas alla del
            punto mas cercano, o hasta donde el terreno recupera la cota) a z_f = min(repisa - 1.1, pista - 1.0);
          * foso cerrado de tierra lejos de la pista (v3 N3: barranco en V de 35-45 m entre el arcen N del penon y
            la ladera del promontorio; el terreno vuelve a subir a la cota del arcen a < 40 m): la roca llena el foso
            hasta el borde mas bajo de los dos (- 0.3): el de dentro es el arcen de la repisa (cota - 1.1) o la loma
            de terreno pegada a la roca si la hay (+ 1 m), el de fuera la ladera; solo fosos de > 8 m; cota y largo
            alisados entre columnas (un arcen liso, sin tablones radiales) (params relleno_fosos, por defecto True
            desde v3; la v2 lo tenia apagado por la rampa de la ranura SO, que el terreno ya no tiene);
          * foso de agua al pie (mar entre el pie y la costa a < 15 m): orilla de rocas a z_mar + 0.8 (siempre).
        Solo donde hace falta (el terreno baja > 3 m de z_f); sin puntas (r_lim <= la vecina mas larga + 4 m).
        Debajo del arcen la cara baja en talud (~70 grados) con el relieve de la roca (_perfil.nat)."""
        self.relleno = {}
        M = self.M
        pista = self.pista
        fosos = bool(self.params.get('relleno_fosos', True))
        res = {}
        ctx_foso = {}
        for i in range(M):
            cs = self.cruces[i]
            c_low = min(cs, key=lambda c: c['z']) if cs else None
            r0 = (c_low['R_out'] + 0.3) if c_low is not None else self.R_top[i] + 0.3
            zb = (c_low['z'] if c_low is not None else self.z_top) - 0.6
            if c_low is not None and c_low['kind'] in ('cala', 'salida'):
                continue
            ux, uy = math.cos(self.phi[i]), math.sin(self.phi[i])
            cand = []
            for q in pista:
                px, py = q[0] - self.cx, q[1] - self.cy
                t_ = px * ux + py * uy
                if r0 - 30.0 < t_ < r0 + 75.0 and abs(-px * uy + py * ux) < 60.0:
                    cand.append(q)
            hecho = False
            if cand:
                # banda de la pista: de D_RELLENO (6 m) a D_MAX_RELLENO (22 m) del borde del asfalto. El rayo
                # debe entrar en la banda a < 10 m de la roca; el arcen sigue mientras el rayo siga en ella, hasta
                # 6 m del borde o hasta donde el terreno recupera la cota del arcen
                rr = [r0 + 0.5 * k for k in range(int(55.0 / 0.5) + 1)]
                dz = [self._d_pista(*self.xy(i, r), cand) for r in rr]
                k0 = next((k for k in range(len(rr)) if rr[k] <= r0 + 10.0 and dz[k][0] <= self.D_MAX_RELLENO), None)
                if k0 is not None and dz[k0][0] > self.D_RELLENO:
                    k_c = min(range(len(rr)), key=lambda k: dz[k][0])          # punto mas cercano a la pista
                    z_f = min(zb - 0.5, dz[k_c][1] - 1.0)
                    k1 = k0
                    d_min = dz[k0][0]
                    for k in range(k0, len(rr)):
                        if dz[k][0] <= self.D_RELLENO or dz[k][0] > self.D_MAX_RELLENO or rr[k] - r0 > self.L_RELLENO:
                            break
                        if rr[k] > r0 + 2.0 and self.t(i, rr[k]) >= z_f - 0.5:
                            break
                        if dz[k][0] > d_min + 6.0:          # pasado el punto mas cercano: ya no esta entre roca y pista
                            break
                        d_min = min(d_min, dz[k][0])
                        k1 = k
                    r_lim = rr[k1]
                    t_min = min(self.t(i, r) for r in rr if r <= r_lim)
                    if t_min < z_f - 3.0 and r_lim > r0 + 1.0:
                        res[i] = (r_lim, z_f, 'pista')
                if k0 is not None:
                    hecho = True
            if hecho:
                continue
            # foso de AGUA al pie (celdas de mar entre el pie de la roca y la tierra, < 15 m): plataforma de roca a
            # z_mar + 0.8 hasta la tierra (orilla de rocas, sin canal de agua cerrado)
            r_pie = self.F(i, self.z_mar)
            r_t = None
            # solo columnas de mar (en las de tierra el nucleo del penon es mar forzado bajo la roca)
            for dphi_ in ((-0.5, 0.0, 0.5) if (self.terreno_fn is not None and not self.tierra[i]) else ()):
                r, agua = r_pie, False
                while r < r_pie + 15.0:
                    tz = self.terreno_fn(*self.xy_ang(self.phi[i] + dphi_ * self.dphi, r))
                    if tz <= self.z_mar + 0.3:
                        agua = True
                    elif agua and tz > self.z_mar + 1.0:
                        r_t = r if r_t is None else max(r_t, r)
                        break
                    r += 0.5
            if r_t is not None and r_t - r_pie > 1.0:
                res[i] = (r_t + 8.0, min(self.z_mar + 0.8, zb - 0.5), 'agua')   # +8: bajo la ladera de la costa
                continue
            if not self.tierra[i] or not fosos:
                continue
            ctx_foso[i] = (r0, zb - 0.5, cand)
            f_ = self._foso_tierra(i, r0, zb - 0.5, cand)
            if f_ is not None:
                res[i] = f_
        # v3 (N3): en los extremos de un foso hondo el arcen sigue por las columnas vecinas (a la misma cota y FOSO_DR_COL m
        # mas corto por columna) mientras alli quede una hondonada de > FOSO_HONDO_VECINA m bajo el arcen y su final siga
        # bajo la ladera: sin esto el arcen acababa en una pared de 5-8 m sobre una hondonada verde
        for i0 in sorted(i for i, v in res.items() if v[2] == 'foso'):
            for paso in (1, -1):
                j, (rl, zf, _t) = i0, res[i0]
                for _ in range(6):
                    j = (j + paso) % M
                    if j in res or j not in ctx_foso:
                        break
                    r0_j, zr_j, cand_j = ctx_foso[j]
                    rl -= self.FOSO_DR_COL
                    zf = min(zf, zr_j - 0.3)
                    r_s = max(r0_j, self.F(j, zf - 6.0))     # por dentro de r_s el suelo es la propia roca
                    if rl < r_s + 2.0 or self.t(j, rl) < zf - 1.0:
                        break
                    perf_ = [self.t(j, r_s + 0.5 * k) for k in range(int((rl - r_s) / 0.5) + 1)]
                    k_h = next((k for k, tz in enumerate(perf_) if tz < zf - self.FOSO_HONDO_VECINA), None)
                    # hondonada CERRADA: antes de ella el terreno vuelve a la cota del arcen (si no, es una ladera que
                    # sube desde el pie de la roca y no se tapa con roca)
                    if k_h is None or max(perf_[:k_h] or [-1e9]) < zf - 1.0:
                        break
                    if cand_j and min(self._d_pista(*self.xy(j, rq), cand_j)[0] for rq in (r_s, (r_s + rl) / 2.0, rl)) < self.D_RELLENO + 1.0:
                        break
                    res[j] = (rl, zf, 'foso')
        # v3 (N3): un solo arcen liso por foso, no tablones radiales: la cota es la envolvente inferior con FOSO_DZ_COL m
        # por columna (solo baja: el relleno nunca rebosa el borde mas bajo) y el largo la envolvente superior con
        # FOSO_DR_COL m por columna, solo si el final queda bajo la ladera (terreno >= z_f - 1) y lejos de la pista
        fs0 = {i: v for i, v in res.items() if v[2] == 'foso'}
        fs_ = {}
        for i, (rl, zf, _t) in fs0.items():
            vec_ = [(j, fs0[j]) for j in ((i + k) % M for k in range(-12, 13)) if j in fs0 and j != i]
            zf = min([zf] + [v[1] + self.FOSO_DZ_COL * abs(self.dcol(i, j)) for (j, v) in vec_])
            r_n = max([rl] + [v[0] - self.FOSO_DR_COL * abs(self.dcol(i, j)) for (j, v) in vec_])
            if r_n > rl + 0.1:
                ok_ = all(self.t(i, rl + 0.5 * k) >= zf - 1.0 for k in range(1, int((r_n - rl) / 0.5) + 1))
                if ok_ and self.pista:
                    ok_ = self._d_pista(*self.xy(i, r_n), self.pista)[0] >= self.D_RELLENO + 1.0
                rl = r_n if ok_ else rl
            fs_[i] = (rl, zf, 'foso')
        res.update(fs_)
        for i, (rl, zf, tipo) in res.items():
            # sin puntas: una columna no pasa en mas de 4 m a la mas larga de sus vecinas; sueltas fuera (salvo la
            # orilla de rocas a ras del agua, que se extiende a las dos vecinas: el charco suele ocupar 1-2 columnas)
            vec = [res[j][0] for j in ((i - 1) % M, (i + 1) % M) if j in res and res[j][2] == tipo]
            if tipo == 'agua':
                for j in ((i - 1) % M, i, (i + 1) % M):
                    if j == i or j not in res:
                        prev = self.relleno.get(j)
                        self.relleno[j] = (max(rl, prev[0]) if prev else rl, zf, tipo)
            elif vec:
                self.relleno[i] = (min(rl, max(vec) + 4.0), zf, tipo)
        self.n_relleno = (sum(1 for v in self.relleno.values() if v[2] == 'pista'),
                          sum(1 for v in self.relleno.values() if v[2] != 'pista'))
        self.n_foso_tierra = sum(1 for v in self.relleno.values() if v[2] == 'foso')

    def _foso_tierra(self, i, r0, z_ref, cand):
        """v3 (N3): (r_lim, z_f, 'foso') si en la columna de tierra i hay un FOSO cerrado entre la roca y la ladera de
        fuera, o None. z_ref = cota del arcen bajo la repisa mas baja (repisa - 1.1), r0 = su borde de fuera.
          * el foso empieza (r_b) donde el terreno baja de z_ref - 6, mirando desde la cara de la roca a esa cota
            (r_s = F(z_ref - 6): por dentro el terreno es el nucleo bajo la roca y no cuenta);
          * se cierra (r_c) donde el terreno vuelve a z_ref - 1 a < FOSO_ANCHO m del fondo (si no, es una ladera
            abierta que baja al mar o al valle: no se toca);
          * cota del arcen = borde mas bajo - 0.3: min(z_ref, ladera en r_c) y, si entre la roca y el foso hay una
            loma de terreno, tampoco mas de FOSO_SOBRE_LOMA m por encima de ella (no se tapa hierba buena con roca);
          * solo si el fondo queda > FOSO_HONDO m bajo el arcen y el relleno no se acerca a la pista (D_RELLENO + 1).
        El relleno llega 2 m bajo la ladera de fuera (r_c + 2) y por debajo baja en talud (_perfil.nat)."""
        r_s = max(r0, self.F(i, z_ref - 6.0))
        r, r_b, loma = r_s, None, None
        while r < r_s + 40.0:
            tz = self.t(i, r)
            if tz < z_ref - 6.0:
                r_b = r
                break
            loma = tz if loma is None else max(loma, tz)
            r += 1.0
        if r_b is None:
            return None
        r, r_c, fondo = r_b, None, 1e9
        while r < r_b + self.FOSO_ANCHO:
            tz = self.t(i, r)
            if tz >= z_ref - 1.0:
                r_c = r
                break
            fondo = min(fondo, tz)
            r += 1.0
        if r_c is None or r_c + 2.0 - r0 > self.FOSO_LARGO:
            return None
        nivel = min(z_ref, self.t(i, r_c))
        if loma is not None:
            nivel = min(nivel, loma + self.FOSO_SOBRE_LOMA)
        z_f = nivel - 0.3
        if fondo > z_f - self.FOSO_HONDO:
            return None
        if cand:
            rq = r0
            while rq <= r_c + 2.0:
                if self._d_pista(*self.xy(i, rq), cand)[0] < self.D_RELLENO + 1.0:
                    return None
                rq += 2.0
        return (r_c + 2.0, z_f, 'foso')

    # ------------------------------------------------------------------ perfil y malla de la roca
    def F_malla(self, i, z, cs):
        """Cara natural con textura (que se desvanece 4 m bajo cada repisa), empotrada en el
        terreno y con contrafuertes y tope. Devuelve (radio, banco)."""
        R = self.F_libre(i, z)
        t, k = self.textura(i, z)
        fade = 1.0
        for c in cs:
            if c['z'] - 4.0 < z <= c['z'] + 0.01:
                fade = min(fade, (c['z'] - z) / 4.0)
        R += t * fade
        e = self.empotrado(i, z)
        if e is not None and e > R:
            R = e
        # lado de tierra: bajo una repisa la roca baja en talud (1.2 m por m) hasta el terreno
        # cercano, en vez de un muro retranqueado sobre un rellano de roca a ras de la hierba
        for c in cs:
            dz = c['z'] - z
            if 0.3 < dz < 14.0 and c['kind'] not in ('salida', 'cala'):
                tal = c['R_out'] + 0.3 + 1.2 * dz
                if tal > R:
                    z_pie = self._pie_talud(i, c)
                    if z_pie is not None and z >= z_pie - 1.0:
                        R = tal
        return min(R, self.R_cap[i % self.M] + 1.5), k

    def _pie_talud(self, i, c):
        """Cota a la que el talud (1.2 m por m) que baja desde el borde exterior de la repisa c
        toca el terreno, si lo toca en menos de 14 m de desnivel (None si debajo hay mar o vacio)."""
        cache = self.__dict__.setdefault('_cache_pie', {})
        key = (i % self.M, id(c))
        if key not in cache:
            res = None
            dz = 0.5
            while dz < 14.0:
                if self.t(i, c['R_out'] + 0.3 + 1.2 * dz) >= c['z'] - dz - 0.2:
                    res = c['z'] - dz
                    break
                dz += 0.5
            cache[key] = res
        return cache[key]

    def _perfil(self, i):
        """Perfil (r, z, material, etiqueta) de la columna i de abajo arriba. Sobre una repisa
        la roca NUNCA vuelve a salir (r <= R_in de toda repisa inferior); si la repisa sale de
        la cara, muro (bastion) hasta encontrar la roca. Etiquetas ('o'|'i', leg) = anclas de
        la cremallera entre columnas; 'labio' = cornisa de estrato."""
        cs = sorted(self.cruces[i], key=lambda c: (c['z'], -c.get('orden', 0)))
        rel = self.relleno.get(i % self.M)

        def nat(z):
            R, k = self.F_malla(i, z, cs)
            if rel is not None and z <= rel[1]:
                # v2: arcen de roca que llena la grieta / el foso: arriba llano a z_f hasta r_lim (-0.8 m +- relieve);
                # debajo cara natural en talud (~70 grados) con el relieve de la roca, no un muro vertical
                t_ = self.textura(i, z)[0]
                R = max(R, rel[0] - 0.8 + 0.4 * t_ + min(6.0, 0.36 * (rel[1] - z)))
            for c in cs:
                if c['z'] < z - 0.005:
                    R = min(R, c['R_in'])
            return R, k

        def mat_nat(z, k):
            if z < self.z_mar - 0.5:
                return 'roca_oscura'
            return ('roca', 'roca_clara', 'roca', 'roca_oscura')[k % 4]
        alturas = [(self.z_mar - 1.0, False), (self.z_mar + 0.6, False)]
        for k in range(len(self.bordes) - 1):
            b0, b1 = self.bordes[k] + self.fase[i], self.bordes[k + 1] + self.fase[i]
            for (zz, lab) in ((b0 + 0.4, False), ((b0 + b1) / 2.0, False), (b1 - 0.45, True)):
                if self.z_fondo + 0.5 < zz < self.z_top - 0.4:
                    alturas.append((zz, lab))
        if rel is not None:                                # borde nitido del arcen de relleno (llano) y talud
            alturas = [(zz, lab) for (zz, lab) in alturas if abs(zz - rel[1]) > 0.6]
            alturas += [(rel[1] - 0.02, False), (rel[1] + 0.35, False)]
            alturas += [(rel[1] - dz_, False) for dz_ in (1.2, 3.0, 5.5, 8.5, 12.0, 16.0, 21.0, 27.0)
                        if all(abs(rel[1] - dz_ - zz) > 0.8 for (zz, _l) in alturas)]
        alturas.sort()
        pts = [(nat(self.z_fondo)[0] + 2.0, self.z_fondo, 'roca_oscura', None)]
        z_prev = self.z_fondo
        arriba = False
        for c in cs:
            z = c['z']
            Rb = nat(z - 0.6)[0]
            bast = c['kind'] == 'cala' or Rb < c['R_out'] - 0.3
            zb = z - 0.6
            if c['kind'] == 'cala':
                zb = z_prev + 0.3
            elif bast:
                while zb - 0.5 > z_prev + 0.3 and nat(zb)[0] < c['R_out'] - 0.3:
                    zb -= 0.5
                if rel is not None and zb <= rel[1] + 0.3 < z - 0.6:
                    zb = rel[1] + 0.3                      # v2: el bastion arranca SOBRE el arcen de relleno
            zb = max(zb, z_prev + 0.2)
            for (zz, lab) in alturas:
                if z_prev + 0.25 < zz < zb - 0.25:
                    R, k = nat(zz)
                    pts.append((R, zz, mat_nat(zz, k), 'labio' if lab else None))
            R, k = nat(zb)
            # bajo la CALZADA el bastion es cara de roca con estratos y relieve suave (antes un muro de
            # fabrica liso de hasta 20 m: 'parking'); muelles, plataformas y salida siguen de fabrica
            roca_b = bast and c['kind'] == 'carretera'
            if bast:
                m_b = mat_nat(zb, k) if roca_b else 'muro'
                pts.append((min(R, c['R_out']), zb, m_b, None))
                pts.append((c['R_out'], zb + 0.05, m_b, None))
                if roca_b:
                    p_ = self.phi[i]
                    zz = zb + 2.5
                    while zz < z - 1.5:
                        j = max(-0.4, min(0.8, 1.1 * _ruido(math.cos(p_) * 22.0 + 5.0, math.sin(p_) * 22.0, zz * 0.17)))
                        pts.append((c['R_out'] + j, zz, mat_nat(zz, self.estrato(i, zz)[0]), None))
                        zz += 2.5
            else:
                # junto al terreno (empotrado) la roca llega bajo la repisa hasta la ladera: arcen
                # de roca a ras, sin cuneta entre el borde de la carretera y la hierba
                e_b = self.empotrado(i, zb)
                R_b = R if (e_b is not None and e_b > c['R_out'] + 0.3) else min(R, c['R_out'] + 0.3)
                pts.append((R_b, zb, mat_nat(zb, k), None))
            pts.append((c['R_out'], z - 0.25, 'muro' if (bast and not roca_b) else 'roca', None))
            if z >= self.z_top - 0.02:                     # entrada a la meseta: la repisa es la meseta
                pts.append((c['R_out'], self.z_top, 'plaza', ('o', c['leg'])))
                arriba = True
                break
            pts.append((c['R_out'], z, 'repisa', ('o', c['leg'])))
            pts.append((c['R_in'], z, 'roca', ('i', c['leg'])))
            z_prev = z
        if not arriba:
            for (zz, lab) in alturas:
                if z_prev + 0.25 < zz < self.z_top - 0.3:
                    R, k = nat(zz)
                    pts.append((R, zz, mat_nat(zz, k), 'labio' if lab else None))
            R_t = min([self.R_top[i]] + [c['R_in'] for c in cs])
            pts.append((R_t, self.z_top, 'plaza', 'top'))
        self.R_top_eff[i] = pts[-1][0]
        return pts

    def _cremallera(self, mr, A, B, a0, a1, b0, b1):
        """Triangula la franja entre las columnas A y B de (a0, b0) a (a1, b1) por cota."""
        a, b = a0, b0
        while a < a1 or b < b1:
            if b == b1:
                av = True
            elif a == a1:
                av = False
            else:
                za, zb = A[a + 1][1], B[b + 1][1]
                av = (za < zb) if abs(za - zb) > 0.02 else (A[a][1] <= B[b][1])
            if av:
                mr.cara((A[a][0], B[b][0], A[a + 1][0]), A[a][2])
                a += 1
            else:
                mr.cara((A[a][0], B[b][0], B[b + 1][0]), B[b][2])
                b += 1

    def malla_roca(self, parent, raiz):
        M = self.M
        mr = _Malla('PENON_roca', ('roca', 'roca_clara', 'roca_oscura', 'repisa', 'muro', 'plaza'))
        self.R_top_eff = [0.0] * M
        self._cache_pie = {}
        self._preparar_relleno()
        cols = []
        self.labios = []
        for i in range(M):
            col = []
            for (r, z, mat, tag) in self._perfil(i):
                x, y = self.xy(i, r)
                col.append((mr.vert((x, y, z)), z, mat, tag, r))
                if tag == 'labio':
                    self.labios.append((x, y, z, r, i))
            cols.append(col)
        for i in range(M):
            A, B = cols[i], cols[(i + 1) % M]
            ta = {p[3]: k for k, p in enumerate(A) if isinstance(p[3], tuple)}
            tb = {p[3]: k for k, p in enumerate(B) if isinstance(p[3], tuple)}
            pares = [(0, 0)]
            for (ka, kb) in sorted((ta[t], tb[t]) for t in ta if t in tb):
                if ka > pares[-1][0] and kb > pares[-1][1] and ka < len(A) - 1 and kb < len(B) - 1:
                    pares.append((ka, kb))
            pares.append((len(A) - 1, len(B) - 1))
            for (a0, b0), (a1, b1) in zip(pares, pares[1:]):
                self._cremallera(mr, A, B, a0, a1, b0, b1)
        c_inf = mr.vert((self.cx, self.cy, self.z_fondo))
        c_sup = mr.vert((self.cx, self.cy, self.z_top))
        for i in range(M):
            j = (i + 1) % M
            mr.cara((c_inf, cols[j][0][0], cols[i][0][0]), 'roca_oscura')
            mr.cara((c_sup, cols[i][-1][0], cols[j][-1][0]), 'plaza')
        self.roca_v, self.roca_f = list(mr.v), list(mr.f)
        self.tris_roca = mr.tris()
        self.roca = mr.objeto(parent, raiz) if bpy is not None else None
        return self.roca

    # ------------------------------------------------------------------ ejes de la carretera
    def _lane(self, c, lado=None):
        x, y = self.xy(c['i'], self.r_eje(c, lado))
        return (x, y, c['z'])

    def _lazo(self, h):
        """Semicirculo del eje en la horquilla h: del carril interior (A, llega en el sentido
        h['s']) al exterior (B), abombado hacia h['s'] sobre la plataforma."""
        pl = h['plat'][0]
        r_a, r_b = pl['R_in'] + 3.1, pl['R_out'] - 3.1
        phi = self.phi[h['i']]
        ur = (math.cos(phi), math.sin(phi))
        ut = (-math.sin(phi) * h['s'], math.cos(phi) * h['s'])
        r_m, rho = (r_a + r_b) / 2.0, (r_b - r_a) / 2.0
        cxh, cyh = self.cx + r_m * ur[0], self.cy + r_m * ur[1]
        n = max(12, int(math.pi * rho / 1.4))
        out = []
        for k in range(1, n):
            th = math.pi * k / n
            out.append((cxh + rho * (-math.cos(th) * ur[0] + math.sin(th) * ut[0]),
                        cyh + rho * (-math.cos(th) * ur[1] + math.sin(th) * ut[1]), h['z']))
        h['centro'] = (cxh, cyh)
        h['rho'] = rho
        return out

    def _cintas(self):
        """Ejes (x, y, z): [subida (meseta -> plataforma de entrada), bajada (entrada -> cala)]."""
        M = self.M
        ent = {c['i']: c for c in self.cadenas['ent']}
        cols_ent = [(self.i_ent + k) % M for k in range(-self.n_ent, self.n_ent + 1)]
        lado_sub = 'in' if self.s_sub == self.s_baj else 'out'
        # --- subida: giro hacia dentro sobre la meseta, rampa, plataforma hasta la columna de entrada
        sub_c = self.cadenas.get('sub', [])
        sub = []
        if sub_c:
            last = sub_c[-1]
            phi_l = self.phi[last['i']]
            r_l = self.r_eje(last)
            rr = 9.0
            # tramo recto de 4 m hacia el centro de la meseta y cuarto de giro; muestras cada ~2 m
            # (antes el primer punto saltaba 4 m de golpe y contaba como quiebro)
            giro = [(rr, rr + e) for e in (4.0, 2.0)]
            for k in range(7, 0, -1):
                th = (math.pi / 2.0) * k / 7.0
                giro.append((rr * math.sin(th), rr * (1.0 - math.cos(th))))
            for (t_k, n_k) in giro:
                sub.append(self.xy_ang(phi_l + self.s_sub * t_k / r_l, r_l - n_k) + (self.z_top,))
            sub += [self._lane(c) for c in reversed(sub_c)]
        lados = [i for i in cols_ent if ((i - self.i_ent) * self.s_sub) % M <= self.n_ent]
        lados.sort(key=lambda i: -(((i - self.i_ent) * self.s_sub) % M))
        sub += [self._lane(ent[i], lado_sub) for i in lados]
        # --- bajada
        lados = [i for i in cols_ent if ((i - self.i_ent) * self.s_baj) % M <= self.n_ent]
        lados.sort(key=lambda i: ((i - self.i_ent) * self.s_baj) % M)
        baj = [self._lane(ent[i], 'out') for i in lados]
        for n, (leg, _s) in enumerate(self.orden):
            baj += [self._lane(c) for c in self.cadenas.get(leg, [])]
            if n < len(self.horquillas):
                h = self.horquillas[n]
                pl = {c['i']: c for c in h['plat']}
                atras = h['cols'][:h['n_b'] + 1]
                baj += [self._lane(pl[i], 'in') for i in atras]
                baj += self._lazo(h)
                baj += [self._lane(pl[i], 'out') for i in reversed(atras)]
        if self.espigon is not None:
            e = self.espigon
            baj += list(e['pts'][1:])
            ox, oy = e['o']
            for d in (4.0, 8.0, 12.0):
                baj.append((ox + e['u'][0] * d, oy + e['u'][1] * d, self.z_cala))
        elif self.cala:
            baj += [self._lane(c, 'in') for c in self.cala[:4]]
        out = []
        for pts in (sub, baj):
            lim = []
            for p in pts:
                if not lim or math.hypot(p[0] - lim[-1][0], p[1] - lim[-1][1]) > 0.3:
                    lim.append(p)
            out.append(lim)
        return out

    def _lr(self, pts, k, half=2.5):
        """Puntos izquierdo y derecho del eje en la muestra k (tangente centrada)."""
        a = pts[max(0, k - 1)]
        b = pts[min(len(pts) - 1, k + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / l, tx / l
        p = pts[k]
        return ((p[0] + nx * half, p[1] + ny * half), (p[0] - nx * half, p[1] - ny * half))

    def malla_carretera(self, parent, raiz):
        mc = _Malla('PENON_carretera', ('carretera', 'borde'))
        self.cintas = self._cintas()
        self.muestras_xyz = []
        self.longitud = 0.0
        for pts in self.cintas:
            lr = [self._lr(pts, k) for k in range(len(pts))]
            for k in range(len(pts) - 1):
                (la, ra), (lb, rb) = lr[k], lr[k + 1]
                za, zb = pts[k][2] + 0.06, pts[k + 1][2] + 0.06
                mc.quad_hacia((la[0], la[1], za), (ra[0], ra[1], za), (rb[0], rb[1], zb), (lb[0], lb[1], zb), (0, 0, 1), 'carretera')
                for (ea, eb) in ((la, lb), (ra, rb)):
                    nax, nay = (pts[k][0] - ea[0]) / 2.5 * 0.22, (pts[k][1] - ea[1]) / 2.5 * 0.22
                    nbx, nby = (pts[k + 1][0] - eb[0]) / 2.5 * 0.22, (pts[k + 1][1] - eb[1]) / 2.5 * 0.22
                    mc.quad_hacia((ea[0], ea[1], za + 0.012), (ea[0] + nax, ea[1] + nay, za + 0.012),
                                  (eb[0] + nbx, eb[1] + nby, zb + 0.012), (eb[0], eb[1], zb + 0.012), (0, 0, 1), 'borde')
                self.longitud += math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
            for p in pts:
                if not self.muestras_xyz or math.hypot(p[0] - self.muestras_xyz[-1][0], p[1] - self.muestras_xyz[-1][1]) > 0.05:
                    self.muestras_xyz.append((p[0], p[1], p[2]))
        self.carretera = mc.objeto(parent, raiz)

    # ------------------------------------------------------------------ espigon y muelle
    def malla_espigon(self, parent, raiz):
        """Dique con calzada (7.2 m, muros de mamposteria hasta 3 m bajo el agua, pretil a los
        dos lados) desde la roca hasta el muelle (26 x 62 m, bolardos en el borde)."""
        self.espigon_ob = None
        e = self.espigon
        if e is None:
            return None
        me = _Malla('PENON_espigon', ('muro', 'muelle', 'borde', 'bolardo'))
        pts = e['pts']
        zf = self.z_mar - 3.0
        lr = [self._lr(pts, k, 3.6) for k in range(len(pts))]
        for k in range(len(pts) - 1):
            (la, ra), (lb, rb) = lr[k], lr[k + 1]
            za, zb = pts[k][2], pts[k + 1][2]
            me.quad_hacia((la[0], la[1], za), (ra[0], ra[1], za), (rb[0], rb[1], zb), (lb[0], lb[1], zb), (0, 0, 1), 'muelle')
            for (ea, eb) in ((la, lb), (ra, rb)):
                fuera = (ea[0] - pts[k][0], ea[1] - pts[k][1], 0.0)
                me.quad_hacia((ea[0], ea[1], zf), (eb[0], eb[1], zf), (eb[0], eb[1], zb), (ea[0], ea[1], za), fuera, 'muro')
                if k >= 2:      # pretil (los primeros 5 m salen de la repisa de la roca)
                    ia = (ea[0] - fuera[0] / 3.6 * 0.45, ea[1] - fuera[1] / 3.6 * 0.45)
                    ib = (eb[0] - fuera[0] / 3.6 * 0.45, eb[1] - fuera[1] / 3.6 * 0.45)
                    me.quad_hacia((ea[0], ea[1], za), (eb[0], eb[1], zb), (eb[0], eb[1], zb + 0.9), (ea[0], ea[1], za + 0.9), fuera, 'muro')
                    me.quad_hacia((ia[0], ia[1], za), (ib[0], ib[1], zb), (ib[0], ib[1], zb + 0.9), (ia[0], ia[1], za + 0.9),
                                  (-fuera[0], -fuera[1], 0.0), 'muro')
                    me.quad_hacia((ea[0], ea[1], za + 0.9), (eb[0], eb[1], zb + 0.9), (ib[0], ib[1], zb + 0.9), (ia[0], ia[1], za + 0.9), (0, 0, 1), 'borde')
        ux, uy = e['u']
        vx, vy = e['v']
        ox, oy = e['o']
        L, A = e['L_q'], e['A_q'] / 2.0
        z = self.z_cala
        esq = [(ox + ux * u + vx * v, oy + uy * u + vy * v) for (u, v) in ((0.0, -A), (L, -A), (L, A), (0.0, A))]
        me.quad_hacia(*[(p[0], p[1], z) for p in esq], (0, 0, 1), 'muelle')
        for k in range(4):
            p, q = esq[k], esq[(k + 1) % 4]
            mx, my = (p[0] + q[0]) / 2.0 - (ox + ux * L / 2.0), (p[1] + q[1]) / 2.0 - (oy + uy * L / 2.0)
            me.quad_hacia((p[0], p[1], zf), (q[0], q[1], zf), (q[0], q[1], z), (p[0], p[1], z), (mx, my, 0.0), 'muro')
            me.quad_hacia((p[0], p[1], z), (q[0], q[1], z), (q[0], q[1], z + 0.06), (p[0], p[1], z + 0.06), (mx, my, 0.0), 'borde')
        self.bolardos = []
        for u in range(4, int(L) - 1, 6):
            for v in (-A + 0.6, A - 0.6):
                x, y = ox + ux * u + vx * v, oy + uy * u + vy * v
                me.caja((x, y, z), 0.35, 0.35, 0.55, 'bolardo')
                self.bolardos.append((x, y, z))
        self.espigon_ob = me.objeto(parent, raiz)
        self.espigon_v, self.espigon_f = list(me.v), list(me.f)
        return self.espigon_ob

    # ------------------------------------------------------------------ apoyos (ray-cast)
    def _bvh(self):
        v, f = list(self.roca_v), list(self.roca_f)
        if self.espigon is not None:
            n = len(v)
            v += self.espigon_v
            f += [tuple(i + n for i in fa) for fa in self.espigon_f]
        self.bvh = BVHTree.FromPolygons(v, f, all_triangles=False)
        from mathutils.kdtree import KDTree
        self.kd_road = KDTree(len(self.muestras_xyz))
        for k, m in enumerate(self.muestras_xyz):
            self.kd_road.insert(Vector((m[0], m[1], 0.0)), k)
        self.kd_road.balance()

    def z_roca(self, x, y, z_desde):
        hit = self.bvh.ray_cast(Vector((x, y, z_desde)), Vector((0.0, 0.0, -1.0)), 800.0)
        return None if hit[0] is None else hit[0].z

    def roca_encima(self, x, y, z, alto=60.0):
        return self.bvh.ray_cast(Vector((x, y, z)), Vector((0.0, 0.0, 1.0)), alto)[0] is not None

    def d_calzada(self, x, y, z, dz_max=4.0):
        """Distancia en planta al eje de carretera mas cercano a una cota parecida."""
        d_min = 1e9
        for (_co, idx, d) in self.kd_road.find_n(Vector((x, y, 0.0)), 8):
            if abs(self.muestras_xyz[idx][2] - z) < dz_max:
                d_min = min(d_min, d)
        return d_min

    def caida(self, x, y, z):
        """Desnivel entre la cota z y lo que hay debajo en (x, y): roca, terreno o mar."""
        zr = self.z_roca(x, y, z + 0.5)
        zt = self.terreno_fn(x, y) if self.terreno_fn else self.z_mar - 4.0
        return z - max(zr if zr is not None else -1e9, zt, self.z_mar)

    def _apoyo_ok(self, pts_xy, z, alto, tol=0.35):
        for (x, y) in pts_xy:
            zr = self.z_roca(x, y, z + alto + 1.0)
            if zr is None or abs(zr - z) > tol or self.roca_encima(x, y, z + 0.3, alto + 2.0):
                return False
        return True

    # ------------------------------------------------------------------ parapetos y farolas
    def _segmentos_parapeto(self):
        """Pares (a, b) de cruces consecutivos (columnas vecinas) por el borde exterior de cada
        repisa, mas los empalmes entre tramos; sin el hueco de la entrada (espolon) ni el
        muelle; el ultimo tramo antes del espigon queda abierto."""
        M = self.M
        hueco = set((self.i_ent + k) % M for k in range(-2, 3))
        segs = []
        for leg, cs in self.cadenas.items():
            if leg in ('cala', 'tmp', 'esp'):
                continue
            orden = cs
            if leg == 'ent':
                orden = sorted(cs, key=lambda c: (c['i'] - self.i_ent + M // 2) % M)
            for a, b in zip(orden, orden[1:]):
                if ((b['i'] - a['i']) % M) in (1, M - 1):
                    segs.append((a, b))
        ent = sorted(self.cadenas['ent'], key=lambda c: (c['i'] - self.i_ent + M // 2) % M)
        extremo = {1: ent[-1], -1: ent[0]}
        enl = []
        if self.cadenas.get('sub'):
            enl.append((extremo[self.s_sub], self.cadenas['sub'][0]))
        prev = extremo[self.s_baj]
        for n, (leg, _s) in enumerate(self.orden):
            cs = self.cadenas.get(leg, [])
            if cs:
                enl.append((prev, cs[0]))
            if n < len(self.horquillas):
                h = self.horquillas[n]
                if cs:
                    enl.append((cs[-1], h['plat'][0]))
                prev = h['plat'][0]
        for (a, b) in enl:
            if abs(a['R_out'] - b['R_out']) < 4.0 and ((b['i'] - a['i']) % M) in (1, M - 1):
                segs.append((a, b))
        abiertos = set()
        if self.espigon is not None and self.orden:
            ult = self.cadenas.get(self.orden[-1][0], [])
            abiertos = set(id(c) for c in ult[-3:])
        return [(a, b) for (a, b) in segs if not (a['leg'] == 'ent' and (a['i'] in hueco or b['i'] in hueco))
                and id(a) not in abiertos and id(b) not in abiertos]

    def malla_parapeto(self, parent, raiz):
        mp = _Malla('PENON_parapeto', ('muro', 'borde'))
        mf = _Malla('PENON_farolas', ('poste', 'farol'))
        self.farolas = []
        acum = {}
        self.n_parapeto = 0
        for (a, b) in self._segmentos_parapeto():
            pm = self.xy_ang(self.phi[a['i']] + 0.5 * ((b['i'] - a['i'] + self.M // 2) % self.M - self.M // 2) * self.dphi,
                             (a['R_out'] + b['R_out']) / 2.0 + 0.8)
            if self.caida(pm[0], pm[1], (a['z'] + b['z']) / 2.0) < 0.6:
                acum[a['leg']] = 0.0
                continue
            self._parapeto(mp, a, b)
            self.n_parapeto += 1
            if a.get('fijo') or a['kind'] == 'plaza_entrada':
                continue
            pa, pb = self.xy(a['i'], a['R_out']), self.xy(b['i'], b['R_out'])
            acum[a['leg']] = acum.get(a['leg'], -6.0) + math.hypot(pb[0] - pa[0], pb[1] - pa[1])
            if acum[a['leg']] >= 16.0:
                acum[a['leg']] = 0.0
                self._farola(mf, a)
        for h in self.horquillas:          # pretil de cierre en el extremo de cada plataforma
            c = h['plat'][-1]
            phi = self.phi[c['i']]
            p_ext = self.xy_ang(phi + h['s'] * 0.6 * self.dphi, (c['R_in'] + c['R_out']) / 2.0 + 4.0)
            if self.caida(p_ext[0], p_ext[1], c['z']) >= 0.6:
                self._pretil_radial(mp, phi, c['R_in'] + 7.0, c['R_out'] - 0.1, c['z'], h['s'])
        self.bolardos = getattr(self, 'bolardos', [])
        if self.espigon is None and self.cala and self.fin == 'cala':
            # v2: bolardos en el borde del muelle de la cala de la roca (cada ~6 m; libre el arranque del pantalan)
            pc = self._pantalan_cala()
            acum = 6.0
            for k, c in enumerate(self.cala):
                acum += (c['R_out'] - 0.6) * self.dphi
                if acum < 6.0 or (pc is not None and abs(k - pc[0]) <= 1):
                    continue
                acum = 0.0
                x, y = self.xy(c['i'], c['R_out'] - 0.6)
                mp.caja((x, y, self.z_cala), 0.35, 0.35, 0.55, 'bolardo')
                self.bolardos.append((x, y, self.z_cala))
        self.parapeto = mp.objeto(parent, raiz)
        self.farolas_ob = mf.objeto(parent, raiz)

    def _parapeto(self, mp, a, b, h=0.95, grosor=0.45):
        za, zb = a['z'], b['z']
        o0, o1 = self.xy(a['i'], a['R_out'] - 0.1), self.xy(b['i'], b['R_out'] - 0.1)
        i0, i1 = self.xy(a['i'], a['R_out'] - 0.1 - grosor), self.xy(b['i'], b['R_out'] - 0.1 - grosor)
        fuera = (o0[0] - self.cx, o0[1] - self.cy, 0.0)
        dentro = (-fuera[0], -fuera[1], 0.0)
        mp.quad_hacia((o0[0], o0[1], za - 0.3), (o1[0], o1[1], zb - 0.3), (o1[0], o1[1], zb + h), (o0[0], o0[1], za + h), fuera, 'muro')
        mp.quad_hacia((i0[0], i0[1], za), (i1[0], i1[1], zb), (i1[0], i1[1], zb + h), (i0[0], i0[1], za + h), dentro, 'muro')
        e = 0.07
        o0e, o1e = self.xy(a['i'], a['R_out'] - 0.1 + e), self.xy(b['i'], b['R_out'] - 0.1 + e)
        i0e, i1e = self.xy(a['i'], a['R_out'] - 0.1 - grosor - e), self.xy(b['i'], b['R_out'] - 0.1 - grosor - e)
        mp.quad_hacia((o0e[0], o0e[1], za + h), (o1e[0], o1e[1], zb + h), (i1e[0], i1e[1], zb + h), (i0e[0], i0e[1], za + h), (0, 0, 1), 'borde')
        mp.quad_hacia((o0e[0], o0e[1], za + h - 0.12), (o1e[0], o1e[1], zb + h - 0.12), (o1e[0], o1e[1], zb + h), (o0e[0], o0e[1], za + h), fuera, 'borde')
        mp.quad_hacia((i0e[0], i0e[1], za + h - 0.12), (i1e[0], i1e[1], zb + h - 0.12), (i1e[0], i1e[1], zb + h), (i0e[0], i0e[1], za + h), dentro, 'borde')

    def _pretil_radial(self, mp, phi, r0, r1, z, s, h=0.95, grosor=0.45):
        """Pretil a lo largo del radio (cierre del extremo de una plataforma)."""
        a0, a1 = self.xy_ang(phi, r0), self.xy_ang(phi, r1)
        t = (-math.sin(phi) * s, math.cos(phi) * s)
        b0, b1 = (a0[0] - t[0] * grosor, a0[1] - t[1] * grosor), (a1[0] - t[0] * grosor, a1[1] - t[1] * grosor)
        mp.quad_hacia((a0[0], a0[1], z - 0.3), (a1[0], a1[1], z - 0.3), (a1[0], a1[1], z + h), (a0[0], a0[1], z + h), (t[0], t[1], 0.0), 'muro')
        mp.quad_hacia((b0[0], b0[1], z), (b1[0], b1[1], z), (b1[0], b1[1], z + h), (b0[0], b0[1], z + h), (-t[0], -t[1], 0.0), 'muro')
        mp.quad_hacia((a0[0], a0[1], z + h), (a1[0], a1[1], z + h), (b1[0], b1[1], z + h), (b0[0], b0[1], z + h), (0, 0, 1), 'borde')

    def _farola(self, mf, a):
        """Farola sobre la albardilla del parapeto (a 2.78 m del eje: fuera del asfalto)."""
        x, y = self.xy(a['i'], a['R_out'] - 0.325)
        z = a['z'] + 0.95
        mf.caja((x, y, z), 0.42, 0.42, 0.10, 'poste')
        mf.caja((x, y, z + 0.10), 0.15, 0.15, 3.3, 'poste')
        mf.caja((x, y, z + 3.40), 0.34, 0.34, 0.5, 'farol')
        mf.caja((x, y, z + 3.90), 0.48, 0.48, 0.12, 'poste')
        self.farolas.append((x, y, z))

    # ------------------------------------------------------------------ balaustrada y pavimentos
    def malla_balaustrada(self, parent, raiz):
        M = self.M
        mb = _Malla('PENON_balaustrada', ('balaustrada',))
        gap = set()
        for c in self.cadenas.get('sub', []):
            if c['kind'] == 'plaza_entrada':
                gap.update(((c['i'] + k) % M) for k in (-1, 0, 1))
        self.hueco_meseta = sorted(gap)
        z = self.z_top
        acum = 0.0
        for i in range(M):
            j = (i + 1) % M
            if i in gap or j in gap:
                continue
            r0, r1 = self.R_top_eff[i] - 0.45, self.R_top_eff[j] - 0.45
            o0, o1 = self.xy(i, r0), self.xy(j, r1)
            q0, q1 = self.xy(i, r0 - 0.4), self.xy(j, r1 - 0.4)
            fuera = (o0[0] - self.cx, o0[1] - self.cy, 0.0)
            dentro = (-fuera[0], -fuera[1], 0.0)
            for (za, zb_, top) in ((z - 0.2, z + 0.32, True), (z + 0.94, z + 1.06, True)):
                mb.quad_hacia((o0[0], o0[1], za), (o1[0], o1[1], za), (o1[0], o1[1], zb_), (o0[0], o0[1], zb_), fuera, 'balaustrada')
                mb.quad_hacia((q0[0], q0[1], max(za, z)), (q1[0], q1[1], max(za, z)), (q1[0], q1[1], zb_), (q0[0], q0[1], zb_), dentro, 'balaustrada')
                mb.quad_hacia((o0[0], o0[1], zb_), (o1[0], o1[1], zb_), (q1[0], q1[1], zb_), (q0[0], q0[1], zb_), (0, 0, 1), 'balaustrada')
            mb.quad_hacia((o0[0], o0[1], z + 0.94), (o1[0], o1[1], z + 0.94), (q1[0], q1[1], z + 0.94), (q0[0], q0[1], z + 0.94), (0, 0, -1), 'balaustrada')
            acum += math.hypot(o1[0] - o0[0], o1[1] - o0[1])
            n_b = int(acum / 1.4)
            if n_b >= 1:
                acum -= n_b * 1.4
                for k in range(n_b):
                    f = (k + 0.5) / n_b
                    x, y = self.xy_ang(self.phi[i] + self.dphi * f, r0 + (r1 - r0) * f - 0.2)
                    mb.caja((x, y, z + 0.32), 0.2, 0.2, 0.62, 'balaustrada', self.phi[i])
        self.balaustrada = mb.objeto(parent, raiz)

    def malla_pavimentos(self, parent, raiz):
        """Pavimento claro en plataformas (entrada, horquillas), muelle en la cala de la roca y
        paseo junto a la balaustrada de la meseta."""
        M = self.M
        mp = _Malla('PENON_plazas', ('plaza', 'muelle', 'plaza_dibujo'))
        for leg, cs in self.cadenas.items():
            if not (leg == 'ent' or leg.startswith('pl') or leg == 'cala'):
                continue
            por_i = {c['i']: c for c in cs}
            for c in cs:
                d = por_i.get((c['i'] + 1) % M)
                if d is None:
                    continue
                mat = 'muelle' if leg == 'cala' else 'plaza'
                A = self.xy(c['i'], c['R_in'] + 0.3) + (c['z'] + 0.04,)
                B = self.xy(c['i'], c['R_out'] - 0.3) + (c['z'] + 0.04,)
                C = self.xy(d['i'], d['R_out'] - 0.3) + (d['z'] + 0.04,)
                D = self.xy(d['i'], d['R_in'] + 0.3) + (d['z'] + 0.04,)
                mp.quad_hacia(A, B, C, D, (0, 0, 1), mat)
        gap = set(self.hueco_meseta)
        for i in range(M):
            j = (i + 1) % M
            if i in gap or j in gap:
                continue
            A = self.xy(i, self.R_top_eff[i] - 4.2) + (self.z_top + 0.03,)
            B = self.xy(i, self.R_top_eff[i] - 0.9) + (self.z_top + 0.03,)
            C = self.xy(j, self.R_top_eff[j] - 0.9) + (self.z_top + 0.03,)
            D = self.xy(j, self.R_top_eff[j] - 4.2) + (self.z_top + 0.03,)
            mp.quad_hacia(A, B, C, D, (0, 0, 1), 'plaza_dibujo')
        self.plazas_ob = mp.objeto(parent, raiz)

    # ------------------------------------------------------------------ casas de la cala
    def _clonar(self, ob, raiz, parent, loc, rot_z, escala=1.0):
        nb = ob.copy()
        parent.objects.link(nb)
        nb.parent = raiz
        nb.location = Vector(loc)
        nb.rotation_euler = (0.0, 0.0, rot_z)
        if escala != 1.0:
            nb.scale = (escala, escala, escala)
        return nb

    def _huella(self, x, y, rot, an, fo):
        ca, sa = math.cos(rot), math.sin(rot)
        return [(x + u * ca - v * sa, y + u * sa + v * ca)
                for u in (-an / 2.0 + 0.2, 0.0, an / 2.0 - 0.2) for v in (-fo + 0.3, -fo / 2.0, -0.3)]

    def casas(self, parent, raiz, casas_kit):
        """4-6 casas de pescadores en el muelle: en el lado del muelle que no da a la roca, con la
        fachada hacia el paseo y la roca (pivote en el centro de la fachada, fachada +Y local:
        rot_z = atan2(fy, fx) - pi/2), trasera a 1.2 m del borde. Cada casa se comprueba por
        ray-cast (9 puntos: apoyo y nada encima) y contra la calzada."""
        self.plazas_casas = []
        self.casas_malas = 0
        if casas_kit is None:
            return
        if self.espigon is None:
            if self.cala:
                self._casas_cala_roca(parent, raiz, casas_kit)
            return
        e = self.espigon
        ux, uy = e['u']
        vx, vy = e['v']
        ox, oy = e['o']
        lado = -e['lado_roca']
        A = e['A_q'] / 2.0
        variantes = [(3, 9.0, 8.0), (2, 8.0, 8.5), (3, 10.0, 8.0), (2, 9.0, 7.5), (3, 8.0, 8.0), (2, 10.0, 8.5)]
        fx, fy = -lado * vx, -lado * vy
        rot = math.atan2(fy, fx) - math.pi / 2.0
        lib = {}
        u = 15.0
        n = 0
        while n < 6:
            k = (n * 5 + self.seed) % len(variantes)
            pl, an, fo = variantes[k]
            if u + an > e['L_q'] - 3.0:
                break
            uc = u + an / 2.0
            vf = lado * (A - 1.2 - fo)
            x, y = ox + ux * uc + vx * vf, oy + uy * uc + vy * vf
            hu = self._huella(x, y, rot, an, fo)
            if not self._apoyo_ok(hu, self.z_cala, pl * 3.3 + 2.0) or min(self.d_calzada(px, py, self.z_cala) for (px, py) in hu) < 2.8:
                self.casas_malas += 1
                u += 3.0
                continue
            if k not in lib:
                ob = casas_kit.build_casa(parent, plantas=pl, ancho=an, fondo=fo, seed=self.seed * 3 + k)
                ob.name = 'PENON_casa_v%d' % k
                ob.parent = raiz
                ob.location = Vector((x, y, self.z_cala))
                ob.rotation_euler = (0.0, 0.0, rot)
                lib[k] = ob
            else:
                self._clonar(lib[k], raiz, parent, (x, y, self.z_cala), rot)
            self.plazas_casas.append({'x': x, 'y': y, 'z': self.z_cala, 'rot_z': rot, 'ancho': an, 'fondo': fo,
                                      'plantas': pl, 'tipo': 'cala'})
            n += 1
            u += an + 2.2

    # ------------------------------------------------------------------ cala al pie de la roca (v2)
    VARIANTES_CASA = ((3, 9.0, 8.0), (2, 8.0, 8.5), (3, 10.0, 8.0), (2, 9.0, 7.5), (3, 8.0, 8.0), (2, 10.0, 8.5))

    def _arco_cala(self, r_off):
        """Distancia de arco (m) de cada columna del muelle de la cala de la roca, medida a R_in + r_off."""
        q = self.cala
        acum = [0.0]
        for a, b in zip(q, q[1:]):
            acum.append(acum[-1] + (0.5 * (a['R_in'] + b['R_in']) + r_off) * self.dphi)
        return acum

    def _phi_cala(self, acum, u):
        """(angulo, indice k del muelle) a la distancia de arco u."""
        q = self.cala
        k = len(q) - 2
        for j in range(len(acum) - 1):
            if acum[j + 1] >= u:
                k = j
                break
        k = max(0, k)
        f = (u - acum[k]) / max(1e-6, acum[k + 1] - acum[k])
        return self.phi[q[k]['i']] + self.s_cala * f * self.dphi, k

    def _pantalan_cala(self):
        """Columna del muelle de la roca desde la que sale el pantalan (radial, hacia el mar): la primera, desde
        el 70 % del muelle hacia la llegada, con pantalan y lanchas en agua libre. (k, origen, u, v) o None."""
        if hasattr(self, '_pant_cala'):
            return self._pant_cala
        q = self.cala
        res = None
        orden = sorted(range(3, len(q) - 2), key=lambda k: abs(k - 0.7 * len(q)))
        for k in orden:
            c = q[k]
            p = self.phi[c['i']]
            ux, uy = math.cos(p), math.sin(p)
            vx, vy = -uy, ux
            ox, oy = self.xy(c['i'], c['R_out'] - 0.5)
            ok = all(self._fuera_de_roca(ox + ux * du + vx * dv, oy + uy * du + vy * dv, 2.5)
                     for du in (3.0, 10.0, 18.0, 26.0, 34.0) for dv in (-7.0, 0.0, 7.0))
            if ok:
                res = (k, (ox, oy), (ux, uy), (vx, vy))
                break
        self._pant_cala = res
        return res

    def _casas_cala_roca(self, parent, raiz, casas_kit):
        """Casas de pescadores en el muelle al pie de la roca: trasera a 1.2 m de la cara (nada encima: la roca
        nunca sale por encima de una repisa), fachada al mar (radial), paseo de >= 7 m delante; empiezan pasada la
        llegada de la carretera (carril interior de las 4 primeras columnas del muelle). Mismas comprobaciones de
        ray-cast y calzada que en el espigon."""
        q = self.cala
        acum = self._arco_cala(1.2)
        lib = {}
        u = acum[min(len(q) - 1, 4)] + 3.0          # la carretera llega por las 4 primeras columnas
        n = 0
        while n < 6:
            k = (n * 5 + self.seed) % len(self.VARIANTES_CASA)
            pl, an, fo = self.VARIANTES_CASA[k]
            if u + an > acum[-1] - 3.0:
                break
            _p0, k0 = self._phi_cala(acum, u)
            _p1, k1 = self._phi_cala(acum, u + an)
            phi_c, _kc = self._phi_cala(acum, u + an / 2.0)
            ks = [kk for kk in range(min(k0, k1), max(k0, k1) + 2) if kk < len(q)]
            R_back = max(q[kk]['R_in'] for kk in ks) + 1.2
            if R_back + fo > min(q[kk]['R_out'] for kk in ks) - 7.0:
                self.casas_malas += 1
                u += 3.0
                continue
            rot = phi_c - math.pi / 2.0                     # fachada (+Y local) hacia fuera (radial)
            x, y = self.xy_ang(phi_c, R_back + fo)
            hu = self._huella(x, y, rot, an, fo)
            if not self._apoyo_ok(hu, self.z_cala, pl * 3.3 + 2.0) or min(self.d_calzada(px, py, self.z_cala) for (px, py) in hu) < 2.8:
                self.casas_malas += 1
                u += 3.0
                continue
            if k not in lib:
                ob = casas_kit.build_casa(parent, plantas=pl, ancho=an, fondo=fo, seed=self.seed * 3 + k)
                ob.name = 'PENON_casa_v%d' % k
                ob.parent = raiz
                ob.location = Vector((x, y, self.z_cala))
                ob.rotation_euler = (0.0, 0.0, rot)
                lib[k] = ob
            else:
                self._clonar(lib[k], raiz, parent, (x, y, self.z_cala), rot)
            self.plazas_casas.append({'x': x, 'y': y, 'z': self.z_cala, 'rot_z': rot, 'ancho': an, 'fondo': fo,
                                      'plantas': pl, 'tipo': 'cala'})
            n += 1
            u += an + 1.4                             # hilera de casas de pescadores (casi pegadas)

    def _marina_cala_roca(self, parent, raiz, italiano_kit, yates_kit):
        """Cala al pie de la roca: fuente en el paseo, pantalan VIP radial desde el borde del muelle y 3 lanchas."""
        q = self.cala
        cm = q[len(q) // 2]
        self.cala_xyz = self.xy(cm['i'], 0.5 * (cm['R_in'] + cm['R_out'])) + (self.z_cala,)
        self.cala_huella = [self.xy(c['i'], c['R_in'] - 2.0) for c in q] + [self.xy(c['i'], c['R_out'] + 8.0) for c in reversed(q)]
        if italiano_kit is not None:
            try:
                f = italiano_kit.build_fuente(parent, seed=self.seed)
                f.parent = raiz
                x, y = self.xy(cm['i'], cm['R_out'] - 6.5)
                f.location = Vector((x, y, self.z_cala + 0.02))
                for ch in f.children_recursive:
                    ch.name = 'ITAL_penon_' + ch.name
            except Exception as ex:  # pragma: no cover
                self.avisos.append('fuente: %s' % ex)
        pc = self._pantalan_cala()
        if yates_kit is None or pc is None:
            if pc is None:
                self.avisos.append('cala de la roca: sin agua libre para el pantalan')
            return
        try:
            _k, (ox, oy), (ux, uy), (vx, vy) = pc
            h = math.atan2(uy, ux)
            pant = yates_kit.build_pantalan_vip(parent, largo=30.0, seed=self.seed, z_cubierta=0.9)
            pant.parent = raiz
            pant.location = Vector((ox, oy, self.z_mar))
            pant.rotation_euler = (0.0, 0.0, h)
            for k, (du, dv) in enumerate(((7.0, 4.6), (16.0, -4.6), (25.0, 4.6))):
                lan = yates_kit.build_lancha(parent, eslora=9.0, seed=self.seed + k)
                lan.parent = raiz
                lan.location = Vector((ox + ux * du + vx * dv, oy + uy * du + vy * dv, self.z_mar))
                lan.rotation_euler = (0.0, 0.0, h + (0.0 if k != 1 else math.pi))
                self.n_barcos += 1
        except Exception as ex:  # pragma: no cover
            self.avisos.append('marina: %s' % ex)

    # ------------------------------------------------------------------ vegetacion
    # v3 (N1): el ESPOLON (camino de 6 m de integrar_escena.zona_caminos, pista -> entrada) pasa por fuera de la roca, sobre
    # el arcen de roca de la entrada; la roca no lo ve, asi que se protege su eje y la boca de la entrada
    D_VEG_ESPOLON = 9.5   # arbol: tronco a >= 3 m (semiancho) + 6.5 m (copa de un pino de 12 m x 1.15) del eje
    D_MATA_ESPOLON = 4.5  # mata: >= 3 + 1.5 m
    R_VEG_ENTRADA = 14.0  # nada por fuera de la plataforma a < 14 m del punto de entrada (hueco del parapeto)
    D_VEG_PISTA = 8.0     # arbol: tronco a >= 8 m del borde del asfalto de la pista

    def _entrada_xy(self):
        """Punto de entrada (hueco del parapeto donde llega el espolon) = info['entrada'] y su radio."""
        c_e = next(c for c in self.cadenas['ent'] if c['i'] == self.i_ent)
        r_e = c_e['R_out'] - 0.3
        return self.xy(self.i_ent, r_e), r_e

    def _preparar_espolon(self):
        (ex, ey), r_e = self._entrada_xy()
        self.entrada_xy = (ex, ey, r_e)
        self.espolon_eje = _eje_espolon(self.geom_pista, self.geom_curvas, (ex, ey, self.z_ent))

    def sitio_veg_ok(self, x, y, z, arbol=True):
        """v3 (N1): una planta del penon no puede ir en el espolon del integrador ni en la boca de la entrada (por fuera
        de la plataforma), ni quedar enterrada por la ladera (terreno > base + 0.3: arcenes de relleno bajo la hierba);
        un arbol tampoco a < D_VEG_PISTA m del borde de la pista."""
        if self.terreno_fn is not None and float(self.terreno_fn(x, y)) > z + 0.3:
            return False
        if self.entrada_xy is not None:
            ex, ey, r_e = self.entrada_xy
            if math.hypot(x - ex, y - ey) < self.R_VEG_ENTRADA and math.hypot(x - self.cx, y - self.cy) > r_e - 1.0:
                return False
        if self.espolon_eje:
            d, ze = _d_polilinea(x, y, self.espolon_eje)
            if d < (self.D_VEG_ESPOLON if arbol else self.D_MATA_ESPOLON) and (ze is None or abs(z - ze) < 15.0):
                self.n_veg_espolon += 1
                return False
        if arbol and self.pista and self._d_pista(x, y, self.pista)[0] < self.D_VEG_PISTA:
            return False
        return True

    def vegetacion(self, parent, raiz, veg):
        """Palmeras y cipreses en el borde de la meseta (fuera de la huella del casino), pino en
        la isla de cada horquilla, cipreses en la entrada, palmeras en el paseo del muelle,
        pinos en los taludes tendidos y matas en las cornisas de estrato LIBRES (el primer
        impacto de un rayo vertical es la propia cornisa)."""
        self.n_veg = 0
        self.n_matas = 0
        self.veg_pts = []
        self.n_veg_espolon = 0
        self._preparar_espolon()
        if veg is None:
            return
        lib = {}
        rnd = self.rnd

        def poner(tipo, x, y, z, escala=1.0, var=0):
            if z < self.z_mar + 0.5:          # G13: nada bajo el agua (cornisas sumergidas del pie)
                return False
            key = (tipo, var)
            if key not in lib:
                sd = self.seed * 11 + var * 3 + len(lib)
                if tipo == 'palmera':
                    ob = veg.build_palmera(parent, alto=9.0 + var, seed=sd)
                elif tipo == 'pino':
                    ob = veg.build_pino(parent, alto=10.0 + 2 * var, seed=sd)
                elif tipo == 'cipres':
                    ob = veg.build_cipres(parent, alto=9.0 + var, seed=sd)
                else:
                    ob = veg.build_arbusto(parent, tam=1.6, seed=sd)
                ob.name = 'VEG_penon_%s%d' % (tipo, var)
                ob.parent = raiz
                lib[key] = ob
                ob.location = Vector((x, y, z))
                ob.rotation_euler = (0.0, 0.0, rnd.uniform(0, TAU))
                ob.scale = (escala, escala, escala)
            else:
                self._clonar(lib[key], raiz, parent, (x, y, z), rnd.uniform(0, TAU), escala)
            self.n_veg += 1
            self.veg_pts.append((x, y, z, tipo))
            return True

        def libre(x, y, z, d_min=4.5, r_obj=4.0):
            if self.d_calzada(x, y, z) < d_min:
                return False
            if any(math.hypot(x - c['x'], y - c['y']) < 9.0 and abs(z - c['z']) < 12.0 for c in self.plazas_casas):
                return False
            if any(math.hypot(x - p[0], y - p[1]) < r_obj and abs(z - p[2]) < 6.0 for p in self.veg_pts):
                return False
            if not self.sitio_veg_ok(x, y, z, arbol=True):
                return False
            zr = self.z_roca(x, y, z + 60.0)
            return zr is not None and abs(zr - z) < 0.12

        def en_casino(x, y, m=4.0):
            ca, sa = math.cos(self.theta_casino), math.sin(self.theta_casino)
            u = (x - self.cx) * ca + (y - self.cy) * sa
            v = -(x - self.cx) * sa + (y - self.cy) * ca
            hx, hy = self.params.get('casino_huella', (84.6, 48.6))
            return abs(u) < hx / 2.0 + m and abs(v) < hy / 2.0 + m
        for k in range(28):
            a = TAU * k / 28.0 + 0.11
            i = int(round((a % TAU) / self.dphi)) % self.M
            if i in self.hueco_meseta:
                continue
            x, y = self.xy_ang(a, self.R_top_eff[i] - 5.5)
            if not en_casino(x, y) and libre(x, y, self.z_top, 4.0, 6.0):
                poner('palmera' if k % 2 == 0 else 'cipres', x, y, self.z_top, var=k % 2)
        for h in self.horquillas:
            x, y = h.get('centro', (None, None))
            if x is not None and libre(x, y, h['z'], 3.8):
                poner('pino', x, y, h['z'], var=1)
        ent = sorted(self.cadenas['ent'], key=lambda c: c['i'])
        for c in (ent[1], ent[-2]):
            x, y = self.xy(c['i'], c['R_in'] + 1.2)
            if libre(x, y, c['z'], 4.0):
                poner('cipres', x, y, c['z'], var=0)
        if self.espigon is not None:
            e = self.espigon
            v = e['lado_roca'] * (e['A_q'] / 2.0 - 2.5)
            for u in range(18, int(e['L_q']) - 3, 11):
                x = e['o'][0] + e['u'][0] * u + e['v'][0] * v
                y = e['o'][1] + e['u'][1] * u + e['v'][1] * v
                if libre(x, y, self.z_cala, 3.0, 5.0):
                    poner('palmera', x, y, self.z_cala, escala=rnd.uniform(0.9, 1.1), var=0)
        elif self.cala and self.fin == 'cala':
            # v2: palmeras en el borde del muelle de la cala de la roca (fuera del pantalan)
            pc = self._pantalan_cala()
            for k in range(6, len(self.cala), 4):
                c = self.cala[k]
                if pc is not None and abs(k - pc[0]) < 3:
                    continue
                x, y = self.xy(c['i'], c['R_out'] - 3.2)
                if libre(x, y, self.z_cala, 3.0, 5.0):
                    poner('palmera', x, y, self.z_cala, escala=rnd.uniform(0.9, 1.1), var=0)
        # pinos en taludes tendidos y matas en cornisas libres (lejos de la calzada)
        cand = []
        for fa in self.roca_f[::3]:
            vs = [self.roca_v[q] for q in fa]
            if len(vs) != 3:
                continue
            ax, ay, az = vs[1][0] - vs[0][0], vs[1][1] - vs[0][1], vs[1][2] - vs[0][2]
            bx, by, bz = vs[2][0] - vs[0][0], vs[2][1] - vs[0][1], vs[2][2] - vs[0][2]
            nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            if ln < 6.0:
                continue
            cz = (vs[0][2] + vs[1][2] + vs[2][2]) / 3.0
            if nz / ln > 0.82 and self.z_mar + 3.0 < cz < self.z_top - 3.0:
                cand.append(((vs[0][0] + vs[1][0] + vs[2][0]) / 3.0, (vs[0][1] + vs[1][1] + vs[2][1]) / 3.0, cz))
        rnd.shuffle(cand)
        n_p = 0
        for (x, y, z) in cand:
            if n_p >= 22:
                break
            zr = self.z_roca(x, y, z + 80.0)
            if zr is not None and abs(zr - z) < 0.5 and libre(x, y, zr, 6.0, 9.0):
                if poner('pino', x, y, zr, escala=rnd.uniform(0.8, 1.15), var=n_p % 2):
                    n_p += 1
        labios = [p for p in self.labios if _ruido(p[0] * 0.09 + self.seed, p[1] * 0.09, p[2] * 0.3) > 0.1]
        rnd.shuffle(labios)
        for (x, y, z, r, i) in labios:
            if self.n_matas >= 70:
                break
            xx, yy = self.xy(i, r - 0.35)
            zr = self.z_roca(xx, yy, z + 80.0)
            if zr is None or abs(zr - z) > 0.8 or self.d_calzada(xx, yy, zr, 6.0) < 4.5:
                continue
            if not self.sitio_veg_ok(xx, yy, zr, arbol=False):
                continue
            if poner('arbusto', xx, yy, zr - 0.05, escala=rnd.uniform(0.7, 1.3), var=rnd.randint(0, 1)):
                self.n_matas += 1

    # ------------------------------------------------------------------ marina
    def marina(self, parent, raiz, italiano_kit, yates_kit):
        """Fuente en el paseo del muelle, pantalan VIP en la punta y 3 lanchas amarradas."""
        self.n_barcos = 0
        self.cala_xyz = None
        self.cala_huella = []
        e = self.espigon
        if e is None:
            if self.cala and self.fin == 'cala':
                self._marina_cala_roca(parent, raiz, italiano_kit, yates_kit)
            return
        ux, uy = e['u']
        vx, vy = e['v']
        ox, oy = e['o']
        L, A = e['L_q'], e['A_q'] / 2.0
        self.cala_xyz = (ox + ux * L / 2.0, oy + uy * L / 2.0, self.z_cala)
        self.cala_huella = [(ox + ux * u + vx * v, oy + uy * u + vy * v)
                            for (u, v) in ((-2.0, -A - 4), (L + e['L_p'] + 8, -A - 4), (L + e['L_p'] + 8, A + 4), (-2.0, A + 4))]
        if italiano_kit is not None:
            try:
                vv = e['lado_roca'] * 4.5
                f = italiano_kit.build_fuente(parent, seed=self.seed)
                f.parent = raiz
                f.location = Vector((ox + ux * (L - 14.0) + vx * vv, oy + uy * (L - 14.0) + vy * vv, self.z_cala + 0.02))
                for ch in f.children_recursive:
                    ch.name = 'ITAL_penon_' + ch.name
            except Exception as ex:  # pragma: no cover
                self.avisos.append('fuente: %s' % ex)
        if yates_kit is None:
            return
        try:
            h = math.atan2(uy, ux)
            pant = yates_kit.build_pantalan_vip(parent, largo=e['L_p'], seed=self.seed, z_cubierta=0.9)
            pant.parent = raiz
            pant.location = Vector((ox + ux * (L - 0.5), oy + uy * (L - 0.5), self.z_mar))
            pant.rotation_euler = (0.0, 0.0, h)
            for k, (du, dv) in enumerate(((7.0, 4.6), (16.0, -4.6), (25.0, 4.6))):
                lan = yates_kit.build_lancha(parent, eslora=9.0, seed=self.seed + k)
                lan.parent = raiz
                lan.location = Vector((ox + ux * (L + du) + vx * dv, oy + uy * (L + du) + vy * dv, self.z_mar))
                lan.rotation_euler = (0.0, 0.0, h + (0.0 if k != 1 else math.pi))
                self.n_barcos += 1
        except Exception as ex:  # pragma: no cover
            self.avisos.append('marina: %s' % ex)


def _leer_geom(params):
    """(muestras, curvas) de la pista: params['pista'] (dicts con x, y, z, w[, nx, ny, lat] o tuplas (x, y, z, w)) y
    params['curvas']; lo que no venga se lee de la MISMA geometria que integrar_escena (env GEOM o
    03_blender/geometria_3d.json; una sola lectura). Sin pista: [] (no hay relleno junto a la pista ni espolon)."""
    pista, curvas = params.get('pista'), params.get('curvas')
    if pista is None or curvas is None:
        ruta = os.environ.get('GEOM') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'geometria_3d.json')
        try:
            with open(ruta, encoding='utf-8') as fh:
                G = json.load(fh)
        except (OSError, ValueError, TypeError):
            G = {}
        if pista is None:
            pista = G.get('muestras') if isinstance(G, dict) else None
        if curvas is None:
            curvas = G.get('curvas') if isinstance(G, dict) else None
    return list(pista or []), list(curvas or [])


def _xyzw(q):
    if isinstance(q, dict):
        return float(q['x']), float(q['y']), float(q['z']), float(q['w'])
    return float(q[0]), float(q[1]), float(q[2]), float(q[3])


def _eje_espolon(pista, curvas, ent):
    """v3 (N1): eje en planta del ESPOLON que integrar_escena.zona_caminos tiende de la pista a la entrada del penon
    (info['entrada']): muestra i_j de la cresta (curvas 36-38: range(i36 - 30, i38 + 4, 2)) mas cercana a la
    entrada, boca a w/2 + 1 del eje por el lado de la entrada, tramo perpendicular de 6 m y entrada. Sin curvas: la
    muestra mas cercana a +-6 m de la cota de la entrada. Devuelve [(x, y, z)] (3 puntos) o None."""
    N = len(pista)
    if N < 3:
        return None
    ex, ey, ez = float(ent[0]), float(ent[1]), float(ent[2])
    cv = {}
    for c in curvas:
        try:
            cv[int(c['n'])] = int(c['s_idx'])
        except (KeyError, TypeError, ValueError):
            continue
    if 36 in cv and 38 in cv:
        idx = [i % N for i in range(cv[36] - 30, cv[38] + 4, 2)]
    else:
        idx = [i for i in range(0, N, 2) if abs(_xyzw(pista[i])[2] - ez) < 6.0]
    if not idx:
        return None
    i_j = min(idx, key=lambda i: (_xyzw(pista[i])[0] - ex) ** 2 + (_xyzw(pista[i])[1] - ey) ** 2)
    x, y, z, w = _xyzw(pista[i_j])
    if math.hypot(x - ex, y - ey) > 250.0:          # escaparate (penon suelto lejos de la cresta): no hay espolon
        return None
    q = pista[i_j]
    if isinstance(q, dict) and 'nx' in q:
        nx, ny = float(q['nx']), float(q['ny'])
    else:
        ax, ay = _xyzw(pista[(i_j - 1) % N])[:2]
        bx, by = _xyzw(pista[(i_j + 1) % N])[:2]
        lt = math.hypot(bx - ax, by - ay) or 1.0
        nx, ny = -(by - ay) / lt, (bx - ax) / lt
    side = 1.0 if (ex - x) * nx + (ey - y) * ny > 0 else -1.0
    lat = float(q.get('lat', 0.0)) if isinstance(q, dict) else 0.0
    z_b = z - lat * side * w / 2.0 - 0.03
    pb = (x + side * nx * (w / 2.0 + 1.0), y + side * ny * (w / 2.0 + 1.0), z_b)
    pp = (pb[0] + side * nx * 6.0, pb[1] + side * ny * 6.0, z_b)
    return [pb, pp, (ex, ey, ez + 0.1)]


def _d_polilinea(x, y, pl):
    """Distancia en planta de (x, y) a la polilinea pl [(x, y, ...)] y cota interpolada en el punto mas cercano."""
    best, zb = 1e9, None
    for a, b in zip(pl, pl[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dy * dy
        f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / l2))
        d = math.hypot(x - a[0] - f * dx, y - a[1] - f * dy)
        if d < best:
            best = d
            zb = (a[2] + f * (b[2] - a[2])) if len(a) > 2 else None
    return best, zb


def _muestras_pista(pista, cx, cy, radio=340.0):
    """Muestras (x, y, z, w/2) de la pista (lista de _leer_geom) a menos de `radio` del centro del penon."""
    out = []
    for q in pista:
        if isinstance(q, dict):
            x, y, z, w = q['x'], q['y'], q['z'], q['w']
        else:
            x, y, z, w = q[0], q[1], q[2], q[3]
        if math.hypot(x - cx, y - cy) < radio:
            out.append((float(x), float(y), float(z), float(w) / 2.0))
    return out


def _pendiente_max(pts):
    pend = 0.0
    for a, b in zip(pts, pts[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if d > 0.5:
            pend = max(pend, abs(b[2] - a[2]) / d)
    return pend


def _quiebro_max(pts, excluir=()):
    """Mayor desvio lateral de una muestra respecto al punto medio de sus vecinas, por metro
    (0.05 en una curva de 25 m con paso de 2.5 m; un salto lateral de 4 m da > 1)."""
    q = 0.0
    for k in range(1, len(pts) - 1):
        if k in excluir:
            continue
        a, p, b = pts[k - 1], pts[k], pts[k + 1]
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        d = math.hypot(b[0] - a[0], b[1] - a[1]) / 2.0
        if d > 0.3:
            q = max(q, math.hypot(p[0] - mx, p[1] - my) / d)
    return q


def build(parent_collection, contorno=None, z_base=None, z_plaza=None, entrada=None, z_mar=0.0, seed=0,
          casas_kit=None, vegetacion_kit=None, italiano_kit=None, yates_kit=None, **params):
    """Ver docstring del modulo. Sin contorno: escaparate (elipse 118x78 en el mar)."""
    if contorno is None:
        contorno = []
        for k in range(64):
            a = TAU * k / 64.0
            ex, ey = 118.0 * math.cos(a), 78.0 * math.sin(a)
            contorno.append((ex * math.cos(0.5) - ey * math.sin(0.5), ex * math.sin(0.5) + ey * math.cos(0.5)))
        z_base = 0.3 if z_base is None else z_base
        z_plaza = 96.0 if z_plaza is None else z_plaza
        entrada = (contorno[40][0], contorno[40][1], 84.0) if entrada is None else entrada
    log = params.get('log') or (lambda s: print('[roca_casino] ' + s))
    raiz = bpy.data.objects.new('PENON_cara', None)
    raiz.empty_display_size = 5.0
    parent_collection.objects.link(raiz)
    P = _Penon(contorno, z_base, z_plaza, entrada, z_mar, seed, params)
    P.trazar()
    P.malla_roca(parent_collection, raiz)
    P.malla_carretera(parent_collection, raiz)
    P.malla_espigon(parent_collection, raiz)
    P._bvh()
    P.malla_parapeto(parent_collection, raiz)
    P.malla_balaustrada(parent_collection, raiz)
    P.malla_pavimentos(parent_collection, raiz)
    P.casas(parent_collection, raiz, casas_kit)
    P.vegetacion(parent_collection, raiz, vegetacion_kit)
    P.marina(parent_collection, raiz, italiano_kit, yates_kit)
    sub, baj = P.cintas
    (ex, ey), _r_e = P._entrada_xy()
    # vueltas de la bajada alrededor del centro y longitud
    sw = 0.0
    for a, b in zip(baj, baj[1:]):
        sw += abs(_dang(math.atan2(b[1] - P.cy, b[0] - P.cx), math.atan2(a[1] - P.cy, a[0] - P.cx)))
    lazos = set()
    k = 0
    for h in P.horquillas:
        c0 = h.get('centro')
        for kk, p in enumerate(baj):
            if c0 and math.hypot(p[0] - c0[0], p[1] - c0[1]) < h.get('rho', 6.5) + 1.0:
                lazos.update((kk - 1, kk, kk + 1))
    meseta = [P.xy(i, P.R_top_eff[i] - 1.0) for i in range(0, P.M, 2)]
    r_mes = min(math.hypot(x - P.cx, y - P.cy) for (x, y) in meseta)
    tipo_fin = 'espigon' if P.espigon is not None else ('cala_roca' if (P.cala and P.fin == 'cala') else P.fin)
    info = {'entrada': (ex, ey, P.z_ent), 'z_top': P.z_top, 'centro_top': P.centro_top,
            'radio_meseta': r_mes, 'meseta_poligono': meseta, 'casino_rect': P.casino_rect,
            'muestras_carretera': P.muestras_xyz, 'cintas': [sub, baj], 'plazas_casas': P.plazas_casas,
            'cala': P.cala_xyz, 'cala_huella': P.cala_huella, 'camino_pie': [], 'tipo_fin': tipo_fin,
            'conexion_cala': 'bajada' if P.fin == 'cala' else None,
            'llega_cala': P.fin == 'cala', 'n_horquillas': len(P.horquillas), 'vueltas_bajada': sw / TAU,
            'longitud_bajada': sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(baj, baj[1:])),
            'pendiente_max_bajada': _pendiente_max(baj),
            'longitud_subida': sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(sub, sub[1:])),
            'pendiente_max_subida': _pendiente_max(sub), 'longitud_carretera': P.longitud,
            'pendiente_max': max(_pendiente_max(sub), _pendiente_max(baj)), 'casas_malas': P.casas_malas,
            'quiebro_max': max(_quiebro_max(sub), _quiebro_max(baj, lazos)), 'quiebro_polar': P.quiebro_max,
            'n_voladizos_apilado': P.n_voladizos, 'sentido': P.s_baj, 'sentido_subida': P.s_sub,
            'avisos': P.avisos, 'tris_roca': P.tris_roca, 'farolas': P.farolas, 'n_farolas': len(P.farolas),
            'n_veg': P.n_veg, 'n_matas': P.n_matas, 'n_barcos': P.n_barcos,
            'horquillas': [{'centro': h.get('centro'), 'z': h['z'], 'rho': h.get('rho')} for h in P.horquillas],
            'espigon': None if P.espigon is None else {'pts': P.espigon['pts'], 'z0': P.espigon['z0'],
                                                       'largo': 2.5 * (len(P.espigon['pts']) - 1)},
            'forma': {'f_bot': P.f_bot, 'a': P.a_med, 'k_top': P.k_top}, 'modo': P.modo,
            'fin_carretera': list(baj[-1]) if baj else None, 'bolardos': len(P.bolardos),
            'relleno_pista': P.n_relleno[0], 'relleno_fosos': P.n_relleno[1], 'n_muestras_pista': len(P.pista),
            'relleno_foso_tierra': P.n_foso_tierra, 'espolon_eje': P.espolon_eje, 'veg_rechazada_espolon': P.n_veg_espolon}
    raiz['info'] = json.dumps(info)
    global _ultimo
    _ultimo = P
    log('sentido bajada %+d (subida %+d), entrada col %d z %.1f; subida %.0f m (%.1f%%); bajada %.0f m, %.2f vueltas, '
        '%d horquillas, pend max %.1f%%, fin %s (modo %s), barcos %d; casas %d (malas %d), farolas %d, veg %d (matas %d), '
        'roca %d tris, meseta r>=%.1f, voladizos %d, quiebro %.2f; relleno %d col. junto a la pista (%d muestras), %d en fosos '
        '(%d de tierra); espolon %s, plantas fuera del espolon %d'
        % (P.s_baj, P.s_sub, P.i_ent, P.z_ent, info['longitud_subida'], info['pendiente_max_subida'] * 100,
           info['longitud_bajada'], info['vueltas_bajada'], len(P.horquillas), info['pendiente_max_bajada'] * 100,
           tipo_fin, P.modo, P.n_barcos, len(P.plazas_casas), P.casas_malas, len(P.farolas), P.n_veg, P.n_matas, P.tris_roca,
           r_mes, P.n_voladizos, info['quiebro_max'], P.n_relleno[0], len(P.pista), P.n_relleno[1], P.n_foso_tierra,
           'si' if P.espolon_eje else 'no', P.n_veg_espolon))
    for a in P.avisos:
        log('AVISO ' + a)
    return raiz, info
