# Entender el bloque AGUA / COSTA / PÚBLICO / RELLENO / CAPTURAS (fase visual, 04/10/2026)

Lector técnico del pipeline (Blender 5.1 + Python → KN5). No se ha modificado ningún fichero del proyecto ni se ha
lanzado Blender: todo sale de leer el código, los logs del último pipeline (`03_blender/_rev/logs_final/*.log`,
04/10 13:00) y las 57 capturas de `03_blender/renders/capturas`. Rutas relativas a `E:/Escritorio/claude-pc/arnau-aseto-corsa`.
Encargo: `03_blender/_rev/fase_visual/PLAN_USUARIO.md`, puntos 6 (agua y costa), 7 (público y relleno) y el método de
capturas antes/después.

## 0. Resumen en diez líneas

- El mar es UN quad de 20 km (`AGUA`, z=0) con un material (`MAT_agua`) cuyo "degradado" turquesa/azul es un ruido 2D
  de 250 m, NO depende de la profundidad; debajo hay otro quad plano (`AGUA_fondo`, z=-4.05) con el material del terreno.
- La costa es una máscara binaria de la rejilla de 4 m suavizada con gaussiana de 12 m; no hay malla de playa, ni
  rompiente, ni rocas de orilla salvo las propias de las rocas del lazo y del casino. La "playa" blanquecina es la rampa
  de color del terreno (arena en z≈0) con la hierba estirada encima.
- El puerto es un dique en arco de 200° y radio 145 m (perfil lofteado liso, no bloques), 3 pantalanes radiales con
  hasta 36 barcos de 3 modelos simples + 7 veleros sueltos (log: 41 barcos) y 1 faro. Aparte, 10 embarcaciones VIP de
  `yates_kit` (3 yates, 1 superyate, 4 lanchas, 2 fondeados) con público a bordo.
- Público: 4 tribunas de 45 m × 12 filas (público = coches de 89 tris, 4 siluetas × 8 colores) + la grada de los 20
  boxes; coches-espectador "de verdad" (`coches_kit_v2`, 9 tipos × 10 colores × 3 expresiones × 4 bocas) sólo hay
  UNA fila de 6 junto a la pista (s=734) y 3-4 filas de 5 en el paseo-mirador; 5 coches-cámara + 4 helicópteros.
- Relleno: ermita, 8 capillitas, fuente, 5 bancales de 14 m, cipreses, acueducto, hotel, ayuntamiento, campanile,
  dirigible. NO existen viñedos, villas con piscina, carpas, autocaravanas/tiendas ni torres costeras.
- Horizonte: NO hay anillo. `zona_montanas_fondo` se auto-desactiva desde la ronda 15 (el macizo va en el terreno);
  `montanas_fondo_v2.py` (aprobado) queda sin usar. Más allá de 1 km sólo hay mar plano hasta 9 km y el gradiente del cielo.
- Capturas: `renderizar_capturas.py` (57 tomas, 1600×900, ~1.7 s/toma) abre `porto_corsa.blend` a ruta fija y pasa cada
  cámara por `_rev/camara_segura.py`; `_rev/capturas_avance.py` es una copia antigua sobre `escena_rev.blend`. No hay
  sistema antes/después: las cámaras no se guardan y `camara_segura` puede moverlas entre dos renders.
- Propuesta (sección 9): `_rev/capturas_ab.py` + `_rev/montaje_ab.py` con cámaras CONGELADAS en JSON por bloque,
  set reducido (aéreas + piloto s300/800/1700/2900/3400/4150 + 4-8 tomas del bloque) y hojas lado a lado.

## 1. Mapa de ficheros del bloque

| Fichero | Qué hace en este bloque | Líneas clave | Estado |
|---|---|---|---|
| `03_blender/construir_pista.py` | Crea `AGUA`, `AGUA_fondo`, `MAT_agua`, `MAT_terreno`, sol y cielo | 92-160, 349, 1476-1513, 1566-1607 | activo |
| `03_blender/terreno_montana.py` | Máscara de mar `es_mar`, campo de costa `coastF`, playa 8 m | 1053-1075, 1101-1115, 1167-1179 | activo (ronda 15) |
| `03_blender/assets/puerto_kit.py` | Dique, faro, pantalán, yate/velero simples | 289-531 | único (sin v2) |
| `03_blender/assets/yates_kit.py` | Yates de lujo con público, superyate, lancha, pantalán VIP, coches de lujo | 1-75 (API), 1038, 1231, 1341, 1466, 1776 | opcional, cargado |
| `03_blender/assets/carrera_kit_v2.py` | Tribunas con público-coche, pórtico, pantallas, muros, vallas, pacas | 325-480 (público), 485-858 (tribuna) | v2 aprobado |
| `03_blender/assets/pit_kit.py` | Boxes con grada encima (`PIT_boxes_publico`), muro de boxes, torre, pasarela | 509-935 | v2 aprobado |
| `03_blender/assets/coches_kit_v2.py` | Coches-espectador detallados (9 tipos) y filas aparcadas | 509-652 (tipos), 1433-1543 (API) | v2 aprobado |
| `03_blender/assets/coches_kit.py` | v1 (5 tipos, 552 líneas): ya no se carga (coches_kit → v2) | 161-221, 414-550 | sustituido |
| `03_blender/assets/camaras_kit.py` | Furgoneta TV, grúa, torre, helicóptero-cámara | 1-43 (API), 1415, 1505, 1619, 1744 | activo |
| `03_blender/assets/horquilla_loews.py` | Rotonda-rueda de la horquilla (1 malla) | 345-474 | activo |
| `03_blender/assets/montanas_fondo_v2.py` | Cordilleras/picos/peñas/lomas de fondo | 1-80 (API) | aprobado pero NO usado |
| `03_blender/assets/italiano_kit.py` | Ermita, capitella, fuente, bancal, cipreses, pérgola, hito | 1-75 (API) | activo |
| `03_blender/assets/caminos_kit.py` | `build_camino(tipo='muelle')`: la escollera del puerto | 19-53, 554-650 | activo |
| `03_blender/integrar_escena.py` | `zona_meta` 333, `zona_pit` 449, `zona_puerto` 1323, `zona_dirigible` 1378, `zona_yates` 1412, `zona_loews` 2123, `zona_coches` 2339, `zona_montanas_fondo` 2486, paseo-mirador coches 4073, carretera del puerto 5726, `zona_camaras` 6033 | ver §2-§7 | activo |
| `03_blender/aplicar_texturas.py` | Familias de textura: `agua` (bump), `terreno` (hierba z 0.5-80), `piedra` (dique) | 44-101, 345-356 | activo |
| `03_blender/renderizar_capturas.py` | Las 57 capturas | todo (344 líneas) | activo, editado 04/10 13:20 |
| `03_blender/_rev/camara_segura.py` | Recoloca cámaras dentro del terreno / tapadas | 11, 34, 37-52, 55-80 | activo |
| `03_blender/_rev/render_vistas.py` | Vistas genéricas (piloto/dron/lateral/cenital) sobre `escena_rev.blend` | 43-66 | herramienta de revisión |
| `03_blender/_rev/capturas_avance.py` | Copia de las capturas sobre `escena_rev.blend` → `renders/capturas_avance` | 11-14 | copia del 03/10 22:33 (desfasada) |
| `04_export/kn5_writer_opt.py` | Cómo salen materiales, texturas y UV al KN5 | 73, 215-263, 387-408 | NO TOCAR (otro equipo) |
| `04_export/color_ac.py` | `ext_config.ini` de CSP: ya escribe `[Material_Water] Type = SEA` | 862-886 | NO TOCAR |

Cómo se carga cada módulo: `integrar_escena.py:40-63` (`load_mod`) usa `assets/<nombre>_v2.py` si el nombre está en
`assets/v2_aprobados.txt` (hoy: casino, carrera_kit, viaducto_curvo, casas_kit, coches_kit, edificios_civicos,
vegetacion_kit, pit_kit, montanas_fondo, montana_coche). `puerto_kit`, `yates_kit`, `camaras_kit`, `horquilla_loews`,
`italiano_kit`, `caminos_kit` no tienen v2.

## 2. AGUA: cómo está hecha

### 2.1 Mallas
`construir_pista.py:1476-1485`:
- `AGUA`: un solo quad de 4 vértices a z=0 que cubre la rejilla del terreno (x -933..1135, y -908..1152) más 9000 m por
  cada lado ("el mar llega al horizonte también en las tomas aéreas"). Material `MAT_agua` (slot único).
