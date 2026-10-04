# Plan C — "JUGADOR PRIMERO": fase visual de Porto Corsa vista desde la cámara del coche

Arquitecto técnico C, 04/10/2026. Solo lectura: no se ha modificado ningún fichero del proyecto, no se ha
lanzado Blender, no se ha descargado nada. Fuentes: `PLAN_USUARIO.md`, `director_final.md`, `RONDA15_PLAN.md`
(convenciones y estado), los 10 informes de `_rev/fase_visual/` (entender_terreno / materiales / vegetacion /
pueblo / rocas / agua_publico_capturas, web_treefx / csp_agua_luces / multilayer_vao_erosion / texturas_cc0) y
15 capturas de `renders/capturas/` (01, 04, 07, 08, 13, 15, 32, 36_general, 40, 49, 50, 51, 52, 53, 54).
Las líneas de código citadas son las que dan esos informes (estado del 04/10 por la mañana).

Ángulo de este plan: ordenar TODO lo que pide el usuario por lo que de verdad ocupa el cuadro desde el coche
(las 6 vistas de piloto s300/800/1700/2900/3400/4150 a 1.4 m + los 5 momentos postal) y, en segundo lugar, por
las aéreas; decir qué dejar fuera o para después; y separar lo que se ve en AC "a pelo" de lo que es extra CSP.

---

## 0. Qué ve el jugador de verdad (inventario antes de priorizar)

### 0.1 Reparto del cuadro en las 6 vistas de piloto (medido a ojo sobre las capturas de 1600x900)

| Vista | Lo que ocupa el cuadro (aprox.) | Defectos que SE VEN desde el coche | Bloques que lo arreglan |
|---|---|---|---|
| 49 s300 (recta → túnel) | asfalto 45 %, pedestal/desmonte del McLaren 25 %, talud dcho con hierba estirada 15 %, cielo 10 %, mar/guardarraíl izq 5 % | caliza "plástico crema" con rayas; portal pequeño bajo la rueda (radios a la vista); hierba estirada en vertical; desmonte con curvas de nivel; césped saturado | 2 (McLaren, máscara), 3 (hierba BOX, paleta), 1 (talud) |
| 50 s800 (pueblo) | asfalto 40 %, casas izq 15 %, terrazas dchas vacías + muros-aleta 25 %, cielo 15 % | prados verdes planos a la derecha sin casas, muros que asoman de la ladera, césped entre casas, cono beige al fondo | 5 (escarpa, manzanas), 3 (paleta), 1 (berma) |
| 51 s1700 (tierra) | tierra beige lisa 40 %, ladera verde uniforme 35 %, desmonte gris con rayas 10 %, cielo 10 %, pacas-cubo 5 % | no se lee "tallado en la montaña": lomas suaves; desmonte-cantera; pino = disco en palo; bancal-caja; césped saturado | 1 (reglas de tierra), 3 (máscara/paleta), 2 (bancos), 4 (siluetas), 7 (bancal tallado) |
| 52 s2900 (recta de subida) | asfalto 40 %, cielo 35 %, prado verde + piruletas 20 %, muro sillares 5 % | anodina: nada a 20-100 m salvo piruletas; nada que diga "costa" ni "subida" | 4 (masas), 3, 7 (aparcamiento/horizonte), 1 (acantilado lado mar) |
| 53 s3400 (casino) | asfalto 55 %, casino + torre cámara 15 %, casa 10 %, cielo 20 % | ok; el casino "de dibujo" funciona; falta carificación en fachada noble | 8 (opcional) |
| 54 s4150 (viaducto/roca del lazo) | roca gris lisa 40 %, asfalto 35 %, mar 15 %, cielo 10 % | la pared de roca no tiene textura ni estratos; mar plano sin degradado ni orilla | 2 (material caliza), 6 (agua) |

Conclusión 1: a 1.4 m de altura el cuadro lo llenan **la banda de 0-40 m a ambos lados de la pista y las caras
verticales pegadas a ella** (desmontes, pedestal del McLaren, roca del lazo, muros, fachadas). El macizo lejano,
la erosión del heightmap, el puerto-llanta o la silueta Topolino del peñón son cosas de cámara aérea.

Conclusión 2: los 5 defectos que aparecen en MÁS vistas de piloto son, por este orden: (a) césped verde saturado y
uniforme (6 de 6), (b) hierba/roca por vértice con bordes difusos, dientes de sierra y hierba estirada (49, 50, 51),
(c) árboles-piruleta aislados sobre prado (50, 51, 52), (d) caras de corte lisas con "curvas de nivel" (49, 51, 54),
(e) nada entre 20 y 120 m que dé escala (52, 51). Son materiales y densidad, no geometría grande.

### 0.2 Los 5 momentos postal (cámaras que hay que CREAR, fuera de las 6 de piloto)

| Postal | Cámara propuesta (`renderizar_capturas.py` / `_rev/tomas_capturas.py`) | Qué debe verse | Bloques |
|---|---|---|---|
| P1 salida del túnel del McLaren | `55_postal_tunel_salida`: piloto en s 528 (12 m antes de la boca de salida s 540), tgt s 610, lente 20 | el arco del portal/llanta enmarcando el talud y el mar; sillería del portal; la pared del túnel con juntas | 2 (portal alto, galería con juntas), 1 (talud de salida), 6 |
| P2 cima de la tierra, bahía entera | `56_postal_cima_bahia`: piloto en s 1870 girado hacia el S/SE (azimut hacia la bahía (300,-300)), lente 20 | la bahía, el viaducto y el peñón abajo; nada de pacas/árboles tapando a < 40 m | 1 (caída exterior, despeje de vista), 6, 7 (horizonte) |
| P3 puente del casino | `57_postal_viaducto`: piloto en s 3660 (tras la Loews, entrando al viaducto), tgt s 3760; se mantiene 54 | la curva del viaducto, la roca del lazo con bancos, mar con degradado | 2 (lazo), 6 |
| P4 bajada a la horquilla de la fuente | `58_postal_loews`: piloto en s 3500 bajando, tgt la Loews; (ver pregunta Q5: Loews o C26) | la rotonda-fuente, el casino detrás, farolas | 8, 9 (luces), 6 |
| P5 recta del puerto | `59_postal_recta_puerto`: piloto en s 5150, tgt s 5230 (+ variante en s 60 mirando a s 140 con lente 20) | tribunas, puerto a la izquierda, y AL FONDO el McLaren saliendo de la montaña | 2 (McLaren integrado), 6 (puerto, escollera), 7 (público) |

P5 es la postal que castiga el defecto 1 del director (el islote): desde s 60 el McLaren está en el eje de la
recta a 350-500 m. Por eso el "cabo bajo la zaga" (entender_rocas 8.4.a) NO es solo aéreo: cuenta para el jugador.

### 0.3 La verdad incómoda: lo que verá el amigo NO es lo que vemos en las capturas

Verificado en entender_materiales §2 y entender_vegetacion §3.4: en el KN5 actual el terreno es UN tile de
césped verde tintado en todo el macizo (la roca por pendiente no existe), todas las rocas son colores planos 8x8,
los árboles son colores planos sin sombra, no hay AO ni bump ni rampa por altura. Es decir, **en AC "a pelo" la
pista se ve HOY peor que en las capturas**, y cualquier mejora de materiales en Blender que no pase por el
exportador no llega al jugador. Consecuencias para el plan:

1. Cada bloque tiene dos mitades: "Blender" (se puede hacer ya) y "export" (04_export, cerrado hasta que el otro
   equipo cierre v1.1). La mitad export se entrega como **lista cerrada de 10 cambios** (sección X) para hacerlos
   de una vez, con un KN5 de ensayo pequeño para el amigo ANTES del circuito entero.
2. Las capturas antes/después necesitan un **modo "fiel a AC"** (flag `--modo-ac` en `capturas_ab.py`): sombras de
   vegetación apagadas, materiales reducidos a lo que el writer entiende (ya existe la base en
   `_rev/color_ac/simular_vistas.py`). Si no, juzgaremos lo que el jugador nunca verá.
3. Lo "esencial" (se ve sin CSP) va siempre antes que lo "extra" (CSP): TreeFX, luces, cáusticas, animados, VAO,
   nm4 son extras y se dejan para el final o para una entrega posterior.

### 0.4 Regla de prioridad usada en todo el plan

`impacto = superficie media en el cuadro de piloto × nº de vistas de piloto/postal afectadas × (2 si se ve en AC
a pelo, 1 si solo con CSP)`; `esfuerzo = horas-agente + nº de regeneraciones completas de Blender (~1 h cada una
con la cola) + riesgo de romper QA (urbanismo 0 fallos es bloqueante, checks de terreno, tests de rocas)`.
Prioridad = impacto / esfuerzo. Lo que sale con prioridad baja va a "después" o a "no hacer" (sección 13).

### 0.5 Medidas automáticas comunes (nuevo `_rev/medir_capturas.py`, python del sistema + PIL/numpy)

Para que "objetivo visual medible" no sea una opinión, un script de 80 líneas que, sobre cada PNG de piloto/postal
y sobre 01/07/21, calcula y escribe `renders/ab/<bloque>/medidas.json`:
- `pct_cesped`: % de píxeles con HSV en H 95-135°, S > 0.45, V > 0.5 (el verde césped del tile actual). Hoy 40-70 %
  en 50/51/52; objetivo final < 8 % en piloto (solo jardines/rotondas).
- `riqueza`: varianza local media (ventana 9 px) en las zonas de terreno (fuera de cielo y asfalto); objetivo x2.
- `bandas_blancas`: nº de componentes conexas de píxeles claros (V > 0.75, S < 0.15) rodeadas de verde, de más de
  40 px (los dientes de sierra de 07/08); objetivo 0.
- `pared_lisa`: % de píxeles de roca (HSV gris/ocre) con varianza local < umbral; objetivo < 30 % (hoy ~80 % en 54).
- `siluetas_20_120`: nº de árboles contados por el log de `vegetacion.py` dentro de un cono de 60° y 20-120 m
  desde cada cámara de piloto; objetivo x3 respecto a hoy.
Son 4 h de un agente y sirven para los 9 bloques. Se hacen en el bloque 0.

---

