# -*- coding: utf-8 -*-
"""ensayo_f_pueblo.py - mini-pista F "pueblo junto al puerto" para validar la PALETA v2 con Pure en el PC del amigo
(decision del usuario, DECISIONES_USUARIO.md "Paleta v2": "exportar esa zona a Assetto Corsa para comprobarla con Pure").

    python 04_export/ensayo_f_pueblo.py --export <escena de export .blend> --geom <geometria.json> --out <carpeta>
                                        [--zip <ruta.zip>] [--sin-zip]
      (python del sistema; lanza Blender SOLO por la cola 03_blender/_rev/blender_cola.sh, dos veces: escena + writer)

Que hace:
  1. (Blender, este mismo fichero con --escena) abre la escena YA EXPORTADA (exportar_ac.py + cierre_ac: prefijos
     fisicos, muros de cierre de la pista) y se queda con la ZONA del pueblo de s 650-1000: rectangulo ZONA (x -820..-300,
     y 380..720 en Blender), elegido con las camaras 50_piloto_s800, 40_pueblo_travesia y 06_pueblo_calle (las tres
     estan dentro y miran al pueblo, hacia el NE; ver CAMARAS_F) y con el tramo de pista s ~605-1110 que lo cruza.
       * objetos con el centro dentro de la zona: enteros; mallas grandes que la cruzan (pista, pianos, arcenes, muros de
         cierre, caminos largos, marcas): solo sus caras con el centro dentro; el resto se borra;
       * se conservan ENTEROS el terreno (1GRASS_terreno, para que el fondo de montes no sea un vacio y la bbox fisica
         sea la del circuito: kn5_check 6), el mar (AGUA*) y el horizonte (HORIZ_);
       * el puerto (pantalanes a 250-300 m al S de la recta de meta, a ~500 m del pueblo) NO entra: no se ve desde
         50/40/06 (miran al NE) y meterlo duplicaria la zona y anadiria el McLaren y el tunel (113 k tris) sin fachadas;
         la costa (a 84-220 m del pueblo, al O) si entra en la zona;
       * muro de cierre INVISIBLE (1WALL_cierre_f, 60 m de alto, dos caras) en el borde de la zona: el coche no sale de
         ella ni del tramo de pista; AC_START_0..19 (parrilla en s 688-760), AC_PIT_0..19 (s 786-900, por el eje),
         AC_TIME_0 (s 1000) / AC_TIME_1 (s 860) y AC_HOTLAP_START_0 (s 650), con la orientacion de exportar_ac
         (rot = rumbo + 90 grados, a 1 m sobre el asfalto) y la marca porto_corsa_export_v = 2.
  2. kn5_writer_opt.py (el MISMO writer y color_ac que el circuito: terreno, paleta, P2...) -> ensayo_f_pueblo.kn5.
  3. carpeta content/tracks/ensayo_f_pueblo/ (kn5, data/surfaces.ini y map.ini, ui/ui_track.json, map.png, extension/
     ext_config.ini como el circuito), LEEME.txt de 6 lineas para el amigo, kn5_check (8 + la 9 de shaders) y zip aparte
     ensayo_f_pueblo.zip (no va dentro de porto_corsa_mod.zip: es una pista de laboratorio que se instala, se prueba y se
     borra, y puede mandarse ANTES que el zip v1.2).
"""
import json
import math
import os
import subprocess
import sys
import time
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(AQUI)
NOMBRE = 'ensayo_f_pueblo'
ZONA = (-820.0, -300.0, 380.0, 720.0)            # x0, x1, y0, y1 (Blender, m)
CAMARAS_F = {   # loc/tgt/lens congelados (renders/ab/paleta_v2/camaras.json y f1_r4/camaras_paleta.json)
    '50_piloto_s800': {'loc': [-585.142, 514.785, 40.389], 'tgt': [-519.894, 559.377, 40.559], 'lens': 24.0},
    '40_pueblo_travesia': {'loc': [-549.391, 532.719, 39.789], 'tgt': [-479.286, 565.067, 52.89], 'lens': 26.0},
    '06_pueblo_calle': {'loc': [-602.726, 505.281, 53.621], 'tgt': [-422.726, 587.386, 56.372], 'lens': 28.0},
}
ENTEROS = ('1GRASS_terreno', 'AGUA', 'HORIZ_')    # se conservan enteros
GRANDE_M = 250.0                                  # mallas con bbox > 250 m: se recortan por caras
S_PARRILLA, S_PITS, S_T0, S_T1, S_HOTLAP = 760.0, 900.0, 1000.0, 860.0, 650.0
ALTURA_AC = 1.0
CIERRE_H = (-25.0, 60.0)
LEEME = """PORTO CORSA - pista de prueba F (pueblo): solo sirve para mirar los COLORES de las casas en tu Assetto Corsa.
1. Instala ensayo_f_pueblo.zip como el circuito (arrastralo a Content Manager) y entra en Practice en la pista "Ensayo F - pueblo".
2. En Content Manager pon el filtro Pure (CSP) y la hora entre las 17:00 y las 18:00, cielo despejado.
3. Sales en la recta del pueblo: conduce despacio por el tramo (hay un muro invisible al final de la zona).
4. Haz 4-6 fotos (F8) desde el coche mirando a las FACHADAS de las casas, de cerca y de lejos, y una del monte de detras.
5. Mandanos las fotos y dinos tu version de CSP y si algo se ve negro, blanco o raro (tambien el suelo junto a la carretera).
"""


