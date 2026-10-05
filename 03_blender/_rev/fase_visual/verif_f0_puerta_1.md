# Verificación independiente — F0 bloque 0 "puerta" (pipeline a candidata, puerta de calidad, promoción, presupuesto KN5, peticiones)

Verificador: 04/10/2026 15:20-15:32. Solo se ha escrito este fichero; todas las salidas de prueba fueron al scratchpad
(`C:/Users/arcej/AppData/Local/Temp/claude/.../scratchpad/`). No se lanzó Blender (nada del bloque lo necesita) ni
`pipeline_escena.sh` completo. **Veredicto: APROBADO (0 REAL, 5 MENOR, 5 COSMÉTICO).**

## 1. Lo que se ha ejecutado (órdenes reales y cifras)

| # | Orden | Resultado |
|---|---|---|
| A | `python _rev/puerta_calidad.py --out <scratch>/puerta_actual.json` | `ok: true`, 0 claves distintas de la base, 1 aviso (costuras 2.03 m), exit 0 |
| B | `... --qa renders/qa --logs _rev/logs_final --blend _rev/escena_rev.blend --snapshot <scratch>/linea_base_verif.json` | `valores` idénticos a `_rev/linea_base.json` del propietario (`==` True); con `--out` ok:true exit 0 |
| C | `regresion.py` (27 casos: copias de renders/qa + logs_final rotas de UNA en UNA) | 26 según lo esperado: sano ok; costuras +0.04 m ok (tolerancia); 24 regresiones -> `ok:false` exit 1 con el motivo correcto (casa_muro 1->2 con total igual, total 24, farola en `dirt`, 12 invasores, arboles_quitados 4, flotaban 29, celdas invaden 3, hierba 5, fosos 7, costuras 2.50, celdas>0.6 140, Loews 0.120, QA fallos 1, casas 185, ERRORES 2, 180 casas, línea COSTURAS/QA/ERRORES/OK borradas, asentar.json/integrar.log ausentes, json roto, sin linea_base). **1 inesperado**: informe sin clave `total_fallos` -> ok:true (ver M1) |
| D | `kn5_presupuesto.py 04_export/kn5/informe_check_opt.json` (fichero del 02/10, antes de las 15:24) | 5.26 M / 572 / 441 / 11.96 MiB / 338.81 MiB, veg 1.73 M, exit 0, 7 avisos vs base fisica |
| D' | ídem sobre el `informe_check_opt.json` NUEVO (el zip v1.1 lo regeneró a las 15:24:42) `--sin-base` | 4.63 M / 602 / 465 / 13.31 MiB / 272.5 MiB, veg 1.34 M, exit 0 |
| D'' | `_fisica/informe_check_fisica.json --base kn5/informe_check_opt.json` / `--estricto` / fichero inexistente / sintético (6.5 M tris, 900 mallas, 500 MiB) | exit 0 con 14 avisos / exit 1 / exit 2 / exit 1 con 3 `TOPE SUPERADO` |
| E | `puerta_calidad.py --kn5 <opt>` / `--kn5 <sintético>` | ok:true exit 0 / ok:false 3 motivos exit 1 |
| F | `bash -n pipeline_escena.sh`; `SOLO_COPIA=1 REV_DIR=<tmp> bash _rev/pipeline_escena.sh E:/.../_rev/logs_final` | sintaxis ok; 1 s; 8 ficheros en `<tmp>`; md5 `escena_candidata` = `porto_corsa.blend` = a6fb4195; manifiesto con `logs` absoluto; puerta ok:true; **no** creó `_rev/logs`; ningún `cp` a `escena_rev.blend` fuera de comentarios |
| G | `prueba_promover.sh` (REV_DIR temporal con ficheros falsos) | v1 OK (md5 escena_rev = candidata = promociones/escena_v1.blend; 5 json `_rev` copiados; `promocion.lock` retirado), v2 OK (N incremental), md5 distinto -> exit 3, `ok:false` -> exit 3, `cola/zip.lock` -> exit 3, sin argumentos -> exit 2, `SIMULAR=1` -> exit 0 y nada cambia, falta `geometria_candidata.json` -> exit 3, falta `puerta.json` -> exit 3; `PROMOCIONES.md` de prueba con 2 filas bien formadas |
| H | Falso `hacer_zip.sh` (bash de fondo que solo duerme 50 s) + `REV_DIR=<tmp> bash _rev/promover.sh ...` | `NO SE PROMUEVE: hay 4 proceso(s) ejecutando hacer_zip.sh`, exit 3, sin v3 |
| H' | Export REAL del zip v1.1 ocurrió durante la verificación (15:23-15:25, `04_export/_zip_logs/5_empaquetar.txt`) | la misma orden de PowerShell de `promover.sh` contó **3 procesos** a las 15:24 y **0** a las 15:26: el lock por proceso funciona con el export de verdad |
| I | `SIMULAR=1 bash _rev/promover.sh "verificador f0" "ninguna (simulacion)"` sobre el `_rev` REAL | "autorizaría v1", exit 0; `escena_rev.blend` md5 a6fb4195 y mtime 13:00:37 intactos; `PROMOCIONES.md` 21 -> 21 líneas; `promociones/` vacío |

