"""vegetacion_kit_v2.py — Vegetación mediterránea low-poly estilo Cars 2 (Porto Corsa), v2.

Kit procedural para Blender 5.1 (bpy, sin bpy.ops de modelado, sin texturas de
imagen). Estilo Riviera italiana saturada y limpia. Unidades en metros, origen
en el centro de la base (z=0 en el suelo), cara principal mirando a +Y.
Cada pieza crea UN objeto malla (varios materiales) linkado a
parent_collection y lo devuelve.

COMPATIBILIDAD con vegetacion_kit.py (v1): mismas funciones, firmas, valores
de retorno y nombres de objeto/material (VEG_<pieza>, MAT_VEG_<clave>). Solo
se añaden kwargs opcionales (`variante=`) y piezas nuevas.

VARIANTES DE SILUETA (elegidas con `seed % N`, o forzadas con `variante=`;
un valor de `variante` desconocido lanza ValueError):
  build_pino(parent, alto=12.0, seed=0, variante=None)
      "parasol"  pino piñonero: tronco alto desnudo, copa plana y ancha
      "carrasco" pino carrasco: alto y estrecho, copa cónica irregular en
                 4-5 lóbulos apilados y desplazados a lados alternos
      "costero"  pino costero batido por el viento: tronco muy inclinado,
                 copa en bandera hacia sotavento
      "joven"    pino piñonero joven: tronco corto, copa ovoide densa y clara.
                 Es pequeño por naturaleza: si sale por reparto automático
                 (variante=None) se construye con min(alto, 7.0); con
                 variante="joven" explícito se respeta `alto`.
  build_cipres(parent, alto=10.0, seed=0, variante=None)
      "lapiz"    ciprés lápiz muy esbelto      "llama"  ciprés en llama, más lleno
  build_palmera(parent, alto=8.0, seed=0, variante=None)
      "datil"        palmera datilera: tronco grueso escamado, palmas largas caídas
      "washingtonia" tronco altísimo y fino, corona pequeña de hojas en abanico
                     con falda estrecha de hojas secas
      "abanico"      palmito: 1-3 troncos cortos y gruesos, hojas en abanico.
                     Pequeño por naturaleza: por reparto automático se
                     construye con min(alto, 5.0); explícito respeta `alto`.
  build_adelfa(parent, seed=0, variante=None)
      "rosa" mata redonda compacta | "blanca" mata alta en copa (vaso) |
      "roja" mata baja y extendida
  build_arbusto(parent, tam=1.5, seed=0, variante=None)       (NUEVO)
      "romero" | "lavanda" (espigas moradas) | "retama" (flores amarillas)
  Cada objeto devuelto lleva ob["VEG_variante"] con la variante usada.

`alto` es la altura NOMINAL: la altura real de la malla queda entre 0.93 y
1.02 x alto según el jitter de la copa (la copa se sube para acercarse a alto).

PIEZAS NUEVAS:
  build_olivo(parent, alto=5.0, seed=0)     tronco retorcido nudoso + copa
                                            irregular verde plata/salvia
  build_encina(parent, alto=9.0, seed=0)    copa redonda densa verde oscuro
  build_platano(parent, alto=14.0, seed=0)  árbol caduco grande, copa amplia
                                            en pisos verde claro (paseo)
  build_arbol(parent, tipo=None, alto=None, seed=0)
      Despachador: tipo en {"pino","cipres","palmera","olivo","encina",
      "platano","adelfa","arbusto"} o None (aleatorio ponderado por seed);
      alto None -> rango típico del tipo (para "arbusto" es `tam`). Marca el
      objeto con la propiedad ob["VEG_tipo"].

PIEZAS v1 (sin cambios de firma):
  build_jardinera(parent, largo=6.0, seed=0), build_roca(parent, tam=3.0, seed=0),
  build_acantilado(parent, largo=40.0, alto=25.0, seed=0),
  build(parent, seed=0, **params) -> Empty raíz VEG_muestrario.

Copas de varios lóbulos solapados con jitter por seed, troncos ahusados y
(pinos/olivos) curvados, colores de follaje variables por seed dentro de cada
familia. Presupuesto: <= 1200 tris por árbol, <= 500 por arbusto.
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

PREFIX = "VEG"
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Paleta plana estilo Cars 2 (color lineal, roughness)
# FASE VISUAL F1 (bloque 3 punto 1): las COPAS (pino, cipres, encina, olivo, adelfa, arbustos, palmera,
# platano, colgante) salen de 03_blender/paleta.json: oliva_oscuro / salvia y sus variantes de luminancia
# (paleta.variante) o mezclas entre colores de la paleta; antes eran verdes cesped (51_piloto_s1700).
# Las rocas/caliza del kit tambien (caliza_ocre, caliza_gris_calido, caliza_sombra). Troncos no cambian.
# PALETA v2 (usuario 04/10): cipreses y pinos oscuros (pino_a, pino_b) en cipres_pino_oscuro #34503A con la
# misma variacion por instancia (tonos a/b + _luz); pino_c queda como variante oliva mas clara. BUGANVILLA
# #C2407A solo como ACENTO: flores de la adelfa rosa (flor_rosa / flor_rosa_clara) y un 12 % de los arbustos
# con flor (build_arbusto, sorteo propio por seed); el resto de flores no cambia.
# ---------------------------------------------------------------------------
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import paleta as _paleta  # noqa: E402


def _v(nombre, lum=1.0):
    return _paleta.variante(nombre, lum)


def _mez(c1, c2, t):
    """Mezcla lineal entre dos colores de la paleta (t = peso del segundo)."""
    return tuple(a * (1.0 - t) + b * t for a, b in zip(c1, c2))


_OLIVA = _paleta.rgb('oliva_oscuro')
_SALVIA = _paleta.rgb('salvia')
_SECA = _paleta.rgb('hierba_seca')
_CIP = _paleta.rgb('cipres_pino_oscuro')       # paleta v2: cipres y pino oscuro #34503A
_BUGANVILLA = _paleta.rgb('buganvilla')        # paleta v2: acento de flores #C2407A (pequenas dosis)
_PALETA = {
    # --- v1 (se mantienen) ---
    "tronco_palmera": ((0.38, 0.24, 0.11), 0.90),
    "palma":          (_mez(_v('oliva_oscuro', 1.25), _SALVIA, 0.35), 0.75),
    "palma_clara":    (_mez(_v('oliva_oscuro', 1.5), _v('salvia', 1.15), 0.5), 0.75),
    "coco":           ((0.45, 0.28, 0.10), 0.85),
    "cipres":         (_CIP, 0.80),
    "tronco":         ((0.30, 0.17, 0.08), 0.90),
    "pino":           (_CIP, 0.80),
    "adelfa_hoja":    (_mez(_OLIVA, _SALVIA, 0.3), 0.80),
    "flor_rosa":      (_BUGANVILLA, 0.60),                        # adelfa rosa -> buganvilla (acento)
    "flor_rosa_clara": (_v('buganvilla', 1.6), 0.60),
    "buganvilla":     (_BUGANVILLA, 0.60),                        # acento del 12 % de los arbustos con flor
    "flor_roja":      ((0.80, 0.06, 0.08), 0.60),
    "piedra":         (_v('caliza_ocre', 1.25), 0.90),
    "tierra":         (_v('tierra', 0.55), 1.00),
    "roca":           (_paleta.rgb('caliza_ocre'), 0.95),
    "caliza_clara":   (_v('caliza_ocre', 1.2), 0.95),
    "caliza_ocre":    (_paleta.rgb('caliza_ocre'), 0.95),
    "caliza_gris":    (_paleta.rgb('caliza_gris_calido'), 0.95),
    "colgante":       (_mez(_OLIVA, _SALVIA, 0.4), 0.80),
    # --- v2: pinos (tres tonos + claro): paleta v2 pino oscuro (a, b) y una variante oliva (c) ---
    "pino_a":         (_CIP, 0.80),                                                     # pino oscuro #34503A
    "pino_a_luz":     (_v('cipres_pino_oscuro', 1.45), 0.80),
    "pino_b":         (_mez(_CIP, _paleta.rgb('mar_profundo'), 0.08), 0.80),            # un punto mas azulado
    "pino_b_luz":     (_mez(_v('cipres_pino_oscuro', 1.4), _paleta.rgb('mar_profundo'), 0.08), 0.80),
    "pino_c":         (_mez(_CIP, _OLIVA, 0.45), 0.80),                                 # un punto mas oliva/dorado
    "pino_c_luz":     (_mez(_v('cipres_pino_oscuro', 1.4), _v('oliva_oscuro', 1.2), 0.45), 0.80),
    "pino_joven":     (_mez(_v('oliva_oscuro', 1.2), _SALVIA, 0.45), 0.80),
    "pino_joven_luz": (_mez(_v('oliva_oscuro', 1.4), _v('salvia', 1.15), 0.5), 0.80),
    # --- v2: cipreses (paleta v2 cipres_pino_oscuro; _luz = +35..45 % de luminancia) ---
    "cipres_luz":     (_v('cipres_pino_oscuro', 1.4), 0.80),
    "cipres_b":       (_v('cipres_pino_oscuro', 0.9), 0.80),   # F1 cierre (decision 14): paleta pura (antes mezcla con mar_profundo #335144)
    "cipres_b_luz":   (_mez(_v('cipres_pino_oscuro', 1.45), _paleta.rgb('mar_profundo'), 0.06), 0.80),
    # --- v2: palmeras (algo mas verdes que el pino: salvia + oliva) ---
    "palma_wash":     (_mez(_v('oliva_oscuro', 1.3), _SALVIA, 0.4), 0.75),
    "palma_wash_clara": (_mez(_v('oliva_oscuro', 1.5), _v('salvia', 1.2), 0.5), 0.75),
    "palma_seca":     (_v('hierba_seca', 0.9), 0.95),
    "palma_abanico":  (_mez(_v('oliva_oscuro', 1.2), _SALVIA, 0.35), 0.75),
    "palma_abanico_clara": (_mez(_v('oliva_oscuro', 1.45), _v('salvia', 1.1), 0.45), 0.75),
    "datil":          ((0.78, 0.40, 0.10), 0.70),
    "tronco_wash":    ((0.44, 0.34, 0.22), 0.90),
    "tronco_abanico": ((0.32, 0.21, 0.11), 0.95),
    # --- v2: adelfas ---
    "adelfa_hoja_b":  (_mez(_OLIVA, _SALVIA, 0.45), 0.80),
    "flor_blanca":    ((0.95, 0.93, 0.85), 0.60),
    "flor_crema":     ((0.98, 0.90, 0.70), 0.60),
    "flor_roja_clara": ((0.92, 0.22, 0.20), 0.60),
    # --- v2: olivo (salvia) ---
    "tronco_olivo":   ((0.36, 0.28, 0.18), 0.95),
    "olivo_salvia":   (_v('salvia', 0.85), 0.80),
    "olivo_plata":    (_v('salvia', 1.15), 0.80),
    # --- v2: encina (oliva oscuro, algo mas apagado) ---
    "tronco_encina":  ((0.22, 0.15, 0.09), 0.95),
    "encina":         (_v('oliva_oscuro', 0.8), 0.80),
    "encina_luz":     (_v('oliva_oscuro', 1.05), 0.80),
    "encina_b":       (_mez(_v('oliva_oscuro', 0.85), _SALVIA, 0.15), 0.80),
    "encina_b_luz":   (_mez(_v('oliva_oscuro', 1.1), _SALVIA, 0.2), 0.80),
    # --- v2: plátano (el mas claro: salvia dorada) ---
    "tronco_platano": ((0.36, 0.33, 0.25), 0.90),
    "tronco_platano_claro": ((0.56, 0.54, 0.42), 0.90),
    "platano":        (_mez(_SALVIA, _SECA, 0.2), 0.75),
    "platano_luz":    (_mez(_v('salvia', 1.25), _SECA, 0.25), 0.75),
    "platano_b":      (_mez(_v('salvia', 0.9), _OLIVA, 0.3), 0.75),
    "platano_b_luz":  (_mez(_v('salvia', 1.15), _OLIVA, 0.2), 0.75),
    # --- v2: arbustos (salvia y oliva) ---
    "romero":         (_mez(_v('oliva_oscuro', 1.1), _SALVIA, 0.4), 0.85),
    "romero_luz":     (_mez(_v('oliva_oscuro', 1.3), _v('salvia', 1.1), 0.5), 0.85),
    "flor_romero":    ((0.60, 0.70, 0.92), 0.60),
    "lavanda":        (_mez(_v('salvia', 1.1), _paleta.rgb('caliza_gris_calido'), 0.25), 0.85),
    "lavanda_luz":    (_mez(_v('salvia', 1.3), _paleta.rgb('caliza_gris_calido'), 0.25), 0.85),
    "flor_lavanda":   ((0.45, 0.25, 0.72), 0.60),
    "retama":         (_SALVIA, 0.85),   # F1 cierre (decision 14): salvia de paleta (antes mezcla salvia/hierba_seca #A5A77F)
    "retama_luz":     (_mez(_v('salvia', 1.2), _SECA, 0.35), 0.85),
    "flor_amarilla":  ((0.96, 0.80, 0.08), 0.55),
}


def _mat(key):
    """Devuelve (reutilizando si existe) el material plano MAT_VEG_<key>."""
    name = "MAT_%s_%s" % (PREFIX, key)
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    color, rough = _PALETA[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


# ---------------------------------------------------------------------------
# Acumulador de malla multi-material
# ---------------------------------------------------------------------------
class _MB:
    """Acumula (verts, faces, material, smooth) y construye una malla única."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.fmat = []
        self.fsm = []

    def add(self, verts, faces, mat, smooth=False):
        base = len(self.verts)
        if mat in self.mats:
            mi = self.mats.index(mat)
        else:
            self.mats.append(mat)
            mi = len(self.mats) - 1
        self.verts.extend(verts)
        for f in faces:
            self.faces.append(tuple(i + base for i in f))
            self.fmat.append(mi)
            self.fsm.append(smooth)

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def build(self, name, parent_collection):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        for m in self.mats:
            me.materials.append(m)
        for p, mi, sm in zip(me.polygons, self.fmat, self.fsm):
            p.material_index = mi
            p.use_smooth = sm
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        parent_collection.objects.link(ob)
        return ob


