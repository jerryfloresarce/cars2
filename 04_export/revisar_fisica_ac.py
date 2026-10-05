# -*- coding: utf-8 -*-
"""revisar_fisica_ac.py - INSPECTOR de la fisica de Assetto Corsa sobre la escena YA EXPORTADA (exportar_ac.py).

En AC solo colisiona lo que lleva prefijo fisico en el nombre de la malla (1WALL_, 1ROAD_, 1KERB_, 1GRASS_,
2GRASS_, 1DIRT_, 1PIT_) y las caras de espaldas NO se dibujan. Mide:
  (a) BARRERAS: rayos horizontales a 0.4, 0.7 y 1.0 m sobre el borde peraltado, cada 0.5 m de pista y a los dos
      lados, del borde hacia fuera hasta 14 m, contra TODAS las mallas 1WALL_ (BVH en mundo): tramos de hueco
      (sin impacto: s0, s1, lado, largo) y distancia tipica a la barrera.
  (b) BARRERAS FALSAS: objetos con forma de barrera sin prefijo fisico (por nombre) y obstaculos visuales que
      los rayos tocan antes que un 1WALL_ (el coche los atraviesa).
  (c) SUPERFICIE CONDUCIBLE: perfiles cada 0.25 m de la superficie fisica conducible mas alta (rayo vertical)
      por el eje, los cuartos y los bordes de la pista, el eje del pit lane, lineas transversales cada 2 m y
      longitudinales en la entrada (s L-200..L-120) y la salida (100..200) del pit, y del garaje (AC_PIT_*)
      al pit lane: escalones > 0.03 m y cambios de pendiente > 8 % en 1 m.
  (d) 1WALL_ dentro del asfalto (> 0.1 m).
  (e) HUECOS (rayo vertical sin suelo conducible) y superficies ajenas POR ENCIMA del asfalto de la pista.
  (f) CARAS DE ESPALDAS: lo que se ve desde la pista (rayos a 0.4/1.0/1.6 m) por detras: AC no lo dibuja.
  (c2) PIT: ademas del eje, CARRILES paralelos cada 0.5 m de lado a lado de todo el pit lane (escalones / pendiente).
  (g) REJILLA del pit lane (0.5 m x 0.25 m): 1WALL_ dentro del carril, superficie ajena > 0.02 m sobre el 1PIT_pit,
      sin suelo. (h) 1WALL_ a lo largo del pit lane (rayos horizontales por carril a 0.3 / 1.0 m).
  (i) VISIBLES ANTE EL CIERRE: objetos visibles no fisicos entre el borde y el muro de cierre invisible.
  (j) HOYOS VISIBLES del terreno de 0 a 4 m fuera del borde (profundidad de charco > 0.25 m).
  (k) RODADAS de cada garaje (t = 0, +-0.8, +-1.0 m del eje; recto y girando +-20 grados) cada 5 cm hasta el pit lane:
      saltos > 0.03 m (en ronda 2 solo se miraba el eje y no se vio la rampa corta de AC_PIT_0 / AC_PIT_19).
  (l) REJILLA de 0.25 m delante de la puerta de cada garaje: saltos > 0.03 m entre celdas vecinas.
  (m) Superficies fisicas INVISIBLES > 3 cm por encima de la superficie visible (el coche flotaria).
  (n) BORDE FINO en la zona del pit: transversales cada 1 m, del borde derecho a 3 m fuera, cada 5 cm.
  (o) CAIDAS en la escapatoria: del borde a 30/60/90 grados, bajadas de > 0.5 m en 0.25 m antes del primer muro.
  (p) ATAJOS y ESCAPES: coches de 1.8 m que salen de cada borde cada 2 m a 15..90 grados (y 30/60 marcha atras) y
      siguen recto por el suelo fisico: 'atajo' si vuelven al asfalto a > 60 m de pista de donde lo dejaron, con todo
      el coche fuera y ganando >= 5 m (de un ramal de una horquilla al otro, curva cerrada cortada por dentro); 'escape'
      si se alejan > 12 m del borde fuera del pit o caen sin muro. Las cuerdas por la escapatoria de curvas abiertas
      (sin ganar un coche de largo) y el paso por el pit lane salen como informacion.
Ejecutar (SIEMPRE con la cola de Blender):
  BLEND=<escena exportada .blend> GEOM=<geometria .json> OUT=<informe .json> \\
    bash 03_blender/_rev/blender_cola.sh --python 04_export/revisar_fisica_ac.py
  (por defecto BLEND = 04_export/_fisica/escena_ac.blend, GEOM = 03_blender/_rev/geometria_rev.json,
   OUT = <BLEND sin .blend>_fisica.json)
Mapa (python del sistema, matplotlib):  python 04_export/revisar_fisica_ac.py --mapa <informe.json> [salida.png]
"""
import json
import math
import os
import sys
import time

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
SUELO_PREF = ('1ROAD_', '1PIT_', '1KERB_', '1DIRT_', '1GRASS_', '2GRASS_')
MURO_PREF = ('1WALL_',)
PISTA_OBJ = ('1ROAD_pista', '1DIRT_ladera')        # la calzada de la pista (separada de PISTA por exportar_ac)
# familias con forma de barrera: si salen sin prefijo fisico el coche las atraviesa
FAMILIAS_BARRERA = ('CARRERA_muro', 'CARRERA_valla', 'CARRERA_paca', 'CARRERA_portico_zocalo', 'GUARDARRAIL',
                    'VIADUCTO_tramo_balaustrada', 'VIADUCTO_pilastra', 'VIADUCTO_pretil', 'CAMINO_valla',
                    'CAMINO_muro', 'PENON_parapeto', 'PENON_balaustrada', 'PENON_puente_muros', 'PENON_puente_vallas',
                    'MUROC', 'MIRADOR_muro', 'MIRADOR_paseo', 'PIT_muro', 'PIT_amortiguador', 'TUNEL_portal',
                    'PPUEBLO_muro', 'CASINO_escalinata_balaustrada', 'ITAL_bancal_muro', 'LOEWS_tambor',
                    'CARRERA_pantalla_estructura')
# decorado que el coche atraviesa sin que sea un fallo de barrera (vegetacion, pintura, cielo...)
NO_OBSTACULO = ('VEG_', 'OLI_', 'ITAL_cipres', 'ITAL_olivo', 'MARCA', 'linea', 'LINEA', 'AGUA', 'DIRIGIBLE',
                'CAMARA_helicoptero', 'CALLE_guirnalda', 'PIT_marcas', 'MCOCHE_veg', 'PENON_puente_matas',
                'CARRERA_tribuna_publico', 'PIT_boxes_publico', 'CAMINO_marcas', 'PIT_boxes_banderas',
                'PIT_pasarela_banderas',
                # v1.2 (P6 de PETICIONES_04_EXPORT.md): montes del horizonte a 2-5 km (decorado, nunca junto a la pista)
                'HORIZ_')
H_RAYOS = (0.4, 0.7, 1.0)     # alturas de los rayos de barrera sobre el borde peraltado (0.7: viga del guardarrail)
D_MAX = 14.0                  # alcance de los rayos de barrera desde el borde
DS_BARRERA = 0.5              # paso (m) de los rayos de barrera a lo largo de la pista
DS_PERFIL = 0.25              # paso (m) de los perfiles de superficie
UMBRAL_ESCALON = 0.03
UMBRAL_PENDIENTE = 0.08       # cambio de pendiente en 1 m
LINEAS_PIT = ('pit_eje', 'pit_carriles', 'pit_transversal', 'pit_longitudinal', 'garajes')


def fam(nombre):
    """Familia de un objeto: nombre sin sufijo .001 ni numeros finales."""
    b = nombre.split('.')[0]
    while b and (b[-1].isdigit() or b[-1] in '_-'):
        b = b[:-1]
    return b


# ----------------------------------------------------------------------------- geometria de la pista
class Pista:
    def __init__(self, G):
        self.G = G
        self.S = G['muestras']
        self.N = len(self.S)
        self.paso = G['paso_m']
        self.L = G['largo_m']

    def marco(self, s):
        """Muestra interpolada en la abscisa s (m): x, y, z, nx, ny (unitaria), w, lat, sec."""
        s = s % self.L
        f = s / self.paso
        i0 = int(f) % self.N
        i1 = (i0 + 1) % self.N
        t = f - int(f)
        a, b = self.S[i0], self.S[i1]
        q = {k: a[k] + (b[k] - a[k]) * t for k in ('x', 'y', 'z', 'nx', 'ny', 'w', 'lat')}
        ln = math.hypot(q['nx'], q['ny']) or 1.0
        q['nx'] /= ln
        q['ny'] /= ln
        q['sec'] = a['sec']
        q['s'] = s
        return q

    @staticmethod
    def punto(q, u):
        """(x, y, z) a la distancia lateral u (+ = izquierda = +n) sobre el plano peraltado."""
        return q['x'] + q['nx'] * u, q['y'] + q['ny'] * u, q['z'] - q['lat'] * u


def s_unw(s, s0, L):
    """Abscisa desenrollada respecto de s0 (para zonas que cruzan la meta)."""
    return s if s >= s0 else s + L


def lateral(P, kd, x, y):
    """(s, u, t, q) de (x, y) respecto de la pista: abscisa, distancia lateral (+ = izquierda), desvio longitudinal
    residual y marco interpolado en la proyeccion (mismo calculo que cierre_ac._lateral)."""
    _c, i, _d = kd.find((x, y, 0.0))
    q0 = P.S[i]
    t = (x - q0['x']) * q0['ny'] - (y - q0['y']) * q0['nx']
    t = max(-P.paso, min(P.paso, t))
    q = P.marco(i * P.paso + t)
    u = (x - q['x']) * q['nx'] + (y - q['y']) * q['ny']
    t2 = (x - q['x']) * q['ny'] - (y - q['y']) * q['nx']
    return q['s'], u, t2, q


