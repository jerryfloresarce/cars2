"""revisar_urbanismo.py - QA de URBANISMO de la escena integrada (ronda 15, T6).

  blender --background --factory-startup --python revisar_urbanismo.py
  env BLEND = .blend a revisar (defecto 03_blender/porto_corsa.blend; NO lo modifica)
  env GEOM  = geometria_3d.json (defecto 03_blender/geometria_3d.json)
  env URBANISMO = ruta de urbanismo.json (T2) para superponer el plan (opcional)

1. Exporta HUELLAS 2D a renders/qa/huellas.json:
   - casas/edificios: rectangulo rotado de la base (4 esquinas, fachada = lado
     +Y local del kit de casas: pivote en el centro de la fachada, cuerpo a -Y)
   - calles/caminos: eje (polilinea 3D) + ancho, deducidos de la cinta del
     caminos_kit (un anillo de perfil por frame; stride = vertices por anillo)
     y, solo con env URBANISMO, las calles/rampas/travesias de urbanismo.json (T2)
   - muros: puntos de la malla (celdas de 1 m) + eje si es cinta
   - pista y pit lane: muestras (x, y, w) de geometria_3d.json
   - arboles: punto + radio de copa;  props: punto + radio + rectangulo
2. Comprueba: casa-casa, casa-calle, casa-camino, casa-muro (<1 m delante de la
   fachada = 'muro tapa ventanas'; muro que atraviesa una casa), casa-pista
   (< 3 m fallo, < 6 m aviso; edificios de carrera: fallo solo si tocan el
   asfalto), casa-pit lane, arbol-casa, arbol-calle/camino, arbol-pista,
   prop-casa/pista/camino con el RECTANGULO del prop, caminos sin destino
   (extremo a > 6 m de otro camino/pista/edificio/plaza/muelle) y, leyendo
   renders/qa/asentar.json, flotantes/enterrados/fuera del terreno/bajo una
   superficie (objeto_bajo_superficie) y voladizos atravesados (aviso).
   v1 inspectores: ermita_desnivel (esquinas a +-0.5 m), bancal_mal_asentado, losa_tambor
   (CALLE_plaza* con canto > 1.3 m), losa_volada (aire bajo el borde), cipres_flotando/
   enterrado (hijos de hileras y ermitas, con la triangulacion del render) y, como aviso,
   los arboles que asentar tuvo que quitar o sacar de un muro.
   v2 inspectores: losa_tambor con el canto VISIBLE (corona - max(terreno, fondo)) y losa_volada
   arista a arista del fondo; plaza_muro (BVH losa/muro, N2); sendero_volado/sendero_enterrado
   (cara de arriba de CAMINO_tierra contra el terreno, C2-08); copa_sobre_calzada (arbol fijo) y
   avisos arbol_copa_apartada, arbol_junto_a_camino y coche_quitado_por_asentar (asentar.json).
   v3 inspectores: losa_hierba (terreno sobre la corona dentro de la cara de arriba de una losa, C-12);
   CALLE_plazoleta entra en losa_tambor/losa_volada/plaza_muro/losa_hierba; sendero_volado con aire
   > 0.25 m (antes 0.40) medido hasta el primer apoyo (terreno, terraplen, muro o losa); avisos
   bancal_bajado_por_asentar / bancal_quitado_por_asentar (D2).
3. Escribe renders/qa/urbanismo_informe.json: {'fallos': [{tipo, objeto, x, y,
   detalle}], 'avisos': [...], 'resumen': {tipo: n}}. El mapa lo dibuja
   revisar_urbanismo_plot.py (python del sistema).
Sin bpy.ops salvo abrir el fichero.
"""
import bisect
import json
import math
import os
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

BASE = 'E:/Escritorio/claude-pc/arnau-aseto-corsa'
DIR = BASE + '/03_blender'
BLEND = os.environ.get('BLEND', DIR + '/porto_corsa.blend')
GEOM = os.environ.get('GEOM', DIR + '/geometria_3d.json')
# urbanismo.json (T2) solo se superpone si se pide (env URBANISMO=ruta): sirve para
# revisar el PLAN contra la escena; por defecto se revisa SOLO lo que hay en el .blend
URB = os.environ.get('URBANISMO', '')
OUT = os.environ.get('QA_OUT', DIR + '/renders/qa')     # (QA_OUT: pruebas sobre copias)
os.makedirs(OUT, exist_ok=True)

# --- familias (prefijos de nombre; los clones llevan sufijo .001) ---
CASA_PREF = ('CASAS_', 'PENON_casa', 'PUEBLO_')              # fachada fiable (kit de casas)
EDIF_PREF = ('CIVICO_', 'HOTEL_root', 'AYTO_root', 'CAMPANILE_root', 'CASINO_root',
             'PENON_campanile', 'PENON_palazzo', 'ITAL_ermita', 'CARRERA_tribuna',
             'CARRERA_boxes', 'PIT_boxes', 'PIT_torre', 'CARRERA_pantalla', 'MIRADOR_parking')
# (CARRERA_portico cruza la pista a proposito y LOEWS_rotonda es parte del trazado: no son urbanismo)
SIN_HUELLA = ('CASAS_zocalo', 'ITAL_cipres', 'ITAL_olivo', 'VEG_', 'OLI_')   # hijos que no cuentan en la base
CALLE_PREF = ('CAMINO_asfalto', 'CAMINO_adoquin', 'CAMINO_tierra', 'CAMINO_muelle',
              'CALLE_calzada', 'CALLE_calle', 'CALLE_rampa', 'CALLE_travesia',
              'URB_calle', 'URB_rampa', 'URB_travesia', 'PPUEBLO_carretera', 'PENON_carretera')
MARGEN_CINTA = {'asfalto': 0.5, 'adoquin': 1.6, 'muelle': 0.7, 'tierra': 1.5}   # perfil - calzada
MURO_PREF = ('CAMINO_muro', 'MUROC_', 'PPUEBLO_muro', 'MIRADOR_muro', 'ITAL_bancal_muro',
             'URB_muro', 'CALLE_muro', 'PENON_muro')
ARBOL_PREF = ('VEG_', 'OLI_', 'ITAL_cipres', 'ITAL_olivo', 'MIRADOR_palmera', 'PENON_pino',
              'PENON_palmera', 'PENON_arbol')
ARBOL_NO = ('VEG_roca', 'VEG_jardinera')
PROP_PREF = ('CALLE_', 'CARRERA_paca', 'CARRERA_valla', 'CARRERA_muro', 'COCHE_', 'CAMINO_cartel',
             'CAMINO_valla', 'CAMARA_tierra', 'ITAL_fuente', 'ITAL_capitella', 'VEG_roca',
             'VEG_jardinera', 'MONT_pena', 'PIT_muro')
PROP_NO = ('CALLE_guirnalda', 'CALLE_plaza', 'CALLE_plazoleta')   # (losas de suelo: destino de calles, no mobiliario)
DESTINO_PREF = ('PPUEBLO_', 'MIRADOR_paseo', 'MIRADOR_parking', 'PUERTO_pantalan', 'PUERTO_dique',
                'LOEWS_rotonda', 'PIT_LANE', 'TUNEL_suelo', 'PENON_plaza', 'PENON_meseta',
                'PENON_carretera', 'PENON_terraza', 'PENON_cala', 'CASINO_', 'CALLE_plaza', 'CALLE_plazoleta',
                'PENON_puente_plaza', 'PENON_puente_muelle', 'PENON_plazas')

