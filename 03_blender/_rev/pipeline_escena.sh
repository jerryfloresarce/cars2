#!/bin/bash
# Genera la escena COMPLETA con los datos actuales y congela una copia CANDIDATA para juzgar.
#   bash 03_blender/_rev/pipeline_escena.sh <carpeta_logs>
#   SOLO_COPIA=1 bash 03_blender/_rev/pipeline_escena.sh <carpeta_logs>   # prueba SOLO el paso final de copia (no regenera nada)
# Pasos: preparar_geometria (python) -> medir_relieve (python, informativo) -> urbanismo (python)
#        -> mascara_terreno (python, F1 3.4) -> vegetacion (python, F1 4.1) -> mascara_terreno --solo-base (sombra de bosque)
#        -> construir_pista -> integrar_escena -> inspectores -> asentar -> revisar_urbanismo (con el plan) -> materiales -> plot
#        -> banda_terreno_2m (F1 r4: TERRENO a 2 m junto al asfalto; ULTIMO paso de Blender sobre porto_corsa.blend)
#        -> copia CANDIDATA en 03_blender/_rev/escena_candidata.blend (+ comprobacion de rutas de imagen absolutas, F1 r2 A7;
#           + geometria_candidata.json, urbanismo_candidata.json,
#           urbanismo_informe_candidata.json, asentar_candidata.json, nada_en_pista_candidata.json, vegetacion_candidata.json,
#           medir_relieve_candidata.json, candidata.json = manifiesto)
#        -> _rev/puerta_calidad.py (solo json/logs) -> _rev/puerta.json {ok, motivos, diff contra linea_base.json}
#        -> _rev/presupuesto_paleta_candidata.py (F1 r4, solo lectura): _rev/presupuesto_candidata.json (tris + RGB fuera de paleta)
# FASE VISUAL (plan secc. 0 decision 1 / bloque 0): este script YA NO escribe _rev/escena_rev.blend (la escena congelada que
# prueban fisica y color; 04_export/hacer_zip.sh exporta su copia 04_export/_zip_src/escena_v11.blend, mismo md5).
# escena_rev.blend solo cambia por `bash 03_blender/_rev/promover.sh <bloque> <hoja>` y solo cuando puerta.json dice ok: true.
# Ver _rev/puerta_README.md.
COLA="E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender/_rev/blender_cola.sh"
D="E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender"
REV="${REV_DIR:-$D/_rev}"      # REV_DIR=<carpeta> solo para probar la copia en otro sitio
LOGS="${1:-$D/_rev/logs}"
mkdir -p "$LOGS"
unset GEOM URBANISMO BLEND
cd "$D" || exit 1