## Bloque 0 — Infraestructura de juicio (prerrequisito de todo)

**Objetivo medible**: poder renderizar el set reducido (7 base + 5 postales + 4-8 del bloque) en < 60 s desde las
MISMAS cámaras antes/después, con hoja lado a lado y medidas automáticas; y poder renderizar "como AC".

**Cambios técnicos** (todos nuevos en `_rev/`, ninguno toca el pipeline):
- `_rev/tomas_capturas.py`: `construir_tomas(G, bpy) -> [(nombre, loc, tgt, lens)]` = las líneas 45-330 de
  `renderizar_capturas.py` dentro de una función + las 5 postales 55-59 de §0.2 + las 4 tomas 60-63 propuestas en
  entender_agua §9.2. `renderizar_capturas.py` no se toca hasta que el coordinador decida que importe de aquí.
- `_rev/capturas_ab.py` (esbozo completo en entender_agua §9.5): `--set`, `--guardar-camaras` / `--camaras`
  (cámaras congeladas en JSON, sin `camara_segura` en el "después"), `--solo`, `--res`, y el flag nuevo
  `--modo-ac`: desactiva `cast_shadow`/`visible_shadow` en objetos `VEG_/OLI_/ITAL_cipres` (lo que hace
  `castShadows=0` en el KN5), fuerza `use_gtao=False`, y para cada material sin Image Texture enlazado sustituye el
  árbol por el `diffuse_color` plano (lo que hace `analizar_material`). Es una aproximación honesta, no AC.
- `_rev/montaje_ab.py` (esbozo en entender_agua §9.6) + `_rev/medir_capturas.py` (§0.5).
- Sets: `BASE` = 01 + 49-54 + 55-59 (siempre); por bloque los listados en cada sección de abajo.

**Dependencias**: ninguna. **CSP**: no aplica. **Riesgos**: `escena_rev.blend` se sobreescribe en cada
`pipeline_escena.sh`: el "antes" se renderiza ANTES de regenerar (o se copia el blend a `_rev/escena_antes_<bloque>.blend`).
**Verificación**: un AB sobre la escena actual (antes = después) debe dar diferencias de píxel 0.
**Horas**: 8-10 h, 1 agente, 1 hueco de cola (render de prueba). Primer día.

---
## Bloque 3 — Paleta, texturas y luz (EL PRIMERO: máximo impacto por hora desde el coche)

Se adelanta al bloque 1 a propósito: el césped saturado y la máscara por vértice están en las 6 vistas de piloto, se
arreglan sin tocar geometría, y toda regeneración posterior (relieve, pueblo, vegetación) se juzga mejor con la
paleta buena. Además es el bloque que define el contrato con 04_export (máscara por texel).

**Objetivo medible** (en 49-54 y 01/07/21, modo normal y modo AC): `pct_cesped` < 8 % (hoy 40-70 %); `bandas_blancas`
= 0 en 07/08; `riqueza` x2 en terreno; en 51 el desmonte tiene >= 3 tonos (roca, tierra al pie, hierba seca en
berma); ninguna cara > 45° con el tile de hierba estirado (medir: % de píxeles "verde" en caras con nz < 0.7, 0 %).

**Cambios técnicos (Blender, ya)**:
1. `03_blender/paleta.json` + `03_blender/paleta.py` (importable desde bpy y desde python del sistema; `color(nombre)`
   -> RGB lineal, `srgb(nombre)`, `familia_ac(nombre)`). 9 entradas: oliva_oscuro, salvia, hierba_seca, caliza_ocre,
   caliza_gris_calido, terracota, cesped_jardin, tierra, asfalto (valores de partida en entender_materiales 3.a y
   entender_rocas 8.1). Consumidores (entender_materiales 3.a, tabla): `construir_pista.py` l.86, 110-114, 125-126,
   179-181, 262-263, 1169, 1285; `texturas/generar_texturas.py` l.102-310; `casas_kit_v2.py` l.87 (PALETA_FACHADA,
   COL_TEJA); `roca_lazo._PALETA` l.150-175 y `roca_casino._PALETA` l.98-116 (unificar: hoy el mismo nombre con dos
   valores); `montana_coche_v2._mat_piedra` l.131-158; `vegetacion_kit_v2._PALETA` l.78-152 (copas a oliva/salvia).
   Regla: `diffuse_color` o Base Color sin enlazar = media lineal que se quiere ver (es lo que lee el writer).
2. `texturas/generar_texturas.py`: 4 tiles nuevos PIL seamless (misma síntesis espectral): `hierba_seca_d.png`
   (dorado, briznas 2-4 cm, tile 3 m), `matorral_d.png` (oliva/salvia, manchas 1-3 m, tile 6 m), `caliza_d.png`
   (ocre con juntas horizontales + grano, tile 3 m, para rocas y muros), `cesped_d.png` (el actual, solo jardines).
   `hierba_d.png` deja de ser el tile del terreno. Re-medir medias -> `ganancia`. Si el usuario autoriza CC0 (Q2),
   `texturas/recolorear_cc0.py` sustituye estos PIL por `withered_grass`, `aerial_grass_rock`, `rock_06`, `Ground105`
   recoloreados (lista y pesos en web_texturas_cc0 §5: 4 texturas P1, ~19 MB en 1K-JPG); la API del material es la
   misma, así que el orden "PIL primero, CC0 después" no cuesta trabajo doble.
3. `aplicar_texturas.py`: familias nuevas `seca`, `matorral`, `cesped`, `caliza` en `FAMILIAS` l.44-65 y `familia_de`
   l.73-101 (subcadenas `cesped`, `LOEWS_`, `URB_jardin` -> cesped; `roca`/`caliza`/`PPUEBLO_roca`/`MCOCHE_caliza` ->
   caliza con imagen); `FAMILIAS['hierba'].proy` FLAT -> BOX (l.59-60) para lo que siga usando hierba; `aplicar_roca()`
   l.359-398: manchas de 20 m de ±50 % a ±10 % (es el "velo de bruma" de 13/19/45) o retirarla cuando entre el grupo
   de caliza del bloque 2.
4. **Máscara por texel** (nuevo `03_blender/mascara_terreno.py`, python del sistema, después de `preparar_geometria.py`):
   `generar(geom_path, out_dir, px=2048, seed) -> {'mask': ruta, 'base': ruta, 'ao': ruta, 'stats': {...}}`. Lee
   `geometria_3d.json` (z, mar, mascara_roca, cumbres, muestras) y escribe `texturas/terreno_mask.png` RGBA (R matorral,
   G hierba seca, B tierra, A roca; suma = 1; bordes con ruido de 10-30 m, nunca por celda), `texturas/terreno_base.png`
   (color de baja frecuencia = paleta por canal × parches de pradera × AO numpy: cavidad + oclusión por horizonte 8
   direcciones + hillshade suave) y `terreno_ao.png`. Reglas: A donde pendiente suavizada > 0.70-0.84 (35-40°) o
   `mascara_roca` > 0.5 o `_corte`; B en una banda de 6-10 m al pie de cada A (derrubios), en bermas y a < 8 m del
   borde en `sec == dirt`; G en llanos (< 0.35) a < 60 m de la pista y z < 60; R en el resto de laderas y en el macizo;
   césped NO (los jardines llevan material propio). 2048 px sobre 2068 x 2060 m = 1 m/texel (la celda es de 4 m).
5. `construir_pista.py`: capa UV planar en TERRENO (`me.uv_layers.new('UVMap')`, u = (x-x0)/(nx·cell),
   v = (y-y0)/(ny·cell)) tras l.1448-1468; `mat_terreno()` v2 = Image(mask, UV) + 4 Image tiles (UV × mult_k) +
   base/AO multiplicando, mezcla por canal; se CONSERVA el nodo etiquetado `ROCA_mascara`/`Math.002` (ahora = canal A
   max talud por nz) porque lo leen los revisores, `aplicar_texturas` y `color_ac` (umbrales 0.50/0.49/0.82);
   `diffuse_color` = media de hierba seca. `aplicar_terreno()` (l.247-342) se retira para `MAT_terreno`.
   `AGUA_fondo` (l.1485) deja de usar `M_TER`: material propio `MAT_fondo_marino` (arena clara) — enlaza con bloque 6.
6. Luz (`construir_pista.py` l.1566-1618): sol 34° -> 42° y azimut que rasante la ladera de la tierra (sombra propia
   de los desmontes y del macizo); NO activar niebla de mundo (el director ya confunde manchas con bruma); mantener
   `view_transform Standard` (R1 de color_ac: cambiar la curva invalida todas las medidas).
7. "Bisel" barato: `shade_smooth` + auto smooth 30-40° en los kits que van en `shade_flat` (casas, muros, pretiles,
   bancales): el writer exporta `corner_normals`. NO modificador Bevel (7 M de vértices).

**Cambios técnicos (04_export, después de v1.1; sección X)**: plan A `ksMultilayer_fresnel_nm` (shader VANILLA de
Kunos: txDiffuse = base×AO, txMask, txDetailR/G/B/A, txDetailNM; `multR..A` ≈ 2068/tile_m; fresnel bajo) + extra CSP
`[SHADER_REPLACEMENT] SHADER = ksMultilayer_fresnel_nm4 + tilingFixR/G/B/A` en `ext_config.ini`; plan B si A no se
puede probar a tiempo: `repartir_terreno()` en `exportar_ac.py` (4-6 materiales por cara con ruido por cara, bordes
de 4 m). La máscara y la UV de los puntos 4-5 sirven para los dos planes. Re-medir `color_ac` al final.

