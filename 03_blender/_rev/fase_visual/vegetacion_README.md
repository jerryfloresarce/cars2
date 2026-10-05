# Plan de vegetación por máscaras (`03_blender/vegetacion.py`) — fase visual F1, bloque 4.1

Propietario `vegetacion_plan`, 04/10/2026. Python del sistema (numpy + scipy + PIL), sin Blender. Lo pide
`FASE_VISUAL_PLAN.md` §7 punto 1 y `entender_vegetacion.md` §8.1. En F1 **solo se genera el JSON**: nadie lo consume
todavía (la integración en `integrar_escena.py` y el kit v3 son de F3; `PARCHES_F1_vegetacion_plan.md` dice cómo).

## 1. Qué hace

`python 03_blender/vegetacion.py` (5.4 s) lee `geometria_3d.json` + `urbanismo.json` + `urbanismo_spec.json`
(+ opcionales `renders/qa/huellas.json`, `renders/ab/_base_antes/camaras.json`, `texturas/terreno_mask.png`,
`bancales_spec.json`; hoy existen los tres primeros) y escribe:

- `03_blender/vegetacion_plan.json` (3.6 MB, md5 `57a50b65ae1e362e8d67cfa3721c7a6c` con la geometría del 04/10 12:57 y
  `terreno_mask.png` de las 16:28, md5 `a224738e...`; la máscara la está afinando su propietario: cada versión cambia el
  plan al re-ejecutar, y el paso del pipeline lo regenera solo).
- `renders/qa/vegetacion_mapa.png`: izquierda hábitats a 4 m (pinar / encinar / olivar / palmeral / matorral, rojo =
  no apto, gris = calles/edificios/muros/props); derecha el plan por especie con los círculos de las masas y las 12
  cámaras (6 de piloto + 5 postales + 59b).

API (importable desde python del sistema): `planificar(geom, urb, seed, cfg, spec, huellas, camaras, mask_png,
bancales_spec) -> (datos, plan, Z, exc)`, `zonas(geom, exc, cams_pts, mask_png) -> Z` (campos a 4 m y máscaras de
hábitat), `masas(zona, especie, radio_poisson, claros, plan, nombre, cz, cobertura_raster) -> (n_plantas, n_masas)`,
`verificar(datos, geom, urb, huellas) -> fallos`, `mapa_qa(datos, Z, exc, ruta)`. CLI: `--geom --urb --spec --salida
--qa-dir --seed --huellas --camaras --mask --bancales --cfg ajustes.json --sin-qa` (`QA_DIR` por entorno).

### Hábitats (reglas del plan, umbrales en `CFG['zonas']`; ha medidas CON la máscara del terreno)

| Zona | Regla (sobre la rejilla de 4 m) | ha | Especie | r Poisson | Masas |
|---|---|---|---|---|---|
| pinar | z 60-180 m, pendiente <= 0.70, no vaguada (z - z suavizada 40 m >= -6), roca <= 0.6 **o repisa** (roca > 0.6 y pend < 0.30) | 32.0 | pino | 4.0 m (x0.8 junto a cámaras) | R 62 m, cobertura 46 %, claros 0.6/ha, sueltos 0.35/ha |
| encinar | umbría (la ladera baja hacia +y, componente >= 0.25), pendiente 0.466-0.90 (25-42 grados), z 15-160 | 10.9 | encina | 4.6 m | R 52 m, cobertura 42 % |
| olivar | z 20-90, pendiente <= 0.45, a 12-90 m de solares/plazas/casas del pueblo (NO de pacas ni vallas) | 6.3 | olivo (+3 cipreses "acento" por masa) | 7.5 m | R 58 m, cobertura 60 % |
| palmeral | z 1.5-20, a < 60 m del mar, pendiente <= 0.40 | 11.9 | palmera | 6.5 m | R 42 m, cobertura 26 % |
| matorral | pendiente > 0.577 (30 grados) y <= 1.6, z > 2, roca <= 0.6 | 13.4 | matorral | 2.8 m | R 46 m, cobertura 75 % |
| sotobosque | bajo las huellas de las masas de pinar/encinar | - | matorral | 3.7 / 3.6 m | - |
| cipreses | a ambos lados de los senderos `CAMINO_tierra` (cada 9-14 m, a 4.6-6.2 m del eje), caminos de asfalto/adoquín del casino y del puerto (con palmeras), anillo de 8 alrededor de cada `ITAL_ermita` | - | cipres | 3.5 m | - |
| jardín casino | cuadrado de +-60 m en el centroide de las curvas 33/35/39 (lo que hoy hace `zona_casino` l.2097-2119) | - | adelfa, palmera, cipres, olivo, arbusto | 9 m | 1 masa |
| jardín hotel | anillo 10-26 m alrededor de `HOTEL_root` | - | palmera, adelfa, arbusto | 8 m | 1 masa |
| bordes de calle | a 2.3-3.2 m del borde de calles/travesías del plan y caminos de malla, cada 6-9 m | - | adelfa, arbusto | - | - |
| plazas | anillo 2.6-4 m FUERA de plazas y plazoletas (despeje_final quita lo de dentro) | - | adelfa, arbusto | - | - |
| bancales | `bancales_spec.json` (no existe aún; formato supuesto `{'bancales': [{'lineas': [...]}]}`) | - | olivo | 7-9 m | - |

