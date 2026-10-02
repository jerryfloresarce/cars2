"""PUENTES — Puentes de piedra clara estilo viaducto romano / Riviera (Porto Corsa, Cars 2).

Kit procedural para el sector del casino. Piedra caliza calida, dovelas
marcadas en los arcos, balaustrada de piedra y astas para banderolas.

Piezas (todas linkan a la coleccion recibida y devuelven un Empty raiz):
  build_viaducto(parent, largo=120, ancho_tablero=14, alto=18, n_arcos=5)
      Gran viaducto del Puente del Casino: pilas con tajamares e impostas,
      arcos de medio punto con anillo de dovelas alternadas y clave resaltada,
      tablero plano con calzada asfaltada, balaustrada a ambos lados y astas
      doradas con banderolas rojas/verdes cada 15 m.
  build_puente_menor(parent, largo=40, ancho_tablero=12, alto=8, n_arcos=1)
      Puente arqueado menor (lomo de asno suave, apto para coches): un arco
      rebajado, tablero en comba y balaustrada continua.
  build(parent_collection, seed=0, **params)
      Muestra el viaducto de 120 m.

Convenciones: metros, origen en el centro de la base (z=0 en el suelo/agua),
eje largo en X, caras principales mirando a +/-Y. <= 8k tris por puente.
"""

import math
import random

import bpy
import bmesh

PFX = "PUENTES"

# ---------------------------------------------------------------- materiales

