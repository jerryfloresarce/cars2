"""test_roca_casino.py - construye el PENON DEL CASINO (roca_casino.py) con EXACTAMENTE los
datos de zona_casino() (integrar_escena.py) sobre una copia de geometria_3d.json
(v3: geometria_3d.json o env GEOM, o la indicada con -- --geom <ruta>): contorno 'pts' (elipse
118x78, giro 0.5, a 190 m del lobulo 36-38, _contorno_libre margen 8), 'ent' (punto del
contorno mas cercano a la muestra de la curva 36), z_base_c = max(terreno en el contorno)
+ 0.3, z_plaza = max(z curvas 36-38) - 2, z_top_c = max(z_plaza + 12.2, z_base_c + 8.0),
entrada = (ent, z36 + 0.1), terreno bilineal de la rejilla, y la misma llamada que el
integrador. Comprueba e imprime (todo 0 salvo las medidas):
  horquillas, vueltas, longitud y pendiente max de la bajada; casas malas (ray-cast 9 puntos,
  roca encima, calzada, solapes); voladizos sobre la calzada (rayos hacia arriba); quads
  cruzados; farolas en el asfalto; matas enterradas; quiebros; meseta llana (r 34) y huella
  real del casino (casino_v2 colocado como el integrador); roca cerrada; carretera bajo el
  terreno; HUECOS roca-terreno en el perimetro (360 columnas: rayo horizontal al pie y foso
  de agua entre roca y espolon) y roca que flota; pista bajo la roca.
  v2: la bajada acaba en una cala con barcos (espigon o cala al pie de la roca; 3 horquillas y <= 2.1
  vueltas en modo 'roca'); roca delante del final de la calzada (>= 3 m); grieta junto a la rotonda
  (s 3546-3580, lado +1, 6-20 m del borde: suelo >= pista - 3); saltos del suelo > 25 m en 8 m (QA).
  Vistas nuevas roca_casino_v2_* (cala desde el mar y desde arriba, final de la calzada, vistas del
  revisor G2-01/G2-02/G2-05, rotonda cenital). La roca recibe pista=muestras (relleno junto a la pista).
  v3: curvas=G['curvas'] y relleno_fosos por defecto (como el integrador; --sin_fosos lo apaga). Falla con plantas
  del penon en el ESPOLON de zona_caminos (info['espolon_eje'], dibujado como CTX_espolon) o en la boca de la entrada,
  enterradas por la ladera o arboles a < 8 m de la pista (N1), y con saltos > 15 m en 4 m en el barranco N
  (x 650-690, y -560..-530, N3). Vistas roca_casino_v3_* (las del revisor de N1/N3 y el foso N cenital y desde el E).
Previews (EEVEE 1280x800) en previews/roca_casino_*.png: 4 aereas (sureste a media altura
como la foto, noreste, oeste desde la pista, sur), cenital, carretera a 1.5 m y desde la
cala mirando arriba. Guarda blend/roca_casino.blend.

  blender --background --factory-startup --python test_roca_casino.py [-- --geom ruta.json]
"""
import importlib.util
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AQUI = os.path.dirname(os.path.abspath(__file__))
T0 = time.time()


