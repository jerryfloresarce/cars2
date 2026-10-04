# Plan B (RIESGO PRIMERO) para la fase visual de Porto Corsa

Arquitecto técnico, 04/10/2026. Ángulo: qué puede romper el pipeline, la física validada (cierre_ac, inspectores,
kn5_check 8/8), el tamaño del zip y el rendimiento en AC; cómo escalonar los bloques para que SIEMPRE haya un zip
jugable y cómo validar cada paso sin AC instalado. Solo se ha escrito este fichero. Fuentes: `PLAN_USUARIO.md`,
`director_final.md`, `RONDA15_PLAN.md` (convenciones y registro), los 9 informes de `_rev/fase_visual/`, las capturas
01/07/15/32/36/40/49/50/51/54, `_rev/pipeline_escena.sh`, `_rev/blender_cola.sh`, `04_export/hacer_zip.sh` (leído, no
tocado), `logs_final/` (mtimes) y `renders/qa/`.

---

## 0. Estado de partida y presupuestos (lo que NO se puede perder)

| Invariante validado hoy | Dónde se mide | Valor actual | Regla de esta fase |
|---|---|---|---|
| Física del circuito: cierre invisible, 0 huecos > 2 m, 0 escalones en pista/pit, rodadas de garajes 0, atajos 0 | `04_export/revisar_fisica_ac.py` -> `informe_fisica_final.json` (resumen) | ronda 4: todo 0 salvo 1 cambio de pendiente en s 2365 y 190 hoyos visibles de 0.65 m | ningún bloque puede empeorar un contador del resumen; los 190 hoyos solo pueden bajar |
| KN5 válido | `04_export/kn5_check.py` | 8/8 OK, 355 MB (`porto_corsa_opt.kn5`), 5.26 M tris, 7.07 M vértices, 572 mallas, 441 materiales, 438 texturas (12.5 MB) | 8/8 siempre; ver presupuestos abajo |
| Zip instalable | `04_export/porto_corsa_mod.zip` | 172 MB (02/10); v1.1 en cierre por otro equipo sobre `_rev/escena_rev.blend` | el zip siempre sale de una escena CONGELADA que pasó la puerta de calidad (sección 1.2) |
| Plan urbano | `urbanismo.py` (25 controles, `assert` l.2841 ABORTA el pipeline) | 0 fallos, 193 casas | 0 fallos y >= 190 casas o el pipeline no arranca |
| Escena | `revisar_urbanismo.py` -> `urbanismo_informe.json` | 23 fallos (director, defecto 10) | objetivo 0; mientras tanto NUNCA más de 23 y ninguno nuevo de tipo casa_pista/casa_muro/losa |
| `_rev/nada_en_pista.py` | `renders/qa/nada_en_pista.json` | 11 (cabezas de farola a 4.1 m sobre la calzada) | <= 11 y 0 en tierra |
| Terreno | `terreno_montana.construir` `checks` | celdas_invaden_pista 0, hierba_asfalto 0, fosos <= 1.5 m, costuras < 0.6, `loews_ref_dz_max` 0.000 | idénticos; la Loews a < 40 m es bit a bit la referencia `assets/_loews_terreno.npz` |
| Tiempo de una regeneración | `logs_final/` 12:57:56 -> 13:00:37 + capturas 13:01:00 -> 13:02:41 | ~3 min pipeline + ~2 min 57 capturas | iterar es barato: regenerar SIEMPRE antes de juzgar, nunca "a ojo" sobre la escena vieja |
| Cola de Blender | `_rev/blender_cola.sh` | 6 huecos, ~5 GB cada Blender | la fase visual usa como mucho 4 a la vez: el equipo del zip (hacer_zip.sh usa la misma cola, 3 Blender seguidos) necesita los otros |

Presupuestos duros (sin AC no se puede medir FPS: se controlan los indicadores que SÍ correlacionan con FPS en AC, y
se vigilan con `_rev/kn5_presupuesto.py`, sección 1.4):

| Indicador | Hoy | Tope de la fase | Motivo |
|---|---|---|---|
| Triángulos del KN5 | 5.26 M (vegetación 1.74 M = 33 %) | 6.0 M | las pistas Kunos van en 1-3 M; ya estamos al doble; cualquier bloque que añada tris lo paga la vegetación (bloque 4 baja a < 0.6 M) |
| Mallas (draw calls) | 572 | 800 | fusión por material del writer: cada material nuevo = 1 malla más por trozo de 65 k vértices |
| Materiales | 441 | 520 | ídem; prohibido "un material por instancia" |
| Bytes de texturas en el KN5 | 12.5 MB (todas <= 1024 px, 512 tintadas) | 80 MB | TEX_SIZE 1024 para roca/asfalto/estuco x4 bytes ~ 45 MB + máscara/batimetría |
| KN5 | 355 MB | 450 MB | el usuario ya instaló 355 MB sin quejas; 450 deja margen para +0.7 M tris |
| Zip | 172 MB | 250 MB (a confirmar con el usuario) | GitHub Release y descarga del amigo |
| Samplers por píxel del terreno | 1 (`txDiffuse`) | 7 (multilayer _nm) solo si el amigo lo prueba antes | sin AC no hay FPS: por eso el multicapa es la ÚLTIMA pieza, no la primera |

---

## 1. Infraestructura previa (bloque 0): sin esto no se puede juzgar ni entregar

### 1.1 Capturas antes/después con cámaras congeladas
- Ficheros nuevos en `03_blender/_rev/`: `tomas_capturas.py` (`construir_tomas(G, bpy) -> [(nombre, loc, tgt, lens)]`,
  copia de `renderizar_capturas.py` l.45-330 + tomas nuevas 60-63 y las 5 "postales"), `capturas_ab.py`
  (`--blend --geom --set BLOQUE --out DIR [--camaras cams.json | --guardar-camaras cams.json]`) y `montaje_ab.py`
  (PIL, hojas lado a lado). Esbozo completo en `entender_agua_publico_capturas.md` §9: adoptarlo tal cual.
- Regla: `camara_segura` solo en el "antes"; el "después" lee loc/tgt/lens del JSON y NO mueve nada; si una cámara
  queda dentro del relieve nuevo se avisa en `ab.log` y se añade toma nueva con otro nombre.
- Salidas: `renders/ab/<bloque>/{camaras.json, antes/, despues/, AB_*.png, hoja_<bloque>_piloto.png}`.
- Las 6 de piloto (s 300/800/1700/2900/3400/4150 = capturas 49-54) van en TODAS las hojas a tamaño completo.
- Coste: 2 renders de 13-18 tomas (~45 s cada uno) + montaje; 1 hueco de cola.

### 1.2 Puerta de calidad y escena congelada "candidata" (zip siempre jugable)
Hoy `pipeline_escena.sh` copia `porto_corsa.blend` a `_rev/escena_rev.blend` SIEMPRE (incluso con fallos), y
`hacer_zip.sh` exporta `escena_rev.blend`. Riesgo: un bloque a medias pisa la escena que el equipo del zip está
cerrando. Propuesta (solo `03_blender/_rev/`, sin tocar `04_export`):
- `_rev/pipeline_escena.sh` deja de copiar a `escena_rev.blend`; copia a `_rev/escena_candidata.blend` (+
  `geometria_candidata.json`, `urbanismo_candidata.json`).
- Nuevo `_rev/puerta_calidad.py` (python del sistema, lee solo JSON/logs): comprueba `urbanismo_informe.json`
  (fallos <= línea base y 0 de las familias bloqueantes), `nada_en_pista.json` (<= 11, 0 en tierra), `asentar.json`
  (`arboles_quitados`, `flotaban_mas_0_6`, `enterrados_mas_0_6` no peores que la base), `preparar_geometria.log`
  (checks del terreno), `integrar_escena.log` (`ERRORES: ninguno`, casas >= 190), y escribe `_rev/puerta.json`
  con `ok: true/false` y el diff contra `_rev/linea_base.json` (snapshot de hoy, 13:00).
- Nuevo `_rev/promover.sh`: solo si `puerta.ok` copia candidata -> `escena_rev.blend` y anota en
  `_rev/PROMOCIONES.md` (fecha, md5, bloque, hoja A/B). `hacer_zip.sh` sigue exportando `escena_rev.blend` sin cambios.
- Así SIEMPRE hay un `escena_rev.blend` que pasó la puerta; la fase visual trabaja en `porto_corsa.blend` y en
  la candidata; el zip vN+1 se hace cuando se promueve.

### 1.3 Export de ensayo sin tocar 04_export
`kn5_writer_opt.py` admite `BLEND`/`KN5`/`KN5_JSON` por entorno y `exportar_ac.py` `BLEND`/`SALIDA`/`GEOM`
(registro v2/v3): se pueden EJECUTAR sobre copias con salida en `03_blender/_rev/kn5_prueba/` sin modificar nada de
`04_export`. Después `kn5_check.py <kn5> <json> --no-wait`. Es la única comprobación "de verdad" del KN5 que tenemos
aquí: cada bloque que cambie nombres, prefijos, materiales con imagen o UV debe pasar por ella antes de promover.
Coste estimado: 15-30 min por export completo (desconocido aquí; el zip v1.1 lo mide). Hacerlo 1 vez por bloque, no
por iteración.

### 1.4 Presupuesto automático
`_rev/kn5_presupuesto.py <informe_check.json> [--base informe_check_opt.json]`: lee `totales`, `texturas`, `mallas`
y `materiales` del JSON de `kn5_check` y falla si se supera un tope de la tabla de §0 o si una familia (prefijo de
malla / `MAT_`) crece más del 50 % respecto a la base. Sin bpy, 60 líneas.

