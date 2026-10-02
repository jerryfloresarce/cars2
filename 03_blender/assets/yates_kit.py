"""yates_kit.py - Yates de lujo con publico VIP (Porto Corsa, Cars 2) para Blender 5.1.

En Porto Corsa los ricos ven la carrera desde sus yates amarrados junto a la
recta de meta. Este kit genera PROCEDURALMENTE (bpy puro + bmesh para
normales, sin bpy.ops, sin texturas de imagen) yates a motor, un megayate,
una lancha rapida, un pantalan VIP y coches de lujo con cara de Cars.

CONVENCIONES
  * metros; z=0 = NIVEL DEL MAR. Los cascos bajan como mucho 2.5 m bajo el
    agua (nunca por debajo de z=-2.6).
  * la PROA apunta a +X. El yate se amarra con la banda de ESTRIBOR (+Y)
    hacia la pista: todo el publico (coches) mira a +Y, hacia la carrera.
  * origen de cada barco en el centro de su flotacion (x=0 a media eslora,
    y=0 en crujia). La roda tiene 'rake': la regala de proa vuela hasta
    x = +L/2 + rake (yate 0.03 L, superyate 0.055 L, lancha 0.03 L).
  * cubiertas: amurada de 0.16 m de grosor; el semiancho util es
    cs.w_cub(t) (= cs.wi(t)) y la cubierta sigue el arrufo (cs.z_deck(t)),
    de modo que la amurada mide F - z_cub en toda la eslora.
  * coches-espectador de coches_kit_v2.py (mismo directorio; se importa por
    ruta): build_coche(parent, tipo, color, seed, expresion, boca). Tipos
    usados: sedan, deportivo, familiar, compacto, topolino. Colores
    elegantes: negro, blanco perla, burdeos, azul marino, dorado, plata.
  * materiales MAT_YATE_<clave> (Principled de color plano + nodos
    procedurales en la teca y el agua), reutilizados por nombre. Los coches
    de coches_kit_v2 usan sus MAT_COCHE_*; los coches de lujo propios
    (limusina, cabrio) usan MAT_YATE_coche_<HEX> para la carroceria y
    reutilizan los fijos MAT_COCHE_* (cristal, cromo, ojos, faros...).
  * cada barco es un Empty raiz con pocas mallas hijas (casco, cabina,
    detalles) + un coche por objeto (COCHE_*), todos hijos del raiz.

API
  build_yate(parent_collection, eslora=32.0, seed=0, con_publico=True,
             **params) -> Empty 'YATE_root'
      Yate a motor: casco blanco con franja azul marino en la flotacion,
      proa afilada, popa con plataforma de bano y escalera, superestructura
      de 2 pisos con cristaleras oscuras reflectantes, puente con radar y
      antenas, flybridge con sombrillas y tumbonas, barandillas de acero,
      bandera italiana en popa, defensas, pasarela con alfombra roja a
      estribor (hacia +Y, baja hasta z=0.9 = pantalan). Publico: 4-8 coches
      de lujo mirando a +Y, mesa alta con champan, mayordomo-coche.
      Hijos: YATE_casco, YATE_cabina, YATE_detalles (+ COCHE_*).
      params: n_coches (4..8), pasarela=True, bandera=True.
      <= 9k tris sin coches.
  build_superyate(parent_collection, eslora=70.0, seed=0, con_publico=True)
      -> Empty 'YATE_super': megayate de 3 pisos con roda lanzada,
      helipuerto elevado en proa con mini helicoptero, piscina en la
      cubierta superior y mas publico (9-12 coches + mayordomo). Hijos:
      YATE_super_casco, YATE_super_cabina, YATE_super_detalles,
      YATE_super_helicoptero. params: n_coches, pasarela. <= 16k tris sin
      coches.
  build_lancha(parent_collection, eslora=9.0, seed=0, n_coches=None)
      -> Empty 'YATE_lancha': lancha rapida estilo Riva (caoba, cockpit
      crema, consola con volante y parabrisas curvo por delante del morro
      del coche, tapa de motor a popa) con 1 coche (a veces 2 topolinos)
      mirando a +X. <= 2k tris.
  build_pantalan_vip(parent_collection, largo=60.0, seed=0, z_cubierta=0.9)
      -> Empty 'YATE_pantalan': pantalan flotante a lo largo de +X desde
      x=0 hasta x=largo, ancho 3.6 (y en [-1.8, 1.8]), ORIGEN EN EL EXTREMO
      x=0 a nivel del mar; la superficie de paseo queda a z=0.9 (los
      flotadores bajan a z=-0.55). Alfombra roja, farolillos emisivos,
      jardineras con limoneros, cordon de terciopelo con postes dorados y
      portal con cartel 'VIP' en x=0.
  build_coche_lujo(parent_collection, tipo='limusina'|'deportivo'|'cabrio',
                   seed=0, color=None) -> malla COCHE_lujo_<tipo>
      Misma convencion que coches_kit_v2: frontal +Y, ojos en el
      parabrisas, boca en el parachoques, ruedas apoyadas en z=0, origen en
      el centro de la base. 'deportivo' delega en coches_kit_v2 (renombrado);
      limusina y cabrio se modelan aqui (<= 1.5k tris).
  build_agua(parent_collection, lado=2500.0, nombre='YATE_agua') -> malla
      Plano de mar turquesa (rizado procedural) a z=-0.01, centrado en 0.
  build(parent_collection, seed=0, agua=True) -> Empty 'YATE_escaparate'
      Escaparate: pantalan VIP de 150 m en y=0, un superyate, dos yates y
      una lancha amarrados al sur (-Y) con estribor hacia el pantalan, coches
      de lujo en el pantalan y un plano de agua (YATE_agua) opcional.
"""

import importlib.util
import math
import os
import random
import sys

import bpy
import bmesh

PREFIX = "YATE"
TAU = 2.0 * math.pi
Z_MIN_CASCO = -2.5          # calado maximo (el test exige >= -2.6)

# ---------------------------------------------------------------------------
# Paleta MAT_YATE_<clave>: (color lineal, roughness, metallic[, emision])
# ---------------------------------------------------------------------------
_PALETA = {
    "casco":        ((0.930, 0.940, 0.930), 0.22, 0.0),
    "franja":       ((0.020, 0.050, 0.180), 0.30, 0.0),
    "obra_viva":    ((0.040, 0.050, 0.090), 0.50, 0.0),
    "cubierta":     ((0.640, 0.420, 0.190), 0.65, 0.0),
    "cristal":      ((0.020, 0.050, 0.100), 0.04, 0.50),
    "cristal_claro": ((0.500, 0.700, 0.800), 0.04, 0.30),     # parabrisas: alpha 0.4
    "acero":        ((0.800, 0.820, 0.840), 0.18, 1.0),
    "blanco":       ((0.940, 0.930, 0.900), 0.40, 0.0),
    "crema":        ((0.960, 0.920, 0.800), 0.60, 0.0),
    "azul":         ((0.060, 0.200, 0.550), 0.45, 0.0),
    "alfombra":     ((0.620, 0.020, 0.040), 0.90, 0.0),
    "dorado":       ((0.900, 0.680, 0.180), 0.25, 1.0),
    "verde_bandera": ((0.000, 0.550, 0.250), 0.60, 0.0),
    "rojo_bandera": ((0.800, 0.080, 0.100), 0.60, 0.0),
    "defensa":      ((0.050, 0.100, 0.300), 0.55, 0.0),
    "madera":       ((0.350, 0.200, 0.100), 0.70, 0.0),
    "terracota":    ((0.750, 0.380, 0.220), 0.80, 0.0),
    "hoja":         ((0.150, 0.450, 0.150), 0.80, 0.0),
    "limon":        ((0.980, 0.850, 0.150), 0.40, 0.0),
    "farol":        ((1.000, 0.850, 0.500), 0.30, 0.0, (1.0, 0.75, 0.40, 1.2)),
    "negro":        ((0.020, 0.020, 0.025), 0.50, 0.0),
    "gris":         ((0.550, 0.560, 0.580), 0.50, 0.0),
    "helipuerto":   ((0.200, 0.210, 0.220), 0.90, 0.0),
    "agua_piscina": ((0.100, 0.650, 0.750), 0.08, 0.0),
    "agua":         ((0.020, 0.400, 0.500), 0.22, 0.0),
    "champan":      ((0.950, 0.800, 0.400), 0.20, 0.0),
    "cordon":       ((0.450, 0.020, 0.100), 0.90, 0.0),
    "burdeos":      ((0.400, 0.020, 0.060), 0.28, 0.0),
    "letras":       ((0.950, 0.780, 0.250), 0.25, 1.0),
    "caoba":        ((0.420, 0.160, 0.060), 0.15, 0.0),
    "cinta":        ((0.900, 0.700, 0.200), 0.35, 0.15),
    "interior":     ((0.060, 0.050, 0.045), 0.80, 0.0),
    "cuero":        ((0.720, 0.560, 0.380), 0.65, 0.0),
}

# colores elegantes para el publico VIP (nombre, rgb lineal)
COLORES_LUJO = [
    ("negro",        (0.020, 0.020, 0.025)),
    ("blanco_perla", (0.920, 0.900, 0.850)),
    ("burdeos",      (0.400, 0.020, 0.060)),
    ("azul_marino",  (0.030, 0.060, 0.220)),
    ("dorado",       (0.850, 0.620, 0.120)),
    ("plata",        (0.700, 0.720, 0.750)),
]
TIPOS_LUJO = ("limusina", "deportivo", "cabrio")


def _mat_nuevo(name, color, rough, metal, emit=None):
    m = bpy.data.materials.new(name)
    if getattr(m, "node_tree", None) is None:      # Blender 5.1: use_nodes deprecado
        m.use_nodes = True
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (emit[0], emit[1], emit[2], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit[3]
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


def _nodos_teca(m):
    """Tablas de teca: onda procedural a lo largo de X mezclando dos tonos."""
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    onda = nt.nodes.new("ShaderNodeTexWave")
    onda.wave_type = "BANDS"
    onda.bands_direction = "Y"
    onda.inputs["Scale"].default_value = 3.0
    onda.inputs["Distortion"].default_value = 0.8
    onda.inputs["Detail"].default_value = 1.0
    mezcla = nt.nodes.new("ShaderNodeMix")
    mezcla.data_type = "RGBA"
    mezcla.inputs["A"].default_value = (0.640, 0.420, 0.190, 1.0)
    mezcla.inputs["B"].default_value = (0.520, 0.330, 0.140, 1.0)
    nt.links.new(coord.outputs["Object"], onda.inputs["Vector"])
    nt.links.new(onda.outputs["Fac"], mezcla.inputs["Factor"])
    nt.links.new(mezcla.outputs["Result"], bsdf.inputs["Base Color"])


def _nodos_agua(m):
    """Rizado suave del mar: ruido -> bump."""
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 0.35
    ruido.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    nt.links.new(ruido.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def _nodos_cristal_claro(m, alpha=0.40):
    """Cristal semitransparente (parabrisas de la lancha): alpha en el
    Principled + render 'BLENDED' de EEVEE (si la version lo expone)."""
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Alpha"].default_value = alpha
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND"),
                      ("use_backface_culling", False)):
        try:
            setattr(m, attr, val)
        except (AttributeError, TypeError):
            pass


def _mat(key):
    """Material fijo MAT_YATE_<key> (reutilizado si ya existe)."""
    name = "MAT_%s_%s" % (PREFIX, key)
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    spec = _PALETA[key]
    m = _mat_nuevo(name, spec[0], spec[1], spec[2], spec[3] if len(spec) > 3 else None)
    if key == "cubierta":
        _nodos_teca(m)
    elif key == "agua":
        _nodos_agua(m)
    elif key == "cristal_claro":
        _nodos_cristal_claro(m)
    return m


def _mat_color(color, rough=0.25):
    """Carroceria de coche de lujo MAT_YATE_coche_<HEX> (reutilizado)."""
    r, g, b = [max(0.0, min(1.0, c)) for c in color[:3]]
    name = "MAT_%s_coche_%02X%02X%02X" % (PREFIX, round(r * 255), round(g * 255), round(b * 255))
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    return _mat_nuevo(name, (r, g, b), rough, 0.0)


# ---------------------------------------------------------------------------
# Acumulador de malla multi-material
# ---------------------------------------------------------------------------
class _MB:
    def __init__(self):
        self.verts, self.faces, self.mats = [], [], []
        self.fmat, self.fsm, self.frec = [], [], []

    def _mi(self, mat):
        for i, m in enumerate(self.mats):
            if m is mat:
                return i
        self.mats.append(mat)
        return len(self.mats) - 1

    def add(self, verts, faces, mat, smooth=False, recalc=False):
        """mat: material o lista (uno por cara). recalc=True: pieza cerrada
        cuyas normales recalcula bmesh (hacia fuera)."""
        base = len(self.verts)
        self.verts.extend(tuple(v) for v in verts)
        idxs = ([self._mi(m) for m in mat] if isinstance(mat, (list, tuple))
                else [self._mi(mat)] * len(faces))
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
            fs = [bm.faces[i] for i, r in enumerate(self.frec) if r and i < len(bm.faces)]
            bmesh.ops.recalc_face_normals(bm, faces=fs)
            bm.to_mesh(me)
            bm.free()
        for m in self.mats:
            me.materials.append(m)
        if len(me.polygons) == len(self.fmat):
            me.polygons.foreach_set("material_index", self.fmat)
            me.polygons.foreach_set("use_smooth", self.fsm)
        me.validate()
        me.update()
        try:
            me.set_sharp_from_angle(angle=math.radians(48.0))
        except (AttributeError, TypeError):
            pass
        ob = bpy.data.objects.new(name, me)
        parent_collection.objects.link(ob)
        return ob


def _empty(name, parent_collection, size=2.0):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    parent_collection.objects.link(e)
    return e


# ---------------------------------------------------------------------------
# Primitivas (todas cerradas -> recalc de normales, salvo laminas)
# ---------------------------------------------------------------------------
def _rot(p, rz=0.0, ry=0.0, rx=0.0):
    x, y, z = p
    if rx:
        c, s = math.cos(rx), math.sin(rx)
        y, z = y * c - z * s, y * s + z * c
    if ry:
        c, s = math.cos(ry), math.sin(ry)
        x, z = x * c + z * s, -x * s + z * c
    if rz:
        c, s = math.cos(rz), math.sin(rz)
        x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


def _caja(mb, c, s, mat, rz=0.0, ry=0.0, rx=0.0, smooth=False):
    """Caja de CENTRO c y tamano s, rotada (rx, luego ry, luego rz)."""
    hx, hy, hz = s[0] / 2.0, s[1] / 2.0, s[2] / 2.0
    base = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    verts = []
    for p in base:
        q = _rot(p, rz, ry, rx) if (rz or ry or rx) else p
        verts.append((q[0] + c[0], q[1] + c[1], q[2] + c[2]))
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]
    mb.add(verts, faces, mat, smooth=smooth, recalc=True)


