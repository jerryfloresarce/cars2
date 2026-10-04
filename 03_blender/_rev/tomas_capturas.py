# -*- coding: utf-8 -*-
"""tomas_capturas.py - lista de tomas (camaras) de las capturas de revision, como funcion importable.

    import tomas_capturas
    tomas = tomas_capturas.construir_tomas(G, bpy)        # -> [(nombre, loc, tgt, lens), ...]

`construir_tomas` reproduce TAL CUAL la logica de 03_blender/renderizar_capturas.py (tomas 01-54, incluidas
las 5 rehechas en la ronda 15: 15, 34_roca_lazo_desde_pista, 40, 43, 47b) sin abrir ningun blend ni renderizar:
recibe la geometria `G` (geometria_3d.json / geometria_rev.json) y el modulo `bpy` con la escena YA abierta
(algunas tomas se calculan desde objetos: CASINO_root, PENON_puente, TUNEL_acantilado, YATE_, CAMARA_tierra...).
Anade las tomas nuevas del plan de la fase visual (FASE_VISUAL_PLAN.md seccion 1): postales 55-59 (+59b) y
60-63 (entender_agua_publico_capturas.md 9.2). renderizar_capturas.py NO se modifica (sigue con su copia).
Listar sin renderizar (por la cola):
    bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/tomas_capturas.py -- --blend X.blend --geom G.json
Convenciones: muestras cada 2 m; (nx, ny) = normal IZQUIERDA de la marcha (lado +1 = izquierda, hacia el mar
en la recta de meta); piloto = 1.4 m sobre el asfalto mirando 80 m adelante (objetivo a +1.2 m), lente 24.
"""
import json
import math
import os
import sys

# ------------------------------------------------------------------ nuevas tomas de la fase visual (seccion 1 del plan)
# nombre -> descripcion corta (se copia a camaras.json para el coordinador)
TOMAS_NUEVAS = {
    '55_postal_tunel_salida': 'postal 1: piloto s 528 (dentro del tunel) mirando a s 610, lente 20: portal, talud, mar',
    '56_postal_cima_bahia': 'postal 2: piloto s 1870 mirando al S (azimut con mas mar en 135-240 grados), lente 20',
    '57_postal_viaducto': 'postal 3: piloto s 3660 mirando a s 3760, lente 24: viaducto, lazo, mar',
    '58_postal_loews': 'postal 4: piloto s 3500 bajando, objetivo el centro de la Loews, lente 24',
    '59_postal_recta_puerto': 'postal 5: piloto s 60 mirando a s 140, lente 20: tribunas, puerto, McLaren',
    '59b_postal_recta_puerto_s5150': 'postal 5 variante: piloto s 5150 mirando 80 m adelante (s 30), lente 20',
    '60_puerto_llanta_cenital': 'cenital sobre el centro del puerto (PUERTO_dique / frame(60)+n*190) a 420 m, lente 35',
    '61_orilla_piloto_s150': 'piloto s 150 girado 35 grados hacia el mar (lado del mar segun la rejilla), lente 24',
    '62_tribuna_piloto_s5100': 'piloto s 5100 girado 30 grados al lado +1 (izquierda): la grada del mar, lente 24',
    '63_horizonte_piloto_s2200': 'piloto en la cima de tierra (s 2200) mirando al mar (azimut con mas mar, 150-270), lente 20',
}


