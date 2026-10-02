"""test_casas_kit_v2.py - auditoria headless de casas_kit_v2 (Blender 5.1).

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python este_archivo

Que hace:
  1. Carga casas_kit_v2 por ruta y construye LAS 22 VARIANTES que usa la escena
     (10 de pueblo seed=300+k, 6 de roca seed=70+k, 6 de la montana del
     viaducto seed=170+k) + una manzana (build()).
  2. Auditoria NUMERICA (sin mirar pixeles): tris por casa (<=5000), caras
     grandes orientadas hacia fuera, y -si el modulo rellena
     params['auditoria']- solapes entre ventanas / pilastras / bandas /
     cornisa / zocalo / toldos / balcones, alineacion de plantas entre las 4
     fachadas, paredes ciegas, oculos bajo el tejado y chimeneas sobre el tejado.
  3. Renderiza (EEVEE, 1280x720, sol + cielo, backface culling ACTIVADO para
     que una cara invertida se vea como un agujero):
        previews/casas_v2_frente.png    alzado de las 22 casas (3 filas x 8;
        previews/casas_v2_trasera.png   fila alta = pueblo P07..P00, media =
        previews/casas_v2_lado_izq.png  R05..R00+P09,P08, baja = V05..V00; la
        previews/casas_v2_lado_der.png  camara mira a -Y: el indice 0 a la DERECHA)
        previews/casas_v2_det_<g>_a.png  3/4 frente + lado derecho (4 casas)
        previews/casas_v2_det_<g>_b.png  3/4 trasera + lado izquierdo
        previews/casas_v2_cerca_<casa>_{bajo,alto,tras,lado,cubierta,porton}.png
                                         primeros planos a la altura del piloto,
                                         cubierta desde arriba y planta baja
        previews/casas_v2_lod1_det.png   la fachada lejana (lod=1) a media distancia
        previews/casas_kit_v2.png        preview canonico del contrato (= manzana)
        previews/casas_v2_manzana.png    build() por delante
        previews/casas_v2_manzana_tras.png  build() por detras
        previews/casas_v2_lejos_{400m,900m}.png       teleobjetivo, clip_start 0.1,
        previews/casas_v2_lejos_{400m,900m}_lod1.png  1 muestra: prueba de z-fighting
     'estanco': tras cada hoja / detalle se repite el render con una caja
     MAGENTA emisiva dentro de cada casa y se cuentan los pixeles magenta:
     con huecos reales en el muro, cualquier rendija o cara invertida la delata.
  4. Guarda blend/casas_kit_v2.blend.

Variables de entorno opcionales (solo para iterar mas rapido):
  CASAS_MOD=casas_kit_v2   modulo a cargar
  CASAS_PREFIX=casas_v2    prefijo de los PNG
  CASAS_RENDERS=hojas,detalles,zoom,cerca,manzana,lejos,estanco
                           (por defecto todo menos zoom)
"""

import importlib.util
import math
import os
import shutil
import sys
import traceback

import bpy
from mathutils import Vector

BASE = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets"
MOD = os.environ.get("CASAS_MOD", "casas_kit_v2")
PREFIX = os.environ.get("CASAS_PREFIX", "casas_v2")
RENDERS = os.environ.get("CASAS_RENDERS",
                         "hojas,detalles,cerca,manzana,lejos,estanco").split(",")
PREV = os.environ.get("CASAS_PREV", os.path.join(BASE, "previews"))
BLEND = os.path.join(os.environ.get("CASAS_BLEND_DIR", os.path.join(BASE, "blend")),
                     MOD + ".blend")
MAX_TRIS = 5000

VAR_PUEBLO = ((3, 9.0, 11), (4, 10.0, 12), (5, 9.5, 11), (4, 11.5, 12), (3, 12.0, 11),
              (5, 10.5, 12), (6, 10.0, 12), (4, 9.0, 10), (3, 10.5, 12), (5, 12.0, 12))
VAR_ROCA = ((3, 10, 10), (4, 11, 10), (5, 9, 9), (4, 13, 11), (3, 12, 10), (5, 11, 10))
# tercera familia que tambien usa integrar_escena.py (montana del viaducto, seed=170+k)
VAR_VIADUCTO = ((3, 9, 9), (4, 10, 9), (5, 9, 9), (4, 11, 10), (3, 10, 9), (6, 10, 10))
FAMILIAS = (("P", VAR_PUEBLO, 300), ("R", VAR_ROCA, 70), ("V", VAR_VIADUCTO, 170))
# casas de los primeros planos 'cerca': P03 (dos aguas, 4 pl.), P06 (plano, 6 pl.)
CERCA_IDX = (3, 6)

VISTAS = (("frente", 0.0), ("trasera", math.pi),
          ("lado_izq", -math.pi / 2.0), ("lado_der", math.pi / 2.0))

H_BAJA, H_PLANTA = 3.8, 3.0


# ---------------------------------------------------------------------------
# auditoria numerica
# ---------------------------------------------------------------------------

def _solapan(r1, r2, eps=1e-4):
    return (r1["a0"] < r2["a1"] - eps and r2["a0"] < r1["a1"] - eps and
            r1["z0"] < r2["z1"] - eps and r2["z0"] < r1["z1"] - eps)


PARES_OK = (
    {"banda", "pilastra"}, {"zocalo", "pilastra"}, {"cornisa", "pilastra"},
    {"balcon", "banda"}, {"toldo", "escaparate"}, {"pilastra"}, {"zocalo"},
)
ABERTURAS = ("ventana", "puerta", "escaparate")


