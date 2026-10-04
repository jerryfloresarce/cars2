# Exporta la escena final a formato Assetto Corsa (version 2 de la escena de export):
#  - separa la pista en mallas fisicas 1ROAD_/1DIRT_ y renombra kerbs/terreno/muros; el pit lane
#    pasa a 1PIT_pit (superficie PIT con IS_PITLANE=1 en surfaces.ini: limitador de boxes)
#  - garajes: el suelo de los boxes -> 1PIT_boxes_suelo (fisico) y el edificio -> 1WALL_pit_boxes
#    (antes nada de eso colisionaba y el coche nacia sobre 1GRASS_terreno, 0,6 m mas abajo)
#  - crea los objetos logicos como mini-mallas: AC_START_0..19, AC_PIT_0..19,
#    AC_TIME_0/1/2_L-R, AC_HOTLAP_START_0, a 1 m sobre el suelo y orientados de modo que el
#    +Z LOCAL en AC (hacia donde mira el coche) sea el sentido de la marcha (parrilla/hotlap) o la
#    salida del garaje hacia el pit lane (AC_PIT). kn5_writer.py ya NO tiene que girar nada.
#  - marca la escena con scene['porto_corsa_export_v'] = 2 (kn5_writer.py lo lee)
#  - guarda 04_export/porto_corsa_export.blend; el FBX (solo ksEditor) solo si PORTO_FBX=1
# Ejecutar:
#   blender --background --factory-startup --python exportar_ac.py
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
# fisica: env BLEND = escena integrada a abrir, SALIDA = .blend de export a guardar, GEOM = geometria de esa
# escena (pruebas sobre copias en 04_export/_fisica sin tocar porto_corsa.blend)
BLEND_IN = os.environ.get('BLEND') or BASE + r'\03_blender\porto_corsa.blend'
BLEND_OUT = os.environ.get('SALIDA') or BASE + r'\04_export\porto_corsa_export.blend'
G = json.load(open(os.environ.get('GEOM') or BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
OUT_FBX = BASE + r'\04_export\fbx\porto_corsa.fbx'
os.makedirs(os.path.dirname(OUT_FBX), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
sc = bpy.context.scene
S = G['muestras']
N = G['n']
paso = G['paso_m']
L = G['largo_m']

def frame(s_m):
    return S[int(round((s_m % L) / paso)) % N]

def tangent(s_m):
    p = frame(s_m)
    return (p['ny'], -p['nx'])

# --- separar PISTA por material: 0/2 = asfalto/puente -> ROAD, 1 -> DIRT ---
pista = bpy.data.objects['PISTA']

def separar_por_materiales(obj, indices, nombre):
    dup = obj.copy()
    dup.data = obj.data.copy()
    dup.name = nombre
    sc.collection.objects.link(dup)
    bm = bmesh.new()
    bm.from_mesh(dup.data)
    quitar = [f for f in bm.faces if f.material_index not in indices]
    bmesh.ops.delete(bm, geom=quitar, context='FACES')
    bm.to_mesh(dup.data)
    bm.free()
    return dup

separar_por_materiales(pista, {0, 2}, '1ROAD_pista')
separar_por_materiales(pista, {1}, '1DIRT_ladera')
pista.name = 'PISTA_visual_off'
pista.hide_render = True
# la fisica la dan las nuevas; la visual duplicada se excluye del export
bpy.data.objects.remove(pista, do_unlink=True)

renombrar = {
    'PIT_LANE': '1PIT_pit',        # superficie PIT (IS_PITLANE=1): limitador de velocidad en boxes
    'PIANOS': '1KERB_pianos',
    'TERRENO': '1GRASS_terreno',
    'LINEA_SALIDA': 'linea_salida_visual',
}
for viejo, nuevo in renombrar.items():
    ob = bpy.data.objects.get(viejo)
    if ob:
        ob.name = nuevo
k = 0
for ob in list(bpy.data.objects):
    if ob.name.startswith('MUROC'):
        ob.name = '1WALL_muro%d' % k
        k += 1
    elif ob.name.startswith('ARCEN'):
        ob.name = '2GRASS_' + ob.name.lower()
    elif ob.name.startswith('PIT_muro'):
        ob.name = '1WALL_' + ob.name.lower()
    elif ob.name.startswith('CAMARA_peana'):
        ob.name = '1WALL_' + ob.name.lower()
    elif ob.name.startswith('MIRADOR_paseo'):
        ob.name = '1WALL_mirador_paseo'        # el paseo y su pretil son solidos
    elif ob.name.startswith(('MIRADOR_pasarela', 'MIRADOR_parking_cubierta')):
        ob.name = '1ROAD_' + ob.name.lower()   # v1 integrador (F-04): pasarela del paseo a la azotea-parking
    elif ob.name.startswith('GUARDARRAIL'):
        ob.name = '1WALL_' + ob.name.lower()   # el guardarrail de acero es colisionable
    # v2 integrador (H2-2/H2-4): el pretil (balaustrada) del viaducto era decorado: el coche lo atravesaba y
    # caia al mar. Solo el pretil (no VIADUCTO_tramo_cuerpo: losa plana bajo el 1ROAD y ~150k tris de arcos)
    # y las pilastras que cierran los huecos de las puertas de la roca del lazo
    elif ob.name.startswith(('VIADUCTO_tramo_balaustrada', 'VIADUCTO_pilastra')):
        ob.name = '1WALL_' + ob.name.lower()
    # v2 integrador (B-N1): el suelo de piedra del tunel no tenia fisica (el coche rodaba sobre hierba
    # 0.4-0.6 m por debajo de lo que se ve); sigue en SUELO por el prefijo 1ROAD
    elif ob.name.startswith('TUNEL_suelo'):
        ob.name = '1ROAD_' + ob.name.lower()
    # v2 integrador (A-r2-03): el dique-tapacubos del puerto (paseo, morros y paredes) es solido y transitable
    # al final de la escollera (antes el coche caia al agua al pasar de CAMINO_muelle al dique)
    elif ob.name.startswith('PUERTO_dique_malla') and ob.type == 'MESH':
        ob.name = '1ROAD_' + ob.name.lower()
    # ronda 15 (v1 integrador, N2): el muro+valla blanco de la recta y del resto del circuito es la
    # unica barrera del lado del mar: antes salia como decorado y el coche lo atravesaba. El portico
    # de meta, la pasarela y las torres de control (ya fuera del pit lane y de la pista) tambien
    elif ob.name.startswith(('CARRERA_muro', 'CARRERA_portico_estructura', 'PIT_pasarela_cuerpo', 'PIT_torre_cuerpo',
                             'CARRERA_paca_tierra', 'CARRERA_tribuna_estructura', 'PIT_amortiguador',
                             # fisica: barreras que se veian pero eran decorado (revisar_fisica_ac.py, 1b): vallas
                             # publicitarias (y sus rotulos), TODAS las pacas, zocalo del portico, patas de las
                             # pantallas, muro de arcadas del mirador, isleta de la rotonda Loews, balaustrada de la
                             # escalinata del casino y muros de los bancales
                             'CARRERA_valla', 'CARRERA_paca', 'CARRERA_portico_zocalo', 'CARRERA_pantalla_estructura',
                             'MIRADOR_muro', 'LOEWS_tambor', 'LOEWS_rotonda', 'CASINO_escalinata_balaustrada',
                             'ITAL_bancal_muro')):
        # (CARRERA_paca_tierra: pacas de las curvas de tierra y filas continuas sobre los terraplenes)
        # v2 integrador (A-r2-02): la estructura de las tribunas es solida (el coche atravesaba la grada interior);
        # PIT_amortiguador: neumaticos delante del morro del muro de boxes (N1)
        ob.name = '1WALL_' + ob.name.lower()
    # ronda 13: red de caminos ("mini ciudad funcional"): calzadas transitables, vallas y
    # muros solidos; los carteles no colisionan
    elif ob.name.startswith(('CAMINO_valla', 'CAMINO_muro', 'CAMINO_puente', 'CAMINO_terraplen')):
        ob.name = '1WALL_' + ob.name.lower()
    elif ob.name.startswith('CAMINO_tierra'):
        ob.name = '1DIRT_' + ob.name.lower()
    # ronda 15 (v1 integrador, D4/N1): las calles del PLAN URBANO (urbanismo_escena.camino3d las llama
    # CAMINO_calle/enlace/travesia/rampa/union) tambien son calzada: sin esto la mini ciudad no se
    # podia recorrer en AC (el coche rodaba sobre 1GRASS_terreno bajo la calle visual)
    elif ob.name.startswith(('CAMINO_asfalto', 'CAMINO_adoquin', 'CAMINO_muelle', 'CAMINO_marcas',
                             'CAMINO_calle', 'CAMINO_enlace', 'CAMINO_travesia', 'CAMINO_rampa', 'CAMINO_union')):
        ob.name = '1ROAD_' + ob.name.lower()
    elif ob.name.startswith('ACERA_'):
        ob.name = '1ROAD_' + ob.name.lower()   # acera transitable (en las terrazas, +0.5 sobre la pista)
    elif ob.name.startswith('BORDILLO_') and ob.type == 'MESH':
        # el bordillo ALTO de las terrazas es una faja vertical de 0.55 m (muro); el bajo, un bordillo
        _ver = sum(1 for f in ob.data.polygons if abs(f.normal.z) < 0.5)
        ob.name = ('1WALL_' if _ver > 0.5 * max(1, len(ob.data.polygons)) else '1KERB_') + ob.name.lower()
    elif ob.name.startswith('PPUEBLO_carretera') or ob.name.startswith('PPUEBLO_plaza'):
        ob.name = '1ROAD_' + ob.name.lower()   # carreteras en espiral de las rocas-pueblo
    elif ob.name.startswith(('PPUEBLO_roca', 'PPUEBLO_muro', 'PPUEBLO_escaleras')):
        ob.name = '1WALL_' + ob.name.lower()
    # ronda 15: rocas naturales (roca_lazo / roca_casino), su carretera de bajada, escaleras,
    # plazas y rampas del plan urbano, McLaren de piedra (el tunel va taladrado en el)
    elif ob.name.startswith(('PENON_carretera', 'PENON_plazas', 'CALLE_plaza')):
        ob.name = '1ROAD_' + ob.name.lower()
    elif ob.name.startswith(('TUNEL_acantilado', 'TUNEL_portal')):
        ob.name = '1WALL_' + ob.name.lower()   # la montana-coche con el tunel taladrado: el coche no la atraviesa
    elif ob.name.startswith(('PENON_puente_roca', 'PENON_puente_muros', 'PENON_puente_escaleras', 'PENON_puente_plaza',
                             'PENON_puente_muelle', 'PENON_puente_vallas', 'PENON_roca', 'PENON_parapeto', 'PENON_escaleras',
                             'PENON_balaustrada', 'CAMINO_escalera', 'CAMINO_muro_rampa')):
        ob.name = '1WALL_' + ob.name.lower()
    # fisica (revisar_fisica_ac.py, 'visibles ante el cierre'): mobiliario solido en aceras y escapatorias, entre el
    # borde y el muro de cierre invisible: farolas, postes de guirnaldas, maceteros, zocalos de las casas y postes de
    # los carteles de los caminos. Siendo decorado el coche los atravesaba y se paraba contra un muro que no se ve
    elif ob.name.startswith(('CALLE_farola', 'CALLE_poste_guirnalda', 'CALLE_maceta', 'CASAS_zocalo',
                             'CAMINO_cartel_cuerpo')) and ob.type == 'MESH':
        ob.name = '1WALL_' + ob.name.lower()

# --- ronda 15 (v1 integrador): ninguna superficie fisica SECUNDARIA dentro del asfalto. Las bocas de
# los caminos y los enlaces del plan llegan al borde de la pista (y alguna tapa o 'cuna' entraba hasta
# 2.4 m en la calzada, G2/F-02): ahora que son 1ROAD_/1WALL_ serian escalones y muros reales sobre la
# pista. Se borran sus caras con algun vertice > 0.15 m dentro del asfalto y a menos de 1.2 m de la cota
# de la calzada (los puentes y caminos a otra cota no se tocan). ---
from mathutils import kdtree as _kdt
_kd = _kdt.KDTree(N)
for _i, _q in enumerate(S):
    _kd.insert((_q['x'], _q['y'], 0.0), _i)
_kd.balance()
_lib0 = bpy.data.collections.get('LIB')
_en_lib0 = set(o.name for o in _lib0.all_objects) if _lib0 else set()

def _dentro_asfalto(w):
    _co, _i, _d = _kd.find((w.x, w.y, 0.0))
    q = S[_i]
    dx, dy = w.x - q['x'], w.y - q['y']
    u = dx * q['nx'] + dy * q['ny']
    if abs(dx * q['ny'] - dy * q['nx']) > 1.6 or abs(u) > q['w'] / 2 - 0.15:
        return False
    return abs(w.z - (q['z'] - q['lat'] * u)) < 1.2

_n_rec = 0
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in _en_lib0
           and o.name.startswith(('1ROAD_camino_', '1ROAD_calle_', '1WALL_camino_', '1DIRT_camino_'))]:
    mw = ob.matrix_world
    malas = [f.index for f in ob.data.polygons if any(_dentro_asfalto(mw @ ob.data.vertices[v].co) for v in f.vertices)]
    if not malas:
        continue
    if ob.data.users > 1:
        ob.data = ob.data.copy()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in malas], context='FACES')
    bm.to_mesh(ob.data)
    bm.free()
    _n_rec += len(malas)
