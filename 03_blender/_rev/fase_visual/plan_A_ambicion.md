# Plan A — FIDELIDAD MÁXIMA al plan del usuario (fase visual de Porto Corsa)

Arquitecto técnico, 04/10/2026. Ángulo: cumplir los 9 bloques de `PLAN_USUARIO.md` con la máxima ambición visual
(formas exageradas y suaves + superficies ricas), aunque exija cambiar el writer KN5 o añadir shaders nuevos.
Fuentes: `PLAN_USUARIO.md`, `director_final.md`, `RONDA15_PLAN.md` (convenciones y estado), los 11 informes de
`_rev/fase_visual/` (entender_terreno/materiales/vegetacion/pueblo/rocas/agua_publico_capturas, web_treefx,
web_csp_agua_luces, web_multilayer_vao_erosion, web_texturas_cc0) y las capturas 01, 07, 15, 32, 36, 40, 49, 51, 54.
No se ha modificado ningún fichero del proyecto ni se ha lanzado Blender. Las líneas citadas (l.) son las de los
informes del 04/10.

Convención de etiquetas: **[E]** = esencial, se ve en AC "a pelo"; **[X]** = extra que solo actúa con CSP y que no
rompe nada sin él; **[W]** = exige el writer v2 (`04_export`, solo cuando el equipo del zip v1.1 haya cerrado);
**[U]** = necesita una decisión o un permiso del usuario (lista en la sección 13).

---

## 0. Diagnóstico en una frase y decisiones de arquitectura

Diagnóstico (director + informes + capturas): el relieve es tímido y plano (lomas suaves, desmontes-cantera,
McLaren en un islote), las superficies son planas (un color por material, sin UV, sin textura, sin AO, sin bisel),
la roca es procedural y no sobrevive al KN5 (todo `ksPerPixel` + 1 `txDiffuse` tintado de 512 px), los árboles son
piruletas sin sombra, el pueblo tiene terrazas vacías y "muros-aleta", el agua es un quad con ruido, el público
cabe en una fila, y no hay horizonte. Capturas 32 y 15 lo resumen: crema plástico con "franjas de pintura" y una
pared gris sin textura; 01 y 07: cono verde uniforme con parches grises; 51: lomas verdes, desmonte gris borroso.

Decisiones que condicionan todos los bloques (se justifican en los bloques):

- **A1. Una paleta única** `03_blender/paleta.json` (nombre -> RGB lineal + sRGB + familia AC) leída por
  `construir_pista`, `generar_texturas`, `aplicar_texturas`, los 4 kits de roca, `casas_kit_v2`, `vegetacion_kit_v3`.
  Regla: `diffuse_color` o Base Color sin enlazar = la media lineal que se quiere ver (lo que lee el writer).
- **A2. El terreno pasa de "atributo por vértice" a "máscara por texel"**: UV planar real en `TERRENO`
  (`construir_pista`), `mascara_terreno.py` (numpy, python del sistema) que escribe `texturas/terreno_mask.png`
  RGBA 4096² (0.5 m/texel sobre la rejilla de 2068 x 2060 m) y `texturas/terreno_diffuse.png` 2048² (paleta x AO
  del heightmap). Blender mezcla 4 detalles por esa máscara (lo que verá AC); el KN5 lleva `ksMultilayer_fresnel_nm`
  [E] y `ksMultilayer_fresnel_nm4` + `tilingFix` por `ext_config` [X]. Es lo que elimina de raíz el defecto 4 del
  director (dientes de sierra, escaleras, hierba estirada) y el 3 (desmontes pintados).
- **A3. Writer v2** (`04_export/kn5_writer_opt.py`, SOLO tras el cierre de v1.1): shader/props/samplers POR
  material (custom property `m['ac_shader']` + `m['ac_props']` + `m['ac_samplers']` escritas desde Blender),
  texturas "tal cual" (sin tintar) y `TEX_MAX` por material, PNG RGBA con alfa conservado (+ bleed) y
  `alphaTested`/`ksAlphaRef`, DDS BC1/BC3 con mipmaps para las > 1024, `KEEP_PREFIXES` + `ANIM_`, `lodIn/lodOut`
  por malla, troceo de la fusión DECO por área (celdas de 200 m), `castShadows = 1` para la vegetación con alfa,
  `kn5_check` con la comprobación 9 (shader conocido + samplers/props esperados + tamaño/potencia de 2). Todo el
  trabajo de Blender se prepara ANTES con esas custom properties para que, cuando se abra `04_export`, el cambio
  sea mecánico. Hasta entonces el KN5 sale como hoy y las capturas de Blender son el juez.
- **A4. Un solo material de caliza** `NG_caliza_estratos` (node group, coordenadas de MUNDO) compartido por
  terreno, roca del lazo, peñón, McLaren y afloramientos; horneado a texturas por objeto (`hornear_rocas.py`,
  Cycles) para que AC vea estratos, grano y AO.
- **A5. Los "planes" se calculan en python del sistema y Blender solo ejecuta**: `urbanismo.py` (ya), más
  `vegetacion.py`, `bancales_spec.py`, `generar_mar.py`, `mascara_terreno.py`. Un plan = un JSON revisable = la
  misma fuente para el KN5 y para `trees.txt`.
- **A6. Capturas antes/después congeladas** (`_rev/capturas_ab.py`, `_rev/montaje_ab.py`,
  `_rev/tomas_capturas.py`, hojas por bloque en `renders/ab/<bloque>/`): la cámara se congela en JSON la
  primera vez y el "después" NO pasa por `camara_segura`. Set BASE = 01 + las 6 de piloto (s300, 800, 1700, 2900,
  3400, 4150) + las 5 postales (04/08/13/11/02).
- **A7. Esencial vs extra**: todo lo que da forma, color, silueta, sombra y densidad vive en el KN5 [E]; TreeFX,
  VAO, GrassFX, luces, animados, pantallas, cáusticas y nm4 van en `extension/` [X] y se degradan solos.
- **A8. Presupuesto**: hoy 5.26 M tris (33 % vegetación piruleta) y 355 MB. Objetivo final ≤ 6.5 M tris, KN5 ≤ 450
  MB, texturas ≤ 120 MB; vegetación v3 ≤ 0.9 M tris con el triple de densidad.
- **A9. Ficheros del coordinador**: `integrar_escena.py` y `preparar_geometria.py` solo los edita el coordinador;
  cada bloque entrega sus zonas como módulos con API fija + `test_<modulo>.py` + previews, y un parche corto para
  el integrador.
- **A10. Formas exageradas**: el usuario pide monumentos +30-50 %; se extiende a cumbre del macizo (210 -> ~300 m
  nominales), pinos parasol (12 -> 18-24 m), escolleras, torres y faro; la rejilla del terreno NO cambia de extensión
  (lo exige la referencia congelada de la Loews, `assets/_loews_terreno.npz`).

---

## Bloque 0 — Infraestructura de la fase (antes de cualquier bloque)

**Objetivo medible**: poder renderizar el "antes" y el "después" de cualquier bloque desde cámaras idénticas en
< 2 min de cola, con una hoja lado a lado por bloque, y tener la paleta única y el presupuesto de tris medidos.

**Cambios**
1. `03_blender/_rev/tomas_capturas.py` (nuevo): `construir_tomas(G, bpy) -> [(nombre, loc, tgt, lens)]` = las
   l.45-330 de `renderizar_capturas.py` en una función + tomas nuevas `60_puerto_llanta_cenital`,
   `61_orilla_piloto_s150`, `62_tribuna_piloto_s5100`, `63_horizonte_piloto_s2200`, `64_postal_tunel_salida_s560`,
   `65_postal_cima_s1870`. Arreglar las 5 tomas inútiles (15, 34_desde_pista, 43, 47b, 40) aquí, no en el fichero
   actual.
2. `03_blender/_rev/capturas_ab.py` (nuevo, esbozo en `entender_agua_publico_capturas.md` §9.5): `--blend --geom
   --set --out [--camaras | --guardar-camaras] [--solo] [--res]`; aviso en `ab.log` si la cámara congelada queda
   dentro del terreno (no se mueve).
3. `03_blender/_rev/montaje_ab.py` (nuevo, PIL): pares `AB_<toma>.png` + `hoja_<bloque>_piloto.png` y
   `hoja_<bloque>_aereas.png`.
4. `03_blender/paleta.json` (nuevo) + `03_blender/paleta.py` (`cargar()`, `rgb(nombre)`, `srgb(nombre)`,
   `familia(nombre)`); valores iniciales: `oliva_oscuro (0.16,0.20,0.08)`, `salvia (0.30,0.36,0.22)`,
   `hierba_seca (0.55,0.45,0.20)`, `caliza_ocre (0.46,0.37,0.24)`, `caliza_gris_calido (0.34,0.31,0.26)`,
   `caliza_sombra (0.25,0.20,0.14)`, `terracota (0.62,0.30,0.20)`, `cesped_jardin (0.22,0.42,0.12)`,
   `tierra (0.60,0.43,0.24)`, `arena (0.78,0.72,0.55)`, `mar_orilla (0.25,0.75,0.72)`, `mar_profundo (0.01,0.22,0.42)`.
   Todos [U]: el usuario valida la paleta con una "carta de color" renderizada (plano con 12 esferas).
5. `03_blender/_rev/presupuesto.py` (nuevo, python del sistema): lee `renders/qa/asentar.json['por_familia']` y
   `04_export/kn5/informe_check_opt.json` -> tabla tris/MB por familia; objetivo A8.
6. Copia congelada del "antes" global: `_rev/escena_antes_visual.blend` + `geometria_antes_visual.json`
   (42 MB) y el set BASE renderizado una vez (`renders/ab/_base_antes/`).

**Dependencias**: ninguna. **CSP**: no aplica. **Riesgo**: `camara_segura` solo actúa en el "antes" (una vez);
las tomas por objeto (`CASINO_root`, `YATE_`) se congelan por loc/tgt, no por regla.
**Verificación**: renderizar BASE dos veces seguidas con `--camaras` y comprobar diff de píxeles = 0.
**Estimación**: 10 h-agente, 1 agente, 2 huecos de cola.

---
## Bloque 1 — RELIEVE (macizo, erosión, acantilados, tierra tallada, postales)

**Objetivo visual medible** (todo medido sobre `geometria_3d.json` con el mismo script numpy que usó
`entender_terreno.md`, más las capturas BASE):
- Macizo detrás del pueblo: cumbre nominal del Monte Porto Corsa 220 -> 300 (real ~260-280 m tras limitadores);
  `pct_natural_gt_100` (laderas naturales > 100 %) de 0.28 % a 4-8 % concentrado en el macizo trasero y
  los espolones; desde el piloto en s800 (captura 50) la cresta ocupa el tercio superior del cuadro, con
  crestas y vaguadas legibles (hillshade: >= 10 vaguadas de > 150 m en el macizo N).
- Acantilados tipo Amalfi: orilla con z > 10 m del 7.5 % actual a >= 40 % en los tramos elegidos (lado +1 de
  s 170-402 y 616-820, lado -1 de la recta 2770-2976, bajo `bajada_ladera`, costa N/NE); caras > 60 grados
  con pie de derrubios y repisas de estrato.
- Tramo de tierra: "pared en un lado Y caída en el otro" a 25 m del borde del 5 % actual a >= 45 % de las
  muestras de s 1430-2440 (a 50 m: >= 60 %); rasante <= 15 % (hoy 16.5 %) con <= 9 % en ±40 m de los apex de
  las horquillas C18-19 y C26; `pacas_tierra` no cierra la vista de la bahía en s 1840-1900 lado +1.
- Erosión hidráulica en el macizo (no en el corredor): corredor de la pista con cambio máximo 0.000 m
  (`checks`), `loews_ref_dz_max` = 0, costuras < 0.6 m, fosos <= 1.5 m, `celdas_invaden_pista` = 0.
- McLaren: terreno bajo la zaga (hoy mar a -4 m) >= 60 m en los 120 m detrás de la cola (`coche_120m_pct_ge_90`
  >= 80 %), medido en el marco del coche con `encaje_mclaren.Sitio.terreno`.
- Cinco postales encuadradas (tomas 64, 65, 13, 11/44, 02/49) sin árbol/paca/cartel que tape el motivo.

**Cambios técnicos** (todos en `03_blender/terreno_montana.py` salvo donde se indica; python del sistema):
1. `LANDFORMS` (l.135-175): 'Monte Porto Corsa' h 220 -> 300, `s_foot` 0.40 -> 0.60, `p` 1.3 -> 1.6; 'Espolón del
   coche' 150 -> 200 con cresta a 70-90 m detrás de `o_fin` (63 m) de `pueblo_subida_ladera`; 'espolón SO' +40;
   NUEVO landform 'Cabo del McLaren': cordal (-700,520,70)-(-760,440,95)-(-800,360,80)-(-820,300,40) que sale
   del Espolón del coche bajo la zaga del coche (orientación `ang_c` de `zona_tunel`), con regla de costa anulada
   dentro de su huella (como el peñón, l.1215-1229) y acantilado al mar en la punta. Ridged l.394: `4 + 24·clip`
   -> `6 + 40·clip(M/250)`.
