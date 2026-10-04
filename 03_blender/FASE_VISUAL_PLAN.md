# Porto Corsa — PLAN FINAL de la FASE VISUAL (síntesis del juez, 04/10/2026)

Síntesis de los tres planes de `_rev/fase_visual/` (A ambición, B riesgo, C jugador), del encargo del usuario
(`_rev/fase_visual/PLAN_USUARIO.md`), del veredicto del director (`_rev/director_final.md`) y de los 11 informes.
Puntuaciones y motivos en `_rev/fase_visual/juez_puntuaciones.md`. Ganador: **plan C** (orden por lo que se ve
desde el coche) por un punto sobre el B; este plan final es **el orden del C con la red de seguridad del B**
(puerta de calidad, escena candidata, KN5 de ensayo, presupuestos, zips escalonados) y tres piezas del A
(custom properties `ac_*` desde el primer día, `paleta.json` como única fuente de color, cabo bajo la zaga del
McLaren como pregunta al usuario). Nada de este plan se ha ejecutado: no se ha tocado ningún fichero del
proyecto ni se ha lanzado Blender.

Etiquetas: **[E]** esencial, se ve en AC "a pelo"; **[X]** extra que solo actúa con CSP y no rompe nada sin él;
**[W]** necesita cambios en `04_export` (cerrado hasta que el equipo del zip v1.1 termine; se entrega como lista
`PETICIONES_04_EXPORT.md`, bloque X); **[U]** necesita una respuesta del usuario (sección 14).
Las líneas de código citadas (l.) son las de los informes del 04/10 por la mañana: comprobar antes de editar.

---

## 0. Las diez decisiones que mandan

1. **Proteger el zip v1.1 ANTES de nada**: hoy `_rev/pipeline_escena.sh` l.35 copia `porto_corsa.blend` a
   `_rev/escena_rev.blend` en cada ejecución, y `04_export/hacer_zip.sh` exporta `escena_rev.blend`. La primera
   regeneración de la fase visual pisaría la escena que el otro equipo está cerrando. Primer cambio de la fase
   (solo en `_rev/`): el pipeline copia a `_rev/escena_candidata.blend`; `escena_rev.blend` solo cambia por
   `_rev/promover.sh` cuando `_rev/puerta_calidad.py` da `ok: true` (plan B §1.2).
2. **Dos verdades y una sola juez**: cada hoja A/B se renderiza en modo "Blender" y en modo `--modo-ac`
   (sin sombras de vegetación/terreno, sin GTAO, materiales reducidos a lo que exporta el writer: color plano o
   tile tintado de 512). El criterio de "bloque cerrado" es el modo AC (plan C §0.3). Hoy, en AC a pelo, la pista se
   ve PEOR que en las capturas (terreno = un tile verde tintado, rocas = colores planos, sin AO ni sombra de árboles).
3. **Orden desde el coche**: bloque 3 (paleta + máscara por texel + luz) va primero porque está en las 6 vistas de
   piloto y no toca geometría; en paralelo, lo barato y seguro del resto (caliza compartida, tierra tallada + berma,
   horizonte, plan de vegetación). El macizo alto, la erosión, el puerto-llanta, villas/camping y la silueta
   Topolino son cosas de cámara aérea: después o fuera.
4. **El terreno pasa de "atributo por vértice" a "máscara por texel"** en Blender desde el bloque 3 (`mascara_terreno.py`,
   RGBA 2048 = 1 m/texel, UV planar en TERRENO). Es lo que elimina el defecto 4 del director (dientes de sierra,
   escaleras, hierba estirada) y el 3 (desmontes pintados). Al KN5 llega por uno de dos caminos [W]: (A)
   `repartir_terreno()` por cara (4-6 materiales, sin cambio de formato, bordes de 4 m) o (B) `ksMultilayer_fresnel_nm`
   vanilla (por texel) SOLO si el KN5 de ensayo carga en el PC del amigo. Nunca `_nm4` en el KN5 (es de CSP).
5. **Custom properties `ac_shader` / `ac_props` / `ac_samplers` / `ac_tex_max` / `ac_alpha_test` / `ac_raw`** en
   todo material nuevo desde el primer día (plan A A3), con valor por defecto = comportamiento actual. Cuando
   `04_export` abra, el cambio del writer es mecánico y se prueba primero con 5 KN5 minúsculos de ensayo.
6. **McLaren**: faldón de ladera + pedruscos + grietas + caliza menos clara (quita "repisa" y "plástico" desde el
   coche) se hace sí o sí; el **cabo de tierra bajo la zaga** (lo único que quita el "islote" en 01/02/13 y en la
   postal de la recta del puerto) es la pregunta 4; el túnel "por la rueda" se resuelve con portal de sillería de
   11-12 m hasta los radios (sin tocar física) salvo que el usuario pida hundir el coche (pregunta 5).
7. **La rasante de la tierra no se toca** (ya va al 13-16.5 %, por encima del 12-15 % pedido; bajarla rebaja la cima a
   ~105 m y toca física validada). El "más desnivel" viene del terreno lateral: pared en un lado y caída en el otro.
   Solo se suavizan los apex de las horquillas C18-19/C26 a <= 9-10 % (física: s 2365).
8. **Presupuestos duros** (sin AC no hay FPS; se controlan los indicadores que correlacionan): tris <= 6.0 M (hoy
   5.26; vegetación de 1.74 M a <= 0.9 M con el triple de densidad), mallas <= 800, materiales <= 520, texturas en
   el KN5 <= 80 MB, KN5 <= 450 MB, zip <= 250 MB [U]. `_rev/kn5_presupuesto.py` falla si se supera un tope.
9. **Vegetación**: kit v3 `sin_alfa` (casquetes cóncavos de borde ondulado, <= 250 tris) es lo esencial; hojas con
   alfa y sombra solo tras W; TreeFX es una capa extra con la MISMA lista (`vegetacion_plan.json`), nunca la única.
10. **CSP inerte sin CSP**: todo en `extension/` con `ACTIVE = 0` por defecto; `ksEmissive = 0` en el KN5; animados
    como nodo `ANIM_` del KN5 principal (quietos en pose creíble sin CSP); árboles del KN5 nunca ocultos antes de
    ver TreeFX funcionando en el PC del amigo.

---

## 1. Contrato de capturas antes/después (vale para todos los bloques)

**Herramientas** (bloque 0, todas nuevas en `03_blender/_rev/`, ninguna toca el pipeline):
- `tomas_capturas.py`: `construir_tomas(G, bpy) -> [(nombre, loc, tgt, lens)]` = l.45-330 de `renderizar_capturas.py`
  en una función + las tomas nuevas de abajo. Las 5 tomas inútiles (15, 34_desde_pista, 43, 47b, 40) se arreglan AQUÍ.
- `capturas_ab.py` (esbozo en `entender_agua_publico_capturas.md` §9.5): `--blend --geom --set <bloque> --out <dir>
  [--camaras cams.json | --guardar-camaras cams.json] [--solo pref] [--res 1600x900] [--modo-ac]`.
  `camara_segura` actúa UNA vez (al congelar); el "después" lee loc/tgt/lens tal cual y NO mueve nada; si una
  cámara queda dentro del relieve nuevo se avisa en `ab.log`, se renderiza igual y se añade una toma nueva con otro
  nombre (nunca se mueve la vieja).
- `montaje_ab.py` (PIL): pares y hojas. `medir_capturas.py` (PIL/numpy, plan C §0.5): `pct_cesped`, `riqueza`,
  `bandas_blancas`, `pared_lisa`, `siluetas_20_120` -> `medidas.json`.

**Cámaras fijas** (set `BASE`, en TODAS las hojas, a tamaño completo las de piloto):
| Toma | Nombre de fichero | Dónde | Juzga |
|---|---|---|---|
| aérea general | `01_aerea_general` | la actual | macizo, costa, McLaren, horizonte |
| piloto s300 | `49_piloto_s300` | 1.4 m, s 300 | McLaren, portal, talud, césped |
| piloto s800 | `50_piloto_s800` | s 800 | pueblo, terrazas, muros |
| piloto s1700 | `51_piloto_s1700` | s 1700 | tierra tallada, desmontes, afloramientos |
| piloto s2900 | `52_piloto_s2900` | s 2900 | recta de subida, masas, acantilado lado mar |
| piloto s3400 | `53_piloto_s3400` | s 3400 | casino, carificación |
| piloto s4150 | `54_piloto_s4150` | s 4150 | roca del lazo, mar |
| postal 1 túnel | `55_postal_tunel_salida` | piloto s 528, tgt s 610, lente 20 | portal, talud, mar |
| postal 2 cima | `56_postal_cima_bahia` | s 1870 mirando S/SE a la bahía, lente 20 | bahía entera, nada a < 40 m |
| postal 3 viaducto | `57_postal_viaducto` | s 3660, tgt s 3760 | viaducto, lazo con bancos, mar |
| postal 4 fuente | `58_postal_loews` | s 3500 bajando, tgt Loews [U pregunta 7] | rotonda, casino, farolas |
| postal 5 puerto | `59_postal_recta_puerto` | s 60 mirando a s 140, lente 20 (+ variante s 5150) | tribunas, puerto, McLaren al fondo |
| aéreas de apoyo | `07_tierra_subida`, `13_puente_alto`, `21_montana_dentro_del_lazo`, `36_roca_casino_general` | las actuales | relieve, rocas, peñón |
Más las tomas nuevas 60-63 de `entender_agua` §9.2 (`60_puerto_llanta_cenital`, `61_orilla_piloto_s150`,
`62_tribuna_piloto_s5100`, `63_horizonte_piloto_s2200`) y, por bloque, el set adicional que indica cada sección.

**Nombres de salida**: `renders/ab/<bloque>/camaras.json`, `antes/<toma>.png`, `despues/<toma>.png`,
`antes_ac/`, `despues_ac/`, `AB_<toma>.png`, `AB_ac_<toma>.png`, `hoja_<bloque>_piloto.png`,
`hoja_<bloque>_aereas.png`, `medidas.json`, `ab.log`. El "antes" global de la fase se congela una vez en
`renders/ab/_base_antes/` + `_rev/escena_antes_visual.blend` (copia, 42 MB).

**Criterio de aceptación de un bloque** (los cinco a la vez):
1. Calibración: un A/B de la misma escena (antes = después) da diferencia de píxel 0 en todas las tomas.
2. Los KPI del bloque (su sección) se cumplen en `medidas.json` del modo AC, no solo del modo Blender.
3. `_rev/puerta_calidad.py` -> `puerta.json ok: true`: `urbanismo.py` 0 fallos y >= 190 casas, `revisar_urbanismo`
   <= línea base (23 hoy, objetivo 0) y 0 nuevos de tipo casa_pista/casa_muro/losa, `nada_en_pista` <= 11 y 0 en
   tierra, `asentar.json` no peor que la base, `checks` del terreno (`celdas_invaden_pista` 0, `hierba_asfalto` 0,
   fosos <= 1.5, costuras < 0.6, `loews_ref_dz_max` 0.000), `integrar_escena.log` "ERRORES: ninguno",
   `kn5_presupuesto.py` sin topes superados (cuando haya export de prueba).
4. Sin regresión en ninguna toma BASE: el revisor marca cada toma "ok / mejora / regresión" en la hoja; UNA
   regresión en una vista de piloto bloquea la promoción (se arregla o se revierte el cambio).
5. La hoja A/B y 3 líneas en el REGISTRO DE ARREGLOS de `RONDA15_PLAN.md` acompañan a la promoción
   (`_rev/PROMOCIONES.md`: fecha, md5, bloque, hoja).

---

## 2. Bloque 0 — Infraestructura de juicio y de seguridad (día 1-2; nada se promueve sin esto)

**Objetivo medible**: renderizar el set BASE (17-20 tomas) antes/después desde cámaras idénticas en < 90 s de
cola, con hoja lado a lado, modo AC y medidas; `escena_rev.blend` protegida por puerta; presupuesto automático;
5 KN5 de ensayo listos para el amigo; `PETICIONES_04_EXPORT.md` abierto.

**Cambios técnicos** (todo en `03_blender/_rev/`, python del sistema salvo `capturas_ab.py`):
1. `tomas_capturas.py`, `capturas_ab.py` (con `--modo-ac`), `montaje_ab.py`, `medir_capturas.py` (sección 1).
2. `pipeline_escena.sh`: copia a `escena_candidata.blend` (+ `geometria_candidata.json`, `urbanismo_candidata.json`)
   en vez de a `escena_rev.blend`. `puerta_calidad.py` (lee solo JSON/logs, escribe `puerta.json` con diff contra
   `linea_base.json` = snapshot de hoy 13:00). `promover.sh` (solo con `ok`, anota en `PROMOCIONES.md`, guarda
   `promociones/escena_vN.blend`). `hacer_zip.sh` NO se toca.
3. `kn5_presupuesto.py <informe_check.json> [--base informe_check_opt.json]`: topes de la decisión 8 y aviso si
   una familia (prefijo de malla / `MAT_`) crece > 50 %.