**Dependencias y orden**: 1 -> 2 -> 3 (un agente); 4 -> 5 (otro agente); 6-7 (tercero). Bloque 2 (material de
caliza) se enchufa en 5 cuando exista; mientras, `caliza_d.png`. Nada toca `04_export`.
**CSP**: esencial = todo lo de Blender + plan A o B en el writer. Extra = nm4 + tilingFix, VAO (bloque 9).
**Riesgos**: R1 de color_ac (todas las medidas caducan: se re-mide una sola vez al final); `familia()` de color_ac
clasifica por nombre (`MAT_matorral` caería en "pintado": añadir subcadenas en `_REGLAS` l.309-331: petición a
export); la rejilla de 4 m sigue dando "escalera" en AC si se usa el plan B (mitigar con 2 clases de transición).
**Verificación**: AB `BASE` + set `paleta` (05, 06, 09, 14, 16, 21, 22, 39) en modo normal y `--modo-ac`;
`medir_capturas` (umbrales de arriba); `revisar_*` sin cambios (la máscara que leen es la misma); `kn5_check`
sin cambios hasta la sección X.
**Horas**: paleta + consumidores 8 h; tiles + familias 6 h; máscara + AO 10 h; UV + material v2 6 h; luz/bisel 3 h;
AB y medidas 3 h = **36 h, 3 agentes en paralelo, 2 regeneraciones**. Export (sección X): 15-20 h adicionales.

---

## Bloque 2 — Roca integrada (segundo: 49, 54, P1, P3, P5 y todas las aéreas)

**Objetivo medible**: en 54 y 49 `pared_lisa` < 30 % (hoy ~80 %); en 54 se cuentan >= 4 juntas de estrato horizontales
por 10 m de pared; en 49/33 el umbral del coche NO queda a la vista (la "repisa plana" desaparece: 0 píxeles de cara
horizontal crema bajo la carrocería); en 49/P1 el portal llega a los radios (altura del arco >= 11 m); en 01/02/P5
el McLaren tiene terreno detrás de la zaga por encima de la línea de agua (hoy: mar a -4 m en 120 m); en 13/P3
la roca del lazo muestra >= 3 bancos con repisa fuera del corte.

**Cambios técnicos, por orden de impacto desde el coche**:
1. **Material compartido** `assets/materiales_roca.py` -> node group `NG_caliza_estratos` (entender_rocas 8.1) en
   coordenadas de MUNDO (`Geometry.Position`, no `TexCoord.Object`: TUNEL_acantilado y PENON_* no están en el origen);
   estratos por z (periodo 2.5-4 m, junta hundida en el bump), bancos de 8-14 m con tono alterno, grano 0.3-1 m,
   manchas ±10 %, mojado bajo z = 1, paleta del bloque 3. Enchufar en `construir_pista._roca_terreno` (sustituye
   ROCA_rampa..ROCA_bump l.252-337, deja `Math.002`), `roca_lazo._mat` l.180-193, `roca_casino._mat`, `montana_coche_v2.
   _mat_piedra` (los 9 `MAT_MCOCHE_*`: `hueso` 0.80 -> 0.58, `cristal_pulido` rugosidad 0.26 -> 0.5). Con imagen
   `caliza_d.png` (o CC0 rock_06) multiplicando para que el writer tenga ALGO que exportar (plan vanilla: una imagen por
   material tintada; plan mejor en sección X: horneado por objeto).
2. **Máscara 35-40°**: `terreno_montana.construir` l.2261-2266 umbral natural 1.0 -> 0.70-0.84 con ruido, apertura 3x3
   y tamaño mínimo 12 celdas; banda de pie de derrubios 0.5; `construir_pista._roca_terreno` talud nz 0.50-0.56 ->
   0.70-0.78; quitar `ROCA_llano_hierba` donde atributo = 1. Petición export: `color_ac.ROCA_NZ/ROCA_ATR` alineados.
   (Con el bloque 3, el canal A de la máscara por texel usa la MISMA regla: un solo sitio de verdad, `mascara_terreno.py`
   lee los mismos umbrales de `terreno_montana`.)
3. **Desmontes en bancos** (49 pedestal/talud, 51, 09, 16, 28, 42): `terreno_montana` nueva `bancos_en_cortes(z,
   _corte, pend, hb=6..10, berma=1.5..2.5, fase=ruido 2D 40-80 m)` solo donde `_dsm` y pendiente > 0.75: cuantiza z en
   bancos con cara 80-88° y berma; `mascara_roca` = 1 en la cara, 0.3-0.5 en la berma (hierba seca); ridged 10-20 m en
   la pared. `integrar_escena.explanar` l.785-833 (coordinador): desmonte 1:1 liso -> mismo perfil en bancos (la pared de
   25-45 m tras el paddock). A 4 m de celda un banco de 6 m es 1.5 celdas: se lee en aéreas; desde el coche lo completan
   los afloramientos (punto 5).
4. **McLaren** (49, 33, 32, P1, P5, 01, 02, 13): en `montana_mclaren._roca`: (b) faldón de ladera (`_K_FALDA` 0.36 ->
   1.2-1.7 fuera de la zona del túnel, talud 30-40°, hasta la CINTURA +0.72R en los flancos y el capó en el morro),
   pared vertical SOLO en el ancho del portal (21 + 2 m de sillería); `_bloques` 28 -> 80-150 pedruscos (densidad
   máxima en los 15 m sobre el agua y en el contacto con el terreno); grietas en el macizo y el faldón (horizontales en
   juntas + 3-5 verticales por bloque, mismo `_grieta_v`); `_vegetacion` tipo "junta" (matas 0.6-1.2 m + hierba seca
   colgando, `_VEG_TRIS_MAX` 3400 -> 8000); portal: `_galeria`/`_portal` con arco de 11-12 m para que llegue a los radios
   (opción barata) en vez de hundir la rueda 8 m (`alto_base` 12 -> 20: Boolean, encaje y revisar_tunel otra vez: Q6).
   (a) CABO bajo la zaga en `terreno_montana.LANDFORMS` (cordal 60-100 m, 300-350 m, costa anulada en su huella,
   `mascara_roca` = 1 en la cresta): cambia la costa a 150-250 m del puerto y la QA de orilla: pregunta Q7. Sin (a),
   (b) ya quita la "repisa" y el "plástico" desde el coche; el "islote" de 01/02/13/P5 solo lo quita (a).
5. **Afloramientos semienterrados** (51, 52, 50 fondo, 07, 21): nuevo `assets/afloramiento_kit.py` con
   `build_afloramiento(parent, largo=8..40, alto=2..8, seed) -> ob 'AFLOR_roca'` (losa de caliza con 2-4 bancos, cornisa,
   pie en talud, NG_caliza_estratos, 300-900 tris) y `build_pedrusco(parent, r=0.6..3, seed)` (reutiliza
   `montana_coche_v2._pedrusco` / `vegetacion_kit.build_roca`); `test_afloramiento_kit.py` + previews. Zona
   `zona_afloramientos` en `integrar_escena` (coordinador, tras `zona_tierra`): candidatos con `pendiente_terreno` 0.5-1.0,
   alineados con la curva de nivel (rotación por gradiente), base 1-2 m bajo el terreno, 150-300 piezas en "cinturones",
   3-6 pedruscos al pie, matas en la repisa; exclusiones `_sitio_lejos_pista` (> 12 m), `_libre`, `zonas_excluidas`,
   rocas de los tres generadores, Loews. Alta de `AFLOR_` en `asentar_objetos.SOPORTE_PREF`/`ASENTAR_NO`,
   `revisar_flotantes.EXENTOS` (se asientan por su base enterrada), `despeje_final.DESPEJE_PROP`.
6. **Roca del lazo** (13, 34, 45, 15, P3; desde 54 solo cambia el material): `roca_lazo._bancos_naturales(M, G, seed)`
   tras l.3481-3490 (cuantización MONÓTONA, solo resta: `M' <= M`, bancos 8-14 m con fase por ruido 40-80 m, cara
   80-88°, repisa 2.5-6 m; restringida a `o > o_b + 8` y fuera de rasgos dilatados 6-10 m); 2-3 espolones (`domo` con
   a 3-4, b 0.6-0.9) en el lado N/NE; pinos en repisas con nz > 0.9 y ancho >= 3 m (`_poblar`); torre/fortín opcional
   (~2 k tris, sin logos). Es el H7 del registro: cambia terrazas, carreteras y cuencas (`_rellenar_cuencas`); todos los
   `checks` deben seguir en `ok`. Riesgo medio-alto: después de 1-5.
7. **Peñón del casino** (19, 20, 36, 10): `_perfil` l.1781-1786 de 3 cotas por banco a cada 1.5-2 m (27 k -> ~80 k tris);
   `estrato()` con labio 1.5-3 m; `textura()` con ruido 2-5 m; meseta `MAT_PPUEBLO_plaza/borde/muelle` texturizadas y
   oscurecidas un 25 % (la "nieve" de 36); pinos en labios anchos. Aéreo/parcial: después de 1-5.

**Dependencias y orden**: 1 y 2 en paralelo con el bloque 3 (mismo contrato de máscara); 3 y 4 necesitan
`terreno_montana` y `montana_mclaren` (ficheros distintos: 2 agentes); 5 es un kit independiente + 1 zona del
coordinador; 6 y 7 al final. `encaje_mclaren.evaluar()` tras 4; `urbanismo.py` tras 4(a) si crece `zonas_excluidas`.
**CSP**: todo esencial. Extra: VAO (bloque 9) para "AO en los huecos"; sin él, la AO va horneada en la textura del
objeto (sección X, horneado por objeto) o en el canal base del terreno (bloque 3).
**Riesgos**: cadena Boolean del McLaren (MANIFOLD; probar seeds 0/3/7/11 con `test_montana_mclaren`); `pista bajo
huella` en s 718-728 (holgura 5.6 m, ya al límite); H7 "represaba cuencas" (por eso cuantización monótona); tris:
+0.3-0.5 M (afloramientos 180 k, lazo +40 %, casino +50 k); el 28 % de las celdas de tierra pasa a candidata a roca:
sin la paleta del bloque 3 sería "todo gris".
**Verificación**: AB `BASE` + set `roca` (02, 13, 17, 19, 20, 32, 33, 33b, 34_general, 36_general, 45); `medir_capturas`
(`pared_lisa`, repisa 0 px); `test_montana_mclaren` TEST_OK, `encaje_mclaren` (pista bajo huella 0, holgura >= 4),
`revisar_tunel`, `test_roca_lazo`/`test_roca_casino` checks ok, `asentar.json`, `nada_en_pista` 0 de rocas.
**Horas**: material 8 h; máscara 3 h; bancos 8 h (+3 h coordinador en explanar); McLaren (b) 14 h (+6 h si (a));
afloramiento kit 10 h (+4 h coordinador); lazo 12 h; casino 6 h = **65-75 h, 3 agentes en paralelo** (material+máscara;
McLaren; kit) y luego 2 (lazo; casino); 3 regeneraciones.