2. Limitador por celda: sustituir la llamada `limitar_pendiente(M, cell, 0.8)` (l.1123) por
   `limitar_pendiente_celda(M, cell, smax_cell)` (nueva, variante de `limitar_pendiente_mascara` l.309) con
   `smax_cell` = 0.8 a < 150 m de la pista, 1.3 en el macizo trasero (máscara `_wf`-like a > 150 m) y 1.8 en las
   crestas (`M > 0.7·max(M)`). La máscara de roca lo pintará de caliza sola.
3. Erosión: NUEVO `03_blender/erosion.py` (numpy + scipy.ndimage; método de rejilla de dandrino + reposo térmico
   por material + pasada opcional de gotas vectorizadas): `erosionar(z, cell, w_eros, mascara_roca, iters=300,
   semilla=0, escala=2) -> z2, caudal, deposito` (simula en rejilla x2 = 2 m con `_zoom_a`, remuestrea a 4 m con
   `map_coordinates`, devuelve además `caudal` (para el canal "tierra" de la máscara) y la diferencia fina a 2 m
   para `txDetailNM`). Inserción en `construir()` entre l.1127 y l.1135 (ANTES de la costa y de todas las reglas
   duras, informe terreno §6); máscara `w_eros` exactamente la de `entender_terreno.md` §6 (dedge 30->80 m,
   viaducto, Loews 90 m, McLaren, peñón r 1.9, `fac_valle`, mar, pit 150 m). Barrancos N1 (l.1135-1161) quedan
   con `_dg` x0.4. Coste medido: ~8 s a 2 m (web_multilayer §3.2.3).
4. Cara tras la última terraza (defecto 3): `techo_tras_terraza` (l.731-739) con BERMA de 18 m entre `o_fin+1.5`
   y el arranque de la cara, bancales también en `w_coche` (quitar la exclusión de `w_tope`, l.1460),
   `BANCO_H` 16 -> 11, `BANCO_A` 1.6 -> 2.6, costillas l.1812-1823 con tope 2 -> 5 m en caras > 20 m, y
   ESCALONES en los cortes: cuantización de `z` en bancos de 7 m con berma de 2 m donde `_corte > 0.3` y
   pendiente > 0.75 (fase por ruido xy de 60 m), aplicada también en `integrar_escena.explanar` (parche al
   coordinador: desmonte 1:1 liso -> mismo perfil en bancos).
5. Acantilados: `r_prot = 30 + 1.7·(z-4)` (l.978) -> `20 + 0.8·(z-4)` en los tramos elegidos (máscara por `s`),
   `pend` de costa 0.6 -> 2.5-4.0 ahí, quitar los topes F-07 (`_wb` l.1203-1206) y `_pm` (l.1210-1211) en esos
   tramos, J1 170 -> 60 m, costillas `_wcf` (l.1829-1831) extendidas a todo `acantilado & _acant`, `s_fl` por
   celda 1.5-3.0 en el lado del mar con berma `d_llano` de 7 m (arcén + guardarraíl + `cierre_ac`).
6. Tierra: `peso` del tirón `_idw_pull` (l.1083) 0.5 en dirt; `techo_desmonte_c1(z0, dedge0, pend=array)`
   (l.720-724) con `pend` 2.0 en el lado INTERIOR de cada curva (signo de `_kap[g_near]`), `s_fl` 1.5 en el lado
   exterior con berma 7 m; `preparar_geometria.py` l.386-392: `MAXG` por muestra (0.15 en dirt, 0.09 en ±40 m
   de los apex C18, C19, C26; parche al coordinador).
7. Máscara de 4 capas: en l.2244-2298 sacar `extras['capas']` = {matorral, hierba_seca, tierra, roca} (floats
   0..1, suma 1) por celda a partir de pendiente, z, `dist_mar`, `dedge0`, `acantilado`, `desmonte`, `caudal`
   de la erosión, sectores de `urbanismo_spec` y `cumbres`; roca natural desde pendiente suavizada > 0.75
   (37 grados) en vez de 1.0; `preparar_geometria.py` l.539-541 las escribe en `geometria_3d.json`.
   `mascara_roca` se mantiene (la leen `color_ac`, revisores, `construir_pista`).
8. Cámaras postal en `_rev/tomas_capturas.py` (bloque 0): 64 (s 560, salida del túnel), 65 (s 1870 mirando
   S/SE, lente 20). "Bajada a la horquilla de la fuente" [U]: Loews (s 3564) o C26 (s 2364).
9. QA: `checks` nuevos `pared_y_caida_25m_pct`, `orilla_z10_pct_tramos`, `cabo_mclaren_z_media`,
   `erosion_corredor_dz_max`; `qa_figuras` añade `terreno_erosion_antes_despues.png` y `terreno_capas.png`.

**Dependencias y orden**: 6 (tierra, sin erosión) -> 1+2+4 (macizo, cabo, cara tras terrazas) -> 5 (costa) ->
3 (erosión, con todo estable) -> 7 (capas) -> 8-9. Tras cada paso: `python preparar_geometria.py` (QA_DIR de
prueba) + `python urbanismo.py` (re-ejecutar SIEMPRE: muros, casas enterradas) y solo con QA limpia
`bash _rev/pipeline_escena.sh`. Avisar a `04_export`: `GROUND_PREFIXES` deja al TERRENO sin sombra
(`castShadows = 0`): con un macizo que da sombra a la pista hay que exceptuar `1GRASS_terreno` [W].
Depende de: nada. Lo necesitan: 2 (cabo, umbrales), 3 (capas), 4 (máscaras), 5 (bandas), 6 (costa), 7 (explanadas).

**CSP**: nada [E]. **Riesgos**: tajo de cantera más alto si se sube el macizo sin la berma (hacer 4 antes que 1);
McLaren más enterrado por el morro (B11) -> `encaje_mclaren.evaluar()` con "pista bajo huella" = 0 y holgura
>= 4 m; depósito de la erosión en la vega/orilla (`np.minimum` con la z previa a < 40 m del mar); pretiles con
pie al aire en acantilados (`construir_pista._pretil` baja el pie a `min(ze-2.5, zt-1.5)`: comprobar); cámaras
aéreas congeladas dentro del macizo nuevo (aviso en `ab.log`, toma nueva con otro nombre); el puerto/dique a
150-250 m del cabo (medir contra `PUERTO_dique` y la rotonda s 300-400).
**Verificación**: `checks` + figuras QA; capturas A/B BASE + 05/07/08/09/14/16/21/22/42; `revisar_urbanismo`
(objetivo 0), `revisar_fisica_ac` (caídas en escapatoria), `nada_en_pista`.
**Estimación**: 75 h-agente; 3 agentes en paralelo (A: macizo+limitador+erosión; B: tierra+costa; C: cabo del
McLaren + capas + cámaras + QA), 2-3 huecos de cola simultáneos (cada regeneración completa ~1 h).

---

## Bloque 2 — ROCA INTEGRADA (terreno, lazo, peñón, McLaren, afloramientos)

**Objetivo visual medible**:
- Una sola caliza cálida con estratos horizontales en TODO lo que sea roca (terreno, lazo, peñón, McLaren,
  afloramientos, escolleras): misma paleta, mismo periodo de estrato (3 m) y misma fase en z de mundo; en AC
  se ven estratos, grano y AO (texturas horneadas por objeto).
- Roca del terreno por pendiente > 37 grados (hoy 45-60): celdas de tierra con pendiente > 0.75 y roca > 0.5
  del 21 % al >= 90 %; borde roca/hierba por texel (máscara 0.5 m), 0 "dientes de sierra" en 07/08.
- Afloramientos: 200-300 piezas semienterradas en cinturones por curva de nivel + 600-900 pedruscos al pie,
  matas en las repisas; desde el piloto s1700 (51) y s2900 (52) al menos 3 afloramientos visibles por cuadro.
- Roca del lazo: >= 60 % de la superficie fuera del corte en bancos verticales (80-88 grados) con repisas de
  2.5-6 m; 2-3 espolones y una aguja/torre en la cumbre; pinos agrupados en repisas (>= 40); capturas 13/45/34
  sin "cúpula lisa".
- Peñón: perfil cada 1.5-2 m, cornisas de 1.5-3 m, meseta texturizada y oscurecida un 25 %, 0 planos blancos
  sin material (19).
- McLaren: terreno/faldón hasta la cintura del coche en los flancos y hasta el capó en el morro, 0 "repisa
  plana" en 33/17, >= 100 escombros, grietas en el macizo, plantas en las juntas, túnel por el centro de la
  rueda con portal de sillería de 11-12 m; caliza de la carrocería a (0.46,0.37,0.24) con estratos como surcos
  de junta, no franjas.

**Cambios técnicos**
1. NUEVO `03_blender/assets/materiales_roca.py`: `node_group_caliza(nombre='NG_caliza_estratos') -> NodeGroup`
   con entradas (tono_base, tono_junta, periodo_m=3.0, fuerza_bump, mojado_z, fase) y salidas (Color, Normal, AO),
   coordenadas `Geometry.Position` (mundo); estratos `TexWave BANDS Z` con junta hundida, bancos de 8-14 m con
   tono alterno, grano 0.3-1 m, manchas 15-25 m a ±10 % (hoy ±50 %: es lo que el director lee como "bruma"),
   líquenes/mojado bajo z=1; `aplicar_a(material, **kw)` (enlaza Base Color/Normal y deja `diffuse_color` =
   media). `test_materiales_roca.py` + previews. Enchufar en: `construir_pista._roca_terreno` (sustituye
   `ROCA_rampa..ROCA_bump` l.252-337, mantiene `Math.002`/`ROCA_mascara`), `roca_lazo._mat` y `roca_casino._mat`
   (unificar las dos `_PALETA` con `paleta.json`), `montana_coche_v2._mat_piedra` (los 9 `MAT_MCOCHE_*`; `hueso`
   0.80 -> 0.58; `cristal_pulido` rugosidad 0.26 -> 0.5). Quitar la familia `roca` de `aplicar_texturas.aplicar_roca`
   (l.359-398) o dejarla solo como bump fino.
2. NUEVO `03_blender/hornear_rocas.py` (Blender, Cycles, por la cola; paso nuevo del pipeline tras
   `aplicar_texturas`): por objeto (`TUNEL_acantilado`, `PENON_puente_roca`, `PENON_roca`, obra `PENON_*` de
   roca, `AFLOR_*` agrupados por cinturón) `Smart UV Project` (ángulo 45, margen 0.004) a un `uv_layers['UVMap']`,
   bake Diffuse(Color) x AO (+ Normal en espacio tangente para `ksPerPixelNM`) a 4096/4096/2048/1024 px, material
   nuevo `MAT_ROCA_<obj>` con la imagen en Base Color (sin Mapping), `diffuse_color` blanco, custom props
   `ac_shader = 'ksPerPixelNM'`, `ac_samplers = {txDiffuse, txNormal}`, `ac_tex_max = 4096`. Idempotente
   (marcador `HORNEADO`). Las imágenes van a `03_blender/texturas/horneadas/`. [W] para que llegue al KN5; en
   Blender se ve desde el primer día.
3. Terreno: umbrales en `terreno_montana` (bloque 1.7) y en `construir_pista._roca_terreno` l.203-206: `talud`
   0.50-0.56 -> 0.70-0.78; quitar `ROCA_llano_hierba` donde atributo = 1 (desmontes). `aplicar_texturas.FAMILIAS
   ['hierba'].proy` FLAT -> BOX (transición hasta que el multicapa del bloque 3 sustituya `aplicar_terreno`).
4. NUEVO `03_blender/assets/afloramiento_kit.py`: `build_afloramiento(parent, largo, alto, bancos, seed,
   material) -> ob 'AFLOR_losa'` (losa de caliza con 2-4 bancos, cornisas, pie en talud, 300-900 tris),
   `build_pedrusco(parent, r, seed)` (reusa `montana_coche_v2._pedrusco`), `build_cinturon(parent, polilinea,
   n, seed)` (agrupa en una malla por cinturón, `AFLOR_cinturon`). `test_afloramiento_kit.py`. Zona nueva
   `zona_afloramientos` (parche al integrador, después de `zona_tierra`): candidatos donde `pendiente_terreno`
   entre 0.5 y 1.0 siguiendo la curva de nivel, base 1-2 m bajo el terreno, exclusiones `_sitio_lejos_pista`
   (12 m), `_libre`, `zonas_excluidas`, rocas de los 3 generadores, Loews, senderos; matas de `vegetacion_kit`
   en la repisa. Alta en `asentar_objetos.SOPORTE_PREF`/`ASENTAR_NO`, `revisar_flotantes`, `despeje_final`,
   `exportar_ac` (1WALL solo a < 6 m del borde).
