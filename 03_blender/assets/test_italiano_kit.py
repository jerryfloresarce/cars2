"""test_italiano_kit.py — Test headless del kit de ambiente italiano (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python
  "E:\\Escritorio\\claude-pc\\arnau-aseto-corsa\\03_blender\\assets\\test_italiano_kit.py"

Construye el escaparate build(), comprueba presupuestos de triangulos y
nombres, renderiza previews/italiano_kit.png (conjunto), italiano_ermita.png,
italiano_bancal.png (+ fuente, pergola, detalles) en EEVEE 1280x800 con sol
calido y cielo azul (view_transform Standard) y guarda blend/italiano_kit.blend.

Comprobacion de ORIENTACION (para el backface culling del kn5 de Assetto
Corsa): se parchea ik._MB.add y, por cada chunk anadido,
  - cerrado (cada arista aparece en ambos sentidos): volumen firmado
    (sum a.(b x c)/6 por triangulo en abanico) debe ser >= 0;
  - plano abierto (todas las normales paralelas y del mismo sentido): la
    normal media debe apuntar a la direccion esperada por material (puerta,
    vidriera, sol, fondo de hornacina y textos a +Y; hierba y agua a +Z;
    paneles 'sombra' de las ventanitas a +-X segun el lado);
  - abierto no plano (troncos, tubos, revoluciones sin polos): el flujo
    n.(c - centroide) ponderado por area debe ser positivo (caras hacia
    fuera en promedio).
"""

import importlib.util
import math
import os
import sys
from collections import Counter

import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(AQUI, "italiano_kit.py")

# --- escena vacia -----------------------------------------------------------
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for me in list(bpy.data.meshes):
    bpy.data.meshes.remove(me)
for ma in list(bpy.data.materials):
    bpy.data.materials.remove(ma)

# --- cargar modulo por ruta -------------------------------------------------
spec = importlib.util.spec_from_file_location("italiano_kit", MOD)
ik = importlib.util.module_from_spec(spec)
sys.modules["italiano_kit"] = ik
spec.loader.exec_module(ik)

fallos = []

# --- comprobacion de orientacion (monkeypatch de _MB.add) -------------------


def orientacion_chunk(verts, faces):
    """('cerrado', vol) | ('plano', normal, centro) | ('abierto', flujo) |
    ('degenerado',)."""
    edges = Counter()
    for f in faces:
        n = len(f)
        for i in range(n):
            edges[(f[i], f[(i + 1) % n])] += 1
    cerrado = all(c == 1 and edges.get((b, a), 0) == 1 for (a, b), c in edges.items())
    V = [Vector(v) for v in verts]
    if cerrado:
        vol = 0.0
        for f in faces:
            a = V[f[0]]
            for i in range(1, len(f) - 1):
                vol += a.dot(V[f[i]].cross(V[f[i + 1]]))
        return ("cerrado", vol / 6.0)
    normales, centros = [], []
    for f in faces:
        a = V[f[0]]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(1, len(f) - 1):
            n += (V[f[i]] - a).cross(V[f[i + 1]] - a)
        normales.append(n)
        centros.append(sum((V[i] for i in f), Vector()) / len(f))
    total = sum(normales, Vector())
    suma = sum(n.length for n in normales)
    if suma < 1e-12:
        return ("degenerado",)
    cc = sum(centros, Vector()) / len(centros)
    if total.length > 0.98 * suma:
        return ("plano", total.normalized(), cc)
    flujo = sum(n.dot(c - cc) for n, c in zip(normales, centros))
    norma = sum(n.length * (c - cc).length for n, c in zip(normales, centros))
    return ("abierto", flujo / max(norma, 1e-12))


# direccion esperada de los paneles/discos abiertos, por material
ESPERADO = {"vidrio": (0, 1, 0), "oro": (0, 1, 0), "madera_oscura": (0, 1, 0),
            "azul_hornacina": (0, 1, 0), "negro": (0, 1, 0), "blanco": (0, 1, 0),
            "hierba_seca": (0, 0, 1), "agua": (0, 0, 1)}
orient_stats = Counter()
orient_fallos = Counter()
_add_original = ik._MB.add


