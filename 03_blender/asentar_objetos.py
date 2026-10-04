"""asentar_objetos.py - ASIENTA sobre el suelo real los objetos apoyados de la
escena integrada (ronda 15, T6) y da un informe de casas enterradas/flotantes.

  blender --background --factory-startup --python asentar_objetos.py
  env BLEND = ruta del .blend (defecto 03_blender/porto_corsa.blend)
  env GEOM  = ruta de geometria_3d.json (defecto 03_blender/geometria_3d.json)

Que hace:
  1. Construye UN BVH (mathutils.bvhtree, mallas evaluadas en coordenadas de
     mundo) con las superficies de apoyo: TERRENO, rocas (PPUEBLO_roca/plaza/
     carretera/escaleras de los PENON_*, TUNEL_acantilado = McLaren/MCOCHE_*),
     caminos (CAMINO_asfalto/adoquin/tierra/muelle/terraplen), arcenes y
     aceras de la pista, PIT_LANE/PIT_*suelo, TUNEL_suelo y MIRADOR_paseo.
  2. Para cada objeto RAIZ (sin padre, fuera de LIB) de las familias apoyadas
     (arboles VEG_/OLI_, mobiliario CALLE_, pacas y vallas CARRERA_, coches
     COCHE_, carteles/vallas CAMINO_, props ITAL_, camaras de tierra...) lanza
     un rayo vertical desde z=+400 y recoge TODOS los impactos. Los impactos
     separados menos de GAP_APILADO (3 m) son la MISMA superficie apilada
     (cinta de camino, arcen o acera sobre el terreno; cara superior e inferior
     de una cinta): de cada pila solo vale la CIMA. Entre las cimas se elige la
     mas cercana a la z actual (asi un arbol bajo un voladizo de roca a > 3 m no
     sube al techo, pero nada queda enterrado bajo una calzada o un arcen).
     z = impacto + 0.02. Registra movidos, sin impacto, saltos > 25 m y objetos
     que quedan bajo el mar.
  3. Edificios (CASAS_, PENON_casa, HOTEL/AYTO/CAMPANILE/CASINO...): NO se
     mueven; se informa enterrada (terreno > z_base + 1.2 en alguna esquina) o
     flotante (terreno < z_base - 0.6 sin zocalo; con zocalo, por debajo del
     fondo del zocalo - 0.3) por las 4 esquinas de la base.
  4. Autocomprobacion: rayo hacia ARRIBA desde la base de cada objeto apoyado
     (desde su apoyo + 0.05) contra soporte + PISTA + PIT_LANE: si toca algo a
     < 3 m es 'bajo_superficie' (fallo); si toca algo mas arriba pero por
     debajo de la copa del objeto es 'atraviesa_voladizo' (aviso).
  5. Guarda el .blend y escribe renders/qa/asentar.json.
Ronda 15 v1 (inspectores):
  - El BVH se triangula IGUAL que el render y el exportador (mesh.loop_triangles:
    los quads del TERRENO se parten por la diagonal 0-2). Antes FromPolygons
    (all_triangles=False) partia los quads no planos por la otra diagonal y en
    laderas los arboles quedaban hasta 1 m flotando o enterrados (A-18, N2).
  - Son apoyo tambien las losas del plan urbano: CAMINO_calle/enlace/travesia/
    rampa/escalera, CALLE_plaza* (plaza, plaza_fondo, plaza_hotel, plazoleta) y
    el relleno de los bancales (ITAL_bancal_tierra) (B7, C-04, G7, N1). Una losa
    CALLE_plaza* es MACIZA: lo que el rayo encuentra por debajo de su cara de
    arriba y hasta su fondo es la misma pila (nada se queda dentro del tambor).
  - Arboles (VEG_, OLI_, ITAL_cipres, ITAL_olivo): 5 rayos (centro y anillo de
    R_ANILLO m sobre la MISMA malla); base = minimo - hundimiento (no flota por el
    lado de abajo). Si el desnivel del anillo pasa de DESNIVEL_MOVER se prueba a
    moverlo PASO_LADERA m ladera arriba/abajo; si sigue > DESNIVEL_MAX se quita.
    Un arbol suelto (no VEG_plazoleta) con el tronco en una losa del plan (calle,
    escalera, plaza: LOSA_PLAN) es un resto del reparto de vegetacion: se quita.
    El rayo de autocomprobacion de un arbol sale del suelo del CENTRO del tronco.
  - Hijos sueltos: los arboles hijos de ITAL_cipreses / ITAL_bancal / ITAL_ermita
    se asientan uno a uno (las hileras rigidas quedaban +-20 m) (E1, J2, C-05, D2).
    La raiz ITAL_bancal no se mueve (su cota la fija el integrador en la linea del
    muro); se informa su desnivel en 'bancales'.
  - Arbol dentro de un muro o una casa (N3): rayos verticales en el tronco y a
    +-0.3 m contra CAMINO_muro/MIRADOR_muro/bancales/edificios; si alguno da por
    encima del suelo, se mueve 1.5-3 m hacia fuera y se vuelve a asentar; si no
    hay sitio, se quita. Informe 'dentro_de_muro'.
Ronda 15 v2 (inspectores):
  - Losas CALLE_plaza* (G2-09): ANTES del BVH, el anillo de fondo de cada losa baja hasta 0.15 m
    bajo el TERRENO definitivo a lo largo de sus aristas (el canto se calculaba con el terreno de
    antes de las explanadas del integrador y quedaba aire bajo el borde). Informe 'losas'.
  - Tronco en o BAJO una calzada (D2-03): todos los impactos (no las cimas) del centro y del anillo
    de 0.6 m; una losa del plan o una cinta de camino entre la base - 0.3 y la copa -> el arbol se
    aparta 2-4 m o se quita. La autocomprobacion quita (no apunta) un arbol con una calzada encima.
  - Pisada (E2-10): ningun arbol nuevo (ni movido) con un camino a < 1.5 m del tronco; si el sitio
    original lo tiene, se intenta apartar (si no hay sitio, se queda y va a 'junto_a_camino').
  - Copa sobre una calzada (A-r2-11): rayos hacia abajo desde 16 puntos de la copa; calzada a menos
    de 4.5 m (2.2 en senderos y escaleras) -> el arbol se aparta 2-4 m o se quita ('copa_calzada').
    CAMINO_terraplen ya no es apoyo de arboles: es obstaculo (como un muro).
  - Coches (C2-03): las filas COCHE_fila* no se mueven enteras; cada coche se asienta sobre sus 4
    ruedas (cabeceo y balanceo del plano de los 4 impactos, 3 cm hundido); se quita si el desnivel
    pasa de 0.8 m, si tiene roca encima (< 8 m) o si el suelo le atraviesa la carroceria.
  env QA_OUT = carpeta del informe (defecto renders/qa; para pruebas sobre copias).
Ronda 15 v3 (inspectores): garantias de TERRENO antes de las losas y del BVH (solo nodos de la rejilla,
  nunca en el mar ni junto a la pista, y limitadas por casas, muros, losas, calles y rocas de alrededor):
  - C-12/C-08: ninguna hierba sobre las losas CALLE_plaza*/CALLE_plazoleta* (a >= 0.5 m de su borde, el
    terreno <= corona - 0.05: se bajan lo justo los nodos que sobran, como mucho 1.5 m).
  - N1/E4: senderos CAMINO_tierra sobre la cinta real: el borde no vuela (relleno hasta la cara - 0.06 en el
    triangulo del borde y talud 1:1.6, como mucho 2.5 m) y la hierba no asoma (se bajan lo justo los nodos
    por encima de la cara, como mucho 2.5 m; la berma exterior puede quedar 8 cm bajo el desmonte).
  - D2/E2: bancal con el borde de atras al aire > 0.3 m: se baja si enrasa (aire <= 0.25, tapa <= 0.30 m)
    o se quita con sus olivos.
  - Edificios: el terreno no baja mas de 0.20 m bajo su base (las casas son cascaras: el pie es el de la
    raiz) ni sube mas de 0.10 m junto a ellos; calles y cintas de una cara cuentan con su faldon (0.3 m).
  - CALLE_plazoleta pasa a apoyo y losa maciza (no empieza por 'CALLE_plaza'); si rebajar el terreno haria
    volar las casas de al lado, la plazoleta sube lo justo (<= 0.45 m: jardin elevado un escalon).
  Informe 'terreno_v3' y 'bancales_ajuste'.
Sin bpy.ops salvo abrir/guardar el fichero.
"""
import json
import math
import os
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

BASE = 'E:/Escritorio/claude-pc/arnau-aseto-corsa'
DIR = BASE + '/03_blender'
BLEND = os.environ.get('BLEND', DIR + '/porto_corsa.blend')
GEOM = os.environ.get('GEOM', DIR + '/geometria_3d.json')
OUT = os.environ.get('QA_OUT', DIR + '/renders/qa')
os.makedirs(OUT, exist_ok=True)

Z_RAYO = 400.0          # origen del rayo vertical
Z_FONDO = -60.0         # hasta donde baja el rayo
SALTO_M = 25.0          # salto sospechoso
HOLGURA = 0.02          # el objeto queda 2 cm sobre el impacto
UMBRAL_INFORME = 0.6    # a partir de aqui se cuenta como 'flotaba' / 'estaba enterrado'
DUDOSO_M = 2.0          # desplazamiento que se apunta como dudoso (lo revisa el coordinador)
GAP_APILADO = 3.0       # impactos a menos de esto son una superficie apilada: vale la cima
BAJO_SUP_M = 3.0        # superficie de apoyo a < 3 m por encima de la base = objeto enterrado
# mallas que NO son apoyo del mobiliario pero si cuentan en la comprobacion
# 'bajo superficie': la calzada (nada puede quedar bajo la pista o el pit lane)
# y las penas/cordillera sueltas MONT_* (se van en T7; mientras, nada enterrado en ellas)
CALZADA_PREF = ('PISTA', 'PIT_LANE', 'MONT_')
# hundimiento por familia (negativo = la base entra en el suelo: en ladera un
# tronco a +0.02 ensena hueco por el lado de abajo; el integrador ya los ponia
# ~0.15 m bajo la rejilla). Lo demas queda a HOLGURA sobre el impacto.
HUNDIMIENTO = {'VEG_roca': -0.30, 'VEG_arbusto': -0.10, 'OLI_matorral': -0.10, 'VEG_': -0.15,
               'OLI_': -0.15, 'ITAL_cipreses': -0.15, 'MIRADOR_palmera': -0.15,
               'ITAL_cipres': -0.15, 'ITAL_olivo': -0.15}

# --- superficies de apoyo (nombre exacto o prefijo; mallas de cualquier nivel) ---
# (v1 inspectores: las losas del plan urbano llevan los nombres de urbanismo_escena.camino3d
# -CAMINO_calle/enlace/travesia/rampa/escalera- y CALLE_plaza* (cubre plaza, plaza_fondo,
# plaza_hotel y plazoleta); CAMINO_asfalto/adoquin son las cintas de los senderos del integrador)
SOPORTE_PREF = ('TERRENO', 'TUNEL_acantilado', 'TUNEL_suelo', 'MCOCHE_roca',
                'PPUEBLO_roca', 'PPUEBLO_plaza', 'PPUEBLO_carretera', 'PPUEBLO_escaleras',
                'PPUEBLO_terraza', 'PPUEBLO_cala', 'PPUEBLO_muelle',
                'CAMINO_asfalto', 'CAMINO_adoquin', 'CAMINO_tierra', 'CAMINO_muelle',
                'CAMINO_terraplen', 'CAMINO_calle', 'CAMINO_enlace', 'CAMINO_travesia',
                'CAMINO_rampa', 'CAMINO_escalera', 'CALLE_plaza', 'CALLE_plazoleta', 'ITAL_bancal_tierra',
                'PIT_LANE', 'PIT_suelo', 'ARCEN_', 'ACERA_', 'MIRADOR_paseo')
# losas MACIZAS de cota constante (cara de arriba = corona, fondo = zmin de su caja): todo lo
# que el rayo encuentre entre la corona y el fondo es la misma pila
# (v3: 'CALLE_plazoleta' NO empieza por 'CALLE_plaza' -plazo/plaza-: las plazoletas de urbanismo_escena no
# eran apoyo ni losa maciza aunque v1 las daba por incluidas)
LOSA_PREF = ('CALLE_plaza', 'CALLE_plazoleta')
# hijos de las raices PENON_* que tambien son apoyo salvo que su nombre lleve
# alguna de estas claves (casas, vegetacion, muros, parapetos, farolas, coches, matas...)
PENON_RAICES = ('PENON_cara', 'PENON_puente', 'PENON_lado')
PENON_NO = ('casa', 'veg', 'pino', 'arbol', 'palm', 'muro', 'parapeto', 'balaustr',
            'farola', 'campanile', 'palazzo', 'barca', 'pantalan', 'lancha', 'yate',
            'valla', 'cartel', 'texto', 'fuente', 'banco', 'cipres', 'olivo', 'coche',
            'mata', 'ital_')

# --- familias que se asientan (solo raices) ---
ASENTAR_PREF = ('VEG_', 'OLI_', 'ITAL_', 'CALLE_', 'CARRERA_paca', 'CARRERA_valla',
                'COCHE_', 'CAMINO_cartel', 'CAMINO_valla', 'CAMARA_tierra',
                'MIRADOR_palmera', 'PUERTO_prop', 'PUERTO_banco', 'PUERTO_farola',
                'PUERTO_caseta')
# (ITAL_bancal: su cota la fija el integrador sobre la linea del muro; un rayo en el centro la
# estropearia. Sus olivos se asientan como hijos sueltos y su desnivel va a 'bancales')
ASENTAR_NO = ('CALLE_guirnalda', 'ITAL_ermita', 'YATE', 'LIB', 'CALLE_plaza', 'CALLE_plazoleta',
              'CALLE_toldo_mercado', 'ITAL_bancal')
# --- arboles: 5 rayos (centro + anillo) y, si la ladera es imposible, moverlos o quitarlos ---
ARBOL_PREF = ('VEG_', 'OLI_', 'ITAL_cipres', 'ITAL_olivo')
ARBOL_NO = ('ITAL_cipreses',)
R_ANILLO = 0.6           # radio del anillo de rayos alrededor del tronco
DESNIVEL_MOVER = 0.8     # desnivel en el anillo a partir del cual se intenta mover el arbol
DESNIVEL_MAX = 1.6       # si tras intentarlo sigue por encima: se quita (acantilado/escalon)
PASO_LADERA = 2.0        # desplazamiento de prueba ladera arriba (y luego abajo)
# --- hijos que se asientan uno a uno (hileras y grupos rigidos del italiano_kit) ---
GRUPO_HIJOS_PREF = ('ITAL_cipreses', 'ITAL_bancal', 'ITAL_ermita')
HIJO_ARBOL_PREF = ('ITAL_cipres', 'ITAL_olivo')
# --- obstaculos para el tronco de los arboles (N3: palmera saliendo de un muro) ---
# (v2, A-r2-11: CAMINO_terraplen, el relleno bajo las calzadas con rasante propia, es obstaculo y no
# apoyo de los arboles: un olivo en su cara metia la copa en la subida al hotel)
OBST_PREF = ('CAMINO_muro', 'MIRADOR_muro', 'MUROC_', 'ITAL_bancal_muro', 'CAMINO_terraplen')
NO_APOYO_ARBOL = ('CAMINO_terraplen',)
OBST_RAICES = ('CASAS_', 'PUEBLO_', 'CIVICO_', 'HOTEL_root', 'AYTO_root', 'CAMPANILE_root',
               'CASINO_root', 'ITAL_ermita', 'ITAL_capitella', 'ITAL_pergola', 'CARRERA_tribuna',
               'PIT_boxes', 'PIT_torre')