def construir_tomas(G, bpy, incluir_nuevas=True):
    """Devuelve [(nombre, (x, y, z), (tx, ty, tz), lente)] con las tomas de renderizar_capturas.py y, si
    incluir_nuevas, las 55-63. No crea camaras ni renderiza; necesita la escena abierta en bpy."""
    from mathutils import Vector
    sc = bpy.context.scene
    S = G['muestras']; N = G['n']; paso = G['paso_m']; L = G['largo_m']
    CUR = {c['n']: c for c in G['curvas']}

    def fr(s_m):
        return S[int(round((s_m % L) / paso)) % N]

    def s_curva(n):
        return CUR[n]['s_idx'] * paso

    def tras(s_m, atras=90.0, alto=22.0, lateral=0.0, adelante=110.0, lens=30):
        """Camara detras de un punto de la pista mirando hacia delante."""
        p0 = fr(s_m - atras)
        p1 = fr(s_m + adelante)
        return ((p0['x'] + p0['nx'] * lateral, p0['y'] + p0['ny'] * lateral, p0['z'] + alto),
                (p1['x'], p1['y'], p1['z'] + 3.0), lens)

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
        # ronda 15: desde el mar, por fuera de la U (antes la roca del lazo tapaba la vista)
        ('15_final_puente_roca', (fr(s_curva(43))['x'] - fr(s_curva(43))['nx'] * 190, fr(s_curva(43))['y'] - fr(s_curva(43))['ny'] * 190,
                                  fr(s_curva(43))['z'] + 70), (fr(s_curva(43))['x'], fr(s_curva(43))['y'], fr(s_curva(43))['z'] + 8), 30),
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
        if _r is None or not any(o.name.startswith(('PPUEBLO', 'PENON_puente_roca', 'PENON_roca')) for o in _r.children_recursive):
            continue
        _bb = _bbox_centro(_r)
        _qr = fr(_s_ref)
        _dx, _dy = _bb[0] - _qr['x'], _bb[1] - _qr['y']
        _dl = math.hypot(_dx, _dy) or 1.0
        tomas.append((_tag + '_general', (_bb[0] - _dx / _dl * 330 - _dy / _dl * 120, _bb[1] - _dy / _dl * 330 + _dx / _dl * 120, _bb[3] + 60),
                      (_bb[0], _bb[1], (_bb[2] + _bb[3]) / 2), 30))
        if _nom == 'PENON_puente':
            # ronda 15: la roca del lazo es un macizo que llena el encuadre si se mira a su centro:
            # vista de piloto a lo largo de la calzada pegada a la pared (algo girada hacia la roca)
            _qa, _qb = fr(_s_ref - 60), fr(_s_ref + 20)
            _ld = 1.0 if ((_bb[0] - _qb['x']) * _qb['nx'] + (_bb[1] - _qb['y']) * _qb['ny']) > 0 else -1.0
            tomas.append((_tag + '_desde_pista', (_qa['x'], _qa['y'], _qa['z'] + 2.2),
                          (_qb['x'] + _qb['nx'] * _ld * 9.0, _qb['y'] + _qb['ny'] * _ld * 9.0, _qb['z'] + 6.0), 24))
        else:
            tomas.append((_tag + '_desde_pista', (_qr['x'], _qr['y'], _qr['z'] + 6), (_bb[0], _bb[1], _bb[2] + (_bb[3] - _bb[2]) * 0.45), 26))
    # ronda 13: caminos
    _qp = fr(870)
    tomas.append(('39_pueblo_calles_aerea', (_qp['x'] - _qp['nx'] * 40 - _qp['ny'] * 120, _qp['y'] - _qp['ny'] * 40 + _qp['nx'] * 120, _qp['z'] + 120),
                  (_qp['x'] - _qp['nx'] * 30, _qp['y'] - _qp['ny'] * 30, _qp['z']), 30))
    tomas.append(('40_pueblo_travesia', (_qp['x'] + _qp['nx'] * 3, _qp['y'] + _qp['ny'] * 3, _qp['z'] + 4),
                  (_qp['x'] - _qp['nx'] * 30, _qp['y'] - _qp['ny'] * 30, _qp['z'] + 3), 30))
    _qc = fr(s_curva(38))
    _rc = bpy.data.objects.get('PENON_cara')
    if _rc is not None and any(o.name.startswith(('PPUEBLO', 'PENON_roca')) for o in _rc.children_recursive):
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
    # la bajada recta vista desde la camara-grua amarilla de la rotonda (se busca a < 220 m del centro de la Loews;
    # si no hay ninguna, AVISO y la toma se hace igual desde el punto medido de la cresta)
    _cams_r = [o for o in bpy.data.objects if o.name.startswith('CAMARA_tierra') and o.parent is None
               and not any(c.name.startswith('LIB') for c in o.users_collection)
               and math.hypot(o.location.x - fr(s_loews)['x'], o.location.y - fr(s_loews)['y']) < 220]
    _q38 = fr(s_curva(38))
    if _cams_r:
        _cg = min(_cams_r, key=lambda o: math.hypot(o.location.x - fr(s_loews)['x'], o.location.y - fr(s_loews)['y']))
        # desde la cresta se mira bajar hacia la Loews; desde la rotonda, hacia la cresta
        _d38 = math.hypot(_cg.location.x - _q38['x'], _cg.location.y - _q38['y'])
        _dlw = math.hypot(_cg.location.x - fr(s_loews)['x'], _cg.location.y - fr(s_loews)['y'])
        _obj43 = (fr(s_loews)['x'], fr(s_loews)['y'], fr(s_loews)['z'] + 1.0) if _d38 < _dlw else (_q38['x'], _q38['y'], _q38['z'] + 1.0)
        tomas.append(('43_bajada_desde_grua', (_cg.location.x, _cg.location.y, _cg.location.z + 4.0), _obj43, 40))
    else:
        _qg = fr(3440.0)
        _lg = -(_qg['w'] / 2.0 + 10.0)
        print('AVISO capturas: no hay ninguna CAMARA_tierra (grua) a < 220 m de la rotonda Loews; la toma '
              '43_bajada_desde_grua se hace desde la cresta (s 3440, lado -1, 10 m) sin grua')
        tomas.append(('43_bajada_desde_grua', (_qg['x'] + _qg['nx'] * _lg, _qg['y'] + _qg['ny'] * _lg, _qg['z'] + 8.0),
                      (fr(s_loews)['x'], fr(s_loews)['y'], fr(s_loews)['z'] + 1.0), 40))
    _qm = fr(s_loews - 70)
    tomas.append(('44_bajada_recta_lateral', (_qm['x'] + _qm['nx'] * 45, _qm['y'] + _qm['ny'] * 45, _qm['z'] + 12),
                  (_qm['x'] - _qm['nx'] * 5, _qm['y'] - _qm['ny'] * 5, _qm['z'] + 2), 32))
    # empalme roca del lazo <-> viaducto y muelle de la roca
    _qv = fr(4336)
    tomas.append(('45_roca_lazo_puente', (_qv['x'] + _qv['ny'] * 40 + _qv['nx'] * 25, _qv['y'] - _qv['nx'] * 40 + _qv['ny'] * 25, _qv['z'] + 14),
                  (_qv['x'] - _qv['nx'] * 12, _qv['y'] - _qv['ny'] * 12, _qv['z'] - 2), 30))
    _pl = next((o for o in bpy.data.objects if o.name.startswith('PUERTO_pantalan_roca')), None)
    if _pl is None:
        _pl = next((o for o in bpy.data.objects if o.name.startswith('PENON_puente_muelle') and o.type == 'MESH'), None)
    if _pl is not None and _pl.name.startswith('PENON_puente_muelle'):
        # la malla del muelle de la cala va en coordenadas de mundo: se usa un vacio en su centro
        _bbm = [_pl.matrix_world @ Vector(c) for c in _pl.bound_box]
        _pl = type('P', (), {})()
        _pl.location = Vector((sum(v.x for v in _bbm) / 8, sum(v.y for v in _bbm) / 8, 0.0))
    _rl = bpy.data.objects.get('PENON_puente')
    if _pl is not None and _rl is not None and any(o.name.startswith(('PPUEBLO', 'PENON_puente_roca')) for o in _rl.children_recursive):
        _bl = _bbox_centro(_rl)
        _dxl, _dyl = _pl.location.x - _bl[0], _pl.location.y - _bl[1]
        _dll = math.hypot(_dxl, _dyl) or 1.0
        tomas.append(('46_roca_lazo_muelle', (_pl.location.x + _dxl / _dll * 85 + _dyl / _dll * 30, _pl.location.y + _dyl / _dll * 85 - _dxl / _dll * 30, 38),
                      (_pl.location.x - _dxl / _dll * 30, _pl.location.y - _dyl / _dll * 30, 12), 32))
    # yates VIP frente a la recta de meta y ermita del sendero
    _ys = [o for o in bpy.data.objects if o.name.startswith('YATE_') and o.parent is None
           and not any(c.name.startswith('LIB') for c in o.users_collection)]
    _yc = None
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
    # RONDA 15: VISTA DEL PILOTO (1.4 m sobre el asfalto, mirando 80 m adelante) en 6 puntos
    for _k, _sp in enumerate((300, 800, 1700, 2900, 3400, 4150)):
        _pa, _pb = fr(_sp), fr(_sp + 80)
        tomas.append(('%02d_piloto_s%d' % (49 + _k, _sp), (_pa['x'], _pa['y'], _pa['z'] + 1.4),
                      (_pb['x'], _pb['y'], _pb['z'] + 1.2), 24))
    # ronda 15: la 15 se mira desde FUERA de la U, en el lado contrario al centro de la roca del lazo
    _rl15 = bpy.data.objects.get('PENON_puente')
    if _rl15 is not None:
        _pts15 = [o.matrix_world @ Vector(c) for o in _rl15.children_recursive if o.type == 'MESH' for c in o.bound_box]
        if _pts15:
            _cx15 = sum(p.x for p in _pts15) / len(_pts15)
            _cy15 = sum(p.y for p in _pts15) / len(_pts15)
            _q15 = fr(s_curva(43))
            _ux, _uy = _q15['x'] - _cx15, _q15['y'] - _cy15
            _ul = math.hypot(_ux, _uy) or 1.0
            tomas = [((n_, (_q15['x'] + _ux / _ul * 200, _q15['y'] + _uy / _ul * 200, _q15['z'] + 75),
                       (_q15['x'] - _ux / _ul * 30, _q15['y'] - _uy / _ul * 30, _q15['z'] + 10), 30) if n_ == '15_final_puente_roca' else (n_, l_, t_, k_))
                     for (n_, l_, t_, k_) in tomas]
    # ronda 15: 40, 43 y 47b desde la propia pista (no hay nada encima de ella)
    _rehechas = {}
    _a40, _b40 = fr(840), fr(930)
    _o40 = -(_b40['w'] / 2.0 + 18.0)
    _rehechas['40_pueblo_travesia'] = ((_a40['x'], _a40['y'], _a40['z'] + 3.0),
                                       (_b40['x'] + _b40['nx'] * _o40, _b40['y'] + _b40['ny'] * _o40, _b40['z'] + 6.0), 26)
    _a43 = fr(3440.0)
    _rehechas['43_bajada_desde_grua'] = ((_a43['x'], _a43['y'], _a43['z'] + 5.0),
                                         (fr(s_loews)['x'], fr(s_loews)['y'], fr(s_loews)['z'] + 1.0), 32)
    if _ys:
        # el punto de la recta (lo mas cerca posible de L-70) desde el que la linea al yate no corta nada
        _dg47 = bpy.context.evaluated_depsgraph_get()
        _t47 = Vector((_yc.location.x, _yc.location.y, 4.0))
        _a47 = fr(L - 70)
        _o47 = Vector((_a47['x'], _a47['y'], _a47['z'] + 3.0))
        for _s47 in sorted(range(int(L - 300), int(L - 5), 10), key=lambda s_: abs(s_ - (L - 70))):
            _a = fr(_s47)
            _o = Vector((_a['x'], _a['y'], _a['z'] + 3.0))
            _d = _t47 - _o
            _ok, _hl, _hn, _hi, _hob, _hm = sc.ray_cast(_dg47, _o, _d.normalized(), distance=_d.length)
            _raiz = _hob
            while _raiz is not None and _raiz.parent is not None:
                _raiz = _raiz.parent
            if not _ok or (_raiz is not None and _raiz.name.startswith('YATE_')) or (_hl - _o).length > 0.92 * _d.length:
                _o47 = _o
                break
        _rehechas['47b_yates_desde_pista'] = (tuple(_o47), tuple(_t47), 30)
    tomas = [((n_,) + _rehechas[n_]) if n_ in _rehechas else (n_, l_, t_, k_) for (n_, l_, t_, k_) in tomas]

    if incluir_nuevas:
        tomas.extend(tomas_nuevas(G, bpy))
    # tuplas de floats planos (serializables en camaras.json)
    return [(n_, tuple(float(v) for v in l_), tuple(float(v) for v in t_), float(k_)) for (n_, l_, t_, k_) in tomas]


