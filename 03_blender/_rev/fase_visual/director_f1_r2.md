# Director de arte — F1 (fase visual), ronda 2 — 04/10/2026 ~22:05

**Veredicto: NO APROBADO** (`aprobado = false`). Motivo único de bloqueo: `_rev/puerta.json` `ok: false` (4 motivos, todos del
relieve: asentar/urbanismo peor que la base) y el KPI de F1 del bloque 1 (pared Y caída a 25 m) sigue en 25.5 % (objetivo 40 %):
el propietario `terreno` no ejecutó su ronda 2 (geometría idéntica a r1: dz 20.81 m, 25.5 / 27.7 / 83.0). Todo lo demás de r1 que
era REAL está arreglado: rutas 0 relativas, A/B completo en el proyecto (BASE 21 + paleta 9, normal y AC), horizonte ya no es
iceberg, B1 aplicado (roca > 35° 81.6 %, verde en nz < 0.7 = 0.1 %).

Regresiones en vistas de piloto (49-54) en MODO AC: **0**. En modo normal: 0 (51 con reserva). Postal 56: regresión (forma), igual que r1.

Candidata juzgada: `_rev/escena_candidata.blend` md5 `39e8a969d8c5b11aa5a08ca074b814f9` (21:37); logs `_rev/logs_f1_r2/`;
`_rev/logs_f1_r2_pipeline.out` (rc 0, 21:33 -> 21:37, ERRORES: ninguno); `_rev/puerta.json` 21:37; hojas y medidas en
`renders/ab/f1_r2/` (21:38-21:40). Base: `_rev/escena_antes_visual.blend` md5 a6fb4195… = `renders/ab/_base_antes/`.

## 0. Qué he mirado

- 6 hojas: `hoja_f1_r2_piloto.png`, `hoja_f1_r2_piloto_ac.png`, `hoja_f1_r2_aereas.png`, `hoja_f1_r2_aereas_ac.png`,
  `hoja_f1_r2_aereas_paleta.png`, `hoja_f1_r2_aereas_ac_paleta.png`.
- 30 pares `AB_*`/`AB_ac_*` de 49-54, 55-59 y 01/07/21/36 (ambos modos) + `medidas.json`, `medidas_ac.json`, `medidas_paleta.json`,
  `medidas_paleta_ac.json`.
- Muestras de píxel y medias por región sobre `despues_ac/*.png` y `despues/*.png` (PIL/numpy, sin Blender), cobertura de horizonte
  por columnas (línea mar/cielo con silueta `HORIZ_` en una banda de 60 px).
- Logs: `preparar_geometria`, `medir_relieve`, `mascara_terreno`, `vegetacion`, `construir_pista`, `integrar_escena`, `asentar_objetos`,
  `revisar_urbanismo`, `mejorar_materiales`, `aplicar_texturas`, `comprobar_rutas`; `renders/qa/terreno_mask_stats.json`,
  `renders/qa/medir_relieve.json`.
- Blender: 0 vistas extra (no hacía falta).

## 1. Bloqueo n.º 1: `puerta.json ok: false` (propietario terreno; red: integrador)

4 motivos (regla "no peor que la base", base 15:12):
- `revisar_urbanismo` 29 fallos > base 23 (r1: 25). Por tipo, nuevos o peores: `objeto_salto_grande` 8 -> 9, `prop_camino` 1 -> 2,
  `bancal_mal_asentado` 1 -> 2, `sendero_enterrado` 1 -> 2, y 2 TIPOS NUEVOS: `camino_sin_destino` 1, `ermita_desnivel` 1.
  Los prohibidos (`casa_pista`/`casa_muro`/`losa*`) siguen 0/1/2 = base.