# --- umbrales (m) ---
TOL_CASA_CASA = 0.3        # solape minimo en TODOS los ejes del SAT para contar
TOL_PROP = 0.3             # un prop (rectangulo de su caja) entra > 0.3 m en casa/asfalto/camino: fallo
MURO_TAPA = 1.0            # muro a < 1 m delante de la fachada (plan T6: 'tapa ventanas')
MURO_AVISO = 3.0           # aviso: muro a < 3 m delante de la fachada (contrato T2)
# casa/edificio a < CASA_PISTA del borde del asfalto: fallo (env CASA_PISTA_M=6 cuando T7
# integre urbanismo.json y los solares esten a w/2+6); entre CASA_PISTA y el margen del
# contrato (urbanismo_spec ancho_margen_pista = 6): aviso
CASA_PISTA = float(os.environ.get('CASA_PISTA_M', 3.0))
SPEC = DIR + '/urbanismo_spec.json'
CASA_PISTA_AVISO = float(json.load(open(SPEC, encoding='utf-8')).get('ancho_margen_pista', 6.0)) if os.path.exists(SPEC) else 6.0
# edificios de carrera (tribunas, boxes, torre, pantalla) estan junto a la pista a proposito:
# fallo solo si tocan el asfalto (< 0.5 m), aviso a < 3 m
CARRERA_PREF = ('CARRERA_tribuna', 'CARRERA_boxes', 'PIT_boxes', 'PIT_torre', 'CARRERA_pantalla')
CARRERA_PISTA = 0.5
CARRERA_PISTA_AVISO = 3.0
DESTINO_R = 6.0
# v1 inspectores: ermitas en plataforma (J N1), losas de plaza (C-04/B7: tambor; G7: volada)
ERMITA_TOL = 0.5           # terreno - base en cada esquina de una ermita
LOSA_CANTO_MAX = 1.3       # canto VISIBLE maximo de una CALLE_plaza* (corona - max(terreno, fondo))
LOSA_HUECO_MAX = 0.1       # aire maximo entre el fondo de la losa y el terreno a lo largo del borde
# v2 inspectores: muros que cruzan una plaza (N2) y senderos de tierra despegados del terreno (C2-08)
PLAZA_MURO_FALLO = 5       # pares de triangulos losa/muro (con el muro por encima del terreno): >= fallo, 1-4 aviso
SENDERO_AIRE_MAX = 0.25    # cara de arriba - apoyo (v3, N1: criterio del revisor; antes 0.40 'la falda lo tapa')
SENDERO_HIERBA_MAX = 0.15  # terreno - cara de arriba (hierba asomando por la cinta)
SENDERO_PREF = ('CAMINO_tierra',)
# v3: lo que puede sostener el borde de un sendero ademas del terreno (terraplen o muro de mamposteria del
# integrador, losas y calles en los empalmes): el aire se mide hasta la primera de estas bajo la cara
SENDERO_APOYO_PREF = ('CAMINO_terraplen', 'CAMINO_muro', 'MUROC_', 'ITAL_bancal', 'CALLE_plaza', 'CALLE_plazoleta',
                      'PPUEBLO_', 'CAMINO_calle', 'CAMINO_escalera', 'CAMINO_adoquin', 'CAMINO_asfalto', 'CAMINO_rampa',
                      'CAMINO_enlace', 'CAMINO_travesia')
LOSA_PREF_QA = ('CALLE_plaza', 'CALLE_plazoleta')   # (v3: 'CALLE_plazoleta' no empieza por 'CALLE_plaza')
LOSA_HIERBA_MAX = 0.02     # v3 (C-12): terreno por encima de la corona dentro de la cara de arriba de una losa
LOSA_HIERBA_MARGEN = 0.5   # ...a >= 0.5 m de su borde (como asentar_objetos.LOSA_TER_MARGEN)


def log(msg):
    print('[urbanismo] ' + str(msg))


t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
LIBc = bpy.data.collections.get('LIB')
EN_LIB = set(o.name for o in LIBc.all_objects) if LIBc else set()
G = json.load(open(GEOM, encoding='utf-8'))
S = G['muestras']
N = len(S)
PIT = G.get('pit_lane') or []
T = G['terreno']
# ronda 15: el integrador talla EXPLANADAS en la malla TERRENO (tribunas, hotel, ayuntamiento,
# plazuelas): la cota real es la de la malla, no la del JSON
_ter_m = bpy.data.objects.get('TERRENO')
# F1 r4 (PARCHES_F1_mascara.md R4.4 A9): '>=' y solo los nx*ny primeros: tras banda_terreno_2m.py (ultimo paso del pipeline)
# el TERRENO lleva +45 k vertices de la banda de 2 m AL FINAL; la rejilla conserva sus indices j*nx+i
if _ter_m is not None and _ter_m.type == 'MESH' and len(_ter_m.data.vertices) >= T['nx'] * T['ny']:
    _co = [0.0] * (3 * len(_ter_m.data.vertices))
    _ter_m.data.vertices.foreach_get('co', _co)
    T = dict(T)
    T['z'] = _co[2::3][:T['nx'] * T['ny']]


def empieza(nombre, prefijos):
    return any(nombre.startswith(p) for p in prefijos)


def raiz_de(ob):
    while ob.parent is not None:
        ob = ob.parent
    return ob


def objetos_escena(solo_raices=True):
    for ob in scene.collection.all_objects:
        if ob.name in EN_LIB:
            continue
        if solo_raices and ob.parent is not None:
            continue
        yield ob


def verts_mundo(ob):
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    mw = ob.matrix_world
    R = np.array([[mw[i][j] for j in range(3)] for i in range(3)])
    t = np.array([mw[0][3], mw[1][3], mw[2][3]])
    return co @ R.T + t


def huella_local(root, z_max=0.6, sin=('CASAS_zocalo',)):
    """(x0, y0, x1, y1) de la base en coordenadas locales de la raiz (vertices
    con z local < z_max; si no hay, toda la caja)."""
    inv = root.matrix_world.inverted()
    base, todo = [], []
    for ob in [root] + list(root.children_recursive):
        if ob.type != 'MESH' or ob.name.startswith(sin) or len(ob.data.vertices) == 0:
            continue
        me = ob.data
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        mw = inv @ ob.matrix_world
        R = np.array([[mw[i][j] for j in range(3)] for i in range(3)])
        t = np.array([mw[0][3], mw[1][3], mw[2][3]])
        loc = co @ R.T + t
        todo.append(loc)
        sel = loc[loc[:, 2] < z_max]
        if len(sel):
            base.append(sel)
    if not todo:
        return None
    pts = np.concatenate(base) if base else np.concatenate(todo)
    return (float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max()))


def rect_de(root, hl):
    """Rectangulo rotado en mundo: esquinas (x0,y0),(x1,y0),(x1,y1),(x0,y1) y
    marco {cx, cy, ux, uy, vx, vy, hu, hv}; la fachada es el lado y1 (2->3)."""
    x0, y0, x1, y1 = hl
    mw = root.matrix_world
    e = [mw @ Vector((x0, y0, 0.0)), mw @ Vector((x1, y0, 0.0)),
         mw @ Vector((x1, y1, 0.0)), mw @ Vector((x0, y1, 0.0))]
    cx = sum(p.x for p in e) / 4.0
    cy = sum(p.y for p in e) / 4.0
    ux, uy = e[1].x - e[0].x, e[1].y - e[0].y
    lu = math.hypot(ux, uy) or 1.0
    vx, vy = e[3].x - e[0].x, e[3].y - e[0].y
    lv = math.hypot(vx, vy) or 1.0
    return {'esq': [[round(p.x, 3), round(p.y, 3)] for p in e], 'cx': cx, 'cy': cy,
            'ux': ux / lu, 'uy': uy / lu, 'vx': vx / lv, 'vy': vy / lv,
            'hu': lu / 2.0, 'hv': lv / 2.0, 'z': [round(p.z, 2) for p in e]}


