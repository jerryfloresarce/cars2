# Investigacion web: CSP para la fase visual de Porto Corsa (agua, luces, animados, pantallas, GrassFX, color global)

Fecha: 04/10/2026. Investigador tecnico (solo lectura; no se ha modificado ningun fichero del proyecto ni se ha
lanzado Blender). Fuentes: wiki oficial de Custom Shaders Patch (CSP) en GitHub, su espejo de texto
github-wiki-see, la copia estructurada en cup.acstuff.club, los ficheros `common/*.ini` del repo
`acc-extension-config` y un ini real de pista (`mugello.ini`). Nada descargado.

Leyenda: **[V]** = hecho verificado en la fuente citada (texto leido). **[S]** = suposicion/inferencia nuestra,
pendiente de probar en un PC con AC+CSP. **[L]** = dato del proyecto, leido en el codigo local.

Encargo del usuario (PLAN_USUARIO.md, puntos 6 y 9): `[Material_Water] Type=SEA` + `[BOUNCED_LIGHT] CAUSTICS=1`,
rotor del helicoptero / dirigible / barcos animados, las dos pantallas gigantes con camara en directo, luces
nocturnas en casino, paseo y puerto, GrassFX solo en cespedes, probar con Pure y con Sol. Restriccion del
coordinador: todo lo de CSP es un extra que no puede romper AC "a pelo".

---

## 0. Resumen ejecutivo (lo que importa para decidir)

1. **Todo lo de CSP vive en `content/tracks/porto_corsa/extension/ext_config.ini`** (+ ficheros al lado:
   `.ksanim`, `trees/`, texturas). AC sin CSP ignora la carpeta `extension/` [V, cabecera de nuestro propio
   ext_config.ini y wiki]. Por tanto la degradacion es automatica: sin CSP, nada de esto existe y el KN5 se ve
   tal cual. **La unica forma de "romper" AC a pelo es meter en el KN5 cosas que dependan de CSP** (p. ej.
   ksEmissive > 0 que en AC vanilla brilla de dia, o un rotor separado que se queda quieto y raro).
2. **AC vanilla no tiene noche**: la hora va de 8:00 a 18:00; el ciclo 24 h lo dan CSP WeatherFX + Sol o Pure
   [V, foros: overtake.gg, freakhosting]. Las luces nocturnas son 100 % CSP y solo se ven con Sol/Pure.
3. **Nuestro KN5 actual** [L, `04_export/kn5_writer_opt.py`]: shader fijo `ksPerPixel`, 1 textura `txDiffuse`
   por material (plana 8x8 o tintada 512), 1 capa UV, `ksEmissive = 0`, `isTransparent` si alpha < 0.999,
   jerarquia APLANADA (toda la decoracion se fusiona por material en mallas `DECO_<material>_pN` bajo un dummy
   `DECO`; solo AGUA/TERRENO/PISTA/PIT_LANE/AC_* conservan nodo propio). Esto condiciona 3 de las 6 cosas:
   - agua: OK tal cual (`MAT_agua` con alpha 0.84 ya sale transparente) [L];
   - luces: OK si cada "bombilla" tiene **material propio** (LIGHT_SERIES por MATERIALS + CLUSTER_THRESHOLD
     funciona sobre mallas fusionadas) [V+S];
   - animados: **NO** tal cual: CSP solo mueve nodos, y el writer no deja nodos. Dos salidas: `[WRAP_MESHES_...]`
     de CSP (envuelve una malla en un nodo en tiempo de carga) [V] o un KN5 aparte insertado desde ext_config
     [V parcial];
   - pantallas: necesitan una **textura real** (no 8x8) y UVs que cubran la region [V+L].
4. **GrassFX no se activa solo**: hay que listar `GRASS_MATERIALS` en ext_config [V]. Para "cesped solo en
   jardines y rotondas" basta un material dedicado (p. ej. `MAT_cesped`) y no listar `MAT_terreno`.
5. **Color global**: ninguna clave de ext_config cambia el sol/ambiente del estilo de tiempo [V, investigacion
   previa de color_ac]. Lo que si hay: `[LIGHTING]` (multiplicadores de luces dinamicas, especular, ambiente
   del suelo), `[MATERIAL_ADJUSTMENT_n]` (ksAmbient/ksDiffuse/ksEmissive por material, con CONDITION),
   `[SHADER_REPLACEMENT_n]` y los templates de `common/materials_track.ini`. Todo ello se ignora sin CSP.

---

## 1. Marco comun: ext_config.ini, condiciones y degradacion sin CSP

**Hechos [V]**
- El fichero se llama `extension/ext_config.ini` dentro de la carpeta de la pista; CSP tambien puede traer una
  config propia para la pista (`[BASIC] IGNORE_OTHER_CONFIGS = 0/1` decide si se combinan).
  Fuente: wiki *Tracks – General options*
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-General-options>.
- Las plantillas de materiales se cargan con `[INCLUDE: common/materials_track.ini]` (nuestro ext_config ya lo
  hace) y las condiciones comunes con `[INCLUDE: common/conditions.ini]`.
- `common/conditions.ini` define, entre otras: `NIGHT_SMOOTH` (INPUT=SUN, LAG 0.97), `NIGHT_SHARP`,
  `NIGHT_SMOOTH_HEATING`, `NIGHT_SLOW_HEATING` (LAG_DELAY_ON 1800 s, SIMULATE_HEATING 0.7), `ALWAYS_ON`,
  `RACING_FLAG`, `HAZARDS` (parpadeo 4 Hz), `FLAME_FLICKERING`, `SHARP_SUN_A/B`, `SMOOTH_SUN_A/B`, `ALL_DAYS`,
  `SEASON_*`. Las condiciones 0-74 quedan libres para el usuario.
  Fuente: <https://raw.githubusercontent.com/ac-custom-shaders-patch/acc-extension-config/master/config/tracks/common/conditions.ini>.
- Condiciones propias: `[CONDITION_n] NAME=..., INPUT=SUN|TIME|TIME_SMOOTH|AMBIENT|FOG|RAIN|FLAG_TYPE|SPECTATORS|
  ONE..., LUT=(ang|valor)..., LAG, LAG_DELAY_ON/OFF, FLASHING_FREQUENCY, FLASHING_NOISE_AMPLITUDE`, y expresiones
  tipo `INPUT = 'SUN * 2 + TIME'` con `saturate()`, `clamp()`, `remap()`, `sin()`.
  Fuente: wiki *Tracks – Conditions*
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Conditions>.
- Sin CSP la carpeta `extension/` no se lee: lo dice la cabecera de nuestro `04_export/extension/ext_config.ini`
  (generado por color_ac v2) y es la premisa de toda la wiki (cada pagina describe funciones "de CSP").
