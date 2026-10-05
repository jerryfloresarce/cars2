#!/bin/bash
# Cadena completa del paquete de Assetto Corsa (v1.2 "paleta y fondo", 05/10/2026; v1.1 del 04/10 en _v12_dev/hacer_zip_v11.sh)
#   1. exportar_ac.py      (bpy)  escena integrada -> escena de export (prefijos fisicos + cierre_ac)
#   2. kn5_writer_opt.py   (bpy)  escena de export -> porto_corsa_opt.kn5 (color_ac; terreno TERRENO_MODO, por defecto 'detalle')
#   3. kn5_check.py        (py)   validacion independiente 8 + la 9 de shaders (--shaders) -> informe_check_opt.json
#   4. revisar_fisica_ac.py(bpy)  inspector de fisica -> informe_fisica_final.json; PUERTA: los contadores de fallo deben ser 0
#   5. kn5_vista.py        (bpy)  "como AC sin CSP" leido del propio KN5: tomas 01, 49-54, 56, 59 (VISTA=0 lo salta)
#   6. empaquetar.py       (py)   paquete/ + porto_corsa_mod.zip (version ZIP_VERSION, solo si el kn5 esta validado)
#   7. ensayo_f_pueblo.py  (py+bpy) mini-pista F del pueblo -> ensayo_f_pueblo.zip APARTE (ENSAYO_F=0 lo salta)
# Se para en el primer fallo. Blender SOLO por la cola (03_blender/_rev/blender_cola.sh).
#
#   bash 04_export/hacer_zip.sh [carpeta_logs]
# Variables (todas opcionales):
#   ESCENA / GEOMETRIA   escena de origen y su geometria (por defecto la promovida, COPIADA a 04_export/_zip_src/
#                        escena_v12.blend + geometria_v12.json; se prepara con PREPARAR=1, ver abajo)
#   TEXTURAS_TERRENO     carpeta con terreno_base.png / terreno_mask.png congelados (por defecto _zip_src/texturas_v12)
#   SALIDA               carpeta de TODAS las salidas (pruebas: 04_export/_v12_dev/zip_prueba). Sin ella, las de siempre:
#                        04_export/porto_corsa_export.blend, kn5/, informe_fisica_final.json, paquete/, porto_corsa_mod.zip
#   ZIP_VERSION (1.2), TERRENO_MODO (detalle | base | tile), VISTA (1), ENSAYO_F (1)
#   VISTA_OUT            carpeta de kn5_vista (por defecto <salidas>/vista_kn5; la cadena v1.2: 03_blender/renders/ab/v12_como_ac)
#   COMPARAR             carpetas del modo AC de Blender para los pares, separadas por coma, en orden de preferencia
#                        (por defecto renders/ab/f1_final/despues_ac y, para la 01 que alli no esta, f1_r4/despues_ac)
#   PREPARAR=1           copia 03_blender/_rev/escena_rev.blend + geometria_rev.json (la escena PROMOVIDA por promover.sh) y
#                        03_blender/texturas/terreno_{base,mask,ao}.png a _zip_src/ (escena_v12, geometria_v12, texturas_v12)
#                        con sus md5 en _zip_src/origen_v12.txt, y sigue con la cadena
#   ESCENA_MD5           (con PREPARAR=1) md5 esperado de escena_rev.blend (el del cierre en PROMOCIONES.md): si no coincide, se para
set -e
cd /e/Escritorio/claude-pc/arnau-aseto-corsa
R=E:/Escritorio/claude-pc/arnau-aseto-corsa
LOGS=${1:-04_export/_zip_logs}
mkdir -p "$LOGS"
ZS=$R/04_export/_zip_src
if [ -z "$SALIDA" ]; then
  # seguro anti-pisada de la fase visual (03_blender/_rev/PROMOCIONES.md): mientras exista este lock, promover.sh se niega
  # a cambiar escena_rev.blend. Solo en la cadena de verdad (con SALIDA es una prueba y no bloquea a nadie). Se crea ANTES
  # de PREPARAR para que la copia de la escena promovida no pueda solaparse con una promocion.
  ZIP_LOCK=03_blender/_rev/cola/zip.lock
  mkdir -p "$(dirname "$ZIP_LOCK")"
  if [ -f 03_blender/_rev/cola/promocion.lock ]; then echo "PARADO: hay una promocion en curso (_rev/cola/promocion.lock)"; exit 1; fi
  date '+%Y-%m-%d %H:%M:%S hacer_zip.sh pid '$$ > "$ZIP_LOCK"
  trap 'rm -f "$ZIP_LOCK"' EXIT
