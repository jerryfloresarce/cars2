"""camaras_kit.py - Vehiculos-camara de TV del World Grand Prix (Cars 2, Porto Corsa).

Kit procedural para Blender 5.1 (bpy puro + bmesh solo para recalcular
normales; sin bpy.ops, sin texturas). Son los coches y helicopteros que GRABAN
la carrera: se colocan en las curvas, detras de la barrera, mirando a la pista.

Cada pieza es UNA malla multi-material (el helicoptero: un Empty con 2 mallas
hijas, cuerpo + discos translucidos), en metros, con el origen en el centro
de la base del vehiculo/torre (z=0 = suelo), y con el FRONTAL del personaje y
su CAMARA mirando a +Y (hacia donde estara la pista). Todos los personajes
tienen OJOS en el parabrisas y BOCA sonriente en el parachoques (los faros no
son ojos). Camaras grandes y contrastadas (caja de optica blanca, parasol
negro, lente azul con aro cromado, piloto rojo 'tally') para leerse a 30-80 m.

API:
  build_furgoneta_tv(parent_collection, color=None, seed=0)
      Furgoneta de TV redondeada (~4.6 x 2.0 x 2.2 m de carroceria) con
      plataforma en el techo, camara broadcast sobre cabezal pan/tilt apuntando
      adelante-abajo, parabolica atras y librea de franjas 'WGP TV'.
      color=None -> blanco / azul / rojo por seed. Objeto CAMARA_furgoneta_tv.
  build_grua_camara(parent_collection, alto=7.0, seed=0, alcance=5.0)
      Camion-grua compacto (amarillo / naranja por seed) con brazo articulado
      que sube hasta `alto` m (altura de la camara) y llega `alcance` m hacia
      +Y por encima de la barrera; cabeza remota colgada mirando abajo a la
      pista; 4 patas estabilizadoras apoyadas. Objeto CAMARA_grua.
  build_torre_camara(parent_collection, alto=6.0, seed=0)
      Torre de andamio tubular (diagonales, tarima de tablones, barandilla,
      pancarta verde WGP al frente, montacargas trasero) con un mini
      coche-camara con ojos sobre la tarima (z=alto). Objeto CAMARA_torre.
  build_helicoptero_camara(parent_collection, seed=0)
      Helicoptero-personaje (~9 m) blanco con franjas roja/azul, barriga de
      color, patines, botalon de cola rotulado, rotor principal (2 palas +
      disco translucido), rotor de cola y bola giroestabilizada bajo el morro.
      Origen en el centro de la base de los patines (z=0 = apoyo): el
      integrador lo sube a la altura de vuelo que quiera. Devuelve el Empty
      CAMARA_helicoptero con hijas CAMARA_helicoptero_cuerpo y
      CAMARA_helicoptero_discos (discos de rotor con alpha, sin sombra).
  build(parent_collection, seed=0, **params)
      Muestrario: las cuatro piezas lado a lado, hijas del Empty CAMARA_kit
      (el helicoptero flotando a params.get('z_heli', 2.5) m).

Limites: furgoneta <= 4500 tris, grua <= 5000, torre <= 4500, heli <= 5000.
"""

import math
import random

import bpy
import bmesh
from mathutils import Matrix, Vector

PREFIX = "CAMARA"
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Paleta plana: color lineal, roughness, metallic [, emision, alfa]
# ---------------------------------------------------------------------------
_PALETA = {
    # cara / vehiculo
    "cristal":     ((0.015, 0.050, 0.130), 0.08, 0.0),
    "ojo":         ((0.940, 0.945, 0.950), 0.25, 0.0),
    "pupila":      ((0.006, 0.008, 0.014), 0.20, 0.0),
    "iris_azul":   ((0.030, 0.250, 0.750), 0.25, 0.0),
    "iris_marron": ((0.260, 0.110, 0.030), 0.25, 0.0),
    "iris_verde":  ((0.050, 0.420, 0.160), 0.25, 0.0),
    "boca":        ((0.060, 0.008, 0.010), 0.60, 0.0),
    "lengua":      ((0.800, 0.160, 0.170), 0.50, 0.0),
    "diente":      ((0.950, 0.940, 0.900), 0.30, 0.0),
    "goma":        ((0.030, 0.030, 0.034), 0.92, 0.0),
    "negro":       ((0.035, 0.035, 0.040), 0.60, 0.0),
    "llanta":      ((0.880, 0.860, 0.800), 0.40, 0.0),
    "cromo":       ((0.800, 0.810, 0.820), 0.22, 1.0),
    "faro":        ((1.000, 0.880, 0.560), 0.15, 0.0),
    "piloto":      ((0.800, 0.020, 0.020), 0.25, 0.0),
    "ambar":       ((1.000, 0.420, 0.020), 0.25, 0.0, 1.2),
    "placa":       ((0.930, 0.930, 0.900), 0.50, 0.0),
    # camara broadcast
    "cam_cuerpo":  ((0.050, 0.055, 0.065), 0.45, 0.0),
    "cam_optica":  ((0.880, 0.885, 0.890), 0.35, 0.0),
    "cam_parasol": ((0.010, 0.010, 0.012), 0.85, 0.0),
    "cam_lente":   ((0.030, 0.100, 0.420), 0.04, 0.0),
    "cam_pantalla": ((0.250, 0.650, 0.950), 0.30, 0.0, 1.5),
    "tally":       ((1.000, 0.030, 0.020), 0.30, 0.0, 2.0),
    # estructura
    "acero":       ((0.560, 0.580, 0.610), 0.38, 0.55),
    "acero_osc":   ((0.150, 0.160, 0.175), 0.50, 0.30),
    "chapa":       ((0.300, 0.310, 0.330), 0.60, 0.20),
    "madera":      ((0.560, 0.370, 0.170), 0.80, 0.0),
    "madera2":     ((0.440, 0.280, 0.120), 0.80, 0.0),
    "verde_wgp":   ((0.015, 0.400, 0.110), 0.50, 0.0),
    "blanco":      ((0.880, 0.880, 0.860), 0.35, 0.0),
    "amarillo":    ((0.980, 0.760, 0.040), 0.40, 0.0),
    "rojo":        ((0.800, 0.045, 0.035), 0.35, 0.0),
    "azul":        ((0.035, 0.200, 0.720), 0.35, 0.0),
    "plato":       ((0.900, 0.905, 0.910), 0.40, 0.0),
    "plato_tras":  ((0.620, 0.640, 0.660), 0.50, 0.0),
    "rotor":       ((0.050, 0.050, 0.058), 0.50, 0.0),
    "disco_rotor": ((0.300, 0.320, 0.350), 0.60, 0.0, 0.0, 0.17),
}

COLORES_FURGO = [
    ("blanco", (0.88, 0.88, 0.86), "azul", "rojo"),
    ("azul",   (0.035, 0.20, 0.72), "blanco", "amarillo"),
    ("rojo",   (0.80, 0.045, 0.035), "blanco", "amarillo"),
]
COLORES_GRUA = [("amarillo", (0.98, 0.72, 0.03)), ("naranja", (0.96, 0.36, 0.03))]
COLORES_MINI = [(0.95, 0.33, 0.03), (0.03, 0.55, 0.55), (0.95, 0.68, 0.04),
                (0.80, 0.05, 0.04), (0.35, 0.62, 0.90)]


def _mat_nuevo(name, color, rough, metal, emision=0.0, alfa=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    rgba = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emision > 0.0:
        ec = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if ec is not None:
            ec.default_value = rgba
        es = bsdf.inputs.get("Emission Strength")
        if es is not None:
            es.default_value = emision
    if alfa < 1.0:
        al = bsdf.inputs.get("Alpha")
        if al is not None:
            al.default_value = alfa
        try:
            m.surface_render_method = "BLENDED"
        except (AttributeError, TypeError):
            try:
                m.blend_method = "BLEND"
            except (AttributeError, TypeError):
                pass
        m.use_backface_culling = True
    m.diffuse_color = (color[0], color[1], color[2], alfa)
    return m


def _mat(key):
    """Material fijo MAT_CAMARA_<key> (reutilizado si existe)."""
    name = "MAT_%s_%s" % (PREFIX, key)
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    p = _PALETA[key]
    return _mat_nuevo(name, p[0], p[1], p[2],
                      p[3] if len(p) > 3 else 0.0, p[4] if len(p) > 4 else 1.0)


def _mat_color(clase, color, rough=0.30):
    """Material MAT_CAMARA_<clase>_<HEX> para un rgb dado (reutilizado)."""
    r, g, b = [max(0.0, min(1.0, c)) for c in color[:3]]
    name = "MAT_%s_%s_%02X%02X%02X" % (
        PREFIX, clase, round(r * 255), round(g * 255), round(b * 255))
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    return _mat_nuevo(name, (r, g, b), rough, 0.0)


def _mezcla(c, d, t):
    return tuple(a + (b - a) * t for a, b in zip(c, d))


def _luma(c):
    return 0.30 * c[0] + 0.55 * c[1] + 0.15 * c[2]


# ---------------------------------------------------------------------------
# Acumulador de malla multi-material con pila de transformaciones
# ---------------------------------------------------------------------------
class _MB:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.fmat = []
        self.fsm = []
        self.frec = []
        self._pila = [None]

    def push(self, M):
        top = self._pila[-1]
        self._pila.append(M if top is None else top @ M)

    def pop(self):
        self._pila.pop()

    def _mi(self, mat):
        for i, m in enumerate(self.mats):
            if m is mat:
                return i
        self.mats.append(mat)
        return len(self.mats) - 1

    def add(self, verts, faces, mat, smooth=False, recalc=False):
        """recalc=True: pieza cerrada cuyas normales recalcula bmesh."""
        M = self._pila[-1]
        if M is not None:
            verts = [tuple(M @ Vector(v)) for v in verts]
        base = len(self.verts)
        self.verts.extend(verts)
        if isinstance(mat, (list, tuple)):
            idxs = [self._mi(m) for m in mat]
        else:
            idxs = [self._mi(mat)] * len(faces)
        for f, mi in zip(faces, idxs):
            self.faces.append(tuple(i + base for i in f))
            self.fmat.append(mi)
            self.fsm.append(bool(smooth))
            self.frec.append(bool(recalc))

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def build(self, name, parent_collection):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        if any(self.frec):
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            fs = [bm.faces[i] for i, r in enumerate(self.frec) if r]
            bmesh.ops.recalc_face_normals(bm, faces=fs)
            bm.to_mesh(me)
            bm.free()
        for m in self.mats:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", self.fmat)
        me.polygons.foreach_set("use_smooth", self.fsm)
        me.validate()
        me.update()
        try:                       # aristas vivas > 50 grados (Blender >= 4.1)
            me.set_sharp_from_angle(angle=math.radians(50.0))
        except (AttributeError, TypeError):
            pass
        ob = bpy.data.objects.new(name, me)
        parent_collection.objects.link(ob)
        ob["camara_tris"] = self.tris()
        return ob


def _T(x, y, z):
    return Matrix.Translation(Vector((x, y, z)))


def _Rx(deg):
    return Matrix.Rotation(math.radians(deg), 4, "X")


def _Rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Z")


# ---------------------------------------------------------------------------
# Primitivas
# ---------------------------------------------------------------------------
_CARAS_CAJA = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
               (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]


def _box(sx, sy, sz, off=(0, 0, 0)):
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    ox, oy, oz = off
    verts = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
             (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    verts = [(a + ox, b + oy, c + oz) for (a, b, c) in verts]
    return verts, list(_CARAS_CAJA)


def _caja(mb, x0, x1, y0, y1, z0, z1, mat):
    """Caja por limites."""
    mb.add(*_box(x1 - x0, y1 - y0, z1 - z0,
                 off=(0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1))), mat)


def _tronco_y(mb, y0, w0, h0, zc0, y1, w1, h1, zc1, mat):
    """Tronco de piramide rectangular cerrado a lo largo de Y."""
    verts = []
    for (y, w, h, zc) in ((y0, w0, h0, zc0), (y1, w1, h1, zc1)):
        verts += [(-w / 2, y, zc - h / 2), (w / 2, y, zc - h / 2),
                  (w / 2, y, zc + h / 2), (-w / 2, y, zc + h / 2)]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
             (2, 6, 7, 3), (3, 7, 4, 0)]
    mb.add(verts, faces, mat, recalc=True)


def _marco(d, lateral=None):
    """Base ortonormal (u, v, d): u ~ lateral, v = d x u."""
    d = Vector(d).normalized()
    if lateral is None:
        lateral = (1.0, 0.0, 0.0) if abs(d.x) < 0.9 else (0.0, 1.0, 0.0)
    u = Vector(lateral)
    u = (u - d * u.dot(d))
    if u.length < 1e-6:
        u = d.orthogonal()
    u.normalize()
    v = d.cross(u).normalized()
    return u, v, d


