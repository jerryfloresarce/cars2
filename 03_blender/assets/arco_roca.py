"""arco_roca.py — Arco de roca natural de Porto Corsa (Cars 2), Blender 5.1.

Arco natural que cruza sobre la carretera del acantilado (la pista pasa por
debajo, como un tunel corto natural): dos ESTRIBOS rocosos macizos que nacen
del suelo y un DINTEL-arco irregular de caliza ocre-gris estratificada
uniendolos por arriba, con matas verdes colgando del borde.

100%% procedural: tubo loft (anillos superelipticos) barrido a lo largo de un
perfil pared-arco-pared con marcos por diferencias finitas + ruido fbm +
repisas/estratos periodicos + bolos sueltos al pie. Sin bpy.ops, sin texturas.

GARANTIA DE GALIBO: el hueco libre es >= luz x alto_libre (la carretera pasa
en direccion +Y a traves del origen). El perfil interior se disenya con
margen y ademas cada vertice se proyecta fuera de la caja de galibo
(clamp de seguridad).

Piezas (kit):
  build(parent_collection, luz=18, alto_libre=9, grosor=10, seed=0,
        con_vegetacion=True)                 -> Empty raiz ARCO_roca
  build_roca(parent_collection, ...)         -> malla ARCO_cuerpo (~5k tris)
  build_vegetacion(parent_collection, ...)   -> malla ARCO_vegetacion (<1k)

Unidades en metros. Origen en el centro del hueco a nivel de suelo (z=0),
eje del hueco alineado con +Y.
"""

import math
import random

import bpy
import bmesh
from mathutils import Vector

# ---------------------------------------------------------------- ruido ----
try:
    from mathutils import noise as _mnoise

    def _n3(x, y, z):
        return _mnoise.noise(Vector((x, y, z)))
except Exception:  # fallback puro python (valor-ruido trilineal)
    def _h(ix, iy, iz):
        n = (ix * 374761393 + iy * 668265263 + iz * 1440662683) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

    def _n3(x, y, z):
        ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
        fx, fy, fz = x - ix, y - iy, z - iz

        def s(t):
            return t * t * (3.0 - 2.0 * t)

        fx, fy, fz = s(fx), s(fy), s(fz)
        v = 0.0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = ((fx if dx else 1 - fx) * (fy if dy else 1 - fy) *
                         (fz if dz else 1 - fz))
                    v += w * _h(ix + dx, iy + dy, iz + dz)
        return v * 2.0 - 1.0


def _fbm(x, y, z, so):
    """3 octavas a escala de arco (~45 m): bultos, medianos, grano."""
    return (_n3(x * 0.085 + so, y * 0.085 + so * 0.7, z * 0.085) * 2.1 +
            _n3(x * 0.22 + so * 2.1, y * 0.22 + 11.3, z * 0.22) * 0.85 +
            _n3(x * 0.55 + so * 3.3, y * 0.55 + 23.7, z * 0.55 + 5.1) * 0.35)


def _sstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _sq(v, q):
    """Superelipse: firma de v con |v|^(2/q)."""
    return math.copysign(abs(v) ** (2.0 / q), v)


# --------------------------------------------------- perfil del hueco ------
_UW = 0.24        # fraccion del recorrido que es pared (cada lado)
_Z_BASE = -2.6    # faldon enterrado bajo el suelo


def _perfil(u, w_in, z_spring, h_top, lean):
    """Punto (x, z) del borde interior del hueco. u=0 base izq, u=1 base dcha.

    Pared que se abre en la base (lean) + arco eliptico por arriba.
    """
    if u < _UW:
        t = u / _UW
        return -(w_in + lean * (1.0 - t) ** 1.5), \
            _Z_BASE + (z_spring - _Z_BASE) * t
    if u > 1.0 - _UW:
        t = (1.0 - u) / _UW
        return (w_in + lean * (1.0 - t) ** 1.5), \
            _Z_BASE + (z_spring - _Z_BASE) * t
    s = (u - _UW) / (1.0 - 2.0 * _UW)
    return -w_in * math.cos(math.pi * s), \
        z_spring + (h_top - z_spring) * math.sin(math.pi * s)


def _clamp_galibo(x, z, hw, hh):
    """Proyecta fuera de la caja de galibo [-hw,hw] x [0,hh] (todo Y)."""
    if 0.0 < z < hh and abs(x) < hw:
        if (hw - abs(x)) <= (hh - z):
            x = math.copysign(hw, x if x != 0.0 else 1.0)
        else:
            z = hh
    return x, z


