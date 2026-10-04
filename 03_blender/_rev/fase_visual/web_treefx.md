# Investigación web: TreeFX de CSP y alternativas sin CSP para los árboles de Porto Corsa

Fecha: 04/10/2026. Autor: agente investigador (fase visual, bloque "vegetación"). Solo lectura: no se ha
modificado ningún fichero del proyecto ni se ha descargado nada; no se ha lanzado Blender.

Convención de este informe:
- **[V]** = hecho verificado en la fuente citada (cita corta o clave literal).
- **[S]** = suposición o inferencia nuestra (no está escrita así en ninguna fuente).
- **[P]** = verificado en ficheros del proyecto (no en la web).

---

## 0. Resumen ejecutivo

1. **TreeFX existe desde CSP 0.1.79** y es un sistema de árboles 3D instanciados con LODs y billboards,
   configurado por `extension/ext_config.ini` (`[TREES] LIST_0 = trees/trees.txt`) y una lista de texto
   `trees.txt` con una línea por árbol. [V]
2. **Formato de `trees.txt`** (una línea = un árbol): `tree: <modelo>.bin; X, Y, Z` o la forma larga
   `tree: tree0.bin; pos=X, Y, Z; angle = 180; size = 1; width = 1; color = r, g, b`. Las líneas
   `configure: <parámetro> = ...` fijan rangos aleatorios (tamaño, anchura, ángulo, color, brillo,
   sombra falsa, semilla) para los árboles que vienen después. [V] Las coordenadas son las del mundo de
   AC (Y arriba): desde Blender, `(x, y, z)_blender -> (x, z, -y)_AC`, la misma conversión que ya usa
   nuestro `kn5_writer_opt.py`. [P]+[S]
3. **El FBX de árbol**: un solo FBX con 1 a 3 LODs (orientación: ~10K / 6K / 3K triángulos), una sola
   malla por LOD (multi-material permitido), pivote en el centro de la base, materiales con difusa
   (alfa = transparencia; el tronco opaco) y normal (alfa = oclusión ambiental local). [V]
4. **La conversión FBX -> .bin solo está documentada en la GUI de Content Manager** (Content > Tools >
   Creator tools > tree converter). No hay CLI ni script oficial; no se ha encontrado ninguna herramienta
   de terceros que escriba el .bin. El .bin es un zip con `tree.ini` + mallas + texturas, editable a
   mano después (pero no documentado para generarlo desde cero). **Conclusión: hay que convertir en el PC
   del amigo (o en cualquier PC con Content Manager), no aquí.** [V]+[S]
5. **Sin CSP no hay árboles TreeFX ni fallback**: es una función propia de CSP; AC "a pelo" no lee
   `extension/`. La única red de seguridad es poner árboles "normales" dentro del KN5 y, con CSP activo,
   ocultarlos con `[SHADER_REPLACEMENT_...] IS_VISIBLE = 0` para que no se dupliquen. [V] (la clave
   IS_VISIBLE) + [S] (la estrategia de dos capas).
6. **Alternativas sin CSP** (todas van dentro del KN5): planos cruzados en X/Y con shader `ksTree`
   (alpha test, `ksAlphaRef = 0.5`, normales hacia arriba) o `ksPerPixelAT` / `ksPerPixelAT_NM`; o
   seguir con mallas low-poly opacas `ksPerPixel` como ahora, pero con mejor silueta y color. `ksGrass`
   hay que evitarlo: CSP lo oculta cuando Grass FX está activo. [V]
7. En el KN5 actual todos los materiales son `ksPerPixel` opacos (`alphaTested = 0`), con 221 líneas
   de materiales `MAT_VEG_*` y `castShadows = 0` en la vegetación. Para un material de árbol con alfa
   nuestro escritor solo tendría que escribir: shader `ksTree` (o `ksPerPixelAT`), `alphaBlendMode = 0`,
   `alphaTested = 1`, `depthMode = 0`, `ksAlphaRef = 0.5` y el sampler `txDiffuse` con una textura PNG
   RGBA. [P]+[V]

---

## 1. Fuentes consultadas