# ------------------------------------------------------------------ tomas nuevas 55-63
def _rejilla_mar(G):
    """Devuelve es_mar(x, y) -> bool (None fuera de la rejilla) a partir de G['terreno'] (orden iy, ix)."""
    T = G.get('terreno') or {}
    if not T or 'mar' not in T:
        return lambda x, y: None
    nx, ny, x0, y0, cell = T['nx'], T['ny'], T['x0'], T['y0'], T['cell']
    mar = T['mar']

    def es_mar(x, y):
        ix = int(round((x - x0) / cell)); iy = int(round((y - y0) / cell))
        if 0 <= ix < nx and 0 <= iy < ny:
            return bool(mar[iy * nx + ix])
        return None
    return es_mar


def azimut_mar(G, x, y, az_min, az_max, d0=200.0, d1=1200.0, paso_d=50.0, paso_az=5):
    """Azimut (grados desde el norte, sentido horario) entre az_min y az_max con MAS mar a lo largo de un rayo
    de d0 a d1 m desde (x, y); empates -> el mas cercano al centro del intervalo. Determinista desde G."""
    es_mar = _rejilla_mar(G)
    centro = (az_min + az_max) / 2.0
    mejor = None
    for az in range(int(az_min), int(az_max) + 1, paso_az):
        a = math.radians(az)
        dx, dy = math.sin(a), math.cos(a)
        vals = [es_mar(x + dx * d, y + dy * d) for d in _frange(d0, d1, paso_d)]
        frac = sum(1 for v in vals if v) / float(len(vals))
        clave = (frac, -abs(az - centro))
        if mejor is None or clave > mejor[0]:
            mejor = (clave, az)
    return mejor[1]