5. `roca_lazo.py`: tras `M = mac.eval(...)` + ruido (l.3481-3490) aplicar `_bancos_naturales(M, G, seed)`
   (cuantización monótona `M' <= M` en bancos de 8-14 m, fase por ruido 2D de 40-80 m, cara 80-88 grados,
   repisa 0.25-0.4 del banco, solo `o > o_b + 8` y fuera de rasgos dilatados 6-10 m); 2-3 espolones (`_Macizo.domo`
   con a 3-4, b 0.6-0.9) en el lado NE/N; aguja de 15-25 m en la cumbre o fortín de `italiano_kit.build_torre_costera`
   [U]; `_poblar`: pinos (`vegetacion_kit.build_pino` parasol, alto 16-20) en repisas nz > 0.9 y >= 3 m, 1 cada
   6-10 m, agrupados; filtro de normal vertical para las matas (no más "matas en la pared", 11/15/20/38). Los
   estratos del grupo de caliza usan el mismo `hb` y fase que los bancos geométricos.
6. `roca_casino.py`: `_perfil` l.1781-1786 de 3 cotas por banco a cada 1.5-2 m (27 k -> ~80 k tris),
   `estrato()` con labio 1.5-3 m y segunda escala de bancos finos, `textura()` con ruido 2-5 m; meseta
   (`plaza`, `borde`, `muelle`) con el grupo de caliza o familia piedra y -25 % de luminancia; pinos en labios
   anchos (hoy máximo 22); localizar el "plano blanco" de la 19 con `test_roca_casino.py` vistas `roca_casino_v3_*`.
   Silueta Topolino desde el mar: ver bloque 8.
7. `montana_mclaren.py`: (a) `_roca`: `_K_FALDA` 0.36 -> 1.4 fuera de la zona del túnel (talud 35 grados) con
   faldón hasta `+0.72R` sobre el buje en los flancos y hasta el capó en el morro; en x entre -1.3R y 1.5R pared
   vertical SOLO en el ancho del portal (21 + 2 m) y relleno a los lados; (b) `_bloques` 28 -> 100-150 pedruscos
   de 1-6 m (densidad máxima en los 15 m sobre `z_agua` y en el contacto `ft`) + 3 bloques de 8-15 m con grieta
   madre; (c) `_cortes`: familia de grietas en macizo y faldón (horizontales en juntas + 3-5 verticales por
   `_celda_suave`), `_bandas_finas` de la carrocería -> surcos de junta con bump del grupo; (d) `_vegetacion`:
   tipo "junta" (repisa con pared detrás), `_VEG_TRIS_MAX` 3400 -> 8000; (e) `alto_base` 12 -> 19-20 m para que
   el arco de 21 x 9.5 m quede centrado en la llanta (buje a pista + 5) y `_galeria`/`_portal` con sillares de
   11-12 m; (f) AO horneada (2). Parámetros nuevos de `build()` con valores por defecto = comportamiento actual.
   Parche al coordinador en `zona_tunel` (l.2881: `alto_base`, `faldon=True`). Con el cabo del bloque 1.1 la
   zaga apoya en tierra: `_contacto_terreno` ('auto') pasará más caras a `caliza_monte`/`MAT_terreno`.

**Dependencias y orden**: 1 (grupo) -> 3 (umbrales, con bloque 1.7) -> 5, 6, 7 en paralelo (cada uno con su
test) -> 4 (afloramientos, con el relieve final) -> 2 (hornear, al final, con geometría estable). Depende de:
bloque 1 (cabo, máscara). Lo necesitan: 3 (la caliza del terreno), 6 (escolleras con el mismo grupo), 8 (peñón).
**CSP**: nada [E]; VAO [X] (bloque 3). **[W]**: texturas horneadas por objeto + `ksPerPixelNM` + tangentes
reales desde la UV + `TEX_MAX` 4096 por material.
**Riesgos**: cadena Boolean del McLaren con faldón más ancho (probar seeds 0/3/7/11 en `test_montana_mclaren`,
MANIFOLD con red de seguridad); "pista bajo huella" en s 718-728 (hoy 5.6 m de holgura) y solares de
`pueblo_subida_ladera` (`zonas_excluidas` +20-40 m -> `urbanismo_spec.json` + re-ejecutar `urbanismo.py`);
H7 del lazo (cuencas): solo RESTAR relieve, comprobar `n2['celdas_rellenas']` y todos los `checks` en `ok`;
tris: lazo +20-40 %, peñón x3, afloramientos +0.2 M (presupuesto A8); bake de Cycles de 3-4 objetos a 4 k:
~1 h de cola (GPU) o varias (CPU) [U]; el 28 % de celdas pasa a candidata a roca: acompañar con la paleta
(bloque 3) para que no sea "todo gris".
**Verificación**: `test_roca_lazo/casino/montana_mclaren` TEST_OK, `encaje_mclaren.evaluar()`, `revisar_tunel`,
`asentar_objetos`, `nada_en_pista`; capturas A/B 02/13/17/19/20/32/33/33b/34/36/45/46/54 + BASE; recortes
ampliados del borde roca/hierba en 07/08/14/22.
**Estimación**: 95 h-agente; 4 agentes (A: materiales_roca + hornear; B: roca_lazo; C: roca_casino +
afloramiento_kit; D: montana_mclaren), 4 huecos de cola.

---
## Bloque 3 — PALETA, TEXTURAS Y LUZ (multicapa, CC0, AO, bisel, VAO)

**Objetivo visual medible**:
- Fuera el césped uniforme: en las 6 capturas de piloto, el verde saturado (H 90-130, S > 0.5) cae del ~45 % de
  píxeles actual (01, 07, 51) a < 8 % (solo jardines, rotondas, copas); dominan oliva/salvia, dorado, ocre y
  terracota. Medido con un script PIL sobre las capturas A/B (`_rev/medir_paleta.py`).
- Terreno con 4 capas por texel (matorral / hierba seca / tierra / roca) en Blender Y en AC: 0 bordes en
  escalera o dientes de sierra en 07/08/14/22 a 1:1; textura legible desde el coche (detalle de 2-3 m a
  1024-2048 px) y variación macro (diffuse 2048² con AO) desde el aire.
- AO: oclusión visible en vaguadas, pie de muros, bajo copas y en los huecos del McLaren (diffuse x AO en
  terreno y rocas; VAO en CSP). Bisel: cantos de casas, muros, pretiles, bordillos y kits con `shade_smooth` +
  auto smooth 35 grados o modificador Bevel de 2 segmentos (solo kits, nunca terreno).
- Consistencia Blender <-> AC: `color_ac` re-medido con la paleta nueva; diferencia media < 0.03 lineal entre
  la vista simulada y el render en las 6 vistas de ajuste.

**Cambios técnicos**
1. `paleta.json` (bloque 0) aplicada: `construir_pista.py` rampa por altura l.110-114 (hierba seca abajo,
   matorral en el macizo, caliza en cumbres), `mixr.inputs[7]`/`ROCA_rampa` (caliza ocre/gris cálido),
   `diffuse_color` l.181 = hierba seca (media de la zona dominante), `MAT_arcen` l.1169, `MAT_tierra` l.86,
   `MAT_muro_contencion_piedra` l.1285; `casas_kit_v2.PALETA_FACHADA` (8-10 tonos Riviera) y `COL_TEJA`;
   `vegetacion_kit_v3` (copas oliva/salvia, no césped); `color_ac._REGLAS` (l.309-331): subcadenas nuevas
   `matorral`, `seca`, `cesped`, `caliza_ocre` [W, lista de petición].
2. NUEVO `03_blender/texturas/recolorear_cc0.py` (PIL, python del sistema) [U permiso de descarga]: por textura
   CC0 -> luminancia + tinte de `paleta.json` conservando ±15 % de croma, seamless comprobado (`mosaico_3x3_*`),
   salida 1024 (detalle) o 2048 (cenitales) en `03_blender/texturas/cc0/<nombre>_d.png` + `_n.png` + `_ao.png`
   + `LICENSE_CC0.txt` y `CREDITS.txt`. Lista P1 (web_texturas_cc0 §5): `rock_06` (roca), `withered_grass`
   (hierba seca), `Ground105` (tierra), `aerial_grass_rock` (matorral, cenital 15 m), `asphalt_track`,
   `white_stucco`, `clay_roof_tiles_03`, `PavingStones150`; P2: `rock_face_03`, `gravel_road`, `rock_wall_10`,
   `rocks_ground_06`, `aerial_sand`. 1K-JPG: 49 MB; 2K-JPG: 186 MB. Si NO hay permiso: `generar_texturas.py`
   (PIL/FFT) produce las mismas 13 con el estilo plano actual (plan B, sin fotorealismo: coherente con Pixar).
3. NUEVO `03_blender/mascara_terreno.py` (numpy, python del sistema; paso tras `preparar_geometria`, antes de
   `construir_pista`): lee `geometria_3d.json['terreno']` + `extras capas` (bloque 1.7) + `urbanismo.json`
   (solares, calles: césped de jardín en plazas y rotondas, tierra en patios) + `muestras` -> `texturas/
   terreno_mask.png` RGBA 4096² (R matorral, G hierba seca, B tierra, A roca; bordes con ruido de 3-12 m y
   transiciones de 2-4 texeles, suma ≈ 1) y `texturas/terreno_diffuse.png` 2048² sRGB (color base de la paleta
   por capa x AO del heightmap (cavidad + hillshade suave + horizonte) x "sombra de bosque" oscurecida bajo las
   masas del plan de vegetación). API: `generar(geom, urb, veg_plan, out_dir, res_mask=4096, res_diff=2048)`;
   QA `renders/qa/terreno_mask.png` reducida.
4. `construir_pista.py`: UV planar en `TERRENO` (`me.uv_layers.new('UVMap')`, u = (x-x0)/(nx·cell),
   v = (y-y0)/(ny·cell)) l.1448-1468; `mat_terreno()` NUEVO (`mat_terreno_multicapa()`): Image `terreno_mask`
   (UV) + Image `terreno_diffuse` (UV) + 4 Image de detalle (UV x mult: 2068/tile_m) + 4 normales de detalle,
   mezcla por canal (Mix por R, G, B, A) y multiplicación detalle x diffuse (como hace el shader de AC: overlay);
   mantener el nodo `ROCA_mascara`/`Math.002` = canal A (lo leen revisores y `color_ac`); custom props
   `ac_shader = 'ksMultilayer_fresnel_nm'`, `ac_samplers = {txDiffuse: terreno_diffuse, txMask: terreno_mask,
   txDetailR/G/B/A: <cc0>_d, txDetailNM: <roca>_n}`, `ac_props = {multR: 345, multG: 517, multB: 1034,
   multA: 1379, detailNMMult: (1379, 1379), fresnelC: 0.02, fresnelEXP: 3, fresnelMaxLevel: 0.1, ksSpecular: 0.08}`,
   `ac_tex_max = {txMask: 4096, txDiffuse: 2048, detalles: 1024}`. `aplicar_texturas.aplicar_terreno` se retira
   para `MAT_terreno` (familia nueva `multicapa` que no toca). `AGUA_fondo` deja de usar `MAT_terreno` (bloque 6).
5. Césped de jardín: material nuevo `MAT_cesped` (paleta `cesped_jardin`, tile `cesped_d` 3 m) en
   `horquilla_loews` (parterre), `zona_casino` jardines, `CALLE_plazoleta`/`CALLE_patio` (bloque 5), rotonda de
   la palmera; es el ÚNICO material que lista GrassFX (bloque 9).
6. AO y bisel: (a) terreno: en `terreno_diffuse` (3); (b) rocas y McLaren: `hornear_rocas.py` (bloque 2.2);
   (c) kits: `_MB.to_object` de `casas_kit_v2`, `caminos_kit`, `edificios_civicos_v2`, `pit_kit`, `carrera_kit_v2`,
   `italiano_kit` con `shade_smooth` + `use_auto_smooth`/atributo `sharp_edge` a 35 grados; modificador Bevel
   (2 segmentos, 4 cm, limitar por ángulo) en casas, muros y pretiles, aplicado antes de exportar (+10-20 %
   vértices en 216 casas: asumible); (d) AO horneada por objeto en el casino, hotel, ayuntamiento, campanile
   (los 4 "monumentos"): atlas 2048 por objeto vía `hornear_rocas.py` generalizado a `hornear_objetos.py`
   (misma API, lista de objetos) [W].
7. VAO [X][U]: descargar `acc-bakeryoptix build-v22.zip` (1.8 MB; Vulkan RT o CPU Embree), ejecutar
   `bakeryoptix.exe porto_corsa.kn5` con `baked_shadow_params.ini` (`[MODE_TRACK] BAKE_AS_TREES = DECO_MAT_VEG?,
   BAKE_AS_GRASS = 1GRASS?, EXCLUDE_FROM_BAKING = *invisible*, *cierre*, TUNNEL_FIX_0_NAMES = TUNEL_*`) ->
   `porto_corsa.vao-patch`; `empaquetar.py` lo copia + README "copiar a assettocorsa/extension/vao-patches/" [W].
8. Luz de Blender (para que las capturas juzguen como AC): `construir_pista.py` l.1566-1618: sol 34 -> 42 grados,
   color (1,0.96,0.88) -> (1,0.95,0.85), cielo menos saturado, exposición 0.12 -> 0.10, GTAO 12 -> 20 m, y
   niebla de mundo (`use_mist`) SOLO para la perspectiva atmosférica lejana > 1.5 km (hoy la "bruma" es de los
   materiales, no de la niebla). `renderizar_capturas` + `capturas_ab` fuerzan los mismos ajustes.