Formatos comprobados contra las fuentes: las 7 regex de `valores_terreno/valores_integrar/valores_urbanismo_log` casan
con las líneas 9/14/15/16/18-24/63-69/75/85 de `logs_final/preparar_geometria.log`, 125/134 de `urbanismo.log` y
50/218/227 de `integrar_escena.log`; la QA de `urbanismo.py` sí trae `fallos` (25 tipos, todos 0). Claves de
`informe_check_opt.json` (`totales.total_triangulos/n_mallas/n_materiales/bytes_texturas/bytes_fichero`, `mallas[].ruta/
n_triangulos/materialId`, `materiales[].samplers[].textura`, `texturas[].tamano`) = las que lee `kn5_presupuesto.py`.
Nombres citados en PETICIONES existen en `04_export` (`escribir_texturas_y_materiales`, `separar_roca_terreno`,
`KEEP_PREFIXES`, `NO_OBSTACULO`, `GROUND_PREFIXES`, `TEX_SIZE/TEX_MAX`, `generar_ext_config`, `_REGLAS`,
`calibrar_todos`); `repartir_terreno` no existe porque es la función propuesta (P10). `puerta_README.md` = 10 líneas.

## 2. Ficheros prohibidos: no tocados por este bloque

mtimes: `integrar_escena.py` 12:57, `preparar_geometria.py` 12:52, `construir_pista.py` 12:06, `asentar_objetos.py` 12:18,
`terreno_montana.py` 12:49, `urbanismo.py` 12:44, `urbanismo_escena.py` 12:23, `porto_corsa.blend` 13:00, `geometria_3d.json`
12:57, `_rev/escena_rev.blend`/`geometria_rev.json`/`urbanismo_rev.json` 13:00:37 (md5 a6fb4195 = `04_export/_zip_src/
escena_v11.blend`); `assets/` sin ficheros posteriores a las 14:40. En `04_export` cambiaron `hacer_zip.sh` 15:02,
`color_ac.py` 15:16 y `kn5_writer_opt.py` 15:20: son del equipo del zip (coinciden con su export de 15:23 y con
`_rev/color_ac/CAMBIO_KN5_WRITER.md`); `git diff 04_export` no menciona candidata/puerta/promover/zip.lock. Lo demás
modificado en la ventana 14:45-15:20 fuera de `_rev/` es de otros bloques (`paleta.json/py`, `texturas/cc0/*`,
`renders/qa/paleta_muestras.png`, `FASE_VISUAL_PLAN.md`).

## 3. Problemas

**REAL (bloquean): ninguno.**

**MENOR**
- M1 `puerta_calidad.py` l.98 `inf.get('total_fallos', -1)`: un `urbanismo_informe.json` sin esa clave (truncado/malformado)
  da -1 <= base y **pasa** (regresion.py caso 3: ok=True exit=0). Mismo patrón en `nada.get('n', len(fallos))` l.108 y
  `total_avisos` l.100. Arreglo: ausencia de clave esencial = motivo (como ya hace con las líneas de los logs).