- AC vanilla: "You cannot drive after 18:00 PM (at night) in stock Assetto Corsa"; Sol/Pure + CSP dan 24 h.
  Fuentes: <https://www.overtake.gg/threads/assetto-corsa-server-manager-time-of-day-not-24-hours.217956/>,
  <https://help.freakhosting.com/games/assetto-corsa/installing-sol-pure-weather>.

**Suposiciones [S]**
- Las condiciones con INPUT=SUN funcionan igual con Sol y con Pure (ambos son estilos de WeatherFX y el sol lo
  calcula CSP). No he encontrado ninguna clave de ext_config especifica de Sol o Pure para pistas: la busqueda
  solo devolvio planes de tiempo (sol_planner / PurePlanner), no configuracion por circuito.

---

## 2. Agua: `[Material_Water] Type = SEA` y causticas

**Hechos [V]**
- Receta minima (wiki *Tracks – Water shader*):
  ```ini
  [INCLUDE: common/materials_track.ini]
  [Material_Water]
  Materials = your_water_material
  Type = POND
  ```
  Valores de `Type`: LAKE, POND, POOL, SEA, OCEAN. Para los demas parametros la wiki remite a
  `[TEMPLATE: Material_Water]` en `extension/config/tracks/common/materials_track.ini`.
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Water-shader>.
- El template real (leido en el ini del repo) y sus valores por defecto:
  ```ini
  [TEMPLATE: Material_Water]
  Type = LAKE                      ; LAKE, POND, POOL, SEA, OCEAN
  UseNormalMapTwice = 0            ; usa txNormal tambien como 2a normal
  UseAlphaFromDiffuse = 0          ; alfa de txDiffuse para el fundido
  UseAlphaFromNormal = 0           ; alfa de txNormal para el fundido
  UseRecommendedTextures = 1       ; normales de agua recomendadas (de CSP)
  UseRecommendedDetailTexture = 0
  UnevenWaterFix = 0               ; subir si la malla de agua no es plana
  ; FirstNormalMap = water.dds     ; textura del KN5 como normal principal
  ; SecondNormalMap = water.dds
  DepthAware = 0                   ; refraccion y causticas con depth buffer
  CausticsMultiplier = 1.0         ; brillo de causticas, solo con DepthAware = 1
  RainOffset = 0.0                 ; metros que sube/baja el agua con lluvia
  ```
  Comentarios literales que importan: `DepthAware` "for it to work you need to set alpha from txDiffuse and set
  mesh transparent flag"; `CausticsMultiplier` "caustics map is taken from txNormal alpha channel; recommended
  texture already has it"; `UnevenWaterFix` "increase for uneven water meshes".
  Fuente: <https://cdn.jsdelivr.net/gh/ac-custom-shaders-patch/acc-extension-config@master/config/tracks/common/materials_track.ini>
  (misma ruta en raw.githubusercontent.com).
- Internamente el template es un `SHADER_REPLACEMENT` al shader `smWaterSurface` y el tipo se codifica en
  `ksAlphaRef` via `_Material_Water_MapType`: OCEAN=-2, LAKE=-1, SEA=0, POOL=1, POND=3. Con
  `UseRecommendedTextures=1` CSP asigna `txNormal` y `txDetailNM` = `?textures/common/water_normal.dds` (textura
  que trae CSP, no hace falta meterla en el KN5).
- Causticas: "[BOUNCED_LIGHT] CAUSTICS = 1" y "requires bounced light from Extra FX to be active" (ajuste del
  usuario en CSP). La pagina *Tracks – Bounced light* anade `CAUSTICS_SCALE = 1`, `SUPPORTED = 1`,
  `SURFACE_MATERIALS`, `OBJECT_MATERIALS`, `OCCLUDING_MATERIALS`, coste ~0.3 ms/frame, y avisa de que la luz
  rebotada "works primarily with a single layer tracks" (pistas sin varios pisos).
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Bounced-light>.
- `[Material_WaterDrain]` (charcos/desagues con lluvia) existe en el mismo ini; no lo necesitamos.

**Estado local [L]**
- `construir_pista.py`: objeto `AGUA` = UN quad de 4 vertices a z=0 que llega 9 km mas alla del terreno, material
  `MAT_agua` (alpha 0.84, blend BLEND), y `AGUA_fondo` a z=-4.05 con el material del terreno. El writer conserva
  `AGUA` como nodo propio, lo marca `castShadows=0` y `isTransparent=1` (alpha < 0.999). Nuestro
  `04_export/extension/ext_config.ini` YA lleva `[Material_Water] Materials = MAT_agua / Type = SEA`.

**Que exige del KN5**
- [V] Un material de agua identificable por nombre (`Materials = MAT_agua`). Nada mas para el modo basico.
- [V] Para `DepthAware = 1` (refraccion + causticas): malla con flag transparente (ya) y alfa en `txDiffuse`
  (`UseAlphaFromDiffuse = 1`). Nuestro `txDiffuse` del agua es una textura plana generada por el writer; [S] hay
  que comprobar que `construir_textura()` escribe el alfa 0.84 en el PNG y no solo en el flag.
- [S] La malla plana de 4 vertices es el caso ideal (`UnevenWaterFix = 0`). Un quad de 18 km puede dar
  imprecision de profundidad en el horizonte; si se ve "z-fighting" con la costa, subdividir el quad (4x4) o
  acercar `ext` no cambia nada en AC a pelo.
- [S] El degradado turquesa/azul del encargo NO lo da el shader de agua: viene del fondo marino (`AGUA_fondo`)
  visto a traves del agua refractiva (`DepthAware=1`) o, sin CSP, de la propia tinta de `MAT_agua`. Conviene
  dar a `AGUA_fondo` un material propio (arena clara en la orilla, azul oscuro mar adentro, por vertice o
  textura) para que funcione en los dos mundos.

**ext_config propuesto (borrador, no aplicado)**
```ini
[INCLUDE: common/materials_track.ini]
[Material_Water]
Materials = MAT_agua
Type = SEA
UseAlphaFromDiffuse = 1      ; requisito de DepthAware
DepthAware = 1               ; refraccion + causticas (probar FPS)
CausticsMultiplier = 1.0
[BOUNCED_LIGHT]
SUPPORTED = 1
CAUSTICS = 1
CAUSTICS_SCALE = 1
```

**Sin CSP**: `MAT_agua` se ve con `ksPerPixel` calibrado (color plano translucido). No se rompe nada: la seccion
entera se ignora. [S] `DepthAware` y `CAUSTICS` dependen ademas de que el usuario tenga Extra FX activado; si no,
CSP cae al agua basica, tambien sin romper.

