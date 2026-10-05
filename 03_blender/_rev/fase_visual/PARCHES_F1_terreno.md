# PARCHES F1 — propietario `terreno` (bloque 1 puntos 1.1, 1.2, 1.6 + bloque 2.2; 04/10/2026, dos sesiones)

Ficheros MIOS (editados): `03_blender/terreno_montana.py` (unico propietario), `03_blender/_rev/medir_relieve.py` (NUEVO),
`03_blender/assets/_geom_snapshot_terreno.json` (= `geometria_3d.json` del 04/10 12:57, byte a byte: entrada del test aislado).
Pruebas y sondas en `03_blender/_rev/_tmp_terreno/` (`qa_v13..v23/`, `geom_v*.json`, `preparar_v*.log`, `medir_v*.json`,
`urbanismo_v21/v23.json|.log`, `diag_tierra.py`, `perfiles_tierra.py`, `sonda*.py`). Blender NO se ha lanzado (todo es python del
sistema: `preparar_geometria.py` 14 s, `urbanismo.py` 60 s, `medir_relieve.py` 4 s). `04_export` sin tocar.
Las lineas citadas (l.) son las de los ficheros tal como estan el 04/10 por la noche: comprobar con `grep -n` antes de editar.

## 0. Que hace ahora `terreno_montana.construir()` (resumen para el integrador) y cifras

Todo con comentarios `F1 (bloque X)` en el codigo y constantes `TIERRA_*`, `BERMA_TERRAZA*`, `BANCO_*`, `COSTILLA_TOPE`,
`ROCA_*`, `CAPAS_*` en la cabecera (l.218-265):
- **1.1 Tierra tallada (s 1540-2440; 1430-1540 son las terrazas de pueblo_alto)**: por muestra se elige el LADO ALTO (natural
  mas alto a 60-80 m; si empata, interior de la curva). Lado alto: desmonte C1 a `TIERRA_PEND_INT` 2.0 (63 grados) y ladera
  minima al 85 % hasta +14 m; lado bajo: berma llana de 7.5 m (> w/2 + 6.75 del cierre_ac), terraplen 1.3 y caida minima al
  55 % hasta -16 m. BANCO DE HORQUILLA (sesion 2): donde una rama plegada (rumbo opuesto, > 40 m por la pista y < 80 % en
  recta, a < 45 m) esta >= 4 m mas alta, la isla sube de la rama baja a la alta (C26 s 2380-2430: +10..+12 m a 25 m del
  borde). Todo acotado por techo/suelo de TODOS los ramales: el corredor de la pista y el de las otras ramas no cambian
  (`dz < 4.5 m del asfalto` = 0.10 m, por la berma 6 -> 7.5 m). Peso del tiron `TIERRA_PESO_TIRON` 0.5 (es relativo: solo
  cambia en los extremos del tramo). NO se toca `MAXG`.
- **1.2 Berma + bancales + costillas**: berma de 15-25 m (ruido 60 m, pendiente 25 %) entre el patio de la ultima terraza y
  el arranque de la cara (`techo_tras_terraza(..., berma=)`), `BANCO_H` 11.5, `BANCO_A` 1.65 (= 0.9*H/2pi: con 2.5 la cara se
  invertia y abria fosos), bancales tambien en el espolon del coche (`BANCOS_EN_COCHE = True`: probado, `coche_120m_*` no
  baja: min 27 / max 110 / >= 90 m en 17 %, fuera de terrazas 57 %, igual que antes), costillas hasta 4 m en caras > 20 m.
- **2.2 Roca por pendiente**: umbral natural 1.0 -> `mascara_terreno.UMBRALES['PEND_ROCA']` (0.70-0.84 con ruido de 30 m;
  importado: UN solo sitio, PARCHES_F1_mascara.md A2 APLICADO), suavizado 10 m, apertura 3x3, minimo 12 celdas, banda PIE DE
  DERRUBIOS 0.5 a 6-10 m bajo cada afloramiento (5474 celdas). Exporta `umbrales_roca()` y `ROCA_UMBRAL_NZ` (0.792) para
  `color_ac` (P1) y los revisores.
- **1.6 Capas**: `res['extras']['capas']` = {matorral, hierba_seca, tierra, roca}, nx*ny floats 0..1, suma 1 por celda
  (pendiente, z, distancia al mar y a la pista, acantilado, desmonte, sectores de terrazas, cumbres; bordes con ruido de 20 m).
  `mascara_roca` se mantiene. `qa_figuras` escribe `terreno_capas.png`. Media en tierra: matorral 49 %, hierba seca 20 %,
  tierra 8 %, roca 23 %.
- **Checks nuevos** en `checks`: `pared_y_caida_25m_pct`, `pared_y_caida_50m_pct`, `pct_pista_con_pared_roca_tierra`,
  `caida_25m_pct_tierra`, `celdas_35_roca_pct`, `celdas_35_pct_tierra`, `roca_pie_derrubios_celdas`, `capas_media_pct`,
  `tierra_tallada_*`, `costillas_celdas_gt_2m`, `erosion_corredor_dz_max` (= 0.000: la erosion es F4). Linea de QA
  `F1 tierra tallada (s 1430-2440): ...` en el log de preparar_geometria.
- **`_rev/medir_relieve.py`** (numpy sobre `geometria_3d.json`, independiente de construir): KPIs de la tierra, pared de roca,
  terreno a 120 m tras cada sector, orilla z > 10 (informativo), roca > 35 grados, capas, invariantes (invaden, hierba_asfalto
  proxy, loews_ref_dz_max; el foso es un proxy 1D mas severo que la QA de construir, que sigue siendo la referencia de la
  puerta: solo avisa) y, con `--antes`, dz por bandas (corredor, McLaren, Loews, por 200 m) y tabla antes/despues.
  `python 03_blender/_rev/medir_relieve.py [--geom g.json] [--antes g0.json] [--out medidas.json] [--tramo 1430 2440] [--estricto]`.

| KPI (plan secc. 5 / 16) | antes (12:57) | entregado (v23) | objetivo |
|---|---|---|---|
| pared Y caida a 25 m en tierra (s 1430-2440) | 4.5 % | **25.5 %** | >= 40 % |
| idem a 50 m | 22.1 % | 27.7 % | >= 60 % |
| pct_pista_con_pared_roca en tierra (toda la pista) | 22.7 % (29.7) | **45.1 %** (35.3) | >= 50 % |
| celdas de tierra > 35 grados con roca | 21.2 % | **73.3 %** (> 40 grados: 82.9 %) | >= 80 % (81.4 % con B1) |
| terreno a 120 m tras pueblo_subida_ladera (media) | 83.0 m | 78.1 m | >= 110 (es del macizo, F2) |
| orilla z > 10 m en los tramos del plan | 0 / 0 / 0 % | igual (F2) | >= 25 % (F2) |
| celdas_invaden_pista / hierba_asfalto / loews_ref_dz_max | 0 / 0 / 0.000 | 0 / 0 / 0.000 | 0 / 0 / 0.000 |
| fosos > 1.5 m tras la ultima terraza (muestras) | 0 | 0 (max 1.40 casino_mar, como antes) | 0 |
| costuras max / celdas > 0.6 | 2.03 m / 127 | 2.03 m / 127 (identico) | no peor que la base + 0.05 |
| coche_120m_pct_ge_90 (y fuera de terrazas) | 17 % (57 %) | 17 % (57 %) | no baja |
| urbanismo.py con la geometria nueva | 193 casas, 0 fallos | 193 casas, 0 fallos | >= 190, 0 |
| dz McLaren (huella / < 10 m / 10-20 m / 20-25 m) | - | 0.00 / 0.00 / 0.09 / 0.68 m (a 22.6 m, franja del margen) | 0.000 a < 25 m |

**Por que no llega al 40 %** (medido por tramos de 100 m con `medir_relieve`, `diag_tierra.py`): s 1430-1525 son las terrazas
de pueblo_alto (10 % del tramo: ni pared ni caida posibles); s 1760-1860 (cima) el natural sube por los DOS lados (corte en
trinchera: pared si, caida no); s 2020-2060 y 2230-2290 son crestas (cae por los dos lados); s 1870-1960 el interior del lazo es
una meseta tirada a la rasante (tiron sigma 100 m): pared de 3-7 m, no de 8; s 1600-1660 collado llano. Lo que lo subiria de
verdad es el relieve NATURAL del lazo (macizo/espolon del lazo = landform, bloque 1.3 de F2) o aceptar lomos artificiales de
8 m sobre terreno llano (probado con `TIERRA_LOMO_EXTRA` = 3 m: pared en algun lado 39 -> 44 % pero el lomo apaga la vaguada
vecina, PyC 21.7 -> 20.9 % y un foso de 1.68 m tras pueblo_alto_ladera: se deja a 0). Mejor dejarlo asi y volver con el macizo.

## A. Parches a `preparar_geometria.py` (los aplica el integrador; NO los he aplicado)

### A1. `extras['capas']` + umbrales + checks F1 en `geometria_3d.json` (bloque 1.6; contrato de PARCHES_F1_mascara.md 0)

Tras la l.510 (`_mascara_roca = _res_t['extras']['mascara_roca']`) insertar:

```python
# fase visual F1 (bloque 1.6, propietario terreno): capas de la mascara por texel (R matorral, G hierba seca, B tierra,
# A roca; nx*ny floats 0..1, suma 1 por celda) para mascara_terreno.py, + umbrales de roca (un solo sitio) y KPIs del
# relieve. 2 decimales: +5.3 MB en geometria_3d.json (4.1 -> ~9.5 MB); mascara_terreno los lee con np.array.
_capas = _res_t['extras'].get('capas') or {}
_checks_t = _res_t['extras'].get('checks') or {}
_extras_out = {
    'capas': {k: [round(float(v), 2) for v in np.asarray(arr).ravel()] for k, arr in _capas.items()},
    'umbrales_roca': _res_t['extras'].get('umbrales_roca'),
    'checks_f1': {k: _checks_t.get(k) for k in ('pared_y_caida_25m_pct', 'pared_y_caida_50m_pct', 'pct_pista_con_pared_roca',
                                                 'pct_pista_con_pared_roca_tierra', 'celdas_35_roca_pct', 'capas_media_pct',
                                                 'roca_pie_derrubios_celdas', 'erosion_corredor_dz_max', 'coche_120m_pct_ge_90')},
}
```

y en el dict `out` (l.512-541), tras la clave `'mascara_roca': [...]`, la linea:

```python
    'extras': _extras_out,     # F1: capas de la mascara (bloque 1.6), umbrales de roca y KPIs (ver PARCHES_F1_terreno.md A1)
```

Prueba: `python preparar_geometria.py` (o con `GEOM_OUT`/`QA_DIR` a una carpeta de prueba) -> `geometria_3d.json` con
`extras.capas.{matorral,hierba_seca,tierra,roca}` de 266 255 valores cada una; `python 03_blender/_rev/medir_relieve.py` imprime
`capas (media % en tierra): {'matorral': 49.0, 'hierba_seca': 20.1, 'tierra': 8.2, 'roca': 22.6} | suma = 1 en 100.0 % de las
celdas`; `python mascara_terreno.py` toma las capas en vez de sus reglas (su log lo dice) y `renders/qa/terreno_mask.png`
coincide con `renders/qa/terreno_capas.png` salvo el ruido de borde. `urbanismo.py`, `construir_pista.py` e inspectores no leen
`extras`: nada mas cambia. Sin este parche todo funciona igual que hoy (mascara_terreno usa sus reglas).

### A2. Controles de rasante <= 9-10 % a +-40 m de los apex C18-19 / C26 (plan 0.7 y 5.1) — [U] NO APLICAR SIN DECISION

El plan lo pide (fisica: borde interior colapsado en s 2365 al 16.5 %), pero DECISIONES_USUARIO dice "la cuesta del tramo de
tierra NO se baja" y el tope local BAJA LA CIMA: medido sobre el perfil actual, tope 9.5 % en +-40 m de los tres apex ->
cima 120.7 -> 117.0 m, dz max 4.15 m en s 1874, 163 muestras movidas en s 1824-2398 (con 10 %: 117.6 m, 3.6 m). Toca fisica
validada (zip v1.1: `revisar_fisica_ac`, `cierre_ac.chaflan_horquilla`, `HORQ_TRAMOS`) y las cotas de `pacas_tierra`, camaras
y senderos CIMA. Lo dejo escrito para cuando el usuario/el equipo de fisica lo pidan. En `preparar_geometria.py`, tras el bucle
de `MAXG` (l.386-392) y ANTES de `Z = smooth_closed(Z, 15)` (l.393):

```python
# fase visual F1 (bloque 1.1, plan 0.7): rasante <= APEX_G a +-40 m de los apex de las horquillas C18-19 (cima) y C26.
# Solo actua en esas ventanas; el resto sigue a MAXG. [U] baja la cima ~3.7 m (ver PARCHES_F1_terreno.md A2).
APEX_G = 0.095 * paso
_G = np.full(N, MAXG)
for _sa in (s_cima, s_cima + 90.0, curvas[26]['s_idx'] * paso):
    _G[int((_sa - 40.0) / paso):int((_sa + 40.0) / paso) + 1] = APEX_G
for _ in range(4):
    for i in range(1, N):
        Z[i] = min(Z[i], Z[i - 1] + _G[i])
    for i in range(N - 2, -1, -1):
        Z[i] = min(Z[i], Z[i + 1] + _G[i + 1])
    Z[0] = min(Z[0], Z[-1] + MAXG)
```

Prueba: la linea `alturas: min .. max .. | pendiente max ..` del log (max sigue en 16.5 % fuera de las ventanas);
`python 03_blender/_rev/medir_relieve.py --antes <geometria anterior>` (dz por 200 m en s 1800-2400 y KPIs de la tierra, que
cambian poco: el terreno lateral sigue a la rasante); `urbanismo.py` (no hay sectores en 1525-2620); y, cuando abra
`04_export`, `revisar_fisica_ac` en s 2365. `terreno_montana.py` NO depende de este parche.

### A3. (opcional, recomendado) `_rev/pipeline_escena.sh`: medir el relieve tras `preparar_geometria`

Tras `echo "preparar_geometria ok"` (l.52):

```bash
# fase visual F1 (bloque 1): KPIs del relieve antes/despues (informativo: no tumba el pipeline). 'antes' = la geometria de la
# escena congelada (_rev/geometria_rev.json) o, si no existe, la candidata anterior.
ANTES="$REV/geometria_rev.json"; [ -f "$ANTES" ] || ANTES="$REV/geometria_candidata.json"
python _rev/medir_relieve.py --antes "$ANTES" --out renders/qa/medir_relieve.json > "$LOGS/medir_relieve.log" 2>&1
grep -E "KPI antes|invariantes" "$LOGS/medir_relieve.log" | cut -c1-300
```

y en `copiar_candidata()` (opcional) `&& cp renders/qa/medir_relieve.json "$REV/medir_relieve_candidata.json"`.
`puerta_calidad.py` no cambia (sus criterios de terreno se cumplen: fosos 0, costuras identicas, loews 0.000, invaden 0).

## B. Para el propietario `mascara` (`mascara_terreno.py`; acordado por este fichero y PARCHES_F1_mascara.md 0/A2)

### B1. Umbrales compartidos: aplicado el A2 de su entrega, y propuesta de valores para el KPI del plan

`terreno_montana.py` l.241-257 hace `from mascara_terreno import UMBRALES` (con defectos iguales si no se puede importar) y
deriva `ROCA_UMBRAL_PEND` = media de `PEND_ROCA`, `ROCA_UMBRAL_RUIDO` = semirrango, `ROCA_SIGMA_M` = `PEND_SUAVIZADO_M`,
`ROCA_MIN_CELDAS`, `ROCA_PIE_M` = `PIE_M`, `CAPAS_LLANO_PEND/HIERBA_D_PISTA/HIERBA_Z/DIRT_BORDE_M` = `LLANO_PEND/LLANO_DIST_M/
LLANO_Z/DIRT_BORDE_M`. `umbrales_roca()` devuelve todo (con `origen`) y `ROCA_UMBRAL_NZ` = 1/sqrt(1+pend^2) para `color_ac`.
Con los valores de hoy (0.70-0.84, sigma 10 m) el KPI "celdas de tierra > 35 grados con roca" queda en **73.3 %** (> 40
grados: 82.9 %); con `'PEND_ROCA': (0.68, 0.80)` y `'PEND_SUAVIZADO_M': 8.0` (l.54 y l.56 de `mascara_terreno.py`) sube a
**81.4 %** (> 40 grados: 86.1 %; medido v13-v16) y `roca_pct_tierra` 24.3 -> 27.5 %. Es su fichero: lo decide el propietario
`mascara` (o el integrador); `terreno_montana` lo seguira solo con re-ejecutar. Prueba: `python preparar_geometria.py` a un
QA_DIR y `python _rev/medir_relieve.py --geom <qa>/geometria_3d.json` -> linea `roca: ... con roca XX %`.

### B2. Pie de derrubios y capas

En `mascara_roca` el pie vale `ROCA_PIE_VALOR` = 0.5 (plan 2.2) y en `capas` es 'tierra' 0.85. Como `mascara_terreno` lee
`mascara_roca > ROCA_ATR +- 0.08`, SIN el parche A1 la mitad de las celdas del pie saldrian como roca en el canal A; CON A1
(`extras['capas']`) la mascara usa las capas y el pie es tierra. Recomendacion: con capas presentes, no mezclar `mascara_roca`
en el canal A (o umbral 0.6 para el pie). Nada que cambiar en `terreno_montana`.

## C. `PETICIONES_04_EXPORT.md`: linea que debe ANADIR el integrador (P1, datos)

- **P1 (datos, F1 terreno)** `color_ac.ROCA_NZ` = `terreno_montana.ROCA_UMBRAL_NZ` (hoy 0.792 = pendiente 0.77 = 37.6 grados,
  derivado de `mascara_terreno.UMBRALES['PEND_ROCA']`) y `ROCA_ATR` 0.49 (sin cambio); el pie de derrubios (`mascara_roca` 0.5)
  NO es roca: leer `extras['capas']['roca']` de `geometria_3d.json` cuando exista (parche A1). `umbrales_roca()` tambien va en
  `geometria_3d.json['extras']['umbrales_roca']` tras A1.

## D. Altas en inspectores

Ninguna: esta entrega no crea objetos ni prefijos (solo el campo de alturas, la mascara y las capas).

## E. Verificacion hecha (todo en python del sistema, carpeta `_rev/_tmp_terreno/`)