# ============================================================================= parte Blender (escena F)
def _en_zona(x, y):
    return ZONA[0] <= x <= ZONA[1] and ZONA[2] <= y <= ZONA[3]


def construir_escena(blend_in, geom_path, blend_out, log=print):
    import bmesh
    import bpy
    import numpy as np
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=blend_in)
    sc = bpy.context.scene
    G = json.load(open(geom_path, encoding='utf-8'))
    S, N, paso, L = G['muestras'], G['n'], G['paso_m'], G['largo_m']
    st = {'enteros': [], 'recortados': {}, 'dentro': 0, 'borrados': 0, 'tris_dentro': 0}
    for ob in list(bpy.data.objects):
        if ob.type != 'MESH':
            if ob.type in ('CAMERA',):
                bpy.data.objects.remove(ob, do_unlink=True)
            continue
        if ob.name.startswith('AC_'):
            bpy.data.objects.remove(ob, do_unlink=True)
            st['borrados'] += 1
            continue
        if ob.name.startswith(ENTEROS):
            st['enteros'].append(ob.name)
            continue
        cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        x0, x1 = min(c.x for c in cs), max(c.x for c in cs)
        y0, y1 = min(c.y for c in cs), max(c.y for c in cs)
        cruza = not (x1 < ZONA[0] or x0 > ZONA[1] or y1 < ZONA[2] or y0 > ZONA[3])
        grande = (x1 - x0) > GRANDE_M or (y1 - y0) > GRANDE_M
        if not cruza or (not grande and not _en_zona((x0 + x1) / 2, (y0 + y1) / 2)):
            bpy.data.objects.remove(ob, do_unlink=True)
            st['borrados'] += 1
            continue
        if grande:                       # solo las caras con el centro dentro de la zona
            if ob.data.users > 1:
                ob.data = ob.data.copy()
            me = ob.data
            n = len(me.polygons)
            cen = np.empty(n * 3, np.float32)
            me.polygons.foreach_get('center', cen)
            M = np.array(ob.matrix_world, np.float64)
            P = cen.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
            fuera = ~((P[:, 0] >= ZONA[0]) & (P[:, 0] <= ZONA[1]) & (P[:, 1] >= ZONA[2]) & (P[:, 1] <= ZONA[3]))
            if fuera.all():
                bpy.data.objects.remove(ob, do_unlink=True)
                st['borrados'] += 1
                continue
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(fuera)[0]], context='FACES')
            bm.to_mesh(me)
            bm.free()
            st['recortados'][ob.name] = [int(n), int((~fuera).sum())]
        st['dentro'] += 1
        st['tris_dentro'] += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    # objetos logicos (formulas de exportar_ac.py)
    def frame(s_m):
        return S[int(round((s_m % L) / paso)) % N]

    def heading(s_m):
        p = frame(s_m)
        return math.atan2(-p['nx'], p['ny'])

    def mini(name, loc, rot_z):
        me = bpy.data.meshes.new(name)
        d = 0.18
        v = [(-d, -d, 0), (d, -d, 0), (d, d, 0), (-d, d, 0), (-d, -d, 2 * d), (d, -d, 2 * d), (d, d, 2 * d), (-d, d, 2 * d)]
        f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)]
        me.from_pydata(v, [], f)
        o = bpy.data.objects.new(name, me)
        o.location = Vector(loc)
        o.rotation_euler = (0, 0, rot_z)
        sc.collection.objects.link(o)
        return o
    ac = {}
    for i in range(20):
        s_m = S_PARRILLA - 8.0 * (i // 2)
        lado = 2.3 if i % 2 == 0 else -2.3
        p = frame(s_m)
        o = mini('AC_START_%d' % i, (p['x'] + p['nx'] * lado, p['y'] + p['ny'] * lado, p['z'] + ALTURA_AC),
                 heading(s_m) + math.pi / 2)
        ac[o.name] = round(s_m, 1)
    for j in range(20):
        s_m = S_PITS - 6.0 * j
        p = frame(s_m)
        o = mini('AC_PIT_%d' % j, (p['x'], p['y'], p['z'] + ALTURA_AC), heading(s_m) + math.pi / 2)
        ac[o.name] = round(s_m, 1)
    for nombre, s_m in (('AC_TIME_0', S_T0), ('AC_TIME_1', S_T1)):
        p = frame(s_m)
        h = p['w'] / 2 - 0.3
        for suf, sg in (('_L', 1), ('_R', -1)):
            mini(nombre + suf, (p['x'] + sg * p['nx'] * h, p['y'] + sg * p['ny'] * h, p['z'] + 0.5), heading(s_m) + math.pi / 2)
    p = frame(S_HOTLAP)
    mini('AC_HOTLAP_START_0', (p['x'], p['y'], p['z'] + ALTURA_AC), heading(S_HOTLAP) + math.pi / 2)
    fuera_zona = sorted(k for k in ac if not _en_zona(*[frame(ac[k])[c] for c in ('x', 'y')]))
    # muro de cierre invisible: 4 paredes de dos caras en el borde de la zona
    x0, x1, y0, y1 = ZONA
    z0, z1 = CIERRE_H
    vs, fs = [], []
    for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        k = len(vs)
        vs += [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]
        fs += [(k, k + 1, k + 2, k + 3), (k + 3, k + 2, k + 1, k)]
    me = bpy.data.meshes.new('1WALL_cierre_f')
    me.from_pydata(vs, [], fs)
    m_inv = bpy.data.materials.get('MAT_cierre_invisible') or bpy.data.materials.new('MAT_cierre_invisible')
    me.materials.append(m_inv)
    sc.collection.objects.link(bpy.data.objects.new('1WALL_cierre_f', me))
    sc['porto_corsa_export_v'] = 2
    sc['ensayo_f'] = json.dumps({'zona': ZONA, 'ac': ac})
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    st.update(ac_fuera_de_zona=fuera_zona, mallas=sum(1 for o in bpy.data.objects if o.type == 'MESH'))
    log('ESCENA_F %s' % json.dumps(st, ensure_ascii=False))
    return st


# ============================================================================= parte python del sistema
def _cola(args, log_path, env=None):
    cmd = ['bash', os.path.join(BASE, '03_blender', '_rev', 'blender_cola.sh')] + args
    e = dict(os.environ)
    e.update(env or {})
    with open(log_path, 'w', encoding='utf-8') as fh:
        r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=e, cwd=BASE)
    return r.returncode