---

## 3. Luces nocturnas: `[LIGHT_...]`, `[LIGHT_SERIES_...]`, emisivos

**Hechos [V]** (wiki *Tracks – Lights*
<https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Lights>)
- Tres formas de colocar una luz: `POSITION = X, Y, Z` (coordenadas del KN5: Y arriba), `MESH = nombre` (+
  `OFFSET`), o linea `LINE_FROM / LINE_TO` con `COLOR_FROM / COLOR_TO`. Direccion por defecto `0, -1, 0` (hacia
  abajo).
- Series: `[LIGHT_SERIES_n]` con `POSITION_0..k` (+ `DIRECTION_k`), o generadas desde geometria:
  ```ini
  [LIGHT_SERIES_...]
  MESHES = lamppost?, glowing_window?
  MATERIALS = glowing_material?
  OFFSET = X, Y, Z
  DIRECTION = NORMAL            ; alinea con la normal de la superficie
  CLUSTER_THRESHOLD = 10        ; metros: agrupa vertices en una luz por grupo (min 1 m)
  UV_FILTER_0 = x, y, w, h      ; solo los vertices cuyo UV cae en esa zona de la textura
  ```
  Algoritmo citado: para cada vertice busca el grupo mas cercano; si esta a menos de la distancia umbral se une,
  si no crea grupo. Es decir, una malla fusionada con 40 farolas da 40 luces si el umbral es menor que la
  separacion entre farolas y mayor que el tamano de cada bombilla.
- Parametros por luz: `ACTIVE`, `DESCRIPTION`, `SPOT` (grados; 0 = puntual), `SPOT_SHARPNESS` 0-1, `RANGE` (m),
  `RANGE_GRADIENT_OFFSET`, `COLOR = r, g, b, intensidad` (tambien `'#ff8844', 2`), `SPECULAR_MULT`,
  `SINGLE_FREQUENCY` (1 = sodio monocromatico), `DIFFUSE_CONCENTRATION`, `FADE_AT` (m, 50 % de intensidad) y
  `FADE_SMOOTH`, `VOLUMETRIC_LIGHT` (caro), `LONG_SPECULAR` (mojado, pide SSLR), `SKIP_LIGHT_MAP`,
  `CONDITION = NIGHT_SMOOTH` (+ `CONDITION_OFFSET`), `RELATIVE_TO = nodo` para luces sobre objetos moviles.
- Sombras: solo en focos con angulo < 180; `SHADOWS_STATIC = 1` y `SHADOWS_HALF_RESOLUTION = 1` para rendimiento;
  15 ranuras de alta + 16 de baja resolucion en total. "Avoid enabling shadows for lights that are constantly in
  motion".
- Rendimiento: lo que cuesta es la cobertura en pixeles, no el numero de luces; usar `FADE_AT/FADE_SMOOTH`.
- Herramienta "Light Maker" (app de CSP) para ajustar una luz y pegarla con Ctrl+V.
- Ejemplo real (`mugello.ini` del repo de CSP): series por material con offset y umbral
  ```ini
  [LIGHT_SERIES_0]
  MATERIALS = Gazebo_Tent
  OFFSET = 0,-2.5,0
  CLUSTER_THRESHOLD = 8
  COLOR = 255,172,50,0.065
  SPOT = 180
  RANGE = 6
  CONDITION = SHARP_SUN_A
  ```
  y emisivo condicionado
  ```ini
  [MATERIAL_ADJUSTMENT_0]
  MESHES = Plane018a,Object400a
  CONDITION = SMOOTH_SUN_A
  KEY_0 = ksEmissive
  VALUE_0 = 255, 172, 100, 0.5
  ```
  <https://raw.githubusercontent.com/ac-custom-shaders-patch/acc-extension-config/master/config/tracks/mugello.ini>.
  Ese mismo fichero usa `[Material_DistantEmissive]`, `[Material_RoomWindows]`, 7 `[DISPLAY_...]` y 4
  `[MODEL_REPLACEMENT_n]` (inserta KN5 extra: "emissive, windows, flood, flags").
- Emisivos lejanos: `[Material_DistantEmissive]` sustituye la emision por billboards que miran a la camara
  (punto pequeno + halo grande en niebla); claves `Meshes`, `UseAlpha`, `UseEmissiveTexture`,
  `FloodlightPower`, `FloodlightEXP`, `BrightnessMult`, `DotMaxDistance`; agrupacion `[DISTANT_GLOW]
  THRESHOLD = 50, SHARED_THRESHOLD = 25`.
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Distant-emissives>.
- Contaminacion luminosa de ciudad (halo del cielo nocturno): `[LIGHT_POLLUTION] RELATIVE_POSITION, RADIUS_KM,
  DENSITY, COLOR` (wiki *Tracks – Miscellaneous options*
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Miscellaneous-options>).
- Multiplicadores globales en `[LIGHTING]`: `LIT_MULT`, `SPECULAR_MULT`, `CAR_LIGHTS_LIT_MULT`,
  `BOUNCED_LIGHT_MULT`, `ENABLE_TREES_LIGHTING`, `TRACK_AMBIENT_GROUND_MULT`, `TERRAIN_SHADOWS_THRESHOLD`
  (*Tracks – General options*).

**Estado local [L]**
- Hay farolas en la bajada del penon (`roca_casino.py`, lista `farolas`), luminarias en boxes (`pit_kit_v2.py`,
  "luminarias emisivas", monitores "pantallas emisivas"), farolas de azotea (`mirador_kit.py`), postes de
  guirnalda (`CALLE_guirnalda`), pantalla con material `pantalla_luz` (carrera_kit_v2). En el KN5 TODO esto se
  fusiona en `DECO_<material>_pN` y `ksEmissive` se escribe a 0 (SHADER_PROPS del writer). No he comprobado si
  las bombillas tienen material propio en todos los kits; en carrera_kit_v2 si (`pantalla_luz`).

**Que exige del KN5**
- [V] Para `LIGHT_SERIES` por geometria: que las bombillas/ventanas tengan un **material propio** (o malla propia)
  y que su geometria sea pequena y separada entre si (el clustering es por distancia entre vertices). Con el
  writer actual, `MATERIALS = MAT_luz_?` funciona aunque las mallas esten fusionadas; `MESHES = DECO_MAT_luz_?`
  tambien (comodin `?`). [S] Si una malla fusionada abarca farolas a 300 m unas de otras, CSP crea una luz por
  farola igualmente: el umbral manda. Hay que verificar en AC con `DESCRIPTION` y el inspector de luces.
