# paleta.json / paleta.py — la única fuente de color de la fase visual

Bloque 0, punto 7 del `FASE_VISUAL_PLAN.md` (decisión 0.5: "`paleta.json` como única fuente de color"). Escrito el 04/10/2026.
Estado: **v2 (04/10 ~19:45), valores del usuario aplicados** (sección "Paleta v2" de `DECISIONES_USUARIO.md`); la v1 fue
validada por el usuario con `renders/qa/carta_color.png` y corregida con sus valores. Los consumidores de F1 ya la leen.

## 0. v2 — qué cambió (propietario `paleta`, 04/10 tarde-noche)

- **Claves conservadas**, valores nuevos (sRGB del usuario → lineal exacto, ambos en el JSON): `caliza_ocre` = caliza CLARA
  #D8CCB0, `caliza_gris_calido` = MEDIA #B3A68A, `caliza_sombra` = roca OSCURA #7F766A (sin gris azulado); `terracota` #BF6440.
  Alias en `alias`: `caliza_clara`, `caliza_media`, `roca_oscura` (misma entrada; `paleta.nombres()` no los lista).
- **Nuevos**: `cipres_pino_oscuro` #34503A, `verdin_cupula` #6FA391, `contraventanas` #3E6A48, `buganvilla` #C2407A (acento,
  pequeñas dosis), `marmol_casino` #EEE4CF, `marco_ventana_crema` #F1E9D6 (crema claro coherente con crema_calido). 18 colores.
- **Fachadas**: `fachadas_propuesta` = azafrán #E2A84A, ocre_naranja #D88A4C, siena #C46A43, rojo_pompeyano #B04A3B, melocotón
  #E6A487, crema_calido #EBDDBE; retirados blanco_roto / rosa_antico / ocre_portofino / amarillo_napoles / rojo_pompeya;
  `fachadas_actual_compatibles.claves = []`. `fachadas_variacion` (tono ±5°, brillo ±5 %) → `casas_kit_v2` crea 3 variantes
  por tono (`MAT_CASAS_fachada_<tono>`, `_osc`, `_cla`) = 18 materiales, elegidas por seed de casa sin tocar la geometría.
- **Consumidores tocados** (solo constantes de color): `casas_kit_v2` (PALETA_FACHADA, COL_TEJA, COL_PIEDRA → marco crema,
  COL_PERSIANA → contraventanas), `casino_v2` (`_COLORS` por paleta; cúpulas/linternas en verdín con `patina=True`), `edificios_civicos_v2`
  (`_PALETTE` admite nombres de paleta), `vegetacion_kit_v2` (cipreses/pinos oscuros, buganvilla en adelfa rosa y 12 % de arbustos),
  `calle_kit` (maceta terracota + flor buganvilla), `montanas_fondo_v2` (pueblo lejano → marmol_casino), `aplicar_texturas.FAMILIAS`
  (ganancias teja 4.87, piedra 1.99, caliza 1.78). Tiles regenerados: teja, piedra, caliza (PIL) y caliza/teja/piedra_seca/escollera/
  afloramiento/acantilado (CC0). `carta_color.py` admite N colores (filas de 6).
- **Validación**: `renders/ab/paleta_v2/` (pares AB_* antes/después con luz de tarde desde el coche; `hoja_paleta_v2_piloto.png`,
  `hoja_paleta_v2_aereas.png`) hecha con `_rev/_tmp_paleta/validar_paleta_v2.py` sobre una copia de escena_rev (re-tintado por
  nombre de material; la escena real se re-tinta al regenerar). Carta de registro: `renders/qa/carta_color.png` (v2).

## 1. Qué es

- `03_blender/paleta.json`: 12 colores de partida (`oliva_oscuro`, `salvia`, `hierba_seca`, `caliza_ocre`, `caliza_gris_calido`,
  `caliza_sombra`, `terracota`, `cesped_jardin`, `tierra`, `arena`, `mar_orilla`, `mar_profundo`), cada uno con `rgb` (lineal 0..1),
  `srgb_hex`, `familia_ac` (familia de `04_export/color_ac.py` `FAMILIAS` l.307-321: terreno / roca / vegetacion / edificio / agua) y `uso`.
  Además dos secciones solo informativas: `fachadas_actual` (los 5 tonos que pinta hoy `casas_kit_v2.PALETA_FACHADA` l.87, con su
  lineal real: `_srgb()` usa gamma 2.2) y `fachadas_propuesta` (5 tonos Riviera: `ocre_portofino`, `rosa_antico`, `amarillo_napoles`,
  `rojo_pompeya`, `blanco_roto`).
- `03_blender/paleta.py`: `cargar()`, `rgb(n)`, `rgba(n)`, `srgb(n)`, `srgb8(n)`, `srgb_hex(n)`, `familia_ac(n)`, `uso(n)`, `variante(n, lum)`,
  `nombres()`; conversión sRGB exacta (`lin_a_srgb`, `srgb_a_lin`, no gamma 2.2). Las fachadas se piden como `fachada_<nombre>` y
  `fachada_actual_<nombre>`. `python paleta.py` lista y verifica (hex == sRGB(rgb), familias válidas); `--png out.png` dibuja muestras planas.
