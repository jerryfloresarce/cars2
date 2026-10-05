# Verificación independiente — bloque 0 "Capturas A/B, modo AC, medidas y antes congelado" (04/10/2026, verif_f0_ab_1)

**Veredicto: APROBADO (ningún problema REAL; 5 MENORES y 7 COSMÉTICOS abajo).** Todo se ha ejecutado de verdad
(4 Blender por la cola, máx. 2 a la vez; python del sistema para montaje/medidas). No se ha modificado ningún fichero
del proyecto salvo este informe; mis salidas están en el scratchpad (`.../scratchpad/verif/`).

## 1. Qué se ha comprobado y con qué órdenes

| # | Comprobación | Orden (desde la raíz del proyecto) | Resultado |
|---|---|---|---|
| 1 | Ficheros de la entrega existen | bucle `[ -e ]` sobre los 14 ficheros/carpetas listados | 14/14 OK; rutas del README existen (las de `renders/ab/roca/` son ejemplos) |
| 2 | Ficheros prohibidos intactos | `git status --short -- 04_export 03_blender/renderizar_capturas.py integrar_escena.py ... porto_corsa.blend _rev/escena_rev.blend geometria_3d.json _rev/pipeline_escena.sh` | vacío (nada modificado ni nuevo); `escena_rev.blend` mtime 13:00, md5 `a6fb4195…` = `escena_antes_visual.blend` |
| 3 | `tomas_capturas.py` lista por la cola | `blender_cola.sh --python _rev/tomas_capturas.py -- --blend _rev/escena_antes_visual.blend --geom _rev/geometria_rev.json` | exit 0, **67 tomas**; las 21 BASE coinciden con `camaras.json` a 0.05 m salvo 36 (36 m: movida por camara_segura al congelar, documentado) |
| 4 | `construir_tomas` = `renderizar_capturas.py` l.45-330 | `cmp_codigo.py` (diff normalizado sin comentarios/indentación) | **1 línea distinta**: el guard `_yc = None`; las 5 tomas rehechas (15/34_desde_pista/40/43/47b) conservadas |
| 5 | Copia fiel del writer | `cmp_codigo.py` sobre `srgb_to_lin`, `lin_to_srgb`, `imagen_lineal`, `_socket`, `analizar_material` y la fórmula de `construir_textura` | idénticas (solo difiere el docstring); GROUND_PREFIXES/DECO_SIN_SOMBRA/DECO_MAT_SIN_SOMBRA/TEX_SIZE iguales a `kn5_writer_opt.py` l.69-81; renombres iguales a `exportar_ac.py` l.61-162 |
| 6 | Re-render normal con cámaras congeladas | `capturas_ab.py -- --blend … --camaras renders/ab/_base_antes/camaras.json --out <scratch>/normal2` | exit 0, 21 PNG, 35 s; log loc/tgt/lens = `camaras.json` (desvío ≤ 0.05 m por redondeo del log); 0 avisos DENTRO |
| 7 | Re-render modo AC | ídem `--modo-ac --out <scratch>/ac2` | exit 0, 26 s; mismas cifras que el propietario (roca 22695 caras/5 obj, sombras 539/2791/8/0, materiales 387/98/3, eevee raytracing+fast_gi off); **0/21 tomas distintas frente a `ac/`** |
| 8 | Calibración (diff de píxel) | `diff_dirs.py normal calibracion normal2` | normal vs calibracion: 4/21 con max 2 (= `calibracion_calib.json`); normal vs normal2: **6/21**, max 2, hasta 0.0045 % px (62: 65 px, 61: 54 px); calibracion vs normal2: 5/21 |
| 9 | Cámara DENTRO de geometría | `--camaras cams_dentro.json` (49 y 53 hundidas 25/40 m) | exit 0; `ab.log`: "AVISO 49…: camara DENTRO de geometria (AGUA_fondo)… se renderiza igual", ídem 53 (TERRENO); PNG generados; 55 (dentro del túnel) sin falso aviso |
| 10 | Fusión de `--guardar-camaras` + camara_segura reproducible | copia de `camaras.json` → `--set BASE --solo 60,36 --guardar-camaras <copia>` | 21/21 tomas conservadas, 36 reproducida exactamente (misma loc congelada), `_meta.actualizaciones` añadida |
| 11 | `montaje_ab.py` | `--antes normal --despues normal2 --diff` / `--tol-max 2 --tol-pct 0.01` / `--antes ac --despues ac2 --diff --modo ac` / rótulos BLENDER-"MODO AC" / toma faltante | exit 3 / 0 / 0 / 0 / 3 (`faltan`: 20); 105 pares, hojas 3212x14610 y 1612x3180; rótulos legibles (toma, A/B, modo, etiqueta, fecha, diferencia) |
| 12 | `medir_capturas.py` | `medir_capturas.py <scratch>/normal2 <scratch>/ac2 --camaras …/camaras.json` | exit 0, 8 s; **todas las métricas idénticas** (delta 0.0000) a `medidas.json` del propietario pese al ruido de píxel |
| 13 | Igual que `renderizar_capturas.py` | `diff_dirs.py renders/capturas renders/ab/_base_antes/normal` (11 tomas comunes de las 13:00) | 7 idénticas, 3 con max 1 (ruido), 36 con max 16 en 5.9 % px (sub-píxel por redondeo a 0.1 mm de camara_segura: explicado por el propietario) |
| 14 | Inspección propia de la escena (`inspect_ac.py`, solo lectura) | por la cola | view transform Standard / exposición 0.12 ya en el blend (= `construir_pista.py` l.1611-1612); 484 materiales, 0 con `use_nodes=False`, 97 con imagen de color, 0 mallas mixtas MAT_VEG/otros, 8 solo-MAT_VEG por material, 427/427 objetos de suelo proyectan sombra en modo normal; `sc.eevee` sin `use_gtao` (5.1), con `use_raytracing`/`use_fast_gi` True |
| 15 | Imágenes miradas | `AB_49`, `AB_56`, `AB_60`, `AB_61`, hojas (miniaturas) y la cámara hundida | modo AC plausible: sin sombras de árboles/terreno, terreno = tile verde pálido, rocas planas; 56 tapada por el macizo (documentado); 61 a 100° muestra dique y pantalanes tras la valla |

