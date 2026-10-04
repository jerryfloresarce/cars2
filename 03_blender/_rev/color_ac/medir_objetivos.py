# -*- coding: utf-8 -*-
"""medir_objetivos.py - mide en las vistas de AJUSTE (render_ac.py) el aspecto REAL de cada material en nuestro
render de Blender: color mediano en pantalla por clase de cara (suelo/pared x sol/sombra), con su N.L y N.z
medianos, y su albedo medio en la escena (pase alb). Es el objetivo que color_ac.calibrar_todos() reproduce en AC.
Por que: el albedo x luz (v1) no da el aspecto de muchos materiales: el asfalto y el agua brillan por el reflejo
del cielo; las tejas, fachadas o el terreno (hierba + roca) se ven en la escena mas claros o menos saturados que
su albedo medio de laboratorio; la oclusion y el rebote cambian las sombras.
Las vistas de CONTROL (bajada, puente, piloto_s2900) NO se usan aqui: sirven para comprobar que generaliza.
  python 03_blender/_rev/color_ac/medir_objetivos.py
Salida: 04_export/color_ac_objetivos.json  {material: {'color_writer': [...], 'clases': {clase: {...}}, ...}}
"""
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import simular_vistas as S  # noqa: E402

C = S.C
SALIDA = os.path.join(os.path.dirname(C.__file__), 'color_ac_objetivos.json')
MIN_PX = 150             # pixeles minimos de una clase para usarla
MAX_PX = 6000            # muestra maxima por material, clase y vista
CLASES = {               # (N.z minima, N.z maxima, N.L minima, N.L maxima)
    'suelo_sol': (0.5, 1.01, 0.40, 1.01),
    'pared_sol': (-0.3, 0.5, 0.20, 1.01),
    'sombra_pared': (-0.3, 0.5, -1.0, 0.03),
    'sombra_suelo': (0.5, 1.01, -1.0, 0.03),
}


def main():
    rng = np.random.default_rng(1)
    acum = {}
    for v in S.META['ajuste']:
        d = S.cargar(v)
        for clase, (z0, z1, l0, l1) in CLASES.items():
            m = d['valido'] & (d['nz'] >= z0) & (d['nz'] < z1) & (d['nl'] >= l0) & (d['nl'] < l1)
            ys, xs = np.nonzero(m)
            ids = d['idx'][ys, xs]
            orden = np.argsort(ids, kind='stable')
            ids, ys, xs = ids[orden], ys[orden], xs[orden]
            cortes = np.flatnonzero(np.diff(ids)) + 1
            for grupo in np.split(np.arange(len(ids)), cortes):
                if len(grupo) < 30:
                    continue
                if len(grupo) > MAX_PX:
                    grupo = rng.choice(grupo, MAX_PX, replace=False)
                i = int(ids[grupo[0]])
                y, x = ys[grupo], xs[grupo]
                a = acum.setdefault(i, {}).setdefault(clase, {'ref': [], 'nl': [], 'nz': [], 'alb': [], 'vistas': set()})
                a['ref'].append(d['ref'][y, x])
                a['nl'].append(d['nl'][y, x])
                a['nz'].append(d['nz'][y, x])
                a['alb'].append(d['alb'][y, x, :3])
                a['vistas'].add(v)
        print('vista', v, 'materiales con datos:', len(acum))
    out = {'version': C.VERSION, 'vistas': S.META['ajuste'], 'min_pixeles': MIN_PX, 'materiales': {}}
    for i, clases in sorted(acum.items()):
        mat = S.MATS[i]
        ent = {'color_writer': [round(float(c), 5) for c in mat['color']], 'familia': C.familia(mat['name']),
               'clases': {}}
        albs = []
        for clase, a in clases.items():
            ref = np.concatenate(a['ref'])
            if len(ref) < MIN_PX:
                continue
            ent['clases'][clase] = {'rgb': np.round(np.median(ref, 0), 4).tolist(),
                                    'nl': round(float(np.median(np.concatenate(a['nl']))), 3),
                                    'nz': round(float(np.median(np.concatenate(a['nz']))), 3),
                                    'pixeles': int(len(ref)), 'vistas': sorted(a['vistas'])}
            albs.append(np.concatenate(a['alb']))
        if ent['clases']:
            ent['albedo_escena'] = np.round(np.mean(np.concatenate(albs), 0), 4).tolist()
            out['materiales'][mat['name']] = ent
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print('OK %d materiales con objetivo medido -> %s' % (len(out['materiales']), SALIDA))
    for n in S.MUESTRAS:
        if n in out['materiales']:
            print(' ', n, {k: (c['rgb'], c['pixeles']) for k, c in out['materiales'][n]['clases'].items()})


if __name__ == '__main__':
    main()
