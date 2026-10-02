"""VIADUCTO_CURVO — Viaducto de arcos de piedra que sigue una curva (Porto Corsa, Cars 2).

EL icono de Porto Corsa: la pista cruza el mar sobre puentes de arcos romanos
de caliza ocre-dorada. Este modulo recibe el EJE del tablero como lista de
puntos 3D (la carretera va ENCIMA y ya existe: aqui NO se construye calzada)
y genera bajo el la obra de fabrica siguiendo la curva:

  - pilas rectangulares cada ~14 m que bajan hasta nivel_agua - 4, con
    zocalo oscuro al nivel del agua y TAJAMAR (espolon) a ambos costados,
  - ARCOS de medio punto entre pilas (rebajados automaticamente si el
    tablero va demasiado bajo), con banda clara en el intrados y anillo de
    dovelas insinuadas (tonos alternos + clave resaltada) en ambas caras,
  - muro de timpano continuo entre tablero y arcos,
  - imposta corrida (cornisa) bajo el tablero e
  - balaustrada baja de piedra a ambos lados.

API (ver CONTRATO.md):
  build_desde_puntos(parent_collection, puntos, ancho=13.0, nivel_agua=0.0,
                     seed=0, nombre="tramo", vano_objetivo=14.0)
      puntos = [(x, y, z), ...] eje del tablero en coordenadas de mundo
      (z variable admitido: curvas suaves 3D). La geometria se genera en esas
      mismas coordenadas y cuelga de un Empty raiz en el origen del mundo
      (excepcion documentada a la regla "origen en el centro de la base":
      el asset se ancla al trazado que recibe).
  build(parent_collection, seed=0, **params)
      Muestra: curva en S de 150 m con z variable.

Presupuesto: <= 1500 tris por cada 30 m de viaducto. Sin bpy.ops.
Convenciones: metros; materiales Principled planos con prefijo MAT_VIADUCTO_.
"""

import bisect
import math
import random

import bpy
import bmesh
from mathutils import Vector

PFX = "VIADUCTO"

# ---------------------------------------------------------------- materiales

_PALETA = {
    "piedra":    ((0.590, 0.385, 0.140), 0.93, 0.0),  # caliza ocre-dorada
    "sillar":    ((0.790, 0.565, 0.240), 0.90, 0.0),  # imposta / cornisas
    "intrados":  ((0.870, 0.670, 0.330), 0.88, 0.0),  # banda clara bajo arco
    "dovela_a":  ((0.845, 0.630, 0.280), 0.90, 0.0),
    "dovela_b":  ((0.475, 0.295, 0.095), 0.90, 0.0),
    "clave":     ((0.930, 0.770, 0.410), 0.86, 0.0),
    "zocalo":    ((0.360, 0.250, 0.115), 0.95, 0.0),  # piedra mojada
    "balaustre": ((0.810, 0.615, 0.300), 0.90, 0.0),
}


