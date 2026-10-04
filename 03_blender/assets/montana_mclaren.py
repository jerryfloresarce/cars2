"""montana_mclaren.py — El McLAREN DE PIEDRA de Porto Corsa (Cars 2), ronda 15.

Blender 5.1. Misma API publica que montana_coche_v2.py (y reutiliza sus
helpers de malla: materiales, _tubo/_capsula/_revolucion, _disco_rueda,
_cinta, _pedrusco, _cerrar_en, _boolean_cadena, _pulir...) pero el coche
fosil es un McLAREN 720S/P1 INTEGRADO en un cerro de roca:

  * SILUETA (unid. R = radio de rueda): largo ~13R (morro +2.9R, zaga
    -10.1R), batalla 7.6R (rueda trasera en x=-7.6R), via = `ancho`, techo
    en 3.4R sobre el suelo del coche (2.4R sobre el buje). Morro bajo y
    afilado con SPLITTER, boca inferior oscura, faros "ojo" rasgados
    (cuenca excavada + barra LED de hueso), pasos de rueda muy marcados
    (aletas delanteras en pico y caderas anchas), cintura alta, canal
    lateral que desemboca en TOMAS DE AIRE profundas delante de las caderas,
    cabina en lagrima con parabrisas muy tumbado (~25 grados), luneta
    descendente, zaga corta con ALERON sobre dos pilones, difusor/escapes.
    Llantas fosiles de 10 radios (disco de montana_coche_v2), neumaticos
    anchos.
  * PIEDRA: caliza con estratos finos (0.13R) en la roca, grano suave en la
    carroceria, grietas (surcos quebrados de 0.10-0.15R con labios en
    bisel, rama secundaria solo si mide >= 0.5R, fondo 0.045R, material
    MAT_MCOCHE_caliza_grieta = caliza -13 %: ronda 15, B13 v1/v3),
    desconchones (casquetes claros), cristales =
    piedra oscura pulida (MAT_MCOCHE_cristal_pulido). Nada de colores de
    coche. Musgo/matas solo sobre apoyo franco (nz >= 0.6) y orientados a
    el (B15).
  * INTEGRADO EN LA MONTANA: la zaga (desde x=-4.4R hacia atras) se funde en
    un macizo que lame el flanco, cubre la mitad baja de las ruedas traseras
    y sube por detras de la cola hasta una CRESTA de `alto_montana`
    (defecto 3.2R: por encima del techo, 2.9R) a 1.4R detras de la cola,
    con laterales en talud `talud_deg`; el coche emerge del cerro (cabina,
    caderas y aleron fuera de la roca). `enterrado='morro'` entierra el
    morro (faros medio tapados, cresta a 3.8R) en vez de la zaga.
    `largo_macizo` (unid. R desde el origen) reescala el macizo; 0 = sin
    macizo (solo el pedestal). `enterrado='ambos'` = macizo de la zaga +
    afloramiento rocoso en el morro (alto_montana y largo_macizo admiten
    un par (zaga, morro)). `ancho_macizo` y `talud_deg` admiten un par
    (lado -Y, lado +Y) para encajar un lado contra la pista.
  * SITIO (ronda 15, comprobado con encaje_mclaren sobre geometria_3d con
    el terreno T1): detras del tunel, en el lado de tierra (-n), la pista
    vuelve en horquilla (curvas 4-6, s 780-1020) a 60-260 m del origen, de
    modo que la orientacion 'morro al mar' (+X = +n) pisa la horquilla con
    cualquier R (123 muestras con R=26, 68 sin macizo, 8 con R=16). La
    unica orientacion valida es la ACTUAL del integrador (+X = -n, morro
    tierra adentro, lado_visible=-1): el morro se hunde en la ladera T1
    (42-58 m sobre z=0 a 40-75 m del origen; el capo asoma) y la zaga sale
    de un PENON en el mar (macizo de la zaga, 62 % de la huella sobre el
    agua, con base en z_fondo = -(z_pista + 8)). Configuracion recomendada
    (0 muestras de pista bajo la huella, sin tocar el terreno):
      build(col, radio=26, ancho=135, z_fondo=-(pf.z + 8), seed=11,
            lado_visible=-1, enterrado='ambos', alto_montana=(83.2, 65.0),
            largo_macizo=(14.5, 4.8), talud_deg=(38.0, 52.0))
    ('zaga' solo = sin afloramiento en el morro; tambien valida).
    Medido el 03/10 con el terreno actual (encaje_mclaren, seed=11 del
    integrador): el 'Espolon del coche' de T1 entierra el morro hasta 39 m
    (asoma el 68 % del techo del morro); 0 muestras de pista a < 2 m del
    borde, 6 (s 718-728) entre 2 y 6 m: el pie del afloramiento del morro
    junto a la salida del tunel, 1-3 m sobre la calzada. Alargar el morro
    (7R/95 m, 8.5R/110 m) pisa la horquilla (68-85 muestras, s 716-888);
    acortarlo (2.5R/40 m) o quitarlo ('zaga') sin recortar el terreno
    deja el morro AUN MAS bajo la ladera (asoma 47-50 %, hasta 56-78 m).
  * Base: pedestal/zocalo bajo el coche (|y| = flanco - 0.05R, pie en
    talud) hasta z_fondo con base plana; zona prohibida |y| <= W/2 + 2.5
    para x en [-1.3R, 1.5R] (tunel del integrador a traves de la rueda
    delantera, a lo largo de Y, caja 21 x 9.5 m en x=-0.65R desde z=0).

  * RONDA 15 v2 (B2-06/B2-10/N1): bloques de _celda con juntas SUAVIZADAS
    (_celda_suave: meseta por bloque y transicion smoothstep de 0.5 celda;
    antes escalones de 5 m que se leian como pixeles) y peso menor; roca
    con sombreado suave (aristas > 30 grados vivas, _pulir); franja oscura
    SOLO en la linea de agua (z_agua) con estratos hasta el mar; falda en
    talud (~70 grados) y relieve franco del pedestal entre las ruedas
    fuera de la zona del tunel (alli la roca es la de la v1: los Boolean
    del tunel estan probados con ella); techo de la meseta del macizo
    LEJOS del coche con hierba (MAT_terreno de la escena, o
    MAT_MCOCHE_hierba) y bancos de caliza meteorizada
    (MAT_MCOCHE_caliza_monte), con pinos y matas en la hierba: el cerro
    pasa de roca a monte.
  * RONDA 15 v3 (J10 c / B15 / B11 / B13), _contacto_terreno sobre la malla
    final (solo materiales; nunca carroceria, ruedas, roca mojada ni zona
    del tunel): la caliza del macizo a mas de 1.6-2.4R de la huella del
    coche (limite por estrato) y la falda del pedestal bajo umbral - 0.25R
    pasan a caliza meteorizada, ahora en el tono de la roca del TERRENO: el
    cerro deja de ser una escultura blanca suelta. build(terreno='auto') conoce ademas el TERRENO
    real del sitio (encaje_mclaren.sitio_de_build + TerrenoMalla: solo con
    los parametros del integrador y una malla TERRENO en la escena; o un
    callable f(lx, ly) -> (z_local, es_mar)). Con el: (a) la roca a menos
    de 3-7 m sobre el terreno toma MAT_terreno y la caliza base hasta 16-34
    m, caliza meteorizada (continuidad con la ladera); (b) las cuencas
    oscuras (_M_HUECO, salvo pasa-ruedas) medio enterradas pasan a caliza
    (el faro +Y del morro, a 2.7 m del suelo, se leia como la boca de una
    cueva); (c) ninguna mata ni pino donde el terreno los tapa (antes 17 de
    82 islas bajo el TERRENO); con o sin terreno, fuera tambien las islas
    voladas a > 0.4 m de su apoyo. Grietas: surcos de 0.10-0.15R con bisel
    (labio a ~24 grados, sombreado suave), caliza -13 % y solo ramas de
    >= 0.5R. Red de seguridad de la cadena Boolean: una candidata
    derrumbada (< 60 % de caras) no gana nunca y, si ninguna sale limpia,
    se rehace con los cortes sin grietas (mesh["mcoche_grietas"] = 0).

API:
  build(parent_collection, radio=40.0, ancho=78.0, alto_base=12.0,
        z_fondo=-45.0, seed=0, con_vegetacion=True, n_radios=10,
        segmentos_por_radio=7, talud_deg=38.0, solver="MANIFOLD",
        detalle_secundario=0.6, lado_visible=+1, enterrado="zaga",
        alto_montana=None, largo_macizo=None, ancho_macizo=1.0,
        z_agua=None, terreno='auto')
      (enterrado 'zaga' | 'morro' | 'ambos'; alto_montana None = 3.2R zaga /
       2.5R morro; largo_macizo None = 14.5R zaga / 4.8R morro, 0 = sin
       macizo; con 'ambos' ambos admiten un par (zaga, morro); talud_deg y
       ancho_macizo admiten un par (lado -Y, lado +Y); z_agua = cota LOCAL
       del mar, None = z_fondo + 9.4 (convencion del integrador: z_fondo =
       -(z_pista + 8) y origen a z_pista - 1.4, asi que el mar queda en
       1.4 - z_pista))
      -> malla raiz MCOCHE_roca (unica, cerrada, manifold) + hijo MCOCHE_veg.
         Props: obj["radio"], ["ancho"], ["alto_base"], ["z_fondo"],
         ["hubs"], ["huella_x"], ["bbox"], ["lado_visible"], ["enterrado"],
         ["alto_montana"], ["largo_macizo"], ["talud_deg"], ["ancho_macizo"];
         mesh["mcoche_no_manifold"] (0), ["mcoche_solver"].
  podar_vegetacion(raiz_colocada, oclusores, holgura=0.5) -> (islas, borradas)
      (integrador, con el coche ya en su sitio: quita las matas/pinos de
       MCOCHE_veg que tapan el TERRENO, las CASAS_ u otra malla de la
       escena: rayo vertical hacia arriba desde lo mas alto de cada isla).

Convenciones (metros): origen = centro de la rueda delantera en planta,
+X morro, -X zaga, z=0 suelo local; bujes en (0, +-W/2, R-alto_base) y
(-7.6R, +-W/2, R-alto_base); cara del neumatico en |y| = W/2.
ORIENTACION EN LA PISTA (integrar_escena.zona_tunel, verificado con la
geometria): el tunel va a lo largo de +-Y local, en x=-0.65R. Si el
integrador pone +X local = -n (ang_c = atan2(-ny, -nx), morro tierra
adentro), +Y local = t y los coches LLEGAN por -Y: lado_visible=-1. Si
pone +X local = +n (morro al mar), +Y local = -t y llegan por +Y:
lado_visible=+1. Encaje en el sitio: ver test_montana_mclaren.py
(seccion 'sitio': muestras de pista bajo la huella, terreno vs coche).
Alturas de la carroceria relativas al BUJE (dz, unid. R): umbral -0.45,
cintura +0.72 (caderas +0.96), hombro/capo +1.24 (pico de aleta), techo
+2.36, aleron +2.02, cubierta trasera +1.70. Las lineas claras horizontales
de la carroceria (bisect cada 4 band_h) coinciden con las bandas claras de
indice 0 de la roca: la talla atraviesa los mismos estratos.
Tras la cadena Boolean, _limpiar() colapsa aristas < 2 mm y elimina
cascaras sueltas (< 12 caras): sin ello el solver EXACT del integrador
(tunel) devolvia una malla vacia. Comprobado: EXACT y MANIFOLD perforan
la caja del tunel limpiamente (test_montana_mclaren.py).
Materiales (indices fijos, los 0-4 los mismos que la v2): 0 MAT_MCOCHE_caliza,
1 _caliza_clara, 2 _caliza_oscura, 3 _hueco, 4 _hueso,
5 MAT_MCOCHE_cristal_pulido, 6 MAT_MCOCHE_caliza_grieta (ronda 15),
7 hierba del monte (MAT_terreno si ya existe en la escena; si no,
MAT_MCOCHE_hierba), 8 MAT_MCOCHE_caliza_monte (ronda 15 v2; ningun nombre
lleva 'roca' ni 'piedra': integrar._paredes_de_roca y aplicar_texturas no
los confunden); veg: MAT_MCOCHE_veg/_veg_clara/_tronco.
Cadena Boolean (depsgraph, temporales en bpy.context.scene.collection):
roca U bloques U carroceria U cabina - pasa-ruedas U ruedas U detalles_a
U detalles_b - cristales - cortes - ramas de grietas U luces (cada
operando sin solapes internos: las ramas arrancan dentro de su grieta y
por eso van en un operando aparte).
"""

import importlib.util
import math
import os
import random

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