| # | Fuente | URL | Estado |
|---|--------|-----|--------|
| F1 | Wiki oficial CSP "Tracks – Trees" | https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Trees | leída (3 pasadas) |
| F2 | Espejo de F1 (github-wiki-see) | https://github-wiki-see.page/m/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Trees | leída |
| F3 | Docs CSP en cup.acstuff.club (misma página) | https://cup.acstuff.club/docs/csp/tracks/trees | leída |
| F4 | Hilo overtake.gg "Q: Creating TreeFX Tree Models" (2023-2024) | https://overtake.gg/threads/q-creating-treefx-tree-models.263542 | leída |
| F5 | Wiki CSP "General – Shader replacements" | https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements | leída |
| F6 | Wiki CSP "Tracks – General options" | https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-General-options | leída |
| F7 | Wiki CSP "Tracks – Grass FX" | https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Grass-FX | leída |
| F8 | README acc-bakeryoptix (VAO bakery) | https://github.com/ac-custom-shaders-patch/acc-bakeryoptix | leída |
| F9 | Hilo assettocorsamods.net "SHADER setting-up trees" (2014-2017) | https://assettocorsamods.net/goto/post?id=5088 y https://assettocorsamods.net/goto/post?id=5376 | leída |
| F10 | Hilo assettocorsamods.net "Assetto Mods and track creation" (2024) | https://assettocorsamods.net/goto/post?id=22837 | leída |
| F11 | Hilo assettocorsamods.net "What shaders do you use in kseditor" (2017) | https://assettocorsamods.net/threads/what-shaders-do-you-use-in-kseditor-for-different-objects.1016/ | leída |
| F12 | TreePlanter (app Lua para CSP) en overtake.gg | https://overtake.gg/downloads/3d-trees-in-2-minutes-with-treeplanter.59142/updates | leída |
| F13 | Pack "TreeFX for Nordschleife" en overtake.gg | https://overtake.gg/downloads/treefx-for-nordschleife-3d-trees.58778 | leída |
| F14 | Índice de la wiki de CSP | https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki | leída |
| F15 | gtplanet, hilo "AC PC Mods General Discussion" (ksTree) | https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14628506 | **403 al leer**; solo fragmento del buscador |
| P1 | `04_export/kn5_writer_opt.py` (escritor KN5 del proyecto) | local | leído (cabecera y bloque de materiales, líneas 1-45 y 301-339) |
| P2 | `04_export/kn5_check.py`, `kn5_writer.py`, `kn5_writer_b.py` | local | grep (convención de bytes del material) |
| P3 | `04_export/extension/ext_config.ini` | local | leído |
| P4 | `04_export/kn5/resumen_writer_opt.json`, `informe_check_opt.txt` | local | leídos (recuentos) |
| P5 | `03_blender/assets/vegetacion_kit_v2.py` | local | docstring |

Ninguna fuente documenta una CLI del conversor de árboles ni el formato interno de las mallas del
`.bin`. Búsquedas hechas sin resultado útil: "tree converter command line", "treefx bin format reverse",
"convert KSTREE kn5 trees to TreeFX automatically".

---

## 2. TreeFX: qué es y qué versión de CSP hace falta

- [V] F1/F2: "New CSP 0.1.79 feature: a way to add thousands of trees on tracks." y "With LODs,
  billboards for distant trees and heavy use of instancing CSP should be able to handle hundreds of
  thousands of trees."
- [V] F13 (pack real de Nordschleife): requiere "CSP 1.79 or higher" (así lo escribe el autor; es 0.1.79).
  F12 (TreePlanter): "CSP 0.1.79 or greater".
- [V] F4: el conversor de CM está en "creator tools" y, según el hilo, hace falta activar el **developer
  mode** de Content Manager para ver esa sección.
- [S] Cualquier CSP actual (0.1.80 y toda la serie 0.2.x) incluye TreeFX; no se ha encontrado ninguna
  nota de retirada. No hemos podido confirmar la versión concreta que usa el amigo (ni si usa CSP).
