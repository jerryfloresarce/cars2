# -*- coding: utf-8 -*-
"""simular_vistas.py (v3) - aplica los modelos de luz de AC (04_export/color_ac.py) a los pases de render_ac.py.
La textura que veria AC en cada pixel se RECONSTRUYE con el pase id (material) y el pase pat (patron de la imagen):
tx = sRGB(color_del_material * patron), igual que construir_textura() del writer, para la calibracion ANTES (writer
actual) y DESPUES (color_ac.calibrar_todos), sin volver a renderizar. Modos:
  ac       AC sin CSP / CSP con estilo gamma: espacio gamma, 3_clear, niebla de Kunos, autoexposicion + Yebis
  lcs      CSP con espacio de color lineal (Pure LCS, WeatherFX por defecto con LCS): pow 2.2, luz fisica, ACES
  lcsy     igual, pero lineal -> sRGB y curva Yebis del filtro (conversion por defecto de CSP antes de YEBIS)
  captura  la configuracion del amigo ESTIMADA ajustando 4 parametros a la captura (ver ajuste_captura.py), con su
           brillo bajado (x0.5): lo que tiene ahora
  captura1 la misma con el brillo por defecto (x1): como lo veia antes de tocar nada ("antes era peor")
  nubes    AC sin CSP con el tiempo 5_light_clouds de Kunos (ambiente el doble que el sol): prueba de robustez
  nubes2   el mismo con el brillo x1.4 y la saturacion 0.7 del filtro: la segunda hipotesis que reproduce la captura
           (tiempos_captura.py: coste 3.8, frente a 1.5 de la configuracion estimada con 4 parametros)
v3: las caras de MAT_terreno que el writer pasa a MAT_terreno_roca (pase msk + color_ac.mascara_roca) se simulan
con ese material (indice virtual al final de MATS; ANTES llevaban el color de MAT_terreno).
Python del sistema (numpy + PIL):  python 03_blender/_rev/color_ac/simular_vistas.py [vista1,vista2]
Salidas en 03_blender/_rev/color_ac/: <vista>_<modo>_<antes|despues>.png, comparativa_<vista>.png, vistas_cifras.json,
luz_escena.json (luz de Blender por canal), muestras_materiales.json
"""
import copy
import json
import math
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(AQUI, '..', '..', '..', '04_export')))
import color_ac as C  # noqa: E402

PASES = os.path.join(AQUI, '_pases')
META = json.load(open(os.path.join(PASES, 'vistas.json'), encoding='utf-8'))
MATS = json.load(open(os.path.join(PASES, 'materiales_vista.json'), encoding='utf-8'))['materiales']
LUM_SOL_B = float(C.luminancia(np.array(META['sol_color'])))
S_NOM = None      # nombres por indice (se rellena tras anadir el material virtual)
CAPTURA_CFG = os.path.join(AQUI, 'config_captura.json')
# material virtual MAT_terreno_roca (no existe en Blender: lo crea el writer con color_ac.separar_roca_terreno)
IDX_TER = next(i for i, m in enumerate(MATS) if m['name'] == C.ROCA_BASE)
MATS.append(dict(MATS[IDX_TER], name=C.ROCA_MAT, color=list(C.ROCA_COLOR), virtual=True))
IDX_ROCA = len(MATS) - 1
S_NOM = [m['name'] for m in MATS]
MODOS_V = ('ac', 'lcs', 'lcsy', 'captura', 'captura1', 'nubes', 'nubes2')
NUBES2 = {'brillo': 1.4, 'saturacion': 0.7}      # mejor ajuste de 5_light_clouds a la captura (tiempos_captura.json)
MUESTRAS = ('MAT_asfalto', 'MAT_terreno', C.ROCA_MAT, 'MAT_agua', 'MAT_MCOCHE_caliza', 'MAT_CASAS_fachada_amarillo', 'MAT_CASINO_fachada',
            'MAT_CARRERA_blanco', 'MAT_CARRERA_verde_wgp', 'MAT_PIT_blanco', 'MAT_VEG_encina_b', 'MAT_CASAS_teja')


