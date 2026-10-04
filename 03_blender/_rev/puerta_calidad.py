#!/usr/bin/env python3
"""puerta_calidad.py -- puerta de calidad de la escena CANDIDATA (fase visual, bloque 0, plan secc. 1 criterio 3).

Lee SOLO json y logs (nunca abre Blender) y escribe _rev/puerta.json {ok, motivos, avisos, valores, diff}.
  python 03_blender/_rev/puerta_calidad.py                          # juzga la candidata (_rev/candidata.json -> logs + *_candidata.json)
  python 03_blender/_rev/puerta_calidad.py --qa renders/qa --logs _rev/logs_final [--blend X.blend]   # juzga esos datos sueltos
  python 03_blender/_rev/puerta_calidad.py --qa renders/qa --logs _rev/logs_final --snapshot _rev/linea_base.json   # congela la base
  Opciones: --base linea_base.json (defecto _rev/linea_base.json), --out puerta.json (defecto _rev/puerta.json),
            --kn5 informe_check.json (ademas pasa kn5_presupuesto: topes), --quiet.
Fuentes: urbanismo.log (QA del plan: fallos 0, casas >= 190), urbanismo_informe.json (revisar_urbanismo: <= base, 0 nuevos
casa_pista/casa_muro/losa*), nada_en_pista.json (<= base, 0 en tierra), asentar.json (resumen no peor que la base),
preparar_geometria.log (celdas_invaden_pista 0, hierba_asfalto 0, fosos 0 muestras > 1.5 m, costuras no peores, loews 0.000),
integrar_escena.log ("ERRORES: ninguno", casas >= 190). Codigos de salida: 0 ok, 1 no pasa, 2 error de uso.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys

RAIZ = r'E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender'
REV = os.path.join(RAIZ, '_rev')
MIN_CASAS = 190
# tipos de fallo de revisar_urbanismo que bloquean si aparece UNO nuevo respecto a la base (prefijos)
TIPOS_BLOQUEANTES = ('casa_pista', 'casa_muro', 'losa')
# claves del resumen de asentar.json que no pueden empeorar (crecer) respecto a la base
ASENTAR_NO_PEOR = ('arboles_quitados', 'flotaban_mas_0_6', 'enterrados_mas_0_6', 'saltos', 'bajo_mar', 'sin_impacto',
                   'fuera_del_terreno', 'edificios_flotantes', 'edificios_enterrados', 'edificios_sin_suelo',
                   'losas_con_aire', 'bancales_mal', 'coches_quitados', 'dentro_de_muro_quitados')
TOL_COSTURAS_M = 0.05   # redondeo del log (2 decimales)


def _p(*a):
    print(*a)


def md5_fichero(ruta: str) -> str | None:
    if not ruta or not os.path.isfile(ruta):
        return None
    h = hashlib.md5()
    with open(ruta, 'rb') as f:
        for trozo in iter(lambda: f.read(1 << 20), b''):
            h.update(trozo)
    return h.hexdigest()


def leer_json(ruta: str, motivos: list[str], etiqueta: str):
    if not ruta or not os.path.isfile(ruta):
        motivos.append('falta %s (%s)' % (etiqueta, ruta))
        return None
    try:
        return json.load(open(ruta, encoding='utf-8'))
    except Exception as e:  # json roto = no pasa
        motivos.append('%s ilegible (%s): %r' % (etiqueta, ruta, e))
        return None


def leer_texto(ruta: str, motivos: list[str], etiqueta: str) -> str | None:
    if not ruta or not os.path.isfile(ruta):
        motivos.append('falta %s (%s)' % (etiqueta, ruta))
        return None
    return open(ruta, encoding='utf-8', errors='replace').read()


# ----------------------------------------------------------------------------------------------- extraccion de valores
def valores_urbanismo_log(txt: str | None, v: dict, motivos: list[str]):
    """QA del plan urbano (urbanismo.py): linea '[urbanismo] QA: {...}' y 'TOTAL casas N'."""
    if txt is None:
        return
    m = re.search(r'\[urbanismo\] QA: (\{.*\})', txt)
    if not m:
        motivos.append('urbanismo.log sin linea "[urbanismo] QA: {...}" (el plan no termino)')
        return
    try:
        qa = json.loads(m.group(1))
    except Exception as e:
        motivos.append('urbanismo.log: QA ilegible: %r' % e)
        return
    fallos = qa.get('fallos', {}) or {}
    v['urbanismo_plan_fallos'] = int(sum(int(x) for x in fallos.values()))
    v['urbanismo_plan_fallos_por_tipo'] = {k: int(x) for k, x in fallos.items() if int(x)}
    v['urbanismo_plan_casas'] = int(qa.get('casas_total', 0))
    v['urbanismo_plan_huecos_m'] = round(float(qa.get('huecos_suma_m', 0.0)), 1)
    v['urbanismo_plan_terrazas_vacias'] = len(qa.get('terrazas_vacias', []) or [])
    m2 = re.search(r'TOTAL casas (\d+)', txt)
    if m2:
        v['urbanismo_plan_casas_total_linea'] = int(m2.group(1))


def valores_informe(inf: dict | None, v: dict):
    """revisar_urbanismo.py -> urbanismo_informe.json."""
    if inf is None:
        return
    v['revisar_urbanismo_fallos'] = int(inf.get('total_fallos', -1))
    v['revisar_urbanismo_por_tipo'] = {k: int(x) for k, x in (inf.get('resumen') or {}).items()}
    v['revisar_urbanismo_avisos'] = int(inf.get('total_avisos', 0))
    v['revisar_urbanismo_n_casas_huella'] = int((inf.get('n_huellas') or {}).get('casas', 0))


def valores_nada(nada: dict | None, v: dict):
    if nada is None:
        return
    fallos = nada.get('fallos', []) or []
    v['nada_en_pista'] = int(nada.get('n', len(fallos)))
    v['nada_en_pista_tierra'] = int(sum(1 for f in fallos if f.get('sec') == 'dirt'))
    v['nada_en_pista_objetos'] = sorted(f.get('objeto', '?') for f in fallos)


def valores_asentar(asentar: dict | None, v: dict):
    if asentar is None:
        return
    res = asentar.get('resumen') or {}
    v['asentar'] = {k: res.get(k) for k in ASENTAR_NO_PEOR if k in res}
    v['asentar_movidos'] = res.get('movidos')
    v['asentar_candidatos'] = res.get('candidatos')


def valores_terreno(txt: str | None, v: dict, motivos: list[str]):
    """checks de terreno_montana.construir que preparar_geometria imprime en su log (no van al geometria_3d.json)."""
    if txt is None:
        return
    m = re.search(r'celdas que invaden la pista: (\d+) \(viaducto: (\d+)\)', txt)
    if m:
        v['terreno_celdas_invaden_pista'] = int(m.group(1))
        v['terreno_celdas_invaden_viaducto'] = int(m.group(2))
    else:
        motivos.append('preparar_geometria.log sin "celdas que invaden la pista"')
    m = re.search(r'hierba sobre el asfalto[^\n]*?: (\d+) puntos > 2 cm \(max ([-\d.]+) m\) -> (\d+) \(max ([-\d.]+) m\)', txt)
    if m:
        v['terreno_hierba_asfalto_antes'] = int(m.group(1))
        v['terreno_hierba_asfalto'] = int(m.group(3))
        v['terreno_hierba_asfalto_max_m'] = float(m.group(4))
    else:
        motivos.append('preparar_geometria.log sin "hierba sobre el asfalto"')
    fosos = re.findall(r'foso tras la ultima terraza (\S+)\s+(\d+) de\s+(\d+) muestras > 1\.5 m', txt)
    if fosos:
        v['terreno_fosos_gt_1p5_por_sector'] = {s: int(n) for s, n, _ in fosos}
        v['terreno_fosos_gt_1p5'] = int(sum(int(n) for _, n, _ in fosos))
    else:
        motivos.append('preparar_geometria.log sin "foso tras la ultima terraza"')
    m = re.search(r'COSTURAS[^\n]*?: max ([\d.]+) m; celdas > 0\.3: (\d+), > 0\.6: (\d+)', txt)
    if m:
        v['terreno_costuras_max_m'] = float(m.group(1))
        v['terreno_costuras_celdas_gt_0p3'] = int(m.group(2))
        v['terreno_costuras_celdas_gt_0p6'] = int(m.group(3))
    else:
        motivos.append('preparar_geometria.log sin linea COSTURAS')
    sect = re.findall(r'^\s+(\S+)\s+costuras max ([\d.]+) m \(> 0\.6: (\d+) celdas', txt, re.M)
    if sect:
        v['terreno_costuras_por_sector'] = {s: [float(mx), int(n)] for s, mx, n in sect}
    m = re.search(r'\|z - referencia\| a < 40 m: ([\d.]+) m', txt)
    if m:
        v['terreno_loews_ref_dz_max'] = float(m.group(1))
    else:
        motivos.append('preparar_geometria.log sin "|z - referencia| a < 40 m" (Loews)')
    m = re.search(r'pendiente max ([\d.]+)%', txt)
    if m:
        v['pista_pendiente_max_pct'] = float(m.group(1))
    m = re.search(r'alturas: min ([\d.]+) max ([\d.]+)', txt)
    if m:
        v['pista_z_max'] = float(m.group(2))
    v['preparar_geometria_ok'] = bool(re.search(r'^OK -> ', txt, re.M))


def valores_integrar(txt: str | None, v: dict, motivos: list[str]):
    if txt is None:
        return
    m = re.search(r'^ERRORES: (.*)$', txt, re.M)
    v['integrar_errores'] = m.group(1).strip() if m else None
    if not m:
        motivos.append('integrar_escena.log sin linea "ERRORES:" (no termino)')
    m = re.search(r'\[integrar\] urbanismo: (\d+) casas', txt)
    if m:
        v['integrar_casas'] = int(m.group(1))
    else:
        motivos.append('integrar_escena.log sin "[integrar] urbanismo: N casas"')
    m = re.search(r'despeje final: .*?quitados (\d+) arboles y (\d+) props', txt)
    if m:
        v['integrar_despeje_arboles_quitados'] = int(m.group(1))
        v['integrar_despeje_props_quitados'] = int(m.group(2))


# ----------------------------------------------------------------------------------------------- reglas
def juzgar(v: dict, base: dict | None, motivos: list[str], avisos: list[str], diff: dict):
    """Aplica el criterio 3 de la seccion 1 del plan. Anade motivos (bloquean) y avisos (no bloquean)."""
    b = (base or {}).get('valores', {}) if base else {}

    def d(clave, regla):
        if clave in v or clave in b:
            diff[clave] = {'base': b.get(clave), 'candidata': v.get(clave), 'regla': regla}

    # 1. plan urbano (urbanismo.py): 0 fallos y >= 190 casas
    d('urbanismo_plan_fallos', '== 0')
    d('urbanismo_plan_casas', '>= %d' % MIN_CASAS)
    if 'urbanismo_plan_fallos' in v and v['urbanismo_plan_fallos'] != 0:
        motivos.append('urbanismo.py: %d fallos del plan (%s); debe ser 0' % (v['urbanismo_plan_fallos'], v.get('urbanismo_plan_fallos_por_tipo')))
    if 'urbanismo_plan_casas' in v and v['urbanismo_plan_casas'] < MIN_CASAS:
        motivos.append('urbanismo.py: %d casas < %d' % (v['urbanismo_plan_casas'], MIN_CASAS))

    # 2. revisar_urbanismo: <= base y 0 nuevos de los tipos bloqueantes
    d('revisar_urbanismo_fallos', '<= base')
    if 'revisar_urbanismo_fallos' in v:
        bf = b.get('revisar_urbanismo_fallos')
        if bf is not None and v['revisar_urbanismo_fallos'] > bf:
            motivos.append('revisar_urbanismo: %d fallos > base %d' % (v['revisar_urbanismo_fallos'], bf))
        bt = b.get('revisar_urbanismo_por_tipo', {}) or {}
        ct = v.get('revisar_urbanismo_por_tipo', {}) or {}
        for tipo, n in sorted(ct.items()):
            if tipo.startswith(TIPOS_BLOQUEANTES) and n > int(bt.get(tipo, 0)):
                motivos.append('revisar_urbanismo: %d fallos "%s" (base %d): tipo bloqueante, 0 nuevos permitidos' % (n, tipo, int(bt.get(tipo, 0))))
        nuevos = {t: n for t, n in ct.items() if t not in bt}
        if nuevos:
            avisos.append('revisar_urbanismo: tipos de fallo nuevos respecto a la base: %s' % nuevos)
        d('revisar_urbanismo_por_tipo', 'casa_pista/casa_muro/losa* <= base')

    # 3. nada_en_pista: <= base (11) y 0 en tierra
    d('nada_en_pista', '<= base')
    d('nada_en_pista_tierra', '== 0')
    if 'nada_en_pista' in v:
        bn = b.get('nada_en_pista')
        if bn is not None and v['nada_en_pista'] > bn:
            motivos.append('nada_en_pista: %d objetos invasores > base %d' % (v['nada_en_pista'], bn))
        if v.get('nada_en_pista_tierra', 0) != 0:
            motivos.append('nada_en_pista: %d objetos sobre la tierra (debe ser 0)' % v['nada_en_pista_tierra'])
        if bn is not None and set(v.get('nada_en_pista_objetos', [])) - set(b.get('nada_en_pista_objetos', [])):
            avisos.append('nada_en_pista: objetos distintos de los de la base: %s'
                          % sorted(set(v.get('nada_en_pista_objetos', [])) - set(b.get('nada_en_pista_objetos', []))))

    # 4. asentar.json: resumen no peor que la base
    if 'asentar' in v:
        ba = b.get('asentar', {}) or {}
        for k, val in v['asentar'].items():
            diff['asentar.' + k] = {'base': ba.get(k), 'candidata': val, 'regla': '<= base'}
            if val is not None and ba.get(k) is not None and val > ba[k]:
                motivos.append('asentar: %s = %s peor que la base %s' % (k, val, ba[k]))

    # 5. checks del terreno
    d('terreno_celdas_invaden_pista', '== 0')
    d('terreno_hierba_asfalto', '== 0')
    d('terreno_fosos_gt_1p5', '== 0')
    d('terreno_costuras_max_m', '<= base + %.2f' % TOL_COSTURAS_M)
    d('terreno_costuras_celdas_gt_0p6', '<= base')
    d('terreno_loews_ref_dz_max', '== 0.000')
    if v.get('terreno_celdas_invaden_pista', 0) != 0:
        motivos.append('terreno: %d celdas invaden la pista (debe ser 0)' % v['terreno_celdas_invaden_pista'])
    if v.get('terreno_hierba_asfalto', 0) != 0:
        motivos.append('terreno: hierba sobre el asfalto en %d puntos (debe ser 0)' % v['terreno_hierba_asfalto'])
    if v.get('terreno_fosos_gt_1p5', 0) != 0:
        motivos.append('terreno: %d muestras con foso > 1.5 m tras la ultima terraza (debe ser 0): %s'
                       % (v['terreno_fosos_gt_1p5'], {s: n for s, n in v.get('terreno_fosos_gt_1p5_por_sector', {}).items() if n}))
    if 'terreno_costuras_max_m' in v:
        bc = b.get('terreno_costuras_max_m')
        if bc is not None and v['terreno_costuras_max_m'] > bc + TOL_COSTURAS_M:
            motivos.append('terreno: costuras max %.2f m > base %.2f m' % (v['terreno_costuras_max_m'], bc))
        bc6 = b.get('terreno_costuras_celdas_gt_0p6')
        if bc6 is not None and v.get('terreno_costuras_celdas_gt_0p6', 0) > bc6:
            motivos.append('terreno: %d celdas con costura > 0.6 m > base %d' % (v['terreno_costuras_celdas_gt_0p6'], bc6))
        if v['terreno_costuras_max_m'] >= 0.6:
            avisos.append('terreno: costuras max %.2f m (objetivo del plan < 0.6; hoy la base ya lo supera, se exige "no peor")'
                          % v['terreno_costuras_max_m'])
    if 'terreno_loews_ref_dz_max' in v and abs(v['terreno_loews_ref_dz_max']) > 0.0005:
        motivos.append('terreno: Loews |z - referencia| = %.3f m (debe ser 0.000)' % v['terreno_loews_ref_dz_max'])
    if 'preparar_geometria_ok' in v and not v['preparar_geometria_ok']:
        motivos.append('preparar_geometria.log sin "OK -> geometria_3d.json"')

    # 6. integrar_escena
    d('integrar_errores', '== ninguno')
    d('integrar_casas', '>= %d' % MIN_CASAS)
    if 'integrar_errores' in v and v['integrar_errores'] is not None and v['integrar_errores'] != 'ninguno':
        motivos.append('integrar_escena: ERRORES: %s' % v['integrar_errores'][:300])
    if 'integrar_casas' in v and v['integrar_casas'] < MIN_CASAS:
        motivos.append('integrar_escena: %d casas < %d' % (v['integrar_casas'], MIN_CASAS))
    if 'integrar_despeje_arboles_quitados' in v and b.get('integrar_despeje_arboles_quitados') is not None \
            and v['integrar_despeje_arboles_quitados'] > 1.5 * b['integrar_despeje_arboles_quitados'] + 20:
        avisos.append('despeje final quita %d arboles (base %d)' % (v['integrar_despeje_arboles_quitados'], b['integrar_despeje_arboles_quitados']))


def presupuesto_kn5(informe: str, motivos: list[str], avisos: list[str], v: dict, base_kn5: str | None):
    """Opcional: pasa kn5_presupuesto sobre un informe de kn5_check (export de prueba)."""
    sys.path.insert(0, REV)
    try:
        import kn5_presupuesto  # noqa: E402
    except Exception as e:
        avisos.append('kn5_presupuesto no importable: %r' % e)
        return
    res = kn5_presupuesto.evaluar(informe, base_kn5)
    v['kn5'] = res.get('totales')
    for m in res.get('fallos', []):
        motivos.append('kn5_presupuesto: ' + m)
    for a in res.get('avisos', []):
        avisos.append('kn5_presupuesto: ' + a)


# ----------------------------------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--candidata', default=os.path.join(REV, 'candidata.json'),
                    help='manifiesto que escribe pipeline_escena.sh al copiar la candidata (rutas de logs y json)')
    ap.add_argument('--qa', help='carpeta con urbanismo_informe.json, asentar.json, nada_en_pista.json (ignora el manifiesto)')
    ap.add_argument('--logs', help='carpeta con preparar_geometria.log, urbanismo.log, integrar_escena.log')
    ap.add_argument('--blend', help='.blend juzgado (para anotar md5); defecto el del manifiesto o _rev/escena_candidata.blend')
    ap.add_argument('--base', default=os.path.join(REV, 'linea_base.json'))
    ap.add_argument('--out', default=os.path.join(REV, 'puerta.json'))
    ap.add_argument('--snapshot', help='escribe la linea base con los valores leidos (no juzga) en esa ruta')
    ap.add_argument('--kn5', help='informe_check.json de un export de prueba: pasa tambien kn5_presupuesto')
    ap.add_argument('--kn5-base', default=None, help='informe base para kn5_presupuesto (defecto: el de kn5_presupuesto)')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)

    motivos: list[str] = []
    avisos: list[str] = []
    fuentes: dict = {}
    manifiesto = None
    if a.qa is None and os.path.isfile(a.candidata):
        try:
            manifiesto = json.load(open(a.candidata, encoding='utf-8'))
        except Exception as e:
            motivos.append('manifiesto de la candidata ilegible: %r' % e)
    if a.qa is not None:
        fuentes = {'urbanismo_informe': os.path.join(a.qa, 'urbanismo_informe.json'),
                   'asentar': os.path.join(a.qa, 'asentar.json'),
                   'nada_en_pista': os.path.join(a.qa, 'nada_en_pista.json')}
        logs = a.logs
        blend = a.blend
    elif manifiesto:
        fuentes = {'urbanismo_informe': manifiesto.get('urbanismo_informe', os.path.join(REV, 'urbanismo_informe_candidata.json')),
                   'asentar': manifiesto.get('asentar', os.path.join(REV, 'asentar_candidata.json')),
                   'nada_en_pista': manifiesto.get('nada_en_pista', os.path.join(REV, 'nada_en_pista_candidata.json'))}
        logs = a.logs or manifiesto.get('logs')
        blend = a.blend or manifiesto.get('blend', os.path.join(REV, 'escena_candidata.blend'))
    else:
        fuentes = {'urbanismo_informe': os.path.join(REV, 'urbanismo_informe_candidata.json'),
                   'asentar': os.path.join(REV, 'asentar_candidata.json'),
                   'nada_en_pista': os.path.join(REV, 'nada_en_pista_candidata.json')}
        logs = a.logs or os.path.join(REV, 'logs')
        blend = a.blend or os.path.join(REV, 'escena_candidata.blend')
        if not os.path.isfile(a.candidata):
            avisos.append('sin manifiesto %s: se usan las rutas por defecto' % a.candidata)
    if not logs:
        motivos.append('no se sabe donde estan los logs del pipeline (--logs o manifiesto)')
        logs = ''
    for k in ('preparar_geometria', 'urbanismo', 'integrar_escena'):
        fuentes[k + '.log'] = os.path.join(logs, k + '.log') if logs else ''
    fuentes['blend'] = blend

    v: dict = {}
    valores_urbanismo_log(leer_texto(fuentes['urbanismo.log'], motivos, 'urbanismo.log'), v, motivos)
    valores_informe(leer_json(fuentes['urbanismo_informe'], motivos, 'urbanismo_informe.json'), v)
    valores_nada(leer_json(fuentes['nada_en_pista'], motivos, 'nada_en_pista.json'), v)
    valores_asentar(leer_json(fuentes['asentar'], motivos, 'asentar.json'), v)
    valores_terreno(leer_texto(fuentes['preparar_geometria.log'], motivos, 'preparar_geometria.log'), v, motivos)
    valores_integrar(leer_texto(fuentes['integrar_escena.log'], motivos, 'integrar_escena.log'), v, motivos)
    md5 = md5_fichero(blend) if blend else None
    if blend and md5 is None:
        avisos.append('no existe el .blend juzgado (%s): se juzgan solo json/logs' % blend)

    ahora = _dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    if a.snapshot:
        if motivos:
            _p('NO se congela la base: faltan datos ->')
            for m in motivos:
                _p('  -', m)
            return 1
        base = {'fecha': ahora, 'descripcion': 'linea base de la puerta de calidad (snapshot de los datos del pipeline)',
                'fuentes': fuentes, 'blend_md5': md5, 'valores': v}
        json.dump(base, open(a.snapshot, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        _p('LINEA BASE escrita en', a.snapshot)
        for k in ('urbanismo_plan_fallos', 'urbanismo_plan_casas', 'revisar_urbanismo_fallos', 'nada_en_pista', 'nada_en_pista_tierra',
                  'terreno_celdas_invaden_pista', 'terreno_hierba_asfalto', 'terreno_fosos_gt_1p5', 'terreno_costuras_max_m',
                  'terreno_costuras_celdas_gt_0p6', 'terreno_loews_ref_dz_max', 'integrar_errores', 'integrar_casas'):
            _p('  %-34s %s' % (k, v.get(k)))
        _p('  asentar', json.dumps(v.get('asentar')))
        return 0

    base = None
    if os.path.isfile(a.base):
        try:
            base = json.load(open(a.base, encoding='utf-8'))
        except Exception as e:
            motivos.append('linea base ilegible (%s): %r' % (a.base, e))
    else:
        motivos.append('falta la linea base %s (crear con --snapshot)' % a.base)

    diff: dict = {}
    juzgar(v, base, motivos, avisos, diff)
    if a.kn5:
        presupuesto_kn5(a.kn5, motivos, avisos, v, a.kn5_base)

    ok = not motivos
    salida = {'ok': ok, 'fecha': ahora, 'candidata': {'blend': blend, 'md5': md5,
                                                     'mtime': _dt.datetime.fromtimestamp(os.path.getmtime(blend)).strftime('%Y-%m-%d %H:%M') if md5 else None},
              'base': {'ruta': a.base, 'fecha': (base or {}).get('fecha'), 'blend_md5': (base or {}).get('blend_md5')},
              'fuentes': fuentes, 'motivos': motivos, 'avisos': avisos, 'diff': diff, 'valores': v}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(salida, open(a.out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if not a.quiet:
        _p('PUERTA %s -> %s' % ('ok: true' if ok else 'ok: FALSE', a.out))
        for m in motivos:
            _p('  MOTIVO:', m)
        for w in avisos:
            _p('  aviso:', w)
        cambios = {k: d for k, d in diff.items() if d['base'] != d['candidata'] and not isinstance(d['candidata'], dict)}
        _p('  diff con la base (%s): %d claves distintas' % ((base or {}).get('fecha'), len(cambios)))
        for k, d in sorted(cambios.items()):
            _p('    %-34s base %s -> candidata %s' % (k, d['base'], d['candidata']))
    return 0 if ok else 1


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as e:  # error de uso o de lectura inesperado
        print('ERROR puerta_calidad:', repr(e))
        sys.exit(2)
