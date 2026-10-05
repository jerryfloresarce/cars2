# Verificación independiente — bloque 0, entrega "5 KN5 de ensayo + paleta.json/py + carta de color" (04/10/2026)

Verificador: agente independiente. Intento de refutación de la entrega del propietario (puntos 4 y 7 del bloque 0 del
`FASE_VISUAL_PLAN.md`). Nada del proyecto se ha modificado: todas mis salidas fueron al scratchpad de la sesión; este
fichero es lo único que escribo. `04_export/*` solo se ha EJECUTADO (kn5_check.py).

**Veredicto: APROBADO (aprobado = true). 0 problemas REALES, 1 MENOR, 5 COSMÉTICOS.**

## 1. Qué he ejecutado (órdenes exactas y salida resumida)

| # | Orden | Resultado |
|---|---|---|
| 1 | `python 03_blender/_rev/kn5_ensayo.py --out <scratch>/ensayos_repro` | 5 ensayos en 52.96 s, `TOTAL: 5 ensayos -> TODO OK`, exit 0; zip 1.7 MB |
| 2 | `cmp` de los 5 kn5 regenerados contra los entregados (+ surfaces.ini, map.ini, ui_track.json, map.png, LEEME.txt) | **IDÉNTICOS byte a byte** (generación determinista: reproducible) |
| 3 | `python 04_export/kn5_check.py <kn5> <scratch>/informes_verif/ensayo_x_check.json --no-wait` x5 | exit 0 los 5; `RESULTADO: OK`, 8/8 comprobaciones OK en cada uno (45/45 dummies, parrilla 10.0 m / 7.81 m, bbox físicas 1200 x 60 x 1200 m, 1ROAD [-10,10]x[-130,130], normales 1ROAD 1.000 arriba, 0 bytes sobrantes) |
| 4 | `python 03_blender/_rev/kn5_ensayo.py --solo b,e --sin-check --out <scratch>/ensayos_solo` | opciones documentadas funcionan: 2 ensayos en 0.4 s, exit 0 |
| 5 | `python 03_blender/paleta.py --png <scratch>/paleta_muestras_verif.png` | `verificacion: OK (22 entradas)`, exit 0; PNG idéntico a `renders/qa/paleta_muestras.png` (bbox diff None) |
| 6 | `bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/carta_color.py -- <scratch>/carta_color_verif.png` | `OK carta de color ... 1600x900, BLENDER_EEVEE, 12 esferas + 10 cubos`, 2.3 s, exit 0; **diff máx 0 píxeles** contra `renders/qa/carta_color.png` (versión del working copy, 1476409 B) |
| 7 | `Read renders/qa/carta_color.png` | legible: 12 esferas + 5 cubos "FACHADAS HOY" + 5 "FACH. PROPUESTA", nombre y hex bajo cada uno, cabecera con versión |
| 8 | Script numpy/PIL sobre `ensayos/texturas/` | máscara 2048x2048 RGBA, suma por texel 254..256, media del canal propio por cuadrante 236.6/239.9/239.9/239.9, rayas B=255 en filas 16k y 16k+1 (R=0) y ausentes en 16k+2, disco central (64,64,64,64); detalles 512 RGBA alfa=25 constante; hojas 1024 RGBA alfa0 48.8 % / alfa255 33.1 % / halo(90) 15.4 %; uv_2048 RGB 2048; DDS cabecera 124, flags 0x2100F, 11 mips, 5 592 532 B = esperado |
| 9 | `git status --short` / `git diff --stat` / mtimes | cambios solo en `_rev/*.py`, `renders/qa/carta_color.png` (M) y `fase_visual/paleta_README.md` (??); `04_export/` limpio en git; ficheros prohibidos (porto_corsa.blend 13:00, escena_rev.blend 13:00, construir_pista 12:06, integrar/preparar/asentar/terreno 12:18-12:57, geometria_3d.json 12:57) anteriores a la entrega (15:16-15:31) |

