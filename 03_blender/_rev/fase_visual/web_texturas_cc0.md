# Texturas CC0 para la fase visual de Porto Corsa (Poly Haven + ambientCG)

Fecha: 04/10/2026. Investigacion solo web (sin descargar nada). Autor: agente investigador de la fase visual.
Encargo: `03_blender/_rev/fase_visual/PLAN_USUARIO.md`, punto 3 ("4 texturas de detalle CC0 de Poly Haven o
ambientCG, recoloreadas a la paleta") y puntos 2, 5 y 6 (roca integrada, pueblo, costa).

## 0. Resumen en diez lineas

- Las dos bibliotecas son CC0 1.0 (dominio publico efectivo, sin atribucion obligatoria). Verificado en
  `polyhaven.com/license` y `docs.ambientcg.com/license/` (citas en la seccion 2).
- Resolucion recomendada: **1K en JPG** para todo lo que vaya al kn5. Motivo verificado en el proyecto:
  `04_export/kn5_writer_opt.py` fija `TEX_MAX = 1024` (ninguna textura embebida supera 1024 px) y
  `TEX_SIZE = 512` (las tintadas se generan a 512 desde fuentes de 1024). Un 2K solo serviria para los
  renders de Blender y se reduciria igualmente al exportar.
- Lista final: **13 texturas (11 de Poly Haven + 2 de ambientCG)**, mas 1 opcional. Descarga total estimada:
  **~49 MB en 1K-JPG** (~186 MB en 2K-JPG). Si se descarga solo Diffuse+Normal+Roughness de Poly Haven y los
  dos zips de ambientCG: ~40 MB en 1K.
- Las cuatro capas del terreno (ksMultilayer_fresnel_nm4, mascara RGBA): `rock_06` (caliza calida estratificada),
  `withered_grass` (hierba seca), `Ground105` (tierra beige erosionada) y `aerial_grass_rock` (base para
  matorral oliva, recolorear).
- Pueblo: `white_stucco` (estuco, tintar a la paleta Riviera), `clay_roof_tiles_03` (teja de barro),
  `PavingStones150` (adoquin beige/gris en abanico, 0,9 m), `rock_wall_10` (piedra seca de bancal).
- Pista: `asphalt_track` (asfalto fino de circuito, 2 m) y `gravel_road` (pista de tierra/grava, 2 m).
- Costa: `rocks_ground_06` (escollera/grava costera, 3 m), `aerial_sand` (fondo marino, 15 m) y `rock_face_03`
  (segunda roca para afloramientos). No existe en ninguna de las dos bibliotecas una textura de agua (normal de
  olas): hay que hacerla procedural en Blender o dejarla al shader de agua de AC.
- Ninguna de las dos bibliotecas tiene foto cenital de "matorral mediterraneo": el matorral se resuelve con
  geometria (TreeFX/arbustos) sobre una capa oliva oscura tintada.
- Todo lo que aparece en las tablas con tamano en bytes esta leido de la API oficial de cada sitio
  (`api.polyhaven.com/files/<id>` y `ambientcg.com/api/v2/full_json`). Lo no verificado esta marcado en la seccion 7.

## 1. Contexto del proyecto que condiciona la eleccion (hechos leidos en el repo)

- `04_export/kn5_writer_opt.py`: `TEX_SIZE = 512  # lado de las texturas tintadas embebidas (las fuentes son de 1024)`
  y `TEX_MAX = 1024  # ninguna textura embebida supera este lado`. El escritor codifica las texturas como PNG de
  8 bits (`png_bytes`) y construye una cadena `TEX_imagen -> TEX_ganancia -> TEX_multiplicar -> Base Color`
  (solo difuso). Los mapas normal/roughness/AO no se exportan hoy: para usarlos en AC hara falta trabajo en el
  escritor (otro equipo esta cerrando el zip v1.1; no se toca 04_export en esta fase).
- `04_export/kn5/informe_check_opt.json`: `n_texturas: 438`, `bytes_texturas: 12543428` (12,5 MB), fichero kn5 de
  355 MB. El zip `porto_corsa_mod.zip` pesa 164 MB. Anadir 13 texturas 1K no cambia el orden de magnitud.
- `03_blender/aplicar_texturas.py`: usa ficheros planos `asfalto_d.png` (escala 1/8), `tierra_d.png` (1/6),
  `teja_d.png` (1/2), `piedra_d.png` (1/3), `estuco_d.png` (1/4), `hierba_d.png` (1/7), `agua_h.png` (1/40).
  Las texturas nuevas pueden entrar por el mismo esquema `<nombre>_d.png` con la escala ajustada a las
  dimensiones fisicas reales de cada textura (tabla de la seccion 4).
- `RONDA15_PLAN.md`, T8: "terreno multicapa por mascara (hierba viva/seca/tierra/roca), roca caliza triplanar
  horneada, agua con degradado, AO horneado".
- Capturas miradas: `51_piloto_s1700.png` (tierra beige lisa, hierba verde cesped, desmonte gris con rayas),
  `13_puente_alto.png` (roca del lazo gris lisa, acantilado beige con curvas de nivel), `06_pueblo_calle.png`
  (fachadas planas, tejas rojas planas, muros de sillares, cesped uniforme). Confirman el diagnostico del director:
  superficies planas y paleta verde-cesped/gris.

## 2. Licencias (hechos verificados en la fuente)

- Poly Haven (`https://polyhaven.com/license`): CC0. Citas: "Anyone can then use the work in any way and for any
  purpose, including commercial purposes" y "You do not need to give credit or attribution when using them
  (although it is appreciated)".
- ambientCG (`https://docs.ambientcg.com/license/`): Creative Commons CC0 1.0 Universal. Citas: "You can copy,
  modify, distribute and perform the assets, even for commercial purposes, all without asking permission" y
  "You don't need to give credit but I would of course appreciate it, if you did it anyways". Formato de
  atribucion sugerido por el sitio: `Created using <asset name> from ambientCG.com, licensed under the Creative
  Commons CC0 1.0 Universal License.`
- Consecuencia para el repo publico `jerryfloresarce/cars2`: se pueden redistribuir las texturas (tintadas o no)
  dentro del kn5 y del zip sin fichero de licencia obligatorio. Recomendable igualmente un `CREDITS.txt` con la
  lista de ids (es gratis y evita preguntas).

## 3. Metodo y fuentes consultadas

- Poly Haven: API publica `https://api.polyhaven.com/assets?t=textures&c=<categoria>` (listas por categoria:
  rock, asphalt, plaster, cobblestone, sandstone, sand, gravel, roofing, terrain), `/files/<id>` (tamano en
  bytes de cada mapa por resolucion y formato) y `/info/<id>` (dimensiones, autores, fecha). Segun el swagger
  oficial (`api.polyhaven.com/api-docs/swagger.json`): `dimensions` = "the dimensions of this asset on each axis
  in millimeters"; `size` = "Size of the file in bytes". Pagina de cada textura: `https://polyhaven.com/a/<id>`
  (comprobada con `rock_06`: titulo "Rock 06", "CC0 License", 1,5 m, autor Rob Tuytel).
- ambientCG: API `https://ambientcg.com/api/v2/full_json?q=<texto>&type=Material&include=downloadData,tagData,mapData`
  (devuelve `assetId`, `tags`, `maps`, `creationMethod` y, por zip, `attribute` 1K-JPG/1K-PNG/2K-JPG/2K-PNG con
  `size` en bytes). Pagina de cada material: `https://ambientcg.com/view?id=<AssetId>` (comprobadas 10 paginas;
  muestran tecnica, "ca. X m x X m" en algunas y los tamanos de descarga).
- Las listas de la categoria `terrain` de Poly Haven (131 entradas) se truncan en la lectura a partir de la "r":
  todo lo que esta en este informe se verifico ademas con `/files/<id>` o `/info/<id>` (respuesta 200). Los ids
  que devolvieron 404 se descartaron (seccion 8).

## 4. Candidatos por necesidad

Convenciones de las tablas:
- "1K / 2K" = suma en MB de los cinco mapas JPG Diffuse + nor_gl + Rough + AO + Displacement (Poly Haven), o
  tamano del zip completo 1K-JPG / 2K-JPG (ambientCG). Ambos leidos de la API; sumas comprobadas con Python.
- "Dim." = lado fisico de la textura (tileado) en metros, de la API (`dimensions`, en mm) o de la pagina ("ca.").
- Mapas Poly Haven (verificado en `/files` de cada id): Diffuse, nor_gl, nor_dx, Rough, AO, Displacement, arm
  (+ blend, gltf, mtlx; algunos ademas rough_ao o spec). Formatos jpg/png (y exr en algunos). Resoluciones 1k,
  2k, 4k, 8k (16k en los marcados).
- Mapas ambientCG (campo `maps` de la API): color, normal, roughness, ambient-occlusion, displacement (algunos sin
  AO; `RoofingTiles` anade opacity; `Rock051` anade metalness). Zips 1K/2K/4K/8K en JPG y PNG.

### 4.1 Caliza / roca estratificada calida (acantilados, roca del lazo, penon, McLaren petrificado)

| Textura (id) | Fuente / URL | Tags relevantes | Dim. | 1K / 2K (MB) | Nota |
|---|---|---|---|---|---|
| **rock_06** "Rock 06" | https://polyhaven.com/a/rock_06 | yellow, cliff, striated, striations, geological, exposed rock, weathered rock | 1,5 m | 2,14 / 8,07 | **P1.** Unica caliza amarilla estriada de PH. Autor Rob Tuytel (2018), 8k max. |
| marble_cliff_02 "Marble Cliff 02" | https://polyhaven.com/a/marble_cliff_02 | sedimentary, cracked, craggy, drone, dusty, brown, aerial | 6,8 m | 4,43 / 16,11 | Alternativa P3 para paredes grandes vistas de lejos (foto de dron, 2026, Amal Kumar). |
| marble_cliff_03 | https://polyhaven.com/a/marble_cliff_03 | strata, rock wall, sedimentary, cracks, drone | 5,7 m | no consultado | Misma serie; "strata" explicito. |
| cliff_side "Cliff Side" | https://polyhaven.com/a/cliff_side | cliff, rugged, eroded, orange, sediment, canyon, 16k | 1,83 m | 2,91 / 10,62 | Mas naranja/arido (Namaqualand); valido si la paleta tira a ocre fuerte. |
| Rock063 "Rock 063" | https://ambientcg.com/view?id=Rock063 | cliff, layered, eroded, gray, green, mossy | no indicada | 4,98 / 14,92 | Estratos reales pero gris-verde: habria que retintar. Fotogrametria. |
| Rock029 | https://ambientcg.com/view?id=Rock029 | cliff, desert, orange, red | no consultada | 9,68 / 33,49 | Procedural, muy naranja (desierto); descartable. |

### 4.2 Afloramiento rocoso (segunda roca para romper la repeticion; piedras al pie, repisas)

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **rock_face_03** "Rock Face 03" | https://polyhaven.com/a/rock_face_03 | cliff, rugged, eroded, cracks, chipped, 16k | 2,7 m | 3,67 / 14,33 | **P2.** Fotogrametria 2024 (Barresi/Cilliers). Gris-pardo neutro, facil de tintar a caliza. |
| rock_wall_02 "Rock Wall 02" | https://polyhaven.com/a/rock_wall_02 | rock face, coastal landscape, eroded, mossy patches | 2,0 m | 0,95 / 3,66 | Muy ligera; roca costera con manchas de musgo. |
| aerial_rocks_02 "Aerial Rocks 02" | https://polyhaven.com/a/aerial_rocks_02 | rocks, moss, cliff, rock face, aerial | 50 m | no consultado | Cenital de 50 m: solo para el macizo de fondo. |
| rocky_terrain "Rocky Terrain" | https://polyhaven.com/a/rocky_terrain | rock face, mountain, grass, terrain, aerial | 90 m | no consultado | Idem, 90 m: candidata a "capa lejana" del macizo. |
| Rock022 "Rock 022" | https://ambientcg.com/view?id=Rock022 | cliff, rock, wall | no indicada | 8,41 / 26,25 | Fotogrametria 2019. |

### 4.3 Hierba seca dorada

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **withered_grass** "Withered Grass" | https://polyhaven.com/a/withered_grass | old, weathered, grass, dead grass, discolored, driedup, dry | 2,0 m | 5,14 / 20,96 | **P1.** Charlotte Baglioni, 2023, 8k. El resumen del buscador la describe como hierba "sun-bleached" en tonos marron/tan. |
| grass_ground "Grass Ground" | https://polyhaven.com/a/grass_ground | grass, dry grass, dirt, root, dead grass, turf, dry, 16k | 2,51 m | 4,22 / 18,01 | Alternativa: hierba pisada sobre tierra (mas tierra visible). 2026. |
| forrest_ground_01 "Forest Ground 01" | https://polyhaven.com/a/forrest_ground_01 | dry grass, dead grass, twigs, leaves, underbrush | 2,0 m | 3,50 / 13,08 | Mas "sotobosque" (ramitas y hojas): bajo pinos. |
| ambientCG Grass0xx | https://ambientcg.com/view?id=Grass004 | grass, lawn, green | - | ~10 / ~39 | Todas las Grass de ambientCG son cesped verde procedural: no sirven para hierba seca (verificado con q=grass y q=dry). |

### 4.4 Matorral mediterraneo / salvia (capa oliva oscura)

Hecho: ninguna busqueda (PH categorias terrain/rock; aCG q=moss, q=grass, q=dry) devuelve una textura cenital
de matorral mediterraneo. Lo mas parecido:

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **aerial_grass_rock** "Aerial Grass Rock" | https://polyhaven.com/a/aerial_grass_rock | moss, grass, cliff, cave, rock face, aerial | 15 m | 2,61 / 10,61 | **P1 (como capa).** Cenital de 15 m con mezcla verde-sobre-roca: tintada a oliva oscuro da la "mancha de matorral" en laderas. Rob Tuytel 2020. |
| Ground037 "Ground 037" | https://ambientcg.com/view?id=Ground037 | moss, overgrown, grass, earth, woodland | ca. 2,1 m | 10,57 / 37,87 | Musgo y hierba densa: mas humedo de lo deseable; util como salvia si se desatura. |
| lichen_rock "Lichen Rock" | https://polyhaven.com/a/lichen_rock | rock, lichen, moss, cliff, boulder | no consultada | no consultado | Roca con liquen: para repisas del lazo. |
| forest_leaves_02 | https://polyhaven.com/a/forest_leaves_02 | moss, mossy patches, forest floor | no consultada | no consultado | Solo bajo pinar. |

Recomendacion: el matorral en si (bolas de salvia, lentisco) debe ser geometria/TreeFX (punto 4 del plan); la
textura solo aporta el color de fondo oliva. Una alternativa sin descarga es generar la capa en Blender (ruido
+ rampa oliva/salvia) y hornearla a 1024 px.

### 4.5 Tierra y pista de tierra

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **Ground105** "Ground 105" | https://ambientcg.com/view?id=Ground105 | beige, brown, dirt, dry, eroded, layered, rustic, uneven | no indicada | 9,40 / 33,64 (zip) | **P1 (capa tierra del terreno).** Fotogrametria 2026-01; es justo el "beige erosionado en capas" de la paleta. |
| **gravel_road** "Gravel Road" | https://polyhaven.com/a/gravel_road | gravel road, driveway gravel, gritty, pebbly, worn, 16k | 2,0 m | 2,85 / 10,26 | **P2 (superficie de la pista de tierra).** Amal Kumar 2024. |
| red_laterite_soil_stones | https://polyhaven.com/a/red_laterite_soil_stones | red, laterite, stones, pebbles, path | 2,0 m | 4,92 / 18,42 | Rojo laterita: habria que desaturar a ocre. Buen relieve (piedras). |
| dirt_aerial_02 "Dirt Aerial 02" | https://polyhaven.com/a/dirt_aerial_02 | mud, soil, erosion, compacted, tracks | 20 m | 1,94 / 7,83 | Cenital de 20 m con rodadas y erosion: para la banda ancha del tramo de tierra vista desde el aire. |
| dry_mud_field_001 "Dry Mud Field 001" | https://polyhaven.com/a/dry_mud_field_001 | road, mud, dry, farm, ground, brown, 16k | 3,0 m | 1,76 / 6,77 | Camino de tierra seco; ligera. |
| Ground110 "Ground 110" | https://ambientcg.com/view?id=Ground110 | brown, dirt, dry, gravel, rocky, scattered | ca. 2,1 m | 10,42 / 35,16 | Tierra con grava gris-marron (cuneta). |
| Ground081 / Pathway004 | https://ambientcg.com/view?id=Ground081 | dirt, gravel, path, rocky | no consultada | 5,74 / 18,18 ; 5,41 / 17,37 | Senderos (ermita, cima). |

### 4.6 Adoquin (calles del pueblo, plaza, paseo)

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **PavingStones150** "Paving Stones 150" | https://ambientcg.com/view?id=PavingStones150 | arches, beige, cobblestone, historic, patterned, rustic | ca. 0,9 m | 5,34 / 16,08 (zip) | **P1.** Adoquin en abanico beige/gris (tipico de Liguria/Costa Azul). Fotogrametria. Zip pequeno. |
| PavingStones151 | https://ambientcg.com/view?id=PavingStones151 | arch, arches, beige, mosaic, pedestrian | no consultada | 8,74 / 28,85 | Variante con mosaico. |
| cobblestone_floor_08 | https://polyhaven.com/a/cobblestone_floor_08 | cobblestone, smooth, old, moss, pavement | 2,0 m | 2,42 / 9,38 | Adoquin liso antiguo (PH, 2020). |
| cobblestone_large_01 | https://polyhaven.com/a/cobblestone_large_01 | cobblestone, farm, old, village, dry | 4,0 m | 2,83 / 10,79 | Bloques grandes de pueblo: plazas. |
| patterned_cobblestone_02 | https://polyhaven.com/a/patterned_cobblestone_02 | cobblestones, pattern, rugged, 16k | 2,1 m | no consultado | Con dibujo. |

### 4.7 Estuco / revoco de fachada

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **white_stucco** "White Stucco" | https://polyhaven.com/a/white_stucco | stucco, painted, granular, matte, uneven, porous | 2,0 m | 2,94 / 11,58 | **P1.** Blanco neutro: se tinta a ocre, rosa, salmon, amarillo (Riviera) con la cadena de tintado del escritor. Amal Kumar 2026. |
| plastered_wall_02 | https://polyhaven.com/a/plastered_wall_02 | plastered, discolored, flat, urban, exterior | 2,23 m | 2,67 / 10,31 | Revoco con manchas: variacion para fachadas viejas. |
| red_plaster_weathered | https://polyhaven.com/a/red_plaster_weathered | red, weathered, stained, cracked, brown, house | 2,0 m | no consultado | Ya "rojo pompeyano" desgastado. |
| cracked_concrete_wall | https://polyhaven.com/a/cracked_concrete_wall | beige, painted, plaster, cracked | 1,0 m | no consultado | Beige agrietado. |
| Plaster001 "Plaster 001" | https://ambientcg.com/view?id=Plaster001 | stucco, matte, outdoor, white | no consultada | 7,41 / 26,14 | Procedural, sin AO; muy limpio (mas Pixar que foto). |

### 4.8 Teja arabe (barro)

Hecho: ninguna de las dos bibliotecas etiqueta "barrel", "spanish" o "arabic"; los candidatos son tejas de barro
curvas/solapadas segun sus tags. Confirmar con la miniatura antes de descargar (seccion 7).

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **clay_roof_tiles_03** "Clay Roof Tiles 03" | https://polyhaven.com/a/clay_roof_tiles_03 | clay tiles, overlapping tiles, traditional roofing, uneven | 2,6 m | 3,29 / 12,56 | **P1.** "overlapping" + "traditional" + "uneven" es lo mas cercano a teja arabe. Amal Kumar 2024. |
| clay_roof_tiles_02 | https://polyhaven.com/a/clay_roof_tiles_02 | interlocking, overlapping, traditional, old | 2,5 m | 3,16 / 11,44 | "interlocking" sugiere teja plana tipo Marsella: segunda opcion. |
| roof_tiles "Roof Tiles" | https://polyhaven.com/a/roof_tiles | terracotta, interlocking, clay roof tiles, 16k | 2,0 m | 3,83 / 15,10 | Terracota limpia (Stephan Seeliger, 2025). |
| roof_09 / roof_07 | https://polyhaven.com/a/roof_09 | ceramic, old, worn, clay tiles, discolored | 4,0 / 2,0 m | no consultado | Serie antigua (2018) de Rob Tuytel: tejado viejo con musgo. |
| RoofingTiles013A | https://ambientcg.com/view?id=RoofingTiles013A | clay, roof, tiling (procedural, "Clean") | ca. 2,9 m | 4,35 / 11,89 | Procedural con mapa de opacidad; regular y limpio, encaja con el look Pixar si se quiere teja "de dibujo". |

### 4.9 Asfalto fino (pista, pit lane, calles)

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **asphalt_track** "Asphalt Track" | https://polyhaven.com/a/asphalt_track | track, racing, speedway, race track, tarmac road | 2,0 m | 3,00 / 13,00 | **P1.** Hecho para circuito (Dimitrios Savva, 2024). |
| clean_asphalt "Clean Asphalt" | https://polyhaven.com/a/clean_asphalt | fine-grained, gritty, racing, pit lane, bitumen | 2,1 m | 3,19 / 14,73 | Grano mas fino; alternativa para pit lane. 2026. |
| asphalt_pit_lane | https://polyhaven.com/a/asphalt_pit_lane | pit lane, race track | 2,0 m | no consultado | Misma serie. |
| Asphalt031 "Asphalt 031" | https://ambientcg.com/view?id=Asphalt031 | asphalt, grey, light, street | no indicada | 8,70 / 30,86 | Gris claro (calles del pueblo). |

### 4.10 Piedra seca de bancal (muros de olivar, terrazas)

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **rock_wall_10** "Rock Wall 10" | https://polyhaven.com/a/rock_wall_10 | rock, rocks, wall, cracks, dirt, earthy, stone wall | 1,8 m | 3,80 / 15,04 | **P2.** Muro de piedra con tierra entre juntas: bancal. Amal Kumar 2023. |
| rock_wall_06 | https://polyhaven.com/a/rock_wall_06 | stones, wall, rock, chipped, dry | 1,31 m | no consultado | "dry": piedra seca; mas pequena. |
| old_stone_wall_02 | https://polyhaven.com/a/old_stone_wall_02 | stone wall, masonry, rock wall, fortress walls, 16k | 2,09 m | no consultado | Mamposteria vieja (2026). |
| broken_wall "Broken Wall" | https://polyhaven.com/a/broken_wall | stacked, stones, old, ancient | 3,0 m | no consultado | Piedra apilada. |
| Bricks100 | https://ambientcg.com/view?id=Bricks100 | beige, medieval, old, stone, wall | no consultada | 4,83 / 14,46 | Sillares beige (muros de contencion del pueblo). |

### 4.11 Agua y fondo marino

Hecho: Poly Haven no tiene categoria de agua (lista de 56 categorias de `api.polyhaven.com/categories/textures`)
y en ambientCG `q=water` solo devuelve Ice001-004, SurfaceImperfections y suelos humedos. Para la superficie del
agua hay que usar una normal procedural (ruido de Blender horneado a 512-1024 px tileable) o el propio shader de
agua de AC (plan punto 6: `[Material_Water] Type = SEA` con CSP).

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **aerial_sand** "Aerial Sand" | https://polyhaven.com/a/aerial_sand | sand, coastal, seaside, ocean, sea | 15 m | 2,04 / 7,79 | **P2 (fondo marino).** Cenital de 15 m: bajo el agua con degradado turquesa-azul por vertice. |
| coral_ground_02 "Coral Ground 02" | https://polyhaven.com/a/coral_ground_02 | exposed seabed, reef, coral, sandy, coastline | 2,0 m | 3,36 / 12,01 | Fondo con coral/piedras para la orilla (cala del casino). |
| Ground054 "Ground 054" | https://ambientcg.com/view?id=Ground054 | beach, dirt, mud, sand | ca. 3,5 m | 8,67 / 32,99 | Arena de playa (la "banda blanquecina" de la captura 16). |
| aerial_beach_02 | https://polyhaven.com/a/aerial_beach_02 | beach, flat, coastal | no consultada | no consultado | Playa cenital. |

### 4.12 Grava / escollera / bloques de dique

| Textura (id) | URL | Tags | Dim. | 1K / 2K | Nota |
|---|---|---|---|---|---|
| **rocks_ground_06** "Rocks Ground 06" | https://polyhaven.com/a/rocks_ground_06 | rocks, broken, gravel, scattered rocks, coastal, layered rock | 3,0 m | 3,03 / 11,76 | **P2.** Roca costera rota en capas: pie de acantilado y escollera. Rob Tuytel 2020. |
| rock_ground "Rock Ground" | https://polyhaven.com/a/rock_ground | gravel, rough, broken, rock, ground | 1,5 m | 3,70 / 13,94 | Grava gruesa rota. |
| coast_sand_rocks_02 | https://polyhaven.com/a/coast_sand_rocks_02 | grass, rock face, moss, stones, cliff, seaside | 15 m | 3,89 / 14,10 | Cenital de costa (15 m): mezcla roca-hierba para la linea de costa. |
| Rocks011 "Rocks 011" | https://ambientcg.com/view?id=Rocks011 | cliff, ground, rock, rocks, stones (procedural) | no indicada | 8,37 / 28,24 | Bloques sueltos. |
| Gravel041 "Gravel 041" | https://ambientcg.com/view?id=Gravel041 | beach, gravel, pebbles | no consultada | 10,16 / 32,00 | Cantos de playa. |
| gray_rocks | https://polyhaven.com/a/gray_rocks | rocks, rocky, gray | 1,8 m | no consultado | Piedras grises. |

Nota: los bloques de escollera del dique (plan punto 6) son mejor geometria (cubos biselados con `rock_06`) que una
textura plana.

## 5. Lista final recomendada (13 + 1 opcional), con prioridad y tamano

Prioridad: P1 = necesaria para el terreno multicapa y las "postales"; P2 = necesaria para pueblo/costa pero
sustituible por material procedural; P3 = opcional.

| # | Pri. | Uso | id | Fuente | Dim. | Formato/res. | Mapas a bajar | 1K (MB) | 2K (MB) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | P1 | Terreno capa ROCA (caliza calida estratificada) | rock_06 | Poly Haven | 1,5 m | JPG 1K | Diffuse, nor_gl, Rough, AO, Displacement | 2,14 | 8,07 |
| 2 | P1 | Terreno capa HIERBA SECA | withered_grass | Poly Haven | 2,0 m | JPG 1K | idem | 5,14 | 20,96 |
| 3 | P1 | Terreno capa TIERRA (beige erosionada) | Ground105 | ambientCG | n/d | zip 1K-JPG | Color, NormalGL/DX, Roughness, AO, Displacement | 9,40 | 33,64 |
| 4 | P1 | Terreno capa MATORRAL (tintar a oliva) | aerial_grass_rock | Poly Haven | 15 m | JPG 1K | Diffuse, nor_gl, Rough, AO | 2,61 | 10,61 |
| 5 | P1 | Asfalto de pista y pit | asphalt_track | Poly Haven | 2,0 m | JPG 1K | Diffuse, nor_gl, Rough, AO | 3,00 | 13,00 |
| 6 | P1 | Estuco de fachadas (tintar por casa) | white_stucco | Poly Haven | 2,0 m | JPG 1K | Diffuse, nor_gl, Rough, AO | 2,94 | 11,58 |
| 7 | P1 | Teja de barro | clay_roof_tiles_03 | Poly Haven | 2,6 m | JPG 1K | Diffuse, nor_gl, Rough, AO, Displacement | 3,29 | 12,56 |
| 8 | P1 | Adoquin del pueblo | PavingStones150 | ambientCG | 0,9 m | zip 1K-JPG | Color, NormalGL/DX, Roughness, AO, Displacement | 5,34 | 16,08 |
| 9 | P2 | Segunda roca (afloramientos, repisas) | rock_face_03 | Poly Haven | 2,7 m | JPG 1K | Diffuse, nor_gl, Rough, AO | 3,67 | 14,33 |
| 10 | P2 | Pista de tierra (superficie conducible) | gravel_road | Poly Haven | 2,0 m | JPG 1K | Diffuse, nor_gl, Rough, AO | 2,85 | 10,26 |
| 11 | P2 | Piedra seca de bancal | rock_wall_10 | Poly Haven | 1,8 m | JPG 1K | Diffuse, nor_gl, Rough, AO | 3,80 | 15,04 |
| 12 | P2 | Grava / escollera / pie de acantilado | rocks_ground_06 | Poly Haven | 3,0 m | JPG 1K | Diffuse, nor_gl, Rough, AO | 3,03 | 11,76 |
| 13 | P2 | Fondo marino | aerial_sand | Poly Haven | 15 m | JPG 1K | Diffuse, nor_gl | 2,04 | 7,79 |
| 14 | P3 | Acantilados lejanos (6,8 m, foto de dron) | marble_cliff_02 | Poly Haven | 6,8 m | JPG 1K | Diffuse, nor_gl, Rough, AO | 4,43 | 16,11 |

Totales (sumas comprobadas):
- 13 texturas (1-13): **49,3 MB en 1K-JPG**; **185,7 MB en 2K-JPG**.
- 14 texturas (con la opcional): 53,7 MB en 1K; 201,8 MB en 2K.
- Minimo util (solo Diffuse + nor_gl + Rough de las 11 de Poly Haven + los 2 zips completos de ambientCG, que no
  se pueden recortar): **~39,6 MB en 1K**.
- En PNG las cifras se multiplican por 3-5 (p. ej. rock_06 1K-PNG: 8,5 MB frente a 2,1 MB en JPG): no compensa,
  porque el escritor vuelve a codificar a PNG de 8 bits a 512/1024 px.

Por que 1K y no 2K: `TEX_MAX = 1024` en el escritor; las texturas se tilean a 1,5-3 m (0,9 m el adoquin), asi que
1024 px dan 3-7 px/cm, mas que suficiente para la camara del coche a 1,5 m del suelo. 2K solo tendria sentido para
capturas de Blender de primer plano y cuadruplica la descarga.

## 6. Notas de integracion (sin tocar 04_export)

- Escala de tileado: usar las dimensiones reales de la tabla (mm de la API). Equivalencia con `aplicar_texturas.py`:
  `escala = 1 / lado_m` (rock_06 -> 1/1,5; withered_grass -> 1/2; adoquin 150 -> 1/0,9; aerial_sand -> 1/15).
  Las cenitales de 15-20 m (aerial_grass_rock, aerial_sand, dirt_aerial_02) son para capas de terreno vistas desde
  lejos; de cerca se les superpone una de 2-3 m (detalle) por la misma mascara.
- Tintado a la paleta: la cadena `TEX_imagen -> TEX_ganancia -> TEX_multiplicar` del escritor ya normaliza la media
  lineal y multiplica por el color base; por eso conviene bajar texturas neutras (white_stucco, rock_face_03) y
  dejar el color en el material. Las que ya traen el tono (rock_06 amarilla, Ground105 beige, withered_grass tan)
  necesitan factor ~1.
- Normales: Poly Haven da `nor_gl` (OpenGL, verde arriba) y `nor_dx` (DirectX); ambientCG incluye NormalGL y
  NormalDX en el zip. Hay que comprobar con una prueba cual convencion espera el shader de AC antes de elegir;
  bajar solo una de las dos (son identicas salvo el canal verde invertido).
- Terreno multicapa: el shader `ksMultilayer_fresnel_nm4` de AC necesita 4 texturas de detalle + mascara RGBA +
  normal; hoy el escritor solo emite difuso, asi que esto es trabajo del equipo de 04_export en una fase posterior.
  Mientras tanto, en Blender las mismas 4 texturas se mezclan por la mascara por pendiente/altura y se hornean a
  una difusa por sector (que si cabe en el flujo actual `<nombre>_d.png`).
- Agua: sin textura descargable; normal procedural horneada (ruido Voronoi/ondas, 512 px tileable) y degradado por
  vertice sobre `aerial_sand` para el fondo.
- Credito: aunque CC0 no lo exige, anadir `CREDITS.txt` al zip con los ids y la frase sugerida por ambientCG.

## 7. Hechos verificados en la fuente frente a suposiciones

Hechos verificados (leidos directamente de las APIs o paginas citadas en esta sesion):
- Licencia CC0 de ambos sitios y las citas de la seccion 2.
- Existencia, nombre, tags, autores, dimensiones (mm) y resolucion maxima de cada id de Poly Haven listado con
  "Dim." (respuesta de `/assets` o `/info`), y la lista de mapas y tamano en bytes de cada mapa 1k/2k en jpg/png
  de los ids con cifra en "1K / 2K" (respuesta de `/files/<id>`).
- Para ambientCG: assetId, tags, campo `maps`, `creationMethod` y tamano en bytes de los zips 1K/2K JPG/PNG
  (API v2), mas los datos de pagina de Rock063, Ground110, Ground105, PavingStones150, RoofingTiles013A,
  Ground054, Rocks011, Ground037, Rock022 y Asphalt031 (tecnica, "ca. X m" donde lo muestran).
- Que `dimensions` de la API de Poly Haven esta en milimetros y `size` en bytes (swagger oficial).
- Ausencia de texturas de agua en ambos sitios y de hierba seca fotografica en ambientCG.
- Contexto del repo: `TEX_MAX = 1024`, `TEX_SIZE = 512`, 438 texturas / 12,5 MB en el kn5, zip de 164 MB,
  escalas de `aplicar_texturas.py`.

Suposiciones (razonables, pero no comprobadas en la fuente):
- Que el zip de Poly Haven pesa aproximadamente la suma de los mapas elegidos (los JPG no se comprimen mas en
  zip). La pagina de rock_06 muestra "67.27 MB" para el paquete 4K por defecto; no se leyo la cifra del 1K.
- Que los PNG de Poly Haven son de 16 bits: se deduce del tamano (un Diffuse 1k PNG de 5,5-6,6 MB frente a
  0,5-1,1 MB en JPG), no de la documentacion (la FAQ de docs.polyhaven.com no devolvio contenido).
- Que `arm` es el mapa empaquetado AO/Roughness/Metal y que `nor_gl`/`nor_dx` difieren solo en el canal verde
  (convencion habitual de Poly Haven).
- El nombre de los ficheros dentro del zip de ambientCG (`<Id>_1K-JPG_Color.jpg`, `_NormalGL.jpg`, `_NormalDX.jpg`,
  `_Roughness.jpg`, `_AmbientOcclusion.jpg`, `_Displacement.jpg` + .usdc/.mtlx): convencion conocida; el campo
  `zipContent` de la API venia vacio y la pagina solo dice "PBR Maps (USDZ-compatible)".
- Que `clay_roof_tiles_03` es teja curva solapada y `clay_roof_tiles_02` teja plana encajada: deducido de los
  tags "overlapping/traditional/uneven" frente a "interlocking". Hay que mirar la miniatura antes de bajar.
- Que `withered_grass` es "dorada": los tags dicen dead grass/dry/discolored y el resumen del buscador habla de
  tonos marron/tan; el tono final se ajusta con el tintado.
- Que `Ground105` ("beige, dry, eroded, layered") lee como tierra calida de ladera: por tags y fecha (2026-01),
  no se vio la miniatura.
- La idoneidad "Pixar" de cada textura es juicio de este informe, no un hecho.

## 8. Descartados y no verificables

- `sparse_grass_ground`, `sandy_dirt_road`, `rocky_ground_01`, `sand_pathway_01`: aparecieron en una lectura
  truncada de la categoria terrain y `/files/<id>` devolvio 404 para los dos primeros. No existen con ese id
  (si existe `sparse_grass`, 2,0 m, verde con raices: no es hierba seca).
- `asphalt_02`: no esta en la categoria asphalt (aparece solo en terrain). No se necesita.
- `worn_rock_natural_01` (sandstone: yellow, brown, cliff, coastal): existe en la lista, pero no se consultaron
  sus ficheros ni dimensiones; candidata de reserva para caliza.
- ambientCG `Grass001-008`: cesped verde procedural, descartado para hierba seca. `Rock029`: naranja desierto.
  `Tiles139/142/143` (limestone): baldosa de interior, no roca.

## 9. Fuentes (URLs consultadas)

- https://polyhaven.com/license ; https://docs.ambientcg.com/license/
- https://api.polyhaven.com/categories/textures ; https://api.polyhaven.com/assets?t=textures&c=rock (y
  c=asphalt, c=plaster, c=cobblestone, c=sandstone, c=sand, c=gravel, c=roofing, c=terrain)
