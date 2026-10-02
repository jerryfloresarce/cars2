# Capturas de revision para el usuario: recorre los puntos clave del circuito
# a altura de "dron bajo" y guarda renders/capturas/NN_nombre.png
import json
import math
import os

import bpy
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(BASE + r'\03_blender\geometria_3d.json', encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=BASE + r'\03_blender\porto_corsa.blend')
sc = bpy.context.scene
OUT = BASE + r'\03_blender\renders\capturas'
os.makedirs(OUT, exist_ok=True)
S = G['muestras']; N = G['n']; paso = G['paso_m']; L = G['largo_m']
CUR = {c['n']: c for c in G['curvas']}

def fr(s_m):
    return S[int(round((s_m % L) / paso)) % N]

def s_curva(n):
    return CUR[n]['s_idx'] * paso

def cam(name, loc, tgt, lens=30):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 12000
    c = bpy.data.objects.new(name, cd)
    c.location = Vector(loc)
    c.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(c)
    return c

def tras(s_m, atras=90.0, alto=22.0, lateral=0.0, adelante=110.0, lens=30):
    """Camara detras de un punto de la pista mirando hacia delante."""
    p0 = fr(s_m - atras)
    p1 = fr(s_m + adelante)
    return ((p0['x'] + p0['nx'] * lateral, p0['y'] + p0['ny'] * lateral, p0['z'] + alto),
            (p1['x'], p1['y'], p1['z'] + 3.0), lens)

sc.render.resolution_x = 1600
sc.render.resolution_y = 900

xs = [p['x'] for p in S]; ys = [p['y'] for p in S]
cxm, cym = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
s_tunel = (s_curva(2) + s_curva(3)) / 2 + 20
_ac = bpy.data.objects.get('TUNEL_acantilado')
s_in = float(_ac['s_in']) if _ac is not None and 's_in' in _ac else s_tunel - 72
s_out = float(_ac['s_out']) if _ac is not None and 's_out' in _ac else s_tunel + 72
s_loews = G['loews']['s_idx'] * paso

tomas = [
    ('01_aerea_general', (cxm - 300, cym - 1500, 1250), (cxm, cym, 30), 32),
    ('02_meta_y_puerto', *tras(0, atras=80, alto=14, lens=28)),
    ('03_tunel_entrada', *tras(s_in + 30, atras=110, alto=6, lens=28)),
    ('04_tunel_salida', (fr(s_in + 25)['x'], fr(s_in + 25)['y'], fr(s_in + 25)['z'] + 3.0),
     (fr(s_out)['x'], fr(s_out)['y'], fr(s_out)['z'] + 3.5), 28),
    ('05_pueblo_subida', *tras(s_curva(6), atras=90, alto=18)),
    ('06_pueblo_calle', *tras(880, atras=100, alto=14, lens=28)),
    ('07_tierra_subida', *tras(s_curva(15), atras=100, alto=20)),
    ('08_tierra_cima', *tras(s_curva(18), atras=120, alto=30)),
    ('09_bajada_recta', *tras(s_curva(30), atras=80, alto=16)),
    ('10_casino_sector', *tras(s_curva(34), atras=90, alto=24)),
    ('11_bajada_rotonda', (fr(s_curva(38) + 4)['x'], fr(s_curva(38) + 4)['y'], fr(s_curva(38) + 4)['z'] + 9),
     (fr(s_curva(39))['x'], fr(s_curva(39))['y'], fr(s_curva(39))['z'] + 2), 28),
    ('12_rotonda_loews', (fr(s_loews)['x'] - 60, fr(s_loews)['y'] - 50, fr(s_loews)['z'] + 30),
     (fr(s_loews)['x'], fr(s_loews)['y'], fr(s_loews)['z']), 40),
    ('13_puente_alto', *tras(s_curva(41), atras=80, alto=24)),
    ('14_puente_mar', (fr(4000)['x'] + fr(4000)['nx'] * 220, fr(4000)['y'] + fr(4000)['ny'] * 220, 60),
     (fr(3700)['x'], fr(3700)['y'], fr(3700)['z'] + 5), 30),
    ('15_final_puente_roca', *tras(s_curva(43), atras=80, alto=22)),
    ('16_retorno_chicane', *tras(s_curva(48), atras=90, alto=16)),
]
q = fr(s_out + 80)
tomas.append(('17_tunel_salida_exterior',
              (q['x'] + q['nx'] * 30, q['y'] + q['ny'] * 30, q['z'] + 20),
              (fr(s_out)['x'], fr(s_out)['y'], fr(s_out)['z'] + 5), 30))