print('recorte: %d caras de caminos/calles/muros secundarios dentro del asfalto borradas' % _n_rec)

# --- ronda 15 (v1 integrador, D4): las casas no se podian atravesar en el juego solo si su malla era
# fisica. En vez de convertir la malla visual (5000 tris por casa) se crea una CAJA 1WALL_ por edificio,
# metida 0.45-0.6 m dentro de los muros (no se ve: el vidrio va rehundido 6 cm y es opaco), de la base
# a +4 m. Casas: pivote en el centro de la fachada (y=0, cuerpo hacia -Y); civicos: cuerpo centrado. ---
_m_col = bpy.data.materials.get('MAT_zocalo_piedra') or bpy.data.materials.new('MAT_colision')
_cajas_vs, _cajas_fs = [], []

def _caja_colision(mw, x0, x1, y0, y1, z0, z1):
    if x1 - x0 < 1.0 or y1 - y0 < 1.0:
        return
    o = len(_cajas_vs)
    for (a, b) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        _cajas_vs.append(tuple(mw @ Vector((a, b, z0))))
    for (a, b) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        _cajas_vs.append(tuple(mw @ Vector((a, b, z1))))
    _cajas_fs.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7)] +
                     [(o + k, o + (k + 1) % 4, o + 4 + (k + 1) % 4, o + 4 + k) for k in range(4)])