# ------------------------------------------------- helpers de la v2 ----------
def _cargar_v2():
    aqui = os.path.dirname(os.path.abspath(__file__))
    ruta = os.path.join(aqui, "montana_coche_v2.py")
    spec = importlib.util.spec_from_file_location("montana_coche_v2_para_mclaren", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_V2 = _cargar_v2()
_n3 = _V2._n3
_hash01 = _V2._hash01
_sstep = _V2._sstep
_spline = _V2._spline
_sq = _V2._sq
_ridged = _V2._ridged
_celda = _V2._celda
_onda_estrato = _V2._onda_estrato
_blob = _V2._blob
_pino = _V2._pino
_mat = _V2._mat
_add_face = _V2._add_face
_malla = _V2._malla
_objeto = _V2._objeto
_tubo = _V2._tubo
_capsula = _V2._capsula
_revolucion = _V2._revolucion
_disco_rueda = _V2._disco_rueda
_cinta = _V2._cinta
_domo = _V2._domo
_pedrusco = _V2._pedrusco
_lin = _V2._lin
_cerrar_en = _V2._cerrar_en
_fusionar = _V2._fusionar
_boolean_cadena = _V2._boolean_cadena
_pulir = _V2._pulir

_M_CAL, _M_CLARA, _M_OSC, _M_HUECO, _M_HUESO, _M_CRISTAL = 0, 1, 2, 3, 4, 5
_M_GRIETA = 6             # paredes de las grietas (ronda 15, B13): caliza un 30 % mas oscura
_M_HIERBA = 7             # hierba del monte en el techo de la meseta del macizo (ronda 15 v2, N1)
_M_MONTE = 8              # caliza meteorizada (gris ocre) del macizo lejos del coche (v2, N1/E2-12)
# ronda 15 v2 (B2-06/B2-10): relieve de la roca
_Z_AGUA_SOBRE_FONDO = 9.4   # z_agua por defecto = z_fondo + 9.4 (convencion del integrador)
_FRANJA_AGUA = 1.0          # m de roca mojada (caliza oscura) sobre la linea de agua
_K_FALDA = 0.36             # falda del pedestal: +0.36 m de ancho por m de bajada (~70 grados)
_K_CEL_MACIZO = 1.0         # peso de los bloques (antes 2.2 con escalon duro: 'pixeles')
_K_CEL_PEDESTAL = 0.6       # (antes 1.2)
_JUNTA_CELDA = 0.25         # media anchura de la junta suavizada, en fraccion de celda
_TAPA_MIN = 0.94            # hierba en el techo de la meseta: sin(th)^(2/2.6) de la seccion >= ~0.94
_HIERBA_D = 0.6             # unid. R: ni hierba ni caliza meteorizada a menos de esto del coche


def _mat_hierba():
    """Hierba del macizo: el MISMO material del terreno de la escena
    (MAT_terreno, de construir_pista: color por cota y pendiente en
    coordenadas de mundo) para que el cerro empalme con el monte; en una
    escena sin terreno (test) un verde parecido."""
    m = bpy.data.materials.get("MAT_terreno")
    if m is not None:
        return m
    return _V2._mat_piedra("MAT_MCOCHE_hierba", (0.165, 0.300, 0.085),
                           (0.235, 0.380, 0.120), 0.97, 0.035, 0.15)


_TONO_GRIETA = ((0.522, 0.426, 0.287), (0.644, 0.566, 0.426))   # caliza -13 % (v3, B13; v1: -30 %)
# v3 (J10 c): caliza meteorizada = el tono de la roca del TERRENO (construir_pista._roca_terreno:
# 0.30/0.235/0.15 - 0.46/0.37/0.245) un punto mas clara; v2: (0.400, 0.352, 0.268) gris ocre claro,
# que al sol se leia tan blanco como la caliza del coche
_TONO_MONTE = ((0.34, 0.28, 0.19), (0.46, 0.385, 0.27))


def _retintar(m, color, color2):
    """Pone los tonos de un material de _mat_piedra que ya existia en la
    escena (de una version anterior): diffuse_color (lo que lee el kn5),
    Base Color y los dos extremos de su rampa de moteado."""
    m.diffuse_color = (*color, 1.0)
    if m.node_tree is None:
        return
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED" and not n.inputs["Base Color"].links:
            n.inputs["Base Color"].default_value = (*color, 1.0)
        elif n.type == "VALTORGB" and len(n.color_ramp.elements) >= 2:
            n.color_ramp.elements[0].color = (*color, 1.0)
            n.color_ramp.elements[-1].color = (*color2, 1.0)


def _mats_mc():
    """Los 5 primeros materiales de la v2 (caliza, clara, oscura, hueco,
    hueso) + cristal de piedra oscura PULIDA (rugosidad baja) + caliza de
    GRIETA (indice 6: la caliza base oscurecida un 13 %; v1 -30 %, que de
    lejos daba lineas oscuras como ramitas; antes aun, la caliza oscura) +
    hierba (7) y caliza meteorizada del monte (8, v3: el tono de la roca
    del TERRENO, _TONO_MONTE)."""
    base = _V2._mats_roca()
    cristal = _mat("MAT_MCOCHE_cristal_pulido", (0.050, 0.062, 0.080), 0.26, 0.60)
    grieta = _V2._mat_piedra("MAT_MCOCHE_caliza_grieta", _TONO_GRIETA[0], _TONO_GRIETA[1],
                             0.95, 0.06)
    _retintar(grieta, *_TONO_GRIETA)
    monte = _V2._mat_piedra("MAT_MCOCHE_caliza_monte", _TONO_MONTE[0], _TONO_MONTE[1], 0.96, 0.035)
    _retintar(monte, *_TONO_MONTE)
    return tuple(base[:5]) + (cristal, grieta, _mat_hierba(), monte)


def _mats_veg():
    return _V2._mats_veg()


# ----------------------------------------------------------- layout (R) -----
_X_REAR = -7.6            # rueda trasera
_X_TAIL, _X_NOSE = -10.1, 2.9
_Y_BODY = 0.03            # flanco maximo (aletas): W/2 - 0.03R
_Y_WALL = 0.09            # plano del zocalo junto a las ruedas (collar del disco)
_WELL_R = 1.12            # radio del pasa-ruedas
_WELL_D = 0.36            # fondo del pasa-ruedas: |y| = W/2 - 0.36R
_BAND_H = 0.13            # estratos finos de la roca (unid. R)
_JUNTAS = (-1.72, -4.95)  # juntas de puerta (x/R)
# lineas de la carroceria baja (x/R -> dz/R sobre el buje, o fraccion de wmax)
_ZF = [(-10.1, -0.08), (-9.7, -0.22), (-9.2, -0.38), (-8.6, -0.45), (0.6, -0.45),
       (1.6, -0.44), (2.3, -0.41), (2.7, -0.36), (2.9, -0.31)]
_ZB = [(-10.1, 0.78), (-9.4, 0.88), (-8.4, 0.96), (-7.6, 0.96), (-6.7, 0.88),
       (-5.6, 0.74), (-3.0, 0.70), (-1.0, 0.72), (0.0, 0.76), (0.8, 0.72),
       (1.6, 0.58), (2.3, 0.40), (2.9, 0.18)]
_ZD = [(-10.1, 1.42), (-9.6, 1.58), (-9.0, 1.67), (-8.2, 1.70), (-7.6, 1.64),
       (-6.8, 1.52), (-6.0, 1.44), (-5.0, 1.40), (-4.0, 1.36), (-3.0, 1.31),
       (-2.0, 1.27), (-1.2, 1.24), (-0.4, 1.23), (0.1, 1.24), (0.6, 1.16),
       (1.2, 1.00), (1.8, 0.78), (2.3, 0.56), (2.7, 0.35), (2.9, 0.22)]
_CR = [(-10.1, 0.02), (-8.2, 0.03), (-6.8, 0.0), (-5.2, 0.03), (-3.0, 0.06),
       (-1.6, 0.0), (-0.8, -0.09), (0.0, -0.14), (0.6, -0.14), (1.2, -0.10),
       (1.8, -0.05), (2.4, -0.01), (2.9, 0.01)]
# inset del hombro (fraccion de w) y radio de la arista del hombro (R):
# caderas y aletas redondeadas (bulto sobre la rueda), puertas con arista viva
_SH = [(-10.1, 0.80), (-8.5, 0.80), (-7.6, 0.78), (-6.4, 0.84), (-5.2, 0.92),
       (-3.5, 0.93), (-1.6, 0.92), (-0.4, 0.85), (0.2, 0.84), (1.0, 0.86),
       (2.0, 0.90), (2.9, 0.92)]
_SR = [(-10.1, 0.18), (-8.5, 0.18), (-7.6, 0.20), (-6.4, 0.16), (-5.2, 0.06),
       (-3.5, 0.05), (-1.6, 0.06), (-0.4, 0.09), (0.2, 0.08), (1.0, 0.07),
       (2.0, 0.06), (2.9, 0.06)]
_WB = [(-10.1, 0.84), (-9.7, 0.93), (-9.0, 0.99), (-7.6, 1.0), (-6.6, 0.985),
       (-6.0, 0.95), (-5.4, 0.905), (-3.6, 0.90), (-2.2, 0.915), (-1.2, 0.955),
       (-0.4, 0.995), (0.2, 1.0), (0.8, 0.975), (1.4, 0.90), (1.9, 0.79),
       (2.3, 0.66), (2.6, 0.53), (2.8, 0.40), (2.9, 0.30)]
_CH = [(-6.6, 0.0), (-6.45, 0.16), (-6.25, 0.28), (-5.9, 0.24), (-5.4, 0.15),
       (-4.8, 0.06), (-4.3, 0.0)]
# cabina (lagrima): cota del techo y semiancho (fraccion de wmax)
# (720S: el habitaculo termina sobre el eje trasero, techo en arco corto)
_ZG = [(-7.9, 1.66), (-7.7, 1.72), (-7.3, 1.84), (-6.8, 2.00), (-6.2, 2.16),
       (-5.6, 2.29), (-5.1, 2.35), (-4.6, 2.36), (-4.0, 2.33), (-3.5, 2.24),
       (-3.1, 2.12), (-2.7, 1.98), (-2.2, 1.77), (-1.8, 1.54), (-1.5, 1.36),
       (-1.3, 1.24), (-1.15, 1.18)]
_WG = [(-7.9, 0.40), (-7.3, 0.47), (-6.6, 0.55), (-6.0, 0.60), (-5.0, 0.665),
       (-4.0, 0.71), (-3.0, 0.735), (-2.2, 0.745), (-1.5, 0.735), (-1.15, 0.70)]
_X_CAB0, _X_CAB1 = -1.15, -7.9
# macizo: perfil de la cresta (u = distancia enterrada desde el origen, unid.
# R -> fraccion de alto_montana) y semiancho de la meseta (fraccion de wmax).
# Zaga: lame el flanco desde u=4.4, cubre media rueda trasera (u=7.6:
# 0.33), llega a la cota del aleron en la cola (u=10.1: 0.76) y culmina
# en una cresta estrecha a u=11.5 (1.0 = alto_montana > techo); cae en
# ~50 grados hasta u=14.5. Morro: tapa el splitter desde u=2.0 y medio
# faro en u=2.1, cresta en u=2.8 (justo donde el capo entra en la roca),
# fin en u=4.8. `largo_macizo` reescala
# las u desde el arranque (_U0) hasta el final (_U1).
_ZM_ZAGA = [(3.9, -0.28), (4.4, -0.04), (5.0, 0.10), (5.8, 0.19), (6.6, 0.28),
            (7.4, 0.36), (8.2, 0.46), (9.0, 0.58), (9.7, 0.70), (10.3, 0.82),
            (10.9, 0.93), (11.5, 1.0), (12.1, 0.97), (12.7, 0.84), (13.3, 0.60),
            (13.9, 0.30), (14.3, 0.05), (14.5, -0.2)]
_WP_ZAGA = [(3.9, 0.96), (6.0, 0.98), (8.0, 1.02), (9.5, 1.0), (10.3, 0.82),
            (11.0, 0.60), (11.8, 0.46), (12.6, 0.40), (13.4, 0.32), (14.0, 0.22),
            (14.5, 0.06)]
_ZM_MORRO = [(1.2, -0.30), (1.5, -0.08), (1.8, 0.30), (2.1, 0.62), (2.4, 0.85),
             (2.8, 1.0), (3.2, 0.95), (3.6, 0.80), (4.0, 0.58), (4.4, 0.30),
             (4.7, 0.05), (4.8, -0.2)]
_WP_MORRO = [(1.2, 1.0), (1.8, 0.95), (2.4, 0.80), (2.8, 0.62), (3.2, 0.50),
             (3.6, 0.42), (4.0, 0.35), (4.4, 0.25), (4.8, 0.08)]
_U0 = {"zaga": 3.9, "morro": 1.2}      # arranque del macizo (unid. R)
_U1 = {"zaga": 14.5, "morro": 4.8}     # largo_macizo por defecto (unid. R)
_U_CRESTA = {"zaga": 11.5, "morro": 2.8}
_ALTO_DEF = {"zaga": 3.2, "morro": 2.5}  # alto_montana por defecto (unid. R)
# bloques caidos: (fraccion del largo del macizo desde _U0, y/R, radio/R)
_BLOQUES = [(0.13, 3.0, 0.09), (0.22, 3.5, 0.08), (0.33, 3.9, 0.11), (0.44, 4.4, 0.09),
            (0.57, 4.6, 0.12), (0.69, 3.7, 0.10), (0.78, 2.2, 0.11), (0.84, 0.8, 0.09),
            (0.27, 2.95, 0.06), (0.63, 3.3, 0.07), (0.38, 3.4, 0.07), (0.50, 3.8, 0.08)]


# ===================================================== perfiles / anillos ===
def _redondea(pts, rads, k=5):
    """Polilinea abierta -> esquinas redondeadas (Bezier cuadratica de k
    muestras por esquina, radio por punto acotado al 45 % del lado mas
    corto). Topologia FIJA: 2 + k*(n-2) puntos. Sin duplicados."""
    n = len(pts)
    lens = [max(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]), 1e-6)
            for i in range(n - 1)]
    out = [pts[0]]
    for i in range(1, n - 1):
        r = max(min(rads[i], 0.45 * lens[i - 1], 0.45 * lens[i]), 1e-4)
        p, pm, pp = pts[i], pts[i - 1], pts[i + 1]
        ui = ((p[0] - pm[0]) / lens[i - 1], (p[1] - pm[1]) / lens[i - 1])
        uo = ((pp[0] - p[0]) / lens[i], (pp[1] - p[1]) / lens[i])
        a = (p[0] - r * ui[0], p[1] - r * ui[1])
        c = (p[0] + r * uo[0], p[1] + r * uo[1])
        for j in range(k):
            t = j / (k - 1.0)
            s = 1.0 - t
            out.append((s * s * a[0] + 2 * s * t * p[0] + t * t * c[0],
                        s * s * a[1] + 2 * s * t * p[1] + t * t * c[1]))
    out.append(pts[-1])
    return out


def _anillo_simetrico(bm, x, medio):
    """Medio perfil (y>=0, de abajo-centro a arriba-centro) -> anillo
    cerrado de vertices en el plano x (sube por +Y, baja por -Y)."""
    ring = [bm.verts.new((x, y, z)) for y, z in medio]
    ring += [bm.verts.new((x, -y, z)) for y, z in medio[-2:0:-1]]
    return ring


# ============================================================ carroceria ====
def _lineas(R, wmax, xr):
    """Lineas de la carroceria baja en la estacion xr (m): semiancho w,
    suelo zf, cintura zb, hombro zd (dz relativos al buje, aun sin sumar
    zc), bombeo cr y canal lateral ch."""
    w = wmax * max(_spline(_WB, xr), 0.06)
    zf = R * _spline(_ZF, xr)
    zb = R * _spline(_ZB, xr)
    zd = R * _spline(_ZD, xr)
    zb = min(max(zb, zf + 0.30 * R), zd - 0.10 * R)
    cr = R * _spline(_CR, xr)
    ch = R * max(_spline(_CH, xr), 0.0)
    return w, zf, zb, zd, cr, ch


def _perfil_cuerpo(R, wmax, xr, zc, k=5):
    """Medio perfil (y, z) de la seccion YZ de la carroceria baja: vientre
    plano, umbral, canal lateral (recesado w-ch), cintura (lo mas ancho),
    HOMBRO vivo y capo/cubierta con bombeo (negativo = valle entre los picos
    de las aletas). Esquinas redondeadas con radio propio."""
    w, zf, zb, zd, cr, ch = _lineas(R, wmax, xr)
    h = zb - zf
    sh = _spline(_SH, xr)
    sr = R * _spline(_SR, xr)
    pts = [(0.0, zf), (0.88 * w, zf), (w, zf + 0.19 * h), (w - 0.02 * R, zf + 0.36 * h),
           (w - ch, zf + 0.45 * h), (w - ch, zf + 0.88 * h), (w, zb), (sh * w, zd),
           (0.50 * w, zd + cr), (0.0, zd + 1.1 * cr)]
    rads = [0.0, 0.12 * R, 0.06 * R, 0.05 * R, 0.07 * R, 0.07 * R, 0.09 * R, sr,
            0.22 * R, 0.0]
    return [(y, z + zc) for y, z in _redondea(pts, rads, k)]


def _estaciones(x0, x1, paso, fino=0.3):
    """Cotas x (unid. R) de x0 a x1 con paso `paso` y mas finas (paso/2) en
    los `fino` R extremos; sin dos a < 0.015."""
    xs = set()
    x = x0
    while x < x1:
        xs.add(round(x, 3))
        d = min(x - x0, x1 - x)
        x += paso * 0.5 if d < fino else paso
    xs.add(round(x1, 3))
    out = []
    for xr in sorted(xs):
        if not out or xr - out[-1] >= 0.015:
            out.append(xr)
    return out


def _desplaza_mc(R, p, n, so):
    """Grano fino de la piedra + juntas de puerta (surcos) en los flancos."""
    x = p.x / R
    d = 0.0
    if abs(n.y) > 0.5:
        for xk in _JUNTAS:
            d -= 0.030 * math.exp(-((x - xk) / 0.025) ** 2)
    d += (0.008 * _n3(p.x * 0.05 + so, p.y * 0.05, p.z * 0.05) +
          0.004 * _n3(p.x * 0.18, p.y * 0.18 + so, p.z * 0.18))
    return d * R


def _bandas_finas(bm, R, so):
    """Estratos FINOS de la caliza en la carroceria: lineas claras
    horizontales (band_h/2 = 0.065R de grosor, cada 4 band_h = 0.52R) a las
    MISMAS cotas que las bandas claras de indice 0 de la roca (la talla
    atraviesa los mismos estratos); bordes rectos por bisect."""
    band_h = _BAND_H * R
    zs = [v.co.z for v in bm.verts]
    z0, z1 = min(zs), max(zs)
    j = math.floor(z0 / (4.0 * band_h)) - 1
    while 4.0 * j * band_h - 0.25 * band_h < z1:
        for zk in (4.0 * j * band_h - 0.25 * band_h, 4.0 * j * band_h + 0.25 * band_h):
            if z0 + 0.05 < zk < z1 - 0.05:
                geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
                bmesh.ops.bisect_plane(bm, geom=geom, dist=0.02,
                                       plane_co=(0.0, 0.0, zk), plane_no=(0.0, 0.0, 1.0),
                                       use_snap_center=False, clear_outer=False,
                                       clear_inner=False)
        j += 1
    for fce in bm.faces:
        k = math.floor(2.0 * fce.calc_center_median().z / band_h + 0.5)
        fce.material_index = _M_CLARA if k % 8 == 0 else _M_CAL
        fce.smooth = True