def _mat(clave):
    nombre = "MAT_%s_%s" % (PFX, clave)
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough, metal = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bsdf = None
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bsdf = n
            break
    if bsdf is None:
        bsdf = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        out = m.node_tree.nodes.get('Material Output')
        if out is not None:
            m.node_tree.links.new(bsdf.outputs[0], out.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    m.diffuse_color = (*color, 1.0)
    return m


# ------------------------------------------------------------------- espina

def _catmull(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return (p1 * 2.0 + (p2 - p0) * t
            + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2
            + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * t3) * 0.5


class _Espina:
    """Polilinea densa (Catmull-Rom) parametrizada por longitud EN PLANTA."""

    def __init__(self, puntos, subdiv=12):
        pts = [Vector((p[0], p[1], p[2])) for p in puntos]
        if len(pts) < 2:
            raise ValueError("viaducto_curvo: hacen falta >= 2 puntos")
        dense = []
        n = len(pts)
        for i in range(n - 1):
            p0 = pts[i - 1] if i > 0 else pts[0] * 2.0 - pts[1]
            p1, p2 = pts[i], pts[i + 1]
            p3 = pts[i + 2] if i + 2 < n else pts[-1] * 2.0 - pts[-2]
            for k in range(subdiv):
                dense.append(_catmull(p0, p1, p2, p3, k / subdiv))
        dense.append(pts[-1].copy())
        self.pts = [dense[0]]
        for p in dense[1:]:
            if (p.xy - self.pts[-1].xy).length > 1e-5:
                self.pts.append(p)
        if len(self.pts) < 2:
            raise ValueError("viaducto_curvo: eje degenerado (sin avance en planta)")
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + (b.xy - a.xy).length)
        self.L = self.cum[-1]

    def _loc(self, s):
        s = min(max(s, 0.0), self.L)
        i = bisect.bisect_right(self.cum, s) - 1
        i = min(max(i, 0), len(self.pts) - 2)
        d = self.cum[i + 1] - self.cum[i]
        t = 0.0 if d <= 1e-12 else (s - self.cum[i]) / d
        return i, t

    def pos(self, s):
        i, t = self._loc(s)
        return self.pts[i].lerp(self.pts[i + 1], t)

    def frame(self, s):
        """(posicion, tangente horizontal unitaria, normal lateral unitaria)."""
        i, t = self._loc(s)
        seg = (self.pts[i + 1] - self.pts[i]).xy
        j = i
        while seg.length < 1e-9 and j > 0:
            j -= 1
            seg = (self.pts[j + 1] - self.pts[j]).xy
        seg.normalize()
        tang = Vector((seg.x, seg.y, 0.0))
        nrm = Vector((-seg.y, seg.x, 0.0))
        return self.pts[i].lerp(self.pts[i + 1], t), tang, nrm


# ---------------------------------------------------------- geometria basica

def _tubo_espina(v, f, fm, esp, cols, off0, off1, mi, fondos=None,
                 techo=True, caps=True):
    """Tubo que sigue la espina. cols = [(s, z_bajo, z_alto)]; dos columnas
    con la misma s generan cara vertical. fondos[j]: indice de material del
    fondo del tramo j, o None para omitirlo."""
    base = len(v)
    for (s, zb, zt) in cols:
        p, _t, nrm = esp.frame(s)
        v += [(p.x + nrm.x * off0, p.y + nrm.y * off0, zb),
              (p.x + nrm.x * off0, p.y + nrm.y * off0, zt),
              (p.x + nrm.x * off1, p.y + nrm.y * off1, zt),
              (p.x + nrm.x * off1, p.y + nrm.y * off1, zb)]
    n = len(cols)
    for j in range(n - 1):
        a = base + 4 * j
        b = a + 4
        if abs(cols[j][0] - cols[j + 1][0]) < 1e-9:
            f.append((a, a + 3, b + 3, b)); fm.append(mi)
            continue
        f.append((a, b, b + 1, a + 1)); fm.append(mi)          # cara off0
        f.append((a + 2, b + 2, b + 3, a + 3)); fm.append(mi)  # cara off1
        if techo:
            f.append((a + 1, b + 1, b + 2, a + 2)); fm.append(mi)
        mif = mi if fondos is None else fondos[j]
        if mif is not None:
            f.append((a + 3, b + 3, b, a)); fm.append(mif)
    if caps:
        f.append((base, base + 1, base + 2, base + 3)); fm.append(mi)
        e = base + 4 * (n - 1)
        f.append((e + 3, e + 2, e + 1, e)); fm.append(mi)


def _caja_espina(v, f, fm, esp, s, off, z0, sx, sy, sz, mi, taper=1.0):
    """Caja orientada segun la tangente local (sx a lo largo, sy lateral)."""
    p, tang, nrm = esp.frame(s)
    c = Vector((p.x + nrm.x * off, p.y + nrm.y * off, 0.0))
    base = len(v)
    for (dz, esc) in ((0.0, 1.0), (sz, taper)):
        hx, hy = sx * esc / 2.0, sy * esc / 2.0
        for (ax, ay) in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)):
            q = c + tang * ax + nrm * ay
            v.append((q.x, q.y, z0 + dz))
    for quad in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        f.append(tuple(base + i for i in quad)); fm.append(mi)