class PitLane:
    """Eje del pit lane (G['pit_lane']: x, y, z, w por punto) con proyeccion sobre el segmento mas cercano."""

    def __init__(self, G, kdtree):
        self.Q = G.get('pit_lane') or []
        self.kd = kdtree.KDTree(max(1, len(self.Q)))
        for i, p in enumerate(self.Q):
            self.kd.insert((p['x'], p['y'], 0.0), i)
        self.kd.balance()

    def segmento(self, i):
        """(A, B, tx, ty, nx, ny, largo) del segmento i (n = izquierda de la marcha de 0 a N-1)."""
        A, B = self.Q[i], self.Q[i + 1]
        vx, vy = B['x'] - A['x'], B['y'] - A['y']
        ln = math.hypot(vx, vy) or 1e-9
        return A, B, vx / ln, vy / ln, -vy / ln, vx / ln, ln

    def lateral(self, x, y):
        """(u, hw, z_eje, i, f, d_fuera): distancia lateral al eje del segmento mas cercano, semiancho y cota del eje
        en la proyeccion, segmento y fraccion, y cuanto queda la proyeccion fuera de los extremos (0 dentro)."""
        if len(self.Q) < 2:
            return None
        best = None
        for (_c, j, _d) in self.kd.find_n((x, y, 0.0), 3):
            for i0 in (j - 1, j):
                if i0 < 0 or i0 + 1 >= len(self.Q):
                    continue
                A, B, tx, ty, nx, ny, ln = self.segmento(i0)
                f = ((x - A['x']) * tx + (y - A['y']) * ty) / ln
                fc = min(1.0, max(0.0, f))
                px, py = A['x'] + tx * ln * fc, A['y'] + ty * ln * fc
                d = math.hypot(x - px, y - py)
                if best is None or d < best[0]:
                    fuera = abs(f - fc) * ln if (i0 == 0 and f < 0) or (i0 + 2 == len(self.Q) and f > 1) else 0.0
                    best = (d, (x - px) * nx + (y - py) * ny, (A['w'] + (B['w'] - A['w']) * fc) / 2.0,
                            A['z'] + (B['z'] - A['z']) * fc, i0, fc, fuera)
        return best[1:] if best else None

    def dentro(self, x, y, margen=0.15):
        """True si (x, y) cae dentro del carril a mas de `margen` del borde (sin pasar de los extremos)."""
        r = self.lateral(x, y)
        return bool(r and r[5] == 0.0 and abs(r[0]) < r[1] - margen)


# ----------------------------------------------------------------------------- BVH en coordenadas mundo
def objetos_exportables(bpy):
    """Mallas que escribe kn5_writer_opt.py (view layer, visibles y renderizables)."""
    objs = []
    for ob in bpy.context.view_layer.objects:
        if ob.type != 'MESH' or ob.hide_render or ob.hide_viewport:
            continue
        try:
            if not ob.visible_get():
                continue
        except Exception:  # noqa
            pass
        objs.append(ob)
    return objs


def tris_mundo(ob, dg, np, claves=False, q=1e-4):
    """(co, tv) en mundo; con claves=True tambien (n_tris, 2) int64: clave de su POLIGONO, independiente del orden y
    de la diagonal (suma y suma de cuadrados del hash de sus vertices cuantizados): una cara y su copia invertida
    (malla a dos caras) tienen la misma clave aunque se trianguen por distinta diagonal."""
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        nt, nv = len(me.loop_triangles), len(me.vertices)
        if nt == 0 or nv == 0:
            return (None, None, None) if claves else (None, None)
        co = np.empty(nv * 3, np.float64)
        me.vertices.foreach_get('co', co)
        tv = np.empty(nt * 3, np.int64)
        me.loop_triangles.foreach_get('vertices', tv)
        if claves:
            tp = np.empty(nt, np.int64)
            me.loop_triangles.foreach_get('polygon_index', tp)
            ls = np.empty(len(me.polygons), np.int64)
            me.polygons.foreach_get('loop_start', ls)
            lv = np.empty(len(me.loops), np.int64)
            me.loops.foreach_get('vertex_index', lv)
    finally:
        ev.to_mesh_clear()
    M = np.array(ob.matrix_world, np.float64)
    co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    if not claves:
        return co, tv.reshape(-1, 3)
    Q = np.round(co / q).astype(np.int64)
    hv = (Q[:, 0] * 73856093) ^ (Q[:, 1] * 19349663) ^ (Q[:, 2] * 83492791)
    hl = hv[lv]
    with np.errstate(over='ignore'):
        k1 = np.add.reduceat(hl, ls) if len(ls) else np.zeros(0, np.int64)
        k2 = np.add.reduceat(hl * hl, ls) if len(ls) else np.zeros(0, np.int64)
    return co, tv.reshape(-1, 3), np.stack([k1[tp], k2[tp], tp], axis=1)      # (clave1, clave2, poligono)


def mallas_mundo(objs, dg, np, claves=False):
    """(V, T, O): vertices en mundo, triangulos y propietario (indice en objs) de cada triangulo; con claves=True
    tambien K (clave de poligono por triangulo, ver tris_mundo)."""
    vs, ts, own, ks = [], [], [], []
    base = 0
    for k, ob in enumerate(objs):
        r = tris_mundo(ob, dg, np, claves)
        co, tv = r[0], r[1]
        if co is None:
            continue
        vs.append(co)
        ts.append(tv + base)
        own.append(np.full(len(tv), k, np.int32))
        if claves:
            kk = r[2].copy()
            kk[:, 2] += np.int64(k) << 32          # poligono unico en todo el conjunto
            ks.append(kk)
        base += len(co)
    if not vs:
        return (None, None, np.zeros(0, np.int32)) + ((None,) if claves else ())
    out = (np.concatenate(vs), np.concatenate(ts), np.concatenate(own))
    return out + ((np.concatenate(ks),) if claves else ())


def bvh_de(objs, dg, np, BVHTree, etiqueta):
    """BVH de varios objetos en mundo; devuelve (bvh, propietario de cada triangulo, n_tris)."""
    t0 = time.time()
    V, T, O = mallas_mundo(objs, dg, np)
    if V is None:
        return None, O, 0
    bvh = BVHTree.FromPolygons(V.tolist(), T.tolist(), all_triangles=True)
    print('BVH %-8s %4d objetos, %8d triangulos [%.1fs]' % (etiqueta, len(objs), len(T), time.time() - t0))
    return bvh, O, len(T)


def caras_gemelas(K, np):
    """Mascara de triangulos cuyo POLIGONO tiene un gemelo con los mismos vertices (la copia invertida de una malla a
    dos caras: se ve por los dos lados). K = claves de mallas_mundo(..., claves=True). (BVHTree.find_nearest_range
    no devolvia ni la propia cara del impacto en estas mallas: no sirve para esto.)"""
    if K is None or not len(K):
        return np.zeros(0, bool)
    # un poligono aporta varios triangulos con la misma clave: se cuentan POLIGONOS distintos por clave
    pol = np.unique(K, axis=0)
    _u, n_pol = np.unique(pol[:, :2], axis=0, return_counts=True)
    _u2, inv = np.unique(K[:, :2], axis=0, return_inverse=True)
    return n_pol[np.asarray(inv).ravel()] >= 2


def es_invisible(nombre):
    """Mallas solo de colision (kn5_writer_opt las escribe con isRenderable=0)."""
    n = nombre.lower()
    return '_invisible' in n or 'cierre' in n


def tramos(flags, paso, s_de_k, extra=None):
    """Agrupa indices consecutivos marcados en tramos [(s0, s1, largo, k0, k1)]."""
    out = []
    k = 0
    n = len(flags)
    while k < n:
        if not flags[k]:
            k += 1
            continue
        k0 = k
        while k < n and flags[k]:
            k += 1
        out.append({'s0': round(s_de_k(k0), 1), 's1': round(s_de_k(k - 1), 1), 'largo': round((k - k0) * paso, 1),
                    'k0': k0, 'k1': k - 1})
    return out


