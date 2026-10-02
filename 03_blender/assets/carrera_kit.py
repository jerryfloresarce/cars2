"""carrera_kit.py — Kit procedural de infraestructura de carrera World Grand Prix
(Porto Corsa, Cars 2) para Blender 5.1.

Todas las piezas crean sus objetos, los linkan a `parent_collection` y devuelven
el objeto raiz. Unidades en metros, base en z=0, fachada principal mirando a +Y.
Materiales Principled BSDF de color plano, reutilizados por nombre.

Piezas del kit:
- build_tribuna(parent, largo=40, filas=12, seed=0): grada techada con
  coches-espectador abstractos (bloques de colores saturados como publico).
- build_portico_meta(parent, ancho=20): portico sobre la pista con panel
  "MONDIALE GRAND PRIX" (texto 3D), banda de cuadros y semaforo de salida.
- build_pantalla(parent): pantalla gigante ~12x7 m sobre torre.
- build_boxes(parent, n=12): edificio de pit lane con n boxes numerados,
  portones, terraza y muro de pits.
- build_muro_valla(parent, largo=10): muro bajo blanco + valla de captura
  (postes y barrotes finos), pensado para repetir a lo largo de la pista.
- build_valla_publicitaria(parent, largo=8, texto='ALLINOL'): panel
  publicitario verde/blanco con texto 3D.
- build_paca(parent): pila de balas de paja con flejes.
- build(parent_collection, seed=0): vineta completa (portico + tribuna +
  boxes + pantalla + muros + vallas + pacas sobre asfalto con linea de meta).
"""

import math
import random

import bpy

PRE = 'CARRERA'

# ------------------------------------------------------------------ materiales

# clave: (color, roughness, metallic, color_emision | None, fuerza_emision)
_PALETA = {
    'blanco':        ((0.92, 0.90, 0.86), 0.55, 0.0, None, 0.0),
    'crema':         ((0.95, 0.86, 0.62), 0.60, 0.0, None, 0.0),
    'ocre':          ((0.86, 0.54, 0.20), 0.65, 0.0, None, 0.0),
    'terracota':     ((0.62, 0.25, 0.12), 0.70, 0.0, None, 0.0),
    'verde_wgp':     ((0.04, 0.58, 0.18), 0.45, 0.0, None, 0.0),
    'verde_oscuro':  ((0.05, 0.22, 0.11), 0.50, 0.0, None, 0.0),
    'gris_acero':    ((0.30, 0.33, 0.36), 0.40, 0.6, None, 0.0),
    'gris_oscuro':   ((0.09, 0.09, 0.10), 0.60, 0.0, None, 0.0),
    'negro':         ((0.02, 0.02, 0.02), 0.60, 0.0, None, 0.0),
    'asfalto':       ((0.13, 0.13, 0.14), 0.90, 0.0, None, 0.0),
    'piedra_clara':  ((0.58, 0.52, 0.40), 0.85, 0.0, None, 0.0),
    'azul_oscuro':   ((0.02, 0.05, 0.15), 0.40, 0.0, None, 0.0),
    'paja':          ((0.85, 0.62, 0.20), 0.80, 0.0, None, 0.0),
    'paja_oscura':   ((0.48, 0.32, 0.10), 0.80, 0.0, None, 0.0),
    'rojo_luz':      ((0.85, 0.04, 0.02), 0.40, 0.0, (1.0, 0.04, 0.02), 6.0),
    'pantalla_luz':  ((0.04, 0.12, 0.40), 0.30, 0.0, (0.28, 0.55, 1.00), 2.6),
    'cabina':        ((0.28, 0.44, 0.55), 0.20, 0.0, None, 0.0),
    'pub_rojo':      ((0.80, 0.08, 0.06), 0.50, 0.0, None, 0.0),
    'pub_azul':      ((0.08, 0.22, 0.78), 0.50, 0.0, None, 0.0),
    'pub_amarillo':  ((0.95, 0.72, 0.08), 0.50, 0.0, None, 0.0),
    'pub_verde':     ((0.10, 0.58, 0.16), 0.50, 0.0, None, 0.0),
    'pub_naranja':   ((0.90, 0.36, 0.04), 0.50, 0.0, None, 0.0),
    'pub_morado':    ((0.42, 0.09, 0.58), 0.50, 0.0, None, 0.0),
    'pub_cian':      ((0.08, 0.62, 0.68), 0.50, 0.0, None, 0.0),
    'pub_blanco':    ((0.90, 0.90, 0.88), 0.50, 0.0, None, 0.0),
}