# ---------------------------------------------------------------------------
# Primitivas procedurales (verts, faces) con winding hacia fuera
# ---------------------------------------------------------------------------
def _sphere(r=1.0, seg=8, rings=5, scale=(1, 1, 1), off=(0, 0, 0), rng=None, jit=0.0, yaw=0.0):
    """Esfera UV low-poly; `jit` perturba el radio por vértice (lóbulo
    irregular); `scale` escala por eje y `yaw` gira el resultado en Z."""
    verts = []
    faces = []

    def j():
        return 1.0 + (rng.uniform(-jit, jit) if (rng is not None and jit) else 0.0)

    verts.append((0.0, 0.0, r * j()))  # polo superior
    ring_rows = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        row = []
        for k in range(seg):
            th = TAU * k / seg
            f = j()
            row.append(len(verts))
            verts.append((r * math.sin(phi) * math.cos(th) * f,
                          r * math.sin(phi) * math.sin(th) * f,
                          r * math.cos(phi) * f))
        ring_rows.append(row)
    bot = len(verts)
    verts.append((0.0, 0.0, -r * j()))  # polo inferior

    r0 = ring_rows[0]
    for k in range(seg):
        faces.append((0, r0[k], r0[(k + 1) % seg]))
    for i in range(len(ring_rows) - 1):
        up = ring_rows[i]
        lo = ring_rows[i + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((up[k], lo[k], lo[k2], up[k2]))
    rl = ring_rows[-1]
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((bot, rl[k2], rl[k]))

    sx, sy, sz = scale
    ox, oy, oz = off
    if yaw:
        cy, sy_ = math.cos(yaw), math.sin(yaw)
        verts = [(x * sx * cy - y * sy * sy_ + ox, x * sx * sy_ + y * sy * cy + oy, z * sz + oz)
                 for (x, y, z) in verts]
    else:
        verts = [(x * sx + ox, y * sy + oy, z * sz + oz) for (x, y, z) in verts]
    return verts, faces


def _lathe(profile, seg=8, off=(0, 0, 0), rng=None, jit=0.0):
    """Revolución alrededor de Z. profile = [(radio, z), ...] de abajo a arriba;
    radio 0 en extremos = polo."""
    verts = []
    faces = []
    rows = []
    for (r, z) in profile:
        if r <= 1e-6:
            rows.append((len(verts),))
            verts.append((0.0, 0.0, z))
        else:
            row = []
            for k in range(seg):
                th = TAU * k / seg
                f = 1.0 + (rng.uniform(-jit, jit) if (rng is not None and jit) else 0.0)
                row.append(len(verts))
                verts.append((r * f * math.cos(th), r * f * math.sin(th), z))
            rows.append(tuple(row))
    for i in range(len(rows) - 1):
        a = rows[i]
        b = rows[i + 1]
        if len(a) == 1 and len(b) > 1:      # polo inferior
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((a[0], b[k2], b[k]))
        elif len(b) == 1 and len(a) > 1:    # polo superior
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((b[0], a[k], a[k2]))
        elif len(a) > 1 and len(b) > 1:
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((a[k], a[k2], b[k2], b[k]))
    ox, oy, oz = off
    verts = [(x + ox, y + oy, z + oz) for (x, y, z) in verts]
    return verts, faces


def _tube(points, radii, sides=7, cap_top=True, cap_bottom=False):
    """Barre una sección circular por una polilínea (tronco curvado).
    `cap_bottom` cierra el extremo inicial (tronco no hueco visto desde
    abajo con backface culling)."""
    verts = []
    faces = []
    rings = []
    n = len(points)
    for i, p in enumerate(points):
        if i == 0:
            t = Vector(points[1]) - Vector(points[0])
        elif i == n - 1:
            t = Vector(points[-1]) - Vector(points[-2])
        else:
            t = Vector(points[i + 1]) - Vector(points[i - 1])
        t.normalize()
        ref = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
        u = t.cross(ref)
        u.normalize()
        v = t.cross(u)
        row = []
        for k in range(sides):
            th = TAU * k / sides
            q = Vector(p) + (u * math.cos(th) + v * math.sin(th)) * radii[i]
            row.append(len(verts))
            verts.append((q.x, q.y, q.z))
        rings.append(row)
    for i in range(n - 1):
        a = rings[i]
        b = rings[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((a[k], a[k2], b[k2], b[k]))
    if cap_top:
        c = len(verts)
        verts.append(tuple(points[-1]))
        b = rings[-1]
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c, b[k], b[k2]))
    if cap_bottom:
        c = len(verts)
        verts.append(tuple(points[0]))
        a = rings[0]
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c, a[k2], a[k]))   # normal hacia -tangente (fuera)
    return verts, faces


def _box(sx, sy, sz, off=(0, 0, 0)):
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    ox, oy, oz = off
    verts = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
             (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    verts = [(a + ox, b + oy, c + oz) for (a, b, c) in verts]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]
    return verts, faces


def _doble(verts, faces):
    """Duplica la geometría con winding invertido (hojas visibles por las dos
    caras aunque el motor haga backface culling). Vértices duplicados para
    que las normales suaves de cada cara sean independientes."""
    n = len(verts)
    verts2 = list(verts) + list(verts)
    faces2 = list(faces) + [tuple(i + n for i in reversed(f)) for f in faces]
    return verts2, faces2