- `AGUA_fondo`: el mismo quad a z=-4.05 con `MAT_terreno` ("sin fondo se veía el borde recto del terreno como un
  rectángulo claro en el agua"). Es un fondo PLANO y uniforme: no hay degradado batimétrico.
- El `TERRENO` (rejilla 517×515 de 4 m, `geometria_3d.json['terreno']`) SÍ continúa bajo el agua: 163 534 de 266 255
  celdas son mar (61 %), z mínima -24.5 m. Es decir, cerca de la costa el fondo real que se ve a través del agua es el
  terreno (de -0.5 a -24 m), y a partir de donde el terreno acaba, el quad plano a -4.05.

### 2.2 Material `MAT_agua` (`construir_pista.py:349, 1486-1513`)
- Principled: `Alpha 0.84`, `blend_method BLEND`, `Roughness 0.04`.
- Color: `Noise(Object, Scale 0.004, Detail 4) → Mix RGBA` entre profundo `(0.015, 0.28, 0.44)` y turquesa
  `(0.04, 0.44, 0.54)`. Parches de ~250 m repartidos al azar: NO es "turquesa en la orilla, azul mar adentro".
- Normal: `Noise(Scale 0.02, Detail 5) → Bump 0.12` (olas suaves procedurales).
- `aplicar_texturas.py:63-64, 345-356` (familia `agua`, `familia_de()` línea 97): añade `agua_h.png` como bump de olas
  (tile 40 m, strength 1.0), factor de color 0.0 (no toca el color).
- Al KN5 (`kn5_writer_opt.analizar_material`, 215-258): el color base lineal + alpha 0.84 y, si hubiera imagen de
  color, su mapping Object FLAT/BOX con `scale`. Hoy el agua no lleva imagen de color → sale como color plano
  `(0.199, 0.350, 0.386)` efectivo (`color_ac.py:354 ALBEDO_EFECTIVO`) con `ksPerPixel` calibrado (`color_ac.py:281`,
  'agua': specular 0.45/0.60/0.80, exp 250). Sin sombra proyectada (`SIN_SOMBRA_TOKENS` en `kn5_writer_b.py:41`,
  `kn5_writer_opt.py:73 KEEP_PREFIXES`). Sin física (no lleva prefijo `1ROAD/1GRASS`; la lista `SUELO` de
  `exportar_ac.py:414-415` sólo endereza normales).
- CSP: `color_ac.py:862-869` ya genera en `extension/ext_config.ini` el bloque
  `[INCLUDE: common/materials_track.ini]` + `[Material_Water] Materials = MAT_agua / Type = SEA`. Falta
  `[BOUNCED_LIGHT] CAUSTICS = 1` que pide el usuario (no está en `EXT_CONFIG`).

### 2.3 Lo que se ve en las capturas
- `01_aerea_general`: mar uniforme y plano hasta el borde del cuadro; sin horizonte ni costa lejana; los parches
  turquesa/azul se leen como manchas, no como batimetría.
- `14_puente_mar`, `54_piloto_s4150`: el mar es una lámina azul lisa con una franja de rizado homogéneo; el borde
  tierra/mar es una línea limpia sin espuma ni rompiente (el director: "la playa es una banda blanquecina difusa", 16).
- `36_roca_casino_general`: "cala-marina es una losa rectangular blanca flotando en el mar" (plataforma de
  `roca_casino`, no del agua, pero la ausencia de orilla/rocas la delata).
- `47_yates_vip`, `02_meta_y_puerto`: el agua junto a la orilla es azul saturado hasta el mismo borde de la hierba; la
  orilla es hierba → arena de la rampa → agua, sin piedras ni humedad.

## 3. COSTA Y ESCOLLERAS

### 3.1 Orilla (terreno)
- `terreno_montana.py:1053-1075`: `es_mar` = (lado del mar a > 45 m de la pista) | (distancia a la bahía < 70+60·ruido)
  & no protegido; se eliminan lagunas (`_label`, 1070-1075). `1101-1115`: lejos de la pista el suelo sube al 3.5 % desde
  la costa (drenaje); la costa N/NE baja con smoothstep en 170 m (J1).
- `1167-1179`: `coast = gaussian_filter(es_mar, 12 m)`; `coastF = clip((coast-0.35)/0.3)` → 0 tierra / 1 mar. Con la
  ronda 15 (RONDA15_PLAN.md líneas 300, 429): orilla continua con distancia firmada, "playa 8 m al 40 %" (pendiente
  reducida en los primeros 8 m), fondo al 35 %. La rejilla es de 4 m: la orilla es una polilínea de celdas.
- Color: `MAT_terreno` (`construir_pista.py:92-160`) es una rampa por altura absoluta: fondo marino (z -4)
  `(0.40,0.48,0.34)`, arena z≈0 `(0.72,0.66,0.48)`, hierba a partir de z 0.5-3, monte, cumbres; roca sólo donde la
  normal.z < 0.58 (paredes > 55°, líneas 135-149); `aplicar_texturas.py:23-24, 270`: `hierba_d` multiplicada sólo
  entre z 0.5 y 80 (máscara de altura "sube en z 0.5..3"). De ahí la "banda blanquecina" de playa: 0.5-3 m de altura
  con la arena de la rampa y la hierba empezando a mezclarse.
- No hay NINGUNA malla de playa, rocas de orilla, espuma, línea de marea ni humedad. La única "orilla de rocas" es la de
  `roca_casino.py` (columnas 162-165 según RONDA15_PLAN.md:385) y la cala de `roca_lazo.py`.

### 3.2 Dique del puerto (`puerto_kit.build_dique`, 438-479)
- Loft de un PERFIL de 8 puntos (offset radial, z): interior -7.0/0 → paseo en z 3.05 (ancho 7.7 m) → parapeto
  2.8-3.9 a z 4.35 → talud exterior hasta +9.0/0. Arco de 200° centrado en -Y, `n = arco/5` secciones (≈40), tapas
  en los extremos. Materiales `MAT_PUERTO_piedra` (0.55,0.47,0.36, rough 0.9), `MAT_PUERTO_paseo`, `metal`, `farol`;
  9 farolas (cilindro + esfera emisiva) en el lado de la dársena; MORROS cilíndricos r 8 m en ambos extremos.
- Es decir: la "escollera" es una superficie LISA continua (una franja por tramo del perfil), no bloques; la textura
  `piedra_d` (familia `piedra` por la palabra 'piedra' en el nombre, `aplicar_texturas.py:70, 85-86`, box 3 m) es lo
  único que la rompe.
- Colocación `integrar_escena.zona_puerto` 1323-1341: centro a 190 m a la izquierda (mar) de s=60, `R_DQ=145`,
  `ARCO_DQ=200`, girado con `rot_facing_road(60, 1)`, z 0 (en el kit `build()` lo hunde 0.55; aquí no). `PUERTO_INFO`
  guarda centro, rot, R, a0, a1. Faro (`build_faro`, 398-435: zócalo r 3.4, 4 bandas rojo/blanco, galería, linterna
  emisiva, 18 m) en el morro a1 a z 3.25.
- Export: `exportar_ac.py:106-107` → `1ROAD_puerto_dique_malla` (transitable, el coche llega por la escollera).

### 3.3 Escollera de la carretera del puerto (`integrar_escena.zona_caminos` apartado 5, 5726-5826)
- Boca elegida entre s 40..160 donde la recta boca→dique no cruza tribunas/pantallas/boxes/PIT/PUERTO/HOTEL (`_choca`,
  5735-5747; log final: s=140). `_empalme` + `_perp` (6 m perpendicular) → tramo de tierra (asfalto 5.5 m, terraplén)
  hasta donde `z_terreno < 0.6` (la "orilla", 5755-5758) → `_camino([orilla, fin_d], tipo='muelle', z_fijo=mar+3.25,
  canto=hasta el fondo-0.5, nivel_agua=0)` (5819-5823) hasta el centro del morro a0 del dique. Log: 30 m tierra + 144 m
  de escollera.
- `caminos_kit.build_camino(tipo='muelle')` (docstring 31-36; perfil 619-644): losas Voronoi 0.65 m
  (`MAT_CAMINO_piedra_muelle`), pretil de piedra crema 0.35×0.55 a ambos lados, faldón de piedra con ruido hasta
  `-canto`, norays y banda oscura de línea de agua (`muelle_agua`) hasta nivel_agua+0.35. Otra vez: superficie lisa con
  ruido, no bloques apilados.
- Inspección: `revisar_flotantes.py:43-46` (EXENTOS: PUERTO_faro, YATE, AGUA, AGUA_fondo...) y referencia marina =
  primera obra del puerto bajo la caja (RONDA15_PLAN.md:308).

### 3.4 Muelles secundarios
- Cala de la roca del lazo: `PENON_puente_muelle` (malla en coordenadas de mundo, `roca_lazo.py`), con pantalán
  `PUERTO_pantalan_roca` si existe (lo busca `renderizar_capturas.py:249-256` para la toma 46).
- Cala del casino: plataforma + pantalán + 3 lanchas de `roca_casino.py` (T4 de RONDA15_PLAN.md:155-157); hoy una
  "losa blanca flotante" (36_roca_casino_general).

## 4. PUERTO Y EMBARCACIONES: cuántas hay y cómo son

### 4.1 Marina del dique (`zona_puerto`, 1342-1374) — 41 barcos (log 13:00)
- 3 pantalanes `build_pantalan(largo=60)` (364-395: flotadores, bastidor, tablazón de dos tonos, norays) radiales a
  225°, 270° y 315° (en el marco del dique), arrancando en R-7 y apuntando al centro.
- Por pantalán, 6 posiciones cada 9 m × 2 lados, alternando `('yate2', 18 m)`, `('velero', 12 m)`, `('yate', 25 m)`
  de la biblioteca (`build_library` 304-306); se coloca sólo si proa, centro y popa tienen `z_terreno < -1.0` → máximo
  36 en la dársena.
- 7 veleros "navegando" en un rectángulo de 580×500 m fuera de la dársena (R+25) donde `z_terreno < -2.5`.
- Modelos (`puerto_kit`): casco por loft de 7 secciones de 7 puntos (`_casco`, 255-284) + cajas (cabina, cristal,
  segunda cubierta, techo), radar, radomo (`build_yate`, 289-325); velero con mástil, botavara, velas recogidas como
  conos (`build_velero`, 328-361). Muy por debajo de 5k tris cada uno; 1 malla + Empty raíz `PUERTO_yate` /
  `PUERTO_velero`. Sin público, sin variación de color (16 materiales fijos `MAT_PUERTO_*`, 54-75).
- Tamaños: sólo 3 (25, 18, 12 m). Ningún barco "grande" en la marina; ninguna lancha.

### 4.2 Flota VIP (`zona_yates`, 1412-1483) — 10 embarcaciones (log 13:00)
- `yates_kit` (API en 1-75): proa a +X, estribor (+Y) hacia la pista, z=0 nivel del mar, calado máximo -2.5.
  `build_yate(eslora 26/32)` 4-8 coches VIP + mesa + mayordomo, pasarela con alfombra roja, bandera, defensas;
  `build_superyate(70)` 3 pisos, helipuerto con mini-helicóptero, piscina, 9-12 coches; `build_lancha(9)` estilo Riva
  con 1-2 coches; `build_pantalan_vip(largo 100)` con farolillos, limoneros, cordón; `build_coche_lujo` (limusina,
  deportivo, cabrio) y coches de `coches_kit_v2` (sedan, deportivo, familiar, compacto, topolino, colores negro/perla/
  burdeos/azul marino/dorado/plata).
- Colocación: frente a la recta de meta (s_a = L-130): 3 yates en s 5070/5110/5150 a 62 m+dv del borde, 1 superyate en
  s 5130 a 118 m, 4 lanchas en s 5040..5175 a 92 m; pantalán VIP de 100 m a `off_v` (medido buscando la orilla,
  1448-1461); y 4 fondeados sin pasarela (2 frente al paseo-mirador s 3060/3120 lado -1, 2 en el retorno s 4700/4780).
  De 12 posibles se colocaron 10 (`_agua()` exige `z_terreno < -1.8`).
- El público de los yates mira a +Y; es el único público "detallado" (coches_kit_v2 con cara) fuera de las filas.

### 4.3 Otros
- Dirigible (`zona_dirigible`, 1378-1409): elipsoide 48×17×17 m + góndola, a 380 m mar adentro de s=30 y z 230, estático.
- Faro: 1 (`PUERTO_faro`, morro a1). No hay torres costeras ni segundo faro.
- `puerto_kit.build()` (484-531) es sólo la viñeta de test (agua propia `PUERTO_agua` disco de 320 m): no se usa.

## 5. PÚBLICO: cuántos hay y de qué tipos

### 5.1 Tribunas (4) — `carrera_kit_v2.build_tribuna` (485-858)
- Biblioteca: `lib['tribuna'] = ck.build_tribuna(LIB, largo=45, filas=12)` (`integrar_escena.py:259`); clones en
  `zona_meta` 360-379: lado del mar en s 40, 100 y L-60 (offset 16/26/36 según haya tierra) + 1 interior en s L-226
  (lado -1, a la cota de la pista +0.25). Log `explanadas: CARRERA_tribuna.001..004` → 4 tribunas.
- Público: `_pub_coche` (350-480) = coche de ~89 tris: 3 anillos octogonales (faldón, cintura, capó), cabina con
  parabrisas/luneta mate, 2 ojos (8 lados) + pupilas (6) sobre el parabrisas, boca cerrada/abierta, 2 cajas-eje de
  ruedas. 4 siluetas `_PUB_TIPOS` (berlina 5, deportivo 3, furgoneta 2, utilitario 3; 325-331) × 8 colores
  `_PUBLICO` (rojo, azul, amarillo, verde, naranja, morado, cian, blanco; pesos 334) → 32 combinaciones, escala
  0.90-1.06, jitter ±0.13 m, todos miran al mismo punto (829-852, 12 % "despistados"). Plazas: paso 2.05 m por bloque
  × 12 filas, ocupación 0.9, tope `max_tris 16000` → `(16000 - estructura - techo) // 90` ≈ 120-160 coches por grada.
  UNA malla `CARRERA_tribuna_publico` con 11 materiales (`_PUB_MATS`, 338). Banderas tricolor sólo en el frontis de la
  estructura (765-780), no en los coches.
- Export: `CARRERA_tribuna_estructura` → `1WALL_` (`exportar_ac.py:112`); el público no colisiona
  (`revisar_fisica_ac.py:61 NO_OBSTACULO`).

### 5.2 Grada de los boxes — `pit_kit.build_boxes_tribuna` (509-935)
- 20 boxes × 6 m con grada encima (`PIT_boxes_grada/techo/publico/numeros`), público a tresbolillo con paso 1.55 m
  (`_PASO_PUB`, 493), primera fila pegada al peto (docstring 17-27), mismo estilo low-poly que las tribunas
  (sección "coches-espectador (publico)" 353+). Colocado por `zona_pit` 449-494 (`PIT_boxes`). Es la grada más grande
  de la escena (120 m).

### 5.3 Coches-espectador detallados — `coches_kit_v2` (aprobado) + `zona_coches` (2339-2433)
- Kit: `build_coche(tipo, color, seed, expresion, boca, baca/bitono/franjas/carga)` (1433-1460). 9 TIPOS (509-510):
  topolino, compacto, sedan, familiar, deportivo, furgoneta, pickup, todoterreno, ape (3 ruedas); 10 `COLORES_VIVOS`
  (95-106); 3 expresiones × 4 bocas; opciones por seed (baca con maleta, bitono, franjas, alerón, rueda de repuesto,
  carga). ≤ 3500 tris por coche, ≤ 10 slots (`MAT_COCHE_cuerpo_<HEX>` + 11 fijos). `build_fila_aparcada(n=6, seed)`
  (1484-1523): fila lado a lado, paso ~2.6-2.9 m, jitter y giro ±6°, tipos por sorteo ponderado sin repetir
  (`_PESOS_FILA` 1463). `build_muestrario` (1526) = los 9 tipos en fila para inspección.
- Colocación: `zona_coches` construye 5 filas de 6 (seeds 1-5) y busca sitios con `sitio_ok` (2359-2404): no bridge/
  dirt, no s 300-660 (túnel), no s > L-300 ni < 230, no a 80 m antes / 20 m después de un piano del mismo lado, tramo
  recto (giro < 0.22 rad en 28 m), terreno > 0.6 m y desnivel < 1.8 m en 10 sondas, |z_borde - z_media| < 1.6 (+0.25
  por metro de offset extra), lejos de casas (11 m) y edificios (30 m) y de otros tramos de pista (w/2+6). Preferencia 1:
  pradera de la Loews (±45-95 m); preferencia 2: cada 22 m a 14.5 o 9.5 m del borde; máximo 11 filas, separación 70 m
  (otro lado) / 170 m (mismo lado). RESULTADO (log 13:00): `coches-espectador: 1 filas junto a la pista en s=[734]
  (de 1 sitios validos)`. Con el macizo de la ronda 15 (desmontes, terrazas, peraltes) casi ningún sitio pasa el filtro.
- Paseo-mirador (s 2990-3150, lado -1): `integrar_escena.py:4073-4089`, 3 filas de 5 (`build_fila_aparcada(n=5,
  seed 20..22)`) cada 40 m a 7.5 m del borde → `MIRADOR_coches` (3-4 filas, saltando la pasarela). Más el aparcamiento
  en terraza del mirador (`mirador_kit.build_parking_terraza`, 1164; 4121 en integrar).
- En total, coches-espectador "con cara y variación": 1 fila × 6 + 3-4 × 5 + los de los yates (≈ 4-8 × 5 + 9-12 + 4-8
  lanchas) ≈ 70-90 en toda la escena; el resto del público (miles) son los low-poly de 89 tris de gradas y boxes.

### 5.4 Coches-cámara y helicópteros — `camaras_kit` + `zona_camaras` (6033-6303)
- Piezas (6038-6040): furgoneta TV (seed 1), grúa 7 m (seed 2), torre 6 m (seed 3), furgoneta (seed 4), grúa 8.5 m
  (seed 5). Cada una ≤ 4.5-5k tris, con cara (ojos en el parabrisas, boca) y cámara broadcast grande.
- Sitios: ápices de curvatura (6168-6174, máximo local de |kappa| > 0.009 en ±24 m), fuera de puentes, túnel (s 522 ±
  110), pit lane (lado -1 en s > L-230 o < 210), mirador; exterior de la curva a 8.5/11/14/18 m o interior a 9/12.5
  (en tierra o tras bajada primero el interior, 6192-6195); terreno > 0.8, |zt - z_borde| < 2.6, desnivel < 1.2 m en
  6×6; `sitio_valido` (6065-6081) contra ejes de calles/caminos (umbral 6.3 m), edificios, plazas. Furgoneta y grúa
  necesitan RAMAL de tierra con valla desde 12 m antes (`_ramal_camara`, 6088-6115; si no cabe → torre fija).
  `poner` (6117-6166): peana de piedra 6.8×5.4×0.7 m (`CAMARA_peana`, 1WALL_ en export 87-88) + clon `CAMARA_tierra`.
  Grúa fija de la Loews (6240-6284): cresta s 3440 lado -1 con ≥ 80 % de la bajada visible por rayos.
  Log: 6 puestos (s 1084, 2364, 2502, 2648, 3198, 3440); `despeje_final` quita el de s 2502 con peana y ramal → 5.
- Helicópteros (6288-6300): 4 clones `CAMARA_heli` a 26 m fuera del borde y 34-42 m de altura en s 60, Loews-30,
  curva 43 y s 1840, morro -14°. `build_helicoptero_camara` (1744): cuerpo + discos de rotor con alpha (sin sombra).
- Las torres sobre losa en el prado sin camino son el defecto 8 del director (27_coche_camara_0/1/2, 36, 41).

### 5.5 Rotonda Loews — `horquilla_loews.build` (345-474) + `zona_loews` (2123-2204)
- 1 malla `LOEWS_rotonda` ≤ 6000 tris por `_lathe` de perfiles (murete, flores azules, seto, parterre-rueda con 8
  radios de seto y 8 cuñas de flores, 2 palmeras), 13 materiales `MAT_LOEWS_*`. Radio medido contra el borde interior
  (2144-2158), escala si no cabe, tambor de piedra de 7 m debajo (2164-2186), 5 vallas publicitarias por fuera.
  Intacta por petición del usuario (`construir_loews_intacta`, terreno congelado en `assets/_loews_terreno.npz`).

## 6. RELLENO existente (lo que hay y lo que falta)

| Pide el usuario | Hay hoy | Dónde |
|---|---|---|
| Bancales de olivos con muro de piedra seca | `italiano_kit.build_bancal(largo 14, alto s/pendiente, fondo 3.5)` con olivos cada 7 m; 2 en el sendero CIMA y 3 en el ERMITA (log) + muros de terraza del pueblo | `integrar_escena.py:5266-5303`, `urbanismo_escena` |
| Viñedos | ninguno (sólo la parra de `build_pergola`) | — |
| Villas con piscina | ninguna (`casas_kit_v2` son casas de pueblo; la única piscina es la del superyate) | — |
| Aparcamientos llenos | 1 fila de 6 + paseo-mirador (3-4 × 5) + parking en terraza del mirador | §5.3 |
| Carpas de hospitality | ninguna (grep `carpa|hospitality`: 0 resultados) | — |
| Torres costeras / faro | 1 faro en el dique; 0 torres costeras (sólo `PIT_torre` de control y torres de cámara) | §3.2 |
| Autocaravanas / tiendas de campaña en la ladera | ninguna (grep `caravana|tienda de campa`: 0) | — |
| Público en balcones / terraza del casino | ninguno; en yates sí (§4.2) | — |
| Ermita, capillitas, fuente, hitos, pérgola | `italiano_kit`: 1 ermita (mirador del sendero), 8 edículas (`zona_edicolas`, 1224), fuentes en plazas, pérgola, hitos | 1224-1320, 5097-5320 |
| Acueducto, hotel, ayuntamiento, campanile | sí (`zona_acueducto` 2466, `zona_meta` 358, `zona_pueblo`) | — |
| Dirigible, helicópteros, barcos (animables con CSP) | estáticos | §4.3, §5.4 |

## 7. HORIZONTE

- `zona_montanas_fondo` (`integrar_escena.py:2486-2533`): si `G['cumbres']` existe (ronda 15: 5 cumbres de 107-210 m)
  hace `return` en la línea 2495 → ni cordilleras ni peñascos. `montanas_fondo_v2.py` (aprobado en `v2_aprobados.txt`,
  API: `build_pico`, `build_cordillera(largo, n_picos, alto=195)`, `build_pena`, `build_loma`, materiales
  `MAT_MONT_bosque*/roca*`, ≤ 60k tris por cordillera) está disponible pero sin usar.
- Cielo: world `CIELO` (`construir_pista.py:1586-1607`): rampa por la Z del vector Generated, horizonte claro
  (0.70,0.84,0.98) → cenit (0.12,0.34,0.86). Sol 34° de elevación, azimut -140° (1566-1572). El world no se exporta: en
  AC el cielo lo pone el juego (o Sol/Pure con CSP).
- Geometría: rejilla de terreno 2.07 × 2.06 km; pista en x -713..612, y -688..590; `AGUA` hasta ±9 km; cámaras con
  `clip_end 12000`. Desde la pista y las aéreas, más allá de ~1 km sólo se ve mar y cielo (01, 14, 16, 54).
- En AC, sin anillo de horizonte la línea mar/cielo queda a 9 km y cualquier cámara alta ve el corte del quad.

## 8. SISTEMA DE CAPTURAS ACTUAL

### 8.1 `03_blender/renderizar_capturas.py` (344 líneas, editado 04/10 13:20)
- Entrada: `GEOM` (env, defecto `geometria_3d.json`); abre SIEMPRE `porto_corsa.blend` (ruta fija, línea 12);
  salida `renders/capturas/<nombre>.png` (líneas 14-15); 1600×900 (42-43); motor = el guardado en el blend (EEVEE con
  los ajustes de `construir_pista.py:1609+`).
- Utilidades: `fr(s)` muestra de la pista, `s_curva(n)`, `cam(name, loc, tgt, lens)` (25-33: cámara `CAP_<nombre>`,
  rotación `to_track_quat('-Z','Y')`, clip 12000), `tras(s, atras, alto, lateral, adelante, lens)` (35-40: cámara
  `atras` m detrás de s a `alto` m mirando a s+`adelante` a +3 m), `_bbox_centro(raiz)` (137-146).
- Lista `tomas = [(nombre, loc, tgt, lens)]` (53-330), 57 tomas:
  - fijas por s: 01 aérea (centro del bbox, -1500 m, z 1250, lente 32); 02 meta; 03/04 túnel (`TUNEL_acantilado`
    `s_in/s_out`); 05-10 por curvas 6, 880 m, 15, 18, 30, 34; 11-12 Loews; 13-16 viaducto/roca del lazo/chicane; 17
    salida del túnel.
  - por objetos: 19/20 `CASINO_root`; 21/22 `PENON_puente`; 23/24 Loews; 25/26 `G['miradores']`; 27_x `CAMARA_tierra`
    (3 primeros); 28 `CAMARA_heli`; 29-31 `PIT_boxes`; 32/33/33b `TUNEL_acantilado` (McLaren); 34/36 `PENON_puente` /
    `PENON_cara` (general + desde_pista); 39/40 pueblo s 870; 41 espolón; 42 paddock; 43 grúa de la Loews; 44 bajada;
    45/46 roca del lazo; 47/47b `YATE_` más cercano a L-70; 48 `ITAL_ermita`; 38 rotonda.
  - PILOTO 49-54 (284-287): `loc = fr(s) + 1.4 m`, `tgt = fr(s+80) + 1.2 m`, lente 24, en s 300, 800, 1700, 2900,
    3400, 4150 (sec: straight, tech, dirt, straight, tech, bridge).
  - "rehechas" (289-330): 15 desde fuera de la U a 200 m y +75; 40 desde la pista (s 840 → s 930 a 18 m del borde);
    43 desde s 3440 +5 m hacia la Loews; 47b buscando por rayos el punto de la recta (L-300..L-5 cada 10 m) desde el
    que se ve el yate sin tribuna delante (314-329).
- Bucle (331-344): `CAPTURAS_SOLO=prefijo1,prefijo2` filtra; cada toma pasa por `camara_segura.asegurar()` y se
  renderiza con `bpy.ops.render.render(write_still=True)`. Las cámaras `CAP_*` quedan en memoria, NO se guardan: no hay
  registro de dónde acabó cada una (sólo el print de `camara_segura`).
- Tiempos (log 13:00): 57 tomas en 1:40 min, ≈ 1.7 s/toma + 5 s de carga (escena de 42 MB).
- Nota: el director revisó el render de 13:01; `15_final_puente_roca.png` y `47b_yates_desde_pista.png` se
  re-renderizaron a 13:16 y 13:20 con el script ya corregido (CAPTURAS_SOLO). Las otras 55 son de 13:01.

### 8.2 `03_blender/_rev/camara_segura.py` (80 líneas)
- `NO_TOCAR = ('piloto', 'desde_pista', 'tunel', 'pit_lane', 'travesia', 'yates_desde')`; `LIGERO = ('desde_pista',
  'travesia', 'yates_desde', 'desde_grua')` → `_ajuste_ligero` sube de 2.5 en 2.5 m (máx 12.5) si algo tapa el primer
  35 % del rayo o la cámara está "dentro" (`_dentro`: rayo vertical hacia arriba que choca con una cara de frente).
- Resto: `asegurar` (55-80) hasta 14 pasos de +12 m y 7.2 m hacia atrás mientras esté dentro o el TERRENO corte el
  rayo a < 90 % con el impacto a > 25 m del objetivo. Log 13:00: movió 05 (+1 paso), 33b (+3), 36_general (+3).
- Consecuencia para antes/después: si el relieve cambia entre dos renders (bloque 1 del plan), la MISMA toma puede
  salir desde otra posición. Hay que congelar.

### 8.3 `03_blender/_rev/capturas_avance.py` (278 líneas, 03/10 22:33)
- Copia de `renderizar_capturas.py` que abre `_rev/escena_rev.blend` + `_rev/geometria_rev.json` y escribe en
  `renders/capturas_avance/`. Está DESFASADA: no tiene la 15 desde fuera de la U (línea 72 = `tras(curva 43)`), ni
  34_desde_pista de piloto (189), ni la grúa a < 220 m (213: < 90), ni las rehechas 40/43/47b. Sirve como ejemplo de
  "mismas tomas sobre la escena congelada", que es justo la base del antes/después.

### 8.4 `03_blender/_rev/render_vistas.py` (82 líneas)
- `blender_cola.sh --python render_vistas.py -- vistas.json carpeta [ancho alto]` (defecto 960×540) sobre
  `escena_rev.blend`. Modos: `loc/target` explícitos, `piloto` (1.4 m, 80 m adelante), `piloto_atras`, `dron` (90 m
  atrás, `alto`), `lateral` (`lado`, `dist`, `alto`), `cenital` (`alto`, lente 35). Es la herramienta de vistas ad hoc de
  los revisores (sin `camara_segura`). Las cámaras se llaman `REV_<nombre>`.

### 8.5 Infraestructura
- `_rev/blender_cola.sh`: máximo 6 Blender a la vez (slots en `_rev/cola/`), `--background --factory-startup`.
- `_rev/pipeline_escena.sh`: genera la escena completa y la congela en `_rev/escena_rev.blend` + `geometria_rev.json`
  + `urbanismo_rev.json` (líneas 35-37). Es el "estado antes" natural de cada bloque.
- `renders/capturas_resumen/hoja_01..10.png` y `resumen_*.png`: hojas de contacto hechas a mano (ningún script del
  repo las genera: grep `capturas_resumen` = 0). PIL 12.3 y numpy 2.5 están en el python del sistema.
- Los workflows (`_rev/workflows/*.js`) lanzan `renderizar_capturas.py` entero tras el pipeline (5-15 min previstos;
  real 1:45).

## 9. PROPUESTA: capturas antes/después desde las mismas cámaras, por bloque

### 9.1 Principios
1. Las cámaras se CONGELAN en un JSON por bloque la primera vez (el "antes"); el "después" las lee tal cual y NO pasa
   por `camara_segura`. Si una cámara congelada queda dentro del terreno nuevo, se avisa y se renderiza igual (se ve en
   la hoja y se decide a mano), o se añade una toma nueva con otro nombre: nunca se mueve la congelada.
2. Las posiciones se calculan desde la geometría de la pista (`fr(s)`), que no cambia en la fase visual, con el mismo
   código que `renderizar_capturas.py` (misma `tras`, mismo piloto 1.4/1.2/80 m/lente 24). Para no duplicar 300
   líneas, la lista de tomas se saca a un módulo importable `_rev/tomas_capturas.py` con `construir_tomas(G, bpy)` →
   `[(nombre, loc, tgt, lens)]` (copia de las líneas 45-330 metidas en una función; `renderizar_capturas.py` puede
   seguir igual hasta que el coordinador decida que importe del módulo).
3. Un set REDUCIDO por bloque (12-18 tomas, ~40 s de render) en vez de las 57, y el set completo sólo al cerrar la fase.
4. Las hojas lado a lado se generan con PIL fuera de Blender, sin ocupar hueco de la cola.
5. Se juzga sobre todo desde el coche: las 6 de piloto van SIEMPRE, a tamaño completo, en todas las hojas.

### 9.2 Sets por bloque (nombres = los de `renderizar_capturas.py`)
- `BASE` (en todos): `01_aerea_general`, `49_piloto_s300`, `50_piloto_s800`, `51_piloto_s1700`, `52_piloto_s2900`,
  `53_piloto_s3400`, `54_piloto_s4150`.
- `agua_costa`: + `02_meta_y_puerto`, `14_puente_mar`, `16_retorno_chicane`, `22_viaducto_arcos_altos`,
  `36_roca_casino_general`, `46_roca_lazo_muelle`, `47_yates_vip`, `47b_yates_desde_pista` y 2 nuevas:
  `60_puerto_llanta_cenital` (cenital sobre `PUERTO_INFO['centro']` a 420 m, lente 35) y `61_orilla_piloto_s150`
  (piloto en s 150 girado 35° hacia el mar: ve la orilla, la escollera y el dique).
- `publico`: + `02_meta_y_puerto`, `29_boxes_desde_pista`, `30_boxes_tribuna_aerea`, `47_yates_vip`,
  `27_coche_camara_0/1/2`, `28_helicoptero_camara`, `12_rotonda_loews`, `25_paseo_mirador_desde_pista` y 1 nueva:
  `62_tribuna_piloto_s5100` (piloto en s 5100 girado 30° al lado +1: la grada del mar a la altura del coche).
- `relleno`: + `09_bajada_recta`, `21_montana_dentro_del_lazo`, `26_paseo_y_parking_desde_abajo`, `42_paddock_hotel`,
  `48_ermita_sendero`, `10_casino_sector`, `39_pueblo_calles_aerea`.
- `horizonte`: + `14_puente_mar`, `16_retorno_chicane`, `13_puente_alto`, `08_tierra_cima`, `19_penon_casino_foto` y
  1 nueva: `63_horizonte_piloto_s2200` (piloto en la cima de tierra mirando al mar, lente 20).
- Las 5 "postales" del punto 1 del plan (salida del túnel, cima de tierra, puente del casino, bajada a la horquilla,
  recta del puerto) son `04_tunel_salida`, `08_tierra_cima`/`51`, `13_puente_alto`, `11_bajada_rotonda`, `02`/`49`:
  conviene añadirlas al `BASE` cuando el bloque RELIEVE las fije.

### 9.3 Nombres de ficheros
```
03_blender/renders/ab/<bloque>/camaras.json                 cámaras congeladas: {nombre: {loc, tgt, lens, s?}}
03_blender/renders/ab/<bloque>/antes/<NN_nombre>.png        render de la escena congelada antes del bloque
03_blender/renders/ab/<bloque>/despues/<NN_nombre>.png      render tras el bloque (misma cámara)
03_blender/renders/ab/<bloque>/AB_<NN_nombre>.png           antes | después lado a lado, rótulo con bloque y fecha
03_blender/renders/ab/<bloque>/hoja_<bloque>_piloto.png     las 6 de piloto, 2 columnas (antes/después) × 6 filas
03_blender/renders/ab/<bloque>/hoja_<bloque>_aereas.png     el resto del set, 2 columnas
03_blender/renders/ab/<bloque>/ab.log                       cámaras que quedaron dentro del terreno, tiempos
```
`<bloque>` ∈ {relieve, roca, paleta, vegetacion, pueblo, agua_costa, publico, relleno, horizonte, carificacion, csp}
(los 9 puntos del plan). Si un bloque se repite, `antes_v2/`, `despues_v2/`.

### 9.4 Flujo por bloque (comandos)
```
# 0) estado ANTES = la escena congelada por el último pipeline
bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/capturas_ab.py -- \
     --blend 03_blender/_rev/escena_rev.blend --geom 03_blender/_rev/geometria_rev.json \
     --set agua_costa --out 03_blender/renders/ab/agua_costa/antes \
     --guardar-camaras 03_blender/renders/ab/agua_costa/camaras.json
# 1) trabajo del bloque (kits + integrador) y regeneración:
bash 03_blender/_rev/pipeline_escena.sh 03_blender/_rev/logs_agua          # congela escena_rev.blend nueva
# 2) DESPUÉS con las MISMAS cámaras (sin camara_segura)
bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/capturas_ab.py -- \
     --blend 03_blender/_rev/escena_rev.blend --geom 03_blender/_rev/geometria_rev.json \
     --set agua_costa --out 03_blender/renders/ab/agua_costa/despues \
     --camaras 03_blender/renders/ab/agua_costa/camaras.json
# 3) hojas lado a lado (python del sistema, sin Blender)
python 03_blender/_rev/montaje_ab.py 03_blender/renders/ab/agua_costa
```
Opcional: `--res 1600 900` (defecto), `--solo 49,50` (prefijos), `--etiqueta "agua v1"`.

### 9.5 Esbozo de `03_blender/_rev/capturas_ab.py` (Blender, ~90 líneas)
```python
"""capturas_ab.py - capturas ANTES/DESPUES desde las mismas camaras (congeladas en JSON).
  blender_cola.sh --python capturas_ab.py -- --blend B --geom G --set BLOQUE --out DIR
        [--camaras cams.json | --guardar-camaras cams.json] [--solo 49,50] [--res 1600 900]
Sin --camaras: calcula las tomas con tomas_capturas.construir_tomas (mismas formulas que
renderizar_capturas.py), pasa por camara_segura UNA vez y guarda el resultado en --guardar-camaras.
Con --camaras: usa loc/tgt/lens tal cual (NO camara_segura) y avisa si la camara queda dentro del terreno."""
import argparse, json, os, sys, time
import bpy
from mathutils import Vector
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
ap = argparse.ArgumentParser()
ap.add_argument('--blend', required=True); ap.add_argument('--geom', required=True)
ap.add_argument('--set', default='base'); ap.add_argument('--out', required=True)
ap.add_argument('--camaras'); ap.add_argument('--guardar-camaras')
ap.add_argument('--solo', default=''); ap.add_argument('--res', nargs=2, type=int, default=(1600, 900))
A = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
G = json.load(open(A.geom, encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(A.blend))
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = A.res
os.makedirs(A.out, exist_ok=True)
SETS = {'base': ['01_', '49_', '50_', '51_', '52_', '53_', '54_'],
        'agua_costa': ['02_', '14_', '16_', '22_', '36_roca_casino_general', '46_', '47_', '47b', '60_', '61_'],
        'publico': ['02_', '29_', '30_', '47_', '27_', '28_', '12_', '25_', '62_'],
        'relleno': ['09_', '21_', '26_', '42_', '48_', '10_', '39_'],
        'horizonte': ['14_', '16_', '13_', '08_', '19_', '63_']}
quiero = SETS['base'] + SETS.get(A.set, []) + ([p for p in A.solo.split(',') if p])
if A.camaras:
    cams = json.load(open(A.camaras, encoding='utf-8'))
    tomas = [(n, tuple(c['loc']), tuple(c['tgt']), c['lens']) for n, c in cams.items()]
else:
    import tomas_capturas, camara_segura
    tomas = [(n, *camara_segura.asegurar(n, l, t), k) for (n, l, t, k) in tomas_capturas.construir_tomas(G, bpy)]
tomas = [t for t in tomas if any(t[0].startswith(p) for p in quiero)]
dg = bpy.context.evaluated_depsgraph_get()
log = open(os.path.join(A.out, 'ab.log'), 'a', encoding='utf-8')
guardar = {}
for nombre, loc, tgt, lens in tomas:
    loc, tgt = Vector(loc), Vector(tgt)
    ok, hit, nrm, _i, ob, _m = sc.ray_cast(dg, loc, Vector((0, 0, 1)), distance=3000.0)
    if ok and nrm.z >= 0.0:
        log.write('AVISO %s: camara dentro de %s (no se mueve)\n' % (nombre, ob.name))
    cd = bpy.data.cameras.new('AB_' + nombre); cd.lens = lens; cd.clip_end = 12000
    c = bpy.data.objects.new('AB_' + nombre, cd); c.location = loc
    c.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(c); sc.camera = c
    sc.render.filepath = os.path.join(A.out, nombre + '.png')
    t0 = time.time(); bpy.ops.render.render(write_still=True)
    log.write('%s %.1fs loc=%s\n' % (nombre, time.time() - t0, tuple(round(v, 1) for v in loc)))
    guardar[nombre] = {'loc': list(loc), 'tgt': list(tgt), 'lens': lens}
if A.guardar_camaras:
    json.dump(guardar, open(A.guardar_camaras, 'w', encoding='utf-8'), indent=1)
print('OK capturas_ab', len(tomas), 'tomas ->', A.out)
```
`tomas_capturas.construir_tomas(G, bpy)` = las líneas 45-330 de `renderizar_capturas.py` dentro de una función que
recibe `G` y devuelve la lista (sin abrir blend ni renderizar), más las 4 tomas nuevas 60-63 de §9.2. Es un fichero
nuevo en `_rev/`, no toca el actual.

### 9.6 Esbozo de `03_blender/_rev/montaje_ab.py` (python del sistema + PIL, ~50 líneas)
```python
"""montaje_ab.py - hojas antes/despues:  python montaje_ab.py renders/ab/<bloque> [--etiqueta txt]"""
import os, sys, datetime
from PIL import Image, ImageDraw, ImageFont
D = sys.argv[1]; etq = sys.argv[sys.argv.index('--etiqueta') + 1] if '--etiqueta' in sys.argv else os.path.basename(D)
A, B = os.path.join(D, 'antes'), os.path.join(D, 'despues')
nombres = sorted(n for n in os.listdir(A) if n.endswith('.png') and os.path.exists(os.path.join(B, n)))
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 28)
hoy = datetime.date.today().isoformat()
def par(n, w=960):
    a, b = Image.open(os.path.join(A, n)), Image.open(os.path.join(B, n))
    h = int(a.height * w / a.width)
    a, b = a.resize((w, h)), b.resize((w, h))
    im = Image.new('RGB', (2 * w + 10, h + 44), (24, 24, 24)); dr = ImageDraw.Draw(im)
    im.paste(a, (0, 44)); im.paste(b, (w + 10, 44))
    dr.text((8, 8), 'ANTES  %s' % n[:-4], font=font, fill=(255, 255, 255))
    dr.text((w + 18, 8), 'DESPUES  %s  (%s, %s)' % (n[:-4], etq, hoy), font=font, fill=(255, 220, 120))
    return im
pil, otras = [], []
for n in nombres:
    im = par(n); im.save(os.path.join(D, 'AB_' + n))
    (pil if '_piloto_' in n else otras).append(im)
for grupo, nom in ((pil, 'piloto'), (otras, 'aereas')):
    if not grupo: continue
    H = sum(i.height for i in grupo); hoja = Image.new('RGB', (grupo[0].width, H), (24, 24, 24)); y = 0
    for i in grupo: hoja.paste(i, (0, y)); y += i.height
    hoja.save(os.path.join(D, 'hoja_%s_%s.png' % (os.path.basename(D), nom)))
print('OK montaje', len(nombres), 'pares en', D)
```

### 9.7 Coste y riesgos del sistema
- Por bloque: 2 renders de 13-18 tomas (≈ 45 s cada uno + 5 s de carga) + montaje (< 10 s). Un hueco de la cola.
- Riesgo 1: `escena_rev.blend` lo sobreescribe cada `pipeline_escena.sh`: el "antes" hay que renderizarlo ANTES de
  regenerar (paso 0) o copiar el blend a `_rev/escena_antes_<bloque>.blend` (42 MB; aceptable, borrar al cerrar).
- Riesgo 2: tomas por objeto (`CASINO_root`, `YATE_`, `CAMARA_tierra`, `PIT_boxes`) cambian si el objeto cambia de
  nombre/posición; por eso se congela loc/tgt, no la regla.
- Riesgo 3: el bloque RELIEVE sube el terreno: cámaras congeladas dentro del macizo. El `AVISO` del log lo detecta; la
  decisión (toma nueva con otro nombre) es humana.
- Riesgo 4: `camara_segura` sólo actúa en el "antes" (una vez); así el "después" es comparable.
- Dependencia: ninguna sobre `04_export`. Nuevos ficheros sólo en `_rev/` y `renders/ab/`.

## 10. Qué haría falta para el plan del usuario (cambios concretos, riesgos, dependencias)

Convenciones que condicionan TODO lo de abajo (verificadas en el exportador, `04_export/kn5_writer_opt.py`):
- Las mallas no llevan UV: el KN5 genera UV = coordenadas de objeto × `scale` del `TEX_mapping`, FLAT o BOX, SIN
  offset (387-408). Si una malla trae `uv_layers`, se usa tal cual (394-395). Los colores por vértice NO se exportan.
- Una imagen de color se re-codifica "tintada" a 512 px y nunca > 1024 px (`construir_textura`, 261-263). Un
  degradado de 2.6 km a 1024 px = 2.5 m/píxel: suficiente para batimetría, insuficiente para detalle de orilla.
- Cada objeto = draw calls por slot de material; el proyecto ya pide ≤ 10 slots por coche y "unir filas por material".
- Inspectores que BORRAN o HUNDEN lo que no conocen: `revisar_flotantes.py:43-46` (EXENTOS), `eliminar_sumergidos.py`,
  `asentar_objetos.py:439` (PROT_NO), `integrar_escena.despeje_final` (5947-5950 DESPEJE_*), `_rev/nada_en_pista.py:34`
  (PERMITIDOS) y `04_export/revisar_fisica_ac.py:59-61` (NO_OBSTACULO): cada familia nueva (prefijo) hay que darla de
  alta en esas listas o acabará eliminada, hundida o contada como barrera falsa.
- `04_export` está cerrado por otro equipo: lo que necesite el exportador (CAUSTICS, tokens sin sombra, unión de
  mallas) se entrega como LISTA de peticiones, no como cambios.

### 10.1 Fondo marino con degradado (turquesa en la orilla → azul profundo)
Cambio: generar una TEXTURA batimétrica desde la rejilla final del terreno y mapearla sobre el mar con UV reales.
1. Nuevo paso python (sistema) `03_blender/generar_mar.py`, después de `preparar_geometria.py` y antes de
   `construir_pista.py`: lee `geometria_3d.json['terreno']` (`z`, `mar`, cell 4), calcula `prof = max(0, -z)` y
   `d_costa = distance_transform_edt(mar)·4` (ya se hace así en `terreno_montana.py:1102, 1115`), y escribe
   `03_blender/texturas/mar_color.png` (1024×1024 sobre la caja de la rejilla + 60 m) con una rampa por profundidad y
   distancia: 0-2 m turquesa claro `(0.25,0.75,0.72)`, 2-8 m turquesa `(0.04,0.55,0.60)`, 8-25 m azul medio
   `(0.02,0.36,0.52)`, > 25 m o > 250 m de la costa azul profundo `(0.01,0.22,0.42)`, con ruido suave de 60 m
   (no el de 250 m actual) y una franja de 6-10 m de "espuma" clara en la orilla (`d_costa < 8`).
2. `construir_pista.py:1476-1513`: partir `AGUA` en `AGUA` (rejilla de 32 m sobre la caja del terreno + 60 m, con
   `uv_layers.new()` = (x-x0)/ancho, (y-y0)/alto) y `AGUA_lejos` (anillo hasta 9 km, color profundo plano, 8 quads).
   En `MAT_agua`: Image Texture `mar_color.png` (sRGB) → `TEX_ganancia/TEX_multiplicar` como hace `aplicar_texturas`
   (`crear_cadena_textura`), base color = blanco para que la textura sea EL color; mantener alpha 0.84 + bump; subir
   `Roughness` a 0.08 (hoy 0.04 deslumbra en 54). Mantener `AGUA_fondo` pero con material propio `MAT_fondo_marino`
   (arena oscura, no la rampa del terreno) y, entre -0.5 y -6 m, el `MAT_terreno` ya pinta "fondo marino" (rampa
   107-116): cambiar ese tramo a arena clara `(0.78,0.72,0.55)` para que el agua turquesa se vea sobre arena.
3. Petición a `04_export`: comprobar que `analizar_material` (215-258) toma `mar_color.png` como `img` (necesita
   `n.outputs['Color'].is_linked` y colorspace sRGB, 234-235) y que el tintado de 512 px conserva el degradado; subir
   `TEX_MAX` a 2048 sólo para `MAT_agua`. Opcional CSP: ya hay `Type = SEA`; añadir `[BOUNCED_LIGHT] CAUSTICS = 1`
   (`color_ac.py:862-869`). Sin CSP, el agua es opaca-brillante y el degradado se verá SOLO por la textura.
Riesgos: `aplicar_texturas.py` reconoce la familia por nombre (`familia_de`, 97) y marca `TEXTURIZADO`: coordinar para
que no vuelva a meter su bump encima dos veces; `revisar_flotantes`/`nada_en_pista` ya exentan `AGUA*`
(`AGUA_lejos` también empieza por AGUA). El ruido de olas de `agua_h` (tile 40 m) se nota repetido desde el aire.
Dependencias: el bloque RELIEVE cambia la costa → la textura se regenera con cada pipeline (es un paso, no un asset).

### 10.2 Costa: orilla, playa y rocas
1. `construir_pista.py` (tras el TERRENO, ~1467): malla `COSTA_orilla` = franja de 6 m a cada lado de la isolínea
   `coastF = 0.5` (marching squares sobre `G['terreno']['mar']` suavizado 2 celdas), con 3 materiales por tramo:
   arena mojada oscura (-0.5..0.3), arena clara (0.3..1.5), y "espuma" blanca rota con ruido en el agua (-0.3..0).
   Una sola malla, 1 material por banda → 3 draw calls. Sólo donde la pendiente < 35 % (playas); en acantilados, nada.
2. Rocas de orilla: en `integrar_escena` nueva `zona_costa()` que recorre la isolínea cada 12-20 m y, donde la
   pendiente del terreno > 30 % o a < 60 m del dique/muelles, clona `vegetacion_kit.build_roca` (tam 2-5, 2-4 por
   grupo, media hundida 40 %, color caliza cálida del bloque ROCA) → 300-500 rocas. UNIR por material al final de la
   zona (una malla `COSTA_rocas` por tono) para no disparar draw calls.
3. `MAT_terreno` (92-160): la banda "arena z≈0" (111) pasa a arena de playa sólo si pendiente < 20 % (mezclar por
   normal.z como ya hace el talud 135-149); en acantilado, roca mojada oscura entre 0 y 1.5 m.
Riesgos: la rejilla de 4 m hace la orilla dentada (director 14, 22: "escalera/almenas"): la franja `COSTA_orilla`
suavizada TAPA ese borde (es su principal utilidad). Las rocas deben entrar en `revisar_flotantes` como "marinas"
(referencia = terreno bajo el centro, admitir hundidas 40 %) y en `nada_en_pista.PERMITIDOS` no (están lejos).
Dependencia: RELIEVE (costa final) antes; PALETA (color de la caliza) en paralelo.

### 10.3 Escolleras de bloques (costa, dique y espigón)
1. `puerto_kit.build_dique` (438-479): nuevo parámetro `bloques=True`: malla hija `PUERTO_dique_bloques` con
   600-900 superelipsoides (p 4-6, 1.2-3.0 m, giro aleatorio, 8 seg × 4 anillos ≈ 48 tris) apilados en 2-3 capas
   sobre el talud exterior (offset 4.1..9.0 del perfil) y 1 capa al pie interior, un 30 % bajo el agua; 3 tonos
   `MAT_PUERTO_bloque_a/b/c` (caliza cálida); sombreado plano. ≈ 40k tris en 3 slots. El loft actual se queda (es el
   `1ROAD_` transitable); los bloques son decorado.
2. `caminos_kit.build_camino(tipo='muelle')` (619-644): mismo parámetro `bloques=True` para el faldón de la escollera
   de la carretera del puerto (144 m): `CAMINO_muelle_bloques` hija.
3. Espigón de la cala de la roca del lazo y plataforma de la cala del casino (`roca_lazo.py`, `roca_casino.py`): los
   dueños de esos módulos (otros bloques) deberían usar la MISMA función de bloques: proponer `assets/escollera_kit.py`
   con `build_bloques_a_lo_largo(parent, puntos, ancho, z_agua, seed)` reutilizable por los tres.
Riesgos: `revisar_flotantes` (A-r2-04) toma como referencia marina "la primera obra del puerto bajo el centro": los
bloques son hijos del dique, no raíces → no se inspeccionan (bien). `revisar_fisica_ac` podría ver bloques "vistos por
detrás": sombreado plano con normales hacia fuera (`_MB.to_object` ya recalcula). Vigilar `exportar_ac` DECO sin sombra.

### 10.4 Puerto deportivo con forma de llanta
Hoy: arco de 200° (tapacubos en C) + 3 pantalanes radiales + morros. Para que desde el aire (01, toma nueva 60) se lea
"llanta":
1. `zona_puerto` (1323-1375): BUJE central = isla circular r 16-18 m (`puerto_kit.build_buje`: plataforma de piedra
   z 1.2, pequeño club náutico o faro bajo de 9 m, 4 palmeras) en `PUERTO_INFO['centro']`; 5 RADIOS = pantalanes de
   `R-7-18` m (≈ 120 m) desde el buje a la cara interior del dique cada 40° (190°..350° del marco del dique), barcos a
   ambos lados cada 9 m (misma lógica 1349-1366, con `d_` recorrido desde `R-13` hasta `18+6`); PESTAÑA = segundo
   anillo de pretil con norays y 18 farolas en el paseo del dique (hoy 9); cerrar el arco a 230° y dejar la bocana de
   50 m con dos balizas (roja/verde) en los morros.
2. Para que las posiciones nuevas pasen el filtro `z_terreno < -1.0` (1363), la dársena debe estar dragada: añadir en
   `terreno_montana.construir` (o en `preparar_geometria`) un disco de mar forzado a z -6 de radio `R_DQ+12` en el
   centro del puerto (hoy ya es mar, pero el fondo sube cerca del dique → barcos omitidos: 36 posibles, 41-7=34 puestos).
Riesgos: la carretera del puerto llega al morro a0 (5805-5810): si el arco crece, `fin_d` sigue valiendo (usa
`PUERTO_INFO['a0']`). El buje añade `1ROAD_` si debe ser transitable: NO (el coche no llega): dejarlo decorado y fuera
de `NO_OBSTACULO`. Dependencia: ninguna de otros bloques.

### 10.5 Veleros, yates de varios tamaños y lanchas
1. Marina (`zona_puerto`): sustituir el trío fijo (25/18/12) por un sorteo con 7 tamaños: `puerto_kit.build_yate`
   eslora 14-30 (ya es paramétrico), `build_velero` 9-16 con nuevo parámetro `velas='recogidas'|'izadas'` (vela mayor
   y génova como 2 láminas de 1 cara, `_lamina`), `yates_kit.build_lancha` 7-11 (2k tris, con `n_coches=0` nuevo) y 4-6
   `yates_kit.build_yate(26-40, con_publico=False)` en los amarres exteriores. Variación de color: `build_yate` acepta
   `color_franja`/`color_bimini` (3-4 tonos) → materiales `MAT_PUERTO_casco_<HEX>` reutilizados.
2. Bahía: 7 veleros sueltos → 10-14 con velas izadas y rumbo coherente (todos escorados al mismo viento, ±15°), 3-4
   lanchas "navegando" con estela (lámina blanca de 12 m detrás, alpha): se ven desde 54 y desde el viaducto.
3. Yates VIP: los 2 huecos que no se colocaron (`_agua` < -1.8) se recuperan con el dragado del punto 10.4.2.
Riesgos: presupuesto. Hoy la marina pesa < 36×5k = 180k tris; con 6 yates de `yates_kit` sin público (+54k) y velas
(+2k) sigue por debajo de 250k. Las lanchas de `yates_kit` traen coches (3.5k tris cada uno): pedir `n_coches=0`.
CSP (punto 9 del plan): barcos animados = `[ANIMATED_...]`/`[MODEL_REPLACEMENT]` en `ext_config`: fuera de alcance aquí;
basta con que cada barco sea un objeto con nombre único (`YATE_*`, `PUERTO_yate.00N`) para que el otro equipo lo anime.

### 10.6 10-12 tipos de coche espectador con variación, y dónde ponerlos
Los TIPOS ya existen (9 de `coches_kit_v2` + limusina/cabrio/deportivo de `yates_kit` = 12). Lo que falta es
VARIACIÓN visible y, sobre todo, SITIOS: hoy 1 fila de 6.
1. `coches_kit_v2.build_coche`: opción nueva `bandera` (mástil en la ventanilla o el techo + banderola tricolor/WGP/
   cuadros, 24 tris, materiales existentes `piloto`/`blanco`/`verde` → añadir `MAT_COCHE_verde_bandera`), opción `ojos`
   (`iris` ya variable; añadir `mirada=(du,dv)` como en `_pub_coche`) y en `build_fila_aparcada` escala 0.92-1.08 por
   coche (`ob.scale`) además del giro ±6° (ya existe) → 9 tipos × 10 colores × 3 expresiones × 4 bocas × bandera/no.
2. `zona_coches` (2339-2433): el filtro `sitio_ok` no encuentra sitio en el macizo. Sustituir por APARCAMIENTOS
   explanados: 8-12 losas de grava 30×14 m (`explanar()` 785 + cinta de tierra `_camino(tipo='tierra')` de acceso con
   valla `_empalme`, exactamente como `_ramal_camara`/`poner` de `zona_camaras` 6088-6166) en los exteriores de curva a
   16-30 m del borde, 2-3 filas de 6 por losa → 150-200 coches con cara. Muro de piedra seca (`ITAL_bancal_muro`) en
   el borde bajo de cada losa para que no sea una "caja suelta" (director 07/48).
3. Balcones: `casas_kit_v2` debe exponer la lista de balcones (`info['balcones'] = [(x,y,z,rot)]` por casa); el
   integrador pone 1 topolino/compacto (escala 0.85) en el 25 % de los balcones que miran a la pista (<= 40 m).
   DEPENDE del bloque PUEBLO (atlas de fachadas): hacerlo después.
4. Terraza del casino: 10-16 `yates_kit.build_coche_lujo` en la meseta (`roca_casino` `info['centro_top']`,
   RONDA15_PLAN.md:158) mirando a la pista, con mesas y sombrillas del mismo kit (`_mesa_alta`, `_sombrilla`, 815-850).
5. Yates: ya llevan público; subir `n_coches` a 6-8 en los 3 de la recta.
6. Ladera (tierra, s 1300-2200 exterior): nuevo `assets/camping_kit.py`: `build_autocaravana(seed)` (coche grande
   con cara, techo blanco, toldo, 2.5k tris), `build_tienda(seed)` (iglú/canadiense 2 colores, 120 tris),
   `build_campamento(n, seed)` (3-5 unidades + hoguera + nevera + banderín), 6-10 campamentos sobre mini-explanadas
   (`explanar` r 9 m) con sendero de tierra a la pista o al sendero de montaña más cercano.
7. Público de gradas (`_pub_coche`, 350-480): subir de 4 a 6 siluetas (pickup, furgoneta alta), 8 → 10 colores,
   bandera en el 20 % (16 tris) y 2 escalas más: ≈ +25 tris por coche, +20k por grada. `pit_kit` usa la misma función
   (353+): mismo cambio.
Riesgos: draw calls (200 coches × ≤ 10 slots): pedir a `04_export` la unión por material de cada `COCHE_fila`
(coches_kit_v2 docstring 34-35 ya lo advierte). `despeje_final` (5950) trata `COCHE_` como prop desechable: los
aparcamientos nuevos deben llevar su losa en `EDIF_PREF` o quedar fuera de los ejes. `revisar_coches.py` asienta cada
coche en el terreno (1-36): las losas explanadas deben estar en la malla TERRENO antes (orden: explanar → clonar →
revisar_coches ya lo hace así).
Dependencias: RELIEVE (explanadas sobre el macizo final), PUEBLO (balcones), CASINO (meseta).

### 10.7 Bancales, viñedos, villas, aparcamientos, carpas, torres costeras y faro
1. Bancales: `italiano_kit.build_bancal` vale; lo que falla es la colocación "bandeja suelta". Nuevo paso python
   `03_blender/bancales_spec.py` ANTES de `preparar_geometria.py` (como `urbanismo_spec.json`): elige 6-10 laderas de
   pradera (pendiente 10-35 %, sin pista a < 40 m, sin solares de `urbanismo.json`, sin senderos) y escribe polilíneas
   por curva de nivel cada `alto` 1.6-2.2 m; `terreno_montana.construir` las TALLA (escalón real en la rejilla, como
   las terrazas del pueblo, 78-80 de RONDA15_PLAN) y `integrar_escena.zona_bancales` clona `build_bancal` por tramos de
   14-20 m con olivos (`sin_olivos` donde cruza un camino) → 40-80 bancales. Así el muro apoya en su escalón.
2. Viñedos: `italiano_kit.build_vinedo(largo, filas, paso=2.4, seed)`: postes + 2 alambres (cilindros de 4 lados) +
   cepas (2 esferas aplastadas de 6 seg, 2 verdes) → ≤ 35 tris/m lineal; 4-6 parcelas de 40×30 m en laderas < 15 %
   cerca del pueblo y del hotel; tierra ocre entre hileras (losa con `MAT_ITAL_tierra`).
3. Villas con piscina: `assets/villa_kit.py` `build_villa(seed)` (2 plantas 12×9, cubierta de teja, pérgola, muro
   bajo, piscina 8×4 `agua_piscina` de `yates_kit`, 2 cipreses, 1 coche de lujo aparcado) ≤ 6k tris; 6-10 villas en
   laderas que miran al mar (sector casino y retorno), cada una sobre su explanada (`explanar`) con acceso de tierra.
4. Carpas de hospitality: `carrera_kit_v2.build_carpa(largo=16, ancho=10, color)` (lona a dos aguas con faldón,
   banderas WGP, mesas) 6-8 en el paddock (detrás de `PIT_boxes`, zona 5516-5670 de `zona_caminos` 3) y detrás de la
   tribuna interior; todas sobre terreno explanado (`explanar_edificios`).
5. Torres costeras: `italiano_kit.build_torre_costera(alto=11)` (torreón cilíndrico de piedra con base ataluzada,
   almenas, puerta elevada, 1.5k tris): 3 en promontorios: sobre el espolón del casino, en la cumbre (-381, 432) y en
   la roca del lazo (consensuar con T3). Faro 2: faro pequeño (`build_faro` escala 0.6, bandas negras) en la punta de
   la cala de la roca del lazo o en el morro a0 (hoy el a0 tiene la escollera: usar a0 sólo si queda el morro libre).
6. Aparcamientos llenos: 10.6.2 + el `MIRADOR_parking` ya existente.
Riesgos: todo lo nuevo son RAÍCES nuevas con prefijo nuevo (VILLA_, CARPA_, CAMPING_, ITAL_vinedo, ITAL_torre): darlas
de alta en `revisar_flotantes.EXENTOS`/`SOPORTE_PREF`, `asentar_objetos`, `despeje_final.EDIF_PREF` (5947) y en
`exportar_ac` (muros de villa → 1WALL si el coche puede llegar; carpas en el paddock sí: `1WALL_carpa`). Presupuesto:
+300-400k tris en total; agrupar por material dentro de cada kit (una malla por villa/carpa).
Dependencias: RELIEVE (bancales tallados y explanadas), VEGETACIÓN (olivos/cipreses nuevos de TreeFX sustituyen a los
`ITAL_olivo` de los bancales: dejar `sin_olivos` o `olivos=False`).

### 10.8 Anillo de horizonte (costa y montañas lejanas)
1. Reactivar el gancho `zona_montanas_fondo` (2486-2533) como `zona_horizonte`: en vez de `return` cuando hay
   cumbres, construir un ANILLO: 7-9 cordilleras `montanas_fondo_v2.build_cordillera(largo 1400-1800, n_picos 5-7,
   alto 380-520, linea_arboles > 1 para las cercanas, pie=True)` colocadas sobre un arco de radio 3.2-4.5 km centrado
   en el centro del terreno, cubriendo 200° (N, E y O; abierto al S/SO, por donde la bahía y el viaducto miran al mar
   abierto), con 2 planos de profundidad (fila 3.2 km baja y verde-azulada, fila 4.5 km alta y gris-azul) y 6-8 lomas
   de costa (`build_loma`) a 2.4-2.8 km que hagan de "orilla lejana" con 2-3 pueblecitos-silueta (cajas crema de
   30×10×8 m, 20 por pueblo, un material) y 1 faro lejano.
2. Materiales: `MAT_MONT_*` ya los recolorea `aplicar_texturas` (familia `roca`/`bosque`, 87-92); añadir en
   `mejorar_materiales.py` una mezcla con el color del cielo del horizonte `(0.70,0.84,0.98)` al 35-55 % según la
   distancia (perspectiva atmosférica horneada en el color: en AC sin CSP no hay niebla de distancia fiable).
3. Geometría: el pie de los picos baja a z -6 (`pie=True`), por debajo de `AGUA_fondo` (-4.05): sin huecos. Las
   cámaras tienen `clip_end 12000`: entra. En AC: añadir a la petición de `04_export` el token `HORIZ`/`MONT_` en
   `SIN_SOMBRA_TOKENS` y DECO sin colisión; presupuesto total ≤ 250k tris (7 cordilleras × ≤ 60k → usar `res 0.5`).
Riesgos: el anillo tapa la línea mar/cielo en las aéreas (01 pierde el "mar infinito"): es lo que pide el usuario, pero
hay que mirar 54 y 14 (viaducto): desde ahí debe seguir viéndose mar abierto → abertura S/SO de 160°. `eliminar_
sumergidos` podría borrar los picos cuyo origen esté a z 0 sobre mar: exentar `MONT_` (ya está `MONT_pena` en
`revisar_flotantes.EXENTOS`, línea 43: ampliar a `MONT_`).
Dependencias: ninguna (se puede hacer el primero y da contexto a todas las capturas).

### 10.9 Orden sugerido dentro de este bloque y qué medir
1. Sistema de capturas A/B (§9) — 1 sesión; sin él no se puede juzgar nada de lo demás.
2. Horizonte (10.8) — independiente, cambia todas las aéreas y las de piloto que miran al mar (49, 52, 54).
3. Agua: textura batimétrica + AGUA con UV (10.1) y orilla/rocas (10.2) — tras el RELIEVE del bloque 1 (la costa cambia).
4. Puerto llanta + bloques + flota (10.3, 10.4, 10.5) — módulos propios, se prueban con `test_puerto_kit.py` y previews.
5. Público (10.6) y relleno (10.7) — después de PUEBLO y RELIEVE (balcones, explanadas, bancales tallados).
Medidas automáticas por bloque (además de las hojas A/B): nº de barcos colocados vs posibles (log de `zona_puerto`),
nº de coches con cara y nº de filas (log de `zona_coches`), tris totales por familia (`asentar.json['por_familia']`),
y las comprobaciones de siempre: `revisar_flotantes`, `nada_en_pista`, `revisar_fisica_ac` (barreras falsas = 0),
`kn5_check.py`.

### 10.10 Peticiones a `04_export` (para el equipo que cierra el zip, no para hacerlas ahora)
- `TEX_MAX` 2048 para `MAT_agua` y comprobar que el degradado sobrevive al tintado de `construir_textura`.
- `[BOUNCED_LIGHT] CAUSTICS = 1` en `EXT_AGUA` (`color_ac.py:862`), siempre como extra CSP.
- Unión por material de `COCHE_fila*`, `PUERTO_dique_bloques`, `COSTA_rocas`, `HORIZ_*` (draw calls).
- Tokens sin sombra: `HORIZ`, `MONT_` (`kn5_writer_b.py:41`, `kn5_writer_opt.py:75`).
- Nuevos prefijos en `revisar_fisica_ac.NO_OBSTACULO` (COSTA_, HORIZ_, CAMPING_, VILLA_ decorativos) y `1WALL_` para
  carpas del paddock y muros de villas alcanzables.