# como la foto de referencia 'montana por dentro': el penon del casino desde el mar
_cas = next((o for o in bpy.data.objects if o.name.startswith('CASINO_root') and o.parent is None
             and not any(c.name == 'LIB' for c in o.users_collection)), None)
if _cas is not None:
    _dx, _dy = _cas.location.x - cxm, _cas.location.y - cym
    _dl = math.hypot(_dx, _dy) or 1.0
    _ux, _uy = _dx / _dl, _dy / _dl
    tomas.append(('19_penon_casino_foto',
                  (_cas.location.x + _ux * 210 - _uy * 230, _cas.location.y + _uy * 210 + _ux * 230, 95),
                  (_cas.location.x - _ux * 40, _cas.location.y - _uy * 40, _cas.location.z - 25), 30))
    tomas.append(('20_penon_casino_cerca',
                  (_cas.location.x + _ux * 60 + _uy * 190, _cas.location.y + _uy * 60 - _ux * 190, _cas.location.z + 25),
                  (_cas.location.x, _cas.location.y, _cas.location.z - 10), 35))
_pp = bpy.data.objects.get('PENON_puente')
if _pp is not None:
    tomas.append(('21_montana_dentro_del_lazo',
                  (_pp.location.x - 330, _pp.location.y - 300, 150),
                  (_pp.location.x, _pp.location.y, 30), 32))
    tomas.append(('22_viaducto_arcos_altos',
                  (fr(s_curva(41))['x'] - 260, fr(s_curva(41))['y'] - 120, 18),
                  (fr(s_curva(41))['x'], fr(s_curva(41))['y'], fr(s_curva(41))['z'] - 25), 28))
# frenada de la horquilla como el fotograma de la pelicula: zigzag amarillo y pianos por dentro
_q0 = fr(s_loews - 108)
tomas.append(('23_zigzag_y_pianos', (_q0['x'] + _q0['nx'] * 2.0, _q0['y'] + _q0['ny'] * 2.0, _q0['z'] + 9.0),
              (fr(s_loews - 45)['x'], fr(s_loews - 45)['y'], fr(s_loews - 45)['z']), 30))
_q1 = fr(s_loews)
tomas.append(('24_horquilla_cenital', (_q1['x'] - 25, _q1['y'] - 35, _q1['z'] + 48),
              (_q1['x'], _q1['y'], _q1['z']), 28))
for _m in (G.get('miradores') or []):
    _qa = fr(_m['s0'] - 40)
    tomas.append(('25_paseo_mirador_desde_pista', (_qa['x'], _qa['y'], _qa['z'] + 4.0),
                  (fr(_m['s0'] + 60)['x'] + fr(_m['s0'] + 60)['nx'] * _m['side'] * 10,
                   fr(_m['s0'] + 60)['y'] + fr(_m['s0'] + 60)['ny'] * _m['side'] * 10, fr(_m['s0'] + 60)['z'] + 2), 24))
    _qb = fr((_m['s0'] + _m['s1']) / 2)
    tomas.append(('26_paseo_y_parking_desde_abajo',
                  (_qb['x'] + _qb['nx'] * _m['side'] * 120 - _qb['ny'] * 70, _qb['y'] + _qb['ny'] * _m['side'] * 120 + _qb['nx'] * 70, _qb['z'] + 8),
                  (_qb['x'] + _qb['nx'] * _m['side'] * 20, _qb['y'] + _qb['ny'] * _m['side'] * 20, _qb['z'] - 4), 28))
# coches-camara: primer plano del primero que haya en tierra y de un helicoptero
_cams = [o for o in bpy.data.objects if o.name.startswith('CAMARA_tierra') and o.parent is None
         and not any(c.name == 'LIB' for c in o.users_collection)]
for _k, _c in enumerate(_cams[:3]):
    _i = min(range(N), key=lambda i: (S[i]['x'] - _c.location.x) ** 2 + (S[i]['y'] - _c.location.y) ** 2)
    _q = S[(_i - 14) % N]
    tomas.append(('27_coche_camara_%d' % _k, (_q['x'], _q['y'], _q['z'] + 3.0),
                  (_c.location.x, _c.location.y, _c.location.z + 2.5), 32))
