#!/bin/bash
# promover.sh -- promueve la escena CANDIDATA a _rev/escena_rev.blend SOLO si la puerta de calidad dice ok: true.
#   bash 03_blender/_rev/promover.sh "<bloque>" "<hoja A/B>" ["nota corta"]
#     p.ej. bash 03_blender/_rev/promover.sh "bloque 3 paleta" renders/ab/bloque3/hoja_bloque3_piloto.png "F1 cierre"
#   SIMULAR=1 ...   -> hace todas las comprobaciones e imprime lo que haria, sin copiar ni anotar nada
#   REV_DIR=<dir>   -> otra carpeta _rev (pruebas); PUERTA=<json> otra puerta.json
# Se NIEGA (exit 3) si: hay un export en marcha, falta puerta.json o dice ok: false, el md5 de la candidata no es el que
#   juzgo la puerta (candidata regenerada despues de juzgar), o falta algun fichero de la candidata.
# EXPORT EN MARCHA = existe 03_blender/_rev/cola/zip.lock  O  hay un proceso con "hacer_zip.sh" en su linea de ordenes
#   (Get-CimInstance Win32_Process; sin powershell, ps -ef). Desde el 04/10 (remate del bloque 0) hacer_zip.sh crea zip.lock
#   al empezar (`date > ...`) y lo borra al terminar (trap EXIT, tambien si falla un paso); la deteccion del proceso queda
#   como segundo seguro. Mientras promueve, este script deja 03_blender/_rev/cola/promocion.lock (por si hacer_zip.sh quiere esperar).
# Hace: candidata -> escena_rev.blend + geometria_rev.json + urbanismo_rev.json (+ urbanismo_informe_rev.json, asentar_rev.json,
#   nada_en_pista_rev.json), guarda promociones/escena_vN.blend + puerta_vN.json (N incremental) y anota
#   fecha | vN | md5 | bloque | hoja | nota | avisos de la puerta en _rev/PROMOCIONES.md. hacer_zip.sh NO se toca.
D="E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender"
REV="${REV_DIR:-$D/_rev}"
PUERTA="${PUERTA:-$REV/puerta.json}"
BLOQUE="${1:-}"
HOJA="${2:-}"
NOTA="${3:-}"
SIM="${SIMULAR:-0}"
CAND="$REV/escena_candidata.blend"
REG="$REV/PROMOCIONES.md"
PROM="$REV/promociones"
mkdir -p "$REV/cola"

negar() { echo "NO SE PROMUEVE: $1"; exit 3; }

[ -n "$BLOQUE" ] && [ -n "$HOJA" ] || { echo "uso: bash promover.sh \"<bloque>\" \"<hoja A/B>\" [nota]   (SIMULAR=1 para ensayar)"; exit 2; }

# 1. export en marcha?
if [ -f "$REV/cola/zip.lock" ]; then
  negar "existe $REV/cola/zip.lock ($(head -c 200 "$REV/cola/zip.lock" | tr -d '\r\n')): hay un export del zip en marcha"
fi
if command -v powershell >/dev/null 2>&1; then
  n=$(powershell -NoProfile -Command "@(Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'hacer_zip\.sh' -and \$_.CommandLine -notmatch 'promover\.sh' }).Count" 2>/dev/null | tr -d '\r\n ')
  [ -n "$n" ] && [ "$n" != "0" ] && negar "hay $n proceso(s) ejecutando hacer_zip.sh (export del zip en marcha)"
else
  ps -ef 2>/dev/null | grep -v grep | grep -q "hacer_zip.sh" && negar "hay un proceso ejecutando hacer_zip.sh (export del zip en marcha)"
fi

# 2. candidata completa
for f in "$CAND" "$REV/geometria_candidata.json" "$REV/urbanismo_candidata.json"; do
  [ -f "$f" ] || negar "falta $f (ejecutar primero pipeline_escena.sh)"
done

# 2b. fase visual F1 r2 (PARCHES_F1_mascara.md A7): ninguna Image con ruta relativa '//' (magenta fuera de 03_blender/; director_f1_r1.md 1)
BPY="C:/Program Files/Blender Foundation/Blender 5.1/5.1/python/bin/python.exe"
[ -f "$BPY" ] && { "$BPY" "$D/_rev/comprobar_rutas_blend.py" "$CAND" | tail -6; [ "${PIPESTATUS[0]}" = "1" ] && negar "la candidata lleva rutas de imagen relativas (ver arriba): saldria magenta fuera de 03_blender/"; }

