# PARCHES F1 — propietario `mascara` (máscara del terreno por texel, UV planar, MAT_terreno v2, MAT_cesped, luz)

Fase visual F1, bloque 3 puntos 4-6 de `FASE_VISUAL_PLAN.md`. Escrito el 04/10/2026. Ficheros MÍOS (ya editados):
`03_blender/mascara_terreno.py` (nuevo, python del sistema) y `03_blender/construir_pista.py`. Todo lo demás va aquí como
parche exacto para el integrador (o para el propietario del fichero, donde se indica). Nada de `04_export` se ha tocado.

## 0. Contratos que fija esta entrega (para todos)

- **Ficheros generados por `mascara_terreno.py`** (tras `preparar_geometria` + `urbanismo`, antes de `construir_pista`):
  `texturas/terreno_mask.png` (RGBA 2048, R matorral / G hierba seca / B tierra / A roca, suma = 1), `texturas/terreno_ao.png`
  (L 2048), `texturas/terreno_base.png` (RGB 2048 sRGB = paleta x parches x AO x sombra de bosque), `renders/qa/terreno_mask.png`
  y `renders/qa/terreno_mask_stats.json`. ~5 s. Deterministas (seed 15).
- **UV planar del TERRENO** (y de `ARCEN_IZQ/DER`, `ARCEN_PIT_*`, que comparten MAT_terreno): `u = (x - x0) / (nx·cell)`,
  `v = (y - y0) / (ny·cell)` con la rejilla de `geometria_3d.json['terreno']` (hoy 2068 x 2060 m). Fila 0 de los PNG = y máximo
  (convención de imagen de Blender: v = 0 abajo). El material la recalcula por `Geometry.Position`, así que cualquier cara con
  MAT_terreno sin capa UV (la falda del McLaren que asigna `integrar_escena` l.3172) se pinta igual de bien.
- **Umbrales en UN solo sitio**: `mascara_terreno.UMBRALES` (dict): `PEND_ROCA (0.70, 0.84)`, `PEND_ROCA_ANCHO 0.12`,
  `PEND_SUAVIZADO_M 10`, `PEND_ROCA_DURA 1.25`, `ROCA_MIN_CELDAS 12`, `ROCA_ATR 0.50 ± 0.08`, `PIE_M (6, 10)`, `DIRT_BORDE_M 8`,
  `LLANO_PEND 0.35`, `LLANO_DIST_M 60`, `LLANO_Z 60`, `RUIDO_M (10, 30)`, `LOEWS_R_INTACTA 90`. El módulo se importa SIN scipy
  (Blender) para leer solo constantes; `terreno_montana` debe importarlos de aquí (parche A2), no al revés.
- **Sol de la escena**: `mascara_terreno.SOL = {'elev_deg': 48, 'azimut_deg': 151, 'rot_blender_deg': (42, 0, -119)}`;
  `construir_pista.py` lo lee de ahí (antes `(34, 0, -140)`). El hillshade de `terreno_ao.png` usa el mismo sol.
- **`extras['capas']`** (bloque 1.6, cuando el propietario `terreno` lo saque): `geometria_3d.json['extras']['capas']` =
  `{'matorral': [...], 'hierba_seca': [...], 'tierra': [...], 'roca': [...]}` listas de `nx·ny` floats 0..1 por celda. Si existe,
  `mascara_terreno` lo usa en vez de sus reglas (solo añade ruido de borde y normaliza). `mascara_roca` se mantiene.
- **`vegetacion_plan.json`**: contrato A3 de `PARCHES_F1_vegetacion_plan.md` ya implementado: `plantas` de especie con
  `clase == 'arbol'`, radio de sombra `1.2 x especies[e].radio_copa_m x escala_xy`; respaldo `masas` (cx, cy, r).
- **Custom props `ac_*`** (decisión 5): `MAT_terreno`: `ac_shader = 'ksMultilayer_fresnel_nm'`, `ac_samplers = {txDiffuse:
  terreno_base.png, txMask: terreno_mask.png, txDetailR/G/B/A: matorral_d/hierba_seca_d/tierra_d/caliza_d (rutas absolutas),
  txDetailNM: caliza_n.png}`, `ac_props = {multR 344.67, multG 689.33, multB 344.67, multA 689.33, detailNMMult 689.33,
  fresnelC 0.02, fresnelEXP 3, fresnelMaxLevel 0.1, ksAmbient 0.45, ksDiffuse 0.55, ksSpecular 0.08, ksSpecularEXP 10,
  ksEmissive 0, ksAlphaRef 0, magicMult 1}`, `ac_tex_max = {txMask 2048, txDiffuse 2048, txDetail* 1024}`, `ac_raw 1`,
  `ac_ao = terreno_ao.png`. `MAT_cesped` y `MAT_fondo_marino`: `ksPerPixel` con los `SHADER_PROPS` de hoy (`ac_raw 0`);
  `MAT_cesped['ac_grassfx'] = 1` (es el ÚNICO material que listará GrassFX, bloque 9).
- **Lo que ve el writer de HOY** en MAT_terreno (sin P3/P10): `diffuse_color = hierba_seca`; la primera Image sRGB enlazada es
  `hierba_seca_d.png`; nodo `TEX_mapping` (sin enlazar) con escala 1/3 m para las mallas sin UV y para `capturas_ab --modo-ac`.
  El nodo `Math.002` con etiqueta `ROCA_mascara` sigue existiendo = max(canal A, atributo `roca` con ruido y sin llano, talud
  por normal real): lo leen `_rev/color_ac/render_ac.py`, los revisores y `color_ac`.

## A. Parches a ficheros ajenos (los aplica el integrador salvo donde se diga)

### A1. `_rev/pipeline_escena.sh` — paso `mascara_terreno.py` (integrador)

Tras la línea `python urbanismo.py ... grep -E "QA:|TOTAL casas" ...` y ANTES del bucle `for p in construir_pista ...`:

```bash
# fase visual F1 (bloque 3.4): mascara del terreno por texel (python del sistema, ~5 s): texturas/terreno_mask.png,
# terreno_ao.png, terreno_base.png + renders/qa/terreno_mask.png. construir_pista.py la lee (MAT_terreno v2); si faltara,
# construir_pista la genera el solo (red de seguridad), pero el orden del plan secc. 13 es este.
python mascara_terreno.py > "$LOGS/mascara_terreno.log" 2>&1 || { echo "FALLO mascara_terreno"; tail -20 "$LOGS/mascara_terreno.log"; exit 1; }
grep "MASCARA_TERRENO" "$LOGS/mascara_terreno.log" | cut -c1-300
```

Y, si el integrador coloca `python vegetacion.py` (parche A1 de `PARCHES_F1_vegetacion_plan.md`) DESPUÉS de la máscara (el plan
lee los canales A/B de `terreno_mask.png`), inmediatamente después de `vegetacion.py` añadir la segunda pasada que solo
reescribe la base con la sombra de bosque del plan recién calculado (mismo cálculo determinista, ~5 s):

```bash
python mascara_terreno.py --solo-base >> "$LOGS/mascara_terreno.log" 2>&1 || { echo "FALLO mascara_terreno --solo-base"; exit 1; }
```

Prueba: `bash _rev/pipeline_escena.sh <logs>`; en `$LOGS/mascara_terreno.log` la línea `MASCARA_TERRENO: 2048x2048 | ... suma
ok 100.00 %`; `construir_pista.log` con `MAT_terreno v2: mascara terreno_mask.png, base terreno_base.png, tiles {...}` y SIN la
línea `AVISO: faltan PNG de la mascara`.

### A2. `terreno_montana.py` l.2261 — mismos umbrales que la máscara (propietario `terreno`, bloque 2.2)