---

## Bloque 1 — Relieve (lo que se ve desde el coche primero; erosión y macizo lejano después)

Desde el coche el relieve que importa es el de 0-60 m: pared a un lado y caída al otro en la tierra (51), berma
detrás de las terrazas (50), talud de salida del túnel (P1), acantilado lado mar en s 170-402 (49, izquierda) y en la
recta 2770-2976 (52). El macizo alto, las crestas y la erosión se ven en 01/21/P2 (cima) y como fondo lejano en 05/39.

**Objetivo medible**: KPI "pared > +8 m en un lado Y caída < -8 m en el otro a 25 m" en `sec == dirt`: 5 % -> >= 40 %
(a 50 m: 22 % -> >= 60 %); `pct_pista_con_pared_roca` 29.7 % -> >= 50 % en tierra; en 51 la silueta del terreno a la
derecha sube > 12° sobre la línea de horizonte de la cámara; orilla con z > 10 m: 7.5 % -> >= 25 % de las celdas de
costa en los tramos elegidos; en P2 la bahía ocupa >= 25 % del cuadro sin árboles/pacas a < 40 m; `coche_120m_pct_ge_90`
y `loews_ref_dz_max` = 0 sin cambios; `celdas_invaden_pista` = 0.

**Cambios técnicos (todos en `terreno_montana.py` salvo donde se indica; UN agente, el fichero no se reparte)**:
1. **Reglas de tierra** (entender_terreno §8.2): `peso` del tirón `_idw_pull` l.1083: 0.5 en s 1430-2440; `techo_desmonte_c1`
   con `pend` como ARRAY (1.8-2.0 en el lado interior de cada curva por signo de `_kap`, 1.15 en el resto); `s_fl` l.1306:
   1.2-1.5 en el lado exterior con berma `d_llano` 6-8 m (arcén + pacas + cierre); NO tocar la rasante (`MAXG` ya está al
   16.5 %, por encima del 12-15 % pedido; con 12 % la cima BAJARÍA: ver "no hacer"); controles de rasante solo a ±40 m de
   los apex de C18-19 y C26 (<= 8-10 %) en `preparar_geometria.py` l.332-392 (coordinador).
2. **Berma + bancales + costillas tras la última terraza** (50, 05, 06, 39): `techo_tras_terraza` l.731-739 y l.1458-1461:
   berma de 15-25 m entre el patio y el arranque de la cara; bancales también en el espolón del coche (`w_tope` l.1460);
   `BANCO_A` 1.6 -> 2.5 / `BANCO_H` 16 -> 12; costillas l.1812-1823 tope 2 m -> 4-6 m en caras > 20 m. QA de fosos <= 1.5 m
   y costuras < 0.6 m deben seguir.
3. **Macizo trasero** (05, 39, 01, 21, P2): `LANDFORMS` l.135-175: 'Espolón del coche' h 150 -> 190-220, s_foot 0.47 ->
   0.65-0.8, p 1.3 -> 1.6; 'espolón SO' +40; ridged l.394 `4 + 24·clip` -> `6 + 40·clip`; limitador por celda (0.8 a
   < 150 m de la pista, 1.3-1.6 en el macizo trasero) con `limitar_pendiente_mascara` dos veces. Riesgo: tajo tras las
   terrazas (por eso 2 va antes) y McLaren más enterrado (B11): `encaje_mclaren.evaluar()`.
4. **Acantilados Amalfi selectivos** (49 izq, 52, P1, 14, 22, 16): solo en 4 tramos: lado +1 de s 170-402 y 616-820
   (bajo el pretil), lado -1 de la recta 2770-2976, costa N/NE. `r_prot` l.978 `30 + 1.7·(z-4)` -> `20 + 0.8·(z-4)`;
   `pend` 2.5-4.0 y quitar topes `_wb` (l.1203-1206) y `_pm` (l.1210-1211) en esos tramos; J1 l.1115-1120 de 170 -> 60 m;
   costillas `_wcf` l.1829-1831 a todo `acantilado & _acant`; `s_fl` por celda >= 1.5-3.0 en el lado del mar con berma
   6-8 m. `construir_pista._pretil` pie `min(ze-2.5, zt-1.5)` debe seguir apoyando (revisar).
5. **Cámaras postal** (bloque 0) + despeje de vista en P2: `zona_tierra` l.1711-1757 y `pacas_tierra`: nada a < 40 m en
   el cono de P2 (s 1840-1900 lado +1).
6. **Erosión hidráulica NumPy** (01, 21, P2, 05/39 fondo; NO se ve en 49-54): `erosion.py` junto a `terreno_montana`
   (método de rejilla dandrino, 2 m y remuestreo a 4 m, reposo térmico por material con `mascara_roca`, `w_eros` de
   entender_terreno §6, inserción entre l.1127 y l.1135, N1 atenuado); coste 6-8 s a 2 m (web_multilayer §3.2.3).
   Determinista con semilla; QA hillshade antes/después. **Al final del bloque y opcional**: aporta a las aéreas y a la
   P2, no al jugador en pista; la diferencia fina (1-2 m) puede ir al canal normal de detalle del terreno (sección X).

**Dependencias y orden**: 1 -> 2 -> 3 -> 4 -> 6, cada paso con `python preparar_geometria.py` (QA_DIR de prueba, ~1-2
min) + `python urbanismo.py` (0 fallos obligatorio) ANTES de gastar una regeneración de Blender. Después de cada
regeneración: `revisar_urbanismo` 0 fallos, `encaje_mclaren`, capturas AB. Bloque 5 (escarpa de muros) y bloque 7
(bancales tallados) también tocan nodos del TERRENO: coordinar con el mismo agente.
**CSP**: todo esencial (geometría). Petición a export: el TERRENO no proyecta sombras (`GROUND_PREFIXES`): un macizo
que da sombra a la pista en Blender no la dará en AC; decidir si `1GRASS_terreno` pasa a castShadows = 1 (coste FPS).
**Riesgos**: urbanismo se regenera solo pero puede perder/ganar casas (re-ejecutar y mirar `huecos`); senderos CIMA/
ERMITA se replanifican (A*); pacas y cámaras de tierra se quitan por desnivel; cámaras aéreas congeladas dentro del
macizo nuevo (aviso del log, toma nueva); `revisar_fisica_ac` caídas en la escapatoria (cierre_ac ya cierra a w/2+6.75).
**Verificación**: `checks` de terreno (§2.8 de entender_terreno), `terreno_perfil.png` (±40 m), KPI pared/caída
(script numpy sobre `geometria_3d.json`, 1 h), AB `BASE` + set `relieve` (05, 07, 08, 09, 14, 16, 21, 22, 39, 42).
**Horas**: 1: 8 h; 2: 6 h; 3: 8 h; 4: 10 h; 5: 2 h; 6: 10 h (opcional) = **34-44 h, 1 agente (serial) + 4 h de
coordinador**, 3-4 regeneraciones. Puede empezar el mismo día que el bloque 3 (ficheros distintos).

---
## Bloque 5 — Pueblo (50 es la vista de piloto más rota; 40, 05, 06, 39)

**Objetivo medible**: en 50 (lado derecho, terrazas 1-2) >= 8 fachadas visibles donde hoy hay 0; "muros-aleta" = 0
(coronación de cada `CAMINO_muro` sigue `z_top` del JSON y el terreno a < 2.5 m del muro queda a `z_top-0.1` /
`z_base+0.1`); `huecos` de fila 515 m -> < 300 m; césped entre casas y delante de fachadas = 0 en 06/50 (aceras y
patios como losas); `urbanismo_informe.json` 0 fallos (hoy 23, 4 del pueblo); 40 deja de ser "muro ciego".

**Cambios técnicos (orden de entender_pueblo §8.5, adaptado al coche)**:
1. **Escarpa + muros con altura por vértice** (lo que quita las aletas; solo escena + asentar, 1-2 días):
   `urbanismo_escena.muro3d` l.171-191 -> usar `muro_rampa_sillares` l.215-281 (piezas de 4 m, coronación = `z_top` del
   JSON) para los muros del plan; pasada "escarpa" sobre nodos del TERRENO a < 2.5 m del muro (lado alto `z_top-0.1`,
   lado bajo `z_base+0.1`, respetando `_proteger_pista`) como `garantia_losas_terreno` en `asentar_objetos.py` l.680 o en
   `integrar` tras construir los muros (coordinador). Es el N2/F-06 pendiente del registro.
2. **Manzanas pegadas** (`urbanismo.py`): `construir_solares` l.1875-1998 por manzanas de 3-7 casas (`t += a`, sin buffer
   1.02 dentro de la manzana; hueco 1.5-2.5 m = carruggio/escalera entre manzanas); anchos `[4.5..9]`; plantas "no dos
   vecinas iguales"; exportar `medianera_izq/der` y `manzana` (solo AÑADIR campos al JSON); fachada en curva: opción B
   (solape trasero <= 0.6 m con medianeras ciegas y QA relajada dentro de la manzana); elementos nuevos `aceras` y
   `patios` (losas); casas de espaldas a la rampa donde `plan['alto']` queda detrás (recupera los ~50 m de patio por
   rampa). `verificar()` l.2529-2531 (`solar_solar` -> intersección de interiores salvo misma manzana), `huecos` entre
   manzanas. `urbanismo_escena.casa_var` l.407-413 con `laterales=(not medianera_izq, not medianera_der)`; retranqueo
   1-2 cm de la medianera más baja (z-fighting); `poligono('CALLE_acera'/'CALLE_patio')` dados de alta en
   `asentar_objetos.SOPORTE_PREF/LOSA_PLAN` l.132/1230 y `revisar_urbanismo.LOSA_PREF_QA/PROP_NO` l.83/120.
   **Para 50 en concreto**: el hueco de T0 816-935 y T1 821-970 viene de `rampa_alta` (278) + `lejos_calle` (808) +
   `terreno` (248 en s 920-1000): además de las manzanas, `GAP_RAMPA_ALTO` 4.0 -> 2.5 y la berma del bloque 1.2 (la banda
   de T2 no es llana ahí) son lo que rellena ESA vista.
