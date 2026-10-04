# -*- coding: utf-8 -*-
"""cierre_ac.py - FISICA de Assetto Corsa en la escena de export. Lo llama exportar_ac.py al final del renombrado
(con todo ya en 1WALL_/1ROAD_/1PIT_..., la rampa de garajes y los AC_* creados): construir(G, log).

En AC solo colisiona lo que tiene prefijo fisico y NO se dibujan las caras de espaldas. Pasos:
  0. recorte_pit(): el pit lane es la unica superficie de su carril y sin muros dentro: las calzadas secundarias que
     se metian en la losa 1PIT_pit (asomaban 7-11 cm en la entrada y en la salida) se hunden bajo ella y se cosen a
     su borde; los muros de caminos que entraban en el carril (1WALL_camino_muro.108, 1.5 m) se recortan y se tapan.
  1. orientar_barreras(): mallas 1WALL_ CERRADAS con el volumen al reves (normales hacia dentro: la roca del lazo)
     -> se les da la vuelta (caras y normales personalizadas); mallas 1WALL_ ABIERTAS cerca de la pista que desde
     ella se ven por detras (guardarrailes, vallas, pretiles, arcadas...) -> DOS CARAS (copia invertida). Eran
     barreras que "parece que estan pero son invisibles".
  2. subdividir_pista(): la calzada (2 vertices por seccion) se parte en 8 tramos a lo ancho: sin pliegues de
     4-22 cm en las curvas con pendiente (tierra). terreno_bajo_asfalto(): los vertices de 1GRASS_terreno dentro del
     asfalto bajan a plano-0.05 y las aristas que asomarian en el borde se parten alli (la hierba no asoma sobre la
     calzada y por fuera del borde el terreno no se hunde).
     pianos_rampa(): borde interior y extremos de los pianos a +1.2 cm (eran un escalon vertical de 5 cm).
  3. cuna_pit(): el arcen 2GRASS_arcen_der entre el borde de la pista y el borde interior del pit lane sube en rampa
     hasta la cota del pit lane (escalones de 0.08-0.68 m y ranura entre el muro de boxes y el pit lane); en la cuna
     se subdivide para seguir la S de la tira invisible y su borde se cose a la cota de la calzada.
     chaflan_horquilla(): en el apice colapsado de la horquilla de tierra el canto del arcen en voladizo pasa a talud.
     labio_viaducto(): copia fisica invisible del labio visible del tablero del viaducto (0.5-0.6 m por fuera del borde).
  4. rampa_garajes(): 1PIT_boxes_rampa en S (cubica) con el largo que pide su desnivel (cambio de pendiente <= 7 %
     por metro), por toda la fila de garajes y la zanja de sus extremos, buscando el borde del carril por rayos.
  5. muros_cierre(): 1WALL_cierre_izq / 1WALL_cierre_der, muro vertical continuo a los dos lados de TODA la pista
     (z_borde-1 .. z_borde+3, siguiendo el suelo), al final de la zona de escape (w/2 + 6.75), justo detras de las
     barreras reales (pretil, guardarrail, bordillo alto, tunel), por fuera del pit lane en la zona de boxes (sin
     tapar los garajes) y por la mediana donde hay otro ramal cerca; tapones_boxes() lo une a las paredes de los
     extremos del edificio de boxes. kn5_writer_opt.py lo escribe INVISIBLE (isRenderable=0, sin sombra) porque su
     nombre lleva 'cierre'.
  6. cierre_horquillas(): 1WALL_cierre_horquillas, muro invisible a 2.5 m del borde INTERIOR de las horquillas (dos
     partes de la pista lejos en s y cerca en planta, con la pista girando >= 90 grados entre ellas) y de las curvas
     cerradas (radio < 30 m, giro >= 30 grados), cosido al cierre normal: no se puede pasar por la hierba de un ramal
     al otro ni cortar la curva por dentro.
"""
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, kdtree
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from revisar_fisica_ac import (Pista, PitLane, bvh_de, caras_gemelas, es_invisible, mallas_mundo,  # noqa: E402
                               objetos_exportables, SUELO_PREF, MURO_PREF)

E_ESCAPE = 6.75          # fin del arcen de hierba (m desde el borde)
E_MIN = 1.0              # el cierre nunca a menos de esto del borde (salvo puentes)
E_MIN_PUENTE = 0.6
DETRAS = 0.4             # detras de una barrera real
PEND_TRANS = 0.5         # el cierre se acerca/aleja como mucho 0.5 m por metro de pista
DS_CIERRE = 1.0          # paso del muro de cierre a lo largo de la pista
MAT_INVISIBLE = 'MAT_cierre_invisible'


def _sin_sel():
    for o in bpy.context.selected_objects:
        o.select_set(False)


def _cerca_pista(P, kd):
    def cerca(ob, margen):
        cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        cx = sum(c.x for c in cs) / 8.0
        cy = sum(c.y for c in cs) / 8.0
        r = max(math.hypot(c.x - cx, c.y - cy) for c in cs)
        _c, i, d = kd.find((cx, cy, 0.0))
        return d - r < P.S[i]['w'] / 2.0 + margen
    return cerca


def _kd_pista(P):
    kd = kdtree.KDTree(P.N)
    for i, q in enumerate(P.S):
        kd.insert((q['x'], q['y'], 0.0), i)
    kd.balance()
    return kd


def _lateral(P, kd, x, y):
    """(s, u, t, q): abscisa, distancia lateral (+ = izquierda), desvio longitudinal y marco en la proyeccion."""
    _c, i, _d = kd.find((x, y, 0.0))
    q0 = P.S[i]
    t = (x - q0['x']) * q0['ny'] - (y - q0['y']) * q0['nx']
    t = max(-P.paso, min(P.paso, t))
    q = P.marco(i * P.paso + t)
    u = (x - q['x']) * q['nx'] + (y - q['y']) * q['ny']
    t2 = (x - q['x']) * q['ny'] - (y - q['y']) * q['nx']
    return q['s'], u, t2, q


# ----------------------------------------------------------------------------- 0. pit lane libre de caminos
# calzadas y muros SECUNDARIOS (red de caminos y plan urbano) que pueden invadir la losa del pit lane
PIT_AJENOS_SUELO = ('1ROAD_camino_', '1ROAD_calle_', '1ROAD_acera_', '1DIRT_camino_', '1KERB_bordillo')
PIT_AJENOS_MURO = ('1WALL_camino_', '1WALL_bordillo', '1WALL_calle_')


def _bbox_mundo(ob):
    cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (min(c.x for c in cs), min(c.y for c in cs), max(c.x for c in cs), max(c.y for c in cs))


def _solapa(a, b, m):
    return a[0] - m <= b[2] and b[0] - m <= a[2] and a[1] - m <= b[3] and b[1] - m <= a[3]


def _borde_losa(me, mw, paso=0.1):
    """KD-tree (xy) de puntos cada `paso` m por las aristas de contorno de una losa y su cota en cada punto."""
    pts = []
    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:
        if len(e.link_faces) != 1:
            continue
        a, b = mw @ e.verts[0].co, mw @ e.verts[1].co
        n = max(1, int((b - a).length / paso))
        for j in range(n + 1):
            pts.append(a.lerp(b, j / float(n)))
    bm.free()
    kd = kdtree.KDTree(max(1, len(pts)))
    for i, p in enumerate(pts):
        kd.insert((p.x, p.y, 0.0), i)
    kd.balance()
    return kd, [p.z for p in pts]


def recorte_pit(G, log, margen=0.15, dz=1.2, hundir=0.04, banda=1.5, llano=0.4):
    """El pit lane (1PIT_pit) tiene que ser la UNICA superficie de su carril y sin muros dentro:
      - calzadas secundarias (PIT_AJENOS_SUELO) que se meten en la losa (1ROAD_camino_adoquin.034 asomaba 11 cm en la
        entrada, 1ROAD_camino_asfalto.043 4-7 cm en la entrada y en la salida, s ~90): sus vertices dentro de la huella
        de la losa (a menos de dz de su cota) bajan `hundir` m bajo ella y, en una banda de `banda` m por fuera del
        borde (los primeros `llano` m a la cota del borde - hundir), se cosen a la cota del borde (la calzada llega a
        ras al pit lane, sin escalon ni hueco);
      - muros de caminos (PIT_AJENOS_MURO; 1WALL_camino_muro.108 entraba 1.5 m en el carril de entrada, s 5048-5062):
        se borran sus caras con algun vertice o el centro a mas de `margen` m dentro del carril y a menos de dz de la
        cota de la losa, y se tapa la boca abierta."""
    pits = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.split('.')[0] == '1PIT_pit']
    PL = PitLane(G, kdtree)
    if not pits or len(PL.Q) < 2:
        log('fisica: recorte_pit: no hay 1PIT_pit / pit_lane')
        return {}
    dg = bpy.context.evaluated_depsgraph_get()
    bvh, _o, _n = bvh_de(pits, dg, np, BVHTree, 'pit')
    kd_b, z_b = _borde_losa(pits[0].data, pits[0].matrix_world)
    bb_pit = _bbox_mundo(pits[0])
    abajo = Vector((0.0, 0.0, -1.0))

    def losa(x, y, z):
        loc, _nn, _i, _d = bvh.ray_cast(Vector((x, y, z + dz)), abajo, 2.0 * dz)
        return loc.z if loc is not None else None

    res = {'suelo': {}, 'muro': {}}
    lib = bpy.data.collections.get('LIB')
    en_lib = set(o.name for o in lib.all_objects) if lib else set()      # plantillas: exportar_ac las borra
    for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(PIT_AJENOS_SUELO + PIT_AJENOS_MURO)
               and o.name not in en_lib and _solapa(_bbox_mundo(o), bb_pit, banda + 0.5)]:
        es_muro = ob.name.startswith(PIT_AJENOS_MURO)
        mw = ob.matrix_world
        mwi = mw.inverted()
        W = [mw @ v.co for v in ob.data.vertices]
        if not es_muro:
            nuevos = {}
            for k, w in enumerate(W):
                zp = losa(w.x, w.y, w.z)
                if zp is not None and abs(w.z - zp) < dz:
                    if w.z > zp - hundir:
                        nuevos[k] = zp - hundir
                    continue
                _c, j, d = kd_b.find((w.x, w.y, 0.0))
                if j is None or d >= banda or abs(w.z - z_b[j]) > 0.3:
                    continue
                f = _smooth((d - llano) / (banda - llano))     # 0 hasta `llano` m del borde: las caras que cruzan
                zt = (z_b[j] - hundir) + (w.z - (z_b[j] - hundir)) * f    # el borde no asoman sobre la losa
                if abs(zt - w.z) > 0.002:
                    nuevos[k] = zt
            if not nuevos:
                continue
            if ob.data.users > 1:
                ob.data = ob.data.copy()
            me = ob.data
            for k, z in nuevos.items():
                me.vertices[k].co = mwi @ Vector((W[k].x, W[k].y, z))
            me.update()
            res['suelo'][ob.name] = [len(nuevos), round(max(abs(W[k].z - z) for k, z in nuevos.items()), 3)]
            continue
        dentro_v = [PL.dentro(w.x, w.y, margen) and (losa(w.x, w.y, w.z) is not None) for w in W]
        malas = []
        for f in ob.data.polygons:
            c = mw @ f.center
            if any(dentro_v[i] for i in f.vertices) or (PL.dentro(c.x, c.y, margen) and losa(c.x, c.y, c.z) is not None):
                malas.append(f.index)
        if not malas:
            continue
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        n_tapas = _borrar_y_tapar(ob.data, malas)
        res['muro'][ob.name] = [len(malas), n_tapas]
    log('fisica: pit lane libre: calzadas hundidas bajo la losa / cosidas a su borde %s; muros recortados del carril '
        '(caras, tapas) %s' % (res['suelo'], res['muro']))
    return res