def _viga(mb, p0, p1, ancho, canto, mat, ancho1=None, canto1=None, lateral=None):
    """Viga de seccion rectangular entre dos puntos (ancho sobre `lateral`)."""
    p0, p1 = Vector(p0), Vector(p1)
    u, v, _d = _marco(p1 - p0, lateral)
    a1 = ancho if ancho1 is None else ancho1
    c1 = canto if canto1 is None else canto1
    verts = []
    for (p, a, c) in ((p0, ancho, canto), (p1, a1, c1)):
        for (su, sv) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append(tuple(p + u * (su * a / 2.0) + v * (sv * c / 2.0)))
    mb.add(verts, list(_CARAS_CAJA), mat, recalc=True)


def _revolucion(mb, o, eje, perfil, mat, seg=12, smooth=True, fase=0.0,
                lateral=None):
    """Solido de revolucion alrededor de la recta o + t*eje. perfil = lista de
    (a, r) o (a, r, mat_i); mat_i pinta la banda que TERMINA en ese punto.
    Los puntos con r=0 son apices; los extremos con r>0 se tapan."""
    u, v, d = _marco(eje, lateral)
    o = Vector(o)
    verts, idx = [], []
    for p in perfil:
        a, r = p[0], p[1]
        if r <= 1e-6:
            idx.append([len(verts)])
            verts.append(tuple(o + d * a))
        else:
            ring = []
            for k in range(seg):
                th = fase + TAU * k / seg
                ring.append(len(verts))
                verts.append(tuple(o + d * a + u * (r * math.cos(th))
                                   + v * (r * math.sin(th))))
            idx.append(ring)
    faces, mats = [], []
    for i in range(len(perfil) - 1):
        A, B = idx[i], idx[i + 1]
        m = perfil[i + 1][2] if len(perfil[i + 1]) > 2 else mat
        if len(A) == 1 and len(B) == 1:
            continue
        for k in range(seg):
            k2 = (k + 1) % seg
            if len(A) == 1:
                faces.append((A[0], B[k2], B[k]))
            elif len(B) == 1:
                faces.append((A[k], A[k2], B[0]))
            else:
                faces.append((A[k], A[k2], B[k2], B[k]))
            mats.append(m)
    if len(idx[0]) > 1:
        faces.append(tuple(reversed(idx[0])))
        mats.append(perfil[1][2] if len(perfil[1]) > 2 else mat)
    if len(idx[-1]) > 1:
        faces.append(tuple(idx[-1]))
        mats.append(perfil[-1][2] if len(perfil[-1]) > 2 else mat)
    mb.add(verts, faces, mats, smooth=smooth, recalc=True)


def _tubo(mb, p0, p1, r0, mat, r1=None, seg=6, smooth=True):
    """Cilindro / cono truncado entre dos puntos."""
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    if L < 1e-6:
        return
    _revolucion(mb, p0, p1 - p0, [(0.0, r0), (L, r0 if r1 is None else r1)],
                mat, seg=seg, smooth=smooth)


def _esfera(mb, c, r, mat, seg=12, anillos=6, mat_sup=None):
    """Esfera de eje Z; mat_sup pinta el hemisferio superior."""
    perfil = []
    for i in range(anillos + 1):
        ph = -0.5 * math.pi + math.pi * i / anillos
        m = mat_sup if (mat_sup is not None and i > anillos // 2) else mat
        perfil.append((r * math.sin(ph), r * math.cos(ph) if 0 < i < anillos else 0.0, m))
    _revolucion(mb, c, (0.0, 0.0, 1.0), perfil, mat, seg=seg)


def _prisma_x(mb, pts_yz, x0, x1, mat):
    """Poligono convexo (y, z) extruido en X de x0 a x1 (cerrado)."""
    n = len(pts_yz)
    verts = [(x0, y, z) for (y, z) in pts_yz] + [(x1, y, z) for (y, z) in pts_yz]
    faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    faces.append(tuple(range(n)))
    faces.append(tuple(n + k for k in reversed(range(n))))
    mb.add(verts, faces, mat, recalc=True)


def _orientar(verts, faces, hint):
    """Da la vuelta a las caras cuya normal (Newell) no mira hacia `hint`."""
    out = []
    for f in faces:
        nx = ny = nz = 0.0
        for k in range(len(f)):
            a = verts[f[k]]
            b = verts[f[(k + 1) % len(f)]]
            nx += (a[1] - b[1]) * (a[2] + b[2])
            ny += (a[2] - b[2]) * (a[0] + b[0])
            nz += (a[0] - b[0]) * (a[1] + b[1])
        if nx * hint[0] + ny * hint[1] + nz * hint[2] < 0.0:
            f = tuple(reversed(f))
        out.append(tuple(f))
    return out


def _orientar_desde(verts, faces, p_int):
    """Orienta cada cara para que su normal se aleje del punto interior."""
    out = []
    for f in faces:
        nx = ny = nz = 0.0
        cx = cy = cz = 0.0
        for k in range(len(f)):
            a = verts[f[k]]
            b = verts[f[(k + 1) % len(f)]]
            nx += (a[1] - b[1]) * (a[2] + b[2])
            ny += (a[2] - b[2]) * (a[0] + b[0])
            nz += (a[0] - b[0]) * (a[1] + b[1])
            cx += a[0]
            cy += a[1]
            cz += a[2]
        n = float(len(f))
        d = ((cx / n - p_int[0]) * nx + (cy / n - p_int[1]) * ny
             + (cz / n - p_int[2]) * nz)
        if d < 0.0:
            f = tuple(reversed(f))
        out.append(tuple(f))
    return out


def _linspace(a, b, n):
    return [a + (b - a) * k / (n - 1) for k in range(n)]


# ---------------------------------------------------------------------------
# Rotulo de pixeles 5x7 ('WGP TV'): cada tramo horizontal es un quad
# ---------------------------------------------------------------------------
_FUENTE = {
    "W": ("1...1", "1...1", "1...1", "1.1.1", "1.1.1", "11.11", "1...1"),
    "G": (".111.", "1...1", "1....", "1.111", "1...1", "1...1", ".111."),
    "P": ("1111.", "1...1", "1...1", "1111.", "1....", "1....", "1...."),
    "T": ("11111", "..1..", "..1..", "..1..", "..1..", "..1..", "..1.."),
    "V": ("1...1", "1...1", "1...1", "1...1", "1...1", ".1.1.", "..1.."),
    " ": (".....",) * 7,
}


def _ancho_texto(texto):
    return 6 * len(texto) - 1


def _texto(mb, texto, fp, s0, t0, ps, pt, mat, hint):
    """Rotulo: fp(s, t) -> punto 3D; (s0, t0) esquina inferior izquierda de
    lectura; ps, pt = tamano del pixel en unidades de s y t."""
    verts, faces = [], []
    for ci, ch in enumerate(texto):
        g = _FUENTE.get(ch, _FUENTE[" "])
        for r, fila in enumerate(g):
            c = 0
            while c < 5:
                if fila[c] != "1":
                    c += 1
                    continue
                c1 = c
                while c1 < 5 and fila[c1] == "1":
                    c1 += 1
                sa, sb = s0 + (6 * ci + c) * ps, s0 + (6 * ci + c1) * ps
                ta, tb = t0 + (6 - r) * pt, t0 + (7 - r) * pt
                b = len(verts)
                verts += [fp(sa, ta), fp(sb, ta), fp(sb, tb), fp(sa, tb)]
                faces.append((b, b + 1, b + 2, b + 3))
                c = c1
    if faces:
        mb.add(verts, _orientar(verts, faces, hint), mat)


# ---------------------------------------------------------------------------
# Piezas de coche (mismo lenguaje formal que coches_kit_v2)
# ---------------------------------------------------------------------------
def _rueda(mb, cx, cy, cz, r, hw, sign, m_llanta=None, S=12):
    """Rueda de eje X por revolucion: neumatico + llanta hundida + tapacubos.
    Un vertice cae exactamente en el punto mas bajo (apoyo en z = cz - r)."""
    g, ll, cr = _mat("goma"), (m_llanta or _mat("llanta")), _mat("cromo")
    perfil = [(-hw, 0.55 * r, g), (-0.60 * hw, r, g), (0.60 * hw, r, g),
              (0.96 * hw, 0.90 * r, g), (hw, 0.68 * r, g),
              (0.72 * hw, 0.63 * r, ll), (0.66 * hw, 0.27 * r, ll),
              (1.02 * hw, 0.20 * r, cr)]
    verts = []
    for a, rr, _m in perfil:
        for k in range(S):
            th = -0.5 * math.pi + TAU * k / S
            verts.append((cx + sign * a, cy + rr * math.cos(th), cz + rr * math.sin(th)))
    n = len(perfil)
    c_in = len(verts)
    c_out = c_in + 1
    verts.append((cx - sign * hw, cy, cz))
    verts.append((cx + sign * 1.10 * hw, cy, cz))
    faces, mats = [], []
    for i in range(n - 1):
        for k in range(S):
            k2 = (k + 1) % S
            faces.append((i * S + k, i * S + k2, (i + 1) * S + k2, (i + 1) * S + k))
            mats.append(perfil[i + 1][2])
    for k in range(S):
        k2 = (k + 1) % S
        faces.append((c_in, k2, k))
        mats.append(g)
        faces.append((c_out, (n - 1) * S + k, (n - 1) * S + k2))
        mats.append(cr)
    mb.add(verts, faces, mats, smooth=True, recalc=True)


def _domo(mb, c, n, ru, rv, prof, m_aro, m_lente, seg=10):
    """Casquete elipsoidal (faro / lente) con eje horizontal n=(nx, ny)."""
    nx, ny = n
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    tx, ty = -ny, nx
    anillos = [(1.00, -0.05), (1.00, 0.30 * prof), (0.78, 0.72 * prof)]
    verts = []
    for rad, h in anillos:
        for k in range(seg):
            th = TAU * k / seg
            a, b = rad * ru * math.cos(th), rad * rv * math.sin(th)
            verts.append((c[0] + tx * a + nx * h, c[1] + ty * a + ny * h, c[2] + b))
    top = len(verts)
    verts.append((c[0] + nx * prof, c[1] + ny * prof, c[2]))
    faces, mats = [], []
    for i in range(2):
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((i * seg + k, i * seg + k2, (i + 1) * seg + k2, (i + 1) * seg + k))
            mats.append(m_aro if i == 0 else m_lente)
    for k in range(seg):
        faces.append((top, 2 * seg + k, 2 * seg + (k + 1) % seg))
        mats.append(m_lente)
    p_int = (c[0] - nx * 0.30, c[1] - ny * 0.30, c[2])
    faces = _orientar_desde(verts, faces, p_int)
    mb.add(verts, faces, mats, smooth=True)


def _barrido(mb, camino, seccion, mat, smooth=True):
    """Barre `seccion` [(d, dz)] por `camino` [((x, y, z), (nx, ny))]."""
    P = len(seccion)
    verts = []
    for (o, nrm) in camino:
        for (d, dz) in seccion:
            verts.append((o[0] + nrm[0] * d, o[1] + nrm[1] * d, o[2] + dz))
    faces = []
    for i in range(len(camino) - 1):
        for j in range(P):
            j2 = (j + 1) % P
            faces.append((i * P + j, i * P + j2, (i + 1) * P + j2, (i + 1) * P + j))
    faces.append(tuple(range(P)))
    last = (len(camino) - 1) * P
    faces.append(tuple(last + j for j in reversed(range(P))))
    mb.add(verts, faces, mat, smooth=smooth, recalc=True)


def _arco_extruido(mb, cy, cz, r0, r1_in, r1_out, x_in, x_out, a0, a1, mat, seg=8):
    """Aleta del paso de rueda: banda en arco (eje X), cerrada."""
    verts = []
    for k in range(seg + 1):
        th = a0 + (a1 - a0) * k / seg
        c, s = math.cos(th), math.sin(th)
        verts.append((x_in, cy + r0 * c, cz + r0 * s))
        verts.append((x_in, cy + r1_in * c, cz + r1_in * s))
        verts.append((x_out, cy + r1_out * c, cz + r1_out * s))
        verts.append((x_out, cy + r0 * c, cz + r0 * s))
    faces = []
    for i in range(seg):
        for j in range(4):
            j2 = (j + 1) % 4
            faces.append((i * 4 + j, i * 4 + j2, (i + 1) * 4 + j2, (i + 1) * 4 + j))
    faces.append((0, 1, 2, 3))
    faces.append(tuple(seg * 4 + j for j in (3, 2, 1, 0)))
    mb.add(verts, faces, mat, smooth=True, recalc=True)


def _paso_rueda(mb, cy, cz, r, z_corte, x_in, x_out, m_osc, m_cuerpo, seg=8):
    """Hueco del paso de rueda: medio disco extruido en X; exterior oscuro."""
    s0 = max(-1.0, min(1.0, (z_corte - cz) / r))
    a0 = math.asin(s0)
    a1 = math.pi - a0
    ring = []
    for k in range(seg + 1):
        th = a0 + (a1 - a0) * k / seg
        ring.append((cy + r * math.cos(th), cz + r * math.sin(th)))
    n = len(ring)
    verts = [(x_in, y, z) for (y, z) in ring] + [(x_out, y, z) for (y, z) in ring]
    faces, mats = [], []
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((k, k2, n + k2, n + k))
        mats.append(m_cuerpo)
    faces.append(tuple(range(n)))
    mats.append(m_cuerpo)
    faces.append(tuple(n + k for k in reversed(range(n))))
    mats.append(m_osc)
    mb.add(verts, faces, mats, smooth=False, recalc=True)


class _Planta:
    """Planta del morro / cola: superelipse |x/bw|^n + |Y/dy|^n = 1."""

    def __init__(self, y_tip, dy, bw, sentido=1, n=2.6):
        self.y_tip, self.dy, self.bw, self.s, self.n = y_tip, dy, bw, sentido, n

    def X(self, s):
        if s >= self.dy:
            return self.bw
        q = max(0.0, 1.0 - max(0.0, s) / self.dy)
        return self.bw * max(0.0, 1.0 - q ** self.n) ** (1.0 / self.n)

    def s_de_x(self, x):
        t = min(1.0, abs(x) / self.bw)
        return self.dy * (1.0 - max(0.0, 1.0 - t ** self.n) ** (1.0 / self.n))

    def y(self, x, off=0.0):
        return self.y_tip - self.s * (self.s_de_x(x) - off)

    def normal(self, x):
        t = min(0.999, abs(x) / self.bw)
        Y = max(1e-4, 1.0 - t ** self.n) ** (1.0 / self.n)
        gx = (t ** (self.n - 1.0)) / self.bw * (1.0 if x >= 0 else -1.0)
        gy = (Y ** (self.n - 1.0)) / self.dy * self.s
        ln = math.hypot(gx, gy) or 1.0
        return (gx / ln, gy / ln)


class _Sup:
    """Ray-cast axial por fuerza bruta contra la carroceria."""
    _OTROS = ((1, 2), (0, 2), (0, 1))

    def __init__(self):
        self.tris = []

    def add(self, verts, faces):
        for f in faces:
            for k in range(1, len(f) - 1):
                a, b, c = verts[f[0]], verts[f[k]], verts[f[k + 1]]
                self.tris.append((a, b, c,
                                  min(a[0], b[0], c[0]), max(a[0], b[0], c[0]),
                                  min(a[1], b[1], c[1]), max(a[1], b[1], c[1]),
                                  min(a[2], b[2], c[2]), max(a[2], b[2], c[2])))

    def hit(self, eje, p, q, signo):
        i, j = self._OTROS[eje]
        ilo, ihi, jlo, jhi = 3 + 2 * i, 4 + 2 * i, 3 + 2 * j, 4 + 2 * j
        best = None
        for t in self.tris:
            if p < t[ilo] or p > t[ihi] or q < t[jlo] or q > t[jhi]:
                continue
            a, b, c = t[0], t[1], t[2]
            d = (b[j] - c[j]) * (a[i] - c[i]) + (c[i] - b[i]) * (a[j] - c[j])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[j] - c[j]) * (p - c[i]) + (c[i] - b[i]) * (q - c[j])) / d
            l2 = ((c[j] - a[j]) * (p - c[i]) + (a[i] - c[i]) * (q - c[j])) / d
            l3 = 1.0 - l1 - l2
            if l1 < -1e-6 or l2 < -1e-6 or l3 < -1e-6:
                continue
            v = l1 * a[eje] + l2 * b[eje] + l3 * c[eje]
            if best is None or (v - best) * signo > 0.0:
                best = v
        return best


