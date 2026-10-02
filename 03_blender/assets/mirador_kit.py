"""mirador_kit.py — Kit procedural "las vistas de la bajada" de Porto Corsa
(Cars 2) para Blender 5.1: el decorado que se ve en la pelicula mientras la
calle baja por el pueblo (fotograma peli_bajada_viaducto_alto): palazzo
neoclasico con APARCAMIENTO EN LA AZOTEA lleno de coches-espectador, muro de
contencion de piedra con arcadas ciegas bajo la calzada, muretes de piedra de
borde de calle y un mirador semicircular con balaustrada.

Todo es codigo puro (bpy.data.meshes + from_pydata), materiales Principled
BSDF de color plano reutilizados por nombre (prefijo MAT_MIRADOR_; los de
piedra llevan la palabra 'piedra' en el nombre para la pasada de texturizado),
objetos con prefijo MIRADOR_, unidades en metros, z=0 en el suelo y cara
principal mirando a +Y.

Piezas (todas linkan a `parent_collection` y devuelven el objeto raiz):

- build_parking_terraza(parent_collection, ancho=40.0, fondo=18.0, alto=20.0,
                        seed=0)
    PALAZZO NEOCLASICO de piedra gris-rosada (medido en el fotograma: unos
    40 x 18 m y ~20 m de alto) cuya CUBIERTA PLANA es un aparcamiento.
    Huella exacta ancho x fondo centrada en el origen (solo vuelan la
    cornisa ~0.95 m, el toldo ~2.3 m y el cartel "P"), fachada de calle en
    +Y. `alto` es la cota de la LOSA de la azotea (donde se apoyan los
    coches); por encima queda el PETO MACIZO BLANCO de 1.20 m con albardilla
    (0.5 m de grueso), SIN barandilla como en la pelicula (barandilla=True
    anade un pasamanos de hierro de 10 cm). Alzado de abajo arriba: planta
    baja almohadillada con
    arcos (el de la esquina -X de la fachada +Y es la ENTRADA de coches con
    arranque de rampa y cartel "P"), imposta, dos plantas de ventanas altas
    y estrechas (la noble con fronton) entre pilastras de orden gigante,
    friso, modillones y CORNISA muy volada, ATICO con lunetos semicirculares
    entre machones y cornisilla bajo el peto. Toldo a rayas sobre los arcos
    centrales del lado de la calle. Con alto < 11 m se suprime el atico y
    con poca altura quedan solo los arcos. En la azotea (losa beige): dos
    filas de plazas pintadas en grupos de 3 con isletas cebreadas, pasillo
    central con flechas, DOS FAROLAS FINAS en las isletas, pozo de RAMPA de
    acceso a lo largo del lado -X (rampa descendente con murete) y dos
    banderas en las esquinas traseras (param banderas=True). La piedra es
    SIEMPRE la gris-rosada de la peli con cualquier seed (solo cambia con
    piedra='piedra_palazzo_crema' | 'piedra_palazzo_gris'); seed % 2 elige
    el color del toldo (0 rojo, 1 verde; o color_toldo='rojo'|'verde').
    La fachada trasera (-Y) lleva el MISMO ritmo de vanos que el frente
    (pilastras, lunetos y arcos casan con las esquinas) pero sin ornamento;
    trasera='completa' le da el detalle de los laterales (se sale del tope
    de tris: usar con tope_tris=None). Las caras "calcomania" (lineas de
    plaza, flechas, llagas, vidrios de luneto, parteluces) van despegadas
    5 cm de su soporte para que no parpadeen en Assetto Corsa a 100-150 m.
    DEGRADACION AUTOMATICA: si el edificio no cabe en tope_tris (6000 por
    defecto; None la desactiva) se recorta detalle por niveles (parteluces,
    modillones, llagas, ornamento y, desde el nivel 3, vanos mas anchos);
    con detalle completo caben hasta ~44 x 20 x 20 m. El nivel usado queda
    en raiz['mirador_lod'] y los tris en raiz['mirador_tris'].
    Raiz: Empty MIRADOR_parking con 3 mallas (_edificio, _cubierta,
    _detalles). Vuelos fuera de la huella: cornisa 0.95 m, toldo 2.3 m (en
    +Y, canto inferior a ~3.8 m), cartel P 2 m (en +Y), banderas hasta
    x = +ancho/2 + 1.7.

- plazas_parking(ancho=40.0, fondo=18.0, alto=20.0)
    Funcion PURA. Lista de (x, y, z, rot_z) en coordenadas locales del
    edificio, una por plaza pintada en la azotea. (x, y) es el centro de la
    plaza = centro del coche, z = alto (la losa), rot_z = 0.0 rad para un
    coche cuyo frontal mira a +Y (convencion de coches_kit): todos miran al
    borde de la calle (+Y) para que los ojos del parabrisas vean la carrera.
    Plazas holgadas de 3.6 x 5.0 m (coche 4.2 x 1.9 m). Coincide exactamente
    con las lineas que pinta build_parking_terraza con los mismos
    ancho/fondo. Por defecto: 12 plazas en 2 filas (6 junto al peto de la
    calle en y=+5.75 y 6 detras en y=-5.75), ordenadas fila a fila de -X a
    +X.

- build_muro_arcadas(parent_collection, largo=40.0, alto=8.0, n_arcos=5,
                     seed=0)
    Muro de contencion de piedra con `n_arcos` arcadas ciegas profundas
    (nicho oscuro de 1.3 m), zocalo, pilastras entre arcos, arquivoltas con
    clave, cornisa y peto bajo con pilarones. Largo a lo largo de X centrado
    en el origen, cara vista en y = +MURO_ARCADAS_GROSOR/2 (= +0.9) mirando
    a +Y, trasdos en y = -0.9. `alto` es la cota de la CORNISA (= nivel de
    la calzada contenida); el peto sube 0.9 m mas (pilarones 1.15 m).
    Teselable extremo con extremo: media pilastra y medio pilaron en cada
    testa. Malla unica MIRADOR_muro_arcadas. params: grosor=1.8,
    parapeto=True, inglete_izq=0.0, inglete_der=0.0.
    INGLETES (para seguir una curva, como el muro de la pelicula): angulo en
    radianes (|a| <= 0.45) que gira el plano de cada testa alrededor de la
    arista vertical de la CARA VISTA (x = +-largo/2, y = +0.9). En una junta
    donde el tramo siguiente gira un angulo T respecto a este (T > 0 = giro
    hacia +Y = cara vista CONCAVA; T < 0 = convexa), pasar inglete_der = T/2
    a este tramo e inglete_izq = T/2 al siguiente, y unir los tramos por esa
    arista de la cara vista: las dos testas coinciden exactamente en el
    plano bisector (cornisa, zocalo, pilastras y peto incluidos), sin cuna.
    Con 0.0 (por defecto) la geometria es identica al teselado recto.

- build_muro_arcadas_curvo(parent_collection, puntos, alto=8.0, seed=0)
    Atajo para lo anterior: cadena de tramos ingleteados que sigue la
    polilinea `puntos` [(x, y) o (x, y, z), ...] de la arista inferior de la
    cara vista (la cara mira a la IZQUIERDA del avance; invertir=True para
    la derecha; cerrado=True para anillos). Cuerdas de 6-10 m recomendadas,
    arcos por tramo = largo/modulo (modulo=8.0). Con z, cada tramo se apoya
    en la media de las z de sus extremos (muro escalonado). Raiz: Empty
    MIRADOR_muro_arcadas_curvo con una malla MIRADOR_muro_arcadas por tramo
    (307 tris el tramo de 8 m con 1 arco).

- build_muro_piedra(parent_collection, largo=10.0, alto=1.1)
    Murete bajo de piedra de borde de calle con hilada de base y albardilla
    a dos aguas. Largo en X centrado en el origen, 0.5 m de grueso (0.66 la
    albardilla) centrado en y=0, teselable en X. Malla unica
    MIRADOR_muro_piedra. params: seed=0 (piedras de acento).

- build_mirador(parent_collection, radio=7.0, seed=0)
    Terraza-mirador semicircular. OJO INTEGRADOR, convenio propio: el ORIGEN
    esta en el centro del BORDE RECTO (lado calzada, y=0), NO en el centro
    de la base; la terraza se abomba hacia +Y hasta y=radio (las vistas
    quedan a +Y). z=0 es el nivel de la ACERA/calzada (el pavimento queda a
    +6 cm, como un bordillo); por debajo baja un tambor de piedra ataluzado
    de `faldon` metros (param, 4.0 por defecto; 0 lo quita) para volarlo
    sobre una ladera, asi que la pieza ocupa z[-faldon, ~+4.9]. Colocarla
    con z = cota de la acera y el borde recto sobre el borde de la calzada.
    Toda la piedra queda en y >= 0; solo las frondas de las palmeras vuelan
    ~0.5 m hacia la calzada a mas de 3 m de altura. Con radios > ~9 m los
    balaustres se espacian automaticamente para caber en tope_tris (4000;
    None lo desactiva; nivel en raiz['mirador_lod']). Pavimento de piedra
    en abanico bicolor, balaustrada de piedra con 5 pilarones y balaustres
    torneados, farola de tres globos sobre el pilaron central, y dos
    jardineras de piedra con palmerita y adelfas en flor flanqueando la
    entrada. Raiz: Empty MIRADOR_mirador.

- build(parent_collection, seed=0, **params)
    Muestrario con todas las piezas (parking, muro de arcadas, dos muretes
    teselados, mirador levantado sobre su tambor). Raiz: Empty MIRADOR_kit.

Presupuesto medido (parametros por defecto): parking 5920 tris (tope 6k:
edificio 5333 + cubierta 201 + detalles 386), muro de arcadas 1207 (tope
1.5k), murete 154, mirador 3694 (tope 4k). Con degradacion automatica:
parking 48x22x20 5748 (nivel 2), 60x30x25 5985 (nivel 3), 80x40x30 5899
(nivel 4); mirador radio 12 3598 (nivel 2), radio 18 3790 (nivel 3).
"""

import math
import random

import bpy

PRE = 'MIRADOR'
TAU = 2.0 * math.pi

MURO_ARCADAS_GROSOR = 1.8      # grosor por defecto del muro de arcadas (m)
INGLETE_MAX = 0.45             # inglete maximo por testa (rad, ~26 grados)

# topes de triangulos por pieza (degradacion automatica de detalle)
TOPE_PARKING = 6000
TOPE_MIRADOR = 4000
_LOD_PARKING_MAX = 5           # ultimo nivel de degradacion del palazzo
_LOD_MIRADOR_MAX = 4           # idem del mirador

# despegue minimo de las caras "calcomania" (lineas pintadas, llagas, vidrios
# aplicados...) sobre su soporte: 5 cm para que no parpadeen en Assetto Corsa
# vistas a 100-150 m (precision de profundidad de 1-2 cm a esa distancia)
_DESPEGUE = 0.05

# geometria del aparcamiento compartida por build_parking_terraza y
# plazas_parking (no tocar una sin la otra)
_PETO_G = 0.50                 # grueso del peto macizo de la azotea
_PETO_H = 1.05                 # alto del peto (sin albardilla)
_PETO_ALB = 0.15               # canto de la albardilla (peto total 1.20 m)
_PLAZA_FONDO = 5.0
_PLAZA_ANCHO = 3.4             # ancho nominal de plaza (mundo de coches: holgada)
_PLAZA_ANCHO_MAX = 3.6
_PLAZA_ANCHO_MIN = 2.7
_GRUPO = 3                     # plazas por grupo
_ISLETA = 3.4                  # isleta cebreada entre grupos
_PASILLO_MIN = 4.4
_POZO_ANCHO = 3.8              # ancho libre de la rampa de acceso
_MURETE_G = 0.25
_ESQ = 1.1                     # ancho del machon de esquina del palazzo

# ------------------------------------------------------------------ materiales