def _tajamar_espina(v, f, fm, esp, s, lado, y_cara, w, d, z0, z1, mi):
    """Espolon triangular con remate piramidal en un costado de la pila."""
    p, tang, nrm = esp.frame(s)
    c = Vector((p.x, p.y, 0.0))
    y0 = lado * y_cara
    y1 = y0 + lado * d

    def P(ax, ay, z):
        q = c + tang * ax + nrm * ay
        return (q.x, q.y, z)

    base = len(v)
    v += [P(-w / 2, y0, z0), P(w / 2, y0, z0), P(0.0, y1, z0),
          P(-w / 2, y0, z1), P(w / 2, y0, z1), P(0.0, y1, z1),
          P(0.0, y0 + lado * d * 0.35, z1 + w * 0.75)]
    for fc in ((0, 2, 5, 3), (2, 1, 4, 5), (0, 1, 2),
               (3, 5, 6), (5, 4, 6), (4, 3, 6)):
        f.append(tuple(base + i for i in fc)); fm.append(mi)


def _anillo_espina(v, f, fm, esp, s_c, R, zc, a0, a1, off_in, off_out,
                   mi_a, mi_b, mi_clave, n_seg):
    """Anillo de dovelas insinuadas (tonos alternos, clave resaltada)."""
    for s in range(n_seg):
        th0 = a0 + (a1 - a0) * (s / n_seg)
        th1 = a0 + (a1 - a0) * ((s + 1) / n_seg)
        clave = (n_seg % 2 == 1 and s == n_seg // 2)
        extra = 0.30 if clave else 0.0
        mi = mi_clave if clave else (mi_a if s % 2 == 0 else mi_b)
        r0 = R - 0.10
        r1 = R + 0.82 + extra
        base = len(v)
        for th in (th0, th1):
            cs, sn = math.cos(th), math.sin(th)
            for (r, off) in ((r0, off_in), (r1, off_in),
                             (r1, off_out), (r0, off_out)):
                p, _t, nrm = esp.frame(s_c + r * cs)
                v.append((p.x + nrm.x * off, p.y + nrm.y * off,
                          zc + r * sn))
        a, b = base, base + 4
        f.append((a + 1, b + 1, b + 2, a + 2)); fm.append(mi)  # trasdos
        f.append((a, b, b + 3, a + 3)); fm.append(mi)          # intrados
        f.append((a + 2, b + 2, b + 3, a + 3)); fm.append(mi)  # frente
        if s == 0 or clave:
            f.append((a, a + 1, a + 2, a + 3)); fm.append(mi)
        if s == n_seg - 1 or clave:
            f.append((b, b + 1, b + 2, b + 3)); fm.append(mi)


def _malla(nombre, verts, faces, fmats, mats, parent_obj, coleccion):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    for m in mats:
        me.materials.append(m)
    for p, mi in zip(me.polygons, fmats):
        p.material_index = mi
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(nombre, me)
    ob.parent = parent_obj
    coleccion.objects.link(ob)
    return ob


# --------------------------------------------------------------- constructor

def build_desde_puntos(parent_collection, puntos, ancho=13.0, nivel_agua=0.0,
                       seed=0, nombre="tramo", vano_objetivo=14.0, **params):
    """Genera la obra de fabrica del viaducto bajo el eje `puntos`."""
    del seed  # determinista; se acepta por contrato
    esp = _Espina(puntos)
    L = esp.L
    coleccion = parent_collection
    raiz = bpy.data.objects.new("%s_%s" % (PFX, nombre), None)
    raiz.empty_display_size = 2.0
    coleccion.objects.link(raiz)

    hw_muro = ancho / 2.0 - 0.45     # muro de timpano
    hw_losa = ancho / 2.0            # tablero (estructura, no calzada)
    hw_imp = ancho / 2.0 + 0.22      # imposta corrida
    y_bal = ancho / 2.0 - 0.38       # eje de la balaustrada
    base_z = nivel_agua - 4.0
    hp = 1.3                          # semi-ancho de pila a lo largo del eje

    n_vanos = max(1, int(round(L / vano_objetivo)))
    while n_vanos > 1 and L / n_vanos - 2.0 * hp < 4.0:
        n_vanos -= 1
    vano = L / n_vanos

    def z_eje(s):
        return esp.pos(s).z

    # ---- perfil inferior del muro: pilas + arcos
    cols = [(0.0, base_z)]
    fondos = []
    arcos = []   # (s_c, R, zc, a0, a1, z_arranque)

    def add(s, z, fondo):
        cols.append((s, z))
        fondos.append(fondo)

    for i in range(n_vanos):
        s_l = i * vano + hp
        s_r = (i + 1) * vano - hp
        luz = s_r - s_l
        s_c = (s_l + s_r) / 2.0
        z_min = min(z_eje(s_l + luz * k / 8.0) for k in range(9))
        z_clave = z_min - 1.55            # intrados en la clave
        R = luz / 2.0
        if z_clave - R >= nivel_agua + 0.35:
            z_arr = z_clave - R           # medio punto
            zc = z_arr
            a0, a1 = math.pi, 0.0
        else:                             # rebajado (tablero bajo)
            flecha = max(z_clave - (nivel_agua + 0.35), luz * 0.15)
            z_arr = z_clave - flecha
            R = flecha / 2.0 + luz * luz / (8.0 * flecha)
            zc = z_arr + flecha - R
            half = math.asin((luz / 2.0) / R)
            a0, a1 = math.pi / 2.0 + half, math.pi / 2.0 - half
        add(s_l, base_z, None)
        add(s_l, z_arr, None)
        n_seg = max(8, min(16, int(round(luz))))
        for k in range(1, n_seg):
            th = a0 + (a1 - a0) * (k / n_seg)
            add(s_c + R * math.cos(th), zc + R * math.sin(th), 2)
        add(s_r, z_arr, 2)
        add(s_r, base_z, None)
        arcos.append((s_c, R, zc, a0, a1, z_arr))
    add(L, base_z, None)

    m_piedra = _mat("piedra")
    m_sillar = _mat("sillar")
    m_intra = _mat("intrados")
    m_dov_a = _mat("dovela_a")
    m_dov_b = _mat("dovela_b")
    m_clave = _mat("clave")
    m_zoc = _mat("zocalo")
    m_bal = _mat("balaustre")

    # =============================== cuerpo ===============================
    v, f, fm = [], [], []
    mats = [m_piedra, m_sillar, m_intra, m_dov_a, m_dov_b, m_clave, m_zoc]

    cols3 = [(s, zb, z_eje(s) - 0.92) for (s, zb) in cols]
    _tubo_espina(v, f, fm, esp, cols3, -hw_muro, hw_muro, 0, fondos=fondos)

    # anillos de dovelas insinuadas en ambas caras
    for (s_c, R, zc, a0, a1, _za) in arcos:
        luz_a = 2.0 * R * abs(math.cos(a0))
        if a0 == math.pi:
            luz_a = 2.0 * R
        n_dov = int(luz_a * 0.8)
        n_dov = max(7, min(13, n_dov if n_dov % 2 == 1 else n_dov + 1))
        for lado in (-1, 1):
            _anillo_espina(v, f, fm, esp, s_c, R, zc, a0, a1,
                           lado * (hw_muro - 0.05), lado * (hw_muro + 0.24),
                           3, 4, 5, n_dov)

    # zocalos, cornisas de arranque y tajamares por pila
    for i in range(n_vanos + 1):
        s_p = min(max(i * vano, hp * 0.6), L - hp * 0.6)
        z_arrs = []
        if i > 0:
            z_arrs.append(arcos[i - 1][5])
        if i < n_vanos:
            z_arrs.append(arcos[i][5])
        z_arr_min = min(z_arrs)
        _caja_espina(v, f, fm, esp, s_p, 0.0, z_arr_min - 0.45,
                     2.0 * hp + 0.55, 2.0 * hw_muro + 0.55, 0.42, 1)
        _caja_espina(v, f, fm, esp, s_p, 0.0, base_z,
                     2.0 * hp + 0.8, 2.0 * hw_muro + 0.8,
                     (nivel_agua + 0.85) - base_z, 6)
        if 0 < i < n_vanos:
            z_taj = min(nivel_agua + 2.5, z_arr_min - 0.55)
            if z_taj > nivel_agua + 0.6:
                for lado in (-1, 1):
                    _tajamar_espina(v, f, fm, esp, s_p, lado, hw_muro + 0.02,
                                    2.0 * hp * 0.85, 1.25, base_z, z_taj, 6)

    # imposta corrida + losa del tablero (la calzada va aparte, ENCIMA)
    n_s = max(2, int(L / 2.6) + 1)
    ss = [L * k / (n_s - 1) for k in range(n_s)]
    cols_i = [(s, z_eje(s) - 1.38, z_eje(s) - 1.02) for s in ss]
    _tubo_espina(v, f, fm, esp, cols_i, -hw_imp, hw_imp, 1)
    cols_l = [(s, z_eje(s) - 1.05, z_eje(s) - 0.06) for s in ss]
    _tubo_espina(v, f, fm, esp, cols_l, -hw_losa, hw_losa, 0,
                 fondos=[1] * (n_s - 1))
    _malla("%s_%s_cuerpo" % (PFX, nombre), v, f, fm, mats, raiz, coleccion)

    # ============================ balaustrada =============================
    v, f, fm = [], [], []
    mats = [m_bal]
    sa, sb = 0.25, L - 0.25
    n_s = max(2, int((sb - sa) / 2.6) + 1)
    ss = [sa + (sb - sa) * k / (n_s - 1) for k in range(n_s)]
    sin_fondo = [None] * (n_s - 1)
    for lado in (-1, 1):
        yc = lado * y_bal
        cols_p = [(s, z_eje(s) - 0.10, z_eje(s) + 0.22) for s in ss]
        _tubo_espina(v, f, fm, esp, cols_p, yc - 0.17, yc + 0.17, 0,
                     fondos=sin_fondo)
        cols_r = [(s, z_eje(s) + 0.74, z_eje(s) + 0.96) for s in ss]
        _tubo_espina(v, f, fm, esp, cols_r, yc - 0.15, yc + 0.15, 0,
                     fondos=sin_fondo)
        n_post = max(1, int((sb - sa) / 2.2))
        for k in range(n_post + 1):
            s = sa + (sb - sa) * k / n_post
            _caja_espina(v, f, fm, esp, s, yc, z_eje(s) + 0.20,
                         0.26, 0.26, 0.56, 0, taper=0.72)
    _malla("%s_%s_balaustrada" % (PFX, nombre), v, f, fm, mats, raiz, coleccion)

    return raiz


# ----------------------------------------------------------------- API kit

def _curva_s_demo(largo=150.0):
    """Curva en S de `largo` m con z variable (muestra)."""
    pts = []
    n = 21
    for i in range(n):
        t = i / (n - 1)
        x = -largo / 2.0 + largo * t
        y = 15.0 * math.sin(t * math.pi * 1.5)
        z = 10.8 + 3.4 * math.sin(t * math.pi)
        pts.append((x, y, z))
    return pts


def build(parent_collection, seed=0, **params):
    """Muestra: tramo en S de 150 m sobre agua a z=0."""
    return build_desde_puntos(parent_collection, _curva_s_demo(),
                              seed=seed, **params)
