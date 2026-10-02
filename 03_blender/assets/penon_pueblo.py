"""penon_pueblo.py - ROCA-PUEBLO de Porto Corsa (Cars 2) para Blender 5.1.

Una roca-meseta con la planta que se le pida (contorno en coordenadas de mundo)
por la que sube una CARRETERA EN ESPIRAL: la roca es una helice de repisas
(terrazas) que dan una vuelta completa cada `H` metros de altura; en cada
repisa va la carretera (por el borde exterior, con su parapeto de piedra) y,
pegados al paredon de detras, los solares de las casas (la parte trasera de
cada casa queda dentro de la roca, como en Cinque Terre). Escaleras de piedra
adosadas al paredon comunican una terraza con la siguiente. Arriba, la PLAZA
(meseta) delimitada por la ultima vuelta de la carretera, con parapeto.

API:
  build_desde_contorno(parent_collection, contorno, altura=80.0, z_base=-5.0,
                       n_terrazas=4, seed=0, entrada_xy=None, **params)
      contorno: [(x, y), ...] en mundo, orientado en cualquier sentido.
      altura: de z_base a la plaza. n_terrazas: MAXIMO de vueltas (se ajusta
      por tamano y pendiente: repisa >= 6 m, pendiente <= ~10%).
      entrada_xy: donde arranca la carretera (punto del contorno mas cercano).
      -> (raiz Empty 'PPUEBLO_root', info)
         hijos: PPUEBLO_roca (malla cerrada, taladrable), PPUEBLO_carretera,
                PPUEBLO_muro (parapetos), PPUEBLO_escaleras, PPUEBLO_plaza.
         info: {'plazas_casas': [{'x','y','z','rot_z','ancho_max','fondo_max',
                                  'alto_max'}], 'z_top', 'centro_top',
                'entrada': (x, y, z), 'muestras_carretera': [(x, y, z), ...],
                'n_terrazas', 'ancho_repisa', 'ancho_carretera', 'H'}
         La raiz tambien guarda info en raiz['casas'] (JSON).
  build(parent_collection, seed=0, **params): escaparate (elipse 60x40 m).

Convenciones: metros; la malla lleva las coordenadas de mundo (la raiz va en
el origen, sin rotar). Materiales MAT_PPUEBLO_*. Sin bpy.ops.
"""
import json
import math
import random

import bpy
from mathutils import Vector

try:
    from mathutils import noise as _mnoise

    def _ruido(x, y, z):
        return _mnoise.noise(Vector((x, y, z)))
except Exception:  # pragma: no cover
    def _ruido(x, y, z):
        return math.sin(x * 1.7 + y * 0.9) * math.cos(z * 1.3 + x * 0.4) * 0.5


# ----------------------------------------------------------------- materiales
_PALETA = {
    'roca':        ((0.40, 0.36, 0.29), 0.95),
    'roca_clara':  ((0.47, 0.43, 0.35), 0.95),
    'roca_oscura': ((0.31, 0.28, 0.23), 0.96),
    'repisa':      ((0.36, 0.33, 0.25), 0.95),
    'carretera':   ((0.21, 0.21, 0.22), 0.90),
    'borde':       ((0.86, 0.84, 0.78), 0.70),
    'muro':        ((0.80, 0.74, 0.60), 0.85),
    'escalera':    ((0.70, 0.64, 0.52), 0.85),
    'plaza':       ((0.70, 0.63, 0.50), 0.80),
    'plaza_dibujo': ((0.64, 0.57, 0.45), 0.80),
    'mata':        ((0.07, 0.22, 0.06), 0.92),
    'mata_clara':  ((0.14, 0.34, 0.10), 0.92),
}


def _mat(clave):
    nombre = 'MAT_PPUEBLO_' + clave
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    if bs is not None:
        bs.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
        bs.inputs['Roughness'].default_value = rough
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