def _borrar_y_tapar(me, malas, lados_max=16):
    """Borra las caras `malas` y tapa las bocas pequenas que quedan (la normal de la tapa mira hacia lo borrado)."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    quitar = [bm.faces[i] for i in malas]
    centros = [f.calc_center_median() for f in quitar]
    borde = {e for f in quitar for e in f.edges if any(g not in quitar for g in e.link_faces)}
    bmesh.ops.delete(bm, geom=quitar, context='FACES')
    borde = [e for e in borde if e.is_valid and len(e.link_faces) == 1]
    # cadenas conexas de aristas nuevas de contorno: lazo cerrado pequeno -> holes_fill; cadena abierta (el corte se
    # une al contorno de la base abierta del muro) -> se cierra con la arista entre sus extremos y se rellena
    resto = set(borde)
    tapas = []
    while resto:
        e0 = resto.pop()
        cad, pila = {e0}, [e0]
        while pila:
            e = pila.pop()
            for v in e.verts:
                for e2 in v.link_edges:
                    if e2 in resto:
                        resto.discard(e2)
                        cad.add(e2)
                        pila.append(e2)
        grado = {}
        for e in cad:
            for v in e.verts:
                grado[v] = grado.get(v, 0) + 1
        ext = [v for v, g in grado.items() if g == 1]
        if not ext and len(cad) <= lados_max:
            tapas += bmesh.ops.holes_fill(bm, edges=list(cad), sides=lados_max)['faces']
        elif len(ext) == 2 and len(cad) <= 4 * lados_max:
            ec = bm.edges.get(ext) or bm.edges.new(ext)
            c = sum((v.co for v in grado), Vector()) / len(grado)
            ref = min(centros, key=lambda p: (p - c).length_squared)
            nrm = (ref - c)
            nrm.z = 0.0
            if nrm.length > 1e-6:
                g = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=list(cad) + [ec],
                                            normal=nrm.normalized())['geom']
                tapas += [x for x in g if isinstance(x, bmesh.types.BMFace)]
    for f in tapas:
        c = f.calc_center_median()
        ref = min(centros, key=lambda p: (p - c).length_squared)
        f.normal_update()
        if f.normal.dot(ref - c) < 0:
            f.normal_flip()
    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(tapas)


# ----------------------------------------------------------------------------- 1. orientar barreras
def _invertir(me):
    """Da la vuelta a todas las caras; si hay normales personalizadas tambien se invierten (misma esquina)."""
    cust = me.has_custom_normals
    if cust:
        nl = len(me.loops)
        cn = np.empty(nl * 3, np.float32)
        me.corner_normals.foreach_get('vector', cn)
        cn = cn.reshape(-1, 3)
        lv = np.empty(nl, np.int32)
        me.loops.foreach_get('vertex_index', lv)
        lt = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get('loop_total', lt)
        lp = np.repeat(np.arange(len(me.polygons)), lt)
        mapa = {(int(p), int(v)): k for k, (p, v) in enumerate(zip(lp, lv))}
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    if cust:
        lv2 = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get('vertex_index', lv2)
        lt2 = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get('loop_total', lt2)
        lp2 = np.repeat(np.arange(len(me.polygons)), lt2)
        idx = np.array([mapa.get((int(p), int(v)), 0) for p, v in zip(lp2, lv2)], np.int64)
        me.normals_split_custom_set([tuple(v) for v in (-cn[idx])])
    me.update()


def _recalcular(me):
    """Normales coherentes y hacia fuera en una malla cerrada (sin normales personalizadas). True si cambia."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    antes = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    cambia = sum(1 for f, n0 in zip(bm.faces, antes) if f.normal.dot(n0) < 0)
    if cambia:
        bm.to_mesh(me)
        me.update()
    bm.free()
    return cambia > 0


def _dos_caras(me):
    """Anade una copia invertida de cada cara (se ve por los dos lados en AC; la fisica tambien)."""
    bm = bmesh.new()
    bm.from_mesh(me)
    d = bmesh.ops.duplicate(bm, geom=bm.faces[:] + bm.edges[:] + bm.verts[:])
    nuevas = [g for g in d['geom'] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=nuevas)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(nuevas)


def _vistas_por_detras(P, objs, paso=0.5):
    """Mallas (por nombre de datos) cuya PRIMERA cara vista desde el borde de la pista (rayos horizontales hacia
    fuera a 0.4 / 1.0 / 1.6 m, hasta 30 m) es de espaldas y sin cara de delante pegada: AC no la dibuja."""
    dg = bpy.context.evaluated_depsgraph_get()
    V, T, O, K = mallas_mundo(objs, dg, np, claves=True)
    if V is None:
        return {}
    bvh = BVHTree.FromPolygons(V.tolist(), T.tolist(), all_triangles=True)
    gem = caras_gemelas(K, np)
    vistas = {}
    for k in range(int(P.L / paso)):
        q = P.marco(k * paso)
        h = q['w'] / 2.0
        for side in (1, -1):
            ex, ey, ez = P.punto(q, side * h)
            d = Vector((side * q['nx'], side * q['ny'], 0.0))
            for hh in (0.4, 1.0, 1.6):
                loc, nor, idx, _dd = bvh.ray_cast(Vector((ex, ey, ez + hh)), d, 30.0)
                if loc is None or nor.dot(d) <= 0.05:
                    continue
                if gem[idx]:
                    continue                    # ya tiene la cara gemela invertida (a dos caras)
                nm = objs[int(O[idx])].data.name
                vistas[nm] = vistas.get(nm, 0) + 1
    return vistas


def orientar_barreras(P, kd, log):
    cerca = _cerca_pista(P, kd)
    vistos = set()
    giradas, dobles, recalc, n_caras, ya_dobles = [], [], [], 0, 0
    candidatas = []
    cercanas = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(MURO_PREF)
                and not es_invisible(o.name) and cerca(o, 25.0)]
    for ob in cercanas:
        me = ob.data
        if me.name in vistos:
            continue
        vistos.add(me.name)
        bm = bmesh.new()
        bm.from_mesh(me)
        n_e = len(bm.edges)
        n_b = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        n_nm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        claves = {}
        for f in bm.faces:
            k = frozenset(v.index for v in f.verts)
            claves[k] = claves.get(k, 0) + 1
        gemelas = sum(c for c in claves.values() if c >= 2) / float(max(1, len(bm.faces)))
        vol = bm.calc_volume(signed=True) * (1.0 if ob.matrix_world.determinant() >= 0 else -1.0)
        bm.free()
        fb = n_b / max(1, n_e)
        if gemelas > 0.3:
            ya_dobles += 1                      # ya tiene cada cara por los dos lados (p. ej. bordillos altos)
        elif fb < 0.02 and n_nm == 0 and vol < -1.0:
            _invertir(me)
            giradas.append(ob.name)
        elif fb < 0.02 and n_nm == 0 and not me.has_custom_normals:
            if _recalcular(me):
                recalc.append(ob.name)
        elif len(me.polygons) <= 40000 and not me.has_custom_normals:
            candidatas.append(ob)               # abierta: a dos caras solo si desde la pista se ve por detras
    vistas = _vistas_por_detras(P, cercanas)
    for ob in candidatas:
        if ob.data.name in vistas:
            nc = _dos_caras(ob.data)
            n_caras += nc
            dobles.append((nc, ob.name))
    dobles.sort(reverse=True)
    log('fisica: %d mallas 1WALL_ cerradas al reves giradas %s' % (len(giradas), giradas[:12]))
    log('fisica: %d mallas 1WALL_ cerradas con caras sueltas al reves recalculadas %s' % (len(recalc), recalc[:12]))
    log('fisica: %d de %d mallas 1WALL_ abiertas que se ven por detras desde la pista, a dos caras (+%d caras; '
        'las mayores %s); %d ya lo eran' % (len(dobles), len(candidatas), n_caras, [(n, c) for c, n in dobles[:8]],
                                             ya_dobles))
    return {'giradas': giradas, 'recalculadas': len(recalc), 'dos_caras': len(dobles), 'caras_nuevas': n_caras,
            'ya_dobles': ya_dobles}