1. `GEOM_OUT=... QA_DIR=... python preparar_geometria.py` 11 veces (v13-v23, 14 s cada una); v23 = codigo entregado:
   `celdas que invaden la pista: 0`, hierba sobre el asfalto 0 tras la garantia, `|z - referencia Loews| 0.000`, fosos 0 muestras
   > 1.5 m en los 7 sectores, costuras identicas a la base (2.03 m / 127 celdas > 0.6), `coche_120m` igual, figuras
   `terreno_hillshade/perfil/secciones/zoom/costuras/capas.png` en `qa_v23/`.
2. `python urbanismo.py --geom _rev/_tmp_terreno/geom_v23.json --salida ...`: 193 casas, 0 fallos (24 controles), huecos 515 m.
3. `python _rev/medir_relieve.py --geom geom_v23.json --antes geom_antes.json` (tabla de arriba); `diag_tierra.py` por cada 10 m.
4. Encaje del McLaren: `assets/encaje_mclaren.evaluar()` necesita Blender (BVH de la malla): NO ejecutado. Medido en su lugar el
   dz del terreno en la huella de `zonas_excluidas`: 0.00 m dentro y a < 10 m, 0.09 m a 17 m, 0.68 m a 22.6 m (franja del
   margen de `peso_fuera_zonas`, 25 m + 15 de fundido; la EDT de la huella y la de `en_poligono` difieren 2-3 m en el borde),
   3.9 m a 29 m: el apoyo del coche y la holgura del portal (rayos a 1-3 m del borde, dentro del tunel) no cambian.
   El integrador debe pasar `test_montana_mclaren`/`encaje` en la regeneracion, como siempre.
5. Determinismo: v22 (constante parcheada en memoria) y v23 (constante en el fichero) dan el mismo `geometria_3d.json`.

## F. Pendiente honesto

- KPI principal 25.5 % (obj 40): limites estructurales de arriba; el siguiente paso real es el macizo/espolon del lazo (F2).
- Terreno a 120 m tras pueblo_subida_ladera baja de 83.0 a 78.1 m por la berma de 15-25 m (y 0.3 m mas por los bancales del espolon) (la cara retrocede: con 1.15 de
  pendiente son hasta 18 m menos de cota a 120 m); el objetivo >= 110 m es del macizo (F2, mismo propietario): recalibrar
  LANDFORMS 'Espolon del coche' entonces, no ahora.
- Roca > 35 grados 73.3 % con los umbrales de la mascara (B1: 81.4 % si el propietario `mascara` acepta 0.68-0.80 / 8 m).
- A2 (rasante en los apex) escrito pero NO aplicado: contradice la decision 7 (baja la cima 3.7 m); necesita [U].
- Capturas A/B (set `relieve`) y `terreno_perfil.png` de la escena real: solo tras la regeneracion del integrador.

---

# RONDA 2 (04/10/2026, noche) — arreglos a `director_f1_r1.md` problemas 2 y 3 (REAL), 9 y 12 (MENOR)

Ficheros MIOS cambiados en r2: `03_blender/terreno_montana.py` (+~160/-30 lineas, comentarios `F1 r2`), `03_blender/_rev/medir_relieve.py`
(KPIs a 15/20 m y vista sintetica de la postal 56). `assets/_geom_snapshot_terreno.json` no cambia (la pista no ha cambiado desde el
04/10 12:57; sigue siendo la entrada del test aislado). Pruebas en `03_blender/_rev/_tmp_terreno/r2/` (`qa_v24..v31/`, `geom_v*.json`,
`preparar_v*.log`, `medir_v*.json`, `urb_v28/`, `exp_*.log`, `diag_muestras.py`, `sonda*.py`, `exp_r2.py`, `vista56.py`, `scan56.py`).
Blender NO se ha lanzado. **AVISO al integrador**: `python urbanismo.py --geom ... --salida ...` escribe sus PNG de QA en `renders/qa/`
aunque se desvie la salida (lo lance sin `--sin-qa`): `renders/qa/urbanismo_*.png` son ahora los de mi geometria v28; el pipeline los
regenera. `geometria_3d.json`, `urbanismo.json` y `renders/qa/*.json` del proyecto NO se han tocado.

## r2.0 Que ha cambiado en `terreno_montana.construir()` (cada punto con su cifra)

| # | Cambio (constante) | Por que (director) | Medido (base = `_rev/geometria_rev.json`; r1 = candidata 20:07; r2 = `geom_v30.json`) |
|---|---|---|---|
| 1 | Lomo = LOMA redondeada: subida `1-(1-u)^2.5` en `TIERRA_LOMO_SUBIDA` 20 m (arranque 2.5h/L = 1.75 bajo el techo de 2.0), cresta `TIERRA_LOMO_CRESTA` 18 m, bajada al 50 % con acuerdo `TIERRA_LOMO_T` 12 m, cresta que serpentea `TIERRA_LOMO_SERP` +-4 m (ruido 50 m); costillas ridged (24/12 m, hasta 2 m) tambien en la CARA del lomo (relleno > 2 m, < 20 m del borde, solo 'dirt') | 2: postal 56 'piramide facetada' (tienda lineal con meseta plana de 30 m y dos planos) | check `costillas_relleno_celdas`; vista sintetica 56 sin cambio de silueta respecto a r1 (tierra 64.9 %, horizonte en la fila 25/108); el A/B real lo hace el integrador |
| 2 | Vaguada: acuerdo parabolico `TIERRA_CAIDA_T` 2 m, fondo = minimo suave `TIERRA_CAIDA_K` 2 m, `TIERRA_CAIDA_PEND` 0.55 -> 0.60, ruido de altura 0.9-1.2 (antes 0.8-1.2) | 2: caidas de -6.4/-7.6 m a 25 m por ruido | PyC 25 m 25.5 % (r1 25.5; con acuerdo de 6 m bajaba a 24.5) |
| 3 | Lomo y vaguada a 0 a < 4.5 m del borde de asfalto mas cercano (propio u OTRO ramal), fundido a 8 m (`TIERRA_SIN_CORREDOR`) | 9: `dz_corredor_4p5m_max` 0.100 | corredor: 224 celdas con dz 0.10 -> **7 celdas** (todas en la isla de la C26, entre z0-0.6 y z0-0.5: el limitador de pendiente, morfologico, propaga el cambio de z_land de la celda vecina; invisible bajo el arcen) |
| 4 | El peso del tiron de la tierra (`TIERRA_PESO_TIRON` 0.5) solo cambia z_land a < 100 m de una muestra dirt (fundido a 160 m) y fuera del corredor: segunda `_idw_pull` con los pesos de antes y mezcla | 1 y 9: la media gaussiana (sigma 100 m) movia 0.01-0.11 m el terreno a 300 m de la tierra (13 522 celdas con dz > 0.5 en r1) | celdas con dz > 0.5: 13 522 -> **6 872**; > 2 m: 7 683 -> 3 988; McLaren huella y +10 m: **0.000** |
| 5 | Lo nuevo de F1 junto al McLaren con margen +30 m (`_w_mcl_f1`, `TIERRA_MCL_MARGEN`): bancales en el espolon (`w_banco_sel`), berma (`w_tope`), costillas de 4 m | 9: McLaren lt_25m 0.68 | lt_25m 0.68 -> **0.12** (6 celdas a 14-23 m del poligono `zonas_excluidas`, NO del coche: su esquina NE tras pueblo_subida_ladera a 97 m de la pista; es el NIVEL DE RELLENO de la QA de fosos, que sube 0.12 m porque la cara tras la berma, a > 30 m, es mas alta; 0.000 dentro del poligono y a < 10 m) |
| 6 | Berma tras la ultima terraza: acuerdo parabolico `BERMA_ACUERDO_T` 3 m y cara x`BERMA_CARA_FACTOR` 1.8 (1.15 -> 2.07; en el espolon del coche sigue 2.0 sin berma); bancales en FASE CERO al final de la berma (`A (1 - cos(2 pi (c - c0)/H))`, derivada nula en c0) en vez de la rampa de la v3 sobre el seno | 2: 'terreno a 120 m tras pueblo_subida_ladera EMPEORA 83.0 -> 78.1'; fosos | 120 m: **83.0 m** (= base; x1.3 81.4, x1.5 82.6, x1.75 82.9); fosos > 1.5 m **0** en los 7 sectores (max 1.31 m en s 960; base 1.06-1.40); `coche_120m` 27.1/110.4/17.4 % igual |
| 7 | Banda de los perfiles de la QA de fosos (o_fin-3..o_fin+40 por la normal de cada muestra de cada sector, su lado) sin lomo ni vaguada (< 3 m, fundido 9 m) | foso de 2.04 m tras pueblo_alto_ladera que aparecio en v24 (la cresta del lomo de s 1540-1600, mas corta, asomaba a o_fin+15-20) | pueblo_alto_ladera 0 muestras > 1.5 (max 0.46) |
| 8 | Capas: canal B (tierra) de los cortes someros = peso continuo (pendiente > 0.35 +- 0.08 con ruido de 15 m, profundidad del corte > 1.5 +- 1 m) en vez de `_dsm & pendiente > 0.35` | 12: ladera del penon partida en dos tonos (toma 36) | medias en tierra matorral 46.0 / seca 20.2 / tierra 7.5 / roca 26.3 %; suma 1 en el 100 % |
| 9 | Probado y DESACTIVADO (`TIERRA_PARED_H_MIN` = 0): lomo minimo de 10 m donde el natural sube >= 3 m | 2: pared de 3-7 m en el interior del lazo | +0.2 % de PyC por 131 celdas levantadas 1.2 m de media: donde faltaba pared manda el TECHO de la rama de al lado (isla B-C de la cima: natural +13.9, techo de la rama baja +5.1), no la altura del lomo |