# ---------------------------------------------------------------- huellas
def anillos_cinta(ob):
    """Anillos de perfil de una cinta del caminos_kit: la malla empieza con un anillo de `stride`
    vertices por frame y quads (a+j, b+j, b+j+1, a+j+1). Devuelve los vertices de mundo de los
    anillos (n_frames x stride x 3) o None (los adornos sueltos que van detras no cuentan)."""
    me = ob.data
    if len(me.polygons) < 2:
        return None
    f0 = tuple(me.polygons[0].vertices)
    if len(f0) != 4:
        return None
    stride = f0[1] - f0[0]
    if stride < 2 or f0[3] != f0[0] + 1 or f0[2] != f0[1] + 1:
        return None
    n_max = 0
    for p in me.polygons:
        v = tuple(p.vertices)
        if len(v) != 4 or v[1] - v[0] != stride or v[3] != v[0] + 1 or v[2] != v[1] + 1:
            break
        n_max = max(n_max, v[2] + 1)
    n_frames = n_max // stride
    if n_frames < 2:
        return None
    return verts_mundo(ob)[:n_frames * stride].reshape(n_frames, stride, 3)


def eje_cinta(ob):
    """Eje y ancho de una cinta del caminos_kit (ver anillos_cinta). Devuelve
    (eje Nx3 en mundo, extension media del perfil) o None."""
    co = anillos_cinta(ob)
    if co is None:
        return None
    eje = (co[:, 0, :] + co[:, -1, :]) / 2.0
    eje[:, 2] = co[:, :, 2].max(axis=1)
    ext = np.hypot(co[:, 0, 0] - co[:, -1, 0], co[:, 0, 1] - co[:, -1, 1])
    return eje, float(np.median(ext))


def tipo_de(nombre):
    base = nombre.split('.')[0]
    return base.split('_', 1)[1] if '_' in base else base


