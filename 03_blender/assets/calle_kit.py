"""calle_kit.py — Kit procedural de mobiliario urbano de la Riviera de Porto
Corsa (Cars 2) para Blender 5.1.

Todas las piezas crean sus objetos, los linkan a `parent_collection` y
devuelven el objeto raiz. Unidades en metros, origen en el centro de la base
(z=0 en el suelo salvo la guirnalda, ver abajo), fachada principal mirando a
+Y. Materiales Principled BSDF de color plano reutilizados por nombre
(prefijo MAT_CALLE_). <= 1.5k tris por pieza.

Piezas del kit:
- build_farola(parent, alto=5.2, seed=0): farola clasica de fundicion verde
  oscuro con pedestal, fuste estriado, brazo curvado hacia +Y y globo calido
  levemente emisivo colgando del brazo.
- build_guirnalda(parent, luz=16.0, seed=0): guirnalda de banderines
  triangulares colgada en catenaria entre dos puntos separados `luz` metros.
  Origen en el punto MEDIO entre los dos extremos: extremos en x=-luz/2 y
  x=+luz/2 con z=0, la cuerda cuelga hacia -z (~1.2 m de comba en el centro).
  Banderines alternando verde/blanco/rojo con alguno en verde WGP.
- build_maceta(parent, seed=0): maceta de terracota con flores rojas y rosas
  rebosantes (~0.9 m de alto total).
- build_toldo_mercado(parent, seed=0): puestecito de mercado con mostrador de
  madera, cajas de fruta y toldo a rayas (~3x2 m) para plazas.
- build(parent_collection, seed=0): muestrario (dos farolas con guirnalda,
  puesto de mercado y macetas sobre losa de piedra clara).
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

PRE = 'CALLE'

# ------------------------------------------------------------------ materiales
# FASE VISUAL, paleta v2 (usuario 04/10): la terracota de las macetas y el acento de flores
# (buganvilla #C2407A, "solo en pequenas dosis": las macetas de calle/balcon) salen de
# 03_blender/paleta.json; el resto de colores del kit no cambia.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import paleta as _paleta  # noqa: E402

# clave: (color, roughness, metallic, color_emision | None, fuerza_emision)
_PALETA = {
    'verde_farola': ((0.045, 0.135, 0.080), 0.35, 0.30, None, 0.0),
    'oro':          ((0.60, 0.45, 0.16), 0.35, 0.85, None, 0.0),
    'globo':        ((0.95, 0.72, 0.40), 0.30, 0.0, (1.0, 0.60, 0.24), 1.0),
    'cuerda':       ((0.42, 0.33, 0.22), 0.85, 0.0, None, 0.0),
    'band_verde':   ((0.05, 0.45, 0.14), 0.55, 0.0, None, 0.0),
    'band_blanco':  ((0.93, 0.91, 0.86), 0.55, 0.0, None, 0.0),
    'band_rojo':    ((0.78, 0.07, 0.05), 0.55, 0.0, None, 0.0),
    'verde_wgp':    ((0.04, 0.58, 0.18), 0.45, 0.0, None, 0.0),
    'terracota':    (_paleta.rgb('terracota'), 0.75, 0.0, None, 0.0),       # paleta v2 #BF6440
    'tierra':       ((0.23, 0.15, 0.09), 0.95, 0.0, None, 0.0),
    'hojas':        ((0.10, 0.34, 0.09), 0.70, 0.0, None, 0.0),
    'flor_roja':    ((0.85, 0.05, 0.04), 0.50, 0.0, None, 0.0),
    'flor_rosa':    (_paleta.rgb('buganvilla'), 0.50, 0.0, None, 0.0),      # paleta v2: acento buganvilla
    'madera':       ((0.44, 0.27, 0.13), 0.70, 0.0, None, 0.0),
    'madera_clara': ((0.66, 0.48, 0.26), 0.70, 0.0, None, 0.0),
    'toldo_rojo':   ((0.80, 0.10, 0.07), 0.60, 0.0, None, 0.0),
    'toldo_crema':  ((0.95, 0.90, 0.80), 0.60, 0.0, None, 0.0),
    'blanco':       ((0.92, 0.90, 0.86), 0.55, 0.0, None, 0.0),
    'limon':        ((0.95, 0.80, 0.10), 0.45, 0.0, None, 0.0),
    'tomate':       ((0.85, 0.12, 0.05), 0.40, 0.0, None, 0.0),
    'piedra_clara': ((0.58, 0.52, 0.40), 0.85, 0.0, None, 0.0),
}


def _mat(clave):
    """Crea (o reutiliza) el material MAT_CALLE_<clave> de la paleta."""
    nombre = 'MAT_%s_%s' % (PRE, clave)
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough, metal, emision, fuerza = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    try:
        if not m.use_nodes:
            m.use_nodes = True
    except AttributeError:
        pass
    bsdf = None
    nt = m.node_tree
    if nt is not None:
        for nd in nt.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                bsdf = nd
                break
        if bsdf is None:
            bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
            salida = None
            for nd in nt.nodes:
                if nd.type == 'OUTPUT_MATERIAL':
                    salida = nd
                    break
            if salida is None:
                salida = nt.nodes.new('ShaderNodeOutputMaterial')
            nt.links.new(bsdf.outputs['BSDF'], salida.inputs['Surface'])
    if bsdf is not None:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = rough
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metal
        if emision is not None:
            ent = bsdf.inputs.get('Emission Color') or bsdf.inputs.get('Emission')
            fue = bsdf.inputs.get('Emission Strength')
            if ent is not None:
                ent.default_value = (*emision, 1.0)
            if fue is not None:
                fue.default_value = fuerza
    m.diffuse_color = (*color, 1.0)
    return m


# ------------------------------------------------------------ utilidades malla

class _MB:
    """Acumulador de primitivas que produce una unica malla multi-material."""

    def __init__(self):
        self.v = []
        self.f = []
        self.fm = []

    def caja(self, centro, dim, mat=0, rz=0.0):
        cx, cy, cz = centro
        hx, hy, hz = dim[0] / 2.0, dim[1] / 2.0, dim[2] / 2.0
        base = len(self.v)
        c, s = math.cos(rz), math.sin(rz)
        for dx, dy, dz in ((-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz),
                           (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz),
                           (hx, hy, hz), (-hx, hy, hz)):
            self.v.append((cx + dx * c - dy * s, cy + dx * s + dy * c, cz + dz))
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f.append((base + q[0], base + q[1], base + q[2], base + q[3]))
            self.fm.append(mat)

    def cilindro(self, base_c, r_abajo, r_arriba, alto, mat=0, n=8, tapas=True):
        """Cono truncado vertical; base_c es el centro de la base inferior."""
        cx, cy, cz = base_c
        b = len(self.v)
        for j in range(n):
            th = 2.0 * math.pi * j / n
            self.v.append((cx + r_abajo * math.cos(th),
                           cy + r_abajo * math.sin(th), cz))
        for j in range(n):
            th = 2.0 * math.pi * j / n
            self.v.append((cx + r_arriba * math.cos(th),
                           cy + r_arriba * math.sin(th), cz + alto))
        for j in range(n):
            j2 = (j + 1) % n
            self.f.append((b + j, b + j2, b + n + j2, b + n + j))
            self.fm.append(mat)
        if tapas:
            self.f.append(tuple(b + j for j in reversed(range(n))))
            self.fm.append(mat)
            self.f.append(tuple(b + n + j for j in range(n)))
            self.fm.append(mat)

    def esfera(self, centro, r, mat=0, nseg=8, nan=5, escala_z=1.0):
        cx, cy, cz = centro
        b = len(self.v)
        self.v.append((cx, cy, cz + r * escala_z))
        for i in range(1, nan):
            phi = math.pi * i / nan
            zc = math.cos(phi) * r * escala_z
            rr = math.sin(phi) * r
            for j in range(nseg):
                th = 2.0 * math.pi * j / nseg
                self.v.append((cx + rr * math.cos(th),
                               cy + rr * math.sin(th), cz + zc))
        self.v.append((cx, cy, cz - r * escala_z))
        for j in range(nseg):
            j2 = (j + 1) % nseg
            self.f.append((b, b + 1 + j, b + 1 + j2))
            self.fm.append(mat)
        for i in range(nan - 2):
            r0 = b + 1 + i * nseg
            r1 = r0 + nseg
            for j in range(nseg):
                j2 = (j + 1) % nseg
                self.f.append((r0 + j2, r0 + j, r1 + j, r1 + j2))
                self.fm.append(mat)
        polo = b + 1 + (nan - 1) * nseg
        r0 = b + 1 + (nan - 2) * nseg
        for j in range(nseg):
            j2 = (j + 1) % nseg
            self.f.append((polo, r0 + j2, r0 + j))
            self.fm.append(mat)

    def tubo(self, puntos, radio, mat=0, n=6, tapas=True):
        """Tubo de seccion circular barrido a lo largo de una polilinea."""
        pts = [Vector(p) for p in puntos]
        m = len(pts)
        b = len(self.v)
        for i in range(m):
            if i == 0:
                t = (pts[1] - pts[0])
            elif i == m - 1:
                t = (pts[-1] - pts[-2])
            else:
                t = (pts[i + 1] - pts[i - 1])
            t.normalize()
            ref = Vector((0.0, 0.0, 1.0))
            if abs(t.dot(ref)) > 0.92:
                ref = Vector((0.0, 1.0, 0.0))
            b1 = ref.cross(t)
            b1.normalize()
            b2 = t.cross(b1)
            for j in range(n):
                th = 2.0 * math.pi * j / n
                p = pts[i] + b1 * (radio * math.cos(th)) + b2 * (radio * math.sin(th))
                self.v.append((p.x, p.y, p.z))
        for i in range(m - 1):
            r0 = b + i * n
            r1 = r0 + n
            for j in range(n):
                j2 = (j + 1) % n
                self.f.append((r0 + j, r0 + j2, r1 + j2, r1 + j))
                self.fm.append(mat)
        if tapas:
            self.f.append(tuple(b + j for j in reversed(range(n))))
            self.fm.append(mat)
            self.f.append(tuple(b + (m - 1) * n + j for j in range(n)))
            self.fm.append(mat)

    def tri(self, a, bb, c, mat=0):
        base = len(self.v)
        self.v.extend((a, bb, c))
        self.f.append((base, base + 1, base + 2))
        self.fm.append(mat)

    def obj(self, nombre, claves_mat, col):
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(self.v, [], self.f)
        for clave in claves_mat:
            me.materials.append(_mat(clave))
        for p, mi in zip(me.polygons, self.fm):
            p.material_index = mi
        me.validate()
        ob = bpy.data.objects.new(nombre, me)
        col.objects.link(ob)
        return ob


def _raiz(nombre, col):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_size = 0.5
    col.objects.link(e)
    return e


# ------------------------------------------------------------------ las piezas

def build_farola(parent_collection, alto=5.2, seed=0, **params):
    """Farola clasica de fundicion verde oscuro: pedestal, fuste conico con
    anillos dorados, brazo curvado hacia +Y y globo calido colgante."""
    col = parent_collection
    rng = random.Random(seed)

    mb = _MB()  # 0 verde_farola, 1 oro, 2 globo
    # pedestal
    mb.cilindro((0, 0, 0.0), 0.26, 0.24, 0.10, mat=0, n=8)
    mb.cilindro((0, 0, 0.10), 0.185, 0.17, 0.32, mat=0, n=8)
    mb.cilindro((0, 0, 0.42), 0.21, 0.13, 0.07, mat=0, n=8)
    # fuste conico
    z_top = alto - 1.15
    mb.cilindro((0, 0, 0.49), 0.078, 0.050, z_top - 0.49, mat=0, n=8, tapas=False)
    # anillos decorativos
    mb.cilindro((0, 0, 0.52), 0.105, 0.095, 0.09, mat=1, n=8)
    mb.cilindro((0, 0, z_top * 0.52), 0.082, 0.078, 0.07, mat=1, n=8)
    mb.cilindro((0, 0, z_top - 0.12), 0.088, 0.075, 0.12, mat=0, n=8)
    # brazo curvado hacia +Y (arranca vertical, termina horizontal)
    alcance = 0.85
    subida = 0.90 * rng.uniform(0.98, 1.02)
    arm = []
    for k in range(10):
        th = (math.pi / 2.0) * k / 9.0
        arm.append((0.0, alcance * (1.0 - math.cos(th)),
                    z_top + subida * math.sin(th)))
    mb.tubo(arm, 0.042, mat=0, n=6)
    # voluta decorativa bajo el brazo
    mb.esfera((0.0, 0.16, z_top + 0.55), 0.07, mat=1, nseg=6, nan=4)
    # cuelgue + tapa + globo
    z_arm = z_top + subida
    mb.cilindro((0, alcance, z_arm - 0.16), 0.028, 0.028, 0.16, mat=0, n=6)
    mb.cilindro((0, alcance, z_arm - 0.30), 0.155, 0.045, 0.15, mat=0, n=8)
    r_globo = 0.27
    mb.esfera((0.0, alcance, z_arm - 0.30 - r_globo * 0.82), r_globo,
              mat=2, nseg=10, nan=6)
    # remate sobre el codo del brazo
    mb.esfera((0.0, alcance * 0.5, z_top + subida + 0.05), 0.055,
              mat=1, nseg=6, nan=4)

    ob = mb.obj('%s_farola' % PRE, ('verde_farola', 'oro', 'globo'), col)
    return ob


def build_guirnalda(parent_collection, luz=16.0, seed=0, **params):
    """Guirnalda de banderines en catenaria entre x=-luz/2 y x=+luz/2 (z=0 en
    los extremos, comba ~1.2 m hacia -z). Verde/blanco/rojo + verde WGP."""
    col = parent_collection
    rng = random.Random(seed)
    comba = 1.2 * min(1.0, luz / 16.0 + 0.35)

    def z_de(x):
        u = 2.0 * x / luz
        return -comba * (1.0 - u * u)

    mb = _MB()  # 0 cuerda, 1 band_verde, 2 band_blanco, 3 band_rojo, 4 verde_wgp
    # cuerda
    nseg = max(16, int(luz * 1.8))
    cuerda = []
    for k in range(nseg + 1):
        x = -luz / 2.0 + luz * k / nseg
        cuerda.append((x, 0.0, z_de(x)))
    mb.tubo(cuerda, 0.018, mat=0, n=5)

    # banderines triangulares colgando de la cuerda
    w = 0.30
    largo_b = 0.45
    paso = 0.50
    n_band = max(3, int((luz - 0.9) / paso))
    x_ini = -(n_band - 1) * paso / 2.0 - w / 2.0
    ciclo = (1, 2, 3)  # verde, blanco, rojo
    for i in range(n_band):
        x0 = x_ini + i * paso
        x1 = x0 + w
        za = z_de(x0) - 0.02
        zb = z_de(x1) - 0.02
        xm = (x0 + x1) / 2.0
        zm = (za + zb) / 2.0
        sway = rng.uniform(-0.22, 0.22)
        punta = (xm, largo_b * math.sin(sway), zm - largo_b * math.cos(sway))
        mat = 4 if rng.random() < 0.13 else ciclo[i % 3]
        mb.tri((x0, 0.0, za), (x1, 0.0, zb), punta, mat=mat)

    ob = mb.obj('%s_guirnalda' % PRE,
                ('cuerda', 'band_verde', 'band_blanco', 'band_rojo',
                 'verde_wgp'), col)
    return ob


def build_maceta(parent_collection, seed=0, **params):
    """Maceta de terracota con flores rojas y rosas rebosantes (~0.9 m)."""
    col = parent_collection
    rng = random.Random(seed)

    mb = _MB()  # 0 terracota, 1 tierra, 2 hojas, 3 flor_roja, 4 flor_rosa
    # tiesto troncoconico con labio
    mb.cilindro((0, 0, 0.0), 0.27, 0.25, 0.03, mat=0, n=10)
    mb.cilindro((0, 0, 0.03), 0.25, 0.355, 0.44, mat=0, n=10, tapas=False)
    mb.cilindro((0, 0, 0.47), 0.395, 0.40, 0.10, mat=0, n=10)
    # tierra
    mb.cilindro((0, 0, 0.52), 0.34, 0.33, 0.04, mat=1, n=10)
    # follaje: cupula baja + matas descolgando por el borde
    mb.esfera((0.0, 0.0, 0.60), 0.25, mat=2, nseg=8, nan=5, escala_z=0.62)
    for _ in range(4):
        th = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.30, 0.38)
        mb.esfera((rr * math.cos(th), rr * math.sin(th),
                   rng.uniform(0.46, 0.52)), rng.uniform(0.12, 0.16),
                  mat=2, nseg=7, nan=4, escala_z=0.8)
    # flores rebosantes: cupula tupida arriba + colgando sobre el labio
    for k in range(13):
        th = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.0, 0.26)
        r_f = rng.uniform(0.08, 0.115)
        z = 0.66 + 0.17 * math.cos(rr * 3.6) + rng.uniform(-0.02, 0.05)
        mb.esfera((rr * math.cos(th), rr * math.sin(th), z), r_f,
                  mat=3 if k % 3 else 4, nseg=6, nan=4)
    for k in range(7):
        th = 2 * math.pi * (k + rng.uniform(-0.2, 0.2)) / 7.0
        rr = rng.uniform(0.36, 0.44)
        mb.esfera((rr * math.cos(th), rr * math.sin(th),
                   rng.uniform(0.44, 0.55)), rng.uniform(0.065, 0.09),
                  mat=rng.choice((3, 4)), nseg=6, nan=4)

    ob = mb.obj('%s_maceta' % PRE,
                ('terracota', 'tierra', 'hojas', 'flor_roja', 'flor_rosa'), col)
    return ob


def build_toldo_mercado(parent_collection, seed=0, **params):
    """Puestecito de mercado (~3x2 m): mostrador de madera, cajas de fruta y
    toldo a rayas rojas/crema inclinado hacia +Y con volante festoneado."""
    col = parent_collection
    rng = random.Random(seed)
    raiz = _raiz('%s_toldo_mercado' % PRE, col)

    mb = _MB()  # 0 madera, 1 madera_clara, 2 blanco, 3 limon, 4 tomate, 5 hojas
    # mostrador
    mb.caja((0, 0.25, 0.44), (2.6, 1.15, 0.88), mat=0)
    mb.caja((0, 0.25, 0.905), (2.85, 1.4, 0.07), mat=1)
    mb.caja((0, 0.84, 0.45), (2.62, 0.06, 0.62), mat=2)   # faldon frontal
    # postes (traseros mas altos: toldo cae hacia delante)
    for sx in (-1, 1):
        mb.caja((sx * 1.38, -0.82, 1.22), (0.09, 0.09, 2.44), mat=0)
        mb.caja((sx * 1.38, 0.95, 1.06), (0.09, 0.09, 2.12), mat=0)
    # cajas de fruta sobre el mostrador
    for cx, cy, rot, fruta in ((-0.72, 0.18, 0.10, 3), (0.15, 0.30, -0.14, 4),
                               (0.95, 0.10, 0.24, 3)):
        mb.caja((cx, cy, 1.02), (0.56, 0.42, 0.16), mat=1, rz=rot)
        for _ in range(5):
            mb.esfera((cx + rng.uniform(-0.16, 0.16),
                       cy + rng.uniform(-0.10, 0.10),
                       1.11 + rng.uniform(0.0, 0.03)),
                      rng.uniform(0.052, 0.066), mat=fruta, nseg=6, nan=4)
        mb.esfera((cx + rng.uniform(-0.1, 0.1), cy + rng.uniform(-0.08, 0.08),
                   1.16), 0.055, mat=5, nseg=6, nan=4)
    cuerpo = mb.obj('%s_toldo_cuerpo' % PRE,
                    ('madera', 'madera_clara', 'blanco', 'limon', 'tomate',
                     'hojas'), col)
    cuerpo.parent = raiz

    # toldo a rayas (malla propia, inclinada luego en objeto)
    mt = _MB()  # 0 toldo_rojo, 1 toldo_crema
    n_rayas = 8
    ancho = 3.0
    fondo = 2.05
    wr = ancho / n_rayas
    for i in range(n_rayas):
        x = -ancho / 2.0 + (i + 0.5) * wr
        mt.caja((x, 0, 0), (wr, fondo, 0.045), mat=i % 2)
        # volante festoneado colgando del borde delantero
        mt.caja((x, fondo / 2.0 + 0.005, -0.15), (wr - 0.03, 0.035, 0.27),
                mat=i % 2)
    toldo = mt.obj('%s_toldo_lona' % PRE, ('toldo_rojo', 'toldo_crema'), col)
    toldo.location = (0, 0.08, 2.26)
    toldo.rotation_euler = (math.radians(-10.5), 0, 0)
    toldo.parent = raiz
    return raiz


# ---------------------------------------------------------------- el muestrario

def build(parent_collection, seed=0, **params):
    """Muestrario: dos farolas unidas por una guirnalda, puesto de mercado con
    toldo a rayas y macetas floridas, sobre una losa de piedra clara."""
    col = parent_collection
    raiz = _raiz('%s_kit' % PRE, col)

    mb = _MB()
    mb.caja((-0.5, 0, -0.04), (17, 10.5, 0.08), mat=0)
    suelo = mb.obj('%s_suelo' % PRE, ('piedra_clara',), col)
    suelo.parent = raiz

    x_a, x_b, y_far = -4.8, 2.4, 1.4
    far_a = build_farola(col, alto=5.2, seed=seed)
    far_a.location = (x_a, y_far, 0)
    far_a.parent = raiz

    far_b = build_farola(col, alto=5.2, seed=seed + 1)
    far_b.location = (x_b, y_far, 0)
    far_b.parent = raiz

    # guirnalda colgada entre los dos fustes, bajo el arranque del brazo
    guir = build_guirnalda(col, luz=x_b - x_a, seed=seed + 2)
    guir.location = ((x_a + x_b) / 2.0, y_far, 3.95)
    guir.parent = raiz

    toldo = build_toldo_mercado(col, seed=seed + 3)
    toldo.location = (4.7, -2.3, 0)
    toldo.rotation_euler = (0, 0, math.radians(-20))
    toldo.parent = raiz

    for k, (mx, my) in enumerate(((-2.3, -2.6), (0.6, -3.0), (-7.0, -2.0))):
        mac = build_maceta(col, seed=seed + 4 + k)
        mac.location = (mx, my, 0)
        mac.parent = raiz

    return raiz
