# Entender MATERIALES, TEXTURAS y EXPORT (fase visual) — lectura tecnica, 04/10/2026

Lector: bloque "materiales, texturas y export" del plan del usuario (`_rev/fase_visual/PLAN_USUARIO.md`,
apartado 3 "Paleta, texturas y luz" y parte del 2 "Roca integrada"). No se ha modificado ningun fichero del
proyecto ni se ha lanzado Blender: todo sale de leer el codigo, los JSON y las capturas. Lineas = las del
fichero en disco a las 14:10 del 04/10 (git status: `04_export/kn5_writer_opt.py` y `exportar_ac.py` estan
modificados sin commit; `color_ac.py` y `_color_ac_prueba/` sin seguimiento).

## 0. Resumen en 12 lineas

1. En Blender los materiales son 110 nombres `MAT_*` repartidos por `construir_pista.py` y los 87 ficheros
   .py de `03_blender/assets/` (solo 40 fijan `diffuse_color`), casi todos **procedurales** (rampas,
   ruidos, atributos, Mix Shader) y **sin UVs**.
2. `mejorar_materiales.py` (patina/bump) y `aplicar_texturas.py` (7 tiles PIL de `texturas/`) enriquecen
   el .blend; marcan los arboles con nodos `MEJORADO` / `TEXTURIZADO` (idempotentes).
3. El writer (`04_export/kn5_writer_opt.py::analizar_material`, l.215-258) de cada material entiende SOLO:
   `diffuse_color` (color de viewport) o Base Color sin enlazar, Alpha, la PRIMERA Image Texture sRGB
   enlazada, y los nodos `TEX_ganancia` / `TEX_multiplicar` / `TEX_mapping`. Todo lo demas (rampas por
   altura, mascara de roca, ruidos, bump, Mix Shader, Attribute) **se ignora**.
4. Cada material sale como `ksPerPixel` con 1 sampler `txDiffuse`: PNG plano 8x8 del color, o PNG 512x512
   = tile "tintado" (patron de la imagen x color del material). Shader y `SHADER_PROPS` (l.83-84) son
   constantes para los 441 materiales del KN5.
5. `color_ac.py` (v2) corrige el color y los ks* por familia para que AC se parezca al render de Blender;
   el parche al writer esta hecho y probado pero **a las 14:10 aun no esta aplicado** en
   `kn5_writer_opt.py` (ningun `import color_ac`; vive en `_color_ac_prueba/kn5_writer_opt.diff`).
6. El terreno (`MAT_terreno`, 266 255 vertices, 1 material) llega a AC como **un unico tile de hierba
   verde** en todo el macizo: la roca por pendiente/mascara solo existe en Blender. `color_ac.separar_roca_terreno`
   (l.476-509) resolveria la roca con un 2o material, pero **nadie lo llama**.
7. Lo que pide el usuario (paleta oliva/salvia/seca/caliza/terracota, `ksMultilayer_fresnel_nm4`, CC0, AO,
   bisel) exige cambios en: paleta unica, `generar_texturas.py`, `aplicar_texturas.py`, `construir_pista.py`,
   `color_ac.py` (re-medir) y, sobre todo, en el writer (shader/props/samplers por material + UV real +
   texturas sin tintar y > 1024) y en `kn5_check.py` (que hoy no valida nada de materiales).

## 1. Mapa del pipeline de materiales (donde nace cada cosa)

Orden real (RONDA15_PLAN.md l.24-26): `construir_pista.py` -> `integrar_escena.py` (+assets) ->
`mejorar_materiales.py` -> `aplicar_texturas.py` -> `renderizar_*.py` -> `04_export/exportar_ac.py` ->
`kn5_writer_opt.py` (+`color_ac.py`) -> `kn5_check.py` -> `empaquetar.py`.

### 1.1 `03_blender/construir_pista.py` (materiales base de pista, terreno y mar)

| Que | Donde | Detalle |
|---|---|---|
| `mat(name, rgba, rough, metal, emit)` | l.42-56 | Principled plano; **fija `diffuse_color = rgba`** (lo que leera el writer). |
| `mat_con_ruido(...)` | l.58-82 | dos tonos por Noise + Bump; `diffuse_color = c1`. `MAT_asfalto` (0.105,0.102,0.108) l.84, `MAT_tierra` (0.60,0.43,0.24) l.86. |
| `mat_terreno()` | l.92-183 | **rampa por altura** (Map Range z -4..170 -> ColorRamp: fondo marino, arena 0.023, hierba baja 0.042 (0.22,0.40,0.13), monte 0.50 (0.20,0.33,0.12), cumbres 0.97 (0.30,0.33,0.20)), parches de pradera (Noise 0.005 x rampa 0.78..1.15) l.119-134, **mascara de roca** = max(talud por N.z, atributo `roca`) l.136-177, `mixr.inputs[7]` = color roca (0.25,0.23,0.19) l.179, `diffuse_color = (0.32,0.45,0.2)` l.181. |
| `_roca_terreno(...)` | l.185-345 | talud smoothstep N.z 0.50-0.56 + ruido +-0.04 (l.203-235); atributo smoothstep 0.47-0.51 + ruido +-0.33 (l.205, 236-240); `ROCA_llano_hierba` anula roca si N.z > 0.78-0.86 (l.241-251); caliza = `ROCA_rampa` (0.30,0.235,0.15)->(0.46,0.37,0.245) l.259-264 x estratos (Wave BANDS eje Z, 2.6 m, l.266-284) x grano x meteorizacion; **BSDF propio `ROCA_bsdf` + `ROCA_mezcla` (Mix Shader)** l.333-345. `Math.002` = mascara que leen revisores y `aplicar_texturas`. |
| atributo `roca` | l.1469-1474 | `terreno.data.attributes.new('roca','FLOAT','POINT')` desde `geometria_3d.json['mascara_roca']` (terreno_montana.py l.2243-2298; hoy media 0.029, 2.6 % de vertices > 0.5). |
| `MAT_agua` | l.349, 1486-1513 | Alpha 0.84, BLEND, dos azules por Noise 0.004, bump de olas. |
| `MAT_arcen` | l.1169 | (0.21,0.37,0.125) verde cesped; `MAT_muro_contencion_piedra` l.1285/1516. |
| luz/mundo | l.1566-1618 | sol 4.6 (1,.96,.88) a 34 grados, cielo azul saturado, vista Standard exp 0.12, GTAO 12 m. |

### 1.2 Kits de `03_blender/assets/` (paletas propias, cada una a su aire)

