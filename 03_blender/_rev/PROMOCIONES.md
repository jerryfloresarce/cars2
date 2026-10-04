# PROMOCIONES de _rev/escena_rev.blend (fase visual)

`_rev/escena_rev.blend` es la escena congelada que exporta `04_export/hacer_zip.sh` (hoy a través de la copia
`04_export/_zip_src/escena_v11.blend`, mismo md5). Desde el bloque 0 de la fase visual **solo cambia por
`bash 03_blender/_rev/promover.sh "<bloque>" "<hoja A/B>" [nota]`**, y solo cuando `_rev/puerta.json` dice `ok: true`
sobre la candidata actual (`_rev/escena_candidata.blend`, que es lo que escribe `pipeline_escena.sh`).
Cada promoción guarda una copia en `_rev/promociones/escena_vN.blend` (+ `puerta_vN.json`) para poder retroceder
(plan B §2: si un zip vN+1 falla en el PC del amigo, vN sigue en la Release). Borrar las copias antiguas al cerrar la fase.

Mecanismo anti-pisada: `promover.sh` se niega si existe `03_blender/_rev/cola/zip.lock` o si hay un proceso con
`hacer_zip.sh` en su línea de órdenes (Win32_Process). Hoy nadie crea `zip.lock`: cuando el equipo del zip quiera
blindarse del todo, basta `date > 03_blender/_rev/cola/zip.lock` al empezar `hacer_zip.sh` y `rm` al terminar
(petición, no cambio: `hacer_zip.sh` no se toca desde la fase visual). Mientras promueve, `promover.sh` deja
`_rev/cola/promocion.lock`.

Línea base (no es una promoción): `escena_rev.blend` del 04/10/2026 13:00, md5 `a6fb4195c32f20c41299b4b68cff46db`
(= `04_export/_zip_src/escena_v11.blend` del zip v1.1 en cierre); sus cifras están en `_rev/linea_base.json`
(urbanismo 0 fallos / 193 casas, revisar_urbanismo 23, nada_en_pista 11 / 0 tierra, costuras max 2.03 m, Loews 0.000).

| fecha | version | md5 escena_rev.blend | bloque | hoja A/B | nota | avisos de la puerta |
|---|---|---|---|---|---|---|
