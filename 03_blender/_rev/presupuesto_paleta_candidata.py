# -*- coding: utf-8 -*-
"""presupuesto_paleta_candidata.py - SOLO LECTURA sobre la candidata (nunca guarda): los dos comandos que pide el director
(director_f1_r2.md problema 9 / tabla 16 del plan):
  1) tris de la escena (sin LIB) por familia de prefijo + total, HORIZ_ y vegetacion (VEG_/OLI_), frente a los topes del plan
     (6.0 M tris, 800 mallas, 520 materiales); imagenes distintas usadas por materiales con usuarios.
  2) RGB fuera de paleta.json: para cada material de las familias que manda la paleta (terreno, roca/caliza, teja, fachada,
     vegetacion, horizonte, cesped, tierra) el color que lee el writer (diffuse_color o Base Color sin enlazar) se compara con
     los colores de paleta.json: 'exacto' (dist < 0.01), 'variante' (misma cromatica con factor de luminancia 0.5-1.5, residuo
     relativo < 0.08; paleta.variante() y mezclas de ruido lo producen), 'horizonte' (MAT_HORIZ_: se juzga horiz_color_base),
     o FUERA. Escribe <out>.json y resume por stdout.
  bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/presupuesto_paleta_candidata.py -- <blend> <out.json>
F1 r4 (integrador): escrito en r3 (_tmp_integrador/r3), pasa a _rev/ y lo llama pipeline_escena.sh tras copiar la candidata
(informativo: nunca tumba el pipeline). Es el 'recuento equivalente' de kn5_presupuesto sin 04_export: cuenta tris de Blender
(el writer fusiona mallas por material: 'mallas' aqui no es el n de draw calls del KN5).
"""
import json
import os
import sys

import bpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
BLEND = argv[0]
OUT = argv[1]
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = AQUI
while not os.path.isfile(os.path.join(RAIZ, 'paleta.json')) and os.path.dirname(RAIZ) != RAIZ:
    RAIZ = os.path.dirname(RAIZ)        # 03_blender (donde esta paleta.json), venga de _rev/ o de _rev/_tmp_*/rN/

bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)

# ---------------- 1) tris / mallas / materiales ----------------
lib = bpy.data.collections.get('LIB')
en_lib = set(o.name for o in lib.all_objects) if lib else set()
fam = {}
total = 0
n_mallas = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.name in en_lib:
        continue
    me = ob.data
    tris = sum(max(0, len(p.vertices) - 2) for p in me.polygons)
    if ob.modifiers:
        try:
            me_ev = ob.evaluated_get(dg).to_mesh()
            tris = sum(max(0, len(p.vertices) - 2) for p in me_ev.polygons)
            ob.evaluated_get(dg).to_mesh_clear()
        except Exception:
            pass
    base = ob.name.split('.')[0]
    pref = base.split('_')[0] + '_'
    if base.startswith(('MAT_',)):
        pref = base
    fam[pref] = fam.get(pref, 0) + tris
    total += tris
    n_mallas += 1
mats = [m for m in bpy.data.materials if m.users]
imgs = set()
for m in mats:
    if m.node_tree:
        for n in m.node_tree.nodes:
            if n.bl_idname == 'ShaderNodeTexImage' and n.image:
                imgs.add(n.image.name)
veg = sum(v for k, v in fam.items() if k in ('VEG_', 'OLI_'))
horiz = fam.get('HORIZ_', 0)
top = sorted(fam.items(), key=lambda kv: -kv[1])[:25]
print('PRESUPUESTO candidata: tris (sin LIB) %d (tope 6.0 M: %s) | mallas %d (tope 800: %s; el writer fusiona por material) | '
      'materiales con uso %d (tope 520: %s) | imagenes distintas %d | HORIZ_ %d tris (<= 250 k: %s) | vegetacion VEG_+OLI_ %d tris'
      % (total, 'OK' if total <= 6_000_000 else 'FUERA', n_mallas, 'OK' if n_mallas <= 800 else 'solo Blender (fusion P9)',
         len(mats), 'OK' if len(mats) <= 520 else 'FUERA', len(imgs), horiz, 'OK' if horiz <= 250_000 else 'FUERA', veg))
print('  familias (tris): ' + ', '.join('%s %d' % kv for kv in top))

# ---------------- 2) RGB fuera de paleta ----------------
pal = json.load(open(os.path.join(RAIZ, 'paleta.json'), encoding='utf-8'))
colores = {}
for k, v in pal.get('colores', {}).items():
    if isinstance(v, dict) and 'rgb' in v:
        colores[k] = tuple(float(c) for c in v['rgb'][:3])