_hel = next((o for o in bpy.data.objects if o.name.startswith('CAMARA_heli') and o.parent is None
             and not any(c.name == 'LIB' for c in o.users_collection)), None)
if _hel is not None:
    tomas.append(('28_helicoptero_camara', (_hel.location.x - 30, _hel.location.y - 38, _hel.location.z + 6),
                  (_hel.location.x, _hel.location.y, _hel.location.z - 2), 40))
pen = bpy.data.objects.get('PENON_lado_derecho')
if pen:
    q = fr(s_in - 80)
    tomas.append(('18_montana_coche', (q['x'], q['y'], q['z'] + 14),
                  (pen.location.x, pen.location.y, pen.location.z + 12), 28))
# ---- ronda 12: boxes, montana-rueda, rocas-pueblo, rotonda ----
def _bbox_centro(raiz):
    xs, ys, zs = [], [], []
    for o in [raiz] + list(raiz.children_recursive):
        if o.type == 'MESH':
            for c_ in o.bound_box:
                w_ = o.matrix_world @ Vector(c_)
                xs.append(w_.x); ys.append(w_.y); zs.append(w_.z)
    if not xs:
        return None
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs), max(zs))
_pb = next((o for o in bpy.data.objects if o.name.startswith('PIT_boxes') and o.parent is None
            and not any(c.name.startswith('LIB') for c in o.users_collection)), None)
if _pb is not None:
    _qb = fr(L - 40)
    tomas.append(('29_boxes_desde_pista', (_qb['x'] + _qb['nx'] * 6, _qb['y'] + _qb['ny'] * 6, _qb['z'] + 7),
                  (_pb.location.x, _pb.location.y, _pb.location.z + 9), 28))
    _qc = fr(L - 60)
    tomas.append(('30_boxes_tribuna_aerea', (_pb.location.x + _qc['nx'] * 150 + _qc['ny'] * 90, _pb.location.y + _qc['ny'] * 150 - _qc['nx'] * 90, _pb.location.z + 75),
                  (_pb.location.x, _pb.location.y, _pb.location.z + 8), 30))
    tomas.append(('31_boxes_pit_lane', (fr(L - 150)['x'] - fr(L - 150)['nx'] * 13.5, fr(L - 150)['y'] - fr(L - 150)['ny'] * 13.5, fr(L - 150)['z'] + 3.5),
                  (fr(L - 40)['x'] - fr(L - 40)['nx'] * 16, fr(L - 40)['y'] - fr(L - 40)['ny'] * 16, fr(L - 40)['z'] + 4), 30))
_tr = bpy.data.objects.get('TUNEL_acantilado')
_es_coche = _tr is not None and (('MCOCHE' in (_tr.data.name if _tr.type == 'MESH' else '')) or any(o.name.startswith('MCOCHE') for o in _tr.children_recursive))
_es_rueda = _tr is not None and (('MRUEDA' in (_tr.data.name if _tr.type == 'MESH' else '')) or any(o.name.startswith('MRUEDA') for o in _tr.children_recursive))
if _es_coche:
    # coche fosil: origen = rueda delantera; los coches llegan por -Y local (= -t); el morro apunta a +X local (= -n, tierra adentro)
    _ang = _tr.rotation_euler.z
    _xx, _xy = math.cos(_ang), math.sin(_ang)        # +X local
    _yx, _yy = -math.sin(_ang), math.cos(_ang)       # +Y local
    _cz = _tr.location.z + 28.0
    tomas.append(('32_montana_coche_lado', (_tr.location.x - _yx * 200 - _xx * 70, _tr.location.y - _yy * 200 - _xy * 70, _cz + 25),
                  (_tr.location.x - _xx * 60, _tr.location.y - _xy * 60, _cz + 10), 30))
    _qi = fr(s_in - 70)
    tomas.append(('33_montana_coche_desde_pista', (_qi['x'], _qi['y'], _qi['z'] + 5), (_tr.location.x - _yx * 20, _tr.location.y - _yy * 20, _cz - 10), 26))
    tomas.append(('33b_montana_coche_34', (_tr.location.x - _yx * 150 + _xx * 140, _tr.location.y - _yy * 150 + _xy * 140, _cz + 60),
                  (_tr.location.x - _xx * 50, _tr.location.y - _xy * 50, _cz + 15), 32))