- [V] F6: en `[LIGHTING]` existe `ENABLE_TREES_LIGHTING = 0` ("improve performance a lot by disabling
  trees lighting completely") y en `[WIND]` `TREES_NORMALIZATION = 0.8, 1`. [S] Esas claves afectan a
  los árboles ksTree del KN5 (viento/iluminación de árboles "clásicos"), no solo a TreeFX.

---

## 3. Formato exacto de `extension/trees/trees.txt`

### 3.1 Dónde se declara [V] F1

```ini
[TREES]
LIST_0 = trees/trees.txt
```
La ruta es relativa a la carpeta `extension/` de la pista: `content/tracks/<pista>/extension/trees/trees.txt`.
Se pueden declarar varias listas (`LIST_0`, `LIST_1`, ...). [S] (la wiki solo muestra `LIST_0`; el sufijo
numérico sigue la convención de todas las listas de CSP.)

### 3.2 Sintaxis de las líneas [V] F1 (bloques literales de la wiki)

Forma corta (modelo; X, Y, Z):
```
tree: my_tree.bin; 208.4, -1, -53
tree: my_tree.bin; 207.9, -1, -29
tree: my_tree.bin; 207.1, -1, -19
tree: my_tree.bin; 138.5, -1, -12
```
Líneas de configuración (valen para todos los árboles que vienen DESPUÉS en el fichero):
```
configure: size variance = 0.8, 1.2
configure: angle variance = 0, 360
```
Forma larga con parámetros por árbol:
```
tree: tree0.bin; pos=-83.3, -0.99, -74.14; angle = 180; size = 1; width = 1; color = 2, 2, 2
```

### 3.3 Parámetros de `configure:` [V] F1/F2 (texto de la wiki, resumido fielmente)

| Parámetro | Significado según la wiki | Unidad / forma |
|-----------|---------------------------|----------------|
| `size variance = a, b` | "sets range for random size" | multiplicador (p. ej. 0.8, 1.2) |
| `width variance = a, b` | rango aleatorio del multiplicador de anchura | multiplicador |
| `angle variance = a, b` | "sets range for random angles" | grados (ejemplo 0, 360) |
| `color variance = ...` | "sets range for random RGB color shifts" | desplazamiento RGB |
| `brightness variance = ...` | rango aleatorio de brillo | multiplicador |
| `fake shadow = v` | "needs a single value which will be used as fake shadow opacity for all following trees" | 0..1 |
| `seed = n` | "replaces random seed for all subsequent trees with a new single value" | entero |

[V] F2: "all random values are predetermined with a fixed seed even if no explicit seed is set"
(la distribución es reproducible entre cargas).

Por árbol (forma larga) se admiten `pos=`, `angle =`, `size =`, `width =`, `color = r, g, b`. [V]
[S] `size`/`width` son multiplicadores sobre el tamaño nativo del modelo (1 = tal cual el FBX);
`angle` en grados alrededor del eje vertical; `color = 2, 2, 2` es un multiplicador RGB (>1 aclara).
La wiki no dice la unidad explícitamente, pero los ejemplos (`size = 1`, `angle = 180`) solo encajan así.

### 3.4 Unidades y ejes [V]+[P]+[S]

- [V] F1: las posiciones del ejemplo son `208.4, -1, -53`: tres números, el del medio ~ -1 (altura
  justo bajo el suelo) -> el orden es **X, Y(arriba), Z** del mundo de AC, en metros.
- [P] `04_export/kn5_writer_opt.py` (cabecera) y `kn5_writer.py` línea 11: "ejes (x, y, z)_blender ->
  (x, z, -y)_kn5 (Y arriba, Z = -Y de Blender)". `empaquetar.py` línea 5: "Coordenadas AC: x = x_blender,
  y = z_blender (arriba), z = -y_blender". Es la MISMA conversión que hay que aplicar a `trees.txt`:
  `pos = x_b, z_b, -y_b`.
- [S] Rotación: `angle` de AC es giro alrededor de Y(arriba). Con el cambio de ejes, el giro de Blender
  alrededor de Z (`rot_z`, antihorario visto desde arriba en Blender) pasa a girar alrededor de Y de AC,
  pero el sistema de AC es "mano izquierda" respecto al de Blender (Z = -Y), así que el signo puede
  invertirse: `angle = -degrees(rot_z) (+ offset)`. **Validar con los 3 árboles de prueba** (PLAN_USUARIO
  §4 lo pide): poner un árbol asimétrico con `angle = 0/90/180` y comparar con Blender.
- [V] F1 "Surface alignment": con `SURFACE_MATERIALS = tarmac, Concrete2Mat` CSP "snaps trees to
  underlying surface and aligns lighting" -> con esto la Y escrita puede ser aproximada (la wiki usa -1).
  [S] Conviene listar los materiales del TERRENO (`MAT_terreno`, roca, hierba) en `SURFACE_MATERIALS`,
  nunca el asfalto, y aun así escribir la z real del terreno de Blender para que la lista valga también
  sin alineación.

### 3.5 Estaciones y listas compiladas [V] F1 (relevante solo si se quiere ir más lejos)

- Estaciones: `[TREES] SEASON_AUTUMN_0 = SEASON_AUTUMN` / `SEASON_WINTER_0 = SEASON_WINTER` enlazan la
  lista 0 con condiciones `[CONDITION_...] INPUT = YEAR_PROGRESS`. También `SEASON_AUTUMN_1 = tree_pine?,
  tree_big_pine.bin, 0` (filtro por modelo). Por defecto los árboles NO pierden hojas en invierno; para
  eso hay que añadir `[BASIC] LEAFLESS_WINTER=1` al `tree.ini` dentro del `.bin`.
- Compilación: la VAO bakery (acc-bakeryoptix v17+) genera `compiled_trees.bin` ("faster loading and
  ambient shadows from trees"); se referencia con `[TREES] COMPILED_LIST = compiled_trees.bin` y
  **sustituye** a `LIST_...` en ejecución normal. La alineación con el suelo queda cacheada: hay que
  recompilar si cambia el terreno. [V] F1. Requiere la pista en el AC root y CSP 0.1.79 instalado
  (es decir, PC del amigo). [V] F1 + [S].
- Para Porto Corsa: no compilar en la primera iteración; `LIST_0` basta. [S]

---

## 4. Requisitos del FBX de árbol (modelo fuente)

### 4.1 Lo que exige la wiki [V] F1/F2/F3

- Triángulos (sugerencia, no límite duro): "10K triangles for LOD A, 6K triangles for LOD B, 3K
  triangles for LOD C". "don't have to be three LODs either, could be fewer if needed".
- "Single mesh per LOD" (multi-material permitido: tronco + hojas en la misma malla).
- "Pivot of each model should be right at the middle of its base (think of it as a tree positioning
  point on a surface)".
- "Materials should contain both diffuse (albedo) and normal texture (use bump texture in 3DS Max)".
- "Alpha of normal textures can be used for local ambient occlusion; Alpha of diffuse textures is used
  for transparency: make sure trunk texture is opaque".
- Flujo: "Once you got a few LOD models fitting requirements (...) combine them in a single scene and
  export as FBX", luego CM.

### 4.2 Lo que aporta la práctica (hilo overtake F4) [V]

- Mino Cal (16/09/2023): por material hace falta "diffuse texture file (the base texture with
  alpha-channel for transparency) and a normal texture file", en .dds. Los materiales van "combined
  into one multi/sub-object material". Importar todos los LOD "into one file in Blender/3dsmax, make
  sure the pivot point is at the same spot for all" y exportar juntos. **El conversor identifica los
  LOD por número de polígonos** (no por nombre).
