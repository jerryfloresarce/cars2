"""test_carrera_kit_v2.py — prueba de carrera_kit_v2 (tribuna con publico de
coches). Construye build_tribuna(largo=45, filas=12) (lo que usa la escena),
verifica API / nombres / sombreado plano / caras coplanares / presupuesto de
triangulos / identidad del resto de piezas con la v1, renderiza (EEVEE,
1280x720, sol + cielo suave):
  previews/tribuna_v2_frente.png   (frontal cercano: se ven coches y ojos)
  previews/tribuna_v2_lado.png     (lateral: muro blanco liso, rampa, perfil)
  previews/tribuna_v2_detalle.png  (primer plano de los coches-espectador)
  previews/tribuna_v2_general.png  (3/4 de toda la pieza)
  previews/tribuna_v2_trasera.png  (por detras)
  previews/tribuna_v2_pista.png    (ojo del piloto, oblicua a ~75 m)
  previews/tribuna_v2_lejos.png    (ojo del piloto, oblicua a ~150 m)
  previews/tribuna_v2_pasillo.png  (camara alta: junta rampa/terrazas, ruedas)
Los renders se hacen con backface culling activado (condicion de AC).
Guarda blend/carrera_kit_v2.blend.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_carrera_kit_v2.py"
"""

import importlib.util
import inspect
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
LARGO, FILAS = 45, 12
MAX_TRIS = 16000


def cargar(nombre):
    ruta = os.path.join(BASE, nombre + '.py')
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod      # inspect.getsource de clases lo necesita
    spec.loader.exec_module(mod)
    return mod


