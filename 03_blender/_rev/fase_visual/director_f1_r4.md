# Director de arte — F1 (fase visual), ronda 4 (última) — 05/10/2026 ~09:50

**Veredicto: NO APROBADO** (`aprobado = false`), por **un único motivo**: `_rev/puerta.json` `ok: false` porque
`asentar.arboles_quitados` es **4 > base 3**. La acotación 3 solo exime los fallos de `revisar_urbanismo` heredados, no este contador.
Todo lo demás que bloqueaba en r3 está cerrado:
- La postal 56 ya es una **cúpula sin dientes**: caras vistas a menos de 20 m de la cumbre con máximo 29.2 grados y 0 % por encima de 30.
- PyC a 25 m da **32.4 %** (umbral 30) y a 50 m **23.3 %** (umbral 20).
- `revisar_urbanismo` baja a **13**, todos heredados y documentados (tope 23).
- Tris **4 752 822** (tope 6.0 M).
- Horizonte: cumple la decisión 9.
- **0 regresiones de piloto** en modo AC y en modo normal.

Arreglo propuesto (§1): una regeneración más, que solo cambia la zona del casino porque el RNG va por zona, o una tolerancia +1 escrita por
el coordinador. Con `ok: true` y sin cambios en 49-54, F1 se puede promover sin otra ronda del director.

Candidata juzgada:
- `_rev/escena_candidata.blend`, md5 `1f5c2d6e0312a5ce63d6e2a07707e47e` (09:15).
- `_rev/logs_f1_r4_pipeline.out`: 09:05 -> 09:15, `ERRORES: ninguno`, termina en `PIPELINE rc=0`.
- Logs en `_rev/logs_f1_r4/`.
- A/B en `renders/ab/f1_r4/`: 30 tomas x 2 modos, 0 avisos.
- Base: `_rev/escena_antes_visual.blend` = `renders/ab/_base_antes/`.

## 0. Qué he mirado

- Las 6 hojas: `hoja_f1_r4_{piloto,piloto_ac,aereas,aereas_ac,aereas_paleta,aereas_ac_paleta}.png`. Las he troceado (5+5+2+2+3+3 trozos) y
  las he leído enteras.
- Los pares base|r4 de 49-54, 55-59 (+59b), 60-63 y 01/07/13/21/36/56, en los dos modos (son las filas de las hojas).
- Pares **r3|r4** hechos por mí (scratchpad, fuera del proyecto) de `despues{,_ac}/` 56, 50, 51, 54, 07, 13, 36, 21, 57.
- Recortes 1:1 de 08 normal (r3 y r4), 49 y 62 (McLaren, r3/r4 en los dos modos).
- `medidas{,_ac,_paleta,_paleta_ac,_r3_r4,_r3_r4_ac}.json/.log`, `horizonte_{ac,normal,director_ac}.log`.
- `_rev/logs_f1_r4/medir_relieve.log`, `asentar_objetos.log`, `presupuesto_paleta.log`.
- `_rev/puerta.json`, `_rev/presupuesto_candidata.json`, `_rev/asentar_candidata.json`, `_rev/PROMOCIONES.md` y
  `RONDA15_PLAN.md` (líneas 479-486).
- Única pasada de Blender, de solo lectura: `_rev/presupuesto_paleta_candidata.py` sobre la BASE `escena_antes_visual.blend`, con salida en
  el scratchpad. Sirve para saber qué materiales fuera de paleta son nuevos de F1 (§4).
- No he modificado ningún fichero del proyecto salvo este informe.

## 1. Bloqueo único: `puerta.json ok: false` (propietario: integrador; decisión: coordinador)

**Motivo.** `asentar.arboles_quitados` 4 > 3. Los 4 quitados (`asentar_candidata.json` -> `quitados`) son:
- `VEG_adelfa.004` (482, -556): "ladera imposible" 2.84 m.
- `VEG_palmera.011` (498, -592): 4.71 m.
- `VEG_adelfa.013` (473, -566): 3.45 m.
- `VEG_arbusto.130` (-256, 555): 1.64 m en 1.2 m de tronco.