def _caja_base(mb, cx, cy, z0, sx, sy, sz, mat, rz=0.0):
    """Caja con la base centrada en (cx, cy) apoyada en z0."""
    _caja(mb, (cx, cy, z0 + sz / 2.0), (sx, sy, sz), mat, rz=rz)


def _base_ortonormal(p0, p1):
    dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    a = (dx / ln, dy / ln, dz / ln)
    ref = (0.0, 0.0, 1.0) if abs(a[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = (a[1] * ref[2] - a[2] * ref[1], a[2] * ref[0] - a[0] * ref[2], a[0] * ref[1] - a[1] * ref[0])
    lu = math.sqrt(sum(k * k for k in u)) or 1.0
    u = (u[0] / lu, u[1] / lu, u[2] / lu)
    v = (a[1] * u[2] - a[2] * u[1], a[2] * u[0] - a[0] * u[2], a[0] * u[1] - a[1] * u[0])
    return a, u, v, ln


def _cil(mb, p0, p1, r0, r1, mat, seg=8, tapas=True, smooth=True):
    """Cilindro/cono truncado entre p0 y p1 (radios r0 y r1)."""
    a, u, v, ln = _base_ortonormal(p0, p1)
    verts = []
    for p, r in ((p0, r0), (p1, r1)):
        for k in range(seg):
            th = TAU * k / seg
            cu, sv = r * math.cos(th), r * math.sin(th)
            verts.append((p[0] + u[0] * cu + v[0] * sv, p[1] + u[1] * cu + v[1] * sv,
                          p[2] + u[2] * cu + v[2] * sv))
    faces = []
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((k, k2, seg + k2, seg + k))
    if tapas:
        faces.append(tuple(reversed(range(seg))))
        faces.append(tuple(seg + k for k in range(seg)))
    mb.add(verts, faces, mat, smooth=smooth, recalc=True)


def _elipsoide(mb, c, rx, ry, rz, mat, seg=10, anillos=5, smooth=True):
    """Elipsoide UV (polos en +-z)."""
    verts = [(c[0], c[1], c[2] + rz)]
    for i in range(1, anillos):
        ph = math.pi * i / anillos
        for k in range(seg):
            th = TAU * k / seg
            verts.append((c[0] + rx * math.sin(ph) * math.cos(th),
                          c[1] + ry * math.sin(ph) * math.sin(th),
                          c[2] + rz * math.cos(ph)))
    last = len(verts)
    verts.append((c[0], c[1], c[2] - rz))
    faces = []
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((0, 1 + k, 1 + k2))
        for i in range(anillos - 2):
            b = 1 + i * seg
            faces.append((b + k, b + seg + k, b + seg + k2, b + k2))
        b = 1 + (anillos - 2) * seg
        faces.append((last, b + k2, b + k))
    mb.add(verts, faces, mat, smooth=smooth, recalc=True)


def _loft(mb, anillos, mats, tapa_ini=False, tapa_fin=False, smooth=True, recalc=True):
    """Superficie entre anillos (misma longitud). mats: material unico o
    lista por BANDA (len(anillos)-1). Tapas como n-gonos."""
    P = len(anillos[0])
    verts = [p for an in anillos for p in an]
    faces, fm = [], []
    for i in range(len(anillos) - 1):
        m = mats[i] if isinstance(mats, (list, tuple)) else mats
        for j in range(P):
            j2 = (j + 1) % P
            faces.append((i * P + j, i * P + j2, (i + 1) * P + j2, (i + 1) * P + j))
            fm.append(m)
    m0 = mats[0] if isinstance(mats, (list, tuple)) else mats
    m1 = mats[-1] if isinstance(mats, (list, tuple)) else mats
    if tapa_ini:
        faces.append(tuple(range(P)))
        fm.append(m0)
    if tapa_fin:
        b = (len(anillos) - 1) * P
        faces.append(tuple(b + j for j in reversed(range(P))))
        fm.append(m1)
    mb.add(verts, faces, fm, smooth=smooth, recalc=recalc)


def _orientar(verts, faces, hint):
    """Da la vuelta a las caras cuya normal (Newell) no mira hacia `hint`."""
    out = []
    for f in faces:
        nx = ny = nz = 0.0
        for k in range(len(f)):
            a, b = verts[f[k]], verts[f[(k + 1) % len(f)]]
            nx += (a[1] - b[1]) * (a[2] + b[2])
            ny += (a[2] - b[2]) * (a[0] + b[0])
            nz += (a[0] - b[0]) * (a[1] + b[1])
        if nx * hint[0] + ny * hint[1] + nz * hint[2] < 0.0:
            f = tuple(reversed(f))
        out.append(tuple(f))
    return out


def _lamina(mb, verts, faces, mat, hint, doble=False, smooth=False):
    """Lamina abierta orientada hacia `hint` (opcionalmente doble cara)."""
    fs = _orientar(verts, faces, hint)
    mb.add(verts, fs, mat, smooth=smooth)
    if doble:
        mb.add(verts, [tuple(reversed(f)) for f in fs], mat, smooth=smooth)


def _disco(mb, c, r, mat, seg=12, normal=(0, 0, 1), rx=None):
    """Disco plano (n-gono) de radio r (rx para elipse) centrado en c."""
    rx = r if rx is None else rx
    a, u, v, _ln = _base_ortonormal((0.0, 0.0, 0.0), normal)
    verts = []
    for k in range(seg):
        th = TAU * k / seg
        cu, sv = rx * math.cos(th), r * math.sin(th)
        verts.append((c[0] + u[0] * cu + v[0] * sv, c[1] + u[1] * cu + v[1] * sv,
                      c[2] + u[2] * cu + v[2] * sv))
    _lamina(mb, verts, [tuple(range(seg))], mat, normal)


def _lerp(a, b, t):
    return a + (b - a) * t


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _planta_redondeada(x0, x1, y_half, r, seg=3):
    """Rectangulo x0..x1 (+-y_half) con esquinas redondeadas (CCW)."""
    r = max(0.01, min(r, (x1 - x0) / 2.0 - 0.01, y_half - 0.01))
    pts = []
    esquinas = [((x1 - r, -y_half + r), -0.25), ((x1 - r, y_half - r), 0.0),
                ((x0 + r, y_half - r), 0.25), ((x0 + r, -y_half + r), 0.5)]
    for (cx, cy), a0 in esquinas:
        for k in range(seg + 1):
            th = TAU * (a0 + 0.25 * k / seg)
            pts.append((cx + r * math.cos(th), cy + r * math.sin(th)))
    return pts


# ---------------------------------------------------------------------------
# CASCO: loft de secciones a lo largo de X (popa x=-L/2, proa x=+L/2)
# ---------------------------------------------------------------------------
_PERFIL = [(1.00, 0.00), (1.035, 0.20), (1.02, 0.40), (0.93, 0.60),
           (0.72, 0.78), (0.42, 0.92), (0.00, 1.00)]


def _yfrac(zf):
    """Semiancho relativo del perfil de seccion a la altura relativa zf
    (0 = regala, 1 = quilla)."""
    for i in range(len(_PERFIL) - 1):
        (y0, z0), (y1, z1) = _PERFIL[i], _PERFIL[i + 1]
        if zf <= z1:
            t = (zf - z0) / (z1 - z0) if z1 > z0 else 0.0
            return _lerp(y0, y1, t)
    return 0.0


def _semimanga(t, B, planta=2.4):
    """Semiancho en planta a la fraccion t (0 popa .. 1 proa). `planta`:
    exponente del afinado de proa (mayor = proa mas llena)."""
    if t <= 0.45:
        return 0.5 * B * (0.86 + 0.14 * _smooth(t / 0.45))
    u = (t - 0.45) / 0.55
    return 0.5 * B * max(0.03, (max(0.0, 1.0 - u ** planta)) ** 0.55)


def _z_quilla(t, D):
    if t < 0.25:
        k = _lerp(0.70, 1.0, _smooth(t / 0.25))
    elif t < 0.55:
        k = 1.0
    else:
        k = _lerp(1.0, 0.28, _smooth((t - 0.55) / 0.45))
    return -D * k


def _z_regala(t, F, arrufo=0.30):
    return F * (1.0 + arrufo * t ** 2.2)


class _Casco:
    """Geometria de un casco: guarda las estaciones para colocar cosas.
    z_cub: altura de la cubierta en popa (t=0); la cubierta sube con el
    arrufo (k_deck = fraccion del arrufo que sigue; 1 = amurada de altura
    constante F - z_cub). rake: vuelo de la roda en +X a la altura de la
    regala (0 en la quilla), solo en el ultimo 20% de la eslora. planta:
    exponente del afinado de proa (ver _semimanga)."""

    def __init__(self, L, B, D, F, z_cub, n_est=18, arrufo=0.30, rake=0.0,
                 planta=2.4, k_deck=1.0):
        self.L, self.B, self.D, self.F, self.z_cub = L, B, D, F, z_cub
        self.ts = [k / float(n_est - 1) for k in range(n_est)]
        # mas densidad hacia la proa
        self.ts = [t ** 0.8 for t in self.ts]
        self.arrufo = arrufo
        self.rake = float(rake)
        self.planta = planta
        self.k_deck = k_deck

    def x(self, t):
        return -self.L / 2.0 + t * self.L

    def w(self, t):
        return _semimanga(t, self.B, self.planta)

    def z_top(self, t):
        return _z_regala(t, self.F, self.arrufo)

    def z_quilla(self, t):
        return _z_quilla(t, self.D)

    def x_rake(self, t, z):
        """x real de la piel del casco en la estacion t a la altura z (la
        roda vuela hacia +X cuanto mas arriba)."""
        if self.rake <= 0.0 or t < 0.80:
            return self.x(t)
        zt, zk = self.z_top(t), self.z_quilla(t)
        f = max(0.0, min(1.0, (z - zk) / (zt - zk)))
        return self.x(t) + self.rake * _smooth((t - 0.80) / 0.20) * f ** 1.4

    def w_cub(self, t):
        """Semiancho UTIL de la cubierta = semiancho interior de la amurada
        (grosor 0.16 m; junto a la roda, 40% del semiancho). Todo lo que se
        apoye en cubierta debe cumplir |y| + semiancho_pieza <= w_cub(t)."""
        w = self.w(t)
        return max(0.02, w - 0.16, 0.6 * w)

    def wi(self, t):
        """Alias de w_cub(t)."""
        return self.w_cub(t)

    def z_deck(self, t):
        """Altura de la cubierta en la estacion t (sigue el arrufo)."""
        return self.z_cub + self.k_deck * (self.z_top(t) - self.z_top(0.0))

    def zd(self, x):
        """Altura de la cubierta en la coordenada x."""
        return self.z_deck(self.t_de_x(x))

    def t_de_x(self, x):
        return max(0.0, min(1.0, (x + self.L / 2.0) / self.L))


def _orientar_cada(verts, faces, hint_fn):
    """Orienta cada cara segun hint_fn(centro) -> vector guia."""
    out = []
    for f in faces:
        n = float(len(f))
        c = (sum(verts[i][0] for i in f) / n, sum(verts[i][1] for i in f) / n,
             sum(verts[i][2] for i in f) / n)
        out.extend(_orientar(verts, [f], hint_fn(c)))
    return out


def _construir_casco(mb, cs, m_casco, m_franja, m_obra, m_cub, zs_top=None, zs_bot=None):
    """Casco cerrado (loft de estaciones, roda con rake) + amurada de 0.16 m
    (tapa a la regala + pared interior vertical en cs.w_cub) + cubierta a
    cs.z_deck(t). Deja en cs.anillos las regalas (x, +-y, z) por estacion
    para barandillas. Cada cara lleva su vector guia explicito."""
    D, F = cs.D, cs.F
    zs_top = 0.15 * F if zs_top is None else zs_top
    zs_bot = -0.10 * D if zs_bot is None else zs_bot
    bandas_m = [m_casco, m_casco, m_franja, m_obra, m_obra, m_obra]
    banda_de_cara = [0, 1, 2, 3, 4, 5, 5, 4, 3, 2, 1, 0]
    verts, faces, fm, hints = [], [], [], []
    regalas, zms = [], []
    P = 13
    for t in cs.ts:
        w, zt, zk = cs.w(t), cs.z_top(t), cs.z_quilla(t)
        zf_st = (zt - zs_top) / (zt - zk)
        zf_sb = (zt - zs_bot) / (zt - zk)
        niveles = [0.0, 0.5 * zf_st, zf_st, zf_sb, zf_sb + 0.42 * (1.0 - zf_sb),
                   zf_sb + 0.78 * (1.0 - zf_sb), 1.0]
        pts = []
        for zf in niveles:                       # babor, de regala a quilla
            z = zt - zf * (zt - zk)
            pts.append((cs.x_rake(t, z), -w * _yfrac(zf), z))
        for zf in reversed(niveles[:-1]):        # estribor, de quilla a regala
            z = zt - zf * (zt - zk)
            pts.append((cs.x_rake(t, z), w * _yfrac(zf), z))
        verts.extend(pts)
        regalas.append((cs.x_rake(t, zt), w, zt))
        zms.append(0.5 * (zt + zk))
    n = len(cs.ts)
    for i in range(n - 1):
        zm = 0.5 * (zms[i] + zms[i + 1])
        for j in range(P - 1):
            f = (i * P + j, i * P + j + 1, (i + 1) * P + j + 1, (i + 1) * P + j)
            faces.append(f)
            fm.append(bandas_m[banda_de_cara[j]])
            cy = sum(verts[k][1] for k in f) / 4.0
            cz = sum(verts[k][2] for k in f) / 4.0
            hints.append((0.0, cy, cz - zm))
    # tapas: espejo de popa y roda
    faces.append(tuple(range(P))); fm.append(m_casco); hints.append((-1.0, 0.0, 0.0))
    faces.append(tuple((n - 1) * P + j for j in range(P))); fm.append(m_casco)
    hints.append((1.0, 0.0, 0.0))
    # amurada (tapa + pared interior) y cubierta
    b = len(verts)
    for k, t in enumerate(cs.ts):
        x, w, zt = regalas[k]
        wi, zc = cs.w_cub(t), cs.z_deck(t)
        verts.extend([(x, -w, zt), (x, -wi, zt), (x, -wi, zc),
                      (x, wi, zc), (x, wi, zt), (x, w, zt)])
    bul_m = [m_casco, m_casco, m_cub, m_casco, m_casco]
    bul_h = [(0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)]
    for i in range(n - 1):
        a, c = b + 6 * i, b + 6 * (i + 1)
        for j in range(5):
            faces.append((a + j, a + j + 1, c + j + 1, c + j))
            fm.append(bul_m[j])
            hints.append(bul_h[j])
    fs = []
    for f, h in zip(faces, hints):
        fs.extend(_orientar(verts, [f], h))
    mb.add(verts, fs, fm, smooth=True)
    cs.anillos = regalas
    cs.z_sb = zs_bot


def _popa(mb, cs, m_casco, m_cub, m_acero):
    """Plataforma de bano con tapa de teca, escalera al agua, rampa a la
    cubierta y amurada de popa con porton central."""
    L, F = cs.L, cs.F
    w0 = cs.w(0.0)
    lp = max(0.45, 0.045 * L)
    zp = min(0.70, max(0.32, 0.18 * F))
    x0 = -L / 2.0
    _caja(mb, (x0 - lp / 2.0 + 0.1, 0.0, zp - 0.16), (lp + 0.2, 2.0 * (w0 - 0.30), 0.30), m_casco)
    _caja(mb, (x0 - lp / 2.0 + 0.1, 0.0, zp + 0.005), (lp + 0.2, 2.0 * (w0 - 0.34), 0.03), m_cub)
    # escalera de bano (2 largueros + 3 peldanos) hacia el agua
    xe = x0 - lp - 0.05
    ye = -(w0 - 0.9)
    for dy in (-0.22, 0.22):
        _cil(mb, (xe, ye + dy, zp + 0.05), (xe - 0.25, ye + dy, -0.85), 0.02, 0.02, m_acero, seg=5)
    for k in range(3):
        f = (k + 1) / 4.0
        z = zp + 0.05 - f * (zp + 0.9)
        _cil(mb, (xe - 0.25 * f, ye - 0.22, z), (xe - 0.25 * f, ye + 0.22, z), 0.018, 0.018,
             m_acero, seg=5, tapas=False)
    # amurada de popa con porton central de 1.8 m
    zt0 = cs.z_top(0.0)
    wi = cs.w_cub(0.0)
    ancho = wi - 0.9
    if ancho > 0.2:
        for s in (-1, 1):
            _caja(mb, (x0 + 0.08, s * (0.9 + ancho / 2.0), (zt0 + cs.z_cub) / 2.0),
                  (0.16, ancho, zt0 - cs.z_cub), m_casco)
    # rampa (escalera-rampa 'car-ificada') de la plataforma a la cubierta
    dz = cs.z_cub - zp
    lr = max(1.2, dz * 2.2)
    ang = math.atan2(dz, lr)
    cx = x0 + lr / 2.0 - 0.1
    _caja(mb, (cx, 0.0, zp + dz / 2.0), (math.hypot(lr, dz), 1.7, 0.12), m_cub, ry=-ang)
    # apoyo de la rampa (cuna)
    _caja(mb, (x0 + lr * 0.5, 0.0, zp + dz * 0.25), (lr * 0.5, 1.5, dz * 0.5), m_casco)
    return zp


# ---------------------------------------------------------------------------
# SUPERESTRUCTURA: piso con frente redondeado e inclinado + banda de cristal
# ---------------------------------------------------------------------------
def _cabina(mb, xa, xb, yh, z0, h, m_casco, m_cristal, rake=None, r_frente=None,
            cristal=(0.40, 0.86), visera=0.45, tumble=0.96, chaflan=0.6, seg_frente=8):
    """Piso entre xa (popa) y xb (proa). yh: semiancho o funcion yh(x).
    Devuelve (z_techo, contorno_techo[(x, y)]) para colocar barandillas."""
    if not callable(yh):
        yv = float(yh)
        yh = lambda _x: yv
    rf = r_frente if r_frente is not None else min(0.45 * (xb - xa), 0.95 * yh(xb - 0.01))
    rf = max(0.05, rf)
    rake = 0.30 * h if rake is None else rake
    xm = xb - rf
    chaflan = min(chaflan, 0.45 * yh(xa), 0.45 * (xm - xa))

    def contorno(off, zf):
        ya = yh(xa) + off
        pts = [(xa - off, ya - chaflan), (xa + chaflan, ya)]
        for k in range(1, 5):
            x = _lerp(xa + chaflan, xm, k / 4.0)
            pts.append((x, yh(x) + off))
        ry = yh(xm) + off
        for k in range(1, seg_frente):
            a = 0.5 * math.pi - math.pi * k / seg_frente
            pts.append((xm + (rf + off) * math.cos(a), ry * math.sin(a)))
        for k in range(4, 0, -1):
            x = _lerp(xa + chaflan, xm, k / 4.0)
            pts.append((x, -(yh(x) + off)))
        pts.append((xa + chaflan, -ya))
        pts.append((xa - off, -(ya - chaflan)))
        out = []
        for (x, y) in pts:
            if x > xm:
                x = x - rake * zf * (x - xm) / (rf + off)
            out.append((x, y * (1.0 - (1.0 - tumble) * zf)))
        return out

    def anillo(off, zf, z):
        return [(x, y, z) for (x, y) in contorno(off, zf)]

    _loft(mb, [anillo(0.0, 0.0, z0), anillo(0.0, 1.0, z0 + h)], m_casco,
          tapa_ini=True, tapa_fin=True, smooth=True)
    c0, c1 = cristal
    _loft(mb, [anillo(0.04, c0, z0 + c0 * h), anillo(0.04, c1, z0 + c1 * h)], m_cristal,
          tapa_ini=True, tapa_fin=True, smooth=True)
    if visera > 0.0:
        _loft(mb, [anillo(visera, 1.0, z0 + h - 0.02), anillo(visera, 1.0, z0 + h + 0.10)],
              m_casco, tapa_ini=True, tapa_fin=True, smooth=False)
    return z0 + h + (0.10 if visera > 0.0 else 0.0), contorno(0.0, 1.0)


def _barandilla(mb, puntos, alto, m_acero, paso=1.3, cerrada=False, r=0.022, medio=True):
    """Barandilla de acero sobre la polilinea `puntos` [(x, y, z)]: candeleros
    cada ~paso + pasamanos (y barra intermedia)."""
    if cerrada:
        puntos = list(puntos) + [puntos[0]]
    longs = []
    for a, b in zip(puntos[:-1], puntos[1:]):
        longs.append(math.dist(a, b))
    total = sum(longs)
    if total < 1e-6:
        return
    n = max(2, int(round(total / paso)) + 1)
    tops = []
    for k in range(n):
        d = total * k / (n - 1)
        acc, seg_i = 0.0, 0
        while seg_i < len(longs) - 1 and acc + longs[seg_i] < d:
            acc += longs[seg_i]
            seg_i += 1
        f = (d - acc) / longs[seg_i] if longs[seg_i] > 1e-9 else 0.0
        a, b = puntos[seg_i], puntos[seg_i + 1]
        p = (_lerp(a[0], b[0], f), _lerp(a[1], b[1], f), _lerp(a[2], b[2], f))
        _cil(mb, p, (p[0], p[1], p[2] + alto), r, r, m_acero, seg=5, tapas=False)
        tops.append(p)
    for a, b in zip(tops[:-1], tops[1:]):
        _cil(mb, (a[0], a[1], a[2] + alto), (b[0], b[1], b[2] + alto), r, r, m_acero,
             seg=4, tapas=False)
        if medio:
            _cil(mb, (a[0], a[1], a[2] + 0.5 * alto), (b[0], b[1], b[2] + 0.5 * alto),
                 0.7 * r, 0.7 * r, m_acero, seg=4, tapas=False)


def _defensas(mb, cs, m_defensa, m_acero, lado=1, ts=(0.10, 0.28, 0.48, 0.66, 0.82)):
    for t in ts:
        x, w, zt = cs.x_rake(t, 0.3), cs.w(t), cs.z_top(t)
        y = lado * (w + 0.30)
        _cil(mb, (x, y, -0.15), (x, y, 0.70), 0.27, 0.27, m_defensa, seg=8)
        _elipsoide(mb, (x, y, -0.15), 0.27, 0.27, 0.12, m_defensa, seg=8, anillos=3)
        _elipsoide(mb, (x, y, 0.70), 0.27, 0.27, 0.12, m_defensa, seg=8, anillos=3)
        _cil(mb, (x, y, 0.80), (x, lado * w, zt), 0.012, 0.012, m_acero, seg=4, tapas=False)


def _bandera(mb, base, alto, m_acero, m_v, m_b, m_r, ancho=0.9, alto_b=0.6, incl=0.42):
    """Mastil inclinado hacia popa (-X) con bandera italiana ondulada."""
    top = (base[0] - alto * math.sin(incl), base[1], base[2] + alto * math.cos(incl))
    _cil(mb, base, top, 0.03, 0.02, m_acero, seg=6)
    _elipsoide(mb, top, 0.06, 0.06, 0.06, m_acero, seg=6, anillos=3)
    dx, dz = -math.sin(incl), math.cos(incl)         # eje del mastil
    NC, NF = 6, 3
    verts = []
    for i in range(NF + 1):
        s = alto_b * i / NF
        for j in range(NC + 1):
            u = ancho * j / NC
            px = top[0] - dz * u - dx * s
            pz = top[2] + dx * u - dz * s
            py = top[1] + 0.06 * math.sin(4.0 * u / ancho + 1.5 * s / alto_b) * (u / ancho)
            verts.append((px, py, pz))
    faces, fm = [], []
    for i in range(NF):
        for j in range(NC):
            a = i * (NC + 1) + j
            faces.append((a, a + 1, a + NC + 2, a + NC + 1))
            fm.append([m_v, m_v, m_b, m_b, m_r, m_r][j])
    mb.add(verts, faces, fm, smooth=True)
    mb.add(verts, [tuple(reversed(f)) for f in faces], fm, smooth=True)


def _sombrilla(mb, c, m_palo, m_a, m_b, r=1.3, alto=2.3, seg=8):
    _cil(mb, c, (c[0], c[1], c[2] + alto + 0.30), 0.025, 0.02, m_palo, seg=6)
    apex = (c[0], c[1], c[2] + alto + 0.30)
    rim = [(c[0] + r * math.cos(TAU * k / seg), c[1] + r * math.sin(TAU * k / seg), c[2] + alto - 0.08)
           for k in range(seg)]
    for capa in (0.0, -0.015):
        verts = [(apex[0], apex[1], apex[2] + capa)] + [(p[0], p[1], p[2] + capa) for p in rim]
        faces = [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)]
        fm = [m_a if k % 2 == 0 else m_b for k in range(seg)]
        if capa == 0.0:
            mb.add(verts, _orientar(verts, faces, (0, 0, 1)), fm, smooth=False)
        else:
            mb.add(verts, _orientar(verts, faces, (0, 0, -1)), fm, smooth=False)


def _tumbona(mb, c, rz, m_blanco, m_crema):
    _caja(mb, (c[0], c[1], c[2] + 0.16), (0.70, 1.90, 0.28), m_blanco, rz=rz)
    _caja(mb, (c[0], c[1], c[2] + 0.36), (0.64, 1.86, 0.12), m_crema, rz=rz)
    p = _rot((0.0, -0.78, 0.66), rz)
    _caja(mb, (c[0] + p[0], c[1] + p[1], c[2] + p[2]), (0.62, 0.62, 0.10), m_crema, rz=rz, rx=-0.95)


def _mesa_alta(mb, c, m_blanco, m_acero, m_champan, m_negro, copas=3):
    _cil(mb, c, (c[0], c[1], c[2] + 0.04), 0.32, 0.32, m_acero, seg=10)
    _cil(mb, (c[0], c[1], c[2] + 0.04), (c[0], c[1], c[2] + 1.02), 0.04, 0.04, m_acero, seg=6)
    zt = c[2] + 1.02
    _cil(mb, (c[0], c[1], zt), (c[0], c[1], zt + 0.05), 0.42, 0.42, m_blanco, seg=12)
    for k in range(copas):
        th = TAU * k / copas
        x, y = c[0] + 0.22 * math.cos(th), c[1] + 0.22 * math.sin(th)
        _cil(mb, (x, y, zt + 0.05), (x, y, zt + 0.15), 0.012, 0.012, m_acero, seg=4, tapas=False)
        _cil(mb, (x, y, zt + 0.15), (x, y, zt + 0.31), 0.025, 0.035, m_champan, seg=6)
    _cil(mb, (c[0], c[1], zt + 0.05), (c[0], c[1], zt + 0.30), 0.11, 0.14, m_acero, seg=8)
    _cil(mb, (c[0], c[1], zt + 0.20), (c[0], c[1], zt + 0.55), 0.045, 0.025, m_negro, seg=6)


def _tr(p, c, rz, ry):
    q = _rot(p, rz, ry)
    return (q[0] + c[0], q[1] + c[1], q[2] + c[2])


def _pasarela(mb, A, B, m_blanco, m_alfombra, m_acero, ancho=1.0):
    """Pasarela recta de A a B (caja inclinada) con alfombra roja y pasamanos."""
    dx, dy, dz = B[0] - A[0], B[1] - A[1], B[2] - A[2]
    ln = math.sqrt(dx * dx + dy * dy + dz * dz)
    rz = math.atan2(dy, dx)
    ry = -math.asin(max(-1.0, min(1.0, dz / ln)))
    c = ((A[0] + B[0]) / 2.0, (A[1] + B[1]) / 2.0, (A[2] + B[2]) / 2.0)
    _caja(mb, c, (ln, ancho, 0.08), m_blanco, rz=rz, ry=ry)
    _caja(mb, _tr((0.0, 0.0, 0.055), c, rz, ry), (ln - 0.1, ancho * 0.78, 0.02), m_alfombra, rz=rz, ry=ry)
    for s in (-1, 1):
        y = s * (ancho / 2.0 - 0.04)
        tops = []
        for f in (-0.42, 0.0, 0.42):
            p0 = _tr((f * ln, y, 0.04), c, rz, ry)
            p1 = _tr((f * ln, y, 0.95), c, rz, ry)
            _cil(mb, p0, p1, 0.02, 0.02, m_acero, seg=5, tapas=False)
            tops.append(p1)
        for a, b in zip(tops[:-1], tops[1:]):
            _cil(mb, a, b, 0.022, 0.022, m_acero, seg=4, tapas=False)


def _mastil_radar(mb, x, y, z, s, m_casco, m_acero, m_gris):
    """Arco de radar sobre el techo del puente: arco inclinado, radomo,
    barra de radar giratoria, antenas y foco."""
    for sg in (-1, 1):
        _cil(mb, (x, y + sg * 1.1 * s, z), (x - 0.55 * s, y + sg * 0.65 * s, z + 1.7 * s),
             0.09 * s, 0.07 * s, m_casco, seg=6)
    _cil(mb, (x - 0.55 * s, y - 0.65 * s, z + 1.7 * s), (x - 0.55 * s, y + 0.65 * s, z + 1.7 * s),
         0.09 * s, 0.09 * s, m_casco, seg=6)
    _elipsoide(mb, (x - 0.55 * s, y, z + 2.0 * s), 0.42 * s, 0.42 * s, 0.30 * s, m_casco, seg=10, anillos=4)
    _cil(mb, (x - 0.55 * s, y + 0.35 * s, z + 1.75 * s), (x - 0.55 * s, y + 0.35 * s, z + 2.35 * s),
         0.05 * s, 0.04 * s, m_acero, seg=5)
    _caja(mb, (x - 0.55 * s, y + 0.35 * s, z + 2.42 * s), (1.3 * s, 0.14 * s, 0.14 * s), m_gris, rz=0.5)
    _cil(mb, (x - 0.55 * s, y - 0.45 * s, z + 1.75 * s), (x - 0.55 * s, y - 0.45 * s, z + 3.4 * s),
         0.025 * s, 0.015 * s, m_acero, seg=4, tapas=False)
    _cil(mb, (x - 0.55 * s, y - 0.2 * s, z + 1.75 * s), (x - 0.55 * s, y - 0.2 * s, z + 2.9 * s),
         0.02 * s, 0.012 * s, m_acero, seg=4, tapas=False)
    _cil(mb, (x - 0.40 * s, y, z + 1.72 * s), (x - 0.15 * s, y, z + 1.72 * s),
         0.12 * s, 0.14 * s, m_acero, seg=8)


# ---------------------------------------------------------------------------
# Coches-espectador (coches_kit_v2.py, importado por ruta) y publico VIP
# ---------------------------------------------------------------------------
_TIPOS_VIP = ("sedan", "deportivo", "familiar", "compacto", "topolino")


def _coches():
    m = sys.modules.get("coches_kit_v2")
    if m is None:
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coches_kit_v2.py")
        spec = importlib.util.spec_from_file_location("coches_kit_v2", ruta)
        m = importlib.util.module_from_spec(spec)
        sys.modules["coches_kit_v2"] = m
        spec.loader.exec_module(m)
    return m


def _coche_vip(parent_collection, root, pos, tipo, color, seed, rng, expresion=None,
               boca=None, giro=0.0):
    """Coche de coches_kit_v2 (sin baca/franjas/bitono, mirando a +Y) apoyado
    en la cubierta `pos`, hijo del raiz."""
    ck = _coches()
    if expresion is None:
        expresion = rng.choice(("abierto", "feliz", "feliz", "sorpresa"))
    if boca is None:
        boca = "abierta" if expresion == "sorpresa" else rng.choice(("sonrisa", "sonrisa", "dientes"))
    ob = ck.build_coche(parent_collection, tipo=tipo, color=color, seed=seed,
                        expresion=expresion, boca=boca, baca=False, bitono=False,
                        franjas=False, carga=False)
    ob.parent = root
    ob.location = pos
    ob.rotation_euler = (0.0, 0.0, giro)
    return ob


def _mayordomo(parent_collection, root, mb, pos, seed, rng, tipo="topolino", giro=-math.pi / 2.0):
    """Coche negro (mayordomo) con pajarita blanca en el capo y bandeja de
    copas en el techo. Por defecto un topolino mirando a +X (giro=-90 grados)."""
    ob = _coche_vip(parent_collection, root, pos, tipo, COLORES_LUJO[0][1], seed, rng,
                    expresion="feliz", boca="sonrisa", giro=giro)
    zt = max(v.co.z for v in ob.data.vertices)
    yf = max(v.co.y for v in ob.data.vertices)
    zc = max(v.co.z for v in ob.data.vertices if v.co.y > yf - 0.6)
    m_blanco, m_acero, m_champan = _mat("blanco"), _mat("acero"), _mat("champan")

    def P(p):
        q = _rot(p, giro)
        return (q[0] + pos[0], q[1] + pos[1], q[2] + pos[2])
    # bandeja en el techo con 4 copas
    c = P((0.0, -0.25, zt + 0.02))
    _cil(mb, c, (c[0], c[1], c[2] + 0.03), 0.36, 0.36, m_acero, seg=10)
    for k in range(4):
        th = TAU * k / 4.0 + 0.4
        q = P((0.2 * math.cos(th), -0.25 + 0.2 * math.sin(th), zt + 0.05))
        _cil(mb, q, (q[0], q[1], q[2] + 0.09), 0.012, 0.012, m_acero, seg=4, tapas=False)
        _cil(mb, (q[0], q[1], q[2] + 0.09), (q[0], q[1], q[2] + 0.24), 0.025, 0.035, m_champan, seg=6)
    # pajarita blanca sobre el capo, delante del parabrisas
    for s in (-1, 1):
        _caja(mb, P((s * 0.12, yf - 0.55, zc + 0.05)), (0.18, 0.07, 0.11), m_blanco, rz=giro, ry=s * 0.35)
    _caja(mb, P((0.0, yf - 0.55, zc + 0.05)), (0.07, 0.07, 0.07), m_blanco, rz=giro)
    return ob


def _colores_vip(rng, n):
    cols = [c for _n, c in COLORES_LUJO]
    rng.shuffle(cols)
    return [cols[i % len(cols)] for i in range(n)]


# ---------------------------------------------------------------------------
# YATE (32 m por defecto)
# ---------------------------------------------------------------------------
def _dims(L):
    """Manga, calado, francobordo y altura de cubierta segun la eslora."""
    B = 2.4 + 0.16 * L if L >= 20.0 else 0.30 * L
    D = min(-Z_MIN_CASCO, 0.07 * L + 0.2)
    F = min(4.2, 0.068 * L)
    # amurada de 0.55..1.0 m (cubierta en popa a F - amurada)
    return B, D, F, F - min(1.0, max(0.55, 0.28 * F))


def _ojos_de_buey(mb, cs, m_cristal, n=6, t0=0.18, t1=0.66, frac=0.25):
    """Fila de ventanas ovaladas oscuras en el casco (ambas bandas), a la
    fraccion `frac` de la altura entre la cubierta y la franja."""
    for k in range(n):
        t = _lerp(t0, t1, k / float(n - 1))
        w, zt, zk = cs.w(t), cs.z_top(t), cs.z_quilla(t)
        z = cs.z_cub - frac * (cs.z_cub - 0.15 * cs.F)
        x = cs.x_rake(t, z)
        zf = (zt - z) / (zt - zk)
        y = w * _yfrac(zf) + 0.02
        for s in (-1, 1):
            _disco(mb, (x, s * y, z), 0.20, m_cristal, seg=10, normal=(0, s, 0), rx=0.34)


def _cinta(mb, cs, z, m, off=0.03, alto=0.10, t0=0.0, t1=0.985):
    """Cinta de color (rub rail) a la altura z (numero o funcion z(t))
    siguiendo el casco, ambas bandas."""
    z_fn = z if callable(z) else (lambda _t: z)
    for s in (-1, 1):
        verts, faces = [], []
        for t in cs.ts:
            if t < t0 or t > t1:
                continue
            w, zt, zk, zc = cs.w(t), cs.z_top(t), cs.z_quilla(t), z_fn(t)
            x = cs.x_rake(t, zc)
            zf = (zt - zc) / (zt - zk)
            y = w * _yfrac(zf) + off
            verts.append((x, s * y, zc - alto / 2.0))
            verts.append((x, s * y, zc + alto / 2.0))
        for i in range(len(verts) // 2 - 1):
            faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
        _lamina(mb, verts, faces, m, (0, s, 0), smooth=True)


def _rail_flybridge(mb, xa, x_fin, yh, chaflan, z, m_acero, alto=0.9):
    xs = [_lerp(x_fin, xa + chaflan, k / 3.0) for k in range(4)]
    stb = [(x, yh(x), z) for x in xs] + [(xa, yh(xa) - chaflan, z)]
    port = [(x, -y, z) for (x, y, _z) in reversed(stb)]
    _barandilla(mb, stb + port, alto, m_acero, paso=1.25)


def _spots_yate(cs, xa1, xa2, z_tf, lr):
    """Plazas de publico (x, y, z, tipos, giro) en orden de prioridad. Las
    de cubierta principal van a estribor (y>0) dentro de cs.w_cub y a la
    altura cs.zd(x)."""
    L = cs.L
    spots = []
    x = xa1 - 1.3
    while x - 0.95 > -L / 2.0 + lr + 0.1 and len(spots) < 3:
        spots.append((x, 0.8, cs.zd(x), ("sedan", "deportivo", "familiar"), 0.0))
        x -= 2.25
    if xa2 - xa1 > 4.6:
        spots.append((xa1 + 1.45, 0.35, z_tf, ("deportivo", "compacto"), 0.0))
        spots.append((xa1 + 3.65, 0.35, z_tf, ("compacto", "deportivo"), 0.0))
    spots.append((0.345 * L, 0.5, cs.zd(0.345 * L), ("topolino",), 0.0))
    if xa2 - xa1 > 6.8:
        spots.append((xa1 + 5.85, 0.35, z_tf, ("compacto",), 0.0))
    return spots


def build_yate(parent_collection, eslora=32.0, seed=0, con_publico=True, **params):
    """Yate a motor de lujo (Empty YATE_root). Ver docstring del modulo."""
    n_coches = params.pop("n_coches", None)
    con_pasarela = params.pop("pasarela", True)
    con_bandera = params.pop("bandera", True)
    if params:
        raise TypeError("build_yate() no admite %s" % sorted(params))
    rng = random.Random(7919 * int(seed) + 41)
    L = float(eslora)
    B, D, F, z_cub = _dims(L)
    cs = _Casco(L, B, D, F, z_cub, n_est=20, rake=0.03 * L)
    m_casco, m_franja, m_obra = _mat("casco"), _mat("franja"), _mat("obra_viva")
    m_cub, m_cristal, m_acero = _mat("cubierta"), _mat("cristal"), _mat("acero")
    root = _empty("%s_root" % PREFIX, parent_collection, size=3.0)

    # ---- casco + popa + ojos de buey
    mb = _MB()
    _construir_casco(mb, cs, m_casco, m_franja, m_obra, m_cub)
    zp = _popa(mb, cs, m_casco, m_cub, m_acero)
    lr = max(1.2, (z_cub - zp) * 1.8)
    _ojos_de_buey(mb, cs, m_cristal)
    _cinta(mb, cs, lambda t: cs.z_deck(t) - 0.10, _mat("cinta"), alto=0.09)
    ob = mb.build("%s_casco" % PREFIX, parent_collection)
    ob.parent = root

    # ---- superestructura: salon (piso 1) + puente (piso 2) + hardtop + radar
    mb = _MB()
    xa1, xb1 = -0.22 * L, 0.30 * L
    h1 = max(2.3, 0.072 * L)
    yh1 = lambda x: max(0.8, cs.w_cub(cs.t_de_x(x)) - 0.55)
    z_c1 = cs.zd(xa1) - 0.02          # la cubierta sube hacia proa bajo el salon
    z_tf, _c1 = _cabina(mb, xa1, xb1, yh1, z_c1, h1, m_casco, m_cristal, rake=0.9,
                        cristal=(0.40, 0.86), visera=0.40, chaflan=0.6)
    xa2, xb2 = -0.04 * L, xb1 - 0.075 * L
    h2 = 0.92 * h1
    yh2 = lambda x: max(0.7, yh1(x) - 0.45)
    z_t2, _c2 = _cabina(mb, xa2, xb2, yh2, z_tf, h2, m_casco, m_cristal, rake=1.25,
                        cristal=(0.36, 0.88), visera=0.55, chaflan=0.5)
    # hardtop volado hacia popa sobre el flybridge + tornapuntas
    lx = 0.10 * L
    _caja(mb, (xa2 - lx / 2.0 + 0.2, 0.0, z_t2 - 0.06), (lx + 0.4, 2.0 * (yh2(xa2) + 0.55), 0.12), m_casco)
    for s in (-1, 1):
        _cil(mb, (xa2 - lx + 0.5, s * (yh1(xa1 + 1.0) - 0.35), z_tf),
             (xa2 - lx + 0.55, s * (yh2(xa2) + 0.35), z_t2 - 0.12), 0.06, 0.05, m_casco, seg=6)
    s_r = math.sqrt(L / 32.0)
    _mastil_radar(mb, xa2 + 0.55 * (xb2 - xa2), 0.0, z_t2, s_r, m_casco, m_acero, _mat("gris"))
    ob = mb.build("%s_cabina" % PREFIX, parent_collection)
    ob.parent = root

    # ---- detalles: barandillas, defensas, bandera, sombrillas, tumbonas...
    mb = _MB()
    for s in (-1, 1):
        pts = [(x, s * w, zt) for (x, w, zt) in cs.anillos if 0.02 <= cs.t_de_x(x) <= 0.96]
        _barandilla(mb, pts, 0.85, m_acero, paso=1.35)
    _rail_flybridge(mb, xa1, xa2 - 0.3, yh1, 0.6, z_tf, m_acero)
    _defensas(mb, cs, _mat("defensa"), m_acero, lado=1)
    if con_bandera:
        _bandera(mb, (-L / 2.0 + 0.5, -(cs.w(0.0) - 0.75), cs.z_top(0.0)), 2.2, m_acero,
                 _mat("verde_bandera"), _mat("blanco"), _mat("rojo_bandera"))
    m_blanco, m_crema, m_azul = _mat("blanco"), _mat("crema"), _mat("azul")
    # flybridge: sombrilla + tumbonas a babor (los coches van a estribor)
    _sombrilla(mb, (xa1 + 0.55 * (xa2 - xa1), -yh1(xa1) * 0.45, z_tf), m_acero, m_crema, m_azul, r=1.25)
    _tumbona(mb, (xa1 + 1.2, -yh1(xa1) * 0.55, z_tf), 0.0, m_blanco, m_crema)
    _tumbona(mb, (xa1 + 2.1, -yh1(xa1) * 0.55, z_tf), 0.0, m_blanco, m_crema)
    # cubierta de popa (babor, dentro de w_cub): mesa alta con champan + sombrilla
    _mesa_alta(mb, (xa1 - 1.6, -2.3, cs.zd(xa1 - 1.6)), m_blanco, m_acero, _mat("champan"), _mat("negro"))
    _sombrilla(mb, (xa1 - 2.6, -2.2, cs.zd(xa1 - 2.6)), m_acero, m_crema, m_azul, r=1.2, alto=2.4)
    # proa: tumbona a babor a lo largo de X (el coche va a estribor)
    _tumbona(mb, (0.40 * L, -1.2, cs.zd(0.40 * L)), math.pi / 2.0, m_blanco, m_crema)
    # pasarela con alfombra roja a estribor (baja hasta z=0.95 = pantalan)
    if con_pasarela:
        tp = cs.t_de_x(-0.30 * L)
        A = (cs.x(tp), cs.w(tp) + 0.05, cs.z_top(tp) + 0.02)
        _pasarela(mb, A, (A[0] - 4.2, cs.w(tp) + 2.1, 0.95), m_blanco, _mat("alfombra"), m_acero)
    # mayordomo en popa (mirando a +X, junto a la mesa)
    ob_mb_det = mb          # la bandeja del mayordomo se anade a esta malla
    coches = []
    if con_publico:
        spots = _spots_yate(cs, xa1, xa2, z_tf, lr)
        n = min(len(spots), max(1, n_coches if n_coches is not None else rng.randint(4, 8)))
        cols = _colores_vip(rng, n)
        for i in range(n):
            x, y, z, tipos, giro = spots[i]
            coches.append(_coche_vip(parent_collection, root, (x, y, z), rng.choice(tipos),
                                     cols[i], seed * 100 + i, rng, giro=giro))
        _mayordomo(parent_collection, root, ob_mb_det, (xa1 - 4.4, -2.25, cs.zd(xa1 - 4.4)),
                   seed * 100 + 50, rng)
    ob = mb.build("%s_detalles" % PREFIX, parent_collection)
    ob.parent = root
    root["eslora"] = L
    return root


# ---------------------------------------------------------------------------
# SUPERYATE: helipuerto, helicoptero, piscina
# ---------------------------------------------------------------------------
def _helipuerto(mb, c, r, m_suelo, m_blanco, alto=0.22):
    """Plataforma circular (base en c, `alto` de grosor) con anillo y H
    blancos. Devuelve la z de la superficie."""
    _cil(mb, (c[0], c[1], c[2]), (c[0], c[1], c[2] + alto), r, r, m_suelo, seg=20, smooth=False)
    zt = c[2] + alto + 0.015
    # anillo blanco (banda de 0.25 m) + H central
    seg = 20
    verts = []
    for rr in (r - 0.35, r - 0.10):
        for k in range(seg):
            th = TAU * k / seg
            verts.append((c[0] + rr * math.cos(th), c[1] + rr * math.sin(th), zt))
    faces = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)]
    _lamina(mb, verts, faces, m_blanco, (0, 0, 1))
    hh = 0.32 * r
    _caja(mb, (c[0], c[1] - 0.62 * hh, zt + 0.01), (2.0 * hh, 0.34 * hh, 0.02), m_blanco)
    _caja(mb, (c[0], c[1] + 0.62 * hh, zt + 0.01), (2.0 * hh, 0.34 * hh, 0.02), m_blanco)
    _caja(mb, (c[0], c[1], zt + 0.01), (0.34 * hh, 1.6 * hh, 0.02), m_blanco)
    return c[2] + alto