# clave: (color lineal, roughness, metallic, color_emision | None, fuerza)
_PALETA = {
    'piedra_palazzo':       ((0.600, 0.365, 0.360), 0.85, 0.0, None, 0.0),
    'piedra_palazzo_crema': ((0.720, 0.560, 0.330), 0.85, 0.0, None, 0.0),
    'piedra_palazzo_gris':  ((0.520, 0.480, 0.460), 0.85, 0.0, None, 0.0),
    'piedra_palazzo_base':  ((0.455, 0.300, 0.295), 0.90, 0.0, None, 0.0),
    'piedra_palazzo_clara': ((0.800, 0.630, 0.570), 0.80, 0.0, None, 0.0),
    'vidrio_portal':  ((0.018, 0.030, 0.050), 0.30, 0.0, None, 0.0),
    'piedra_palazzo_llaga': ((0.270, 0.170, 0.170), 0.95, 0.0, None, 0.0),
    'piedra_blanca':  ((0.860, 0.840, 0.790), 0.75, 0.0, None, 0.0),
    'azotea_beige':   ((0.640, 0.540, 0.380), 0.90, 0.0, None, 0.0),
    'piedra_clara':   ((0.800, 0.715, 0.540), 0.80, 0.0, None, 0.0),
    'piedra_muro':    ((0.640, 0.460, 0.235), 0.90, 0.0, None, 0.0),
    'piedra_sombra':  ((0.330, 0.215, 0.110), 0.92, 0.0, None, 0.0),
    'piedra_zocalo':  ((0.420, 0.370, 0.300), 0.90, 0.0, None, 0.0),
    'piedra_pavimento_claro': ((0.720, 0.640, 0.480), 0.85, 0.0, None, 0.0),
    'piedra_pavimento_rosa':  ((0.640, 0.330, 0.230), 0.85, 0.0, None, 0.0),
    'hueco_oscuro':   ((0.030, 0.026, 0.030), 0.95, 0.0, None, 0.0),
    'ventana':        ((0.030, 0.075, 0.150), 0.12, 0.0, None, 0.0),
    'asfalto':        ((0.160, 0.155, 0.150), 0.92, 0.0, None, 0.0),
    'hormigon':       ((0.500, 0.480, 0.440), 0.90, 0.0, None, 0.0),
    'linea_blanca':   ((0.900, 0.900, 0.870), 0.70, 0.0, None, 0.0),
    'linea_amarilla': ((0.950, 0.680, 0.030), 0.70, 0.0, None, 0.0),
    'hierro':         ((0.030, 0.060, 0.050), 0.45, 0.50, None, 0.0),
    'toldo_rojo':     ((0.760, 0.075, 0.055), 0.65, 0.0, None, 0.0),
    'toldo_verde':    ((0.050, 0.360, 0.150), 0.65, 0.0, None, 0.0),
    'toldo_crema':    ((0.930, 0.870, 0.720), 0.65, 0.0, None, 0.0),
    'cartel_azul':    ((0.015, 0.110, 0.560), 0.40, 0.0, None, 0.0),
    'bandera_verde':  ((0.000, 0.420, 0.130), 0.60, 0.0, None, 0.0),
    'tierra':         ((0.120, 0.080, 0.050), 0.95, 0.0, None, 0.0),
    'tronco_palma':   ((0.300, 0.200, 0.105), 0.90, 0.0, None, 0.0),
    'hoja_palma':     ((0.120, 0.380, 0.070), 0.70, 0.0, None, 0.0),
    'hoja_adelfa':    ((0.070, 0.250, 0.095), 0.75, 0.0, None, 0.0),
    'flor_rosa':      ((0.930, 0.230, 0.420), 0.55, 0.0, None, 0.0),
    'farola_verde':   ((0.040, 0.125, 0.075), 0.40, 0.30, None, 0.0),
    'globo':          ((0.950, 0.780, 0.480), 0.30, 0.0, (1.0, 0.62, 0.26), 1.2),
}


def _mat(clave):
    """Crea (o reutiliza) el material MAT_MIRADOR_<clave> de la paleta."""
    nombre = 'MAT_%s_%s' % (PRE, clave)
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough, metal, emision, fuerza = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    try:
        if not m.use_nodes:
            m.use_nodes = True
    except AttributeError:
        pass
    bsdf = None
    nt = getattr(m, 'node_tree', None)
    if nt is not None:
        for nd in nt.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                bsdf = nd
                break
        if bsdf is None:
            bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
            salida = None
            for nd in nt.nodes:
                if nd.type == 'OUTPUT_MATERIAL':
                    salida = nd
                    break
            if salida is None:
                salida = nt.nodes.new('ShaderNodeOutputMaterial')
            nt.links.new(bsdf.outputs['BSDF'], salida.inputs['Surface'])
    if bsdf is not None:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = rough
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metal
        if emision is not None:
            ent = bsdf.inputs.get('Emission Color') or bsdf.inputs.get('Emission')
            fue = bsdf.inputs.get('Emission Strength')
            if ent is not None:
                ent.default_value = (*emision, 1.0)
            if fue is not None:
                fue.default_value = fuerza
    m.diffuse_color = (*color, 1.0)
    return m


# ------------------------------------------------------------ utilidades malla