_PALETA = {
    "piedra":          ((0.640, 0.475, 0.245), 0.92, 0.0),
    "dovela_clara":    ((0.870, 0.700, 0.400), 0.90, 0.0),
    "dovela_oscura":   ((0.360, 0.235, 0.105), 0.90, 0.0),
    "clave":           ((0.930, 0.800, 0.480), 0.88, 0.0),
    "balaustre":       ((0.840, 0.720, 0.480), 0.90, 0.0),
    "asfalto":         ((0.042, 0.042, 0.048), 0.92, 0.0),
    "asta":            ((0.560, 0.360, 0.090), 0.35, 0.85),
    "banderola_roja":  ((0.580, 0.030, 0.030), 0.60, 0.0),
    "banderola_verde": ((0.025, 0.380, 0.095), 0.60, 0.0),
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


# ---------------------------------------------------------- geometria basica

def _tubo(verts, faces, fmats, cols, y0, y1, mi, caps=True, fondo=True):
    """Tubo a lo largo de X. cols = [(x, z_bajo, z_alto)]. Columnas repetidas
    en la misma x generan la pared vertical (costado de pila)."""
    base = len(verts)
    for (x, zb, zt) in cols:
        verts += [(x, y0, zb), (x, y0, zt), (x, y1, zt), (x, y1, zb)]
    n = len(cols)
    for j in range(n - 1):
        a = base + 4 * j
        b = a + 4
        xa, zba, _ = cols[j]
        xb, zbb, _ = cols[j + 1]
        if abs(xa - xb) < 1e-9:
            faces.append((a, a + 3, b + 3, b)); fmats.append(mi)
            continue
        faces.append((a, b, b + 1, a + 1)); fmats.append(mi)          # cara y0
        faces.append((a + 1, b + 1, b + 2, a + 2)); fmats.append(mi)  # techo
        faces.append((a + 2, b + 2, b + 3, a + 3)); fmats.append(mi)  # cara y1
        if fondo and not (zba < 1e-6 and zbb < 1e-6):
            faces.append((a + 3, b + 3, b, a)); fmats.append(mi)      # fondo
    if caps:
        faces.append((base, base + 1, base + 2, base + 3)); fmats.append(mi)
        e = base + 4 * (n - 1)
        faces.append((e + 3, e + 2, e + 1, e)); fmats.append(mi)


def _caja(verts, faces, fmats, cx, cy, cz, sx, sy, sz, mi, sx_top=None, sy_top=None):
    hx0, hy0 = sx / 2.0, sy / 2.0
    hx1 = (sx_top if sx_top is not None else sx) / 2.0
    hy1 = (sy_top if sy_top is not None else sy) / 2.0
    z0, z1 = cz, cz + sz
    base = len(verts)
    verts += [(cx - hx0, cy - hy0, z0), (cx + hx0, cy - hy0, z0),
              (cx + hx0, cy + hy0, z0), (cx - hx0, cy + hy0, z0),
              (cx - hx1, cy - hy1, z1), (cx + hx1, cy - hy1, z1),
              (cx + hx1, cy + hy1, z1), (cx - hx1, cy + hy1, z1)]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
              (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        faces.append(tuple(base + i for i in q)); fmats.append(mi)


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


# ------------------------------------------------------------ sub-elementos

def _columnas_arcos(largo, n_arcos, ancho_pila, z_arranque, margen_clave,
                    seg_arco, z_techo_fn):
    """Perfil inferior del cuerpo con vanos de arco. Devuelve columnas
    (x, z_bajo) y datos de cada arco (cx, R, zc, a0, a1, luz)."""
    luz = (largo - (n_arcos + 1) * ancho_pila) / n_arcos
    x0 = -largo / 2.0
    cols = [(x0, 0.0)]
    arcos = []
    for i in range(n_arcos):
        xl = x0 + ancho_pila + i * (luz + ancho_pila)
        xr = xl + luz
        cx = (xl + xr) / 2.0
        disp = z_techo_fn(cx) - margen_clave - z_arranque
        if disp >= luz / 2.0:
            R = luz / 2.0
            zc = z_arranque
            a0, a1 = math.pi, 0.0
        else:
            flecha = max(disp, luz * 0.12)
            R = flecha / 2.0 + luz * luz / (8.0 * flecha)
            zc = z_arranque + flecha - R
            half = math.asin((luz / 2.0) / R)
            a0, a1 = math.pi / 2.0 + half, math.pi / 2.0 - half
        cols.append((xl, 0.0))
        cols.append((xl, z_arranque))
        for k in range(1, seg_arco):
            th = a0 + (a1 - a0) * (k / seg_arco)
            cols.append((cx + R * math.cos(th), zc + R * math.sin(th)))
        cols.append((xr, z_arranque))
        cols.append((xr, 0.0))
        arcos.append((cx, R, zc, a0, a1, luz))
    cols.append((largo / 2.0, 0.0))
    return cols, arcos, luz


def _anillo_dovelas(verts, faces, fmats, cx, R, zc, a0, a1, y_in, y_out,
                    mi_a, mi_b, mi_clave, n_seg):
    """Anillo de dovelas alternadas con clave resaltada, en una cara."""
    for s in range(n_seg):
        th0 = a0 + (a1 - a0) * (s / n_seg)
        th1 = a0 + (a1 - a0) * ((s + 1) / n_seg)
        extra = 0.0
        mi = mi_a if s % 2 == 0 else mi_b
        clave = (n_seg % 2 == 1 and s == n_seg // 2)
        if clave:
            extra = 0.35
            mi = mi_clave
        r0 = R - 0.10
        r1 = R + 0.95 + extra
        base = len(verts)
        for th in (th0, th1):
            cs, sn = math.cos(th), math.sin(th)
            verts += [(cx + r0 * cs, y_in, zc + r0 * sn),
                      (cx + r1 * cs, y_in, zc + r1 * sn),
                      (cx + r1 * cs, y_out, zc + r1 * sn),
                      (cx + r0 * cs, y_out, zc + r0 * sn)]
        a, b = base, base + 4
        faces.append((a + 1, b + 1, b + 2, a + 2)); fmats.append(mi)  # trasdos
        faces.append((a, b, b + 3, a + 3)); fmats.append(mi)          # intrados
        faces.append((a + 2, b + 2, b + 3, a + 3)); fmats.append(mi)  # frente
        if s == 0 or clave:
            faces.append((a, a + 1, a + 2, a + 3)); fmats.append(mi)
        if s == n_seg - 1 or clave:
            faces.append((b, b + 1, b + 2, b + 3)); fmats.append(mi)


def _tajamar(verts, faces, fmats, cx, y_cara, sentido, w, d, h, mi):
    """Espolon triangular en la base de una pila (una cara)."""
    y0 = y_cara
    y1 = y_cara + sentido * d
    base = len(verts)
    verts += [(cx - w / 2, y0, 0.0), (cx + w / 2, y0, 0.0), (cx, y1, 0.0),
              (cx - w / 2, y0, h), (cx + w / 2, y0, h), (cx, y1, h),
              (cx, y_cara + sentido * d * 0.35, h + w * 0.85)]
    for f in ((0, 2, 5, 3), (2, 1, 4, 5), (3, 5, 6), (5, 4, 6), (4, 3, 6)):
        faces.append(tuple(base + i for i in f)); fmats.append(mi)


def _asta(verts, faces, fmats, cx, cy, z0, h, r, mi):
    n = 6
    base = len(verts)
    for z in (z0, z0 + h):
        for k in range(n):
            a = 2.0 * math.pi * k / n
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((base + k, base + k2, base + n + k2, base + n + k))
        fmats.append(mi)
    apex = len(verts)
    verts.append((cx, cy, z0 + h + 0.35))
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((base + n + k, base + n + k2, apex)); fmats.append(mi)


# --------------------------------------------------------------- constructor

def _construir_puente(parent, nombre, largo, ancho, alto, n_arcos,
                      comba=0.0, astas_cada=0.0, ancho_pila=None,
                      z_arranque=None, seed=0):
    rnd = random.Random(seed)
    coleccion = parent
    raiz = bpy.data.objects.new("%s_%s" % (PFX, nombre), None)
    raiz.empty_display_size = 2.0
    coleccion.objects.link(raiz)

    grosor_tab = 1.1
    hw = ancho / 2.0

    def z_tablero(x):
        if comba <= 0.0:
            return float(alto)
        t = (2.0 * x / largo)
        return alto - comba * t * t

    def z_techo(x):
        return z_tablero(x) - grosor_tab

    if ancho_pila is None:
        if n_arcos <= 1:
            ancho_pila = max(3.5, largo * 0.11)
        else:
            ancho_pila = max(2.4, min(4.2, largo * 0.03))
    if z_arranque is None:
        z_arranque = max(0.8, min(alto * 0.32, 6.0))

    m_piedra = _mat("piedra")
    m_dov_a = _mat("dovela_clara")
    m_dov_b = _mat("dovela_oscura")
    m_clave = _mat("clave")
    m_bal = _mat("balaustre")
    m_asf = _mat("asfalto")
    m_asta = _mat("asta")
    m_ban_r = _mat("banderola_roja")
    m_ban_v = _mat("banderola_verde")

    # ---- cuerpo: muro con vanos de arco + dovelas + impostas + tajamares
    v, f, fm = [], [], []
    mats = [m_piedra, m_dov_a, m_dov_b, m_clave]
    seg_arco = 18
    cols2, arcos, luz = _columnas_arcos(largo, n_arcos, ancho_pila,
                                        z_arranque, 0.7, seg_arco, z_techo)
    cols3 = [(x, zb, z_techo(x)) for (x, zb) in cols2]
    _tubo(v, f, fm, cols3, -hw, hw, 0)

    for (cx, R, zc, a0, a1, luz_a) in arcos:
        n_seg = int(luz_a * 0.7)
        n_seg = max(9, min(23, n_seg if n_seg % 2 == 1 else n_seg + 1))
        _anillo_dovelas(v, f, fm, cx, R, zc, a0, a1, -hw + 0.05, -hw - 0.25,
                        1, 2, 3, n_seg)
        _anillo_dovelas(v, f, fm, cx, R, zc, a0, a1, hw - 0.05, hw + 0.25,
                        1, 2, 3, n_seg)

    # linea de imposta corrida bajo el tablero (cornisa que recorre el cuerpo)
    x0 = -largo / 2.0
    n_s = 2 if comba <= 0.0 else 16
    xs = [x0 + largo * i / (n_s - 1) for i in range(n_s)]
    cols = [(x, z_techo(x) - 0.55, z_techo(x) - 0.15) for x in xs]
    _tubo(v, f, fm, cols, -(hw + 0.15), hw + 0.15, 1)

    # impostas (cornisa al nivel de arranque), zocalos y tajamares por pila
    for i in range(n_arcos + 1):
        cxp = x0 + i * (luz + ancho_pila) + ancho_pila / 2.0
        _caja(v, f, fm, cxp, 0.0, z_arranque - 0.5,
              ancho_pila + 0.7, ancho + 0.5, 0.5, 1)
        _caja(v, f, fm, cxp, 0.0, 0.0,
              ancho_pila + 0.9, ancho + 0.9, min(1.4, z_arranque * 0.5), 0)
        if 0 < i < n_arcos and z_arranque > 2.0:
            _tajamar(v, f, fm, cxp, -hw, -1, ancho_pila * 0.85, 1.15,
                     z_arranque * 0.78, 0)
            _tajamar(v, f, fm, cxp, hw, 1, ancho_pila * 0.85, 1.15,
                     z_arranque * 0.78, 0)
    _malla("%s_%s_cuerpo" % (PFX, nombre), v, f, fm, mats, raiz, coleccion)

    # ---- tablero + calzada
    v, f, fm = [], [], []
    mats = [m_bal, m_asf]
    n_s = 2 if comba <= 0.0 else 16
    xs = [x0 + largo * i / (n_s - 1) for i in range(n_s)]
    cols = [(x, z_techo(x) - 0.2, z_tablero(x)) for x in xs]
    _tubo(v, f, fm, cols, -(hw + 0.6), hw + 0.6, 0)
    cols = [(x, z_tablero(x) + 0.005, z_tablero(x) + 0.07) for x in xs]
    _tubo(v, f, fm, cols, -(hw - 1.15), hw - 1.15, 1, fondo=False)
    _malla("%s_%s_tablero" % (PFX, nombre), v, f, fm, mats, raiz, coleccion)

    # ---- balaustrada de piedra a ambos lados
    v, f, fm = [], [], []
    mats = [m_bal]
    margen_x = 0.35
    xa, xb = x0 + margen_x, -x0 - margen_x
    n_s = 2 if comba <= 0.0 else 16
    xs = [xa + (xb - xa) * i / (n_s - 1) for i in range(n_s)]
    for lado in (-1, 1):
        yc = lado * (hw - 0.55)
        cols = [(x, z_tablero(x) - 0.05, z_tablero(x) + 0.22) for x in xs]
        _tubo(v, f, fm, cols, yc - 0.30, yc + 0.30, 0, fondo=False)
        cols = [(x, z_tablero(x) + 0.98, z_tablero(x) + 1.30) for x in xs]
        _tubo(v, f, fm, cols, yc - 0.28, yc + 0.28, 0)
        n_bal = int((xb - xa) / 1.6)
        for i in range(n_bal + 1):
            x = xa + (xb - xa) * i / n_bal
            _caja(v, f, fm, x, yc, z_tablero(x) + 0.20, 0.30, 0.30, 0.80, 0,
                  sx_top=0.20, sy_top=0.20)
    _malla("%s_%s_balaustrada" % (PFX, nombre), v, f, fm, mats, raiz, coleccion)

    # ---- astas para banderolas
    if astas_cada and astas_cada > 0.0:
        v, f, fm = [], [], []
        mats = [m_asta, m_ban_r, m_ban_v]
        n_p = int(largo / astas_cada)
        alterna = rnd.randrange(2)
        for i in range(n_p):
            x = x0 + astas_cada * (i + 0.5)
            for lado in (-1, 1):
                yc = lado * (hw - 0.55)
                zt = z_tablero(x)
                _asta(v, f, fm, x, yc, zt - 0.1, 4.8, 0.09, 0)
                mi_ban = 1 if (i + (0 if lado < 0 else 1) + alterna) % 2 == 0 else 2
                _caja(v, f, fm, x, yc - lado * 0.44, zt + 2.05,
                      1.15, 0.08, 2.35, mi_ban)
        _malla("%s_%s_astas" % (PFX, nombre), v, f, fm, mats, raiz, coleccion)

    return raiz


# ----------------------------------------------------------------- API kit

def build_viaducto(parent, largo=120.0, ancho_tablero=14.0, alto=18.0,
                   n_arcos=5, seed=0, **params):
    """Gran viaducto del Puente del Casino (arcos de medio punto)."""
    return _construir_puente(parent, "viaducto", largo, ancho_tablero, alto,
                             n_arcos, comba=0.0, astas_cada=15.0, seed=seed)


def build_puente_menor(parent, largo=40.0, ancho_tablero=12.0, alto=8.0,
                       n_arcos=1, seed=0, **params):
    """Puente menor arqueado (tablero en comba suave)."""
    return _construir_puente(parent, "menor", largo, ancho_tablero, alto,
                             n_arcos, comba=1.3, astas_cada=0.0,
                             z_arranque=max(0.8, alto * 0.16), seed=seed)


def build(parent_collection, seed=0, **params):
    """Asset de muestra: viaducto de 120 m."""
    return build_viaducto(parent_collection, seed=seed, **params)