def _helicoptero(mb, c, m_cuerpo, m_cristal, m_acero, m_negro, m_crema, rz=0.0):
    """Mini helicoptero (~5 m) apoyado en c (patines en z=c[2]), morro a +X
    girado rz."""
    def P(p):
        q = _rot(p, rz)
        return (q[0] + c[0], q[1] + c[1], q[2] + c[2])
    zb = 1.05
    # fuselaje (gota) + cabina acristalada delante
    _elipsoide(mb, P((0.0, 0.0, zb + 0.75)), 1.55, 0.95, 0.85, m_cuerpo, seg=12, anillos=6)
    _elipsoide(mb, P((0.85, 0.0, zb + 0.82)), 0.95, 0.80, 0.68, m_cristal, seg=12, anillos=6)
    _caja(mb, P((-0.2, 0.0, zb + 0.35)), (2.0, 1.1, 0.30), m_crema, rz=rz)
    # cola + aleta + rotor de cola
    _cil(mb, P((-1.3, 0.0, zb + 0.95)), P((-3.9, 0.0, zb + 1.25)), 0.30, 0.10, m_cuerpo, seg=8)
    _caja(mb, P((-3.8, 0.0, zb + 1.7)), (0.55, 0.08, 0.9), m_crema, rz=rz, ry=-0.35)
    _cil(mb, P((-3.85, -0.05, zb + 1.35)), P((-3.85, 0.18, zb + 1.35)), 0.06, 0.06, m_acero, seg=6)
    _caja(mb, P((-3.85, 0.22, zb + 1.35)), (0.10, 0.04, 1.3), m_negro, rz=rz)
    _caja(mb, P((-3.85, 0.22, zb + 1.35)), (0.10, 0.04, 1.3), m_negro, rz=rz, rx=1.5708)
    # mastil y rotor principal (2 palas)
    _cil(mb, P((0.0, 0.0, zb + 1.4)), P((0.0, 0.0, zb + 2.0)), 0.10, 0.08, m_acero, seg=6)
    _elipsoide(mb, P((0.0, 0.0, zb + 2.0)), 0.18, 0.18, 0.10, m_acero, seg=8, anillos=3)
    _caja(mb, P((0.0, 0.0, zb + 2.0)), (7.4, 0.26, 0.05), m_negro, rz=rz + 0.35)
    _caja(mb, P((0.0, 0.0, zb + 2.0)), (7.4, 0.26, 0.05), m_negro, rz=rz + 0.35 + 1.5708)
    # patines
    for s in (-1, 1):
        _cil(mb, P((-1.6, s * 0.95, 0.06)), P((1.9, s * 0.95, 0.06)), 0.06, 0.06, m_acero, seg=6)
        _cil(mb, P((1.9, s * 0.95, 0.06)), P((2.25, s * 0.95, 0.40)), 0.06, 0.04, m_acero, seg=6)
        for xk in (-0.9, 0.9):
            _cil(mb, P((xk, s * 0.95, 0.06)), P((xk, s * 0.75, zb + 0.35)), 0.05, 0.05, m_acero, seg=5)


