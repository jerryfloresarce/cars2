"""coches_kit_v2.py - Coches-espectador estilo Cars 2 (Porto Corsa), version 2.

Kit procedural para Blender 5.1 (bpy puro + bmesh solo para recalcular
normales; sin bpy.ops, sin texturas). Cada coche es UNA malla:

  * carroceria por LOFT de secciones de 17 puntos a lo largo del coche (capo
    y maletero abombados; morro y cola que siguen en planta la misma
    superelipse que el parachoques) + CABINA como segundo loft de 9 puntos y
    7 lazos (luneta, techo abovedado con cantos caidos, parabrisas curvo),
  * pasos de rueda que SIGUEN el flanco real de la carroceria (banda oscura
    conformada + aleta de color cuya protuberancia se reduce hacia los
    extremos del arco), 4 ruedas (3 en el Ape) con neumatico, llanta y
    tapacubos cromado,
  * CARA de Cars: dos ojos grandes SIEMPRE visibles y simetricos sobre el
    parabrisas (esclerotica blanca, iris de color, pupila, brillo, parpados del
    color de la carroceria) y BOCA sonriente integrada en el parachoques
    delantero (hueco oscuro + labio inferior claro/cromado; algunas bocas
    abiertas con dientes y lengua, otras con 'dientes' de rejilla cromada).
    Los faros NO son ojos.
  * detalles: parachoques envolventes, faros, pilotos, intermitentes,
    retrovisores, manillas, matricula trasera, pilares, y por seed: baca con
    maleta, pintura bitono, franjas de carreras, aleron, rueda de repuesto...

Unidades en metros. Origen en el centro de la base (z=0 = apoyo de las
ruedas), frontal mirando a +Y. <= 3500 tris por coche.

MATERIALES (pensado para Assetto Corsa: pocos draw calls). Cada coche usa
<= 10 slots: MAT_COCHE_cuerpo_<HEX> (unico material por color) + los fijos
cristal, blanco (esclerotica, dientes, matricula, franjas, parachoques
pintado, techo claro, llanta clara), negro (neumaticos, pupila, boca, juntas,
pasos de rueda, caja, techo oscuro), cromo, iris_<azul|marron|verde>, faro
(faros, limones), piloto (pilotos, lengua, maleta roja), ambar
(intermitentes) y madera (equipaje/cajas). Una escena completa usa como mucho 10 colores de
carroceria + 11 materiales fijos. Al exportar a AC conviene ademas UNIR las
filas de coches por material.
Las laminas tipo 'decal' (boca, ojos, franjas, juntas) van separadas >= 1.5 cm
de la superficie para evitar z-fighting a distancia; los pilares son parches
con retornos (grosor), no laminas flotantes.

API (compatible con coches_kit.py):
  build_coche(parent_collection, tipo='compacto', color=(r,g,b), seed=0,
              expresion=None, boca=None, **opciones)
      tipo: 'topolino' | 'compacto' | 'sedan' | 'familiar' | 'deportivo' |
            'furgoneta' | 'pickup' | 'todoterreno' | 'ape'
            (alias antiguos: 'furgo' -> 'furgoneta'; 'compacto' y 'deportivo'
            siguen existiendo). El objeto se llama COCHE_<tipo pedido>.
      opciones (None/ausente = por seed): baca, bitono, franjas, carga (bool).
            Cualquier otra clave lanza TypeError.
      expresion: 'abierto' | 'feliz' | 'sorpresa' | None (por seed)
            (alias antiguos: 'sonrisa' -> 'feliz', 'guino' -> 'abierto';
            nunca se genera un guino ni un ojo tapado).
      boca: 'sonrisa' | 'abierta' | 'dientes' | 'rejilla' | None (por seed).
      Devuelve el objeto malla COCHE_<tipo>.
  build_fila_aparcada(parent_collection, n=6, seed=0)
      Fila de n coches lado a lado mirando a +Y, hijos del Empty COCHE_fila.
  build_muestrario(parent_collection, seed=0, paso=3.2)
      Los 9 tipos en fila (Empty COCHE_muestrario), para inspeccion.
  build(parent_collection, seed=0, **params)
      Muestra: build_fila_aparcada(n=params.get('n', 6)).
"""

import math
import random

import bpy
import bmesh

PREFIX = "COCHE"
TAU = 2.0 * math.pi

# ---------------------------------------------------------------------------
# Paleta plana (color lineal, roughness, metallic)
# ---------------------------------------------------------------------------
# Paleta CONSOLIDADA (11 materiales fijos + 1 por color de carroceria) para
# que cada coche tenga <= 10 slots (draw calls en Assetto Corsa):
#   blanco = esclerotica, brillo, dientes, matricula, franjas, parachoques
#            pintado, techo claro bitono, llanta clara
#   negro  = neumaticos, pupila, boca, juntas, pasos de rueda, caja, techo
#            oscuro bitono
#   piloto = pilotos, lengua, maleta roja      faro = faros, limones de la caja
_PALETA = {
    "cristal":   ((0.015, 0.050, 0.130), 0.08, 0.0),
    "blanco":    ((0.930, 0.930, 0.900), 0.30, 0.0),
    "negro":     ((0.030, 0.030, 0.034), 0.75, 0.0),
    "cromo":     ((0.800, 0.810, 0.820), 0.22, 1.0),
    "iris_azul":   ((0.030, 0.250, 0.750), 0.25, 0.0),
    "iris_marron": ((0.260, 0.110, 0.030), 0.25, 0.0),
    "iris_verde":  ((0.050, 0.420, 0.160), 0.25, 0.0),
    "faro":      ((1.000, 0.880, 0.560), 0.15, 0.0),
    "piloto":    ((0.800, 0.020, 0.020), 0.30, 0.0),
    "ambar":     ((1.000, 0.420, 0.020), 0.30, 0.0),
    "madera":    ((0.450, 0.250, 0.100), 0.80, 0.0),
}

COLORES_VIVOS = [
    ("rojo",     (0.80, 0.05, 0.04)),
    ("azul",     (0.04, 0.20, 0.70)),
    ("verde",    (0.06, 0.45, 0.12)),
    ("amarillo", (0.95, 0.68, 0.04)),
    ("morado",   (0.36, 0.09, 0.52)),
    ("crema",    (0.90, 0.84, 0.66)),
    ("naranja",  (0.95, 0.33, 0.03)),
    ("turquesa", (0.03, 0.55, 0.55)),
    ("celeste",  (0.35, 0.62, 0.90)),
    ("rosa",     (0.90, 0.30, 0.45)),
]


def _mat_nuevo(name, color, rough, metal):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    m.diffuse_color = (color[0], color[1], color[2], 1.0)
    return m


def _mat(key):
    """Material fijo MAT_COCHE_<key> (reutilizado si existe)."""
    name = "MAT_%s_%s" % (PREFIX, key)
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    color, rough, metal = _PALETA[key]
    return _mat_nuevo(name, color, rough, metal)


def _mat_color(clase, color, rough=0.30):
    """Material MAT_COCHE_<clase>_<HEX> para un rgb dado (reutilizado)."""
    r, g, b = [max(0.0, min(1.0, c)) for c in color]
    name = "MAT_%s_%s_%02X%02X%02X" % (
        PREFIX, clase, round(r * 255), round(g * 255), round(b * 255))
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    return _mat_nuevo(name, (r, g, b), rough, 0.0)


def _mat_cuerpo(color):
    return _mat_color("cuerpo", color, 0.28)


# ---------------------------------------------------------------------------
# Acumulador de malla multi-material
# ---------------------------------------------------------------------------
class _MB:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.fmat = []
        self.fsm = []
        self.frec = []

    def _mi(self, mat):
        for i, m in enumerate(self.mats):
            if m is mat:
                return i
        self.mats.append(mat)
        return len(self.mats) - 1

    def add(self, verts, faces, mat, smooth=False, recalc=False):
        """recalc=True: pieza cerrada cuyas normales recalcula bmesh."""
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

    def recentrar(self):
        """Origen al centro de la base: bbox centrado en XY y min z = 0."""
        xs = [v[0] for v in self.verts]
        ys = [v[1] for v in self.verts]
        zs = [v[2] for v in self.verts]
        cx = (min(xs) + max(xs)) * 0.5
        cy = (min(ys) + max(ys)) * 0.5
        z0 = min(zs)
        self.verts = [(x - cx, y - cy, z - z0) for (x, y, z) in self.verts]

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
        return ob


