"""urbanismo_escena.py - Instancia en la escena de Blender el plan urbano de
urbanismo.json (ronda 15, T7): calles, enlaces con valla, travesias, rampas
con terraplen y muros, escaleras, muros de contencion, casas en sus solares,
plazoletas y plazas. Lo llama integrar_escena.zona_pueblo() pasando un
contexto `ctx` con sus helpers (clone, root_col, LIB, M, lib, log, z_terreno,
valla_cierre, terraplen, zocalo_global, mat_simple, rnd).

Convenciones (ver RONDA15_PLAN.md): coordenadas de mundo, z absoluta; casa =
casas_kit_v2.build_casa con pivote en el centro de la fachada (y=0, +Y).
"""
import math

import bpy
from mathutils import Vector


def _dens3(pts, paso=3.0):
    """Polilinea 3D densificada a <= paso m (interpolacion lineal en x, y, z)."""
    out = []
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        l_ = math.hypot(b[0] - a[0], b[1] - a[1])
        n_ = max(1, int(math.ceil(l_ / paso)))
        for j in range(n_):
            f = j / float(n_)
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f))
    out.append(tuple(pts[-1][:3]))
    # sin puntos repetidos (el kit de caminos no admite tramos de longitud 0)
    lim = []
    for p_ in out:
        if lim and math.hypot(p_[0] - lim[-1][0], p_[1] - lim[-1][1]) < 0.05:
            continue
        lim.append(p_)
    return lim


def _malla(nombre, vs, fs, mat, root_col):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(vs, [], fs)
    if mat is not None:
        me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    root_col.objects.link(ob)
    return ob


def _caja(vs, fs, p0, p1, ancho, z_top, z_bot):
    """Prisma entre p0 y p1 (eje), de `ancho`, tapa en z_top y fondo en z_bot."""
    tx, ty = p1[0] - p0[0], p1[1] - p0[1]
    l_ = math.hypot(tx, ty) or 1.0
    nx_, ny_ = -ty / l_ * ancho / 2, tx / l_ * ancho / 2
    o = len(vs)
    for (x, y) in ((p0[0] + nx_, p0[1] + ny_), (p0[0] - nx_, p0[1] - ny_), (p1[0] - nx_, p1[1] - ny_), (p1[0] + nx_, p1[1] + ny_)):
        vs.append((x, y, z_top))
    for (x, y) in ((p0[0] + nx_, p0[1] + ny_), (p0[0] - nx_, p0[1] - ny_), (p1[0] - nx_, p1[1] - ny_), (p1[0] + nx_, p1[1] + ny_)):
        vs.append((x, y, z_bot))
    fs.append((o, o + 1, o + 2, o + 3))
    fs.append((o + 7, o + 6, o + 5, o + 4))
    for k in range(4):
        a, b = k, (k + 1) % 4
        fs.append((o + a, o + 4 + a, o + 4 + b, o + b))


