# -*- coding: utf-8 -*-
"""informe_vistas.py (v3) - escribe informe_color_ac.md con las cifras de la simulacion (vistas_cifras.json,
muestras_materiales.json, materiales_dE.json, config_captura.json, tiempos_captura.json, palanca_csp.json,
informe_color_ac.json, expo_lcs.json). Sin cifras a mano.
  python 03_blender/_rev/color_ac/informe_vistas.py
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(AQUI, '..', '..', '..', '04_export')))
import color_ac as C  # noqa: E402

MODOS = (('ac', 'AC sin CSP / CSP gamma (3_clear)'), ('lcs', 'CSP lineal, curva ACES'), ('lcsy', 'CSP lineal, sRGB + Yebis'),
         ('captura', 'config. estimada del amigo (brillo x0.5)'), ('captura1', 'la misma con el brillo por defecto'),
         ('nubes', 'AC sin CSP, 5_light_clouds'), ('nubes2', '5_light_clouds, brillo x1.4, sat 0.7 (2a hipotesis)'))
CLAVE = ('MAT_asfalto', 'MAT_terreno', C.ROCA_MAT, 'MAT_agua', 'MAT_MCOCHE_caliza', 'MAT_CASAS_teja',
         'MAT_CASAS_fachada_amarillo')


def j(n):
    p = os.path.join(AQUI, n)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def main():
    vc, mu, cfg, inf = j('vistas_cifras.json'), j('muestras_materiales.json'), j('config_captura.json'), \
        j('informe_color_ac.json')['informe']
    tc, pal, md, ex = j('tiempos_captura.json'), j('palanca_csp.json'), j('materiales_dE.json'), j('expo_lcs.json')
    V = vc['vistas']
    meta = json.load(open(os.path.join(AQUI, '_pases', 'vistas.json'), encoding='utf-8'))
    todas = meta['ajuste'] + meta['control']
    t = ['# Informe color_ac v3: antes / despues', '',
         'Generado por `informe_vistas.py` a partir de la simulacion (`render_ac.py` sobre `escena_color.blend` -> '
         '`simular_vistas.py`). deltaE = diferencia CIE76 en Lab frente al render de Blender (media por pixel, sin cielo); '
         'croma y contraste (desviacion de luminancia) como cociente frente a Blender (1 = igual).', '',
         'Vistas de AJUSTE (con ellas se eligio todo): %s. Vistas de CONTROL (no se usaron para nada): %s.'
         % (', '.join(meta['ajuste']), ', '.join(meta['control'])), '',
         'Valores elegidos: ksAmbient %.2f / ksDiffuse %.2f en todas las familias; caras de roca del terreno -> %s; '
         'exposicion de los modos lineales en el ajuste %s (autoexposicion real de las vistas: antes %.2f, despues %.2f).'
         % (C.FAMILIAS['terreno']['props'][0], C.FAMILIAS['terreno']['props'][1], C.ROCA_MAT, C.EXPO_LCS_AJUSTE,
            ex['lcs_antes']['autoexposicion'], ex['lcs_despues']['autoexposicion']), '',
         '## 1. Resumen por modo de sombreado', '',
         '| modo | grupo | deltaE antes -> despues | croma/Blender antes -> despues | contraste/Blender antes -> despues |',
         '|---|---|---|---|---|']
    for m, nom in MODOS:
        for g in ('ajuste', 'control'):
            r = vc['resumen'][g]
            if m + '_antes' in r:
                a, b = r[m + '_antes'], r[m + '_despues']
                t.append('| %s | %s | %.1f -> %.1f | %.2f -> %.2f | %.2f -> %.2f |' % (
                    nom, g, a['deltaE'], b['deltaE'], a['croma/blender'], b['croma/blender'], a['std/blender'], b['std/blender']))
    t += ['', '## 2. deltaE por vista (antes -> despues)', '', '| vista | ' + ' | '.join(n for _, n in MODOS) + ' |',
          '|' + '---|' * (len(MODOS) + 1)]
    for v in todas:
        cel = []
        for m, _ in MODOS:
            a, b = V[v][m + '_antes']['deltaE_con_blender'], V[v][m + '_despues']['deltaE_con_blender']
            cel.append('%.1f -> %.1f%s' % (a, b, ' (peor)' if b > a else ''))
        t.append('| %s%s | %s |' % (v, ' (control)' if v in meta['control'] else '', ' | '.join(cel)))
    t += ['', '## 3. Luminancia, croma, contraste y saturacion por vista, modo gamma (Blender / antes / despues)', '',
          '| vista | lum media | croma media | contraste (std lum) | saturacion media |', '|---|---|---|---|---|']
    for v in todas:
        b, a, d = V[v]['blender'], V[v]['ac_antes'], V[v]['ac_despues']
        t.append('| %s | %.0f / %.0f / %.0f | %.1f / %.1f / %.1f | %.1f / %.1f / %.1f | %.2f / %.2f / %.2f |' % (
            v, b['lum_media'], a['lum_media'], d['lum_media'], b['croma_media'], a['croma_media'], d['croma_media'],
            b['contraste_lum_std'], a['contraste_lum_std'], d['contraste_lum_std'], b['saturacion_media'],
            a['saturacion_media'], d['saturacion_media']))
    t += ['', '## 4. Materiales clave al sol (color mediano en pantalla, sRGB)', '',
          '| vista | material | Blender | AC antes | AC despues | ACES despues | Yebis despues | amigo antes -> despues |',
          '|---|---|---|---|---|---|---|---|']
    for v in ('captura', 'meta_tunel', 'meta_puerto', 'pueblo', 'tierra', 'piloto_s300', 'puente'):
        for n, x in mu.get(v, {}).items():
            if n in CLAVE:
                t.append('| %s | %s | %s | %s | %s | %s | %s | %s -> %s |' % (v, n, x['blender'], x['ac_antes'], x['ac_despues'],
                                                                         x['lcs_despues'], x['lcsy_despues'],
                                                                         x['captura_antes'], x['captura_despues']))
    acc = {}
    for mats in md.values():
        for n, x in mats.items():
            a = acc.setdefault(n, {'pixeles': 0})
            a['pixeles'] += x['pixeles']
            for k, val in x.items():
                if k != 'pixeles':
                    a[k] = a.get(k, 0.0) + val * x['pixeles']
    prot = sorted(acc.items(), key=lambda kv: -kv[1]['pixeles'])[:14]
    t += ['', '## 5. Materiales protagonistas (los 14 con mas pixeles en las 10 vistas): deltaE antes -> despues', '',
          '| material | pixeles | ' + ' | '.join(nom for m, nom in MODOS if m != 'captura1') + ' |',
          '|' + '---|' * (len(MODOS) + 1)]
    for n, a in prot:
        t.append('| %s | %d | %s |' % (n, a['pixeles'], ' | '.join(
            '%.1f -> %.1f%s' % (a[m + '_antes'] / a['pixeles'], a[m + '_despues'] / a['pixeles'],
                                ' (peor)' if a[m + '_despues'] > a[m + '_antes'] + a['pixeles'] * 0.5 else '')
            for m, _ in MODOS if m != 'captura1')))
    t += ['', '## 6. Lo que se sabe de la configuracion del amigo', '',
          'Captura (zona de juego sin coche ni HUD): %s.' % cfg['captura'], '',
          '- Configuracion estimada (ajuste_captura.py, %s): ambiente x%.1f, brillo x%.2f, bruma a %d m, saturacion %.2f; '
          'reproduce lum %.0f, sat %.3f, asfalto %s. Con el brillo por defecto daria lum %.0f (casi blanco): encaja con '
          '"antes era peor".' % (cfg['nota'].split(':')[0], cfg['ambiente'], cfg['brillo'], cfg['distancia_bruma'],
                                 cfg['saturacion'], cfg['modelo_antes']['lum_media'], cfg['modelo_antes']['saturacion_media'],
                                 cfg['modelo_antes']['asfalto'], cfg['modelo_antes_brillo_1']['lum_media'])]
    if tc:
        t += ['- Tiempos de Kunos (tiempos_captura.py, coste del ajuste a la captura; la estimada da %.1f):' %
              tc['config_estimada']['coste']]
        for k, x in tc['tiempos'].items():
            t.append('  - %s: por defecto lum %.0f, sat %.3f, asfalto %s (coste %.0f); mejor con brillo x%.1f y saturacion %.2f '
                     '(coste %.1f)' % (k, x['por_defecto']['lum_media'], x['por_defecto']['saturacion_media'],
                                       [round(c) for c in x['por_defecto']['asfalto']], x['por_defecto']['coste'],
                                       x['mejor']['brillo'], x['mejor']['saturacion'], x['mejor']['coste']))
    t += ['', 'Lo que veria el amigo con el KN5 nuevo y sus ajustes de ahora (vista de la captura): estimada %s, '
          '2a hipotesis %s; con el brillo por defecto %s (Blender %s). Formato: lum / sat / contraste.' % tuple(
              '%.0f / %.2f / %.0f' % (V['captura'][k]['lum_media'], V['captura'][k]['saturacion_media'],
                                      V['captura'][k]['contraste_lum_std'])
              for k in ('captura_despues', 'nubes2_despues', 'captura1_despues', 'blender'))]
    if pal:
        t += ['', '## 7. Palanca de ext_config.ini (solo CSP), media de las vistas de ajuste', '',
              '| ks | ' + ' | '.join(pal[next(iter(pal))]) + ' |', '|' + '---|' * (len(pal[next(iter(pal))]) + 1)]
        for k, x in pal.items():
            t.append('| %s | %s |' % (k, ' | '.join('%.1f' % val for val in x.values())))
    t += ['', '## 8. Por familia (modo gamma, caras de referencia; color_ac --informe)', '',
          'Origen del objetivo de cada material: %s.' % ', '.join('%s %d' % (k, n) for k, n in inf['fuentes'].items()), '',
          C.informe_texto(inf), '']
    open(os.path.join(AQUI, 'informe_color_ac.md'), 'w', encoding='utf-8').write('\n'.join(t))
    print('\n'.join(t))


if __name__ == '__main__':
    main()