- `03_blender/_rev/carta_color.py` (bpy, solo por `blender_cola.sh`): 12 esferas + 10 cubos con la luz, el cielo y la vista de
  `renderizar_capturas.py` (sol 4.6 W a 34°/-140°, Standard, exposición 0.12, GTAO) -> `renders/qa/carta_color.png` (1600x900, ~2 s).
- `renders/qa/paleta_muestras.png`: las mismas muestras planas en sRGB (sin luz), de `paleta.py --png`.

**Regla del plan (decisión 0.5 / `entender_materiales.md` §3.a.1)**: `material.diffuse_color` o el Base Color del Principled **sin
enlazar** = la media lineal que se quiere ver. Es lo único que lee `04_export/kn5_writer_opt.py` (`analizar_material` l.221-266); lo
procedural (rampas, Mix, atributos) solo existe en Blender. Por eso cada entrada es un único RGB lineal y no una rampa.

## 2. Valores v1 (lineal -> sRGB) y de dónde salen

| nombre | rgb lineal | sRGB | familia | nota |
|---|---|---|---|---|
| oliva_oscuro | 0.16, 0.20, 0.08 | #6F7C50 | vegetacion | plan A B0.4 |
| salvia | 0.30, 0.36, 0.22 | #95A281 | vegetacion | plan A |
| hierba_seca | 0.55, 0.45, 0.20 | #C4B37C | terreno | plan A |
| caliza_ocre | 0.46, 0.37, 0.24 | #B5A486 | roca | plan A |
| caliza_gris_calido | 0.34, 0.31, 0.26 | #9E978B | roca | plan A |
| caliza_sombra | 0.25, 0.20, 0.14 | #897C69 | roca | plan A |
| terracota | 0.45, 0.145, 0.072 | #B36A4C | edificio | **ajustado**: el del plan A (0.62, 0.30, 0.20) daba salmón claro (#CE957B); este es teja de verdad y menos naranja que `COL_TEJA` (#AB4524) |
| cesped_jardin | 0.22, 0.42, 0.12 | #81AD61 | terreno | plan A; SOLO jardines y rotondas |
| tierra | 0.52, 0.37, 0.20 | #BFA47C | terreno | **ajustado** un 13 % más oscuro que el plan A (0.60, 0.43, 0.24 = el `MAT_tierra` actual l.86) |
| arena | 0.78, 0.72, 0.55 | #E5DDC4 | terreno | plan A |
| mar_orilla | 0.25, 0.75, 0.72 | #89E1DD | agua | plan A |
| mar_profundo | 0.006, 0.11, 0.30 | #125D95 | agua | **ajustado**: el del plan A (0.01, 0.22, 0.42 = #1A8CAF) era un azul medio, no "profundo" |

Lo que se ve en la carta es lo que verá Blender; en AC el color pasa por `color_ac` (gamma de Kunos, `CROMA_MAX` 1.08, `techo` por familia),
así que los ocres y terracotas saturados pueden salir algo más lavados hasta que se re-mida (§3.a.4 de `entender_materiales.md`, F4).

## 3. Quién la consume y dónde (líneas de los informes del 04/10 por la mañana; las de `04_export` re-comprobadas con `grep -n` por la tarde, tras los cambios del equipo del zip: comprobar antes de editar)

Hoy el color vive en >= 9 sitios que no se leen entre sí (`entender_materiales.md` §3.a, tabla). Cada consumidor sustituye su literal por
`paleta.rgb(...)`/`paleta.rgba(...)` (bpy) o `paleta.srgb8(...)` (PIL), y **nada más**: los nodos procedurales siguen como están.