- `asentar`: `arboles_quitados` 3 -> 5, `enterrados_mas_0_6` 57 -> 66 (r1: 72), `bancales_mal` 1 -> 2. Mejora: `flotaban_mas_0_6` 28 -> 25.
- Avisos (no bloquean): costuras máx 2.03 m = base (pueblo_alto_mar 2.03 / casino_mar 2.01 / pueblo_subida_ladera 1.49 con 74 celdas > 0.6).
- Igual o mejor: 193 casas, 0 fallos de plan, nada_en_pista 11 (tierra 0), invaden 0, hierba_asfalto 0, fosos 0, Loews 0.000, integrar ninguno.

Decisión del director sobre el parche r2.3-B (re-basar `linea_base.json`): **NO se re-basa a ciegas**. El integrador comprobó que en
celdas con dz = 0 los enterrados pasan de 54 a 60: eso no lo explica el relieve, así que hay 6 objetos que hay que mirar uno a uno
(`_rev/asentar_candidata.json`, `renders/qa/urbanismo_informe.json`: los 2 `prop_camino`, el `camino_sin_destino`, la `ermita_desnivel`,
el bancal nuevo). Camino aceptable: (a) terreno reduce el dz en el entorno de esos props/caminos (están todos a < 120 m del borde, s
800-2400 según `medir_relieve.log` "por 200 m de s") o el coordinador los re-asienta; (b) SOLO después, re-base justificada de los
contadores que dependan del dz (enterrados/flotaban), nunca de `revisar_urbanismo` ni de `arboles_quitados`.

## 2. Bloqueo n.º 2: KPI de F1 del bloque 1 sin alcanzar (propietario terreno)

`medir_relieve.log` (21:33) ANTES -> DESPUÉS, idéntico a r1 (la geometría no cambió en r2):
- pared Y caída a 25 m (s 1430-2440): 4.5 -> **25.5 %** (obj >= 40); a 50 m 22.1 -> 27.7 % (obj 60); a 20 m 27.3 %, a 15 m 11.3 %.
- pared_roca en tierra 22.7 -> 45.8 % (obj 50): casi. Pared en algún lado 45.8 %, caída en algún lado 51.8 %: el problema es la
  coincidencia por tramo (por 100 m: 1430/1830/2030/2230/2430 = 0 %; 2130 = 80 %, 1930 = 50 %).
- 120 m tras pueblo_subida_ladera 83.0 -> 83.0 m (obj 110): bloque 1.3 (macizo), NO es de F1: informativo.
- orilla z > 10 m 5.6 % (obj 25): bloque 1.4, NO es de F1: informativo.
- postal 56: mar 1.2 % del cuadro (obj >= 25); horizonte de terreno en la fila 25 de 108. La loma sigue tapando la bahía y es una
  pirámide de dos picos con aristas rectas (ver `AB_ac_56`, `AB_56`): media de la pirámide AC #D0D5B4 (V 0.84), roca por cara a la
  derecha #C0BEA4. Regresión de forma respecto a la base (loma redonda), igual que en r1.
- corredor < 4.5 m del asfalto dz 0.100 m (obj 0.000); McLaren lt_25m 0.12 m (r1 0.68; obj 0.000); Loews 0.000 ok.

Si el coordinador acota F1 a "1a + capas" (como propuse en r1), que lo escriba: entonces el KPI de 25 m pasa a F2 y este bloqueo
desaparece; sin esa decisión escrita, no cumple.

## 3. Tomas del set BASE: ok / mejora / regresión (criterio = MODO AC; el modo normal se anota)

Cifras: `medidas_ac.json` antes -> después (modo AC) salvo que se indique "normal".