OBST_PENON = ('casa', 'palazzo', 'campanile', 'muro')
OBST_NO = ('VEG_', 'OLI_', 'ITAL_cipres', 'ITAL_olivo')
OFF_TRONCO = 0.3         # rayos en el tronco y a +-0.3 m
SEPARAR_M = (1.5, 3.0)   # distancias de prueba para sacar el arbol del muro
# --- edificios: solo informe por esquinas ---
EDIFICIO_PREF = ('CASAS_', 'PENON_casa', 'PUEBLO_', 'CIVICO_', 'HOTEL_root', 'AYTO_root',
                 'CAMPANILE_root', 'CASINO_root', 'PENON_campanile', 'PENON_palazzo',
                 'ITAL_ermita', 'CARRERA_tribuna', 'CARRERA_boxes', 'PIT_boxes', 'PIT_torre',
                 'CARRERA_pantalla', 'CARRERA_portico', 'MIRADOR_parking', 'LOEWS_rotonda')
# --- solo informe de desnivel, sin mover (las penas sueltas se van en T7) ---
INFORME_PREF = ('MONT_pena',)


def log(msg):
    print('[asentar] ' + str(msg))


t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
LIBc = bpy.data.collections.get('LIB')
EN_LIB = set(o.name for o in LIBc.all_objects) if LIBc else set()
G = json.load(open(GEOM, encoding='utf-8'))
NIVEL_MAR = float(G.get('nivel_mar', 0.0))
S = G['muestras']
T = G['terreno']
# ronda 15: el integrador talla EXPLANADAS en la malla TERRENO (tribunas, hotel, ayuntamiento,
# plazuelas): la cota real es la de la malla, no la del JSON
_ter_m = bpy.data.objects.get('TERRENO')
if _ter_m is not None and _ter_m.type == 'MESH' and len(_ter_m.data.vertices) == T['nx'] * T['ny']:
    _co = [0.0] * (3 * len(_ter_m.data.vertices))
    _ter_m.data.vertices.foreach_get('co', _co)
    T = dict(T)
    T['z'] = _co[2::3]
KD_PISTA = KDTree(len(S))
for _i, _q in enumerate(S):
    KD_PISTA.insert(Vector((_q['x'], _q['y'], 0.0)), _i)
KD_PISTA.balance()


def pista_cerca(x, y):
    """(z de la calzada, distancia al eje, ancho) de la muestra mas cercana."""
    _co, i, d = KD_PISTA.find(Vector((x, y, 0.0)))
    return S[i]['z'], d, S[i]['w']


def dentro_terreno(x, y):
    return (T['x0'] <= x <= T['x0'] + (T['nx'] - 1) * T['cell']
            and T['y0'] <= y <= T['y0'] + (T['ny'] - 1) * T['cell'])


def hundimiento(nombre):
    for k in sorted(HUNDIMIENTO, key=len, reverse=True):
        if nombre.startswith(k):
            return HUNDIMIENTO[k]
    return HOLGURA


def en_escena(ob):
    return ob.name not in EN_LIB


def empieza(nombre, prefijos):
    return any(nombre.startswith(p) for p in prefijos)


def raiz_de(ob):
    while ob.parent is not None:
        ob = ob.parent
    return ob


def es_soporte(ob):
    if ob.type != 'MESH' or not en_escena(ob):
        return False
    if empieza(ob.name, SOPORTE_PREF):
        return True
    r = raiz_de(ob)
    if r is not ob and empieza(r.name, PENON_RAICES):
        n = ob.name.lower()
        return not any(k in n for k in PENON_NO)
    return False


# ---------------------------------------------------------------- BVH de apoyo
def malla_mundo(ob, dg):
    """(vertices Nx3 en mundo, triangulos Mx3) de la malla evaluada, triangulada
    IGUAL que el render y el exportador (loop_triangles: los quads se parten por
    la diagonal 0-2). FromPolygons(all_triangles=False) partia los quads no planos
    del TERRENO por la otra diagonal: en laderas, hasta metros de diferencia."""
    ob_e = ob.evaluated_get(dg)
    me = ob_e.data
    n = len(me.vertices)
    if n == 0 or len(me.polygons) == 0:
        return None, None
    co = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    mw = ob_e.matrix_world
    R = np.array([[mw[i][j] for j in range(3)] for i in range(3)])
    t = np.array([mw[0][3], mw[1][3], mw[2][3]])
    co = co @ R.T + t
    try:
        me.calc_loop_triangles()
    except Exception:
        pass          # (en Blender 4+ los loop_triangles se calculan solos al pedirlos)
    nt = len(me.loop_triangles)
    if nt == 0:
        return None, None
    tri = np.empty(nt * 3, dtype=np.int64)
    me.loop_triangles.foreach_get('vertices', tri)
    return co, tri.reshape(-1, 3)


def construir_bvh(filtro=es_soporte, etiqueta='apoyo'):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, rangos = [], [], []
    off, p0 = 0, 0
    for ob in bpy.data.objects:
        if not filtro(ob):
            continue
        co, pl = malla_mundo(ob, dg)
        if co is None:
            continue
        verts.append(co)
        polys.append(pl + off)
        rangos.append((p0, p0 + len(pl), ob.name))
        p0 += len(pl)
        off += len(co)
    V = np.concatenate(verts) if verts else np.zeros((0, 3))
    P = np.concatenate(polys) if polys else np.zeros((0, 3), dtype=np.int64)
    log('BVH de %s: %d mallas, %d vertices, %d triangulos' % (etiqueta, len(rangos), len(V), len(P)))
    # triangulos ya hechos (los del render): all_triangles=True para que no se vuelvan a partir
    bvh = BVHTree.FromPolygons(V.tolist(), P.tolist(), all_triangles=True)
    return bvh, rangos


# ---------------------------------------------------------------- losas CALLE_plaza* (v2, G2-09)
LOSA_BAJO_TERRENO = 0.15   # el fondo de la losa queda 0.15 m bajo el terreno en todo su borde
LOSA_CANTO_TOPE = 3.0      # ...pero no se baja por debajo de corona - 3 m (sobre un hueco real: aviso)
PASO_ARISTA = 0.25         # muestreo del terreno a lo largo de cada arista del fondo


def z_ter_tri(x, y):
    """Cota del TERRENO que SE VE en (x, y): triangulos del render (diagonal a -> a+nx+1). None fuera."""
    fx = (x - T['x0']) / T['cell']
    fy = (y - T['y0']) / T['cell']
    if not (0.0 <= fx <= T['nx'] - 1 and 0.0 <= fy <= T['ny'] - 1):
        return None
    i0 = min(T['nx'] - 2, int(fx))
    j0 = min(T['ny'] - 2, int(fy))
    tx, ty = fx - i0, fy - j0
    nxx = T['nx']
    z00, z10 = T['z'][j0 * nxx + i0], T['z'][j0 * nxx + i0 + 1]
    z01, z11 = T['z'][(j0 + 1) * nxx + i0], T['z'][(j0 + 1) * nxx + i0 + 1]
    if tx >= ty:
        return z00 + (z10 - z00) * tx + (z11 - z10) * ty
    return z00 + (z01 - z00) * ty + (z11 - z01) * tx


def _muestras_arista(p, q):
    n = max(1, int(math.ceil(math.hypot(q.x - p.x, q.y - p.y) / PASO_ARISTA)))
    return [k / float(n) for k in range(n + 1)]


def aire_fondo(cw, zf, aristas):
    """Aire maximo (m) entre el fondo de la losa (z del fondo zf[i]) y el terreno a lo largo de las
    aristas del anillo de fondo (positivo = el terreno queda por debajo del fondo)."""
    peor = -1e9
    for i, j in aristas:
        for t in _muestras_arista(cw[i], cw[j]):
            zt = z_ter_tri(cw[i].x + (cw[j].x - cw[i].x) * t, cw[i].y + (cw[j].y - cw[i].y) * t)
            if zt is not None:
                peor = max(peor, zf[i] + (zf[j] - zf[i]) * t - zt)
    return peor


def ajustar_losas():
    """urbanismo_escena/integrar dan a cada CALLE_plaza* un canto calculado con el terreno de ANTES
    de las explanadas y del despeje del integrador: en la escena final el borde de abajo puede
    quedar al aire (G2-09: 0.45 m bajo CALLE_plaza_fondo.007). Con el TERRENO definitivo, cada
    vertice del anillo de FONDO (el mas bajo de su columna: misma planta que uno de la cara de
    arriba) baja a min(terreno a lo largo de sus dos aristas del fondo) - LOSA_BAJO_TERRENO. Solo
    baja (lo que ya va enterrado se queda) y nunca por debajo de corona - LOSA_CANTO_TOPE."""
    res = []
    for ob in list(scene.collection.all_objects):
        if ob.type != 'MESH' or not en_escena(ob) or not empieza(ob.name, LOSA_PREF) or len(ob.data.vertices) < 6:
            continue
        me = ob.data
        if me.users > 1:
            ob.data = me = me.copy()
        mw = ob.matrix_world.copy()
        cw = [mw @ v.co for v in me.vertices]
        corona = max(c.z for c in cw)
        col = {}
        for i, c in enumerate(cw):
            col.setdefault((round(c.x, 2), round(c.y, 2)), []).append(i)
        fondo = {}
        for ids in col.values():
            if len(ids) >= 2:
                i = min(ids, key=lambda k: cw[k].z)
                if cw[i].z < max(cw[k].z for k in ids) - 0.05:
                    fondo[i] = []
        aristas = []
        for e in me.edges:
            a_, b_ = e.vertices
            if a_ in fondo and b_ in fondo:
                fondo[a_].append(b_)
                fondo[b_].append(a_)
                aristas.append((a_, b_))
        if not aristas:
            continue
        zf = {i: cw[i].z for i in fondo}
        aire0 = aire_fondo(cw, zf, aristas)
        nuevos = {}
        for i, vec in fondo.items():
            zt = [z_ter_tri(cw[i].x, cw[i].y)]
            for j in vec:
                zt += [z_ter_tri(cw[i].x + (cw[j].x - cw[i].x) * t, cw[i].y + (cw[j].y - cw[i].y) * t)
                       for t in _muestras_arista(cw[i], cw[j])]
            zt = [z for z in zt if z is not None]
            if not zt:
                continue
            z_new = min(cw[i].z, max(min(zt) - LOSA_BAJO_TERRENO, corona - LOSA_CANTO_TOPE))
            if z_new < cw[i].z - 0.005:
                nuevos[i] = z_new
        if not nuevos:
            continue
        inv = mw.inverted()
        for i, z in nuevos.items():
            me.vertices[i].co = inv @ Vector((cw[i].x, cw[i].y, z))
            zf[i] = z
        me.update()
        aire1 = aire_fondo(cw, zf, aristas)
        res.append({'nombre': ob.name, 'vertices_bajados': len(nuevos), 'de_fondo': len(fondo),
                    'max_bajada': round(max(cw[i].z - z for i, z in nuevos.items()), 2),
                    'aire_antes': round(aire0, 2), 'aire_despues': round(aire1, 2),
                    'canto_max': round(corona - min(zf.values()), 2), 'queda_aire': aire1 > 0.1})
    return res


# ---------------------------------------------------------------- v3 inspectores: garantias de TERRENO
# (C-12, N1, D2) Lo ultimo que toca el TERRENO, antes de las losas y del BVH: (1) ninguna hierba sobre
# las losas CALLE_plaza*/CALLE_plazoleta*, (2) senderos de tierra (CAMINO_tierra) sin canto al aire ni
# hierba encima, (3) bancales de olivos con el borde de atras enrasado con la ladera. Solo se mueven
# NODOS de la rejilla (mismos vertices j*nx+i y triangulacion a -> a+nx+1 que el render y el kn5),
# nunca en el mar, nunca rellenando a < TER_PISTA_LIBRE m del borde del asfalto ni rebajando bajo el
# pasillo de la pista (como integrar._proteger_pista), y limitado por lo que hay alrededor (casas,
# muros, losas, calles, rocas, calzadas: BVH 'protegidos'); lo que asentar vuelve a posar despues
# (arboles, mobiliario, coches, carteles) no limita. Si un integrador ya lo hizo bien, no toca nada.
import bisect
TER_PISTA_LIBRE = 6.0      # ningun relleno a menos de esto del borde del asfalto
ABAJO_V = Vector((0.0, 0.0, -1.0))
TER_OB = bpy.data.objects.get('TERRENO')
TER_OK = (TER_OB is not None and TER_OB.type == 'MESH' and TER_OB.data.users == 1
          and len(TER_OB.data.vertices) == T['nx'] * T['ny'] and isinstance(T['z'], list)
          and all(abs(TER_OB.matrix_world[i][j] - (1.0 if i == j else 0.0)) < 1e-6 for i in range(4) for j in range(4)))
MAR_T = T.get('mar') or []
TOCADOS = {}               # nodo -> cota original (informe)
LIMITE_QUIEN = {}          # nodo -> (objeto que limita la subida, objeto que limita la bajada) (informe)
PROT_NO = ('TERRENO', 'CAMINO_tierra', 'AGUA', 'LIB')
# sondas alrededor de un nodo: rejilla de 0.5 m (desfasada 0.25 m: comun a todos los nodos, se cachea) en
# su celda de 4 m a cada lado. Un cambio dz del nodo mueve el terreno de la sonda w * dz, con w = peso
# baricentrico del nodo en el triangulo de la sonda (0 fuera de sus 6 triangulos): limite / w
SONDAS = [(0.0, 0.0)] + [(-3.75 + 0.5 * a, -3.75 + 0.5 * b) for a in range(16) for b in range(16)]


def _movil(r):
    """Raiz que asentar vuelve a posar despues (arboles, mobiliario, coches, carteles): no protege."""
    n = r.name
    if empieza(n, EDIFICIO_PREF) or any(k in n for k in ASENTAR_NO):
        return False
    return empieza(n, ASENTAR_PREF) or empieza(n, ARBOL_PREF)


def es_protegido(ob):
    if ob.type != 'MESH' or not en_escena(ob) or empieza(ob.name, PROT_NO) or empieza(ob.name, OBST_NO):
        return False
    return not _movil(raiz_de(ob))


if TER_OK:
    BVH_PROT, RANGOS_PROT = construir_bvh(es_protegido, 'protegidos (v3, garantias de terreno)')
    _ini_prot = [r[0] for r in RANGOS_PROT]
else:
    BVH_PROT, RANGOS_PROT, _ini_prot = None, [], []
    log('AVISO v3: TERRENO no editable (falta, compartido o con transformacion): sin garantias de terreno')


def _nombre_prot(idx):
    k = bisect.bisect_right(_ini_prot, idx) - 1
    return RANGOS_PROT[k][2] if 0 <= k < len(RANGOS_PROT) else '?'


# las casas y edificios son cascaras (fachadas verticales + tejado): un rayo vertical dentro de la huella
# solo toca el tejado o un forjado y parecerian un voladizo. Cualquier malla de un edificio usa como pie la
# BASE de su raiz (origen = centro de la base): el terreno de alrededor no puede bajar de ahi
EDIF_HUECO = 0.20          # el terreno puede quedar como mucho 0.20 m bajo la base de un edificio (revisores: +-0.38)
PIE_EDIF = {}
for _r in RANGOS_PROT:
    _o = bpy.data.objects.get(_r[2])
    _rz = raiz_de(_o) if _o is not None else None
    if _rz is not None and empieza(_rz.name, EDIFICIO_PREF + OBST_RAICES):
        PIE_EDIF[_r[2]] = float(_rz.matrix_world.translation.z)


_COL_PROT = {}


def columna_prot(x, y):
    """{objeto protegido: (z mas baja, z mas alta, impactos)} de un rayo vertical en (x, y)."""
    key = (round(x, 1), round(y, 1))
    if key in _COL_PROT:
        return _COL_PROT[key]
    objs = {}
    z = Z_RAYO
    for _ in range(40):
        loc, _n, idx, _d = BVH_PROT.ray_cast(Vector((x, y, z)), ABAJO_V, z - Z_FONDO)
        if loc is None:
            break
        nm = _nombre_prot(idx)
        zb, za, nh = objs.get(nm, (loc.z, loc.z, 0))
        objs[nm] = (min(zb, loc.z), max(za, loc.z), nh + 1)
        z = loc.z - 0.02
        if z <= Z_FONDO:
            break
    _COL_PROT[key] = objs
    return objs


