"""montana_coche.py — La MONTAÑA-COCHE FÓSIL de Porto Corsa (Cars 2), Blender 5.1.

Un COCHE GIGANTE DE PIEDRA (tipo Fiat 500 Topolino redondeado, fósil, medio
enterrado en la ladera y asomado al mar por la zaga) visto de LADO desde la
carretera. Sustituye a la "sola rueda" de montana_rueda.py: la rueda fósil
(neumático, llanta, hueco en sombra, buje y 12 radios de hueso) es ahora la
RUEDA DELANTERA de un coche completo, con rueda trasera, guardabarros en
relieve, capó, parabrisas y ventanillas rehundidas, puerta insinuada, faros
y zócalo/falda rocosa hasta el fondo del mar.

Construcción: piezas cerradas independientes (carrocería = loft de secciones
YZ superelípticas a lo largo de X cerrado con domos en morro y zaga, con las
ALETAS como abultamiento del propio flanco alrededor de cada pasa-ruedas;
4 discos-rueda con topología polar copiada de montana_rueda.py; roca = loft
de secciones YZ con talud, cortado por z_fondo y tapado) que se UNEN con el
Boolean del modificador (solver MANIFOLD, con EXACT de reserva) evaluando el
depsgraph — sin bpy.ops. La carrocería y la roca reciben antes un pasa-
ruedas (cilindro) para que el hueco de la llanta no quede relleno. Resultado:
UNA malla cerrada (2-manifold) 'MCOCHE_roca' + hijo 'MCOCHE_veg' (matas).
Los estratos de la carrocería son rectos (fase 0) y la malla se corta con
bisect_plane en cada borde de banda antes de asignar el material, de modo
que el cambio de color es una arista horizontal limpia (sin escalera).

Reutiliza (importa por ruta, mismo directorio) de montana_rueda.py: ruido
(_n3, _ridged, _celda), estratos (_estrato_mat), rueda (_tyre_pt, _talla,
_radios_en, _angulos_cara, _U_RINGS, _PSI_RINGS), vegetación (_blob, _pino).

API:
  build(parent_collection, radio=40.0, ancho=78.0, alto_base=12.0,
        z_fondo=-45.0, seed=0, con_vegetacion=True, n_radios=12,
        segmentos_por_radio=7, talud_deg=35.0, solver="MANIFOLD",
        detalle_secundario=0.6)
      -> malla raíz MCOCHE_roca (única, cerrada) + hijo MCOCHE_veg.
         Propiedades: obj["radio"], obj["ancho"], obj["alto_base"],
         obj["z_fondo"], obj["hubs"] ((x,y,z) rueda delantera y trasera, lado
         +Y), obj["huella_x"], obj["bbox"], mesh["mcoche_no_manifold"] (0),
         mesh["mcoche_solver"] (solver usado).

Convenciones (metros; R = radio, W = ancho):
  Origen = centro de la RUEDA DELANTERA en planta (x=0, y=0); z=0 = suelo
  local (carretera, lado +Y, para x > -1.3R); el mar (z=-4) empieza en
  x < -1.5R y la FALDA rocosa baja hasta z_fondo con base plana. La cara
  visible mira a +Y; el MORRO apunta a +X y la ZAGA a -X.
  Ruedas: bujes en (0, ±W/2, R-alto_base) y (-3.4R, ±W/2, R-alto_base);
  cara del neumático en |y| = W/2, hundida alto_base m bajo z=0.
  Carrocería: flanco máximo en |y| = W/2 - 0.15R; aletas (relieve 0.12R
  del flanco, radios 1.15R..1.44R alrededor de cada buje) hasta
  |y| = W/2 - 0.03R; pared rocosa (zócalo) en |y| = W/2 - 0.09R.
  Perfil (XZ): parachoques x=+1.35R (z 0.6R..1.0R), capó 1.0R->1.6R,
  parabrisas hasta el techo z=2.9R en x=-0.2R, techo hasta -2.3R, zaga
  cayendo a 1.3R en x=-4.2R, faldón a 0.9R; domos de morro (0.12R) y zaga
  (0.09R). Cristal (parabrisas, ventanillas, luneta) rehundido 0.08R con
  marco saliente 0.06R; faros = domos de 0.11R con aro. Arco visto-a-través
  entre las ruedas (x -2.02R..-1.38R) SOLO por encima de z=0.55R; en |x| < 1.1R roca
  maciza bajo el coche (túnel del integrador: caja 21 x 9.5 a lo largo de Y,
  centrada en x=-0.65R, z desde 0, atraviesa roca en todo el grosor W).
  Zona prohibida respetada: |y| <= W/2 + 2.5 para x en [-1.3R, +1.5R]
  (la falda sólo se ensancha, con talud `talud_deg` respecto a la vertical,
  para x < -1.3R).
  Materiales (índices fijos): 0 MAT_MCOCHE_caliza, 1 _caliza_clara,
  2 _caliza_oscura, 3 _hueco, 4 _hueso, 5 _cristal; veg: MAT_MCOCHE_veg/
  _veg_clara/_tronco.
  Integrador: build() evalúa Booleans en el depsgraph, así que los objetos
  temporales se linkan a bpy.context.scene.collection (siempre en el view
  layer) y se comprueba que el resultado difiere de la roca sola; si el
  view layer no evalúa, lanza RuntimeError en vez de devolver sólo la roca.
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
    spec = importlib.util.spec_from_file_location("montana_rueda_helpers", ruta)
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


def _mats_roca():
    """Colores idénticos a MAT_MRUEDA_* (caliza cálida, hueco casi negro,
    hueso gris claro) con nombres MAT_MCOCHE_*, más el cristal fósil
    (gris azulado muy oscuro, algo satinado) de ventanillas y faros."""
    return (
        _mat("MAT_MCOCHE_caliza", (0.470, 0.405, 0.305), 0.95),
        _mat("MAT_MCOCHE_caliza_clara", (0.600, 0.535, 0.415), 0.95),
        _mat("MAT_MCOCHE_caliza_oscura", (0.300, 0.250, 0.185), 0.95),
        _mat("MAT_MCOCHE_hueco", (0.090, 0.075, 0.055), 0.97, 0.10),
        _mat("MAT_MCOCHE_hueso", (0.400, 0.360, 0.290), 0.92, 0.20),
        _mat("MAT_MCOCHE_cristal", (0.075, 0.085, 0.105), 0.60, 0.40),
    )


def _mats_veg():
    return (
        _mat("MAT_MCOCHE_veg", (0.062, 0.195, 0.058), 0.92),
        _mat("MAT_MCOCHE_veg_clara", (0.130, 0.310, 0.090), 0.92),
        _mat("MAT_MCOCHE_tronco", (0.230, 0.150, 0.090), 0.95),
    )


# ------------------------------------------------------------ layout (R) ----
_X_REAR = -3.4          # rueda trasera
_BAND_H = 0.17          # altura de estrato (unid. R)
_Y_BODY = 0.15          # flanco de la carrocería: W/2 - 0.15R
_Y_WALL = 0.09          # pared rocosa (zócalo): W/2 - 0.09R
_FEND_R0 = 1.15         # radio (unid. R) donde arranca la aleta: holgura 0.15R
_FEND_R1 = 1.44         # radio donde la aleta muere en el flanco
_FEND_H = 0.12          # relieve de la aleta sobre el flanco (unid. R)
_WELL_R = 1.17          # radio del pasa-ruedas (cilindro que corta cuerpo/roca)
_WELL_D = 0.36          # profundidad del pasa-ruedas desde la cara: W/2-0.36R
#                       # (8.4 m por dentro del flanco, 12 m por dentro de la aleta)
_FARO_C = (0.36, 1.05)  # centro del faro (|y|/R, z/R) en el frente del capó
_FARO_X1 = 1.37         # el faro se apaga en x > 1.37R (no toca el domo)
_FARO_R = 0.14          # radio del faro (unid. R); aro hasta 1.45x
_FARO_H = 0.11          # relieve del domo del faro (unid. R)
_DOME_NOSE, _DOME_TAIL = 0.12, 0.09   # fondo del domo de morro / zaga (R)
_DOME_F = (0.34, 0.62, 0.83, 0.95)    # anillos del domo (fracción del fondo)
_WIN_Z0, _WIN_Z1 = 2.00, 2.52         # cristal de las ventanillas (z/R), en
#                                     # el flanco plano (no llega al hombro)
_WS_Z0, _LU_Z0 = 1.72, 1.90           # pie del parabrisas / de la luneta (z/R);
#                                     # arriba los limita su estación x
_WIN_MARCO = 0.05                     # anchura del marco (unid. R)
# perfil lateral de la carrocería (x/R -> z/R); morro redondeado (sin kink)
_ZTOP = [(-4.25, 1.25), (-4.2, 1.32), (-4.0, 1.72), (-3.6, 2.22),
         (-3.1, 2.62), (-2.6, 2.84), (-2.3, 2.90), (-1.3, 2.94), (-0.2, 2.90),
         (0.0, 2.70), (0.25, 2.15), (0.5, 1.60), (0.9, 1.38), (1.2, 1.16),
         (1.32, 1.06), (1.40, 0.93)]
_ZBOT = [(-4.25, 0.98), (-4.2, 0.90), (-3.8, 0.76), (-3.0, 0.88), (-1.0, 0.90),
         (0.5, 0.82), (1.1, 0.66), (1.3, 0.60), (1.40, 0.63)]
# semiancho de la carrocería relativo a (W/2 - 0.15R)
_WBODY = [(-4.25, 0.34), (-4.2, 0.62), (-4.0, 0.86), (-3.5, 0.96),
          (-3.0, 1.00), (-0.3, 1.00), (0.4, 0.95), (1.0, 0.86), (1.25, 0.76),
          (1.4, 0.58)]


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
    """1 en la mitad superior de la rueda (zona del guardabarros: el collar
    de roca se rehunde al fondo del pasa-ruedas), 0 en la mitad inferior
    (collar a ras de la pared rocosa). Transición suave de 10 grados."""
    if a_deg > 180.0:
        return 0.0
    return _sstep((a_deg - 6.0) / 10.0) * (1.0 - _sstep((a_deg - 164.0) / 10.0))


# =========================================================== disco-rueda ====
def _disco_rueda(R, W, alto_base, x_hub, side, so, n_spokes, m, detalle):
    """Disco CERRADO de una rueda: polo del buje -> anillos de la cara fósil
    (talla de montana_rueda) -> neumático (superelipse) -> collar de roca
    (a ras de la pared abajo, rehundido bajo el guardabarros arriba) ->
    cilindro trasero -> polo trasero. side=+1: cara en y=+W/2; -1: en -W/2.
    detalle<1 reduce los anillos (ruedas secundarias). Devuelve bmesh."""
    N = n_spokes * m
    zc = R - alto_base
    y_face = 0.5 * W
    d_wall = -_Y_WALL * R
    d_well = -_WELL_D * R - 2.0
    d_back = d_well - 1.4     # dorso justo tras el collar rehundido (el
    #                         # flanco interior del neumático, visto por la zaga)
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
    """Caras del disco con material por zona (copiado de montana_rueda:
    hueso en buje/collarín/radios/aro, hueco en el fondo, llanta clara,
    capas concéntricas del neumático) + collar (estratos / oscuro en el
    pasa-ruedas) + trasera oscura."""
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
    y_face_abs = abs(r0[0].co.y)  # ~W/2 (referencia para el collar)
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
def _seccion_cuerpo(t, w, zb, zt, q_top, q_bot):
    """Punto (y, z) de la sección YZ: superelipse (hombros redondeados)
    con exponente distinto arriba/abajo; t en [0,1) recorre el anillo desde
    el flanco +Y (t=0) por arriba (t=0.25), flanco -Y (0.5) y abajo (0.75).
    Los puntos se concentran en los flancos (ventanillas, puerta)."""
    th = 2.0 * math.pi * t
    th = th - 0.15 * math.sin(2.0 * th)         # warp: más puntos en flancos
    q = q_top if math.sin(th) >= 0.0 else q_bot
    zm, h = 0.5 * (zt + zb), 0.5 * (zt - zb)
    return w * _sq(math.cos(th), q), zm + h * _sq(math.sin(th), q)


# cristales (x0, x1 en unid. R): ventanilla trasera, delantera, parabrisas,
# luneta; el marco de _WIN_MARCO rodea cada uno por fuera
_VENTANAS = ((-2.13, -1.34), (-1.14, -0.38))
_PARABRISAS = (-0.10, 0.36)
_LUNETA = (-3.55, -2.85)


def _estaciones_cuerpo(R):
    """Cotas x (unid. R) de las secciones: paso base 0.10R + estaciones extra
    en juntas de puerta, a ambos lados de cada borde de cristal y de marco
    (aristas nítidas: el escalón cae entre dos estaciones a 0.024R), morro
    fino (faros, parrilla) y remates de zaga/morro."""
    xs = set()
    x = -4.2
    while x < 1.16:
        xs.add(round(x, 3))
        x += 0.10
    for xk in (-1.24, -0.30):                 # juntas de puerta
        for dx in (-0.045, 0.0, 0.045):
            xs.add(round(xk + dx, 3))
    mk = _WIN_MARCO
    for x0, x1 in _VENTANAS + (_PARABRISAS, _LUNETA):
        for xk in (x0 - mk, x0, x1, x1 + mk):   # bordes de marco y cristal
            for dx in (-0.012, 0.012):
                xs.add(round(xk + dx, 3))
    x = 1.16
    while x < 1.39:                           # morro: faros y parrilla
        xs.add(round(x, 3))
        x += 0.03
    for xk in (-4.25, -4.235, -4.215, 1.395, 1.40):  # remates zaga/morro
        xs.add(xk)
    return sorted(xs)


def _desplaza_cuerpo(R, wmax, zc_r, p, n, so):
    """Desplazamiento (m) a lo largo de la normal n en el punto p de la
    carrocería, desplazamiento VERTICAL (parabrisas y luneta) y pesos de
    zona (cristal, marco, faro, aro, parrilla) para el material por cara.
    Devuelve (d_normal, d_z, zonas). Relieves: cristales rehundidos 0.08R con marco
    saliente 0.06R (bordes nítidos: cajas con transición 0.012R que cae
    entre dos estaciones/cortes), juntas de puerta, ALETAS = abultamiento
    del flanco de _FEND_H alrededor de cada buje (radios _FEND_R0.._FEND_R1,
    sólo por encima de -15 grados), faros en domo con aro, parrilla oscura
    rehundida, parachoques trasero y grano de piedra con escalón de estrato
    RECTO (fase 0; fuera de cristal y faros)."""
    x, y, z = p.x / R, p.y / R, p.z / R
    d = 0.0            # a lo largo de la normal
    dz = 0.0           # vertical (parabrisas/luneta: sobre el techo/capó
    #                  # inclinados un escalón normal de 0.14R plegaría la malla)
    g = l = fd = fa = pr = 0.0
    ay = abs(n.y)
    mk = _WIN_MARCO

    def caja(x0, x1, z0, z1, s=0.012):
        return (_sstep((x - x0) / s) * _sstep((x1 - x) / s) *
                _sstep((z - z0) / s) * _sstep((z1 - z) / s))

    def cristal(x0, x1, z0, z1, lat=1.0):
        # marco (+0.06R) por fuera del cristal (-0.08R); lat recorta en y
        m_out = caja(x0 - mk, x1 + mk, z0 - mk, z1 + mk) * lat
        m_in = caja(x0, x1, z0, z1) * lat
        return 0.06 * m_out - 0.14 * m_in, m_in, m_out * (1.0 - m_in)

    if ay > 0.55:                                      # flancos: ventanillas
        for x0, x1 in _VENTANAS:
            dd, gi, li = cristal(x0, x1, _WIN_Z0, _WIN_Z1)
            d += dd
            g, l = max(g, gi), max(l, li)
        # junta de la puerta (surco fino) por x=-1.24 y x=-0.30, z 0.95..1.95
        for xk in (-1.24, -0.30):
            gx = math.exp(-((x - xk) / 0.03) ** 2)
            gz = _sstep((z - 0.95) / 0.05) * (1.0 - _sstep((z - 1.93) / 0.05))
            d -= 0.035 * gx * gz
        # umbral de la puerta (surco horizontal) z=0.98 entre las juntas
        gz = math.exp(-((z - 0.98) / 0.03) ** 2)
        gx = _sstep((x + 1.24) / 0.04) * (1.0 - _sstep((x + 0.30) / 0.04))
        d -= 0.03 * gz * gx
    # parabrisas / luneta: recorte lateral SUAVE en |y| (0.15R, pilares A/C)
    # para que el escalón del marco no pliegue la malla en los hombros; por
    # arriba los limita su estación x (el techo), no una cota z
    if n.z > 0.25 and n.x > 0.25 and ay < 0.85:        # parabrisas
        lat = _sstep((0.72 * wmax - abs(y)) / 0.15)
        dd, gi, li = cristal(_PARABRISAS[0], _PARABRISAS[1], _WS_Z0, 3.2, lat)
        dz += dd
        g, l = max(g, gi), max(l, li)
    if n.z > 0.2 and n.x < -0.25 and ay < 0.85:        # luneta trasera
        lat = _sstep((0.68 * wmax - abs(y)) / 0.15)
        dd, gi, li = cristal(_LUNETA[0], _LUNETA[1], _LU_Z0, 3.2, lat)
        dz += dd
        g, l = max(g, gi), max(l, li)
    if ay > 0.30:                                      # ALETAS (abultamiento)
        wf = _sstep((ay - 0.30) / 0.35)
        for xh in (0.0, _X_REAR):
            rho = math.hypot(x - xh, z - zc_r)
            if rho < _FEND_R0 - 0.02 or rho > _FEND_R1:
                continue
            up = _sstep((rho - _FEND_R0 + 0.02) / 0.08)
            down = 1.0 - _sstep((rho - _FEND_R1 + 0.17) / 0.17)
            ang = _sstep(((z - zc_r) / rho + 0.26) / 0.16)   # sólo sobre el buje
            d += _FEND_H * wf * up * down * ang
    if n.x > 0.35 and x < _FARO_X1 + 0.05:             # frente: faros con aro
        kf = 1.0 - _sstep((x - _FARO_X1) / 0.05)       # no invade el domo
        for sy in (-1.0, 1.0):
            rr = math.hypot((y - sy * _FARO_C[0]) / _FARO_R,
                            (z - _FARO_C[1]) / _FARO_R)
            if rr < 1.0:
                d += kf * _FARO_H * max(1.0 - rr * rr, 0.0) ** 0.75
                fd = 1.0
            elif rr < 1.45:
                d += kf * 0.045 * math.sin(math.pi * (rr - 1.0) / 0.45)
                fa = 1.0
        # (sin parrilla: con los dos faros leería como una cara; es un fósil)
    if n.x < -0.4 and ay < 0.8:                        # zaga: parachoques
        d += 0.04 * _sstep((z - 0.93) / 0.04) * (1.0 - _sstep((z - 1.07) / 0.04))
    # grano de piedra + escalón de estratos RECTO (fase 0), no en cristal/faro
    piedra = 1.0 - max(g, fd, pr)
    d += piedra * 0.010 * math.tanh(2.5 * _onda_estrato(p.z, _BAND_H * R, 0.0))
    d += piedra * (0.012 * _n3(p.x * 0.05 + so, p.y * 0.05, p.z * 0.05) +
                   0.006 * _n3(p.x * 0.18, p.y * 0.18 + so, p.z * 0.18))
    return d * R, dz * R, (g, l, fd, fa, pr)


def _domo(bm, ring, x_end, depth, sign):
    """Anillos de domo (elipsoide de fondo `depth`) que cierran el loft
    tras el anillo `ring` (en x_end) hacia sign*X, y el polo final.
    Devuelve (lista de anillos, polo)."""
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


def _planos_cuerpo(R, z_min, z_max):
    """Cotas z (m) de los cortes bisect de la carrocería: bordes de media
    banda de estrato (fase 0: t = z/band_h, borde en z = band_h*(j/2 - 1/4))
    y pares a +-0.012R de cada borde de cristal/marco (escalón nítido)."""
    band_h = _BAND_H * R
    zs = set()
    j = math.floor(z_min / band_h * 2.0)
    while band_h * (0.5 * j - 0.25) < z_max:
        zk = band_h * (0.5 * j - 0.25)
        if z_min < zk < z_max:
            zs.add(round(zk, 4))
        j += 1
    mk = _WIN_MARCO
    for zr in (_WIN_Z0, _WIN_Z0 - mk, _WIN_Z1, _WIN_Z1 + mk, _WS_Z0, _WS_Z0 - mk,
               _LU_Z0, _LU_Z0 - mk):
        for dz in (-0.012, 0.012):
            zs.add(round((zr + dz) * R, 4))
    return sorted(zs)


def _carroceria(R, W, alto_base, so, n_ring=64):
    """Loft cerrado de la carrocería (estaciones X x anillo YZ) rematado con
    domos en morro y zaga; cortes bisect en cada borde de banda de estrato y
    de cristal; material por cara ANTES de desplazar (bordes de color =
    aristas rectas); después desplazamiento a lo largo de la normal
    (cristales, marcos, juntas, aletas, faros, grano). Devuelve bmesh."""
    wmax = 0.5 * W - _Y_BODY * R
    zc_r = (R - alto_base) / R
    xs = _estaciones_cuerpo(R)
    bm = bmesh.new()
    rings = []
    for xr in xs:
        w = wmax * max(_spline(_WBODY, xr), 0.05)
        zb = R * _spline(_ZBOT, xr)
        zt = max(R * _spline(_ZTOP, xr), zb + 0.04 * R)
        q_top = 2.7 - 0.5 * _sstep((xr - 0.3) / 0.6)     # capó más redondo
        q_bot = 4.0
        ring = []
        for k in range(n_ring):
            y, z = _seccion_cuerpo(k / n_ring, w, zb, zt, q_top, q_bot)
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
    # Las franjas de 0.024R entre las dos estaciones que flanquean cada borde
    # de cristal/marco del parabrisas y la luneta NO se cortan: sobre el capó
    # y el techo inclinados un corte horizontal metería un vértice a mitad
    # del escalón (máscara discontinua) y la malla se plegaría.
    mk = _WIN_MARCO
    x_crisp = [xk * R for x0, x1 in (_PARABRISAS, _LUNETA)
               for xk in (x0 - mk, x0, x1, x1 + mk)]
    excl_f = {f for f in bm.faces
              if any(abs(f.calc_center_median().x - xc) < 0.02 * R
                     for xc in x_crisp)}
    excl_e = {e for e in bm.edges
              if e.link_faces and all(f in excl_f for f in e.link_faces)}
    z_min = min(v.co.z for v in bm.verts)
    z_max = max(v.co.z for v in bm.verts)
    for zk in _planos_cuerpo(R, z_min, z_max):
        geom = (bm.verts[:] + [e for e in bm.edges if e not in excl_e] +
                [f for f in bm.faces if f not in excl_f])
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-3,
                               plane_co=(0.0, 0.0, zk), plane_no=(0.0, 0.0, 1.0),
                               use_snap_center=False, clear_outer=False,
                               clear_inner=False)
    bm.normal_update()
    desp, zona = {}, {}
    for v in bm.verts:
        d, dz, zn = _desplaza_cuerpo(R, wmax / R, zc_r, v.co, v.normal, so)
        desp[v] = v.normal * d + Vector((0.0, 0.0, dz))
        zona[v] = zn
    band_h = _BAND_H * R
    for fce in bm.faces:
        nv = len(fce.verts)
        g, l, fd, fa, pr = (sum(zona[v][i] for v in fce.verts) / nv
                            for i in range(5))
        fce.smooth = True
        if g > 0.5:
            fce.material_index = _M_CRISTAL
        elif pr > 0.5:
            fce.material_index = _M_HUECO
        elif fd > 0.5 or l > 0.5:
            fce.material_index = _M_HUESO
        elif fa > 0.5:
            fce.material_index = _M_CLARA
        else:
            fce.material_index = _estrato_mat(fce.calc_center_median().z,
                                              band_h, 0.0)
    for v, dv in desp.items():
        v.co += dv
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method="BEAUTY",
                              ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# ============================================================ pasa-ruedas ====
def _pasa_ruedas(R, W, alto_base, hubs_x, n=64):
    """Cilindros cerrados (uno por rueda y lado) a lo largo de Y que se
    RESTAN a carrocería y roca: radio _WELL_R = 1.17R, desde |y| = W/2 -
    _WELL_D (0.36R, fondo del pasa-ruedas) hasta |y| = W/2 + 0.3R. Devuelve
    bmesh (4 cáscaras)."""
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


# =================================================================== roca ====
# cota superior de la roca (x/R -> z/R): sube dentro de la carrocería, baja a
# 0.55R en el arco entre ruedas, cae al mar por la zaga y muere en el morro
_ZROCK = [(-6.10, -1.25), (-5.60, -0.70), (-5.15, -0.10), (-4.75, 0.35),
          (-4.50, 0.78), (-4.30, 0.94), (-4.05, 1.05), (-3.70, 1.15), (-2.30, 1.15),
          (-2.17, 1.10), (-2.02, 0.55), (-1.38, 0.55), (-1.23, 1.10),
          (-1.10, 1.15), (0.60, 1.15), (1.00, 0.95), (1.36, 0.66),
          (1.42, 0.30), (1.50, -0.30), (1.58, -1.25)]


def _lin(pts, x):
    """Interpolación lineal suavizada (smoothstep por tramo): sin sobre-
    oscilaciones (a diferencia de Catmull-Rom) para perfiles con escalones."""
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * _sstep((x - x0) / (x1 - x0))
    return pts[-1][1]


def _w_cuerpo(R, wmax, xr, z):
    """Semiancho (m) de la sección de la carrocería en la cota z (0 fuera)."""
    if xr < -4.22 or xr > 1.38:
        return 0.0
    w = wmax * max(_spline(_WBODY, xr), 0.05)
    zb = R * _spline(_ZBOT, xr)
    zt = max(R * _spline(_ZTOP, xr), zb + 0.04 * R)
    zm, h = 0.5 * (zt + zb), 0.5 * (zt - zb)
    s = (z - zm) / h
    if abs(s) >= 1.0:
        return 0.0
    q = 2.7 - 0.5 * _sstep((xr - 0.3) / 0.6) if s >= 0.0 else 4.0
    return w * (1.0 - abs(s) ** q) ** (1.0 / q)


def _z_meet(R, xr):
    """Cota (m) donde el talud rocoso encuentra el flanco de la carrocería:
    justo sobre el vientre plano (zb + 6%% de la altura); None sin coche."""
    if xr < -4.22 or xr > 1.38:
        return None
    zb = R * _spline(_ZBOT, xr)
    zt = max(R * _spline(_ZTOP, xr), zb + 0.04 * R)
    return zb + 0.06 * (zt - zb)


def _roca(R, W, alto_base, z_fondo, so, talud_deg, n_ring=72):
    """Loft cerrado de la roca (secciones YZ a lo largo de X): pared/zócalo
    en |y| = W/2 - 0.09R hasta z=0.35R, talud hasta encontrar el flanco de la
    carrocería (y por dentro de ella, oculto), cresta redondeada donde la
    roca queda al aire (arco entre ruedas, zaga, morro) y FALDA bajo z=-4
    con talud `talud_deg` (respecto a la vertical) sólo para x < -1.3R.
    Relieve: ridged + bloques + escalones de estrato (amortiguado junto a las
    ruedas y anulado dentro del coche). Se corta por z_fondo y se tapa."""
    wmax = 0.5 * W - _Y_BODY * R
    w0 = 0.5 * W - _Y_WALL * R
    zc = R - alto_base
    tan_t = math.tan(math.radians(talud_deg))
    band_h = _BAND_H * R
    cw, ch = 0.22 * R, 0.50 * R
    hubs = (0.0, _X_REAR * R)
    xs = set()
    x = -6.10
    while x < 1.58:
        xs.add(round(x, 3))
        x += 0.095
    for xk in (-2.17, -2.02, -1.38, -1.23):
        for dx in (-0.03, 0.03):
            xs.add(round(xk + dx, 3))
    xs.add(1.58)
    xs = sorted(xs)

    def flare(xm):
        return _sstep((-1.30 * R - xm) / (0.35 * R))

    def w_roca(xm, z, z_top):
        xr = xm / R
        w = w0 * (1.0 + 0.04 * _n3(xm * 0.02 + so, z * 0.02, 8.1))
        if xr > 1.0:                        # proa del zócalo: planta redondeada
            w *= math.sqrt(max(1.0 - ((xr - 1.0) / 0.64) ** 2, 0.04))
            # pie en talud (más ancho abajo, dentro de la zona permitida)
            w *= 1.0 + 0.14 * _sstep((xr - 0.95) / 0.3) * _sstep((0.3 * R - z) / (0.4 * R))
        if z < -4.0:
            w += (-4.0 - z) * tan_t * flare(xm)
        z1 = 0.35 * R
        if z <= z1:
            return w
        zm = _z_meet(R, xr)
        if zm is not None and z_top > zm - 0.5:   # la roca se esconde en el coche
            w_meet = _w_cuerpo(R, wmax, xr, zm) + 1.5
            if z <= zm:
                return w + (w_meet - w) * _sstep((z - z1) / (zm - z1))
            return max(_w_cuerpo(R, wmax, xr, z) - 1.5, 2.0)
        w_top = 0.55 * w                    # cresta al aire, redondeada
        return w + (w_top - w) * _sstep((z - z1) / max(z_top - z1, 1.0))

    bm = bmesh.new()
    rings = []
    desp = {}            # vértice -> (D, dirección radial YZ, peso de normal)
    for xr in xs:
        xm = xr * R
        kn = _sstep((xr - 0.85) / 0.35)          # proa del zócalo (morro)
        z_top = R * _lin(_ZROCK, xr)
        z_top += kn * 0.07 * R * _n3(xm * 0.07 + so, 2.2, 5.5)   # silueta rota
        # fondo de la sección bajo z_fondo (lo corta el bisect); los extremos
        # (z_top < z_fondo) quedan enteros bajo el plano, nunca invertidos
        z_low = min(z_fondo - 0.30 * (z_top - z_fondo), z_top - 0.25 * R)
        zmid, H = 0.5 * (z_top + z_low), 0.5 * (z_top - z_low)
        zm = _z_meet(R, xr)
        oculto_desde = zm + 1.0 if (zm is not None and z_top > zm - 0.5) else 1e9
        # exponente alto: los flancos siguen w_roca(z) y sólo la cresta se
        # redondea; en la proa baja a ~2.8 (esquinas y cresta redondeadas)
        q = 6.0 - 3.2 * kn
        ring = []
        for k in range(n_ring):
            th = 2.0 * math.pi * (k + 0.5) / n_ring
            cy, sz = _sq(math.cos(th), q), _sq(math.sin(th), q)
            z0 = zmid + H * sz
            y0 = cy * w_roca(xm, max(z0, z_fondo), z_top)
            # relieve de roca, amortiguado junto a las ruedas
            amp = 1.0
            if abs(y0) > 0.5 * W - 0.30 * R:      # sólo junto a las ruedas
                for xh in hubs:
                    amp = min(amp, 0.25 + 0.75 * _sstep(
                        (math.hypot(xm - xh, z0 - zc) - 1.30 * R) / (0.25 * R)))
            amp *= 1.0 + 0.7 * _sstep((-2.0 - z0) / 8.0)   # falda: más relieve
            if z0 > oculto_desde:
                amp = 0.0
            zq = max(z0, z_fondo)
            D = amp * (_ridged(xm, y0, zq, so) + 2.2 * _celda(xm, y0, zq, so, cw, ch))
            if kn > 0.0:     # proa: ridged medio y bloques tumbados (es roca)
                Dn = amp * 1.3 * (_ridged(xm, y0, zq, so + 2.0, 1.6) + 0.8 * _celda(
                    xm, y0, zq, so + 5.0, 0.26 * R, 0.10 * R))
                D = D * (1.0 - kn) + Dn * kn
            D += amp * 1.3 * math.tanh(2.5 * _onda_estrato(
                zq, band_h, _fase_estrato(xm, y0, so)))
            cap = 5.0 - 1.5 * kn
            D = cap * math.tanh(D / cap)
            if z0 > 0.5 * R and z0 > oculto_desde - 3.0:
                D = 0.0
            dv = Vector((0.0, cy, sz * _sstep((z0 - z_fondo - 2.0) / 6.0)))
            if dv.length < 1e-6:
                dv = Vector((0.0, 0.0, 1.0))
            dv.normalize()
            v = bm.verts.new((xm, y0, z0))
            # normal sólo en la proa y lejos del corte de la base (z_fondo)
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
    # desplazamiento: radial en YZ en el cuerpo del macizo; en la proa del
    # morro y la popa del peñón a lo largo de la NORMAL de la malla (las
    # caras frontales reciben relieve real en X, no quedan planas)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for v, (D, dv, kx) in desp.items():
        if D == 0.0:
            continue
        dr = dv * (1.0 - kx) + v.normal * kx
        if dr.length < 1e-6:
            dr = dv
        v.co += dr.normalized() * D
    for fce in caras:
        c = fce.calc_center_median()
        if c.z < -2.0:
            fce.material_index = _M_OSC
        else:
            fce.material_index = _estrato_mat(
                c.z, band_h, _fase_estrato(c.x, c.y, so))
    _cerrar_en(bm, z_fondo)
    return bm


def _cerrar_en(bm, z_plane):
    """Corta por z=z_plane, elimina lo de debajo y tapa con un n-gon
    triangulado (base plana). Devuelve nº de aristas no manifold."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4,
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
    los evalúa, evaluated_get devuelve la base sin booleanos y se lanza
    RuntimeError en vez de devolver la roca sola en silencio."""
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
            "montana_coche: el depsgraph no evaluó los Booleans (¿'%s' fuera "
            "del view layer activo o colección excluida?)" % base.name)
    return me


def _pulir(me):
    """Limpieza final: micro-agujeros del boolean (slivers degenerados)
    tapados y vértices casi coincidentes fundidos, caras degeneradas fuera,
    normales coherentes, aristas vivas (>30 grados) con normales partidas.
    Devuelve nº de aristas no manifold."""
    bm = bmesh.new()
    bm.from_mesh(me)
    # Solapas de grosor nulo (dos caras sobre los mismos vértices, que
    # Mesh.validate() dejaría medio abiertas): fuera las dos y sus aristas.
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
    # NO dissolve_degenerate/remove_doubles globales: la salida del boolean
    # ya es manifold y colapsar slivers abre rendijas. Sólo se repara si
    # de verdad hay borde abierto.
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
                n_max=34):
    """Matas low-poly apoyadas por ray-cast sobre la malla final: techo y
    capó del coche, lomo del arco entre ruedas, cresta trasera (con pinos),
    zócalo del flanco +Y y delantal del morro. Malla aparte MCOCHE_veg.
    `alto_base` sitúa los bujes (exclusión de matas alrededor de las ruedas)."""
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
            for _t in range(12):
                loc, nrm = sonda(rng.uniform(x0, x1), rng.uniform(y0, y1),
                                 z_desde)
                if valido(loc, nrm, 0.6) and loc.z > z_min:
                    placed.append(loc.copy())
                    _pino(bm, loc, rng.uniform(12.0, 17.0), rng,
                          0 if rng.random() < 0.5 else 1, 2)
                    break

    wb = 0.5 * W - _Y_BODY * R
    grupo(-2.2 * R, -0.4 * R, -0.55 * wb, 0.55 * wb, 6, (2.6, 4.2), 3.4 * R)
    grupo(0.5 * R, 1.2 * R, -0.5 * wb, 0.5 * wb, 3, (2.4, 3.6), 2.0 * R)
    grupo(-2.0 * R, -1.4 * R, -0.8 * wb, 0.8 * wb, 6, (2.8, 4.5), 1.0 * R)
    grupo(-5.3 * R, -4.25 * R, -0.9 * wb, 0.9 * wb, 8, (3.0, 5.0), 1.6 * R,
          pinos=3, z_min=3.0)
    grupo(-3.0 * R, -1.3 * R, wb - 2.0, wb + 4.0, 4, (2.5, 3.8), 0.7 * R,
          min_nz=0.3, z_min=2.0)
    grupo(1.3 * R, 1.6 * R, -0.7 * wb, 0.7 * wb, 3, (2.5, 3.5), 0.55 * R,
          z_min=2.0)                       # zócalo del morro (bajo los faros)
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
    """Montaña-coche completa. Devuelve la malla raíz MCOCHE_roca (única y
    cerrada); la vegetación va en el hijo MCOCHE_veg.
    Los Booleans se evalúan en el depsgraph: las piezas temporales se linkan
    a bpy.context.scene.collection (no a parent_collection, que podría estar
    excluida del view layer) y se borran al terminar; si aun así el depsgraph
    no evalúa, se lanza RuntimeError (nunca se devuelve la roca sin coche)."""
    R, W, AB = float(radio), float(ancho), float(alto_base)
    zf = float(z_fondo)
    n_spokes = int(params.get("n_radios", 12))
    m = max(7, int(params.get("segmentos_por_radio", 7)))
    talud = float(params.get("talud_deg", 35.0))
    solver = str(params.get("solver", "MANIFOLD")).upper()
    det = float(params.get("detalle_secundario", 0.6))
    so = seed * 17.37 + 3.1
    mats = _mats_roca()
    hubs_x = (0.0, _X_REAR * R)

    me_roca = _malla("MCOCHE_tmp_roca", _roca(R, W, AB, zf, so, talud), mats)
    me_body = _malla("MCOCHE_tmp_cuerpo", _carroceria(R, W, AB, so), mats)
    me_wells = _malla("MCOCHE_tmp_pasarruedas", _pasa_ruedas(R, W, AB, hubs_x),
                      mats)
    discos = []
    for xh in hubs_x:
        for side in (1.0, -1.0):
            d_here = 1.0 if (xh == 0.0 and side > 0.0) else det
            discos.append(_disco_rueda(R, W, AB, xh, side, so, n_spokes, m,
                                       d_here))
    me_discs = _fusionar(discos, "MCOCHE_tmp_ruedas", mats)
    coll_tmp = bpy.context.scene.collection
    temp = [_objeto(me.name, me, coll_tmp)
            for me in (me_roca, me_body, me_wells, me_discs)]
    ob_roca, ob_body, ob_wells, ob_discs = temp
    ops = [("UNION", ob_body), ("DIFFERENCE", ob_wells), ("UNION", ob_discs)]
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
