# -*- coding: utf-8 -*-
"""simular_ac.py (v3) - SIMULACION por familia de material, sin el juego (Python del sistema + numpy + PIL), de los
modelos de luz de AC de 04_export/color_ac.py sobre los 465 materiales de escena_rev.blend (materiales.json),
ANTES (colores y props actuales del writer) y DESPUES (color_ac.calibrar_todos), frente al render de Blender.
Modos (ver color_ac.py e investigacion.md):
  ac    AC sin CSP / CSP con estilo gamma: escena = tx*(ksA*AMB + ksD*SOL*N.L) + ksS*N.H^e*SOL*N.L, 3_clear
        (SOL 170,160,140 x20; AMB 105 x11), exposicion 0.2 (la autoexposicion se queda en su minimo), Yebis + 1.2.
  lcs   CSP con espacio lineal, curva ACES; lcsy: igual con conversion a sRGB + curva Yebis. Su autoexposicion
        depende de la escena: v3, una sola exposicion por etapa, la media geometrica de la que da la autoexposicion en
        las 7 vistas de ajuste (expo_lcs.json; la v2 la estimaba con los materiales sueltos y salia 0.27, la mitad).
Ademas, deltaE por familia EN LAS VISTAS (materiales_dE.json de simular_vistas.py, ponderado por pixeles): es la cifra
buena; la de las caras de referencia es solo orientativa.
Caras: suelo al sol, pared al sol, pared en sombra (N.L de las vistas; objetivo = aspecto medido o albedo x luz).
Salidas en 03_blender/_rev/color_ac/: simulacion_familias.md y simulacion_muestras.png
  python 03_blender/_rev/color_ac/simular_ac.py
"""
import copy
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(AQUI, '..', '..', '..', '04_export')))
import color_ac as C  # noqa: E402

CARAS = ('suelo_sol', 'pared_sol', 'sombra_pared')
MODOS = ('ac', 'lcs', 'lcsy')


def preparar():
    infos, caras = C._infos_de_volcado(os.path.join(AQUI, 'materiales.json'))
    antes = copy.deepcopy(infos)
    C.calibrar_todos(infos)
    return antes, infos, caras


def lineal(tx, info, props):
    """Valor lineal del modo LCS en las caras de referencia de este material."""
    nl = np.asarray(info.get('nl_ac', C._NL_G))[:3]
    nz = C._NZ_G[:3]
    p = dict(props)
    return C.escena_lcs(np.broadcast_to(tx, (3, 3)), p['ksAmbient'], p['ksDiffuse'], nl, nz, ks_emis=p['ksEmissive'])


def pantallas(tx, info, props, e_lcs):
    p = dict(props)
    nl = np.asarray(info.get('nl_ac', C._NL_G))[:3]
    esc = C.escena_ac(np.broadcast_to(tx, (3, 3)), p['ksAmbient'], p['ksDiffuse'], nl, ks_emis=p['ksEmissive'])
    lin = lineal(tx, info, props)
    return {'ac': C.pantalla_ac(esc), 'lcs': C.pantalla_lcs(lin, e_lcs), 'lcsy': C.pantalla_lcs_yebis(lin, e_lcs)}