_PUBLICO = ('pub_rojo', 'pub_azul', 'pub_amarillo', 'pub_verde',
            'pub_naranja', 'pub_morado', 'pub_cian', 'pub_blanco')


def _mat(clave):
    """Crea (o reutiliza) el material MAT_CARRERA_<clave> de la paleta."""
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
    """Acumulador de cajas/quads que produce una unica malla multi-material."""

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


def _texto_3d(nombre, texto, tam, clave_mat, col, extrude=0.05):
    """Texto 3D via curva FONT convertida a malla, centrado en su origen y
    puesto de pie mirando a +Y (legible desde +Y). Solo falta ubicarlo."""
    cu = bpy.data.curves.new(nombre + '_cu', type='FONT')
    cu.body = texto
    cu.size = tam
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.resolution_u = 3
    tmp = bpy.data.objects.new(nombre + '_tmp', cu)
    col.objects.link(tmp)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(deps))
    me.name = nombre
    me.materials.clear()
    me.materials.append(_mat(clave_mat))
    ob = bpy.data.objects.new(nombre, me)
    # de pie y legible desde +Y (girar el cartel, no espejarlo)
    ob.rotation_euler = (math.radians(90), 0.0, math.pi)
    col.objects.link(ob)
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    return ob


# ------------------------------------------------------------------ las piezas