def auditar_registro(nombre, reg, plantas, ancho, fondo, laterales=(True, True)):
    """Devuelve lista de defectos (strings) a partir del registro del modulo."""
    defectos = []
    h_muro = H_BAJA + (plantas - 1) * H_PLANTA
    largo = {"frente": ancho, "trasera": ancho, "izq": fondo, "der": fondo}
    por_pared = {}
    for r in reg:
        if "pared" in r:
            por_pared.setdefault(r["pared"], []).append(r)

    for pared, rects in por_pared.items():
        L = largo[pared]
        # 1) solapes prohibidos
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                r1, r2 = rects[i], rects[j]
                if not _solapan(r1, r2):
                    continue
                tipos = {r1["tipo"], r2["tipo"]}
                if tipos in PARES_OK:
                    continue
                if "balcon" in tipos and r1.get("grupo") is not None \
                        and r1.get("grupo") == r2.get("grupo"):
                    continue
                defectos.append("%s/%s: %s(%.2f..%.2f, z %.2f..%.2f) solapa %s(%.2f..%.2f, z %.2f..%.2f)" % (
                    nombre, pared, r1["tipo"], r1["a0"], r1["a1"], r1["z0"], r1["z1"],
                    r2["tipo"], r2["a0"], r2["a1"], r2["z0"], r2["z1"]))
        # 2) aberturas dentro del pano util del muro
        for r in rects:
            if r["tipo"] not in ABERTURAS:
                continue
            if r["a0"] < -L / 2 + 0.45 - 1e-4 or r["a1"] > L / 2 - 0.45 + 1e-4:
                defectos.append("%s/%s: %s se sale del pano (a %.2f..%.2f, L=%.1f)" % (
                    nombre, pared, r["tipo"], r["a0"], r["a1"], L))
            if r["z0"] < -1e-4 or r["z1"] > h_muro - 0.20 + 1e-4:
                defectos.append("%s/%s: %s fuera en altura (z %.2f..%.2f, muro %.2f)" % (
                    nombre, pared, r["tipo"], r["z0"], r["z1"], h_muro))

    # 3) paredes expuestas sin huecos / con panos ciegos grandes
    expuestas = ["frente", "trasera"]
    if laterales[0]:
        expuestas.append("izq")
    if laterales[1]:
        expuestas.append("der")
    for pared in expuestas:
        L = largo[pared]
        rects = [r for r in por_pared.get(pared, []) if r["tipo"] in ABERTURAS]
        for p in range(plantas):
            zc0 = 0.0 if p == 0 else H_BAJA + (p - 1) * H_PLANTA
            zc1 = H_BAJA if p == 0 else zc0 + H_PLANTA
            fila = sorted((r for r in rects if zc0 <= 0.5 * (r["z0"] + r["z1"]) < zc1),
                          key=lambda r: r["a0"])
            if not fila:
                defectos.append("%s/%s: planta %d SIN huecos (pared ciega)" % (nombre, pared, p))
                continue
            bordes = [-L / 2] + [v for r in fila for v in (r["a0"], r["a1"])] + [L / 2]
            huecos = [bordes[k + 1] - bordes[k] for k in range(0, len(bordes), 2)]
            if max(huecos) > 5.0:
                defectos.append("%s/%s: planta %d pano ciego de %.1f m" % (
                    nombre, pared, p, max(huecos)))

    # 4) alineacion vertical: las cotas de ventana de plantas altas coinciden
    def cotas(pared):
        return sorted({round(r["z1"], 3) for r in por_pared.get(pared, [])
                       if r["tipo"] == "ventana" and r.get("planta", 0) >= 1})
    ref = cotas("frente")
    for pared in expuestas[1:]:
        c = cotas(pared)
        if ref and c and c != ref:
            defectos.append("%s/%s: dinteles %s no alineados con el frente %s" % (
                nombre, pared, c, ref))

    # 4b) contraventanas cerradas: tope por muro y como mucho una por planta
    for pared, rects in por_pared.items():
        vent = [r for r in rects if r["tipo"] == "ventana"]
        cer = [r for r in vent if r.get("modo") == "cerrada"]
        if len(cer) > max(1, len(vent) // 6):
            defectos.append("%s/%s: %d de %d contraventanas cerradas (tope %d)" % (
                nombre, pared, len(cer), len(vent), max(1, len(vent) // 6)))
        pls = [r.get("planta") for r in cer]
        if len(pls) != len(set(pls)):
            defectos.append("%s/%s: dos contraventanas cerradas en la misma planta" % (
                nombre, pared))

    # 5) oculos y chimeneas
    for r in reg:
        if r.get("tipo") == "oculo":
            for (t, z) in r["puntos"]:
                z_lim = r["z_cima_inf"] - r["pendiente"] * abs(t)
                if z > z_lim - 0.05:
                    defectos.append("%s: oculo cortado por el tejado (z %.2f > %.2f)" % (
                        nombre, z, z_lim))
                if z < r["z_min"] + 0.05:
                    defectos.append("%s: oculo pisa la cornisa" % nombre)
        if r.get("tipo") == "chimenea":
            if not (r["z_base"] < r["z_tejado_min"]):
                defectos.append("%s: chimenea flotando (base %.2f, tejado %.2f)" % (
                    nombre, r["z_base"], r["z_tejado_min"]))
            if r["z_top"] - r["z_tejado_max"] < 0.7:
                defectos.append("%s: chimenea enterrada (asoma %.2f m)" % (
                    nombre, r["z_top"] - r["z_tejado_max"]))
            if abs(r["cx"]) + r["r"] > ancho / 2 or r["cy"] - r["r"] < -fondo or r["cy"] + r["r"] > 0:
                defectos.append("%s: chimenea fuera de la planta" % nombre)
    return defectos


def auditar_malla(obj, ancho, fondo, plantas):
    """Tris + orientacion de las caras grandes (muros y faldones)."""
    me = obj.data
    me.calc_loop_triangles()
    tris = len(me.loop_triangles)
    h_muro = H_BAJA + (plantas - 1) * H_PLANTA
    centro = Vector((0.0, -fondo / 2.0, h_muro / 2.0))
    malas = 0
    grandes = 0
    faldones = {}
    for poly in me.polygons:
        if poly.area < 6.0:
            continue
        c = poly.center
        nz = poly.normal.z
        if abs(nz) < 0.3 and c.z < h_muro:
            # muros del cuerpo: deben mirar hacia fuera en horizontal
            grandes += 1
            d = Vector((c.x - centro.x, c.y - centro.y, 0.0))
            if poly.normal.dot(d) < 0:
                malas += 1
        elif c.z > h_muro + 0.5 and 0.3 < abs(nz) < 0.98:
            # faldones inclinados: en cada placa, la cara ALTA mira arriba y la
            # BAJA mira abajo
            grandes += 1
            faldones.setdefault((round(c.x), round(c.y)), []).append((c.z, nz))
    for caras in faldones.values():
        caras.sort()
        if caras[-1][1] < 0:
            malas += 1
        if len(caras) > 1 and caras[0][1] > 0:
            malas += 1
    # estadistica de los elementos de fachada (marcos, vidrios, persianas...):
    # sus caras paralelas al muro deben mirar hacia FUERA casi siempre (las
    # unicas que miran al muro son traseras de barandillas y faldones de toldo)
    fuera = dentro = 0
    hx = ancho / 2.0
    for poly in me.polygons:
        c, n = poly.center, poly.normal
        if c.z > h_muro - 0.25 or abs(n.z) > 0.2:
            continue
        if c.y > 1e-4 and abs(n.y) > 0.9:
            s = n.y
        elif c.y < -fondo - 1e-4 and abs(n.y) > 0.9:
            s = -n.y
        elif c.x > hx + 1e-4 and abs(n.x) > 0.9:
            s = n.x
        elif c.x < -hx - 1e-4 and abs(n.x) > 0.9:
            s = -n.x
        else:
            continue
        if s > 0:
            fuera += 1
        else:
            dentro += 1
    if dentro > 0.25 * max(1, fuera + dentro):
        malas += dentro
    return tris, grandes, malas


def auditar_coplanares(obj, tol_error=0.008, tol_aviso=0.025):
    """Candidatas a z-fighting: pares de caras paralelas a un eje, con la MISMA
    orientacion, de DISTINTO material y cuyas cajas 2D se solapan.
      error: planos a < tol_error (coplanares de hecho) con solape > 0.01 m2
      aviso: planos a < tol_aviso con solape grande (> 0.25 m2)
    Devuelve (errores, avisos) como listas de strings."""
    me = obj.data
    nombres = [m.name.replace("MAT_CASAS_", "") for m in me.materials]
    grupos = {}
    for poly in me.polygons:
        n = poly.normal
        for ax in range(3):
            if abs(n[ax]) > 0.9999:
                vs = [me.vertices[i].co for i in poly.vertices]
                o = sum(v[ax] for v in vs) / len(vs)
                u, w = [k for k in range(3) if k != ax]
                rect = (min(v[u] for v in vs), max(v[u] for v in vs),
                        min(v[w] for v in vs), max(v[w] for v in vs))
                grupos.setdefault((ax, n[ax] > 0), []).append((o, rect, poly.material_index))
    errores, avisos = [], []
    for (ax, pos), lst in grupos.items():
        lst.sort(key=lambda t: t[0])
        for i in range(len(lst)):
            oi, ri, mi = lst[i]
            j = i + 1
            while j < len(lst) and lst[j][0] - oi < tol_aviso:
                oj, rj, mj = lst[j]
                j += 1
                if mi == mj:
                    continue
                du = min(ri[1], rj[1]) - max(ri[0], rj[0])
                dw = min(ri[3], rj[3]) - max(ri[2], rj[2])
                if du <= 0.005 or dw <= 0.005:
                    continue
                txt = "%s: %s/%s eje %s%s planos a %.3f m, solape %.2fx%.2f en (%.2f, %.2f)" % (
                    obj.name, nombres[mi], nombres[mj], "+" if pos else "-", "XYZ"[ax],
                    oj - oi, du, dw, max(ri[0], rj[0]), max(ri[2], rj[2]))
                if oj - oi < tol_error and du * dw > 0.01:
                    errores.append(txt)
                elif du * dw > 0.25:
                    avisos.append(txt)
    return errores, avisos


def auditar_fondos(obj, dist_max=0.30):
    """HUECOS REALES: ninguna cara rectangular de ESTUCO puede quedar DETRAS
    (misma orientacion, entre 0.5 y 30 cm) de una cara vertical de otro
    material con solape de mas de 2 cm en las dos direcciones. (Los solapes de
    1 cm con que el muro entra bajo marcos/bandas/pilastras no cuentan.)
    Es la causa del z-fighting a distancia de la version anterior."""
    me = obj.data
    nombres = [m.name.replace("MAT_CASAS_", "") for m in me.materials]
    grupos = {}
    for poly in me.polygons:
        n = poly.normal
        for ax in (0, 1):
            if abs(n[ax]) > 0.9999:
                vs = [me.vertices[i].co for i in poly.vertices]
                o = sum(v[ax] for v in vs) / len(vs)
                u = 1 - ax
                rect = (min(v[u] for v in vs), max(v[u] for v in vs),
                        min(v[2] for v in vs), max(v[2] for v in vs))
                area = (rect[1] - rect[0]) * (rect[3] - rect[2])
                es_rect = abs(poly.area - area) < 1e-3 * max(1.0, area)
                grupos.setdefault((ax, n[ax] > 0), []).append(
                    (o, rect, nombres[poly.material_index], es_rect))
    errores = []
    for (ax, pos), lst in grupos.items():
        estucos = [t for t in lst if t[2].startswith("fachada") and t[3]]
        otros = [t for t in lst if not t[2].startswith("fachada")]
        for (oe, re_, _, _) in estucos:
            for (oo, ro, nm, _) in otros:
                delante = (oo - oe) if pos else (oe - oo)
                if not (0.005 < delante < dist_max):
                    continue
                du = min(re_[1], ro[1]) - max(re_[0], ro[0])
                dw = min(re_[3], ro[3]) - max(re_[2], ro[2])
                if du > 0.02 and dw > 0.02:
                    errores.append("%s: estuco %.2f m DETRAS de %s (eje %s%s, solape %.2fx%.2f, z=%.2f)" % (
                        obj.name, delante, nm, "+" if pos else "-", "XY"[ax], du, dw,
                        max(re_[2], ro[2])))
    return errores


# ---------------------------------------------------------------------------
# escena de test
# ---------------------------------------------------------------------------

def mat_plano(nombre, col, rough=0.95):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*col, 1.0)
    b.inputs["Roughness"].default_value = rough
    return m


def suelo(nombre, x0, x1, y0, y1, z, mat, scene):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z),
                    (x0, y0, z - 0.4), (x1, y0, z - 0.4), (x1, y1, z - 0.4), (x0, y1, z - 0.4)],
                   [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
                        (2, 6, 7, 3), (3, 7, 4, 0)])
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    scene.collection.objects.link(ob)
    return ob


