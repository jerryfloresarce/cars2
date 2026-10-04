# Investigación web: ksMultilayer_fresnel_nm4, acc-bakeryoptix (VAO) y erosión hidráulica

Fase visual de Porto Corsa. Investigador técnico, 04/10/2026. Sin descargas, sin tocar Blender ni `04_export`.
Fuentes leídas por fetch (GitHub, API de GitHub, docs de CSP, foros de modders). Una sola medición propia:
un benchmark NumPy reimplementado por mí en el scratchpad (apartado 3.2.3), no código descargado.

Convención del documento: **[V]** = hecho verificado en la fuente citada (cita corta o dato literal).
**[S]** = suposición, inferencia o dato de foro sin confirmación oficial. Las cifras "medidas" se marcan **[M]**.

---

## 0. Resumen ejecutivo

1. **ksMultilayer_fresnel_nm4 es un shader de CSP, no de Kunos** [V]. Está en el pack `sdk-shaders` de
   x4fab (MIT) y "todos esos shaders están incluidos en CSP"; en AC "a pelo" solo existe si el jugador se
   instala el pack `ac-new.zip`. El shader vanilla equivalente es **ksMultilayer_fresnel_nm** (el que usa
   Kunos en carreteras y terreno, según los modders) [V/S].
   **Recomendación**: escribir en el KN5 `ksMultilayer_fresnel_nm` (txDiffuse + txMask + txDetailR/G/B/A +
   txDetailNM) y, como extra para CSP, subir a nm4 con `[SHADER_REPLACEMENT_...] SHADER=ksMultilayer_fresnel_nm4`
   + `tilingFixR/G/B/A` en `extension/ext_config.ini`. Así lo esencial se ve sin CSP y no rompe nada.
   No he encontrado en ninguna fuente los nombres de los 4 samplers de normal del nm4 [S]: no escribirlo a ciegas.
2. **acc-bakeryoptix** [V]: herramienta de CSP que hornea oclusión ambiental por vértice (VAO) a partir de un
   `.kn5` o `models.ini`; desde v21 (03/03/2026) usa **Vulkan RT** (NVIDIA RTX 20+, AMD RX 6000+, Intel Arc)
   con **fallback a CPU (Embree)**: ya no exige RTX/CUDA/OptiX. Se usa arrastrando el kn5 al exe o pasándolo como
   argumento; no hay flags de línea de comandos, todo va en `baked_shadow_params.ini` junto al kn5. Salida:
   `<nombre>.vao-patch` junto al kn5; el jugador lo copia a `assettocorsa/extension/vao-patches/`. Solo lo lee CSP.
   Repo sin fichero LICENSE (API: license null); el código lleva cabeceras BSD de NVIDIA (sample de OptiX Prime).
   **Alternativa vanilla**: el vértice KN5 no tiene color (pos+normal+uv+tangente) [V], así que "AO en vertex
   color" no existe en AC; lo compatible es hornear AO a textura y multiplicarla en `txDiffuse` (con ksMultilayer
   el detalle se superpone al diffuse, así que la AO del diffuse se conserva).