- [V] Para que el emisivo se encienda solo de noche: dejar `ksEmissive = 0` en el KN5 y subirlo con
  `[MATERIAL_ADJUSTMENT_n] KEY_0 = ksEmissive, VALUE_0 = r, g, b, k, CONDITION = NIGHT_SMOOTH`. Asi en AC a pelo
  no brilla nunca (correcto: es de dia) y en CSP brilla al anochecer. Si se horneara `ksEmissive > 0` en el KN5
  brillaria de dia en vanilla (la formula de ksPerPixel suma `ksEmissive` sin condicion; ver
  `_rev/color_ac/investigacion.md`, seccion 1).
- [S] Un material "oscuro" para la bombilla apagada (gris calido) queda mejor de dia que uno blanco puro.
- [S] Para las ventanas del pueblo de noche, `[Material_RoomWindows]` (template del mismo ini) da interiores
  falsos; no he leido su documentacion en detalle, solo su existencia en el template y su uso en mugello.ini.

**ext_config propuesto (borrador)**
```ini
[INCLUDE: common/conditions.ini]
[LIGHT_SERIES_FAROLAS]
MATERIALS = MAT_farola_luz
OFFSET = 0, -0.3, 0
CLUSTER_THRESHOLD = 6
DIRECTION = 0, -1, 0
SPOT = 150
SPOT_SHARPNESS = 0.2
RANGE = 18
COLOR = 255, 200, 140, 0.6
FADE_AT = 350
FADE_SMOOTH = 60
CONDITION = NIGHT_SMOOTH
DESCRIPTION = farolas paseo/puerto/penon
[MATERIAL_ADJUSTMENT_FAROLAS]
MATERIALS = MAT_farola_luz
KEY_0 = ksEmissive
VALUE_0 = 255, 200, 140, 1.5
CONDITION = NIGHT_SMOOTH
[LIGHT_POLLUTION]
RELATIVE_POSITION = 0, 0, 0   ; [S] centro del pueblo en coords KN5 (X, Y arriba, Z = -y_blender)
RADIUS_KM = 1.5
DENSITY = 0.3
COLOR = 1.0, 0.8, 0.6
```
Valores numericos: todos [S], a calibrar en AC. Repetir el par serie+ajuste para `MAT_casino_luz`,
`MAT_guirnalda_luz`, `MAT_pit_luminaria`, `MAT_ventana_luz`.

**Sin CSP**: no hay noche, asi que no se echa en falta nada; las bombillas se ven como material opaco calibrado.
La unica condicion es NO hornear emisivos en el KN5.

---

## 4. Objetos animados: rotor, dirigible, barcos