def nodo_xy(k):
    return T['x0'] + (k % T['nx']) * T['cell'], T['y0'] + (k // T['nx']) * T['cell']


def tri_nodos(x, y):
    """(nodos, pesos) del triangulo del render (diagonal a -> a+nx+1) que contiene (x, y), o None."""
    nx_, c_ = T['nx'], T['cell']
    fx, fy = (x - T['x0']) / c_, (y - T['y0']) / c_
    if not (0.0 <= fx <= nx_ - 1 and 0.0 <= fy <= T['ny'] - 1):
        return None
    i = min(nx_ - 2, int(fx))
    j = min(T['ny'] - 2, int(fy))
    u, v = fx - i, fy - j
    a = j * nx_ + i
    if u >= v:
        return (a, a + 1, a + nx_ + 1), (1.0 - u, u - v, v)
    return (a, a + nx_ + 1, a + nx_), (1.0 - v, u, v - u)


def limites_nodo(k, excluir=()):
    """(subida_max, bajada_max) del nodo k por los objetos protegidos de las sondas de alrededor:
    - apoyado en el suelo (pie a <= 0.3 m sobre el terreno): subir como mucho 0.10 m (no enterrar
      fachadas ni muros) y bajar como mucho hasta 5 cm bajo su pie (EDIF_HUECO bajo la base de un
      edificio) (no dejarlo al aire); un edificio que ya vuela no deja bajar nada;
    - por encima del suelo (puente, guirnalda, voladizo): subir hasta 0.10 m bajo su pie;
    - enterrado entero (cimientos): no cuenta. Cada limite se divide por el peso del nodo en la sonda
      (se aplica nodo a nodo con el terreno ya cambiado: los nodos vecinos no suman de mas)."""
    x, y = nodo_xy(k)
    up, down = [1e9, None], [1e9, None]
    for dx, dy in SONDAS:
        tn = tri_nodos(x + dx, y + dy)
        if tn is None or k not in tn[0]:
            continue
        w = tn[1][tn[0].index(k)]
        if w < 0.04:
            continue
        objs = columna_prot(x + dx, y + dy)
        if not objs:
            continue
        zt = sum(T['z'][a_] * b_ for a_, b_ in zip(*tn))
        for nm, (zb, za, nh) in objs.items():
            if nm in excluir or (za < zt - 0.05 and nm not in PIE_EDIF):
                continue
            if nm in PIE_EDIF:
                zb = min(zb, PIE_EDIF[nm])     # (un edificio siempre esta en el suelo, aunque ya vuele)
                suelo = True
            else:
                if nh == 1:
                    zb = za - 0.30     # (una sola cara: cinta abierta -calle, arcen- con su faldon de ~0.35 m)
                suelo = zb <= zt + 0.3
            u_ = max(0.0, zb - 0.1 - zt) / w if zb > zt + 0.3 else 0.10 / w
            if u_ < up[0]:
                up = [u_, nm]
            if suelo:
                d_ = max(0.0, zt - (zb - (EDIF_HUECO if nm in PIE_EDIF else 0.05))) / w
                if d_ < down[0]:
                    down = [d_, nm]
    LIMITE_QUIEN[k] = (up[1], down[1])
    return up[0], down[0]


def limite_pista(k, z, z_new):
    """integrar._proteger_pista: nada de relleno a < TER_PISTA_LIBRE m del borde del asfalto y nunca por
    debajo del pasillo de la pista (eje - 0.6 y talud 0.55 mas alla de 6 m) a menos de 12 m."""
    x, y = nodo_xy(k)
    zp, d, w = pista_cerca(x, y)
    d -= w / 2.0
    if z_new > z and d < TER_PISTA_LIBRE:
        return z
    if d < 12.0:
        z_lim = zp - 0.6 - max(0.0, d - 6.0) * 0.55
        if z_new < z_lim:
            z_new = max(z_new, min(z, z_lim))
    return z_new


def aplicar_nodos(mods, excluir=(), bloqueos=None):
    """Escribe {nodo: cota objetivo} en T y en la malla TERRENO con todos los limites. -> nodos cambiados.
    bloqueos (dict): nombre del objeto protegido (o 'pista'/'mar') que impidio llegar al objetivo -> veces."""
    n = 0
    for k, zo in mods.items():
        z = T['z'][k]
        if MAR_T and MAR_T[k] and z < 0.5:
            if bloqueos is not None:
                bloqueos['mar'] = bloqueos.get('mar', 0) + 1
            continue
        zn = limite_pista(k, z, zo)
        if bloqueos is not None and abs(zn - zo) > 0.02:
            bloqueos['pista'] = bloqueos.get('pista', 0) + 1
        if abs(zn - z) < 0.005:
            continue
        up, down = limites_nodo(k, excluir)
        zl = min(zn, z + up) if zn > z else max(zn, z - down)
        if bloqueos is not None and abs(zl - zn) > 0.02:
            q = LIMITE_QUIEN.get(k, (None, None))[0 if zn > z else 1] or '?'
            q = q.split('.')[0]
            bloqueos[q] = bloqueos.get(q, 0) + 1
        zn = zl
        if abs(zn - z) < 0.005:
            continue
        TOCADOS.setdefault(k, z)
        T['z'][k] = zn
        TER_OB.data.vertices[k].co.z = zn
        n += 1
    return n


# --- (1) C-12/C-08: hierba sobre las losas. urbanismo_escena pone CALLE_plaza/plazoleta/plaza_fondo a su
# cota con canto hasta el terreno pero nunca rebaja el terreno de debajo (garantia_losa del integrador solo
# va en sus plazas): CALLE_plaza (-510, 487) tenia 185 de 215 puntos bajo la hierba (hasta 0.34 m) y las
# plazoletas hasta 0.43 m. Como integrar._garantia_losa: donde el terreno pasa de corona - 0.05 (dentro
# de la losa, a >= LOSA_TER_MARGEN m del borde) se bajan los nodos de su triangulo que sobran, lo justo ---
LOSA_TER_PREF = ('CALLE_plaza', 'CALLE_plazoleta')
LOSA_TER_HOLGURA = 0.05
LOSA_TER_MARGEN = 0.5      # se mira la losa a >= 0.5 m de su borde (en el borde de una losa tallada sube el talud)
LOSA_TER_BAJADA_MAX = 1.5  # desmonte maximo de un nodo por una losa


def cara_corona(ob):
    """(corona, [(x, y)] de la cara de arriba): la cara con mas vertices, todos a la corona."""
    mw = ob.matrix_world
    cw = [mw @ v.co for v in ob.data.vertices]
    if not cw:
        return None, []
    corona = max(c.z for c in cw)
    mejor = []
    for p in ob.data.polygons:
        vs = [cw[i] for i in p.vertices]
        if len(vs) > len(mejor) and all(v.z > corona - 0.02 for v in vs):
            mejor = vs
    return corona, [(v.x, v.y) for v in mejor]


def dentro_poly(px, py, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def d_poly(px, py, poly):
    best = 1e9
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy
        f = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / l2))
        best = min(best, math.hypot(px - ax - vx * f, py - ay - vy * f))
    return best


def puntos_losa(poly, margen, paso=0.5):
    """Rejilla de `paso` m (desfasada medio paso) DENTRO de la losa y a >= `margen` m de su borde: [(x, y)]."""
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    res = []
    x = min(xs) + paso / 2.0
    while x < max(xs):
        y = min(ys) + paso / 2.0
        while y < max(ys):
            if dentro_poly(x, y, poly) and (margen <= 0.0 or d_poly(x, y, poly) >= margen):
                res.append((x, y))
            y += paso
        x += paso
    return res


def garantia_losas_terreno(etiqueta):
    """Hierba sobre la losa: en los puntos a >= LOSA_TER_MARGEN m dentro de su borde, el terreno no pasa de
    corona - LOSA_TER_HOLGURA. Se bajan solo los nodos del triangulo que estan por encima (lo justo, repartido;
    si no basta, los 3) y nunca mas de LOSA_TER_BAJADA_MAX respecto a su cota de partida: junto al borde de una
    losa tallada en un talud el terreno sube, y bajarlo ahi abria zanjas de 4 m (CALLE_plaza_hotel)."""
    res = []
    for ob in list(scene.collection.all_objects):
        if ob.type != 'MESH' or not en_escena(ob) or not empieza(ob.name, LOSA_TER_PREF):
            continue
        corona, poly = cara_corona(ob)
        if corona is None or len(poly) < 3:
            continue
        pts = puntos_losa(poly, LOSA_TER_MARGEN)
        obj = corona - LOSA_TER_HOLGURA

        def hierba():
            zs = [z_ter_tri(x, y) for (x, y) in pts]
            zs = [z for z in zs if z is not None]
            return (max(zs) - corona if zs else -1e9), sum(1 for z in zs if z > corona + 0.02), len(zs)
        h0, n0, n_in = hierba()
        if h0 <= -LOSA_TER_HOLGURA:
            continue
        n_mod = 0
        bloq = {}
        for _it in range(4):
            mods = {}
            for (x, y) in pts:
                tn = tri_nodos(x, y)
                if tn is None:
                    continue
                zt = sum(T['z'][k] * w for k, w in zip(*tn))
                d = zt - (obj - 0.02)
                if zt <= obj or d <= 0.0:
                    continue
                culp = [(k, w, T['z'][k] - (obj - 0.02)) for k, w in zip(*tn) if T['z'][k] > obj - 0.02 + 0.005]
                cap = sum(w * s_ for _k, w, s_ in culp)
                f = min(1.0, d / cap) if cap > 1e-6 else 0.0
                resto = max(0.0, d - f * cap)
                for k, w in zip(*tn):
                    baja = next((f * c[2] for c in culp if c[0] == k), 0.0) + resto
                    if baja > 0.0:
                        zk = max(T['z'][k] - baja - 0.005, TOCADOS.get(k, T['z'][k]) - LOSA_TER_BAJADA_MAX)
                        mods[k] = min(mods.get(k, 1e9), zk)
            n_it = aplicar_nodos(mods, excluir={ob.name}, bloqueos=bloq) if mods else 0
            n_mod += n_it
            if n_it == 0:
                break
        h1, n1, _n = hierba()
        if n_mod or n0:
            res.append({'nombre': ob.name, 'pasada': etiqueta, 'corona': round(corona, 2), 'puntos': n_in,
                        'hierba_antes': [n0, round(h0, 2)], 'hierba_despues': [n1, round(h1, 2)], 'nodos': n_mod,
                        'limitado_por': dict(sorted(bloq.items(), key=lambda kv: -kv[1])[:4])})
    return res


# (1b) Plazoletas (jardin de un solar entre dos casas) que siguen bajo la hierba porque rebajar el terreno haria
# volar las casas de al lado (estan a la cota del terreno, 0.3-0.6 m por encima de la losa del plan): la losa
# SUBE lo justo (hierba maxima + 5 cm, como mucho PLAZOLETA_SUBIDA_MAX), un jardin elevado un escalon sobre la
# acera. Las plazas con fuente (CALLE_plaza*) no: las calles llegan a su cota.
PLAZOLETA_PREF = ('CALLE_plazoleta',)
PLAZOLETA_SUBIDA_MAX = 0.45


def subir_plazoletas():
    res = []
    for ob in list(scene.collection.all_objects):
        if ob.type != 'MESH' or not en_escena(ob) or not empieza(ob.name, PLAZOLETA_PREF):
            continue
        corona, poly = cara_corona(ob)
        if corona is None or len(poly) < 3:
            continue
        zs = [z_ter_tri(x, y) for (x, y) in puntos_losa(poly, LOSA_TER_MARGEN, 0.25)]
        zs = [z for z in zs if z is not None]
        if not zs or max(zs) - corona <= 0.02:
            continue
        d = min(PLAZOLETA_SUBIDA_MAX, max(zs) - corona + 0.05)
        ob.location.z += d
        res.append({'nombre': ob.name, 'corona': round(corona, 2), 'subida': round(d, 2),
                    'hierba_antes': round(max(zs) - corona, 2), 'hierba_despues': round(max(zs) - corona - d, 2)})
    return res


# --- (3) D2/E2: bancales de olivos (italiano_kit.build_bancal: muro en y=0 cara a +Y, relleno hasta y=-fondo
# a z=alto). El integrador fija la corona con el punto MAS ALTO del borde de atras (bilineal): en una ladera
# del 48-76 % el relleno quedaba hasta 1.46 m al aire por detras (ITAL_bancal.001), una jardinera puesta
# encima de la ladera. La rejilla de 4 m no puede rellenar detras de un bancal de 3.5 m de fondo sin
# enterrar el muro, asi que: si el borde de atras (9 puntos) vuela > BANC_AIRE_MAX, se BAJA el bancal
# hasta dejar BANC_AIRE_OBJ en el punto peor, si con eso el terreno no tapa la corona mas de BANC_TAPA_MAX
# en el otro extremo y el muro sigue asomando BANC_MURO_MIN delante; si no, se QUITA (con sus olivos) ---
BANC_AIRE_MAX = 0.30
BANC_AIRE_OBJ = 0.25
BANC_TAPA_MAX = 0.30
BANC_MURO_MIN = 0.6


def ajustar_bancales():
    res = []
    for ob in [o for o in scene.collection.all_objects
               if o.parent is None and en_escena(o) and o.name.startswith('ITAL_bancal')]:
        L_, A_, F_ = float(ob.get('largo', 30.0)), float(ob.get('alto', 1.6)), float(ob.get('fondo', 7.0))
        mw = ob.matrix_world.copy()
        corona = (mw @ Vector((0.0, 0.0, A_))).z
        lxs = [-L_ / 2.0 + 0.4 + (L_ - 0.8) * k / 8.0 for k in range(9)]
        atras, frente = [], []
        for lx in lxs:
            e = mw @ Vector((lx, -F_, A_))
            zt = z_ter_tri(e.x, e.y)
            if zt is not None:
                atras.append(corona - zt)
            for ly in (0.3, 1.0):
                e = mw @ Vector((lx, ly, 0.0))
                zt = z_ter_tri(e.x, e.y)
                if zt is not None:
                    frente.append(zt)
        if not atras or not frente:
            continue
        a_max, a_min = max(atras), min(atras)
        reg = {'nombre': ob.name, 'x': round(mw.translation.x, 2), 'y': round(mw.translation.y, 2),
               'corona': round(corona, 2), 'aire_atras': [round(a, 2) for a in atras],
               'muro_visto_min': round(corona - max(frente), 2)}
        if a_max <= BANC_AIRE_MAX:
            continue
        d = a_max - BANC_AIRE_OBJ
        if a_min - d < -BANC_TAPA_MAX:
            reg['accion'] = ('quitado: el borde de atras va de %.2f a %.2f m de aire (%.2f m de desnivel a lo largo del '
                             'bancal; enrasarlo enterraria %.2f m la otra punta)' % (a_min, a_max, a_max - a_min, d - a_min))
        elif corona - d - max(frente) < BANC_MURO_MIN:
            reg['accion'] = 'quitado: bajado %.2f m el muro solo asomaria %.2f m' % (d, corona - d - max(frente))
        else:
            ob.location.z -= d
            reg['accion'] = 'bajado %.2f m (aire atras %.2f..%.2f -> %.2f..%.2f)' % (d, a_min, a_max, a_min - d, a_max - d)
        if reg['accion'].startswith('quitado'):
            for ch in list(ob.children_recursive):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(ob, do_unlink=True)
        res.append(reg)
    return res