elif _es_rueda:
    _ang = _tr.rotation_euler.z
    _fx, _fy = -math.sin(_ang), math.cos(_ang)     # +Y local = cara de la rueda
    _cz = _tr.location.z + 44.0
    tomas.append(('32_montana_rueda_frente', (_tr.location.x + _fx * 175 - _fy * 60, _tr.location.y + _fy * 175 + _fx * 60, _cz - 5),
                  (_tr.location.x + _fx * 20, _tr.location.y + _fy * 20, _cz - 8), 32))
    _qi = fr(s_in - 60)
    tomas.append(('33_montana_rueda_desde_pista', (_qi['x'], _qi['y'], _qi['z'] + 5), (_tr.location.x + _fx * 30, _tr.location.y + _fy * 30, _cz - 14), 24))
for _nom, _tag, _s_ref in (('PENON_puente', '34_roca_lazo', s_curva(43)), ('PENON_cara', '36_roca_casino', s_curva(37))):
    _r = bpy.data.objects.get(_nom)
    if _r is None or not any(o.name.startswith('PPUEBLO') for o in _r.children_recursive):
        continue
    _bb = _bbox_centro(_r)
    _qr = fr(_s_ref)
    _dx, _dy = _bb[0] - _qr['x'], _bb[1] - _qr['y']
    _dl = math.hypot(_dx, _dy) or 1.0
    tomas.append((_tag + '_general', (_bb[0] - _dx / _dl * 330 - _dy / _dl * 120, _bb[1] - _dy / _dl * 330 + _dx / _dl * 120, _bb[3] + 60),
                  (_bb[0], _bb[1], (_bb[2] + _bb[3]) / 2), 30))
    tomas.append((_tag + '_desde_pista', (_qr['x'], _qr['y'], _qr['z'] + 6), (_bb[0], _bb[1], _bb[2] + (_bb[3] - _bb[2]) * 0.45), 26))
# ronda 13: caminos
_qp = fr(870)
tomas.append(('39_pueblo_calles_aerea', (_qp['x'] - _qp['nx'] * 40 - _qp['ny'] * 120, _qp['y'] - _qp['ny'] * 40 + _qp['nx'] * 120, _qp['z'] + 120),
              (_qp['x'] - _qp['nx'] * 30, _qp['y'] - _qp['ny'] * 30, _qp['z']), 30))
tomas.append(('40_pueblo_travesia', (_qp['x'] + _qp['nx'] * 3, _qp['y'] + _qp['ny'] * 3, _qp['z'] + 4),
              (_qp['x'] - _qp['nx'] * 30, _qp['y'] - _qp['ny'] * 30, _qp['z'] + 3), 30))
_qc = fr(s_curva(38))
_rc = bpy.data.objects.get('PENON_cara')
if _rc is not None and any(o.name.startswith('PPUEBLO') for o in _rc.children_recursive):
    _bc = _bbox_centro(_rc)
    _dxc, _dyc = _bc[0] - _qc['x'], _bc[1] - _qc['y']
    _dlc = math.hypot(_dxc, _dyc) or 1.0
    tomas.append(('41_espolon_casino', (_qc['x'] - _dxc / _dlc * 60 + _dyc / _dlc * 40, _qc['y'] - _dyc / _dlc * 60 - _dxc / _dlc * 40, _qc['z'] + 40),
                  (_qc['x'] + _dxc / _dlc * 45, _qc['y'] + _dyc / _dlc * 45, _qc['z'] + 4), 30))
_pbx = next((o for o in bpy.data.objects if o.name.startswith('PIT_boxes') and o.parent is None
             and not any(c.name.startswith('LIB') for c in o.users_collection)), None)
if _pbx is not None:
    _qb2 = fr(L - 60)
    tomas.append(('42_paddock_hotel', (_pbx.location.x + _qb2['nx'] * 60 - _qb2['ny'] * 160, _pbx.location.y + _qb2['ny'] * 60 + _qb2['nx'] * 160, _pbx.location.z + 90),
                  (_pbx.location.x - _qb2['nx'] * 50, _pbx.location.y - _qb2['ny'] * 50, _pbx.location.z + 20), 30))
# la bajada recta vista desde la camara-grua amarilla de la rotonda (peticion: desde ahi no se ve lo que hay tras la cresta)
_cams_r = [o for o in bpy.data.objects if o.name.startswith('CAMARA_tierra') and o.parent is None
           and not any(c.name.startswith('LIB') for c in o.users_collection)
           and math.hypot(o.location.x - fr(s_loews)['x'], o.location.y - fr(s_loews)['y']) < 90]
