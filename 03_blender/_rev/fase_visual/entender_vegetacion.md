# Entender la vegetación de Porto Corsa (bloque VEGETACIÓN Y ÁRBOLES)

Lector técnico, 04/10/2026. Solo lectura: no se ha modificado ningún fichero del proyecto ni se ha
lanzado Blender (los recuentos de triángulos se han medido con un stub de `bpy` en el scratchpad,
`tris_veg.py`, ejecutando los kits con el Python del sistema; el resto sale del código, de los logs
`03_blender/_rev/logs_final/` (12:59-13:00), de `renders/qa/asentar.json` (13:00), del informe del
KN5 `04_export/kn5/informe_check_opt.json` (export del 02/10) y de las capturas de las 13:01).
Las líneas citadas son las de los ficheros tal y como están hoy.

## 0. Resumen

- Todos los árboles son mallas opacas de color plano, sin UV, sin textura, sin alfa y sin normal,
  generadas por `03_blender/assets/vegetacion_kit_v2.py` (pino, ciprés, palmera, olivo, encina,
  adelfa, arbusto; el plátano existe pero nunca se planta), `assets/olivos.py` (OLI_olivo,
  OLI_matorral) y `assets/italiano_kit.py` (ITAL_cipres, ITAL_olivo de bancales). Copa = sólido de
  revolución + 5-8 esferas "lóbulo"; tronco = tubo de 7 lados. Entre 232 y 968 triángulos por pieza.
- Se colocan como clones (`integrar_escena.clone`, malla compartida) desde una biblioteca oculta
  `LIB` de 31 piezas. El grueso (2826 árboles en la última pasada) lo pone `zona_montana`
  (`integrar_escena.py:2223-2318`) en "masas" aleatorias de 4-8 árboles sin ninguna máscara de
  pendiente/orientación/mar/pueblo, solo con la cota (3.5-80 m) y la distancia a la pista; por
  encima de 80 m no hay NADA (de ahí el "macizo verde uniforme" de las capturas 01 y 21).
- Tras los inspectores quedan 2.72 k raíces de vegetación (asentar.json 13:00): 576 pinos, 292
  cipreses (+42 de plazoleta), 220 encinas, 292 olivos VEG + 174 OLI, 171 palmeras (+8 del
  mirador), 208 adelfas, 399 arbustos, 161 matorrales, 124 rocas, 34+10 ITAL. En el KN5 son
  1.74 M de los 5.26 M de triángulos (33 %), fusionados por material en 55 mallas `DECO_MAT_VEG_*`
  / `DECO_MAT_OLI_*`, con `castShadows = 0`, shader `ksPerPixel` opaco y textura plana de 8x8 px.
- "Piruletas" = bola/huso suave sobre un palo + un solo color por material (la variación de color
  que inyecta `enriquecer_vegetacion` NO se exporta al KN5) + sin sombra proyectada en AC + reparto
  uniforme a 1 árbol por ~30 m en una pradera verde uniforme.
- Para una silueta mejor SIN CSP la vía realista son árboles de 2-3 planos cruzados con atlas RGBA
  (alfa test, doble cara), 8-24 tris/árbol: exige que el kit escriba UV y materiales con imagen+alfa
  y que `04_export/kn5_writer*.py` admita `ksPerPixelAT`/`ksTree`, `alphaTested = 1`, `ksAlphaRef` y
  PNG con canal alfa (hoy descarta el alfa de la imagen y fuerza `ksPerPixel`).
- Para TreeFX de CSP hace falta: (1) un "plan de vegetación" único (especie, x, y, z, ángulo, escala,
  anchura, color) que alimente a la vez las mallas (sin CSP) y `extension/trees/trees.txt` (con CSP),
  (2) el cambio de ejes `(x, y, z)_blender -> (x, z, -y)_AC` (el mismo de `kn5_writer.py:11`),
  (3) un FBX por especie con 2-3 LOD, pivote en la base, difusa con alfa + normal, convertido a .bin
  con el tree converter de Content Manager (en el PC del amigo), (4) `[TREES] LIST_0 = trees/trees.txt`
  en `extension/ext_config.ini` y (5) `[MODEL_REPLACEMENT_0] HIDE = DECO_MAT_VEG_?, DECO_MAT_OLI_?`
  para que, con CSP, desaparezcan las mallas y queden solo los TreeFX. Sin CSP todo eso se ignora.

## 1. De dónde sale cada árbol

### 1.1 Módulos y versiones

| Módulo | Qué aporta | Estado |
|---|---|---|
| `03_blender/assets/vegetacion_kit.py` (605 l.) | v1: palmera, ciprés, pino, adelfa, jardinera, roca, acantilado | NO se usa: `integrar_escena.load_mod` (l.40-49) carga `<nombre>_v2.py` si el nombre está en `assets/v2_aprobados.txt` (l.8: `vegetacion_kit`). Log: `modulo vegetacion_kit -> vegetacion_kit_v2.py` |
| `03_blender/assets/vegetacion_kit_v2.py` (1332 l.) | Misma API + variantes de silueta + olivo, encina, plátano, arbusto, despachador `build_arbol` | ES el kit en uso. Presupuesto autoimpuesto <= 1200 tris/árbol, <= 500/arbusto (docstring l.63; `test_vegetacion_kit_v2.py:14,248-257`) |
| `03_blender/assets/olivos.py` (442 l.) | `build_olivo` (l.237), `build_seto` (l.325), `build_matorral` (l.384); prefijo `OLI_`, materiales `MAT_OLI_*` | Lo carga `integrar` como opcional (l.54) y `zona_montana` añade `lib['olivo']` y `lib['matorral']` (l.2226-2229) |
| `03_blender/assets/italiano_kit.py` | `build_cipres` (l.622, <= 250 tris), `build_fila_cipreses` (l.650, raíz `ITAL_cipreses`), `build_olivo` (l.665), olivos hijos de `build_bancal` (l.1066) | Cipreses sueltos de los senderos y bancales (`integrar._adornos_sendero` l.5232-5320) |
| `03_blender/assets/montana_mclaren.py` | `_vegetacion` (l.1662): matas (42 tris) y pinos (78 tris) como ISLAS de una sola malla `MCOCHE_veg`, presupuesto 3400 tris (l.1591); `_podar_islas` (l.1609) | 66 islas en la escena (RONDA15_PLAN l.395) |
| `03_blender/assets/roca_lazo.py` | `_poblar` l.2958-2999: pinos alrededor del cerrete, pinos en terrazas, palmeras en la cala, 2 cipreses junto al campanile (usa el kit v2 y el italiano) + 420 "matas" propias | Log: `11 plantas/props (descartados por copa en casa: 6), 420 matas` |
| `03_blender/assets/roca_casino.py` | `vegetacion` l.2529-2568: palmeras/cipreses en el borde de la meseta, pino en cada isla de horquilla, palmeras en el muelle, pinos en taludes, matas en cornisas; nombres `VEG_penon_<tipo><var>` | ~128 plantas (RONDA15_PLAN l.382); exentas de casi todos los inspectores |
| `assets/penon_topolino.py`, `penon_cara.py` | `build_vegetacion` (mallas `PENON_vegetacion`) | NO están en la escena: `integrar` los construye con `con_vegetacion=False` (l.2048, 3050, 3463) |

