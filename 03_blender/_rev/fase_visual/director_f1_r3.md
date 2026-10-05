# Director de arte — F1 (fase visual), ronda 3 — 04/10/2026 ~23:25

**Veredicto: NO APROBADO** (`aprobado = false`). Motivos de bloqueo: (1) `_rev/puerta.json` `ok: false` (3 motivos: revisar_urbanismo
27 > 23, asentar enterrados 60 > 57, flotaban 29 > 28); (2) KPI del bloque 1 de F1 sin alcanzar y sin acotación escrita del coordinador
(pared Y caída a 25 m **33.6 %**, obj 40; postal 56 mar **1.1 %** del cuadro, obj 25, y la cima sigue siendo un cono de arista recta).
Todo lo demás de r2 que era REAL o se pedía para r3 está hecho o ha mejorado: terreno ejecutó su ronda (25.5 -> 33.6 %, pared_roca
52.2 %), el proxy AC ya enseña la roca con el color del writer (P1 adelantado), el contraste del desmonte de 51 se lee (3 tonos, ΔV 0.17-0.21),
el horizonte cubre más línea de mar (54: 34.8 -> 43.2 %; 57: 3.4 -> 28.4 %), 0 regresiones en las 6 vistas de piloto en modo AC.

Regresiones en vistas de piloto (49-54), MODO AC: **0**. Modo normal: **0**. Postal 56: **regresión de forma** (igual que r1 y r2; cono
puntiagudo + fila de dientes de roca a la derecha), en AC y en normal. r2 -> r3: en 50 `siluetas_20_120` baja 6 -> 2 (sigue > base 1).

Candidata juzgada: `_rev/escena_candidata.blend` md5 `d7e23a550d9c32d1f55f315f47951542` (23:10); logs `_rev/logs_f1_r3/`;
`_rev/logs_f1_r3_pipeline.out` (23:04 -> 23:10, ERRORES: ninguno; le falta la última línea `PIPELINE rc=0` porque la sesión del integrador
se cortó en el eco final: `candidata.json`/`puerta.json`/`vegetacion_candidata.json` 23:10:14 completos, `_rev/cola/` sin slot huérfano);
`_rev/puerta.json` 23:10; hojas y medidas en `renders/ab/f1_r3/` (A/B lanzado por el director con el `ab_r3.sh` del integrador a las 23:10,
219 s, 21 + 9 tomas x 2 modos, 0 avisos, montajes 4/4, medidas 6/6). Base: `_rev/escena_antes_visual.blend` = `renders/ab/_base_antes/`.

## 0. Qué he mirado

- 6 hojas: `hoja_f1_r3_piloto.png`, `hoja_f1_r3_piloto_ac.png`, `hoja_f1_r3_aereas.png`, `hoja_f1_r3_aereas_ac.png`,
  `hoja_f1_r3_aereas_paleta.png`, `hoja_f1_r3_aereas_ac_paleta.png`.
- 30 pares `AB_*`/`AB_ac_*` de 49-54, 55-59 (+59b) y 01/07/21/36 en ambos modos, más recortes 1:1 de `despues_ac/{07,56,51,36,50,49,55}`
  y `despues/{51,36,07}` (scratchpad del director, no en el proyecto).
- `medidas.json`, `medidas_ac.json`, `medidas_paleta{,_ac}.json`, `medidas_r2_r3{,_ac}.json`.
- Medias por región (PIL/numpy, sin Blender) y cobertura de horizonte por columnas (línea cielo/mar con silueta `HORIZ_` en la banda
  entre el último píxel de cielo y el primero de mar), con el MISMO método sobre `f1_r2/despues_ac` para comparar.
- Logs: `preparar_geometria`, `medir_relieve`, `urbanismo`, `mascara_terreno`, `vegetacion`, `construir_pista`, `integrar_escena`,
  `revisar_flotantes/invasores`, `asentar_objetos`, `revisar_urbanismo`, `nada_en_pista`, `mejorar_materiales`, `aplicar_texturas`,
  `comprobar_rutas`; `renders/qa/terreno_mask_stats.json`; `_rev/_tmp_terreno/r3/atribucion_puerta.py` (ejecutado, solo lectura).
- Blender: 0 vistas extra. No he modificado ningún fichero del proyecto salvo este informe.

## 1. Bloqueo n.º 1: `puerta.json ok: false` (propietario: integrador; red: terreno y coordinador)

