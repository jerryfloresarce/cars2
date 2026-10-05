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

FASE VISUAL F1 (bloque 7.1 de FASE_VISUAL_PLAN.md, propietario 'horizonte'):
  - COLORES: todos salen de 03_blender/paleta.json via paleta.py (unica
    fuente de color): MAT_MONT_bosque = oliva_oscuro, bosque_claro = salvia,
    roca = caliza_ocre, roca_clara = caliza_ocre x1.25, roca_oscura =
    caliza_sombra. Sin literales: si la paleta cambia, basta re-ejecutar.
  - build_cordillera admite ademas: res=float (resolucion de los picos; sin
    ella se calcula para <= 60k tris), pie=bool, cordal_div=int (celdas del
    cordal, 118 por defecto), prefijo='MONT_' (nombres de objetos),
    materiales=tupla de 5 (slots 0..4) y unir=True (devuelve UNA malla
    '<prefijo>cordillera' con todos los picos y el cordal fundidos, sin
    Empty: menos draw calls y sin jerarquia que exportar).
  - build_loma / build_pena / build_pico admiten prefijo= y materiales=;
    build_loma admite unir=True (malla unica '<prefijo>loma').
  - ANILLO DE HORIZONTE (prefijo HORIZ_, materiales MAT_HORIZ_*):
      build_anillo_horizonte(parent_collection, terreno=T|centro=(x, y),
                             seed=0, mezcla=None, **cfg) -> dict
      Dos filas de cordilleras lejanas (3.2 km verde-azulada, 4.5 km
      gris-azul; picos de tipos domo/cresta/piramide/meseta SIN 'aguja' y
      radio x1.35 = macizos romos, r3) sobre un arco de 200 grados centrado
      en el centro de la rejilla del terreno, abierto 160 grados al S/SO (mar
      abierto); 9 lomas a 2.4-2.8 km (cuatro crestas de costa que prolongan
      el anillo en sus extremos, entrando <= 10 grados en la abertura; cuatro
      islotes dentados de 110-150 m DENTRO de la abertura, con mar abierto
      entre ellos: son la unica silueta posible en la mitad visible de la
      linea mar/cielo de las tomas 54/61/63 sin cerrar la abertura; y una
      loma 'ventana' a 40.5 grados del extremo O, en el hueco de la linea
      mar/cielo de 57 entre la roca del lazo y el islote 212.5, r3), 3
      pueblecitos-silueta (cajas crema 30x10x8, 1 material) y 1 faro lejano
      sobre un islote. CFG_ANILLO manda (tipos, ensanche, lomas_ventana,
      islote_alto...). Perspectiva atmosferica HORNEADA en el
      color: cada material = color de paleta mezclado con el color del cielo
      del horizonte (0.70, 0.84, 0.98) al 35 % (2.4 km) .. 55 % (4.5 km);
      'mezcla' (contrato mezcla(rgb_lineal, dist_m) -> rgb_lineal) permite
      sustituir esa formula. OJO: mejorar_materiales.horizonte() NO es una
      'mezcla' (es un pase de escena posterior del pipeline que recalcula el
      color desde mat['horiz_color_base'], que este kit deja escrito con el
      color de paleta sin mezclar): no pasarla como mezcla.
      Materiales con custom props ac_shader/ac_props/ac_samplers/ac_tex_max/
      ac_alpha_test/ac_raw (defecto = comportamiento actual del writer) y
      diffuse_color = Base Color = media lineal (lo que lee analizar_material).
      Todo fuera de la rejilla del terreno; ningun vertice bajo z = -6;
      presupuesto <= 250k tris (se comprueba en test_montanas_fondo_v2.py).
      Devuelve {'objetos', 'tris', 'materiales', 'cordilleras', 'lomas',
      'pueblos', 'faros', 'centro', 'abertura'}.
      build_pueblecito(parent_collection, n_casas=20, seed=0, ...) -> malla
      build_faro(parent_collection, alto=30.0, seed=0, ...) -> malla
