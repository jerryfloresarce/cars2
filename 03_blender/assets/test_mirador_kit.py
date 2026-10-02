"""test_mirador_kit.py — construye el muestrario de mirador_kit, comprueba API
y presupuestos de tris, renderiza las previews (EEVEE, 1280x720, sol + cielo
suave) y guarda blend/mirador_kit.blend.

Previews obligatorias:
  previews/mirador_kit.png            muestrario completo
  previews/mirador_parking.png        tres cuartos cenital del parking (plazas)
  previews/mirador_muro_arcadas.png   muro de arcadas
Extra (revision desde todos los lados):
  previews/mirador_parking_calle.png  parking a pie de calle (fachada +Y)
  previews/mirador_parking_tras.png   parking por detras / lado rampa
  previews/mirador_parking_plazas.png parking con cajas-proxy en plazas_parking()
  previews/mirador_mirador.png        mirador de cerca
  previews/mirador_muros_lado.png     muro de arcadas por detras + muretes
  previews/mirador_muro_curvo.png     muro de arcadas en S (tramos ingleteados)
  previews/mirador_muro_curvo_junta.png  juntas ingleteadas de cerca
  previews/mirador_lod.png            parking 60x30x25 y mirador r=12 degradados

Ademas comprueba: degradacion automatica de detalle (parking y mirador
grandes dentro del tope), piedra de la peli con cualquier seed, sillares de
acento sin solapes y ajuste exacto (< 2 mm) de las testas ingleteadas.

Variable de entorno MIRADOR_VISTAS="kit,parking,..." limita las vistas.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_mirador_kit.py"
"""

import importlib.util
import math
import os
import traceback

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
RES = (1280, 720)


def _descendientes(ob):
    res = [ob]
    for h in ob.children:
        res.extend(_descendientes(h))
    return res


def _tris(obs):
    n = 0
    for ob in obs:
        if ob.type == 'MESH':
            ob.data.calc_loop_triangles()
            n += len(ob.data.loop_triangles)
    return n


def _encuadrar(escena, cam, obs, direccion, margen=1.05):
    """Coloca la camara mirando en -direccion, lo mas cerca posible con todas
    las esquinas de las bounding boxes dentro del cuadro."""
    bpy.context.view_layer.update()
    pts = []
    for ob in obs:
        if ob.type != 'MESH':
            continue
        for c in ob.bound_box:
            pts.append(ob.matrix_world @ Vector(c))
    dirv = Vector(direccion).normalized()
    rot = dirv.to_track_quat('Z', 'Y')
    cam.rotation_euler = rot.to_euler()
    inv = rot.to_matrix().inverted()
    tanx = (cam.data.sensor_width / 2.0) / cam.data.lens
    tany = tanx * RES[1] / RES[0]
    loc = [inv @ p for p in pts]
    cx = cy = 0.0
    d = 10.0
    for _ in range(12):
        d = max(max(p.z + abs(p.x - cx) / tanx, p.z + abs(p.y - cy) / tany)
                for p in loc) * margen
        us = [(p.x - cx) / (d - p.z) for p in loc]
        vs = [(p.y - cy) / (d - p.z) for p in loc]
        cx += (max(us) + min(us)) / 2.0 * d * 0.7
        cy += (max(vs) + min(vs)) / 2.0 * d * 0.7
    d = max(max(p.z + abs(p.x - cx) / tanx, p.z + abs(p.y - cy) / tany)
            for p in loc) * margen
    cam.location = rot.to_matrix() @ Vector((cx, cy, d))