`vegetacion_kit_v2.build_arbol` (l.1262-1291, reparto ponderado por especie) NO lo usa nadie:
`integrar_escena.build_library` llama a cada constructor con `alto` y `seed` fijos.

### 1.2 Cómo se construye una pieza (vegetacion_kit_v2)

- Acumulador `_MB` (l.178-216): junta (verts, caras, material, smooth) de varias primitivas y crea UN
  objeto malla con `from_pydata`; `use_smooth` por cara; NO crea UV ni vertex colors. Materiales
  `_mat(clave)` (l.155-172): Principled con `Base Color` plano y `Roughness` 0.6-1.0; 75 claves en
  `_PALETA` (l.78-152); nombre `MAT_VEG_<clave>` (48 materiales de vegetación en el KN5).
- Primitivas: `_sphere` (l.222, esfera UV de 7-10 segmentos con jitter radial), `_lathe` (l.272,
  revolución de un perfil), `_tube` (l.310, tronco por polilínea, `cap_bottom` para que no se vea hueco
  con el backface culling de AC), `_doble` (l.371, duplica caras con winding invertido: palmas a dos
  caras), `_hoja_abanico` (l.414), `_tronco` ahusado/curvo (l.441), `_rama` (l.484), `_lobulo` y
  `_anillo_lobulos` (l.492, 497), `_flores_sobre` (l.515).
- Variantes por `seed % N` o `variante=` (l.531): pino `parasol|carrasco|costero|joven` (l.747),
  ciprés `lapiz|llama` (l.682), palmera `datil|washingtonia|abanico` (l.549), adelfa
  `rosa|blanca|roja` (l.869), arbusto `romero|lavanda|retama` (l.914). Cada objeto lleva
  `ob["VEG_variante"]` (y `VEG_tipo` solo si viene de `build_arbol`).
- Olivo (l.966), encina (l.1023) y plátano (l.1057): tronco + 2-4 ramas + 5-9 lóbulos esféricos
  solapados; dos tonos de verde alternados por lóbulo.

### 1.3 Triángulos por pieza (medidos con el stub, 24 semillas por tipo)

| Pieza (v2) | tris min / mediana / max | vértices (med.) | materiales |
|---|---|---|---|
| pino alto=12 (todas las variantes) | 440 / 484 / 690 | 267 | 3 |
| - parasol / carrasco / costero / joven | 601-732 / 440-504 / 484 / 456-498 | 358 / 273 / 267 / 259 | 3 |
| ciprés alto=10 (lapiz 322, llama ~424-508) | 322 / 415 / 508 | 223 | 3 |
| palmera alto=8 (datil 816-896, washingtonia ~462, abanico 270-744) | 292 / 595 / 896 | 583 | 3-4 |
| olivo alto=5 | 612 / 642 / 706 | 353 | 3 |
| encina alto=9 | 730 / 760 / 824 | 416 | 3 |
| plátano alto=14 | 968 / 983 / 998 | 539 | 4 |
| adelfa | 474 / 490 / 492 | 283 | 3 |
| arbusto tam=1.5 | 232 / 316 / 422 | 187 | 3 |
| roca tam=3 | 64 | 34 | 1 |
| jardinera largo=6 | 428 | 248 | 4 |
| OLI_olivo alto=5 (`olivos.py`) | 540 / 570 / 642 | 324 | 3 |
| OLI_matorral | 196 / 250 / 304 | 138 | 2 |
| ITAL_cipres / ITAL_olivo (docstrings) | <= 250 / <= 400 | - | 3 |
| (v1, sin uso) pino / ciprés / palmera | 277 / 154 / 405-445 | - | 2-4 |

La biblioteca exacta de `build_library` (31 piezas, l.255-311) va de 64 (roca) a 968 (plátano) tris;
las 22 variantes "extra" (`VEG_EXTRA`, l.253) son pino_v0..3 (joven 498, parasol 668, carrasco 440,
costero 484), cipres_v0..1 (llama 424, lapiz 322), encina_v0..1 (824), olivo_v0..1 (612, 676) y
arbusto_v0..2 (232-380). Las palmeras_v0..2, adelfas_v0..1 y plátanos están en `lib` pero NO en
`VEG_EXTRA`: las palmeras y adelfas solo entran en la lista "bajos" (cota < 16 m); el plátano no se
planta en ningún sitio (no hay `clone(lib['platano'])` y no existe familia `VEG_platano` en
asentar.json).

## 2. Biblioteca oculta y clonado