# ---------------------------------------------------------- geometria ------
def _arch_geometry(luz, alto_libre, grosor, seed):
    """Malla del arco (tubo loft + bolos) y candidatos de vegetacion.

    Devuelve (verts, faces, candidates) con candidates = lista de
    (pos Vector, normal Vector, cs, sn) para anclar matas.
    """
    rng = random.Random(seed * 73 + 19)
    so = seed * 17.37 + 3.1

    w_in = luz * 0.5 + 2.0          # borde interior con margen lateral
    z_spring = alto_libre * 0.62    # arranque del arco
    h_top = alto_libre + 3.8        # apice del hueco
    lean = 0.9                      # las paredes se abren hacia la base
    hw = luz * 0.5 + 0.35           # caja de galibo + guarda
    hh = alto_libre + 0.35

    a_crown, a_base = grosor * 0.28, grosor * 0.62   # semiespesor radial
    b_crown, b_base = grosor * 0.45, grosor * 0.85   # semiancho en Y
    band_h, ledge_amp, qr = 3.0, 1.35, 3.2
    asym = 0.16 * _n3(so * 1.1, 4.2, 9.9)  # un estribo mas gordo que el otro

    n_st, n_ring = 64, 36
    verts, faces, cands = [], [], []
    rings = []
    eps = 0.004

    for j in range(n_st):
        u = j / (n_st - 1.0)
        px, pz = _perfil(u, w_in, z_spring, h_top, lean)
        # marco local por diferencias finitas
        x2, z2 = _perfil(min(u + eps, 1.0), w_in, z_spring, h_top, lean)
        x1, z1 = _perfil(max(u - eps, 0.0), w_in, z_spring, h_top, lean)
        tx, tz = x2 - x1, z2 - z1
        tl = math.hypot(tx, tz) or 1.0
        tx, tz = tx / tl, tz / tl
        nx, nz = -tz, tx            # normal hacia FUERA del hueco

        # el borde interior solo puede desplazarse hacia fuera (hueco organico)
        pn = max(0.0, 1.2 * _n3(u * 3.1 + so * 1.3, 0.0, 3.3))
        px += nx * pn
        pz += nz * pn

        # engorde hacia los estribos + variacion organica + asimetria
        f = _sstep((0.36 - min(u, 1.0 - u)) / 0.36)
        lado = 1.0 if u < 0.5 else -1.0
        va = 1.0 + 0.32 * _n3(u * 4.1 + so, 1.3, 7.7) + f * asym * lado
        a = (a_crown + (a_base - a_crown) * f ** 1.3) * va
        b = (b_crown + (b_base - b_crown) * f ** 1.3) * \
            (1.0 + 0.22 * _n3(u * 3.3 + so * 2.2, 5.1, 2.9) +
             f * asym * lado * 0.7)

        cx, cz = px + nx * a, pz + nz * a   # centro del tubo
        ring = []
        for k in range(n_ring):
            ph = 2.0 * math.pi * k / n_ring
            cs, sn = _sq(math.cos(ph), qr), _sq(math.sin(ph), qr)
            wx = cx + nx * a * cs
            wz = cz + nz * a * cs
            wy = b * sn
            nrm = Vector((nx * cs, sn, nz * cs))
            if nrm.length < 1e-6:
                nrm = Vector((nx, 0.0, nz))
            nrm.normalize()

            # ruido fbm (amortiguado en la cara interior del hueco)
            ampf = 0.25 + 0.75 * _sstep((cs + 0.85) / 1.1)
            d = _fbm(wx, wy, wz, so) * ampf
            # repisas/estratos: cornisas periodicas, nunca en la cara interior
            steep = math.hypot(nrm.x, nrm.y)
            phase = 2.1 * _n3(wx * 0.05 + so, wy * 0.05, 4.4)
            ledge = max(0.0, math.cos(2.0 * math.pi * wz / band_h +
                                      phase)) ** 3
            bul = ledge_amp * ledge * steep * _sstep((cs + 0.5) / 0.5)
            wx += nrm.x * (d + bul)
            wy += nrm.y * (d + bul * 0.5)
            wz += nrm.z * d - abs(bul) * 0.25
            # cresta irregular: levanta bultos en el lomo superior
            if nrm.z > 0.35:
                cr = 0.5 + 0.5 * _n3(wx * 0.10 + so * 4.7, wy * 0.10, 8.8)
                wz += cr * cr * 2.4 * nrm.z
            # jitter longitudinal en Y para romper los anillos
            wy += _n3(wx * 0.13 + so * 1.7, wz * 0.13, 2.2) * 0.9

            wx, wz = _clamp_galibo(wx, wz, hw, hh)
            if wz < _Z_BASE:
                wz = _Z_BASE
            ring.append(len(verts))
            verts.append((wx, wy, wz))
            if wz > 2.0:
                cands.append((Vector((wx, wy, wz)), nrm.copy(), cs, sn))
        rings.append(ring)

    for ra, rb in zip(rings, rings[1:]):
        for k in range(n_ring):
            k2 = (k + 1) % n_ring
            faces.append((ra[k], ra[k2], rb[k2], rb[k]))

    # tapas: polo enterrado en cada extremo
    for ring, uu in ((rings[0], 0.0), (rings[-1], 1.0)):
        px, pz = _perfil(uu, w_in, z_spring, h_top, lean)
        pole = len(verts)
        verts.append((px + math.copysign(a_base, px), 0.0, _Z_BASE - 1.2))
        for k in range(n_ring):
            k2 = (k + 1) % n_ring
            if uu == 0.0:
                faces.append((pole, ring[k], ring[k2]))
            else:
                faces.append((pole, ring[k2], ring[k]))

    # bolos sueltos al pie de los estribos (macizan la base)
    for _ in range(6):
        r = rng.uniform(1.4, 3.0)
        side = 1.0 if rng.random() < 0.5 else -1.0
        bx = side * (hw + 0.8 + 1.7 * r + rng.uniform(0.0, 4.5))
        by = rng.uniform(-1.3, 1.3) * b_base
        _blob(verts, faces, None, Vector((bx, by, r * 0.32)), r, 0.8, rng,
              flat=0.75)

    return verts, faces, cands


