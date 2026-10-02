"""italiano_kit.py — Kit de AMBIENTE ITALIANO (Riviera / Cars 2) para los
caminos y colinas de Porto Corsa (Blender 5.1, bpy puro, sin bpy.ops).

Piezas que dan "sentido" a los caminos secundarios: una ermita en la cima,
capillitas de cruce, una fuente de plaza, bancales de olivar con muro de
piedra seca (apilables para hacer laderas con altibajos), hileras de
cipreses, la pergola con parra de una trattoria y mojones kilometricos.

Convenciones
- Unidades en metros. Origen de cada pieza en el centro de su base, z=0 en
  el suelo, fachada / cara vista mirando a +Y. Objetos con prefijo ITAL_,
  materiales MAT_ITAL_* (Principled BSDF de color plano; piedra, tierra,
  hierba y suelo llevan un ruido PROCEDURAL de nodos en coordenadas de
  objeto, nunca imagenes). Materiales reutilizados por nombre.
- Mallas por from_pydata. Texto 3D del hito/cartel: curva FONT convertida
  con bpy.data.meshes.new_from_object (sin bpy.ops).
- Orientacion (backface culling del kn5): todos los volumenes cerrados
  tienen las caras hacia FUERA (volumen firmado positivo) y los paneles de
  una sola cara (puerta, vidriera, sol, hierba, agua, textos) miran hacia
  el espectador (+Y o +Z). Los perfiles de _extruir y _marco se dan en CCW;
  _extruir corrige por si solo el sistema a izquierdas de eje='y'.
- Cada build_* devuelve un Empty raiz; los hijos (mallas) cuelgan de el con
  location relativa y estan linkados a parent_collection.

API
- build_ermita(parent_collection, seed=0) -> Empty 'ITAL_ermita'
    Capilla de colina, planta 9 x 14 m (X x Y), fachada a +Y en y=+7.
    Hijos: ITAL_ermita_cuerpo (muros de piedra crema con esquinas de sillar,
    zocalo, tejado de teja a dos aguas con canales, espadana de remate
    redondeado con cruz, portada arqueada con puerta de madera, oculo,
    ventanitas laterales, rampa de acceso y banco de piedra),
    ITAL_ermita_campana (campana de bronce con yugo, objeto aparte para
    poder animarla) y dos ITAL_cipres laterales. <= 5000 tris en total.
- build_capitella(parent_collection, seed=0) -> Empty 'ITAL_capitella'
    Edicula de camino 1.2 x 1.2 m: pedestal, cuerpo con hornacina azul
    (nicho con fondo y laterales azules, sol dorado, dos macetas con
    flores), marco de arco y tejadillo de teja con cruz. Hijo:
    ITAL_capitella_cuerpo. <= 800 tris.
- build_fuente(parent_collection, seed=0) -> Empty 'ITAL_fuente'
    Fuente de plaza: gradas, pilon circular r=2.2 (borde exterior 2.42),
    columna central con taza alta y remate, 4 canos con chorros.
    Hijos: ITAL_fuente_cuerpo (piedra), ITAL_fuente_agua (agua, aparte).
    <= 1500 tris.
- build_bancal(parent_collection, largo=30.0, alto=1.6, seed=0, fondo=7.0,
    sin_olivos=()) -> Empty 'ITAL_bancal': muro de piedra seca de contencion a lo largo de
    X (x en [-largo/2, largo/2]), cara vista a +Y en y=0 (ligeramente
    ataluzada hacia -Y), grosor 0.75; relleno de tierra detras hasta
    y=-fondo con la cara superior en z=alto cubierta de hierba amarilla y
    matas; albardilla de losas y piedras en relieve. Encima, OLIVOS cada
    ~7 m (mallas ITAL_olivo, <= 400 tris cada uno, copa plateada), salvo en
    los tramos locales de X `sin_olivos=[(x0, x1), ...]` (donde se apoya
    una ermita o cruza un camino). Para hacer una ladera con altibajos,
    apilar: el siguiente bancal en (y=-fondo+0.4, z=alto). Hijos:
    ITAL_bancal_muro, ITAL_bancal_tierra, ITAL_olivo*. Propiedades
    personalizadas en la raiz: largo, alto, fondo. Muro + tierra <= 40 tris/m.
- build_fila_cipreses(parent_collection, largo=40.0, paso=6.0, seed=0)
    -> Empty 'ITAL_cipreses': hilera de cipreses a lo largo de X (alturas
    8-12 m), mallas ITAL_cipres <= 250 tris cada una.
- build_pergola(parent_collection, largo=8.0, seed=0) -> Empty
    'ITAL_pergola': terraza de trattoria: solado de terracota, pergola de
    madera (postes, vigas y cabios) a lo largo de X con parra (hojas y
    racimos), mesas redondas con sombrilla a rayas, macetas y cartel
    TRATTORIA colgado en el frente (+Y). Hijos: ITAL_pergola_cuerpo,
    ITAL_pergola_parra. <= 3000 tris.
- build_hito(parent_collection, texto='PORTO CORSA 2', seed=0) -> Empty
    'ITAL_hito': mojon kilometrico italiano (piedra blanca con tapa roja,
    texto negro legible desde +Y; el ultimo token numerico va grande como
    km). Hijos: ITAL_hito_cuerpo, ITAL_hito_texto. <= 400 tris.
- build_cipres(parent_collection, alto=10.0, seed=0) / build_olivo(
    parent_collection, alto=4.0, seed=0): mallas sueltas ITAL_cipres /
    ITAL_olivo (sin Empty), para repartir por el mapa.
- build(parent_collection, seed=0): escaparate con todo (dos bancales
    apilados, ermita y cipreses en la cima, fuente, pergola, capitella e
    hito abajo). Devuelve el Empty 'ITAL_escaparate'.
"""

import math
import random

import bpy
from mathutils import Euler, Vector