- `roca_lazo.py::_PALETA` l.150-175: roca (0.46,0.39,0.28), clara (0.62,0.55,0.42), oscura (0.29,0.24,0.17),
  repisa, piedras, matas... Nombres `MAT_PPUEBLO_*` (l.132-134): familia `roca` en aplicar_texturas.
- `roca_casino.py` l.99-116: `MAT_PPUEBLO_roca` (0.55,0.47,0.36) / clara / oscura (**distintos** de roca_lazo
  para el mismo nombre: gana el que se cree primero, `bpy.data.materials.get`).
- `penon_cara.py` l.303-305 y `penon_topolino.py` l.277-279: `MAT_PENON_caliza` (0.52,0.40,0.24) +clara/oscura.
- `montanas_fondo_v2.py` l.245-247: `MAT_MONT_roca` (0.48,0.38,0.25) +clara/oscura.
- `montana_mclaren.py` l.143-149, 255-267: `MAT_MCOCHE_caliza` (indices fijos 0-8), `_caliza_grieta`,
  `_caliza_monte`, `_hierba` (0.165,0.30,0.085), `_cristal_pulido`.
- `casas_kit_v2.py::PALETA_FACHADA` l.87 y `_get_mat` l.172-183: `MAT_CASAS_fachada_<color>`, `_teja`,
  `_piedra`, `_madera`, `_vidrio`, `_persiana`, `_forja`, `_metal`, `_cromo`, `_terraza`, `_toldo_*`.
- Prefijos contados en 03_blender (`grep MAT_`): PPUEBLO 26, PIT 20, PENON 15, terreno 13, CAMINO 13,
  zocalo 9, MIRADOR 9, MONT 7, piedra 6, CARRERA 6, CASAS 5, CIVICO 4, CASINO 3, ... (110 nombres).
- 47 de 87 ficheros de assets NO fijan `diffuse_color`; si ademas enlazan Base Color, el writer exporta el
  gris 0.8 por defecto de Blender (de ahi el JSON de albedos de color_ac, ver 2.3).

### 1.3 `03_blender/mejorar_materiales.py` (patina, roughness, bump; 289 lineas)

- Objetivo: `PREFIJOS` l.24-25 (CASAS, CASINO, PUENTES, EDIF, HOTEL, AYTO, CAMPANILE, `MAT_piedra`) menos
  `EXCLUIR` (vidrio, luz, emis, persiana). Idempotente por nodo `MEJORADO` (l.67, 79-82).
- `mejorar_material()` l.61-201: (c) Noise 3-6.5 -> ColorRamp (0.48,0.43,0.38)->blanco -> Mix MULTIPLY
  factor 0.12-0.18 **delante del Base Color** (l.89-117; si habia enlace previo lo encadena); roughness
  +-0.1 por Noise + Map Range (l.119-139); (d) tejas: Wave BANDS Y, Bump 0.3/0.025 (l.149-168);
  (e) piedra: Brick girado 90 grados en X, Bump 0.25/0.03 invertido (l.170-198).
- `pintura_coches()` l.214-260: metallic/coat en `MAT_COCHE_*`, `MAT_CAMARA_*`, `MAT_PIT_coche*`; activa
  raytracing de EEVEE. Nada de esto llega al KN5 (ksPerPixel no tiene coat ni roughness): solo influye en
  el render de Blender y, via `color_ac`, en el "aspecto medido".

### 1.4 `03_blender/aplicar_texturas.py` (tiles PIL por familia; 446 lineas)

- `FAMILIAS` l.44-65: asfalto (8 m, FLAT, bump), tierra (6 m), teja (2 m, BOX, bump), piedra (3 m, BOX,
  bump), piedra_suave (viaducto), estuco (4 m, BOX), hierba (7 m, FLAT), bosque (BOX), agua (40 m, solo
  bump). `ganancia` = 1/media lineal medida de cada PNG (2.19 asfalto, 1.85 hierba...).
- `familia_de()` l.73-101: por nombre. **`roca`** = `mat_mont_roca`, `mat_penon_caliza/meseta`,
  `mat_ppueblo_roca/repisa`, `mat_mrueda_caliza` -> `aplicar_roca()` l.359-398: **procedural, sin imagen**
  (Noise 0.045 -> rampa gris->crema, multiply 0.9/1.15, bump de grano 0.35). Por eso en AC las rocas de los
  penones salen con color plano (el writer no ve ninguna Image Texture): "tambor liso" de las capturas 19/20/45.
- `crear_cadena_textura()` l.148-172: TexCoord **Object** -> Mapping(1/tile) -> Image (REPEAT, Linear,
  FLAT o BOX blend 0.3). Sin UVs en ninguna malla (docstring l.9).
- `multiplicar_base_color()` l.175-200: `TEX_ganancia` (Mix x ganancia, sin clamp) -> `TEX_multiplicar`
  (MULTIPLY, factor) -> Base Color. **Estos dos nombres de nodo son el contrato con el writer.**
- `aplicar_terreno()` l.247-342: hierba_d multiplicada x0.5 sobre la salida de la rampa, SOLO en
  z 0.5-3 -> 150-168 y donde N.z > 0.60-0.78 (`TEX_llano`). Como `_roca_terreno` ya separa la roca en otro
  BSDF, la hierba no vela la roca en Blender; pero la **proyeccion FLAT (x,y)** estira la hierba en las caras
  casi verticales que quedan en la rama de hierba (capturas 03, 05, 17, 33, 40, 48, 49: "hierba estirada").
- `aplicar_agua()` l.345-356: `agua_h.png` Non-Color como bump 1.0/0.4 (olas de 40 m).

### 1.5 `03_blender/texturas/generar_texturas.py` (7 tiles 1024, PIL + numpy FFT; 346 lineas)

- Ruido periodico por sintesis espectral (`ruido_espectral` l.26-48, `ruido_banda` l.51-64): tilea sin
  costuras por construccion; `guardar()` l.82-92 escribe el PNG y un `mosaico_3x3_*.png` de control.
- Colores base (valores 0..1 escritos tal cual al PNG; Blender los lee como sRGB): asfalto gris frio 0.46
  (l.102-138); tierra ocre (0.74,0.60,0.43) con 5200 guijarros (l.143-180); teja terracota
  (0.80,0.42,0.28)/(0.72,0.35,0.24) en 8x8 tejas (l.185-230); estuco casi blanco 0.88-1.0 (l.235-247);
  piedra arenisca clara (v, 0.955v, 0.875v), 8 hiladas (l.252-288); **hierba = verde cesped saturado
  (0.28,0.60,0.15)/(0.42,0.65,0.14)** (l.293-310); `agua_h` altura (l.315-334).
