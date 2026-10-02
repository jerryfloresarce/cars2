"""montana_coche_v2.py — La MONTAÑA-COCHE FÓSIL de Porto Corsa (Cars 2), v2.

Blender 5.1. Sustituye a montana_coche.py con la MISMA API pública y las
mismas garantías, pero con un coche gigante de piedra que se LEE como un
Fiat 500 / Topolino de Cars:

  * SILUETA: capó corto y redondeado, parabrisas inclinado, techo abombado
    continuo (cumbre 3.35R), zaga redondeada cayendo hasta el parachoques,
    estribos entre las aletas y parachoques delantero/trasero como BARRAS de
    piedra curvadas (piezas propias unidas por Boolean).
  * CARROCERÍA LISA de piedra desgastada: sin estratos; ruido suave de baja
    amplitud (0.01R) + GRIETAS finas (surcos de 0.25-0.4 m tallados con
    Boolean de cintas) + desconchones (casquetes restados, piedra clara).
    Loft de 0.07R entre estaciones y 88 vértices por anillo.
  * GUARDABARROS = pontones (cáscaras cerradas) que siguen el neumático con
    holgura 0.16R, ceja de 0.12R sobre el flanco y borde redondeado. La
    aleta delantera arranca a la altura del buje (-2 grados, no baja hasta
    el suelo) y su cara interior se prolonga hacia el capó, que se
    estrecha, para que no quede ranura abierta tras el faro; los extremos
    colapsan hacia un punto enterrado. Bajo ella la roca forma una repisa
    (delantal del morro).
  * DETALLES: faros en domo con aro (revolución), boca del parachoques
    rehundida y oscura, juntas y tiradores de puerta, VENTANILLAS, parabrisas
    y luneta como piezas Boolean (rebaje de 0.08R con fondo de cristal +
    marco de hueso saliente 0.06R con esquinas redondeadas, muestreados por
    ray-cast sobre el loft; montante B entre las dos ventanillas),
    retrovisores y tapa de rueda de repuesto (disco) en la zaga.
  * BASE: acantilado que envuelve los bajos (pie en talud con estratos
    marcados, bloques caídos, repisas escalonadas en la zaga que baja al mar).
  * COLORES: caliza cálida con moteado procedural (nodos, sin imágenes),
    cristal azulado oscuro mate, hueso claro en bujes/radios/aros.

API (idéntica a montana_coche.py):
  build(parent_collection, radio=40.0, ancho=78.0, alto_base=12.0,
        z_fondo=-45.0, seed=0, con_vegetacion=True, n_radios=12,
        segmentos_por_radio=7, talud_deg=35.0, solver="MANIFOLD",
        detalle_secundario=0.6, lado_visible=+1)
      -> malla raíz MCOCHE_roca (única, cerrada) + hijo MCOCHE_veg.
         lado_visible (+1 / -1): lado Y hacia el que llegan los coches; la
         rueda delantera de ese lado lleva detalle 1.0 y las grietas y
         desconchones de flanco/aleta se colocan en él (el integrador que
         oriente -Y hacia la pista debe pasar lado_visible=-1 o girar el
         coche 180 grados).
         Propiedades: obj["radio"], obj["ancho"], obj["alto_base"],
         obj["z_fondo"], obj["hubs"], obj["huella_x"], obj["bbox"],
         obj["lado_visible"], mesh["mcoche_no_manifold"] (0),
         mesh["mcoche_solver"].

Convenciones (metros; R = radio, W = ancho):
  Origen = centro de la RUEDA DELANTERA en planta (x=0, y=0); z=0 = suelo
  local (carretera, lado +Y, para x > -1.3R); mar (z=-4) para x < -1.5R y
  FALDA rocosa hasta z_fondo con base plana. Cara visible +Y; MORRO +X;
  ZAGA -X. Bujes en (0, ±W/2, R-alto_base) y (-3.4R, ±W/2, R-alto_base);
  cara del neumático en |y| = W/2, hundida alto_base bajo z=0.
  Carrocería: flanco máximo |y| = W/2 - 0.15R; aletas hasta |y| = W/2 -
  0.03R; zócalo rocoso en |y| = W/2 - 0.09R (pie hasta W/2 - 0.02R).
  Perfil (XZ, unid. R): parachoques delantero x=+1.56 z=0.90 (barra de
  caliza clara, sección 0.07R, extremos en el flanco del capó en x=0.96),
  morro 1.58, capó 1.3 -> 2.2, parabrisas hasta 3.05 en x=-0.55, techo
  3.35, luneta, zaga cayendo a 1.2 en x=-4.55, parachoques trasero
  x=-4.64 z=1.06 (barra corta de caliza clara, sección 0.09R, bajo la
  curva baja de la zaga; asoma ~3 m tras el domo, extremos hacia x=-4.28).
  Túnel del integrador: caja 21 x 9.5 m a lo largo de Y centrada en
  x=-0.65R desde z=0 atraviesa roca maciza en todo el grosor W (roca
  maciza bajo el coche en |x| < 1.1R). Zona prohibida: |y| <= W/2 + 2.5
  para x en [-1.3R, +1.5R] (clamp explícito de los vértices de la roca).
  Materiales (índices fijos): 0 MAT_MCOCHE_caliza, 1 _caliza_clara,
  2 _caliza_oscura, 3 _hueco, 4 _hueso, 5 _cristal; veg: MAT_MCOCHE_veg/
  _veg_clara/_tronco.
  Integrador: los Booleans se evalúan en el depsgraph con los temporales
  en bpy.context.scene.collection; si no evalúa -> RuntimeError.
  Cadena (solver MANIFOLD, EXACT de reserva): roca U bloques U carrocería
  - pasa-ruedas U aletas U ruedas U detalles U espejos U marcos - rebajes
  (cristales) - cortes (boca, grietas, desconchones). ~0.9 s.
"""

import importlib.util
import math
import os
import random

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