### 1.5 KN5 de ensayo para el PC del amigo (reduce el riesgo mayor de toda la fase)
Lo que NO se puede verificar aquí y condiciona los bloques 3, 4 y 5: que AC cargue `ksMultilayer_fresnel_nm`
con nuestros nombres de sampler/props, `ksPerPixelAT`/`ksTree` con PNG RGBA (alfa test), PNG embebido con
mipmaps, UV de usuario, texturas > 1024. Propuesta: `_rev/kn5_ensayo.py` (python del sistema, ~150 líneas, formato
KN5 v5 según `kn5_check.py` l.19-20 y `kn5_refs/`): escribe 5 KN5 minúsculos (un plano de 4 triángulos sobre un
suelo `1ROAD_` de 20 m + `AC_START_0`), uno por hipótesis, y `kn5_check` los valida. Se meten en el zip v1.2 como
`FUENTES/ensayos/` con un `LEEME.txt` de 10 líneas para el amigo ("carga porto_corsa_ensayo_X, haz foto"). Con sus 5
fotos se decide qué camino de export abrir. Hasta entonces, todo lo que se construya en Blender debe tener una
salida "a pelo" que ya funciona hoy (ksPerPixel + imagen tintada).

### 1.6 Lista de peticiones a 04_export (se entrega al cerrar v1.1, no se aplica desde la fase visual)
Fichero `_rev/fase_visual/PETICIONES_04_EXPORT.md`, una línea por petición, con bloque que la necesita y prueba
asociada: (P1) cablear `color_ac.separar_roca_terreno` + imagen de caliza en `MAT_terreno_roca`; (P2) `TEX_SIZE`
por material (1024 roca/asfalto/estuco) y `TEX_MAX` 2048 solo para `MAT_agua` y `txMask`; (P3) shader/props/samplers
por material (`m['ac_shader']`, `m['ac_samplers']`) + texturas sin tintar (`m['ac_imagen_tal_cual']`); (P4) alfa test
(`ksPerPixelAT`/`ksTree`, `alphaTested 1`, `ksAlphaRef 0.5`, PNG RGBA con bleed, `castShadows 1` por especie); (P5)
`kn5_check` comprobación 9 (shader conocido + samplers esperados + tamaños potencia de 2); (P6) prefijos nuevos en
`exportar_ac` (`CALLE_bolardo` -> 1WALL, `CARPA_`/`VILLA_muro` -> 1WALL si alcanzables), `SIN_SOMBRA_TOKENS`
(`HORIZ`, `MONT_`, `COSTA_`), `revisar_fisica_ac.NO_OBSTACULO` (COSTA_, HORIZ_, CAMPING_, VILLA_); (P7) `KEEP_PREFIXES`
`ANIM_` (nodos propios para CSP); (P8) `[TREES]`, `[GRASS_FX]`, `[LIGHT_SERIES]`, `[DISPLAY]`, `[BOUNCED_LIGHT]` en el
generador de `ext_config.ini` de `color_ac.py`, todos con `ACTIVE = 0` hasta prueba; (P9) unión por material de
`COCHE_fila*`, `PUERTO_dique_bloques`, `COSTA_rocas`; (P10) `repartir_terreno()` (alternativa A del multicapa).

Horas bloque 0: A/B 4 h, puerta+promoción 4 h, presupuesto 2 h, kn5_ensayo 8 h, peticiones 2 h = **20 h-agente,
2 agentes en paralelo (1 Blender cada uno), 1 día**. Es la primera tarea de la fase; ningún bloque promueve sin 1.1 y 1.2.

---

## 2. Escalonado de zips (siempre hay uno jugable)

| Zip | Contenido (solo lo que NO necesita cambios del writer salvo lo indicado) | Puerta |
|---|---|---|
| v1.1 (en cierre, otro equipo) | física ronda 4 + color_ac | la suya |
| v1.2 "paleta y fondo" | paleta única (3a), horizonte (7a), agua con batimetría (6a), kits de roca con `diffuse_color` de caliza (2a), vegetación v3 sin alfa + plan por máscaras (4a/4b), `kn5_ensayo` x5 | A/B de los bloques 3/6/7; kn5_check 8/8; presupuesto; física sin cambios (no se toca terreno) |
| v1.3 "relieve y roca" | relieve 1a-1c (+1d si estable), roca por pendiente y afloramientos (2b/2c), McLaren faldón (2d), pueblo muros+manzanas (5a/5b), costa/escollera/puerto (6b-6d) | TODO el resumen de `revisar_fisica_ac` igual o mejor; urbanismo 0; A/B de piloto |
| v1.4 "superficies" | lo que dependa de P1-P5 según resultado de los ensayos del amigo: terreno multicapa o alternativa A, atlas de fachadas, árboles con alfa, texturas CC0 1K, AO en diffuse | kn5_check 9 nuevo; presupuesto de texturas; ensayos OK |
| v1.5 "CSP" | ext_config completo (luces, GrassFX, animados, pantallas, cáusticas), trees.txt + .bin, vao-patch | se prueba SOLO en el PC del amigo; cada sección con ACTIVE para apagarla |

Regla de retroceso: si un zip vN+1 falla en el PC del amigo, vN sigue en la Release; `escena_rev.blend` de cada
promoción se guarda como `_rev/promociones/escena_vN.blend` (42 MB cada una; borrar las antiguas al cerrar la fase).

---

## 3. Bloques (riesgo primero)

Formato de cada bloque: objetivo medible / cambios concretos / dependencias y orden / esencial (AC a pelo) vs extra
(CSP) / riesgos y verificación / horas y agentes. "Coordinador" = quien edita `integrar_escena.py` y
`preparar_geometria.py` (regla RONDA15 l.33-34): esos cambios se entregan como parches pequeños y probados en copia.

### Bloque 1: RELIEVE (riesgo ALTO: toca `terreno_montana.py`, del que cuelgan urbanismo, McLaren, senderos, cámaras, coches, física)

Objetivo medible (medido con numpy sobre `geometria_3d.json`, script en `_rev/medir_relieve.py`):
- Tramo de tierra (s 1430-2440), a 25 m del borde: "pared > +8 m en un lado Y caída < -8 m en el otro" del 5 % al
  >= 40 % de las muestras; a 50 m del 22 % al >= 60 %.
- Macizo tras `pueblo_subida_ladera`: terreno a 120 m del borde >= 110 m de media (hoy 83) sin bajar
  `checks['coche_120m_pct_ge_90']`.
- Orilla: celdas de costa con z > 10 m del 7.5 % al >= 25 % en los tramos elegidos (lado +1 de s 170-402 y 616-820,
  lado -1 de s 2770-2976, costa N/NE); 0 % de cambio a < 15 m de la pista.
- Invariantes: `celdas_invaden_pista` 0, `hierba_asfalto` 0, fosos <= 1.5, costuras < 0.6, `loews_ref_dz_max` 0.000,
  `pct_natural_gt_100` <= 5 % fuera de la máscara del macizo trasero, urbanismo 0 fallos y >= 190 casas,
  `encaje_mclaren.evaluar()` con pista bajo huella 0 y holgura >= 4 m, hoyos visibles (`revisar_fisica_ac`) <= 190.
- Postales: 5 tomas nuevas en `tomas_capturas.py` (`64_postal_tunel_salida` s 560, `65_postal_cima` s 1870 mirando
  S/SE, `66_postal_puente_casino` = 54, `67_postal_horquilla` (Loews s 3564 o C26 s 2364: pregunta al usuario),
  `68_postal_puerto` s 5100) y juicio en la hoja A/B.

Cambios concretos, en 4 pasos independientes (cada uno con `python preparar_geometria.py` + `python urbanismo.py`
con `GEOM_OUT`/`QA_DIR` a una carpeta de prueba ANTES de tocar `geometria_3d.json`):
- 1a. Tierra tallada (`terreno_montana.py`): `peso` del tirón `_idw_pull` 0.5 en s 1430-2440 (l.1083);
  `techo_desmonte_c1(z0, dedge0, pend)` con `pend` como ARRAY (l.720-724/1297): 1.8-2.0 en el lado interior de cada
  curva de tierra (signo de `_kap[g_near]`); `s_fl` por celda (l.1306-1310) 1.2-1.5 en el lado exterior con berma
  llana `d_llano` de 6-8 m (arcén + pacas + cierre invisible a w/2+6.75). NO tocar `MAXG` (§6 "no hacer").
- 1b. Macizo trasero + cara tras terrazas: `LANDFORMS` (l.135-175) 'Espolón del coche' h 150 -> 190-200, s_foot 0.47 ->
  0.65, p 1.3 -> 1.6; 'espolón SO' +40; amplitud ridged l.394 `6 + 40*clip(M/200)`; limitador por celda
  (sustituir la llamada l.1123 por `limitar_pendiente_mascara` dos veces: 0.8 a < 150 m de la pista, 1.4 en la
  máscara del macizo); `techo_tras_terraza` (l.731-739, 1458-1461): berma de 15-25 m entre patio y arranque de la
  cara, bancales también en `w_coche` (quitar la exclusión `w_tope` l.1460 solo si `checks['coche_120m_*']` no baja),
  costillas l.1823 tope 2 -> 5 m en caras > 20 m.
- 1c. Acantilados (solo tramos elegidos, por máscara `_acant` ampliada): `r_prot` 30+1.7(z-4) -> 20+0.8(z-4) (l.978) en
  esos tramos, `pend` 2.5-4.0 y topes F-07/`_pm` (l.1203-1211) relajados ahí, fundido J1 170 -> 60 m, costillas
  `_wcf` extendidas a `acantilado & _acant`. Nunca a < 25 m del asfalto (`_acant` = 0), nunca Loews < 90 m, peñón
  r < 1.9, viaducto < 20 m, McLaren + 25 m.
- 1d. Erosión (nuevo módulo `03_blender/erosion.py`, python del sistema, numpy+scipy; API
  `erosionar(z, cell, w_eros, roca, iters=250, semilla=42, res_mult=2) -> (z_nuevo, delta)`; método de rejilla
  dandrino a 2 m con reposo térmico por material y remuestreo a 4 m; medido ~6-8 s a 460x450). Inserción en
  `construir()` entre l.1127 y l.1135 sobre `M`, con `w_eros` = producto de máscaras ya existentes
  (`entender_terreno.md` §6); barrancos N1 (l.1135-1161) atenuados (`_dg` x0.5) o apagados si doblan canal.
  `delta` fino (1-2 m) se guarda en `extras['erosion_detalle']` para la máscara del bloque 3.
