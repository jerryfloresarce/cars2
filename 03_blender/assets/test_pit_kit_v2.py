"""test_pit_kit_v2.py — prueba de pit_kit_v2 (complejo de boxes, version 2).

Construye las piezas sueltas (muro, torre, pasarela, marcas, variantes del
edificio) y el escaparate build(), verifica API / nombres de raiz / hijos /
presupuestos de triangulos (edificio <= 90k con publico, muro <= 3k por
tramo, torre <= 4k, pasarela <= 6k) / caras coplanares solapadas / capas
pintadas separadas >= 3 cm / materiales procedurales (ruido + bump, vidrio con
Coat, metal en postes, vigas y persianas, techo azul sin especular de base) /
slots de material compactados (draw calls) / plazas / marcas del pit lane
(numeros hacia los garajes o hacia el piloto), y renderiza (EEVEE con trazado
de rayos y sombras, 1280x800, sol + cielo azul, backface culling como en AC):
  previews/pit_v2_frente.png    (desde el pit lane a 2 m: un box de cerca)
  previews/pit_v2_grada.png     (3/4 desde arriba: grada, techo, focos)
  previews/pit_v2_muro.png      (muro de boxes de cerca)
  previews/pit_v2_conjunto.png  (escaparate completo)
  previews/pit_v2_marcas.png    (cenital del escaparate: marcas del pit lane)
  previews/pit_v2_interior.png  (dentro de un box: utillaje)
  previews/pit_v2_torre.png     (torre de control + pasarela)
  previews/pit_v2_marcas_60.png (el '60' de la entrada desde el piloto)
  previews/pit_v2_ruedas.png    (pilas de ruedas y par tumbado de un box)
  previews/pit_v2_pancarta.png  (pancarta del peto de cerca)
  previews/pit_v2_torre_pie.png (puerta de la torre desde el pit lane)
Guarda blend/pit_kit_v2.blend.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_pit_kit_v2.py"
"""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
N_BOXES = 20
PRESUP = {'boxes': 90000, 'muro': 3000, 'torre': 4000, 'pasarela': 6000}