```python
# cabecera (python del sistema; mascara_terreno importa paleta y numpy/scipy, sin bpy)
from mascara_terreno import UMBRALES as UMBRALES_MASCARA
...
# l.2261: antes  _nat_r = (gaussian_filter(pendiente, 2.5) > 1.0 + 0.1 * _nr) & ~_acg & ~_dsm
_p_lo, _p_hi = UMBRALES_MASCARA['PEND_ROCA']                       # (0.70, 0.84) = 35-40 grados, UN solo sitio de verdad
_nat_r = (gaussian_filter(pendiente, UMBRALES_MASCARA['PEND_SUAVIZADO_M'] / cell)
          > 0.5 * (_p_lo + _p_hi) + 0.5 * (_p_hi - _p_lo) * _nr) & ~_acg & ~_dsm
# l.2265: _peq = _tam_r < 12  ->  _peq = _tam_r < UMBRALES_MASCARA['ROCA_MIN_CELDAS']
```

(`_nr` ya es ruido de 30 m en [-1, 1]; `mascara_terreno` usa además la convexidad para que la roca aflore en crestas.)
Prueba: `python preparar_geometria.py` a un QA_DIR; `mascara_roca > 0.5` pasa del 6.6 % de las celdas de tierra a ~20-25 %;
`python mascara_terreno.py --geom <qa>/geometria_3d.json --out <tmp> --qa <tmp>`: `area_pct_tierra_dominante.roca` sube poco
(ya cuenta la pendiente) y `nz_lt_0_7.pct_roca_A_gt_0_5` se mantiene >= 90 %. Pedir también a `color_ac.ROCA_NZ/ROCA_ATR` (P1).

### A3. `MAT_cesped` en los objetos de jardín (el material ya existe en el .blend con fake user desde `construir_pista.py`)

Hoy NINGÚN objeto de `construir_pista.py` es un jardín: los lleva `integrar_escena.py` y los kits. Localizados:

**A3.a `assets/horquilla_loews.py` (rotonda de la palmera = parterre de la Loews; propietario kits)**, l.353 y l.418: los dos
discos de "suelo de tierra" del interior y del parterre superior pasan a césped:

```python
# l.353  mb.add(*_lathe([(R - 0.35, 0.03), (0.0, 0.03)], seg=SEG), _mat("tierra"))
mb.add(*_lathe([(R - 0.35, 0.03), (0.0, 0.03)], seg=SEG), bpy.data.materials.get('MAT_cesped') or _mat("tierra"))
# l.418  mb.add(*_lathe([(rp - 0.30, ztop), (0.0, ztop)], seg=SEG), _mat("tierra"))
mb.add(*_lathe([(rp - 0.30, ztop), (0.0, ztop)], seg=SEG), bpy.data.materials.get('MAT_cesped') or _mat("tierra"))
```

(`_mat("tierra")` queda como respaldo en `test_horquilla_loews.py`, que no pasa por construir_pista.) Prueba: en la escena,
`LOEWS_rotonda` tiene un slot `MAT_cesped`; captura `58_postal_loews` y `12_rotonda_loews`: césped verde solo en la isleta.

**A3.b `integrar_escena.py` `zona_casino` l.2098-2119 (jardines del casino; integrador)**: hoy los jardines son solo plantas
sobre el TERRENO (que ahora es hierba seca/matorral por la máscara). Para césped de verdad hace falta UNA losa fina:

```python
    # fase visual F1 (bloque 3.5): parterre de cesped bajo los jardines del casino (unico sitio con MAT_cesped ademas de la
    # Loews). Disco de r 55 m centrado en (gx, gy) que sigue el terreno (+0.04) y respeta 11 m al eje de la pista.
    m_c = bpy.data.materials.get('MAT_cesped')
    if m_c is not None:
        vs, fs = [], []
        anillos, radios = 24, [0.0] + [55.0 * k / 6.0 for k in range(1, 7)]
        for r_ in radios:
            for k in range(anillos if r_ > 0 else 1):
                a_ = 2 * math.pi * k / anillos
                x_, y_ = gx + r_ * math.cos(a_), gy + r_ * math.sin(a_)
                vs.append((x_ - gx, y_ - gy, z_terreno(x_, y_) + 0.04 - z_terreno(gx, gy)))
        # (triangular los anillos como un abanico: n = 1 + 6 * anillos vertices; omitir los triangulos cuyo centro queda a < 11 m
        #  del eje de la pista, min((cx - S[i]['x'])**2 + (cy - S[i]['y'])**2 for i in range(0, N, 6)) < 11**2)
        ...
        me_ = bpy.data.meshes.new('CALLE_jardin_casino'); me_.from_pydata(vs, [], fs); me_.materials.append(m_c)
        ob_ = bpy.data.objects.new('CALLE_jardin_casino', me_); root_col.objects.link(ob_)
        ob_.location = (gx, gy, z_terreno(gx, gy))
```

Alta necesaria por ser PREFIJO NUEVO (plan 15.21): `asentar_objetos.SOPORTE_PREF`/`LOSA_PLAN` (como `CALLE_plaza*`, losa que
sigue el terreno: NO macizar en `cimas()`), `revisar_urbanismo.LOSA_PREF_QA/PROP_NO`, `revisar_flotantes.EXENTOS`,
`nada_en_pista.PERMITIDOS` (está a >= 11 m del eje: no debe salir), `eliminar_sumergidos` (z > 8 m: no afecta) y en
`PETICIONES_04_EXPORT.md`/P6: `CALLE_jardin` -> `1GRASS_` en `exportar_ac` (suelo con física de hierba, `castShadows = 0`) y
`revisar_fisica_ac.NO_OBSTACULO += CALLE_jardin`. Si el integrador prefiere NO crear geometría en F1, la alternativa sin
coste es dejar el terreno de los jardines como hierba seca (la máscara ya lo hace a < 60 m de la pista) y aplazar la losa a F3.

**A3.c `urbanismo_escena.py` l.321 `poligono(nombre, poly, z, mat, grosor)` (propietario pueblo-escena, bloque 5.2)**: cuando
existan `patios`/`CALLE_patio` del plan de manzanas, los patios ajardinados van con `bpy.data.materials.get('MAT_cesped')`;
las plazuelas (`CALLE_plaza_fondo`, `edicolas`) siguen de adoquín (`m_ad`): no son césped.

### A4. `_rev/carta_color.py` l.~120 (sol) — misma luz que la escena (propietario `materiales`/infra, opcional)

```python
# antes: sun.rotation_euler = (math.radians(34), 0, math.radians(-140))
import mascara_terreno
sun.rotation_euler = tuple(math.radians(v) for v in mascara_terreno.SOL['rot_blender_deg'])   # (42, 0, -119)
```

Prueba: `blender_cola.sh --python _rev/carta_color.py` -> la carta cambia solo el sombreado de las esferas (color igual).

### A5. `PETICIONES_04_EXPORT.md` — líneas que debe AÑADIR el integrador (bloque X)

- **P10 (ampliación, interino)** El TERRENO y los `ARCEN_*` llevan ahora `uv_layers[0]` planar 0..1 sobre 2068 m. Con el writer
  de hoy (`loops_grupo` l.387-408: "uv_layers[0] si existe") el tile `hierba_seca_d` de 512 px se ESTIRA sobre todo el terreno
  (un texel = 4 m: color plano dorado, sin grano). Hasta que P10 lleve el multicapa, el writer debe o bien IGNORAR la UV de
  `1GRASS_terreno` / `2GRASS_arcen*` cuando el shader es ksPerPixel (UV generada Object x `TEX_mapping` 1/3 m, como hasta hoy),
  o bien multiplicar la UV por `m['ac_props']['multG']`. Prueba: `kn5_check --quiet` `uv_rango` del terreno ~[0, 689] y foto del
  amigo con grano de hierba de 3 m.