def construir(ctx, ruta):
    import json
    d = json.load(open(ruta, encoding='utf-8'))
    clone, root_col, LIB, M, lib = ctx['clone'], ctx['root_col'], ctx['LIB'], ctx['M'], ctx['lib']
    log, z_terreno, rnd = ctx['log'], ctx['z_terreno'], ctx['rnd']
    zocalo_global, mat_simple = ctx['zocalo_global'], ctx['mat_simple']
    ck, ik, hk = M.get('caminos_kit'), M.get('italiano_kit'), M['casas_kit']
    m_terr = mat_simple('MAT_CAMINO_terraplen', (0.46, 0.42, 0.35, 1), 0.95)
    n_vallas = {'n': 0}

    def valla_cierre(px, py, z, rot, texto=None, ancho=6.0):
        """Valla cerrada (caminos_kit) en la boca de un enlace; los helpers del
        integrador se definen mas tarde en el fichero, asi que va aqui."""
        if ck is not None and hasattr(ck, 'build_valla_cierre'):
            v = ck.build_valla_cierre(LIB, ancho=ancho, seed=n_vallas['n'])
            vv = clone(v, (px, py, z), rot)
            vv.name = 'CAMINO_valla'
            n_vallas['n'] += 1

    def terraplen(pts3, ancho):
        """Relleno de piedra (talud ~1:1) bajo una rampa hasta el terreno."""
        vs, fs = [], []
        for k, (x, y, z) in enumerate(pts3):
            k2 = min(k + 1, len(pts3) - 1)
            k1 = max(k - 1, 0)
            tx, ty = pts3[k2][0] - pts3[k1][0], pts3[k2][1] - pts3[k1][1]
            l_ = math.hypot(tx, ty) or 1.0
            nx_, ny_ = -ty / l_, tx / l_
            for sg in (1.0, -1.0):
                xa, ya = x + sg * nx_ * ancho / 2, y + sg * ny_ * ancho / 2
                h = max(0.0, z - 0.05 - z_terreno(xa, ya))
                xb, yb = xa + sg * nx_ * (h * 0.9 + 0.4), ya + sg * ny_ * (h * 0.9 + 0.4)
                vs.append((xa, ya, z - 0.05))
                vs.append((xb, yb, z_terreno(xb, yb) - 0.8))
        for k in range(len(pts3) - 1):
            o = 4 * k
            fs.append((o, o + 4, o + 5, o + 1))
            fs.append((o + 2, o + 3, o + 7, o + 6))
            fs.append((o + 1, o + 5, o + 7, o + 3))
        if fs:
            ob = _malla('CAMINO_terraplen', vs, fs, m_terr, root_col)
            import bmesh as _bm
            bb = _bm.new()
            bb.from_mesh(ob.data)
            _bm.ops.recalc_face_normals(bb, faces=bb.faces)
            bb.to_mesh(ob.data)
            bb.free()
    m_adoq = mat_simple('MAT_CAMINO_adoquin_plaza', (0.55, 0.50, 0.46, 1), 0.9)
    m_esc = mat_simple('MAT_URB_escalera', (0.58, 0.55, 0.50, 1), 0.95)
    info = {'salidas': [], 'casas': 0, 'plazoletas': 0, 'calles': 0, 'muros': 0, 'escaleras': 0, 'rampas': 0, 'vallas': 0, 'plazas': 0,
            'ejes': [], 'huellas': [], 'fondos_saco': 0,
            'plazas_poly': [], 'fuentes': []}      # v1 integrador (N2 de D): el despeje no deja arboles en plazas ni fuentes
    cont = {'n': 0}

    m_calle = {'m': None}

    def _mat_asfalto_calle(ob):
        """v2 integrador (D2-08): las calles de servicio, enlaces y rampas del plan llevan un asfalto mas
        claro y gastado que el de la pista (copia de MAT_CAMINO_asfalto aclarada) y SIN linea discontinua:
        desde el puesto del piloto ya no se leen como un ramal de la pista."""
        if m_calle['m'] is None:
            base = bpy.data.materials.get('MAT_CAMINO_asfalto')
            if base is None:
                return
            m2 = base.copy()
            m2.name = 'MAT_CAMINO_asfalto_calle'
            if m2.node_tree is not None:
                for nd in m2.node_tree.nodes:
                    if nd.type == 'VALTORGB':
                        for el in nd.color_ramp.elements:
                            c = el.color
                            el.color = (min(1.0, c[0] * 1.9 + 0.03), min(1.0, c[1] * 1.85 + 0.025), min(1.0, c[2] * 1.7 + 0.02), c[3])
                    elif nd.type == 'BSDF_PRINCIPLED' and not nd.inputs['Base Color'].is_linked:
                        c = nd.inputs['Base Color'].default_value
                        nd.inputs['Base Color'].default_value = (min(1.0, c[0] * 1.9 + 0.03), min(1.0, c[1] * 1.85 + 0.025), min(1.0, c[2] * 1.7 + 0.02), 1.0)
            c = m2.diffuse_color
            m2.diffuse_color = (min(1.0, c[0] * 1.9 + 0.03), min(1.0, c[1] * 1.85 + 0.025), min(1.0, c[2] * 1.7 + 0.02), c[3])
            m_calle['m'] = m2
        if ob.type == 'MESH':
            for k_, m_ in enumerate(ob.data.materials):
                if m_ is not None and m_.name == 'MAT_CAMINO_asfalto':
                    ob.data.materials[k_] = m_calle['m']

    def camino3d(pts, ancho, tipo, nombre, **kw):
        dens = _dens3(pts)
        if len(dens) < 2:
            return None
        info['ejes'].append(([(p[0], p[1]) for p in dens], float(ancho)))   # para el despeje final del integrador
        cont['n'] += 1
        r = None
        if ck is not None and hasattr(ck, 'build_camino'):
            try:
                ob = ck.build_camino(LIB, dens, ancho=ancho, tipo=tipo, seed=cont['n'], **kw)
                if tipo == 'asfalto' and kw.get('lineas') is False:
                    _mat_asfalto_calle(ob)
                r = clone(ob, (0.0, 0.0, 0.0), 0.0)
            except Exception as e:
                log('urbanismo: build_camino fallo (%s)' % e)
        if r is None:
            vs, fs = [], []
            for k in range(len(dens) - 1):
                _caja(vs, fs, dens[k], dens[k + 1], ancho, dens[k][2], dens[k][2] - 0.3)
            r = _malla('CAMINO_' + nombre, vs, fs, m_adoq, root_col)
        r.name = 'CAMINO_' + nombre
        info['calles'] += 1
        return dens

    def muro3d(pts4, nombre):
        pts = [(p[0], p[1], p[2]) for p in pts4]
        if len(pts) < 2:
            return
        altos = sorted(max(0.0, p[3] - p[2]) for p in pts4)
        alto = max(0.6, min(7.5, altos[len(altos) // 2]))
        cont['n'] += 1
        if ck is not None and hasattr(ck, 'build_muro_contencion'):
            try:
                mw = ck.build_muro_contencion(LIB, pts, alto=alto, seed=cont['n'])
                mm = clone(mw, (0.0, 0.0, 0.0), 0.0)
                mm.name = 'CAMINO_' + nombre
                info['muros'] += 1
                return
            except Exception as e:
                log('urbanismo: muro fallo (%s)' % e)
        vs, fs = [], []
        for k in range(len(pts) - 1):
            _caja(vs, fs, pts[k], pts[k + 1], 0.5, pts[k][2] + alto, pts[k][2] - 0.4)
        _malla('CAMINO_' + nombre, vs, fs, m_esc, root_col)
        info['muros'] += 1

    def muro_variable(pts4, nombre, pretil=0.0, grosor=0.5):
        """Muro de piedra de altura VARIABLE por vertice: [(x, y, z_base, z_top)], con pretil
        opcional sobre z_top (rampas: la cara libre del relleno sube con la calzada)."""
        pts = [p for p in pts4 if len(p) >= 4]
        if len(pts) < 2:
            return
        vs, fs = [], []
        for k, p in enumerate(pts):
            a = pts[max(0, k - 1)]
            b = pts[min(len(pts) - 1, k + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            l_ = math.hypot(tx, ty) or 1.0
            nx_, ny_ = -ty / l_ * grosor / 2, tx / l_ * grosor / 2
            z0, z1 = p[2] - 0.6, p[3] + pretil
            vs += [(p[0] + nx_, p[1] + ny_, z0), (p[0] + nx_, p[1] + ny_, z1), (p[0] - nx_, p[1] - ny_, z1), (p[0] - nx_, p[1] - ny_, z0)]
        for k in range(len(pts) - 1):
            o, q = 4 * k, 4 * (k + 1)
            fs += [(o, q, q + 1, o + 1), (o + 1, q + 1, q + 2, o + 2), (o + 2, q + 2, q + 3, o + 3)]
        fs += [(0, 1, 2, 3), (4 * (len(pts) - 1) + 3, 4 * (len(pts) - 1) + 2, 4 * (len(pts) - 1) + 1, 4 * (len(pts) - 1))]
        _malla('CAMINO_' + nombre, vs, fs, m_esc, root_col)
        info['muros'] += 1

    def muro_rampa_sillares(pts4, eje, nombre, pretil=0.9, pieza=4.0):
        """v2 integrador (D2-07): muro de rampa de SILLARES (caminos_kit.build_muro_contencion, como los muros de
        terraza) en vez del prisma liso de muro_variable. El kit solo admite un alto constante: el muro se trocea
        en piezas de <= `pieza` m; en cada una la coronacion sigue la rampa (z_top + pretil en cada punto) y el
        alto es el maximo de la pieza, asi el pie queda siempre >= 0.6 m bajo z_base (como antes) y los escalones
        quedan enterrados. Relieve solo en la cara vista (la opuesta al eje de la rampa). Una malla por muro."""
        pts = [tuple(float(c) for c in p[:4]) for p in pts4 if len(p) >= 4]
        if len(pts) < 2 or ck is None or not hasattr(ck, 'build_muro_contencion'):
            return muro_variable(pts4, nombre, pretil=pretil)
        acc = [0.0]
        for k in range(1, len(pts)):
            acc.append(acc[-1] + math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]))
        tot = acc[-1]
        if tot < 1.0:
            return muro_variable(pts4, nombre, pretil=pretil)

        def interp(s):
            for k in range(1, len(pts)):
                if acc[k] >= s or k == len(pts) - 1:
                    f = 0.0 if acc[k] - acc[k - 1] < 1e-9 else max(0.0, min(1.0, (s - acc[k - 1]) / (acc[k] - acc[k - 1])))
                    a, b = pts[k - 1], pts[k]
                    return tuple(a[i] + (b[i] - a[i]) * f for i in range(4))
            return pts[-1]
        # cara vista: la que NO mira al eje de la rampa (relieve 'izq' = lado +n del sentido del muro)
        pa, pb = interp(max(0.0, tot / 2 - 0.5)), interp(min(tot, tot / 2 + 0.5))
        tx, ty = pb[0] - pa[0], pb[1] - pa[1]
        lt = math.hypot(tx, ty) or 1.0
        nx_, ny_ = -ty / lt, tx / lt
        pm = interp(tot / 2)
        ej = min(([float(q[0]), float(q[1])] for q in eje), key=lambda q: (q[0] - pm[0]) ** 2 + (q[1] - pm[1]) ** 2) if eje else None
        relieve = 'ambos'
        if ej is not None:
            relieve = 'der' if (ej[0] - pm[0]) * nx_ + (ej[1] - pm[1]) * ny_ > 0 else 'izq'
        CANTO = 0.35
        n_p = max(1, int(math.ceil(tot / pieza)))
        vs, fs, fm, mats = [], [], [], None
        for j in range(n_p):
            s0, s1 = tot * j / n_p, tot * (j + 1) / n_p
            ps = [interp(s0)] + [pts[k] for k in range(len(pts)) if s0 + 0.05 < acc[k] < s1 - 0.05] + [interp(s1)]
            tops = [p[3] + pretil for p in ps]
            alto = max(0.6, max(t - p[2] for t, p in zip(tops, ps)) + 0.6 - CANTO)
            p3 = [(p[0], p[1], t - alto) for p, t in zip(ps, tops)]
            cont['n'] += 1
            try:
                mw = ck.build_muro_contencion(LIB, p3, alto=alto, seed=cont['n'], relieve=relieve, canto=CANTO)
            except Exception as e:
                log('urbanismo: muro de rampa con sillares fallo (%s): muro liso' % e)
                return muro_variable(pts4, nombre, pretil=pretil)
            me = mw.data
            if mats is None:
                mats = list(me.materials)
            o = len(vs)
            mwm = mw.matrix_world
            vs.extend(tuple(mwm @ v.co) for v in me.vertices)
            for pl in me.polygons:
                fs.append(tuple(o + i for i in pl.vertices))
                fm.append(pl.material_index)
            bpy.data.objects.remove(mw, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me)
        ob = _malla('CAMINO_' + nombre, vs, fs, None, root_col)
        for m_ in (mats or []):
            ob.data.materials.append(m_)
        if fm:
            ob.data.polygons.foreach_set('material_index', fm)
            ob.data.update()
        info['muros'] += 1

    def _z_pie(p0, p1, an):
        """v3 integrador (N1 de s 668): cota mas baja del terreno bajo las 4 esquinas (y el centro) de una caja."""
        tx, ty = p1[0] - p0[0], p1[1] - p0[1]
        l_ = math.hypot(tx, ty) or 1.0
        nx_, ny_ = -ty / l_ * an / 2, tx / l_ * an / 2
        pts_ = [(p0[0] + nx_, p0[1] + ny_), (p0[0] - nx_, p0[1] - ny_), (p1[0] - nx_, p1[1] - ny_), (p1[0] + nx_, p1[1] + ny_),
                ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)]
        return min(z_terreno(a_, b_) for (a_, b_) in pts_)

    def escalera(e):
        """v3 integrador (N1 de s 668): escalera de FABRICA MACIZA: el fondo de cada peldano, del descansillo y de la
        pasarela baja hasta el terreno - 0.3 (antes un fondo fijo de 0.9 m: tramos colgando con 2.2-5.8 m de aire y su
        sombra en la hierba, CAMINO_escalera.003/.004/.002...)."""
        vs, fs = [], []
        an = float(e.get('ancho', 1.6))
        for tr in e.get('tramos', []):
            pts = tr['pts']
            for k in range(len(pts) - 1):
                a, b = pts[k], pts[k + 1]
                dz = b[2] - a[2]
                l_ = math.hypot(b[0] - a[0], b[1] - a[1])
                n_ = max(1, int(round(abs(dz) / 0.17)))
                for j in range(n_):
                    f0, f1 = j / float(n_), (j + 1) / float(n_)
                    p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
                    p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
                    z_t = a[2] + dz * f1 if dz >= 0 else a[2] + dz * f0
                    _caja(vs, fs, p0, p1, an, z_t, min(z_t - 0.9 - abs(dz) / n_, _z_pie(p0, p1, an) - 0.3))
        desc = e.get('descansillo')
        if desc and len(desc) >= 2:
            _caja(vs, fs, desc[0], desc[-1], an + 0.4, desc[0][2], min(desc[0][2] - 0.5, _z_pie(desc[0], desc[-1], an + 0.4) - 0.3))
        pas = e.get('pasarela')
        if pas and len(pas) >= 2:
            _caja(vs, fs, pas[0], pas[-1], an, pas[0][2], min(pas[0][2] - 0.35, _z_pie(pas[0], pas[-1], an) - 0.3))
        if fs:
            _malla('CAMINO_escalera', vs, fs, m_esc, root_col)
            info['escaleras'] += 1

    def poligono(nombre, poly, z, mat, grosor=0.25):
        """Losa poligonal con el ORIGEN en su centro y a su cota (los inspectores miden
        por el origen: en (0, 0, 0) la daban por flotante y la bajaban decenas de m)."""
        n_ = len(poly)
        cx_ = sum(p_[0] for p_ in poly) / n_
        cy_ = sum(p_[1] for p_ in poly) / n_
        if grosor is None:
            # v2 integrador (D2-12): canto hasta el terreno mas bajo del borde (vertices y puntos medios) + 0.1, como
            # los fondos de saco: con 0.3 fijo la losa quedaba con aire bajo una esquina en ladera
            bordes = [p_[:2] for p_ in poly] + [((poly[k][0] + poly[(k + 1) % n_][0]) / 2.0, (poly[k][1] + poly[(k + 1) % n_][1]) / 2.0)
                                                for k in range(n_)]
            grosor = max(0.3, z - min(z_terreno(a_, b_) for (a_, b_) in bordes) + 0.1)
        vs = [(x - cx_, y - cy_, 0.0) for (x, y) in poly] + [(x - cx_, y - cy_, -grosor) for (x, y) in poly]
        fs = [tuple(range(n_)), tuple(range(2 * n_ - 1, n_ - 1, -1))]
        for k in range(n_):
            fs.append((k, n_ + k, n_ + (k + 1) % n_, (k + 1) % n_))
        ob = _malla(nombre, vs, fs, mat, root_col)
        ob.location = (cx_, cy_, z)
        return ob

    def _dist_seg(px, py, a, b):
        vx, vy = b[0] - a[0], b[1] - a[1]
        l2 = vx * vx + vy * vy
        f = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, ((px - a[0]) * vx + (py - a[1]) * vy) / l2))
        return math.hypot(px - a[0] - vx * f, py - a[1] - vy * f)

    def valla_enlace(v, enlaces):
        """Valla CERRADA cruzando el enlace a 3.5 m del borde del asfalto (el punto del
        plan esta en la boca, medio dentro de la calzada) y perpendicular a el."""
        en = next((e for e in enlaces if e['id'] == v.get('enlace')), None)
        if en is None or len(en['pts']) < 2:
            valla_cierre(float(v['x']), float(v['y']), float(v['z']), float(v['rot_z']))
            return
        pts = _dens3(en['pts'], 0.5)
        # extremo de la boca = el mas cercano al punto de la valla del plan
        if math.hypot(pts[0][0] - v['x'], pts[0][1] - v['y']) > math.hypot(pts[-1][0] - v['x'], pts[-1][1] - v['y']):
            pts = pts[::-1]
        # el enlace es casi paralelo a la pista (va de la calle de servicio, a 1.5-6 m,
        # al borde del asfalto): la valla va donde el eje ya esta a >= 2.6 m del asfalto
        # (o al 80 % del enlace), con 4.6 m de ancho: sus extremos quedan sobre el bordillo
        k = int(0.8 * (len(pts) - 1))
        if dist_pista is not None:
            for j in range(len(pts)):
                if dist_pista(pts[j][0], pts[j][1]) >= 2.6:
                    k = j
                    break
        k = max(1, min(k, len(pts) - 2))
        p, q = pts[k], pts[k + 1]
        rot = math.atan2(q[1] - p[1], q[0] - p[0]) - math.pi / 2     # +Y local = a lo largo del enlace
        valla_cierre(p[0], p[1], p[2], rot, ancho=4.6)

    muros_pend, discos_corte = [], []

    def _cortar_muro(pts4, discos, margen=0.5):
        """v3 integrador (N2): trozos de un muro del plan [(x, y, z_base, z_top)] fuera de los discos (r + margen):
        densificado a 1 m, sin los puntos de dentro; trozos de < 3 m fuera. Sin corte devuelve [pts4] tal cual."""
        pts = [tuple(float(c) for c in p[:4]) for p in pts4 if len(p) >= 4]
        if not discos or len(pts) < 2:
            return [pts4]
        cerca = [d_ for d_ in discos if any(math.hypot(p[0] - d_[0], p[1] - d_[1]) < d_[2] + 40.0 for p in pts)]
        if not cerca:
            return [pts4]
        den = []
        for k in range(len(pts) - 1):
            a_, b_ = pts[k], pts[k + 1]
            n_ = max(1, int(math.ceil(math.hypot(b_[0] - a_[0], b_[1] - a_[1]) / 1.0)))
            for j in range(n_):
                f = j / float(n_)
                den.append(tuple(a_[i] + (b_[i] - a_[i]) * f for i in range(4)))
        den.append(pts[-1])
        trozos, act = [], []
        for p in den:
            if any(math.hypot(p[0] - cx_, p[1] - cy_) < r_ + margen for (cx_, cy_, r_) in cerca):
                if len(act) >= 2:
                    trozos.append(act)
                act = []
                continue
            act.append(p)
        if len(act) >= 2:
            trozos.append(act)
        if len(trozos) == 1 and len(trozos[0]) == len(den):
            return [pts4]
        return [t_ for t_ in trozos if math.hypot(t_[-1][0] - t_[0][0], t_[-1][1] - t_[0][1]) >= 3.0]

    variantes = {}

    def casa_var(plantas, ancho, fondo, seed):
        an = round(ancho * 2) / 2.0
        fo = round(fondo * 2) / 2.0
        key = (int(plantas), an, fo, int(seed) % 3)      # 3 colores/detalles por tamano
        if key not in variantes:
            variantes[key] = hk.build_casa(LIB, plantas=int(plantas), ancho=an, fondo=fo, seed=int(seed))
        return variantes[key]

    arboles = [t_ for t_ in ('adelfa', 'olivo', 'cipres', 'adelfa_v0', 'olivo_v0', 'palmera2') if t_ in lib]
    n_plazoleta = 0
    dist_pista = ctx.get('dist_pista')

    def _d_poly(px, py, poly):
        """distancia de un punto a un poligono (0 si esta dentro)."""
        dentro = False
        n_ = len(poly)
        for k in range(n_):
            (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % n_]
            if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / ((y2 - y1) or 1e-9):
                dentro = not dentro
        if dentro:
            return 0.0
        return min(_dist_seg(px, py, poly[k], poly[(k + 1) % n_]) for k in range(n_))

    def fondos_de_saco(dat):
        """NADA SIN DESTINO: cada extremo de calle/travesia que no llega a otra calle,
        escalera, casa, plaza ni a la pista acaba en una PLAZOLETA de giro (fondo de
        saco) con fuente o cipreses, sin pisar casas y asentada en el terreno."""
        ejes = info['ejes']
        destinos_poly = list(info['huellas'])
        for sec in dat['sectores']:
            for p_ in sec.get('plazas', []):
                if p_.get('poligono'):
                    destinos_poly.append([(float(a), float(b)) for (a, b) in p_['poligono']])
        n_f = 0
        fuente_lib = {'ob': None, 'r': 9.0}
        finales = []          # extremos ya resueltos con plazoleta (para unir pares)
        # v3 integrador (N2 de (-552, 595)): los muros del plan no pueden entrar en el disco (CAMINO_muro.055 cruzaba
        # CALLE_plaza_fondo.003 y .039/.041 la .002): primero se buscan radios sin muro a < r + 0.4; si no cabe
        # ninguno, el disco se queda y el muro se CORTA en su borde (muros_pend se construyen despues)
        segs_muro = []
        for sec_ in dat['sectores']:
            for m_ in sec_.get('muros', []):
                pm_ = m_.get('pts') or []
                segs_muro += [(pm_[k][:2], pm_[k + 1][:2]) for k in range(len(pm_) - 1)]

        def _muro_cerca(cx_, cy_, r_):
            return any(_dist_seg(cx_, cy_, a_, b_) < r_ + 0.4 for (a_, b_) in segs_muro
                       if abs(a_[0] - cx_) < r_ + 60.0 and abs(a_[1] - cy_) < r_ + 60.0)
        for i_e, (pts, ancho) in enumerate(list(ejes)):
            if len(pts) < 2 or ancho < 3.0:          # las escaleras no necesitan plazoleta
                continue
            for (pe, pa) in ((pts[0], pts[1]), (pts[-1], pts[-2])):
                x, y = pe
                ok = dist_pista is not None and dist_pista(x, y) < 6.0
                if not ok:
                    for j, (q, an_q) in enumerate(ejes):
                        if j == i_e:
                            continue
                        if any(_dist_seg(x, y, q[k], q[k + 1]) < 6.0 + an_q / 2 for k in range(len(q) - 1)):
                            ok = True
                            break
                if not ok:
                    ok = any(_d_poly(x, y, pol) < 6.0 for pol in destinos_poly)
                if ok:
                    continue
                dx, dy = pe[0] - pa[0], pe[1] - pa[1]
                l_ = math.hypot(dx, dy) or 1.0
                dx, dy = dx / l_, dy / l_
                z0 = z_terreno(x, y)
                hecho = False
                # dos calles que mueren cerca (esquina interior de una curva cerrada): se unen
                union = None
                for (q_e, q_z) in finales:
                    dq = math.hypot(q_e[0] - x, q_e[1] - y)
                    if 0.5 < dq < 26.0 and abs(q_z - z_terreno(x, y)) / dq < 0.15:
                        union = (q_e, q_z)
                        break
                if union is not None:
                    camino3d([(x, y, z_terreno(x, y) + 0.05), (union[0][0], union[0][1], union[1] + 0.05)], ancho, 'adoquin', 'union')
                    info['sin_destino'] = [sd for sd in info.get('sin_destino', [])
                                           if math.hypot(sd[0] - union[0][0], sd[1] - union[0][1]) > 0.5]
                    n_f += 1
                    continue
                for (r, sin_muro) in ((6.5, True), (5.5, True), (4.5, True), (6.5, False), (5.5, False), (4.5, False)):
                    cx_, cy_ = x + dx * (r - 1.0), y + dy * (r - 1.0)
                    if any(_d_poly(cx_, cy_, pol) < r + 0.8 for pol in info['huellas']):
                        continue
                    if dist_pista is not None and dist_pista(cx_, cy_) < r + 2.0:
                        continue
                    if sin_muro and _muro_cerca(cx_, cy_, r):
                        continue
                    circ = [(cx_ + r * math.cos(2 * math.pi * k / 18), cy_ + r * math.sin(2 * math.pi * k / 18)) for k in range(18)]
                    zt = [z_terreno(a, b) for (a, b) in circ]
                    if max(zt) > z0 + 0.6:                  # se enterraria: la ladera sube ahi
                        continue
                    if z0 - min(zt) > 1.2:                  # v3 (C-04): seria un tambor (canto > 1.8 m): radio menor
                        continue
                    grosor = max(0.3, z0 - min(zt) + 0.6)
                    poligono('CALLE_plaza_fondo', circ, z0 + 0.08, m_adoq, grosor)
                    if not sin_muro:
                        discos_corte.append((cx_, cy_, r))
                    info['plazas_poly'].append([(float(a), float(b)) for (a, b) in circ])
                    if fuente_lib['ob'] is None and ik is not None and hasattr(ik, 'build_fuente'):
                        fuente_lib['ob'] = ik.build_fuente(LIB, seed=20)
                        fuente_lib['r'] = max(max(abs(c[0]), abs(c[1])) for h in [fuente_lib['ob']] + list(fuente_lib['ob'].children_recursive)
                                              if h.type == 'MESH' for c in h.bound_box)
                    # la fuente solo si cabe entera a >= 0.8 m de la calle que llega
                    # (la caja de la fuente es cuadrada: sus esquinas llegan a 1.42 r)
                    if fuente_lib['ob'] is not None and (r - 0.2) - 1.42 * fuente_lib['r'] >= 1.4:
                        f_ = clone(fuente_lib['ob'], (cx_ + dx * 1.2, cy_ + dy * 1.2, z0 + 0.1), 0.0)
                        f_.name = 'ITAL_fuente'
                        info['fuentes'].append((cx_ + dx * 1.2, cy_ + dy * 1.2))
                    elif 'cipres' in lib:
                        for sg in (1.0, -1.0):
                            c_ = clone(lib['cipres'], (cx_ + dx * (r - 1.2) - dy * sg * 2.0, cy_ + dy * (r - 1.2) + dx * sg * 2.0, z0 + 0.08), rnd.uniform(0, 6.28))
                            c_.name = 'VEG_plazoleta'
                    destinos_poly.append(circ)
                    finales.append(((x, y), z0))
                    n_f += 1
                    hecho = True
                    break
                if not hecho:
                    finales.append(((x, y), z_terreno(x, y)))
                    info.setdefault('sin_destino', []).append((x, y, z_terreno(x, y), dx, dy))
                    log('urbanismo: extremo sin destino en (%.0f, %.0f) y sin sitio para plazoleta' % (x, y))
        info['fondos_saco'] = n_f
        log('urbanismo: %d plazoletas de fondo de saco' % n_f)
    for sec in d['sectores']:
        # v2 integrador (D2-08): calles de servicio, enlaces y rampas en asfalto de calle (mas claro) y sin la
        # linea discontinua de la pista (pegadas a ella se leian como un segundo carril o un desvio)
        for c in sec.get('calles', []):
            if c.get('tipo') == 'servicio':
                camino3d(c['pts'], float(c.get('ancho', 4.5)), 'asfalto', 'calle', lineas=False)
            else:
                camino3d(c['pts'], float(c.get('ancho', 4.5)), 'adoquin', 'calle')
        for e in sec.get('enlaces', []):
            camino3d(e['pts'], float(e.get('ancho', 4.5)), 'asfalto', 'enlace', lineas=False)
        for v in sec.get('vallas', []):
            valla_enlace(v, sec.get('enlaces', []))
            info['vallas'] += 1
        for t in sec.get('travesias', []):
            camino3d(t['pts'], float(t.get('ancho', 4.5)), 'adoquin', 'travesia')
        for r in sec.get('rampas', []):
            # RONDA 15: la rampa es un RELLENO entre muros verticales (los del plan, de altura
            # variable z_base=terreno .. z_top=calzada) con pretil de 0.9 m; nada de talud:
            # invadia la casa de delante (solares de 4 m de fondo junto a las rampas)
            camino3d(r['pts'], float(r.get('ancho_calzada', 4.5)), 'asfalto', 'rampa', lineas=False)
            for m in r.get('muros_rampa', []):
                muro_rampa_sillares(m['pts'], r['pts'], 'muro_rampa', pretil=0.9)
            info['rampas'] += 1
        for e in sec.get('escaleras', []):
            escalera(e)
            for tr in e.get('tramos', []):
                info['ejes'].append(([(q[0], q[1]) for q in tr['pts']], float(e.get('ancho', 1.6))))
        for m in sec.get('muros', []):
            muros_pend.append(m['pts'])           # v3 (N2): se construyen tras los fondos de saco (corte en su disco)
        for s in sec.get('solares', []):
            px, py, zs = float(s['px']), float(s['py']), float(s['z_suelo'])
            if s.get('tipo') == 'casa':
                var = casa_var(s.get('plantas', 3), s['ancho'], s['fondo'], s.get('seed', 0))
                casa = clone(var, (px, py, zs + 0.02), float(s['rot_z']))
                casa.name = 'CASAS_casa'
                if s.get('poligono'):
                    info['huellas'].append([(float(a), float(b)) for (a, b) in s['poligono']])
                te = s.get('terreno_esquinas') or [0.0]
                if min(te) < -0.3:
                    zocalo_global(casa, zs + min(te) - 1.0)
                info['casas'] += 1
            else:
                poly = s.get('poligono') or []
                if len(poly) >= 3:
                    poligono('CALLE_plazoleta', poly, zs + 0.06, m_adoq, None)
                    info['plazas_poly'].append([(float(a), float(b)) for (a, b) in poly])
                cx_, cy_ = float(s['cx']), float(s['cy'])
                if arboles:
                    for j in range(2):
                        t_ = arboles[(n_plazoleta * 2 + j) % len(arboles)]
                        ob = clone(lib[t_], (cx_ + (j - 0.5) * 3.2 * float(s['fy']), cy_ - (j - 0.5) * 3.2 * float(s['fx']), zs + 0.08), rnd.uniform(0, 6.28))
                        ob.name = 'VEG_plazoleta'
                if ik is not None and n_plazoleta % 2 == 0 and hasattr(ik, 'build_pergola'):
                    try:
                        pg = clone(ik.build_pergola(LIB, largo=min(6.0, float(s['ancho']) - 1.5), seed=n_plazoleta), (cx_, cy_, zs + 0.05), float(s['rot_z']))
                        pg.name = 'ITAL_pergola'
                    except Exception as e:
                        log('urbanismo: pergola fallo (%s)' % e)
                n_plazoleta += 1
                info['plazoletas'] += 1
        for p in sec.get('plazas', []):
            poly = p.get('poligono') or []
            zp = float(p['z'])
            if len(poly) >= 3:
                poligono('CALLE_plaza', poly, zp + 0.06, m_adoq, None)
                info['plazas_poly'].append([(float(a), float(b)) for (a, b) in poly])
            fu = p.get('fuente')
            if fu and ik is not None and hasattr(ik, 'build_fuente'):
                f_ = clone(ik.build_fuente(LIB, seed=info['plazas']), (float(fu[0]), float(fu[1]), zp + 0.1), 0.0)
                f_.name = 'ITAL_fuente'
                info['fuentes'].append((float(fu[0]), float(fu[1])))
            # (sin campanile en las plazas: caia sobre el muro de la terraza; el campanile del
            # pueblo va en la plaza del ayuntamiento, zona_pueblo_urbanismo)
            info['plazas'] += 1
        info['salidas'] += [dict(s_) for s_ in sec.get('salidas', [])]
        log('urbanismo %s: %d casas' % (sec['id'], sum(1 for s_ in sec.get('solares', []) if s_.get('tipo') == 'casa')))
    fondos_de_saco(d)
    # v3 integrador (N2): las salidas de la ultima terraza y los extremos sin destino acaban en una PLAZUELA de edicola
    # (integrar_escena.zona_edicolas, r 4.5 a 3.7 m del punto) o en el arranque de un sendero: el extremo de un muro del
    # plan entraba en ese disco (pueblo_subida_mar_muro1_0 junto a la salida0, casino_ladera_muro0_1 junto a la salida1)
    discos_ext = []
    for sec in d['sectores']:
        for s_ in sec.get('salidas', []):
            try:
                discos_ext.append((float(s_['x']) + float(s_['dx']) * 3.7, float(s_['y']) + float(s_['dy']) * 3.7, 4.5))
            except Exception:
                pass
    for (x_, y_, z_, dx_, dy_) in info.get('sin_destino', []):
        discos_ext.append((x_ + dx_ * 3.7, y_ + dy_ * 3.7, 4.5))
    n_cortes = 0
    for pts4 in muros_pend:
        trozos = _cortar_muro(pts4, discos_corte + discos_ext)
        n_cortes += 1 if (len(trozos) != 1 or trozos[0] is not pts4) else 0
        for t_ in trozos:
            muro3d(t_, 'muro')
    log('urbanismo: %d muros del plan cortados en el borde de %d plazoletas sin sitio libre y %d plazuelas/salidas'
        % (n_cortes, len(discos_corte), len(discos_ext)))
    log('urbanismo: %d casas (%d variantes), %d plazoletas, %d plazas, %d calles/tramos, %d muros, %d escaleras, %d rampas, %d vallas, %d salidas'
        % (info['casas'], len(variantes), info['plazoletas'], info['plazas'], info['calles'], info['muros'], info['escaleras'], info['rampas'], info['vallas'], len(info['salidas'])))
    return info