Los tres primeros son jardines del casino en los cantiles del peñón. El terreno es idéntico a la base a menos de 10 m en los 4 (PROMOCIONES.md).
Es un sorteo nuevo de la semilla por zona, no un cambio de relieve de F1.

**El resto de la puerta está igual o mejor que la base:**

| Contador | Base -> r4 | r3 |
|---|---|---|
| `revisar_urbanismo` | 23 -> **13** | 27 |
| `objeto_salto_grande` | 8 -> 0 | — |
| `prop_camino` ITAL_fuente.005 | fuera | — |
| `camino_sin_destino` | 0 | — |
| Enterrados | 57 -> **47** | 60 |
| Flotaban | 28 -> **24** | 29 |
| Dudosos | 8 -> 0 | — |
| `bancales_mal` | 1 -> 0 | — |

Sin cambios respecto a la base:
- `nada_en_pista` 11 / 0 en tierra.
- Urbanismo: 193 casas, 0 fallos.
- Invaden 0, `hierba_asfalto` 0, fosos 0.
- Loews 0.000.
- Edificios flotantes 3 = base.
- Costuras 2.03 m / 127 celdas = base (aviso).

**Heredados.** Los 13 de `revisar_urbanismo` son el mismo objeto y el mismo tipo que en la base, y PROMOCIONES.md los lista uno a uno.
0 tipos nuevos; los prohibidos (`casa_muro` 1, `losa_hierba` 2) están igual que en la base. Cumple la acotación 3 en esa parte.

**Lo que pido.**
- (a) **Integrador:** UNA regeneración con el filtro de pendiente que ya está en `integrar_escena.zona_casino` (pendiente > 0.62 o anillo
  > 1.25). Con el RNG por zona solo cambia el sorteo de `zona_casino`. Después, la puerta y el A/B solo de 36/58/59/62 más 49-54 en AC para
  confirmar que no hay cambios de piloto. Si sale `ok: true`, se promueve con este informe.
- (b) **Alternativa del coordinador:** tolerancia escrita "+1 en `arboles_quitados` cuando los quitados nuevos están en terreno idéntico a la
  base". En r3 desaconsejé tolerancias en este contador; hoy está probado, con RNG determinista, que es sorteo y no relieve. Si se elige (b),
  hay que dejar la lista de los 4 objetos en `linea_base.json`.

Mi preferencia es (a): son 10 minutos y el código ya está escrito.

## 2. KPI del relieve (acotación 1): cumple

`medir_relieve.log` (r4), base -> r4:

| KPI | Base -> r4 | r3 | Umbral / estado |
|---|---|---|---|
| Pared Y caída a 25 m | 4.5 -> **32.4 %** | 33.6 | >= 30: ok |
| Pared Y caída a 50 m | 22.1 -> **23.3 %** | 23.3 | >= 20: ok |
| Pared Y caída a 20 m | 10.5 -> 25.7 % | — | informativo |
| Pared Y caída a 15 m | 0 -> 7.9 % | — | informativo |
| `pared_roca` en tierra | 22.7 -> **51.0 %** | 52.2 | >= 50: ok, justo |
| Roca > 35 grados | 21.2 -> **81.7 %** | — | ok |

Estructura por filas de 10 m: PyC 33/102; imposibles 15.

**Cúpula 56.**
- Cumbre (39.1, 520.2, 122.38), +0.5 grados sobre el ojo.
- **78 caras vistas a menos de 20 m de la cumbre: máximo 29.2 grados, 0.0 % por encima de 30.**
- Todas las caras: 134, el 32.8 % por encima de 30. Es el flanco trasero, que es la pared del KPI, y no se ve desde 56.
- Roca por cara vista en la isla 0, **dientes 0**. Veredicto del script: `CUMPLE`. La base daba `NO cumple` (máximo 52.5 grados).