for ob in bpy.data.objects:
    if ob.name in _en_lib0:
        continue
    if ob.type == 'MESH' and ob.name.startswith(('CASAS_casa', 'CASAS_lazo')):
        xs = [c[0] for c in ob.bound_box]
        ys = [c[1] for c in ob.bound_box]
        if max(ys) > 2.0 or min(ys) > -3.0:
            continue                      # no sigue la convencion de casa (fachada en y=0)
        esc = ob.scale.z or 1.0
        _caja_colision(ob.matrix_world, min(xs) + 0.6, max(xs) - 0.6, min(ys) + 0.6, -0.45, -1.0 / esc, 4.0 / esc)
    elif ob.type == 'EMPTY' and ob.parent is None and ob.name.startswith(('AYTO_root', 'CAMPANILE_root', 'HOTEL_root')):
        # medidas del cuerpo macizo en edificios_civicos_v2 (22x13 / fuste 4.2 / 42x22 + pabellones 11x24)
        hx, hy = {'AYTO': (10.7, 6.2), 'CAMP': (1.9, 1.9), 'HOTE': (29.5, 10.5)}[ob.name[:4]]
        _caja_colision(ob.matrix_world, -hx, hx, -hy, hy, -1.0, 4.0)
if _cajas_fs:
    _me_c = bpy.data.meshes.new('1WALL_casas_colision')
    _me_c.from_pydata(_cajas_vs, [], _cajas_fs)
    _me_c.materials.append(_m_col)
    _me_c.update()
    sc.collection.objects.link(bpy.data.objects.new('1WALL_casas_colision', _me_c))