9. `color_ac`: re-medir (`_rev/color_ac/render_ac.py` + `medir_objetivos.py` + `medir_albedo.py`) tras cerrar
   la paleta; revisar `CROMA_MAX` 1.08 (ocres y terracotas saturados) y `techo` por familia; `calibrar_todos`
   debe saltar los materiales con `ac_shader` != ksPerPixel (imagen tal cual) [W].

**Dependencias y orden**: 1 -> 2 (o plan B) -> 3+4 (con `capas` del bloque 1.7 y el plan de vegetación del
bloque 4.1 para la sombra de bosque; se puede empezar con máscara sin bosque) -> 5 -> 6 -> 8 -> 9 (al final de
la fase) ; 7 cuando exista el KN5 v2. Depende de: 1 (capas), 2 (grupo de caliza y hornear). Lo necesitan: todos
(paleta) y 9 (MAT_cesped, ext_config).
**CSP**: [E] paleta, multicapa `_nm`, AO en diffuse, bisel; [X] nm4 + `tilingFixR/G/B/A` por
`[SHADER_REPLACEMENT_...] MATERIALS = MAT_terreno`, VAO, `DOUBLE_FACE_SHADOW_BIASED = 1`.
**[W]** (lista cerrada para el equipo de export): (i) shader/props/samplers por material desde custom props;
(ii) modo "imagen tal cual" sin tintar ni reducir, `TEX_MAX` por material (txMask 4096); (iii) DDS BC1/BC3 con
mipmaps para > 1024 (hoy PNG sin mipmaps garantizados); (iv) `kn5_check` comprobación 9 (tabla `SHADERS` con
samplers/props esperados, potencia de 2, <= 4096); (v) KN5 DE ENSAYO (plano de 4 triángulos con el multicapa +
un cubo `ksPerPixelNM` + un quad `ksPerPixelAT`) para que el amigo lo pruebe ANTES del circuito [U]; (vi)
tangentes reales desde la UV (hoy ficticias, l.448-458); (vii) `color_ac` por familia multicapa.
**Riesgos**: R4 nombres de shader/samplers mal -> AC no carga (mitigación: `_nm` vanilla, cuyos samplers están
verificados; nm4 solo por ext_config; KN5 de ensayo); fresnel sin normal -> `ksSpecular` bajo; `TEX_MAX` 4096
en una máscara RGBA PNG = 16-30 MB (DDS BC3: 11 MB con mips); cambiar `diffuse_color` invalida las medidas de
`color_ac` (guarda ±0.02) hasta re-medir (hacerlo al final); repetición de los tiles de 2 m en praderas grandes
(lo tapa `terreno_diffuse` de baja frecuencia + tilingFix en CSP); GPU para los bakes [U].
**Verificación**: capturas A/B BASE + 03/05/06/07/08/09/14/16/17/21/22/33/40/48 + carta de color; `medir_paleta.py`;
`kn5_check` 9/9; `_color_ac_prueba/leer_kn5_color.py`; simulación `simular_vistas.py`; prueba en el PC del amigo
del KN5 de ensayo (sí/no carga, sí/no mipmaps, FPS).
**Estimación**: 70 h-agente en Blender (2 agentes: A: paleta + tiles + recolorear + luz; B: mascara_terreno +
multicapa + MAT_cesped + bisel) + 20 h de `hornear_objetos`/VAO cuando haya writer v2; la parte [W] se cuenta en
el bloque W.

---

## Bloque 4 — VEGETACIÓN (plan por máscaras, kit v3, alfa test, TreeFX)

**Objetivo visual medible**:
- Cero piruletas: ninguna copa convexa lisa sobre palo; pinos parasol 16-24 m con copa plana y gruesa de borde
  ondulado, cipreses 10-16, palmeras 12-20, olivos 5-7 con tronco grueso, encinas 9-12; variación de altura
  por especie y escala no uniforme (x/y vs z), ±10 % de color por instancia QUE LLEGUE al KN5.
- Masas, no reparto uniforme: >= 70 % de los árboles dentro de masas de >= 12 piezas con dosel continuo
  (distancia media al vecino 3-5 m en pinar, 7-9 en olivar); claros explícitos; nada por encima de 80 m hoy ->
  pinar hasta 180 m y matorral/roca por encima; sotobosque (matorral/arbusto) 1 cada 15 m² bajo las masas.
- Densidad x3 (2.7 k -> 7-9 k árboles + 15-20 k matas) con <= 0.9 M tris (hoy 1.74 M): híbrido casquetes +
  hojas en tarjetas con alfa (150-250 tris/árbol) + sombra proyectada en AC (`castShadows = 1` con alfa test).
- GrassFX solo en `MAT_cesped`. TreeFX como capa extra con la MISMA lista.

**Cambios técnicos**
1. NUEVO `03_blender/vegetacion.py` (python del sistema, como `urbanismo.py`): lee `geometria_3d.json`
   (terreno, capas, cumbres, muestras), `urbanismo.json`, `bancales_spec.json` (bloque 7), senderos y rocas
   (huellas exportadas por el integrador a `renders/qa/huellas.json`) -> `vegetacion_plan.json` [{especie,
   variante, x, y, z, rot, escala_xy, escala_z, tono, masa_id, lod}] + `renders/qa/vegetacion_mapa.png`.
   Zonas por máscara: pinar en crestas/collados 60-180 m y umbrías > 25 grados (encinar), olivar en bancales
   20-90 m junto al pueblo, cipreses en caminos/ermita/cementerio, palmeras < 20 m junto al mar/paseo/casino,
   adelfas y arbustos con flor en bordes de calle y jardines, matorral donde pendiente > 30 grados, nada donde
   roca > 0.6 salvo pinos en repisas; masas por semillas + disco de Poisson con radio por especie + claros;
   exclusiones = las de los inspectores (pista + 12 m, calles, plazas, edificios, caminos, bancales, rocas,
   Loews, `zonas_excluidas`) para que `despeje_final`/asentar no quiten ~140 por pasada. `zona_montana`,
   `zona_tierra` (árboles) y `zona_casino` (jardines) pasan a `zona_vegetacion_plan` (parche al integrador):
   un árbol = una línea del plan = un clon.
2. NUEVO `03_blender/assets/vegetacion_kit_v3.py` (misma API que v2: `build_pino(parent, alto, seed, variante,
   sin_alfa=False)` -> `VEG_pino` con `ob["VEG_variante"]`, pivote en la base) + `test_vegetacion_kit_v3.py`
   (presupuesto <= 250 tris/árbol, <= 80/arbusto, previews por familia) + `assets/render_impostores_veg.py`
   (cámara ortográfica, fondo alfa, 4 vistas por especie, 512x1024, AO horneado) -> `texturas/veg/atlas_<especie>.png`
   RGBA. Copa = 2-3 casquetes cóncavos de borde ondulado (60-120 tris) + 4-8 tarjetas de hojas del atlas pegadas
   a la superficie (`_doble` para dos caras) + tronco grueso de 7 lados + 2-4 ramas visibles; `sin_alfa=True` =
   solo casquetes (lo que se ve en AC hasta el writer v2). UV en `_MB` (`uv_layers.new`), materiales
   `MAT_VEGC_<especie>` con Image RGBA en Base Color y Alpha, custom props `ac_shader = 'ksTree'` (alternativa
   `ksPerPixelAT`), `ac_props = {ksAmbient 0.4, ksDiffuse 0.3, ksSpecular 0, ksSpecularEXP 1, ksAlphaRef 0.5}`,
   `ac_alpha_test = 1`, `ac_cast_shadows = 1`, normales de las tarjetas (0,0,1). Variación de tono por instancia:
   3 materiales por especie (`_a/_b/_c`) elegidos por `tono` del plan (sí llega al KN5, a diferencia de
   `enriquecer_vegetacion`). `build_library` (integrador l.255-311) -> v3 vía `v2_aprobados.txt`/`load_mod`
   con sufijo configurable.
3. Sotobosque y suelo: `build_arbusto`/`build_matorral` v3 en tarjeta (24-40 tris); "sombra de bosque" en
   `terreno_diffuse` (bloque 3.3) a partir de `vegetacion_plan.json`.
4. [W] writer v2: `ksTree`/`ksPerPixelAT` + `alphaTested 1` + `ksAlphaRef` + PNG RGBA con bleed + `castShadows 1`
   para `VEG_` + troceo por área (celdas de 200 m, no un trozo de 65 k vértices = todo el mapa) + nombres
   `DECO_MAT_VEGC_*` + `lodIn/lodOut` (tarjetas cruzadas con `lodOut 150`, billboard de 2 tris con `lodIn 150`).
5. TreeFX [X]: NUEVO `03_blender/exportar_trees_txt.py` (python del sistema): `vegetacion_plan.json` ->
   `04_export/extension/trees/trees.txt` con bloques `configure:` por masa (`size variance`, `width variance`,
   `angle variance 0,360`, `color variance`, `brightness variance 0.9,1.1`, `seed`) y líneas `tree: <especie>.bin;
   pos=x_b, z_b, -y_b; angle=...; size=...` (conversión `(x,y,z)_b -> (x,z,-y)`; signo del ángulo [U validar]).
   FBX por especie con 3 LOD (A = v3 detallado <= 3 k, B = v3 <= 1 k, C = casquetes <= 250), pivote en la base,
   difusa+alfa y normal: `assets/exportar_fbx_veg.py` con `bpy.ops.export_scene.fbx` [U excepción a "sin bpy.ops"].
   `.bin` con el tree converter de Content Manager (developer mode) en el PC del amigo. `ext_config.ini`:
   `[TREES] LIST_0 = trees/trees.txt`, `SURFACE_MATERIALS = MAT_terreno`, y `[SHADER_REPLACEMENT_...] MATERIALS =
   MAT_VEGC_?; IS_VISIBLE = 0` para ocultar las mallas solo con CSP [W: lo genera `color_ac.generar_ext_config`].
   PRIMERO 3 árboles de prueba (meta, casino, cima) en el zip de ensayo.
6. Filtros: `asentar_objetos.copa_calzada` con la anchura real de la tarjeta; `revisar_invasores.REGLAS` radio
   por especie; `eliminar_sumergidos` igual.

**Dependencias y orden**: 1 (plan, se puede hacer YA con el terreno actual y se regenera solo con el bloque 1)
-> 2 (kit v3 + impostores; en paralelo con 1) -> 3 -> integración (`zona_vegetacion_plan`) -> 5 (trees.txt +
FBX, cuando el plan sea estable) ; 4 en el bloque W. Depende de: 1 (relieve final para el plan definitivo),
3 (paleta de copas), 7 (bancales). Lo necesitan: 3 (sombra de bosque), 9 (GrassFX, HIDE).
**CSP**: [E] silueta, densidad, color, sombra (con W); [X] TreeFX, viento, `ENABLE_TREES_LIGHTING`.
**Riesgos**: hasta W las hojas con alfa saldrían opacas en AC (cuadrados verdes) -> `sin_alfa=True` en el
export hasta entonces; halos en bordes (bleed + `ksAlphaRef 0.5`); "cartón" a 1.4 m (mezclar con árboles héroe
opacos v3 en los primeros 20 m de pista, plazas y casino); aliasing de hojas finas (hojas gordas estilo Cars);
`.bin` solo en el PC del amigo; con CSP < 0.1.79 `HIDE` sin TreeFX = pista sin árboles (confirmar versión [U]).
**Verificación**: `test_vegetacion_kit_v3` + previews; `vegetacion_mapa.png`; `asentar.json` (quitados por
pasada: objetivo < 15); tris por familia (`presupuesto.py`); capturas A/B BASE + 01/07/10/21/34 + variante
"sin sombras de vegetación" hasta W; coordenadas de los 3 árboles de prueba contra `nodos_AC` de
`resumen_writer_opt.json`.
**Estimación**: 85 h-agente; 3 agentes (A: vegetacion.py + mapa; B: kit v3 + impostores + test; C: trees.txt +
FBX + integración), 3 huecos de cola.

---
## Bloque 5 — PUEBLO (densidad, terrazas llanas, atlas de fachadas, suelo urbano)

**Objetivo visual medible**:
- Fachadas pegadas: huecos entre solares de una misma fila (`huecos` del QA de urbanismo) de 515 m a < 120 m
  en total; separación 0 dentro de manzanas de 3-7 casas; 0 m² de césped entre acera y fachada (losas `CALLE_acera`)
  y patios pavimentados o con muro de parcela.
- Terrazas 1-2 de `pueblo_subida_ladera` ocupadas (hoy 41 casas / 3 terrazas con rechazos `rampa_alta 278`,
  `terreno 248`): objetivo >= 70 casas en el sector y ninguna plaza/rampa sin casas alrededor (39, 40, 50).
- Muros que se leen como muros: coronación que sigue `z_top` por vértice y terreno "escarpado" a < 2.5 m del
  muro (lado alto a z_top-0.1, bajo a z_base+0.1): 0 aletas en 05/06/39/40/50.