def _palma_frond(L, wmax, tanp, droop, yaw, base, doble=False):
    """Palma pinnada plana: tira de quads con nervio central elevado, arqueada
    (`tanp` = pendiente inicial, `droop` = caída cuadrática)."""
    ts = (0.0, 0.18, 0.40, 0.62, 0.82, 1.0)
    ws = (0.10, 0.58, 0.78, 0.62, 0.34, 0.02)
    cy, sy_ = math.cos(yaw), math.sin(yaw)
    bx, by, bz = base
    verts = []
    faces = []
    rows = []
    for t, wr in zip(ts, ws):
        x = t * L
        z = L * (tanp * t - droop * t * t)
        w = wmax * wr
        ridge = 0.22 * wmax * wr
        station = ((x, -w, z), (x, 0.0, z + ridge), (x, w, z))
        row = []
        for (lx, ly, lz) in station:
            gx = lx * cy - ly * sy_ + bx
            gy = lx * sy_ + ly * cy + by
            row.append(len(verts))
            verts.append((gx, gy, lz + bz))
        rows.append(row)
    for i in range(len(rows) - 1):
        l0, c0, r0 = rows[i]
        l1, c1, r1 = rows[i + 1]
        faces.append((l0, l1, c1, c0))
        faces.append((c0, c1, r1, r0))
    if doble:
        return _doble(verts, faces)
    return verts, faces


def _hoja_abanico(R, yaw, pitch, base, nseg=8, span=2.6, doble=True, serrado=0.86):
    """Hoja en abanico (palmito / Washingtonia): semicírculo de `nseg`
    triángulos desde el hub `base`, borde serrado, bordes ligeramente caídos.
    `pitch` > 0 levanta la punta; `yaw` orienta el abanico en planta."""
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    bx, by, bz = base

    def g(lx, ly, lz):
        x1 = lx * cp - lz * sp
        z1 = lx * sp + lz * cp
        return (x1 * cy_ - ly * sy_ + bx, x1 * sy_ + ly * cy_ + by, z1 + bz)

    verts = [g(0.0, 0.0, 0.0)]
    for k in range(nseg + 1):
        al = -span / 2.0 + span * k / nseg
        rk = R * (1.0 if k % 2 == 0 else serrado)
        verts.append(g(rk * math.cos(al), rk * math.sin(al), -0.10 * R * abs(math.sin(al))))
    faces = [(0, k + 1, k + 2) for k in range(nseg)]
    if doble:
        return _doble(verts, faces)
    return verts, faces


# ---------------------------------------------------------------------------
# Ayudantes de árbol: tronco ahusado/curvado, ramas, lóbulos de copa
# ---------------------------------------------------------------------------
def _tronco(mb, rng, alto, r0, r1, mat, lean=0.0, yaw=0.0, exp=1.6, wobble=0.0,
            npts=6, sides=7, anillos=0.0, base=(0.0, 0.0, 0.0)):
    """Tronco ahusado (r0 abajo -> r1 arriba), inclinado `lean` metros hacia
    `yaw` con perfil t**exp, con deriva aleatoria `wobble` por tramo (nudoso;
    el primer tramo queda centrado para que collares/raíces casen) y anillos
    alternos (`anillos` = sobre-radio relativo). Tronco cerrado por abajo.
    Devuelve (pts, radii)."""
    pts = []
    radii = []
    dx = dy = 0.0
    for i in range(npts):
        t = i / (npts - 1.0)
        if i > 1 and wobble:
            dx += rng.uniform(-1.0, 1.0) * wobble
            dy += rng.uniform(-1.0, 1.0) * wobble
        off = lean * (t ** exp)
        pts.append((base[0] + math.cos(yaw) * off + dx,
                    base[1] + math.sin(yaw) * off + dy,
                    base[2] + t * alto))
        r = r0 + (r1 - r0) * t
        if anillos and i % 2 == 1:
            r *= 1.0 + anillos
        radii.append(r)
    mb.add(*_tube(pts, radii, sides=sides, cap_bottom=True), mat, smooth=True)
    return pts, radii


def _pt_en_z(pts, z):
    """Punto de la polilínea del tronco a altura z (extrapola por encima)."""
    if z <= pts[0][2]:
        return Vector(pts[0])
    for i in range(len(pts) - 1):
        z0, z1 = pts[i][2], pts[i + 1][2]
        if z <= z1:
            t = (z - z0) / max(1e-6, z1 - z0)
            return Vector(pts[i]).lerp(Vector(pts[i + 1]), t)
    p0, p1 = Vector(pts[-2]), Vector(pts[-1])
    d = p1 - p0
    if d.z < 1e-6:
        return p1.copy()
    return p1 + d * ((z - p1.z) / d.z)


def _rama(mb, p0, p2, r0, r1, mat, comba=0.0, sides=5):
    """Rama: tubo de 3 puntos p0 -> p2 combado `comba` metros hacia arriba."""
    p0 = Vector(p0)
    p2 = Vector(p2)
    p1 = (p0 + p2) / 2.0 + Vector((0.0, 0.0, comba))
    mb.add(*_tube([p0, p1, p2], [r0, (r0 + r1) / 2.0, r1], sides=sides), mat, smooth=True)


def _lobulo(mb, rng, centro, r, mat, esc=(1.0, 1.0, 0.85), jit=0.10, seg=8, rings=5, yaw=0.0):
    mb.add(*_sphere(r, seg=seg, rings=rings, scale=esc, off=tuple(centro), rng=rng, jit=jit, yaw=yaw),
           mat, smooth=True)


def _anillo_lobulos(mb, rng, centro, n, d, r, mats, z_jit=0.0, esc_z=0.85, jit=0.10,
                    seg=8, rings=5, yaw0=None, esc_xy=(0.9, 1.15)):
    """n lóbulos en anillo alrededor de `centro`, a distancia ~d y radio ~r,
    alternando los materiales de `mats`."""
    if yaw0 is None:
        yaw0 = rng.uniform(0.0, TAU)
    cx, cy, cz = centro
    for i in range(n):
        ang = yaw0 + TAU * i / n + rng.uniform(-0.3, 0.3) * (TAU / n)
        dd = d * rng.uniform(0.80, 1.15)
        rr = r * rng.uniform(0.85, 1.15)
        z = cz + rng.uniform(-z_jit, z_jit)
        _lobulo(mb, rng, (cx + math.cos(ang) * dd, cy + math.sin(ang) * dd, z), rr,
                mats[i % len(mats)],
                esc=(rng.uniform(*esc_xy), rng.uniform(*esc_xy), esc_z),
                jit=jit, seg=seg, rings=rings)


def _flores_sobre(mb, rng, blobs, n, mats, r_flor=(0.20, 0.28), sesgo_arriba=0.55):
    """`n` racimos de flores (esferas de 20 tris) sobre la superficie
    superior de los lóbulos `blobs` = [(r, (cx,cy,cz), esc_z), ...]."""
    for i in range(n):
        r, c, ez = blobs[rng.randrange(len(blobs))]
        ang = rng.uniform(0.0, TAU)
        # dirección con sesgo hacia arriba (flores en la parte alta y visible)
        up = rng.uniform(sesgo_arriba, 1.0)
        hz = math.sqrt(max(0.0, 1.0 - up * up))
        p = (c[0] + math.cos(ang) * hz * r * 0.92,
             c[1] + math.sin(ang) * hz * r * 0.92,
             c[2] + up * r * ez * 0.92)
        mb.add(*_sphere(rng.uniform(*r_flor), seg=5, rings=3, off=p),
               mats[i % len(mats)], smooth=True)


def _elegir_variante(variante, seed, lista, pieza):
    """Variante automática (seed % N) o validación de la explícita.
    Devuelve (variante, automatica)."""
    if variante is None:
        return lista[seed % len(lista)], True
    if variante not in lista:
        raise ValueError("variante desconocida para %s: %r (válidas: %s)"
                         % (pieza, variante, ", ".join(lista)))
    return variante, False


# ---------------------------------------------------------------------------
# PALMERAS
# ---------------------------------------------------------------------------
_PALMERA_VARIANTES = ("datil", "washingtonia", "abanico")
_ALTO_MAX_ABANICO = 5.0     # palmito: tope de alto en reparto automático


