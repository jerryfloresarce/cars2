"""test_review_tribuna.py - script de REVISION (solo lectura del modulo
carrera_kit_v2): construye build_tribuna(largo=45, filas=12), hace comprobaciones
numericas y renderiza angulos extra con backface culling activado (como AC).
No modifica el modulo ni guarda .blend."""

import importlib.util
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
LARGO, FILAS = 45, 12


def cargar(nombre):
    ruta = os.path.join(BASE, nombre + '.py')
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


def mirar(cam, pos, objetivo):
    cam.location = Vector(pos)
    d = Vector(objetivo) - Vector(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def firma_malla(ob):
    me = ob.data
    return (len(me.vertices), len(me.polygons),
            round(sum(v.co.x for v in me.vertices), 3),
            round(sum(v.co.y for v in me.vertices), 3),
            round(sum(v.co.z for v in me.vertices), 3))


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    v2 = cargar('carrera_kit_v2')
    v1 = cargar('carrera_kit')
    escena = bpy.context.scene

    # ---- bbox v1 vs v2 (lo que usa el integrador para zocalos)
    def bbox(raiz):
        bpy.context.view_layer.update()
        xs, ys, zs = [], [], []
        for ob in raiz.children_recursive:
            if ob.type != 'MESH':
                continue
            for c in ob.bound_box:
                w = ob.matrix_world @ Vector(c)
                xs.append(w.x); ys.append(w.y); zs.append(w.z)
        return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

    c1 = bpy.data.collections.new('TMP_v1')
    escena.collection.children.link(c1)
    r1 = v1.build_tribuna(c1, largo=LARGO, filas=FILAS)
    print('[rev] bbox v1: x[%.2f %.2f] y[%.2f %.2f] z[%.2f %.2f]' % bbox(r1))
    for ob in list(c1.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(c1)

    # ---- determinismo
    firmas = []
    for k in range(2):
        c = bpy.data.collections.new('TMP_det')
        escena.collection.children.link(c)
        r = v2.build_tribuna(c, largo=LARGO, filas=FILAS)
        firmas.append([firma_malla(o) for o in sorted(r.children, key=lambda o: o.name.split('.')[0])])
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(c)
    print('[rev] determinista (misma seed -> misma malla):', firmas[0] == firmas[1])

    col = bpy.data.collections.new('CARRERA_ASSET')
    escena.collection.children.link(col)
    raiz = v2.build_tribuna(col, largo=LARGO, filas=FILAS)
    print('[rev] bbox v2: x[%.2f %.2f] y[%.2f %.2f] z[%.2f %.2f]' % bbox(raiz))
    hijos = {o.name: o for o in raiz.children}
    print('[rev] hijos:', sorted(hijos))
    for n, ob in sorted(hijos.items()):
        me = ob.data
        me.calc_loop_triangles()
        print('[rev] %s: tris %d, mats %s, loc %s rot %s'
              % (n, len(me.loop_triangles), [m.name for m in me.materials],
                 tuple(round(v, 3) for v in ob.location),
                 tuple(round(v, 3) for v in ob.rotation_euler)))
        usados = set(p.material_index for p in me.polygons)
        print('[rev]    slots usados %d de %d' % (len(usados), len(me.materials)))
        # planaridad de n-gonos
        peor = 0.0
        for p in me.polygons:
            if len(p.vertices) > 3:
                n_ = p.normal
                d0 = n_.dot(me.vertices[p.vertices[0]].co)
                for vi in p.vertices:
                    peor = max(peor, abs(n_.dot(me.vertices[vi].co) - d0))
        print('[rev]    desviacion maxima de planaridad: %.4f m' % peor)
        deg = sum(1 for p in me.polygons if p.area < 1e-6)
        print('[rev]    caras degeneradas: %d' % deg)

    # ojos: normal media debe mirar a +Y
    pub = hijos['CARRERA_tribuna_publico'].data
    i_ojo = [i for i, m in enumerate(pub.materials) if m.name.endswith('_ojo')][0]
    ny = [p.normal.y for p in pub.polygons if p.material_index == i_ojo]
    nz = [p.normal.z for p in pub.polygons if p.material_index == i_ojo]
    print('[rev] ojos: %d caras, normal.y min %.3f media %.3f ; normal.z media %.3f'
          % (len(ny), min(ny), sum(ny) / len(ny), sum(nz) / len(nz)))
    # tamano de coches
    areas = [p.area for p in pub.polygons if p.material_index == i_ojo]
    print('[rev] area ojo min %.3f max %.3f m2 (diametro aprox %.2f..%.2f m)'
          % (min(areas), max(areas), 2 * math.sqrt(min(areas) / math.pi),
             2 * math.sqrt(max(areas) / math.pi)))

    # ---- backface culling en todos los materiales (como en AC)
    for m in bpy.data.materials:
        try:
            m.use_backface_culling = True
        except AttributeError:
            pass

    # ---- escenario
    me_s = bpy.data.meshes.new('TEST_suelo')
    me_s.from_pydata([(-120, -70, -0.02), (120, -70, -0.02), (120, 12.5, -0.02),
                      (-120, 12.5, -0.02), (-120, 12.5, -0.03), (120, 12.5, -0.03),
                      (120, 90, -0.03), (-120, 90, -0.03)], [],
                     [(0, 1, 2, 3), (4, 5, 6, 7)])
    for nombre_m, colr in (('TEST_hierba', (0.30, 0.52, 0.22)),
                           ('TEST_asfalto', (0.16, 0.16, 0.17))):
        m = bpy.data.materials.new(nombre_m)
        m.use_nodes = True
        bs = m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (*colr, 1.0)
        bs.inputs['Roughness'].default_value = 0.9
        me_s.materials.append(m)
    me_s.polygons[1].material_index = 1
    suelo = bpy.data.objects.new('TEST_suelo', me_s)
    escena.collection.objects.link(suelo)

    sol_d = bpy.data.lights.new('SOL', type='SUN')
    sol_d.energy = 2.5
    sol_d.color = (1.0, 0.96, 0.90)
    sol = bpy.data.objects.new('SOL', sol_d)
    escena.collection.objects.link(sol)

    def poner_sol(v):
        sol.rotation_euler = Vector(v).to_track_quat('-Z', 'Y').to_euler()

    mundo = bpy.data.worlds.new('CIELO')
    try:
        mundo.use_nodes = True
    except AttributeError:
        pass
    fondo_n = None
    if getattr(mundo, 'node_tree', None):
        for n in mundo.node_tree.nodes:
            if n.type == 'BACKGROUND':
                fondo_n = n
                break
    if fondo_n is not None:
        fondo_n.inputs[0].default_value = (0.50, 0.72, 0.98, 1.0)
        fondo_n.inputs[1].default_value = 0.55
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

    cam_d = bpy.data.cameras.new('CAM_rev')
    cam = bpy.data.objects.new('CAM_rev', cam_d)
    escena.collection.objects.link(cam)
    escena.camera = cam
    cam_d.clip_end = 800

    dir_prev = os.path.join(BASE, 'previews')
    y0 = FILAS * 0.85 + 0.18
    prof = 1.674
    base, alto = 0.6, 0.75
    a2 = LARGO / 2.0
    fila = 4
    y_f = y0 - 0.14 - (fila + 0.5) * prof
    z_f = base + fila * alto
    sol_frente = (-0.42, -0.55, -0.72)
    sol_lateral = (-0.80, -0.15, -0.55)      # rasante sobre el muro lateral +X
    sol_tras = (0.30, 0.65, -0.70)           # desde detras
    tomas = (
        # nombre, lente, posicion, objetivo, sol
        ('review_tribuna_oblicua_zoom', 90, (-52.0, y0 + 11.0, 1.3), (-10.0, 3.0, 4.5), sol_frente),
        ('review_tribuna_pasando', 30, (-30.0, y0 + 9.0, 1.3), (-10.0, 0.0, 4.0), sol_frente),
        ('review_tribuna_tv_alta', 100, (10.0, y0 + 45.0, 24.0), (6.0, 0.0, 4.0), sol_frente),
        ('review_tribuna_coche_bajo', 50, (8.0, y0 + 2.5, 0.9), (8.0, y0 - 1.0, 1.3), sol_frente),
    )
    for nombre, lente, pos, obj, sv in tomas:
        cam_d.lens = lente
        mirar(cam, pos, obj)
        poner_sol(sv)
        png = os.path.join(dir_prev, nombre + '.png')
        escena.render.filepath = png
        bpy.ops.render.render(write_still=True)
        print('[rev] render', png, os.path.isfile(png))

    print('== REVIEW OK ==')


try:
    main()
except Exception:
    traceback.print_exc()
    print('== REVIEW FALLO ==')
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
