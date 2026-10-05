# -*- coding: utf-8 -*-
"""banda_terreno_2m.py - F1 r4 (ACOTACIONES_COORDINADOR_F1.md 4; PARCHES_F1_mascara.md ronda 4): paso FINAL del pipeline.
Subdivide a 2 m el TERRENO en la banda de 20 m junto al asfalto (construir_pista.subdividir_banda_terreno) y vuelve a aplicar
el umbral nz < 0.62 sin dientes en la cima de 56 y a < 150 m de 51/07 (construir_pista.roca_zonas_nz) sobre la malla ya
subdividida. Se ejecuta DESPUES de asentar_objetos / revisar_* / nada_en_pista y ANTES de copiar_candidata: hasta aqui el
TERRENO es la rejilla nx*ny (plan 15.7); a partir de aqui tiene nx*ny + ~38 k vertices (los nx*ny primeros no cambian de
indice) y los inspectores que exigen len(vertices) == nx*ny caerian al z del JSON (por eso va el ultimo).
  bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/banda_terreno_2m.py [-- --blend <in.blend> --out <out.blend> --json <cifras.json>]
Sin argumentos: abre y guarda 03_blender/porto_corsa.blend (solo el integrador, dentro de pipeline_escena.sh). Idempotente.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

import bpy
import numpy as np

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
D3 = BASE + r'\03_blender'
if D3 not in sys.path:
    sys.path.insert(0, D3)
import paleta  # noqa: E402
try:
    import mascara_terreno as _mt  # noqa: E402
except Exception as e:
    print('AVISO: mascara_terreno no importable (%s): constantes por defecto' % e)
    _mt = None

ap = argparse.ArgumentParser()
ap.add_argument('--blend', default=os.path.join(D3, 'porto_corsa.blend'))
ap.add_argument('--out', default=None, help='defecto: el mismo fichero')
ap.add_argument('--json', default=os.path.join(D3, 'renders', 'qa', 'banda_terreno_2m.json'))
A = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
blend_in = os.path.abspath(A.blend)
blend_out = os.path.abspath(A.out) if A.out else blend_in
assert 'escena_rev.blend' not in blend_out.lower(), 'nunca sobre escena_rev.blend'

G = json.load(open(os.environ.get('GEOM', os.path.join(D3, 'geometria_3d.json')), encoding='utf-8'))
DIR_TEX = os.path.join(D3, 'texturas')
src = open(os.path.join(D3, 'construir_pista.py'), encoding='utf-8').read()
i_mat, i_masf = src.index('def mat(name, rgba'), src.index('M_ASF = mat_con_ruido')
a, b = src.index('# >>> MATERIAL TERRENO v2'), src.index('# <<< MATERIAL TERRENO v2')
ns = {'bpy': bpy, 'math': math, 'os': os, 'np': np, 'G': G, 'BASE': BASE, 'DIR_TEX': DIR_TEX, 'paleta': paleta, '_mt': _mt,
      'DIR_MASCARA': os.environ.get('MASCARA_DIR', DIR_TEX), 'sys': sys, 'subprocess': subprocess}
exec(src[i_mat:i_masf], ns)
exec(src[a:b], ns)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=blend_in)
ter = bpy.data.objects.get('TERRENO')
if ter is None or ter.type != 'MESH':
    print('BANDA_2M: sin TERRENO: nada que hacer')
    sys.exit(0)
n0 = len(ter.data.vertices)
res = {'blend': blend_in, 'vertices_antes': n0}
s4 = ns['subdividir_banda_terreno'](ter)
if s4 is None:
    print('BANDA_2M: ya aplicada o no procede (%s): no se guarda' % dict(ter.get('banda_2m', {})))
    sys.exit(0)
res['banda'] = s4
z4 = ns['roca_zonas_nz'](ter)
res['zonas'] = z4
me = ter.data
print('BANDA_2M: banda %.0f m | celdas %d | vertices %d -> %d (+%d) | tris %d -> %d | canal A en los medios %s | %.1f s'
      % (s4['banda_m'], s4['celdas'], s4['vertices_antes'], s4['vertices_despues'], s4['vertices_nuevos'], s4['tris_antes'],
         s4['tris_despues'], s4['canal_a_en_medios'], time.time() - t0))
if z4:
    print('BANDA_2M zonas nz < %.2f: caras de roca AC %d -> %d | dientes %d -> %d | huecos %d -> %d'
          % (z4['nz_zona'], z4['global']['roca_antes'], z4['global']['roca_despues'], z4['global']['dientes_antes'],
             z4['global']['dientes_despues'], z4['global']['huecos_antes'], z4['global']['huecos_despues']))
    for nm, zz in z4['zonas'].items():
        print('   zona %-22s roca %4d -> %4d | dientes %3d -> %3d | huecos %2d -> %2d' % (
            nm, zz['roca_antes'], zz['roca_despues'], zz['dientes_antes'], zz['dientes_despues'], zz['huecos_antes'], zz['huecos_despues']))
vr = np.empty(len(me.vertices), np.float32)
me.attributes['roca'].data.foreach_get('value', vr)
res['atributo_roca'] = {'vertices': int(len(vr)), 'media': round(float(vr.mean()), 4), 'pct_gt_0_49': round(100.0 * float((vr > 0.49).mean()), 2)}
print('BANDA_2M atributo roca: %d vertices, media %.3f, > 0.49 en el %.1f %%' % (len(vr), vr.mean(), 100.0 * (vr > 0.49).mean()))
# rutas absolutas (como construir_pista r2): nunca '//'
for im in bpy.data.images:
    if (im.filepath or '').startswith('//'):
        im.filepath = os.path.normpath(os.path.join(D3, im.filepath[2:]))
os.makedirs(os.path.dirname(blend_out), exist_ok=True)
if blend_out == blend_in:
    bpy.ops.wm.save_mainfile(filepath=blend_out, relative_remap=False)
else:
    bpy.ops.wm.save_as_mainfile(filepath=blend_out, copy=True, relative_remap=False)
rel = [im.name for im in bpy.data.images if (im.filepath or '').startswith('//')]
res['rutas_relativas'] = rel
try:
    os.makedirs(os.path.dirname(A.json), exist_ok=True)
    json.dump(res, open(A.json, 'w', encoding='utf-8'), indent=1, default=str)
except Exception as e:
    print('AVISO: no se pudo escribir %s (%s)' % (A.json, e))
print('OK banda_terreno_2m -> %s (%.1f MB, %.0f s)%s' % (blend_out, os.path.getsize(blend_out) / 1e6, time.time() - t0,
                                                         '' if not rel else ' AVISO rutas relativas: %s' % rel[:5]))
if rel:
    sys.exit(1)