- Bouzinc (05/2024, Blender): los LOD separados en varias mallas hacen fallar la conversión; hay que
  tener las partes unidas (una malla por LOD). El modificador Decimate en modo planar le dio problemas.
- srahmoune (01/2024): error "Index was outside the bounds of the array"; MoriSan: todas las partes
  "linked (only one mesh)".
- El `.bin` "is essentially a .zip file that contains textures, meshes, and a tree.ini". Se puede abrir
  el `.bin` y "change settings in the .ini file or textures/meshes without needing to generate a new
  .bin" (no tenerlo abierto mientras AC corre). Al copiar un `tree.ini` a otro árbol, los nombres de las
  mallas LOD tienen que seguir siendo correctos "otherwise it won't show anything".
- `tree.ini` lleva parámetros de sombreado ("coniferous trees would definitely need less
  subscattering and reflectivity"), dimensiones base y distancias de cambio de LOD ("set quite near"
  por defecto; subirlas suaviza el salto a costa de rendimiento).

### 4.3 Suposiciones para nuestro flujo desde Blender 5.1 [S]

- Exportar FBX con escala 1 unidad = 1 m, `-Z forward / Y up` (ajuste estándar de Blender para FBX),
  normales y tangentes incluidas, sin armaduras ni animación: comprobar en CM que el árbol mide lo que
  mide en Blender (un pino de 12 m debe salir de 12 m con `size = 1`).