- 1e. Coordinador: `tomas_capturas.py` (postales); `integrar_escena.zona_tunel` solo si 2d cambia parámetros;
  `urbanismo_spec.json` sin cambios de contrato (21/6/0.5 m).

Dependencias y orden: 0 -> 1a -> 1b -> 1c -> (bloque 2b/2c en paralelo sobre la geometría de 1c) -> 1d al final con
todo estable. Cada paso: capturas A/B (`relieve`), `python terreno_montana.py <qa>` con
`assets/_geom_snapshot_terreno.json` ACTUALIZADO primero (hoy es anterior a E5), pipeline completo, puerta.

Esencial / extra: TODO es esencial (geometría del KN5). Nada de CSP. Aviso: el TERRENO no proyecta sombras en AC
(`GROUND_PREFIXES` del writer): un macizo más alto no dará sombra a la pista en AC aunque sí en las capturas; la hoja
A/B debe incluir una variante "sin sombras de terreno" (render con `cast_shadow` apagado en TERRENO) para no engañarse.

Riesgos y verificación:
- Tajo de cantera más alto tras las terrazas (defecto 3) si 1b sube el macizo sin la berma: verificar con capturas
  05/06/39/50 y `foso_*`.
- Pretiles/guardarraíles con el pie al aire (1c): `construir_pista._pretil` pie min(ze-2.5, zt-1.5); rayos como en el
  registro v3 pista N1 (barrera en 100 % de muestras a 0.3/0.7 m).
- Caídas en la escapatoria (1a/1c): `cierre_ac.muros_cierre` cierra antes de cantos > 0.4 m; `revisar_fisica_ac` (o)
  debe seguir en 0; si el terreno cae > 0.5 m a < 6.75 m del borde el cierre se adelanta y el coche "choca con el
  aire": por eso la berma de 6-8 m es obligatoria.
- Más pacas (`pacas_tierra` E6: filas donde cae > 2.5 m a 10 m) y coches/cámaras quitados por desnivel: contar en
  los logs (`asentar.json`, `integrar_escena.log`).
- Senderos CIMA/ERMITA se replanifican solos (A*): comprobar `sendero_volado` en `revisar_urbanismo`.
- McLaren más o menos enterrado (B11): `encaje_mclaren.evaluar()` tras cada paso; 1b cerca de (-600, 350) exige
  repetir `test_montana_mclaren` con la geometría nueva.
- Erosión: depósito en la vega/orilla (np.minimum con z previa en `_dm1 < 40`), cambios en el corredor = 0 por
  construcción (reglas duras después), coste +10 s por pasada.
- Cámaras aéreas congeladas dentro del macizo nuevo: aviso de `capturas_ab.py`, toma nueva.

Horas / agentes: 1a 8 h, 1b 12 h, 1c 10 h, 1d 10 h (módulo 6 + integración 4), QA/pipeline/A/B 8 h, coordinador 6 h =
**54 h-agente; 2 agentes (terreno + erosión/medidas) + coordinador; 2 huecos de cola**.

### Bloque 2: ROCA INTEGRADA (riesgo MEDIO en material, ALTO en Boolean del McLaren y en el macizo del lazo)

Objetivo medible:
- Celdas de tierra con pendiente > 35° que llevan roca (atributo > 0.5 o nz < 0.78): del 21 % al >= 80 %, sin manchas
  < 12 celdas (apertura 3x3) y con pie de derrubios.
- Afloramientos: 150-300 piezas en cinturones (pendiente 0.5-1.0), 0 a < 12 m del asfalto, 0 dentro de casas/calles.
- McLaren: terreno/faldón toca la carrocería hasta la cintura en los flancos (medido en el marco local: a x = -3R,
  z del apoyo >= umbral + 0.3R); 80-150 pedruscos; grietas en el macizo; `encaje`: pista bajo huella 0, holgura >= 4 m.
- Lazo: >= 2 bancos verticales de 8-14 m con repisa >= 2.5 m visibles desde la 34_general; pinos en repisas; todos
  los `checks['ok']` de `roca_lazo._comprobar` a 0.
- Capturas: 13/19/32/33/34_general/36_general/45/54 A/B.

Cambios concretos:
- 2a. `assets/materiales_roca.py` (nuevo, bpy): `ng_caliza_estratos(nombre='NG_caliza_estratos') -> NodeGroup` con
  entradas (tono_base, tono_junta, periodo_m, bump, mojado) en `Geometry.Position` (mundo), estratos por z, bancos
  8-14 m, grano 0.3-1 m, manchas ±10 % (no ±50 %: es la "bruma"); `aplicar_a(material, tono)` que enchufa el grupo
  al Base Color dejando `diffuse_color` = media (lo que lee el writer) y el nodo `Math.002`/`ROCA_mascara` intacto
  en `MAT_terreno`. Enchufar en `construir_pista._roca_terreno` (l.252-337), `roca_lazo._mat`, `roca_casino._mat`,
  `montana_coche_v2._mat_piedra`. Unificar `_PALETA` de roca_lazo (l.150-175) y roca_casino (l.99-116): leer
  `paleta.json` (bloque 3). `aplicar_texturas.aplicar_roca` (l.359-398): bajar manchas o retirar familia `roca`.
- 2b. Máscara 35-40°: `terreno_montana` l.2261-2274 umbral natural 1.0 -> 0.75 ±0.1 ruido, banda "pie de derrubios"
  0.5 a 6-10 m bajo cada afloramiento; `construir_pista._roca_terreno` l.203-206 `talud` 0.50-0.56 -> 0.70-0.78 y
  sin `ROCA_llano_hierba` donde atributo = 1; `aplicar_texturas.FAMILIAS['hierba'].proy` FLAT -> BOX. Petición P1
  para que `color_ac.ROCA_NZ/ROCA_ATR` sigan los mismos umbrales.
- 2c. `assets/afloramiento_kit.py` (nuevo) + `test_afloramiento_kit.py`: `build_afloramiento(parent, largo, alto,
  seed) -> obj 'AFLOR_losa'` (300-900 tris, 2-4 bancos, cornisas, pie en talud, material del grupo 2a) y
  `build_pedrusco(parent, r, seed)` (reutiliza `montana_coche_v2._pedrusco`). Coordinador: `zona_afloramientos`
  tras `zona_tierra` (candidatos `pendiente_terreno` 0.5-1.0, rotación por gradiente, base 1-2 m enterrada,
  cinturones; exclusiones `_sitio_lejos_pista` >= 12 m, `_libre`, `zonas_excluidas`, rocas de los 3 generadores,
  Loews). Alta de `AFLOR_` en `asentar_objetos.SOPORTE_PREF`/`ASENTAR_NO`, `revisar_flotantes.EXENTOS` (se
  asientan por su base enterrada, no por z=0), `despeje_final` (prop), `_rev/nada_en_pista` (no permitido:
  deben estar lejos). Presupuesto 300 x 600 = 180 k tris.
- 2d. `assets/montana_mclaren.py`: `_K_FALDA` 0.36 -> 1.2-1.7 fuera de [-1.3R, 1.5R] y faldón hasta la cintura
  (`+0.72R`); `_bloques` 28 -> 80-150 por altura; grietas en macizo/faldón (horizontales en juntas + 3-5
  verticales por bloque, mismo `_grieta_v`); `_vegetacion` tipo "junta" y `_VEG_TRIS_MAX` 3400 -> 8000; `hueso`
  0.80 -> 0.58, `cristal_pulido` rugosidad 0.26 -> 0.5. El "túnel por la rueda" (`alto_base` 12 -> 19-20) se
  deja para una decisión del usuario (§5): cambia `TUNEL_suelo`/galerías (1ROAD/1WALL) y obliga a repetir
  `revisar_tunel.py` + física.