class Inspector:
    def __init__(self, bpy, np, Vector, BVHTree, kdtree, G):
        self.np, self.V = np, Vector
        self.P = Pista(G)
        self.G = G
        objs = objetos_exportables(bpy)
        dg = bpy.context.evaluated_depsgraph_get()
        P = self.P
        kd = kdtree.KDTree(P.N)
        for i, q in enumerate(P.S):
            kd.insert((q['x'], q['y'], 0.0), i)
        kd.balance()
        self.kd = kd

        def cerca(ob, margen=18.0):
            cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            cx = sum(c.x for c in cs) / 8.0
            cy = sum(c.y for c in cs) / 8.0
            r = max(math.hypot(c.x - cx, c.y - cy) for c in cs)
            _co, i, d = kd.find((cx, cy, 0.0))
            return d - r < P.S[i]['w'] / 2.0 + margen
        self.cerca = cerca
        self.objs = objs
        self.muros = [o for o in objs if o.name.startswith(MURO_PREF)]
        self.suelos = [o for o in objs if o.name.startswith(SUELO_PREF)]
        self.pista = [o for o in objs if o.name.startswith(PISTA_OBJ)]
        fis = MURO_PREF + SUELO_PREF + ('AC_',)
        self.visuales = [o for o in objs if not o.name.startswith(fis) and not o.name.startswith(NO_OBSTACULO)
                         and cerca(o)]
        self.render = [o for o in self.muros if not es_invisible(o.name) and cerca(o, 30.0)] + self.visuales
        self.b_muro, self.o_muro, self.n_muro = bvh_de(self.muros, dg, np, BVHTree, 'muros')
        self.b_suelo, self.o_suelo, self.n_suelo = bvh_de(self.suelos, dg, np, BVHTree, 'suelo')
        self.b_pista, self.o_pista, _n = bvh_de(self.pista, dg, np, BVHTree, 'pista')
        self.b_vis, self.o_vis, self.n_vis = bvh_de(self.visuales, dg, np, BVHTree, 'visual')
        Vr, Tr, self.o_ren, Kr = mallas_mundo(self.render, dg, np, claves=True)
        self.b_ren = BVHTree.FromPolygons(Vr.tolist(), Tr.tolist(), all_triangles=True) if Vr is not None else None
        self.n_ren = len(Tr) if Vr is not None else 0
        self.gem_ren = caras_gemelas(Kr, np)
        del Vr, Tr, Kr
        # pit lane (rejilla), muros visibles / invisibles (lo que hay delante del cierre), terreno y todo lo que se
        # ve (hoyos visibles del terreno junto al borde)
        self.PL = PitLane(G, kdtree)
        self.pitl = [o for o in self.suelos if o.name.split('.')[0] == '1PIT_pit']
        self.b_pitl = bvh_de(self.pitl, dg, np, BVHTree, 'pit')[0]
        self.m_vis = [o for o in self.muros if not es_invisible(o.name)]
        self.m_inv = [o for o in self.muros if es_invisible(o.name)]
        self.b_mvis, self.o_mvis, _n = bvh_de(self.m_vis, dg, np, BVHTree, 'mur_vis')
        self.b_minv, self.o_minv, _n = bvh_de(self.m_inv, dg, np, BVHTree, 'mur_inv')
        self.terr = [o for o in self.suelos if o.name.startswith('1GRASS_terreno')]
        self.b_ter, _o, _n = bvh_de(self.terr, dg, np, BVHTree, 'terreno')
        self.todo = ([o for o in self.suelos if not es_invisible(o.name) and cerca(o, 12.0)] + self.render)
        self.b_todo, self.o_todo, _n = bvh_de(self.todo, dg, np, BVHTree, 'todo')
        self.inf = {'blend': os.environ.get('BLEND'), 'n_objetos': len(objs), 'n_muros': len(self.muros),
                    'n_suelos': len(self.suelos), 'tris_muros': self.n_muro, 'tris_suelo': self.n_suelo,
                    'invisibles': sorted(o.name for o in self.muros if es_invisible(o.name))}

    # --- rayos
    def rayo(self, bvh, own, objs, o, d, dist):
        if bvh is None:
            return None
        loc, nor, idx, dd = bvh.ray_cast(self.V(o), self.V(d), dist)
        if loc is None:
            return None
        return dd, objs[int(own[idx])].name, loc, nor, idx

    def cara_delante(self, idx):
        """True si el triangulo del impacto tiene gemelo invertido (malla a dos caras: la de delante se dibuja)."""
        return bool(self.gem_ren[idx]) if 0 <= idx < len(self.gem_ren) else False

    def suelo(self, x, y, zref, arriba=1.5, abajo=2.5):
        """(z, nombre) de la superficie conducible mas alta bajo (x, y) entre zref-abajo y zref+arriba."""
        h = self.rayo(self.b_suelo, self.o_suelo, self.suelos, (x, y, zref + arriba), (0, 0, -1), arriba + abajo)
        return (h[2].z, h[1]) if h else None

    def muro_encima(self, x, y, z, alto=1.5):
        """Nombre del 1WALL_ que ocupa la vertical de (x, y) entre z y z+alto (el coche no puede estar ahi) o None."""
        h = self.rayo(self.b_muro, self.o_muro, self.muros, (x, y, z + alto), (0, 0, -1), alto - 0.02)
        return h[1] if h is not None else None

    # --- (a) barreras, (d) muros dentro del asfalto, (b) obstaculos falsos, (f) caras de espaldas
    def barreras(self):
        P, V = self.P, self.V
        n = int(P.L / DS_BARRERA)
        res = {1: [None] * n, -1: [None] * n}
        invas, falsos, espaldas, delante = [], {}, {}, {}
        for k in range(n):
            s = k * DS_BARRERA
            q = P.marco(s)
            h = q['w'] / 2.0
            for side in (1, -1):
                ex, ey, ez = P.punto(q, side * h)
                cx, cy, cz = P.punto(q, 0.0)
                d = (side * q['nx'], side * q['ny'], 0.0)
                mejor = None
                for hh in H_RAYOS:
                    r = self.rayo(self.b_muro, self.o_muro, self.muros, (ex, ey, ez + hh), d, D_MAX)
                    if r and (mejor is None or r[0] < mejor[0]):
                        mejor = r
                    # (d) muro dentro del asfalto: rayo por el plano peraltado del eje al borde
                    vin = V((ex - cx, ey - cy, ez - cz))
                    lv = vin.length
                    ri = self.rayo(self.b_muro, self.o_muro, self.muros, (cx, cy, cz + hh), vin.normalized(), lv - 0.1)
                    if ri:
                        inv = h - ri[0] * h / lv
                        if inv > 0.1:
                            invas.append({'s': round(s, 1), 'lado': side, 'h': hh, 'invade_m': round(inv, 2),
                                          'objeto': ri[1]})
                    # (b) obstaculo visual antes que cualquier muro
                    rv = self.rayo(self.b_vis, self.o_vis, self.visuales, (ex, ey, ez + hh), d, D_MAX)
                    if rv and (r is None or rv[0] < r[0] - 0.3):
                        f = fam(rv[1])
                        falsos.setdefault(f, []).append((round(s, 1), side, round(rv[0], 2)))
                res[side][k] = (round(mejor[0], 2), fam(mejor[1])) if mejor else None
                # (f) lo que se ve desde la pista: cara de delante o de espaldas
                for hh in (0.4, 1.0, 1.6):
                    rr = self.rayo(self.b_ren, self.o_ren, self.render, (ex, ey, ez + hh), d, 30.0)
                    if rr is None:
                        continue
                    f = fam(rr[1])
                    if rr[3].dot(V(d)) > 0.05 and not self.cara_delante(rr[4]):
                        espaldas.setdefault(f, []).append((round(s, 1), side, hh, round(rr[0], 2)))
                    else:
                        delante[f] = delante.get(f, 0) + 1
        self.res_barrera = res
        return res, invas, falsos, espaldas, delante

    # --- (c) perfiles de la superficie conducible
    def perfil(self, pts, ds, marchar=False):
        """pts = [(x, y, zref, s_o_None)] cada ds m. Devuelve (zs, nombres, n_bajo_muro, huecos). Con marchar,
        la cota de referencia de cada punto es la del anterior (sigue rampas y escalones fuera del plano)."""
        zs, noms, huecos = [], [], []
        n_muro = 0
        zprev = None
        for (x, y, zr, s) in pts:
            zref = zprev if (marchar and zprev is not None and abs(zprev - zr) < 1.2) else zr
            r = self.suelo(x, y, zref)
            if r is None:
                zs.append(None)
                noms.append(None)
                huecos.append((round(x, 2), round(y, 2), s))
                zprev = None
                continue
            mu = self.muro_encima(x, y, r[0])
            if mu and marchar and es_invisible(mu):
                break                           # muro de cierre: lo que hay detras ya no es circuito
            if mu:
                n_muro += 1
                zs.append(None)                 # bajo un muro: el coche no puede estar ahi
                noms.append('(muro)')
                zprev = r[0]
                continue
            zs.append(r[0])
            noms.append(r[1])
            zprev = r[0]
        return zs, noms, n_muro, huecos

    @staticmethod
    def eventos(zs, noms, pts, ds):
        """Escalones (> UMBRAL_ESCALON) y cambios de pendiente (> UMBRAL_PENDIENTE en 1 m) de un perfil."""
        m = max(1, int(round(1.0 / ds)))
        n = len(zs)
        crudo = []
        for k in range(1, n - 2):
            w = zs[k - 1:k + 3]
            if None in w:
                continue
            e = (w[2] - w[1]) - 0.5 * ((w[1] - w[0]) + (w[3] - w[2]))
            if abs(e) > UMBRAL_ESCALON:
                crudo.append(('escalon', k, e))
        for k in range(m, n - m):
            if zs[k - m] is None or zs[k] is None or zs[k + m] is None:
                continue
            dg = (zs[k + m] - zs[k]) - (zs[k] - zs[k - m])
            if abs(dg) > UMBRAL_PENDIENTE:
                crudo.append(('pendiente', k, dg))
        out = []
        for tipo in ('escalon', 'pendiente'):
            ev = sorted((c for c in crudo if c[0] == tipo), key=lambda c: c[1])
            grupo = []
            for c in ev + [None]:
                if c is not None and grupo and c[1] - grupo[-1][1] <= m:
                    grupo.append(c)
                    continue
                if grupo:
                    g = max(grupo, key=lambda c: abs(c[2]))
                    k = g[1]
                    x, y, _zr, s = pts[k]
                    sup = sorted({fam(noms[j]) for j in range(max(0, k - 1), min(n, k + 3)) if noms[j]})
                    out.append({'tipo': tipo, 'valor': round(g[2], 3), 'x': round(x, 2), 'y': round(y, 2),
                                'pos': (round(s, 2) if s is not None else None), 'z': round(zs[k], 3),
                                'superficies': sup, 'kerb': any(f.startswith('1KERB') for f in sup)})
                grupo = [c] if c is not None else []
        return out

    def lineas_pista(self):
        """Perfiles longitudinales de la pista: eje, cuartos y bordes (u = 0, +-w/4, +-(w/2-0.3))."""
        P = self.P
        n = int(P.L / DS_PERFIL)
        lineas = {}
        for nom, f, off in (('eje', 0.0, 0.0), ('cuarto_izq', 0.25, 0.0), ('cuarto_der', -0.25, 0.0),
                            ('borde_izq', 0.5, -0.3), ('borde_der', -0.5, 0.3)):
            pts = []
            for k in range(n):
                q = P.marco(k * DS_PERFIL)
                u = f * q['w'] + off
                x, y, z = P.punto(q, u)
                pts.append((x, y, z, k * DS_PERFIL))
            lineas[nom] = pts
        return lineas

    def ajenas(self, pts, noms, zs):
        """(e) superficie conducible que NO es la calzada y queda > 2 cm por encima de ella."""
        out = []
        for (x, y, zr, s), nm, z in zip(pts, noms, zs):
            if nm is None or z is None or nm.startswith(PISTA_OBJ) or nm.startswith('1KERB_'):
                continue
            h = self.rayo(self.b_pista, self.o_pista, self.pista, (x, y, z + 0.5), (0, 0, -1), 3.0)
            if h is None:
                continue
            dz = z - h[2].z
            if dz > 0.02:
                out.append((s, nm, dz))
        return out


    # --- lineas del pit: eje, transversales, longitudinales y garajes
    def lineas_pit(self, bpy):
        P = self.P
        L = P.L
        PIT = self.G.get('pit_lane') or []
        out = {}
        # eje del pit lane remuestreado cada DS_PERFIL
        pts = []
        for a, b in zip(PIT, PIT[1:]):
            d = math.hypot(b['x'] - a['x'], b['y'] - a['y'])
            m = max(1, int(d / DS_PERFIL))
            for j in range(m):
                t = j / float(m)
                x, y = a['x'] + (b['x'] - a['x']) * t, a['y'] + (b['y'] - a['y']) * t
                _c, i, _d = self.kd.find((x, y, 0.0))
                pts.append((x, y, a['z'] + (b['z'] - a['z']) * t, i * P.paso))
        out['pit_eje'] = [('eje', None, pts)]
        zonas = ((L - 200.0, L - 120.0, 'entrada'), (100.0, 200.0, 'salida'))
        # transversales cada 2 m: de +(w/2-0.3) a -(w/2+16)
        trans = []
        for s0, s1, zn in zonas:
            s = s0
            while s <= s1 + 1e-6:
                q = P.marco(s)
                h = q['w'] / 2.0
                pts = []
                u = h - 0.3
                while u >= -(h + 16.0):
                    x, y, _z = P.punto(q, u)
                    pts.append((x, y, P.punto(q, max(u, -h))[2], round(u, 2)))
                    u -= DS_PERFIL
                trans.append(('%s_s%.0f' % (zn, s), round(s % L, 1), pts))
                s += 2.0
        out['pit_transversal'] = trans
        # longitudinales paralelas al borde del lado de boxes (u = -w/2 + o)
        lon = []
        for s0, s1, zn in ((L - 205.0, L - 105.0, 'entrada'), (95.0, 210.0, 'salida')):
            for o in [0.5] + [-0.5 - j for j in range(13)]:
                pts = []
                s = s0
                while s <= s1:
                    q = P.marco(s)
                    h = q['w'] / 2.0
                    x, y, _z = P.punto(q, -h + o)
                    pts.append((x, y, P.punto(q, max(-h + o, -h))[2], round(s % L, 2)))
                    s += DS_PERFIL
                lon.append(('%s_u%+.1f' % (zn, o), o, pts))
        out['pit_longitudinal'] = lon
        # garajes: de cada AC_PIT_* hacia el pit lane (el +Z de AC = (sin rz, -cos rz) en Blender), 18 m
        gar = []
        for ob in sorted((o for o in bpy.data.objects if o.name.startswith('AC_PIT_')), key=lambda o: o.name):
            rz = ob.rotation_euler.z
            dx, dy = math.sin(rz), -math.cos(rz)
            z0 = ob.location.z - 1.0
            pts = [(ob.location.x + dx * t, ob.location.y + dy * t, z0, round(t, 2))
                   for t in [j * DS_PERFIL for j in range(int(18.0 / DS_PERFIL) + 1)]]
            gar.append((ob.name, None, pts))
        out['garajes'] = gar
        # carriles: paralelas al eje del pit lane cada 0.5 m de lado a lado, de punta a punta (cubren entre los
        # garajes y la salida, s ~ 49..170, donde antes solo se miraba el eje)
        car = []
        Q = self.PL.Q
        if len(Q) >= 2:
            hw_max = max(p['w'] for p in Q) / 2.0
            for j in range(int(2 * (hw_max - 0.3) / 0.5) + 1):
                u = -(hw_max - 0.3) + 0.5 * j
                pts = []
                for i in range(len(Q) - 1):
                    A, B, tx, ty, nx, ny, ln = self.PL.segmento(i)
                    m = max(1, int(ln / DS_PERFIL))
                    for k in range(m):
                        f = k / float(m)
                        hw = (A['w'] + (B['w'] - A['w']) * f) / 2.0
                        uu = max(-(hw - 0.3), min(hw - 0.3, u))      # dentro del carril donde se estrecha
                        x = A['x'] + tx * ln * f + nx * uu
                        y = A['y'] + ty * ln * f + ny * uu
                        pts.append((x, y, A['z'] + (B['z'] - A['z']) * f, round(i + f, 3)))
                car.append(('carril_u%+.1f' % u, round(u, 2), pts))
        out['pit_carriles'] = car
        return out

    # --- (g) rejilla del pit lane: muros dentro, superficies ajenas por encima del 1PIT_pit, huecos
    def pit_rejilla(self, ds=0.5, du=0.25):
        """Cada ds m del eje y du m a lo ancho (hasta 1 m fuera del borde): suelo conducible mas alto, cota del
        1PIT_pit y obstaculos 1WALL_ entre 0.05 y 2.0 m sobre el suelo. Fallos DENTRO del carril (|u| <= hw-0.25):
        'muro:<obj>', 'encima:<obj>' (otra superficie > 0.02 m sobre el 1PIT_pit, salvo la propia pista) y
        'sin_suelo'. 'sin_1PIT' (suelo sin losa de pit) es informativo."""
        V = self.V
        Q = self.PL.Q
        mal = {}
        n = 0
        for i in range(len(Q) - 1):
            A, B, tx, ty, nx, ny, ln = self.PL.segmento(i)
            m = max(1, int(ln / ds))
            for k in range(m):
                f = k / float(m)
                cz = A['z'] + (B['z'] - A['z']) * f
                hw = (A['w'] + (B['w'] - A['w']) * f) / 2.0
                u = -hw - 1.0
                while u <= hw + 1.0001:
                    x = A['x'] + tx * ln * f + nx * u
                    y = A['y'] + ty * ln * f + ny * u
                    dentro = abs(u) <= hw - 0.25
                    n += 1
                    g = self.suelo(x, y, cz, 1.2, 2.5)
                    zp = None
                    if self.b_pitl is not None:
                        lp, _nn, _ip, _dd = self.b_pitl.ray_cast(V((x, y, cz + 1.2)), V((0, 0, -1)), 3.7)
                        zp = lp.z if lp is not None else None
                    clave = None
                    if g is None:
                        clave = 'sin_suelo' if dentro else None
                    else:
                        mu = self.muro_encima(x, y, g[0], 2.0)
                        if mu is None:
                            r = self.rayo(self.b_muro, self.o_muro, self.muros, (x, y, g[0] + 0.05), (0, 0, 1), 1.95)
                            mu = r[1] if r else None
                        if mu and dentro:
                            clave = 'muro:' + mu
                        elif (zp is not None and g[0] - zp > 0.02 and not g[1].startswith(('1PIT_',) + PISTA_OBJ)
                              and not g[1].startswith('1KERB_')):
                            clave = ('encima:' if abs(u) <= hw + 1e-3 else 'borde_encima:') + g[1]
                        elif dentro and zp is None and not g[1].startswith(('1PIT_',) + PISTA_OBJ):
                            clave = 'sin_1PIT:' + g[1]
                    if clave:
                        mal.setdefault(clave, []).append((i, round(u, 2), round(x, 2), round(y, 2),
                                                          round(g[0] - zp, 3) if (g and zp is not None) else None))
                    u += du
        res = {}
        for k, v in sorted(mal.items(), key=lambda kv: -len(kv[1])):
            dzs = [p[4] for p in v if p[4] is not None]
            res[k] = {'n': len(v), 'indices_pit': sorted({p[0] for p in v})[:40],
                      'u': [min(p[1] for p in v), max(p[1] for p in v)], 'dz_max': max(dzs) if dzs else None,
                      'xy': [[min(p[2] for p in v), max(p[2] for p in v)], [min(p[3] for p in v), max(p[3] for p in v)]],
                      'ejemplos': v[:4]}
        fallos = {k: v['n'] for k, v in res.items() if k.startswith(('muro:', 'encima:', 'sin_suelo'))}
        return {'n_puntos': n, 'claves': res, 'fallos': fallos, 'n_fallos': sum(fallos.values())}

    # --- (h) muros a lo largo del pit lane (rayos horizontales por cada carril a 0.3 y 1.0 m)
    def pit_muros_largo(self):
        V = self.V
        Q = self.PL.Q
        hits = []
        for i in range(len(Q) - 1):
            A, B, tx, ty, nx, ny, ln = self.PL.segmento(i)
            hw = min(A['w'], B['w']) / 2.0 - 0.3
            for j in range(-int(hw / 0.5), int(hw / 0.5) + 1):
                u = j * 0.5
                x, y = A['x'] + nx * u, A['y'] + ny * u
                g = self.suelo(x, y, A['z'], 1.2, 2.5)
                z0 = g[0] if g else A['z']
                d = V((B['x'] - A['x'], B['y'] - A['y'], B['z'] - A['z']))
                for hh in (0.3, 1.0):
                    r = self.rayo(self.b_muro, self.o_muro, self.muros, (x, y, z0 + hh), d.normalized(), d.length)
                    if r:
                        hits.append({'i': i, 'u': u, 'h': hh, 'objeto': r[1], 'xy': [round(r[2].x, 1), round(r[2].y, 1)]})
                        break
        por = {}
        for h in hits:
            por[h['objeto']] = por.get(h['objeto'], 0) + 1
        return {'n': len(hits), 'por_objeto': por, 'lista': hits[:60]}

    # --- (i) objetos visibles NO fisicos entre el borde y el muro de cierre invisible (el coche los atraviesa y se
    # para contra un muro que no se ve)
    def visuales_ante_cierre(self, e_max=8.0):
        """Por vertice de cada objeto visual cercano, en la banda de 0.1 a 1.5 m sobre el borde y fuera del asfalto:
        rayo horizontal del borde hacia el vertice. Fallo si el cierre invisible esta MAS LEJOS que el vertice y no
        hay un 1WALL_ visible antes."""
        if self.b_minv is None:
            return {'n_objetos': 0, 'familias': {}, 'objetos': []}
        P, V = self.P, self.V
        out = {}
        for ob in self.visuales:
            if not self.cerca(ob, e_max):
                continue
            mw = ob.matrix_world
            best = None
            for v in ob.data.vertices:
                w = mw @ v.co
                s, u, t, q = lateral(P, self.kd, w.x, w.y)
                h = q['w'] / 2.0
                e = abs(u) - h
                if e <= 0.05 or e > e_max or abs(t) > 1.5:
                    continue
                side = 1 if u > 0 else -1
                ex, ey, ez = P.punto(q, side * h)
                if not (ez + 0.1 <= w.z <= ez + 1.5):
                    continue
                if best is not None and e >= best[0]:
                    continue
                d = V((w.x - ex, w.y - ey, 0.0))
                dist = d.length
                if dist < 1e-3:
                    continue
                d.normalize()
                o = V((ex, ey, w.z))
                lc, _n, _i, dc = self.b_minv.ray_cast(o, d, dist + 25.0)
                if lc is None or dc < dist:
                    continue                    # cierre antes del objeto (queda fuera del circuito) o sin cierre
                if self.b_mvis is not None:
                    lv, _n, _i, _dv = self.b_mvis.ray_cast(o, d, dist + 0.3)
                    if lv is not None:
                        continue                # una barrera visible lo tapa (o lo sostiene: rotulo pegado al cartel)
                best = (e, round(s, 1), side, round(dc - dist, 2))
            if best:
                out[ob.name] = {'e': round(best[0], 2), 's': best[1], 'lado': best[2], 'cierre_detras_m': best[3]}
        fams = {}
        for nm, r in out.items():
            f = fam(nm)
            a = fams.setdefault(f, {'n': 0, 'e_min': 99.0, 's': []})
            a['n'] += 1
            a['e_min'] = min(a['e_min'], r['e'])
            if len(a['s']) < 20:
                a['s'].append((r['s'], r['lado']))
        return {'n_objetos': len(out), 'familias': dict(sorted(fams.items(), key=lambda kv: -kv[1]['n'])),
                'objetos': sorted(out.items(), key=lambda kv: kv[1]['s'])[:200]}

    # --- (j) hoyos VISIBLES del terreno junto al borde (p. ej. vertices hundidos bajo el asfalto)
    def terreno_hoyos(self, ds=1.0, umbral=0.25):
        """Perfil del 1GRASS_terreno de e = 0 a 4 m fuera del borde cada 0.25 m: profundidad de 'charco' (cuanto
        queda por debajo de min(borde, terreno mas alto hacia fuera)). Hoyo si > umbral y lo que se ve desde arriba
        en ese punto es el propio terreno."""
        if self.b_ter is None:
            return {'n_puntos': 0}
        P, V = self.P, self.V
        pts = []
        es = [0.25 * j for j in range(17)]
        for k in range(int(P.L / ds)):
            q = P.marco(k * ds)
            h = q['w'] / 2.0
            for side in (1, -1):
                ze = P.punto(q, side * h)[2]
                zs = []
                for e in es:
                    x, y, _z = P.punto(q, side * (h + e))
                    lt, _n, _i, _d = self.b_ter.ray_cast(V((x, y, ze + 3.0)), V((0, 0, -1)), 15.0)
                    zs.append((lt.z if lt is not None else None, x, y))
                for j, (z, x, y) in enumerate(zs):
                    if z is None:
                        continue
                    fuera = [zz for (zz, _a, _b) in zs[j + 1:] if zz is not None]
                    if not fuera or max(fuera) < ze - 0.5:
                        continue                # terreno que baja hacia fuera (terraplen, valle bajo un puente)
                    prof = min(ze, max(fuera)) - z
                    if prof <= umbral:
                        continue
                    lt, _n, it, _d = self.b_todo.ray_cast(V((x, y, z + 6.0)), V((0, 0, -1)), 6.3)
                    if lt is None or not self.todo[int(self.o_todo[it])].name.startswith('1GRASS_terreno'):
                        continue                # tapado por arcen, acera, muro...
                    pts.append((round(k * ds, 1), side, es[j], round(prof, 2)))
        trs = rangos(pts, junta=3.0)
        return {'n_puntos': len(pts), 'prof_max': max([p[3] for p in pts], default=0.0),
                'tramos': trs[:80], 'ejemplos': sorted(pts, key=lambda p: -p[3])[:30]}

    # --- (k) rodadas de salida de cada garaje y (l) rejilla delante de su puerta
    def seguir(self, x, y, zg, subida=0.7, caida=1.5):
        """Cota del suelo siguiendo al coche desde zg: (estado, z, nombre); estado 'ok' | 'talud' | 'cae'."""
        up = self.rayo(self.b_suelo, self.o_suelo, self.suelos, (x, y, zg + 0.02), (0, 0, 1), 1.6)
        if up is not None:
            z = zg + 0.02 + up[0]
            return ('ok' if z - zg <= subida else 'talud'), z, up[1]
        dn = self.rayo(self.b_suelo, self.o_suelo, self.suelos, (x, y, zg + 0.02), (0, 0, -1), 60.0)
        if dn is None:
            return 'cae', None, None
        z = zg + 0.02 - dn[0]
        return ('ok' if zg - z <= caida else 'cae'), z, dn[1]

    def rodadas_garajes(self, bpy, paso=0.05, u0=-1.5, u1=9.0):
        """Desde cada AC_PIT_*: rodadas t = -1.0/-0.8/0/+0.8/+1.0 m del eje, recto y girando +-20 grados, del fondo
        (u0) a u1 m hacia el pit lane: suelo fisico cada `paso` m siguiendo al coche hasta el primer 1WALL_ (0.3 m);
        fallo = salto > 0.03 m entre dos puntos seguidos (con `paso` = 5 cm, una pendiente de > 60 %)."""
        V = self.V
        out, peor = {}, {}
        for ob in sorted((o for o in bpy.data.objects if o.name.startswith('AC_PIT_')),
                         key=lambda o: int(o.name.split('_')[-1].split('.')[0])):
            rz = ob.rotation_euler.z
            ux, uy = math.sin(rz), -math.cos(rz)
            tx, ty = -uy, ux
            x0, y0, z0 = ob.location.x, ob.location.y, ob.location.z - 1.0
            fallos = []
            for giro in (0.0, 20.0, -20.0):
                c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))
                dx, dy = ux * c + tx * s, uy * c + ty * s
                for t in (-1.0, -0.8, 0.0, 0.8, 1.0):
                    x, y = x0 + (-dy) * t + dx * u0, y0 + dx * t + dy * u0
                    g = self.suelo(x, y, z0, 0.6, 1.5)
                    if g is None:
                        fallos.append((giro, t, u0, None, 'sin_suelo'))
                        continue
                    z, nom = g
                    for k in range(1, int((u1 - u0) / paso) + 1):
                        xn, yn = x + dx * paso, y + dy * paso
                        d = V((dx, dy, 0.0))
                        if self.rayo(self.b_muro, self.o_muro, self.muros, (x, y, z + 0.3), d, paso):
                            break
                        st, zn, nn = self.seguir(xn, yn, z)
                        if zn is None or abs(zn - z) > 0.03:
                            fallos.append((giro, t, round(u0 + k * paso, 2), None if zn is None else round(zn - z, 3),
                                           '%s>%s' % (fam(nom or ''), fam(nn or ''))))
                            if zn is None or st != 'ok':
                                break
                        x, y, z, nom = xn, yn, zn, nn
            out[ob.name] = fallos[:12]
            peor[ob.name] = max([abs(f[3]) for f in fallos if f[3] is not None] + [0.0])
        return {'n_garajes': len(out), 'n_fallos': sum(len(v) for v in out.values()),
                'peor_salto_m': peor, 'fallos': {k: v for k, v in out.items() if v}}

    def garajes_rejilla(self, bpy, du=0.25, u0=-1.5, u1=8.0, t_med=2.9):
        """Delante de la puerta de cada garaje (u0..u1 hacia el pit lane, |t| <= t_med): suelo fisico mas alto cada
        `du` m; fallo = salto > 0.03 m entre celdas vecinas sin 1WALL_ encima de ninguna de las dos."""
        res, n_f = {}, 0
        for ob in sorted((o for o in bpy.data.objects if o.name.startswith('AC_PIT_')),
                         key=lambda o: int(o.name.split('_')[-1].split('.')[0])):
            rz = ob.rotation_euler.z
            ux, uy = math.sin(rz), -math.cos(rz)
            tx, ty = -uy, ux
            x0, y0, z0 = ob.location.x, ob.location.y, ob.location.z - 1.0
            U = [u0 + du * i for i in range(int((u1 - u0) / du) + 1)]
            T = [-t_med + du * j for j in range(int(2 * t_med / du) + 1)]
            Z, N, B = {}, {}, {}
            for i, u in enumerate(U):
                for j, t in enumerate(T):
                    x, y = x0 + ux * u + tx * t, y0 + uy * u + ty * t
                    g = self.suelo(x, y, z0, 1.5, 2.5)
                    Z[i, j], N[i, j] = (g if g else (None, None))
                    B[i, j] = bool(g and self.muro_encima(x, y, g[0] + 0.05, 1.95))
            mal = []
            for (i, j), z in Z.items():
                for di, dj in ((1, 0), (0, 1)):
                    b = (i + di, j + dj)
                    if z is None or Z.get(b) is None or B[i, j] or B[b]:
                        continue
                    if abs(Z[b] - z) > 0.03:
                        mal.append((U[i], T[j], 'u' if di else 't', round(Z[b] - z, 3), fam(N[i, j]), fam(N[b])))
            n_f += len(mal)
            if mal:
                res[ob.name] = {'n': len(mal), 'max': max(abs(m[3]) for m in mal), 'ejemplos': mal[:10]}
        return {'n_fallos': n_f, 'garajes': res}

    # --- (m) superficies fisicas INVISIBLES por encima de lo que se ve (el coche flota sobre la hierba visible); se
    # compara con TODO lo visible (suelos fisicos y decorado: el labio del viaducto copia un decorado)
    def invisibles_sobre_visible(self):
        P = self.P
        inv = [o for o in self.suelos if es_invisible(o.name)]
        vis = [o for o in self.objs if not es_invisible(o.name) and not o.name.startswith('AC_')
               and not o.name.startswith(NO_OBSTACULO) and self.cerca(o, 30.0)]
        if not inv or not vis:
            return {'n': 0}
        import bpy as _b
        from mathutils.bvhtree import BVHTree as _BT
        b_v = bvh_de(vis, _b.context.evaluated_depsgraph_get(), self.np, _BT, 'suelo_vis')[0]
        out = {}
        for ob in inv:
            mw = ob.matrix_world
            ds, mal = [], []
            for f in ob.data.polygons:
                c = mw @ f.center
                loc = b_v.ray_cast(self.V((c.x, c.y, c.z + 1.0)), self.V((0, 0, -1)), 3.0)[0]
                if loc is None:
                    continue
                d = c.z - loc.z
                ds.append(d)
                if d > 0.03:
                    s, u, _t, _q = lateral(P, self.kd, c.x, c.y)
                    mal.append((round(c.x, 1), round(c.y, 1), round(s, 1), round(d, 3)))
            out[ob.name] = {'caras': len(ob.data.polygons), 'medidas': len(ds), 'max_m': round(max(ds), 3) if ds else None,
                            'n_mas_3cm': len(mal), 'ejemplos': sorted(mal, key=lambda m: -m[3])[:12]}
        return {'n': sum(v['n_mas_3cm'] for v in out.values()), 'mallas': out}

    # --- (n) borde de la calzada en la zona del pit, fino: transversales cada 1 m, de 0.3 m dentro a 3 m fuera del
    # borde derecho, cada 5 cm (las de 0.25 m no veian una ranura de 5-10 cm de ancho, s 134)
    def borde_fino_pit(self, ds=1.0, paso=0.05, dentro=0.3, fuera=3.0):
        P = self.P
        L = P.L
        Q = self.PL.Q
        if len(Q) < 2:
            return {'n_fallos': 0}
        s0 = lateral(P, self.kd, Q[0]['x'], Q[0]['y'])[0]
        s1 = lateral(P, self.kd, Q[-1]['x'], Q[-1]['y'])[0]
        s1 = s1 + L if s1 < s0 else s1
        fallos, kerb = [], 0
        s = s0
        while s <= s1:
            q = P.marco(s % L)
            h = q['w'] / 2.0
            e = -dentro
            zp, np_ = None, None
            while e <= fuera + 1e-6:
                x, y, _z = P.punto(q, -(h + e))
                zr = P.punto(q, -(h + min(e, 0.0)))[2] if zp is None else zp
                g = self.suelo(x, y, zr, 0.8, 1.5)
                if g is None:
                    break
                if self.muro_encima(x, y, g[0] + 0.05, 1.5):
                    break
                if zp is not None and abs(g[0] - zp) > 0.03:
                    par = (fam(np_ or ''), fam(g[1]))
                    if any(f.startswith('1KERB') for f in par):
                        kerb += 1
                    else:
                        fallos.append((round(s % L, 1), round(e, 2), round(g[0] - zp, 3), par[0], par[1]))
                zp, np_ = g
                e += paso
            s += ds
        return {'n_fallos': len(fallos), 'n_kerb': kerb, 'max_m': max([abs(f[2]) for f in fallos] + [0.0]),
                'lista': fallos[:80]}

    # --- (o) caidas en la escapatoria: del borde hacia fuera a 30/60/90 grados, siguiendo el suelo cada 0.25 m
    # hasta el primer 1WALL_ (0.3 / 0.6 m) o 8 m: bajadas de > 0.5 m entre dos puntos (canto: el coche cae)
    def caidas_escapatoria(self, ds=2.0, paso=0.25, e_max=8.0, umbral=0.5):
        P = self.P
        out = []
        for k in range(int(P.L / ds)):
            s = k * ds
            q = P.marco(s)
            h = q['w'] / 2.0
            tx, ty = q['ny'], -q['nx']
            for side in (1, -1):
                for ang in (30.0, 60.0, 90.0):
                    a = math.radians(ang)
                    dx = tx * math.cos(a) + side * q['nx'] * math.sin(a)
                    dy = ty * math.cos(a) + side * q['ny'] * math.sin(a)
                    x, y, zr = P.punto(q, side * (h - 0.3))
                    g = self.suelo(x, y, zr, 0.8, 1.5)
                    if g is None:
                        continue
                    z = g[0]
                    d = 0.0
                    while d < e_max:
                        if any(self.rayo(self.b_muro, self.o_muro, self.muros, (x, y, z + hh), (dx, dy, 0.0), paso)
                               for hh in (0.3, 0.6)):
                            break
                        x, y, d = x + dx * paso, y + dy * paso, d + paso
                        st, zn, nn = self.seguir(x, y, z, 0.6, 60.0)
                        if st == 'talud':
                            break
                        if zn is None or z - zn > umbral:
                            # voladizo: si a 1.2 m por delante hay muro, el coche apoya en el antes de caer
                            if not any(self.rayo(self.b_muro, self.o_muro, self.muros, (x, y, z + hh), (dx, dy, 0.0),
                                                 1.2) for hh in (0.3, 0.6)):
                                out.append((s, side, ang, round(d, 2), None if zn is None else round(zn - z, 2),
                                            fam(nn or '')))
                            break
                        z = zn
        return {'n': len(out), 'tramos': rangos(out, junta=4.0)[:60], 'lista': out[:120]}

    # --- (p) ATAJOS y ESCAPES: coches de 1.8 m que salen del borde y siguen recto por el suelo fisico
    def atajos(self, ds=2.0, paso=0.5, dmax=70.0, ds_atajo=60.0, gan_atajo=5.0, e_escapa=12.0):
        """Desde cada borde cada `ds` m, coches rectos a 15..90 grados hacia fuera (y 30/60 marcha atras), 5 rayos a lo
        ancho (+-0.9 m) x 0.3/0.6/1.0 m sobre el suelo fisico, cada `paso` m siguiendo el suelo, hasta un 1WALL_, un
        talud (> 0.6 m en `paso`) o `dmax` m. Por EXCURSION (desde el ultimo punto sobre el asfalto hasta que vuelve):
          atajo  vuelve al asfalto a > ds_atajo m de pista de donde lo dejo, con todo el coche fuera (> 1 m del borde)
                 y ahorrandose >= gan_atajo m (un coche) frente a la pista, o a otro tramo a > 200 m: pasa por la hierba
                 de un ramal a otro (horquillas) o corta una curva cerrada por dentro;
          cuerda lo mismo sin ganar un coche de largo (por la escapatoria de una curva abierta): informativo;
          pit    la excursion pasa por el pit lane o su cuna (es circuito): informativo;
          escapa a > e_escapa m del borde mas cercano fuera de la zona del pit, o cae sin muro: el coche sale."""
        P, V = self.P, self.V
        ofs = (-0.9, -0.45, 0.0, 0.45, 0.9)
        zona_pit = ('1PIT_', '2GRASS_arcen_pit', '2GRASS_cuna')

        def choque(x, y, z, x2, y2, z2, px, py):
            for o in ofs:
                for hh in (0.3, 0.6, 1.0):
                    a = V((x + px * o, y + py * o, z + hh))
                    b = V((x2 + px * o, y2 + py * o, z2 + hh))
                    v = b - a
                    if v.length > 1e-6 and self.b_muro.ray_cast(a, v.normalized(), v.length)[0] is not None:
                        return True
            return False

        def dist_s(a, b):
            d = abs(a - b) % P.L
            return min(d, P.L - d)
        atj, info, esc, n = [], [], [], 0
        for k in range(int(P.L / ds)):
            s = k * ds
            q = P.marco(s)
            h = q['w'] / 2.0
            tx, ty = q['ny'], -q['nx']
            for side in (1, -1):
                for ang, atras in ((15, False), (30, False), (45, False), (60, False), (75, False), (90, False),
                                   (30, True), (60, True)):
                    n += 1
                    a = math.radians(ang)
                    f = -1.0 if atras else 1.0
                    dx = f * tx * math.cos(a) + side * q['nx'] * math.sin(a)
                    dy = f * ty * math.cos(a) + side * q['ny'] * math.sin(a)
                    px, py = -dy, dx
                    x, y, zr = P.punto(q, side * (h - 0.3))
                    g = self.suelo(x, y, zr, 0.8, 1.5)
                    if g is None:
                        continue
                    zg = g[0]
                    s_sal, fuera, emx, d_sal, por_pit = s, False, -9.0, 0.0, False
                    d = 0.0
                    while d < dmax:
                        nx_, ny_ = x + dx * paso, y + dy * paso
                        st, zn, nom = self.seguir(nx_, ny_, zg, 0.6, 1.0)
                        zn_ef = zn if (st == 'ok' and zn is not None) else zg
                        if choque(x, y, zg, nx_, ny_, zn_ef, px, py):
                            break
                        if st == 'talud':
                            break
                        if st == 'cae':
                            if not choque(nx_, ny_, zg, nx_ + dx * 1.2, ny_ + dy * 1.2, zg, px, py):
                                esc.append((s, side, ang, atras, 'cae', round(d, 1), fam(nom or '')))
                            break
                        d += paso
                        s2, u2, _t, q2 = lateral(P, self.kd, nx_, ny_)
                        e = abs(u2) - q2['w'] / 2.0
                        en_pit = (nom or '').startswith(zona_pit)
                        if e > e_escapa and not en_pit:
                            esc.append((s, side, ang, atras, 'escapa', round(d, 1), fam(nom or ''), round(e, 1)))
                            break
                        if e < -0.5:
                            dss = dist_s(s2, s_sal)
                            if fuera and emx > 1.0 and dss > ds_atajo:
                                gan = dss - (d - d_sal)
                                reg = (s, side, ang, atras, round(s_sal, 1), round(s2, 1), round(dss, 1), round(gan, 1),
                                       round(emx, 2))
                                if por_pit:
                                    info.append(reg + ('pit',))
                                elif gan >= gan_atajo or dss > 200.0:
                                    atj.append(reg)
                                    break
                                else:
                                    info.append(reg + ('cuerda',))
                            s_sal, fuera, emx, d_sal, por_pit = s2, False, -9.0, d, False
                        else:
                            fuera = True
                            emx = max(emx, e)
                            por_pit = por_pit or en_pit
                        x, y, zg = nx_, ny_, zn
        return {'n_coches': n, 'n_atajos': len(atj), 'atajos': atj[:80], 'n_escapes': len(esc), 'escapes': esc[:80],
                'n_cuerdas_info': sum(1 for i in info if i[-1] == 'cuerda'),
                'n_pit_info': sum(1 for i in info if i[-1] == 'pit'),
                'info': sorted(info, key=lambda i: -i[7])[:40],
                'campos': '(s, lado, rumbo, marcha_atras, s_deja, s_llega, ds, ganancia_m, e_max[, tipo])'}

    def analizar_lineas(self, lineas, ds, marchar):
        evs, n_huecos, huecos, n_muro, perfiles = [], 0, [], 0, {}
        for nom, extra, pts in lineas:
            zs, noms, nm, hu = self.perfil(pts, ds, marchar)
            n_muro += nm
            n_huecos += len(hu)
            huecos += [dict(linea=nom, x=h[0], y=h[1], pos=h[2]) for h in hu[:20]]
            for e in self.eventos(zs, noms, pts, ds):
                e['linea'] = nom
                if extra is not None:
                    e['ref'] = extra
                # fallo = en la calzada, el pit lane o la cuna (con pit/pista en la ventana); el resto es
                # escapatoria de hierba/terreno (informativo)
                e['fallo'] = any(f.startswith(('1PIT', '1ROAD_pista', '1DIRT_ladera', '1KERB'))
                                 for f in e['superficies'])
                evs.append(e)
            perfiles[nom] = [None if z is None else round(z, 3) for z in zs]
        return evs, n_huecos, huecos, n_muro, perfiles


