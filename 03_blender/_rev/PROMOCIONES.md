# PROMOCIONES de _rev/escena_rev.blend (fase visual)

`_rev/escena_rev.blend` es la escena congelada que exporta `04_export/hacer_zip.sh` (hoy a través de la copia
`04_export/_zip_src/escena_v11.blend`, mismo md5). Desde el bloque 0 de la fase visual **solo cambia por
`bash 03_blender/_rev/promover.sh "<bloque>" "<hoja A/B>" [nota]`**, y solo cuando `_rev/puerta.json` dice `ok: true`
sobre la candidata actual (`_rev/escena_candidata.blend`, que es lo que escribe `pipeline_escena.sh`).
Cada promoción guarda una copia en `_rev/promociones/escena_vN.blend` (+ `puerta_vN.json`) para poder retroceder
(plan B §2: si un zip vN+1 falla en el PC del amigo, vN sigue en la Release). Borrar las copias antiguas al cerrar la fase.

Mecanismo anti-pisada: `promover.sh` se niega si existe `03_blender/_rev/cola/zip.lock` o si hay un proceso con
`hacer_zip.sh` en su línea de órdenes (Win32_Process). `hacer_zip.sh` crea `zip.lock` (fecha + pid) al empezar y lo borra con `trap EXIT` (remate del bloque 0,
04/10 16:10): el export y la promocion no pueden solaparse.
(petición, no cambio: `hacer_zip.sh` no se toca desde la fase visual). Mientras promueve, `promover.sh` deja
`_rev/cola/promocion.lock`.

Línea base (no es una promoción): `escena_rev.blend` del 04/10/2026 13:00, md5 `a6fb4195c32f20c41299b4b68cff46db`
(= `04_export/_zip_src/escena_v11.blend` del zip v1.1 en cierre); sus cifras están en `_rev/linea_base.json`
(urbanismo 0 fallos / 193 casas, revisar_urbanismo 23, nada_en_pista 11 / 0 tierra, costuras max 2.03 m, Loews 0.000).

## Fallos heredados documentados (ACOTACIONES_COORDINADOR_F1.md 3) — candidata F1 r4 (NO promovida)

Candidata `_rev/escena_candidata.blend` md5 `1f5c2d6e0312a5ce63d6e2a07707e47e` (05/10 09:15, `_rev/logs_f1_r4/`), RNG de `integrar_escena`
determinista por zona. `_rev/puerta.json` **ok: false** por UN motivo que no es de `revisar_urbanismo`: `asentar.arboles_quitados` 4 > base 3
(VEG_adelfa.004/.013 y VEG_palmera.011 = jardines del casino en los cantiles del peñón, pendiente 2.7-3.5, 'ladera imposible' 2.8-4.7 m;
VEG_arbusto.130 (-256, 555) 1.64 m en 1.2 m; terreno IDÉNTICO a la base a < 10 m en los 4: sorteo nuevo por la semilla por zona, no F1).
Arreglo ya en `integrar_escena.zona_casino` (filtro de pendiente de zona_montana en los jardines) pero NO en esta candidata (regeneración única).
`revisar_urbanismo` 13 fallos (base 23, r3 27), 0 tipos nuevos; los 13 son HEREDADOS (mismo objeto y mismo tipo que en la base 13:00):
casa_flotante CASAS_casa.066 / CASAS_casa.146 / LOEWS_rotonda.001; casa_muro CASAS_casa.066 (CAMINO_muro.130 = .132 de la base, otro número);
losa_hierba CALLE_plaza / CALLE_plaza_ayto; plaza_muro CALLE_plaza_ayto; prop_camino CAMINO_cartel.003; prop_pista + prop_pitlane
PIT_muro_morro; sendero_volado CAMINO_tierra.001 y .003; sendero_enterrado CAMINO_tierra.001 (1 vértice 0.24 m; base 7 / 0.42 m).
Resto de la puerta igual o mejor que la base: enterrados 47 < 57, flotaban 24 < 28, dudosos 0 < 8, bancales_mal 0 < 1, nada_en_pista 11 / 0 tierra,
urbanismo 193 casas / 0 fallos, costuras 2.03 m (= base, aviso).

## Cierre de F1 (ACOTACIONES_COORDINADOR_F1.md 13/14) — candidata F1 final (promovida como v1)

Regeneración ÚNICA `bash _rev/pipeline_escena.sh _rev/logs_f1_final` (05/10 09:38 -> 09:42, `PIPELINE rc=0`, `ERRORES: ninguno`) con el filtro
de pendiente de `zona_casino` (pendiente > 0.62 o anillo d=0.6 > 1.25) y los 3 literales de la decisión 14 en paleta. Candidata md5
`31c18b1bf77ba551eafa288d44b9275f`. `_rev/puerta.json` **ok: true**, 0 motivos, 1 aviso (costuras 2.03 m = base):
`asentar.arboles_quitados` **1** (base 3, r4 4: VEG_adelfa.004/.013 y VEG_palmera.011 ya no se plantan en los cantiles; queda VEG_arbusto.130
(-256, 555), 'ladera imposible' 1.64 m en 1.2 m, terreno idéntico a la base a < 10 m, max|dz| 0.0000). **No hizo falta la tolerancia de la
decisión 13**: `linea_base.json` no se toca. Enterrados 46 (base 57), flotaban 25 (28), bancales_mal 0 (1), revisar_urbanismo 13 (base 23):
los MISMOS 13 heredados de la lista de r4 de arriba (mismo objeto y tipo, `urbanismo_informe_candidata.json`). Paleta: FUERA 33 -> 30
(MAT_VEG_cipres_b, MAT_VEG_retama y MAT_fondo_marino pasan a 'exacto'). A/B corto en `renders/ab/f1_final/` (12 tomas x 2 modos).

| fecha | version | md5 escena_rev.blend | bloque | hoja A/B | nota | avisos de la puerta |
|---|---|---|---|---|---|---|
| 2026-10-05 09:47 | v1 | 31c18b1bf77ba551eafa288d44b9275f | F1 cierre (bloques 3, 2.1, 2.2, 1.1-1.2, 7.1, 4.1) | renders/ab/f1_final | director r4 + decision 13/14 | terreno: costuras max 2.03 m (objetivo del plan < 0.6 es del bloque 1; la puerta exige "no peor que la base") |