- Texturas: la wiki habla de .dds en 3DS Max y el hilo usa .dds; no está escrito que el conversor
  acepte PNG. **Suposición prudente: entregar DDS (DXT5 para difusa con alfa, DXT5/BC5 para la
  normal)**; si CM acepta PNG, mejor para nosotros (se comprobará en el PC del amigo). Blender no
  escribe DDS; habría que usar texconv/NVTT/GIMP en el PC del amigo o pedir permiso para instalar una
  herramienta aquí.
- Nombres de LOD: como el conversor ordena por polígonos, llamar a las mallas `LOD_A/B/C` solo sirve
  para nosotros; lo que importa es A > B > C en triángulos y que las tres compartan pivote (0,0,0).
- Estilo Cars: los modelos pueden ser los low-poly del `vegetacion_kit_v2` (<= 1200 tris) con una
  textura difusa pintada (no fotorealista) y una normal casi plana; TreeFX no obliga a hojas en tarjetas
  con alfa, pero sus billboards lejanos se generan a partir del modelo, así que la silueta debe leerse
  bien de lejos.

---

## 5. Conversión FBX -> .bin: ¿se puede hacer sin la GUI de Content Manager?

### 5.1 Hechos [V]

- F1/F3: "use AC Content Manager (https://acstuff.ru/app/#get) to quickly convert that FBX to
  ready-to-use tree model": "Content/Tools/Creator tools" > tree converter; se elige el FBX y el .bin de
  salida ("content/tracks/<yourtrack>/extension/trees"); "Tool should also track changes in FBX file
  while running" (vigila el FBX y regenera).