def _normal(pts):
    """Normal (sin normalizar) de un poligono por el metodo de Newell."""
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0, z0 = pts[i]
        x1, y1, z1 = pts[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return nx, ny, nz


_CARAS_CAJA = (('-z', (0, 3, 2, 1)), ('+z', (4, 5, 6, 7)),
               ('-y', (0, 1, 5, 4)), ('+x', (1, 2, 6, 5)),
               ('+y', (2, 3, 7, 6)), ('-x', (3, 0, 4, 7)))


class _MB:
    """Acumulador de primitivas -> una unica malla multi-material. Los
    materiales se pasan por clave de paleta (str)."""

    def __init__(self):
        self.v = []
        self.f = []
        self.fm = []
        self.fs = []
        self.mats = []

    # -- basicos
    def m(self, clave):
        if clave not in self.mats:
            self.mats.append(clave)
        return self.mats.index(clave)

    def _add(self, idx, mat, suave=False):
        self.f.append(tuple(idx))
        self.fm.append(self.m(mat))
        self.fs.append(bool(suave))

    def cara(self, pts, mat, hacia=None, doble=False):
        """Poligono plano con vertices propios. `hacia`: vector orientativo
        de la normal deseada (se invierte el orden si hace falta). `doble`:
        anade la cara inversa (vertices propios, 4 mm por detras)."""
        pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts]
        n = _normal(pts)
        if hacia is not None:
            if n[0] * hacia[0] + n[1] * hacia[1] + n[2] * hacia[2] < 0.0:
                pts.reverse()
                n = (-n[0], -n[1], -n[2])
        b = len(self.v)
        self.v.extend(pts)
        self._add(range(b, b + len(pts)), mat)
        if doble:
            ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
            o = (-0.004 * n[0] / ln, -0.004 * n[1] / ln, -0.004 * n[2] / ln)
            b = len(self.v)
            self.v.extend([(p[0] + o[0], p[1] + o[1], p[2] + o[2])
                           for p in reversed(pts)])
            self._add(range(b, b + len(pts)), mat)

    def caja(self, centro, dim, mat, rz=0.0, sin=()):
        cx, cy, cz = centro
        hx, hy, hz = dim[0] / 2.0, dim[1] / 2.0, dim[2] / 2.0
        b = len(self.v)
        c, s = math.cos(rz), math.sin(rz)
        for dx, dy, dz in ((-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz),
                           (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz),
                           (hx, hy, hz), (-hx, hy, hz)):
            self.v.append((cx + dx * c - dy * s, cy + dx * s + dy * c, cz + dz))
        for nombre, q in _CARAS_CAJA:
            if nombre in sin:
                continue
            self._add((b + q[0], b + q[1], b + q[2], b + q[3]), mat)

    def caja2(self, x0, x1, y0, y1, z0, z1, mat, sin=()):
        self.caja(((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0),
                  (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), mat, sin=sin)

    def revolucion(self, centro, perfil, mat, n=8, suave=True,
                   tapa_inf=False, tapa_sup=False, fase=0.0):
        """Cuerpo de revolucion vertical. perfil = [(radio, z), ...] de abajo
        arriba (radios > 0). Tapas con vertices propios (canto vivo)."""
        cx, cy, cz = centro
        b = len(self.v)
        for r, z in perfil:
            for j in range(n):
                th = fase + TAU * j / n
                self.v.append((cx + r * math.cos(th), cy + r * math.sin(th),
                               cz + z))
        for i in range(len(perfil) - 1):
            for j in range(n):
                j2 = (j + 1) % n
                self._add((b + i * n + j, b + i * n + j2,
                           b + (i + 1) * n + j2, b + (i + 1) * n + j),
                          mat, suave)
        if tapa_inf:
            r, z = perfil[0]
            self.cara([(cx + r * math.cos(fase + TAU * j / n),
                        cy + r * math.sin(fase + TAU * j / n), cz + z)
                       for j in range(n)], mat, hacia=(0, 0, -1))
        if tapa_sup:
            r, z = perfil[-1]
            self.cara([(cx + r * math.cos(fase + TAU * j / n),
                        cy + r * math.sin(fase + TAU * j / n), cz + z)
                       for j in range(n)], mat, hacia=(0, 0, 1))

    def esfera(self, centro, r, mat, nseg=8, nan=5, escala_z=1.0, suave=True):
        cx, cy, cz = centro
        b = len(self.v)
        self.v.append((cx, cy, cz + r * escala_z))
        for i in range(1, nan):
            phi = math.pi * i / nan
            zc = math.cos(phi) * r * escala_z
            rr = math.sin(phi) * r
            for j in range(nseg):
                th = TAU * j / nseg
                self.v.append((cx + rr * math.cos(th), cy + rr * math.sin(th),
                               cz + zc))
        self.v.append((cx, cy, cz - r * escala_z))
        for j in range(nseg):
            j2 = (j + 1) % nseg
            self._add((b, b + 1 + j, b + 1 + j2), mat, suave)
        for i in range(nan - 2):
            r0 = b + 1 + i * nseg
            r1 = r0 + nseg
            for j in range(nseg):
                j2 = (j + 1) % nseg
                self._add((r0 + j2, r0 + j, r1 + j, r1 + j2), mat, suave)
        polo = b + 1 + (nan - 1) * nseg
        r0 = b + 1 + (nan - 2) * nseg
        for j in range(nseg):
            j2 = (j + 1) % nseg
            self._add((polo, r0 + j2, r0 + j), mat, suave)

    def tubo(self, puntos, radios, mat, n=6, suave=True, tapas=True):
        """Tubo barrido por una polilinea; `radios` float o lista por punto."""
        m = len(puntos)
        if not isinstance(radios, (list, tuple)):
            radios = [radios] * m
        b = len(self.v)
        for i in range(m):
            p = puntos[i]
            a = puntos[max(i - 1, 0)]
            c = puntos[min(i + 1, m - 1)]
            t = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            lt = math.sqrt(t[0] ** 2 + t[1] ** 2 + t[2] ** 2) or 1.0
            t = (t[0] / lt, t[1] / lt, t[2] / lt)
            ref = (0.0, 0.0, 1.0) if abs(t[2]) < 0.92 else (0.0, 1.0, 0.0)
            b1 = (ref[1] * t[2] - ref[2] * t[1], ref[2] * t[0] - ref[0] * t[2],
                  ref[0] * t[1] - ref[1] * t[0])
            l1 = math.sqrt(b1[0] ** 2 + b1[1] ** 2 + b1[2] ** 2) or 1.0
            b1 = (b1[0] / l1, b1[1] / l1, b1[2] / l1)
            b2 = (t[1] * b1[2] - t[2] * b1[1], t[2] * b1[0] - t[0] * b1[2],
                  t[0] * b1[1] - t[1] * b1[0])
            rr = radios[i]
            for j in range(n):
                th = TAU * j / n
                ct, st = math.cos(th) * rr, math.sin(th) * rr
                self.v.append((p[0] + b1[0] * ct + b2[0] * st,
                               p[1] + b1[1] * ct + b2[1] * st,
                               p[2] + b1[2] * ct + b2[2] * st))
        for i in range(m - 1):
            r0 = b + i * n
            r1 = r0 + n
            for j in range(n):
                j2 = (j + 1) % n
                self._add((r0 + j, r0 + j2, r1 + j2, r1 + j), mat, suave)
        if tapas:
            self.cara([self.v[b + j] for j in range(n)], mat,
                      hacia=(puntos[0][0] - puntos[1][0],
                             puntos[0][1] - puntos[1][1],
                             puntos[0][2] - puntos[1][2]))
            self.cara([self.v[b + (m - 1) * n + j] for j in range(n)], mat,
                      hacia=(puntos[-1][0] - puntos[-2][0],
                             puntos[-1][1] - puntos[-2][1],
                             puntos[-1][2] - puntos[-2][2]))

    def anillo(self, r_in, r_out, z0, z1, th0, th1, nseg, mat,
               caras=('ext', 'int', 'sup', 'inf'), centro=(0.0, 0.0),
               r_out_base=None, tapas=False):
        """Sector anular de seccion rectangular (barandales curvos, tambor).
        r_out_base: radio exterior en z0 si la cara exterior va ataluzada."""
        cx, cy = centro
        rob = r_out if r_out_base is None else r_out_base
        for k in range(nseg):
            a0 = th0 + (th1 - th0) * k / nseg
            a1 = th0 + (th1 - th0) * (k + 1) / nseg
            c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
            am = (a0 + a1) / 2.0
            rad = (math.cos(am), math.sin(am), 0.0)
            if 'ext' in caras:
                self.cara([(cx + rob * c0, cy + rob * s0, z0),
                           (cx + rob * c1, cy + rob * s1, z0),
                           (cx + r_out * c1, cy + r_out * s1, z1),
                           (cx + r_out * c0, cy + r_out * s0, z1)], mat, hacia=rad)
            if 'int' in caras:
                self.cara([(cx + r_in * c0, cy + r_in * s0, z0),
                           (cx + r_in * c1, cy + r_in * s1, z0),
                           (cx + r_in * c1, cy + r_in * s1, z1),
                           (cx + r_in * c0, cy + r_in * s0, z1)], mat,
                          hacia=(-rad[0], -rad[1], 0.0))
            if 'sup' in caras:
                self.cara([(cx + r_in * c0, cy + r_in * s0, z1),
                           (cx + r_out * c0, cy + r_out * s0, z1),
                           (cx + r_out * c1, cy + r_out * s1, z1),
                           (cx + r_in * c1, cy + r_in * s1, z1)], mat,
                          hacia=(0, 0, 1))
            if 'inf' in caras:
                self.cara([(cx + r_in * c0, cy + r_in * s0, z0),
                           (cx + rob * c0, cy + rob * s0, z0),
                           (cx + rob * c1, cy + rob * s1, z0),
                           (cx + r_in * c1, cy + r_in * s1, z0)], mat,
                          hacia=(0, 0, -1))
        if tapas:
            for a, sg in ((th0, -1.0), (th1, 1.0)):
                c, s = math.cos(a), math.sin(a)
                self.cara([(cx + r_in * c, cy + r_in * s, z0),
                           (cx + rob * c, cy + rob * s, z0),
                           (cx + r_out * c, cy + r_out * s, z1),
                           (cx + r_in * c, cy + r_in * s, z1)], mat,
                          hacia=(-s * sg, c * sg, 0.0))

    def anexar(self, otro, rz=0.0, t=(0.0, 0.0, 0.0)):
        """Incorpora otro _MB girado rz sobre Z y trasladado t."""
        b = len(self.v)
        c, s = math.cos(rz), math.sin(rz)
        for x, y, z in otro.v:
            self.v.append((x * c - y * s + t[0], x * s + y * c + t[1], z + t[2]))
        for idx, mi, sv in zip(otro.f, otro.fm, otro.fs):
            self.f.append(tuple(b + i for i in idx))
            self.fm.append(self.m(otro.mats[mi]))
            self.fs.append(sv)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def obj(self, nombre, col, padre=None):
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(self.v, [], self.f)
        for clave in self.mats:
            me.materials.append(_mat(clave))
        me.polygons.foreach_set('material_index', self.fm)
        try:
            me.polygons.foreach_set('use_smooth', self.fs)
        except (AttributeError, TypeError, RuntimeError):
            pass
        me.validate()
        me.update()
        ob = bpy.data.objects.new(nombre, me)
        col.objects.link(ob)
        if padre is not None:
            ob.parent = padre
        return ob


def _raiz(nombre, col, tam=1.0):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_size = tam
    col.objects.link(e)
    return e


# --------------------------------------------------- pared con huecos (canonica)
# Marco canonico de fachada: pared en el plano y = const mirando a +Y, x a lo
# largo, z arriba. Las fachadas laterales/trasera se construyen aqui y luego
# se giran con _MB.anexar().

def _arco_pts(xc, zs, r, n):
    """Puntos (x, z) del semicirculo, de +x a -x."""
    return [(xc + r * math.cos(math.pi * k / n), zs + r * math.sin(math.pi * k / n))
            for k in range(n + 1)]


def _hueco(mb, h, y, n_arc):
    """Nicho/hueco retranqueado `prof` tras el plano y."""
    xa = h['xc'] - h['w'] / 2.0
    xb = h['xc'] + h['w'] / 2.0
    zb, zs = h['zb'], h['zs']
    yb = y - h['prof']
    mj, mf = h['m_jamba'], h['m_fondo']
    mb.cara([(xa, y, zb), (xa, yb, zb), (xa, yb, zs), (xa, y, zs)], mj,
            hacia=(1, 0, 0))
    mb.cara([(xb, y, zb), (xb, yb, zb), (xb, yb, zs), (xb, y, zs)], mj,
            hacia=(-1, 0, 0))
    if h.get('suelo', True):
        mb.cara([(xa, y, zb), (xb, y, zb), (xb, yb, zb), (xa, yb, zb)],
                h.get('m_suelo', mj), hacia=(0, 0, 1))
    if h.get('arco'):
        pts = _arco_pts(h['xc'], zs, h['w'] / 2.0, n_arc)
        for k in range(n_arc):
            (ax, az), (bx, bz) = pts[k], pts[k + 1]
            mb.cara([(ax, y, az), (bx, y, bz), (bx, yb, bz), (ax, yb, az)], mj,
                    hacia=(h['xc'] - (ax + bx) / 2.0, 0.0, zs - (az + bz) / 2.0))
        fondo = [(xa, yb, zb), (xb, yb, zb)] + [(px, yb, pz) for px, pz in pts]
        mb.cara(fondo, mf, hacia=(0, 1, 0))
    else:
        mb.cara([(xa, y, zs), (xb, y, zs), (xb, yb, zs), (xa, yb, zs)], mj,
                hacia=(0, 0, -1))
        mb.cara([(xa, yb, zb), (xb, yb, zb), (xb, yb, zs), (xa, yb, zs)], mf,
                hacia=(0, 1, 0))


def _pared(mb, x0, x1, z0, z1, y, huecos, m_pared, n_arc=10):
    """Pano de pared con huecos (rectangulares o de medio punto)."""
    x = x0
    for h in sorted(huecos, key=lambda q: q['xc']):
        xa = h['xc'] - h['w'] / 2.0
        xb = h['xc'] + h['w'] / 2.0
        if xa > x + 1e-6:
            mb.cara([(x, y, z0), (xa, y, z0), (xa, y, z1), (x, y, z1)],
                    m_pared, hacia=(0, 1, 0))
        if h['zb'] > z0 + 1e-6:
            mb.cara([(xa, y, z0), (xb, y, z0), (xb, y, h['zb']), (xa, y, h['zb'])],
                    m_pared, hacia=(0, 1, 0))
        if h.get('arco'):
            pts = _arco_pts(h['xc'], h['zs'], h['w'] / 2.0, n_arc)
            for k in range(n_arc):
                (ax, az), (bx, bz) = pts[k], pts[k + 1]
                mb.cara([(ax, y, az), (ax, y, z1), (bx, y, z1), (bx, y, bz)],
                        m_pared, hacia=(0, 1, 0))
        elif z1 > h['zs'] + 1e-6:
            mb.cara([(xa, y, h['zs']), (xb, y, h['zs']), (xb, y, z1), (xa, y, z1)],
                    m_pared, hacia=(0, 1, 0))
        _hueco(mb, h, y, n_arc)
        x = xb
    if x1 > x + 1e-6:
        mb.cara([(x, y, z0), (x1, y, z0), (x1, y, z1), (x, y, z1)], m_pared,
                hacia=(0, 1, 0))


def _arquivolta(mb, xc, zs, r, banda, y, sal, mat, n_arc, clave=True,
                labio=True):
    """Rosca de dovelas resaltada `sal` alrededor de un arco + clave."""
    pi_ = _arco_pts(xc, zs, r, n_arc)
    po = _arco_pts(xc, zs, r + banda, n_arc)
    yf = y + sal
    for k in range(n_arc):
        (ax, az), (bx, bz) = pi_[k], pi_[k + 1]
        (cx, cz), (dx, dz) = po[k], po[k + 1]
        mb.cara([(ax, yf, az), (cx, yf, cz), (dx, yf, dz), (bx, yf, bz)], mat,
                hacia=(0, 1, 0))
        mb.cara([(cx, yf, cz), (cx, y, cz), (dx, y, dz), (dx, yf, dz)], mat,
                hacia=((cx + dx) / 2.0 - xc, 0.0, (cz + dz) / 2.0 - zs))
        if labio:
            mb.cara([(ax, yf, az), (ax, y, az), (bx, y, bz), (bx, yf, bz)], mat,
                    hacia=(xc - (ax + bx) / 2.0, 0.0, zs - (az + bz) / 2.0))
    if clave:
        kw = max(0.34, banda * 1.05)
        mb.caja2(xc - kw / 2.0, xc + kw / 2.0, y, y + sal + 0.07,
                 zs + r - 0.04, zs + r + banda + 0.14, mat, sin=('-y',))


# ------------------------------------------------------------ piezas menores

def _farola_globos(mb, base, alto, brazos=0, eje=(1.0, 0.0), r_globo=0.26):
    """Farola de fundicion verde: basa torneada, fuste, globo superior y
    `brazos` (0 o 2) laterales con globo a lo largo de `eje`."""
    bx, by, bz = base
    mb.revolucion(base, [(0.20, 0.0), (0.20, 0.10), (0.13, 0.18), (0.11, 0.55),
                         (0.15, 0.62), (0.075, 0.72), (0.055, alto - 0.18),
                         (0.11, alto - 0.12), (0.11, alto - 0.04)],
                  'farola_verde', n=6, suave=True, tapa_sup=True)
    mb.esfera((bx, by, bz + alto + r_globo * 0.82), r_globo, 'globo',
              nseg=8, nan=5)
    if brazos:
        ex, ey = eje
        z_b = bz + alto * 0.74
        for sg in (-1.0, 1.0):
            pts = []
            for k in range(5):
                th = (math.pi / 2.0) * k / 4.0
                d = 0.78 * math.sin(th)
                pts.append((bx + sg * ex * d, by + sg * ey * d,
                            z_b + 0.42 * (1.0 - math.cos(th))))
            mb.tubo(pts, 0.035, 'farola_verde', n=5, tapas=False)
            fx, fy, fz = pts[-1]
            mb.revolucion((fx, fy, fz), [(0.035, -0.02), (0.10, 0.04), (0.10, 0.09)],
                          'farola_verde', n=6, tapa_sup=True)
            mb.esfera((fx, fy, fz + 0.09 + r_globo * 0.72), r_globo * 0.86,
                      'globo', nseg=8, nan=5)


def _fronda(mb, origen, az, largo, sube, mat, nseg=4, ancho=0.36):
    ox, oy, oz = origen
    ca, sa = math.cos(az), math.sin(az)
    esp = []
    for i in range(nseg + 1):
        s = i / nseg
        h = largo * s * (1.0 - 0.12 * s)
        z = largo * (sube * s - 1.15 * s * s) + 0.10
        w = ancho * (math.sin(math.pi * (0.14 + 0.86 * s)) ** 0.8) + 0.025
        esp.append(((ox + ca * h, oy + sa * h, oz + z), w))
    for i in range(nseg):
        (p0, w0), (p1, w1) = esp[i], esp[i + 1]
        l0 = (p0[0] - sa * w0, p0[1] + ca * w0, p0[2] - 0.5 * w0)
        l1 = (p1[0] - sa * w1, p1[1] + ca * w1, p1[2] - 0.5 * w1)
        r0 = (p0[0] + sa * w0, p0[1] - ca * w0, p0[2] - 0.5 * w0)
        r1 = (p1[0] + sa * w1, p1[1] - ca * w1, p1[2] - 0.5 * w1)
        mb.cara([p0, p1, l1, l0], mat, hacia=(0, 0, 1), doble=True)
        mb.cara([p0, r0, r1, p1], mat, hacia=(0, 0, 1), doble=True)


def _palmera(mb, base, alto, rng, n_hojas=8, largo=1.9):
    bx, by, bz = base
    az = rng.uniform(0.0, TAU)
    lean = rng.uniform(0.18, 0.38)
    pts, radios = [], []
    ns = 5
    for i in range(ns + 1):
        t = i / ns
        pts.append((bx + lean * t * t * math.cos(az),
                    by + lean * t * t * math.sin(az), bz + alto * t))
        radios.append(0.18 - 0.07 * t + (0.06 if i == 0 else 0.0))
    mb.tubo(pts, radios, 'tronco_palma', n=6, tapas=False)
    top = pts[-1]
    mb.esfera((top[0], top[1], top[2] + 0.04), 0.25, 'tronco_palma', nseg=6,
              nan=4, escala_z=1.2)
    for k in range(n_hojas):
        a = TAU * k / n_hojas + rng.uniform(-0.22, 0.22)
        _fronda(mb, (top[0], top[1], top[2] + 0.12), a,
                largo * rng.uniform(0.85, 1.12),
                rng.uniform(0.35, 0.95) if k % 3 else rng.uniform(1.0, 1.3),
                'hoja_palma')


def _adelfa(mb, centro, r, rng, n_flores=7):
    cx, cy, cz = centro
    bolas = [(0.0, 0.0, 0.0, 1.0)]
    for _ in range(2):
        a = rng.uniform(0.0, TAU)
        bolas.append((0.55 * r * math.cos(a), 0.55 * r * math.sin(a),
                      -0.12 * r, rng.uniform(0.62, 0.78)))
    for dx, dy, dz, k in bolas:
        mb.esfera((cx + dx, cy + dy, cz + dz + r * k * 0.75), r * k,
                  'hoja_adelfa', nseg=6, nan=3, escala_z=0.85)
    for _ in range(n_flores):
        a = rng.uniform(0.0, TAU)
        el = rng.uniform(0.25, 1.25)
        rr = r * 0.98
        fx = cx + rr * math.cos(a) * math.sin(el)
        fy = cy + rr * math.sin(a) * math.sin(el)
        fz = cz + r * 0.75 + rr * 0.85 * math.cos(el)
        mb.esfera((fx, fy, fz), 0.11, 'flor_rosa', nseg=4, nan=2, suave=False)


# ================================================================== APARCAMIENTO

def _dims_parking(ancho, fondo, alto):
    """Normaliza las dimensiones (compartido por geometria y plazas)."""
    return max(8.0, float(ancho)), max(8.0, float(fondo)), max(4.5, float(alto))


def _layout_parking(ancho, fondo):
    """Distribucion de la azotea (compartida por geometria y plazas)."""
    A, F = ancho / 2.0, fondo / 2.0
    gx = A - _PETO_G - 0.25
    gy = F - _PETO_G - 0.25
    rampa = ancho >= 16.0 and fondo >= 13.0
    lay = {'A': A, 'F': F, 'gx': gx, 'gy': gy, 'rampa': rampa}
    if rampa:
        px0 = -A + _PETO_G
        px1 = px0 + _POZO_ANCHO
        py0 = -F + _PETO_G + 0.9
        py1 = gy - _PLAZA_FONDO - 0.2
        lay.update(px0=px0, px1=px1, py0=py0, py1=py1,
                   caida=min(2.7, 0.30 * (py1 - py0)))
        xb0 = px1 + _MURETE_G + 0.8
    else:
        xb0 = -gx
    xb1 = gx
    span = xb1 - xb0
    # plazas holgadas en grupos de 3 separados por isletas cebreadas
    if span >= _GRUPO * 3.0:
        ng = max(1, int((span + _ISLETA) / (_GRUPO * _PLAZA_ANCHO + _ISLETA) + 1e-6))
        w = min(_PLAZA_ANCHO_MAX, (span - (ng - 1) * _ISLETA) / (ng * _GRUPO))
        grupos_n = [_GRUPO] * ng
    else:
        n1 = max(1, int(span / _PLAZA_ANCHO_MIN + 1e-6))
        w = min(_PLAZA_ANCHO_MAX, span / n1)
        grupos_n = [n1]
    bloque = sum(grupos_n) * w + (len(grupos_n) - 1) * _ISLETA
    x = xb0 + (span - bloque) / 2.0
    grupos, isletas, xs = [], [], []
    for ig, n in enumerate(grupos_n):
        grupos.append((x, x + n * w, n))
        for k in range(n):
            xs.append(x + w * (k + 0.5))
        x += n * w
        if ig < len(grupos_n) - 1:
            isletas.append((x, x + _ISLETA))
            x += _ISLETA
    # filas (fila 0 = la de la calle, pegada al peto +Y) y pasillos
    D = 2.0 * gy
    nf = 1
    while (nf + 1) * _PLAZA_FONDO + math.ceil((nf + 1) / 2.0) * _PASILLO_MIN <= D + 1e-6:
        nf += 1
    npas = int(math.ceil(nf / 2.0))
    pasillo = max(0.0, (D - nf * _PLAZA_FONDO) / npas)
    filas, pasillos = [], []
    y = gy
    for i in range(nf):
        filas.append((y - _PLAZA_FONDO, y))
        y -= _PLAZA_FONDO
        if i % 2 == 0:
            pasillos.append((y - pasillo, y))
            y -= pasillo
    lay.update(xb0=xb0, xb1=xb1, w=w, xs=xs, grupos=grupos, isletas=isletas,
               filas=filas, pasillos=pasillos, bloque=(grupos[0][0], grupos[-1][1]))
    # dos farolas finas: en las isletas de las dos primeras filas (o junto al
    # peto trasero si no hay isletas)
    far = []
    if isletas:
        xi = (isletas[len(isletas) // 2][0] + isletas[len(isletas) // 2][1]) / 2.0
        for (ya, yb) in filas[:2]:
            far.append((xi, (ya + yb) / 2.0))
        if len(far) == 1:
            far.append((xi, -gy + 0.2))
    else:
        far = [(-A * 0.5, -gy + 0.15), (A * 0.5, -gy + 0.15)]
    lay['farolas'] = far
    return lay


def plazas_parking(ancho=40.0, fondo=18.0, alto=20.0):
    """Transformaciones (x, y, z, rot_z) de cada plaza de la azotea en
    coordenadas locales del edificio. rot_z = 0 -> frontal del coche a +Y."""
    ancho, fondo, alto = _dims_parking(ancho, fondo, alto)
    lay = _layout_parking(ancho, fondo)
    res = []
    for (ya, yb) in lay['filas']:
        for x in lay['xs']:
            res.append((round(x, 4), round((ya + yb) / 2.0, 4), alto, 0.0))
    return res


def _niveles_palazzo(alto):
    """Cotas del alzado neoclasico: planta baja almohadillada, imposta,
    plantas nobles con orden gigante, entablamento con cornisa volada, atico
    de lunetos y peto."""
    atico = alto >= 11.0
    ha = min(3.2, max(2.2, 0.16 * alto)) if atico else 0.0
    hc = 0.8 if atico else 0.55
    hf = 0.9 if atico else 0.5
    z_cor1 = alto - ha
    z_cor0 = z_cor1 - hc
    z_fri0 = z_cor0 - hf
    hg = min(5.6, max(3.4, 0.27 * alto))
    pisos = []
    if z_fri0 - (hg + 0.35) >= 3.0:
        z_imp0, z_imp1 = hg, hg + 0.35
        libre = z_fri0 - z_imp1
        n_up = max(1, int(round(libre / 4.6)))
        fh = libre / n_up
        for i in range(n_up):
            z0 = z_imp1 + fh * i
            hv = max(1.2, min(3.0, fh - 1.7) if i == 0 else min(2.4, fh - 1.9))
            zb = z0 + max(0.55, (fh - hv) * (0.42 if i == 0 else 0.40))
            pisos.append({'z0': z0, 'z1': z0 + fh, 'zb': zb, 'zt': zb + hv,
                          'noble': i == 0})
    else:
        z_imp0 = z_imp1 = z_fri0
    util = ha - 0.30
    r_l = min(0.85, 0.42 * util) if atico else 0.0
    return {'alto': alto, 'atico': atico, 'z_zoc': 0.9, 'z_imp0': z_imp0,
            'z_imp1': z_imp1, 'z_fri0': z_fri0, 'z_cor0': z_cor0,
            'z_cor1': z_cor1, 'hc': hc, 'pisos': pisos, 'r_l': r_l,
            'zs_l': z_cor1 + (util - r_l) / 2.0 - 0.05}


def _fronton(mb, xc, w, z0, h, y, sal, mat):
    """Fronton triangular macizo sobre una ventana noble."""
    xa, xb = xc - w / 2.0, xc + w / 2.0
    yf = y + sal
    mb.cara([(xa, yf, z0), (xb, yf, z0), (xc, yf, z0 + h)], mat, hacia=(0, 1, 0))
    mb.cara([(xa, y, z0), (xa, yf, z0), (xc, yf, z0 + h), (xc, y, z0 + h)], mat,
            hacia=(-h, 0.0, w / 2.0))
    mb.cara([(xb, y, z0), (xb, yf, z0), (xc, yf, z0 + h), (xc, y, z0 + h)], mat,
            hacia=(h, 0.0, w / 2.0))
    mb.cara([(xa, y, z0), (xb, y, z0), (xb, yf, z0), (xa, yf, z0)], mat,
            hacia=(0, 0, -1))


def _luneto(mb, xc, zs, r, y, mat_marco, n=6, marco=True):
    """Ventana semicircular del atico (vidrio + rosca + alfeizar + parteluz),
    aplicada sobre el pano sin recortarlo."""
    pts = _arco_pts(xc, zs, r, n)
    mb.cara([(px, y + _DESPEGUE, pz) for px, pz in pts], 'ventana',
            hacia=(0, 1, 0))
    if not marco:
        return
    po = _arco_pts(xc, zs, r + 0.17, n)
    yf = y + 2.0 * _DESPEGUE
    for k in range(n):
        (ax, az), (bx, bz) = pts[k], pts[k + 1]
        (cx_, cz), (dx, dz) = po[k], po[k + 1]
        mb.cara([(ax, yf, az), (cx_, yf, cz), (dx, yf, dz), (bx, yf, bz)],
                mat_marco, hacia=(0, 1, 0))
    mb.caja2(xc - r - 0.30, xc + r + 0.30, y, y + 0.15, zs - 0.17, zs, mat_marco,
             sin=('-y',))
    mb.cara([(xc - 0.04, yf, zs), (xc + 0.04, yf, zs),
             (xc + 0.04, yf, zs + r), (xc - 0.04, yf, zs + r)],
            mat_marco, hacia=(0, 1, 0))


def _fachada_palazzo(W, off, esquinas, niv, mats, det, entrada=False):
    """Fachada canonica del palazzo (mirando a +Y en y=off, ancho W centrado
    en x=0). mats = (muro, base, realce). det: nivel de detalle. Devuelve
    (_MB, centros_de_vano, ancho_de_vano)."""
    mb = _MB()
    muro, base, trim = mats
    alto = niv['alto']
    e = 1.0 if esquinas else 0.0
    nb = max(1, int(round((W - 2.0 * _ESQ) / det.get('paso', 4.2))))
    bw = (W - 2.0 * _ESQ) / nb
    cx = [-W / 2.0 + _ESQ + bw * (i + 0.5) for i in range(nb)]
    xk = [-W / 2.0 + _ESQ + bw * k for k in range(1, nb)]
    n_arc = det.get('n_arc', 8)
    orn = det.get('ornamento', True)

    # ---- planta baja almohadillada con arcos
    z_pb = niv['z_imp0']
    w_arc = min(2.6, bw - 1.5, 2.0 * (z_pb - 0.85 - 1.2))
    huecos = []
    zs_arc = z_pb
    if w_arc >= 0.9:
        zs_arc = z_pb - 0.85 - w_arc / 2.0
        for i, xc in enumerate(cx):
            if entrada and i == 0 and bw >= 3.9:
                w_e = min(3.2, bw - 0.9, 2.0 * (z_pb - 0.62 - 1.5))
                huecos.append({'xc': xc, 'w': w_e, 'zb': 0.0,
                               'zs': z_pb - 0.62 - w_e / 2.0, 'arco': True,
                               'prof': 3.0, 'm_jamba': 'hormigon',
                               'm_fondo': 'hueco_oscuro', 'suelo': False,
                               'entrada': True})
            else:
                huecos.append({'xc': xc, 'w': w_arc, 'zb': 0.0, 'zs': zs_arc,
                               'arco': True, 'prof': det.get('prof_arco', 0.5),
                               'm_jamba': base, 'm_fondo': 'vidrio_portal',
                               'suelo': False})
    _pared(mb, -W / 2.0, W / 2.0, 0.0, z_pb, off, huecos, base, n_arc)
    # zocalo y llagas del almohadillado en los machones entre arcos
    x = -W / 2.0 + _ESQ
    tramos = []
    for h in huecos + [None]:
        xa = (W / 2.0 - _ESQ) if h is None else h['xc'] - h['w'] / 2.0
        if xa > x + 0.05:
            tramos.append((x, xa))
        if h is not None:
            x = h['xc'] + h['w'] / 2.0
    for xa, xb in tramos:
        if det.get('zocalo', True):
            mb.caja2(xa, xb, off, off + 0.10, 0.0, niv['z_zoc'], 'piedra_zocalo',
                     sin=('-y', '-z'))
        if det.get('llagas', True):
            zl = niv['z_zoc'] + 0.65
            yl = off + _DESPEGUE
            while zl < zs_arc - 0.05:
                mb.cara([(xa, yl, zl), (xb, yl, zl), (xb, yl, zl + 0.08),
                         (xa, yl, zl + 0.08)],
                        'piedra_palazzo_llaga', hacia=(0, 1, 0))
                zl += det.get('paso_llaga', 0.65)
    if det.get('llagas', True) and huecos:
        zl = z_pb - 0.30
        yl = off + _DESPEGUE
        mb.cara([(-W / 2.0 + _ESQ, yl, zl), (W / 2.0 - _ESQ, yl, zl),
                 (W / 2.0 - _ESQ, yl, zl + 0.08),
                 (-W / 2.0 + _ESQ, yl, zl + 0.08)],
                'piedra_palazzo_llaga', hacia=(0, 1, 0))
    for h in huecos:
        if h.get('entrada'):
            xa, xb = h['xc'] - h['w'] / 2.0, h['xc'] + h['w'] / 2.0
            # arranque de la rampa interior visible desde la calle
            mb.cara([(xa, off, 0.015), (xb, off, 0.015), (xb, off - 3.0, 1.0),
                     (xa, off - 3.0, 1.0)], 'asfalto', hacia=(0, 0, 1))
        if det.get('arquivoltas', True):
            _arquivolta(mb, h['xc'], h['zs'], h['w'] / 2.0, 0.28, off, 0.08,
                        trim, n_arc, clave=det.get('claves', True), labio=False)

    # ---- imposta + plantas nobles (ventanas altas y estrechas, orden gigante)
    if niv['pisos']:
        mb.caja2(-W / 2.0 - 0.16 * e, W / 2.0 + 0.16 * e, off, off + 0.16,
                 niv['z_imp0'], niv['z_imp1'], trim, sin=('-y',))
        wv = min(1.35, bw - 1.9)
        for p in niv['pisos']:
            zb, zt = p['zb'], p['zt']
            vent = []
            if wv >= 0.7:
                vent = [{'xc': xc, 'w': wv, 'zb': zb, 'zs': zt, 'arco': False,
                         'prof': 0.18, 'm_jamba': trim, 'm_fondo': 'ventana'}
                        for xc in cx]
            _pared(mb, -W / 2.0, W / 2.0, p['z0'], p['z1'], off, vent, muro)
            for xc in (cx if vent else ()):
                xa, xb = xc - wv / 2.0, xc + wv / 2.0
                if orn:
                    mb.caja2(xa - 0.22, xb + 0.22, off, off + 0.16, zb - 0.18, zb,
                             trim, sin=('-y',))
                    if p['noble'] and det.get('frontones', True):
                        mb.caja2(xa - 0.18, xb + 0.18, off, off + 0.10, zt + 0.06,
                                 zt + 0.28, trim, sin=('-y', '+z'))
                        _fronton(mb, xc, wv + 0.78, zt + 0.28, 0.50, off, 0.20,
                                 trim)
                    else:
                        mb.caja2(xa - 0.24, xb + 0.24, off, off + 0.14, zt + 0.06,
                                 zt + 0.30, trim, sin=('-y',))
                if det.get('parteluz', False):
                    yv = off - 0.18 + _DESPEGUE
                    zc = zb + (zt - zb) * 0.66
                    mb.cara([(xc - 0.04, yv, zb), (xc + 0.04, yv, zb),
                             (xc + 0.04, yv, zt), (xc - 0.04, yv, zt)], trim,
                            hacia=(0, 1, 0))
                    mb.cara([(xa, yv, zc - 0.04), (xb, yv, zc - 0.04),
                             (xb, yv, zc + 0.04), (xa, yv, zc + 0.04)], trim,
                            hacia=(0, 1, 0))
        if det.get('pilastras', True):
            z0p, z1p = niv['z_imp1'], niv['z_fri0']
            pw = 0.78
            for x in xk:
                if orn:
                    mb.caja2(x - pw / 2 - 0.10, x + pw / 2 + 0.10, off, off + 0.24,
                             z0p, z0p + 0.45, trim, sin=('-y', '-z'))
                    mb.caja2(x - pw / 2, x + pw / 2, off, off + 0.16, z0p + 0.45,
                             z1p - 0.45, trim, sin=('-y', '-z', '+z'))
                    mb.caja2(x - pw / 2 - 0.12, x + pw / 2 + 0.12, off, off + 0.26,
                             z1p - 0.45, z1p, trim, sin=('-y', '+z'))
                else:
                    mb.caja2(x - pw / 2, x + pw / 2, off, off + 0.16, z0p, z1p,
                             trim, sin=('-y', '-z', '+z'))

    # ---- entablamento: friso, talon, modillones y cornisa muy volada
    s = niv['hc'] / 0.8
    z_f0, z_c0, z_c1 = niv['z_fri0'], niv['z_cor0'], niv['z_cor1']
    zb2 = z_c0 + 0.47 * s
    mb.caja2(-W / 2.0 - 0.10 * e, W / 2.0 + 0.10 * e, off, off + 0.10, z_f0, z_c0,
             trim, sin=('-y', '+z'))
    mb.caja2(-W / 2.0 - 0.30 * e, W / 2.0 + 0.30 * e, off, off + 0.30, z_c0, zb2,
             trim, sin=('-y', '+z'))
    if det.get('modillones', True):
        for k in range(2 * nb + 1):
            xm = -W / 2.0 + _ESQ + bw * 0.5 * k
            mb.caja2(xm - 0.16, xm + 0.16, off + 0.30, off + 0.30 + 0.56 * s,
                     z_c0 + 0.20 * s, zb2, trim, sin=('-y', '+z'))
    vc = 0.95 * s
    mb.caja2(-W / 2.0 - vc * e, W / 2.0 + vc * e, off, off + vc, zb2, z_c1, trim,
             sin=('-y',))

    # ---- atico de lunetos entre machones + cornisilla de la azotea
    if niv['atico']:
        mb.cara([(-W / 2.0, off, z_c1), (W / 2.0, off, z_c1), (W / 2.0, off, alto),
                 (-W / 2.0, off, alto)], muro, hacia=(0, 1, 0))
        z_a1 = alto - 0.30
        if det.get('pilastras', True):
            for x in xk:
                mb.caja2(x - 0.50, x + 0.50, off, off + 0.12, z_c1, z_a1, trim,
                         sin=('-y', '-z', '+z'))
        r_l = min(niv['r_l'], bw / 2.0 - 0.9)
        if r_l >= 0.35:
            for xc in cx:
                _luneto(mb, xc, niv['zs_l'], r_l, off, trim,
                        n=det.get('n_luneto', 6), marco=orn)
        mb.caja2(-W / 2.0 - 0.28 * e, W / 2.0 + 0.28 * e, off, off + 0.28, z_a1,
                 alto, trim, sin=('-y',))
    return mb, cx, bw


def _peto_azotea(mb, W, off, esquinas, alto):
    """Peto macizo blanco de 1.2 m con albardilla (marco canonico)."""
    g = _PETO_G
    x0 = -W / 2.0 if esquinas else -W / 2.0 + g
    x1 = -x0
    testas = () if esquinas else ('-x', '+x')
    mb.caja2(x0, x1, off - g, off, alto, alto + _PETO_H, 'piedra_blanca',
             sin=('-z', '+z') + testas)
    v = 0.07
    ve = v if esquinas else -v
    mb.caja2(x0 - ve, x1 + ve, off - g - v, off + v, alto + _PETO_H,
             alto + _PETO_H + _PETO_ALB, 'piedra_blanca', sin=testas)


def _barandilla_peto(mb, W, off, z_top, paso=5.6):
    """Pasamanos de hierro OPCIONAL sobre la albardilla (marco canonico). En
    la pelicula el peto es macizo y sin barandilla, asi que por defecto no se
    construye; seccion de 10 cm para que no haga aliasing a distancia."""
    yc = off - _PETO_G / 2.0
    xr0, xr1 = -W / 2.0 + _PETO_G / 2.0, W / 2.0 - _PETO_G / 2.0
    mb.caja2(xr0, xr1, yc - 0.05, yc + 0.05, z_top + 0.26, z_top + 0.36,
             'hierro', sin=('-x', '+x'))
    npost = max(1, int(math.ceil((xr1 - xr0) / paso)))
    for k in range(npost):
        xp = xr0 + (xr1 - xr0) * k / npost
        mb.caja2(xp - 0.045, xp + 0.045, yc - 0.045, yc + 0.045, z_top,
                 z_top + 0.26, 'hierro', sin=('-z', '+z'))


def _toldo(mb, x0, x1, y_pared, z_pared, vuelo, caida, mats, franja=0.62):
    n = max(2, int(round((x1 - x0) / franja)))
    yf = y_pared + vuelo
    zf = z_pared - caida
    for i in range(n):
        xa = x0 + (x1 - x0) * i / n
        xb = x0 + (x1 - x0) * (i + 1) / n
        m = mats[i % 2]
        mb.cara([(xa, y_pared, z_pared), (xb, y_pared, z_pared), (xb, yf, zf),
                 (xa, yf, zf)], m, hacia=(0, 0, 1))
        xm = (xa + xb) / 2.0
        mb.cara([(xa, yf, zf), (xb, yf, zf), (xb, yf, zf - 0.22),
                 (xm, yf, zf - 0.36), (xa, yf, zf - 0.22)], m, hacia=(0, 1, 0),
                doble=True)
    # cara inferior y faldones laterales
    mb.cara([(x0, y_pared, z_pared - 0.012), (x1, y_pared, z_pared - 0.012),
             (x1, yf, zf - 0.012), (x0, yf, zf - 0.012)], mats[1],
            hacia=(0, 0, -1))
    for xs, m in ((x0, mats[0]), (x1, mats[(n - 1) % 2])):
        mb.cara([(xs, y_pared, z_pared), (xs, yf, zf), (xs, yf, zf - 0.22),
                 (xs, y_pared, zf - 0.22)], m, hacia=(xs - (x0 + x1) / 2.0, 0, 0),
                doble=True)
    # brazos de hierro
    for xs in (x0 + 0.04, x1 - 0.04):
        mb.caja2(xs - 0.03, xs + 0.03, y_pared, yf, zf - 0.27, zf - 0.21,
                 'hierro', sin=('-y',))


def _cartel_p(mb, x, y0, zc, lado=1.3):
    """Cartel "P" en banderola perpendicular a la fachada +Y."""
    k = lado
    yc = y0 + 0.30 + lado / 2.0
    mb.caja((x, yc, zc), (0.08, lado, lado), 'cartel_azul')
    mb.caja((x, yc, zc), (0.11, lado + 0.12, lado + 0.12), 'linea_blanca',
            sin=('-x', '+x'))
    for dz in (0.33 * k, -0.33 * k):
        mb.caja2(x - 0.025, x + 0.025, y0, y0 + 0.32, zc + dz - 0.03,
                 zc + dz + 0.03, 'hierro', sin=('-y', '+y'))
    # glifo P por las dos caras (a = coordenada horizontal en el plano)
    trazos = ((-0.20, -0.05, -0.33, 0.33), (-0.05, 0.22, 0.20, 0.33),
              (-0.05, 0.22, -0.06, 0.07), (0.09, 0.22, 0.07, 0.20))
    for cara_x in (1.0, -1.0):
        # 2.5 cm por delante de la cara azul (media caja 0.04) y 1 cm por
        # delante del marco blanco (media caja 0.055): sin z-fighting en AC
        xs = x + cara_x * 0.065
        for a0, a1, z0, z1 in trazos:
            ya, yb = yc + cara_x * a0 * k, yc + cara_x * a1 * k
            mb.cara([(xs, ya, zc + z0 * k), (xs, yb, zc + z0 * k),
                     (xs, yb, zc + z1 * k), (xs, ya, zc + z1 * k)],
                    'linea_blanca', hacia=(cara_x, 0, 0))


def _bandera(mb, base, alto_mastil, largo=1.9, alto_b=1.2):
    bx, by, bz = base
    mb.revolucion(base, [(0.06, 0.0), (0.035, alto_mastil)], 'linea_blanca',
                  n=5, tapa_sup=True)
    z1 = bz + alto_mastil - 0.08
    z0 = z1 - alto_b
    cols = ('bandera_verde', 'linea_blanca', 'toldo_rojo')
    onda = (0.0, 0.12, -0.07, 0.14)
    for i in range(3):
        xa = bx + 0.03 + largo * i / 3.0
        xb = bx + 0.03 + largo * (i + 1) / 3.0
        mb.cara([(xa, by + onda[i], z0 - 0.03 * i),
                 (xb, by + onda[i + 1], z0 - 0.03 * (i + 1)),
                 (xb, by + onda[i + 1], z1 - 0.03 * (i + 1)),
                 (xa, by + onda[i], z1 - 0.03 * i)],
                cols[i], doble=True)


def _farola_fina(mb, base, alto=5.4, rz=0.0):
    """Farola fina de azotea: fuste esbelto, cruceta y dos luminarias."""
    bx, by, bz = base
    mb.caja((bx, by, bz + 0.11), (0.62, 0.62, 0.22), 'hormigon', sin=('-z',))
    mb.revolucion((bx, by, bz + 0.22), [(0.12, 0.0), (0.12, 0.40), (0.06, 0.55),
                                        (0.045, alto - 0.22)],
                  'hierro', n=5, suave=True, tapa_sup=True)
    zc = bz + alto - 0.10
    mb.caja((bx, by, zc), (1.7, 0.07, 0.07), 'hierro', rz=rz, sin=('-x', '+x'))
    c, s = math.cos(rz), math.sin(rz)
    for sg in (-1.0, 1.0):
        hx, hy = bx + sg * 0.80 * c, by + sg * 0.80 * s
        mb.caja((hx, hy, zc - 0.02), (0.62, 0.30, 0.14), 'hierro', rz=rz,
                sin=('-z',))
        dx, dy = 0.31, 0.15
        esq = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
        mb.cara([(hx + ex * c - ey * s, hy + ex * s + ey * c, zc - 0.09)
                 for ex, ey in esq], 'globo', hacia=(0, 0, -1))


def _cebra(cu, x0, x1, y0, y1, zl, mat='linea_amarilla'):
    """Isleta cebreada (franjas diagonales + recerco)."""
    desl = min(1.0, (x1 - x0) * 0.35)
    wd = 0.28
    nst = max(2, int((x1 - x0 - desl - wd) / 0.62) + 1)
    for k in range(nst):
        xs = x0 + k * (x1 - x0 - desl - wd) / max(1, nst - 1)
        cu.cara([(xs, y0, zl), (xs + wd, y0, zl), (xs + wd + desl, y1, zl),
                 (xs + desl, y1, zl)], mat, hacia=(0, 0, 1))
    for (xa_, xb_, ya_, yb_) in ((x0 - 0.12, x1 + 0.12, y0 - 0.12, y0),
                                 (x0 - 0.12, x1 + 0.12, y1, y1 + 0.12),
                                 (x0 - 0.12, x0, y0, y1),
                                 (x1, x1 + 0.12, y0, y1)):
        cu.cara([(xa_, ya_, zl), (xb_, ya_, zl), (xb_, yb_, zl), (xa_, yb_, zl)],
                mat, hacia=(0, 0, 1))


def build_parking_terraza(parent_collection, ancho=40.0, fondo=18.0, alto=20.0,
                          seed=0, **params):
    """Palazzo neoclasico con aparcamiento en la azotea (ver docstring del
    modulo). Devuelve el Empty raiz MIRADOR_parking."""
    col = parent_collection
    ancho, fondo, alto = _dims_parking(ancho, fondo, alto)
    rng = random.Random(seed)
    lay = _layout_parking(ancho, fondo)
    niv = _niveles_palazzo(alto)
    # la piedra gris-rosada de la pelicula es el rasgo identificativo del
    # edificio: se usa SIEMPRE salvo que se pida otra con piedra='<clave>'
    muro = params.get('piedra') or 'piedra_palazzo'
    if muro not in _PALETA:
        muro = 'piedra_palazzo'
    mats = (muro, 'piedra_palazzo_base', 'piedra_palazzo_clara')
    color_toldo = params.get('color_toldo') or ('rojo', 'verde')[int(seed) % 2]
    toldo_m = (('toldo_verde', 'toldo_crema') if color_toldo == 'verde'
               else ('toldo_rojo', 'toldo_crema'))
    trasera = params.get('trasera', 'simple')
    tope = params.get('tope_tris', TOPE_PARKING)
    mastiles = [4.2 + rng.uniform(-0.15, 0.15) for _ in range(2)]
    raiz = _raiz('%s_parking' % PRE, col, 2.0)

    cu = _cubierta_parking(ancho, fondo, alto, lay)
    # degradacion automatica de detalle: se sube de nivel hasta caber en el tope
    lod = 0
    while True:
        ed, cx_fr, bw_fr = _edificio_parking(ancho, fondo, alto, lay, niv, mats,
                                             _detalle_parking(lod, trasera))
        de = _detalles_parking(ancho, fondo, alto, lay, niv, cx_fr, bw_fr,
                               toldo_m, mastiles, params)
        total = ed.tris() + cu.tris() + de.tris()
        if tope is None or total <= tope or lod >= _LOD_PARKING_MAX:
            break
        lod += 1
    if tope is not None and total > tope:
        print('AVISO %s_parking %gx%gx%g: %d tris > tope %d incluso con el '
              'detalle minimo' % (PRE, ancho, fondo, alto, total, tope))
    ed.obj('%s_parking_edificio' % PRE, col, raiz)
    cu.obj('%s_parking_cubierta' % PRE, col, raiz)
    de.obj('%s_parking_detalles' % PRE, col, raiz)
    raiz['mirador_lod'] = lod
    raiz['mirador_tris'] = total
    return raiz


def _detalle_parking(lod, trasera='simple'):
    """Nivel de detalle (frente, lados, trasera) del palazzo. lod 0 = completo
    (el de los tamanos por defecto); cada nivel recorta ornamento y, a partir
    del 3, ensancha el paso de los vanos, para que edificios mas grandes que
    ~44 x 20 m sigan cabiendo en TOPE_PARKING."""
    fr = {'n_arc': 8, 'parteluz': True}
    la = {'n_arc': 6, 'claves': False}
    if trasera == 'completa':
        tr = dict(la)
    else:
        # mismo ritmo de vanos que el frente (pilastras y lunetos casan con
        # las esquinas y los laterales) pero sin ornamento
        tr = {'n_arc': 6, 'arquivoltas': False, 'ornamento': False,
              'modillones': False, 'llagas': False, 'prof_arco': 0.3}
    if lod >= 1:
        fr.update(parteluz=False)
        la.update(modillones=False, paso_llaga=1.3)
        tr.update(modillones=False, paso_llaga=1.3)
    if lod >= 2:
        fr.update(n_arc=6, paso_llaga=1.3)
        la.update(ornamento=False, llagas=False)
        tr.update(ornamento=False, llagas=False, arquivoltas=False)
    if lod >= 3:
        fr.update(modillones=False, frontones=False)
        for d in (fr, la, tr):
            d.update(paso=5.2)
        la.update(arquivoltas=False, zocalo=False)
        tr.update(zocalo=False)
    if lod >= 4:
        fr.update(ornamento=False, llagas=False)
        for d in (fr, la, tr):
            d.update(paso=6.4)
        la.update(pilastras=False)
        tr.update(pilastras=False)
    if lod >= 5:
        fr.update(arquivoltas=False, zocalo=False, pilastras=False)
        for d in (fr, la, tr):
            d.update(paso=8.0)
    return fr, la, tr


def _edificio_parking(ancho, fondo, alto, lay, niv, mats, dets):
    """Malla del edificio (4 fachadas + machones de esquina). Devuelve
    (_MB, centros de vano del frente, ancho de vano del frente)."""
    A, F = ancho / 2.0, fondo / 2.0
    trim = mats[2]
    det_full, det_lado, det_tras = dets
    ed = _MB()
    fr, cx_fr, bw_fr = _fachada_palazzo(ancho, F, True, niv, mats, det_full,
                                        entrada=lay['rampa'])
    ed.anexar(fr, 0.0)
    tr, _, _ = _fachada_palazzo(ancho, F, True, niv, mats, det_tras)
    ed.anexar(tr, math.pi)
    for ang in (-math.pi / 2.0, math.pi / 2.0):
        ld, _, _ = _fachada_palazzo(fondo, A, False, niv, mats, det_lado)
        ed.anexar(ld, ang)
    # machones de esquina: almohadillado abajo, pilastron con capitel, atico
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            def esquina(sal, z0, z1, mat, sin):
                ed.caja2(sx * (A - _ESQ), sx * (A + sal), sy * (F - _ESQ),
                         sy * (F + sal), z0, z1, mat, sin=sin)
            esquina(0.10, 0.0, niv['z_imp0'], 'piedra_palazzo_base', ('-z', '+z'))
            if niv['pisos']:
                esquina(0.16, niv['z_imp1'], niv['z_fri0'] - 0.45, trim,
                        ('-z', '+z'))
                esquina(0.26, niv['z_fri0'] - 0.45, niv['z_fri0'], trim, ('+z',))
            if niv['atico']:
                esquina(0.12, niv['z_cor1'], alto - 0.30, trim, ('-z', '+z'))
    return ed, cx_fr, bw_fr


def _cubierta_parking(ancho, fondo, alto, lay):
    """Malla de la azotea: losa, pozo de rampa, plazas pintadas y peto."""
    A, F = ancho / 2.0, fondo / 2.0
    cu = _MB()
    z = alto
    losa = 'azotea_beige'
    if lay['rampa']:
        px0, px1, py0, py1 = lay['px0'], lay['px1'], lay['py0'], lay['py1']
        caida = lay['caida']
        cu.cara([(-A, -F, z), (px0, -F, z), (px0, F, z), (-A, F, z)], losa,
                hacia=(0, 0, 1))
        cu.cara([(px1, -F, z), (A, -F, z), (A, F, z), (px1, F, z)], losa,
                hacia=(0, 0, 1))
        cu.cara([(px0, -F, z), (px1, -F, z), (px1, py0, z), (px0, py0, z)],
                losa, hacia=(0, 0, 1))
        cu.cara([(px0, py1, z), (px1, py1, z), (px1, F, z), (px0, F, z)],
                losa, hacia=(0, 0, 1))
        # pozo de la rampa
        zr = z - caida
        cu.cara([(px0, py0, zr), (px1, py0, zr), (px1, py1, z), (px0, py1, z)],
                'hormigon', hacia=(0, 0, 1))
        cu.cara([(px0, py1, z), (px0, py0, z), (px0, py0, zr)], 'hormigon',
                hacia=(1, 0, 0))
        cu.cara([(px1, py1, z), (px1, py0, z), (px1, py0, zr)], 'hormigon',
                hacia=(-1, 0, 0))
        cu.cara([(px0, py0, z - 0.35), (px1, py0, z - 0.35), (px1, py0, z),
                 (px0, py0, z)], 'hormigon', hacia=(0, 1, 0))
        cu.cara([(px0, py0, zr), (px1, py0, zr), (px1, py0, z - 0.35),
                 (px0, py0, z - 0.35)], 'hueco_oscuro', hacia=(0, 1, 0))
        # lineas amarillas de borde de rampa + flecha de subida
        pend = caida / (py1 - py0)
        for xl in (px0 + 0.22, px1 - 0.36):
            cu.cara([(xl, py0, zr + _DESPEGUE), (xl + 0.14, py0, zr + _DESPEGUE),
                     (xl + 0.14, py1, z + _DESPEGUE), (xl, py1, z + _DESPEGUE)],
                    'linea_amarilla', hacia=(0, 0, 1))
        xm = (px0 + px1) / 2.0
        ya_f = py0 + (py1 - py0) * 0.45
        cu.cara([(p[0], p[1], zr + pend * (p[1] - py0) + _DESPEGUE)
                 for p in ((xm - 0.14, ya_f), (xm + 0.14, ya_f),
                           (xm + 0.14, ya_f + 1.6), (xm - 0.14, ya_f + 1.6))],
                'linea_blanca', hacia=(0, 0, 1))
        cu.cara([(p[0], p[1], zr + pend * (p[1] - py0) + _DESPEGUE)
                 for p in ((xm - 0.5, ya_f + 1.6), (xm + 0.5, ya_f + 1.6),
                           (xm, ya_f + 2.5))], 'linea_blanca', hacia=(0, 0, 1))
        # muretes del pozo (lado +X y testa -Y) con albardilla
        cu.caja2(px1, px1 + _MURETE_G, py0 - _MURETE_G, py1, z, z + 0.62,
                 'piedra_blanca', sin=('-z',))
        cu.caja2(px1 - 0.04, px1 + _MURETE_G + 0.04, py0 - _MURETE_G - 0.04,
                 py1 + 0.04, z + 0.62, z + 0.70, 'piedra_blanca')
        cu.caja2(px0, px1, py0 - _MURETE_G, py0, z, z + 0.62, 'piedra_blanca',
                 sin=('-z', '+x'))
        cu.caja2(px0, px1 - 0.04, py0 - _MURETE_G - 0.04, py0 + 0.04, z + 0.62,
                 z + 0.70, 'piedra_blanca', sin=('+x',))
    else:
        cu.cara([(-A, -F, z), (A, -F, z), (A, F, z), (-A, F, z)], losa,
                hacia=(0, 0, 1))

    # plazas pintadas (grupos de 3 + isletas cebreadas), 5 cm sobre la losa
    zl = z + _DESPEGUE
    lw = 0.14
    for i, (ya, yb) in enumerate(lay['filas']):
        # la linea de fondo de plaza va en el lado opuesto al pasillo de acceso
        # (filas pares: pasillo a -Y; impares: pasillo a +Y)
        yc0, yc1 = (yb - lw, yb) if i % 2 == 0 else (ya, ya + lw)
        for (gx0, gx1, n) in lay['grupos']:
            for k in range(n + 1):
                xl = gx0 + lay['w'] * k
                cu.cara([(xl - lw / 2, ya, zl), (xl + lw / 2, ya, zl),
                         (xl + lw / 2, yb, zl), (xl - lw / 2, yb, zl)],
                        'linea_blanca', hacia=(0, 0, 1))
            cu.cara([(gx0, yc0, zl), (gx1, yc0, zl), (gx1, yc1, zl),
                     (gx0, yc1, zl)], 'linea_blanca', hacia=(0, 0, 1))
        for (ix0, ix1) in lay['isletas']:
            _cebra(cu, ix0 + 0.35, ix1 - 0.35, ya + 0.35, yb - 0.35, zl)
    # flechas de circulacion en los pasillos
    bx0, bx1 = lay['bloque']
    for (ya, yb) in lay['pasillos']:
        if yb - ya < 2.5:
            continue
        ym = (ya + yb) / 2.0
        for fx in (0.22, 0.72):
            xf = bx0 + (bx1 - bx0) * fx
            cu.cara([(xf - 1.3, ym - 0.14, zl), (xf + 0.4, ym - 0.14, zl),
                     (xf + 0.4, ym + 0.14, zl), (xf - 1.3, ym + 0.14, zl)],
                    'linea_blanca', hacia=(0, 0, 1))
            cu.cara([(xf + 0.4, ym - 0.55, zl), (xf + 1.5, ym, zl),
                     (xf + 0.4, ym + 0.55, zl)], 'linea_blanca',
                    hacia=(0, 0, 1))

    # peto macizo perimetral
    for W, off, esq, ang in ((ancho, F, True, 0.0), (ancho, F, True, math.pi),
                             (fondo, A, False, -math.pi / 2.0),
                             (fondo, A, False, math.pi / 2.0)):
        sub = _MB()
        _peto_azotea(sub, W, off, esq, alto)
        cu.anexar(sub, ang)
    return cu


def _detalles_parking(ancho, fondo, alto, lay, niv, cx_fr, bw_fr, toldo_m,
                      mastiles, params):
    """Malla de detalles: toldo, cartel P, farolas finas, banderas y (solo si
    se pide con barandilla=True) pasamanos de hierro sobre el peto."""
    A, F = ancho / 2.0, fondo / 2.0
    z = alto
    de = _MB()
    z_peto = z + _PETO_H + _PETO_ALB
    if params.get('barandilla', False):
        for W, off, ang in ((ancho, F, 0.0), (ancho, F, math.pi),
                            (fondo, A, -math.pi / 2.0), (fondo, A, math.pi / 2.0)):
            sub = _MB()
            _barandilla_peto(sub, W, off, z_peto)
            de.anexar(sub, ang)
    # toldo a rayas sobre los arcos centrales del lado de la calle
    nb = len(cx_fr)
    if params.get('toldo', True) and nb >= 2:
        if nb >= 5:
            k_t = 3 if nb % 2 else 2
        else:
            k_t = 1 if nb % 2 else 2
        i0 = (nb - k_t) // 2
        if lay['rampa'] and i0 == 0:
            i0, k_t = 1, max(1, k_t - 1)
        x_t0 = cx_fr[i0] - bw_fr / 2.0 + 0.30
        x_t1 = cx_fr[i0 + k_t - 1] + bw_fr / 2.0 - 0.30
        _toldo(de, x_t0, x_t1, F + 0.02, niv['z_imp0'] - 0.12, 2.3, 1.1, toldo_m,
               franja=0.9)
    # cartel P junto a la entrada
    if lay['rampa']:
        _cartel_p(de, -A + _ESQ / 2.0, F + 0.10,
                  min(niv['z_imp0'] - 0.9, 4.6))
    # dos farolas finas en la azotea y banderas en las esquinas traseras
    for k, (fx, fy) in enumerate(lay['farolas']):
        _farola_fina(de, (fx, fy, z), 5.4 + 0.2 * k, rz=0.0)
    if params.get('banderas', True):
        for k, sx in enumerate((-1.0, 1.0)):
            _bandera(de, (sx * (A - _PETO_G / 2.0), -F + _PETO_G / 2.0, z_peto),
                     mastiles[k])
    return de


# ================================================================ MURO DE ARCADAS

def build_muro_arcadas(parent_collection, largo=40.0, alto=8.0, n_arcos=5,
                       seed=0, **params):
    """Muro de contencion de piedra con arcadas ciegas profundas. Devuelve la
    malla MIRADOR_muro_arcadas (ver docstring del modulo). params: grosor,
    parapeto, n_arc, inglete_izq, inglete_der (rad; medio giro de la junta,
    > 0 si el tramo contiguo gira hacia +Y = cara vista concava)."""
    col = parent_collection
    rng = random.Random(seed)
    L, H = float(largo), float(alto)
    n = max(1, int(n_arcos))
    G = float(params.get('grosor', MURO_ARCADAS_GROSOR))
    parapeto = params.get('parapeto', True)
    n_arc = int(params.get('n_arc', 10))
    yF, yB = G / 2.0, -G / 2.0
    mod = L / n
    pil_w = min(1.0, mod * 0.16)
    z_zoc = min(0.7, H * 0.12)
    z_cor = H - 0.5
    banda = 0.38

    mb = _MB()
    w = min(0.64 * mod, mod - pil_w - 0.8)
    r = w / 2.0
    top_max = z_cor - 0.55 - banda
    zs = top_max - r
    if zs < z_zoc + 0.4:
        zs = z_zoc + 0.4
        r = top_max - zs
        w = 2.0 * r
    huecos = []
    if r >= 0.5:
        prof = max(0.3, min(1.3, G - 0.4))
        for i in range(n):
            huecos.append({'xc': -L / 2.0 + mod * (i + 0.5), 'w': w, 'zb': z_zoc,
                           'zs': zs, 'arco': True, 'prof': prof,
                           'm_jamba': 'piedra_sombra', 'm_fondo': 'hueco_oscuro',
                           'm_suelo': 'piedra_sombra'})
    _pared(mb, -L / 2.0, L / 2.0, 0.0, H, yF, huecos, 'piedra_muro', n_arc)
    for h in huecos:
        _arquivolta(mb, h['xc'], zs, r, banda, yF, 0.10, 'piedra_clara', n_arc)
        for sg in (-1.0, 1.0):      # impostas en el arranque del arco
            xi = h['xc'] + sg * r
            mb.caja2(xi - 0.32, xi + 0.32, yF - 0.02, yF + 0.16, zs - 0.26, zs,
                     'piedra_clara', sin=('-y',))
    # cuerpo: trasdos, coronacion y testas
    mb.cara([(-L / 2, yB, 0), (L / 2, yB, 0), (L / 2, yB, H), (-L / 2, yB, H)],
            'piedra_muro', hacia=(0, -1, 0))
    mb.cara([(-L / 2, yB, H), (L / 2, yB, H), (L / 2, yF, H), (-L / 2, yF, H)],
            'piedra_muro', hacia=(0, 0, 1))
    for sg in (-1.0, 1.0):
        mb.cara([(sg * L / 2, yB, 0), (sg * L / 2, yF, 0), (sg * L / 2, yF, H),
                 (sg * L / 2, yB, H)], 'piedra_muro', hacia=(sg, 0, 0))
    # zocalo corrido
    mb.caja2(-L / 2, L / 2, yF, yF + 0.30, 0.0, z_zoc, 'piedra_zocalo',
             sin=('-y', '-z'))
    # pilastras con capitel (medias en las testas para teselar)
    for k in range(n + 1):
        xk = -L / 2.0 + mod * k
        xa, xb = max(-L / 2.0, xk - pil_w / 2.0), min(L / 2.0, xk + pil_w / 2.0)
        mb.caja2(xa, xb, yF, yF + 0.22, z_zoc, z_cor - 0.30, 'piedra_muro',
                 sin=('-y', '-z', '+z'))
        xa2, xb2 = max(-L / 2.0, xk - pil_w / 2.0 - 0.10), \
            min(L / 2.0, xk + pil_w / 2.0 + 0.10)
        mb.caja2(xa2, xb2, yF, yF + 0.32, z_cor - 0.30, z_cor, 'piedra_clara',
                 sin=('-y', '+z'))
    # cornisa de dos escalones
    mb.caja2(-L / 2, L / 2, yF, yF + 0.22, z_cor, z_cor + 0.22, 'piedra_clara',
             sin=('-y', '+z'))
    mb.caja2(-L / 2, L / 2, yF, yF + 0.42, z_cor + 0.22, H, 'piedra_clara',
             sin=('-y',))
    # peto bajo con albardilla y pilarones (las testas del peto corrido y de
    # su albardilla no se construyen: las tapan los medios pilarones extremos)
    if parapeto:
        mb.caja2(-L / 2, L / 2, yF - 0.45, yF, H, H + 0.75, 'piedra_muro',
                 sin=('-z', '+z', '-x', '+x'))
        mb.caja2(-L / 2, L / 2, yF - 0.51, yF + 0.06, H + 0.75, H + 0.90,
                 'piedra_clara', sin=('-x', '+x'))
        for k in range(n + 1):
            xk = -L / 2.0 + mod * k
            xa, xb = max(-L / 2.0, xk - 0.45), min(L / 2.0, xk + 0.45)
            mb.caja2(xa, xb, yF - 0.56, yF + 0.10, H, H + 1.02, 'piedra_muro',
                     sin=('-z', '+z'))
            xa2, xb2 = max(-L / 2.0, xk - 0.52), min(L / 2.0, xk + 0.52)
            mb.caja2(xa2, xb2, yF - 0.63, yF + 0.17, H + 1.02, H + 1.15,
                     'piedra_clara')
    # sillares de acento junto a las jambas (tono de piedra mas oscuro/claro)
    # Los dos sillares de cada jamba van en franjas de z DISJUNTAS (uno en la
    # mitad baja y otro en la alta) para que nunca se pisen en el mismo plano.
    if huecos:
        hueco_l = (mod - pil_w - w) / 2.0
        z_lo = z_zoc + 0.4
        z_hi = max(z_lo + 0.5, zs - 0.36)       # bajo las impostas del arco
        n_fr = 2 if z_hi - z_lo >= 1.0 else 1
        h_fr = (z_hi - z_lo) / n_fr
        if hueco_l > 0.75:
            for i in range(n):
                for sg in (-1.0, 1.0):
                    for j in range(n_fr):
                        bw_ = rng.uniform(0.45, min(0.75, hueco_l - 0.2))
                        bh_ = rng.uniform(0.24, min(0.34, h_fr - 0.10))
                        xc = huecos[i]['xc'] + sg * (r + hueco_l / 2.0) + \
                            rng.uniform(-1, 1) * (hueco_l - bw_ - 0.15) / 2.0
                        zc = z_lo + h_fr * j + \
                            rng.uniform(0.0, h_fr - bh_ - 0.06)
                        mb.caja2(xc - bw_ / 2, xc + bw_ / 2, yF, yF + 0.04,
                                 zc, zc + bh_,
                                 rng.choice(('piedra_sombra', 'piedra_clara',
                                             'piedra_zocalo')),
                                 sin=('-y',))
    # ---- ingletes: cizalla de los vertices de cada testa alrededor de la
    # arista de la CARA VISTA (y = yF), de modo que dos tramos girados 2*a
    # entre si y unidos por esa arista cierran exactamente en el plano bisector
    # (cornisa, zocalo, pilastras y peto incluidos) sin abrir cunas.
    t_i = math.tan(max(-INGLETE_MAX, min(INGLETE_MAX,
                                         float(params.get('inglete_izq', 0.0)))))
    t_d = math.tan(max(-INGLETE_MAX, min(INGLETE_MAX,
                                         float(params.get('inglete_der', 0.0)))))
    if t_i or t_d:
        for iv, (x, y, z) in enumerate(mb.v):
            if t_d and abs(x - L / 2.0) < 1e-5:
                mb.v[iv] = (x + (yF - y) * t_d, y, z)
            elif t_i and abs(x + L / 2.0) < 1e-5:
                mb.v[iv] = (x - (yF - y) * t_i, y, z)
    return mb.obj('%s_muro_arcadas' % PRE, col)


def build_muro_arcadas_curvo(parent_collection, puntos, alto=8.0, seed=0,
                             **params):
    """Muro de arcadas que SIGUE UNA CURVA (el de la pelicula es curvo): cadena
    de tramos rectos de build_muro_arcadas ingleteados entre si.

    `puntos`: polilinea [(x, y) o (x, y, z), ...] de la ARISTA INFERIOR DE LA
    CARA VISTA, en coordenadas locales del Empty devuelto. La cara vista mira
    a la IZQUIERDA del sentido de avance (invertir=True la pone a la derecha).
    Cada tramo va de un punto al siguiente (cuerdas de 6-10 m recomendadas;
    giros de hasta ~50 grados por junta); arcos por tramo = largo / `modulo`
    (8.0 m por defecto). Si los puntos traen z, cada tramo se apoya en la
    media de las z de sus dos extremos (muro escalonado que acompana a una
    calle en pendiente). cerrado=True une el ultimo tramo con el primero.
    Resto de params (grosor, parapeto, n_arc...) pasan a build_muro_arcadas.
    Devuelve el Empty raiz MIRADOR_muro_arcadas_curvo (hijos: mallas
    MIRADOR_muro_arcadas[.NNN], cada una <= 1.5k tris)."""
    col = parent_collection
    pts = [tuple(float(c) for c in p) for p in puntos]
    if params.pop('invertir', False):
        pts.reverse()
    cerrado = params.pop('cerrado', False)
    modulo = max(2.0, float(params.pop('modulo', 8.0)))
    for k in ('inglete_izq', 'inglete_der', 'largo', 'n_arcos'):
        params.pop(k, None)
    G = float(params.get('grosor', MURO_ARCADAS_GROSOR))
    raiz = _raiz('%s_muro_arcadas_curvo' % PRE, col, 2.0)
    tramos = []
    for k in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[k][:2], pts[k + 1][:2]
        lg = math.hypot(bx - ax, by - ay)
        if lg < 0.5:
            continue
        za = pts[k][2] if len(pts[k]) > 2 else 0.0
        zb = pts[k + 1][2] if len(pts[k + 1]) > 2 else 0.0
        tramos.append(((ax + bx) / 2.0, (ay + by) / 2.0, (za + zb) / 2.0, lg,
                       math.atan2(by - ay, bx - ax)))

    def medio_giro(r0, r1):
        d = (r1 - r0 + math.pi) % TAU - math.pi
        return d / 2.0

    nt = len(tramos)
    for k, (mx, my, mz, lg, rum) in enumerate(tramos):
        ant = tramos[k - 1] if (k > 0 or cerrado) else None
        sig = tramos[(k + 1) % nt] if (k < nt - 1 or cerrado) else None
        ob = build_muro_arcadas(
            col, largo=lg, alto=alto, n_arcos=max(1, int(round(lg / modulo))),
            seed=seed + k,
            inglete_izq=medio_giro(ant[4], rum) if ant else 0.0,
            inglete_der=medio_giro(rum, sig[4]) if sig else 0.0, **params)
        ob.parent = raiz
        # el origen del tramo esta en el eje del muro: G/2 por detras de la cara
        ob.location = (mx + math.sin(rum) * G / 2.0,
                       my - math.cos(rum) * G / 2.0, mz)
        ob.rotation_euler = (0.0, 0.0, rum)
    return raiz


# ================================================================ MURETE DE PIEDRA

def build_muro_piedra(parent_collection, largo=10.0, alto=1.1, **params):
    """Murete bajo de piedra de borde de calle con albardilla a dos aguas,
    teselable en X. Devuelve la malla MIRADOR_muro_piedra."""
    col = parent_collection
    rng = random.Random(params.get('seed', 0))
    L, H = float(largo), max(0.5, float(alto))
    g = 0.25
    z_alb = H - 0.17
    mb = _MB()
    mb.caja2(-L / 2, L / 2, -0.31, 0.31, 0.0, 0.18, 'piedra_zocalo', sin=('-z',))
    mb.caja2(-L / 2, L / 2, -g, g, 0.18, z_alb, 'piedra_muro',
             sin=('-z', '+z'))
    # albardilla a dos aguas (prisma pentagonal)
    perfil = [(-0.33, z_alb), (0.33, z_alb), (0.33, z_alb + 0.09), (0.0, H),
              (-0.33, z_alb + 0.09)]
    np_ = len(perfil)
    for i in range(np_):
        (ya, za), (yb, zb) = perfil[i], perfil[(i + 1) % np_]
        ym, zm = (ya + yb) / 2.0, (za + zb) / 2.0
        mb.cara([(-L / 2, ya, za), (L / 2, ya, za), (L / 2, yb, zb),
                 (-L / 2, yb, zb)], 'piedra_clara',
                hacia=(0.0, ym, zm - (z_alb + 0.06)))
    for sg in (-1.0, 1.0):
        mb.cara([(sg * L / 2, y, z) for y, z in perfil], 'piedra_clara',
                hacia=(sg, 0, 0))
    # sillares de acento por las dos caras
    n_s = max(2, int(L / 1.6))
    for cara_y in (1.0, -1.0):
        for k in range(n_s):
            bw_ = rng.uniform(0.35, 0.6)
            bh_ = rng.uniform(0.16, 0.24)
            xc = -L / 2.0 + (k + rng.uniform(0.25, 0.75)) * L / n_s
            xc = max(-L / 2 + bw_ / 2 + 0.05, min(L / 2 - bw_ / 2 - 0.05, xc))
            zc = rng.uniform(0.24, max(0.25, z_alb - bh_ - 0.06))
            y0, y1 = (g, g + 0.04) if cara_y > 0 else (-g - 0.04, -g)
            mb.caja2(xc - bw_ / 2, xc + bw_ / 2, y0, y1, zc, zc + bh_,
                     rng.choice(('piedra_sombra', 'piedra_clara', 'piedra_zocalo')),
                     sin=('-y',) if cara_y > 0 else ('+y',))
    return mb.obj('%s_muro_piedra' % PRE, col)


# ======================================================================== MIRADOR

def build_mirador(parent_collection, radio=7.0, seed=0, **params):
    """Terraza-mirador semicircular con balaustrada, jardineras y farola.
    Origen en el centro del borde recto (y=0), abombada hacia +Y. Devuelve el
    Empty raiz MIRADOR_mirador."""
    col = parent_collection
    rng = random.Random(seed)
    R = max(3.5, float(radio))
    faldon = max(0.0, float(params.get('faldon', 4.0)))
    nseg = 16
    z_f = 0.06
    raiz = _raiz('%s_mirador' % PRE, col, 2.0)

    # --------------------------------------------------------------- terraza
    te = _MB()
    r1, r2, r3 = 0.30 * R, 0.64 * R, R - 0.46
    tonos = ('piedra_pavimento_claro', 'piedra_pavimento_rosa')
    for k in range(nseg):
        a0 = math.pi * k / nseg
        a1 = math.pi * (k + 1) / nseg
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        te.cara([(0, 0, z_f), (r1 * c0, r1 * s0, z_f), (r1 * c1, r1 * s1, z_f)],
                tonos[1], hacia=(0, 0, 1))
        te.cara([(r1 * c0, r1 * s0, z_f), (r2 * c0, r2 * s0, z_f),
                 (r2 * c1, r2 * s1, z_f), (r1 * c1, r1 * s1, z_f)],
                tonos[k % 2], hacia=(0, 0, 1))
        te.cara([(r2 * c0, r2 * s0, z_f), (r3 * c0, r3 * s0, z_f),
                 (r3 * c1, r3 * s1, z_f), (r2 * c1, r2 * s1, z_f)],
                tonos[(k // 2 + 1) % 2], hacia=(0, 0, 1))
        te.cara([(r3 * c0, r3 * s0, z_f), (R * c0, R * s0, z_f),
                 (R * c1, R * s1, z_f), (r3 * c1, r3 * s1, z_f)],
                'piedra_clara', hacia=(0, 0, 1))
    # moldura bajo el pavimento y tambor ataluzado
    te.anillo(R - 0.05, R + 0.14, -0.30, z_f, 0.0, math.pi, nseg, 'piedra_clara',
              caras=('ext', 'inf'))
    te.anillo(R, R + 0.14, z_f - 0.001, z_f, 0.0, math.pi, nseg,
              'piedra_clara', caras=('sup',))
    # trasdos plano (mira a -Y, normalmente enterrado bajo la calzada) con el
    # MISMO perfil escalonado que el tambor: moldura, talud y zocalo, en tres
    # quads convexos (el de la moldura hace tambien de canto del borde recto,
    # lado calzada, de z=0 a z_f)
    te.cara([(-R - 0.14, 0, -0.30), (R + 0.14, 0, -0.30), (R + 0.14, 0, z_f),
             (-R - 0.14, 0, z_f)], 'piedra_clara', hacia=(0, -1, 0))
    if faldon > 0.35:
        zb = -faldon
        tal = 0.07 * (faldon - 0.30)
        te.anillo(R - 0.3, R, zb + 0.6, -0.30, 0.0, math.pi, nseg, 'piedra_muro',
                  caras=('ext',), r_out_base=R + tal)
        te.anillo(R - 0.3, R + tal + 0.16, zb, zb + 0.6, 0.0, math.pi, nseg,
                  'piedra_zocalo', caras=('ext', 'sup'))
        te.cara([(-R - tal, 0, zb + 0.6), (R + tal, 0, zb + 0.6),
                 (R, 0, -0.30), (-R, 0, -0.30)], 'piedra_muro',
                hacia=(0, -1, 0))
        te.cara([(-R - tal - 0.16, 0, zb), (R + tal + 0.16, 0, zb),
                 (R + tal + 0.16, 0, zb + 0.6), (-R - tal - 0.16, 0, zb + 0.6)],
                'piedra_zocalo', hacia=(0, -1, 0))

    # ---------------------------------------------------------------- farola
    rc = R - 0.23
    n_pil = 5
    ang_pil = [math.pi * k / (n_pil - 1) for k in range(n_pil)]
    fa = _MB()
    a_c = ang_pil[n_pil // 2]
    _farola_globos(fa, (rc * math.cos(a_c), rc * math.sin(a_c), z_f + 1.26),
                   3.1, brazos=2, eje=(1.0, 0.0))

    # ----------------------------------------------------------- balaustrada
    # los pilarones extremos se meten 0.36 m hacia +Y para que ni su capitel
    # (0.70 de lado) cruce el borde recto y=0 (lado calzada)
    d_ext = 0.36
    # el plinto y el pasamanos arrancan DENTRO de los pilarones extremos (sus
    # testas abiertas nunca quedan a la vista desde la calzada)
    th_e = math.asin(min(1.0, d_ext / rc))

    def balaustrada(paso, lados):
        ba = _MB()
        z_p0, z_p1 = z_f, z_f + 0.24
        z_r0, z_r1 = z_f + 0.90, z_f + 1.05
        ba.anillo(rc - 0.20, rc + 0.20, z_p0, z_p1, th_e, math.pi - th_e, nseg,
                  'piedra_clara', caras=('ext', 'int', 'sup'))
        ba.anillo(rc - 0.23, rc + 0.23, z_r0, z_r1, th_e, math.pi - th_e, nseg,
                  'piedra_clara', caras=('ext', 'int', 'sup', 'inf'))
        for k, a in enumerate(ang_pil):
            px, py = rc * math.cos(a), rc * math.sin(a)
            if k in (0, n_pil - 1):
                py += d_ext
            ba.caja((px, py, z_f + 0.58), (0.58, 0.58, 1.16), 'piedra_clara',
                    rz=a, sin=('-z', '+z'))
            ba.caja((px, py, z_f + 1.21), (0.70, 0.70, 0.10), 'piedra_clara',
                    rz=a)
            if k != n_pil // 2:
                ba.revolucion((px, py, z_f + 1.26), [(0.24, 0.0), (0.06, 0.20)],
                              'piedra_clara', n=4, suave=False, tapa_sup=True,
                              fase=a + math.pi / 4.0)
        perfil_bal = [(0.075, 0.0), (0.125, 0.24), (0.055, 0.50), (0.075, 0.66)]
        h_bal = z_r0 - z_p1
        perfil_bal = [(rr, zz * h_bal / 0.66) for rr, zz in perfil_bal]
        delta = (0.29 + 0.10) / rc
        for k in range(n_pil - 1):
            a0 = ang_pil[k] + delta + (d_ext / rc if k == 0 else 0.0)
            a1 = ang_pil[k + 1] - delta - (d_ext / rc if k == n_pil - 2 else 0.0)
            nb = max(2, int(round((a1 - a0) * rc / paso)))
            for j in range(nb):
                a = a0 + (a1 - a0) * (j + 0.5) / nb
                ba.revolucion((rc * math.cos(a), rc * math.sin(a), z_p1),
                              perfil_bal, 'piedra_clara', n=lados, suave=True,
                              fase=a)
        return ba

    # ------------------------------------------------------------ jardineras
    jardineras = []
    for nombre, sx in (('L', -1.0), ('R', 1.0)):
        ja = _MB()
        jx, jy = sx * R * 0.60, max(1.45, R * 0.22)
        rj = min(0.95, R * 0.14)
        ja.revolucion((jx, jy, z_f),
                      [(rj * 0.74, 0.0), (rj * 0.80, 0.10), (rj * 0.70, 0.16),
                       (rj * 0.98, 0.62), (rj * 1.06, 0.66), (rj * 1.06, 0.78)],
                      'piedra_clara', n=10, suave=True)
        ja.revolucion((jx, jy, z_f), [(rj * 0.90, 0.78), (rj * 1.06, 0.78)],
                      'piedra_clara', n=10, suave=False)
        ja.cara([(jx + rj * 0.90 * math.cos(TAU * j / 10),
                  jy + rj * 0.90 * math.sin(TAU * j / 10), z_f + 0.72)
                 for j in range(10)], 'tierra', hacia=(0, 0, 1))
        _palmera(ja, (jx, jy, z_f + 0.70), 2.5 + rng.uniform(-0.2, 0.35), rng)
        for q in range(3):
            a = TAU * q / 3.0 + rng.uniform(-0.3, 0.3) + (0.5 if sx > 0 else 0.0)
            _adelfa(ja, (jx + rj * 0.52 * math.cos(a), jy + rj * 0.52 * math.sin(a),
                         z_f + 0.66), rj * rng.uniform(0.40, 0.50), rng,
                    n_flores=5)
        jardineras.append((nombre, ja))

    # degradacion automatica: con radios grandes (> ~9 m) los balaustres se
    # espacian y pierden lados hasta caber en el tope de triangulos
    tope = params.get('tope_tris', TOPE_MIRADOR)
    fijo = te.tris() + fa.tris() + sum(j.tris() for _, j in jardineras)
    niveles = ((0.55, 5), (0.72, 5), (0.90, 4), (1.15, 4), (1.50, 4))
    lod = 0
    while True:
        ba = balaustrada(*niveles[lod])
        total = fijo + ba.tris()
        if tope is None or total <= tope or lod >= _LOD_MIRADOR_MAX:
            break
        lod += 1
    if tope is not None and total > tope:
        print('AVISO %s_mirador radio %g: %d tris > tope %d incluso con el '
              'detalle minimo' % (PRE, R, total, tope))
    te.obj('%s_mirador_terraza' % PRE, col, raiz)
    ba.obj('%s_mirador_balaustrada' % PRE, col, raiz)
    fa.obj('%s_mirador_farola' % PRE, col, raiz)
    for nombre, ja in jardineras:
        ja.obj('%s_mirador_jardinera_%s' % (PRE, nombre), col, raiz)
    raiz['mirador_lod'] = lod
    raiz['mirador_tris'] = total
    return raiz


# ====================================================================== MUESTRARIO

def build(parent_collection, seed=0, **params):
    """Muestrario del kit con todas las piezas. Devuelve el Empty MIRADOR_kit.
    params opcionales: ancho, fondo, alto (parking); largo_arcadas,
    alto_arcadas, n_arcos; largo_muro, alto_muro; radio, faldon."""
    col = parent_collection
    raiz = _raiz('%s_kit' % PRE, col, 3.0)

    ancho = params.get('ancho', 40.0)
    fondo = params.get('fondo', 18.0)
    alto = params.get('alto', 20.0)
    pk = build_parking_terraza(col, ancho=ancho, fondo=fondo, alto=alto, seed=seed)
    pk.parent = raiz
    pk.location = (-(ancho / 2.0 + 6.0), 0.0, 0.0)

    la = params.get('largo_arcadas', 40.0)
    ma = build_muro_arcadas(col, largo=la, alto=params.get('alto_arcadas', 8.0),
                            n_arcos=params.get('n_arcos', 5), seed=seed)
    ma.parent = raiz
    ma.location = (la / 2.0 + 2.0, -7.0, 0.0)

    fal = params.get('faldon', 4.0)
    radio = params.get('radio', 7.0)
    mi = build_mirador(col, radio=radio, seed=seed, faldon=fal)
    mi.parent = raiz
    mi.location = (radio + 4.0, 7.0, fal)

    lm = params.get('largo_muro', 10.0)
    for k in range(2):
        mp = build_muro_piedra(col, largo=lm, alto=params.get('alto_muro', 1.1),
                               seed=seed + k)
        mp.parent = raiz
        mp.location = (2.0 * radio + 8.0 + lm * (k + 0.5), 10.0, 0.0)
    return raiz