def cargar(nombre, fichero=None):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(AQUI, (fichero or nombre) + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


rc = cargar('roca_casino')
kits = {}
for nombre, fichero in (('casas_kit', 'casas_kit_v2'), ('vegetacion_kit', 'vegetacion_kit_v2'),
                        ('italiano_kit', 'italiano_kit'), ('yates_kit', 'yates_kit'), ('casino', 'casino_v2')):
    try:
        kits[nombre] = cargar(nombre, fichero)
    except Exception as e:
        kits[nombre] = None
        print('kit %s no disponible: %s' % (nombre, e))

# ---------------------------------------------------------------- datos del integrador
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
# v3: por defecto la MISMA geometria que integrar_escena (env GEOM o 03_blender/geometria_3d.json); la copia del 03/10
# (_geom_snapshot_roca_casino.json, con --geom) es de antes del arreglo de las curvas y su terreno tapa la bajada
RUTA_GEOM = (ARGS[ARGS.index('--geom') + 1] if '--geom' in ARGS
             else (os.environ.get('GEOM') or os.path.join(AQUI, '..', 'geometria_3d.json')))
if not os.path.isabs(RUTA_GEOM):
    RUTA_GEOM = os.path.join(AQUI, RUTA_GEOM)
print('geometria:', RUTA_GEOM)
# --param k=v (repetible): parametros extra de roca_casino.build para probar ramas (p. ej. la red de seguridad:
# --param horquillas_extra=0 --param espigon_z_max=-1 -> plataforma final 'mirador')
EXTRA = {}
for k_a, a_ in enumerate(ARGS):
    if a_ == '--param' and k_a + 1 < len(ARGS):
        k_p, v_p = ARGS[k_a + 1].split('=')
        EXTRA[k_p] = float(v_p) if ('.' in v_p or v_p.lstrip('-').isdigit()) else v_p
print('parametros extra:', EXTRA)
G = json.load(open(RUTA_GEOM, encoding='utf-8'))
S, N, T = G['muestras'], G['n'], G['terreno']
CURVAS = {c['n']: c for c in G['curvas']}
Z_MAR = float(G.get('nivel_mar', 0.0))


def z_terreno(x, y, key='z'):
    fx = (x - T['x0']) / T['cell']
    fy = (y - T['y0']) / T['cell']
    i0 = max(0, min(T['nx'] - 2, int(fx)))
    j0 = max(0, min(T['ny'] - 2, int(fy)))
    tx = min(max(fx - i0, 0), 1)
    ty = min(max(fy - j0, 0), 1)

    def zz(i, j):
        return T[key][j * T['nx'] + i]
    return ((zz(i0, j0) * (1 - tx) + zz(i0 + 1, j0) * tx) * (1 - ty)
            + (zz(i0, j0 + 1) * (1 - tx) + zz(i0 + 1, j0 + 1) * tx) * ty)


def _contorno_libre(pts, margen):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for (x, y) in pts:
        for _ in range(60):
            j = min(range(0, N, 2), key=lambda j: (x - S[j]['x']) ** 2 + (y - S[j]['y']) ** 2)
            d = math.hypot(x - S[j]['x'], y - S[j]['y']) - S[j]['w'] / 2
            if d >= margen:
                break
            dx, dy = cx - x, cy - y
            l_ = math.hypot(dx, dy) or 1.0
            x += dx / l_ * 2.0
            y += dy / l_ * 2.0
        out.append((x, y))
    return out


cs = [CURVAS[n] for n in (36, 37, 38)]
cxc = sum(c['x'] for c in cs) / len(cs)
cyc = sum(c['y'] for c in cs) / len(cs)
mx = sum(S[i]['x'] for i in range(0, N, 20)) / len(range(0, N, 20))
my = sum(S[i]['y'] for i in range(0, N, 20)) / len(range(0, N, 20))
dx, dy = cxc - mx, cyc - my
dl = math.hypot(dx, dy) or 1.0
z_plaza = max(S[CURVAS[n]['s_idx']]['z'] for n in (36, 37, 38)) - 2.0
cxc = cxc + dx / dl * 190.0
cyc = cyc + dy / dl * 190.0
ang0 = 0.5
pts = []
for k_ in range(64):
    a_ = 2 * math.pi * k_ / 64
    ex_, ey_ = 118.0 * math.cos(a_), 78.0 * math.sin(a_)
    pts.append((cxc + ex_ * math.cos(ang0) - ey_ * math.sin(ang0), cyc + ex_ * math.sin(ang0) + ey_ * math.cos(ang0)))
pts = _contorno_libre(pts, 8.0)
q37_ = S[CURVAS[36]['s_idx']]      # el integrador usa CURVAS[36] (la llama 'curva 37')
ent = min(pts, key=lambda p_: (p_[0] - q37_['x']) ** 2 + (p_[1] - q37_['y']) ** 2)
z_ter_c = [z_terreno(x_, y_) for (x_, y_) in pts]
z_base_c = max(z_ter_c) + 0.3
z_top_c = max(z_plaza + 12.2, z_base_c + 8.0)
n_mar = sum(1 for z_ in z_ter_c if z_ <= Z_MAR + 0.3)
print('datos: centro (%.1f, %.1f), entrada (%.1f, %.1f) z=%.2f (terreno ahi %.1f), contorno: terreno %.1f..%.1f, %d/64 en el mar; '
      'z_base_c %.2f, z_plaza %.2f -> meseta z_top_c %.2f'
      % (cxc, cyc, ent[0], ent[1], q37_['z'] + 0.1, z_terreno(*ent), min(z_ter_c), max(z_ter_c), n_mar, z_base_c, z_plaza, z_top_c))

# ---------------------------------------------------------------- construir (llamada del integrador)
sc = bpy.context.scene
for ob in list(sc.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
root_col = bpy.data.collections.new('PENON')
sc.collection.children.link(root_col)
# v3: relleno_fosos por defecto (como el integrador, que no lo pasa); --sin_fosos lo apaga. curvas = las de la misma
# geometria (eje del espolon de zona_caminos)
if '--sin_fosos' in ARGS:
    EXTRA['relleno_fosos'] = False
raiz, info = rc.build(root_col, pts, z_base_c, z_top_c, (ent[0], ent[1], q37_['z'] + 0.1),
                      Z_MAR, seed=2,
                      casas_kit=kits['casas_kit'], vegetacion_kit=kits['vegetacion_kit'],
                      italiano_kit=kits['italiano_kit'], yates_kit=kits['yates_kit'],
                      terreno_fn=z_terreno, z_entrada=q37_['z'] + 0.1, log=print, pista=S, curvas=G['curvas'],
                      **EXTRA)
bpy.context.view_layer.update()
print('build en %.1f s' % (time.time() - T0))
P = rc._ultimo

# ---------------------------------------------------------------- comprobaciones
fallos = []
hijos = list(raiz.children_recursive)
roca = next(o for o in hijos if o.name.startswith('PENON_roca'))
solidos = [o for o in hijos if o.type == 'MESH' and o.name.startswith(('PENON_roca', 'PENON_espigon'))]
vs_, fs_ = [], []
for o in solidos:
    n0 = len(vs_)
    mw = o.matrix_world
    vs_ += [tuple(mw @ v.co) for v in o.data.vertices]
    fs_ += [tuple(i + n0 for i in p.vertices) for p in o.data.polygons]
bvh = BVHTree.FromPolygons(vs_, fs_)
bvh_roca = BVHTree.FromPolygons([tuple(v.co) for v in roca.data.vertices], [tuple(p.vertices) for p in roca.data.polygons])


def z_roca(x, y, desde, arbol=None):
    h = (arbol or bvh).ray_cast(Vector((x, y, desde)), Vector((0, 0, -1)), 900.0)
    return None if h[0] is None else h[0].z


def roca_encima(x, y, z, alto):
    return bvh.ray_cast(Vector((x, y, z)), Vector((0, 0, 1)), alto)[0] is not None


def huella(c):
    ca, sa = math.cos(c['rot_z']), math.sin(c['rot_z'])
    return [(c['x'] + u * ca - v * sa, c['y'] + u * sa + v * ca)
            for (u, v) in ((-c['ancho'] / 2, 0.0), (c['ancho'] / 2, 0.0), (c['ancho'] / 2, -c['fondo']), (-c['ancho'] / 2, -c['fondo']))]


def _sep_axis(A, B):
    for poly in (A, B):
        for k in range(4):
            x0, y0 = poly[k]
            x1, y1 = poly[(k + 1) % 4]
            nx, ny = y0 - y1, x1 - x0
            pa = [nx * p[0] + ny * p[1] for p in A]
            pb = [nx * p[0] + ny * p[1] for p in B]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return True
    return False


sub, baj = info['cintas']
ejes = sub + baj
res = {}
# 1) casas: apoyo, roca encima, calzada, solapes
malas = 0
for c in info['plazas_casas']:
    ca, sa = math.cos(c['rot_z']), math.sin(c['rot_z'])
    alto = c['plantas'] * 3.3 + 3.0
    mal = False
    for u in (-c['ancho'] / 2 + 0.2, 0.0, c['ancho'] / 2 - 0.2):
        for v in (-c['fondo'] + 0.2, -c['fondo'] / 2, -0.2):
            x, y = c['x'] + u * ca - v * sa, c['y'] + u * sa + v * ca
            zr = z_roca(x, y, c['z'] + alto + 1.0)
            if zr is None or abs(zr - c['z']) > 0.4 or roca_encima(x, y, c['z'] + 0.3, alto + 2.0):
                mal = True
    h = huella(c)
    for (x, y, z) in ejes:
        if abs(z - c['z']) < 4.0 and min(math.hypot(x - p[0], y - p[1]) for p in h) < 2.6:
            mal = True
            break
    malas += 1 if mal else 0
hs = [huella(c) for c in info['plazas_casas']]
solapes = sum(1 for a in range(len(hs)) for b in range(a + 1, len(hs))
              if abs(info['plazas_casas'][a]['z'] - info['plazas_casas'][b]['z']) < 6.0 and not _sep_axis(hs[a], hs[b]))
res['casas'] = len(info['plazas_casas'])
res['casas_malas'] = malas + solapes
print('casas: %d (cala), malas (apoyo/roca encima/calzada) %d, solapes %d, descartadas al colocar %d'
      % (len(info['plazas_casas']), malas, solapes, info['casas_malas']))
if malas or solapes or not (4 <= len(info['plazas_casas']) <= 6):
    fallos.append('casas: %d, malas %d, solapes %d' % (len(info['plazas_casas']), malas, solapes))
# 2) voladizos: rayos hacia arriba desde el eje y los bordes (+-2.4 m) de cada cinta
vol = n_ray = 0
for cinta in (sub, baj):
    for k in range(len(cinta) - 1):
        a, b = cinta[k], cinta[k + 1]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / l, tx / l
        for off in (-2.4, 0.0, 2.4):
            n_ray += 1
            if roca_encima(a[0] + nx * off, a[1] + ny * off, a[2] + 0.6, 40.0):
                vol += 1
                if vol <= 4:
                    print('   voladizo en (%.1f, %.1f, %.1f) off %.1f' % (a[0], a[1], a[2], off))
res['voladizos'] = vol
print('voladizos sobre la calzada: %d de %d rayos (apilado interno %d)' % (vol, n_ray, info['n_voladizos_apilado']))
if vol or info['n_voladizos_apilado']:
    fallos.append('%d voladizos' % vol)
# 3) quads cruzados en la calzada (convexidad en planta)
calz = next(o for o in hijos if o.name.startswith('PENON_carretera'))
cruz = 0
for p in calz.data.polygons:
    vv = [calz.data.vertices[i].co for i in p.vertices]
    if len(vv) != 4:
        continue
    sg, ok = 0, True
    for k in range(4):
        a, b, c = vv[k], vv[(k + 1) % 4], vv[(k + 2) % 4]
        cr = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)
        if abs(cr) < 1e-6:
            continue
        if sg == 0:
            sg = 1 if cr > 0 else -1
        elif (cr > 0) != (sg > 0):
            ok = False
    cruz += 0 if ok else 1
    if not ok and cruz <= 3:
        print('   quad cruzado en (%.1f, %.1f, %.1f)' % (vv[0].x, vv[0].y, vv[0].z))
res['quads_cruzados'] = cruz
print('quads cruzados en PENON_carretera: %d de %d' % (cruz, len(calz.data.polygons)))
if cruz:
    fallos.append('%d quads cruzados' % cruz)
# 4) farolas en el asfalto (< 2.6 m del eje a cota parecida)
from mathutils.kdtree import KDTree
kd = KDTree(len(ejes))
for k, p in enumerate(ejes):
    kd.insert(Vector((p[0], p[1], 0.0)), k)
kd.balance()
far_mal, d_far = 0, 99.0
for (x, y, z) in info['farolas']:
    dm = min([d for (co, idx, d) in kd.find_n(Vector((x, y, 0.0)), 8) if abs(ejes[idx][2] - (z - 0.95)) < 3.0] or [99.0])
    d_far = min(d_far, dm)
    far_mal += 1 if dm < 2.6 else 0
    if dm < 2.6:
        print('   farola en el asfalto (%.1f, %.1f, %.1f) a %.2f m' % (x, y, z, dm))
res['farolas_asfalto'] = far_mal
print('farolas: %d, en el asfalto (< 2.6 m del eje): %d, distancia minima al eje %.2f m' % (len(info['farolas']), far_mal, d_far))
if far_mal:
    fallos.append('%d farolas en el asfalto' % far_mal)
# 5) vegetacion enterrada / flotando (primer impacto desde arriba = su apoyo)
veg = [o for o in hijos if o.name.startswith('VEG_penon') and o.parent == raiz]
ent_m = 0
for o in veg:
    x, y, z = o.matrix_world.translation
    zr = z_roca(x, y, z + 80.0)
    if zr is None or abs(zr - z) > 0.6 or roca_encima(x, y, z + 0.8, 30.0):
        ent_m += 1
res['veg_enterrada'] = ent_m
bajo_agua = sum(1 for o in veg if o.matrix_world.translation.z < Z_MAR + 0.5)       # G13
res['veg_bajo_agua'] = bajo_agua
print('vegetacion: %d piezas (%d matas), enterradas/flotando: %d, bajo el agua: %d' % (len(veg), info['n_matas'], ent_m, bajo_agua))
if ent_m or bajo_agua:
    fallos.append('%d plantas enterradas, %d bajo el agua' % (ent_m, bajo_agua))
# 6) carretera continua, pendientes, horquillas, vueltas, quiebros
for nombre, cinta in (('subida', sub), ('bajada', baj)):
    saltos = sum(1 for a, b in zip(cinta, cinta[1:]) if abs(b[2] - a[2]) > 0.115 * math.hypot(b[0] - a[0], b[1] - a[1]) + 0.1)
    k_p = max(range(len(cinta) - 1), key=lambda k: abs(cinta[k + 1][2] - cinta[k][2]) / max(0.5, math.hypot(cinta[k + 1][0] - cinta[k][0], cinta[k + 1][1] - cinta[k][1])))
    print('   %s: pendiente max en k=%d (%.1f, %.1f, %.1f)' % (nombre, k_p, cinta[k_p][0], cinta[k_p][1], cinta[k_p][2]))
    d_max = max(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(cinta, cinta[1:]))
    pend = max(abs(b[2] - a[2]) / math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(cinta, cinta[1:])
               if math.hypot(b[0] - a[0], b[1] - a[1]) > 0.5)
    print('%s: %d muestras, saltos de cota: %d, paso max %.1f m, pendiente max %.1f%%' % (nombre, len(cinta), saltos, d_max, pend * 100))
    if saltos or pend > 0.1105 or d_max > 8.0:
        fallos.append('%s discontinua o empinada (%.1f%%)' % (nombre, pend * 100))
print('bajada: %d horquillas, %.2f vueltas, %.0f m, pendiente max %.1f%%; fin %s; quiebro lateral max %.2f m/m'
      % (info['n_horquillas'], info['vueltas_bajada'], info['longitud_bajada'], info['pendiente_max_bajada'] * 100,
         info['tipo_fin'], info['quiebro_max']))
res.update({'horquillas': info['n_horquillas'], 'vueltas': round(info['vueltas_bajada'], 2),
            'longitud_bajada': round(info['longitud_bajada']), 'pendiente_max': round(info['pendiente_max'] * 100, 1)})
# vueltas <= 1.75 con 2 horquillas + espigon: con la ladera N y el espolon de tierra la cara libre es ~270 grados
# y bajar 117 m al 11 % pide >= 1060 m de carretera; v2: en modo 'roca' (sin espigon) 3 horquillas y la bajada
# sigue por la cara hasta la cala al pie: <= 2.1 vueltas
v_max = 1.75 if info['n_horquillas'] <= 2 else 2.1
if info['n_horquillas'] > 3 or info['vueltas_bajada'] > v_max or info['quiebro_max'] > 0.3 or not info['llega_cala']:
    fallos.append('bajada: horquillas %d, vueltas %.2f, quiebro %.2f, llega_cala %s'
                  % (info['n_horquillas'], info['vueltas_bajada'], info['quiebro_max'], info['llega_cala']))
# G3/G2-01: la bajada NO puede morir contra la roca ni en un mirador: acaba en la cala (muelle con barcas y casas)
print('fin de la bajada: %s (modo %s), cala %s, barcos %d, bolardos %d, conexion %s' % (
    info['tipo_fin'], info.get('modo'), info['cala'], info['n_barcos'], info.get('bolardos', 0), info.get('conexion_cala')))
if info['tipo_fin'] not in ('espigon', 'cala_roca') or not info['cala'] or info['n_barcos'] < 3:
    fallos.append('bajada sin cala (fin %s, cala %s, barcos %d)' % (info['tipo_fin'], info['cala'], info['n_barcos']))
# G2-01 (consulta2.fin_carretera): delante del final de la calzada no hay roca a menos de 3 m (rayos horizontales
# en la direccion del ultimo tramo, a 1 y 2.5 m sobre el asfalto, en el eje y a +-2 m)
a_, b_ = baj[-2], baj[-1]
tx_, ty_ = b_[0] - a_[0], b_[1] - a_[1]
l_ = math.hypot(tx_, ty_) or 1.0
tx_, ty_ = tx_ / l_, ty_ / l_
d_fin = 99.0
for off_ in (-2.0, 0.0, 2.0):
    for dz_ in (1.0, 2.5):
        o_ = Vector((b_[0] - ty_ * off_, b_[1] + tx_ * off_, b_[2] + dz_))
        h_ = bvh.ray_cast(o_, Vector((tx_, ty_, 0.0)), 60.0)
        if h_[0] is not None:
            d_fin = min(d_fin, h_[3])
res['fin_carretera_roca_m'] = round(d_fin, 1)
print('final de la calzada (%.1f, %.1f, %.1f): roca delante a %.1f m' % (b_[0], b_[1], b_[2], d_fin))
if d_fin < 3.0:
    fallos.append('la calzada acaba contra la roca (%.1f m)' % d_fin)
# 7) meseta llana (circulo r 34) y huella real del casino colocada como el integrador
cx_t, cy_t = info['centro_top']
z_top = info['z_top']
mal_meseta = n_meseta = 0
for ix in range(-34, 35, 4):
    for iy in range(-34, 35, 4):
        if math.hypot(ix, iy) > 34.0:
            continue
        n_meseta += 1
        zr = z_roca(cx_t + ix, cy_t + iy, z_top + 60.0)
        if zr is None or abs(zr - z_top) > 0.05:
            mal_meseta += 1
cas_fuera = cas_n = 0
if kits.get('casino') is not None:
    lib_col = bpy.data.collections.new('LIB_test')
    sc.collection.children.link(lib_col)
    cas = kits['casino'].build(lib_col, seed=0)
    hacia_meta = math.atan2(S[0]['y'] - cy_t, S[0]['x'] - cx_t)
    cas.location = Vector((cx_t, cy_t, z_top - 0.2))
    cas.rotation_euler = (0.0, 0.0, hacia_meta - math.pi / 2)
    cas.scale = (0.9, 0.9, 0.9)
    bpy.context.view_layer.update()
    for o in [cas] + list(cas.children_recursive):
        if o.type != 'MESH':
            continue
        mw = o.matrix_world
        for v in list(o.data.vertices)[::7]:
            w = mw @ v.co
            if w.z > z_top + 0.6:
                continue
            cas_n += 1
            zr = z_roca(w.x, w.y, z_top + 60.0, bvh_roca)
            ang = math.atan2(w.y - P.cy, w.x - P.cx) % (2 * math.pi)
            i_c = int(round(ang / P.dphi)) % P.M
            if zr is None or abs(zr - z_top) > 0.05 or math.hypot(w.x - P.cx, w.y - P.cy) > P.R_top_eff[i_c] - 0.9:
                cas_fuera += 1
    for o in list(lib_col.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(lib_col)
res['meseta_fuera'] = mal_meseta
res['casino_fuera'] = cas_fuera
print('meseta: %d/%d puntos del circulo r=34 fuera de cota (radio llano %.1f m); casino: %d/%d puntos de su base fuera de la meseta'
      % (mal_meseta, n_meseta, info['radio_meseta'], cas_fuera, cas_n))
if mal_meseta or info['radio_meseta'] < 34.0 or cas_fuera:
    fallos.append('meseta no llana o casino fuera (%d, %d)' % (mal_meseta, cas_fuera))
import bmesh
bm = bmesh.new()
bm.from_mesh(roca.data)
no_man = sum(1 for e in bm.edges if not e.is_manifold)
bm.free()
print('roca: %d tris (%d aristas no manifold)' % (info['tris_roca'], no_man))
res['no_manifold'] = no_man
if no_man:
    fallos.append('roca no cerrada (%d aristas)' % no_man)
ent_ter = sum(1 for (x, y, z) in ejes if z_terreno(x, y) > z + 0.5)
res['carretera_enterrada'] = ent_ter
print('muestras de carretera bajo el terreno: %d de %d' % (ent_ter, len(ejes)))
if ent_ter:
    fallos.append('%d muestras de carretera enterradas' % ent_ter)
# 8) HUECOS roca-terreno en el perimetro (360 columnas) y roca que flota
huecos, fosos, ejemplos = 0, 0, []
for k in range(360):
    a = math.radians(k + 0.5)
    ux, uy = math.cos(a), math.sin(a)
    r_e = None
    r = 270.0
    while r > 5.0:
        x, y = P.cx + r * ux, P.cy + r * uy
        zr = z_roca(x, y, 400.0, bvh_roca)
        if zr is not None and zr > max(z_terreno(x, y), Z_MAR) + 0.05:
            r_e = r
            break
        r -= 0.5
    if r_e is None:
        continue
    xo, yo = P.cx + (r_e + 0.75) * ux, P.cy + (r_e + 0.75) * uy
    zg = max(z_terreno(xo, yo), Z_MAR)
    o = Vector((P.cx + (r_e + 8.0) * ux, P.cy + (r_e + 8.0) * uy, zg + 0.4))
    h = bvh_roca.ray_cast(o, Vector((-ux, -uy, 0.0)), 40.0)
    if h[0] is None or h[3] > 11.5:
        # union a ras (la ladera sube desde el arcen de roca de la carretera, sin pared que cortar):
        # no es hueco si la cara de arriba de la roca sigue a menos de 1 m de la cota de la union
        # (donde roca y terreno se cruzan) en los 8 m hacia dentro: no hay cuneta ni zanja
        z_j = z_roca(P.cx + r_e * ux, P.cy + r_e * uy, 400.0, bvh_roca) or zg
        z_ras = min((z_roca(P.cx + (r_e - d) * ux, P.cy + (r_e - d) * uy, 400.0, bvh_roca) or -1e9)
                    for d in (0.5, 2.0, 4.0, 6.0, 8.0))
        if z_ras < min(zg, z_j) - 1.0:
            huecos += 1
            ejemplos.append((k, round(r_e, 1), round(zg, 1), None if h[0] is None else round(h[3], 1), round(z_ras - zg, 2)))
    agua = False
    d = 0.5
    while d < 15.0:
        zt = z_terreno(P.cx + (r_e + d) * ux, P.cy + (r_e + d) * uy)
        if zt <= Z_MAR + 0.3:
            agua = True
        elif agua and zt > Z_MAR + 1.0:
            fosos += 1
            ejemplos.append((k, 'foso', round(r_e, 1), round(d, 1)))
            break
        d += 0.5
flota = 0
for i in range(P.M):
    x, y = P.xy(i, P._perfil(i)[0][0])
    if max(z_terreno(x, y), Z_MAR - 3.0) < P.z_fondo + 0.5:
        flota += 1
res['huecos_perimetro'] = huecos + fosos
res['roca_flota'] = flota
print('perimetro: %d huecos al pie (rayo horizontal), %d fosos de agua roca-espolon, %d columnas con la base por encima del suelo; ejemplos %s'
      % (huecos, fosos, flota, ejemplos[:40]))
print('   angulos con hueco/foso: %s' % [e[0] for e in ejemplos])
if huecos or fosos or flota:
    fallos.append('huecos %d / fosos %d / flota %d' % (huecos, fosos, flota))
# 9) la pista no pasa bajo la roca (eje y bordes + 1 m)
pis = 0
for i in range(0, N, 2):
    q = S[i]
    if math.hypot(q['x'] - P.cx, q['y'] - P.cy) > 360.0:
        continue
    for lt in (-(q['w'] / 2 + 1.0), 0.0, q['w'] / 2 + 1.0):
        x, y = q['x'] + q['nx'] * lt, q['y'] + q['ny'] * lt
        zr = z_roca(x, y, q['z'] + 300.0, bvh_roca)
        if zr is not None and zr > q['z'] - 3.0:
            pis += 1
res['pista_bajo_roca'] = pis
d_pista = min(math.hypot(v[0] - S[i]['x'], v[1] - S[i]['y']) - S[i]['w'] / 2 for v in vs_[::5] for i in range(0, N, 6)
              if math.hypot(S[i]['x'] - P.cx, S[i]['y'] - P.cy) < 360.0 and v[2] > S[i]['z'] - 4.0)
print('pista: %d rayos tocan la roca; vertice de roca/espigon mas cercano al borde de la pista (por encima de z-4): %.1f m' % (pis, d_pista))
if pis:
    fallos.append('%d rayos de pista tocan la roca' % pis)
# 10) G2-05: grieta entre la rotonda Loews y el penon: rayos verticales en s 3546-3580, lado +1 (hacia el penon), a
# 6-20 m del borde: suelo (terreno o roca) >= z_pista - 3 (la rotonda y su terreno congelado quedan como estan:
# lo llena el arcen de relleno de la roca)
# s 3576-3580 se mide aparte (informativo): la salida de la rotonda hacia el viaducto, donde los radios del penon
# rozan el borde de la pista (< 5 m) y el terraplen baja a su aire hacia el SO (no hay roca entre medias)
paso_m = G.get('paso_m', 2.0)
grieta, n_g, peor, grieta_info = 0, 0, (0.0, None), 0
for s_ in range(3546, 3582, 2):
    q = S[int(round(s_ / paso_m)) % N]
    if math.hypot(q['x'] - P.cx, q['y'] - P.cy) > 200.0:
        continue
    for d_ in (6.0, 9.0, 12.0, 16.0, 20.0):
        x, y = q['x'] + q['nx'] * (q['w'] / 2 + d_), q['y'] + q['ny'] * (q['w'] / 2 + d_)
        zr = z_roca(x, y, q['z'] + 200.0, bvh_roca)
        g_ = max(z_terreno(x, y), zr if zr is not None else -1e9) - q['z']
        n_g += 1
        if g_ < -3.0:
            info_ = s_ > 3574
            grieta_info += 1 if info_ else 0
            grieta += 0 if info_ else 1
            print('   %s en s %d d %.0f (%.1f, %.1f): suelo %.1f m bajo la pista (terreno %.1f, roca %s)'
                  % ('terraplen (info)' if info_ else 'GRIETA', s_, d_, x, y, g_, z_terreno(x, y) - q['z'],
                     None if zr is None else round(zr - q['z'], 1)))
            if g_ < peor[0] and not info_:
                peor = (g_, (s_, d_))
res['grieta_rotonda'] = grieta
res['terraplen_salida_rotonda'] = grieta_info
print('grieta rotonda-penon (s 3546-3574, lado +1, d 6-20): %d puntos con el suelo > 3 m bajo la pista (peor %.1f m en %s); '
      's 3576-3580 (informativo): %d; de %d puntos; relleno: %d columnas junto a la pista, %d en fosos (%d muestras de pista)'
      % (grieta, peor[0], peor[1], grieta_info, n_g, info.get('relleno_pista', 0), info.get('relleno_fosos', 0), info.get('n_muestras_pista', 0)))
if grieta:
    fallos.append('grieta junto a la rotonda: %d puntos' % grieta)
# 11) G2-02 (QA): saltos del suelo (max(terreno, roca)) > 25 m en 8 m en el anillo de 1.0 a 1.6 Rc alrededor del penon
# (solo informativo: la aleta del borde N/NE es del terreno; en el SO la roca llena la ranura)
saltos, n_s, s_ej = 0, 0, []


def suelo(x, y):
    zr = z_roca(x, y, 400.0, bvh_roca)
    return max(z_terreno(x, y), Z_MAR, zr if zr is not None else -1e9)


for k in range(0, 360, 3):
    a = math.radians(k)
    ux, uy = math.cos(a), math.sin(a)
    i_c = int(round((a % (2 * math.pi)) / P.dphi)) % P.M
    for f_ in (1.0, 1.1, 1.2, 1.3, 1.45, 1.6):
        r_ = P.Rc[i_c] * f_
        z0_ = suelo(P.cx + r_ * ux, P.cy + r_ * uy)
        z1_ = suelo(P.cx + (r_ + 8.0) * ux, P.cy + (r_ + 8.0) * uy)
        n_s += 1
        if abs(z1_ - z0_) > 25.0:
            saltos += 1
            s_ej.append((k, round(r_), round(z0_), round(z1_)))
res['saltos_suelo_25m'] = saltos
print('suelo alrededor del penon: %d de %d pares (8 m radiales, r 1.0-1.6 Rc) con salto > 25 m; ejemplos %s' % (saltos, n_s, s_ej[:16]))

# 12) v3 N1: ninguna planta del penon en el ESPOLON de zona_caminos (eje info['espolon_eje'], 6 m de ancho: tronco a
# >= 3 + 2.6 m como _despejar_camino y copa fuera de la calzada), ni por fuera de la plataforma a < 14 m de la entrada,
# ni enterrada por la ladera (terreno > base + 0.3), ni un arbol a < 8 m del borde de la pista
def _d_pl(x, y, pl):
    best = 1e9
    for a, b in zip(pl, pl[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dy * dy or 1e-9
        f = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / l2))
        best = min(best, math.hypot(x - a[0] - f * dx, y - a[1] - f * dy))
    return best


esp = info.get('espolon_eje')
ex_, ey_, _ez = info['entrada']
r_ent = math.hypot(ex_ - P.cx, ey_ - P.cy)
v_esp, v_ent, v_ter, v_pis, d_esp_min = [], [], [], [], 99.0
for o in veg:
    x, y, z = o.matrix_world.translation
    mata = 'arbusto' in o.name
    cs_ = [o.matrix_world @ Vector(c) for c in o.bound_box]
    r_copa = max(max(c.x for c in cs_) - min(c.x for c in cs_), max(c.y for c in cs_) - min(c.y for c in cs_)) / 2.0
    if esp:
        d_ = _d_pl(x, y, esp)
        d_esp_min = min(d_esp_min, d_)
        if d_ < 3.0 + (1.0 if mata else max(2.6, r_copa)):
            v_esp.append((o.name, round(x, 1), round(y, 1), round(z, 1), round(d_, 1), round(r_copa, 1)))
    if math.hypot(x - ex_, y - ey_) < 14.0 and math.hypot(x - P.cx, y - P.cy) > r_ent - 1.0:
        v_ent.append((o.name, round(x, 1), round(y, 1), round(z, 1)))
    if z_terreno(x, y) > z + 0.3:
        v_ter.append((o.name, round(x, 1), round(y, 1), round(z, 1), round(z_terreno(x, y) - z, 2)))
    if not mata:
        dp_ = min(math.hypot(x - q['x'], y - q['y']) - q['w'] / 2 for q in S[::2])
        if dp_ < 7.9:
            v_pis.append((o.name, round(x, 1), round(y, 1), round(dp_, 1)))
res['veg_espolon'] = len(v_esp)
res['veg_boca_entrada'] = len(v_ent)
res['veg_bajo_terreno'] = len(v_ter)
res['arboles_junto_pista'] = len(v_pis)
print('espolon: eje %s; plantas en el espolon %d %s (planta mas cercana a %.1f m del eje; rechazadas al plantar %d), en la boca '
      'de la entrada %d %s, enterradas por la ladera %d %s, arboles a < 8 m de la pista %d %s'
      % ('ok' if esp else 'NO', len(v_esp), v_esp[:4], d_esp_min, info.get('veg_rechazada_espolon', 0), len(v_ent), v_ent[:4],
         len(v_ter), v_ter[:4], len(v_pis), v_pis[:4]))
if not esp or v_esp or v_ent or v_ter or v_pis:
    fallos.append('plantas: espolon %d (eje %s), boca %d, enterradas %d, junto a la pista %d'
                  % (len(v_esp), bool(esp), len(v_ent), len(v_ter), len(v_pis)))
# 13) v3 N3: barranco en V entre el flanco S del promontorio y el arcen N del penon (x 650-690, y -560..-530): suelo
# (max(terreno, roca)) sin saltos > 15 m entre puntos a 4 m; perfiles N-S como el revisor (vq4 grieta_perfiles)
saltos_n3, ej_n3 = 0, []
for xq in range(650, 691, 4):
    for yq in range(-560, -529, 4):
        z0_ = suelo(xq, yq)
        for (dx_, dy_) in ((4, 0), (0, 4)):
            if xq + dx_ > 690 or yq + dy_ > -530:
                continue
            z1_ = suelo(xq + dx_, yq + dy_)
            if abs(z1_ - z0_) > 15.0:
                saltos_n3 += 1
                ej_n3.append((xq, yq, round(z0_, 1), xq + dx_, yq + dy_, round(z1_, 1)))
res['saltos_barranco_N'] = saltos_n3
perf = []
for xq in range(652, 689, 6):
    perf.append((xq, [round(suelo(xq, yq), 1) for yq in range(-536, -576, -3)]))
print('barranco N (x 650-690, y -560..-530): %d pares con salto > 15 m en 4 m %s; relleno de fosos de tierra: %d columnas'
      % (saltos_n3, ej_n3[:6], info.get('relleno_foso_tierra', 0)))
print('   perfiles N-S (y -536 -> -575 cada 3 m): %s' % perf)
if saltos_n3:
    fallos.append('barranco N: %d saltos > 15 m' % saltos_n3)

# ---------------------------------------------------------------- contexto: terreno, mar, pista
def _mat_simple(nombre, rgba, rough=0.9):
    m = bpy.data.materials.get(nombre)
    if m is None:
        m = bpy.data.materials.new(nombre)
        m.use_nodes = True
        bs = m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = rgba
        bs.inputs['Roughness'].default_value = rough
    return m


R_CTX = 560
i0 = max(0, int((P.cx - R_CTX - T['x0']) / T['cell']))
i1 = min(T['nx'] - 1, int((P.cx + R_CTX - T['x0']) / T['cell']))
j0 = max(0, int((P.cy - R_CTX - T['y0']) / T['cell']))
j1 = min(T['ny'] - 1, int((P.cy + R_CTX - T['y0']) / T['cell']))
vs, fs, idx = [], [], {}
for j in range(j0, j1 + 1):
    for i in range(i0, i1 + 1):
        idx[(i, j)] = len(vs)
        vs.append((T['x0'] + i * T['cell'], T['y0'] + j * T['cell'], T['z'][j * T['nx'] + i]))
for j in range(j0, j1):
    for i in range(i0, i1):
        fs.append((idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
me = bpy.data.meshes.new('CTX_terreno')
me.from_pydata(vs, [], fs)
me.materials.append(_mat_simple('MAT_ctx_terreno', (0.34, 0.46, 0.20, 1)))
sc.collection.objects.link(bpy.data.objects.new('CTX_terreno', me))
me = bpy.data.meshes.new('CTX_mar')
me.from_pydata([(P.cx - 1500, P.cy - 1500, Z_MAR - 0.05), (P.cx + 1500, P.cy - 1500, Z_MAR - 0.05),
                (P.cx + 1500, P.cy + 1500, Z_MAR - 0.05), (P.cx - 1500, P.cy + 1500, Z_MAR - 0.05)], [], [(0, 1, 2, 3)])
me.materials.append(_mat_simple('MAT_ctx_mar', (0.06, 0.42, 0.58, 1), 0.3))
sc.collection.objects.link(bpy.data.objects.new('CTX_mar', me))
vs, fs = [], []
for i in range(N):
    q = S[i]
    if math.hypot(q['x'] - P.cx, q['y'] - P.cy) > 700:
        continue
    w = q['w'] / 2
    vs.append((q['x'] + q['nx'] * w, q['y'] + q['ny'] * w, q['z'] + 0.2))
    vs.append((q['x'] - q['nx'] * w, q['y'] - q['ny'] * w, q['z'] + 0.2))
    if len(vs) >= 4 and math.hypot(q['x'] - S[i - 1]['x'], q['y'] - S[i - 1]['y']) < 5:
        n = len(vs)
        fs.append((n - 4, n - 3, n - 1, n - 2))
me = bpy.data.meshes.new('CTX_pista')
me.from_pydata(vs, [], fs)
me.materials.append(_mat_simple('MAT_ctx_pista', (0.20, 0.20, 0.21, 1)))
sc.collection.objects.link(bpy.data.objects.new('CTX_pista', me))
# v3: el espolon de zona_caminos (cinta de 6 m por info['espolon_eje'], cota lineal de la boca a la entrada)
if esp:
    largo_ = [0.0]
    for a, b in zip(esp, esp[1:]):
        largo_.append(largo_[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    vs, fs = [], []
    n_e = max(2, int(largo_[-1] / 2.0))
    for k in range(n_e + 1):
        u = largo_[-1] * k / n_e
        j = max(0, min(len(esp) - 2, next((jj for jj in range(len(esp) - 1) if largo_[jj + 1] >= u), len(esp) - 2)))
        f = (u - largo_[j]) / max(1e-6, largo_[j + 1] - largo_[j])
        x = esp[j][0] + f * (esp[j + 1][0] - esp[j][0])
        y = esp[j][1] + f * (esp[j + 1][1] - esp[j][1])
        z = esp[0][2] + (esp[-1][2] - esp[0][2]) * u / largo_[-1]
        tx, ty = esp[j + 1][0] - esp[j][0], esp[j + 1][1] - esp[j][1]
        lt = math.hypot(tx, ty) or 1.0
        vs += [(x - ty / lt * 3.0, y + tx / lt * 3.0, z + 0.05), (x + ty / lt * 3.0, y - tx / lt * 3.0, z + 0.05)]
        if k:
            n = len(vs)
            fs.append((n - 4, n - 3, n - 1, n - 2))
    me = bpy.data.meshes.new('CTX_espolon')
    me.from_pydata(vs, [], fs)
    me.materials.append(_mat_simple('MAT_ctx_espolon', (0.28, 0.28, 0.30, 1)))
    sc.collection.objects.link(bpy.data.objects.new('CTX_espolon', me))

# ---------------------------------------------------------------- render
world = bpy.data.worlds.new('W')
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs[0].default_value = (0.58, 0.74, 0.96, 1)
bg.inputs[1].default_value = 0.75
sun = bpy.data.objects.new('Sol', bpy.data.lights.new('Sol', 'SUN'))
sun.data.energy = 2.3
sun.data.angle = math.radians(2.0)
sc.collection.objects.link(sun)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.clip_end = 5000.0
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
for attr, val in (('taa_render_samples', 24), ('use_shadows', True), ('use_raytracing', False)):
    try:
        setattr(sc.eevee, attr, val)
    except (AttributeError, TypeError):
        pass
sc.render.resolution_x, sc.render.resolution_y = 1280, 800
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'
os.makedirs(os.path.join(AQUI, 'previews'), exist_ok=True)
os.makedirs(os.path.join(AQUI, 'blend'), exist_ok=True)


def toma(nombre, pos, obj, lens=35.0, luz=(0.45, -0.55, -0.72)):
    cam.data.lens = lens
    cam.location = Vector(pos)
    cam.rotation_euler = (Vector(obj) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sun.rotation_euler = Vector(luz).normalized().to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(AQUI, 'previews', nombre + '.png')
    bpy.ops.render.render(write_still=True)


def desde(ang_deg, dist, alto):
    a = math.radians(ang_deg)
    return (P.cx + dist * math.cos(a), P.cy + dist * math.sin(a), alto)


for f_ in os.listdir(os.path.join(AQUI, 'previews')):
    if f_.startswith('roca_casino_'):
        os.remove(os.path.join(AQUI, 'previews', f_))
k_cam = max(10, min(len(baj) - 30, int(len(baj) * 0.42)))
p_cam, p_obj = baj[k_cam], baj[k_cam + 22]
toma('roca_casino_sureste', desde(-45, 470, 70), (P.cx, P.cy, 62), 35, (-0.55, 0.45, -0.70))
toma('roca_casino_noreste', desde(40, 430, z_top + 120), (P.cx, P.cy, 70), 35, (0.45, -0.55, -0.72))
toma('roca_casino_oeste', desde(175, 420, z_top + 55), (P.cx, P.cy, 85), 35, (0.35, -0.55, -0.72))
toma('roca_casino_sur', desde(-100, 450, 165), (P.cx, P.cy, 60), 35, (-0.35, 0.55, -0.70))
toma('roca_casino_cenital', (P.cx + 1.0, P.cy - 60.0, z_top + 600), (P.cx, P.cy, z_top - 40), 35, (0.45, -0.55, -0.72))
toma('roca_casino_carretera', (p_cam[0], p_cam[1], p_cam[2] + 1.5), (p_obj[0], p_obj[1], p_obj[2] + 1.0), 28, (-0.55, 0.45, -0.70))
if info['cala']:
    xq, yq, zq = info['cala']
    toma('roca_casino_cala', (xq, yq, zq + 1.6), (P.cx + 0.25 * (xq - P.cx), P.cy + 0.25 * (yq - P.cy), z_top - 25), 22, (-0.45, 0.5, -0.72))
    # v2: la cala desde el mar (casas, pantalan, lanchas) y desde arriba
    ux_, uy_ = xq - P.cx, yq - P.cy
    l_ = math.hypot(ux_, uy_) or 1.0
    ux_, uy_ = ux_ / l_, uy_ / l_
    toma('roca_casino_v2_cala_mar', (xq + ux_ * 110.0 - uy_ * 30.0, yq + uy_ * 110.0 + ux_ * 30.0, 24.0), (xq, yq, 8.0), 32, (-0.45, 0.5, -0.72))
    toma('roca_casino_v2_cala_alto', (xq + ux_ * 70.0, yq + uy_ * 70.0, 95.0), (xq, yq, 2.0), 30, (-0.45, 0.5, -0.72))
# v2: final de la calzada visto por el conductor (G2-01: antes una caja de roca cerrada a z 15.8)
k_f = max(0, len(baj) - 9)
toma('roca_casino_v2_fin_conductor', (baj[k_f][0], baj[k_f][1], baj[k_f][2] + 1.5),
     (baj[-1][0] + (baj[-1][0] - baj[k_f][0]), baj[-1][1] + (baj[-1][1] - baj[k_f][1]), baj[-1][2] + 0.8), 30, (-0.45, 0.5, -0.72))
# v2: las vistas del revisor (G2-01 fin, G2-05 grieta, G2-02 ranura SO) y la rotonda desde arriba
toma('roca_casino_v2_g01_fin_desde_mar', (860.0, -520.0, 32.0), (812.0, -563.0, 14.0), 32, (-0.45, 0.5, -0.72))
toma('roca_casino_v2_g05_grieta_alto', (637.2, -634.4, 154.9), (607.5, -640.0, 94.7), 30, (-0.45, 0.5, -0.72))
toma('roca_casino_v2_g05_grieta_piloto', (613.98, -616.96, 111.4), (603.39, -642.96, 101.6), 30, (-0.45, 0.5, -0.72))
toma('roca_casino_v2_g02_SO_ranura', (560.0, -700.0, 125.0), (606.0, -705.0, 80.0), 30, (-0.45, 0.5, -0.72))
toma('roca_casino_v2_cen_rotonda', (610.7, -621.4, 370.0), (610.7, -620.4, 110.0), 35, (-0.45, 0.5, -0.72))
toma('roca_casino_v2_foso_N', (590.0, -470.0, 160.0), (642.0, -526.0, 112.0), 30, (-0.45, 0.5, -0.72))
# v3: vistas del revisor de N1 (pino en el espolon) y N3 (barranco N), con el espolon dibujado (CTX_espolon)
toma('roca_casino_v3_n_norte_penon', (640.0, -520.0, 150.0), (675.0, -555.0, 100.0), 28, (-0.45, 0.5, -0.72))
toma('roca_casino_v3_n_norte_penon_e', (652.0, -572.0, 126.0), (682.0, -552.0, 100.0), 28, (-0.45, 0.5, -0.72))
toma('roca_casino_v3_g4_cresta_oeste', (470.0, -560.0, 175.0), (640.0, -520.0, 140.0), 28, (-0.45, 0.5, -0.72))
toma('roca_casino_v3_foso_N_cenital', (670.0, -549.0, 330.0), (670.0, -548.0, 110.0), 35, (-0.45, 0.5, -0.72))
toma('roca_casino_v3_foso_N_este', (760.0, -500.0, 150.0), (668.0, -552.0, 108.0), 30, (-0.45, 0.5, -0.72))
toma('roca_casino_v3_n_pino_espolon', (628.0, -566.0, 123.0), (644.0, -581.0, 120.0), 28, (-0.45, 0.5, -0.72))
toma('roca_casino_v3_n_espolon_hierba', (616.0, -558.0, 121.6), (640.0, -578.0, 119.4), 28, (-0.45, 0.5, -0.72))
toma('roca_casino_v3_espolon_aereo', (585.0, -490.0, 165.0), (620.0, -560.0, 118.0), 28, (-0.45, 0.5, -0.72))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, 'blend', 'roca_casino.blend'))
print('RESUMEN', json.dumps(res))
print('total %.0f s' % (time.time() - T0))
if fallos:
    for f in fallos:
        print('FALLO:', f)
    sys.exit(1)
print('OK test_roca_casino')