def _piscina(mb, c, sx, sy, m_borde, m_agua, m_cub, alto=0.55):
    """Piscina elevada: brocal blanco, lamina de agua turquesa y escalerilla."""
    e = 0.35
    for s in (-1, 1):
        _caja(mb, (c[0], c[1] + s * (sy / 2.0 + e / 2.0), c[2] + alto / 2.0), (sx + 2 * e, e, alto), m_borde)
        _caja(mb, (c[0] + s * (sx / 2.0 + e / 2.0), c[1], c[2] + alto / 2.0), (e, sy, alto), m_borde)
    for s in (-1, 1):                       # brocal de teca (marco, no tapa)
        _caja(mb, (c[0], c[1] + s * (sy / 2.0 + e / 2.0), c[2] + alto + 0.02), (sx + 2 * e, e, 0.04), m_cub)
        _caja(mb, (c[0] + s * (sx / 2.0 + e / 2.0), c[1], c[2] + alto + 0.02), (e, sy, 0.04), m_cub)
    # hueco del agua: recorte simulado (lamina hundida 0.15 m + paredes interiores)
    z_ag = c[2] + alto - 0.15
    x0, x1, y0, y1 = c[0] - sx / 2.0, c[0] + sx / 2.0, c[1] - sy / 2.0, c[1] + sy / 2.0
    zt = c[2] + alto + 0.04
    verts = [(x0, y0, z_ag), (x1, y0, z_ag), (x1, y1, z_ag), (x0, y1, z_ag),
             (x0, y0, zt), (x1, y0, zt), (x1, y1, zt), (x0, y1, zt)]
    _lamina(mb, verts, [(0, 1, 2, 3)], m_agua, (0, 0, 1))
    paredes = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    fs = _orientar_cada(verts, paredes, lambda q: (c[0] - q[0], c[1] - q[1], 0.0))
    mb.add(verts, fs, m_borde)