# --- (2) N1/E4: senderos de tierra LEVANTADOS como losas. integrar._tallar_sendero deja la pisada a
# eje - 0.15 en los nodos a < 2.8 m y su garantia solo sube los nodos hasta pisada - 0.35 cuando el borde
# vuela > 0.4 m: con la rejilla de 4 m el eje quedaba 0.47 m (mediana) sobre el terreno y el borde hasta
# 5.8 m, tapado por el canto vertical de 1 m de la cinta. Aqui, sobre la cinta REAL (anillos de perfil del
# caminos_kit: vertices de arriba 1..stride-2, bordes 1 y stride-2), cada 0.6 m:
#  - subir: punto de borde con aire > SEND_TOL (y sin terraplen/muro/losa protegida debajo) -> los nodos de
#    su triangulo (a <= 5.7 m) hasta el plano de la cinta - SEND_OBJ (hombro llano); puntos de talud a
#    SEND_ANILLOS m fuera del borde -> sus nodos en talud SEND_TALUD (1:1.6) desde el borde; relleno de un
#    nodo como mucho SEND_SUBIDA_MAX (si faltan > SEND_SUBIDA_LIMITE es una horquilla: no se rellena);
#  - bajar: punto de la cara con el terreno a < SEND_HIERBA bajo ella (la berma exterior: > SEND_BORDE_TAPA
#    sobre ella) -> el exceso se reparte entre los nodos de su triangulo que estan por encima del plano (si
#    no basta, el resto los 3): bajar no vuelve a hundir el lado de cuesta abajo; como mucho SEND_BAJADA_MAX.
#    4 vueltas subir/bajar y una ultima de bajar (nunca hierba encima).
# El plano de la cinta en un nodo = cota del eje del frame + pendiente * avance + la cota mas baja del perfil
# a +-1 m de su lateral (fuera de la cinta, la mas baja del perfil), con el frame de la MISMA rama (+-4 del
# punto) mas cercano al nodo: en una horquilla cada condicion mira su rama ---
SEND_PREF = ('CAMINO_tierra',)
SEND_OBJ = 0.06
SEND_TOL = 0.12
SEND_HIERBA = 0.05
SEND_BORDE_TAPA = 0.08     # el borde exterior de la cinta (berma) puede quedar hasta 8 cm bajo el talud de desmonte
SEND_TALUD = 0.6
SEND_ANILLOS = (1.0, 2.0, 3.0)
SEND_SUBIDA_MAX = 2.5      # relleno maximo de un nodo (se rellena hasta aqui aunque falte)
SEND_SUBIDA_LIMITE = 4.0   # si falta mas que esto es una horquilla de ramas pegadas: esa condicion no rellena
SEND_BAJADA_MAX = 2.5      # desmonte maximo de un nodo respecto a su cota de partida
SEND_APOYO = 0.45          # terraplen/muro/losa protegida a menos de esto bajo el borde: ya tiene apoyo


def anillos_cinta(ob):
    """Anillos de perfil (n_frames x stride x 3, mundo) de una cinta del caminos_kit, o None."""
    me = ob.data
    if len(me.polygons) < 2:
        return None
    f0 = tuple(me.polygons[0].vertices)
    if len(f0) != 4:
        return None
    st = f0[1] - f0[0]
    if st < 5 or f0[3] != f0[0] + 1 or f0[2] != f0[1] + 1:
        return None
    n_max = 0
    for p in me.polygons:
        v = tuple(p.vertices)
        if len(v) != 4 or v[1] - v[0] != st or v[3] != v[0] + 1 or v[2] != v[1] + 1:
            break
        n_max = max(n_max, v[2] + 1)
    nf = n_max // st
    if nf < 2:
        return None
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)[:nf * st]
    mw = ob.matrix_world
    R = np.array([[mw[i][j] for j in range(3)] for i in range(3)])
    t = np.array([mw[0][3], mw[1][3], mw[2][3]])
    return (co @ R.T + t).reshape(nf, st, 3)


def frames_cinta(arr):
    """Por frame: (ax, ay, az, tx, ty, nx, ny, pendiente, lats, dzs) con el perfil de arriba ordenado."""
    nf, st, _ = arr.shape
    c = st // 2
    res = []
    for f in range(nf):
        a, b = arr[max(0, f - 1), c], arr[min(nf - 1, f + 1), c]
        tx, ty = b[0] - a[0], b[1] - a[1]
        hl = math.hypot(tx, ty) or 1.0
        tx, ty = tx / hl, ty / hl
        nx_, ny_ = -ty, tx
        A = arr[f, c]
        top = arr[f, 1:st - 1]
        lats = (top[:, 0] - A[0]) * nx_ + (top[:, 1] - A[1]) * ny_
        o = np.argsort(lats)
        dzs = (top[o, 2] - A[2]).astype(float)
        res.append((float(A[0]), float(A[1]), float(A[2]), float(tx), float(ty), float(nx_), float(ny_), float(b[2] - a[2]) / hl,
                    lats[o].astype(float), dzs, float(dzs.min())))
    return res


def plano_cinta(fr, x, y):
    """(cota de referencia de la cara de arriba en (x, y), distancia fuera del borde) segun el frame fr: eje +
    pendiente * avance + la cota MAS BAJA del perfil a +-1 m de su lateral (fuera de la cinta, la mas baja de
    todo el perfil). Un plano de 4 m no sigue la berma (+0.05) junto al bombeo de la pisada (-0.04): con la
    cota de la berma el nodo subido hacia asomar la hierba en la pisada de al lado y la bajada lo volvia a
    hundir (el borde quedaba a 0.2 m)."""
    ax, ay, az, tx, ty, nx_, ny_, g, lats, dzs, dz_min = fr
    dx, dy = x - ax, y - ay
    la = dx * nx_ + dy * ny_
    fuera = max(0.0, la - lats[-1], lats[0] - la)
    if fuera > 0.0:
        dz = dz_min
    else:
        cerca = dzs[np.abs(lats - la) <= 1.0]
        dz = float(cerca.min()) if len(cerca) else float(np.interp(la, lats, dzs))
    return az + g * (dx * tx + dy * ty) + dz, fuera


def garantia_senderos():
    cintas = []
    for ob in list(scene.collection.all_objects):
        if ob.type == 'MESH' and en_escena(ob) and empieza(ob.name, SEND_PREF) and not ob.hide_render:
            arr = anillos_cinta(ob)
            if arr is not None:
                cintas.append((ob.name, arr, frames_cinta(arr)))
    pts = []        # [x, y, z_cara, (cinta, frame), tipo ('b' borde, 'p' pisada, 'r' talud), cinta, apoyado]
    for ci, (nm, arr, frs) in enumerate(cintas):
        nf, st, _ = arr.shape
        for f in range(nf):
            for t in ((0.0,) if f == nf - 1 else (0.0, 0.25, 0.5, 0.75)):
                fi = f if t < 0.5 else f + 1
                for j in range(1, st - 1):
                    P = arr[f, j] if t == 0.0 else arr[f, j] * (1.0 - t) + arr[f + 1, j] * t
                    borde = j in (1, st - 2)
                    pts.append([float(P[0]), float(P[1]), float(P[2]), (ci, fi), 'b' if borde else 'p', ci, None])
                    if borde:
                        fr = frs[fi]
                        sg = 1.0 if (P[0] - fr[0]) * fr[5] + (P[1] - fr[1]) * fr[6] > 0 else -1.0
                        for r in SEND_ANILLOS:
                            pts.append([float(P[0]) + sg * fr[5] * r, float(P[1]) + sg * fr[6] * r, None, (ci, fi), 'r', ci, None])

    def plano(ref, x, y):
        """plano_cinta con el frame de la MISMA rama (fi +-4) que mas cerca cae de (x, y) a lo largo del eje:
        en curva, el plano del frame del punto prolongado 5 m no es el de al lado del nodo."""
        ci, fi = ref
        frs = cintas[ci][2]
        mejor, sm = None, 1e9
        for f in range(max(0, fi - 4), min(len(frs), fi + 5)):
            fr = frs[f]
            s_ = abs((x - fr[0]) * fr[3] + (y - fr[1]) * fr[4])
            if s_ < sm:
                mejor, sm = fr, s_
        return plano_cinta(mejor, x, y)

    def apoyado(p):
        if p[6] is None:
            loc, _n, idx, _d = BVH_PROT.ray_cast(Vector((p[0], p[1], p[2] - 0.02)), ABAJO_V, SEND_APOYO)
            p[6] = loc is not None
        return p[6]

    def objetivo(p, k):
        """Cota objetivo del nodo k por la condicion del punto p: borde -> llano al plano - SEND_OBJ (el
        triangulo del borde tiene sus nodos a <= 5.7 m); talud -> 1:1.6 desde el borde."""
        zk, lok = plano(p[3], *nodo_xy(k))
        return zk - SEND_OBJ - (0.0 if p[4] == 'b' else SEND_TALUD * lok)

    def medir():
        out = {}
        for p in pts:
            if p[4] == 'r':
                continue
            zt = z_ter_tri(p[0], p[1])
            if zt is None:
                continue
            o = out.setdefault(cintas[p[5]][0], {'n': 0, 'aire_025': 0, 'aire_max': 0.0, 'hierba_005': 0, 'hierba_max': 0.0})
            o['n'] += 1
            if p[4] == 'b' and not apoyado(p):
                o['aire_025'] += int(p[2] - zt > 0.25)
                o['aire_max'] = round(max(o['aire_max'], p[2] - zt), 2)
            o['hierba_005'] += int(zt - p[2] > SEND_HIERBA)
            o['hierba_max'] = round(max(o['hierba_max'], zt - p[2]), 2)
        return out

    def subir():
        mods, excesivos = {}, set()
        for p in pts:
            if p[4] == 'p':
                continue
            zt = z_ter_tri(p[0], p[1])
            tn = tri_nodos(p[0], p[1])
            if zt is None or tn is None:
                continue
            if p[4] == 'b':
                if zt >= p[2] - SEND_TOL or apoyado(p):
                    continue
            else:
                zc, lo = plano(p[3], p[0], p[1])
                if zt >= zc - SEND_OBJ - SEND_TALUD * lo - 0.05:
                    continue
            for k in tn[0]:
                tgt = objetivo(p, k)
                z0k = TOCADOS.get(k, T['z'][k])
                if tgt - z0k > SEND_SUBIDA_LIMITE:
                    excesivos.add(k)          # (esa condicion no: horquilla de ramas pegadas; las demas si)
                    continue
                tgt = min(tgt, z0k + SEND_SUBIDA_MAX)
                if tgt > T['z'][k] + 0.02 and tgt > mods.get(k, -1e9):
                    mods[k] = tgt
        return mods, len(excesivos - set(mods))

    def bajar():
        mods = {}
        for p in pts:
            if p[4] == 'r':
                continue
            zt = z_ter_tri(p[0], p[1])
            tn = tri_nodos(p[0], p[1])
            # (el borde exterior de la berma puede quedar bajo el arranque del desmonte hasta SEND_BORDE_TAPA:
            # bajar ahi un nodo de 4 m ladera arriba abria cortes de 2.5 m por unos cm de hierba)
            lim = SEND_BORDE_TAPA if p[4] == 'b' else -SEND_HIERBA
            if zt is None or tn is None or zt <= p[2] + lim:
                continue
            # lo JUSTO: el exceso del punto se reparte entre los nodos que estan por encima del plano de la
            # cinta (en proporcion a lo que les sobra); si no basta, el resto baja los 3 por igual
            d = zt - (p[2] + (lim - 0.02 if p[4] == 'b' else -0.07))
            culp = []
            for k, w in zip(*tn):
                sob = T['z'][k] - (plano(p[3], *nodo_xy(k))[0] - SEND_OBJ)
                if sob > 0.005:
                    culp.append((k, w, sob))
            cap = sum(w * sob for _k, w, sob in culp)
            f = min(1.0, d / cap) if cap > 1e-6 else 0.0
            resto = max(0.0, d - f * cap)
            for k, w in zip(*tn):
                baja = next((f * c[2] for c in culp if c[0] == k), 0.0) + resto
                if baja <= 0.0:
                    continue
                zk = T['z'][k] - baja - 0.01
                mods[k] = min(mods.get(k, 1e9), max(zk, TOCADOS.get(k, T['z'][k]) - SEND_BAJADA_MAX))
        return mods

    def causas(bajados):
        """Por que queda aire > 0.25 en un borde: 'pista' (a < TER_PISTA_LIBRE m del asfalto), 'protegido'
        (casa, muro, losa... alrededor), 'horquilla' (faltan > SEND_SUBIDA_LIMITE m), 'relleno_tope' (ya
        subido SEND_SUBIDA_MAX),
        'conflicto' (otro punto de la cara -otra rama- obliga a bajar el mismo nodo) u 'otro'."""
        cuenta, lista = {}, []
        for p in pts:
            if p[4] != 'b' or apoyado(p):
                continue
            zt = z_ter_tri(p[0], p[1])
            tn = tri_nodos(p[0], p[1])
            if zt is None or tn is None or p[2] - zt <= 0.25:
                continue
            c = 'otro'
            for k in tn[0]:
                tgt = objetivo(p, k)
                if tgt <= T['z'][k] + 0.02:
                    continue
                if tgt - TOCADOS.get(k, T['z'][k]) > SEND_SUBIDA_LIMITE:
                    c = 'horquilla'
                elif T['z'][k] >= TOCADOS.get(k, T['z'][k]) + SEND_SUBIDA_MAX - 0.02:
                    c = 'relleno_tope'
                elif limite_pista(k, T['z'][k], tgt) <= T['z'][k]:
                    c = 'pista'
                elif k in bajados:
                    c = 'conflicto'
                elif limites_nodo(k)[0] < tgt - T['z'][k] - 0.01:
                    c = 'protegido'
                if c != 'otro':
                    break
            cuenta[c] = cuenta.get(c, 0) + 1
            if len(lista) < 400:
                lista.append([round(p[0], 1), round(p[1], 1), round(p[2] - zt, 2), c, cintas[p[5]][0]])
        return cuenta, lista

    antes = medir()
    n_sub = n_baj = n_exc = 0
    bajados = set()
    for it in range(5):
        if it < 4:
            m, ex = subir()
            n_exc = max(n_exc, ex)
            n_sub += aplicar_nodos(m)
        mb = bajar()
        bajados |= set(mb)
        n_baj += aplicar_nodos(mb)
    despues = medir()
    cuenta, lista = causas(bajados)
    return [{'nombre': nm, 'antes': antes.get(nm), 'despues': despues.get(nm)} for nm, _a, _f in cintas], \
        {'cintas': len(cintas), 'puntos': len(pts), 'subidas': n_sub, 'bajadas': n_baj, 'nodos_relleno_excesivo': n_exc,
         'aire_restante_por_causa': cuenta, 'aire_restante': lista}


TERRENO_V3 = {'ok': TER_OK}
if TER_OK:
    _t3 = time.time()
    _losas_t = garantia_losas_terreno('antes de senderos')
    _send_t, _send_r = garantia_senderos()
    _losas_t += garantia_losas_terreno('despues de senderos')
    if TOCADOS:
        TER_OB.data.update()
    _dz = [T['z'][k] - z for k, z in TOCADOS.items()]
    # (todos los nodos tocados, para verificar: [x, y, z de partida, dz])
    TERRENO_V3['nodos_lista'] = [[round(nodo_xy(k)[0], 1), round(nodo_xy(k)[1], 1), round(z, 2), round(T['z'][k] - z, 3)]
                                 for k, z in TOCADOS.items()]
    TERRENO_V3['nodos_grandes'] = sorted([[round(nodo_xy(k)[0], 1), round(nodo_xy(k)[1], 1), round(z, 2), round(T['z'][k] - z, 2)]
                                          for k, z in TOCADOS.items() if abs(T['z'][k] - z) > 1.5], key=lambda r: -abs(r[3]))[:200]
    TERRENO_V3.update({'nodos': len(TOCADOS), 'subidos': sum(1 for d in _dz if d > 0),
                       'subida_max': round(max(_dz + [0.0]), 2), 'bajada_max': round(-min(_dz + [0.0]), 2),
                       'losas': _losas_t, 'senderos': _send_t, 'senderos_resumen': _send_r, 's': round(time.time() - _t3, 1)})
    log('v3 garantias de terreno: %d nodos (%d subidos, max +%.2f / -%.2f m) en %.0f s'
        % (len(TOCADOS), TERRENO_V3['subidos'], TERRENO_V3['subida_max'], TERRENO_V3['bajada_max'], TERRENO_V3['s']))
    for _r in _losas_t:
        log('  losa %s (%s): hierba sobre la corona %s -> %s, %d nodos (limitado por %s)'
            % (_r['nombre'], _r['pasada'], _r['hierba_antes'], _r['hierba_despues'], _r['nodos'], _r['limitado_por']))
    for _r in _send_t:
        log('  sendero %s: antes %s -> despues %s' % (_r['nombre'], json.dumps(_r['antes']), json.dumps(_r['despues'])))
    log('  senderos: %s' % json.dumps({k: v for k, v in _send_r.items() if k != 'aire_restante'}))
    TERRENO_V3['plazoletas_subidas'] = subir_plazoletas()
    for _r in TERRENO_V3['plazoletas_subidas']:
        log('  plazoleta %s subida %.2f m (hierba %.2f -> %.2f)' % (_r['nombre'], _r['subida'], _r['hierba_antes'],
                                                                 _r['hierba_despues']))