def cargar(nombre):
    ruta = os.path.join(BASE, nombre + '.py')
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def tris_de(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def tris_arbol(raiz):
    obs = [raiz] + list(raiz.children_recursive)
    return sum(tris_de(o) for o in obs if o.type == 'MESH')


def mi(ob, clave):
    """Indice del slot MAT_PIT_<clave> en la malla (los slots se compactan:
    nunca suponer el indice)."""
    i = ob.data.materials.find('MAT_PIT_' + clave)
    assert i >= 0, '%s no tiene el material %s' % (ob.name, clave)
    return i


def capas_z(obs, x0, x1, y0, y1, z_max=0.3):
    """Alturas (redondeadas al mm) de las caras horizontales hacia +Z cuya
    caja en XY solapa la region x0..x1, y0..y1 (el suelo epoxi es un unico
    quad que la cubre entera) y quedan por debajo de z_max, en coordenadas
    del mundo."""
    zs = set()
    for ob in obs:
        mw = ob.matrix_world
        vs = ob.data.vertices
        for p in ob.data.polygons:
            if p.normal.z < 0.9:
                continue
            c = mw @ p.center
            if c.z > z_max:
                continue
            pts = [mw @ vs[i].co for i in p.vertices]
            if (max(q.x for q in pts) >= x0 and min(q.x for q in pts) <= x1
                    and max(q.y for q in pts) >= y0 and min(q.y for q in pts) <= y1):
                zs.add(round(c.z, 3))
    return sorted(zs)


def pares_coplanares(me, area_min=0.02):
    """Pares de caras en el mismo plano cuyas proyecciones se solapan
    (candidatas a z-fighting)."""
    planos = {}
    for p in me.polygons:
        if p.area < area_min:
            continue
        n = p.normal
        d = n.dot(p.center)
        s = 1.0
        for comp in (n.x, n.y, n.z):
            if abs(comp) > 1e-4:
                s = 1.0 if comp > 0 else -1.0
                break
        clave = (round(n.x * s, 3), round(n.y * s, 3), round(n.z * s, 3),
                 round(d * s, 3))
        planos.setdefault(clave, []).append(p.index)

    def solapan_2d(pa, pb, tol=0.004):
        for poli in (pa, pb):
            n = len(poli)
            for k in range(n):
                ex = poli[(k + 1) % n][0] - poli[k][0]
                ey = poli[(k + 1) % n][1] - poli[k][1]
                ln = math.hypot(ex, ey)
                if ln < 1e-9:
                    continue
                ax, ay = -ey / ln, ex / ln
                a_ = [p[0] * ax + p[1] * ay for p in pa]
                b_ = [p[0] * ax + p[1] * ay for p in pb]
                if min(max(a_), max(b_)) - max(min(a_), min(b_)) < tol:
                    return False
        return True

    pares = []
    for clave, idxs in planos.items():
        if len(idxs) < 2:
            continue
        dom = max(range(3), key=lambda k: abs(clave[k]))
        ejes = [k for k in range(3) if k != dom]
        polis = []
        for i in idxs:
            cs = [me.vertices[v].co for v in me.polygons[i].vertices]
            polis.append((i, [(c[ejes[0]], c[ejes[1]]) for c in cs]))
        for a in range(len(polis)):
            for b in range(a + 1, len(polis)):
                if solapan_2d(polis[a][1], polis[b][1]):
                    pares.append((polis[a][0], polis[b][0]))
    return pares


def informe_coplanares(ob, exigir=True):
    pares = pares_coplanares(ob.data)
    print('[test] %-26s tris %6d  caras coplanares solapadas = %d'
          % (ob.name, tris_de(ob), len(pares)))
    me = ob.data
    for i, j in pares[:24]:
        pi, pj = me.polygons[i], me.polygons[j]
        print('        ', i, tuple(round(c, 2) for c in pi.center), pi.material_index,
              '<->', j, tuple(round(c, 2) for c in pj.center), pj.material_index)
    if exigir:
        assert not pares, ob.name + ' tiene caras coplanares solapadas'
    return len(pares)


def bbox(raiz):
    xs, ys, zs = [], [], []
    for ob in [raiz] + list(raiz.children_recursive):
        if ob.type != 'MESH':
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            xs.append(w.x)
            ys.append(w.y)
            zs.append(w.z)
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def mirar(cam, pos, objetivo):
    cam.location = Vector(pos)
    d = Vector(objetivo) - Vector(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def bsdf_de(mat):
    for nd in mat.node_tree.nodes:
        if nd.type == 'BSDF_PRINCIPLED':
            return nd
    return None


def valor(bsdf, nombre):
    ent = bsdf.inputs.get(nombre)
    if ent is None:
        return None
    if ent.links:
        return 'enlazado'
    return ent.default_value


def comprobar_materiales():
    """Materiales procedurales: sin imagenes, relieve por nodos, vidrio con
    Coat, metal, emisivos."""
    tipos = {}
    for m in bpy.data.materials:
        if not m.name.startswith('MAT_PIT_'):
            continue
        assert m.node_tree is not None, m.name
        for nd in m.node_tree.nodes:
            assert nd.type != 'TEX_IMAGE', '%s usa una imagen' % m.name
        tipos[m.name] = sorted(set(nd.type for nd in m.node_tree.nodes))
    for clave in ('crema', 'blanco', 'ocre', 'hormigon', 'asfalto', 'suelo_box'):
        t = tipos['MAT_PIT_' + clave]
        assert 'TEX_NOISE' in t and 'BUMP' in t, (clave, t)
    b = bsdf_de(bpy.data.materials['MAT_PIT_cristal'])
    assert valor(b, 'Roughness') <= 0.06 and valor(b, 'Coat Weight') >= 0.5
    b = bsdf_de(bpy.data.materials['MAT_PIT_gris_acero'])
    assert valor(b, 'Metallic') >= 0.85 and valor(b, 'Roughness') <= 0.25
    b = bsdf_de(bpy.data.materials['MAT_PIT_cromo'])
    assert valor(b, 'Metallic') >= 0.95
    b = bsdf_de(bpy.data.materials['MAT_PIT_azul_techo'])
    assert valor(b, 'Coat Weight') >= 0.1, 'techo azul sin laca'
    # sin especular de base (lavaba el azul con el cielo en angulos rasantes)
    assert valor(b, 'Specular IOR Level') <= 0.3, 'techo azul con demasiado reflejo'
    assert valor(b, 'Base Color')[2] >= 0.5 and valor(b, 'Base Color')[1] <= 0.15, \
        'techo azul poco saturado'
    b = bsdf_de(bpy.data.materials['MAT_PIT_luz_blanca'])
    assert valor(b, 'Emission Strength') >= 3.0
    b = bsdf_de(bpy.data.materials['MAT_PIT_pub_rojo'])
    assert valor(b, 'Coat Weight') >= 0.5
    n_rel = sum(1 for t in tipos.values() if 'BUMP' in t)
    print('[test] materiales MAT_PIT_: %d (con relieve por nodos: %d), sin imagenes'
          % (len(tipos), n_rel))
    return len(tipos)


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    pk = cargar('pit_kit_v2')
    escena = bpy.context.scene

    # ------------------------------------------------ 1) piezas sueltas
    col_t = bpy.data.collections.new('TMP_piezas')
    escena.collection.children.link(col_t)

    plazas = pk.plazas_boxes(N_BOXES, 6.0)
    assert len(plazas) == N_BOXES
    assert abs(plazas[0][0] + 57.0) < 1e-6 and abs(plazas[-1][0] - 57.0) < 1e-6
    assert all(abs(p[1] - 3.5) < 1e-6 and abs(p[2] - math.pi) < 1e-6 for p in plazas)
    print('[test] plazas_boxes(20): primera %s ultima %s' % (
        tuple(round(v, 3) for v in plazas[0]), tuple(round(v, 3) for v in plazas[-1])))

    muro = pk.build_muro_boxes(col_t, largo=12.0, seed=1)
    assert muro.type == 'MESH' and muro.name == 'PIT_muro_boxes'
    t_muro = tris_arbol(muro)
    informe_coplanares(muro)
    (mx0, mx1), (my0, my1), (mz0, mz1) = bbox(muro)
    print('[test] muro: tris %d (malla %d)  bbox x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]'
          % (t_muro, tris_de(muro), mx0, mx1, my0, my1, mz0, mz1))
    assert t_muro <= PRESUP['muro'], t_muro
    assert abs(mx0 + 6.0) < 1e-3 and abs(mx1 - 6.0) < 1e-3 and abs(mz0) < 1e-3
    assert my0 >= -2.06 and my1 <= 0.30
    hijos_m = {o.name: o for o in muro.children}
    assert 'PIT_muro_boxes_equipo' in hijos_m, 'faltan los coches-mecanico'
    n_mec = sum(1 for p in hijos_m['PIT_muro_boxes_equipo'].data.polygons
                if len(p.vertices) == 8)
    assert 2 <= n_mec <= 4, n_mec
    me_m = muro.data
    m_bl, m_cr, m_pa = mi(muro, 'blanco'), mi(muro, 'cromo'), mi(muro, 'pantalla_luz')
    pb = [p for p in me_m.polygons if p.normal.y < -0.9 and p.center.z > 1.95
          and abs(p.center.y - 0.22) < 0.01 and p.material_index == m_bl]
    assert pb, 'pit board sin cara hacia el pit lane'
    # cromo en la valla, sombrilla (cono: triangulos altos) y monitores emisivos
    assert any(p.material_index == m_cr and p.center.y > 0.15 for p in me_m.polygons)
    assert any(p.material_index == m_pa for p in me_m.polygons)
    assert any(len(p.vertices) == 3 and p.center.z > 3.0 for p in me_m.polygons), 'sin sombrilla'
    # slots compactados: solo los materiales usados (2 equipos por tramo, no 8)
    n_slots_m = len(me_m.materials)
    print('[test] muro: %d slots de material (compactados)' % n_slots_m)
    assert n_slots_m <= 15, n_slots_m
    assert all(any(p.material_index == k for p in me_m.polygons) for k in range(n_slots_m)), \
        'slot de material sin caras'

    def caras_en_x(ob, x, tol=1e-3):
        return sum(1 for p in ob.data.polygons
                   if abs(p.normal.x) > 0.9 and abs(p.center.x - x) < tol)
    assert caras_en_x(muro, -6.0) == 0 and caras_en_x(muro, 6.0) == 0
    muro_t = pk.build_muro_boxes(col_t, largo=12.0, seed=1, tapa_x0=True, tapa_x1=True,
                                 equipo=False)
    assert not muro_t.children
    n_t0, n_t1 = caras_en_x(muro_t, -6.0), caras_en_x(muro_t, 6.0)
    print('[test] muro con tapas: %d caras en x=-6, %d en x=+6, %d tris'
          % (n_t0, n_t1, tris_de(muro_t)))
    assert n_t0 >= 3 and n_t1 >= 3
    informe_coplanares(muro_t)

    torre = pk.build_torre_control(col_t, alto=16.0, seed=0)
    assert torre.type == 'EMPTY' and torre.name == 'PIT_torre'
    t_torre = tris_arbol(torre)
    for o in torre.children:
        informe_coplanares(o)
    (tx0, tx1), _, (tz0, tz1) = bbox(torre)
    print('[test] torre: tris %d  radio %.2f  alto %.2f' % (t_torre, tx1, tz1))
    assert t_torre <= PRESUP['torre'], t_torre
    assert abs(tz0) < 1e-3 and tx1 <= 3.95

    pasarela = pk.build_pasarela(col_t, luz=22.0, alto=7.0, seed=0)
    assert pasarela.type == 'EMPTY' and pasarela.name == 'PIT_pasarela'
    t_pas = tris_arbol(pasarela)
    for o in pasarela.children:
        if o.name == 'PIT_pasarela_cuerpo':
            informe_coplanares(o)
    (px0, px1), (py0, py1), (pz0, pz1) = bbox(pasarela)
    print('[test] pasarela: tris %d  bbox x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]'
          % (t_pas, px0, px1, py0, py1, pz0, pz1))
    assert t_pas <= PRESUP['pasarela'], t_pas
    assert abs(pz0 + 0.12) < 0.2
    assert abs(px1 - (11.0 + 7.4)) < 0.05, px1
    ob_pas = bpy.data.objects['PIT_pasarela_cuerpo']
    me_pas = ob_pas.data
    m_rampa = mi(ob_pas, 'piedra_clara')
    n_ramp_dn = sum(1 for p in me_pas.polygons if p.material_index == m_rampa and p.normal.z < -0.5)
    assert n_ramp_dn >= 14, n_ramp_dn
    assert bpy.data.objects.get('PIT_pasarela_banderas') is not None

    # marcas del pit lane: malla plana, todas las caras hacia +Z, numeros
    marcas = pk.build_marcas_pit_lane(col_t, largo=144.0, ancho_pit=7.5, n=N_BOXES,
                                      ancho_box=6.0, seed=0)
    assert marcas.type == 'MESH' and marcas.name == 'PIT_marcas'
    me_k = marcas.data
    assert all(p.normal.z > 0.9 for p in me_k.polygons), 'marcas con caras no horizontales'
    (kx0, kx1), (ky0, ky1), (kz0, kz1) = bbox(marcas)
    n_txt = sum(1 for p in me_k.polygons if len(p.vertices) == 3)   # texto: triangulos
    print('[test] marcas: tris %d  bbox x[%.2f, %.2f] y[%.2f, %.2f] z[%.3f, %.3f]  caras de texto %d'
          % (tris_de(marcas), kx0, kx1, ky0, ky1, kz0, kz1, n_txt))
    assert abs(kx0 + 72.0) < 1e-3 and abs(kx1 - 72.0) < 1e-3
    assert ky0 >= -3.75 - 1e-3 and ky1 <= 3.75 + 1e-3
    assert 0.025 <= kz0 and kz1 <= 0.04, (kz0, kz1)     # >= 3 cm sobre el asfalto
    assert n_txt >= 22 * 4, 'faltan los numeros / 60 pintados'
    # caja del box 1 con sentido=-1: centrada en x = +57 (girada respecto al
    # edificio); con sentido=+1 en x = -57
    k_am = mi(marcas, 'marca_amarilla')
    amar = [p.center for p in me_k.polygons if p.material_index == k_am and len(p.vertices) == 4]
    assert any(abs(c.x - 57.0) < 2.7 and c.y > 0.0 for c in amar)
    marcas2 = pk.build_marcas_pit_lane(col_t, largo=60.0, n=6, sentido=1)
    k_am2 = mi(marcas2, 'marca_amarilla')
    xs2 = [p.center.x for p in marcas2.data.polygons if p.material_index == k_am2
           and len(p.vertices) == 3]
    assert xs2 and min(xs2) < -12.0, xs2
    assert len(me_k.materials) == 2

    def extension_numero(ob, xc):
        """(ancho en x, alto en y) del numero pintado de la caja centrada en xc."""
        k = mi(ob, 'marca_amarilla')
        xs_, ys_ = [], []
        for p in ob.data.polygons:
            if p.material_index == k and len(p.vertices) == 3 and abs(p.center.x - xc) < 2.4:
                for v in p.vertices:
                    xs_.append(ob.data.vertices[v].co.x)
                    ys_.append(ob.data.vertices[v].co.y)
        return max(xs_) - min(xs_), max(ys_) - min(ys_)
    # numeros='piloto': el numero gira 90 grados (mas ancho en X que alto en Y)
    marcas3 = pk.build_marcas_pit_lane(col_t, largo=60.0, n=6, sentido=1, numeros='piloto')
    wg, hg = extension_numero(marcas2, -15.0)      # box 1 (sentido +1): x = -15
    wp, hp_ = extension_numero(marcas3, -15.0)
    print('[test] numero del box 1: garajes %.2f x %.2f, piloto %.2f x %.2f' % (wg, hg, wp, hp_))
    assert hg > wg and wp > hp_, (wg, hg, wp, hp_)

    # variantes de parametros de los boxes (robustez)
    for kw in ({'n': 4, 'ancho_box': 6.0}, {'n': 12, 'ancho_box': 5.0, 'filas': 4},
               {'n': 26, 'ancho_box': 6.0, 'seed': 3}):
        r = pk.build_boxes_tribuna(col_t, **kw)
        t = tris_arbol(r)
        (bx0, bx1), (by0, by1), (bz0, bz1) = bbox(r)
        print('[test] build_boxes_tribuna(%s): %d tris, x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]'
              % (kw, t, bx0, bx1, by0, by1, bz0, bz1))
        assert t <= PRESUP['boxes'] * max(1.0, kw['n'] / 20.0) + 2000
        for o in r.children:
            if o.name.split('.')[0] in ('PIT_boxes_edificio', 'PIT_boxes_grada',
                                        'PIT_boxes_techo', 'PIT_boxes_equipos'):
                assert informe_coplanares(o, exigir=False) == 0, \
                    'coplanares en %s con %s' % (o.name, kw)
    for ob in list(col_t.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(col_t)

    # ------------------------------------------------ 2) escaparate
    col = bpy.data.collections.new('PIT_ASSET')
    escena.collection.children.link(col)
    raiz = pk.build(col, seed=0)
    assert raiz is not None and raiz.type == 'EMPTY' and raiz.name == 'PIT_kit'
    bpy.context.view_layer.update()
    n_mats = comprobar_materiales()

    boxes = bpy.data.objects.get('PIT_boxes')
    assert boxes is not None and boxes.type == 'EMPTY'
    hijos = {o.name: o for o in boxes.children}
    for nm in ('PIT_boxes_edificio', 'PIT_boxes_grada', 'PIT_boxes_techo',
               'PIT_boxes_publico', 'PIT_boxes_numeros', 'PIT_boxes_rotulo',
               'PIT_boxes_utillaje', 'PIT_boxes_banderas', 'PIT_boxes_pancartas',
               'PIT_boxes_equipos'):
        assert nm in hijos and hijos[nm].type == 'MESH', 'falta ' + nm
    num = hijos['PIT_boxes_numeros']
    assert all(abs(v) < 1e-6 for v in num.location) and \
        all(abs(v) < 1e-6 for v in num.rotation_euler)
    xs_num = sorted(v.co.x for v in num.data.vertices)
    for i in range(N_BOXES):
        cx = -60.0 + (i + 0.5) * 6.0
        assert any(abs(x - cx) < 0.6 for x in xs_num), 'sin numero en el box %d' % (i + 1)
    assert all(v.co.y > 6.5 for v in num.data.vertices), 'numeros dentro de la fachada'
    assert all(p.normal.y > 0.9 for p in num.data.polygons), 'numeros no miran al pit lane'
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.name.startswith('PIT_'):
            for m in ob.data.materials:
                assert m.name.startswith('MAT_PIT_'), m.name
            assert not ob.data.has_custom_normals

    total = 0
    for nm in ('PIT_boxes_edificio', 'PIT_boxes_grada', 'PIT_boxes_techo',
               'PIT_boxes_equipos'):
        total += informe_coplanares(hijos[nm])
        assert not any(p.use_smooth for p in hijos[nm].data.polygons), nm + ' caras suaves'
        assert len(hijos[nm].data.vertices) == sum(len(p.vertices)
                                                   for p in hijos[nm].data.polygons)
    informe_coplanares(hijos['PIT_boxes_utillaje'], exigir=False)
    t_pub = tris_de(hijos['PIT_boxes_publico'])
    me_p = hijos['PIT_boxes_publico'].data
    n_coches = sum(1 for p in me_p.polygons if len(p.vertices) == 8)
    print('[test] publico: %d coches, %d tris (%.1f tris/coche)'
          % (n_coches, t_pub, t_pub / max(1, n_coches)))
    assert n_coches >= 300 and t_pub / n_coches <= 60.0
    # pancartas: textos de patrocinio de pie (peto y muro trasero); numeros
    # planos en el suelo de los garajes en la malla de equipos; banderas de
    # doble cara
    me_pc = hijos['PIT_boxes_pancartas'].data
    me_eq = hijos['PIT_boxes_equipos'].data
    n_pie = sum(1 for p in me_pc.polygons if abs(p.normal.y) > 0.9)
    n_atras = sum(1 for p in me_pc.polygons if p.normal.y < -0.9)
    n_plano = sum(1 for p in me_eq.polygons if p.normal.z > 0.9 and len(p.vertices) == 3
                  and 0.07 < p.center.z < 0.09)
    print('[test] pancartas: %d caras de pie (%d hacia el paddock); numeros del suelo: '
          '%d caras planas en PIT_boxes_equipos' % (n_pie, n_atras, n_plano))
    assert n_pie >= 200 and n_atras >= 60 and n_plano >= 60
    assert all(abs(p.normal.y) > 0.9 for p in me_pc.polygons), 'pancarta no vertical'
    assert len(me_pc.materials) <= 2, 'pancartas con mas de 2 materiales'
    assert len(me_eq.materials) == 8, 'equipos: %d materiales' % len(me_eq.materials)
    # capas pintadas del garaje 5 (suelo epoxi, banda / plaza, numero): todas
    # las alturas de caras horizontales bajo 0.3 m separadas >= 3 cm
    obs_g = [hijos[k] for k in ('PIT_boxes_edificio', 'PIT_boxes_equipos', 'PIT_boxes_utillaje')]
    zs_g = capas_z(obs_g, -35.9, -30.1, 0.6, 6.4)
    print('[test] capas horizontales en el garaje 5 (z < 0.3): %s' % zs_g)
    assert zs_g[0] >= 0.015 and len(zs_g) >= 3
    assert all(b - a >= 0.03 - 1e-6 for a, b in zip(zs_g, zs_g[1:])), zs_g
    # textos a >= 3 cm de su banda: pancarta del peto (banda y 6.54, texto
    # 6.57), muro trasero (banda -6.55, texto -6.58), placas (7.76 / 7.79)
    ys_pc = sorted(set(round(p.center.y, 3) for p in me_pc.polygons))
    assert min(ys_pc) <= -6.58 + 1e-6 and max(ys_pc) >= 6.57 - 1e-6, ys_pc
    assert all(v.co.y >= 7.79 - 1e-6 for v in hijos['PIT_boxes_numeros'].data.vertices)
    me_b = hijos['PIT_boxes_banderas'].data
    n_fl = sum(1 for p in me_b.polygons if abs(p.normal.y) > 0.5)
    print('[test] banderas: %d caras de tela (doble cara), %d tris'
          % (n_fl, tris_de(hijos['PIT_boxes_banderas'])))
    assert n_fl >= 20 * 24
    # marquesina volada: caras hacia -Z (sombra) de la losa entre y=6.5 y 7.7
    me_e = hijos['PIT_boxes_edificio'].data
    marq = [p for p in me_e.polygons if p.normal.z < -0.9 and abs(p.center.z - 4.42) < 0.01
            and 6.6 < p.center.y < 7.7]
    assert marq, 'sin marquesina'
    pil = [p for p in me_e.polygons if p.normal.y > 0.9 and abs(p.center.y - 6.7) < 0.01]
    assert len(pil) >= N_BOXES, 'pilastras sin relieve de 0.20'
    # persiana metalica: faldon (y = 5.93, z 3.4..4.05) y tambor en gris_acero
    e_ac = mi(hijos['PIT_boxes_edificio'], 'gris_acero')
    fald = [p for p in me_e.polygons if p.material_index == e_ac and p.normal.y > 0.9
            and abs(p.center.y - 5.93) < 0.005 and 3.4 < p.center.z < 4.05]
    print('[test] persianas: %d faldones metalicos hacia el pit lane' % len(fald))
    assert len(fald) >= N_BOXES
    n_slots = sum(len(o.data.materials) for o in hijos.values() if o.type == 'MESH')
    for o in hijos.values():
        if o.type == 'MESH':
            usados_o = set(p.material_index for p in o.data.polygons)
            assert usados_o == set(range(len(o.data.materials))), \
                '%s: slots sin caras' % o.name
    print('[test] slots de material (draw calls) del edificio de boxes: %d  (%s)'
          % (n_slots, '  '.join('%s %d' % (k.replace('PIT_boxes_', ''), len(o.data.materials))
                                for k, o in sorted(hijos.items()) if o.type == 'MESH')))
    assert n_slots <= 64, n_slots
    t_boxes = tris_arbol(boxes)
    partes = {nm: tris_de(o) for nm, o in hijos.items() if o.type == 'MESH'}
    print('[test] boxes: ' + '  '.join('%s %d' % (k.replace('PIT_boxes_', ''), v)
                                       for k, v in sorted(partes.items())))
    print('[test] boxes TOTAL %d tris (max %d)' % (t_boxes, PRESUP['boxes']))
    assert t_boxes <= PRESUP['boxes']
    (bx0, bx1), (by0, by1), (bz0, bz1) = bbox(boxes)
    print('[test] boxes bbox x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]'
          % (bx0, bx1, by0, by1, bz0, bz1))
    assert abs(bz0) < 1e-3 and abs(bx0 + 60.3) < 1e-3 and abs(bx1 - 60.3) < 1e-3
    assert by1 <= 7.85 and by0 >= -6.85
    t_total = tris_arbol(raiz)
    print('[test] escaparate completo: %d tris, %d materiales MAT_PIT_' % (t_total, n_mats))
    marcas_e = bpy.data.objects.get('PIT_marcas')
    assert marcas_e is not None

    # --- pit lane LIBRE: las torres (plinto r 2.7, balcon r 3.9) fuera de la
    # franja del pit lane marcado (y 8.1..15.6, x +-72) y sin tapar los '60'
    # (x +-66.5) ni las franjas de speed limit (x +-69.5); la pasarela solo
    # pasa por encima del pit lane y de la pista (>= 6.5 m libres)
    (ex0, ex1), (ey0, ey1), _ = bbox(marcas_e)
    y_pl0, y_pl1 = ey0, ey1
    print('[test] marcas en el escaparate: x[%.1f, %.1f] y[%.1f, %.1f]' % (ex0, ex1, ey0, ey1))
    torres = [o for o in bpy.data.objects if o.name.startswith('PIT_torre') and o.type == 'EMPTY']
    assert len(torres) == 2
    for t in torres:
        (tx0_, tx1_), (ty0_, ty1_), _ = bbox(t)
        print('[test] torre en (%.1f, %.1f): bbox x[%.1f, %.1f] y[%.1f, %.1f]'
              % (t.location.x, t.location.y, tx0_, tx1_, ty0_, ty1_))
        assert ty1_ < y_pl0 - 0.5 or ty0_ > y_pl1 + 0.5 or tx0_ > ex1 + 0.5 or tx1_ < ex0 - 0.5, \
            'torre dentro del pit lane'
        assert min(abs(tx0_), abs(tx1_)) > 72.0 + 0.5, 'torre sobre las marcas'
    pas = bpy.data.objects.get('PIT_pasarela')
    assert pas is not None
    bajo = 0
    for o in [pas] + list(pas.children_recursive):
        if o.type != 'MESH':
            continue
        for v in o.data.vertices:
            wv = o.matrix_world @ v.co
            if (y_pl0 - 0.3 <= wv.y <= y_pl1 + 0.3) or (19.0 <= wv.y <= 35.0):
                if wv.z < 6.5:
                    bajo += 1
    print('[test] pasarela: %d vertices por debajo de 6.5 m sobre el pit lane / la pista' % bajo)
    assert bajo == 0, bajo
    # los '60' y las franjas transversales existen en las marcas del
    # escaparate: caras blancas (mat 0) de texto (triangulos) cerca de x=+-66.5
    me_me = marcas_e.data
    mw = marcas_e.matrix_world
    xs60 = [(mw @ me_me.vertices[p.vertices[0]].co).x for p in me_me.polygons
            if p.material_index == 0 and len(p.vertices) == 3]
    assert xs60 and min(xs60) < -64.5 and max(xs60) > 64.5, 'faltan los 60'
    n_tri60 = len(xs60)
    print('[test] marcas: %d triangulos de los dos 60 (resolucion 4)' % n_tri60)
    assert n_tri60 >= 2 * 40, n_tri60      # con resolucion 1 salen ~20 por '60'

    # --- puerta de la torre: marco blanco, hojas azules, ventanucos de
    # cristal y tirador cromado en la cara +Y del fuste (z < 3.8)
    ob_tc = bpy.data.objects['PIT_torre_cuerpo']
    me_tc = ob_tc.data
    def caras_puerta(clave, z0, z1):
        k = mi(ob_tc, clave)
        return [p for p in me_tc.polygons if p.material_index == k and p.normal.y > 0.9
                and z0 <= p.center.z <= z1 and abs(p.center.x) < 1.5]
    n_marco = len(caras_puerta('blanco', 0.5, 3.4))
    n_hoja = len(caras_puerta('azul_techo', 0.5, 3.3))
    n_vent = len(caras_puerta('cristal', 1.8, 3.0))
    n_tir = len(caras_puerta('cromo', 1.4, 1.6))
    print('[test] puerta de la torre: %d caras de marco, %d de hoja, %d de cristal, %d de tirador'
          % (n_marco, n_hoja, n_vent, n_tir))
    assert n_marco >= 3 and n_hoja == 2 and n_vent == 2 and n_tir == 2

    # --- ruedas: perfil con hombro (caras de goma a radio 0.90 r) y hueco de
    # 2 cm entre ruedas apiladas en el utillaje; llantas cromadas tumbadas
    # (normal +Y) en cada box
    ob_u = hijos['PIT_boxes_utillaje']
    me_u = ob_u.data
    u_osc, u_cr, u_goma = mi(ob_u, 'gris_oscuro'), mi(ob_u, 'cromo'), mi(ob_u, 'goma')
    # llanta visible = disco oscuro (>= 8 lados) + 5 radios cromados (quads)
    # + buje cromado (5 lados); fondo = disco cromado
    n_disco_y = sum(1 for p in me_u.polygons if p.material_index == u_osc and p.normal.y > 0.9
                    and len(p.vertices) >= 8)
    n_radios_y = sum(1 for p in me_u.polygons if p.material_index == u_cr and p.normal.y > 0.9
                     and len(p.vertices) in (4, 5))
    n_disco_z = sum(1 for p in me_u.polygons if p.material_index == u_osc and p.normal.z > 0.9
                    and len(p.vertices) >= 8)
    n_fondo_z = sum(1 for p in me_u.polygons if p.material_index == u_cr and p.normal.z < -0.9
                    and len(p.vertices) >= 8)
    print('[test] llantas en los boxes: %d tapas de pila (con radios), %d fondos cromados, '
          '%d tumbadas hacia +Y (%d radios/bujes)' % (n_disco_z, n_fondo_z, n_disco_y, n_radios_y))
    assert n_disco_y >= N_BOXES and n_radios_y >= 6 * N_BOXES
    assert n_disco_z >= 2 * N_BOXES and n_fondo_z >= 3 * N_BOXES
    # perfil con hombro: caras de goma cuya normal tiene componente vertical
    # apreciable (bandas inclinadas de los hombros) en las pilas
    n_hombro = sum(1 for p in me_u.polygons if p.material_index == u_goma and len(p.vertices) == 4
                   and 0.15 < abs(p.normal.z) < 0.85)
    print('[test] caras de hombro de neumatico en los boxes: %d' % n_hombro)
    assert n_hombro >= 2 * 10 * 4 * N_BOXES

    # --- postes del techo: cada poste (gris_acero) acaba en la cara inferior
    # de una viga (tambien metalica, cara hacia -Z a z_vig) que lo cubre
    ob_t = hijos['PIT_boxes_techo']
    me_t = ob_t.data
    t_ac, t_luz = mi(ob_t, 'gris_acero'), mi(ob_t, 'luz_blanca')
    z_vig = pk._Z_TECHO - 0.35
    vigas = []
    for p in me_t.polygons:
        if p.material_index == t_ac and p.normal.z < -0.9 and abs(p.center.z - z_vig) < 1e-3:
            xs = [me_t.vertices[v].co.x for v in p.vertices]
            vigas.append((min(xs), max(xs)))
    postes = {}
    for p in me_t.polygons:
        if p.material_index == t_ac and abs(p.normal.z) < 0.1:
            zs = [me_t.vertices[v].co.z for v in p.vertices]
            if abs(max(zs) - z_vig) < 1e-3:
                postes[round(p.center.x, 1)] = p.center.x
    sueltos = [x for x in postes.values() if not any(a - 1e-3 <= x <= b + 1e-3 for a, b in vigas)]
    n_focos = sum(1 for p in me_t.polygons if p.material_index == t_luz)
    assert 'MAT_PIT_blanco' not in me_t.materials, 'vigas del techo sin metal'
    print('[test] techo: %d vigas, %d postes, %d postes sin viga encima, %d caras de foco' % (
        len(vigas), len(postes), len(sueltos), n_focos))
    assert len(postes) >= 10 and not sueltos, sueltos
    assert n_focos >= 2 * len(vigas)

    # --- linea de vision desde la pista a altura de piloto (y=30, z=1.4)
    z_peto = pk._Z_GRADA + pk._H_PETO
    y_peto = 6.5
    p_ojo = mi(hijos['PIT_boxes_publico'], 'pub_blanco')
    ojos = [p.center for p in me_p.polygons
            if len(p.vertices) == 6 and p.material_index == p_ojo]
    assert ojos
    vis, tot = 0, 0
    for c in ojos:
        if c.y > 6.2 - 1.76:
            continue
        z_lin = 1.4 + (z_peto - 1.4) * (30.0 - c.y) / (30.0 - y_peto)
        tot += 1
        if c.z > z_lin:
            vis += 1
    print('[test] visual desde la pista: %d de %d ojos (filas 2..) sobre el peto (%.1f%%)'
          % (vis, tot, 100.0 * vis / max(1, tot)))
    assert vis >= 0.95 * tot

    # ------------------------------------------------ 3) render
    sol_d = bpy.data.lights.new('SOL', type='SUN')
    sol_d.energy = 4.0
    sol_d.color = (1.0, 0.94, 0.84)
    for attr, val in (('angle', math.radians(1.2)), ('use_shadow', True),
                      ('shadow_maximum_resolution', 0.002)):
        try:
            setattr(sol_d, attr, val)
        except (AttributeError, TypeError):
            pass
    sol = bpy.data.objects.new('SOL', sol_d)
    escena.collection.objects.link(sol)
    sol.rotation_euler = Vector((0.45, -0.55, -0.72)).to_track_quat('-Z', 'Y').to_euler()

    mundo = bpy.data.worlds.new('CIELO')
    # en 5.x el mundo nuevo ya trae node_tree; `use_nodes` (deprecado, se va
    # en 6.0) solo se toca si falta el arbol
    nt_w = getattr(mundo, 'node_tree', None)
    if nt_w is None:
        try:
            mundo.use_nodes = True
        except AttributeError:
            pass
        nt_w = getattr(mundo, 'node_tree', None)
    if nt_w is not None:
        salida_w = None
        for nd in nt_w.nodes:
            if nd.type == 'OUTPUT_WORLD':
                salida_w = nd
                break
        if salida_w is None:
            salida_w = nt_w.nodes.new('ShaderNodeOutputWorld')
        amb = nt_w.nodes.new('ShaderNodeBackground')
        amb.inputs[0].default_value = (0.70, 0.80, 0.95, 1.0)
        amb.inputs[1].default_value = 0.55
        cielo = nt_w.nodes.new('ShaderNodeBackground')
        cielo.inputs[0].default_value = (0.38, 0.62, 0.96, 1.0)
        cielo.inputs[1].default_value = 1.0
        ruta = nt_w.nodes.new('ShaderNodeLightPath')
        mezcla = nt_w.nodes.new('ShaderNodeMixShader')
        nt_w.links.new(ruta.outputs['Is Camera Ray'], mezcla.inputs[0])
        nt_w.links.new(amb.outputs[0], mezcla.inputs[1])
        nt_w.links.new(cielo.outputs[0], mezcla.inputs[2])
        nt_w.links.new(mezcla.outputs[0], salida_w.inputs['Surface'])
    else:
        mundo.color = (0.62, 0.76, 0.94)
    escena.world = mundo

    for motor in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            escena.render.engine = motor
            break
        except TypeError:
            continue
    ee = escena.eevee
    for attr, val in (('use_raytracing', True), ('use_shadows', True),
                      ('taa_render_samples', 48), ('shadow_ray_count', 2),
                      ('shadow_step_count', 4)):
        try:
            setattr(ee, attr, val)
        except (AttributeError, TypeError):
            pass
    escena.render.resolution_x = 1280
    escena.render.resolution_y = 800
    escena.render.resolution_percentage = 100
    escena.render.image_settings.file_format = 'PNG'
    try:
        escena.view_settings.view_transform = 'Standard'
    except TypeError:
        pass

    cam_d = bpy.data.cameras.new('CAM_preview')
    cam = bpy.data.objects.new('CAM_preview', cam_d)
    escena.collection.objects.link(cam)
    escena.camera = cam
    cam_d.clip_end = 800

    dir_prev = os.path.join(BASE, 'previews')
    os.makedirs(dir_prev, exist_ok=True)
    tomas = (
        ('pit_v2_frente', 32, (13.0, 14.5, 2.0), (3.5, 6.5, 3.4)),
        ('pit_v2_grada', 32, (44.0, 52.0, 26.0), (-8.0, 0.0, 11.0)),
        ('pit_v2_muro', 35, (-9.0, 9.0, 3.6), (-1.0, 18.5, 1.9)),
        ('pit_v2_conjunto', 30, (150.0, 118.0, 66.0), (-4.0, 16.0, 4.0)),
        # cenital del pit lane completo (x +-75): los dos '60' y las franjas
        ('pit_v2_marcas', 24, (0.0, 12.0, 100.0), (0.0, 12.0, 0.0)),
        # el '60' de la entrada visto desde el asiento del piloto (y=13.95,
        # carril rapido, marcha hacia +X)
        ('pit_v2_marcas_60', 40, (-86.0, 13.95, 1.3), (-66.5, 13.95, 0.0)),
        ('pit_v2_interior', 26, (-34.5, 13.5, 1.7), (-32.5, 2.0, 1.6)),
        # pancarta CARBONARA del peto de la grada de cerca (letras redondas)
        ('pit_v2_pancarta', 60, (-13.0, 17.0, 9.4), (-18.0, 6.5, 8.7)),
        # pila de ruedas y par tumbado del box 5 (x -33) desde el pit lane
        ('pit_v2_ruedas', 45, (-31.5, 10.5, 1.4), (-34.9, 3.6, 0.5)),
        ('pit_v2_torre', 30, (34.0, 60.0, 18.0), (80.0, 14.0, 8.0)),
        # puerta de la torre desde el pit lane (altura de camara 1.4 m)
        ('pit_v2_torre_pie', 35, (73.5, 12.5, 1.4), (78.0, 5.2, 1.9)),
    )
    for m in bpy.data.materials:
        if m.name.startswith('MAT_PIT_'):
            m.use_backface_culling = True
    hechos = []
    for nombre, lente, pos, obj in tomas:
        cam_d.lens = lente
        mirar(cam, pos, obj)
        png = os.path.join(dir_prev, nombre + '.png')
        escena.render.filepath = png
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(png), 'no se genero ' + png
        hechos.append(png)

    dir_blend = os.path.join(BASE, 'blend')
    os.makedirs(dir_blend, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(dir_blend, 'pit_kit_v2.blend'))
    print('== TEST OK == pit_kit_v2: boxes %d tris (%d coches), muro %d, torre %d, '
          'pasarela %d, %d previews' % (t_boxes, n_coches, t_muro, t_torre, t_pas,
                                        len(hechos)))


try:
    main()
except Exception:
    traceback.print_exc()
    print('== TEST FALLO ==')
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