## 2. Problemas

### REAL (bloquean): ninguno.

### MENOR
1. **La calibración no es 0 en modo normal y el ruido es algo mayor que el citado.** 4/21 (propietario) y 5-6/21 (mis dos pasadas) tomas con max|d| 1-2/255; hasta **0.0045 % px** (62_tribuna: 65 px; 61: 54 px), no "≤ 0.0015 %". En modo AC (raytracing y fast GI apagados) es **0/21 determinista**: el ruido viene del raytracing/fast GI de EEVEE, no de las cámaras. El criterio 1 del plan (diff 0) solo se cumple en modo AC, que es el que decide "bloque cerrado". Decisión del coordinador: `--tol-max 2 --tol-pct 0.02` (0.01 queda justo) para el modo normal, 0 para el modo AC. Prueba: `diff_dirs.py`, `calibracion_calib.json`, `montaje_ab.py --diff` exit 3/0.
2. **Tomas 61 y 56 se apartan del esbozo.** 61 va girada 100° (esbozo entender_agua §9.2: 35°), con motivo documentado en `camaras.json["61…"]["desc"]`; 56 elige el azimut con "más mar" (190°, S) sin tener en cuenta la oclusión del relieve y hoy sale tapada por el macizo (plan C §0.2 proponía azimut hacia (300,-300) ≈ 164°). Ambas documentadas; a ratificar por el coordinador (o toma nueva 56b/61b con otro nombre, regla 16).
3. **`--guardar-camaras` sobre un JSON existente SUSTITUYE las tomas que se vuelven a pedir** (capturas_ab.py l.503-511; probado con 36 y 60 sobre una copia). Conserva las demás, pero si alguien relanza el "antes" tras una regeneración, pisa cámaras congeladas sin aviso (contra la regla 16 del plan). Conviene negarse a sustituir una toma existente salvo `--forzar`.
4. **Modo AC no aplica `color_ac.calibrar_todos()`** (el writer sí, `kn5_writer_opt.py` l.304-305). La razón del propietario es correcta (esos colores compensan la luz de AC y bajo la luz de Blender darían una imagen falsa), pero la tarea decía "materiales reducidos a lo que exporta el writer": el coordinador debe ratificar que el modo AC se juzga con colores sin calibrar.
5. **`siluetas_20_120` cuenta solo 10 tipos** (medir_capturas.py l.34-35): quedan fuera 1004 de 2799 objetos (VEG_arbusto 399, VEG_adelfa 208, OLI_matorral 161, VEG_roca 124, VEG_penon_arbusto 70, **VEG_plazoleta 42**). Excluir arbustos/matorral/roca es defendible ("árboles"), pero VEG_plazoleta puede ser árbol: documentarlo en `_doc` o incluirlo.

### COSMÉTICO
6. `medidas.json["_doc"]` recorta cada métrica a la primera línea del docstring (riqueza, bandas_blancas, pared_lisa y siluetas quedan a medias) y no documenta pct_roca/pct_azul (medir_capturas.py l.159).
7. README punto 5 cita "≤ 0.0015 %" (ver MENOR 1); la entrega cita hojas "3212x14250" pero miden 3212x14610 (cabecera de 70 px).
8. Constantes del writer y renombres de `exportar_ac.py` están copiados, no leídos (capturas_ab.py l.70-83): hoy coinciden línea a línea, pero si `04_export` cambia hay deriva silenciosa; anotar en `PETICIONES_04_EXPORT.md` o importar cuando abra.
9. Set `carificacion` omite 02_meta_y_puerto y 29_boxes_desde_pista, que cita la cabecera §10 del plan (están en `csp`); `paleta` coincide exactamente con el plan §3 (05, 06, 09, 14, 16, 21, 22, 39).
10. En los pares BLENDER vs MODO AC hechos con `--antes normal --despues ac` el pie dice "modo Blender" (los rótulos de cabecera sí dicen MODO AC).
11. `hoja_base_antes_piloto.png` pesa 33 MB (15 tomas piloto+postal a 1600 px): usable; `--ancho-piloto 1200` la dejaría en ~18 MB.
12. Git: las versiones finales de los 4 scripts siguen sin commitear (el commit a0a3b86 de las 15:28 arrastró borradores: `git diff` muestra la fusión de cámaras, la roca del terreno en modo AC, `pct_verde` y las tolerancias); `renders/qa/carta_color.png` modificado es del bloque paleta, no de este.

## 3. Conclusión
Las 6 piezas del bloque (tomas, capturas_ab con --modo-ac, montaje, medidas, antes congelado, README) existen, corren con las órdenes
documentadas y sus resultados se reproducen: cámaras idénticas antes/después, modo AC determinista y fiel al writer (funciones
copiadas literalmente, sombras según los renombres de export), medidas reproducibles al 0.0000. Lo único que no cumple la letra
del plan es el diff 0 en modo normal (ruido 1-2/255 del raytracing de EEVEE, < 0.005 % px), que el propietario reportó con causa
y que se resuelve con una tolerancia que debe fijar el coordinador.
