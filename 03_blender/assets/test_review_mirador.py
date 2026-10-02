"""test_review_mirador.py - revision independiente de mirador_kit (NO edita el
modulo). Comprueba: caras perdidas en validate(), caras degeneradas, caras
coplanares solapadas (z-fighting), bounding boxes / origen, y renderiza vistas
extra CON backface culling (como Assetto Corsa) en previews/review_mirador_*.png
"""

import importlib.util
import math
import os
import traceback

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
RES = (1280, 720)


def _desc(ob):
    r = [ob]
    for h in ob.children:
        r.extend(_desc(h))
    return r


def _tris(obs):
    n = 0
    for ob in obs:
        if ob.type == 'MESH':
            ob.data.calc_loop_triangles()
            n += len(ob.data.loop_triangles)
    return n


def _bbox(obs):
    bpy.context.view_layer.update()
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for ob in obs:
        if ob.type != 'MESH':
            continue
        for v in ob.data.vertices:
            p = ob.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], p[i])
                mx[i] = max(mx[i], p[i])
    return mn, mx


# ------------------------------------------------------------ solapes coplanares

def _clip(subject, clipper):
    """Sutherland-Hodgman 2D (poligonos convexos, clipper CCW)."""
    out = subject
    n = len(clipper)
    for i in range(n):
        a = clipper[i]
        b = clipper[(i + 1) % n]
        inp = out
        out = []
        if not inp:
            break
        for j in range(len(inp)):
            p = inp[j]
            q = inp[(j + 1) % len(inp)]
            sp = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
            sq = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
            if sp >= 0:
                out.append(p)
            if (sp >= 0) != (sq >= 0):
                t = sp / (sp - sq)
                out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def _area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _solapes(obs, etiqueta, tol_d=0.004, max_print=14):
    """Pares de caras coplanares (misma orientacion, |d| < tol_d) cuyo solape
    en el plano supera 20 cm2."""
    bpy.context.view_layer.update()
    caras = []
    for ob in obs:
        if ob.type != 'MESH':
            continue
        me = ob.data
        mw = ob.matrix_world
        for p in me.polygons:
            pts = [mw @ me.vertices[i].co for i in p.vertices]
            n = (mw.to_3x3() @ p.normal).normalized()
            if p.area < 1e-7:
                continue
            mat = me.materials[p.material_index].name if me.materials else '-'
            caras.append((n, pts, mat, ob.name))
    grupos = {}
    for n, pts, mat, nom in caras:
        d = n.dot(pts[0])
        clave = (round(n.x, 2), round(n.y, 2), round(n.z, 2))
        grupos.setdefault(clave, []).append((d, n, pts, mat, nom))
    hall = []
    for clave, lst in grupos.items():
        lst.sort(key=lambda q: q[0])
        n0 = Vector(clave).normalized()
        ref = Vector((0, 0, 1)) if abs(n0.z) < 0.9 else Vector((1, 0, 0))
        u = n0.cross(ref).normalized()
        v = n0.cross(u).normalized()
        pro = []
        for d, n, pts, mat, nom in lst:
            p2 = [(p.dot(u), p.dot(v)) for p in pts]
            if _area(p2) < 0:
                p2.reverse()
            xs = [q[0] for q in p2]
            ys = [q[1] for q in p2]
            pro.append((d, p2, (min(xs), max(xs), min(ys), max(ys)), mat, nom, pts))
        for i in range(len(pro)):
            di, pi, bi, mi, ni, _ = pro[i]
            for j in range(i + 1, len(pro)):
                dj, pj, bj, mj, nj, ptsj = pro[j]
                if dj - di > tol_d:
                    break
                if bi[1] <= bj[0] + 1e-4 or bj[1] <= bi[0] + 1e-4 or \
                        bi[3] <= bj[2] + 1e-4 or bj[3] <= bi[2] + 1e-4:
                    continue
                inter = _clip(pi, pj)
                a = abs(_area(inter)) if len(inter) >= 3 else 0.0
                if a > 0.002:
                    c = sum(ptsj, Vector()) / len(ptsj)
                    hall.append((a, abs(dj - di), mi, mj, ni, nj, c, clave))
    hall.sort(key=lambda q: -q[0])
    print('  [%s] solapes coplanares (<%.0f mm): %d pares, area total %.2f m2' % (
        etiqueta, tol_d * 1000, len(hall), sum(h[0] for h in hall)))
    for a, dd, mi, mj, ni, nj, c, clave in hall[:max_print]:
        print('      %.3f m2 sep %.1f mm  %s | %s  @(%.2f,%.2f,%.2f) n=%s  [%s|%s]' % (
            a, dd * 1000, mi.replace('MAT_MIRADOR_', ''), mj.replace('MAT_MIRADOR_', ''),
            c.x, c.y, c.z, clave, ni.replace('MIRADOR_', ''), nj.replace('MIRADOR_', '')))
    return hall


