#!/bin/bash
# Cadena completa del paquete de Assetto Corsa (zip v1.1, 04/10/2026), siempre sobre la escena final
# 03_blender/porto_corsa.blend + geometria_3d.json:
#   1. exportar_ac.py      (bpy)  escena integrada -> porto_corsa_export.blend (prefijos fisicos + cierre_ac)
#   2. kn5_writer_opt.py   (bpy)  porto_corsa_export.blend -> kn5/porto_corsa_opt.kn5 (color_ac activado)
#   3. kn5_check.py        (py)   validacion independiente del KN5 -> kn5/informe_check_opt.json (RESULTADO OK)
#   4. revisar_fisica_ac.py(bpy)  inspector de fisica sobre porto_corsa_export.blend -> informe_fisica_final.json
#   5. empaquetar.py       (py)   paquete/ + porto_corsa_mod.zip (solo si el kn5 esta validado)
# Se para en el primer fallo. Blender SOLO por la cola (03_blender/_rev/blender_cola.sh).
#   bash 04_export/hacer_zip.sh [carpeta_logs]
set -e
cd /e/Escritorio/claude-pc/arnau-aseto-corsa
LOGS=${1:-04_export/_zip_logs}
mkdir -p "$LOGS"
COLA="bash 03_blender/_rev/blender_cola.sh"
# se exporta la copia CONGELADA (_rev/escena_rev.blend + geometria_rev.json, la que probaron los equipos
# de fisica y color), no la escena viva: la fase visual puede seguir cambiando porto_corsa.blend mientras
SRC=E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/_zip_src/escena_v11.blend
GEO=E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/_zip_src/geometria_v11.json
EXP=E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/porto_corsa_export.blend
FIS=E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/informe_fisica_final.json
export GEOM=$GEO

paso() { echo; echo "===== [$1] $2  ($(date +%H:%M:%S))"; }
fallo() { echo "FALLO en el paso $1: mira $2"; exit 1; }

echo "escena: $SRC ($(md5sum "$SRC" | cut -c1-8))  geometria: $GEO"
paso 1/5 "exportar_ac.py (cierre_ac)"
BLEND=$SRC SALIDA=$EXP $COLA --python 04_export/exportar_ac.py > "$LOGS/1_exportar.txt" 2>&1 || fallo 1 "$LOGS/1_exportar.txt"
grep -E "^OK blend|^rampa garajes|^AVISO|^Traceback" "$LOGS/1_exportar.txt" | tail -6
grep -q "^OK blend de export" "$LOGS/1_exportar.txt" || fallo 1 "$LOGS/1_exportar.txt"

paso 2/5 "kn5_writer_opt.py (color_ac)"
BLEND=$EXP $COLA --python 04_export/kn5_writer_opt.py > "$LOGS/2_kn5.txt" 2>&1 || fallo 2 "$LOGS/2_kn5.txt"
grep -E "^OK KN5|^AVISO|^texturas:|^Traceback" "$LOGS/2_kn5.txt" | tail -5
grep -q "^OK KN5" "$LOGS/2_kn5.txt" || fallo 2 "$LOGS/2_kn5.txt"

paso 3/5 "kn5_check.py"
python 04_export/kn5_check.py 04_export/kn5/porto_corsa_opt.kn5 04_export/kn5/informe_check_opt.json --no-wait \
    > "$LOGS/3_check.txt" 2>&1 || fallo 3 "$LOGS/3_check.txt"
grep -E "^RESULTADO" "$LOGS/3_check.txt"
grep -q "^RESULTADO: OK" "$LOGS/3_check.txt" || fallo 3 "$LOGS/3_check.txt"

paso 4/5 "revisar_fisica_ac.py"
BLEND=$EXP GEOM=$GEO OUT=$FIS $COLA --python 04_export/revisar_fisica_ac.py > "$LOGS/4_fisica.txt" 2>&1 \
    || fallo 4 "$LOGS/4_fisica.txt"
grep -q "^OK informe" "$LOGS/4_fisica.txt" || fallo 4 "$LOGS/4_fisica.txt"
python - "$FIS" <<'EOF'
import json, sys
inf = json.load(open(sys.argv[1], encoding='utf-8'))
res = inf.get('resumen', {})
for k, v in res.items():
    print('  %-42s %s' % (k, v))
EOF

paso 5/5 "empaquetar.py"
python 04_export/empaquetar.py > "$LOGS/5_empaquetar.txt" 2>&1 || fallo 5 "$LOGS/5_empaquetar.txt"
grep -E "^candidato|^kn5 incluido|^ext_config|^AVISO|^OK zip|^Traceback" "$LOGS/5_empaquetar.txt"
grep -q "^kn5 incluido" "$LOGS/5_empaquetar.txt" || fallo 5 "$LOGS/5_empaquetar.txt"
grep -q "^OK zip" "$LOGS/5_empaquetar.txt" || fallo 5 "$LOGS/5_empaquetar.txt"
echo; echo "OK cadena completa ($(date +%H:%M:%S)): 04_export/porto_corsa_mod.zip"
ls -la --time-style=+%d/%m-%H:%M 04_export/porto_corsa_mod.zip