def _add_comprobado(self, verts, faces, mat, smooth=False):
    fr = sys._getframe(1)
    donde = "italiano_kit.py L%d (%s)" % (fr.f_lineno, fr.f_code.co_name)
    key = mat.name.replace("MAT_ITAL_", "")
    r = orientacion_chunk(verts, faces)
    orient_stats[r[0]] += 1
    msg = None
    if r[0] == "cerrado":
        if r[1] < -1e-9:
            msg = "chunk cerrado con volumen firmado negativo (%.4f m3)" % r[1]
    elif r[0] == "plano":
        n, c = r[1], r[2]
        if key == "sombra":
            exp = Vector((1.0 if c.x > 0 else -1.0, 0.0, 0.0))
        else:
            exp = Vector(ESPERADO[key]) if key in ESPERADO else None
        if exp is not None and n.dot(exp) < 0.9:
            msg = "panel plano con normal %s, esperada %s" % (
                tuple(round(x, 2) for x in n), tuple(exp))
    elif r[0] == "abierto":
        if r[1] < 0.0:
            msg = "chunk abierto con caras hacia dentro (flujo %.3f)" % r[1]
    if msg:
        orient_fallos[(donde, key, msg)] += 1
    return _add_original(self, verts, faces, mat, smooth)


ik._MB.add = _add_comprobado

sc = bpy.context.scene
coll = bpy.data.collections.new("ITAL_KIT")
sc.collection.children.link(coll)
root = ik.build(coll, seed=1)
print("Raiz:", root.name)

print("== Orientacion == chunks: %s" % dict(orient_stats))
for (donde, key, msg), n in sorted(orient_fallos.items()):
    print("  INVERTIDO x%d %s [%s]: %s" % (n, donde, key, msg))
    fallos.append("orientacion x%d %s [%s]: %s" % (n, donde, key, msg))
if not orient_fallos:
    print("  todos los chunks bien orientados")

# --- presupuestos -----------------------------------------------------------


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons) if ob.type == "MESH" else 0


def tris_arbol(ob):
    return tris(ob) + sum(tris_arbol(c) for c in ob.children)


def check(nombre, val, lim):
    ok = val <= lim
    print("  %-30s %6d tris (limite %d)%s" % (nombre, val, lim, "" if ok else "  <-- EXCEDE"))
    if not ok:
        fallos.append("%s: %d > %d" % (nombre, val, lim))


def base(n):
    return n.split(".")[0]


print("== Presupuestos ==")
vistos = set()
for ob in root.children:
    b = base(ob.name)
    vistos.add(b)
    if b == "ITAL_ermita":
        check(ob.name, tris_arbol(ob), 5000)
    elif b == "ITAL_capitella":
        check(ob.name, tris_arbol(ob), 800)
    elif b == "ITAL_fuente":
        check(ob.name, tris_arbol(ob), 1500)
    elif b == "ITAL_pergola":
        check(ob.name, tris_arbol(ob), 3000)
    elif b == "ITAL_hito":
        check(ob.name, tris_arbol(ob), 400)
    elif b == "ITAL_bancal":
        largo = float(ob["largo"])
        fijo = sum(tris(c) for c in ob.children if base(c.name) in ("ITAL_bancal_muro", "ITAL_bancal_tierra"))
        # 40/m de muro frontal + 50/m de fondo por los dos muros de vuelta (E2-09)
        check("%s muro+tierra (%.0f m)" % (ob.name, largo), fijo, int(40 * largo + 50 * float(ob["fondo"])))
        for c in ob.children:
            if base(c.name) == "ITAL_olivo":
                check(c.name, tris(c), 400)
    elif b == "ITAL_cipreses":
        for c in ob.children:
            check(c.name, tris(c), 250)
for esperado in ("ITAL_ermita", "ITAL_capitella", "ITAL_fuente", "ITAL_bancal",
                 "ITAL_cipreses", "ITAL_pergola", "ITAL_hito"):
    if esperado not in vistos:
        fallos.append("falta la raiz %s en el escaparate" % esperado)
for ob in bpy.data.objects:
    if ob.name.startswith("ITAL_cipres") and ob.type == "MESH" and tris(ob) > 250:
        fallos.append("%s: %d > 250" % (ob.name, tris(ob)))
for ma in bpy.data.materials:
    if not ma.name.startswith("MAT_ITAL_"):
        fallos.append("material sin prefijo: %s" % ma.name)
    if ma.node_tree and any(n.type == "TEX_IMAGE" for n in ma.node_tree.nodes):
        fallos.append("material con imagen: %s" % ma.name)
    if not ma.use_backface_culling:
        fallos.append("material sin backface culling (los previews no delatarian normales invertidas): %s" % ma.name)
