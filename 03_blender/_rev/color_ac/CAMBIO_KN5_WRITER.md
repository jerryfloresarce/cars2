# CAMBIO en kn5_writer_opt.py y empaquetar.py para usar color_ac.py (v3)

Para el coordinador. Ninguno de los dos ficheros se ha tocado: abajo va el cambio exacto, en diff unificado.

- Los diffs estan en `04_export/_color_ac_prueba/kn5_writer_opt.diff` y `empaquetar.diff`. Los genera
  `04_export/_color_ac_prueba/hacer_parches.py` sobre las versiones ACTUALES (kn5_writer_opt.py de las 11:49 y
  empaquetar.py de las 14:09; si alguien los vuelve a tocar, basta con ejecutarlo otra vez): 6 cambios en el writer y
  1 en empaquetar. El script comprueba que cada fragmento antiguo
  aparece exactamente una vez y respeta los CRLF del original.
- Los dos pasan `git apply --check`.

## Que cambia respecto a la v2 del diff

- **Writer, cambio nuevo: roca del terreno.** Antes de `objetos_exportables()`, `color_ac.separar_roca_terreno()` pasa
  las caras de roca de MAT_terreno (mismo criterio que el nodo de Blender: N.z < 0.50, o atributo `roca` > 0.49 con
  N.z < 0.82) a un material nuevo `MAT_terreno_roca` (copia de MAT_terreno). Solo en memoria: el .blend no se guarda.
  Las mallas fisicas siguen igual (la fisica va por el prefijo del nombre de la malla, no por el material).
- **Writer:** el resumen JSON gana `color_ac_roca_terreno` (caras de roca por objeto).
- **empaquetar.py:** el mismo cambio que en la v2, regenerado sobre el fichero de las 14:09.
- **ext_config.ini:** sin el agua de CSP (sus olas se estirarian en nuestro quad de 20 km con UV 0..1) y con la
  palanca en ksAmbient 0.30 / ksDiffuse 0.55, apagada.

## Que hace

1. `kn5_writer_opt.py` importa `04_export/color_ac.py`.
   - `main()`: `separar_roca_terreno()` antes de recoger los objetos (ver arriba).
   - `recopilar_materiales()` pasa los infos por `color_ac.calibrar_todos()`. Esto cambia `info['color']`: el
     writer sigue haciendo la textura plana 8x8 o la tintada de 512 exactamente igual, con el color nuevo. Tambien
     anade `info['props_ac']`.
   - `escribir_texturas_y_materiales()` escribe `props_ac` en vez de `SHADER_PROPS`: los mismos 6 (ksAmbient,
     ksDiffuse, ksSpecular, ksSpecularEXP, ksEmissive, ksAlphaRef) y en el mismo orden.
   - El resumen JSON gana `color_ac` (antes/despues por familia y origen del objetivo) y `color_ac_roca_terreno`.
   - `COLOR_AC=0` en el entorno lo desactiva todo (tambien la roca) y deja el KN5 de siempre, para comparar.
2. `empaquetar.py` copia `04_export/extension/ext_config.ini` TAL CUAL a
   `paquete/content/tracks/porto_corsa/extension/ext_config.ini`, donde lo busca CSP. Sin CSP la carpeta se ignora.
   Solo si el fichero no existe lo crea con los valores por defecto.

`color_ac.py` usa solo numpy (lo tienen el Python de Blender y el del sistema) y lee dos ficheros de 04_export:

- `color_ac_objetivos.json`: el aspecto real de 151 materiales en 7 vistas de Blender, por clase de cara (incluido
  `MAT_terreno_roca`). Lo genera `03_blender/_rev/color_ac/medir_objetivos.py` con los pases de `render_ac.py`.
- `color_ac_albedo.json`: el albedo medido de 177 materiales procedurales (`medir_albedo.py`).

Si un material cambia en Blender (su color del writer se mueve mas de 0.02), sus medidas se ignoran solas y se usa el
modelo albedo x luz. Las medidas salen de la copia congelada `03_blender/_rev/color_ac/escena_color.blend`
(= porto_corsa.blend de las 13:00, md5 a6fb4195...).

## Ya probado (sin tocar los originales)

- Export de la escena congelada con el `exportar_ac.py` actual (BLEND/SALIDA/GEOM por el entorno) ->
  `04_export/_color_ac_prueba/export_color.blend`; writer parcheado (`kn5_writer_opt_color.py`) ->
  `04_export/_color_ac_prueba/porto_corsa_color.kn5`: 285.7 MB, 465 materiales, md5 ce33daa0ac5ff08055df5ead3d961af3.
  - Roca: 18659 caras de roca en 1GRASS_terreno 13463, 1WALL_tunel_acantilado 4002, 2GRASS_arcen_der 720, 2GRASS_arcen_izq 474.
