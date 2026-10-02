"""test_pit_kit.py — prueba de pit_kit (complejo de boxes de Porto Corsa).

Construye el escaparate build() (boxes n=20 + pit lane + muro de boxes +
torres + pasarela), verifica API / nombres / presupuestos de triangulos /
caras coplanares solapadas / plazas de boxes / tris por espectador, y
renderiza (EEVEE, 1280x720, sol + cielo suave, backface culling como en AC):
  previews/pit_kit.png              (escaparate, 3/4 desde arriba)
  previews/pit_boxes_frente.png     (desde el pit lane: numeros legibles)
  previews/pit_boxes_tribuna.png    (3/4 desde arriba: terrazas llenas, techo azul)
  previews/pit_torre_pasarela.png   (torre de control + pasarela)
  previews/pit_muro.png             (puestos del muro de boxes de cerca)
  previews/pit_boxes_trasera.png    (fachada trasera / paddock)
  previews/pit_boxes_interior.png   (dentro de un box: persiana, armario, ruedas)
  previews/pit_boxes_pista.png      (desde la pista a altura de piloto: el
                                     publico debe asomar sobre el peto)
  previews/pit_techo_postes.png     (bajo el techo: postes contra las vigas)
Guarda blend/pit_kit.blend.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_pit_kit.py"
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
PRESUP = {'boxes': 60000, 'muro': 2500, 'torre': 3000, 'pasarela': 5000}


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


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    pk = cargar('pit_kit')
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
    # pit board opaco desde el pit lane: alguna cara blanca mirando a -Y por
    # encima del pupitre (z > 2.05) en y ~ 0.22
    me_m = muro.data
    pb = [p for p in me_m.polygons if p.normal.y < -0.9 and p.center.z > 1.95
          and abs(p.center.y - 0.22) < 0.01 and p.material_index == 1]
    assert pb, 'pit board sin cara hacia el pit lane'

    # sin tapas: ninguna cara en los planos x = +-6; con tapas: las hay
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
    assert abs(tz0) < 1e-3

    pasarela = pk.build_pasarela(col_t, luz=22.0, alto=7.0, seed=0)
    assert pasarela.type == 'EMPTY' and pasarela.name == 'PIT_pasarela'
    t_pas = tris_arbol(pasarela)
    for o in pasarela.children:
        if not o.name.startswith('PIT_pasarela_texto'):
            informe_coplanares(o)
    (px0, px1), (py0, py1), (pz0, pz1) = bbox(pasarela)
    print('[test] pasarela: tris %d  bbox x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]'
          % (t_pas, px0, px1, py0, py1, pz0, pz1))
    assert t_pas <= PRESUP['pasarela'], t_pas
    assert abs(pz0 + 0.12) < 0.2
    # rampas y rellanos con cara inferior (visibles desde la pista con
    # backface culling): caras de material rampa (3) mirando hacia -Z
    me_pas = bpy.data.objects['PIT_pasarela_cuerpo'].data
    n_ramp_up = sum(1 for p in me_pas.polygons if p.material_index == 3 and p.normal.z > 0.5)
    n_ramp_dn = sum(1 for p in me_pas.polygons if p.material_index == 3 and p.normal.z < -0.5)
    print('[test] pasarela: caras de rampa/rellano hacia +Z %d, hacia -Z %d'
          % (n_ramp_up, n_ramp_dn))
    assert n_ramp_dn >= 14, n_ramp_dn      # 8 rampas + 6 rellanos intermedios

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
                                        'PIT_boxes_techo'):
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

    boxes = bpy.data.objects.get('PIT_boxes')
    assert boxes is not None and boxes.type == 'EMPTY'
    hijos = {o.name: o for o in boxes.children}
    for nm in ('PIT_boxes_edificio', 'PIT_boxes_grada', 'PIT_boxes_techo',
               'PIT_boxes_publico', 'PIT_boxes_numeros', 'PIT_boxes_rotulo'):
        assert nm in hijos and hijos[nm].type == 'MESH', 'falta ' + nm
    # los numeros: una sola malla con transform identidad y 20 islas
    # centradas en cada box (x de cada isla ~ centro del box)
    num = hijos['PIT_boxes_numeros']
    assert all(abs(v) < 1e-6 for v in num.location) and \
        all(abs(v) < 1e-6 for v in num.rotation_euler)
    xs_num = sorted(v.co.x for v in num.data.vertices)
    for i in range(N_BOXES):
        cx = -60.0 + (i + 0.5) * 6.0
        assert any(abs(x - cx) < 0.6 for x in xs_num), 'sin numero en el box %d' % (i + 1)
    assert all(v.co.y > 6.5 for v in num.data.vertices), 'numeros dentro de la fachada'
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.name.startswith('PIT_'):
            assert ob.name.startswith('PIT_'), ob.name
            for m in ob.data.materials:
                assert m.name.startswith('MAT_PIT_'), m.name
            assert not ob.data.has_custom_normals

    total = 0
    for nm in ('PIT_boxes_edificio', 'PIT_boxes_grada', 'PIT_boxes_techo'):
        total += informe_coplanares(hijos[nm])
        assert not any(p.use_smooth for p in hijos[nm].data.polygons), nm + ' caras suaves'
        # vertices propios por cara (normales partidas de fabrica)
        assert len(hijos[nm].data.vertices) == sum(len(p.vertices)
                                                   for p in hijos[nm].data.polygons)
    t_pub = tris_de(hijos['PIT_boxes_publico'])
    me_p = hijos['PIT_boxes_publico'].data
    n_coches = sum(1 for p in me_p.polygons if len(p.vertices) == 8)
    print('[test] publico: %d coches, %d tris (%.1f tris/coche)'
          % (n_coches, t_pub, t_pub / max(1, n_coches)))
    assert n_coches > 0 and t_pub / n_coches <= 60.0
    t_num = tris_de(hijos['PIT_boxes_numeros'])
    t_boxes = tris_arbol(boxes)
    print('[test] boxes: edificio %d  grada %d  techo %d  publico %d  numeros %d  TOTAL %d (max %d)'
          % (tris_de(hijos['PIT_boxes_edificio']), tris_de(hijos['PIT_boxes_grada']),
             tris_de(hijos['PIT_boxes_techo']), t_pub, t_num, t_boxes, PRESUP['boxes']))
    assert t_boxes <= PRESUP['boxes']
    (bx0, bx1), (by0, by1), (bz0, bz1) = bbox(boxes)
    print('[test] boxes bbox x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]'
          % (bx0, bx1, by0, by1, bz0, bz1))
    assert abs(bz0) < 1e-3 and abs(bx0 + 60.3) < 1e-3 and abs(bx1 - 60.3) < 1e-3
    n_mats = sum(len(o.data.materials) for o in hijos.values() if o.type == 'MESH')
    print('[test] materiales (draw calls) del edificio de boxes: %d' % n_mats)
    t_total = tris_arbol(raiz)
    print('[test] escaparate completo: %d tris' % t_total)

    # --- postes del techo: cada poste (acero, material 2) acaba en la cara
    # inferior de una viga (blanco, material 4, cara hacia -Z) que lo cubre en x
    me_t = hijos['PIT_boxes_techo'].data
    z_vig = pk._Z_TECHO - 0.35
    vigas = []
    for p in me_t.polygons:
        if p.material_index == 4 and p.normal.z < -0.9 and abs(p.center.z - z_vig) < 1e-3:
            xs = [me_t.vertices[v].co.x for v in p.vertices]
            vigas.append((min(xs), max(xs)))
    postes = {}
    for p in me_t.polygons:
        if p.material_index == 2 and abs(p.normal.z) < 0.1:
            zs = [me_t.vertices[v].co.z for v in p.vertices]
            if abs(max(zs) - z_vig) < 1e-3:
                postes[round(p.center.x, 1)] = p.center.x
    sueltos = [x for x in postes.values() if not any(a - 1e-3 <= x <= b + 1e-3 for a, b in vigas)]
    print('[test] techo: %d vigas, %d postes, %d postes sin viga encima' % (
        len(vigas), len(postes), len(sueltos)))
    assert len(postes) >= 10 and not sueltos, sueltos

    # --- linea de vision desde la pista a altura de piloto (y=30, z=1.4):
    # los ojos (material blanco del publico, hexagonos) de las filas 2.. deben
    # quedar por encima de la visual que pasa por la coronacion del peto
    z_peto = pk._Z_GRADA + pk._H_PETO
    y_peto = 6.5
    ojos = [p.center for p in me_p.polygons
            if len(p.vertices) == 6 and p.material_index == pk._PM_OJO]
    assert ojos
    vis, tot = 0, 0
    for c in ojos:
        if c.y > 6.2 - 1.76:          # primera fila: tapada por el peto, se acepta
            continue
        z_lin = 1.4 + (z_peto - 1.4) * (30.0 - c.y) / (30.0 - y_peto)
        tot += 1
        if c.z > z_lin:
            vis += 1
    print('[test] visual desde la pista: %d de %d ojos (filas 2..) sobre el peto (%.1f%%)'
          % (vis, tot, 100.0 * vis / max(1, tot)))
    assert vis >= 0.95 * tot

    # ------------------------------------------------ 3) render
    # sol calido y mas fuerte, que ilumina la fachada principal (+Y): el rayo
    # viaja hacia -Y; cielo algo mas neutro (previews saturados, como la peli)
    sol_d = bpy.data.lights.new('SOL', type='SUN')
    sol_d.energy = 3.8
    sol_d.color = (1.0, 0.93, 0.82)
    try:
        sol_d.angle = math.radians(2.0)
    except AttributeError:
        pass
    sol = bpy.data.objects.new('SOL', sol_d)
    escena.collection.objects.link(sol)
    sol.rotation_euler = Vector((0.45, -0.55, -0.72)).to_track_quat('-Z', 'Y').to_euler()

    # cielo: luz ambiente neutra y suave para la escena; lo que VE la camara
    # es un azul de cielo limpio (Light Path / Is Camera Ray)
    mundo = bpy.data.worlds.new('CIELO')
    try:
        if not mundo.use_nodes:
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
        amb.inputs[0].default_value = (0.74, 0.80, 0.90, 1.0)
        amb.inputs[1].default_value = 0.45
        cielo = nt_w.nodes.new('ShaderNodeBackground')
        cielo.inputs[0].default_value = (0.40, 0.64, 0.96, 1.0)
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
    escena.render.resolution_x = 1280
    escena.render.resolution_y = 720
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
        ('pit_kit', 28, (118.0, 96.0, 54.0), (4.0, 12.0, 4.0)),
        ('pit_boxes_frente', 40, (12.0, 16.0, 2.0), (5.0, 6.5, 3.0)),
        ('pit_boxes_tribuna', 32, (44.0, 52.0, 26.0), (-8.0, 0.0, 11.0)),
        ('pit_torre_pasarela', 32, (28.0, 64.0, 16.0), (68.0, 22.0, 8.0)),
        ('pit_muro', 35, (-9.0, 9.0, 3.6), (-1.0, 18.5, 1.9)),
        ('pit_boxes_trasera', 32, (-40.0, -60.0, 12.0), (0.0, -6.0, 7.0)),
        ('pit_boxes_interior', 28, (-34.0, 13.0, 1.6), (-32.5, 2.0, 1.8)),
        ('pit_boxes_pista', 35, (12.0, 30.0, 1.4), (-4.0, 4.0, 11.0)),
        ('pit_techo_postes', 35, (23.0, 5.6, 13.8), (14.65, 3.3, 16.6)),
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
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(dir_blend, 'pit_kit.blend'))
    print('== TEST OK == pit_kit: boxes %d tris (%d coches), muro %d, torre %d, '
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