def cargar(v, escala=1):
    """Pases de una vista (cada `escala` pixeles) + mascaras."""
    d = {p: np.load(os.path.join(PASES, '%s_%s.npy' % (v, p))).astype(np.float32)[::escala, ::escala]
         for p in ('sol', 'geo', 'pat', 'alb')}
    a = np.load(os.path.join(PASES, '%s_id.npy' % v))[::escala, ::escala]
    r = a[..., 0] * 1024.0
    idx = np.round(r).astype(int) - 1
    gchk = ((idx + 1) * 37 % 101) / 101.0
    d['cielo'] = a[..., 3] < 0.5
    d['valido'] = (~d['cielo']) & (np.abs(r - np.round(r)) < 0.02) & (np.abs(a[..., 1] - gchk) < 0.004) & \
        (idx >= 0) & (idx < IDX_ROCA)
    d['idx'] = np.where(d['valido'], idx, 0)
    pm = os.path.join(PASES, '%s_msk.npy' % v)
    if os.path.exists(pm):        # caras de roca del writer -> MAT_terreno_roca
        k = np.load(pm)[::escala, ::escala]
        d['roca_blender'] = k[..., 0] > 0.5
        roca = d['valido'] & (d['idx'] == IDX_TER) & C.mascara_roca(k[..., 2] * 2.0 - 1.0, k[..., 1])
        d['idx'] = np.where(roca, IDX_ROCA, d['idx'])
    d['nl'] = np.clip(C.luminancia(d['sol'][..., :3]) / (META['sol_energia'] / math.pi * LUM_SOL_B), 0, 1)
    d['nh'], d['nz'], d['dist'] = d['geo'][..., 0], d['geo'][..., 1] * 2 - 1, d['geo'][..., 2] * 1000.0
    ref = Image.open(os.path.join(AQUI, '%s_blender.png' % v)).convert('RGB')
    d['ref'] = (np.asarray(ref).astype(np.float32) / 255.0)[::escala, ::escala]
    d['elev'] = elevacion(v, *d['ref'].shape[:2])
    return d


def elevacion(v, h, w):
    """Elevacion (rad) del rayo de cada pixel (sensor 36 mm horizontal)."""
    c = META['camaras'][v]
    f, u = np.array(c['adelante']), np.array(c['arriba'])
    r = np.cross(f, u)
    xs = ((np.arange(w) + 0.5) / w - 0.5) * 36.0 / c['lens']
    ys = (0.5 - (np.arange(h) + 0.5) / h) * 36.0 * h / w / c['lens']
    X, Y = np.meshgrid(xs, ys)
    d = f[None, None] + X[..., None] * r[None, None] + Y[..., None] * u[None, None]
    return np.arcsin(np.clip(d[..., 2] / np.linalg.norm(d, axis=-1), -1, 1))


def cielo_ac(elev):
    t = np.clip(elev / math.radians(35.0), 0, 1)[..., None] ** 0.6
    return C.HORIZONTE_AC * (1 - t) + C.CIELO_AC * t


def tablas(etapa, infos_d=None):
    """Por material: color lineal (M,3) y props (M,5) de la etapa ANTES (writer actual) o DESPUES."""
    if etapa == 'antes':
        col = np.array([m['color'] for m in MATS], dtype=np.float64)
        col[IDX_ROCA] = col[IDX_TER]                   # antes no habia MAT_terreno_roca
        pr = np.tile([v for _, v in C.SHADER_PROPS_ANTES[:5]], (len(MATS), 1))
    else:
        col = np.array([i['color'] for i in infos_d], dtype=np.float64)
        pr = np.array([[v for _, v in i['props_ac'][:5]] for i in infos_d], dtype=np.float64)
    return col, pr


def calibrados():
    infos = [{'name': m['name'], 'color': tuple(m['color']), 'alpha': m.get('alpha', 1.0), 'img': None}
             for m in copy.deepcopy(MATS)]
    return C.calibrar_todos(infos)


def textura(d, col):
    return C.lineal_a_srgb(col[d['idx']] * d['pat'][..., :3])