4. `kn5_ensayo.py` (~150 líneas, formato KN5 v5 según `kn5_check.py` l.19-20 y `kn5_refs/`): 5 KN5 minúsculos
   (plano `1ROAD_` de 20 m + `AC_START_0` + un plano de 4 triángulos), uno por hipótesis: (a) `ksMultilayer_fresnel_nm`
   con txMask 2048 sin tintar, (b) `ksPerPixelAT` con PNG RGBA (alfa test), (c) `ksTree`, (d) PNG 2048 (mipmaps,
   UV de usuario), (e) nodo `ANIM_` + `castShadows` con alfa. `kn5_check` los valida aquí; el amigo los carga y manda
   5 fotos. Salida en `_rev/kn5_prueba/ensayos/` (no en `04_export`) + `LEEME.txt` de 10 líneas.
5. `kn5_prueba/`: `kn5_writer_opt.py` y `exportar_ac.py` admiten `BLEND`/`KN5`/`SALIDA`/`GEOM` por entorno: se
   EJECUTAN sobre copias con salida en `_rev/kn5_prueba/` sin modificar `04_export`. Una vez por bloque, no por
   iteración (15-30 min; el zip v1.1 lo medirá).
6. `fase_visual/PETICIONES_04_EXPORT.md`: una línea por petición (P1-P10 del plan B §1.6 + la lista X), con el
   bloque que la necesita y su prueba.
7. `03_blender/paleta.json` + `paleta.py` (`cargar()`, `rgb()`, `srgb()`, `familia_ac()`): 12 entradas de partida
   (plan A B0.4: oliva_oscuro, salvia, hierba_seca, caliza_ocre, caliza_gris_calido, caliza_sombra, terracota,
   cesped_jardin, tierra, arena, mar_orilla, mar_profundo) + "carta de color" (plano con 12 esferas) renderizada para
   que el usuario la valide [U pregunta 15]. Regla: `diffuse_color` o Base Color sin enlazar = media lineal deseada
   (es lo que lee el writer).
8. Congelar el "antes": `_rev/escena_antes_visual.blend` + `renders/ab/_base_antes/` (modo normal y modo AC).

**Dependencias y orden**: 2 el primer día (antes de cualquier regeneración); 1 y 7 en paralelo; 3-6 el segundo
día. **Esencial/extra**: no aplica. **Riesgos**: `camara_segura` solo en el "antes"; tomas por objeto (`CASINO_root`,
`YATE_`) se congelan por loc/tgt, no por regla. **Verificación**: calibración antes = antes (diff 0); `puerta.json`
sobre la escena actual = `ok: true` con 23 fallos de base. **Horas**: 28 h-agente, 2 agentes (infra A/B + medidas;
puerta/presupuesto/ensayo/peticiones), 2 huecos de cola.

---

## 3. Bloque 3 — Paleta, máscara por texel y luz (PRIMERO: máximo impacto por hora desde el coche)

**Objetivo medible** (en 49-54, 55-59 y 01/07/21, modo normal y modo AC): `pct_cesped` (H 95-135, S > 0.45,
V > 0.5) de 40-70 % a < 8 % en piloto (solo jardines/rotondas/copas); `bandas_blancas` = 0 en 07/08; `riqueza` x2
en terreno; 0 % de píxeles "verde" en caras con nz < 0.7 (hierba estirada); en 51 el desmonte muestra >= 3 tonos
(roca, tierra al pie, hierba seca en berma); 0 valores RGB de terreno/roca/teja/vegetación fuera de `paleta.json`
(grep); bytes de texturas en el KN5 de prueba <= 80 MB.

**Cambios técnicos (Blender, ya)**:
1. `paleta.json` aplicada a sus consumidores (`entender_materiales.md` §3.a): `construir_pista.py` l.86, 110-114,
   125-126, 179-181, 262-263, 1169, 1285 (rampa por altura: hierba seca abajo, matorral en el macizo, caliza en
   cumbres); `texturas/generar_texturas.py` l.102-310; `casas_kit_v2.PALETA_FACHADA`/`COL_TEJA` l.87 (8-10 tonos
   Riviera); `roca_lazo._PALETA` l.150-175 y `roca_casino._PALETA` l.98-116 (unificar: hoy el mismo nombre con dos
   valores); `montana_coche_v2._mat_piedra` l.131-158; `vegetacion_kit_v2._PALETA` l.78-152 (copas oliva/salvia).
2. Tiles nuevos PIL seamless en `generar_texturas.py` (misma síntesis espectral, mosaico 3x3 comprobado):
   `hierba_seca_d` (3 m), `matorral_d` (6 m), `caliza_d` (ocre, juntas horizontales, 3 m), `cesped_d` (el actual,
   solo jardines), `teja_d` terracota, `tierra_d` ocre. `hierba_d` deja de ser el tile del terreno. Re-medir medias
   -> `aplicar_texturas.FAMILIAS.ganancia`. Si el usuario autoriza CC0 [U pregunta 3]: `texturas/recolorear_cc0.py`
   (luminancia + tinte de paleta, croma ±15 %, 1024 px) sustituye los 4 del terreno (`rock_06`, `withered_grass`,
   `Ground105`, `aerial_grass_rock`, ~19 MB) y después los demás (13 en total, 49 MB 1K-JPG) con `CREDITS.txt` +
   `LICENSE_CC0.txt`; misma API, orden "PIL primero, CC0 después" sin trabajo doble. Nunca 2K (el writer recorta).