- Variedad: 2-7 plantas sin dos vecinas iguales, anchos 4.5-11 m, 8-10 tonos Riviera, contraventanas de 4
  colores, balcones con macetas, ropa tendida en carruggi, soportales con tiendas en >= 30 % de las plantas
  bajas de la calle de servicio, 1 iglesia con cúpula + campanile por sector grande, torreones de esquina.
- Suelo urbano: adoquín en el tramo central de cada calle de servicio, farola cada 18 m, bolardos en bocas,
  alcantarillas cada 25 m. QA `urbanismo.py` 0 fallos (bloqueante) y `revisar_urbanismo` 0 (hoy 23).

**Cambios técnicos**
1. `urbanismo.py`: `construir_solares` (l.1875-1998) por MANZANAS (3-7 casas, `t += a`, sin buffer 1.02 dentro
   de la manzana, hueco de 1.5-2.5 m entre manzanas = carruggio/escalera corta), `anchos = [4.5..9]`, plantas
   2-7 con regla "no dos vecinas iguales", solares TRAPEZOIDALES en curva (lados radiales) + `inglete` por
   casa; exportar `medianera_izq/der`, `manzana`, `soportal`, `inglete` (campos nuevos, sin tocar claves
   existentes); elementos nuevos `aceras` y `patios` (polígonos por manzana) y `escalera_corta` entre k y k+1
   en los huecos entre manzanas; `travesia_cada_m` 150 -> 75; casas "de espaldas" a las rampas (medianera ciega
   al muro de la rampa) para recuperar los 278 rechazos `rampa_alta`; `construir_plaza` admite una plaza por
   terraza con edificio cívico al fondo (`iglesia`). `verificar()`: `solar_solar` -> intersección de interiores
   > 0.05 m² salvo misma manzana; `calle_solar` y `huecos` por manzana. Rechazos `terreno` en s 920-1000: se
   resuelven con la berma del bloque 1.4 (banda llana) y, si no, `TOL_SOLAR` 0.5 -> 0.7 con zócalo.
2. `urbanismo_escena.py`: `casa_var` con clave `(plantas, ancho, fondo, seed%3, laterales, soportal, inglete)`
   y `hk.build_casa(..., laterales=(not med_izq, not med_der), soportal=..., inglete=...)`; retranqueo 1-2 cm de
   la medianera de la casa más baja; `poligono('CALLE_acera')`/`('CALLE_patio')` (alta en
   `asentar_objetos.SOPORTE_PREF`/`LOSA_PLAN`, `revisar_urbanismo.LOSA_PREF_QA`/`PROP_NO`); muros del plan con
   `muro_rampa_sillares` (altura por vértice, coronación = `z_top`) en vez de `muro3d` (mediana); ESCARPA:
   nueva pasada `escarpar_muros(T, muros)` (nodos del TERRENO a < 2.5 m del muro: lado alto a z_top-0.1, bajo a
   z_base+0.1, respeta `_proteger_pista`) llamada tras construir los muros (parche al integrador o en
   `asentar_objetos` junto a `garantia_losas_terreno`); farola cada 18 m alternando lado y bolardos en bocas
   (`calle_kit.build_bolardo` nuevo); tramo central de la calle de servicio en adoquín (`tipo='servicio_adoquin'`).
3. `casas_kit_v2.py` (o `casas_kit_v3.py` con la misma API): UVs en `_MB.cara/box/pbox` (pared u = a/escala,
   v = z/escala; tejado por faldón) y `to_object` con `uv_layers.new`; `params['soportal']` (planta baja
   retranqueada 2.5 m con pilares/arcos cada columna); `params['inglete']`; `params['macetas']` (dentro de la
   malla); `params['persiana_color']`; `tendedero` interno entre dos ventanas; torreón de esquina en cabecera
   de manzana; chimeneas tubo de escape exageradas (bloque 8). Materiales `MAT_CASAS_atlas_<tono>` (Image
   Texture del atlas en Base Color, sin Mapping), excluidos de `aplicar_texturas.familia_de` (l.98-99) y de
   `mejorar_materiales.PREFIJOS` (l.24). Atlas: NUEVO `assets/atlas_fachadas.py` (PIL): 4096² con 8-10 tonos de
   estuco (de `white_stucco` recoloreado o del tile PIL), zócalo de piedra, cornisa, teja, contraventanas (4
   colores, abiertas/cerradas), persianas, balcón de forja (alfa), macetas (alfa), ropa (alfa, 4 variantes),
   alcantarilla, carteles de tienda genéricos (sin marcas); hasta W los decals con alfa van como geometría
   opaca (`macetas`, `tendedero` low-poly) y el atlas se usa solo para lo opaco.
4. `edificios_civicos_v2.py`: `build_iglesia(parent, seed)` (cúpula + campanile, <= 12 k tris) y
   `build_torreon`; `calle_kit.py`: `build_bolardo`, `build_tendedero(luz, seed)` (catenaria de `build_guirnalda`
   con prendas), `build_alcantarilla`. `exportar_ac` [W]: `CALLE_bolardo` -> `1WALL_`.
5. Plaza del ayuntamiento (s 1120-1160): pasar su huella a `urbanismo_spec.json` como `zonas_reservadas` para
   que el plan no choque (quita el `casa_muro`/`plaza_muro` de CASAS_casa.066).

**Dependencias y orden**: 2-escarpa + muros por vértice (quita las aletas; solo escena + asentar) -> 1+2
manzanas, aceras, patios (plan + escena + QA el mismo día) -> farolas/bolardos/adoquín -> 3 UV + atlas ->
soportales, iglesia, torreones -> decals alfa [W]. Depende de: 1 (bandas llanas finales, berma), 3 (paleta
Riviera, tiles). Lo necesitan: 7 (balcones con público), 8 (chimeneas, rejillas en fachadas nobles).
**CSP**: nada [E]; luces de farolas y ventanas [X] (bloque 9). **[W]**: `ksPerPixelAT` para decals, `1WALL_` para
bolardos, atlas 4096 sin tintar.
**Riesgos**: QA bloqueante (`urbanismo.py:2841` aborta): cambiar `verificar()` el mismo día; `revisar_urbanismo
.casa_casa` tolera 0.3 m (medianeras: 0); presupuesto (<= 5000 tris/casa; soportales +100, medianeras -400);
convenciones intocables (`CASAS_casa`, fachada +Y en y=0, hijo `CASAS_zocalo`, pivote en el centro de la
fachada); z-fighting de medianeras; `exportar_ac` descarta casas con `max(ys) > 2` (los soportales no mueven
la línea de fachada: OK).
**Verificación**: `renders/qa/urbanismo_*.png`, `urbanismo_informe.json` (0), `asentar.json`; capturas A/B 05/06/
10/39/40/50 + BASE; conteo de casas por sector en el log.
**Estimación**: 95 h-agente; 3 agentes (A: urbanismo.py + QA; B: urbanismo_escena + muros/escarpa + calle_kit;
C: casas_kit UV/atlas/soportal + edificios_civicos), 3 huecos de cola.

---

## Bloque 6 — AGUA Y COSTA (batimetría, orilla, escolleras, puerto-llanta, flota)

**Objetivo visual medible**:
- Degradado real por profundidad y distancia (turquesa 0-2 m -> azul profundo > 25 m / > 250 m de la costa) en
  Blender Y en AC, con franja de espuma de 6-10 m en la orilla; roughness 0.08 (hoy 0.04 deslumbra en 54).
- Orilla sin escalera de 4 m: franja `COSTA_orilla` (arena mojada / arena / espuma) que tapa el borde dentado
  donde la pendiente < 35 %; 300-500 rocas de orilla en acantilados y junto a muelles; 0 "banda blanquecina".
- Escolleras de bloques en dique (600-900 bloques), espigón de la carretera del puerto, cala del lazo y del
  casino (misma función); puerto deportivo con forma de LLANTA legible desde el aire (buje + 5 radios + pestaña,
  bocana con balizas); dársena dragada a -6 m (36 -> 60+ amarres ocupados).
- Flota: 7 tamaños de barco, veleros con velas izadas y escora coherente, lanchas con estela, yates VIP
  completos (12/12).

**Cambios técnicos**
1. NUEVO `03_blender/generar_mar.py` (python del sistema; tras `preparar_geometria`, antes de `construir_pista`):
   `prof = max(0, -z)`, `d_costa = EDT(mar)·4` -> `texturas/mar_color.png` 2048² sRGB (rampa por profundidad y
   distancia + ruido de 60 m + espuma `d_costa < 8`) + `texturas/mar_fondo.png` (arena clara `aerial_sand`
   recoloreada x degradado). API: `generar(geom, out_dir, res=2048)`.
2. `construir_pista.py` l.1476-1513: `AGUA` = rejilla de 32 m sobre la caja del terreno + 60 m con UV
   (x-x0)/ancho, (y-y0)/alto, y `AGUA_lejos` (anillo hasta 9 km, 8 quads, color profundo plano); `MAT_agua`:
   Image `mar_color` (sRGB) en Base Color (blanco), alpha 0.84, roughness 0.08, bump de olas (`agua_h` 40 m +
   una segunda de 7 m), custom props `ac_tex_max = 2048`, `ac_alpha_in_texture = 1` (alfa en el PNG para
   `DepthAware`); `AGUA_fondo` con material propio `MAT_fondo_marino` (`mar_fondo.png`) y el tramo -0.5..-6 m de
   la rampa del terreno a arena clara. `aplicar_texturas.familia_de` ('agua'): no duplicar bump (marcador).
3. `construir_pista.py` (tras TERRENO): malla `COSTA_orilla` (marching squares sobre `coastF = 0.5` suavizado,
   franja de 6 m a cada lado, 3 materiales por banda; solo donde pendiente < 35 %); parche al integrador:
   `zona_costa()` (rocas `vegetacion_kit.build_roca` 2-5 m en grupos de 2-4, hundidas 40 %, caliza del grupo,
   donde pendiente > 30 % o a < 60 m de muelles; unidas por material en `COSTA_rocas_<tono>`). Alta en
   `revisar_flotantes` (marinas, referencia = terreno bajo el centro) y `revisar_fisica_ac.NO_OBSTACULO` [W].
4. NUEVO `03_blender/assets/escollera_kit.py`: `build_bloques_a_lo_largo(parent, puntos, ancho, z_agua, seed,
   capas=2) -> 'ESCOLLERA_bloques'` (superelipsoides p 4-6 de 1.2-3 m, 48 tris, 3 tonos, 30 % bajo el agua, una
   malla por tono); usado por `puerto_kit.build_dique(bloques=True)`, `caminos_kit.build_camino(tipo='muelle',
   bloques=True)`, `roca_lazo._disenar_cala` y `roca_casino` (espigón). `test_escollera_kit.py`.
5. Puerto-llanta: `puerto_kit.build_buje(parent, r=17)` (plataforma, club náutico bajo, 4 palmeras),
   `zona_puerto` (parche): 5 radios de pantalán desde el buje a R-7 cada 40 grados, barcos a ambos lados cada 9 m,
   pestaña = segundo anillo de pretil + 18 farolas, arco 200 -> 230 grados, bocana de 50 m con 2 balizas;
   `terreno_montana`: disco de mar forzado a z -6 de radio `R_DQ + 12` en el centro del puerto (dragado).
6. Flota: `puerto_kit.build_velero(eslora 9-16, velas='izadas', escora)` (2 láminas de una cara), `build_yate
   (eslora 14-30, color_franja)`, `yates_kit.build_lancha(n_coches=0, estela=True)`; `zona_puerto` sortea 7
   tamaños; bahía 10-14 veleros al mismo viento (±15 grados) + 3-4 lanchas con estela; yates VIP 12/12 con el
   dragado. Nombres únicos (`YATE_*`, `PUERTO_yate.00N`) para animarlos en el bloque 9.

**Dependencias y orden**: 1+2 (agua) -> 3 (orilla, tras el relieve final) -> 4 (escollera_kit; en paralelo)
-> 5+6 (puerto y flota; independientes). Depende de: 1 (costa final), 2 (caliza de las rocas). Lo necesitan:
9 (nombres de barcos, DepthAware).
**CSP**: [E] batimetría por textura, orilla, escolleras, llanta, flota; [X] `[Material_Water] Type = SEA` (ya)
+ `UseAlphaFromDiffuse = 1` + `DepthAware = 1` + `CausticsMultiplier` + `[BOUNCED_LIGHT] SUPPORTED = 1,
CAUSTICS = 1, CAUSTICS_SCALE = 1`. **[W]**: `TEX_MAX` 2048 para `MAT_agua`, alfa en el PNG, tokens sin sombra
`COSTA_`, `ESCOLLERA_`, unión por material.
**Riesgos**: el tintado del writer aplana el degradado (modo "tal cual" [W]); z-fighting del quad de 18 km en el
horizonte (subdividir `AGUA_lejos`); `revisar_flotantes` hunde rocas de orilla si no se declaran; `_agua()` <
-1.8 para yates: lo resuelve el dragado; coste de la flota < 250 k tris con `n_coches=0`.
**Verificación**: capturas A/B 02/14/16/22/36/46/47/47b/54/60/61 + BASE; log de `zona_puerto` (barcos
colocados/posibles); `revisar_flotantes`; `kn5_check`.
**Estimación**: 55 h-agente; 2 agentes (A: generar_mar + AGUA + orilla + zona_costa; B: escollera_kit +
puerto-llanta + flota), 2 huecos de cola.