3. **Suelo urbano desde el coche**: farolas cada ~18 m alternas en las calles de terraza (`calle_kit.build_farola`),
   `build_bolardo` nuevo (40 tris) en bocas de carruggi y plazoletas, tramos de adoquín en la calle de servicio
   (`tipo='servicio_adoquin'` en el centro del sector), alcantarilla de geometría (30 tris) cada 25 m en el eje. Petición
   export: `CALLE_bolardo` -> `1WALL_`.
4. **UVs + atlas de fachadas**: `_MB.cara/box/pbox` l.223-272 guardan (u, v) y `to_object` l.291-302 crea `uv_layers`;
   material `MAT_CASAS_atlas_<tono>` con Image Texture (el writer ya lee `uv_layers[0]`); excluir de `aplicar_texturas.
   familia_de` l.98-99 y de `mejorar_materiales.PREFIJOS` l.24. Contenido: 8-10 tonos Riviera con manchas de humedad en
   la base, zócalo, cornisa, contraventanas verde/azul/marrón, persiana, alcantarilla, cartel; PIL procedural primero
   (2048²), CC0 `white_stucco` + `clay_roof_tiles_03` + `PavingStones150` si Q2 (web_texturas_cc0 §5: ~12 MB en 1K).
   Macetas y ropa tendida como GEOMETRÍA opaca dentro de la malla de la casa (`macetas=0.3`, tendedero copiando
   `build_guirnalda` entre balcones enfrentados a < 6 m) hasta que el writer admita alpha test (sección X).
5. **Soportales, iglesia con cúpula, torreones**: `params['soportal']` (planta baja retranqueada 2.5 m con arcos;
   `huella_local` sigue viendo los pilares en y = 0: colisión intacta); `edificios_civicos_v2.build_iglesia` (cúpula +
   campanile, ~6 k tris) con solar de 2 anchos reservado en `construir_plaza` l.1832-1871 (una plaza por terraza, no por
   sector); torreón +1 planta en la casa de cabecera de manzana. Desde el coche (50, 53) se ven como silueta: después.

**Dependencias y orden**: 1 (escena) || 2 (plan) -> 3 -> 4 -> 5. 2 exige re-ejecutar `urbanismo.py` (0 fallos) y
`revisar_urbanismo` (0 fallos: `assert` l.2841 aborta el pipeline). Bloque 1.2 (berma) antes de juzgar 50. La plaza
del ayuntamiento del integrador (s 1120-1160, lado +1) sigue generando el `casa_muro` de CASAS_casa.066: pasar su
huella al spec como `zonas_reservadas` (coordinador, 2 h).
**CSP**: todo esencial. Extra: ventanas de noche `[Material_RoomWindows]` (bloque 9).
**Riesgos**: presupuesto (<= 5000 tris/casa × 193 -> medianeras ahorran, soportales gastan; medir en `kn5_check`); claves
de `urbanismo.json` solo se añaden (las leen `construir_pista._BOCAS` y `revisar_urbanismo._polilineas`); convenciones
intocables: `CASAS_casa`, fachada +Y en y = 0 (`exportar_ac` l.226-227), hijo `CASAS_zocalo`, pivote en el centro de la
fachada; dos medianeras coplanares (z-fighting).
**Verificación**: AB `BASE` + set `pueblo` (05, 06, 10, 39, 40); `urbanismo_informe.json` 0 fallos; `huecos` del log;
`asentar.json` casas flotantes/enterradas 0; `medir_capturas` (`pct_cesped` en 50 lado derecho < 10 %).
**Horas**: 1: 8 h (+2 h coordinador); 2: 16 h; 3: 6 h; 4: 12 h; 5: 12 h = **54-56 h, 2 agentes** (plan `urbanismo.py`;
escena + kits), 3 regeneraciones.

---

## Bloque 4 — Vegetación (siluetas a 20-120 m: 50, 51, 52; masas en laderas: 01, 21, 07)

**Objetivo medible**: `siluetas_20_120` x3 en 50/51/52 (hoy ~1 árbol cada 19 m de media, en masas de 4-8); dosel
continuo: en 51/52 >= 40 % de la ladera por encima del horizonte de la cámara cubierta por copas (hoy < 10 %); nada
"piruleta": ningún pino con copa de disco plano; 32 % del terreno por encima de 80 m plantado (hoy 0 %); árboles
quitados por `despeje_final`/asentar por pasada: 140 -> < 20 (el plan respeta las exclusiones); vegetación en el KN5
<= 1.8 M tris (hoy 1.74 M) a pesar de densificar x3 (v3 <= 250 tris/árbol).

**Cambios técnicos**:
1. **Plan por máscaras** (`03_blender/vegetacion.py`, nuevo, python del sistema, como `urbanismo.py`): lee
   `geometria_3d.json` + `urbanismo.json` (+ `terreno_mask.png` del bloque 3 si existe) y escribe `vegetacion_plan.json`
   (lista de `{especie, variante, x, y, z, rot, escala_xy, escala_z, tono}`) + `renders/qa/vegetacion_mapa.png`. API:
   `planificar(geom, urb, seed, cfg) -> plan`; `zonas(geom)` -> máscaras por pendiente, cota, orientación, distancia al
   mar / pueblo / pista / caminos; `masas(zona, especie, radio_poisson, claros)` (disco de Poisson por semillas +
   relleno, radio 3-5 m pinar, 7-9 m olivar, claros explícitos); reparto por hábitat: pinar en crestas y collados 60-180 m,
   encinar en umbrías > 25°, olivar en bancales 20-90 m junto al pueblo, cipreses en caminos y ermita, palmeras < 20 m
   junto a mar/paseo/casino, matorral/arbusto (sotobosque) en todo lo que pase de 30° y bajo las masas, roca desnuda
   donde `mascara_roca` > 0.6; densidad extra en la banda 20-120 m de las 6 cámaras de piloto y de las 5 postales (es
   lo que ve el jugador). Exclusiones iguales a las de hoy (pista + 12 m, calles, plazas, edificios, caminos, bancales,
   rocas, Loews, `zonas_excluidas`). Sustituye a `zona_montana` l.2223-2318, `zona_tierra` l.1711-1724 (árboles) y
   `zona_casino` l.2097-2119 (jardines), que pasan a `clone` del plan (coordinador). El MISMO plan alimenta `trees.txt`.
2. **Kit v3** (`assets/vegetacion_kit_v3.py`, misma API que v2: `build_pino(parent, alto, seed, variante)` -> `VEG_pino`
   con `ob["VEG_variante"]`, pivote en la base): copas en 2-4 "nubes" cóncavas de borde ondulado (el pino parasol de la
   película: copa plana, gruesa, bordes redondeados, huecos entre masas por donde pasa el cielo), ramas que salen de la
   copa, tronco el doble de grueso, escala NO uniforme (xy vs z), alturas por especie (pinos 14-22 m, palmeras 10-18:
   "formas exageradas"), tono por instancia vía material `MAT_VEG_<clave>_<k>` (3-4 tonos por especie: lo único que el
   writer exporta); modo `sin_alfa=True` (solo casquetes, <= 250 tris) para HOY, y modo con 4-8 planos de hojas con alfa
   (`MAT_VEGC_*`, UV, atlas renderizado por `assets/render_impostores_veg.py`) para cuando el writer admita alpha test.
   `test_vegetacion_kit_v3.py` con presupuesto (<= 250 tris/árbol, <= 80/arbusto) y previews. Cambio de `build_library`
   l.255-311 a v3 (coordinador, vía `assets/v2_aprobados.txt` -> `v3` o `load_mod` con sufijo).
3. **Suelo bajo las masas**: oscurecer el canal base del terreno bajo las masas del plan (`mascara_terreno.py` lee
   `vegetacion_plan.json`: -20 % de luminancia en un radio de 1.2 × copa) y sotobosque de arbustos v3 (80 tris) dentro de
   cada masa: es lo que convierte "árboles puestos" en "monte" (entender_vegetacion §6).
4. **Export (sección X)**: `ksPerPixelAT`/`ksTree` + `alphaTested=1` + `ksAlphaRef 0.5` + PNG RGBA con bleed + `castShadows
   = 1` para `VEG_` (planos con alfa sí sombrean en AC) + troceado por área (frustum culling) + nombres `DECO_MAT_VEGC_*`.
5. **TreeFX (extra CSP, última prioridad)**: `03_blender/exportar_trees_txt.py` (python del sistema) desde
   `vegetacion_plan.json` -> `extension/trees/trees.txt` con `configure:` por zona y `pos = x_b, z_b, -y_b` (web_treefx
   §3.4); FBX por especie (LOD A = v3 con hojas, B = v3 casquetes, C = v2 o billboard) con `bpy.ops.export_scene.fbx`
   (excepción a "sin bpy.ops": Q8); `.bin` SOLO con Content Manager en el PC del amigo (no hay CLI: web_treefx §5);
   `[TREES] LIST_0` + `SURFACE_MATERIALS = <materiales del terreno>` + `[SHADER_REPLACEMENT] MATERIALS = MAT_VEG_?,
   IS_VISIBLE = 0` en `ext_config.ini` (generador en `color_ac.py`: petición export). Prueba de 3 árboles ANTES de nada.

**Dependencias y orden**: 1 || 2 (dos agentes); 3 tras bloque 3; `build_library` v3 y las zonas del plan: coordinador;
bloque 1 ANTES de congelar el plan (las máscaras de pendiente cambian) o re-ejecutar `vegetacion.py` después (es
determinista: 10 s). `revisar_flotantes`/`revisar_invasores`/asentar siguen (miran el pivote); con tarjetas, `copa_calzada`
debe medir la anchura real (ancho del plano).
**CSP**: esencial = plan + v3 `sin_alfa` (+ alpha test en el writer); extra = TreeFX, viento, `ENABLE_TREES_LIGHTING`.
**Riesgos**: tris si se densifica con v2 (x3 = 5 M: por eso v3 primero); halos de alfa en AC (bleed + ksAlphaRef); "cartón"
al pasar a 1.4 m (mezclar con v3 opaco en los primeros 20 m); el bosque cambiaba con cada `Random(42)` consumido: el plan
JSON lo fija; `MODEL_REPLACEMENT HIDE` con CSP viejo podría ocultar sin sustituir (verificar en el PC del amigo).
**Verificación**: AB `BASE` + set `vegetacion` (01, 07, 10, 21, 34_general) en modo normal y `--modo-ac` (sin sombras de
vegetación: lo que verá el amigo HOY); `vegetacion_mapa.png`; `asentar.json` `por_familia` y `arboles_quitados`; tris
por familia en `kn5_check`.
**Horas**: plan 12 h; kit v3 + test 14 h; impostores 6 h; suelo/sotobosque 4 h; coordinador (zonas + library) 4 h;
trees.txt + FBX 7 h (extra) = **41-47 h, 2 agentes**, 2 regeneraciones. Export: 10-12 h (sección X).