| Toma | AC | Nota |
|---|---|---|
| 49_piloto_s300 | **mejora** | pared_lisa 87.0 -> 32.1 % (obj < 30, casi), roca 65.6 -> 57.8 %; talud derecho con tile de caliza (#C8C4BA, V 0.79), arcén hierba seca. Reserva: la carrocería del McLaren en AC es gris AZULADO #919E9E (H 184) con repetición visible del tile de 3 m; el usuario pidió rocas cálidas. Normal: mejora (estratos en el McLaren, talud caliza; césped 6.84 -> 0.00 %). |
| 50_piloto_s800 | **mejora** | la mejor toma: fachadas azafrán/siena/pompeyano, copas oliva, laderas doradas con muros; verde 11.0 -> 2.8 %; siluetas 20-120 m 1 -> 6; riqueza 1.21 -> 2.09. Normal: mejora; reserva: la loma alta a la izquierda sale gris-verdosa con retícula (#9EA094, sdV 0.166). |
| 51_piloto_s1700 | **mejora (con reserva)** | silueta derecha claramente sobre el horizonte; roca por cara gris en la ladera izquierda (#8F908E V 0.56) con borde en sierra de 4 m; pared derecha caliza #DBD0BF (V 0.86) / berma hierba seca #ECE5BD (V 0.93) / tierra #DCCCB2 (V 0.87): ΔV pared-tierra 0.01, pared-berma 0.07 = crema sobre crema (ver §4 KPI "3 tonos"). Riqueza 1.07 -> 1.95. Siluetas 1 -> 1. Normal: pared derecha casi blanca #E7E1CD (V 0.91) con retícula diagonal: "pared de hielo", reserva (no regresión: antes era verde + crema). |
| 52_piloto_s2900 | **mejora** | loma dorada, pinos parasol y cipreses oliva; verde 10.3 -> 1.3 %; siluetas 6 -> 7; riqueza 1.04 -> 1.99. Sin línea de mar en el cuadro (KPI horizonte N/A). |
| 53_piloto_s3400 | **mejora** | fachada ocre naranja, cúpulas verdín, asfalto con grano (riqueza 0.75 -> 2.09). |
| 54_piloto_s4150 | **mejora** | roca del lazo con caliza (pared_lisa 78.3 -> 40.8 %, obj < 30 es del bloque 2/F2); 2 islas HORIZ_ #A9B9E1 (V 0.88) MÁS OSCURAS que el cielo #D0EAFF (V 1.00): arreglado el iceberg. Cobertura de la línea mar/cielo 32.4 % (280 de 865 columnas). Sombra larga correcta. Normal: mejora (estratos horizontales en la pared). |
| 55_postal_tunel_salida | **mejora** | talud derecho con tile de caliza (pared_lisa 69.2 -> 58.0 %, aún alto), ladera izquierda hierba seca; cordillera del fondo ya con color (#ABAAA6-#B8B6B0, V 0.67-0.72) pero de PICOS DE AGUJA (cosmético). Normal: mejora. |
| 56_postal_cima_bahia | **regresión (forma)** | la loma pirámide facetada tapa la bahía (mar 1.2 % del cuadro); color ok (hierba seca + roca por cara). Postal, no piloto: no bloquea por la regla 4, bloquea por el KPI del bloque 1 (§2). Normal: misma pirámide con retícula (#B5B5A6). |
| 57_postal_viaducto | **mejora** | 2 islas HORIZ_ a la izquierda (#98A8CE, V 0.81 < cielo 1.00), roca del lazo con caliza (pared_lisa 83.2 -> 40.2 %); cobertura horizonte 12.0 %; cordillera derecha = agujas. Normal: mejora. |
| 58_postal_loews | **mejora** | estratos en el acantilado, césped solo en la isleta (césped 1.14 -> 0.17 %), isla al fondo; bandas_blancas 0 -> 1 (un grupo claro en la isla: es la cima más clara del `HORIZ_`, no sierra). Normal: mejora. |
| 59 / 59b postal recta puerto | **mejora** | ladera dorada tras boxes, arcén hierba seca; verde 6.5 -> 5.1 % (banderas/tribunas); pared_lisa 89.5 -> 47.3 %. |
| 60_puerto_llanta_cenital | ok | sin cambio relevante. |
| 61_orilla_piloto_s150 | **mejora** | césped 0.74 -> 0; horizonte con silueta en el 79.7 % de la línea mar/cielo (1000 de 1255 columnas). bandas 0 -> 1 (cresta clara del HORIZ_). |
| 62_tribuna_piloto_s5100 | ok / mejora | arcén hierba seca; ladera tras la tribuna dorada. |
| 63_horizonte_piloto_s2200 | **mejora** | 3 islas (6.5 % del ancho), árboles oliva, pacas sobre hierba seca. |
| 01_aerea_general | **mejora** | verde 20.4 -> 0.26 %; isla dorada con roca en el macizo; parches de roca con borde poligonal (W P1). Normal: mejora (máscara 4 capas visible). |
| 07_tierra_subida | **mejora / regresión parcial** | AC: lomas doradas, roca por cara gris con borde en sierra (roca 2.2 -> 20.7 %, pared_lisa 39.5 -> 31.0 %) y un PARCHE CUADRADO gris de bordes rectos en (1176,630) #7F8484 (V 0.52) de ~100 px (ver §5 n.º 8). Normal: montículos de roca blanca con retícula (#949C95-#A2B1AE, sdV 0.11-0.19): "montones de hielo" (§5 n.º 5). bandas_blancas 0 en ambos modos. |
| 13_puente_alto | **mejora** | horizonte violeta #697FAD (V 0.68) ya más oscuro que el cielo; roca del lazo y monte-coche con caliza. Agujas al fondo. Normal: roca del lazo gris AZULADA #859FAA (H 196) con retícula (§5 n.º 5). |
| 21_montana_dentro_del_lazo | **mejora** | bosque, pueblo, macizo dorado; horizonte 67.5 % de la línea con color correcto (#9AA9CD / #5D749F). Normal: mejora, con retícula en las lomas de roca. |
| 36_roca_casino_general | **mejora** | casino crema, cúpulas verdín; ladera partida en dos tonos con frontera dura (cosmético, r1 n.º 12). Normal: la ladera bajo el peñón sale CIAN claro #9CCAD7 (H 192, S 0.27) con retícula de celdas de 10-15 m: "red de pesca" (§5 n.º 5). |

Set `paleta` (05/06/08/09/14/16/21/22/39), modo AC: césped 0.00 % en las 9 (antes 0.03-2.40), verde 42.8 -> 2.0 % (05), 52.9 -> 0.2 % (08),
35.5 -> 1.9 % (39); bandas_blancas 0/9 (08 = 0 en AC y normal). Modo normal: césped 40.9 -> 0.0 (05), 48.0 -> 0.0 (08), 30.9 -> 0.0 (39);
bandas 09 1, 39 1 (resto 0); 08 pared_lisa 75.6 -> 0.1 %.

## 4. KPIs con cifras

| KPI | Objetivo | Medido | Estado |
|---|---|---|---|
| `pct_cesped` piloto 49-54, modo AC | < 8 % | 0.00 % en las 6 (antes media 0.41 %) | ok |
| `pct_cesped` piloto, modo normal | < 8 % | media 8.0 -> 0.00 % (51: 18.2 -> 0.0) | ok (esta ronda sí vale: 0 magenta) |
| `pct_verde` piloto AC (amplio) | - | 5.46 -> 0.84 % | mejora |
| `riqueza` terreno piloto AC | x2 | 0.874 -> 1.950 (x2.23); 51 1.07 -> 1.95, 54 0.30 -> 1.63 | ok |
| `varianza_local` piloto AC | - | 0.017 -> 0.036 (x2.1) | ok |
| `bandas_blancas` 07 / 08 | 0 | 07: 0 (AC y normal); 08: 0 (AC y normal) | ok |
| verde en caras nz < 0.7 (máscara) | 0 % | roca 99.7 %, verde 0.1 % (`terreno_mask_stats.json`, PEND_ROCA 0.68-0.80) | ok (r1 5.9 %) |
| 51 desmonte >= 3 tonos (AC) | sí | gris por cara #8F908E (V 0.56) / caliza #DBD0BF (0.86) / hierba seca #ECE5BD (0.93) / tierra #DCCCB2 (0.87) | de forma sí; la PARED del desmonte vs la tierra ΔV 0.01: no se lee |
| celdas > 35° con roca | >= 80 % | 81.6 % (antes 21.2; > 40°: 86.0 %) | ok |
| pared Y caída a 25 m (tierra) | >= 40 % | 25.5 % (50 m 27.7 %) | NO (sin cambio desde r1) |
| pared_roca en tierra | >= 50 % | 45.8 % | casi |
| horizonte >= 60 % del ancho mar/cielo en 49/52/54/56 (AC) | >= 60 % | 49: 9 columnas de mar (N/A); 52: 0 (N/A); 54: 32.4 %; 56: 0.4 % | NO. Informativo: 61 79.7 %, 21 67.5 %, 13 56.2 %, 57 12.0 %, 63 6.5 % |
| horizonte: V < cielo, 0 px #FFFFFF | sí | 54 #A9B9E1 vs #D0EAFF; 21 #9AA9CD/#5D749F vs #D8EFFF; 13 #697FAD; log HORIZONTE V max 0.63, S min 0.15 | ok (r1 n.º 4 arreglado) |
| vegetacion_plan árboles | 6-9 k | 7 654 (+15 145 matas, 291 masas; vecino < 6 m 85.1 %; z > 80 m 58.3 %; verificación 0/0/0) | ok (se integra en F3) |
| máscara suma = 1 | 100 % | 100.00 %; matorral 45.9 / seca 21.6 / tierra 4.8 / roca 27.8 %; AO 0.758 | ok |
| rutas de imagen relativas en la candidata | 0 | 0 relativas / 15 absolutas (`comprobar_rutas.log`); construir_pista "7 absolutas, 0 relativas" | ok (r1 n.º 1 arreglado) |
| `puerta.json` | ok: true | **false** (4 motivos) | NO |
| tris KN5 | <= 6.0 M | sin informe de la candidata (`kn5_presupuesto.py` no se ejecutó; HORIZ_ 182 890 tris dentro de los 250 k) | sin medir |
| RGB fuera de `paleta.json` | 0 | no medido (grep pendiente desde r1) | sin medir |
| pared_lisa 49 / 54 (bloque 2, informativo) | < 30 % | 32.1 % / 40.8 % (antes 87.0 / 78.3) | casi / no (F2) |
| siluetas 20-120 m 50/51/52 (bloque 4, informativo) | x3 | 1 -> 6 / 1 -> 1 / 6 -> 7 | parcial (F3) |
| pipeline | rc 0, 1 intento | rc 0, 4 min, ERRORES: ninguno, 193 casas, 644 mallas con bisel | ok |

## 5. Problemas (gravedad / propietario / prueba)

1. **REAL — terreno** (red: integrador). `puerta.json ok: false`: revisar_urbanismo 29 > 23 (tipos nuevos `camino_sin_destino` 1,
   `ermita_desnivel` 1; `objeto_salto_grande` 9, `prop_camino` 2, `bancal_mal_asentado` 2, `sendero_enterrado` 2); asentar
   `arboles_quitados` 5 > 3, `enterrados_mas_0_6` 66 > 57, `bancales_mal` 2 > 1. Sin `ok: true` no hay promoción (plan §0.1). Arreglo §1.
2. **REAL — terreno**. KPI de F1 pared Y caída a 25 m 25.5 % (obj 40), idéntico a r1: la ronda 2 de terreno no se ejecutó. Postal 56:
   mar 1.2 % del cuadro, loma pirámide facetada (`AB_ac_56`, `AB_56`). Corredor dz 0.100 m y McLaren lt_25m 0.12 m (obj 0.000). O se
   termina 1a (coincidencia pared/caída en los tramos 1430/1830/2030/2230/2430 que dan 0 %) o el coordinador acota F1 por escrito.
3. **MENOR — materiales**. Contraste del desmonte en 51 (AC): pared caliza #DBD0BF vs tierra #DCCCB2 (ΔV 0.01) y vs hierba seca
   #ECE5BD (ΔV 0.07): crema sobre crema, igual que r1 n.º 7. El parche 9.1 (`roca_caras_mascara` + `color_roca_terreno_ac` #B0A286 en
   el proxy AC) no se aplicó a propósito porque exige P1 en el writer. Decisión: la pared del desmonte debe ir al tono medio
   `caliza_gris_calido` #B3A68A (V 0.70) y no al claro; en el tile tintado del proxy AC también (es el mismo albedo que verá el amigo).
4. **MENOR — materiales [W, 04_export P1]**. Roca por cara en AC = polígonos de 4 m con borde en sierra (07, 51 izquierda, 01, 21, 36);
   `MAT_terreno_roca` debe leer el canal A de la máscara (P1 nota de máscara, código listo en `materiales_roca.roca_caras_mascara`).
   Sin cambio desde r1 n.º 8; no bloquea F1 porque es del writer.
5. **MENOR — materiales** (modo normal; no bloquea porque el criterio es AC, pero lo verá el usuario en las capturas y lo heredará
   el horneado 2.8). `NG_caliza_estratos` sobre el TERRENO/roca del lazo/monte-coche se lee como RETÍCULA (celdas de 10-15 m, "red de
   pesca"/"colmena") y con tinte FRÍO: 36 ladera #9CCAD7 (H 192, S 0.27), 13 roca del lazo #859FAA (H 196), 13 monte-coche #909C9A,
   07 montículos #949C95-#A2B1AE (sdV 0.11-0.19), 51 pared #E7E1CD (V 0.91). El usuario pidió caliza cálida #D8CCB0/#B3A68A/#7F766A
   "sin gris azulado". Prueba: media de la pared de 51 normal con H 30-45 y V <= 0.86; en 36 normal ninguna celda regular visible a
   > 100 m (bajar la amplitud de la junta/grieta con la distancia o quitar la componente vertical del patrón); comprobar rugosidad
   (reflejo del cielo = cian) de `ng_caliza_estratos`.
6. **MENOR — materiales**. McLaren en AC: carrocería gris azulada #919E9E (H 184, V 0.62) con el tile de 3 m repetido de forma visible
   en 49 (`AB_ac_49`, 0-600 x 50-250). `MAT_MCOCHE_*` deben ir a la paleta cálida (hueso 0.58) y el tile a BOX >= 6 m o con manchas.
7. **MENOR — horizonte (+ coordinador)**. Cobertura: 54 32.4 %, 56 0.4 % (obj 60); 49/52 no tienen mar. 54 mira al S/SO = abertura de
   160° decidida en 7.1 (mar abierto a propósito): el KPI tal como está escrito es incumplible en 54 y 56 (56 la tapa la loma de §2).
   Propuesta: medir el 60 % en 61 (79.7 %), 21 (67.5 %), 13 (56.2 %) y 57 (12.0 %): 57 y 63 (6.5 %) sí son mejorables añadiendo
   1-2 lomas a 2.4-2.8 km en la ventana de 57 (brújula de la cámara 520,-614 -> 422,-608).
8. **MENOR — mascara/terreno**. 07 AC: parche CUADRADO gris #7F8484 (V 0.52, S 0.04) de bordes rectos en (1176,630) de
   `despues_ac/07_tierra_subida.png` (~100 px); en modo normal en ese sitio hay un montículo de roca con estratos. Identificar qué es
   (¿explanada/peana de `CAMARA_tierra`, ¿roca de cima `VEG_roca`, ¿celdas con nz < 0.5 en bloque?) y darle borde de ruido o quitarlo.
9. **MENOR — integrador**. Sin informe de tris de la candidata (`_rev/kn5_presupuesto.py` no se lanzó) y sin grep de RGB fuera de
   `paleta.json` (pendiente desde r1). Son 2 comandos; los pide la tabla 16.
10. **COSMÉTICO — horizonte**. Picos de aguja en las cordilleras (55, 57, 13, 21: `res 0.5`, `n_picos` 5-7): redondear (Pixar), al menos
    la fila de 2.4-2.8 km. El color ya está bien: no tocar la mezcla.
11. **COSMÉTICO — terreno/mascara**. 36: ladera del peñón partida en dos tonos con frontera dura en la cresta (r1 n.º 12): ruido de
    10-30 m también en el canal B junto a `_corte`.
12. **COSMÉTICO — terreno**. Costuras máx 2.03 m (= base; objetivo < 0.6 del bloque 1): pueblo_alto_mar / casino_mar.

## 6. Lo que SÍ está bien (no tocar en r3)

Paleta v2 en fachadas (50, 53, 09), tejas #BF6440, cúpulas verdín, casino crema; copas oliva / pino oscuro; césped solo en la isleta
Loews y jardines (0.00 % en las 15 tomas de piloto/postal en AC); arcenes y taludes en hierba seca; asfalto con grano; sol 42° con
sombra larga (54); máscara 2048 coherente (B1: roca 99.7 % en nz < 0.7; > 35° 81.6 %); plan de vegetación 7 654 árboles con 0
invasiones; horizonte con el color correcto (V < cielo en 54/57/13/21, 0 px blancos) y dentro del presupuesto (182 890 tris);
roca del lazo y acantilado Loews con estratos de caliza (54, 57, 58: pared_lisa 78 -> 41, 83 -> 40); tile de caliza en el talud de
49 (87 -> 32 %); rutas absolutas + lector A7 en pipeline y promover; A/B completo (BASE 21 + paleta 9, normal y AC) en 4 min.

## 7. Orden de r3

1 (terreno: puerta, §1: mirar los 6 enterrados en celdas sin cambio y los 2 tipos nuevos de urbanismo) -> 2 (terreno: 1a hasta
>= 40 % a 25 m o acotación escrita del coordinador; despeje del cono de 56) -> 3+6 (materiales: tono medio en el desmonte y McLaren
cálido, 1 h) -> 5 (materiales: retícula/tinte frío del grupo de caliza en modo normal) -> 9 (integrador: presupuesto + grep) -> 7/10
(horizonte: KPI re-escrito + lomas en la ventana de 57, picos redondeados) -> 8 (parche de 07). Sin 1 no hay promoción aunque todo lo
demás esté bien; con 1 y 2 cerrados y 0 regresiones de piloto en AC, F1 se puede promover con 3-12 abiertos como MENOR/COSMÉTICO
documentados para F2/F3.

Ficheros citados: `_rev/puerta.json`, `_rev/logs_f1_r2_pipeline.out`, `_rev/logs_f1_r2/{preparar_geometria,medir_relieve,mascara_terreno,
vegetacion,construir_pista,integrar_escena,asentar_objetos,revisar_urbanismo,mejorar_materiales,aplicar_texturas,comprobar_rutas}.log`,
`renders/qa/terreno_mask_stats.json`, `renders/qa/medir_relieve.json`, `renders/ab/f1_r2/{medidas,medidas_ac,medidas_paleta,
medidas_paleta_ac}.json`, `renders/ab/f1_r2/AB_*.png`, `renders/ab/f1_r2/AB_ac_*.png`, `renders/ab/f1_r2/hoja_f1_r2_*.png`,
`_rev/fase_visual/PETICIONES_04_EXPORT.md` (P1, P10), `_rev/fase_visual/director_f1_r1.md`.