- 2e. `assets/roca_lazo.py` `_bancos_naturales(M, G, seed)` tras l.3490: cuantización en bancos hb 8-14 m con fase por
  ruido 2D de 40-80 m, cara 80-88°, repisa 2.5-6 m, SOLO restando (M' <= M), restringida a `o > o_b + 8` y fuera de
  rasgos dilatados 6-10 m; 2-3 espolones (`_Macizo.domo` a 3-4, b 0.6-0.9) en el lado NE/N; `_poblar`: pinos en
  repisas nz > 0.9 y ancho >= 3 m. Torre/fortín opcional: pieza de `italiano_kit` (`build_torre_costera`, bloque 7).
- 2f. `assets/roca_casino.py` `_perfil` cotas cada 1.5-2 m (27 k -> ~80 k tris), `estrato()` labio 1.5-3 m, `textura()`
  con ruido de 2-5 m; meseta `MAT_PPUEBLO_plaza/_borde/MAT_PENON_muelle` a familia piedra y -25 % de luminancia.
- 2g. `03_blender/hornear_rocas.py` (nuevo, Cycles por la cola, DESPUÉS de `aplicar_texturas`): Smart UV Project +
  bake Diffuse (+AO multiplicada) de `TUNEL_acantilado`, `PENON_puente_roca`, `PENON_roca` a 2048/2048/1024, material
  por objeto `MAT_ROCA_<obj>` con Image como Base Color y `diffuse_color` blanco. Solo útil cuando exista P3
  (imagen sin tintar); mientras tanto el bake se usa SOLO para las capturas y el A/B.

Dependencias y orden: 2a (independiente, primero: cambia 5 capturas sin riesgo) -> 2b (tras 1c, comparte
`terreno_montana`) -> 2c (tras 1b/1c: candidatos sobre el relieve final) -> 2d (independiente de 1 salvo `encaje`)
-> 2e (independiente; es el más largo) -> 2f -> 2g (al final, tras bloque 3 paleta).

Esencial / extra: en AC a pelo HOY ninguna roca lleva textura (colores planos 8x8) y la roca del terreno es
hierba (`separar_roca_terreno` sin cablear). Esencial mínimo que SÍ llega con el writer actual: `diffuse_color` de
los kits = media de la caliza del grupo (2a), geometría nueva (2c/2d/2e/2f) y, con P1, la roca del terreno como
material plano de caliza. Texturas horneadas (2g) y multicapa dependen de P2/P3 (v1.4). Extra CSP: VAO (bloque 3).

Riesgos y verificación:
- 2b convierte de golpe el 28 % de las celdas en candidatas: hacerlo junto con la paleta (bloque 3) o se ve "todo
  gris"; medir el % y mirar 07/09/21/51.
- Boolean del McLaren (2d): `test_montana_mclaren` seeds 0/3/7/11 + config del integrador (no-manifold 0, 1 cáscara,
  EXACT del túnel 0); red de seguridad "sin grietas" ya existe; +tris -> presupuesto.
- Lazo (2e): H7 ya se intentó con ridged isótropo y represaba cuencas: solo restar, comprobar
  `n2['celdas_rellenas']`, `test_roca_lazo` con todos los checks (casas, carreteras, matas, contacto, orientación,
  `cerca_asfalto_n` 0); tris 175 k -> +20-40 % (troceo del writer a 65 k vértices).
- Afloramientos (2c): prefijo nuevo -> si no se da de alta en los inspectores se borra o se hunde; cualquier pieza a
  < w/2+6.75 m del borde es "visible no físico" para `revisar_fisica_ac` (o): regla >= 12 m.
- `_paredes_de_roca` elige por subcadenas `roca`/`caliza`: no renombrar materiales del McLaren (cabecera l.147-149).
- Bake (2g): Cycles con 7 M vértices, 10-30 min por objeto en CPU; solo 3 objetos.

Horas / agentes: 2a 8, 2b 6, 2c 14, 2d 20, 2e 16, 2f 6, 2g 10 = **80 h-agente; 3 agentes (material+kit, McLaren, lazo/casino)
+ coordinador para `zona_afloramientos`; 3 huecos de cola**.

### Bloque 3: PALETA, TEXTURAS Y LUZ (riesgo BAJO en Blender, ALTO en la calibración color_ac y en el export)

Objetivo medible:
- Un único `03_blender/paleta.json` leído por >= 9 sitios (tabla de `entender_materiales.md` §3.a); 0 valores RGB
  de terreno/roca/teja/vegetación escritos a mano fuera de él (grep).
- Verde césped `hierba_d` fuera del terreno: solo en `MAT_cesped` (jardines, rotondas, meseta del casino).
- Terreno en Blender con máscara de 4 capas por texel (2048 px, 1 px/m): bordes hierba/roca sin escalera ni rombos en
  07/08/14/22 (inspección visual A/B) y 0 "hierba estirada" (BOX o roca a > 35°).
- Variación: parches de pradera (baja frecuencia) presentes también en AC vía `txDiffuse` del multicapa o vía 4-6
  materiales con ruido por cara (alternativa A).
- Rendimiento: bytes de texturas <= 80 MB; KN5 <= 450 MB.

Cambios concretos:
- 3a. `paleta.json` + `03_blender/paleta.py` (`cargar()`, `rgb(nombre)`, `familia_ac(nombre)`); lectores:
  `texturas/generar_texturas.py` (tintes), `construir_pista.py` l.86-114/179-181/262-263/1169/1285, kits de roca
  (2a), `casas_kit_v2.PALETA_FACHADA` l.87 (tejas, estucos Riviera), `vegetacion_kit_v2._PALETA` (oliva/salvia),
  `olivos.py`, `italiano_kit.py`. Regla: Base Color sin enlazar o `diffuse_color` = media lineal deseada.
- 3b. Tiles: `generar_texturas.py` nuevos `hierba_seca_d`, `matorral_d`, `cesped_d`, `caliza_d` (ocre, juntas cálidas),
  `teja_d` terracota, `tierra_d` ocre; re-medir medias -> `aplicar_texturas.FAMILIAS.ganancia`; familias nuevas
  `cesped`, `matorral` en `familia_de` (l.73-101) y en `color_ac._REGLAS` (petición, R2). CC0: solo si el usuario
  autoriza la descarga (§5): `texturas/recolorear_cc0.py` (luminancia + tinte de paleta, 1024 seamless comprobado
  con mosaico 3x3) y `CREDITS.txt` en el zip; lista y pesos en `web_texturas_cc0.md` §5 (13 texturas, 49 MB 1K-JPG).
- 3c. Terreno multicapa en Blender: `construir_pista.py` crea UV planar en TERRENO (`me.uv_layers.new`, u=(x-x0)/(nx*cell),
  v=(y-y0)/(ny*cell)); nuevo `03_blender/mascara_terreno.py` (python del sistema, tras `preparar_geometria`): lee
  `geometria_3d.json` (z, pendiente, `mascara_roca`, `mar`, distancia a pista/pueblo via `urbanismo.json`,
  `erosion_detalle` de 1d) y escribe `texturas/terreno_mask.png` (RGBA 2048, R matorral, G hierba seca, B tierra,
  A roca, suma 1, bordes con ruido 10-30 m) + `texturas/terreno_ao.png` (AO numpy: cavidad + horizonte + hillshade
  suave, 2048) + `texturas/terreno_base.png` (color de baja frecuencia x AO = `txDiffuse`); `mat_terreno()` nuevo:
  Image máscara (UV) + 4 tiles (UV x mult) mezclados por canal, x base; `aplicar_terreno()` se retira para
  `MAT_terreno`. Mantener el nodo `ROCA_mascara`/`Math.002` como salida escalar (A de la máscara) para revisores y
  `color_ac`.
- 3d. Salida a AC (dos caminos, decididos por los ensayos de 1.5): (A) `repartir_terreno()` en `exportar_ac.py` (P10):
  4-6 materiales `MAT_terreno_{matorral,seca,tierra,roca,trans1,trans2}` por cara con ruido, tiles tintados de 512:
  0 cambios de formato, kn5_check ya lo valida, bordes duros de 4 m (mitigados con 2 clases de transición y
  subdivisión a 2 m en una banda de 20 m junto a la pista: +40-50 k vértices). (B) `ksMultilayer_fresnel_nm`
  (shader de Kunos; NO `_nm4`, que es de CSP) con `txDiffuse`+`txMask`+`txDetailR/G/B/A`+`txDetailNM` (P3): por
  texel, exige `TEX_MAX` 2048 para `txMask` (P2) y el ensayo del amigo. Extra CSP: `[SHADER_REPLACEMENT] SHADER =
  ksMultilayer_fresnel_nm4` + `tilingFixR/G/B/A` en `ext_config.ini` (P8) sobre (B).
- 3e. AO y bisel: AO del terreno en `terreno_base.png` (3c) -> llega a AC solo con (B); AO de rocas/McLaren en 2g;
  "bisel" = `shade_smooth` + Auto Smooth 30-40° en los kits (casas, cívicos, pit, carrera, puerto: hoy muchos en
  flat): el writer exporta `corner_normals` y suelda por posición+normal+uv (l.434-445): vigilar vértices (+10-20 %
  en kits, nunca en TERRENO). Extra CSP: `acc-bakeryoptix` v22 (1.8 MB, descarga con permiso) sobre el KN5 final ->
  `porto_corsa.vao-patch` en el zip con instrucción "copiar a assettocorsa/extension/vao-patches/"; CPU (Embree)
  vale; tiempo decenas de minutos con 5 M tris; no comprobable aquí.
- 3f. Re-medir color_ac UNA vez al final de la fase (no por bloque): `_rev/color_ac/render_ac.py` (90 s) +
  `medir_objetivos.py` + `medir_albedo.py` (04_export JSON: petición o lo ejecuta el equipo del zip). Mientras
  tanto, los materiales con `diffuse_color` cambiado > 0.02 caen al modelo albedo x luz (peor pero no roto).
- 3g. Luz de las capturas: `construir_pista.py` l.1566-1618 sol 34° y `view_transform Standard` se mantienen (es la
  referencia de color_ac). Añadir en `capturas_ab.py` la variante "sin sombras de TERRENO y vegetación"
  (`castShadows=0` en AC) para juzgar lo que verá el amigo.

Dependencias y orden: 3a -> 3b -> (2a) -> 3c (necesita 1d opcional y 2b) -> 3e kits en paralelo -> 3d según ensayos
-> 3f al cierre. 3a/3b/3e pueden ir YA (v1.2).

Esencial / extra: esencial = paleta en `diffuse_color` (llega hoy), tiles tintados nuevos (llegan hoy), (A) o (B).
Extra = nm4 tilingFix, VAO, texturas sin tintar > 1024.

Riesgos y verificación:
- R1 color_ac: cambiar `diffuse_color` invalida 127 medidas a la vez; comprobar con `simular_vistas.py` (el
  modelo de color_ac sin AC) que el aspecto previsto no se lava; el techo de croma `CROMA_MAX` 1.08 puede desaturar
  ocres/terracotas (petición: revisar techos por familia).
- R2 `familia()` por nombre: `MAT_matorral` caería en 'pintado'; nombrar `MAT_terreno_matorral`.
- Máscara 2048 RGBA (4-8 MB PNG) + 4 tiles + normal: 20-60 MB más de KN5 y 7 samplers por píxel de terreno: sin
  FPS medibles, (A) es el plan por defecto y (B) solo con foto del amigo.
- El shader multicapa es solo opaco: el fundido terreno/asfalto sigue siendo por malla (arcén), no por alfa.
- Nombres de samplers/props de `_fresnel_nm` verificados en foros, no en SDK: por eso el ensayo 1.5.
- `aplicar_texturas` marca `TEXTURIZADO` y `mejorar_materiales` `MEJORADO` (idempotentes): el `mat_terreno()` nuevo
  debe llevar el marcador o el pase lo pisa.
- Verificación: hoja A/B set `paleta` (01, 07, 09, 13, 21, 51 + piloto), `kn5_prueba` + `kn5_check` + presupuesto de
  texturas, grep de RGB fuera de `paleta.json`, histograma de la máscara (suma = 1 ± 0.02 en el 99 % de texeles).

Horas / agentes: 3a 8, 3b 6 (+4 CC0), 3c 16, 3d (A) 6 de especificación (la ejecución es de 04_export), 3e 6 (+2 VAO
instrucciones), 3f 4, 3g 2 = **50 h-agente; 2 agentes (paleta/tiles/kits, máscara/terreno); 2 huecos de cola**.

### Bloque 4: VEGETACIÓN (riesgo ALTO de presupuesto; TreeFX es extra puro)

Objetivo medible:
- Triángulos de vegetación en el KN5: 1.74 M -> <= 0.6 M con densidad x2-3 (6 000-8 000 árboles) y masas reales
  (>= 70 % de los árboles con otro a < 6 m; hoy una pieza por 340-680 m2).
- Cobertura por hábitat (del plan JSON): pinar en crestas/collados 60-180 m, encinar en umbrías > 25°, olivar
  20-90 m junto al pueblo, cipreses en caminos/ermita, palmeras < 20 m junto al mar/paseo/casino, matorral > 30°,
  nada donde `mascara_roca > 0.6`; 0 árboles por encima de 80 m hoy -> >= 30 % del total.
- Árboles quitados por `despeje_final` + asentar: 139+3 por pasada -> < 20 (el plan ya respeta exclusiones).
- Silueta: en 51/52/10 no se reconoce la misma copa cada pocos metros (>= 12 siluetas por especie); desde 1.4 m
  los árboles de los primeros 30 m no son tarjetas.
- Determinismo: dos regeneraciones con el mismo JSON dan los mismos árboles (hoy el bosque cambia con el `rnd` global).

Cambios concretos:
- 4a. `03_blender/vegetacion.py` (nuevo, python del sistema, como `urbanismo.py`): lee `geometria_3d.json` +
  `urbanismo.json` (+ `terreno_mask.png` de 3c cuando exista) y escribe `vegetacion_plan.json`
  (`[{especie, variante, x, y, z, rot, escala, ancho, tono}]`, agrupado por zona) y `renders/qa/vegetacion_mapa.png`.
  Máscaras: pendiente, cota, distancia al mar (`mar` dilatada), al pueblo (solares + 40 m), a pista (>= 12 m,
  `_sitio_lejos_pista`), calles/caminos/plazas/bancales/rocas; masas por semillas + disco de Poisson (3-5 m pinar,
  7-9 m olivar) con claros explícitos; tamaño/ángulo/tono por árbol; semilla fija.
- 4b. `assets/vegetacion_kit_v3.py` + `test_vegetacion_kit_v3.py` (misma API `build_pino(parent, alto, seed, variante)`
  -> `VEG_pino` con `ob["VEG_variante"]`, pivote en la base): copas de 2-3 casquetes aplastados de borde ondulado
  (estilo Cars), ramas que asoman, tronco x2, huecos; modo `sin_alfa=True` (60-120 tris por árbol, 30-50 arbusto)
  que es el ESENCIAL mientras no exista P4; modo con 4-8 planos de hojas con alfa (150-250 tris, UV + material
  `MAT_VEGC_<especie>` con Image RGBA) preparado pero apagado. Presupuesto en el test: <= 250 tris/árbol, <= 80/arbusto.
  `assets/render_impostores_veg.py` (bpy.ops.render permitido): atlas `assets/texturas/veg_<especie>.png` 2048 RGBA
  renderizado de las propias piezas (coherente con el look; no hace falta descargar).
- 4c. Coordinador: `integrar_escena.build_library` (l.255-311) carga v3 vía `assets/v2_aprobados.txt`/`load_mod`;
  `zona_montana` (l.2223-2318), `zona_tierra` l.1711-1724 y jardines de `zona_casino` l.2097-2119 pasan a ejecutar
  `vegetacion_plan.json` (clones); `enriquecer_vegetacion` deja de aleatorizar (el tono viene del plan).
  `asentar_objetos.copa_calzada` mide la anchura real de la copa (sigue válido con casquetes).
- 4d. Sotobosque y suelo: arbustos/matorral del plan (ya en 4a) y oscurecimiento bajo masas = canal R de la máscara
  (3c), no objetos.
- 4e. TreeFX (extra CSP): `03_blender/exportar_trees_txt.py` (python del sistema) desde `vegetacion_plan.json` ->
  `04_export/extension/trees/trees.txt` (conversión `(x, y, z)_b -> (x, z, -y)_AC`, `configure:` por zona, prueba
  de 3 árboles meta/casino/cima primero); FBX por especie con 2-3 LOD (v3 detallado / v3 / v2) con
  `bpy.ops.export_scene.fbx` (excepción a "sin bpy.ops": pedir permiso) o `PORTO_FBX=1` de `exportar_ac.py`;
  `.bin` solo en el PC del amigo (Content Manager, developer mode); `[TREES] LIST_0` + `SURFACE_MATERIALS` y
  `[SHADER_REPLACEMENT] MATERIALS = MAT_VEG_?, IS_VISIBLE = 0` con ACTIVE = 0 hasta verificar (P8).

Dependencias y orden: 4a y 4b en paralelo YA (no dependen del relieve: el plan se regenera con cada pipeline) ->
4c (coordinador) -> v1.2 -> 4e cuando el amigo confirme CSP >= 0.1.79. Si 3c existe, 4a lee la máscara; si no,
calcula las suyas.

Esencial / extra: esencial = plan + v3 sin alfa (menos tris, más densidad, mejor silueta; sin sombra en AC,
`castShadows=0` sigue). Extra = planos con alfa (P4), `castShadows=1` por especie (P4), TreeFX (CSP), viento.

Riesgos y verificación:
- Densificar x3 con mallas v2 (400-900 tris) reventaría el presupuesto: PROHIBIDO sin v3 (ver "no hacer").
- Sin P4 las "hojas" con alfa salen como cuadrados verdes opacos en AC: por eso el modo `sin_alfa` es el que se
  promueve.
- Tarjetas a 1.4 m de altura cantan: primeros 20-30 m de pista siempre con copas opacas (v3 sin alfa), tarjetas
  solo en masas lejanas si P4 llega.
- Inspectores miran el pivote; copas sobre la calzada las mide `nada_en_pista` (hoy 0 de vegetación): mantener.
- Verificación: `vegetacion_mapa.png`, `asentar.json['por_familia']` y `arboles_quitados`, `tris_veg` (stub del
  informe) en el test del kit, `kn5_presupuesto` (DECO_MAT_VEG_* <= 0.6 M), A/B set `vegetacion` (01, 07, 10, 21,
  51 + piloto), coordenadas de los 3 árboles de prueba contra `pos_kn5` de `resumen_writer_opt.json`.

Horas / agentes: 4a 14, 4b 16, impostores 6, 4c 6 (coordinador), 4e 10 (exportador 4 + FBX 4 + ensayo 2) =
**52 h-agente; 2 agentes (plan, kit) + coordinador; 2 huecos de cola**.

### Bloque 5: PUEBLO (riesgo MEDIO; la QA 0 fallos es BLOQUEANTE para todo el pipeline)

Objetivo medible:
- Huecos > 12 m entre solares de una fila: 515 m -> < 200 m; casas >= 200; terrazas 1-2 de `pueblo_subida_ladera`
  con >= 60 % de frente edificado (hoy ~30 %).
- 0 "muros aleta": coronación de cada `CAMINO_muro` sigue `z_top` del JSON y el terreno a < 2.5 m del muro queda a
  z_top-0.1 (lado alto) / z_base+0.1 (lado bajo) -> medible con rayos (script `_rev/medir_muros.py`).
- 0 césped entre casas de una manzana; franja acera-fachada pavimentada (`CALLE_acera`) en el 100 % de las manzanas.
- `urbanismo.py` 0 fallos; `revisar_urbanismo` casa_casa/casa_muro/casa_calle 0; los 4 fallos actuales del pueblo
  (CASAS_casa.066 + CAMINO_muro.132, .146 flotante, 2 losa_hierba) resueltos.
- Capturas 05/06/39/40/50 A/B y la 50 (piloto s800) como juez.

Cambios concretos:
- 5a. Muros y escarpa: `urbanismo_escena.muro3d` (l.171-191) pasa a `muro_rampa_sillares` (l.215-281) con coronación
  = `z_top` por vértice; "escarpa" de nodos del TERRENO a < 2.5 m del muro (lado alto z_top-0.1, lado bajo
  z_base+0.1), implementada como pasada en `asentar_objetos` tipo `garantia_losas_terreno` (respeta
  `_proteger_pista`, tope ±2.5 m, nunca a < 6 m del asfalto); sube el atributo `roca` solo si corta > 2 m. Es el
  N2/F-06 pendiente.
- 5b. Manzanas: `urbanismo.py construir_solares` (l.1875-1998) por manzanas de 3-7 casas (`t += a`, sin buffer
  1.02 dentro de la manzana, hueco 1.5-2.5 m entre manzanas), anchos `[4.5..9]`, plantas "no dos vecinas iguales",
  campos nuevos por solar `manzana`, `medianera_izq/der`; polígonos nuevos `aceras` y `patios` (losas con canto);
  QA: `solar_solar` -> intersección de interiores > 0.05 m2 salvo misma manzana; `huecos` entre manzanas. Solares
  trapezoidales en curva (opción A del informe) o solape trasero <= 0.6 m con medianera ciega (opción B, más
  barata). `urbanismo_escena.casa_var` con `laterales=(not med_izq, not med_der)` y retranqueo 1-2 cm de la casa
  más baja (z-fighting). Prefijos `CALLE_acera`/`CALLE_patio` dados de alta en `asentar_objetos.SOPORTE_PREF`/
  `LOSA_PLAN` y `revisar_urbanismo.LOSA_PREF_QA`/`PROP_NO` (o reutilizar `CALLE_plazoleta`).
- 5c. Suelo urbano: farolas cada ~18 m en calles de terraza (`calle_kit.build_farola`, ya 1WALL), tramos de adoquín en
  la calle de servicio (`tipo='servicio_adoquin'`, asfalto en los 30 m de cada boca), alcantarillas como geometría
  dentro de la malla de la calle; bolardos (`calle_kit.build_bolardo`) SOLO cuando P6 los haga 1WALL (si no, un
  bolardo entre borde y cierre es "visible no físico": el coche lo atraviesa).
- 5d. Atlas: `casas_kit_v2._MB` escribe UV (pared u=a/esc, v=z/esc); material `MAT_CASAS_atlas_<tono>` excluido de
  `aplicar_texturas.familia_de` (l.98-99) y de `mejorar_materiales.PREFIJOS`; atlas 2048 generado en Blender
  (estuco procedural + desconchones + zócalo + cornisa; `assets/render_atlas_fachadas.py`) o CC0 recoloreado si
  hay permiso. Llega a AC hoy tintado a 512 (P2 para 1024). Decals con alfa (ropa, macetas) esperan a P4; mientras,
  macetas como geometría dentro de la casa (`macetas=0.3`) y tendedero como `DECO_tendedero` (no `CALLE_`: evita
  `prop_casa`).
- 5e. Soportales (`params['soportal']`: planta baja retranqueada 2.5 m, pilares en y=0; la caja de colisión de
  `exportar_ac` llega a y=-0.45: el coche no entra), torreones de esquina, plantas 2-7, `build_iglesia` en
  `edificios_civicos_v2` (cúpula + campanile) sobre un solar de 2 anchos reservado por `construir_plaza`.
  Convenciones intocables: `CASAS_casa`, fachada +Y en y=0 (`max(ys) <= 2`, `min(ys) <= -3`), hijo `CASAS_zocalo`,
  huella por vértices z < 0.6, pivote en el centro de la fachada.
- 5f. Plaza del ayuntamiento (fuera del plan, causa de casa_muro .066): exportar su huella a `urbanismo_spec.json`
  como `zonas_reservadas` (como `zonas_excluidas`) para que el plan la respete.

Dependencias y orden: 5a (solo escena + asentar; quita las aletas: 05/06/39/40/50) -> 5b (plan + escena + QA el
mismo día: el `assert` aborta el pipeline) -> 5c -> 5d -> 5e. Si el bloque 1 cambia el relieve, el plan se regenera
solo; el spec (21/6/0.5) no cambia. 5a toca nodos del TERRENO: coordinar con 2b/3c (atributo `roca`, máscara).

Esencial / extra: todo esencial (geometría + difuso); nada necesita CSP. Luces de farolas de noche = bloque 9.

Riesgos y verificación:
- Presupuesto: <= 5000 tris x ~200 casas <= 1 M; medianeras ahorran 400-800 por casa; soportales/macetas gastan;
  `assert` del test del kit + presupuesto del KN5.
- `urbanismo.py` aborta con 1 fallo: cualquier cambio en solares va con su `verificar()` el mismo commit; probar con
  `--salida <scratchpad> --sin-qa` primero.
- `revisar_urbanismo.casa_casa` tolera 0.3 m: dos medianeras con zócalo+pilastra suman 0.24 (pasa); con
  `laterales=False` 0.
- Escarpa (5a): nodos del TERRENO cerca de la pista -> hoyos visibles de `revisar_fisica_ac`; nunca a < 6 m.
- Verificación: `urbanismo.log` (QA, casas, huecos), `urbanismo_informe.json`, `_rev/medir_muros.py`, A/B set `pueblo`
  (05, 06, 39, 40, 10 + piloto 50).

Horas / agentes: 5a 10, 5b 18, 5c 6, 5d 12, 5e 14, 5f 2 = **62 h-agente; 2 agentes (plan/QA, kit/escena); 2 huecos de cola**.

### Bloque 6: AGUA Y COSTA (riesgo BAJO-MEDIO; una parte depende del relieve final)

Objetivo medible:
- Agua: color por profundidad/distancia (turquesa 0-8 m, azul > 25 m) con 0 parches de 250 m; visible desde 01, 14,
  54 y la nueva `61_orilla_piloto_s150`.
- Orilla: franja continua `COSTA_orilla` en el 100 % de la isolínea `coastF=0.5` con pendiente < 35 %; 0 "almenas"
  hierba/mar en 14/22 (el borde de 4 m queda tapado).
- Escolleras de bloques en dique (600-900 piezas), espigón del puerto y cala; puerto con buje + 5 radios; marina con
  >= 7 esloras distintas y >= 55 barcos colocados (hoy 41 + 10 VIP); 10-14 veleros con velas izadas.
- Presupuesto: +<= 300 k tris en todo el bloque; 3 draw calls por material nuevo.

Cambios concretos:
- 6a. `03_blender/generar_mar.py` (nuevo, python del sistema, tras `preparar_geometria`): `texturas/mar_color.png`
  (1024-2048, batimetría desde `terreno.z`/`mar` + `distance_transform_edt`, ruido de 60 m, franja de espuma
  `d_costa < 8`). `construir_pista.py` l.1476-1513: `AGUA` = rejilla de 32 m sobre la caja del terreno + 60 m con
  UV (x-x0)/ancho; `AGUA_lejos` = anillo a 9 km de color profundo; `MAT_agua` con Image `mar_color.png` por
  `TEX_ganancia/TEX_multiplicar` (contrato del writer) y base blanco; roughness 0.04 -> 0.08; `AGUA_fondo` con
  `MAT_fondo_marino` (arena). `aplicar_texturas` familia `agua` (bump) no debe pisar la cadena (marcador).
- 6b. Orilla: `construir_pista.py` tras el TERRENO: malla `COSTA_orilla` (marching squares sobre `mar` suavizado,
  franja ±6 m, 3 materiales: arena mojada, arena clara, espuma) solo donde pendiente < 35 %; coordinador:
  `zona_costa()` con rocas de orilla (`vegetacion_kit.build_roca` 2-5 m, 40 % hundidas, unidas por tono en
  `COSTA_rocas`). Alta: `revisar_flotantes.EXENTOS` (referencia marina), `eliminar_sumergidos` (no es `VEG_`),
  `nada_en_pista` no (lejos), P6 para `NO_OBSTACULO` (lungomare s 4930-5200 está cerca de la orilla).
- 6c. Escolleras: `assets/escollera_kit.py` (nuevo) `build_bloques_a_lo_largo(parent, puntos, ancho, z_agua, seed)`
  (superelipsoides 1.2-3 m, 48 tris, 3 tonos, 30 % bajo el agua), usado por `puerto_kit.build_dique(bloques=True)`
  (hija `PUERTO_dique_bloques`), `caminos_kit.build_camino(tipo='muelle', bloques=True)`, y ofrecido a `roca_lazo`/
  `roca_casino` (sus dueños, bloque 2). Decorado: el loft `1ROAD_puerto_dique_malla` sigue siendo la física.
- 6d. Puerto llanta: `puerto_kit.build_buje` (isla r 16-18 m, club náutico, 4 palmeras), 5 pantalanes radiales desde
  el buje, arco 200° -> 230°, bocana de 50 m con balizas, 18 farolas; `zona_puerto` (coordinador). Dragado: disco de
  mar forzado a z -6 de radio R_DQ+12 en `terreno_montana` (bloque 1, 1 línea, fuera de toda protección).
- 6e. Flota: `puerto_kit.build_yate(eslora 14-30)`, `build_velero(velas='izadas'|'recogidas')`, `yates_kit.build_lancha
  (n_coches=0)`, 4-6 `yates_kit.build_yate(con_publico=False)`; `color_franja`/`color_bimini` -> `MAT_PUERTO_casco_<HEX>`
  (<= 6 tonos para no disparar materiales); veleros con rumbo coherente y escora; estelas con alfa esperan a P4.
- 6f. CSP (extra): `[Material_Water] Type = SEA` ya está; `DepthAware`/`UseAlphaFromDiffuse`/`[BOUNCED_LIGHT] CAUSTICS`
  solo como sección con `ACTIVE = 0` (P8) hasta ver FPS en el PC del amigo.

Dependencias y orden: 6a y 6c/6e YA (v1.2: no tocan terreno) -> 6b y 6d tras el bloque 1 (la costa final) -> v1.3.

Esencial / extra: esencial = textura batimétrica (llega hoy: el writer coge la primera Image sRGB, tintada a 512 =
5 m/px, suficiente; P2 para 2048), orilla, bloques, puerto, flota. Extra = cáusticas/refracción, barcos animados
(bloque 9).

Riesgos y verificación:
- `AGUA` está en `KEEP_PREFIXES` (nodo propio) y `AGUA_lejos` también empieza por AGUA: OK; `revisar_flotantes` exenta
  `AGUA*`.
- El tintado del writer puede lavar el degradado (gain = 1/media por canal): comprobar en `kn5_prueba` con
  `_color_ac_prueba/leer_kn5_color.py` y, si hace falta, pedir modo "tal cual" (P3) para `MAT_agua`.
- Bloques de escollera "vistos por detrás" en `revisar_fisica_ac`: sombreado plano con normales hacia fuera
  (`_MB.to_object` recalcula); son hijos del dique (no raíces: no se inspeccionan).
- Verificación: A/B set `agua_costa` (02, 14, 16, 22, 36_general, 46, 47, 47b, 60, 61 + piloto), log de `zona_puerto`
  (barcos colocados/posibles), presupuesto.

Horas / agentes: 6a 8, 6b 10, 6c 8, 6d 10, 6e 8 = **44 h-agente; 2 agentes (agua/orilla, puerto/flota) + coordinador;
2 huecos de cola**.

### Bloque 7: PÚBLICO Y RELLENO (riesgo MEDIO: muchos prefijos nuevos; el horizonte es lo más barato y lo más visible)

Objetivo medible:
- Horizonte: anillo de 7-9 cordilleras + 6-8 lomas de costa en 200° (abierto S/SO 160°), <= 250 k tris, visible en
  01/13/14/16/08/19 y en 49/52/54; mar abierto sigue viéndose desde 54 y 14.
- Público con cara: 70-90 -> 250-350 coches (12 tipos, escala 0.92-1.08, banderas 20 %), en 8-12 aparcamientos
  explanados, terraza del casino (10-16 de lujo), yates (n_coches 6-8), ladera (6-10 campamentos).
- Relleno: 40-80 bancales TALLADOS en el terreno (no bandejas), 4-6 viñedos, 6-10 villas, 6-8 carpas en el paddock,
  3 torres costeras + 2º faro.
- Defecto 8 del director (torres sobre losa sin camino): 0 torres sin ramal o peana integrada.
- Presupuesto: +<= 400 k tris; cada kit una malla por unidad; materiales reutilizados por nombre.

Cambios concretos:
- 7a. `zona_horizonte` (coordinador, sustituye el `return` de `zona_montanas_fondo` l.2495): `montanas_fondo_v2.build_
  cordillera(largo 1400-1800, n_picos 5-7, alto 380-520, pie=True, res 0.5)` en arco de 3.2-4.5 km, dos planos de
  profundidad, `build_loma` a 2.4-2.8 km con pueblecitos-silueta (cajas, 1 material) y 1 faro lejano; prefijo `HORIZ_`;
  `mejorar_materiales` mezcla con el color del horizonte (0.70,0.84,0.98) al 35-55 % (perspectiva atmosférica
  horneada: AC sin CSP no tiene niebla fiable). Alta: `revisar_flotantes.EXENTOS` (`MONT_` -> `HORIZ_`),
  `eliminar_sumergidos` (pie a z -6), P6 (`SIN_SOMBRA_TOKENS`, `NO_OBSTACULO`).
- 7b. Público: `coches_kit_v2.build_coche` opciones `bandera`, `mirada`; `build_fila_aparcada` escala por coche;
  `_pub_coche` (carrera_kit_v2 y pit_kit) 6 siluetas, 10 colores, bandera 20 %. Coordinador: `zona_coches` por
  APARCAMIENTOS explanados (losa de grava 30x14 con `explanar()` + ramal de tierra con valla como `_ramal_camara`,
  muro de piedra seca en el borde bajo) en exteriores de curva a 16-30 m; `asentar_coche` ya pone cada coche sobre
  4 ruedas. `casas_kit_v2` expone `info['balcones']` (coches en balcones: DESPUÉS de 5d, y solo si sobra presupuesto).
- 7c. Relleno: `03_blender/bancales_spec.py` (nuevo, python del sistema, ANTES de `preparar_geometria`): polilíneas por
  curva de nivel en 6-10 laderas de pradera (pendiente 10-35 %, sin pista a < 40 m, sin solares, sin senderos) ->
  `terreno_montana.construir` las talla (escalón real, como las terrazas) -> `zona_bancales` clona
  `italiano_kit.build_bancal` por tramos (`olivos=False` si el bloque 4 pone los olivos). Kits nuevos con test y
  previews: `italiano_kit.build_vinedo`, `build_torre_costera(alto=11)`; `assets/villa_kit.py build_villa(seed)`
  (<= 6 k tris, piscina `agua_piscina` de yates_kit, explanada + acceso); `carrera_kit_v2.build_carpa`;
  `assets/camping_kit.py` (`build_autocaravana`, `build_tienda`, `build_campamento`). Prefijos `VILLA_`, `CARPA_`,
  `CAMPING_`, `ITAL_vinedo`, `ITAL_torre`: alta en `revisar_flotantes.EXENTOS`/`SOPORTE_PREF`, `asentar_objetos`,
  `despeje_final.EDIF_PREF`, y P6 (1WALL para carpas del paddock y muros de villa alcanzables).
- 7d. Torres de cámara (defecto 8): `zona_camaras` (coordinador): torre fija SIEMPRE con ramal de tierra o peana
  fundida en el terreno (`explanar` r 6 + talud 1:2) y nunca sobre losa-caja; peana `CAMARA_peana` en
  `SOPORTE_PREF` (pendiente del registro v2 integrador).

Dependencias y orden: 7a YA (independiente, v1.2); 7b/7c/7d tras el bloque 1 (explanadas y bancales sobre el relieve
final) y 7b-balcones tras 5d -> v1.3/v1.4.

Esencial / extra: todo esencial salvo animación de dirigible/barcos/rotor (bloque 9).

Riesgos y verificación:
- Cada familia nueva que no esté en las listas de los inspectores acaba borrada, hundida o contada como barrera
  falsa (`revisar_flotantes`, `eliminar_sumergidos`, `asentar PROT_NO`, `despeje_final`, `nada_en_pista.PERMITIDOS`,
  `revisar_fisica_ac.NO_OBSTACULO`): checklist por prefijo en el test de cada kit.
- Explanadas de aparcamiento = nodos del TERRENO -> hoyos y `copa_calzada`; mantener >= 16 m del borde.
- Draw calls: 200 coches x <= 10 slots: P9 (unión por material) o limitar slots a 6 por coche.
- Horizonte tapa la línea mar/cielo en 01: es lo pedido; abertura S/SO obligatoria (54/14).
- Verificación: A/B sets `publico`, `relleno`, `horizonte`; logs de `zona_puerto`/`zona_coches` (colocados vs
  posibles); `asentar.json['por_familia']`; presupuesto.

Horas / agentes: 7a 8, 7b 14, 7c 28 (bancales 10 + kits 18), 7d 4 = **54 h-agente; 2 agentes (kits, bancales/público) +
coordinador; 2 huecos de cola**.

### Bloque 8: CARIFICACIÓN (riesgo BAJO en kits; MEDIO en el peñón del casino)

Objetivo medible:
- Chimeneas-escape en >= 80 % de las casas (ya existe la pieza en `casas_kit_v2` l.709: subir probabilidad y tamaño
  x1.5); 4 estatuas de coche en las esquinas del casino; rejilla + faros en ayuntamiento, hotel y casino; monumentos
  (casino, campanile, hotel, pórtico, faro) +30 % (no +50 %: ver riesgos); peñón con silueta Topolino reconocible
  desde 36_general y 01 (contorno del peñón: `R_top`/`R_bot` por columna).
- 0 logotipos de marcas reales (grep de nombres/texturas; ya es regla).

Cambios concretos: `casas_kit_v2` (chimeneas), `casino_v2` (`build_estatua_coche` desde `coches_kit_v2` en pedestal,
rejilla/faros en la fachada), `edificios_civicos_v2` (ídem en ayuntamiento/hotel), `integrar` escala de monumentos
(`explanar_edificios` recalcula la explanada; la caja 1WALL de `exportar_ac` sale del `bound_box`: se adapta sola);
`roca_casino._meseta/_forma` (l.454-521): perfil de `R_top`/`R_bot` por columna con la silueta Topolino (morro al mar)
y `trazar()` vuelve a resolver la bajada (red de seguridad "modo roca" ya existe).

Dependencias: tras 2f (perfil del peñón) y 5e (kits cívicos). Esencial todo.

Riesgos: +50 % en el casino cambia `casino_contorno`, la distancia a la Loews (8-14 m, intocable), las farolas a
>= 2.76 m del eje y la QA `casa_pista`: por eso +30 % y nunca la Loews ni la rotonda; silueta Topolino: si `trazar()`
no encuentra bajada limpia se queda la actual (`_calidad`). Verificación: `test_roca_casino`, `test_casino_v2`,
A/B 19/20/36 + 10 + 02.

Horas / agentes: **18 h-agente; 1 agente; 1 hueco de cola**.

### Bloque 9: CSP Y AMBIENTE (riesgo BAJO en el KN5 si se hace bien, ALTO si se "hornea" algo de CSP en el KN5)

Objetivo medible: `ext_config.ini` v1.5 con secciones `[Material_Water]` (+DepthAware/cáusticas), `[GRASS_FX]`,
`[LIGHT_SERIES_*]` + `[MATERIAL_ADJUSTMENT_*]` (farolas paseo/puerto/peñón/casino/guirnaldas/boxes/ventanas),
`[LIGHT_POLLUTION]`, `[WRAP_MESHES_*]` + `[ANIMATED_*]` (rotor .ksanim, dirigible y barcos tipo train),
`[DISPLAY_*]` (2 pantallas), `[TREES]`, `[SHADER_REPLACEMENT]` nm4 tilingFix y ocultación de árboles KN5; cada
sección con `ACTIVE = 0/1` independiente; AC a pelo idéntico con o sin la carpeta `extension/`.

Cambios concretos (lo que SÍ es de la fase visual, en Blender, inocuo sin CSP):
- Materiales exclusivos por función: `MAT_cesped` (jardines, rotondas, meseta), `MAT_farola_luz`, `MAT_casino_luz`,
  `MAT_guirnalda_luz`, `MAT_pit_luminaria`, `MAT_ventana_luz` (bombillas apagadas = gris cálido; `ksEmissive` 0 en el
  KN5 SIEMPRE), `MAT_heli_rotor` (un solo objeto por material: un rotor por helicóptero -> `MAT_heli_rotor_1..4`),
  `MAT_pantalla_1/2` con textura REAL 1024x576 (imagen estática "WGP LIVE"/bahía; UV 0..1 en la cara frontal, marco
  con otro material). Objetos móviles con nombre `ANIM_<cosa>` y pivote donde deben girar (P7) y pose creíble si no
  se mueven (palas en cruz, barcos amarrados).
- `_rev/fase_visual/ext_config_v1_5.ini` (borrador, NO en 04_export) con todos los bloques de `web_csp_agua_luces.md`
  §2-§7 y `web_treefx.md` §8, coordenadas KN5 (x, z, -y) calculadas por un script `_rev/coords_csp.py` desde el
  `.blend` (farolas, cámaras de pantalla, rutas de barcos como mallas `ANIM_ruta_*` ocultas).
- VAO (3e) y TreeFX (4e) ya descritos.

Dependencias: materiales en cada kit durante los bloques 5/6/7 (coste marginal); `ext_config` al final; prueba solo en
el PC del amigo con Pure y con Sol (visual).

Esencial / extra: NADA de este bloque es esencial; su único efecto en AC a pelo debe ser nulo. Condición para no
romper: ni emisivos > 0, ni alpha blend, ni `ksGrass`, ni nodos que dependan de CSP para verse (opción C de los
animados = KN5 aparte: descartada porque sin CSP desaparecerían).

Riesgos y verificación: una clave mal escrita no rompe AC pero puede dejar una sección muerta; `ACTIVE = 0` por
defecto y activación una a una en el PC del amigo; `HIDE`/`IS_VISIBLE = 0` de los árboles solo tras confirmar que
TreeFX se ve (si no, pista sin árboles). FPS: `DepthAware`, luces con sombras y GrassFX son lo que más cuesta: apagados
por defecto. Verificación local: `kn5_check` de materiales exclusivos (nombres presentes), `coords_csp.py` contra
`pos_kn5` del resumen del writer, la textura de pantalla visible en 02/29.

Horas / agentes: materiales/nombres en kits 10, pantallas 4, ANIM_ y rutas 6, borrador ext_config + coords 8 =
**28 h-agente; 1 agente (+ marginal en los dueños de los kits); 1 hueco de cola**.

---

## 4. Orden recomendado, paralelismo y duración

Orden (cada flecha = puerta de calidad + hoja A/B; "YA" = no toca terreno ni writer):
1. Bloque 0 (infra) y 1a (tierra) en paralelo con 3a/3b (paleta, tiles), 2a (material de roca), 7a (horizonte),
   6a/6c/6e (agua, escollera, flota), 4a/4b (plan + kit v3). Promoción -> **zip v1.2** (1-2 días de calendario).
2. 1b -> 1c -> 2b/2c -> 5a -> 5b -> 6b/6d -> 2d/2e/2f -> 7b/7c/7d -> 8. Promoción -> **zip v1.3**. 1d (erosión) solo
   si tras 1c sobra tiempo y todo está estable.
3. Con las 5 fotos de ensayo del amigo: 3c/3d, 5d, 4b-alfa, 2g, CC0 -> **zip v1.4** (depende de que 04_export abra
   P1-P5).
4. Bloque 9 + 4e + VAO -> **zip v1.5**.

Paralelismo razonable: 5 agentes + coordinador. Reparto estable (evita que dos agentes editen el mismo fichero):
A) terreno (`terreno_montana`, `erosion.py`, `mascara_terreno.py`, `bancales_spec.py`); B) materiales/paleta/tiles
(`paleta.json`, `generar_texturas`, `aplicar_texturas`, `materiales_roca`, `hornear_rocas`); C) rocas (`roca_lazo`,
`roca_casino`, `montana_mclaren`, `afloramiento_kit`); D) pueblo (`urbanismo.py`, `urbanismo_escena`, `casas_kit_v2`,
`edificios_civicos_v2`, `calle_kit`); E) vegetación + agua/público/relleno/CSP (`vegetacion.py`, kit v3, `puerto_kit`,
`yates_kit`, `escollera_kit`, `villa/camping/carrera kits`, `coches_kit_v2`, `ext_config` borrador); coordinador:
`integrar_escena`, `preparar_geometria`, `construir_pista` (zonas nuevas, UV, AGUA, COSTA), `asentar_objetos` (listas),
pipeline, puerta, promociones. Cola de Blender: <= 4 huecos para la fase visual (1 por agente A-E solo cuando lanzan
test/pipeline; el pipeline completo y las capturas A/B los lanza el coordinador en serie), 2 huecos para el zip.