# ---------------------------------------------------------------------------
# Primitivas
# ---------------------------------------------------------------------------
def _box(sx, sy, sz, off=(0, 0, 0)):
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    ox, oy, oz = off
    verts = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
             (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    verts = [(a + ox, b + oy, c + oz) for (a, b, c) in verts]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]
    return verts, faces


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


def _rueda(mb, cx, cy, cz, r, hw, sign, eje="x", m_llanta=None, S=12):
    """Rueda por revolucion: neumatico + llanta hundida + tapacubos cromado.
    Un vertice cae exactamente en el punto mas bajo (apoyo en z = cz - r)."""
    g, ll, cr = _mat("negro"), (m_llanta or _mat("blanco")), _mat("cromo")
    perfil = [(-hw, 0.55 * r, g), (-0.60 * hw, r, g), (0.60 * hw, r, g),
              (0.96 * hw, 0.90 * r, g), (hw, 0.68 * r, g),
              (0.72 * hw, 0.63 * r, ll), (0.66 * hw, 0.27 * r, ll),
              (1.02 * hw, 0.20 * r, cr)]
    verts = []
    for a, rr, _m in perfil:
        for k in range(S):
            th = -0.5 * math.pi + TAU * k / S
            c, s = rr * math.cos(th), rr * math.sin(th)
            if eje == "x":
                verts.append((cx + sign * a, cy + c, cz + s))
            else:
                verts.append((cx + c, cy + sign * a, cz + s))
    n = len(perfil)
    c_in = len(verts)
    c_out = c_in + 1
    if eje == "x":
        verts.append((cx - sign * hw, cy, cz))
        verts.append((cx + sign * 1.10 * hw, cy, cz))
    else:
        verts.append((cx, cy - sign * hw, cz))
        verts.append((cx, cy + sign * 1.10 * hw, cz))
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


def _domo(mb, c, n, ru, rv, prof, m_aro, m_lente, seg=10, plano=False):
    """Casquete elipsoidal (faro) con eje horizontal n=(nx, ny). plano=True:
    lente de cara PLANA con canto biselado (pilotos e intermitentes), sin el
    vertice central en punta."""
    nx, ny = n
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    tx, ty = -ny, nx                       # tangente horizontal
    if plano:
        anillos = [(1.00, -0.05), (1.00, 0.45 * prof), (0.84, prof)]
    else:
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
    """Barre `seccion` [(d, dz)] por `camino` [((x, y, z), (nx, ny))]: d se mide
    sobre la normal horizontal, dz en vertical. Pieza cerrada con tapas."""
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


def _arco_extruido(mb, cy, cz, r0, r1_in, r1_out, x_in, x_out, a0, a1, mat,
                   seg=8, smooth=True):
    """Banda en arco (eje X) de radio interior r0 y exterior r1 (r1_in en el
    lado x_in, r1_out en x_out), de angulo a0..a1 (rad). Cerrada."""
    camino = []
    for k in range(seg + 1):
        th = a0 + (a1 - a0) * k / seg
        camino.append((math.cos(th), math.sin(th)))
    verts = []
    for (c, s) in camino:
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
    mb.add(verts, faces, mat, smooth=smooth, recalc=True)


def _elipsoide(mb, c, rx, ry, rz, mat, seg=8):
    """Elipsoide low-poly de eje Y (2 polos + 2 anillos), cerrado. Carcasa
    redondeada de los retrovisores."""
    verts = [(c[0], c[1] + ry, c[2])]
    for f in (0.45, -0.45):
        kr = math.sqrt(1.0 - f * f)
        for k in range(seg):
            th = TAU * k / seg
            verts.append((c[0] + rx * kr * math.cos(th), c[1] + ry * f,
                          c[2] + rz * kr * math.sin(th)))
    last = len(verts)
    verts.append((c[0], c[1] - ry, c[2]))
    faces = []
    for k in range(seg):
        k2 = (k + 1) % seg
        faces.append((0, 1 + k, 1 + k2))
        faces.append((1 + k, 1 + seg + k, 1 + seg + k2, 1 + k2))
        faces.append((last, 1 + seg + k2, 1 + seg + k))
    mb.add(verts, faces, mat, smooth=True, recalc=True)


def _parche(mb, quad, off, mat, fondo=0.03):
    """Parche lateral CON GROSOR (pilares): cara exterior desplazada `off` en
    X hacia fuera + cuatro retornos que se hunden `fondo` bajo la superficie.
    Evita el z-fighting y el aspecto de lamina flotante de un decal."""
    sg = 1.0 if quad[0][0] >= 0.0 else -1.0
    verts = ([(p[0] + sg * off, p[1], p[2]) for p in quad]
             + [(p[0] - sg * fondo, p[1], p[2]) for p in quad])
    faces = [(0, 1, 2, 3)]
    for k in range(4):
        k2 = (k + 1) % 4
        faces.append((k, k2, 4 + k2, 4 + k))
    p_int = tuple(sum(v[i] for v in verts[4:]) / 4.0 for i in range(3))
    mb.add(verts, _orientar_desde(verts, faces, p_int), mat)


# ---------------------------------------------------------------------------
# Planta del morro / cola: superelipse |x/bw|^n + |Y/dy|^n = 1
# ---------------------------------------------------------------------------
class _Planta:
    def __init__(self, y_tip, dy, bw, sentido=1, n=2.6):
        self.y_tip, self.dy, self.bw, self.s, self.n = y_tip, dy, bw, sentido, n

    def X(self, s):
        """Semiancho a distancia s (>=0) por detras de la punta."""
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


# ---------------------------------------------------------------------------
# Superficie de referencia: ray-cast axial por fuerza bruta. Sirve para
# conformar boca, faros, pilotos, franjas... EXACTAMENTE sobre la carroceria.
# ---------------------------------------------------------------------------
class _Sup:
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
        """Corte con la recta paralela al eje (0=x, 1=y, 2=z) que pasa por las
        otras dos coordenadas (p, q). Devuelve el valor extremo o None."""
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


# ---------------------------------------------------------------------------
# TIPOS. nucleo = estaciones (y, z_capo_centro, z_hombro, factor_ancho) de
# atras a delante; morro y cola se generan solos (superelipse en planta y
# redondeo en alzado hasta zF / zR). cab = cabina (loft aparte):
# y0 base luneta, y1 techo trasero, y2 techo delantero, y3 base parabrisas.
# ---------------------------------------------------------------------------
TIPOS = ("topolino", "compacto", "sedan", "familiar", "deportivo",
         "furgoneta", "pickup", "todoterreno", "ape")
_ALIAS_TIPO = {"furgo": "furgoneta"}
EXPRESIONES = ("abierto", "feliz", "sorpresa")
_ALIAS_EXPRESION = {"sonrisa": "feliz", "guino": "abierto"}
# todo lo que acepta build_coche(expresion=...): las nuevas + los nombres de
# coches_kit.py v1 ('sonrisa', 'guino'), que se traducen a expresiones felices
EXPRESIONES_ACEPTADAS = EXPRESIONES + tuple(_ALIAS_EXPRESION)
BOCAS = ("sonrisa", "abierta", "dientes", "rejilla")
OPCIONES = ("baca", "bitono", "franjas", "carga")

