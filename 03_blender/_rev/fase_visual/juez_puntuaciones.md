# Juez de la fase visual — puntuaciones de los planes A / B / C (04/10/2026)

Juez y sintetizador. Leídos: `PLAN_USUARIO.md`, `director_final.md`, `RONDA15_PLAN.md` (principios, convenciones y
registro de arreglos), los tres planes completos y, para comprobar afirmaciones, `web_multilayer_vao_erosion.md`
(samplers del multicapa, Hydra), `entender_materiales.md` (writer: tintado a 512, `TEX_MAX`, UV), `entender_terreno.md`
(rasante 16.5 %, KPI pared/caída 5 %, orilla 7.5 %), `entender_agua_publico_capturas.md` §9 (esbozo de capturas
A/B), `_rev/pipeline_escena.sh` l.35 (copia a `escena_rev.blend` en cada ejecución) y las capturas 01, 49, 50, 51,
54. No se ha modificado ningún fichero del proyecto ni se ha lanzado Blender. Escala 1-10.

## Tabla

| Criterio | Plan A (ambición) | Plan B (riesgo primero) | Plan C (jugador primero) |
|---|---|---|---|
| **Fidelidad al encargo** | **10** — Cubre los 9 bloques del usuario al pie de la letra y los amplía (cabo del McLaren, Topolino, puerto-llanta, villas, carpas, camping, torres, faro, +30-50 % monumentos, erosión en el corredor protegido). | **7** — Cubre los 9 bloques pero rebaja varios puntos del encargo: erosión "solo si sobra tiempo", multicapa a v1.4, monumentos +30 % en vez de +30-50 %, lazo H7 tardío, Topolino condicionado. | **8** — Respeta el criterio explícito del usuario ("juzga sobre todo desde el coche"; "primero relieve, integración, paleta, densidad") y lo convierte en método; pero pospone el macizo alto/erosión (punto 1 del usuario) y deja fuera llanta, villas y Topolino. |
| **Viabilidad técnica real** (writer KN5, inspectores, sin AC) | **5** — Muchas piezas dependen del writer v2 [W] para verse (horneado por objeto, máscara 4096, alfa, ANIM_, DDS); 770 h y 25-35 regeneraciones; bakes Cycles a 4 k sobre 7 M de vértices sin GPU confirmada; máscara 4096 RGBA = 16-30 MB PNG; no protege `escena_rev.blend`. A favor: custom props `ac_*` desde el día 1 y KN5 de ensayo. | **9** — Todo pensado con las herramientas reales: puerta de calidad sobre JSON/logs, escena candidata (evita pisar `escena_rev.blend`, que `pipeline_escena.sh` l.35 copia siempre), export de prueba en `_rev/kn5_prueba/` por variables de entorno sin tocar `04_export`, 5 KN5 de ensayo, presupuesto automático, lista P1-P10. Reconoce que el multicapa `_nm` solo tras foto del amigo. | **8** — Modo `--modo-ac` (sin sombras/GTAO, materiales como el writer) y `medir_capturas.py` son la mejor idea de los tres para juzgar sin AC; sección X cerrada; máscara 2048 (1 m/texel) razonable. Falta la protección de `escena_rev.blend` y la puerta de calidad; 36 h para máscara por texel + UV + material v2 + paleta parece corto (B pide 50 para lo mismo). |
| **Impacto visual desde el coche** | **7** — Lo que más se ve (paleta, máscara, roca del McLaren) está, pero mezclado al mismo nivel con lo aéreo (macizo 300 m, llanta, Topolino, horizonte 2 planos); el orden F1 pone el relieve completo antes que la paleta, así que las primeras hojas de piloto cambian poco. | **5** — Ordena por riesgo, no por lo que llena el cuadro: v1.2 "paleta y fondo" sí es visible, pero la máscara por texel (la que quita dientes de sierra/escalera/hierba estirada en las 6 vistas de piloto) se aplaza a v1.4 y el camino por defecto (materiales por cara) deja bordes de 4 m en AC. | **10** — Tabla de reparto del cuadro por vista (asfalto/talud/cielo), los 5 defectos más repetidos desde el coche (césped saturado 6/6, máscara por vértice, piruletas, cortes lisos, nada a 20-120 m), 5 postales con cámara concreta (s 528, 1870, 3660, 3500, 60->140), y la observación clave de que la recta del puerto (P5) castiga el "islote" del McLaren: el cabo no es solo aéreo. |
| **Riesgo controlado** | **4** — F1 lanza relieve completo + erosión + macizo 300 m + cabo + kits nuevos con 5-6 agentes a la vez; no hay zip intermedio ni retroceso; sin puerta de calidad; `GROUND_PREFIXES` y sombras de terreno como [W] sin plan B; muchas altas de prefijos nuevos simultáneas. | **10** — Es su ángulo y lo hace bien: tabla de invariantes con valor actual y regla, topes duros, zips escalonados v1.2-v1.5 con retroceso, `ACTIVE = 0` en todo lo CSP, `HIDE` nunca antes de ver TreeFX, bermas obligatorias para `cierre_ac`, orden terreno -> pueblo -> rocas, un propietario por fichero. | **7** — Bloque 3 primero = bajo riesgo (no toca geometría); fases con ficheros distintos; "fase E prescindible". Pero sin puerta ni candidata, la primera regeneración pisaría la escena del zip v1.1; no tiene presupuesto automático. |
| **Honestidad en los tiempos** | **6** — 770 h / 5 semanas es coherente con su alcance (no esconde horas), pero el calendario asume que `04_export` abre en F5, que el amigo responde 3 veces y que hay GPU para los bakes; "~1 h de cola por regeneración" y "25-35 regeneraciones" implican 30 h de cola que no están en la tabla. | **9** — 460 h ±30 %, 110-130 h de reloj, v1.2 a ~25 h; cuenta coordinador, mide el tiempo real de una regeneración (logs 12:57 -> 13:02) y admite lo desconocido (export completo 15-30 min "lo mide el zip v1.1"). | **8** — 410 h / 3-4 semanas + 1-2 de export, con lo opcional separado y el aviso "en AC a pelo hoy se ve peor que en las capturas" (la verdad incómoda). Bloque 3 (36 h) y vegetación (41-47 h) algo optimistas. |
| **Total** | **32** | **40** | **41** |