Duración: suma 20+54+80+50+52+62+44+54+18+28 = **~460 h-agente** (±30 %). Con 5 agentes activos y las serializaciones
(terreno -> pueblo -> rocas sobre el relieve final; coordinador como cuello de botella en `integrar_escena`),
**~110-130 h de reloj**; v1.2 a las ~25 h, v1.3 a las ~80 h, v1.4/v1.5 condicionadas al amigo y a 04_export.

---

## 5. Preguntas que SOLO el usuario puede responder (bloquean decisiones)

1. ¿El amigo usa CSP? ¿Qué versión (TreeFX exige >= 0.1.79)? ¿Tiene Content Manager con developer mode (conversor
   de árboles)? ¿GPU (para FPS y para VAO en su PC)? Si "no sé": el plan asume NO (v1.2-v1.4 sin CSP; v1.5 opcional).
2. ¿Puede el amigo cargar 5 KN5 de ensayo (plano + material) y mandar fotos antes de v1.4? Sin eso, el terreno
   multicapa, los árboles con alfa y los atlas se quedan en la alternativa A (materiales por cara) y geometría opaca.
3. Permiso para descargar texturas CC0 (Poly Haven + ambientCG, licencia CC0, sin atribución obligatoria):
   13 texturas, **~49 MB en 1K-JPG** (mínimo útil ~40 MB; 2K serían 186 MB y no aportan: el writer recorta a 1024).
   Lista exacta en `web_texturas_cc0.md` §5. Y permiso para `CREDITS.txt` en el repo público.
