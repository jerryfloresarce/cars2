#!/bin/bash
# COLA DE BLENDER: como mucho NSLOTS Blender a la vez en todo el equipo: cada Blender con la escena entera usa ~5 GB
# de memoria y 10 a la vez agotaron la RAM + paginacion (40 GB) y colgaron Windows y la app (03/10).
#   bash 03_blender/_rev/blender_cola.sh --python script.py [-- args...]
# (anade --background --factory-startup). Todos los agentes deben lanzar Blender SOLO asi.
B="C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
COLA="E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender/_rev/cola"
NSLOTS=6
mkdir -p "$COLA"
slot=""
espera=0
while [ -z "$slot" ]; do
  for i in $(seq 0 $((NSLOTS - 1))); do
    if mkdir "$COLA/slot$i" 2>/dev/null; then
      slot="$COLA/slot$i"
      date +%s > "$slot/inicio"
      break
    fi
  done
  if [ -z "$slot" ]; then
    # libera huecos abandonados (un agente que murio con el hueco cogido): > 20 min
    ahora=$(date +%s)
    for i in $(seq 0 $((NSLOTS - 1))); do
      f="$COLA/slot$i/inicio"
      if [ -f "$f" ] && [ $((ahora - $(cat "$f" 2>/dev/null || echo $ahora))) -gt 1200 ]; then
        rm -rf "$COLA/slot$i"
      fi
    done
    sleep 3
    espera=$((espera + 3))
  fi
done
[ $espera -gt 0 ] && echo "[cola] esperado ${espera} s por un hueco de Blender"
trap 'rm -rf "$slot"' EXIT INT TERM
"$B" --background --factory-startup "$@"
exit $?