---

## Bloque 7 — PÚBLICO Y RELLENO (coches espectador, aparcamientos, bancales, villas, horizonte)

**Objetivo visual medible**:
- Coches-espectador con cara y variación: de ~80 a >= 600 (10-12 tipos x 10 colores x 3 expresiones x 4 bocas x
  bandera/no, escala 0.92-1.08, giro ±6 grados), en 8-12 aparcamientos explanados (2-3 filas de 6), 25 % de los
  balcones que miran a la pista, terraza del casino (10-16 de lujo con mesas y sombrillas), yates (6-8 por
  yate), 6-10 campamentos en la ladera de tierra (autocaravanas + tiendas).
- Praderas vacías rellenas: 40-80 bancales TALLADOS en el terreno (muro apoyado en su escalón, no "bandeja"),
  4-6 viñedos de 40x30 m, 6-10 villas con piscina en laderas que miran al mar, 6-8 carpas de hospitality en el
  paddock, 3 torres costeras en promontorios, 2º faro; público en gradas 6 siluetas x 10 colores x bandera 20 %.
- Horizonte: anillo de 7-9 cordilleras a 3.2-4.5 km (dos planos de profundidad) + 6-8 lomas de costa a
  2.4-2.8 km con 2-3 pueblecitos-silueta y un faro lejano, cubriendo 200 grados (N, E, O), abierto al S/SO
  (desde 54 y 14 se sigue viendo mar abierto); perspectiva atmosférica horneada en el color.

**Cambios técnicos**
1. `coches_kit_v2.py`: opciones `bandera` (24 tris), `mirada=(du,dv)`, escala por coche en `build_fila_aparcada`;
   `carrera_kit_v2._pub_coche`/`pit_kit`: 6 siluetas, 10 colores, bandera 20 %, 2 escalas (+25 tris/coche).
2. Aparcamientos (parche al integrador, sustituye el filtro `sitio_ok` de `zona_coches` l.2359-2404): 8-12 losas
   de grava 30x14 m con `explanar()` + cinta de tierra de acceso con valla (`_ramal_camara`/`poner` de
   `zona_camaras` como modelo) en exteriores de curva a 16-30 m del borde + muro de piedra seca
   (`ITAL_bancal_muro`) en el borde bajo; losas en `EDIF_PREF` para que `despeje_final` no las trate como prop.
   Torres de cámara sobre losa (defecto 8): mismo tratamiento (ramal de tierra + muro) o torre sobre peana
   enrasada; la plaza del palazzo con camino (`zona_paseo_mirador`, F-04).
3. Balcones: `casas_kit_v2` expone `info['balcones'] = [(x,y,z,rot)]` por casa; el integrador pone 1 topolino/
   compacto (escala 0.85) en el 25 % de los balcones a < 40 m de la pista (después del bloque 5).
4. Terraza del casino: 10-16 `yates_kit.build_coche_lujo` + `_mesa_alta`/`_sombrilla` en la meseta
   (`roca_casino info['centro_top']`), mirando a la pista.
5. NUEVO `03_blender/assets/camping_kit.py`: `build_autocaravana(seed)` (2.5 k tris, con cara), `build_tienda
   (seed)` (120 tris), `build_campamento(n, seed)` (3-5 unidades + hoguera + nevera + banderín) -> `CAMPING_*`;
   6-10 campamentos sobre mini-explanadas (r 9 m) en s 1300-2200 exterior con sendero de tierra.
6. NUEVO `03_blender/bancales_spec.py` (python del sistema, ANTES de `preparar_geometria`): elige 6-10 laderas
   de pradera (pendiente 10-35 %, sin pista a < 40 m, sin solares, sin senderos) y escribe `bancales_spec.json`
   (polilíneas por curva de nivel cada 1.6-2.2 m); `terreno_montana.construir` las TALLA (escalón real, como las
   terrazas); `zona_bancales` (parche) clona `italiano_kit.build_bancal` por tramos de 14-20 m con olivos del plan
   de vegetación (`olivos=False` si TreeFX los pone). `italiano_kit.build_vinedo(largo, filas, paso=2.4, seed)`
   (<= 35 tris/m), `build_torre_costera(alto=11)` (torreón con base ataluzada, 1.5 k tris), `build_faro(escala=0.6,
   bandas negras)`.
7. NUEVO `03_blender/assets/villa_kit.py`: `build_villa(seed)` (2 plantas 12x9, teja, pérgola, muro bajo, piscina
   8x4 con `agua_piscina`, 2 cipreses, 1 coche de lujo) <= 6 k tris -> `VILLA_*`; 6-10 villas sobre explanada con
   acceso de tierra en sector casino y retorno. `carrera_kit_v2.build_carpa(largo=16, ancho=10, color)`: 6-8 en el
   paddock (zona 5516-5670) y tras la tribuna interior, sobre `explanar_edificios`.
8. Horizonte: `zona_montanas_fondo` (l.2486-2533) -> `zona_horizonte` (parche): anillo con
   `montanas_fondo_v2.build_cordillera(largo 1400-1800, n_picos 5-7, alto 380-520, pie=True, res 0.5)` en dos
   filas (3.2 km baja verde-azulada, 4.5 km alta gris-azul) + `build_loma` x 6-8 a 2.4-2.8 km + pueblecitos-
   silueta (cajas crema 30x10x8, 20 por pueblo, 1 material) + faro lejano; `mejorar_materiales.py`: mezcla con el
   color del cielo del horizonte (0.70,0.84,0.98) al 35-55 % según distancia; `MAT_MONT_*` por `paleta.json`;
   <= 250 k tris; exentar `MONT_`/`HORIZ_` en `eliminar_sumergidos`/`revisar_flotantes`. [X] opcional:
   `[Material_DistantGeometry]` para que CSP los dibuje siempre.
9. Altas de prefijos nuevos (`VILLA_`, `CARPA_`, `CAMPING_`, `ITAL_vinedo`, `ITAL_torre`, `HORIZ_`, `COSTA_`) en
   `revisar_flotantes.EXENTOS`/`SOPORTE_PREF`, `asentar_objetos`, `despeje_final.EDIF_PREF`, `nada_en_pista`,
   `exportar_ac` (`1WALL_carpa`, muros de villa alcanzables) y `revisar_fisica_ac.NO_OBSTACULO` [W].

**Dependencias y orden**: 8 (horizonte: independiente, da contexto a todas las capturas: HACERLO PRIMERO) ->
1 + 5 + 6 + 7 kits en paralelo (cada uno con test y previews) -> 2 + 6 (bancales tallados: necesitan el relieve
final) -> 3 (tras bloque 5) -> 4 (tras bloque 2.6). Depende de: 1 (explanadas, bancales), 2 (meseta), 5
(balcones). Lo necesitan: 9 (nombres de objetos animables).
**CSP**: [E] todo; [X] `[Material_DistantGeometry]`, luces en villas/carpas.
**Riesgos**: draw calls (600 coches x <= 10 slots): unión por material por fila [W]; +300-400 k tris; el anillo
tapa la línea mar/cielo en 01 (abertura S/SO 160 grados); `despeje_final` quita `COCHE_` como prop si la losa no
está en `EDIF_PREF`; `revisar_coches` asienta cada coche en el terreno (explanar antes de clonar).
**Verificación**: logs de `zona_coches`/`zona_puerto` (nº con cara, filas); `presupuesto.py`; capturas A/B
09/10/12/21/25/26/27_x/28/29/30/39/41/42/47/48/62/63 + BASE; `revisar_flotantes`, `nada_en_pista`,
`revisar_fisica_ac` (barreras falsas = 0).
**Estimación**: 80 h-agente; 3 agentes (A: horizonte + bancales_spec + italiano_kit; B: camping_kit +
villa_kit + carpas + torres; C: coches/aparcamientos/balcones/casino + integración), 3 huecos de cola.

---
## Bloque 8 — CARIFICACIÓN (el mundo de Cars sin logotipos)

**Objetivo visual medible**:
- Chimeneas en forma de tubo de escape en el 100 % de las casas (ya existen en el kit: hacerlas 2x más grandes,
  cromadas, dobles en edificios nobles) y en hotel, ayuntamiento, casino.
- Estatuas de coche (2-4 m, piedra) en las 4 esquinas del casino y 2 en la plaza del ayuntamiento; rejillas
  de radiador y faros en las fachadas nobles (casino, hotel, ayuntamiento, campanile, iglesia): >= 1 motivo por
  fachada principal.
- Peñón del casino con silueta de Fiat Topolino vista desde el mar (toma 19) y desde el aire (36): la silueta
  (capó, cabina, rueda) se reconoce en una vista a 400 m y en la cenital, sin romper la bajada, el espolón ni
  la meseta.
- Monumentos +30-50 %: casino, campanile, ayuntamiento, hotel, faro, pórtico de meta, pasarela WGP, torres
  costeras, dirigible; proporciones Pixar (bases anchas, remates redondeados).
- 0 logotipos de marcas reales ni imágenes de la película (los carteles usan "WGP", "Porto Corsa", "Mondiale",
  "Allinol" ya existentes y nombres inventados).

**Cambios técnicos**
1. NUEVO `03_blender/assets/carificacion_kit.py`: `build_chimenea_escape(parent, alto, doble, seed)`,
   `build_estatua_coche(parent, alto=3.5, pose, seed)` (coche estilizado de piedra sobre pedestal, <= 2.5 k tris,
   material del grupo de caliza), `build_rejilla_fachada(parent, ancho, alto, estilo)` y `build_faros_fachada
   (parent, r)` (relieves de 10-20 cm para fachadas nobles, <= 400 tris), `build_cartel_generico(texto)`
   (sin marcas). `test_carificacion_kit.py` + previews.
2. `casas_kit_v2` (bloque 5.3): chimeneas x2 de tamaño, cromo (`MAT_CASAS_cromo`), doble en casas de >= 5
   plantas; `edificios_civicos_v2` (`build_ayuntamiento`, `build_hotel`, `build_campanile`, `build_iglesia`):
   parámetros `escala_monumento` (1.3-1.5), `rejilla=True`, `faros=True`, `estatuas=True`; `casino_v2`: 4
   estatuas en esquinas + rejilla en la fachada + faros flanqueando la entrada (alfombra roja ya existente).
3. Peñón Topolino: `roca_casino.py` `_forma`/`F_libre` (l.484-566): modular `R_top`/`R_bot` y la forma `a` por
   columna con un perfil de silueta (`penon_topolino.py`, legado, trae la silueta y helpers: reutilizar su
   curva 2D) SOLO en el arco de columnas que mira al mar y al aire (bahía -130..40 grados), manteniendo
   `R_cap_v`, muescas junto a la pista, horquillas y meseta; el "capó" y la "cabina" salen de la meseta por el
   lado del mar como bancos redondeados (q 6 -> 3) y la "rueda" es un domo lateral con estratos circulares.
   Verificar con `test_roca_casino.py` (vista 19 y cenital) y con los `checks` de bajada (pendiente <= 11 %,
   cala, 0 roca sobre carreteras) [U: confirmar que el usuario quiere la silueta Topolino en el peñón aunque
   rechazó el Fiat 500 para el coche-montaña].
4. Escala de monumentos: parámetro `escala` en las llamadas del integrador (`zona_casino`, `zona_meta` hotel/
   pórtico/pasarela, ayuntamiento/campanile, `zona_puerto` faro, `zona_dirigible` 48 -> 70 m) con re-explanado
   (`explanar_edificios` ya sigue el bbox) y comprobación de `revisar_urbanismo` (casa_pista, prop_calle) y de
   la meseta del peñón (`z_top_c`, `R_top`: el casino x1.4 debe caber: medir con `test_roca_casino`).
5. Guía de estilo de 1 página (`_rev/fase_visual/estilo_carificacion.md`): proporciones, cromo, ojos solo en
   coches, nada de logos; la revisa el usuario [U].

**Dependencias y orden**: 1 (kit) -> 2 (kits de edificios) -> 4 (escala) -> 3 (peñón, tras bloque 2.6).
Depende de: 2 (grupo de caliza), 5 (kit de casas). Lo necesitan: 7 (terraza del casino), 9 (luces en rejillas/faros).
**CSP**: [E] todo; [X] faros de fachada como `LIGHT_SERIES` de noche.
**Riesgos**: el casino x1.4 no cabe en la meseta (ajustar `R_top` o escala 1.25); la silueta Topolino compite
con la bajada tallada (G3 trazó 1249 m al 11 % con 2 horquillas: cualquier cambio de `F_libre` obliga a
re-trazar); tris de estatuas y relieves (+60 k); los `checks` de `roca_casino` (cala, pendiente, quiebro).
**Verificación**: previews del kit; `test_roca_casino` TEST_OK; capturas A/B 02/10/19/20/36 + BASE + una toma
nueva `66_penon_desde_mar` (400 m, lente 35).
**Estimación**: 35 h-agente; 2 agentes (A: carificacion_kit + edificios; B: peñón Topolino + escala), 2 huecos.