# 3. puerta ok y sobre ESTA candidata
[ -f "$PUERTA" ] || negar "falta $PUERTA (ejecutar python 03_blender/_rev/puerta_calidad.py)"
md5=$(md5sum "$CAND" | cut -c1-32)
PUERTA_="$PUERTA" MD5_="$md5" python - <<'PYEOF' || negar "la puerta no autoriza (ver arriba)"
import json, os, sys
p = json.load(open(os.environ['PUERTA_'], encoding='utf-8'))
md5 = os.environ['MD5_']
ok = p.get('ok') is True
juzgado = (p.get('candidata') or {}).get('md5')
print('puerta %s: ok=%s fecha=%s md5 juzgado=%s' % (os.environ['PUERTA_'], p.get('ok'), p.get('fecha'), juzgado))
for m in p.get('motivos', []):
    print('  MOTIVO:', m)
for a in p.get('avisos', []):
    print('  aviso:', a)
if not ok:
    print('  -> puerta.json ok: false')
    sys.exit(1)
if juzgado != md5:
    print('  -> la puerta juzgo otra candidata (md5 %s != actual %s): volver a pasar puerta_calidad.py' % (juzgado, md5))
    sys.exit(1)
PYEOF

# 4. numero de version
mkdir -p "$PROM"
ultimo=$(ls "$PROM"/escena_v*.blend 2>/dev/null | sed -E 's/.*escena_v([0-9]+)\.blend/\1/' | sort -n | tail -1)
N=$(( ${ultimo:-0} + 1 ))
fecha=$(date '+%Y-%m-%d %H:%M')
avisos=$(PUERTA_="$PUERTA" python -c "import json,os; p=json.load(open(os.environ['PUERTA_'],encoding='utf-8')); print('; '.join(p.get('avisos',[]))[:300] or '-')")

echo "promocion v$N: $CAND (md5 $md5) -> $REV/escena_rev.blend | bloque: $BLOQUE | hoja: $HOJA | nota: ${NOTA:--}"
if [ "$SIM" = "1" ]; then
  echo "SIMULAR=1: no se copia ni se anota nada (todo lo anterior esta comprobado y autorizaria la promocion)"
  exit 0
fi

# 5. copiar (con lock de promocion)
date '+%Y-%m-%d %H:%M:%S' > "$REV/cola/promocion.lock"
trap 'rm -f "$REV/cola/promocion.lock"' EXIT INT TERM
cp "$CAND" "$REV/escena_rev.blend" && cp "$REV/geometria_candidata.json" "$REV/geometria_rev.json" \
  && cp "$REV/urbanismo_candidata.json" "$REV/urbanismo_rev.json" || { echo "FALLO copiando a escena_rev"; exit 1; }
[ -f "$REV/urbanismo_informe_candidata.json" ] && cp "$REV/urbanismo_informe_candidata.json" "$REV/urbanismo_informe_rev.json"
[ -f "$REV/asentar_candidata.json" ] && cp "$REV/asentar_candidata.json" "$REV/asentar_rev.json"
[ -f "$REV/nada_en_pista_candidata.json" ] && cp "$REV/nada_en_pista_candidata.json" "$REV/nada_en_pista_rev.json"
cp "$CAND" "$PROM/escena_v$N.blend" && cp "$PUERTA" "$PROM/puerta_v$N.json" || { echo "FALLO guardando promociones/escena_v$N.blend"; exit 1; }
md5rev=$(md5sum "$REV/escena_rev.blend" | cut -c1-32)
[ "$md5rev" = "$md5" ] || { echo "FALLO: md5 de escena_rev.blend ($md5rev) distinto de la candidata ($md5)"; exit 1; }

# 6. registro
if [ ! -f "$REG" ]; then
  {
    echo "# PROMOCIONES de _rev/escena_rev.blend (fase visual)"
    echo
    echo "| fecha | version | md5 escena_rev.blend | bloque | hoja A/B | nota | avisos de la puerta |"
    echo "|---|---|---|---|---|---|---|"
  } > "$REG"
fi
echo "| $fecha | v$N | $md5 | $BLOQUE | $HOJA | ${NOTA:--} | $avisos |" >> "$REG"
echo "OK promovida v$N: $REV/escena_rev.blend (md5 $md5); copia en $PROM/escena_v$N.blend; anotada en $REG"
