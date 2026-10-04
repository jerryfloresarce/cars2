#!/usr/bin/env python3
"""kn5_presupuesto.py -- presupuesto duro del KN5 (plan de la fase visual, decision 8 / plan B secc. 0 y 1.4).

Lee el informe JSON de 04_export/kn5_check.py (claves totales, mallas, materiales, texturas) y FALLA (exit 1) si se supera
un tope: tris <= 6.0 M, mallas <= 800, materiales <= 520, texturas <= 80 MB, KN5 <= 450 MB. Con --base compara familias
(prefijo fisico de malla, familia de material MAT_X) y AVISA (no falla) si una crece > 50 % en tris, mallas, materiales o
bytes de textura; --estricto convierte los avisos en fallos.
  python 03_blender/_rev/kn5_presupuesto.py <informe_check.json> [--base 04_export/kn5/informe_check_opt.json] [--json salida.json] [--estricto]
  Base por defecto: 04_export/kn5/informe_check_opt.json (zip v1.0, 02/10) si existe, si no 04_export/_fisica/informe_check_fisica.json.
  Sin bpy: python del sistema. Codigos de salida: 0 dentro del presupuesto, 1 tope superado (o aviso con --estricto), 2 error de lectura.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys

EXPORT = r'E:\Escritorio\claude-pc\arnau-aseto-corsa\04_export'
BASES_DEFECTO = (os.path.join(EXPORT, 'kn5', 'informe_check_opt.json'),
                 os.path.join(EXPORT, '_fisica', 'informe_check_fisica.json'))
TOPES = {  # clave del informe -> (tope, etiqueta, divisor para imprimir, unidad)
    'total_triangulos': (6_000_000, 'triangulos', 1e6, 'M'),
    'n_mallas': (800, 'mallas (draw calls)', 1, ''),
    'n_materiales': (520, 'materiales', 1, ''),
    'bytes_texturas': (80 * 1024 * 1024, 'bytes de texturas en el KN5', 1024 * 1024, 'MB'),
    'bytes_fichero': (450 * 1024 * 1024, 'bytes del KN5', 1024 * 1024, 'MB'),
}
CRECIMIENTO_MAX = 0.50      # +50 % respecto a la base dispara el aviso
MIN_TRIS_FAMILIA = 20_000   # familias mas pequenas no se avisan por tris (ruido)
MIN_BYTES_FAMILIA = 512 * 1024
FAMILIAS_VEG = ('MAT_VEG', 'MAT_OLI')   # informativo: tris de vegetacion (objetivo del plan <= 0.9 M)


def familia_malla(nombre: str) -> str:
    """prefijo fisico/decorativo de la malla: 1ROAD, 1WALL, DECO, 1GRASS, AC, AGUA..."""
    return nombre.split('_', 1)[0] if '_' in nombre else nombre


def familia_material(nombre: str) -> str:
    """MAT_CAMINO_tierra -> MAT_CAMINO; MAT_asfalto -> MAT_asfalto; otro -> primer token."""
    m = re.match(r'^(MAT_[A-Za-z0-9]+)', nombre)
    return m.group(1) if m else nombre.split('_', 1)[0]


def cargar(ruta: str) -> dict:
    inf = json.load(open(ruta, encoding='utf-8'))
    for k in ('totales', 'mallas', 'materiales', 'texturas'):
        if k not in inf:
            raise ValueError('el informe %s no tiene la clave "%s" (no es un informe de kn5_check)' % (ruta, k))
    return inf


def resumir(inf: dict) -> dict:
    """tris/mallas por prefijo de malla, tris/mallas/materiales por familia MAT_, bytes de textura por familia MAT_."""
    mats = inf['materiales']
    mat_por_id = {m['indice']: m['nombre'] for m in mats}
    tex_bytes = {t['nombre']: int(t.get('tamano', 0)) for t in inf['texturas']}
    r = {'pref_tris': collections.Counter(), 'pref_mallas': collections.Counter(),
         'mat_tris': collections.Counter(), 'mat_mallas': collections.Counter(), 'mat_n': collections.Counter(),
         'mat_tex_bytes': collections.Counter()}
    for m in inf['mallas']:
        nombre = m['ruta'].split('/')[-1]
        tris = int(m.get('n_triangulos', 0))
        pf = familia_malla(nombre)
        r['pref_tris'][pf] += tris
        r['pref_mallas'][pf] += 1
        fm = familia_material(mat_por_id.get(m.get('materialId'), '?'))
        r['mat_tris'][fm] += tris
        r['mat_mallas'][fm] += 1
    vistas = set()
    for m in mats:
        fm = familia_material(m['nombre'])
        r['mat_n'][fm] += 1
        for s in m.get('samplers', []) or []:
            tn = s.get('textura') or s.get('nombre_textura') or s.get('texture')
            if tn and tn in tex_bytes and (fm, tn) not in vistas:
                vistas.add((fm, tn))
                r['mat_tex_bytes'][fm] += tex_bytes[tn]
    if not r['mat_tex_bytes']:   # el informe no enlaza samplers con texturas: por nombre de fichero (flat_MAT_X..., tex_MAT_X...)
        for tn, b in tex_bytes.items():
            mm = re.search(r'(MAT_[A-Za-z0-9]+)', tn)
            r['mat_tex_bytes'][mm.group(1) if mm else 'otras'] += b
    r['veg_tris'] = sum(r['mat_tris'][f] for f in r['mat_tris'] if f.startswith(FAMILIAS_VEG))
    return r


def evaluar(ruta: str, base: str | None = None) -> dict:
    """Devuelve {ok, fallos, avisos, totales, familias, base}. ok = sin topes superados (los avisos no cuentan)."""
    inf = cargar(ruta)
    tot = inf['totales']
    fallos, avisos, info = [], [], []
    totales = {}
    for k, (tope, etiqueta, div, uni) in TOPES.items():
        val = tot.get(k)
        if val is None:
            avisos.append('el informe no trae totales.%s' % k)
            continue
        totales[k] = {'valor': val, 'tope': tope, 'pct': round(100.0 * val / tope, 1)}
        txt = '%s: %.2f %s de %.2f %s (%.0f %%)' % (etiqueta, val / div, uni, tope / div, uni, 100.0 * val / tope) if div != 1 \
            else '%s: %d de %d (%.0f %%)' % (etiqueta, val, tope, 100.0 * val / tope)
        if val > tope:
            fallos.append('TOPE SUPERADO ' + txt)
        else:
            info.append(txt)
    r = resumir(inf)
    totales['veg_tris'] = r['veg_tris']
    info.append('tris de vegetacion (%s): %.2f M (objetivo del plan <= 0.9 M)' % ('+'.join(FAMILIAS_VEG), r['veg_tris'] / 1e6))
    comprob = [c for c in inf.get('comprobaciones', []) if not c.get('ok', True)]
    if inf.get('resultado') not in (None, 'OK'):
        fallos.append('kn5_check resultado %s (%d comprobaciones fallan)' % (inf.get('resultado'), len(comprob)))

    familias = {}
    rb = None
    if base:
        if not os.path.isfile(base):
            avisos.append('informe base no encontrado: %s (sin comparacion por familias)' % base)
        else:
            rb = resumir(cargar(base))
            for etiqueta, clave, minimo in (('tris por prefijo de malla', 'pref_tris', MIN_TRIS_FAMILIA),
                                            ('mallas por prefijo', 'pref_mallas', 20),
                                            ('tris por familia MAT_', 'mat_tris', MIN_TRIS_FAMILIA),
                                            ('mallas por familia MAT_', 'mat_mallas', 10),
                                            ('materiales por familia MAT_', 'mat_n', 10),
                                            ('bytes de textura por familia MAT_', 'mat_tex_bytes', MIN_BYTES_FAMILIA)):
                tabla = {}
                for fam in sorted(set(r[clave]) | set(rb[clave])):
                    a, b = int(r[clave].get(fam, 0)), int(rb[clave].get(fam, 0))
                    tabla[fam] = [b, a]
                    if a < minimo:
                        continue
                    if b == 0:
                        avisos.append('%s: familia NUEVA %s = %d' % (etiqueta, fam, a))
                    elif a > b * (1 + CRECIMIENTO_MAX):
                        avisos.append('%s: %s crece %+.0f %% (%d -> %d)' % (etiqueta, fam, 100.0 * (a - b) / b, b, a))
                familias[clave] = tabla
    else:
        for clave in ('pref_tris', 'mat_tris', 'mat_n', 'mat_tex_bytes'):
            familias[clave] = {fam: [None, int(n)] for fam, n in r[clave].most_common()}
    return {'ok': not fallos, 'fichero': inf.get('fichero'), 'generado': inf.get('generado'), 'base': base if rb else None,
            'fallos': fallos, 'avisos': avisos, 'info': info, 'totales': totales, 'familias': familias}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('informe', help='informe_check.json de kn5_check.py')
    ap.add_argument('--base', default=None, help='informe de referencia para el aviso de familias (+50 %%)')
    ap.add_argument('--sin-base', action='store_true', help='no comparar con ninguna base')
    ap.add_argument('--json', default=None, help='guarda el resultado en este json')
    ap.add_argument('--estricto', action='store_true', help='los avisos de familias tambien fallan')
    ap.add_argument('--top', type=int, default=12, help='familias que se imprimen por tabla')
    a = ap.parse_args(argv)
    base = a.base
    if base is None and not a.sin_base:
        base = next((b for b in BASES_DEFECTO if os.path.isfile(b) and os.path.abspath(b) != os.path.abspath(a.informe)), None)
    try:
        res = evaluar(a.informe, base)
    except Exception as e:
        print('ERROR leyendo el informe:', repr(e))
        return 2
    print('kn5_presupuesto: %s (%s)%s' % (res['fichero'], res['generado'], ('  base: ' + res['base']) if res['base'] else '  (sin base)'))
    for t in res['info']:
        print('  ', t)
    for clave, etiqueta in (('pref_tris', 'tris por prefijo'), ('mat_tris', 'tris por familia MAT_'), ('mat_tex_bytes', 'bytes textura por familia')):
        tabla = res['familias'].get(clave) or {}
        filas = sorted(tabla.items(), key=lambda kv: -(kv[1][1] or 0))[:a.top]
        print('  %s: %s' % (etiqueta, ', '.join('%s %s%s' % (f, ('%d->' % b) if b is not None else '', v) for f, (b, v) in filas)))
    for w in res['avisos']:
        print('  AVISO:', w)
    for f in res['fallos']:
        print('  FALLO:', f)
    if a.json:
        json.dump(res, open(a.json, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print('  ->', a.json)
    ok = res['ok'] and not (a.estricto and res['avisos'])
    print('RESULTADO: %s' % ('OK dentro del presupuesto' if ok else 'FALLO (presupuesto superado)'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