- **P10 (datos)** `MAT_terreno['ac_samplers']` trae rutas ABSOLUTAS (`txDiffuse` terreno_base.png 2048, `txMask` terreno_mask.png
  2048 RGBA sin tintar, `txDetailR/G/B/A` 1024, `txDetailNM` caliza_n.png 1024 OpenGL), `ac_props` con `multR..A`,
  `detailNMMult`, fresnel y ks*, `ac_tex_max` por sampler y `ac_raw = 1`. Presupuesto medido: 0.58 + 1.2 + 0.46 MB de PNG
  (+ 4 tiles de ~2 MB + normal 2 MB): ~11 MB, muy por debajo de los 80 MB.
- **P1 (nota)** `color_ac.separar_roca_terreno` sigue válido: el atributo `roca` y las normales no cambian; el canal A de
  `terreno_mask.png` ya incluye la pendiente > 35-40 grados, así que `MAT_terreno_roca` (ksPerPixel) debería leer la máscara
  (`mask[..., 3] > 0.5` muestreada con la misma UV) y no solo `nz < 0.50`.
- **P6 (si se aplica A3.b)** `CALLE_jardin` -> `1GRASS_`; `NO_OBSTACULO += CALLE_jardin`.

### A6. Nada que registrar en inspectores

Esta entrega NO crea objetos con prefijo nuevo (solo materiales: `MAT_terreno` v2, `MAT_cesped`, `MAT_fondo_marino`; `AGUA_fondo`
ya existía). `aplicar_texturas.py` salta MAT_terreno y MAT_cesped por el nodo `TEXTURIZADO` (`familia_de` devuelve `terreno` /
None); `mejorar_materiales.py` no los toca (PREFIJOS). `asentar_objetos.TER_OK` (nx·ny vértices, identidad) no cambia con la UV.

## B. Lo hecho en mis ficheros (resumen para el integrador)

- `mascara_terreno.py`: `generar(geom, urb, out_dir, px=2048, seed=15, veg_plan=None, qa_dir=None, solo_base=False)`; CLI con
  `--geom/--urb/--out/--qa/--px/--seed/--veg/--solo-base` (y `GEOM`/`URBANISMO` por entorno). Reglas 3.4 + limpieza morfológica
  (manchas y huecos < 12 celdas), roca "dura" en pendiente real > 1.25, hierba seca también en las bandas de terrazas de
  `urbanismo.json`, fondo marino somero = canal B con base arena apagada (NO banda blanquecina), AO = cavidad + horizonte 8 dir
  (160 m) + hillshade suave, sombra de bosque desde `vegetacion_plan.json`. Stats en `renders/qa/terreno_mask_stats.json`.
- `construir_pista.py`: bloque importable `>>> MATERIAL TERRENO v2 ... <<<` (`mat_terreno`, `_roca_terreno`, `mat_cesped`,
  `mat_fondo_marino`, `_uv_planar`, `_ac_props`, `_mascara_ficheros`, enganche `materiales_roca.crear_nodos` cuando existe:
  HOY existe y se usa); UV planar en TERRENO/arcenes; `AGUA_fondo` con `MAT_fondo_marino`; literales de paleta sustituidos
  (`MAT_tierra`, `MAT_acera_piedra`, `MAT_bordillo_piedra`, `MAT_arcen`, `MAT_muro_contencion_piedra`); sol (42, 0, -119);
  `use_fast_gi` explícito con `fast_gi_distance 0` (= sin límite = lo de hoy; `use_gtao` no existe en 5.1); `BLEND_OUT` /
  `RENDERS_OUT` por entorno SOLO para pruebas sobre copia. `view_transform` y exposición intactos; sin niebla.
- Prueba sobre copia completa sin regenerar: `_rev/_tmp_mascara/aplicar_v2_a_copia.py` (exec del bloque v2 sobre
  `escena_antes_visual.blend` -> `_rev/_tmp_mascara/escena_v2.blend`) + `capturas_ab.py --solo 49_,51_,07_,01_` normal y AC.

## Ronda 2 (04/10/2026, noche) — arreglos a `director_f1_r1.md` problemas 1 (REAL) y 6 (MENOR), + cosmético 12

Ficheros MÍOS cambiados: `03_blender/construir_pista.py`, `03_blender/mascara_terreno.py` (y mi prueba `_rev/_tmp_mascara/aplicar_v2_a_copia.py`).
Pruebas en `_rev/_tmp_mascara/r2/` (geometria_r2.json, tex/, qa/, pista_r2.blend, ab/, logs). Nada del proyecto regenerado.

### R2.1 Problema 1 (REAL): rutas de imagen relativas -> MAGENTA fuera de `03_blender/`. ARREGLADO en `construir_pista.py`

- Causa confirmada: `--factory-startup` (fichero sin nombre) + `save_as_mainfile(OUT_BLEND)` con `relative_remap=True` por defecto
  convertía las 7 Image de F1 a `//texturas\...` al guardar por primera vez. Comprobado con un lector zstd (sin Blender):
  `escena_candidata.blend` 7 rutas relativas (`//texturas\{caliza_d,cesped_d,hierba_seca_d,matorral_d,terreno_base,terreno_mask,tierra_d}.png`),
  `escena_antes_visual.blend` 0 relativas / 8 absolutas, y mi `pista_v2.blend` de r1 (guardado en `_tmp_mascara/`) 7 relativas
  `//..\..\texturas\...` (el mismo mecanismo).
- Arreglo (final de `construir_pista.py`): `bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, relative_remap=False)`, precedido de una
  red (cualquier `//` se hace absoluta respecto a `03_blender/`) y seguido de la comprobación `rutas de imagen tras guardar: N
  absolutas, 0 relativas`; si quedara alguna, `ERROR ...` y `sys.exit(1)` (el pipeline corta porque mira el rc).
  `integrar_escena`/`aplicar_texturas`/`mejorar_materiales` abren y guardan sobre el MISMO fichero: no remapean (por eso
  `escena_antes_visual.blend` tenía absolutas). Comportamiento idéntico al de antes de F1.
- Prueba hecha: `GEOM=... MASCARA_DIR=... BLEND_OUT=_rev/_tmp_mascara/r2/pista_r2.blend bash blender_cola.sh --python construir_pista.py`
  -> log `rutas de imagen tras guardar: 7 absolutas, 0 relativas`; lector zstd sobre `pista_r2.blend`: `relativas: 0 | absolutas: 6
  (de texturas/: 6)`; `capturas_ab --solo 49_,51_,07_,01_` modo normal desde `_rev/_tmp_mascara/r2/` SIN magenta (ver R2.4).
- **Parche A7 al integrador (red de seguridad, `_rev/*`)**: lector de rutas sin abrir Blender (necesita `zstandard`: lo trae el
  python de Blender 5.1, no el del sistema; los .blend de 5.1 van en zstd):
  ```bash
  cp 03_blender/_rev/_tmp_mascara/r2/comprobar_rutas_blend.py 03_blender/_rev/comprobar_rutas_blend.py
  ```
  y en `_rev/pipeline_escena.sh`, dentro de `copiar_candidata()` justo tras el `cp porto_corsa.blend "$REV/escena_candidata.blend" ...`
  (antes del md5):
  ```bash
  # fase visual F1 r2 (PARCHES_F1_mascara.md R2.1): ninguna Image con ruta relativa '//' en la candidata (si no, magenta fuera de 03_blender/)
  BPY="C:/Program Files/Blender Foundation/Blender 5.1/5.1/python/bin/python.exe"
  "$BPY" "$D/_rev/comprobar_rutas_blend.py" "$REV/escena_candidata.blend" | tail -12 \
    || { echo "FALLO candidata con rutas de imagen relativas (ver arriba): no se promueve"; return 1; }
  ```
  (con `set -o pipefail` o comprobando `${PIPESTATUS[0]}`; el script sale 1 si hay alguna `//`, 2 si no puede leer el .blend).
  Opcional en `_rev/promover.sh` antes del `cp "$CAND" "$REV/escena_rev.blend"`: la misma llamada con `|| negar "candidata con rutas relativas"`.
  Prueba del parche: `"$BPY" _rev/comprobar_rutas_blend.py _rev/escena_candidata.blend` sobre la candidata de r1 -> exit 1 con las 7
  rutas; sobre `_rev/escena_antes_visual.blend` -> exit 0.