def cuenta_eventos(evs, con_kerb=True, solo_fallo=False):
    c = {'escalon': 0, 'pendiente': 0}
    for e in evs:
        if (con_kerb or not e['kerb']) and (not solo_fallo or e.get('fallo', True)):
            c[e['tipo']] += 1
    return c


def rangos(lista, junta=2.0):
    """[(s, lado, ...)] -> tramos [[lado, s0, s1, n]] (puntos a <= junta m se unen)."""
    out = []
    for side in (1, -1):
        ss = sorted(set(x[0] for x in lista if x[1] == side))
        for s in ss:
            if out and out[-1][0] == side and s - out[-1][2] <= junta:
                out[-1][2] = s
                out[-1][3] += 1
            else:
                out.append([side, s, s, 1])
    return out


def mediana(v):
    v = sorted(v)
    return round(v[len(v) // 2], 2) if v else None


def main():
    import bpy
    import numpy as np
    from mathutils import Vector, kdtree
    from mathutils.bvhtree import BVHTree
    t0 = time.time()
    blend = os.environ.get('BLEND') or BASE + r'\04_export\_fisica\escena_ac.blend'
    geom = os.environ.get('GEOM') or BASE + r'\03_blender\_rev\geometria_rev.json'
    out = os.environ.get('OUT') or os.path.splitext(blend)[0] + '_fisica.json'
    bpy.ops.wm.open_mainfile(filepath=blend)
    G = json.load(open(geom, encoding='utf-8'))
    I = Inspector(bpy, np, Vector, BVHTree, kdtree, G)
    P = I.P
    inf = {'blend': blend, 'geom': geom, 'generado': time.strftime('%Y-%m-%d %H:%M:%S')}
    inf.update(I.inf)
    # (a) (b) (d) (f)
    res, invas, falsos, espaldas, delante = I.barreras()
    n = len(res[1])
    huecos = []
    for side in (1, -1):
        flags = [r is None for r in res[side]]
        for t in tramos(flags, DS_BARRERA, lambda k: k * DS_BARRERA):
            t['lado'] = side
            t['sec'] = P.marco(t['s0'])['sec']
            huecos.append(t)
    # un hueco que cruza la meta (final + principio) es uno solo
    for side in (1, -1):
        hs = [h for h in huecos if h['lado'] == side]
        a = [h for h in hs if h['k0'] == 0]
        b = [h for h in hs if h['k1'] == n - 1]
        if a and b and a[0] is not b[0]:
            b[0]['largo'] = round(b[0]['largo'] + a[0]['largo'], 1)
            b[0]['s1'] = a[0]['s1']
            huecos.remove(a[0])
    huecos.sort(key=lambda h: -h['largo'])
    dist = {}
    por_sec = {}
    for side in (1, -1):
        ds_ = [r[0] for r in res[side] if r]
        dist[side] = {'mediana': mediana(ds_), 'p10': (sorted(ds_)[len(ds_) // 10] if ds_ else None),
                      'p90': (sorted(ds_)[9 * len(ds_) // 10] if ds_ else None)}
        for k, r in enumerate(res[side]):
            sec = P.marco(k * DS_BARRERA)['sec']
            e = por_sec.setdefault('%s_%+d' % (sec, side), {'muestras': 0, 'con_barrera': 0, 'd': []})
            e['muestras'] += 1
            if r:
                e['con_barrera'] += 1
                e['d'].append(r[0])
    for e in por_sec.values():
        e['d_mediana'] = mediana(e.pop('d'))
    quien = {}
    for side in (1, -1):
        for r in res[side]:
            if r:
                quien[r[1]] = quien.get(r[1], 0) + 1
    por_nombre = {}
    for ob in I.objs:
        if ob.name.startswith(FAMILIAS_BARRERA) and I.cerca(ob, 20.0):
            por_nombre[fam(ob.name)] = por_nombre.get(fam(ob.name), 0) + 1
    falsos_m = {f: round(len(v) * DS_BARRERA / len(H_RAYOS), 1) for f, v in falsos.items()}
    falsos_barr = {f: m for f, m in falsos_m.items() if f.startswith(FAMILIAS_BARRERA)}
    esp_m = {f: round(len(v) * DS_BARRERA / 3.0, 1) for f, v in espaldas.items()}
    inf['barreras'] = {
        'n_muestras_por_lado': n, 'paso_m': DS_BARRERA,
        'n_huecos': len(huecos), 'n_huecos_mayor_2m': sum(1 for h in huecos if h['largo'] > 2.0),
        'm_hueco_total': round(sum(h['largo'] for h in huecos), 1), 'huecos': huecos[:300],
        'distancia_tipica': dist, 'por_sector_lado': por_sec,
        'barrera_mas_cercana_por_familia_muestras': dict(sorted(quien.items(), key=lambda kv: -kv[1])),
        # para el mapa: distancia a la barrera cada 2 m (o -1 = hueco)
        'd_cada_2m': {str(side): [(-1 if res[side][k] is None else res[side][k][0]) for k in range(0, n, 4)]
                      for side in (1, -1)}}
    inf['barreras_falsas'] = {'por_nombre_cerca_de_pista': por_nombre, 'por_rayo_m': falsos_m,
                              'por_rayo_familia_barrera_m': falsos_barr,
                              'n': len(por_nombre) + len(falsos_barr),
                              'ejemplos': {f: v[:6] for f, v in falsos.items()},
                              'tramos': {f: rangos(v)[:60] for f, v in falsos.items()}}
    inf['muros_en_asfalto'] = {'n_muestras': len(invas), 'max_m': max([i['invade_m'] for i in invas], default=0.0),
                               'por_objeto': {}, 'lista': invas[:200]}
    for i_ in invas:
        f = fam(i_['objeto'])
        inf['muros_en_asfalto']['por_objeto'][f] = inf['muros_en_asfalto']['por_objeto'].get(f, 0) + 1
    inf['caras_espaldas'] = {'m_por_familia': dict(sorted(esp_m.items(), key=lambda kv: -kv[1])),
                             'delante_muestras_por_familia': dict(sorted(delante.items(), key=lambda kv: -kv[1])[:40]),
                             'ejemplos': {f: v[:6] for f, v in espaldas.items()},
                             'tramos': {f: rangos(v)[:60] for f, v in espaldas.items()}}
    print('barreras: %d huecos (%d > 2 m, %.0f m) | falsas %s | muros en asfalto %d | espaldas %s [%.0fs]' % (
        len(huecos), inf['barreras']['n_huecos_mayor_2m'], inf['barreras']['m_hueco_total'], falsos_barr,
        len(invas), esp_m, time.time() - t0))
    _superficie(I, bpy, inf, t0)
    # (g) rejilla del pit lane, (h) muros a lo largo del pit lane, (i) visibles delante del cierre, (j) hoyos
    rej = I.pit_rejilla()
    mpl = I.pit_muros_largo()
    vac = I.visuales_ante_cierre()
    hoy = I.terreno_hoyos()
    inf['pit_rejilla'] = rej
    inf['pit_muros_largo'] = mpl
    inf['visuales_ante_cierre'] = vac
    inf['terreno_hoyos'] = hoy
    r = inf['resumen']
    r['pit_rejilla_fallos'] = rej['fallos']
    r['pit_rejilla_n_fallos'] = rej['n_fallos']
    r['pit_muros_largo'] = mpl['por_objeto']
    r['visuales_ante_cierre'] = {f: v['n'] for f, v in vac['familias'].items()}
    r['visuales_ante_cierre_n'] = vac['n_objetos']
    r['terreno_hoyos_visibles'] = [hoy['n_puntos'], hoy.get('prof_max', 0.0)]
    print('pit rejilla: %d puntos, fallos %s | muros a lo largo del pit %s | visibles ante el cierre %d %s | '
          'hoyos de terreno visibles %s [%.0fs]' % (rej['n_puntos'], rej['fallos'], mpl['por_objeto'], vac['n_objetos'],
                                                    r['visuales_ante_cierre'], r['terreno_hoyos_visibles'],
                                                    time.time() - t0))
    # (k) rodadas de los garajes, (l) rejilla delante de las puertas, (m) invisibles sobre lo visible, (n) borde fino
    # de la calzada en el pit, (o) caidas en la escapatoria
    rod = I.rodadas_garajes(bpy)
    rgj = I.garajes_rejilla(bpy)
    ivs = I.invisibles_sobre_visible()
    bfp = I.borde_fino_pit()
    cai = I.caidas_escapatoria()
    inf.update({'garajes_rodadas': rod, 'garajes_rejilla': rgj, 'invisibles_sobre_visible': ivs,
                'borde_fino_pit': bfp, 'caidas_escapatoria': cai})
    r['garajes_rodadas_fallos'] = rod['n_fallos']
    r['garajes_rodadas_peor_m'] = max(list(rod['peor_salto_m'].values()) + [0.0])
    r['garajes_rejilla_fallos'] = rgj['n_fallos']
    r['invisibles_sobre_visible_3cm'] = ivs['n']
    r['borde_fino_pit_fallos'] = [bfp['n_fallos'], bfp.get('max_m', 0.0)]
    r['caidas_escapatoria'] = cai['n']
    print('garajes: rodadas %d fallos (peor %.3f m), rejilla %d | invisibles > 3 cm sobre lo visible %d | borde fino '
          'del pit %s (kerb %s) | caidas en la escapatoria %d %s [%.0fs]' % (
              rod['n_fallos'], r['garajes_rodadas_peor_m'], rgj['n_fallos'], ivs['n'], r['borde_fino_pit_fallos'],
              bfp.get('n_kerb'), cai['n'], cai['tramos'][:6], time.time() - t0))
    # (p) atajos de un ramal a otro / curvas cortadas por dentro y escapes
    atj = I.atajos()
    inf['atajos'] = atj
    r['atajos'] = atj['n_atajos']
    r['escapes'] = atj['n_escapes']
    r['atajos_info_cuerdas_pit'] = [atj['n_cuerdas_info'], atj['n_pit_info']]
    print('atajos: %d coches, %d atajos %s | %d escapes %s | info: %d cuerdas sin ganar un coche, %d por el pit lane '
          '[%.0fs]' % (atj['n_coches'], atj['n_atajos'], atj['atajos'][:6], atj['n_escapes'], atj['escapes'][:6],
                       atj['n_cuerdas_info'], atj['n_pit_info'], time.time() - t0))
    # objetos de cierre (para el mapa): vertices XY cada ~2 m
    cierre = []
    for ob in I.muros:
        if es_invisible(ob.name):
            vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
            cierre.append({'nombre': ob.name, 'xy': [(round(v.x, 1), round(v.y, 1)) for v in vs[::8]]})
    inf['cierre'] = cierre
    json.dump(inf, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('RESUMEN', json.dumps(inf['resumen'], ensure_ascii=False, indent=1))
    print('OK informe -> %s [%.0fs]' % (out, time.time() - t0))


def _superficie(I, bpy, inf, t0):
    """(c) perfiles y (e) huecos / superficies ajenas; rellena inf['superficie'] e inf['resumen']."""
    sup = {}
    # pista: eje, cuartos y bordes
    lp = I.lineas_pista()
    evs_p, hu_p, aj = [], [], {}
    n_hu_p = 0
    for nom, pts in lp.items():
        zs, noms, _nm, hu = I.perfil(pts, DS_PERFIL, False)
        n_hu_p += len(hu)
        hu_p += [dict(linea=nom, x=h[0], y=h[1], s=h[2]) for h in hu[:30]]
        for e in I.eventos(zs, noms, pts, DS_PERFIL):
            e['linea'] = nom
            evs_p.append(e)
        for s, nm, dz in I.ajenas(pts, noms, zs):
            a = aj.setdefault(fam(nm), {'m': 0.0, 'dz_max': 0.0, 's': []})
            a['m'] += DS_PERFIL
            a['dz_max'] = max(a['dz_max'], round(dz, 3))
            if not a['s'] or s - a['s'][-1] > 5.0:
                a['s'].append(round(s, 1))
    for a in aj.values():
        a['m'] = round(a['m'], 1)
        a['s'] = a['s'][:40]
    sup['pista'] = {'eventos': cuenta_eventos(evs_p), 'eventos_sin_kerb': cuenta_eventos(evs_p, False),
                    'lista': sorted(evs_p, key=lambda e: -abs(e['valor']))[:250], 'n_huecos': n_hu_p,
                    'huecos': hu_p[:100], 'ajenas_sobre_asfalto': aj}
    print('superficie pista: %s (sin kerb %s), huecos %d, ajenas %s [%.0fs]' % (
        sup['pista']['eventos'], sup['pista']['eventos_sin_kerb'], n_hu_p,
        {k: (v['m'], v['dz_max']) for k, v in aj.items()}, time.time() - t0))
    # pit: eje, transversales, longitudinales, garajes (marchando: siguen rampas fuera del plano)
    perf = {}
    tot_pit = {'escalon': 0, 'pendiente': 0}
    tot_fallo = {'escalon': 0, 'pendiente': 0}
    for clave, lineas in I.lineas_pit(bpy).items():
        evs, nh, hus, nm, perfiles = I.analizar_lineas(lineas, DS_PERFIL, True)
        c = cuenta_eventos(evs)
        for k in c:
            tot_pit[k] += c[k]
        cf = cuenta_eventos(evs, solo_fallo=True)
        for k in cf:
            tot_fallo[k] += cf[k]
        sup[clave] = {'n_lineas': len(lineas), 'eventos': c, 'eventos_sin_kerb': cuenta_eventos(evs, False),
                      'fallos_pit_pista': cf,
                      'n_puntos_bajo_muro': nm, 'n_huecos': nh, 'huecos': hus[:40],
                      'lista': sorted(evs, key=lambda e: -abs(e['valor']))[:200],
                      'fallos_lista': [e for e in evs if e.get('fallo')][:100]}
        if clave in ('pit_eje', 'garajes', 'pit_carriles'):
            perf[clave] = perfiles
        print('superficie %-16s %3d lineas: %s (en pit/pista/cuna %s), huecos %d, bajo muro %d' % (
            clave, len(lineas), c, cf, nh, nm))
    sup['perfiles'] = perf
    inf['superficie'] = sup
    b = inf['barreras']
    inf['resumen'] = {
        'huecos_barrera': b['n_huecos'], 'huecos_barrera_mayor_2m': b['n_huecos_mayor_2m'],
        'm_sin_barrera': b['m_hueco_total'],
        'd_barrera_mediana_izq_der': [b['distancia_tipica'][1]['mediana'], b['distancia_tipica'][-1]['mediana']],
        'barreras_falsas': inf['barreras_falsas']['n'],
        'barreras_falsas_por_nombre': inf['barreras_falsas']['por_nombre_cerca_de_pista'],
        'barreras_falsas_por_rayo_m': inf['barreras_falsas']['por_rayo_familia_barrera_m'],
        'muros_en_asfalto_muestras': inf['muros_en_asfalto']['n_muestras'],
        'muros_en_asfalto_max_m': inf['muros_en_asfalto']['max_m'],
        'caras_espaldas_m': inf['caras_espaldas']['m_por_familia'],
        'pista_escalones_pendientes': sup['pista']['eventos'],
        'pista_escalones_pendientes_sin_kerb': sup['pista']['eventos_sin_kerb'],
        'pista_huecos_suelo': sup['pista']['n_huecos'],
        'pista_ajenas_m': {k: v['m'] for k, v in sup['pista']['ajenas_sobre_asfalto'].items()},
        'pit_escalones_pendientes': tot_pit,
        'pit_fallos_en_pit_pista_cuna': tot_fallo,
        'pit_fallos_por_linea': {k: sup[k]['fallos_pit_pista'] for k in LINEAS_PIT},
        'pit_por_linea': {k: sup[k]['eventos'] for k in LINEAS_PIT},
        'pit_huecos_suelo': sum(sup[k]['n_huecos'] for k in LINEAS_PIT),
        'invisibles': len(inf.get('invisibles', [])),
    }


def mapa(ruta_json, ruta_png=None):
    """PNG con el trazado, huecos de barrera (rojo), barreras falsas (naranja), muros de cierre (azul) y,
    a la derecha, la zona del pit con los escalones / cambios de pendiente (magenta / violeta)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    inf = json.load(open(ruta_json, encoding='utf-8'))
    G = json.load(open(inf['geom'], encoding='utf-8'))
    P = Pista(G)
    ruta_png = ruta_png or os.path.splitext(ruta_json)[0] + '.png'
    fig, axs = plt.subplots(1, 2, figsize=(22, 11), gridspec_kw={'width_ratios': [1.25, 1]})
    xs = [q['x'] for q in P.S] + [P.S[0]['x']]
    ys = [q['y'] for q in P.S] + [P.S[0]['y']]
    pit = G.get('pit_lane') or []
    for ax in axs:
        ax.plot(xs, ys, color='0.55', lw=1.2, zorder=1)
        if pit:
            ax.plot([p['x'] for p in pit], [p['y'] for p in pit], color='0.3', lw=1.0, ls='--', zorder=1)
        for c in inf.get('cierre', []):
            if c['xy']:
                ax.scatter([p[0] for p in c['xy']], [p[1] for p in c['xy']], s=1.0, color='tab:blue', zorder=2)
        for h in inf['barreras']['huecos']:
            pts = []
            s = h['s0']
            while True:
                q = P.marco(s)
                x, y, _z = P.punto(q, h['lado'] * (q['w'] / 2.0 + 1.5))
                pts.append((x, y))
                if abs(((s - h['s1']) % P.L)) < 0.3 or len(pts) > 4000:
                    break
                s = (s + 0.5) % P.L
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color='red', lw=3.0 if h['largo'] > 2 else 1.5, zorder=4)
        for f, ej in inf['barreras_falsas']['ejemplos'].items():
            for (s, side, d) in ej:
                q = P.marco(s)
                x, y, _z = P.punto(q, side * (q['w'] / 2.0 + d))
                ax.scatter([x], [y], s=12, color='orange', zorder=5)
        for clave, col in (('pit_eje', 'magenta'), ('pit_transversal', 'magenta'), ('pit_longitudinal', 'purple'),
                           ('garajes', 'green'), ('pista', 'black')):
            for e in inf['superficie'].get(clave, {}).get('lista', []):
                if clave == 'pista' and e.get('kerb'):
                    continue
                if clave != 'pista' and not e.get('fallo', True):
                    ax.scatter([e['x']], [e['y']], s=4, color='0.75', zorder=3)      # escapatoria de hierba
                    continue
                ax.scatter([e['x']], [e['y']], s=10 + 300 * min(0.3, abs(e['valor'])), color=col,
                           marker='x' if e['tipo'] == 'escalon' else 'o', zorder=6)
        ax.set_aspect('equal')
    r = inf['resumen']
    axs[0].set_title('Porto Corsa - fisica AC: huecos de barrera %d (%d > 2 m, %.0f m), falsas %d, cierre (azul)'
                     % (r['huecos_barrera'], r['huecos_barrera_mayor_2m'], r['m_sin_barrera'], r['barreras_falsas']))
    # zoom del pit: s L-220 .. 220
    zx = [P.marco(s)['x'] for s in range(-220, 221, 10)]
    zy = [P.marco(s)['y'] for s in range(-220, 221, 10)]
    axs[1].set_xlim(min(zx) - 40, max(zx) + 40)
    axs[1].set_ylim(min(zy) - 40, max(zy) + 40)
    axs[1].set_title('pit lane: escalones x / pendiente o en pit/pista/cuna %s (gris: hierba)'
                     % r.get('pit_fallos_en_pit_pista_cuna', r['pit_escalones_pendientes']))
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=110)
    print('mapa ->', ruta_png)


if __name__ == '__main__':
    if '--mapa' in sys.argv:
        k = sys.argv.index('--mapa')
        mapa(sys.argv[k + 1], sys.argv[k + 2] if len(sys.argv) > k + 2 else None)
    else:
        main()