def _loft(bm, rings, mi, smooth, tapas):
    """Caras entre anillos consecutivos + tapas: ('domo', v_a, v_b) = polos
    ya creados (la lista rings incluye los anillos del domo) o ('fan', ) =
    abanicos planos a un centroide en cada extremo."""
    n = len(rings[0])
    if tapas[0] == "fan":
        for ring, sign in ((rings[0], -1.0), (rings[-1], 1.0)):
            c = sum((v.co for v in ring), Vector()) / n
            vc = bm.verts.new(c)
            for k in range(n):
                k2 = (k + 1) % n
                if sign < 0:
                    _add_face(bm, (vc, ring[k2], ring[k]), mi, smooth)
                else:
                    _add_face(bm, (vc, ring[k], ring[k2]), mi, smooth)
    else:
        va, vb = tapas[1], tapas[2]
        for k in range(n):
            k2 = (k + 1) % n
            _add_face(bm, (va, rings[0][k2], rings[0][k]), mi, smooth)
            _add_face(bm, (vb, rings[-1][k], rings[-1][k2]), mi, smooth)
    for ra, rb in zip(rings, rings[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            _add_face(bm, (ra[k], ra[k2], rb[k2], rb[k]), mi, smooth)


def _carroceria(R, W, AB, so):
    """Loft cerrado de la carroceria baja (estaciones cada 0.08R, anillos de
    82 vertices) con domos en morro y zaga, desplazado por la normal (grano
    + juntas). bmesh, un material (caliza)."""
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    bm = bmesh.new()
    rings = [_anillo_simetrico(bm, xr * R, _perfil_cuerpo(R, wmax, xr, zc))
             for xr in _estaciones(_X_TAIL, _X_NOSE, 0.08)]
    cola, v_tail = _domo(bm, rings[0], _X_TAIL * R, 0.09 * R, -1.0)
    morro, v_nose = _domo(bm, rings[-1], _X_NOSE * R, 0.14 * R, 1.0)
    rings = cola[::-1] + rings + morro
    _loft(bm, rings, _M_CAL, True, ("domo", v_tail, v_nose))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    desp = {v: v.normal * _desplaza_mc(R, v.co, v.normal, so) for v in bm.verts}
    for v, dv in desp.items():
        v.co += dv
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _bandas_finas(bm, R, so)
    return bm


def _cabina_lineas(R, wmax, xr):
    """(wg, zgb, zt): semiancho, base (oculta dentro del cuerpo) y techo de
    la cabina en xr (z sin sumar zc)."""
    wg = wmax * max(_spline(_WG, xr), 0.05)
    _w, _zf, _zb, zd, cr, _ch = _lineas(R, wmax, xr)
    zgb = zd + min(cr, 0.0) - 0.30 * R
    zt = max(R * _spline(_ZG, xr), zgb + 0.05 * R)
    return wg, zgb, zt


def _perfil_cabina(R, wmax, xr, zc, k=5):
    """Medio perfil de la cabina: base plana (dentro del cuerpo), zocalo
    vertical del cristal, tumblehome, borde del techo redondeado."""
    wg, zgb, zt = _cabina_lineas(R, wmax, xr)
    h = zt - zgb
    pts = [(0.0, zgb), (wg, zgb), (wg, zgb + 0.30 * h), (0.84 * wg, zgb + 0.72 * h),
           (0.50 * wg, zt), (0.0, zt)]
    rads = [0.0, 0.03 * R, 0.06 * R, 0.16 * R, 0.30 * R, 0.0]
    return [(y, z + zc) for y, z in _redondea(pts, rads, k)]


def _cabina(R, W, AB, so):
    """Loft cerrado de la cabina en lagrima (parabrisas tumbado, techo,
    luneta); su base queda dentro de la carroceria (se UNE). bmesh."""
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    bm = bmesh.new()
    rings = [_anillo_simetrico(bm, xr * R, _perfil_cabina(R, wmax, xr, zc))
             for xr in _estaciones(_X_CAB1, _X_CAB0, 0.08, 0.2)]
    _loft(bm, rings, _M_CAL, True, ("fan",))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    desp = {v: v.normal * (0.006 * R * _n3(v.co.x * 0.05 + so, v.co.y * 0.05,
                                            v.co.z * 0.05))
            for v in bm.verts}
    for v, dv in desp.items():
        v.co += dv
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _bandas_finas(bm, R, so)
    return bm


def _pasa_ruedas(R, W, AB, hubs, n=64):
    """Cilindros cerrados a lo largo de Y que se RESTAN (radio _WELL_R):
    desde |y| = W/2 - _WELL_D R hasta W/2 + fuera[i] (la rueda enterrada en
    el macizo corta poco hacia fuera: la roca lame el neumatico)."""
    zc = R - AB
    rw = _WELL_R * R
    bm = bmesh.new()
    for xh, fuera in hubs:
        for side in (1.0, -1.0):
            y0 = side * (0.5 * W - _WELL_D * R)
            y1 = side * (0.5 * W + fuera)
            ra = [bm.verts.new((xh + rw * math.cos(2 * math.pi * k / n), y0,
                                zc + rw * math.sin(2 * math.pi * k / n))) for k in range(n)]
            rb = [bm.verts.new((xh + rw * math.cos(2 * math.pi * k / n), y1,
                                zc + rw * math.sin(2 * math.pi * k / n))) for k in range(n)]
            _add_face(bm, ra, _M_OSC, False)
            _add_face(bm, rb[::-1], _M_OSC, False)
            for k in range(n):
                k2 = (k + 1) % n
                _add_face(bm, (ra[k], ra[k2], rb[k2], rb[k]), _M_OSC, False)
    return bm


# ================================================================== roca ====
def _hash_k(k, so):
    """Hash determinista en [0, 1) por indice de banda."""
    v = math.sin(k * 12.9898 + so * 7.1 + 78.233) * 43758.5453
    return v - math.floor(v)


def _celda_suave(x, y, z, so, cw, ch, junta=_JUNTA_CELDA):
    """Bloques de fractura como _celda (mismas celdas cw x cw x ch, mismas
    juntas onduladas y el MISMO valor por bloque) pero con las juntas
    SUAVIZADAS: meseta en el centro de cada bloque y transicion smoothstep
    a la celda vecina en +-junta (fraccion de celda) alrededor de la junta.
    Ronda 15 v2 (B2-06/B2-10): el salto constante por bloque, muestreado en
    el loft cada 0.1R, salia como escalones de pixel; asi se leen cornisas
    y resaltes. Devuelve [-1, 1]."""
    jx = 0.22 * cw * _n3(y * 0.05 + so, z * 0.05, 1.7)
    jy = 0.22 * cw * _n3(x * 0.05, z * 0.05 + so, 6.1)
    jz = 0.18 * ch * _n3(x * 0.04 + so, y * 0.04, 9.3)

    def eje(c, w):
        u = c / w - 0.5               # centros de bloque en los enteros
        i0 = math.floor(u)
        return i0, _sstep((u - i0 - 0.5 + junta) / (2.0 * junta))

    ix, tx = eje(x + jx, cw)
    iy, ty = eje(y + jy, cw)
    iz, tz = eje(z + jz, ch)
    k_so = 7 * int(so)
    v = 0.0
    for dx, wx in ((0, 1.0 - tx), (1, tx)):
        if wx <= 0.0:
            continue
        for dy, wy in ((0, 1.0 - ty), (1, ty)):
            if wy <= 0.0:
                continue
            for dz, wz in ((0, 1.0 - tz), (1, tz)):
                if wz <= 0.0:
                    continue
                v += wx * wy * wz * (2.0 * _hash01(ix + dx + k_so, iy + dy + 3, iz + dz) - 1.0)
    return v


def _dist_coche(c, R, wmax):
    """Distancia en planta (m) de un punto a la huella de la carroceria
    (x en [_X_TAIL, _X_NOSE] R, |y| <= wmax)."""
    dx = max(_X_TAIL * R - c.x, 0.0, c.x - _X_NOSE * R)
    dy = max(abs(c.y) - wmax, 0.0)
    return math.hypot(dx, dy)


def _mat_estrato_mc(z, band_h, so):
    """Estratos de la roca con MENOS contraste que el patron compartido de
    la v2 (que daba 'tarta a rayas'): banda clara solo cada 4 band_h (la
    misma cota que las lineas claras de la carroceria), lineas oscuras solo
    en medias bandas entrantes (k impar) y de forma irregular (hash, ~45 %
    de ellas); el resto, caliza base."""
    k = int(math.floor(2.0 * z / band_h + 0.5))
    if k % 8 == 0:
        return _M_CLARA
    if k % 2 == 1 and _hash_k(k, so) < 0.45:
        return _M_OSC
    return _M_CAL


def _perfil_macizo(ent, largo):
    """(zm, wp, u_cresta): perfiles del macizo `ent` ('zaga' | 'morro')
    reescalados en u desde _U0[ent] hasta `largo` (unid. R; None =
    _U1[ent]). (None, None, u0) si el largo no deja macizo (<= _U0 + 0.4)."""
    zm0, wp0 = (_ZM_ZAGA, _WP_ZAGA) if ent == "zaga" else (_ZM_MORRO, _WP_MORRO)
    u0, u1 = _U0[ent], _U1[ent]
    if largo is None:
        largo = u1
    if largo <= u0 + 0.4:
        return None, None, u0
    f = (largo - u0) / (u1 - u0)
    zm = [(u0 + (u - u0) * f, v) for u, v in zm0]
    wp = [(u0 + (u - u0) * f, v) for u, v in wp0]
    return zm, wp, u0 + (_U_CRESTA[ent] - u0) * f


def _por_lado(v, lado):
    """Valor para 'zaga' | 'morro' de un escalar o de un par (zaga, morro)."""
    if isinstance(v, (tuple, list)):
        return v[0 if lado == "zaga" else 1]
    return v


def _macizos(ent, largo, alto, R):
    """Lista de macizos [(sgn, zm_pts, wp_pts, alto_m, u_cresta)] para
    enterrado = 'zaga' | 'morro' | 'ambos'. `largo` (unid. R) y `alto`
    (m; None = _ALTO_DEF[lado]*R) admiten un par (zaga, morro)."""
    lados = ("zaga", "morro") if ent == "ambos" else (ent,)
    out = []
    for lado in lados:
        lg = _por_lado(largo, lado)
        lg = None if lg is None else max(float(lg), 0.0)
        al = _por_lado(alto, lado)
        al = _ALTO_DEF[lado] * R if al is None else float(al)
        zm, wp, uc = _perfil_macizo(lado, lg)
        if zm is not None:
            out.append((-1.0 if lado == "zaga" else 1.0, zm, wp, al, uc))
    return out


def _par(v, nombre):
    """float o par (lado -Y, lado +Y) -> (a, b) de floats."""
    if isinstance(v, (tuple, list)):
        if len(v) != 2:
            raise ValueError("montana_mclaren: %s debe ser un numero o un par" % nombre)
        return float(v[0]), float(v[1])
    return float(v), float(v)


def _roca(R, W, AB, z_fondo, so, talud, macs, ancho_mac, z_agua=None, n_ring=84):
    """Loft cerrado (secciones YZ a lo largo de X) de PEDESTAL + MACIZO(S):
    pedestal bajo el coche (|y| = flanco - 0.05R, pie en talud, oculto
    dentro de la carroceria por encima del umbral; seccion en domo como la
    v2) y macizo(s) `macs` (_macizos) que lamen el flanco a la cota z_m(x)
    (perfil _ZM_*, cresta = alto) con seccion de MESETA plana (q=6) y
    laderas en talud `talud` = (grados lado -Y, lado +Y) hasta el suelo,
    falda a 60 grados bajo el; meseta de semiancho wp * ancho_mac[lado].
    Relieve ridged + bloques (_celda_suave) + crestas secundarias (manso
    junto al coche y a las ruedas), estratos con escalon suave, clamp de la
    zona prohibida, cortes de estrato hasta la linea de agua `z_agua`
    (cota local del mar; None = z_fondo + 9.4), roca mojada (caliza oscura)
    solo hasta z_agua + 1, hierba y caliza meteorizada lejos del coche
    (_hierba_y_monte) y base plana en z_fondo. Sombreado suave (las
    aristas vivas las marca _pulir). Sin macizos solo queda el pedestal."""
    if z_agua is None:
        z_agua = z_fondo + _Z_AGUA_SOBRE_FONDO
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    y_lim = 0.5 * W + 2.3
    tan_t = tuple(math.tan(math.radians(t)) for t in talud)
    tan_f = math.tan(math.radians(60.0))
    band_h = _BAND_H * R
    cw, chh = 0.30 * R, 0.45 * R
    hubs = ((0.0, zc), (_X_REAR * R, zc))
    x_ini, x_fin = _X_TAIL + 0.3, 2.70
    con_morro = False
    for sgn, zm_pts, _wp, _al, _uc in macs:
        if sgn < 0:
            x_ini = min(x_ini, -zm_pts[-1][0] - 0.05)
        else:
            x_fin = max(x_fin, zm_pts[-1][0] + 0.05)
            con_morro = True
    xs = _estaciones(x_ini, x_fin, 0.10, 0.3)

    bm = bmesh.new()
    tapa = bm.verts.layers.float.new("mc_tapa")    # posicion en la seccion (bisect la interpola)
    rings, desp = [], {}
    for xr in xs:
        xm = xr * R
        con_coche = _X_TAIL <= xr <= _X_NOSE
        z_pt = z_meet = zf_abs = w_ped = w_b = -1e9
        if con_coche:
            w_b, zf, _zb, _zd, _cr, _chn = _lineas(R, wmax, xr)
            zf_abs = zc + zf
            w_ped = max(w_b - 0.05 * R, 0.3 * R)
            z_pt = zf_abs + 0.35 * R
            z_meet = zf_abs + 0.12 * R
        zm, w_pl, al_here = None, 0.0, 1.0
        for sgn, zm_pts, wp_pts, al, _uc in macs:
            u = sgn * xr
            if zm_pts[0][0] <= u <= zm_pts[-1][0]:
                zm = al * _lin(zm_pts, u)
                w_pl = wmax * _lin(wp_pts, u)
                al_here = al
                break
        if zm is not None and zm > 0.0:
            zm *= 1.0 + 0.14 * _n3(xm * 0.012 + so, 1.3, 2.2) * _sstep(zm / (0.3 * al_here))
        z_top = max(z_pt if con_coche else -1e9, zm if zm is not None else -1e9)
        z_top = max(z_top, z_fondo + 1.5)
        z_low = min(z_fondo - 0.30 * (z_top - z_fondo), z_top - 0.25 * R)
        zmid, H = 0.5 * (z_top + z_low), 0.5 * (z_top - z_low)
        flare = _sstep((-1.30 * R - xm) / (0.35 * R))
        if con_morro:
            flare = max(flare, _sstep((xm - 1.6 * R) / (0.3 * R)))
        q, q_m = 2.6, 6.0      # pedestal: domo (v2); macizo: meseta de techo plano
        ring = []
        for k in range(n_ring):
            th = 2.0 * math.pi * (k + 0.5) / n_ring
            cy, sz = _sq(math.cos(th), q), _sq(math.sin(th), q)
            cy_m = _sq(math.cos(th), q_m)
            lado = 0 if cy < 0.0 else 1
            z0 = zmid + H * sz
            zq = max(z0, z_fondo)
            w1 = w2 = 0.0
            if con_coche and z0 <= z_pt + 0.01:
                w1 = w_ped * (1.0 + 0.03 * _n3(xm * 0.02 + so, zq * 0.02, 8.1))
                w1 += 0.05 * R * _sstep((0.30 * R - zq) / (0.30 * R))
                w1 *= 1.0 - 0.55 * _sstep((zq - z_meet) / (0.2 * R))
                # v2 (B2-06 c): falda en talud (~70 grados) bajo la linea de la carroceria
                # entre las ruedas (fuera de la zona del tunel: flare = 0 alli)
                w1 += flare * _K_FALDA * max(0.0, z_meet - 0.3 * R - zq)
            if zm is not None and z0 <= zm + 0.01:
                tt = tan_t[lado] * (1.0 + 0.30 * _n3(xm * 0.016, zq * 0.03 + so, 7.7))
                # crestas secundarias: la ladera (no la meseta) varia +-24 %
                mod = 1.0 + 0.24 * _n3(xm * 0.009 + so, zq * 0.012, 4.4 + 2.0 * lado)
                w2 = w_pl * ancho_mac[lado] + mod * max(0.0, zm - max(zq, 0.0)) / tt
            if zq < 0.0:
                w_fal = (-zq) * flare / tan_f
                w1 += w_fal if w1 > 0.0 else 0.0
                w2 += w_fal if w2 > 0.0 else 0.0
            w_here = max(w1, w2, 0.2 * R)
            y_p = cy * max(w1, 0.2 * R)
            y_m = cy_m * w2 if zm is not None else 0.0
            dom_m = zm is not None and abs(y_m) >= abs(y_p)
            y0 = y_m if dom_m else y_p
            amp = _sstep((w_here - 4.0) / 8.0)
            if con_coche and not dom_m:
                # v2 (B2-06 c): el pedestal pasa de 0.6 junto a la carroceria a 1.8 en la
                # falda (antes 0.6 hasta el agua: pared lisa)
                a_ped = 0.6 + 1.2 * flare * _sstep((z_meet - 0.3 * R - zq) / (0.5 * R))
                amp *= a_ped * (1.0 - _sstep((zq - z_meet + 0.1 * R) / (0.15 * R)))
            if con_coche and dom_m and abs(y0) < w_b + 0.15 * R and zq > zf_abs - 0.1 * R:
                amp *= 0.25
            if abs(y0) > 0.5 * W - 0.30 * R:
                for xh, zh in hubs:
                    amp = min(amp, 0.25 + 0.75 * _sstep(
                        (math.hypot(xm - xh, zq - zh) - 1.30 * R) / (0.25 * R)))
            amp *= 1.0 + 0.5 * _sstep((-2.0 - zq) / 8.0)
            libre = dom_m and (not con_coche or abs(y0) > w_b + 0.3 * R)
            if libre:
                amp *= 2.4                       # laderas del cerro: relieve franco
            if dom_m:
                cel = _K_CEL_MACIZO * _celda_suave(xm, y0, zq, so, cw, chh)
            else:
                # junto al tunel (flare = 0) el pedestal conserva los bloques de la v1: los
                # Boolean del tunel (EXACT del test, EXACT/MANIFOLD del integrador) estaban
                # probados con esa geometria (con la suave el EXACT del test dejaba 33 aristas)
                cel = (1.0 - flare) * 1.2 * _celda(xm, y0, zq, so, cw, chh)
                if flare > 0.0:
                    cel += flare * _K_CEL_PEDESTAL * _celda_suave(xm, y0, zq, so, cw, chh)
            D = amp * (_ridged(xm, y0, zq, so) + cel)
            D += amp * (0.9 if libre else 1.1) * math.tanh(2.5 * _onda_estrato(zq, band_h, 0.0))
            lim = 9.0 if libre else 6.5
            D = lim * math.tanh(D / lim)
            dv = Vector((0.0, cy, sz * _sstep((z0 - z_fondo - 2.0) / 6.0)))
            if dv.length < 1e-6:
                dv = Vector((0.0, 0.0, 1.0))
            dv.normalize()
            v = bm.verts.new((xm, y0, z0))
            v[tapa] = sz if dom_m else -1.0      # techo de la meseta del macizo ~ 1
            desp[v] = (D, dv)
            ring.append(v)
        rings.append(ring)
    p0 = bm.verts.new((xs[0] * R - 0.05 * R, 0.0, z_fondo - 0.3 * R))
    p1 = bm.verts.new((xs[-1] * R + 0.05 * R, 0.0, z_fondo - 0.3 * R))
    for k in range(n_ring):
        k2 = (k + 1) % n_ring
        _add_face(bm, (p0, rings[0][k2], rings[0][k]), _M_OSC, False)
        _add_face(bm, (p1, rings[-1][k], rings[-1][k2]), _M_OSC, False)
    for ra, rb in zip(rings, rings[1:]):
        for k in range(n_ring):
            k2 = (k + 1) % n_ring
            _add_face(bm, (ra[k], ra[k2], rb[k2], rb[k]), _M_CAL, False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for v, (D, dv) in desp.items():
        if D != 0.0:
            v.co += dv * D
        if -1.3 * R <= v.co.x <= 1.5 * R and abs(v.co.y) > y_lim:
            v.co.y = math.copysign(y_lim, v.co.y)
    # cortes de estrato (bordes de material horizontales) desde la linea de agua; v2
    # (B2-06 a): antes solo sobre z = -2 y TODO lo de debajo era caliza oscura (una
    # franja uniforme de ~18 m sobre el mar en el sitio del integrador)
    z_moja = max(z_agua + _FRANJA_AGUA, z_fondo + 0.5)
    z_max = max(v.co.z for v in bm.verts)
    planos = [z_moja]
    k = int(math.floor((z_moja / band_h + 0.25) * 2.0)) + 1
    while band_h * (0.5 * k - 0.25) < z_max:
        zk = band_h * (0.5 * k - 0.25)
        if zk > z_moja + 0.3:
            planos.append(zk)
        k += 1
    for zk in planos:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, dist=0.12,
                               plane_co=(0.0, 0.0, zk), plane_no=(0.0, 0.0, 1.0),
                               use_snap_center=False, clear_outer=False,
                               clear_inner=False)
    for fce in bm.faces:
        c = fce.calc_center_median()
        fce.smooth = True
        fce.material_index = _M_OSC if c.z < z_moja else _mat_estrato_mc(c.z, band_h, so)
    _hierba_y_monte(bm, R, wmax, so, z_agua, band_h, tapa)
    bm.verts.layers.float.remove(tapa)
    _cerrar_en(bm, z_fondo)
    return bm


def _hierba_y_monte(bm, R, wmax, so, z_agua, band_h, tapa):
    """Ronda 15 v2 (N1/E2-12): el macizo LEJOS del coche (> _HIERBA_D R de
    la huella de la carroceria) pasa de roca a monte. (a) HIERBA en el
    techo de la meseta (capa `tapa` >= _TAPA_MIN +-0.025 de ruido: borde
    continuo a lo largo del macizo, no damero) salvo donde asoma roca
    (normal suavizada con dos pasadas de media con los vecinos: nz < 0.6) y
    por encima de z_agua + 3. (b) Caliza METEORIZADA (_M_MONTE) en las
    bandas de caliza base del macizo mas alla de una distancia al coche
    propia de cada banda (0.6-2.8R mas): los limites siguen los estratos
    (bancos que se adelgazan), las lineas clara/oscura siguen. La carroceria
    y su pedestal conservan la caliza del coche."""
    bm.normal_update()
    nz = {v: v.normal.z for v in bm.verts}
    for _pasada in range(2):
        nz = {v: 0.5 * g + 0.5 * (sum(nz[e.other_vert(v)] for e in v.link_edges) /
                                  max(1, len(v.link_edges)))
              for v, g in nz.items()}
    d_min = _HIERBA_D * R
    for fce in bm.faces:
        if fce.material_index == _M_OSC:
            continue
        c = fce.calc_center_median()
        d = _dist_coche(c, R, wmax)
        if d < d_min:
            continue
        t = sum(v[tapa] for v in fce.verts) / len(fce.verts)
        g = sum(nz[v] for v in fce.verts) / len(fce.verts)
        t_min = _TAPA_MIN + 0.025 * _n3(c.x * 0.02 + so, c.y * 0.02, 2.7)
        if c.z > z_agua + 3.0 and t >= t_min and g >= 0.6 and fce.normal.z >= 0.45:
            fce.material_index = _M_HIERBA
            continue
        if fce.material_index == _M_CAL:
            k = int(math.floor(2.0 * c.z / band_h + 0.5))
            if d > d_min + (0.6 + 2.2 * _hash_k(k, so + 3.3)) * R:
                fce.material_index = _M_MONTE


# ===================================================== contacto (v3, J10) ===
_FALDA_H = (3.0, 7.0)       # m sobre el terreno: MAT_terreno (hierba en lo tendido / roca del monte)
_MONTE_H = (16.0, 34.0)     # m sobre el terreno: la caliza base pasa a caliza meteorizada
_TERRENO_D = (1.6, 2.4)     # unid. R de la huella del coche: mas alla el macizo es roca del monte
_HUECO_H = 4.0              # m: cuenca oscura con algun trozo a menos de esto del suelo -> caliza
_PED_MONTE = 0.25           # unid. R bajo el umbral: falda del pedestal en caliza meteorizada


def _terreno_sitio(param, R, W, zf, lv, caja):
    """Cota del terreno en el marco local para build(terreno=...): un
    callable f(lx, ly) -> (z_local, es_mar) se usa tal cual; 'auto' = la
    malla TERRENO de la escena en el sitio del integrador
    (encaje_mclaren.sitio_de_build: solo si z_fondo/lado_visible son los de
    integrar_escena.zona_tunel) o None (test, otra escena); None/False ->
    None. Nunca lanza: si algo falla, None (el coche sale como en la v2)."""
    if param is None or param is False:
        return None
    if callable(param):
        return param
    if str(param).lower() != "auto":
        return None
    ter = bpy.data.objects.get("TERRENO")
    if ter is None or ter.type != "MESH" or not len(ter.data.polygons):
        return None
    try:
        aqui = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location("encaje_mclaren_para_build",
                                                      os.path.join(aqui, "encaje_mclaren.py"))
        en = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(en)
        sit = en.sitio_de_build(R, W, zf, lv)
        if sit is None:
            return None
        ft = en.TerrenoMalla(sit, ter, caja)
        return ft if ft.tree is not None else None
    except Exception as e:                  # sin geometria, sin numpy...: como antes
        print("montana_mclaren: sin terreno del sitio (%s)" % e)
        return None


def _en_rueda(c, R, W, AB, r_rel=1.35):
    """Punto local dentro de la zona de una rueda (pasa-ruedas, neumatico,
    llanta): |y| > W/2 - 0.6R y a menos de r_rel R del buje en XZ."""
    if abs(c.y) <= 0.5 * W - 0.6 * R:
        return False
    zc = R - AB
    return any(math.hypot(c.x - xh, c.z - zc) < r_rel * R for xh in (0.0, _X_REAR * R))


def _zona_coche(c, R, W, AB):
    """'coche' (carroceria por encima del umbral -0.1R, o rueda), 'pedestal'
    (dentro de la huella, por debajo) o 'roca' (fuera de la huella)."""
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    xr = c.x / R
    if abs(c.y) > 0.5 * W - 0.45 * R:
        for xh in (0.0, _X_REAR * R):
            if math.hypot(c.x - xh, c.z - zc) < 1.20 * R:
                return "coche"
    if not (_X_TAIL <= xr <= _X_NOSE) or abs(c.y) > wmax + 0.05 * R:
        return "roca"
    z_umb = zc + _lin(_ZF, xr) * R
    return "coche" if c.z >= z_umb - 0.10 * R else "pedestal"


def _contacto_terreno(me, R, W, AB, ft, z_agua, so):
    """Ronda 15 v3 (J10 c, B11): materiales del CONTACTO con el monte sobre
    la malla final (despues de la cadena Boolean; no toca vertices). Nunca
    la carroceria ni las ruedas (_zona_coche), ni la roca mojada y su
    franja (por debajo de z_agua + 1.5), ni la zona del tunel (x en
    [-1.3R, 1.5R]). (1) Caliza base y clara del macizo a mas de _TERRENO_D
    R de la huella del coche (limite por estrato) -> caliza meteorizada, en
    el tono de la roca del TERRENO (el cerro deja de ser una escultura
    blanca suelta; MAT_terreno en todo el macizo daba un damero verde en
    las repisas de los estratos). (2) Falda del pedestal
    por debajo de umbral - _PED_MONTE R: caliza base -> caliza meteorizada.
    Con `ft` (cota del terreno en el marco local) y SOLO en tierra (terreno
    sobre z_agua + 0.5, no mar): (3) roca no-coche a menos de _FALDA_H m
    sobre el terreno (o por debajo) -> MAT_terreno; (4) caliza base hasta
    _MONTE_H m -> caliza meteorizada; (5) cada cuenca oscura (_M_HUECO,
    conexa, salvo los pasa-ruedas) con alguna cara a < _HUECO_H m del
    terreno pasa entera a caliza: medio enterrada se leia como la boca de
    una cueva. Devuelve dict con los recuentos."""
    band_h = _BAND_H * R
    zc = R - AB
    wmax = 0.5 * W - _Y_BODY * R
    z_seco = z_agua + _FRANJA_AGUA + 0.5
    bm = bmesh.new()                 # solo lectura (centros y vecindad): la malla no se reescribe
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    nuevo = [f.material_index for f in bm.faces]
    roca_mi = (_M_CAL, _M_CLARA, _M_OSC, _M_MONTE)
    cuenta = dict(monte_lejos=0, pedestal_monte=0, falda=0, monte=0, cuencas=0, cuencas_caras=0)
    h_cara = {}
    for f in bm.faces:
        mi = f.material_index
        if mi not in roca_mi and mi != _M_HUECO:
            continue
        c = f.calc_center_median()
        zona = _zona_coche(c, R, W, AB)
        if ft is not None:
            zt, mar = ft(c.x, c.y)
            tierra = (not mar) and zt > z_agua + 0.5
            h = c.z - zt if tierra else None
        else:
            h = None
        if mi == _M_HUECO:
            # los pasa-ruedas oscuros llegan siempre al suelo y hacen leer la rueda: no se tocan
            if h is not None and not _en_rueda(c, R, W, AB):
                h_cara[f.index] = h
            continue
        if zona == "coche" or c.z < z_seco or -1.3 * R <= c.x <= 1.5 * R:
            continue
        k = int(math.floor(2.0 * c.z / band_h + 0.5))
        if zona == "roca" and mi in (_M_CAL, _M_CLARA):
            d = _dist_coche(c, R, wmax)
            if d > (_TERRENO_D[0] + (_TERRENO_D[1] - _TERRENO_D[0]) * _hash_k(k, so + 5.1)) * R:
                nuevo[f.index] = _M_MONTE
                cuenta["monte_lejos"] += 1
                continue
        if h is not None:
            h1 = _FALDA_H[0] + (_FALDA_H[1] - _FALDA_H[0]) * (0.5 + 0.5 * _n3(c.x * 0.05 + so, c.y * 0.05, 5.3))
            if h < h1:
                nuevo[f.index] = _M_HIERBA
                cuenta["falda"] += 1
                continue
            if mi == _M_CAL and h < _MONTE_H[0] + (_MONTE_H[1] - _MONTE_H[0]) * _hash_k(k, so + 7.9):
                nuevo[f.index] = _M_MONTE
                cuenta["monte"] += 1
                continue
        if zona == "pedestal" and mi == _M_CAL:
            z_umb = zc + _lin(_ZF, c.x / R) * R
            if c.z < z_umb - _PED_MONTE * R * (1.0 + 0.4 * _n3(c.x * 0.03 + so, c.y * 0.03, 6.1)):
                nuevo[f.index] = _M_MONTE
                cuenta["pedestal_monte"] += 1
    if h_cara:
        visto = set()
        for i0 in h_cara:
            if i0 in visto:
                continue
            pila, region = [bm.faces[i0]], []
            visto.add(i0)
            while pila:
                f = pila.pop()
                region.append(f)
                for e in f.edges:
                    for g in e.link_faces:
                        if (g.index not in visto and g.material_index == _M_HUECO
                                and not _en_rueda(g.calc_center_median(), R, W, AB)):
                            visto.add(g.index)
                            pila.append(g)
            if min(h_cara.get(f.index, 1e9) for f in region) < _HUECO_H:
                for f in region:
                    nuevo[f.index] = _M_CAL
                cuenta["cuencas"] += 1
                cuenta["cuencas_caras"] += len(region)
    bm.free()
    me.polygons.foreach_set("material_index", nuevo)
    me.update()
    return cuenta


# ============================================================== cristales ===
def _loop_poly(pts, rcs, paso):
    """Poligono 2D (vertices (a, b) en orden) -> contorno cerrado muestreado
    cada ~paso con esquinas redondeadas (Bezier cuadratica, radio rcs[i]
    acotado al 45 por ciento de los lados). Sin puntos duplicados."""
    n = len(pts)
    out = []

    def rad(i):
        p, pm, pp = pts[i], pts[i - 1], pts[(i + 1) % n]
        li = max(math.hypot(p[0] - pm[0], p[1] - pm[1]), 1e-6)
        lo = max(math.hypot(pp[0] - p[0], pp[1] - p[1]), 1e-6)
        return max(min(rcs[i], 0.45 * li, 0.45 * lo), 1e-4), li, lo

    for i in range(n):
        p, pm, pp = pts[i], pts[i - 1], pts[(i + 1) % n]
        r, li, lo = rad(i)
        ui = ((p[0] - pm[0]) / li, (p[1] - pm[1]) / li)
        uo = ((pp[0] - p[0]) / lo, (pp[1] - p[1]) / lo)
        a = (p[0] - r * ui[0], p[1] - r * ui[1])
        c = (p[0] + r * uo[0], p[1] + r * uo[1])
        kc = max(3, int(round(0.5 * math.pi * r / paso)) + 1)
        for j in range(kc):
            t = j / float(kc)
            s = 1.0 - t
            out.append((s * s * a[0] + 2 * s * t * p[0] + t * t * c[0],
                        s * s * a[1] + 2 * s * t * p[1] + t * t * c[1]))
        rn, _li2, _lo2 = rad((i + 1) % n)
        a_next = (pp[0] - rn * uo[0], pp[1] - rn * uo[1])
        seg = math.hypot(a_next[0] - c[0], a_next[1] - c[1])
        ns = max(1, int(round(seg / paso)))
        for j in range(ns):
            t = j / float(ns)
            out.append((c[0] + (a_next[0] - c[0]) * t, c[1] + (a_next[1] - c[1]) * t))
    return out


def _espina(pts, m, paso):
    """m puntos (a, b) a lo largo del eje a del contorno, b = centro entre el
    borde inferior y el superior en esa a."""
    a_min = min(p[0] for p in pts)
    a_max = max(p[0] for p in pts)
    da = a_max - a_min
    out = []
    for j in range(m):
        a = a_min + da * (0.07 + 0.86 * j / (m - 1.0))
        bs = [p[1] for p in pts if abs(p[0] - a) < 1.5 * paso]
        if len(bs) < 2:
            bs = [p[1] for p in pts if abs(p[0] - a) < 4.0 * paso]
        out.append((a, 0.5 * (min(bs) + max(bs))))
    return out


def _muestreo_mc(tree, R, pts, modo, s=1.0):
    """Puntos 3D (ray-cast sobre carroceria+cabina) y normales del impacto
    para un contorno 2D en metros: modo 'techo' (a=x, b=y, rayo desde
    arriba) o 'flanco' (a=x, b=z, rayo desde el lado s)."""
    out = []
    for a, b in pts:
        if modo == "flanco":
            o, d = Vector((a, s * 4.0 * R, b)), Vector((0.0, -s, 0.0))
        else:
            o, d = Vector((a, b, 6.0 * R)), Vector((0.0, 0.0, -1.0))
        loc, nrm, _i, _d = tree.ray_cast(o, d, 12.0 * R)
        if loc is None:
            raise RuntimeError("montana_mclaren: cristal fuera de la carroceria en "
                               "(%.1f, %.1f) modo %s" % (a, b, modo))
        out.append((loc.copy(), nrm.copy()))
    return out


def _suaviza_normales(ms, cerrado, peso_media=0.6, radio=2):
    """Normales suavizadas (media de +-radio vecinos) mezcladas con la
    normal media del conjunto: paredes del prisma sin torsion."""
    n = len(ms)
    nm = sum((nn for _p, nn in ms), Vector()).normalized()
    out = []
    for i in range(n):
        acc = Vector()
        for j in range(-radio, radio + 1):
            idx = (i + j) % n if cerrado else max(0, min(n - 1, i + j))
            acc += ms[idx][1]
        acc.normalize()
        out.append((ms[i][0], (peso_media * nm + (1.0 - peso_media) * acc).normalized()))
    return out


def _asigna_espina(pts, m):
    """Indice de punto de espina (0..m-1 a lo largo del eje a) para cada
    punto del contorno, MONOTONO: no decreciente del minimo de a al maximo
    y no creciente de vuelta (cada arista de la espina queda cubierta
    exactamente por dos triangulos)."""
    n = len(pts)
    a0 = min(p[0] for p in pts)
    a1 = max(p[0] for p in pts)
    j = [max(0, min(m - 1, int(round((p[0] - a0) / max(a1 - a0, 1e-6) * (m - 1)))))
         for p in pts]
    k0 = min(range(n), key=lambda i: pts[i][0])
    k1 = max(range(n), key=lambda i: pts[i][0])
    j[k0], j[k1] = 0, m - 1
    i = k0
    while i != k1:
        i2 = (i + 1) % n
        if i2 != k1:
            j[i2] = max(j[i2], j[i])
        i = i2
    i = k1
    while i != k0:
        i2 = (i + 1) % n
        if i2 != k0:
            j[i2] = min(j[i2], j[i])
        i = i2
    return j


def _disco_espina(bm, L, S, j, mi, smooth, invert):
    """Disco triangulado entre el contorno L (vertices) y la espina S."""
    n = len(L)
    for k in range(n):
        k2 = (k + 1) % n
        ja, jb = j[k], j[k2]
        tris = [(L[k], L[k2], S[ja])]
        if jb > ja:
            for t in range(ja, jb):
                tris.append((L[k2], S[t + 1], S[t]))
        elif jb < ja:
            for t in range(ja, jb, -1):
                tris.append((L[k2], S[t - 1], S[t]))
        for tri in tris:
            _add_face(bm, tri[::-1] if invert else tri, mi, smooth)


def _prisma_espina(bm, ms, sp, j, d_out, d_in, mi_fondo, mi_pared):
    """Prisma cerrado que sigue la superficie: contorno ms y espina sp
    (puntos (p, n)), de +d_out (fuera) a -d_in (dentro) por la normal; el
    fondo (cristal) y la tapa siguen la curvatura gracias a la espina.
    Se RESTA."""
    Lo = [bm.verts.new(p + nn * d_out) for p, nn in ms]
    Li = [bm.verts.new(p - nn * d_in) for p, nn in ms]
    So = [bm.verts.new(p + nn * d_out) for p, nn in sp]
    Si = [bm.verts.new(p - nn * d_in) for p, nn in sp]
    n = len(ms)
    for k in range(n):
        k2 = (k + 1) % n
        _add_face(bm, (Lo[k], Lo[k2], Li[k2], Li[k]), mi_pared, False)
    _disco_espina(bm, Lo, So, j, mi_pared, False, True)
    _disco_espina(bm, Li, Si, j, mi_fondo, True, False)


def _ventanas(R, W, AB, tree):
    """Rebajes (bmesh a RESTAR: paredes oscuras, fondo de cristal pulido)
    del parabrisas, la luneta y las dos ventanillas en lagrima, muestreados
    por ray-cast sobre carroceria+cabina."""
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    paso = 0.05 * R
    bm = bmesh.new()
    piezas = []
    wg_f = wmax * _spline(_WG, -1.7)
    wg_r = wmax * _spline(_WG, -3.55)
    piezas.append(("techo", 1.0, [(-1.7 * R, -0.74 * wg_f), (-1.7 * R, 0.74 * wg_f),
                                  (-3.55 * R, 0.64 * wg_r), (-3.55 * R, -0.64 * wg_r)],
                   [0.08 * R, 0.08 * R, 0.14 * R, 0.14 * R]))
    wg_a = wmax * _spline(_WG, -5.4)
    wg_b = wmax * _spline(_WG, -7.0)
    piezas.append(("techo", 1.0, [(-5.4 * R, -0.74 * wg_a), (-5.4 * R, 0.74 * wg_a),
                                  (-7.0 * R, 0.60 * wg_b), (-7.0 * R, -0.60 * wg_b)],
                   [0.12 * R] * 4))
    for s in (1.0, -1.0):
        pts, rcs = [], []
        xs_lo = (-2.0, -3.1, -4.2, -5.3, -6.4)
        for xr in xs_lo:
            _w, _zf, _zb, zd, _cr, _ch = _lineas(R, wmax, xr)
            _wg, zgb, zt = _cabina_lineas(R, wmax, xr)
            pts.append((xr * R, zc + max(zd + 0.12 * R, zgb + 0.30 * (zt - zgb) + 0.03 * R)))
            rcs.append(0.12 * R if xr in (xs_lo[0], xs_lo[-1]) else 0.04 * R)
        xs_hi = (-5.9, -5.0, -4.1, -3.3, -2.6)
        for xr in xs_hi:
            _wg, zgb, zt = _cabina_lineas(R, wmax, xr)
            pts.append((xr * R, zc + zgb + 0.70 * (zt - zgb) - 0.02 * R))
            rcs.append(0.12 * R if xr in (xs_hi[0], xs_hi[-1]) else 0.04 * R)
        piezas.append(("flanco", s, pts, rcs))
    for modo, s, poly, rcs in piezas:
        loop = _loop_poly(poly, rcs, paso)
        m = max(4, int(round((max(p[0] for p in loop) - min(p[0] for p in loop)) / (0.25 * R))))
        sp2 = _espina(loop, m, paso)
        ms = _suaviza_normales(_muestreo_mc(tree, R, loop, modo, s), True)
        sp = _suaviza_normales(_muestreo_mc(tree, R, sp2, modo, s), False)
        j = _asigna_espina(loop, m)
        _prisma_espina(bm, ms, sp, j, 0.30 * R, 0.06 * R, _M_CRISTAL, _M_OSC)
    return bm


# ================================================================ detalles ==
def _barra_curva(bm, R, wmax, x_c, curv, z, semi_f, ru, rv, mi, n=15):
    """Barra de piedra curvada en planta (parabola x = x_c - curv*(y/wmax)^2)
    a la cota z, extremos en y = +-semi_f*wmax, radios (ru, rv) en R que
    se afinan hacia los extremos. _tubo (cerrada)."""
    pts, rad = [], []
    for i in range(n):
        t = -1.0 + 2.0 * i / (n - 1.0)
        f = max(1.0 - abs(t) ** 4.0, 0.0) ** 0.25
        yy = semi_f * t
        pts.append(Vector((R * (x_c - curv * yy * yy), yy * wmax, z)))
        rad.append((max(ru * R * f, 0.35), max(rv * R * f, 0.35)))
    _tubo(bm, pts, rad, mi, 12)


def _detalles_a(R, W, AB, so):
    """Piezas cerradas disjuntas que se UNEN: splitter delantero (caliza
    clara), plano del aleron, vastagos de los retrovisores, escapes y barra
    de luz trasera."""
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    bm = bmesh.new()
    _barra_curva(bm, R, wmax, 3.00, 1.55, zc - 0.42 * R, 0.70, 0.22, 0.022, _M_CAL)
    _capsula(bm, (-9.55 * R, 0.0, zc + 2.02 * R), (0.0, 1.0, 0.0), 0.86 * wmax,
             0.30 * R, 0.045 * R, _M_CAL, 5.0, 15, 16)
    for s in (1.0, -1.0):
        p0 = Vector((-1.75 * R, s * 0.86 * wmax, zc + 1.20 * R))
        p1 = Vector((-1.66 * R, s * (0.92 * wmax + 0.08 * R), zc + 1.36 * R))
        _capsula(bm, 0.5 * (p0 + p1), p1 - p0, 0.5 * (p1 - p0).length + 0.02 * R,
                 0.035 * R, 0.035 * R, _M_CAL, 2.5, 5, 8)
        _capsula(bm, (-10.12 * R, s * 0.10 * wmax, zc + 1.02 * R), (1.0, 0.0, 0.0),
                 0.14 * R, 0.07 * R, 0.07 * R, _M_OSC, 4.0, 7, 12)
    _capsula(bm, (-10.12 * R, 0.0, zc + 1.36 * R), (0.0, 1.0, 0.0), 0.72 * wmax,
             0.09 * R, 0.03 * R, _M_CRISTAL, 5.0, 9, 12)
    return bm


def _detalles_b(R, W, AB):
    """Piezas que solapan a las anteriores (operando aparte): pilones del
    aleron y cabezas de los retrovisores."""
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    bm = bmesh.new()
    for s in (1.0, -1.0):
        _capsula(bm, (-9.45 * R, s * 0.42 * wmax, zc + 1.82 * R), (0.3, 0.0, 1.0),
                 0.30 * R, 0.13 * R, 0.05 * R, _M_CAL, 4.0, 7, 12)
        _capsula(bm, (-1.64 * R, s * (0.92 * wmax + 0.16 * R), zc + 1.38 * R),
                 (0.0, 1.0, 0.0), 0.13 * R, 0.11 * R, 0.07 * R, _M_CLARA, 2.2, 9, 12)
    return bm


def _n_cuenca(s):
    return Vector((0.25, 0.75 * s, 0.60)).normalized()


def _luces(R, W, AB):
    """Barras LED de hueso dentro de las cuencas de los faros (se UNEN
    despues de los cortes)."""
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    bm = bmesh.new()
    for s in (1.0, -1.0):
        c = Vector((2.1 * R, s * 0.68 * wmax, zc + 0.73 * R)) - _n_cuenca(s) * (0.14 * R)
        _capsula(bm, c, (0.74, -0.56 * s, -0.37), 0.40 * R, 0.035 * R, 0.035 * R,
                 _M_HUESO, 2.5, 9, 10)
    return bm


# ================================================================= cortes ===
# grietas: ("techo", [(x/R, y/R)...]) | ("flanco", [(x/R, dz)...]) en el lado
# visible (lv); desconchones: ("techo", x/R, y/R) | ("flanco", x/R, dz)
_GRIETAS = [
    ("techo", [(0.30, -1.10), (0.60, -0.80), (0.90, -0.95), (1.25, -0.60)]),
    ("techo", [(-0.60, 1.20), (-0.30, 1.45), (0.10, 1.35), (0.40, 1.60)]),
    ("techo", [(1.30, 0.30), (1.60, 0.10), (1.95, 0.25)]),
    ("techo", [(-3.60, -0.50), (-4.00, -0.20), (-4.50, -0.35), (-4.90, -0.10)]),
    ("techo", [(-4.20, 0.60), (-4.60, 0.75), (-5.10, 0.60)]),
    ("techo", [(-8.40, -0.90), (-8.80, -0.50), (-9.10, -0.70)]),
    ("flanco", [(-2.30, 0.90), (-2.65, 0.62), (-2.90, 0.40)]),
    ("flanco", [(0.90, 0.95), (1.20, 0.75), (1.40, 0.50)]),
    ("flanco", [(-7.00, 1.05), (-7.30, 1.20), (-7.70, 1.15)]),
    ("flanco", [(-3.60, 0.05), (-4.00, -0.10), (-4.50, -0.05)]),
]
_DESCONCHONES = [("techo", 0.75, 0.60), ("techo", -4.40, -0.40), ("techo", -8.70, 0.50),
                 ("flanco", -3.40, 0.55), ("flanco", -0.20, 1.00)]


def _sonda(tree, R, o, d):
    loc, nrm, _i, _d = tree.ray_cast(Vector(o), Vector(d), 12.0 * R)
    return loc, nrm


# grietas (ronda 15, B13): de lejos las cintas rectas de 0.35-0.55 m y casi
# negras se leian como 'alambres'. Ahora: trazo quebrado de 6-8 puntos con
# desvio de 0.03R, una rama secundaria, ancho 0.9-1.5 m en la superficie,
# seccion en V (paredes inclinadas que reciben luz), fondo 0.04R y material
# de tono medio (_M_GRIETA); las puntas se afinan.
# v3 (B13): a 30-80 m las de 0.9-1.5 m seguian leyendose como lineas oscuras finas y
# ramificadas ('ramitas pegadas'): ahora 0.10-0.15R (2.6-3.9 m con R=26), labios en
# BISEL (seccion de 5 puntos: el labio entra a ~24 grados, menos que el umbral de 30 de
# _pulir, asi que se sombrea suave y no hay arista negra), caliza -13 % y solo las
# ramas de >= 0.5R.
_GRIETA_ANCHO = (0.10, 0.15)  # unid. R, ancho maximo en la superficie (v1: 0.9-1.5 m)
_GRIETA_PROF = 0.045          # unid. R, fondo maximo
_GRIETA_JIT = 0.03            # unid. R, desvio perpendicular de cada punto
_GRIETA_FUERA = 0.45          # m: la arista exterior del prisma sale de la superficie
_GRIETA_BISEL = (0.45, 0.35)  # quiebro del bisel: a 0.45 del semiancho y 0.35 del fondo
_GRIETA_RAMA_MIN = 0.5        # unid. R: las ramas mas cortas no se tallan


def _meandro(lista, R, rng, n_pts, jit):
    """Polilinea de control (unid. R) -> n_pts puntos 2D (m) repartidos por
    longitud de arco, con desvio perpendicular aleatorio +-jit (m; un tercio
    en las puntas). Devuelve (puntos, largo)."""
    P = [(a * R, b * R) for a, b in lista]
    seg = [max(math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]), 1e-6)
           for i in range(len(P) - 1)]
    largo = sum(seg)
    out = []
    for k in range(n_pts):
        s = largo * k / (n_pts - 1.0)
        i = 0
        while i < len(seg) - 1 and s > seg[i]:
            s -= seg[i]
            i += 1
        f = min(max(s / seg[i], 0.0), 1.0)
        tx = (P[i + 1][0] - P[i][0]) / seg[i]
        ty = (P[i + 1][1] - P[i][1]) / seg[i]
        d = rng.uniform(-1.0, 1.0) * jit * (1.0 if 0 < k < n_pts - 1 else 0.33)
        out.append((P[i][0] + tx * seg[i] * f - ty * d, P[i][1] + ty * seg[i] * f + tx * d))
    return out, largo