- Para el A/B del integrador (problema 5 del director): tras regenerar con este `construir_pista.py`, el "después" en modo normal
  ya no sale magenta; la hoja normal de r1 (scratchpad del director) queda invalidada y hay que repetirla dentro de `renders/ab/f1_r1/`.

### R2.2 Problema 6 (MENOR): B1 aplicado + roca dura también con `extras['capas']`. ARREGLADO en `mascara_terreno.py`

- `UMBRALES['PEND_ROCA'] = (0.68, 0.80)` y `PEND_SUAVIZADO_M = 8.0` (B1 de `PARCHES_F1_terreno.md`; `terreno_montana` los importa:
  `umbrales_roca()` -> `pend 0.74, ruido 0.06, nz 0.804, sigma_m 8.0, origen mascara_terreno.UMBRALES`, comprobado).
  `preparar_geometria.py` a `_rev/_tmp_mascara/r2/` (15 s): `roca: 81.3 % de las celdas de tierra > 35 grados llevan roca` (antes 73.3;
  objetivo >= 80), > 40 grados 85.9 % (antes 82.9), roca en 27.6 % de la tierra (antes 24.3), pie de derrubios 5734 celdas (5475).
  `medir_relieve.py --antes geometria_3d.json`: **dz = 0.00 m en todas las celdas** (solo cambian `mascara_roca` y `extras.capas`):
  urbanismo (193 casas), asentar, costuras, Loews, McLaren y corredor NO cambian por este parche; invariantes iguales.
- El 5.9 % de verde en caras nz < 0.7 NO venía de los umbrales: en r1 la máscara ya usaba `extras.capas` (parche A1 de terreno
  aplicado por el integrador) y la regla de "roca dura por pendiente REAL" solo se aplicaba en la vía de reglas. Ahora es común a
  las dos vías (`_forzar_roca`), con `PEND_ROCA_DURA 1.25 -> 1.0` (45 grados; nz < 0.7 = pendiente real > 1.02) y transición
  `PEND_ROCA_DURA_ANCHO 0.30` (0.85-1.15). Igual la banda de tierra del tramo de tierra (`_forzar_tierra`, regla B del plan, ligada a
  la pista y no a la rejilla).
- Medido (`mascara_terreno.py --geom geometria_r2.json`, `_rev/_tmp_mascara/r2/qa/terreno_mask_stats.json`): nz < 0.7: **roca 99.75 %,
  verde R+G 0.05 %** (r1: 88.4 / 5.9; objetivo <= 1 %); pendiente > 0.84: roca 92.7 % (84.6), verde 4.3 % (9.0); borde dirt < 8 m
  tierra 93.5 % (88.9); suma = 1 en el 100.00 % (desvío máx 1/255); dominante en tierra matorral 45.1 / hierba seca 21.5 / tierra
  5.5 / roca 27.9 % (r1: 49.1 / 21.2 / 5.2 / 24.6); AO 0.757 igual. Sobre la geometría de r1 (sin B1) el solo cambio de la máscara ya
  da nz < 0.7 roca 99.8 % / verde 0.1 %.
- Sin cambios para `terreno_montana` (sigue importando). `color_ac.ROCA_NZ` (P1, 04_export): `ROCA_UMBRAL_NZ` pasa de 0.792 a
  0.804 (pendiente 0.74): el integrador debe actualizar la línea P1 de `PETICIONES_04_EXPORT.md` ("hoy 0.792" -> 0.804).
  La clave de stats `pend_gt_0_84` queda fija en 0.84 (antes seguía a `PEND_ROCA[1]`) para comparar rondas.

### R2.3 Cosmético 12 (frontera dura dorado/tierra en la cresta del peñón, toma 36)

Con `extras['capas']`, el muestreo de la rejilla de 4 m se desplaza +-`WARP_BORDE_M` = 6 m con ruido de 30 m (`_up(..., warp)`, 0 a
< 90 m de la Loews): las fronteras entre capas ondulan a escala de 10-30 m, nunca por celda. Las reglas ligadas a la pista
(roca dura, banda dirt) se imponen DESPUÉS, así que no se mueven. Coste 0 en KPIs (cifras de R2.2). Sin render de la 36 en esta ronda
(no está en mi set de 4): lo verá el integrador en el A/B BASE.

### R2.4 Verificación con renders (copia `_rev/_tmp_mascara/r2/pista_r2.blend` = SOLO construir_pista: pista, terreno, arcenes, mar, sol)

`capturas_ab.py --camaras renders/ab/_base_antes/camaras.json --solo 49_,51_,07_,01_` en modo normal (7 s) y `--modo-ac` (`ab/despues`,
`ab/despues_ac`, logs `ab_normal.log` / `ab_ac.log`), medidas con `medir_capturas.py` contra `renders/ab/_base_antes/{normal,ac}`
(`ab/medidas.json`, `ab/medidas_ac.json`):
- **Magenta 0.00 %** en las 4 tomas (muestreo 1/16 de píxeles, R > 200 & G < 170 & B > 200). Píxeles del director: `51` (1300,550) =
  rgb(239,234,215) (r1: 255,129,255), (1500,300) = rgb(255,255,250); `07` (400,600) = rgb(186,187,179).
- Modo normal, piloto (49+51): `pct_cesped` 12.53 -> 0.00 %, `pct_verde` 16.23 -> 0.00 %, `bandas_blancas` 0.5 -> 0; aéreas (01+07):
  `pct_cesped` 35.8 -> 0.0 %, `bandas_blancas` 4.5 -> 0, `riqueza` 1.96 -> 2.36. `51`: `pct_roca` 5.9 -> 43.0 % (el desmonte derecho,
  antes "hierba estirada", ahora es roca con estratos), `pared_lisa` 39 -> 83 % (cara de corte lisa de 4 m: F2/afloramientos).
- Modo AC, piloto: `pct_cesped` 1.03 -> 0.00 %, `pct_verde` 4.9 -> 0.0 %; aéreas `pct_verde` 24.3 -> 0.0 %; `07` `pct_roca` 2.2 -> 27.2 %.
- Observación para `materiales` (apoya el MENOR 7 del director): en modo normal la caliza de `ng_caliza_estratos` a pleno sol satura
  a rgb(255,255,250) (`51` (1500,300)): `caliza_ocre` lineal 0.69 x sol 4.6 con exposición 0.12 ya supera 1.0 (la hierba seca, 0.55,
  queda en 243,228,199). La pared vertical debería ir al tono medio `caliza_gris_calido` (0.45 lineal) como pide el director; no es
  cosa de la máscara ni de la exposición (decisión 17: no se toca).
- Limitación honesta: `pista_r2.blend` es la escena de `construir_pista.py` sin `integrar_escena` (sin casas/árboles/rocas de kit),
  suficiente para probar el mecanismo de rutas, la máscara r2 y la luz; las cifras de `riqueza`/`siluetas` no son comparables con la
  base completa. El A/B BASE + paleta completo lo hace el integrador con la regeneración (problema 5 del director).

### R2.5 Env nuevo (solo pruebas): `MASCARA_DIR`

`construir_pista.py` lee `terreno_mask/base/ao.png` de `MASCARA_DIR` si existe (si no, `texturas/`, como siempre): permite probar una
máscara de ensayo sobre copia sin pisar `texturas/` (que escribe `mascara_terreno.py` en el pipeline). El pipeline NO la define.