def _spots_super(cs, L, xa1, xa2, xa3, z_t1, z_t2, lr):
    """Plazas (x, y, z, tipos, giro): popa estribor (cubierta principal,
    z=cs.zd), cubierta superior, sun deck y una plaza a babor de popa
    (todas con |y| + 2.3 <= semiancho util del piso)."""
    spots = []
    x = xa1 - 1.5
    while x - 0.95 > -L / 2.0 + 0.55 * lr and len(spots) < 3:    # popa, 1a fila
        spots.append((x, 2.3, cs.zd(x), ("sedan", "deportivo", "familiar"), 0.0))
        x -= 2.4
    x, k = xa2 - 1.6, 0
    while x - 0.95 > xa1 + 0.6 and k < 4:                        # cubierta superior
        spots.append((x, 3.0, z_t1, ("deportivo", "compacto", "sedan"), 0.0))
        x -= 2.3
        k += 1
    x, k = xa3 - 1.5, 0
    while x - 0.95 > xa2 + 0.6 and k < 3:                        # sun deck
        spots.append((x, 0.5, z_t2, ("compacto", "deportivo", "topolino"), 0.0))
        x -= 2.2
        k += 1
    x = xa1 - 1.5
    if x - 0.95 > -L / 2.0 + lr + 3.6:                           # popa, babor
        spots.append((x, -3.0, cs.zd(x), ("compacto", "topolino"), 0.0))
    return spots