Visual, par r3|r4 de `despues_ac/56` y `despues/56`: el cono de arista recta y la fila de 6 dientes de r3 han desaparecido. Queda una loma
redonda de hierba seca con el ciprés en la cumbre, que en modo normal se lee como matorral verde. A la derecha aparece más línea de mar y una
isla. Es forma Pixar y queda cerrado.

El "mar >= 25 % en 56" pasa a F2 por escrito (acotación 1). Hoy es 0.8 % en la vista sintética.

Corredor a menos de 4.5 m dz 0.100 (= r3), McLaren a menos de 25 m 0.12 (= r3), Loews 0.000.

## 3. Tomas: ok / mejora / regresión (criterio = modo AC; el modo normal se anota)

Las cifras son base -> r4 de `medidas_ac.json`, con r3 entre paréntesis de `medidas_r3_r4_ac.json`. Los colores son medias de región en
`despues{,_ac}/*.png` a 1600x900.

| Toma | AC | Nota |
|---|---|---|
| 49_piloto_s300 | **mejora** | pared_lisa 87.0 -> **7.1 %** (6.3); roca 65.6 -> 40.6; riqueza 0.88 -> 2.24. McLaren AC #8E978E (H 123, S 0.06; r3 #8A9797 H 182): el tinte azulado ha desaparecido. Normal: McLaren #6A6D62 (H 76, S 0.10, V 0.43): oliva oscuro, no caliza cálida, con las líneas de estrato aún marcadas (§5 n.º 4). Talud #B7B6A9. |
| 50_piloto_s800 | **mejora (con reserva)** | verde 11.0 -> 1.7; riqueza 1.21 -> 2.33; pared_lisa 39.3 -> 19.7. Fachadas, tejas y laderas doradas, bien. Reserva: `siluetas_20_120` **1 -> 0** (r3 2). En el par r3\|r4 se pierden el pino piñonero y 2 copas redondas de la ladera derecha a 20-120 m (sorteo nuevo), y la ladera queda pelada con los muros. No la cuento como regresión de toma porque el conjunto es claramente mejor que la base (césped fluorescente -> hierba seca, x1.9 de riqueza), pero ya está por debajo de la base en esa métrica (§5 n.º 3). Bloque de roca por cara a la izquierda con borde en sierra (W). Normal: mejora. |
| 51_piloto_s1700 | **mejora** | roca 5.0 -> **46.5 %** (51.9); pared_lisa 61.5 -> 20.0; riqueza 1.07 -> 2.36 (2.46). La pared derecha AC es #C7C1A1 (H 50, S 0.19, V 0.78; r3 S 0.14): más cálida. Al fondo, el cono pasa a loma con una losa de roca recortada. Normal: sin las horizontales continuas ni las estrías oblicuas de r3 (v4 + 18.2); pared #D6CFB9 (H 45, S 0.14). |
| 52_piloto_s2900 | **mejora** | verde 10.3 -> 1.8; siluetas 6 -> **11** (8); riqueza 1.04 -> 2.20. pared_lisa 0.0 -> 27.9 (= r3 27.5): ladera seca lisa, informativo (normal 53.5 -> 56.5). |
| 53_piloto_s3400 | **mejora** | riqueza 0.75 -> 2.30; fachadas, cúpulas y asfalto bien. Siluetas 4 -> 2 (r3 5), informativo. |
| 54_piloto_s4150 | **mejora** | pared_lisa 78.3 -> **23.2 %** (31.0): < 30 cumplido. Roca 6.2 -> 27.2; riqueza 0.30 -> 1.19 (1.51): islas ahora redondas, con menos textura. 2 islas romas con faro, sin peñascos-torre. Horizonte banda director 39.2 % y mar abierto 60.8 %. Normal: la roca del lazo tiene bandas oscuras de estrato largas y curvas, cosmético (§5 n.º 9). |
| 55_postal_tunel_salida | **mejora** | pared_lisa 69.2 -> 2.2; cordillera de domos/lomos sin agujas (r3 agujas). Siluetas 2 -> 0 (r3 5), informativo. |
| 56_postal_cima_bahia | **mejora** (era regresión de forma en r1-r3) | cúpula sin dientes (§2); roca 0.9 -> 43.7; riqueza 1.23 -> 2.11. Mar a F2. |
| 57_postal_viaducto | **mejora** | pared_lisa 83.2 -> 31.7 (39.6); islas y cordillera romas; banda director 44.2 %, mar abierto 55.8 %. |
| 58_postal_loews | **mejora** | pared_lisa 39.8 -> 9.7; césped 1.1 -> 0.3 (isleta); bandas 0 -> 1 (= r3, cresta de la isla). Normal: bandas 4 -> 2. |
| 59 / 59b | **mejora** | pared_lisa 89.5 -> 14.0 y 91.2 -> 5.2. |
| 60_puerto_llanta_cenital | ok | sin cambio relevante. |
| 61_orilla_piloto_s150 | **mejora** | césped 0.7 -> 0; isletas tras la valla; bandas 1 (= r3). |
| 62_tribuna_piloto_s5100 | **mejora** | pared_lisa 85.6 -> 8.6; McLaren AC #849A99 (H 177, fuera de 180-240 por poco). |
| 63_horizonte_piloto_s2200 | **mejora** | césped 1.4 -> 0; siluetas 16 -> 17 (r3 10); 2 islas romas. |
| 01_aerea_general | **mejora** | verde 20.4 -> 0.7; riqueza 2.33 -> 2.55. |
| 07_tierra_subida | **mejora (con reserva)** | roca 2.2 -> 29.1 (36.9). La sierra de dientes de r3 se reduce, pero queda un **bloque de roca por cara en L con bordes rectos** en el centro (P1 [W]). Normal: celosía de tile (§5 n.º 5). |
| 13_puente_alto | **mejora** | pared_lisa 71.9 -> 14.1; cordillera roma (en r3, agujas y una losa-torre); banda director 33.5 %. |
| 21_montana_dentro_del_lazo | **mejora** | cordillera de domos; macizo dorado; roca por cara en sierra en las laderas (W). |
| 36_roca_casino_general | **mejora (con reserva)** | AC: ladera izquierda con un bloque de roca por cara de frontera en sierra (W, cosmético 36 atenuado, no cerrado). Normal: celosía de 4 m. |