### R2.6 Determinismo y guarda del nombre QA

`mascara_terreno.py` sobre `geometria_r2.json` tres veces (seed 15) = mismos md5 de `terreno_mask.png` (d1690c2b...), `terreno_base.png`
(92478198...) y `terreno_ao.png` (40ccd29c...): byte a byte. La figura QA se llama igual que la textura (`terreno_mask.png` en
`renders/qa/` vs `texturas/`, plan 3.4): si alguien pasa `--qa` == `--out` (pruebas), ahora la figura sale como `terreno_mask_qa.png`
y no pisa la textura (en el pipeline son carpetas distintas: sin cambio).

## Ronda 3 (04/10/2026, ~22:15) — arreglo a `director_f1_r2.md` problema 8 (MENOR, mascara/terreno): cuadrado gris en 07 AC

Fichero MÍO cambiado: `03_blender/construir_pista.py` (solo el atributo `roca` del TERRENO: `roca_atributo_terreno` + `_canal_a_en_vertices`
dentro del bloque `>>> MATERIAL TERRENO v2`, y las líneas que lo escribían al crear la malla). `mascara_terreno.py` SIN cambios (re-ejecutado:
md5 idénticos a `texturas/`). Pruebas en `_rev/_tmp_mascara/r3/` (`atributo_roca_a_copia.py`, `medir_cuadrado.py`, logs, `ab_cand/`, `ab/`).