Prioridad donde se solapan: encinar > olivar > palmeral > pinar > matorral. Masas: centros por disco de Poisson
(R_masa) en orden aleatorio hasta cubrir la fracción `cobertura` de la zona; forma elíptica alargada **a lo largo de la
curva de nivel** (eje mayor 0.55-0.85 R, menor 0.55-0.9 del mayor) con borde ondulado (3 armónicos) y borde
deshilachado (probabilidad 0.25-1 en el 30 % exterior); claros aleatorios de 6-14 m + claros explícitos (postal 56:
40 m); relleno por dardos con hash espacial (misma clase: distancia >= (r_a + r_b)/2; árbol-mata: >= 1.2 m, las matas
van bajo las copas; jardines: todo a >= r del jardín). Cada masa fija una variante dominante (70 %) y un tono base (70 %).

### Exclusiones (= lo que protegen los inspectores; todas se verifican al final)

Pista: distancia EXACTA a la polilínea de muestras >= w/2 + 12 m (también en puentes). Pit lane: w/2 + 8. Raster de
1 m con calles/travesías/enlaces/rampas (+relleno)/escaleras/pasarelas del plan, caminos de malla (`huellas.calles`),
solares, plazas, edificios de `huellas.casas` (hotel, tribunas, boxes, casino, ayuntamiento, ermitas...), muros
(plan + huellas, +-1.2 m), props con huella (pacas, vallas, postes, farolas, +1 m): tronco a >= 1.0 + 0.7 x radio de
copa (pino 4.85 m, olivo 3.45, adelfa 2.12). Duras: celdas de `PENON_roca` y `TUNEL_acantilado` (+1 m), zonas
excluidas del spec (McLaren + 4 m), Loews r 40 m, árboles que SE QUEDAN (`ITAL_`, `MIRADOR_`, `VEG_plazoleta`:
94, r 3 m), mar, `mascara_roca` > 0.6 salvo pinos en repisas, y los canales A (roca > 0.6) y B (tierra > 0.6) de
`terreno_mask.png` (fila 0 del PNG = y máximo, como documenta `mascara_terreno.py`; comprobado: correlación 0.52 del
canal A con `mascara_roca` y 0.63 con la pendiente en esa orientación, 0.03 en la contraria).

### Formato de `vegetacion_plan.json`