Set `paleta` (05/06/08/09/14/16/21/22/39):
- Césped **0.00 %** en las 9, en los dos modos.
- bandas_blancas 0 salvo 09 = 1, en los dos modos.
- AC verde 25.6 -> 1.9 %.
- Roca por cara en sierra (W) muy visible en AC en 08, 14, 16, 22 y 39.
- Celosía de tile clara en modo normal en 08, 14, 39, 05 y 06.

**Regresiones de piloto (49-54): AC 0, normal 0.** r3 -> r4 en piloto: 50 pierde los árboles de la ladera derecha (reserva arriba). 54 y 13
bajan de riqueza por las islas y cordilleras romas: es lo que se pidió.

## 4. KPIs con cifras

| KPI | Objetivo | Medido r4 (r3) | Estado |
|---|---|---|---|
| `pct_cesped` piloto (15 tomas), AC | < 8 % | 0.02 % (base 0.40); 0.0 en 49-54 | ok |
| `pct_cesped` piloto, normal | < 8 % | 0.02 % (base 6.76) | ok |
| `riqueza` piloto | x2 | AC 0.937 -> 2.067 (x2.21); normal 0.882 -> 2.048 (x2.32) | ok |
| `varianza_local` piloto AC | - | 0.020 -> 0.040 | ok |
| `bandas_blancas` 07 / 08 | 0 | 0 / 0 en los dos modos | ok |
| Verde en nz < 0.7 | 0 % | roca 99.8 %, verde 0.1 % (máscara r4) | ok |
| Pared Y caída 25 / 50 m (acotación 1) | >= 30 / >= 20 % | **32.4 / 23.3** | ok |
| Cúpula 56 (<= 30 grados en 20 m, sin dientes) | sí | máximo 29.2 grados, 0 % > 30, dientes 0; visual sin cono ni arista | ok |
| pared_roca tierra | >= 50 % | 51.0 (52.2) | ok (justo) |
| Roca > 35 grados | >= 80 % | 81.7 | ok |
| Horizonte, métrica del propietario (`medir_horizonte`, normal) | media >= 50 %; mar abierto 54/63 >= 50 | 54 44.8 / 57 51.7 / 13 51.8 / 21 100 / 61 35.6 = **56.8 %**; mar abierto **55.2 / 72.5** | ok |
| Horizonte, métrica del director (banda 60 px) | media >= 45 %; mar abierto 54/63 >= 50 | AC: 54 39.2 / 57 44.2 / 13 33.5 / 61 10.9 / 21 sin línea en la banda (silueta > 60 px en todo el ancho = cubierta, 100 % como en r3) = **45.6 %**; mar abierto **60.8 / 75.4**. Normal: 40.2 / 56.2 / 51.0 / 34.1 = 45.4 % de 4; mar abierto 59.8 / 71.0 | ok (justo) |
| Horizonte: V < cielo, sin agujas | sí | islas y cordilleras romas en 13/21/54/55/57; HORIZ_ 23 mallas, 210 778 tris (<= 250 k), 14 materiales | ok |
| `puerta.json` (acotación 3) | ok: true (heredados <= 23 no bloquean) | **false**, 1 motivo (`arboles_quitados` 4 > 3); urbanismo 13 heredados | **NO** |
| Tris KN5 | <= 6.0 M | **4 752 822** (base 4 450 279; +302 543 de F1: banda TERRENO y HORIZ_) | ok |
| Materiales con uso | <= 520 | 512 | ok (quedan 8) |
| RGB fuera de `paleta.json` | 0 | **33** de 123 juzgados (base: 57 de 95). **3 nuevos de F1**: `MAT_VEG_cipres_b` #335144 (base #45815D, variante), `MAT_VEG_retama` #A5A77F (base #95B86F, variante), `MAT_fondo_marino` #C2DECF (material nuevo); 30 heredados de los kits; 27 de la base arreglados | NO (MENOR, §5 n.º 2) |
| McLaren y roca con caliza cálida (decisión 10) | normal: tono y S; AC: H fuera de 180-240 | AC: McLaren 49 H 123 / 62 H 177; roca 51 H 50, 55 H 69, 07 H 76, 54 H 163: ok. Normal: McLaren #6A6D62 H 76 S 0.10 V 0.43 (caliza media #B3A68A: H 41 S 0.23 V 0.70): **no**. Roca 51 #D6CFB9 H 45 S 0.14 (ok); 54 lazo #606964 H 144 S 0.08 (fría) | parcial |
| Sin retícula en modo normal | sí | juntas largas y estrías oblicuas fuera (36, 51, 07). **Sigue la celosía de tile de ~4 m** en laderas de roca/seca (08, 07, 36, 14, 39, 05, 06). Recorte 08: paso alto sdV 20.5 -> 15.3 (más suave), pero el pico de autocorrelación es 0.32 -> 0.40: la repetición es más regular | NO (MENOR, §5 n.º 5) |
| Vértices TERRENO (banda 2 m) | +40-50 k | 266 255 -> 311 536 (+45 281) | ok |
| Plan de vegetación | 6-9 k | 7 514 árboles + 14 740 matas, VERIFICACIÓN 0/0/0 | ok |
| Siluetas 20-120 m 50/51/52 (informativo) | x3 (F3) | 1 -> 0 / 1 -> 1 / 6 -> 11 (r3 2 / 1 / 8) | parcial (50 < base) |
| Pipeline | rc 0 | 09:05 -> 09:15, rc 0, `ERRORES: ninguno`, eco final presente; prueba en seco determinista (geometría = geom_v59) | ok |
| A/B | 21 + 9, 2 modos | 60 renders, 0 avisos, 144 s | ok |

