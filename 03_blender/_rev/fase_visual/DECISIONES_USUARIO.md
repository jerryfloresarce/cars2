# Decisiones del usuario para la fase visual (04/10/2026, ~15:20)

Respuestas a las preguntas de la seccion 14 de `03_blender/FASE_VISUAL_PLAN.md`. Mandan sobre el plan.

1. **CSP: SI.** El amigo juega con Custom Shaders Patch (Content Manager). Version desconocida todavia.
   -> Lo de CSP (TreeFX, agua Type=SEA + causticas, luces de noche, animados, pantallas, VAO, nm4 por
   ext_config) pasa de "extra apagado" a "extra que SI se hace y se prueba"; se sigue entregando con
   `ACTIVE` por seccion y el KN5 sigue siendo valido sin CSP (no se rompe nada si lo desactiva).
2. **5 KN5 de ensayo: SI** (confirmado ~15:30): el amigo puede instalar las 5 mini-pistas y mandar 5 fotos.
   -> Se entregan con el zip v1.1 (o justo despues) en un zip aparte `porto_corsa_ensayos.zip` con LEEME.txt;
   el camino del terreno (multicapa vs por cara) y de los arboles (alfa test) se decide con sus fotos.
3. **Descargas: SI, "lo que necesites".** Permiso para las 13 texturas CC0 de Poly Haven / ambientCG
   (lista de `web_texturas_cc0.md`, 1K, ~49 MB) y para acc-bakeryoptix (1.8 MB) cuando toque (bloque 9).
   Siempre CC0 (sin atribucion obligatoria), con CREDITS.txt + LICENSE_CC0.txt en texturas/cc0/.
4. **Cabo de tierra bajo la zaga del McLaren: SI** (landform en terreno_montana; la costa puede acercarse
   al puerto a 150-250 m). Va con el bloque 1 (agente de terreno).
5. **Tunel por la rueda:** "lo que sea mas conveniente y mejor" -> se aplica la recomendacion: PORTAL de
   silleria grande (11-12 m) hasta los radios, sin tocar la fisica. Hundir el coche solo si tras las
   capturas no convence.
6. **Monumentos:** +30 % en general. El CASINO: probar +50 % si cabe en el penon sin invadir la carretera;
   ENSENAR capturas de las DOS versiones (+30 y +50) desde la horquilla (rotonda Loews) y desde la recta
   del puerto. SOLO monumentos (casino, campanarios, cupulas, ayuntamiento): nunca casas normales ni
   elementos junto a la pista.
   **Topolino: no ahora, queda para el final.** En esta fase el penon del casino solo recibe la
   INTEGRACION BASICA (material de caliza compartido, luminancia de la meseta, cala con escollera), NO el
   detalle fino de roca (perfil por banco, estratos finos), para no repetir trabajo cuando se le de la
   silueta. (Bloque 2.7 se reduce a eso.)
   **Torre en la roca del lazo: SI** (italiano_kit.build_torre_costera en una repisa alta, bloque 2.6).
7. **Zips frecuentes: SI** (v1.2 tras F1, v1.3 tras F3, v1.4/v1.5 tras el export).

NOTA DEL COORDINADOR (04/10 19:15, para el propietario 'terreno' de F1): la sesion se corto a las ~16:50 con tu
trabajo a medias. terreno_montana.py YA tiene +353/-23 lineas tuyas (compila), assets/_geom_snapshot_terreno.json
esta actualizado y en 03_blender/_rev/_tmp_terreno/ estan tus QA_DIR qa_v6..v9, sonda.py, sonda_lado.py y
urbanismo_v12.json/.log (16:47). NO empieces de cero: lee `git diff 03_blender/terreno_montana.py`, retoma desde
ahi, y te faltan (al menos) medir_relieve.py, los checks nuevos, PARCHES_F1_terreno.md y la verificacion final.
Los otros 4 propietarios ya entregaron (sus parches estan en PARCHES_F1_*.md; mascara_terreno.py importa de
terreno_montana las constantes de umbral de roca si existen: coordina nombres leyendo PARCHES_F1_mascara.md).

## Paleta v2 (feedback del usuario sobre la carta de color, 04/10 ~19:30; valores sRGB del selector de Blender)

"Buena direccion en verdes y azules." Cambios que MANDAN sobre paleta.json v1:
- ROCAS mas calidas, sin gris azulado (el frio lo pone la sombra): caliza clara #D8CCB0, caliza media #B3A68A,
  roca oscura #7F766A.
- FACHADAS menos pastel, mas profundas y calidas; fuera el blanco grisaceo y el rosa bebe: azafran #E2A84A,
  ocre naranja #D88A4C, siena #C46A43, rojo pompeyano #B04A3B, melocoton #E6A487, crema calido #EBDDBE.
  Variacion aleatoria de +-5 % en tono y brillo POR CASA. Marcos de ventana y molduras en crema claro (estilo ligur).
- TEJADOS: terracota mas anaranjada #BF6440.
- ANADIR: cipres y pino oscuro #34503A; verdin de cupula #6FA391; contraventanas #3E6A48; acento de flores
  (buganvilla) #C2407A solo en pequenas dosis; marmol del casino en crema #EEE4CF, no blanco puro.
- CESPED verde vivo: solo en jardines y rotondas (ya decidido).
- AGUA: si se usa el shader de agua de CSP, estos azules valen para el FONDO marino; el color final lo dan el
  shader y el reflejo del cielo.
- VALIDACION: la paleta aplicada al PUEBLO JUNTO AL PUERTO, con LUZ DE TARDE y desde la CAMARA DEL COCHE (no en
  esferas). Y, si se puede, exportar esa zona a Assetto Corsa para comprobarla con Pure (-> mini-pista "F"
  pueblo_puerto para el amigo, tras la regeneracion de F1).
- 04/10 19:55, tras ver los pares antes/despues (renders/ab/paleta_v2): el usuario da el OK y pide bajar
  crema_calido a #E6D4B0 (leia casi blanco con sol de tarde). PALETA v2 = DEFINITIVA (paleta.json). No se
  vuelve a preguntar por colores salvo que el usuario lo pida.

Sigue vigente: la cuesta del tramo de tierra NO se baja (13-16 %); el desnivel viene del terreno lateral.
Sin logotipos de marcas reales. Video solo tras OK explicito del usuario sobre capturas.