total = tris_arbol(root)
print("Total escaparate: %d tris, %d materiales" % (total, len(bpy.data.materials)))

# --- suelo de preview: ladera escalonada + camino (no forma parte del kit) --


def mat_plano(nombre, color, rough=0.95):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    b.inputs["Roughness"].default_value = rough
    return m


def quad(nombre, pts, mat):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(pts, [], [(0, 1, 2, 3)])
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    sc.collection.objects.link(ob)
    return ob


hierba = mat_plano("MAT_TEST_hierba", (0.34, 0.47, 0.16))
tierra = mat_plano("MAT_TEST_tierra", (0.55, 0.40, 0.22))
S = 160.0
quad("TEST_suelo", [(-S, -S, -0.02), (S, -S, -0.02), (S, S, -0.02), (-S, S, -0.02)], hierba)
quad("TEST_terraza1", [(-S, -S, 1.59), (S, -S, 1.59), (S, -0.62, 1.59), (-S, -0.62, 1.59)], hierba)
quad("TEST_terraza2", [(-S, -S, 3.19), (S, -S, 3.19), (S, -9.25, 3.19), (-S, -9.25, 3.19)], hierba)
quad("TEST_camino", [(-60, 9.0, 0.0), (60, 9.0, 0.0), (60, 14.0, 0.0), (-60, 14.0, 0.0)], tierra)

# --- E2-09: bancal de la CIMA en ladera, como lo pone integrar_escena.zona_caminos
# (largo 14, fondo 3.5, pie 0.3 bajo la cara, corona 0.1 sobre el fondo). Ladera
# medida en ITAL_bancal.001/.003/.005: terreno 0.65-0.8 m sobre el pie a y=-0.6 y +0.56/m
# hacia el fondo. En los extremos (x = +-L/2) nada de relleno a la vista sobre el terreno.
from mathutils.bvhtree import BVHTree
OX, OY = 400.0, 0.0
LB, FB, PEND = 14.0, 3.5, 0.56


def z_ladera(lx, ly):
    return 0.46 + PEND * (-ly) + 0.02 * lx


AB = max(z_ladera(lx, -FB) for lx in (-7.0, 7.0)) + 0.1
ladera = quad("TEST_ladera", [(OX + lx, OY + ly, z_ladera(lx, ly)) for (lx, ly) in
                              ((-16.0, -12.0), (16.0, -12.0), (16.0, 10.0), (-16.0, 10.0))], hierba)
bl = ik.build_bancal(coll, largo=LB, alto=AB, seed=4, fondo=FB)
bl.location = (OX, OY, 0.0)
bpy.context.view_layer.update()
vs_b, fs_b, fm_b = [], [], []
for c in bl.children:
    if c.type != "MESH" or base(c.name) not in ("ITAL_bancal_muro", "ITAL_bancal_tierra"):
        continue
    b0 = len(vs_b)
    vs_b.extend(c.matrix_world @ v.co for v in c.data.vertices)
    for p in c.data.polygons:
        fs_b.append([b0 + i for i in p.vertices])
        fm_b.append(c.material_slots[p.material_index].material.name)
bvh_b = BVHTree.FromPolygons(vs_b, fs_b)
# relleno = tierra y hierba de la corona (las matas que asoman sobre la albardilla son vegetacion, no cuna)
RELLENO = ("MAT_ITAL_tierra", "MAT_ITAL_hierba_seca")
print("== E2-09 extremos del bancal en ladera (L %.0f, A %.2f, F %.1f) ==" % (LB, AB, FB))
peor_ext = 0.0
for sx in (-1.0, 1.0):
    fila_antes, fila_ahora = [], []
    for j in range(36):
        ly = -FB + 0.05 + j * (FB - 0.1) / 35.0
        zt = z_ladera(sx * LB / 2.0, ly)
        vista = 0.0
        z = zt + 0.02
        while z < AB + 0.25:
            h = bvh_b.ray_cast(Vector((OX + sx * (LB / 2.0 + 3.0), OY + ly, z)), Vector((-sx, 0.0, 0.0)), 6.0)
            if h[0] is not None and fm_b[h[2]] in RELLENO:
                vista += 0.02
            z += 0.02
        fila_ahora.append(vista)
        fila_antes.append(max(0.0, AB - zt))
        peor_ext = max(peor_ext, vista)
    print("  extremo %+d: relleno a la vista antes (sin vuelta) max %.2f m (y=-0.6: %.2f, -F/2: %.2f, -F: %.2f);"
          " ahora max %.2f m" % (sx, max(fila_antes), AB - z_ladera(sx * 7, -0.6), AB - z_ladera(sx * 7, -FB / 2),
                                 AB - z_ladera(sx * 7, -FB), max(fila_ahora)))