```
{"version": 1, "seed": 42, "generador", "notas", "cfg": {...CFG...}, "entradas": {...rutas relativas usadas...},
 "especies": {"pino": {"clase": "arbol", "alto_m": [16, 24], "alto_nominal_m": 18, "radio_copa_m": 5.5,
              "radio_poisson_m": 4.0, "paleta": "oliva_oscuro", "tonos": {"a": 1.0, "b": 0.85, "c": 1.15},
              "variantes": [...], "paleta_rgb_lineal": {...se recalcula desde paleta.json al ejecutar...}}, ...},
 "masas": [{"id", "zona", "especie", "cx", "cy", "r", "n", "tono", "variante"}, ...],
 "stats": {...},
 "plantas": [{"especie", "variante", "x", "y", "z", "rot", "escala_xy", "escala_z", "tono", "masa_id", "lod"}, ...]}
```
`x, y, z` metros de mundo Blender (z = terreno bilineal, SIN el hundimiento de asentar); `rot` radianes
(`rotation_euler.z`); `escala_*` relativas a `alto_nominal_m` de la especie (pino 18, encina 10, olivo 6, ciprés 12,
palmera 14, adelfa 3, arbusto 1.5, matorral 1.2); `tono` a|b|c = material `MAT_VEG_<especie>_<tono>` (factor de
luminancia sobre el color de paleta; **nada de RGB copiados**: si el usuario cambia `paleta.json`, re-ejecutar);
`masa_id` -1 = suelto o lineal; `lod` 0 (< 150 m de la pista) / 1 (< 400) / 2. Para `trees.txt` (FX): `pos = (x, z, -y)`,
`angle = grados(rot)`. Sin fechas, tiempos ni rutas absolutas: determinista byte a byte.

## 2. Resultado (geometría del 04/10 12:57 + terreno_mask.png 16:28, seed 42)

| Especie | n | vecino < 6 m | nn mediana | z > 80 m | z |
|---|---|---|---|---|---|
| pino | 5328 | 98 % | 4.3 m | 71 % | 59-180 m |
| encina | 1448 | 87 % | 5.0 m | 33 % | 14-141 |
| palmera | 453 | 1 % | 7.1 m | 2 % | 1-127 |
| olivo | 438 | 4 % | 7.8 m | 35 % | 20-117 |
| cipres | 85 | 22 % | 11.7 m | 54 % | 2-157 |
| **árboles** | **7752** (objetivo 6-9 k) | **84.2 %** (>= 70) | | **57.4 %** (>= 30; 4448) | |
| matorral | 15903 | | | | |
| adelfa / arbusto | 92 / 45 | | | | |
| **matas** | **16040** (15-20 k) | | | | |

Por zona: pinar 5328 (44 masas, mediana 116 árboles/masa), encinar 1448 (40, mediana 36), olivar 435 (23) + 6
cipreses de acento, palmeral 437 (23), matorral 8810 (158), sotobosque 5098 + 1995, cipreses lineales 75, jardines 74
(casino 62, hotel 12), plazas 23, bordes de calle 63, bancales 0. Masas con plantas: 289. LOD: 12826 / 9656 / 1310.
23 % de las plantas en la banda 20-120 m de las cámaras (ahí el radio es x0.8). Hábitats aptos 109.6 ha de 164 de tierra.

Verificación (automática al final y en `stats`): holgura mínima al borde de la pista **12.01 m** (0 puntos < 12),
al pit 8.5 m (>= 8), al core urbano 2.0 m (0 dentro), 0 en exclusión dura, 0 no-pinos sobre roca > 0.6, 0 en el mar,
0 dentro de solar/edificio (prueba independiente punto-en-polígono con los 418 polígonos). **Determinismo**: dos
ejecuciones con copias congeladas de las 6 entradas -> `cmp` idéntico (md5 `8452ec38...` las dos, con tiempos de 5.5 y
6.2 s); el entregado solo difiere de esas copias en las rutas de `entradas`. (Un `stats.tiempo_s` que yo metía en el
JSON rompía la igualdad byte a byte: quitado.) **Tiempo**: 5.4 s (exclusiones 0.3 s). Rasters: 2065x2057 a 1 m.
Sin `terreno_mask.png` (y mismos ajustes): 8959 árboles + 23.7 k matas (la máscara quita al encinar y al matorral las
laderas > 0.70 que ella marca como roca: apto 135.6 -> 109.6 ha); sin `huellas.json` ni cámaras el plan sigue (log).
Antes (asentar.json 13:00): 2.72 k raíces, nada por encima de 80 m, ~1 árbol cada 19 m.

## 3. Decisiones y avisos honestos

1. Olivos (r 7.5) y palmeras (r 6.5) nunca tienen vecino a < 6 m **por definición** (el plan pide 7-9 m en olivar); el
   KPI global (>= 70 %) se cumple gracias a pinar y encinar. Si se quiere, `--cfg` con `especies.olivo.r` 5.5.