4. Permiso para descargar `acc-bakeryoptix` build-v22.zip (1.8 MB, binario de Releases; sin fichero LICENSE en el
   repo) para generar `porto_corsa.vao-patch` (solo CSP).
5. Permiso para la excepción `bpy.ops.export_scene.fbx` (FBX de árboles para TreeFX) o usar `PORTO_FBX=1`.
6. Tope de tamaño del zip/KN5 aceptable para la Release y para el amigo (propuesto 250 MB / 450 MB; hoy 172 / 355).
7. "Bajada a la horquilla de la fuente": ¿rotonda Loews (s 3564) o la horquilla C26 de tierra (s 2364)?
8. Tramo de tierra: ¿se acepta que la RASANTE no cambie (ya va al 13-16.5 %, por encima del 12-15 % pedido; bajar
   `MAXG` a 12 % rebaja la cima a ~105 m y obliga a revalidar la física de las horquillas)? Propuesta: solo el relieve
   lateral (1a), rasante intacta salvo tope 10 % a ±40 m de los dos apex (física: 1 cambio de pendiente en s 2365).
9. McLaren "túnel por la rueda": hundir la rueda ~8 m (`alto_base` 12 -> 20) cambia el túnel físico (TUNEL_suelo,
   galerías, cierre): ¿sí (v1.3, +12 h y revalidación de física) o se mantiene el portal actual y se agranda la
   sillería hasta los radios (sin física)?