## 5. Problemas (gravedad / propietario / prueba)

1. **REAL — integrador** (decisión: coordinador). `puerta.json ok: false` por `arboles_quitados` 4 > 3. Las pruebas y el arreglo están en §1.
   Es el único bloqueo de F1.
2. **MENOR — materiales (+ mascara para `MAT_fondo_marino`).** Hay 3 literales RGB nuevos de F1 fuera de la paleta v2, contra la letra de la
   acotación 6: `MAT_VEG_cipres_b` #335144, `MAT_VEG_retama` #A5A77F y `MAT_fondo_marino` #C2DECF. Llevarlos a `cipres_pino_oscuro`, `salvia`
   y a la arena de paleta (o darlos de alta en `paleta.json` con permiso del coordinador) antes del zip v1.2: son 3 líneas. Los 30 restantes
   (10 de LOEWS congelados, 5 de MCOCHE, OLI_, PENON_, flores y troncos) vienen de la base y van a F2. Prueba: `presupuesto_paleta.log` (r4)
   frente a mi pasada sobre la base (57 FUERA).
3. **MENOR — integrador / vegetacion_plan.** En 50, `siluetas_20_120` es 0, por debajo de la base (1) y de r3 (2): se pierden el pino
   piñonero y 2 copas de la ladera derecha por el sorteo nuevo. La decisión 8 lo dejaba para F3 porque "no es regresión contra la base", y hoy
   sí lo es en esa métrica. Si se regenera para el n.º 1, comprobar 50. Si no, F3 tiene que plantar al menos 3 copas en la ladera derecha de
   s 800 a 20-120 m. Lo mismo, a menor escala, en 53 (4 -> 2) y en 55 (2 -> 0).