def _rama(pts2, largo, rng, jit, solo_arriba=False):
    """Rama secundaria 2D: sale de un punto del tercio central de la grieta
    con 35-60 grados de desvio y 35-50 % de su largo (3-4 puntos);
    solo_arriba (flancos) = hacia +b (arriba: nunca hacia los pasa-ruedas).
    Devuelve (puntos, indice del punto de arranque)."""
    n = len(pts2)
    k = rng.randint(max(1, n // 3), max(1, (2 * n) // 3 - 1))
    (x0, y0), (x1, y1) = pts2[k], pts2[min(k + 1, n - 1)]
    a0 = math.atan2(y1 - y0, x1 - x0)
    dv = math.radians(rng.uniform(35, 60))
    sg = rng.choice((-1.0, 1.0))
    if solo_arriba and math.sin(a0 + sg * dv) < math.sin(a0 - sg * dv):
        sg = -sg
    ang = a0 + sg * dv
    ca, sa = math.cos(ang), math.sin(ang)
    lr = largo * rng.uniform(0.35, 0.50)
    m = rng.choice((3, 4))
    out = [pts2[k]]
    for j in range(1, m):
        s = lr * j / (m - 1.0)
        d = rng.uniform(-1.0, 1.0) * jit * (0.6 if j < m - 1 else 0.3)
        out.append((x0 + ca * s - sa * d, y0 + sa * s + ca * d))
    return out, k


def _grieta_v(bm, pts, nrms, anchos, profs, mi, fuera=_GRIETA_FUERA, bisel=_GRIETA_BISEL):
    """Surco con BISEL (v3, B13): prisma cerrado de seccion PENTAGONAL
    (embudo: simple, no convexa) a lo largo de la polilinea `pts` (Vector) con normal local
    `nrms`: labio en la superficie a +-anchos[i]/2, quiebro del bisel en
    (+-bisel[0] * semiancho, -bisel[1] * fondo), fondo en V a profs[i] (m)
    y arista exterior `fuera` m por encima (prolongando el bisel: corte
    limpio). Restado talla una grieta cuyo labio entra a ~24 grados (con
    0.45/0.35, ancho 3 m y fondo 1.2 m) y se hunde despues a ~45: se lee
    como talla en la piedra, no como una raya. bisel=None: la V de la v1."""
    secs = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        nn = nrms[i].normalized()
        b = nn.cross(t)
        if b.length < 1e-6:
            continue
        b.normalize()
        hw0, pr = 0.5 * anchos[i], profs[i]
        if bisel is None:
            hw = hw0 * (pr + fuera) / pr
            secs.append((bm.verts.new(p - b * hw + nn * fuera), bm.verts.new(p + b * hw + nn * fuera),
                         bm.verts.new(p - nn * pr)))
            continue
        qb, qz = bisel[0] * hw0, bisel[1] * pr
        hw = hw0 + fuera * (hw0 - qb) / qz      # el bisel prolongado hasta +fuera
        secs.append((bm.verts.new(p - b * hw + nn * fuera), bm.verts.new(p + b * hw + nn * fuera),
                     bm.verts.new(p + b * qb - nn * qz), bm.verts.new(p - nn * pr),
                     bm.verts.new(p - b * qb - nn * qz)))
    if len(secs) < 2:
        return
    m = len(secs[0])
    if m == 3:
        _add_face(bm, secs[0][::-1], mi, False)
        _add_face(bm, secs[-1], mi, False)
    else:
        # tapas del embudo en dos piezas convexas (trapecio + triangulo del fondo)
        for s_, inv in ((secs[0], True), (secs[-1], False)):
            for cara in ((s_[0], s_[1], s_[2], s_[4]), (s_[4], s_[2], s_[3])):
                _add_face(bm, cara[::-1] if inv else cara, mi, False)
    for sa, sb in zip(secs, secs[1:]):
        for k in range(m):
            k2 = (k + 1) % m
            _add_face(bm, (sa[k], sa[k2], sb[k2], sb[k]), mi, False)


def _cortes(R, W, AB, so, seed, lv, tree, con_grietas=True):
    """Cascaras que se RESTAN, en dos operandos (cada uno sin solapes
    internos): (bm, bm_ramas). bm = boca inferior del morro, cuencas de los
    faros, tomas de aire laterales, grietas principales (surcos con bisel
    quebrados, _grieta_v) y desconchones (casquetes claros; se omite el que
    caeria a menos de 0.07R + medio ancho de grieta + 0.75 m de una grieta).
    bm_ramas = ramas secundarias de las grietas (arrancan DENTRO de la
    principal: van aparte). Grietas y desconchones de flanco en el lado
    visible. con_grietas=False: el mismo operando sin grietas ni ramas (red
    de seguridad de build() si la cadena con grietas sale mal)."""
    rng = random.Random(seed * 7 + 3)
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    bm = bmesh.new()
    bm_ramas = bmesh.new()
    _barra_curva(bm, R, wmax, 3.02, 1.50, zc - 0.11 * R, 0.64, 0.20, 0.13, _M_HUECO, 13)
    for s in (1.0, -1.0):
        _capsula(bm, (2.1 * R, s * 0.68 * wmax, zc + 0.73 * R),
                 (0.74, -0.56 * s, -0.37), 0.58 * R, 0.15 * R, 0.11 * R, _M_HUECO,
                 3.0, 11, 14)
        _capsula(bm, (-6.35 * R, s * 0.95 * wmax, zc + 0.52 * R), (1.0, 0.0, 0.0),
                 0.60 * R, 0.17 * R, 0.30 * R, _M_HUECO, 3.0, 11, 14)
    prof = _GRIETA_PROF * R
    jit = _GRIETA_JIT * R

    def proyecta(modo, pts2):
        """Puntos 2D (m) -> [(punto, normal)] sobre carroceria+cabina."""
        out = []
        for a, b in pts2:
            if modo == "techo":
                loc, nrm = _sonda(tree, R, (a, b, 6.0 * R), (0, 0, -1))
            else:
                loc, nrm = _sonda(tree, R, (a, lv * 4.0 * R, zc + b), (0, -lv, 0))
            if loc is not None and (not out or (loc - out[-1][0]).length > 0.5):
                out.append((loc.copy(), nrm.copy()))
        return out

    def talla(dest, ms, anchos, profs):
        if len(ms) < 2:
            return
        n_med = sum((nn for _p, nn in ms), Vector()).normalized()
        nrms = [(0.5 * nn + 0.5 * n_med).normalized() for _p, nn in ms]
        _grieta_v(dest, [p for p, _n in ms], nrms, anchos, profs, _M_GRIETA)

    trazos = {"techo": [], "flanco": []}
    w_max = _GRIETA_ANCHO[1] * R
    for modo, lista in (_GRIETAS if con_grietas else []):
        pts2, largo = _meandro(lista, R, rng, rng.randint(6, 8), jit)
        ms = proyecta(modo, pts2)
        if len(ms) < 3:
            continue
        w = rng.uniform(*_GRIETA_ANCHO) * R
        n = len(ms)
        fs = [math.sin(math.pi * i / (n - 1.0)) ** 0.7 for i in range(n)]
        anchos = [max(0.15, w * (0.12 + 0.88 * f)) for f in fs]
        talla(bm, ms, anchos, [max(0.20, prof * (0.20 + 0.80 * f)) for f in fs])
        trazos[modo] += pts2
        # (se sortea siempre: el resto de grietas no cambia con el filtro de largo)
        rama2, k = _rama(pts2, largo, rng, jit, solo_arriba=(modo == "flanco"))
        l_rama = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(rama2, rama2[1:]))
        if l_rama < _GRIETA_RAMA_MIN * R:
            continue                          # v3 (B13): las ramas cortas eran las 'ramitas'
        mr = proyecta(modo, rama2)
        if len(mr) >= 2:
            w0 = 0.65 * anchos[min(k, n - 1)]
            m = len(mr)
            gs = [1.0 - 0.8 * j / (m - 1.0) for j in range(m)]
            talla(bm_ramas, mr, [max(0.15, w0 * g) for g in gs],
                  [max(0.20, 0.8 * prof * g) for g in gs])
            trazos[modo] += rama2
    for modo, a, b in _DESCONCHONES:
        # v3: separacion medida con el semiancho de las grietas nuevas (antes 1.5 m fijos)
        if any(math.hypot(a * R - px, b * R - py) < 0.07 * R + 0.5 * w_max + 0.75
               for px, py in trazos[modo]):
            continue
        if modo == "techo":
            loc, nrm = _sonda(tree, R, (a * R, b * R, 6.0 * R), (0, 0, -1))
        else:
            loc, nrm = _sonda(tree, R, (a * R, lv * 4.0 * R, zc + b * R), (0, -lv, 0))
        if loc is None:
            continue
        c = loc + nrm * (0.01 * R)
        eje = nrm.cross(Vector((0.0, 0.0, 1.0)))
        if eje.length < 0.2:
            eje = Vector((1.0, 0.0, 0.0))
        _capsula(bm, c, eje, 0.07 * R, 0.045 * R, 0.03 * R, _M_CLARA, 2.0, 7, 10)
    return bm, bm_ramas


# ================================================================ bloques ===
def _bloques(R, W, tree, seed, macs):
    """Bloques caidos (facetados, hundidos un 30 por ciento) apoyados por
    ray-cast sobre la roca, a ambos lados de cada macizo (posiciones como
    fraccion del largo del macizo). bmesh (vacio si no hay macizo)."""
    rng = random.Random(seed * 13 + 5)
    y_lim = 0.5 * W + 2.3
    bm = bmesh.new()
    sitios = []
    for sgn, zm_pts, _wp, _al, _uc in macs:
        u0, u1 = zm_pts[0][0], zm_pts[-1][0]
        sitios += [(sgn * (u0 + fr * (u1 - u0)), yr, rr) for fr, yr, rr in _BLOQUES]
    for xr, yr, rr in sitios:
        for s in (1.0, -1.0):
            x, y, r = xr * R, s * yr * R * rng.uniform(0.9, 1.1), rr * R
            if -1.3 * R <= x <= 1.5 * R:
                y = math.copysign(min(abs(y), y_lim - r - 0.3), y)
            loc, nrm, _i, _d = tree.ray_cast(Vector((x, y, 6.0 * R)),
                                             Vector((0.0, 0.0, -1.0)), 12.0 * R)
            if loc is None or loc.z < 0.3:
                continue
            c = Vector((x, y, loc.z - 0.30 * r))
            _pedrusco(bm, c, r, rng, _M_CAL if rng.random() < 0.6 else _M_CLARA)
    return bm


# ============================================================= vegetacion ===
_VEG_NZ = 0.6       # normal minima de apoyo de cualquier mata (ronda 15, B15: <= 53 grados)


_VEG_TRIS_MAX = 3400   # presupuesto de MCOCHE_veg con UN macizo (el test admite 3500): mata 42, pino 78


def _veg_tris_max(macs):
    """Presupuesto de triangulos de MCOCHE_veg: 3400 con un macizo, +1400
    por cada macizo mas ('ambos': 4800), 2000 sin macizo."""
    return _VEG_TRIS_MAX + 1400 * (len(macs) - 1)


def _bajo_terreno(p, ft, margen=0.3):
    """True si el punto local `p` queda por debajo del terreno del sitio
    (cota ft(x, y) - margen) en tierra; False sin terreno o sobre el mar."""
    if ft is None:
        return False
    zt, mar = ft(p.x, p.y)
    return (not mar) and p.z < zt - margen


def _podar_islas(bm, tree, ft, holgura=0.5, gap=0.4, n_bajos=4):
    """Ronda 15 v3 (B15): borra de la bmesh de la vegetacion (marco local)
    las islas (matas, pinos) (a) TAPADAS: su vertice mas alto + holgura
    queda bajo el terreno del sitio `ft` (el criterio de podar_vegetacion
    con la cota del terreno); (b) VOLADAS: bajo sus `n_bajos` vertices mas
    bajos el apoyo (roca `tree` o terreno, rayo vertical desde encima de la
    isla) queda a mas de `gap` m en TODOS, o a mas de 3 gap en alguno (o no
    hay apoyo: mata que asoma por el borde de una repisa sobre el mar).
    Devuelve (islas, tapadas, voladas)."""
    if not len(bm.verts):
        return 0, 0, 0
    bm.verts.index_update()          # bmesh recien construida: sin esto los indices no valen
    bm.verts.ensure_lookup_table()
    abajo = Vector((0.0, 0.0, -1.0))
    visto, borrar, n_i, n_t, n_v = set(), [], 0, 0, 0
    for v0 in bm.verts:
        if v0.index in visto:
            continue
        pila, isla = [v0], []
        visto.add(v0.index)
        while pila:
            v = pila.pop()
            isla.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if o.index not in visto:
                    visto.add(o.index)
                    pila.append(o)
        n_i += 1
        top = max((v.co for v in isla), key=lambda q: q.z)
        if _bajo_terreno(top + Vector((0.0, 0.0, holgura)), ft, 0.0):
            borrar += isla
            n_t += 1
            continue
        gaps = []
        for v in sorted(isla, key=lambda q: q.co.z)[:n_bajos]:
            loc = tree.ray_cast(Vector((v.co.x, v.co.y, top.z + 3.0)), abajo, 4000.0)[0]
            z_sup = -1e9 if loc is None else loc.z
            if ft is not None:
                zt, mar = ft(v.co.x, v.co.y)
                if not mar:
                    z_sup = max(z_sup, zt)
            gaps.append(v.co.z - z_sup)
        # volada: ninguno de sus vertices bajos toca (> gap) o alguno cuelga claramente (> 3 gap)
        volada = bool(gaps) and (min(gaps) > gap or max(gaps) > 3.0 * gap)
        if volada:
            borrar += isla
            n_v += 1
    if borrar:
        bmesh.ops.delete(bm, geom=borrar, context="VERTS")
    return n_i, n_t, n_v


def _vegetacion(parent_collection, roca_obj, R, W, AB, tree, seed, macs, n_max=70,
                mi_caras=None, z_agua=None, ft=None):
    """MUSGO (cojines planos oscuros) en las cornisas/estratos de cada macizo
    y en las repisas del coche (valle del capo, cubierta, hombros), matas en
    las laderas y pinos en la parte baja del cerro. Malla aparte MCOCHE_veg.
    Ronda 15 (B15): en paredes de mas de 60 grados las matas salian como
    estantes. Ahora cada mata exige APOYO FRANCO: normal del impacto y
    normal media de 5 sondas (centro + 4 a 0.6 r) con nz >= _VEG_NZ, sin
    borde ni voladizo a 0.6 r (desnivel <= 0.9 r), y se ORIENTA a esa
    normal media (cojin pegado a la repisa). Las matas que tape el terreno
    o una casa de la escena final las quita podar_vegetacion().
    Ronda 15 v2 (N1): con `mi_caras` (material por cara de la malla del
    arbol) ademas PINOS y matas sobre las caras de hierba (_M_HIERBA) del
    macizo, por encima de z_agua + 3, hasta _veg_tris_max(macs) triangulos.
    Ronda 15 v3 (B15): con `ft` (cota del terreno del sitio, marco local)
    ninguna mata ni pino se apoya bajo el terreno (17 de 82 islas quedaban
    enterradas en el monte) y al final se podan las islas que el terreno
    tapa; y, con o sin terreno, las que quedan voladas a mas de 0.4 m de
    su apoyo (_podar_islas)."""
    rng = random.Random(seed * 91 + 101)
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - AB
    alto_m = max([al for _s, _z, _w, al, _u in macs] + [2.5 * R])
    bm = bmesh.new()
    placed = []
    cnt = [0]
    hubs = ((0.0, zc), (_X_REAR * R, zc))
    up = Vector((0.0, 0.0, 1.0))

    def sonda(x, y):
        loc, nrm, _i, _d = tree.ray_cast(Vector((x, y, 8.0 * R)),
                                         Vector((0.0, 0.0, -1.0)), 14.0 * R)
        return loc, nrm

    def valido(loc, nrm, min_nz, z_min, d_min):
        if loc is None or nrm.z < max(min_nz, _VEG_NZ) or loc.z < z_min:
            return False
        if _bajo_terreno(loc, ft):
            return False
        if abs(loc.y) > 0.5 * W - 0.5 * R:
            for xh, zh in hubs:
                if math.hypot(loc.x - xh, loc.z - zh) < 1.30 * R:
                    return False
        return not any((loc - p).length < d_min for p in placed)

    def apoyo(loc, r):
        """Normal media de apoyo bajo la mata (None si cae por un borde,
        hay un voladizo encima o la repisa es demasiado empinada)."""
        acc = Vector()
        for dx, dy in ((0.0, 0.0), (0.6, 0.0), (-0.6, 0.0), (0.0, 0.6), (0.0, -0.6)):
            l2, n2 = sonda(loc.x + dx * r, loc.y + dy * r)
            if l2 is None or abs(l2.z - loc.z) > 0.9 * r:
                return None
            acc += n2
        acc.normalize()
        return acc if acc.z >= _VEG_NZ else None

    def cojin(loc, n_ap, r, sz, mi_):
        """Mata _blob orientada a la normal de apoyo (mezclada con la vertical)."""
        n_or = (0.35 * up + 0.65 * n_ap).normalized()
        c = loc + n_or * (0.12 * r)
        i0 = len(bm.verts)
        _blob(bm, c, r, sz, rng, mi_)
        q = up.rotation_difference(n_or)
        bm.verts.ensure_lookup_table()
        for i in range(i0, len(bm.verts)):
            v = bm.verts[i]
            v.co = c + q @ (v.co - c)

    def grupo(x0, x1, y0, y1, n_here, r_rng, sz, min_nz=0.45, z_min=0.5, pinos=0,
              d_min=3.0, mi=0):
        n = 0
        for _ in range(60):
            if n >= n_here or cnt[0] >= n_max:
                break
            loc, nrm = sonda(rng.uniform(x0, x1), rng.uniform(y0, y1))
            if not valido(loc, nrm, min_nz, z_min, d_min):
                continue
            r = rng.uniform(*r_rng)
            n_ap = apoyo(loc, r)
            if n_ap is None:
                continue
            placed.append(loc.copy())
            cojin(loc, n_ap, r, sz, mi if mi == 0 else (0 if rng.random() < 0.6 else 1))
            cnt[0] += 1
            n += 1
        for _ in range(pinos):
            for _t in range(16):
                loc, nrm = sonda(rng.uniform(x0, x1), rng.uniform(y0, y1))
                if (valido(loc, nrm, 0.6, z_min, 6.0) and loc.z < 0.75 * alto_m
                        and apoyo(loc, 2.5) is not None):
                    placed.append(loc.copy())
                    _pino(bm, loc, rng.uniform(11.0, 16.0), rng,
                          0 if rng.random() < 0.5 else 1, 2)
                    break

    for sgn, zm_pts, _wp, _al, u_c in macs:
        u0, u1 = zm_pts[0][0], zm_pts[-1][0]
        xa, xb = sgn * (u0 + 0.14 * (u1 - u0)) * R, sgn * (u0 + 0.72 * (u1 - u0)) * R
        x0, x1 = min(xa, xb), max(xa, xb)
        for s in (1.0, -1.0):
            grupo(x0, x1, s * (wmax + 0.2 * R), s * (wmax + 2.2 * R), 9, (1.2, 2.4), 0.38)
            grupo(x0, x1, s * (wmax + 1.0 * R), s * (wmax + 4.5 * R), 6, (2.6, 4.2), 0.6,
                  min_nz=0.3, mi=1)
            grupo(x0 - 0.5 * R, x1 + 0.5 * R, s * (wmax + 1.5 * R), s * (wmax + 5.0 * R),
                  0, (2.0, 3.0), 0.5, pinos=3)
        xc0, xc1 = (sgn * (u_c - 1.1) * R, sgn * (u_c + 1.5) * R)
        grupo(min(xc0, xc1), max(xc0, xc1), -1.5 * wmax, 1.5 * wmax, 6, (2.2, 3.8), 0.55,
              min_nz=0.35, mi=1)
    grupo(0.0, 0.9 * R, -1.0 * R, 1.0 * R, 3, (1.0, 1.8), 0.35, min_nz=0.3, d_min=2.0)
    grupo(-9.4 * R, -8.2 * R, -0.9 * wmax, 0.9 * wmax, 4, (1.0, 1.8), 0.35, min_nz=0.3,
          d_min=2.0)
    for s in (1.0, -1.0):
        grupo(-5.0 * R, -2.2 * R, s * 0.80 * wmax, s * 0.90 * wmax, 2, (0.8, 1.4), 0.35,
              min_nz=0.3, d_min=2.0)
    if mi_caras:
        _veg_hierba(bm, R, wmax, tree, rng, macs, mi_caras, placed, valido, apoyo, cojin,
                    -1e9 if z_agua is None else z_agua + 3.0, _veg_tris_max(macs))
    _n_isl, n_pod, n_vol = _podar_islas(bm, tree, ft)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("MCOCHE_veg")
    bm.to_mesh(me)
    bm.free()
    me.validate()
    for mt in _mats_veg():
        me.materials.append(mt)
    ob = bpy.data.objects.new("MCOCHE_veg", me)
    ob["mcoche_podadas_terreno"] = int(n_pod)
    ob["mcoche_podadas_voladas"] = int(n_vol)
    parent_collection.objects.link(ob)
    ob.parent = roca_obj
    return ob


def _tris_bm(bm):
    return sum(len(f.verts) - 2 for f in bm.faces)


def _veg_hierba(bm, R, wmax, tree, rng, macs, mi_caras, placed, valido, apoyo, cojin, z_min,
                tri_max=_VEG_TRIS_MAX, pinos=(12, 5), matas=(10, 4), intentos=700):
    """Ronda 15 v2 (N1): PINOS y matas sobre la HIERBA del macizo (caras
    _M_HIERBA de la roca, buscadas por rayo vertical) con el mismo apoyo
    franco que el resto (valido/apoyo/cojin de _vegetacion), por encima de
    z_min y sin pasar de tri_max triangulos en toda la malla. pinos y
    matas = (macizo de la zaga, macizo del morro)."""
    tris = _tris_bm(bm)
    abajo = Vector((0.0, 0.0, -1.0))
    for sgn, zm_pts, _wp, _al, _uc in macs:
        k = 0 if sgn < 0 else 1
        x0, x1 = sorted((sgn * zm_pts[0][0] * R, sgn * zm_pts[-1][0] * R))
        ymax = wmax + 4.5 * R
        n_p = n_m = 0
        for _ in range(intentos):
            if (n_p >= pinos[k] and n_m >= matas[k]) or tris + 42 > tri_max:
                break
            loc, nrm, idx, _d = tree.ray_cast(Vector((rng.uniform(x0, x1), rng.uniform(-ymax, ymax),
                                                     8.0 * R)), abajo, 14.0 * R)
            if (loc is None or idx is None or idx >= len(mi_caras) or mi_caras[idx] != _M_HIERBA
                    or loc.z < z_min):
                continue
            if (n_p < pinos[k] and tris + 78 <= tri_max and valido(loc, nrm, 0.7, z_min, 7.0)
                    and apoyo(loc, 2.5) is not None):
                placed.append(loc.copy())
                _pino(bm, loc, rng.uniform(10.0, 15.0), rng, 0 if rng.random() < 0.5 else 1, 2)
                n_p += 1
                tris += 78
                continue
            if n_m < matas[k] and valido(loc, nrm, 0.6, z_min, 4.0):
                r = rng.uniform(2.0, 3.6)
                n_ap = apoyo(loc, r)
                if n_ap is None:
                    continue
                placed.append(loc.copy())
                cojin(loc, n_ap, r, 0.55, 0 if rng.random() < 0.6 else 1)
                n_m += 1
                tris += 42


def _arbol_mundo(oclusores, caja, margen):
    """BVH (coordenadas de MUNDO) de los triangulos de `oclusores` (mallas
    evaluadas) con algun vertice dentro de la caja xy (x0, y0, x1, y1) +
    margen. None si no queda ninguno."""
    import numpy as np
    x0, y0, x1, y1 = caja[0] - margen, caja[1] - margen, caja[2] + margen, caja[3] + margen
    dg = bpy.context.evaluated_depsgraph_get()
    verts, tris, base = [], [], 0
    for ob in oclusores:
        if ob is None or getattr(ob, "type", None) != "MESH":
            continue
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        if (max(p.x for p in bb) < x0 or min(p.x for p in bb) > x1 or
                max(p.y for p in bb) < y0 or min(p.y for p in bb) > y1):
            continue                     # lejos de la vegetacion: ni se evalua
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        try:
            me.calc_loop_triangles()
            nv, nt = len(me.vertices), len(me.loop_triangles)
            if nv == 0 or nt == 0:
                continue
            co = np.empty(nv * 3, dtype=np.float32)
            me.vertices.foreach_get("co", co)
            mw = np.array(ob.matrix_world, dtype=float)
            cw = co.reshape(-1, 3).astype(float) @ mw[:3, :3].T + mw[:3, 3]
            tri = np.empty(nt * 3, dtype=np.int32)
            me.loop_triangles.foreach_get("vertices", tri)
            tri = tri.reshape(-1, 3)
            den = (cw[:, 0] > x0) & (cw[:, 0] < x1) & (cw[:, 1] > y0) & (cw[:, 1] < y1)
            tri = tri[den[tri].any(axis=1)]
            if not len(tri):
                continue
            usados, inv = np.unique(tri.ravel(), return_inverse=True)
            verts += cw[usados].tolist()
            tris += (inv.reshape(-1, 3) + base).tolist()
            base += len(usados)
        finally:
            ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, tris) if tris else None


