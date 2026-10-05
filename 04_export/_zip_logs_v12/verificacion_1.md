# Verificación independiente del zip v1.2 de Porto Corsa (intento 1), 05/10/2026

Veredicto: **APROBADO**. No hay ningún problema REAL. Quedan 4 MENORES y 4 COSMÉTICOS, abajo.
No he modificado nada del proyecto. Todo lo mío está en el scratchpad de la sesión (`<S>` = `C:/Users/arcej/AppData/Local/Temp/claude/E--Escritorio-claude-pc-arnau-aseto-corsa/1a7b6c0c-72d8-44ab-af11-95e782d87886/scratchpad`).
`04_export/porto_corsa_export.blend` tiene el mismo md5 antes y después de mis dos pasadas del writer (`md5sum -c`, OK).

## 1. Zip y KN5
- **Integridad del zip.** `zipfile.testzip()` da None.
  - 18 entradas; md5 del zip 09becf31.
  - El KN5 de dentro tiene md5 `cb604373e64bb85c8941eaa75d6dbc4d`, igual que `04_export/kn5/porto_corsa_opt.kn5`.
  - La copia de v1.1 en `_v12_dev/respaldo_v11/porto_corsa_mod.zip` tiene md5 213f15b2. Coincide.
- **kn5_check sobre el KN5 extraído del zip**: 9/9 OK (las 8 de siempre más la de shaders), rc=0, y la lectura consume 326 556 077 bytes exactos.
  - Orden: `python 04_export/kn5_check.py <S>/zip/content/tracks/porto_corsa/porto_corsa.kn5 --json <S>/check_zip.json --no-wait --shaders --quiet`
  - Tiene 45/45 dummies, 34 mallas 1ROAD, 141 1WALL, 0 normales nulas y 626 mallas.
- **Contenido del zip:**
  - `data/surfaces.ini`: DIRT con FRICTION=0.98, IS_VALID_TRACK=1.
  - `ui/ui_track.json`: "version": "1.2".
  - `extension/ext_config.ini`: VERSION = 1.2, palanca `ACTIVE = 0`.
  - `ai/fast_lane.ai`: 59 820 B.
  - `INSTRUCCIONES.md`: incluye la sección "Novedades de la versión 1.2" y menciona `ensayo_f_pueblo.zip`.
- **Reproducibilidad.** Volví a correr el writer con las mismas variables de entorno que hacer_zip (GEOM, TERRENO_BASE y TERRENO_MASK de `_zip_src`, `TERRENO_MODO=detalle`) y salió `<S>/repro.kn5` con md5 **cb604373…**, idéntico byte a byte.
  - Las 3 escenas tienen md5 31c18b1b: `escena_rev.blend`, `_zip_src/escena_v12.blend` y `promociones/escena_v1.blend`.
- **COLOR_AC=0 sigue funcionando:** `<S>/sin_color.kn5` sale con rc=0 y 324.3 MB. Tiene 485 texturas y 492 materiales, y kn5_check da 9/9 OK.

## 2. El terreno dentro del KN5
Lo leí con un lector propio (`<S>/ver_terreno.py`, `<S>/orient2.py`).
- **Material.** `MAT_terreno` usa `ksPerPixelMultiMap`, con useDetail=1 y detailUVMultiplier=689.33 (un tile de detalle cada 3.0 m).
  - Valores: ksSpecular 0, ksEmissive 0, fresnelMaxLevel 0. Es opaco y sin alpha test.
  - El aviso "pide ksMultilayer_fresnel_nm, se ignora" es correcto según el plan, §15.4 y 15.5.
- **Samplers:**
  - txDiffuse: `terreno_base_2048.png`, 2048², RGBA, con alfa constante 128. El detalle se mezcla al 50 % (color × (0.5 + 0.5·detalle)).
  - txNormal: 4×4 plano (128,128,255).
  - txMaps: 4×4 negro.
  - txDetail: 512², gris, media 187/255.
  - Todo PNG potencia de 2; no hay ningún DDS en el KN5 (489 de 489 son PNG).
- **UV.** El terreno son 7 mallas: 1GRASS p1 a p5, 2GRASS p1 y 1WALL p1. La 1WALL_..._terreno_roca usa `MAT_terreno_roca`.
  - Rango: u 0..0.998, v 0.002..1.0.
  - El ajuste lineal es exacto: u = x/2068 + 0.4511 y v = z/2060 + 0.5593. El error máximo es menor que 1e-4 texel de 2048.
  - Continuidad: el salto de UV por metro de arista da p99 = máx = 4.85e-4 (= 1/2060). No hay costuras ni estiramientos.
  - Las tangentes miden 1 y |T·N| ≤ 4e-5.
- **Orientación.** La correlación de la pendiente del vértice con el alfa de `terreno_mask.png` (la roca) es **+0.77** con la UV DirectX del KN5, frente a −0.05 con v volteada y +0.12 con u volteada.
  - La `terreno_base` del KN5 correla 0.966 con la de FUENTES, y 0.23 si se voltea.
  - Conclusión: la máscara no está ni volteada ni girada.

## 3. Física (`informe_fisica_final.json` v1.2 frente a `_v12_dev/respaldo_v11/informe_fisica_final.json`)
- **Puerta OK, todos a 0:**
  - huecos y huecos mayores de 2 m;
  - barreras falsas y muros en asfalto;
  - garajes (rodadas y rejilla);
  - atajos, escapes y caídas de escapatoria;
  - invisibles sobre visible a 3 cm.
