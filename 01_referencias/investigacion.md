# PORTO CORSA (Cars 2, 2011) — Documento de referencia para el mod de Assetto Corsa

Documento único de trabajo. Sintetiza cuatro investigaciones (trazado, entorno, desniveles, pipeline, mods existentes). Todo dato "deportivo" (curvas, vueltas, tiempos) procede de wikis de fans derivadas de fotogramas de la película: no hay ficha oficial de Pixar con longitud ni sentido de giro. Donde hay que decidir, este documento decide.

---

## 1. El circuito y su trazado

### 1.1 Contexto
- Ciudad costera FICTICIA de la Riviera italiana ("la Gema de la Riviera"), sede de la 2.ª carrera del World Grand Prix y ciudad natal de Francesco Bernoulli. En Italia el evento se rotula **"Mondiale Grand Prix"** (usar ese texto en vallas y pórticos).
- Diseño de Pixar: **trazado de Mónaco + terreno de la Costa Amalfitana**, con inspiración de Portofino, Porto Cervo, Vernazza, Positano, Génova y Montecarlo.
- Carrera de la película: 60 vueltas, día soleado, 11 coches, Francesco en pole; gana McQueen por 0.033 s (55:18.000). El accidente masivo ocurre en el Puente del Casino.

### 1.2 Cifras de trabajo (fan-derivadas, adoptadas como canon del mod)
| Dato | Valor | Fuente/nota |
|---|---|---|
| Curvas | ~50-51 (13 de tierra, 17 "técnicas") | Pixar Cars Wiki (dpcarswiki dice 50; discrepan) |
| Longitud | SIN dato oficial. Decisión: **diseñar para vuelta de ~55 s con hypercar ≈ 2,5-3,5 km** | 60 vueltas en 55:18 → ~55,3 s/vuelta (cálculo propio) |
| Sentido | No documentado. Decisión: **fijarlo al replantear el mapa fan sobre la secuencia puerto→subida→tierra→casino→puerto** y mantenerlo en todo el proyecto | El mapa fan SVG no lleva flechas |
| Superficie | Asfalto + sección larga de TIERRA (13 curvas) | Única pista WGP con tierra en ladera |
| Chicane final | Sí, justo antes de meta | |

### 1.3 La vuelta, sector a sector (orden documentado: puerto → subida → cima → bajada → casino → puerto)
1. **S1 - Recta de meta / puerto (nivel del mar).** Recta ancha junto al agua, 4 tribunas, zona de prensa/podio, 2 pantallas gigantes en la grada del mar, yates detrás, pit lane con 12 boxes. Curva 1 al final.
2. **S2 - Subida del acantilado (curvas ~1-2).** "The climb section after turn 1": cornisa panorámica sobre muro de mampostería a media altura del acantilado este, con arco natural de roca que hace de túnel y una rueda fósil gigante tallada en la pared. ~2 coches de ancho.
3. **S3 - Calles del pueblo en subida (curvas ~3-10, técnicas).** Calles estrechas y sinuosas "parcialmente pavimentadas", entre fachadas estilo Portofino, con puentes en arco.
4. **S4 - Sección de TIERRA en la ladera (curvas ~11-25). Punto más alto.** Lazo de montaña con 13 curvas de tierra: horquilla de 180° en la cima (c.18) y switchbacks en eses (14-16 y 19-25). "El gran igualador" según la retransmisión; terreno de Raoul ÇaRoule.
5. **S5 - Descenso al pueblo (curvas ~26-30) + recta rápida cuesta abajo.**
6. **S6 - Sector "Mónaco" / casino (curvas ~31-41).** Chicanes 31-33, repecho 35-36 y la **horquilla de la c.38** (copia de la Loews/Fairmont de Mónaco): 180° descendente alrededor de un parterre circular elevado con palmeras. Nota importante: según la trivia de la wiki, el modelo 3D real de Pixar ("Finding Porto Corsa") NO tiene las curvas cerradas que el mapa fan dibuja justo antes de esta horquilla — **omitirlas**.
7. **S7 - Puente del Casino (curvas ~41-45).** Viaducto de arcos de piedra que RODEA el peñón del casino (peñón con forma de capó de Fiat 500 Topolino de 1948); es el mayor de los TRES puentes del peñón. El trazado cruza el agua dos veces (ida y vuelta al peñón) y desciende ("bajan como un tobogán" tras el puente). Escenario del accidente.
8. **S8 - Retorno y chicane final (curvas ~46-50).** Rectas costeras rápidas de vuelta al puerto y chicane antes de la línea de meta.