- F4: hace falta developer mode en CM (opción de los ajustes de CM).
- Ninguna de las fuentes (wiki, cup.acstuff, overtake, búsquedas específicas) menciona una línea de
  comandos del conversor, un script, ni una herramienta de terceros que escriba `.bin`. TreePlanter
  (F12) es una app Lua in-game que SOLO genera `trees.txt` a partir de `.bin` ya existentes ("I am not
  a 3D modeler and will not create trees", FastFred).
- La VAO bakery (F8) es una herramienta aparte (GPU RTX/RX6000/Arc o CPU Embree) que compila listas y
  hornea AO, pero no convierte FBX.

### 5.2 Conclusión y suposiciones [S]

- **No hay forma documentada de generar el .bin sin Content Manager.** El contenido del .bin es un zip
  con `tree.ini` + mallas + texturas, pero el formato binario de esas mallas no está documentado; intentar
  escribirlo a mano desde nuestro Python sería ingeniería inversa sin referencia (riesgo alto, fuera de
  alcance).
- Content Manager es una aplicación Windows (.NET) que necesita una instalación de AC para funcionar con
  normalidad. Como aquí no hay AC, **la conversión se hace en el PC del amigo** (o en cualquier PC con
  AC + CM + developer mode). Lo que sí preparamos aquí: los FBX (uno por especie), las texturas, el
  `trees.txt` generado desde Blender y el `ext_config.ini` con la sección `[TREES]`.
- Flujo propuesto para el amigo (10 minutos por especie): abrir CM > Settings > activar developer mode
  > Content > Tools > Creator tools > Tree converter > elegir `pino.fbx` > salida
  `content/tracks/porto_corsa/extension/trees/pino.bin` > repetir. Luego copiar los `.bin` de vuelta al
  repo (son ficheros nuestros, sin logotipos) para incluirlos en el zip.
- Alternativa sin pasar por CM: usar `.bin` ya hechos por terceros (packs de TreeFX). Tienen licencia y
  estilo fotorealista ajenos al look Cars y habría que descargarlos (necesita permiso): **no
  recomendado** salvo para la prueba de 3 árboles.

---

## 6. ¿Qué pasa si el jugador NO tiene CSP?

- [V] TreeFX es "New CSP 0.1.79 feature" (F1): el motor original de AC no tiene ese código. La
  configuración vive en `extension/ext_config.ini`, que es el fichero de configuración de CSP (F6, F1).
  [P] Nuestro `ext_config.ini` ya lo deja escrito: "Solo lo lee Custom Shaders Patch (CSP): sin CSP, AC
  ignora la carpeta extension/ y nada cambia".
- Consecuencia [V]+[S]: **sin CSP los árboles TreeFX no aparecen y no hay fallback automático**: la
  pista se vería sin ellos. No hay ninguna opción tipo "bake TreeFX into KN5".
- [V] F13: el pack de Nordschleife mantiene los árboles originales del KN5 y añade los TreeFX encima
  ("every bit of vegetation helps with the immersion"), quitando después solo los 2D cercanos a la pista.
  Es la práctica real de la comunidad: TreeFX como capa extra, no como sustituto.
- Mecanismo para que no se dupliquen cuando SÍ hay CSP [V] F5: `[SHADER_REPLACEMENT_...]` admite
  `MATERIALS = ...` / `MESHES = ...` con comodín `?` (ejemplos de la wiki: `MATERIALS = tree?,
  texture:grass?.dds`, `MESHES = mesh_bush_?`) y `IS_VISIBLE = 1` ("sets mesh visibility, set to 0 to
  hide mesh"). También `SHADER = ksTree_ppshadows`, `BLEND_MODE = ALPHA_BLEND`, `DEPTH_MODE =
  NORMAL_FORCED`. [S] Para Porto Corsa: `MATERIALS = MAT_VEG_?` + `IS_VISIBLE = 0` oculta las copas y
  troncos del KN5 solo con CSP activo (nuestro writer fusiona la vegetación en mallas
  `DECO_MAT_VEG_<clave>_pN`, P1 líneas 14-17 y P4; la wiki aconseja MATERIALS frente a MESHES).
- Grass FX, relacionado [V] F7/F10: `[GRASS_FX] GRASS_MATERIALS = ...` limita la hierba a materiales
  concretos (lo que pide el plan: "Grass FX solo en céspedes"); `ORIGINAL_GRASS_MATERIALS` oculta la
  hierba 3D original; y "CSP hides everything with KsGrass shader" (Fuzo, 06/06/2024) -> **no usar
  `ksGrass` para arbustos ni setos** si queremos que se vean con CSP.

---

## 7. Alternativas SIN CSP para árboles decentes en AC (dentro del KN5)

### 7.1 Opciones y lo que dicen las fuentes

| Opción | Shader | Qué es | Fuente |
|--------|--------|--------|--------|
| A. Planos cruzados (X o Y) con alfa test | `ksTree` | el shader de árbol de Kunos; "apply this one only for X or Y shaped tree models with normals pointing up and maybe bushes as well" (Fuzo, F10, 06/06/2024); "For trees you use ksTree" (Johnr777, F11, 17/08/2017) | [V] |
| B. Planos cruzados con alfa test "normal" | `ksPerPixelAT` / `ksPerPixelAT_NM` | "you can also do it using ksPerPixelAT (or ksPerPixelAT_NM if you have a normal map)" (luchian, F9, 04/11/2014) | [V] |
| C. Mallas low-poly opacas (lo actual) | `ksPerPixel` | "the simplest shader (...) primarily for off track objects if you dont have normal maps" (Fuzo, F10) | [V] |
| D. Billboard único que mira a la cámara | — | AC no tiene billboard automático documentado para árboles: los "árboles 2D" de Kunos son planos cruzados fijos; el billboard real solo lo hace TreeFX (CSP) | [S] |
| E. Hierba/arbustos con `ksGrass` | `ksGrass` | descartado: CSP lo oculta con Grass FX (F10) | [V] |

Detalles de la opción A, material ksTree de referencia (LilSKi, NJMP, F9, 11/07/2017) [V]:
`ksAmbient 0.4`, `ksDiffuse 0.25`, `ksSpecular 0`, `ksSpecularEXP 1`, `ksEmissive 0`,
`ksAlphaRef 0.5`, `ALPHATEST=1`, `ALPHABLEND=0`, `DEPTHMODE=0`, una sola textura `txDiffuse` con canal
alfa. Pixelchaser: el ambiente/difuso "generally you balance that with your complete main scenery (...)
hovering around 0.2 to 0.3". Luchian: "the pivot point of the single tree must be in the center of the
geometry (or slightly moved on Z axis)" y naming `KSTREE_GROUP_<nombre>_<n>`; LilSKi: "origin of the
object MUST be at the bottom" y "The KSTREE naming scheme does that for you with the groups" (ksEditor
pone las normales verticales a los objetos así llamados); sombras de los tree-walls: "it is best to
turn off shadows on them as they are not needed".

Comportamiento del shader ksTree (fragmento del buscador sobre F15, NO verificado en la página porque
devolvió 403): "a shadow gradient (subtracting brightness) starting at the bottom of the tree's
geometry, extending up to the horizontal cut-line", que lo distingue de los shaders solo-alfa. [S]

### 7.2 Cómo se escribe en nuestro KN5 (kn5_writer_opt.py) [P]+[V]

Hoy (P1, líneas 322-338) TODOS los materiales se escriben así: `shader = 'ksPerPixel'`,
`alphaBlendMode = 1 si alpha < 0.999 si no 0`, `alphaTested = 0`, `depthMode = 0`, propiedades
(ksAmbient, ksDiffuse, ksSpecular, ksSpecularEXP 24, ksEmissive, ksAlphaRef 0.0) y UN sampler
`txDiffuse` (slot 0) con una textura PNG embebida (`png_bytes`, línea 143). Es decir: en el KN5 actual
no hay ningún material con alpha test ni ningún `ksTree` (en `informe_check_opt.txt` no aparece
`alphaTested=1`), y la vegetación son 221 materiales `MAT_VEG_*` opacos con `castShadows = 0`.

Para un material de árbol de planos cruzados haría falta (bytes según `kn5_check.py` líneas 19-20 y
`kn5_writer_b.py` líneas 55-57, que citan AcTools `Kn5Writer.cs`/`Kn5MaterialBlendMode.cs`):

```
string  nombre            MAT_VEG_pino_copa_at
string  shader            ksTree            (o ksPerPixelAT; ksPerPixelAT_NM si lleva txNormal)
uint8   alphaBlendMode    0                 (Opaque; NO alpha blend: el test se hace con alphaTested)
uint8   alphaTested       1
int32   depthMode         0                 (DepthNormal)
props   ksAmbient 0.4, ksDiffuse 0.25-0.3, ksSpecular 0, ksSpecularEXP 1, ksEmissive 0, ksAlphaRef 0.5
sampler txDiffuse -> PNG RGBA (alfa = recorte de la hoja)   [+ txNormal si _NM]
```
[S] sobre esto: (a) que AC acepte PNG con alfa dentro del KN5 (ya acepta nuestros PNG RGB: el zip v1.0
se ha probado en el PC del amigo, según `color_ac.py`); (b) que `ksTree` no exija más propiedades que
las seis listadas (es lo que exporta ksEditor en el fbx.ini de LilSKi); (c) las normales: como no
pasamos por ksEditor, el writer debe escribir él mismo normales (0, 1, 0) en AC (= +Z Blender) para
todos los vértices de la copa (así se ilumina plana, sin "cara oscura" al girar los planos). Con
`ksPerPixelAT` conviene lo mismo o normales esféricas; (d) `castShadows`: los planos con alfa test SÍ
proyectan sombra recortada en AC si `castShadows = 1`; hoy la vegetación va a 0 (P1 línea 33): habría
que decidir por especie (los pinos grandes con sombra se leen mejor desde el coche); (e) el prefijo
`KSTREE_GROUP_` solo importa en ksEditor (normales automáticas), no en el motor: no hace falta
renombrar nuestras mallas `DECO_`, pero tampoco perjudica.

### 7.3 Qué opción encaja con el look Pixar/Cars [S]

- Los árboles de Cars 2 son volúmenes suaves y saturados, no fotografías recortadas. Los planos
  cruzados con textura fotográfica (opción A clásica) romperían el estilo. Lo coherente es:
  **mantener mallas 3D low-poly (opción C) pero con copas de volumen más rico** (más lóbulos, bisel,
  AO horneada en vértices, variación de tono por instancia) y, SOLO para masas lejanas y laderas,
  planos cruzados `ksTree` cuya textura sea un render de nuestros propios modelos (misma paleta,
  silueta "nube"), 4-8 variantes en un atlas 2048 con alfa.
- Para la capa CSP (TreeFX) el mismo modelo low-poly sirve como LOD A (<= 1200 tris, muy por debajo
  del límite), con LOD B/C decimados; la textura difusa es plana por material (colores del kit) y la
  normal, neutra. La variación de color de TreeFX (`color variance`, `brightness variance`) sustituye a
  las variantes por seed que hoy hace el kit.

---

## 8. Plan de dos capas propuesto para Porto Corsa (resumen operativo) [S]

Capa 1 (siempre, dentro del KN5; lo "esencial" del coordinador):
1. Sustituir las copas-piruleta por copas en masas (ver captura `51_piloto_s1700.png`: hoy el pino
   parasol, el ciprés y los olivos son volúmenes aislados, limpios y planos). Densidad por máscara
   (pendiente, altura, cercanía al mar/pueblo) como pide el plan, pero instanciando mallas en el KN5
   (nuestro writer ya fusiona por material: el coste es de triángulos, no de draw calls).
2. Opcional: masas lejanas con planos cruzados `ksTree` + alfa test (7.2) para subir la densidad en
   laderas sin disparar los triángulos (hoy 5,26 M en el KN5, P4).
3. Presupuesto: sin AC aquí no se mide FPS; limitar a +1,5 M triángulos de vegetación y comprobar con
   `kn5_check.py`.

Capa 2 (extra, solo con CSP, no rompe nada sin él):
4. `03_blender/exportar_trees_txt.py` (python del sistema o bpy): lee `geometria_3d.json` + terreno,
   genera `extension/trees/trees.txt` con bloques `configure:` por zona (p. ej. pinar: `size variance
   = 0.85, 1.25`, `angle variance = 0, 360`, `color variance` suave, `brightness variance = 0.9, 1.1`)
   y líneas `tree: pino.bin; x_b, z_b, -y_b` (conversión de ejes 3.4), agrupadas en masas (Poisson en
   clústeres, no uniforme). Primero 3 árboles de prueba a coordenadas conocidas (meta, cima de tierra,
   casino) para validar ejes y escala en el PC del amigo.
5. `ext_config.ini`: `[TREES] LIST_0 = trees/trees.txt` + `SURFACE_MATERIALS = <materiales del
   terreno>`; `[SHADER_REPLACEMENT_...] MATERIALS = MAT_VEG_? ; IS_VISIBLE = 0` (oculta los árboles
   KN5 solo con CSP) y, para Grass FX, `GRASS_MATERIALS` restringido a los materiales de césped.
6. FBX por especie (pino piñonero, ciprés, palmera, olivo, encina, arbusto con flor) con 2-3 LOD,
   pivote en la base, difusa+alfa y normal; conversión a `.bin` en el PC del amigo con CM (5.2).
7. Comprobar en el PC del amigo: aparecen los 3 árboles de prueba, tamaño y giro correctos, los KN5
   desaparecen con CSP, FPS con 12 coches; después, escalar a la lista completa.

---

## 9. Lista de comprobaciones pendientes en el PC del amigo (no se pueden hacer aquí)

- Versión de CSP instalada (>= 0.1.79; cualquier 0.2.x vale) y si tiene Content Manager con developer
  mode.
- Que el tree converter acepte el FBX exportado por Blender 5.1 (una malla por LOD, pivote común) y
  texturas PNG; si no, convertir a DDS allí.
- Signo del `angle` respecto a `rot_z` de Blender (3.4) y que `size = 1` conserve la altura en metros.
- Que `IS_VISIBLE = 0` sobre `MATERIALS = MAT_VEG_?` oculte las mallas fusionadas `DECO_MAT_VEG_*`.
- FPS con el preset completo; si cae, reducir la lista (el pack de Nordschleife ofrece presets de 17000
  a 1250 árboles por ese motivo, F13).

## 10. Suposiciones (lista cerrada, para que el coordinador las vea de un vistazo)

S1. `size`/`width` son multiplicadores sobre el tamaño nativo del FBX; `angle` en grados sobre el eje
    vertical; `color` es un multiplicador RGB. (La wiki no da unidades.)
S2. Conversión de ejes para `trees.txt` = la del KN5 (`x, z, -y`); el signo del ángulo se valida con
    los 3 árboles de prueba.
S3. Todas las versiones de CSP posteriores a 0.1.79 conservan TreeFX.
S4. El conversor de CM acepta PNG; si no, DDS DXT5. No está documentado.
S5. No existe CLI ni herramienta de terceros para generar `.bin`; el formato interno de malla del
    `.bin` no está documentado -> no se intenta escribir desde Python.
S6. Sin CSP: ni árboles TreeFX ni fallback -> capa KN5 obligatoria si queremos árboles para todos.
S7. `ksTree` con las seis propiedades de LilSKi y normales (0,1,0) escritas por nuestro writer
    funciona sin pasar por ksEditor; `ksPerPixelAT(_NM)` como alternativa más predecible.
S8. AC acepta PNG RGBA embebido en el KN5 para alfa test (hoy solo hemos probado PNG RGB).
S9. El fragmento sobre el degradado de sombra de `ksTree` (F15) no se ha podido leer en su fuente.