for seccion in ('fachadas_propuesta', 'fachadas_actual'):
    for k, v in pal.get(seccion, {}).items():
        if isinstance(v, dict) and 'rgb' in v:
            colores[seccion + '.' + k] = tuple(float(c) for c in v['rgb'][:3])
        elif isinstance(v, (list, tuple)) and len(v) >= 3 and all(isinstance(c, (int, float)) for c in v[:3]):
            colores[seccion + '.' + k] = tuple(float(c) for c in v[:3])

FAMILIAS = ('MAT_terreno', 'MAT_cesped', 'MAT_tierra', 'MAT_arcen', 'MAT_fondo_marino', 'MAT_PPUEBLO_roca', 'MAT_MCOCHE_',
            'MAT_PENON', 'MAT_TUNEL', 'MAT_ROCA', 'MAT_roca', 'MAT_caliza', 'MAT_CASAS_teja', 'MAT_CASAS_fachada', 'MAT_VEG_',
            'MAT_OLI_', 'MAT_HORIZ_', 'MAT_MONT_', 'MAT_LOEWS', 'MAT_bosque', 'MAT_hierba', 'MAT_matorral')


def color_writer(m):
    c = tuple(float(x) for x in m.diffuse_color[:3])
    if m.node_tree:
        pr = next((n for n in m.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
        if pr is not None and not pr.inputs['Base Color'].is_linked:
            c = tuple(float(x) for x in pr.inputs['Base Color'].default_value[:3])
    return c


def hexs(c):
    def s(v):
        v = max(0.0, min(1.0, v))
        v = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        return int(round(v * 255))
    return '#%02X%02X%02X' % tuple(s(v) for v in c)


def clasificar(c):
    mejor = None
    for k, p in colores.items():
        d = sum((a - b) ** 2 for a, b in zip(c, p)) ** 0.5
        if d < 0.01:
            return 'exacto', k, 1.0, d
        pp = sum(b * b for b in p)
        if pp < 1e-9:
            continue
        kf = sum(a * b for a, b in zip(c, p)) / pp
        kf = max(0.5, min(1.5, kf))
        res = sum((a - kf * b) ** 2 for a, b in zip(c, p)) ** 0.5
        nc = max(1e-6, sum(a * a for a in c) ** 0.5)
        rel = res / nc
        if mejor is None or rel < mejor[3]:
            mejor = ('variante' if rel < 0.08 else 'FUERA', k, kf, rel)
    return mejor if mejor else ('FUERA', None, 0.0, 1.0)


res = {'exacto': 0, 'variante': 0, 'horizonte': 0, 'FUERA': []}
detalle = {}
for m in sorted(mats, key=lambda x: x.name):
    if not m.name.startswith(FAMILIAS):
        continue
    if m.name.startswith('MAT_HORIZ_'):
        base = m.get('horiz_color_base')
        if base is not None:
            cl = clasificar(tuple(float(x) for x in base)[:3])
            detalle[m.name] = {'clase': 'horizonte/' + cl[0], 'paleta': cl[1], 'k': round(cl[2], 3), 'hex': hexs(color_writer(m)),
                               'base_hex': hexs(tuple(float(x) for x in base)[:3])}
            res['horizonte'] += 1
            if cl[0] == 'FUERA':
                res['FUERA'].append(m.name)
            continue
    c = color_writer(m)
    cl = clasificar(c)
    detalle[m.name] = {'clase': cl[0], 'paleta': cl[1], 'k': round(cl[2], 3), 'residuo_rel': round(cl[3], 3), 'hex': hexs(c),
                       'rgb': [round(x, 4) for x in c]}
    if cl[0] == 'FUERA':
        res['FUERA'].append(m.name)
    else:
        res[cl[0]] += 1
print('PALETA candidata: %d materiales juzgados: exacto %d, variante %d, horizonte %d, FUERA %d'
      % (len(detalle), res['exacto'], res['variante'], res['horizonte'], len(res['FUERA'])))
for n in res['FUERA']:
    d = detalle[n]
    print('  FUERA %s %s (mas cercano %s k %.2f residuo %.3f)' % (n, d.get('hex'), d.get('paleta'), d.get('k', 0), d.get('residuo_rel', 0)))
json.dump({'blend': BLEND, 'tris_total_sin_lib': total, 'mallas': n_mallas, 'materiales': len(mats), 'imagenes': len(imgs),
           'horiz_tris': horiz, 'veg_tris': veg, 'familias_tris': dict(sorted(fam.items(), key=lambda kv: -kv[1])),
           'paleta_resumen': {k: (v if k != 'FUERA' else len(v)) for k, v in res.items()}, 'paleta_fuera': res['FUERA'],
           'paleta_detalle': detalle},
          open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('PRESUPUESTO_PALETA_OK -> %s' % OUT)