def _render(escena, nombre):
    dir_prev = os.path.join(BASE, 'previews')
    os.makedirs(dir_prev, exist_ok=True)
    png = os.path.join(dir_prev, nombre)
    escena.render.filepath = png
    bpy.ops.render.render(write_still=True)
    assert os.path.isfile(png), 'no se genero %s' % png
    print('  render OK -> %s' % png)
    return png


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    ruta = os.path.join(BASE, 'mirador_kit.py')
    spec = importlib.util.spec_from_file_location('mirador_kit', ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    escena = bpy.context.scene
    col = bpy.data.collections.new('MIRADOR_ASSET')
    escena.collection.children.link(col)

    raiz = mod.build(col, seed=0)
    assert raiz is not None and raiz.name.startswith('MIRADOR_kit')
    bpy.context.view_layer.update()

    # ---------------------------------------------------------------- API
    for fn in ('build', 'build_parking_terraza', 'plazas_parking',
               'build_muro_arcadas', 'build_muro_piedra', 'build_mirador'):
        assert callable(getattr(mod, fn, None)), 'falta %s' % fn
    import inspect
    for fn, esperado in (('build_parking_terraza', (40.0, 18.0, 20.0)),
                         ('plazas_parking', (40.0, 18.0, 20.0))):
        sig = inspect.signature(getattr(mod, fn)).parameters
        assert tuple(sig[k].default for k in ('ancho', 'fondo', 'alto')) == esperado
    plazas = mod.plazas_parking()
    assert plazas and all(len(p) == 4 for p in plazas)
    assert 10 <= len(plazas) <= 12, 'plazas por defecto: %d' % len(plazas)
    assert len(set(round(p[1], 3) for p in plazas)) == 2, 'deben ser 2 filas'
    for x, y, z, rz in plazas:
        assert abs(x) + 0.95 <= 20.0 - 0.5 and abs(y) + 2.1 <= 9.0 - 0.5, \
            'plaza fuera de la azotea: %r' % ((x, y),)
        assert abs(z - 20.0) < 1e-6 and rz == 0.0

    def sin_solape(pl):
        for a in range(len(pl)):
            for b in range(a + 1, len(pl)):
                dx = abs(pl[a][0] - pl[b][0])
                dy = abs(pl[a][1] - pl[b][1])
                assert dx >= 1.9 + 0.3 or dy >= 4.2 + 0.3, 'plazas solapadas'
    sin_solape(plazas)
    print('  plazas_parking(): %d plazas -> %s' % (
        len(plazas), ' '.join('(%.2f,%.2f)' % (p[0], p[1]) for p in plazas)))
    for dims in ((34.0, 26.0, 12.0), (26.0, 16.0, 9.0), (14.0, 10.0, 6.0)):
        pv = mod.plazas_parking(*dims)
        sin_solape(pv)
        for x, y, z, rz in pv:
            assert abs(x) + 0.95 <= dims[0] / 2 - 0.5 and \
                abs(y) + 2.1 <= dims[1] / 2 - 0.5, 'plaza fuera: %r' % ((x, y),)
        print('  plazas_parking%r: %d plazas' % (dims, len(pv)))

    # --------------------------------------------------------- presupuestos
    piezas = {}
    for h in raiz.children:
        clave = h.name.split('.')[0]
        piezas.setdefault(clave, []).append(h)
    topes = {'MIRADOR_parking': 6000, 'MIRADOR_muro_arcadas': 1500,
             'MIRADOR_muro_piedra': 1500, 'MIRADOR_mirador': 4000}
    total = 0
    for clave in sorted(piezas):
        for h in piezas[clave]:
            n = _tris(_descendientes(h))
            total += n
            print('  pieza %-24s %5d tris (tope %d)' % (h.name, n, topes[clave]))
            for d in _descendientes(h):
                if d.type == 'MESH':
                    print('      %-34s %5d tris, %d mats' %
                          (d.name, _tris([d]), len(d.data.materials)))
            assert n <= topes[clave], '%s supera el tope (%d)' % (h.name, n)
            # bounding box en coordenadas locales de la pieza (para el integrador)
            inv = h.matrix_world.inverted()
            ps = [inv @ (d.matrix_world @ v.co) for d in _descendientes(h)
                  if d.type == 'MESH' for v in d.data.vertices]
            print('      bbox local x[%.2f, %.2f] y[%.2f, %.2f] z[%.2f, %.2f]' % (
                min(p.x for p in ps), max(p.x for p in ps),
                min(p.y for p in ps), max(p.y for p in ps),
                min(p.z for p in ps), max(p.z for p in ps)))
    for ob in col.all_objects:
        assert ob.name.startswith('MIRADOR_'), 'prefijo: %s' % ob.name
        if ob.type == 'MESH':
            for m in ob.data.materials:
                assert m.name.startswith('MAT_MIRADOR_'), m.name
    # variantes parametricas (no deben petar) en coleccion aparte, sin render
    col2 = bpy.data.collections.new('MIRADOR_VARIANTES')
    escena.collection.children.link(col2)
    v1 = mod.build_parking_terraza(col2, ancho=34.0, fondo=26.0, alto=12.0, seed=1)
    v2 = mod.build_parking_terraza(col2, ancho=14.0, fondo=10.0, alto=6.0, seed=2)
    v7 = mod.build_parking_terraza(col2, ancho=26.0, fondo=16.0, alto=9.0, seed=4)
    print('  variante parking26x16x9 %d tris' % _tris(_descendientes(v7)))
    v3 = mod.build_muro_arcadas(col2, largo=24.0, alto=5.0, n_arcos=4, seed=3)
    v4 = mod.build_muro_arcadas(col2, largo=12.0, alto=12.0, n_arcos=1, seed=3)
    v5 = mod.build_mirador(col2, radio=5.0, seed=4, faldon=0.0)
    v6 = mod.build_muro_piedra(col2, largo=4.0, alto=0.8)
    print('  variantes: parking34x26x12 %d tris, parking14x10x6 %d tris, '
          'arcadas24x5 %d, arcadas12x12 %d, mirador r5 %d, murete4 %d' % (
              _tris(_descendientes(v1)), _tris(_descendientes(v2)),
              _tris([v3]), _tris([v4]), _tris(_descendientes(v5)), _tris([v6])))
    # -- degradacion automatica de detalle: tamanos grandes dentro del tope
    for dims in ((48.0, 22.0, 20.0), (60.0, 30.0, 25.0), (80.0, 40.0, 30.0)):
        vg = mod.build_parking_terraza(col2, ancho=dims[0], fondo=dims[1],
                                       alto=dims[2])
        ng = _tris(_descendientes(vg))
        print('  parking %gx%gx%g: %d tris (lod %d)' % (dims + (ng, vg['mirador_lod'])))
        assert ng == vg['mirador_tris'], 'estimacion de tris incoherente'
        assert ng <= 6000, 'parking grande supera el tope: %d' % ng
    for rg in (9.0, 12.0, 18.0):
        vm = mod.build_mirador(col2, radio=rg)
        nm = _tris(_descendientes(vm))
        print('  mirador radio %g: %d tris (lod %d)' % (rg, nm, vm['mirador_lod']))
        assert nm == vm['mirador_tris'] and nm <= 4000, 'mirador grande: %d' % nm
    # -- cualquier seed conserva la piedra gris-rosada de la pelicula
    for sd in (1, 2, 7):
        vs = mod.build_parking_terraza(col2, seed=sd)
        nombres = set(m.name for d in _descendientes(vs) if d.type == 'MESH'
                      for m in d.data.materials)
        assert 'MAT_MIRADOR_piedra_palazzo' in nombres, 'seed %d sin piedra peli' % sd
        assert not [n for n in nombres if n.endswith(('_crema', '_gris'))
                    and 'palazzo' in n], 'seed %d cambia la piedra' % sd
    vc = mod.build_parking_terraza(col2, piedra='piedra_palazzo_crema',
                                   trasera='completa', barandilla=True,
                                   tope_tris=None)
    print('  parking trasera completa + barandilla, sin tope: %d tris' %
          _tris(_descendientes(vc)))
    # -- sillares de acento del muro de arcadas: nunca se pisan en su plano
    for sd in range(12):
        va = mod.build_muro_arcadas(col2, seed=sd)
        rects = []
        for p in va.data.polygons:
            if p.normal.y > 0.99 and abs(p.center.y - (0.9 + 0.04)) < 1e-4:
                xs = [va.data.vertices[i].co.x for i in p.vertices]
                zs = [va.data.vertices[i].co.z for i in p.vertices]
                rects.append((min(xs), max(xs), min(zs), max(zs)))
        assert rects, 'no encuentro los sillares de acento'
        for a in range(len(rects)):
            for b in range(a + 1, len(rects)):
                ra, rb = rects[a], rects[b]
                assert (ra[1] <= rb[0] + 1e-6 or rb[1] <= ra[0] + 1e-6 or
                        ra[3] <= rb[2] + 1e-6 or rb[3] <= ra[2] + 1e-6), \
                    'sillares solapados con seed %d' % sd
    print('  sillares de acento sin solapes (12 seeds)')
    for ob in list(col2.all_objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(col2)

    # ------------------------------------------------ muro de arcadas en curva
    # S de 7 cuerdas de 8 m con 14 grados por junta: 3 juntas concavas (giro a
    # izquierda) y 3 convexas. Se comprueba numericamente que las testas de
    # tramos contiguos coinciden (inglete exacto, sin cuna).
    col3 = bpy.data.collections.new('MIRADOR_CURVA')
    escena.collection.children.link(col3)
    rumbos = [math.radians(g) for g in (-21, -7, 7, 21, 7, -7, -21)]
    pts_c = [(0.0, 0.0)]
    for rb in rumbos:
        pts_c.append((pts_c[-1][0] + 8.0 * math.cos(rb),
                      pts_c[-1][1] + 8.0 * math.sin(rb)))
    curva = mod.build_muro_arcadas_curvo(col3, pts_c, alto=8.0, seed=0)
    assert curva.name.startswith('MIRADOR_muro_arcadas_curvo')
    bpy.context.view_layer.update()
    tramos_c = sorted((h for h in curva.children),
                      key=lambda o: (o.location.x - pts_c[0][0]) ** 2 +
                      (o.location.y - pts_c[0][1]) ** 2)
    assert len(tramos_c) == 7
    for h in tramos_c:
        assert _tris([h]) <= 1500, '%s: %d tris' % (h.name, _tris([h]))
    peor = 0.0
    for k in range(len(tramos_c) - 1):
        a, b = tramos_c[k], tramos_c[k + 1]
        ta = [a.matrix_world @ v.co for v in a.data.vertices
              if abs(v.co.x - 4.0) < 0.6 and v.co.x > 3.4]
        tb = [b.matrix_world @ v.co for v in b.data.vertices if v.co.x < -3.4]
        # vertices de la testa derecha de a (los desplazados por el inglete)
        pj = Vector((pts_c[k + 1][0], pts_c[k + 1][1], 0.0))
        bis = (rumbos[k] + rumbos[k + 1]) / 2.0
        n_bis = Vector((math.cos(bis), math.sin(bis), 0.0))
        en_plano_a = [p for p in ta if abs((p - pj).dot(n_bis)) < 1e-3]
        en_plano_b = [p for p in tb if abs((p - pj).dot(n_bis)) < 1e-3]
        assert len(en_plano_a) >= 20 and len(en_plano_b) >= 20, \
            'testas fuera del plano bisector en la junta %d' % k
        for p in en_plano_a:
            d = min((p - q).length for q in en_plano_b)
            peor = max(peor, d)
    print('  muro curvo: 7 tramos, %d tris/tramo, desajuste maximo entre testas '
          '%.2f mm' % (_tris([tramos_c[0]]), peor * 1000.0))
    assert peor < 2e-3, 'las testas ingleteadas no casan: %.1f mm' % (peor * 1e3)
    for ob in col3.all_objects:
        ob.hide_render = True

    # --------------------------------------------------------------- escena
    sm = bpy.data.meshes.new('SUELO')
    s = 220.0
    sm.from_pydata([(-s, -s, -0.02), (s, -s, -0.02), (s, s, -0.02), (-s, s, -0.02)],
                   [], [(0, 1, 2, 3)])
    msu = bpy.data.materials.new('MAT_SUELO_TEST')
    msu.use_nodes = True
    for nd in msu.node_tree.nodes:
        if nd.type == 'BSDF_PRINCIPLED':
            nd.inputs['Base Color'].default_value = (0.36, 0.34, 0.29, 1.0)
            nd.inputs['Roughness'].default_value = 0.95
    sm.materials.append(msu)
    suelo = bpy.data.objects.new('SUELO', sm)
    escena.collection.objects.link(suelo)

    cam_d = bpy.data.cameras.new('CAM_preview')
    cam_d.lens = 40
    cam_d.clip_end = 2000.0
    cam = bpy.data.objects.new('CAM_preview', cam_d)
    escena.collection.objects.link(cam)
    escena.camera = cam

    sol_d = bpy.data.lights.new('SOL', type='SUN')
    sol_d.energy = 2.9
    sol_d.color = (1.0, 0.95, 0.88)
    try:
        sol_d.angle = math.radians(2.0)
    except AttributeError:
        pass
    sol = bpy.data.objects.new('SOL', sol_d)
    escena.collection.objects.link(sol)
    sol.rotation_euler = (math.radians(50), 0.0, math.radians(148))

    mundo = bpy.data.worlds.new('CIELO')
    try:
        mundo.use_nodes = True
    except AttributeError:
        pass
    fondo = None
    if getattr(mundo, 'node_tree', None):
        for n in mundo.node_tree.nodes:
            if n.type == 'BACKGROUND':
                fondo = n
                break
    if fondo is not None:
        fondo.inputs[0].default_value = (0.42, 0.66, 0.95, 1.0)
        fondo.inputs[1].default_value = 0.8
    escena.world = mundo

    for motor in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            escena.render.engine = motor
            break
        except TypeError:
            continue
    escena.render.resolution_x, escena.render.resolution_y = RES
    escena.render.resolution_percentage = 100
    escena.render.image_settings.file_format = 'PNG'
    try:
        escena.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    try:
        escena.view_settings.view_transform = 'Standard'
    except TypeError:
        pass

    # previews CON backface culling, como renderiza Assetto Corsa: cualquier
    # cara de una sola hoja vista por detras se delataria como agujero
    for m in bpy.data.materials:
        if m.name.startswith('MAT_MIRADOR_'):
            try:
                m.use_backface_culling = True
            except AttributeError:
                pass

    todos = [ob for ob in col.all_objects if ob.type == 'MESH']
    parking =[h for h in raiz.children if h.name.startswith('MIRADOR_parking')][0]
    arcadas = [h for h in raiz.children if h.name.startswith('MIRADOR_muro_arcadas')][0]
    muretes = [h for h in raiz.children if h.name.startswith('MIRADOR_muro_piedra')]
    mirador = [h for h in raiz.children if h.name.startswith('MIRADOR_mirador')][0]

    def solo(grupos):
        visibles = set()
        for g in grupos:
            visibles.update(_descendientes(g))
        for ob in col.all_objects:
            ob.hide_render = ob not in visibles
        return [ob for ob in visibles if ob.type == 'MESH']

    vistas = os.environ.get('MIRADOR_VISTAS', '').strip()
    vistas = [v.strip() for v in vistas.split(',') if v.strip()] or None

    def quiero(v):
        return vistas is None or v in vistas

    if quiero('kit'):
        solo([raiz])
        cam_d.lens = 40
        _encuadrar(escena, cam, todos, (0.35, 1.0, 0.55), 1.03)
        _render(escena, 'mirador_kit.png')
    if quiero('parking'):
        obs = solo([parking])
        cam_d.lens = 45
        _encuadrar(escena, cam, obs, (0.55, 1.0, 0.95), 1.03)
        _render(escena, 'mirador_parking.png')
    if quiero('arcadas'):
        obs = solo([arcadas])
        cam_d.lens = 45
        _encuadrar(escena, cam, obs, (0.45, 1.0, 0.22), 1.03)
        _render(escena, 'mirador_muro_arcadas.png')
    if quiero('calle'):
        obs = solo([parking])
        cam_d.lens = 28
        _encuadrar(escena, cam, obs, (-0.55, 1.0, 0.06), 1.02)
        _render(escena, 'mirador_parking_calle.png')
    if quiero('tras'):
        obs = solo([parking])
        cam_d.lens = 40
        _encuadrar(escena, cam, obs, (-1.0, -0.8, 0.5), 1.03)
        _render(escena, 'mirador_parking_tras.png')
    if quiero('mirador'):
        obs = solo([mirador])
        cam_d.lens = 45
        _encuadrar(escena, cam, obs, (0.6, 1.0, 0.45), 1.03)
        _render(escena, 'mirador_mirador.png')
    if quiero('mirador2'):
        obs = solo([mirador])
        cam_d.lens = 35
        _encuadrar(escena, cam, obs, (-0.35, -1.0, 0.7), 1.03)
        _render(escena, 'mirador_mirador_dentro.png')
    if quiero('muros'):
        # muretes teselados de cerca (con el muro de arcadas de fondo, de testa)
        solo([arcadas] + muretes)
        obs = []
        for g in muretes:
            obs.extend(d for d in _descendientes(g) if d.type == 'MESH')
        cam_d.lens = 35
        _encuadrar(escena, cam, obs, (0.8, 1.0, 0.30), 1.10)
        _render(escena, 'mirador_muros_lado.png')
    if quiero('plazas'):
        obs = solo([parking])
        colp = bpy.data.collections.new('PROXIES')
        escena.collection.children.link(colp)
        colores = ((0.80, 0.06, 0.04), (0.04, 0.22, 0.72), (0.95, 0.70, 0.04),
                   (0.07, 0.48, 0.12), (0.38, 0.09, 0.55), (0.90, 0.88, 0.80))
        bpy.context.view_layer.update()
        for i, (x, y, z, rz) in enumerate(plazas):
            me = bpy.data.meshes.new('PROXY')
            hx, hy = 0.95, 2.1
            vs = [(-hx, -hy, 0.25), (hx, -hy, 0.25), (hx, hy, 0.25), (-hx, hy, 0.25),
                  (-hx * 0.9, -hy * 0.8, 1.3), (hx * 0.9, -hy * 0.8, 1.3),
                  (hx * 0.9, hy * 0.35, 1.3), (-hx * 0.9, hy * 0.35, 1.3)]
            fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
                  (2, 3, 7, 6), (3, 0, 4, 7)]
            me.from_pydata(vs, [], fs)
            mp = bpy.data.materials.new('MAT_PROXY_%d' % i)
            mp.use_nodes = True
            for nd in mp.node_tree.nodes:
                if nd.type == 'BSDF_PRINCIPLED':
                    nd.inputs['Base Color'].default_value = (*colores[i % 6], 1.0)
            me.materials.append(mp)
            pr = bpy.data.objects.new('PROXY_%02d' % i, me)
            colp.objects.link(pr)
            pr.location = parking.matrix_world @ Vector((x, y, z))
            pr.rotation_euler = (0.0, 0.0, rz)
        cam_d.lens = 45
        _encuadrar(escena, cam, obs, (0.25, 1.0, 1.25), 1.03)
        _render(escena, 'mirador_parking_plazas.png')
        for ob in list(colp.all_objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(colp)
    if quiero('curva'):
        solo([])
        for ob in col3.all_objects:
            ob.hide_render = False
        obs = [ob for ob in col3.all_objects if ob.type == 'MESH']
        cam_d.lens = 40
        _encuadrar(escena, cam, obs, (0.15, 1.0, 0.5), 1.03)
        _render(escena, 'mirador_muro_curvo.png')
        # de cerca: el tramo central, con una junta concava a su izquierda
        # (vista desde +Y queda a la derecha) y una convexa al otro lado
        cam_d.lens = 45
        _encuadrar(escena, cam, [tramos_c[3]], (0.10, 1.0, 0.42), 1.25)
        _render(escena, 'mirador_muro_curvo_junta.png')
        for ob in col3.all_objects:
            ob.hide_render = True
    if quiero('lod'):
        # piezas MUY grandes, degradadas automaticamente para caber en el tope
        solo([])
        col4 = bpy.data.collections.new('MIRADOR_LOD')
        escena.collection.children.link(col4)
        pg = mod.build_parking_terraza(col4, ancho=60.0, fondo=30.0, alto=25.0)
        mg = mod.build_mirador(col4, radio=12.0)
        mg.location = (48.0, 16.0, 4.0)
        bpy.context.view_layer.update()
        for m in bpy.data.materials:
            if m.name.startswith('MAT_MIRADOR_'):
                m.use_backface_culling = True
        obs = [ob for ob in col4.all_objects if ob.type == 'MESH']
        cam_d.lens = 40
        _encuadrar(escena, cam, obs, (0.45, 1.0, 0.5), 1.03)
        _render(escena, 'mirador_lod.png')
        for ob in list(col4.all_objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col4)

    solo([raiz])
    cam_d.lens = 40
    _encuadrar(escena, cam, todos, (0.35, 1.0, 0.55), 1.03)
    dir_blend = os.path.join(BASE, 'blend')
    os.makedirs(dir_blend, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(dir_blend, 'mirador_kit.blend'))

    mallas = sum(1 for ob in col.all_objects if ob.type == 'MESH')
    print('== TEST OK == mirador_kit: mallas %d, tris totales %d, plazas %d' %
          (mallas, total, len(plazas)))


try:
    main()
except Exception:
    traceback.print_exc()
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)