### R3.1 Diagnóstico con cifras (qué era el cuadrado)
- NO es un objeto: mi render r2 de la escena SOLO pista (`_rev/_tmp_mascara/r2/ab/despues_ac/07_tierra_subida.png`, sin peanas `CAMARA_` ni
  `VEG_roca`) ya tenía el mismo cuadrado (componente gris #858987 de 190x166 px, solidez convexa 0.995 = cuadrilátero perfecto).
- Rayo de la cámara 07 (loc (-12.0, 294.9, 91.5), tgt (15.2, 454.1, 104.2), lente 30) por el píxel (1176,630) contra `geometria_3d.json`:
  impacto en (16.0, 354.0, 88.0), celda (i 237, j 315), a 65 m (0.049 m/px: el cuadrado de ~170 px = ~8 m). Es el desmonte C1 del 63 % de
  la tierra tallada (bloque 1.1): z 84 -> 92 m entre j 315 y 316; nz por triángulo en j 315: 0.47/0.52, 0.47/0.46, 0.52/0.47 (i 236-238),
  0.51-0.80 en el resto de la pared.
- `capturas_ab --modo-ac` ejecuta `color_ac.separar_roca_terreno` (= `kn5_writer_opt.py` l.753 con `USAR_COLOR_AC`): cara de roca si
  nz < 0.50 o (atributo `roca` > 0.49 y nz < 0.82). El atributo era `G['mascara_roca']` = 0.00 en toda esa pared (desmonte nuevo de F1, no
  macizo): SOLO los 4 triángulos con nz 0.46-0.47 pasaban a `MAT_terreno_roca` = 2 celdas (8 m) de ancho x 8 m de subida = el cuadrado
  (#7F8484 = `ROCA_COLOR` x tile de hierba EN SOMBRA: la pared mira al S y el sol está a azimut 151).
- La máscara por texel ya pintaba de roca toda la pared (canal A = 1.00 en j 315 i 235-240, 0.79 en i 240: roca dura por pendiente real
  > 1.0), por eso en modo normal se ve el montículo de estratos de 28 m. El defecto es la desconexión entre la máscara (verdad del material)
  y lo que lee el writer de hoy (atributo v1 + nz). De las tres hipótesis del director (peana, `VEG_roca`, bloque de celdas nz < 0.5):
  la tercera, pero son 4 triángulos, no un bloque.

### R3.2 Arreglo (`construir_pista.py`): el atributo `roca` del TERRENO = canal A de `terreno_mask.png` en cada vértice
- `roca_atributo_terreno(ob, mascara_roca)`: canal A muestreado bilinealmente en los vértices con la UV planar de mundo (fila 0 del buffer
  de Blender = y mínimo, como el nodo Image; comprobado desde Blender: j 315 i 235-239 = 1.00, i 240 = 0.79, igual que PIL); respaldo
  `G['mascara_roca']` (v1, con aviso) si el PNG no se puede leer. `integrar_escena._poner_celda` sigue subiéndolo en cortes > 2 m (solo sube).
  Nodo `Math.002`/`ROCA_mascara` = max(canal A, atributo con ruido y sin llano, talud): contrato intacto.
- Efecto por cara con el criterio de `color_ac` (numpy sobre `geometria_3d.json`, 203 394 caras de tierra): roca AC hoy 47 465 (23.3 %) ->
  48 332 (23.8 %); coincidencia con el criterio P1 ideal (`A > 0.5 en el centro de la cara o nz < 0.35` = `materiales_roca.roca_caras_mascara`)
  94.98 % -> 96.60 %. Vértices de tierra que cambian de clase (> 0.49): 4.5 %: ENTRAN las paredes de roca dura que solo la máscara tenía
  (0.74 % de los vértices) y SALE el pie de derrubios (`mascara_roca` = 0.5 exacto > `ROCA_ATR` 0.49: 2 301 vértices que la P1-datos de terreno
  y su B2 dicen que NO es roca). En la candidata (322 vértices subidos por integrar conservados): caras `MAT_terreno_roca` 47 644 -> 48 479
  (`atributo_roca_r3.log`); `capturas_ab --modo-ac` 57 406 -> 58 262 caras en 5 objetos.
- Lo que NO hace (y por qué): el borde de la roca en AC sigue siendo por cara (sierra de 4 m = MENOR 4 del director = P1 [W]) y el color/tile
  de `MAT_terreno_roca` sigue siendo el literal `ROCA_COLOR` x tile de hierba seca (P1 / PARCHES_F1_materiales.md 9.1). "Quitarlo" no es
  posible desde mis ficheros: el nz < 0.50 está en `04_export/color_ac.py`.

### R3.3 Verificación (copia de `_rev/escena_candidata.blend` md5 39e8a969 -> `_rev/_tmp_mascara/r3/escena_r3.blend`: SOLO el atributo recalculado; cámaras congeladas `renders/ab/f1_r2/camaras.json`; antes = `renders/ab/f1_r2/despues{,_ac}`; pares `ab_cand/AB_*.png`)
- 07 AC: el cuadrado desaparece; toda la pared sale como roca con el borde de la máscara (`ab_cand/AB_ac_07_tierra_subida.png`): componente
  gris que contiene (1176,630) área 26 838 -> 118 126 px (580x339 px = los 28 m de pared), solidez convexa 0.853 -> 0.795, color medio
  #808584 -> #868A88 (el mismo `ROCA_COLOR` en sombra; el tono lo cambia P1). `medir_capturas` 07 AC: pct_roca 20.7 -> 26.6 %, pared_lisa
  31.0 -> 36.0 % (la roca nueva lleva el tile tintado de hierba del writer de hoy), riqueza 2.02 -> 1.99, bandas_blancas 0, pct_cesped 0.00,
  pct_verde 1.50 = 1.50.
- 49 / 51 / 01 AC: px distintos 0.09 / 1.61 / 1.52 % (max|d| 32-49); medidas iguales a 2 decimales salvo 51 pct_roca 34.23 -> 34.34 y
  pared_lisa 28.7 -> 28.9. 0 regresiones en vistas de piloto (`AB_ac_51`: sin cambio visible).
- Modo normal: 07 7.0 % px distintos pero solo 1.76 % con |d| > 8 (ruido del término del atributo en el borde + fast GI), 49 0.27 %,
  51 2.07 %, 01 1.57 %; medidas idénticas (07 pct_roca 22.58 -> 22.22, riqueza 2.24 = 2.24; 51 pared_lisa 6.7 = 6.7); `AB_07` sin
  diferencia visible: el montículo de estratos ya estaba y sigue.
- `construir_pista.py` entero sobre copia (`BLEND_OUT`/`RENDERS_OUT` a `_rev/_tmp_mascara/r3/`, rc 0): log `terreno: atributo roca = canal A
  de ...terreno_mask.png en 266255 vertices (media 0.118; > 0.49 en el 26.7 % de los vertices de tierra; mascara_roca v1 > 0.49: 27.5 %,
  difieren en el 4.57 %)`, `rutas de imagen tras guardar: 7 absolutas, 0 relativas`; `capturas_ab --modo-ac` sobre `pista_r3.blend`:
  50 152 caras de roca (r2 49 398), componente de 07 solidez 0.995 -> 0.795.
- `mascara_terreno.py` re-ejecutado sobre `geometria_3d.json` (21:33) + `vegetacion_plan.json` a `_rev/_tmp_mascara/r3/tex`: md5 de
  mask / ao / base IDÉNTICOS a `texturas/` (742578b7 / 5dc29d6d / 1a2e967e); nz < 0.7: roca 99.7 %, verde 0.1 %; suma 100.00 %; 6.4 s.

### R3.4 Parches / notas para otros (el pipeline NO cambia)
- Integrador, `PETICIONES_04_EXPORT.md`, línea a AÑADIR bajo P1: "P1 (nota r3, F1 mascara; PARCHES_F1_mascara.md R3.2): desde r3 el atributo
  `roca` del TERRENO es el canal A de `terreno_mask.png` en cada vértice (`construir_pista.roca_atributo_terreno`): con el writer de HOY
  `separar_roca_terreno` ya sigue la máscara (coincidencia con `materiales_roca.roca_caras_mascara` 96.6 %, antes 95.0 %) y el pie de
  derrubios (`mascara_roca` 0.5) deja de ser roca en AC. P1 sigue haciendo falta para el tile/color de `MAT_terreno_roca` y para el borde
  por texel; `ROCA_ATR` 0.49 sigue valiendo."
- Pipeline: nada (el orden preparar -> urbanismo -> mascara -> vegetacion -> mascara --solo-base -> construir_pista garantiza que
  `texturas/terreno_mask.png` existe cuando construir_pista escribe el atributo; si faltara, la red de seguridad lo genera y, si aun así no se
  lee, respaldo v1 con `AVISO`). Prueba en la regeneración: `construir_pista.log` con `terreno: atributo roca = canal A de ...` y en
  `ab.log` del modo AC `roca de terreno {"caras": ~58 k}`; `AB_ac_07` sin cuadrado.
- Terreno (co-propietario del 8): nada que cambiar en la geometría; el desmonte C1 del 63 % da nz 0.46-0.47, justo bajo el 0.50 del writer, y
  con el atributo = máscara ya no importa. Su B2 ("con capas presentes no mezclar `mascara_roca` en el canal A") queda aplicado también en el
  atributo.
- Materiales: 9.1 sigue válido tal cual (cuando P1 abra); mientras tanto `--modo-ac` y el writer ven la MISMA clasificación por el atributo.
- Cosmético 11 (36, frontera dura en la cresta): no tocado en r3 (terreno r2 ya puso ruido de 15 m en el canal B de las capas y la máscara
  añade el warp de 6 m; sin render de 36 en mi set): lo juzga el integrador en el A/B BASE.

## Ronda 4 (04/10/2026, ~23:45-00:40) — ACOTACIONES_COORDINADOR_F1.md 4 (mitigación interina de la roca por cara, modo AC) y cosmético 10 (36)

Ficheros MÍOS cambiados: `03_blender/mascara_terreno.py` (UMBRALES + ruido por canal en la vía de capas) y `03_blender/construir_pista.py`
(bloque `>>> MATERIAL TERRENO v2`: `roca_zonas_nz`, `subdividir_banda_terreno`, `estimar_banda_terreno`, `sincronizar_banda_terreno`,
`_canal_a_en_xy` y utilidades; llamada a las zonas tras el atributo + líneas de log; env `TERRENO_BANDA_2M=1` solo para pruebas sobre copia).
Pruebas en `_rev/_tmp_mascara/r4/` (`analisis_dientes.py` + `dientes_*.json`, `mascara_r4.log`, `tex/`, `qa/`, `construir_pista_r4.log`,
`pista_r4.blend`, `aplicar_r4_a_copia.py` + `aplicar_r4.log`, `escena_r4.blend` (copia de la candidata r3 md5 d7e23a55 + r4), `ab/`
(antes = `renders/ab/f1_r3/despues{,_ac}` de 51/07/36/56, después = r4; `AB_*`, `AB_ac_*`, `medidas{,_ac}.json`), `banda_terreno_2m.py`).
`04_export`, `porto_corsa.blend`, `escena_candidata.blend`, `escena_rev.blend`, `texturas/` y `renders/qa/` del proyecto NO se han tocado.

### R4.1 Qué hace cada mitigación y dónde vive (umbrales en UN sitio: `mascara_terreno.UMBRALES`)

| # | Acotación | Dónde | Cómo |
|---|---|---|---|
| a | ruido del atributo roca 0.08 -> 0.20 | `mascara_terreno.py` `UMBRALES['ROCA_ATR_RUIDO'] = 0.20` (vivía aquí, no en terreno_montana: sin coordinación) | vía de capas (la del pipeline): canal A = capa + `amp · n_b` (10 m) con `amp = 0.08 + 0.12 · 4c(1-c)`: 0.20 en la FRONTERA (c = 0.5) y 0.08 en roca o hierba puras (no motea las praderas). Vía de reglas: `ROCA_ATR ± 0.20` (dormida: hay `extras.capas`). |
| a' | cosmético 10 (36): ruido 10-30 m en el canal B junto a `_corte` | `UMBRALES['TIERRA_RUIDO'] = 0.20`, canal B con ruido propio `0.5(n_b + n_d)` (10 + 30 m) en su frontera | Nota honesta: la "ladera partida en dos tonos" de 36 en modo AC es roca/hierba POR CARA (anillo W del peñón a 160-360 m: capa roca media 0.46, A > 0.5 en el 45-47 % de las celdas, pendiente 0.78-1.0 = justo en el umbral 0.68-0.80), no el canal B (0.05 ahí): lo que la rompe es el ruido del canal A (a). |
| b | subdivisión a 2 m del TERRENO en la banda junto a la pista | `construir_pista.subdividir_banda_terreno(ob)`; `UMBRALES['BANDA_2M_M'] = 25.0` | 4 triángulos por triángulo (puntos medios SOBRE el plano del padre: la superficie no cambia, la clasificación por cara de AC pasa a 2 m); los nx·ny vértices de la rejilla conservan su índice y los nuevos van al final con `banda_p0/p1` (INT, padres; -1 en la rejilla); material por cara heredado; atributo `roca` en los medios = max(media de los padres, canal A en el punto medio); UV planar nueva; smooth. Se aplica al FINAL del pipeline (parche A8), nunca en construir_pista: hasta entonces el TERRENO sigue siendo la rejilla nx·ny que integrar/asentar/revisar_* editan y leen por `j·nx+i` (plan 15.7). 25 m y no 20: la cresta del desmonte de la tierra tallada está a 4.5-25 m del borde (ahí está la sierra de 51); medido 20 m +38 258 / 22 m +41 109 / 24 m +43 900 / **25 m +45 281** / 28 m +49 339 / 30 m +52 110 vértices (tope +40-50 k del coordinador). |
| c | nz < 0.62 en la cima de 56 y laderas a < 150 m de 51/07 | `construir_pista.roca_zonas_nz(ob)`; `UMBRALES['ROCA_NZ_ZONA'] = 0.62`, `ROCA_ZONA_MIN_CARAS 6`, `ROCA_ZONA_FUNDIDO_M 12`, `ROCA_NZ_ZONAS` = loc de las 3 cámaras congeladas de `renders/ab/_base_antes/camaras.json` (56 (47.97, 567.54), 51 (15.02, 426.26), 07 (-12.02, 294.89); r 150 m) | Sobre el ATRIBUTO `roca` (lo que lee `color_ac.separar_roca_terreno`: cara de roca si nz < 0.50 o (media > 0.49 y nz < 0.82); criterio copiado, 04_export intacto): dentro de las zonas el objetivo = roca de hoy ∧ nz < 0.62; limpieza de componentes de roca y huecos < 6 caras (2 pasadas, solo componentes enteramente en zona; las caras nz < 0.50 no se pueden quitar: son roca por talud pase lo que pase); el atributo pasa a {1 si todas las caras incidentes son roca, 0.5 si mezcla (las tiras de 1 cara de ancho = el desmonte se conservan: 0.5 > 0.49), 0} con corrección a 0.45 de las caras de hierba con 3 vértices de frontera, fundido con el canal A en un anillo de 12 m. Fuera de las zonas el atributo sigue = canal A (R3.2). La MÁSCARA por texel (modo normal, P1) no cambia. El umbral general de terreno (`umbrales_roca()['nz']` 0.804) se imprime como referencia; el 0.62 es el de la acotación. |

### R4.2 Cifras (python del sistema `analisis_dientes.py` sobre geometria_3d.json + máscara; Blender sobre COPIA de la candidata r3)

"Diente" = cara de roca AC con <= 1 vecina de roca (triángulo aislado o colgando); "hueco" = cara de hierba con 3 vecinas de roca.
- Máscara r3 (ruido 0.08) -> r4 (0.20): área roca 27.81 -> 27.49 % de la tierra, tierra 4.76 -> 5.15, matorral 45.87 -> 45.82, seca 21.55 -> 21.53;
  nz < 0.7: roca 99.75 -> 99.77 %, verde 0.08 -> 0.11 % (obj <= 1); pend > 0.84: roca 92.94 -> 92.93 %; borde dirt 91.7 -> 91.73; suma 100.00 %;
  AO 0.757 (=); aristas de frontera roca/hierba por cara (toda la tierra, 4 m) 7 924 -> 8 027 (+1.3 %: la frontera serpentea), dientes 1 179 -> 1 226.
  Es decir: el ruido 0.20 rompe las rectas pero NO quita dientes; lo que los quita es (c), y lo que los encoge es (b).
- Candidata r3 (copia) + r4 (`aplicar_r4.log`): atributo = canal A r4 (266 255 vértices; > 0.49 en el 27.10 % de la tierra, r3 27.03; difieren 0.44 %;
  131 538 subidas de integrar conservadas). Zonas (rejilla 4 m): caras de roca AC / dientes / huecos: 56: 3 205 -> 903 / 138 -> 67 (20 por talud
  nz < 0.50 + 30 en el anillo) / 7 -> 0; 51: 1 083 -> 512 / 98 -> 32 (8 + 4) / 6 -> 0; 07: 813 -> 260 / 84 -> 34 (17 + 7) / 5 -> 0; global 49 105 -> 46 235
  caras (-5.8 %), vértices que cambian de clase 1 754 (0.66 %). Banda 25 m: 14 324 celdas, 28 648 caras -> 114 592, **vértices 266 255 -> 311 536
  (+45 281)**, tris 530 448 -> 616 392 (+85 944 = +0.09 M sobre los 5.26 M: presupuesto 6.0 M intacto), canal A en los medios sí, 1.6 s. Zonas tras la
  banda (2 m): 56: 3 306 -> 1 948 / 194 -> 110 (25 talud + 31 anillo) ; 51: 2 827 -> 1 624 / 195 -> 70 (16 + 4); 07: 1 304 -> 750 / 109 -> 48 (20 + 8).
  Segunda pasada (idempotencia): 32 vértices cambian de clase, dientes 1 514 -> 1 511. 19 s en total.
- `construir_pista.py` entero sobre copia (`construir_pista_r4.log`, rc 0, `TERRENO_BANDA_2M=1`): `terreno: atributo roca = canal A ... en 266255 vertices
  (media 0.118; > 0.49 en el 26.7 %)`, `terreno: zonas nz < 0.62 (... umbral de terreno_montana nz 0.804) en 9468 vertices: caras de roca AC 48915 -> 45713,
  dientes 1288 -> 1173, huecos 220 -> 206` + 1 línea por zona, `terreno: atributo roca tras las zonas: 266255 vertices, media 0.110, > 0.49 en el 25.0 %`,
  `terreno: banda ... celdas -> +N vertices (266255 -> ...)`, `rutas de imagen tras guardar: 7 absolutas, 0 relativas`. Nodo `Math.002`/`ROCA_mascara`
  y custom props `ac_shader ksMultilayer_fresnel_nm`, `ac_samplers` (7), `ac_props` (15), `ac_tex_max`, `ac_raw 1`, `ac_ao` intactos (línea `CONTRATO` de
  `aplicar_r4.log`); `aplicar_texturas`/`mejorar_materiales` no tocan el TERRENO (marcador TEXTURIZADO; `_centro_circuito` usa el bound_box).

### R4.3 Renders (copia de la candidata r3 + r4 = `escena_r4.blend`; cámaras congeladas `renders/ab/_base_antes/camaras.json`; antes = `renders/ab/f1_r3/despues{,_ac}`)

`_rev/_tmp_mascara/r4/ab/{AB_ac_*,AB_*,hoja_ab_*}.png`, `medidas_ac.json`, `medidas.json`. Modo AC (el que juzga):
- **56**: la fila de 6 dientes de roca de la derecha (recorte (1200-1600, 330-630)) DESAPARECE: la loma derecha lleva roca solo en su parte alta,
  con contorno continuo; el cono central queda en hierba seca con una banda de roca solo en la cresta (nz < 0.62) y la arista del espolón
  izquierdo. pct_roca 43.5 -> 40.6 (la métrica cuenta también la tierra del primer plano), riqueza 2.195 -> 2.187, pct_cesped 0, bandas 0;
  px distintos 19.1 % (|d| > 8: 8.8 %). La arista recta del cono (regresión de forma del director) es del relieve (terreno: cúpula), no de la máscara.
- **51**: la pared derecha sigue siendo roca (desmonte 63 grados, nz < 0.50) y la ladera del 85 % de encima pasa a hierba seca (nz 0.76 >= 0.62):
  la frontera es la cresta geométrica del desmonte y, dentro de la banda de 25 m, a 2 m; en la ladera izquierda los bloques de roca bajan de
  tamaño y los dientes sueltos se van. pct_roca 51.9 -> 48.2, pared_lisa 17.7 -> 19.3, riqueza 2.46 -> 2.39, pct_cesped 0, pct_verde 0.07 (=),
  siluetas 1 (=); px distintos 24.0 % (|d| > 8: 7.5 %). Las lomas lejanas con parches de roca "rayados" (tile 3 m) son P1/materiales (10.5).
- **07**: roca 36.9 -> 28.2 % (los bloques de pared cercanos, nz < 0.50, se quedan; los parches aislados de la media distancia a 35-52 grados
  se van), pared_lisa 10.9 -> 14.9 (los bloques que quedan son los lisos), riqueza 2.28 -> 2.17, bandas 0; px distintos 37.8 % (|d| > 8: 17.4 %).
- **36** (fuera de las zonas; solo ruido 0.20 + banda junto a la calzada): la frontera de dos tonos del peñón serpentea en vez de ser una
  recta en sierra, pero sigue siendo por cara de 4 m (pct_roca 21.9 -> 21.8, riqueza 2.14 -> 2.15; px distintos 9.8 %, |d| > 8: 0.4 %):
  la quita de verdad P1 (`roca_caras_mascara`), no esta mitigación. Cosmético 10 queda "atenuado", no cerrado.
Modo normal (máscara por texel, sin cambios en las zonas): 51 pct_roca 18.65 -> 19.07, riqueza 2.72 -> 2.73; 56 17.07 -> 16.66; 07 23.11 -> 23.79;
36 12.0 -> 12.03; pct_cesped 0 en las 4; px con |d| > 8: 5-11 % (ruido 0.20 en las fronteras + banda; sin cambio de aspecto: la retícula de
`NG_caliza_estratos` y los estratos que cruzan la arista son 10.3/10.4 de materiales). 0 regresiones en 51 (piloto) en los dos modos.
Limitación honesta: en las zonas el atributo ya NO es el canal A (contrato R3.2 roto a propósito: 1 754 vértices cambian de clase, 0.66 %) y el
modo normal sigue enseñando roca a 35-52 grados donde el AC enseña hierba seca; el KPI "atributo roca = canal A" pasa a leerse como "= canal A
fuera de las 3 zonas" (la línea `terreno: zonas nz < 0.62 ...` del log lo cuantifica). Cuando P1 lea la máscara por texel, `roca_zonas_nz`
sobra (una constante: `ROCA_NZ_ZONAS = {}` la apaga).

### R4.4 Parches para el integrador (`_rev/*`, pipeline) — los únicos que hacen falta

**A8. Paso FINAL de Blender en `_rev/pipeline_escena.sh` (obligatorio para que la banda de 2 m llegue a la candidata)**. Copiar el script:
```bash
cp 03_blender/_rev/_tmp_mascara/r4/banda_terreno_2m.py 03_blender/_rev/banda_terreno_2m.py
```
y en `pipeline_escena.sh`, tras `echo "plot exit $?"` (l.119) y ANTES de `copiar_candidata || exit 1` (l.120):
```bash
# F1 r4 (ACOTACIONES 4; PARCHES_F1_mascara.md R4.4 A8): ULTIMO paso de Blender: TERRENO a 2 m en la banda de 25 m junto al asfalto
# (+45 k vertices, +86 k tris) y zonas nz < 0.62 sin dientes sobre la malla final. Va el ultimo porque a partir de aqui el TERRENO ya
# no tiene nx*ny vertices: integrar/asentar/revisar_*/nada_en_pista deben haber terminado (los nx*ny primeros conservan su indice).
bash "$COLA" --python _rev/banda_terreno_2m.py > "$LOGS/banda_terreno_2m.log" 2>&1 || { echo "FALLO banda_terreno_2m"; tail -20 "$LOGS/banda_terreno_2m.log"; exit 1; }
grep "BANDA_2M" "$LOGS/banda_terreno_2m.log" | cut -c1-300
```
y en `copiar_candidata()` (junto a `medir_relieve.json`, l.46): `[ -f renders/qa/banda_terreno_2m.json ] && cp renders/qa/banda_terreno_2m.json "$REV/banda_terreno_2m_candidata.json"`.
Prueba: `banda_terreno_2m.log` con `BANDA_2M: banda 25 m | celdas 14324 | vertices 266255 -> 311536 (+45281) | tris 530448 -> 616392 | canal A en los
medios True` y `BANDA_2M zonas nz < 0.62: caras de roca AC ... | dientes ... -> ...`; `OK banda_terreno_2m -> porto_corsa.blend`; `comprobar_rutas_blend.py`
sigue dando 0 relativas (el script guarda con `relative_remap=False`); en el A/B `ab.log` del modo AC `roca de terreno {"caras": ~63 k}` (r3: 58 k; son
caras de 2 m). Idempotente: una segunda ejecución imprime `ya subdividido` y no guarda. Sin este paso la candidata sale igual que r3 + (a) + (c) en la
rejilla de 4 m (construir_pista ya aplica las zonas): la banda es la única parte que depende del integrador. ~25 s de cola (abrir + guardar 50 MB).
Añadir también a `grep -E "MAT_terreno v2|AVISO: faltan PNG|atributo roca"` de la l.114 el patrón `|zonas nz <|banda de` para que el pipeline eche
las dos líneas nuevas de `construir_pista.log`.

**A9 (opcional, robustez; propietario integrador)**: los inspectores que leen la cota de la malla exigen `len(vertices) == nx*ny`
(`asentar_objetos.py` l.208 y l.434, `revisar_flotantes.py` l.20, `revisar_invasores.py` l.21, `revisar_urbanismo.py` l.142, `revisar_coches.py`
l.16). Dentro del pipeline no les afecta (A8 va después), pero si alguien los relanza a mano sobre la candidata YA subdividida caen al `z` del
JSON (sin explanadas). Cambio exacto (6 sitios): `== T['nx'] * T['ny']` -> `>= T['nx'] * T['ny']` y `T['z'] = _co[2::3]` -> `T['z'] = _co[2::3][:T['nx'] * T['ny']]`
(los nx*ny primeros vértices son la rejilla; en asentar l.434 TER_OK sigue valiendo porque solo mueve nodos `j*nx+i`; si asentar llegara a mover
nodos de una malla subdividida, llamar después a `construir_pista.sincronizar_banda_terreno(TER_OB)` — hoy no hace falta).

**A10. `PETICIONES_04_EXPORT.md`, línea a AÑADIR bajo P1** (datos): "P1 (nota r4, F1 mascara; PARCHES_F1_mascara.md R4.1): el atributo `roca` del
TERRENO sigue siendo el canal A de `terreno_mask.png` salvo en 3 zonas (cima de 56, < 150 m de 51 y 07: `mascara_terreno.UMBRALES['ROCA_NZ_ZONAS']`)
donde es la clasificación por cara limpiada con nz < 0.62 (`construir_pista.roca_zonas_nz`); y el TERRENO llega al writer con nx*ny + 45 281 vértices
(banda de 25 m a 2 m: `1GRASS_terreno` +85 944 tris, presupuesto 5.26 -> ~5.35 M <= 6.0). Con `roca_caras_mascara` (P1) las zonas sobran: poner
`ROCA_NZ_ZONAS = {}`; la banda se queda (también mejora el borde por texel junto al coche)."

**Nada para `terreno`** (la constante del ruido vivía en `mascara_terreno`, no en `terreno_montana`; `umbrales_roca()` sigue importando de aquí: `nz` 0.804
sin cambio) **ni para `materiales`** (36 y el tile rayado de las lomas son 10.3-10.5/P1, ya pedidos). Presupuesto de tris: +85 944 (+1.6 %); texturas 0.

### R4.5 Pendiente honesto
- La sierra por cara NO desaparece fuera de las zonas (36, 50, 21, 01) ni en la cresta del desmonte más allá de la banda: es P1 [W]; esto es la
  mitigación interina pedida y nada más. Dentro de las zonas quedan 29-67 "dientes" por zona (4 m) de los que 8-20 son caras nz < 0.50 (roca por
  talud, intocables desde el atributo) y 4-30 están en el anillo de fundido de 12 m.
- La banda de 2 m solo entra en la candidata si el integrador aplica A8 (1 script + 3 líneas); sin A8 la entrega vale igual para (a) y (c).
- Modo normal y modo AC difieren en las zonas (roca a 35-52 grados solo en el texel): decisión consciente; se revierte con `ROCA_NZ_ZONAS = {}`.
- No he lanzado el pipeline ni tocado `porto_corsa.blend`/candidata; el A/B oficial de r4 lo hace el integrador tras regenerar.