_QS = (0.04, 0.14, 0.34, 0.62)      # estaciones auto de morro/cola (s/dy)
_FX = (0.80, 0.97, 1.00, 1.00, 0.965, 0.86, 0.60, 0.30)


def _g(q, m=2.2):
    q = max(0.0, min(1.0, q))
    return (1.0 - (1.0 - q) ** m) ** (1.0 / m)


def _interp(tabla, y, k):
    if y <= tabla[0][0]:
        return tabla[0][k]
    if y >= tabla[-1][0]:
        return tabla[-1][k]
    for a, b in zip(tabla, tabla[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / ((b[0] - a[0]) or 1.0)
            return a[k] + (b[k] - a[k]) * t
    return tabla[-1][k]


def _estaciones(d):
    """Estaciones (y, semiancho, z_suelo, z_hombro, z_centro) de cola a morro
    + plantas (superelipses) del morro y de la cola."""
    nuc = [(y, zc, ze, d["bw"] * wf) for (y, zc, ze, wf) in d["nucleo"]]
    yR, yF, zg = d["yR"], d["yF"], d["zg"]
    est = []
    y0, zc0, ze0, w0 = nuc[0]
    dyR = y0 - yR
    plR = _Planta(yR, dyR, w0, -1, d.get("nR", 2.6))
    for q in _QS:
        g = _g(q)
        zc = d["zR"] + (zc0 - d["zR"]) * g
        est.append((yR + q * dyR, plR.X(q * dyR),
                    zg + d.get("dzR", 0.08) * (1.0 - g), zc - (zc0 - ze0), zc))
    for (y, zc, ze, w) in nuc:
        est.append((y, w, zg, ze, zc))
    yN, zcN, zeN, wN = nuc[-1]
    dyF = yF - yN
    plF = _Planta(yF, dyF, wN, 1, d.get("nF", 2.6))
    for q in reversed(_QS):
        g = _g(q)
        zc = d["zF"] + (zcN - d["zF"]) * g
        est.append((yF - q * dyF, plF.X(q * dyF),
                    zg + d.get("dzF", 0.08) * (1.0 - g), zc - (zcN - zeN), zc))
    return est, plF, plR


def _sec_cuerpo(y, w, zg, ze, zc, cuad=0.0, panza=0.0):
    """Seccion cerrada: bajos, flanco, hombro redondeado y capo abombado.
    17 puntos; con panza>0 (helicoptero) 22 puntos con barriga redonda."""
    h, dd = ze - zg, zc - ze
    fx = list(_FX)
    fx[4] += 0.020 * cuad
    fx[5] += 0.075 * cuad
    fx[6] += 0.080 * cuad
    zs = (zg, zg + 0.10 * h, zg + 0.40 * h, zg + 0.72 * h,
          zg + (0.93 + 0.03 * cuad) * h, ze + 0.30 * dd, ze + 0.75 * dd,
          ze + 0.95 * dd)
    der = [(f * w, z) for f, z in zip(fx, zs)]
    if panza > 0.0:
        der = [(0.34 * w, zg - 0.93 * panza), (0.62 * w, zg - 0.58 * panza)] + der
        pts = ([(0.0, zg - panza)] + der + [(0.0, zc)]
               + [(-x, z) for (x, z) in reversed(der)])
    else:
        pts = der + [(0.0, zc)] + [(-x, z) for (x, z) in reversed(der)]
    return [(x, y, z) for (x, z) in pts]


def _sec_cab(y, wb, wr, zb, zrail, cr, bow):
    """Seccion de cabina de 9 puntos; `bow` adelanta el centro en planta."""
    der = [(wb, zb, 0.0), (wr, zrail, 0.0),
           (0.88 * wr, zrail + 0.60 * cr, bow * (1.0 - 0.88 ** 2)),
           (0.50 * wr, zrail + 0.93 * cr, bow * 0.75)]
    pts = der + [(0.0, zrail + cr, bow)] + [(-x, z, b) for (x, z, b) in reversed(der)]
    return [(x, y + b, z) for (x, z, b) in pts]


def _loft(loops, c_ini, c_fin):
    """Loft cerrado: quads [i*P + j] + abanicos de tapa inicial y final."""
    P, n = len(loops[0]), len(loops)
    verts = [v for lp in loops for v in lp]
    faces = []
    for i in range(n - 1):
        a, b = i * P, (i + 1) * P
        for j in range(P):
            j2 = (j + 1) % P
            faces.append((a + j, a + j2, b + j2, b + j))
    ci = len(verts)
    verts.append(c_ini)
    cf = len(verts)
    verts.append(c_fin)
    last = (n - 1) * P
    for j in range(P):
        faces.append((ci, (j + 1) % P, j))
    for j in range(P):
        faces.append((cf, last + j, last + (j + 1) % P))
    return verts, faces


def _camino_parag(pl, z0, s_lim, kb=0.0, pasos=10):
    """Camino del parachoques por la planta `pl`, recortado a s <= s_lim."""
    if s_lim <= 0.02:
        return []
    e = 2.0 / pl.n
    if s_lim >= pl.dy:
        t_lim = 0.5 * math.pi
    else:
        t_lim = math.acos(max(0.0, min(1.0, ((pl.dy - s_lim) / pl.dy) ** (pl.n / 2.0))))
    out = []
    for k in range(pasos + 1):
        t = -t_lim + 2.0 * t_lim * k / pasos
        sx, cx = math.sin(t), max(0.0, math.cos(t))
        x = pl.bw * (1.0 if sx >= 0 else -1.0) * abs(sx) ** e
        Y = pl.dy * cx ** e
        out.append(((x, pl.y_tip - pl.s * (pl.dy - Y), z0 + kb * x * x),
                    pl.normal(x)))
    if s_lim > pl.dy + 0.03:
        s_ret = min(s_lim, pl.dy + 0.30)
        zr = z0 + kb * pl.bw * pl.bw
        out.insert(0, ((-pl.bw, pl.y_tip - pl.s * s_ret, zr), (-1.0, 0.0)))
        out.append(((pl.bw, pl.y_tip - pl.s * s_ret, zr), (1.0, 0.0)))
    return out


def _conformada(mb, fsurf, xs, zlo, zhi, off, mat, filas=1, hint=(0.0, 1.0, 0.0)):
    """Malla entre zlo(x) y zhi(x) pegada a la superficie y = fsurf(x, z)."""
    R = filas + 1
    verts = []
    for x in xs:
        a, b = zlo(x), zhi(x)
        o = off(x) if callable(off) else off
        for r in range(R):
            z = a + (b - a) * r / filas
            verts.append((x, fsurf(x, z) + o, z))
    faces = []
    for k in range(len(xs) - 1):
        for r in range(filas):
            i0 = k * R + r
            faces.append((i0, i0 + R, i0 + R + 1, i0 + 1))
    mb.add(verts, _orientar(verts, faces, hint), mat, smooth=True)


# ---------------------------------------------------------------------------
# CARA: ojos sobre el parabrisas + boca en el morro
# ---------------------------------------------------------------------------
_U_ANC = 0.50 / 0.88
_OFF_OJO, _OFF_IRIS, _OFF_PUP, _OFF_BRI, _OFF_PARP = 0.016, 0.025, 0.033, 0.041, 0.050


def _parabrisas_uv(arc_top, arc_bot):
    anclas = (-1.0, -_U_ANC, 0.0, _U_ANC, 1.0)

    def borde(arc, u):
        u = max(-1.0, min(1.0, u))
        for k in range(4):
            if u <= anclas[k + 1] or k == 3:
                t = (u - anclas[k]) / (anclas[k + 1] - anclas[k])
                a, b = arc[k], arc[k + 1]
                return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t,
                        a[2] + (b[2] - a[2]) * t)

    def surf(u, v):
        p0, p1 = borde(arc_bot, u), borde(arc_top, u)
        return (p0[0] + (p1[0] - p0[0]) * v, p0[1] + (p1[1] - p0[1]) * v,
                p0[2] + (p1[2] - p0[2]) * v)

    def punto(u, v, off):
        p = surf(u, v)
        e = 0.02
        pa, pb = surf(min(1.0, u + e), v), surf(max(-1.0, u - e), v)
        pc, pd = surf(u, v + e), surf(u, v - e)
        tu = (pa[0] - pb[0], pa[1] - pb[1], pa[2] - pb[2])
        tv = (pc[0] - pd[0], pc[1] - pd[1], pc[2] - pd[2])
        n = (tu[1] * tv[2] - tu[2] * tv[1], tu[2] * tv[0] - tu[0] * tv[2],
             tu[0] * tv[1] - tu[1] * tv[0])
        ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) or 1.0
        s = (1.0 if (0.6 * n[1] + 0.8 * n[2]) >= 0.0 else -1.0) / ln
        return (p[0] + n[0] * s * off, p[1] + n[1] * s * off, p[2] + n[2] * s * off)

    return surf, punto


def _fan_uv(mb, punto, centro, contorno, off, mat):
    verts = [punto(centro[0], centro[1], off)]
    verts += [punto(u, v, off) for (u, v) in contorno]
    n = len(contorno)
    faces = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    mb.add(verts, _orientar(verts, faces, (0.0, 0.6, 0.8)), mat, smooth=True)