class _Malla:
    """Acumulador de vertices/caras con indice de material por cara."""

    def __init__(self, nombre, claves):
        self.nombre = nombre
        self.v = []
        self.f = []
        self.mi = []
        self.claves = list(claves)

    def vert(self, p):
        self.v.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.v) - 1

    def cara(self, idx, clave):
        idx = [i for k, i in enumerate(idx) if i != idx[k - 1]]
        if len(idx) < 3:
            return
        self.f.append(tuple(idx))
        self.mi.append(self.claves.index(clave))

    def objeto(self, parent_collection, parent_obj=None, recalc=True):
        me = bpy.data.meshes.new(self.nombre)
        me.from_pydata(self.v, [], self.f)
        for clave in self.claves:
            me.materials.append(_mat(clave))
        for p, mi in zip(me.polygons, self.mi):
            p.material_index = mi
        me.validate(verbose=False)
        me.update()
        if recalc:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
            me.update()
        ob = bpy.data.objects.new(self.nombre, me)
        parent_collection.objects.link(ob)
        if parent_obj is not None:
            ob.parent = parent_obj
        return ob


# ----------------------------------------------------------------- contorno
def _resamplear(contorno, paso_obj):
    """Contorno cerrado -> M puntos equiespaciados (antihorario)."""
    pts = [(float(p[0]), float(p[1])) for p in contorno]
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:
        pts = pts[:-1]
    area = 0.0
    for k in range(len(pts)):
        x0, y0 = pts[k]
        x1, y1 = pts[(k + 1) % len(pts)]
        area += x0 * y1 - x1 * y0
    if area < 0:
        pts = pts[::-1]
    per = 0.0
    tramos = []
    for k in range(len(pts)):
        x0, y0 = pts[k]
        x1, y1 = pts[(k + 1) % len(pts)]
        l_ = math.hypot(x1 - x0, y1 - y0)
        tramos.append(l_)
        per += l_
    M = max(48, int(round(per / paso_obj)))
    out = []
    k = 0
    acum = 0.0
    for j in range(M):
        s = per * j / M
        while k < len(pts) - 1 and acum + tramos[k] < s:
            acum += tramos[k]
            k += 1
        f = (s - acum) / tramos[k] if tramos[k] > 1e-9 else 0.0
        x0, y0 = pts[k]
        x1, y1 = pts[(k + 1) % len(pts)]
        out.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
    return out, per


def _suavizar_cerrado(pts, pasadas=2):
    n = len(pts)
    for _ in range(pasadas):
        pts = [((pts[(i - 1) % n][0] + 2 * pts[i][0] + pts[(i + 1) % n][0]) / 4.0,
                (pts[(i - 1) % n][1] + 2 * pts[i][1] + pts[(i + 1) % n][1]) / 4.0) for i in range(n)]
    return pts