def main():
    antes, desp, caras = preparar()
    w = np.array([caras.get(i['name'], 1) for i in desp], dtype=np.float64)
    props0 = C.SHADER_PROPS_ANTES
    tx_a = [C.lineal_a_srgb(i['color']) for i in antes]
    tx_d = [np.asarray(i['tx_ac']) for i in desp]
    ex = json.load(open(os.path.join(AQUI, 'expo_lcs.json'), encoding='utf-8'))
    expo = {et: ex['lcs_%s' % et]['autoexposicion'] for et in ('antes', 'despues')}
    vistas = {}                        # deltaE por familia en las vistas: {familia: {clave: [suma, pixeles]}}
    for mats in json.load(open(os.path.join(AQUI, 'materiales_dE.json'), encoding='utf-8')).values():
        for n, x in mats.items():
            f = vistas.setdefault(C.familia(n), {})
            for k, val in x.items():
                if k != 'pixeles':
                    a = f.setdefault(k, [0.0, 0])
                    a[0] += val * x['pixeles']
                    a[1] += x['pixeles']
    filas, fams = [], {}
    for k, i in enumerate(desp):
        obj = np.asarray(i['objetivo_ac'])[:3] if 'objetivo_ac' in i else \
            C.pantalla_blender(np.asarray(i['albedo_ac'])[None], C._K_G[:3])
        r = {'blender': obj, 'nombre': i['name'], 'caras': w[k]}
        for et, tx, pp in (('antes', tx_a[k], props0), ('despues', tx_d[k], i['props_ac'])):
            for m, img in pantallas(tx, i, pp, expo[et]).items():
                r['%s_%s' % (m, et)] = img
        fams.setdefault(i['familia'], []).append(r)
    md = ['# Simulacion por familia (color_ac %s)' % C.VERSION, '',
          'Pantalla sRGB 0-255 media de cada familia (ponderada por caras) en suelo al sol / pared al sol / pared en '
          'sombra, y deltaE Lab medio frente a Blender. Exposicion de los modos lineales (escena): ANTES %.2f, '
          'DESPUES %.2f. Generado por simular_ac.py.' % (expo['antes'], expo['despues']), '',
          '| familia | n | Blender (suelo / pared / sombra) | AC antes | AC despues | dE AC antes -> despues | '
          'dE lineal ACES antes -> despues | dE lineal Yebis antes -> despues | EN LAS VISTAS: px, dE gamma / ACES / '
          'Yebis / config. del amigo, antes -> despues |', '|' + '---|' * 9]
    for fam, lst in sorted(fams.items()):
        ww = np.array([r['caras'] for r in lst])
        ww = ww / ww.sum()
        med = lambda k: (np.tensordot(ww, np.array([r[k] for r in lst]), 1) * 255).round().astype(int).tolist()  # noqa
        de = lambda k: float(ww @ np.array([np.linalg.norm(C.lab(r[k]) - C.lab(r['blender']), axis=-1).mean()  # noqa
                                            for r in lst]))
        fv = vistas.get(fam, {})
        env = lambda m: ('%.1f -> %.1f' % (fv[m + '_antes'][0] / fv[m + '_antes'][1], fv[m + '_despues'][0] /  # noqa
                                         fv[m + '_despues'][1])) if m + '_antes' in fv else '-'
        md.append('| %s | %d | %s | %s | %s | %.1f -> %.1f | %.1f -> %.1f | %.1f -> %.1f | %s px: %s |' % (
            fam, len(lst), med('blender'), med('ac_antes'), med('ac_despues'), de('ac_antes'), de('ac_despues'),
            de('lcs_antes'), de('lcs_despues'), de('lcsy_antes'), de('lcsy_despues'),
            fv['ac_antes'][1] if 'ac_antes' in fv else 0, ' / '.join(env(m) for m in ('ac', 'lcs', 'lcsy', 'captura'))))
        filas += sorted(lst, key=lambda r: -r['caras'])[:2]
    md += ['', 'Muestras (2 materiales con mas caras por familia) en simulacion_muestras.png: cada casilla es '
           'suelo al sol | pared al sol | pared en sombra.']
    open(os.path.join(AQUI, 'simulacion_familias.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    cols = ['blender'] + ['%s_%s' % (m, et) for m in MODOS for et in ('antes', 'despues')]
    tit = ['Blender', 'AC antes', 'AC despues', 'ACES antes', 'ACES desp.', 'Yebis antes', 'Yebis desp.']
    cw, ch, x0 = 96, 22, 230
    lam = Image.new('RGB', (x0 + cw * len(cols), 24 + ch * len(filas)), (30, 30, 34))
    dr = ImageDraw.Draw(lam)
    for j, t in enumerate(tit):
        dr.text((x0 + j * cw + 4, 6), t, fill=(230, 230, 230))
    for k, r in enumerate(filas):
        y = 24 + k * ch
        dr.text((4, y + 5), r['nombre'][:36], fill=(230, 230, 230))
        for j, c in enumerate(cols):
            for q in range(3):
                col = tuple(int(v) for v in (np.clip(r[c][q], 0, 1) * 255).round())
                dr.rectangle((x0 + j * cw + q * (cw // 3), y + 1, x0 + j * cw + (q + 1) * (cw // 3) - 1, y + ch - 2), fill=col)
    lam.save(os.path.join(AQUI, 'simulacion_muestras.png'))
    print('\n'.join(md))


if __name__ == '__main__':
    main()