- `integrar_escena.py:66-69`: colección `LIB` (`hide_render`/`hide_viewport`); `build_library`
  (l.255-311) construye cada pieza UNA vez con `alto` y `seed` fijos: `palmera` (8 m, seed 0 ->
  datil), `palmera2` (6.5, seed 3 -> datil), `cipres` (10, lapiz), `pino` (12, parasol), `pino2`
  (9, seed 5 -> carrasco), `adelfa` (rosa; l.273-276 le hunde los vértices 0.35 m "para que no
  parezca flotar"), `jardinera`, `roca` (3 m), `roca2` (5 m) y, si el kit es v2 (`hasattr(vk,
  'build_encina')`, l.281), las 22 variantes extra + palmeras_v + adelfas_v + plátanos.
- `clone(root, loc, rot_z, scale, pitch)` (l.90-104): `ob.copy()` por cada objeto de la jerarquía
  -> el objeto nuevo COMPARTE el datablock de malla (instancias de 31 mallas; miles de objetos),
  con `location`, `rotation_euler = (0, pitch, rot_z)` y escala uniforme. Las ID properties
  (`VEG_variante`) se copian con el objeto; el nombre queda `VEG_pino.NNN` salvo que la zona lo
  renombre (`VEG_plazoleta`, `VEG_penon`, `MIRADOR_palmera`, `ITAL_cipres`, `ITAL_bancal`).
- Consecuencia para AC: `04_export/kn5_writer_opt.py` (l.14-35) pasa todo lo que no es físico a
  coordenadas de mundo y lo FUSIONA por material bajo el dummy `DECO` (`DECO_<material>_pN`, trozos
  de <= 65 000 vértices ordenados por curva Z de 25 m), así que en el KN5 ya no existe "un árbol":
  existen 46 mallas `DECO_MAT_VEG_*` y 5 `DECO_MAT_OLI_*`. `DECO_SIN_SOMBRA = ('VEG_', 'OLI_')` y
  `DECO_MAT_SIN_SOMBRA` (l.74-75) ponen `castShadows = 0` a toda la vegetación.

## 3. Dónde y cómo se colocan

### 3.1 Zonas de `integrar_escena.py` que plantan (todas con `safe(...)`, en este orden)

| Zona (líneas) | Regla de colocación | Resultado (logs_final, 12:59) |
|---|---|---|
| `zona_meta` l.437-443 | 10 palmeras lado mar (`side=+1`) a 8-9 m del borde, cada 33 m, nunca a < 30 m de tribunas/pantallas | ~8-10 palmeras |
| `zona_pueblo` l.1594-1598 (legacy, 14 cipreses cada 62 m) | **código muerto**: `safe('zona_pueblo', zona_pueblo_urbanismo)` (l.1687) ejecuta la versión del plan urbano | 0 |
| `urbanismo_escena.py` l.415, 520-523, 582-586 | 2 árboles por plazoleta/fondo de saco (`adelfa, olivo, cipres, adelfa_v0, olivo_v0, palmera2` rotando, o 2 cipreses), nombre `VEG_plazoleta` | 23 plazoletas -> ~42 `VEG_plazoleta` |
| `zona_edicolas` l.1312-1315 | 2 `VEG_plazoleta` (ciprés) flanqueando cada capillita de fondo de saco | 8 plazuelas |
| `zona_tierra` l.1711-1724 | de s 1570 a 2370 cada 52 m un `pino`/`cipres`/`pino2` alternando lados, a 15-27 m del borde y a >= 12 m de CUALQUIER tramo (`_sitio_lejos_pista` l.1700); 10 rocas de cima (l.1752-1756) | 16 árboles, "0 sin sitio" |
| `zona_horquillas` l.2206-2219 | jardineras + adelfas en el interior de las horquillas 43 (3) y 3 (2); nada junto a puentes | <= 5 + 5 |
| `zona_casino` l.2097-2119 | 26 "jardines" (adelfa, palmera, cipres, adelfa, palmera2; cada 3º olivo) en un cuadrado de +-70 m dentro del lazo 31-41, a >= 11 m del eje | 26 |
| `zona_montana` l.2223-2318 | **el bosque** (ver 3.2) | 2826 |
| `zona_rocas_pueblo` (roca_lazo) l.3894-3928 y `zona_casino` (roca_casino) | la vegetación de cada roca la pone su módulo (1.1) | 11 + 420 matas; ~128 |
| `zona_paseo_mirador` l.4090-4103 | `MIRADOR_palmera` cada 20 m por el paseo del mirador | 8 |
| `zona_caminos` -> `_adornos_sendero` l.5232-5320 | 15 `ITAL_cipres` sueltos en los últimos 60 m de cada sendero (cada 7 m, a 4.4 m del eje, ambos lados, si `libre`) + 2-3 `ITAL_bancal` de 14 m con olivos por la curva de nivel (pendiente 0.15-0.85) | CIMA 15 + 2; ERMITA 15 + 3 |

### 3.2 `zona_montana` en detalle (l.2223-2318)

Dos pasadas de "masas" (semilla + 4-8 árboles alrededor):

1. Pasada 1 (l.2236-2270): hasta 480 semillas en puntos uniformes de TODA la rejilla del terreno
   (`T['x0']..x1`, `y0..y1` = 2068 x 2060 m, mar incluido), aceptadas si `3.5 <= z <= 80` y a
   >= 26 m de la pista (la distancia se mide contra 1 de cada 8 muestras, es decir cada 16 m: es
   aproximada). Alrededor, `randint(4, 8)` intentos en un cuadrado de +-26 m: cada árbol necesita
   `3 <= z <= 82`, >= 24 m de la pista, `_libre(x, y)` (l.179: nada a < 3.4 m, rejilla de 4 m) y
   `pendiente_terreno <= 0.62` (l.2266; ~32 grados). Se clona a `z_terreno - 0.15`, rotación 0-2pi,
   **escala uniforme 0.75-1.4** (l.2268-2269).
2. Pasada 2 (l.2275-2317): 420 semillas a 30-230 m de una muestra de la pista elegida de un `pool`
   con peso extra en las curvas 31-39 (x8), 21-30 (x4) y 3-6 (x4); mismos filtros (28/24 m);
   4-7 árboles en +-22 m.

Especie: la semilla fija un `t_base` y cada árbol lo usa con prob. 0.7, si no, uno al azar de
`tipos`. `tipos` (l.2224-2229) = `pino, pino2, cipres, adelfa, roca, roca2` + `VEG_EXTRA` x2 +
`olivo, olivo, matorral, matorral`; si `z < 16`, `bajos` = palmeras, adelfas, olivos, arbustos
(l.2247-2251). Es decir: NO hay máscara de pendiente (salvo el tope 0.62), ni de orientación, ni de
distancia al mar o al pueblo, ni de cota por encima de 16 m: un pino, una adelfa y una roca de 5 m
pueden salir de la misma semilla. Y la cota máxima 80-82 m deja SIN vegetación los 0.52 km2 de
terreno por encima de 80 m (32 % de los 1.64 km2 de tierra; cumbres a 210/185/155 m,
`geometria_3d.json` `cumbres`): la franja plantable es 0.99 km2 -> ~2 850 árboles/km2, uno cada ~19 m
de media, en masas de +-26 m con 4-8 piezas (una pieza por 340-680 m2). A 30-100 m de la cámara
eso se lee como árboles aislados sobre césped, no como un pinar.

### 3.3 Cuántos hay (raíces en la escena, `renders/qa/asentar.json` 13:00, `por_familia`)

| Familia | n | Familia | n |
|---|---|---|---|
| VEG_pino | 576 | VEG_arbusto | 399 |
| VEG_cipres | 292 | OLI_matorral | 161 |
| VEG_plazoleta (cipreses/adelfas/olivos de plazoleta) | 42 | VEG_roca | 124 |
| VEG_encina | 220 | ITAL_cipres (senderos) | 34 |
| VEG_olivo | 292 | ITAL_olivo (bancales) | 10 |
| OLI_olivo | 174 | MIRADOR_palmera | 8 |
| VEG_palmera | 171 | VEG_adelfa | 208 |

Total 2 711 raíces (+ ~128 `VEG_penon_*` hijos de `PENON_cara`, 11 plantas + 420 matas de la roca
del lazo y 66 islas de `MCOCHE_veg`, que no pasan por asentar). Evolución entre pasadas del
pipeline: `bosque: 3086 / 2777 / 2888 / 2826` árboles (logs_r0 / r2 / r3 / final) y `despeje final:
quitados 118 / 138 / 99 / 139 arboles`: el bosque cambia con cada regeneración porque el `rnd`
global (`Random(42)`, l.30) se consume en zonas anteriores que han cambiado.

### 3.4 Lo que llega al KN5 (`04_export/kn5/informe_check_opt.json`, export del 02/10)

- Triángulos: `DECO_MAT_VEG_*` 1 590 278 tris / 920 135 verts en 46 mallas; `DECO_MAT_OLI_*`
  136 740 / 76 665 en 5; `ITAL_cipres/olivo` 11 320; `MCOCHE_veg` 1 484. Total vegetación 1.74 M de
  5.26 M (33 %). Para comparar: la pista (`1ROAD_`) son 35 696 tris y el terreno (`1GRASS_`) 103 040.
- Material (ejemplo `MAT_VEG_pino_a`): `ksPerPixel`, `alphaBlendMode 0 (Opaque)`, `alphaTested 0`,
  `ksAmbient 0.45, ksDiffuse 0.55, ksSpecular 0.15` en ese KN5 (el `color_ac.py` v2 del 04/10 fija
  para la familia `vegetacion` 0.45 / 0.60 / 0.00, `FAMILIAS` l.294 y `_REGLAS` l.317-322);
  textura `flat_MAT_VEG_pino_a.png` de 8x8 px (informe_check.txt l.287-399).
- `lodIn = lodOut = 0` en todas las mallas (sin LOD); las familias pequeñas quedan en UNA malla que
  abarca todo el mapa (p. ej. `DECO_MAT_OLI_hoja_plata_p1`: 13 452 verts, esfera de culling de radio
  1 057 m): AC no puede descartarlas por frustum.
- Lo que NO llega: UV (no hay; `loops_grupo` l.387-408 escribe UV = 0), vertex colors, el ruido de
  `enriquecer_vegetacion` (ver 5.b), las sombras proyectadas (`castShadows = 0`).

## 4. QA que toca a los árboles (orden real: `03_blender/_rev/pipeline_escena.sh` l.17-23)

`construir_pista -> integrar_escena -> revisar_flotantes -> revisar_invasores -> eliminar_sumergidos
-> revisar_coches -> revisar_tunel -> asentar_objetos -> _rev/nada_en_pista.py -> revisar_urbanismo
-> mejorar_materiales -> aplicar_texturas` (los dos últimos no tocan `MAT_VEG_`: `mejorar_materiales`
filtra por `PREFIJOS` de arquitectura, l.22-23, y `aplicar_texturas` no menciona vegetación).

### 4.1 Dentro de `integrar_escena.py` (antes de guardar)

- `_despejar_camino` (l.4284-4318): al tender cada camino borra `VEG_`, `OLI_`... que caigan en su
  cinta. `_limpiar_bajo_roca` (l.1815): fuera lo que quede bajo una roca-pueblo. `zona_tunel`
  (l.2985-3005): fuera `CASAS_/VEG_/OLI_/...` dentro de la huella real del McLaren (BVH), y las
  `VEG_plazoleta` de una losa quitada. `zona_paseo_mirador` (l.4161-4165): fuera la vegetación en la
  huella del palazzo. `roca_lazo._poblar` y `roca_casino` traen sus propias comprobaciones (copa
  dentro de casa, nada en el espolón ni a < 8 m de la pista, `D_VEG_PISTA` l.2497).
- `despeje_final` (l.6537-6667), con `DESPEJE_ARBOL = ('VEG_', 'OLI_', 'ITAL_cipres', 'ITAL_olivo')`
  (l.5949) y `DESPEJE_PROP` (incluye `VEG_roca`): un árbol se quita si su tronco está dentro de un
  edificio (margen 1 m) o su COPA (8 puntos a 0.7 del radio de su caja, tope 9 m) entra en uno
  (margen 0.3), si está a < 0.8 m del eje de una calle/camino del plan, dentro de un polígono de
  plaza/plazoleta (`PLAZAS_POLY`) o a < 3.5 m de una fuente; `VEG_plazoleta` queda exenta de la regla
  de plaza; `VEG_roca` se trata como prop (eje a < 0.5 + r, plazas, fuentes). Resultado final:
  `quitados 139 arboles y 29 props`.

### 4.2 Inspectores sueltos (cada uno abre y GUARDA `porto_corsa.blend`)

| Script | Qué hace con la vegetación | Última pasada |
|---|---|---|
| `revisar_flotantes.py` (163 l.) | raíces fuera de `EXENTOS` (l.43-48: `VEG_penon`, `ITAL`, `MIRADOR`... exentos): `z_terreno(x, y)` del PIVOTE con la triangulación del render (l.25-40, diagonal a -> a+nx+1); si `zmin > terr + 1.2` baja a `terr - 0.2`; si `zmax < terr - 0.5` sube | 18 corregidos: 1 pino flotando 1.7 m, 1 ciprés 1.4 m, 14 enterrados (casi todos en (-280..-230, 210..235): la explanada del hotel/paddock los había tapado) |
| `revisar_invasores.py` (164 l.) | `REGLAS` l.72: `VEG_`/`OLI_` no pueden estar a menos de `w/2 + 2.0 + min(radio, 8)` del eje de la pista ni a < 5.5 (+radio) del pit lane -> se borran; además asienta vegetación con `zmin > terr + 0.45` (l.147-158). `VEG_penon`/`PENON_` excluidos (l.97) | 2 borrados, 11 asentados |
| `eliminar_sumergidos.py` (49 l.) | `VEG_` (no `VEG_penon`, ni nombres con `roca`/`acantilado`) con `zmax < 0.9` o `zmin < -1.0` -> fuera | 0 |
| `asentar_objetos.py` (2221 l.) | ver 4.3 | candidatos 3096, movidos 3036 |
| `_rev/nada_en_pista.py` (115 l.) | para CADA malla visible (hijos incluidos: cipreses de filas, olivos de bancales, matas de rocas) cuenta vértices sobre la calzada (`d < w/2 + 0.3`, `-0.3 < z - z_calzada < 5.5`) -> `renders/qa/nada_en_pista.json`; solo informa | 11 fallos, ninguno de vegetación |
| `revisar_urbanismo.py` | fallos `cipres_flotando/enterrado`, `bancal_mal_asentado`, avisos `arbol_quitado_por_asentar`, `arbol_sacado_de_muro` (RONDA15 l.248, 406) | - |

### 4.3 `asentar_objetos.py`: lo que decide sobre un árbol (docstring l.1-90)

- Soporte: UN BVH con TERRENO + rocas (PPUEBLO_/PENON_/TUNEL_acantilado) + caminos/calles/losas del
  plan + arcenes/aceras + pit; triangulado como el render (`loop_triangles`). `CAMINO_terraplen` y
  muros NO son apoyo de árboles (`NO_APOYO_ARBOL`, `OBST_PREF` l.174).
- `ARBOL_PREF = ('VEG_', 'OLI_', 'ITAL_cipres', 'ITAL_olivo')` (l.162); `ARBOL_FIJO = ('VEG_roca',
  'VEG_plazoleta', 'VEG_jardinera')` (l.1227) se asientan pero no se mueven ni quitan.
- `apoyo_arbol` (l.1266-1298): 5 rayos (centro + anillo de `R_ANILLO = 0.6` m, l.164) sobre la
  MISMA malla; base = mínimo del anillo + `HUNDIMIENTO` (l.124-126: `VEG_` -0.15, `VEG_arbusto`
  -0.10, `OLI_matorral` -0.10, `VEG_roca` -0.30) para que el tronco no enseñe hueco ladera abajo.
  Si el desnivel del anillo > `DESNIVEL_MOVER = 0.8` se prueba `PASO_LADERA = 2.0` m arriba/abajo;
  si sigue > `DESNIVEL_MAX = 1.6` se quita (l.165-167).
- Tronco en/bajo una losa del plan o cinta de camino (`tronco_en_calzada` l.1314): apartar 2-4 m
  (`DIST_HUIDA` l.1242) o quitar. Copa (16 puntos) sobre una calzada a < 4.5 m (2.2 en senderos):
  apartar o quitar (`copa_calzada`). Camino a < 1.5 m del tronco: apartar (`junto_a_camino`).
  Tronco dentro de muro/edificio (rayos en el tronco y a +-0.3 m): sacar 1.5/3 m (`SEPARAR_M`
  l.182) o quitar (`dentro_de_muro`). Hijos `ITAL_cipres`/`ITAL_olivo` de hileras/bancales: uno a
  uno (l.1749-1770). Autocomprobación: rayo hacia arriba desde el suelo del centro del tronco.
- Última pasada (asentar.json 13:00): `flotaban_mas_0_6: 28`, `enterrados_mas_0_6: 57`,
  `arboles_desplazados_ladera: 53`, `arboles_quitados: 3` (VEG_cipres.011 "ladera imposible: 2.89 m
  de desnivel en 1.2 m de tronco", VEG_olivo.037 tronco bajo CAMINO_calle.006, VEG_encina.140 copa a
  0.86 m sobre CAMINO_rampa), `dentro_de_muro: 4 (movidos 4)`, `copa_calzada: 4`.

### 4.4 Observaciones sobre esta cadena

1. Hay TRES nociones distintas de "suelo": `integrar.z_terreno` (bilineal, l.145-155, es la que
   planta a `z - 0.15`), `revisar_*.z_terreno` (triángulos del render) y el BVH de asentar (malla
   real + losas). Por eso asentar "mueve" 3036 de 3096 raíces (casi todas unos cm) y por eso
   `revisar_flotantes` y `revisar_invasores` siguen encontrando 1-2 m en laderas: asentar va después
   y los arregla, pero cada script guarda el .blend (3 escrituras de 42 MB).
2. Los inspectores miran el PIVOTE (x, y) del objeto, no la copa: un pino parasol de 12 m con copa
   de 10 m de diámetro puede tener el tronco "legal" a 2 m del borde y la copa colgando sobre la
   pista. `nada_en_pista.py` sí mira vértices, pero no borra. Hoy no hay vegetación en los 11
   fallos.
3. Los árboles de las rocas (`VEG_penon_*`, `PENON_`) y `MCOCHE_veg` están exentos de todo salvo
   de las comprobaciones internas de sus módulos: las "matas pegadas en la pared vertical" que cita
   el director (capturas 11, 15, 20, 38) y la "mata en lunares" de la roca del lazo (34) vienen de
   `roca_casino.vegetacion` (matas en cornisas) y de las 420 matas de `roca_lazo` (RONDA15 l.382
   dice que el filtro del espolón quitó 14 enterradas, pero no hay filtro de normal vertical).
4. El bosque y los inspectores no comparten un "plan": `zona_montana` planta a ciegas y luego
   `despeje_final` + asentar quitan ~145 árboles por pasada. Para el plan del usuario (máscaras y
   masas) lo lógico es que el plan se calcule ANTES (en Python del sistema, como `urbanismo.py`) y
   que el integrador solo lo ejecute; así el mismo plan sirve para `trees.txt`.

## 5. Por qué parecen piruletas

Capturas miradas: 01, 07, 10, 21, 51 (y la preview `assets/previews/veg_v2_familias.png`). El
director las describe como "prado vacío con una palmera suelta" (10), "matas en lunares regulares"
(34), "un árbol y una roca apoyados en la cara" (51), "macizo verde uniforme" (01, 21).

a. **Geometría de bola sobre palo.** La copa es un sólido de revolución (`_lathe`) más 5-8 esferas
   de 7-10 segmentos con `use_smooth`: silueta convexa, cerrada, sin huecos ni ramas que asomen. El
   tronco es un tubo fino (radio 0.03 x alto, l.768: 36 cm para 12 m) que entra por el centro. Las
   variantes v2 (lóbulos desplazados, copa en bandera, carrasco apilado) rompen la silueta a < 30 m;
   a 50-150 m, que es la distancia a la que se ve el bosque desde el coche, los lóbulos se funden en
   una bola. El pino parasol es literalmente un disco plano sobre un palo (`copa` l.780-782).
b. **Un solo color por material, sin textura.** Cada lóbulo es `pino_a` o `pino_a_luz`: dos verdes
   planos alternados (l.761-764), roughness 0.8, especular 0 -> plastilina. `enriquecer_vegetacion`
   (l.6498-6530) añade en Blender un ruido por coordenadas de objeto (escala 0.08 = ~12 m) que varía
   el tono entre instancias... pero `kn5_writer.analizar_material` (l.185-187) toma `diffuse_color`
   cuando `Base Color` está enlazado, y `construir_textura` (l.217-239) escribe un PNG plano de 8x8:
   **en AC todos los pinos `pino_a` son exactamente del mismo verde** (57 materiales "variados" que no
   se exportan). No hay AO, ni normal, ni degradado copa-abajo oscuro, ni translucidez.
c. **Sin sombra en AC.** `kn5_writer_opt` fuerza `castShadows = 0` en `VEG_`/`OLI_` y en todo lo que
   lleve `MAT_VEG_`/`MAT_OLI_` (l.33-35, 74-75). Las capturas de Blender SÍ muestran sombras
   (Cycles), así que en el juego el bosque se verá peor que en las capturas: árboles sin sombra sobre
   hierba plana parecen pegatinas.
d. **Reparto sin hábitat ni masa.** Semillas uniformes en todo el mapa, especie por `semillas %
   len(tipos)` (pino, pino2, ciprés, adelfa, roca, roca2, variantes, olivo, matorral), 30 % de
   mezcla aleatoria dentro de cada masa, escala uniforme 0.75-1.4 sin relación con la especie ni con
   la cota: cipreses de 14 m sueltos en mitad de una ladera, adelfas junto a pinos, rocas de 5 m en
   el bosque. Las masas de 4-8 piezas en +-26 m con `_libre` 3.4 m nunca forman un dosel continuo.
   Nada por encima de 80 m (32 % del terreno), nada en los bancales, nada "agrupado en masas" como
   pide el usuario (la palabra "masas" del código es una nube de 4-8 puntos).
e. **El suelo no acompaña.** Debajo hay la misma textura de césped uniforme que en los jardines; no
   hay sotobosque (399 arbustos + 161 matorrales para 1 km2), ni pinaza, ni oscurecimiento del
   terreno bajo las copas, ni rocas integradas: el árbol "está puesto encima", no "sale del monte".
f. **Escala tímida.** Pinos de 8-14 m (x 0.75-1.4) frente a casas de 4-6 plantas y un casino de
   30 m; en la película los pinos de Porto Corsa son parasoles enormes y las palmeras altísimas. El
   usuario pide formas exageradas (monumentos +30-50 %): a la vegetación le pasa lo mismo.
g. **Siluetas repetidas.** 31 mallas para 2 700 objetos: la variación es solo rotación y escala; el
   ojo reconoce la misma copa cada pocos metros.

## 6. Qué haría falta para árboles con mejor silueta visibles en AC "a pelo" (sin CSP)

Tres opciones, de más a menos impacto por triángulo:

### 6.A Planos cruzados con alfa (lo que hacen las pistas de Kunos y casi todos los mods)

- Modelo: 2-3 quads verticales cruzados a 60-90 grados (+ opcional un quad horizontal para las
  vistas aéreas 01/21) con un atlas RGBA de la especie; 8-24 tris/árbol; doble cara DUPLICANDO las
  caras con winding invertido (como `vegetacion_kit_v2._doble` l.371), porque AC hace backface
  culling y el KN5 no tiene flag de dos caras. 2 826 árboles -> ~50 k tris (hoy 1.74 M, x35 menos),
  lo que deja presupuesto para 3-5 veces más densidad y para sotobosque.
- Atlas: sin descargar nada, la opción coherente con el estilo es RENDERIZAR IMPOSTORES de las
  propias piezas v2 (o de un kit v3 más exagerado) en Blender: cámara ortográfica, fondo
  transparente, 2-4 vistas por especie (frontal, 90 grados, 3/4 desde arriba), 512 x 1024 por vista,
  con AO horneado y luz suave; así el "look Pixar" de color plano se conserva pero la silueta ya es
  la de un árbol (hojas, huecos, ramas). La alternativa son atlas CC0 (Kenney, OpenGameArt;
  Poly Haven/ambientCG no tienen árboles): solo listar, no descargar.
- Cambios en 03_blender:
  1. `assets/vegetacion_kit_v3.py` (misma API: `build_pino(parent, alto, seed, variante)` ->
     objeto `VEG_pino`), que genere los quads con UV (hoy `_MB.build` no crea `uv_layers`, l.204-216)
     y un material `MAT_VEGC_<especie>` con nodo `ShaderNodeTexImage` (imagen RGBA) enlazado a
     `Base Color` y su alfa a `Alpha`. Mantener `ob["VEG_variante"]`, el pivote en la base y los
     nombres `VEG_*` para que `integrar`, `asentar` y `despeje_final` sigan funcionando sin cambios.
  2. El render de impostores: script `assets/render_impostores_veg.py` (bpy.ops.render está
     permitido) que escriba `assets/texturas/veg_<especie>.png` a partir del kit v2/v3.
  3. `integrar_escena.build_library` (l.255-311): un solo punto de cambio para pasar a v3 (o
     `assets/v2_aprobados.txt` -> `v3`, si `load_mod` aprende a leer sufijos).
- Cambios en 04_export (DEPENDENCIA: cerrado por el equipo del zip v1.1; preparar aquí, aplicar
  cuando abran):
  1. `kn5_writer.py` l.278-283 y `kn5_writer_opt.py` (l.8-10): hoy shader fijo `'ksPerPixel'`,
     `alphaBlendMode = 1` solo si `alpha < 0.999`, `alphaTested = 0`, `ksAlphaRef = 0`. Hace falta
     escribir, para los materiales marcados (p. ej. ID property `m['ac_shader'] = 'ksPerPixelAT'` o
     prefijo `MAT_VEGC_`): shader `ksPerPixelAT` (o `ksTree`, el de los árboles de Kunos, que suaviza
     las normales de los planos para que no se vea el plano), `alphaTested = 1`, `ksAlphaRef ~0.5`,
     `alphaBlendMode = 0` (nada de alpha blend: sin orden de dibujado).
  2. `construir_textura` (l.217-239) descarta el alfa de la imagen (solo añade un alfa uniforme):
     tiene que conservar el canal A del PNG y, para evitar halos en los mipmaps, dilatar el color
     bajo el alfa (bleed) antes de embeber.
  3. `DECO_SIN_SOMBRA`: con alfa test los árboles pueden volver a `castShadows = 1` (la sombra de un
     plano con alfa es la silueta de las hojas). **A verificar en AC**: que el sombreado de AC
     respete el alfa en `ksPerPixelAT`/`ksTree` (lo hace en las pistas de Kunos).
  4. Fusión: con 8 verts/árbol un trozo de 65 000 verts = 8 000 árboles = todo el mapa; conviene
     trocear por área (celda Morton de 25 m -> grupos de ~150-250 m) para que el frustum culling de
     AC funcione, y dejar las mallas de árboles con nombre propio (`DECO_MAT_VEGC_*`) para poder
     ocultarlas desde CSP (7.5).
  5. LOD sin CSP: el formato KN5 tiene `lodIn`/`lodOut` por malla (el escritor pone 0.0): se podría
     exportar un billboard de 2 tris con `lodIn = 150` y las cruces con `lodOut = 150`. A verificar
     que AC los aplica en mallas de pista (ksEditor lo expone por objeto).
- Riesgos: halos blancos/negros en los bordes (bleed + `ksAlphaRef`), "cartón" visible al pasar al
  lado a 1.4 m de altura (cámaras 49-54: mezclar con 6.B en los primeros 20 m), aliasing de hojas
  finas a distancia (atlas con hojas gordas estilo Cars, no agujas), el tamaño del KN5 crece con los
  atlas (hoy 12.5 MB de texturas, ninguna > 1024 px por `TEX_MAX`, `kn5_writer_opt.py:64`).

### 6.B Mallas opacas pero con silueta de verdad (sin cambiar shader ni escritor)

- Copas como 3-6 "nubes" cóncavas (casquetes aplastados con borde ondulado, como los pinos de la
  película: copa plana, gruesa, de bordes redondeados), ramas de 2-4 segmentos que SALEN de la copa
  y se ven, tronco el doble de grueso, 2-3 huecos entre masas para que pase el cielo; variación de
  altura por especie (pinos 14-22 m, palmeras 10-18) y escala NO uniforme (x/y vs z).
- Coste: sigue en 400-900 tris/árbol -> 2 700 árboles = 1.5-2.5 M tris; no permite densificar.
  Sigue sin textura ni sombra en AC (salvo que se active `castShadows` = más coste).
- Útil solo para los "árboles héroe" de los primeros 20-30 m de la pista, plazas y casino, donde la
  tarjeta de 6.A cantaría.

### 6.C Híbrido (recomendado para el look Pixar)

Copa opaca sencilla (2-3 casquetes, 60-120 tris) + 4-8 "hojas" en planos con alfa pegados a la
superficie de la copa (cada plano un manojo de hojas del atlas) + tronco 7 lados. Es lo que hacen los
juegos de estilo cartoon (Mario Kart, el propio videojuego de Cars 2): silueta rota, volumen desde
cualquier ángulo, 150-250 tris. Exige los mismos cambios de exportación que 6.A.

En los tres casos: oscurecer el terreno bajo las masas (vía la máscara RGBA del
`ksMultilayer_fresnel_nm4` que pide el usuario en su punto 3, o con una capa "sombra de bosque" en
`aplicar_texturas`) y meter sotobosque (matorral/arbusto en tarjeta) es lo que convierte "árboles
puestos" en "monte".

## 7. Qué haría falta para `extension/trees/trees.txt` (CSP TreeFX)

Fuente: wiki de CSP "Tracks – Trees" y "General – Model replacements" (consultadas el 04/10 vía
WebFetch; no se ha descargado nada). TreeFX es "New CSP 0.1.79 feature": el amigo necesita CSP
>= 0.1.79 y, si no lo tiene, AC ignora `extension/` entera (como ya avisa `ext_config.ini` l.2).

### 7.1 Formato de `trees.txt` (literal de la wiki)

```
tree: my_tree.bin; 208.4, -1, -53
configure: size variance = 0.8, 1.2
configure: angle variance = 0, 360
tree: tree0.bin; pos=-83.3, -0.99, -74.14; angle = 180; size = 1; width = 1; color = 2, 2, 2
```

- `tree: <modelo.bin>; x, y, z` o `pos=x, y, z` + opcionales `angle` (grados, giro vertical),
  `size` (escala), `width` (multiplicador de anchura), `color = r, g, b` (multiplicador).
- `configure:` cambia valores globales hasta la siguiente línea `configure:`: `size variance`,
  `width variance`, `angle variance`, `color variance`, `brightness variance`, `fake shadow`
  (opacidad de la sombra falsa), `seed`. "All random values are predetermined with a fixed seed".
- Ejes: "coordinates in track space" = los del KN5, es decir **AC(x, y, z) = (x_blender, z_blender,
  -y_blender)**, exactamente la conversión de `04_export/kn5_writer.py:11,65` (`C_AXIS`) y
  `kn5_writer_opt.a_ejes_kn5` (l.411). La `y` es la altura; la `z` de AC es `-y` de Blender. Con
  `SURFACE_MATERIALS` / `SURFACE_MESHES` en `[TREES]` CSP "snapea" los árboles a la superficie, así
  que un error de +-0.5 m en `y` se corrige solo si se declara `MAT_terreno` (o `1GRASS_terreno`).
- En `extension/ext_config.ini`: `[TREES]` con `LIST_0 = trees/trees.txt`, `SURFACE_MATERIALS =
  ...` (opcional `COMPILED_LIST = compiled_trees.bin`, `SEASON_AUTUMN_0`/`SEASON_WINTER_0`).
  **Dependencia**: `ext_config.ini` lo GENERA `04_export/color_ac.py` (cabecera l.1-5) y
  `empaquetar.py` lo copia tal cual: la sección `[TREES]` hay que añadirla al generador (04_export,
  cerrado ahora) o editarla a mano después de cada regeneración.

### 7.2 Modelos `.bin`

- Por especie un FBX con 3 LOD ("10K triangles for LOD A, 6K for LOD B, 3K for LOD C" es el tope,
  no el mínimo; para el estilo low-poly valen 1.5k/600/150), "single mesh per LOD (use
  multi-material if you need one texture for trunk and another for branches)", "pivot of each model
  should be right at the middle of its base", materiales con difusa (alfa = transparencia) + normal
  (alfa = AO local).
- Conversión: Content Manager > Content/Tools/Creator tools > tree converter (FBX -> .bin; "tracks
  changes in FBX file while running"). CM no está en este PC: el FBX se prepara aquí (export FBX de
  Blender es `bpy.ops.export_scene.fbx`: es una excepción a "sin bpy.ops salvo render" que habrá que
  autorizar, o usar el camino `PORTO_FBX=1` que ya existe en `exportar_ac.py:11`) y el .bin se hace
  en el PC del amigo. Los .bin van en `extension/trees/`.
- Especies que pide el usuario: pino piñonero, ciprés, palmera, olivo, encina, arbustos con flor.
  Las piezas v2 ya cubren las 6 (más carrasco/costero/joven, washingtonia/palmito, romero/lavanda/
  retama): el FBX puede salir del kit actual (como LOD C) + una versión más detallada (LOD A/B) del
  kit v3 de 6.C, con UV y atlas RGBA + normal (la normal se puede hornear en Blender).

### 7.3 Script generador

Propuesta: `03_blender/exportar_trees_txt.py` (Python del sistema, sin Blender) que lea un
`03_blender/vegetacion_plan.json` y escriba `04_export/extension/trees/trees.txt`:

```
configure: seed = 42
configure: size variance = 0.85, 1.25
configure: width variance = 0.9, 1.1
configure: angle variance = 0, 360
configure: color variance = ...   (+-10 % para romper la uniformidad)
tree: pino_pinonero.bin; pos=<x>, <z>, <-y>; angle=<grados>; size=<alto/alto_modelo>; width=<w>
```

Dos fuentes posibles para el plan:

1. **Rápida (lo que ya hay)**: leer `_rev/escena_rev.blend` (o `porto_corsa.blend` tras asentar) y
   volcar cada raíz `VEG_*`, `OLI_*`, `ITAL_cipres`, `ITAL_olivo`, `MIRADOR_palmera`, `VEG_penon_*`
   (estas como hijos de `PENON_cara`: usar `matrix_world`): posición = `matrix_world.translation`,
   `angle = degrees(rotation_euler.z)`, `size = scale.z x alto_pieza/alto_modelo`, especie por
   nombre + `ob["VEG_variante"]`. Es un script de lectura de ~80 líneas y sirve para la prueba de 3
   árboles. Pero hereda el reparto malo de `zona_montana`.
2. **La del plan del usuario**: un `vegetacion.py` (Python del sistema, como `urbanismo.py`) que
   calcule el plan por máscaras sobre la rejilla `terreno` de `geometria_3d.json` (cell 4 m,
   517 x 515, `z`, `mar`, `mascara_roca`, `cumbres`) + `urbanismo.json` (sectores, solares, calles)
   + `muestras` (distancia a pista): pendiente (gradiente de `z`), cota, distancia al mar (`mar`
   dilatada), distancia al pueblo (polígonos de solares + 40 m), distancia a caminos/pista;
   zonas -> especies y densidades (p. ej. pinar en crestas y collados 60-180 m, encinar en
   umbrías > 25 grados, olivar en bancales 20-90 m junto al pueblo, cipreses en caminos/ermita,
   palmeras < 20 m junto al mar/paseo/casino, matorral en todo lo que pase de 30 grados, roca
   desnuda donde `mascara_roca > 0.6`); masas por semillas + relleno de disco de Poisson con radio
   por especie (3-5 m en pinar, 7-9 m en olivar) y huecos (claros) explícitos; variación de tamaño,
   ángulo y color por árbol. Ese MISMO plan lo ejecuta `integrar_escena` (clones de las mallas, para
   AC sin CSP) y lo vuelca `exportar_trees_txt.py` (para CSP): un árbol = una línea = una malla.

### 7.4 Validar primero con 3 árboles (como pide el usuario)

- `trees.txt` de prueba con 3 entradas en puntos reconocibles: meta (-176, 112, z 3), casino
  (560, -560) y cima del lazo de tierra (-96, 702, z ~117), convertidos a `(x, z, -y)`; un solo
  `.bin`. Comprobación local posible sin AC: comparar las coordenadas con los `nodos_AC`
  (`pos_kn5`) del `resumen_writer_opt.json` (misma transformación: si `AC_START_0` sale bien, los
  árboles también). En el PC del amigo: ¿aparecen en el sitio, con la base en el suelo, mirando donde
  toca (`angle`), a la escala correcta? Si salen en espejo respecto al trazado, el signo de `z` es
  el culpable.

### 7.5 Que las mallas no se dupliquen con TreeFX

- Wiki "General – Model replacements": `[MODEL_REPLACEMENT_0]` con `FILE = porto_corsa.kn5` y
  `HIDE = name1, name2` ("meshes or nodes to hide (no protected meshes)"; `?` es comodín, p. ej.
  `RIM_?`; no vale para nombres con `WALL`, que empiecen por `AC_` o por dígito). Funciona en pistas.
  Con la fusión actual bastaría `HIDE = DECO_MAT_VEG_?, DECO_MAT_OLI_?` (y `DECO_MAT_ITAL_cipres?`,
  `..._olivo?`, `MCOCHE_veg?` si también se sustituyen). Ojo: las palmeras de `HOTEL_`/`PUERTO_` usan
  `MAT_VEG_*` (kn5_writer_opt l.75) y se ocultarían también: o se incluyen en el plan o se les cambia
  el material.
- Sin CSP: `extension/` se ignora, quedan las mallas. Con CSP viejo (< 0.1.79): `[TREES]` se ignora
  pero `HIDE` quizá no -> riesgo de pista SIN árboles; mitigación: comprobar en el PC del amigo y, si
  hace falta, condicionar con `[BASIC] IGNORE_OTHER_CONFIGS` o quitar `HIDE` hasta confirmar.

## 8. Qué haría falta para el plan del usuario (punto 4 de PLAN_USUARIO.md)

Cambios concretos, en el orden en que se pueden hacer sin pisar a nadie:

1. **Plan de vegetación por máscaras** (`03_blender/vegetacion.py`, nuevo, Python del sistema; lee
   `geometria_3d.json` + `urbanismo.json`, escribe `vegetacion_plan.json` + `renders/qa/
   vegetacion_mapa.png` con las zonas y los puntos). Sustituye a `zona_montana` (l.2223-2318),
   `zona_tierra` l.1711-1724 y `zona_casino` l.2097-2119 (jardines), que pasarían a leer el plan. Es
   independiente del formato de los árboles y se puede hacer YA. Debe respetar lo que hoy protegen los
   inspectores (pista + 12 m, calles, plazas, edificios, caminos, bancales, rocas) para que
   `despeje_final`/asentar dejen de quitar 140 árboles por pasada.
2. **Quitar las piruletas**: nuevo `assets/vegetacion_kit_v3.py` (6.C: casquetes + hojas en planos
   con alfa, UV, atlas renderizado desde Blender) + `assets/test_vegetacion_kit_v3.py` con previews y
   presupuesto (<= 250 tris/árbol, <= 80/arbusto) + `assets/render_impostores_veg.py`. Cambio de
   `build_library` (l.255-311) a v3 por `v2_aprobados.txt`/`load_mod`. Riesgo: hasta que 04_export
   admita alfa test, en AC las "hojas" saldrían opacas (cuadrados verdes): por eso el v3 debe tener un
   modo `sin_alfa=True` (solo casquetes) que ya mejora la silueta y no depende de nadie.
3. **Exportador** (DEPENDENCIA 04_export, cuando cierren el zip v1.1): `ksPerPixelAT`/`ksTree` +
   `alphaTested` + `ksAlphaRef` + PNG RGBA con bleed + `castShadows = 1` para `VEG_` + troceado por
   área + nombres `DECO_MAT_VEGC_*`. Lista cerrada de cambios en 6.A. Preparar aquí el material y las
   ID properties para que el día que abran sea un cambio de 40 líneas en `kn5_writer_opt.py`.
4. **TreeFX (extra para CSP)**: `exportar_trees_txt.py` (7.3) desde `vegetacion_plan.json`; FBX por
   especie (LOD A = v3 detallado, LOD B = v3, LOD C = v2 o billboard) con `bpy.ops.export_scene.fbx`
   (autorizar la excepción); `.bin` con el tree converter de CM en el PC del amigo; `[TREES]` +
   `[MODEL_REPLACEMENT_0] HIDE` en `ext_config.ini` (generador en `color_ac.py`, 04_export). Prueba
   de 3 árboles antes de nada (7.4).
5. **Capturas antes/después**: las mismas cámaras de `renderizar_capturas.py` (piloto 49-54 =
   s 300/800/1700/2900/3400/4150 a 1.4 m, l.282-287; aéreas 01, 07, 21; casino 10) y, para juzgar lo
   que verá el amigo, una variante de render SIN sombras de vegetación (lo que hace `castShadows = 0`)
   hasta que el exportador las active.
6. **Grass FX solo en céspedes** (fuera de mi bloque): afecta a qué material lleva el césped de
   jardines/rotondas vs. el terreno (`MAT_terreno` hoy único); conviene decidirlo junto con la máscara
   RGBA del punto 3 del usuario.

Riesgos generales: (a) tris: hoy la vegetación es el 33 % del KN5 y ya no hay LOD; densificar x3 con
mallas v2 reventaría el presupuesto (5.2 M tris, 355 MB); con tarjetas/híbrido cabe. (b) Sin CSP no
hay viento ni TreeFX: lo esencial (silueta, densidad, color, sombra) tiene que vivir en el KN5.
(c) No hay AC aquí: el alfa test, las sombras con alfa y los LOD solo se confirman en el PC del
amigo; planificar una entrega intermedia "3 árboles de prueba" en el zip. (d) La aleatoriedad global
(`rnd = Random(42)`, l.30) hace que el bosque cambie entera cada vez que otra zona consume números:
el plan en JSON lo deja fijo y revisable. (e) `revisar_flotantes`/`revisar_invasores`/asentar
siguen siendo necesarios con cualquier malla (miran el pivote), pero con tarjetas la "copa sobre la
pista" (`copa_calzada`) necesita medir la anchura real de la tarjeta.