**El trazado NO se cruza sobre sí mismo** (verificado en el mapa fan): bajada 25-30 y retorno 46-50 corren paralelos; los únicos pasos sobre agua son los puentes al peñón.

### 1.4 Referencias cartográficas
- Mapa fan del circuito (base de replanteo): https://static.wikia.nocookie.net/worldofcarsdrivein/images/2/28/Porto_Corsa_Map.svg/revision/latest?cb=20210416142955
- Layout con curvas numeradas y secciones por color (rojo=rectas, azul=técnicas, amarillo=tierra, blanco=puentes): https://static.wikia.nocookie.net/worldofcarsdrivein/images/6/65/Layout_Porto_Corsa_Grand_Prix.svg/revision/latest
- Modelo oficial a vista de pájaro (making-of): https://pixarcars.fandom.com/wiki/File:Italytrackmodel_reference.png
- Wikis: https://pixarcars.fandom.com/wiki/Porto_Corsa · https://pixarcars.fandom.com/wiki/Porto_Corsa_Grand_Prix · https://dpcarswiki.com/Porto_Corsa · https://disney.fandom.com/wiki/Porto_Corsa

---

## 2. Entorno: assets a modelar, por prioridad

Estilo global: Riviera italiana "de lujo" — tejados de terracota, fachadas ocre/amarillo/salmón/rosa/crema con persianas verdes, piedra clara en puentes, mar turquesa, todo limpio y saturado (cita del diseñador Harley Jessup). Mundo "car-ificado": marina con forma de tapacubos, chimeneas-tubo de escape, dados peludos en el casino.