## Ganador y motivo

**Plan C por un punto sobre el B.** C acierta en LO QUE hay que hacer primero y en CÓMO juzgarlo (modo fiel a AC,
medidas automáticas, postales con cámara concreta); B acierta en CÓMO no romper nada mientras se hace (puerta,
candidata, ensayo, presupuesto, zips). Son complementarios y por eso el plan final (`03_blender/FASE_VISUAL_PLAN.md`)
es "el orden de C con la red de seguridad de B". El plan A es el más fiel al texto del usuario pero el menos
ejecutable aquí: la mitad de su valor solo existe cuando abra `04_export`, y su calendario y su riesgo no caben en
un equipo que comparte la cola con el cierre del zip v1.1.

## Lo que se toma de cada plan

- **De C**: orden (bloque 3 -> 2 -> 1 -> 5 -> 4 -> 6 -> 7 -> 8 -> 9), `--modo-ac`, `medir_capturas.py`, las 5
  postales 55-59, el inventario "qué llena el cuadro", la lista "después o fuera", la regla de prioridad
  impacto/esfuerzo, la sección X como lista cerrada, preguntas Q5-Q7-Q12-Q13.
- **De B**: tabla de invariantes y presupuestos duros, `pipeline_escena.sh` -> candidata + `puerta_calidad.py` +
  `promover.sh`, `kn5_prueba/` por variables de entorno, `kn5_ensayo.py` (5 KN5), `kn5_presupuesto.py`,
  `PETICIONES_04_EXPORT.md` (P1-P10), zips escalonados con retroceso, propietario único por fichero, la variante
  "sin sombras de terreno" en las hojas, las 20 entradas de "no hacer".
- **De A**: `paleta.json`/`paleta.py` con las 12 entradas y la carta de color, custom props `ac_*` en todo material
  nuevo desde el día 1 (para que el cambio del writer sea mecánico), el landform "Cabo del McLaren" como pregunta,
  `extras['capas']` del terreno como fuente de la máscara, horizonte el primero de los rellenos, la tabla única de KPIs,
  `hornear_rocas.py` como paso opcional de pipeline, las preguntas sobre GPU/escala/marcas.

## Afirmaciones comprobadas (y una corrección)

- `pipeline_escena.sh` l.35 copia `porto_corsa.blend` a `_rev/escena_rev.blend` en cada ejecución (verificado):
  el riesgo que B señala es real y es la primera tarea del plan final.
- `ksMultilayer_fresnel_nm` es vanilla con samplers `txDiffuse/txMask/txDetailR/G/B/A/txDetailNM` [V] y `_nm4` es de
  CSP con samplers de normal no encontrados (`web_multilayer` §6): los tres planes coinciden y el final lo adopta.
- Hydra engancha el contexto OpenGL de la interfaz y no funciona en `--background` (`web_multilayer` §3.1): "no
  hacer" en los tres.
- Rasante de tierra ya al 13-16.5 % (`entender_terreno` l.316-322) y KPI pared/caída a 25 m = 5 % (l.328): B y C
  tienen razón en no tocar `MAXG`; A lo convierte en "bajar a 15 %/9 % en apex", que es lo mismo que proponen los
  otros para los apex.
- Writer: una textura por material, tintada por `diffuse_color` y reducida a 512, `TEX_MAX` 1024, sin UVs en la
  escena salvo `uv_layers[0]` (`entender_materiales` l.126-129, 420-424): confirma la "verdad incómoda" de C y la
  necesidad de la sección X / bloque W.
- Corrección al plan C: su bloque 3 no incluye `MAT_cesped` como material separado (lo hace en el 9); el plan final
  lo mete en el bloque 3 (A/B lo hacen) porque es la condición para que GrassFX no toque el terreno y para que el
  césped saturado desaparezca de la medida `pct_cesped`.
- Corrección a los tres: ninguno fija explícitamente que la promoción a `escena_rev.blend` no puede coincidir con una
  exportación del equipo del zip; el plan final lo añade como serialización obligatoria.