def podar_vegetacion(raiz, oclusores, holgura=0.5, margen=30.0):
    """PARA EL INTEGRADOR (ronda 15, B15), con el coche ya colocado y el
    tunel taladrado: borra de los MCOCHE_veg* de `raiz` (el clon colocado,
    p. ej. TUNEL_acantilado) las islas (matas y pinos) TAPADAS en la escena
    final: el rayo vertical HACIA ARRIBA desde su vertice mas alto
    (+holgura) choca con alguno de `oclusores` (objetos malla: TERRENO,
    CASAS_*, la propia roca...). Asi no quedan poligonos perdidos dentro del
    monte (morro enterrado en la ladera T1) ni en los zocalos. Si la malla
    de la vegetacion es compartida (clone() copia el objeto, no la malla) se
    duplica antes. Devuelve (islas, borradas) y lo apunta en
    veg["mcoche_podadas"]."""
    vegs = [o for o in [raiz] + list(raiz.children_recursive)
            if o.type == "MESH" and o.name.startswith("MCOCHE_veg")]
    bpy.context.view_layer.update()
    n_islas = n_borr = 0
    for veg in vegs:
        if not len(veg.data.vertices):
            continue
        mw = veg.matrix_world
        cw = [mw @ v.co for v in veg.data.vertices]
        caja = (min(p.x for p in cw), min(p.y for p in cw), max(p.x for p in cw),
                max(p.y for p in cw))
        tree = _arbol_mundo([o for o in oclusores if o is not veg], caja, margen)
        bm = bmesh.new()
        bm.from_mesh(veg.data)
        bm.verts.ensure_lookup_table()
        visto, borrar, n_aqui = set(), [], 0
        up = Vector((0.0, 0.0, 1.0))
        for v0 in bm.verts:
            if v0.index in visto:
                continue
            pila, isla = [v0], []
            visto.add(v0.index)
            while pila:
                v = pila.pop()
                isla.append(v)
                for e in v.link_edges:
                    o = e.other_vert(v)
                    if o.index not in visto:
                        visto.add(o.index)
                        pila.append(o)
            n_islas += 1
            top = max((cw[v.index] for v in isla), key=lambda p: p.z)
            if tree is not None:
                hit = tree.ray_cast(top + up * holgura, up, 5000.0)[0]
                if hit is not None:
                    borrar += isla
                    n_aqui += 1
        if borrar:
            if veg.data.users > 1:
                veg.data = veg.data.copy()
            bmesh.ops.delete(bm, geom=borrar, context="VERTS")
            bm.to_mesh(veg.data)
            veg.data.update()
        bm.free()
        veg["mcoche_podadas"] = int(veg.get("mcoche_podadas", 0)) + n_aqui
        n_borr += n_aqui
    return n_islas, n_borr