---

## Bloque 6 — Agua y costa (54, 49, P1, P2, P3, P5; aéreas 01, 14, 16, 22)

Desde el coche el mar aparece grande solo en 54, P3 y P5 (y de reojo en 49/52): lo que cuenta es el degradado hacia la
orilla, la línea de costa sin almenas y la escollera del puerto. El puerto-llanta solo se lee en 01: va después.

**Objetivo medible**: en 54/P3 el agua muestra >= 3 bandas de tono entre la orilla y el horizonte (medir hue por
columnas); borde tierra/mar sin escalones de 4 m en 14/22 (la franja `COSTA_orilla` los tapa); en P5/02 el dique tiene
bloques visibles (>= 600 piezas) y la bahía >= 10 veleros con velas izadas; `Roughness` del agua 0.04 -> 0.08 (54 deslumbra).

**Cambios técnicos** (entender_agua §10.1-10.5, resumidos):
1. `03_blender/generar_mar.py` (python del sistema, tras `preparar_geometria`): `texturas/mar_color.png` 1024² por
   profundidad y `d_costa` (turquesa 0-2 m -> azul profundo > 25 m, ruido de 60 m, franja de espuma `d_costa < 8`).
   `construir_pista.py` l.1476-1513: `AGUA` en rejilla de 32 m con UV planar + `AGUA_lejos` (anillo a 9 km, color plano);
   `MAT_agua` con la imagen como color (base blanco), alpha 0.84, bump; `AGUA_fondo` con `MAT_fondo_marino` (arena clara).
   Petición export: `TEX_MAX` 2048 para `MAT_agua`; CSP extra: `DepthAware = 1`, `[BOUNCED_LIGHT] CAUSTICS = 1`.
2. `COSTA_orilla` (franja de 6 m a cada lado de `coastF = 0.5`, 3 bandas: arena mojada, arena clara, espuma) en
   `construir_pista.py` tras el TERRENO; `zona_costa()` en `integrar` (coordinador): rocas de orilla cada 12-20 m donde la
   pendiente > 30 % o a < 60 m de dique/muelles (`vegetacion_kit.build_roca`, tono caliza), unidas por material
   (`COSTA_rocas`); alta en `revisar_flotantes` como marinas y en `revisar_fisica_ac.NO_OBSTACULO` (petición).
3. `assets/escollera_kit.py` `build_bloques_a_lo_largo(parent, puntos, ancho, z_agua, seed)` (superelipsoides 1.2-3 m,
   3 tonos, 30 % bajo el agua, ~48 tris/bloque) usado por `puerto_kit.build_dique(bloques=True)`, por el `tipo='muelle'`
   de `caminos_kit` y, cuando toque, por la cala del lazo y la plataforma del casino (la "losa blanca" de 36).
4. Flota: `build_velero(velas='izadas')`, 7 tamaños en la marina, 10-14 veleros en la bahía escorados al mismo viento,
   3-4 lanchas con estela; nombres únicos por barco (para animarlos con CSP después).
5. **Después (aéreo)**: puerto-llanta (buje + 5 radios + pestaña, dragado a -6 m en `terreno_montana`): 10 h que solo se
   ven en 01 y en la toma 60. Se deja para el final o fuera.

**Dependencias**: bloque 1 (la costa cambia con los acantilados y el cabo del McLaren) antes de 1-2; bloque 3 (paleta
de la caliza) para 3. **CSP**: esencial = 1-4 (el degradado va en la textura); extra = SEA (ya), cáusticas, barcos
animados (`[ANIMATED_...]` tipo train, bloque 9). **Riesgos**: `aplicar_texturas.familia_de` l.97 (`agua`) volvería a
meter su bump: coordinar; `eliminar_sumergidos` con objetos a z 0 (exentar `COSTA_`, `AGUA_lejos`); el ruido de olas de
40 m se repite desde el aire.
**Verificación**: AB `BASE` + set `agua_costa` (02, 14, 16, 22, 36_general, 46, 47, 47b, 60, 61); `revisar_flotantes`;
log de `zona_puerto` (barcos colocados / posibles).
**Horas**: 1: 8 h; 2: 10 h (+3 h coordinador); 3: 8 h; 4: 6 h = **32-35 h, 2 agentes**, 2 regeneraciones; 5 (llanta): +10 h
si se decide hacer.

---
## Bloque 7 — Público y relleno (52, P5, 53; aéreas 01, 09, 21, 26, 42)

Desde el coche lo que da escala en los tramos vacíos (52, 51, 09) son aparcamientos llenos junto a la pista, bancales
bien asentados y, al mirar al mar (49, 52, 54, P2), un horizonte con costa lejana. Villas, viñedos, carpas, camping y
torres costeras son relleno de aéreas: después.

**Objetivo medible**: coches con cara 70-90 -> >= 250 (log de `zona_coches`: filas 1 -> >= 10); en 52 y P5 >= 1
aparcamiento o grada visible a < 120 m; bancales "bandeja" 0 (desnivel en `asentar.json['bancales']` <= 0.3 m);
horizonte: en 49/52/54/P2 la línea mar/cielo tiene silueta de costa en >= 60 % del ancho; `revisar_fisica_ac`
barreras falsas = 0.

**Cambios técnicos**:
1. **Horizonte** (independiente, cambia todas las vistas que miran al mar): `zona_montanas_fondo` l.2486-2533 deja de hacer
   `return` y pasa a `zona_horizonte`: 7-9 cordilleras `montanas_fondo_v2.build_cordillera(largo 1400-1800, n_picos 5-7,
   alto 380-520, pie=True)` en un arco de 3.2-4.5 km cubriendo 200° (abierto 160° al S/SO: desde 54/14 debe seguir
   viéndose mar abierto), 2 planos de profundidad, 6-8 lomas de costa a 2.4-2.8 km con 2-3 pueblecitos-silueta y un
   faro; `mejorar_materiales.py`: mezcla con el color del cielo del horizonte al 35-55 % según distancia (perspectiva
   atmosférica horneada: en AC a pelo no hay niebla fiable). <= 250 k tris (`res 0.5`). Exentar `MONT_` en
   `revisar_flotantes.EXENTOS` (hoy solo `MONT_pena`) y `eliminar_sumergidos`. Petición export: token sin sombra `MONT_`.
2. **Aparcamientos explanados** (sustituyen al `sitio_ok` de `zona_coches` l.2359-2404 que hoy solo encuentra 1 sitio):
   8-12 losas de grava 30×14 m con `explanar()` + cinta de tierra de acceso con valla (como `_ramal_camara`/`poner` de
   `zona_camaras` l.6088-6166), en exteriores de curva a 16-30 m del borde, 2-3 filas de 6 por losa, muro de piedra seca
   en el borde bajo (que no sea "caja suelta"); 2 de ellas en el cono de 52 y de P5. Variación en `coches_kit_v2`: opción
   `bandera` (24 tris), `mirada`, escala 0.92-1.08 en `build_fila_aparcada`. Público de gradas (`_pub_coche`): 6 siluetas,
   10 colores, bandera en el 20 %. Terraza del casino: 10-16 `build_coche_lujo` con mesas/sombrillas (53/P4 lo ven).
   Petición export: unión por material de `COCHE_fila*` (draw calls).
3. **Bancales tallados** (51, 07, 48): `03_blender/bancales_spec.py` ANTES de `preparar_geometria` elige 6-10 laderas
   (pendiente 10-35 %, sin pista a < 40 m, sin solares, sin senderos) y escribe polilíneas por curva de nivel;
   `terreno_montana.construir` TALLA el escalón (como las terrazas del pueblo); `zona_bancales` clona `build_bancal` por
   tramos de 14-20 m con olivos (o `olivos=False` si el plan de vegetación los pone). 40-80 bancales con muro apoyado.
   Toca `terreno_montana`: mismo agente que el bloque 1.
4. **Después (aéreo / lejos del coche)**: villas con piscina (`villa_kit`, 6-10, cada una sobre explanada), viñedos
   (`build_vinedo`), carpas de hospitality en el paddock (`build_carpa`, 6-8; se ven en 42/30, no desde el coche salvo
   P5 de lejos), camping en la ladera de tierra (`camping_kit`), torres costeras (3) y faro 2. Todos son raíces nuevas:
   alta en `revisar_flotantes.EXENTOS`, `SOPORTE_PREF`, `despeje_final.EDIF_PREF`, `exportar_ac` (1WALL donde el coche
   llega). ~20-25 h; solo si sobra tiempo tras los bloques 1-6.

**Dependencias**: 1 ninguna (puede ir el primero); 2 tras bloque 1 (explanadas sobre el macizo final) y bloque 5
(balcones); 3 con el agente de `terreno_montana`. **CSP**: todo esencial. **Riesgos**: `despeje_final` trata `COCHE_`
como prop desechable (losa en `EDIF_PREF`); `revisar_coches` asienta cada coche (orden explanar -> clonar); el anillo
tapa el "mar infinito" de 01 (es lo que pide el usuario, pero mirar 54/14).
**Verificación**: AB `BASE` + set `relleno` (09, 21, 26, 42, 48, 10, 39) + `horizonte` (13, 14, 16, 08, 19, 63);
`nada_en_pista`, `revisar_fisica_ac`, `asentar.json`.
**Horas**: 1: 8 h; 2: 10 h (+3 h coordinador); 3: 10 h = **28-31 h, 2 agentes**; 4: +20-25 h si se hace.