3. `aplicar_texturas.py`: familias `seca`, `matorral`, `cesped`, `caliza` en `FAMILIAS` l.44-65 y `familia_de`
   l.73-101 (`cesped`, `LOEWS_`, `URB_jardin` -> cesped; `roca`/`caliza`/`PPUEBLO_roca`/`MCOCHE_caliza` -> caliza);
   `FAMILIAS['hierba'].proy` FLAT -> BOX; `aplicar_roca()` l.359-398 manchas de 20 m de ±50 % a ±10 % (es el "velo
   de bruma" de 13/19/45) o retirada cuando entre el grupo de caliza (bloque 2.1). Nombrar `MAT_terreno_matorral`
   (no `MAT_matorral`: `color_ac.familia()` lo clasificaría como "pintado").
4. **Máscara por texel**: NUEVO `03_blender/mascara_terreno.py` (python del sistema, tras `preparar_geometria`,
   antes de `construir_pista`): `generar(geom_path, urb_path, out_dir, px=2048, seed, veg_plan=None) -> {'mask',
   'base', 'ao', 'stats'}`. Lee `geometria_3d.json` (z, mar, `mascara_roca`, cumbres, muestras, `extras['capas']`
   cuando exista) + `urbanismo.json` (solares, calles) y escribe `texturas/terreno_mask.png` RGBA 2048 (R matorral,
   G hierba seca, B tierra, A roca; suma = 1 ± 0.02 en el 99 % de texeles; bordes con ruido de 10-30 m, nunca por
   celda), `texturas/terreno_ao.png` (cavidad + horizonte 8 direcciones + hillshade suave) y `texturas/terreno_base.png`
   (paleta por canal x parches de pradera x AO x "sombra de bosque" bajo las masas del plan de vegetación cuando
   exista). Reglas: A donde pendiente suavizada > 0.70-0.84 (35-40 grados) o `mascara_roca` > 0.5 o `_corte`; B en
   banda de 6-10 m al pie de cada A, bermas y a < 8 m del borde en `sec == dirt`; G en llanos (< 0.35) a < 60 m de
   la pista y z < 60; R en el resto; césped NO (jardines con material propio). QA `renders/qa/terreno_mask.png`.
   Un solo sitio de verdad para los umbrales: los lee de `terreno_montana` (bloque 2.2).
5. `construir_pista.py`: UV planar en TERRENO (`me.uv_layers.new('UVMap')`, u = (x-x0)/(nx·cell), v = (y-y0)/(ny·cell))
   tras l.1448-1468; `mat_terreno()` v2 = Image(mask, UV) + 4 Image tiles (UV x mult_k) + base/AO multiplicando,
   mezcla por canal; se CONSERVA el nodo etiquetado `ROCA_mascara`/`Math.002` (= canal A) porque lo leen los
   revisores, `aplicar_texturas` y `color_ac`; `diffuse_color` = media de hierba seca; marcador `TEXTURIZADO`
   para que `aplicar_terreno()` (l.247-342) no lo pise; custom props `ac_shader = 'ksMultilayer_fresnel_nm'`,
   `ac_samplers = {txDiffuse: terreno_base, txMask: terreno_mask, txDetailR/G/B/A: tiles, txDetailNM: caliza_n}`,
   `ac_props = {multR..A ≈ 2068/tile_m, fresnelC 0.02, fresnelEXP 3, fresnelMaxLevel 0.1, ksSpecular 0.08}`,
   `ac_tex_max = {txMask: 2048, txDiffuse: 2048, detalles: 1024}`; `AGUA_fondo` (l.1485) deja de usar `M_TER`
   (material propio `MAT_fondo_marino`, bloque 6). Material nuevo `MAT_cesped` (paleta `cesped_jardin`, tile 3 m)
   en parterre de la Loews, jardines del casino, plazoletas/patios y rotonda de la palmera: el ÚNICO con GrassFX.
6. Luz (`construir_pista.py` l.1566-1618): sol 34 -> 42 grados con azimut que rasante la ladera de la tierra;
   GTAO 12 -> 20 m; NO niebla de mundo (el director ya lee manchas como bruma); `view_transform Standard` y
   exposición se mantienen (referencia de `color_ac`). `capturas_ab.py` fuerza los mismos ajustes.
7. "Bisel" barato: `shade_smooth` + auto smooth 30-40 grados (atributo `sharp_edge`) en los kits que van en
   `shade_flat` (casas, muros, pretiles, bancales, cívicos, pit, puerto); el writer exporta `corner_normals`.
   NO modificador Bevel (vértices x2) y nunca en el TERRENO. AO: terreno en `terreno_base` (4); rocas y McLaren
   horneadas por objeto (bloque 2.8, [W]); en casas, bisel + sombras + atlas (nunca AO por casa).

**Cambios [W] (bloque X)**: camino (A) `repartir_terreno()` por cara o (B) `_nm` vanilla por texel según el ensayo
del amigo; `_REGLAS` de `color_ac` con `matorral`/`seca`/`cesped`/`caliza`; re-medir `color_ac` UNA vez al final
de la fase (cambiar `diffuse_color` invalida 127 medidas; mientras tanto caen al modelo albedo x luz: peor, no roto).
**Dependencias y orden**: 1 -> 2 -> 3 (agente materiales) || 4 -> 5 (agente máscara/terreno; `construir_pista.py`
es suyo en esta fase) || 6-7 (tercero). El grupo de caliza (bloque 2.1) se enchufa en 5 cuando exista; mientras,
`caliza_d.png`. **CSP**: [E] todo lo de Blender + A o B en el writer; [X] `[SHADER_REPLACEMENT] ksMultilayer_fresnel_nm4`
+ `tilingFixR/G/B/A`, VAO (bloque 9). **Riesgos**: R1 `color_ac` (re-medir una vez); con el camino (A) la rejilla de
4 m sigue dando escalera en AC (mitigar con 2 clases de transición + subdivisión a 2 m en una banda de 20 m junto a
la pista, +40-50 k vértices); máscara 2048 RGBA PNG 4-8 MB + 4 tiles + normal = 20-60 MB de KN5 y 7 samplers por
píxel de terreno: por eso (B) solo con foto del amigo. **Verificación**: A/B `BASE` + set `paleta` (05, 06, 09, 14,
16, 21, 22, 39) en modo normal y AC; `medir_capturas`; histograma de la máscara; `revisar_*` sin cambios;
`kn5_prueba` + `kn5_check` 8/8 + presupuesto; carta de color validada. **Horas**: 44 h-agente, 3 agentes, 2
regeneraciones (paleta+tiles+familias 14; máscara+AO 12; UV+material+MAT_cesped 10; luz/bisel 4; A/B 4).

---

## 4. Bloque 2 — Roca integrada (segundo: 49, 54, postales 1/3/5 y todas las aéreas)

**Objetivo medible**: en 54 y 49 `pared_lisa` < 30 % (hoy ~80 %); en 54 >= 4 juntas de estrato por 10 m de pared;
en 49/33 0 píxeles de "repisa plana" crema bajo la carrocería; en 49/55 el portal llega a los radios (arco >= 11 m);
celdas de tierra con pendiente > 35 grados que llevan roca del 21 % al >= 80 % (sin manchas < 12 celdas); 150-300
afloramientos en cinturones (0 a < 12 m del asfalto, 0 dentro de casas/calles); McLaren con faldón hasta la cintura
(+0.72R) en los flancos, 80-150 pedruscos, grietas, `encaje_mclaren.evaluar()` pista bajo huella 0 y holgura >= 4 m;
roca del lazo con >= 2-3 bancos verticales (8-14 m) con repisa >= 2.5 m visibles en 13/34_general; peñón con
perfil cada 1.5-2 m, 0 planos blancos sin material (19), meseta -25 % de luminancia.

**Cambios técnicos, por orden de impacto desde el coche**:
1. **Material compartido** NUEVO `assets/materiales_roca.py`: `ng_caliza_estratos(nombre='NG_caliza_estratos')`
   (entradas tono_base, tono_junta, periodo_m=3, bump, mojado, fase; salidas Color/Normal/AO) en coordenadas de
   MUNDO (`Geometry.Position`: TUNEL_acantilado y PENON_* no están en el origen); estratos por z con junta hundida,
   bancos de 8-14 m con tono alterno, grano 0.3-1 m, manchas ±10 %, mojado bajo z = 1; `aplicar_a(material, **kw)`
   deja `diffuse_color` = media y el nodo `Math.002`/`ROCA_mascara` intacto. Enchufar en `construir_pista._roca_terreno`
   (sustituye `ROCA_rampa..ROCA_bump` l.252-337), `roca_lazo._mat` l.180-193, `roca_casino._mat`,
   `montana_coche_v2._mat_piedra` (los 9 `MAT_MCOCHE_*`: `hueso` 0.80 -> 0.58, `cristal_pulido` rugosidad 0.26 ->
   0.5; NO renombrar: `_paredes_de_roca` elige por subcadenas `roca`/`caliza`). Con `caliza_d.png` multiplicando para
   que el writer tenga ALGO que exportar hoy. `test_materiales_roca.py` + previews.
2. **Máscara 35-40 grados**: `terreno_montana.construir` l.2261-2274 umbral natural 1.0 -> 0.70-0.84 con ruido,
   apertura 3x3, mínimo 12 celdas, banda "pie de derrubios" 0.5 a 6-10 m bajo cada afloramiento;
   `construir_pista._roca_terreno` l.203-206 `talud` 0.50-0.56 -> 0.70-0.78; sin `ROCA_llano_hierba` donde
   atributo = 1. Petición P1: `color_ac.ROCA_NZ/ROCA_ATR` alineados. Lo edita el agente de terreno (mismo fichero
   que el bloque 1) y SIEMPRE junto con la paleta del bloque 3 (el 28 % de las celdas pasa a candidata: sin paleta
   sería "todo gris").
3. **Desmontes en bancos** (49, 51, 09, 16, 28, 42): `terreno_montana` nueva `bancos_en_cortes(z, _corte, pend,
   hb=6..10, berma=1.5..2.5, fase=ruido 2D 40-80 m)` solo donde `_dsm` y pendiente > 0.75: cuantiza z en bancos con
   cara 80-88 grados y berma; `mascara_roca` 1 en la cara, 0.3-0.5 en la berma (hierba seca). Parche al
   coordinador en `integrar_escena.explanar` l.785-833 (la pared de 25-45 m tras el paddock: mismo perfil en bancos).
4. **McLaren** (49, 33, 32, 55, 59, 01, 02, 13): `montana_mclaren._roca`: faldón de ladera (`_K_FALDA` 0.36 ->
   1.2-1.7 fuera de [-1.3R, 1.5R], talud 30-40 grados, hasta la cintura +0.72R en los flancos y el capó en el morro),
   pared vertical SOLO en el ancho del portal (21 + 2 m); `_bloques` 28 -> 80-150 pedruscos de 1-6 m (densidad
   máxima en los 15 m sobre el agua y en el contacto con el terreno) + 3 bloques de 8-15 m con grieta madre;
   grietas en macizo y faldón (horizontales en juntas + 3-5 verticales por bloque, mismo `_grieta_v`); `_bandas_finas`
   de la carrocería -> surcos de junta con bump (no franjas); `_vegetacion` tipo "junta", `_VEG_TRIS_MAX` 3400 ->
   8000; portal: `_galeria`/`_portal` con arco de sillería de 11-12 m hasta los radios (opción barata). Parámetros
   nuevos de `build()` con valores por defecto = comportamiento actual; parche al coordinador en `zona_tunel` l.2881.
   [U pregunta 5] hundir el coche (`alto_base` 12 -> 19-20): Boolean, encaje, `revisar_tunel` y física otra vez.
   [U pregunta 4] CABO bajo la zaga: landform 'Cabo del McLaren' en `terreno_montana.LANDFORMS` (cordal 300-350 m
   desde el Espolón del coche bajo la zaga, costa anulada en su huella como el peñón l.1215-1229, `mascara_roca` 1
   en la cresta, acantilado al mar en la punta): es lo único que quita el "islote" de 01/02/13/59; mueve la costa a
   150-250 m del puerto (medir contra `PUERTO_dique` y la rotonda s 300-400). Si sí, va con el bloque 1 (mismo fichero).
5. **Afloramientos semienterrados** (51, 52, 50 fondo, 07, 21): NUEVO `assets/afloramiento_kit.py`:
   `build_afloramiento(parent, largo=8..40, alto=2..8, bancos, seed) -> 'AFLOR_losa'` (2-4 bancos, cornisa, pie en
   talud, grupo de caliza, 300-900 tris), `build_pedrusco(parent, r, seed)` (reusa `montana_coche_v2._pedrusco`),
   `build_cinturon(parent, polilinea, n, seed)` (una malla por cinturón); `test_afloramiento_kit.py` + previews.
   Zona `zona_afloramientos` (parche al coordinador, tras `zona_tierra`): candidatos con `pendiente_terreno` 0.5-1.0
   siguiendo la curva de nivel (rotación por gradiente), base 1-2 m bajo el terreno, 150-300 piezas en cinturones,
   3-6 pedruscos al pie, matas en la repisa; exclusiones `_sitio_lejos_pista` (>= 12 m), `_libre`, `zonas_excluidas`,
   rocas de los 3 generadores, Loews, senderos. Alta de `AFLOR_` en `asentar_objetos.SOPORTE_PREF`/`ASENTAR_NO`,
   `revisar_flotantes.EXENTOS`, `despeje_final.DESPEJE_PROP`, `nada_en_pista` (no permitido: deben estar lejos).
   Presupuesto 300 x 600 = 180 k tris.
6. **Roca del lazo** (13, 34, 45, 15, 57; desde 54 solo cambia el material): `roca_lazo._bancos_naturales(M, G, seed)`
   tras l.3481-3490: cuantización MONÓTONA (solo resta, `M' <= M`) en bancos de 8-14 m con fase por ruido 2D de
   40-80 m, cara 80-88 grados, repisa 2.5-6 m, restringida a `o > o_b + 8` y fuera de rasgos dilatados 6-10 m; 2-3
   espolones (`_Macizo.domo` a 3-4, b 0.6-0.9) en el lado N/NE; `_poblar`: pinos parasol en repisas nz > 0.9 y
   ancho >= 3 m, filtro de normal vertical para las matas (no más "matas en la pared" de 11/15/20/38); torre/fortín
   opcional de `italiano_kit.build_torre_costera` [U pregunta 9]. Es el H7 del registro (ya se intentó ridged
   isótropo y represaba cuencas): comprobar `n2['celdas_rellenas']` y TODOS los `checks` en ok. Fase 4.
7. **Peñón del casino** (19, 20, 36, 10): `roca_casino._perfil` l.1781-1786 de 3 cotas por banco a cada 1.5-2 m
   (27 k -> ~80 k tris), `estrato()` con labio 1.5-3 m, `textura()` con ruido 2-5 m; meseta `MAT_PPUEBLO_plaza/
   _borde/MAT_PENON_muelle` a familia piedra y -25 % de luminancia (la "nieve" de 36); pinos en labios anchos;
   localizar el "plano blanco" de la 19 con `test_roca_casino.py`; la cala del casino con escollera (bloque 6). Fase 4.
8. **Horneado por objeto** [W] NUEVO `hornear_rocas.py` (Cycles por la cola, tras `aplicar_texturas`): Smart UV
   Project (ángulo 45, margen 0.004, excepción a "sin bpy.ops" [U pregunta 14]) + bake Diffuse x AO (+ Normal
   tangente) de `TUNEL_acantilado`, `PENON_puente_roca`, `PENON_roca` a 2048/2048/1024; material `MAT_ROCA_<obj>`
   con la imagen en Base Color, `diffuse_color` blanco, `ac_shader = 'ksPerPixelNM'`, `ac_raw = 1`, `ac_tex_max =
   2048`; idempotente (marcador `HORNEADO`); imágenes en `texturas/horneadas/`. Solo 3 objetos (10-30 min cada
   uno en CPU); hasta W el bake sirve para las capturas y el A/B; AO en los huecos del McLaren viene de aquí (vanilla)
   o de VAO (CSP).

**Dependencias y orden**: 1 || bloque 3 (mismo contrato de máscara) -> 2 (agente terreno, tras 1a/1b del bloque 1)
-> 3 (terreno) || 4 (McLaren: fichero propio) || 5 (kit; la zona la integra el coordinador sobre el relieve de la
fase 2) -> 6 || 7 (fase 4) -> 8 (al final, geometría estable). `encaje_mclaren.evaluar()` tras 4; `urbanismo.py`
tras 4 si crecen `zonas_excluidas` [U pregunta 13]. **CSP**: [E] todo; [X] VAO. **[W]**: P1, P2 (`TEX_SIZE` 1024
roca/asfalto/estuco), P3 (imagen tal cual por material/objeto). **Riesgos**: cadena Boolean del McLaren (probar seeds
0/3/7/11 con `test_montana_mclaren`, MANIFOLD, red de seguridad "sin grietas"); "pista bajo huella" en s 718-728
(holgura 5.6 m, al límite); H7 (solo restar); tris +0.3-0.5 M (lazo +20-40 %, peñón x3, afloramientos 180 k);
prefijo `AFLOR_` sin alta en inspectores = borrado o hundido; pieza a < w/2+6.75 m del borde = "visible no físico"
(regla >= 12 m). **Verificación**: A/B `BASE` + set `roca` (02, 13, 17, 19, 20, 32, 33, 33b, 34_general, 36_general,
45, 46) + recortes del borde roca/hierba en 07/08/14/22; `medir_capturas` (`pared_lisa`, repisa 0 px);
`test_montana_mclaren` TEST_OK, `encaje_mclaren`, `revisar_tunel`, `test_roca_lazo`/`test_roca_casino` checks ok,
`asentar.json`, `nada_en_pista` 0 de rocas. **Horas**: 78 h-agente (material 8; máscara 4; bancos 8 + 3 coord;
McLaren 16 + 6 si cabo; afloramientos 12 + 4 coord; lazo 14; casino 6; hornear 8 [W]); 3 agentes en las fases 1-2
(material; McLaren; kit) y 2 en la fase 4 (lazo; casino); 3 regeneraciones.

---

## 5. Bloque 1 — Relieve (lo que se ve desde el coche primero; macizo lejano y erosión después)

**Objetivo medible** (numpy sobre `geometria_3d.json`, nuevo `_rev/medir_relieve.py`): tramo de tierra (s 1430-2440)
a 25 m del borde "pared > +8 m en un lado Y caída < -8 m en el otro" del 5 % al >= 40 % (a 50 m: 22 % -> >= 60 %);
`pct_pista_con_pared_roca` 29.7 % -> >= 50 % en tierra; en 51 la silueta del terreno a la derecha sube > 12 grados
sobre el horizonte de la cámara; macizo tras `pueblo_subida_ladera`: terreno a 120 m del borde >= 110 m de media
(hoy 83) sin bajar `coche_120m_pct_ge_90`; orilla con z > 10 m del 7.5 % al >= 25 % en los tramos elegidos (lado +1
de s 170-402 y 616-820, lado -1 de la recta 2770-2976, costa N/NE), 0 % de cambio a < 15 m de la pista; en 56 la
bahía ocupa >= 25 % del cuadro sin árboles/pacas a < 40 m; invariantes: `celdas_invaden_pista` 0, `hierba_asfalto`
0, fosos <= 1.5, costuras < 0.6, `loews_ref_dz_max` 0.000, `pct_natural_gt_100` <= 5 % fuera del macizo trasero,
urbanismo 0 fallos y >= 190 casas, `encaje_mclaren` ok, hoyos visibles de `revisar_fisica_ac` <= 190.

**Cambios técnicos** (todos en `terreno_montana.py` salvo donde se indica; UN agente, el fichero no se reparte;
cada paso con `python preparar_geometria.py` a un QA_DIR de prueba + `python urbanismo.py` ANTES de gastar una
regeneración de Blender; `assets/_geom_snapshot_terreno.json` actualizado primero):
1. **Tierra tallada** (1a, fase 1): `peso` del tirón `_idw_pull` l.1083 0.5 en s 1430-2440; `techo_desmonte_c1(z0,
   dedge0, pend)` l.720-724/1297 con `pend` como ARRAY (1.8-2.0 en el lado interior de cada curva por signo de
   `_kap[g_near]`, 1.15 en el resto); `s_fl` por celda l.1306-1310 1.2-1.5 en el lado exterior con berma llana
   `d_llano` 6-8 m (arcén + pacas + cierre invisible a w/2+6.75: obligatoria o `cierre_ac` adelanta el muro y el coche
   "choca con el aire"). NO tocar `MAXG`; controles de rasante <= 9-10 % a ±40 m de los apex C18-19/C26 en
   `preparar_geometria.py` l.386-392 (parche al coordinador) [U pregunta 6].
2. **Berma + bancales + costillas tras la última terraza** (1a, fase 1; 50, 05, 06, 39): `techo_tras_terraza`
   l.731-739 y l.1458-1461 con berma de 15-25 m entre el patio y el arranque de la cara; bancales también en
   `w_coche` (quitar la exclusión `w_tope` l.1460 solo si `checks['coche_120m_*']` no baja); `BANCO_H` 16 -> 11-12,
   `BANCO_A` 1.6 -> 2.5; costillas l.1812-1823 tope 2 -> 4-6 m en caras > 20 m. Fosos <= 1.5 y costuras < 0.6 deben
   seguir. Va ANTES del macizo (si no, el tajo de cantera crece).
3. **Macizo trasero** (1b, fase 2; 05, 39, 01, 21, 56): `LANDFORMS` l.135-175 'Espolón del coche' h 150 -> 190-220,
   `s_foot` 0.47 -> 0.65-0.8, `p` 1.3 -> 1.6; 'espolón SO' +40; 'Monte Porto Corsa' 220 -> 260-300 (real ~250-280
   tras limitadores); ridged l.394 `4 + 24·clip` -> `6 + 40·clip(M/250)`; limitador por celda (sustituir la llamada
   l.1123 por `limitar_pendiente_mascara` dos veces: 0.8 a < 150 m de la pista, 1.3-1.6 en el macizo trasero y en las
   crestas `M > 0.7·max(M)`). Riesgo B11 (McLaren más enterrado): `encaje_mclaren.evaluar()` y repetir
   `test_montana_mclaren` con la geometría nueva. La rejilla NO cambia de extensión ni de `cell` (Loews `.npz`).
4. **Acantilados Amalfi selectivos** (1c, fase 2; 49 izq, 52, 55, 14, 22, 16): solo en los 4 tramos por máscara
   `_acant` ampliada: `r_prot` l.978 `30 + 1.7·(z-4)` -> `20 + 0.8·(z-4)`, `pend` de costa 0.6 -> 2.5-4.0, topes F-07
   (`_wb` l.1203-1206) y `_pm` (l.1210-1211) relajados ahí, J1 l.1115-1120 170 -> 60 m, costillas `_wcf` l.1829-1831
   a todo `acantilado & _acant`, `s_fl` por celda 1.5-3.0 en el lado del mar con berma 6-8 m. Nunca a < 25 m del
   asfalto, nunca Loews < 90 m, peñón r < 1.9, viaducto < 20 m, McLaren + 25 m. `construir_pista._pretil` pie
   `min(ze-2.5, zt-1.5)` debe seguir apoyando (rayos como en el registro v3 pista N1).
5. **Cámaras postal + despeje de vista**: tomas 55-59 (bloque 0); `zona_tierra` l.1711-1757 y `pacas_tierra`: nada a
   < 40 m en el cono de la postal 56 (s 1840-1900 lado +1) (parche al coordinador).
6. **Capas para la máscara**: en l.2244-2298 sacar `extras['capas']` = {matorral, hierba_seca, tierra, roca} por celda
   (pendiente, z, `dist_mar`, `dedge0`, `acantilado`, `desmonte`, sectores, cumbres); `preparar_geometria.py`
   l.539-541 las escribe en `geometria_3d.json` (parche). `mascara_roca` se mantiene.
7. **Erosión hidráulica NumPy** (1d, fase 4, OPCIONAL: solo aéreas y 56): NUEVO `03_blender/erosion.py` (numpy +
   scipy.ndimage; método de rejilla de dandrino a 2 m con `_zoom_a`, reposo térmico por material con `mascara_roca`,
   remuestreo a 4 m; `erosionar(z, cell, w_eros, roca, iters=250, semilla=42, res_mult=2) -> (z2, delta, caudal)`;
   6-8 s medidos a 460x450). Inserción en `construir()` entre l.1127 y l.1135 (ANTES de la costa y de las reglas
   duras) con `w_eros` = las máscaras de `entender_terreno.md` §6 (dedge 30 -> 80 m, viaducto, Loews 90 m, McLaren,
   peñón r 1.9, mar, pit 150 m); barrancos N1 l.1135-1161 con `_dg` x0.4-0.5; depósito limitado en la vega/orilla
   (`np.minimum` con la z previa a < 40 m del mar); `delta` fino a `extras['erosion_detalle']` (canal normal de
   detalle [W]). Determinista; QA hillshade antes/después. Nunca Hydra.
8. QA: `checks` nuevos `pared_y_caida_25m_pct`, `orilla_z10_pct_tramos`, `erosion_corredor_dz_max` (= 0.000);
   `qa_figuras` añade `terreno_capas.png` y, si hay erosión, `terreno_erosion_antes_despues.png`.

**Dependencias y orden**: 1 -> 2 (fase 1, en paralelo con el bloque 3: ficheros distintos) -> 3 -> 4 -> 6 (fase 2)
-> 5 -> 7 (fase 4, con todo estable). Tras cada regeneración: `revisar_urbanismo` 0 nuevos, `encaje_mclaren`, A/B.
Bloque 5.1 (escarpa de muros), 7.3 (bancales tallados), 6.4 (dragado del puerto) y 2.2/2.3 tocan `terreno_montana`
o nodos del TERRENO: mismo agente. **CSP**: todo esencial (geometría). Aviso [W]: el TERRENO no proyecta sombras en
AC (`GROUND_PREFIXES`): un macizo que da sombra a la pista en Blender no la dará en AC; el modo AC lo refleja;
decidir si `1GRASS_terreno` pasa a `castShadows = 1` (coste FPS) en X. **Riesgos**: tajo de cantera tras las
terrazas (por eso 2 antes que 3); pretiles con pie al aire; caídas en la escapatoria (`cierre_ac` cierra antes de
cantos > 0.4 m); más pacas y coches/cámaras quitados por desnivel (contar en `asentar.json`, `integrar_escena.log`);
senderos CIMA/ERMITA se replanifican solos (A*: comprobar `sendero_volado`); urbanismo puede perder/ganar casas
(`huecos`); cámaras aéreas congeladas dentro del macizo nuevo (toma nueva). **Verificación**: `checks`,
`terreno_perfil.png` (±40 m), `medir_relieve.py`, A/B `BASE` + set `relieve` (05, 07, 08, 09, 14, 16, 21, 22, 39, 42)
con variante "sin sombras de terreno". **Horas**: 48 h-agente (1a 8; berma 6; macizo 10; acantilados 10; postales/
despeje 2; capas 4; erosión 8 opcional) + 6 h de coordinador; 1 agente serial, 3-4 regeneraciones.

---

## 6. Bloque 5 — Pueblo (50 es la vista de piloto más rota; 40, 05, 06, 39)

**Objetivo medible**: en 50 (lado derecho, terrazas 1-2) >= 8 fachadas visibles donde hoy hay 0; "muros-aleta" = 0
(coronación de cada `CAMINO_muro` sigue `z_top` del JSON y el terreno a < 2.5 m del muro queda a `z_top-0.1` /
`z_base+0.1`: `_rev/medir_muros.py` con rayos); huecos de fila 515 m -> < 200 m; casas >= 200 (hoy 193);
`pueblo_subida_ladera` >= 60 % de frente edificado en terrazas 1-2 (hoy ~30 %); 0 césped entre casas y delante de
fachadas en 06/50 (aceras y patios como losas); `urbanismo.py` 0 fallos; `revisar_urbanismo` casa_casa/casa_muro/
casa_calle 0 y los 4 fallos actuales del pueblo (CASAS_casa.066 + CAMINO_muro.132, .146 flotante, 2 losa_hierba)
resueltos; 40 deja de ser "muro ciego"; <= 5000 tris por casa.

**Cambios técnicos**:
1. **Escarpa + muros con altura por vértice** (5a, fase 2; quita las aletas; solo escena + asentar): `urbanismo_escena.
   muro3d` l.171-191 -> `muro_rampa_sillares` l.215-281 (piezas de 4 m, coronación = `z_top` del JSON) para los
   muros del plan; pasada `escarpar_muros(T, muros)` sobre nodos del TERRENO a < 2.5 m del muro (lado alto `z_top-0.1`,
   lado bajo `z_base+0.1`, respeta `_proteger_pista`, tope ±2.5 m, nunca a < 6 m del asfalto) como
   `garantia_losas_terreno` en `asentar_objetos.py` l.680 (parche al coordinador); sube el atributo `roca` solo si
   corta > 2 m. Es el N2/F-06 pendiente del registro. Coordinar con 2.2/3.4 (atributo `roca`, máscara).
2. **Manzanas pegadas** (5b, fase 2; plan + escena + QA el mismo día: el `assert` l.2841 aborta el pipeline):
   `urbanismo.py construir_solares` l.1875-1998 por manzanas de 3-7 casas (`t += a`, sin buffer 1.02 dentro de la
   manzana; hueco 1.5-2.5 m = carruggio/escalera entre manzanas); anchos `[4.5..9]`; plantas 2-7 "no dos vecinas
   iguales"; campos NUEVOS por solar `manzana`, `medianera_izq/der` (solo añadir claves: las leen `construir_pista.
   _BOCAS` y `revisar_urbanismo._polilineas`); fachada en curva: opción B (solape trasero <= 0.6 m con medianeras
   ciegas y QA relajada dentro de la manzana); elementos nuevos `aceras` y `patios` (losas con canto); casas de
   espaldas a la rampa donde `plan['alto']` queda detrás (recupera los 278 rechazos `rampa_alta`); `GAP_RAMPA_ALTO`
   4.0 -> 2.5; `travesia_cada_m` 150 -> 75; `verificar()` l.2529-2531 (`solar_solar` -> intersección de interiores
   > 0.05 m² salvo misma manzana; `huecos` por manzana). Rechazos `terreno` en s 920-1000: los resuelve la berma
   del bloque 1.2 y, si no, `TOL_SOLAR` 0.5 -> 0.7 con zócalo. `urbanismo_escena.casa_var` l.407-413 con
   `laterales=(not med_izq, not med_der)`, retranqueo 1-2 cm de la medianera más baja (z-fighting);
   `poligono('CALLE_acera'/'CALLE_patio')` dados de alta en `asentar_objetos.SOPORTE_PREF/LOSA_PLAN` l.132/1230 y
   `revisar_urbanismo.LOSA_PREF_QA/PROP_NO` l.83/120. Probar siempre con `--salida <scratchpad> --sin-qa` primero.
3. **Plaza del ayuntamiento** (s 1120-1160, causa del `casa_muro` de CASAS_casa.066): exportar su huella a
   `urbanismo_spec.json` como `zonas_reservadas` (coordinador, 2 h).
4. **Suelo urbano desde el coche** (5c, fase 3): farolas cada ~18 m alternas en calles de terraza
   (`calle_kit.build_farola`, ya 1WALL), tramos de adoquín en la calle de servicio (`tipo='servicio_adoquin'`, asfalto
   en los 30 m de cada boca), alcantarilla como geometría (30 tris) cada 25 m en el eje; `build_bolardo` (40 tris)
   SOLO cuando P6 lo haga `1WALL_` (si no, un bolardo entre borde y cierre es "visible no físico").
5. **UVs + atlas de fachadas** (5d, fase 4): `casas_kit_v2._MB.cara/box/pbox` l.223-272 guardan (u, v) (pared
   u = a/esc, v = z/esc; tejado por faldón) y `to_object` l.291-302 crea `uv_layers`; material `MAT_CASAS_atlas_<tono>`
   con Image Texture (el writer ya lee `uv_layers[0]`), excluido de `aplicar_texturas.familia_de` l.98-99 y de
   `mejorar_materiales.PREFIJOS` l.24; atlas 2048 PIL procedural (`assets/atlas_fachadas.py`: 8-10 tonos Riviera con
   humedad en la base, zócalo, cornisa, contraventanas verde/azul/marrón, persiana, cartel genérico sin marcas) o
   CC0 `white_stucco` + `clay_roof_tiles_03` + `PavingStones150` si hay permiso. Llega a AC tintado a 512 (P2 para
   1024; P3 para "tal cual"). Macetas y ropa tendida como GEOMETRÍA opaca (`macetas=0.3`, `build_tendedero` copiando
   `build_guirnalda` entre balcones enfrentados a < 6 m, nombre `DECO_tendedero`, no `CALLE_`) hasta que W admita alfa.
6. **Soportales, iglesia con cúpula, torreones** (5e, fase 4): `params['soportal']` (planta baja retranqueada 2.5 m
   con arcos; los pilares siguen en y = 0: colisión intacta); `edificios_civicos_v2.build_iglesia` (cúpula + campanile,
   <= 12 k tris) con solar de 2 anchos reservado en `construir_plaza` l.1832-1871 (una plaza por terraza, no por
   sector); torreón +1 planta en la casa de cabecera de manzana; chimeneas-escape x1.5-2 (bloque 8). Convenciones
   intocables: `CASAS_casa`, fachada +Y en y = 0 (`max(ys) <= 2`, `min(ys) <= -3`), hijo `CASAS_zocalo`, huella por
   vértices z < 0.6, pivote en el centro de la fachada.

**Dependencias y orden**: 1 (escena) || 2 (plan) -> 3 -> 4 -> 5 -> 6. Bloque 1.2 (berma) antes de juzgar 50. Si el
bloque 1 cambia el relieve, el plan se regenera solo; el spec (21/6/0.5) no cambia. **CSP**: todo esencial; extra =
luces de farolas y ventanas de noche (bloque 9). **Riesgos**: `revisar_urbanismo.casa_casa` tolera 0.3 m (dos
medianeras con zócalo + pilastra suman 0.24: pasa; con `laterales=False` 0); escarpa cerca de la pista -> hoyos
visibles de `revisar_fisica_ac` (nunca a < 6 m); presupuesto (medianeras ahorran 400-800 tris/casa, soportales y
macetas gastan); `exportar_ac` descarta casas con `max(ys) > 2` (los soportales no mueven la fachada: ok).
**Verificación**: `urbanismo.log` (QA, casas, huecos), `urbanismo_informe.json` 0, `medir_muros.py`, `asentar.json`
casas flotantes/enterradas 0, A/B `BASE` + set `pueblo` (05, 06, 10, 39, 40) + 50 como juez, `medir_capturas`
(`pct_cesped` en 50 lado derecho < 10 %). **Horas**: 60 h-agente (escarpa 10 + 2 coord; manzanas 18; plaza 2; suelo
6; atlas 12; soportales/iglesia 12); 2 agentes (plan `urbanismo.py` + QA; escena + kits), 3 regeneraciones.

---

## 7. Bloque 4 — Vegetación (siluetas a 20-120 m: 50, 51, 52; masas en laderas: 01, 21, 07)

**Objetivo medible**: `siluetas_20_120` x3 en 50/51/52 (hoy ~1 árbol cada 19 m, masas de 4-8); dosel continuo en
51/52 >= 40 % de la ladera sobre el horizonte de la cámara (hoy < 10 %); 0 piruletas (ninguna copa convexa lisa
sobre palo); >= 70 % de los árboles con otro a < 6 m; >= 30 % del total por encima de 80 m (hoy 0 %); árboles
quitados por `despeje_final`/asentar por pasada 140 -> < 20; vegetación en el KN5 <= 0.9 M tris (hoy 1.74 M) con
6-9 k árboles + 15-20 k matas; determinismo: dos regeneraciones con el mismo JSON dan los mismos árboles.

**Cambios técnicos**:
1. **Plan por máscaras** (4a, puede empezar en la fase 1 con el terreno actual; se regenera en 10 s): NUEVO
   `03_blender/vegetacion.py` (python del sistema, como `urbanismo.py`): lee `geometria_3d.json` + `urbanismo.json`
   (+ `terreno_mask.png` y `bancales_spec.json` cuando existan; huellas de rocas/senderos de `renders/qa/huellas.json`)
   y escribe `vegetacion_plan.json` [{especie, variante, x, y, z, rot, escala_xy, escala_z, tono, masa_id, lod}] +
   `renders/qa/vegetacion_mapa.png`. API: `planificar(geom, urb, seed, cfg)`, `zonas(geom)`, `masas(zona, especie,
   radio_poisson, claros)`. Hábitats: pinar en crestas/collados 60-180 m, encinar en umbrías > 25 grados, olivar
   20-90 m junto al pueblo (bancales), cipreses en caminos/ermita/cementerio, palmeras < 20 m junto a mar/paseo/
   casino, adelfas y arbustos con flor en bordes de calle y jardines, matorral > 30 grados y bajo las masas, nada donde
   `mascara_roca` > 0.6 salvo pinos en repisas; disco de Poisson (3-5 m pinar, 7-9 m olivar) por semillas + claros
   explícitos; densidad extra en la banda 20-120 m de las 6 cámaras de piloto y las 5 postales; exclusiones = las de
   los inspectores (pista + 12 m, calles, plazas, edificios, caminos, bancales, rocas, Loews, `zonas_excluidas`).
   Sustituye a `zona_montana` l.2223-2318, `zona_tierra` l.1711-1724 (árboles) y `zona_casino` l.2097-2119 (jardines),
   que pasan a `zona_vegetacion_plan` = clones del plan (parche al coordinador); `enriquecer_vegetacion` deja de
   aleatorizar (el tono viene del plan). El MISMO plan alimenta `trees.txt`.
2. **Kit v3** (4b, fase 3): NUEVO `assets/vegetacion_kit_v3.py` (misma API que v2: `build_pino(parent, alto, seed,
   variante, sin_alfa=True)` -> `VEG_pino` con `ob["VEG_variante"]`, pivote en la base): copas en 2-4 casquetes
   cóncavos de borde ondulado (pino parasol de la película: plana, gruesa, huecos por donde pasa el cielo), ramas que
   asoman, tronco x2 de 7 lados, escala NO uniforme; alturas exageradas (pinos 16-24 m, cipreses 10-16, palmeras
   12-20, olivos 5-7 con tronco grueso, encinas 9-12); tono por instancia vía 3 materiales por especie
   (`MAT_VEG_<clave>_a/b/c`: es lo único que el writer exporta); modo `sin_alfa=True` (60-120 tris/árbol, 30-50/
   arbusto) = ESENCIAL hoy; modo con 4-8 tarjetas de hojas con alfa (150-250 tris, UV, `MAT_VEGC_<especie>` con
   Image RGBA, `ac_shader = 'ksTree'` o `ksPerPixelAT`, `ac_alpha_test = 1`, `ac_cast_shadows = 1`) preparado pero
   apagado hasta W. `assets/render_impostores_veg.py` (bpy.ops.render permitido): atlas de nuestras propias piezas,
   nunca árboles fotográficos. `test_vegetacion_kit_v3.py` con presupuesto (<= 250 tris/árbol, <= 80/arbusto) y
   previews. `build_library` l.255-311 -> v3 vía `assets/v2_aprobados.txt`/`load_mod` con sufijo (coordinador).
3. **Suelo bajo las masas**: oscurecer `terreno_base` bajo las masas del plan (-20 % en un radio 1.2 x copa;
   `mascara_terreno.py` lee `vegetacion_plan.json`) y sotobosque de arbustos v3 (80 tris) dentro de cada masa: es lo
   que convierte "árboles puestos" en "monte". `asentar_objetos.copa_calzada` con la anchura real de la copa;
   `revisar_invasores.REGLAS` radio por especie.
4. **[W] writer**: `ksTree`/`ksPerPixelAT` + `alphaTested 1` + `ksAlphaRef 0.5` + PNG RGBA con bleed + `castShadows 1`
   para `VEG_` con alfa + troceo DECO por celdas de 200 m + `lodIn/lodOut` (tarjetas `lodOut 150`, billboard `lodIn 150`).
5. **TreeFX [X], último**: NUEVO `03_blender/exportar_trees_txt.py` (python del sistema): `vegetacion_plan.json` ->
   `extension/trees/trees.txt` con `configure:` por masa (`size/width/angle/color/brightness variance`, `seed`) y
   `tree: <especie>.bin; pos = x_b, z_b, -y_b` (signo del ángulo a validar con 3 árboles); FBX por especie con 3 LOD
   (`assets/exportar_fbx_veg.py` con `bpy.ops.export_scene.fbx` [U pregunta 14] o `PORTO_FBX=1`); `.bin` SOLO con el
   tree converter de Content Manager en el PC del amigo; `[TREES] LIST_0` + `SURFACE_MATERIALS` + `[SHADER_REPLACEMENT]
   MATERIALS = MAT_VEG_?, IS_VISIBLE = 0` con `ACTIVE = 0` hasta verificar (P8). PRIMERO 3 árboles de prueba
   (meta, casino, cima) en el zip de ensayo; con CSP < 0.1.79 nunca `HIDE`.

**Dependencias y orden**: 1 (fase 1) || 2 (fase 3) -> 3 (tras bloque 3) -> integración (coordinador, fase 3) -> 5
(fase X/9). Bloque 1 ANTES de congelar el plan (las máscaras de pendiente cambian) o re-ejecutar después (10 s).
**CSP**: [E] plan + v3 sin alfa (+ alfa test con W); [X] TreeFX, viento, `ENABLE_TREES_LIGHTING`. **Riesgos**:
densificar x3 con mallas v2 (400-900 tris) = 5 M tris: PROHIBIDO sin v3; sin P4 las hojas con alfa saldrían como
cuadrados verdes opacos (por eso se promueve `sin_alfa`); "cartón" a 1.4 m (primeros 20-30 m de pista siempre con
copas opacas); el bosque cambiaba con cada `Random(42)` consumido: el plan JSON lo fija. **Verificación**:
`vegetacion_mapa.png`; `asentar.json['por_familia']` y `arboles_quitados`; tris por familia (`kn5_presupuesto`);
A/B `BASE` + set `vegetacion` (01, 07, 10, 21, 34_general) en modo normal y AC (sin sombras de vegetación: lo que
verá el amigo HOY); coordenadas de los 3 árboles de prueba contra `pos_kn5` de `resumen_writer_opt.json`.
**Horas**: 50 h-agente (plan 14; kit v3 + test 16; impostores 6; suelo/sotobosque 4; coordinador 4; trees.txt + FBX
6 [X]); 2 agentes (plan; kit) + coordinador; 2 regeneraciones.

---

## 8. Bloque 6 — Agua y costa (54, 49, 55, 56, 57, 59; aéreas 01, 14, 16, 22)

**Objetivo medible**: en 54/57 el agua muestra >= 3 bandas de tono entre orilla y horizonte (hue por columnas);
roughness 0.04 -> 0.08 (54 deslumbra); borde tierra/mar sin escalones de 4 m en 14/22 (franja `COSTA_orilla` en el
100 % de la isolínea `coastF = 0.5` con pendiente < 35 %); 0 "banda blanquecina" de playa (16); dique con >= 600
bloques visibles; bahía con >= 10 veleros con velas izadas; marina con >= 7 esloras y >= 55 barcos; la cala del
casino deja de ser una losa blanca flotante (36); +<= 300 k tris en todo el bloque.

**Cambios técnicos** (detalle en `entender_agua_publico_capturas.md` §10):
1. **Batimetría** (6a, fase 2; no toca terreno): NUEVO `03_blender/generar_mar.py` (python del sistema, tras
   `preparar_geometria`): `prof = max(0, -z)`, `d_costa = EDT(mar)·4` -> `texturas/mar_color.png` 1024-2048 sRGB
   (turquesa 0-2 m -> azul profundo > 25 m / > 250 m de la costa, ruido de 60 m, espuma `d_costa < 8`) +
   `texturas/mar_fondo.png` (arena clara). `construir_pista.py` l.1476-1513: `AGUA` = rejilla de 32 m con UV planar,
   `AGUA_lejos` (anillo hasta 9 km, 8 quads, color profundo plano, subdividido contra el z-fighting), `MAT_agua` con
   la imagen en Base Color (base blanco), alpha 0.84, roughness 0.08, bump de olas 40 m + 7 m, `ac_tex_max = 2048`,
   `ac_alpha_in_texture = 1`; `AGUA_fondo` con `MAT_fondo_marino`. `aplicar_texturas.familia_de` ('agua') no duplica
   el bump (marcador). Llega a AC hoy tintada a 512 (5 m/px: suficiente); P2 para 2048; el tintado puede lavar el
   degradado: comprobar en `kn5_prueba` con `leer_kn5_color.py` y pedir P3 para `MAT_agua` si hace falta.
2. **Orilla** (6b, fase 3, tras el relieve final): malla `COSTA_orilla` en `construir_pista.py` tras el TERRENO
   (marching squares sobre `coastF = 0.5` suavizado, franja de 6 m a cada lado, 3 materiales: arena mojada, arena
   clara, espuma; solo donde pendiente < 35 %); `zona_costa()` (parche al coordinador): rocas de orilla
   `vegetacion_kit.build_roca` 2-5 m en grupos de 2-4, hundidas 40 %, caliza del grupo, donde pendiente > 30 % o a
   < 60 m de muelles, unidas por tono en `COSTA_rocas_<tono>`. Alta en `revisar_flotantes.EXENTOS` (referencia
   marina), `eliminar_sumergidos` (exentar `COSTA_`, `AGUA_lejos`), P6 `NO_OBSTACULO` (lungomare s 4930-5200).
3. **Escolleras** (6c, fase 3): NUEVO `assets/escollera_kit.py` `build_bloques_a_lo_largo(parent, puntos, ancho,
   z_agua, seed, capas=2) -> 'ESCOLLERA_bloques'` (superelipsoides 1.2-3 m, 48 tris, 3 tonos, 30 % bajo el agua, una
   malla por tono); usado por `puerto_kit.build_dique(bloques=True)` (hija `PUERTO_dique_bloques`: el loft
   `1ROAD_puerto_dique_malla` sigue siendo la física), `caminos_kit.build_camino(tipo='muelle', bloques=True)`, la cala
   del lazo (`roca_lazo._disenar_cala`) y el espigón/cala del casino (`roca_casino`). `test_escollera_kit.py`.
4. **Flota** (6e, fase 3): `puerto_kit.build_velero(eslora 9-16, velas='izadas', escora)` (2 láminas), `build_yate
   (eslora 14-30, color_franja)`, `yates_kit.build_lancha(n_coches=0, estela=True)`; `zona_puerto` sortea 7 tamaños;
   bahía 10-14 veleros al mismo viento (±15 grados) + 3-4 lanchas; yates VIP 12/12; `color_franja` -> `MAT_PUERTO_
   casco_<HEX>` (<= 6 tonos); nombres únicos (`YATE_*`, `PUERTO_yate.00N`) para animarlos en el bloque 9.
5. **Puerto-llanta** (6d, fase 4, solo aéreo: 01 y toma 60; si sobra tiempo): `puerto_kit.build_buje(r 16-18, club
   náutico, 4 palmeras)`, 5 radios de pantalán cada 40 grados, pestaña = segundo anillo de pretil + 18 farolas, arco
   200 -> 230 grados, bocana de 50 m con 2 balizas; dragado = disco de mar forzado a z -6 de radio `R_DQ + 12` en
   `terreno_montana` (1 línea, agente de terreno).

**Dependencias y orden**: 1 YA (fase 2) -> 3 || 4 (fase 3, kits independientes) -> 2 (tras la costa final del bloque
1) -> 5 (fase 4, opcional). Bloque 2.1 (caliza de las rocas). **CSP**: [E] batimetría por textura, orilla,
escolleras, flota; [X] `[Material_Water] Type = SEA` (ya) + `UseAlphaFromDiffuse = 1` + `DepthAware = 1` +
`[BOUNCED_LIGHT] CAUSTICS = 1` solo con `ACTIVE = 0` hasta ver FPS. **Riesgos**: `revisar_flotantes` hunde rocas de
orilla si no se declaran; bloques de escollera "vistos por detrás" en `revisar_fisica_ac` (son hijos del dique: no
se inspeccionan); `_agua()` < -1.8 para yates (lo resuelve el dragado); ruido de olas de 40 m repetido desde el aire.
**Verificación**: A/B `BASE` + set `agua_costa` (02, 14, 16, 22, 36_general, 46, 47, 47b, 60, 61); log de
`zona_puerto` (barcos colocados/posibles); `revisar_flotantes`; `kn5_check`. **Horas**: 36 h-agente (batimetría 8;
orilla 10 + 3 coord; escollera 8; flota 7) + 10 h de llanta si se hace; 2 agentes; 2 regeneraciones.

---

## 9. Bloque 7 — Público y relleno (52, 59, 53; aéreas 01, 09, 21, 26, 42)

**Objetivo medible**: horizonte con silueta de costa en >= 60 % del ancho de la línea mar/cielo en 49/52/54/56
(anillo de 7-9 cordilleras a 3.2-4.5 km en dos planos + 6-8 lomas a 2.4-2.8 km con pueblecitos-silueta y faro, 200
grados, abierto 160 grados al S/SO: desde 54 y 14 se sigue viendo mar abierto; <= 250 k tris); coches con cara
70-90 -> >= 250 (filas 1 -> >= 10), en 52 y 59 >= 1 aparcamiento o grada visible a < 120 m; bancales "bandeja" 0
(desnivel en `asentar.json['bancales']` <= 0.3 m; 40-80 bancales tallados); torres de cámara sobre losa sin camino
0 (defecto 8 del director); `revisar_fisica_ac` barreras falsas 0; +<= 400 k tris.

**Cambios técnicos**:
1. **Horizonte** (7a, fase 1: independiente, da contexto a todas las vistas que miran al mar, lo más barato y lo más
   visible): `zona_montanas_fondo` l.2486-2533 deja de hacer `return` y pasa a `zona_horizonte` (parche al
   coordinador): `montanas_fondo_v2.build_cordillera(largo 1400-1800, n_picos 5-7, alto 380-520, pie=True, res 0.5)`
   en dos filas (3.2 km verde-azulada, 4.5 km gris-azul) + `build_loma` x 6-8 a 2.4-2.8 km + pueblecitos-silueta
   (cajas crema 30x10x8, 1 material) + faro lejano; prefijo `HORIZ_`; `mejorar_materiales.py` mezcla con el color
   del cielo (0.70,0.84,0.98) al 35-55 % según distancia (perspectiva atmosférica horneada: en AC a pelo no hay
   niebla fiable); `MAT_MONT_*` por `paleta.json`. Alta en `revisar_flotantes.EXENTOS` (`MONT_` -> `HORIZ_`),
   `eliminar_sumergidos` (pie a z -6), P6 (`SIN_SOMBRA_TOKENS`, `NO_OBSTACULO`). [X] opcional `[Material_DistantGeometry]`.
2. **Aparcamientos explanados + torres de cámara** (7b/7d, fase 3): sustituyen el `sitio_ok` de `zona_coches`
   l.2359-2404 (hoy solo 1 sitio): 8-12 losas de grava 30x14 m con `explanar()` + ramal de tierra de acceso con valla
   (`_ramal_camara`/`poner` de `zona_camaras` l.6088-6166 como modelo) en exteriores de curva a 16-30 m del borde,
   2-3 filas de 6, muro de piedra seca en el borde bajo; 2 de ellas en el cono de 52 y de 59; losas en `EDIF_PREF`
   (que `despeje_final` no las trate como prop); `revisar_coches` asienta cada coche (explanar antes de clonar).
   Torres de cámara (`zona_camaras`): SIEMPRE con ramal de tierra o peana fundida en el terreno (`explanar` r 6 +
   talud 1:2), nunca sobre losa-caja; `CAMARA_peana` en `SOPORTE_PREF`. Plaza del palazzo con camino (`zona_paseo_
   mirador`, F-04). `coches_kit_v2`: opciones `bandera` (24 tris), `mirada`, escala 0.92-1.08 en `build_fila_aparcada`;
   `_pub_coche` (carrera_kit_v2 y pit_kit): 6 siluetas, 10 colores, bandera 20 %. Terraza del casino: 10-16
   `yates_kit.build_coche_lujo` + mesas/sombrillas (53/58 lo ven). Petición P9 (unión por material de `COCHE_fila*`).
3. **Bancales tallados** (7c, fase 4; 51, 07, 48): NUEVO `03_blender/bancales_spec.py` (python del sistema, ANTES de
   `preparar_geometria`): elige 6-10 laderas de pradera (pendiente 10-35 %, sin pista a < 40 m, sin solares, sin
   senderos) y escribe polilíneas por curva de nivel cada 1.6-2.2 m -> `terreno_montana.construir` las TALLA (escalón
   real, como las terrazas del pueblo; agente de terreno) -> `zona_bancales` clona `italiano_kit.build_bancal` por
   tramos de 14-20 m con olivos del plan de vegetación (`olivos=False` si el plan los pone). 40-80 bancales con muro
   apoyado en su escalón, no "bandeja".
4. **Después / si sobra tiempo (aéreo)**: villas con piscina (`villa_kit`, 6-10 sobre explanada con acceso), viñedos
   (`italiano_kit.build_vinedo`), carpas de hospitality (`carrera_kit_v2.build_carpa`, 6-8 en el paddock), camping en
   la ladera de tierra (`camping_kit`), 3 torres costeras (`build_torre_costera`) y 2º faro; coches en balcones (tras
   5d). Todos son raíces nuevas: alta en `revisar_flotantes.EXENTOS`, `SOPORTE_PREF`, `despeje_final.EDIF_PREF`,
   `nada_en_pista`, `exportar_ac` (1WALL donde el coche llega), `revisar_fisica_ac.NO_OBSTACULO` [W]. ~24 h.

**Dependencias y orden**: 1 (fase 1, ninguna dependencia) -> 2 (tras bloque 1: explanadas sobre el macizo final)
-> 3 (fase 4, con el agente de terreno) -> 4 (solo tras los bloques 1-6). **CSP**: todo esencial; animación de
dirigible/barcos/rotor en el bloque 9. **Riesgos**: cada familia nueva sin alta en los inspectores acaba borrada,
hundida o contada como barrera falsa (checklist por prefijo en el test de cada kit); explanadas = nodos del TERRENO
-> hoyos y `copa_calzada` (>= 16 m del borde); draw calls de 250 coches x <= 10 slots (P9 o <= 6 slots por coche);
el anillo tapa la línea mar/cielo de 01 (es lo pedido; abertura S/SO obligatoria). **Verificación**: A/B `BASE` +
sets `horizonte` (13, 14, 16, 08, 19, 63), `relleno` (09, 21, 26, 42, 48, 10, 39), `publico` (27_x, 28, 29, 30, 41,
47, 62); logs de `zona_coches`/`zona_puerto`; `asentar.json`; `nada_en_pista`; `revisar_fisica_ac`. **Horas**: 34
h-agente (horizonte 8; aparcamientos + torres 14 + 3 coord; bancales 10) + 24 h si se hace 4; 2 agentes.

---

## 10. Bloque 8 — Carificación (53, 58, 02/29; aéreas 19/20/36)

**Objetivo medible**: en 53 y 58 se cuentan >= 3 elementos "coche" en el casino (estatuas, rejilla, faros);
chimeneas-escape en >= 80 % de las casas visibles en 50/06 (ya existen en `casas_kit_v2` l.709: subir probabilidad y
tamaño x1.5-2, cromo, dobles en >= 5 plantas); monumentos (casino, campanile, ayuntamiento, hotel, pórtico de meta,
faro) un 30 % más grandes SIN fallos de QA nuevos [U pregunta 8]; 0 logotipos de marcas reales (grep).

**Cambios técnicos**: NUEVO `assets/carificacion_kit.py` (`build_chimenea_escape`, `build_estatua_coche(alto=3.5,
pose, seed)` <= 2.5 k tris en pedestal con la caliza del grupo, `build_rejilla_fachada`, `build_faros_fachada`
(relieves de 10-20 cm, <= 400 tris), `build_cartel_generico(texto)` sin marcas) + test + previews; `casino_v2`: 4
estatuas en las esquinas de la meseta + rejilla + faros flanqueando la entrada; `edificios_civicos_v2`
(`build_ayuntamiento`, `build_hotel`, `build_campanile`, `build_iglesia`): `escala_monumento`, `rejilla`, `faros`;
escala en las llamadas del integrador (casino 1.3-1.35 dentro de la elipse 118 x 78 m, campanile 1.4, ayuntamiento
1.3, pórtico 1.2, hotel 1.2, dirigible 48 -> 70 m) con re-explanado (`explanar_edificios` sigue el bbox; la caja
1WALL de `exportar_ac` sale del `bound_box`) y comprobación de `casa_pista`/`casino_contorno`/farolas a >= 2.76 m del
eje; NUNCA la Loews ni la rotonda (8-14 m del casino, intocables). Guía de estilo de 1 página
(`_rev/fase_visual/estilo_carificacion.md`: proporciones, cromo, ojos solo en coches, nada de logos) [U].
**Silueta Topolino del peñón** (`roca_casino._forma`/`F_libre` l.484-566 con el perfil 2D de `penon_topolino.py`
legado solo en el arco que mira al mar -130..40 grados): proyecto propio de 20-30 h con riesgo alto para la bajada
(G3: 1249 m al 11 % con 2 horquillas) y la cala; FUERA de esta fase salvo [U pregunta 9].
**Dependencias**: bloque 2.1 (caliza), 5.6 (kits cívicos), 2.7 (peñón). **CSP**: [E] todo; [X] faros de fachada como
`LIGHT_SERIES` de noche. **Riesgos**: el casino x1.35 puede no caber (bajar a 1.2); tris +60 k. **Verificación**:
previews del kit; `test_roca_casino`, `test_casino_v2`; A/B set `carificacion` (10, 19, 20, 36_general, 53, 58) +
toma nueva `66_penon_desde_mar` (400 m, lente 35) si se hace la silueta. **Horas**: 16 h-agente (kit 8; edificios +
escala 8); 1 agente; 1 hueco; +25 h si Topolino.

---

## 11. Bloque 9 — CSP y ambiente (TODO extra: su efecto en AC a pelo debe ser nulo)

**Objetivo medible**: `ext_config.ini` con `[Material_Water]` (+DepthAware/cáusticas), `[GRASS_FX]` solo
`MAT_cesped`, `[LIGHT_SERIES_*]` + `[MATERIAL_ADJUSTMENT_*]` (farolas paseo/puerto/peñón/casino/guirnaldas/boxes/
ventanas, `CONDITION = NIGHT_SMOOTH`, `CLUSTER_THRESHOLD 6-10`), `[LIGHT_POLLUTION]`, `[WRAP_MESHES_*]` + `[ANIMATED_*]`
(rotor .ksanim en bucle; dirigible y 3-5 barcos tipo "train" con camino oculto), `[DISPLAY_1/2]` (`MODE = CAMERA`,
`CAMERA_0_TARGET = CLOSEST_CAR`), `[TREES]`, `[SHADER_REPLACEMENT]` nm4 + tilingFix y ocultación de árboles; cada
sección con `ACTIVE = 0/1` independiente; en el PC del amigo: luces de noche con Sol y con Pure, rotor girando,
pantalla con cámara, 3 árboles TreeFX, FPS con 12 coches >= los de v1.0.

**Cambios técnicos (Blender, baratos, durante los bloques 5/6/7)**: materiales EXCLUSIVOS por función
(`MAT_farola_luz`, `MAT_casino_luz`, `MAT_guirnalda_luz`, `MAT_pit_luminaria`, `MAT_ventana_luz`, `MAT_faro_luz`)
con bombillas pequeñas y separadas, color "apagado" gris cálido y `ksEmissive = 0` SIEMPRE; `MAT_heli_rotor_N` (un
objeto por material) y objetos `ANIM_heli_rotor`, `ANIM_dirigible`, `ANIM_yate_01..05` con pivote donde giran y
pose creíble si no se mueven (palas en cruz, barcos amarrados); mallas-ruta ocultas `ANIM_ruta_*` (`isRenderable
= 0` [W]); pantallas (`carrera_kit_v2.build_pantalla`): cara frontal con UV 0..1 y `MAT_pantalla_1/2` con Image
1024x576 real (`texturas/pantalla_live.png` PIL: "WGP LIVE", sin marcas; se ve sin CSP), marco con otro material.
Borrador `_rev/fase_visual/ext_config_v1_5.ini` + `_rev/coords_csp.py` (coordenadas KN5 (x, z, -y) de farolas,
cámaras de pantalla y rutas desde el `.blend`) + `_rev/validar_ext_config.py` (secciones, claves conocidas,
materiales citados existen en el KN5 vía `kn5_check --quiet`).
**[W]**: `KEEP_PREFIXES += ANIM_` (P7), `generar_ext_config` con las secciones (P8), `lodIn/lodOut` por malla,
textura real en la pantalla. **VAO** [U pregunta 13]: `acc-bakeryoptix` v22 (1.8 MB) sobre el KN5 final con
`baked_shadow_params.ini` (`BAKE_AS_TREES`, `EXCLUDE_FROM_BAKING` de las mallas invisibles, `TUNNEL_FIX` para el
túnel) -> `porto_corsa.vao-patch` en el zip con README; CPU vale (10-60 min). **Pure/Sol**: ninguna clave de pista
los distingue; prueba visual en el PC del amigo con la palanca `[MATERIAL_ADJUSTMENT_0]` por familias, `ACTIVE = 0`.
**Dependencias**: nombres de materiales de cada kit; `04_export` abierto; CSP confirmado [U pregunta 1].
**Riesgos**: `WRAP_MESHES` sobre malla fusionada no probado; signo de ejes de `PIVOT_POS`; `DepthAware` exige alfa
en el PNG; `HIDE` con CSP viejo = pista sin árboles; FPS no medibles aquí. **Verificación**: `validar_ext_config.py`,
`coords_csp.py` contra `pos_kn5`, pantalla visible en 02/29, lista de comprobación del amigo (`web_csp` §11 +
`web_treefx` §9). **Horas**: 24 h-agente (materiales/nombres 8; pantallas 4; ANIM_ y rutas 4; borrador + coords +
validador 8); 1 agente; + 2-3 rondas del amigo.

---

## 12. Bloque X — Export (lista cerrada para `04_export`; SOLO cuando el equipo del zip v1.1 cierre)

Se entrega como UNA tanda con los 5 KN5 de ensayo del bloque 0 probados por el amigo ANTES del circuito entero.
Mientras `04_export` esté cerrado se prepara como copia `04_export/_writer_v2/` (diff) sin tocar los ficheros vivos
[U pregunta 2 y fecha]. En orden de valor para el jugador:
1. (P3) Shader, props y samplers POR MATERIAL (`escribir_texturas_y_materiales` l.301-339) leídos de `m['ac_shader']`,
   `m['ac_props']`, `m['ac_samplers']`; por defecto lo de hoy. Texturas "tal cual" (`m['ac_raw']`): sin tintar, sin
   reducir a 512, tope `m['ac_tex_max']`; alfa conservado + bleed.
2. (P10 / P3) Terreno: camino (A) `repartir_terreno()` por cara o (B) `ksMultilayer_fresnel_nm` por texel (txMask
   2048 sin tintar: excepción a `TEX_MAX`/`imagen_lineal`) según las fotos del ensayo. (P1) `color_ac.separar_roca_
   terreno` cableado con imagen de caliza mientras tanto; `ROCA_NZ/ROCA_ATR` alineados al bloque 2.
3. Texturas por objeto (atlas horneados de McLaren, lazo, peñón) sin pasar por `calibrar_todos`; tangentes reales
   desde la UV (hoy ficticias, l.448-458) cuando hay `txNormal`/`txDetailNM`.
4. (P4) Alfa test: `ksPerPixelAT`/`ksTree`, `alphaTested = 1`, `ksAlphaRef 0.5`, PNG RGBA con bleed, `castShadows = 1`
   para `VEG_` con alfa, troceo DECO por celdas de 200 m (frustum culling), `lodIn/lodOut` desde `ob['ac_lod']`.
5. (P7, P6) `KEEP_PREFIXES += ANIM_` (nodo propio con pivote), `isRenderable = 0` para `ANIM_ruta_*`; tokens sin
   sombra `MONT_`/`HORIZ_`/`COSTA_`/`ESCOLLERA_`; `1WALL_` nuevos (`CALLE_bolardo`, carpas, muros de villa);
   `revisar_fisica_ac.NO_OBSTACULO` nuevos (COSTA_, HORIZ_, CAMPING_, VILLA_); `GROUND_PREFIXES`: sombra del
   terreno opcional.
6. (P2) `TEX_MAX` 2048 solo para `MAT_agua` y `txMask`; `TEX_SIZE` 1024 para roca/caliza/asfalto/estuco (12.5 -> ~45 MB);
   DDS BC1/BC3 con mipmaps para > 1024 solo si el ensayo (d) muestra que AC no genera mips del PNG.
7. `color_ac._REGLAS` l.309-331 con `matorral`, `seca`, `cesped`, `caliza`; `calibrar_todos` salta materiales con
   `ac_shader` != ksPerPixel; re-medir objetivos/albedos UNA vez al final (`render_ac.py` + `medir_objetivos.py` +
   `medir_albedo.py`).
8. (P5) `kn5_check.py` comprobación 9: shader conocido + samplers/props esperados por shader (`SHADERS = {...}`),
   texturas potencia de 2 y <= 4096, materiales sin uso, UV fuera de 0..1 en atlas, recuento de tris por familia;
   `--quiet` para el validador de ext_config.
9. (P8) `generar_ext_config` con las secciones del bloque 9 desde `03_blender/ext_config_plantilla.ini`, todas con
   `ACTIVE`; `empaquetar.py` copia `extension/trees/`, `.vao-patch`, `CREDITS.txt`, `LICENSE_CC0.txt`, README.
10. (P9) Unión por material de `COCHE_fila*`, `COSTA_rocas`, `PUERTO_dique_bloques`.
Lo que SOLO se valida en el PC del amigo: que el shader multicapa cargue, mipmaps de PNG, alfa test y sombras con
alfa, `lodIn/lodOut`, VAO, TreeFX, luces, displays, FPS con 12 coches (si caen: LOD, agrupar por material,
`ENABLE_TREES_LIGHTING = 0`). **Horas**: 40 h-agente (1-2 agentes en serie sobre los mismos ficheros) + 2 huecos de
cola para `exportar_ac` + 2-3 rondas del amigo. **Riesgo mayor de toda la fase (R4)**: un nombre de shader/sampler
mal -> AC no carga; mitigación = `_nm` vanilla con samplers verificados [V] en `web_multilayer` §6, nunca nm4 en el
KN5, KN5 de ensayo primero, retroceso al zip anterior.

---

## 13. Orden de bloques, duración y paralelismo

Cada fase termina con UNA regeneración completa (`pipeline_escena.sh`, ~3 min de pipeline + ~1 h de cola con los
tests y las capturas) + A/B del `BASE` en modo normal y AC + medidas + puerta; entre regeneraciones todo se prueba
en python del sistema (segundos) y con los tests de kit (previews por la cola, 1 hueco cada uno). Las 57 capturas
solo al cerrar cada fase; el set reducido (12-20 tomas) por bloque.

| Fase | Días | Agentes (cola <= 4 para la fase visual; 2 para el zip) | Bloques y entregable | Zip |
|---|---|---|---|---|
| F0 | 1-2 | 2 | Bloque 0: A/B + modo AC + medidas, pipeline a candidata + puerta + promoción, presupuesto, 5 KN5 de ensayo, peticiones, `paleta.json` + carta de color, "antes" congelado | ensayos para el amigo |
| F1 | 3-6 | 5 | 3 (paleta, tiles, máscara por texel, UV, luz, bisel) + 2.1 (caliza compartida) + 1.1-1.2 (tierra tallada + berma) + 7.1 (horizonte) + 4.1 (plan de vegetación con el terreno actual) | **v1.2 "paleta y fondo"** (si el usuario quiere zips frecuentes) |
| F2 | 7-11 | 5 | 1.3-1.4-1.6 (macizo, acantilados, capas; + cabo si [U4]) + 2.2-2.3 (roca por pendiente, bancos) + 2.4 (McLaren faldón) + 2.5 (afloramientos) + 5.1-5.3 (escarpa, manzanas, plaza) + 6.1 (batimetría) | |
| F3 | 12-16 | 5 | 4.2-4.3 (kit v3, sotobosque, integración) + 6.2-6.4 (orilla, escollera, flota) + 7.2 (aparcamientos, torres) + 5.4 (suelo urbano) + 8 (carificación básica) + 9 materiales exclusivos | **v1.3 "relieve y roca"** |
| F4 | 17-21 | 4 | 2.6 (lazo) + 2.7 (casino) + 5.5-5.6 (atlas, soportales, iglesia) + 7.3 (bancales tallados) + 1.7 (erosión, opcional) + 6.5 (llanta, opcional) + 2.8 hornear + re-medir `color_ac` + 57 capturas finales + hojas de los 9 bloques | |
| FX | cuando abra `04_export`; 5-8 días | 1-2 | Bloque X + ensayo del amigo + circuito completo + bloque 9 (ext_config, VAO, trees.txt) | **v1.4 "superficies"** y **v1.5 "CSP"** |

**Horas-agente**: 0: 28; 3: 44; 2: 78; 1: 54; 5: 60; 4: 50; 6: 36 (+10); 7: 34 (+24); 8: 16 (+25); 9: 24; X: 40;
coordinador (parches a `integrar_escena`/`preparar_geometria`/`construir_pista`/`asentar_objetos`, pipeline,
puerta, promociones, hojas, registro): ~45. **Total ≈ 510 h-agente (± 25 %)**, de las que ~60 son opcionales
(erosión, llanta, villas/camping, Topolino) y ~65 dependen de que `04_export` abra. **Calendario de reloj**: 4
semanas de Blender (F0-F4, ~21 jornadas con 4-5 agentes y 12-15 regeneraciones completas) + 1-2 semanas de export
condicionadas a `04_export` y al bucle con el amigo. Si hay que recortar: F4 entera es prescindible (con F0-F3 el
jugador ya ve el 80 % del cambio). Comparación: plan A 770 h / 5-6 semanas, plan B 460 h / 3-4 semanas, plan C 410 h
/ 3-4 + 1-2.

**Qué puede ir en paralelo y qué no (propietario único por fichero; dos agentes nunca editan el mismo)**:
| Propietario | Ficheros | Fases |
|---|---|---|
| Infra (-> coordinador) | `_rev/*` (tomas, capturas_ab, montaje, medir, puerta, promover, presupuesto, kn5_ensayo, validar_ext_config, coords_csp) | F0, luego el coordinador |
| Terreno (1 agente, SERIAL) | `terreno_montana.py`, `erosion.py`, `bancales_spec.py`, `_rev/medir_relieve.py` (+ 2.2, 2.3, 6.4 dragado, 7.3) | F1-F4 |
| Materiales | `paleta.json/py`, `texturas/generar_texturas.py`, `recolorear_cc0.py`, `aplicar_texturas.py`, `assets/materiales_roca.py`, `hornear_rocas.py`, `mejorar_materiales.py` (horizonte) | F1, F4 |
| Máscara/terreno-material | `mascara_terreno.py`, `construir_pista.py` (solo en F1: UV, `mat_terreno`, `MAT_cesped`, luz, `_roca_terreno` enganche) | F1 |
| Rocas | `assets/montana_mclaren.py` (F2), `assets/afloramiento_kit.py` (F2), `assets/roca_lazo.py` (F4), `assets/roca_casino.py` (F4): hasta 3 agentes a la vez porque son ficheros distintos | F2, F4 |
| Pueblo-plan | `urbanismo.py`, `urbanismo_spec.json` (solo `zonas_reservadas`) | F2 |
| Pueblo-escena/kits | `urbanismo_escena.py`, `casas_kit_v2.py` (o v3), `edificios_civicos_v2.py`, `calle_kit.py`, `casino_v2.py`, `assets/atlas_fachadas.py`, `assets/carificacion_kit.py` | F2-F4 |
| Vegetación | `vegetacion.py`, `assets/vegetacion_kit_v3.py`, `render_impostores_veg.py`, `exportar_trees_txt.py`, `exportar_fbx_veg.py` | F1 (plan), F3, FX |
| Agua/relleno | `generar_mar.py`, `assets/escollera_kit.py`, `puerto_kit.py`, `yates_kit.py`, `coches_kit_v2.py`, `carrera_kit_v2.py`, `italiano_kit.py`, `montanas_fondo_v2.py`, `villa/camping kits`, `ext_config_v1_5.ini` borrador | F1 (horizonte), F2-F4 |
| Coordinador (único) | `integrar_escena.py`, `preparar_geometria.py`, `asentar_objetos.py`, `construir_pista.py` (F2+: AGUA, COSTA_orilla, zonas nuevas), `_rev/pipeline_escena.sh`, `RONDA15_PLAN.md` registro | todas |
| Nadie hasta que abra | `04_export/*` (se prepara `_writer_v2/` como copia; `PETICIONES_04_EXPORT.md`) | FX |

Serializaciones obligatorias: (1) cualquier cambio de `terreno_montana.py` -> `preparar_geometria.py` + `urbanismo.py`
en un QA_DIR de prueba ANTES de regenerar; (2) solo el coordinador lanza `pipeline_escena.sh` (regenera
`porto_corsa.blend`: nunca dos a la vez) y las capturas A/B; (3) 5.2 (manzanas) exige `verificar()` el mismo commit;
(4) 2.2/2.3/5.1/7.3 tocan el terreno o sus nodos: pasan por el agente de terreno o por el coordinador; (5) la
promoción a `escena_rev.blend` solo con `puerta.json ok` y nunca mientras el equipo del zip esté exportando.
Compartidos de solo lectura: `geometria_3d.json`, `urbanismo.json`, `vegetacion_plan.json`, `terreno_mask.png` (los
escribe un único script cada uno, en el orden del pipeline: preparar_geometria -> urbanismo -> mascara_terreno ->
generar_mar -> vegetacion -> construir_pista -> integrar_escena).

---

## 14. Preguntas para el usuario (cortas; con la recomendación del juez; sin respuesta se aplica la recomendación)

1. **¿Tu amigo usa Custom Shaders Patch (CSP) y Content Manager?** ¿Sabe la versión? -> Recomiendo asumir que NO
   hasta que lo confirme: todo lo de CSP (árboles TreeFX, luces de noche, cosas animadas, pantallas, agua con
   cáusticas) se entrega preparado pero apagado, y lo esencial se ve en AC "a pelo".
2. **¿Puede tu amigo cargar 5 ficheros pequeños de prueba y mandar 5 fotos antes del circuito completo?** -> Sí,
   por favor: es la única forma de saber si el terreno con 4 texturas, los árboles con hojas y las texturas grandes
   se ven en su juego. Sin esas fotos usamos el camino seguro (más tosco).
3. **¿Nos dejas descargar texturas libres (CC0, sin atribución obligatoria) de Poly Haven y ambientCG?** Son 13
   ficheros, unos 49 MB. -> Sí; si no, se generan por código (look más "de dibujo", también válido para Pixar).
4. **¿Puede el McLaren tener un "cabo" de tierra detrás que lo una a la montaña, aunque la costa se acerque al
   puerto (150-250 m)?** -> Sí: es lo único que quita el efecto "coche sobre un islote" en la vista aérea y en la
   recta del puerto.
5. **Túnel "por la rueda": ¿vale un portal de piedra grande que llegue hasta los radios (barato, sin tocar la
   física) o quieres que la pista pase por el centro de la llanta (hundir el coche 8 m, rehacer túnel y física)?**
   -> Portal grande ahora; el centro de la llanta solo si tras ver las capturas no convence.
6. **Tramo de tierra: la cuesta ya va al 13-16 %, por encima del 12-15 % que pediste; bajarla haría la cima MÁS
   baja.** ¿Aceptas que no se toque y que el "desnivel" venga del terreno a los lados (pared a un lado, caída al
   otro)? -> Sí.
7. **"Bajada a la horquilla de la fuente": ¿es la rotonda con la fuente y la palmera (Loews, antes del viaducto) o
   la horquilla del tramo de tierra?** -> La rotonda Loews.
8. **Monumentos más grandes: ¿+30 % o +50 %?** -> +30 % (el casino crece dentro de su meseta; la rotonda Loews no se
   toca).
9. **¿Quieres la silueta de Fiat Topolino en el peñón del casino en esta fase?** (20-30 h, riesgo para la carretera
   de bajada que ya funciona) ¿Y una torre o fortín en la roca del lazo? -> Topolino no ahora (ronda aparte con su
   propia prueba); torre sí (barata).
10. **¿Juzgamos las capturas en modo "Blender bonito" o en modo "fiel a lo que verá tu amigo" (sin sombras de
    árboles ni de montaña, materiales como los exporta el juego)?** -> Las dos hojas, pero el "cerrado" de cada
    bloque se decide con el modo fiel.
11. **Tamaño: ¿vale un circuito de hasta 450 MB y un zip de hasta 250 MB?** (hoy 355 / 172) -> Sí con esos topes.
12. **¿Prefieres zips frecuentes (uno en ~1 semana con colores, horizonte y mar; otro con relieve y rocas a las 3
    semanas) o esperar a tenerlo todo?** -> Frecuentes: siempre hay uno jugable y tu amigo puede ir probando.
13. **¿Permiso para descargar `acc-bakeryoptix` (1.8 MB) para las sombras ambientales de CSP?** -> Solo si la
    pregunta 1 es "sí"; al final de la fase.
14. **¿Permiso para dos excepciones a "sin bpy.ops"?** (exportar FBX de árboles para TreeFX y desplegar UV para
    hornear rocas) -> Sí, solo en esos dos scripts.
15. **Validar la "carta de color" (12 esferas) y los 8-10 tonos de fachada antes de propagarlos** (5 minutos al
    cerrar el bloque 0). -> Sí; sin respuesta se usa la propuesta.
16. **¿Cuándo cierra el equipo del zip v1.1?** Hasta entonces `04_export` no se toca y la mitad de las mejoras solo
    se ven en las capturas de Blender. -> Preparar el writer v2 como copia aparte mientras tanto.

---

## 15. Lista de "NO HACER" (con el motivo)

1. **No regenerar `escena_rev.blend` sin puerta de calidad** ni mientras el equipo del zip exporta: es la escena de
   `hacer_zip.sh`; hoy `pipeline_escena.sh` la pisa en cada ejecución (decisión 1).
2. **No tocar `04_export`** hasta que cierre v1.1; todo va a `PETICIONES_04_EXPORT.md` y a `_writer_v2/` (copia).
3. **No usar Hydra** (add-on con contexto OpenGL de la interfaz: no funciona en `--background`, no probado en 5.x,
   no reproducible). Erosión = `erosion.py` NumPy, al final y opcional; nunca gotas a 1 m ni GAN.
4. **No escribir `ksMultilayer_fresnel_nm4` en el KN5** (shader de CSP; samplers de normal no documentados): en el
   KN5 `ksMultilayer_fresnel_nm` vanilla y solo tras el ensayo del amigo; nm4 por `ext_config`.
5. **No empezar por el multicapa en el KN5**: 7 samplers por píxel y 20-60 MB sin poder medir FPS; primero paleta
   + máscara en Blender, el camino al KN5 lo deciden las fotos.
6. **No AO por color de vértice** (el vértice KN5 es pos+normal+uv+tangente); AO en textura (terreno, 3 rocas,
   McLaren) o VAO.
7. **No hornear AO por casa** (216 atlas) ni modificador Bevel en casas o terreno ni subdividir el TERRENO a 2 m en
   toda la rejilla: `cell` es único en todo el pipeline y la Loews está congelada por `.npz`.
8. **No densificar la vegetación con el kit v2** (400-900 tris/árbol = 5 M tris): solo con v3 <= 250 tris.
9. **No bajar la rasante de la tierra (`MAXG`) al 12 %**: la cima bajaría a ~105 m y toca física validada.
10. **No mover el McLaren ni alargar su morro** (pisa la horquilla s 716-888 y los solares): traer el terreno al
    coche (faldón + cabo).
11. **No erosionar antes de fijar tierra/berma/acantilados**: habría que recalibrar con cada cambio de macizo.
12. **No `ksEmissive > 0` en el KN5** (brilla de día en vanilla), **no alpha blend** en árboles/decals, **no `ksGrass`**
    (CSP lo oculta con GrassFX; GrassFX solo sobre `MAT_cesped`).
13. **No animados como KN5 aparte (`MODEL_REPLACEMENT`)**: sin CSP desaparecen. Nodo `ANIM_` en el KN5 principal.
14. **No ocultar los árboles del KN5 (`HIDE`/`IS_VISIBLE = 0`)** antes de ver TreeFX funcionando en el PC del amigo;
    no usar packs `.bin` ni árboles fotográficos de terceros (estilo y licencia ajenos).
15. **No `DepthAware`/cáusticas/luces con sombras/GrassFX activos por defecto**: `ACTIVE = 0` y uno a uno.
16. **No mover cámaras entre el antes y el después** (`camara_segura` solo en el "antes"); si una queda dentro del
    terreno, toma nueva con otro nombre.
17. **No cambiar `view_transform`/exposición de Blender** para que las capturas "queden bonitas", ni niebla de mundo:
    invalida `color_ac` y no cambia nada en AC; la lejanía se hornea en el color del horizonte.
18. **No cambiar `diffuse_color` de materiales medidos sin re-medir `color_ac`** al final (una sola vez, F4).
19. **No tocar la Loews, el corredor de la pista, el viaducto, el peñón a r < 1.9 ni la extensión/`cell` de la
    rejilla**: congelados por el usuario y por la física.
20. **No añadir props a < w/2+6.75 m del borde sin prefijo `1WALL_`** (bolardos, estatuas, rocas de orilla, bloques):
    `revisar_fisica_ac` los marca "visibles no físicos" y el coche los atraviesa.
21. **No crear objetos con prefijo nuevo sin darlo de alta** en `revisar_flotantes.EXENTOS`, `eliminar_sumergidos`,
    `asentar_objetos`, `despeje_final`, `nada_en_pista.PERMITIDOS`, `revisar_fisica_ac.NO_OBSTACULO`: acaban
    borrados, hundidos o contados como barrera falsa.
22. **No "rellenar praderas" con villas, carpas, camping, torres o coches en balcones antes de los bloques 3/1/2/5/4**
    (regla del usuario: primero relieve, integración, paleta y densidad); y nunca como "cajas sueltas en la loma".
23. **No texturas 2K/4K ni PNG de 16 bits**: el writer recorta a 1024/512; cuadruplican descarga y KN5 sin verse.
24. **No renderizar las 57 capturas en cada iteración**: set reducido por bloque; las 57 solo al cerrar cada fase.
25. **No usar Mix Shader ni atributos para nada que deba verse en AC**: lo que pasa al KN5 va como imagen + UV +
    custom props `ac_*`; lo procedural queda para previews.
26. **No escalar la Loews ni la rotonda** con los monumentos; el casino crece dentro de su meseta o no crece.

---

## 16. KPIs resumen (tabla única para el coordinador; "hoy" según los informes del 04/10)

| Bloque | KPI | Hoy | Objetivo | Cómo se mide |
|---|---|---|---|---|
| 0 | diff de píxel antes = antes | - | 0 | `capturas_ab` calibración |
| 0 | `escena_rev.blend` solo por promoción | no | sí | `PROMOCIONES.md` |
| 3 | verde césped en vistas de piloto (modo AC) | 40-70 % | < 8 % | `medir_capturas.pct_cesped` |
| 3 | dientes de sierra / escalera / hierba estirada (07/08/14/22/49) | sí | 0 | `bandas_blancas`, % verde en nz < 0.7 |
| 3 | RGB fuera de `paleta.json` | muchos | 0 | grep |
| 2 | `pared_lisa` en 54/49 | ~80 % | < 30 % | `medir_capturas` |
| 2 | celdas > 35 grados con roca | 21 % | >= 80 % | numpy sobre `geometria_3d.json` |
| 2 | McLaren: repisa plana en 33/17/49 | sí | 0 px | captura A/B |
| 2 | afloramientos / pedruscos | 0 / 124 | 150-300 / 600-900 | log `zona_afloramientos` |
| 2 | lazo: bancos con repisa visibles en 34_general | 0 | >= 2-3 | captura + `roca_lazo` checks |
| 1 | pared Y caída a 25 m en tierra | 5 % | >= 40 % | `medir_relieve.py` |
| 1 | orilla z > 10 m (tramos elegidos) | 7.5 % | >= 25 % | idem |
| 1 | terreno a 120 m tras `pueblo_subida_ladera` | 83 m | >= 110 m | idem |
| 1 | cambio en el corredor / `loews_ref_dz_max` | - | 0.000 | `checks` |
| 5 | fachadas visibles en 50 lado derecho | 0 | >= 8 | captura A/B |
| 5 | muros-aleta | sí | 0 | `medir_muros.py` |
| 5 | huecos entre solares / casas | 515 m / 193 | < 200 m / >= 200 | `urbanismo.log` |
| 5 | fallos `revisar_urbanismo` | 23 | 0 | `urbanismo_informe.json` |
| 4 | árboles / tris de vegetación | 2.7 k / 1.74 M | 6-9 k / <= 0.9 M | `kn5_presupuesto` |
| 4 | árboles quitados por inspectores por pasada | ~140 | < 20 | `asentar.json` |
| 4 | `siluetas_20_120` en 50/51/52 | x1 | x3 | `medir_capturas` |
| 6 | bandas de tono en el mar (54/57) | 1 | >= 3 | hue por columnas |
| 6 | banda blanquecina de playa (16) / cala losa (36) | sí | no | captura A/B |
| 7 | horizonte en 49/52/54/56 | no | >= 60 % del ancho | captura A/B |
| 7 | coches con cara / bancales tallados | ~80 / 5 bandejas | >= 250 / 40-80 | logs |
| 7 | torres sobre losa sin camino | 5 | 0 | captura 27_x/36/41 |
| 8 | elementos "coche" en el casino (53/58) | 0 | >= 3 | captura |
| 9 | secciones ext_config activas / inertes sin CSP | 2 / sí | 10-12 / sí | `validar_ext_config.py` |
| X | KN5 de ensayo cargan en AC | - | 5/5 | fotos del amigo |
| Todos | tris / mallas / materiales / texturas / KN5 / zip | 5.26 M / 572 / 441 / 12.5 MB / 355 MB / 172 MB | <= 6.0 M / 800 / 520 / 80 MB / 450 MB / 250 MB | `kn5_presupuesto.py` |