def build_superyate(parent_collection, eslora=70.0, seed=0, con_publico=True, **params):
    """Megayate de 3 pisos con helipuerto en proa, mini helicoptero, piscina
    en la cubierta superior y 9-12 coches VIP (Empty YATE_super)."""
    n_coches = params.pop("n_coches", None)
    con_pasarela = params.pop("pasarela", True)
    if params:
        raise TypeError("build_superyate() no admite %s" % sorted(params))
    rng = random.Random(7919 * int(seed) + 977)
    L = float(eslora)
    B, D, F, z_cub = _dims(L)
    cs = _Casco(L, B, D, F, z_cub, n_est=26, arrufo=0.18, rake=0.055 * L)
    m_casco, m_franja, m_obra = _mat("casco"), _mat("franja"), _mat("obra_viva")
    m_cub, m_cristal, m_acero = _mat("cubierta"), _mat("cristal"), _mat("acero")
    m_blanco, m_crema, m_azul = _mat("blanco"), _mat("crema"), _mat("azul")
    root = _empty("%s_super" % PREFIX, parent_collection, size=4.0)

    mb = _MB()
    _construir_casco(mb, cs, m_casco, m_franja, m_obra, m_cub)
    zp = _popa(mb, cs, m_casco, m_cub, m_acero)
    lr = max(1.2, (z_cub - zp) * 1.8)
    _ojos_de_buey(mb, cs, m_cristal, n=10, t0=0.10, t1=0.70, frac=0.22)
    _ojos_de_buey(mb, cs, m_cristal, n=8, t0=0.14, t1=0.62, frac=0.62)
    _cinta(mb, cs, lambda t: cs.z_deck(t) - 0.12, _mat("cinta"), alto=0.12)
    ob = mb.build("%s_super_casco" % PREFIX, parent_collection)
    ob.parent = root

    # ---- 3 pisos (el salon ocupa el 58% de la eslora) + hardtop + radar
    mb = _MB()
    xa1, xb1 = -0.34 * L, 0.24 * L
    yh1 = lambda x: max(1.0, cs.w_cub(cs.t_de_x(x)) - 0.70)
    z_c1 = cs.zd(xa1) - 0.02
    z_t1, _c = _cabina(mb, xa1, xb1, yh1, z_c1, 2.9, m_casco, m_cristal, rake=1.0,
                       cristal=(0.38, 0.84), visera=0.45, chaflan=0.8, seg_frente=10)
    xa2, xb2 = -0.16 * L, xb1 - 0.05 * L
    yh2 = lambda x: max(0.9, yh1(x) - 0.55)
    z_t2, _c = _cabina(mb, xa2, xb2, yh2, z_t1, 2.7, m_casco, m_cristal, rake=1.3,
                       cristal=(0.36, 0.86), visera=0.55, chaflan=0.7, seg_frente=10)
    xa3, xb3 = -0.02 * L, xb2 - 0.05 * L
    yh3 = lambda x: max(0.8, yh2(x) - 0.55)
    z_t3, _c = _cabina(mb, xa3, xb3, yh3, z_t2, 2.5, m_casco, m_cristal, rake=1.5,
                       cristal=(0.34, 0.88), visera=0.65, chaflan=0.6, seg_frente=10)
    lx = 0.07 * L
    _caja(mb, (xa3 - lx / 2.0 + 0.2, 0.0, z_t3 - 0.06), (lx + 0.4, 2.0 * (yh3(xa3) + 0.6), 0.12), m_casco)
    for s in (-1, 1):
        _cil(mb, (xa3 - lx + 0.5, s * (yh2(xa2 + 1.0) - 0.35), z_t2),
             (xa3 - lx + 0.55, s * (yh3(xa3) + 0.4), z_t3 - 0.12), 0.07, 0.06, m_casco, seg=6)
    _mastil_radar(mb, xa3 + 0.55 * (xb3 - xa3), 0.0, z_t3, math.sqrt(L / 32.0), m_casco, m_acero, _mat("gris"))
    # helipuerto elevado en proa (plataforma de 0.55 m sobre la cubierta) + helicoptero
    x_h = 0.34 * L
    t_h = cs.t_de_x(x_h)
    r_h = cs.w_cub(t_h) - 0.6
    z_h = _helipuerto(mb, (x_h, 0.0, cs.z_deck(t_h) - 0.30), r_h, _mat("helipuerto"), m_blanco,
                      alto=(F - z_cub) + 0.25)      # superficie 5 cm bajo la regala
    ob = mb.build("%s_super_cabina" % PREFIX, parent_collection)
    ob.parent = root
    mb = _MB()
    _helicoptero(mb, (x_h + 0.2, 0.0, z_h), _mat("burdeos"), m_cristal, m_acero, _mat("negro"), m_crema, rz=0.35)
    ob = mb.build("%s_super_helicoptero" % PREFIX, parent_collection)
    ob.parent = root

    # ---- detalles
    mb = _MB()
    for s in (-1, 1):
        pts = [(x, s * w, zt) for (x, w, zt) in cs.anillos if 0.02 <= cs.t_de_x(x) <= 0.96]
        _barandilla(mb, pts, 0.95, m_acero, paso=1.4)
    _rail_flybridge(mb, xa1, xa2 - 0.3, yh1, 0.8, z_t1, m_acero)
    _rail_flybridge(mb, xa2, xa3 - 0.3, yh2, 0.7, z_t2, m_acero)
    _defensas(mb, cs, _mat("defensa"), m_acero, lado=1, ts=(0.08, 0.20, 0.34, 0.48, 0.62, 0.76, 0.88))
    _bandera(mb, (-L / 2.0 + 0.6, -(cs.w(0.0) - 0.9), cs.z_top(0.0)), 2.8, m_acero,
             _mat("verde_bandera"), m_blanco, _mat("rojo_bandera"), ancho=1.2, alto_b=0.8)
    # piscina y tumbonas a babor de la cubierta superior; sombrillas
    _piscina(mb, (xa1 + 4.4, -1.2, z_t1), 4.2, 2.6, m_blanco, _mat("agua_piscina"), m_cub)
    y_tumb = -(yh1(xa1) - 1.3)
    for k in range(3):
        _tumbona(mb, (xa1 + 3.4 + 1.0 * k, y_tumb, z_t1), 0.0, m_blanco, m_crema)
    _sombrilla(mb, (xa1 + 2.2, y_tumb - 0.5, z_t1), m_acero, m_crema, m_azul, r=1.4)
    _sombrilla(mb, (xa1 + 6.6, y_tumb - 0.5, z_t1), m_acero, m_crema, m_azul, r=1.3)
    # sun deck: tumbonas a babor
    for k in range(2):
        _tumbona(mb, (xa2 + 1.2 + 1.0 * k, -(yh2(xa2) - 1.2), z_t2), 0.0, m_blanco, m_crema)
    _sombrilla(mb, (xa2 + 3.4, -(yh2(xa2) - 1.4), z_t2), m_acero, m_crema, m_azul, r=1.3)
    # popa a babor (todo dentro de w_cub ~ 5.8): mesas altas, sombrilla, mayordomo
    x_tab = -L / 2.0 + lr + 1.4
    _mesa_alta(mb, (x_tab, -1.2, cs.zd(x_tab)), m_blanco, m_acero, _mat("champan"), _mat("negro"), copas=4)
    _mesa_alta(mb, (x_tab + 2.2, -4.9, cs.zd(x_tab + 2.2)), m_blanco, m_acero, _mat("champan"),
               _mat("negro"), copas=3)
    _sombrilla(mb, (x_tab + 1.0, -3.6, cs.zd(x_tab + 1.0)), m_acero, m_crema, m_azul, r=1.5, alto=2.5)
    if con_pasarela:
        tp = cs.t_de_x(-0.40 * L)
        A = (cs.x(tp), cs.w(tp) + 0.05, cs.z_top(tp) + 0.02)
        _pasarela(mb, A, (A[0] - 7.5, cs.w(tp) + 2.1, 0.95), m_blanco, _mat("alfombra"), m_acero, ancho=1.2)
    if con_publico:
        spots = _spots_super(cs, L, xa1, xa2, xa3, z_t1, z_t2, lr)
        n = min(len(spots), max(1, n_coches if n_coches is not None else rng.randint(9, 12)))
        cols = _colores_vip(rng, n)
        for i in range(n):
            x, y, z, tipos, giro = spots[i]
            _coche_vip(parent_collection, root, (x, y, z), rng.choice(tipos), cols[i],
                       seed * 100 + i, rng, giro=giro)
        _mayordomo(parent_collection, root, mb, (x_tab + 1.2, -2.6, cs.zd(x_tab + 1.2)),
                   seed * 100 + 60, rng)
    ob = mb.build("%s_super_detalles" % PREFIX, parent_collection)
    ob.parent = root
    root["eslora"] = L
    return root