---

## Bloque 9 — CSP Y AMBIENTE (animados, pantallas, luces, GrassFX, Pure/Sol, FPS)

**Objetivo visual medible** (solo comprobable en el PC del amigo con CSP; aquí se valida la sintaxis y que
AC a pelo no cambie):
- Rotor del helicóptero girando (ksanim en bucle), dirigible y 3-5 barcos moviéndose por rutas cerradas (tipo
  Train), rotor en pose "en cruz" sin CSP.
- Las 2 pantallas de la recta muestran la cámara en directo (`CLOSEST_CAR`); sin CSP, una imagen estática
  "WGP LIVE" (1024x576) coherente.
- Noche: farolas del paseo, puerto, peñón y pueblo + ventanas + rejillas/faros del casino encendidos con
  `NIGHT_SMOOTH`; `[LIGHT_POLLUTION]` sobre el pueblo; `ksEmissive = 0` en el KN5 (nada brilla de día en vanilla).
- GrassFX solo en `MAT_cesped`; TreeFX con `IS_VISIBLE = 0` de las mallas; agua `SEA` + DepthAware + cáusticas.
- FPS: con 12 coches >= 60 fps en la GPU del amigo; si no, `lodIn/lodOut` en vegetación y DECO lejano, y
  unión por material (ya) + `ENABLE_TREES_LIGHTING = 0`.

**Cambios técnicos**
1. Blender (para que el KN5 tenga lo que ext_config necesita): materiales EXCLUSIVOS por tipo de bombilla
   (`MAT_farola_luz`, `MAT_casino_luz`, `MAT_guirnalda_luz`, `MAT_pit_luminaria`, `MAT_ventana_luz`,
   `MAT_faro_luz`) en `calle_kit`, `casino_v2`, `pit_kit`, `mirador_kit`, `roca_casino`, `puerto_kit`, con
   geometría pequeña y separada (clustering de CSP) y color "apagado" gris cálido; rotor con material propio
   `MAT_heli_rotor` y objeto `ANIM_heli_rotor` (pivote en el eje); `ANIM_dirigible`, `ANIM_yate_01..05` (pivote en
   el centro); mallas-ruta ocultas `ANIM_ruta_bahia`, `ANIM_ruta_dirigible` (tiras estrechas, `isRenderable = 0`
   [W]); pantallas (`carrera_kit_v2.build_pantalla`): cara frontal con UV 0..1 y material `MAT_pantalla_1/2` con
   Image 1024x576 (`texturas/pantalla_live.png`, generada con PIL: "WGP LIVE", sin marcas), marco con otro material.
2. [W] writer v2: `KEEP_PREFIXES += ('ANIM_',)` (nodo propio con matriz, como TERRENO/AGUA), `isRenderable = 0`
   para `ANIM_ruta_*`, `lodIn/lodOut` por malla desde custom props, textura real en la pantalla (sin tintar).
   Hasta W: `[WRAP_MESHES_...]` sobre `DECO_MAT_heli_rotor_p0` (funciona si el rotor es el único objeto con ese
   material).
3. `.ksanim` del rotor: `assets/exportar_ksanim_rotor.py` (FBX con 1 vuelta -> ksEditor en el PC del amigo, o el
   exportador ksanim de Blender [U permiso de instalar/descargar]); alternativa sin ksanim: `CLOCK_NEEDLE =
   SECONDS` (lento) o windmill con `WIND_SPEED_KMH_STOP = 0`.
4. `ext_config.ini` v1.1 [W, lo genera `color_ac.generar_ext_config`; hasta entonces, borrador en
   `_rev/fase_visual/ext_config_v1_1.ini`]: `[INCLUDE common/materials_track.ini]`, `[INCLUDE common/conditions.ini]`,
   `[Material_Water] Materials = MAT_agua, Type = SEA, UseAlphaFromDiffuse = 1, DepthAware = 1`, `[BOUNCED_LIGHT]
   SUPPORTED = 1, CAUSTICS = 1`, `[GRASS_FX] GRASS_MATERIALS = MAT_cesped, OCCLUDING_MATERIALS = MAT_asfalto,
   MAT_adoquin, MAT_acera, MAT_bordillo, MASK_* = -1, 0, -1, 1, SHAPE_TIDY 0.7`, `[LIGHT_SERIES_*]` +
   `[MATERIAL_ADJUSTMENT_*]` por familia de bombilla (`CLUSTER_THRESHOLD 6`, `CONDITION = NIGHT_SMOOTH`, `FADE_AT
   350`), `[LIGHT_POLLUTION]`, `[WRAP_MESHES]`/`[ANIMATED_*]` (rotor ksanim `DURATION 0.15`; Train para barcos
   `SPEED_KMH 8-12`, `DELAY_BETWEEN_RUNS`; dirigible a 120 m), `[DISPLAY_PANTALLA_1/2]` (`REGION 0,0,1024,576`,
   `MODE = CAMERA`, `CAMERA_0_TARGET = CLOSEST_CAR`, `FOV 40`), `[SHADER_REPLACEMENT_TERRENO]` (nm4 + tilingFix +
   `DOUBLE_FACE_SHADOW_BIASED`), `[TREES]` + `[SHADER_REPLACEMENT_VEG] IS_VISIBLE = 0`, `[MATERIAL_ADJUSTMENT_0]`
   palanca de brillo `ACTIVE = 0`. Cada sección con `ACTIVE` para activarla por separado.
5. FPS y LOD [W]: `lodOut` 400 m para `DECO` fino (bolardos, macetas, estatuas, matas), `lodIn/lodOut` 150 m
   para las tarjetas/billboards de vegetación, troceo DECO por celdas de 200 m (frustum culling), `castShadows`
   solo en pinos grandes y edificios. Lista de pruebas para el amigo: 12 coches en meta, viaducto y pueblo con
   CSP por defecto, Pure y Sol (gamma y LCS), con y sin DepthAware/cáusticas, con y sin TreeFX.

**Dependencias y orden**: 1 (materiales exclusivos, ANIM_, pantalla) en cuanto existan los kits de cada
bloque -> 4 (borrador ext_config) -> 2+5 (writer v2) -> 3 (ksanim) -> pruebas en el PC del amigo. Depende de:
3 (MAT_cesped), 4 (trees.txt), 5 (farolas), 6 (barcos), 8 (casino). Lo necesitan: nadie (es el cierre).
**CSP**: [X] todo, por definición; [E] solo "no romper": rotor en cruz, pantalla estática, bombillas apagadas,
`ksEmissive = 0`, nada de KN5 aparte que desaparezca sin CSP.
**Riesgos**: `WRAP_MESHES` sobre malla fusionada (no probado); signo de ejes de `PIVOT_POS`; `DepthAware` exige
alfa en el PNG; CSP < 0.1.79; FPS no medibles aquí; Pure/Sol solo visual en el PC del amigo.
**Verificación**: parser propio `_rev/validar_ext_config.py` (secciones, claves conocidas, materiales citados
existen en el KN5 vía `kn5_check --quiet`); `kn5_check`; lista de comprobación del amigo (web_csp §11 + web_treefx
§9).
**Estimación**: 30 h-agente; 1 agente (+ 1 para materiales exclusivos repartido en los kits), 1 hueco de cola;
más 2-3 rondas de prueba del amigo.

---

## Bloque W — Writer v2 (`04_export`, transversal; SOLO tras el cierre del zip v1.1)

**Objetivo**: que todo lo preparado en Blender (custom props `ac_*`, UV, imágenes, alfa, ANIM_) llegue al KN5
sin tocar nada más, con `kn5_check` ampliado y un KN5 de ensayo probado por el amigo ANTES del circuito.

**Cambios** (en `04_export/kn5_writer_opt.py`, `color_ac.py`, `kn5_check.py`, `exportar_ac.py`, `empaquetar.py`):
1. `analizar_material`: leer `m['ac_shader']`, `m['ac_props']`, `m['ac_samplers']`, `m['ac_tex_max']`,
   `m['ac_alpha_test']`, `m['ac_raw']` (imagen tal cual); si no existen, comportamiento actual.
2. `construir_textura`: modo raw (sin tintar, sin reducir a 512, tope `ac_tex_max`), conservar alfa + bleed,
   DDS BC1/BC3 con mipmaps para > 1024 (numpy, cabecera 128 bytes + bloques) o PNG si se confirma que AC genera
   mips [U prueba del amigo].
3. `escribir_texturas_y_materiales`: shader/props/samplers por material; `alphaTested`, `ksAlphaRef`,
   `alphaBlendMode` según props; `castShadows` por material (`VEG_` con alfa -> 1).
4. `con_tangentes`: tangentes reales desde la UV (MikkTSpace simplificado) cuando hay `txNormal`/`txDetailNM`.
5. Fusión: `KEEP_PREFIXES += ANIM_`; troceo DECO por celdas de 200 m; `lodIn/lodOut` desde `ob['ac_lod']`;
   `isRenderable = 0` para `ANIM_ruta_*`; `GROUND_PREFIXES`: sombra del terreno opcional.
6. `color_ac`: saltar materiales con `ac_shader` != ksPerPixel; familias nuevas; `generar_ext_config` escribe
   las secciones del bloque 9 desde un YAML/INI plantilla en `03_blender/ext_config_plantilla.ini`.
7. `kn5_check`: comprobación 9 (shader conocido, samplers/props esperados, tamaño/potencia de 2/<= 4096,
   materiales sin uso, UV fuera de 0..1 en materiales con atlas) y `--quiet` para el validador de ext_config.
8. `empaquetar.py`: copiar `extension/trees/`, `.vao-patch`, `CREDITS.txt`, `LICENSE_CC0.txt`, README de
   instalación (vao-patches, CSP).
9. KN5 DE ENSAYO (`04_export/ensayo/porto_ensayo.kn5`, < 5 MB): plano multicapa `_nm` + cubo `ksPerPixelNM` +
   quad `ksTree` con alfa + nodo `ANIM_` + 3 árboles TreeFX + pantalla con textura; lo prueba el amigo con la
   lista de comprobación; solo después se exporta el circuito con el writer v2.

**Dependencias**: bloqueado hasta que el equipo de v1.1 cierre [U fecha]; mientras tanto se prepara como rama
`04_export/_writer_v2/` (copia + diff) sin tocar los ficheros vivos. **Riesgos**: R4 (shader mal -> AC no
carga): mitigado por el KN5 de ensayo; DDS mal formado; tamaño del KN5 (+60-100 MB); no hay AC aquí.
**Verificación**: `kn5_check` 9/9 en ensayo y circuito; `leer_kn5_color.py`; informe del amigo.
**Estimación**: 60 h-agente; 1-2 agentes (secuencial sobre los mismos ficheros), 2 huecos de cola para
`exportar_ac` + 2-3 pruebas del amigo.

---
## 10. Orden recomendado de bloques (fases, con qué corre en paralelo)

Regla del usuario: "primero relieve, integración, paleta y densidad; no añadir objetos sin más". Y la regla
técnica: todo lo que cambia el terreno va ANTES de todo lo que se apoya en él; lo que necesita el writer v2 se
prepara en Blender desde el primer día y se exporta al final.

| Fase | Bloques (en paralelo) | Entregable visible | Cola Blender |
|---|---|---|---|
| F0 | 0 (infra) + 7.8 horizonte + 3.1 paleta.json + 4.1 vegetacion.py (plan con el terreno actual) | BASE "antes" congelada; carta de color; anillo de horizonte en todas las aéreas | 2-3 |
| F1 | 1 (relieve completo) + 2.1 grupo de caliza + 3.2 texturas (CC0 o PIL) + 4.2 kit v3 + 6.4 escollera_kit + 7 kits nuevos (camping, villa, carpas, torres, viñedo) | Macizo, acantilados, tierra tallada, cabo del McLaren; caliza en Blender; previews de todos los kits | 5-6 |
| F2 | 2 (rocas: lazo, peñón, McLaren, afloramientos) + 3.3-3.6 (máscara, multicapa, MAT_cesped, bisel, AO) + 5.1-5.2 (manzanas, escarpa, muros) + 6.1-6.3 (agua, orilla) | Las 3 rocas + McLaren integrados; terreno multicapa; pueblo denso y llano; mar con batimetría | 6 |
| F3 | 4.3-4.5 (integración del plan de vegetación, sotobosque, trees.txt/FBX) + 5.3-5.5 (atlas, soportales, iglesia) + 6.5-6.6 (puerto-llanta, flota) + 7.1-7.7 (público, aparcamientos, bancales tallados, villas, carpas) + 8 (carificación) | Bosque en masas, pueblo con atlas, puerto-llanta, público x7, carificación | 6 |
| F4 | 2.2 hornear_rocas + 3.6d hornear_objetos + 3.9 re-medir color_ac + 9.1/9.4 (materiales exclusivos, ANIM_, pantallas, borrador ext_config) + capturas finales (57 + nuevas) | Texturas horneadas; escena final en Blender; hojas A/B de los 9 bloques | 4 |
| F5 | W (writer v2) + 3.7 VAO + 9.2-9.5 + KN5 de ensayo -> prueba del amigo -> circuito completo -> zip v2 | KN5 v2 + extension/ (trees, vao-patch, ext_config) + README | 2 + amigo |