## 2. Contra el plan (secciones 1, 2, 15) y la tarea

- **Formato KN5**: cabecera `sc6969`+5, texturas, materiales (u8 blend, u8 alphaTested, i32 depth, props A/B2/C3/D4, samplers nombre/slot/textura), dummies con matriz m[col][row] (= `np.T.reshape`, misma convención que `kn5_writer_opt.Writer.matrix` l.129-136 y `kn5_check.matriz_desde_floats`), mallas pos3 nrm3 uv2 tan3 + u16 + 29 bytes de cola, mini-malla no renderable bajo cada AC_* (como `kn5_writer_opt` l.783-800). kn5_check lee los 5 hasta el último byte. OK.
- **Desviación 1ROAD 20x260 m + 45 AC_* + 1GRASS 1200 m + muro invisible 60 m** (plan: "plano de 20 m + AC_START_0"): justificada y comprobada en `kn5_check.py`: `AC_REQUERIDOS` l.63-64 son 45 nombres; comprobación (1) exige cada AC_* dentro de la bbox de 1ROAD +30 m; (6) exige extensión XZ 1000..3200 m e Y máx 50..400 m. Sin eso no hay `RESULTADO: OK`. No es defecto.
- **Shaders/samplers/props vs fuentes**: (a) `ksMultilayer_fresnel_nm` con `txDiffuse/txMask/txDetailR/G/B/A/txDetailNM` = tabla 1.1 de `web_multilayer_vao_erosion.md` [V]; `multR/G/B/A`, `detailNMMult`, `fresnelC/EXP/MaxLevel` [V nombres] §1.2; `magicMult` y campo de `detailNMMult` y slots marcados [S] en el LEEME, como pide la tarea. (b)(e) `ksPerPixelAT` + alphaTested 1 + blend 0 + depth 0 + ksAlphaRef 0.5 = `web_treefx.md` §7.2; citas a AcTools comprobadas: `MaterialsProviderDark.cs` l.64 = `case "ksPerPixelAT":`, `ShadowsRendererBase.cs` l.279 = `GetPropertyValueAByName("ksAlphaRef")`. (c) `ksTree` con props LilSki 0.4/0.25/0/1/0/0.5 (§7.1) y normales (0,1,0) [S]. (d) PNG RGB 2048 + DDS con mips. (e) dummy `ANIM_` con matriz propia (0,6,55, 30°) y `castShadows=1`.
- **"No hacer" §15**: 4 (nm4) no: se escribe `_nm`; 12: `ksEmissive = 0` en todos, blend 0 (sin alpha blend), sin ksGrass; 13: ANIM_ en el KN5 principal; 23 (2K): es la hipótesis que el plan manda ensayar, no una violación. OK.
- **paleta.json**: 12 entradas con rgb lineal, srgb_hex, familia_ac, uso; familias comprobadas contra `color_ac.FAMILIAS` real (11 claves, l.307-321): vegetacion/terreno/roca/edificio/agua existen. Hex = sRGB(rgb) verificado (yo recalculé terracota: 0.45→B3, 0.145→6A). Valores = plan A B0.4 (l.84-88) con 3 ajustes documentados. `paleta.py`: `cargar/rgb/srgb/familia_ac` (+ rgba/srgb8/srgb_hex/uso/variante/nombres), docstring de uso, CLI con verificación.
- **carta_color.py**: escena desde cero, no abre ni guarda nada; sol 4.6 W (1,0.96,0.88) 34°/-140°, cielo en rampa, Standard, exposición 0.12, GTAO 12 m: coincide línea a línea con `construir_pista.py` 1566-1618 (y `renderizar_capturas.py` no sobreescribe nada de eso: solo fija resolución). 12 esferas + 10 cubos (5 actuales de `casas_kit_v2.PALETA_FACHADA` l.87 con gamma 2.2 de `_srgb` l.82-84, correcto, + 5 propuestos).
- **paleta_README.md**: citas de `construir_pista.py` (86, 110-114, 125-126, 179, 181, 262-263, 807-808, 1169, 1285, 1516), `roca_lazo` 151, `roca_casino` 98, `casas_kit_v2` 87/95/172-183, `generar_texturas` 306-307, `penon_cara` 303-305, `montana_mclaren` 255-267, `montanas_fondo_v2` 245-247: todas comprobadas y correctas.