- La media de cada PNG es la que compensa `ganancia` en `aplicar_texturas.FAMILIAS`; si se regenera una
  textura hay que re-medir la media y actualizar la ganancia a mano (no es automatico).

### 1.6 `04_export/exportar_ac.py` (escena de export; 160 lineas nuevas sin commit)

- Renombra `TERRENO -> 1GRASS_terreno` (l.71): en el writer deja de ser 'suelto' y pasa a **fusion fisica**
  (`1GRASS_fusion_MAT_terreno_pN`, coordenadas mundo, trozos de <= 65 000 vertices ordenados por Morton).
- Voltea las normales de suelo que miran abajo (`SUELO` l.414-431). No toca materiales ni crea UVs.
- Guarda `04_export/porto_corsa_export.blend` (es lo que abre el writer).

### 1.7 `04_export/kn5_writer_opt.py` (861 lineas; formato KN5 v5)

| Funcion | Lineas | Que hace con los materiales |
|---|---|---|
| `SHADER_PROPS` | 83-84 | ksAmbient 0.45, ksDiffuse 0.55, ksSpecular 0.15, ksSpecularEXP 24, ksEmissive 0, ksAlphaRef 0, para TODOS. |
| `analizar_material(m)` | 215-258 | ver tabla 2.1. |
| `construir_textura(info)` | 261-283 | sin imagen: PNG **8x8** `flat_<mat>.png` del color (sRGB). Con imagen: `imagen_lineal()` (l.185-204) reduce a `TEX_SIZE=512` por media 2x2 y **tinta**: rgb = color * (1 - f + f * lin * gain), con gain = 1/media lineal por canal: la imagen aporta solo el patron y **el tono lo decide `color`** (una textura CC0 pierde su color propio). Alpha < 0.999 -> canal A constante. `limitar_tamano()` l.162-179 recorta a `TEX_MAX=1024`. |
| `recopilar_materiales()` | 286-298 | orden de aparicion + `MAT_default` (el parche color_ac llama aqui a `calibrar_todos`). |
| `escribir_texturas_y_materiales()` | 301-339 | dedup por md5 solo si hay imagen (l.308); material = nombre, shader **ksPerPixel fijo** (l.324), alphaBlendMode 0/1, alphaTested 0, depthMode 0, props (nombre, A float, B vec2, C vec3, D vec4; ksEmissive tambien en C) y **1 sampler txDiffuse, slot 0**. |
| `loops_grupo()` | 387-408 | UV: `uv_layers[0]` si existe; si no y el material tiene imagen, **UV generada** = Object*scale (FLAT: xy; BOX: por eje dominante de la normal de cara); si no, ceros. Luego v = 1 - v. |
| `con_tangentes()` | 448-458 | tangente **ficticia** = normal x (0,1,0): vale para ksPerPixel, NO para normal maps. |
| vertice | 444, 551-562 | 11 floats: pos3 nrm3 uv2 tan3. **El formato no tiene color de vertice** (ni UV2). |
| `categoria()` | 606-619 | ac / invisible / fisica (1ROAD_,1KERB_,1GRASS_,2GRASS_,1WALL_,1DIRT_,1PIT_) / suelto (AC_,PIT_LANE,PISTA,TERRENO,AGUA) / deco. Fusion POR MATERIAL: una "malla por zona" solo sobrevive si tiene material distinto. |
| resumen (`04_export/kn5/resumen_writer_opt.json`, 02/10) | 816-853 | 441 materiales, 438 texturas (12.5 MB), 87 con imagen, 572 mallas, 7.07 M vertices, 5.26 M triangulos, **355 MB**. |

### 1.8 `04_export/color_ac.py` (931 lineas; calibracion para AC) y estado del parche

- Modelo de AC en gamma (l.40-56, 195-214: tx*(ksA*AMB + ksD*SOL*N.L) + especular, curva Yebis + gamma 1.2,
  autoexposicion [0.2, 0.5]) y modelo lineal CSP/LCS (l.83-91, 228-258; dos curvas, ACES y sRGB+Yebis).
- `FAMILIAS` l.277-289: ks por familia (asfalto, pintura_vial, terreno, agua, roca, edificio, pintado,
  metal, cristal, vegetacion, luz), todas 0.60/0.48 salvo cristal, con `techo` de textura por familia.
  `_REGLAS` l.309-331 y `familia()` l.334-342 clasifican **por subcadenas del nombre** (terreno, hierba,
  tierra, terraplen, paja -> terreno; roca, caliza -> roca; piedra, sillar, fachada, estuco, teja -> edificio).
- Objetivo de cada material: `objetivo_medido()` l.387-398 (`color_ac_objetivos.json`: 127 materiales medidos
  en 6 vistas por `_rev/color_ac/medir_objetivos.py`) > `albedo_real()` l.368-379 (`color_ac_albedo.json`:
  177 procedurales, `medir_albedo.py`) > `diffuse_color`. **Guarda +-0.02** (l.376, 396): si el color del
  writer cambia mas de 0.02 la medida se ignora sola. Con una paleta nueva hay que RE-MEDIR (render_ac.py
  ~90 s + medir_objetivos.py + medir_albedo.py) o se cae al modelo albedo x luz.
- `ajustar_texturas()` l.613-689: Levenberg-Marquardt en log(tx) por canal, 4 caras de referencia x modos
  (gamma 0.6, LCS 0.2, LCSY 0.2), techo de croma `CROMA_MAX` 1.08 (l.303), suelo `SUELO_TX` 0.03.
- `separar_roca_terreno()` l.476-509 + `mascara_roca()` l.423-429 (N.z < 0.50, o atributo > 0.49 con
  N.z < 0.82): crea `MAT_terreno_roca` y reasigna caras **sin guardar el .blend**. **No lo llama nadie**:
  `_color_ac_prueba/kn5_writer_opt_color.py` l.305 solo llama a `calibrar_todos`; grep en el repo: solo su
  definicion y un comentario en `simular_vistas.py` l.38. `CAMBIO_KN5_WRITER.md` l.170 lo reconoce:
  "Laderas de roca del terreno. Siguen saliendo verdes".
- `generar_ext_config()` l.872-886: `04_export/extension/ext_config.ini` (ya existe, 13:04) con
  `[Material_Water] Type = SEA` y una palanca `[MATERIAL_ADJUSTMENT_0]` desactivada. Solo lo lee CSP.
- Estado: `04_export/kn5_writer_opt.py` NO importa `color_ac` (grep vacio a las 14:10); el parche probado
  (`_color_ac_prueba/porto_corsa_color.kn5`, 273 MB, kn5_check OK 8/8) se aplica con `git apply` de
  `_color_ac_prueba/kn5_writer_opt.diff` (5 cambios) y `empaquetar.diff`. Lo esta cerrando el equipo del zip
  v1.1: **esta lectura no lo toca**.