_TIPOS = {
    "topolino": dict(
        bw=0.68, zg=0.17, yR=-1.48, yF=1.50, nF=2.4, nR=2.4,
        nucleo=[(-1.05, 0.76, 0.69, 1.0), (-0.45, 0.84, 0.76, 1.0),
                (0.62, 0.84, 0.76, 1.0), (1.02, 0.77, 0.69, 0.98)],
        zF=0.60, zR=0.54,
        cab=dict(y0=-1.22, y1=-0.66, y2=0.24, y3=0.70, wb=0.60, wr=0.47,
                 zroof=1.36, cr=0.10, bowF=0.10, bowR=0.08, luna3=False,
                 domo=0.075),
        ruedas=dict(r=0.27, hw=0.085, ejes=(-0.92, 0.95)),
        faro=dict(x=0.60, dz=0.07, ru=0.10, rv=0.10, prof=0.07),
        piloto=dict(x=0.70, z=0.56, ru=0.05, rv=0.07),
        parag="cromo", zbF=0.28, zbR=0.29,
        pilares=[(-0.36, 0.09)], puerta=(0.58, -0.36),
        p_baca=0.35, p_bitono=0.40, p_franjas=0.20,
    ),
    "compacto": dict(
        bw=0.86, zg=0.18, yR=-1.92, yF=1.95, nF=2.6, nR=2.8,
        nucleo=[(-1.50, 1.00, 0.92, 1.0), (-0.55, 1.00, 0.92, 1.0),
                (1.00, 0.98, 0.90, 1.0), (1.42, 0.90, 0.82, 1.0)],
        zF=0.72, zR=0.86,
        cab=dict(y0=-1.84, y1=-1.26, y2=0.24, y3=1.08, wb=0.78, wr=0.60,
                 zroof=1.50, cr=0.09, bowF=0.12, bowR=0.06, luna3=False),
        ruedas=dict(r=0.31, hw=0.10, ejes=(-1.20, 1.22)),
        faro=dict(x=0.66, dz=0.05, ru=0.13, rv=0.085, prof=0.05),
        piloto=dict(x=0.74, z=0.88, ru=0.06, rv=0.10),
        parag="labio", zbF=0.30, zbR=0.34,
        pilares=[(-0.42, 0.10)], puerta=(0.74, -0.42),
        p_baca=0.20, p_bitono=0.35, p_franjas=0.20,
    ),
    "sedan": dict(
        bw=0.89, zg=0.17, yR=-2.25, yF=2.25, nF=2.6, nR=2.6,
        nucleo=[(-1.75, 0.93, 0.85, 1.0), (-0.80, 0.97, 0.89, 1.0),
                (0.85, 0.96, 0.88, 1.0), (1.62, 0.86, 0.78, 1.0)],
        zF=0.68, zR=0.76,
        cab=dict(y0=-1.50, y1=-0.78, y2=0.08, y3=0.95, wb=0.80, wr=0.60,
                 zroof=1.42, cr=0.08, bowF=0.12, bowR=0.10, luna3=False),
        ruedas=dict(r=0.31, hw=0.10, ejes=(-1.38, 1.42)),
        faro=dict(x=0.66, dz=0.05, ru=0.14, rv=0.075, prof=0.05),
        piloto=dict(x=0.70, z=0.78, ru=0.11, rv=0.055),
        parag="labio", zbF=0.29, zbR=0.32,
        pilares=[(-0.35, 0.10)], puerta=(0.72, -0.35),
        p_baca=0.10, p_bitono=0.15, p_franjas=0.0,
    ),
    "familiar": dict(
        bw=0.89, zg=0.18, yR=-2.30, yF=2.28, nF=2.6, nR=3.0,
        nucleo=[(-1.88, 0.97, 0.89, 1.0), (-0.80, 0.98, 0.90, 1.0),
                (0.88, 0.96, 0.88, 1.0), (1.65, 0.86, 0.78, 1.0)],
        zF=0.68, zR=0.84,
        cab=dict(y0=-2.20, y1=-1.86, y2=0.10, y3=0.98, wb=0.80, wr=0.63,
                 zroof=1.47, cr=0.08, bowF=0.12, bowR=0.05, luna3=True),
        ruedas=dict(r=0.31, hw=0.10, ejes=(-1.42, 1.44)),
        faro=dict(x=0.66, dz=0.05, ru=0.12, rv=0.09, prof=0.05),
        piloto=dict(x=0.78, z=0.90, ru=0.05, rv=0.12),
        parag="labio", zbF=0.30, zbR=0.34,
        pilares=[(-0.32, 0.10), (-1.18, 0.10)], puerta=(0.74, -0.32),
        p_baca=0.65, p_bitono=0.10, p_franjas=0.0,
    ),
    "deportivo": dict(
        bw=0.96, zg=0.13, yR=-2.18, yF=2.22, nF=2.4, nR=2.8,
        nucleo=[(-1.75, 0.84, 0.77, 1.0), (-0.95, 0.86, 0.78, 1.0),
                (0.50, 0.78, 0.70, 1.0), (1.55, 0.66, 0.59, 0.99)],
        zF=0.54, zR=0.72,
        cab=dict(y0=-1.60, y1=-0.62, y2=-0.12, y3=0.72, wb=0.80, wr=0.55,
                 zroof=1.17, cr=0.07, bowF=0.14, bowR=0.10, luna3=False),
        ruedas=dict(r=0.32, hw=0.13, ejes=(-1.36, 1.40)),
        faro=dict(x=0.70, dz=0.035, ru=0.15, rv=0.05, prof=0.035),
        piloto=dict(x=0.68, z=0.74, ru=0.12, rv=0.045),
        parag="labio", zbF=0.22, zbR=0.27,
        pilares=[], puerta=(0.45, -0.55),
        aleron=True, p_baca=0.0, p_bitono=0.10, p_franjas=0.60,
    ),
    "furgoneta": dict(
        bw=0.90, zg=0.21, yR=-2.12, yF=2.15, nF=3.0, nR=3.2, cuadrado=0.6,
        nucleo=[(-1.78, 1.04, 0.98, 1.0), (0.0, 1.05, 0.99, 1.0),
                (1.72, 1.04, 0.98, 1.0)],
        zF=0.96, zR=0.96,
        cab=dict(y0=-2.06, y1=-1.86, y2=1.42, y3=1.98, wb=0.84, wr=0.72,
                 zroof=1.93, cr=0.12, bowF=0.10, bowR=0.04, luna3=True),
        ruedas=dict(r=0.32, hw=0.10, ejes=(-1.25, 1.32)),
        faro=dict(x=0.62, dz=-0.16, ru=0.12, rv=0.12, prof=0.06),
        piloto=dict(x=0.80, z=0.80, ru=0.055, rv=0.11),
        parag="cromo", zbF=0.34, zbR=0.34, boca_zhi=0.74,
        pilares=[(-0.95, 0.10), (0.20, 0.10), (1.05, 0.10)],
        puerta=(1.28, 0.20),
        p_baca=0.50, p_bitono=1.0, p_franjas=0.0,
    ),
    "pickup": dict(
        bw=0.92, zg=0.26, yR=-2.30, yF=2.30, nF=2.8, nR=4.0, cuadrado=0.5,
        nucleo=[(-2.02, 0.99, 0.96, 1.0), (-0.35, 0.99, 0.96, 1.0),
                (1.05, 1.04, 0.96, 1.0), (1.72, 0.98, 0.90, 1.0)],
        zF=0.84, zR=0.93,
        cab=dict(y0=-0.42, y1=-0.28, y2=0.40, y3=1.12, wb=0.82, wr=0.66,
                 zroof=1.60, cr=0.08, bowF=0.10, bowR=0.03, luna3=False),
        ruedas=dict(r=0.35, hw=0.12, ejes=(-1.40, 1.45)),
        faro=dict(x=0.66, dz=0.0, ru=0.12, rv=0.10, prof=0.05),
        piloto=dict(x=0.82, z=0.80, ru=0.05, rv=0.12),
        parag="cromo", zbF=0.40, zbR=0.40, boca_zhi=0.74,
        pilares=[], puerta=(0.92, -0.18),
        caja=(-2.12, -0.56, 0.74),
        p_baca=0.0, p_bitono=0.15, p_franjas=0.0,
    ),
    "todoterreno": dict(
        bw=0.94, zg=0.34, yR=-1.95, yF=2.00, nF=3.2, nR=3.6, cuadrado=0.8,
        nucleo=[(-1.62, 1.10, 1.04, 1.0), (0.75, 1.12, 1.04, 1.0),
                (1.45, 1.08, 1.00, 1.0)],
        zF=0.96, zR=1.02,
        cab=dict(y0=-1.86, y1=-1.68, y2=0.38, y3=0.82, wb=0.86, wr=0.76,
                 zroof=1.84, cr=0.07, bowF=0.06, bowR=0.03, luna3=True),
        ruedas=dict(r=0.40, hw=0.13, ejes=(-1.15, 1.22)),
        faro=dict(x=0.64, dz=-0.06, ru=0.11, rv=0.11, prof=0.06),
        piloto=dict(x=0.82, z=0.95, ru=0.05, rv=0.10),
        parag="cromo", zbF=0.48, zbR=0.48, boca_zhi=0.78,
        pilares=[(-0.30, 0.11), (-1.05, 0.11)], puerta=(0.62, -0.30),
        repuesto=True, p_baca=0.70, p_bitono=0.25, p_franjas=0.0,
    ),
    "ape": dict(
        bw=0.70, zg=0.26, yR=-1.45, yF=1.45, nF=2.2, nR=4.0, dzF=0.12,
        nucleo=[(-1.25, 0.76, 0.74, 1.0), (-0.12, 0.76, 0.74, 1.0),
                (-0.05, 0.86, 0.80, 0.84), (0.75, 0.86, 0.80, 0.84),
                (1.05, 0.84, 0.78, 0.80)],
        zF=0.70, zR=0.72,
        cab=dict(y0=-0.10, y1=0.0, y2=0.72, y3=1.10, wb=0.54, wr=0.46,
                 zroof=1.56, cr=0.08, bowF=0.10, bowR=0.02, luna3=False),
        ruedas=dict(r=0.23, hw=0.075, ejes=(-0.78,), central=1.00),
        faro=dict(x=0.66, dz=0.05, ru=0.075, rv=0.075, prof=0.05),
        piloto=dict(x=0.82, z=0.62, ru=0.04, rv=0.06),
        parag="cromo", zbF=None, zbR=0.36,
        pilares=[], puerta=(0.98, 0.10),
        caja=(-1.36, -0.16, 0.60),
        p_baca=0.0, p_bitono=0.30, p_franjas=0.0,
    ),
}