- **Lo que cambia:**
  - terreno_hoyos: 190 → 261, con la misma profundidad máxima de 0.65 m. Es informativo.
  - n_muros: 893 → 876.
  - Tris de suelo: 735 k → 822 k.
  - Distancia mediana a la barrera en la tierra: lado +1 de 5.0 → 2.75 m y lado −1 de 4.0 → 6.7 m. Es la "tierra tallada", con pared a un lado y caída al otro.
- **Dummies.** Con un rayo vertical propio (`<S>/suelo_dummies.py`), los 47 AC_* del circuito caen sobre suelo físico, sin ningún caso raro:
  - 23 sobre ROAD, 20 sobre PIT, 2 sobre DIRT y 2 sobre KERB.

## 4. Vista "como AC" (03_blender/renders/ab/v12_como_ac)
- **Revisión visual.** Miré con Read las 9 imágenes `_par` y la hoja completa.
  - No hay texturas estiradas ni pixeladas en el terreno.
  - No hay materiales rosa, blancos ni negros nuevos, ni faltan objetos.
  - El mar y las islas están bien en 54 y 56.
  - Las casas llevan la paleta v2 (azafrán, siena, rojo pompeyano, crema): se ve en 50, 53 y en la vista F 40/06.
- **Reproducción.** Ejecuté kn5_vista por la cola sobre el KN5 del zip con las tomas 53 y 56: la diferencia con las entregadas es **0.0** (p99 0, máx 0).
  - Orden: `bash 03_blender/_rev/blender_cola.sh --python 04_export/kn5_vista.py -- --kn5 <S>/zip/.../porto_corsa.kn5 --out <S>/vista12 --solo 53,56`
- **Contraste con v1.1.** El mismo kn5_vista sobre el KN5 de v1.1, tomas 53 y 54, en `<S>/vista11`:
  - El pretil oscuro de 53 (textura tipo asfalto) ya estaba en v1.1.
  - La sombra casi negra de 54 sale igual: media [80,85,91] frente a [81,87,91] en v1.2.
  - Ninguna de las dos es una regresión.

## 5. Presupuestos (lo recalculé con kn5_check)
- tris: 4 935 674 de 6.0 M.
- KN5: 326.56 de 450 MB.
- texturas: 41.80 de 80 MB.
- mallas: 626 de 800.
- materiales: 493 de 520.
- zip: 190.08 de 250 MB.
- ksEmissive > 0: los mismos 8 materiales que en v1.1 (luces y pantallas, a 1.2).

## 6. Mini-pista F
- **El zip.** `ensayo_f_pueblo.zip` da testzip None y tiene 8 entradas.
  - El KN5 tiene md5 ab9cf400, igual dentro y fuera del zip.
  - kn5_check da 9/9 OK, con 45/45 dummies: AC_START 0-19, AC_PIT 0-19, AC_HOTLAP_START_0 y AC_TIME_0 y 1 (L y R).
- **Suelo bajo los dummies:** todos caen sobre `1ROAD_fusion_MAT_asfalto_p1`, a 1.0 m, y los TIME a entre 0.29 y 0.71 m.
  - Sus ficheros: `surfaces.ini` con DIRT 0.98, `ui_track` con versión 1.2-F, y LEEME.txt.
- **Toma 50:** la vista F frente a la del circuito completo tiene una diferencia media de 0.09 y un 0.3 % de píxeles por encima de 8.

## Clasificación
**REAL: ninguno.**

**MENOR:**
1. `INSTRUCCIONES.md` dice "La física es la misma que en la 1.1: mismos muros, mismas vallas, mismos boxes". No es literal:
   - n_muros pasa de 893 a 876;
   - en la tierra las barreras cambian: mediana +1 de 5.0 → 2.75 m y −1 de 4.0 → 6.7 m;
   - el muro `1WALL_..._LOEWS_tierra` pasa a `1WALL_..._cesped`.
   - Cómo verlo: el diff de los dos `informe_fisica_final.json`, en la sección 3.
   - Conviene decir "mismos boxes y vallas; en la subida de tierra la pared lateral cambia".
2. **Celosía del tile de detalle.** El detalle de 3 m se repite y se ve como una retícula en laderas a 100-500 m: `ensayo_f/vista_f/06_pueblo_calle.png`, zona 0-500 × 180-480, ampliada en `<S>/z06.png`.
   - Ya está registrada como F2 (decisión 15) y las instrucciones piden avisar si sale "a cuadros". Depende de los mipmaps de AC con PNG, que solo se pueden comprobar en el PC del amigo.
3. **Sombra casi negra en la vista de 54** (V≈0.09) y pretil oscuro en 53: ya estaban en v1.1 (`<S>/vista11`). Es el modelo de luz de color_ac y no se puede verificar sin AC.
4. **Vegetación:** 1.35 M tris frente al objetivo del plan de ≤ 0.9 M (`8_presupuesto.txt`). No es un tope duro.

**COSMÉTICO:**
1. La entrega da "891 732 tris" para la mini-pista F, pero el KN5 F tiene **1 719 568** (kn5_check). La cifra entregada es `tris_dentro` y no cuenta el terreno entero ni el horizonte (`resumen_f.json`).
2. La hoja da para la toma 01 un KN5 medio de [155,189,196] y `vista.json` de [154,189,200]. Es otra forma de medir.
3. `FUENTES/texturas/cesped_d.png` y `hierba_d.png` son el mismo fichero (md5 2c355a2a).
4. Ninguna de las 9 tomas mira de lleno al horizonte nuevo (HORIZ_ a 2.1-5.6 km del origen), así que la vista no lo ejercita. El mar, a 14 km, ya iba en v1.1.

**Pendiente honesto:** solo el PC del amigo puede confirmar que ksPerPixelMultiMap, los mipmaps de PNG, los FPS y el aspecto con CSP se ven como en la vista.
