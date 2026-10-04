# -*- coding: utf-8 -*-
"""prueba_color_ac.py (v3) - pruebas de 04_export/color_ac.py (Python del sistema, numpy + PIL).
  python 04_export/prueba_color_ac.py
1. modelo de AC frente a la captura: el ANTES por defecto es mas claro que la captura en el asfalto, la configuracion
   estimada (config_captura.json) la reproduce y coincide con las constantes CAP_* de color_ac; ningun tiempo de Kunos
   la reproduce con el brillo por defecto (tiempos_captura.json);
2. calibrar_todos(): idempotente, igual que calibrar(), sin NaN, props validas (0.4-0.6, cociente 0.6-1.1) en el orden
   del writer, medidas obsoletas ignoradas;
3. los materiales de la escena congelada: el deltaE gamma no empeora por familia y la croma respeta su techo;
4. ext_config: INI legible, sin TRACK_AMBIENT_GROUND_MULT ni agua de CSP por defecto, no se machaca uno editado a mano;
5. el parche de CAMBIO_KN5_WRITER.md sigue aplicando sobre kn5_writer_opt.py y empaquetar.py actuales;
6. roca del terreno: el criterio de color_ac.mascara_roca() da la mascara de Blender en >= 95 % de los pixeles de
   terreno de las 10 vistas; y si existe _color_ac_prueba/porto_corsa_color.kn5, sus props y colores son los de color_ac
   y lleva MAT_terreno_roca;
7. simulacion de vistas (vistas_cifras.json, materiales_dE.json). PUEDE FALLAR en todos los modos de referencia
   (ac, lcs, lcsy, captura): el deltaE medio tiene que mejorar en ajuste Y en control; ninguna vista puede empeorar
   (gamma: nada; los demas: mas de 0.5); ningun material protagonista (>= 50 000 pixeles en las vistas) puede quedar
   mas de 2.3 de deltaE peor (una diferencia apenas perceptible); croma y contraste del modo gamma entre 0.85 y 1.2 x
   Blender. Los modos de robustez (nubes, nubes2, captura1) solo se listan.
Sale con codigo 0 si todo va bien."""
import configparser
import copy
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import color_ac as C  # noqa: E402

REV = os.path.join(AQUI, '..', '03_blender', '_rev', 'color_ac')
fallos = []


def comprobar(cond, texto):
    print(('  OK    ' if cond else '  FALLO ') + texto)
    if not cond:
        fallos.append(texto)


def j(n):
    p = os.path.join(REV, n)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


print('1. modelo de AC frente a la captura del usuario')
asf = C.pantalla_ac(C.escena_ac(C.lineal_a_srgb([0.105, 0.102, 0.108]), 0.45, 0.55, C.COS_SUELO)) * 255
comprobar(150 <= asf.mean() <= 175, 'asfalto ANTES al sol, 3_clear por defecto = %s (captura: 156,154,157)' % asf.round().astype(int))
comprobar(abs(C.tonemap_ac_inv(C.tonemap_ac(0.7)) - 0.7) < 1e-3 and abs(C.aces_inv(C.aces(0.3)) - 0.3) < 1e-3,
          'las curvas (Yebis, ACES) y sus inversas cuadran')
cfg = j('config_captura.json')
if cfg:
    a, m, b1 = cfg['captura'], cfg['modelo_antes'], cfg['modelo_antes_brillo_1']
    comprobar(abs(a['lum_media'] - m['lum_media']) < 8 and abs(a['saturacion_media'] - m['saturacion_media']) < 0.03
              and np.abs(np.subtract(a['asfalto'], m['asfalto'])).max() < 6,
              'config. estimada (ambiente x%.1f, brillo %.2f, bruma %d m): lum %.0f/%.0f, sat %.3f/%.3f, asfalto %s/%s' % (
                  cfg['ambiente'], cfg['brillo'], cfg['distancia_bruma'], m['lum_media'], a['lum_media'],
                  m['saturacion_media'], a['saturacion_media'], m['asfalto'], a['asfalto']))
    comprobar((cfg['ambiente'], cfg['brillo'], cfg['saturacion']) == (C.CAP_AMBIENTE, C.CAP_BRILLO, C.CAP_SAT),
              'las constantes CAP_* de color_ac son las de config_captura.json')
    comprobar('4 parametros' in cfg['nota'], 'config_captura.json dice "4 parametros"')
tc = j('tiempos_captura.json')
if tc:
    d = {k: v['por_defecto']['coste'] for k, v in tc['tiempos'].items()}
    comprobar(min(d.values()) > 10 * tc['config_estimada']['coste'],
              'ningun tiempo de Kunos con el brillo por defecto explica la captura (coste %s; estimada %.1f)' % (
                  d, tc['config_estimada']['coste']))

print('2. calibrar_todos()')
nombres_writer = ['ksAmbient', 'ksDiffuse', 'ksSpecular', 'ksSpecularEXP', 'ksEmissive', 'ksAlphaRef']
for fam in C.FAMILIAS:
    p = C.props_familia(fam)
    comprobar([n for n, _ in p] == nombres_writer and 0.4 <= p[1][1] <= 0.6 and 0.4 <= p[0][1] <= 0.6
              and 0.6 <= p[0][1] / p[1][1] <= 1.1, '%s: props %s' % (fam, tuple(v for _, v in p)))