def simular_modo(d, modo, col, pr, cfg=None):
    """Pantalla sRGB 0..1 de la vista en un modo, y su exposicion."""
    tx = textura(d, col)
    p = pr[d['idx']]
    ka, kd, ks, ke, kem = (p[..., k] for k in range(5))
    if modo in ('ac', 'captura', 'captura1', 'nubes', 'nubes2'):
        sol, amb, nie, sky = C.SOL_AC, C.AMB_AC, C.NIEBLA_AC, cielo_ac(d['elev'])
        if modo in ('nubes', 'nubes2'):       # cielo cubierto: el de la captura (blanco) en HDR de la exposicion 0.2
            sol, amb, nie = C.TIEMPOS_AC['5_light_clouds']
            sky = np.broadcast_to(C.saturar(C.tonemap_ac_inv(np.array([215.0, 221.0, 225.0]) / 255), 1 / C.PP_SAT)
                                  / C.EXPO_MIN, sky.shape)
        if modo in ('captura', 'captura1'):
            sol = np.full(3, float(C.luminancia(C.SOL_AC)))           # sol de mediodia de WeatherFX: blanco
            amb = C.AMB_AC * cfg['ambiente']
            nie = (np.asarray(cfg['bruma']), 1.0, cfg['distancia_bruma'])
            sky = np.broadcast_to(np.asarray(cfg['bruma']), sky.shape)
        esc = C.escena_ac(tx, ka, kd, d['nl'], ks, ke, d['nh'], kem, sol=sol, amb=amb, distancia=d['dist'], niebla=nie)
        esc[d['cielo']] = sky[d['cielo']]
        e = C.autoexposicion_ac(float(np.mean(C.luminancia(esc))))
        if modo == 'nubes2':
            return C.pantalla_ac(esc, e * NUBES2['brillo'], NUBES2['saturacion']), e * NUBES2['brillo']
        if modo in ('captura', 'captura1'):
            e *= cfg['brillo'] if modo == 'captura' else 1.0
            return C.pantalla_ac(esc, e, cfg.get('saturacion', C.PP_SAT)), e
        return C.pantalla_ac(esc, e), e
    lin = C.escena_lcs(tx, ka, kd, d['nl'], d['nz'], ks, ke, d['nh'], kem)
    lin[d['cielo']] = C.srgb_a_lineal(d['ref'][d['cielo']]) * 2 ** -META['exposicion_blender']
    e = C.autoexposicion_lcs(C.luminancia(lin))
    return (C.pantalla_lcs_yebis(lin, e) if modo == 'lcsy' else C.pantalla_lcs(lin, e)), e


def cifras(img, d, mask=None):
    m = d['valido'] if mask is None else mask
    x, ref = img[m], d['ref'][m]
    sat = (x.max(-1) - x.min(-1)) / np.maximum(x.max(-1), 1e-4)
    out = {'lum_media': round(float(C.luminancia(x).mean()) * 255, 1),
           'contraste_lum_std': round(float(C.luminancia(x).std()) * 255, 1),
           'saturacion_media': round(float(sat.mean()), 3),
           'croma_media': round(float(C.croma(x).mean()), 1),
           'quemados_%': round(float((x.max(-1) > 0.96).mean()) * 100, 1)}
    if ref is not None:
        out['deltaE_con_blender'] = round(float(np.linalg.norm(C.lab(x) - C.lab(ref), axis=-1).mean()), 1)
    return out


def luz_blender(d):
    """K = pantalla lineal de Blender / albedo, POR CANAL, en materiales difusos sin recortar (mediana)."""
    fam = np.array([C.familia(m['name']) for m in MATS])
    alb = d['alb'][..., :3]
    k = C.srgb_a_lineal(d['ref']) * 2 ** -0 / np.maximum(alb, 1e-3)
    dif = d['valido'] & np.isin(fam[d['idx']], ['edificio', 'roca', 'terreno', 'pintado', 'vegetacion']) & \
        (d['ref'].max(-1) < 0.93) & (alb.min(-1) > 0.04)
    top, ver = d['nz'] > 0.9, np.abs(d['nz']) < 0.3
    out = {}
    for nom, m in (('suelo_sol', top & (d['nl'] > 0.7)), ('pared_sol', ver & (d['nl'] > 0.3)),
                   ('sombra_pared', ver & (d['nl'] < 0.02)), ('sombra_suelo', top & (d['nl'] < 0.02))):
        mm = m & dif
        if mm.sum() > 200:
            out[nom] = {'K': np.round(np.median(k[mm], 0), 3).tolist(), 'pixeles': int(mm.sum()),
                        'N.L_mediana': round(float(np.median(d['nl'][mm])), 3)}
    return out