def _blob(verts, faces, face_mat, center, r, sz, rng, flat=1.0, mi=0):
    """Pedrusco/mata: esfera irregular low-poly (7x4)."""
    u_res, v_res = 7, 4
    rows = []
    for i in range(1, v_res):
        phi = math.pi * i / v_res
        zc, rc = math.cos(phi), math.sin(phi)
        row = []
        for k in range(u_res):
            th = 2.0 * math.pi * k / u_res + rng.random() * 0.5
            rr = r * (0.72 + 0.55 * rng.random())
            row.append(len(verts))
            verts.append((center.x + rc * rr * math.cos(th),
                          center.y + rc * rr * math.sin(th),
                          center.z + zc * r * sz * flat *
                          (0.8 + 0.4 * rng.random())))
        rows.append(row)
    top = len(verts)
    verts.append((center.x, center.y, center.z + r * sz * flat))
    bot = len(verts)
    verts.append((center.x, center.y, center.z - r * sz * 0.75))
    for k in range(u_res):
        k2 = (k + 1) % u_res
        faces.append((top, rows[0][k], rows[0][k2]))
        for i in range(len(rows) - 1):
            faces.append((rows[i][k], rows[i + 1][k],
                          rows[i + 1][k2], rows[i][k2]))
        faces.append((bot, rows[-1][k2], rows[-1][k]))
        if face_mat is not None:
            face_mat.extend([mi] * (len(rows) + 1))


# ------------------------------------------------------------ materiales ----
def _mat(name, color, rough=0.93):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                bsdf = n
                break
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*color, 1.0)
    return m


