# Investigacion: por que Porto Corsa sale lavado en Assetto Corsa y que valores usar (v3)

Fecha: 2026-10-04. Ronda 3: secciones 2b (tiempos de Kunos y post-proceso apagado), 5 (agua de CSP), 6 (captura) y 7
nuevas o rehechas; la nota de Mugello corregida. Fragmentos literales cortos entre comillas; lo demas es resumen
nuestro. Las cifras son las que usa `04_export/color_ac.py` v3.

## 1. Como sombrea AC y como lo cambia CSP

- **AC sin CSP: espacio gamma.** La textura sRGB se multiplica por la luz tal cual, sin pasarla a lineal.
  - Wiki de CSP, *General: Linear color space*
    ([github-wiki-see](https://github-wiki-see.page/m/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Linear-color-space),
    texto descargado de `raw.githubusercontent.com/wiki/...`). Explica que es un error facil para un juego que
    "the actual 3D shading is also done in sRGB", y que en AC "any shading-related computation in AC was
    completely incorrect".
  - Los estilos de WeatherFX se ajustaban con valores falsos para compensarlo, segun la wiki "even for
    something as basic as sun/ambient light relation". Por eso un estilo gamma de CSP puede llevar mucho mas
    ambiente que Kunos (ver la configuracion estimada de la captura, seccion 6).
- **Formula del shader ksPerPixel.** Es la de Kunos que reproduce Content Manager
  (`04_export/kn5_refs/actools_b/AcTools.Render/Shaders/Includes/DarkMaterial.Lighting.Simple.fx`):
  `color = tx * (ksAmbient*AMBIENTE + ksDiffuse*SOL*max(N.L,0)*sombra + ksEmissive) + ksSpecular*N.H^ksSpecularEXP*SOL*N.L*sombra`.
  El ambiente es uniforme y no hay oclusion. Sin props, AcTools usa ksAmbient 0.4, ksDiffuse 0.6 y
  ksSpecularEXP 50 (`Kn5Basic.cs`).
- **Espacio lineal de CSP (LCS).** Llego en CSP 0.2.3, viene desactivado y lo activa el estilo de WeatherFX.
  - Lo que cambia: el producto textura x parametro pasa a lineal. La wiki pone como ejemplo de conversion
    `resultEmissive = pow(ksEmissive * txDiffuse, 2.2)`. Para los scripts aconseja pasar textura x ksDiffuse
    por `toLinearColorSpace()`.
  - Conversion final a sRGB: la puede hacer el estilo con su propia curva o, si no, "By default CSP would do
    that step for you before sending image to YEBIS". De ahi salen los dos modelos lineales de la simulacion:
    curva ACES (`lcs`) y conversion a sRGB + curva Yebis del filtro (`lcsy`). La curva real de cada estilo no
    esta documentada.
  - Consejo para materiales: salvo con fuPBR, "consider targeting old color space for now". Es decir, apuntar
    al espacio gamma. Por eso el modo gamma pesa 0.6 en el ajuste (0.2 cada modelo lineal).
- **Pure Gamma y Pure LCS.** El estilo Pure tiene las dos variantes. Una guia de Pure dice que Pure Gamma puede
  dar un aspecto "slightly 'washed-out' look due to comparatively higher brightness levels"
  ([simracingcockpit.gg](https://simracingcockpit.gg/what-is-the-pure-weather-mod-for-assetto-corsa-and-how-do-i-install-it/)).
  En el estilo por defecto de CSP, LCS es una opcion de los ajustes de WeatherFX (resumen de hilos de GTPlanet
  que dio el buscador; GTPlanet devuelve 403 y no se pudo abrir).

## 2. Luz, tiempo y post-proceso de AC

- **Tiempo `3_clear`** (tabla de presets de [newksEditor src/lighting.js](https://github.com/619motorsports/newksEditor/blob/main/src/lighting.js),
  sacada de `sdk/editor/content/weather/*`). Cada componente HDR vale RGB x intensidad / 255
  (`GraphicsManager::loadLightingSettings` en `ksNet.dll`,
  [newksEditor docs/RESEARCH.md](https://github.com/619motorsports/newksEditor/blob/main/docs/RESEARCH.md), lineas ~2189-2269).
  - SOL HIGH 170,160,140 x 20, es decir (13.3, 12.5, 11.0): calido. AMBIENTE HIGH 105,105,105 x 11 = 4.53 gris.
  - HORIZON HIGH 150,170,220 x 3.5 y SKY HIGH 30,73,167 x 3. Niebla: color (1.8, 2.37, 3.42), blend 0.85,
    distancia 9000 m (a 500 m apenas un 5 %; la formula exacta de la niebla es una suposicion nuestra).
  - El `system/cfg/colorCurves.ini` del juego ([scullionw/ac-config](https://github.com/scullionw/ac-config/blob/master/system/cfg/colorCurves.ini))
    trae otros valores: SUN HIGH 170,170,160,20 y AMBIENT HIGH 85,105,128,10. Simulado con ellos, el resultado
    apenas cambia: deltaE 25.5 -> 15.0, frente a 25.0 -> 14.9 con 3_clear (`sensibilidad_luz_ac.json`).
- **Post-proceso.**
  - Limites de la autoexposicion 0.2-0.5: RESEARCH.md los saca del `cfg/lighting.ini` del editor. El
    `system/cfg/ppfilters/default.ini` del juego lo confirma (misma copia de scullionw): AUTO_EXPOSURE
    ENABLED=1, MIN 0.2, MAX 0.5, TARGET 0.32.
  - TONEMAPPING GAMMA 1.2 y FUNCTION -1 (curva Yebis). COLOR SATURATION 0.95, aplicada antes de la curva.
  - Curva recuperada del binario: `q = exp(-2.658*x)`, `y = (1-q)*(1-0.665*q)^2 + 2^-22`, salida `y^(1/1.2)`.
- **Consecuencia.** Con nuestras texturas pastel la escena es tan clara que la autoexposicion se queda en 0.2.
  Lo iluminado cae en el hombro de la curva y sale blanco y sin color: asfalto al sol 161,154,146 y hierba
  220,228,185 en el modelo con los ajustes por defecto.

## 2b. Tiempos de Kunos y post-proceso apagado (nuevo en la v3)

- **Los siete tiempos del SDK** (misma tabla de newksEditor `src/lighting.js`, `RAW_STOCK_WEATHER`; cada componente
  RGB x intensidad / 255, mezcla HIGH -> LOW con `pow(1 - sol.y, ANGLE_GAMMA)`). Con el sol de nuestra escena (56 grados):
  - `3_clear`: sol 13.3 / 12.5 / 11.0, ambiente 4.5 gris: el ambiente es un tercio del sol.
  - `5_light_clouds`: sol 4.1 / 4.0 / 3.7, ambiente 7.2 / 7.8 / 8.4 azulado, nubes que cubren todo el cielo. El
    ambiente pesa el DOBLE que el sol: todo sale plano. Es el tiempo con el que arranca el editor (RESEARCH.md:
    `sdk/editor/cfg/race.ini`).
  - `2_light_fog`: sol 5.2 / 5.1 / 5.0, ambiente 5.1 / 5.3 / 5.5, niebla gris a 2700 m con blend 0.85.
  - `6_mid_clouds` y `7_heavy_clouds`: sin sol, solo ambiente.
  - Estan en `color_ac.TIEMPOS_AC` (3_clear, 5_light_clouds, 2_light_fog) y en `tiempos_captura.py` (los demas).
- **Post-proceso apagado.** Segun RESEARCH.md, al desactivar el camino HDR del post-proceso AC aplica ademas
  `HDR_OFF_MULT` a la luz. En el `system/cfg/colorCurves.ini` del juego (copia de scullionw) vale 0.28, y en
  [Steam](https://steamcommunity.com/app/244210/discussions/0/558752449812127177) se recomienda subirlo o bajarlo para
  ajustar el brillo sin HDR (un usuario usa 0.575). Como no conocemos la formula exacta de ese camino, no se simula:
  es una de las preguntas para el amigo.
- **Brillo en el juego.** Con el HDR activo, Re Pag / Av Pag cambian la exposicion (mismo hilo de Steam): es lo que
  modelamos como "brillo" en la configuracion estimada.

## 3. Valores de los materiales en circuitos de Kunos y mods

- **CSP**, misma pagina de LCS: "your ksAmbient/ksDiffuse values should be around 0.4…0.6", y ademas
  "please try and keep them similar".
- **Circuitos corregidos por CSP** ([configs de CSP](https://github.com/ac-custom-shaders-patch/acc-extension-config/tree/master/config/tracks)):
  - `mugello.ini`, valores OFF_VALUE (los que el ajuste de CSP deja cuando esta apagado), como ksDiffuse / ksAmbient.
    Que sean los originales de Kunos es una inferencia nuestra: el fichero no lo dice.
    - hierba 0.25 / 0.35; grass-brd2 0.225 / 0.325; temp 0.20 / 0.25; grassBB 0.15 / 0.225;
    - skybox 0.25 / 0.30; arboles 0.14-0.15 / 0.175.
  - `mugello.ini`, ajustes "deneonize": bordillo 0.225 / 0.325, objetos 0.30 / 0.30, asfalto 0.325 / 0.40.
  - `ks_drag.ini`: hierba y muro 0.2 / 0.2; asfalto ksDiffuse 0.3, ksAmbient 0.25, ksSpecular 0.1, ksSpecularEXP 6.
  - En Mugello ksAmbient >= ksDiffuse (cociente 1.0-1.4), pero no siempre: en ks_drag el asfalto lleva
    ksAmbient 0.25 < ksDiffuse 0.30. Son texturas de foto, oscuras.
- **Foros**:
  - ksAmbient es el brillo en sombra y ksDiffuse el brillo al sol
    ([overtake: Very white or bright textures](https://www.overtake.gg/threads/very-white-or-bright-textures.220379/)).
  - Para hierba demasiado clara se baja ksAmbient/ksDiffuse a 0.20-0.30 via ext_config
    ([overtake: Changing the colour of grass](https://www.overtake.gg/threads/changing-the-colour-of-grass.243989/),
    [assettocorsamods: lower the brightness](https://assettocorsamods.net/threads/can-i-lower-the-brightness-of-that-texture.3603/)).
  - ksAmbient entre 0.1 y 1; con 0 las sombras salen negras
    ([assettocorsamods: strange shadows](https://assettocorsamods.net/threads/strange-shadows-lighting-on-my-track-and-other-objects.2136/)).
- **Albedos de referencia**, en lineal:
  - [physicallybased.info](https://physicallybased.info/): asfalto nuevo 0.043, hierba 0.105, hormigon 0.51,
    arena 0.44, nieve 0.85.
  - [Wikipedia, Albedo](https://en.wikipedia.org/wiki/Albedo) (albedo solar de banda ancha, no sRGB): asfalto
    nuevo 0.04, asfalto gastado 0.12, hierba verde 0.25, hormigon nuevo 0.55, nieve reciente 0.80.
  - Las nuestras: luminancia lineal mediana 0.39 y p90 0.86. La hierba exportada era (0.32, 0.45, 0.20), cuando
    la del render es (0.066, 0.271, 0.019).

## 4. Shaders

- Lista de shaders y sus texturas: [overtake: AC shaders, texture maps list](https://www.overtake.gg/threads/assetto-corsa-shaders-texture-maps-list.126166/).
- **ksPerPixel** (txDiffuse): difuso + especular. Es el que escribimos y basta para colores planos.
- **ksPerPixelMultiMap** (txDiffuse, txNormal, txMaps, txDetail): especular, brillo y reflejo por pixel.
  Necesita txMaps y txDetail (pendiente).
- **ksMultilayer / ksMultilayer_fresnel_nm** (txMask + 4 detalles): el de las carreteras de Kunos
  ([assettocorsamods: Photo Quality Road Surface](https://assettocorsamods.net/goto/post?id=3602)). Permitiria
  mezclar hierba y roca en el terreno como Blender (pendiente: ver seccion 7).
- **ksTree**: arboles de billboard con alfa. Nuestra vegetacion es geometria 3D, asi que se queda en ksPerPixel.

## 5. CSP: `extension/ext_config.ini` de la pista

Fuente: wiki de CSP, *Tracks: General options* (descargada). Las claves vienen en un bloque de ejemplo con
valores; la wiki no siempre dice cuales son los valores por defecto.

- **[BASIC]**: SUPPORTS_WIND, RALLY_TRACK, PITBOXES, IGNORE_OTHER_CONFIGS.
- **[LIGHTING]**: ENABLE_TREES_LIGHTING, BOUNCED_LIGHT_MULT, LIT_MULT, SPECULAR_MULT, CAR_LIGHTS_LIT_MULT,
  TERRAIN_SHADOWS_THRESHOLD.
  - TRACK_AMBIENT_GROUND_MULT aparece con 0.5 de ejemplo y el aviso "only define it if needed!".
  - **No lo definimos.** En la v1 con 0.35, el propio modelo dejaba las paredes en sombra en 84,66,46, frente a
    149,133,107 en Blender.
- **Ninguna clave cambia el sol o el ambiente.** El brillo se arregla en el material (KN5) o con
  [MATERIAL_ADJUSTMENT_n] (KEY_n, VALUE_n, ACTIVE, MATERIALS con comodin ?). Dejamos una palanca desactivada:
  ksAmbient 0.30 / ksDiffuse 0.55, solo con CSP (`palanca_csp.py`: ayuda con mucho ambiente, empeora con LCS).
- **Agua de CSP**: `[INCLUDE: common/materials_track.ini]` + `[Material_Water] Materials = ... Type = SEA`
  ([wiki Water shader](https://github-wiki-see.page/m/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Water-shader)).
  - v3: **desactivada por defecto.** En la plantilla `[TEMPLATE: Material_Water]` de
    [materials_track.ini](https://github.com/ac-custom-shaders-patch/acc-extension-config/blob/master/config/tracks/common/materials_track.ini)
    el shader usa por defecto sus texturas de normales (`UseRecommendedTextures = 1`) con las UV de la malla. Nuestra
    malla AGUA es un quad de 4 vertices y ~20 km con UV 0..1: las olas saldrian estiradas. Se puede activar con
    `color_ac.py --ext-config <ruta> --sobrescribir --agua` cuando la malla lleve UV en metros.
- **Oclusion por vertice** (VAO, CustomTracksBakery): [wiki Vertex AO](https://github-wiki-see.page/m/ac-custom-shaders-patch/acc-extension-config/wiki/Tracks-%E2%80%93-Vertex-AO).
  Daria el volumen que en Blender aporta la oclusion (pendiente).
- **empaquetar.py** copia `04_export/extension/ext_config.ini` tal cual. `color_ac` solo lo genera si no
  existe, asi que los ajustes a mano no se pierden.

## 6. Lo que se midio en Blender y en la captura

- **Escena congelada propia** (v3): `escena_color.blend`, copia de `escena_rev.blend` de las 13:00 (md5 en
  `escena_color.md5`). render_ac.py, medir_albedo.py y volcar_materiales.py solo abren esa copia, asi que los pases ya
  no se desfasan cuando otro equipo toca la escena.
- **Luz de nuestro render, POR CANAL.** K = pantalla lineal / albedo (pases `ref` y `alb` de `render_ac.py`),
  mediana de las vistas de ajuste en materiales difusos sin recortar (`luz_escena.json`). Con la escena congelada y
  las 7 vistas de la v3:
  - suelo al sol (1.67, 1.80, 2.39) y pared al sol (1.08, 1.19, 1.40);
  - pared en sombra (0.34, 0.47, 0.63) y suelo en sombra (0.23, 0.41, 0.70).
  - `color_ac.K_BLENDER` conserva los de la v2 (1.65/1.82/2.30, 1.15/1.27/1.42, 0.36/0.49/0.65, 0.23/0.41/0.65):
    menos de un 7 % de diferencia, y solo se usan sin aspecto medido y para la luz de los modos lineales.
  - La luz de Blender es azulada (B/R 1.4 al sol y 1.8-2.8 en sombra); la de AC 3_clear es calida (B/R 0.82).
- **Aspecto real de cada material** (`medir_objetivos.py` -> `04_export/color_ac_objetivos.json`, 151 materiales,
  7 vistas de ajuste). Ejemplos:
  - el asfalto brilla por el reflejo del cielo: 98,101,111 al sol;
  - el mar (nueva vista `meta_puerto`, la unica de ajuste con agua): 155,212,248;
  - la hierba del terreno 107,181,87 y, aparte, sus caras de roca (`MAT_terreno_roca`) 164,171,150 al sol.
- **Roca del terreno.** El criterio del writer (`color_ac.mascara_roca`: N.z < 0.50, o atributo `roca` > 0.49 con
  N.z < 0.82) coincide con la mascara del nodo de Blender (pase `msk`) en el 96.5 % de 1.09 millones de pixeles de
  terreno de las 10 vistas; los umbrales se eligieron asi (0.53 daba 96.2 %).
- **Captura del usuario** (`captura_juego.png`; zona de juego sin coche ni HUD): luminancia 183, saturacion 0.084,
  asfalto 156,154,157 neutro, cielo 215,221,225, bruma a media distancia y casi sin sombras. El coche de Kunos sale
  con su rojo saturado (206,61,46 al sol): el filtro no desatura, lo lavado es la luz sobre nuestras texturas.
  - **Hipotesis 1, configuracion estimada** (`ajuste_captura.py`, 4 parametros): estilo gamma con sol blanco de
    WeatherFX, ambiente x4.4, brillo x0.5, bruma a 400 m, saturacion 1.0. Reproduce la captura (coste 1.45: lum
    177, sat 0.071, asfalto 156,155,158). Con el brillo por defecto daria lum 236: casi blanco. El usuario dice ahora
    que el amigo lo estuvo tocando para que se notara lo menos posible y que antes era peor: encaja con un brillo
    bajado.
  - **Tiempos de Kunos** (`tiempos_captura.py`): ninguno la reproduce con el brillo por defecto (coste 75 con
    3_clear, 224 con 5_light_clouds, mas de 370 con niebla o nubes). La **hipotesis 2** es 5_light_clouds con el brillo
    SUBIDO x1.4 y saturacion 0.7 (coste 3.8). Encaja peor con "lo bajo", pero explica igual de bien el cielo blanco y la
    falta de sombras: en los dos casos el ambiente pesa mas que el sol.
  - **Son estimaciones, no datos**: hay que preguntar al amigo si usa CSP (y que estilo de tiempo y filtro), que
    tiempo elige, si tiene el post-proceso apagado y que toco.

## 7. Limitaciones que siguen

- **Sin oclusion en AC.** Un bake de VAO de CSP (CustomTracksBakery) daria el volumen que en Blender aporta la
  oclusion.
- **El asfalto en gamma sigue algo claro y calido** (118-125 en las vistas frente a 92-101 en Blender): el sol de
  3_clear es calido y en los modelos lineales el mismo asfalto ya sale azulado y algo oscuro (Yebis: deltaE 7.2 frente
  a 5.1 antes). El reflejo del cielo que lo enfria en Blender pediria ksPerPixelMultiMap con txMaps (pendiente).
- **Tiempo nublado.** Con 5_light_clouds las rectas salen mas oscuras que el render soleado de Blender (3 vistas
  peor que antes): es lo esperable en un dia nublado; el resto mejora.
- **Modos lineales.** La curva de cada estilo LCS no esta documentada: `lcs` (ACES) y `lcsy` (sRGB + Yebis) con la luz
  de Blender son aproximaciones. El modo gamma esta modelado con los valores del juego.
- **El brillo por defecto de la configuracion estimada** lo lava todo (deltaE 46 -> 41): si el amigo vuelve a esos
  ajustes, ningun color de textura lo arregla; la palanca de ext_config.ini ayuda algo (41 -> 36).
