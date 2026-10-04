"""encaje_mclaren.py — encaje del McLaren de piedra en el sitio del tunel.

Blender 5.1 (sin shapely). Lee la geometria (geometria_3d.json o un
snapshot) y reproduce el MARCO LOCAL del coche tal como lo calcula
integrar_escena.zona_tunel: s_face = s_mid - 0.42*ancho, origen = p -
n*0.65R, z0 = p.z - 1.4; orientacion sx=-1 (+X local = -n, morro tierra
adentro, +Y = t, lado_visible=-1) o sx=+1 (+X = +n, morro al mar, +Y = -t,
lado_visible=+1). Con ello:
  * Sitio.evaluar(obj): muestras de pista bajo la huella del coche (rayo
    vertical sobre la malla en el eje y en los dos bordes + 6 m: colision
    si la malla asoma por encima de la calzada), fraccion del coche
    EXPUESTA sobre el terreno por zonas (morro / centro / zaga / macizo) y
    fraccion de la huella sobre el MAR.
  * Sitio.malla_terreno / malla_pista / malla_mar: mallas del sitio en
    coordenadas locales para los previews del test.
  * Sitio.colocacion(): (cx, cy, z0, ang_z, lado_visible) para clone().
  * Sitio.local / mundo / terreno: marco local <-> mundo y cota del
    terreno (sin bpy: el python del sistema puede importar este modulo,
    p. ej. terreno_montana.py para recortar el terreno junto al coche).
Uso: test_montana_mclaren.py (seccion 'sitio') y el coordinador (T7).
Ronda 15 (vuelta 1): cargar() usa la geometria MAS RECIENTE (antes el
snapshot del 02/10, cuyo terreno difiere hasta 22 m junto al morro; la
pista es la misma) y evaluar() mide tambien cuanto queda el coche BAJO el
terreno por zonas (enterrado).
Ronda 15 (vuelta 2, B2-10): Sitio.holgura(obj) = distancia horizontal del
borde de la calzada a la roca (rayos a 1 y 3 m, fuera del tunel); evaluar()
la devuelve en res['holgura'] y resumen() la imprime (el pie del
afloramiento del morro en s 714-742 debe quedar a >= 4 m).
Ronda 15 (vuelta 3, J10/B15/B11): sitio_de_build(radio, ancho, z_fondo,
lado_visible) devuelve el Sitio del integrador SOLO si esos parametros de
build() son los suyos (z_fondo == -(z_pista(s_face) + 8)); TerrenoMalla
(sitio, TERRENO) da la cota de la malla REAL del terreno de la escena
(triangulos del render, rayo vertical) en el marco local del coche, con la
misma firma que Sitio.terreno: f(lx, ly) -> (z_local, es_mar).
montana_mclaren.build(terreno='auto') los usa para la falda de hierba y
caliza meteorizada hasta el contacto con el terreno, las matas que el
terreno tapaba y las cuencas oscuras medio enterradas ('cueva').
"""

import json
import math
import os

try:                                 # sin Blender solo funcionan las partes 2D
    import bpy
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
except ImportError:                  # python del sistema
    bpy = bmesh = Vector = BVHTree = None

AQUI = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(AQUI, "_geom_snapshot_mclaren.json")
GEOMETRIA = os.path.join(os.path.dirname(AQUI), "geometria_3d.json")


def cargar(ruta=None):
    """Geometria: la ruta dada; si no, la MAS RECIENTE de geometria_3d.json
    (la del pipeline) y el snapshot del constructor. None si no hay
    ninguna."""
    if ruta:
        cands = [ruta]
    else:
        cands = sorted((r for r in (GEOMETRIA, SNAPSHOT) if os.path.exists(r)),
                       key=os.path.getmtime, reverse=True)
    for r in cands:
        if r and os.path.exists(r):
            with open(r, encoding="utf-8") as f:
                G = json.load(f)
            G["_ruta"] = r
            return G
    return None