3. **Erosión**: Hydra (ozikazina) es un add-on legacy (`bl_info`, `"blender": (4, 0, 0)`, v1.1.0 de 06/2024)
   que hace `moderngl.get_context()` sobre el contexto OpenGL de la **interfaz** de Blender ("standalone crashes
   blender" en el comentario del código) [V] → **no funciona en `--background`** y no está probado en Blender 5.x.
   Un script NumPy propio tipo dandrino (rejilla, vectorizado) cuesta **~1 s a 230x225, ~22 s a 512², ~3 min a
   1024²** en este PC [M], se integra en `terreno_montana.py` y admite máscara de corredor de forma trivial.
   **Recomendación**: script NumPy propio (rejilla + reposo térmico, a 2 m y remuestreo a 4 m), con máscara de
   protección; Hydra solo como experimento manual en un Blender 4.x con interfaz, fuera del pipeline.

---

## 1. Shaders multilayer de Assetto Corsa

### 1.1 Familia y samplers

| Shader | Samplers (nombre exacto) | Origen |
|---|---|---|
| `ksMultilayer` | `txDiffuse`, `txMask`, `txDetailR`, `txDetailG`, `txDetailB`, `txDetailA` | Kunos [V] |
| `ksMultilayer_fresnel_nm` | los anteriores + `txDetailNM` | Kunos [V] |
| `ksMultilayer_objsp` | como `ksMultilayer` (variante de proyección por objeto) | Kunos [V] |
| `ksMultilayer_fresnel_nm4` | `txMask` citado; el resto "igual que fresnel_nm" pero con **cuatro normales** "mapeadas como las texturas de detalle" | CSP (x4fab) [V]; nombres de las 4 normales **no encontrados** [S] |

- [V] Lista de samplers por shader: hilo "Assetto Corsa Shaders, Texture maps list"
  (https://www.overtake.gg/threads/assetto-corsa-shaders-texture-maps-list.126166/). El `kn5-obj-converter` de
  `04_export/kn5_refs` lee exactamente esos nombres (`txDetailR/G/B/A`, `txDetailNM`, `txMask`).
- [V] Descripción oficial de nm4 (doc HTML de 753 bytes en el repo de CSP,
  https://github.com/ac-custom-shaders-patch/sdk-shaders/blob/master/new/html/ksMultilayer_fresnel_nm4/ksMultilayer_fresnel_nm4.html):
  "very similar to ksMultilayer_fresnel_nm, but with four separate normal textures instead of single one, mapped
  same as detail textures, and masked with txMask. Good for landscapes." Y: "Unlike original multilayer shader,
  this one has proper options for tiling fix, separate for each channel: tilingFixR, tilingFixG, tilingFixB and
  tilingFixA" (0 → 1 para activar); "tiling fix requires an extra texture sample, do not use it for textures
  which are too high res".
- [V] README de sdk-shaders (https://github.com/ac-custom-shaders-patch/sdk-shaders): nm4 = "alternative to
  'ksMultilayer_fresnel' with four normal maps aligned with detail maps instead of one texture mapped to main
  UV", "four separate options for fixed tiling, instead of ksEmissive trick". Packs: `ac-new.zip` "new shaders
  for vanilla AC", `sdk-new.zip` (ksEditor > 1.2.2), `sdk-old.zip`. "All those shaders are included in CSP."
  Licencia MIT.
- [V] Conversión automática: "enabling tiling fix converts the original ksMultilayer_fresnel to this new one,
  automatically" (Johnr777, moderador, https://assettocorsamods.net/goto/post?id=17039). Receta de movo
  (29/08/2024, https://assettocorsamods.net/goto/post?id=17042): poner `MultTilingFix = 1` en ksEditor o en
  ext_config, y entonces aparecen `tilingFixA/R/G/B`. Ejemplo literal:
  ```
  [SHADER_REPLACEMENT_...]
  MATERIALS = grass_1
  SHADER = ksMultilayer_fresnel_nm4
  PROP_... = tilingFixA, 0
  PROP_... = tilingFixR, 1
  PROP_... = tilingFixB, 1
  PROP_... = tilingFixG, 1
  DOUBLE_FACE_SHADOW_BIASED = 1
  ```
  ("This will make the terrain textures look less tiled"; el DOUBLE_FACE_SHADOW_BIASED evita que "el sol
  atraviese la colina".)
- [V] Sintaxis de shader replacement en la doc de CSP (https://cup.acstuff.club/docs/csp/general/shader-replacements):
  `MATERIALS = ...`, `MESHES = ...`, `SHADER = ...`, `PROP_0 = ksAmbient, 0.4`, `BLEND_MODE = ALPHA_BLEND`;
  "shader replacements are completely static, applied once either during loading or after config change".

### 1.2 Semántica de la máscara RGBA y de las propiedades

No hay documentación oficial de Kunos accesible en la web; lo que sigue viene de modders veteranos (LilSki,
Johnr777, Luchian) y es coherente entre fuentes.

- [V] La máscara va en el **mismo UV que el diffuse**: "the mask needs to match your uv's to work"
  (https://assettocorsamods.net/threads/need-some-help-clearing-up-with-terrain-masks.1207/); "the mask uses the
  UV of the diffuse" (Johnr777, https://assettocorsamods.net/threads/photo-quality-road-surface.834/page-5).
- [V] Cada canal selecciona una textura de detalle y los canales se mezclan: "Red is one type of grass, Green is
  another type of grass, and Blue is a 'road/gravel' type of detail"
  (https://assettocorsamods.net/threads/grass-scenery.2800/). En la guía de carreteras de LilSki (17/12/2016,
  https://assettocorsamods.net/goto/post?id=3602): rojo = detalle principal, azul = grietas, "purple" = rojo
  mezclado con azul, "even mix in the green channel if you want with another detail texture". El canal alfa
  (txDetailA) es el cuarto detalle [V por lista de samplers].
- [V] El detalle **se superpone** al diffuse, no lo sustituye: "The ksMultilayer shader *overlays* detail
  textures, onto the main diffuse texture, it doesn't *replace* them" (hilo 1207). Con diffuse blanco/neutro se
  ve solo el detalle.
- [V] `multR/G/B/A` = **repetición (tiling) de cada detalle**: "the multR slot in the editor controls the tiling
  for your detail texture" (hilo 1207). [S] Unidad: Xuacu pregunta "1 = 1x1 meter value?" sin respuesta
  confirmada; interpretar como multiplicador de UV.
- [V] `detailNMMult`: "You adjust the normal map resolution with the two numbers in detailNMMult" (LilSki).
  [S] Al ser dos números, lo más probable es que se guarde en el campo B (vec2) de la propiedad KN5.
- [V] Alfa del diffuse y de cada detalle = **nivel especular**: "the alpha channel here is your specular level.
  White is 100% and black is 0%" (LilSki); consejo del hilo 1207: los detalles necesitan "a really dark alpha
  channel" (Photoshop exporta alfa negro como blanco: usar #010101).
- [V] Fresnel (descripción de Johnr777/Xuacu, pág. 5 del hilo 834): `fresnelC` = reflectividad base (mirando
  perpendicular), `fresnelMaxLevel` = tope de reflectividad en ángulo rasante, `fresnelEXP` = curva de caída.
  [V] Ejemplo de valores Kunos (config de CSP para `ks_nordschleife`, material `asph?`,
  https://raw.githubusercontent.com/ac-custom-shaders-patch/acc-extension-config/master/config/tracks/ks_nordschleife.ini):
  `ksSpecular 0.6`, `ksDiffuse 0.2`, `fresnelC 0.08`. Para terreno mate: fresnelC/fresnelMaxLevel bajos [S].
- [S] `magicMult`: citado en los hilos 1207 y 834 como propiedad del multilayer ("decides how to mix diffuse
  with details: 0 is black, 1 is okay, more than one seems emissive"). No verificado en ninguna lista oficial.
- [V] Limitación: "ksMultilayer_fresnel_nm doesn't support a blend mode other than opaque"
  (https://assettocorsamods.net/threads/road-to-terrain-transition-issue.3475/): no sirve para fundir el borde
  terreno/asfalto con alfa; el fundido se hace con la máscara o con una malla de transición aparte.
- [S] **Proyección de los detalles**: fuentes contradictorias. Johnr777 dice que "the detail maps are global";
  un resumen de buscador afirma "top-down projection"; la guía de LilSki implica que el detalle repite a lo largo
  del UV de la carretera (multR). Como no está claro, dar al TERRENO un **UV planar cenital** (x,y del mundo
  escalados) de modo que ambas interpretaciones coincidan, y pintar diffuse y máscara en ese mismo espacio.
- [V] Tamaños de ejemplo (LilSki, carretera): diffuse 1024x4096 DXT5, máscara 128x512 DXT3 (puede ser mucho más
  pequeña que el diffuse), detalles 1024² DXT5, grietas 512² DXT3, normal 1024² DXT1, 4 mipmaps.
- [S] Pistas Kunos: nm4 es de CSP, luego **ninguna pista Kunos lo usa de forma nativa**. Las pistas Kunos usan
  `ksMultilayer_fresnel_nm` en carreteras y terreno ("ksMultilayer_fresnel_nm is the shader that Kunos uses in
  official tracks", Luchian en https://assettocorsamods.net/threads/terrain-texture.1073/, y "You don't have to use
  ALL detail slots, just the one you need (like grass detail)"). No he podido comprobarlo con un volcado de kn5
  Kunos (no hay AC en este PC).

### 1.3 Cómo escribirlo en un KN5 v5 (con `04_export/kn5_writer_opt.py`)

Estructura binaria del material, verificada en el writer propio y en las referencias locales
(`kn5_refs/blender-assetto-corsa-tools/exporter/material_writer.py`, `kn5_refs/actools/Kn5Material.cs`,
`kn5_refs/kn5-obj-converter/convert.py`) [V]:

```
string nombre
string shader                      # p.ej. 'ksMultilayer_fresnel_nm'
u8     alphaBlendMode              # 0 Opaque, 1 AlphaBlend, 2 AlphaToCoverage
u8     alphaTested
i32    depthMode                   # 0 DepthNormal, 1 DepthNoWrite, 2 DepthOff
i32    nProps; por propiedad: string nombre, f32 A, 2xf32 B, 3xf32 C, 4xf32 D
i32    nSamplers; por sampler:  string nombre, i32 slot, string nombreTextura
```
La sección de texturas va antes (count; por textura: i32 activa=1, string nombre, blob). El writer actual
escribe siempre `ksPerPixel`, 6 propiedades (`ksAmbient 0.45, ksDiffuse 0.55, ksSpecular 0.15, ksSpecularEXP 24,
ksEmissive 0, ksAlphaRef 0`) y un único sampler `txDiffuse` con slot 0 [V, líneas 83-84 y 319-338].

Propuesta de material de terreno (vanilla, sin CSP):

| Campo | Valor propuesto | Estado |
|---|---|---|
| shader | `ksMultilayer_fresnel_nm` | [V] existe en vanilla |
| alphaBlendMode / alphaTested / depthMode | 0 / 0 / 0 | [V] solo opaco |
| props estándar | `ksAmbient`, `ksDiffuse`, `ksSpecular` (bajo, 0.05-0.15), `ksSpecularEXP`, `ksEmissive 0`, `ksAlphaRef 0` | [V] nombres; valores [S] |
| `multR`, `multG`, `multB`, `multA` | tiling de cada detalle (A = float). Con UV planar de 1 unidad = toda la rejilla (~920 m), un detalle de 4 m de periodo necesita mult ≈ 230 | [V] nombre, [S] unidad |
| `detailNMMult` | tiling de la normal; probablemente B = (u, v) | [V] nombre, [S] campo |
| `fresnelC`, `fresnelEXP`, `fresnelMaxLevel` | p.ej. 0.02 / 3 / 0.1 para tierra mate | [V] nombres, [S] valores |
| samplers | `txDiffuse` 0, `txMask` 1, `txDetailR` 2, `txDetailG` 3, `txDetailB` 4, `txDetailA` 5, `txDetailNM` 6 | [V] nombres; [S] números de slot |

- [V] Slots: el exportador de referencia de Blender usa `txDiffuse 0, txNormal 1, txMaps 2, txDetail 3,
  txDetailNM 4, txEmissive 5, txEnvironment 6` y asigna a cualquier otro nombre un número correlativo; el
  `kn5-obj-converter` lee el slot y lo ignora. [S] Inferencia: AC enlaza los samplers **por nombre** y el slot
  no es crítico; aun así, escribirlos en el orden de la tabla y validar con `kn5_check.py`.
- [S] Formato de las texturas embebidas: el writer actual genera blobs con `construir_textura()`; para una
  máscara RGBA con transiciones suaves conviene DDS DXT5 (o BC7) con mipmaps; PNG embebido también carga en AC
  pero sin mipmaps propios. Comprobar qué formato produce hoy el writer antes de añadir 6 samplers.
- [S] Normalización de la máscara: ninguna fuente dice si el shader renormaliza R+G+B+A. Pintar la máscara de
  modo que la suma por texel sea ≈ 1 (un canal dominante, transiciones de 2-4 texeles) para no depender de ello.
- Semántica propuesta para Porto Corsa (PLAN_USUARIO 3): R = matorral (oliva/salvia), G = hierba seca dorada,
  B = tierra/arena, A = roca caliza. La máscara se calcula en NumPy desde la rejilla del terreno (pendiente,
  altura, distancia a pista/mar; ya existe `mascara_roca` en `terreno_montana.py`) y se hornea a una imagen en el
  UV planar: a 4096² sobre ~920x900 m sale 0.22 m/texel (2048² → 0.45 m). Esto elimina de raíz el defecto 4 del
  director (bandas en dientes de sierra, bordes en escalera, hierba estirada): hoy la roca/hierba es un atributo
  **por vértice** interpolado en triángulos de 4 m; con txMask es **por texel**.
- Hierba estirada en caras verticales: con UV planar cenital cualquier textura se estira en paredes. Soluciones
  [S]: (a) en la máscara, A = roca donde pendiente > 35-40° (así la textura estirada es roca, menos visible);
  (b) para los desmontes y acantilados, malla aparte con UV por proyección lateral (triplanar manual: 2-3 mallas
  por eje) y material `ksPerPixelNM` de caliza; (c) con CSP, nm4 + tilingFix reduce el patrón repetido.
- **nm4 en el KN5: no.** Al no estar documentados los 4 samplers de normal (ni en el HTML del shader, ni en el
  README, ni en foros), escribirlo a ciegas puede dejar el material sin normales o sin shader en AC vanilla
  (comportamiento ante shader desconocido no verificado [S]). Hacerlo por `ext_config.ini` como extra CSP.

### 1.4 Texturas de detalle CC0 (solo listado; no se descarga nada)

[S] Candidatas (4 detalles + normales, 1024-2048², CC0): Poly Haven (https://polyhaven.com/textures, p.ej.
`aerial_grass_rock`, `brown_mud_leaves_01`, `rock_face`, `coast_sand_rocks_02`) y ambientCG
(https://ambientcg.com, p.ej. `Grass004`, `Ground037`, `Rock030`, `Gravel022`). Tamaños típicos 10-40 MB por
set de 2K (confirmar en la ficha; los nombres son de memoria y hay que comprobarlos en la web). Recolorear a la
paleta (oliva/salvia, dorado, ocre, gris cálido) antes de embeber; el diffuse del terreno puede ser un mapa de
color de baja resolución (2048²) con AO horneada (ver 2.3).

---

## 2. acc-bakeryoptix: VAO (vertex ambient occlusion) para CSP

### 2.1 Qué es y qué hace [V]

- Repo: https://github.com/ac-custom-shaders-patch/acc-bakeryoptix (C++, rama `master`, último push 04/05/2026).
  README: "A tool to bake vertex ambient occlusion for racing simulator Assetto Corsa with Custom Shaders
  Patch", "Embree for CPU-only baking and Vulcan for GPU-accelerated baking available, functional on any
  hardware". Pistas: ".kn5" y ".ini" como entrada, "Special trees baking (without self-occlusion, with normals
  facing up)", "Special grass baking (without any shadows from grass, with normals facing up)", "Baking of
  shadows cast by CSP procedural trees", re-horneado de zonas oscuras con más rayos. General: rebotes de luz,
  brillo/opacidad/gamma, ajustes por objeto.
- Doc oficial de CSP (https://cup.acstuff.club/docs/csp/tracks/vertex-ao): "Per-vertex ambient occlusion helps
  to add some smooth ambient shadows at zero FPS cost". Dos formas de guardarlo: "modifying original KN5 and
  replacing some unnecessary data in there by occlusion values" o un fichero ".vao-patch" aparte ("if you'd
  change something like a texture or material in original KN5, you wouldn't need to rebake it").
  [S] Los "datos innecesarios" sustituidos son probablemente las tangentes.
- Releases (https://api.github.com/repos/ac-custom-shaders-patch/acc-bakeryoptix/releases): v17 (25/10/2022,
  `build-v17-optix.zip`, 451 KB) "uses OptiX ... with support for RTX GPUs"; **v21 "Liberating update"
  (03/03/2026, `build-v21.zip`, 1.8 MB): "OptiX is replaced with Vulcan RT, so hardware-accelerated baking
  should work on most modern GPUs; If Vulcan RT is not available, baking will be done on CPU using Embree"**;
  v22 (04/05/2026, `build-v22.zip`, 1.8 MB): "Fix for missing or misconfigured driver model crashing the bakery".
- Requisitos (README, "Tips"): "GPU baking requires NVIDIA RTX 20…, AMD RX 6000, Intel Arc A-Series or newer";
  si no, "Embree should be pretty fast as well". Conclusión: **ya no hace falta RTX ni CUDA/OptiX**; funciona
  en CPU en cualquier PC Windows.

### 2.2 Uso por línea de comandos, entrada y salida [V, leído en `bakeryoptix/main.cpp`]

- **No hay flags**: `main` recorre `argv` y hace `file_processor(argv[i]).run()` por cada ruta; sin argumentos
  abre un diálogo de Windows (`GetOpenFileNameW`). Es decir: `bakeryoptix.exe ruta\porto_corsa.kn5` o
  `bakeryoptix.exe ruta\models.ini`, o arrastrar el kn5 sobre el exe ("Just take the KN5 file ... and drop it
  onto the BakeryOptix.exe", xezez, GTPlanet 17/04/2020,
  https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-1016).
- **Configuración** en `baked_shadow_params.ini` (también `baked shadow params.ini`), buscada en este orden:
  carpeta del fichero de entrada → carpeta del exe; `baked_shadow_params__local.ini` como override local.
  Modo `MODE = AUTO` (CAR si la ruta contiene `/cars/`, si no TRACK). Secciones `[GENERAL]` (`USE_VULKAN = true`,
  `BATCH_SIZE`, ...) y `[MODE_TRACK]` / `[MODE_CAR]` con, entre otros: `SAMPLES = AUTO`, `RAYS_PER_SAMPLE = 64`,
  `BRIGHTNESS = 1.02`, `GAMMA = 0.92`, `OPACITY = 0.97`, `BOUNCES = 5`, `FILTER_MODE = LEAST_SQUARES`,
  `EXCLUDE_FROM_BAKING`, `FORCE_PASSING_LIGHT`, `BAKE_AS_TREES`, `BAKE_AS_GRASS`, `TREES_SHADOW_FACTOR = 1.0`,
  `USE_ENCLOSING_BLOCKER`, `USE_GROUND`, `TUNNEL_FIX_<n>_NAMES/_OFFSET`, `EXTRA_BLOCKERS_<n>_FILE`,
  `EXTRA_ADJUSTMENT_<n>_NAMES/_MULT/_OFFSET/_GAMMA`, `AO_SAMPLES_AI_LANES`, `AO_SAMPLES_PHYSICS_SURFACES`,
  flags `EXT_PROCEDURAL_TREES_*`, `EXT_REBAKE_DARK_OBJECTS`. Los nombres de malla admiten patrones.
  El ini de ejemplo va dentro del zip de la release (no está en el repo) [V por listado de la raíz].
- **Salida**: `<nombre_entrada>.vao-patch` en la misma carpeta (`model.kn5` → `model.vao-patch`; para LODs de
  coche, `main_geometry.vao-patch`). El código no menciona `extension/vao-patches`.
- **Dónde lo pone el jugador** (tutorial de assettocorsamods con la herramienta antigua CustomTracksBakery,
  https://assettocorsamods.net/threads/creating-a-vao-patch.1858/; y https://fileinfo.com/extension/vao-patch):
  para probar, en la carpeta de la pista; definitivo, en `assettocorsa\extension\vao-patches\<pista>.vao-patch`
  (varios layouts: `<pista>__<layout>.vao-patch`). CSP lo muestra en su menú "TRACKS VAO". [S] No he verificado
  si CSP también lo carga desde `content/tracks/<pista>/extension/`; conviene entregar instrucciones de copia.
- [S] Tiempo: el tutorial de la herramienta antigua habla de "one or two minutes"; para nuestros 4.6 M de
  triángulos en CPU (Embree) cuento con minutos a decenas de minutos. Solo CSP lo usa; AC vanilla lo ignora.
- **Licencia** [V]: no hay fichero LICENSE (listado de la raíz por API; `license: null`). `main.cpp` empieza con
  la cabecera BSD-3 "Copyright (c) 2018, NVIDIA CORPORATION" (deriva del sample "OptiX Prime baking", que el
  README acredita junto con Intel Embree). [S] Uso del binario publicado en Releases: práctica general de la
  comunidad; para redistribuir el **código** habría que preguntar al autor. El `.vao-patch` que generemos es
  nuestro (datos derivados de nuestra malla).

### 2.3 Plan para Porto Corsa y alternativa vanilla

- Flujo propuesto (extra CSP, no rompe nada): exportar `porto_corsa.kn5` (ya lo hace `04_export`), poner al lado
  un `baked_shadow_params.ini` con `[MODE_TRACK]`: `BAKE_AS_TREES = ARBOL*, VEG_*` (los billboards/árboles),
  `BAKE_AS_GRASS = GRASS*`, `EXCLUDE_FROM_BAKING = 1WALL_invisible*, *_invisible, *cierre*` (las mallas de
  colisión con `isRenderable=0` no deberían ocluir; precaución [S]), `FORCE_PASSING_LIGHT` para vallas/mallas
  finas, `TUNNEL_FIX_0_NAMES = TUNEL_*` si el túnel del McLaren sale negro. Ejecutar
  `bakeryoptix.exe porto_corsa.kn5` en este PC (CPU si no hay GPU RT), obtener `porto_corsa.vao-patch` y meterlo
  en el zip con un README: "copiar a assettocorsa/extension/vao-patches/". Validar solo visualmente en el PC del
  amigo (aquí no hay AC). Requiere permiso del usuario para descargar `build-v22.zip` (1.8 MB).
- **"AO en vertex color" no existe en AC vanilla** [V]: el vértice KN5 que escribe `kn5_writer_opt.py`
  (`con_tangentes`) y el exportador de referencia es posición(3) + normal(3) + uv(2) + tangente(3), sin color.
  El VAO de CSP es justamente la vía para AO por vértice.
- Alternativa compatible con AC a pelo [S, práctica habitual: "AC uses baked AO since it doesn't have realtime
  AO", GTPlanet]: hornear AO en Blender (Cycles, bake AO) a textura y **multiplicarla en `txDiffuse`**. Con
  ksMultilayer el detalle se superpone al diffuse, así que un diffuse de baja resolución (2048² para todo el
  terreno, 0.45 m/texel) con color base de la paleta × AO horneada da "oclusión en los huecos" y variación de
  color sin coste en el shader. Para props (McLaren, roca del lazo, casas) un atlas AO por objeto en su propio
  UV. Coste [S]: minutos por bake a 2048-4096² con Cycles en GPU; sin GPU, decenas de minutos. Esto cubre el
  punto 3 del PLAN_USUARIO ("oclusión ambiental horneada y, en Assetto Corsa, VAO con acc-bakeryoptix") en sus
  dos mitades: AO en textura siempre + VAO como extra CSP.

---

## 3. Erosión hidráulica del heightmap

### 3.1 Hydra (ozikazina/Hydra)

Hechos [V] (https://github.com/ozikazina/Hydra, API del repo, `src/hydra/__init__.py`, `src/hydra/common.py`,
README y releases):

- "Blender hydraulic erosion addon using OpenGL." Licencia MIT; es la implementación de un TFG de la Brno
  University of Technology. Rama `main`, último push 17/11/2025, 40 estrellas, 3 issues abiertas.
- Releases: v1.0.0 (12/11/2023), v1.0.1 "Blender 4.0" (26/11/2023, "Update to support Blender 4.0"),
  **v1.1.0 "Simulation overhaul" (16/06/2024, `Hydra_1.1.0.zip`, 57 KB)**: nuevo tipo de erosión de agua,
  nieve, partículas "up to 60x" más rápidas en iGPU, generación de heightmaps, geometry nodes, UI nueva.
- `bl_info`: `"version": (1, 1, 0)`, `"blender": (4, 0, 0)`. Es un **add-on legacy** (`bl_info`, no hay
  `blender_manifest.toml` en el repo); se instala "import the zip file into Blender add-ons". Dependencias
  externas (~5 MB): **ModernGL ≥ 5.10** + glcontext, instaladas con un botón en las preferencias (pip dentro del
  Python de Blender; "will probably require elevated privileges"; en Linux/Wayland puede fallar
  "Failed to initialize OpenGL context").
- **Contexto GL**: `common.py` → `self.context = mgl.get_context()  #standalone crashes blender; create_context
  doesn't work with wayland`. Es decir, se **engancha al contexto OpenGL de la ventana de Blender**; no crea uno
  propio.
- Funciones: erosión de agua por **partículas** (iteraciones, lifetime, smoothness, deposition, capacity,
  acceleration, drag), por **tuberías/flujo** (hardness, capacity, rain), **térmica** (reposo), nieve, transporte
  de color, flujo. "Both types also support variable hardness in the Advanced settings." Trabaja sobre
  heightmaps internos "Source"/"Result" de 256² a 2048² a partir de un objeto o una imagen; el resultado se
  aplica como imagen, nodos, modificador, displacement, bump o malla. Planes futuros: textura de fuente de agua,
  erosión planetaria, CUDA.
- README: no declara versiones de Blender soportadas más allá del `bl_info`; en Blender Artists (27/11/2023):
  "latest release work with blender 4 alpha and first release work with blender 3.6"
  (https://blenderartists.org/t/new-hydrolic-erosion-addon-for-blender/1494763).

Conclusiones sobre Blender 5.1 headless:

- [V+S] **No funciona en `blender --background`**: en modo background no hay ventana ni contexto OpenGL al que
  `moderngl.get_context()` pueda engancharse, y el propio autor descarta el contexto standalone ("crashes
  blender"). Esto es inferencia directa del código, no una prueba ejecutada (no he lanzado Blender).
- [S] En Blender 5.1 **con interfaz** tampoco está garantizado: el add-on es de la era 4.0 y Blender 5.0 quitó
  `bgl`, cambió el almacenamiento de `bpy.props` y la API de acciones
  (https://developer.blender.org/docs/release_notes/5.0/python_api/); Blender 5.1 lleva Python 3.13 (la rueda
  de ModernGL/glcontext tendría que existir para 3.13). Además el backend por defecto: 5.0 siguió en OpenGL
  (https://www.phoronix.com/news/Blender-5.0-Vulkan-OpenGL-RAM, 11/08/2025) y, según los resultados de búsqueda,
  Vulkan pasa a ser el backend por defecto en Windows/Linux en 5.3; con Vulkan activo `get_context()` no
  encuentra contexto OpenGL. No he encontrado ninguna confirmación de que Hydra funcione en 5.x.
- [V] Hydra no tiene máscara de protección como tal; lo más parecido es "variable hardness" (dureza variable),
  que serviría para endurecer el corredor de la pista, pero habría que ajustarlo a mano en la UI.
- Veredicto: **incompatible con el pipeline** ("todo se genera por código", Blender solo por cola headless).
  Útil como experimento manual en un Blender 4.0-4.2 con interfaz, a lo sumo para calibrar visualmente qué
  intensidad de erosión queremos y reproducirla luego con el script propio.

### 3.2 Script NumPy propio (dandrino/terrain-erosion-3-ways y método de gotas)

#### 3.2.1 Método de rejilla (dandrino, `simulation.py`) [V]

- Repo https://github.com/dandrino/terrain-erosion-3-ways (MIT; Python 3.6 + NumPy; tres métodos:
  simulación, GAN y redes de ríos). Pasos del método de simulación (README): "1. Increment the water level (as
  in via precipitation)... 2. Compute the terrain gradient. 3. Determine the sediment capacity for each point.
  4. Erode or deposit sediment. 5. Displace water and sediment downhill. 6. Evaporate some fraction of the
  water away."
- Constantes de `simulation.py` (https://raw.githubusercontent.com/dandrino/terrain-erosion-3-ways/master/simulation.py):
  `full_width = 200`, `dim = 512`, `cell_width = full_width / dim`, `rain_rate = 0.0008 * cell_area`,
  `evaporation_rate = 0.0005`, `min_height_delta = 0.05`, `repose_slope = 0.03`, `gravity = 30.0`,
  `gradient_sigma = 0.5`, `sediment_capacity_constant = 50.0`, `dissolving_rate = 0.25`,
  `deposition_rate = 0.001`, `iterations = int(1.4 * dim)`. Todo vectorizado sobre la rejilla (`np.roll`,
  lerp bilineal manual, blur gaussiano por FFT en `util.py`): O(N²) por iteración.
- Coste declarado: "you need O(N) iterations, which puts the overall runtime at O(N³)"; "doubling the grid
  dimension can result in 8x execution time". Contras: "Parameter hell. There are around 10 constants that need
  to be set"; "Fairly inefficient". Pros: los rasgos "simply emerge from running these rules"; fácil de
  vectorizar/paralelizar.

#### 3.2.2 Método de gotas (Beyer 2015 / SebLague) [V]

- Implementación de referencia: https://github.com/SebLague/Hydraulic-Erosion (`Assets/Scripts/Erosion.cs`).
  Parámetros por defecto: `erosionRadius 3` [2..8], `inertia 0.05`, `sedimentCapacityFactor 4`,
  `minSedimentCapacity 0.01`, `erodeSpeed 0.3`, `depositSpeed 0.3`, `evaporateSpeed 0.01`, `gravity 4`,
  `maxDropletLifetime 30`, `initialWaterVolume 1`, `initialSpeed 1`. Bucle por gota: posición aleatoria →
  altura/gradiente bilineal → dirección con inercia → mover 1 celda → capacidad = f(velocidad, agua, desnivel)
  → depositar (si exceso o cuesta arriba) o erosionar con brocha de radio `erosionRadius` → actualizar velocidad,
  evaporar → hasta agotar lifetime. [S] Número de gotas típico: 50 000-500 000 para 512²-1024².
- [S] En NumPy puro un bucle por gota es lento (~3 M pasos para 100 k gotas × 30 → decenas de segundos a
  minutos); vectorizando lotes de miles de gotas en paralelo con `np.add.at` para la brocha baja a segundos.
  Da barrancos finos y abanicos de depósito más "dibujados" que el método de rejilla; combina bien como segunda
  pasada ligera sobre el macizo (fondo no conducible).

#### 3.2.3 Coste medido en este PC [M]

Reimplementé los pasos del método de rejilla (lluvia, gradiente, muestreo bilineal, capacidad, erosión/
depósito, desplazamiento por splat de 4 vecinos, reposo con blur gaussiano, velocidad, evaporación) en
`scratchpad/erosion_bench/bench_grid.py` (Python 3.12.10, NumPy 2.5.2, SciPy 1.18.1; usa
`scipy.ndimage.map_coordinates` y `gaussian_filter` en lugar del lerp manual y el blur FFT de dandrino, así que es
una aproximación, no el código original):

| Rejilla | ms/iteración | Iteraciones 1.4·dim | Tiempo total |
|---|---|---|---|
| 225x230 (celda 4 m, la actual) | 2.3 | 322 | **0.75 s** |
| 512x512 (≈ celda 1.8 m) | 30.5 | 716 | **~22 s** (extrapolado de 60 it.) |
| 1024x1024 (≈ celda 0.9 m) | 127 | 1433 | **~3 min** (extrapolado de 25 it.) |

[S] Con el blur FFT original a 1024² el coste subiría quizá ×1.5-2 (5-6 min). Sigue siendo asumible en el
pipeline de `preparar_geometria.py`, que ya corre en Python del sistema con numpy/scipy.

#### 3.2.4 Resolución, protección del corredor y encaje en el pipeline [S, propuesta]

- **Resolución**: la rejilla actual es de 4 m (230x225 ≈ 920x900 m). A 4 m solo salen vaguadas de ≥ 8-12 m de
  ancho (2-3 celdas): sirve para "crestas y barrancos" del macizo (PLAN 1) pero no para surcos finos. Propuesta:
  interpolar a **2 m (460x450, ~6-8 s)** o 1 m (≈1024², ~3-5 min), erosionar, y (a) remuestrear a 4 m para la
  malla y (b) guardar la diferencia fina (1-2 m) como **mapa de normales/detalle** (`txDetailNM`) o como
  entrada de la máscara (canal "tierra" en las vaguadas, "roca" en las crestas de las costillas). Así el detalle
  que la malla de 4 m no puede mostrar llega por el material.
- **Máscara de protección del corredor** M(x,y) ∈ [0,1] (1 = protegido), con borde suavizado 2-3 celdas:
  asfalto + arcenes (w/2+6 m), caja del pit, terrazas del pueblo, Loews, estribos del viaducto, miradores,
  cala del casino, costa (celdas de mar fijadas al fondo marino). Tres mecanismos combinables, de más simple a
  más fiel: (1) **dureza**: multiplicar `dissolving_rate` y el depósito por (1-M) (equivale al "variable
  hardness" de Hydra); (2) **restauración**: cada k iteraciones `z = M·z0 + (1-M)·z` (el corredor vuelve a su
  cota); (3) para gotas: matar la gota al entrar en M > 0.5 o anular su erosión. Después de la erosión volver a
  aplicar las acotaciones de desmonte/terraplén de `terreno_montana.py` (z ≤ z_pista+0.4+... y z ≥ z_pista-0.6-...)
  como clamp final, de modo que la pista siga "tallada" y los inspectores no cambien.
- **Unidades**: dandrino normaliza el terreno a [0,1] sobre `full_width = 200`; con alturas de 0-235 m y
  920 m de ancho hay que escalar z a unidades de celda o re-tunear `min_height_delta`, `gravity` y
  `sediment_capacity_constant`. Empezar con el terreno en unidades de celda (z/cell), 150-300 iteraciones, y
  calibrar con `renders/qa/terreno_hillshade.png` (ya existe) comparando antes/después.
- **Erosión térmica** (reposo): el paso `apply_slippage` de dandrino (blur donde pendiente > `repose_slope`) ya
  la incluye; en nuestro caso usar ángulos de reposo distintos por material (hierba/tierra 30-35°, roca sin
  reposo) con la `mascara_roca` existente, para que las caras de roca sigan escarpadas (PLAN 2: roca > 35-40°).
- **Dónde**: función `erosionar(z_grid, cell, mascara_protegida, mascara_roca, iters, semilla)` en
  `terreno_montana.py` (o módulo `erosion.py` junto a él), llamada tras construir el macizo y antes de
  banqueta/desmonte/terrazas; determinista con semilla; imprime % de celdas modificadas y máximo cambio en el
  corredor (debe ser 0). Un solo PNG de QA antes/después.

### 3.3 Recomendación

**Script NumPy propio, método de rejilla (dandrino) a 2 m con reposo térmico por material y máscara de corredor;
pasada opcional de gotas sobre el macizo.** Motivos: corre headless en el pipeline actual (Python del sistema),
cuesta segundos, es determinista y reproducible, y la máscara de protección es una línea de código. Hydra queda
descartado para el pipeline (depende de la ventana OpenGL de Blender, add-on de la era 4.0 sin soporte declarado
para 5.x, sin modo background); solo tiene sentido como experimento manual fuera de este PC/flujo.

---

## 4. Relación con el veredicto del director (`_rev/director_final.md`)

- Defecto 3 (desmontes tipo cantera/parches pintados) y 4 (dientes de sierra, escaleras, hierba estirada):
  máscara **por texel** (txMask) en lugar del atributo por vértice + UV planar + roca por pendiente; nm4 con
  tilingFix como extra CSP.
- Defecto 6 (la tierra no se lee como montaña tallada) y macizo "cono verde uniforme" (01, 21): erosión de
  rejilla sobre el macizo con corredor protegido → crestas y vaguadas; reposo por material mantiene las paredes.
- Defecto 7 (roca del lazo/peñón lisos): el mismo material multilayer (canal A = caliza con txDetailNM de
  estratos) en vez de MAT_PPUEBLO_roca plano; AO horneada en txDiffuse para "oclusión en los huecos".
- "Oclusión ambiental" del PLAN 2-3: AO a textura (vanilla) + `porto_corsa.vao-patch` (CSP) entregado en el zip.

## 5. Fuentes (URL → qué se verificó)

- https://github.com/ac-custom-shaders-patch/sdk-shaders — README: packs, "included in CSP", MIT, descripción nm4.
- https://raw.githubusercontent.com/ac-custom-shaders-patch/sdk-shaders/master/new/html/ksMultilayer_fresnel_nm4/ksMultilayer_fresnel_nm4.html — texto oficial del shader nm4, tilingFixR/G/B/A.
- https://www.overtake.gg/threads/assetto-corsa-shaders-texture-maps-list.126166/ — samplers de ksMultilayer, _fresnel_nm, _objsp.
- https://assettocorsamods.net/goto/post?id=17039 y ?id=17042 — conversión automática a nm4; `MultTilingFix`; ejemplo ext_config.
- https://cup.acstuff.club/docs/csp/general/shader-replacements — sintaxis SHADER_REPLACEMENT, estático.
- https://assettocorsamods.net/goto/post?id=3602 — guía LilSki: canales de la máscara, alfa = especular, tamaños.
- https://assettocorsamods.net/threads/need-some-help-clearing-up-with-terrain-masks.1207/ — máscara en UV del diffuse, overlay, multR = tiling, alfa oscuro.
- https://assettocorsamods.net/threads/grass-scenery.2800/ — R/G/B = tipos de hierba/grava para terreno.
- https://assettocorsamods.net/threads/photo-quality-road-surface.834/page-5 — fresnelC/EXP/MaxLevel, detailNMMult, "detail maps are global".
- https://assettocorsamods.net/threads/road-to-terrain-transition-issue.3475/ — solo blend opaco.
- https://assettocorsamods.net/threads/terrain-texture.1073/ — Kunos usa ksMultilayer_fresnel_nm; no hace falta usar todos los slots.
- https://raw.githubusercontent.com/ac-custom-shaders-patch/acc-extension-config/master/config/tracks/ks_nordschleife.ini — valores Kunos (ksSpecular 0.6, ksDiffuse 0.2, fresnelC 0.08).
- Locales (solo lectura): `04_export/kn5_writer_opt.py`, `04_export/kn5_refs/blender-assetto-corsa-tools/exporter/material_writer.py`, `kn5_refs/actools/Kn5Material.cs`, `kn5_refs/kn5-obj-converter/convert.py` — estructura de material/sampler/propiedad y vértice KN5.
- https://github.com/ac-custom-shaders-patch/acc-bakeryoptix (+ README crudo, `bakeryoptix/main.cpp`, API de releases y de contenidos) — qué es, Vulkan/Embree, requisitos, argumentos, ini, salida, licencia.
- https://cup.acstuff.club/docs/csp/tracks/vertex-ao — definición oficial de VAO y dos modos de almacenamiento.
- https://assettocorsamods.net/threads/creating-a-vao-patch.1858/ y https://fileinfo.com/extension/vao-patch — carpeta `extension/vao-patches`, nombres por layout.
- https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-1016 — uso por arrastre.
- https://github.com/ozikazina/Hydra (+ API, `src/hydra/__init__.py`, `src/hydra/common.py`, README, releases) — bl_info 4.0.0, get_context, ModernGL ≥ 5.10, MIT, fechas.
- https://blenderartists.org/t/new-hydrolic-erosion-addon-for-blender/1494763 — "blender 4 alpha / 3.6".
- https://developer.blender.org/docs/release_notes/5.0/python_api/ y https://developer.blender.org/docs/release_notes/5.1/ — cambios de API 5.0, Python 3.13 en 5.1.
- https://www.phoronix.com/news/Blender-5.0-Vulkan-OpenGL-RAM — 5.0 sigue en OpenGL por defecto.
- https://github.com/dandrino/terrain-erosion-3-ways (+ README y `simulation.py`, `util.py` crudos) — algoritmo, constantes, O(N³), MIT.
- https://github.com/SebLague/Hydraulic-Erosion (`Assets/Scripts/Erosion.cs`) — parámetros del método de gotas.
- Benchmark propio: `scratchpad/erosion_bench/bench_grid.py` (no forma parte del proyecto).

## 6. Tabla resumen: verificado vs supuesto

| Afirmación | Estado |
|---|---|
| nm4 es shader de CSP, incluido en CSP; en vanilla solo con el pack ac-new.zip | [V] |
| Samplers de ksMultilayer y _fresnel_nm (txDiffuse, txMask, txDetailR/G/B/A, txDetailNM) | [V] |
| Nombres de los 4 samplers de normal de nm4 | **no encontrados** [S] |
| Máscara en UV del diffuse; canales = detalles; detalle se superpone; alfa = especular; multR = tiling | [V] (foros) |
| detailNMMult en campo B (vec2); unidad de mult; magicMult; slots numéricos | [S] |
| Proyección cenital o por UV de los detalles | contradictorio → UV planar [S] |
| Estructura binaria del material KN5 y vértice sin color | [V] (código local) |
| acc-bakeryoptix: v21/v22 Vulkan RT + Embree, sin RTX obligatorio; sin flags; ini; salida .vao-patch | [V] |
| Carpeta extension/vao-patches | [V] (tutorial/fileinfo), no en el código |
| Licencia de acc-bakeryoptix | sin LICENSE; cabeceras BSD NVIDIA [V]; uso del binario [S] |
| Hydra: bl_info 4.0.0, get_context sobre la ventana, ModernGL ≥ 5.10, MIT, v1.1.0 06/2024 | [V] |
| Hydra no funciona en --background ni está probado en 5.x | [V+S] inferido del código, no ejecutado |
| Constantes y complejidad del método de rejilla de dandrino; parámetros de gotas de SebLague | [V] |
| Coste 0.75 s / 22 s / 3 min (230², 512², 1024²) | [M] aproximación propia |
| Diseño de máscara de corredor y encaje en terreno_montana.py | [S] propuesta |