# ------------------------------------------------ helpers de montana_rueda --
def _cargar_mrueda():
    aqui = os.path.dirname(os.path.abspath(__file__))
    ruta = os.path.join(aqui, "montana_rueda.py")
    spec = importlib.util.spec_from_file_location("montana_rueda_helpers2", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MR = _cargar_mrueda()
_n3 = _MR._n3
_hash01 = _MR._hash01
_ridged = _MR._ridged
_celda = _MR._celda
_sstep = _MR._sstep
_spline = _MR._spline
_sq = _MR._sq
_mat = _MR._mat
_fase_estrato = _MR._fase_estrato
_onda_estrato = _MR._onda_estrato
_estrato_mat = _MR._estrato_mat
_radios_en = _MR._radios_en
_talla = _MR._talla
_angulos_cara = _MR._angulos_cara
_tyre_pt = _MR._tyre_pt
_perfil_base = _MR._perfil_base
_blob = _MR._blob
_pino = _MR._pino
_U_RINGS = _MR._U_RINGS
_PSI_RINGS = _MR._PSI_RINGS
_RING_U1 = _MR._RING_U1
_RIM_U1 = _MR._RIM_U1
_FLOOR_U1 = _MR._FLOOR_U1
_HUB_U = _MR._HUB_U
_COL_U0, _COL_U1 = _MR._COL_U0, _MR._COL_U1
_SPK_U0, _SPK_U1 = _MR._SPK_U0, _MR._SPK_U1
_RING_U0 = _MR._RING_U0

# índices de material (mismo orden en TODAS las piezas: el boolean los copia)
_M_CAL, _M_CLARA, _M_OSC, _M_HUECO, _M_HUESO, _M_CRISTAL = 0, 1, 2, 3, 4, 5


def _mat_piedra(name, color, color2, rough, escala, spec=0.25):
    """Principled BSDF de color plano con MOTEADO procedural (Noise Texture
    en coordenadas de objeto -> mezcla suave entre `color` y `color2`).
    Sin imágenes. Reutiliza el material si ya existe."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = _mat(name, color, rough, spec)
    nt = m.node_tree
    if nt is None:
        return m
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return m
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = escala
    nz.inputs["Detail"].default_value = 3.0
    nz.inputs["Roughness"].default_value = 0.55
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].position = 0.38
    rampa.color_ramp.elements[0].color = (*color, 1.0)
    rampa.color_ramp.elements[1].position = 0.66
    rampa.color_ramp.elements[1].color = (*color2, 1.0)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def _mats_roca():
    """Caliza CÁLIDA (ocre-crema, no gris frío) moteada; hueco casi negro
    pardo; hueso claro (buje, radios, aros, marcos); cristal azulado oscuro
    mate."""
    return (
        _mat_piedra("MAT_MCOCHE_caliza", (0.600, 0.490, 0.330),
                    (0.740, 0.650, 0.490), 0.95, 0.045),
        _mat_piedra("MAT_MCOCHE_caliza_clara", (0.740, 0.660, 0.500),
                    (0.840, 0.770, 0.610), 0.95, 0.06),
        _mat_piedra("MAT_MCOCHE_caliza_oscura", (0.400, 0.310, 0.200),
                    (0.490, 0.400, 0.280), 0.95, 0.06),
        _mat("MAT_MCOCHE_hueco", (0.085, 0.065, 0.045), 0.97, 0.10),
        _mat_piedra("MAT_MCOCHE_hueso", (0.800, 0.750, 0.620),
                    (0.870, 0.830, 0.700), 0.90, 0.12, 0.20),
        _mat("MAT_MCOCHE_cristal", (0.085, 0.125, 0.185), 0.72, 0.35),
    )


def _mats_veg():
    return (
        _mat("MAT_MCOCHE_veg", (0.062, 0.195, 0.058), 0.92),
        _mat("MAT_MCOCHE_veg_clara", (0.130, 0.310, 0.090), 0.92),
        _mat("MAT_MCOCHE_tronco", (0.230, 0.150, 0.090), 0.95),
    )


# ------------------------------------------------------------ layout (R) ----
_X_REAR = -3.4          # rueda trasera
_BAND_H = 0.17          # altura de estrato de la ROCA (unid. R)
_Y_BODY = 0.15          # flanco de la carrocería: W/2 - 0.15R
_Y_WALL = 0.09          # pared rocosa (zócalo): W/2 - 0.09R
_Y_FEND = 0.03          # cara exterior de la aleta: W/2 - 0.03R
_WELL_R = 1.17          # radio del pasa-ruedas (cilindro que corta cuerpo/roca)
_WELL_D = 0.36          # profundidad del pasa-ruedas desde la cara: W/2-0.36R
_DOME_NOSE, _DOME_TAIL = 0.08, 0.07   # fondo del domo de morro / zaga (R)
_DOME_F = (0.30, 0.56, 0.78, 0.92, 0.985)   # anillos del domo
_WIN_MARCO = 0.05                     # anchura del marco (unid. R)
_BELT = 2.30                          # línea de cintura (z/R)
# perfil lateral (x/R -> z/R): Fiat 500 / Topolino con techo abombado
_ZTOP = [(-4.58, 1.18), (-4.55, 1.24), (-4.48, 1.50), (-4.36, 1.86),
         (-4.15, 2.22), (-3.85, 2.62), (-3.45, 2.98), (-2.95, 3.22),
         (-2.40, 3.34), (-1.85, 3.36), (-1.35, 3.32), (-0.95, 3.22),
         (-0.62, 3.06), (-0.45, 2.90), (-0.05, 2.42), (0.18, 2.20),
         (0.35, 2.10), (0.70, 1.95), (1.05, 1.78), (1.30, 1.60),
         (1.42, 1.42), (1.48, 1.28), (1.50, 1.22)]
_ZBOT = [(-4.58, 1.12), (-4.55, 1.06), (-4.45, 0.94), (-4.20, 0.84),
         (-3.60, 0.80), (-1.00, 0.80), (0.60, 0.78), (1.20, 0.74),
         (1.42, 0.74), (1.50, 0.80)]
# semiancho relativo a (W/2 - 0.15R): pontón de anchura casi constante,
# esquinas redondeadas en planta en la zaga y morro estrechado
_WBODY = [(-4.58, 0.26), (-4.55, 0.40), (-4.48, 0.62), (-4.36, 0.80),
          (-4.15, 0.93), (-3.80, 0.99), (-3.40, 1.00), (-0.40, 1.00),
          (0.20, 0.97), (0.70, 0.88), (1.10, 0.74), (1.35, 0.60),
          (1.46, 0.50), (1.50, 0.45)]


# ================================================================ helpers ====
def _add_face(bm, vs, mi, smooth):
    try:
        fce = bm.faces.new(vs)
    except ValueError:
        return None
    fce.material_index = mi
    fce.smooth = smooth
    return fce


def _malla(nombre, bm, mats):
    """bmesh -> Mesh con normales recalculadas y los materiales del kit."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    me.validate()
    for mt in mats:
        me.materials.append(mt)
    return me


def _objeto(nombre, me, coll):
    ob = bpy.data.objects.new(nombre, me)
    coll.objects.link(ob)
    return ob


def _f_up(a_deg):
    """1 en la mitad superior de la rueda (bajo el guardabarros el collar de
    roca se rehunde al fondo del pasa-ruedas), 0 abajo (a ras de la pared)."""
    if a_deg > 180.0:
        return 0.0
    return _sstep((a_deg - 6.0) / 10.0) * (1.0 - _sstep((a_deg - 164.0) / 10.0))


def _frame(t):
    """Base ortonormal (u, v) perpendicular a la tangente t (v lo más
    vertical posible)."""
    t = t.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(t.dot(up)) > 0.9:
        up = Vector((0.0, 1.0, 0.0))
    u = t.cross(up).normalized()
    v = u.cross(t).normalized()
    return u, v


def _tubo(bm, pts, rad, mi, n=12, smooth=True):
    """Cáscara CERRADA barrida a lo largo de la polilínea `pts` (Vector):
    anillo elíptico (rad[i] = (ru, rv) en la base _frame de la tangente
    local) por punto y polos en los extremos. Los radios de los extremos
    deben ser pequeños (remate redondeado). Devuelve nada."""
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        u, v = _frame(t)
        ru, rv = rad[i]
        rings.append([bm.verts.new(p + u * (ru * math.cos(2 * math.pi * k / n))
                                   + v * (rv * math.sin(2 * math.pi * k / n)))
                      for k in range(n)])
    t0 = (pts[1] - pts[0]).normalized()
    t1 = (pts[-1] - pts[-2]).normalized()
    p0 = bm.verts.new(pts[0] - t0 * (0.35 * max(rad[0])))
    p1 = bm.verts.new(pts[-1] + t1 * (0.35 * max(rad[-1])))
    for k in range(n):
        k2 = (k + 1) % n
        _add_face(bm, (p0, rings[0][k2], rings[0][k]), mi, smooth)
        _add_face(bm, (p1, rings[-1][k], rings[-1][k2]), mi, smooth)
    for ra, rb in zip(rings, rings[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            _add_face(bm, (ra[k], ra[k2], rb[k2], rb[k]), mi, smooth)


def _capsula(bm, c, eje, semi, ru, rv, mi, q=3.0, n_l=9, n=12, smooth=True):
    """Barra de sección elíptica (ru x rv) y extremos redondeados
    (superelipse q; q=2 -> elipsoide) centrada en c a lo largo de `eje`."""
    eje = Vector(eje).normalized()
    pts, rad = [], []
    for i in range(n_l):
        t = -1.0 + 2.0 * (i + 0.5) / n_l
        f = max(1.0 - abs(t) ** q, 0.0) ** (1.0 / q)
        pts.append(Vector(c) + eje * (t * semi))
        rad.append((max(ru * f, 0.02), max(rv * f, 0.02)))
    _tubo(bm, pts, rad, mi, n, smooth)


def _revolucion(bm, c, eje, perfil, mats, n=20, smooth=True):
    """Cáscara cerrada de revolución alrededor de `eje` (por c): perfil =
    lista de (a, r) con a = cota axial y r = radio, de polo a polo (r=0 en
    los extremos); mats[i] = material del tramo i."""
    eje = Vector(eje).normalized()
    u, v = _frame(eje)
    rings = []
    for a, r in perfil[1:-1]:
        rings.append([bm.verts.new(Vector(c) + eje * a
                                   + u * (r * math.cos(2 * math.pi * k / n))
                                   + v * (r * math.sin(2 * math.pi * k / n)))
                      for k in range(n)])
    p0 = bm.verts.new(Vector(c) + eje * perfil[0][0])
    p1 = bm.verts.new(Vector(c) + eje * perfil[-1][0])
    for k in range(n):
        k2 = (k + 1) % n
        _add_face(bm, (p0, rings[0][k], rings[0][k2]), mats[0], smooth)
        _add_face(bm, (p1, rings[-1][k2], rings[-1][k]), mats[-1], smooth)
    for i, (ra, rb) in enumerate(zip(rings, rings[1:])):
        for k in range(n):
            k2 = (k + 1) % n
            _add_face(bm, (ra[k], rb[k], rb[k2], ra[k2]), mats[i + 1], smooth)


# =========================================================== disco-rueda ====
def _disco_rueda(R, W, alto_base, x_hub, side, so, n_spokes, m, detalle):
    """Disco CERRADO de una rueda (topología de montana_rueda): polo del buje
    -> anillos de la cara fósil -> neumático (superelipse) -> collar de roca
    (a ras de la pared abajo, rehundido bajo el guardabarros arriba) ->
    cilindro trasero -> polo trasero. side=+1: cara en y=+W/2; -1: en -W/2.
    detalle<1 reduce los anillos (ruedas secundarias). Devuelve bmesh."""
    N = n_spokes * m
    zc = R - alto_base
    y_face = 0.5 * W
    d_wall = -_Y_WALL * R
    d_well = -_WELL_D * R - 2.0
    d_back = d_well - 1.4
    u_rings = list(_U_RINGS)
    psi_rings = list(_PSI_RINGS) + [20.0, 12.0, 4.0]
    if detalle < 0.99:
        planos = [it for it in u_rings if not isinstance(it, tuple)]
        labio = [it for it in u_rings if isinstance(it, tuple)]
        planos = planos[0::2] + ([0.700] if planos[-1] != planos[0::2][-1]
                                 else [])
        u_rings = planos + labio[0::2] + [labio[-1]]
        psi_rings = list(_PSI_RINGS)[0::2] + [18.0, 10.0, 4.0]
    collar = [(1.015, -1.4, 0.0), (1.045, 0.9, -0.15), (1.12, 1.1, -0.35),
              (1.20, 0.5, -0.55), (1.225, -2.0, -0.8)]

    def W3(xr, d, zr):
        return (x_hub + xr, side * (y_face + d), zc + zr)

    bm = bmesh.new()
    rings, info = [], []
    radios0 = _radios_en(0.0, R, n_spokes, so)
    h0, _ = _talla(0.0, 0.0, 0.0, R, radios0, so)
    v_hub = bm.verts.new(W3(0.0, R * _perfil_base(0.0) + h0, 0.0))
    for item in u_rings:
        if isinstance(item, tuple):
            u, dbase = item
        else:
            u, dbase = item, _perfil_base(item)
        lam = 1.0 - _sstep((u - _RING_U1) / (_RIM_U1 - _RING_U1))
        radios = _radios_en(u, R, n_spokes, so)
        angs = _angulos_cara(u, R, n_spokes, m, lam, radios)
        r = u * R
        ring = []
        for a in angs:
            xr, zr = r * math.cos(a), r * math.sin(a)
            h, _es = _talla(u, xr, zr, R, radios, so)
            d = R * dbase + h
            if u > _FLOOR_U1 and dbase > -0.07:
                d += 0.30 * _n3(xr * 0.09 + so, zr * 0.09, 1.7) + \
                    0.10 * _n3(xr * 0.3, zr * 0.3 + so, 4.4)
            else:
                d += 0.10 * _n3(xr * 0.12 + so, zr * 0.12, 2.9)
            ring.append(bm.verts.new(W3(xr, d, zr)))
        rings.append(ring)
        info.append(("cara", (u, dbase)))
    angs_uni = _angulos_cara(1.0, R, n_spokes, m, 0.0, radios0)
    for psi in psi_rings:
        r0, y0 = _tyre_pt(psi, R)
        r1, y1 = _tyre_pt(psi + 0.5, R)
        r2, y2 = _tyre_pt(psi - 0.5, R)
        tr, ty = r2 - r1, y2 - y1
        tl = math.hypot(tr, ty) or 1.0
        nr, ny = -ty / tl, tr / tl
        ring = []
        for a in angs_uni:
            ca, sa = math.cos(a), math.sin(a)
            x, z = x_hub + r0 * ca, zc + r0 * sa
            yy = y_face + y0
            dn = (0.45 * _n3(x * 0.07 + so, yy * 0.07, z * 0.07) +
                  0.18 * _n3(x * 0.22, yy * 0.22 + so, z * 0.22 + 2.0))
            dn -= 1.5 * math.exp(-((psi - 102.0) / 4.0) ** 2)
            dn -= 1.3 * math.exp(-((psi - 74.0) / 4.0) ** 2)
            dn -= 1.0 * math.exp(-((psi - 48.0) / 4.0) ** 2)
            dn *= _sstep((psi - 2.0) / 12.0)          # rodadura limpia
            rr = r0 + nr * dn
            ring.append(bm.verts.new(W3(rr * ca, y0 + ny * dn, rr * sa)))
        rings.append(ring)
        info.append(("neu", psi))
    for i_c, (ur, dlo_off, dhi_off) in enumerate(collar):
        ring = []
        for a in angs_uni:
            ca, sa = math.cos(a), math.sin(a)
            a_deg = math.degrees(a) % 360.0
            fu = _f_up(a_deg)
            d_lo = d_wall + dlo_off
            if 0 < i_c < 4:
                d_lo += 0.35 * _n3(ur * ca * 3.0 + so, ur * sa * 3.0, 5.5)
            d = d_lo * (1.0 - fu) + (d_well + dhi_off) * fu
            kn = 0.003 if i_c == 0 else 0.008
            ur_up = 1.015 + (ur - 1.015) * 0.25          # arriba: collar corto
            ur_e = ur * (1.0 - fu) + ur_up * fu
            rr = ur_e * R * (1.0 + kn * _n3(a * 4.0 + so, ur * 7.0, 1.2))
            ring.append(bm.verts.new(W3(rr * ca, d, rr * sa)))
        rings.append(ring)
        info.append(("collar", i_c))
    for ur in (1.08, 0.50):
        ring = [bm.verts.new(W3(ur * R * math.cos(a), d_back,
                                ur * R * math.sin(a))) for a in angs_uni]
        rings.append(ring)
        info.append(("tras", ur))
    v_back = bm.verts.new(W3(0.0, d_back - 0.03 * R, 0.0))
    _caras_disco(bm, rings, info, v_hub, v_back, N, m, R, zc, d_wall, so,
                 side)
    return bm


def _caras_disco(bm, rings, info, v_hub, v_back, N, m, R, zc, d_wall, so,
                 side):
    """Caras del disco con material por zona: hueso en buje/collarín/radios/
    aro, hueco en el fondo, llanta clara, capas concéntricas del neumático,
    collar (estratos / oscuro en el pasa-ruedas) y trasera oscura."""
    band_h = _BAND_H * R
    spoke_k = (0, 1, 2, m - 3, m - 2, m - 1)

    def mat_cara(ua, ub, k):
        u_mid = 0.5 * (ua[0] + ub[0])
        d_mid = 0.5 * (ua[1] + ub[1])
        if u_mid < _HUB_U or _COL_U0 <= u_mid <= _COL_U1:
            return _M_HUESO
        if _RING_U0 <= u_mid <= _RING_U1:
            return _M_HUESO
        if _SPK_U0 <= u_mid <= _SPK_U1 and (k % m) in spoke_k:
            return _M_HUESO
        if u_mid < _FLOOR_U1 - 0.003 or d_mid < -0.0705:
            return _M_HUECO
        if u_mid > 0.685:
            return _M_CLARA
        return _M_CAL

    def mat_neu(pa, pb):
        p = 0.5 * (pa + pb)
        if p > 128.0:
            return _M_CLARA
        if p > 102.0:
            return _M_CAL
        if p > 89.0:
            return _M_CLARA
        if p > 74.0:
            return _M_CAL
        if p > 61.0:
            return _M_OSC
        if p > 48.0:
            return _M_CAL
        return _M_OSC

    r0 = rings[0]
    for k in range(N):
        _add_face(bm, (v_hub, r0[k], r0[(k + 1) % N]), _M_HUESO, False)
    y_face_abs = abs(r0[0].co.y)
    for i in range(len(rings) - 1):
        ra, rb = rings[i], rings[i + 1]
        ta, ua = info[i]
        tb, ub = info[i + 1]
        for k in range(N):
            k2 = (k + 1) % N
            vs = (ra[k], ra[k2], rb[k2], rb[k])
            if ta == "cara" and tb == "cara":
                mi = mat_cara(ua, ub, k)
                _add_face(bm, vs, mi, mi != _M_HUESO)
            elif ta == "cara" or (ta == "neu" and tb == "neu"):
                _add_face(bm, vs, mat_neu(ua if ta == "neu" else 131.0,
                                          ub if tb == "neu" else 131.0), True)
            elif tb == "tras" or ta == "tras":
                _add_face(bm, vs, _M_OSC, False)
            else:                      # neu->collar, collar->collar
                c = (ra[k].co + ra[k2].co + rb[k2].co + rb[k].co) * 0.25
                d = abs(c.y) - y_face_abs
                if d < d_wall - 2.5:
                    _add_face(bm, vs, _M_OSC, False)      # en el pasa-ruedas
                elif ta == "neu" or ua == 0:
                    _add_face(bm, vs, _M_OSC, False)      # surco al pie
                else:
                    _add_face(bm, vs, _estrato_mat(
                        c.z, band_h, _fase_estrato(c.x, c.y, so)), False)
    rl = rings[-1]
    for k in range(N):
        _add_face(bm, (v_back, rl[(k + 1) % N], rl[k]), _M_OSC, False)


# ============================================================= carrocería ====
def _q_top(xr):
    """Exponente de la superelipse arriba: hombros redondeados, capó más
    redondo aún."""
    return 2.6 - 0.4 * _sstep((xr - 0.3) / 0.7)


_Q_BOT = 3.6


def _seccion_cuerpo(t, w, zb, zt, q_top, q_bot):
    """Punto (y, z) de la sección YZ: superelipse con exponente distinto
    arriba/abajo; t en [0,1) recorre el anillo desde el flanco +Y (t=0) por
    arriba (0.25), flanco -Y (0.5) y abajo (0.75); más puntos en flancos."""
    th = 2.0 * math.pi * t
    th = th - 0.15 * math.sin(2.0 * th)
    q = q_top if math.sin(th) >= 0.0 else q_bot
    zm, h = 0.5 * (zt + zb), 0.5 * (zt - zb)
    return w * _sq(math.cos(th), q), zm + h * _sq(math.sin(th), q)


# cristales (unid. R): ventanillas del flanco (x0, x1, z0, z1): custodia y
# puerta; parabrisas y luneta sobre el techo (x0, x1, semiancho en y).
# Esquinas de radio _RC_WIN y marco de _WIN_MARCO por fuera; son piezas
# Boolean (_ventanas): rebaje de 0.08R con fondo de cristal y marco de hueso
# saliente 0.06R, muestreadas por ray-cast sobre el loft.
_VENTANAS = ((-2.55, -1.88, 2.36, 2.96), (-1.62, -0.66, 2.36, 2.96))
_PARABRISAS = (-0.50, 0.10, 0.56)
_LUNETA = (-4.05, -3.45, 0.50)
_JUNTAS = (-0.745, -1.745)        # juntas de puerta (x/R): pilar A y B
_RC_WIN = 0.07                    # radio de las esquinas de los cristales (R)


def _estaciones_cuerpo(R):
    """Cotas x (unid. R) de las secciones: paso base 0.07R + estaciones en
    las juntas de puerta, morro y zaga finos; nunca dos a < 0.015R."""
    esp = set(round(xk, 3) for xk in _JUNTAS)
    for xk in (-4.58, -4.565, -4.545, 1.485, 1.50):
        esp.add(xk)
    xs = set(esp)

    def libre(xr):       # sin estación especial a < 0.02R (nada de slivers)
        return all(abs(xr - e) >= 0.02 for e in esp)

    for x0, x1, paso in ((-4.58, 1.50, 0.07), (1.30, 1.50, 0.035),
                         (-4.56, -4.30, 0.035)):
        x = x0
        while x < x1:
            xr = round(x, 3)
            if libre(xr):
                xs.add(xr)
            x += paso
    out = []
    for xr in sorted(xs):            # última red: nada a < 0.015R
        if not out or xr - out[-1] >= 0.015:
            out.append(xr)
    return out


def _desplaza_cuerpo(R, p, n, so):
    """Desplazamiento (m) a lo largo de la normal n en el punto p de la
    carrocería LISA: juntas de puerta y umbral (surcos) y grano suave de
    piedra (0.010R); sin estratos. Los cristales y marcos son piezas
    Boolean aparte (_ventanas)."""
    x, z = p.x / R, p.z / R
    d = 0.0
    if abs(n.y) > 0.55:                                # flancos
        for xk in _JUNTAS:                             # juntas de puerta
            gx = math.exp(-((x - xk) / 0.03) ** 2)
            gz = _sstep((z - 0.95) / 0.05) * (1.0 - _sstep((z - _BELT) / 0.05))
            d -= 0.035 * gx * gz
        # umbral: surco horizontal en z=0.98 entre las juntas (sobre el estribo)
        gz = math.exp(-((z - 0.98) / 0.03) ** 2)
        gx = _sstep((x - _JUNTAS[1]) / 0.04) * (1.0 - _sstep((x - _JUNTAS[0]) / 0.04))
        d -= 0.025 * gz * gx
    d += (0.010 * _n3(p.x * 0.05 + so, p.y * 0.05, p.z * 0.05) +
          0.005 * _n3(p.x * 0.16, p.y * 0.16 + so, p.z * 0.16))
    return d * R


def _domo(bm, ring, x_end, depth, sign):
    """Anillos de domo (elipsoide de fondo `depth`) que cierran el loft
    tras `ring` (en x_end) hacia sign*X, y el polo final."""
    yc = sum(v.co.y for v in ring) / len(ring)
    zc = sum(v.co.z for v in ring) / len(ring)
    out = []
    for f in _DOME_F:
        s = math.sqrt(max(1.0 - f * f, 0.0))
        out.append([bm.verts.new((x_end + sign * f * depth,
                                  yc + (v.co.y - yc) * s,
                                  zc + (v.co.z - zc) * s)) for v in ring])
    polo = bm.verts.new((x_end + sign * depth, yc, zc))
    return out, polo


def _carroceria(R, W, alto_base, so, n_ring=88):
    """Loft cerrado de la carrocería (estaciones X x anillo YZ) rematado con
    domos en morro y zaga, desplazado a lo largo de la normal (juntas de
    puerta y grano suave). Devuelve bmesh (un solo material: caliza)."""
    wmax = 0.5 * W - _Y_BODY * R
    xs = _estaciones_cuerpo(R)
    bm = bmesh.new()
    rings = []
    for xr in xs:
        w = wmax * max(_spline(_WBODY, xr), 0.05)
        zb = R * _spline(_ZBOT, xr)
        zt = max(R * _spline(_ZTOP, xr), zb + 0.04 * R)
        ring = []
        for k in range(n_ring):
            y, z = _seccion_cuerpo(k / n_ring, w, zb, zt, _q_top(xr), _Q_BOT)
            ring.append(bm.verts.new((xr * R, y, z)))
        rings.append(ring)
    cola, v_tail = _domo(bm, rings[0], xs[0] * R, _DOME_TAIL * R, -1.0)
    morro, v_nose = _domo(bm, rings[-1], xs[-1] * R, _DOME_NOSE * R, 1.0)
    rings = cola[::-1] + rings + morro
    r0, rl = rings[0], rings[-1]
    for k in range(n_ring):
        k2 = (k + 1) % n_ring
        _add_face(bm, (v_tail, r0[k2], r0[k]), _M_CAL, True)
        _add_face(bm, (v_nose, rl[k], rl[k2]), _M_CAL, True)
    for ra, rb in zip(rings, rings[1:]):
        for k in range(n_ring):
            k2 = (k + 1) % n_ring
            _add_face(bm, (ra[k], ra[k2], rb[k2], rb[k]), _M_CAL, True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    desp = {v: v.normal * _desplaza_cuerpo(R, v.co, v.normal, so)
            for v in bm.verts}
    for v, dv in desp.items():
        v.co += dv
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# =============================================================== ventanas ====
def _loop_rect(a0, a1, b0, b1, rc, paso):
    """Contorno 2D antihorario de un rectángulo de esquinas redondeadas:
    lista de ((a, b), (na, nb)) puntos y normales exteriores, ~paso."""
    pts = []

    def lado(p, q, nrm):
        n = max(1, int(round(math.hypot(q[0] - p[0], q[1] - p[1]) / paso)))
        for i in range(n):
            t = i / n
            pts.append(((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t), nrm))

    def esquina(c, ang0):
        n = max(2, int(round(0.5 * math.pi * rc / paso)))
        for i in range(n):
            a = math.radians(ang0) + 0.5 * math.pi * i / n
            pts.append(((c[0] + rc * math.cos(a), c[1] + rc * math.sin(a)),
                        (math.cos(a), math.sin(a))))

    lado((a0 + rc, b0), (a1 - rc, b0), (0.0, -1.0))
    esquina((a1 - rc, b0 + rc), -90.0)
    lado((a1, b0 + rc), (a1, b1 - rc), (1.0, 0.0))
    esquina((a1 - rc, b1 - rc), 0.0)
    lado((a1 - rc, b1), (a0 + rc, b1), (0.0, 1.0))
    esquina((a0 + rc, b1 - rc), 90.0)
    lado((a0, b1 - rc), (a0, b0 + rc), (-1.0, 0.0))
    esquina((a0 + rc, b0 + rc), 180.0)
    return pts


def _muestreo(tree, R, wmax, pts2d, modo, s=1.0):
    """Puntos 3D sobre el loft (ray-cast) y normales analíticas suaves para
    un contorno 2D: modo 'flanco' (a=x, b=z, lado s) o 'techo' (a=x, b=y)."""
    out = []
    for (a, b), _n2 in pts2d:
        if modo == "flanco":
            o, d = Vector((a * R, s * 3.0 * R, b * R)), Vector((0.0, -s, 0.0))
        else:
            o, d = Vector((a * R, b * R, 5.0 * R)), Vector((0.0, 0.0, -1.0))
        loc, nrm, _i, _d = tree.ray_cast(o, d, 8.0 * R)
        if loc is None:
            raise RuntimeError("montana_coche_v2: ventana fuera de la carrocería")
        if modo == "flanco":
            n = _n_flanco(R, wmax, a, b * R, s)
        else:
            e = 0.01 * R
            dzdx = (_z_techo(R, wmax, a + 0.01, b * R) - _z_techo(R, wmax, a - 0.01, b * R)) / (2 * e)
            dzdy = (_z_techo(R, wmax, a, b * R + e) - _z_techo(R, wmax, a, b * R - e)) / (2 * e)
            n = Vector((-dzdx, -dzdy, 1.0)).normalized()
        out.append((loc, n))
    return out


def _prisma(bm, ms, d_out, d_in, mi_fondo, mi_pared):
    """Prisma cerrado que sigue la superficie: de +d_out (fuera) a -d_in
    (dentro) a lo largo de la normal; fondo en abanico (material del
    cristal), paredes y tapa exterior con mi_pared. Se RESTA."""
    n = len(ms)
    c = sum((p for p, _n in ms), Vector()) / n
    nc = sum((nn for _p, nn in ms), Vector()).normalized()
    outer = [bm.verts.new(p + nn * d_out) for p, nn in ms]
    inner = [bm.verts.new(p - nn * d_in) for p, nn in ms]
    v_out = bm.verts.new(c + nc * d_out)
    v_in = bm.verts.new(c - nc * d_in)
    for k in range(n):
        k2 = (k + 1) % n
        _add_face(bm, (outer[k], outer[k2], inner[k2], inner[k]), mi_pared, False)
        _add_face(bm, (v_out, outer[k2], outer[k]), mi_pared, False)
        _add_face(bm, (v_in, inner[k], inner[k2]), mi_fondo, True)


def _marco(bm, mo, mi_, d_front, d_back, mi):
    """Anillo cerrado (género 1) entre el contorno exterior mo y el interior
    mi_ (mismo nº de puntos), de +d_front a -d_back por la normal. Se UNE."""
    n = len(mo)
    fo = [bm.verts.new(p + nn * d_front) for p, nn in mo]
    bo = [bm.verts.new(p - nn * d_back) for p, nn in mo]
    fi = [bm.verts.new(p + nn * d_front) for p, nn in mi_]
    bi = [bm.verts.new(p - nn * d_back) for p, nn in mi_]
    for k in range(n):
        k2 = (k + 1) % n
        _add_face(bm, (fo[k], fo[k2], fi[k2], fi[k]), mi, True)
        _add_face(bm, (bo[k], bo[k2], fo[k2], fo[k]), mi, False)
        _add_face(bm, (bi[k], bi[k2], bo[k2], bo[k]), mi, False)
        _add_face(bm, (fi[k], fi[k2], bi[k2], bi[k]), mi, False)


def _ventanas(R, W, tree):
    """Marcos (bmesh a UNIR, hueso) y rebajes (bmesh a RESTAR: paredes de
    hueso, fondo de cristal) de las 4 ventanillas, el parabrisas y la
    luneta, muestreados por ray-cast sobre el loft de la carrocería."""
    wmax = 0.5 * W - _Y_BODY * R
    mk = _WIN_MARCO
    paso = 0.045
    bm_m, bm_r = bmesh.new(), bmesh.new()
    ventanas = [("flanco", s, v) for s in (1.0, -1.0) for v in _VENTANAS]
    ventanas.append(("techo", 1.0, (_PARABRISAS[0], _PARABRISAS[1],
                                    -_PARABRISAS[2], _PARABRISAS[2])))
    ventanas.append(("techo", 1.0, (_LUNETA[0], _LUNETA[1], -_LUNETA[2], _LUNETA[2])))
    for modo, s, (a0, a1, b0, b1) in ventanas:
        rc = _RC_WIN if modo == "flanco" else 0.10
        interior = _loop_rect(a0, a1, b0, b1, rc, paso)
        exterior = [((a + na * mk, b + nb * mk), (na, nb))
                    for (a, b), (na, nb) in interior]
        rebaje = [((a + na * 0.006, b + nb * 0.006), (na, nb))
                  for (a, b), (na, nb) in interior]
        m_i = _muestreo(tree, R, wmax, interior, modo, s)
        m_o = _muestreo(tree, R, wmax, exterior, modo, s)
        m_r = _muestreo(tree, R, wmax, rebaje, modo, s)
        _marco(bm_m, m_o, m_i, 0.06 * R, 0.10 * R, _M_HUESO)
        _prisma(bm_r, m_r, 0.14 * R, 0.08 * R, _M_CRISTAL, _M_HUESO)
    return bm_m, bm_r


# ============================================================ pasa-ruedas ====
def _pasa_ruedas(R, W, alto_base, hubs_x, n=64):
    """Cilindros cerrados (uno por rueda y lado) a lo largo de Y que se
    RESTAN a carrocería y roca: radio _WELL_R, desde |y| = W/2 - _WELL_D
    (fondo del pasa-ruedas) hasta |y| = W/2 + 0.3R. bmesh (4 cáscaras)."""
    zc = R - alto_base
    rw = _WELL_R * R
    bm = bmesh.new()
    for xh in hubs_x:
        for side in (1.0, -1.0):
            y0 = side * (0.5 * W - _WELL_D * R)
            y1 = side * (0.5 * W + 0.30 * R)
            ra = [bm.verts.new((xh + rw * math.cos(2 * math.pi * k / n), y0,
                                zc + rw * math.sin(2 * math.pi * k / n)))
                  for k in range(n)]
            rb = [bm.verts.new((xh + rw * math.cos(2 * math.pi * k / n), y1,
                                zc + rw * math.sin(2 * math.pi * k / n)))
                  for k in range(n)]
            _add_face(bm, ra, _M_OSC, False)
            _add_face(bm, rb[::-1], _M_OSC, False)
            for k in range(n):
                k2 = (k + 1) % n
                _add_face(bm, (ra[k], ra[k2], rb[k2], rb[k]), _M_OSC, False)
    return bm


# =========================================================== guardabarros ===
# perfil de la ceja (rho/R desde el buje, dy/R respecto a la cara exterior):
# labio interior redondeado -> lomo plano -> caída redondeada -> dentro
_FEND_PERFIL = [(1.16, -0.10), (1.165, -0.045), (1.185, -0.012), (1.215, 0.0),
                (1.265, 0.0), (1.315, -0.010), (1.365, -0.040), (1.405, -0.085),
                (1.435, -0.145), (1.425, -0.20), (1.395, -0.215), (1.30, -0.22),
                (1.18, -0.20), (1.16, -0.16)]
# factor de EXTENSIÓN hacia dentro (hacia el capó) de cada punto del perfil:
# 0 = piel exterior (no se mueve), 1 = cara interior. El capó se estrecha
# (_WBODY 0.88 -> 0.45) y la cara interior por defecto (W/2 - 0.25R) queda
# fuera de él en casi todo el arco delantero; la aleta DELANTERA se prolonga
# _FEND_EXT*R hacia dentro (hombro redondeado) entre a0+8 y ~85 grados para
# morir en el flanco del capó en vez de dejar una ranura abierta tras el faro.
_FEND_K = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.35, 0.72, 1.0, 1.0,
           0.85)
_FEND_EXT = 0.30
_FEND_ANG = ((-2.0, 192.0), (-12.0, 125.0))  # (a0, a1) grados: delantera, trasera
_FEND_RHO_C = 1.19                           # radio al que colapsan los extremos


def _guardabarros(R, W, alto_base, so):
    """Pontones cerrados de las 4 aletas: la sección _FEND_PERFIL barrida
    alrededor del buje (holgura 0.16R sobre el neumático, ceja de 0.12R
    sobre el flanco, borde redondeado). La delantera arranca a -2 grados
    (a la altura del buje, no llega al suelo) y su cara interior se prolonga
    hacia el capó (_FEND_K/_FEND_EXT); los extremos colapsan en radio y
    anchura hacia un punto enterrado en la roca/carrocería. bmesh (4)."""
    zc = R - alto_base
    y_out = 0.5 * W - _Y_FEND * R
    bm = bmesh.new()
    for xh, (a0, a1), con_ext in ((0.0, _FEND_ANG[0], True),
                                  (_X_REAR * R, _FEND_ANG[1], False)):
        n_ang = int(round((a1 - a0) / 4.5))
        for side in (1.0, -1.0):
            rings = []
            for i in range(n_ang + 1):
                a = a0 + (a1 - a0) * i / n_ang
                fe = 0.25 + 0.75 * _sstep((a - a0) / 16.0) * _sstep((a1 - a) / 16.0)
                ext = 0.0
                if con_ext:
                    ext = _sstep((a - a0) / 8.0) * (1.0 - _sstep((a - 70.0) / 25.0))
                dy_end = -0.40 - _FEND_EXT * ext        # punto de colapso
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                ring = []
                for (rho, dy), k in zip(_FEND_PERFIL, _FEND_K):
                    dy -= _FEND_EXT * ext * k
                    dyy = dy_end + (dy - dy_end) * fe
                    rr = _FEND_RHO_C + (rho - _FEND_RHO_C) * fe
                    rr *= R * (1.0 + 0.004 * _n3(a * 0.05 + so, rho * 6.0, 2.0))
                    ring.append(bm.verts.new((xh + rr * ca, side * (y_out + dyy * R),
                                              zc + rr * sa)))
                rings.append(ring)
            npf = len(_FEND_PERFIL)
            tapas = [_add_face(bm, rings[0], _M_CAL, False),
                     _add_face(bm, rings[-1][::-1], _M_CAL, False)]
            for ra, rb in zip(rings, rings[1:]):
                for k in range(npf):
                    k2 = (k + 1) % npf
                    _add_face(bm, (ra[k], rb[k], rb[k2], ra[k2]), _M_CAL, True)
            tapas = [f for f in tapas if f is not None]
            if tapas:
                bmesh.ops.triangulate(bm, faces=tapas, quad_method="BEAUTY",
                                      ngon_method="BEAUTY")
    return bm


def _dy_fend(rho):
    """dy/R de la cara exterior de la aleta en rho/R (tramo exterior del
    perfil, interpolado); None fuera de la ceja."""
    ext = _FEND_PERFIL[:9]
    if rho < ext[0][0] or rho > ext[-1][0]:
        return None
    for (r0, d0), (r1, d1) in zip(ext, ext[1:]):
        if r0 <= rho <= r1:
            return d0 + (d1 - d0) * (rho - r0) / max(r1 - r0, 1e-6)
    return ext[-1][1]


# ============================================================ superficie ====
def _w_cuerpo(R, wmax, xr, z):
    """Semiancho (m) de la sección de la carrocería en la cota z (0 fuera)."""
    if xr < -4.57 or xr > 1.49:
        return 0.0
    w = wmax * max(_spline(_WBODY, xr), 0.05)
    zb = R * _spline(_ZBOT, xr)
    zt = max(R * _spline(_ZTOP, xr), zb + 0.04 * R)
    zm, h = 0.5 * (zt + zb), 0.5 * (zt - zb)
    s = (z - zm) / h
    if abs(s) >= 1.0:
        return 0.0
    q = _q_top(xr) if s >= 0.0 else _Q_BOT
    return w * (1.0 - abs(s) ** q) ** (1.0 / q)


def _z_techo(R, wmax, xr, y):
    """Cota (m) de la superficie superior de la carrocería en (x, y)."""
    w = wmax * max(_spline(_WBODY, xr), 0.05)
    zb = R * _spline(_ZBOT, xr)
    zt = max(R * _spline(_ZTOP, xr), zb + 0.04 * R)
    zm, h = 0.5 * (zt + zb), 0.5 * (zt - zb)
    s = min(abs(y) / w, 1.0)
    q = _q_top(xr)
    return zm + h * (1.0 - s ** q) ** (1.0 / q)


def _z_meet(R, xr):
    """Cota (m) donde el talud rocoso encuentra el flanco de la carrocería:
    justo sobre el vientre plano; None sin coche."""
    if xr < -4.57 or xr > 1.49:
        return None
    zb = R * _spline(_ZBOT, xr)
    zt = max(R * _spline(_ZTOP, xr), zb + 0.04 * R)
    return zb + 0.06 * (zt - zb)


# =============================================================== detalles ====
_FARO_PERFIL = [(0.15, 0.0), (0.146, 0.045), (0.135, 0.085), (0.115, 0.115),
                (0.085, 0.135), (0.05, 0.145), (0.02, 0.15), (0.03, 0.163),
                (0.055, 0.18), (0.055, 0.198), (0.03, 0.21), (-0.02, 0.212),
                (-0.10, 0.19), (-0.17, 0.12), (-0.20, 0.0)]
_FARO_MATS = [_M_CRISTAL] * 6 + [_M_HUESO] * 5 + [_M_CAL] * 3
_TAPA_PERFIL = [(0.14, 0.0), (0.13, 0.08), (0.10, 0.16), (0.07, 0.20),
                (0.065, 0.24), (0.06, 0.32), (0.045, 0.40), (0.02, 0.46),
                (0.0, 0.50), (-0.04, 0.51), (-0.09, 0.50), (-0.25, 0.45),
                (-0.30, 0.0)]
_TAPA_MATS = [_M_HUESO] * 4 + [_M_CLARA] * 5 + [_M_HUESO] + [_M_CAL] * 2


def _parachoques(bm, R, x0, z0, semi, curv, n=17, ru=0.060, rv=0.055):
    """Barra de piedra curvada en planta (parábola: los extremos retroceden
    `curv` R hacia la carrocería, es decir hacia x=0 sea cual sea el signo
    de x0), sección ru x rv (unid. R) redondeada."""
    pts, rad = [], []
    hacia = math.copysign(curv, x0)
    for i in range(n):
        t = -1.0 + 2.0 * i / (n - 1)
        f = max(1.0 - abs(t) ** 4.0, 0.0) ** 0.25
        pts.append(Vector((R * (x0 - hacia * t * t), R * semi * t, R * z0)))
        rad.append((max(ru * R * f, 0.4), max(rv * R * f, 0.4)))
    _tubo(bm, pts, rad, _M_CLARA, 12)      # caliza clara: pieza legible en sombra


def _detalles(R, W, alto_base, so):
    """Piezas cerradas (cáscaras disjuntas) que se UNEN a la carrocería:
    parachoques delantero y trasero, dos faros (domo de cristal + aro de
    hueso), retrovisores, tiradores de puerta, estribos y tapa de la rueda
    de repuesto en la zaga. bmesh."""
    wmax = 0.5 * W - _Y_BODY * R
    bm = bmesh.new()
    # delantero: extremos (y = +-0.54R, x = 0.96R) dentro del flanco del capó
    _parachoques(bm, R, 1.56, 0.90, 0.54, 0.60, ru=0.070, rv=0.065)
    # trasero: barra CORTA y gorda (0.09R) bajo la curva baja de la zaga
    # (x0 = -4.64, z0 = 1.06: solapa el domo y el vientre y asoma ~3 m tras
    # el polo del domo), no un listón flotando
    _parachoques(bm, R, -4.64, 1.06, 0.50, 0.36, ru=0.090, rv=0.090)
    for s in (1.0, -1.0):
        c = (1.44 * R, s * 0.30 * R, 1.30 * R)
        eje = Vector((0.92, s * 0.16, 0.36))
        perfil = [(a * R, r * R * (1.0 + 0.02 * _n3(a * 9.0 + so, r * 9.0, s)))
                  for a, r in _FARO_PERFIL]
        perfil[0] = (perfil[0][0], 0.0)
        perfil[-1] = (perfil[-1][0], 0.0)
        _revolucion(bm, c, eje, perfil, _FARO_MATS, 22)
        # vástago del retrovisor (la cabeza va en _retrovisores: se solapan)
        p0 = Vector((-0.42 * R, s * 0.79 * R, 2.33 * R))
        p1 = Vector((-0.36 * R, s * 0.90 * R, 2.40 * R))
        _capsula(bm, 0.5 * (p0 + p1), p1 - p0, 0.5 * (p1 - p0).length + 0.02 * R,
                 0.03 * R, 0.03 * R, _M_CAL, 2.5, 5, 8)
        # tirador de puerta (hueso) y estribo entre las aletas
        _capsula(bm, (-1.58 * R, s * (wmax + 0.012 * R), 2.15 * R), (1.0, 0.0, 0.0),
                 0.06 * R, 0.022 * R, 0.020 * R, _M_HUESO, 2.5, 7, 10)
        _capsula(bm, (-1.70 * R, s * 0.86 * R, 0.90 * R), (1.0, 0.0, 0.0),
                 0.50 * R, 0.07 * R, 0.045 * R, _M_CAL, 3.0, 11, 12)
    perfil = [(a * R, r * R) for a, r in _TAPA_PERFIL]
    _revolucion(bm, (-4.38 * R, 0.0, 1.78 * R), (-0.93, 0.0, 0.37), perfil,
                _TAPA_MATS, 28)
    return bm


def _retrovisores(R, W):
    """Cabezas de los retrovisores (elipsoides planos de hueso): operando
    aparte porque se solapan con su vástago. bmesh (2 cáscaras)."""
    bm = bmesh.new()
    for s in (1.0, -1.0):
        _capsula(bm, (-0.34 * R, s * 0.93 * R, 2.43 * R), (0.0, 1.0, 0.0),
                 0.09 * R, 0.035 * R, 0.075 * R, _M_HUESO, 2.0, 9, 12)
    return bm


# ================================================================= cortes ====
def _cinta(bm, pts, nrms, ancho, prof, mi):
    """Cinta cerrada (sección rectangular ancho x 2*prof) a lo largo de la
    polilínea `pts` con la normal local `nrms`: RESTADA a la malla talla un
    surco (grieta) de `ancho` y profundidad `prof`."""
    hw = 0.5 * ancho
    secs = []
    for i, p in enumerate(pts):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        n = nrms[i].normalized()
        b = n.cross(t).normalized()
        secs.append([bm.verts.new(p - b * hw - n * prof),
                     bm.verts.new(p + b * hw - n * prof),
                     bm.verts.new(p + b * hw + n * prof),
                     bm.verts.new(p - b * hw + n * prof)])
    _add_face(bm, secs[0][::-1], mi, False)
    _add_face(bm, secs[-1], mi, False)
    for sa, sb in zip(secs, secs[1:]):
        for k in range(4):
            k2 = (k + 1) % 4
            _add_face(bm, (sa[k], sa[k2], sb[k2], sb[k]), mi, False)


def _n_flanco(R, wmax, xr, z, s):
    """Normal exterior aproximada del flanco (lado s) en (x, z)."""
    zb = R * _spline(_ZBOT, xr)
    zt = max(R * _spline(_ZTOP, xr), zb + 0.04 * R)
    zm, h = 0.5 * (zt + zb), 0.5 * (zt - zb)
    w = wmax * max(_spline(_WBODY, xr), 0.05)
    y = _w_cuerpo(R, wmax, xr, z)
    q = _q_top(xr) if z >= zm else _Q_BOT
    ny = q * (max(y, 1e-3) / w) ** (q - 1.0) / w
    nz = q * (abs(z - zm) / h) ** (q - 1.0) / h * (1.0 if z >= zm else -1.0)
    return Vector((0.0, s * ny, nz)).normalized()


# grietas: ("techo", [(x, y)...]) | ("flanco", lado, [(x, z)...]) |
#          ("aleta", buje, lado, [(rho, grados)...])
_GRIETAS = [
    ("techo", [(0.45, -0.25), (0.62, -0.12), (0.78, -0.18), (0.98, -0.05)]),
    ("techo", [(0.30, 0.30), (0.55, 0.38), (0.75, 0.30), (0.92, 0.36)]),
    ("techo", [(-2.90, -0.35), (-2.65, -0.15), (-2.35, -0.20), (-2.05, 0.05)]),
    ("techo", [(-1.60, 0.45), (-1.35, 0.30), (-1.05, 0.38), (-0.85, 0.20)]),
    ("techo", [(-2.25, 0.40), (-2.02, 0.48), (-1.78, 0.44), (-1.68, 0.50)]),
    ("techo", [(-3.55, 0.64), (-3.80, 0.68), (-4.05, 0.60)]),
    ("techo", [(-1.30, -0.30), (-1.08, -0.38), (-0.80, -0.34)]),
    ("techo", [(-4.15, -0.62), (-4.30, -0.55), (-4.45, -0.42)]),
    ("flanco", 1.0, [(-2.52, 2.26), (-2.38, 2.12), (-2.30, 1.98)]),
    ("flanco", 1.0, [(-1.30, 3.10), (-1.10, 3.14), (-0.85, 3.11)]),
    ("flanco", 1.0, [(-3.30, 2.92), (-3.10, 2.98), (-2.85, 2.96)]),
    ("flanco", -1.0, [(-2.48, 2.24), (-2.36, 2.08), (-2.26, 1.96)]),
    ("flanco", -1.0, [(-1.55, 3.10), (-1.30, 3.14), (-1.05, 3.11)]),
    ("aleta", 0.0, 1.0, [(1.18, 62.0), (1.26, 66.0), (1.34, 68.0), (1.42, 73.0)]),
    ("aleta", 0.0, 1.0, [(1.20, 140.0), (1.30, 136.0), (1.41, 131.0)]),
    ("aleta", _X_REAR, 1.0, [(1.19, 95.0), (1.27, 100.0), (1.36, 108.0), (1.43, 112.0)]),
    ("aleta", 0.0, -1.0, [(1.19, 105.0), (1.28, 110.0), (1.38, 113.0)]),
    ("aleta", _X_REAR, -1.0, [(1.20, 70.0), (1.30, 66.0), (1.41, 62.0)]),
]
# desconchones: ("techo", x, y) | ("flanco", lado, x, z) | ("aleta", buje, lado, rho, grados)
_DESCONCHONES = [("techo", -2.55, 0.15), ("techo", 0.85, -0.30),
                 ("techo", -3.35, -0.60), ("flanco", 1.0, -2.18, 2.10),
                 ("aleta", 0.0, 1.0, 1.30, 100.0), ("aleta", _X_REAR, 1.0, 1.32, 78.0),
                 ("techo", -2.80, 0.52)]


def _cortes(R, W, alto_base, so, seed, lv=1.0):
    """Cáscaras disjuntas que se RESTAN al final: boca del parachoques
    (hueco oscuro), grietas finas (cintas de 0.25-0.4 m, piedra oscura) y
    desconchones (casquetes de piedra clara). lv = lado visible (+1/-1):
    las grietas y desconchones de flanco/aleta se espejan en Y. bmesh."""
    rng = random.Random(seed * 7 + 3)
    wmax = 0.5 * W - _Y_BODY * R
    zc = R - alto_base
    y_out = 0.5 * W - _Y_FEND * R
    bm = bmesh.new()
    _capsula(bm, (1.60 * R, 0.0, 1.035 * R), (0.0, 1.0, 0.0), 0.23 * R,
             0.10 * R, 0.045 * R, _M_HUECO, 3.5, 11, 14)
    prof = 0.03 * R

    def jit():
        return rng.uniform(-0.015, 0.015) * R

    for g in _GRIETAS:
        pts, nrms = [], []
        if g[0] == "techo":
            for x, y in g[1]:
                xr, ym = x + jit() / R, y * R + jit()
                pts.append(Vector((xr * R, ym, _z_techo(R, wmax, xr, ym))))
                nrms.append(Vector((0.0, 0.0, 1.0)))
        elif g[0] == "flanco":
            s = g[1] * lv
            for x, z in g[2]:
                xr, zm = x + jit() / R, z * R + jit()
                pts.append(Vector((xr * R, s * _w_cuerpo(R, wmax, xr, zm), zm)))
                nrms.append(_n_flanco(R, wmax, xr, zm, s))
            n_med = sum(nrms, Vector()).normalized()   # sin torsión de la cinta
            nrms = [n_med for _ in nrms]
        else:
            xh, s = g[1] * R, g[2] * lv
            for rho, ang in g[3]:
                rho = min(max(rho + jit() / R, 1.17), 1.43)
                a = math.radians(ang + jit() / R * 30.0)
                dy = _dy_fend(rho) or 0.0
                pts.append(Vector((xh + rho * R * math.cos(a), s * (y_out + dy * R),
                                   zc + rho * R * math.sin(a))))
                nrms.append(Vector((0.0, s, 0.0)))
        _cinta(bm, pts, nrms, rng.uniform(0.25, 0.40), prof, _M_OSC)
    for d in _DESCONCHONES:
        if d[0] == "techo":
            xr, ym = d[1], d[2] * R
            c = Vector((xr * R, ym, _z_techo(R, wmax, xr, ym) + 0.3 * 0.03 * R))
            _capsula(bm, c, (1.0, 0.0, 0.0), 0.07 * R, 0.05 * R, 0.03 * R,
                     _M_CLARA, 2.0, 7, 10)
        elif d[0] == "flanco":
            s, xr, zm = d[1] * lv, d[2], d[3] * R
            c = Vector((xr * R, s * (_w_cuerpo(R, wmax, xr, zm) + 0.3 * 0.03 * R), zm))
            _capsula(bm, c, (1.0, 0.0, 0.0), 0.06 * R, 0.03 * R, 0.045 * R,
                     _M_CLARA, 2.0, 7, 10)
        else:
            xh, s, rho, ang = d[1] * R, d[2] * lv, d[3], math.radians(d[4])
            dy = _dy_fend(rho) or 0.0
            c = Vector((xh + rho * R * math.cos(ang),
                        s * (y_out + dy * R + 0.3 * 0.03 * R),
                        zc + rho * R * math.sin(ang)))
            _capsula(bm, c, (1.0, 0.0, 0.0), 0.06 * R, 0.03 * R, 0.05 * R,
                     _M_CLARA, 2.0, 7, 10)
    return bm


# =================================================================== roca ====
# cota superior de la roca (x/R -> z/R): sube dentro de la carrocería, baja a
# 0.55R en el arco entre ruedas, envuelve el morro y cae al mar por la zaga
# en REPISAS escalonadas
_ZROCK = [(-6.10, -1.25), (-5.85, -0.90), (-5.60, -0.45), (-5.42, 0.04),
          (-5.28, 0.06), (-5.12, 0.28), (-4.98, 0.47), (-4.82, 0.50),
          (-4.68, 0.72), (-4.52, 0.86), (-4.30, 0.98), (-4.05, 1.08),
          (-3.70, 1.15), (-2.30, 1.15), (-2.17, 1.10), (-2.02, 0.55),
          (-1.38, 0.55), (-1.23, 1.10), (-1.10, 1.15), (0.90, 1.12),
          (1.20, 0.92), (1.42, 0.77), (1.52, 0.42), (1.58, -0.30),
          (1.64, -1.25)]


def _lin(pts, x):
    """Interpolación lineal suavizada (smoothstep por tramo): sin sobre-
    oscilaciones para perfiles con escalones."""
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * _sstep((x - x0) / (x1 - x0))
    return pts[-1][1]


def _roca(R, W, alto_base, z_fondo, so, talud_deg, n_ring=84):
    """Loft cerrado de la roca (secciones YZ a lo largo de X): zócalo en
    |y| = W/2 - 0.09R con PIE EN TALUD (+2.5 m en z=0), talud hasta el
    flanco de la carrocería (y por dentro de ella, oculto), cresta redondeada
    donde queda al aire (arco entre ruedas, zaga en repisas, morro) y FALDA
    bajo z=-4 con talud `talud_deg` sólo para x < -1.3R. Relieve: ridged +
    bloques + estratos (amortiguado junto a las ruedas, nulo dentro del
    coche). Clamp de zona prohibida. Se corta por z_fondo y se tapa."""
    wmax = 0.5 * W - _Y_BODY * R
    w0 = 0.5 * W - _Y_WALL * R
    y_lim = 0.5 * W + 2.3
    zc = R - alto_base
    tan_t = math.tan(math.radians(talud_deg))
    band_h = _BAND_H * R
    cw, ch = 0.22 * R, 0.50 * R
    y_ap = 0.5 * W - _Y_FEND * R - 0.24 * R   # delantal: hasta la cara interior
    hubs = (0.0, _X_REAR * R)                  # de la aleta delantera (- margen)
    xs = set()
    x = -6.10
    while x < 1.64:
        xs.add(round(x, 3))
        x += 0.08
    for xk in (-2.17, -2.02, -1.38, -1.23, -4.98, -4.82, -5.42, -5.28):
        for dx in (-0.03, 0.03):
            xs.add(round(xk + dx, 3))
    xs.add(1.64)
    xs = sorted(xs)

    def flare(xm):
        return _sstep((-1.30 * R - xm) / (0.35 * R))

    def w_roca(xm, z, z_top, oculto):
        xr = xm / R
        w = w0 * (1.0 + 0.04 * _n3(xm * 0.02 + so, z * 0.02, 8.1))
        if xr > 1.0:                        # proa del zócalo: planta redondeada
            w *= math.sqrt(max(1.0 - ((xr - 1.0) / 0.70) ** 2, 0.04))
        w += 2.5 * _sstep((0.35 * R - z) / (0.35 * R))     # pie en talud
        if z < -4.0:
            w += (-4.0 - z) * tan_t * flare(xm)
        z1 = 0.35 * R
        if z <= z1:
            return w
        zm = _z_meet(R, xr)
        if oculto:                          # la roca se esconde en el coche
            w_meet = _w_cuerpo(R, wmax, xr, zm) + 1.5
            if xr > 0.95:       # delantal del morro: repisa de roca bajo la aleta
                w_ap = y_ap * _sstep((xr - 0.95) / 0.12)
                if xr > 1.0:
                    w_ap *= math.sqrt(max(1.0 - ((xr - 1.0) / 0.70) ** 2, 0.04))
                w_meet = max(w_meet, w_ap)
            if z <= zm:
                return w + (w_meet - w) * _sstep((z - z1) / (zm - z1))
            return max(_w_cuerpo(R, wmax, xr, z) - 1.5, 2.0)
        w_top = 0.55 * w                    # cresta al aire, redondeada
        return w + (w_top - w) * _sstep((z - z1) / max(z_top - z1, 1.0))

    bm = bmesh.new()
    rings = []
    desp = {}
    for xr in xs:
        xm = xr * R
        kn = _sstep((xr - 0.85) / 0.35)          # proa del zócalo (morro)
        z_top0 = R * _lin(_ZROCK, xr)
        z_top = z_top0 + kn * 0.07 * R * _n3(xm * 0.07 + so, 2.2, 5.5)
        z_low = min(z_fondo - 0.30 * (z_top - z_fondo), z_top - 0.25 * R)
        zmid, H = 0.5 * (z_top + z_low), 0.5 * (z_top - z_low)
        zm = _z_meet(R, xr)
        oculto = zm is not None and z_top0 > zm - 0.5   # sin ruido: sin parpadeo
        oculto_desde = zm + 1.0 if oculto else 1e9
        # delantal (x 1.0-1.45R): sección CAJEADA (q alto) para que la repisa
        # bajo la aleta delantera sea plana y ancha hasta z ~ 0.8R; la punta
        # de la proa (x > 1.45R) vuelve a ser redondeada
        kbox = _sstep((xr - 0.98) / 0.10) * (1.0 - _sstep((xr - 1.40) / 0.08))
        q = (6.0 - 3.2 * kn) * (1.0 - kbox) + 8.0 * kbox
        ring = []
        for k in range(n_ring):
            th = 2.0 * math.pi * (k + 0.5) / n_ring
            cy, sz = _sq(math.cos(th), q), _sq(math.sin(th), q)
            z0 = zmid + H * sz
            w_here = w_roca(xm, max(z0, z_fondo), z_top, oculto)
            y0 = cy * w_here
            amp = _sstep((w_here - 4.0) / 8.0)       # sin relieve en secciones finas
            if kn > 0.0:      # proa: bajo tierra (z<0) sin relieve (se estrecha
                amp *= max(1.0 - kn, _sstep(z0 / (0.2 * R)))   # muy deprisa)
            # parte alta de la repisa del delantal: lisa (la punta de la aleta
            # muere dentro de ella con margen de ~1 m)
            amp *= 1.0 - kbox * _sstep((z0 - 0.45 * R) / (0.18 * R))
            if abs(y0) > 0.5 * W - 0.30 * R:      # sólo junto a las ruedas
                for xh in hubs:
                    amp = min(amp, 0.25 + 0.75 * _sstep(
                        (math.hypot(xm - xh, z0 - zc) - 1.30 * R) / (0.25 * R)))
            amp *= 1.0 + 0.7 * _sstep((-2.0 - z0) / 8.0)   # falda: más relieve
            if z0 > oculto_desde:
                amp = 0.0
            zq = max(z0, z_fondo)
            D = amp * (_ridged(xm, y0, zq, so) + 1.6 * _celda(xm, y0, zq, so, cw, ch))
            if kn > 0.0:
                Dn = amp * 1.3 * (_ridged(xm, y0, zq, so + 2.0, 1.6) + 0.8 * _celda(
                    xm, y0, zq, so + 5.0, 0.26 * R, 0.10 * R))
                D = D * (1.0 - kn) + Dn * kn
            D += amp * 1.8 * math.tanh(2.5 * _onda_estrato(zq, band_h, 0.0))
            cap = 5.0 - 1.5 * kn
            D = cap * math.tanh(D / cap)
            if z0 > 0.5 * R and z0 > oculto_desde - 3.0:
                D = 0.0
            dv = Vector((0.0, cy, sz * _sstep((z0 - z_fondo - 2.0) / 6.0)))
            if dv.length < 1e-6:
                dv = Vector((0.0, 0.0, 1.0))
            dv.normalize()
            v = bm.verts.new((xm, y0, z0))
            desp[v] = (D, dv, kn * _sstep((z0 - z_fondo - 8.0) / 10.0))
            ring.append(v)
        rings.append(ring)
    p0 = bm.verts.new((xs[0] * R - 0.05 * R, 0.0, z_fondo - 0.3 * R))
    p1 = bm.verts.new((xs[-1] * R + 0.05 * R, 0.0, z_fondo - 0.3 * R))
    for k in range(n_ring):
        k2 = (k + 1) % n_ring
        _add_face(bm, (p0, rings[0][k2], rings[0][k]), _M_OSC, False)
        _add_face(bm, (p1, rings[-1][k], rings[-1][k2]), _M_OSC, False)
    caras = []
    for ra, rb in zip(rings, rings[1:]):
        for k in range(n_ring):
            k2 = (k + 1) % n_ring
            fce = _add_face(bm, (ra[k], ra[k2], rb[k2], rb[k]), _M_CAL, False)
            if fce is not None:
                caras.append(fce)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for v, (D, dv, kx) in desp.items():
        if D != 0.0:
            dr = dv * (1.0 - kx) + v.normal * kx
            if dr.length < 1e-6:
                dr = dv
            v.co += dr.normalized() * D
        if -1.3 * R <= v.co.x <= 1.5 * R and abs(v.co.y) > y_lim:
            v.co.y = math.copysign(y_lim, v.co.y)          # zona prohibida
    # cortes horizontales en cada borde de media banda (fase 0): el cambio
    # de color de los estratos es una arista recta, no un ajedrezado
    z_max = max(v.co.z for v in bm.verts)
    k = 0
    while band_h * (0.5 * k - 0.25) < z_max:
        zk = band_h * (0.5 * k - 0.25)
        if zk > -2.0:
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, dist=0.15,
                                   plane_co=(0.0, 0.0, zk), plane_no=(0.0, 0.0, 1.0),
                                   use_snap_center=False, clear_outer=False,
                                   clear_inner=False)
        k += 1
    for fce in bm.faces:
        c = fce.calc_center_median()
        fce.smooth = False
        if c.z < -2.0:
            fce.material_index = _M_OSC
        else:
            fce.material_index = _estrato_mat(c.z, band_h, 0.0)
    _cerrar_en(bm, z_fondo)
    return bm


def _cerrar_en(bm, z_plane):
    """Corta por z=z_plane, elimina lo de debajo y tapa con un n-gon
    triangulado (base plana). Devuelve nº de aristas no manifold."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=0.05,
                           plane_co=(0.0, 0.0, z_plane),
                           plane_no=(0.0, 0.0, 1.0), use_snap_center=False,
                           clear_outer=False, clear_inner=False)
    bajo = [v for v in bm.verts if v.co.z < z_plane - 1e-4]
    if bajo:
        bmesh.ops.delete(bm, geom=bajo, context="VERTS")
    borde = [e for e in bm.edges if e.is_boundary]
    res = bmesh.ops.holes_fill(bm, edges=borde, sides=0)
    tapa = res.get("faces", [])
    for fce in tapa:
        fce.material_index = _M_OSC
        fce.smooth = False
    if tapa:
        bmesh.ops.triangulate(bm, faces=tapa, quad_method="BEAUTY",
                              ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return sum(1 for e in bm.edges if len(e.link_faces) != 2)


# ================================================================ bloques ====
def _pedrusco(bm, c, r, rng, mi, n_u=8, n_v=5):
    """Bloque caído: esfera facetada (n_u x n_v) con radio irregular y
    achatada, cerrada. Sombreado plano."""
    rows = []
    for i in range(1, n_v):
        phi = math.pi * i / n_v
        row = []
        for k in range(n_u):
            th = 2.0 * math.pi * k / n_u + 0.3 * rng.random()
            rr = r * (0.70 + 0.55 * rng.random())
            row.append(bm.verts.new((c.x + rr * math.sin(phi) * math.cos(th),
                                     c.y + rr * math.sin(phi) * math.sin(th),
                                     c.z + 0.72 * rr * math.cos(phi))))
        rows.append(row)
    top = bm.verts.new((c.x + 0.2 * r * rng.uniform(-1, 1),
                        c.y + 0.2 * r * rng.uniform(-1, 1), c.z + 0.72 * r))
    bot = bm.verts.new((c.x, c.y, c.z - 0.72 * r))
    for k in range(n_u):
        k2 = (k + 1) % n_u
        _add_face(bm, (top, rows[0][k], rows[0][k2]), mi, False)
        for i in range(len(rows) - 1):
            _add_face(bm, (rows[i][k], rows[i + 1][k], rows[i + 1][k2],
                           rows[i][k2]), mi, False)
        _add_face(bm, (bot, rows[-1][k2], rows[-1][k]), mi, False)


# bloques caídos: (x/R, y/R, r/R); z por ray-cast sobre la roca
_BLOQUES = [(-1.75, 0.93, 0.08), (-2.06, 0.96, 0.06), (-1.45, 0.96, 0.05),
            (1.32, 0.86, 0.08), (1.50, 0.70, 0.07), (1.62, 0.40, 0.09),
            (-1.85, -0.95, 0.07), (1.40, -0.80, 0.07), (1.58, -0.50, 0.08),
            (-4.95, 0.50, 0.11), (-5.25, -0.30, 0.10), (-5.05, -0.72, 0.09),
            (-5.50, 0.22, 0.13), (-5.35, 0.62, 0.09), (-4.80, -0.55, 0.08),
            (-5.62, -0.42, 0.11), (-4.72, 0.86, 0.07), (-5.15, 0.88, 0.08)]


def _bloques(R, W, tree, seed):
    """Bloques caídos apoyados por ray-cast sobre la roca (hundidos un 30 %
    de su radio); fuera de los pasa-ruedas y dentro de la zona permitida.
    bmesh (cáscaras disjuntas)."""
    rng = random.Random(seed * 13 + 5)
    y_lim = 0.5 * W + 2.3
    bm = bmesh.new()
    for xr, yr, rr in _BLOQUES:
        x, y, r = xr * R, yr * R, rr * R
        if -1.3 * R <= x <= 1.5 * R:
            y = math.copysign(min(abs(y), y_lim - r - 0.3), y)
        loc, nrm, _i, _d = tree.ray_cast(Vector((x, y, 4.0 * R)),
                                         Vector((0.0, 0.0, -1.0)), 8.0 * R)
        if loc is None or loc.z < -5.0:
            continue
        c = Vector((x, y, loc.z - 0.30 * r))
        _pedrusco(bm, c, r, rng, _M_CAL if rng.random() < 0.6 else _M_CLARA)
    return bm


# ============================================================== ensamblaje ==
def _fusionar(bms, nombre, mats):
    """Varios bmesh cerrados -> un Mesh con varias cáscaras disjuntas."""
    out = bmesh.new()
    for bm in bms:
        tmp = bpy.data.meshes.new(nombre + "_tmp")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(tmp)
        bm.free()
        out.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    return _malla(nombre, out, mats)


def _boolean_cadena(base, ops, solver):
    """Aplica en cadena modificadores Boolean (operation, objeto) sobre
    `base`, evalúa el depsgraph y devuelve un Mesh nuevo (sin bpy.ops).
    REQUISITO: `base` y los operandos deben estar en el view layer activo
    (build() los linka a bpy.context.scene.collection); si el depsgraph no
    los evalúa se lanza RuntimeError en vez de devolver la roca sola."""
    for i, (op, ob) in enumerate(ops):
        md = base.modifiers.new("mc_bool_%d" % i, "BOOLEAN")
        md.operation = op
        md.solver = solver
        md.object = ob
        md.material_mode = "INDEX"
        if solver == "EXACT":
            md.use_self = False
            md.use_hole_tolerant = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = base.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True,
                                         depsgraph=dg)
    for md in list(base.modifiers):
        base.modifiers.remove(md)
    if ev is base or len(me.polygons) == len(base.data.polygons):
        bpy.data.meshes.remove(me)
        raise RuntimeError(
            "montana_coche_v2: el depsgraph no evaluó los Booleans (¿'%s' fuera "
            "del view layer activo o colección excluida?)" % base.name)
    return me


def _pulir(me):
    """Limpieza final: solapas de grosor nulo fuera, micro-agujeros del
    boolean tapados y vértices casi coincidentes fundidos sólo si hay borde
    abierto, normales coherentes, aristas vivas (>30 grados) con normales
    partidas. Devuelve nº de aristas no manifold."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.index_update()
    grupos = {}
    for fce in bm.faces:
        grupos.setdefault(frozenset(v.index for v in fce.verts), []).append(fce)
    dup = [fce for fs in grupos.values() if len(fs) > 1 for fce in fs]
    if dup:
        bmesh.ops.delete(bm, geom=dup, context="FACES_ONLY")
        sueltas = [e for e in bm.edges if not e.link_faces]
        if sueltas:
            bmesh.ops.delete(bm, geom=sueltas, context="EDGES")
    for _ in range(3):
        bv = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
        if not bv:
            break
        bmesh.ops.remove_doubles(bm, verts=bv, dist=0.05)
        borde = [e for e in bm.edges if e.is_boundary]
        if not borde:
            break
        res = bmesh.ops.holes_fill(bm, edges=borde, sides=16)
        for fce in res.get("faces", []):
            fce.material_index = _M_OSC
            fce.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    lim = math.radians(30.0)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    nm = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bm.to_mesh(me)
    bm.free()
    me.validate()
    me.update()
    return nm


# ============================================================ vegetación ====
def _vegetacion(parent_collection, roca_obj, R, W, alto_base, tree, seed,
                n_max=44):
    """Matas low-poly apoyadas por ray-cast sobre la malla final: techo y
    capó (pocas: es un coche), lomo del arco entre ruedas, REPISAS de la
    zaga (con pinos), pie del zócalo +Y (entre bloques) y delantal del
    morro. Malla aparte MCOCHE_veg."""
    rng = random.Random(seed * 91 + 101)
    zc = R - alto_base
    bm = bmesh.new()
    placed = []
    cnt = [0]
    hubs = ((0.0, zc), (_X_REAR * R, zc))

    def sonda(x, y, z_desde):
        loc, nrm, _i, _d = tree.ray_cast(Vector((x, y, z_desde)),
                                         Vector((0.0, 0.0, -1.0)), 8.0 * R)
        return loc, nrm

    def valido(loc, nrm, min_nz):
        if loc is None or nrm.z < min_nz or loc.z < -1.0:
            return False
        if loc.x < -4.45 * R and loc.z > 0.93 * R:   # parachoques trasero / domo
            return False
        if abs(loc.y) > 0.5 * W - 0.5 * R:              # caras de las ruedas
            for xh, zh in hubs:
                if math.hypot(loc.x - xh, loc.z - zh) < 1.30 * R:
                    return False
        return not any((loc - p).length < 4.0 for p in placed)

    def grupo(x0, x1, y0, y1, n_here, r_rng, z_desde, min_nz=0.4, pinos=0,
              z_min=-1.0):
        n = 0
        for _ in range(40):
            if n >= n_here or cnt[0] >= n_max:
                break
            loc, nrm = sonda(rng.uniform(x0, x1), rng.uniform(y0, y1), z_desde)
            if not valido(loc, nrm, min_nz) or loc.z < z_min:
                continue
            placed.append(loc.copy())
            r = rng.uniform(*r_rng)
            _blob(bm, loc + nrm * (0.15 * r), r, 0.55, rng,
                  0 if rng.random() < 0.65 else 1)
            cnt[0] += 1
            n += 1
        for _ in range(pinos):
            for _t in range(14):
                loc, nrm = sonda(rng.uniform(x0, x1), rng.uniform(y0, y1),
                                 z_desde)
                if valido(loc, nrm, 0.6) and loc.z > z_min:
                    placed.append(loc.copy())
                    _pino(bm, loc, rng.uniform(12.0, 17.0), rng,
                          0 if rng.random() < 0.5 else 1, 2)
                    break

    wb = 0.5 * W - _Y_BODY * R
    grupo(-2.9 * R, -1.6 * R, -0.5 * wb, 0.5 * wb, 3, (2.4, 3.6), 3.6 * R)
    grupo(-2.0 * R, -1.4 * R, -0.8 * wb, 0.8 * wb, 6, (2.8, 4.5), 1.0 * R)
    grupo(-5.5 * R, -4.6 * R, -0.9 * wb, 0.9 * wb, 12, (3.0, 5.2), 1.6 * R,
          pinos=4, z_min=1.0)
    for s in (1.0, -1.0):                   # pie del zócalo, ambos lados
        grupo(-2.2 * R, -1.3 * R, s * (wb + 1.0), s * (wb + 6.0), 4, (2.5, 3.8),
              0.7 * R, min_nz=0.3, z_min=0.5)
        grupo(-4.7 * R, -4.2 * R, s * (wb - 1.0), s * (wb + 5.0), 3, (2.5, 3.6),
              0.9 * R, min_nz=0.3, z_min=0.5)
    grupo(1.25 * R, 1.62 * R, -0.8 * wb, 0.8 * wb, 5, (2.5, 3.8), 0.9 * R,
          z_min=0.5)                        # delantal del morro
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("MCOCHE_veg")
    bm.to_mesh(me)
    bm.free()
    me.validate()
    for mt in _mats_veg():
        me.materials.append(mt)
    ob = bpy.data.objects.new("MCOCHE_veg", me)
    parent_collection.objects.link(ob)
    ob.parent = roca_obj
    return ob


# ================================================================= build ====
def build(parent_collection, radio=40.0, ancho=78.0, alto_base=12.0,
          z_fondo=-45.0, seed=0, con_vegetacion=True, **params):
    """Montaña-coche completa (v2). Devuelve la malla raíz MCOCHE_roca (única
    y cerrada); la vegetación va en el hijo MCOCHE_veg.
    params: n_radios=12, segmentos_por_radio=7, talud_deg=35, solver=
    "MANIFOLD", detalle_secundario=0.6 y lado_visible=+1 (lado Y que verá el
    jugador: la rueda delantera de ese lado lleva detalle 1.0 y las grietas/
    desconchones de flanco y aleta se colocan en él; -1 los espeja).
    Cadena Boolean (depsgraph, temporales en bpy.context.scene.collection):
    roca U bloques U carrocería - pasa-ruedas U aletas U ruedas U detalles
    U espejos U marcos - rebajes - cortes. Si el depsgraph no evalúa ->
    RuntimeError."""
    R, W, AB = float(radio), float(ancho), float(alto_base)
    zf = float(z_fondo)
    n_spokes = int(params.get("n_radios", 12))
    m = max(7, int(params.get("segmentos_por_radio", 7)))
    talud = float(params.get("talud_deg", 35.0))
    solver = str(params.get("solver", "MANIFOLD")).upper()
    det = float(params.get("detalle_secundario", 0.6))
    lv = 1.0 if float(params.get("lado_visible", 1.0)) >= 0.0 else -1.0
    so = seed * 17.37 + 3.1
    mats = _mats_roca()
    hubs_x = (0.0, _X_REAR * R)

    me_roca = _malla("MCOCHE_tmp_roca", _roca(R, W, AB, zf, so, talud), mats)
    bm_r = bmesh.new()
    bm_r.from_mesh(me_roca)
    tree_r = BVHTree.FromBMesh(bm_r)
    bm_r.free()
    me_bloq = _malla("MCOCHE_tmp_bloques", _bloques(R, W, tree_r, seed), mats)
    bm_body = _carroceria(R, W, AB, so)
    tree_b = BVHTree.FromBMesh(bm_body)
    me_body = _malla("MCOCHE_tmp_cuerpo", bm_body, mats)
    bm_marcos, bm_rebajes = _ventanas(R, W, tree_b)
    me_marcos = _malla("MCOCHE_tmp_marcos", bm_marcos, mats)
    me_rebajes = _malla("MCOCHE_tmp_rebajes", bm_rebajes, mats)
    me_wells = _malla("MCOCHE_tmp_pasarruedas", _pasa_ruedas(R, W, AB, hubs_x),
                      mats)
    me_fend = _malla("MCOCHE_tmp_aletas", _guardabarros(R, W, AB, so), mats)
    discos = []
    for xh in hubs_x:
        for side in (1.0, -1.0):
            d_here = 1.0 if (xh == 0.0 and side == lv) else det
            discos.append(_disco_rueda(R, W, AB, xh, side, so, n_spokes, m,
                                       d_here))
    me_discs = _fusionar(discos, "MCOCHE_tmp_ruedas", mats)
    me_det = _malla("MCOCHE_tmp_detalles", _detalles(R, W, AB, so), mats)
    me_esp = _malla("MCOCHE_tmp_espejos", _retrovisores(R, W), mats)
    me_cut = _malla("MCOCHE_tmp_cortes", _cortes(R, W, AB, so, seed, lv), mats)
    coll_tmp = bpy.context.scene.collection
    temp = [_objeto(me.name, me, coll_tmp)
            for me in (me_roca, me_bloq, me_body, me_wells, me_fend, me_discs,
                       me_det, me_esp, me_marcos, me_rebajes, me_cut)]
    (ob_roca, ob_bloq, ob_body, ob_wells, ob_fend, ob_discs, ob_det, ob_esp,
     ob_marcos, ob_rebajes, ob_cut) = temp
    ops = [("UNION", ob_bloq), ("UNION", ob_body), ("DIFFERENCE", ob_wells),
           ("UNION", ob_fend), ("UNION", ob_discs), ("UNION", ob_det),
           ("UNION", ob_esp), ("UNION", ob_marcos), ("DIFFERENCE", ob_rebajes),
           ("DIFFERENCE", ob_cut)]
    usado = solver
    me = _boolean_cadena(ob_roca, ops, solver)
    nm = _pulir(me)
    if nm != 0 and solver != "EXACT":         # reserva: el mejor de los dos
        me2 = _boolean_cadena(ob_roca, ops, "EXACT")
        nm2 = _pulir(me2)
        if nm2 < nm:
            bpy.data.meshes.remove(me)
            me, nm, usado = me2, nm2, "EXACT"
        else:
            bpy.data.meshes.remove(me2)
    for ob in temp:
        mesh = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    me.name = "MCOCHE_roca"
    if not me.materials:
        for mt in mats:
            me.materials.append(mt)
    me["mcoche_no_manifold"] = nm
    me["mcoche_solver"] = usado
    obj = bpy.data.objects.new("MCOCHE_roca", me)
    obj["radio"], obj["ancho"], obj["alto_base"], obj["z_fondo"] = R, W, AB, zf
    obj["lado_visible"] = lv
    obj["hubs"] = ((0.0, 0.5 * W, R - AB), (_X_REAR * R, 0.5 * W, R - AB))
    suelo = [v.co.x for v in me.vertices if abs(v.co.z) < 1.0]
    obj["huella_x"] = (min(suelo), max(suelo)) if suelo else (0.0, 0.0)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    obj["bbox"] = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
    parent_collection.objects.link(obj)
    if con_vegetacion:
        bm = bmesh.new()
        bm.from_mesh(me)
        tree = BVHTree.FromBMesh(bm)
        bm.free()
        _vegetacion(parent_collection, obj, R, W, AB, tree, seed)
    return obj