info_t = lambda col, n='MAT_terreno': {'name': n, 'color': col, 'alpha': 1.0, 'img': None}  # noqa: E731
i = C.calibrar(info_t((0.32, 0.45, 0.20)))
c1 = i['color']
comprobar(C.calibrar(i)['color'] == c1, 'idempotente (calibrar dos veces no cambia nada)')
lote = C.calibrar_todos([info_t((0.32, 0.45, 0.20)), {'name': 'MAT_asfalto', 'color': (0.105, 0.102, 0.108), 'alpha': 1,
                                                        'img': None}])
comprobar(np.allclose(lote[0]['color'], c1), 'calibrar(uno) == calibrar_todos(lote)')
comprobar(i['albedo_fuente'] == 'aspecto medido en las vistas de Blender', 'MAT_terreno usa su aspecto medido en las vistas')
r = C.calibrar(info_t(C.ROCA_COLOR, C.ROCA_MAT))
comprobar(r['albedo_fuente'] == 'aspecto medido en las vistas de Blender' and r['tx_ac'][1] / r['tx_ac'][0] < 1.25
          and i['tx_ac'][1] / i['tx_ac'][0] > 1.6,
          'MAT_terreno_roca: objetivo medido y textura gris-roca (%s, G/R %.2f), la hierba sigue verde (%s, G/R %.2f)' % (
              (np.array(r['tx_ac']) * 255).round(), r['tx_ac'][1] / r['tx_ac'][0], (np.array(i['tx_ac']) * 255).round(),
              i['tx_ac'][1] / i['tx_ac'][0]))
jj = C.calibrar(info_t((0.5, 0.5, 0.5)))
comprobar(jj['albedo_fuente'].startswith('diffuse (medida obsoleta') and 'objetivo_ac' in jj,
          'si el material cambia en Blender, las medidas se ignoran (%s)' % jj['albedo_fuente'])

print('3. materiales de la escena congelada')
infos, caras = C._infos_de_volcado(os.path.join(REV, 'materiales.json'))
C.calibrar_todos(infos)
tx = np.array([x['tx_ac'] for x in infos])
techo = np.array([C.FAMILIAS[x['familia']]['techo'] for x in infos])
comprobar(np.isfinite(tx).all() and np.isfinite([x['color'] for x in infos]).all(), '%d materiales sin NaN' % len(infos))
comprobar((tx >= C.SUELO_TX - 1e-9).all() and (tx.max(1) <= techo + 1e-9).all(), 'texturas entre el suelo y el techo')
rep = C.informe(infos, caras)
peores = {f: (v['deltaE_ac_antes'], v['deltaE_ac_despues']) for f, v in rep['familias'].items()
          if v['deltaE_ac_despues'] > v['deltaE_ac_antes'] + 0.5}
comprobar(not peores, 'deltaE gamma frente a Blender no empeora en ninguna familia (%s)' % (peores or 'ninguna peor'))
exceso = []
for x in infos:
    s = C.simular_material(x)
    k = 0 if C.FAMILIAS[x['familia']]['suelo'] else 1
    cb, cd = C.croma(s['blender'][k] / 255), C.croma(s['ac_despues'][k] / 255)
    if cd > C.CROMA_MAX * cb + 2.0 + 3.0:
        exceso.append((x['name'], round(float(cb), 1), round(float(cd), 1)))
comprobar(len(exceso) <= 0.03 * len(infos), 'croma gamma en la cara principal <= 1.08 x Blender + 2 (+3 de margen): '
          '%d fuera %s' % (len(exceso), exceso[:4]))

print('4. ext_config')
with tempfile.TemporaryDirectory() as d:
    rr = os.path.join(d, 'extension', 'ext_config.ini')
    C.generar_ext_config(rr)
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.read(rr, encoding='utf-8')
    comprobar(cp.has_section('LIGHTING') and cp.has_section('BASIC') and not cp.has_section('Material_Water')
              and not cp.has_option('LIGHTING', 'TRACK_AMBIENT_GROUND_MULT') and cp.get('MATERIAL_ADJUSTMENT_0', 'ACTIVE') == '0',
              'INI legible, sin agua de CSP, sin TRACK_AMBIENT_GROUND_MULT y con la palanca apagada: %s' % cp.sections())
    open(rr, 'a', encoding='utf-8').write('\n; AJUSTE A MANO\n')
    C.generar_ext_config(rr)
    dst = C.copiar_ext_config(os.path.join(d, 'pista'), rr)
    comprobar('AJUSTE A MANO' in open(dst, encoding='utf-8').read(),
              'generar_ext_config() no machaca uno editado y copiar_ext_config() lo copia tal cual')
    C.generar_ext_config(rr, agua=True, palanca=True, sobrescribir=True)
    t = open(rr, encoding='utf-8').read()
    comprobar('ACTIVE = 1' in t and '[Material_Water]' in t, 'sobrescribir=True lo regenera con lo pedido (agua, palanca)')
ext = open(C.EXT_ORIGEN, encoding='utf-8').read()
comprobar('[Material_Water]' not in ext and 'ACTIVE = 0' in ext, '04_export/extension/ext_config.ini: sin agua y palanca apagada')

print('5. el parche sigue aplicando sobre los ficheros actuales')
pr = subprocess.run([sys.executable, os.path.join(AQUI, '_color_ac_prueba', 'hacer_parches.py')], capture_output=True, text=True)
comprobar(pr.returncode == 0, 'hacer_parches.py: %s' % (pr.stdout.strip() or pr.stderr.strip()).replace('\n', ' | '))
import prueba_color_ac_b as B  # noqa: E402  (bloques 6 y 7)
B.bloques(comprobar, infos)
print('RESULTADO:', 'OK' if not fallos else 'FALLOS: %d' % len(fallos))
sys.exit(1 if fallos else 0)