# ---------------------------------------------------------------------------
# LANCHA RAPIDA (estilo Riva: casco de caoba barnizada, cubierta crema)
# ---------------------------------------------------------------------------
def build_lancha(parent_collection, eslora=9.0, seed=0, **params):
    """Lancha rapida estilo Riva (Empty YATE_lancha; hijos YATE_lancha_casco,
    YATE_lancha_detalles + COCHE_*). Cockpit crema a z_cub con el suelo
    plano; cubierta de proa de caoba a la altura de la regala; parabrisas
    curvo y consola con volante POR DELANTE del morro del coche; tapa de
    motor corta a popa. Distribucion (L=9, x en metros): tapa de motor
    [-4.35, -3.65] | banco trasero (solo con 1 coche) x=-2.45 | coches
    (1: en x=+0.3, topolino o compacto; 2: dos topolinos en x=-2.05 y
    +1.0) | consola [2.75, 3.15] | parabrisas base en x~3.5.
    params: n_coches (1..2; por defecto 1 dos de cada tres veces)."""
    n_coches = params.pop("n_coches", None)
    if params:
        raise TypeError("build_lancha() no admite %s" % sorted(params))
    rng = random.Random(7919 * int(seed) + 313)
    L = float(eslora)
    s = L / 9.0
    B, D, F, z_cub = 2.85 * s, 0.70 * s, 0.85 * s, 0.58 * s
    cs = _Casco(L, B, D, F, z_cub, n_est=12, arrufo=0.35, rake=0.03 * L, planta=3.2, k_deck=0.0)
    m_caoba, m_blanco, m_crema = _mat("caoba"), _mat("blanco"), _mat("crema")
    m_cristal, m_acero, m_negro = _mat("cristal"), _mat("acero"), _mat("negro")
    root = _empty("%s_lancha" % PREFIX, parent_collection, size=1.5)
    n = n_coches if n_coches is not None else rng.choice((1, 1, 2))
    n = max(1, min(2, int(n)))
    x_fore = 3.3 * s                     # de aqui a proa, cubierta de caoba cerrada
    mb = _MB()
    _construir_casco(mb, cs, m_caoba, m_blanco, _mat("obra_viva"), m_crema,
                     zs_top=0.10 * s, zs_bot=-0.08 * s)
    # cubierta de proa (lamina de caoba a la altura de la regala, sigue el arrufo)
    ts_f = [t for t in cs.ts if cs.x(t) >= x_fore - 0.01]
    ts_f = [cs.t_de_x(x_fore)] + ts_f
    verts, faces = [], []
    for t in ts_f:
        x, wi, zt = cs.x_rake(t, cs.z_top(t)), cs.w_cub(t) + 0.02, cs.z_top(t) - 0.02
        verts.extend([(x, -wi, zt), (x, wi, zt)])
    for i in range(len(ts_f) - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    _lamina(mb, verts, faces, m_caoba, (0, 0, 1), smooth=True)
    _caja(mb, (x_fore - 0.05 * s, 0.0, (cs.z_top(cs.t_de_x(x_fore)) + z_cub) / 2.0),
          (0.10 * s, 2.0 * cs.w_cub(cs.t_de_x(x_fore)) + 0.04, cs.z_top(cs.t_de_x(x_fore)) - z_cub), m_caoba)
    # tapa de motor (popa) hasta 2 cm bajo la regala
    zt0 = cs.z_top(0.0)
    _caja_base(mb, -4.0 * s, 0.0, z_cub - 0.01, 0.70 * s, 2.0 * cs.w_cub(cs.t_de_x(-4.0 * s)) + 0.02,
               zt0 - 0.02 - z_cub, m_caoba)
    # consola de caoba con volante cromado (cara de popa, inclinado)
    xc = 2.95 * s
    _caja_base(mb, xc, 0.0, z_cub, 0.40 * s, 1.5 * s, 0.44 * s, m_caoba)
    _cil(mb, (xc - 0.15 * s, -0.35 * s, z_cub + 0.42 * s), (xc - 0.32 * s, -0.35 * s, z_cub + 0.58 * s),
         0.02 * s, 0.02 * s, m_acero, seg=5)
    _cil(mb, (xc - 0.32 * s, -0.35 * s, z_cub + 0.58 * s), (xc - 0.345 * s, -0.35 * s, z_cub + 0.60 * s),
         0.18 * s, 0.18 * s, m_acero, seg=10)
    ob = mb.build("%s_lancha_casco" % PREFIX, parent_collection)
    ob.parent = root

    mb = _MB()
    # parabrisas curvo (banda doble cara) con marco cromado sobre la cubierta de proa
    xw, NW = 3.5 * s, 6
    tw = cs.t_de_x(xw)
    wb = cs.w_cub(tw) - 0.06
    zw = cs.z_top(tw) - 0.02
    base, top = [], []
    for k in range(NW + 1):
        f = k / float(NW)
        y = -wb + 2.0 * wb * f
        curva = 0.30 * s * (1.0 - (y / wb) ** 2)
        base.append((xw + curva - 0.30 * s, y, zw))
        top.append((xw + curva - 0.52 * s, y * 0.96, zw + 0.50 * s))
    verts = base + top
    faces = [(k, k + 1, NW + 2 + k, NW + 1 + k) for k in range(NW)]
    _lamina(mb, verts, faces, _mat("cristal_claro"), (1, 0, 0), doble=True, smooth=True)
    for a, b in zip(top[:-1], top[1:]):
        _cil(mb, a, b, 0.02 * s, 0.02 * s, m_acero, seg=4, tapas=False)
    for p, q in ((base[0], top[0]), (base[-1], top[-1])):
        _cil(mb, p, q, 0.02 * s, 0.02 * s, m_acero, seg=4)
    # banco trasero de cuero crema (solo si el cockpit no lo ocupa un 2o coche)
    if n == 1:
        xs_ = -2.45 * s
        wb_ = 2.0 * cs.w_cub(cs.t_de_x(xs_))
        _caja(mb, (xs_, 0.0, z_cub + 0.12 * s), (0.65 * s, wb_ - 0.30, 0.24 * s), m_crema)
        _caja(mb, (xs_ - 0.28 * s, 0.0, z_cub + 0.40 * s), (0.12 * s, wb_ - 0.40, 0.36 * s), m_crema)
    # cornamusas y bandera
    for t in (0.12, 0.80):
        for sg in (-1, 1):
            _caja(mb, (cs.x(t), sg * (cs.w(t) - 0.10), cs.z_top(t) + 0.04), (0.22 * s, 0.06 * s, 0.06 * s), m_acero)
    _bandera(mb, (-L / 2.0 + 0.25 * s, 0.0, zt0 - 0.03), 0.9 * s, m_acero,
             _mat("verde_bandera"), m_blanco, _mat("rojo_bandera"), ancho=0.5 * s, alto_b=0.34 * s)
    ob = mb.build("%s_lancha_detalles" % PREFIX, parent_collection)
    ob.parent = root
    # coches mirando a +X (proa): 1 -> centrado; 2 -> dos topolinos en fila
    cols = _colores_vip(rng, 2)
    if n == 1:
        plazas = [(0.30 * s, rng.choice(("topolino", "compacto")) if s >= 1.0 else "topolino")]
    else:
        plazas = [(1.0 * s, "topolino"), (-2.05 * s, "topolino")]
    for i, (x, tipo) in enumerate(plazas):
        _coche_vip(parent_collection, root, (x, 0.0, z_cub + 0.01), tipo, cols[i],
                   seed * 100 + 70 + i, rng, giro=-math.pi / 2.0)
    root["eslora"] = L
    return root


# ---------------------------------------------------------------------------
# PANTALAN VIP
# ---------------------------------------------------------------------------
def _letras_vip(mb, c, sx, alto, m, grosor=0.05):
    """Letras V I P (cajas) en el plano YZ centradas en c, legibles desde
    sx*X: vistas desde x>0 (sx=+1) el texto avanza hacia +Y y vistas desde
    x<0 (sx=-1) hacia -Y (u se espeja y con el las inclinaciones de la V)."""
    h, e = alto, 0.16 * alto
    x = c[0] + sx * grosor / 2.0
    off = -0.53 * h

    def caja(u, v, su, sv, rx=0.0):
        _caja(mb, (x, c[1] + sx * (u + off), c[2] + v), (grosor, su, sv), m, rx=sx * rx)
    lv = math.hypot(0.3 * h, h)
    av = math.atan2(0.3 * h, h)
    # V: rx>0 lleva la parte alta de la caja hacia -y (izquierda vista desde +X)
    caja(-0.15 * h, 0.0, e, lv, rx=av)           # trazo izquierdo '\'
    caja(0.15 * h, 0.0, e, lv, rx=-av)           # trazo derecho '/'
    caja(0.58 * h, 0.0, e, h)                     # I
    caja(0.94 * h, 0.0, e, h)                     # P
    caja(1.11 * h, 0.42 * h, 0.50 * h, e)
    caja(1.11 * h, 0.02 * h, 0.50 * h, e)
    caja(1.28 * h, 0.22 * h, e, 0.44 * h)


def build_pantalan_vip(parent_collection, largo=60.0, seed=0, z_cubierta=0.9, **params):
    """Pantalan flotante VIP a lo largo de +X (x en [0, largo], y en
    [-1.8, 1.8]), origen en el extremo x=0 a nivel del mar; superficie a
    z=z_cubierta. Empty YATE_pantalan; hijos YATE_pantalan_cuerpo y
    YATE_pantalan_detalles."""
    if params:
        raise TypeError("build_pantalan_vip() no admite %s" % sorted(params))
    rng = random.Random(7919 * int(seed) + 555)
    Lg, W, zc = float(largo), 3.6, float(z_cubierta)
    m_cub, m_blanco, m_alf = _mat("cubierta"), _mat("blanco"), _mat("alfombra")
    m_dor, m_cord, m_neg = _mat("dorado"), _mat("cordon"), _mat("negro")
    m_farol, m_terra, m_hoja = _mat("farol"), _mat("terracota"), _mat("hoja")
    root = _empty("%s_pantalan" % PREFIX, parent_collection, size=2.0)
    mb = _MB()
    _caja(mb, (Lg / 2.0, 0.0, zc - 0.06), (Lg, W, 0.12), m_cub)
    _caja(mb, (Lg / 2.0, 0.0, zc - 0.12 - 0.19), (Lg - 0.2, W - 0.3, 0.38), m_blanco)
    n_fl = max(2, int(Lg / 4.0))
    for k in range(n_fl):
        x = (k + 0.5) * Lg / n_fl
        for sg in (-1, 1):
            _caja(mb, (x, sg * 1.05, -0.05), (1.6, 1.3, 1.0), _mat("defensa"))
    _caja(mb, (Lg / 2.0, 0.0, zc + 0.012), (Lg - 1.0, 1.5, 0.024), m_alf)
    ob = mb.build("%s_pantalan_cuerpo" % PREFIX, parent_collection)
    ob.parent = root

    mb = _MB()
    # cordon de terciopelo con postes dorados cada 3 m en ambos bordes
    n_p = max(2, int(round(Lg / 3.0)) + 1)
    for sg in (-1, 1):
        tops = []
        for k in range(n_p):
            x = 0.6 + (Lg - 1.2) * k / (n_p - 1)
            y = sg * 1.55
            _cil(mb, (x, y, zc), (x, y, zc + 0.03), 0.17, 0.17, m_dor, seg=8)
            _cil(mb, (x, y, zc + 0.03), (x, y, zc + 0.95), 0.035, 0.03, m_dor, seg=6)
            _elipsoide(mb, (x, y, zc + 1.0), 0.07, 0.07, 0.07, m_dor, seg=6, anillos=3)
            tops.append((x, y, zc + 0.93))
        for a, b in zip(tops[:-1], tops[1:]):
            pts = []
            for k in range(4):
                f = k / 3.0
                pts.append((_lerp(a[0], b[0], f), _lerp(a[1], b[1], f) + sg * 0.03,
                            a[2] - 0.22 * 4.0 * f * (1.0 - f)))
            for p, q in zip(pts[:-1], pts[1:]):
                _cil(mb, p, q, 0.03, 0.03, m_cord, seg=5, tapas=False)
    # farolillos cada 6 m (alternando lado) y jardineras con limoneros
    k = 0
    x = 2.0
    while x < Lg - 1.0:
        sg = 1 if k % 2 == 0 else -1
        _cil(mb, (x, sg * 1.62, zc), (x, sg * 1.62, zc + 2.4), 0.045, 0.035, m_neg, seg=6)
        _caja(mb, (x, sg * 1.62, zc + 2.62), (0.34, 0.34, 0.44), m_farol)
        _caja(mb, (x, sg * 1.62, zc + 2.87), (0.46, 0.46, 0.06), m_neg)
        _caja(mb, (x, sg * 1.62, zc + 2.40), (0.40, 0.40, 0.04), m_neg)
        _elipsoide(mb, (x, sg * 1.62, zc + 2.95), 0.05, 0.05, 0.07, m_neg, seg=5, anillos=2)
        xj = x + 3.0
        if xj < Lg - 1.0:
            _caja(mb, (xj, -sg * 1.45, zc + 0.28), (0.62, 0.62, 0.56), m_terra)
            _cil(mb, (xj, -sg * 1.45, zc + 0.56), (xj, -sg * 1.45, zc + 1.25), 0.05, 0.04, _mat("madera"), seg=5)
            _elipsoide(mb, (xj, -sg * 1.45, zc + 1.62), 0.55, 0.55, 0.52, m_hoja, seg=8, anillos=4)
            for j in range(4):
                th = TAU * j / 4.0 + rng.uniform(0.0, 1.0)
                _elipsoide(mb, (xj + 0.45 * math.cos(th), -sg * 1.45 + 0.45 * math.sin(th),
                                zc + 1.55 + 0.25 * math.sin(th * 2.0)), 0.07, 0.07, 0.09,
                           _mat("limon"), seg=5, anillos=2)
        x += 6.0
        k += 1
    # portal 'VIP' en x=0: dos pilastras + dintel azul marino con letras doradas
    for sg in (-1, 1):
        _caja(mb, (0.45, sg * 1.62, zc + 1.45), (0.30, 0.30, 2.9), m_blanco)
        _caja(mb, (0.45, sg * 1.62, zc + 2.92), (0.42, 0.42, 0.10), m_dor)
    _caja(mb, (0.45, 0.0, zc + 3.35), (0.30, 3.9, 0.85), _mat("franja"))
    _caja(mb, (0.45, 0.0, zc + 3.80), (0.40, 4.1, 0.08), m_dor)
    for sx in (-1, 1):
        _letras_vip(mb, (0.45 + sx * 0.15, 0.0, zc + 3.35), sx, 0.55, _mat("letras"))
    ob = mb.build("%s_pantalan_detalles" % PREFIX, parent_collection)
    ob.parent = root
    root["largo"] = Lg
    return root


# ---------------------------------------------------------------------------
# COCHES DE LUJO propios (limusina, cabrio): misma convencion que coches_kit_v2
#   frontal +Y, ruedas en z=0, ojos en el parabrisas, boca en el parachoques
# ---------------------------------------------------------------------------
def _seccion_coche(y, w, zb, zt, n=3.2, P=12):
    """Anillo (P puntos) de seccion rectangular redondeada en el plano XZ."""
    zc, hz = (zb + zt) / 2.0, (zt - zb) / 2.0
    pts = []
    for k in range(P):
        th = TAU * k / P + TAU / (2 * P)
        c, s = math.cos(th), math.sin(th)
        x = w * math.copysign(abs(c) ** (2.0 / n), c)
        z = zc + hz * math.copysign(abs(s) ** (2.0 / n), s)
        pts.append((x, y, z))
    return pts


def _cuerpo_coche(mb, estaciones, m_cuerpo):
    """Loft del cuerpo: estaciones [(y, w, zb, zt)] de atras a delante."""
    anillos = [_seccion_coche(y, w, zb, zt) for (y, w, zb, zt) in estaciones]
    _loft(mb, anillos, m_cuerpo, tapa_ini=True, tapa_fin=True, smooth=True)


def _rueda_lujo(mb, c, r, hw, m_neg, m_cromo, S=12):
    """Rueda de eje X: neumatico + llanta cromada hundida, apoyo en z=c[2]-r."""
    verts, faces, fm = [], [], []
    for xo in (-hw, hw):
        for k in range(S):
            th = -0.5 * math.pi + TAU * k / S
            verts.append((c[0] + xo, c[1] + r * math.cos(th), c[2] + r * math.sin(th)))
    for xo in (-hw, hw):
        for k in range(S):
            th = -0.5 * math.pi + TAU * k / S
            verts.append((c[0] + xo * 0.85, c[1] + 0.64 * r * math.cos(th), c[2] + 0.64 * r * math.sin(th)))
    ci = len(verts)
    verts.append((c[0] - hw * 1.02, c[1], c[2]))
    verts.append((c[0] + hw * 1.02, c[1], c[2]))
    for k in range(S):
        k2 = (k + 1) % S
        faces.append((k, k2, S + k2, S + k)); fm.append(m_neg)             # banda
        faces.append((k, 2 * S + k, 2 * S + k2, k2)); fm.append(m_neg)     # flanco -x
        faces.append((S + k, S + k2, 3 * S + k2, 3 * S + k)); fm.append(m_neg)
        faces.append((ci, 2 * S + k2, 2 * S + k)); fm.append(m_cromo)      # llanta -x
        faces.append((ci + 1, 3 * S + k, 3 * S + k2)); fm.append(m_cromo)
    mb.add(verts, faces, fm, smooth=True, recalc=True)


def _paso_rueda(mb, c, r, w, m_neg, seg=8):
    """Arco oscuro (medio anillo) en el flanco del coche alrededor de la rueda."""
    for sg in (-1, 1):
        x = sg * (w + 0.012)
        verts = []
        for k in range(seg + 1):
            th = math.pi * k / seg
            verts.append((x, c[1] + (r + 0.03) * math.cos(th), c[2] + (r + 0.03) * math.sin(th)))
            verts.append((x, c[1] + (r + 0.13) * math.cos(th), c[2] + (r + 0.13) * math.sin(th)))
        faces = [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(seg)]
        _lamina(mb, verts, faces, m_neg, (sg, 0, 0), smooth=True)


def _ojo(mb, c, u, v, n, ru, rv, mats, parpado=0.0, seg=12, mirada=(0.0, 0.0)):
    """Ojo de Cars sobre un plano: esclerotica, iris, pupila, brillo y
    parpado superior (fraccion cubierta). u/v/n unitarios (n = normal)."""
    m_blanco, m_iris, m_negro, m_parpado = mats

    def P(a, b, d):
        return (c[0] + u[0] * a + v[0] * b + n[0] * d, c[1] + u[1] * a + v[1] * b + n[1] * d,
                c[2] + u[2] * a + v[2] * b + n[2] * d)

    def disco(ca, cb, ra, rb, d, m, sg=seg):
        verts = [P(ca + ra * math.cos(TAU * k / sg), cb + rb * math.sin(TAU * k / sg), d) for k in range(sg)]
        _lamina(mb, verts, [tuple(range(sg))], m, n)
    disco(0.0, 0.0, ru, rv, 0.02, m_blanco)
    ia, ib = mirada[0] * ru * 0.35, mirada[1] * rv * 0.25
    disco(ia, ib, 0.52 * ru, 0.52 * rv, 0.032, m_iris)
    disco(ia, ib, 0.26 * ru, 0.26 * rv, 0.040, m_negro)
    disco(ia - 0.20 * ru, ib + 0.22 * rv, 0.11 * ru, 0.11 * rv, 0.046, m_blanco, sg=6)
    if parpado > 0.0:
        b0 = rv * (1.0 - 2.0 * parpado)
        a_lim = math.asin(max(-1.0, min(1.0, b0 / rv)))
        verts = []
        NP = 8
        for k in range(NP + 1):
            th = a_lim + (math.pi - 2.0 * a_lim) * k / NP
            verts.append(P(1.04 * ru * math.cos(th), 1.04 * rv * math.sin(th), 0.05))
        _lamina(mb, verts, [tuple(range(NP + 1))], m_parpado, n)


def _boca_lujo(mb, yF, zc, xh, m_negro, m_cromo, m_blanco, sonrisa=0.07, dientes=True):
    """Boca sonriente en el plano y=yF: hueco oscuro, dientes y labio cromado."""
    N = 8
    top, bot, lip, teeth = [], [], [], []
    for k in range(N + 1):
        x = -xh + 2.0 * xh * k / N
        q = (x / xh) ** 2
        top.append((x, yF + 0.02, zc + 0.07 + sonrisa * q))
        bot.append((x, yF + 0.02, zc - 0.05 + 0.4 * sonrisa * q))
        lip.append((x, yF + 0.025, zc - 0.08 + 0.4 * sonrisa * q))
        teeth.append((x, yF + 0.025, zc + 0.035 + sonrisa * q))
    verts = top + bot
    faces = [(k, k + 1, N + 2 + k, N + 1 + k) for k in range(N)]
    _lamina(mb, verts, faces, m_negro, (0, 1, 0), smooth=True)
    verts = bot + lip
    _lamina(mb, verts, faces, m_cromo, (0, 1, 0), smooth=True)
    if dientes:
        verts = top + teeth
        verts = [(p[0], p[1] + 0.006, p[2]) for p in verts]
        _lamina(mb, verts, faces, m_blanco, (0, 1, 0), smooth=True)


def _cabina_coche(mb, anillos, tipos, m_cuerpo, m_cristal):
    """Cabina: anillos [(y, wb, wr, zb, zg, zr)] (zb=zg=zr -> anillo plano de
    base de luna). tipos: por banda, 'techo' (laterales de cristal, techo de
    color) o 'luna' (toda la banda de cristal salvo los pilares)."""
    rings = []
    for (y, wb, wr, zb, zg, zr) in anillos:
        rings.append([(-wb, y, zb), (-wr, y, zg), (-0.92 * wr, y, zr - 0.06 * (zr - zg > 0.01)),
                      (-0.6 * wr, y, zr), (0.6 * wr, y, zr), (0.92 * wr, y, zr - 0.06 * (zr - zg > 0.01)),
                      (wr, y, zg), (wb, y, zb)])
    P = 8
    verts = [p for r in rings for p in r]
    faces, fm = [], []
    for i in range(len(rings) - 1):
        for j in range(P - 1):
            faces.append((i * P + j, i * P + j + 1, (i + 1) * P + j + 1, (i + 1) * P + j))
            if j in (0, 6):
                fm.append(m_cuerpo)
            elif tipos[i] == "luna" or j in (1, 5):
                fm.append(m_cristal)
            else:
                fm.append(m_cuerpo)
    fs = _orientar_cada(verts, faces, lambda c: (c[0], 0.0, c[2] - 0.9))
    mb.add(verts, fs, fm, smooth=True)


def _ojos_en_luna(mb, y_top, z_top, y_bot, z_bot, sep, ru, rv, mats, parpado, rng, f=0.5):
    dy, dz = y_bot - y_top, z_top - z_bot
    ln = math.hypot(dy, dz)
    n = (0.0, dz / ln, dy / ln)
    v = (0.0, -dy / ln, dz / ln)
    mirada = (rng.uniform(-0.3, 0.3), rng.uniform(-0.2, 0.2))
    for sg in (-1, 1):
        c = (sg * sep, _lerp(y_top, y_bot, f), _lerp(z_top, z_bot, f))
        _ojo(mb, c, (1.0, 0.0, 0.0), v, n, ru, rv, mats, parpado=parpado, mirada=mirada)


def _detalles_coche(mb, w, yF, yR, zbump, m_cromo, m_faro, m_piloto, m_blanco, x_faro, z_faro, r_faro):
    _caja(mb, (0.0, yF - 0.02, zbump), (2.0 * w * 0.94, 0.16, 0.13), m_cromo)
    _caja(mb, (0.0, yR + 0.02, zbump), (2.0 * w * 0.94, 0.16, 0.13), m_cromo)
    for sg in (-1, 1):
        _elipsoide(mb, (sg * x_faro, yF - 0.05, z_faro), r_faro[0], r_faro[1], r_faro[2], m_faro, seg=10, anillos=4)
        _caja(mb, (sg * (x_faro - 0.02), yR + 0.02, z_faro), (0.22, 0.06, 0.10), m_piloto)
    _caja(mb, (0.0, yR + 0.01, zbump + 0.17), (0.36, 0.03, 0.14), m_blanco)


def _limusina(mb, m_cuerpo, ck, rng):
    m_cristal, m_neg, m_cromo = ck._mat("cristal"), ck._mat("negro"), ck._mat("cromo")
    m_blanco = ck._mat("blanco")
    m_iris = ck._mat(rng.choice(("iris_azul", "iris_marron", "iris_verde")))
    _cuerpo_coche(mb, [(-3.80, 0.62, 0.42, 0.78), (-3.62, 0.82, 0.30, 0.94), (-3.20, 0.88, 0.26, 0.98),
                       (-1.20, 0.90, 0.26, 1.00), (1.20, 0.90, 0.26, 1.00), (2.90, 0.88, 0.26, 0.96),
                       (3.45, 0.84, 0.28, 0.90), (3.68, 0.76, 0.33, 0.82), (3.80, 0.60, 0.40, 0.72)], m_cuerpo)
    zb = 0.975
    _cabina_coche(mb, [(-2.55, 0.86, 0.80, zb, zb, zb), (-2.05, 0.86, 0.74, zb, 1.36, 1.46),
                       (1.35, 0.86, 0.74, zb, 1.36, 1.46), (1.85, 0.86, 0.80, zb, zb, zb)],
                  ["luna", "techo", "luna"], m_cuerpo, m_cristal)
    _ojos_en_luna(mb, 1.35, 1.46, 1.85, zb, 0.27, 0.19, 0.22, (m_blanco, m_iris, m_neg, m_cuerpo),
                  0.30, rng, f=0.48)
    _boca_lujo(mb, 3.80, 0.53, 0.40, m_neg, m_cromo, m_blanco, sonrisa=rng.uniform(0.06, 0.09),
               dientes=rng.random() < 0.6)
    _detalles_coche(mb, 0.90, 3.80, -3.80, 0.33, m_cromo, ck._mat("faro"), ck._mat("piloto"), m_blanco,
                    0.52, 0.64, (0.13, 0.10, 0.08))
    for (y, r) in ((-2.40, 0.33), (2.50, 0.33)):
        for sg in (-1, 1):
            _rueda_lujo(mb, (sg * 0.88, y, r), r, 0.11, m_neg, m_cromo)
        _paso_rueda(mb, (0.0, y, r), r, 0.90, m_neg)
    for y in (-1.15, -0.05, 1.05):                       # pilares laterales
        for sg in (-1, 1):
            _caja(mb, (sg * 0.815, y, 1.165), (0.04, 0.09, 0.40), m_cuerpo, ry=sg * 0.30)
    for y in (-1.7, -0.5, 0.6):                          # manillas cromadas
        for sg in (-1, 1):
            _caja(mb, (sg * 0.905, y, 0.86), (0.02, 0.16, 0.035), m_cromo)
    _elipsoide(mb, (0.0, 3.50, 0.93), 0.05, 0.10, 0.06, _mat("dorado"), seg=6, anillos=3)
    _cil(mb, (0.55, -2.3, 1.45), (0.62, -2.45, 1.85), 0.012, 0.008, m_cromo, seg=4)


def _cabrio(mb, m_cuerpo, ck, rng):
    m_cristal, m_neg, m_cromo = ck._mat("cristal"), ck._mat("negro"), ck._mat("cromo")
    m_blanco, m_cuero = ck._mat("blanco"), _mat("cuero")
    m_iris = ck._mat(rng.choice(("iris_azul", "iris_marron", "iris_verde")))
    _cuerpo_coche(mb, [(-2.35, 0.60, 0.40, 0.74), (-2.20, 0.82, 0.28, 0.90), (-1.80, 0.88, 0.25, 0.94),
                       (-0.60, 0.90, 0.25, 0.95), (0.80, 0.90, 0.25, 0.93), (1.80, 0.88, 0.25, 0.88),
                       (2.15, 0.82, 0.28, 0.82), (2.30, 0.68, 0.34, 0.74), (2.35, 0.55, 0.40, 0.68)], m_cuerpo)
    # parabrisas curvo con marco cromado
    NW, wb, wt = 6, 0.80, 0.72
    base, top = [], []
    for k in range(NW + 1):
        f = k / float(NW)
        xb, xt = -wb + 2.0 * wb * f, -wt + 2.0 * wt * f
        cb = 0.10 * (1.0 - (xb / wb) ** 2)
        base.append((xb, 0.65 + cb, 0.93))
        top.append((xt, 0.40 + cb, 1.40))
    verts = base + top
    faces = [(k, k + 1, NW + 2 + k, NW + 1 + k) for k in range(NW)]
    _lamina(mb, verts, faces, m_cristal, (0, 1, 0.5), doble=True, smooth=True)
    for a, b in zip(top[:-1], top[1:]):
        _cil(mb, a, b, 0.022, 0.022, m_cromo, seg=4, tapas=False)
    for p, q in ((base[0], top[0]), (base[-1], top[-1])):
        _cil(mb, p, q, 0.025, 0.022, m_cromo, seg=5)
    _ojos_en_luna(mb, 0.50, 1.40, 0.75, 0.93, 0.30, 0.19, 0.18, (m_blanco, m_iris, m_neg, m_cuerpo),
                  0.12, rng, f=0.5)
    # habitaculo: suelo oscuro, dos asientos de cuero, capota plegada
    _caja(mb, (0.0, -0.55, 0.985), (1.50, 2.10, 0.10), _mat("interior"))
    for sg in (-1, 1):
        _caja(mb, (sg * 0.40, -0.30, 1.10), (0.56, 0.60, 0.16), m_cuero)
        _caja(mb, (sg * 0.40, -0.72, 1.30), (0.56, 0.14, 0.52), m_cuero, rx=0.18)
        _elipsoide(mb, (sg * 0.96, 0.55, 1.03), 0.07, 0.05, 0.05, m_cromo, seg=6, anillos=3)
        _caja(mb, (sg * 0.905, -0.1, 0.60), (0.02, 3.2, 0.05), m_cromo)
    _caja(mb, (0.0, -1.50, 1.06), (1.56, 0.62, 0.24), _mat("crema"))
    _boca_lujo(mb, 2.35, 0.51, 0.36, m_neg, m_cromo, m_blanco, sonrisa=rng.uniform(0.06, 0.09),
               dientes=rng.random() < 0.7)
    _detalles_coche(mb, 0.90, 2.35, -2.35, 0.32, m_cromo, ck._mat("faro"), ck._mat("piloto"), m_blanco,
                    0.50, 0.60, (0.12, 0.10, 0.09))
    for (y, r) in ((-1.45, 0.32), (1.50, 0.32)):
        for sg in (-1, 1):
            _rueda_lujo(mb, (sg * 0.88, y, r), r, 0.12, m_neg, m_cromo)
        _paso_rueda(mb, (0.0, y, r), r, 0.90, m_neg)


def build_coche_lujo(parent_collection, tipo="limusina", seed=0, color=None, **params):
    """Coche de lujo COCHE_lujo_<tipo> (limusina | deportivo | cabrio) con
    cara de Cars: frontal +Y, ruedas en z=0, origen en el centro de la base."""
    if params:
        raise TypeError("build_coche_lujo() no admite %s" % sorted(params))
    if tipo not in TIPOS_LUJO:
        raise ValueError("tipo debe ser uno de %s" % (TIPOS_LUJO,))
    rng = random.Random(7919 * int(seed) + 11 * TIPOS_LUJO.index(tipo) + 5)
    ck = _coches()
    if color is None:
        color = rng.choice(COLORES_LUJO)[1]
    nombre = "COCHE_lujo_%s" % tipo
    if tipo == "deportivo":
        ob = ck.build_coche(parent_collection, tipo="deportivo", color=color, seed=seed,
                            expresion=rng.choice(("feliz", "abierto")), baca=False, bitono=False,
                            franjas=False, carga=False)
        ob.name = nombre
        ob.data.name = nombre
        return ob
    mb = _MB()
    m_cuerpo = _mat_color(color, rough=0.22)
    (_limusina if tipo == "limusina" else _cabrio)(mb, m_cuerpo, ck, rng)
    return mb.build(nombre, parent_collection)


# ---------------------------------------------------------------------------
# ESCAPARATE
# ---------------------------------------------------------------------------
def build_agua(parent_collection, lado=2500.0, nombre="YATE_agua"):
    """Plano de mar turquesa (lado x lado) a z=-0.01 con rizado procedural."""
    mb = _MB()
    h = lado / 2.0
    mb.add([(-h, -h, -0.01), (h, -h, -0.01), (h, h, -0.01), (-h, h, -0.01)],
           [(0, 1, 2, 3)], _mat("agua"), smooth=False)
    return mb.build(nombre, parent_collection)


def build(parent_collection, seed=0, agua=True, **params):
    """Escaparate (Empty YATE_escaparate): pantalan VIP de 150 m en y=0 (de
    x=0 a x=150), superyate + dos yates amarrados al sur del pantalan con
    estribor (+Y) hacia el, lancha navegando por delante (lado +Y, para que
    se vea desde la 'pista'), coches de lujo en el pantalan y plano de agua.
    La 'pista' estaria al norte (+Y): todo el publico mira a +Y."""
    if params:
        raise TypeError("build() no admite %s" % sorted(params))
    root = _empty("%s_escaparate" % PREFIX, parent_collection, size=5.0)
    pant = build_pantalan_vip(parent_collection, largo=150.0, seed=seed)
    pant.parent = root
    B, _D, _F, _z = _dims(70.0)
    sy = build_superyate(parent_collection, eslora=70.0, seed=seed)
    sy.parent = root
    sy.location = (40.0, -(B / 2.0 + 2.6), 0.0)      # popa en x=5: la pasarela cae en x~4.5
    B, _D, _F, _z = _dims(32.0)
    y1 = build_yate(parent_collection, eslora=32.0, seed=seed + 1)
    y1.parent = root
    y1.location = (97.0, -(B / 2.0 + 2.6), 0.0)
    B, _D, _F, _z = _dims(28.0)
    y2 = build_yate(parent_collection, eslora=28.0, seed=seed + 2, n_coches=5)
    y2.parent = root
    y2.location = (134.0, -(B / 2.0 + 2.6), 0.0)
    la = build_lancha(parent_collection, eslora=9.0, seed=seed)
    la.parent = root
    la.location = (70.0, 12.0, 0.0)
    la.rotation_euler = (0.0, 0.0, 0.30)
    for i, (tipo, x) in enumerate((("limusina", 14.0), ("deportivo", 50.0), ("cabrio", 100.0))):
        ob = build_coche_lujo(parent_collection, tipo=tipo, seed=seed + i)
        ob.parent = root
        ob.location = (x, 0.0, 0.9)
        ob.rotation_euler = (0.0, 0.0, -math.pi / 2.0)
    if agua:
        ag = build_agua(parent_collection)
        ag.parent = root
    return root