print('colision de edificios: %d cajas 1WALL_' % (len(_cajas_fs) // 6))

# --- garajes: los coches arrancan DENTRO (AC_PIT_*), asi que el suelo y el edificio tienen que ser
# FISICOS. El suelo de los boxes (material MAT_PIT_suelo_box, 1 cara a z=2,74) pasa a 1PIT_boxes_suelo
# (superficie PIT) y el resto del edificio (paredes, pilares, techo) a 1WALL_pit_boxes. Antes el unico
# suelo colisionable bajo los AC_PIT era 1GRASS_terreno, 0,55-0,70 m mas abajo (coche hundido). ---
MAT_SUELO_BOX = 'MAT_PIT_suelo_box'
_lib = bpy.data.collections.get('LIB')
_en_lib = set(o.name for o in _lib.all_objects) if _lib else set()   # plantillas: se borran al final
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('PIT_boxes_edificio')
           and o.name not in _en_lib]:
    nombre_viejo = ob.name
    sufijo = nombre_viejo[len('PIT_boxes_edificio'):]          # '.001', ...
    idx_suelo = {i for i, m in enumerate(ob.data.materials) if m is not None and m.name == MAT_SUELO_BOX}
    if not idx_suelo:
        print('AVISO: %s no tiene %s; todo el edificio pasa a 1WALL_' % (nombre_viejo, MAT_SUELO_BOX))
        ob.name = '1WALL_pit_boxes' + sufijo
        continue
    resto = set(range(len(ob.data.materials))) - idx_suelo
    separar_por_materiales(ob, idx_suelo, '1PIT_boxes_suelo' + sufijo)
    separar_por_materiales(ob, resto, '1WALL_pit_boxes' + sufijo)
    bpy.data.objects.remove(ob, do_unlink=True)
    print('garajes: %s -> 1PIT_boxes_suelo%s + 1WALL_pit_boxes%s' % (nombre_viejo, sufijo, sufijo))

# --- objetos logicos como mini-mallas ---
def mini_mesh(name, loc, rot_z):
    me = bpy.data.meshes.new(name)
    d = 0.18
    verts = [(-d, -d, 0), (d, -d, 0), (d, d, 0), (-d, d, 0),
             (-d, -d, 2 * d), (d, -d, 2 * d), (d, d, 2 * d), (-d, d, 2 * d)]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
             (1, 2, 6, 5), (0, 3, 7, 4)]
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, me)
    ob.location = Vector(loc)
    ob.rotation_euler = (0, 0, rot_z)
    sc.collection.objects.link(ob)
    return ob