### 1.9 `04_export/kn5_check.py` (828 lineas; lector independiente, sin bpy)

- Lee texturas (l.148-165: nombre, tamano, formato por magia, ancho/alto/modo con Pillow), materiales
  (l.168-205: shader, blend, alphaTested, depth, props con A/B/C/D, samplers nombre/slot/textura) y nodos.
- Las 8 comprobaciones (`comprobar()` l.366-571): (1) dummies AC_* con matriz y posiciones plausibles;
  (2) existen mallas 1ROAD_/1KERB_/1GRASS_/1WALL_; (3) indices < n_vertices y materialId en rango;
  (4) ninguna malla > 65 535 vertices; (5) **toda textura referenciada por un sampler existe en la tabla**;
  (6) bbox del circuito fisico; (7) normales de 1ROAD_ hacia +Y; (8) se consumen todos los bytes.
- Lo que NO comprueba (importa para el plan): que el nombre del shader exista en AC, que props y samplers
  sean los de ese shader, formato / tamano / mipmaps de las texturas (solo informa ancho x alto), rango de
  UV (lo informa en `uv_rango` l.296, no decide), tangentes, materiales sin uso, texturas duplicadas.

## 2. Que entiende el writer de un material (y que se pierde)

### 2.1 Tabla nodo -> KN5

| Nodo / dato de Blender | Lo lee el writer | Resultado en el KN5 |
|---|---|---|
| `material.diffuse_color` | si (l.219, base) | color de la textura plana o tinte del tile |
| Principled Base Color **sin enlazar** | si (l.229-231; manda sobre diffuse_color) | idem |
| Principled Base Color **enlazado** (rampa, noise, mix) | NO: se queda `diffuse_color` | color de viewport (0.8 gris si el kit no lo fijo): por eso existe `color_ac_albedo.json` |
| Principled Alpha sin enlazar | si (l.226-228) | alphaBlendMode 1 + canal A constante |
| Primera Image Texture sRGB con Color enlazado | si (l.233-241) | tile 512 tintado; `projection` FLAT/BOX |
| TEX_ganancia.B, TEX_multiplicar.Factor, TEX_mapping.Scale | si (l.242-257) | gain (informativo: el writer recalcula 1/media), factor f, escala UV |
| Image Non-Color (bump), Bump, Normal Map | NO | nada (sin relieve en AC) |
| Roughness, Metallic, Coat, Specular, Emission | NO | ks* fijos (SHADER_PROPS) o por familia (color_ac) |
| Attribute 'roca', Geometry.Normal, Map Range, Mix Shader (ROCA_mezcla) | NO | la mascara de roca no existe en AC |
| Segundo Principled (ROCA_bsdf) | NO (toma el primero, l.224) | la rama de roca se pierde |
| UV map | si existe `uv_layers[0]` (l.367-374) | hoy ninguna malla la tiene: UV generadas por objeto |
| Color attributes / vertex color | NO (el formato no tiene color) | imposible en KN5 |

### 2.2 Como sale el TERRENO hoy en AC

- 1 material `MAT_terreno` con imagen `hierba_d.png` (FLAT, tile 7 m) tintada con `diffuse_color`
  (0.32,0.45,0.20) o, con color_ac, con el aspecto medido de la hierba al sol (128,191,102 en pantalla).
- Todo el macizo, los desmontes, los acantilados y el fondo marino (`AGUA_fondo` usa `M_TER`, construir_pista
  l.1485) llevan el mismo verde: la roca por pendiente, la rampa por altura (arena, monte, cumbres) y los
  parches de pradera **no salen del .blend**. Lo documenta `_rev/color_ac/investigacion.md` seccion 7 (lo
  senala en `comparativa_piloto_s300.png`, `comparativa_pueblo.png` y `comparativa_tierra.png`; ojo: la
  simulacion de `simular_vistas.py` l.38 ya pinta un `MAT_terreno_roca` virtual que el KN5 real no lleva).
- Como `1GRASS_terreno` va a fusion fisica por material, la unica forma de que AC muestre dos cosas en el
  terreno es tener DOS (o N) materiales sobre sus caras, o un shader multicapa con mascara.

### 2.3 Artefactos de las capturas que nacen en los materiales (no en la geometria)

| Defecto (director_final.md) | Origen en el material | Donde |
|---|---|---|
| bandas blancas en dientes de sierra junto al sendero (07, 08) | atributo `roca` por vertice interpolado en triangulos de 4 m y umbral smoothstep de solo 0.04 (0.47-0.51): el borde cae dentro de UNA celda y sigue la diagonal fija a-c | construir_pista l.205-206, 1460-1466 |
| borde hierba/roca en escalera (14, 22) | lo mismo, en la costa (mascara dilatada al mar, terreno_montana l.2281) | idem |
| hierba estirada en caras casi verticales (03, 05, 17, 33, 40, 48, 49) | hierba_d proyectada FLAT (x,y) sobre caras con N.z 0.6-0.78 (`TEX_llano`) que siguen en la rama de hierba | aplicar_texturas l.59-60, 306-324 |
| rayas tipo curva de nivel en laderas (05, 06, 13, 27, 39) | `ROCA_estratos` = Wave BANDS en Z cada 2.6 m con distorsion 6: en una ladera del 30 % cada junta queda a ~9 m horizontales y se lee como isolinea; en caras de 75 grados funciona | construir_pista l.266-284 |
| desmontes como manchas grises lisas con borde difuso (01, 07, 09, 16, 21, 42, 51) | caliza con manchas de 20 m y grano de 2 m pero sin normal/AO; borde = smoothstep + ruido de 2.5 m; en AC ni siquiera existe (todo hierba) | construir_pista l.253-331 |
| cupulas lisas de roca_lazo / tambor del penon (13, 19, 20, 45) | `aplicar_roca()` procedural sin imagen + materiales planos de los kits; en AC color plano 8x8 | aplicar_texturas l.359-398; roca_lazo l.150-175 |
| caliza del McLaren "plastico crema" (02, 32) | MAT_MCOCHE_caliza objetivo medido 202,197,183 (muy claro) y estratos como franjas de pintura | montana_mclaren l.255-267 |
| meseta del casino blanca / cala blanca (20, 36) | MAT_PENON_meseta y losas sin textura (familia roca procedural) | penon_cara l.303-305 |

## 3. Que haria falta para cada punto del plan

### 3.a Paleta nueva (oliva / salvia oscuros, hierba seca dorada, caliza ocre y gris calido, terracota) consistente Blender <-> AC