4. **MENOR — materiales.** McLaren en modo normal #6A6D62 (H 76, S 0.10, V 0.43): oliva oscuro con líneas de estrato, no caliza cálida
   #B3A68A (S 0.23, V 0.70). En AC ya no es gris azulado (H 182 -> 123: cumple la decisión 10). El tile de 24 m quitó las manchas periódicas.
   Falta el tono base y bajar las juntas en este kit (10.5, "Rocas" de montana_mclaren). La roca del lazo en 54/13 en normal es #606964
   (H 144): fría.
5. **MENOR — mascara / materiales.** Celosía de tile de ~4 m en modo normal en laderas de roca y hierba seca: 08 (muy visible), 07, 36, 14,
   39, 05 y 06. Viene del detalle A en BOX con su repetición: las juntas largas se han ido, la repetición no. Hay que romperla con un segundo
   tile girado o escalado (factor 2.7) mezclado por ruido de 20-40 m, o con la variación por celda de 18.2. Prueba: recorte 1:1 de
   `despues_paleta/08` r3|r4.
6. **MENOR — [W] 04_export (P1) / mascara.** Roca por cara de 4 m con bordes en sierra o en L fuera de las 3 zonas: 07 (bloque en L), 36
   (frontera de la ladera), 50 (izquierda), 21, 08, 14, 16, 22 y 39 en AC. No bloquea F1 (acotación 4). La mitigación interina está
   aplicada (ruido 0.20, banda 2 m, nz < 0.62 en 56/51/07) y en 56/51 funciona.