def _recalc_and_smooth(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True


# ----------------------------------------------------------------- piezas ----
def build_roca(parent_collection, luz=18.0, alto_libre=9.0, grosor=10.0,
               seed=0, _shared=None, **kw):
    """Cuerpo del arco ARCO_cuerpo: caliza ocre-gris estratificada + bolos."""
    verts, faces, cands = _arch_geometry(luz, alto_libre, grosor, seed)
    if _shared is not None:
        _shared["candidates"] = cands

    me = bpy.data.meshes.new("ARCO_cuerpo")
    me.from_pydata(verts, [], faces)
    me.validate()
    _recalc_and_smooth(me)

    mats = (
        _mat("MAT_ARCO_caliza", (0.520, 0.390, 0.205), 0.95),
        _mat("MAT_ARCO_caliza_clara", (0.685, 0.545, 0.300), 0.95),
        _mat("MAT_ARCO_caliza_oscura", (0.315, 0.228, 0.125), 0.95),
    )
    for m in mats:
        me.materials.append(m)

    # bandas de estratos alineadas con la fase de las cornisas
    so = seed * 17.37 + 3.1
    band_h = 3.0
    patron = (0, 1, 0, 2)
    for p in me.polygons:
        c = p.center
        if c.z < 1.3:
            p.material_index = 2  # zocalo oscuro
        else:
            phase = 2.1 * _n3(c.x * 0.05 + so, c.y * 0.05, 4.4)
            bnd = math.floor(c.z / band_h + phase / (2.0 * math.pi))
            p.material_index = patron[bnd % 4]

    obj = bpy.data.objects.new("ARCO_cuerpo", me)
    parent_collection.objects.link(obj)
    return obj


def build_vegetacion(parent_collection, luz=18.0, alto_libre=9.0,
                     grosor=10.0, seed=0, candidates=None, **kw):
    """Matas verdes ARCO_vegetacion colgando del borde y sobre los estribos."""
    if candidates is None:
        _v, _f, candidates = _arch_geometry(luz, alto_libre, grosor, seed)
    rng = random.Random(seed * 91 + 7)
    hw, hh = luz * 0.5 + 0.35, alto_libre + 0.35

    hangs = [c for c in candidates
             if abs(c[3]) > 0.6 and c[1].z > -0.2 and
             c[0].z > alto_libre + 1.5]
    hangs += [c for c in candidates
              if c[2] < -0.6 and c[0].z > alto_libre + 2.6]
    sits = [c for c in candidates if c[1].z > 0.55 and c[0].z > 3.0]
    rng.shuffle(hangs)
    rng.shuffle(sits)

    verts, faces, face_mat = [], [], []
    placed = []

    def ok_galibo(center, r, sz):
        zmin = center.z - r * sz * 0.95 - 0.3
        if abs(center.x) - 1.4 * r < hw and zmin < hh + 0.3:
            return False
        return True

    def place(pool, count, offset_fn, r_rng, sz):
        n = 0
        for pos, nrm, _cs, _sn in pool:
            if n >= count:
                break
            r = rng.uniform(*r_rng)
            center = offset_fn(pos, nrm, r)
            if not ok_galibo(center, r, sz):
                continue
            if any((center - p).length < 4.2 for p in placed):
                continue
            placed.append(center)
            _blob(verts, faces, face_mat, center, r, sz, rng,
                  mi=0 if rng.random() < 0.6 else 1)
            n += 1

    # colgantes del borde del dintel (hundidas en la roca, cayendo)
    place(hangs, 10,
          lambda p, nm, r: p - nm * (0.35 * r) - Vector((0, 0, r * 0.45)),
          (0.9, 1.6), 1.3)
    # asentadas sobre lomos y estribos (bien enraizadas)
    place(sits, 8,
          lambda p, nm, r: p + nm * 0.05 - Vector((0, 0, r * 0.38)),
          (1.2, 2.2), 0.62)

    me = bpy.data.meshes.new("ARCO_vegetacion")
    me.from_pydata(verts, [], faces)
    me.validate()
    _recalc_and_smooth(me)
    me.materials.append(_mat("MAT_ARCO_vegetacion", (0.070, 0.230, 0.055),
                             0.9))
    me.materials.append(_mat("MAT_ARCO_vegetacion_clara",
                             (0.150, 0.360, 0.085), 0.9))
    for p, mi in zip(me.polygons, face_mat):
        p.material_index = mi

    obj = bpy.data.objects.new("ARCO_vegetacion", me)
    parent_collection.objects.link(obj)
    return obj


def build(parent_collection, luz=18.0, alto_libre=9.0, grosor=10.0, seed=0,
          con_vegetacion=True, **params):
    """Arco natural completo. Devuelve el Empty raiz ARCO_roca."""
    root = bpy.data.objects.new("ARCO_roca", None)
    root.empty_display_size = 3.0
    parent_collection.objects.link(root)

    shared = {}
    roca = build_roca(parent_collection, luz=luz, alto_libre=alto_libre,
                      grosor=grosor, seed=seed, _shared=shared)
    roca.parent = root
    if con_vegetacion:
        veg = build_vegetacion(parent_collection, luz=luz,
                               alto_libre=alto_libre, grosor=grosor,
                               seed=seed,
                               candidates=shared.get("candidates"))
        veg.parent = root
    return root