# ================================================================== build ===
def _nm(bm):
    return sum(1 for e in bm.edges if len(e.link_faces) != 2)


def _pares_cruce(bm):
    """Pares de caras que se cruzan sin compartir vertice (BVH overlap)."""
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    out = []
    for i, j in tree.overlap(tree):
        if i < j:
            vi = {v.index for v in bm.faces[i].verts}
            if not any(v.index in vi for v in bm.faces[j].verts):
                out.append((i, j))
    return out


def _auto_inter(me, fundir=True, dist=0.3):
    """Numero de pares de caras que se cruzan sin compartir vertice. Con
    fundir=True suelda antes los vertices casi coincidentes de esos pares
    (resto tipico del Boolean: la curva de corte queda duplicada a < dist,
    p. ej. 9 cm, entre el pedestal y el vientre) y reescribe la malla si
    sigue manifold."""
    bm = bmesh.new()
    bm.from_mesh(me)
    pares = _pares_cruce(bm)
    if pares and fundir:
        bm.faces.ensure_lookup_table()
        vs = set()
        for i, j in pares:
            vs.update(bm.faces[i].verts)
            vs.update(bm.faces[j].verts)
        bmesh.ops.remove_doubles(bm, verts=list(vs), dist=dist)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if _nm(bm) == 0:
            bm.to_mesh(me)
            me.validate()
            me.update()
            bm.free()
            bm = bmesh.new()
            bm.from_mesh(me)
            pares = _pares_cruce(bm)
    bm.free()
    return len(pares)