Verificacion (todo python del sistema): `preparar_geometria.py` x8 (v24-v31, 14 s), v29 = v30 = v31 byte a byte (`md5_final.txt`: determinista);
`urbanismo.py --geom geom_v28.json`: **193 casas, 0 fallos** (24 controles), huecos 515 m (igual); `medir_relieve.py --antes geometria_rev.json`:
invaden 0, hierba_asfalto 0, Loews 0.000, costuras **2.03 m / 127 celdas (identicas a la base)**, `erosion_corredor_dz_max` 0.000;
`terreno_perfil.png` / `terreno_hillshade.png` / `terreno_capas.png` en `qa_v30/`. Umbrales de roca: `mascara_terreno.UMBRALES` ya trae
0.68-0.80 / 8 m (B1 aplicado por 'mascara' en r2) -> **celdas > 35 grados con roca 81.6 %** (obj 80; r1 73.3), > 40 grados 86.0 %, roca
en el 27.5 % de la tierra.

## r2.1 KPI 'pared Y caida a 25 m' 25.5 % (obj 40): por que no sube y que propongo al coordinador

Medido por muestra (`diag_muestras.py`, tabla cada 10 m con natural a 60 m, dz a 25 m y lado alto) y por celda (`sonda*.py`):
- Las ramas del zigzag del lazo van **apiladas a ~50 m** con 10-14 m de desnivel (A 1670-1750 / B 1770-1860, D 2020-2110 / E 2120-2220,
  E / F 2230-2290, G 2300-2360 / E' 2380-2440). A 25 m del borde las dos ramas de cada par comparten la MISMA celda (la linea media):
  'pared' para la rama baja (>= +8 sobre ella) y 'caida' para la alta (<= -8 bajo ella) exigen a esa celda estar a la vez >= z_baja+8 y
  <= z_alta-8: con 10-14 m de desnivel es imposible. Por diseno gana el lomo (rama baja: pared de 14 m tallada en la ladera; la alta se
  queda con hombro llano). Las que ganan: 1570-1580, 1680-1750, 1970-2010, 2150-2210, 2390-2420 = 25.5 %.
- La cima (B 1770-1860) es una trinchera natural (pared a los dos lados: la isla de la horquilla, +14 m natural, y la ladera) y C
  (1880-1960) tiene su pared recortada por el techo de desmonte de B (1.15) a +5 m: subirla exige un desmonte mas empinado en B, que
  levanta 2-6 m la isla que mira la postal 56 (fila 25 -> ~13 del cuadro). No lo he hecho (regresion segura en 56).
- 1430-1525 son las terrazas de pueblo_alto (10 % del tramo), 1600-1660 un collado y 2230-2290 una cresta natural sin ladera que acercar.
- Tope alcanzable con la geometria actual de la pista: ~30 %. A **20 m** (lo que ve el piloto) PyC es **27.3 %** (base 10.5) y a 15 m
  11.3 % (base 0). 'pared en algun lado' a 25 m: 45.8 % en tierra (obj 50; base 22.7); a 20 m 48.8 %.
- Propuesta [coordinador]: dar el KPI por 'acotado por la geometria del zigzag' en F1 (o medirlo a 20 m), y pasar lo que queda
  (macizo/espolon del lazo, 1b) a F2 como ya dice la decision del coordinador para esta ronda.

## r2.2 Postal 56 ('bahia entera abajo'): analisis con cifras y propuesta [coordinador / infra]

Vista sintetica (`vista56.py` / `medir_relieve.medir_postal56`: rayos desde la camara congelada `56_postal_cima_bahia` = ojo de piloto en
s 1870, azimut 190, lente 20; sin arboles ni objetos, es el TECHO de lo visible):
- Base: mar **0.9 %** del cuadro, tierra 63.6 %, horizonte de terreno en el centro en la fila 35/108. r1: 1.2 % / 64.9 % / fila 25.
  r2: 1.2 % / 64.9 % / fila 25 (sin regresion respecto a r1; la 'piramide' ya es loma redondeada con costillas: lo juzga el A/B real).
- Lo que tapa la bahia a 14-23 m de la camara es la **isla de la horquilla C18-19** (z 121-125; en la base 117-124) y, detras, la rama
  C (s 1920 a 45-55 m, z 113.6 = justo en la linea ojo-bahia a -10 grados). Para ver el mar la isla tendria que quedar POR DEBAJO de
  la rasante (< 118 m a 20 m) = un hoyo en el interior de la horquilla: no es terreno natural ni lo pide nadie.
- `scan56.py` (ojo de piloto en s 1850-1980 cada 10 m x azimut 100-260 cada 10 grados, lente 20) sobre r2: el MAXIMO de mar es **4.5 %**
  (s 1860, az 170; s 1960, az 160: 4.3 %). Desde el coche, en la cima, la bahia esta tapada por el relieve natural al S del lazo
  (espolon entre el lazo y la costa, lomas de la recta 107 m): bajarlo es landform (bloque 1.3, F2) o la postal se hace desde mas
  alto (grua/helicoptero) o se redefine. Decision del coordinador; en r2 NO toco landforms (decision 'macizo = F2').

## r2.3 Puerta (`asentar` 57 -> 72 / 28 -> 31, `revisar_urbanismo` 23 -> 25): atribucion y parche

Comparando `_rev/asentar_rev.json` (base) con `_rev/asentar_candidata.json` por POSICION (no por nombre: la vegetacion se renumera):
- De los 54 'nuevos' (> 0.6 m) de la candidata, **~20 estan en celdas que F1 movio** (dz_terreno != 0: 9 en el tramo de tierra sobre el
  lomo/caida de 15-27 m del borde, 5 en el arranque de la cara tras pueblo_subida_ladera, 6 tras pueblo_alto); los otros ~34 estan en
  celdas con dz = 0.00 (re-sorteo del integrador: misma posicion con otro nombre o posicion nueva lejos de todo cambio: ITAL_cipres.0xx a
  266-296 m de la pista, VEG_cipres.273/370/275 en el casino, el grupo de s 88-140...). 36 de la base desaparecen por lo mismo.
- Arboles del integrador sobre pendiente > 0.67 (medido en las posiciones asentadas): base 9, r1 18; con la geometria r2 en esas mismas
  posiciones 52 (el lomo ahora arranca a 1.75 bajo el techo de 2.0 y lleva costillas), en las posiciones de la base 39. Con el relieve
  pedido por el plan (pared de 40-63 grados a 4.5-25 m del borde) **cualquier arbol que `zona_tierra` plante a 15-27 m del borde cae en
  la pared**; `asentar` lo mueve 2-4 m ladera abajo (dz 1-3 m = 'enterrado/flotaba > 0.6') o lo quita ('ladera imposible'). Hoy
  `zona_tierra` no mira la pendiente (las otras zonas si: `pendiente_terreno > 0.62` en integrar_escena l.2266/2313).
- `objeto_salto_grande` 8 -> 10: 1 de los 10 (VEG_cipres.006, s 2090, lomo +8.5 m) es de F1; los otros 9 estan en celdas sin cambio
  (el grupo de 4 en s 88-140 esta en la base con otros nombres). `prop_camino` +1 (ITAL_fuente.005, s 1344 a 75 m, dz_terreno -0.15)
  y `arbol_calle` -1 son sorteo. `dentro_de_muro_quitados` 0 -> 1 (VEG_pino.569 en CAMINO_muro.073, s 1460 a 26 m, dz 0.00): sorteo.

### r2.3-A Parche a `integrar_escena.py` `zona_tierra()` (l.1711-1725): no plantar en la pared [integrador]

Sustituir el bucle de los arboles por:

```python
    while s_m < 2370:
        tipo = ('pino', 'cipres', 'pino2')[k % 3]
        side = 1 if k % 2 else -1
        res_ = None
        # fase visual F1 r2 (PARCHES_F1_terreno.md r2.3-A): el lado alto de la tierra tallada es una pared de 40-63 grados a 4.5-25 m
        # del borde: el arbol va al primer sitio con pendiente < 0.62 (el mismo umbral que las laderas, l.2266) probando los
        # dos lados y 3 offsets; si no hay, no se planta (asentar lo movia 2-4 m ladera abajo o lo quitaba: 'ladera imposible')
        for sd_ in (side, -side):
            for o_ in (15 + (k % 3) * 6, 23 + (k % 3) * 6, 31 + (k % 3) * 6):
                (p_, _) = pos_side(s_m, sd_, o_)
                if _d_borde_cualquiera(p_[0], p_[1]) >= 12.0 and pendiente_terreno(p_[0], p_[1]) <= 0.62:
                    res_ = (p_, sd_)
                    break
            if res_ is not None:
                break
        if res_ is not None:
            clone(lib[tipo], res_[0], rnd.uniform(0, 6.28))
        else:
            n_fuera += 1
        s_m += 52
        k += 1
```

Medido con la geometria r2 sobre los 43 VEG_ de la candidata plantados por `zona_tierra` (s 1560-2380, 10-30 m del borde): **9 estan
sobre pendiente > 0.62** (VEG_cipres.004/005/006/007, VEG_pino.010/011/014, VEG_roca.006, VEG_olivo.285; 7 de ellos en la lista de
'nuevos' de asentar) -> con el parche no se plantan ahi (o van al otro lado / mas lejos) y desaparecen de `flotaban/enterrados > 0.6` y
de `objeto_salto_grande`. Prueba: `integrar_escena.log` linea `tierra: N arboles sin sitio` (sube de 0-2 a <= 9) y `asentar.json`
`arboles_desplazados_ladera` (64 en r1) baja. Lo mismo vale para las 10 `VEG_roca` de cima (`_sitio_lejos_pista(s_m, ..., 26-41 m)`):
anadir el mismo filtro de pendiente si siguen cayendo en la pared.

### r2.3-B Peticion de RE-BASE justificada [coordinador]

Aun con el parche, los contadores de `asentar` son un sorteo (+-10 por regeneracion: 36 de la base desaparecen y 34 nuevos aparecen sin
que el terreno cambie en su celda). Propongo re-basar `linea_base.json` tras la regeneracion r2 con el parche r2.3-A SI se cumplen:
costuras 2.03/127 (= base), fosos 0, invaden 0, Loews 0.000, urbanismo 0 fallos y 193 casas (todo medido ya en r2) y
`flotaban/enterrados` no peores que la base **en las celdas donde F1 no mueve el terreno** (dz < 0.5: 259 383 de las 266 255 celdas).
Hasta F3 (plan de vegetacion, que ya respeta roca > 0.6 y la mascara) los arboles del integrador seguiran cayendo en las paredes nuevas
de la tierra: es el precio del relieve que pide el usuario, no un defecto del terreno.

## r2.4 Residuos explicados (no son fallos del terreno)

- `dz_corredor_4p5m_max` 0.100 en **7 celdas** (r1: 224), todas en la isla de la horquilla C26 (s 2332-2398), entre z0-0.6 (suelo) y
  z0-0.5 (techo): el limitador de pendiente (morfologico) propaga 0.3 m de cambio de z_land de la celda vecina y el clip cambia de cota.
  Bajo el arcen, no fisico. Para 0.000 habria que correr el limitador dos veces (+3 s) y mezclar: no lo veo necesario.
- `dz_mclaren lt_25m` 0.12 en 6 celdas a 14-23 m de la ESQUINA NE del poligono `zonas_excluidas` (290 x 480 m: el poligono es la zona
  del coche, no el coche), a 97 m de la pista tras pueblo_subida_ladera: nivel de relleno de la QA de fosos +0.12 m. 0.000 dentro del
  poligono y a < 10 m: el apoyo y la holgura del McLaren no cambian. `encaje_mclaren.evaluar()` necesita Blender: integrador.
- `medir_relieve` foso 'proxy 1D' 1.90 m en pueblo_alto_ladera es el proxy severo (aviso); la QA de construir (referencia de la puerta)
  da 0 muestras > 1.5 m (max 0.46).

## r2.5 Otras notas para el integrador / coordinador

- `_rev/medir_relieve.py` imprime ahora PyC a 15/20 m y la linea `postal 56 (vista sintetica ...)`; el JSON lleva `postal56`.
  A3 (medir_relieve en el pipeline) ya esta aplicado por el integrador (`_rev/logs_f1_r1/medir_relieve.log`).
- A1 (extras['capas']) aplicado por el integrador. A2 (rasante en los apex) sigue [U]: NO aplicar.
- B1: aplicado por 'mascara' (UMBRALES 0.68-0.80 / 8 m): 81.6 % medido aqui, cierra el KPI del plan (>= 80).
- Determinismo: v29 = v30 = v31 (md5 iguales) con el mismo `assets/_geom_snapshot_terreno.json` y `urbanismo_spec.json`.

---

# RONDA 3 (04/10/2026, noche, ~22:10-23:40) — `director_f1_r2.md` problemas 1 y 2 (REAL), propietario `terreno`

Ficheros MIOS cambiados: `03_blender/terreno_montana.py` (comentarios `F1 r3`; constantes nuevas `TIERRA_CAIDA_LIBRE_D/ASF`,
`TIERRA_PARED_REAL`, `TIERRA_BLOQ_APEX`, `TIERRA_LOMO_CORE`, `TIERRA_LOMO_GAP`, `TIERRA_LOMO_COLA_T` (desactivada), `TIERRA_TIRON_ALCANCE`;
extras nuevos `tierra_raise_who`, `tierra_lower_who`, `tierra_caida_libre`; checks `tierra_caida_bloqueada_muestras`,
`tierra_tallada_celdas_cola_recortada`), `03_blender/_rev/medir_relieve.py` (linea y JSON `estructura_10m`: cuantas filas de 10 m
tienen PyC y cuantas son imposibles por la geometria de la pista). `assets/_geom_snapshot_terreno.json` NO cambia (muestras, curvas,
pit_lane y loews identicos a `geometria_3d.json`, comprobado por md5: sigue siendo la entrada del test aislado). Pruebas en
`_rev/_tmp_terreno/r3/` (`ciclo.sh vNN` = preparar_geometria a QA_DIR + medir_relieve + tabla por filas; `geom_v33..v42.json`,
`preparar_v*.log`, `medir_v*.{json,log}`, `qa_v*/` con `terreno_perfil/hillshade/capas.png`, `ramas.py` + `ramas_v*.log` (estructura del
zigzag: otra rama por la normal y perfil lateral), `sonda_dbg.py` (z_land/techo/suelo/lomo/vaguada y la MUESTRA que manda en cada
celda), `zoom_fig.py` + `zoom_*.png` (hillshade + curvas de nivel de la cima y del lazo, base / r2 / r3), `atribucion_puerta.py`,
`urb_v42/urbanismo_v42.json` + `urbanismo_v42.log`). Blender NO se ha lanzado; `geometria_3d.json`, `urbanismo.json` y `renders/qa/`
del proyecto NO se han tocado. **Version entregada = v42** (`geom_v42.json`; determinismo: v38 = v39 byte a byte, md5 394b49cc…).

## r3.0 Que cambia en `terreno_montana.construir()` y por que (con cifras; base = `_rev/geometria_rev.json`, r2 = candidata 21:37)

| # | Cambio | Por que (director r2) | Medido |
|---|---|---|---|
| 1 | **CAIDA LIBRE por muestra** (`_caida_libre`, entra en `_caida_ok`): la vaguada solo se excava si su punto de medida (25 m, lado bajo) NO esta en la ZONA DE PARED de otra rama (celdas a < 27 m del borde de una muestra que tiene ese punto en su lado alto con pared real: natural >= z + 7 o lomo natural >= 7.5) ni a < 12 m de su asfalto; suavizado 4 m en s | 2: tramos 1830 y 1930 con 0-50 %. La vaguada de la horquilla de la cima (B, s 1770-1860, lado bajo = isla) abria una ZANJA de 13-14 m (`sonda_dbg`: s1940-1@24: z_land 125.0, lower 13.2 -> 111.4) en la isla natural (+13..+15 sobre C) que es la pared de la rama C (s 1880-1960): C sin pared a 25 m y B sin caida (su punto de 25 m queda sobre el lomo de C). Esa zanja era la 'piramide de dos picos' de la postal 56 | PyC 25 m **25.3 -> 30.6 %**, pared en algun lado **45.7 -> 52.0 %** (obj 50). Filas ganadas: s 1904-1960. `zoom_cima_v33.png`: isla continua 118-126 m, sin zanja |
| 2 | Cono (techo) de cada muestra a `TIERRA_PEND_INT` (2.0) tambien en su lado bajo BLOQUEADO y, para las OTRAS ramas (`ceil_j`), el mismo pend por (celda, j) que el propio (antes 1.15 fijo) | el cono de B a 1.15 recortaba la pared natural de C a +0.8..+5 en s 1900-1920 | +1900-1920 (PyC 30.6 -> 31.0) |
| 3 | **Zona de pared del lomo** (`raise_core`, dedge <= `TIERRA_LOMO_CORE` 32 m, o todo el lomo si la celda esta en un hueco de < `TIERRA_LOMO_GAP` 60 m entre su rama y otra): solo esa parte apaga la vaguada de otra rama (`lower *= 1 - clip(raise_core/3)`); la COLA (meseta final y bajada, hasta 70 m) ya no la apaga | 2: s 1660-1690 (+1) sin caida: la cola del lomo de 14 m del collado (s 1588) llegaba a 45-50 m con 3.4 m y mataba la vaguada | PyC **31.0 -> 33.6 %** (+1658-1674, +2070-2078); el hueco < 60 m mantiene 'gana el lomo' entero en las islas de horquilla (D/E, s 2090-2110: sin hoyo en medio) |
| 4 | Probado y DESACTIVADO (`TIERRA_LOMO_COLA_T` 1e9): recorte de la cola del lomo al techo de la vaguada de enfrente con fundido 15 m (v35) | 2: ramas apiladas a 60-80 m (s 1610-1620 sobre 2150-2220) | PyC 34.6 % (+1 punto) pero zanja en V de 10-16 m entre el lomo de la rama baja y la alta y hoyo cerrado en el collado (`zoom_lazo_v35.png`); PyC a 50 m 19.2 %. 'Formas suaves' manda: fuera |
| 5 | Probado y REVERTIDO (`TIERRA_LOMO_H_NAT` = (3, 5)): lomo solo con subida natural >= 6-8 m | - | sin ganancia a 25 m y -5 puntos a 50 m (s 2320-2350) |
| 6 | Junto a los apex de horquilla (`TIERRA_BLOQ_APEX` 30 m por la pista) los conos se quedan en 1.15 (lado alto y lado bajo bloqueado) | postal 56: con 2.0 la isla de la cima crecia (horizonte de terreno en la fila 18 del cuadro) | fila 20 (r2: 25; base: 35); PyC igual; pared de B (+1) +25 -> +16 en s 1840 (sigue >= 8) |
| 7 | Alcance del peso 0.5 del tiron (`TIERRA_TIRON_ALCANCE` 60-110 m; r2: 100-160) | 1: a 85-110 m de la tierra (hinterland de pueblo_alto_ladera: ermita, cipreses del sendero ERMITA) el natural bajaba 0.6-1.5 m sin tocar el KPI | ermita centro dz -0.89 -> -0.28, esquina -1.04 -> -0.38, mirador -0.60 -> -0.07; celdas con dz > 0.5 vs base **6872 -> 5178** (> 2 m: 3988 -> 3209); hinterland x -200..-50 / y 440..580: 649 -> 316 celdas (> 2 m: 209 -> 35) |

**KPIs base -> r2 -> r3 (medir_relieve v42, `medir_v42_base.log`)**: pared Y caida a 25 m **4.5 -> 25.5 -> 33.6 %** (obj 40); a 20 m 10.5 ->
27.3 -> 29.8; a 15 m 0 -> 11.3 -> 11.7; a 50 m 22.1 -> 27.7 -> **23.3 %** (perdidas s 2132-2160 y 2336-2350: la meseta de la cola del lomo de
E a 50 m ya no es 'pared' al no mandar fuera de su zona; obj 60 inalcanzable con esta pista); pared en algun lado (pared_roca tierra) **22.7
-> 45.8 -> 52.2 %** (obj 50, cumplido); caida en algun lado 48.4 -> 51.8 -> 55.5 %; roca > 35 grados 81.7 %; 120 m tras pueblo_subida_ladera
83.0 (=). Invariantes: costuras **2.03 m / 127 celdas (= base)**, fosos **0** en los 7 sectores (max 1.31 / 0.43 / 0.46 / 0.10 / 0.20 / 0.48 /
1.40 m), invaden 0, hierba_asfalto 0, Loews 0.000, `coche_120m` 27/110/17 % (=). `urbanismo.py --geom geom_v42.json`: **193 casas, 0
fallos (25 controles), huecos 515 m** (=). dz r3 - r2: max 13.8 m, celdas > 0.5: 2704 (todas en s 1200-2600 a < 120 m del borde: el lazo
y el hinterland de pueblo_alto); corredor 0.000 y McLaren 0.000 respecto a r2.

## r3.1 KPI 'pared Y caida a 25 m': 33.6 % y por que no llega al 40 % (cifras; peticion de acotacion escrita al coordinador)

`medir_relieve` imprime ahora la ESTRUCTURA por filas de 10 m (102 filas en s 1430-2440): PyC 34 (33 %); imposibles por la geometria de la
pista 17 (17 %): terrazas de pueblo_alto a ambos lados 8, pared a ambos lados (horquilla de la cima B, s 1780-1860, y trinchera) 6, caida a
ambos lados (crestas s 1540-1560, 2250-2290) 3; 'solo pared' 14, 'solo caida' 19, 'ninguno' 18. De las 51 filas con un solo lado, medidas
una a una con `ramas_v42.log` y `sonda_dbg.py`:
- 1590-1620 (lado -1), 2020-2060, 2090-2110: la rama de enfrente esta apilada a 34-57 m con 4-13 m de desnivel: a 25 m las dos comparten
  celda y 'pared de la baja' (>= z_baja+8) y 'caida de la alta' (<= z_alta-8) solo caben juntas si el desnivel es >= 16 m. Con 60-80 m
  (1610-1620 / 2150-2220) caben, pero solo como lomo + ZANJA en V (probado, v35: +1 punto): descartado por forma.
- 1770-1860 (B): pared natural a +1 (loma NO de 122-128 m) y la isla/pared de C a -1: pared a ambos lados; una vaguada seria un hoyo.
- 2230-2290 y 1530-1560: cresta natural (cae a los dos lados): la pared exigiria un dique de 8 m sobre llano ('levee').
- 2300-2360 (G): lado alto llano (natural +0..+3.5 a 60 m, sin ladera que acercar) y lado bajo = banco de la C26 (pared de E').
- 1430-1520: terrazas de pueblo_alto (plan: no se tocan).
Tope alcanzable con esta pista sin zanjas: ~34 %; con zanjas ~35 %. Lo que si subiria el KPI de verdad es relieve natural nuevo en el
lazo (espolon/macizo = landform, bloque 1.3, F2). **Propuesta [coordinador, por escrito]**: dar por cerrado 1a en F1 con PyC 25 m >= 30 %
(hoy 33.6) + pared_roca >= 50 % (52.2) + 0 regresiones de forma, y pasar el resto del 40 % a F2 con el macizo. Sin esa decision escrita el
KPI no cumple y lo digo tal cual.

## r3.2 Postal 56

La 'piramide facetada de dos picos' era la zanja de la vaguada de B en la isla (r3.0 n.º 1): en r3 la isla es una loma continua (118-126 m,
`zoom_cima_v42.png`). Mar en el cuadro 1.2 % (= r2; base 0.9): sigue tapado por la rama C a 45-55 m y por el espolon natural al S del lazo
(lomas de 107 m a 300 m: `scan56.py` r2, maximo 4.5 % desde cualquier punto de la cima) = landform F2. Horizonte de terreno en el centro:
fila 20 de 108 (r2 25, base 35): la isla sin zanja es algo mas alta en esa columna; el A/B real (`AB_56`, `AB_ac_56`) lo hace el integrador.

## r3.3 Puerta (`puerta.json ok: false`): atribucion objeto a objeto (`atribucion_puerta.py`, sobre la candidata r2 del director)

Criterio: dz del terreno base -> candidata en la celda del objeto y maximo a < 10 m; 'F1' si |dz| > 0.3 a < 10 m, 'sorteo' si el terreno es
IDENTICO a < 10 m y el objeto no esta en la base (posicion nueva: el RNG de `integrar_escena` cambia con cualquier objeto mas o menos),
'igual que la base' si el mismo fallo esta en la base.

**revisar_urbanismo 29 vs 23**: 11 iguales que la base, **11 sorteo** (terreno identico: `arbol_calle` OLI_matorral.152, `bancal_mal`
ITAL_bancal.011 (pie_centro -0.16, muro del plan), `objeto_salto_grande` VEG_palmera.126/.127, VEG_pino.566/.605, VEG_cipres.023, OLI_olivo.162,
`sendero_enterrado` CAMINO_tierra.001 (168,661), `sendero_volado` x2) y **7 F1**: `camino_sin_destino` URB_travesias_0_1 (extremo (-488,505):
dz 0.00 en el punto, 0.35 a < 10 m; el log de integrar dice 'extremo sin destino en (-488, 505)' TAMBIEN en la base: el plan de urbanismo
perdio un muro 'ultimo' de pueblo_subida_ladera (23 -> 22 muros, muro2_1 9 -> 7 pts) al suavizar la berma el escalon de atras: el extremo
ya no toca nada a < 6 m), `ermita_desnivel` ITAL_ermita.003 (mirador del sendero ERMITA movido de (-96,543) a (-107,546) por el A*; esquina
0.61 m: `explanar(margen=2.0)` no cubre las esquinas en una celda de 4 m con la cara de 2.07 detras; en r3 el terreno ahi vuelve a dz
-0.28/-0.38 (r3.0 n.º 7)), `prop_camino` ITAL_fuente.005 (el sendero CIMA re-planificado por el A* entra 0.7 m en la fuente de la plazoleta de
su salida), `bancal_mal` ITAL_bancal.005 (CIMA, s 1828 lado +1 a 48 m: fondo_der 0.92 tras `tallar_cinta`), `sendero_enterrado` CAMINO_tierra.003
(-288,598: berma de pueblo_subida_ladera, dz -5.44; 2 vertices, 0.26 m), `objeto_salto_grande` VEG_arbusto.349 (junto a la cinta del CIMA, dz
-4.09 -> -2.27 en r3) y VEG_pino.189 (C26, dz -0.87, anillo 1.19 -> 1.23).
**asentar enterrados > 0.6: base 57 (7 en celdas F1) vs candidata 66 (14 en celdas F1: 11 F1 + 39 iguales + 16 sorteo)**; flotaban 28 (11 F1)
vs 25 (5 F1). Los 28 `CALLE_poste_guirnalda` 'enterrados 0.92' estan igual en la base. **arboles_quitados 5 vs 3**: VEG_cipres.011 (viaducto)
igual que la base; VEG_cipres.115 (-430,562), VEG_olivo.257 (-443,542), VEG_cipres.280 (-229,522) 'ladera imposible': **terreno identico base =
candidata (dz 0.00, anillo de 1.2 m 1.67 / 1.63 / 0.68 m en las dos)** = posiciones nuevas junto a los muros de terraza (pendiente a 10 m 0.58-0.60
<= 0.62: pasan el filtro del integrador y el anillo de asentar las tumba); VEG_pino.483 copa sobre calle: sorteo. Ninguno de los 5 es del
terreno. **bancales_mal 2 vs 1**: .005 F1 (CIMA), .011 sorteo.

### r3.3-A Parches a `integrar_escena.py` [integrador] (quitan los 4 fallos nuevos que dependen de colocacion, pase lo que pase con el sorteo)

1. **Ermita**, l.5236 `explanar(e_, margen=2.0, desmonte=1.2, roca=False)` -> `explanar(e_, margen=4.5, desmonte=1.2, roca=False)`: con margen
   >= `T['cell']` + 0.5 todos los vertices de los triangulos que contienen las esquinas quedan a `zb`; `ermita_desnivel` (tolerancia 0.5 m) no
   puede salir por la rejilla. Prueba: `revisar_urbanismo` sin `ermita_desnivel`; `asentar.json` edificios ITAL_ermita sin cambio.
2. **'Ladera imposible' = anillo de asentar**: en `zona_montana()` l.2275 y l.2322 y en `_sitio_lejos_pista()` l.1710 anadir a la condicion de
   pendiente `or pendiente_terreno(xa, ya, d=0.6) > 1.25` (resp. `pendiente_terreno(p[0], p[1], d=0.6) > 1.25`): es el mismo anillo de 1.2 m
   que `asentar_objetos.apoyo_arbol` (DESNIVEL_MAX 1.6 / 1.2 = 1.33) medido con la bilineal; a 10 m un muro de terraza de 6 m da 0.6 (pasa) y
   a 1.2 m da 1.6+ (se quita). Prueba: `asentar.json` `quitados` con motivo 'ladera imposible' = 0 (hoy 4), `arboles_desplazados_ladera` baja.
3. **Fuentes y plazoletas prohibidas para el A* de los senderos**: en `_prohibido_sendero()` (l.5001) `f(x, y)`, tras la linea l.5027
   (`d_casa < 5 or d_calle < 4`), anadir `if any(math.hypot(fx_ - x, fy_ - y) < 6.0 for (fx_, fy_) in ctx.get('fuentes', ())): return True` y
   en `_contexto_senderos()` cargar `ctx['fuentes'] = [(o.location.x, o.location.y) for o in root_col.objects if o.parent is None and
   o.name.startswith('ITAL_fuente')]` (misma lista que l.6570). El arranque (`cerca_ini` 16 m) sigue exento, pero el recorte 'la cinta pisaba
   la plaza' ya aleja el primer punto; si el primer tramo aun entra en la fuente, subir el margen del recorte 0.3 -> 1.0 m (l.5165).
   Prueba: `revisar_urbanismo` sin `prop_camino` nuevo (CAMINO_cartel.003 es de la base).
4. (menor) `sendero_enterrado` 2 vertices / 0.26 m en CAMINO_tierra.003: `garantia_senderos` de asentar ya baja +-2.5 m; si queda, bajar su
   tolerancia de 'hierba > 0.15' no es cosa del terreno. Se deja anotado.

### r3.3-B Re-base justificada [coordinador], SOLO tras regenerar con r3 + r3.3-A

Con la geometria r3 el terreno vuelve a la base en el hinterland de pueblo_alto (ermita/cipreses: dz <= 0.4) y cambia menos celdas en total
(5178 vs 6872). Lo que queda: (a) `revisar_urbanismo`: con r3.3-A caen `ermita_desnivel`, `prop_camino` nuevo y 'ladera imposible'; el
`camino_sin_destino` (muro del plan que desaparece con la berma) y el `bancal` del CIMA son consecuencia del relieve pedido: si siguen,
son 2 fallos de tipo nuevo que el coordinador debe aceptar o no (no son del terreno en si). (b) `asentar.enterrados/flotaban`: son un sorteo
+-10 (16 'nuevos' y 36 'desaparecidos' en celdas con terreno identico): propongo re-basar SOLO esos dos contadores cuando se cumpla
'no peores que la base en las celdas que F1 no mueve' (`atribucion_puerta.py` lo imprime: hoy 52 vs 50 en celdas identicas) y costuras /
fosos / invaden / Loews / urbanismo 0 fallos y >= 190 casas iguales. `arboles_quitados` y `revisar_urbanismo` NO se re-basan (director).

## r3.4 Residuos (explicados, no son fallos del terreno; sin cambio desde r2.4)

`dz_corredor_4p5m_max` 0.100 m en 7 celdas de la isla de la C26 (entre z0-0.6 y z0-0.5, bajo el arcen, por el limitador morfologico);
`dz_mclaren lt_25m` 0.12 m en 6 celdas a 14-23 m de la ESQUINA NE del poligono `zonas_excluidas` (290 x 480 m: la zona, no el coche), a 97 m
de la pista, nivel de relleno de la QA de fosos: 0.000 dentro del poligono y a < 10 m. Respecto a la candidata r2 los dos son 0.000.
`encaje_mclaren.evaluar()` necesita Blender (BVH): lo pasa el integrador en la regeneracion, como en r1/r2.

## r3.5 Verificacion hecha (todo python del sistema, `_rev/_tmp_terreno/r3/`)

`preparar_geometria.py` x10 (v33-v42, 14 s cada una, QA_DIR propio); v38 = v39 byte a byte; `urbanismo.py --geom geom_v42.json --sin-qa`:
193 casas, 0 fallos, huecos 515; `medir_relieve.py --antes geometria_rev.json` y `--antes geometria_candidata.json` (`medir_v42_base.log`,
`medir_v42_r2.log`); `ramas.py`, `sonda_dbg.py`, `zoom_fig.py` (figuras `zoom_cima_v42.png`, `zoom_lazo_v36.png`); `qa_v42/terreno_perfil.png`
(pared +1/-1 a 40 m en todo el lazo), `terreno_hillshade.png`, `terreno_capas.png`. Capturas A/B (set BASE + relieve) y `encaje_mclaren`:
integrador.

## r3.6 Pendiente honesto

- PyC 25 m 33.6 % (obj 40): tope ~34-35 % con esta pista (r3.1); hace falta la acotacion escrita del coordinador o el macizo del lazo (F2).
- PyC 50 m 23.3 % (r2 27.7, base 22.1): consecuencia de que la cola del lomo ya no mande; obj 60 fuera de alcance en F1.
- Postal 56: forma arreglada; mar 1.2 % (obj 25) = landform F2.
- Los 3 parches r3.3-A son del integrador; sin ellos `revisar_urbanismo` puede seguir > 23 por sorteo aunque el terreno sea identico.
- A2 (rasante en los apex) sigue [U]: NO aplicar.

---

# RONDA 4 (04/10 23:40 -> 05/10 ~09:30, con dos cortes; ACOTACIONES_COORDINADOR_F1.md 1 y 4, director_f1_r3.md n.º 2) — propietario `terreno`

Ficheros MIOS cambiados: `03_blender/terreno_montana.py` (bloque `CUPULA_*` de la cabecera, l.~326-378; bloque `--- F1 r4: CUPULA` en
`construir()`, l.~2386-2470; costillas y roca/capas de la cupula; constante `CAPAS_PIE_FUERA_DE_A`; lectura y export de `ROCA_NZ_ZONA`,
`ROCA_NZ_ZONAS`, `ROCA_ATR_RUIDO`) y `03_blender/_rev/medir_relieve.py` (medida nueva `cupula56` + linea `cupula 56 ... -> CUMPLE/NO cumple`).
`assets/_geom_snapshot_terreno.json` NO cambia. Pruebas en `03_blender/_rev/_tmp_terreno/r4/` (`ciclo4.sh vNN`; `geom_v43..v59.json`,
`preparar_v*.log`, `medir_v*.{json,log}`, `vista_sintetica.py` + `vs56_*/vs51_*/vs07_*.png`, `sonda56.py`, `exp_cupula.py`, `urb_v55|v59/`,
`tex_v55|v57|v59/` (mascara de prueba), `aplicar_terreno_a_copia.py` + `aplicar_v*.log`, `escena_cand_r3_copia.blend` (copia de la candidata
r3 md5 d7e23a55), `escena_t_v59.blend` (copia + terreno r4b), `ab_v59/` (antes = `renders/ab/f1_r3/despues{,_ac}`) y `ab_v59_vs_mascara/`
(antes = `_rev/_tmp_mascara/r4/ab/despues{,_ac}`: aisla el cambio de terreno), con `AB_*`, `AB_ac_*`, `hoja_*`, `medidas{,_ac}.json`).
**Version entregada = v59** (determinista: v58 = v59 byte a byte, md5 24aff8fb...). Blender solo por la cola (5 pasadas, siempre sobre copias).

## r4.0 Que hace la CUPULA de la isla de la cima (interior de la horquilla C18-19, apex s 1864, postal 56)

1. **Cupula** (a < `CUPULA_SUR_T[0]` = 70 m del apex por la isla): techo que se IMPONE (rellena y rebaja; corredor < 4.5 m intacto, fundido a
   6 m) = smooth-min (radio 0.6 m) de dos familias de perfiles por muestra: rama ALTA (la cara que ve 56) convexa `h (1 - (1 - u)^1.5)`,
   h 12.5, L 33 (pendiente al pie 0.57 = 29.6 grados -> 0 en la cumbre); rama BAJA a 49 grados (`CUPULA_PEND_B` 1.15: mira al O, cara trasera
   desde 56, es la PARED del KPI de las filas s 1926-1976 de la rama alta); nariz (los 45 m delante de la camara) acotada a apex + 0.3 m.
2. **Loma sur = r3** (a > 95 m; transicion 70-95): la pared de 63 grados de la rama baja con su roca y costillas es la pared DERECHA de la
   toma de piloto **51** y la que ve la 07. La primera version (v48) llevaba la cupula hasta ahi y la vista sintetica de 51 pasaba de pared de
   roca a ladera dorada (3-8 m mas baja): regresion de piloto, descartada. La cresta de la loma sur la acota la LINEA DE VISTA de 56
   (`CUPULA_VIS_*`: ojo = apex + 1.2, <= 0 grados; queda a -0.2..-0.6 grados, por debajo de la cumbre de la cupula, +0.5).
3. **Sin roca, sin 'tierra' de corte y sin costillas en la cupula** (`_wroca56` / `_wdome56`); el flanco oculto de la rama baja conserva la roca
   hasta s 1815 (`CUPULA_ROCA_B_S`, fondo de la recta de 51). Origen de los dientes de r3: frontera roca/hierba sobre el flanco del cono a
   35-40 grados (nz 0.62-0.82 = justo el umbral por cara) + costillas ridged de 24/12 m que la hacian serpentear; en la cupula no hay frontera.
4. **Probado y APAGADO** `CAPAS_PIE_FUERA_DE_A` (pie de derrubios fuera del canal A): en 51/07 (modo normal) pintaba una banda marron al pie
   de la pared y en AC no quitaba dientes (rejilla 4 m tras las zonas de 'mascara': 1265 -> 1314). Con False el pie es como en r1-r3.

## r4.1 Cifras (python del sistema; `medir_v59.log` = base -> r4b, `medir_v59_r3.log` = candidata r3 -> r4b)

| Medida | base | r3 | **r4b (v59)** | objetivo / acotacion |
|---|---|---|---|---|
| pared Y caida a 25 m (tierra s 1430-2440) | 4.5 % | 33.6 % | **32.4 %** | >= 30 % (acotacion 1) |
| idem a 50 m | 22.1 | 23.3 | **23.3** | >= 20 % (acotacion 1) |
| pared en algun lado (pared_roca tierra) | 22.7 | 52.2 | **51.0** | >= 50 |
| PyC a 20 m / 15 m (informativo) | 10.5 / 0 | 29.8 / 11.7 | 25.7 / 7.9 | - |
| roca > 35 grados | 21.2 | 81.7 | 81.7 | >= 80 |
| cupula 56: cumbre sobre el ojo de la camara | +3.9 grados | +10.8 (cono, z 128.9) | **+0.5 (z 122.4)** | sin cono |
| caras a < 20 m de la cumbre VISTAS desde 56: max / % > 30 grados | 52.5 / 63.8 % | 68.4 / 88.0 % | **29.2 / 0.0 %** | <= 30 grados |
| todas las caras a < 20 m (incl. el flanco oculto = pared del KPI) | 53.8 / 67.2 % | 68.4 / 79.2 % | 56.5 / 32.8 % | ver r4.2 |
| roca por cara vista en la isla / dientes (regla del writer) | - | 39 / 7 | **0 / 0** | 0 dientes |
| invaden / hierba_asfalto / Loews / costuras / fosos > 1.5 | 0 / 0 / 0.000 / 2.03 m-127 / 0 | = | **0 / 0 / 0.000 / 2.03 m-127 / 0** (max 1.40) | no peor que la base |
| dz r4b - r3: corredor < 4.5 m / McLaren (0-40 m) / Loews | | | **0.000 / 0.000 / 0.000**; 111 celdas > 0.5 m, todas en la isla | |
| `urbanismo.py --geom geom_v59.json` | 193, 0 | 193, 0 | **193 casas, 0 fallos (25 controles)**, huecos 515 | >= 190, 0 |

Encaje McLaren: dz del terreno 0.000 en la huella y hasta 40 m respecto a r3 (y `coche_120m` igual) -> `encaje_mclaren` da lo mismo que en r3
(necesita Blender: lo pasa el integrador en la regeneracion, como siempre). Hierba sobre el asfalto (QA de preparar): 253 -> 0, igual que r3.
Mar de 56 (vista sintetica) 0.8 % (r3 1.2): pasa a F2 (acotacion 1); en el render se ve mas linea de mar a la derecha de la cupula.

## r4.2 Lo que NO cumple la lectura estricta de 'pendiente <= 30 grados en los 20 m superiores' (y por que)

La isla mide 36 m entre corredores (18 m de semiancho) y las dos ramas van 2-9 m por debajo de la cumbre. Las filas s 1926-1976 de la rama alta
cuentan para el KPI solo si a 25 m de su borde (15 m del corredor de la rama baja) el terreno esta a >= Z_alta + 8 = Z_baja + 12-13: pendiente
media >= 37 grados en ese flanco, que esta a < 20 m de la cumbre. Con <= 30 grados en TODO el disco de 20 m se pierden 6-9 filas (PyC 31 -> 25 %,
`exp_cupula.py`): incompatible con la acotacion de >= 30 %. Solucion entregada: la cupula que se VE (cara de la rama alta, nariz y cumbre:
0 % de caras > 30 grados a < 20 m de la cumbre, max 29.2) y el flanco de 49 grados en la cara trasera (mira al O; desde 56 no se ve: lo
confirman el ray-cast de `medir_relieve` y el render). Si el coordinador quiere la lectura estricta: `CUPULA_PEND_B` 0.577 y PyC ~25 %.

## r4.3 Renders sobre COPIA (Blender por la cola; `aplicar_terreno_a_copia.py`: dz r4b - r3 en el TERRENO y en los objetos sobre celdas que
cambian, mascara de v59, atributo roca = canal A, `roca_zonas_nz` y banda de 2 m de 'mascara' = lo que hara el pipeline con su A8)

Camaras congeladas `renders/ab/_base_antes/camaras.json`, `capturas_ab.py --solo 56_,07_,51_` en los dos modos, 0 avisos:
- **56** (`ab_v59/AB_ac_56*`): el cono de arista recta y la fila de dientes de la derecha DESAPARECEN; loma redondeada de hierba seca a la
  altura del ojo, sin roca ni aristas (recorte 1:1 `crop56_v55.png`, misma geometria en la isla); se ve mas linea de mar a la derecha. AC:
  pct_roca 43.5 -> 44.1 (la roca contada es la loma de la derecha y el primer plano), pct_azul 28.2 -> 29.5, cesped 0, bandas 0, riqueza
  2.20 -> 2.09 (la cupula es lisa). Normal: igual (cupula verde-matorral, una linea de estrato fina a la izquierda).
- **51** (piloto; `ab_v59_vs_mascara/AB_ac_51*` aisla mi cambio): la pared derecha cercana es IDENTICA; al fondo (110-130 m, s 1770-1830) el
  pico del cono pasa a loma de hierba y queda una losa de roca recortada + una franja estrecha. AC vs mascara r4: pct_roca 48.2 -> 46.5, riqueza
  2.39 -> 2.36, pared_lisa 19.3 -> 20.0, cesped/verde/bandas iguales; vs r3: roca 51.9 -> 46.5 (incluye la mitigacion de 'mascara'). Sigue
  siendo mejora fuerte contra la base (roca 5.0). Normal vs mascara r4: roca 19.1 -> 17.9, riqueza 2.73 -> 2.72.
- **07**: practicamente igual a la de 'mascara' r4 (AC: px distintos 2 %; roca 28.2 -> 28.1; normal riqueza 2.52 -> 2.51).

## r4.4 Parches / notas para otros

**Integrador** (`_rev/pipeline_escena.sh` l.84; opcional pero recomendado: que el log del pipeline ensene la condicion de la acotacion 1):
```bash
grep -E "KPI antes|invariantes|cupula 56" "$LOGS/medir_relieve.log" | cut -c1-420
```
Nada mas: `terreno_montana.py` y `medir_relieve.py` son mios y ya estan; el pipeline los usa tal cual (A1 y A3 aplicados en r1).
Puerta: respecto a la candidata r3 solo cambian 111 celdas (> 0.5 m), todas en la isla (x 20-66, y 470-560); sobre ellas en la candidata r3 solo
habia VEG_cipres.004 (dz -4.4) y CAMARA_heli.003; asentar los recoloca. Cualquier otro fallo nuevo de la puerta esta en terreno identico a r3.

**Mascara / acotacion 4 (constantes de umbral de roca)**: `ROCA_ATR_RUIDO` (0.08 -> 0.20), `ROCA_NZ_ZONA` (0.62) y `ROCA_NZ_ZONAS` VIVEN en
`mascara_terreno.UMBRALES` (los aplican `mascara_terreno` y `construir_pista.roca_zonas_nz`, propietario 'mascara'); `terreno_montana` los
importa y los re-exporta en `umbrales_roca()` -> `geometria_3d.json['extras']['umbrales_roca']` (`nz` 0.804 = `ROCA_UMBRAL_NZ`, `nz_zona` 0.62,
`atr_ruido` 0.20, `nz_zonas`, `origen` 'mascara_terreno.UMBRALES': comprobado en geom_v59). Sin cambios que pedir.

## r4.5 Pendiente honesto

- PyC 25 m baja 33.6 -> 32.4 % (las filas s 1906-1916 de la rama alta tenian pared gracias al cono): dentro de la acotacion (>= 30) pero no sube.
  PyC a 20 m 29.8 -> 25.7 (la cara visible de la cupula, <= 30 grados, no llega a +8 m a 20 m del borde): informativo.
- Lectura estricta de los '20 m superiores' (todas las caras): 32.8 % > 30 grados por el flanco trasero (r4.2): decision del coordinador.
- Fondo de 51: losa de roca recortada y franja estrecha en la transicion cupula / loma sur (detalle a 110-130 m); MENOR, F2 con el macizo.
- Mar de 56 0.8 % (F2, acotacion 1). Las copias `escena_*_v5x.blend` de `_rev/_tmp_terreno/r4/` (~50 MB cada una) se pueden borrar.