---

## Bloque 8 — Carificación (53, P4, 02/29; aéreas 19/20/36)

**Objetivo medible**: en 53 y P4 se cuentan >= 3 elementos "coche" en el casino (estatuas, rejilla, faros); chimeneas-escape
en >= 80 % de las casas visibles en 50/06 (ya existen en `casas_kit_v2` l.709: comprobar que se ven); monumentos
(casino, campanile, ayuntamiento, pórtico de meta) un 30-50 % más grandes SIN fallos de QA nuevos.

**Cambios técnicos**:
1. Casino (`assets/casino*_v2.py`): `build_estatua_coche(parent, seed)` (~1.5 k tris, coche genérico sin logos sobre
   pedestal) en las 4 esquinas de la meseta; rejilla de radiador y faros en la fachada noble (geometría, 2 materiales
   cromo/vidrio ya existentes en `casas_kit_v2`); lo mismo, más discreto, en hotel y ayuntamiento (`edificios_civicos_v2`).
2. Escala de monumentos: parámetro `escala` en los constructores (casino 1.35, campanile 1.4, ayuntamiento 1.3, pórtico
   1.2) y re-explanar (`explanar_edificios`, HOTEL con 1.2) — comprobar `casa_pista`, `casa_casa` y la elipse del peñón
   (`elipse_casino` 118 x 78 m: el casino crece dentro de la meseta; si no cabe, 1.2).
3. **Después / opcional**: peñón del casino con silueta de Fiat Topolino vista desde el mar y el aire (19/36/01): hay
   código legado (`penon_topolino.py`, no en escena); choca con `roca_casino` (256 columnas, carretera de bajada con
   2 horquillas y espigón): rehacer el perfil radial para que lea como un coche es un proyecto propio (20-30 h, riesgo
   alto para la bajada y la cala). Solo se ve desde el aire/mar: fuera de esta fase o pregunta Q10.
**Dependencias**: bloque 5 (kits de fachada) y 2.7 (peñón). **CSP**: esencial. **Riesgos**: QA del casino (`casino_contorno`),
tris. **Verificación**: AB set `carificacion` (10, 19, 20, 36_general, 53, 58); `revisar_urbanismo`.
**Horas**: 1: 8 h; 2: 4 h = **12 h, 1 agente**; 3: +20-30 h si se decide.

---

## Bloque 9 — CSP y ambiente (TODO extra: nada de esto se ve en AC a pelo)

**Objetivo medible**: `ext_config.ini` con las secciones de abajo, cada una `ACTIVE = 0/1` por separado, inerte sin CSP;
en Blender, materiales con nombre exclusivo para cada función; en el PC del amigo: 3 árboles TreeFX en su sitio, luces
encendidas de noche con Sol y con Pure, rotor girando, pantalla con cámara, FPS con 12 coches >= los de v1.0.

**Cambios técnicos (Blender, ya; baratos, ~6 h)**: materiales exclusivos y `ksEmissive = 0` en el KN5 (si se hornea
emisivo brilla de día en vanilla): `MAT_cesped` (jardines, rotondas, Loews, plaza del casino) para `[GRASS_FX]
GRASS_MATERIALS = MAT_cesped` + `OCCLUDING_MATERIALS = asfalto/adoquín/acera`; `MAT_farola_luz`, `MAT_casino_luz`,
`MAT_guirnalda_luz`, `MAT_pit_luminaria` (bombillas pequeñas y separadas: `LIGHT_SERIES` por `MATERIALS` +
`CLUSTER_THRESHOLD 6-10` funciona sobre mallas fusionadas) con `CONDITION = NIGHT_SMOOTH`; `MAT_heli_rotor` único por
helicóptero y `MAT_pantalla_1/2` con textura real 1024x576 (imagen estática "LIVE" que se ve sin CSP) y UV 0..1 en la
cara frontal, marco con otro material.
**Cambios técnicos (04_export, sección X)**: generador de secciones en `color_ac.generar_ext_config` l.872-886:
`[Material_Water]` (ya) + `UseAlphaFromDiffuse/DepthAware` + `[BOUNCED_LIGHT] CAUSTICS = 1`, `[GRASS_FX]`, `[LIGHT_SERIES_*]`
+ `[MATERIAL_ADJUSTMENT_*]` + `[LIGHT_POLLUTION]`, `[DISPLAY_*] MODE = CAMERA, CAMERA_0_TARGET = CLOSEST_CAR`,
`[WRAP_MESHES_*]` + `[ANIMATED_*]` (rotor con `.ksanim` en bucle; barcos y dirigible tipo "train" con camino oculto) o,
más limpio, prefijo `ANIM_` en `KEEP_PREFIXES` del writer para que esas piezas salgan como nodo propio; `[TREES]` +
`IS_VISIBLE = 0` (bloque 4.5); `[SHADER_REPLACEMENT]` nm4 + tilingFix (bloque 3). Borradores literales en
web_csp_agua_luces §2-§6 y §10.
**VAO** (`acc-bakeryoptix` v22, 1.8 MB, Vulkan RT o CPU Embree, sin flags: `bakeryoptix.exe porto_corsa.kn5` +
`baked_shadow_params.ini` con `BAKE_AS_TREES`, `EXCLUDE_FROM_BAKING` de las mallas invisibles, `TUNNEL_FIX` para el túnel):
se ejecuta AQUÍ sobre el KN5 final (permiso de descarga Q3; 10-60 min en CPU con 5 M de tris), produce
`porto_corsa.vao-patch`, va al zip con instrucciones de copia a `assettocorsa/extension/vao-patches/`.
**Pure/Sol**: ninguna clave de pista distingue uno de otro; solo prueba visual en el PC del amigo con el mismo KN5 +
ext_config (dejar la palanca `[MATERIAL_ADJUSTMENT_0]` por familias, ACTIVE = 0).
**Dependencias**: todo lo anterior (nombres de materiales), 04_export abierto, CSP confirmado (Q1). **Riesgos**: con
CSP viejo (< 0.1.79) `[TREES]` se ignora pero `HIDE` quizá no (pista sin árboles): comprobar antes de activar; KN5 aparte
para animados desaparece sin CSP (no usar). **Verificación**: solo en el PC del amigo (lista de web_csp §11 y web_treefx §9).
**Horas**: Blender 6 h; export/ext_config 10 h; VAO 2 h; trees.txt/FBX 7 h (bloque 4) = **18-25 h, 1 agente**, al final.

---

## Sección X — Lista cerrada para 04_export (cuando el equipo del zip v1.1 abra; 1-2 agentes, 30-40 h)

Se entrega como UNA tanda, con un **KN5 de ensayo** (plano de 4 triángulos con el material multicapa + 1 árbol con alfa
+ 1 nodo `ANIM_`) que el amigo prueba ANTES del circuito. En orden de valor para el jugador:
1. Shader, props y samplers POR MATERIAL (`escribir_texturas_y_materiales` l.301-339) leídos de custom properties
   `m['ac_shader']`, `m['ac_props']`, `m['ac_samplers']` que ponen los kits; por defecto lo de hoy.
2. Terreno: plan A `ksMultilayer_fresnel_nm` (txDiffuse base×AO, txMask RGBA 2048 sin tintar ni recortar: excepción a
   `TEX_MAX`/`imagen_lineal`, 4 detalles 1024, txDetailNM) con la UV planar del bloque 3; plan B `repartir_terreno()` por
   cara. `color_ac.separar_roca_terreno` con imagen mientras tanto; `ROCA_NZ/ROCA_ATR` alineados al bloque 2.
3. Texturas "tal cual" por material (`m['ac_tex_raw']`) y por objeto (atlas horneados de McLaren, lazo, peñón: Smart UV +
   bake Diffuse×AO en Cycles por la cola, `hornear_rocas.py`), sin pasar por `calibrar_todos`.
4. Alpha test: `ksPerPixelAT`/`ksTree`, `alphaTested = 1`, `ksAlphaRef 0.5`, PNG RGBA con bleed, `castShadows = 1` para
   `VEG_` con alfa, troceado por área de `DECO_MAT_VEGC_*`.
5. `KEEP_PREFIXES` + `ANIM_` (nodo propio con pivote) y tokens sin sombra `MONT_`, `HORIZ_`, `COSTA_`; `1WALL_` nuevos
   (`CALLE_bolardo`, carpas, muros de villa); `NO_OBSTACULO` nuevos en `revisar_fisica_ac`.
6. `TEX_MAX` 2048 solo para `MAT_agua` y `txMask`; `TEX_SIZE` 1024 para familias roca/caliza/asfalto (12.5 -> ~45 MB).
7. `color_ac._REGLAS` l.309-331: subcadenas `matorral`, `seca`, `cesped`, `caliza`; re-medir objetivos/albedos UNA vez al
   final (`render_ac.py` + `medir_objetivos.py` + `medir_albedo.py`).
8. `kn5_check.py`: check 9 "shader conocido + samplers/props esperados por shader" (`SHADERS = {...}`), aviso de texturas
   no potencia de 2 o > 2048, materiales sin uso, recuento de tris por familia.
9. `generar_ext_config` con las secciones del bloque 9 (cada una con `ACTIVE`).
10. Unión por material de `COCHE_fila*`, `COSTA_rocas`, `PUERTO_dique_bloques`; decidir `castShadows` de `1GRASS_terreno`.
Lo que SOLO se valida en el PC del amigo: que el shader multicapa cargue, mipmaps de PNG, alfa test y sombras con alfa,
`lodIn/lodOut`, VAO, TreeFX, luces, displays, FPS con 12 coches (si caen: LOD por `lodIn/lodOut`, agrupar por material,
`ENABLE_TREES_LIGHTING = 0`).

---

## 10. Orden recomendado y calendario

Principio: cada fase termina con UNA regeneración completa (`pipeline_escena.sh`, ~1 h de cola) + AB del `BASE` en modo
normal y `--modo-ac` + medidas; entre regeneraciones todo se prueba en python del sistema (preparar_geometria, urbanismo,
vegetacion, mascara_terreno: segundos) y con los tests de kit (previews por la cola, 1 hueco cada uno).