7. **MENOR — integrador / 04_export.** `revisar_fisica_ac` no se ha ejecutado. El TERRENO llega al writer con nx*ny + 45 281 vértices
   (nota A10 en P1). Es **condición previa del zip v1.2**: hay que ejecutarlo antes de empaquetar, aunque no bloquee la promoción de la
   escena Blender.
8. **MENOR — integrador.** Materiales con uso 512 de 520: quedan 8 de margen para F2. Hay que pedir la fusión de materiales antes de añadir
   los de F2.
9. **COSMÉTICO — materiales.** 54 en normal: bandas oscuras de estrato largas y curvas en la roca del lazo, que se leen como arañazos.
   Atenuar su amplitud con la distancia.
10. **COSMÉTICO — horizonte.** Con la métrica del director, 61 cubre el 10.9 % y 13 el 33.5 %. La media cumple justo (45.6 %). La loma
    HORIZ_loma.009 no se ve desde 54 (tras la pared del lazo). Basta para F1. En F2, si se quiere margen, 1 islote bajo (< 60 px) en la
    ventana de 61.
11. **COSMÉTICO — terreno.** Costuras de 2.03 m / 127 celdas (= base): F2 (acotación 7).

## 6. Lo que SÍ está bien (no tocar)

- Paleta v2 en fachadas, tejas, cúpulas verdín y casino crema.
- Césped 0.00 % en todas las tomas de piloto y postal, y en las 9 del set paleta, en los dos modos.
- Arcenes y taludes en hierba seca; asfalto con grano.
- Cúpula de 56.
- Relieve de la tierra: PyC 32.4 / 23.3, pared_roca 51.0, > 35 grados 81.7, con el corredor (0.100) y Loews (0.000) intactos.
- pared_lisa 49 7.1 / 54 23.2 / 55 2.2 / 57 31.7 / 59 14.0 / 62 8.6.
- Horizonte romo y del color correcto (210 778 tris).
- RNG determinista por zona: `revisar_urbanismo` 13 heredados, enterrados y flotaban por debajo de la base.
- Pipeline determinista en 10 minutos; A/B completo en 144 s.
- Presupuesto y grep de paleta ya en el pipeline.

## 7. Para cerrar F1

1. **Integrador:** regenerar una vez con el filtro de pendiente del casino; comprobar `puerta.json ok: true` y el A/B de 49-54 en AC sin
   cambios más 36/50/58/59/62. O bien el coordinador escribe la tolerancia +1 de §1(b).
2. **Materiales:** los 3 literales del n.º 2 (antes del zip).
3. **Integrador / 04_export:** `revisar_fisica_ac` con la banda de 2 m (antes del zip).
4. Se promueve y se hace el zip v1.2. Los n.º 3-11 van al registro para F2/F3 como MENOR/COSMÉTICO.

Con el paso 1 en `ok: true` y el paso 2 hecho, para mí F1 queda aprobada sin otra ronda de director, salvo que el A/B de 49-54 cambie.

Ficheros citados:
- `_rev/puerta.json`, `_rev/presupuesto_candidata.json`, `_rev/asentar_candidata.json`, `_rev/PROMOCIONES.md`.
- `_rev/logs_f1_r4_pipeline.out`.
- `_rev/logs_f1_r4/{medir_relieve,asentar_objetos,presupuesto_paleta,integrar_escena}.log`.
- `RONDA15_PLAN.md` l.479-486.
- `_rev/fase_visual/{ACOTACIONES_COORDINADOR_F1.md, f1r4_entregas_cache.json, director_f1_r3.md}`.
- `renders/ab/f1_r4/{hoja_f1_r4_*.png, AB_*.png, AB_ac_*.png, despues{,_ac,_paleta,_paleta_ac}/, medidas*.json/.log,
  horizonte_{ac,normal,director_ac}.log}`.
- `renders/ab/f1_r3/despues{,_ac,_paleta}/`.