def bbox_jerarquia_local(root):
    """Caja (x0,y0,x1,y1) de toda la jerarquia en coordenadas locales de la raiz."""
    inv = root.matrix_world.inverted()
    xs, ys = [], []
    for ob in [root] + list(root.children_recursive):
        if ob.type != 'MESH':
            continue
        for c in ob.bound_box:
            l = inv @ (ob.matrix_world @ Vector(c))
            xs.append(l.x)
            ys.append(l.y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


casas, calles, muros, arboles, props, destinos_pts = [], [], [], [], [], []
# --- casas y edificios ---
for ob in objetos_escena():
    if ob.type not in ('MESH', 'EMPTY'):
        continue
    if empieza(ob.name, CASA_PREF):
        tipo = 'casa'
    elif empieza(ob.name, EDIF_PREF):
        tipo = 'edificio'
    else:
        continue
    hl = huella_local(ob, sin=SIN_HUELLA)
    if hl is None:
        continue
    r = rect_de(ob, hl)
    f = ob.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
    lf = math.hypot(f.x, f.y) or 1.0
    zoc = any(c.name.startswith('CASAS_zocalo') for c in ob.children_recursive)
    r.update({'nombre': ob.name, 'tipo': tipo, 'fx': f.x / lf, 'fy': f.y / lf,
              'fachada_fiable': tipo == 'casa', 'zocalo': zoc,
              'ancho': round(2 * r['hu'], 2), 'fondo': round(2 * r['hv'], 2),
              'z_base': round(ob.matrix_world.translation.z, 2)})
    casas.append(r)
log('casas/edificios: %d' % len(casas))

# --- calles y caminos (cintas del kit + urbanismo.json si existe) ---
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not empieza(ob.name, CALLE_PREF):
        continue
    ec = eje_cinta(ob)
    tipo = tipo_de(ob.name)
    if ec is None:
        log('calle %s: no es cinta del kit, se omite' % ob.name)
        continue
    eje, ext = ec
    ancho = max(1.5, ext - MARGEN_CINTA.get(tipo, 0.5))
    calles.append({'nombre': ob.name, 'tipo': tipo, 'fuente': 'malla', 'ancho': round(ancho, 2),
                   'eje': [[round(float(x), 2), round(float(y), 2), round(float(z), 2)] for x, y, z in eje]})


def _polilineas(obj, ancho_def):
    """Lee tolerante listas de puntos [x,y(,z)] con 'ancho' de urbanismo.json."""
    res = []
    if isinstance(obj, dict):
        pts = obj.get('pts') or obj.get('puntos') or obj.get('polilinea') or obj.get('eje')
        if pts and isinstance(pts[0], (list, tuple)) and len(pts[0]) >= 2:
            res.append((pts, float(obj.get('ancho', ancho_def))))
        else:
            for v in obj.values():
                res.extend(_polilineas(v, ancho_def))
    elif isinstance(obj, list) and obj:
        if isinstance(obj[0], (list, tuple)) and len(obj[0]) >= 2 and not isinstance(obj[0][0], (list, tuple, dict)):
            res.append((obj, ancho_def))
        else:
            for v in obj:
                res.extend(_polilineas(v, ancho_def))
    return res


if URB and os.path.exists(URB):
    U = json.load(open(URB, encoding='utf-8'))
    sectores = U.get('sectores', U) if isinstance(U, dict) else {}
    n_u = 0
    for sid, sec in (sectores.items() if isinstance(sectores, dict) else enumerate(sectores)):
        if not isinstance(sec, dict):
            continue
        for clave, ancho_def in (('calles', 4.5), ('travesias', 4.5), ('rampas', 4.5), ('escaleras', 1.6)):
            for k, (pts, ancho) in enumerate(_polilineas(sec.get(clave), ancho_def)):
                calles.append({'nombre': 'URB_%s_%s_%d' % (clave, sid, k), 'tipo': clave, 'fuente': 'urbanismo.json',
                               'ancho': ancho, 'eje': [[float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0] for p in pts]})
                n_u += 1
        for k, (pts, _a) in enumerate(_polilineas(sec.get('muros'), 0.5)):
            muros.append({'nombre': 'URB_muro_%s_%d' % (sid, k), 'fuente': 'urbanismo.json',
                          'eje': [[float(p[0]), float(p[1])] for p in pts], 'celdas': [], 'puntos': [[float(p[0]), float(p[1])] for p in pts]})
    log('urbanismo.json: %d polilineas de calles' % n_u)
log('calles/caminos: %d' % len(calles))

# --- muros: celdas de 1 m de la malla (+ eje si es cinta del kit) ---
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not empieza(ob.name, MURO_PREF):
        continue
    co = verts_mundo(ob)
    if len(co) == 0:
        continue
    paso = max(1, len(co) // 4000)
    sub = co[::paso]
    celdas = sorted(set((int(math.floor(x)), int(math.floor(y))) for x, y in co[:, :2]))
    reg = {'nombre': ob.name, 'fuente': 'malla', 'eje': [],
           'celdas': [[cx + 0.5, cy + 0.5] for cx, cy in celdas],
           'puntos': [[round(float(x), 2), round(float(y), 2)] for x, y in sub[:, :2]]}
    ec = eje_cinta(ob)
    if ec is not None:
        reg['eje'] = [[round(float(x), 2), round(float(y), 2)] for x, y, _z in ec[0]]
    muros.append(reg)
log('muros: %d' % len(muros))

# --- pista y pit lane ---
pista = [[round(q['x'], 2), round(q['y'], 2), q['w'], round(q['z'], 2), q.get('sec', '')] for q in S]
pit_lane = [[round(q['x'], 2), round(q['y'], 2), q.get('w', 3.0), round(q.get('z', 0.0), 2)] for q in PIT]

# --- arboles (cualquier nivel; no los de assets de roca ni del coche) ---
NO_ARBOL_RAIZ = ('PPUEBLO_', 'PENON_cara', 'PENON_puente', 'TUNEL_', 'MCOCHE_', 'MONT_')
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not empieza(ob.name, ARBOL_PREF) or empieza(ob.name, ARBOL_NO):
        continue
    if empieza(raiz_de(ob).name, NO_ARBOL_RAIZ):
        continue
    p = ob.matrix_world.translation
    d = ob.dimensions
    arboles.append({'nombre': ob.name, 'fam': tipo_de(ob.name).split('_')[0], 'x': round(p.x, 2),
                    'y': round(p.y, 2), 'z': round(p.z, 2), 'r': round(max(d.x, d.y) / 2.0, 2),
                    'alto': round(d.z, 1)})
log('arboles: %d' % len(arboles))

# --- props: raices de mobiliario, pacas, vallas, coches, carteles, rocas... ---
for ob in objetos_escena():
    if ob.type not in ('MESH', 'EMPTY') or not empieza(ob.name, PROP_PREF) or empieza(ob.name, PROP_NO):
        continue
    hl = bbox_jerarquia_local(ob)
    if hl is None:
        continue
    r = rect_de(ob, hl)
    p = ob.matrix_world.translation
    props.append({'nombre': ob.name, 'fam': tipo_de(ob.name).split('_')[0], 'x': round(p.x, 2),
                  'y': round(p.y, 2), 'z': round(p.z, 2), 'r': round(max(r['hu'], r['hv']), 2),
                  'esq': r['esq'], 'cx': r['cx'], 'cy': r['cy'], 'ux': r['ux'], 'uy': r['uy'],
                  'vx': r['vx'], 'vy': r['vy'], 'hu': r['hu'], 'hv': r['hv']})
log('props: %d' % len(props))

# --- destinos de caminos (plazas, muelles, pantalanes, paseos...) ---
DEST_CAJAS = []
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not empieza(ob.name, DESTINO_PREF):
        continue
    if 'veg' in ob.name.lower() or 'roca' in ob.name.lower():
        continue
    co = verts_mundo(ob)
    paso = max(1, len(co) // 1500)
    destinos_pts.extend((float(x), float(y), ob.name) for x, y in co[::paso, :2])
    if len(co) <= 200:            # losas pequenas (plazas, aparcamientos): tambien su interior
        _bb = [ob.matrix_world.inverted() @ ob.matrix_world @ Vector(c) for c in ob.bound_box]
        DEST_CAJAS.append((ob.matrix_world.inverted(), min(v.x for v in _bb), max(v.x for v in _bb),
                           min(v.y for v in _bb), max(v.y for v in _bb)))
log('puntos de destino: %d' % len(destinos_pts))

# --- rocas (solo contexto del mapa: celdas de 4 m de las mallas de roca que
# SOBRESALEN del terreno; las bases enterradas de penas/cordillera no se dibujan) ---
ROCA_PREF = ('PPUEBLO_roca', 'TUNEL_acantilado', 'MCOCHE_roca', 'PENON_roca', 'MONT_pena', 'MONT_cordal', 'MONT_pico')
_ZT = np.array(T['z'], dtype=float).reshape(T['ny'], T['nx'])


def z_terreno(co):
    """z de la rejilla del terreno (celda mas cercana) para puntos Nx2; fuera de la
    rejilla +1e9 (no hay suelo: esa roca no se dibuja como contexto)."""
    i = np.rint((co[:, 0] - T['x0']) / T['cell']).astype(int)
    j = np.rint((co[:, 1] - T['y0']) / T['cell']).astype(int)
    ok = (i >= 0) & (i < T['nx']) & (j >= 0) & (j < T['ny'])
    z = np.full(len(co), 1e9)
    z[ok] = _ZT[j[ok], i[ok]]
    return z


rocas = []
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not empieza(ob.name, ROCA_PREF):
        continue
    co = verts_mundo(ob)
    co = co[co[:, 2] > z_terreno(co[:, :2]) + 0.3]
    celdas = sorted(set((int(math.floor(x / 4.0)), int(math.floor(y / 4.0))) for x, y in co[:, :2]))
    rocas.append({'nombre': ob.name, 'celda_m': 4.0, 'celdas': [[4.0 * cx + 2.0, 4.0 * cy + 2.0] for cx, cy in celdas]})
log('rocas: %d' % len(rocas))


# ---------------------------------------------------------------- geometria 2D
def d_pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _orient(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def d_seg_seg(a, b, c, d):
    if _orient(a, b, c) * _orient(a, b, d) < 0 and _orient(c, d, a) * _orient(c, d, b) < 0:
        return 0.0
    return min(d_pt_seg(a[0], a[1], c[0], c[1], d[0], d[1]), d_pt_seg(b[0], b[1], c[0], c[1], d[0], d[1]),
               d_pt_seg(c[0], c[1], a[0], a[1], b[0], b[1]), d_pt_seg(d[0], d[1], a[0], a[1], b[0], b[1]))


def rect_local(r, x, y):
    dx, dy = x - r['cx'], y - r['cy']
    return dx * r['ux'] + dy * r['uy'], dx * r['vx'] + dy * r['vy']


def rect_contiene(r, x, y, m=0.0):
    u, v = rect_local(r, x, y)
    return abs(u) <= r['hu'] + m and abs(v) <= r['hv'] + m


def d_pt_rect(r, x, y):
    u, v = rect_local(r, x, y)
    return math.hypot(max(abs(u) - r['hu'], 0.0), max(abs(v) - r['hv'], 0.0))


def d_rect_seg(r, a, b):
    if rect_contiene(r, a[0], a[1]) or rect_contiene(r, b[0], b[1]):
        return 0.0
    e = r['esq']
    return min(d_seg_seg(e[i], e[(i + 1) % 4], a, b) for i in range(4))


def solape_sat(r1, r2):
    """Minimo solape proyectado sobre los 4 ejes de los dos rectangulos (<= 0 = separados)."""
    m = 1e9
    for r in (r1, r2):
        for ax, ay in ((r['ux'], r['uy']), (r['vx'], r['vy'])):
            p1 = [e[0] * ax + e[1] * ay for e in r1['esq']]
            p2 = [e[0] * ax + e[1] * ay for e in r2['esq']]
            m = min(m, min(max(p1), max(p2)) - max(min(p1), min(p2)))
    return m


def kd_de(puntos):
    kd = KDTree(len(puntos))
    for i, p in enumerate(puntos):
        kd.insert(Vector((p[0], p[1], 0.0)), i)
    kd.balance()
    return kd


def cerca(kd, x, y, r):
    return kd.find_range(Vector((x, y, 0.0)), r) if kd is not None else []


KD_P = kd_de(pista)
KD_PIT = kd_de(pit_lane) if pit_lane else None
SEGS = []
for ci, c in enumerate(calles):
    eje = c['eje']
    for k in range(len(eje) - 1):
        SEGS.append((eje[k][:2], eje[k + 1][:2], c['ancho'] / 2.0, ci))
KD_SEG = kd_de([((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b, _h, _c in SEGS]) if SEGS else None
R_SEG = (max(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b, _h, _c in SEGS) / 2 + max(c['ancho'] for c in calles) / 2 + 1.0) if SEGS else 0.0
KD_CASA = kd_de([(c['cx'], c['cy']) for c in casas]) if casas else None
R_CASA = (max(math.hypot(c['hu'], c['hv']) for c in casas) + 1.0) if casas else 0.0
MURO_PTS = [(x, y, mi) for mi, m in enumerate(muros) for x, y in m['puntos']]
KD_MURO = kd_de(MURO_PTS) if MURO_PTS else None
KD_DEST = kd_de(destinos_pts) if destinos_pts else None


def d_borde(kd, lista, x, y):
    """Distancia al borde del asfalto (negativa = dentro) y muestra mas cercana."""
    _co, i, d = kd.find(Vector((x, y, 0.0)))
    return d - lista[i][2] / 2.0, i


def d_rect_pista(r, lista, kd):
    """Distancia minima del rectangulo al borde del asfalto a lo largo de las
    muestras vecinas (negativa = solape)."""
    _co, i0, _d = kd.find(Vector((r['cx'], r['cy'], 0.0)))
    n = len(lista)
    mejor = 1e9
    for k in range(i0 - 14, i0 + 14):
        a, b = lista[k % n], lista[(k + 1) % n]
        if n < 200 and not (0 <= k < n - 1):
            continue
        mejor = min(mejor, d_rect_seg(r, a[:2], b[:2]) - (a[2] + b[2]) / 4.0)
    return mejor


# ---------------------------------------------------------------- comprobaciones
fallos, avisos = [], []


def fallo(tipo, objeto, x, y, detalle):
    fallos.append({'tipo': tipo, 'objeto': objeto, 'x': round(float(x), 1), 'y': round(float(y), 1), 'detalle': detalle})


def aviso(tipo, objeto, x, y, detalle):
    avisos.append({'tipo': tipo, 'objeto': objeto, 'x': round(float(x), 1), 'y': round(float(y), 1), 'detalle': detalle})


def tipo_calle(c):
    return 'calle' if (c['fuente'] == 'urbanismo.json' or c['tipo'] in ('calzada', 'calle', 'rampa', 'travesia', 'escaleras')) else 'camino'


for i, r in enumerate(casas):
    diag = math.hypot(r['hu'], r['hv'])
    # casa - casa
    for _co, j, _d in cerca(KD_CASA, r['cx'], r['cy'], diag + R_CASA):
        if j <= i:
            continue
        s = solape_sat(r, casas[j])
        if s > TOL_CASA_CASA:
            fallo('casa_casa', r['nombre'], (r['cx'] + casas[j]['cx']) / 2, (r['cy'] + casas[j]['cy']) / 2,
                  'solapa %.1f m con %s' % (s, casas[j]['nombre']))
    # casa - calle / camino
    peor = {}
    for _co, k, _d in cerca(KD_SEG, r['cx'], r['cy'], diag + R_SEG):
        a, b, h, ci = SEGS[k]
        dd = d_rect_seg(r, a, b)
        pen = h - 0.1 - dd
        if pen > 0 and pen > peor.get(ci, (0, 1))[0]:
            peor[ci] = (pen, dd)
    for ci, (pen, dd) in peor.items():
        if dd <= 0.0:
            det = 'el EJE de %s pasa por dentro de la casa' % calles[ci]['nombre']
        else:
            det = '%s entra %.1f m en la casa' % (calles[ci]['nombre'], pen)
        fallo('casa_' + tipo_calle(calles[ci]), r['nombre'], r['cx'], r['cy'], det)
    # casa - pista / pit lane (edificios de carrera: solo si tocan el asfalto)
    de_carrera = empieza(r['nombre'], CARRERA_PREF)
    lim_f, lim_a = (CARRERA_PISTA, CARRERA_PISTA_AVISO) if de_carrera else (CASA_PISTA, CASA_PISTA_AVISO)
    dp = d_rect_pista(r, pista, KD_P)
    if dp < lim_f:
        fallo('casa_pista', r['nombre'], r['cx'], r['cy'], 'a %.1f m del borde del asfalto (minimo %.1f)' % (dp, lim_f))
    elif dp < lim_a:
        aviso('casa_pista_cerca', r['nombre'], r['cx'], r['cy'], 'a %.1f m del asfalto (%s: %.0f)'
              % (dp, 'edificio de carrera' if de_carrera else 'contrato', lim_a))
    if KD_PIT is not None:
        dq = d_rect_pista(r, pit_lane, KD_PIT)
        if dq < lim_f:
            fallo('casa_pitlane', r['nombre'], r['cx'], r['cy'], 'a %.1f m del pit lane (minimo %.1f)' % (dq, lim_f))
    # casa - muro: delante de la fachada (tapa ventanas) o atravesando la casa
    e = r['esq']
    fcx, fcy = (e[2][0] + e[3][0]) / 2.0, (e[2][1] + e[3][1]) / 2.0
    tapa, aviso_m, cruza = {}, {}, {}
    for _co, k, _d in cerca(KD_MURO, r['cx'], r['cy'], diag + MURO_AVISO + 1.0):
        px, py, mi = MURO_PTS[k]
        if rect_contiene(r, px, py, -0.25):
            cruza[mi] = cruza.get(mi, 0) + 1
            continue
        if not r['fachada_fiable']:
            continue
        v = (px - fcx) * r['fx'] + (py - fcy) * r['fy']
        u = (px - fcx) * r['ux'] + (py - fcy) * r['uy']
        if abs(u) < r['hu'] + 0.3 and -0.3 < v:
            if v < MURO_TAPA:
                tapa[mi] = min(tapa.get(mi, 9), v)
            elif v < MURO_AVISO:
                aviso_m[mi] = min(aviso_m.get(mi, 9), v)
    for mi, v in tapa.items():
        # se apunta aunque el mismo muro tambien atraviese la casa: son dos defectos distintos
        fallo('casa_muro', r['nombre'], fcx, fcy, '%s a %.1f m delante de la fachada (tapa ventanas)%s'
              % (muros[mi]['nombre'], max(v, 0), ' y ademas la atraviesa' if mi in cruza else ''))
    for mi, n in cruza.items():
        fallo('muro_atraviesa_casa', r['nombre'], r['cx'], r['cy'], '%s atraviesa la casa (%d vertices dentro)' % (muros[mi]['nombre'], n))
    for mi, v in aviso_m.items():
        if mi not in tapa:
            aviso('casa_muro_3m', r['nombre'], fcx, fcy, '%s a %.1f m delante de la fachada (contrato: 3)' % (muros[mi]['nombre'], v))

for a in arboles:
    x, y = a['x'], a['y']
    for _co, j, _d in cerca(KD_CASA, x, y, R_CASA + 1.0):
        if rect_contiene(casas[j], x, y, 0.3):
            fallo('arbol_casa', a['nombre'], x, y, 'tronco dentro de %s' % casas[j]['nombre'])
    d, _i = d_borde(KD_P, pista, x, y)
    if d < 0.3:
        fallo('arbol_pista', a['nombre'], x, y, 'tronco a %.1f m del borde del asfalto' % d)
    if KD_PIT is not None:
        d, _i = d_borde(KD_PIT, pit_lane, x, y)
        if d < 0.3:
            fallo('arbol_pitlane', a['nombre'], x, y, 'tronco a %.1f m del pit lane' % d)
    hecho = set()
    for _co, k, _d in cerca(KD_SEG, x, y, R_SEG + 1.0):
        sa, sb, h, ci = SEGS[k]
        if ci not in hecho and d_pt_seg(x, y, sa[0], sa[1], sb[0], sb[1]) < h + 0.2:
            hecho.add(ci)
            fallo('arbol_' + tipo_calle(calles[ci]), a['nombre'], x, y, 'tronco sobre %s' % calles[ci]['nombre'])

# props: con el RECTANGULO de su caja (vallas de 10 m, filas de coches, toldos, muros-valla),
# no solo con el pivote. MONT_pena (penas sueltas de 30-40 m, se van en T7) solo va al mapa.
for p in props:
    x, y = p['x'], p['y']
    if p['nombre'].startswith('MONT_pena'):
        continue
    diag = math.hypot(p['hu'], p['hv'])
    for _co, j, _d in cerca(KD_CASA, x, y, R_CASA + diag + 1.0):
        s = solape_sat(p, casas[j])
        if s > TOL_PROP:
            fallo('prop_casa', p['nombre'], x, y, 'entra %.1f m en %s' % (s, casas[j]['nombre']))
    dp = d_rect_pista(p, pista, KD_P)
    if dp < -TOL_PROP:
        fallo('prop_pista', p['nombre'], x, y, '%.1f m dentro del asfalto' % -dp)
    if KD_PIT is not None and d_rect_pista(p, pit_lane, KD_PIT) < -TOL_PROP:
        fallo('prop_pitlane', p['nombre'], x, y, '%.1f m dentro del pit lane' % -d_rect_pista(p, pit_lane, KD_PIT))
    if p['nombre'].startswith('CAMINO_valla'):
        continue      # la valla de cierre cruza la boca del camino a proposito
    peor = {}
    for _co, k, _d in cerca(KD_SEG, x, y, R_SEG + diag + 1.0):
        sa, sb, h, ci = SEGS[k]
        pen = h - d_rect_seg(p, sa, sb)
        if pen > TOL_PROP and pen > peor.get(ci, 0.0):
            peor[ci] = pen
    for ci, pen in peor.items():
        fallo('prop_' + tipo_calle(calles[ci]), p['nombre'], x, y, 'entra %.1f m en %s' % (pen, calles[ci]['nombre']))

for ci, c in enumerate(calles):
    for extremo in (c['eje'][0], c['eje'][-1]):
        x, y = extremo[0], extremo[1]
        ok = d_borde(KD_P, pista, x, y)[0] < DESTINO_R
        if not ok and KD_PIT is not None:
            ok = d_borde(KD_PIT, pit_lane, x, y)[0] < DESTINO_R
        if not ok:
            for _co, k, _d in cerca(KD_SEG, x, y, DESTINO_R + R_SEG):
                sa, sb, h, cj = SEGS[k]
                if cj != ci and d_pt_seg(x, y, sa[0], sa[1], sb[0], sb[1]) < DESTINO_R + h:
                    ok = True
                    break
        if not ok:
            ok = any(d_pt_rect(casas[j], x, y) < DESTINO_R for _co, j, _d in cerca(KD_CASA, x, y, R_CASA + DESTINO_R))
        if not ok:
            ok = bool(cerca(KD_DEST, x, y, DESTINO_R))
        if not ok:
            for (_inv, _x0, _x1, _y0, _y1) in DEST_CAJAS:
                _l = _inv @ Vector((x, y, 0.0))
                if _x0 - DESTINO_R < _l.x < _x1 + DESTINO_R and _y0 - DESTINO_R < _l.y < _y1 + DESTINO_R:
                    ok = True
                    break
        if not ok:
            fallo('camino_sin_destino', c['nombre'], x, y, 'extremo a > %.0f m de todo (pista, caminos, casas, plazas, muelles)' % DESTINO_R)

# --- flotantes / enterrados: informe de asentar_objetos.py ---
corregidos = {}
ASENTAR = OUT + '/asentar.json'
if os.path.exists(ASENTAR):
    A = json.load(open(ASENTAR, encoding='utf-8'))
    for e_ in A['edificios']['enterrados']:
        fallo('casa_enterrada', e_['nombre'], e_['x'], e_['y'], 'terreno %.1f m sobre la base (fachada %.1f, trasera %.1f)'
              % (e_['enterrada_m'], e_.get('enterrada_fachada_m', 0), e_.get('enterrada_trasera_m', 0)))
    for e_ in A['edificios']['flotantes']:
        fallo('casa_flotante', e_['nombre'], e_['x'], e_['y'], 'esquina %.1f m sobre el suelo%s' % (e_['flotante_m'], ' (bajo el zocalo)' if e_['zocalo'] else ''))
    for e_ in A['edificios']['sin_suelo']:
        fallo('casa_sin_suelo', e_['nombre'], e_['x'], e_['y'], 'esquina sin superficie debajo')
    for s_ in A['sin_impacto']:
        fallo('objeto_fuera_del_terreno' if s_.get('motivo') == 'fuera_del_terreno' else 'objeto_sin_apoyo', s_['nombre'], s_['x'], s_['y'], 'sin superficie bajo el objeto')
    for s_ in A['bajo_mar']:
        fallo('objeto_sobre_el_mar', s_['nombre'], s_['x'], s_['y'], s_.get('motivo', ''))
    for s_ in A.get('dudosos', []):
        fallo('objeto_junto_a_puente' if 'puente' in s_.get('motivo', '') else 'objeto_salto_grande', s_['nombre'], s_['x'], s_['y'], s_.get('motivo', ''))
    for s_ in A.get('bajo_superficie', []):
        fallo('objeto_bajo_superficie', s_['nombre'], s_['x'], s_['y'],
              '%s a %.2f m por encima de la base' % (s_['superficie'], s_['altura_sobre_base']))
    for s_ in A.get('atraviesa_voladizo', []):
        aviso('objeto_atraviesa_voladizo', s_['nombre'], s_['x'], s_['y'],
              '%s a %.1f m sobre la base de un objeto de %.1f m' % (s_['superficie'], s_['altura_sobre_base'], s_['alto_objeto']))
    # v1 inspectores: ermitas a +-0.5 m del terreno en las 4 esquinas (J N1: enterrada ladera
    # arriba y volada ladera abajo; el umbral general de casas, 1.2 m, no la veia)
    for e_ in A['edificios'].get('todos', []):
        if not e_['nombre'].startswith('ITAL_ermita'):
            continue
        dd = [d for d in e_.get('desnivel_esquinas', []) if d is not None]
        if dd and max(abs(d) for d in dd) > ERMITA_TOL:
            fallo('ermita_desnivel', e_['nombre'], e_['x'], e_['y'], 'terreno - base en las esquinas %s (tolerancia +-%.1f m)'
                  % (dd, ERMITA_TOL))
    # bancales: pie del muro volado o relleno que no enrasa con la ladera (D2, C-05)
    for b_ in A.get('bancales', []):
        if not b_.get('ok', True):
            fallo('bancal_mal_asentado', b_['nombre'], b_['x'], b_['y'], 'puntos mal %s (terreno - punto: %s)'
                  % (b_['mal'], json.dumps(b_['terreno_menos_punto'])))
    # arboles que asentar tuvo que quitar o sacar de un muro: aviso (el fallo de origen es de quien los planto)
    for q_ in A.get('quitados', []):
        aviso('arbol_quitado_por_asentar', q_['nombre'], q_['x'], q_['y'], q_.get('motivo', ''))
    for d_ in A.get('dentro_de_muro', []):
        if d_.get('accion', '').startswith('movido'):
            aviso('arbol_sacado_de_muro', d_['nombre'], d_['x'], d_['y'], '%s asomaba %.2f m: %s'
                  % (d_['obstaculo'], d_['asoma_m'], d_['accion']))
    # v2 inspectores: copas sobre una calzada (A-r2-11), troncos junto a un camino (E2-10) y coches
    # que no caben (C2-03). Lo que asentar arreglo es aviso (el fallo de origen es de quien lo puso);
    # una copa de arbol fijo (plazoleta/jardinera) sobre una calzada sigue ahi: fallo
    for d_ in A.get('copa_calzada', []):
        det = 'copa a %.2f m sobre %s (minimo %.1f): %s' % (d_['holgura'], d_['calzada'], d_['minimo'], d_['accion'])
        if d_.get('accion', '').startswith('aviso'):
            fallo('copa_sobre_calzada', d_['nombre'], d_['x'], d_['y'], det)
        elif d_.get('accion', '').startswith('movido'):
            aviso('arbol_copa_apartada', d_['nombre'], d_['x'], d_['y'], det)
    for j_ in A.get('junto_a_camino', []):
        aviso('arbol_junto_a_camino', j_['nombre'], j_['x'], j_['y'], 'tronco a < 1.5 m de %s y sin sitio libre para apartarlo'
              % ', '.join(j_.get('camino', [])))
    for c_ in A.get('coches_quitados', []):
        aviso('coche_quitado_por_asentar', c_['nombre'], c_.get('x', 0), c_.get('y', 0), '%s (fila %s)'
              % (c_.get('motivo', ''), c_.get('fila', '')))
    # v3 inspectores (D2/E2): bancales que asentar tuvo que bajar o quitar (el origen es del integrador)
    for b_ in A.get('bancales_ajuste', []):
        tipo_b = 'bancal_quitado_por_asentar' if b_.get('accion', '').startswith('quitado') else 'bancal_bajado_por_asentar'
        aviso(tipo_b, b_['nombre'], b_['x'], b_['y'], b_.get('accion', ''))
    corregidos = {k: A['resumen'].get(k) for k in ('candidatos', 'movidos', 'flotaban_mas_0_6', 'enterrados_mas_0_6',
                                                   'arboles_quitados', 'hijos_asentados', 'dentro_de_muro',
                                                   'losas_ajustadas', 'copa_calzada', 'junto_a_camino',
                                                   'coches_asentados', 'coches_quitados', 'terreno_nodos_v3',
                                                   'losas_hierba_rebajada', 'senderos_aire_025', 'bancales_bajados',
                                                   'bancales_quitados')}
    log('asentar.json leido: %s' % json.dumps(corregidos))
else:
    log('AVISO: no hay %s; no se comprueban flotantes/enterrados' % ASENTAR)


# --- v1 inspectores: losas CALLE_plaza* (C-04, B7, G7) y cipreses de hileras (E1, J2) ---
def z_ter_tri(x, y):
    """Cota del TERRENO que SE VE en (x, y): triangulos del render (loop_triangles), que parten
    cada quad (a, a+1, a+nx+1, a+nx) por la diagonal a -> a+nx+1. None fuera de la rejilla."""
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


def losa_columnas(co):
    """{i_fondo: i_arriba}: en una losa con canto (anillo de arriba + anillo de fondo con la misma
    planta) el vertice mas bajo de cada columna es el fondo y el mas alto la corona."""
    col = {}
    for i, (x_, y_, _z) in enumerate(co):
        col.setdefault((round(float(x_), 2), round(float(y_), 2)), []).append(i)
    res = {}
    for ids in col.values():
        if len(ids) >= 2:
            i_a = max(ids, key=lambda k: co[k][2])
            i_f = min(ids, key=lambda k: co[k][2])
            if co[i_a][2] - co[i_f][2] > 0.05:
                res[i_f] = i_a
    return res


def _dentro_poly(px, py, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def _d_poly(px, py, poly):
    best = 1e9
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy
        f = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / l2))
        best = min(best, math.hypot(px - ax - vx * f, py - ay - vy * f))
    return best


def losa_hierba(poly, corona, paso=0.5):
    """(puntos con hierba > LOSA_HIERBA_MAX sobre la corona, maximo, puntos) en una rejilla de `paso` m
    dentro del poligono de arriba de la losa y a >= LOSA_HIERBA_MARGEN m de su borde (en el borde de una
    losa tallada en un talud el terreno sube: eso es el talud, no hierba encima). Triangulacion del render."""
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    n_h, h_max, n_p = 0, -1e9, 0
    x = min(xs) + paso / 2.0
    while x < max(xs):
        y = min(ys) + paso / 2.0
        while y < max(ys):
            if _dentro_poly(x, y, poly) and _d_poly(x, y, poly) >= LOSA_HIERBA_MARGEN:
                zt_ = z_ter_tri(x, y)
                if zt_ is not None:
                    n_p += 1
                    h_max = max(h_max, zt_ - corona)
                    n_h += int(zt_ - corona > LOSA_HIERBA_MAX)
            y += paso
        x += paso
    return n_h, h_max, n_p


n_losas = 0
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not ob.name.startswith(LOSA_PREF_QA):
        continue
    co = verts_mundo(ob)
    if len(co) == 0:
        continue
    n_losas += 1
    z0_, z1_ = float(co[:, 2].min()), float(co[:, 2].max())
    cx_, cy_ = float(co[:, 0].mean()), float(co[:, 1].mean())
    # v2 inspectores (G2-09 y el falso positivo de CALLE_plaza_hotel): a lo largo de cada arista del
    # FONDO (y de la de arriba que tiene encima), cada 0.25 m: canto VISIBLE = corona - max(terreno,
    # fondo) y aire = fondo - terreno. Antes: zmax - zmin (un canto enterrado contaba como tambor) y
    # el fondo mas bajo de toda la losa (el aire bajo un vertice concreto no se veia)
    fondo_de = losa_columnas(co)
    aristas = [tuple(e.vertices) for e in ob.data.edges if e.vertices[0] in fondo_de and e.vertices[1] in fondo_de]
    visible, hueco, donde = 0.0, -1e9, (cx_, cy_)
    for f1, f2 in aristas or [(f, f) for f in fondo_de]:
        a1, a2 = fondo_de[f1], fondo_de[f2]
        n_ = max(1, int(math.ceil(math.hypot(co[f2][0] - co[f1][0], co[f2][1] - co[f1][1]) / 0.25)))
        for k in range(n_ + 1):
            t = k / float(n_)
            x_, y_ = co[f1][0] + (co[f2][0] - co[f1][0]) * t, co[f1][1] + (co[f2][1] - co[f1][1]) * t
            zt_ = z_ter_tri(float(x_), float(y_))
            if zt_ is None:
                continue
            za = co[a1][2] + (co[a2][2] - co[a1][2]) * t
            zf = co[f1][2] + (co[f2][2] - co[f1][2]) * t
            visible = max(visible, za - max(zt_, zf))
            if zf - zt_ > hueco:
                hueco, donde = zf - zt_, (x_, y_)
    if not fondo_de:          # (losa sin columnas: el criterio de v1)
        visible = z1_ - z0_
        for x_, y_, _z in co[co[:, 2] > z1_ - 0.05]:
            zt_ = z_ter_tri(float(x_), float(y_))
            if zt_ is not None:
                hueco = max(hueco, z0_ - zt_)
    if visible > LOSA_CANTO_MAX:
        fallo('losa_tambor', ob.name, cx_, cy_, 'canto visible %.1f m (corona %.2f, fondo %.2f): tambor sobre un talud (maximo %.1f m)'
              % (visible, z1_, z0_, LOSA_CANTO_MAX))
    if hueco > LOSA_HUECO_MAX:
        fallo('losa_volada', ob.name, donde[0], donde[1], 'hasta %.2f m de aire bajo el fondo del borde (corona %.2f, canto %.2f)'
              % (hueco, z1_, z1_ - z0_))
    # v3 inspectores (C-12): hierba SOBRE la losa (terreno por encima de la corona dentro de su cara de arriba)
    cara = []
    for p_ in ob.data.polygons:
        vs_ = [int(i) for i in p_.vertices]
        if len(vs_) > len(cara) and all(co[i][2] > z1_ - 0.02 for i in vs_):
            cara = vs_
    if len(cara) >= 3:
        n_h, h_max, n_p = losa_hierba([(float(co[i][0]), float(co[i][1])) for i in cara], z1_)
        if h_max > LOSA_HIERBA_MAX:
            fallo('losa_hierba', ob.name, cx_, cy_, '%d de %d puntos de la losa con la hierba por encima (max %.2f m sobre la '
                  'corona %.2f)' % (n_h, n_p, h_max, z1_))
log('losas CALLE_plaza* revisadas: %d' % n_losas)

# --- v2 inspectores (N2): MURO que cruza una plaza/plazuela. BVH de cada losa CALLE_plaza* contra
# cada muro (MURO_PREF) cuya caja la toca; cuentan los pares cuyo triangulo de muro asoma sobre el
# terreno (las cimentaciones enterradas no se ven). >= PLAZA_MURO_FALLO pares: fallo ---


def bvh_de(ob):
    co_ = verts_mundo(ob)
    return BVHTree.FromPolygons(co_.tolist(), [tuple(p.vertices) for p in ob.data.polygons]), co_


MUROS_OB = []
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not empieza(ob.name, MURO_PREF) or len(ob.data.polygons) == 0:
        continue
    c_ = verts_mundo(ob)
    MUROS_OB.append((ob, c_[:, 0].min(), c_[:, 0].max(), c_[:, 1].min(), c_[:, 1].max(), c_[:, 2].min(), c_[:, 2].max()))
_BVH_MURO = {}
n_pm = 0
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not ob.name.startswith(LOSA_PREF_QA) or len(ob.data.polygons) == 0:
        continue
    bl, cl = bvh_de(ob)
    lx0, lx1, ly0, ly1, lz0, lz1 = cl[:, 0].min(), cl[:, 0].max(), cl[:, 1].min(), cl[:, 1].max(), cl[:, 2].min(), cl[:, 2].max()
    for (mo, mx0, mx1, my0, my1, mz0, mz1) in MUROS_OB:
        if mx1 < lx0 - 0.2 or mx0 > lx1 + 0.2 or my1 < ly0 - 0.2 or my0 > ly1 + 0.2 or mz1 < lz0 - 0.2 or mz0 > lz1 + 0.2:
            continue
        if mo.name not in _BVH_MURO:
            _BVH_MURO[mo.name] = bvh_de(mo) + ([tuple(p.vertices) for p in mo.data.polygons],)
        bm, cm, pm = _BVH_MURO[mo.name]
        pares = bl.overlap(bm)
        vistos = set()
        for _il, im in pares:
            tri = cm[list(pm[im])]
            zt_ = z_ter_tri(float(tri[:, 0].mean()), float(tri[:, 1].mean()))
            if zt_ is None or float(tri[:, 2].max()) > zt_ + 0.1:
                vistos.add(im)
        if not vistos:
            continue
        n_pm += 1
        det = '%s cruza la losa (%d triangulos de muro sobre el terreno, %d pares en total)' % (mo.name, len(vistos), len(pares))
        if len(vistos) >= PLAZA_MURO_FALLO:
            fallo('plaza_muro', ob.name, (lx0 + lx1) / 2, (ly0 + ly1) / 2, det)
        else:
            aviso('plaza_muro_roce', ob.name, (lx0 + lx1) / 2, (ly0 + ly1) / 2, det)
log('cruces plaza/muro: %d' % n_pm)

# --- v2 inspectores (C2-08): la cara de arriba de los senderos de tierra sigue al terreno. Por
# cada vertice de la cara de arriba (anillos de perfil sin los dos de la falda): aire = cara -
# terreno <= SENDERO_AIRE_MAX y hierba = terreno - cara <= SENDERO_HIERBA_MAX ---
# v3 inspectores (N1/E4): el aire se mide hasta el primer APOYO bajo la cara (terreno o, si el integrador lo
# pone, el terraplen / muro de mamposteria / losa del empalme): un borde sostenido por un muro no vuela
_ap_v, _ap_p = [], []
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not empieza(ob.name, SENDERO_APOYO_PREF) or len(ob.data.polygons) == 0:
        continue
    _c = verts_mundo(ob)
    _o = sum(len(v_) for v_ in _ap_v)
    _ap_v.append(_c.tolist())
    _ap_p += [tuple(i + _o for i in p_.vertices) for p_ in ob.data.polygons]
BVH_APOYO_S = BVHTree.FromPolygons([v_ for c_ in _ap_v for v_ in c_], _ap_p) if _ap_p else None
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or not empieza(ob.name, SENDERO_PREF):
        continue
    an = anillos_cinta(ob)
    if an is None or an.shape[1] < 3:
        continue
    top = an[:, 1:-1, :].reshape(-1, 3)
    dif, n_apoyo = [], 0
    for x_, y_, z_ in top:
        zt_ = z_ter_tri(float(x_), float(y_))
        if zt_ is None:
            continue
        aire = float(z_) - zt_
        if aire > SENDERO_AIRE_MAX and BVH_APOYO_S is not None:
            loc_, _n, _i, _d = BVH_APOYO_S.ray_cast(Vector((float(x_), float(y_), float(z_) - 0.01)), Vector((0.0, 0.0, -1.0)), aire)
            if loc_ is not None and float(z_) - loc_.z <= SENDERO_AIRE_MAX:
                aire = float(z_) - loc_.z
                n_apoyo += 1
        dif.append((aire, float(x_), float(y_), float(z_) - zt_))
    if not dif:
        continue
    volados = [d for d in dif if d[0] > SENDERO_AIRE_MAX]
    enterrados = [d for d in dif if -d[3] > SENDERO_HIERBA_MAX]
    if volados:
        p_ = max(volados)
        fallo('sendero_volado', ob.name, p_[1], p_[2], '%d de %d vertices de la cara de arriba con > %.2f m de aire (max %.2f m; '
              '%d sostenidos por terraplen/muro/losa)' % (len(volados), len(dif), SENDERO_AIRE_MAX, p_[0], n_apoyo))
    if enterrados:
        p_ = min(enterrados, key=lambda d: d[3])
        fallo('sendero_enterrado', ob.name, p_[1], p_[2], '%d de %d vertices con la hierba > %.2f m por encima (max %.2f m)'
              % (len(enterrados), len(dif), SENDERO_HIERBA_MAX, -p_[3]))

# cipreses de hileras/ermitas (hijos de ITAL_cipreses / ITAL_ermita, apoyados en el TERRENO): la
# base tiene que quedar entre el minimo del terreno bajo el tronco (anillo de 0.6 m) y 1.8 m bajo
# el centro (asentar los pone a minimo - 0.15)
for ob in scene.collection.all_objects:
    if ob.name in EN_LIB or ob.type != 'MESH' or ob.name.split('.')[0] != 'ITAL_cipres':
        continue
    if ob.parent is None or not raiz_de(ob).name.startswith(('ITAL_cipreses', 'ITAL_ermita')):
        continue
    w = ob.matrix_world.translation
    zs_ = [z_ter_tri(w.x + dx, w.y + dy) for dx, dy in ((0, 0), (0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6))]
    zs_ = [z for z in zs_ if z is not None]
    if not zs_:
        continue
    if w.z > min(zs_) + 0.1:
        fallo('cipres_flotando', ob.name, w.x, w.y, 'base %.2f m sobre el terreno mas bajo bajo el tronco' % (w.z - min(zs_)))
    elif w.z < zs_[0] - 1.8:
        fallo('cipres_enterrado', ob.name, w.x, w.y, 'base %.2f m bajo el terreno' % (zs_[0] - w.z))

# ---------------------------------------------------------------- salida
resumen = {}
for f_ in fallos:
    resumen[f_['tipo']] = resumen.get(f_['tipo'], 0) + 1
res_av = {}
for a_ in avisos:
    res_av[a_['tipo']] = res_av.get(a_['tipo'], 0) + 1
huellas = {'blend': BLEND, 'fecha': time.strftime('%Y-%m-%d %H:%M'),
           'terreno': {k: T[k] for k in ('x0', 'y0', 'cell', 'nx', 'ny')},
           'casas': casas, 'calles': calles,
           'muros': [{k: v for k, v in m.items() if k != 'puntos'} for m in muros],
           'pista': pista, 'pit_lane': pit_lane, 'arboles': arboles, 'props': props, 'rocas': rocas}
with open(OUT + '/huellas.json', 'w', encoding='utf-8') as f:
    json.dump(huellas, f, ensure_ascii=False)
informe = {'blend': BLEND, 'fecha': huellas['fecha'], 'total_fallos': len(fallos), 'resumen': resumen,
           'total_avisos': len(avisos), 'avisos_resumen': res_av, 'corregidos_por_asentar': corregidos,
           'n_huellas': {'casas': len(casas), 'calles': len(calles), 'muros': len(muros),
                         'arboles': len(arboles), 'props': len(props)},
           'fallos': sorted(fallos, key=lambda f_: (f_['tipo'], f_['objeto'])),
           'avisos': sorted(avisos, key=lambda f_: (f_['tipo'], f_['objeto']))}
with open(OUT + '/urbanismo_informe.json', 'w', encoding='utf-8') as f:
    json.dump(informe, f, indent=1, ensure_ascii=False)
log('FALLOS %d: %s' % (len(fallos), json.dumps(resumen, sort_keys=True)))
log('avisos %d: %s' % (len(avisos), json.dumps(res_av, sort_keys=True)))
log('escrito huellas.json + urbanismo_informe.json (%.0f s)' % (time.time() - t0))