# ----------------------------------------------------------------------------- 2. terreno bajo el asfalto
def terreno_bajo_asfalto(P, kd, log, nombre='1GRASS_terreno', margen=0.05):
    """Que el 1GRASS_terreno no asome sobre la calzada (asomaba hasta 0.40 m junto al borde) SIN hundir nada fuera del
    asfalto: (1) los vertices DENTRO del asfalto (entre plano-3 y plano+2.5: ni la montana del tunel ni el fondo bajo
    los puentes) bajan como mucho hasta plano - margen; (2) cada arista que sale de dentro hacia fuera y en el borde
    queda por encima de z_borde - margen se PARTE justo en el borde (punto nuevo a z_borde - margen) y las caras
    afectadas se rehacen en abanico desde ese punto: por fuera del borde el terreno conserva su forma (antes se
    hundia el vertice de dentro hasta 8.4 m y quedaba un hoyo visible detras de la acera, s 3279-3286)."""
    ob = bpy.data.objects.get(nombre)
    if ob is None or ob.type != 'MESH':
        log('fisica: terreno_bajo_asfalto: no hay %s' % nombre)
        return {}
    if ob.data.users > 1:
        ob.data = ob.data.copy()
    me = ob.data
    mw = ob.matrix_world
    mwi = mw.inverted()
    nv = len(me.vertices)
    co = np.empty(nv * 3, np.float64)
    me.vertices.foreach_get('co', co)
    M = np.array(mw, np.float64)
    W = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    wmax = max(q['w'] for q in P.S) / 2.0 + 7.0

    def lat(x, y):
        s, u, t, q = _lateral(P, kd, x, y)
        return u, q['w'] / 2.0, q, abs(t) <= 1.2

    info = {}                                   # vertice -> (u, h, q, dentro)
    for k in range(nv):
        _c, _i, d = kd.find((W[k, 0], W[k, 1], 0.0))
        if d > wmax:
            continue
        u, h, q, ok = lat(W[k, 0], W[k, 1])
        if not ok:
            continue
        zp = q['z'] - q['lat'] * u
        info[k] = (u, h, q, abs(u) < h and zp - 3.0 <= W[k, 2] <= zp + 2.5)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    n_baj, baj_max = 0, 0.0
    for k, (u, h, q, dentro) in info.items():
        zp = q['z'] - q['lat'] * u
        if dentro and W[k, 2] > zp - margen:
            baj_max = max(baj_max, W[k, 2] - (zp - margen))
            W[k, 2] = zp - margen
            bm.verts[k].co = mwi @ Vector((W[k, 0], W[k, 1], W[k, 2]))
            n_baj += 1
    # aristas que cruzan el borde: biseccion del punto de cruce (|u| = h) y cota que tendria la arista alli
    cortes = []
    for e in bm.edges:
        ia, ib = e.verts[0].index, e.verts[1].index
        da, db = info.get(ia), info.get(ib)
        if not da or not db or da[3] == db[3]:
            continue
        a, b = (ia, ib) if da[3] else (ib, ia)
        ua, ub = info[a][0], info[b][0]
        if abs(ub) < info[b][1] or (ua > 0) != (ub > 0):
            continue                            # el de fuera no esta fuera por el mismo lado
        f0, f1 = 0.0, 1.0
        for _it in range(18):
            fm = 0.5 * (f0 + f1)
            x, y = W[a, 0] + (W[b, 0] - W[a, 0]) * fm, W[a, 1] + (W[b, 1] - W[a, 1]) * fm
            u, h, q, _ok = lat(x, y)
            if abs(u) < h:
                f0 = fm
            else:
                f1 = fm
        f = 0.5 * (f0 + f1)
        if f < 1e-3 or f > 1.0 - 1e-3:
            continue
        x, y = W[a, 0] + (W[b, 0] - W[a, 0]) * f, W[a, 1] + (W[b, 1] - W[a, 1]) * f
        u, h, q, _ok = lat(x, y)
        ze = q['z'] - q['lat'] * math.copysign(h, u)
        zl = W[a, 2] + (W[b, 2] - W[a, 2]) * f
        if zl > ze - margen + 0.003:
            cortes.append((e, bm.verts[a], f, Vector((x, y, ze - margen))))
    nuevos = set()
    for e, va, f, w in cortes:
        _ne, nv_ = bmesh.utils.edge_split(e, va, f)
        nv_.co = mwi @ w
        nuevos.add(nv_)
    # caras con puntos nuevos -> triangulos en abanico desde un punto nuevo (nunca alineados con sus vecinos)
    caras = {fc for v in nuevos for fc in v.link_faces}
    n_tri = 0
    for fc in caras:
        if not fc.is_valid or len(fc.verts) <= 3:
            continue
        vs = next((v for v in fc.verts if v in nuevos), None)
        cara = fc
        while vs is not None and len(cara.verts) > 3:
            lps = [lp.vert for lp in cara.loops]
            j = lps.index(vs)
            try:
                otra = bmesh.utils.face_split(cara, vs, lps[(j + 2) % len(lps)], use_exist=False)[0]
            except (ValueError, RuntimeError):
                break
            n_tri += 1
            cara = cara if len(cara.verts) > 3 else otra
    bm.to_mesh(me)
    bm.free()
    me.update()
    log('fisica: terreno bajo el asfalto: %d vertices de dentro bajados a plano-%.2f (max %.2f m), %d aristas partidas '
        'en el borde, %d cortes de cara (de %d vertices junto a la pista)' % (n_baj, margen, baj_max, len(cortes), n_tri,
                                                                           len(info)))
    return {'vertices': n_baj, 'bajada_max': round(baj_max, 3), 'aristas_partidas': len(cortes)}