Hoy la paleta esta repartida en >= 9 sitios que no se leen entre si:

| Donde vive el color hoy | Fichero : lineas | Que pinta |
|---|---|---|
| hierba del tile | `texturas/generar_texturas.py` 306-307 | el patron verde cesped que multiplica a todo el terreno, arcenes y 'bosque' |
| rampa por altura del terreno | `construir_pista.py` 110-114 | arena / hierba baja / monte / cumbres (solo Blender) |
| parches de pradera | `construir_pista.py` 125-126 | multiplicador 0.78..1.15 (solo Blender) |
| roca del terreno | `construir_pista.py` 179, 262-263 | gris caliza (0.25,0.23,0.19) y `ROCA_rampa` |
| color que ve el writer | `construir_pista.py` 181 (`diffuse_color`) | la hierba de AC si no hay medida vigente |
| arcen, tierra, muros, acera, bordillo | `construir_pista.py` 86, 807-808, 1169, 1285 | fisicos y caminos |
| rocas de los kits | roca_lazo 150-175, roca_casino 99-116, penon_cara 303-305, montanas_fondo_v2 245-247, montana_mclaren 255-267 | 4 calizas distintas con el mismo nombre de familia |
| fachadas y tejas | `casas_kit_v2.py` 87 (`PALETA_FACHADA`), 172-183 | tejas (0.80,0.42,0.28) via `teja_d` + COL_TEJA |
| vegetacion | `vegetacion_kit*.py`, `MAT_VEG_*`, `MAT_OLI_*`, `ital_*` | copas verde cesped (ver 51_piloto_s1700) |
| objetivo para AC | `04_export/color_ac_objetivos.json`, `color_ac_albedo.json` | medidas con guarda +-0.02 |
| familias y techos de AC | `color_ac.py` 277-289, 303 | ks* y techo de brillo; `CROMA_MAX 1.08` |

Cambios concretos:

1. **Un unico fichero de paleta** `03_blender/paleta.json` (nombre -> RGB lineal + sRGB de referencia +
   familia AC): `oliva_oscuro`, `salvia`, `hierba_seca`, `caliza_ocre`, `caliza_gris_calido`, `terracota`,
   `cesped_jardin`, `tierra`, `asfalto`. Lo leen `generar_texturas.py` (tintes de los tiles),
   `construir_pista.py` (rampa, roca, arcen, tierra), los kits de roca (sustituir las 4 `_PALETA` por la
   comun, dejando los matices `_clara/_oscura` como +-15 % de luminancia) y `casas_kit_v2` (tejas).
   Regla: **Base Color sin enlazar o `diffuse_color` = la media lineal que se quiere ver**, siempre.
2. **Tiles nuevos**: `hierba_d.png` deja de ser cesped y pasa a dos tiles: `hierba_seca_d.png` (dorado,
   ~(0.55,0.45,0.20)) y `matorral_d.png` (oliva/salvia, manchas de 1-3 m); `cesped_d.png` solo para
   jardines/rotondas (familia nueva `cesped` para `MAT_LOEWS_*`, `MAT_URB_jardin`...). `piedra_d.png` ->
   caliza ocre con juntas calidas; `teja_d.png` mas terracota y menos naranja. Re-medir medias -> `ganancia`.
3. **Terreno en Blender**: la rampa por altura (l.110-114) pasa a leer la paleta (hierba seca abajo,
   matorral en el macizo, caliza en cumbres); `mixr.inputs[7]` y `ROCA_rampa` a caliza ocre/gris calido;
   `diffuse_color` (l.181) = media de la zona dominante (hierba seca junto a la pista) para que AC no se
   quede con el verde.
4. **Consistencia con AC** (sin tocar el shader): color_ac ya reproduce lo medido en Blender, asi que la
   paleta nueva "llega" a AC si (i) se re-renderizan las 6 vistas de ajuste (`_rev/color_ac/render_ac.py`,
   90 s en la cola) y se re-miden objetivos y albedos, y (ii) se revisa `CROMA_MAX` (1.08) y los `techo`:
   los ocres y terracotas saturados de la paleta nueva pueden chocar con el techo de croma y salir
   desaturados. Mientras el equipo del zip tenga el parche sin aplicar, el KN5 saldra con `SHADER_PROPS`
   antiguos y la paleta se vera lavada igual que ahora (ver `informe_color_ac.md` seccion 1).
5. **Vegetacion**: las copas `MAT_VEG_*` (familia vegetacion en color_ac) deben pasar a oliva/salvia
   tambien, si no el contraste copa-verde/suelo-oliva se invierte respecto al plan.

Riesgos: (R1) cambiar `diffuse_color` invalida TODAS las medidas de color_ac de esos materiales a la vez
(guarda +-0.02): hasta re-medir, AC usa albedo x luz, peor. (R2) `familia()` clasifica por nombre: un
`MAT_terreno_hierba_seca` cae en 'terreno' (bien) pero un `MAT_matorral` caeria en 'pintado' (ks y techo de
pintura): hay que anadir subcadenas a `_REGLAS` l.309-331. (R3) las 4 calizas de los kits con el mismo
nombre (`MAT_PPUEBLO_roca`): el primer kit que se construye fija el color; con la paleta comun deja de
importar. Dependencias: paleta.json antes que cualquier kit; generar_texturas antes que aplicar_texturas;
re-medir color_ac despues de renderizar las capturas finales (no antes: miden la escena).

### 3.b Terreno multicapa: `ksMultilayer_fresnel_nm4` (mascara RGBA + 4 detalles) o alternativas

**Que necesita el KN5** (formato leido por kn5_check l.168-205, escrito por el writer l.319-338): por
material, el nombre del shader, la lista de props (nombre + A + B + C + D) y la lista de samplers (nombre,
slot, textura). Para el multicapa de Kunos (familia `ksMultilayer*`, la de las carreteras de Kunos segun
`investigacion.md` seccion 4) haria falta, con el nombre de sampler que conoce el lector de referencia
`kn5_refs/kn5-obj-converter/convert.py` l.52-61 (`txDiffuse`, `txMask`, `txDetailR/G/B/A`, `txDetailNM`):

- samplers: `txDiffuse` (color base, UV de la malla), `txMask` (RGBA, UV de la malla), `txDetailR`,
  `txDetailG`, `txDetailB`, `txDetailA` (tiles de detalle, UV x multR..multA) y los normal maps de detalle
  (en `_nm` uno, `txDetailNM`; en `_nm4` cuatro; **los nombres exactos de los 4 no estan en ninguna referencia
  del repo**: hay que confirmarlos leyendo con `kn5_check.py --quiet` un KN5 de un circuito de Kunos que use
  ese shader, en el PC del amigo, o con la lista de shaders de Content Manager);