### Prioridad A — Hero assets (definen el circuito; modelar primero)
1. **Casino di Porto Corsa**: estilo Belle Époque / Casino de Montecarlo; fachada blanco-crema con dorados, cúpulas verdosas, columnatas, escalinata. Mater: "parece hecho de oro". (https://pixarcars.fandom.com/wiki/Casino_di_Porto_Corsa)
2. **Peñón Topolino**: promontorio rocoso con la silueta del capó de un Fiat 500 Topolino de 1948; caliza gris-ocre con vegetación colgante.
3. **Puente del Casino**: gran viaducto de arcos de piedra clara (estilo acueducto romano) con balaustradas y banderolas; + **2 puentes arqueados menores** (los tres unen el peñón a tierra).
4. **Marina-tapacubos**: dique circular que dibuja una rueda vista desde arriba, pantalanes radiales como radios de llanta.
5. **Municipio (ayuntamiento)**: palazzo con torre/reloj junto a la marina, logo Fiat.
6. **Hotel di Porto Corsa**: grand hotel crema con toldos y balcones frente al mar.

### Prioridad B — Kit modular de ciudad (rellena el 80% del recorrido)
7. Bloques de casas estilo Portofino/Vernazza: 4-6 plantas, estuco de colores, persianas verdes, trompe-l'oeil, teja de terracota, balcones de forja, tendederos.
8. Chimeneas con forma de tubo de escape (detalle firma para tejados).
9. Bajos comerciales con rótulos italianos: **Café di Porto Corsa** (terraza donde vigilan Finn y Holley), **Café Frizione**, **Fluido Enogastronomia**, **Carmani** (parodia de Armani: boutique de calandras), **Moda Motore**, heladerías/enotecas genéricas con toldos rayados.
10. Iglesia/campanile ligur para el skyline (opcional).

### Prioridad C — Infraestructura de carrera WGP (lo que la hace "circuito")
11. Pórtico de salida-meta "Mondiale Grand Prix" con semáforos.
12. Cuatro tribunas llenas de coches-espectador; la del mar con DOS pantallas gigantes.
13. Pit lane con 12 boxes numerados y logos de los 11 equipos; muretes y utillaje de mecánicos.
14. Publicidad **Allinol** (verde/blanco) en vallas, puentes y banderolas verticales; parodias REVIOLI, CARBONARA, FORZA en muros de la horquilla.
15. Barreras tipo Mónaco: muro bajo + valla de captura con paneles publicitarios; pianos rojo-blancos; balas de paja opcionales en la tierra.
16. Zona de prensa y podio; torres de cámara TV; carteles del GP por la ciudad; mascota Globie opcional.

### Prioridad D — Puerto y mar
17. Hilera de yates blancos (genéricos, sin ojos si se prefiere neutralidad), veleros, lanchas; pantalanes, norays, boyas, defensas; faro/baliza en el dique.
18. Shader de agua: turquesa cerca de costa con transición a azul profundo, espuma al pie de acantilados; pequeñas calas de arena.

### Prioridad E — Terreno y vegetación
19. Acantilados estilo Amalfi (estratos calizos ocre-gris) con la carretera colgada a media ladera; colinas de fondo con villas dispersas y bancales de limoneros/viñedos.
20. Sección de tierra: camino compactado, polvo, muretes de piedra seca, arbustos.
21. Túnel/galería en roca estilo Mónaco (presente también en el videojuego).
22. Palmeras (paseo marítimo y casino), cipreses, pinos parasol, olivos, adelfas, buganvillas, setos formales.

### Prioridad F — Mobiliario y detalle
23. Pavimentos: sampietrini/adoquín en el casco antiguo, asfalto en pista, escalinatas.
24. Balaustradas de piedra y miradores en la cornisa; farolas de fundición, fuentes, bancos a escala coche, terrazas con sombrillas.
25. Rotulación italiana genérica y publicidad vintage; ambulancias/grúa como atrezzo estático; banderines cruzando calles.

**Iluminación**: sol alto mediterráneo, sombras nítidas, cielo despejado, temperatura cálida sobre fachadas ocres; multitudes de coches-espectador en gradas, balcones y azoteas.

Fuentes clave: https://pixar.fandom.com/wiki/Porto_Corsa · https://la411.com/blog/post/a-world-of-research-aids-cars-2-production-design · https://www.wearemoviegeeks.com/2011/05/pixars-25th-anniversary-cars-2-going-global/

---

## 3. Desniveles y carácter de cada sector

### 3.1 Perfil de elevación (esquema para el blockout)
```
Puerto (0 m) → subida FUERTE en cornisa (lado este) → pueblo en pendiente →
ladera de TIERRA con horquilla y switchbacks (COTA MAXIMA) → bajada rápida →
recta descendente → repecho al sector casino → horquilla Mónaco T38 en alto →
bajada al viaducto del Casino (cota media, sobre el mar) → lazo alrededor
del peñón (túneles/arcos) → chicane → puerto (0 m)
```
Dos cruces sobre el mar (puentes), ningún cruce del trazado sobre sí mismo. El viaducto desciende (el pelotón accidentado "se desliza cuesta abajo").

### 3.2 Carácter, anchura y barreras por sector (del análisis visual del film)
| Sector | Carácter | Anchura | Barreras |
|---|---|---|---|
| Recta del puerto | Muy rápida, escenográfica | ~5-6 coches + pit lane | Muro bajo + valla de captura alta con paneles "Mondiale Grand Prix"; tribunas a ambos lados |
| Cornisa del acantilado | Subida rápida y estrecha, vértigo | ~2 coches | Parapeto de piedra bajo o borde al vacío; pared de roca interior; SIN Armco |
| Calles del pueblo | Técnicas, revirado en subida | ~2-2,5 coches | Fachadas, muros de piedra y terrazas como barrera natural |
| Tierra (sterrato) | Igualador; horquilla en cima + eses | ~2-2,5 coches | Muretes de piedra seca, balas de paja opcionales |
| Descenso + recta | Rápido, cuesta abajo | ~3 coches | Muros/vegetación |
| Sector casino / T38 | Lento y técnico, estilo Mónaco | ~2,5-3 coches | Muros bajos rojo-blancos con publicidad (REVIOLI, CARBONARA, FORZA) + barandilla; pianos en ambos bordes; zigzag amarillo pintado en la frenada; muro tipo castillo exterior; línea discontinua central (calle pública) |
| Viaducto del Casino | Medio-rápido, descendente, sobre el mar | ~3 coches | Pretil sólido de piedra-hormigón (Carla Veloso patinó contra él); guardarraíl y farolas en el tramo urbano |
| Chicane + meta | Frenada fuerte final | ancha | Muro + valla de captura |

### 3.3 Apuntes del videojuego (Cars 2: TVG) — usar con criterio
- El juego confirma la lógica de elevación (puerto a nivel del mar, túnel bajo casino/hotel, switchbacks apilados a 3-4 alturas con muros de contención, horquilla en promontorio, viaducto de fondo), pero sus pistas son 4-5 carriles con saltos y turbos: **anchura y saltos del juego NO se trasladan al mod** (seguir el film). El logro "ISLAND HOPPER" (atajo saltando a una isleta) es exclusivo del juego.
- Barreras del juego (alternativa estética si falta referencia fílmica): Armco gris-azul con bolardos blancos, muretes amarillo-negro en horquillas de montaña, muros con hiedra en el pueblo.
- Pistas: Harbor Sprint, Mountain Run (espejo de Harbor Sprint), Casino Tour (reciclada en Cars 3: Driven to Win como "Italy's Grand Tour"), Italy Arena. https://cars-2-the-video-game.fandom.com/wiki/Italy

---

## 4. Pipeline técnico Blender → kn5 (sin AC instalado)

### 4.1 Decisiones concretas
| Decisión | Elección | Motivo |
|---|---|---|
| Exportador KN5 | **jwl-7/blender-assetto-corsa-tools v1.0.7** (fork activo, min Blender 3.0, era 4.x) | Exporta KN5 directamente sin juego ni ksEditor; materiales vía settings.json; tangentes correctas; convierte fbx.ini→settings.json. https://github.com/jwl-7/blender-assetto-corsa-tools |
| Plan B exportación | Blender 3.6 LTS portable SOLO para exportar (modelar en Blender moderno) o fork moppius v0.2.0 | Si jwl-7 fallara en vuestro Blender. https://github.com/moppius/blender-assetto-corsa-tools |
| IA y cámaras offline | **leBluem/io_import_accsv v2.8.0** (Blender 2.80+): dibujar la trazada como curva y exportar fast_lane.ai, sidelines .csv y cameras.ini | 100% sin juego. https://github.com/leBluem/io_import_accsv (alternativa web: https://trecorsa.com/docs/?cat=ailines) |
| Fallback total | FBX + ksEditor en el PC del amigo (assettocorsa/sdk/editor/ksEditor.exe) con persistencia .fbx.ini versionada | Solo si el kn5 de Blender diera problemas de shaders. |
| Descartado | LKOLA/blender-kn5-addon | Solo coches, no circuitos. |

### 4.2 Reglas de modelado en Blender (aplicar desde el blockout)
- Escala en metros. Malla visual detallada SEPARADA de mallas físicas low-poly.
- **Mallas físicas**: prefijo numérico + KEY: `1ROAD_puerto`, `2ROAD_pueblo`, `1KERB_t38`, `1GRASS_x`, `1SAND_escapatoria`, `1WALL_muros`, `1DIRT_ladera`. El nombre tras el dígito debe EMPEZAR por la KEY de surfaces.ini. ROAD/KERB/GRASS/SAND funcionan sin definición propia; DIRT es custom y exige entrada en data/surfaces.ini.
- **Objetos lógicos como MALLAS diminutas (NO empties — el exportador ignora no-mesh)**; su posición y orientación definen el spawn: `AC_START_0..N` (parrilla), `AC_PIT_0..11` (12 boxes, debe cuadrar con ui_track.json), `AC_HOTLAP_START_0`, `AC_TIME_0_L`/`AC_TIME_0_R` (meta) + `AC_TIME_1_L/R`, `AC_TIME_2_L/R` (sectores).
- Mínimo viable para probar: `1ROAD_x` + `AC_START_0` + `AC_PIT_0` + `AC_HOTLAP_START_0` + `AC_TIME_0_L/R`.
- Probar el pipeline completo con un óvalo de test ANTES de modelar en serio.

### 4.3 surfaces.ini — superficie DIRT recomendada (sección de tierra)
```ini
[SURFACE_0]
KEY=DIRT
FRICTION=0.78          ; tierra "rápida" (rango útil 0.7-0.85)
DAMPING=0.05
WAV=gravel.wav
WAV_PITCH=1.0
FF_EFFECT=NULL
DIRT_ADDITIVE=0.3      ; bajo a propósito: la sección es larga y valores altos arruinan neumáticos
IS_VALID_TRACK=1
BLACK_FLAG_TIME=0
SIN_HEIGHT=0.02        ; bacheado suave
SIN_LENGTH=1.5
IS_PITLANE=0
VIBRATION_GAIN=0.2
VIBRATION_LENGTH=0.4
```
Referencia: https://site.hagn.io/assettocorsa/modding/tracks/data/surfaces-ini · https://assettocorsamods.net/threads/how-to-use-surfaces-in-surfaces-ini.1683/

### 4.4 Estructura de carpeta del mod
```
content/tracks/porto_corsa/          <- kn5 principal = nombre de carpeta, minúsculas
  porto_corsa.kn5                    (obligatorio)
  models.ini                         (solo si hay varios kn5/layouts)
  map.png                            (provisional: render cenital ortográfico de Blender)
  data/
    surfaces.ini                     (OBLIGATORIO por DIRT custom)
    map.ini                          (CM lo genera)
    lighting.ini                     (sol mediterráneo alto)
    cameras.ini                      (opcional; exportable desde io_import_accsv)
    crew.ini                         (opcional)
  ui/
    ui_track.json                    (OBLIGATORIO: name, country=Italy, length, pitboxes=12, run, author...)
    preview.png
    outline.png
  ai/
    fast_lane.ai                     (necesaria para IA; el circuito carga en Practice sin ella)
    pit_lane.ai
```

### 4.5 Flujo de trabajo completo
1. Blockout del trazado en Blender sobre el mapa fan SVG corregido (quitar las curvas fantasma pre-horquilla, §1.3.6), apuntando a vuelta de ~55 s.
2. Instalar jwl-7 (ZIP de release), exportar cubo+plano de prueba a KN5, verificar el flujo antes de modelar.
3. Modelar por sectores con las convenciones de §4.2; materiales AC (ksPerPixel, ksMultilayer, ksTree, ksGrass...) en settings.json; texturas tipo Imagen (quedan embebidas en el kn5).
4. Montar la carpeta de §4.4; fast_lane.ai provisional dibujada con io_import_accsv.
5. **En el PC del amigo (validación)**: copiar a content/tracks; probar en Practice; grabar IA definitiva con dev apps (`ENABLE_DEV_APPS=1` en system/cfg/assetto_corsa.ini → app "AI" → vuelta limpia → renombrar fast_lane.ai.candidate; "start pits" para pit_lane.ai); sidelines con "AI Line Helper" (https://www.overtake.gg/downloads/ai-line-helper.16016/); map.png/map.ini/outline con Content Manager; fallback ksEditor solo si hay problemas de shaders (guía: https://www.sim-garage.co.uk/working-with-kseditor-the-assetto-corsa-editor/ · modded: https://ascobash.wordpress.com/2015/07/22/kseditor/).

Guías generales: https://assettocorsamods.net/threads/build-your-first-track-basic-guide.12/ · https://assettocorsamods.net/threads/overview-elements-ac_xxxxx.2471/ · https://site.hagn.io/assettocorsa/modding/tracks · https://vosan.co/apps/blender-assetto-corsa-tools

---

## 5. Mods y referencias existentes

### 5.1 Estado del arte: el terreno está libre
- **NO existe ningún mod de Porto Corsa para AC** (comprobado en overtake.gg, AssettoWorld —4.692 pistas indexadas—, Assettoland, YouTube). Hay demanda no atendida: hilo "Pixar's Cars 2 mods" activo de 2022 a 2026 pidiendo exactamente esto sin respuesta. https://www.overtake.gg/threads/pixars-cars-2-mods.251490/
- Sí existen COCHES de Cars para AC (Lightning McQueen Realistic Mod, MLZ McQueen, Mater, Jackson Storm...): público objetivo natural del circuito. https://www.overtake.gg/downloads/lightning-mcqueen-realistic-mod.82507/ · https://www.assettoworld.com/car/mlz-lightning-mcqueen
- No hay modelos 3D descargables de la ciudad (Sketchfab/Models Resource: solo personajes ripeados). **Modelar desde cero es la única vía.**

### 5.2 Plan de referencias visuales
1. **Película**: secuencia completa de la carrera de Italia (fotograma a fotograma para barreras, anchuras, publicidad). Transcript: https://pixarcars.fandom.com/wiki/Cars_2/Transcript
2. **Making-of "Finding Porto Corsa"**: modelo cenital oficial del circuito (la referencia de layout más fiable).
3. **Cars 2: The Video Game** (3 pistas de Porto Corsa jugables) para geometría de túneles, switchbacks y casino; capturas: https://cars-2-the-video-game.fandom.com/wiki/Casino_Tour · Harbor_Sprint · Mountain_Run. Herramientas de ripeo SOLO como referencia visual: https://modcars.fandom.com/wiki/Tools
4. **Wikis** para monumentos: https://pixarcars.fandom.com/wiki/Casino_di_Porto_Corsa y las páginas de Porto Corsa (pixar/disney/pixarcars/dpcarswiki).
5. **Geografía real**: Mónaco (horquilla Fairmont, túnel, barreras urbanas) + Portofino/Vernazza/Positano (paleta, puerto, acantilados).
6. Curiosidades de apoyo: diorama slot "Porto Corsa Project" con fotos de construcción (https://www.slotforum.com/threads/porto-corsa-cars2-project.56691/); recreación del WGP en AC con circuitos sustitutos (https://www.youtube.com/watch?v=p0008Ebc87Y).

### 5.3 Capturas concretas ya localizadas (barreras y sectores del film)
https://static.wikia.nocookie.net/worldofcarsdrivein/images/2/27/Porto_Corsa_hairpin.jpg/revision/latest (horquilla T38) · https://static.wikia.nocookie.net/worldofcarsdrivein/images/9/94/Portocorsacircuit2.jpg/revision/latest · https://static.wikia.nocookie.net/worldofcarsdrivein/images/0/09/Portocorsacircuit3.jpg/revision/latest · https://static.wikia.nocookie.net/worldofcarsdrivein/images/7/7b/Porto_Corsa3.jpg/revision/latest · Vistas del juego: https://static.wikia.nocookie.net/cars-2-the-video-game/images/8/8a/Harbor_Sprint_-_VIEW_1.jpeg/revision/latest · https://static.wikia.nocookie.net/cars-2-the-video-game/images/6/62/Casino_Tour_-_VIEW_1.jpeg/revision/latest

---

## Apéndice: advertencias de fiabilidad
- Las wikis discrepan entre sí (51 vs 50 curvas; sector Mónaco en c.38-49 vs c.28-38). Este documento adopta la numeración de Pixar Cars Wiki (38-49) por coherencia interna.
- El mapa fan SVG añade curvas que no existen en el modelo oficial de Pixar (antes de la horquilla Mónaco): corregir en el blockout.
- No usar como referencia la vuelta récord de Roblox (2:50) ni la pista de slot Carrera (5,4 m a 1/43): no representan el circuito ficticio.
- El emisor AC_AUDIO_x es poco fiable en versiones recientes de AC: no depender de él para el ambiente sonoro.