"""ACUEDUCTO — Acueducto decorativo de dos pisos que corona Porto Corsa (Cars 2).

Doble arcada estilo acueducto romano (Segovia / Pont du Gard "car-ificado"):
piso inferior de arcos altos y esbeltos sobre pilas con zocalo e imposta,
piso superior de arcos mas pequenos y juntos, cornisa corrida entre pisos y
remate superior plano. Piedra clara calida, saturada, low-poly con presencia.
Es el fondo del fotograma del puente en la pelicula.

API:
  build(parent_collection, largo=180, alto=42, n_arcos=8, seed=0, **params)
      Crea el acueducto, lo linka a parent_collection y devuelve el Empty
      raiz. params opcional: n_arcos_sup (por defecto 3*n_arcos).

Convenciones: metros, origen en el centro de la base (z=0 en el suelo),
eje largo en X, caras principales mirando a +/-Y. <= 8k tris.
"""

import math
import random

import bpy
import bmesh

PFX = "ACUEDUCTO"

# ---------------------------------------------------------------- materiales

_PALETA = {
    "piedra":       ((0.600, 0.380, 0.155), 0.92, 0.0),
    "piedra_clara": ((0.860, 0.645, 0.330), 0.90, 0.0),
    "cornisa":      ((0.920, 0.775, 0.460), 0.88, 0.0),
    "zocalo":       ((0.420, 0.255, 0.100), 0.94, 0.0),
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

def _tubo(verts, faces, fmats, cols, y0, y1, mi, caps=True, z_sin_fondo=None):
    """Tubo a lo largo de X. cols = [(x, z_bajo, z_alto)]. Columnas repetidas
    en la misma x generan pared vertical (costado de pila). El fondo se omite
    en los tramos cuyo z_bajo coincide con z_sin_fondo (arranque del piso)."""
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
        oculto = (z_sin_fondo is not None and
                  abs(zba - z_sin_fondo) < 1e-6 and abs(zbb - z_sin_fondo) < 1e-6)
        if not oculto:
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


# ------------------------------------------------------------- sub-elementos

def _cols_arcada(largo, n_arcos, ancho_pila, z_base, z_arranque, seg):
    """Perfil inferior de una arcada de arcos de medio punto. Devuelve
    columnas (x, z_bajo), lista de arcos (cx, R) y la luz de los vanos."""
    luz = (largo - (n_arcos + 1) * ancho_pila) / n_arcos
    R = luz / 2.0
    x0 = -largo / 2.0
    cols = [(x0, z_base)]
    arcos = []
    for i in range(n_arcos):
        xl = x0 + ancho_pila + i * (luz + ancho_pila)
        xr = xl + luz
        cx = (xl + xr) / 2.0
        cols.append((xl, z_base))
        cols.append((xl, z_arranque))
        for k in range(1, seg):
            th = math.pi * (1.0 - k / seg)
            cols.append((cx + R * math.cos(th), z_arranque + R * math.sin(th)))
        cols.append((xr, z_arranque))
        cols.append((xr, z_base))
        arcos.append((cx, R))
    cols.append((largo / 2.0, z_base))
    return cols, arcos, luz


def _anillo(verts, faces, fmats, cx, R, zc, y_in, y_out, mi, mi_clave,
            seg, grosor):
    """Archivolta de un arco en una cara del muro, con clave resaltada
    opcional (mi_clave y seg impar)."""
    for s in range(seg):
        th0 = math.pi * (1.0 - s / seg)
        th1 = math.pi * (1.0 - (s + 1) / seg)
        clave = (mi_clave is not None and seg % 2 == 1 and s == seg // 2)
        r0 = R - (0.24 if clave else 0.08)
        r1 = R + grosor + (0.42 if clave else 0.0)
        m = mi_clave if clave else mi
        base = len(verts)
        for th in (th0, th1):
            cs, sn = math.cos(th), math.sin(th)
            verts += [(cx + r0 * cs, y_in, zc + r0 * sn),
                      (cx + r1 * cs, y_in, zc + r1 * sn),
                      (cx + r1 * cs, y_out, zc + r1 * sn),
                      (cx + r0 * cs, y_out, zc + r0 * sn)]
        a, b = base, base + 4
        faces.append((a + 1, b + 1, b + 2, a + 2)); fmats.append(m)  # trasdos
        faces.append((a, b, b + 3, a + 3)); fmats.append(m)          # intrados
        faces.append((a + 2, b + 2, b + 3, a + 3)); fmats.append(m)  # frente
        if s == 0 or clave:
            faces.append((a, a + 1, a + 2, a + 3)); fmats.append(m)
        if s == seg - 1 or clave:
            faces.append((b, b + 1, b + 2, b + 3)); fmats.append(m)


# ----------------------------------------------------------------- build

def build(parent_collection, largo=180.0, alto=42.0, n_arcos=8, seed=0,
          **params):
    """Acueducto de dos pisos. Devuelve el Empty raiz."""
    rnd = random.Random(seed)
    n_arcos = max(2, int(n_arcos))
    n_sup = int(params.get("n_arcos_sup") or n_arcos * 3)
    coleccion = parent_collection

    raiz = bpy.data.objects.new("%s_raiz" % PFX, None)
    raiz.empty_display_size = 2.0
    coleccion.objects.link(raiz)

    # ---- proporciones verticales
    e_remate = max(0.8, alto * 0.024)          # losa plana superior
    h_cornisa = max(0.55, alto * 0.017)        # banda corrida entre pisos
    h1 = alto * 0.615                          # techo del muro inferior
    z_base2 = h1 + h_cornisa                   # arranque del piso superior
    z_top2 = alto - e_remate                   # techo del muro superior

    ancho_inf = max(4.4, largo * 0.030)
    ancho_sup = ancho_inf * 0.72
    hw_i = ancho_inf / 2.0
    hw_s = ancho_sup / 2.0

    # ---- arcadas
    p1 = (largo / n_arcos) * 0.20              # pila inferior
    p2 = (largo / n_sup) * 0.24                # pila superior (juntas)
    seg1, seg2 = 13, 8

    m_piedra = _mat("piedra")
    m_clara = _mat("piedra_clara")
    m_cornisa = _mat("cornisa")
    m_zocalo = _mat("zocalo")

    v, f, fm = [], [], []
    mats = [m_piedra, m_clara, m_cornisa, m_zocalo]
    MI_P, MI_CL, MI_CO, MI_ZO = 0, 1, 2, 3

    # ---- muro inferior con arcos altos y esbeltos
    z_arr1 = h1 - 1.6 - ((largo - (n_arcos + 1) * p1) / n_arcos) / 2.0
    cols, arcos1, luz1 = _cols_arcada(largo, n_arcos, p1, 0.0, z_arr1, seg1)
    _tubo(v, f, fm, [(x, zb, h1) for (x, zb) in cols], -hw_i, hw_i, MI_P,
          z_sin_fondo=0.0)
    for (cx, R) in arcos1:
        gros = 0.78 + rnd.uniform(-0.05, 0.05)
        _anillo(v, f, fm, cx, R, z_arr1, -hw_i + 0.05, -hw_i - 0.30,
                MI_CL, MI_CO, seg1, gros)
        _anillo(v, f, fm, cx, R, z_arr1, hw_i - 0.05, hw_i + 0.30,
                MI_CL, MI_CO, seg1, gros)

    # ---- muro superior con arcos pequenos y juntos
    z_arr2 = z_top2 - 1.0 - ((largo - (n_sup + 1) * p2) / n_sup) / 2.0
    cols, arcos2, luz2 = _cols_arcada(largo, n_sup, p2, z_base2, z_arr2, seg2)
    _tubo(v, f, fm, [(x, zb, z_top2) for (x, zb) in cols], -hw_s, hw_s, MI_P,
          z_sin_fondo=z_base2)
    for (cx, R) in arcos2:
        _anillo(v, f, fm, cx, R, z_arr2, -hw_s + 0.04, -hw_s - 0.16,
                MI_CL, None, seg2, 0.42)
        _anillo(v, f, fm, cx, R, z_arr2, hw_s - 0.04, hw_s + 0.16,
                MI_CL, None, seg2, 0.42)

    # ---- zocalos, impostas y lesenas por pila inferior
    x0 = -largo / 2.0
    for i in range(n_arcos + 1):
        cxp = x0 + i * (luz1 + p1) + p1 / 2.0
        hz = 1.3 + rnd.uniform(-0.15, 0.15)
        _caja(v, f, fm, cxp, 0.0, 0.0, p1 + 1.0, ancho_inf + 1.0, hz, MI_ZO)
        _caja(v, f, fm, cxp, 0.0, z_arr1 - 0.55,
              p1 + 0.85, ancho_inf + 0.6, 0.55, MI_CO)
        for lado in (-1, 1):
            _caja(v, f, fm, cxp, lado * hw_i, hz + 0.1,
                  p1 * 0.62, 0.34, z_arr1 - 0.65 - hz - 0.1, MI_CL)

    # ---- cornisa corrida entre pisos y remate superior plano
    _caja(v, f, fm, 0.0, 0.0, h1, largo + 0.5, ancho_inf + 1.2, h_cornisa,
          MI_CO)
    _caja(v, f, fm, 0.0, 0.0, z_top2 - 0.35, largo + 0.3, ancho_sup + 0.7,
          0.35, MI_CL)
    _caja(v, f, fm, 0.0, 0.0, z_top2, largo + 0.8, ancho_sup + 1.3, e_remate,
          MI_CO)

    # ---- machones de remate en los extremos
    for lado in (-1, 1):
        cxe = lado * largo / 2.0
        _caja(v, f, fm, cxe, 0.0, 0.0, 4.6, ancho_inf + 1.1, 1.5, MI_ZO)
        _caja(v, f, fm, cxe, 0.0, 1.5, 4.0, ancho_inf + 0.7, z_base2 - 1.5,
              MI_P)
        _caja(v, f, fm, cxe, 0.0, z_base2, 4.4, ancho_inf + 1.0, 0.6, MI_CO)

    _malla("%s_cuerpo" % PFX, v, f, fm, mats, raiz, coleccion)
    return raiz