def tris_de(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def pares_coplanares(me, area_min=0.02):
    """Pares de caras en el mismo plano cuyas cajas envolventes se solapan
    (= candidatas a z-fighting). Devuelve lista de (i, j)."""
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
        """SAT entre dos poligonos convexos 2D: True si se solapan > tol."""
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
        # ejes 2D del plano: se descarta el eje dominante de la normal
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


def firma(raiz):
    """Firma geometrica de una pieza (para comparar v1 y v2)."""
    out = []
    obs = [raiz] + sorted(raiz.children_recursive, key=lambda o: o.name)
    for ob in obs:
        fila = [ob.type, ob.name.split('.')[0],
                tuple(round(v, 4) for v in ob.location),
                tuple(round(v, 4) for v in ob.rotation_euler)]
        if ob.type == 'MESH':
            me = ob.data
            sx = sum(v.co.x for v in me.vertices)
            sy = sum(v.co.y for v in me.vertices)
            sz = sum(v.co.z for v in me.vertices)
            fila += [len(me.vertices), len(me.polygons),
                     round(sx, 2), round(sy, 2), round(sz, 2),
                     tuple(m.name for m in me.materials),
                     tuple(p.material_index for p in me.polygons)]
        out.append(tuple(fila))
    return out


def borrar_col(c):
    for ob in list(c.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(c)


def mirar(cam, pos, objetivo):
    cam.location = Vector(pos)
    d = Vector(objetivo) - Vector(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    v2 = cargar('carrera_kit_v2')
    v1 = cargar('carrera_kit')
    escena = bpy.context.scene

    # ---------------------------------------------- 1) resto de piezas = v1
    otras = ('_mat', '_raiz', '_texto_3d', 'build_portico_meta', 'build_pantalla',
             'build_boxes', 'build_muro_valla', 'build_valla_publicitaria',
             'build_paca', 'build')
    for nombre in otras:
        assert inspect.getsource(getattr(v1, nombre)) == \
            inspect.getsource(getattr(v2, nombre)), 'fuente distinta: ' + nombre
    assert inspect.getsource(v1._MB) == inspect.getsource(v2._MB), '_MB distinta'
    for clave, val in v1._PALETA.items():
        assert v2._PALETA[clave] == val, 'paleta cambiada: ' + clave
    assert v1._PUBLICO == v2._PUBLICO
    for nombre in ('largo', 'filas', 'seed'):
        p1 = inspect.signature(v1.build_tribuna).parameters[nombre]
        p2 = inspect.signature(v2.build_tribuna).parameters[nombre]
        assert p1.default == p2.default and p1.kind == p2.kind
    assert list(inspect.signature(v1.build_tribuna).parameters) == \
        list(inspect.signature(v2.build_tribuna).parameters)
    piezas = (('build_portico_meta', {'ancho': 20}), ('build_pantalla', {}),
              ('build_boxes', {'n': 12}), ('build_muro_valla', {'largo': 10}),
              ('build_valla_publicitaria', {'largo': 8, 'texto': 'ALLINOL'}),
              ('build_paca', {}))
    for nombre, kw in piezas:
        firmas = []
        for mod in (v1, v2):
            c = bpy.data.collections.new('TMP_cmp')
            escena.collection.children.link(c)
            firmas.append(firma(getattr(mod, nombre)(c, **kw)))
            borrar_col(c)
        assert firmas[0] == firmas[1], 'geometria distinta en ' + nombre
    print('[test] resto de piezas identico a la v1: OK')

    # ---------------------------------------------- 2) robustez de parametros
    for kw in ({'largo': 40, 'filas': 12, 'seed': 7}, {'largo': 12, 'filas': 4},
               {'largo': 80, 'filas': 8, 'seed': 3}, {'largo': 22, 'filas': 1},
               {}):
        c = bpy.data.collections.new('TMP_par')
        escena.collection.children.link(c)
        r = v2.build_tribuna(c, **kw)
        t = sum(tris_de(o) for o in r.children if o.type == 'MESH')
        cop = 0
        for o in r.children:
            if o.type == 'MESH' and not o.name.split('.')[0].endswith('_publico'):
                assert not any(p.use_smooth for p in o.data.polygons)
                cop += len(pares_coplanares(o.data))
        xs_ = [(o.matrix_world @ Vector(b)).x for o in r.children for b in o.bound_box]
        print('[test] build_tribuna(%s): %d tris, %d pares coplanares, semiancho %.3f'
              % (kw, t, cop, max(xs_)))
        assert t <= MAX_TRIS, 'presupuesto superado con %s' % kw
        assert cop == 0, 'caras coplanares solapadas con %s' % kw
        assert abs(max(xs_) - (kw.get('largo', 40) / 2.0 + 0.05)) < 2e-3
        borrar_col(c)

    # ---------------------------------------------- 3) la tribuna de la escena
    col = bpy.data.collections.new('CARRERA_ASSET')
    escena.collection.children.link(col)
    raiz = v2.build_tribuna(col, largo=LARGO, filas=FILAS)
    assert raiz is not None and raiz.type == 'EMPTY'
    assert raiz.name == 'CARRERA_tribuna', raiz.name
    assert tuple(raiz.location) == (0.0, 0.0, 0.0)
    hijos = {o.name: o for o in raiz.children}
    for n in ('CARRERA_tribuna_estructura', 'CARRERA_tribuna_techo',
              'CARRERA_tribuna_publico'):
        assert n in hijos and hijos[n].type == 'MESH', 'falta ' + n
        assert hijos[n].name in col.objects
    for ob in hijos.values():
        for m in ob.data.materials:
            assert m.name.startswith('MAT_CARRERA_'), m.name

    bpy.context.view_layer.update()
    total = 0
    for n, ob in sorted(hijos.items()):
        t = tris_de(ob)
        total += t
        suaves = sum(1 for p in ob.data.polygons if p.use_smooth)
        print('[test] %-28s verts %6d  polys %6d  tris %6d  caras suaves %d  mats %d'
              % (n, len(ob.data.vertices), len(ob.data.polygons), t, suaves,
                 len(ob.data.materials)))
    print('[test] TRIS TOTALES tribuna(largo=%d, filas=%d): %d (max %d)'
          % (LARGO, FILAS, total, MAX_TRIS))
    assert total <= MAX_TRIS

    # sombreado plano y sin z-fighting en estructura y techo
    for n in ('CARRERA_tribuna_estructura', 'CARRERA_tribuna_techo'):
        me = hijos[n].data
        assert not any(p.use_smooth for p in me.polygons), n + ' tiene caras suaves'
        assert not me.has_custom_normals, n + ' tiene normales personalizadas'
        # vertices propios por cara: imposible interpolar normales entre planos
        assert len(me.vertices) == sum(len(p.vertices) for p in me.polygons), \
            n + ' comparte vertices entre caras'
        pares = pares_coplanares(me)
        print('[test] %s: pares de caras coplanares solapadas = %d' % (n, len(pares)))
        for i, j in pares[:10]:
            pi, pj = me.polygons[i], me.polygons[j]
            print('        ', i, tuple(round(c, 2) for c in pi.center), pi.material_index,
                  '<->', j, tuple(round(c, 2) for c in pj.center), pj.material_index)
        assert not pares, n + ' tiene caras coplanares solapadas'
    me_p = hijos['CARRERA_tribuna_publico'].data
    n_coches = sum(1 for p in me_p.polygons if len(p.vertices) == 8) // 3
    print('[test] coches-espectador: %d  (%.1f tris/coche)'
          % (n_coches, tris_de(hijos['CARRERA_tribuna_publico']) / max(1, n_coches)))
    print('[test] publico: pares coplanares (informativo) = %d'
          % len(pares_coplanares(me_p, area_min=0.002)))

    # huella
    xs, ys, zs = [], [], []
    for ob in hijos.values():
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            xs.append(w.x)
            ys.append(w.y)
            zs.append(w.z)
    print('[test] bbox x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]'
          % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    assert abs(min(zs)) < 1e-4, 'la base no esta en z=0'
    assert max(ys) <= FILAS * 0.85 + 0.19 and min(ys) >= -FILAS * 0.85 - 0.05
    # huella en X: +-(largo/2 + 0.05). (La v1 media +-(largo/2 + 0.8) por el
    # vuelo lateral del techo; la v2 es mas estrecha a proposito.)
    assert abs(max(xs) - (LARGO / 2.0 + 0.05)) < 2e-3, max(xs)
    assert abs(min(xs) + (LARGO / 2.0 + 0.05)) < 2e-3, min(xs)
    # el integrador (_zocalo_global) levanta un zocalo de piedra en bbox - 0.2 m
    # hasta z = 0.6: sus caras deben caer DENTRO del espesor de los muros
    # (laterales: 0.30 m desde x = +-largo/2; trasero: y_b+0.05 .. y_b+0.45),
    # a >= 8 cm de cualquier cara visible, para que no haya z-fighting.
    zoc_x = max(xs) - 0.2
    assert LARGO / 2.0 - 0.30 + 0.08 <= zoc_x <= LARGO / 2.0 - 0.08, zoc_x
    zoc_y0 = min(ys) + 0.2
    y_b = -FILAS * 0.85
    assert y_b + 0.05 + 0.08 <= zoc_y0 <= y_b + 0.45 - 0.08, zoc_y0
    zoc_y1 = max(ys) - 0.2          # detras de la cara trasera del faldon (oculto)
    assert zoc_y1 < FILAS * 0.85 + 0.18 - 0.14 - 0.04, zoc_y1
    print('[test] zocalo del integrador: x=+-%.3f (muro %.2f..%.2f)  y0=%.3f  y1=%.3f'
          % (zoc_x, LARGO / 2.0 - 0.30, LARGO / 2.0, zoc_y0, zoc_y1))
    # materiales del publico: cristal mate propio, sin el 'cabina' brillante
    mats_p = [m.name for m in me_p.materials]
    assert 'MAT_CARRERA_pub_cristal' in mats_p and 'MAT_CARRERA_cabina' not in mats_p
    n_mats = sum(len(o.data.materials) for o in hijos.values())
    print('[test] materiales (draw calls) por tribuna: %d' % n_mats)

    # ---------------------------------------------- 4) escenario de render
    # suelo de contexto (no forma parte del asset)
    me_s = bpy.data.meshes.new('TEST_suelo')
    me_s.from_pydata([(-90, -70, -0.02), (90, -70, -0.02), (90, 12.5, -0.02),
                      (-90, 12.5, -0.02), (-90, 12.5, -0.03), (90, 12.5, -0.03),
                      (90, 90, -0.03), (-90, 90, -0.03)], [],
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
    try:
        sol_d.angle = math.radians(2.0)
    except AttributeError:
        pass
    sol = bpy.data.objects.new('SOL', sol_d)
    escena.collection.objects.link(sol)
    sol.rotation_euler = Vector((-0.42, -0.55, -0.72)).to_track_quat('-Z', 'Y').to_euler()

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
    else:
        mundo.color = (0.50, 0.72, 0.98)
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
    cam_d.clip_end = 600

    dir_prev = os.path.join(BASE, 'previews')
    os.makedirs(dir_prev, exist_ok=True)
    y0 = FILAS * 0.85 + 0.18
    tomas = (
        # nombre, lente, posicion, objetivo
        ('tribuna_v2_frente', 50, (5.0, y0 + 34.0, 7.5), (5.0, 0.0, 5.6)),
        ('tribuna_v2_lado', 40, (LARGO / 2.0 + 38.0, 17.0, 9.0), (LARGO / 2.0 - 8.0, -1.0, 5.5)),
        ('tribuna_v2_detalle', 40, (4.2, y0 + 1.2, 4.4), (7.6, 3.2, 2.9)),
        ('tribuna_v2_general', 32, (30.0, y0 + 40.0, 19.0), (0.0, -1.0, 5.0)),
        ('tribuna_v2_trasera', 32, (-32.0, -50.0, 8.0), (0.0, -6.0, 5.5)),
        # angulo real de conduccion: ojo del piloto (1.3 m) acercandose por la
        # recta, vista oblicua a ~75 m y a ~150 m
        ('tribuna_v2_pista', 35, (-75.0, y0 + 9.0, 1.3), (-6.0, 0.0, 5.0)),
        ('tribuna_v2_lejos', 60, (-150.0, y0 + 10.0, 1.3), (0.0, 0.0, 5.5)),
        # junta rampa / terrazas y ruedas desde una camara alta de TV
        ('tribuna_v2_pasillo', 50, (1.5, y0 + 16.0, 13.0), (-0.5, 2.0, 3.0)),
    )
    # condicion de Assetto Corsa: backface culling en todos los materiales del
    # kit (una cara invertida o ausente se veria como un agujero en el render)
    culling_previo = {}
    for m in bpy.data.materials:
        if m.name.startswith('MAT_CARRERA_'):
            culling_previo[m.name] = m.use_backface_culling
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
    # variantes de otros tamanos (sin pasillos / un solo bloque): solo para
    # mirarlas en un preview; se borran antes de guardar el .blend
    c_var = bpy.data.collections.new('TMP_variantes')
    escena.collection.children.link(c_var)
    for kw, x_var in (({'largo': 12, 'filas': 4, 'seed': 2}, 49.0),
                      ({'largo': 22, 'filas': 7, 'seed': 5}, 70.0)):
        r = v2.build_tribuna(c_var, **kw)
        r.location = (x_var, 55.0, 0.0)
    cam_d.lens = 35
    mirar(cam, (66.0, 84.0, 7.0), (61.0, 55.0, 3.0))
    png = os.path.join(dir_prev, 'tribuna_v2_variantes.png')
    escena.render.filepath = png
    bpy.ops.render.render(write_still=True)
    assert os.path.isfile(png), 'no se genero ' + png
    hechos.append(png)
    borrar_col(c_var)
    for nombre_m, valor in culling_previo.items():
        bpy.data.materials[nombre_m].use_backface_culling = valor

    dir_blend = os.path.join(BASE, 'blend')
    os.makedirs(dir_blend, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(dir_blend, 'carrera_kit_v2.blend'))

    print('== TEST OK == tribuna v2: %d tris, %d coches, %d previews'
          % (total, n_coches, len(hechos)))


try:
    main()
except Exception:
    traceback.print_exc()
    print('== TEST FALLO ==')
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
