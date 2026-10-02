# Porto Corsa — Mod de circuito para Assetto Corsa

Proyecto: recrear el circuito del mapa de referencia (Porto Corsa) como mod
instalable de Assetto Corsa, con el máximo detalle posible.

## Estado del PC (comprobado 2026-09-08)
- Blender 5.1 instalado en `C:\Program Files\Blender Foundation\Blender 5.1`
- Python 3.12 y Node.js disponibles
- Assetto Corsa NO está instalado en este PC (el juego está en el PC del amigo)
  → el resultado final será una carpeta `porto_corsa` lista para copiar a
  `assettocorsa\content\tracks\` en su PC.

## Características del circuito (confirmadas con el SVG oficial de la wiki)
- Es el Porto Corsa de Cars 2 (World Grand Prix, "Mondiale Grand Prix" en Italia)
- Vuelta de 5.200 m (decisión del usuario) · 50 curvas numeradas + chicane de meta
- Sentido de marcha: meta → 01 → 02 → 03 (hacia el noroeste por la diagonal)
- Rectas rápidas (rojo): diagonal de meta y bajada 30→31 — 1,58 km (30%)
- Técnico (azul): 03–11 (pueblo, subida) y 31–41 (sector casino) — 1,31 km (25%)
- Puentes (blanco en el mapa): sector del casino/peñón Topolino — 1,20 km (23%)
- Tierra (amarillo): ~14–26, ladera con zigzag y horquilla en 18 — 0,92 km (18%)
- Las curvas 12, 13, 34 y 37 no tienen círculo en el mapa oficial (numeración
  reconstruida por picos de curvatura)
- Elevación (de la investigación): puerto a nivel del mar → subida por el
  acantilado (01-02) → pueblo (03-10) → ladera de tierra hasta el punto más
  alto (18) → descenso → sector Mónaco/casino con puentes sobre el mar →
  chicane y vuelta al puerto

## Fases
1. **Trazado** — ✅ HECHO (v1 exacta): línea central extraída matemáticamente
   del SVG oficial de la wiki (esqueletonización raster 8x), 2.600 muestras
   (~2 m), superficies por muestra, 50 curvas numeradas, meta y sentido
   verificados. Datos: `02_trazado/trazado_v1.json` · Visor:
   `02_trazado/preview_trazado.html` · Script: `02_trazado/extraer_centerline.py`
2. **Calibración** — ✅ HECHO: 5.200 m/vuelta → 2,9195 m por unidad SVG.
3. **Construcción 3D en Blender** (por script, reproducible) — EN CURSO:
   - ✅ Perfil de alturas (3→83 m, pendiente máx 12,5%), peraltes, anchos por
     superficie: `03_blender/preparar_geometria.py` → `geometria_3d.json`
   - ✅ Escena base: pista (asfalto/tierra/tablero de puente), 24 pianos,
     faldones y pilas de puentes sobre el mar, arcenes, línea de salida,
     terreno con costa suave y color por altura, mar, sol y 4 cámaras:
     `03_blender/construir_pista.py` → `porto_corsa.blend` + `renders/`
   - ⏳ Assets del entorno: workflow de 8 agentes generando casino, peñón
     Topolino, puentes de piedra, casas Portofino, edificios cívicos, puerto,
     infraestructura WGP y vegetación (en `03_blender/assets/`)
   - ⏳ Integración: colocar assets a lo largo del circuito, casco urbano,
     marina-tapacubos, tribunas en la meta, publicidad
4. **Superficies y físicas AC** — nombres de malla `1ROAD`, `1DIRT`, etc. y
   `surfaces.ini` con grip distinto para asfalto y tierra.
5. **Escenografía** — vallas, gradas, árboles, edificios, decoración.
6. **Lógica de juego** — salida/meta, pit lane, línea de IA (`ai_line`),
   cámaras, `map.png`, iconos, `ui_track.json`.
7. **Exportación** — FBX desde Blender → `.kn5` y prueba en el PC con AC.

## Estructura de carpetas
- `01_referencias/` — imágenes y vídeos de referencia (poner aquí el mapa original)
- `02_trazado/` — trazado digitalizado (JSON) y visor HTML de validación
- `03_blender/` — scripts de Python para Blender y archivos .blend
- `04_track/porto_corsa/` — la carpeta final del mod para Assetto Corsa

## Pendiente de la validación del usuario
- Confirmar que el trazado v0.1 coincide con el mapa (y corregir zonas dudosas:
  curvas 02–03 y el sector 33–40 abajo a la derecha)
- Imagen del mapa en mayor resolución (o el archivo original) en `01_referencias/`
- Longitud aproximada deseada del circuito (¿4 km? ¿5 km?)
- Referencias visuales del entorno (¿de dónde sale el mapa? ¿vídeos?)