if peor_ext > 0.3:
    fallos.append("E2-09: relleno del bancal a la vista en un extremo: %.2f m (> 0.3)" % peor_ext)

# --- luz: sol calido + cielo azul uniforme -----------------------------------
world = bpy.data.worlds.new("WORLD_ital")
sc.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.52, 0.72, 0.96, 1.0)
bg.inputs[1].default_value = 1.0
sun_data = bpy.data.lights.new("SUN_ital", "SUN")
sun_data.energy = 2.8
sun_data.color = (1.0, 0.95, 0.84)
sun_data.angle = math.radians(2.5)
sun = bpy.data.objects.new("SUN_ital", sun_data)
sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(-50.0), 0.0, math.radians(28.0))

# --- render EEVEE 1280x800, Standard ---------------------------------------
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
print("Engine:", sc.render.engine)
sc.render.resolution_x, sc.render.resolution_y = 1280, 800
sc.render.resolution_percentage = 100
try:
    sc.eevee.taa_render_samples = 32
except AttributeError:
    pass
try:
    sc.eevee.use_shadows = True
except AttributeError:
    pass
sc.view_settings.view_transform = "Standard"

cam = bpy.data.objects.new("CAM_ital", bpy.data.cameras.new("CAM_ital"))
sc.collection.objects.link(cam)
sc.camera = cam


def mirar(pos, obj, lente=35.0):
    cam.location = Vector(pos)
    d = Vector(obj) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lente


os.makedirs(os.path.join(AQUI, "previews"), exist_ok=True)
os.makedirs(os.path.join(AQUI, "blend"), exist_ok=True)
TOMAS = (
    ("italiano_kit", (18.0, 48.0, 21.0), (0.0, -8.0, 3.0), 30.0),
    ("italiano_ermita", (15.0, 2.5, 8.0), (5.0, -15.0, 7.2), 30.0),
    ("italiano_ermita_trasera", (-14.0, -30.0, 9.0), (5.0, -19.5, 7.0), 32.0),
    ("italiano_bancal", (12.0, 12.0, 4.5), (-3.0, -2.0, 2.4), 32.0),
    ("italiano_fuente", (14.0, 14.5, 3.6), (9.0, 7.0, 1.3), 40.0),
    ("italiano_pergola", (23.0, 13.0, 3.2), (20.0, 4.0, 1.6), 32.0),
    ("italiano_detalles", (-7.0, 12.5, 2.2), (-11.0, 5.8, 1.1), 35.0),
    ("italiano_hito", (-6.8, 10.3, 1.1), (-8.0, 8.0, 0.5), 45.0),
    # E2-09: el bancal de ladera visto como en la revision (L/2+7 m de lado, 6 m delante, 2.5 m sobre el suelo)
    ("italiano_bancal_extremo", (OX + LB / 2 + 7.0, OY + 6.0, z_ladera(LB / 2 + 7.0, 6.0) + 2.5),
     (OX + LB / 2, OY, AB * 0.5), 28.0),
    ("italiano_bancal_extremo_izq", (OX - LB / 2 - 7.0, OY + 6.0, z_ladera(-LB / 2 - 7.0, 6.0) + 2.5),
     (OX - LB / 2, OY, AB * 0.5), 28.0),
    ("italiano_bancal_extremo_fondo", (OX + LB / 2 + 6.0, OY - FB - 6.0, z_ladera(LB / 2 + 6.0, -FB - 6.0) + 2.0),
     (OX + LB / 2 - 1.0, OY - FB / 2, AB * 0.8), 28.0),
)
for nombre, pos, obj, lente in TOMAS:
    mirar(pos, obj, lente)
    sc.render.filepath = os.path.join(AQUI, "previews", nombre + ".png")
    bpy.ops.render.render(write_still=True)
    print("render:", sc.render.filepath)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, "blend", "italiano_kit.blend"))
print("BLEND guardado")
if fallos:
    print("FALLOS:")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
print("OK test_italiano_kit")