# ---- paso final: copia candidata + manifiesto + puerta de calidad (se usa al final y con SOLO_COPIA=1) ----
copiar_candidata() {
  cp porto_corsa.blend "$REV/escena_candidata.blend" && cp geometria_3d.json "$REV/geometria_candidata.json" \
    && cp urbanismo.json "$REV/urbanismo_candidata.json" && cp renders/qa/urbanismo_informe.json "$REV/urbanismo_informe_candidata.json" \
    && cp renders/qa/asentar.json "$REV/asentar_candidata.json" && cp renders/qa/nada_en_pista.json "$REV/nada_en_pista_candidata.json" \
    || { echo "FALLO copia candidata (falta algun fichero de salida del pipeline)"; return 1; }
  # fase visual F1 r2 (PARCHES_F1_mascara.md R2.1/A7, director_f1_r1.md 1): ninguna Image con ruta relativa '//' en la candidata
  # (si no, el terreno sale MAGENTA fuera de 03_blender/ y el writer heredaria el fallo). Lector zstd SIN abrir Blender, con el
  # python de Blender (trae zstandard): exit 1 = hay '//' (FALLO, no se promueve); exit 2 = no se pudo leer (solo aviso).
  BPY="C:/Program Files/Blender Foundation/Blender 5.1/5.1/python/bin/python.exe"
  "$BPY" "$D/_rev/comprobar_rutas_blend.py" "$REV/escena_candidata.blend" > "$LOGS/comprobar_rutas.log" 2>&1
  rc_rutas=$?
  tail -12 "$LOGS/comprobar_rutas.log" | cut -c1-200
  if [ $rc_rutas -eq 1 ]; then
    echo "FALLO candidata con rutas de imagen relativas (ver arriba; construir_pista.py debe guardar con relative_remap=False): no se promueve"
    return 1
  elif [ $rc_rutas -ne 0 ]; then
    echo "AVISO: comprobar_rutas_blend.py no pudo leer la candidata (rc $rc_rutas): comprobar a mano antes de promover"
  fi
  # fase visual F1: el plan de vegetacion (4.1) y las medidas del relieve (bloque 1) se congelan con la escena (si existen)
  [ -f vegetacion_plan.json ] && cp vegetacion_plan.json "$REV/vegetacion_candidata.json"
  [ -f renders/qa/medir_relieve.json ] && cp renders/qa/medir_relieve.json "$REV/medir_relieve_candidata.json"
  # F1 r4 (PARCHES_F1_mascara.md R4.4 A8): cifras de la banda de 2 m del TERRENO (ultimo paso de Blender)
  [ -f renders/qa/banda_terreno_2m.json ] && cp renders/qa/banda_terreno_2m.json "$REV/banda_terreno_2m_candidata.json"
  md5=$(md5sum "$REV/escena_candidata.blend" | cut -c1-32)
  LOGS_ABS=$(cd "$LOGS" 2>/dev/null && (pwd -W 2>/dev/null || pwd)) || LOGS_ABS="$LOGS"
  REV_="$REV" LOGS_="$LOGS_ABS" MD5_="$md5" python - <<'PYEOF'
import datetime, json, os
rev, logs, md5 = os.environ['REV_'], os.environ['LOGS_'], os.environ['MD5_']
man = {'fecha': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'origen': 'pipeline_escena.sh', 'md5': md5,
       'blend': rev + '/escena_candidata.blend', 'geometria': rev + '/geometria_candidata.json',
       'urbanismo': rev + '/urbanismo_candidata.json', 'urbanismo_informe': rev + '/urbanismo_informe_candidata.json',
       'asentar': rev + '/asentar_candidata.json', 'nada_en_pista': rev + '/nada_en_pista_candidata.json', 'logs': logs}
for k, f in (('vegetacion', 'vegetacion_candidata.json'), ('medir_relieve', 'medir_relieve_candidata.json'),   # F1
             ('banda_terreno_2m', 'banda_terreno_2m_candidata.json')):                                         # F1 r4 A8
    if os.path.isfile(os.path.join(rev, f)):
        man[k] = rev + '/' + f
json.dump(man, open(rev + '/candidata.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
PYEOF
  echo "candidata: $REV/escena_candidata.blend (md5 $md5) | manifiesto $REV/candidata.json | logs $LOGS"
  # la puerta nunca tumba el pipeline: solo informa (promover.sh es quien la exige)
  python "$D/_rev/puerta_calidad.py" --candidata "$REV/candidata.json" --out "$REV/puerta.json" 2>&1 | head -25
  echo "PUERTA exit ${PIPESTATUS[0]} (0 = ok: true; promover con: bash 03_blender/_rev/promover.sh <bloque> <hoja>)"
  return 0
}
if [ "${SOLO_COPIA:-0}" = "1" ]; then
  echo "SOLO_COPIA=1: solo el paso final de copia (porto_corsa.blend actual -> candidata), sin regenerar"
  for l in preparar_geometria urbanismo integrar_escena; do   # mkdir -p ya creo $LOGS: avisar si esta vacio (la puerta dara ok: false)
    [ -f "$LOGS/$l.log" ] || echo "AVISO: falta $LOGS/$l.log (la puerta lo necesita; pasar la carpeta de logs del ultimo pipeline, p.ej. _rev/logs_final)"
  done
  copiar_candidata
  exit $?
fi

python preparar_geometria.py > "$LOGS/preparar_geometria.log" 2>&1 || { echo "FALLO preparar_geometria"; tail -20 "$LOGS/preparar_geometria.log"; exit 1; }
echo "preparar_geometria ok"
grep -E "F1 tierra tallada" "$LOGS/preparar_geometria.log" | head -1 | cut -c1-300
# fase visual F1 (bloque 1, PARCHES_F1_terreno.md A3): KPIs del relieve antes/despues (informativo: no tumba el pipeline).
# 'antes' = la geometria de la escena congelada (_rev/geometria_rev.json) o, si no existe, la candidata anterior.
ANTES="$REV/geometria_rev.json"; [ -f "$ANTES" ] || ANTES="$REV/geometria_candidata.json"
python _rev/medir_relieve.py --antes "$ANTES" --out renders/qa/medir_relieve.json > "$LOGS/medir_relieve.log" 2>&1 \
  || echo "AVISO: medir_relieve.py fallo (informativo): $(tail -2 "$LOGS/medir_relieve.log" | tr '\n' ' ' | cut -c1-200)"
grep -E "KPI antes|invariantes|cupula 56" "$LOGS/medir_relieve.log" | cut -c1-420   # F1 r4 (PARCHES_F1_terreno.md r4.4): condicion de la acotacion 1
python urbanismo.py > "$LOGS/urbanismo.log" 2>&1 || { echo "FALLO urbanismo"; tail -20 "$LOGS/urbanismo.log"; exit 1; }
grep -E "QA:|TOTAL casas" "$LOGS/urbanismo.log" | tail -2 | cut -c1-400
# fase visual F1 (bloque 3.4, PARCHES_F1_mascara.md A1): mascara del terreno por texel (python del sistema, ~5 s):
# texturas/terreno_mask.png, terreno_ao.png, terreno_base.png + renders/qa/terreno_mask.png. construir_pista.py la lee
# (MAT_terreno v2); si faltara, construir_pista la genera el solo (red de seguridad), pero el orden del plan secc. 13 es este.
python mascara_terreno.py > "$LOGS/mascara_terreno.log" 2>&1 || { echo "FALLO mascara_terreno"; tail -20 "$LOGS/mascara_terreno.log"; exit 1; }
grep "MASCARA_TERRENO" "$LOGS/mascara_terreno.log" | cut -c1-300
# fase visual F1 (bloque 4.1, PARCHES_F1_vegetacion_plan.md A1): plan de vegetacion por mascaras (python del sistema, ~5 s).
# Lee los canales A/B de terreno_mask.png: va DETRAS de la mascara. En F1 nadie lo consume (integracion en F3).
python vegetacion.py > "$LOGS/vegetacion.log" 2>&1 || { echo "FALLO vegetacion"; tail -20 "$LOGS/vegetacion.log"; exit 1; }
grep -E "TOTAL|VERIFICACION" "$LOGS/vegetacion.log" | cut -c1-300
# 2a pasada de la mascara: solo reescribe terreno_base.png con la sombra de bosque del plan recien calculado (determinista, ~5 s)
python mascara_terreno.py --solo-base >> "$LOGS/mascara_terreno.log" 2>&1 || { echo "FALLO mascara_terreno --solo-base"; tail -5 "$LOGS/mascara_terreno.log"; exit 1; }
for p in construir_pista integrar_escena revisar_flotantes revisar_invasores eliminar_sumergidos revisar_coches revisar_tunel asentar_objetos; do
  s=$(date +%s)
  bash "$COLA" --python "$p.py" > "$LOGS/$p.log" 2>&1
  rc=$?
  echo "$p exit $rc ($(( $(date +%s)-s )) s)"
  grep -iE "traceback|error:|ERRORES:" "$LOGS/$p.log" | grep -v Deprecation | head -3
  [ $rc -ne 0 ] && exit $rc
done
bash "$COLA" --python _rev/nada_en_pista.py -- "$D/porto_corsa.blend" "$D/geometria_3d.json" "$D/renders/qa/nada_en_pista.json" > "$LOGS/nada_en_pista.log" 2>&1
grep "NADA_EN_PISTA" "$LOGS/nada_en_pista.log"
URBANISMO="$D/urbanismo.json" bash "$COLA" --python revisar_urbanismo.py > "$LOGS/revisar_urbanismo.log" 2>&1
echo "revisar_urbanismo exit $?"
for p in mejorar_materiales aplicar_texturas; do
  bash "$COLA" --python "$p.py" > "$LOGS/$p.log" 2>&1
  echo "$p exit $?"
done
# fase visual F1: lineas de control de la paleta/mascara/horizonte (PARCHES_F1_materiales.md 6, _mascara A1, _horizonte P-H1)
grep -E "MAT_terreno v2|AVISO: faltan PNG|atributo roca|zonas nz <|banda de" "$LOGS/construir_pista.log" | cut -c1-300   # F1 r3: 'atributo roca = canal A de ...' (mascara R3.2); r4: zonas nz < 0.62 (R4.4)
grep -E "BISEL BARATO|HORIZONTE" "$LOGS/mejorar_materiales.log" | cut -c1-300
grep -E "tocados|saltados" "$LOGS/aplicar_texturas.log" | tail -2 | cut -c1-300
URBANISMO="$D/urbanismo.json" python revisar_urbanismo_plot.py > "$LOGS/plot.log" 2>&1
echo "plot exit $?"
# F1 r4 (ACOTACIONES 4; PARCHES_F1_mascara.md R4.4 A8): ULTIMO paso de Blender: TERRENO a 2 m en la banda de 25 m junto al asfalto
# (+45 k vertices, +86 k tris) y zonas nz < 0.62 sin dientes sobre la malla final. Va el ultimo porque a partir de aqui el TERRENO ya
# no tiene nx*ny vertices: integrar/asentar/revisar_*/nada_en_pista deben haber terminado (los nx*ny primeros conservan su indice).
bash "$COLA" --python _rev/banda_terreno_2m.py > "$LOGS/banda_terreno_2m.log" 2>&1 || { echo "FALLO banda_terreno_2m"; tail -20 "$LOGS/banda_terreno_2m.log"; exit 1; }
grep "BANDA_2M" "$LOGS/banda_terreno_2m.log" | cut -c1-300
copiar_candidata || exit 1
# F1 r4 (director_f1_r3.md 7, ACOTACIONES 3; pendiente desde r1): presupuesto de tris de la CANDIDATA (recuento en Blender, sin
# 04_export: tris sin LIB por familia, mallas, materiales, HORIZ_, vegetacion) + RGB fuera de paleta.json. Solo lectura, informativo.
bash "$COLA" --python _rev/presupuesto_paleta_candidata.py -- "$REV/escena_candidata.blend" "$REV/presupuesto_candidata.json" > "$LOGS/presupuesto_paleta.log" 2>&1 \
  || echo "AVISO: presupuesto_paleta_candidata.py fallo (informativo): $(tail -2 "$LOGS/presupuesto_paleta.log" | tr '\n' ' ' | cut -c1-200)"
grep -E "PRESUPUESTO|familias|PALETA|FUERA" "$LOGS/presupuesto_paleta.log" | head -14 | cut -c1-420
python - <<'PYEOF'
import json
d = json.load(open(r'E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\renders\qa\urbanismo_informe.json', encoding='utf-8'))
print('AUDITORIA', json.dumps(d.get('resumen'), ensure_ascii=False))
PYEOF
grep -v "Deprecation\|use_nodes" "$LOGS/integrar_escena.log" | grep -iE "urbanismo: [0-9]+ casas|casino: roca_casino|tunel: entrada|roca del lazo \(roca_lazo\)|despeje final|edicolas|horizonte:|ERRORES" | cut -c1-300
