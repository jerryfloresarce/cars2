# -*- coding: utf-8 -*-
"""escribir_cambio.py - compone CAMBIO_KN5_WRITER.md con el texto, los dos diffs EXACTOS de 04_export/_color_ac_prueba/
y las cifras de la prueba (KN5 de prueba, kn5_check, simulacion). Asi el diff del documento es byte a byte el que pasa
git apply --check.
  python 03_blender/_rev/color_ac/escribir_cambio.py <cuerpo.md>
"""
import hashlib
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.abspath(os.path.join(AQUI, '..', '..', '..', '04_export'))
PRU = os.path.join(EXP, '_color_ac_prueba')


def md5(ruta):
    h = hashlib.md5()
    with open(ruta, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def main(cuerpo):
    res = json.load(open(os.path.join(PRU, 'porto_corsa_color_resumen.json'), encoding='utf-8'))
    vc = json.load(open(os.path.join(AQUI, 'vistas_cifras.json'), encoding='utf-8'))['resumen']
    kn5 = os.path.join(PRU, 'porto_corsa_color.kn5')
    roca = res.get('color_ac_roca_terreno', {})
    nombres = {'ac': 'AC sin CSP, o CSP con estilo gamma (Sol, Pure Gamma), tiempo 3_clear',
               'lcs': 'CSP con espacio lineal, curva ACES', 'lcsy': 'CSP con espacio lineal, sRGB + Yebis',
               'captura': 'Configuracion estimada del amigo (la de su captura, con su brillo bajado)',
               'captura1': 'La misma con el brillo por defecto', 'nubes': 'AC sin CSP con 5_light_clouds',
               'nubes2': 'Segunda hipotesis para la captura: 5_light_clouds, brillo x1.4, saturacion 0.7'}
    esp = []
    for m, n in nombres.items():
        a, c = vc['ajuste'], vc['control']
        esp.append('- **%s.** deltaE frente a Blender %.1f -> %.1f en las vistas de ajuste y %.1f -> %.1f en las de control; '
                   'croma %.2f -> %.2f y contraste %.2f -> %.2f x Blender.' % (
                       n, a[m + '_antes']['deltaE'], a[m + '_despues']['deltaE'], c[m + '_antes']['deltaE'],
                       c[m + '_despues']['deltaE'], a[m + '_antes']['croma/blender'], a[m + '_despues']['croma/blender'],
                       a[m + '_antes']['std/blender'], a[m + '_despues']['std/blender']))
    texto = open(cuerpo, encoding='utf-8').read() % {
        'kn5_mb': os.path.getsize(kn5) / 1e6, 'n_mat': res['n_materiales'], 'md5': md5(kn5),
        'roca': '%d caras de roca en %s' % (sum(roca.values()), ', '.join('%s %d' % kv for kv in roca.items())),
        'espera': '\n'.join(esp)}
    for nom in ('kn5_writer_opt', 'empaquetar'):
        diff = open(os.path.join(PRU, nom + '.diff'), encoding='utf-8', newline='').read().replace('\r\n', '\n')
        texto += '\n## Diff de 04_export/%s.py\n\n```diff\n%s```\n' % (nom, diff)
    open(os.path.join(AQUI, 'CAMBIO_KN5_WRITER.md'), 'w', encoding='utf-8').write(texto)
    print('OK CAMBIO_KN5_WRITER.md (%d lineas)' % texto.count('\n'))


if __name__ == '__main__':
    main(sys.argv[1])