**Hechos [V]** (wiki *Tracks – Animated objects*
<https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Animated-objects>,
copia estructurada <https://cup.acstuff.club/docs/csp/tracks/animated-objects>)
- Sintaxis: `[ANIMATED_...] ACTIVE = 1, NODE = nombre_del_nodo`; el tipo lo decide que claves haya:
  1. **Windmill** (gira con el viento): `WINDMILL_DIR`, `SPIN_AXIS`, `WIND_SPEED_KMH_MIN/MAX/STOP`, `LAG_UP/DOWN/
     BRAKING`, `SPEED_MULT`.
  2. **Weather vane**: `WEATHERVANE_DIR`, `SPIN_AXIS`, `INERTIA`, `ANGLE_OFFSET`.
  3. **Clock needle**: `CLOCK_NEEDLE = SECONDS|MINUTE|HOUR|HOUR24`, `SPIN_AXIS`, `LAG = 0.67`.
  4. **Keyframe**: `ANIMATION = fichero.ksanim` (junto al ext_config), `DURATION = s`, `TICK_TOCK_MODE`,
     `PROGRESS = condicion` (opcional; si no, bucle).
  5. **Train** (sigue un camino): `MOVE_ALONG = malla_camino` ("something like a long narrow strip (possibly
     hidden)", abierta o cerrada), `NODES_FOLLOWING = vagon_1, vagon_2`, `SPEED_KMH`, `PIECE_LENGTH`,
     `CUBIC_INTERPOLATION`, `DELAY_BETWEEN_RUNS = min, max`, `SPEED_ADJUSTMENT_k` por zonas, `DEBUG_PATH = 1`,
     y expone `SPEED_CONDITION_INPUT` / `PROGRESS_CONDITION_INPUT` para luces/sonido. Nota citada: el objeto
     movil debe ir alineado al eje Y y girado 90 grados en X.
  6. **Condicional**: `POSITION = X, Y, Z`, `ROTATION = grados`, `SCALE = X, Y, Z`, `SPIN_AXIS`, donde cada valor
     puede ser una condicion o expresion.
- **Requisito de estructura**: "meshes can't be moved unless they are within their own nodes". Al guardar una
  pista en ksEditor la jerarquia se aplana, por eso la wiki recomienda exportar lo animado a un **KN5 aparte**
  guardado como coche ("Save KN5/Car") para conservar los nodos.
- Alternativa en tiempo de carga (wiki *Tracks – Meshes manipulation*
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Meshes-manipulation>):
  ```ini
  [WRAP_MESHES_...]
  NAME = node
  MESHES = mesh0, ...
  PIVOT_POS = X, Y, Z
  PIVOT_DIR = X, Y, Z
  PIVOT_UP = X, Y, Z
  ```
  "Wrap flattened meshes in nodes for animation": envuelve mallas ya aplanadas en un nodo con pivote propio, que
  luego se mueve con `[ANIMATED_...] NODE = node`. Tambien hay `[SPLIT_MESHES_...]` (separa una malla en
  elementos; mas draw calls), `[SMOOTH_NORMALS_...]`, `[ALTER_NORMALS_...]`, `[SUBDIVIDE_MESHES_...]`.
- Como se hace un `.ksanim`: exportar FBX con animacion, abrirlo en ksEditor y "FBX Animation" genera el
  `.ksanim` en la misma carpeta; para Blender existe un exportador ksanim (los nodos animados dentro de un nodo
  padre con Y arriba y -Z adelante). Fuentes: <https://assettocorsamods.net/goto/post?id=15423>,
  <https://blenderartists.org/t/from-blender-to-assetto-corsa/1413256>.
- Los KN5 extra se cargan desde ext_config con `[MODEL_REPLACEMENT_n]` (mugello.ini usa 4 para insertar
  emisivos, ventanas, focos y banderas) [V que existe]; las claves exactas (`FILE`, `INSERT`, `INSERT_AFTER`,
  `HIDE`) no las he podido leer en la wiki de esta pasada: [S].

**Estado local [L]**
- Helicoptero-camara (`assets/camaras_kit.py`): rotor principal de 2 palas + disco translucido, rotor de cola +
  disco, en `CAMARA_helicoptero_*` (los discos van en malla aparte `CAMARA_helicoptero_discos`, sin sombra).
- Dirigible (`integrar_escena.py` ~1377): objetos `DIRIGIBLE` (globo) y `DIRIGIBLE_gondola`.
- Barcos: yates y veleros del puerto (`yates_kit.py`), lanchas de la cala del casino.
- El writer fusiona todo esto en `DECO_<material>_pN` (coordenadas de mundo, sin nodos). Unica excepcion
  configurable: `KEEP_PREFIXES` (hoy `AC_`, `PIT_LANE`, `PISTA`, `TERRENO`, `AGUA`).

**Que exige del KN5 (y que opciones tenemos)**
- [V] Un **nodo propio** por pieza movil, con el pivote donde debe girar (eje del rotor, centro del dirigible,
  centro del barco). Hoy no existe.
- Opcion A (sin tocar el writer): `[WRAP_MESHES_...]` sobre una malla que SOLO contenga el rotor. Requiere que el
  rotor tenga material propio (`MAT_heli_rotor`) para que la fusion lo deje en su propio `DECO_MAT_heli_rotor_p0`
  y que sea el unico objeto con ese material (si hubiera 2 helicopteros, un solo nodo giraria los dos alrededor
  de un unico pivote: mal). `PIVOT_POS` en coordenadas KN5 (x, z, -y de Blender). [S] Que WRAP acepte una malla
  fusionada de un solo objeto es de esperar, pero no esta probado.
- Opcion B (cambio pequeno en el writer, equipo de 04_export, NO ahora): anadir un prefijo `ANIM_` a
  `KEEP_PREFIXES` para que esos objetos salgan como dummy con su matriz y malla hija en locales (como ya hace con
  TERRENO/AGUA). Entonces `NODE = ANIM_heli_rotor` funciona directo. Es la via mas limpia y sigue siendo inocua
  sin CSP (un nodo mas, quieto).
- Opcion C (la de la wiki): KN5 aparte `porto_corsa_anim.kn5` guardado "como coche" e insertado con
  `[MODEL_REPLACEMENT_n]`. Sin CSP el fichero no se carga: el helicoptero y el dirigible desaparecerian en AC a
  pelo, salvo que el KN5 principal lleve una copia estatica y ext_config la oculte (`HIDE`) al insertar la movil
  [S sobre las claves].
- Rotor girando de continuo: [S] el tipo "windmill" depende del viento (puede quedarse quieto con viento 0);
  el tipo condicional `ROTATION = expresion` necesita una entrada que crezca con el tiempo (la wiki de
  condiciones lista TIME y TIME_SMOOTH, que son hora del dia: 1 vuelta por dia, inutil). La via segura es un
  `.ksanim` de 1 vuelta con `DURATION = 0.15` en bucle, o `CLOCK_NEEDLE = SECONDS` con `LAG = 0` (1 vuelta por
  minuto: lento para un rotor, valido para un radar o una noria). Probar en AC.
- Barcos y dirigible: [V] tipo **Train** con un camino oculto: malla "tira estrecha" (p. ej. `ANIM_ruta_yate`,
  material invisible o `isRenderable=0`), `NODES_FOLLOWING` con 1 nodo por barco, `SPEED_KMH = 8-12`,
  `DELAY_BETWEEN_RUNS` para que no parezca un tren. [S] El camino puede ser cerrado (bucle por la bahia) y, para el
  dirigible, un bucle a 120 m sobre el mar.
- Luces sobre objetos moviles: `[LIGHT_...] RELATIVE_TO = nodo` (sin sombras) [V].

**Sin CSP**: todos los `[ANIMATED_...]` y `[WRAP_MESHES_...]` se ignoran; las piezas quedan quietas en la pose
exportada. Para que eso no se vea raro: exportar el rotor en una pose creible (palas en cruz) y los barcos en
posicion inicial coherente (amarrados o navegando). Con la opcion C, ademas, los objetos desaparecen sin CSP.

---

## 5. Pantallas gigantes con camara en directo: `[DISPLAY_...]`

**Hechos [V]** (wiki *Tracks – Displays*
<https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Displays>,
copia <https://cup.acstuff.club/docs/csp/tracks/displays>)
- "Displays allow to animate track textures. At the moment, they only support camera feed".
- Dos partes: la pantalla (`MESHES = tvstaff_HI_?`, `REGION_START = 20, 320` y `REGION_SIZE = 508, 290` en
  **pixeles de la textura**, `HIGH_REFRESH_RATE = 1` (30 fps; 0 = 15 fps), `FLIP_X/FLIP_Y`, correcciones
  `OUTPUT_ALPHA/GAMMA/SATURATION/BRIGHTNESS/FISH_EYE/VIGNETTE/CHROMATIC_ABERRATION`) y el modo
  (`MODE = CAMERA` con `CAMERA_k = X, Y, Z`, `CAMERA_k_TARGET = X, Y, Z | CLOSEST_CAR | FOCUSED_CAR`,
  `CAMERA_k_UP`, `CAMERA_k_FOV = 50`, `CAMERA_k_ASPECT_RATIO` (por defecto ancho/alto de la region),
  `CAMERA_k_TARGET_INERTIA`, `CAMERA_k_TARGET_REFERENCE_POINT`). Con varias camaras, se usa la mas cercana al
  jugador.
- Limite: "Cameras and displays only work if they're not too far away from camera" (respeta LOD/chunks).
- Opcional `[Material_DigitalScreen]` (template de materials_track.ini) para patron de pixeles y distorsion
  (`ScreenScale`, `UseTextureCoordinates`, mascaras `UseDiffuseMask/UseMapsMask/UseNormalMask/UseAreaMask`).
- Ejemplo real: mugello.ini tiene 7 displays apuntando a `CLOSEST_CAR`.

**Estado local [L]**
- `carrera_kit_v2.build_pantalla`: caja de 11.9 x 6.9 m con material `pantalla_luz` (indice 2) sobre torre de
  celosia; el integrador clona 2 en la tribuna del mar (`CARRERA_pantalla*`). En el KN5 la textura de
  `pantalla_luz` es una plana de 8x8 (writer: "las planas son 8x8") y las UVs de una `caja()` del kit son las
  que genere `_MB` (no comprobado).

**Que exige del KN5**
- [V] La malla de la pantalla con su textura: la region se da en pixeles, asi que hace falta una textura de
  tamano real (p. ej. 1024x576, 16:9) en `txDiffuse` del material de la pantalla, y UVs de la cara frontal que
  cubran exactamente esa region (0..1 si la region es toda la textura: `REGION_START = 0, 0`,
  `REGION_SIZE = 1024, 576`). Las otras caras de la caja (marco) deben llevar OTRO material o UVs fuera de la
  region, o se veran con la camara tambien.
- [L] El writer escribe UV como (u, 1 - v): [S] probablemente haga falta `FLIP_Y = 1` o no; se ajusta viendo la
  pantalla en AC, es un flag.
- [S] Textura base: una imagen estatica que quede bien sin CSP (logo "WGP" + "LIVE" o un plano de la bahia): es lo
  que vera AC a pelo y lo que vera CSP cuando el jugador este lejos.
- [S] Que la textura se pueda dar al writer: hoy `analizar_material()` lee la imagen del nodo del material
  (`info['img']`) y la reduce a <= 1024; una Image Texture conectada al Base Color del material de la pantalla
  deberia bastar. Lo tiene que confirmar el equipo de export.

**ext_config propuesto (borrador)**
```ini
[DISPLAY_PANTALLA_1]
MESHES = DECO_MAT_pantalla_1_?     ; o nombre propio si el writer lo conserva
REGION_START = 0, 0
REGION_SIZE = 1024, 576
HIGH_REFRESH_RATE = 1
OUTPUT_GAMMA = 0.9
OUTPUT_VIGNETTE = 0.2
MODE = CAMERA
CAMERA_0 = X, Y, Z                 ; [S] torre de TV de la recta, coords KN5
CAMERA_0_TARGET = CLOSEST_CAR
CAMERA_0_FOV = 40
CAMERA_0_TARGET_INERTIA = 0.5
```
Dos pantallas con el mismo material compartirian imagen (una sola seccion con `MESHES` que las coja a las dos);
si se quieren imagenes distintas hacen falta dos materiales/texturas.

**Sin CSP**: la pantalla muestra la textura estatica. Nada se rompe.

---

## 6. GrassFX: como limitarlo a los cespedes

**Hechos [V]** (wiki *Tracks – Grass FX*
<https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Grass-FX>,
copia <https://cup.acstuff.club/docs/csp/tracks/grass-fx>)
- "Grass FX replaces original AC grass with the one spawned procedurally around the camera". Hay que decir en
  que mallas o materiales nace: `GRASS_MATERIALS = ...` / `GRASS_MESHES = ...` (se pueden combinar).
- `OCCLUDING_MATERIALS/MESHES` (p. ej. asfalto): tapan la hierba que asomaria a traves; variantes `_ALPHA` para
  fundidos suaves (arena sobre hierba). `ORIGINAL_GRASS_MATERIALS` oculta la hierba 3D original cuando GrassFX
  esta activo; una linea vacia tras `=` conserva la original.
- **Mascara por color de la textura**: por defecto solo nace en zonas "green-ish, not too bright, not too
  dark": `MASK_MAIN_THRESHOLD = 0.5` (saturacion de verde), `MASK_RED_THRESHOLD = 0.05` (tolerancia hacia
  amarillo), `MASK_MIN_LUMINANCE = 0.02`, `MASK_MAX_LUMINANCE = 0.35`. Para que nazca en todo el material:
  -1, 0, -1, 1. `MASK_BLUR = 0..3`.
- Forma: `SHAPE_SIZE` (mas grande = menos densidad), `SHAPE_TIDY`, `SHAPE_CUT`, `SHAPE_WIDTH`; `TRIM_PERIOD =
  THURSDAY` y `SHAPE_SIZE = 0.5, 1.0` para hierba que crece y se corta; textura propia `TEXTURE = grass_fx/
  fichero.dds` con `TEXTURE_GRID = cols, rows`.
- Rendimiento: por defecto GrassFX no se dibuja en el G-buffer ("cutting time almost in half"); si da artefactos
  con reflejos, `[EXTRA_FX] FORCE_GRASSFX_GBUFFER_PASS = 1`.
- Alineacion de arboles al suelo: `[ALIGN_TREES_...] SURFACE_MATERIALS, TREE_MATERIALS` (Miscellaneous options).

**Estado local [L]**
- Hierba fisica = prefijos `1GRASS_`/`2GRASS_` (nombres de malla, deciden la fisica de AC, no el aspecto). El
  terreno visible es `MAT_terreno` (mezcla hierba/roca en Blender; en el KN5 es un color por material). No hay
  todavia un material `MAT_cesped` separado para jardines y rotondas.

**Que exige del KN5**
- [V] Un **material propio para el cesped** (`MAT_cesped`) en jardines, rotondas (Loews, palmera), plaza del
  casino, y NO usarlo en el terreno general. `GRASS_MATERIALS = MAT_cesped` y nada mas: asi el matorral oliva, la
  hierba seca y la roca del terreno quedan limpios, como pide el usuario.
- [V] El color de la textura de `MAT_cesped` debe entrar en la mascara (verde, luminancia 0.02-0.35) o bajar los
  umbrales en ext_config. [L] Nuestras texturas "planas" son 8x8 tintadas con el color calibrado de color_ac: [S]
  un verde cesped calibrado (ksDiffuse 0.4-0.6) probablemente supere `MASK_MAX_LUMINANCE = 0.35`; poner
  `MASK_MAX_LUMINANCE = 1` y `MASK_MAIN_THRESHOLD = -1` para que cubra todo el material (la limitacion ya la da
  el material).
- [V] `OCCLUDING_MATERIALS = MAT_asfalto, MAT_adoquin, MAT_acera, ...` para que no asome hierba por los bordes de
  calzadas y plazas pegadas al cesped.
- [S] Tambien se puede usar GrassFX con otra textura (TEXTURE) para "hierba seca dorada" en una segunda
  seccion... la wiki describe una sola seccion `[GRASS_FX]`; no he visto soporte de varios juegos de hierba por
  material. No prometerlo.

**ext_config propuesto (borrador)**
```ini
[GRASS_FX]
GRASS_MATERIALS = MAT_cesped
OCCLUDING_MATERIALS = MAT_asfalto, MAT_adoquin, MAT_acera, MAT_bordillo
ORIGINAL_GRASS_MATERIALS =
MASK_MAIN_THRESHOLD = -1
MASK_RED_THRESHOLD = 0
MASK_MIN_LUMINANCE = -1
MASK_MAX_LUMINANCE = 1
SHAPE_SIZE = 0.8
SHAPE_TIDY = 0.7      ; cesped cuidado de jardin
SHAPE_CUT = 0.5
```

**Sin CSP**: el cesped es el material plano calibrado; no hay hierba 3D original que ocultar (no la generamos),
asi que no cambia nada.

---

## 7. Opciones de ext_config.ini que afectan al color global de la pista

**Hechos [V]**
- `[LIGHTING]` (*Tracks – General options*): `LIT_MULT = 1` (luces dinamicas sobre la pista), `SPECULAR_MULT = 1`,
  `CAR_LIGHTS_LIT_MULT = 1`, `BOUNCED_LIGHT_MULT = 1, 1, 1, 1`, `ENABLE_TREES_LIGHTING = 0/1`,
  `TRACK_AMBIENT_GROUND_MULT = 0.5` (brillo del ambiente en caras que miran abajo; la wiki avisa "only define it
  if needed!"), `TERRAIN_SHADOWS_THRESHOLD = 0.0`. "Most of those settings require race reload to apply".
- `[MATERIAL_ADJUSTMENT_n]`: `ACTIVE`, `MESHES`/`MATERIALS` (comodin `?`), `KEY_k = ksAmbient|ksDiffuse|ksEmissive|
  ksSpecular|...`, `VALUE_k`, `CONDITION`, `DESCRIPTION`. Es la palanca que ya tenemos (desactivada) en
  `04_export/extension/ext_config.ini` para bajar ksDiffuse/ksAmbient de `MAT_?` sin regenerar el KN5.
- `[SHADER_REPLACEMENT_n]`: `MESHES`/`MATERIALS`, `SHADER = ...`, `PROP_k = nombre, valor`, `RESOURCE_k = txX` +
  `RESOURCE_FILE_k`/`RESOURCE_TEXTURE_k`, `BLEND_MODE`, `IS_TRANSPARENT`, `CAST_SHADOWS`,
  `DOUBLE_FACE_SHADOW_BIASED = 1` (arregla sombras despegadas), `PROP_... = ksAlphaRef, -193` (truco de la wiki
  para disimular el tileado). Es lo que generan por dentro los templates `[Material_*]`: el agua es un
  `SHADER_REPLACEMENT_0_WATER_...` a `smWaterSurface`.
- Templates disponibles en `common/materials_track.ini` [V, lista completa]: `Material_Bale`,
  `Material_DigitalScreen`, `Material_Water`, `Material_WaterDrain`, `Material_DistantEmissive`,
  `Material_RoomWindows`, `Material_DisplacementMap`, `Material_DistantGeometry`, `Material_Horizon`. Para el
  "anillo de fondo con costa y montanas lejanas" del encargo (punto 7) `Material_Horizon` y
  `Material_DistantGeometry` ("render meshes regardless of distance") son los candidatos [S sobre sus claves].
- `[WEATHER_FX] SKY_BELOW_HORIZON = 1` ("360 sky", por defecto 0.2115) para pistas en las que se ve cielo bajo el
  horizonte (nosotros: mar hasta 9 km, no hace falta) [V].
- `[LIGHT_POLLUTION]` (seccion 3) tine el cielo nocturno sobre el pueblo [V].
- **Ninguna clave de ext_config cambia el color del sol ni del ambiente del estilo de tiempo** (ya concluido en
  `_rev/color_ac/investigacion.md`, seccion 5, tras leer *General options*): el tono global lo deciden el KN5
  (ksAmbient/ksDiffuse/colores) y el estilo WeatherFX del usuario (CSP por defecto, Sol, Pure, con o sin espacio
  lineal). Con Pure/Sol en gamma el circuito tiende a verse lavado; con LCS cambia la curva (investigacion, 1 y 6).
- Linear color space: la wiki de CSP pide materiales con `ksAmbient/ksDiffuse` en torno a 0.4-0.6 y parecidos
  entre si (investigacion, seccion 3): sigue siendo el criterio para los materiales nuevos de esta fase
  (`ksMultilayer_fresnel_nm4` del terreno incluido).

**Suposiciones [S]**
- Sol y Pure no leen nada de la pista salvo lo estandar de CSP; lo que si cambia entre ellos es la exposicion y
  la curva de tono, asi que la unica "prueba con Pure y con Sol" posible es visual, en el PC del amigo, con el
  mismo KN5 y el mismo ext_config. Dejar la palanca `[MATERIAL_ADJUSTMENT_0]` como esta (ACTIVE=0, con
  comentario) y, si hace falta, duplicarla por familias (terreno, roca, fachadas) en lugar de un `MAT_?` global.
- `TRACK_AMBIENT_GROUND_MULT` no tocar (la v1 lo probo a 0.35 y oscurecia las sombras de mas).

**Sin CSP**: todo se ignora; por eso el color base DEBE ir bien en el KN5 (trabajo de color_ac), y ext_config
solo afina.

---

## 8. Relacionado, fuera de mi bloque pero leido de paso

- **TreeFX** (wiki *Tracks – Trees*
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Trees>) [V]: lista
  `LIST_0 = trees/trees.txt` -> `content/tracks/<pista>/extension/trees/trees.txt`, lineas
  `tree: mi_arbol.bin; x, y, z` y `tree: tree0.bin; pos=...; angle = 180`, `configure: size variance = 0.8, 1.2`;
  conversion FBX -> .bin con Content Manager > Content/Tools/Creator tools > tree converter; LOD A/B/C de
  10k/6k/3k triangulos, una malla por LOD, pivote "right at the middle of its base", difusa + normal (alfa de la
  normal = AO local); compilar con VAO bakery v17+ a `COMPILED_LIST = compiled_trees.bin`. Sin CSP los arboles
  TreeFX NO existen: hay que dejar en el KN5 arboles de respaldo (los actuales, mejorados) u ocultarlos con CSP
  (`[MESH_ADJUSTMENT]`/`MODEL_REPLACEMENT HIDE` [S]) cuando TreeFX esta activo.
- **Vertex AO** (wiki *Tracks – Vertex AO*
  <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Vertex-AO>) [V]: "Per-
  vertex ambient occlusion helps to add some smooth ambient shadows at zero FPS cost"; se hornea con
  CustomTracksBakery (actools) arrastrando el `models_*.ini` o el KN5, produce un `.vao-patch` aparte (no toca el
  KN5: se puede cambiar una textura sin rehornear); parametros en `baked shadows params.txt`. Sin CSP el
  `.vao-patch` se ignora. El `acc-bakeryoptix` que cita el usuario es la variante con OptiX de esa misma
  herramienta [S].

---

## 9. Tabla resumen

| Funcion | KN5 (malla / material / UV) | ext_config.ini | Sin CSP | Choque con el writer actual |
|---|---|---|---|---|
| Agua SEA | material `MAT_agua` (ya); plano a z=0 (ya); flag transparente (ya) | `[INCLUDE common/materials_track.ini]` + `[Material_Water] Materials, Type=SEA` (ya) | color plano translucido | ninguno |
| Causticas / refraccion | alfa en txDiffuse del agua; fondo marino con material propio | `DepthAware=1`, `UseAlphaFromDiffuse=1`, `[BOUNCED_LIGHT] SUPPORTED=1, CAUSTICS=1` | nada (se ignora) | [S] comprobar alfa en el PNG plano |
| Luces nocturnas | material propio por tipo de bombilla; `ksEmissive=0` en KN5 | `[LIGHT_SERIES] MATERIALS + CLUSTER_THRESHOLD + CONDITION=NIGHT_SMOOTH`; `[MATERIAL_ADJUSTMENT] ksEmissive` | no hay noche: nada que ver | fusion por material: OK si el material es exclusivo de las bombillas |
| Animados (rotor, barcos, dirigible) | nodo propio con pivote (hoy no existe) | `[WRAP_MESHES]` o `KEEP_PREFIXES ANIM_` + `[ANIMATED_...]` (ksanim, train, windmill) | quietos en pose exportada | writer aplana: hace falta WRAP (CSP) o ANIM_ (writer) |
| Pantallas en directo | textura real (1024x576) + UVs 0..1 en la cara frontal; marco con otro material | `[DISPLAY_...] MESHES, REGION_*, MODE=CAMERA, CAMERA_0_TARGET=CLOSEST_CAR` | textura estatica | textura plana 8x8: hay que embeber una imagen |
| GrassFX solo cesped | material `MAT_cesped` exclusivo de jardines/rotondas | `[GRASS_FX] GRASS_MATERIALS=MAT_cesped, OCCLUDING_MATERIALS, MASK_* = -1,0,-1,1` | color plano | ninguno (nuevo material) |
| Color global | ksAmbient/ksDiffuse 0.4-0.6 en el KN5 | `[LIGHTING]`, `[MATERIAL_ADJUSTMENT]`, `[SHADER_REPLACEMENT]`, templates | el KN5 manda | ninguno |

---

## 10. Esqueleto de `extension/ext_config.ini` v1.1 (borrador; NO escrito en 04_export, solo propuesta)

Orden sugerido (todo inerte sin CSP; cada bloque se puede activar por separado con `ACTIVE = 0/1`):
1. `[ABOUT]`, `[BASIC]`, `[LIGHTING]`: como estan hoy (color_ac v2).
2. `[INCLUDE: common/materials_track.ini]`, `[INCLUDE: common/conditions.ini]`.
3. `[Material_Water]` (seccion 2) + `[BOUNCED_LIGHT]`.
4. `[GRASS_FX]` (seccion 6).
5. `[LIGHT_SERIES_*]` + `[MATERIAL_ADJUSTMENT_*]` por familia de bombilla + `[LIGHT_POLLUTION]` (seccion 3).
6. `[WRAP_MESHES_*]` + `[ANIMATED_*]` (seccion 4) cuando existan los materiales/nodos.
7. `[DISPLAY_*]` (seccion 5) cuando la pantalla tenga textura real.
8. `[MATERIAL_ADJUSTMENT_0]` palanca de brillo, ACTIVE = 0 (ya).
Regla de oro: cada seccion referencia materiales con nombre exclusivo (`MAT_cesped`, `MAT_farola_luz`,
`MAT_heli_rotor`, `MAT_pantalla_1`), de modo que Blender decide "que" y ext_config decide "como".

## 11. Pendiente de verificar en un PC con AC + CSP (no se puede aqui)

1. Que `LIGHT_SERIES` por `MATERIALS` sobre mallas fusionadas `DECO_*` cree una luz por farola (umbral 6-10 m).
2. Que `[WRAP_MESHES]` acepte una malla `DECO_MAT_heli_rotor_p0` y que el rotor gire con `.ksanim` en bucle.
3. Si `DepthAware=1` exige realmente alfa en el PNG o basta el flag; FPS con causticas con 12 coches.
4. `FLIP_Y` de la pantalla y la distancia maxima a la que CSP sigue renderizando el display.
5. Que la textura plana tintada de `MAT_cesped` pase la mascara de GrassFX con los umbrales a -1/0/-1/1.
6. Las claves exactas de `[MODEL_REPLACEMENT_n]` (FILE/INSERT/HIDE) si se opta por un KN5 aparte.
7. Aspecto con Pure (gamma y LCS) y con Sol del mismo KN5: solo visual, en el PC del amigo.

## 12. Fuentes (todas consultadas el 04/10/2026)

- Water shader: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Water-shader>
- materials_track.ini (templates): <https://raw.githubusercontent.com/ac-custom-shaders-patch/acc-extension-config/master/config/tracks/common/materials_track.ini>
- Bounced light: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Bounced-light>
- Lights: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Lights>
- Conditions: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Conditions>
- conditions.ini: <https://raw.githubusercontent.com/ac-custom-shaders-patch/acc-extension-config/master/config/tracks/common/conditions.ini>
- Distant emissives: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Distant-emissives>
- Animated objects: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Animated-objects> y <https://cup.acstuff.club/docs/csp/tracks/animated-objects>
- Meshes manipulation (WRAP/SPLIT/SMOOTH): <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Meshes-manipulation>
- Displays: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Displays> y <https://cup.acstuff.club/docs/csp/tracks/displays>
- Grass FX: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Grass-FX> y <https://cup.acstuff.club/docs/csp/tracks/grass-fx>
- General options: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-General-options>
- Miscellaneous options: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Miscellaneous-options>
- Trees: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Trees>
- Vertex AO: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Vertex-AO>
- Ejemplo real de pista: <https://raw.githubusercontent.com/ac-custom-shaders-patch/acc-extension-config/master/config/tracks/mugello.ini>
- Indice del wiki: <https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki>
- .ksanim con ksEditor: <https://assettocorsamods.net/goto/post?id=15423>; exportador Blender: <https://blenderartists.org/t/from-blender-to-assetto-corsa/1413256>
- AC vanilla sin noche: <https://www.overtake.gg/threads/assetto-corsa-server-manager-time-of-day-not-24-hours.217956/>, <https://help.freakhosting.com/games/assetto-corsa/installing-sol-pure-weather>
- Locales [L]: `04_export/kn5_writer_opt.py`, `04_export/extension/ext_config.ini`, `04_export/color_ac.py`,
  `03_blender/construir_pista.py`, `03_blender/assets/carrera_kit_v2.py`, `03_blender/assets/camaras_kit.py`,
  `03_blender/integrar_escena.py`, `03_blender/_rev/color_ac/investigacion.md`.