10. Monumentos: ¿+30 % vale (recomendado) o se exige +50 % (afecta a `casino_contorno` y a la Loews, que debe seguir
    intacta)? ¿La Loews/rotonda quedan fuera de cualquier escalado?
11. Prioridad: ¿zips frecuentes (v1.2 en 1-2 días con paleta/horizonte/agua/vegetación) o esperar a v1.3 con relieve?
12. ¿Capturas de Blender con o sin sombras de terreno/vegetación como criterio de aceptación? (en AC no las hay).

---

## 6. Lista de "NO HACER" (desaconsejado, con motivo)

1. **Hydra (addon)**: se engancha al contexto OpenGL de la ventana (`moderngl.get_context()`), no funciona en
   `--background`, es de la era Blender 4.0 y no reproducible en el pipeline. Erosión = `erosion.py` NumPy.
2. **Escribir `ksMultilayer_fresnel_nm4` en el KN5**: es shader de CSP (sdk-shaders), no de Kunos, y los nombres de
   sus 4 samplers de normal no están documentados; en vanilla puede dejar el terreno sin material. Vanilla =
   `ksMultilayer_fresnel_nm` (y solo tras ensayo del amigo); nm4 solo por `ext_config`.
3. **Empezar por el multicapa**: 7 samplers por píxel de terreno + 20-60 MB de texturas sin poder medir FPS. Primero
   paleta + alternativa A (materiales por cara), multicapa como v1.4.