def muestras(d, imgs):
    """Color mediano (0-255) de unos materiales clave al sol (N.L > 0.3) en cada imagen."""
    out = {}
    nombres = [m['name'] for m in MATS]
    for nom in MUESTRAS:
        if nom not in nombres:
            continue
        m = d['valido'] & (d['idx'] == nombres.index(nom)) & (d['nl'] > 0.3)
        if m.sum() < 150:
            continue
        out[nom] = {'pixeles': int(m.sum()), 'blender': (np.median(d['ref'][m], 0) * 255).round().astype(int).tolist()}
        for k, img in imgs.items():
            out[nom][k] = (np.median(img[m], 0) * 255).round().astype(int).tolist()
    return out


def _u8(img):
    return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))


def comparativa(v, paneles):
    """Lamina de 3 columnas: [(titulo, imagen, cifras)]."""
    from PIL import ImageDraw
    h, w = paneles[0][1].shape[:2]
    filas = (len(paneles) + 2) // 3
    lam = Image.new('RGB', (3 * w, filas * (h + 30)), (24, 24, 28))
    dr = ImageDraw.Draw(lam)
    for k, (t, img, f) in enumerate(paneles):
        x, y = (k % 3) * w, (k // 3) * (h + 30)
        im = _u8(img) if isinstance(img, np.ndarray) else img
        lam.paste(im.resize((w, h)), (x, y + 30))
        txt = t
        if f:
            txt += '  dE %s  lum %.0f  sat %.2f  croma %.0f  std %.0f' % (
                f.get('deltaE_con_blender', '-'), f['lum_media'], f['saturacion_media'], f['croma_media'],
                f['contraste_lum_std'])
        dr.text((x + 6, y + 9), txt, fill=(235, 235, 235))
    lam.save(os.path.join(AQUI, 'comparativa_%s.png' % v))


def simular(v, infos_d, cfg=None, guardar=True):
    d = cargar(v)
    tab = {'antes': tablas('antes'), 'despues': tablas('despues', infos_d)}
    imgs, cif = {}, {'blender': cifras(d['ref'], d)}
    cif['blender'].pop('deltaE_con_blender', None)
    modos = [m for m in MODOS_V if cfg or not m.startswith('captura')]
    ref_lab = C.lab(d['ref'])
    val = d['valido']
    ids, npx = np.unique(d['idx'][val], return_counts=True)
    por_mat = {S_NOM[i]: {'pixeles': int(n)} for i, n in zip(ids, npx)}
    for modo in modos:
        for et in ('antes', 'despues'):
            img, e = simular_modo(d, modo, *tab[et], cfg=cfg)
            imgs['%s_%s' % (modo, et)] = img
            cif['%s_%s' % (modo, et)] = dict(cifras(img, d), exposicion=round(e, 3))
            de = np.linalg.norm(C.lab(img) - ref_lab, axis=-1)[val]
            suma = np.bincount(d['idx'][val], weights=de, minlength=len(MATS))
            for i, n in zip(ids, npx):
                por_mat[S_NOM[i]]['%s_%s' % (modo, et)] = round(float(suma[i] / n), 2)
    if guardar:
        for k, img in imgs.items():
            _u8(img).save(os.path.join(AQUI, '%s_%s.png' % (v, k)))
        pan = [('Blender (objetivo)', d['ref'], cif['blender']),
               ('AC sin CSP ANTES', imgs['ac_antes'], cif['ac_antes']),
               ('AC sin CSP DESPUES', imgs['ac_despues'], cif['ac_despues']),
               ('CSP lineal (ACES) ANTES', imgs['lcs_antes'], cif['lcs_antes']),
               ('CSP lineal (ACES) DESPUES', imgs['lcs_despues'], cif['lcs_despues']),
               ('CSP lineal (sRGB + Yebis) ANTES', imgs['lcsy_antes'], cif['lcsy_antes']),
               ('CSP lineal (sRGB + Yebis) DESPUES', imgs['lcsy_despues'], cif['lcsy_despues'])]
        if cfg:
            if v == 'captura' and os.path.exists(os.path.join(AQUI, 'captura_juego.png')):
                pan.append(('CAPTURA DEL USUARIO (juego)', Image.open(os.path.join(AQUI, 'captura_juego.png')), None))
            pan += [('config. estimada del amigo (brillo x0.5) ANTES', imgs['captura_antes'], cif['captura_antes']),
                    ('config. estimada del amigo (brillo x0.5) DESPUES', imgs['captura_despues'], cif['captura_despues']),
                    ('config. estimada, brillo por defecto ANTES', imgs['captura1_antes'], cif['captura1_antes']),
                    ('config. estimada, brillo por defecto DESPUES', imgs['captura1_despues'], cif['captura1_despues'])]
        pan += [('AC sin CSP, tiempo 5_light_clouds ANTES', imgs['nubes_antes'], cif['nubes_antes']),
                ('AC sin CSP, tiempo 5_light_clouds DESPUES', imgs['nubes_despues'], cif['nubes_despues']),
                ('5_light_clouds, brillo x1.4, sat 0.7 ANTES', imgs['nubes2_antes'], cif['nubes2_antes']),
                ('5_light_clouds, brillo x1.4, sat 0.7 DESPUES', imgs['nubes2_despues'], cif['nubes2_despues'])]
        comparativa(v, pan)
    return cif, luz_blender(d), muestras(d, imgs), por_mat


def resumen_modos(todo, vistas):
    """Media por grupo de vistas (ajuste / control) del deltaE y del cociente de croma frente a Blender."""
    res = {}
    for grupo in ('ajuste', 'control'):
        vs = [v for v in META[grupo] if v in vistas]
        if not vs:
            continue
        r = {}
        for k in todo[vs[0]]:
            if k == 'blender':
                continue
            r[k] = {'deltaE': round(float(np.mean([todo[v][k]['deltaE_con_blender'] for v in vs])), 2),
                    'croma/blender': round(float(np.mean([todo[v][k]['croma_media'] / todo[v]['blender']['croma_media']
                                                          for v in vs])), 2),
                    'std/blender': round(float(np.mean([todo[v][k]['contraste_lum_std'] /
                                                        todo[v]['blender']['contraste_lum_std'] for v in vs])), 2)}
        res[grupo] = r
    return res


if __name__ == '__main__':
    vistas = sys.argv[1].split(',') if len(sys.argv) > 1 else META['ajuste'] + META['control']
    cfg = json.load(open(CAPTURA_CFG, encoding='utf-8')) if os.path.exists(CAPTURA_CFG) else None
    infos_d = calibrados()
    todo, luz, mues, pmat = {}, {}, {}, {}
    for v in vistas:
        todo[v], luz[v], mues[v], pmat[v] = simular(v, infos_d, cfg)
        print(v, json.dumps({k: (x.get('deltaE_con_blender'), x['croma_media'], x['contraste_lum_std'])
                             for k, x in todo[v].items()}))
    res = resumen_modos(todo, vistas)
    print(json.dumps(res, indent=1))
    json.dump({'version': C.VERSION, 'resumen': res, 'vistas': todo}, open(os.path.join(AQUI, 'vistas_cifras.json'), 'w',
                                                                            encoding='utf-8'), indent=1)
    json.dump(luz, open(os.path.join(AQUI, 'luz_escena.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(mues, open(os.path.join(AQUI, 'muestras_materiales.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(pmat, open(os.path.join(AQUI, 'materiales_dE.json'), 'w', encoding='utf-8'), indent=0)