2. Adelfas/arbustos con flor salen pocos (137): en las terrazas no hay sitio (fachada a 1 m de la calle, el lado exterior
   cae en pista + 12 m, los patios de 18-21 miden 3 m con la rampa del muro). Están en el jardín del casino, los anillos
   de plazas y los caminos del casino/puerto. Crecerán cuando el plan urbano traiga `aceras`/`patios` (bloque 5.2).
3. No hay cementerio en la escena: los cipreses van a senderos, ermitas (2), caminos del casino/puerto y acentos del olivar.
4. `huellas.json` es de la ÚLTIMA pasada del pipeline (revisar_urbanismo va después de integrar): un retraso de una
   regeneración en edificios no urbanos/props/rocas; lo que importa (hotel, tribunas, casino, rocas, caminos de malla)
   solo cambia con el relieve, y el plan se regenera en 5 s en cada pasada. Sin `huellas.json` el plan sigue (log).
5. Encinar hasta pendiente 0.90 (42 grados; con la máscara en la práctica <= ~0.75): asentar mueve/quita árboles con
   desnivel > 0.8/1.6 m en 1.2 m (0.96-1.08 m a esa pendiente: los mueve, no los quita). Si
   `asentar.json['arboles_quitados']` sube, bajar `zonas.encinar.pend[1]` a 0.80.
6. Presupuesto (decisión 8): 7.8 k árboles + 16 k matas con el kit v3 `sin_alfa` (60-120 tris/árbol, 30-50/mata) dan
   1.0-1.7 M tris, por encima de los 0.9 M del plan. El kit v3 debe quedarse en ~60 tris/árbol y ~15/mata (matorral de
   2-3 casquetes) O el integrador escala con `--cfg` (`zonas.matorral.cobertura` 0.45 y `sotobosque_r` 5 dejan ~10 k
   matas; `zonas.pinar.cobertura` 0.30 da 3.5 k pinos / 6.1 k árboles, probado) O los `lod` 2 (1.3 k) no se clonan.
   Se decide en F3 con `kn5_presupuesto.py`.
7. El plan NO cubre la vegetación propia de `roca_lazo`, `roca_casino`, `montana_mclaren` (MCOCHE_veg), ni las
   palmeras de `zona_meta`/`zona_paseo_mirador`, las `VEG_plazoleta` ni los `ITAL_cipres`/bancales de senderos: se
   quedan como están (y el plan los esquiva). Las 124 `VEG_roca` de `zona_montana` tampoco están en el plan
   (recomendación en el parche: las sustituyen los afloramientos del bloque 2.5).
8. `terreno_mask.png` apareció a las 16:23 y cambió a las 16:28 (propietario de la máscara, F1): el plan la usa desde
   entonces y cualquier cambio de `mascara_terreno.UMBRALES` cambia el plan al re-ejecutar (ambos deterministas). Los
   ajustes de cobertura están afinados CON la máscara; sin ella sobran matas (23.7 k).
9. La relación con `mascara_terreno.py` ("sombra de bosque" bajo las masas, `veg_plan=`): que lea `plantas` con
   `clase == 'arbol'` (en `especies[e].clase`) y oscurezca en un radio `1.2 x radio_copa_m x escala_xy`; `masas`
   (cx, cy, r) sirve para una versión rápida. El plan solo lee los canales A/B de la máscara (no la base): sin bucle.
10. Cuando el bloque 1 cambie el relieve (F2) el plan cambia solo al re-ejecutar (las máscaras de pendiente son del
    terreno actual); mismo seed -> mismo resultado sobre la misma geometría.

## 4. Cómo probarlo

```
cd 03_blender
python vegetacion.py                                       # escribe vegetacion_plan.json + renders/qa/vegetacion_mapa.png
python vegetacion.py --salida _rev/_tmp_x/p.json --qa-dir _rev/_tmp_x --seed 7     # prueba sin tocar nada
python vegetacion.py --cfg ajustes.json                    # {"zonas": {"pinar": {"cobertura": 0.3}}}
```
Salida 1 si la verificación final encuentra un punto a < w/2 + 12 m del eje, dentro de un solar/edificio o en el mar.
Determinismo: copiar las entradas a una carpeta, ejecutar dos veces con `--geom/--urb/--spec/--huellas/--camaras/--mask`
apuntando a las copias y `cmp` las dos salidas (si las entradas vivas cambian entre medias, el plan cambia: es lo esperado).