def _frange(a, b, p):
    out = []
    v = a
    while v <= b + 1e-9:
        out.append(v)
        v += p
    return out


def tomas_nuevas(G, bpy):
    """Las tomas 55-59 (+59b) y 60-63 de la seccion 1 del plan y de entender_agua 9.2."""
    S = G['muestras']; N = G['n']; paso = G['paso_m']; L = G['largo_m']
    es_mar = _rejilla_mar(G)

    def fr(s_m):
        return S[int(round((s_m % L) / paso)) % N]

    def tang(s_m):
        a, b = fr(s_m - 2 * paso), fr(s_m + 2 * paso)
        dx, dy = b['x'] - a['x'], b['y'] - a['y']
        l = math.hypot(dx, dy) or 1.0
        return dx / l, dy / l

    def piloto_a(s_a, s_b, lens):
        pa, pb = fr(s_a), fr(s_b)
        return (pa['x'], pa['y'], pa['z'] + 1.4), (pb['x'], pb['y'], pb['z'] + 1.2), lens

    def piloto_giro(s_m, giro_deg, lado, lens, dist=80.0):
        """Piloto en s_m mirando `dist` m en la direccion de marcha girada `giro_deg` hacia el lado (+1 izq / -1 der)."""
        p = fr(s_m)
        tx, ty = tang(s_m)
        nx, ny = p['nx'] * lado, p['ny'] * lado
        g = math.radians(giro_deg)
        dx, dy = math.cos(g) * tx + math.sin(g) * nx, math.cos(g) * ty + math.sin(g) * ny
        return (p['x'], p['y'], p['z'] + 1.4), (p['x'] + dx * dist, p['y'] + dy * dist, p['z'] + 1.2), lens

    def piloto_azimut(s_m, az_min, az_max, lens, dist=900.0, z_obj=0.0):
        p = fr(s_m)
        az = azimut_mar(G, p['x'], p['y'], az_min, az_max)
        a = math.radians(az)
        return (p['x'], p['y'], p['z'] + 1.4), (p['x'] + math.sin(a) * dist, p['y'] + math.cos(a) * dist, z_obj), lens

    def lado_mar(s_m, d=120.0):
        p = fr(s_m)
        for lado in (1, -1):
            if es_mar(p['x'] + p['nx'] * lado * d, p['y'] + p['ny'] * lado * d):
                return lado
        return 1

    s_loews = G['loews']['s_idx'] * paso
    q_lw = fr(s_loews)
    lw = G['loews']
    tomas = []
    tomas.append(('55_postal_tunel_salida', *piloto_a(528, 610, 20)))
    tomas.append(('56_postal_cima_bahia', *piloto_azimut(1870, 135, 240, 20)))
    tomas.append(('57_postal_viaducto', *piloto_a(3660, 3760, 24)))
    p35 = fr(3500)
    tomas.append(('58_postal_loews', (p35['x'], p35['y'], p35['z'] + 1.4), (lw['x'], lw['y'], q_lw['z'] + 1.0), 24))
    tomas.append(('59_postal_recta_puerto', *piloto_a(60, 140, 20)))
    tomas.append(('59b_postal_recta_puerto_s5150', *piloto_a(5150, 5230, 20)))
    # 60: centro del puerto = PUERTO_dique (raiz, vacio) o, si no esta, la regla de integrar_escena (frame(60)+n*190)
    dq = next((o for o in bpy.data.objects if o.name.startswith('PUERTO_dique') and o.parent is None and o.type == 'EMPTY'
               and not any(c.name.startswith('LIB') for c in o.users_collection)), None)
    if dq is not None:
        cx, cy = dq.matrix_world.translation.x, dq.matrix_world.translation.y
    else:
        p60 = fr(60)
        cx, cy = p60['x'] + p60['nx'] * 190, p60['y'] + p60['ny'] * 190
    tomas.append(('60_puerto_llanta_cenital', (cx, cy - 1.0, 420.0), (cx, cy, 0.0), 35))
    tomas.append(('61_orilla_piloto_s150', *piloto_giro(150, 35, lado_mar(150), 24)))
    tomas.append(('62_tribuna_piloto_s5100', *piloto_giro(5100, 30, 1, 24)))
    tomas.append(('63_horizonte_piloto_s2200', *piloto_azimut(2200, 150, 270, 20)))
    return tomas


# ------------------------------------------------------------------ listar (Blender, sin renderizar)
if __name__ == '__main__' and '--' in sys.argv:
    import bpy
    args = sys.argv[sys.argv.index('--') + 1:]
    blend = args[args.index('--blend') + 1]
    geom = args[args.index('--geom') + 1]
    G = json.load(open(geom, encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    tomas = construir_tomas(G, bpy)
    for n, l, t, k in tomas:
        print('%-32s loc=(%8.1f %8.1f %7.1f) tgt=(%8.1f %8.1f %7.1f) lente %g' % (n, *l, *t, k))
    print('TOMAS:', len(tomas))