def heading(s_m):
    t = tangent(s_m)
    return math.atan2(t[1], t[0])

# Orientacion: AC hace mirar al coche hacia el +Z LOCAL del dummy. Con el cambio de ejes del escritor
# (x, y, z)_blender -> (x, z, -y)_kn5, el +Z local de AC es el -Y local de Blender: para que el coche
# mire en la direccion `hd` (angulo en el plano XY de Blender) el objeto se gira hd + pi/2.
# (Antes era hd - pi/2 = coche de espaldas, y kn5_writer.py lo parcheaba girando 180 grados.)
ALTURA_AC = 1.0   # m sobre la superficie (tutorial AC: 1-2 m; con 0,4 un coche de origen alto nace hundido)

def rot_ac(hd):
    return hd + math.pi / 2

# parrilla: 20 puestos en dos columnas tras la linea de meta
for i in range(20):
    s_m = L - 14 - 8.0 * (i // 2)
    lado = 2.3 if i % 2 == 0 else -2.3
    p = frame(s_m)
    x = p['x'] + p['nx'] * lado
    y = p['y'] + p['ny'] * lado
    mini_mesh('AC_START_%d' % i, (x, y, p['z'] + ALTURA_AC), rot_ac(heading(s_m)))

# pits: 16 puestos a lo largo del pit lane (zona de boxes)
PIT = G.get('pit_lane') or []
_plazas = sorted((o for o in bpy.data.objects if o.name.startswith('PIT_plaza_')), key=lambda o: o.name)
if _plazas:
    # ronda 12: cada coche arranca DENTRO de su garaje (plazas del pit_kit)
    # El +Y local de las plazas apunta al lado abierto del garaje (hacia el pit lane, medido: el carril
    # esta a 4,5-12 m en esa direccion). Girandolas pi, el +Z de AC (= -Y local) apunta hacia alli.
    _plazas_xy = []
    _salida = None
    for j, e in enumerate(_plazas[:20]):
        rz = e.rotation_euler.z
        mini_mesh('AC_PIT_%d' % j, (e.location.x, e.location.y, e.location.z + ALTURA_AC), rz + math.pi)
        _plazas_xy.append((e.location.x, e.location.y))
        _salida = Vector((-math.sin(rz), math.cos(rz), 0.0))      # +Y local de la plaza, en mundo
        bpy.data.objects.remove(e, do_unlink=True)
    print('AC_PIT: %d plazas dentro de los boxes' % min(20, len(_plazas)))

    # --- rampa garaje -> pit lane (1PIT_boxes_rampa). El suelo de los boxes esta a z=2,74 y el pit lane
    # es una losa a 3,0-3,3 con 1,5 m de hierba (z=2,55) entre medias: sin rampa el coche baja del
    # garaje y no puede subir al carril (escalon de 0,26-0,57 m). Tira de quads desde 1 m por delante
    # del centro de cada garaje (sobre el suelo) hasta el borde cercano del carril, vertice a vertice
    # (el carril sube y baja 0,15 m a lo largo de la fila). Pendiente resultante 7-16 %. ---
    def rampa_garajes(plazas_xy, salida):
        lane = bpy.data.objects.get('1PIT_pit')
        c0 = Vector(plazas_xy[0]) if plazas_xy else None
        suelos = [o for o in bpy.data.objects if o.name.startswith('1PIT_boxes_suelo')]
        # el suelo de la fila de garajes real = el mas cercano a la primera plaza
        def _centro_xy(o):
            c = sum((o.matrix_world @ Vector(b) for b in o.bound_box), Vector()) / 8.0
            return Vector((c.x, c.y))
        suelo = min(suelos, key=lambda o: (_centro_xy(o) - c0).length) if (suelos and c0 is not None) else None
        if not (lane and suelo and plazas_xy and salida is not None):
            print('AVISO: sin rampa de garajes (falta 1PIT_pit o 1PIT_boxes_suelo)')
            return None
        z_suelo = max((suelo.matrix_world @ v.co).z for v in suelo.data.vertices)
        u = Vector((salida.x, salida.y)).normalized()        # hacia el pit lane
        t = Vector((-u.y, u.x))                               # a lo largo de la fila de garajes
        lats = [(Vector(p) - c0).dot(t) for p in plazas_xy]
        lat_min, lat_max = min(lats) - 4.0, max(lats) + 4.0
        borde = []
        for v in lane.data.vertices:
            w = lane.matrix_world @ v.co
            rel = Vector((w.x, w.y)) - c0
            along, lat = rel.dot(u), rel.dot(t)
            if 3.5 <= along <= 5.5 and lat_min <= lat <= lat_max:     # borde cercano del carril (~4,5 m)
                borde.append((lat, along, w.copy()))
        borde.sort(key=lambda b: b[0])
        borde = [b for i, b in enumerate(borde) if i == 0 or b[0] - borde[i - 1][0] > 0.05]
        if len(borde) < 2:
            print('AVISO: sin rampa de garajes (no se encontro el borde del pit lane)')
            return None
        verts, faces = [], []
        for lat, along, w in borde:
            inner = Vector((w.x, w.y)) - u * (along - 1.0)
            verts.append((inner.x, inner.y, z_suelo))
            verts.append((w.x, w.y, w.z))
        for k in range(len(borde) - 1):
            faces.append((2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1))
        me = bpy.data.meshes.new('1PIT_boxes_rampa')
        me.from_pydata(verts, [], faces)
        mat = bpy.data.materials.get('MAT_PIT_hormigon') or bpy.data.materials.get('MAT_asfalto')
        if mat:
            me.materials.append(mat)
        ob = bpy.data.objects.new('1PIT_boxes_rampa', me)
        sc.collection.objects.link(ob)
        desn = [w.z - z_suelo for _, _, w in borde]
        pend = [100.0 * (w.z - z_suelo) / max(along - 1.0, 0.1) for _, along, w in borde]
        print('rampa garajes: %d tramos, largo fila %.0f m, desnivel %.2f..%.2f m, pendiente %.0f..%.0f %%'
              % (len(faces), borde[-1][0] - borde[0][0], min(desn), max(desn), min(pend), max(pend)))
        return ob

    rampa_garajes(_plazas_xy, _salida)
elif PIT:
    pit_in_s = L - 190.0
    for j in range(20):
        s_obj = 36.0 + 6.5 * j
        kidx = int(round((((s_obj - pit_in_s) % L) / 3.0)))
        kidx = max(0, min(len(PIT) - 2, kidx))
        q = PIT[kidx]
        q2 = PIT[kidx + 1]
        hd = math.atan2(q2['y'] - q['y'], q2['x'] - q['x'])
        mini_mesh('AC_PIT_%d' % j, (q['x'], q['y'], q['z'] + ALTURA_AC), rot_ac(hd))

# meta y sectores
def puerta_tiempo(nombre, s_m):
    p = frame(s_m)
    h = p['w'] / 2 - 0.3
    hd = rot_ac(heading(s_m))     # (la orientacion de las puertas de tiempo es indiferente para AC)
    mini_mesh(nombre + '_L', (p['x'] + p['nx'] * h, p['y'] + p['ny'] * h, p['z'] + 0.5), hd)
    mini_mesh(nombre + '_R', (p['x'] - p['nx'] * h, p['y'] - p['ny'] * h, p['z'] + 0.5), hd)

puerta_tiempo('AC_TIME_0', 0.0)
puerta_tiempo('AC_TIME_1', 1780.0)   # tras la seccion de tierra
puerta_tiempo('AC_TIME_2', 3540.0)   # sector casino
p = frame(L - 35)
mini_mesh('AC_HOTLAP_START_0', (p['x'], p['y'], p['z'] + ALTURA_AC), rot_ac(heading(L - 35)))

# --- fisica (cierre_ac.py), con todo ya renombrado: muros de cierre INVISIBLES a los dos lados de la pista (no se
# puede salir del circuito), barreras 1WALL_ visibles por las dos caras (o giradas si estaban al reves), terreno que
# no asoma sobre el asfalto, cuna pista-pit lane sin escalones y rampa de garajes en S ---
import sys as _sys
_sys.path.insert(0, os.path.join(BASE, '04_export'))
import cierre_ac  # noqa: E402
if os.environ.get('CIERRE', '1') != '0':      # CIERRE=0: export de referencia SIN cierre_ac (informe 'antes')
    cierre_ac.construir(G, print)
else:
    print('fisica: CIERRE=0 -> cierre_ac.construir NO se ejecuta (export de referencia)')

# --- normales hacia ARRIBA en todo lo que es suelo (AC descarta las caras de espaldas):
# las cintas de marcas, aceras y bordillos se generan con el orden izquierda->derecha
# y salian mirando hacia abajo: invisibles dentro del juego ---
import bmesh
SUELO = ("1ROAD", "1DIRT", "1KERB", "1GRASS", "2GRASS", "1PIT", "MARCA", "ACERA", "BORDILLO",
         "LINEA", "ARCEN", "PIT", "TUNEL_suelo", "AGUA")   # (1ROAD incluye ya los caminos)
_vistos = set()
_volteadas = 0
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.name.startswith(SUELO) or ob.data.name in _vistos:
        continue
    _vistos.add(ob.data.name)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    malas = [f for f in bm.faces if f.normal.z < -0.05]
    if malas:
        bmesh.ops.reverse_faces(bm, faces=malas)
        _volteadas += len(malas)
        bm.to_mesh(ob.data)
    bm.free()
print("normales de suelo corregidas:", _volteadas, "caras")

# --- limpieza para el export: fuera camaras y biblioteca ---
lib = bpy.data.collections.get('LIB')
if lib:
    for ob in list(lib.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(lib)
for ob in list(bpy.data.objects):
    if ob.type in ('CAMERA', 'LIGHT') and ob.name != 'SOL':
        bpy.data.objects.remove(ob, do_unlink=True)

# version de la escena de export: 2 = orientaciones y alturas AC definitivas, garajes fisicos, 1PIT_.
# kn5_writer.py lee esta marca y solo aplica su antiguo giro de 180 grados a escenas v1.
sc['porto_corsa_export_v'] = 2
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
n_obj = sum(1 for o in bpy.data.objects if o.type == 'MESH')
print('OK blend de export v2 guardado; mallas:', n_obj)

# --- FBX (solo para ksEditor; el paquete usa el KN5 de kn5_writer.py). Tarda minutos: PORTO_FBX=1 ---
if os.environ.get('PORTO_FBX') == '1':
    bpy.ops.export_scene.fbx(
        filepath=OUT_FBX,
        use_selection=False,
        object_types={'MESH'},
        axis_forward='-Z',
        axis_up='Y',
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',
        bake_space_transform=True,
        use_mesh_modifiers=True,
        path_mode='COPY',
        embed_textures=False,
    )
    print('OK FBX ->', OUT_FBX)
else:
    print('FBX omitido (PORTO_FBX != 1): el modelo lo genera kn5_writer.py directamente en KN5')