### Bloque 3 — paleta, máscara por texel y luz (F1; propietario "Materiales" y "Máscara/terreno-material")
| Consumidor | Fichero : líneas | Qué sustituye |
|---|---|---|
| rampa por altura del terreno | `construir_pista.py` 110-114 | arena (z~0) -> `arena`; hierba baja -> `hierba_seca`; monte -> `oliva_oscuro`; cumbres -> `caliza_ocre` |
| parches de pradera | `construir_pista.py` 125-126 | multiplicadores 0.78..1.15 se quedan (son relativos) |
| roca del terreno | `construir_pista.py` 179 (`mixr.inputs[7]`) y 262-263 (`ROCA_rampa`) | `caliza_gris_calido` / `caliza_ocre` |
| color que ve el writer | `construir_pista.py` 181 (`m.diffuse_color`) | `hierba_seca` (media de la zona dominante junto a la pista; hoy (0.32, 0.45, 0.20) = verde césped) |
| tierra, acera, bordillo, arcén, muros | `construir_pista.py` 86 (`MAT_tierra`), 807-808 (`MAT_acera_piedra`, `MAT_bordillo_piedra`), 1169 (`MAT_arcen`), 1285 y 1516 (`MAT_muro_contencion_piedra`) | `tierra`, `caliza_gris_calido`, `caliza_gris_calido`, `hierba_seca`, `caliza_ocre` |
| tiles PIL | `texturas/generar_texturas.py` 306-307 (`hierba()`: `c_a`, `c_b`) | dos tiles nuevos `hierba_seca_d.png` (`hierba_seca` +-8 %) y `matorral_d.png` (`oliva_oscuro`/`salvia`); `cesped_d.png` (`cesped_jardin`) solo jardines; `piedra_d.png` -> `caliza_ocre`; `teja_d.png` -> `terracota` |
| máscara por texel (nuevo `mascara_terreno.py`) | `terreno_diffuse.png` 2048 | color base por capa = R `oliva_oscuro`, G `hierba_seca`, B `tierra`, A `caliza_ocre` x AO |
| césped de jardín (nuevo `MAT_cesped`) | horquilla Loews, casino, plazoletas | `cesped_jardin` |
| luz | `construir_pista.py` 1566-1618 | no toca la paleta (la carta ya usa esa luz) |
| `color_ac` | `04_export/color_ac.py` `_REGLAS` 350-372, `familia()` 375 | [W] subcadenas `matorral`, `seca`, `cesped`, `caliza_ocre`; re-medir objetivos al final (F4); petición X7 de `PETICIONES_04_EXPORT.md` |

### Bloque 2 — roca integrada (F2/F4; propietario "Rocas")
| Consumidor | Fichero : líneas | Qué sustituye |
|---|---|---|
| roca del lazo | `assets/roca_lazo.py` 151-175 (`_PALETA`) | la caliza común: `caliza_ocre` al sol, `variante('caliza_ocre', 0.85)` oscura, `caliza_sombra` en juntas |
| peñón del casino | `assets/roca_casino.py` 98-116 (`_PALETA`) | ídem |
| cara del peñón / meseta | `assets/penon_cara.py` 303-305 | `caliza_ocre` (hoy "meseta blanca") |
| McLaren petrificado | `assets/montana_mclaren.py` 255-267 | `caliza_ocre` x 0.9 (hoy objetivo 202,197,183 = "plástico crema") |
| montañas de fondo | `assets/montanas_fondo_v2.py` 245-247 | `caliza_gris_calido` (más azul por bruma horneada en el propio color) |
| afloramientos (nuevo `afloramiento_kit.py`) | — | `caliza_ocre` / `caliza_sombra` |
Regla para los kits: una sola familia `roca` con matices `_clara/_oscura` = `variante(nombre, 1.15 / 0.85)`; desaparecen las 4 calizas
distintas con el mismo nombre `MAT_PPUEBLO_roca` (riesgo R3 de §3.a).

### Bloque 4 — vegetación (F1 plan, F3 kit v3; propietario "Vegetación")
| Consumidor | Fichero : líneas | Qué sustituye |
|---|---|---|
| copas | `assets/vegetacion_kit_v3.py` (nuevo; hoy `vegetacion_kit*.py`, `MAT_VEG_*`, `MAT_OLI_*`, `ital_*`) | pino/encina `oliva_oscuro`, olivo/matorral `salvia`, variación por instancia `variante(n, 0.85..1.15)`; nunca `cesped_jardin` |
| plan de vegetación | `vegetacion_plan.json` | la "sombra de bosque" de `terreno_diffuse` oscurece con `oliva_oscuro` x 0.6 |
| TreeFX (extra CSP) | `extension/trees/trees.txt` `color variance` | multiplicadores alrededor de 1, el tono lo da la textura del `.bin` (misma paleta) |

### Bloque 5 (pueblo; propietario "Pueblo-escena/kits")
`assets/casas_kit_v2.py` 87 (`PALETA_FACHADA`) -> `fachadas_propuesta` si el usuario la valida; 95 (`COL_TEJA`) y 172-183 (teja) -> `terracota`.

## 4. Pruebas hechas
- `python 03_blender/paleta.py --png renders/qa/paleta_muestras.png` -> "verificacion: OK (22 entradas)" (hex == sRGB(rgb), familias válidas).
- `bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/carta_color.py` -> `renders/qa/carta_color.png` 1600x900, EEVEE, 12 esferas + 10 cubos, 2 s.
- `03_blender/_rev/kn5_ensayo.py` ya la consume (tiles de detalle y hierba de los KN5 de ensayo).

## 5. Pendiente
- Validación del usuario (carta). Si cambia un valor: editar `paleta.json`, `python paleta.py` (verifica) y relanzar la carta.
- Añadir `asfalto` y `pintura_vial` cuando el bloque 3 toque `MAT_asfalto` (hoy los decide `color_ac` por medida, no por paleta).
- Las fachadas propuestas son 5 (no 8-10): el plan pide 8-10 tonos de fachada en la carta y se muestran 10 (5 actuales + 5 propuestos).