Dentro de cada fase, cada bloque entrega: módulo(s) + `test_<modulo>.py` + previews + parche corto para
`integrar_escena.py`/`preparar_geometria.py` (los aplica el coordinador) + hoja A/B del bloque + 3 líneas en el
REGISTRO DE ARREGLOS de `RONDA15_PLAN.md`. Un bloque no se cierra sin su hoja A/B desde las mismas cámaras y
sin los inspectores en verde (urbanismo 0, `revisar_urbanismo` 0, `nada_en_pista` 0 en vegetación/props,
`kn5_check` OK).

## 11. Duración total estimada

| Bloque | h-agente | agentes en paralelo |
|---|---|---|
| 0 Infraestructura | 10 | 1 |
| 1 Relieve | 75 | 3 |
| 2 Roca integrada | 95 | 4 |
| 3 Paleta / texturas / luz | 70 (+20 con W) | 2 |
| 4 Vegetación | 85 | 3 |
| 5 Pueblo | 95 | 3 |
| 6 Agua y costa | 55 | 2 |
| 7 Público y relleno | 80 | 3 |
| 8 Carificación | 35 | 2 |
| 9 CSP y ambiente | 30 | 1 |
| W Writer v2 + ensayo | 60 | 1-2 |
| Coordinación (parches al integrador, pipeline, hojas, registro) | 60 | 1 (coordinador) |
| **Total** | **~770 h-agente** | 5-6 de media |

Calendario de reloj con la cola de 6 Blender y 5-6 agentes en paralelo: F0 1 día; F1 4-5 días; F2 5-6 días;
F3 5-6 días; F4 2-3 días; F5 3-4 días de trabajo + el tiempo del amigo (3 rondas: KN5 de ensayo, 3 árboles,
circuito). **Unas 22-26 jornadas de 8 h** (5 semanas) si el writer v2 puede empezar en F5 sin esperar; si
`04_export` sigue cerrado al llegar a F5, el circuito se entrega en Blender (capturas) y el KN5 v2 queda para
cuando abran (+1 semana). Cada regeneración completa del pipeline cuesta ~1 h de cola; prever 25-35
regeneraciones en total.

## 12. Qué se ve en AC "a pelo" y qué solo con CSP (resumen)

- [E] a pelo: relieve, rocas y McLaren, caliza con estratos (horneada), terreno multicapa `_nm`, paleta, AO en
  difusos, bisel, árboles v3 con alfa test y sombra (tras W), pueblo denso con atlas, agua con batimetría,
  orilla, escolleras, puerto-llanta, flota, público, relleno, horizonte, carificación.
- [X] solo CSP: nm4 + tilingFix, VAO, TreeFX, GrassFX, luces de noche, animados, pantallas en directo,
  cáusticas/refracción, `DistantGeometry`. Todo en `extension/`, todo con `ACTIVE`, nada que desaparezca sin CSP.
- Hasta que exista W, el KN5 sigue siendo el de hoy (ksPerPixel + tintado) y "la verdad" es la captura de Blender:
  por eso Blender debe imitar lo que hará AC (misma máscara, mismos tiles, misma luz).

## 13. Preguntas que SOLO el usuario puede responder

1. **CSP**: ¿el amigo usa Custom Shaders Patch? ¿Qué versión (>= 0.1.79 para TreeFX)? ¿Tiene Content Manager
   con developer mode (tree converter)? ¿Pure, Sol o ninguno? Sin respuesta, todo lo [X] se entrega "inerte".
2. **Permiso de descarga de texturas CC0**: las 13 de `web_texturas_cc0.md` §5: 49 MB en 1K-JPG (recomendado) o
   186 MB en 2K-JPG; +4.4/16 MB con la opcional `marble_cliff_02`. ¿Sí/no y resolución? Si no, plan B con tiles
   PIL (estilo plano, también válido para Pixar).
3. **Permiso de descarga de `acc-bakeryoptix build-v22.zip`** (1.8 MB, Vulkan RT o CPU Embree) para el VAO; y
   del exportador ksanim de Blender (o se hace el ksanim en ksEditor en el PC del amigo).
4. **Cuándo se abre `04_export`** (cierre del zip v1.1) y si se acepta preparar el writer v2 como copia en
   `04_export/_writer_v2/` mientras tanto.
5. **GPU para Cycles** en este PC (bakes de 4 k: minutos con GPU, horas con CPU) y cuántos huecos de la cola se
   pueden dedicar a bakes.
6. **Pruebas del amigo**: ¿acepta 3 rondas cortas (KN5 de ensayo de 5 MB, 3 árboles TreeFX, circuito completo)
   y mandar capturas/FPS? Es la única forma de verificar shaders, alfa, mipmaps, LOD y FPS.
7. **"Bajada a la horquilla de la fuente"** (postal 4): ¿rotonda Loews (s 3564) o la horquilla C26 de tierra
   (s 2364)?
8. **Peñón Topolino**: ¿quiere la silueta de Fiat Topolino en el peñón del casino aunque rechazó el Fiat 500 para
   el coche-montaña? ¿Y la torre/fortín opcional en la roca del lazo?
9. **Paleta**: validar la carta de color (12 esferas) y los 8-10 tonos Riviera antes de propagarlos.
10. **Excepción a "sin bpy.ops salvo render"** para `bpy.ops.export_scene.fbx` (árboles TreeFX) y `Smart UV
    Project` (bakes), y para instalar nada (no hace falta: todo es Python del sistema + Blender).
11. **Escala de monumentos**: +30 % o +50 % (el casino x1.5 puede no caber en la meseta sin agrandarla).
12. **Presupuesto final aceptable**: ¿6.5 M tris / 450 MB de KN5 / 120 MB de texturas, o hay un tope más bajo
    por la GPU del amigo?
13. **Nombres en carteles y pantallas** ("WGP", "Mondiale", "Allinol" existentes): confirmar que ninguno es marca
    registrada que no quiera en el repo público.

## 14. Lista de "no hacer" (cosas del plan que desaconsejo, y por qué)

1. **No usar Hydra** (ozikazina) en el pipeline: add-on de Blender 4.0 que se engancha al contexto OpenGL de la
   ventana (`moderngl.get_context()`), no funciona en `--background`, sin soporte declarado para 5.x y no
   reproducible. Erosión NumPy propia (dandrino) en `erosion.py`: 8 s, determinista, con máscara de corredor.
2. **No escribir `ksMultilayer_fresnel_nm4` directamente en el KN5**: es un shader de CSP (sdk-shaders), en AC
   vanilla no existe y los nombres de sus 4 samplers de normal no están documentados. En el KN5 va
   `ksMultilayer_fresnel_nm` (vanilla, samplers verificados) y nm4 se activa por `[SHADER_REPLACEMENT]` en
   ext_config con `tilingFixR/G/B/A`.
3. **No intentar AO por color de vértice**: el vértice KN5 es pos+normal+uv+tangente (sin color). AO en el difuso
   (vanilla) + VAO `.vao-patch` (CSP).
4. **No usar `ksGrass`** para arbustos ni setos: CSP los oculta con GrassFX. Ni GrassFX sobre `MAT_terreno`:
   solo `MAT_cesped`.
5. **No subir la rasante de la tierra para "más desnivel"**: ya está al 16.5 % (> 12-15 % pedido) y la cima no
   puede subir (434 m de subida al 15 % = 126 m máximo). El desnivel que se VE es del terreno a los lados
   (pared/caída), no de la rasante; bajar el tope a 15 % y a 9 % en los apex de las horquillas.
6. **No mover el McLaren ni alargar su morro** para integrarlo (B11: pisa la horquilla s 716-888 y los solares):
   traer el terreno al coche (cabo bajo la zaga + faldón) en vez de llevar el coche al terreno.
7. **No subdividir el TERRENO a 2 m en toda la rejilla** ni poner Bevel en él: `cell` es único en todo el
   pipeline (JSON, Loews .npz, inspectores, asentar). La resolución fina va por texel (máscara 0.5 m) y por
   `txDetailNM`; la geometría de 4 m se queda.
8. **No hornear AO por casa** (216 atlas): rompe "1 material = 1 textura" y multiplica el KN5. AO solo en lo
   grande y estático (terreno, rocas, McLaren, 4 monumentos); en casas, bisel + sombras + atlas.
9. **No usar árboles fotográficos CC0 ni packs `.bin` de TreeFX de terceros**: rompen el estilo Cars y tienen
   licencia/estilo ajenos; los impostores se renderizan de nuestros propios modelos.
10. **No hacer de TreeFX la única vegetación**: sin CSP no hay árboles ni fallback. Capa KN5 obligatoria, TreeFX
    encima y `IS_VISIBLE = 0` solo con CSP (y confirmar versión antes de activar `HIDE`).
11. **No exportar los animados como KN5 aparte (opción C de la wiki)**: sin CSP desaparecerían. `ANIM_` en
    `KEEP_PREFIXES` (W) o `WRAP_MESHES` (CSP).
12. **No hornear `ksEmissive > 0` en el KN5**: en vanilla brilla de día. Emisivos solo por
    `[MATERIAL_ADJUSTMENT] CONDITION = NIGHT_SMOOTH`.
13. **No tocar `04_export` antes del cierre de v1.1**, ni la Loews (terreno congelado), ni el corredor de la
    pista, ni el viaducto, ni la extensión de la rejilla.
14. **No cambiar `diffuse_color` de los materiales medidos sin re-medir `color_ac`** al final (guarda ±0.02):
    hacer la re-medición una sola vez, en F4.
15. **No "rellenar praderas" con objetos antes del relieve y la paleta** (regla del usuario): villas, carpas y
    campamentos entran en F3, sobre explanadas del terreno final, nunca como "cajas sueltas en la loma".
16. **No usar Mix Shader ni atributos para nada que deba verse en AC**: todo lo que pase al KN5 va como imagen
    + UV + custom props `ac_*`; lo procedural queda para previews.
17. **No confiar en `camara_segura` en el "después"**: las cámaras congeladas no se mueven; si una queda dentro
    del terreno, toma nueva con otro nombre.

## 15. Anexo: KPIs por bloque (tabla única para el coordinador)

| Bloque | KPI | Hoy | Objetivo | Cómo se mide |
|---|---|---|---|---|
| 1 | pared y caída a 25 m (dirt) | 5 % | >= 45 % | numpy sobre geometria_3d.json |
| 1 | orilla z > 10 m (tramos elegidos) | 7.5 % | >= 40 % | idem |
| 1 | pct_natural_gt_100 | 0.28 % | 4-8 % | checks |
| 1 | terreno bajo la zaga del McLaren (120 m) | -4 m (mar) | >= 60 m | encaje_mclaren |
| 1 | cambio en el corredor por erosión | - | 0.000 m | checks |
| 2 | celdas > 37 grados con roca > 0.5 | 21 % | >= 90 % | numpy |
| 2 | afloramientos / pedruscos | 0 / 124 | 200-300 / 600-900 | log zona_afloramientos |
| 2 | lazo: superficie en bancos fuera del corte | 0 % | >= 60 % | roca_lazo checks |
| 2 | McLaren: repisa plana en 33/17 | sí | no | captura A/B |
| 3 | verde césped en capturas de piloto | ~45 % | < 8 % | medir_paleta.py |
| 3 | dientes de sierra / escalera (07/08/14/22) | sí | 0 | recortes A/B |
| 3 | kn5_check comprobaciones | 8/8 | 9/9 | kn5_check |
| 4 | árboles / tris de vegetación | 2.7 k / 1.74 M | 7-9 k / <= 0.9 M | presupuesto.py |
| 4 | árboles quitados por inspectores por pasada | ~140 | < 15 | asentar.json + log |
| 5 | huecos entre solares (QA) | 515 m | < 120 m | urbanismo QA |
| 5 | casas en pueblo_subida_ladera | 41 | >= 70 | urbanismo.json |
| 5 | fallos revisar_urbanismo | 23 | 0 | urbanismo_informe.json |
| 6 | amarres ocupados / posibles | 36 / 36 (41 barcos) | >= 60 | log zona_puerto |
| 6 | banda blanquecina de playa (16) | sí | no | captura A/B |
| 7 | coches con cara | ~80 | >= 600 | log zona_coches |
| 7 | bancales tallados | 5 (bandeja) | 40-80 (escalón) | bancales_spec + QA |
| 7 | anillo de horizonte | no | 200 grados, 2 planos | captura 01/13/14 |
| 8 | monumentos escalados / estatuas / rejillas | 0 | 9 / 6 / >= 5 | log integrador |
| 9 | secciones ext_config activas | 2 | 10-12 | validar_ext_config.py |
| W | KN5 de ensayo carga en AC | - | sí (amigo) | informe del amigo |
| Todos | tris / MB del KN5 | 5.26 M / 355 MB | <= 6.5 M / <= 450 MB | kn5_check |