def carpeta_pista(out, kn5, geom_path):
    import shutil
    import numpy as np
    from PIL import Image, ImageDraw
    sys.path.insert(0, AQUI)
    import color_ac
    d = os.path.join(out, 'content', 'tracks', NOMBRE)
    for sub in ('data', 'ui'):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    shutil.copy2(kn5, os.path.join(d, NOMBRE + '.kn5'))
    # surfaces.ini: la del circuito (empaquetar.py), con PIT/DIRT/SAND aunque aqui no se usen
    src = open(os.path.join(AQUI, 'empaquetar.py'), encoding='utf-8').read()
    surf = src.split('SURFACES = """', 1)[1].split('"""', 1)[0]
    with open(os.path.join(d, 'data', 'surfaces.ini'), 'w', encoding='ascii') as fh:
        fh.write(surf)
    G = json.load(open(geom_path, encoding='utf-8'))
    S = G['muestras']
    pts = [(p['x'], -p['y']) for p in S if _en_zona(p['x'], p['y'])]
    x0, x1, y0, y1 = ZONA
    margen, px = 20.0, 1024
    ancho, alto = (x1 - x0) + 2 * margen, (y1 - y0) + 2 * margen
    esc = ancho / px
    ph = int(alto / esc)
    xoff, zoff = -x0 + margen, y1 + margen          # z_AC = -y_blender: z va de -y1 a -y0
    im = Image.new('RGBA', (px, ph), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.line([((x + xoff) / esc, (z + zoff) / esc) for x, z in pts], fill=(255, 255, 255, 255), width=7)
    im.save(os.path.join(d, 'map.png'))
    with open(os.path.join(d, 'data', 'map.ini'), 'w') as fh:
        fh.write('[PARAMETERS]\nWIDTH=%d\nHEIGHT=%d\nX_OFFSET=%.3f\nZ_OFFSET=%.3f\nMARGIN=20\nSCALE_FACTOR=%.5f\n'
                 'MAX_SIZE=1600\nDRAWING_SIZE=10\n' % (px, ph, xoff, zoff, esc))
    im.resize((px // 2, ph // 2)).save(os.path.join(d, 'ui', 'outline.png'))
    largo = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    ui = {'name': 'Ensayo F - pueblo (Porto Corsa)',
          'description': 'Pista de PRUEBA de Porto Corsa: solo el pueblo de la subida (s 650-1000) y su tramo de pista, '
                         'para comprobar los colores de las fachadas con Pure a las 17-18 h. Muro invisible al borde.',
          'tags': ['ensayo', 'test', 'porto corsa'], 'geotags': [], 'country': 'Italy', 'city': 'Porto Corsa',
          'length': '%d' % round(largo), 'width': '11', 'pitboxes': '20', 'run': 'anticlockwise',
          'author': 'Arnau & Claude', 'version': '1.2-F', 'year': 2026}
    with open(os.path.join(d, 'ui', 'ui_track.json'), 'w', encoding='utf-8') as fh:
        json.dump(ui, fh, ensure_ascii=False, indent=2)
    color_ac.copiar_ext_config(d)
    with open(os.path.join(out, 'LEEME.txt'), 'w', encoding='utf-8') as fh:
        fh.write(LEEME)
    return d, round(largo)


def main(argv):
    if '--escena' in argv:              # dentro de Blender
        a = argv[argv.index('--') + 1:]
        construir_escena(a[0], a[1], a[2])
        return 0
    arg = {'--export': None, '--geom': None, '--out': None, '--zip': None}
    for k in list(arg):
        if k in argv:
            arg[k] = argv[argv.index(k) + 1]
    out = os.path.abspath(arg['--out'])
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    blend_f = os.path.join(out, 'escena_f.blend')
    rc = _cola(['--python', os.path.abspath(__file__), '--', arg['--export'], arg['--geom'], blend_f, '--escena'],
               os.path.join(out, '1_escena.txt'))
    log1 = open(os.path.join(out, '1_escena.txt'), encoding='utf-8', errors='replace').read()
    linea = [ln for ln in log1.splitlines() if ln.startswith('ESCENA_F ')]
    if rc != 0 or not linea:
        print('FALLO escena F (ver %s)' % os.path.join(out, '1_escena.txt'))
        return 1
    st = json.loads(linea[-1][len('ESCENA_F '):])
    print('escena F: %d mallas, %d dentro de la zona (%d tris), %d borradas, recortadas %s, enteras %s' % (
        st['mallas'], st['dentro'], st['tris_dentro'], st['borrados'], {k: v[1] for k, v in st['recortados'].items()},
        st['enteros']))
    kn5 = os.path.join(out, NOMBRE + '.kn5')
    rc = _cola(['--python', os.path.join(AQUI, 'kn5_writer_opt.py')], os.path.join(out, '2_kn5.txt'),
               env={'BLEND': blend_f, 'KN5': kn5, 'GEOM': os.path.abspath(arg['--geom']), 'KN5_RAIZ': NOMBRE})
    log2 = open(os.path.join(out, '2_kn5.txt'), encoding='utf-8', errors='replace').read()
    if rc != 0 or 'OK KN5' not in log2:
        print('FALLO writer F (ver %s)' % os.path.join(out, '2_kn5.txt'))
        return 1
    print([ln for ln in log2.splitlines() if ln.startswith(('texturas:', 'OK KN5', 'terreno:'))])
    d, largo = carpeta_pista(out, kn5, arg['--geom'])
    inf = os.path.join(out, 'informe_check_f.json')
    r = subprocess.run([sys.executable, os.path.join(AQUI, 'kn5_check.py'), os.path.join(d, NOMBRE + '.kn5'), inf, '--no-wait',
                        '--quiet', '--shaders'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    with open(os.path.join(out, '3_check.txt'), 'w', encoding='utf-8') as fh:
        fh.write(r.stdout + r.stderr)
    checks = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith('(')]
    for c in checks:
        print('  ' + c[:110])
    ok = 'RESULTADO: OK' in r.stdout
    print('kn5_check F: %s' % ('OK' if ok else 'FALLO'))
    res = {'escena': st, 'kn5': kn5, 'kn5_MB': round(os.path.getsize(kn5) / 1e6, 1), 'carpeta': d, 'largo_tramo_m': largo,
           'kn5_check': 'OK' if ok else 'FALLO', 'comprobaciones': checks, 'segundos': round(time.time() - t0, 1)}
    if '--sin-zip' not in argv:
        zp = arg['--zip'] or os.path.join(out, NOMBRE + '.zip')
        if os.path.exists(zp):
            os.remove(zp)
        with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(os.path.join(out, 'LEEME.txt'), 'LEEME.txt')
            for raiz, _, fs in os.walk(os.path.join(out, 'content')):
                for fn in fs:
                    p = os.path.join(raiz, fn)
                    z.write(p, os.path.relpath(p, out))
        res['zip'] = zp
        res['zip_MB'] = round(os.path.getsize(zp) / 1e6, 1)
        print('OK zip F -> %s (%.1f MB)' % (zp, res['zip_MB']))
    json.dump(res, open(os.path.join(out, 'resumen_f.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    json.dump(CAMARAS_F, open(os.path.join(out, 'camaras_f.json'), 'w', encoding='utf-8'), indent=1)
    print('OK ensayo F (%.0fs)%s' % (time.time() - t0, '' if ok else ' CON FALLOS en kn5_check'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