def build_tribuna(parent_collection, largo=40, filas=12, seed=0, **params):
    """Grada techada con publico de coches-espectador abstractos."""
    col = parent_collection
    raiz = _raiz('%s_tribuna' % PRE, col)
    rng = random.Random(seed)

    prof = 1.7       # fondo de cada fila
    alto = 0.75      # subida por fila
    base = 0.6       # zocalo frontal
    fondo = filas * prof
    y_frente = fondo / 2.0
    h_top = base + (filas - 1) * alto

    mb = _MB()  # 0 crema, 1 verde_wgp, 2 blanco
    # gradas macizas escalonadas
    for i in range(filas):
        h = base + i * alto
        yc = y_frente - (i + 0.5) * prof
        mb.caja((0, yc, h / 2.0), (largo, prof, h), mat=0)
    # faldon frontal verde
    mb.caja((0, y_frente + 0.09, (base + 0.2) / 2.0), (largo, 0.18, base + 0.2), mat=1)
    # muro trasero hasta el techo
    h_muro = h_top + 2.6
    mb.caja((0, -fondo / 2.0 + 0.2, h_muro / 2.0), (largo, 0.4, h_muro), mat=2)
    # laterales bajos
    for sx in (-1, 1):
        mb.caja((sx * (largo / 2.0 - 0.15), -fondo * 0.15, (h_top * 0.7) / 2.0),
                (0.3, fondo * 0.7, h_top * 0.7), mat=2)
    estructura = mb.obj('%s_tribuna_estructura' % PRE,
                        ('crema', 'verde_wgp', 'blanco'), col)
    estructura.parent = raiz

    # techo inclinado (borde delantero alto)
    mt = _MB()
    mt.caja((0, 0, 0), (largo + 1.6, fondo * 0.85, 0.22), mat=0)
    mt.caja((0, fondo * 0.425 - 0.1, -0.25), (largo + 1.6, 0.2, 0.35), mat=0)
    techo = mt.obj('%s_tribuna_techo' % PRE, ('verde_wgp',), col)
    techo.location = (0, -fondo * 0.02, h_top + 2.9)
    techo.rotation_euler = (math.radians(7), 0, 0)
    techo.parent = raiz

    # publico: coches abstractos (bloque carroceria + bloque cabina)
    mp = _MB()  # mat 0 = cabina, 1..8 = colores publico
    plazas = max(1, int((largo - 1.6) // 2.2))
    x0 = -(plazas - 1) * 2.2 / 2.0
    for i in range(filas):
        z_piso = base + i * alto
        yc = y_frente - (i + 0.5) * prof
        for p in range(plazas):
            if rng.random() > 0.82:
                continue
            x = x0 + p * 2.2 + rng.uniform(-0.15, 0.15)
            rz = rng.uniform(-0.09, 0.09)
            mi = 1 + rng.randrange(len(_PUBLICO))
            mp.caja((x, yc + 0.04, z_piso + 0.28), (0.95, 1.5, 0.56), mat=mi, rz=rz)
            mp.caja((x, yc - 0.12, z_piso + 0.73), (0.70, 0.75, 0.34), mat=0, rz=rz)
    publico = mp.obj('%s_tribuna_publico' % PRE, ('cabina',) + _PUBLICO, col)
    publico.parent = raiz
    return raiz


def build_portico_meta(parent_collection, ancho=20, **params):
    """Portico de meta con panel MONDIALE GRAND PRIX y semaforo de salida."""
    col = parent_collection
    raiz = _raiz('%s_portico' % PRE, col)
    a2 = ancho / 2.0

    mb = _MB()  # 0 crema, 1 verde_oscuro, 2 blanco, 3 negro, 4 terracota,
                # 5 verde_wgp, 6 gris_acero, 7 gris_oscuro, 8 rojo_luz
    for sx in (-1, 1):
        mb.caja((sx * a2, 0, 0.30), (1.6, 1.6, 0.6), mat=1)     # zocalo
        mb.caja((sx * a2, 0, 3.70), (1.1, 1.1, 6.2), mat=0)     # pilar
        mb.caja((sx * a2, 0, 6.95), (1.4, 1.4, 0.3), mat=1)     # capitel
        # banderola vertical verde con ribete blanco en cada pilar
        mb.caja((sx * a2, 0.58, 4.10), (0.95, 0.05, 4.3), mat=2)
        mb.caja((sx * a2, 0.62, 4.10), (0.80, 0.05, 4.1), mat=5)
    # dintel
    mb.caja((0, 0, 8.10), (ancho + 2.2, 1.4, 2.6), mat=0)
    # cornisa terracota
    mb.caja((0, 0, 9.55), (ancho + 2.6, 1.7, 0.3), mat=4)
    # banda de cuadros (blanco + fichas negras)
    mb.caja((0, 0.68, 7.20), (ancho + 2.2, 0.08, 0.8), mat=2)
    n = int((ancho + 2.2) / 0.4)
    x0 = -(n * 0.4) / 2.0 + 0.2
    for c in range(n):
        for r in range(2):
            if (c + r) % 2 == 0:
                mb.caja((x0 + c * 0.4, 0.70, 7.00 + r * 0.4),
                        (0.4, 0.08, 0.4), mat=3)
    # panel del patrocinio (marco blanco + fondo verde)
    mb.caja((0, 0.73, 8.55), (ancho * 0.8 + 0.3, 0.10, 1.74), mat=2)
    mb.caja((0, 0.78, 8.55), (ancho * 0.8, 0.14, 1.5), mat=5)
    # semaforo de salida colgado del dintel
    mb.caja((0, 0, 6.55), (0.18, 0.18, 0.5), mat=6)
    mb.caja((0, 0, 5.95), (2.6, 0.4, 0.9), mat=7)
    for k in range(5):
        mb.caja((-1.0 + k * 0.5, 0.20, 5.95), (0.30, 0.12, 0.30), mat=8)
    estructura = mb.obj('%s_portico_estructura' % PRE,
                        ('crema', 'verde_oscuro', 'blanco', 'negro', 'terracota',
                         'verde_wgp', 'gris_acero', 'gris_oscuro', 'rojo_luz'), col)
    estructura.parent = raiz

    texto = _texto_3d('%s_portico_texto' % PRE, 'MONDIALE GRAND PRIX',
                      1.0, 'blanco', col, extrude=0.06)
    texto.location = (0, 0.90, 8.52)
    texto.parent = raiz
    return raiz


def build_pantalla(parent_collection, **params):
    """Pantalla gigante ~12x7 m sobre torre de celosia."""
    col = parent_collection
    raiz = _raiz('%s_pantalla' % PRE, col)

    mb = _MB()  # 0 gris_acero, 1 gris_oscuro, 2 pantalla_luz
    for sx in (-1, 1):
        mb.caja((sx * 2.8, 0, 4.25), (0.7, 0.7, 8.5), mat=0)
    mb.caja((0, 0, 2.80), (6.3, 0.45, 0.45), mat=0)
    mb.caja((0, 0, 5.60), (6.3, 0.45, 0.45), mat=0)
    mb.caja((0, 0, 12.15), (12.6, 0.7, 7.6), mat=1)             # marco
    mb.caja((0, 0.38, 12.15), (11.9, 0.08, 6.9), mat=2)         # pantalla
    estructura = mb.obj('%s_pantalla_estructura' % PRE,
                        ('gris_acero', 'gris_oscuro', 'pantalla_luz'), col)
    estructura.parent = raiz

    texto = _texto_3d('%s_pantalla_texto' % PRE, 'MONDIALE GP',
                      1.5, 'azul_oscuro', col, extrude=0.04)
    texto.location = (0, 0.48, 12.9)
    texto.parent = raiz

    vivo = _texto_3d('%s_pantalla_texto2' % PRE, 'PORTO CORSA  -  GIRO 42/60',
                     0.8, 'azul_oscuro', col, extrude=0.04)
    vivo.location = (0, 0.48, 10.8)
    vivo.parent = raiz
    return raiz


def build_boxes(parent_collection, n=12, **params):
    """Edificio de pit lane con n boxes numerados, terraza y muro de pits."""
    col = parent_collection
    raiz = _raiz('%s_boxes' % PRE, col)

    w = 6.0
    L = n * w
    fondo = 9.0
    h = 5.2

    mb = _MB()  # 0 crema, 1 terracota, 2 blanco, 3 gris_oscuro, 4 ocre, 5 verde_wgp
    mb.caja((0, 0, h / 2.0), (L, fondo, h), mat=0)                       # cuerpo
    mb.caja((0, 0, h + 0.17), (L + 0.8, fondo + 0.8, 0.34), mat=1)       # cornisa
    mb.caja((0, fondo / 2.0 - 0.15, h + 0.34 + 0.35), (L, 0.14, 0.7), mat=2)  # balaustrada
    for i in range(n + 1):
        mb.caja((-L / 2.0 + i * w, fondo / 2.0 - 0.05, h / 2.0),
                (0.5, 0.4, h), mat=4)                                    # pilastras
    for i in range(n):
        cx = -L / 2.0 + (i + 0.5) * w
        mb.caja((cx, fondo / 2.0 - 0.05, 1.95), (4.6, 0.2, 3.9), mat=3)  # porton
        for k in range(4):
            mb.caja((cx, fondo / 2.0 + 0.06, 0.55 + k * 0.95),
                    (4.6, 0.03, 0.06), mat=2)                            # lamas
        mb.caja((cx, fondo / 2.0 - 0.02, 4.55), (1.2, 0.16, 1.0), mat=2) # placa
    # muro de pits con franja verde
    mb.caja((0, 11.5, 0.55), (L * 0.92, 0.5, 1.1), mat=2)
    mb.caja((0, 11.5, 1.22), (L * 0.92, 0.54, 0.24), mat=5)
    edificio = mb.obj('%s_boxes_edificio' % PRE,
                      ('crema', 'terracota', 'blanco', 'gris_oscuro',
                       'ocre', 'verde_wgp'), col)
    edificio.parent = raiz

    for i in range(n):
        cx = -L / 2.0 + (i + 0.5) * w
        num = _texto_3d('%s_boxes_num%02d' % (PRE, i + 1), str(i + 1),
                        0.72, 'verde_oscuro', col, extrude=0.04)
        num.location = (cx, fondo / 2.0 + 0.08, 4.53)
        num.parent = raiz
    return raiz


def build_muro_valla(parent_collection, largo=10, **params):
    """Muro bajo blanco + valla de captura de barrotes finos (repetible)."""
    col = parent_collection
    mb = _MB()  # 0 blanco, 1 gris_acero
    mb.caja((0, 0, 0.5), (largo, 0.45, 1.0), mat=0)
    postes = max(2, int(largo // 2) + 1)
    for k in range(postes):
        x = -largo / 2.0 + 0.15 + k * (largo - 0.3) / (postes - 1)
        mb.caja((x, 0, 2.15), (0.09, 0.09, 2.3), mat=1)
    for z in (1.45, 2.0, 2.55, 3.1):
        mb.caja((0, 0.10, z), (largo, 0.035, 0.035), mat=1)
    ob = mb.obj('%s_muro_valla' % PRE, ('blanco', 'gris_acero'), col)
    return ob


def build_valla_publicitaria(parent_collection, largo=8, texto='ALLINOL', **params):
    """Panel publicitario verde/blanco con texto 3D (fachada a +Y)."""
    col = parent_collection
    mb = _MB()  # 0 blanco, 1 verde_wgp, 2 gris_acero
    for sx in (-1, 1):
        mb.caja((sx * (largo / 2.0 - 0.6), 0, 0.14), (0.4, 0.7, 0.28), mat=2)
    mb.caja((0, 0, 1.05), (largo, 0.16, 1.5), mat=0)
    mb.caja((0, 0.06, 1.05), (largo - 0.3, 0.10, 1.24), mat=1)
    panel = mb.obj('%s_valla_pub' % PRE, ('blanco', 'verde_wgp', 'gris_acero'), col)

    tam = min(0.85, (largo - 0.9) / max(1, len(texto)) / 0.62)
    tx = _texto_3d('%s_valla_pub_texto' % PRE, texto, tam, 'blanco', col,
                   extrude=0.04)
    tx.location = (0, 0.14, 1.03)
    tx.parent = panel
    return panel


def build_paca(parent_collection, **params):
    """Pila de balas de paja (2 abajo + 1 arriba) con flejes."""
    col = parent_collection
    mb = _MB()  # 0 paja, 1 paja_oscura
    balas = (((-0.72, 0.00, 0.30), 0.05),
             ((0.72, 0.05, 0.30), -0.07),
             ((0.02, 0.02, 0.90), 0.16))
    for (cx, cy, cz), rz in balas:
        mb.caja((cx, cy, cz), (1.4, 0.75, 0.6), mat=0, rz=rz)
        c, s = math.cos(rz), math.sin(rz)
        for off in (-0.38, 0.38):
            mb.caja((cx + off * c, cy + off * s, cz),
                    (0.06, 0.78, 0.63), mat=1, rz=rz)
    ob = mb.obj('%s_paca' % PRE, ('paja', 'paja_oscura'), col)
    return ob


# ------------------------------------------------------------------- la vineta

def build(parent_collection, seed=0, **params):
    """Vineta World Grand Prix: portico de meta, tribuna, boxes, pantalla,
    muros con valla, vallas publicitarias y pacas, sobre asfalto con linea
    de meta. La pista corre a lo largo de +Y, de ancho 16 m (x en [-8, 8])."""
    col = parent_collection
    raiz = _raiz('%s_kit' % PRE, col)

    # suelo: asfalto de pista + aceras de piedra clara
    mb = _MB()  # 0 asfalto, 1 piedra_clara, 2 blanco, 3 negro
    mb.caja((0, 0, -0.05), (46, 120, 0.10), mat=0)
    mb.caja((-22.0, 0, -0.02), (28, 120, 0.12), mat=1)
    mb.caja((22.5, 0, -0.02), (29, 120, 0.12), mat=1)
    # lineas blancas de borde de pista
    for sx in (-1, 1):
        mb.caja((sx * 7.8, 0, 0.02), (0.18, 120, 0.05), mat=2)
    # linea de meta a cuadros
    mb.caja((0, 2.5, 0.045), (16, 1.7, 0.05), mat=2)
    for c in range(20):
        for r in range(2):
            if (c + r) % 2 == 0:
                mb.caja((-7.6 + c * 0.8, 2.1 + r * 0.8, 0.075),
                        (0.8, 0.8, 0.055), mat=3)
    suelo = mb.obj('%s_suelo' % PRE, ('asfalto', 'piedra_clara',
                                      'blanco', 'negro'), col)
    suelo.parent = raiz

    portico = build_portico_meta(col, ancho=20)
    portico.parent = raiz

    tribuna = build_tribuna(col, largo=40, filas=12, seed=seed)
    tribuna.location = (-29, -4, 0)
    tribuna.rotation_euler = (0, 0, -math.pi / 2)
    tribuna.parent = raiz

    boxes = build_boxes(col, n=12)
    boxes.location = (21, -8, 0)
    boxes.rotation_euler = (0, 0, math.pi / 2)
    boxes.parent = raiz

    pantalla = build_pantalla(col)
    pantalla.location = (-31, -34, 0)
    pantalla.rotation_euler = (0, 0, math.radians(-25))
    pantalla.parent = raiz

    for y in (-32, -21.5, -11, 11, 21.5, 32):
        muro = build_muro_valla(col, largo=10)
        muro.location = (-9, y, 0)
        muro.rotation_euler = (0, 0, -math.pi / 2)
        muro.parent = raiz

    valla1 = build_valla_publicitaria(col, largo=8, texto='ALLINOL')
    valla1.location = (-13.2, -14, 0)
    valla1.rotation_euler = (0, 0, -math.pi / 2)
    valla1.parent = raiz

    valla2 = build_valla_publicitaria(col, largo=8, texto='MONDIALE GRAND PRIX')
    valla2.location = (-13.2, 4, 0)
    valla2.rotation_euler = (0, 0, -math.pi / 2)
    valla2.parent = raiz

    valla3 = build_valla_publicitaria(col, largo=8, texto='ALLINOL')
    valla3.location = (12.8, 30, 0)
    valla3.rotation_euler = (0, 0, math.pi / 2)
    valla3.parent = raiz

    paca1 = build_paca(col)
    paca1.location = (-7.2, 36, 0)
    paca1.rotation_euler = (0, 0, 0.35)
    paca1.parent = raiz

    paca2 = build_paca(col)
    paca2.location = (11.8, 22, 0)
    paca2.rotation_euler = (0, 0, -0.7)
    paca2.parent = raiz

    return raiz