BANCALES_AJUSTE = ajustar_bancales()
for _r in BANCALES_AJUSTE:
    log('v3 bancal %s: %s' % (_r['nombre'], _r['accion']))
bpy.context.view_layer.update()

LOSAS_AJUSTADAS = ajustar_losas()
bpy.context.view_layer.update()
log('losas CALLE_plaza* con el fondo bajado al terreno: %d (aire restante > 0.1 m: %d)'
    % (len(LOSAS_AJUSTADAS), sum(1 for r in LOSAS_AJUSTADAS if r['queda_aire'])))

BVH, RANGOS = construir_bvh()
_ini = [r[0] for r in RANGOS]
LOSA_FONDO = {}
for _r in RANGOS:
    if empieza(_r[2], LOSA_PREF):
        _ob = bpy.data.objects[_r[2]]
        # (v2: de los vertices, no de bound_box, que no se recalcula tras ajustar_losas)
        _cw = [(_ob.matrix_world @ v.co).z for v in _ob.data.vertices]
        LOSA_FONDO[_r[2]] = min(_cw) if _cw else min((_ob.matrix_world @ Vector(c)).z for c in _ob.bound_box)
log('losas macizas (CALLE_plaza*): %d' % len(LOSA_FONDO))
BVH_CALZ, RANGOS_CALZ = construir_bvh(
    lambda ob: ob.type == 'MESH' and en_escena(ob) and empieza(ob.name, CALZADA_PREF), 'calzada')
_ini_calz = [r[0] for r in RANGOS_CALZ]


def es_obstaculo(ob):
    """Mallas que el tronco de un arbol no puede atravesar: muros de terraza, de mirador
    y de bancal, y edificios (casas, casino, hotel, ermitas, capillitas, pergolas...)."""
    if ob.type != 'MESH' or not en_escena(ob) or empieza(ob.name, OBST_NO):
        return False
    if empieza(ob.name, OBST_PREF):
        return True
    r = raiz_de(ob)
    if empieza(r.name, OBST_RAICES):
        return True
    if r is not ob and empieza(r.name, PENON_RAICES):
        n = ob.name.lower()
        return any(k in n for k in OBST_PENON)
    return False


BVH_OBST, RANGOS_OBST = construir_bvh(es_obstaculo, 'obstaculos')
_ini_obst = [r[0] for r in RANGOS_OBST]


def nombre_apoyo(idx, rangos=None, ini=None):
    import bisect
    rangos = RANGOS if rangos is None else rangos
    ini = _ini if ini is None else ini
    k = bisect.bisect_right(ini, idx) - 1
    return rangos[k][2] if 0 <= k < len(rangos) else '?'


def impactos(x, y):
    """Todos los impactos (z, nombre) del rayo vertical en (x, y), de arriba abajo."""
    res = []
    z = Z_RAYO
    d = Vector((0.0, 0.0, -1.0))
    for _ in range(24):
        loc, _n, idx, _d = BVH.ray_cast(Vector((x, y, z)), d, z - Z_FONDO)
        if loc is None:
            break
        res.append((float(loc.z), nombre_apoyo(idx)))
        z = loc.z - 0.03
        if z <= Z_FONDO:
            break
    return res


def cimas(hits):
    """Cimas de las pilas de impactos. De arriba abajo, dos impactos consecutivos
    separados menos de GAP_APILADO son la misma superficie apilada (cinta o
    arcen sobre el terreno, cara superior/inferior de una cinta, terraplen bajo
    la calzada): ahi solo vale el mas ALTO. Un hueco >= GAP_APILADO es un
    voladizo real (roca, tunel) y la superficie de debajo sigue siendo candidata."""
    res, z_prev = [], None
    for h in sorted(hits, key=lambda h: -h[0]):
        if z_prev is None or z_prev - h[0] >= GAP_APILADO:
            res.append(h)
            z_prev = h[0]
        # z_prev = punto mas bajo de la pila actual; una losa CALLE_plaza* es maciza hasta su
        # fondo (tambor de 9 m en un talud: el terreno de dentro NO es una superficie libre)
        z_prev = min(z_prev, h[0], LOSA_FONDO.get(h[1], h[0]))
    return res


def mejor_impacto(hits, z_ref):
    """Cima de pila mas cercana a z_ref (voladizos a > 3 m: no sube al techo;
    superficies apiladas: nunca se queda debajo)."""
    return min(cimas(hits), key=lambda h: abs(h[0] - z_ref))


def superficie_encima(x, y, z_ini, alcance):
    """(altura sobre z_ini, nombre) de la primera superficie de apoyo o calzada
    que toca un rayo hacia ARRIBA desde (x, y, z_ini), o None."""
    o = Vector((x, y, z_ini))
    up = Vector((0.0, 0.0, 1.0))
    mejor = None
    for bvh, rangos, ini in ((BVH, RANGOS, _ini), (BVH_CALZ, RANGOS_CALZ, _ini_calz)):
        loc, _n, idx, _d = bvh.ray_cast(o, up, alcance)
        if loc is not None and (mejor is None or loc.z < mejor[0] + z_ini):
            mejor = (float(loc.z) - z_ini, nombre_apoyo(idx, rangos, ini))
    return mejor


# ---------------------------------------------------------------- arboles
ARBOL_FIJO = ('VEG_roca', 'VEG_plazoleta', 'VEG_jardinera')   # 5 rayos, pero no se mueven ni quitan
# losas del plan urbano: un arbol suelto (no VEG_plazoleta, que son los de las plazoletas) cuyo
# tronco cae en una calle, escalera o plaza es un resto del reparto de vegetacion: se quita
LOSA_PLAN = ('CALLE_plaza', 'CALLE_plazoleta', 'CAMINO_calle', 'CAMINO_enlace', 'CAMINO_travesia', 'CAMINO_rampa',
             'CAMINO_escalera')
ABAJO = Vector((0.0, 0.0, -1.0))
ARRIBA = Vector((0.0, 0.0, 1.0))
ANILLO = ((R_ANILLO, 0.0), (-R_ANILLO, 0.0), (0.0, R_ANILLO), (0.0, -R_ANILLO))
# --- v2 inspectores ---
# (D2-03, E2-10) calzadas que un tronco no puede tener encima ni a < R_PISADA m: las losas del
# plan y las cintas de los caminos del integrador (senderos, subida al hotel, muelle, penon)
CALZ_TRONCO = LOSA_PLAN + ('CAMINO_asfalto', 'CAMINO_adoquin', 'CAMINO_tierra', 'CAMINO_muelle',
                           'PPUEBLO_carretera')
R_PISADA = 1.5
ANILLO_P = tuple((R_PISADA * math.cos(k * math.pi / 4.0), R_PISADA * math.sin(k * math.pi / 4.0)) for k in range(8))
DIST_HUIDA = (2.0, 3.0, 4.0)     # distancias de prueba para apartar un arbol de una calzada
# (A-r2-11) holgura minima entre la copa y la calzada que tiene debajo (primer prefijo que case)
COPA_HOLGURA = (('CAMINO_terraplen', None), ('CAMINO_tierra', 2.2), ('CAMINO_escalera', 2.2),
                ('CAMINO_', 4.5), ('CALLE_plaza', 4.5), ('PISTA', 4.5), ('PIT_LANE', 4.5),
                ('PPUEBLO_carretera', 4.5))
# (C2-03) coches: las filas se asientan coche a coche
COCHE_GRUPO_PREF = ('COCHE_fila',)
COCHE_DESNIVEL_MAX = 0.8     # entre los 4 impactos de las ruedas: mas -> se quita
COCHE_HUNDIR = 0.03          # las ruedas entran 3 cm en el suelo
COCHE_LIBRE = 8.0            # roca a menos de esto sobre el coche -> se quita
COCHE_BAJOS = 0.25           # altura de los bajos: el suelo no puede asomar por encima
ROCA_PREF = ('TUNEL_acantilado', 'MCOCHE_', 'PPUEBLO_roca', 'PENON_roca', 'MONT_')


def es_arbol(nombre):
    return empieza(nombre, ARBOL_PREF) and not empieza(nombre, ARBOL_NO)


def borde_pista(x, y):
    """Distancia al borde del asfalto (negativa = dentro)."""
    _zp, d, w = pista_cerca(x, y)
    return d - w / 2.0


def apoyo_arbol(x, y, z_ref):
    """Apoyo de un arbol en (x, y): dict(hz, hc, apoyo, desnivel, gx, gy, n) o None.
    hc = cima mas cercana a z_ref en el centro. En un anillo de R_ANILLO m (4 rayos)
    vale la cima mas cercana a hc SOBRE LA MISMA MALLA (las de otra malla -cinta de
    camino, losa, arcen- no cuentan). hz = minimo de los puntos validos: el tronco no
    ensena hueco por el lado de abajo. (gx, gy) = gradiente (apunta cuesta arriba)."""
    # (v2: CAMINO_terraplen no es apoyo de un arbol; si el tronco cae en el, queda bajo su cara y
    # choque_tronco lo saca como de un muro)
    hits = [h for h in impactos(x, y) if not empieza(h[1], NO_APOYO_ARBOL)]
    if not hits:
        return None
    hc, ap = mejor_impacto(hits, z_ref)
    # el TERRENO es una rejilla de alturas (sin voladizos): cualquier diferencia en el anillo es
    # ladera o escalon real; en las demas mallas (rocas, losas) > GAP_APILADO es otra repisa
    lim = 1e9 if ap == 'TERRENO' else GAP_APILADO
    zs = {-1: hc}
    for k, (dx, dy) in enumerate(ANILLO):
        hk = [h for h in cimas([h_ for h_ in impactos(x + dx, y + dy) if not empieza(h_[1], NO_APOYO_ARBOL)])
              if h[1] == ap and abs(h[0] - hc) < lim]
        if hk:
            zs[k] = min(hk, key=lambda h: abs(h[0] - hc))[0]

    def grad(a, b):
        if a in zs and b in zs:
            return (zs[a] - zs[b]) / (2.0 * R_ANILLO)
        if a in zs:
            return (zs[a] - hc) / R_ANILLO
        if b in zs:
            return (hc - zs[b]) / R_ANILLO
        return 0.0
    v = list(zs.values())
    return {'hz': min(v), 'hc': hc, 'apoyo': ap, 'desnivel': max(v) - min(v),
            'gx': grad(0, 1), 'gy': grad(2, 3), 'n': len(v)}


def calzada_cerca(x, y, hz, anillo, prefijos, dz0, dz1):
    """[(dx, dy, nombre, z)] de los rayos (centro + anillo) que tocan una malla de `prefijos` entre
    hz + dz0 y hz + dz1. Se miran TODOS los impactos, no las cimas (v2, D2-03: en VEG_pino.628 el
    TERRENO asoma 1 cm sobre el adoquin de la calle y la pila se quedaba con el terreno)."""
    malos = []
    for dx, dy in ((0.0, 0.0),) + tuple(anillo):
        for zh, nm in impactos(x + dx, y + dy):
            if hz + dz0 < zh < hz + dz1 and empieza(nm, prefijos):
                malos.append((dx, dy, nm, round(zh, 2)))
                break
    return malos


def tronco_en_calzada(x, y, hz, alto):
    """D2-03: losa del plan (rampa, calle, plaza...) o cinta de camino EN el tronco o ENCIMA de el
    (del pie - 0.3 m hasta la copa + 1 m), en el centro o en el anillo de R_ANILLO m."""
    return calzada_cerca(x, y, hz, ANILLO, CALZ_TRONCO, -0.3, alto + 1.0)


def camino_a_pie(x, y, hz):
    """E2-10: algun camino o losa a < R_PISADA m del tronco (8 rayos + centro), a la cota del arbol
    (de -1.5 a +2.5 m: la calle de otra terraza no cuenta)."""
    return calzada_cerca(x, y, hz, ANILLO_P, CALZ_TRONCO, -1.5, 2.5)


def candidato_ok(x2, y2, a, b0, alto, lim_dz=2.5, copa=None):
    """apoyo_arbol del sitio nuevo (x2, y2) si vale para un arbol que estaba en `a`: sin acercarse
    a la pista (borde >= min(actual, 4 m)), misma malla de apoyo, sin saltar de terraza (lim_dz),
    desnivel <= DESNIVEL_MAX, sin calzada en el tronco, sin camino a < R_PISADA m, sin muro ni
    edificio en el tronco (choque_tronco) y, con copa = (pw, plazoleta, x, y, z, hund) del sitio
    actual, con la copa trasladada libre de calzadas (si no, el arbol iria y volveria). Si no, None."""
    if borde_pista(x2, y2) < min(b0, 4.0):
        return None
    a2 = apoyo_arbol(x2, y2, a['hc'])
    if (a2 is None or a2['apoyo'] != a['apoyo'] or abs(a2['hc'] - a['hc']) > lim_dz
            or a2['desnivel'] > DESNIVEL_MAX):
        return None
    if tronco_en_calzada(x2, y2, a2['hz'], alto) or camino_a_pie(x2, y2, a2['hz']):
        return None
    if choque_tronco(x2, y2, a2['hz'], alto) is not None:
        return None
    if copa is not None and len(copa[0]):
        pw, plazo, x0, y0, z0, hund = copa
        if copa_sobre_calzada(pw + np.array([x2 - x0, y2 - y0, a2['hz'] + hund - z0]), plazoleta=plazo) is not None:
            return None
    return a2


def rumbos_huida(vx, vy, a):
    """Direcciones de prueba: alejarse de (vx, vy) (y +-45 grados), ladera arriba/abajo, 8 rumbos."""
    dirs = []
    lv = math.hypot(vx, vy)
    if lv > 1e-6:
        for da in (0.0, math.pi / 4.0, -math.pi / 4.0):
            c_, s_ = math.cos(da), math.sin(da)
            dirs.append(((vx * c_ - vy * s_) / lv, (vx * s_ + vy * c_) / lv))
    g = math.hypot(a['gx'], a['gy'])
    if g > 1e-3:
        dirs += [(a['gx'] / g, a['gy'] / g), (-a['gx'] / g, -a['gy'] / g)]
    return dirs + [(math.cos(k * math.pi / 4.0), math.sin(k * math.pi / 4.0)) for k in range(8)]


def sitio_arbol(x, y, z_ref, movible=True, alto=6.0, copa=None):
    """(x, y, apoyo_arbol, problema, malos) definitivo de un arbol.
    - (v1) desnivel del anillo > DESNIVEL_MOVER (borde de explanada, desmonte, escalon de
      terraza): prueba PASO_LADERA m ladera ARRIBA y luego abajo y se queda con el de menor
      desnivel.
    - (v2, D2-03) calzada EN o BAJO el tronco, o (E2-10) camino a < R_PISADA m: prueba alejarse
      DIST_HUIDA m del lado malo (+-45 grados), ladera arriba/abajo y 8 rumbos. Si no hay sitio,
      problema = 'losa' (el que llama quita el arbol) o 'camino' (se queda; aviso).
    Todo candidato pasa candidato_ok (pista, misma malla, terraza, desnivel, calzada, pisada)."""
    a = apoyo_arbol(x, y, z_ref)
    if a is None or not movible:
        return x, y, a, None, []
    malos_t = tronco_en_calzada(x, y, a['hz'], alto)
    malos_p = [] if malos_t else camino_a_pie(x, y, a['hz'])
    if not malos_t and not malos_p and a['desnivel'] <= DESNIVEL_MOVER:
        return x, y, a, None, []
    b0 = borde_pista(x, y)
    if not malos_t and not malos_p:
        g = math.hypot(a['gx'], a['gy'])
        mejor = (x, y, a, None, [])
        if g < 1e-3:
            return mejor
        for sg in (1.0, -1.0):
            x2, y2 = x + sg * a['gx'] / g * PASO_LADERA, y + sg * a['gy'] / g * PASO_LADERA
            a2 = candidato_ok(x2, y2, a, b0, alto, copa=copa)
            if a2 is not None and a2['desnivel'] < mejor[2]['desnivel'] - 0.1:
                mejor = (x2, y2, a2, None, [])
                if a2['desnivel'] <= DESNIVEL_MOVER:
                    break
        return mejor
    malos = malos_t or malos_p
    vx, vy = -sum(m[0] for m in malos), -sum(m[1] for m in malos)
    mejor = None
    for dist in DIST_HUIDA:
        for ux, uy in rumbos_huida(vx, vy, a):
            x2, y2 = x + ux * dist, y + uy * dist
            a2 = candidato_ok(x2, y2, a, b0, alto, copa=copa)
            if a2 is None:
                continue
            if a2['desnivel'] <= DESNIVEL_MOVER:
                return x2, y2, a2, None, malos
            if mejor is None or a2['desnivel'] < mejor[2]['desnivel']:
                mejor = (x2, y2, a2, None, malos)
        if mejor is not None:
            return mejor
    return x, y, a, ('losa' if malos_t else 'camino'), malos