def _elipse(uc, vc, ru, rv, n, th0=0.0, th1=TAU, cerrado=True, sx=1.0):
    m = n if cerrado else n + 1
    return [(uc + sx * ru * math.cos(th0 + (th1 - th0) * k / n),
             vc + rv * math.sin(th0 + (th1 - th0) * k / n)) for k in range(m)]


def _cara_ojos(mb, arc_top, arc_bot, mirada, expresion, m_parpado, iris_key):
    """Dos ojos grandes, SIEMPRE los dos y simetricos (nunca guino)."""
    surf, punto = _parabrisas_uv(arc_top, arc_bot)
    m_ojo, m_pup, m_iris = _mat("ojo"), _mat("pupila"), _mat(iris_key)
    UC, VC, RU, RV = 0.49, 0.54, 0.43, 0.40
    e = 0.05
    pa, pb = surf(UC + e, VC), surf(UC - e, VC)
    pc, pd = surf(UC, VC + e), surf(UC, VC - e)
    su = math.dist(pa, pb) / (2 * e)
    sv = math.dist(pc, pd) / (2 * e)
    r_m = min(RU * su, RV * sv)
    ri = 0.56 * r_m
    gx = mirada * 0.45 * max(0.0, RU - ri / su)
    gy = {"abierto": 0.02, "feliz": 0.06}[expresion] * RV
    for s in (-1, 1):
        uc = s * UC
        _fan_uv(mb, punto, (uc, VC), _elipse(uc, VC, RU, RV, 16), _OFF_OJO, m_ojo)
        ic = (uc + gx, VC + gy)
        _fan_uv(mb, punto, ic, _elipse(ic[0], ic[1], ri / su, ri / sv, 12),
                _OFF_IRIS, m_iris)
        rp = 0.50 * ri
        _fan_uv(mb, punto, ic, _elipse(ic[0], ic[1], rp / su, rp / sv, 8),
                _OFF_PUP, m_pup)
        bc = (ic[0] - 0.42 * ri / su, ic[1] + 0.42 * ri / sv)
        rb = 0.20 * ri
        _fan_uv(mb, punto, bc, _elipse(bc[0], bc[1], rb / su, rb / sv, 6),
                _OFF_BRI, m_ojo)
        k_sup, tilt = {"abierto": (0.62, -0.03), "feliz": (0.72, -0.05)}[expresion]
        a = math.asin(k_sup / 1.07)
        th0, th1 = a - tilt, math.pi - a - tilt
        cont = _elipse(uc, VC, 1.07 * RU, 1.07 * RV, 8, th0, th1, False, sx=s)
        cen = (0.5 * (cont[4][0] + 0.5 * (cont[0][0] + cont[-1][0])),
               0.5 * (cont[4][1] + 0.5 * (cont[0][1] + cont[-1][1])))
        _fan_uv(mb, punto, cen, cont, _OFF_PARP, m_parpado)
        if expresion == "feliz":
            kl, comba = 0.66, 0.20
            a = math.asin(kl / 1.07)
            cont = _elipse(uc, VC, 1.07 * RU, 1.07 * RV, 8,
                           math.pi + a, TAU - a, False, sx=s)
            p0, p1 = cont[-1], cont[0]
            for t in (0.2, 0.4, 0.6, 0.8):
                cont.append((p0[0] + (p1[0] - p0[0]) * t,
                             p0[1] + (p1[1] - p0[1]) * t
                             + comba * RV * (1.0 - (2.0 * t - 1.0) ** 2)))
            cen = (uc, VC - 0.84 * RV)
            _fan_uv(mb, punto, cen, cont, _OFF_PARP, m_parpado)


def _boca(mb, fsurf, offn, estilo, xh, z_hi, avail, m_labio):
    """Boca sonriente conformada al morro: 'sonrisa' | 'abierta' | 'dientes'."""
    a_up = (0.40 if estilo == "sonrisa" else 0.26) * avail
    h = {"sonrisa": 0.24, "abierta": 0.72, "dientes": 0.60}[estilo] * avail
    h = max(h, 0.045)

    def grosor(x):
        return h * max(0.0, 1.0 - (x / xh) ** 2)

    def zu(x):
        return z_hi - a_up * (1.0 - (x / xh) ** 2)

    def zl(x):
        return zu(x) - max(0.006, grosor(x))

    xs = _linspace(-xh, xh, 11)
    _conformada(mb, fsurf, xs, zl, zu, lambda x: offn(x, 0.012), _mat("boca"),
                filas=(1 if estilo == "sonrisa" else 2))
    xl = _linspace(-1.04 * xh, 1.04 * xh, 11)
    _conformada(mb, fsurf, xl,
                lambda x: zl(x) - (0.018 + 0.026 * max(0.0, 1.0 - (x / xh) ** 2)),
                lambda x: zl(x) + 0.004, lambda x: offn(x, 0.026), m_labio)
    if estilo in ("abierta", "dientes"):
        xd = _linspace(-0.80 * xh, 0.80 * xh, 7)
        kd = 0.30 if estilo == "abierta" else 0.46
        _conformada(mb, fsurf, xd, lambda x: zu(x) - kd * grosor(x),
                    lambda x: zu(x) - 0.003, lambda x: offn(x, 0.020), _mat("diente"))
    if estilo == "abierta":
        xt = _linspace(-0.55 * xh, 0.55 * xh, 7)
        _conformada(mb, fsurf, xt, lambda x: zl(x) + 0.003,
                    lambda x: zl(x) + 0.004 + 0.46 * grosor(x)
                    * max(0.0, 1.0 - (x / (0.55 * xh)) ** 2),
                    lambda x: offn(x, 0.020), _mat("lengua"))