Regla "no peor que la base" (base 15:12). Motivos y atribución (`atribucion_puerta.py`, candidata 23:10):
- `revisar_urbanismo` **27 > 23** (r1 25, r2 29). Por tipo (base -> r3): `objeto_salto_grande` 8 -> **11**, `prop_camino` 1 -> **2**,
  `sendero_enterrado` 1 -> **2**, tipo nuevo `camino_sin_destino` **1**; desaparecen `arbol_calle` 1 -> 0, `bancal_mal_asentado` 1 -> 0
  y los 2 tipos nuevos de r2 `ermita_desnivel` (parche r3.3-A n.º 1 OK) y el `bancal` del CIMA. Prohibidos (`casa_pista`/`casa_muro`/`losa*`)
  0/1/2 = base. Atribución de los 27: **10 iguales que la base, 6 por F1** (terreno cambiado a < 10 m: `camino_sin_destino` URB_travesias_0_1
  (-488,505), `objeto_salto_grande` OLI_olivo.160 dz -0.33 / VEG_cipres.282 dz -2.21 / VEG_pino.186 dz -0.90, `prop_camino` ITAL_fuente.005
  (-86,428), `sendero_enterrado` CAMINO_tierra.003 (-272,577) dz -1.06) y **11 por sorteo** (terreno idéntico, objeto en posición nueva:
  VEG_palmera.100/.102/.103/.104 y VEG_pino.669 en s 88-144 de la recta, OLI_olivo.169 y VEG_olivo.337 en s 3056-3068, VEG_encina.202,
  `sendero_enterrado` CAMINO_tierra.001 (136,681), `sendero_volado` x2).
- **El parche r3.3-A n.º 3 (fuentes prohibidas para el A*) NO ha surtido efecto**: `prop_camino` ITAL_fuente.005 (-86.1, 428.0) sigue; el
  sendero CIMA arranca en pueblo_alto_ladera_salida0 (-93, 423), a 8.6 m de la fuente, dentro de la exención del arranque (`cerca_ini` 16 m).
  Hay que aplicar la segunda mitad del parche (margen del recorte "la cinta pisaba la plaza" 0.3 -> 1.0 m, `integrar_escena.py` ~l.5165)
  o quitar la exención a < 6 m de una fuente. Parche n.º 2 OK: `asentar` quitados con motivo "ladera imposible" nuevos = 0
  (solo VEG_cipres.011 del viaducto, igual que la base; VEG_pino.468 es copa sobre calle).
- `asentar.enterrados_mas_0_6` **60 > 57** (r2 66): 37 iguales, 5 F1, 18 sorteo. En celdas que F1 NO mueve: base 51 (57 - 6) vs
  candidata 52 (60 - 8): **1 peor**, así que el criterio que el propio terreno puso en r3.3-B ("no peores que la base en celdas idénticas")
  NO se cumple: **no propongo re-base de enterrados**. `flotaban_mas_0_6` **29 > 28** (r2 25): 10 F1, 8 iguales, 11 sorteo; en celdas
  idénticas 19 = 19 (el +1 está en celdas F1). Mejoras: `arboles_quitados` 2 < 3, `bancales_mal` 0 < 1.
- Igual o mejor que la base: 193 casas, 0 fallos de plan, nada_en_pista 11 (tierra 0; las 11 farolas de la base), invaden 0,
  hierba_asfalto 0, fosos 0, costuras 2.03 m / 127 celdas (= base, aviso), Loews 0.000, integrar "ninguno", edificios flotantes 3 = base.

Decisión del director: la puerta la tumban ahora sobre todo **el sorteo del RNG de `integrar_escena`** (11 de 17 fallos nuevos de
urbanismo y 18/11 de enterrados/flotaban están en terreno idéntico) y 6 fallos de colocación junto a la tierra tallada (todos del
integrador, no del relieve en sí). Camino: (a) integrador: semilla del RNG por zona (determinismo, como pide el plan 7 para los árboles)
para que los fallos de sorteo dejen de moverse entre rondas, + recorte 1.0 m en el arranque de los senderos + re-asentar/quitar los 5
objetos F1 (OLI_olivo.160, VEG_cipres.282, VEG_pino.186, CAMINO_tierra.003 en 2 vértices / 0.26 m, el muro perdido de URB_travesias_0_1
(23 -> 22 muros al suavizar la berma, `integrar` dice "extremo sin destino en (-488, 505)")); (b) coordinador, por escrito: si tras (a)
los contadores de asentar siguen a ±3 de la base por sorteo, tolerancia explícita en `linea_base.json` para `enterrados/flotaban` y
`objeto_salto_grande` de `VEG_*` (nunca para `casa_*`, `losa*`, `prop_pista/pitlane`, `arboles_quitados`).