# ----------------------------------------------------------------- la helice
class _Helice:
    """Parametrizacion de la roca: t = vuelta continua (t in [-1, n]); u = t mod 1
    recorre el contorno; todo punto se define por (indice de contorno, desplazamiento
    hacia dentro `o` en metros, cota z)."""

    def __init__(self, pts, per, centro, altura, z_base, n, paso, lw, rw, prof, seed):
        self.pts = pts
        self.M = len(pts)
        self.per = per
        self.cx, self.cy = centro
        self.altura = altura
        self.zb = z_base
        self.n = n
        self.paso = paso        # avance hacia dentro por vuelta (repisa + talud)
        self.lw = lw            # ancho de la repisa (carretera + franja de casas)
        self.rw = rw            # ancho de la carretera
        self.prof = prof        # falda bajo z_base
        self.H = altura / float(n)
        self.seed = seed
        self.dirs = []
        self.rad = []
        for (x, y) in pts:
            dx, dy = self.cx - x, self.cy - y
            r = math.hypot(dx, dy) or 1.0
            self.dirs.append((dx / r, dy / r))
            self.rad.append(r)
        self.z_top = z_base + altura

    # --- cotas y desplazamientos -------------------------------------------------
    def z(self, t):
        if t < 0:
            return self.zb - self.prof
        u_e = getattr(self, 'u_entrada', 0.0)
        if u_e > 0 and t < u_e:
            # rampa de entrada: la carretera arranca enterrada (z_entrada) y sube a la helice
            f = t / u_e
            return self.z_entrada + (self.zb + self.H * u_e - self.z_entrada) * (3 * f * f - 2 * f * f * f)
        return self.zb + self.H * min(t, self.n)

    def o_out(self, t):
        return max(0.0, t) * self.paso

    def punto(self, i, o, z):
        x, y = self.pts[i % self.M]
        dx, dy = self.dirs[i % self.M]
        return (x + dx * o, y + dy * o, z)

    def xy(self, u, o):
        """posicion (interpolada) a la fraccion u de la vuelta y desplazamiento o."""
        f = (u % 1.0) * self.M
        i = int(f)
        g = f - i
        x0, y0, _ = self.punto(i, o, 0.0)
        x1, y1, _ = self.punto(i + 1, o, 0.0)
        return (x0 + (x1 - x0) * g, y0 + (y1 - y0) * g)

    def dir_fuera(self, u):
        f = (u % 1.0) * self.M
        i = int(round(f)) % self.M
        dx, dy = self.dirs[i]
        return (-dx, -dy)

    def bulto(self, i, t):
        """abultamiento del paredon a media altura (>= 0, hacia fuera)."""
        x, y = self.pts[i % self.M]
        v = _ruido(x * 0.035 + self.seed, y * 0.035, t * 1.7)
        v2 = _ruido(x * 0.11 + 3.0, y * 0.11 + self.seed, t * 4.0)
        return max(0.0, 0.9 + 1.2 * v + 0.5 * v2)

    # --- roca ---------------------------------------------------------------------
    def malla_roca(self):
        """Helice de repisas + paredones con BARRIGA y estratos horizontales; la
        falda (t<0) lleva bultos grandes. K sub-anillos por paredon."""
        mr = _Malla('PPUEBLO_roca', ('roca', 'roca_clara', 'roca_oscura', 'repisa'))
        n, M = self.n, self.M
        pasos = int(round((n + 1) * M))       # t de -1 a n
        flare_f = getattr(self, 'flare', 0.3)
        flare_max = getattr(self, 'flare_max', 40.0)
        # sub-anillos por paredon: mas cuantos mas metros (la falda del mar puede tener 100 m)
        K = max(4, min(14, int(round(max(self.H, self.prof + self.H) / 8.0))))
        b_fuera = getattr(self, 'bulto_fuera', 3.5)
        b_pared = getattr(self, 'bulto_pared', 1.2)     # barriga de los paredones SOBRE las repisas (casas delante)
        b_dentro = getattr(self, 'bulto_dentro', 3.0)
        anillos = []
        self.matas = []
        for j in range(pasos + 1):
            t = -1.0 + j / float(M)
            if t > n:
                t = float(n)
            i = j % M
            x_, y_ = self.pts[i]
            zt = self.z(t)
            oo = self.o_out(t)
            oi = oo + (self.lw if t >= 0 else 0.0)
            ot = self.o_out(t + 1.0)
            zt1 = self.z(t + 1.0)
            alto_p = max(zt1 - zt, 0.0)
            # falda (t<0): la base se ensancha hacia fuera como una ladera (proporcional a su altura)
            flare = min(flare_max, flare_f * alto_p) if t < 0 else 0.0
            if t < 0:
                oo = oi = -flare
            v_out = mr.vert(self.punto(i, oo, zt))
            v_in = mr.vert(self.punto(i, oi, zt))
            pared = []
            amp = min(b_dentro, 0.16 * alto_p) if t >= 0 else min(b_dentro * 1.6, 0.12 * alto_p)
            for k in range(1, K):
                f = k / float(K)
                perfil = math.sin(math.pi * f) ** 0.8            # barriga a media altura
                zk = zt + (zt1 - zt) * f
                r0 = _ruido(x_ * 0.006 + self.seed, y_ * 0.006, zk * 0.02)
                r1 = _ruido(x_ * 0.018 + self.seed * 3.1, y_ * 0.018, zk * 0.05)
                r2 = _ruido(x_ * 0.06 + 7.0, y_ * 0.06 + self.seed, zk * 0.15)
                v = max(-1.0, min(1.0, 3.0 * (1.2 * r0 + 1.6 * r1 + 0.7 * r2)))
                if v > 0:
                    desplaz = min(b_fuera if t < 0 else b_pared, amp * 0.55 * v)   # hacia fuera (limitado)
                else:
                    desplaz = max(-amp, amp * 0.9 * v)              # hacia dentro
                if t < 0:
                    ok_ = ot - (ot + flare) * (1.0 - f) ** 1.35 - perfil * desplaz
                else:
                    ok_ = oi + (ot - oi) * f - perfil * desplaz
                pared.append(mr.vert(self.punto(i, ok_, zk)))
                if t >= 0 and 0.25 < f < 0.85 and _ruido(x_ * 0.21 + zk * 0.13, y_ * 0.21, self.seed + 9.0) > 0.42:
                    self.matas.append(self.punto(i, ok_ - 0.6, zk))
            v_top = mr.vert(self.punto(i, ot, zt1))
            anillos.append((v_out, v_in, pared, v_top, t))
        for j in range(pasos):
            a = anillos[j]
            b = anillos[j + 1]
            t = a[4]
            if t >= 0:
                mr.cara((a[0], b[0], b[1], a[1]), 'repisa')
            cadena_a = [a[1]] + a[2] + [a[3]]
            cadena_b = [b[1]] + b[2] + [b[3]]
            zt = self.z(t)
            zt1 = self.z(t + 1.0)
            for k in range(K):
                zk = zt + (zt1 - zt) * (k + 0.5) / K
                ruido_b = _ruido(j * 0.07, self.seed + 2.0, zk * 0.02)
                banda = int((zk + 4.0 * ruido_b) / 7.0)
                if t < 0 and k == 0:
                    clave = 'roca_oscura'
                else:
                    clave = ('roca', 'roca_clara', 'roca', 'roca_oscura', 'roca_clara')[banda % 5]
                mr.cara((cadena_a[k], cadena_b[k], cadena_b[k + 1], cadena_a[k + 1]), clave)
        # tapa inferior (anillo t in [-1, 0)) y tapa superior (cimas de la ultima vuelta)
        c_inf = mr.vert((self.cx, self.cy, self.zb - self.prof))
        for j in range(M):
            mr.cara((c_inf, anillos[j + 1][0], anillos[j][0]), 'roca_oscura')
        c_sup = mr.vert((self.cx, self.cy, self.z_top))
        j0 = pasos - M
        for j in range(j0, pasos):
            mr.cara((c_sup, anillos[j][3], anillos[j + 1][3]), 'repisa')
        # cierre radial de la meseta: de la cima en t=n-1 (u=0) a la cima en t=n (u=1)
        mr.cara((c_sup, anillos[pasos][3], anillos[j0][3]), 'repisa')
        # la repisa final (t=n) queda bajo la meseta: se cierra con la ultima cima
        mr.cara((anillos[pasos][0], anillos[pasos][1], anillos[pasos][3]), 'repisa')
        return mr

    # --- matas verdes colgadas de los paredones (como los acantilados de la peli) ---
    def malla_matas(self, rnd):
        mv = _Malla('PPUEBLO_veg', ('mata', 'mata_clara'))
        # icosaedro low-poly
        phi = (1 + 5 ** 0.5) / 2
        base = [(-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0), (0, -1, phi), (0, 1, phi),
                (0, -1, -phi), (0, 1, -phi), (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)]
        caras = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
                 (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
                 (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
        nrm = 1.0 / (1 + phi * phi) ** 0.5
        n_ = 0
        for (x, y, z) in self.matas[:900]:
            r = rnd.uniform(1.2, 2.6)
            sx, sy, sz = r * rnd.uniform(0.8, 1.3), r * rnd.uniform(0.8, 1.3), r * rnd.uniform(0.6, 0.9)
            i0 = len(mv.v)
            for (bx, by, bz) in base:
                mv.v.append((x + bx * nrm * sx, y + by * nrm * sy, z + bz * nrm * sz))
            clave = 'mata' if n_ % 3 else 'mata_clara'
            for (a_, b_, c_) in caras:
                mv.cara((i0 + a_, i0 + b_, i0 + c_), clave)
            n_ += 1
        return mv

    # --- carretera + parapetos -----------------------------------------------------
    def malla_carretera(self):
        mc = _Malla('PPUEBLO_carretera', ('carretera', 'borde'))
        mm = _Malla('PPUEBLO_muro', ('muro',))
        n, M = self.n, self.M
        pasos = int(round(n * M))
        fila_c, fila_m, muestras = [], [], []
        for j in range(pasos + 1):
            t = min(float(n), j / float(M))
            i = j % M
            zt = self.z(t) + 0.05
            oo = self.o_out(t)
            o_a = oo + 0.5
            o_b = o_a + self.rw
            fila_c.append((mc.vert(self.punto(i, o_a, zt)), mc.vert(self.punto(i, o_a + 0.25, zt)),
                           mc.vert(self.punto(i, o_b - 0.25, zt)), mc.vert(self.punto(i, o_b, zt))))
            xc, yc, _ = self.punto(i, (o_a + o_b) / 2.0, zt)
            muestras.append((xc, yc, zt))
            # parapeto exterior 0.45 x 0.7 m
            zp = self.z(t)
            fila_m.append((mm.vert(self.punto(i, oo, zp - 0.3)), mm.vert(self.punto(i, oo, zp + 0.7)),
                           mm.vert(self.punto(i, oo + 0.45, zp + 0.7)), mm.vert(self.punto(i, oo + 0.45, zp - 0.05))))
        for j in range(pasos):
            a, b = fila_c[j], fila_c[j + 1]
            mc.cara((a[0], b[0], b[1], a[1]), 'borde')
            mc.cara((a[1], b[1], b[2], a[2]), 'carretera')
            mc.cara((a[2], b[2], b[3], a[3]), 'borde')
            a, b = fila_m[j], fila_m[j + 1]
            mm.cara((a[0], b[0], b[1], a[1]), 'muro')
            mm.cara((a[1], b[1], b[2], a[2]), 'muro')
            mm.cara((a[2], b[2], b[3], a[3]), 'muro')
        # parapeto de la plaza (cimas de la ultima vuelta) salvo donde llega la carretera
        fila_p = []
        for j in range(M + 1):
            t = n - 1.0 + j / float(M)
            i = j % M
            ot = self.o_out(t + 1.0)
            if j < M - int(0.05 * M):
                fila_p.append((mm.vert(self.punto(i, ot, self.z_top - 0.3)), mm.vert(self.punto(i, ot, self.z_top + 0.9)),
                               mm.vert(self.punto(i, ot + 0.45, self.z_top + 0.9)), mm.vert(self.punto(i, ot + 0.45, self.z_top - 0.05))))
            else:
                fila_p.append(None)
        for j in range(M):
            a, b = fila_p[j], fila_p[j + 1]
            if a is None or b is None:
                continue
            mm.cara((a[0], b[0], b[1], a[1]), 'muro')
            mm.cara((a[1], b[1], b[2], a[2]), 'muro')
            mm.cara((a[2], b[2], b[3], a[3]), 'muro')
        return mc, mm, muestras

    # --- escaleras -----------------------------------------------------------------
    def malla_escaleras(self, u_escaleras):
        me = _Malla('PPUEBLO_escaleras', ('escalera',))
        n = self.n
        huella, contra, ancho = 0.32, 0.22, 1.6
        ocupadas = []
        for k in range(n):
            for u0 in u_escaleras:
                if k == n - 1 and u0 > 0.6:
                    continue
                # sube en sentido contrario a la carretera (la repisa de arriba baja a su encuentro)
                subida = self.H
                du_total = (subida / contra * huella) / (self.per + subida / contra * huella)
                if du_total > 0.45:
                    continue
                n_pel = int(math.ceil(subida * (1.0 - du_total) / contra))
                t0 = k + u0
                z0 = self.z(t0)
                o_base = self.o_out(t0) + self.lw + 3.2 - ancho
                prev = None
                for p_ in range(n_pel + 1):
                    frac = p_ / float(n_pel)
                    u = u0 - du_total * frac
                    t = k + u
                    zp = z0 + contra * p_
                    zl = self.z(t)              # cota de la repisa ahi (para el costado)
                    o = o_base + (self.paso - self.lw) * frac + self.paso * (t - t0) * 0.0
                    o_in = o + ancho
                    xa, ya = self.xy(u, o)
                    xb, yb = self.xy(u, o_in)
                    cur = (me.vert((xa, ya, zp)), me.vert((xb, yb, zp)), me.vert((xa, ya, zp - 0.6)))
                    if prev is not None:
                        # huella (peldano) + tabica + costado exterior
                        me.cara((prev[0], cur[0], cur[1], prev[1]), 'escalera')
                        me.cara((prev[0], prev[2], cur[2], cur[0]), 'escalera')
                    prev = cur
                ocupadas.append((k, u0 - du_total - 0.01, u0 + 0.01))
        return me, ocupadas

    # --- plaza ---------------------------------------------------------------------
    def malla_plaza(self):
        mp = _Malla('PPUEBLO_plaza', ('plaza', 'plaza_dibujo'))
        n, M = self.n, self.M
        c = mp.vert((self.cx, self.cy, self.z_top + 0.06))
        anillo = []
        for j in range(M + 1):
            t = n - 1.0 + j / float(M)
            ot = self.o_out(t + 1.0) - 0.02
            anillo.append(mp.vert(self.punto(j, ot, self.z_top + 0.06)))
        for j in range(M):
            mp.cara((c, anillo[j], anillo[j + 1]), 'plaza' if (j // 3) % 2 == 0 else 'plaza_dibujo')
        mp.cara((c, anillo[M], anillo[0]), 'plaza')
        return mp

    # --- solares -------------------------------------------------------------------
    def solares(self, ocupadas, rnd, ancho_lote=10.5, ocupacion=1.0):
        lots = []
        libres = []
        n = self.n
        for k in range(n):
            u = max(0.075, getattr(self, 'u_entrada', 0.0) + 0.025) if k == 0 else 0.03
            u_fin = 0.97 if k < n - 1 else 0.90
            while u < u_fin:
                paso_u = (ancho_lote + rnd.uniform(0.8, 2.6)) / self.per
                libre = True
                for (kk, ua, ub) in ocupadas:
                    if kk == k and ua - ancho_lote / self.per / 2 < u < ub + ancho_lote / self.per / 2:
                        libre = False
                        break
                arbolado = False
                if libre and rnd.random() > ocupacion:
                    libre = False
                    arbolado = True
                # repisa demasiado estrecha para una casa entera (fondo < 4.8 m): solo arbolado
                if libre and self.lw - (0.5 + self.rw + 0.6) - 0.3 - getattr(self, 'bulto_pared', 1.2) < 4.8:
                    libre = False
                    arbolado = True
                if libre or arbolado:
                    t = k + u
                    o_front = self.o_out(t) + 0.5 + self.rw + 0.6      # acera de 0.6 m tras la carretera
                    fondo_max = max(3.0, self.lw - (0.5 + self.rw + 0.6) - 0.3 - getattr(self, 'bulto_pared', 1.2))
                    x, y = self.xy(u, o_front)                        # (x, y) = centro de la LINEA DE FACHADA
                    fx, fy = self.dir_fuera(u)
                    lot = {'x': round(x, 3), 'y': round(y, 3), 'z': round(self.z(t), 3),
                           'rot_z': round(math.atan2(fy, fx) - math.pi / 2.0, 4),
                           'ancho_max': round(paso_u * self.per - 0.8, 2), 'fondo_max': round(fondo_max, 2),
                           'alto_max': round(self.H - 1.2, 2), 'terraza': k}
                    if arbolado:
                        xf, yf = self.xy(u, o_front + min(1.5, fondo_max * 0.4))
                        lot['x'], lot['y'] = round(xf, 3), round(yf, 3)
                        libres.append(lot)
                    else:
                        lots.append(lot)
                u += paso_u
        return lots, libres


# ----------------------------------------------------------------- API
def build_desde_contorno(parent_collection, contorno, altura=80.0, z_base=-5.0,
                         n_terrazas=4, seed=0, entrada_xy=None, **params):
    """Roca-pueblo con la planta `contorno`. Ver docstring del modulo."""
    rnd = random.Random(seed)
    pts, per = _resamplear(contorno, params.get('paso_muestreo', 3.0))
    pts = _suavizar_cerrado(pts, params.get('suavizado', 1))
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    # la carretera arranca en el punto del contorno mas cercano a entrada_xy
    if entrada_xy is not None:
        i0 = min(range(len(pts)), key=lambda i: (pts[i][0] - entrada_xy[0]) ** 2 + (pts[i][1] - entrada_xy[1]) ** 2)
        pts = pts[i0:] + pts[:i0]
    if params.get('sentido', 1) < 0:
        pts = [pts[0]] + pts[1:][::-1]
    r_min = min(math.hypot(p[0] - cx, p[1] - cy) for p in pts)
    # vueltas: pendiente de la carretera <= pend_max, repisa >= 6 m, plaza con sitio
    pend_max = params.get('pendiente_max', 0.085)
    n = int(math.ceil(altura / (pend_max * per)))
    n = max(1, min(int(n_terrazas), n))
    lean = params.get('talud', 1.5)
    lw_deseado = params.get('ancho_repisa', 11.5)
    while n > 1:
        paso = min(lw_deseado + lean, 0.92 * r_min / (n + 1.0))
        if paso - lean >= 6.0:
            break
        n -= 1
    paso = min(lw_deseado + lean, 0.92 * r_min / (n + 1.0))
    lw = paso - lean
    rw = max(3.6, min(params.get('ancho_carretera', 6.0), lw - 1.4))
    # si con esas vueltas la repisa no admite casas ENTERAS (fondo >= 4.8 m), una
    # vuelta menos (pendiente hasta el 11%) antes que casas dentro de la roca
    lw_casas = 0.5 + rw + 0.6 + 0.3 + float(params.get('bulto_pared', 1.2)) + 4.8
    while n > 1 and lw < lw_casas and altura / ((n - 1) * per) <= 0.11:
        n -= 1
        paso = min(lw_deseado + lean, 0.92 * r_min / (n + 1.0))
        lw = paso - lean
        rw = max(3.6, min(params.get('ancho_carretera', 6.0), lw - 1.4))
    prof = params.get('profundidad', 14.0)
    h = _Helice(pts, per, (cx, cy), float(altura), float(z_base), n, paso, lw, rw, prof, seed)
    h.bulto_fuera = float(params.get('bulto_fuera', 3.5))
    h.bulto_pared = float(params.get('bulto_pared', 1.2))
    z_ent = params.get('z_entrada')
    if z_ent is not None and float(z_ent) < z_base - 0.5:
        h.z_entrada = float(z_ent)
        h.u_entrada = max(0.04, min(0.2, (z_base + 2.0 - float(z_ent)) / (0.18 * per)))
    else:
        h.z_entrada = float(z_base)
        h.u_entrada = 0.0
    h.flare = float(params.get('flare', 0.3))
    h.flare_max = float(params.get('flare_max', 40.0))
    h.bulto_dentro = float(params.get('bulto_dentro', 3.0))

    raiz = bpy.data.objects.new('PPUEBLO_root', None)
    raiz.empty_display_size = 2.0
    parent_collection.objects.link(raiz)
    roca = h.malla_roca().objeto(parent_collection, raiz, recalc=True)
    mc, mm, muestras = h.malla_carretera()
    mc.objeto(parent_collection, raiz, recalc=False)
    mm.objeto(parent_collection, raiz, recalc=False)
    me, ocupadas = h.malla_escaleras(params.get('u_escaleras', (0.36, 0.72)))
    if me.f:
        me.objeto(parent_collection, raiz, recalc=False)
    h.malla_plaza().objeto(parent_collection, raiz, recalc=False)
    mv = h.malla_matas(rnd)
    if mv.f:
        mv.objeto(parent_collection, raiz, recalc=False)
    lots, libres = h.solares(ocupadas, rnd, ancho_lote=params.get('ancho_lote', 10.5), ocupacion=params.get('ocupacion', 1.0))
    # pendiente real de la carretera
    pend = h.H / per
    ex, ey = h.xy(0.0, 0.5 + rw / 2.0)
    info = {
        'plazas_casas': lots,
        'plazas_libres': libres,
        'z_top': round(h.z_top, 3),
        'centro_top': (round(cx, 3), round(cy, 3)),
        'entrada': (round(ex, 3), round(ey, 3), round(z_base, 3)),
        'muestras_carretera': [(round(a, 2), round(b, 2), round(c, 2)) for (a, b, c) in muestras],
        'n_terrazas': n, 'ancho_repisa': round(lw, 2), 'ancho_carretera': round(rw, 2),
        'H': round(h.H, 2), 'pendiente': round(pend, 4), 'perimetro': round(per, 1),
        'r_min': round(r_min, 1),
        'r_top': round(r_min - (n + 1) * paso, 1),
    }
    raiz['casas'] = json.dumps(info)
    print('[penon_pueblo] %d vueltas de %.1f m (pend. %.1f%%), repisa %.1f m, carretera %.1f m, '
          '%d solares, plaza a z=%.1f (r_min %.0f m, perimetro %.0f m)'
          % (n, h.H, pend * 100, lw, rw, len(lots), h.z_top, r_min, per))
    return raiz, info


def build(parent_collection, seed=0, **params):
    """Escaparate: elipse 60x40 m, 55 m de alto."""
    a, b = params.get('semi_a', 60.0), params.get('semi_b', 40.0)
    pts = [(a * math.cos(2 * math.pi * k / 72), b * math.sin(2 * math.pi * k / 72)) for k in range(72)]
    raiz, info = build_desde_contorno(parent_collection, pts, altura=params.get('altura', 55.0),
                                      z_base=params.get('z_base', 0.0), n_terrazas=params.get('n_terrazas', 4),
                                      seed=seed, entrada_xy=(a, 0.0))
    return raiz