def _mirar(cam, pos, objetivo):
    cam.location = Vector(pos)
    d = Vector(pos) - Vector(objetivo)
    cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()


def _render(escena, nombre):
    png = os.path.join(BASE, 'previews', nombre)
    escena.render.filepath = png
    bpy.ops.render.render(write_still=True)
    assert os.path.isfile(png)
    print('  render OK -> %s' % png)


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    spec = importlib.util.spec_from_file_location(
        'mirador_kit', os.path.join(BASE, 'mirador_kit.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # --- vigilar caras perdidas en validate()
    perdidas = []
    obj_orig = mod._MB.obj

    def obj_vigilado(self, nombre, col, padre=None):
        ob = obj_orig(self, nombre, col, padre)
        if len(ob.data.polygons) != len(self.f):
            perdidas.append((nombre, len(self.f), len(ob.data.polygons)))
        return ob
    mod._MB.obj = obj_vigilado

    escena = bpy.context.scene
    col = bpy.data.collections.new('REV')
    escena.collection.children.link(col)

    if os.environ.get('REVIEW_EDGE'):
        print('== CASOS LIMITE ==')
        casos = [
            ('parking', dict(ancho=16, fondo=13, alto=11)),
            ('parking', dict(ancho=8, fondo=8, alto=4.5)),
            ('parking', dict(ancho=60, fondo=30, alto=25)),
            ('parking', dict(ancho=40, fondo=18, alto=10.9)),
            ('parking', dict(ancho=40, fondo=18, alto=20, seed=7)),
            ('parking', dict(ancho=40, fondo=12, alto=20)),
            ('parking', dict(ancho=20, fondo=18, alto=14)),
            ('arcadas', dict(largo=6, alto=3, n_arcos=3)),
            ('arcadas', dict(largo=40, alto=2, n_arcos=5)),
            ('arcadas', dict(largo=8, alto=8, n_arcos=1)),
            ('arcadas', dict(largo=40, alto=8, n_arcos=0)),
            ('arcadas', dict(largo=40, alto=14, n_arcos=5)),
            ('murete', dict(largo=0.5, alto=0.3)),
            ('murete', dict(largo=30, alto=2.0)),
            ('mirador', dict(radio=3, faldon=0.2)),
            ('mirador', dict(radio=12)),
        ]
        fn = {'parking': mod.build_parking_terraza, 'arcadas': mod.build_muro_arcadas,
              'murete': mod.build_muro_piedra, 'mirador': mod.build_mirador}
        for tipo, kw in casos:
            try:
                r = fn[tipo](col, **kw)
                obs = _desc(r)
                mn, mx = _bbox(obs)
                extra = ''
                if tipo == 'parking':
                    a = {k: v for k, v in kw.items() if k in ('ancho', 'fondo', 'alto')}
                    pl = mod.plazas_parking(**a)
                    filas = sorted(set(p[1] for p in pl))
                    extra = ' plazas=%d filas=%s' % (len(pl), filas)
                print('  OK  %-8s %-40s tris %5d bbox x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f]%s' % (
                    tipo, kw, _tris(obs), mn.x, mx.x, mn.y, mx.y, mn.z, mx.z, extra))
                for o in obs:
                    bpy.data.objects.remove(o, do_unlink=True)
            except Exception:
                print('  FALLO %s %s' % (tipo, kw))
                traceback.print_exc()
        print('  caras perdidas en validate():', perdidas or 'ninguna')
        print('== CASOS LIMITE FIN ==')
        return

    # ------------------------------------------------ piezas sueltas en origen
    pk = mod.build_parking_terraza(col)
    pk.location = (0.0, 0.0, 0.0)
    ma1 = mod.build_muro_arcadas(col, seed=0)
    ma2 = mod.build_muro_arcadas(col, seed=1)
    ma3 = mod.build_muro_arcadas(col, seed=2)
    mp1 = mod.build_muro_piedra(col)
    mp2 = mod.build_muro_piedra(col, seed=1)
    mi = mod.build_mirador(col)

    print('== REVISION mirador_kit ==')
    print('  caras perdidas en validate():', perdidas or 'ninguna')
    for nombre, raiz in (('parking', pk), ('muro_arcadas', ma1),
                         ('muro_piedra', mp1), ('mirador', mi)):
        obs = _desc(raiz)
        mn, mx = _bbox(obs)
        print('  %-13s tris %5d  bbox x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]  root=%s/%s' % (
            nombre, _tris(obs), mn.x, mx.x, mn.y, mx.y, mn.z, mx.z, raiz.type, raiz.name))
        _solapes(obs, nombre)
    print('  plazas:', mod.plazas_parking())
    # determinismo + reutilizacion de materiales
    n_mats = len(bpy.data.materials)
    tmp = mod.build_muro_piedra(col)
    print('  materiales nuevos al reconstruir murete: %d' % (len(bpy.data.materials) - n_mats))
    bpy.data.objects.remove(tmp, do_unlink=True)
    malos = [m.name for m in bpy.data.materials if not m.name.startswith('MAT_MIRADOR_')]
    print('  materiales sin prefijo:', malos or 'ninguno')

    # ------------------------------------------------------------- colocacion
    # parking en el origen; muros teselados lejos en +X; mirador aparte
    ma1.location = (200.0 - 20.0, 0.0, 0.0)
    ma2.location = (200.0 + 20.0, 0.0, 0.0)
    # tercer tramo girado 14 grados pivotando en la arista trasera comun (curva)
    ang = math.radians(-14.0)
    piv = Vector((240.0, -0.9, 0.0))
    ma3.rotation_euler = (0.0, 0.0, ang)
    ma3.location = piv + Vector((20.0 * math.cos(ang) - 0.9 * math.sin(ang),
                                 20.0 * math.sin(ang) + 0.9 * math.cos(ang), 0.0))
    mp1.location = (200.0 - 5.0, -0.2, 8.0)
    mp2.location = (200.0 + 5.0, -0.2, 8.0)
    mi.location = (0.0, 200.0, 4.0)

    # proxies de coche en las plazas
    colores = ((0.80, 0.06, 0.04), (0.04, 0.22, 0.72), (0.95, 0.70, 0.04),
               (0.07, 0.48, 0.12), (0.38, 0.09, 0.55), (0.90, 0.88, 0.80))
    for i, (x, y, z, rz) in enumerate(mod.plazas_parking()):
        me = bpy.data.meshes.new('PROXY')
        hx, hy = 0.95, 2.1
        vs = [(-hx, -hy, 0.25), (hx, -hy, 0.25), (hx, hy, 0.25), (-hx, hy, 0.25),
              (-hx * 0.9, -hy * 0.8, 1.35), (hx * 0.9, -hy * 0.8, 1.35),
              (hx * 0.9, hy * 0.35, 1.35), (-hx * 0.9, hy * 0.35, 1.35)]
        fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
              (2, 3, 7, 6), (3, 0, 4, 7)]
        me.from_pydata(vs, [], fs)
        mp = bpy.data.materials.new('PROXYMAT_%d' % i)
        mp.use_nodes = True
        for nd in mp.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Base Color'].default_value = (*colores[i % 6], 1.0)
        me.materials.append(mp)
        pr = bpy.data.objects.new('PROXY_%02d' % i, me)
        col.objects.link(pr)
        pr.location = (x, y, z)
        pr.rotation_euler = (0, 0, rz)

    # backface culling como en AC
    for m in bpy.data.materials:
        try:
            m.use_backface_culling = True
        except AttributeError:
            pass

    # ------------------------------------------------------------------ escena
    sm = bpy.data.meshes.new('SUELO')
    s = 600.0
    sm.from_pydata([(-s, -s, -0.02), (s, -s, -0.02), (s, s, -0.02), (-s, s, -0.02)],
                   [], [(0, 1, 2, 3)])
    msu = bpy.data.materials.new('SUELO_MAT')
    msu.use_nodes = True
    for nd in msu.node_tree.nodes:
        if nd.type == 'BSDF_PRINCIPLED':
            nd.inputs['Base Color'].default_value = (0.30, 0.30, 0.29, 1.0)
    sm.materials.append(msu)
    suelo = bpy.data.objects.new('SUELO', sm)
    escena.collection.objects.link(suelo)

    cam_d = bpy.data.cameras.new('CAM')
    cam_d.clip_end = 3000.0
    cam = bpy.data.objects.new('CAM', cam_d)
    escena.collection.objects.link(cam)
    escena.camera = cam
    sol_d = bpy.data.lights.new('SOL', type='SUN')
    sol_d.energy = 2.9
    sol_d.color = (1.0, 0.95, 0.88)
    sol = bpy.data.objects.new('SOL', sol_d)
    escena.collection.objects.link(sol)
    sol.rotation_euler = (math.radians(50), 0.0, math.radians(148))
    mundo = bpy.data.worlds.new('CIELO')
    try:
        mundo.use_nodes = True
    except AttributeError:
        pass
    if getattr(mundo, 'node_tree', None):
        for n in mundo.node_tree.nodes:
            if n.type == 'BACKGROUND':
                n.inputs[0].default_value = (0.42, 0.66, 0.95, 1.0)
                n.inputs[1].default_value = 0.8
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
        escena.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    try:
        escena.view_settings.view_transform = 'Standard'
    except TypeError:
        pass

    # A. vista tipo pelicula (desde arriba, lado calle) con culling
    cam_d.lens = 38
    _mirar(cam, (38.0, 62.0, 46.0), (0.0, 0.0, 15.0))
    _render(escena, 'review_mirador_A_peli.png')
    # B. a pie de pista, lejos
    cam_d.lens = 30
    _mirar(cam, (-42.0, 80.0, 1.3), (0.0, 9.0, 10.5))
    _render(escena, 'review_mirador_B_pista.png')
    # C. entrada + cartel P + toldo de cerca
    cam_d.lens = 28
    _mirar(cam, (-7.0, 23.0, 1.8), (-13.5, 9.0, 3.4))
    _render(escena, 'review_mirador_C_entrada.png')
    # D. azotea: pozo de rampa, peto y farolas desde dentro
    cam_d.lens = 24
    _mirar(cam, (-4.0, -7.0, 24.5), (-17.0, 1.5, 19.6))
    _render(escena, 'review_mirador_D_azotea.png')
    # E. cornisa/capiteles desde arriba en escorzo (huecos con culling)
    cam_d.lens = 70
    _mirar(cam, (30.0, 34.0, 27.0), (19.0, 9.3, 15.6))
    _render(escena, 'review_mirador_E_cornisa.png')
    # F. junta de teselado del muro de arcadas + muretes encima
    cam_d.lens = 35
    _mirar(cam, (205.0, 17.0, 6.5), (200.0, 0.9, 6.2))
    _render(escena, 'review_mirador_F_junta.png')
    # G. tramo girado 14 grados (curva) visto desde arriba
    cam_d.lens = 35
    _mirar(cam, (236.0, 26.0, 20.0), (240.0, 0.0, 6.0))
    _render(escena, 'review_mirador_G_curva.png')
    # H. mirador desde la calzada (ojos de piloto)
    cam_d.lens = 28
    _mirar(cam, (-7.5, 200.0 - 9.0, 4.0 + 1.5), (0.5, 200.0 + 4.0, 4.0 + 1.0))
    _render(escena, 'review_mirador_H_mirador_calle.png')
    # I. mirador desde abajo / lateral (tambor, testa)
    cam_d.lens = 35
    _mirar(cam, (17.0, 200.0 - 7.0, 2.2), (0.0, 200.0 + 2.5, 3.0))
    _render(escena, 'review_mirador_I_mirador_lado.png')
    print('== REVISION OK ==')


try:
    main()
except Exception:
    traceback.print_exc()
    import sys
    sys.stdout.flush()
    os._exit(1)