| Fase | Días (calendario) | Agentes en paralelo (cola 6) | Qué |
|---|---|---|---|
| A | 1 | 1 | Bloque 0 (capturas AB, postales 55-59, modo AC, medidas) |
| B | 2-5 | 5: 3 (bloque 3) + 1 (bloque 2.1-2.2 material/máscara) + 1 (bloque 1.1-1.2 tierra + berma) | paleta, máscara por texel, caliza compartida, reglas de tierra, berma. Regeneración + AB |
| C | 6-10 | 5: 1 (bloque 1.3-1.4 macizo + acantilados) + 1 (2.4 McLaren) + 1 (2.3 bancos + 2.5 afloramientos) + 2 (bloque 5.1-5.3) | relieve cercano, McLaren, afloramientos, pueblo denso. Regeneración + AB |
| D | 11-15 | 5: 2 (bloque 4.1-4.3) + 2 (bloque 6.1-6.4) + 1 (bloque 7.1 horizonte + 7.2 aparcamientos) | vegetación por plan + kit v3, agua/orilla/escollera, horizonte. Regeneración + AB |
| E | 16-19 | 4: 1 (2.6 lazo) + 1 (2.7 casino + 8) + 1 (5.4-5.5 atlas, soportales) + 1 (7.3 bancales + 1.6 erosión opcional) | segundo nivel. Regeneración + AB completo (57 + postales) + re-medir color_ac |
| F | cuando 04_export abra; 5-8 días | 1-2 | Sección X + KN5 de ensayo -> amigo -> KN5 completo -> VAO -> ext_config (bloque 9) -> zip v1.2 |

Horas-agente: bloque 0: 9; 3: 36; 2: 70; 1: 38 (+10 erosión); 5: 55; 4: 45; 6: 34; 7: 30; 8: 12; 9: 22; coordinador
(integrar_escena/preparar_geometria/zonas nuevas): ~25; sección X: 35. **Total ≈ 410 h-agente (≈ 360 sin erosión,
llanta, villas/camping, Topolino ni lazo H7)**. Calendario: **3-4 semanas de Blender** con 4-5 agentes en paralelo
(limitado por los ficheros seriales `terreno_montana.py`, `urbanismo.py` e `integrar_escena.py` del coordinador y por
~12 regeneraciones completas) **+ 1-2 semanas de export** que dependen de cuándo se cierre v1.1 y del bucle de prueba
con el amigo. Si hay que recortar, la fase E entera es prescindible: con A-D el jugador ya ve el 80 % del cambio.

Qué dejar FUERA o para después (resumen, con el motivo "no se ve desde el coche" o "coste/riesgo"):
- Erosión hidráulica (1.6): solo aéreas y P2; al final, opcional.
- Cabo bajo la zaga del McLaren (2.4.a): mejora P5/01/02 pero mueve la costa junto al puerto: Q7.
- Roca del lazo H7 (2.6) y peñón 1.5 m (2.7): aéreas/parciales; fase E.
- Puerto-llanta (6.5), villas, viñedos, carpas, camping, torres costeras (7.4): aéreas; si sobra tiempo.
- Silueta Topolino del peñón (8.3): proyecto propio de riesgo alto; fuera salvo Q10.
- Túnel por el centro de la rueda hundiendo el coche 8 m: se sustituye por el portal de 11-12 m (Q6).
- TreeFX, luces, animados, pantallas, cáusticas, VAO, nm4 (bloque 9): extras CSP, última fase.
- Decals con alfa en fachadas (5.4): tras la sección X; mientras, geometría opaca.

## 11. Preguntas que SOLO el usuario puede responder

Q1. ¿El amigo usa CSP y qué versión (>= 0.1.79)? ¿Y Content Manager con developer mode? Decide si el bloque 9 y TreeFX
    entran en esta fase o en otra entrega. Sin respuesta: se hace todo lo esencial y el bloque 9 queda preparado pero inactivo.
Q2. ¿Permiso para descargar texturas CC0 (Poly Haven + ambientCG, licencia CC0 sin atribución)? Mínimo útil: 4 del
    terreno (rock_06, withered_grass, Ground105, aerial_grass_rock) ≈ 19 MB en 1K-JPG; lista completa de 13 ≈ 49 MB en 1K
    (186 MB en 2K: no compensa, el writer recorta a 1024). Sin permiso: tiles PIL procedurales (misma API, look más "dibujo").
Q3. ¿Permiso para descargar y ejecutar aquí `acc-bakeryoptix` build-v22.zip (1.8 MB, sin LICENSE en el repo, cabeceras
    BSD de NVIDIA) para el VAO? Solo tiene sentido si Q1 = sí.
Q4. ¿Cuándo cierra el equipo del zip v1.1 y se puede tocar 04_export? La sección X (lo que hace que TODO se vea en AC)
    depende de ello; mientras, se entrega como lista.
Q5. "Bajada a la horquilla de la fuente": ¿es la rotonda Loews (s 3564, con fuente/palmera) o la horquilla C26 de tierra
    (s 2364)? El plan asume la Loews.
Q6. Túnel por la rueda: ¿vale con un portal de sillería de 11-12 m que llegue a los radios (barato) o quieres que la
    pista pase por el CENTRO de la llanta (hundir el coche ~8 m: Boolean, encaje y revisar_tunel otra vez, +10-14 h, riesgo)?
Q7. ¿Aceptas que el McLaren tenga un CABO de tierra bajo la zaga (300-350 m) aunque cambie la costa a 150-250 m del
    puerto y la dársena quede más cerrada? Es lo único que quita el "islote" en P5/01/02/13.
Q8. ¿Autorizas la excepción "sin bpy.ops salvo render" para `bpy.ops.export_scene.fbx` (FBX de árboles para TreeFX)?
Q9. Monumentos +30-50 %: ¿también el casino (hoy encaja en la meseta de 118 x 78 m; con 1.35 puede no caber) o solo
    campanile/ayuntamiento/pórtico?
Q10. ¿La silueta Topolino del peñón del casino entra en esta fase (20-30 h, riesgo para la bajada y la cala) o se deja?
Q11. ¿Tamaño máximo aceptable del KN5/zip? Hoy 355 MB / 164 MB; con máscara 2048 + detalles 1024 + atlas de rocas +
    horizonte estimo 400-430 MB / 190 MB.
Q12. ¿Prefieres juzgar las capturas en modo "Blender bonito" o en modo "fiel a AC"? El plan entrega los dos, pero el
    criterio de "cerrado" de cada bloque debería ser el modo AC.
Q13. ¿Se puede ampliar `zonas_excluidas` del McLaren 20-40 m (menos casas en `pueblo_subida_ladera`, s 716-888) si el faldón
    lo exige, o manda el pueblo?

## 12. Qué desaconsejo ("no hacer") y por qué

1. **Hydra** (add-on de Blender): engancha el contexto OpenGL de la ventana, no funciona en `--background` ni está probado
   en 5.x; rompería "todo se genera por código". Erosión: NumPy propio o nada.
2. **`ksMultilayer_fresnel_nm4` escrito en el KN5**: es shader de CSP, no vanilla, y los 4 samplers de normal no están
   documentados; en AC a pelo puede dejar el terreno sin material. Vanilla `_nm` en el KN5, nm4 solo por ext_config.
3. **AO por color de vértice**: el vértice KN5 no tiene color; CSP tampoco lo lee del KN5. AO en textura (vanilla) + VAO (CSP).
4. **Bajar la rasante de tierra al 12-15 %**: ya está al 16.5 % y con 12 % la cima BAJA (~105 m); el desnivel que se ve
   es del terreno lateral, no de la rasante. Solo suavizar los apex de las horquillas.
5. **Erosionar antes de fijar las reglas de tierra/berma/acantilados**: habría que recalibrar la erosión con cada cambio
   de macizo; va la última.
6. **Modificador Bevel en el terreno o en 216 casas** y **subdividir TERRENO a 2 m globalmente**: 7 M de vértices ya; el
   "bisel" sale de normales suavizadas y de la AO; la subdivisión, como mucho, en una banda de 20 m junto a la pista.
7. **Densificar el bosque x3 con el kit v2** (400-900 tris/árbol): 5 M de tris de vegetación. Primero v3 <= 250 tris.
8. **Generar los `.bin` de TreeFX aquí o usar packs de terceros**: no hay CLI (solo CM en el PC del amigo) y los packs
   son fotorrealistas y con licencia ajena.
9. **Hornear `ksEmissive > 0` en el KN5** para las luces: en AC vanilla brillan de día. `ksEmissive = 0` + `MATERIAL_ADJUSTMENT`.
10. **KN5 aparte para rotor/barcos/dirigible** (`MODEL_REPLACEMENT`): sin CSP desaparecen. Nodo `ANIM_` en el KN5 principal
    (quieto sin CSP, en pose creíble).
11. **`ksGrass` para setos/arbustos**: CSP lo oculta con Grass FX.
12. **Puerto-llanta, villas, viñedos, carpas, camping, Topolino antes de los bloques 3/2/1/5/4**: solo se ven desde el aire;
    el usuario pidió "no añadir objetos sin más: primero relieve, integración, paleta y densidad".
13. **Niebla de mundo en Blender** para "ambiente": el director ya lee las manchas de 20 m como bruma; la lejanía se hornea
    en el color del horizonte (7.1), que sí viaja al KN5.
14. **Texturas 2K/4K**: el writer recorta a 1024/512; cuadruplican descarga y KN5 sin verse. 1K-JPG.
15. **Renderizar las 57 capturas en cada iteración**: 2 min de cola por pasada y ruido; set reducido por bloque (12-18
    tomas) y las 57 solo al cerrar cada fase.
16. **Tocar la Loews, el corredor de la pista (`techo`/`suelo`), el viaducto o `04_export` antes de que abran**: están
    protegidos por construcción y por el equipo del zip; cualquier cambio ahí es regresión segura.
17. **Cambiar `view_transform`/exposición de Blender** para que las capturas "queden bonitas": invalida todas las medidas
    de `color_ac` y no cambia nada en AC.
18. **Mover la rejilla del terreno (`rejilla_de`) o `cell`**: rompe la referencia congelada de la Loews (`_loews_terreno.npz`)
    y todos los inspectores.