def alto_arbol(ob):
    return min(12.0, max(2.5, float(ob.dimensions.z))) if ob.type == 'MESH' else 6.0


def choque_tronco(x, y, z_suelo, alto):
    """(nombre, z) del muro/edificio que asoma por encima del suelo del arbol en el
    tronco o a +-OFF_TRONCO m (rayos verticales hasta la copa), o None."""
    for dx, dy in ((0.0, 0.0), (OFF_TRONCO, 0.0), (-OFF_TRONCO, 0.0), (0.0, OFF_TRONCO), (0.0, -OFF_TRONCO)):
        loc, _n, idx, _d = BVH_OBST.ray_cast(Vector((x + dx, y + dy, z_suelo + alto)), ABAJO, alto - 0.1)
        if loc is not None:
            return nombre_apoyo(idx, RANGOS_OBST, _ini_obst), float(loc.z)
    return None


def salir_de_obstaculo(x, y, z_suelo, alto, apoyo, hc):
    """Nuevo sitio (x, y, apoyo_arbol) a SEPARAR_M m del muro/edificio, en la direccion
    que se aleja del punto mas cercano (y si no, en 8 rumbos): misma malla de apoyo,
    sin saltar de terraza (< 1.5 m), sin acercarse a la pista y con el tronco libre."""
    dirs = []
    loc, nrm, _i, _d = BVH_OBST.find_nearest(Vector((x, y, z_suelo + 0.5)), 8.0)
    if loc is not None:
        vx, vy = x - loc.x, y - loc.y
        lv = math.hypot(vx, vy)
        if lv < 0.05 and nrm is not None:
            vx, vy = nrm.x, nrm.y
            lv = math.hypot(vx, vy)
        if lv > 1e-3:
            dirs.append((vx / lv, vy / lv))
    dirs += [(math.cos(k * math.pi / 4.0), math.sin(k * math.pi / 4.0)) for k in range(8)]
    b0 = borde_pista(x, y)
    for dist in SEPARAR_M:
        for ux, uy in dirs:
            x2, y2 = x + ux * dist, y + uy * dist
            # (v2: candidato_ok: ademas del tronco libre, sin calzada en el tronco ni camino a < R_PISADA m)
            a2 = candidato_ok(x2, y2, {'apoyo': apoyo, 'hc': hc}, b0, alto, lim_dz=1.5)
            if a2 is None:
                continue
            return x2, y2, a2
    return None


# ---------------------------------------------------------------- copa sobre una calzada (v2, A-r2-11)
_COPA = {}


def copa_local(ob):
    """Puntos de COPA en coordenadas locales (cache por malla, las mallas de arbol son compartidas):
    vertices por encima del 25 % de la altura y a > 0.5 m del eje del tronco; en cada octante, el
    mas exterior y el mas bajo de la parte exterior (>= 0.6 del radio del octante)."""
    me = ob.data
    if me.name in _COPA:
        return _COPA[me.name]
    pts = np.zeros((0, 3))
    n = len(me.vertices)
    if n:
        co = np.empty(n * 3, dtype=np.float64)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        z0, z1 = float(co[:, 2].min()), float(co[:, 2].max())
        r = np.hypot(co[:, 0], co[:, 1])
        sel = (co[:, 2] > z0 + 0.25 * (z1 - z0)) & (r > 0.5)
        if sel.any():
            c, rr = co[sel], r[sel]
            sec = np.floor((np.arctan2(c[:, 1], c[:, 0]) + math.pi) / (math.pi / 4.0)).astype(int) % 8
            lst = []
            for k in range(8):
                m = sec == k
                if not m.any():
                    continue
                ck, rk = c[m], rr[m]
                lst.append(ck[int(np.argmax(rk))])
                ext = ck[rk >= 0.6 * rk.max()]
                lst.append(ext[int(np.argmin(ext[:, 2]))])
            pts = np.array(lst)
    _COPA[me.name] = pts
    return pts


def copa_mundo(ob):
    p = copa_local(ob) if ob.type == 'MESH' else np.zeros((0, 3))
    if not len(p):
        return p
    mw = ob.matrix_world
    R = np.array([[mw[i][j] for j in range(3)] for i in range(3)])
    t = np.array([mw[0][3], mw[1][3], mw[2][3]])
    return p @ R.T + t


def holgura_copa(nombre, plazoleta=False):
    """Holgura minima de copa sobre la malla `nombre` (None = no es calzada)."""
    if plazoleta and nombre.startswith('CALLE_plaza'):
        return None            # (los arboles de plazoleta estan en su plaza a proposito)
    for pref, h in COPA_HOLGURA:
        if nombre.startswith(pref):
            return h
    return None


def copa_sobre_calzada(pw, plazoleta=False):
    """Peor punto de copa (pw: Nx3 en mundo) que tiene debajo, como PRIMER impacto, una calzada a
    menos de su holgura: dict(holgura, minimo, calzada, x, y) o None."""
    peor = None
    for p in pw:
        o = Vector((float(p[0]), float(p[1]), float(p[2])))
        best = None
        for bvh, rangos, ini in ((BVH, RANGOS, _ini), (BVH_CALZ, RANGOS_CALZ, _ini_calz)):
            loc, _n, idx, _d = bvh.ray_cast(o, ABAJO, 40.0)
            if loc is not None and (best is None or loc.z > best[0].z):
                best = (loc, nombre_apoyo(idx, rangos, ini))
        if best is None:
            continue
        lim = holgura_copa(best[1], plazoleta)
        if lim is None:
            continue
        hol = o.z - best[0].z
        if hol < lim and (peor is None or hol - lim < peor['holgura'] - peor['minimo']):
            peor = {'holgura': round(hol, 2), 'minimo': lim, 'calzada': best[1],
                    'x': round(best[0].x, 2), 'y': round(best[0].y, 2)}
    return peor


def quitar(ob):
    """Borra el objeto y sus hijos (sin bpy.ops)."""
    for ch in list(ob.children_recursive):
        bpy.data.objects.remove(ch, do_unlink=True)
    bpy.data.objects.remove(ob, do_unlink=True)


# ---------------------------------------------------------------- coches (v2, C2-03)
def es_roca(nombre):
    n = nombre.lower()
    return empieza(nombre, ROCA_PREF) or 'roca' in n or 'acantilado' in n