- `kn5_check.py` da **RESULTADO: OK** (8/8; `_color_ac_prueba/informe_check_color.json`).
- `_color_ac_prueba/comparar_kn5.py` frente al mismo writer con `COLOR_AC=0` da **OK**: los 61 dummies con sus matrices,
  las 591 mallas que no son de terreno iguales byte a byte, los mismos 4.631.431 triangulos (los de MAT_terreno +
  MAT_terreno_roca = los de MAT_terreno en cada grupo; 23.873 de roca), los 464 materiales de antes en el mismo orden
  + MAT_terreno_roca, y los mismos shader/alphaBlend/alphaTested/depthMode.
- `python 04_export/prueba_color_ac.py` da **RESULTADO: OK** (7 bloques; ahora el 7 puede fallar en los cuatro modos
  de referencia: lo comprobe con la v3 a medio hacer, que fallaba por la caliza en la configuracion estimada).

## Como aplicarlo

```
cd E:/Escritorio/claude-pc/arnau-aseto-corsa
git apply 04_export/_color_ac_prueba/kn5_writer_opt.diff
git apply 04_export/_color_ac_prueba/empaquetar.diff
python 04_export/prueba_color_ac.py           # el bloque 5 dira que el parche ya no aplica: es lo esperado
```

Si `git apply` falla porque los ficheros han cambiado, los 7 reemplazos del diff son literales y cortos y se pueden
hacer a mano. Despues, la cadena de siempre: exportar_ac.py -> kn5_writer_opt.py -> kn5_check.py -> empaquetar.py.

Si otros equipos cambian materiales o la escena, rehacer las medidas antes de exportar (copiar la escena nueva a
`03_blender/_rev/color_ac/escena_color.blend` o pasarla con ESCENA=...):
`bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/color_ac/render_ac.py` (90 s) y
`python 03_blender/_rev/color_ac/medir_objetivos.py`; para los procedurales,
`bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/color_ac/medir_albedo.py`.

## Que esperar en el juego (simulacion: `03_blender/_rev/color_ac/informe_color_ac.md`)

- **AC sin CSP, o CSP con estilo gamma (Sol, Pure Gamma), tiempo 3_clear.** deltaE frente a Blender 25.6 -> 14.2 en las vistas de ajuste y 24.4 -> 13.7 en las de control; croma 0.73 -> 0.89 y contraste 1.44 -> 1.13 x Blender.
- **CSP con espacio lineal, curva ACES.** deltaE frente a Blender 19.5 -> 12.7 en las vistas de ajuste y 17.8 -> 12.3 en las de control; croma 0.93 -> 1.18 y contraste 1.25 -> 1.17 x Blender.
- **CSP con espacio lineal, sRGB + Yebis.** deltaE frente a Blender 20.2 -> 14.8 en las vistas de ajuste y 19.8 -> 17.6 en las de control; croma 0.71 -> 0.86 y contraste 0.96 -> 0.91 x Blender.
- **Configuracion estimada del amigo (la de su captura, con su brillo bajado).** deltaE frente a Blender 28.1 -> 19.2 en las vistas de ajuste y 27.6 -> 19.9 en las de control; croma 0.50 -> 0.58 y contraste 0.77 -> 0.92 x Blender.
- **La misma con el brillo por defecto.** deltaE frente a Blender 46.5 -> 41.4 en las vistas de ajuste y 45.7 -> 41.0 en las de control; croma 0.23 -> 0.29 y contraste 0.38 -> 0.50 x Blender.
- **AC sin CSP con 5_light_clouds.** deltaE frente a Blender 16.7 -> 12.9 en las vistas de ajuste y 16.5 -> 13.1 en las de control; croma 0.71 -> 0.81 y contraste 0.93 -> 0.97 x Blender.
- **Segunda hipotesis para la captura: 5_light_clouds, brillo x1.4, saturacion 0.7.** deltaE frente a Blender 26.5 -> 16.0 en las vistas de ajuste y 25.5 -> 15.3 en las de control; croma 0.49 -> 0.62 y contraste 0.92 -> 1.02 x Blender.


## Diff de 04_export/kn5_writer_opt.py

