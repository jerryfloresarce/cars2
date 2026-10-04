#!/bin/bash
# Genera la escena COMPLETA con los datos actuales y congela una copia CANDIDATA para juzgar.
#   bash 03_blender/_rev/pipeline_escena.sh <carpeta_logs>
#   SOLO_COPIA=1 bash 03_blender/_rev/pipeline_escena.sh <carpeta_logs>   # prueba SOLO el paso final de copia (no regenera nada)
# Pasos: preparar_geometria (python) -> urbanismo (python) -> construir_pista -> integrar_escena
#        -> inspectores -> asentar -> revisar_urbanismo (con el plan) -> materiales -> plot
#        -> copia CANDIDATA en 03_blender/_rev/escena_candidata.blend (+ geometria_candidata.json, urbanismo_candidata.json,
#           urbanismo_informe_candidata.json, asentar_candidata.json, nada_en_pista_candidata.json, candidata.json = manifiesto)
#        -> _rev/puerta_calidad.py (solo json/logs) -> _rev/puerta.json {ok, motivos, diff contra linea_base.json}
# FASE VISUAL (plan secc. 0 decision 1 / bloque 0): este script YA NO escribe _rev/escena_rev.blend (la escena que exporta
# 04_export/hacer_zip.sh). escena_rev.blend solo cambia por `bash 03_blender/_rev/promover.sh <bloque> <hoja>` y solo
# cuando puerta.json dice ok: true. Ver _rev/puerta_README.md.
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
  md5=$(md5sum "$REV/escena_candidata.blend" | cut -c1-32)
  LOGS_ABS=$(cd "$LOGS" 2>/dev/null && (pwd -W 2>/dev/null || pwd)) || LOGS_ABS="$LOGS"
  REV_="$REV" LOGS_="$LOGS_ABS" MD5_="$md5" python - <<'PYEOF'
import datetime, json, os
rev, logs, md5 = os.environ['REV_'], os.environ['LOGS_'], os.environ['MD5_']
man = {'fecha': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'origen': 'pipeline_escena.sh', 'md5': md5,
       'blend': rev + '/escena_candidata.blend', 'geometria': rev + '/geometria_candidata.json',
       'urbanismo': rev + '/urbanismo_candidata.json', 'urbanismo_informe': rev + '/urbanismo_informe_candidata.json',
       'asentar': rev + '/asentar_candidata.json', 'nada_en_pista': rev + '/nada_en_pista_candidata.json', 'logs': logs}
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
python urbanismo.py > "$LOGS/urbanismo.log" 2>&1 || { echo "FALLO urbanismo"; tail -20 "$LOGS/urbanismo.log"; exit 1; }
grep -E "QA:|TOTAL casas" "$LOGS/urbanismo.log" | tail -2 | cut -c1-400
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
URBANISMO="$D/urbanismo.json" python revisar_urbanismo_plot.py > "$LOGS/plot.log" 2>&1
echo "plot exit $?"
copiar_candidata || exit 1
python - <<'PYEOF'
import json
d = json.load(open(r'E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\renders\qa\urbanismo_informe.json', encoding='utf-8'))
print('AUDITORIA', json.dumps(d.get('resumen'), ensure_ascii=False))
PYEOF
grep -v "Deprecation\|use_nodes" "$LOGS/integrar_escena.log" | grep -iE "urbanismo: [0-9]+ casas|casino: roca_casino|tunel: entrada|roca del lazo \(roca_lazo\)|despeje final|edicolas|ERRORES" | cut -c1-300