_q38 = fr(s_curva(38))
if _cams_r:
    _cg = min(_cams_r, key=lambda o: math.hypot(o.location.x - fr(s_loews)['x'], o.location.y - fr(s_loews)['y']))
    tomas.append(('43_bajada_desde_grua', (_cg.location.x, _cg.location.y, _cg.location.z + 4.0),
                  (_q38['x'], _q38['y'], _q38['z'] + 1.0), 40))
_qm = fr(s_loews - 70)
tomas.append(('44_bajada_recta_lateral', (_qm['x'] + _qm['nx'] * 45, _qm['y'] + _qm['ny'] * 45, _qm['z'] + 12),
              (_qm['x'] - _qm['nx'] * 5, _qm['y'] - _qm['ny'] * 5, _qm['z'] + 2), 32))
# empalme roca del lazo <-> viaducto y muelle de la roca
_qv = fr(4336)
tomas.append(('45_roca_lazo_puente', (_qv['x'] + _qv['ny'] * 40 + _qv['nx'] * 25, _qv['y'] - _qv['nx'] * 40 + _qv['ny'] * 25, _qv['z'] + 14),
              (_qv['x'] - _qv['nx'] * 12, _qv['y'] - _qv['ny'] * 12, _qv['z'] - 2), 30))
_pl = next((o for o in bpy.data.objects if o.name.startswith('PUERTO_pantalan_roca')), None)
_rl = bpy.data.objects.get('PENON_puente')
if _pl is not None and _rl is not None and any(o.name.startswith('PPUEBLO') for o in _rl.children_recursive):
    _bl = _bbox_centro(_rl)
    _dxl, _dyl = _pl.location.x - _bl[0], _pl.location.y - _bl[1]
    _dll = math.hypot(_dxl, _dyl) or 1.0
    tomas.append(('46_roca_lazo_muelle', (_pl.location.x + _dxl / _dll * 85 + _dyl / _dll * 30, _pl.location.y + _dyl / _dll * 85 - _dxl / _dll * 30, 38),
                  (_pl.location.x - _dxl / _dll * 30, _pl.location.y - _dyl / _dll * 30, 12), 32))
# yates VIP frente a la recta de meta y ermita del sendero
_ys = [o for o in bpy.data.objects if o.name.startswith('YATE_') and o.parent is None
       and not any(c.name.startswith('LIB') for c in o.users_collection)]
if _ys:
    _yc = min(_ys, key=lambda o: math.hypot(o.location.x - fr(L - 70)['x'], o.location.y - fr(L - 70)['y']))
    _qy = fr(L - 70)
    tomas.append(('47_yates_vip', (_yc.location.x + _qy['nx'] * 70 + _qy['ny'] * 90, _yc.location.y + _qy['ny'] * 70 - _qy['nx'] * 90, 28),
                  (_yc.location.x - _qy['nx'] * 20, _yc.location.y - _qy['ny'] * 20, 4), 30))
    tomas.append(('47b_yates_desde_pista', (_qy['x'] + _qy['nx'] * 8, _qy['y'] + _qy['ny'] * 8, _qy['z'] + 5),
                  (_yc.location.x, _yc.location.y, 6), 32))
_er = next((o for o in bpy.data.objects if o.name.startswith('ITAL_ermita') and o.parent is None
            and not any(c.name.startswith('LIB') for c in o.users_collection)), None)
if _er is not None:
    tomas.append(('48_ermita_sendero', (_er.location.x + 60, _er.location.y - 75, _er.location.z + 40),
                  (_er.location.x, _er.location.y, _er.location.z + 4), 32))
_q2 = fr(s_loews + 40)
tomas.append(('38_rotonda_lateral', (_q2['x'] + _q2['nx'] * 14, _q2['y'] + _q2['ny'] * 14, _q2['z'] + 6),
              (fr(s_loews)['x'], fr(s_loews)['y'], fr(s_loews)['z'] + 1), 30))
_solo = os.environ.get('CAPTURAS_SOLO', '')
for nombre, loc, tgt, lens in tomas:
    if _solo and not nombre.startswith(tuple(_solo.split(','))):
        continue
    c = cam('CAP_' + nombre, loc, tgt, lens)
    sc.camera = c
    sc.render.filepath = os.path.join(OUT, nombre + '.png')
    bpy.ops.render.render(write_still=True)
    print('captura:', nombre)
print('OK capturas')
