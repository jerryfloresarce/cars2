# Director de arte — F1 (fase visual), ronda 1 — 04/10/2026 ~20:40

**Veredicto: NO APROBADO** (`aprobado = false`). Puerta `ok: false` (5 motivos), 2 problemas REALES de artefacto
(rutas de textura relativas -> escena candidata magenta fuera de `03_blender/`; horizonte blanco "iceberg"), KPIs de
relieve sin alcanzar, y el integrador no dejó el "después" del A/B (solo el "antes" del set paleta).

Candidata juzgada: `_rev/escena_candidata.blend` md5 `3a407e9b62eff04b60740f50bf93edea` (20:07), logs `_rev/logs_f1_r1/`,
`_rev/puerta.json` 20:07. Base: `_rev/escena_antes_visual.blend` (md5 a6fb4195…, = `renders/ab/_base_antes/`).

## 0. Qué había y qué he tenido que generar

- En `renders/ab/f1_r1/` SOLO existe el "antes" del set `paleta` (8 tomas: 05/06/09/14/16/21/22/39) en modo normal y AC
  (`antes_paleta/`, `antes_paleta_ac/`, `camaras_paleta.json`, 20:05-20:06). **No hay `despues*/`, ni `AB_*.png`, ni
  `hoja_*`, ni `medidas.json`.** El pipeline terminó a las 20:07 (después del corte del integrador) y nadie lanzó el paso 3
  de `ab_README.md`.
- Para poder juzgar he renderizado yo el "después" con las cámaras congeladas de la BASE (`renders/ab/_base_antes/camaras.json`,
  21 tomas) sobre la candidata, 2 pasadas por la cola (`blender_cola.sh`): modo AC (52 s) y modo normal (67 s), SIN escribir
  nada en el proyecto: todo en el scratchpad de la sesión
  `C:/Users/arcej/AppData/Local/Temp/claude/E--Escritorio-claude-pc-arnau-aseto-corsa/1a7b6c0c-72d8-44ab-af11-95e782d87886/scratchpad/f1_r1/`
  (`despues/`, `despues_ac/`, `AB_*.png`, `AB_ac_*.png`, `hoja_f1_r1_{piloto,aereas}{,_ac}.png`, `medidas.json`, `medidas_ac.json`).
  Montaje con `montaje_ab.py` (antes = `_base_antes/{ac,normal}`) y medidas con `medir_capturas.py`. Son efímeros: el
  integrador debe repetirlos dentro de `renders/ab/f1_r1/` (es trivial: 2 comandos + montaje + medidas, ~3 min).
- El set `paleta` (05/06/09/14/16/22/39) queda SIN "después": pendiente del integrador en la misma tanda.

## 1. Hallazgo bloqueante n.º 1: la candidata renderiza MAGENTA fuera de `03_blender/` (modo normal)