## 3. Problemas encontrados

**REAL**: ninguno.

**MENOR-1 — citas a `04_export` ya desfasadas en `paleta_README.md` y `paleta.json`.** El README dice `color_ac.py FAMILIAS l.277-289`, `_REGLAS 347-370`, `familia() 372` (y en la entrega "verificadas hoy"); en el fichero actual están en **307**, **350** y **375** (`grep -n "^FAMILIAS\|^_REGLAS\|^def familia" 04_export/color_ac.py`). `paleta.json._doc` y README §1 citan `analizar_material l.215-258`; el `def` está en **221** (`sed -n 221p 04_export/kn5_writer_opt.py`). Causa: el equipo del zip tocó `color_ac.py` (mtime 15:16) y `kn5_writer_opt.py` (15:20) y lo commiteó a las 15:28; el README es de las 15:29. No bloquea (el README avisa "comprobar antes de editar"), pero el agente del bloque 3 irá a líneas equivocadas: corregir las cuatro cifras.

**COSMÉTICO-1** — README §3 bloque 4 lista `vegetacion_plan.json` como consumidor sin marcarlo "(nuevo)": no existe aún en el repo (lo crea 4.1 del plan). No es ruta inventada, pero conviene la etiqueta.
**COSMÉTICO-2** — `renders/qa/carta_color.png` y `paleta_muestras.png` están trackeados en git fuera de la lista "_rev/, renders/ab, paleta.*, fase_visual/"; el plan (bloque 0.7) y la tarea los sitúan ahí explícitamente, y el working copy (re-render 15:31) difiere del commit a0a3b86 (15:28). Mi re-render reproduce el working copy con diff 0. Solo hay que saberlo al commitear.
**COSMÉTICO-3** — `carta_color.py` usa `bpy.ops` (primitive_*_add, shade_smooth, render.render). La regla "sin bpy.ops" del plan se aplica al pipeline; aquí es una escena QA aislada que renderiza en 2.3 s en `--background`. Sin efecto.
**COSMÉTICO-4** — Tamaño del script: el plan estimaba ~150 líneas y se entregan 949 (carpeta de pista completa, texturas de diagnóstico, autotest). Justificado por kn5_check; solo es más que lo pedido.
**COSMÉTICO-5** — LEEME línea 10 menciona `kn5_check.py 8/8` (ligeramente técnico para el amigo). Las 10 líneas numeradas existen y el apéndice técnico está separado.

## 4. Lo que NO se puede verificar aquí (correctamente marcado [S] por el propietario)

Que AC cargue PNG RGBA embebido, que `ksTree` funcione sin pasar por ksEditor, el efecto real de `magicMult`, qué mip usa AC, el sentido del eje X (espejo del texto), que AC recorte caras traseras, que la carpeta mínima (sin cameras.ini/lighting.ini) cargue. Todo eso lo decide la foto del amigo: es el objetivo del ensayo. Tampoco he verificado los entregables 'ab' ni 'puerta' (otros verificadores).

## 5. Ficheros de esta verificación (scratchpad, fuera del proyecto)

`<scratch>/ensayos_repro/` (regeneración completa), `<scratch>/ensayos_solo/`, `<scratch>/informes_verif/ensayo_[a-e]_check.json`, `<scratch>/paleta_muestras_verif.png`, `<scratch>/carta_color_verif.png`.