- M2 Datos rancios: `pipeline_escena.sh` l.65-68 no comprueba el exit de `nada_en_pista.py` ni de `revisar_urbanismo.py`
  (comportamiento previo, el propietario solo debía tocar el paso final). Si uno falla, `renders/qa/*.json` del pipeline
  anterior se copian como `*_candidata.json` y la puerta los juzga (iguales a la base -> ok:true). La puerta no
  comprueba frescura: `urbanismo_informe.json` y `asentar.json` traen `fecha` ("2026-10-04 13:00") y `blend`;
  `nada_en_pista.json` solo `blend`. Arreglo barato en la puerta: exigir `fecha` >= mtime de `preparar_geometria.log`
  del manifiesto y que `nada_en_pista.log` tenga la línea `NADA_EN_PISTA` sin `Traceback`. Conviene cerrarlo antes de
  la primera promoción real; no bloquea la entrega.
- M3 Costuras: el plan (§1 criterio 3) dice "costuras < 0.6"; la puerta exige "<= base + 0.05 m y celdas > 0.6 <= base"
  y lo deja en aviso. Hoy la base es max 2.03 m / 127 celdas > 0.6 (`preparar_geometria.log` l.16), así que el literal
  es incompatible con "puerta.json sobre la escena actual = ok: true" (plan §2 Verificación). Documentado con honestidad
  por el propietario; necesita decisión del coordinador (¿objetivo del bloque 1 en vez de criterio de puerta?).
- M4 `kn5_presupuesto.py` l.28-29 usa MiB (450·1024² = 471.9 MB decimales; 80 MiB = 83.9 MB) mientras el plan mide en MB
  decimales ("hoy 355 MB" para 355.267.388 bytes; zip 172/148.7 MB). 4.9 % más permisivo que el plan e imprime
  "272.50 MB" para un KN5 que `ls` da como 285.7 MB. Arreglo: topes 450e6 / 80e6 y etiquetar la unidad.
- M5 `PETICIONES_04_EXPORT.md`: el plan §2 punto 6 pide "P1-P10 del plan B §1.6 **+ la lista X**"; faltan los puntos 3
  (texturas por objeto sin `calibrar_todos` + tangentes reales desde la UV, hoy ficticias l.448-458) y 7 (`color_ac._REGLAS`
  con matorral/seca/cesped/caliza; `calibrar_todos` salta `ac_shader != ksPerPixel`) de §12 (`grep -c "tangente|_REGLAS"` = 0).

**COSMÉTICO**
- C1 `pipeline_escena.sh` l.10-11 y `puerta_README.md` l.8 dicen que `hacer_zip.sh` exporta `escena_rev.blend`; hoy exporta
  `04_export/_zip_src/escena_v11.blend` (copia, mismo md5). `PROMOCIONES.md` sí lo explica bien.
- C2 `linea_base.json.fuentes` con rutas relativas y separadores mezclados (`renders/qa\\urbanismo_informe.json`).
- C3 PETICIONES cita `escribir_texturas_y_materiales` l.301-339; hoy está en l.309 de `kn5_writer_opt.py` (el fichero lo
  cambió el equipo del zip a las 11:49 y 15:20). El propietario avisa de que las líneas son del informe de la mañana.
- C4 Las cifras del resumen del propietario para `informe_check_opt.json` (5.26 M / 572 / 441 / 338.8 MB) ya no son las del
  fichero: el zip v1.1 lo regeneró a las 15:24:42 (4.63 M / 602 / 465 / 13.31 MiB / 272.5 MiB; sigue dentro, exit 0).
- C5 `promover.sh` l.37: la detección por línea de órdenes da falso positivo si la propia orden que lanza `promover.sh`
  contiene el texto "hacer_zip.sh" (p. ej. en la nota o en un `bash -c` envolvente): falla hacia el lado seguro.

## 4. No verificable / pendiente
- "Resto de `pipeline_escena.sh` byte a byte igual": no hay copia previa del script; la secuencia de pasos coincide con
  la salida de `_rev/logs_final_pipeline.out` (que terminaba en "congelada: _rev/escena_rev.blend", línea ya ausente).
- El pipeline completo con la copia a candidata solo lo probará el coordinador en la primera regeneración (prohibido aquí).
- `zip.lock` sigue sin crearlo nadie (petición al equipo del zip en `PROMOCIONES.md`); hoy el seguro es el proceso.