_QS = (0.04, 0.14, 0.34, 0.62)      # estaciones auto de morro/cola (s/dy)
_FX = (0.80, 0.97, 1.00, 1.00, 0.965, 0.86, 0.60, 0.30)
_FH = (0.0, 0.10, 0.40, 0.72)       # alturas relativas de los 4 primeros ptos


def _g(q, m=2.2):
    q = max(0.0, min(1.0, q))
    return (1.0 - (1.0 - q) ** m) ** (1.0 / m)


def _interp(tabla, y, k):
    """Interpolacion lineal de la columna k de `tabla` (ordenada por [0])."""
    if y <= tabla[0][0]:
        return tabla[0][k]
    if y >= tabla[-1][0]:
        return tabla[-1][k]
    for a, b in zip(tabla, tabla[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / ((b[0] - a[0]) or 1.0)
            return a[k] + (b[k] - a[k]) * t
    return tabla[-1][k]


def _estaciones(d, fy):
    """Estaciones (y, semiancho, z_suelo, z_hombro, z_centro) de cola a morro
    + plantas (superelipses) del morro y de la cola."""
    nuc = [(y * fy, zc, ze, d["bw"] * wf) for (y, zc, ze, wf) in d["nucleo"]]
    yR, yF, zg = d["yR"] * fy, d["yF"] * fy, d["zg"]
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


def _sec_cuerpo(y, w, zg, ze, zc, cuad=0.0):
    """Seccion cerrada de 17 puntos: bajos, flanco, hombro redondeado y capo
    abombado (der. abajo->arriba, centro, izq. arriba->abajo)."""
    h, dd = ze - zg, zc - ze
    fx = list(_FX)
    fx[4] += 0.020 * cuad
    fx[5] += 0.075 * cuad
    fx[6] += 0.080 * cuad
    zs = (zg, zg + 0.10 * h, zg + 0.40 * h, zg + 0.72 * h,
          zg + (0.93 + 0.03 * cuad) * h, ze + 0.30 * dd, ze + 0.75 * dd,
          ze + 0.95 * dd)
    der = [(f * w, z) for f, z in zip(fx, zs)]
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
    """Loft cerrado: (n-1)*P quads [indice i*P + j] + P tris de tapa inicial
    + P tris de tapa final."""
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


def _angulos_arco(a0, a1, seg, extras):
    """seg+1 angulos uniformes de a0 a a1. Cada angulo de `extras` (donde el
    arco cruza un quiebro del flanco) sustituye al angulo interior mas cercano
    si esta libre y a < 0.12 rad; si no, se inserta."""
    ths = [a0 + (a1 - a0) * k / seg for k in range(seg + 1)]
    usados, nuevos = set(), []
    for e in extras:
        if not (a0 + 0.06 < e < a1 - 0.06):
            continue
        k = min(range(1, seg), key=lambda i: abs(ths[i] - e))
        if k not in usados and abs(ths[k] - e) < 0.12:
            ths[k] = e
            usados.add(k)
        else:
            nuevos.append(e)
    return sorted(ths + nuevos)


def _aleta_paso(mb, xb, cy, cz, r, R, a0, sg, zquiebros, m_cuerpo, m_osc, seg=8):
    """Paso de rueda que SIGUE la carroceria. xb(y, z) = semiancho real del
    flanco (estrechamiento del morro/cola en planta + metido de los bajos).
      * banda oscura anular (0.8 r .. R) conformada al flanco, a 1.8 cm,
      * aleta del color de la carroceria: labio que sobresale 4.6 cm arriba y
        solo 2.4 cm en los extremos del arco (de frente ya no se ve como un
        tablon), con un faldon interior inclinado que, si el arco asoma por
        encima del capo (deportivo), forma un abultamiento de aleta.
    Pieza de la aleta cerrada (seccion de 4 puntos barrida por el arco)."""
    extras = []
    for zq in zquiebros:
        s = (zq - cz) / R
        if -0.98 < s < 0.98:
            th = math.asin(s)
            extras += [th, math.pi - th]
    ths = _angulos_arco(a0, math.pi - a0, seg, extras)
    n = len(ths)

    vb = []
    for th in ths:
        c, s = math.cos(th), math.sin(th)
        for rho in (0.80 * r, R + 0.004):
            y, z = cy + rho * c, cz + rho * s
            vb.append((sg * (xb(y, z) + 0.018), y, z))
    fb = [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(n - 1)]
    mb.add(vb, _orientar(vb, fb, (sg, 0.0, 0.0)), m_osc, smooth=True)

    va = []
    for th in ths:
        c, s = math.cos(th), math.sin(th)
        x0 = max(xb(cy + R * c, cz + R * s),
                 xb(cy + (R + 0.055) * c, cz + (R + 0.055) * s))
        p = 0.024 + 0.022 * max(0.0, s) ** 0.6
        for (dx, rho) in ((-0.24, R - 0.045), (-0.03, R + 0.055),
                          (p, R + 0.032), (p, R - 0.004)):
            va.append((sg * (x0 + dx), cy + rho * c, cz + rho * s))
    fa = []
    for k in range(n - 1):
        for j in range(4):
            j2 = (j + 1) % 4
            fa.append((4 * k + j, 4 * k + j2, 4 * (k + 1) + j2, 4 * (k + 1) + j))
    fa.append((0, 1, 2, 3))
    fa.append(tuple(4 * (n - 1) + j for j in (3, 2, 1, 0)))
    mb.add(va, fa, m_cuerpo, smooth=True, recalc=True)


def _camino_parag(pl, z0, s_lim, kb=0.0, pasos=10):
    """Camino del parachoques por la planta `pl`, recortado a s <= s_lim
    (para no invadir el paso de rueda) y curvado en sonrisa (z0 + kb*x^2)."""
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
    if s_lim > pl.dy + 0.03:        # retornos laterales hasta el paso de rueda
        s_ret = min(s_lim, pl.dy + 0.30)
        zr = z0 + kb * pl.bw * pl.bw
        out.insert(0, ((-pl.bw, pl.y_tip - pl.s * s_ret, zr), (-1.0, 0.0)))
        out.append(((pl.bw, pl.y_tip - pl.s * s_ret, zr), (1.0, 0.0)))
    return out


def _conformada(mb, fsurf, xs, zlo, zhi, off, mat, filas=1,
                hint=(0.0, 1.0, 0.0)):
    """Malla de len(xs) x (filas+1) puntos entre zlo(x) y zhi(x), pegada a
    la superficie y = fsurf(x, z) con separacion off(x)."""
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
    faces = _orientar(verts, faces, hint)
    mb.add(verts, faces, mat, smooth=True)


def _linspace(a, b, n):
    return [a + (b - a) * k / (n - 1) for k in range(n)]


# ---------------------------------------------------------------------------
# CARA: ojos sobre el parabrisas
# ---------------------------------------------------------------------------
_U_ANC = 0.50 / 0.88
# Separaciones sobre el cristal (m). Los parpados nunca pisan la pupila ni el
# brillo, asi que van a la altura de la pupila: quedan mas pegados a la
# esclerotica y su micro-sombra es menor.
_OFF_OJO, _OFF_IRIS, _OFF_PUP, _OFF_BRI, _OFF_PARP = 0.018, 0.028, 0.038, 0.048, 0.040


def _parabrisas_uv(arc_top, arc_bot):
    """punto(u, v, off) sobre el cristal: u en [-1, 1] a lo ancho (anclas en
    los vertices reales del lazo), v en [0, 1] de la base al techo."""
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
    """Poligono convexo en (u, v) conformado al cristal (abanico)."""
    verts = [punto(centro[0], centro[1], off)]
    verts += [punto(u, v, off) for (u, v) in contorno]
    n = len(contorno)
    faces = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    faces = _orientar(verts, faces, (0.0, 0.6, 0.8))
    mb.add(verts, faces, mat, smooth=True)


def _elipse(uc, vc, ru, rv, n, th0=0.0, th1=TAU, cerrado=True, sx=1.0):
    m = n if cerrado else n + 1
    return [(uc + sx * ru * math.cos(th0 + (th1 - th0) * k / n),
             vc + rv * math.sin(th0 + (th1 - th0) * k / n)) for k in range(m)]


def _cara_ojos(mb, arc_top, arc_bot, rng, expresion, m_parpado, iris_key):
    """Dos ojos grandes, SIEMPRE los dos y simetricos (nunca guino)."""
    surf, punto = _parabrisas_uv(arc_top, arc_bot)
    m_ojo, m_pup, m_iris = _mat("blanco"), _mat("negro"), _mat(iris_key)
    UC, VC, RU, RV = 0.49, 0.54, 0.43, 0.40
    if expresion == "sorpresa":
        RV, VC = 0.43, 0.53
    # escala metrica del cristal en el centro del ojo
    e = 0.05
    pa, pb = surf(UC + e, VC), surf(UC - e, VC)
    pc, pd = surf(UC, VC + e), surf(UC, VC - e)
    su = math.dist(pa, pb) / (2 * e)
    sv = math.dist(pc, pd) / (2 * e)
    r_m = min(RU * su, RV * sv)
    k_iris = {"abierto": 0.56, "feliz": 0.56, "sorpresa": 0.44}[expresion]
    ri = k_iris * r_m
    mirada = rng.choice((-1, 0, 0, 1))
    gx = mirada * 0.45 * max(0.0, RU - ri / su)
    gy = {"abierto": 0.02, "feliz": 0.06, "sorpresa": 0.06}[expresion] * RV
    for s in (-1, 1):
        uc = s * UC
        _fan_uv(mb, punto, (uc, VC), _elipse(uc, VC, RU, RV, 18), _OFF_OJO, m_ojo)
        ic = (uc + gx, VC + gy)
        _fan_uv(mb, punto, ic, _elipse(ic[0], ic[1], ri / su, ri / sv, 14),
                _OFF_IRIS, m_iris)
        rp = (0.50 if expresion != "sorpresa" else 0.42) * ri
        _fan_uv(mb, punto, ic, _elipse(ic[0], ic[1], rp / su, rp / sv, 10),
                _OFF_PUP, m_pup)
        bc = (ic[0] - 0.42 * ri / su, ic[1] + 0.42 * ri / sv)
        rb = 0.20 * ri
        _fan_uv(mb, punto, bc, _elipse(bc[0], bc[1], rb / su, rb / sv, 6),
                _OFF_BRI, m_ojo)
        # parpado superior (color carroceria), caido hacia fuera = amable
        # ('feliz' = ojo bien abierto arriba: si el parpado superior baja, el
        # iris toca los dos parpados y la mirada queda somnolienta)
        k_sup, tilt = {"abierto": (0.62, -0.03), "feliz": (0.84, -0.05),
                       "sorpresa": (0.94, 0.0)}[expresion]
        a = math.asin(k_sup / 1.07)
        th0, th1 = a - tilt, math.pi - a - tilt
        cont = _elipse(uc, VC, 1.07 * RU, 1.07 * RV, 8, th0, th1, False, sx=s)
        cen = (0.5 * (cont[4][0] + 0.5 * (cont[0][0] + cont[-1][0])),
               0.5 * (cont[4][1] + 0.5 * (cont[0][1] + cont[-1][1])))
        _fan_uv(mb, punto, cen, cont, _OFF_PARP, m_parpado)
        if expresion == "feliz":
            # parpado inferior arqueado hacia arriba: ojos que sonrien. Su
            # cresta queda por debajo del iris y nunca tapa mas de ~13 cm
            # (en parabrisas altos: furgoneta, todoterreno, ape) ni mas del
            # ~21 % del alto del ojo.
            comba = 0.16
            kl = max(0.74, min(0.88, 1.0 + comba - 0.13 / max(1e-6, RV * sv)))
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


# ---------------------------------------------------------------------------
# BOCA sonriente sobre el morro (encima del parachoques)
# ---------------------------------------------------------------------------
def _boca(mb, fsurf, offn, estilo, xh, z_hi, avail, m_labio):
    a_up = (0.40 if estilo == "sonrisa" else 0.26) * avail
    h = {"sonrisa": 0.24, "abierta": 0.72, "dientes": 0.60,
         "rejilla": 0.56}[estilo] * avail
    h = max(h, 0.045)

    def grosor(x):
        return h * max(0.0, 1.0 - (x / xh) ** 2)

    def zu(x):
        return z_hi - a_up * (1.0 - (x / xh) ** 2)

    def zl(x):
        return zu(x) - max(0.006, grosor(x))

    # capas (separacion sobre la carroceria, >= 1.2 cm entre capas que se
    # pisan, para que no haya z-fighting a distancia en el motor del juego)
    o_boca, o_capa, o_barra = 0.020, 0.033, 0.045
    m_boca = _mat("negro")
    xs = _linspace(-xh, xh, 13)
    _conformada(mb, fsurf, xs, zl, zu, lambda x: offn(x, o_boca), m_boca,
                filas=(1 if estilo == "sonrisa" else 2))
    # labio inferior claro, mas grueso en el centro
    xl = _linspace(-1.04 * xh, 1.04 * xh, 13)
    _conformada(mb, fsurf, xl,
                lambda x: zl(x) - (0.018 + 0.026 * max(0.0, 1.0 - (x / xh) ** 2)),
                lambda x: zl(x) + 0.004, lambda x: offn(x, o_capa), m_labio)
    if estilo in ("abierta", "dientes"):
        xd = _linspace(-0.80 * xh, 0.80 * xh, 9)
        kd = 0.30 if estilo == "abierta" else 0.46
        _conformada(mb, fsurf, xd, lambda x: zu(x) - kd * grosor(x),
                    lambda x: zu(x) - 0.003, lambda x: offn(x, o_capa),
                    _mat("blanco"))
    if estilo == "abierta":
        xt = _linspace(-0.55 * xh, 0.55 * xh, 7)
        _conformada(mb, fsurf, xt, lambda x: zl(x) + 0.006,
                    lambda x: zl(x) + 0.007 + 0.46 * grosor(x)
                    * max(0.0, 1.0 - (x / (0.55 * xh)) ** 2),
                    lambda x: offn(x, o_capa), _mat("piloto"))
    if estilo == "rejilla":
        m_cr = _mat("cromo")
        for xb in _linspace(-0.72 * xh, 0.72 * xh, 7):
            _conformada(mb, fsurf, [xb - 0.014, xb + 0.014],
                        lambda x: zl(xb) + 0.006, lambda x: zu(xb) - 0.004,
                        lambda x: offn(xb, o_capa), m_cr)
        _conformada(mb, fsurf, _linspace(-0.62 * xh, 0.62 * xh, 7),
                    lambda x: 0.5 * (zl(x) + zu(x)) - 0.010,
                    lambda x: 0.5 * (zl(x) + zu(x)) + 0.010,
                    lambda x: offn(x, o_barra), m_cr)


# ---------------------------------------------------------------------------
# Construccion de un coche
# ---------------------------------------------------------------------------
def _luma(c):
    return 0.30 * c[0] + 0.55 * c[1] + 0.15 * c[2]


def _construir(nombre, tipo, d, color, rng, expresion, boca, op, parent_collection):
    mb = _MB()
    fy = rng.uniform(0.985, 1.025)
    fh = rng.uniform(0.97, 1.04)

    # ---- opciones por seed (o forzadas por parametro)
    def _op(clave, prob):
        u = rng.random()
        v = op.get(clave)
        return (u < prob) if v is None else bool(v)

    con_baca = _op("baca", d.get("p_baca", 0.0))
    con_bitono = _op("bitono", d.get("p_bitono", 0.0))
    con_franjas = _op("franjas", d.get("p_franjas", 0.0))
    con_carga = _op("carga", 0.6)
    iris_key = rng.choice(("iris_azul", "iris_marron", "iris_verde", "iris_azul"))
    llanta_op = rng.choice(("blanco", "blanco", "cromo", "cuerpo"))

    # materiales: SOLO el de carroceria depende del color; el resto son fijos
    # y compartidos por todos los coches (<= 10 slots por coche)
    color = tuple(max(0.0, min(1.0, c)) for c in color[:3])
    m_cuerpo = _mat_cuerpo(color)
    m_cristal, m_negro, m_cromo = _mat("cristal"), _mat("negro"), _mat("cromo")
    m_blanco = _mat("blanco")
    if con_bitono:
        m_techo = m_negro if _luma(color) > 0.55 else m_blanco
    else:
        m_techo = m_cuerpo
    m_labio = m_cromo if d["parag"] == "cromo" else m_blanco
    m_llanta = m_cuerpo if llanta_op == "cuerpo" else _mat(llanta_op)

    # ---- carroceria (loft de 17 puntos)
    est, plF, plR = _estaciones(d, fy)
    cuad = d.get("cuadrado", 0.0)
    loops = [_sec_cuerpo(y, w, zgl, ze, zc, cuad) for (y, w, zgl, ze, zc) in est]
    yR, yF, zg = d["yR"] * fy, d["yF"] * fy, d["zg"]
    c_ini = (0.0, yR, 0.5 * (est[0][2] + est[0][4]))
    c_fin = (0.0, yF, 0.5 * (est[-1][2] + est[-1][4]))
    bverts, bfaces = _loft(loops, c_ini, c_fin)
    mb.add(bverts, bfaces, m_cuerpo, smooth=True, recalc=True)
    sup = _Sup()
    sup.add(bverts, bfaces)

    def w_at(y):
        return _interp(est, y, 1)

    def ze_at(y):
        return _interp(est, y, 3)

    def zc_at(y):
        return _interp(est, y, 4)

    def x_flanco(y, z):
        """Semiancho REAL del flanco en (y, z): planta (w_at) x perfil de los
        bajos de _sec_cuerpo (_FX/_FH). Por encima de 0.40 h vale w_at(y)."""
        zs = _interp(est, y, 2)
        t = (z - zs) / max(0.05, ze_at(y) - zs)
        if t <= _FH[0]:
            f = _FX[0]
        elif t >= _FH[2]:
            f = _FX[2]
        else:
            k = 0 if t < _FH[1] else 1
            f = _FX[k] + (_FX[k + 1] - _FX[k]) * (t - _FH[k]) / (_FH[k + 1] - _FH[k])
        return f * w_at(y)

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

    # ---- cabina (loft de 9 puntos): luneta, techo, parabrisas
    cab = d["cab"]
    y0, y1, y2, y3 = [cab[k] * fy for k in ("y0", "y1", "y2", "y3")]
    ym = 0.5 * (y1 + y2)
    hund = 0.06
    zb_m = ze_at(ym) - hund
    zroof = ze_at(ym) + (cab["zroof"] - ze_at(ym)) * fh
    cr = cab["cr"]
    zrail = zroof - cr
    wr = cab["wr"]

    def wb_at(y):
        return min(cab["wb"], 0.93 * w_at(y))

    def colapsada(y, bow):
        wbc = wb_at(y)
        zb = ze_at(y) - hund
        return _sec_cab(y, wbc, wbc - 0.015, zb, zb + 0.02,
                        max(0.02, zc_at(y) - ze_at(y)), bow)

    # 7 lazos: luneta | canto trasero del techo | techo | centro (mas alto) |
    # techo | canto delantero (ceja) | parabrisas  -> linea de techo redondeada
    domo = cab.get("domo", 0.035)
    dr = min(0.24, 0.30 * (y2 - y1))
    cloops = [
        colapsada(y0, -cab["bowR"]),
        _sec_cab(y1, wb_at(y1), wr - 0.010, ze_at(y1) - hund, zrail - domo, cr,
                 -0.7 * cab["bowR"]),
        _sec_cab(y1 + dr, wb_at(y1 + dr), wr, ze_at(y1 + dr) - hund, zrail, cr,
                 -0.3 * cab["bowR"]),
        _sec_cab(ym, wb_at(ym), wr + 0.012, zb_m, zrail + 0.6 * domo, cr, 0.0),
        _sec_cab(y2 - dr, wb_at(y2 - dr), wr, ze_at(y2 - dr) - hund, zrail, cr,
                 0.3 * cab["bowF"]),
        _sec_cab(y2, wb_at(y2), wr - 0.010, ze_at(y2) - hund, zrail - domo, cr,
                 0.7 * cab["bowF"]),
        colapsada(y3, cab["bowF"]),
    ]
    NL = len(cloops)
    cverts, cfaces = _loft(cloops, (0.0, y0 - cab["bowR"], ze_at(y0) - hund + 0.02),
                           (0.0, y3 + cab["bowF"], ze_at(y3) - hund + 0.02))
    luna3 = cab.get("luna3", False)
    cmats = []
    for i in range(NL - 1):
        for j in range(9):
            if j == 8:
                m = m_cuerpo
            elif i == NL - 2:
                m = m_cristal if (2 <= j <= 5 or j in (0, 7)) else m_techo
            elif i == 0:
                m = m_cristal if (2 <= j <= 5 or (luna3 and j in (0, 7))) else m_techo
            else:
                m = m_cristal if j in (0, 7) else m_techo
            cmats.append(m)
    cmats += [m_techo] * 18
    mb.add(cverts, cfaces, cmats, smooth=True, recalc=True)
    sup_cab = _Sup()
    sup_cab.add(cverts, cfaces)

    # pilares (parches sobre el cristal lateral) y pilar A
    cab_ys = [y0, y1, y1 + dr, ym, y2 - dr, y2, y3]

    def lado(y, j):
        for i in range(NL - 1):
            if cab_ys[i] <= y <= cab_ys[i + 1]:
                t = (y - cab_ys[i]) / ((cab_ys[i + 1] - cab_ys[i]) or 1.0)
                a, b = cloops[i][j], cloops[i + 1][j]
                return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
        return cloops[3][j]

    pilares = [(yp * fy, an) for (yp, an) in d.get("pilares", [])]
    pilares.append((y1 + 0.05, 0.10))
    off_pilar = 0.018
    for sg in (1, -1):
        for (yp, an) in pilares:
            ya, yb = max(y1, yp - an / 2), min(y2, yp + an / 2)
            q = [lado(ya, 0), lado(yb, 0), lado(yb, 1), lado(ya, 1)]
            _parche(mb, [(sg * p[0], p[1], p[2]) for p in q], off_pilar, m_techo)
        A, B, E = cloops[NL - 1][1], cloops[NL - 2][1], cloops[NL - 2][0]
        la, lb = math.dist(A, E) or 1.0, math.dist(B, E) or 1.0
        D = tuple(A[k] + (E[k] - A[k]) * min(1.0, 0.17 / la) for k in range(3))
        C = tuple(B[k] + (E[k] - B[k]) * min(1.0, 0.11 / lb) for k in range(3))
        _parche(mb, [(sg * p[0], p[1], p[2]) for p in (A, D, C, B)], off_pilar,
                m_techo)

    # ---- CARA: ojos en el parabrisas
    arc_top = [cloops[NL - 2][k] for k in (6, 5, 4, 3, 2)]
    arc_bot = [cloops[NL - 1][k] for k in (6, 5, 4, 3, 2)]
    _cara_ojos(mb, arc_top, arc_bot, rng, expresion, m_cuerpo, iris_key)

    # ---- pasos de rueda + ruedas
    rd = d["ruedas"]
    r, hw = rd["r"], rd["hw"]
    r_arco = 1.12 * r + 0.02
    z_corte = zg + 0.03
    a0 = max(-0.6, math.asin(max(-1.0, min(1.0, (z_corte - r) / r_arco))))
    ejes = [ye * fy for ye in rd["ejes"]]
    for ye in ejes:
        wl = w_at(ye)
        h_eje = ze_at(ye) - zg
        zquiebros = (zg + _FH[1] * h_eje, zg + _FH[2] * h_eje)
        for sg in (1, -1):
            # banda oscura + aleta que siguen el flanco real (x_flanco): no
            # sobresalen del morro/cola estrechados ni de los bajos metidos
            _aleta_paso(mb, x_flanco, ye, r, r, r_arco, a0, sg, zquiebros,
                        m_cuerpo, m_negro)
            _rueda(mb, sg * (wl - hw + 0.03), ye, r, r, hw, sg, "x", m_llanta)
    if rd.get("central") is not None:
        yc = rd["central"] * fy
        _rueda(mb, 0.0, yc, r, r, hw, 1, "x", m_llanta)
        # horquilla/guardabarros de la rueda delantera unica
        _arco_extruido(mb, yc, r, r + 0.025, r + 0.06, r + 0.06,
                       -hw - 0.035, hw + 0.035, 0.15, math.pi - 0.15, m_cuerpo)

    # ---- parachoques
    hb = 0.045 if d["parag"] == "cromo" else 0.055
    sec_pg = [(-0.12, -hb), (0.030, -hb), (0.058, -0.45 * hb),
              (0.058, 0.45 * hb), (0.030, hb), (-0.12, hb)]
    bwF = plF.bw
    kb = 0.05 / (bwF * bwF)
    eje_del = max(ejes) if rd.get("central") is None else None
    if d.get("zbF") is not None:
        s_lim = (yF - (eje_del + r_arco + 0.07)) if eje_del is not None else plF.dy + 0.3
        cam = _camino_parag(plF, d["zbF"], s_lim, kb)
        if len(cam) >= 3:
            _barrido(mb, cam, sec_pg, m_labio)
        z_lo = d["zbF"] + hb + 0.025
    else:
        z_lo = est[-1][2] + 0.05
    s_lim = (min(ejes) - r_arco - 0.07) - yR
    cam = _camino_parag(plR, d["zbR"], s_lim, 0.0)
    if len(cam) >= 3:
        _barrido(mb, cam, sec_pg, m_labio)

    # ---- faros (NO son ojos) + intermitentes
    fa = d["faro"]
    xf, zf = fa["x"] * bwF, d["zF"] + fa["dz"]
    for sg in (1, -1):
        x = sg * xf
        nrm = plF.normal(x)
        yv = fsurfF(x, zf)
        _domo(mb, (x - nrm[0] * 0.012, yv - nrm[1] * 0.012, zf), nrm,
              fa["ru"], fa["rv"], fa["prof"], m_cromo, _mat("faro"))
        zi = zf - fa["rv"] - 0.05
        xi = x + sg * 0.06
        nri = plF.normal(xi)
        _domo(mb, (xi, fsurfF(xi, zi) - 0.008, zi), nri, 0.042, 0.030, 0.022,
              _mat("ambar"), _mat("ambar"), seg=6, plano=True)

    # ---- BOCA
    z_hi = d.get("boca_zhi", d["zF"] - 0.05)
    avail = max(0.10, z_hi - z_lo)
    xh = 0.58 * bwF
    if zf - fa["rv"] < z_hi + 0.02:
        xh = min(xh, xf - fa["ru"] - 0.05)
    _boca(mb, fsurfF, offnF, boca, xh, z_hi, avail, m_labio)

    # ---- pilotos traseros + matricula
    pi_ = d["piloto"]
    bwR = plR.bw
    for sg in (1, -1):
        x = sg * pi_["x"] * bwR
        nrm = plR.normal(x)
        yv = fsurfR(x, pi_["z"])
        # piloto de lente plana con canto biselado (sin vertice en punta)
        _domo(mb, (x - nrm[0] * 0.012, yv - nrm[1] * 0.012, pi_["z"]), nrm,
              1.4 * pi_["ru"], 1.4 * pi_["rv"], 0.030, m_cromo, _mat("piloto"),
              seg=8, plano=True)
    zpl = d["zbR"] + 0.17
    ypl = fsurfR(0.0, zpl)
    mb.add(*_box(0.36, 0.03, 0.11, off=(0.0, ypl - 0.010, zpl)), m_blanco)

    # ---- retrovisores, manillas y juntas de puerta
    y_ret = y3 - 0.24
    for sg in (1, -1):
        x_r = wb_at(y_ret) + 0.10
        z_r = ze_at(y_ret) + 0.13
        # carcasa redondeada (elipsoide) + brazo
        _elipsoide(mb, (sg * x_r, y_ret, z_r), 0.070, 0.042, 0.055, m_cuerpo)
        mb.add(*_box(0.12, 0.03, 0.03, off=(sg * (x_r - 0.09), y_ret, z_r - 0.03)),
               m_cuerpo)
    pu = d.get("puerta")
    if pu:
        for sg in (1, -1):
            for yp in pu:
                yp = yp * fy
                wl, zel = w_at(yp), ze_at(yp)
                h = zel - zg
                pts = []
                for k in (1, 2, 3, 4):      # mismo perfil que _sec_cuerpo
                    fz = _FH[k] if k < 4 else 0.93 + 0.03 * cuad
                    fxk = _FX[k] + (0.020 * cuad if k == 4 else 0.0)
                    pts.append((fxk * wl + 0.015, zg + fz * h))
                verts = ([(sg * x, yp - 0.007, z) for (x, z) in pts]
                         + [(sg * x, yp + 0.007, z) for (x, z) in pts])
                faces = [(k, k + 1, k + 5, k + 4) for k in range(3)]
                mb.add(verts, _orientar(verts, faces, (sg, 0.0, 0.0)), m_negro)
            ym_ = pu[1] * fy + 0.16
            wl, zel = w_at(ym_), ze_at(ym_)
            mb.add(*_box(0.03, 0.12, 0.028,
                         off=(sg * (0.985 * wl + 0.010), ym_, zg + 0.80 * (zel - zg))),
                   m_cromo)

    # ---- franjas de carreras (capo, techo, zaga)
    if con_franjas:
        def franja(s_, ya, yb, n, off):
            if yb - ya < 0.25:
                return
            ys = _linspace(ya, yb, n)
            for sg in (1, -1):
                verts = []
                for y in ys:
                    for x in (0.07, 0.20):
                        z = s_.hit(2, sg * x, y, 1)
                        verts.append((sg * x, y, (z if z is not None else 0.0) + off))
                if any(v[2] <= off for v in verts):
                    continue
                faces = [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(n - 1)]
                mb.add(verts, _orientar(verts, faces, (0.0, 0.0, 1.0)), m_blanco,
                       smooth=True)
        franja(sup, y3 + cab["bowF"] + 0.03, yF - 0.10 * plF.dy, 9, 0.020)
        franja(sup_cab, y1, y2, 5, 0.020)
        franja(sup, yR + 0.12 * plR.dy, y0 - cab["bowR"] - 0.04, 6, 0.020)

    # ---- aleron (deportivo)
    if d.get("aleron"):
        ya = yR + 0.34
        zd = zc_at(ya)
        for sx in (-0.42, 0.42):
            mb.add(*_box(0.05, 0.14, 0.24, off=(sx * d["bw"], ya, zd + 0.08)), m_cuerpo)
        mb.add(*_box(1.72 * d["bw"], 0.28, 0.04, off=(0.0, ya - 0.02, zd + 0.215)),
               m_cuerpo)
        for sx in (-1, 1):
            mb.add(*_box(0.03, 0.32, 0.13,
                         off=(sx * 0.86 * d["bw"], ya - 0.02, zd + 0.20)), m_cuerpo)

    # ---- rueda de repuesto (todoterreno)
    if d.get("repuesto"):
        zr_ = 1.02
        yv = fsurfR(0.0, zr_)
        _rueda(mb, 0.0, yv - 0.10, zr_, 0.36, 0.10, -1, "y", m_llanta, S=12)

    # ---- caja de carga (pickup / ape)
    if d.get("caja"):
        ca, cb, chw = d["caja"]
        ca, cb = ca * fy, cb * fy
        zde = ze_at(0.5 * (ca + cb))
        zpi = zc_at(0.5 * (ca + cb)) + 0.020
        vs = [(-chw, ca, zpi), (chw, ca, zpi), (chw, cb, zpi), (-chw, cb, zpi)]
        mb.add(vs, [(0, 1, 2, 3)], m_negro)
        for sx in (-1, 1):
            mb.add(*_box(0.07, cb - ca + 0.14, 0.10,
                         off=(sx * (chw + 0.035), 0.5 * (ca + cb), zde + 0.035)),
                   m_cuerpo)
        for yy in (ca - 0.035, cb + 0.035):
            mb.add(*_box(2 * chw + 0.14, 0.07, 0.10, off=(0.0, yy, zde + 0.035)),
                   m_cuerpo)
        if con_carga:
            cx_ = rng.uniform(-0.10, 0.10)
            lc = min(0.85, 0.62 * (cb - ca))
            yc_ = 0.5 * (ca + cb) + rng.uniform(-0.1, 0.1)
            mb.add(*_box(1.5 * chw, lc, 0.32, off=(cx_, yc_, zpi + 0.16)),
                   _mat("madera"))
            mb.add(*_box(1.5 * chw - 0.10, lc - 0.10, 0.06, off=(cx_, yc_, zpi + 0.33)),
                   _mat("faro"))          # caja de limones (amarillo del faro)

    # ---- baca con equipaje
    if con_baca:
        ya, yb = y1 + 0.14, y2 - 0.10
        if tipo in ("furgoneta", "familiar", "todoterreno"):
            yb = min(yb, ya + 1.9)
        zt = zroof + 0.6 * domo
        xr = 0.80 * wr
        for sx in (-1, 1):
            mb.add(*_box(0.035, yb - ya, 0.03, off=(sx * xr, 0.5 * (ya + yb), zt + 0.06)),
                   m_cromo)
            for yy in (ya + 0.05, yb - 0.05):
                mb.add(*_box(0.04, 0.05, 0.22, off=(sx * xr, yy, zt - 0.05)), m_cromo)
        nb = 3 if (yb - ya) > 1.0 else 2
        for yy in _linspace(ya + 0.05, yb - 0.05, nb):
            mb.add(*_box(2 * xr, 0.035, 0.025, off=(0.0, yy, zt + 0.065)), m_cromo)
        lm = min(0.80, 0.55 * (yb - ya))
        mb.add(*_box(1.05 * xr, lm, 0.24,
                     off=(-0.30 * xr, ya + 0.08 + lm / 2, zt + 0.20)), _mat("madera"))
        if (yb - ya) > 0.9:
            mb.add(*_box(0.80 * xr, 0.42, 0.17,
                         off=(0.42 * xr, yb - 0.30, zt + 0.165)), _mat("piloto"))

    mb.recentrar()
    ob = mb.build(nombre, parent_collection)
    ob["coche_tipo"] = tipo
    ob["coche_tris"] = mb.tris()
    return ob


# ---------------------------------------------------------------------------
# API PUBLICA
# ---------------------------------------------------------------------------
def build_coche(parent_collection, tipo="compacto", color=(0.80, 0.06, 0.04),
                seed=0, expresion=None, boca=None, **opciones):
    """Coche-espectador estilo Cars (malla unica COCHE_<tipo>), frontal a +Y,
    origen en el centro de la base y ruedas apoyadas exactamente en z=0.

    opciones (None = por seed): baca, bitono, franjas, carga (bool)."""
    desconocidas = sorted(k for k in opciones if k not in OPCIONES)
    if desconocidas:
        raise TypeError("build_coche() no admite las opciones %s (validas: %s)"
                        % (desconocidas, ", ".join(OPCIONES)))
    canon = _ALIAS_TIPO.get(tipo, tipo)
    if canon not in _TIPOS:
        raise ValueError("tipo debe ser uno de %s (o el alias 'furgo')" % (TIPOS,))
    rng = random.Random(7919 * int(seed) + 101 * TIPOS.index(canon) + 17)
    e_seed = rng.choice(("abierto", "abierto", "feliz", "feliz", "sorpresa"))
    b_seed = rng.choice(("sonrisa", "sonrisa", "abierta", "dientes", "rejilla"))
    if expresion is None:
        expresion = e_seed
    expresion = _ALIAS_EXPRESION.get(expresion, expresion)
    if expresion not in EXPRESIONES:
        raise ValueError("expresion debe ser 'abierto', 'feliz' o 'sorpresa' "
                         "(alias: 'sonrisa', 'guino')")
    if boca is None:
        boca = "abierta" if expresion == "sorpresa" else b_seed
    if boca not in BOCAS:
        raise ValueError("boca debe ser una de %s" % (BOCAS,))
    return _construir("%s_%s" % (PREFIX, tipo), canon, _TIPOS[canon], color, rng,
                      expresion, boca, opciones, parent_collection)


_PESOS_FILA = (("compacto", 3.0), ("topolino", 2.0), ("sedan", 2.0),
               ("familiar", 1.5), ("deportivo", 1.5), ("furgoneta", 1.5),
               ("pickup", 1.0), ("todoterreno", 1.0), ("ape", 1.0))


def _elige_tipos(rng, n):
    """n tipos por sorteo ponderado SIN repetir hasta agotar la bolsa."""
    out, bolsa = [], []
    while len(out) < n:
        if not bolsa:
            bolsa = list(_PESOS_FILA)
        u = rng.uniform(0.0, sum(p for _, p in bolsa))
        acc, k = 0.0, 0
        for k, (_t, p) in enumerate(bolsa):
            acc += p
            if u <= acc:
                break
        out.append(bolsa.pop(k)[0])
    return out


def build_fila_aparcada(parent_collection, n=6, seed=0):
    """Fila de n coches aparcados lado a lado (en X), mirando a +Y, con el
    mismo paso y jitter que coches_kit.py. Devuelve el Empty COCHE_fila.

    Nota: misma distribucion que v1 (semiplaza ~1.02 m + hueco 0.55-0.85 m,
    jitter x +-0.08, y +-0.30, giro +-6 grados, fila centrada en el origen,
    ~13.4-13.9 m de ancho con n=6), pero NO los mismos numeros para una seed
    dada: v2 sortea 10 colores, 9 tipos y el estilo de boca."""
    rng = random.Random(7919 * seed + 331)
    root = bpy.data.objects.new("%s_fila" % PREFIX, None)
    root.empty_display_size = 1.5
    parent_collection.objects.link(root)

    colores = list(COLORES_VIVOS)
    rng.shuffle(colores)
    expresiones = (list(EXPRESIONES) * ((n + 2) // 3))[:n]
    rng.shuffle(expresiones)
    bocas = (list(BOCAS) * ((n + 3) // 4))[:n]
    rng.shuffle(bocas)
    tipos = _elige_tipos(rng, n)

    half = 1.02                     # plaza de aparcamiento (como el kit v1)
    cursor = 0.0
    xs = []
    for i in range(n):
        cursor += half
        xs.append(cursor)
        cursor += half + rng.uniform(0.55, 0.85)
    centro = (xs[0] + xs[-1]) / 2.0 if xs else 0.0
    for i, x in enumerate(xs):
        expr = expresiones[i]
        ob = build_coche(parent_collection, tipo=tipos[i],
                         color=colores[i % len(colores)][1],
                         seed=seed * 100 + i, expresion=expr,
                         boca=("abierta" if expr == "sorpresa" else bocas[i]))
        ob.parent = root
        ob.location = (x - centro + rng.uniform(-0.08, 0.08),
                       rng.uniform(-0.30, 0.30), 0.0)
        ob.rotation_euler = (0.0, 0.0, math.radians(rng.uniform(-6.0, 6.0)))
    return root


def build_muestrario(parent_collection, seed=0, paso=3.2):
    """Los 9 tipos en fila (Empty COCHE_muestrario), para inspeccion."""
    root = bpy.data.objects.new("%s_muestrario" % PREFIX, None)
    root.empty_display_size = 1.5
    parent_collection.objects.link(root)
    for i, tipo in enumerate(TIPOS):
        ob = build_coche(parent_collection, tipo=tipo,
                         color=COLORES_VIVOS[i % len(COLORES_VIVOS)][1],
                         seed=seed + i, expresion=EXPRESIONES[i % 3],
                         boca=BOCAS[i % 4])
        ob.parent = root
        ob.location = ((i - (len(TIPOS) - 1) / 2.0) * paso, 0.0, 0.0)
    return root


def build(parent_collection, seed=0, **params):
    """Muestra: fila de 6 coches-espectador aparcados. Devuelve el Empty raiz."""
    return build_fila_aparcada(parent_collection, n=params.get("n", 6), seed=seed)