- props: `ksAmbient`, `ksDiffuse`, `ksSpecular`, `ksSpecularEXP`, `ksEmissive`, `ksAlphaRef`, `multR`,
  `multG`, `multB`, `multA` (repeticiones del detalle respecto a la UV), `detailNMMult`, `fresnelC`,
  `fresnelEXP`, `fresnelMaxLevel` (mismos avisos: confirmar nombres y valores en un KN5 real).

**Cambios en el pipeline** (orden de dependencia):

1. `construir_pista.py`: crear en TERRENO una **UV real** (`me.uv_layers.new('UVMap')`): u = (x - x0) /
   (nx*cell), v = (y - y0) / (ny*cell), planar; es la UV de `txMask` y `txDiffuse` (0..1 sobre toda la
   rejilla de 2068 x 2060 m) y los detalles se repiten con `multR = 2068 / tile_m` (tile 6 m -> ~345).
   El writer la exporta tal cual (`arrays_malla` l.367-374) y la fusion por material la conserva.
2. **Mascara RGBA** generada en numpy (nuevo `03_blender/mascara_terreno.py`, python del sistema, desde
   `geometria_3d.json`: z, pendiente de la rejilla, `mascara_roca`, distancia al mar, al pueblo y a la
   pista): R matorral (oliva, laderas medias y macizo), G hierba seca (llanos y bordes de pista), B tierra
   (desmontes, pie de taludes, cortes), A roca (pendiente > 35-40 grados o mascara_roca > 0.5), suma = 1 y
   bordes con ruido de 10-30 m (no por celda). Resolucion: 2048 px = 1 px/m (la celda es de 4 m), o 4096.
   **Choca con `TEX_MAX = 1024`** (writer l.64, 162-179): hay que exceptuar `txMask` del recorte (y pesarla:
   PNG RGBA 2048 ~ 4-8 MB, 4096 ~ 16-30 MB dentro de un KN5 que ya mide 355 MB).
3. `kn5_writer_opt.py`: (i) `analizar_material` reconoce un material "multicapa" (por nombre `MAT_terreno`
   o por un custom property `m['ac_shader']`) y recoge sus 5-9 imagenes **sin tintar ni reducir a 512** (nuevo
   modo en `construir_textura`: PNG sRGB tal cual, o DDS con mipmaps, ver 3.c); (ii) `escribir_texturas_y_materiales`
   escribe shader, props y samplers **por material** (hoy constantes, l.324-338); (iii) `color_ac` debe
   tratar al multicapa aparte (`calibrar_todos` tinta `info['color']`; en multicapa el color va en los
   detalles y en `txDiffuse`); (iv) dedup por md5 ya funciona para los detalles compartidos.
4. `kn5_check.py`: nueva comprobacion (9) "shader conocido + samplers esperados por shader + props
   esperadas" con una tabla `SHADERS = {'ksPerPixel': ..., 'ksMultilayer_fresnel_nm4': ...}` y un aviso
   si una textura supera 2048 o no es cuadrada/potencia de 2.
5. Blender: el material de Blender debe PARECERSE a lo que hara AC (la misma mascara como imagen en
   `Attribute`/Image + 4 tiles mezclados por canal), si no las capturas antes/despues no sirven para juzgar.
   Es un `mat_terreno()` nuevo con Image Texture de la mascara (UV) + 4 Image Texture de detalle (UV x mult)
   + Mix por canal; `aplicar_terreno()` de aplicar_texturas se retira para `MAT_terreno`.

**Riesgos**: (R4) nombre de shader/props/samplers mal: AC no carga el material (o el circuito) y aqui no se
puede probar: solo kn5_check extendido + prueba en el PC del amigo con un KN5 pequeno de ensayo (un plano
de 4 triangulos con el shader, ANTES de tocar el circuito). (R5) sin CSP el multicapa funciona (es shader
de Kunos), pero el `fresnel` sin normal map puede dar brillo raro: ksSpecular bajo. (R6) el ambiente de AC
es uniforme (sin AO): un terreno de 4 texturas sin AO sigue siendo plano; combinar con 3.d.
(R7) `color_ac` no sabe calibrar 4 detalles + base: hay que calibrar cada tile como material virtual
(familia terreno) y pasar el objetivo a `txDiffuse`.

**Alternativa A, sin cambiar de shader: N materiales por cara** (lo que ya hace `color_ac.separar_roca_terreno`
para 2). Generalizar en el writer (o en `exportar_ac.py`, mejor: ahi se guarda la escena de export y se
puede inspeccionar) un `repartir_terreno()`: por triangulo, zona = argmax(matorral, hierba seca, tierra,
roca) con las mismas reglas numpy que la mascara + **ruido por cara** para dentar el borde, y asignar
`MAT_terreno_matorral / _seca / _tierra / _roca` (4 tiles tintados de 512, familia terreno). Ventajas: 0
cambios de formato, funciona sin CSP, kn5_check ya lo valida, color_ac lo calibra solo (4 materiales
mas). Limites: el borde entre zonas es **duro y de 4 m** (triangulos enteros; es exactamente el artefacto
"escalera" de 14/22 pero en AC), no hay mezcla; se mitiga con una 5a y 6a clase de transicion
(matorral+seca, seca+tierra) y con subdividir el terreno a 2 m solo en una banda de 20 m alrededor de la
pista (coste: hoy 266 k vertices; una banda de 20 m a cada lado x 5.2 km pasando de 4 a 2 m anade
~40-50 k vertices; el writer ya parte en trozos de 65 k).

**Alternativa B, vertex color**: **imposible en AC**: el vertice del KN5 es pos3 nrm3 uv2 tan3 (writer
l.444, 551-562; kn5_check l.271: 11 floats) y ksPerPixel no lee color de vertice. CSP tampoco lo lee del
KN5 para mezclar (el VAO de CSP es un fichero aparte). Descartada.

**Alternativa C, solo con CSP**: `extension/ext_config.ini` `[SHADER_REPLACEMENT_...]` (MATERIALS =
MAT_terreno, SHADER = ksMultilayer_fresnel_nm4, PROP_n, RESOURCE_n = txMask + RESOURCE_FILE_n = textura en
`extension/`) sin tocar el writer. Es un extra que no rompe nada sin CSP (la carpeta se ignora), pero sigue
necesitando la UV real del punto 1 y, sin CSP, el terreno se veria con la alternativa A. Claves a confirmar
en la wiki de CSP ("Tracks - Shader replacements"); no hay copia local.