PREFIX = "ITAL"
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Paleta plana estilo Cars 2: clave -> (color lineal, roughness, metallic,
# ruido). ruido = None | ('noise', color2, escala 1/m)
#   | ('piedra', color2, escala, estira (x, y, z), color_junta, ancho_junta)
# 'piedra' = celdas Voronoi (tono por piedra entre color y color2) con juntas
# oscuras; 'estira' alarga las celdas (piedras mas anchas que altas).
# ---------------------------------------------------------------------------
_PALETA = {
    "piedra_crema":   ((0.82, 0.70, 0.48), 0.90, 0.0, ("noise", (0.70, 0.57, 0.36), 0.8)),
    "sillar":         ((0.68, 0.60, 0.44), 0.85, 0.0, None),
    "sillar_claro":   ((0.78, 0.71, 0.56), 0.85, 0.0, None),
    "piedra_seca":    ((0.62, 0.52, 0.35), 0.92, 0.0,
                       ("piedra", (0.46, 0.37, 0.24), 1.5, (1.0, 1.0, 2.4), (0.26, 0.21, 0.14), 0.07)),
    "albardilla":     ((0.66, 0.58, 0.42), 0.88, 0.0, None),
    "teja":           ((0.74, 0.30, 0.14), 0.85, 0.0, ("noise", (0.60, 0.22, 0.10), 1.4)),
    "teja_clara":     ((0.86, 0.42, 0.22), 0.85, 0.0, None),
    "cumbrera":       ((0.62, 0.24, 0.11), 0.85, 0.0, None),
    "madera_oscura":  ((0.24, 0.13, 0.06), 0.75, 0.0, None),
    "madera":         ((0.50, 0.30, 0.13), 0.80, 0.0, None),
    "madera_clara":   ((0.66, 0.44, 0.22), 0.80, 0.0, None),
    "hierro":         ((0.05, 0.05, 0.06), 0.45, 0.6, None),
    "bronce":         ((0.78, 0.56, 0.22), 0.35, 0.9, None),
    "vidrio":         ((0.16, 0.36, 0.62), 0.15, 0.0, None),
    "sombra":         ((0.09, 0.07, 0.06), 0.90, 0.0, None),
    "cipres":         ((0.05, 0.18, 0.07), 0.85, 0.0, None),
    "cipres_claro":   ((0.11, 0.27, 0.10), 0.85, 0.0, None),
    "tronco":         ((0.28, 0.18, 0.09), 0.95, 0.0, None),
    "olivo_plata":    ((0.29, 0.37, 0.19), 0.75, 0.0, None),
    "olivo_salvia":   ((0.16, 0.28, 0.10), 0.80, 0.0, None),
    "tierra":         ((0.50, 0.32, 0.14), 0.95, 0.0, ("noise", (0.38, 0.23, 0.10), 0.6)),
    "hierba_seca":    ((0.72, 0.62, 0.24), 0.92, 0.0, ("noise", (0.56, 0.52, 0.18), 1.1)),
    "hierba_mata":    ((0.56, 0.54, 0.17), 0.92, 0.0, None),
    "agua":           ((0.08, 0.50, 0.62), 0.08, 0.0, None),
    "azul_hornacina": ((0.10, 0.32, 0.78), 0.60, 0.0, None),
    "oro":            ((0.95, 0.72, 0.18), 0.30, 0.8, None),
    "flor_rojo":      ((0.85, 0.08, 0.06), 0.60, 0.0, None),
    "flor_amarillo":  ((0.95, 0.72, 0.08), 0.60, 0.0, None),
    "flor_rosa":      ((0.92, 0.30, 0.55), 0.60, 0.0, None),
    "terracota":      ((0.72, 0.38, 0.22), 0.90, 0.0, None),
    "suelo_terraza":  ((0.66, 0.36, 0.22), 0.90, 0.0,
                       ("piedra", (0.56, 0.28, 0.16), 2.2, (1.0, 1.0, 1.0), (0.32, 0.18, 0.10), 0.06)),
    "parra":          ((0.18, 0.46, 0.10), 0.70, 0.0, None),
    "parra_clara":    ((0.36, 0.62, 0.16), 0.70, 0.0, None),
    "uva":            ((0.28, 0.06, 0.30), 0.45, 0.0, None),
    "mantel":         ((0.95, 0.92, 0.84), 0.70, 0.0, None),
    "sombrilla_rojo": ((0.82, 0.10, 0.08), 0.60, 0.0, None),
    "sombrilla_crema": ((0.96, 0.92, 0.80), 0.60, 0.0, None),
    "blanco":         ((0.93, 0.92, 0.88), 0.55, 0.0, None),
    "rojo":           ((0.82, 0.08, 0.06), 0.50, 0.0, None),
    "negro":          ((0.02, 0.02, 0.02), 0.60, 0.0, None),
    "verde_cartel":   ((0.06, 0.32, 0.14), 0.55, 0.0, None),
}


def _nodos_ruido(nt, bsdf, color, ruido):
    """Conecta al Base Color un ruido procedural en coordenadas de objeto."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    src = tc.outputs["Object"]
    if ruido[0] == "piedra":
        _, color2, escala, estira, cjunta, ajunta = ruido
        esc = nt.nodes.new("ShaderNodeVectorMath")
        esc.operation = "MULTIPLY"
        esc.inputs[1].default_value = estira
        nt.links.new(src, esc.inputs[0])
        src = esc.outputs["Vector"]
        vor_e = nt.nodes.new("ShaderNodeTexVoronoi")
        vor_e.feature = "DISTANCE_TO_EDGE"
        vor_e.inputs["Scale"].default_value = escala
        if "Randomness" in vor_e.inputs:
            vor_e.inputs["Randomness"].default_value = 0.72
        nt.links.new(src, vor_e.inputs["Vector"])
        juntas = nt.nodes.new("ShaderNodeValToRGB")
        el = juntas.color_ramp.elements
        el[0].position, el[1].position = ajunta * 0.35, ajunta
        el[0].color = (cjunta[0], cjunta[1], cjunta[2], 1.0)
        el[1].color = (1.0, 1.0, 1.0, 1.0)
        nt.links.new(vor_e.outputs["Distance"], juntas.inputs["Fac"])
        vor_c = nt.nodes.new("ShaderNodeTexVoronoi")
        vor_c.feature = "F1"
        vor_c.inputs["Scale"].default_value = escala
        if "Randomness" in vor_c.inputs:
            vor_c.inputs["Randomness"].default_value = 0.72
        nt.links.new(src, vor_c.inputs["Vector"])
        tono = nt.nodes.new("ShaderNodeValToRGB")
        el2 = tono.color_ramp.elements
        el2[0].position, el2[1].position = 0.15, 0.85
        el2[0].color = (color[0], color[1], color[2], 1.0)
        el2[1].color = (color2[0], color2[1], color2[2], 1.0)
        nt.links.new(vor_c.outputs["Color"], tono.inputs["Fac"])
        mul = nt.nodes.new("ShaderNodeVectorMath")
        mul.operation = "MULTIPLY"
        nt.links.new(tono.outputs["Color"], mul.inputs[0])
        nt.links.new(juntas.outputs["Color"], mul.inputs[1])
        nt.links.new(mul.outputs["Vector"], bsdf.inputs["Base Color"])
    else:
        _, color2, escala = ruido
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = escala
        if "Detail" in tex.inputs:
            tex.inputs["Detail"].default_value = 2.0
        nt.links.new(src, tex.inputs["Vector"])
        rampa = nt.nodes.new("ShaderNodeValToRGB")
        el = rampa.color_ramp.elements
        el[0].position, el[1].position = 0.35, 0.65
        el[0].color = (color[0], color[1], color[2], 1.0)
        el[1].color = (color2[0], color2[1], color2[2], 1.0)
        nt.links.new(tex.outputs["Fac"], rampa.inputs["Fac"])
        nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])


def _mat(key):
    """Devuelve (reutilizando si existe) el material MAT_ITAL_<key>."""
    name = "MAT_%s_%s" % (PREFIX, key)
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    color, rough, metal, ruido = _PALETA[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out is None:
            out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metal
    if ruido is not None:
        try:
            _nodos_ruido(nt, bsdf, color, ruido)
        except Exception as ex:  # el ruido nunca debe tumbar el build
            print("italiano_kit: sin ruido en %s (%s)" % (name, ex))
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    # como en el kn5 de Assetto Corsa: solo se pinta la cara frontal, asi
    # los previews de EEVEE delatan cualquier chunk con normales invertidas
    m.use_backface_culling = True
    return m


# ---------------------------------------------------------------------------
# Acumulador de malla multi-material
# ---------------------------------------------------------------------------
class _MB:
    """Acumula (verts, faces, material, smooth) y construye una malla unica."""

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

    def build(self, name, parent_collection, parent=None, loc=(0.0, 0.0, 0.0)):
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
        if parent is not None:
            ob.parent = parent
        ob.location = loc
        return ob


def _empty(name, parent_collection, parent=None, loc=(0.0, 0.0, 0.0), size=1.5):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = size
    parent_collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    ob.location = loc
    return ob


# ---------------------------------------------------------------------------
# Primitivas procedurales -> (verts, faces)
# ---------------------------------------------------------------------------
def _rot_off(verts, off=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0)):
    """Aplica rotacion Euler XYZ (radianes) y traslacion a una lista de verts."""
    ox, oy, oz = off
    if rot == (0.0, 0.0, 0.0) or rot is None:
        return [(x + ox, y + oy, z + oz) for (x, y, z) in verts]
    m = Euler(rot, "XYZ").to_matrix()
    out = []
    for v in verts:
        p = m @ Vector(v)
        out.append((p.x + ox, p.y + oy, p.z + oz))
    return out


def _box(sx, sy, sz, off=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), base=False):
    """Caja de lados (sx, sy, sz) centrada en `off` (o con la base en `off`
    si base=True), rotada por `rot` alrededor de su centro/base."""
    hx, hy = sx / 2.0, sy / 2.0
    z0, z1 = (0.0, sz) if base else (-sz / 2.0, sz / 2.0)
    v = [(-hx, -hy, z0), (hx, -hy, z0), (hx, hy, z0), (-hx, hy, z0),
         (-hx, -hy, z1), (hx, -hy, z1), (hx, hy, z1), (-hx, hy, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    return _rot_off(v, off, rot), f


def _extruir(perfil, a0, a1, eje="z", off=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0)):
    """Prisma: poligono cerrado `perfil` [(a, b), ...] extruido de a0 a a1 a lo
    largo de `eje`. eje='z': (a, b) = (x, y); 'x': (a, b) = (y, z);
    'y': (a, b) = (x, z). Tapas como n-gonos."""
    n = len(perfil)

    def P(a, b, c):
        if eje == "z":
            return (a, b, c)
        if eje == "x":
            return (c, a, b)
        return (a, c, b)

    v = [P(a, b, a0) for (a, b) in perfil] + [P(a, b, a1) for (a, b) in perfil]
    f = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        f.append((i, j, n + j, n + i))
    # (x, z, y) es un sistema a izquierdas (permutacion impar): con eje='y'
    # un perfil CCW en (x, z) saldria con todas las caras hacia dentro, asi
    # que se invierte el winding. Lo mismo si se extruye hacia atras (a1<a0).
    if (eje == "y") != (a1 < a0):
        f = [tuple(reversed(face)) for face in f]
    return _rot_off(v, off, rot), f


def _lathe(profile, seg=8, off=(0.0, 0.0, 0.0), rng=None, jit=0.0,
           scale=(1.0, 1.0, 1.0), fase=0.0):
    """Revolucion alrededor de Z. profile = [(radio, z), ...] de abajo a
    arriba; radio 0 en un extremo = polo. `fase` gira los segmentos."""
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
                th = TAU * k / seg + fase
                f = 1.0 + (rng.uniform(-jit, jit) if (rng is not None and jit) else 0.0)
                row.append(len(verts))
                verts.append((r * f * math.cos(th), r * f * math.sin(th), z))
            rows.append(tuple(row))
    for i in range(len(rows) - 1):
        a = rows[i]
        b = rows[i + 1]
        if len(a) == 1 and len(b) > 1:      # polo inferior
            for k in range(seg):
                faces.append((a[0], b[(k + 1) % seg], b[k]))
        elif len(b) == 1 and len(a) > 1:    # polo superior
            for k in range(seg):
                faces.append((b[0], a[k], a[(k + 1) % seg]))
        elif len(a) > 1 and len(b) > 1:
            for k in range(seg):
                k2 = (k + 1) % seg
                faces.append((a[k], a[k2], b[k2], b[k]))
    sx, sy, sz = scale
    ox, oy, oz = off
    verts = [(x * sx + ox, y * sy + oy, z * sz + oz) for (x, y, z) in verts]
    return verts, faces


def _sphere(r=1.0, seg=8, rings=5, scale=(1.0, 1.0, 1.0), off=(0.0, 0.0, 0.0),
            rng=None, jit=0.0):
    """Esfera UV low-poly con jitter radial opcional (copas, matas, flores)."""
    verts = []
    faces = []

    def j():
        return 1.0 + (rng.uniform(-jit, jit) if (rng is not None and jit) else 0.0)

    verts.append((0.0, 0.0, r * j()))
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
    verts.append((0.0, 0.0, -r * j()))
    r0 = ring_rows[0]
    for k in range(seg):
        faces.append((0, r0[k], r0[(k + 1) % seg]))
    for i in range(len(ring_rows) - 1):
        up, lo = ring_rows[i], ring_rows[i + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((up[k], lo[k], lo[k2], up[k2]))
    rl = ring_rows[-1]
    for k in range(seg):
        faces.append((bot, rl[(k + 1) % seg], rl[k]))
    sx, sy, sz = scale
    ox, oy, oz = off
    verts = [(x * sx + ox, y * sy + oy, z * sz + oz) for (x, y, z) in verts]
    return verts, faces


def _tube(points, radii, sides=6, cap_top=True):
    """Barre una seccion circular por una polilinea 3D (troncos, ramas, canos)."""
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
        if t.length < 1e-9:
            t = Vector((0.0, 0.0, 1.0))
        t.normalize()
        ref = Vector((1.0, 0.0, 0.0)) if abs(t.x) < 0.9 else Vector((0.0, 1.0, 0.0))
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
        a, b = rings[i], rings[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((a[k], a[k2], b[k2], b[k]))
    if cap_top:
        c = len(verts)
        verts.append(tuple(points[-1]))
        b = rings[-1]
        for k in range(sides):
            faces.append((c, b[k], b[(k + 1) % sides]))
    return verts, faces


def _disco(r, seg=12, off=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), fase=0.0):
    """Disco plano (abanico) en el plano XY, normal +Z antes de rotar."""
    v = [(0.0, 0.0, 0.0)]
    for k in range(seg):
        th = TAU * k / seg + fase
        v.append((r * math.cos(th), r * math.sin(th), 0.0))
    f = [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)]
    return _rot_off(v, off, rot), f


def _marco(inner, outer, prof, cerrado, off=(0.0, 0.0, 0.0), rot_z=0.0):
    """Anillo/marco con seccion rectangular: perfiles interior y exterior
    [(x, z), ...] con el MISMO numero de puntos, extruido en Y de -prof/2 a
    +prof/2. Si no es cerrado se tapan los dos extremos (pies)."""
    m = len(inner)
    yA, yB = -prof / 2.0, prof / 2.0
    v = ([(x, yA, z) for (x, z) in inner] + [(x, yA, z) for (x, z) in outer]
         + [(x, yB, z) for (x, z) in inner] + [(x, yB, z) for (x, z) in outer])
    fi, fo, bi, bo = 0, m, 2 * m, 3 * m
    f = []
    rng_i = range(m) if cerrado else range(m - 1)
    for i in rng_i:
        j = (i + 1) % m
        f.append((fi + i, fo + i, fo + j, fi + j))      # cara frontal (-Y)
        f.append((bi + i, bi + j, bo + j, bo + i))      # cara trasera (+Y)
        f.append((fi + i, fi + j, bi + j, bi + i))      # intrados
        f.append((fo + i, bo + i, bo + j, fo + j))      # extrados
    if not cerrado:
        f.append((fi, bi, bo, fo))
        f.append((fi + m - 1, fo + m - 1, bo + m - 1, bi + m - 1))
    return _rot_off(v, off, (0.0, 0.0, rot_z)), f


def _anillo_arco(ri, ro, h_pie, prof, n=8, off=(0.0, 0.0, 0.0), rot_z=0.0, techo=None):
    """Marco de arco de medio punto: pilares de ancho ro-ri y altura h_pie,
    hueco de radio ri; exterior redondeado de radio ro o, si se pasa `techo`
    (z), rectangular hasta esa altura. Origen: centro de la base del hueco,
    plano XZ, mirando a +Y."""
    inner = [(-ri, 0.0)]
    outer = [(-ro, 0.0)]
    per = 2.0 * (techo - h_pie) + 2.0 * ro if techo is not None else 0.0
    for k in range(n + 1):
        th = math.pi - math.pi * k / n
        inner.append((ri * math.cos(th), h_pie + ri * math.sin(th)))
        if techo is None:
            outer.append((ro * math.cos(th), h_pie + ro * math.sin(th)))
        else:
            s = per * k / float(n)
            h = techo - h_pie
            if s <= h:
                outer.append((-ro, h_pie + s))
            elif s <= h + 2.0 * ro:
                outer.append((-ro + (s - h), techo))
            else:
                outer.append((ro, techo - (s - h - 2.0 * ro)))
    inner.append((ri, 0.0))
    outer.append((ro, 0.0))
    # el recorrido (-ri,0) -> arco -> (ri,0) es horario en (x, z); _marco
    # espera perfiles CCW (como _anillo_circ), asi que se invierten.
    return _marco(inner[::-1], outer[::-1], prof, False, off, rot_z)


def _anillo_circ(ri, ro, prof, n=12, off=(0.0, 0.0, 0.0), rot_z=0.0):
    """Anillo circular (oculo) en el plano XZ centrado en `off`."""
    inner = [(ri * math.cos(TAU * k / n), ri * math.sin(TAU * k / n)) for k in range(n)]
    outer = [(ro * math.cos(TAU * k / n), ro * math.sin(TAU * k / n)) for k in range(n)]
    return _marco(inner, outer, prof, True, off, rot_z)


def _arco_panel(ri, h_pie, n=8, off=(0.0, 0.0, 0.0), rot_z=0.0):
    """Un solo n-gono con forma de arco (puerta, hueco oscuro) en el plano XZ."""
    pts = [(-ri, 0.0)]
    for k in range(n + 1):
        th = math.pi - math.pi * k / n
        pts.append((ri * math.cos(th), h_pie + ri * math.sin(th)))
    pts.append((ri, 0.0))
    v = [(x, 0.0, z) for (x, z) in pts]
    return _rot_off(v, off, (0.0, 0.0, rot_z)), [tuple(range(len(v)))]


# ---------------------------------------------------------------------------
# Texto 3D (curva FONT -> malla, sin depsgraph ni bpy.ops)
# ---------------------------------------------------------------------------
def _texto_datos(texto, tam, extrude=0.0, res=2):
    """(verts, faces, ancho, alto) del texto centrado en su plano XY local."""
    cu = bpy.data.curves.new("ITAL_txt_cu", type="FONT")
    cu.body = texto
    cu.size = tam
    cu.extrude = extrude
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.resolution_u = res
    try:
        cu.fill_mode = "FRONT" if extrude <= 0.0 else "BOTH"
    except Exception:
        pass
    tmp = bpy.data.objects.new("ITAL_txt_tmp", cu)
    me_t = bpy.data.meshes.new_from_object(tmp)
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    vs = [(v.co.x, v.co.y, v.co.z) for v in me_t.vertices]
    fs = [tuple(p.vertices) for p in me_t.polygons]
    bpy.data.meshes.remove(me_t)
    if vs:
        xs = [v[0] for v in vs]
        ys = [v[1] for v in vs]
        ancho, alto = max(xs) - min(xs), max(ys) - min(ys)
        cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
        vs = [(x - cx, y - cy, z) for (x, y, z) in vs]
    else:
        ancho = alto = 0.0
    return vs, fs, ancho, alto


def _texto_add(mb, datos, pos, mat, rot_z=0.0):
    """Anade a `mb` el texto de pie centrado en `pos`, legible desde +Y con
    rot_z=0 (desde -Y con rot_z=pi); el relieve sale hacia el lector."""
    vs, fs = datos[0], datos[1]
    x, y, z = pos
    co, si = math.cos(math.pi + rot_z), math.sin(math.pi + rot_z)
    verts = []
    for vx, vy, vz in vs:
        px, py, pz = vx, -vz, vy
        verts.append((x + px * co - py * si, y + px * si + py * co, z + pz))
    mb.add(verts, fs, mat, smooth=False)


# ---------------------------------------------------------------------------
# Tejado de teja a dos aguas (cumbrera a lo largo de Y, en x=0)
# ---------------------------------------------------------------------------
def _tejado(mb, hw, hd, he, hr, vuelo=0.45, vuelo_g=0.35, t=0.2, paso=0.42,
            canal_w=0.16, canal_h=0.07, off=(0.0, 0.0, 0.0)):
    """Dos faldones (perfil extruido en Y) desde la cumbrera (x=0, z=hr) hasta
    el alero (x=+-hw, z=he) con vuelo, canales de teja a lo largo de la
    pendiente cada `paso` y cumbrera. Devuelve el punto del alero (xe, ze)."""
    pend = (hr - he) / hw
    xe = hw + vuelo
    ze = he - vuelo * pend
    y0, y1 = -hd - vuelo_g, hd + vuelo_g
    L = math.hypot(xe, hr - ze)
    ox, oy, oz = off
    for sgn in (1, -1):
        perfil = [(0.0, hr), (sgn * xe, ze), (sgn * xe, ze + t), (0.0, hr + t)]
        if sgn < 0:
            perfil.reverse()
        mb.add(*_extruir(perfil, y0, y1, eje="y", off=off), _mat("teja"))
        beta = math.atan2(-sgn * xe, hr - ze)
        # triangulo CCW en (x, y) para ambos signos (caras hacia fuera)
        perfil_c = [(sgn * canal_h, 0.0), (0.0, sgn * canal_w / 2.0), (0.0, -sgn * canal_w / 2.0)]
        nrow = int((y1 - y0 - 0.3) / paso)
        for i in range(nrow + 1):
            y = y0 + 0.15 + i * paso
            mb.add(*_extruir(perfil_c, 0.0, L - 0.04, eje="z",
                             off=(ox + sgn * xe, oy + y, oz + ze + t), rot=(0.0, beta, 0.0)),
                   _mat("teja_clara"))
    mb.add(*_box(0.40, y1 - y0, 0.16, off=(ox, oy, oz + hr + t + 0.02)), _mat("cumbrera"))
    return xe, ze


# ---------------------------------------------------------------------------
# VEGETACION: cipres y olivo (mallas sueltas)
# ---------------------------------------------------------------------------
def build_cipres(parent_collection, alto=10.0, seed=0):
    """Cipres italiano low-poly: huso verde oscuro con lobulos claros y
    tronco corto. Origen en la base, <= 250 tris."""
    rng = random.Random(7919 * seed + 3)
    mb = _MB()
    a = alto
    rmax = a * rng.uniform(0.085, 0.105)
    perfil = [(0.0, 0.0), (rmax * 0.35, a * 0.02), (rmax * 0.80, a * 0.10),
              (rmax, a * 0.26), (rmax * 0.96, a * 0.46), (rmax * 0.80, a * 0.66),
              (rmax * 0.55, a * 0.82), (rmax * 0.27, a * 0.94), (0.0, a)]
    v, f = _lathe(perfil, seg=7, rng=rng, jit=0.10, fase=rng.uniform(0.0, TAU))
    lean = math.radians(rng.uniform(-2.0, 2.0))
    v = [(x + z * math.tan(lean), y, z) for (x, y, z) in v]
    mb.add(v, f, _mat("cipres"), smooth=True)
    for _ in range(3):
        z = a * rng.uniform(0.25, 0.75)
        th = rng.uniform(0.0, TAU)
        rr = rmax * (1.0 - abs(z / a - 0.4) * 0.9) * 0.85
        rl = rmax * rng.uniform(0.32, 0.45)
        mb.add(*_sphere(rl, seg=6, rings=3, scale=(1.0, 1.0, 2.2),
                        off=(math.cos(th) * rr + z * math.tan(lean), math.sin(th) * rr, z),
                        rng=rng, jit=0.12),
               _mat("cipres_claro"), smooth=True)
    mb.add(*_tube([(0.0, 0.0, 0.0), (0.0, 0.0, a * 0.06)], [a * 0.016, a * 0.013], sides=5),
           _mat("tronco"), smooth=True)
    return mb.build("%s_cipres" % PREFIX, parent_collection)


def build_fila_cipreses(parent_collection, largo=40.0, paso=6.0, seed=0):
    """Hilera de cipreses a lo largo de X (alturas 8-12 m). Empty ITAL_cipreses."""
    rng = random.Random(7919 * seed + 11)
    root = _empty("%s_cipreses" % PREFIX, parent_collection)
    n = max(2, int(round(largo / paso)) + 1)
    for i in range(n):
        x = -largo / 2.0 + i * (largo / (n - 1.0)) + rng.uniform(-0.4, 0.4) * min(1.0, paso / 6.0)
        x = max(-largo / 2.0, min(largo / 2.0, x))
        ob = build_cipres(parent_collection, alto=rng.uniform(8.0, 12.0), seed=seed * 101 + i)
        ob.parent = root
        ob.location = (x, rng.uniform(-0.3, 0.3), 0.0)
        ob.rotation_euler = (0.0, 0.0, rng.uniform(0.0, TAU))
    return root


def build_olivo(parent_collection, alto=4.0, seed=0):
    """Olivo low-poly: tronco nudoso, 2-3 ramas y copa en 4-5 masas
    plateadas irregulares. Origen en la base, <= 400 tris."""
    rng = random.Random(7919 * seed + 29)
    mb = _MB()
    a = alto
    ht = a * rng.uniform(0.40, 0.48)
    pts = [(0.0, 0.0, 0.0)]
    dx = dy = 0.0
    for i in range(1, 4):
        dx += rng.uniform(-1.0, 1.0) * 0.05 * a
        dy += rng.uniform(-1.0, 1.0) * 0.05 * a
        pts.append((dx, dy, ht * i / 3.0))
    radii = [a * 0.085, a * 0.075, a * 0.062, a * 0.045]
    mb.add(*_tube(pts, radii, sides=6), _mat("tronco"), smooth=True)
    mb.add(*_lathe([(0.14 * a, 0.0), (0.09 * a, 0.06 * a), (0.07 * a, 0.12 * a)],
                   seg=6, rng=rng, jit=0.12), _mat("tronco"), smooth=True)
    top = Vector(pts[-1])
    nb = rng.randint(2, 3)
    yaw0 = rng.uniform(0.0, TAU)
    centros = []
    for i in range(nb):
        yaw = yaw0 + TAU * i / nb + rng.uniform(-0.3, 0.3)
        d = a * rng.uniform(0.12, 0.22)
        c = Vector((top.x + math.cos(yaw) * d, top.y + math.sin(yaw) * d, a * rng.uniform(0.58, 0.68)))
        centros.append(c)
        mb.add(*_tube([Vector(pts[2]), c - Vector((0.0, 0.0, 0.05 * a))],
                      [0.035 * a, 0.018 * a], sides=5),
               _mat("tronco"), smooth=True)
    masas = list(centros) + [Vector((top.x * 0.5, top.y * 0.5, a * 0.74))]
    while len(masas) < 5:
        yaw = rng.uniform(0.0, TAU)
        d = a * rng.uniform(0.10, 0.20)
        masas.append(Vector((top.x + math.cos(yaw) * d, top.y + math.sin(yaw) * d,
                             a * rng.uniform(0.60, 0.70))))
    for i, c in enumerate(masas[:5]):
        r = a * rng.uniform(0.21, 0.27)
        key = "olivo_plata" if i % 2 == 0 else "olivo_salvia"
        mb.add(*_sphere(r, seg=8, rings=4,
                        scale=(rng.uniform(1.0, 1.2), rng.uniform(1.0, 1.2), 0.78),
                        off=c, rng=rng, jit=0.13),
               _mat(key), smooth=True)
    return mb.build("%s_olivo" % PREFIX, parent_collection)


# ---------------------------------------------------------------------------
# ERMITA DE COLINA (planta 9 x 14, fachada a +Y)
# ---------------------------------------------------------------------------
def build_ermita(parent_collection, seed=0):
    """Capilla de colina con espadana, portada arqueada, oculo, tejado de
    teja, sillares en esquina, dos cipreses y banco. Empty ITAL_ermita."""
    rng = random.Random(7919 * seed + 41)
    root = _empty("%s_ermita" % PREFIX, parent_collection, size=3.0)
    hw, hd = 4.5, 7.0          # semi-planta (X, Y)
    he, hr = 5.0, 7.4          # alero y cumbrera
    zoc = 0.35                 # zocalo (umbral de la puerta)
    S, SC, PC = _mat("sillar"), _mat("sillar_claro"), _mat("piedra_crema")
    mb = _MB()

    # zocalo y muros (prisma pentagonal extruido en Y)
    mb.add(*_box(2 * hw + 0.3, 2 * hd + 0.3, zoc, base=True), S)
    perfil = [(-hw, 0.0), (hw, 0.0), (hw, he), (0.0, hr), (-hw, he)]
    mb.add(*_extruir(perfil, -hd, hd, eje="y"), PC)

    # esquinas de sillar: bloques alternos largo/corto
    for sx in (-1, 1):
        for sy in (-1, 1):
            for i in range(8):
                z = zoc + 0.05 + i * 0.57
                if i % 2 == 0:
                    mb.add(*_box(1.1, 0.56, 0.5, off=(sx * (hw - 0.5), sy * (hd - 0.225), z + 0.25)),
                           S if i % 4 == 0 else SC)
                else:
                    mb.add(*_box(0.56, 1.1, 0.5, off=(sx * (hw - 0.225), sy * (hd - 0.5), z + 0.25)),
                           SC if i % 4 == 1 else S)
    # cornisa bajo el alero (lados +-X)
    for sx in (-1, 1):
        mb.add(*_box(0.30, 2 * hd + 0.2, 0.22, off=(sx * (hw + 0.1), 0.0, he - 0.11)), S)

    # tejado de teja a dos aguas con canales
    _tejado(mb, hw, hd, he, hr, vuelo=0.5, vuelo_g=0.4, t=0.22, paso=0.45)

    # espadana: base, imposta, arco redondeado, pedestal y cruz
    yb = hd - 0.25
    mb.add(*_box(2.6, 0.5, 1.15, off=(0.0, yb, 7.12)), PC)
    mb.add(*_box(2.8, 0.62, 0.12, off=(0.0, yb, 7.72)), S)
    zarc = 7.78
    mb.add(*_anillo_arco(0.55, 1.15, 1.0, 0.5, n=8, off=(0.0, yb, zarc)), PC)
    ztop = zarc + 1.0 + 1.15
    mb.add(*_box(0.34, 0.34, 0.14, off=(0.0, yb, ztop + 0.05)), S)
    mb.add(*_box(0.12, 0.12, 0.95, off=(0.0, yb, ztop + 0.12), base=True), _mat("hierro"))
    mb.add(*_box(0.62, 0.12, 0.12, off=(0.0, yb, ztop + 0.12 + 0.68)), _mat("hierro"))

    # portada: marco de sillar arqueado, puerta de madera con herrajes
    yf = hd
    mb.add(*_anillo_arco(0.85, 1.20, 1.5, 0.4, n=8, off=(0.0, yf + 0.05, zoc)), S)
    mb.add(*_arco_panel(0.83, 1.5, n=8, off=(0.0, yf + 0.07, zoc)), _mat("madera_oscura"))
    for dz in (0.45, 1.25, 1.95):
        mb.add(*_box(1.62, 0.03, 0.09, off=(0.0, yf + 0.085, zoc + dz)), _mat("hierro"))
    mb.add(*_box(0.04, 0.03, 2.28, off=(0.0, yf + 0.085, zoc), base=True), _mat("hierro"))
    for sx in (-1, 1):
        mb.add(*_sphere(0.05, seg=5, rings=2, off=(sx * 0.22, yf + 0.11, zoc + 1.15)), _mat("hierro"))

    # oculo (anillo + vidriera azul)
    mb.add(*_anillo_circ(0.42, 0.60, 0.30, n=12, off=(0.0, yf + 0.05, 5.35)), S)
    mb.add(*_disco(0.44, 12, off=(0.0, yf + 0.035, 5.35), rot=(-math.pi / 2.0, 0.0, 0.0)), _mat("vidrio"))

    # ventanitas laterales (+-X): rot_z=-sx*pi/2 gira la normal +Y a +-X
    for sx in (-1, 1):
        for y in (-3.4, 0.6):
            mb.add(*_anillo_arco(0.32, 0.48, 0.85, 0.30, n=6,
                                 off=(sx * (hw + 0.05), y, 2.6), rot_z=-sx * math.pi / 2.0), S)
            mb.add(*_arco_panel(0.30, 0.85, n=6, off=(sx * (hw + 0.02), y, 2.6),
                                rot_z=-sx * math.pi / 2.0), _mat("sombra"))

    # rampa de acceso (mundo de coches: escalera = rampa) y banco de piedra
    mb.add(*_box(3.4, 1.45, zoc, off=(0.0, yf + 0.15 + 0.725, 0.0), base=True), SC)
    mb.add(*_extruir([(yf + 1.6, 0.0), (yf + 3.4, 0.0), (yf + 1.6, zoc)], -1.7, 1.7, eje="x"), SC)
    bx, by = 3.3, yf + 2.4
    mb.add(*_box(2.0, 0.55, 0.16, off=(bx, by, 0.50)), S)
    for dx in (-0.7, 0.7):
        mb.add(*_box(0.30, 0.45, 0.42, off=(bx + dx, by, 0.21)), SC)
    mb.build("%s_ermita_cuerpo" % PREFIX, parent_collection, parent=root)

    # campana de bronce con yugo (objeto aparte)
    mc = _MB()
    mc.add(*_box(1.3, 0.16, 0.14, off=(0.0, 0.0, 0.72)), _mat("madera_oscura"))
    mc.add(*_box(0.18, 0.12, 0.10, off=(0.0, 0.0, 0.66)), _mat("hierro"))
    campana = [(0.30, 0.0), (0.33, 0.05), (0.28, 0.10), (0.24, 0.30), (0.20, 0.50),
               (0.13, 0.60), (0.0, 0.66)]
    mc.add(*_lathe(campana, seg=10), _mat("bronce"), smooth=True)
    mc.add(*_sphere(0.05, seg=5, rings=2, off=(0.0, 0.0, 0.05)), _mat("hierro"))
    mc.build("%s_ermita_campana" % PREFIX, parent_collection, parent=root, loc=(0.0, yb, zarc + 0.58))

    # cipreses laterales
    for i, (sx, h) in enumerate(((-1, 9.6), (1, 10.8))):
        ob = build_cipres(parent_collection, alto=h, seed=seed * 7 + i)
        ob.parent = root
        ob.location = (sx * (hw + 1.7), hd - 1.4, 0.0)
        ob.rotation_euler = (0.0, 0.0, rng.uniform(0.0, TAU))
    return root


# ---------------------------------------------------------------------------
# CAPITELLA (edicula de camino 1.2 x 1.2)
# ---------------------------------------------------------------------------
def build_capitella(parent_collection, seed=0):
    """Capillita de camino: pedestal, cuerpo con hornacina azul (sol dorado y
    macetas con flores), marco de arco y tejadillo de teja con cruz."""
    rng = random.Random(7919 * seed + 53)
    root = _empty("%s_capitella" % PREFIX, parent_collection, size=1.0)
    S, SC, PC = _mat("sillar"), _mat("sillar_claro"), _mat("piedra_crema")
    AZ = _mat("azul_hornacina")
    mb = _MB()
    mb.add(*_box(1.2, 1.2, 0.85, base=True), PC)
    mb.add(*_box(1.32, 1.32, 0.08, off=(0.0, 0.0, 0.89)), S)
    zb, H = 0.93, 1.35
    mb.add(*_box(1.0, 0.45, H, off=(0.0, -0.225, zb + H / 2.0)), PC)        # trasera
    for sx in (-1, 1):
        mb.add(*_box(0.22, 0.45, H, off=(sx * 0.39, 0.225, zb + H / 2.0)), PC)  # mejillas
    mb.add(*_box(0.56, 0.45, 0.30, off=(0.0, 0.225, zb + H - 0.15)), PC)      # dintel
    # hornacina azul: fondo arqueado, laterales, repisa y sol dorado
    mb.add(*_arco_panel(0.28, 0.72, n=6, off=(0.0, 0.006, zb + 0.005)), AZ)
    for sx in (-1, 1):
        mb.add(*_box(0.012, 0.44, 1.0, off=(sx * 0.275, 0.225, zb + 0.5)), AZ)
    mb.add(*_box(0.72, 0.58, 0.07, off=(0.0, 0.31, zb + 0.035)), S)
    mb.add(*_disco(0.13, 8, off=(0.0, 0.02, zb + 0.66), rot=(-math.pi / 2.0, 0.0, 0.0)), _mat("oro"))
    for k in range(8):
        th = TAU * k / 8.0
        mb.add(*_box(0.03, 0.01, 0.10, off=(math.cos(th) * 0.19, 0.02, zb + 0.66 + math.sin(th) * 0.19),
                     rot=(0.0, -th + math.pi / 2.0, 0.0)), _mat("oro"))
    mb.add(*_anillo_arco(0.28, 0.50, 0.72, 0.14, n=6, off=(0.0, 0.52, zb)), S)
    # macetas con flores
    for i, sx in enumerate((-1, 1)):
        px, py = sx * 0.16, 0.30
        mb.add(*_lathe([(0.07, 0.0), (0.09, 0.13), (0.105, 0.16)], seg=6, off=(px, py, zb + 0.07)),
               _mat("terracota"))
        mb.add(*_sphere(0.11, seg=6, rings=3, scale=(1.2, 1.2, 0.8), off=(px, py, zb + 0.26),
                        rng=rng, jit=0.15), _mat("parra"), smooth=True)
        for j, key in enumerate(("flor_rojo", "flor_amarillo", "flor_rosa")):
            th = TAU * j / 3.0 + i * 1.1
            mb.add(*_sphere(0.045, seg=5, rings=2,
                            off=(px + math.cos(th) * 0.08, py + math.sin(th) * 0.07, zb + 0.34)),
                   _mat(key), smooth=True)
    # tejadillo de teja con cruz
    _tejado(mb, 0.55, 0.55, zb + H, zb + H + 0.36, vuelo=0.14, vuelo_g=0.14, t=0.07,
            paso=0.22, canal_w=0.08, canal_h=0.035)
    zt = zb + H + 0.36 + 0.07 + 0.10
    mb.add(*_box(0.18, 0.18, 0.08, off=(0.0, 0.0, zt)), S)
    mb.add(*_box(0.05, 0.05, 0.42, off=(0.0, 0.0, zt + 0.04), base=True), _mat("hierro"))
    mb.add(*_box(0.26, 0.05, 0.05, off=(0.0, 0.0, zt + 0.34)), _mat("hierro"))
    mb.build("%s_capitella_cuerpo" % PREFIX, parent_collection, parent=root)
    return root


# ---------------------------------------------------------------------------
# HITO KILOMETRICO (piedra blanca, tapa roja, texto negro)
# ---------------------------------------------------------------------------
def build_hito(parent_collection, texto="PORTO CORSA 2", seed=0):
    """Mojon kilometrico italiano. El ultimo token numerico de `texto` va en
    grande (km); el resto en una linea pequena arriba. Legible desde +Y."""
    root = _empty("%s_hito" % PREFIX, parent_collection, size=0.6)
    W, D, H = 0.56, 0.40, 0.74
    mb = _MB()
    mb.add(*_box(W + 0.14, D + 0.14, 0.06, base=True), _mat("sillar"))
    mb.add(*_box(W, D, H, base=True), _mat("blanco"))
    k = math.sqrt(2.0) / 2.0
    mb.add(*_lathe([(1.0, 0.0), (1.0, 0.11), (0.80, 0.19), (0.0, 0.24)], seg=4, fase=math.pi / 4.0,
                   scale=(W / 2.0 / k, D / 2.0 / k, 1.0), off=(0.0, 0.0, H)), _mat("rojo"))
    mb.build("%s_hito_cuerpo" % PREFIX, parent_collection, parent=root)

    tokens = str(texto).split()
    num = tokens[-1] if tokens and tokens[-1].replace(".", "").replace(",", "").isdigit() else ""
    linea = " ".join(tokens[:-1] if num else tokens)
    mt = _MB()
    yf = D / 2.0 + 0.004
    if linea:
        tam = 0.075
        d = _texto_datos(linea, tam, res=2)
        if d[2] > W - 0.08:
            d = _texto_datos(linea, tam * (W - 0.08) / d[2], res=2)
        _texto_add(mt, d, (0.0, yf, H - 0.12), _mat("negro"))
    if num:
        tam = 0.30 if len(num) <= 2 else 0.22
        d = _texto_datos(num, tam, res=2)
        _texto_add(mt, d, (0.0, yf, H * 0.42), _mat("negro"))
    if mt.faces:
        mt.build("%s_hito_texto" % PREFIX, parent_collection, parent=root)
    return root


# ---------------------------------------------------------------------------
# FUENTE DE PLAZA (pilon circular r=2.2 con columna central)
# ---------------------------------------------------------------------------
def build_fuente(parent_collection, seed=0):
    """Fuente: gradas, pilon circular, columna con taza alta y remate, 4 canos
    de bronce con chorros. Hijos ITAL_fuente_cuerpo / ITAL_fuente_agua."""
    rng = random.Random(7919 * seed + 67)
    root = _empty("%s_fuente" % PREFIX, parent_collection, size=2.5)
    S, SC = _mat("sillar"), _mat("sillar_claro")
    AG = _mat("agua")
    mb = _MB()
    ma = _MB()
    # gradas y pilon (revolucion, 16 lados)
    mb.add(*_lathe([(3.10, 0.0), (3.10, 0.14), (2.66, 0.14), (2.66, 0.28), (2.32, 0.28)], seg=16), SC)
    pil = [(2.32, 0.28), (2.32, 0.88), (2.42, 0.88), (2.42, 1.06), (2.04, 1.06),
           (2.04, 0.62), (0.80, 0.62)]
    mb.add(*_lathe(pil, seg=16), S)
    ma.add(*_disco(2.05, 16, off=(0.0, 0.0, 0.96)), AG)
    # bolas decorativas sobre el borde del pilon
    for k in range(4):
        th = TAU * k / 4.0
        mb.add(*_box(0.36, 0.36, 0.12, off=(math.cos(th) * 2.23, math.sin(th) * 2.23, 1.12),
                     rot=(0.0, 0.0, th)), SC)
        mb.add(*_sphere(0.16, seg=6, rings=3, off=(math.cos(th) * 2.23, math.sin(th) * 2.23, 1.30)),
               SC, smooth=True)
    # columna central con taza alta y remate
    col = [(0.80, 0.62), (0.80, 0.98), (0.60, 1.06), (0.44, 1.12), (0.40, 1.30), (0.40, 2.05),
           (0.50, 2.16), (0.95, 2.30), (1.02, 2.50), (0.86, 2.50), (0.86, 2.40), (0.24, 2.40),
           (0.24, 2.92), (0.34, 2.98), (0.0, 3.25)]
    mb.add(*_lathe(col, seg=12), S)
    ma.add(*_disco(0.87, 12, off=(0.0, 0.0, 2.46)), AG)
    # canos de bronce y chorros parabolicos hasta el agua del pilon
    for k in range(4):
        th = TAU * k / 4.0 + math.pi / 4.0
        c, s = math.cos(th), math.sin(th)
        mb.add(*_tube([(0.36 * c, 0.36 * s, 1.62), (0.84 * c, 0.84 * s, 1.62)], [0.06, 0.05], sides=5),
               _mat("bronce"), smooth=True)
        pts = []
        for i in range(5):
            t = i / 4.0
            rr = 0.84 + (1.74 - 0.84) * t
            pts.append((rr * c, rr * s, 1.62 - 0.66 * t * t))
        ma.add(*_tube(pts, [0.045, 0.045, 0.045, 0.045, 0.045], sides=4, cap_top=False), AG, smooth=True)
        # salpicadura: anillo de gotas
        mb_g = _sphere(0.10, seg=5, rings=2, scale=(1.4, 1.4, 0.35), off=(1.74 * c, 1.74 * s, 0.97),
                       rng=rng, jit=0.2)
        ma.add(*mb_g, AG, smooth=True)
    # rebosadero de la taza alta: cortinillas de agua
    for k in range(6):
        th = TAU * k / 6.0 + 0.3
        c, s = math.cos(th), math.sin(th)
        ma.add(*_tube([(0.98 * c, 0.98 * s, 2.50), (1.06 * c, 1.06 * s, 2.30), (1.10 * c, 1.10 * s, 1.0)],
                      [0.05, 0.045, 0.035], sides=4, cap_top=False), AG, smooth=True)
    mb.build("%s_fuente_cuerpo" % PREFIX, parent_collection, parent=root)
    ma.build("%s_fuente_agua" % PREFIX, parent_collection, parent=root)
    return root


# ---------------------------------------------------------------------------
# BANCAL DE OLIVAR (muro de piedra seca de contencion + terraza)
# ---------------------------------------------------------------------------
def build_bancal(parent_collection, largo=30.0, alto=1.6, seed=0, fondo=7.0, sin_olivos=()):
    """Muro de piedra seca a lo largo de X con cara vista a +Y (y=0), relleno
    de tierra detras hasta y=-fondo con hierba amarilla en z=alto y olivos
    cada ~7 m (salvo en los tramos locales [(x0, x1), ...] de `sin_olivos`,
    p. ej. donde se apoya una ermita o cruza un camino). Apilable: el
    siguiente bancal en (y=-fondo+0.4, z=alto)."""
    rng = random.Random(7919 * seed + 83)
    root = _empty("%s_bancal" % PREFIX, parent_collection, size=2.0)
    L, A, F = float(largo), float(alto), max(2.0, float(fondo))
    root["largo"] = L
    root["alto"] = A
    root["fondo"] = F
    talud = 0.08 * A
    mw = _MB()
    mw.add(*_extruir([(-0.75, 0.0), (0.0, 0.0), (-talud, A), (-0.75, A)], -L / 2.0, L / 2.0, eje="x"),
           _mat("piedra_seca"))
    # albardilla de losas
    paso = 0.95
    n = max(1, int(L / paso))
    x0 = -L / 2.0 + (L - (n - 1) * paso) / 2.0
    for i in range(n):
        lw = 0.85 * rng.uniform(0.92, 1.05)
        mw.add(*_box(lw, 0.84, 0.16, off=(x0 + i * paso, -0.34 + rng.uniform(-0.02, 0.02), A + 0.07),
                     rot=(0.0, 0.0, math.radians(rng.uniform(-3.0, 3.0)))), _mat("albardilla"))
    # piedras en relieve sobre la cara vista: mismo material piedra_seca (el
    # Voronoi va en coordenadas de objeto, asi que se funden con el muro) y
    # ligeramente giradas para que no se lean como rectangulos pegados
    for _ in range(int(L * 1.2)):
        x = rng.uniform(-L / 2.0 + 0.4, L / 2.0 - 0.4)
        z = rng.uniform(0.18, A - 0.32)
        yf = -talud * z / A
        w, h = rng.uniform(0.45, 0.85), rng.uniform(0.20, 0.32)
        mw.add(*_box(w, 0.30, h, off=(x, yf - 0.09, z),
                     rot=(math.radians(rng.uniform(-4.0, 4.0)), math.radians(rng.uniform(-5.0, 5.0)), 0.0)),
               _mat("piedra_seca"))
    mw.build("%s_bancal_muro" % PREFIX, parent_collection, parent=root)

    mt = _MB()
    mt.add(*_extruir([(-F, 0.0), (-0.6, 0.0), (-0.6, A), (-F, A)], -L / 2.0, L / 2.0, eje="x"),
           _mat("tierra"))
    zt = A + 0.012
    # quad CCW visto desde arriba (normal +Z)
    mt.add([(-L / 2.0, -0.62, zt), (L / 2.0, -0.62, zt), (L / 2.0, -F + 0.02, zt), (-L / 2.0, -F + 0.02, zt)],
           [(0, 3, 2, 1)], _mat("hierba_seca"))
    for _ in range(int(L * 1.0)):
        x = rng.uniform(-L / 2.0 + 0.3, L / 2.0 - 0.3)
        y = rng.uniform(-F + 0.4, -0.95)
        r = rng.uniform(0.22, 0.34)
        mt.add(*_sphere(r, seg=5, rings=2, scale=(1.8, 1.4, 0.55), off=(x, y, A + r * 0.12),
                        rng=rng, jit=0.35), _mat("hierba_mata"))
    mt.build("%s_bancal_tierra" % PREFIX, parent_collection, parent=root)

    # olivos encima, cada ~7 m
    xo = -L / 2.0 + 3.5
    i = 0
    while xo < L / 2.0 - 2.0:
        xr = xo + rng.uniform(-0.8, 0.8)
        yo = rng.uniform(-3.4, -2.2) if F >= 4.5 else -F * 0.55
        rz = rng.uniform(0.0, TAU)
        if not any(x0 - 1.2 <= xr <= x1 + 1.2 for (x0, x1) in sin_olivos):
            ob = build_olivo(parent_collection, alto=rng.uniform(3.6, 4.6), seed=seed * 97 + i)
            ob.parent = root
            ob.location = (xr, yo, A)
            ob.rotation_euler = (0.0, 0.0, rz)
        xo += 7.0
        i += 1
    return root


# ---------------------------------------------------------------------------
# PERGOLA DE TRATTORIA (madera + parra + mesas con sombrilla)
# ---------------------------------------------------------------------------
def _mesa_sombrilla(mb, rng, x, y):
    """Mesa redonda de hierro con mantel y sombrilla a rayas rojo/crema."""
    mb.add(*_lathe([(0.06, 0.0), (0.27, 0.02), (0.27, 0.06), (0.05, 0.09), (0.05, 0.60)], seg=8,
                   off=(x, y, 0.08)), _mat("hierro"))
    mb.add(*_lathe([(0.0, 0.56), (0.60, 0.50), (0.60, 0.68), (0.0, 0.68)], seg=10, off=(x, y, 0.08)),
           _mat("mantel"))
    mb.add(*_tube([(x, y, 0.70), (x, y, 2.55)], [0.03, 0.03], sides=5), _mat("hierro"))
    apex = (x, y, 2.72)
    rim = [(x + 1.15 * math.cos(TAU * k / 8.0), y + 1.15 * math.sin(TAU * k / 8.0), 2.28) for k in range(8)]
    for par in (0, 1):
        v = [apex] + rim
        f_up = [(0, 1 + k, 1 + (k + 1) % 8) for k in range(8) if k % 2 == par]
        f_dn = [(0, 1 + (k + 1) % 8, 1 + k) for k in range(8) if k % 2 == par]
        mb.add(v, f_up + f_dn, _mat("sombrilla_rojo" if par == 0 else "sombrilla_crema"))
    mb.add(*_sphere(0.06, seg=5, rings=2, off=(x, y, 2.76)), _mat("hierro"))


def _maceta(mb, rng, x, y, r=0.22):
    mb.add(*_lathe([(r * 0.75, 0.0), (r, 0.42), (r * 1.15, 0.50)], seg=6, off=(x, y, 0.08)), _mat("terracota"))
    mb.add(*_sphere(r * 1.3, seg=6, rings=3, scale=(1.1, 1.1, 0.8), off=(x, y, 0.08 + 0.62), rng=rng, jit=0.15),
           _mat("parra"), smooth=True)
    for j, key in enumerate(("flor_rojo", "flor_rojo", "flor_rosa")):
        th = TAU * j / 3.0 + rng.uniform(0.0, 1.0)
        mb.add(*_sphere(r * 0.42, seg=5, rings=2, off=(x + math.cos(th) * r * 0.9, y + math.sin(th) * r * 0.8,
                                                        0.08 + 0.62 + r * 0.9)), _mat(key), smooth=True)


def build_pergola(parent_collection, largo=8.0, seed=0):
    """Terraza de trattoria: solado, pergola de madera a lo largo de X con
    parra, mesas con sombrilla, macetas y cartel TRATTORIA en el frente (+Y)."""
    rng = random.Random(7919 * seed + 97)
    root = _empty("%s_pergola" % PREFIX, parent_collection, size=2.0)
    L, W, Hp = float(largo), 3.2, 2.7
    MAD, MADC = _mat("madera"), _mat("madera_clara")
    mb = _MB()
    mb.add(*_box(L + 1.6, W + 2.4, 0.08, base=True), _mat("suelo_terraza"))
    npost = max(2, int(round(L / 2.7)) + 1)
    xs = [-L / 2.0 + i * L / (npost - 1.0) for i in range(npost)]
    for x in xs:
        for y in (-W / 2.0, W / 2.0):
            mb.add(*_box(0.18, 0.18, Hp, off=(x, y, 0.08), base=True), MAD)
            mb.add(*_box(0.30, 0.30, 0.10, off=(x, y, 0.08), base=True), _mat("sillar"))
    zv = 0.08 + Hp
    for y in (-W / 2.0, W / 2.0):
        mb.add(*_box(L + 0.6, 0.16, 0.22, off=(0.0, y, zv + 0.11)), MAD)
    nc = int(L / 0.55) + 1
    for i in range(nc):
        x = -L / 2.0 - 0.1 + i * (L + 0.2) / (nc - 1.0)
        mb.add(*_box(0.10, W + 1.2, 0.16, off=(x, 0.0, zv + 0.22 + 0.08)), MADC)
    ztop = zv + 0.22 + 0.16
    # cartel TRATTORIA colgado justo debajo de la viga frontal (y=W/2): las
    # varillas van del canto superior del cartel (zv-0.06) al vientre de la
    # viga (zv), sin flotar por delante
    yc = W / 2.0
    mb.add(*_box(2.1, 0.06, 0.52, off=(0.0, yc, zv - 0.32)), _mat("verde_cartel"))
    for dx in (-0.9, 0.9):
        mb.add(*_box(0.03, 0.03, 0.12, off=(dx, yc, zv - 0.07), base=True), _mat("hierro"))
    _texto_add(mb, _texto_datos("TRATTORIA", 0.30, res=2), (0.0, yc + 0.034, zv - 0.32), _mat("blanco"))
    # mesas y macetas
    nm = max(1, int(L / 3.6))
    for i in range(nm):
        _mesa_sombrilla(mb, rng, -L / 2.0 + (i + 0.5) * L / nm + rng.uniform(-0.3, 0.3), rng.uniform(-0.5, 0.3))
    _maceta(mb, rng, -L / 2.0 - 0.55, W / 2.0 + 0.7)
    _maceta(mb, rng, L / 2.0 + 0.55, W / 2.0 + 0.7)
    mb.build("%s_pergola_cuerpo" % PREFIX, parent_collection, parent=root)

    # parra: manto de hojas encima, cepas trepando por los postes, racimos
    mp = _MB()
    for _ in range(int(L * 3.4)):
        x = rng.uniform(-L / 2.0 - 0.2, L / 2.0 + 0.2)
        y = rng.uniform(-W / 2.0 - 0.5, W / 2.0 + 0.5)
        r = rng.uniform(0.32, 0.52)
        key = "parra" if rng.random() < 0.55 else "parra_clara"
        mp.add(*_sphere(r, seg=6, rings=3, scale=(1.3, 1.3, 0.45), off=(x, y, ztop + r * 0.12),
                        rng=rng, jit=0.25), _mat(key), smooth=True)
    for x in xs:
        for y in (-W / 2.0, W / 2.0):
            sy = 1.0 if y > 0 else -1.0
            mp.add(*_tube([(x + 0.12, y + sy * 0.12, 0.1), (x + 0.10, y + sy * 0.15, 1.4),
                           (x + 0.08, y + sy * 0.06, Hp)], [0.035, 0.03, 0.025], sides=4),
                   _mat("tronco"), smooth=True)
            for z in (1.5, 2.3):
                mp.add(*_sphere(rng.uniform(0.22, 0.30), seg=6, rings=3, scale=(1.0, 1.0, 0.7),
                                off=(x + 0.1, y + sy * 0.2, z), rng=rng, jit=0.25),
                       _mat("parra_clara" if z > 2 else "parra"), smooth=True)
    for _ in range(int(L * 0.8)):
        x = rng.uniform(-L / 2.0, L / 2.0)
        y = rng.uniform(-W / 2.0 + 0.2, W / 2.0 + 0.3)
        mp.add(*_sphere(0.12, seg=5, rings=3, scale=(0.8, 0.8, 1.5), off=(x, y, ztop - 0.36),
                        rng=rng, jit=0.2), _mat("uva"), smooth=True)
    mp.build("%s_pergola_parra" % PREFIX, parent_collection, parent=root)
    return root


# ---------------------------------------------------------------------------
# ESCAPARATE
# ---------------------------------------------------------------------------
def build(parent_collection, seed=0, **params):
    """Escaparate: dos bancales apilados (ladera), ermita y cipreses en la
    cima; fuente, pergola, capitella e hito abajo junto al camino (+Y)."""
    root = _empty("%s_escaparate" % PREFIX, parent_collection, size=3.0)

    def col(ob, x, y, z=0.0, rz=0.0):
        ob.parent = root
        ob.location = (x, y, z)
        ob.rotation_euler = (0.0, 0.0, rz)
        return ob

    col(build_bancal(parent_collection, largo=34.0, alto=1.6, seed=seed, fondo=9.0), 0.0, 0.0)
    col(build_bancal(parent_collection, largo=26.0, alto=1.6, seed=seed + 1, fondo=12.0,
                     sin_olivos=[(2.0, 13.0)]), -3.0, -8.6, 1.6)
    col(build_ermita(parent_collection, seed=seed), 5.0, -19.5, 3.2)
    col(build_fila_cipreses(parent_collection, largo=40.0, paso=6.0, seed=seed), 14.0, -31.0, 3.2)
    col(build_fuente(parent_collection, seed=seed), 9.0, 7.0)
    col(build_pergola(parent_collection, largo=8.0, seed=seed), 20.0, 4.0, 0.0, math.radians(-15.0))
    col(build_capitella(parent_collection, seed=seed), -13.0, 5.0)
    col(build_hito(parent_collection, texto="PORTO CORSA 2", seed=seed), -8.0, 8.0)
    return root