"""

import bisect
import importlib.util
import math
import os
import random

import bpy
import bmesh
from mathutils import Matrix, Vector

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


_PALETA = {}


def _paleta():
    """03_blender/paleta.py (unica fuente de color), cargado por ruta
    relativa a este fichero (vale en Blender --factory-startup y en el
    integrador). Lanza ImportError si no esta: no hay colores de reserva."""
    if "mod" not in _PALETA:
        ruta = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             os.pardir, "paleta.py"))
        if not os.path.isfile(ruta):
            raise ImportError("montanas_fondo_v2: falta %s (paleta unica de la fase visual)" % ruta)
        spec = importlib.util.spec_from_file_location("paleta", ruta)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PALETA["mod"] = mod
    return _PALETA["mod"]


# colores base del kit por nombre de paleta.json (slot: (nombre, factor de luminancia))
_PALETA_SLOTS = (("oliva_oscuro", 1.0),      # 0 bosque
                 ("salvia", 1.0),            # 1 bosque_claro
                 ("caliza_ocre", 1.0),       # 2 roca
                 ("caliza_ocre", 1.25),      # 3 roca_clara
                 ("caliza_sombra", 1.0))     # 4 roca_oscura
_SUFIJOS_SLOT = ("bosque", "bosque_claro", "roca", "roca_clara", "roca_oscura")


def _color_slot(k):
    """RGB lineal del slot k segun la paleta (variante() escala la luminancia)."""
    nombre, lum = _PALETA_SLOTS[k]
    return _paleta().variante(nombre, lum)


def _materiales_mont():
    """Los 5 materiales del kit, en el orden de slots del contrato, con los
    colores de paleta.json (fase visual: nada de literales)."""
    return tuple(_mat("MAT_MONT_" + _SUFIJOS_SLOT[k], _color_slot(k), 0.95) for k in range(5))


def _malla(nombre, verts, faces, parent_collection, recalc=True, materiales=None):
    """Crea la malla + objeto, normales coherentes (bmesh), 5 slots.
    recalc=False para campos de altura abiertos (ya orientados a +Z).
    materiales: tupla de 5 materiales (slots 0..4); None = MAT_MONT_*."""
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    me.validate()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    for m in (materiales or _materiales_mont()):
        me.materials.append(m)
    ob = bpy.data.objects.new(nombre, me)
    parent_collection.objects.link(ob)
    return ob


def _unir(nombre, piezas, parent_collection, materiales):
    """Funde varias piezas (lista de (objeto, Matrix 4x4 local->destino)) en
    UNA malla con los mismos 5 slots: copia vertices transformados, caras,
    material_index y use_smooth; borra los objetos y mallas originales.
    Las piezas deben compartir la misma tupla de materiales (mismo orden)."""
    verts, faces, idx, suave = [], [], [], []
    for ob, M in piezas:
        me = ob.data
        off = len(verts)
        verts.extend(tuple(M @ v.co) for v in me.vertices)
        for p in me.polygons:
            faces.append(tuple(i + off for i in p.vertices))
            idx.append(p.material_index)
            suave.append(p.use_smooth)
    for ob, _M in piezas:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    ob = _malla(nombre, verts, faces, parent_collection, recalc=False, materiales=materiales)
    me = ob.data
    if len(me.polygons) == len(idx):
        for p, k, s in zip(me.polygons, idx, suave):
            p.material_index = k
            p.use_smooth = s
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
# F1 r4 (director r3, cosmetico 9 "picos de aguja"): 'lomo' = cresta ROMA para el horizonte: perfil convexo del domo,
# linea de cumbres suave (1-3 lomas anchas, collados someros) y casquete redondeado (cap 'domo'); sin corona dentada ni
# espolones claros. Se da de alta DESPUES de TIPOS a proposito: no entra en el sorteo de _elegir_tipo (MONT_pico sin
# tipo, p. ej. el acantilado del tunel de integrar_escena) ni en la seccion 1 del test; solo se usa pidiendolo.
_TIPOS["lomo"] = dict(
    perfil=[(0.0, 1.0), (0.10, 0.955), (0.24, 0.90), (0.44, 0.80),
            (0.62, 0.70), (0.77, 0.60), (0.89, 0.50), (1.0, 0.40)],
    lados=0, arista=0.0, twist=0.0, canal=0.12, ridged=0.14, estr=2.0,
    crown=0.0, asym=0.14, lean=0.04, cap="domo", tl=0.50, rug=1.0,
    rayas=False, pared=76.0, tl_var=0.16, cumbres_suaves=True)
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


def _cumbres_cresta(rng, suave=False):
    """Línea de cumbres de una cresta: H(s) en [0.45..1] con s en [-1, 1]
    (2-4 cumbres separadas por collados). suave=True (tipo 'lomo', F1 r4):
    1-3 lomas anchas (w 0.30-0.50) y collados someros (H en [0.70..1])."""
    n_c = rng.randint(1, 3) if suave else rng.randint(2, 4)
    piso = 0.70 if suave else 0.45
    cumbres = []
    for j in range(n_c):
        s_j = -0.70 + 1.40 * (j + 0.5) / n_c + rng.uniform(-0.08, 0.08)
        a_j = 1.0 if j == rng.randrange(n_c) else rng.uniform(0.70, 0.92)
        w_j = rng.uniform(0.30, 0.50) if suave else rng.uniform(0.14, 0.24)
        cumbres.append((s_j, a_j, w_j))
    # una de ellas es la principal
    j_max = max(range(n_c), key=lambda j: cumbres[j][1])
    cumbres[j_max] = (cumbres[j_max][0], 1.0, cumbres[j_max][2])

    def H(s):
        b = 0.0
        for (s_j, a_j, w_j) in cumbres:
            b = max(b, a_j * math.exp(-((s - s_j) / w_j) ** 2))
        return piso + (1.0 - piso) * b
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
    if tipo in ("cresta", "lomo"):
        a_x = 0.5 * (largo_cresta if largo_cresta else 2.6 * radio)
        esc_x = max(a_x / radio, 1.0)
        H = _cumbres_cresta(rng, suave=bool(cfg.get("cumbres_suaves")))
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
    if tipo in ("cresta", "lomo"):
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
    ob = _malla(kw.get("prefijo", "MONT_") + "pico", verts, faces, parent_collection,
                materiales=kw.get("materiales"))
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
def _cordal_dims(picos, div=118):
    """Rejilla del cordal: (x0, y0, cell, nx, ny) cubriendo 1.5 radios
    alrededor de cada pico (el borde queda hundido a z=-6). div = celdas
    a lo largo de X (118 por defecto; menos = cordal mas barato)."""
    x0 = min(p["x"] - p["r"] * 1.5 for p in picos)
    x1 = max(p["x"] + p["r"] * 1.5 for p in picos)
    y0 = min(p["y"] - p["r"] * 1.5 for p in picos)
    y1 = max(p["y"] + p["r"] * 1.5 for p in picos)
    cell = max(7.0, (x1 - x0) / float(div))
    nx = int(math.ceil((x1 - x0) / cell)) + 1
    ny = int(math.ceil((y1 - y0) / cell)) + 1
    return x0, y0, cell, nx, ny


def _cordal_geometry(picos, seed, div=118):
    """Campo de alturas que une los picos: banco de base (lomas verdes
    alrededor de los pies) + collados a media altura entre picos vecinos
    (cresta redondeada de anchura ~radio). Devuelve (verts, faces, cresta)
    con cresta[i] en [0..1] = cercanía del vértice a la línea de cumbres."""
    so = seed * 5.31 + 1.7
    x0, y0, cell, nx, ny = _cordal_dims(picos, div)
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
      pend_bosque, pend_pared, linea_arboles, rugosidad -> a cada pico
      res=float     resolucion de los picos (sin ella: la que cabe en 60k)
      pie=bool      pie de derrubios hundido a z=-6 (True)
      cordal_div    celdas del cordal a lo largo de X (118)
      prefijo       prefijo de nombres ('MONT_'); materiales = tupla de 5
      unir=True     UNA malla '<prefijo>cordillera' (picos + cordal fundidos,
                    sin Empty); False (defecto) = Empty + hijos como siempre.
      ensanche=1.0  factor sobre el radio de cada pico (misma altura): > 1 =
                    macizos mas anchos y romos (horizonte 'Pixar': con 1.35 el
                    cociente alto/radio de la fila trasera baja de ~2.2 a ~1.6)."""
    prefijo = kw.get("prefijo", "MONT_")
    materiales = kw.get("materiales")
    unir = bool(kw.get("unir", False))
    cordal_div = int(kw.get("cordal_div", 118))
    ensanche = max(0.5, float(kw.get("ensanche", 1.0)))
    root = None
    if not unir:
        root = bpy.data.objects.new(prefijo + "cordillera", None)
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
        if tipo in ("cresta", "lomo"):              # alargada a lo largo de X
            r = spacing * rng.uniform(0.40, 0.48)
            largo_c = spacing * rng.uniform(1.4, 1.7)
            rot = rng.uniform(-0.30, 0.30) + (math.pi if rng.random() < 0.5 else 0.0)
            if tipo == "lomo":                      # F1 r4: lomo mas largo que ancho aun con ensanche
                largo_c *= 1.3
        r *= ensanche                                # F1 r3: macizos mas anchos (horizonte)
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

    # presupuesto: <= 60k en total (cordal + picos), salvo res explicita
    x0, y0, cell, nx, ny = _cordal_dims(cord_in, cordal_div)
    tris_cordal = (nx - 1) * (ny - 1) * 2
    if kw.get("res") is not None:
        res = _clamp(float(kw["res"]), 0.2, 1.0)
    else:
        objetivo = min(7400.0, (60000.0 - tris_cordal) / n)
        res = _clamp(math.sqrt(objetivo / 9900.0), 0.35, 1.0)
    pie = bool(kw.get("pie", True))

    extra = {k: kw[k] for k in ("pend_bosque", "pend_pared", "linea_arboles",
                                "rugosidad") if k in kw}
    piezas = []
    for p in picos:
        pico = build_pico(parent_collection, alto=p["h"], radio=p["r"],
                          seed=seed * 13 + p["i"] * 101 + 5, tipo=p["tipo"],
                          res=res, largo_cresta=p["largo_c"], pie=pie,
                          prefijo=prefijo, materiales=materiales, **extra)
        if unir:
            piezas.append((pico, Matrix.Translation((p["x"], p["y"], 0.0)) @
                           Matrix.Rotation(p["rot"], 4, "Z")))
        else:
            pico.location = (p["x"], p["y"], 0.0)
            pico.rotation_euler = (0.0, 0.0, p["rot"])
            pico.parent = root

    verts, faces, cresta = _cordal_geometry(cord_in, seed, cordal_div)
    cordal = _malla(prefijo + "cordal", verts, faces, parent_collection, recalc=False,
                    materiales=materiales)
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
    if unir:
        piezas.append((cordal, Matrix.Identity(4)))
        root = _unir(prefijo + "cordillera", piezas, parent_collection, materiales)
    else:
        cordal.parent = root
    root["mont_tipos"] = ",".join(p["tipo"] for p in picos)
    root["mont_alto"] = float(max(p["h"] for p in picos))
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
    ob = _malla(kw.get("prefijo", "MONT_") + "pena", [tuple(v) for v in verts], faces,
                parent_collection, materiales=kw.get("materiales"))
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
    largo de X local, 2-4 cumbres con collados). Empty MONT_loma.
    kw: prefijo ('MONT_'), materiales (tupla de 5), unir=True -> UNA malla
    '<prefijo>loma' (pico + penasco fundidos, sin Empty), res (0.7),
    tipo_largo ('cresta'; 'lomo' = cresta roma con 1-3 lomas anchas, F1 r4)."""
    prefijo = kw.get("prefijo", "MONT_")
    materiales = kw.get("materiales")
    unir = bool(kw.get("unir", False))
    root = None
    if not unir:
        root = bpy.data.objects.new(prefijo + "loma", None)
        root.empty_display_size = 5.0
        parent_collection.objects.link(root)
    comunes = dict(linea_arboles=2.0, rugosidad=0.6, pend_bosque=60.0,
                   pend_pared=80.0, estratos=False,
                   res=float(kw.get("res", 0.7)), prefijo=prefijo,
                   materiales=materiales)
    if largo is None:
        pico = build_pico(parent_collection, alto=alto, radio=radio, seed=seed,
                          tipo="domo", **comunes)
    else:
        pico = build_pico(parent_collection, alto=alto, radio=radio, seed=seed,
                          tipo=str(kw.get("tipo_largo", "cresta")), largo_cresta=float(largo), **comunes)
    piezas = [(pico, Matrix.Identity(4))]
    if not unir:
        pico.parent = root
    if pena:
        cima = max(pico.data.vertices, key=lambda v: v.co.z).co
        pn = build_pena(parent_collection, alto=alto * 0.45, radio=radio * 0.22,
                        seed=seed + 3, prefijo=prefijo, materiales=materiales)
        loc = (cima.x, cima.y, cima.z - alto * 0.08)
        if unir:
            piezas.append((pn, Matrix.Translation(loc)))
        else:
            pn.location = loc
            pn.parent = root
    if unir:
        root = _unir(prefijo + "loma", piezas, parent_collection, materiales)
    root["mont_alto"] = float(alto)
    root["mont_radio"] = float(radio)
    return root


# ======================================================= anillo de horizonte ==
# Color del horizonte del world 'CIELO' (construir_pista.py, rampa ec[0]): en la
# escena integrada se LEE del world (cielo_de_escena); el literal solo es el
# valor de reserva para el test del kit, que no tiene world.
CIELO_HORIZONTE = (0.70, 0.84, 0.98)
# perspectiva atmosferica horneada: fraccion de cielo (f0 a d0 m .. f1 a d1 m)
MEZCLA_DIST = (2400.0, 0.35, 4500.0, 0.55)
# materiales por fila: slot k -> sufijo (lejos comparte bosque/cumbre: 3 materiales)
_HORIZ_FILAS = {
    "cerca": ("bosque", "bosque_claro", "cumbre", "cumbre_clara", "cumbre_oscura"),
    "lejos": ("bosque", "bosque", "cumbre", "cumbre_clara", "cumbre"),
    "loma": ("bosque", "bosque_claro", "cumbre", "cumbre_clara", "cumbre_oscura"),
}
# color base de cada sufijo: (nombre en paleta.json, factor de luminancia)
_HORIZ_BASE = {
    "bosque": ("oliva_oscuro", 1.0), "bosque_claro": ("salvia", 1.0),
    "cumbre": ("caliza_ocre", 1.0), "cumbre_clara": ("caliza_ocre", 1.25),
    "cumbre_oscura": ("caliza_sombra", 1.0), "pueblo": ("marmol_casino", 1.0),   # paleta v2: blanco_roto retirado
}
_HORIZ_BASE_LEJOS = {"bosque": ("caliza_gris_calido", 1.0)}   # fila lejana gris-azul
# custom props ac_* (plan decision 5): defecto = comportamiento actual del writer
_AC_DEFECTO = (("ac_shader", "ksPerPixel"), ("ac_props", {}), ("ac_samplers", {}),
               ("ac_tex_max", 512), ("ac_alpha_test", 0), ("ac_raw", 0))

CFG_ANILLO = dict(
    r_cerca=3200.0, r_lejos=4500.0, n_cerca=4, n_lejos=5,
    largo_cerca=(1400.0, 1800.0), largo_lejos=(1500.0, 1800.0),
    alto_cerca=(380.0, 460.0), alto_lejos=(440.0, 520.0),
    n_picos=(5, 7), res=0.5, cordal_div=56, jitter_r=120.0,
    # F1 r3 (director r2, cosmetico 10 "picos de aguja"): tipos de pico de las cordilleras SIN 'aguja' (gendarmes de
    # alto/radio ~3.5 que a 3-4.5 km se leen como agujas), mayoria de domos/crestas/mesetas (1 piramide de cada 6) y
    # radio x1.5 (alto/radio de la fila trasera ~2.2 -> ~1.5: macizos romos, silueta 'Pixar'); el orden se baraja por
    # cordillera para que no se repita la misma secuencia en todo el anillo
    # F1 r4 (director r3, cosmetico 9: aun "picos de aguja" en 55/57/13/21 = crestas vistas de canto y piramides):
    # sin 'cresta' ni 'piramide'; 'lomo' (cresta roma, cap domo) en su lugar y ensanche 1.7. Tampoco 'meseta': a
    # 3-4.5 km sus paredes verticales y la cima plana se leian como bloques/losas apilados (21, 55), no como picos
    # romos. Para recuperar variedad con mesas: tipos=("domo", "lomo", "meseta", "domo", "lomo", "domo") (una linea).
    tipos=("domo", "lomo", "domo", "lomo", "domo", "lomo"), ensanche=1.7,
    abertura_centro=202.5,      # grados de BRUJULA (0 = N, 90 = E): S/SO
    abertura=160.0,             # grados abiertos (mar abierto)
    lomas_r=(2400.0, 2800.0), lomas_alto=(90.0, 130.0), lomas_radio=(200.0, 280.0),
    lomas_costa=2,              # por extremo del anillo: prolongan la costa <= 10 grados dentro de la abertura
    lomas_frente=0,             # delante del anillo (solo contexto de las aereas: desde el coche las tapa el macizo)
    # F1 r3 (director r2, menor 7): lomas 'ventana' DENTRO de la abertura, en grados hacia dentro desde el extremo O
    # del anillo (a_fin): rellenan el hueco de la linea mar/cielo de 57 (entre la roca del lazo y el islote 212.5) y
    # entran por la izquierda de 13; desde 54 asoman junto a la pared del lazo (x 700-860) y 63/56 (centro de la
    # abertura) no las ven. () = sin ellas (54 con mas mar abierto); se mantienen a >= 30 grados del centro de la
    # abertura para que 63/56 sigan mirando a mar abierto
    lomas_ventana=(40.5,), ventana_alto=(110.0, 135.0), ventana_radio=(170.0, 220.0), ventana_r=(2650.0, 2800.0),
    # F1 r4 (acotacion 2 del coordinador): 1 loma mas a 2.4-2.8 km en la ventana de 54 (horiz_az 190-215), con
    # dimensiones FIJAS (az desde a_fin, r, alto, radio, largo) y construida DESPUES de los islotes para no mover los
    # sorteos de las lomas aprobadas en r3. Az 200 (= a_fin + 32.5): desde 57 cae en el hueco de mar entre la loma
    # ventana 208 y la roca del lazo (x ~560-830), desde 13 en el hueco de la izquierda (x ~150-470), desde 54 queda
    # DETRAS de la pared del lazo (x >= 860: no resta mar abierto) y desde 63 fuera del cuadro (tras los arboles de
    # la derecha). Alto 100 m (ensayo r4a con 120 m: desde 13, camara a z 120 y lente 30 = 24 px/grado, el pie
    # cercano a 2.6 km queda 64 px bajo el horizonte y la silueta media 66 px: la regla "<= 60 px" del director la
    # descartaba en el centro; con 100 m la cima queda 9 px bajo el horizonte y la silueta mide ~55 px; desde 57 asoma
    # ~41 px sobre su pie)
    lomas_ventana_fijas=((32.5, 2650.0, 100.0, 230.0, 600.0),),
    # F1 r4: lomas (costa, ventana, islotes) de tipo 'lomo' (cresta roma) y SIN penasco-torre en la cima (a 2.5 km se
    # leia como torre/bloque: "aguja"); misma huella y misma altura de cuerpo que en r3
    lomas_tipo="lomo", lomas_pena=False,
    # islotes DENTRO de la abertura (grados respecto al centro de la abertura; mar abierto entre ellos): son la
    # unica silueta posible en la mitad visible de la linea mar/cielo de 54/61/63 sin cerrar la abertura.
    # F1 r3: mas altos (110-150 m, antes 55-80: a 2.6 km desde 63 a z 72 asomaban 4 px sobre la linea; ahora ~25 px)
    # con la MISMA huella horizontal (radio 140-190, antes 150-200): el mar abierto entre ellos no cambia
    islotes_az=(-35.0, -20.0, 2.0, 32.0), islote_faro=1, islote_pueblo=3,
    # F1 r4: tope 150 -> 140 m (mismos sorteos: 227.5 125 -> 121 m, 212.5 148 -> 138 m, 249.5 y 279.5 casi igual):
    # con la cima redondeada (lomo) la cumbre ocupa mas columnas y desde 54 (z 38) superaba los 60 px de la regla del
    # director (54 bajaba de 41 a 38 % de silueta); 63 sigue viendo 20-36 px de islote
    islote_alto=(110.0, 140.0), islote_radio=(140.0, 190.0),
    pueblos=3, faro=True, prefijo="HORIZ_")


def cielo_de_escena(defecto=CIELO_HORIZONTE):
    """Color (RGB lineal) del horizonte del world 'CIELO' de la escena: el
    elemento de menor posicion de su rampa; si no hay world, 'defecto'."""
    w = bpy.data.worlds.get("CIELO")
    if w is not None and w.node_tree is not None:
        for n in w.node_tree.nodes:
            if n.type == "VALTORGB" and len(n.color_ramp.elements):
                e = min(n.color_ramp.elements, key=lambda e: e.position)
                return tuple(float(c) for c in e.color[:3])
    return tuple(defecto)


def mezcla_cielo(rgb, dist_m, cielo=None):
    """Perspectiva atmosferica horneada: rgb lineal mezclado con el color del
    cielo del horizonte al 35 % (2.4 km) .. 55 % (4.5 km), lineal en la
    distancia y acotado. Contrato de 'mezcla' (mejorar_materiales.horizonte)."""
    d0, f0, d1, f1 = MEZCLA_DIST
    f = f0 + (f1 - f0) * _clamp((dist_m - d0) / (d1 - d0), 0.0, 1.0)
    c = tuple(cielo) if cielo is not None else cielo_de_escena()
    return tuple(_clamp(a * (1.0 - f) + b * f, 0.0, 1.0) for a, b in zip(rgb, c))


def _color_base(sufijo, fila):
    nombre, lum = (_HORIZ_BASE_LEJOS if fila == "lejos" else {}).get(sufijo, _HORIZ_BASE[sufijo])
    return _paleta().variante(nombre, lum)


def _mat_horiz(nombre, rgb, dist_m, mezcla, cielo):
    """Material plano MAT_HORIZ_* (reutilizado si existe): Base Color sin
    enlazar = diffuse_color = media lineal; custom props ac_* por defecto."""
    color = (mezcla(rgb, dist_m) if mezcla is not None else mezcla_cielo(rgb, dist_m, cielo))
    m = bpy.data.materials.get(nombre)
    nuevo = m is None
    m = _mat(nombre, color, 0.95)
    if nuevo:
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None and "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.25   # sin brillos a 3 km
        for k, v in _AC_DEFECTO:
            m[k] = v
        m["horiz_dist_m"] = float(dist_m)
        m["horiz_base_rgb"] = [float(c) for c in rgb]
        # mejorar_materiales.horizonte() (pase posterior del pipeline, propietario 'materiales') recalcula la
        # mezcla DESDE mat['horiz_color_base'] (idempotente): se deja el color de paleta SIN mezclar para que no
        # mezcle dos veces. Misma formula (35-55 % entre 2.4 y 4.5 km): el resultado coincide.
        m["horiz_color_base"] = [float(c) for c in rgb]
    return m


def materiales_horizonte(fila, dist_m, mezcla=None, cielo=None, prefijo="HORIZ_"):
    """Tupla de 5 materiales (slots 0..4) de la fila 'cerca' | 'lejos' | 'loma'
    a 'dist_m' del espectador, nombres MAT_<prefijo><fila>_<sufijo>."""
    base = "MAT_" + prefijo + fila + "_"
    out = []
    for sufijo in _HORIZ_FILAS[fila]:
        out.append(_mat_horiz(base + sufijo, _color_base(sufijo, fila), dist_m, mezcla, cielo))
    return tuple(out)


def material_pueblo(dist_m, mezcla=None, cielo=None, prefijo="HORIZ_"):
    return _mat_horiz("MAT_" + prefijo + "pueblo", _color_base("pueblo", "loma"), dist_m, mezcla, cielo)


def _caja(verts, faces, cx, cy, sx, sy, z0, z1, yaw=0.0):
    """Caja axis-aligned girada 'yaw' (8 vertices, 6 quads) entre z0 y z1."""
    c, s = math.cos(yaw), math.sin(yaw)
    b = len(verts)
    for (fx, fy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = fx * sx * 0.5, fy * sy * 0.5
        verts.append((cx + c * x - s * y, cy + s * x + c * y, z0))
    for (fx, fy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = fx * sx * 0.5, fy * sy * 0.5
        verts.append((cx + c * x - s * y, cy + s * x + c * y, z1))
    faces.extend([(b, b + 3, b + 2, b + 1), (b + 4, b + 5, b + 6, b + 7),
                  (b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                  (b + 2, b + 3, b + 7, b + 6), (b + 3, b + 0, b + 4, b + 7)])


def build_pueblecito(parent_collection, n_casas=20, seed=0, ancho=30.0, fondo=10.0,
                     alto=8.0, extension=(240.0, 50.0), z_base=_Z_PIE, campanile=True,
                     materiales=None, prefijo="HORIZ_"):
    """Pueblecito-silueta: n cajas crema (ancho x fondo x alto nominales, +-30 %)
    repartidas en una franja 'extension' a lo largo de X local (la costa), con
    la base hundida a z_base (nunca flotan sobre la loma ni el agua) y un
    campanile (caja esbelta x2.2 de alto). UNA malla '<prefijo>pueblo', un
    solo material (slot 0; 'materiales' = tupla de 1). <= 300 tris."""
    rng = random.Random(int(seed) * 613 + 5)
    verts, faces = [], []
    ex, ey = extension
    for i in range(int(n_casas)):
        t = (i + rng.uniform(0.15, 0.85)) / max(n_casas, 1)
        cx = -ex * 0.5 + ex * t
        cy = rng.uniform(-ey * 0.5, ey * 0.5)
        _caja(verts, faces, cx, cy, ancho * rng.uniform(0.7, 1.3), fondo * rng.uniform(0.8, 1.4),
              z_base, alto * rng.uniform(0.75, 1.5), rng.uniform(-0.25, 0.25))
    if campanile:
        _caja(verts, faces, rng.uniform(-ex * 0.25, ex * 0.25), rng.uniform(-ey * 0.3, ey * 0.3),
              6.0, 6.0, z_base, alto * 2.2, rng.uniform(-0.3, 0.3))
    mats = materiales or (material_pueblo(2600.0, prefijo=prefijo),)
    ob = _malla(prefijo + "pueblo", verts, faces, parent_collection, materiales=mats)
    for p in ob.data.polygons:
        p.use_smooth = False
    ob["horiz_n_casas"] = int(n_casas)
    return ob


def build_faro(parent_collection, alto=30.0, seed=0, radio=3.2, z_base=_Z_PIE,
               materiales=None, prefijo="HORIZ_"):
    """Faro lejano: casa del farero (caja 14 x 10 x 5) + torre octogonal
    troncoconica (radio -> 0.75 radio) + linterna oscura + remate piramidal.
    UNA malla '<prefijo>faro' (~120 tris): slot 0 = crema, slot 1 = oscuro."""
    rng = random.Random(int(seed) * 97 + 1)
    verts, faces = [], []
    _caja(verts, faces, 7.0, 0.0, 14.0, 10.0, z_base, 5.0, rng.uniform(-0.2, 0.2))
    n = 8
    anillos = []
    for (z, r) in ((z_base, radio), (0.0, radio), (alto, radio * 0.75),
                   (alto, radio * 0.95), (alto + 3.5, radio * 0.95)):
        ring = []
        for k in range(n):
            th = 2.0 * math.pi * (k + 0.5) / n
            ring.append(len(verts))
            verts.append((math.cos(th) * r, math.sin(th) * r, z))
        anillos.append(ring)
    for a, b in zip(anillos, anillos[1:]):
        for k in range(n):
            faces.append((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    top = len(verts)
    verts.append((0.0, 0.0, alto + 6.0))
    for k in range(n):
        faces.append((top, anillos[-1][(k + 1) % n], anillos[-1][k]))
    bot = len(verts)
    verts.append((0.0, 0.0, z_base))
    for k in range(n):
        faces.append((bot, anillos[0][k], anillos[0][(k + 1) % n]))
    if materiales is None:
        mats = materiales_horizonte("loma", 2600.0, prefijo=prefijo)
        materiales = (material_pueblo(2600.0, prefijo=prefijo), mats[4])
    ob = _malla(prefijo + "faro", verts, faces, parent_collection, materiales=materiales)
    n_f = len(ob.data.polygons)
    for p in ob.data.polygons:
        p.use_smooth = False
        c = p.center
        if c.z > alto + 0.5 and p.index < n_f - n:      # linterna y remate: oscuro
            p.material_index = 1
    ob["horiz_alto"] = float(alto)
    return ob


def _centro_rejilla(terreno, centro):
    if centro is not None:
        return float(centro[0]), float(centro[1])
    if terreno is None:
        raise ValueError("build_anillo_horizonte: hace falta terreno=T (x0, y0, cell, nx, ny) o centro=(x, y)")
    return (float(terreno["x0"]) + (int(terreno["nx"]) - 1) * float(terreno["cell"]) * 0.5,
            float(terreno["y0"]) + (int(terreno["ny"]) - 1) * float(terreno["cell"]) * 0.5)


def _tris_ob(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def matriz_mundo(ob):
    """loc/rot/scale compuestos a mano (matrix_world no se actualiza en
    --background hasta view_layer.update()); los objetos del anillo no
    tienen padre."""
    return (Matrix.Translation(ob.location) @ ob.rotation_euler.to_matrix().to_4x4() @
            Matrix.Diagonal((ob.scale[0], ob.scale[1], ob.scale[2], 1.0)))


def _fuera_de_rejilla(objs, terreno):
    """Lista de objetos con algun vertice (en mundo) DENTRO de la rejilla."""
    if terreno is None:
        return []
    x0 = float(terreno["x0"]); y0 = float(terreno["y0"])
    x1 = x0 + (int(terreno["nx"]) - 1) * float(terreno["cell"])
    y1 = y0 + (int(terreno["ny"]) - 1) * float(terreno["cell"])
    malos = []
    for ob in objs:
        mw = matriz_mundo(ob)
        for v in ob.data.vertices:
            w = mw @ v.co
            if x0 <= w.x <= x1 and y0 <= w.y <= y1:
                malos.append(ob.name)
                break
    return malos


def build_anillo_horizonte(parent_collection, terreno=None, centro=None, seed=0,
                           mezcla=None, cielo=None, **cfg):
    """Anillo de horizonte HORIZ_ alrededor del centro de la rejilla del
    terreno (ver docstring del modulo). cfg: claves de CFG_ANILLO. Devuelve
    un dict con objetos, tris, materiales y la geometria del anillo (angulos
    en grados matematicos: 0 = +X (E), 90 = +Y (N))."""
    C = dict(CFG_ANILLO)
    C.update(cfg)
    pref = C["prefijo"]
    cx, cy = _centro_rejilla(terreno, centro)
    rng = random.Random(int(seed) * 7001 + 3)
    if cielo is None:
        cielo = cielo_de_escena()
    # --- abertura (brujula -> matematico): anillo de a_ini a a_fin (antihorario)
    c_mat = 90.0 - float(C["abertura_centro"])
    arco = 360.0 - float(C["abertura"])
    a_ini = c_mat + float(C["abertura"]) * 0.5
    a_fin = a_ini + arco
    objetos, cordilleras, lomas, pueblos, faros = [], [], [], [], []

    def colocar(ob, az, r, yaw_extra=0.0):
        a = math.radians(az)
        ob.location = (cx + math.cos(a) * r, cy + math.sin(a) * r, 0.0)
        ob.rotation_euler = (0.0, 0.0, a + math.pi * 0.5 + yaw_extra)   # +Y local -> centro
        ob["horiz_az"] = float(az % 360.0)
        ob["horiz_r"] = float(r)
        objetos.append(ob)

    def tipos_cordillera():
        """Secuencia de tipos de pico (sin 'aguja') barajada por cordillera; None = mezcla del kit."""
        t = list(C.get("tipos") or ())
        if not t:
            return None
        rng.shuffle(t)
        return t

    # --- fila cercana (verde-azulada, casi toda bosque)
    m_cerca = materiales_horizonte("cerca", C["r_cerca"], mezcla, cielo, pref)
    n_c = int(C["n_cerca"])
    for i in range(n_c):
        az = a_ini + (i + 0.5) * arco / n_c + rng.uniform(-2.0, 2.0)
        r = C["r_cerca"] + rng.uniform(-C["jitter_r"], C["jitter_r"])
        largo = rng.uniform(*C["largo_cerca"])
        alto = rng.uniform(*C["alto_cerca"])
        ob = build_cordillera(parent_collection, largo=largo, n_picos=rng.randint(*C["n_picos"]),
                              seed=seed * 100 + i, alto=alto, res=C["res"], pie=True,
                              cordal_div=C["cordal_div"], prefijo=pref, materiales=m_cerca,
                              unir=True, linea_arboles=1.2, tipos=tipos_cordillera(),
                              ensanche=C.get("ensanche", 1.0))
        ob["horiz_fila"] = "cerca"
        colocar(ob, az, r)
        cordilleras.append(dict(nombre=ob.name, fila="cerca", az=az % 360.0, r=r, largo=largo,
                                alto=alto, tris=_tris_ob(ob)))
    # --- fila lejana (gris-azul, cumbres de roca): tapa los huecos de la cercana
    m_lejos = materiales_horizonte("lejos", C["r_lejos"], mezcla, cielo, pref)
    n_l = int(C["n_lejos"])
    largos = [rng.uniform(*C["largo_lejos"]) for _ in range(n_l)]
    semi = [math.degrees(0.5 * lg / C["r_lejos"]) for lg in largos]
    for i in range(n_l):
        # repartidas de extremo a extremo del arco (con n_lejos = n_cerca + 1 caen en los
        # huecos de la fila cercana) y recogidas hacia dentro en los extremos
        az = a_ini + i * arco / max(n_l - 1, 1)
        az = _clamp(az, a_ini + semi[i], a_fin - semi[i]) + rng.uniform(-1.5, 1.5)
        r = C["r_lejos"] + rng.uniform(-C["jitter_r"], C["jitter_r"])
        alto = rng.uniform(*C["alto_lejos"])
        ob = build_cordillera(parent_collection, largo=largos[i], n_picos=rng.randint(*C["n_picos"]),
                              seed=seed * 100 + 50 + i, alto=alto, res=C["res"], pie=True,
                              cordal_div=C["cordal_div"], prefijo=pref, materiales=m_lejos, unir=True,
                              tipos=tipos_cordillera(), ensanche=C.get("ensanche", 1.0))
        ob["horiz_fila"] = "lejos"
        colocar(ob, az, r)
        cordilleras.append(dict(nombre=ob.name, fila="lejos", az=az % 360.0, r=r, largo=largos[i],
                                alto=alto, tris=_tris_ob(ob)))
    # --- lomas de costa (2.4-2.8 km): extremos del anillo, frente e islotes
    r_lo = rng.uniform(*C["lomas_r"])
    m_loma = materiales_horizonte("loma", r_lo, mezcla, cielo, pref)
    m_pueblo = (material_pueblo(r_lo, mezcla, cielo, pref),)
    plan_lomas = []                      # (az, clase, pueblo?, faro?)
    nc = int(C["lomas_costa"])
    for j in range(nc):                  # extremo final (a_fin) y extremo inicial (a_ini)
        dentro = 10.0 - j * 13.0         # +10 (dentro de la abertura), -3, -16 ...
        plan_lomas.append((a_fin + dentro, "costa", j == 0, False))
        plan_lomas.append((a_ini - dentro, "costa", j == 0, False))
    nf = int(C["lomas_frente"])
    for j in range(nf):
        plan_lomas.append((a_ini + arco * (0.3 + 0.35 * j / max(nf - 1, 1)), "frente", False, False))
    for off in C.get("lomas_ventana", ()):              # F1 r3: hueco de 57 (ver CFG_ANILLO)
        plan_lomas.append((a_fin + float(off), "ventana", False, False))
    for j, off in enumerate(C["islotes_az"]):           # dentro de la abertura (S/SO)
        plan_lomas.append((c_mat + float(off), "islote", j == int(C["islote_pueblo"]), j == int(C["islote_faro"])))
    plan_lomas = [p + (None,) for p in plan_lomas]      # (az, clase, pueblo?, faro?, dims fijas | None)
    for (off, r_fix, alto_fix, radio_fix, largo_fix) in C.get("lomas_ventana_fijas", ()):   # F1 r4 (ver CFG_ANILLO)
        plan_lomas.append((a_fin + float(off), "ventana", False, False,
                           (float(r_fix), float(alto_fix), float(radio_fix), float(largo_fix))))
    n_pueblos = int(C["pueblos"])
    tipo_largo = str(C.get("lomas_tipo", "cresta"))
    for k, (az, clase, quiere_pueblo, quiere_faro, fijo) in enumerate(plan_lomas):
        if fijo is not None:                 # dimensiones fijas, sin sorteo (van las ultimas: no mueven los demas)
            rr, alto, radio, largo = fijo
        else:
            rr = rng.uniform(*C["lomas_r"])
        if fijo is not None:
            pass
        elif clase == "islote":
            # cresta corta (2-4 cumbres): silueta dentada, no un domo que a 2.5 km se lee como un disco
            alto = rng.uniform(*C["islote_alto"]); radio = rng.uniform(*C["islote_radio"])
            largo = radio * rng.uniform(1.8, 2.2)
        elif clase == "ventana":
            # cresta corta y alta en el hueco de 57: mas lejos que los islotes (2.65-2.8 km) para que no los tape
            rr = rng.uniform(*C.get("ventana_r", C["lomas_r"]))
            alto = rng.uniform(*C.get("ventana_alto", C["lomas_alto"]))
            radio = rng.uniform(*C.get("ventana_radio", C["lomas_radio"]))
            largo = radio * rng.uniform(2.0, 2.4)
        else:
            alto = rng.uniform(*C["lomas_alto"]); radio = rng.uniform(*C["lomas_radio"])
            largo = radio * rng.uniform(2.2, 2.8) if clase == "costa" else None
        quiere_faro = bool(C["faro"]) and quiere_faro
        ob = build_loma(parent_collection, alto=alto, radio=radio, seed=seed * 100 + 70 + k,
                        pena=(not quiere_faro) and bool(C.get("lomas_pena", True)), largo=largo, res=C["res"],
                        prefijo=pref, materiales=m_loma, unir=True, tipo_largo=tipo_largo)
        ob["horiz_fila"] = "loma_" + clase
        colocar(ob, az, rr)
        lomas.append(dict(nombre=ob.name, clase=clase, az=az % 360.0, r=rr, alto=alto, radio=radio,
                          largo=largo, tris=_tris_ob(ob)))
        if quiere_pueblo and len(pueblos) < n_pueblos:
            pu = build_pueblecito(parent_collection, n_casas=20, seed=seed * 100 + 80 + k,
                                  materiales=m_pueblo, prefijo=pref)
            # en la orilla que mira al circuito: 1.02 radios hacia el centro (pie de la
            # loma; la cresta alargada tambien tiene semieje transversal = radio)
            hacia = radio * 1.02
            colocar(pu, az, rr - hacia)
            pu["horiz_fila"] = "pueblo"
            pueblos.append(dict(nombre=pu.name, az=az % 360.0, r=rr - hacia, tris=_tris_ob(pu)))
        if quiere_faro:
            cima = max(ob.data.vertices, key=lambda v: v.co.z).co
            fa = build_faro(parent_collection, alto=30.0, seed=seed + k, z_base=-4.0,
                            materiales=(m_pueblo[0], m_loma[4]), prefijo=pref)
            # sobre la cima del islote (coordenadas locales de la loma -> mundo)
            a = math.radians(az)
            M = Matrix.Translation((cx + math.cos(a) * rr, cy + math.sin(a) * rr, 0.0)) @ \
                Matrix.Rotation(a + math.pi * 0.5, 4, "Z")
            w = M @ Vector((cima.x, cima.y, cima.z))
            fa.location = (w.x, w.y, w.z)
            fa.rotation_euler = (0.0, 0.0, a + math.pi * 0.5)
            fa["horiz_az"] = float(az % 360.0); fa["horiz_r"] = float(rr); fa["horiz_fila"] = "faro"
            objetos.append(fa)
            faros.append(dict(nombre=fa.name, az=az % 360.0, r=rr, z=w.z, tris=_tris_ob(fa)))
    malos = _fuera_de_rejilla(objetos, terreno)
    if malos:
        raise ValueError("anillo de horizonte DENTRO de la rejilla del terreno: %s" % ", ".join(malos))
    mats = sorted({m.name for ob in objetos for m in ob.data.materials if m is not None})
    return dict(objetos=objetos, tris=sum(_tris_ob(o) for o in objetos), materiales=mats,
                cordilleras=cordilleras, lomas=lomas, pueblos=pueblos, faros=faros,
                centro=(cx, cy), cielo=tuple(cielo),
                abertura=dict(centro_brujula=float(C["abertura_centro"]), grados=float(C["abertura"]),
                              anillo_ini=a_ini % 360.0, anillo_fin=a_fin % 360.0, arco=arco))


def build(parent_collection, seed=0, **params):
    """Cordillera de fondo completa. Devuelve el Empty MONT_cordillera."""
    return build_cordillera(parent_collection, seed=seed, **params)