4. **AO por vertex color**: el vértice KN5 es pos+nrm+uv+tan; no existe. AO solo en textura (terreno, 3 rocas) o VAO.
5. **Hornear AO por objeto en 200 casas**: rompe "1 material = 1 textura" del writer y multiplica texturas; el
   "bisel" es `shade_smooth`/Auto Smooth, no el modificador Bevel (vértices x2) y nunca en el TERRENO.
6. **Densificar la vegetación con las mallas v2** (400-900 tris): 1.74 M -> 5 M tris. Solo con v3 (<= 250 tris).
7. **Bajar `MAXG` de la rasante de tierra a 12 %**: no da "más desnivel" (la cima baja) y toca física validada.
8. **Tocar `04_export` desde la fase visual** mientras se cierra v1.1; todo va a `PETICIONES_04_EXPORT.md`.
9. **`ksEmissive > 0` en el KN5** (brilla de día en vanilla), **alpha blend** en árboles/decals (orden de dibujado),
   **`ksGrass`** (CSP lo oculta con GrassFX): solo alfa test y luces por `ext_config` condicionadas.
10. **Animados como KN5 aparte (`MODEL_REPLACEMENT`)**: sin CSP desaparecen helicóptero y dirigible. Nodo propio
    (`ANIM_`, P7) o `WRAP_MESHES`.
11. **Ocultar los árboles del KN5 (`HIDE`/`IS_VISIBLE = 0`) antes de ver TreeFX funcionando** en el PC del amigo:
    riesgo de pista sin árboles con un CSP antiguo.
12. **`DepthAware`/cáusticas/luces con sombras/GrassFX activos por defecto**: FPS desconocidos; `ACTIVE = 0`.
13. **Mover cámaras entre el antes y el después** (`camara_segura` en el "después"): invalida el juicio A/B.
14. **Escalar la Loews/rotonda o tocar el peñón a r < 1.9, el viaducto o el corredor de la pista**: están congelados
    por petición del usuario y por la física.
15. **Props nuevos a < w/2+6.75 m del borde sin prefijo 1WALL** (bolardos, estatuas, rocas de orilla, bloques):
    `revisar_fisica_ac` los marca como "visibles no físicos" y el coche los atraviesa; o 1WALL (P6) o fuera.
16. **Objetos nuevos sin dar de alta su prefijo** en `revisar_flotantes.EXENTOS`, `eliminar_sumergidos`,
    `asentar_objetos`, `despeje_final`, `nada_en_pista.PERMITIDOS`, `revisar_fisica_ac.NO_OBSTACULO`: acaban
    borrados, hundidos o contados como barrera falsa.
17. **Texturas 2K** (el writer recorta a 1024; cuadruplican la descarga) y **PNG de 16 bits** de Poly Haven.
18. **Coches en balcones y campamentos en la ladera antes de 5d y del relieve final**: poco valor por triángulo y
    dependen de geometría que va a cambiar.
19. **Regenerar `escena_rev.blend` sin puerta de calidad**: es la escena que exporta `hacer_zip.sh`.
20. **Erosión por gotas a 1 m o GAN**: minutos por pasada y sin control; el método de rejilla a 2 m basta para
    "crestas y barrancos" a celda de 4 m.