## 2. Bloqueo n.º 2: KPI de F1 del bloque 1 (propietario terreno; decisión del coordinador)

`medir_relieve.log` (23:05) ANTES (base) -> DESPUÉS (r3), con r2 entre paréntesis:
- pared Y caída a 25 m (s 1430-2440): 4.5 -> **33.6 %** (r2 25.5; obj >= 40). A 20 m 10.5 -> 29.8 (27.3); a 15 m 0 -> 11.7; a 50 m
  22.1 -> 23.3 (r2 27.7; obj 60). Estructura por filas de 10 m: PyC 34/102, imposibles por la pista 17 (terrazas 8, pared a ambos lados 6,
  cresta 3), solo pared 14, solo caída 19, ninguno 18. Por 100 m: 1430 0 / 1530 18 / 1630 58 / 1730 30 / 1830 26 / 1930 82 / 2030 10 /
  2130 78 / 2230 0 / 2330 38 / 2430 0 %.
- pared_roca en tierra 22.7 -> **52.2 %** (obj 50: cumplido); toda la pista 37.3 %; caída en algún lado 55.5 %.
- roca > 35 grados 81.7 % (obj 80: cumplido, es del bloque 2.2).
- 120 m tras pueblo_subida_ladera 83.0 -> 83.0 m (obj 110): bloque 1.3, informativo. Orilla z > 10 m 5.6 % (obj 25): bloque 1.4, informativo.
- postal 56: mar **1.1 %** del cuadro medido en `despues_ac/56` (vista sintética del log: 1.2 %; base 0.9); horizonte de terreno en la
  fila 20 de 108 (r2 25, base 35). Terreno dice "la isla es una loma continua (118-126 m)"; el render dice otra cosa: **cono puntiagudo con
  arista recta** desde el pie hasta el vértice (recorte 1:1 de `despues_ac/56` (560-1000, 120-450) y `despues/56` con los estratos siguiendo
  la arista) y, a la derecha, una **fila de 6 dientes de roca** triangulares (recorte (1200-1600, 330-630), media #979D85 V 0.61, sdV 0.153)
  = roca por cara de 4 m sobre una ladera a 35-40 grados. Formas suaves (Pixar) no.
- corredor < 4.5 m del asfalto dz 0.100 m (obj 0.000; 7 celdas de la isla de la C26, = r2); McLaren lt_25m 0.12 m (6 celdas a 97 m de la
  pista, = r2); Loews 0.000 ok; dz r3 - r2 máx 13.8 m, 2 704 celdas > 0.5, todas en s 1200-2600 a < 120 m del borde.

Terreno pide (PARCHES_F1_terreno.md r3.1) acotar por escrito: "1a cerrado en F1 con PyC 25 m >= 30 % + pared_roca >= 50 % + 0
regresiones de forma; el resto del 40 % a F2 con el macizo del lazo". Mi recomendación al coordinador: **aceptar la acotación de cifras**
(33.6 y 52.2 son el tope razonable con este zigzag: lo demuestra fila a fila) **pero la condición "0 regresiones de forma" NO se cumple
hoy** por la cima de 56: hace falta redondear el cono (cúpula de radio >= 30 m, pendiente <= 30 grados en los 20 m superiores para que la
máscara no ponga roca en dientes) antes de dar 1a por cerrado. Sin decisión escrita, el KPI no cumple y lo digo tal cual.

## 3. Tomas del set BASE: ok / mejora / regresión (criterio = MODO AC; el modo normal se anota)

Cifras: `medidas_ac.json` base -> r3 (modo AC) y, cuando importa, r2 -> r3 de `medidas_r2_r3_ac.json`. Colores = media de región en
`despues_ac/*.png` (1600x900).

| Toma | AC | Nota |
|---|---|---|
| 49_piloto_s300 | **mejora** | pared_lisa 87.0 -> **6.3 %** (r2 32.1; obj < 30 cumplido), roca 65.6 -> 37.5 %, riqueza 0.88 -> 2.24; talud derecho caliza #8A8A81 (H 63, S 0.07) + arcén hierba seca. Reserva (= r2 n.º 6): carrocería del McLaren #8A9697 (H 181, S 0.08, V 0.59) gris AZULADO con el tile de 3 m repetido (recorte (0-600, 0-320): manchas claras periódicas cada ~95 px). Normal: mejora (McLaren #686C63, talud #9E9E94 con estratos). |
| 50_piloto_s800 | **mejora** | fachadas azafrán/siena/pompeyano, copas oliva, laderas doradas; verde 11.0 -> 2.6 %, riqueza 1.21 -> 2.35, pared_lisa 39.3 -> 20.0. Reserva: a la izquierda (0-200, 274-436) un bloque de roca por cara #8F827E con borde en sierra de 4 m; `siluetas_20_120` 1 -> 2 pero r2 -> r3 **6 -> 2** (despeje: 126 árboles quitados, r2 135). Normal: mejora. |
| 51_piloto_s1700 | **mejora** | la toma que más cambia: pared derecha de roca ocupa el cuadro (roca 5.0 -> **51.9 %**, r2 34.2), silueta derecha muy por encima del horizonte de cámara. 3 tonos: pared #AEB1A9 (V 0.69) / berma hierba seca #E5DBA9 (V 0.90) / tierra #DBC8A7 (V 0.86): ΔV pared-tierra **0.17**, pared-berma **0.21** (r2: 0.01 / 0.07): se lee (r2 n.º 3 arreglado). Reservas: pared gris NEUTRA (S 0.05; el usuario pidió caliza cálida #B3A68A S 0.23); borde roca/seca en sierra de 4 m en ambas laderas (recortes (1050-1500, 80-420) y (100-550, 330-580)). Normal: pared #C5C7BF V 0.78 (r2 #E7E1CD 0.91: ya no es "hielo") pero con RETÍCULA + líneas de estrato (§5 n.º 5). |
| 52_piloto_s2900 | **mejora** | loma dorada, pinos y cipreses oliva; verde 10.3 -> 1.7 %; siluetas 6 -> **8**; riqueza 1.04 -> 2.17. Sin línea de mar (KPI horizonte N/A). |
| 53_piloto_s3400 | **mejora** | fachada ocre naranja, cúpulas verdín, asfalto con grano; riqueza 0.75 -> 2.30; pared_lisa 36.2 -> 35.4 (r2 29.6: +6, es el muro del pit, informativo). |
| 54_piloto_s4150 | **mejora** | roca del lazo caliza #819093 (V 0.58) con pared_lisa 78.3 -> **31.0 %** (r2 40.8; obj < 30 casi); 2 islas HORIZ_ #97ADCD / #9DB4D6 (V 0.81-0.84) más oscuras que el cielo #BCDEFF (V 1.00) y que el mar #78DFFF: ningún iceberg. Cobertura de la línea mar/cielo **43.2 %** (352 de 814 columnas; r2 34.8 % con el mismo método). Sombra larga ok. Normal: mejora (roca #616964 con estratos). |
| 55_postal_tunel_salida | **mejora** | pared_lisa 69.2 -> **2.3 %** (r2 58.0); talud derecho caliza #878A82 (S 0.06, borde en sierra en la arista superior); cordillera al fondo #A9BFD7 (V 0.84 < cielo) pero de PICOS DE AGUJA (recorte (350-1050, 360-520)). Normal: mejora. |
| 56_postal_cima_bahia | **regresión (forma)** | cono puntiagudo de arista recta + 6 dientes de roca a la derecha (§2); mar 1.1 % (obj 25); roca 0.9 -> 43.5 %; `siluetas_20_120` 2 -> 1. Color correcto (hierba seca #D7D3A2 + roca). Postal: no bloquea por la regla de piloto; bloquea por el KPI del bloque 1 (§2). Normal: mismo cono con estratos marcando la arista. |
| 57_postal_viaducto | **mejora** | 2 islas (#84A4C7 / #8FABCE, V 0.78-0.81) + cordillera derecha #879DC0 (V 0.75): cobertura **28.4 %** (224/790 col.; r2 3.4 %: las lomas nuevas en la ventana de 57 funcionan); roca del lazo pared_lisa 83.2 -> 39.6 (= r2); roca 29.6 -> 11.5 (r2 -> r3). Agujas a la derecha. Normal: mejora. |
| 58_postal_loews | **mejora** | estratos en el acantilado (pared_lisa 39.8 -> 12.8), césped solo en la isleta (1.14 -> 0.33 %), isla #9FB9DA (V 0.85) a la derecha; cobertura 8.5 % (r2 2.2). bandas_blancas 0 -> 1 (cresta clara de la isla, = r2). Normal: mejora. |
| 59 / 59b postal recta puerto | **mejora** | pared_lisa 89.5 -> 14.4 y 91.2 -> 4.8 (r2 47.3 / 37.8): la ladera tras los boxes ya es hierba seca con roca en lo alto; verde 6.5 -> 5.2 (banderas/tribunas). |
| 60_puerto_llanta_cenital | ok | sin cambio relevante (riqueza 1.98 -> 1.88 por el mar liso). |
| 61_orilla_piloto_s150 | **mejora** | césped 0.74 -> 0; isla al fondo; bandas 0 -> 1 (cresta clara del HORIZ_, = r2). |
| 62_tribuna_piloto_s5100 | **mejora** | pared_lisa 85.6 -> 7.6 (r2 45.7); ladera dorada tras la tribuna. |
| 63_horizonte_piloto_s2200 | **mejora** | 3 islas, árboles oliva, pacas sobre hierba seca; `siluetas_20_120` 16 -> 10 (r2 18): menos siluetas que en r2 (despeje), pero > x1 de la base no aplica (es 20-120 m de 63, no 50/51/52). |
| 01_aerea_general | **mejora** | verde 20.4 -> 0.67 % (r2 0.26); isla dorada con parches de roca de borde poligonal (W P1); pared_lisa 23.3 -> 20.6. Normal: mejora (máscara 4 capas visible, bandas 9 -> 0). |
| 07_tierra_subida | **mejora con reserva** | AC: roca 2.2 -> **36.9 %** (r2 20.7): bloques de roca por cara #86887D (S 0.08) con borde en sierra que dominan la vista (recorte (1000-1400, 480-780)); el PARCHE CUADRADO de r2 en (1176,630) ya no se distingue como cuadrado: ese sitio es ahora el interior de un bloque de roca (#69706E, sdV 0.088). bandas_blancas 0 en ambos modos. Normal: montículos con retícula #9DA099 (sdV 0.174), "montones de hielo" más grises que en r2 (#949C95-#A2B1AE). |
| 13_puente_alto | **mejora** | pared_lisa 71.9 -> 17.8 (r2 55.0); horizonte #7388AA-#879DC0 (V 0.67-0.75) < cielo; cobertura 15.6 % (r2 0). Agujas. Normal: roca del lazo #717974 (H 138, S 0.06; r2 #859FAA H 196: el tinte azul se ha ido) con retícula. |
| 21_montana_dentro_del_lazo | **mejora** | bosque, pueblo, macizo dorado, cordillera #9FB0D3 (V 0.83) con 100 % de la línea de mar cubierta (86 col.); roca por cara en el macizo (#C7C49D) con borde en sierra. Normal: mejora, retícula en las lomas. |
| 36_roca_casino_general | **mejora** | casino crema #EEE4CF, cúpulas verdín; ladera partida en dos tonos (#E5DBA8 claro / #9E9C8B oscuro) con frontera en SIERRA de 4 m (recorte (300-800, 650-900)); bandas_blancas 1 = base (meseta). Normal: la ladera ya no es cian (#899377, H 82, S 0.19; r2 #9CCAD7 H 192) pero la RETÍCULA de celdas de 10-15 m sigue (recorte (400-900, 650-900)). |

Set `paleta` (05/06/08/09/14/16/21/22/39), modo AC: césped **0.00 %** en las 9; verde 42.8 -> 3.1 (05), 52.9 -> 0.2 (08), 35.5 -> 2.8 (39);
bandas_blancas **0/9**; 08 pared_lisa 64.8 -> 0.8 %, roca 11.4 -> 66.6 % (la cima es una pared de roca por cara). Modo normal: césped 0.00-0.01;
bandas 05 8 -> 0, 06 6 -> 0, 39 11 -> 0, 09 4 -> 1 (resto 0); 08 pared_lisa 75.6 -> 0.0 %.

## 4. KPIs con cifras

| KPI | Objetivo | Medido r3 (r2) | Estado |
|---|---|---|---|
| `pct_cesped` piloto 49-54, modo AC | < 8 % | 0.00 % en las 6 (base media 0.41) | ok |
| `pct_cesped` piloto, modo normal | < 8 % | 0.00 % en las 6 (base: 51 18.2, 52 11.9, 50 10.1) | ok |
| `pct_verde` piloto AC (15 tomas) | - | 6.10 -> 1.84 % | mejora |
| `riqueza` terreno piloto AC | x2 | 0.937 -> 2.096 (x2.24; r2 1.95); 51 1.07 -> 2.46, 54 0.30 -> 1.51 | ok |
| `varianza_local` piloto AC | - | 0.020 -> 0.041 (x2.1) | ok |
| `bandas_blancas` 07 / 08 | 0 | 07: 0 (AC y normal); 08: 0 (AC y normal) | ok |
| verde en caras nz < 0.7 (máscara) | 0 % | roca 99.75 %, verde **0.08 %** (`terreno_mask_stats.json`; pend > 0.84: roca 92.9 %, verde 4.69 %) | ok |
| atributo roca del terreno = canal A | sí | `construir_pista.log`: 266 255 vértices, > 0.49 en el 26.8 %, difiere de v1 en el 4.45 % | ok (R3.4) |
| 51 desmonte >= 3 tonos (AC) | sí | pared #AEB1A9 V 0.69 / tierra #DBC8A7 V 0.86 / berma #E5DBA9 V 0.90: ΔV 0.17 y 0.21 (r2 0.01 / 0.07) | ok (r2 n.º 3 arreglado); pared gris neutra S 0.05 (reserva) |
| celdas > 35 grados con roca | >= 80 % | 81.7 % (base 21.2) | ok |
| pared Y caída a 25 m (tierra) | >= 40 % | **33.6 %** (r2 25.5; base 4.5); 20 m 29.8; 50 m 23.3 | NO (sin acotación escrita) |
| pared_roca en tierra | >= 50 % | **52.2 %** (r2 45.8) | ok |
| postal 56: mar en el cuadro | >= 25 % | 1.1 % (r2 1.2) | NO |
| horizonte >= 60 % del ancho mar/cielo en 49/52/54/56 (AC) | >= 60 % | 49: sin mar (N/A); 52: sin mar (N/A); 54: **43.2 %** (r2 34.8); 56: 1.7 % (115 col. de mar). Informativo: 21 100 % (86 col.), 57 28.4 (r2 3.4), 13 15.6 (0), 58 8.5 (2.2) | NO (como está escrito es incumplible en 49/52 y 56; ver §5 n.º 6) |
| horizonte: V < cielo, 0 px #FFFFFF | sí | 54 #97ADCD / 57 #84A4C7 / 13 #7388AA vs cielo #BCDEFF; log HORIZONTE 22 mallas, 14 materiales | ok |
| vegetacion_plan árboles | 6-9 k | **7 537** árboles + 15 168 matas, 299 masas (`vegetacion_candidata.json`: pino 5 299, encina 1 214, palmera 470, olivo 451); vecino < 6 m 83.7 %; z > 80 m 52.6 %; VERIFICACIÓN 0/0/0 | ok (se integra en F3) |
| máscara suma = 1 | 100 % | 100.00 % (desvío máx 1/255); matorral 45.9 / seca 21.6 / tierra 4.8 / roca 27.8 %; AO 0.757; dirt < 8 m tierra 91.7 % | ok |
| rutas de imagen relativas en la candidata | 0 | 0 relativas / 15 absolutas (`comprobar_rutas.log`, 198.7 MB); construir_pista 7 abs / 0 rel | ok |
| `puerta.json` | ok: true | **false** (3 motivos, 2 avisos) | NO |
| urbanismo plan | >= 190 casas, 0 fallos | 193 casas, 0 fallos, huecos 515 m (obj < 300: bloque 5) | ok |
| tris KN5 | <= 6.0 M | sin informe (el integrador escribió `_tmp_integrador/r3/presupuesto_paleta_candidata.py` pero no lo ejecutó; HORIZ_ 197 690 tris dentro de los 250 k) | sin medir |
| RGB fuera de `paleta.json` | 0 | no medido (mismo script) | sin medir |
| pared_lisa 49 / 54 (bloque 2, informativo) | < 30 % | **6.3 %** / 31.0 % (r2 32.1 / 40.8) | ok / casi |
| siluetas 20-120 m 50/51/52 (bloque 4, informativo) | x3 | 1 -> 2 / 1 -> 1 / 6 -> 8 (r2: 6 / 1 / 7) | parcial (F3) |
| pipeline | rc 0, 1 intento | 23:04 -> 23:10, ERRORES: ninguno, 193 casas, integrar 161 s; prueba en seco determinista (md5 de `geometria_3d.json` = `geom_v42.json`) | ok (falta solo el eco final) |
| A/B | BASE 21 + paleta 9, 2 modos | 60 renders, 0 avisos, 219 s; proxy AC con `MAT_terreno_roca` = #877D68 + caliza_d 3 m (log) | ok |

## 5. Problemas (gravedad / propietario / prueba)

1. **REAL — integrador** (red: terreno, coordinador). `puerta.json ok: false`: revisar_urbanismo 27 > 23 (10 base + 6 F1 + 11 sorteo),
   enterrados 60 > 57 (52 vs 51 en celdas idénticas: NO cumple el criterio de re-base), flotaban 29 > 28. El parche r3.3-A n.º 3 no quita
   `prop_camino` ITAL_fuente.005 (fuente a 8.6 m del arranque del CIMA, dentro de `cerca_ini` 16 m). Arreglo en §1: recorte 1.0 m en el
   arranque, semilla por zona en el RNG de `integrar_escena`, re-asentar/quitar los 5 objetos F1; después, tolerancia escrita del
   coordinador si queda ruido de sorteo. Prueba: `_rev/puerta.json`, `atribucion_puerta.py` (salida arriba).
2. **REAL — terreno** (decisión: coordinador). KPI pared Y caída a 25 m 33.6 % (obj 40) sin acotación escrita; postal 56 mar 1.1 % (obj
   25) y la cima es un cono de arista recta con 6 dientes de roca (`despues_ac/56` recortes (560-1000,120-450) y (1200-1600,330-630)).
   Recomendación: aceptar la acotación 30 % / 50 % que propone terreno SOLO cuando la cima de 56 sea una cúpula (pendiente <= 30 grados en
   los 20 m superiores, radio >= 30 m) y el A/B de 56 no tenga dientes; el mar de 56 pasa a F2 (landform) por escrito.
3. **MENOR — materiales [W, 04_export P1] + mascara**. La roca por cara de 4 m es ahora el defecto visual dominante en modo AC porque el
   proxy ya la pinta con el color del writer: bordes en sierra en 51 (dos laderas), 07 (roca 36.9 %), 56 (dientes), 36 (frontera de la
   ladera), 50 (bloque izquierdo), 21, 01. En el KN5 de hoy el amigo verá exactamente esto (`separar_roca_terreno` por cara). P1 tiene el
   código listo (`materiales_roca.roca_caras_mascara`); mientras no esté: (a) `ROCA_ATR_RUIDO` 0.08 -> 0.20 en la máscara para romper las
   rectas del umbral, (b) subdividir a 2 m una banda de 20 m junto a la pista (plan bloque 3, riesgo R1), (c) en la cima de 56 y en las
   laderas a < 150 m de 51/07, umbral de roca por cara a nz < 0.62 en vez de 0.70 para que no salgan dientes aislados. Prueba: recortes 1:1.
4. **MENOR — materiales**. McLaren en AC: #8A9697 (H 181, S 0.08, V 0.59) gris azulado con el tile de 3 m repetido (`despues_ac/49`
   (0-600, 0-320)); igual que r2 n.º 6 (10.5 no aplicado a propósito). `MAT_MCOCHE_*` a hueso cálido 0.58 y tile BOX >= 6 m o con manchas.
   Toda la roca del proxy AC sale neutra (49 talud S 0.07, 51 pared S 0.05, 55 talud S 0.06, 07 S 0.08): comprobar que `caliza_d.png` x
   #877D68 no se desatura (el usuario pidió "sin gris"; el tono H 60-85 es correcto, la saturación no).
5. **MENOR — materiales** (modo normal; no bloquea). Tinte frío arreglado (36 ladera #899377 H 82 S 0.19, r2 #9CCAD7 H 192; 13 roca del lazo
   #717974 H 138, r2 #859FAA H 196; 51 pared #C5C7BF V 0.78, r2 #E7E1CD V 0.91) pero la RETÍCULA de `NG_caliza_estratos` (celdas de 10-15 m
   + líneas de estrato que cruzan la arista) sigue en 07 (sdV 0.174), 36, 51, 21, 14, 22 (recortes `despues/{51,36,07}`): bajar la amplitud
   de la junta con la distancia o quitar la componente vertical del patrón (r2 n.º 5, parches 10.3/10.4 pendientes).
6. **MENOR — horizonte (+ coordinador)**. Cobertura 54 43.2 % (obj 60), 57 28.4, 13 15.6, 58 8.5, 56 1.7; 49/52 sin mar. 54 mira a la
   abertura de 160 grados decidida en 7.1: el KPI escrito es incumplible. Propuesta: medir el 60 % como media de 54/57/13/21/61 (hoy 43 /
   28 / 16 / 100 / N/A) y añadir 1 loma más a 2.4-2.8 km en la ventana de 54 (brújula 190-215 grados) para pasar del 43 % al 60 %.
7. **MENOR — integrador**. Sin informe de tris de la candidata ni grep de RGB (script `presupuesto_paleta_candidata.py` escrito, no
   ejecutado; pendiente desde r1). Son 1 pasada de Blender por la cola (~1 min) + 1 línea en PETICIONES. `pipeline.out` sin el eco final.
8. **MENOR — vegetacion_plan / integrador**. r2 -> r3 `siluetas_20_120` en 50: 6 -> 2 y en 63: 18 -> 10 (despeje final 126 árboles,
   `tierra: 1 arboles sin sitio`): no es regresión contra la base (1 -> 2) pero F3 debe recuperar las masas de 50 (lado derecho, 20-120 m).
9. **COSMÉTICO — horizonte**. Picos de aguja en las cordilleras (55, 57, 13, 21): redondear (Pixar); color ya correcto, no tocar la mezcla.
10. **COSMÉTICO — terreno/mascara**. 36: ladera partida en dos tonos con frontera en sierra (r1 n.º 12, r2 n.º 11): ruido 10-30 m en el
    canal B junto a `_corte` (se arregla con el n.º 3).
11. **COSMÉTICO — terreno**. Costuras máx 2.03 m / 127 celdas (= base; objetivo < 0.6 del bloque 1): pueblo_alto_mar 2.03, casino_mar 2.01,
    pueblo_subida_ladera 1.49 (74 celdas).
12. **COSMÉTICO — integrador**. 53 pared_lisa 29.6 -> 35.4 (r2 -> r3, muro del pit sin textura visible); nada_en_pista 11 farolas = base.

## 6. Lo que SÍ está bien (no tocar en r4)

Paleta v2 en fachadas (50, 53, 09), tejas #BF6440, cúpulas verdín, casino crema; copas oliva / pino oscuro; césped solo en la isleta Loews y
jardines (0.00 % en las 15 tomas de piloto/postal en AC y en las 9 del set paleta); arcenes y taludes en hierba seca; asfalto con grano;
sol 42 grados con sombra larga (54); máscara 2048 coherente (roca 99.75 % en nz < 0.7; > 35 grados 81.7 %; atributo roca = canal A);
plan de vegetación 7 537 árboles con 0 invasiones; horizonte con color correcto (V 0.67-0.85 < cielo 1.00) y más cobertura (54 43 %, 57 28 %,
21 100 %), 197 690 tris dentro de los 250 k; roca del lazo, acantilado Loews y taludes con caliza (pared_lisa 49 6.3, 54 31.0, 55 2.3, 58 12.8,
59 14.4, 62 7.6); contraste del desmonte de 51 (3 tonos); relieve de la tierra con pared_roca 52.2 % y PyC 33.6 % sin tocar corredor
(0.100 = r2) ni Loews (0.000); rutas absolutas + lector A7; pipeline determinista (geom r3 = v42 byte a byte) en 6 min; A/B completo en 4 min.

## 7. Orden de r4

1 (integrador: recorte 1.0 m del arranque de senderos + semilla por zona + los 5 objetos F1; relanzar pipeline; `puerta.json`) -> 2 (terreno:
cúpula en la cima de 56; coordinador: acotación escrita 30 % / 50 % + mar de 56 a F2) -> 3 (mascara: `ROCA_ATR_RUIDO` y umbral en cima/laderas
cercanas; materiales: P1 en cuanto 04_export lo admita) -> 4 (materiales: McLaren cálido + saturación de la roca del proxy) -> 7 (integrador:
presupuesto + grep, 1 pasada) -> 5/6 (retícula en normal; KPI de horizonte re-escrito + 1 loma en la ventana de 54) -> 8-12. Con 1 y 2
cerrados y 0 regresiones de piloto en AC (hoy ya 0), F1 se puede promover con 3-12 abiertos como MENOR/COSMÉTICO documentados para F2/F3.

Ficheros citados: `_rev/puerta.json`, `_rev/candidata.json`, `_rev/logs_f1_r3_pipeline.out`, `_rev/logs_f1_r3/{preparar_geometria,medir_relieve,
urbanismo,mascara_terreno,vegetacion,construir_pista,integrar_escena,asentar_objetos,revisar_urbanismo,nada_en_pista,mejorar_materiales,
aplicar_texturas,comprobar_rutas}.log`, `renders/qa/terreno_mask_stats.json`, `renders/qa/medir_relieve.json`, `_rev/vegetacion_candidata.json`,
`_rev/_tmp_terreno/r3/atribucion_puerta.py`, `_rev/_tmp_integrador/r3/{ab_r3.sh,ab_r3.out,presupuesto_paleta_candidata.py}`,
`renders/ab/f1_r3/{medidas,medidas_ac,medidas_paleta,medidas_paleta_ac,medidas_r2_r3,medidas_r2_r3_ac}.json`, `renders/ab/f1_r3/AB_*.png`,
`renders/ab/f1_r3/AB_ac_*.png`, `renders/ab/f1_r3/hoja_f1_r3_*.png`, `renders/ab/f1_r3/despues{,_ac}/*.png`,
`_rev/fase_visual/{PARCHES_F1_terreno.md (r3.0-r3.6), PETICIONES_04_EXPORT.md (P1), director_f1_r2.md, DECISIONES_USUARIO.md}`.