En las 21 tomas de modo Blender el TERRENO, los ARCÉN_*, la montaña-coche, el talud del túnel y la roca del lazo salen
rosa (#FF81FF: textura ausente). Muestras `despues/51_piloto_s1700.png` (1300,550) = rgb(255,129,255); (1500,300) =
rgb(255,132,255); `despues/07_tierra_subida.png` (400,600) = rgb(255,99,255); `despues/56` (1500,520) = rgb(255,119,255).

Causa (comprobada descomprimiendo el .blend con el `zstandard` del python de Blender, sin abrir Blender): en
`escena_candidata.blend` los datablocks Image nuevos de F1 llevan ruta RELATIVA: `//texturas\terreno_mask.png`,
`//texturas\hierba_seca_d.png`, `caliza_d.png` (x14)… mientras que en `escena_antes_visual.blend` `hierba_d.png` /
`tierra_d.png` llevan ruta ABSOLUTA `E:\...\03_blender\texturas\hierba_d.png`. `//texturas/` resuelto desde `_rev/` no
existe -> magenta. En `03_blender/porto_corsa.blend` (misma carpeta) sí resuelve, por eso nadie lo vio en las pruebas
(`_tmp_mascara/escena_v2.blend` y `_tmp_materiales` se guardaron abriendo un blend ya existente -> absolutas).
Mecanismo: `construir_pista.py` arranca con `--factory-startup` (fichero sin nombre) y hace `save_as_mainfile(OUT_BLEND)`
(l.2076) con `relative_remap=True` por defecto: al guardar por primera vez Blender convierte TODAS las rutas a relativas,
aunque `_imagen()` (l.131-150) las cargue absolutas. `aplicar_texturas.py` (l.178, "absoluta, sin '//'") no sufre esto
porque abre `porto_corsa.blend` y guarda encima.

Consecuencias: (a) el A/B en modo normal de ESTA ronda es inválido (todas las tomas = regresión); (b) `promover.sh`
copiaría a `_rev/escena_rev.blend` una escena con texturas rotas, y `04_export/_zip_src/escena_v11.blend` y el writer
(`construir_textura` lee `bpy.path.abspath(img.filepath)`) heredarían el fallo; (c) el modo AC NO lo detecta (pinta
color plano / tile tintado desde disco por nombre), por eso las medidas AC de abajo sí valen.

Arreglo (1-2 líneas, propietario **mascara**, `construir_pista.py` es suyo en F1): `bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND,
relative_remap=False)` en l.2076, o `bpy.ops.file.make_paths_absolute()` justo antes de guardar; y, de red de seguridad
(integrador), `pipeline_escena.sh` puede comprobar tras la copia que ningún Image tenga `//` (o empaquetar). Prueba:
descomprimir el blend y `grep` `//texturas` = 0; render de `49` en modo normal desde `_rev/` sin magenta.

## 2. Hallazgo bloqueante n.º 2: puerta `ok: false`

`_rev/puerta.json` (20:07), 5 motivos, todos "peor que la base":
- `revisar_urbanismo` 25 fallos > base 23: `prop_camino` 1 -> 2, `objeto_salto_grande` 8 -> 10 (desaparece `arbol_calle` 1 -> 0).
  Casa_pista/casa_muro/losa* iguales (1/0/2): no hay tipos prohibidos nuevos.
- `asentar`: `arboles_quitados` 3 -> 4, `flotaban_mas_0_6` 28 -> 31, `enterrados_mas_0_6` 57 -> 72, `dentro_de_muro_quitados` 0 -> 1.
- Aviso (no bloquea): costuras max 2.03 m = base (pueblo_alto_mar 2.03 / casino_mar 2.01 / pueblo_subida_ladera 1.49 con 74 celdas > 0.6).
- Todo lo demás igual o mejor: 193 casas, 0 fallos de plan, nada_en_pista 11 (tierra 0), invaden 0, hierba_asfalto 0, fosos 0,
  Loews 0.000, integrar "ERRORES: ninguno".

Origen: el relieve de F1 (dz hasta 21 m, 13 522 celdas > 0.5 m, 7 683 > 2 m; `medir_relieve.log`) mueve objetos que los
inspectores corrigen, pero los contadores superan la base. Propietario **terreno**: o bien reducir el dz en las zonas de
props/caminos (las 2 `prop_camino`, los 2 `objeto_salto_grande` nuevos: ver `renders/qa/urbanismo_informe.json`), o bien pedir al
coordinador re-basar `linea_base.json` tras F1 con justificación (son 15 enterrados > 0.6 m más; no es cosmético: hay que
mirar cuáles).

## 3. Tomas del set BASE: ok / mejora / regresión (criterio = MODO AC; el modo normal es inválido por §1)

| Toma | AC | Nota (cifras de `medidas_ac.json`, antes -> después) |
|---|---|---|
| 49_piloto_s300 | **mejora** | césped 0.02 -> 0.00 %; talud y arcén hierba seca #F4EDBC; cipreses #34503A; en el talud derecho se ve la frontera roca/hierba en escalera (celda 4 m). Horizonte: 0 % (no hay línea de mar en el cuadro). |
| 50_piloto_s800 | **mejora** | la mejor toma de la ronda: fachadas azafrán/siena/pompeyano, copas oliva, laderas doradas con muros; verde 11.0 -> 3.1 %; siluetas 20-120 m 1 -> 6. |
| 51_piloto_s1700 | **mejora (con reserva)** | desmonte derecho más alto (silueta sube claramente sobre el horizonte); tonos: hierba seca #F4EDBC (V 0.96), roca #DDD2C0 (V 0.87), tierra de pista tan: son 3, pero ΔV hierba/roca 0.09: se leen como "crema y crema". Riqueza 1.07 -> 0.50 (terreno plano en AC, ver §5). Se pierden 2 árboles de la izquierda (siluetas 1 -> 1). |
| 52_piloto_s2900 | **mejora** | pinos parasol oliva, loma dorada; verde 10.3 -> 0.8 %; siluetas 6 -> 7. Horizonte 0 % (no hay mar en el cuadro). |
| 53_piloto_s3400 | **mejora** | fachada ocre naranja #D88A4C, cúpulas verdín, asfalto con grano. |
| 54_piloto_s4150 | **ok / mejora** | 2 lomas HORIZ_ sobre el mar (~53 % del ancho de la línea mar/cielo visible, estimado sobre el par: islas x 130-290 y 365-490 de 540 px) pero BLANCAS (ver §4). Roca del lazo igual (F2). Sombra dura del sol nuevo (42°, -119°) cruza la pista: correcta. |
| 55_postal_tunel_salida | **mejora / regresión parcial** | paleta ok; talud derecho pasa de pared marrón con grano a plano crema liso (pared_lisa 69 -> 78 %); cordillera al fondo = picos blancos agudos (§4). |
| 56_postal_cima_bahia | **regresión** | la loma que tapa la bahía sigue tapándola (bahía 0 % del cuadro; objetivo bloque 1.5 >= 25 %) y ahora es una pirámide facetada (#E2DEB5, aristas visibles también en modo normal, no es cosa del AC). pared_lisa 38 -> 97 %, roca 0.9 -> 51 %. Postal, no vista de piloto 49-54: no bloquea por la regla 4, bloquea por KPI de terreno (§5). |
| 57_postal_viaducto | **mejora** | 2 islas HORIZ_ a la izquierda (~55 % de la línea de mar visible); cordillera derecha = icebergs (§4). |
| 58_postal_loews | **mejora** | césped solo en la isleta Loews (correcto), vegetación oliva, roca del peñón crema. bandas_blancas 0 -> 1 (un píxel-grupo claro en la isla del fondo: es el horizonte blanco). |
| 59 / 59b postal recta puerto | **mejora** | ladera dorada tras boxes, arcén hierba seca; verde 6.5 -> 5.1 % (banderas/tribunas). |
| 60_puerto_llanta_cenital | ok | sin cambio relevante. |
| 61_orilla_piloto_s150 | ok | césped 0.74 -> 0; bandas 0 -> 1 (horizonte blanco). |
| 62_tribuna_piloto_s5100 | ok | arcén hierba seca. |
| 63_horizonte_piloto_s2200 | **mejora** | 3 islas sobre el mar, ~12 % del ancho (medido por columnas); árboles oliva. |
| 01_aerea_general | **mejora** | isla dorada con roca en el macizo; verde 20.4 -> 0.3 %; parches de roca con borde poligonal. |
| 07_tierra_subida | **mejora / regresión** | color ok, pero la roca por cara en AC (`MAT_terreno_roca`, nz < 0.5) sale como polígonos grises de borde en sierra sobre loma lisa (roca 2.2 -> 23.9 %, pared_lisa 40 -> 82 %). |
| 13_puente_alto | **regresión** | cordillera blanca-hielo encima del McLaren (§4). |
| 21_montana_dentro_del_lazo | **mejora + regresión** | bosque y pueblo mejor; macizo dorado con roca; fondo = icebergs (#F0FFFF, #FFFFFF) ocupando toda la franja alta. |
| 36_roca_casino_general | **mejora** | casino crema #EEE4CF, cúpulas verdín; ladera partida en dos tonos (dorado / tierra) con frontera dura en la cresta. |

Regresiones en vistas de PILOTO (49-54): **0**. Postales/aéreas con regresión: 56 (forma), 13/21/55/57 (horizonte blanco), 07 (parches).
Modo normal: 21/21 regresión por magenta (§1), no computa como juicio artístico.

## 4. Hallazgo REAL n.º 3: el horizonte se lee como icebergs, no como costa de la Riviera

Las 9 cordilleras + 8 lomas (`HORIZ_`, 21 objetos, 182 890 tris: dentro de los 250 k) salen casi blancas en AMBOS modos:
`despues_ac/21` (1000,120) = #F0FFFF (S 0.06, V 1.00), (1150,100) = #FFFFFF; `despues/21` (1000,120) = #EBFFFF. El cielo
junto al horizonte es #BAE0FE: las montañas son MÁS claras que el cielo, y con `n_picos` 5-7 a `res 0.5` el perfil es
de agujas; en 13/21/55/57 parecen hielo o nieve. El plan (7.1) pide verde-azulada a 3.2 km y gris-azul a 4.5 km fundidas
al 35-55 % con el cielo (0.70, 0.84, 0.98): la perspectiva atmosférica tiene que dejar la silueta ALGO más oscura y más
violácea que el cielo, nunca más clara. Propietario **horizonte** (`montanas_fondo_v2.build_cordillera/build_loma`, tonos
base) y **materiales** (`mejorar_materiales.py` HORIZONTE: comprobar que la mezcla se hace en lineal con la base de
`paleta.json` y que `diffuse_color` resultante tiene V <= 0.85 y S >= 0.15); prueba: en `21` y `57` AC, V de la cordillera
< V del cielo en la misma columna, 0 píxeles #FFFFFF en HORIZ_. Cosmético añadido: picos menos agudos (lomas redondeadas,
Pixar), al menos en la fila de 2.4-2.8 km.

Cobertura KPI (>= 60 % del ancho de la línea mar/cielo en 49/52/54/56): 49 y 52 no tienen mar en el cuadro (0 %, N/A: KPI
mal planteado para esas dos; proponer 54/56/57/63); 54 ~53 %; 56 ~35 % (solo el hueco a la derecha del macizo); 57 ~55 %;
63 12 %. **No alcanzado** en ninguna.

## 5. KPIs con cifras

| KPI | Objetivo | Medido | Estado |
|---|---|---|---|
| `pct_cesped` piloto, modo AC | < 8 % | 0.012 % (15 tomas; base 0.395 %) | ok (poco informativo: ya era bajo en AC) |
| `pct_cesped` piloto, modo normal | < 8 % | 6.76 -> 0.001 % | inválido (terreno magenta cuenta como no verde) |
| `pct_verde` piloto AC (amplio) | - | 6.10 -> 1.34 % | mejora |
| `bandas_blancas` 07 | 0 | 0 (AC y normal) | ok; 08 no está en BASE ni en `paleta` -> sin medir |
| verde en caras nz < 0.7 (máscara) | 0 % | roca 88.4 %, R+G 5.9 % (`terreno_mask_stats.json`) | no cumple (5.9 %) |
| 51 desmonte >= 3 tonos | sí | hierba seca #F4EDBC / roca #DDD2C0 / tierra | cumple de forma, ΔV 0.09 = poco contraste |
| celdas > 35° con roca | >= 80 % | 73.3 % (antes 21.2 %; `preparar_geometria.log` l.74) | no cumple (B1 de terreno no aplicado) |
| pared Y caída a 25 m (tierra) | >= 40 % | 25.5 % (antes 4.5 %); a 50 m 27.7 % (obj 60) | no cumple |
| pared_roca en tierra | >= 50 % | 45.1 % (antes 22.7 %) | casi |
| terreno a 120 m tras pueblo_subida_ladera | >= 110 m | 78.1 m (antes 83.0: EMPEORA) | no cumple |
| orilla z > 10 m tramos | >= 25 % | 5.6 % (sin cambio) | no cumple (1c no hecho) |
| corredor < 4.5 m, Loews, McLaren < 25 m | 0.000 | 0.100 / 0.000 / 0.68 (lt_25m) | corredor 0.10 m y McLaren 0.68 m > 0: revisar (umbral del plan 0.000) |
| horizonte >= 60 % ancho 49/52/54/56 | >= 60 % | 0 / 0 / ~53 / ~35 % | no cumple |
| vegetacion_plan árboles | 6-9 k | 7 676 (+17 797 matas, 329 masas; vecino < 6 m 83.7 %; z > 80 m 53.9 %; VERIFICACIÓN 0/0/0) | ok (plan; se integra en F3) |
| máscara | suma = 1 | 100.00 %; matorral 49.1 / seca 21.2 / tierra 5.2 / roca 24.6 %; AO 0.757 | ok |
| `riqueza` terreno AC piloto | x2 | 0.94 -> 1.38 (x1.5); pero 51 1.07 -> 0.50, 56 1.23 -> 0.47, 07 1.67 -> 1.04 | mixto: el terreno sale PLANO en AC |
| `puerta.json` | ok: true | **false** (5 motivos) | no |
| tris KN5 | <= 6.0 M | sin informe de la candidata (último `informe_check_opt` 4.63 M + HORIZ_ 0.18 M = ~4.8 M estimado) | sin medir |
| RGB fuera de `paleta.json` | 0 | no medido en esta ronda (grep pendiente del integrador) | sin medir |
| calibración antes = antes (AC) | diff 0 | no repetida en f1_r1 (ratificada el 04/10 sobre la base) | - |

Nota sobre "terreno plano en AC": en modo AC el terreno es UN color (hierba seca tintada) + `MAT_terreno_roca` por cara:
las capas matorral/tierra de la máscara no se ven porque el writer de hoy solo exporta un tile (P10 interino de
`PETICIONES_04_EXPORT.md`: "hay que aplicarla ANTES de exportar la candidata de F1"). Es un límite declarado del modo AC,
no un fallo de la máscara, pero significa que el "cerrado en modo AC" del bloque 3 no puede certificarse hasta P10/P1 (04_export).
Mientras, el 51 en AC es crema sobre crema.

## 6. Problemas (gravedad / propietario / prueba)

1. **REAL — mascara** (red de seguridad: integrador). Rutas de imagen relativas en la candidata -> magenta fuera de `03_blender/`.
   Prueba: `despues/51` rgb(255,129,255); cadenas `//texturas\terreno_mask.png` en `escena_candidata.blend` (zstd). Arreglo §1.
2. **REAL — terreno**. `puerta.json ok: false`: asentar enterrados 57 -> 72, flotaban 28 -> 31, árboles quitados 3 -> 4,
   dentro_de_muro 0 -> 1; revisar_urbanismo 25 > 23 (prop_camino +1, objeto_salto_grande +2). Arreglo §2.
3. **REAL — terreno**. KPIs de relieve: pared Y caída 25 m 25.5 % (obj 40), 50 m 27.7 % (obj 60), 120 m tras pueblo 78.1 m
   (obj 110, y baja desde 83.0), orilla 5.6 % (obj 25); postal 56: bahía 0 % del cuadro y loma facetada (`despues_ac/56`).
   El bloque 1 está a medias (1a sí, 1b/1c/1.5 no): o se termina en r2 o el coordinador acota F1 a 1a+capas y pasa 1b/1c a F2.
4. **REAL — horizonte** (+ materiales en la mezcla). Cordilleras/lomas blancas #F0FFFF-#FFFFFF más claras que el cielo
   #BAE0FE y picos de aguja: se leen como icebergs en 13/21/55/57/54. Arreglo §4.
5. **REAL — integrador**. Falta el "después" del A/B en `renders/ab/f1_r1/` (BASE 21 tomas + set paleta 8, modo normal y AC),
   `AB_*`, hojas y `medidas*.json`; sin hoja no hay promoción (criterio 5). Repetir §0 dentro del proyecto DESPUÉS del arreglo 1
   (si no, la hoja normal saldrá magenta otra vez).
6. **MENOR — mascara**. Caras nz < 0.7 con R+G 5.9 % (obj 0 %); celdas > 35° con roca 73.3 % (obj 80 %): aplicar B1 de
   `PARCHES_F1_terreno.md` (PEND_ROCA 0.68-0.80, pie 8 m) en r2 (decisión del director: sí, se aplica; es afinado de
   `mascara_terreno.UMBRALES`, no de F2). Prueba: `terreno_mask_stats.json` nz<0.7 verde <= 1 %, `preparar_geometria.log` roca>35 >= 80 %.
7. **MENOR — materiales**. Contraste hierba seca / roca en AC: #F4EDBC vs #DDD2C0 (ΔV 0.09, ΔH 15°): el desmonte de 51 no se
   lee a 3 tonos. `caliza_ocre` #D8CCB0 es decisión del usuario; bajar en cambio la luminancia de `hierba_seca` del tile
   tintado o subir el `caliza_gris_calido` #B3A68A en la cara de roca (la pared vertical debería ir al tono medio, no al claro).
8. **MENOR — materiales [W, 04_export P1]**. Roca por cara en AC = polígonos de 4 m con borde en sierra (07, 01, 21, 36):
   `MAT_terreno_roca` debe leer el canal A de la máscara con borde de ruido (P1 nota de mascara), no `nz < 0.5` por cara.
9. **MENOR — terreno**. `dz_corredor_4p5m_max` 0.100 m y McLaren lt_25m 0.68 m (objetivo 0.000 en ambos, `medir_relieve.json`).
10. **MENOR — integrador**. Set `paleta` sin "después"; 08_tierra_cima (KPI bandas_blancas) no está en ningún set rendido:
    añadirlo a `--set paleta` o medir 07 solo. KPI horizonte en 49/52 no tiene línea de mar: proponer al coordinador 54/56/57/63.
11. **COSMÉTICO — horizonte**. Picos de aguja en las cordilleras (res 0.5, n_picos 5-7): redondear (Pixar) al menos en lomas.
12. **COSMÉTICO — terreno/mascara**. En 36 la ladera del peñón queda partida en 2 tonos con frontera dura en la cresta (dorado /
    tierra): meter ruido de 10-30 m también en el canal B junto a `_corte`.

## 7. Lo que SÍ está bien (no tocar en r2)

Paleta v2 en fachadas (azafrán/ocre naranja/siena/pompeyano/melocotón/crema, 50 y 53), tejas #BF6440, cúpulas verdín, casino
crema; copas oliva/pino oscuro; césped solo en la isleta Loews; arcén y taludes en hierba seca; sol 42° con sombra larga de
la roca del lazo (54); asfalto con grano; máscara 2048 coherente (suma 100 %, roca 88 % en nz < 0.7); plan de vegetación
7 676 árboles con 0 invasiones; horizonte en su sitio y con el tris dentro del presupuesto (solo el color y el perfil fallan);
tierra tallada de 51 (silueta derecha más alta, pared_roca 22.7 -> 45.1 %).

## 8. Orden de r2

1 (rutas, 2 líneas) -> 5 (A/B en el proyecto, modo normal y AC, BASE + paleta) -> 4 (color horizonte) -> 2+3 (terreno: puerta y
KPIs, o acotar F1 por decisión del coordinador) -> 6 (B1) -> 7/8 (contraste roca, P1 para 04_export). Sin 1 ninguna hoja en
modo normal vale; sin 2 no hay promoción aunque todo lo demás esté bien.

Ficheros de prueba de este informe (efímeros, scratchpad): `f1_r1/AB_ac_*.png`, `f1_r1/AB_*.png`, `f1_r1/medidas_ac.json`,
`f1_r1/medidas.json`, `f1_r1/despues_ac.log`, `f1_r1/despues.log`. Ficheros del proyecto citados: `_rev/puerta.json`,
`_rev/logs_f1_r1/{preparar_geometria,medir_relieve,mascara_terreno,vegetacion,construir_pista,integrar_escena,revisar_urbanismo,asentar_objetos}.log`,
`renders/qa/terreno_mask_stats.json`, `renders/qa/medir_relieve.json`, `renders/ab/_base_antes/medidas.json`.