def _limpiar(me, dist=2e-3):
    """Elimina cascaras sueltas (< 12 caras, restos del Boolean) y colapsa
    aristas < dist (dissolve_degenerate; si rompe la malla, remove_doubles
    sobre sus vertices; si tambien la rompe, se deja) para que el solver
    EXACT del integrador (tunel) no falle. Solo escribe la malla si queda
    manifold. Devuelve (n de aristas no manifold, n de aristas cortas que
    quedan)."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    visto = set()
    for f0 in bm.faces:
        if f0.index in visto:
            continue
        pila, isla = [f0], []
        visto.add(f0.index)
        while pila:
            f = pila.pop()
            isla.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in visto:
                        visto.add(g.index)
                        pila.append(g)
        if len(isla) < 12:
            bmesh.ops.delete(bm, geom=isla, context="FACES")
            bm.faces.ensure_lookup_table()
    for _ronda in range(3):
        cortas = [e for e in bm.edges if e.calc_length() < dist]
        if not cortas:
            break
        bm.verts.index_update()
        idx = sorted({v.index for e in cortas for v in e.verts})
        bm2 = bm.copy()
        bmesh.ops.dissolve_degenerate(bm2, dist=dist, edges=bm2.edges[:])
        if _nm(bm2) == 0:
            bm.free()
            bm = bm2
            continue
        bm2.free()
        bm3 = bm.copy()
        bm3.verts.ensure_lookup_table()
        bmesh.ops.remove_doubles(bm3, verts=[bm3.verts[i] for i in idx], dist=1.5 * dist)
        if _nm(bm3) == 0:
            bm.free()
            bm = bm3
            continue
        bm3.free()
        break
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    nm = _nm(bm)
    quedan = sum(1 for e in bm.edges if e.calc_length() < dist)
    if nm == 0:
        bm.to_mesh(me)
        me.validate()
        me.update()
    bm.free()
    return nm, quedan


def _quitar_huecos(me):
    """Cascaras cerradas ENCERRADAS por la cascara principal (huecos sin
    salida dentro de la roca: con enterrado='ambos' la boca del morro queda
    tapada por el afloramiento y dejaba 168 caras de 'hueco' dentro del
    macizo) -> fuera: poligonos que nadie ve. Encerrada = un rayo desde su
    centro cruza la cascara principal un numero impar de veces (voto de 3
    direcciones). Devuelve el numero de cascaras quitadas."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    visto, islas = set(), []
    for f0 in bm.faces:
        if f0.index in visto:
            continue
        pila, isla = [f0], []
        visto.add(f0.index)
        while pila:
            f = pila.pop()
            isla.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in visto:
                        visto.add(g.index)
                        pila.append(g)
        islas.append(isla)
    if len(islas) < 2:
        bm.free()
        return 0
    islas.sort(key=len, reverse=True)
    tree = BVHTree.FromPolygons([v.co.copy() for v in bm.verts],
                                [[v.index for v in f.verts] for f in islas[0]])
    quitar, n_q = [], 0
    for isla in islas[1:]:
        c = sum((f.calc_center_median() for f in isla), Vector()) / len(isla)
        votos = 0
        for d in (Vector((0.0, 0.0, 1.0)), Vector((0.31, 0.95, 0.0)), Vector((-0.80, 0.0, -0.60))):
            n_hits, o = 0, c.copy()
            for _ in range(400):
                loc = tree.ray_cast(o, d, 1.0e5)[0]
                if loc is None:
                    break
                n_hits += 1
                o = loc + d * 1.0e-3
            votos += n_hits % 2
        if votos >= 2:
            quitar += isla
            n_q += 1
    if quitar:
        bmesh.ops.delete(bm, geom=quitar, context="FACES")
        bm.to_mesh(me)
        me.validate()
        me.update()
    bm.free()
    return n_q