# ---------------------------------------------------------------------------
# Vehiculo-personaje generico (carroceria + cabina + cara + ruedas)
# ---------------------------------------------------------------------------
def _vehiculo(mb, d, color, rng, expresion="abierto", boca="sonrisa",
              color_techo=None, seg_rueda=12, color_parpado=None, m_panza=None):
    """Construye en `mb` (coordenadas locales: centro en el origen, frontal a
    +Y, ruedas apoyadas en z=0) un personaje descrito por el dict `d` (mismo
    formato que coches_kit_v2). Devuelve un dict `info` con funciones para
    colocar el equipo: w_at, ze_at, zc_at, ztecho_at, flanco, lado, ..."""
    esc = d.get("esc", 1.0)
    color = tuple(max(0.0, min(1.0, c)) for c in color[:3])
    m_cuerpo = _mat_color("cuerpo", color, 0.30)
    m_techo = _mat_color("cuerpo", color_techo, 0.30) if color_techo else m_cuerpo
    if d.get("parag", "cromo") == "cromo":
        m_labio = _mat("cromo")
    else:
        m_labio = _mat_color("labio", _mezcla(color, (1.0, 1.0, 1.0), 0.55), 0.35)
    m_cristal, m_negro, m_cromo = _mat("cristal"), _mat("negro"), _mat("cromo")
    iris_key = rng.choice(("iris_azul", "iris_marron", "iris_verde", "iris_azul"))
    mirada = rng.choice((-1, 0, 0, 1))

    # ---- carroceria
    est, plF, plR = _estaciones(d)
    cuad, panza = d.get("cuadrado", 0.0), d.get("panza", 0.0)
    k0 = 3 if panza > 0.0 else 0
    loops = [_sec_cuerpo(y, w, zgl, ze, zc, cuad, panza) for (y, w, zgl, ze, zc) in est]
    yR, yF, zg = d["yR"], d["yF"], d["zg"]
    c_ini = (0.0, yR, 0.5 * (est[0][2] + est[0][4]))
    c_fin = (0.0, yF, 0.5 * (est[-1][2] + est[-1][4]))
    bverts, bfaces = _loft(loops, c_ini, c_fin)
    if m_panza is not None and panza > 0.0:       # barriga de otro color (helicoptero)
        P = len(loops[0])
        bajo = (0, 1, 2, P - 3, P - 2, P - 1)
        bmats = [m_panza if (j in bajo) else m_cuerpo
                 for _i in range(len(loops) - 1) for j in range(P)]
        bmats += [m_panza if (j in bajo) else m_cuerpo for j in range(P)] * 2
        mb.add(bverts, bfaces, bmats, smooth=True, recalc=True)
    else:
        mb.add(bverts, bfaces, m_cuerpo, smooth=True, recalc=True)
    sup = _Sup()
    sup.add(bverts, bfaces)
    est_ys = [e[0] for e in est]

    def w_at(y):
        return _interp(est, y, 1)

    def ze_at(y):
        return _interp(est, y, 3)

    def zc_at(y):
        return _interp(est, y, 4)

    def flanco(y, f):
        """Punto (x, y, z) del flanco derecho en el indice fraccionario f de
        la seccion (0 = bajos ... 4 = hombro), interpolado entre estaciones."""
        y = max(est_ys[0], min(est_ys[-1], y))
        i = 0
        for i in range(len(est) - 1):
            if est_ys[i] <= y <= est_ys[i + 1]:
                break
        t = (y - est_ys[i]) / ((est_ys[i + 1] - est_ys[i]) or 1.0)
        k = min(6, int(math.floor(f)))
        fr = f - k

        def P(lp):
            a, b = lp[k0 + k], lp[k0 + k + 1]
            return tuple(a[q] + (b[q] - a[q]) * fr for q in range(3))

        A, B = P(loops[i]), P(loops[i + 1])
        return tuple(A[q] + (B[q] - A[q]) * t for q in range(3))

    def fsurfF(x, z):
        for _k in range(12):
            v = sup.hit(1, x, z, 1)
            if v is not None:
                return v
            z -= 0.02
        return plF.y(x)

    def fsurfR(x, z):
        for _k in range(12):
            v = sup.hit(1, x, z, -1)
            if v is not None:
                return v
            z -= 0.02
        return plR.y(x)

    def offnF(x, off):
        return off / max(0.45, plF.normal(x)[1])

    # ---- cabina: luneta | techo (varios lazos) | parabrisas
    cab = d["cab"]
    y0, y1, y2, y3 = cab["y0"], cab["y1"], cab["y2"], cab["y3"]
    ym, half = 0.5 * (y1 + y2), 0.5 * (y2 - y1)
    hund = 0.06 * esc
    zroof, cr, wr = cab["zroof"], cab["cr"], cab["wr"]
    zrail = zroof - cr
    domo = cab.get("domo", 0.035)
    dr = min(0.24, 0.30 * (y2 - y1))

    def zrail_at(y):
        q = (y - ym) / half
        return zrail + domo * (0.6 - 1.6 * q * q)

    def wr_at(y):
        q = (y - ym) / half
        return wr + 0.012 - 0.022 * q * q

    def bow_at(y):
        q = (y - ym) / half
        return (cab["bowF"] if q > 0 else -cab["bowR"]) * 0.7 * abs(q) ** 1.5

    def wb_at(y):
        return min(cab["wb"], 0.93 * w_at(y))

    def colapsada(y, bow):
        wbc = wb_at(y)
        zb = ze_at(y) - hund
        return _sec_cab(y, wbc, wbc - 0.015, zb, zb + 0.02,
                        max(0.02, zc_at(y) - ze_at(y)), bow)

    ys_t = sorted(set([y1, y1 + dr, ym, y2 - dr, y2] + list(cab.get("extra", []))))
    cloops = [colapsada(y0, -cab["bowR"])]
    for y in ys_t:
        cloops.append(_sec_cab(y, wb_at(y), wr_at(y), ze_at(y) - hund,
                               zrail_at(y), cr, bow_at(y)))
    cloops.append(colapsada(y3, cab["bowF"]))
    cab_ys = [y0] + ys_t + [y3]
    NL = len(cloops)
    cverts, cfaces = _loft(cloops, (0.0, y0 - cab["bowR"], ze_at(y0) - hund + 0.02),
                           (0.0, y3 + cab["bowF"], ze_at(y3) - hund + 0.02))
    luna3, luneta, vent = cab.get("luna3", False), cab.get("luneta", True), cab.get("vent")

    def con_cristal(ya, yb):
        if vent is None:
            return True
        ymid = 0.5 * (ya + yb)
        return vent[0] <= ymid <= vent[1]

    cmats = []
    for i in range(NL - 1):
        for j in range(9):
            if j == 8:
                m = m_cuerpo
            elif i == NL - 2:
                m = m_cristal if (2 <= j <= 5 or j in (0, 7)) else m_techo
            elif i == 0:
                if luneta:
                    m = m_cristal if (2 <= j <= 5 or (luna3 and j in (0, 7))) else m_techo
                else:
                    m = m_techo
            else:
                m = (m_cristal if (j in (0, 7) and con_cristal(cab_ys[i], cab_ys[i + 1]))
                     else m_techo)
            cmats.append(m)
    cmats += [m_techo] * 18
    mb.add(cverts, cfaces, cmats, smooth=True, recalc=True)
    sup_cab = _Sup()
    sup_cab.add(cverts, cfaces)

    def lado(y, j):
        """Punto del lazo de cabina (indice j) interpolado en y (lado derecho)."""
        y = max(cab_ys[0], min(cab_ys[-1], y))
        for i in range(NL - 1):
            if cab_ys[i] <= y <= cab_ys[i + 1]:
                t = (y - cab_ys[i]) / ((cab_ys[i + 1] - cab_ys[i]) or 1.0)
                a, b = cloops[i][j], cloops[i + 1][j]
                return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
        return cloops[NL // 2][j]

    # pilares sobre el cristal lateral + pilar A
    pilares = list(d.get("pilares", []))
    if vent is None:
        pilares.append((y1 + 0.05, 0.10))
    for sg in (1, -1):
        for (yp, an) in pilares:
            ya, yb = max(y1, yp - an / 2), min(y2, yp + an / 2)
            q = [lado(ya, 0), lado(yb, 0), lado(yb, 1), lado(ya, 1)]
            q = [(sg * (p[0] + 0.008), p[1], p[2]) for p in q]
            mb.add(q, _orientar(q, [(0, 1, 2, 3)], (sg, 0.0, 0.0)), m_techo)
        A, B, E = cloops[NL - 1][1], cloops[NL - 2][1], cloops[NL - 2][0]
        la, lb = math.dist(A, E) or 1.0, math.dist(B, E) or 1.0
        D = tuple(A[k] + (E[k] - A[k]) * min(1.0, 0.17 * esc / la) for k in range(3))
        C = tuple(B[k] + (E[k] - B[k]) * min(1.0, 0.11 * esc / lb) for k in range(3))
        q = [(sg * (p[0] + 0.008), p[1], p[2]) for p in (A, D, C, B)]
        mb.add(q, _orientar(q, [(0, 1, 2, 3)], (sg, 0.0, 0.0)), m_techo)

    # ---- CARA: ojos en el parabrisas
    arc_top = [cloops[NL - 2][k] for k in (6, 5, 4, 3, 2)]
    arc_bot = [cloops[NL - 1][k] for k in (6, 5, 4, 3, 2)]
    m_parp = _mat_color("parpado", color_parpado, 0.30) if color_parpado else m_cuerpo
    _cara_ojos(mb, arc_top, arc_bot, mirada, expresion, m_parp, iris_key)

    # ---- pasos de rueda + ruedas
    rd = d.get("ruedas")
    ejes, r_arco = [], 0.0
    if rd:
        r, hw = rd["r"], rd["hw"]
        r_arco = 1.12 * r + 0.02
        z_corte = zg + 0.03
        a0 = max(-0.6, math.asin(max(-1.0, min(1.0, (z_corte - r) / r_arco))))
        ejes = list(rd["ejes"])
        for ye in ejes:
            wl = w_at(ye)
            for sg in (1, -1):
                _paso_rueda(mb, ye, r, r_arco, z_corte, sg * (wl - 0.05),
                            sg * (wl + 0.006), m_negro, m_cuerpo)
                _arco_extruido(mb, ye, r, r_arco, r_arco + 0.055 * esc,
                               r_arco + 0.035 * esc, sg * (wl - 0.07),
                               sg * (wl + 0.04 * esc), a0, math.pi - a0, m_cuerpo)
                _rueda(mb, sg * (wl - hw + 0.03), ye, r, r, hw, sg, S=seg_rueda)

    # ---- parachoques
    hb = (0.045 if d.get("parag", "cromo") == "cromo" else 0.055) * max(0.7, esc)
    e7 = max(0.7, esc)
    sec_pg = [(-0.12, -hb), (0.030 * e7, -hb), (0.058 * e7, -0.45 * hb),
              (0.058 * e7, 0.45 * hb), (0.030 * e7, hb), (-0.12, hb)]
    bwF = plF.bw
    kb = 0.05 / (bwF * bwF)
    if d.get("zbF") is not None:
        s_lim = (yF - (max(ejes) + r_arco + 0.07)) if ejes else plF.dy + 0.3
        cam = _camino_parag(plF, d["zbF"], s_lim, kb)
        if len(cam) >= 3:
            _barrido(mb, cam, sec_pg, m_labio)
        z_lo = d["zbF"] + hb + 0.025
    else:
        z_lo = est[-1][2] + 0.05
    if d.get("zbR") is not None:
        s_lim = ((min(ejes) - r_arco - 0.07) - yR) if ejes else plR.dy + 0.3
        cam = _camino_parag(plR, d["zbR"], s_lim, 0.0)
        if len(cam) >= 3:
            _barrido(mb, cam, sec_pg, m_labio)

    # ---- faros (NO son ojos) + intermitentes
    fa = d.get("faro")
    xh = 0.58 * bwF
    z_hi = d.get("boca_zhi", d["zF"] - 0.05)
    if fa:
        xf, zf = fa["x"] * bwF, d["zF"] + fa["dz"]
        for sg in (1, -1):
            x = sg * xf
            nrm = plF.normal(x)
            yv = fsurfF(x, zf)
            _domo(mb, (x - nrm[0] * 0.012, yv - nrm[1] * 0.012, zf), nrm,
                  fa["ru"], fa["rv"], fa["prof"], m_cromo, _mat("faro"), seg=8)
            if fa.get("ambar", True):
                zi = zf - fa["rv"] - 0.05 * esc
                xi = x + sg * 0.06 * esc
                nri = plF.normal(xi)
                _domo(mb, (xi, fsurfF(xi, zi) - 0.008, zi), nri, 0.042 * e7,
                      0.030 * e7, 0.025, _mat("ambar"), _mat("ambar"), seg=6)
        if zf - fa["rv"] < z_hi + 0.02:
            xh = min(xh, xf - fa["ru"] - 0.05 * esc)

    # ---- BOCA
    if d.get("boca_zlo") is not None:
        z_lo = d["boca_zlo"]
    avail = max(0.10 * esc, z_hi - z_lo)
    _boca(mb, fsurfF, offnF, boca, xh, z_hi, avail, m_labio)

    # ---- pilotos traseros + matricula
    pi_ = d.get("piloto")
    if pi_:
        bwR = plR.bw
        for sg in (1, -1):
            x = sg * pi_["x"] * bwR
            nrm = plR.normal(x)
            yv = fsurfR(x, pi_["z"])
            _domo(mb, (x - nrm[0] * 0.012, yv - nrm[1] * 0.012, pi_["z"]), nrm,
                  1.4 * pi_["ru"], 1.4 * pi_["rv"], 0.04, m_cromo, _mat("piloto"), seg=6)
        if d.get("zbR") is not None:
            zpl = d["zbR"] + 0.17 * e7
            ypl = fsurfR(0.0, zpl)
            mb.add(*_box(0.36 * e7, 0.03, 0.11 * e7, off=(0.0, ypl - 0.010, zpl)),
                   _mat("placa"))

    # ---- retrovisores, juntas de puerta y manillas
    if d.get("retro", True):
        y_ret = y3 - 0.24 * esc
        for sg in (1, -1):
            x_r = wb_at(y_ret) + 0.10 * e7
            z_r = ze_at(y_ret) + 0.13 * e7
            mb.add(*_box(0.13 * e7, 0.065 * e7, 0.095 * e7, off=(sg * x_r, y_ret, z_r)),
                   m_cuerpo)
            mb.add(*_box(0.12 * e7, 0.03, 0.03, off=(sg * (x_r - 0.09 * e7), y_ret, z_r - 0.03)),
                   m_cuerpo)
    pu = d.get("puerta")
    if pu:
        for sg in (1, -1):
            for yp in pu:
                verts = []
                for dy in (-0.007, 0.007):
                    for f in (1.0, 2.0, 3.0, 3.95):
                        p = flanco(yp + dy, f)
                        verts.append((sg * (p[0] + 0.004), p[1], p[2]))
                faces = [(k, k + 1, k + 5, k + 4) for k in range(3)]
                mb.add(verts, _orientar(verts, faces, (sg, 0.0, 0.0)), m_negro)
            p = flanco(pu[1] + 0.16 * e7, 3.4)
            mb.add(*_box(0.03, 0.12 * e7, 0.028, off=(sg * (p[0] + 0.008), p[1], p[2])),
                   m_cromo)

    return dict(est=est, est_ys=est_ys, loops=loops, k0=k0, cloops=cloops,
                cab_ys=cab_ys, w_at=w_at, ze_at=ze_at, zc_at=zc_at, flanco=flanco,
                lado=lado, ztecho_at=lambda y: zrail_at(y) + cr, wr_at=wr_at,
                y0=y0, y1=y1, y2=y2, y3=y3, dr=dr, sup=sup, sup_cab=sup_cab,
                plF=plF, plR=plR, m_cuerpo=m_cuerpo, m_techo=m_techo,
                fsurfF=fsurfF, fsurfR=fsurfR)


def _franja_flanco(mb, info, ya, yb, fa, fb, mat, off=0.009):
    """Franja pintada sobre los dos flancos de la carroceria, entre los
    indices fraccionarios de seccion fa..fb y las coordenadas ya..yb."""
    ys = [ya] + [y for y in info["est_ys"] if ya + 1e-4 < y < yb - 1e-4] + [yb]
    for sg in (1, -1):
        verts = []
        for y in ys:
            for f in (fa, fb):
                p = info["flanco"](y, f)
                verts.append((sg * (p[0] + off), p[1], p[2]))
        faces = [(2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1) for k in range(len(ys) - 1)]
        mb.add(verts, _orientar(verts, faces, (sg, 0.0, 0.0)), mat, smooth=True)


def _pt_lado(info, sg, y, t, off=0.010):
    """Punto sobre el lateral alto de la cabina (t=0 base, t=1 canto del techo)."""
    a, b = info["lado"](y, 0), info["lado"](y, 1)
    return (sg * (a[0] + (b[0] - a[0]) * t + off), a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def _franja_lado(mb, info, ya, yb, ta, tb, mat, off=0.010):
    """Franja pintada sobre los dos laterales altos de la cabina."""
    ys = [ya] + [y for y in info["cab_ys"] if ya + 1e-4 < y < yb - 1e-4] + [yb]
    for sg in (1, -1):
        verts = []
        for y in ys:
            verts.append(_pt_lado(info, sg, y, ta, off))
            verts.append(_pt_lado(info, sg, y, tb, off))
        faces = [(2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1) for k in range(len(ys) - 1)]
        mb.add(verts, _orientar(verts, faces, (sg, 0.0, 0.0)), mat)


# ---------------------------------------------------------------------------
# CAMARA BROADCAST (grande y contrastada) + pedestal + parabolica
# ---------------------------------------------------------------------------
def _camara(mb, escala=1.0, visor=True, asas=True, m_acento=None):
    """Camara de TV en coordenadas locales: eje de inclinacion en el origen,
    base de la cuna en z=0, eje optico a +Y. Longitud ~1.95*escala m.
    Caja de optica blanca + parasol negro abierto + lente azul con aro cromado
    + piloto rojo 'tally' + visor trasero con pantalla + asa + barras de paneo."""
    mc, mo, mp = _mat("cam_cuerpo"), _mat("cam_optica"), _mat("cam_parasol")
    ml, cr, mo2 = _mat("cam_lente"), _mat("cromo"), _mat("acero_osc")
    m_acento = m_acento or _mat("verde_wgp")
    mb.push(Matrix.Scale(escala, 4))
    _caja(mb, -0.16, 0.16, -0.45, 0.45, 0.00, 0.06, mo2)            # cuna
    _caja(mb, -0.19, 0.19, -0.62, 0.10, 0.06, 0.48, mc)             # cuerpo
    _caja(mb, -0.23, 0.23, 0.10, 0.78, 0.04, 0.52, mo)              # caja de optica
    for sg in (1, -1):                                               # franja de color
        _caja(mb, sg * 0.226, sg * 0.238, 0.16, 0.72, 0.33, 0.43, m_acento)
    # parasol abierto: exterior, labio, interior y fondo
    zc = 0.28
    anillos = [(0.78, 0.50, 0.50), (1.10, 0.76, 0.68), (1.10, 0.69, 0.61), (0.83, 0.43, 0.43)]
    verts = []
    for (y, w, h) in anillos:
        verts += [(-w / 2, y, zc - h / 2), (w / 2, y, zc - h / 2),
                  (w / 2, y, zc + h / 2), (-w / 2, y, zc + h / 2)]
    faces = []
    for i in range(3):
        for j in range(4):
            j2 = (j + 1) % 4
            faces.append((i * 4 + j, i * 4 + j2, (i + 1) * 4 + j2, (i + 1) * 4 + j))
    faces += [(0, 1, 2, 3), (12, 13, 14, 15)]
    mb.add(verts, faces, mp, recalc=True)
    _domo(mb, (0.0, 0.835, zc), (0.0, 1.0), 0.195, 0.195, 0.075, cr, ml, seg=12)
    _caja(mb, -0.10, 0.10, 0.50, 0.70, 0.52, 0.64, _mat("tally"))   # piloto rojo
    if visor:
        _caja(mb, -0.14, 0.14, -0.74, -0.30, 0.48, 0.68, mc)
        _tronco_y(mb, -0.74, 0.28, 0.20, 0.58, -0.90, 0.36, 0.27, 0.58, mp)
        q = [(-0.15, -0.903, 0.47), (0.15, -0.903, 0.47), (0.15, -0.903, 0.69),
             (-0.15, -0.903, 0.69)]
        mb.add(q, _orientar(q, [(0, 1, 2, 3)], (0.0, -1.0, 0.0)), _mat("cam_pantalla"))
    _caja(mb, -0.03, 0.03, -0.22, -0.16, 0.48, 0.76, mo2)           # asa superior
    _caja(mb, -0.03, 0.03, 0.40, 0.46, 0.52, 0.76, mo2)
    _caja(mb, -0.04, 0.04, -0.24, 0.48, 0.74, 0.81, mo2)
    if asas:
        for sg in (1, -1):
            a = Vector((sg * 0.20, -0.12, 0.03))
            b = Vector((sg * 0.36, -1.02, -0.20))
            m = a + (b - a) * 0.78
            _tubo(mb, a, m, 0.022, mo2, seg=5)
            _tubo(mb, m, b, 0.040, _mat("goma"), seg=5)
    mb.pop()


def _camara_en_pedestal(mb, base, h_pivote, tilt=10.0, yaw=0.0, escala=1.0,
                        m_acento=None, visor=True, asas=True):
    """Pedestal + cabezal pan/tilt + camara. `base` = apoyo del pedestal,
    h_pivote = altura del eje de inclinacion, tilt>0 = mira hacia abajo."""
    s = escala
    mo2, ac = _mat("acero_osc"), _mat("acero")
    _revolucion(mb, base, (0.0, 0.0, 1.0),
                [(0.0, 0.27 * s, mo2), (0.06 * s, 0.27 * s, mo2), (0.11 * s, 0.085 * s, mo2),
                 (h_pivote - 0.30 * s, 0.085 * s, ac), (h_pivote - 0.25 * s, 0.17 * s, mo2),
                 (h_pivote - 0.13 * s, 0.17 * s, mo2)], mo2, seg=8)
    mb.push(_T(base[0], base[1], base[2] + h_pivote) @ _Rz(yaw))
    _caja(mb, -0.17 * s, 0.17 * s, -0.20 * s, 0.20 * s, -0.14 * s, 0.0, mo2)
    mb.push(_Rx(-tilt))
    _camara(mb, escala, visor=visor, asas=asas, m_acento=m_acento)
    mb.pop()
    mb.pop()


def _parabolica(mb, base, h_mastil, R, elev=35.0, azim=180.0):
    """Antena parabolica: zocalo + mastil + plato (eje local +Y girado `azim`
    sobre Z y levantado `elev`) + alimentador sobre 3 varillas."""
    ac, mo2 = _mat("acero"), _mat("acero_osc")
    bx, by, bz = base
    _caja(mb, bx - 0.26, bx + 0.26, by - 0.26, by + 0.26, bz - 0.04, bz + 0.12, mo2)
    _tubo(mb, (bx, by, bz + 0.10), (bx, by, bz + h_mastil), 0.06, ac, seg=6)
    mb.push(_T(bx, by, bz + h_mastil) @ _Rz(azim) @ _Rx(elev))
    k = 0.34 / R                                   # a = k r^2 (profundidad 0.34 R)
    mp, mt = _mat("plato"), _mat("plato_tras")
    perfil = [(0.0, 0.0)]
    for q in (0.34, 0.68, 1.0):
        perfil.append((k * (q * R) ** 2, q * R, mp))
    perfil.append((k * R * R - 0.03, 1.02 * R, mo2))
    for q in (0.68, 0.34):
        perfil.append((k * (q * R) ** 2 - 0.06, q * R, mt))
    perfil.append((-0.10, 0.0, mt))
    _revolucion(mb, (0.0, 0.10, 0.0), (0.0, 1.0, 0.0), perfil, mp, seg=12)
    _caja(mb, -0.10, 0.10, -0.06, 0.10, -0.10, 0.10, mo2)           # rotula
    foco = Vector((0.0, 0.10 + 0.95 * R, 0.0))
    for a in (90.0, 210.0, 330.0):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        p = Vector((0.92 * R * ca, 0.10 + k * (0.92 * R) ** 2, 0.92 * R * sa))
        _tubo(mb, p, foco, 0.016, ac, seg=4)
    _tubo(mb, foco + Vector((0.0, -0.16, 0.0)), foco + Vector((0.0, 0.04, 0.0)),
          0.07, mo2, r1=0.05, seg=6)
    mb.pop()


# ---------------------------------------------------------------------------
# FURGONETA DE TV
# ---------------------------------------------------------------------------
_D_FURGO = dict(
    bw=0.97, zg=0.24, yR=-2.30, yF=2.30, nF=3.0, nR=3.4, cuadrado=0.7,
    nucleo=[(-1.92, 1.12, 1.06, 1.0), (0.0, 1.13, 1.07, 1.0), (1.84, 1.10, 1.04, 1.0)],
    zF=1.00, zR=1.04,
    cab=dict(y0=-2.22, y1=-2.02, y2=1.30, y3=2.02, wb=0.91, wr=0.80, zroof=2.20,
             cr=0.12, bowF=0.10, bowR=0.04, luna3=False, luneta=False,
             vent=(0.35, 9.0), extra=[0.35], domo=0.03),
    ruedas=dict(r=0.36, hw=0.11, ejes=(-1.35, 1.40)),
    faro=dict(x=0.64, dz=-0.18, ru=0.13, rv=0.13, prof=0.06),
    piloto=dict(x=0.80, z=0.86, ru=0.055, rv=0.11),
    parag="cromo", zbF=0.37, zbR=0.37, boca_zhi=0.78,
    pilares=[], puerta=(1.32, 0.35),
)


def build_furgoneta_tv(parent_collection, color=None, seed=0):
    """Furgoneta de TV 'WGP TV' con camara en el techo y parabolica. Malla
    unica CAMARA_furgoneta_tv, frontal y camara a +Y, ruedas en z=0."""
    rng = random.Random(7919 * int(seed) + 11)
    if color is None:
        _n, color, k1, k2 = COLORES_FURGO[int(seed) % len(COLORES_FURGO)]
    else:
        k1, k2 = (("azul", "rojo") if _luma(color) > 0.55 else ("blanco", "amarillo"))
    m1, m2 = _mat(k1), _mat(k2)
    mb = _MB()
    # carroceria clara: parpados tenidos con el color de la franja (que se lean)
    parp = _mezcla(color, _PALETA[k1][0], 0.45) if _luma(color) > 0.55 else None
    info = _vehiculo(mb, _D_FURGO, color, rng,
                     expresion=rng.choice(("abierto", "feliz")),
                     boca=rng.choice(("sonrisa", "abierta", "dientes")),
                     color_parpado=parp)
    # ---- librea: cinturon en el flanco + bandas y rotulo en el lateral alto
    _franja_flanco(mb, info, -2.06, 1.98, 3.12, 3.92, m1)
    ya, yb = info["y1"] + 0.06, 0.31
    _franja_lado(mb, info, ya, yb, 0.10, 0.25, m1)
    _franja_lado(mb, info, ya, yb, 0.28, 0.32, m2)
    a, b = info["lado"](-0.8, 0), info["lado"](-0.8, 1)
    H = math.dist(a, b)
    px = min(0.060, (yb - ya - 0.16) / _ancho_texto("WGP TV"))
    L = px * _ancho_texto("WGP TV")
    yc = 0.5 * (ya + yb)
    _texto(mb, "WGP TV", lambda s, t: _pt_lado(info, 1, yc - L / 2 + s, t, 0.012),
           0.0, 0.44, px, px / H, m1, (1.0, 0.0, 0.0))
    _texto(mb, "WGP TV", lambda s, t: _pt_lado(info, -1, yc + L / 2 - s, t, 0.012),
           0.0, 0.44, px, px / H, m1, (-1.0, 0.0, 0.0))

    # ---- plataforma de techo con barandilla
    ac, ch, mo2 = _mat("acero"), _mat("chapa"), _mat("acero_osc")
    zt = info["ztecho_at"](0.4)
    zd = zt + 0.26
    px0, px1, py0, py1 = -0.74, 0.74, -0.32, 1.12
    for sx in (-0.60, 0.60):
        for sy in (py0 + 0.12, py1 - 0.12):
            _caja(mb, sx - 0.04, sx + 0.04, sy - 0.04, sy + 0.04, zt - 0.10, zd - 0.05, ac)
    _caja(mb, px0, px1, py0, py1, zd - 0.06, zd, ch)
    zr = zd + 0.34
    for sx in (px0 + 0.03, px1 - 0.03):
        for sy in (py0 + 0.03, py1 - 0.03):
            _caja(mb, sx - 0.025, sx + 0.025, sy - 0.025, sy + 0.025, zd, zr, ac)
        _caja(mb, sx - 0.025, sx + 0.025, py0, py1, zr, zr + 0.05, ac)
    _caja(mb, px0, px1, py0, py0 + 0.05, zr, zr + 0.05, ac)

    # ---- camara broadcast mirando adelante-abajo
    _camara_en_pedestal(mb, (0.0, 0.42, zd), 0.66, tilt=rng.uniform(9.0, 13.0),
                        yaw=rng.uniform(-6.0, 6.0), escala=0.88, m_acento=m2)

    # ---- parabolica trasera, caja de equipos y antena de varilla
    zt2 = info["ztecho_at"](-1.4)
    _parabolica(mb, (0.0, -1.42, zt2 - 0.02), 0.62, 0.60,
                elev=rng.uniform(30.0, 42.0), azim=180.0 + rng.uniform(-35.0, 35.0))
    _caja(mb, -0.62, -0.10, -0.92, -0.46, zt - 0.06, zt + 0.20, _mat("blanco"))
    _caja(mb, -0.56, -0.16, -0.925, -0.90, zt + 0.02, zt + 0.14, mo2)
    _tubo(mb, (0.52, -0.66, zt - 0.04), (0.52, -0.66, zt + 1.25), 0.018, mo2, seg=4)
    _esfera(mb, (0.52, -0.66, zt + 1.28), 0.06, _mat("rojo"), seg=6, anillos=4)

    ob = mb.build("%s_furgoneta_tv" % PREFIX, parent_collection)
    ob["camara_pieza"] = "furgoneta_tv"
    return ob


# ---------------------------------------------------------------------------
# CAMION-GRUA CON CAMARA
# ---------------------------------------------------------------------------
_D_GRUA = dict(
    bw=1.00, zg=0.34, yR=-2.40, yF=2.40, nF=2.8, nR=4.0, cuadrado=0.6,
    nucleo=[(-2.08, 1.00, 0.97, 1.0), (0.20, 1.00, 0.97, 1.0),
            (1.10, 1.10, 1.02, 1.0), (1.78, 1.04, 0.96, 1.0)],
    zF=0.90, zR=0.94,
    cab=dict(y0=0.22, y1=0.40, y2=1.00, y3=1.66, wb=0.90, wr=0.74, zroof=1.95,
             cr=0.09, bowF=0.10, bowR=0.03, luna3=False),
    ruedas=dict(r=0.40, hw=0.13, ejes=(-1.42, 1.50)),
    faro=dict(x=0.66, dz=0.0, ru=0.13, rv=0.11, prof=0.06),
    piloto=dict(x=0.82, z=0.82, ru=0.05, rv=0.12),
    parag="cromo", zbF=0.44, zbR=0.44, boca_zhi=0.80,
    pilares=[], puerta=(1.02, 0.30),
)


def _cilindro_hidraulico(mb, p0, p1, r=0.075):
    p0, p1 = Vector(p0), Vector(p1)
    m = p0 + (p1 - p0) * 0.56
    _tubo(mb, p0, m, r, _mat("acero_osc"), seg=6)
    _tubo(mb, m, p1, 0.55 * r, _mat("cromo"), seg=6)


def build_grua_camara(parent_collection, alto=7.0, seed=0, alcance=5.0):
    """Camion-grua con brazo articulado y cabeza remota. `alto` = altura del
    centro de la camara; `alcance` = y de la camara (hacia la pista, +Y).
    Malla unica CAMARA_grua; ruedas y platos de las patas en z=0."""
    rng = random.Random(7919 * int(seed) + 23)
    alto = max(3.6, float(alto))
    alcance = max(2.8, float(alcance))
    _n, color = COLORES_GRUA[int(seed) % len(COLORES_GRUA)]
    mb = _MB()
    info = _vehiculo(mb, _D_GRUA, color, rng,
                     expresion=rng.choice(("abierto", "feliz")),
                     boca=rng.choice(("sonrisa", "dientes", "abierta")))
    m_c = info["m_cuerpo"]
    ac, ch, mo2, ng = _mat("acero"), _mat("chapa"), _mat("acero_osc"), _mat("negro")
    _franja_flanco(mb, info, -0.84, 0.92, 2.25, 3.05, ng)

    # ---- plataforma trasera, torreta, contrapeso y columna
    _caja(mb, -0.97, 0.97, -2.34, 0.16, 0.95, 1.07, ch)
    _caja(mb, -0.99, 0.99, -2.36, -2.30, 0.93, 1.09, ng)
    yT = -1.05
    _revolucion(mb, (0.0, yT, 1.07), (0.0, 0.0, 1.0), [(0.0, 0.56), (0.20, 0.56)],
                mo2, seg=10)
    _caja(mb, -0.44, 0.44, yT - 0.50, yT + 0.50, 1.27, 2.05, m_c)
    _caja(mb, -0.56, 0.56, yT - 1.02, yT - 0.50, 1.27, 1.90, mo2)
    _caja(mb, -0.445, 0.445, yT + 0.20, yT + 0.505, 1.55, 1.95, _mat("cristal"))
    A = Vector((0.0, yT, 2.78))
    _viga(mb, (0.0, yT, 2.0), A, 0.40, 0.40, m_c)
    _tubo(mb, A + Vector((-0.32, 0, 0)), A + Vector((0.32, 0, 0)), 0.21, mo2, seg=8)

    # ---- brazo articulado: A (columna) -> B (codo) -> C (punta)
    C = Vector((0.0, alcance, alto + 0.80))
    B = Vector((0.0, yT + 0.30 * (alcance - yT), max(alto + 1.50, A.z + 1.6)))
    lat = (1.0, 0.0, 0.0)
    a1a, c1a, a1b, c1b = 0.40, 0.50, 0.30, 0.36          # seccion del brazo 1
    a2a, c2a, a2b, c2b = 0.28, 0.34, 0.20, 0.22          # seccion del brazo 2
    _viga(mb, A, B, a1a, c1a, m_c, a1b, c1b, lateral=lat)
    _tubo(mb, B + Vector((-0.27, 0, 0)), B + Vector((0.27, 0, 0)), 0.20, mo2, seg=8)
    _viga(mb, B, C, a2a, c2a, m_c, a2b, c2b, lateral=lat)
    d2 = (C - B)
    for t in (0.72, 0.83, 0.94):                       # bandas negras en la punta
        _viga(mb, B + d2 * (t - 0.025), B + d2 * (t + 0.025),
              a2a + (a2b - a2a) * t + 0.03, c2a + (c2b - c2a) * t + 0.03, ng, lateral=lat)
    d1n = (B - A).normalized()
    n1 = Vector((0.0, -d1n.z, d1n.y))
    d2n = d2.normalized()
    n2 = Vector((0.0, -d2n.z, d2n.y))
    _cilindro_hidraulico(mb, (0.0, yT + 0.42, 2.12), A + (B - A) * 0.34 - n1 * 0.24, 0.085)
    _cilindro_hidraulico(mb, A + (B - A) * 0.70 - n1 * 0.20, B + d2 * 0.30 - n2 * 0.17, 0.07)
    # rotulo 'WGP TV' subiendo por los dos costados del brazo 1
    L1 = (B - A).length
    pxg = min(0.052, 0.45 * L1 / _ancho_texto("WGP TV"))
    s_ini = 0.36 * L1

    def _pt_brazo(sg, s, t):
        a = s_ini + s
        w = 0.5 * (a1a + (a1b - a1a) * a / L1) + 0.008
        p = A + d1n * a + n1 * (sg * (t - 3.5 * pxg))
        return (sg * w, p.y, p.z)

    for sg in (1, -1):
        _texto(mb, "WGP TV", lambda s, t, sg=sg: _pt_brazo(sg, s, t), 0.0, 0.0, pxg, pxg,
               ng, (float(sg), 0.0, 0.0))

    # ---- cabeza remota colgada de la punta, mirando abajo a la pista
    _tubo(mb, C + Vector((0, 0, 0.10)), C - Vector((0, 0, 0.30)), 0.055, mo2, seg=6)
    _caja(mb, -0.50, 0.50, C.y - 0.07, C.y + 0.07, C.z - 0.38, C.z - 0.26, mo2)
    zp = alto - 0.20
    for sg in (1, -1):
        _caja(mb, sg * 0.43, sg * 0.50, C.y - 0.08, C.y + 0.08, zp - 0.10, C.z - 0.30, mo2)
        _tubo(mb, (sg * 0.43, C.y, zp + 0.19), (sg * 0.18, C.y, zp + 0.19), 0.055, ac, seg=5)
    mb.push(_T(0.0, C.y, zp) @ _Rz(rng.uniform(-6.0, 6.0)) @ _Rx(-rng.uniform(30.0, 38.0)))
    _camara(mb, 0.92, visor=False, asas=False, m_acento=_mat("rojo"))
    mb.pop()

    # ---- patas estabilizadoras apoyadas en el suelo
    for ys in (-2.13, -0.32):
        _caja(mb, -1.66, 1.66, ys - 0.08, ys + 0.08, 0.52, 0.68, mo2)
        for sg in (1, -1):
            _caja(mb, sg * 1.58, sg * 1.78, ys - 0.10, ys + 0.10, 0.32, 0.80, m_c)
            _tubo(mb, (sg * 1.68, ys, 0.34), (sg * 1.68, ys, 0.04), 0.05, _mat("cromo"), seg=6)
            _caja(mb, sg * 1.44, sg * 1.92, ys - 0.24, ys + 0.24, 0.0, 0.05, mo2)

    # ---- rotativo ambar sobre la cabina
    zb = info["ztecho_at"](0.72)
    amb = _mat("ambar")
    _revolucion(mb, (0.0, 0.72, zb - 0.02), (0.0, 0.0, 1.0),
                [(0.0, 0.11, mo2), (0.05, 0.11, mo2), (0.06, 0.09, amb),
                 (0.15, 0.08, amb), (0.19, 0.0, amb)], mo2, seg=8)

    ob = mb.build("%s_grua" % PREFIX, parent_collection)
    ob["camara_pieza"] = "grua"
    ob["camara_alto"] = alto
    ob["camara_alcance"] = alcance
    return ob


# ---------------------------------------------------------------------------
# TORRE DE ANDAMIO CON MINI COCHE-CAMARA
# ---------------------------------------------------------------------------
_D_MINI = dict(
    esc=0.6, bw=0.52, zg=0.13, yR=-0.95, yF=0.95, nF=2.4, nR=2.6,
    nucleo=[(-0.62, 0.62, 0.56, 1.0), (-0.10, 0.66, 0.60, 1.0),
            (0.42, 0.64, 0.58, 1.0), (0.62, 0.59, 0.53, 0.98)],
    zF=0.48, zR=0.46,
    cab=dict(y0=-0.70, y1=-0.40, y2=0.10, y3=0.52, wb=0.46, wr=0.38, zroof=1.18,
             cr=0.08, bowF=0.08, bowR=0.05, luna3=False, domo=0.04),
    ruedas=dict(r=0.19, hw=0.07, ejes=(-0.50, 0.50)),
    faro=dict(x=0.62, dz=0.07, ru=0.070, rv=0.065, prof=0.05, ambar=False),
    piloto=dict(x=0.72, z=0.44, ru=0.04, rv=0.05),
    parag="labio", zbF=0.21, zbR=0.22, boca_zhi=0.44,
    pilares=[], puerta=None,
)


def build_torre_camara(parent_collection, alto=6.0, seed=0):
    """Torre de andamio con tarima a z=`alto`, pancarta WGP al frente (+Y) y un
    mini coche-camara con ojos operando una camara grande. Malla CAMARA_torre."""
    rng = random.Random(7919 * int(seed) + 37)
    alto = max(3.0, float(alto))
    mb = _MB()
    ac, mo2, ch = _mat("acero"), _mat("acero_osc"), _mat("chapa")
    verde, blanco, amar = _mat("verde_wgp"), _mat("blanco"), _mat("amarillo")
    hx, hy = 1.35, 1.55
    esquinas = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]

    # ---- patas (siguen como postes de barandilla) y placas base
    for (x, y) in esquinas:
        _tubo(mb, (x, y, 0.03), (x, y, alto + 1.06), 0.065, ac, seg=6)
        _caja(mb, x - 0.17, x + 0.17, y - 0.17, y + 0.17, 0.0, 0.04, mo2)
    # ---- largueros por nivel y diagonales alternas
    n = max(2, min(8, int(round(alto / 2.0))))          # <= 8 niveles: <= 4500 tris
    zs = [0.32 + k * (alto - 0.14 - 0.32) / n for k in range(n + 1)]
    for li, z in enumerate(zs):
        for k in range(4):
            (xa, ya), (xb, yb) = esquinas[k], esquinas[(k + 1) % 4]
            _tubo(mb, (xa, ya, z), (xb, yb, z), 0.045, ac, seg=5)
            if li < n:
                za, zb = (z, zs[li + 1]) if (li + k) % 2 == 0 else (zs[li + 1], z)
                _tubo(mb, (xa, ya, za), (xb, yb, zb), 0.038, ac, seg=5)

    # ---- tarima de tablones, rastreles y rodapie
    dx, dy = hx + 0.16, hy + 0.16
    npl = 9
    paso = 2.0 * dy / npl
    for k in range(npl):
        y0 = -dy + k * paso
        _caja(mb, -dx, dx, y0 + 0.006, y0 + paso - 0.006, alto - 0.07, alto,
              _mat("madera" if k % 2 == 0 else "madera2"))
    for sx in (-0.85, 0.85):
        _caja(mb, sx - 0.05, sx + 0.05, -dy + 0.05, dy - 0.05, alto - 0.17, alto - 0.07, mo2)
    for sg in (1, -1):
        _caja(mb, sg * (dx - 0.03), sg * dx, -dy, dy, alto, alto + 0.15, amar)
    _caja(mb, -dx, dx, -dy, -dy + 0.03, alto, alto + 0.15, amar)
    _caja(mb, -dx, dx, dy - 0.03, dy, alto, alto + 0.08, amar)
    # ---- barandilla: alta atras y a los lados, baja al frente (que se vea la cara)
    for k in range(4):
        (xa, ya), (xb, yb) = esquinas[k], esquinas[(k + 1) % 4]
        frente = (ya > 0 and yb > 0)
        if not frente:
            _tubo(mb, (xa, ya, alto + 1.0), (xb, yb, alto + 1.0), 0.04, ac, seg=5)
        zm = alto + (0.30 if frente else 0.52)
        _tubo(mb, (xa, ya, zm), (xb, yb, zm), 0.04, ac, seg=5)

    # ---- pancarta WGP al frente + bandas laterales
    zb0, zb1 = alto - 1.55, alto - 0.14
    yb_ = hy + 0.07
    _caja(mb, -hx - 0.12, hx + 0.12, yb_, yb_ + 0.02, zb0 - 0.06, zb1 + 0.06, blanco)
    _caja(mb, -hx - 0.06, hx + 0.06, yb_ + 0.02, yb_ + 0.045, zb0, zb1, verde)
    _caja(mb, -hx - 0.06, hx + 0.06, yb_ + 0.045, yb_ + 0.055, zb0 + 0.08, zb0 + 0.20, amar)
    px = 0.125
    L = px * _ancho_texto("WGP")
    zt0 = zb0 + 0.32
    _texto(mb, "WGP", lambda s, t: (L / 2 - s, yb_ + 0.058, zt0 + t), 0.0, 0.0, px, px,
           blanco, (0.0, 1.0, 0.0))
    for sg in (1, -1):
        xs_ = sg * (hx + 0.07)
        _caja(mb, min(xs_, xs_ + sg * 0.03), max(xs_, xs_ + sg * 0.03), -hy - 0.04,
              hy + 0.04, alto - 0.95, alto - 0.14, verde)
        _caja(mb, min(xs_ + sg * 0.03, xs_ + sg * 0.04), max(xs_ + sg * 0.03, xs_ + sg * 0.04),
              -hy - 0.04, hy + 0.04, alto - 0.87, alto - 0.77, amar)

    # ---- montacargas trasero (mundo de coches: sin escaleras)
    yl = -hy - 0.24
    for sx in (-0.80, 0.80):
        _caja(mb, sx - 0.05, sx + 0.05, yl - 0.05, yl + 0.05, 0.0, alto + 1.0, mo2)
    _caja(mb, -0.85, 0.85, yl - 0.05, yl + 0.05, alto + 0.92, alto + 1.0, mo2)
    _caja(mb, -0.92, 0.92, yl - 1.70, yl - 0.08, 0.10, 0.18, ch)
    for sx in (-0.90, 0.90):
        _caja(mb, sx - 0.025, sx + 0.025, yl - 1.68, yl - 0.10, 0.62, 0.68, amar)
        for yy in (yl - 1.66, yl - 0.12):
            _caja(mb, sx - 0.025, sx + 0.025, yy - 0.025, yy + 0.025, 0.18, 0.62, amar)

    # ---- mini coche-camara sobre la tarima
    color = COLORES_MINI[int(seed) % len(COLORES_MINI)]
    mb.push(_T(0.0, 0.10, alto) @ _Rz(rng.uniform(-6.0, 6.0)) @ Matrix.Scale(1.30, 4))   # atras: el morro pisaba la barandilla
    info = _vehiculo(mb, _D_MINI, color, rng, expresion=rng.choice(("abierto", "feliz")),
                     boca=rng.choice(("sonrisa", "abierta")), seg_rueda=10)
    zt = info["ztecho_at"](-0.15)
    _camara_en_pedestal(mb, (0.0, -0.15, zt - 0.03), 0.40, tilt=rng.uniform(10.0, 15.0),
                        yaw=0.0, escala=0.72, m_acento=verde)
    mb.pop()

    ob = mb.build("%s_torre" % PREFIX, parent_collection)
    ob["camara_pieza"] = "torre"
    ob["camara_alto"] = alto
    return ob


# ---------------------------------------------------------------------------
# HELICOPTERO-CAMARA
# ---------------------------------------------------------------------------
_D_HELI = dict(
    bw=0.92, zg=0.80, yR=-1.90, yF=2.30, nF=2.2, nR=2.2, cuadrado=0.2, panza=0.18,
    dzF=0.28, dzR=0.45,
    nucleo=[(-1.05, 1.66, 1.54, 0.90), (-0.20, 1.74, 1.60, 1.0),
            (0.85, 1.66, 1.54, 1.0), (1.45, 1.52, 1.40, 0.93)],
    zF=1.26, zR=1.50,
    cab=dict(y0=-1.45, y1=-0.95, y2=0.42, y3=1.40, wb=0.84, wr=0.62, zroof=2.50,
             cr=0.14, bowF=0.16, bowR=0.10, luna3=True, domo=0.05),
    ruedas=None, faro=None, piloto=None, parag="labio", zbF=None, zbR=None,
    boca_zhi=1.22, boca_zlo=0.96, pilares=[(-0.30, 0.10)], puerta=(0.55, -0.30),
    retro=False,
)


def _disco(mb, c, eje, r, mat, seg=28, grosor=0.02):
    """Disco translucido de dos caras (cada cara visible solo desde su lado)."""
    u, v, d = _marco(eje)
    c = Vector(c)
    for sg in (1, -1):
        o = c + d * (sg * grosor / 2.0)
        verts = [tuple(o)]
        for k in range(seg):
            th = TAU * k / seg
            verts.append(tuple(o + u * (r * math.cos(th)) + v * (r * math.sin(th))))
        faces = [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)]
        mb.add(verts, _orientar(verts, faces, tuple(d * sg)), mat)