def build_palmera(parent_collection, alto=8.0, seed=0, variante=None):
    """Palmera con tres siluetas (seed % 3 o `variante`): "datil"
    (tronco grueso escamado, palmas largas y caídas), "washingtonia" (tronco
    altísimo y fino, corona pequeña de abanicos + falda seca) y "abanico"
    (palmito: 1-3 troncos cortos gruesos, hojas en abanico). `alto` es
    nominal; el palmito elegido automáticamente se limita a 5 m."""
    rng = random.Random(7919 * seed + 11)
    variante, auto = _elegir_variante(variante, seed, _PALMERA_VARIANTES, "palmera")
    mb = _MB()
    a = alto
    if auto and variante == "abanico":
        a = min(alto, _ALTO_MAX_ABANICO)

    if variante == "datil":
        yaw = rng.uniform(0.0, TAU)
        pts, radii = _tronco(mb, rng, a * 0.76, 0.060 * a, 0.040 * a, _mat("tronco_palmera"),
                             lean=rng.uniform(0.08, 0.18) * a, yaw=yaw, exp=1.7,
                             npts=9, sides=7, anillos=0.16)
        crown = Vector(pts[-1])
        mb.add(*_sphere(0.055 * a + 0.10, seg=7, rings=4, off=crown), _mat("palma"), smooth=True)
        for _ in range(2):  # racimos de dátiles colgando
            ang = rng.uniform(0.0, TAU)
            cc = crown + Vector((math.cos(ang) * 0.11 * a, math.sin(ang) * 0.11 * a, -0.10 * a))
            mb.add(*_sphere(0.045 * a, seg=6, rings=3, scale=(0.8, 0.8, 1.5), off=cc),
                   _mat("datil"), smooth=True)
        nf = rng.randint(15, 17)
        Lf = a * 0.50
        for i in range(nf):
            yawf = TAU * i / nf + rng.uniform(-0.15, 0.15)
            tier = i % 4
            if tier == 0:       # palmas altas, casi verticales y cortas
                tanp, droop, key, fl = rng.uniform(1.1, 1.4), rng.uniform(0.70, 0.90), "palma", 0.80
            elif tier == 1:     # palmas medias-altas
                tanp, droop, key, fl = rng.uniform(0.60, 0.80), rng.uniform(0.70, 0.90), "palma", 1.0
            elif tier == 2:     # palmas medias
                tanp, droop, key, fl = rng.uniform(0.30, 0.50), rng.uniform(0.85, 1.05), "palma_clara", 1.0
            else:               # palmas bajas muy caídas
                tanp, droop, key, fl = rng.uniform(0.05, 0.20), rng.uniform(1.00, 1.25), "palma_clara", 0.95
            L = Lf * fl * rng.uniform(0.88, 1.05)
            mb.add(*_palma_frond(L, Lf * 0.19, tanp, droop, yawf, crown, doble=True),
                   _mat(key), smooth=True)

    elif variante == "washingtonia":
        yaw = rng.uniform(0.0, TAU)
        ht = 0.76 * a           # las hojas altas (0.22-0.26a) llevan la cima a ~1.0a
        pts, radii = _tronco(mb, rng, ht, 0.032 * a, 0.024 * a, _mat("tronco_wash"),
                             lean=rng.uniform(0.02, 0.07) * a, yaw=yaw, exp=1.8,
                             npts=6, sides=8)
        crown = Vector(pts[-1])
        # falda estrecha de hojas secas pegada al tronco bajo la corona:
        # sombreado plano, borde inferior irregular, anillos centrados en el
        # tronco inclinado (no en la vertical de la corona)
        falda = [(0.030 * a, ht - 0.26 * a), (0.058 * a, ht - 0.19 * a), (0.068 * a, ht - 0.10 * a),
                 (0.052 * a, ht - 0.03 * a), (0.0, ht)]
        fv, ff = _lathe(falda, seg=8, rng=rng, jit=0.14)
        z_base = falda[0][1]
        fv2 = []
        for (x, y, z) in fv:
            c = _pt_en_z(pts, z)
            dz = rng.uniform(-0.035, 0.015) * a if abs(z - z_base) < 1e-6 else 0.0
            fv2.append((x + c.x, y + c.y, z + dz))
        mb.add(fv2, ff, _mat("palma_seca"), smooth=False)
        mb.add(*_sphere(0.055 * a, seg=6, rings=3, off=crown), _mat("palma_wash"), smooth=True)
        # corona: 12-14 abanicos en 4 pisos (alto, medio y dos caídos) para
        # que la bola verde domine sobre la falda
        nh = rng.randint(12, 14)
        Rh = a * rng.uniform(0.22, 0.26)
        for i in range(nh):
            yawh = TAU * i / nh + rng.uniform(-0.2, 0.2)
            tier = i % 4
            if tier == 0:
                pitch, hz = rng.uniform(65.0, 85.0), 0.03
            elif tier == 1:
                pitch, hz = rng.uniform(25.0, 40.0), 0.02
            elif tier == 2:
                pitch, hz = rng.uniform(-12.0, 2.0), 0.0
            else:
                pitch, hz = rng.uniform(-40.0, -22.0), -0.01
            pitch = math.radians(pitch)
            hub = crown + Vector((math.cos(yawh) * 0.05 * a, math.sin(yawh) * 0.05 * a, hz * a))
            mb.add(*_tube([crown, hub], [0.008 * a, 0.006 * a], sides=4, cap_top=False),
                   _mat("tronco_wash"), smooth=True)
            key = "palma_wash" if i % 2 == 0 else "palma_wash_clara"
            mb.add(*_hoja_abanico(Rh, yawh, pitch, hub, nseg=7), _mat(key), smooth=True)

    else:  # abanico (palmito)
        nt = rng.choice((1, 2, 2, 3))
        yaw0 = rng.uniform(0.0, TAU)
        for k in range(nt):
            ang = yaw0 + TAU * k / max(1, nt)
            bx = math.cos(ang) * 0.06 * a * (nt > 1)
            by = math.sin(ang) * 0.06 * a * (nt > 1)
            # el primer tronco es el alto (fija la cima en ~0.92a); el resto más bajos
            h = a * (0.50 if k == 0 else rng.uniform(0.34, 0.46))
            pts, radii = _tronco(mb, rng, h, 0.050 * a, 0.040 * a, _mat("tronco_abanico"),
                                 lean=0.10 * a * (nt > 1) + 0.03 * a, yaw=ang, exp=1.3,
                                 npts=5, sides=7, anillos=0.16, base=(bx, by, 0.0))
            crown = Vector(pts[-1])
            mb.add(*_sphere(0.045 * a, seg=6, rings=3, off=crown), _mat("palma_abanico"), smooth=True)
            nh = rng.randint(8, 10) if nt < 3 else 7
            Rh = a * rng.uniform(0.28, 0.32)
            for i in range(nh):
                yawh = TAU * i / nh + rng.uniform(-0.25, 0.25)
                pitch = math.radians(80.0 - 90.0 * (i % 3) / 2.0 + rng.uniform(-8.0, 8.0))
                cp = math.cos(pitch)
                pet = 0.12 * a
                hub = crown + Vector((math.cos(yawh) * pet * cp, math.sin(yawh) * pet * cp,
                                      pet * math.sin(pitch)))
                mb.add(*_tube([crown, hub], [0.010 * a, 0.007 * a], sides=4, cap_top=False),
                       _mat("tronco_abanico"), smooth=True)
                key = "palma_abanico" if i % 2 == 0 else "palma_abanico_clara"
                mb.add(*_hoja_abanico(Rh, yawh, pitch, hub, nseg=7), _mat(key), smooth=True)

    ob = mb.build("%s_palmera" % PREFIX, parent_collection)
    ob["VEG_variante"] = variante
    return ob


# ---------------------------------------------------------------------------
# CIPRESES
# ---------------------------------------------------------------------------
_CIPRES_VARIANTES = ("lapiz", "llama")