def build(parent_collection, radio=40.0, ancho=78.0, alto_base=12.0,
          z_fondo=-45.0, seed=0, con_vegetacion=True, **params):
    """McLaren de piedra integrado en el cerro. Devuelve la malla raiz
    MCOCHE_roca (unica, cerrada); la vegetacion va en el hijo MCOCHE_veg.
    params: n_radios=10, segmentos_por_radio=7, talud_deg=38 (o par (lado
    -Y, lado +Y)), solver="MANIFOLD", detalle_secundario=0.6,
    lado_visible=+1 (-1 si el integrador pone +X local = -n: ver cabecera),
    enterrado="zaga" ('zaga' | 'morro' | 'ambos'), alto_montana=None (m
    sobre z=0, cresta del macizo; None = 3.2R zaga / 2.5R morro; con
    'ambos' admite un par (zaga, morro)), largo_macizo=None (unid. R desde
    el origen; None = 14.5 zaga / 4.8 morro; <= arranque + 0.4 o 0 = SIN
    macizo; con 'ambos' admite un par), ancho_macizo=1.0 (factor de la
    meseta, o par por lado -Y/+Y), z_agua=None (cota LOCAL del mar: roca
    mojada solo hasta z_agua + 1 y nada de hierba ni pinos por debajo de
    z_agua + 3; None = z_fondo + 9.4, la convencion del integrador; queda en
    obj["z_agua"]), terreno='auto' (ronda 15 v3: cota del terreno del sitio
    en el marco local para la falda de hierba/caliza meteorizada, las
    cuencas medio enterradas y la poda de matas enterradas; 'auto' = malla
    TERRENO de la escena si los parametros son los del integrador, ver
    _terreno_sitio; callable f(lx, ly) -> (z_local, es_mar); None = sin
    terreno; queda en obj["terreno_sitio"]). Tras la cadena Boolean se comprueban
    no-manifold y auto-intersecciones; si MANIFOLD deja alguna se repite
    con EXACT y se conserva el mejor (mesh["mcoche_auto_inter"]).
    Cadena Boolean (depsgraph, temporales en bpy.context.scene.collection):
    roca U bloques U carroceria U cabina - pasa-ruedas U ruedas U detalles_a
    U detalles_b - cristales - cortes - ramas U luces. Si el depsgraph no
    evalua -> RuntimeError. Tras colocar el clon en la escena, el
    integrador puede llamar a podar_vegetacion()."""
    R, W, AB = float(radio), float(ancho), float(alto_base)
    zf = float(z_fondo)
    n_spokes = int(params.get("n_radios", 10))
    m = max(7, int(params.get("segmentos_por_radio", 7)))
    talud = _par(params.get("talud_deg", 38.0), "talud_deg")
    solver = str(params.get("solver", "MANIFOLD")).upper()
    det = float(params.get("detalle_secundario", 0.6))
    lv = 1.0 if float(params.get("lado_visible", 1.0)) >= 0.0 else -1.0
    ent = str(params.get("enterrado", "zaga")).lower()
    ent = "morro" if ent.startswith("m") else ("ambos" if ent.startswith("a") else "zaga")
    anc = _par(params.get("ancho_macizo", 1.0), "ancho_macizo")
    za = params.get("z_agua", None)
    z_agua = zf + _Z_AGUA_SOBRE_FONDO if za is None else float(za)
    macs = _macizos(ent, params.get("largo_macizo", None), params.get("alto_montana", None), R)
    largo_ef = {"zaga": 0.0, "morro": 0.0}
    alto_ef = {"zaga": 0.0, "morro": 0.0}
    for sgn, zm_pts, _wp, al, _uc in macs:
        lado = "zaga" if sgn < 0 else "morro"
        largo_ef[lado] = zm_pts[-1][0]
        alto_ef[lado] = al
    so = seed * 17.37 + 3.1
    mats = _mats_mc()
    hubs_x = (0.0, _X_REAR * R)

    me_roca = _malla("MCOCHE_tmp_roca", _roca(R, W, AB, zf, so, talud, macs, anc, z_agua), mats)
    bm_r = bmesh.new()
    bm_r.from_mesh(me_roca)
    tree_r = BVHTree.FromBMesh(bm_r)
    bm_r.free()
    me_bloq = _malla("MCOCHE_tmp_bloques", _bloques(R, W, tree_r, seed, macs), mats)
    bm_body = _carroceria(R, W, AB, so)
    bm_cab = _cabina(R, W, AB, so)
    bm_all = bmesh.new()
    for bm_src in (bm_body, bm_cab):
        tmp = bpy.data.meshes.new("MCOCHE_tmp_all")
        bm_src.to_mesh(tmp)
        bm_all.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    tree_b = BVHTree.FromBMesh(bm_all)
    bm_all.free()
    me_body = _malla("MCOCHE_tmp_cuerpo", bm_body, mats)
    me_cab = _malla("MCOCHE_tmp_cabina", bm_cab, mats)
    me_rebajes = _malla("MCOCHE_tmp_cristales", _ventanas(R, W, AB, tree_b), mats)
    fuera_rear = 0.03 * R if ent in ("zaga", "ambos") else 0.30 * R
    fuera_front = 0.30 * R
    me_wells = _malla("MCOCHE_tmp_pasarruedas",
                      _pasa_ruedas(R, W, AB, ((0.0, fuera_front), (_X_REAR * R, fuera_rear))),
                      mats)
    discos = []
    for xh in hubs_x:
        for side in (1.0, -1.0):
            d_here = 1.0 if (xh == 0.0 and side == lv) else det
            discos.append(_disco_rueda(R, W, AB, xh, side, so, n_spokes, m, d_here))
    me_discs = _fusionar(discos, "MCOCHE_tmp_ruedas", mats)
    me_det_a = _malla("MCOCHE_tmp_detalles_a", _detalles_a(R, W, AB, so), mats)
    me_det_b = _malla("MCOCHE_tmp_detalles_b", _detalles_b(R, W, AB), mats)
    bm_cut, bm_ramas = _cortes(R, W, AB, so, seed, lv, tree_b)
    me_cut = _malla("MCOCHE_tmp_cortes", bm_cut, mats)
    me_ramas = _malla("MCOCHE_tmp_grietas_rama", bm_ramas, mats)
    me_luz = _malla("MCOCHE_tmp_luces", _luces(R, W, AB), mats)
    coll_tmp = bpy.context.scene.collection
    temp = [_objeto(me.name, me, coll_tmp)
            for me in (me_roca, me_bloq, me_body, me_cab, me_wells, me_discs, me_det_a,
                       me_det_b, me_rebajes, me_cut, me_ramas, me_luz)]
    (ob_roca, ob_bloq, ob_body, ob_cab, ob_wells, ob_discs, ob_det_a, ob_det_b,
     ob_rebajes, ob_cut, ob_ramas, ob_luz) = temp
    ops = [("UNION", ob_bloq), ("UNION", ob_body), ("UNION", ob_cab),
           ("DIFFERENCE", ob_wells), ("UNION", ob_discs), ("UNION", ob_det_a),
           ("UNION", ob_det_b), ("DIFFERENCE", ob_rebajes), ("DIFFERENCE", ob_cut)]
    if len(me_ramas.polygons):
        ops.append(("DIFFERENCE", ob_ramas))     # ramas de las grietas (solapan la principal)
    ops.append(("UNION", ob_luz))
    def _resultado(solv, ops_=ops):
        """(malla, no-manifold, auto-intersecciones) tras la cadena con
        `solv`, pulido y limpieza."""
        m_ = _boolean_cadena(ob_roca, ops_, solv)
        n_m = _pulir(m_)
        n_l, _q = _limpiar(m_)
        a_i = _auto_inter(m_)
        n_l, _q = _limpiar(m_)
        if n_l == 0:
            n_m = 0
        return m_, n_m, a_i

    # ronda 15 v3: red de seguridad. Antes ganaba siempre el menor (no-manifold, auto-inter)
    # y una cadena EXACT DERRUMBADA (p. ej. R=40: 733 vertices tras restar los cortes, el
    # coche desaparecia) tiene (0, 0): ahora una candidata con menos del 60 % de las caras
    # de la mayor no cuenta, y si ni MANIFOLD ni EXACT salen limpias se prueba la cadena con
    # los cortes SIN grietas (faros, tomas, boca y desconchones siguen).
    cands = []

    def _clave(c):
        n_max = max(len(c_[0].polygons) for c_ in cands)
        return (1 if len(c[0].polygons) < 0.6 * n_max else 0, c[1], c[2])

    me_, nm_, ai_ = _resultado(solver)
    cands.append((me_, nm_, ai_, solver, 1))
    if (nm_ != 0 or ai_ != 0) and solver != "EXACT":
        me_, nm_, ai_ = _resultado("EXACT")
        cands.append((me_, nm_, ai_, "EXACT", 1))
    if min(_clave(c) for c in cands) != (0, 0, 0):
        me_cut0 = _malla("MCOCHE_tmp_cortes_sin_grietas",
                         _cortes(R, W, AB, so, seed, lv, tree_b, con_grietas=False)[0], mats)
        ob_cut0 = _objeto(me_cut0.name, me_cut0, coll_tmp)
        temp.append(ob_cut0)
        ops0 = [(o_, (ob_cut0 if b_ is ob_cut else b_)) for o_, b_ in ops if b_ is not ob_ramas]
        me_, nm_, ai_ = _resultado(solver, ops0)
        cands.append((me_, nm_, ai_, solver, 0))
    mejor = min(cands, key=_clave)
    for c in cands:
        if c is not mejor:
            bpy.data.meshes.remove(c[0])
    me, nm, ai, usado, con_grietas = mejor
    for ob in temp:
        mesh = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    me.name = "MCOCHE_roca"
    if not me.materials:
        for mt in mats:
            me.materials.append(mt)
    me["mcoche_huecos_quitados"] = _quitar_huecos(me)
    me["mcoche_grietas"] = int(con_grietas)
    # ronda 15 v3 (J10 c / B11 / B15): terreno del sitio en el marco local (o None)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    ft = _terreno_sitio(params.get("terreno", "auto"), R, W, zf, lv,
                        (min(xs), min(ys), max(xs), max(ys)))
    for k_, v_ in _contacto_terreno(me, R, W, AB, ft, z_agua, so).items():
        me["mcoche_" + k_] = int(v_)
    me["mcoche_no_manifold"] = nm
    me["mcoche_auto_inter"] = ai
    me["mcoche_solver"] = usado
    obj = bpy.data.objects.new("MCOCHE_roca", me)
    obj["radio"], obj["ancho"], obj["alto_base"], obj["z_fondo"] = R, W, AB, zf
    obj["lado_visible"] = lv
    obj["enterrado"] = ent
    if ent == "ambos":
        obj["alto_montana"] = (alto_ef["zaga"], alto_ef["morro"])
        obj["largo_macizo"] = (largo_ef["zaga"], largo_ef["morro"])
    else:
        obj["alto_montana"] = alto_ef[ent]
        obj["largo_macizo"] = largo_ef[ent]
    obj["talud_deg"] = talud
    obj["ancho_macizo"] = anc
    obj["z_agua"] = z_agua
    obj["terreno_sitio"] = ft is not None
    obj["hubs"] = ((0.0, 0.5 * W, R - AB), (_X_REAR * R, 0.5 * W, R - AB))
    suelo = [v.co.x for v in me.vertices if abs(v.co.z) < 1.0]
    obj["huella_x"] = (min(suelo), max(suelo)) if suelo else (0.0, 0.0)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    obj["bbox"] = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
    parent_collection.objects.link(obj)
    if con_vegetacion:
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        mi_caras = [f.material_index for f in bm.faces]
        tree = BVHTree.FromBMesh(bm)
        bm.free()
        _vegetacion(parent_collection, obj, R, W, AB, tree, seed, macs, mi_caras=mi_caras,
                    z_agua=z_agua, ft=ft)
    return obj