```diff
--- a/04_export/kn5_writer_opt.py
+++ b/04_export/kn5_writer_opt.py
@@ -46,6 +46,7 @@
 import math
 import os
 import struct
+import sys
 import time
 import zlib
 
@@ -54,6 +55,11 @@
 from mathutils import Matrix, Vector
 
 BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
+# color_ac.py: recalibra color y props de shader para AC (antes el circuito salia casi blanco en el juego);
+# env COLOR_AC=0 lo desactiva (colores y SHADER_PROPS de siempre, para comparar)
+sys.path.insert(0, os.path.join(BASE, '04_export'))
+import color_ac  # noqa: E402
+USAR_COLOR_AC = os.environ.get('COLOR_AC', '1') != '0'
 # fisica: env BLEND (escena de export), KN5 (kn5 de salida) y KN5_JSON (resumen) para pruebas sobre copias
 BLEND = os.environ.get('BLEND') or BASE + r'\04_export\porto_corsa_export.blend'
 OUT_KN5 = os.environ.get('KN5') or BASE + r'\04_export\kn5\porto_corsa_opt.kn5'
@@ -295,6 +301,8 @@
     infos = [analizar_material(m) for m in orden]
     infos.append({'name': DEFAULT_MAT, 'color': (0.5, 0.5, 0.5), 'alpha': 1.0, 'img': None,
                   'gain': 1.0, 'factor': 1.0, 'scale': 1.0, 'proj': 'FLAT'})
+    if USAR_COLOR_AC:       # color para AC (aspecto medido en Blender + modelos de luz de AC) y props por familia
+        infos = color_ac.calibrar_todos(infos)
     return infos
 
 
@@ -325,8 +333,9 @@
         w.u8(1 if info['transparent'] else 0)     # alphaBlendMode: 0 opaco, 1 alpha blend
         w.u8(0)                                   # alphaTested
         w.i32(0)                                  # depthMode: DepthNormal
-        w.i32(len(SHADER_PROPS))
-        for pname, val in SHADER_PROPS:
+        props = info.get('props_ac', SHADER_PROPS)   # por familia de material (color_ac.FAMILIAS)
+        w.i32(len(props))
+        for pname, val in props:
             w.string(pname)
             w.f32(val)                            # A
             w.floats((0.0, 0.0))                  # B
@@ -739,6 +748,10 @@
     print('escena de export v%d: giro de 180 grados de AC_* %s' % (
         export_v, 'APLICADO (escena antigua)' if any(AC_GIRAR_180.values()) else 'NO necesario'))
     os.makedirs(os.path.dirname(OUT_KN5), exist_ok=True)
+    # color_ac: las caras de roca de MAT_terreno (mismo criterio que el nodo de Blender) pasan a MAT_terreno_roca,
+    # solo en memoria (el .blend no se guarda)
+    roca_ac = color_ac.separar_roca_terreno() if USAR_COLOR_AC else {}
+    print('color_ac: %d caras de roca -> %s %s' % (sum(roca_ac.values()), color_ac.ROCA_MAT, roca_ac))
     objs = objetos_exportables()
     infos = recopilar_materiales(objs)
     por_nombre = {i['name']: i for i in infos}
@@ -850,6 +863,8 @@
             'texturas_reducidas_a_%d' % TEX_MAX: _tex_stats['reducidas'],
             'n_nodos_total': s['n_dummies'] + s['n_mallas'], 'orden_espacial_celda_m': MORTON_CELL},
         'segundos': round(time.time() - t0, 1),
+        'color_ac': color_ac.informe(infos) if USAR_COLOR_AC else 'desactivado (COLOR_AC=0)',
+        'color_ac_roca_terreno': roca_ac,
     }
     json.dump(resumen, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
     r2 = dict(resumen)
```

## Diff de 04_export/empaquetar.py

```diff
--- a/04_export/empaquetar.py
+++ b/04_export/empaquetar.py
@@ -286,6 +286,14 @@
         if fn.endswith('.png') and not fn.startswith('mosaico'):
             shutil.copy2(os.path.join(texdir, fn), dst)
 
+# ---------- extension/ext_config.ini (Custom Shaders Patch) ----------
+# se copia TAL CUAL 04_export/extension/ext_config.ini (se puede editar a mano; color_ac solo lo genera si no
+# existe) a content/tracks/porto_corsa/extension/, donde lo busca CSP (sin CSP la carpeta se ignora)
+import sys  # noqa: E402
+sys.path.insert(0, os.path.join(BASE, '04_export'))
+import color_ac  # noqa: E402
+print('ext_config.ini (CSP) ->', color_ac.copiar_ext_config(TRACK))
+
 # instrucciones al zip
 ins = BASE + r'\04_export\INSTRUCCIONES.md'
 if os.path.exists(ins):
```