def apuntar(obj, desde, hacia):
    obj.location = desde
    obj.rotation_euler = (Vector(hacia) - Vector(desde)).to_track_quat("-Z", "Y").to_euler()


def main():
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    spec = importlib.util.spec_from_file_location(MOD, os.path.join(BASE, MOD + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    coll = bpy.data.collections.new("ASSET_casas_v2")
    scene.collection.children.link(coll)

    # ---------------- construir las 16 variantes de la escena ----------------
    casas = []          # (obj, plantas, ancho, fondo, etiqueta)
    defectos = []
    avisos_cop = []     # planos casi coplanares de distinto material (informativo)
    print("=== VARIANTES (tris / caras grandes / invertidas) ===")
    for grupo, variantes, seed0 in FAMILIAS:
        for k, (pl, an, fo) in enumerate(variantes):
            reg = []
            etiqueta = "%s%02d" % (grupo, k)
            ob = mod.build_casa(coll, plantas=pl, ancho=an, fondo=fo, seed=seed0 + k,
                                name="CASA_%s" % etiqueta, auditoria=reg)
            assert ob.type == "MESH", "build_casa debe devolver una malla"
            tris, grandes, malas = auditar_malla(ob, an, fo, pl)
            bb = [Vector(c) for c in ob.bound_box]
            print("  %s pl=%d an=%.1f fo=%.1f  tris=%5d %s  grandes=%d invertidas=%d  "
                  "bbox x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]  registro=%d" % (
                      etiqueta, pl, an, fo, tris, "OK" if tris <= MAX_TRIS else "EXCEDIDO",
                      grandes, malas,
                      min(v.x for v in bb), max(v.x for v in bb),
                      min(v.y for v in bb), max(v.y for v in bb),
                      min(v.z for v in bb), max(v.z for v in bb), len(reg)))
            if tris > MAX_TRIS:
                defectos.append("%s: %d tris > %d" % (etiqueta, tris, MAX_TRIS))
            if malas:
                defectos.append("%s: %d caras grandes con la normal invertida" % (etiqueta, malas))
            if reg:
                defectos += auditar_registro(etiqueta, reg, pl, an, fo)
            err_c, av_c = auditar_coplanares(ob)
            defectos += ["coplanar " + e for e in err_c]
            avisos_cop.extend(av_c)
            err_f = auditar_fondos(ob)
            defectos += ["fondo " + e for e in err_f[:6]]
            info = [r for r in reg if r.get("tipo") == "info"]
            if info and info[0]["nivel"] != 0:
                print("     (presupuesto: nivel de degradacion %d)" % info[0]["nivel"])
            casas.append((ob, pl, an, fo, etiqueta))

    # ---------------- fachada lejana (lod=1) de las mismas variantes ----------------
    print("=== LOD 1 (fachada lejana, sin relieves) ===")
    coll_l = bpy.data.collections.new("ASSET_casas_v2_lod1")
    tris_lod = []
    for grupo, variantes, seed0 in FAMILIAS:
        for k, (pl, an, fo) in enumerate(variantes):
            reg = []
            o = mod.build_casa(coll_l, plantas=pl, ancho=an, fondo=fo, seed=seed0 + k,
                               name="CASALOD_%s%02d" % (grupo, k), lod=1, auditoria=reg)
            t, g, m = auditar_malla(o, an, fo, pl)
            tris_lod.append(t)
            if m:
                defectos.append("lod1 %s%02d: %d caras invertidas" % (grupo, k, m))
            defectos += auditar_registro("L%s%02d" % (grupo, k), reg, pl, an, fo)
            err_c, av_c = auditar_coplanares(o)
            defectos += ["coplanar lod1 " + e for e in err_c]
            defectos += ["fondo lod1 " + e for e in auditar_fondos(o)[:6]]
    print("  tris lod1: min=%d max=%d media=%d" % (
        min(tris_lod), max(tris_lod), sum(tris_lod) // len(tris_lod)))

    # ---------------- manzana (build) ----------------
    coll_m = bpy.data.collections.new("ASSET_casas_v2_manzana")
    scene.collection.children.link(coll_m)
    root = mod.build(coll_m, seed=7)
    assert root is not None and root.type == "EMPTY"
    hijos = [o for o in coll_m.objects if o.type == "MESH"]
    assert len(hijos) == 6, "build() debe dar 6 casas"
    print("=== MANZANA build(seed=7) ===")
    for o in hijos:
        o.data.calc_loop_triangles()
        t = len(o.data.loop_triangles)
        print("  %-10s tris=%5d %s" % (o.name, t, "OK" if t <= MAX_TRIS else "EXCEDIDO"))
        if t > MAX_TRIS:
            defectos.append("manzana %s: %d tris" % (o.name, t))
        err_c, av_c = auditar_coplanares(o)
        defectos += ["coplanar manzana " + e for e in err_c]
        avisos_cop.extend(av_c)
    # variantes extremas de la API (no deben romper ni solapar)
    print("=== EXTREMOS API ===")
    coll_x = bpy.data.collections.new("ASSET_casas_v2_extremos")
    for (pl, an, fo, tj, lat) in ((1, 6.0, 7.0, "plano", (True, True)),
                                  (2, 8.0, 8.0, "dosaguas", (False, True)),
                                  (6, 13.0, 13.0, "dosaguas", (True, True)),
                                  (6, 12.0, 13.0, "plano", (True, False)),
                                  (3, 8.5, 10.0, "auto", (False, False))):
        reg = []
        o = mod.build_casa(coll_x, plantas=pl, ancho=an, fondo=fo, seed=pl * 31 + int(an),
                           tejado=tj, laterales=lat, auditoria=reg)
        t, g, m = auditar_malla(o, an, fo, pl)
        print("  pl=%d an=%.1f fo=%.1f %-8s lat=%s tris=%5d invertidas=%d" % (
            pl, an, fo, tj, lat, t, m))
        if t > MAX_TRIS:
            defectos.append("extremo %s: %d tris" % ((pl, an, fo), t))
        if m:
            defectos.append("extremo %s: %d caras invertidas" % ((pl, an, fo), m))
        if reg:
            defectos += auditar_registro("X%d_%.0f" % (pl, an), reg, pl, an, fo, lat)
        err_c, av_c = auditar_coplanares(o)
        defectos += ["coplanar extremo " + e for e in err_c]
        avisos_cop.extend(av_c)
        defectos += ["fondo extremo " + e for e in auditar_fondos(o)[:6]]

    # presupuesto garantizado: tamanos FUERA del rango de la escena, varias seeds
    print("=== PRESUPUESTO (barrido de seeds, debe quedar <= %d) ===" % MAX_TRIS)
    for (pl, an, fo, tj) in ((6, 13.0, 13.0, "dosaguas"), (6, 12.0, 12.0, "auto"),
                             (7, 12.0, 12.0, "auto"), (6, 15.0, 15.0, "dosaguas"),
                             (8, 16.0, 16.0, "plano")):
        peor, niveles = 0, set()
        for s in range(12):
            reg = []
            o = mod.build_casa(coll_x, plantas=pl, ancho=an, fondo=fo, seed=1000 + s,
                               tejado=tj, auditoria=reg)
            o.data.calc_loop_triangles()
            peor = max(peor, len(o.data.loop_triangles))
            niveles.update(r["nivel"] for r in reg if r.get("tipo") == "info")
            me_tmp = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(me_tmp)
        print("  pl=%d %.0fx%.0f %-8s peor=%5d tris  niveles usados=%s" % (
            pl, an, fo, tj, peor, sorted(niveles)))
        if peor > MAX_TRIS:
            defectos.append("presupuesto %s: %d tris" % ((pl, an, fo), peor))

    print("=== AVISOS de planos casi coplanares (<2.5 cm, distinto material): %d ===" % len(avisos_cop))
    for a in avisos_cop[:20]:
        print("  AVISO", a)
    print("=== DEFECTOS NUMERICOS: %d ===" % len(defectos))
    for d in defectos[:80]:
        print("  DEFECTO", d)

    # ---------------- escena de render ----------------
    for m in bpy.data.materials:
        if m.name.startswith("MAT_CASAS_"):
            m.use_backface_culling = True       # una cara invertida = agujero visible

    mat_suelo = mat_plano("MAT_TEST_suelo", (0.50, 0.48, 0.44))
    pivotes = []
    for i, (ob, pl, an, fo, et) in enumerate(casas):
        piv = bpy.data.objects.new("TEST_piv_%s" % et, None)
        scene.collection.objects.link(piv)
        ob.parent = piv
        ob.location = (0.0, fo / 2.0, 0.0)      # centro del cuerpo en el pivote
        pivotes.append(piv)

    # caja MAGENTA emisiva dentro de cada casa (prueba de estanqueidad): solo se
    # ve si el muro tiene una rendija, falta una mocheta o hay una cara invertida
    mat_mg = bpy.data.materials.new("MAT_TEST_magenta")
    mat_mg.use_nodes = True
    nt = mat_mg.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    n_out = nt.nodes.new("ShaderNodeOutputMaterial")
    n_em = nt.nodes.new("ShaderNodeEmission")
    n_em.inputs["Color"].default_value = (1.0, 0.0, 1.0, 1.0)
    n_em.inputs["Strength"].default_value = 200.0
    nt.links.new(n_em.outputs["Emission"], n_out.inputs["Surface"])
    testigos = []
    for (ob, pl, an, fo, et), piv in zip(casas, pivotes):
        h_m = H_BAJA + (pl - 1) * H_PLANTA
        t = suelo("TEST_testigo_%s" % et, -an / 2 + 0.15, an / 2 - 0.15,
                  -fo / 2 + 0.15, fo / 2 - 0.15, h_m - 0.25, mat_mg, scene)
        # suelo() hace una losa de 0.4 m: se estira hasta casi el suelo
        for v in t.data.vertices:
            if v.co.z < h_m - 0.3:
                v.co.z = 0.03
        t.parent = piv
        t.hide_render = True
        try:
            t.visible_shadow = False
        except AttributeError:
            pass
        testigos.append(t)

    # manzana aparte, lejos (y oculta salvo en sus propios renders)
    root.location = (0.0, -400.0, 0.0)
    suelo_m = suelo("TEST_suelo_manzana", -60, 60, -460, -340, -0.01, mat_suelo, scene)

    def ver_manzana(flag):
        for o in hijos + [suelo_m]:
            o.hide_render = not flag
    ver_manzana(False)

    cam_data = bpy.data.cameras.new("TEST_cam")
    cam_data.clip_start = 0.5
    cam_data.clip_end = 1500.0
    cam = bpy.data.objects.new("TEST_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    sun_data = bpy.data.lights.new("TEST_sol", "SUN")
    sun_data.energy = 3.0
    sun_data.color = (1.0, 0.96, 0.88)
    sun_data.angle = math.radians(1.5)
    sun = bpy.data.objects.new("TEST_sol", sun_data)
    scene.collection.objects.link(sun)
    apuntar(sun, (0, 0, 0), (0.55, -1.0, -0.85))   # luz desde camara-izquierda-arriba

    world = bpy.data.worlds.new("TEST_cielo")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.45, 0.68, 0.95, 1.0)
    bg.inputs[1].default_value = 0.9
    scene.world = world

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    try:
        scene.eevee.taa_render_samples = 24
    except Exception:
        pass
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(PREV, exist_ok=True)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)

    pngs = []

    fugas = []          # (nombre, pixeles magenta)
    calibrado = []

    def contar_magenta():
        import numpy as np
        muestras = scene.eevee.taa_render_samples
        # 16 muestras con jitter sub-pixel y testigo de emision 200: basta UNA
        # muestra colada por una rendija para saturar R y B del pixel
        scene.eevee.taa_render_samples = 16
        tmp = os.path.join(PREV, "_estanco_tmp.png")
        scene.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        scene.eevee.taa_render_samples = muestras
        img = bpy.data.images.load(tmp)
        px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(-1, 4)
        mask = (px[:, 0] > 0.97) & (px[:, 2] > 0.97) & (px[:, 1] < 0.93)
        n_mg = int(mask.sum())
        if 0 < n_mg < 50:
            ancho_img = img.size[0]
            for idx in np.nonzero(mask)[0][:8]:
                print("    fuga en pixel x=%d y=%d (desde abajo)" % (idx % ancho_img, idx // ancho_img))
        bpy.data.images.remove(img)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return n_mg

    def render(nombre, estanco=False, ruta=None):
        ruta = ruta or os.path.join(PREV, "%s_%s.png" % (PREFIX, nombre))
        scene.render.filepath = ruta
        bpy.ops.render.render(write_still=True)
        pngs.append(ruta)
        print("PNG:", ruta, os.path.exists(ruta))
        if estanco and "estanco" in RENDERS:
            # mismo encuadre con los testigos magenta visibles, pocas muestras
            for (c, t) in zip(casas, testigos):
                t.hide_render = c[0].hide_render
            if not calibrado:
                # CALIBRACION del detector: con las casas ocultas los testigos
                # tienen que verse (si no, "0 pixeles" no significaria nada)
                visibles = [c[0] for c in casas if not c[0].hide_render]
                for o in visibles:
                    o.hide_render = True
                n_cal = contar_magenta()
                for o in visibles:
                    o.hide_render = False
                print("  ESTANCO calibracion (casas ocultas): %d pixeles magenta" % n_cal)
                if n_cal < 500:
                    raise RuntimeError("el detector de magenta no ve los testigos")
                calibrado.append(n_cal)
            n_mg = contar_magenta()
            for t in testigos:
                t.hide_render = True
            fugas.append((nombre, n_mg))
            print("  ESTANCO %-16s pixeles magenta = %d" % (nombre, n_mg))

    def colocar(indices, paso_x, filas, dz_fila, rot, dy_fila=0.0):
        """Coloca las casas `indices` en rejilla (filas apiladas EN ALTURA; con
        dy_fila las filas altas se alejan en -Y para no sombrear a las bajas:
        la camara ortografica mira a -Y, asi que el alzado no cambia)."""
        por_fila = int(math.ceil(len(indices) / float(filas)))
        for i, piv in enumerate(pivotes):
            visible = i in indices
            casas[i][0].hide_render = not visible
            if not visible:
                piv.location = (0, 300, 0)
                continue
            k = indices.index(i)
            f, c = divmod(k, por_fila)
            piv.location = ((c - (por_fila - 1) / 2.0) * paso_x,
                            -(filas - 1 - f) * dy_fila, (filas - 1 - f) * dz_fila)
            piv.rotation_euler = (0, 0, rot)

    repisas = []

    def limpiar_repisas():
        for r in repisas:
            bpy.data.objects.remove(r, do_unlink=True)
        repisas.clear()

    # --- HOJAS DE CONTACTO: alzado ortografico, 2 filas x 8 ---
    N = len(casas)
    N_G = int(math.ceil(N / 4.0))
    if "hojas" in RENDERS:
        PASO, DZ, FILAS, DY = 16.0, 24.5, 3, 45.0
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 8 * PASO + 8.0
        for f in range(FILAS):
            rep = suelo("TEST_repisa_%d" % f, -4.2 * PASO, 4.2 * PASO, -9 - f * DY, 9 - f * DY,
                        f * DZ - 0.01, mat_suelo, scene)
            try:
                rep.visible_shadow = False      # que no oscurezca los tejados de la fila de abajo
            except AttributeError:
                pass
            repisas.append(rep)
        for nombre, rot in VISTAS:
            colocar(list(range(N)), PASO, FILAS, DZ, rot, DY)
            apuntar(cam, (0.0, 250.0, DZ + 10.0), (0.0, 0.0, DZ + 10.0))
            render(nombre, estanco=True)
        limpiar_repisas()

    # --- ZOOM: alzado de 4 casas por imagen (solo para auditar) ---
    if "zoom" in RENDERS:
        PASO = 16.0
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 4 * PASO + 1.0
        repisas.append(suelo("TEST_repisa_z", -2.2 * PASO, 2.2 * PASO, -9, 9, -0.01,
                             mat_suelo, scene))
        for g in range(N_G):
            for nombre, rot in VISTAS:
                colocar(list(range(4 * g, min(N, 4 * g + 4))), PASO, 1, 0.0, rot)
                apuntar(cam, (0.0, 250.0, 13.0), (0.0, 0.0, 13.0))
                render("zoom_%d_%s" % (g, nombre))
        limpiar_repisas()

    # --- DETALLES 3/4 en perspectiva: 4 casas por imagen ---
    if "detalles" in RENDERS:
        PASO = 23.0
        cam_data.type = "PERSP"
        cam_data.lens = 50.0
        repisas.append(suelo("TEST_suelo_det", -80, 80, -40, 40, -0.01, mat_suelo, scene))
        for g in range(N_G):
            for sufijo, rot in (("a", 0.0), ("b", math.pi)):
                colocar(list(range(4 * g, min(N, 4 * g + 4))), PASO, 1, 0.0, rot)
                objetivo = Vector((2.0, 0.0, 9.0))
                d = Vector((0.85, 1.0, 0.40)).normalized()
                apuntar(cam, objetivo + d * 132.0, objetivo)
                render("det_%d_%s" % (g, sufijo), estanco=True)
        limpiar_repisas()

    # --- CERCA: primeros planos de ventanas (lo que ve el piloto en AC) ---
    if "cerca" in RENDERS:
        cam_data.type = "PERSP"
        repisas.append(suelo("TEST_suelo_cerca", -60, 60, -60, 60, -0.01, mat_suelo, scene))
        for idx in CERCA_IDX:
            ob, pl, an, fo, et = casas[idx]
            h_m = H_BAJA + (pl - 1) * H_PLANTA
            hx_, hy_ = an / 2.0, fo / 2.0
            tomas = (
                # nombre, rot, camara, objetivo, focal
                ("bajo", 0.0, (hx_ + 7.0, hy_ + 11.0, 2.2), (0.5, hy_ - 1.0, 4.4), 26.0),
                ("alto", 0.0, (hx_ + 10.0, hy_ + 13.0, h_m + 2.0), (0.0, 0.0, h_m - 2.5), 30.0),
                ("tras", math.pi, (hx_ + 8.0, hy_ + 12.0, 3.0), (0.5, hy_ - 1.0, 4.8), 26.0),
                ("lado", math.pi / 2.0, (2.0, hx_ + 13.0, 2.0), (0.0, hx_, h_m * 0.5), 24.0),
                # cubierta vista desde arriba (viaducto / camaras aereas)
                ("cubierta", 0.0, (hx_ + 9.0, hy_ + 12.0, h_m + 15.0), (0.0, 0.0, h_m), 32.0),
                # planta baja de cerca: porton rehundido, escaparates, toldos
                ("porton", 0.0, (hx_ + 2.5, hy_ + 8.5, 1.5), (hx_ - 3.2, hy_, 2.1), 26.0),
            )
            for nombre, rot, c_pos, c_obj, focal in tomas:
                colocar([idx], 0.0, 1, 0.0, rot)
                cam_data.lens = focal
                apuntar(cam, c_pos, c_obj)
                render("cerca_%s_%s" % (et, nombre), estanco=True)
        limpiar_repisas()

    # --- MANZANA (+ preview canonico del contrato) ---
    if "manzana" in RENDERS:
        for c in casas:
            c[0].hide_render = True
        ver_manzana(True)
        cam_data.type = "PERSP"
        cam_data.lens = 42.0
        objetivo = Vector((0.0, -406.0, 9.5))
        apuntar(cam, objetivo + Vector((0.55, 1.0, 0.36)).normalized() * 100.0, objetivo)
        render("manzana")
        shutil.copyfile(pngs[-1], os.path.join(PREV, MOD + ".png"))
        pngs.append(os.path.join(PREV, MOD + ".png"))
        print("PNG:", pngs[-1], os.path.exists(pngs[-1]))
        apuntar(sun, (0, 0, 0), (-0.55, 1.0, -0.85))
        apuntar(cam, objetivo + Vector((-0.55, -1.0, 0.36)).normalized() * 100.0, objetivo)
        render("manzana_tras")
        apuntar(sun, (0, 0, 0), (0.55, -1.0, -0.85))
        ver_manzana(False)

    # --- LEJOS: teleobjetivo a 400 y 900 m, clip_start 0.1 m, 1 muestra ---
    # (la prueba de z-fighting del revisor: con planos superpuestos sobre un
    # muro continuo aparecian triangulos del color del muro en vidrios,
    # contraventanas y porton)
    if "lejos" in RENDERS:
        for c in casas:
            c[0].hide_render = True
        coll_z = bpy.data.collections.new("ASSET_casas_v2_lejos")
        scene.collection.children.link(coll_z)
        Y0 = -1500.0
        grupos_z = {}
        for lod in (0, 1):
            x = 0.0
            objs = []
            for (pl, an, fo, sd) in ((5, 12.0, 12, 309), (6, 10.0, 12, 306), (4, 11.5, 12, 303)):
                o = mod.build_casa(coll_z, plantas=pl, ancho=an, fondo=fo, seed=sd,
                                   name="CASAZ_%d_%d" % (lod, sd), lod=lod)
                o.location = (x + an / 2.0, Y0, 0.0)
                o.hide_render = True
                x += an
                objs.append(o)
            grupos_z[lod] = (objs, x)
        for m in bpy.data.materials:
            if m.name.startswith("MAT_CASAS_"):
                m.use_backface_culling = True
        muestras = scene.eevee.taa_render_samples
        scene.eevee.taa_render_samples = 1
        cam_data.type = "PERSP"
        cam_data.clip_start = 0.1
        cam_data.clip_end = 5000.0
        for lod in (0, 1):
            objs, x = grupos_z[lod]
            for o in objs:
                o.hide_render = False
            for dist, lens in ((400.0, 300.0), (900.0, 650.0)):
                cam_data.lens = lens
                apuntar(cam, (x / 2 + dist * 0.5, Y0 + dist, 30.0), (x / 2, Y0, 10.0))
                render("lejos_%dm%s" % (int(dist), "_lod1" if lod else ""))
            for o in objs:
                o.hide_render = True
        scene.eevee.taa_render_samples = muestras
        cam_data.clip_start = 0.5
        cam_data.clip_end = 1500.0
        # la fachada lejana (lod=1) vista a media distancia, para juzgar el cambio
        objs, x = grupos_z[1]
        for o in objs:
            o.hide_render = False
        suelo_z = suelo("TEST_suelo_lod", -40, 80, Y0 - 60, Y0 + 60, -0.01, mat_suelo, scene)
        cam_data.lens = 50.0
        objetivo = Vector((x / 2.0, Y0 - 4.0, 9.0))
        apuntar(cam, objetivo + Vector((0.85, 1.0, 0.40)).normalized() * 95.0, objetivo)
        render("lod1_det")
        for o in objs:
            o.hide_render = True
        suelo_z.hide_render = True

    # dejar el blend ordenado: variantes en fila
    ver_manzana(True)
    colocar(list(range(N)), 18.0, 3, 0.0, 0.0)
    for i, piv in enumerate(pivotes):
        f, c = divmod(i, 8)
        piv.location = ((c - 3.5) * 18.0, -f * 40.0, 0.0)
        casas[i][0].hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("BLEND:", BLEND, os.path.exists(BLEND))

    faltan = [p for p in pngs if not os.path.exists(p)]
    if faltan:
        raise RuntimeError("faltan PNG: %s" % faltan)
    total_fugas = sum(n for (_, n) in fugas)
    print("=== ESTANQUEIDAD: %d renders con testigo magenta, %d pixeles magenta ===" % (
        len(fugas), total_fugas))
    for (nombre, n_mg) in fugas:
        if n_mg > 0:
            defectos.append("estanqueidad %s: %d pixeles magenta (rendija o cara invertida)" % (
                nombre, n_mg))
            print("  DEFECTO estanqueidad", nombre, n_mg)
    if defectos:
        print("TEST_CON_DEFECTOS (%d)" % len(defectos))
    else:
        print("TEST_OK casas_kit_v2: %d variantes + manzana, 0 defectos numericos, %d PNG" % (
            N, len(pngs)))


try:
    main()
except Exception:
    traceback.print_exc()
    print("TEST_FALLO")
    sys.exit(1)