def _radio_perfil(perfil, z):
    for i in range(len(perfil) - 1):
        (r0, z0), (r1, z1) = perfil[i], perfil[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / max(1e-6, z1 - z0)
            return r0 + (r1 - r0) * t
    return 0.0


def build_cipres(parent_collection, alto=10.0, seed=0, variante=None):
    """Ciprés: "lapiz" (huso muy esbelto) o "llama" (más lleno, punta ladeada).
    Huso principal + 4-8 lóbulos verticales pegados que rompen la silueta."""
    rng = random.Random(7919 * seed + 23)
    variante, _ = _elegir_variante(variante, seed, _CIPRES_VARIANTES, "cipres")
    mb = _MB()
    a = alto
    tono = rng.choice(("cipres", "cipres_b"))
    m_osc, m_luz = _mat(tono), _mat(tono + "_luz")

    rt = 0.012 * a + 0.05
    mb.add(*_lathe([(0.0, 0.0), (rt, 0.0), (rt * 0.9, 0.10 * a), (0.0, 0.11 * a)], seg=7),
           _mat("tronco"), smooth=True)

    if variante == "lapiz":
        rm = 0.055 * a
        perfil = [(0.0, 0.05 * a), (0.62 * rm, 0.10 * a), (0.95 * rm, 0.24 * a), (rm, 0.40 * a),
                  (0.90 * rm, 0.56 * a), (0.72 * rm, 0.72 * a), (0.45 * rm, 0.86 * a),
                  (0.18 * rm, 0.95 * a), (0.0, a)]
        nl = rng.randint(4, 6)
        esc_l = (0.55, 0.55, 1.9)
        bend = 0.012 * a
    else:
        rm = 0.115 * a
        perfil = [(0.0, 0.05 * a), (0.55 * rm, 0.09 * a), (0.88 * rm, 0.20 * a), (rm, 0.32 * a),
                  (0.94 * rm, 0.46 * a), (0.78 * rm, 0.60 * a), (0.55 * rm, 0.74 * a),
                  (0.32 * rm, 0.86 * a), (0.12 * rm, 0.95 * a), (0.0, a)]
        nl = rng.randint(6, 8)
        esc_l = (0.60, 0.60, 1.7)
        bend = 0.05 * a
    byaw = rng.uniform(0.0, TAU)
    bx, by = math.cos(byaw) * bend, math.sin(byaw) * bend

    def curva(z):
        f = (max(0.0, z) / a) ** 3
        return bx * f, by * f

    verts, faces = _lathe(perfil, seg=9, rng=rng, jit=0.05)
    verts = [(x + curva(z)[0], y + curva(z)[1], z) for (x, y, z) in verts]
    mb.add(verts, faces, m_osc, smooth=True)

    # lóbulos verticales que sobresalen del huso (bultos de silueta, no
    # parches de color: solo uno de cada tres es del tono claro)
    ang = rng.uniform(0.0, TAU)
    for i in range(nl):
        z = a * (0.15 + 0.68 * (i + rng.uniform(0.1, 0.9)) / nl)
        rp = _radio_perfil(perfil, z)
        ang += rng.uniform(1.8, 2.8)
        rl = rp * rng.uniform(0.50, 0.70)
        d = rp * 0.88
        ox, oy = curva(z)
        _lobulo(mb, rng, (ox + math.cos(ang) * d, oy + math.sin(ang) * d, z), rl,
                m_luz if i % 3 == 1 else m_osc, esc=esc_l, jit=0.10, seg=7, rings=4)
    ob = mb.build("%s_cipres" % PREFIX, parent_collection)
    ob["VEG_variante"] = variante
    return ob


# ---------------------------------------------------------------------------
# PINOS
# ---------------------------------------------------------------------------
_PINO_VARIANTES = ("parasol", "carrasco", "costero", "joven")
_ALTO_MAX_JOVEN = 7.0       # pino joven: tope de alto en reparto automático


def build_pino(parent_collection, alto=12.0, seed=0, variante=None):
    """Pino con cuatro siluetas (seed % 4 o `variante`): "parasol" (piñonero:
    tronco alto desnudo + copa plana ancha), "carrasco" (alto y estrecho, copa
    cónica irregular de 4-5 lóbulos apilados a lados alternos), "costero"
    (batido por el viento, tronco muy inclinado y copa en bandera) y "joven"
    (piñonero joven: tronco corto, copa ovoide densa y clara). `alto` es
    nominal; el "joven" elegido automáticamente se limita a 7 m."""
    rng = random.Random(7919 * seed + 37)
    variante, auto = _elegir_variante(variante, seed, _PINO_VARIANTES, "pino")
    mb = _MB()
    a = alto
    if auto and variante == "joven":
        a = min(alto, _ALTO_MAX_JOVEN)
    m_tr = _mat("tronco")
    tono = rng.choice(("pino_a", "pino_b", "pino_c"))
    if variante == "joven":
        tono = "pino_joven"
    m_osc, m_luz = _mat(tono), _mat(tono + "_luz")
    yaw = rng.uniform(0.0, TAU)

    if variante == "parasol":
        pts, radii = _tronco(mb, rng, a * 0.78, 0.032 * a, 0.014 * a, m_tr,
                             lean=rng.uniform(0.05, 0.12) * a, yaw=yaw, exp=1.5,
                             wobble=0.006 * a, npts=6, sides=7)
        top = Vector(pts[-1])
        z0 = 0.76 * a
        R = rng.uniform(0.38, 0.46) * a
        cx, cy = top.x * 0.7, top.y * 0.7
        nb = rng.randint(3, 4)
        for i in range(nb):  # ramas hacia el borde de la copa
            ang = yaw + TAU * i / nb + rng.uniform(-0.4, 0.4)
            p2 = (cx + math.cos(ang) * 0.62 * R, cy + math.sin(ang) * 0.62 * R, z0 + 0.07 * a)
            _rama(mb, pts[3], p2, 0.014 * a, 0.006 * a, m_tr, comba=0.02 * a)
        copa = [(0.0, z0 - 0.03 * a), (0.66 * R, z0 - 0.005 * a), (R, z0 + 0.05 * a),
                (0.86 * R, z0 + 0.11 * a), (0.50 * R, z0 + 0.16 * a), (0.0, z0 + 0.19 * a)]
        mb.add(*_lathe(copa, seg=10, off=(cx, cy, 0.0), rng=rng, jit=0.07), m_osc, smooth=True)
        nl = rng.randint(5, 6)
        _anillo_lobulos(mb, rng, (cx, cy, z0 + 0.14 * a), nl, 0.40 * R, 0.30 * R,
                        (m_luz, m_osc), z_jit=0.02 * a, esc_z=0.50, jit=0.08)
        for _ in range(rng.randint(1, 2)):  # lóbulos colgando del borde (asimetría)
            ang = rng.uniform(0.0, TAU)
            d = R * rng.uniform(0.75, 0.95)
            _lobulo(mb, rng, (cx + math.cos(ang) * d, cy + math.sin(ang) * d, z0 + 0.02 * a),
                    0.26 * R, m_osc, esc=(1.0, 1.0, 0.55), jit=0.08, seg=7, rings=4)

    elif variante == "carrasco":
        pts, radii = _tronco(mb, rng, a * 0.62, 0.028 * a, 0.010 * a, m_tr,
                             lean=rng.uniform(0.04, 0.10) * a, yaw=yaw, exp=1.3,
                             wobble=0.012 * a, npts=7, sides=7)
        # copa cónica irregular: 4-5 lóbulos alargados, muy solapados en z,
        # cada uno desplazado a un lado alterno del tronco y estirado en esa
        # dirección (silueta ladeada, no muñeco de nieve)
        nlob = rng.randint(4, 5)
        ang = rng.uniform(0.0, TAU)
        for i in range(nlob):
            t = i / (nlob - 1.0)
            z = 0.44 * a + 0.42 * a * t          # paso <= 0.14a con semieje z >= 0.09a: sin cuellos
            r = a * (0.155 - 0.060 * t) * rng.uniform(0.90, 1.10)
            ang += math.pi + rng.uniform(-0.7, 0.7)          # lado alterno
            dl = rng.uniform(0.07, 0.12) * a * (1.0 - 0.45 * t)
            c = _pt_en_z(pts, z)
            c.x += math.cos(ang) * dl
            c.y += math.sin(ang) * dl
            _lobulo(mb, rng, c, r, m_luz if i % 2 else m_osc,
                    esc=(rng.uniform(1.10, 1.35), rng.uniform(0.80, 1.00), 0.95), jit=0.12,
                    yaw=ang + rng.uniform(-0.5, 0.5))
            if i < nlob - 1 and i % 2 == 0:  # rama bajo el lóbulo, punta dentro de él
                p2 = (c.x + math.cos(ang) * r * 0.75, c.y + math.sin(ang) * r * 0.75, z - 0.30 * r)
                _rama(mb, _pt_en_z(pts, z - 0.90 * r), p2, 0.010 * a, 0.004 * a, m_tr, comba=0.01 * a)
        tip = _pt_en_z(pts, 0.93 * a)
        _lobulo(mb, rng, tip, 0.06 * a, m_luz, esc=(1.0, 1.0, 1.3), jit=0.10, seg=6, rings=4)

    elif variante == "costero":
        w = Vector((math.cos(yaw), math.sin(yaw), 0.0))
        pts, radii = _tronco(mb, rng, a * 0.75, 0.034 * a, 0.013 * a, m_tr,
                             lean=rng.uniform(0.30, 0.42) * a, yaw=yaw, exp=1.25,
                             wobble=0.010 * a, npts=7, sides=7)
        top = Vector(pts[-1])
        _rama(mb, pts[-2], top + w * 0.34 * a + Vector((0, 0, 0.03 * a)),
              0.013 * a, 0.005 * a, m_tr, comba=0.03 * a)
        p_bar = Vector(pts[-3]) - w * 0.10 * a + Vector((0, 0, 0.07 * a))  # rama a barlovento
        _rama(mb, pts[-3], p_bar, 0.010 * a, 0.004 * a, m_tr, comba=0.02 * a)
        # copa en bandera: cuña de lóbulos gruesos hacia sotavento, en dos
        # pisos, más larga y baja cuanto más lejos del tronco
        lobos = [(-0.06, 0.00, 0.12), (0.10, 0.00, 0.15), (0.27, -0.01, 0.14), (0.43, -0.03, 0.115),
                 (0.04, 0.12, 0.11), (0.22, 0.11, 0.115), (0.36, 0.08, 0.09)]
        for i, (d, dz, r) in enumerate(lobos):
            lat = rng.uniform(-0.06, 0.06) * a
            c = top + w * (d * a) + Vector((-w.y * lat, w.x * lat, 0.0))
            c.z = top.z + (dz + rng.uniform(-0.015, 0.015)) * a
            _lobulo(mb, rng, c, r * a * rng.uniform(0.9, 1.1), m_luz if i % 2 else m_osc,
                    esc=(1.35, 1.0, 0.62), jit=0.10, yaw=yaw, seg=7, rings=4)
        # mechón a barlovento sobre su rama, solapando el tronco
        c2 = Vector(pts[-3]) - w * 0.06 * a + Vector((0, 0, 0.05 * a))
        _lobulo(mb, rng, c2, 0.095 * a, m_osc, esc=(1.1, 1.0, 0.6), jit=0.10, seg=7, rings=4, yaw=yaw)

    else:  # joven: piñonero joven, copa ovoide densa (más ancha abajo) sobre tronco corto
        pts, radii = _tronco(mb, rng, a * 0.25, 0.030 * a, 0.020 * a, m_tr,
                             lean=rng.uniform(0.01, 0.03) * a, yaw=yaw, exp=1.5, npts=4, sides=7)
        cx, cy = pts[-1][0] * 0.5, pts[-1][1] * 0.5
        # anillo bajo de 5 lóbulos anchos: la base de la copa es lo más ancho
        _anillo_lobulos(mb, rng, (cx, cy, 0.45 * a), 5, 0.17 * a, 0.19 * a,
                        (m_osc, m_luz), z_jit=0.03 * a, esc_z=0.85, jit=0.10, seg=7, rings=4,
                        esc_xy=(0.95, 1.20))
        # núcleo + 2-3 lóbulos superiores solapados que cierran el óvalo (sin punta)
        _lobulo(mb, rng, (cx, cy, 0.60 * a), 0.22 * a, m_osc, esc=(1.0, 1.0, 0.90), jit=0.08)
        _anillo_lobulos(mb, rng, (cx, cy, 0.72 * a), rng.randint(2, 3), 0.09 * a, 0.16 * a,
                        (m_luz, m_osc), z_jit=0.02 * a, esc_z=0.85, jit=0.10, seg=7, rings=4)
        _lobulo(mb, rng, (cx + rng.uniform(-0.03, 0.03) * a, cy + rng.uniform(-0.03, 0.03) * a, 0.85 * a),
                0.13 * a, m_luz, esc=(1.0, 1.0, 0.90), jit=0.10, seg=7, rings=4)

    ob = mb.build("%s_pino" % PREFIX, parent_collection)
    ob["VEG_variante"] = variante
    return ob


# ---------------------------------------------------------------------------
# ADELFAS Y ARBUSTOS
# ---------------------------------------------------------------------------
_ADELFA_VARIANTES = ("rosa", "blanca", "roja")


def build_adelfa(parent_collection, seed=0, variante=None):
    """Adelfa: "rosa" (mata redonda compacta ~1.9 m), "blanca" (mata alta en
    vaso ~2.6 m con tallos visibles) o "roja" (mata baja y extendida ~1.5 m).
    Lóbulos hundidos ligeramente bajo z=0 para que nunca parezca flotar."""
    rng = random.Random(7919 * seed + 53)
    variante, _ = _elegir_variante(variante, seed, _ADELFA_VARIANTES, "adelfa")
    mb = _MB()
    m_h = _mat(rng.choice(("adelfa_hoja", "adelfa_hoja_b")))

    def jp(c, s=0.10):
        return (c[0] + rng.uniform(-s, s), c[1] + rng.uniform(-s, s), c[2] + rng.uniform(-s, s) * 0.5)

    if variante == "rosa":
        blobs = [(0.95, (0.0, 0.0, 0.78)), (0.70, (0.62, 0.30, 0.66)), (0.68, (-0.58, -0.28, 0.68)),
                 (0.60, (0.10, -0.55, 0.72)), (0.56, (-0.15, 0.50, 1.15))]
        flores = ("flor_rosa", "flor_rosa_clara")
        ez = 0.90
    elif variante == "blanca":
        blobs = [(0.78, (0.0, 0.0, 1.85)), (0.66, (0.70, 0.20, 1.55)), (0.62, (-0.62, -0.30, 1.60)),
                 (0.56, (0.15, -0.72, 1.45)), (0.52, (-0.22, 0.62, 1.50))]
        flores = ("flor_blanca", "flor_crema")
        ez = 0.92
        for r, c in blobs[1:]:  # tallos visibles desde el suelo
            p0 = (c[0] * 0.25, c[1] * 0.25, 0.0)
            mb.add(*_tube([p0, (c[0] * 0.7, c[1] * 0.7, c[2] * 0.55), c],
                          [0.05, 0.04, 0.03], sides=4, cap_top=False), _mat("tronco"), smooth=True)
    else:  # roja
        blobs = [(0.82, (0.0, 0.0, 0.62)), (0.70, (1.00, 0.30, 0.55)), (0.68, (-1.00, -0.20, 0.57)),
                 (0.62, (0.30, -0.90, 0.50)), (0.60, (-0.30, 0.85, 0.53)), (0.50, (0.60, 0.70, 0.72))]
        flores = ("flor_roja", "flor_roja_clara")
        ez = 0.82

    blobs = [(r * rng.uniform(0.92, 1.08), jp(c), ez) for (r, c) in blobs]
    for r, c, e in blobs:
        _lobulo(mb, rng, c, r, m_h, esc=(1.0, 1.0, e), jit=0.10, seg=7, rings=4)
    n_fl = {"rosa": 14, "blanca": 10, "roja": 12}[variante]   # presupuesto <= 500 tris
    _flores_sobre(mb, rng, blobs, n_fl, [_mat(k) for k in flores])
    ob = mb.build("%s_adelfa" % PREFIX, parent_collection)
    ob["VEG_variante"] = variante
    return ob


_ARBUSTO_VARIANTES = ("romero", "lavanda", "retama")


def build_arbusto(parent_collection, tam=1.5, seed=0, variante=None):
    """Arbusto mediterráneo genérico de diámetro ~`tam`: "romero" (mata
    baja gris-verde, puntitos azul pálido), "lavanda" (gris-verde con
    espigas moradas) o "retama" (más alta, verde vivo con flores amarillas)."""
    rng = random.Random(7919 * seed + 61)
    variante, _ = _elegir_variante(variante, seed, _ARBUSTO_VARIANTES, "arbusto")
    mb = _MB()
    # por variante: altura relativa, materiales, flor, nº flores, escala y radio
    # de flor, nº lóbulos, radio y distancia relativos de lóbulo, ez máximo,
    # y cota relativa del centro del lóbulo
    if variante == "romero":
        h, mats, flor, nfl, esc_fl, r_fl = 0.55, ("romero", "romero_luz"), "flor_romero", 8, (1, 1, 1), (0.035, 0.05)
        nb_r, rr, dd, ez_max, cz = (4, 6), (0.45, 0.62), (0.25, 0.55), 9.0, (0.72, 0.72)
    elif variante == "lavanda":
        h, mats, flor, nfl, esc_fl, r_fl = 0.50, ("lavanda", "lavanda_luz"), "flor_lavanda", 12, (0.55, 0.55, 2.2), (0.05, 0.07)
        nb_r, rr, dd, ez_max, cz = (4, 6), (0.45, 0.62), (0.25, 0.55), 9.0, (0.72, 0.72)
    else:   # retama: mata más alta de 6-7 lóbulos pequeños desplazados (no
            # un barril), flores amarillas grandes y abundantes
        h, mats, flor, nfl, esc_fl, r_fl = 0.85, ("retama", "retama_luz"), "flor_amarilla", 16, (1, 1, 1), (0.06, 0.08)
        nb_r, rr, dd, ez_max, cz = (6, 7), (0.30, 0.42), (0.30, 0.65), 1.2, (0.75, 0.95)
    # paleta v2: un 12 % de los arbustos con flor llevan buganvilla (acento, pequenas dosis);
    # sorteo con generador propio por seed: la geometria del arbusto no cambia
    if random.Random(7919 * seed + 67).random() < 0.12:
        flor = "buganvilla"
    m0, m1 = _mat(mats[0]), _mat(mats[1])
    R = tam / 2.0
    nb = rng.randint(*nb_r)
    blobs = []
    for i in range(nb):
        ang = TAU * i / nb + rng.uniform(-0.4, 0.4)
        d = R * rng.uniform(*dd)
        r = R * rng.uniform(*rr)
        ez = min(ez_max, h * tam / (2.0 * r) * rng.uniform(0.8, 1.0))
        c = (math.cos(ang) * d, math.sin(ang) * d, r * ez * rng.uniform(*cz))
        blobs.append((r, c, ez))
        _lobulo(mb, rng, c, r, m0 if i % 2 == 0 else m1,
                esc=(rng.uniform(0.9, 1.15), rng.uniform(0.9, 1.15), ez), jit=0.12, seg=7, rings=4)
    m_f = _mat(flor)
    for i in range(nfl):
        r, c, ez = blobs[rng.randrange(len(blobs))]
        ang = rng.uniform(0.0, TAU)
        hz = rng.uniform(0.0, 0.75)
        up = math.sqrt(1.0 - hz * hz)
        p = (c[0] + math.cos(ang) * hz * r * 0.9, c[1] + math.sin(ang) * hz * r * 0.9,
             c[2] + up * r * ez * 0.9)
        rf = rng.uniform(*r_fl) * tam
        mb.add(*_sphere(rf, seg=4, rings=2, scale=esc_fl, off=(p[0], p[1], p[2] + rf * esc_fl[2] * 0.5)),
               m_f, smooth=True)
    ob = mb.build("%s_arbusto" % PREFIX, parent_collection)
    ob["VEG_variante"] = variante
    return ob


# ---------------------------------------------------------------------------
# OLIVO, ENCINA, PLÁTANO
# ---------------------------------------------------------------------------
def build_olivo(parent_collection, alto=5.0, seed=0):
    """Olivo: tronco retorcido y nudoso con collar de raíces, 2-3 ramas y copa
    irregular en 5-6 masas verde salvia / verde plata."""
    rng = random.Random(7919 * seed + 113)
    mb = _MB()
    a = alto
    m_tr = _mat("tronco_olivo")
    ht = a * rng.uniform(0.40, 0.48)
    yaw = rng.uniform(0.0, TAU)
    pts, radii = _tronco(mb, rng, ht, 0.080 * a, 0.038 * a, m_tr,
                         lean=rng.uniform(0.04, 0.10) * a, yaw=yaw, exp=1.2,
                         wobble=0.040 * a, npts=7, sides=8, anillos=0.22)
    # collar de raíces cerrado (polo abajo y arriba; el anillo superior queda
    # dentro del tronco: 0.060a < radio del tronco a esa cota)
    collar = [(0.0, 0.0), (0.155 * a, 0.0), (0.110 * a, 0.05 * a), (0.060 * a, 0.11 * a),
              (0.0, 0.125 * a)]
    mb.add(*_lathe(collar, seg=8, rng=rng, jit=0.12), m_tr, smooth=True)
    for _ in range(3):  # nudos pegados al tronco
        i = rng.randint(1, len(pts) - 2)
        px, py, pz = pts[i]
        th = rng.uniform(0.0, TAU)
        mb.add(*_sphere(radii[i] * 0.72, seg=6, rings=3,
                        off=(px + math.cos(th) * radii[i] * 0.8, py + math.sin(th) * radii[i] * 0.8, pz),
                        rng=rng, jit=0.15), m_tr, smooth=True)
    top = Vector(pts[-1])
    nb = rng.randint(2, 3)
    yaw0 = rng.uniform(0.0, TAU)
    centros = []
    for i in range(nb):
        ang = yaw0 + TAU * i / nb + rng.uniform(-0.35, 0.35)
        d = a * rng.uniform(0.12, 0.22)
        c = Vector((top.x + math.cos(ang) * d, top.y + math.sin(ang) * d, a * rng.uniform(0.58, 0.68)))
        centros.append(c)
        _rama(mb, pts[-2], c - Vector((0, 0, 0.06 * a)), 0.040 * a, 0.016 * a, m_tr,
              comba=0.03 * a, sides=6)
    masas = list(centros)
    nm = rng.randint(5, 6)
    while len(masas) < nm - 1:
        ang = rng.uniform(0.0, TAU)
        d = a * rng.uniform(0.10, 0.26)
        masas.append(Vector((top.x + math.cos(ang) * d, top.y + math.sin(ang) * d,
                             a * rng.uniform(0.54, 0.72))))
    # dos masas salvia por cada plata: el plata es acento, no el tono dominante
    for i, c in enumerate(masas):
        r = a * rng.uniform(0.16, 0.27)
        _lobulo(mb, rng, c, r, _mat("olivo_plata" if i % 3 == 2 else "olivo_salvia"),
                esc=(rng.uniform(0.95, 1.30), rng.uniform(0.95, 1.30), rng.uniform(0.72, 0.88)),
                jit=0.13)
    # masa superior: su cota se deduce del radio para que la cima quede en ~0.97a
    r = a * rng.uniform(0.19, 0.24)
    ez = rng.uniform(0.75, 0.88)
    _lobulo(mb, rng, (top.x * 0.6, top.y * 0.6, 0.97 * a - r * ez), r,
            _mat("olivo_salvia" if nm % 2 else "olivo_plata"),
            esc=(rng.uniform(1.0, 1.3), rng.uniform(1.0, 1.3), ez), jit=0.11)
    return mb.build("%s_olivo" % PREFIX, parent_collection)


def build_encina(parent_collection, alto=9.0, seed=0):
    """Encina: tronco corto y grueso, 3-4 ramas, copa redonda densa verde
    oscuro (central + anillo de 5-6 + 2 superiores)."""
    rng = random.Random(7919 * seed + 149)
    mb = _MB()
    a = alto
    m_tr = _mat("tronco_encina")
    tono = rng.choice(("encina", "encina_b"))
    m_osc, m_luz = _mat(tono), _mat(tono + "_luz")
    yaw = rng.uniform(0.0, TAU)
    pts, radii = _tronco(mb, rng, a * 0.34, 0.050 * a, 0.032 * a, m_tr,
                         lean=rng.uniform(0.02, 0.06) * a, yaw=yaw, exp=1.4,
                         wobble=0.012 * a, npts=5, sides=8, anillos=0.08)
    # collar cerrado; anillo superior 0.040a < radio del tronco a esa cota (~0.046a)
    mb.add(*_lathe([(0.0, 0.0), (0.105 * a, 0.0), (0.075 * a, 0.04 * a), (0.040 * a, 0.08 * a),
                    (0.0, 0.09 * a)], seg=8, rng=rng, jit=0.10), m_tr, smooth=True)
    top = Vector(pts[-1])
    R = a * rng.uniform(0.34, 0.40)
    centro = (top.x * 0.5, top.y * 0.5, 0.64 * a)
    nb = rng.randint(3, 4)
    yaw0 = rng.uniform(0.0, TAU)
    for i in range(nb):
        ang = yaw0 + TAU * i / nb + rng.uniform(-0.3, 0.3)
        p2 = (centro[0] + math.cos(ang) * 0.55 * R, centro[1] + math.sin(ang) * 0.55 * R,
              centro[2] - 0.05 * a + rng.uniform(-0.03, 0.03) * a)
        _rama(mb, pts[-2], p2, 0.025 * a, 0.010 * a, m_tr, comba=0.02 * a, sides=6)
    _lobulo(mb, rng, centro, 0.72 * R, m_osc, esc=(1.0, 1.0, 0.85), jit=0.09)
    _anillo_lobulos(mb, rng, centro, rng.randint(5, 6), 0.55 * R, 0.54 * R, (m_luz, m_osc),
                    z_jit=0.12 * R, esc_z=0.85, jit=0.10)
    _anillo_lobulos(mb, rng, (centro[0], centro[1], centro[2] + 0.50 * R), 2, 0.25 * R, 0.45 * R,
                    (m_luz, m_osc), z_jit=0.05 * R, esc_z=0.80, jit=0.10)
    return mb.build("%s_encina" % PREFIX, parent_collection)


def build_platano(parent_collection, alto=14.0, seed=0):
    """Plátano de paseo: tronco alto moteado (placas claras), 3-4 ramas
    principales abiertas, copa amplia en tres pisos verde claro."""
    rng = random.Random(7919 * seed + 167)
    mb = _MB()
    a = alto
    m_tr, m_pl = _mat("tronco_platano"), _mat("tronco_platano_claro")
    tono = rng.choice(("platano", "platano_b"))
    m_osc, m_luz = _mat(tono), _mat(tono + "_luz")
    yaw = rng.uniform(0.0, TAU)
    pts, radii = _tronco(mb, rng, a * 0.42, 0.036 * a, 0.022 * a, m_tr,
                         lean=rng.uniform(0.02, 0.05) * a, yaw=yaw, exp=1.5,
                         wobble=0.008 * a, npts=6, sides=8)
    for _ in range(5):  # placas claras de la corteza
        z = a * rng.uniform(0.06, 0.38)
        c = _pt_en_z(pts, z)
        rr = _radio_perfil([(radii[0], 0.0), (radii[-1], a * 0.42)], z)
        ang = rng.uniform(0.0, TAU)
        mb.add(*_sphere(rr * 0.45, seg=5, rings=3, scale=(1.0, 1.0, 1.6),
                        off=(c.x + math.cos(ang) * rr * 0.78, c.y + math.sin(ang) * rr * 0.78, z),
                        rng=rng, jit=0.12), m_pl, smooth=True)
    top = Vector(pts[-1])
    R = a * rng.uniform(0.30, 0.36)
    nb = rng.randint(3, 4)
    yaw0 = rng.uniform(0.0, TAU)
    for i in range(nb):
        ang = yaw0 + TAU * i / nb + rng.uniform(-0.3, 0.3)
        d = a * rng.uniform(0.14, 0.22)
        p2 = (top.x + math.cos(ang) * d, top.y + math.sin(ang) * d, a * rng.uniform(0.60, 0.70))
        _rama(mb, top, p2, 0.020 * a, 0.008 * a, m_tr, comba=0.03 * a, sides=6)
    cx, cy = top.x * 0.8, top.y * 0.8
    _anillo_lobulos(mb, rng, (cx, cy, 0.56 * a), 5, 0.70 * R, 0.42 * R, (m_osc, m_luz),
                    z_jit=0.03 * a, esc_z=0.75, jit=0.10, esc_xy=(1.0, 1.2))
    _anillo_lobulos(mb, rng, (cx, cy, 0.71 * a), 4, 0.45 * R, 0.42 * R, (m_luz, m_osc),
                    z_jit=0.02 * a, esc_z=0.78, jit=0.10)
    _lobulo(mb, rng, (cx, cy, 0.87 * a), 0.40 * R, m_luz, esc=(1.1, 1.1, 0.85), jit=0.10)
    ang = rng.uniform(0.0, TAU)
    _lobulo(mb, rng, (cx + math.cos(ang) * 0.35 * R, cy + math.sin(ang) * 0.35 * R, 0.81 * a),
            0.30 * R, m_osc, esc=(1.0, 1.0, 0.8), jit=0.10, seg=7, rings=4)
    return mb.build("%s_platano" % PREFIX, parent_collection)


# ---------------------------------------------------------------------------
# JARDINERA, ROCA, ACANTILADO (v1)
# ---------------------------------------------------------------------------
def build_jardinera(parent_collection, largo=6.0, seed=0):
    """Jardinera de piedra con seto y flores rojas/rosas (horquilla Loews)."""
    rng = random.Random(7919 * seed + 71)
    mb = _MB()
    W = 1.5
    H = 0.75
    mb.add(*_box(largo, W, H, off=(0, 0, H / 2)), _mat("piedra"))
    mb.add(*_box(largo + 0.18, W + 0.18, 0.14, off=(0, 0, H - 0.07)), _mat("piedra"))
    mb.add(*_box(largo + 0.14, W + 0.14, 0.12, off=(0, 0, 0.06)), _mat("piedra"))
    mb.add(*_sphere(1.0, seg=10, rings=5, scale=(largo * 0.47, W * 0.44, 0.42),
                    off=(0, 0, H + 0.06), rng=rng, jit=0.06),
           _mat("adelfa_hoja"), smooth=True)
    n = max(5, int(largo * 2.2))
    for i in range(n):
        t = (i + 0.5) / n
        x = (t - 0.5) * (largo - 0.8)
        y = 0.28 if i % 2 == 0 else -0.28
        key = "flor_roja" if i % 2 == 0 else "flor_rosa"
        mb.add(*_sphere(rng.uniform(0.20, 0.26), seg=6, rings=3,
                        off=(x, y + rng.uniform(-0.08, 0.08),
                             H + 0.34 + rng.uniform(-0.04, 0.06))),
               _mat(key), smooth=True)
    return mb.build("%s_jardinera" % PREFIX, parent_collection)


def build_roca(parent_collection, tam=3.0, seed=0):
    """Bolo calizo irregular, semienterrado (parte de la geometría bajo z=0)."""
    rng = random.Random(7919 * seed + 89)
    mb = _MB()
    mb.add(*_sphere(tam / 2.0, seg=8, rings=5,
                    scale=(rng.uniform(0.95, 1.15), rng.uniform(0.80, 0.95), 0.62),
                    off=(0, 0, tam * 0.24), rng=rng, jit=0.16),
           _mat("roca"))
    return mb.build("%s_roca" % PREFIX, parent_collection)


def build_acantilado(parent_collection, largo=40.0, alto=25.0, seed=0):
    """Acantilado calizo estratificado, tileable en X (frente hacia +Y).

    El perfil del frente y la ondulación de los bordes de estrato usan solo
    armónicos de periodo `largo`, así que dos módulos contiguos casan.
    """
    rng = random.Random(7919 * seed + 101)
    mb = _MB()

    nstr = max(4, int(round(alto / 3.6)))
    pesos = [rng.uniform(0.7, 1.35) for _ in range(nstr)]
    total = sum(pesos)
    zs = [0.0]
    for w in pesos:
        zs.append(zs[-1] + alto * w / total)
    zs[-1] = alto

    slope = 0.32 * alto
    ns = max(16, int(largo / 1.8))
    xs = [(-largo / 2.0) + largo * j / ns for j in range(ns + 1)]

    def _armonicos(a1r, a2r):
        return (rng.randint(1, 3), rng.uniform(*a1r), rng.uniform(0.0, TAU),
                rng.randint(3, 7), rng.uniform(*a2r), rng.uniform(0.0, TAU))

    par_y = []
    lean = []
    for i in range(nstr):
        zmid = (zs[i] + zs[i + 1]) / 2.0
        base = -slope * (zmid / alto)
        par_y.append((base,) + _armonicos((0.55, 0.95), (0.25, 0.50)))
        lean.append(rng.uniform(0.12, 0.45))
    par_z = [None] + [_armonicos((0.18, 0.40), (0.08, 0.20)) for _ in range(nstr - 1)] + [None]

    def yfun(x, i):
        base, k1, a1, p1, k2, a2, p2 = par_y[i]
        return (base + a1 * math.sin(TAU * k1 * x / largo + p1)
                + a2 * math.sin(TAU * k2 * x / largo + p2))

    def zfun(x, i):
        if i <= 0:
            return 0.0
        if i >= nstr:
            return alto
        k1, a1, p1, k2, a2, p2 = par_z[i]
        return (zs[i] + a1 * math.sin(TAU * k1 * x / largo + p1)
                + a2 * math.sin(TAU * k2 * x / largo + p2))

    mats = [_mat("caliza_clara"), _mat("caliza_ocre"), _mat("caliza_gris")]
    orden = []
    for i in range(nstr):
        if i % 2 == 0:
            orden.append(mats[0])
        else:
            orden.append(mats[1] if rng.random() < 0.7 else mats[2])

    for i in range(nstr):
        vs = []
        for j in range(ns + 1):
            vs.append((xs[j], yfun(xs[j], i), zfun(xs[j], i)))
        for j in range(ns + 1):
            vs.append((xs[j], yfun(xs[j], i) - lean[i], zfun(xs[j], i + 1)))
        fs = []
        for j in range(ns):
            b0, b1 = j, j + 1
            t0, t1 = ns + 1 + j, ns + 2 + j
            fs.append((b0, t0, t1, b1))
        mb.add(vs, fs, orden[i])

        if i < nstr - 1:
            vs2 = []
            for j in range(ns + 1):
                vs2.append((xs[j], yfun(xs[j], i) - lean[i], zfun(xs[j], i + 1)))
            for j in range(ns + 1):
                vs2.append((xs[j], yfun(xs[j], i + 1), zfun(xs[j], i + 1)))
            fs2 = []
            for j in range(ns):
                f0, f1 = j, j + 1
                k0, k1_ = ns + 1 + j, ns + 2 + j
                fs2.append((f1, f0, k0, k1_))
            mb.add(vs2, fs2, orden[i + 1])

    yback = -(slope + 0.18 * alto)
    vs3 = []
    for j in range(ns + 1):
        vs3.append((xs[j], yfun(xs[j], nstr - 1) - lean[nstr - 1], alto))
    for j in range(ns + 1):
        vs3.append((xs[j], yback, alto))
    fs3 = []
    for j in range(ns):
        f0, f1 = j, j + 1
        k0, k1_ = ns + 1 + j, ns + 2 + j
        fs3.append((f1, f0, k0, k1_))
    mb.add(vs3, fs3, _mat("caliza_clara"))

    nveg = int(largo / 5.0) + 3
    for _ in range(nveg):
        li = rng.randint(1, nstr - 1)
        xr = rng.uniform(-0.45, 0.45) * largo
        ymid = (yfun(xr, li - 1) - lean[li - 1] + yfun(xr, li)) / 2.0
        r = rng.uniform(0.6, 1.3)
        mb.add(*_sphere(r, seg=7, rings=4, scale=(1.4, 0.9, 0.55),
                        off=(xr, ymid, zfun(xr, li) + r * 0.2), rng=rng, jit=0.15),
               _mat("colgante"), smooth=True)

    return mb.build("%s_acantilado" % PREFIX, parent_collection)


# ---------------------------------------------------------------------------
# DESPACHADOR
# ---------------------------------------------------------------------------
# tipo: (constructor, rango de alto (o de tam para arbusto), peso aleatorio)
_ARBOL_TIPOS = {
    "pino":    (build_pino,    (9.0, 15.0), 24),
    "olivo":   (build_olivo,   (4.0, 6.5),  16),
    "encina":  (build_encina,  (7.0, 11.0), 14),
    "cipres":  (build_cipres,  (7.0, 12.0), 13),
    "arbusto": (build_arbusto, (1.0, 2.2),  13),
    "palmera": (build_palmera, (5.0, 10.0),  8),
    "adelfa":  (build_adelfa,  None,         7),
    "platano": (build_platano, (11.0, 17.0), 5),
}


def build_arbol(parent_collection, tipo=None, alto=None, seed=0):
    """Construye un árbol/arbusto de `tipo` (o aleatorio ponderado si None) con
    `alto` (o un valor típico del tipo si None; para "arbusto" es el `tam`).
    La variante de silueta la elige un sub-seed derivado de `seed`. Devuelve
    el objeto (VEG_<tipo>) marcado con ob["VEG_tipo"]."""
    rng = random.Random(7919 * seed + 131)
    if tipo is None:
        tipos = list(_ARBOL_TIPOS)
        tipo = rng.choices(tipos, weights=[_ARBOL_TIPOS[t][2] for t in tipos], k=1)[0]
    if tipo not in _ARBOL_TIPOS:
        raise ValueError("tipo de árbol desconocido: %r (válidos: %s)"
                         % (tipo, ", ".join(_ARBOL_TIPOS)))
    fn, rango, _ = _ARBOL_TIPOS[tipo]
    sub = rng.randint(0, 99999)
    if tipo == "adelfa":
        ob = fn(parent_collection, seed=sub)
    elif tipo == "arbusto":
        ob = fn(parent_collection, tam=alto if alto is not None else rng.uniform(*rango), seed=sub)
    else:
        if alto is None:
            alto = rng.uniform(*rango)
            # las variantes "pequeñas" por naturaleza se escalan al elegir
            # altura automática (un pino joven o un palmito no miden 12 m)
            if tipo == "pino" and _PINO_VARIANTES[sub % len(_PINO_VARIANTES)] == "joven":
                alto *= 0.55
            elif tipo == "palmera" and _PALMERA_VARIANTES[sub % len(_PALMERA_VARIANTES)] == "abanico":
                alto *= 0.60
        ob = fn(parent_collection, alto=alto, seed=sub)
    ob["VEG_tipo"] = tipo
    return ob


# ---------------------------------------------------------------------------
# MUESTRARIO
# ---------------------------------------------------------------------------
def build(parent_collection, seed=0, **params):
    """Muestrario en fila: piezas delante, acantilado de fondo. Devuelve Empty raíz."""
    root = bpy.data.objects.new("%s_muestrario" % PREFIX, None)
    root.empty_display_size = 2.0
    parent_collection.objects.link(root)

    def place(ob, x, y=0.0, rz=0.0):
        ob.parent = root
        ob.location = (x, y, 0.0)
        ob.rotation_euler = (0.0, 0.0, rz)
        return ob

    # pinos separados >= 13 m: el costero alcanza ~9 m de vuelo hacia sotavento
    place(build_acantilado(parent_collection, largo=120.0, alto=20.0, seed=seed + 5), 0.0, -17.0)
    place(build_platano(parent_collection, alto=14.0, seed=seed), -53.0)
    place(build_palmera(parent_collection, alto=8.0, seed=seed), -44.0)
    place(build_palmera(parent_collection, alto=9.0, seed=seed + 1), -38.0)
    place(build_palmera(parent_collection, alto=4.5, seed=seed + 2), -33.0)
    place(build_cipres(parent_collection, alto=10.0, seed=seed), -28.0)
    place(build_cipres(parent_collection, alto=9.0, seed=seed + 1), -25.5)
    place(build_pino(parent_collection, alto=12.0, seed=seed), -18.0)
    place(build_pino(parent_collection, alto=11.0, seed=seed + 1), -5.0)
    place(build_pino(parent_collection, alto=10.0, seed=seed + 2), 8.0)
    place(build_pino(parent_collection, alto=6.0, seed=seed + 3), 18.0)
    place(build_encina(parent_collection, alto=9.0, seed=seed), 27.0)
    place(build_olivo(parent_collection, alto=5.0, seed=seed), 34.0)
    place(build_adelfa(parent_collection, seed=seed), 38.5)
    place(build_adelfa(parent_collection, seed=seed + 1), 41.5)
    place(build_adelfa(parent_collection, seed=seed + 2), 45.0)
    place(build_arbusto(parent_collection, tam=1.5, seed=seed), 48.5)
    place(build_arbusto(parent_collection, tam=1.5, seed=seed + 1), 50.5)
    place(build_arbusto(parent_collection, tam=1.5, seed=seed + 2), 52.5)
    place(build_jardinera(parent_collection, largo=6.0, seed=seed), 33.0, 6.0)
    place(build_roca(parent_collection, tam=3.0, seed=seed + 3), 41.0, 6.0)
    place(build_roca(parent_collection, tam=1.6, seed=seed + 4), 44.0, 6.0)
    return root