### 3.c Texturas CC0 reales (Poly Haven / ambientCG) en vez de las PIL

Lo que pasa hoy con cualquier imagen que entre por `aplicar_texturas`:

1. `imagen_lineal()` (writer l.185-204) la reduce por media 2x2 hasta **512 px** (`TEX_SIZE`): un tile CC0
   de 2048 pierde 4x de detalle; a 7 m por tile son 1.4 cm/px (suficiente para hierba; corto para una
   caliza de 3 m vista a 1.5 m desde el coche).
2. `construir_textura()` l.271-276 la **tinta**: `gain = 1/media por canal` neutraliza su color y el tono
   lo pone `info['color']` (calibrado por color_ac). Es bueno para la consistencia (el CC0 se "recolorea a
   la paleta" solo) y malo si el CC0 lleva variacion de tono (musgo en la roca, flores): se aplana a
   luminancia por canal. Con `factor` f < 1 (0.7-0.85 en FAMILIAS) la variacion ademas se atenua.
3. Solo se exporta la primera Image sRGB: normal, roughness y AO del paquete CC0 **no viajan** (ksPerPixel
   no tiene samplers para ellos; `ksPerPixelNM` necesitaria `txNormal` + tangentes reales, ver 3.d).
4. Formato: el KN5 embebe PNG (el actual carga en el AC del amigo, luego PNG vale); no se sabe si AC genera
   mipmaps de un PNG. Los circuitos de Kunos llevan DDS con mipmaps; sin mipmaps los tiles de 7 m
   "hormiguean" a distancia. Escribir DDS (BC1/BC3 + mips) desde numpy es factible (cabecera de 128 bytes +
   bloques; o PIL con `pillow` >= 9 que escribe DDS DXT1/DXT5 sin mips) pero es trabajo del writer y hay que
   verificarlo en AC.

Cambios: (i) `aplicar_texturas.FAMILIAS`: `tex=` apunta a los CC0 recoloreados y `ganancia` re-medida;
(ii) nuevo `texturas/recolorear_cc0.py` (PIL, python del sistema): toma el albedo CC0, lo pasa a
luminancia + un tinte de `paleta.json` (o un remapeo de tono hacia la paleta conservando +-15 % de
variacion de croma) y lo guarda a 1024 **seamless comprobado** (`mosaico_3x3_*`); (iii) writer:
`TEX_SIZE` 512 -> 1024 para las familias roca/caliza/asfalto (coste: 87 texturas x4 en bytes, de 12.5 MB a
~45 MB; tolerable en un KN5 de 355 MB) o, mejor, por material (`info['tex_size']`); (iv) `empaquetar.py`
l.281-287 copia `03_blender/texturas/*.png` a `FUENTES/texturas`: los CC0 deben llevar al lado su
`LICENSE.txt` (CC0 no exige atribucion, pero el repo es publico) y no incluir los originales de 4-8 K.
Candidatos a descargar (SOLO listados; nada se descarga en esta fase; nombres de memoria, a confirmar en
polyhaven.com/textures y ambientcg.com antes de pedir permiso; un paquete 2K en JPG/PNG pesa 5-20 MB):
caliza/roca: Poly Haven `rock_face`, `rocky_terrain_02`, `aerial_rocks_02`; ambientCG `Rock035`,
`Rock050`; hierba seca / matorral: ambientCG `Grass004`, `Grass005`, Poly Haven `brown_mud_dry`,
`aerial_grass_rock`; tierra y grava: ambientCG `Ground037`, `Gravel022`; adoquin: ambientCG
`PavingStones070`; teja: ambientCG `RoofingTiles` (varios). Todos CC0 (sin atribucion obligatoria);
URL exacta, version y peso se anotan al pedir el permiso de descarga, uno por uno.

Riesgos: (R8) la textura de hierba seca "real" tiene briznas de 2-5 cm: a 7 m por tile y 512 px no se ven;
hay que bajar el tile a 3-4 m, y entonces la repeticion se nota en las praderas grandes (sin macro-variacion
hoy en AC: en Blender la dan los parches de pradera, que no se exportan: el multicapa de 3.b con `txDiffuse`
de baja frecuencia resuelve justo esto). (R9) color_ac mide el "aspecto" en Blender con las texturas PIL:
cambiar de textura cambia la media -> re-medir (3.a R1).

### 3.d AO horneada y bisel

- **Bisel**: en Blender el nodo Bevel (shader) solo existe en Cycles (el render es EEVEE) y no se exporta;
  el modificador Bevel es geometria real (se exporta) pero multiplica vertices (hoy 7.07 M) y el writer
  suelda por posicion+normal+uv (l.434-445): un bisel de 2 segmentos en 216 casas + muros es asumible
  (+10-20 % vertices), en el terreno no. Alternativa barata para AC: **aristas suavizadas por normal**
  (`shade_smooth` + Auto Smooth 30-40 grados en los kits): el writer exporta `corner_normals` (l.365-366)
  y ksPerPixel las usa; da el "canto redondeado" Pixar sin geometria. Hoy muchos kits van en `shade_flat`.
- **AO horneada** (sin CSP): ksPerPixel solo tiene `txDiffuse`, asi que la AO debe ir **multiplicada
  dentro de la textura difusa**. Eso exige (i) UV unica por objeto (hoy no hay UVs y el writer genera UV
  por coordenadas de objeto repetidas, l.396-404), (ii) una textura por OBJETO y no por material (hoy
  1 textura = 1 material; la fusion por material pondria la misma AO en todas las casas) y (iii) hornear
  en Blender (bake de Cycles, lento con 7 M de vertices). Es un cambio de arquitectura (atlas por kit).
  Lo realista: **AO solo en lo grande y estatico** = TERRENO + rocas de los penones + McLaren: la UV planar
  de 3.b sirve de UV unica para el terreno, y la AO se calcula **en numpy desde el heightmap** (cavidad +
  hillshade suave + oclusion por horizonte, `terreno_montana.py` ya calcula pendiente y gaussianas) y se
  multiplica en `txDiffuse` del multicapa (o en los 4 tiles tintados de la alternativa A, por cara: media
  de AO por triangulo -> NO, eso vuelve a dar escalera; va en la textura). Para penones y McLaren: bake de
  AO en Cycles a una UV por objeto (Smart UV Project) a 1024-2048 y textura propia -> necesita el modo
  "imagen sin tintar por objeto" del writer (nuevo: `info['img']` por objeto en `aportar_fusion`, l.519-537,
  rompiendo la regla 1 material = 1 textura).
- **VAO de CSP (acc-bakeryoptix)**: es la via que pide el usuario y la de menos riesgo para la geometria:
  se ejecuta SOBRE el KN5 ya exportado (no en Blender), produce `extension/porto_corsa.vao-patch` y
  `empaquetar.py` solo tendria que copiarlo junto a `ext_config.ini` (l.284-291 del parche). Dependencias:
  descarga del ejecutable (permiso del usuario), GPU NVIDIA (OptiX) en la maquina que lo corre, y que el
  amigo use CSP (sin CSP se ignora: cumple la regla "extra que no rompe nada"). No se puede comprobar aqui
  (ni AC ni GPU garantizada). Con 7 M de vertices el bake tardara (los circuitos de Kunos tienen 1-3 M).

## 4. Limites del writer y de kn5_check (lista para el coordinador)

Writer (`kn5_writer_opt.py`):
1. Shader fijo `ksPerPixel` y `SHADER_PROPS` constantes (l.83-84, 324-334): cualquier otro shader exige
   escribir shader/props/samplers por material.
2. Un sampler (`txDiffuse`): sin normal, mask, detail, AO.
3. Una textura por MATERIAL, siempre tintada por `info['color']` y reducida a 512 (`TEX_SIZE`), tope 1024
   (`TEX_MAX`): sin texturas por objeto, sin color propio de la imagen, sin texturas grandes (mascaras).
4. Solo lee `diffuse_color` / Base Color sin enlazar + primera Image sRGB + 3 nodos `TEX_*` (l.215-258):
   rampas, atributos, Mix Shader, segundo Principled, bump: ignorados.
5. Sin UVs en la escena: UV generada por coordenadas de objeto (FLAT/BOX) o ceros; con `uv_layers[0]`
   presente la respeta (puerta de entrada para la mascara).
6. Tangentes ficticias (l.448-458): normal maps mal orientados hasta que se calculen desde la UV.
7. Vertice sin color (formato): vertex color descartado.
8. PNG embebido, sin mipmaps garantizados; sin DDS.
9. Fusion por material y trozos de 65 k vertices: "mallas por zona" = materiales por zona.
10. `color_ac` (cuando se aplique) tinta `info['color']` para TODOS los materiales con imagen: un modo
    "imagen tal cual" tiene que esquivar `calibrar_todos` (o calibrar solo props).
11. `separar_roca_terreno` existe pero no esta cableado: hoy el terreno en AC es 100 % hierba.

`kn5_check.py`:
12. No valida shader, props ni samplers contra lo que AC acepta (solo que las texturas referenciadas
    existan, check 5): un `ksMultilayer_fresnel_nm4` con un sampler mal llamado pasa OK.
13. No valida tamano/potencia de 2/mipmaps/formato de texturas (solo informa); no valida rango de UV ni
    tangentes; no detecta materiales duplicados o sin uso.
14. No hay AC en este PC: la unica prueba real del shader es el amigo. Hay que preparar un **KN5 de ensayo
    minusculo** (plano + 1 material multicapa) para que lo pruebe antes del circuito entero.

## 5. Que haria falta para el plan del usuario (cambios concretos, riesgos, dependencias)

Orden propuesto (cada paso con capturas antes/despues desde las 6 camaras de piloto + aereas):

| # | Cambio | Ficheros | Depende de | Riesgo |
|---|---|---|---|---|
| 1 | `paleta.json` unico + kits y construir_pista leyendo de el; `diffuse_color` = media deseada | nuevo `03_blender/paleta.json`; construir_pista l.86-114, 179-181, 262-263, 1169, 1285; roca_lazo l.150; roca_casino l.99; penon_cara l.303; montanas_fondo_v2 l.245; montana_mclaren l.255; casas_kit_v2 l.87; vegetacion | nada | R1 (re-medir color_ac), R3 |
| 2 | Tiles nuevos (seca, matorral, cesped, caliza ocre, terracota) PIL o CC0 recoloreados; re-medir `ganancia` | generar_texturas.py; nuevo recolorear_cc0.py; aplicar_texturas FAMILIAS l.44-65 y familia_de l.73-101 (familia `cesped`, `matorral`) | 1; permiso de descarga si CC0 | R8, R9 |
| 3 | UV planar en TERRENO + `mascara_terreno.py` (RGBA numpy desde geometria_3d.json) + `mat_terreno()` que mezcle 4 tiles por la mascara (Blender) | construir_pista l.92-183, 1467-1474; nuevo mascara_terreno.py; aplicar_terreno l.247-342 (retirar para MAT_terreno) | 1, 2 | solo Blender: sin riesgo en AC |
| 4a | Writer: shader/props/samplers por material + texturas sin tintar y > 1024 para txMask + `kn5_check` check 9 + KN5 de ensayo para el amigo | kn5_writer_opt l.63-64, 215-258, 261-283, 301-339; color_ac calibrar_todos l.716-736; kn5_check comprobar l.366-571 | 3; **que el equipo del zip v1.1 haya cerrado y aplicado el parche color_ac** (no tocar 04_export hasta entonces) | R4 (alto: no se puede probar aqui), R5, R7 |
| 4b | Alternativa A (si 4a no se puede verificar a tiempo): `repartir_terreno()` en exportar_ac.py -> 4-6 materiales `MAT_terreno_*` por cara con ruido | exportar_ac.py (tras l.71); color_ac `_REGLAS` l.323 ya los clasifica como terreno | 1, 2 | bordes duros de 4 m (mitigar con clases de transicion) |
| 5 | AO: numpy desde heightmap en `txDiffuse` del terreno (4a) o en la mascara; VAO acc-bakeryoptix como extra CSP; `shade_smooth`/auto smooth en kits para el "bisel" | terreno_montana.py (gaussian ya importado); empaquetar.py (copiar .vao-patch); kits | 4a; descarga del bakery (permiso) + GPU NVIDIA + CSP del amigo | medio: no comprobable aqui |
| 6 | Re-medir color_ac (render_ac.py + medir_objetivos.py + medir_albedo.py) y regenerar KN5; informe_color_ac nuevo | `_rev/color_ac/*`, `04_export/color_ac_*.json` | todo lo anterior | R1 |

Lo que se puede validar en este PC: capturas de Blender (paleta, mascara, tiles), `kn5_check.py` ampliado,
`_color_ac_prueba/leer_kn5_color.py` (props y colores de dos KN5), simulacion de color_ac. Lo que solo se
valida en el PC del amigo: que el shader multicapa cargue, mipmaps/PNG, VAO, FPS (la mascara 2048-4096 y
los 4 tiles anaden 20-60 MB al KN5 y 5 samplers por pixel de terreno; en una GPU modesta con 12 coches
puede notarse: mantener la alternativa A como plan B).