def build_helicoptero_camara(parent_collection, seed=0):
    """Helicoptero-personaje de TV. Devuelve el Empty CAMARA_helicoptero con
    dos mallas hijas: CAMARA_helicoptero_cuerpo (todo lo opaco) y
    CAMARA_helicoptero_discos (discos translucidos de los rotores, aparte para
    poder quitarles la sombra / darles alpha al exportar). Origen en el centro
    de la base de los patines (z=0), morro y camara a +Y: para ponerlo en
    vuelo basta con mover / girar el Empty (duplicar SIEMPRE con sus hijos)."""
    rng = random.Random(7919 * int(seed) + 53)
    k1, k2 = (("rojo", "azul"), ("azul", "rojo"))[int(seed) % 2]
    m1, m2 = _mat(k1), _mat(k2)
    blanco_rgb = (0.88, 0.88, 0.86)
    mb = _MB()
    info = _vehiculo(mb, _D_HELI, blanco_rgb, rng,
                     expresion=rng.choice(("abierto", "feliz")),
                     boca=rng.choice(("sonrisa", "abierta")),
                     color_parpado=_mezcla(blanco_rgb, _PALETA[k2][0], 0.45),
                     m_panza=m2)
    m_c = info["m_cuerpo"]
    ac, mo2, mrot = _mat("acero"), _mat("acero_osc"), _mat("rotor")
    _franja_flanco(mb, info, -1.45, 1.90, 2.30, 2.96, m1)
    _franja_flanco(mb, info, -1.45, 1.90, 3.08, 3.92, m2)

    # ---- carenado del motor, botalon de cola con bandas, derivas y estabilizador
    _revolucion(mb, (0.0, 0.55, 2.46), (0.0, -1.0, 0.0),
                [(0.0, 0.0), (0.12, 0.22, mo2), (0.50, 0.40), (1.40, 0.44),
                 (2.10, 0.32), (2.62, 0.15)], m_c, seg=10, lateral=(1.0, 0.0, 0.0))
    p0, p1 = Vector((0.0, -1.00, 2.06)), Vector((0.0, -6.30, 2.36))
    Lb = (p1 - p0).length
    r0, r1 = 0.34, 0.11
    perfil = [(0.0, r0)]
    for (t, m) in ((0.60, m_c), (0.66, m1), (0.70, m_c), (0.76, m2), (1.0, m_c)):
        perfil.append((t * Lb, r0 + (r1 - r0) * t, m))
    _revolucion(mb, p0, p1 - p0, perfil, m_c, seg=10, lateral=(1.0, 0.0, 0.0))
    # rotulo 'WGP TV' conformado al botalon (se lee bien por los dos lados)
    dn = (p1 - p0).normalized()
    upb = Vector((0.0, dn.z, -dn.y))
    pxb = 0.0486
    Lt, Ht, a_ini = pxb * _ancho_texto("WGP TV"), 7.0 * pxb, 1.25

    def _pt_botalon(sg, a, t):
        r = r0 + (r1 - r0) * (a / Lb) + 0.010
        ang = (t - Ht / 2.0) / r
        c = p0 + dn * a
        return tuple(c + Vector((sg * r * math.cos(ang), 0.0, 0.0)) + upb * (r * math.sin(ang)))

    _texto(mb, "WGP TV", lambda s, t: _pt_botalon(1, a_ini + Lt - s, t), 0.0, 0.0,
           pxb, pxb, m2, (1.0, 0.0, 0.0))
    _texto(mb, "WGP TV", lambda s, t: _pt_botalon(-1, a_ini + s, t), 0.0, 0.0,
           pxb, pxb, m2, (-1.0, 0.0, 0.0))
    _prisma_x(mb, [(-5.75, 2.32), (-6.42, 2.26), (-6.88, 3.48), (-6.46, 3.48)],
              -0.04, 0.04, m1)
    _prisma_x(mb, [(-5.95, 2.34), (-6.36, 2.30), (-6.52, 1.72), (-6.32, 1.72)],
              -0.035, 0.035, m2)
    _caja(mb, -0.88, 0.88, -4.98, -4.58, 2.27, 2.32, m_c)
    for sg in (1, -1):
        _caja(mb, sg * 0.86, sg * 0.90, -5.04, -4.52, 2.10, 2.50, m2)

    # ---- rotor de cola (lado izquierdo) con disco translucido
    ct = Vector((-0.20, -6.44, 2.92))
    _tubo(mb, (0.0, ct.y, ct.z), (-0.27, ct.y, ct.z), 0.07, mo2, seg=6)
    a = math.radians(rng.uniform(20.0, 70.0))
    dv = Vector((0.0, math.cos(a), math.sin(a)))
    _viga(mb, ct - dv * 0.82, ct + dv * 0.82, 0.13, 0.03, mrot,
          lateral=(0.0, -math.sin(a), math.cos(a)))
    mbd = _MB()                      # discos translucidos -> objeto aparte (sin sombra)
    _disco(mbd, ct, (1.0, 0.0, 0.0), 0.86, _mat("disco_rotor"), seg=16, grosor=0.05)

    # ---- mastil, buje, dos palas y disco translucido del rotor principal
    ym, zr = -0.30, 3.30
    _tubo(mb, (0.0, ym, 2.75), (0.0, ym, zr + 0.02), 0.075, mo2, seg=6)
    _revolucion(mb, (0.0, ym, zr - 0.10), (0.0, 0.0, 1.0),
                [(0.0, 0.10), (0.04, 0.22), (0.16, 0.22), (0.22, 0.08)], ac, seg=8)
    b = math.radians(rng.uniform(15.0, 55.0))
    dh = Vector((math.cos(b), math.sin(b), 0.0))
    ch_ = Vector((0.0, ym, zr))
    for sg in (1, -1):
        _viga(mb, ch_ + dh * (sg * 0.15), ch_ + dh * (sg * 4.25), 0.30, 0.04, mrot,
              ancho1=0.24, lateral=(-math.sin(b), math.cos(b), 0.0))
    _disco(mbd, ch_ + Vector((0, 0, 0.05)), (0.0, 0.0, 1.0), 4.30, _mat("disco_rotor"),
           seg=28, grosor=0.02)

    # ---- patines (apoyo exacto en z=0) y montantes
    rs = 0.055
    for sg in (1, -1):
        _tubo(mb, (sg * 1.02, -1.60, rs), (sg * 1.02, 1.45, rs), rs, mo2, seg=8)
        _tubo(mb, (sg * 1.02, 1.45, rs), (sg * 1.02, 1.90, 0.32), rs, mo2, seg=8)
        for ys in (-0.90, 0.95):
            _tubo(mb, (sg * 1.02, ys, rs), (sg * 0.46, ys, 0.88), 0.045, mo2, seg=6)

    # ---- bola giroestabilizada bajo el morro, lente adelante-abajo
    cb = Vector((0.0, 1.76, 0.41))
    rb = 0.37
    for sg in (1, -1):
        _caja(mb, sg * 0.39, sg * 0.45, cb.y - 0.09, cb.y + 0.09, cb.z - 0.06, 0.82, ac)
        _tubo(mb, (sg * 0.39, cb.y, cb.z), (sg * 0.30, cb.y, cb.z), 0.07, ac, seg=6)
    _esfera(mb, cb, rb, _mat("cam_cuerpo"), seg=12, anillos=8, mat_sup=mo2)
    mb.push(_T(cb.x, cb.y, cb.z) @ _Rx(-rng.uniform(20.0, 30.0)))
    _domo(mb, (0.0, 0.315, -0.02), (0.0, 1.0), 0.20, 0.20, 0.08, _mat("cromo"),
          _mat("cam_lente"), seg=12)
    _domo(mb, (0.245, 0.245, 0.12), (0.0, 1.0), 0.05, 0.05, 0.035, _mat("tally"),
          _mat("tally"), seg=6)
    mb.pop()

    # ---- luz anticolision en el lomo
    _revolucion(mb, (0.0, -1.70, 2.80), (0.0, 0.0, 1.0),
                [(0.0, 0.07), (0.08, 0.06), (0.12, 0.0)], _mat("tally"), seg=6)

    root = bpy.data.objects.new("%s_helicoptero" % PREFIX, None)
    root.empty_display_size = 1.5
    parent_collection.objects.link(root)
    cuerpo = mb.build("%s_helicoptero_cuerpo" % PREFIX, parent_collection)
    discos = mbd.build("%s_helicoptero_discos" % PREFIX, parent_collection)
    for ob in (cuerpo, discos):
        ob.parent = root
    try:                              # los discos de rotor no proyectan sombra
        discos.visible_shadow = False
    except AttributeError:
        pass
    root["camara_pieza"] = "helicoptero"
    root["camara_tris"] = mb.tris() + mbd.tris()
    return root


# ---------------------------------------------------------------------------
# MUESTRARIO
# ---------------------------------------------------------------------------
def build(parent_collection, seed=0, **params):
    """Las cuatro piezas lado a lado (Empty CAMARA_kit con 4 hijos), todas
    mirando a +Y. El helicoptero flota a params['z_heli'] (2.5 m por defecto)."""
    root = bpy.data.objects.new("%s_kit" % PREFIX, None)
    root.empty_display_size = 2.0
    parent_collection.objects.link(root)
    piezas = [
        (build_furgoneta_tv(parent_collection, color=params.get("color"), seed=seed),
         (-10.5, 0.0, 0.0)),
        (build_grua_camara(parent_collection, alto=params.get("alto_grua", 7.0), seed=seed),
         (-4.5, 0.0, 0.0)),
        (build_torre_camara(parent_collection, alto=params.get("alto_torre", 6.0), seed=seed),
         (2.0, 0.0, 0.0)),
        (build_helicoptero_camara(parent_collection, seed=seed),
         (10.5, 0.0, params.get("z_heli", 2.5))),
    ]
    for ob, loc in piezas:
        ob.parent = root
        ob.location = loc
    return root