def subdividir_pista(P, kd, log, cortes=7):
    """La calzada (1ROAD_pista / 1DIRT_ladera) tiene 2 vertices por seccion: cada quad de 2 m x ancho se dobla por
    su diagonal y, en curvas con pendiente, deja pliegues de 4-5 cm (tierra) que el coche nota como baches. Cada
    arista transversal se parte en cortes+1 tramos (rejilla): misma superficie peraltada, pliegues 8 veces menores."""
    out = {}
    for nombre in ('1ROAD_pista', '1DIRT_ladera'):
        ob = bpy.data.objects.get(nombre)
        if ob is None or ob.type != 'MESH':
            continue
        me = ob.data
        if me.users > 1:
            ob.data = me = me.copy()
        mw = ob.matrix_world
        bm = bmesh.new()
        bm.from_mesh(me)
        cruz = []
        for e in bm.edges:
            a, b = mw @ e.verts[0].co, mw @ e.verts[1].co
            dx, dy = b.x - a.x, b.y - a.y
            l2 = math.hypot(dx, dy)
            if l2 < 3.0:
                continue
            s, u, t, q = _lateral(P, kd, (a.x + b.x) / 2.0, (a.y + b.y) / 2.0)
            if abs(dx * q['nx'] + dy * q['ny']) / l2 > 0.7:
                cruz.append(e)
        n0 = len(bm.faces)
        if cruz:
            bmesh.ops.subdivide_edges(bm, edges=cruz, cuts=cortes, use_grid_fill=True)
        n1 = len(bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()
        out[nombre] = [n0, n1]
    log('fisica: calzada subdividida a lo ancho (%d cortes): %s caras antes/despues' % (cortes, out))
    return out


# ----------------------------------------------------------------------------- 3. cuna entre pista y pit lane
def _rango_pit(P, kd, G):
    """(s0, s1) desenrollados del pit lane (s1 puede pasar de L) o None."""
    PIT = G.get('pit_lane') or []
    if not PIT:
        return None
    s0 = _lateral(P, kd, PIT[0]['x'], PIT[0]['y'])[0]
    s1 = _lateral(P, kd, PIT[-1]['x'], PIT[-1]['y'])[0]
    if s1 < s0:
        s1 += P.L
    return s0, s1


def _smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def _borde_pit(P, bvh_pit, s, h_extra=12.0, paso=0.05, d_pend=0.6):
    """Borde interior del pit lane (lado -1) a la altura de s: (u_in, z_in, m_in) o None si el pit esta pegado al
    asfalto; m_in = pendiente transversal del pit lane hacia fuera (dz por m, medida d_pend m mas alla del borde)."""
    q = P.marco(s)
    h = q['w'] / 2.0
    ze = q['z'] + q['lat'] * h
    u = -h + 0.1
    while u > -h - h_extra:
        x, y, _z = P.punto(q, u)
        loc, _n, _i, _d = bvh_pit.ray_cast(Vector((x, y, ze + 1.5)), Vector((0, 0, -1)), 3.5)
        if loc is not None:
            if u > -h - 0.06:
                return None, q
            x2, y2, _z = P.punto(q, u - d_pend)
            l2, n2, _i, _d = bvh_pit.ray_cast(Vector((x2, y2, ze + 1.5)), Vector((0, 0, -1)), 3.5)
            m = (l2.z - loc.z) / d_pend if (l2 is not None and n2.z > 0.7) else 0.0
            return (u, loc.z, max(-0.15, min(0.15, m))), q
        u -= paso
    return None, q


def _perfil_cuna(q, b, u):
    """Cota de la cuna a la distancia lateral u (entre -h y u_in): curva de Hermite del borde de la calzada (con su
    peralte) al borde interior del pit lane (con su pendiente transversal): sin codo arriba ni abajo (con la S de
    pendiente 0 en los extremos quedaba un cambio de pendiente de 8 %/m al entrar en la losa, s 5056-5074)."""
    h = q['w'] / 2.0
    u_in, z_in, m_in = b
    W = max(0.05, -u_in - h)
    x = min(1.0, max(0.0, (-u - h) / W))
    z0 = q['z'] + q['lat'] * h
    m0 = max(-0.15, min(0.15, q['lat']))           # z(u) = z - lat*u: hacia fuera (u decreciente) sube lat por m
    x2, x3 = x * x, x * x * x
    return ((2 * x3 - 3 * x2 + 1) * z0 + (x3 - 2 * x2 + x) * W * m0 + (-2 * x3 + 3 * x2) * z_in
            + (x3 - x2) * W * m_in)


def cuna_pit(P, kd, G, log, nombre='2GRASS_arcen_der'):
    """El arcen entre el borde derecho de la pista y el borde interior del pit lane sube (o baja) en S hasta la cota
    del pit lane 1 cm por debajo: sin escalones al cruzar la cuna ni ranura junto al muro de boxes."""
    rg = _rango_pit(P, kd, G)
    ob = bpy.data.objects.get(nombre)
    pit = bpy.data.objects.get('1PIT_pit')
    if rg is None or ob is None or pit is None:
        log('fisica: cuna_pit: falta pit lane o %s' % nombre)
        return {}
    dg = bpy.context.evaluated_depsgraph_get()
    bvh_pit, _o, _n = bvh_de([pit], dg, np, BVHTree, 'pit')
    s0, s1 = rg
    tabla = {}
    s = s0
    while s <= s1:
        b, _q = _borde_pit(P, bvh_pit, s % P.L)
        tabla[round(s, 1)] = b
        s += 0.5
    claves = sorted(tabla)
    me = ob.data
    if me.users > 1:
        ob.data = me = me.copy()
    mw = ob.matrix_world
    mwi = mw.inverted()
    n_sub = _subdividir_cuna(P, kd, me, mw, tabla, claves, s0, s1)
    cambios, dz_max, n_borde = 0, 0.0, 0
    for v in me.vertices:
        w = mw @ v.co
        s, u, t, q = _lateral(P, kd, w.x, w.y)
        su = s if s >= s0 - 1.0 else s + P.L
        if not (s0 <= su <= s1) or abs(t) > 1.5:
            continue
        k = min(claves, key=lambda c: abs(c - su))
        b = tabla[k]
        h = q['w'] / 2.0
        if u > -h + 0.05:
            continue
        loc, nrm, _i, _d = bvh_pit.ray_cast(Vector((w.x, w.y, w.z + 3.0)), Vector((0, 0, -1)), 6.0)
        if loc is not None and nrm.z < 0.7:
            loc = None                      # el rayo roza el canto de la losa (no su cara de arriba): no es "debajo"
        if loc is not None:                 # bajo el pit lane: 2 cm por debajo de su superficie (no asoma)
            zt = loc.z - 0.02
        elif u >= -h - 0.12:                # en el borde de la calzada: a su cota (en s 134-144, con el pit lane
            zt = (q['z'] - q['lat'] * u) - 0.003      # pegado al borde, quedaba 7 cm por debajo: ranura)
            n_borde += 1
        elif b is not None and b[0] - 0.3 <= u < b[0]:      # pegado al canto de la losa (por fuera de su cara de
            zt = b[1] - 0.02                                 # arriba): a su cota, sin hoyo junto al canto
        elif b is not None and u >= b[0]:   # en la cuna: rampa del borde de la pista al borde del pit
            zt = _perfil_cuna(q, b, u) - 0.01
        else:
            continue
        if abs(zt - w.z) > 0.005:
            dz_max = max(dz_max, abs(zt - w.z))
            v.co = mwi @ Vector((w.x, w.y, zt))
            cambios += 1
    me.update()
    # tira fisica INVISIBLE que cose exactamente el borde de la pista con el borde interior del pit lane (el arcen
    # tiene pocos vertices y entre ellos quedaban 5-8 cm de escalon)
    K = 8
    vs, fs, fila_prev = [], [], None
    for c in claves:
        b = tabla[c]
        if b is None:
            fila_prev = None
            continue
        q = P.marco(c % P.L)
        h = q['w'] / 2.0
        u_in = b[0]
        fila = len(vs)
        for j in range(K + 1):
            f = j / float(K)
            u = -h + (u_in - 0.05 + h) * f
            x, y, _z = P.punto(q, u)
            vs.append((x, y, _perfil_cuna(q, b, u) - 0.004 - 0.004 * f))
        if fila_prev is not None:
            for j in range(K):
                fs.append((fila_prev + j, fila + j, fila + j + 1, fila_prev + j + 1))
        fila_prev = fila
    if fs:
        me_c = bpy.data.meshes.new('2GRASS_cuna_pit_invisible')
        me_c.from_pydata(vs, [], fs)
        me_c.materials.append(_material_invisible())
        bm = bmesh.new()
        bm.from_mesh(me_c)
        bm.normal_update()
        malas = [f for f in bm.faces if f.normal.z < 0]
        if malas:
            bmesh.ops.reverse_faces(bm, faces=malas)
        bm.to_mesh(me_c)
        bm.free()
        oc = bpy.data.objects.new('2GRASS_cuna_pit_invisible', me_c)
        oc.display_type = 'WIRE'
        bpy.context.scene.collection.objects.link(oc)
    n_cuna = sum(1 for b in tabla.values() if b is not None)
    log('fisica: cuna pista-pit lane: %s subdividido en la cuna (+%d caras), %d vertices a su rampa (max %.2f m; '
        '%d del borde de la calzada a su cota), %d secciones con cuna, tira invisible de %d caras'
        % (nombre, n_sub, cambios, dz_max, n_borde, n_cuna, len(fs)))
    return {'vertices': cambios, 'dz_max': round(dz_max, 3), 'secciones': n_cuna, 'caras_nuevas': n_sub,
            'borde': n_borde}


def _subdividir_cuna(P, kd, me, mw, tabla, claves, s0, s1, d_trans=0.4, d_lon=0.5):
    """El arcen tiene 2-3 vertices por seccion (cada 2 m): entre ellos la cara plana quedaba hasta 8.6 cm por debajo
    de la S de la cuna (y de la tira invisible: el coche flotaba sobre la hierba que se ve, x -47..-54, s ~5062).
    En las secciones con cuna (+-2 m) sus aristas transversales se parten en tramos de <= d_trans m y luego las
    longitudinales en tramos de <= d_lon m (rejilla): el arcen visible sigue la misma S que la tira."""
    con_cuna = [c for c in claves if tabla[c] is not None]
    if not con_cuna:
        return 0
    bm = bmesh.new()
    bm.from_mesh(me)
    n0 = len(bm.faces)

    def zona(vs):
        out = {}
        for v in vs:
            w = mw @ v.co
            s, u, t, q = _lateral(P, kd, w.x, w.y)
            su = s if s >= s0 - 1.0 else s + P.L
            if abs(t) > 1.5 or u > -q['w'] / 2.0 + 0.2 or not (s0 - 2.0 <= su <= s1 + 2.0):
                continue
            k = min(con_cuna, key=lambda c: abs(c - su))
            if abs(k - su) <= 2.0:
                out[v] = q
        return out

    for paso_max, transversal in ((d_trans, True), (d_lon, False)):
        bm.verts.ensure_lookup_table()
        zv = zona(bm.verts)
        sel, lmax = [], 0.0
        for e in bm.edges:
            a, b = e.verts
            if a not in zv or b not in zv:
                continue
            wa, wb = mw @ a.co, mw @ b.co
            dx, dy = wb.x - wa.x, wb.y - wa.y
            ln = math.hypot(dx, dy)
            if ln <= paso_max + 0.05:
                continue
            q = zv[a]
            cn = abs(dx * q['nx'] + dy * q['ny']) / ln
            if (cn > 0.7) if transversal else (cn < 0.5):
                sel.append(e)
                lmax = max(lmax, ln)
        if sel:
            bmesh.ops.subdivide_edges(bm, edges=sel, cuts=min(24, int(math.ceil(lmax / paso_max)) - 1),
                                      use_grid_fill=True)
    n1 = len(bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return n1 - n0


def _apices(P, r_in_max, pend_min):
    """[(s, lado)] de los apices con el borde interior colapsado (radio interior < r_in_max m) en pendiente."""
    cand = []
    for i in range(P.N):
        a, b, c = P.S[i - 1], P.S[i], P.S[(i + 1) % P.N]
        ang = math.atan2(c['ny'], c['nx']) - math.atan2(b['ny'], b['nx'])
        ang = (ang + math.pi) % (2.0 * math.pi) - math.pi
        if abs(ang) < 1e-6:
            continue
        r_in = P.paso / abs(ang) - b['w'] / 2.0
        if r_in < r_in_max and abs(c['z'] - a['z']) / (2.0 * P.paso) > pend_min:
            cand.append((r_in, i, 1 if ang > 0 else -1))
    out = []
    for r_in, i, lado in sorted(cand):
        if all(abs(i - j) > 6 for j, _l in out):
            out.append((i, lado))
    return [(i * P.paso, lado) for i, lado in out]


def chaflan_horquilla(P, kd, log, r_in_max=2.0, pend_min=0.08, radio=7.0, celda=0.1, salto=0.2, ancho=1.6,
                      lejos_via=0.15, nombre='2GRASS_horquilla_chaflan'):
    """Apice con el borde interior colapsado en pendiente (tierra, s 2364: 5.4 m de radio en el eje, 10 m de ancho, 15 %;
    el borde interior gira sobre un punto). El arcen interior de la rama alta (abanico alrededor del eje) queda en
    voladizo y acaba en un canto de 0.5-1.1 m sobre el terreno / el arcen de la rama baja (los 2 coches 'cae' del
    revisor, s 2354 / 2358). Correccion de EXPORT (la de fondo es de geometria: preparar_geometria): rejilla de `celda`
    m alrededor del eje; nodo 'alto' = arcen/terreno con un vecino de arcen/terreno > `salto` m mas bajo (canto casi
    vertical: con 0.08 saltaba tambien la ladera, 80 %); desde el pie del canto se rellenan por Laplace los nodos de
    arcen/terreno alcanzables sin subir otro canto, a <= `ancho` m de un alto y a > `lejos_via` m de la calzada (bordes:
    el alto - 5 mm y el resto del suelo; nunca por debajo del suelo que tapan) y se cubren con una malla de cesped
    VISIBLE `nombre` (material del arcen): el canto pasa a talud. La calzada (1DIRT/1ROAD/1KERB) no se toca."""
    apices = _apices(P, r_in_max, pend_min)
    arcen = bpy.data.objects.get('2GRASS_arcen_izq') or bpy.data.objects.get('2GRASS_arcen_der')
    if not apices or arcen is None:
        log('fisica: chaflan_horquilla: sin apices colapsados en pendiente')
        return {}
    dg = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in objetos_exportables(bpy) if o.name.startswith(SUELO_PREF) and not es_invisible(o.name)]
    bvh, own, _n = bvh_de(objs, dg, np, BVHTree, 'suelo')
    editable = ('2GRASS_arcen', '1GRASS_terreno')
    abajo = Vector((0.0, 0.0, -1.0))
    vs, fs, res = [], [], []
    for s_a, lado in apices:
        q = P.marco(s_a)
        ax, ay, az = P.punto(q, lado * q['w'] / 2.0)
        n = int(round(2 * radio / celda)) + 1
        X = ax - radio + celda * np.arange(n)
        Y = ay - radio + celda * np.arange(n)
        Z0 = np.full((n, n), np.nan)
        ED = np.zeros((n, n), bool)
        for i in range(n):
            for j in range(n):
                loc, _nn, idx, _d = bvh.ray_cast(Vector((X[i], Y[j], az + 15.0)), abajo, 30.0)
                if loc is not None:
                    Z0[i, j] = loc.z
                    ED[i, j] = objs[int(own[idx])].name.startswith(editable)
        VIA = ~ED & ~np.isnan(Z0)
        alto = np.zeros((n, n), bool)
        bajo = np.zeros((n, n), bool)              # vecinos del pie del canto
        canto = 0.0
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            Zv = np.roll(np.roll(Z0, -di, 0), -dj, 1)
            EDv = np.roll(np.roll(ED, -di, 0), -dj, 1)
            m = ED & EDv & (Z0 - Zv > salto)
            m[[0, -1], :] = False
            m[:, [0, -1]] = False
            alto |= m
            bajo |= np.roll(np.roll(m, di, 0), dj, 1)
            if m.any():
                canto = max(canto, float(np.nanmax(np.where(m, Z0 - Zv, np.nan))))
        bajo &= ~alto
        if not alto.any():
            res.append({'s': s_a, 'lado': lado, 'altos': 0})
            continue
        ia, ja = np.nonzero(alto)
        kda = kdtree.KDTree(len(ia))
        for k, (i, j) in enumerate(zip(ia, ja)):
            kda.insert((X[i], Y[j], 0.0), k)
        kda.balance()
        kdv = kdtree.KDTree(max(1, int(VIA.sum())))
        for k, (i, j) in enumerate(zip(*np.nonzero(VIA))):
            kdv.insert((X[i], Y[j], 0.0), k)
        kdv.balance()

        def candidato(i, j):
            if not (0 < i < n - 1 and 0 < j < n - 1) or not ED[i, j] or alto[i, j]:
                return False
            if kda.find((X[i], Y[j], 0.0))[2] > ancho:
                return False
            return not (VIA.any() and kdv.find((X[i], Y[j], 0.0))[2] <= lejos_via)
        # relleno = lo que se alcanza desde el pie del canto sin subir otro canto (no pasa a la parte alta)
        UNK = np.zeros((n, n), bool)
        pila = [(int(i), int(j)) for i, j in zip(*np.nonzero(bajo)) if candidato(i, j)]
        for c in pila:
            UNK[c] = True
        while pila:
            i, j = pila.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if not UNK[a, b] and Z0[a, b] - Z0[i, j] < salto and candidato(a, b):
                    UNK[a, b] = True
                    pila.append((a, b))
        Zb = np.where(alto, Z0 - 0.005, Z0)
        Z = Zb.copy()
        Z[UNK] = np.nanmax(np.where(alto, Z0, np.nan))
        piso = Z0 + 0.01
        for _it in range(2500):
            acc = np.zeros((n, n))
            cnt = np.zeros((n, n))
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                Zv = np.roll(np.roll(Z, -di, 0), -dj, 1)
                ok = ~np.isnan(Zv)
                acc += np.where(ok, Zv, 0.0)
                cnt += ok
            nz = np.where(cnt > 0, acc / np.maximum(cnt, 1), Z)
            Z[UNK] = np.maximum(nz[UNK], piso[UNK])
        idv = {}

        def vid(i, j):
            if (i, j) not in idv:
                z = Z[i, j] if UNK[i, j] else (Z0[i, j] - (0.005 if alto[i, j] else 0.01))
                idv[(i, j)] = len(vs)
                vs.append((float(X[i]), float(Y[j]), float(z)))
            return idv[(i, j)]
        n_c = 0
        for i in range(n - 1):
            for j in range(n - 1):
                cs = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
                if not any(UNK[c] for c in cs) or any(np.isnan(Z0[c]) or VIA[c] for c in cs):
                    continue
                fs.append(tuple(vid(*c) for c in cs))
                n_c += 1
        if os.environ.get('CHAFLAN_NPZ'):
            np.savez(os.environ['CHAFLAN_NPZ'], X=X, Y=Y, Z0=Z0, ED=ED, alto=alto, UNK=UNK, Z=Z)
        gx, gy = np.gradient(np.where(UNK, Z, np.nan), celda)
        pend = float(np.nanmax(np.hypot(gx, gy))) if UNK.any() else 0.0
        res.append({'s': s_a, 'lado': lado, 'eje': [round(ax, 2), round(ay, 2)], 'altos': int(alto.sum()),
                    'canto_max_m': round(canto, 2), 'nodos_rellenos': int(UNK.sum()), 'caras': n_c,
                    'pendiente_max': round(pend, 2)})
    if fs:
        old = bpy.data.objects.get(nombre)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(vs, [], fs)
        if arcen.data.materials:
            me.materials.append(arcen.data.materials[0])
        me.update()
        ob = bpy.data.objects.new(nombre, me)
        bpy.context.scene.collection.objects.link(ob)
    log('fisica: chaflan en el apice de las horquillas colapsadas (canto del arcen en voladizo -> talud de cesped '
        '%s): %s' % (nombre, res))
    return {'apices': res}


def pianos_rampa(P, kd, log, nombre='1KERB_pianos', alto_int=0.012):
    """Los pianos son una cinta plana 5-6 cm SOBRE el asfalto: al pisarlos el coche topa con un escalon vertical de
    5 cm en su borde interior. El borde interior baja a +1.2 cm (el exterior sigue a +6): rampa del 3-4 %."""
    ob = bpy.data.objects.get(nombre)
    if ob is None:
        log('fisica: pianos_rampa: no hay %s' % nombre)
        return {}
    me = ob.data
    if me.users > 1:
        ob.data = me = me.copy()
    mw = ob.matrix_world
    mwi = mw.inverted()
    n = 0
    caras_v = [0] * len(me.vertices)
    for f in me.polygons:
        for i in f.vertices:
            caras_v[i] += 1
    for v in me.vertices:
        w = mw @ v.co
        s, u, t, q = _lateral(P, kd, w.x, w.y)
        if abs(t) > 1.5:
            continue
        if abs(u) > q['w'] / 2.0 - 0.6 and caras_v[v.index] > 1:
            continue                         # borde exterior (salvo las esquinas de los extremos de la cinta)
        zt = q['z'] - q['lat'] * u + alto_int
        if w.z > zt + 0.003:
            v.co = mwi @ Vector((w.x, w.y, zt))
            n += 1
    me.update()
    log('fisica: pianos: %d vertices del borde interior y de los extremos a +%.3f m (sin escalon de 5 cm)'
        % (n, alto_int))
    return {'vertices': n}


# ----------------------------------------------------------------------------- 4. rampa de los garajes
class FilaGarajes:
    """Ejes de la fila de garajes: origen en AC_PIT_0, U = hacia el pit lane (+Z de AC: (sin rz, -cos rz)), T = a lo
    largo de la fila; posiciones t de los garajes, media separacion y consultas por rayo al pit lane y al resto del
    suelo fisico (sin la rampa, sin el pit lane y sin mallas invisibles)."""

    def __init__(self, excluir=()):
        self.ok = False
        self.pits = sorted((o for o in bpy.data.objects if o.name.startswith('AC_PIT_') and o.type == 'MESH'),
                           key=lambda o: int(o.name.split('_')[-1].split('.')[0]))
        lib = bpy.data.collections.get('LIB')
        en_lib = set(o.name for o in lib.all_objects) if lib else set()
        objs = [o for o in objetos_exportables(bpy) if o.name not in en_lib]
        lane = [o for o in objs if o.name.split('.')[0] == '1PIT_pit']
        if not self.pits or not lane:
            return
        dg = bpy.context.evaluated_depsgraph_get()
        self.b_l = bvh_de(lane, dg, np, BVHTree, 'pit')[0]
        otros = [o for o in objs if o.name.startswith(SUELO_PREF) and o not in lane and not es_invisible(o.name)
                 and o.name.split('.')[0] not in excluir]
        self.b_g = bvh_de(otros, dg, np, BVHTree, 'suelo')[0]
        r = self.pits[0].rotation_euler.z
        self.U = Vector((math.sin(r), -math.cos(r)))
        self.T = Vector((-self.U.y, self.U.x))
        self.c0 = Vector((self.pits[0].location.x, self.pits[0].location.y))
        self.z_ref = self.pits[0].location.z - 1.0          # AC_PIT a 1 m sobre el suelo (exportar_ac.ALTURA_AC)
        self.ts = sorted((Vector((o.location.x, o.location.y)) - self.c0).dot(self.T) for o in self.pits)
        sep = sorted(b - a for a, b in zip(self.ts, self.ts[1:]))
        self.medio = 0.5 * (sep[len(sep) // 2] if sep else 6.0)
        self.g0, self.g1 = self.ts[0] - self.medio, self.ts[-1] + self.medio     # de puerta a puerta
        self.zf = self.suelo(0.0, 0.0, self.z_ref) or self.z_ref                 # suelo del box
        self.ok = True

    def xy(self, uu, tt):
        p = self.c0 + self.U * uu + self.T * tt
        return p.x, p.y

    def carril(self, uu, tt):
        x, y = self.xy(uu, tt)
        loc = self.b_l.ray_cast(Vector((x, y, self.z_ref + 3.0)), Vector((0.0, 0.0, -1.0)), 6.0)[0]
        return loc.z if loc is not None else None

    def suelo(self, uu, tt, zr):
        if self.b_g is None:
            return None
        x, y = self.xy(uu, tt)
        loc = self.b_g.ray_cast(Vector((x, y, zr + 1.5)), Vector((0.0, 0.0, -1.0)), 4.0)[0]
        return loc.z if loc is not None else None

    def borde(self, tt, u_desde=0.5, u_hasta=14.0):
        """(u, z) del borde del pit lane del lado de los garajes a la altura t (rayos cada 5 cm + biseccion)."""
        uu = u_desde
        while uu < u_hasta and self.carril(uu, tt) is None:
            uu += 0.05
        if uu >= u_hasta:
            return None
        lo, hi = uu - 0.05, uu
        for _i in range(7):
            m = 0.5 * (lo + hi)
            if self.carril(m, tt) is None:
                lo = m
            else:
                hi = m
        z = self.carril(hi + 0.02, tt)
        return (hi, z) if z is not None else None


def rampa_garajes(log, curv=0.07, paso_t=0.5, k_filas=20, u_min=-2.2, l_atras=1.5, ext_max=14.0, fundido=2.5):
    """Rehace 1PIT_boxes_rampa SIN depender de los vertices del carril: exportar_ac.rampa_garajes solo creaba secciones
    donde habia vertices del borde del pit lane y en los garajes de los extremos (AC_PIT_0 y AC_PIT_19) la rampa
    acababa a 0.8-1.25 m del eje: la rueda caia 0.2-0.38 m por su lateral y chocaba con el canto de 0.6 m de la losa.
    Secciones cada `paso_t` m por TODA la fila (de la puerta del primero a la del ultimo) y por la zanja que sigue
    entre el pit lane y el terreno (hasta `ext_max` m mas, mientras el suelo junto al borde quede > 0.10 m bajo el
    carril); en cada una el borde del carril se busca con rayos sobre 1PIT_pit y el perfil es una S cubica (pendiente
    0 en los extremos) de largo sqrt(6 h / curv): cambio de pendiente <= curv por metro. Fuera de la fila: talud
    trasero de `l_atras` m hasta el suelo y, al final, `fundido` m en los que la rampa se hunde 1 cm bajo el suelo que
    tiene debajo (sin canto lateral). El suelo de debajo nunca asoma sobre la rampa (+4 mm)."""
    ob = bpy.data.objects.get('1PIT_boxes_rampa')
    F = FilaGarajes(excluir=('1PIT_boxes_rampa',))
    if ob is None or not F.ok:
        log('fisica: rampa_garajes: falta 1PIT_boxes_rampa, AC_PIT_* o 1PIT_pit')
        return {}
    zf = F.zf
    ext = {}
    for sg, tb in ((-1, F.g0), (1, F.g1)):            # zanja mas alla de los garajes de los extremos
        e, ult = 0.0, 0.0
        while e < ext_max:
            e += paso_t
            be = F.borde(tb + sg * e)
            if be is None:
                break
            zs = F.suelo(be[0] - 0.3, tb + sg * e, be[1])
            if zs is None or zs < be[1] - 0.10:
                ult = e
            elif e - ult > 1.0:
                break
        ext[sg] = ult + 0.5
    t_ini, t_fin = F.g0 - ext[-1] - fundido, F.g1 + ext[1] + fundido
    filas, largos, pend, curvs = [], [], [], []
    for k in range(int(round((t_fin - t_ini) / paso_t)) + 1):
        tt = t_ini + k * paso_t
        be = F.borde(tt)
        if be is None:
            filas.append(None)
            continue
        ue, ze = be
        h = ze - zf
        lr = min(max(3.0, math.sqrt(6.0 * max(h, 0.0) / curv)), ue - u_min)
        u0 = ue - lr
        fuera = max(F.g0 - tt, tt - F.g1, 0.0)           # m mas alla de la fila de garajes
        e_lado = ext[1 if tt > F.g1 else -1]
        f_hund = _smooth((fuera - e_lado) / fundido) if fuera > e_lado else 0.0
        if fuera > 0.25:                                  # talud trasero (pasada la pared del extremo, 0.37 m): del
            ub = u0 - l_atras                             # suelo de fuera a la cota del box
            zb = F.suelo(ub, tt, zf)
            zb = zf if zb is None else min(zb, zf)
        else:                                             # dentro de la fila: llano sobre el suelo del box
            ub, zb = max(u0 - l_atras, -2.9), zf
        pts = [(ub + (u0 - ub) * j / 4.0, zb + (zf - zb) * _smooth(j / 4.0)) for j in range(4)]
        pts += [(u0 + lr * j / float(k_filas), zf + h * _smooth(j / float(k_filas))) for j in range(k_filas + 1)]
        zl = F.carril(ue + 0.15, tt)
        pts.append((ue + 0.15, (zl if zl is not None else ze) - 0.005))      # solape bajo la losa del carril
        fila = []
        for j, (uu, z) in enumerate(pts):
            zg = F.suelo(uu, tt, z)
            if zg is not None and j < len(pts) - 1:
                z = max(z, zg + 0.004)
            if f_hund > 0.0 and zg is not None:
                z = z + ((zg - 0.01) - z) * f_hund
            x, y = F.xy(uu, tt)
            fila.append((x, y, z))
        filas.append(fila)
        if fuera <= 0.0:
            largos.append(lr)
            pend.append(1.5 * h / lr)
            curvs.append(6.0 * h / lr ** 2)
    nv, nf, idx = [], [], {}
    for k, fila in enumerate(filas):
        if fila is not None:
            idx[k] = len(nv)
            nv.extend(fila)
    nr = k_filas + 6
    for k in range(len(filas) - 1):
        if k in idx and k + 1 in idx:
            o0, o1 = idx[k], idx[k + 1]
            nf.extend((o0 + j, o1 + j, o1 + j + 1, o0 + j + 1) for j in range(nr - 1))
    me2 = bpy.data.meshes.new('1PIT_boxes_rampa')
    me2.from_pydata(nv, [], nf)
    for m in ob.data.materials:
        me2.materials.append(m)
    bm = bmesh.new()
    bm.from_mesh(me2)
    bm.normal_update()
    malas = [f for f in bm.faces if f.normal.z < 0]
    if malas:
        bmesh.ops.reverse_faces(bm, faces=malas)
    bm.to_mesh(me2)
    bm.free()
    ob.data = me2
    ob.matrix_world = Matrix.Identity(4)
    n_sec = len(idx)
    log('fisica: rampa de garajes en S: %d secciones cada %.1f m (t %.1f..%.1f; garajes %.1f..%.1f, zanja +%.1f / '
        '+%.1f m, fundido %.1f m), largo %.1f..%.1f m, pendiente max %.0f %%, cambio de pendiente max %.1f %%/m'
        % (n_sec, paso_t, t_ini, t_fin, F.g0, F.g1, ext[-1], ext[1], fundido, min(largos), max(largos),
           100 * max(pend), 100 * max(curvs)))
    return {'secciones': n_sec, 't': [round(t_ini, 1), round(t_fin, 1)], 'garajes_t': [round(F.g0, 2), round(F.g1, 2)],
            'zanja_m': [ext[-1], ext[1]], 'largo_m': [round(min(largos), 2), round(max(largos), 2)],
            'pendiente_max': round(max(pend), 3), 'curvatura_max': round(max(curvs), 3)}


def tapones_boxes(log, alto=4.0, solape=2.5, sep_cierre=0.8):
    """El muro de cierre deja libre el frente de los garajes y empezaba ~4.5 m mas alla del ultimo: entre la pared
    del extremo del edificio (llega a u ~ 2.8) y el cierre (u = borde del carril - 0.8) quedaba un paso de 1.4 x 2.7 m
    por el que el coche salia del circuito por detras del cierre (rayos de 13-40 m sin muro desde delante de AC_PIT_0
    / AC_PIT_19). En cada extremo de la fila: muro INVISIBLE en L 1WALL_cierre_boxes, pegado por fuera a la pared del
    extremo (de u = 1.0, donde la pared sigue, hasta la linea del cierre) y por esa linea `solape` m hacia fuera
    (solapa con el principio del cierre)."""
    F = FilaGarajes()
    if not F.ok:
        log('fisica: tapones_boxes: sin fila de garajes')
        return {}
    vs, fs = [], []
    res = []
    for sg, tw in ((-1, F.g0 - 0.1), (1, F.g1 + 0.1)):
        be = F.borde(tw)
        if be is None:
            continue
        uc = be[0] - sep_cierre
        polil = [(1.0, tw), (uc, tw), (uc, tw + sg * solape)]
        for (ua, ta), (ub, tb) in zip(polil, polil[1:]):
            n = max(1, int(math.hypot(ub - ua, tb - ta) / 0.5))
            for j in range(n):
                p0 = (ua + (ub - ua) * j / n, ta + (tb - ta) * j / n)
                p1 = (ua + (ub - ua) * (j + 1) / n, ta + (tb - ta) * (j + 1) / n)
                o = len(vs)
                for (uu, tt) in (p0, p1):
                    x, y = F.xy(uu, tt)
                    zg = F.suelo(uu, tt, F.zf + 1.0)
                    zg = min(zg, F.zf) if zg is not None else F.zf
                    vs.append((x, y, zg - 1.0))
                    vs.append((x, y, F.zf + alto))
                fs.append((o, o + 2, o + 3, o + 1))
                fs.append((o, o + 1, o + 3, o + 2))
        res.append({'lado': sg, 't_pared': round(tw, 2), 'u_cierre': round(uc, 2)})
    old = bpy.data.objects.get('1WALL_cierre_boxes')
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new('1WALL_cierre_boxes')
    me.from_pydata(vs, [], fs)
    me.materials.append(_material_invisible())
    me.update()
    ob = bpy.data.objects.new('1WALL_cierre_boxes', me)
    ob.display_type = 'WIRE'
    bpy.context.scene.collection.objects.link(ob)
    log('fisica: tapones del frente de boxes (muro invisible en L entre la pared del extremo y el cierre): %s' % res)
    return {'tapones': res, 'caras': len(fs)}


def labio_viaducto(P, kd, log, prefijo='VIADUCTO_tramo_cuerpo', nombre='1ROAD_viaducto_labio_invisible',
                   banda=(0.2, 1.5), bajo=0.4):
    """El tablero visible del viaducto (VIADUCTO_tramo_cuerpo, decorado: con sombra y sus arcos) sobresale 0.50-0.60 m
    por cada lado de la calzada, 5-10 cm por debajo del borde (s 3632-4936): la rueda que pisa ese labio lo atraviesa
    y cae al terreno / al agua, 1-4 m mas abajo (s 4936: sin balaustrada hasta el muro a 2 m). Copia FISICA invisible
    `nombre` de sus caras de arriba (normal z > 0.8) con algun vertice en la banda h+banda[0]..h+banda[1] y a menos de
    `bajo` m bajo el plano de la calzada: misma cota que lo que se ve (no flota), el decorado no cambia."""
    obs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(prefijo)]
    vs, fs, n_o = [], [], 0
    for ob in obs:
        mw = ob.matrix_world
        n3 = mw.to_3x3().inverted().transposed()
        W = [mw @ v.co for v in ob.data.vertices]
        lat = {}
        usado = False
        for f in ob.data.polygons:
            nz = (n3 @ f.normal).normalized().z
            if nz < 0.8:
                continue
            ok = False
            for i in f.vertices:
                if i not in lat:
                    s, u, t, q = _lateral(P, kd, W[i].x, W[i].y)
                    h = q['w'] / 2.0
                    zp = q['z'] - q['lat'] * u
                    lat[i] = abs(t) <= 1.5 and h + banda[0] <= abs(u) <= h + banda[1] and zp - bajo <= W[i].z <= zp + 0.01
                ok = ok or lat[i]
            if not ok:
                continue
            o = len(vs)
            vs.extend((W[i].x, W[i].y, W[i].z) for i in f.vertices)
            fs.append(tuple(range(o, o + len(f.vertices))))
            usado = True
        n_o += usado
    if not fs:
        log('fisica: labio_viaducto: sin caras de %s junto a la calzada' % prefijo)
        return {}
    old = bpy.data.objects.get(nombre)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(vs, [], fs)
    me.materials.append(_material_invisible())
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bm.normal_update()
    malas = [f for f in bm.faces if f.normal.z < 0]
    if malas:
        bmesh.ops.reverse_faces(bm, faces=malas)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    ob.display_type = 'WIRE'
    bpy.context.scene.collection.objects.link(ob)
    log('fisica: labio del tablero del viaducto fisico (copia invisible de %d caras de arriba de %d mallas %s*)'
        % (len(fs), n_o, prefijo))
    return {'caras': len(fs), 'mallas': n_o}


# ----------------------------------------------------------------------------- 5. muros de cierre
CANTO_CIERRE = 0.4       # bajada del suelo entre dos muestras (0.5 m) que corta la escapatoria: el cierre va antes


class _Rayos:
    def __init__(self, P, kd):
        dg = bpy.context.evaluated_depsgraph_get()
        objs = objetos_exportables(bpy)
        self.muros = [o for o in objs if o.name.startswith(MURO_PREF) and not es_invisible(o.name)]
        self.suelos = [o for o in objs if o.name.startswith(SUELO_PREF)]
        self.b_m, self.o_m, _n = bvh_de(self.muros, dg, np, BVHTree, 'muros')
        self.b_s, self.o_s, _n = bvh_de(self.suelos, dg, np, BVHTree, 'suelo')
        pit = [o for o in objs if o.name.startswith('1PIT_pit')]
        self.b_p = bvh_de(pit, dg, np, BVHTree, 'pit')[0] if pit else None
        self.P, self.kd = P, kd

    def muro(self, o, d, dist):
        loc, _n, idx, dd = self.b_m.ray_cast(Vector(o), Vector(d), dist)
        return (dd, self.muros[int(self.o_m[idx])].name) if loc is not None else None

    def suelo(self, x, y, z_desde, largo):
        loc, _n, idx, _d = self.b_s.ray_cast(Vector((x, y, z_desde)), Vector((0, 0, -1)), largo)
        return (loc.z, self.suelos[int(self.o_s[idx])].name) if loc is not None else None

    def techo(self, x, y, z_desde, largo):
        loc, _n, _i, _d = self.b_s.ray_cast(Vector((x, y, z_desde)), Vector((0, 0, 1)), largo)
        return loc.z if loc is not None else None

    def en_asfalto(self, x, y, z, s_propio, margen=0.6):
        """True si (x, y) cae sobre el asfalto (+margen) de otro tramo de pista a una cota parecida."""
        P = self.P
        for (_co, j, _d) in self.kd.find_range((x, y, 0.0), 14.0):
            sj = j * P.paso
            ds = abs(sj - s_propio) % P.L
            if min(ds, P.L - ds) < 9.0:
                continue
            q = P.S[j]
            dx, dy = x - q['x'], y - q['y']
            if abs(dx * q['ny'] - dy * q['nx']) > 1.2:
                continue
            u = dx * q['nx'] + dy * q['ny']
            if abs(u) < q['w'] / 2.0 + margen and abs(q['z'] - q['lat'] * u - z) < 6.0:
                return True
        return False


def _pit_exterior(P, R, s):
    """Distancia del borde de la pista (lado -1) al borde EXTERIOR del pit lane a la altura de s, o None."""
    if R.b_p is None:
        return None
    q = P.marco(s)
    h = q['w'] / 2.0
    ze = q['z'] + q['lat'] * h
    ult = None
    e = -0.5
    while e < 22.0:
        x, y, _z = P.punto(q, -h - e)
        loc, _n, _i, _d = R.b_p.ray_cast(Vector((x, y, ze + 2.0)), Vector((0, 0, -1)), 4.5)
        if loc is not None:
            ult = e
        elif ult is not None and e - ult > 1.0:
            break
        e += 0.25
    return ult


def _limite_suelo(R, q, ex, ey, ez, side, angulos=((0.0, E_ESCAPE), (45.0, 5.0), (-45.0, 5.0))):
    """Distancia lateral (desde el borde) hasta el vacio, la caida (> 2.5 m bajo el borde) o el canto (> CANTO_CIERRE
    m entre dos muestras de 0.5 m) mas cercano: borde del tablero del viaducto, acera sobre un camino mas bajo, arcen
    que acaba en un talud. Se mira por la normal y a +-45 grados de ella hasta 5 m (los cantos oblicuos, como el final
    de una acera o el labio en los huecos de la balaustrada, se veian por la normal 1-2 m mas lejos)."""
    tx, ty = q['ny'], -q['nx']
    nx, ny = side * q['nx'], side * q['ny']
    e_v = E_ESCAPE
    for ang, d_max in angulos:
        a = math.radians(ang)
        dx, dy = nx * math.cos(a) + tx * math.sin(a), ny * math.cos(a) + ty * math.sin(a)
        lat = math.cos(a)
        ult, z_ant, dd = None, ez, 0.5
        while dd <= d_max + 1e-6 and dd * lat < e_v:
            g = R.suelo(ex + dx * dd, ey + dy * dd, ez + 3.0, 9.0)
            if g is None or g[0] < ez - 2.5 or g[0] < z_ant - CANTO_CIERRE:
                e_v = min(e_v, (ult * lat + 0.2) if ult is not None else E_MIN_PUENTE)
                break
            ult, z_ant = dd, g[0]
            dd += 0.5
    return max(E_MIN_PUENTE, e_v)


def _candidatos(P, R, side, zona_pit, garajes):
    """Por muestra (cada DS_CIERRE m): dict con e_lim (escape / vacio / acera), e_b (barrera real), pit."""
    n = int(round(P.L / DS_CIERRE))
    out = []
    for k in range(n):
        s = k * DS_CIERRE
        q = P.marco(s)
        h = q['w'] / 2.0
        ex, ey, ez = P.punto(q, side * h)
        d = (side * q['nx'], side * q['ny'], 0.0)
        c = {'s': s, 'q': q, 'ze': ez, 'pit': False, 'saltar': False}
        su = s if (zona_pit and s >= zona_pit[0] - 12.0) else s + P.L
        if side < 0 and zona_pit and zona_pit[0] - 10.0 <= su <= zona_pit[1] + 10.0:
            c['pit'] = True
            if garajes and garajes[0] <= su <= garajes[1]:
                c['saltar'] = True                       # frente de los garajes: cierra el edificio de boxes
            pe = _pit_exterior(P, R, s)
            c['e'] = max(E_ESCAPE, (pe + 0.8) if pe is not None else 0.0)
            out.append(c)
            continue
        eb = None
        for hh in (0.4, 0.7, 1.0):
            r = R.muro((ex, ey, ez + hh), d, E_ESCAPE + 1.0)
            if r and (eb is None or r[0] < eb):
                eb = r[0]
        c['e_b'] = eb
        c['e_v'] = _limite_suelo(R, q, ex, ey, ez, side)
        # acera alta / baja junto al borde: el cierre justo detras del bordillo
        g = R.suelo(ex + d[0] * 0.6, ey + d[1] * 0.6, ez + 1.5, 3.0)
        c['acera'] = bool(g and g[1].startswith('1ROAD_acera'))
        c['puente'] = q['sec'] == 'bridge' or c['e_v'] < 1.5
        out.append(c)
    return out


def _resolver(P, cands, ventana=7, v_suelo=2):
    """e final por muestra: barreras continuas (>= 2*ventana+1 m) acercan el cierre; el limite del suelo (vacio /
    canto) es el minimo de las +-v_suelo muestras (un rellano estrecho en un hueco de la balaustrada no abre el cierre:
    a sus lados el labio acaba en vacio); transicion <= PEND_TRANS."""
    n = len(cands)
    INF = 1e9
    eb = [c.get('e_b') if c.get('e_b') is not None else INF for c in cands]
    ev = [c.get('e_v', INF) if not c['pit'] else INF for c in cands]
    e = [None] * n
    for k, c in enumerate(cands):
        if c['pit']:
            e[k] = c['e']
            continue
        ebe = max(eb[(k + j) % n] for j in range(-ventana, ventana + 1))      # apertura: solo tramos continuos
        emin = E_MIN_PUENTE if c['puente'] else E_MIN
        e_v = min(ev[(k + j) % n] for j in range(-v_suelo, v_suelo + 1))
        lim = min(E_ESCAPE, e_v, 1.3 if c['acera'] else E_ESCAPE)
        e[k] = min(lim, max(ebe + DETRAS, emin)) if ebe < INF else lim
    libre = [not c['pit'] for c in cands]
    paso = PEND_TRANS * DS_CIERRE
    for _vuelta in range(2):                       # envolvente inferior circular (no entra en la zona del pit)
        for k in range(n):
            j = (k - 1) % n
            if libre[k] and libre[j]:
                e[k] = min(e[k], e[j] + paso)
        for k in range(n - 1, -1, -1):
            j = (k + 1) % n
            if libre[k] and libre[j]:
                e[k] = min(e[k], e[j] + paso)
    return e


def _material_invisible():
    m = bpy.data.materials.get(MAT_INVISIBLE)
    if m is None:
        m = bpy.data.materials.new(MAT_INVISIBLE)
        m.diffuse_color = (0.8, 0.1, 0.1, 1.0)
    return m


_ULTIMO_CIERRE = {}      # muros_cierre -> cierre_horquillas: e por muestra y lado, y los rayos (sin recalcular)


def _columna(R, x, y, ze):
    """(zb, zt) del muro invisible en (x, y) junto a un borde a cota ze: de 1 m bajo el suelo (o el borde) a 3 m sobre
    el borde (o 2 m sobre el suelo), sin pasar de 8 m bajo el borde y con el tope bajo cualquier calzada de encima."""
    g = R.suelo(x, y, ze + 4.0, 40.0)
    zg = g[0] if g else None
    zb = max(min(ze, zg if zg is not None else ze) - 1.0, ze - 8.0)
    zt = max(ze + 3.0, (zg + 2.0) if zg is not None else ze + 3.0)
    base = max(ze, zg if zg is not None else ze) + 0.3
    tc = R.techo(x, y, base, zt - base + 0.2)
    if tc is not None:
        zt = max(base + 0.5, tc - 0.15)
    return zb, zt


def muros_cierre(P, kd, G, log):
    R = _Rayos(P, kd)
    _ULTIMO_CIERRE.clear()
    _ULTIMO_CIERRE['R'] = R
    zona = _rango_pit(P, kd, G)
    garajes = None
    pits = [o for o in bpy.data.objects if o.name.startswith('AC_PIT_')]
    if zona and pits:
        sg = []
        for o in pits:
            s = _lateral(P, kd, o.location.x, o.location.y)[0]
            sg.append(s if s >= zona[0] - 12.0 else s + P.L)
        garajes = (min(sg) - 4.5, max(sg) + 4.5)
    res = {'zona_pit': zona, 'garajes': garajes}
    mat = _material_invisible()
    for side, nombre in ((1, '1WALL_cierre_izq'), (-1, '1WALL_cierre_der')):
        t0 = time.time()
        cands = _candidatos(P, R, side, zona, garajes)
        es = _resolver(P, cands)
        pts = []
        n_asf = n_omit = 0
        for c, e in zip(cands, es):
            if c['saltar']:
                pts.append(None)
                n_omit += 1
                continue
            q = c['q']
            h = q['w'] / 2.0
            ze = c['ze']
            ok = None
            while e >= 0.3:
                x, y, _z = P.punto(q, side * (h + e))
                if not R.en_asfalto(x, y, ze, c['s']):
                    ok = (x, y, e)
                    break
                e -= 0.25
                n_asf += 1
            if ok is None:
                pts.append(None)
                n_omit += 1
                continue
            x, y, e = ok
            zb, zt = _columna(R, x, y, ze)
            pts.append((x, y, zb, zt, e, c['s'], ze))
        _ULTIMO_CIERRE[side] = {'cands': cands, 'pts': pts}
        # malla: quads entre muestras consecutivas validas (dos caras), sin cruzar asfalto ni saltos > 8 m
        vs, fs = [], []
        idx = {}
        n = len(pts)
        n_seg = 0
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            if a is None or b is None:
                continue
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 8.0:
                continue
            medio = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            if R.en_asfalto(medio[0], medio[1], a[6], a[5], margen=0.3):
                continue
            for kk, p in ((k, a), ((k + 1) % n, b)):
                if kk not in idx:
                    idx[kk] = len(vs)
                    vs.append((p[0], p[1], p[2]))
                    vs.append((p[0], p[1], p[3]))
            i0, i1 = idx[k], idx[(k + 1) % n]
            fs.append((i0, i1, i1 + 1, i0 + 1))
            fs.append((i0, i0 + 1, i1 + 1, i1))
            n_seg += 1
        old = bpy.data.objects.get(nombre)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(vs, [], fs)
        me.materials.append(mat)
        me.update()
        ob = bpy.data.objects.new(nombre, me)
        ob.display_type = 'WIRE'
        bpy.context.scene.collection.objects.link(ob)
        if os.environ.get('CIERRE_JSON'):
            import json
            dump = [{'s': c['s'], 'e': (round(p[4], 2) if p else None), 'e_b': c.get('e_b'), 'e_v': c.get('e_v'),
                     'acera': c.get('acera'), 'puente': c.get('puente'), 'pit': c['pit'], 'saltar': c['saltar']}
                    for c, p in zip(cands, pts)]
            json.dump(dump, open(os.environ['CIERRE_JSON'].replace('.json', '_%s.json' % nombre[-3:]), 'w'))
        ev = [p[4] for p in pts if p is not None]
        res[nombre] = {'segmentos_m': round(n_seg * DS_CIERRE, 1), 'omitidos_m': round(n_omit * DS_CIERRE, 1),
                       'recortes_por_otro_ramal': n_asf, 'e_mediana': round(sorted(ev)[len(ev) // 2], 2) if ev else None,
                       'e_min': round(min(ev), 2) if ev else None}
        log('fisica: %s: %.0f m de muro invisible (%.0f m omitidos: garajes / sin sitio), e mediana %.2f m, '
            '%d recortes por otro ramal [%.0fs]' % (nombre, n_seg * DS_CIERRE, n_omit * DS_CIERRE,
                                                    res[nombre]['e_mediana'] or 0, n_asf, time.time() - t0))
    return res


# ----------------------------------------------------------------------------- 6. cierre interior de horquillas
# En las horquillas el arcen interior (6.75 m) de un ramal y el del otro se juntan alrededor del apice: el coche pasaba
# de un ramal al otro por la hierba sin tocar el cierre (rev2_coches2: s 1864 -> 1925 y 2364 -> 2433, 10-12 m mas
# corto). Deteccion GENERAL (sin coordenadas): (1) PLIEGUES: dos partes de la pista separadas H_DS_MIN..H_DS_MAX m en s
# con los bordes a < H_HUECO m en planta y la pista girando >= H_GIRO grados entre ellas (con >= 150 m y < 35 m, la
# regla de partida, no sale ninguna: las dos ramas de las horquillas de tierra estan a 60-100 m en s y sus bordes a
# 26-33 m); (2) CURVAS CERRADAS: tramo de radio < H_R_CURVA m que gira >= H_GIRO_CURVA grados (s 1682 -> 1751 cortaba
# 6 m por dentro de la S de tierra). En la parte curva (radio < H_R_CURVA) +- H_EXT m del lado de dentro, muro
# invisible 1WALL_cierre_horquillas a E_HORQ m del borde (fuera del arcen util), con transiciones de PEND_TRANS m/m
# que acaban 0.4 m por FUERA del cierre normal (lo cruzan: sin rendija), solo donde el cierre normal esta a
# > E_HORQ_MAX m (no delante de barreras, aceras ni puentes) y nunca a < E_HORQ_OTRO m del borde de otro tramo.
H_DS_MIN = 50.0
H_DS_MAX = 160.0
H_HUECO = 35.0
H_GIRO = 90.0
H_R_CURVA = 30.0
H_GIRO_CURVA = 30.0
H_EXT = 8.0
E_HORQ = 2.5
E_HORQ_MAX = 3.0
E_HORQ_OTRO = 2.0


def curvas_interiores(P):
    """[{'s0', 's1', 'lado', 'tipo', 'giro'}]: tramos (s en m, s1 puede pasar de L) del lado INTERIOR de las horquillas
    (pliegues) y de las curvas cerradas que necesitan cierre interior."""
    N, p = P.N, P.paso
    X = np.array([q['x'] for q in P.S])
    Y = np.array([q['y'] for q in P.S])
    H = np.array([q['w'] for q in P.S]) / 2.0
    hd = np.array([math.atan2(-q['nx'], q['ny']) for q in P.S])         # rumbo (ny, -nx)
    d = (np.roll(hd, -1) - hd + math.pi) % (2.0 * math.pi) - math.pi     # giro de k a k+1 (+ = izquierda)
    kap = np.convolve(np.r_[d[-2:], d, d[:2]], np.ones(5) / 5.0, 'valid') / p
    cum = np.concatenate([[0.0], np.cumsum(np.r_[d, d])])

    def giro(i, j):                     # de i a j hacia delante (j puede ser > N)
        return cum[j] - cum[i]
    # partes curvas: tramos contiguos (circulares) con lado * curvatura > 1 / H_R_CURVA
    curvas = []
    for lado in (1, -1):
        m = lado * kap > 1.0 / H_R_CURVA
        if m.all():
            continue
        k0 = int(np.argmin(m))          # empezar en una muestra fuera de curva
        k = 0
        while k < N:
            i = (k0 + k) % N
            if not m[i]:
                k += 1
                continue
            a = k0 + k
            while k < N and m[(k0 + k) % N]:
                k += 1
            curvas.append([a, k0 + k - 1, lado])
    zonas = []
    # (1) pliegues (pares buscados con muestras cada ~2 m: la matriz N x N no crece si la geometria se hace mas fina)
    paso_b = max(1, int(round(2.0 / p)))
    I = np.arange(0, N, paso_b)
    Xb, Yb, Hb = X[I], Y[I], H[I]
    D = np.hypot(Xb[:, None] - Xb[None, :], Yb[:, None] - Yb[None, :]) - (Hb[:, None] + Hb[None, :])
    dk = (I[None, :] - I[:, None]) % N
    ib, jb = np.nonzero((dk * p > H_DS_MIN) & (dk * p < H_DS_MAX) & (D < H_HUECO))
    del D, dk
    plieg = []
    for i, j in zip(I[ib].tolist(), I[jb].tolist()):
        jx = j if j > i else j + N
        g = giro(i, jx)
        if abs(g) >= math.radians(H_GIRO):
            plieg.append((i, jx, 1 if g > 0 else -1))
    plieg.sort()
    fus = []
    for i, jx, lado in plieg:
        if fus and fus[-1][2] == lado and i <= fus[-1][1]:
            fus[-1][1] = max(fus[-1][1], jx)
        else:
            fus.append([i, jx, lado])
    def solapa(lo, hi, a, b):
        """[lo, hi] desplazado una vuelta (-N, 0, +N) para que solape con [a, b], o None."""
        for sh in (-N, 0, N):
            if lo + sh <= b and hi + sh >= a:
                return lo + sh, hi + sh
        return None
    for a, b, lado in fus:
        dentro = [r for r in (solapa(c[0], c[1], a, b) for c in curvas if c[2] == lado) if r]
        if not dentro:
            continue
        c0, c1 = min(r[0] for r in dentro), max(r[1] for r in dentro)
        zonas.append({'k0': c0, 'k1': c1, 'lado': lado, 'tipo': 'horquilla',
                      'giro': round(math.degrees(giro(a, b)), 0), 'pliegue_s': [a * p, (b % N) * p]})
    # (2) curvas cerradas que no estan ya en un pliegue
    for a, b, lado in curvas:
        g = math.degrees(giro(a, b + 1))
        if abs(g) < H_GIRO_CURVA or any(z['lado'] == lado and solapa(a, b, z['k0'], z['k1']) for z in zonas):
            continue
        zonas.append({'k0': a, 'k1': b, 'lado': lado, 'tipo': 'curva_cerrada', 'giro': round(g, 0)})
    for z in zonas:
        z['s0'], z['s1'] = z['k0'] * p - H_EXT, z['k1'] * p + H_EXT
        del z['k0'], z['k1']
    return sorted(zonas, key=lambda z: z['s0'] % P.L)


def cierre_horquillas(P, kd, log, nombre='1WALL_cierre_horquillas'):
    """Muro invisible a E_HORQ m del borde interior de las horquillas y curvas cerradas (curvas_interiores), cosido al
    cierre normal por los dos extremos. Necesita muros_cierre() antes (e por muestra y rayos)."""
    R = _ULTIMO_CIERRE.get('R')
    if R is None:
        log('fisica: cierre_horquillas: falta muros_cierre')
        return {}
    zonas = curvas_interiores(P)
    T = (E_ESCAPE - E_HORQ) / PEND_TRANS + 1.0          # largo maximo de cada transicion
    vs, fs, info = [], [], []
    for z in zonas:
        side = z['lado']
        pts = _ULTIMO_CIERRE[side]['pts']
        cands = _ULTIMO_CIERRE[side]['cands']
        n = len(pts)

        def e_main(k):
            p_ = pts[k % n]
            return None if (p_ is None or cands[k % n]['pit']) else p_[4]
        k_a, k_b = int(math.floor(z['s0'] / DS_CIERRE)), int(math.ceil(z['s1'] / DS_CIERRE))
        nucleo = [e_main(k) for k in range(k_a, k_b + 1)]
        if not any(e is not None and e > E_HORQ_MAX for e in nucleo):
            info.append(dict(z, muro='no hace falta (cierre normal a <= %.1f m)' % E_HORQ_MAX))
            continue
        # polilinea: transicion de entrada (desde 0.4 m por fuera del cierre normal) + nucleo a E_HORQ + transicion de
        # salida (hasta 0.4 m por fuera); nunca mas de 0.4 m por fuera del cierre normal (donde este ya esta cerca,
        # detras de una barrera o una acera, el muro va pegado por detras: cosido, sin rendija)
        col, n_otro = [], 0
        for k in range(k_a - int(T) - 2, k_b + int(T) + 3):
            em = e_main(k)
            fuera = max(k_a - k, k - k_b, 0) * DS_CIERRE
            et = E_HORQ + PEND_TRANS * fuera
            if em is None:
                col.append(None)                         # pit / sin cierre normal
                continue
            if k < k_a and et >= em + 0.4:
                col = [(k, em + 0.4)]                    # extremo de entrada: el ultimo por fuera antes del nucleo
                continue
            col.append((k, min(et, em + 0.4)))
            if k > k_b and et >= em + 0.4:
                break                                    # extremo de salida
        puntos = []
        for c in col:
            if c is None:
                puntos.append(None)
                continue
            k, e = c
            q = P.marco(k * DS_CIERRE)
            h = q['w'] / 2.0
            x, y, ze = P.punto(q, side * (h + e))
            ze = P.punto(q, side * h)[2]
            if R.en_asfalto(x, y, ze, k * DS_CIERRE, margen=E_HORQ_OTRO):
                puntos.append(None)
                n_otro += 1
                continue
            zb, zt = _columna(R, x, y, ze)
            puntos.append((x, y, zb, zt))
        n0 = len(fs)
        idx = {}
        for k in range(len(puntos) - 1):
            a, b = puntos[k], puntos[k + 1]
            if a is None or b is None or math.hypot(b[0] - a[0], b[1] - a[1]) > 4.0:
                continue
            for kk, p_ in ((k, a), (k + 1, b)):
                if kk not in idx:
                    idx[kk] = len(vs)
                    vs.append((p_[0], p_[1], p_[2]))
                    vs.append((p_[0], p_[1], p_[3]))
            i0, i1 = idx[k], idx[k + 1]
            fs.append((i0, i1, i1 + 1, i0 + 1))
            fs.append((i0, i0 + 1, i1 + 1, i1))
        ks = [c[0] for c in col if c is not None]
        info.append(dict(z, muro_m=round((len(fs) - n0) / 2 * DS_CIERRE, 1),
                         s_muro=[round(min(ks) * DS_CIERRE % P.L, 1), round(max(ks) * DS_CIERRE % P.L, 1)] if ks else None,
                         puntos_omitidos_por_otro_tramo=n_otro))
    old = bpy.data.objects.get(nombre)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    if fs:
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(vs, [], fs)
        me.materials.append(_material_invisible())
        me.update()
        ob = bpy.data.objects.new(nombre, me)
        ob.display_type = 'WIRE'
        bpy.context.scene.collection.objects.link(ob)
    for z in info:
        for k in ('s0', 's1'):
            z[k] = round(z[k] % P.L, 1)
    log('fisica: cierre interior de horquillas y curvas cerradas (%s, a %.1f m del borde): %d zonas, %d con muro, '
        '%.0f m: %s' % (nombre, E_HORQ, len(zonas), sum(1 for z in info if 'muro_m' in z),
                        sum(z.get('muro_m', 0) for z in info), info))
    return {'zonas': info, 'caras': len(fs)}


def construir(G, log=print):
    """Punto de entrada (exportar_ac.py, tras renombrar a fisico y crear la rampa de garajes y los AC_*)."""
    t0 = time.time()
    P = Pista(G)
    kd = _kd_pista(P)
    res = {}
    res['pit_libre'] = recorte_pit(G, log)
    res['barreras'] = orientar_barreras(P, kd, log)
    res['calzada'] = subdividir_pista(P, kd, log)
    res['terreno'] = terreno_bajo_asfalto(P, kd, log)
    res['cuna_pit'] = cuna_pit(P, kd, G, log)
    res['pianos'] = pianos_rampa(P, kd, log)
    res['horquilla'] = chaflan_horquilla(P, kd, log)
    res['viaducto'] = labio_viaducto(P, kd, log)
    res['rampa'] = rampa_garajes(log)
    res['cierre'] = muros_cierre(P, kd, G, log)
    res['horquillas'] = cierre_horquillas(P, kd, log)
    res['tapones_boxes'] = tapones_boxes(log)
    bpy.context.scene['porto_corsa_fisica'] = str(res)[:4000]
    log('fisica: cierre_ac completo en %.0fs' % (time.time() - t0))
    return res