def asentar_coche(c):
    """Asienta UN coche (malla con la base en z local minima, largo por el eje mayor de su caja)
    sobre sus 4 ruedas: rayo bajo cada rueda (mejor_impacto), plano por los 4 impactos, giro minimo
    del 'arriba' del coche a la normal del plano (cabeceo y balanceo, sin cambiar el rumbo) y las
    ruedas COCHE_HUNDIR bajo el plano. Devuelve (estado, info): 'ok' (movido), 'sin_suelo',
    'pendiente' (> COCHE_DESNIVEL_MAX entre ruedas), 'roca' (roca a < COCHE_LIBRE m sobre el coche:
    bajo el afloramiento del McLaren) o 'enterrado' (el suelo asoma por los bajos). Solo 'ok' mueve."""
    mw = c.matrix_world.copy()
    bb = [Vector(v) for v in c.bound_box]
    x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
    y0, y1 = min(v.y for v in bb), max(v.y for v in bb)
    zb, zt = min(v.z for v in bb), max(v.z for v in bb)
    lx, ly = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    fx, fy = (0.40, 0.31) if ly >= lx else (0.31, 0.40)
    ruedas = [(cx + sx * fx * lx, cy + sy * fy * ly) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    W = [mw @ Vector((u, v, zb)) for u, v in ruedas]
    hz, aps = [], []
    for w in W:
        hits = impactos(w.x, w.y)
        if not hits:
            return 'sin_suelo', {}
        h = mejor_impacto(hits, w.z)
        hz.append(h[0])
        aps.append(h[1])
    info = {'apoyo': sorted(set(aps)), 'desnivel': round(max(hz) - min(hz), 2),
            'hueco_ruedas': [round(w.z - h, 2) for w, h in zip(W, hz)]}
    if max(hz) - min(hz) > COCHE_DESNIVEL_MAX:
        return 'pendiente', info
    C = sum(W, Vector((0.0, 0.0, 0.0))) / 4.0
    A_ = np.array([[1.0, w.x - C.x, w.y - C.y] for w in W])
    c0, gx, gy = (float(v) for v in np.linalg.lstsq(A_, np.array(hz), rcond=None)[0])
    nrm = Vector((-gx, -gy, 1.0)).normalized()
    up = (mw.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    q = up.rotation_difference(nrm)
    M1 = Matrix.Translation(C) @ q.to_matrix().to_4x4() @ Matrix.Translation(-C) @ mw
    W1 = [M1 @ Vector((u, v, zb)) for u, v in ruedas]
    dz = sum(c0 + gx * (w.x - C.x) + gy * (w.y - C.y) - w.z for w in W1) / 4.0 - COCHE_HUNDIR
    M2 = Matrix.Translation(Vector((0.0, 0.0, dz))) @ M1
    info['inclinacion_grados'] = round(math.degrees(up.angle(nrm)), 1)
    info['torsion_m'] = round(max(abs(c0 + gx * (w.x - C.x) + gy * (w.y - C.y) - h) for w, h in zip(W, hz)), 3)
    alto_c = zt - zb
    for u in (x0 + 0.15 * lx, cx, x1 - 0.15 * lx):
        for v in (y0 + 0.15 * ly, cy, y1 - 0.15 * ly):
            p = M2 @ Vector((u, v, zb + COCHE_BAJOS))
            for bvh, rangos, ini in ((BVH, RANGOS, _ini), (BVH_CALZ, RANGOS_CALZ, _ini_calz)):
                loc, _n, idx, _d = bvh.ray_cast(p, ARRIBA, COCHE_LIBRE)
                if loc is None:
                    continue
                nm = nombre_apoyo(idx, rangos, ini)
                if es_roca(nm):
                    info.update({'encima': nm, 'a_m': round(loc.z - p.z + COCHE_BAJOS, 2)})
                    return 'roca', info
                if loc.z - p.z < alto_c - COCHE_BAJOS:
                    info.update({'encima': nm, 'a_m': round(loc.z - p.z + COCHE_BAJOS, 2)})
                    return 'enterrado', info
    c.matrix_world = M2
    info['dz'] = round(M2.translation.z - mw.translation.z, 3)
    return 'ok', info


# ---------------------------------------------------------------- asentar
def clasificar(ob):
    """'asentar' | 'edificio' | 'informe' | None para una raiz de la escena."""
    if ob.parent is not None or not en_escena(ob) or ob.type not in ('MESH', 'EMPTY'):
        return None
    n = ob.name
    # (v1: los edificios van ANTES que ASENTAR_NO; si no, ITAL_ermita no salia nunca en el informe)
    if empieza(n, EDIFICIO_PREF):
        return 'edificio'
    if any(k in n for k in ASENTAR_NO):
        return None
    if empieza(n, INFORME_PREF):
        return 'informe'
    if empieza(n, ASENTAR_PREF):
        return 'asentar'
    return None


def familia(nombre):
    base = nombre.split('.')[0]
    partes = base.split('_')
    return '_'.join(partes[:2]) if len(partes) > 1 else base


movidos, sin_impacto, saltos, bajo_mar, dudosos, informe_solo = [], [], [], [], [], []
quitados = []                # arboles en una ladera imposible o metidos en un muro sin sitio libre
junto_a_camino = []          # v2 (E2-10): camino a < R_PISADA m del tronco y sin sitio libre (se queda)
por_familia = {}
n_cand = 0
revisar_arriba = []          # [ob, dz_ini]: el rayo de autocomprobacion arranca en z_ob + dz_ini


def fam_reg(fam):
    return por_familia.setdefault(fam, {'n': 0, 'movidos': 0, 'flotaban': 0, 'enterrados': 0, 'sin_impacto': 0,
                                        'no_movidos': 0, 'quitados': 0, 'desplazados_xy': 0})


for ob in list(scene.collection.all_objects):
    try:
        clase = clasificar(ob)
    except ReferenceError:
        continue          # (hijo de un arbol quitado antes)
    if clase not in ('asentar', 'informe'):
        continue
    if ob.name.startswith('COCHE_'):
        continue          # v2 (C2-03): los coches se asientan uno a uno, mas abajo
    n_cand += 1
    x, y, z0 = ob.location.x, ob.location.y, ob.location.z
    fam = familia(ob.name)
    fam_reg(fam)
    por_familia[fam]['n'] += 1
    hits = impactos(x, y)
    if not hits:
        sin_impacto.append({'nombre': ob.name, 'x': round(x, 2), 'y': round(y, 2), 'z': round(z0, 2),
                            'motivo': 'fuera_del_terreno' if not dentro_terreno(x, y) else 'sin_superficie'})
        por_familia[fam]['sin_impacto'] += 1
        continue
    hz, apoyo = mejor_impacto(hits, z0)
    # arboles: 5 rayos (no flotan por el lado de abajo) y, en una ladera imposible, moverlos o quitarlos
    x1, y1, desn, hc_, malos = x, y, None, None, []
    if clase == 'asentar' and es_arbol(ob.name):
        fijo = empieza(ob.name, ARBOL_FIJO)
        x1, y1, a, prob, malos = sitio_arbol(x, y, z0, movible=not fijo, alto=alto_arbol(ob),
                                             copa=(copa_mundo(ob), False, x, y, z0, hundimiento(ob.name)))
        if a is None:          # (v2: solo habia CAMINO_terraplen debajo, que no es apoyo de arboles)
            sin_impacto.append({'nombre': ob.name, 'x': round(x, 2), 'y': round(y, 2), 'z': round(z0, 2),
                                'motivo': 'sin_superficie'})
            por_familia[fam]['sin_impacto'] += 1
            continue
        hz, apoyo, desn, hc_ = a['hz'], a['apoyo'], a['desnivel'], a['hc']
        motivo_q = None
        if not fijo and empieza(apoyo, LOSA_PLAN):
            motivo_q = 'tronco en %s (%.2f m %s de la losa)' % (apoyo, abs(hc_ - z0), 'bajo' if z0 < hc_ else 'sobre')
        elif prob == 'losa':
            motivo_q = ('tronco en/bajo %s (%.2f m sobre el pie) y sin sitio libre a %s m'
                        % (malos[0][2], malos[0][3] - hz, '/'.join('%.0f' % d for d in DIST_HUIDA)))
        elif desn > DESNIVEL_MAX and not fijo:
            motivo_q = 'ladera imposible: %.2f m de desnivel en %.1f m de tronco' % (desn, 2 * R_ANILLO)
        if motivo_q:
            quitados.append({'nombre': ob.name, 'x': round(x, 2), 'y': round(y, 2), 'z': round(z0, 2),
                             'apoyo': apoyo, 'motivo': motivo_q})
            por_familia[fam]['quitados'] += 1
            quitar(ob)
            continue
        if prob == 'camino':
            junto_a_camino.append({'nombre': ob.name, 'x': round(x, 2), 'y': round(y, 2), 'z': round(hz, 2),
                                   'camino': sorted(set(m[2] for m in malos))})
    hund = hundimiento(ob.name)
    z1 = hz + hund
    dz = z1 - z0
    reg = {'nombre': ob.name, 'x': round(x, 2), 'y': round(y, 2), 'z_antes': round(z0, 3),
           'z_despues': round(z1, 3), 'dz': round(dz, 3), 'apoyo': apoyo, 'n_impactos': len(hits),
           'n_cimas': len(cimas(hits))}
    if desn is not None:
        reg['desnivel'] = round(desn, 2)
    movido_xy = (x1, y1) != (x, y)
    if movido_xy:
        reg['dxy'] = [round(x1 - x, 2), round(y1 - y, 2)]
        # v2: por que se movio (calzada/camino cerca del tronco, o desnivel del anillo)
        reg['por'] = ('cerca de ' + ', '.join(sorted(set(m[2] for m in malos)))) if malos else 'desnivel'
    if clase == 'informe':
        # MONT_pena: solo desnivel (el integrador las hunde 2.5 m a proposito; se van en T7)
        informe_solo.append(reg)
        continue
    # el rayo de autocomprobacion arranca 5 cm sobre la base real (base - hundimiento)
    # (arboles: desde 5 cm sobre el suelo del CENTRO del tronco, que en ladera esta por encima
    # del minimo del anillo donde se apoya la base)
    revisar_arriba.append([ob, 0.05 + (max(0.0, -hund) if hc_ is None else hc_ - z1)])
    mover = True
    if abs(dz) > SALTO_M:
        saltos.append(reg)
    if z1 < NIVEL_MAR + 0.3 and z0 >= NIVEL_MAR - 0.5:
        # bajo el agua solo hay roca sumergida: dejarlo donde esta y apuntarlo
        reg['motivo'] = 'quedaria bajo el mar (%.1f): no se mueve' % z1
        bajo_mar.append(reg)
        mover = False
    elif abs(dz) > DUDOSO_M:
        zp, dp, wp = pista_cerca(x, y)
        if abs(z0 - zp) < 2.0 and dp < wp / 2 + 12.0:
            # mobiliario puesto a cota de calzada junto a un tramo elevado
            # (puente/viaducto): el suelo de abajo NO es su apoyo
            reg['motivo'] = 'a cota de pista elevada (puente), suelo %.1f m mas abajo: no se mueve' % (-dz)
            mover = False
        else:
            reg['motivo'] = 'desplazamiento grande, revisar'
        dudosos.append(reg)
    if not mover:
        revisar_arriba[-1][1] = 0.05 + max(0.0, -hund)      # se queda donde estaba
        por_familia[fam]['no_movidos'] += 1
        continue
    if abs(dz) > 0.01 or movido_xy:
        ob.location = (x1, y1, z1)
        movidos.append(reg)
        por_familia[fam]['movidos'] += 1
        if movido_xy:
            por_familia[fam]['desplazados_xy'] += 1
        if dz < -UMBRAL_INFORME:
            por_familia[fam]['flotaban'] += 1
        elif dz > UMBRAL_INFORME:
            por_familia[fam]['enterrados'] += 1
log('candidatos %d, movidos %d, sin impacto %d, saltos>%.0fm %d, bajo el mar %d, dudosos %d, arboles quitados %d'
    % (n_cand, len(movidos), len(sin_impacto), SALTO_M, len(saltos), len(bajo_mar), len(dudosos), len(quitados)))

# --- hijos sueltos: arboles de las hileras/grupos rigidos del italiano_kit (ITAL_cipreses,
# ITAL_bancal, ITAL_ermita), uno a uno. clasificar() solo mira raices y la hilera entera
# quedaba a la cota de su centro: +-20 m en una ladera del 75 % (E1, J2, C-05, D2) ---
bpy.context.view_layer.update()
hijos_asentados = []
for raiz in [o for o in scene.collection.all_objects
             if o.parent is None and en_escena(o) and empieza(o.name, GRUPO_HIJOS_PREF)]:
    for ch in list(raiz.children):
        if ch.type != 'MESH' or not en_escena(ch) or not empieza(ch.name, HIJO_ARBOL_PREF) or not es_arbol(ch.name):
            continue
        w = ch.matrix_world.translation.copy()
        fam = familia(ch.name)
        fam_reg(fam)
        por_familia[fam]['n'] += 1
        x1, y1, a, prob, malos = sitio_arbol(w.x, w.y, w.z, alto=alto_arbol(ch),
                                             copa=(copa_mundo(ch), False, w.x, w.y, w.z, hundimiento(ch.name)))
        if a is None:
            sin_impacto.append({'nombre': ch.name, 'x': round(w.x, 2), 'y': round(w.y, 2), 'z': round(w.z, 2),
                                'motivo': 'fuera_del_terreno' if not dentro_terreno(w.x, w.y) else 'sin_superficie'})
            por_familia[fam]['sin_impacto'] += 1
            continue
        if a['desnivel'] > DESNIVEL_MAX or empieza(a['apoyo'], LOSA_PLAN) or prob == 'losa':
            if empieza(a['apoyo'], LOSA_PLAN):
                mot = 'tronco en %s' % a['apoyo']
            elif prob == 'losa':
                mot = 'tronco en/bajo %s y sin sitio libre' % malos[0][2]
            else:
                mot = 'ladera imposible: %.2f m de desnivel en %.1f m de tronco' % (a['desnivel'], 2 * R_ANILLO)
            quitados.append({'nombre': ch.name, 'grupo': raiz.name, 'x': round(w.x, 2), 'y': round(w.y, 2),
                             'z': round(w.z, 2), 'apoyo': a['apoyo'], 'motivo': mot})
            por_familia[fam]['quitados'] += 1
            quitar(ch)
            continue
        if prob == 'camino':
            junto_a_camino.append({'nombre': ch.name, 'grupo': raiz.name, 'x': round(w.x, 2), 'y': round(w.y, 2),
                                   'z': round(a['hz'], 2), 'camino': sorted(set(m[2] for m in malos))})
        hund = hundimiento(ch.name)
        z1 = a['hz'] + hund
        dz = z1 - w.z
        reg = {'nombre': ch.name, 'grupo': raiz.name, 'x': round(w.x, 2), 'y': round(w.y, 2),
               'z_antes': round(w.z, 3), 'z_despues': round(z1, 3), 'dz': round(dz, 3), 'apoyo': a['apoyo'],
               'desnivel': round(a['desnivel'], 2)}
        if (x1, y1) != (w.x, w.y):
            reg['dxy'] = [round(x1 - w.x, 2), round(y1 - w.y, 2)]
            reg['por'] = ('cerca de ' + ', '.join(sorted(set(m[2] for m in malos)))) if malos else 'desnivel'
            por_familia[fam]['desplazados_xy'] += 1
        if z1 < NIVEL_MAR + 0.3 and w.z >= NIVEL_MAR - 0.5:
            reg['motivo'] = 'quedaria bajo el mar (%.1f): no se mueve' % z1
            bajo_mar.append(reg)
            por_familia[fam]['no_movidos'] += 1
            continue
        revisar_arriba.append([ch, 0.05 + a['hc'] - z1])
        if abs(dz) > 0.01 or 'dxy' in reg:
            mw = ch.matrix_world.copy()
            mw.translation = Vector((x1, y1, z1))
            ch.matrix_world = mw
            hijos_asentados.append(reg)
            por_familia[fam]['movidos'] += 1
            if dz < -UMBRAL_INFORME:
                por_familia[fam]['flotaban'] += 1
            elif dz > UMBRAL_INFORME:
                por_familia[fam]['enterrados'] += 1
log('hijos de hileras/grupos asentados uno a uno: %d (flotaban > %.1f m: %d, enterrados: %d)'
    % (len(hijos_asentados), UMBRAL_INFORME, sum(1 for h in hijos_asentados if h['dz'] < -UMBRAL_INFORME),
       sum(1 for h in hijos_asentados if h['dz'] > UMBRAL_INFORME)))

# --- v2 (C2-03): coches uno a uno. La fila (COCHE_fila*, EMPTY) se movia entera por el rayo de
# su origen y los coches quedaban 0.2-0.56 m al aire en ladera (y la fila de s 734 bajo y dentro
# del afloramiento del McLaren). Ahora cada coche hijo apoya sus 4 ruedas; los que no caben se
# quitan, y una fila sin coches tambien ---
bpy.context.view_layer.update()
coches_asentados, coches_quitados = [], []
for raiz in [o for o in scene.collection.all_objects
             if o.parent is None and en_escena(o) and o.name.startswith('COCHE_')]:
    n_cand += 1
    if empieza(raiz.name, COCHE_GRUPO_PREF) or raiz.type != 'MESH':
        lista = [c for c in raiz.children if c.type == 'MESH' and en_escena(c) and c.name.startswith('COCHE_')]
    else:
        lista = [raiz]            # coche suelto
    for c in lista:
        fam = familia(c.name)
        fam_reg(fam)
        por_familia[fam]['n'] += 1
        w0 = c.matrix_world.translation.copy()
        estado, info = asentar_coche(c)
        reg = dict({'nombre': c.name, 'fila': raiz.name, 'x': round(w0.x, 2), 'y': round(w0.y, 2),
                    'z': round(w0.z, 2), 'estado': estado}, **info)
        if estado == 'ok':
            coches_asentados.append(reg)
            if abs(info.get('dz', 0.0)) > 0.01 or info.get('inclinacion_grados', 0.0) > 0.2:
                por_familia[fam]['movidos'] += 1
            continue
        reg['motivo'] = {'sin_suelo': 'sin superficie bajo las ruedas',
                         'pendiente': 'desnivel de %.2f m entre ruedas (max %.1f)' % (info.get('desnivel', 0), COCHE_DESNIVEL_MAX),
                         'roca': 'roca %s a %.1f m sobre los bajos' % (info.get('encima'), info.get('a_m', 0)),
                         'enterrado': '%s atraviesa la carroceria (%.2f m sobre los bajos)' % (info.get('encima'), info.get('a_m', 0))}[estado]
        coches_quitados.append(reg)
        por_familia[fam]['quitados'] += 1
        if c is raiz:
            quitar(c)
            break
        quitar(c)
    try:
        if raiz.type == 'EMPTY' and not any(ch.name.startswith('COCHE_') for ch in raiz.children):
            coches_quitados.append({'nombre': raiz.name, 'fila': raiz.name, 'estado': 'fila_vacia',
                                    'motivo': 'fila sin coches', 'x': round(raiz.location.x, 2),
                                    'y': round(raiz.location.y, 2), 'z': round(raiz.location.z, 2)})
            quitar(raiz)
    except ReferenceError:
        pass
log('coches asentados sobre sus ruedas: %d, quitados: %d (%s)'
    % (len(coches_asentados), sum(1 for c in coches_quitados if c['estado'] != 'fila_vacia'),
       json.dumps({e: sum(1 for c in coches_quitados if c['estado'] == e)
                   for e in sorted(set(c['estado'] for c in coches_quitados))})))
for c in coches_quitados[:20]:
    log('  COCHE fuera %s (%s): %s' % (c['nombre'], c['fila'], c['motivo']))

# --- arboles metidos en un muro o una casa (N3): rayos verticales en el tronco y a +-0.3 m
# contra muros y edificios; si alguno asoma por encima del suelo, se saca 1.5-3 m y se vuelve
# a asentar; si no hay sitio, se quita ---
bpy.context.view_layer.update()
dentro_de_muro = []
for ent in revisar_arriba:
    ob = ent[0]
    try:
        nombre = ob.name
    except ReferenceError:
        continue
    if not es_arbol(nombre) or empieza(nombre, ARBOL_FIJO):
        continue
    w = ob.matrix_world.translation.copy()
    hund = hundimiento(nombre)
    z_suelo = w.z - hund
    alto = alto_arbol(ob)
    ch_ = choque_tronco(w.x, w.y, z_suelo, alto)
    if ch_ is None:
        continue
    reg = {'nombre': nombre, 'x': round(w.x, 2), 'y': round(w.y, 2), 'z': round(w.z, 2),
           'obstaculo': ch_[0], 'asoma_m': round(ch_[1] - z_suelo, 2)}
    a = apoyo_arbol(w.x, w.y, z_suelo)
    nuevo = salir_de_obstaculo(w.x, w.y, z_suelo, alto, a['apoyo'], a['hc']) if a is not None else None
    if nuevo is None:
        reg['accion'] = 'quitado (sin sitio libre a %s m)' % '/'.join('%.1f' % d for d in SEPARAR_M)
        quitados.append(dict(reg, motivo='dentro de %s' % ch_[0]))
        f_ = familia(nombre)
        if f_ in por_familia:
            por_familia[f_]['quitados'] += 1
        quitar(ob)
    else:
        x2, y2, a2 = nuevo
        mw = ob.matrix_world.copy()
        mw.translation = Vector((x2, y2, a2['hz'] + hund))
        ob.matrix_world = mw
        ent[1] = 0.05 + a2['hc'] - (a2['hz'] + hund)
        reg['accion'] = 'movido %.1f m' % math.hypot(x2 - w.x, y2 - w.y)
        reg['a'] = [round(x2, 2), round(y2, 2), round(a2['hz'] + hund, 3)]
    dentro_de_muro.append(reg)
log('arboles metidos en muros/edificios: %d (movidos %d, quitados %d)'
    % (len(dentro_de_muro), sum(1 for d in dentro_de_muro if d['accion'].startswith('movido')),
       sum(1 for d in dentro_de_muro if d['accion'].startswith('quitado'))))
bpy.context.view_layer.update()

# --- v2 (A-r2-11): COPA sobre una calzada. despeje_final solo aparta el TRONCO del borde; un
# olivo en el terraplen de la subida al hotel tenia la copa a 0.54 m del asfalto (un coche pasaria
# a traves). Rayos hacia abajo desde los puntos de copa: si el primer impacto es una calzada a
# menos de su holgura (COPA_HOLGURA), el arbol se aparta 2-4 m de ella (mismas reglas que
# candidato_ok + tronco libre + copa libre) o se quita. Los arboles fijos (plazoleta, jardinera)
# solo se apuntan ---
copa_calzada = []
for ent in revisar_arriba:
    ob = ent[0]
    try:
        nombre = ob.name
    except ReferenceError:
        continue
    if not es_arbol(nombre) or nombre.startswith('VEG_roca'):
        continue
    pw = copa_mundo(ob)
    if not len(pw):
        continue
    plazo = nombre.startswith('VEG_plazoleta')
    peor = copa_sobre_calzada(pw, plazoleta=plazo)
    if peor is None:
        continue
    w = ob.matrix_world.translation.copy()
    reg = dict({'nombre': nombre, 'x': round(w.x, 2), 'y': round(w.y, 2), 'z': round(w.z, 2)}, **peor)
    if empieza(nombre, ARBOL_FIJO):
        reg['accion'] = 'aviso (arbol fijo de plaza o jardinera)'
        copa_calzada.append(reg)
        continue
    hund = hundimiento(nombre)
    alto = alto_arbol(ob)
    a = apoyo_arbol(w.x, w.y, w.z - hund)
    nuevo = None
    if a is not None:
        b0 = borde_pista(w.x, w.y)
        for dist in DIST_HUIDA:
            for ux, uy in rumbos_huida(w.x - peor['x'], w.y - peor['y'], a):
                x2, y2 = w.x + ux * dist, w.y + uy * dist
                a2 = candidato_ok(x2, y2, a, b0, alto, copa=(pw, plazo, w.x, w.y, w.z, hund))
                if a2 is None:
                    continue
                # (primero uno llano: con desnivel > DESNIVEL_MOVER la siguiente pasada lo volveria a mover)
                if nuevo is None or a2['desnivel'] < nuevo[2]['desnivel']:
                    nuevo = (x2, y2, a2)
                if a2['desnivel'] <= DESNIVEL_MOVER:
                    break
            if nuevo is not None:
                break
    if nuevo is None:
        reg['accion'] = 'quitado (sin sitio a %s m con la copa libre)' % '/'.join('%.0f' % d for d in DIST_HUIDA)
        quitados.append(dict(reg, motivo='copa a %.2f m sobre %s (minimo %.1f)' % (peor['holgura'], peor['calzada'], peor['minimo'])))
        f_ = familia(nombre)
        if f_ in por_familia:
            por_familia[f_]['quitados'] += 1
        quitar(ob)
    else:
        x2, y2, a2 = nuevo
        mw = ob.matrix_world.copy()
        mw.translation = Vector((x2, y2, a2['hz'] + hund))
        ob.matrix_world = mw
        ent[1] = 0.05 + a2['hc'] - (a2['hz'] + hund)
        reg['accion'] = 'movido %.1f m' % math.hypot(x2 - w.x, y2 - w.y)
        reg['a'] = [round(x2, 2), round(y2, 2), round(a2['hz'] + hund, 3)]
    copa_calzada.append(reg)
log('copas sobre una calzada: %d (movidos %d, quitados %d, avisos %d)'
    % (len(copa_calzada), sum(1 for d in copa_calzada if d['accion'].startswith('movido')),
       sum(1 for d in copa_calzada if d['accion'].startswith('quitado')),
       sum(1 for d in copa_calzada if d['accion'].startswith('aviso'))))
bpy.context.view_layer.update()

# --- autocomprobacion: nada apoyado puede tener soporte o calzada justo encima ---
bajo_superficie, atraviesa_voladizo = [], []
for ob, dz_ini in revisar_arriba:
    try:
        w = ob.matrix_world.translation      # (mundo: tambien vale para los hijos sueltos)
    except ReferenceError:
        continue                             # arbol quitado
    x, y = w.x, w.y
    z_ini = w.z + dz_ini
    alto = max(float(ob.dimensions.z), 0.0) if ob.type == 'MESH' else 0.0
    alcance = max(BAJO_SUP_M, alto - dz_ini)
    enc = superficie_encima(x, y, z_ini, alcance)
    if enc is None:
        continue
    h, nombre = enc
    reg = {'nombre': ob.name, 'x': round(x, 2), 'y': round(y, 2), 'z': round(w.z, 3),
           'superficie': nombre, 'altura_sobre_base': round(h + dz_ini, 2), 'alto_objeto': round(alto, 1)}
    # v2 (D2-03): un arbol con una calzada encima (pino bajo el tablero de una rampa) se QUITA
    if es_arbol(ob.name) and not empieza(ob.name, ARBOL_FIJO) and empieza(nombre, CALZ_TRONCO):
        quitados.append(dict(reg, motivo='bajo %s a %.2f m de la base (autocomprobacion)' % (nombre, h + dz_ini)))
        f_ = familia(ob.name)
        if f_ in por_familia:
            por_familia[f_]['quitados'] += 1
        quitar(ob)
        continue
    if h < BAJO_SUP_M:
        bajo_superficie.append(reg)
    else:
        atraviesa_voladizo.append(reg)
log('bajo superficie (< %.0f m encima de la base) %d, atraviesan un voladizo %d'
    % (BAJO_SUP_M, len(bajo_superficie), len(atraviesa_voladizo)))
for b in bajo_superficie[:30]:
    log('  BAJO %s' % json.dumps(b))


# ---------------------------------------------------------------- edificios
def huella_local(root):
    """(x0, y0, x1, y1) de la BASE en coordenadas locales de la raiz: vertices
    de la jerarquia (sin zocalos) con z local < 0.6; si no hay, toda la caja."""
    inv = root.matrix_world.inverted()
    base, todo = [], []
    for ob in [root] + list(root.children_recursive):
        if ob.type != 'MESH' or ob.name.startswith('CASAS_zocalo') or empieza(ob.name, OBST_NO):
            continue
        me = ob.data
        n = len(me.vertices)
        if n == 0:
            continue
        co = np.empty(n * 3, dtype=np.float64)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        mw = inv @ ob.matrix_world
        R = np.array([[mw[i][j] for j in range(3)] for i in range(3)])
        t = np.array([mw[0][3], mw[1][3], mw[2][3]])
        loc = co @ R.T + t
        todo.append(loc)
        sel = loc[loc[:, 2] < 0.6]
        if len(sel):
            base.append(sel)
    if not todo:
        return None
    pts = np.concatenate(base) if base else np.concatenate(todo)
    return (float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max()))


def fondo_zocalo(root):
    zs = []
    for c in root.children_recursive:
        if c.type == 'MESH' and c.name.startswith('CASAS_zocalo'):
            for b in c.bound_box:
                zs.append((c.matrix_world @ Vector(b)).z)
    return min(zs) if zs else None


edificios = []
enterradas, flotantes, sin_suelo = [], [], []
for ob in list(scene.collection.all_objects):
    if clasificar(ob) != 'edificio':
        continue
    hl = huella_local(ob)
    if hl is None:
        continue
    x0, y0, x1, y1 = hl
    mw = ob.matrix_world
    esquinas = [mw @ Vector((x0, y0, 0.0)), mw @ Vector((x1, y0, 0.0)),
                mw @ Vector((x1, y1, 0.0)), mw @ Vector((x0, y1, 0.0))]
    zoc = fondo_zocalo(ob)
    ent, flo, falta = 0.0, 0.0, 0
    ent_fach, ent_tras = 0.0, 0.0        # esquinas 2,3 = fachada (lado y1), 0,1 = trasera
    detalle = []
    for k, e in enumerate(esquinas):
        hits = impactos(e.x, e.y)
        if not hits:
            falta += 1
            detalle.append(None)
            continue
        tz, _ap = mejor_impacto(hits, e.z)
        detalle.append(round(tz - e.z, 2))
        ent = max(ent, tz - e.z)
        if k >= 2:
            ent_fach = max(ent_fach, tz - e.z)
        else:
            ent_tras = max(ent_tras, tz - e.z)
        ref = e.z - 0.6 if zoc is None else zoc - 0.3
        if tz < ref:
            flo = max(flo, (e.z if zoc is None else zoc) - tz)
    reg = {'nombre': ob.name, 'x': round(ob.location.x, 2), 'y': round(ob.location.y, 2),
           'z_base': round(ob.location.z, 2), 'zocalo': zoc is not None,
           'ancho': round(x1 - x0, 2), 'fondo': round(y1 - y0, 2),
           'esquinas': [[round(e.x, 2), round(e.y, 2), round(e.z, 2)] for e in esquinas],
           'desnivel_esquinas': detalle, 'enterrada_m': round(ent, 2),
           'enterrada_fachada_m': round(ent_fach, 2), 'enterrada_trasera_m': round(ent_tras, 2),
           'flotante_m': round(flo, 2)}
    edificios.append(reg)
    if ent > 1.2:
        enterradas.append(reg)
    if flo > 0.0:
        flotantes.append(reg)
    if falta:
        sin_suelo.append(reg)
log('edificios %d: enterrados (>1.2 m) %d, flotantes %d, esquinas sin suelo %d'
    % (len(edificios), len(enterradas), len(flotantes), len(sin_suelo)))

# --- bancales (italiano_kit.build_bancal: muro a lo largo de X local con la cara vista en y=0,
# relleno hasta y=-fondo a z=alto). Bien asentado = el pie del muro no vuela (terreno >= base
# - 0.1 en los extremos de la cara vista) y el relleno enrasa con la ladera de detras
# (|terreno - corona| < 0.5 en las 2 esquinas del fondo) (D2, C-05) ---
bancales = []
for ob in list(scene.collection.all_objects):
    if ob.parent is not None or not en_escena(ob) or not ob.name.startswith('ITAL_bancal'):
        continue
    L_ = float(ob.get('largo', 30.0))
    A_ = float(ob.get('alto', 1.6))
    F_ = float(ob.get('fondo', 7.0))
    mw = ob.matrix_world
    puntos = {'pie_izq': (-L_ / 2.0, 0.3, 0.0), 'pie_der': (L_ / 2.0, 0.3, 0.0), 'pie_centro': (0.0, 0.3, 0.0),
              'fondo_izq': (-L_ / 2.0, -F_ - 0.3, A_), 'fondo_der': (L_ / 2.0, -F_ - 0.3, A_)}
    desv, mal = {}, []
    for k, p in puntos.items():
        e = mw @ Vector(p)
        hits = [h for h in impactos(e.x, e.y) if not h[1].startswith('ITAL_bancal')]
        if not hits:
            desv[k] = None
            mal.append(k)
            continue
        tz, _ap = mejor_impacto(hits, e.z)
        desv[k] = round(tz - e.z, 2)
        if (k.startswith('pie') and tz < e.z - 0.1) or (k.startswith('fondo') and abs(tz - e.z) > 0.5):
            mal.append(k)
    # v3 (D2): TODO el borde de atras del relleno (9 puntos en y = -fondo), no solo las 2 esquinas: aire bajo la
    # corona <= BANC_AIRE_MAX (cara de tierra vista detras) y terreno sobre la corona <= 0.5
    atras = []
    for kk in range(9):
        e = mw @ Vector((-L_ / 2.0 + 0.4 + (L_ - 0.8) * kk / 8.0, -F_, A_))
        hits = [h for h in impactos(e.x, e.y) if not h[1].startswith('ITAL_bancal')]
        if hits:
            atras.append(round(e.z - mejor_impacto(hits, e.z)[0], 2))
    if atras and max(atras) > BANC_AIRE_MAX:
        mal.append('atras_volado')
    if atras and min(atras) < -0.5:
        mal.append('atras_enterrado')
    bancales.append({'nombre': ob.name, 'x': round(mw.translation.x, 2), 'y': round(mw.translation.y, 2),
                     'z': round(mw.translation.z, 2), 'largo': L_, 'alto': A_, 'fondo': F_,
                     'terreno_menos_punto': desv, 'aire_atras': atras, 'mal': mal, 'ok': not mal})
log('bancales %d: mal asentados %d' % (len(bancales), sum(1 for b in bancales if not b['ok'])))

# ---------------------------------------------------------------- salida
resumen = {
    'candidatos': n_cand, 'movidos': len(movidos),
    'flotaban_mas_0_6': sum(1 for m in movidos if m['dz'] < -UMBRAL_INFORME),
    'enterrados_mas_0_6': sum(1 for m in movidos if m['dz'] > UMBRAL_INFORME),
    'sin_impacto': len(sin_impacto),
    'fuera_del_terreno': sum(1 for s in sin_impacto if s['motivo'] == 'fuera_del_terreno'),
    'saltos': len(saltos), 'bajo_mar': len(bajo_mar), 'dudosos': len(dudosos),
    'no_movidos_junto_a_puente': sum(1 for d in dudosos if 'puente' in d.get('motivo', '')),
    'edificios': len(edificios), 'edificios_enterrados': len(enterradas),
    'edificios_enterrados_fachada': sum(1 for e in enterradas if e['enterrada_fachada_m'] > 1.2),
    'edificios_flotantes': len(flotantes), 'edificios_sin_suelo': len(sin_suelo),
    'informe_solo': len(informe_solo),
    'bajo_superficie': len(bajo_superficie), 'atraviesa_voladizo': len(atraviesa_voladizo),
    'arboles_desplazados_ladera': sum(1 for m in movidos if 'dxy' in m) + sum(1 for h in hijos_asentados if 'dxy' in h),
    'arboles_quitados': len(quitados), 'hijos_asentados': len(hijos_asentados),
    'dentro_de_muro': len(dentro_de_muro),
    'dentro_de_muro_quitados': sum(1 for d in dentro_de_muro if d['accion'].startswith('quitado')),
    'bancales': len(bancales), 'bancales_mal': sum(1 for b in bancales if not b['ok']),
    # v2 inspectores
    'losas_ajustadas': len(LOSAS_AJUSTADAS), 'losas_con_aire': sum(1 for r in LOSAS_AJUSTADAS if r['queda_aire']),
    'arboles_bajo_calzada_quitados': sum(1 for q in quitados if 'autocomprobacion' in q.get('motivo', '')
                                         or q.get('motivo', '').startswith('tronco en/bajo')),
    'junto_a_camino': len(junto_a_camino),
    'copa_calzada': len(copa_calzada),
    'copa_calzada_movidos': sum(1 for d in copa_calzada if d['accion'].startswith('movido')),
    'copa_calzada_quitados': sum(1 for d in copa_calzada if d['accion'].startswith('quitado')),
    'coches_asentados': len(coches_asentados),
    'coches_quitados': sum(1 for c in coches_quitados if c['estado'] != 'fila_vacia'),
    # v3 inspectores
    'terreno_nodos_v3': TERRENO_V3.get('nodos', 0),
    'losas_hierba_rebajada': sum(1 for r in TERRENO_V3.get('losas', []) if r['nodos']),
    'losas_hierba_restante': sum(1 for r in TERRENO_V3.get('losas', []) if r['pasada'] == 'despues de senderos'
                                 and r['hierba_despues'][0]) - sum(1 for r in TERRENO_V3.get('plazoletas_subidas', [])
                                                                    if r['hierba_despues'] <= 0.02),
    'plazoletas_subidas': len(TERRENO_V3.get('plazoletas_subidas', [])),
    'senderos_aire_025': sum((r['despues'] or {}).get('aire_025', 0) for r in TERRENO_V3.get('senderos', [])),
    'senderos_hierba_005': sum((r['despues'] or {}).get('hierba_005', 0) for r in TERRENO_V3.get('senderos', [])),
    'bancales_bajados': sum(1 for b in BANCALES_AJUSTE if b['accion'].startswith('bajado')),
    'bancales_quitados': sum(1 for b in BANCALES_AJUSTE if b['accion'].startswith('quitado')),
}
salida = {
    'blend': BLEND, 'geom': GEOM, 'fecha': time.strftime('%Y-%m-%d %H:%M'),
    'soporte': [r[2] for r in RANGOS], 'calzada': [r[2] for r in RANGOS_CALZ],
    'obstaculos': len(RANGOS_OBST), 'losas_macizas': {k: round(v, 2) for k, v in LOSA_FONDO.items()},
    'parametros': {'gap_apilado': GAP_APILADO, 'bajo_superficie_m': BAJO_SUP_M, 'holgura': HOLGURA,
                   'hundimiento': HUNDIMIENTO, 'r_anillo': R_ANILLO, 'desnivel_mover': DESNIVEL_MOVER,
                   'desnivel_max': DESNIVEL_MAX, 'paso_ladera': PASO_LADERA, 'off_tronco': OFF_TRONCO,
                   'triangulacion': 'loop_triangles', 'r_pisada': R_PISADA, 'dist_huida': DIST_HUIDA,
                   'copa_holgura': [list(c) for c in COPA_HOLGURA], 'coche_desnivel_max': COCHE_DESNIVEL_MAX,
                   'coche_libre': COCHE_LIBRE, 'losa_bajo_terreno': LOSA_BAJO_TERRENO,
                   'losa_canto_tope': LOSA_CANTO_TOPE, 'losa_ter_holgura': LOSA_TER_HOLGURA,
                   'losa_ter_margen': LOSA_TER_MARGEN, 'losa_ter_bajada_max': LOSA_TER_BAJADA_MAX, 'send_obj': SEND_OBJ, 'send_tol': SEND_TOL,
                   'send_hierba': SEND_HIERBA, 'send_talud': SEND_TALUD,
                   'send_subida_max': SEND_SUBIDA_MAX, 'send_subida_limite': SEND_SUBIDA_LIMITE,
                   'send_bajada_max': SEND_BAJADA_MAX, 'ter_pista_libre': TER_PISTA_LIBRE,
                   'banc_aire_max': BANC_AIRE_MAX, 'banc_tapa_max': BANC_TAPA_MAX},
    'resumen': resumen, 'por_familia': por_familia,
    'movidos': movidos, 'sin_impacto': sin_impacto, 'saltos': saltos, 'bajo_mar': bajo_mar,
    'dudosos': dudosos, 'informe_solo': informe_solo,
    'hijos_asentados': hijos_asentados, 'quitados': quitados, 'dentro_de_muro': dentro_de_muro,
    'bajo_superficie': bajo_superficie, 'atraviesa_voladizo': atraviesa_voladizo,
    'edificios': {'todos': edificios, 'enterrados': enterradas, 'flotantes': flotantes,
                  'sin_suelo': sin_suelo},
    'bancales': bancales,
    'losas': LOSAS_AJUSTADAS, 'junto_a_camino': junto_a_camino, 'copa_calzada': copa_calzada,
    'coches': coches_asentados, 'coches_quitados': coches_quitados,
    'terreno_v3': TERRENO_V3, 'bancales_ajuste': BANCALES_AJUSTE,
}
with open(OUT + '/asentar.json', 'w', encoding='utf-8') as f:
    json.dump(salida, f, indent=1, ensure_ascii=False)
log('resumen ' + json.dumps(resumen))
for fam in sorted(por_familia):
    log('  %-18s %s' % (fam, json.dumps(por_familia[fam])))
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
log('guardado %s (%.0f s)' % (BLEND, time.time() - t0))