fi
if [ "${PREPARAR:-0}" = "1" ]; then
  if [ -n "$ESCENA_MD5" ]; then
    M=$(md5sum 03_blender/_rev/escena_rev.blend | cut -d' ' -f1)
    [ "$M" = "$ESCENA_MD5" ] || { echo "PARADO: escena_rev.blend md5 $M != esperado $ESCENA_MD5"; exit 1; }
    echo "escena_rev.blend md5 $M = el del cierre (ESCENA_MD5)"
  fi
  mkdir -p "$ZS/texturas_v12"
  cp -p 03_blender/_rev/escena_rev.blend "$ZS/escena_v12.blend"
  cp -p 03_blender/_rev/geometria_rev.json "$ZS/geometria_v12.json"
  for t in terreno_base terreno_mask terreno_ao; do cp -p "03_blender/texturas/$t.png" "$ZS/texturas_v12/$t.png"; done
  { date '+%Y-%m-%d %H:%M:%S preparado desde 03_blender/_rev/escena_rev.blend (promovida)'
    md5sum "$ZS/escena_v12.blend" "$ZS/geometria_v12.json" "$ZS"/texturas_v12/*.png; } > "$ZS/origen_v12.txt"
  cat "$ZS/origen_v12.txt"
fi
SRC=${ESCENA:-$ZS/escena_v12.blend}
GEO=${GEOMETRIA:-$ZS/geometria_v12.json}
TEXT=${TEXTURAS_TERRENO:-$ZS/texturas_v12}
for f in "$SRC" "$GEO"; do
  [ -f "$f" ] || { echo "FALTA $f: copia la escena promovida con PREPARAR=1 (o pasa ESCENA=/GEOMETRIA=)"; exit 1; }
done
if [ -n "$SALIDA" ]; then
  mkdir -p "$SALIDA/kn5"
  EXP=$SALIDA/porto_corsa_export.blend; KN5DIR=$SALIDA/kn5; FIS=$SALIDA/informe_fisica_final.json
  PKG=$SALIDA/paquete; ZIP=$SALIDA/porto_corsa_mod.zip; VISTA_DIR=$SALIDA/vista_kn5; FDIR=$SALIDA/ensayo_f
else
  EXP=$R/04_export/porto_corsa_export.blend; KN5DIR=$R/04_export/kn5; FIS=$R/04_export/informe_fisica_final.json
  PKG=$R/04_export/paquete; ZIP=$R/04_export/porto_corsa_mod.zip; VISTA_DIR=$R/04_export/vista_kn5; FDIR=$R/04_export/ensayo_f
fi
VISTA_DIR=${VISTA_OUT:-$VISTA_DIR}
COMPARAR=${COMPARAR:-$R/03_blender/renders/ab/f1_final/despues_ac,$R/03_blender/renders/ab/f1_r4/despues_ac}
KN5=$KN5DIR/porto_corsa_opt.kn5
COLA="bash 03_blender/_rev/blender_cola.sh"
export GEOM=$GEO
export ZIP_VERSION=${ZIP_VERSION:-1.2}
export TERRENO_MODO=${TERRENO_MODO:-detalle}
if [ -f "$TEXT/terreno_base.png" ]; then export TERRENO_BASE=$TEXT/terreno_base.png; fi
if [ -f "$TEXT/terreno_mask.png" ]; then export TERRENO_MASK=$TEXT/terreno_mask.png; fi

paso() { echo; echo "===== [$1] $2  ($(date +%H:%M:%S))"; }
fallo() { echo "FALLO en el paso $1: mira $2"; exit 1; }

echo "escena: $SRC ($(md5sum "$SRC" | cut -c1-8))  geometria: $GEO  version $ZIP_VERSION  terreno $TERRENO_MODO"
echo "textura del terreno: ${TERRENO_BASE:-la del .blend (AVISO: sin copia congelada en $TEXT)}"
echo "salidas: ${SALIDA:-las de siempre (04_export/)}"
paso 1/7 "exportar_ac.py (cierre_ac)"
BLEND=$SRC SALIDA=$EXP $COLA --python 04_export/exportar_ac.py > "$LOGS/1_exportar.txt" 2>&1 || fallo 1 "$LOGS/1_exportar.txt"
grep -E "^OK blend|^rampa garajes|^AVISO|^Traceback" "$LOGS/1_exportar.txt" | tail -6
grep -q "^OK blend de export" "$LOGS/1_exportar.txt" || fallo 1 "$LOGS/1_exportar.txt"

paso 2/7 "kn5_writer_opt.py (color_ac, terreno $TERRENO_MODO)"
BLEND=$EXP KN5=$KN5 KN5_JSON=$KN5DIR/resumen_writer_opt.json $COLA --python 04_export/kn5_writer_opt.py \
    > "$LOGS/2_kn5.txt" 2>&1 || fallo 2 "$LOGS/2_kn5.txt"
grep -E "^OK KN5|^AVISO|^texturas:|^terreno|^Traceback" "$LOGS/2_kn5.txt" | tail -6
grep -q "^OK KN5" "$LOGS/2_kn5.txt" || fallo 2 "$LOGS/2_kn5.txt"

paso 3/7 "kn5_check.py (8 + 9 de shaders)"
python 04_export/kn5_check.py "$KN5" "$KN5DIR/informe_check_opt.json" --no-wait --shaders \
    > "$LOGS/3_check.txt" 2>&1 || fallo 3 "$LOGS/3_check.txt"
grep -E "^\s*\([0-9]\)|^RESULTADO" "$LOGS/3_check.txt"
grep -q "^RESULTADO: OK" "$LOGS/3_check.txt" || fallo 3 "$LOGS/3_check.txt"

paso 4/7 "revisar_fisica_ac.py (puerta: 0 fallos)"
BLEND=$EXP GEOM=$GEO OUT=$FIS $COLA --python 04_export/revisar_fisica_ac.py > "$LOGS/4_fisica.txt" 2>&1 \
    || fallo 4 "$LOGS/4_fisica.txt"
grep -q "^OK informe" "$LOGS/4_fisica.txt" || fallo 4 "$LOGS/4_fisica.txt"
python - "$FIS" > "$LOGS/4_fisica_puerta.txt" <<'EOF' || { cat "$LOGS/4_fisica_puerta.txt"; fallo 4 "$LOGS/4_fisica_puerta.txt"; }
import json, sys
inf = json.load(open(sys.argv[1], encoding='utf-8'))
res = inf.get('resumen', {})
for k, v in res.items():
    print('  %-42s %s' % (k, v))
# los contadores que en v1.1 eran 0 (huecos, barreras falsas, garajes, atajos, escapes, caidas, invisibles sobre visible...)
CERO = ('huecos_barrera', 'huecos_barrera_mayor_2m', 'm_sin_barrera', 'barreras_falsas', 'muros_en_asfalto_muestras',
        'pista_huecos_suelo', 'pit_rejilla_n_fallos', 'visuales_ante_cierre_n', 'garajes_rodadas_fallos',
        'garajes_rejilla_fallos', 'invisibles_sobre_visible_3cm', 'caidas_escapatoria', 'atajos', 'escapes')
DICT0 = ('pista_escalones_pendientes', 'pit_fallos_en_pit_pista_cuna')
malos = [k for k in CERO if res.get(k) != 0] + [k for k in DICT0 if any((res.get(k) or {'?': 1}).values())]
if (res.get('borde_fino_pit_fallos') or [1])[0] != 0:
    malos.append('borde_fino_pit_fallos')
print('PUERTA FISICA: %s' % ('OK (0 fallos)' if not malos else 'FALLO ' + ', '.join(malos)))
sys.exit(1 if malos else 0)
EOF
grep -E "PUERTA FISICA|terreno_hoyos" "$LOGS/4_fisica_puerta.txt"

if [ "${VISTA:-1}" = "1" ]; then
  paso 5/7 "kn5_vista.py (como AC sin CSP, leido del KN5)"
  $COLA --python 04_export/kn5_vista.py -- --kn5 "$KN5" --out "$VISTA_DIR" \
      --comparar "$COMPARAR" > "$LOGS/5_vista.txt" 2>&1 || fallo 5 "$LOGS/5_vista.txt"
  grep -E "^OK kn5_vista|^shaders" "$LOGS/5_vista.txt"
  grep -q "^OK kn5_vista" "$LOGS/5_vista.txt" || fallo 5 "$LOGS/5_vista.txt"
  python 04_export/hoja_vista.py "$VISTA_DIR" > "$LOGS/5_hoja.txt" 2>&1 || fallo 5 "$LOGS/5_hoja.txt"
  grep -E "^OK hoja" "$LOGS/5_hoja.txt"
else
  paso 5/7 "kn5_vista.py OMITIDO (VISTA=0)"
fi

paso 6/7 "empaquetar.py (version $ZIP_VERSION)"
PKG=$PKG KN5_DIR=$KN5DIR ZIP=$ZIP python 04_export/empaquetar.py > "$LOGS/6_empaquetar.txt" 2>&1 || fallo 6 "$LOGS/6_empaquetar.txt"
grep -E "^candidato|^kn5 incluido|^ext_config|^AVISO|^OK zip|^Traceback" "$LOGS/6_empaquetar.txt"
grep -q "^kn5 incluido" "$LOGS/6_empaquetar.txt" || fallo 6 "$LOGS/6_empaquetar.txt"
grep -q "^OK zip" "$LOGS/6_empaquetar.txt" || fallo 6 "$LOGS/6_empaquetar.txt"

if [ "${ENSAYO_F:-1}" = "1" ]; then
  paso 7/7 "ensayo_f_pueblo.py (mini-pista F, zip aparte)"
  python 04_export/ensayo_f_pueblo.py --export "$EXP" --geom "$GEO" --out "$FDIR" > "$LOGS/7_ensayo_f.txt" 2>&1 \
      || fallo 7 "$LOGS/7_ensayo_f.txt"
  grep -E "^kn5_check F|^OK zip F|^OK ensayo" "$LOGS/7_ensayo_f.txt"
else
  paso 7/7 "ensayo_f_pueblo.py OMITIDO (ENSAYO_F=0)"
fi
EXTRA=""; [ "${ENSAYO_F:-1}" = "1" ] && EXTRA=" + $FDIR/ensayo_f_pueblo.zip"
echo; echo "OK cadena completa ($(date +%H:%M:%S)): $ZIP$EXTRA"
ls -la --time-style=+%d/%m-%H:%M "$ZIP"