class Sitio:
    def __init__(self, G, radio, ancho, sx=-1.0, ds=0.0):
        self.G, self.R, self.W = G, float(radio), float(ancho)
        self.S = G["muestras"]
        self.N, self.paso, self.L = G["n"], G["paso_m"], G["largo_m"]
        self.cur = {c["n"]: c for c in G["curvas"]}
        T = G.get("terreno")         # None si aun no hay rejilla (terreno_montana la esta haciendo)
        self.T = T
        self.sx = -1.0 if sx < 0 else 1.0
        s_a = self.cur[2]["s_idx"] * self.paso
        s_b = self.cur[3]["s_idx"] * self.paso
        self.s_mid = (s_a + s_b) / 2.0 + 20.0
        self.s_face = self.s_mid - 0.42 * self.W + ds
        pf = self.S[self.idx(self.s_face)]
        self.pf = pf
        n = (pf["nx"], pf["ny"])
        self.n = n
        self.t = (pf["ny"], -pf["nx"])
        # el tunel pasa por x local = -0.65R en las dos orientaciones:
        # origen = p - n*0.65R si +X = -n (sx=-1); p + n*0.65R si +X = +n
        self.cx = pf["x"] + self.sx * n[0] * 0.65 * self.R
        self.cy = pf["y"] + self.sx * n[1] * 0.65 * self.R
        self.z0 = pf["z"] - 1.4
        self.ex = (self.sx * n[0], self.sx * n[1])
        self.ey = (-self.ex[1], self.ex[0])
        self.ang = math.atan2(self.ex[1], self.ex[0])
        self.lado_visible = -1.0 if self.sx < 0 else 1.0

    def idx(self, s):
        return int(round(((s % self.L) / self.paso))) % self.N

    def colocacion(self):
        """(cx, cy, z0, ang_z, lado_visible) para clone(raiz, (cx, cy, z0), ang_z)."""
        return self.cx, self.cy, self.z0, self.ang, self.lado_visible

    def local(self, xw, yw):
        dx, dy = xw - self.cx, yw - self.cy
        return dx * self.ex[0] + dy * self.ex[1], dx * self.ey[0] + dy * self.ey[1]

    def mundo(self, lx, ly):
        return (self.cx + self.ex[0] * lx + self.ey[0] * ly,
                self.cy + self.ex[1] * lx + self.ey[1] * ly)

    def terreno(self, lx, ly):
        """(z del terreno en cotas LOCALES, es_mar) por bilineal."""
        T = self.T
        if T is None:
            return -self.z0, True
        xw, yw = self.mundo(lx, ly)
        fi = (xw - T["x0"]) / T["cell"]
        fj = (yw - T["y0"]) / T["cell"]
        i, j = int(math.floor(fi)), int(math.floor(fj))
        nx = T["nx"]
        if i < 0 or j < 0 or i >= nx - 1 or j >= T["ny"] - 1:
            return -self.z0, True
        a, b = fi - i, fj - j
        z = T["z"]
        zz = (z[j * nx + i] * (1 - a) * (1 - b) + z[j * nx + i + 1] * a * (1 - b) +
              z[(j + 1) * nx + i] * (1 - a) * b + z[(j + 1) * nx + i + 1] * a * b)
        return zz - self.z0, bool(T["mar"][j * nx + i])

    def muestras(self, x_rng, y_rng):
        """Muestras de pista en la caja local: (s, lx, ly, z_loc, w, nlx, nly)."""
        out = []
        for i, q in enumerate(self.S):
            lx, ly = self.local(q["x"], q["y"])
            if x_rng[0] <= lx <= x_rng[1] and y_rng[0] <= ly <= y_rng[1]:
                nlx = q["nx"] * self.ex[0] + q["ny"] * self.ex[1]
                nly = q["nx"] * self.ey[0] + q["ny"] * self.ey[1]
                out.append((i * self.paso, lx, ly, q["z"] - self.z0, q["w"], nlx, nly))
        return out

    @staticmethod
    def _arbol(obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        tree = BVHTree.FromBMesh(bm)
        bm.free()
        return tree

    @staticmethod
    def _techo(tree, x, y):
        loc, _n, _i, _d = tree.ray_cast(Vector((x, y, 600.0)), Vector((0.0, 0.0, -1.0)), 1200.0)
        return None if loc is None else loc.z

    def evaluar(self, obj, margen=6.0, dz=0.3):
        """Evalua la malla `obj` (coordenadas locales del coche, sin
        transformar) en el sitio. Devuelve dict: n_col, colisiones [(s, lx,
        ly, z_pista, z_malla)], expuesto {zona: fraccion}, mar (fraccion de la
        huella sobre el mar), techo_terreno (max terreno sobre la cabina)."""
        R = self.R
        tree = self._arbol(obj)
        bb = obj["bbox"] if "bbox" in obj else (-20 * R, -400, -100, 10 * R, 400, 200)
        col, n_tunel = [], 0
        for s, lx, ly, zp, w, nlx, nly in self.muestras((bb[0] - 1, bb[3] + 1), (bb[1] - 1, bb[4] + 1)):
            if abs(lx + 0.65 * R) < 12.0 and abs(ly) < 0.5 * self.W + 2.5 + margen:
                n_tunel += 1                 # galeria a traves de la rueda: la taladra el integrador
                continue
            for k in (0.0, 1.0, -1.0):
                px, py = lx + k * nlx * (0.5 * w + margen), ly + k * nly * (0.5 * w + margen)
                zt = self._techo(tree, px, py)
                if zt is not None and zt > zp - dz:
                    col.append((s, lx, ly, zp, zt))
                    break
        zonas = {"morro": (0.6 * R, 2.9 * R), "centro": (-7.9 * R, 0.6 * R),
                 "zaga": (-10.1 * R, -7.9 * R)}
        wmax = 0.5 * self.W - 0.03 * R
        exp, ent, mar_n, mar_tot, z_t_max = {}, {}, 0, 0, -1e9
        for zona, (xa, xb) in zonas.items():
            n_e = n_t = 0
            e_max = 0.0
            for i in range(14):
                x = xa + (xb - xa) * (i + 0.5) / 14.0
                for j in range(9):
                    y = -0.9 * wmax + 1.8 * wmax * j / 8.0
                    zc_ = self._techo(tree, x, y)
                    if zc_ is None:
                        continue
                    zt, es_mar = self.terreno(x, y)
                    n_t += 1
                    n_e += 1 if zc_ > zt + 0.5 else 0
                    e_max = max(e_max, zt - zc_)
                    mar_tot += 1
                    mar_n += 1 if es_mar else 0
                    if zona == "centro":
                        z_t_max = max(z_t_max, zt)
            exp[zona] = n_e / float(n_t) if n_t else 0.0
            ent[zona] = e_max            # m que el terreno sobrepasa a la malla (lo mas hondo)
        n_e = n_t = 0
        for i in range(24):
            x = bb[0] + (bb[3] - bb[0]) * (i + 0.5) / 24.0
            if -10.1 * R <= x <= 2.9 * R:
                continue
            for j in range(13):
                y = bb[1] + (bb[4] - bb[1]) * (j + 0.5) / 13.0
                zc_ = self._techo(tree, x, y)
                if zc_ is None or zc_ < 0.5:
                    continue
                zt, es_mar = self.terreno(x, y)
                n_t += 1
                n_e += 1 if zc_ > zt + 0.5 else 0
                mar_tot += 1
                mar_n += 1 if es_mar else 0
        exp["macizo"] = n_e / float(n_t) if n_t else 0.0
        return dict(n_col=len(col), colisiones=col, n_tunel=n_tunel, expuesto=exp,
                    enterrado=ent, mar=(mar_n / float(mar_tot) if mar_tot else 0.0),
                    techo_terreno=z_t_max, holgura=self.holgura(obj, tree=tree, margen=margen))

    def holgura(self, obj, tree=None, alturas=(1.0, 3.0), dmax=30.0, minimo=4.0, margen=6.0):
        """Ronda 15 v2 (B2-10): distancia horizontal desde el BORDE de la
        calzada hasta la roca (rayo perpendicular a la pista, hacia fuera, a
        `alturas` m sobre la cota del eje) en todas las muestras de la caja
        de la malla salvo las del tunel de la rueda. Devuelve dict: min (m),
        s y lado del minimo, n_bajo (muestras con algun rayo a < `minimo`
        m), bajo [(s, lado, h, d)] y n (muestras medidas). El pie del
        afloramiento del morro junto a la salida del tunel (s 714-742) debe
        quedar a >= 4 m."""
        R = self.R
        if tree is None:
            tree = self._arbol(obj)
        bb = obj["bbox"] if "bbox" in obj else (-20 * R, -400, -100, 10 * R, 400, 200)
        d_min, s_min, l_min, bajo, n = dmax, None, 0, [], 0
        for s, lx, ly, zp, w, nlx, nly in self.muestras((bb[0] - dmax, bb[3] + dmax),
                                                         (bb[1] - dmax, bb[4] + dmax)):
            if abs(lx + 0.65 * R) < 12.0 and abs(ly) < 0.5 * self.W + 2.5 + margen:
                continue
            n += 1
            for lado in (-1.0, 1.0):
                for h in alturas:
                    o = Vector((lx + lado * nlx * 0.5 * w, ly + lado * nly * 0.5 * w, zp + h))
                    loc, _n, _i, d = tree.ray_cast(o, Vector((lado * nlx, lado * nly, 0.0)), dmax)
                    if loc is None:
                        continue
                    if d < minimo:
                        bajo.append((s, int(lado), h, round(d, 2)))
                    if d < d_min:
                        d_min, s_min, l_min = d, s, int(lado)
        return dict(min=d_min, s=s_min, lado=l_min, n_bajo=len({b[0] for b in bajo}),
                    bajo=bajo, n=n)

    # ------------------------------------------------- mallas del sitio ----
    def _nueva(self, nombre, coll, verts, faces, mat):
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(verts, [], faces)
        me.update()
        if mat is not None:
            me.materials.append(mat)
        ob = bpy.data.objects.new(nombre, me)
        coll.objects.link(ob)
        return ob

    def malla_terreno(self, coll, x_rng, y_rng, paso=6.0, mat=None, mat_mar=None):
        """Rejilla del terreno (cotas locales) en la caja local; las celdas
        de mar llevan `mat_mar` (indice 1)."""
        nx = int((x_rng[1] - x_rng[0]) / paso) + 1
        ny = int((y_rng[1] - y_rng[0]) / paso) + 1
        verts, mar = [], []
        for j in range(ny):
            for i in range(nx):
                x = x_rng[0] + i * paso
                y = y_rng[0] + j * paso
                z, es_mar = self.terreno(x, y)
                verts.append((x, y, z))
                mar.append(es_mar)
        faces, fm = [], []
        for j in range(ny - 1):
            for i in range(nx - 1):
                a = j * nx + i
                faces.append((a, a + 1, a + nx + 1, a + nx))
                fm.append(mar[a] and mar[a + 1] and mar[a + nx] and mar[a + nx + 1])
        ob = self._nueva("SITIO_terreno", coll, verts, faces, mat)
        if mat_mar is not None:
            ob.data.materials.append(mat_mar)
            for p, m in zip(ob.data.polygons, fm):
                p.material_index = 1 if m else 0
        for p in ob.data.polygons:
            p.use_smooth = True
        return ob

    def malla_mar(self, coll, x_rng, y_rng, mat=None):
        """Plano del mar (z local = -z0)."""
        z = -self.z0 + 0.05
        verts = [(x_rng[0], y_rng[0], z), (x_rng[1], y_rng[0], z),
                 (x_rng[1], y_rng[1], z), (x_rng[0], y_rng[1], z)]
        return self._nueva("SITIO_mar", coll, verts, [(0, 1, 2, 3)], mat)

    def malla_pista(self, coll, x_rng, y_rng, mat=None, dz=0.3):
        """Cinta de la calzada (ancho w) con las muestras de la caja."""
        ms = self.muestras(x_rng, y_rng)
        verts, faces = [], []
        prev_s = None
        for s, lx, ly, z, w, nlx, nly in ms:
            a = (lx + nlx * 0.5 * w, ly + nly * 0.5 * w, z + dz)
            b = (lx - nlx * 0.5 * w, ly - nly * 0.5 * w, z + dz)
            if prev_s is not None and abs(s - prev_s) <= 1.5 * self.paso:
                k = len(verts)
                verts += [a, b]
                faces.append((k - 2, k - 1, k + 1, k))
            else:
                verts += [a, b]
            prev_s = s
        return self._nueva("SITIO_pista", coll, verts, faces, mat)


def resumen(nombre, res):
    """Linea de informe para una evaluacion."""
    e = res["expuesto"]
    en = res.get("enterrado", {})
    ho = res.get("holgura")
    txt_h = ("" if not ho else " | roca a %.1f m del borde como minimo (s %s lado %+d), %d muestras a < 4 m"
             % (ho["min"], "-" if ho["s"] is None else "%.0f" % ho["s"], ho["lado"], ho["n_bajo"]))
    return ("%-34s pista bajo huella: %3d muestras%s (tunel %d) | expuesto morro %3.0f%% centro %3.0f%% "
            "zaga %3.0f%% macizo %3.0f%% | bajo terreno hasta: morro %.0f m centro %.0f m | "
            "mar bajo huella %3.0f%% | terreno max sobre cabina %.0f m%s"
            % (nombre, res["n_col"],
               (" (s %.0f-%.0f)" % (res["colisiones"][0][0], res["colisiones"][-1][0])
                if res["colisiones"] else ""), res["n_tunel"],
               100 * e["morro"], 100 * e["centro"], 100 * e["zaga"], 100 * e["macizo"],
               en.get("morro", 0.0), en.get("centro", 0.0),
               100 * res["mar"], res["techo_terreno"], txt_h))


# ------------------------------------------- terreno real del sitio (v3) ----
def sitio_de_build(radio, ancho, z_fondo, lado_visible, tol=0.05, ruta=None):
    """Ronda 15 v3: Sitio de integrar_escena.zona_tunel que corresponde a
    unos parametros de montana_mclaren.build(), o None. El integrador
    construye con z_fondo = -(z_pista(s_face) + 8) y lado_visible = -1
    (+X local = -n); si z_fondo no es ese (test, otra escena) no hay sitio."""
    G = cargar(ruta)
    if G is None or G.get("terreno") is None:
        return None
    sit = Sitio(G, radio, ancho, sx=(-1.0 if float(lado_visible) < 0.0 else 1.0))
    if abs(-(sit.pf["z"] + 8.0) - float(z_fondo)) > tol:
        return None
    return sit


class TerrenoMalla:
    """Ronda 15 v3: cota de la malla TERRENO de la escena (sus triangulos
    de render, en MUNDO) en el marco LOCAL del coche del sitio `sit`:
    f(lx, ly) -> (z_local, es_mar), como Sitio.terreno. Solo carga los
    triangulos de la caja local `caja` = (x0, y0, x1, y1) + margen. es_mar
    = cota < nivel del mar + 0.25 (o sin terreno debajo)."""

    def __init__(self, sit, obj, caja, margen=20.0):
        import numpy as np
        self.sit = sit
        self.nivel = float(sit.G.get("nivel_mar", 0.0))
        xs, ys = [], []
        for lx in (caja[0] - margen, caja[2] + margen):
            for ly in (caja[1] - margen, caja[3] + margen):
                xw, yw = sit.mundo(lx, ly)
                xs.append(xw)
                ys.append(yw)
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        me = obj.data
        me.calc_loop_triangles()
        nv, nt = len(me.vertices), len(me.loop_triangles)
        co = np.empty(nv * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        mw = np.array(obj.matrix_world, dtype=float)
        cw = co.reshape(-1, 3).astype(float) @ mw[:3, :3].T + mw[:3, 3]
        tri = np.empty(nt * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("vertices", tri)
        tri = tri.reshape(-1, 3)
        den = (cw[:, 0] > x0) & (cw[:, 0] < x1) & (cw[:, 1] > y0) & (cw[:, 1] < y1)
        tri = tri[den[tri].any(axis=1)]
        usados, inv = np.unique(tri.ravel(), return_inverse=True)
        self.n_tris = int(len(tri))
        self.tree = (BVHTree.FromPolygons(cw[usados].tolist(), inv.reshape(-1, 3).tolist())
                     if len(tri) else None)
        self.z_tope = float(cw[usados, 2].max()) + 50.0 if len(tri) else 1000.0
        self.abajo = Vector((0.0, 0.0, -1.0))

    def __call__(self, lx, ly):
        z0 = self.sit.z0
        if self.tree is None:
            return self.nivel - z0, True
        xw, yw = self.sit.mundo(lx, ly)
        loc = self.tree.ray_cast(Vector((xw, yw, self.z_tope)), self.abajo, 4000.0)[0]
        if loc is None:
            return self.nivel - z0, True
        return loc.z - z0, bool(loc.z < self.nivel + 0.25)