- https://api.polyhaven.com/files/<id> para: rock_06, marble_cliff_02, cliff_side, rock_face_03, rock_wall_02,
  grass_ground, forrest_ground_01, withered_grass, aerial_grass_rock, red_laterite_soil_stones, dirt_aerial_02,
  cobblestone_floor_08, cobblestone_large_01, white_stucco, plastered_wall_02, clay_roof_tiles_02,
  clay_roof_tiles_03, roof_tiles, asphalt_track, clean_asphalt, rock_wall_10, aerial_sand, coral_ground_02,
  rocks_ground_06, rock_ground, coast_sand_rocks_02, gravel_road, dry_mud_field_001
- https://api.polyhaven.com/info/withered_grass ; https://api.polyhaven.com/info/sparse_grass
- https://api.polyhaven.com/api-docs/swagger.json ; https://github.com/Poly-Haven/Public-API
- https://polyhaven.com/a/rock_06 (pagina de muestra)
- https://ambientcg.com/api/v2/full_json?q=<grass|dry|cliff|roofing|plaster|asphalt|paving|water|gravel|stone+wall|dirt|limestone|sandstone|moss|rocks|sand|path|terracotta>&type=Material&include=downloadData,tagData,mapData
- https://ambientcg.com/view?id=<Rock063|Ground110|Ground105|PavingStones150|RoofingTiles013A|Ground054|Rocks011|Ground037|Rock022|Asphalt031>
- https://docs.ambientcg.com/ ; https://docs.ambientcg.com/api/ ; https://docs.ambientcg.com/asset-types/
- Repo: `04_export/kn5_writer_opt.py`, `04_export/kn5/informe_check_opt.json`, `03_blender/aplicar_texturas.py`,
  `03_blender/RONDA15_PLAN.md`, `03_blender/_rev/director_final.md`, capturas 06, 13 y 51.
