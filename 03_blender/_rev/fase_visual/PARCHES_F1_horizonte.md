# Parches F1 — bloque 7.1 HORIZONTE (propietario 'horizonte', 04/10/2026)

Anillo de horizonte `HORIZ_*` (cordilleras lejanas en dos planos, lomas de costa, islotes, pueblecitos-silueta y faro)
construido por `03_blender/assets/montanas_fondo_v2.py :: build_anillo_horizonte()` (kit aprobado en `v2_aprobados.txt`;
`test_montanas_fondo_v2.py` seccion 5 = TEST_OK, previews `assets/previews/montanas_v2_horizonte_{planta,oblicua,piloto_O,piloto_S}.png`).
Los parches de abajo son EXACTOS; los aplica el integrador en ficheros que no son mios. Orden: P-H1 (integrar_escena) ->
P-H2..P-H5 (inspectores) -> P-H6 (peticiones X, fichero del bloque 0).
Ensayo sin regenerar (lo que hara P-H1, sobre una COPIA):
`bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/_tmp_horizonte/construir_horizonte_copia.py -- <escena.blend> <copia_salida.blend> <geometria.json>`
escribe `<copia_salida>.json` (tris, mallas, materiales, idempotencia con `mejorar_materiales.horizonte()`); el marcador de
exito es la linea `HORIZ_COPIA_OK` (Blender devuelve 0 aunque el script falle).

Convenciones del kit que importan al integrador:
- Todos los objetos son MALLAS RAIZ sin padre: 9 `HORIZ_cordillera[.NNN]` (picos + cordal fundidos), 9 `HORIZ_loma[.NNN]`
  (pico + penasco fundidos; r3: 4 costa + 4 islotes + 1 'ventana'), 3 `HORIZ_pueblo[.NNN]`, 1 `HORIZ_faro` -> 22 mallas,
  197 690 tris, 14 materiales `MAT_HORIZ_*` (r2: 21 mallas, 182 890 tris).
- Custom props en objetos: `horiz_fila` (cerca | lejos | loma_costa | loma_islote | loma_ventana | pueblo | faro), `horiz_az`
  (grados matematicos desde el centro de la rejilla, 0 = +X, 90 = +Y), `horiz_r` (m).
- Materiales `MAT_HORIZ_<fila>_<sufijo>` (cerca: bosque, bosque_claro, cumbre, cumbre_clara, cumbre_oscura; lejos: bosque,
  cumbre, cumbre_clara; loma: los 5) y `MAT_HORIZ_pueblo`: Base Color SIN enlazar = diffuse_color = media lineal = color
  de `paleta.json` (oliva_oscuro, salvia, caliza_ocre, caliza_ocre x1.25, caliza_sombra; fila lejana: caliza_gris_calido;
  pueblo: fachada_blanco_roto) mezclado con el color del horizonte del world `CIELO` (se LEE del world; 35 % a 2.4 km ..
  55 % a 4.5 km). Custom props `ac_shader='ksPerPixel'`, `ac_props={}`, `ac_samplers={}`, `ac_tex_max=512`,
  `ac_alpha_test=0`, `ac_raw=0` (= comportamiento actual del writer), `horiz_dist_m`, `horiz_base_rgb` y
  `horiz_color_base` (= color de paleta SIN mezclar: es lo que lee `mejorar_materiales.horizonte()`, que recalcula la
  misma mezcla en el paso siguiente del pipeline; comprobado idempotente sobre la copia: dif max 0.0073 lineal).
  `aplicar_texturas.familia_de` -> None (no se texturizan), `mejorar_materiales.es_objetivo` -> False,
  `ajustar_montanas` no los toca (solo `MAT_MONT_*`), `color_ac.familia` -> 'pintado' (sin 'roca'/'bosque' en reglas).
- Geometria: centro = centro de la rejilla `T` = (99.1, 120.2); fila cercana a 3.2 km (4 cordilleras, alto 380-460,
  linea_arboles 1.2 = casi todo bosque, 73 % de caras), fila lejana a 4.5 km (5 cordilleras, alto 440-520, 57 % de
  caras de cumbre); anillo de 200 grados abierto 160 grados centrado en brujula 202.5 (S/SO): en grados matematicos el
  anillo va de 327.5 a 167.5 pasando por el N (cobertura angular 98.5 %); 4 crestas de costa a 2.4-2.8 km (2 por
  extremo; la exterior entra 10 grados en la abertura), 4 islotes dentados de 110-150 m (r3; r2: 55-80 m) DENTRO de la
  abertura (az 212.5, 227.5 con el faro, 249.5, 279.5 con pueblo; mar abierto entre ellos) y 1 loma 'ventana' (r3) en
  az 208 a 2.69 km (hueco de la linea mar/cielo de 57); pueblos en las costas O (az 177.5) y E (317.5) y en el islote S.
  Cordilleras sin picos 'aguja' y con radio x1.5 (r3). Pie de todo a z = -6 (bajo AGUA_fondo -4.05 y bajo el mar);
  distancia minima al centro 2244 m (semidiagonal de la rejilla 1460 m). El kit LANZA ValueError si algun vertice cae
  dentro de la rejilla.

---

## P-H1 · `03_blender/integrar_escena.py` · `zona_montanas_fondo` (l.2486-2495) -> `zona_horizonte`

**Que**: sustituir el `return` de la ronda 15 por la construccion del anillo. `M['montanas_fondo']` ya es
`montanas_fondo_v2` (via `assets/v2_aprobados.txt`). Se construye DIRECTAMENTE en `root_col` (mallas raiz con
location/rotation propias; no hace falta `clone` ni LIB).

**Insertar ANTES de `def zona_montanas_fondo():` (l.2486)**:

```python
def zona_horizonte(mf):
    """Fase visual F1 (bloque 7.1): anillo de horizonte HORIZ_ (cordilleras lejanas en dos planos a 3.2/4.5 km, lomas de
    costa e islotes a 2.4-2.8 km, pueblecitos-silueta y faro) fuera de la rejilla del terreno, abierto 160 grados al S/SO.
    Materiales MAT_HORIZ_* planos con la perspectiva atmosferica horneada (paleta.json mezclada con el color del
    horizonte del world CIELO); mejorar_materiales.horizonte() la recalcula despues desde mat['horiz_color_base'].
    Parche PARCHES_F1_horizonte.md P-H1."""
    if not hasattr(mf, 'build_anillo_horizonte'):
        log('horizonte: montanas_fondo_v2.build_anillo_horizonte no disponible: sin anillo')
        return
    res = mf.build_anillo_horizonte(root_col, terreno=T, seed=42)
    ab = res['abertura']
    log('horizonte: %d objetos HORIZ_, %d tris, %d materiales MAT_HORIZ_, %d cordilleras + %d lomas + %d pueblos + %d faro; '
        'anillo %.1f..%.1f grados (abertura %.0f grados centrada en brujula %.1f); cielo %s'
        % (len(res['objetos']), res['tris'], len(res['materiales']),
           len(res['cordilleras']), len(res['lomas']), len(res['pueblos']), len(res['faros']),
           ab['anillo_ini'], ab['anillo_fin'], ab['grados'], ab['centro_brujula'], tuple(round(c, 3) for c in res['cielo'])))
```

**Sustituir (l.2491-2495)**:

```python
    if G.get('cumbres'):
        # RONDA 15: el terreno YA es un macizo con cumbres (terreno_montana.py): fuera las
        # cordilleras postizas y los penascos-cilindro de las cimas
        log('montanas de fondo: el macizo va en el terreno (%d cumbres), sin cordilleras ni penascos' % len(G['cumbres']))
        return
```

**por**:

```python
    if G.get('cumbres'):
        # RONDA 15: el terreno YA es un macizo con cumbres (terreno_montana.py): fuera las
        # cordilleras postizas y los penascos-cilindro de las cimas.
        # FASE VISUAL F1 (7.1): en su lugar, el ANILLO DE HORIZONTE lejano (fuera de la rejilla)
        log('montanas de fondo: el macizo va en el terreno (%d cumbres), sin cordilleras ni penascos' % len(G['cumbres']))
        zona_horizonte(mf)
        return
```

(`root_col`, `T`, `log` son los globales del integrador.) El `safe('zona_montanas_fondo', ...)` existente captura cualquier
excepcion (p. ej. el ValueError del kit si el anillo cayera dentro de la rejilla) y la deja en `integrar_escena.log` como
ERROR. NO pasar `mejorar_materiales.horizonte` como `mezcla=` (es un pase de escena con otra firma; ya se ejecuta dentro
de `mejorar_blend()` en el paso siguiente del pipeline).

**Como probarlo**: `integrar_escena.log` contiene `[integrar] horizonte: 22 objetos HORIZ_, 197690 tris, 14 materiales
MAT_HORIZ_, 9 cordilleras + 9 lomas + 3 pueblos + 1 faro` (r3; en r2 era 21 / 182890 / 8 lomas) y `OK zona_montanas_fondo`;
`mejorar_materiales` imprime `HORIZONTE: 14 materiales mezclados`; en el A/B del set BASE las tomas 13/21/57 muestran la
silueta sobre la linea mar/cielo y 54/61/63 los islotes; `python 03_blender/_rev/_tmp_horizonte/medir_horizonte.py <antes> <despues> <camaras.json> --alt-min 10`
reproduce las cifras de referencia de la seccion 'ronda 3' (+-3 puntos). APLICADO en r2 (l.2495-2522): en r3 NO cambia
(misma llamada `build_anillo_horizonte(root_col, terreno=T, seed=42)`; la nueva configuracion vive en `CFG_ANILLO` del kit).

---

## P-H2 · `03_blender/revisar_flotantes.py` · `EXENTOS` (l.43)

**Sustituir** `'MONT_pena',` **por** `'MONT_', 'HORIZ_',` en la tupla `EXENTOS` (l.43). `es()` compara por subcadena en
minusculas: cubre `HORIZ_cordillera`, `HORIZ_loma`, `HORIZ_pueblo`, `HORIZ_faro` (y cualquier `MONT_*` futuro). Motivo: el
anillo nace con el pie a z -6 sobre el mar, fuera de la rejilla: para el inspector seria "flotante/enterrado".
**Prueba**: `revisar_flotantes` sobre la escena con anillo no lista ningun `HORIZ_` ni cambia su z.

## P-H3 · `03_blender/eliminar_sumergidos.py` · bucle principal (l.30)

Hoy `PREFIJOS` no incluye `HORIZ_` (no se borraria), pero el anillo tiene `zmin = -6 < -1.0` a proposito (pie bajo el
mar). Para que ningun cambio futuro de `PREFIJOS` lo borre, **insertar tras la l.29** (`continue  # ya borrado...`):

```python
    if ob.name.startswith(('HORIZ_', 'MONT_')):
        continue  # fase visual F1 (7.1): anillo de horizonte con el pie hundido a z -6 a proposito (bajo el mar)
```

**Prueba**: `SUMERGIDOS BORRADOS:` no lista ningun `HORIZ_`.

## P-H4 · `03_blender/asentar_objetos.py` · `ASENTAR_NO` (l.159)

`HORIZ_` no esta en `ASENTAR_PREF` (no se asienta), pero por si se amplia: **anadir** `'HORIZ_'` al final de la tupla
`ASENTAR_NO` (l.159-160): `..., 'CALLE_toldo_mercado', 'ITAL_bancal', 'HORIZ_')`. No va en `SOPORTE_PREF` (nada se apoya
en el). `despeje_final` (`DESPEJE_ARBOL`/`DESPEJE_PROP`/`EDIF_PREF`) no lo toca: sin cambio.
**Prueba**: `asentar.json` no contiene entradas `HORIZ_`.

## P-H5 · `03_blender/_rev/nada_en_pista.py` · `PERMITIDOS` (l.34-37)

**Anadir** `'HORIZ_'` a la tupla `PERMITIDOS` (p. ej. tras `'CAMINO_enlace'`). Los objetos estan a >= 2185 m del centro de
la rejilla (nunca sobre la calzada), pero asi el inspector no evalua 21 mallas de hasta 20 k tris cada una.
**Prueba**: `nada_en_pista.json` sin `HORIZ_` y con el mismo total que la linea base (<= 11).

## P-H6 · `03_blender/_rev/fase_visual/PETICIONES_04_EXPORT.md` · P6 ([W], bloque X)

P6 ya cita `HORIZ_` en tokens sin sombra y en `NO_OBSTACULO`. **Anadir** como sub-vineta de **P6**:

```
  - P6-horizonte (F1, 7.1): `kn5_writer_opt.DECO_SIN_SOMBRA += ('HORIZ_',)` y `kn5_writer_b.SIN_SOMBRA_TOKENS += ('HORIZ',)`
    (castShadows = 0: 22 mallas de ~200 k tris a 2-5 km no deben entrar en el shadow map); `revisar_fisica_ac.NO_OBSTACULO
    += ('HORIZ_',)` (decorado, nunca a < 2 km de la pista); P9: ya van fundidas por cordillera/loma (22 mallas, 14
    materiales planos sin textura), sin trocear. Prueba: `kn5_check` lista 22 nodos `HORIZ_*` con castShadows 0;
    `revisar_fisica_ac` 0 "visibles no fisicos" nuevos; `kn5_presupuesto` familia HORIZ_ 197 690 tris.
```

(APLICADO en r2 en `PETICIONES_04_EXPORT.md` P6 con las cifras de r2: en r3 solo cambian los numeros, 21 -> 22 mallas y
182 890 -> 197 690 tris; lo corrige el integrador al pasar.)

---

## Cifras de referencia (ensayo sobre copia de `escena_rev.blend` del 04/10 13:00, camaras congeladas de `renders/ab/_base_antes/camaras.json`)

Ficheros: `03_blender/_rev/_tmp_horizonte/` (`escena_horiz.blend` + `.json`, `ab/{antes,despues,antes_ac,despues_ac}`,
`ab/AB_*.png`, `ab/hoja_ab_piloto.png`, `ab/hoja_ab_aereas.png` (+ `_ac`), `ab/medidas_horizonte.json`, `ab/medidas.json`,
`ab14/` toma 14, `copia.log`, `test_kit.log`).

- Anillo: 21 mallas, 182 890 tris (<= 250 k), 14 materiales (escena 484 -> 498 <= 520), 2.4 s de construccion; escena
  4 450 279 -> 4 633 169 tris (contados en Blender sin LIB). Ningun vertice bajo z -6 ni dentro de la rejilla.
- Mezcla con el cielo medida en el render de 54: islote (160, 185, 194) sRGB frente a cielo (213, 237, 255) y mar
  (191, 224, 249): la silueta es mas oscura que el cielo (ganancia de luz de la escena K ~1.0-1.3 por canal).
- KPI "silueta en la linea mar/cielo" (`medir_horizonte.py`, umbral 12; modo Blender / modo AC):

| toma | linea mar/cielo visible | silueta (% de esa linea) | mar abierto | nota |
|---|---|---|---|---|
| 13_puente_alto | 99 % | 42.9 / 42.4 | 57 % | anillo O + costa; altura media 54 px |
| 21_montana_dentro_del_lazo | 67 % | 66.4 / - | 34 % | anillo N/E |
| 57_postal_viaducto | 88 % | 32.3 / - | 68 % | extremo O del anillo + islote 212.5 |
| 61_orilla_piloto_s150 | 78 % | 29.8 / - | 70 % | islotes 212.5 y 227.5 (faro) |
| 54_piloto_s4150 | 54 % (resto = pared de roca) | 21.7 / 10.4 | 78 % | islotes; el extremo del anillo queda detras de la pared |
| 63_horizonte_piloto_s2200 | 54 % | 1.6 / 1.4 | 98 % | mira al centro de la abertura; islote 227.5 a 20 px |
| 56_postal_cima_bahia | 45 % | 0.0 / 0.0 | 100 % | mira a la abertura; islote S queda bajo la linea (camara a 122 m) |
| 49_piloto_s300 | 0.2 % | n/a | - | sin linea mar/cielo (tunel + McLaren) |
| 52_piloto_s2900 | 0 % | n/a | - | horizonte (0 grados) tapado por el terreno (skyline a 7-12 grados) |
| 36_roca_casino_general | 0 % | n/a | - | el horizonte no entra en el cuadro: no tapa el casino |
| 14_puente_mar | 0 % | n/a | - | mira al viaducto/penon desde el mar: sin linea mar/cielo |

- `medir_capturas`: `pct_azul` delta +3.1 (13), +1.4 (57), 0 +-0.3 en el resto; `riqueza` sube en todas (+0.14..+0.95).
- CONFLICTO documentado: el objetivo "silueta >= 60 % en 49/52/54/56" es geometricamente incompatible con "anillo abierto
  160 grados al S/SO y mar abierto desde 54": 49/52 no ven la linea mar/cielo (horizonte tapado por terreno cercano), y
  la mitad visible de la linea en 54 (az 187-227 desde la camara) y toda la de 56/63 miran al centro de la abertura. Lo
  aplicado: abertura literal (brujula 202.5 +-80) + 4 islotes bajos dentro de ella (21.7 % en 54 con 78 % de mar abierto).
  Si el usuario prefiere mas silueta en 54/63/56, `build_anillo_horizonte(..., abertura=110, abertura_centro=215)` o mas
  `islotes_az` lo cambian sin tocar codigo (parametros de `CFG_ANILLO`); decision del coordinador/usuario.

---

## RONDA 3 (04/10 ~22:15) — director_f1_r2.md problema 7 (MENOR, horizonte + coordinador) y 10 (COSMETICO, horizonte)

Ficheros mios cambiados: `assets/montanas_fondo_v2.py` (CFG_ANILLO + kw `ensanche` en build_cordillera + lomas 'ventana'),
`assets/test_montanas_fondo_v2.py` (seccion 5: 6-10 lomas, regla de la loma 'ventana', prohibido 'aguja'; TEST_OK 22:13,
previews `montanas_v2_horizonte_*` regeneradas), `_rev/_tmp_horizonte/medir_horizonte.py` (`--alt-min`: columna "legible"
solo si la silueta sube >= N px sobre la linea), `_rev/_tmp_horizonte/construir_horizonte_copia.py` (la copia de ensayo
conserva los colores de `mejorar_materiales.horizonte()`, que es lo que ve el pipeline). Ensayo en `_rev/_tmp_horizonte/r3/`
(`escena_horiz_r3.blend` = COPIA de `escena_rev.blend` a6fb4195 + anillo r3; `ab/{antes,antes_ac}` = `_base_antes`
congelado, `ab/{despues,despues_ac}`, `AB_*.png`, `AB_ac_*.png`, hojas, `medidas_horizonte{,_ac}.json`, `medidas{,_ac}.json`;
`ab14/` toma 14; `v1/` = primer intento con ensanche 1.35 y mas piramides, descartado por picos aun puntiagudos en 55).

### Que cambia en el anillo (todo en `CFG_ANILLO`; la llamada del integrador NO cambia)

1. **Islotes mas altos, misma huella** (problema 7, tomas 63 y 57): `islote_alto` 55-80 -> 110-150 m, `islote_radio`
   150-200 -> 140-190 m. Motivo con cifras: desde 63 (camara a z 72, lente 20 = 16.8 px/grado) un islote de 70 m a 2.6 km
   asomaba 0.3 grados = 4 px sobre la linea mar/cielo (director: 6.5 %); con 110-150 m asoma 18-36 px. El mar abierto
   ENTRE islotes no cambia (misma huella horizontal).
2. **Loma 'ventana'** (problema 7, toma 57): `lomas_ventana=(40.5,)` = 1 cresta de 122 m (radio 201, largo 464) en az 208
   (matematico, desde el centro de la rejilla) a 2.69 km, clase `loma_ventana`. Es el hueco de la linea mar/cielo de 57
   entre la roca del lazo (x 600) y el islote 212.5 (x 418): desde 57 queda en x 500-610; desde 54 asoma pegada a la
   pared del lazo (x 700-860, ver AB_54); desde 63 cae en x ~1390 (entre los arboles de la derecha); 56 y 61 no la ven
   (fuera de su ventana); 14 no ve el anillo (0.000 % de pixeles cambiados). Esta a 39.5 grados del centro de la
   abertura (regla nueva del test: >= 30). Para quitarla: `lomas_ventana=()`.
3. **Picos sin aguja y mas anchos** (problema 10): `tipos=("domo","cresta","meseta","domo","cresta","piramide")` (sin
   'aguja': sus gendarmes tienen alto/radio ~3.5 y a 3-4.5 km se leian como agujas; 1 piramide de cada 6) barajados por
   cordillera, y `ensanche=1.5` (nuevo kw de `build_cordillera`: radio de cada pico x1.5 con la misma altura; alto/radio
   de la fila trasera 2.2 -> 1.5). Quedan puntas en las crestas vistas de canto (55, derecha de 57): son triangulos
   anchos, no agujas; si el usuario las quiere aun mas romas, `tipos` sin "cresta" o `ensanche` 1.7 (una linea). La
   mezcla de color NO se toca (la del pipeline es `mejorar_materiales.horizonte()`, bruma #9499B0, V 0.59-0.63).

### Cifras (COPIA de escena_rev + anillo r3, camaras congeladas de `_base_antes`, modo Blender; `medir_horizonte.py
--umbral 14 --alt-min 10`; "r2" = mi ensayo de r2 con la misma metrica; "legible" = columnas con silueta >= 10 px)

| toma | linea mar/cielo visible | silueta r2 -> r3 (% de la linea) | legible r3 | mar abierto r3 | alt. max px r2 -> r3 |
|---|---|---|---|---|---|
| 13_puente_alto | 99 % | 42.9 -> **52.3** | 50.3 | 47.7 % | 124 -> 115 |
| 21_montana_dentro_del_lazo | 67 % | 66.4 -> **95.4** | 85.7 | 4.6 % | 64 -> 64 |
| 57_postal_viaducto | 88 % | 32.3 -> **42.0** | 36.1 | 58.0 % | 113 -> 87 |
| 61_orilla_piloto_s150 | 78 % | 29.8 -> **34.8** | 26.5 | 65.2 % | 43 -> 93 |
| 54_piloto_s4150 | 54 % (resto pared del lazo) | 21.7 -> **41.1** | 29.6 | 58.9 % | 30 -> 65 |
| 63_horizonte_piloto_s2200 | 54 % | 1.6 -> **17.6** | 4.6 | 82.4 % | 4 -> 36 |
| 56_postal_cima_bahia | 45 % | 0.0 -> 5.9 | 3.1 | 94.1 % | 0 -> 18 (islote S; la loma del terreno sigue tapando la bahia) |
| 49 / 52 / 36 / 01 / 14 | 0 % | n/a | - | - | sin linea mar/cielo en el cuadro (49 tunel + McLaren, 52 terreno a 7-12 grados, 36/01 horizonte fuera del cuadro, 14 mira al viaducto); 14: 0.000 % px cambiados |
| 55_postal_tunel_salida | 0 % | silueta sobre el cielo 28.4 -> 30.8 % del ancho | - | - | agujas -> domos/meseta/crestas (comparar `v1/` con `ab/`) |

Media 13/21/57/61 (las 4 tomas con linea mar/cielo que miran al anillo o a sus extremos): 42.9 (r2) -> **56.1 %** (r3).
Modo AC: mismas siluetas donde la deteccion de la linea coincide (13 52.2, 21 95.4, 57 41.7, 63 18.0, 56 5.9); en 54/61/49/52
el "antes" AC clasifica la caliza al sol como azul y `pct_linea_visible` sale distinto (54 100 %, 61 19 %): la geometria es
identica, vale la fila de modo Blender. `medir_capturas` (`medidas.json`): `pct_azul` 13 +4.8, 21 +5.4, 57 +2.6, 54 +1.0,
55 +1.0, 61 +0.5, resto <= 0.2; `riqueza` +0.2..+0.9 en todas las de piloto; `bandas_blancas` 0 nuevas; 01 sin cambio
(-0.01). Color (modo AC, muestras de `despues_ac` en `r3/pixeles_ac.txt`): islotes y loma ventana mas oscuros que el cielo
(54 islote #8192B8 V 0.72 y #B2C1E5 V 0.90 frente a cielo #C8E5FF V 1.00; 57 loma ventana #8D9EC8 V 0.78; 63 islotes
#A1AFD4 / #A8B7DF V 0.83-0.87 frente a #C9E5FF); px #FFFFFF NUEVOS en las filas 100-420 respecto al antes AC: 57 0, 63 0,
13 0, 54 0, 21 9 px en (725, 370) = zona de casas bajo el anillo (el anillo en 21 ocupa las filas 0-130), no HORIZ_; los
blancos que ya existian (63 768 = globo, 13 513 = roca del lazo al sol, 57 92-105 = dirigible) no cambian. Presupuesto: 22
mallas, **197 690 tris** (<= 250 k; r2 182 890), 14 materiales (escena
484 -> 498), construccion 2.2 s; test del kit TEST_OK (cobertura angular 98.5 %, fila cerca 87.7 % bosque, lejos 46.6 %
cumbre, 0 cordilleras con 'aguja', d_min al centro 2244 m, ningun vertice dentro de la rejilla ni bajo z -6).

### PETICION AL COORDINADOR: re-escribir el KPI del bloque 7 (plan 9 / tabla 16 "horizonte en 49/52/54/56 >= 60 %")

Tal como esta escrito es incumplible por geometria, no por falta de anillo: 49 y 52 no tienen linea mar/cielo (tunel +
McLaren; terreno a 7-12 grados), y la linea visible de 54 (az 205-239 desde el centro) y de 56/63 (210-306 / 195-282) ES la
abertura de 160 grados decidida en 7.1 ("desde 54 y 14 se sigue viendo mar abierto"). Lo unico que cabe en 54/63 sin
cerrar la abertura son islotes (ya 41 % / 18 %). Propuesta (la del director r2, con cifras):
- KPI nuevo: "silueta `HORIZ_` en la linea mar/cielo de 13, 21, 57 y 61: media >= 50 % (metrica del director, banda de 60 px
  por columnas; con `medir_horizonte.py` r3 da 56.1 % de media: 13 52 / 21 95 / 57 42 / 61 35)" + condicion de la decision
  7.1: "mar abierto >= 50 % de la linea visible en 54 y 63 (r3: 58.9 % y 82.4 %)". 54/56/63 pasan a informativos.
- 57 no puede llegar al 60 % sin cerrar la mitad O de la abertura: su linea de mar (az 205-232 desde el centro) es el
  mismo mar que ve 54 (205-239); cada loma que se anada en la ventana de 57 aparece tambien en 54 junto a la pared
  del lazo. Si el usuario prefiere mas silueta que mar en 57/54: `lomas_ventana=(40.5, 52.0)` (2 lomas; la segunda
  cae en az 219.5, entre los dos islotes de 54) o `abertura=120` en `CFG_ANILLO` (una linea; decision de usuario).
- 56 depende del despeje del cono de la postal (bloque 1, terreno): con la camara congelada la loma del terreno tapa la
  bahia; el islote S (az 249.5) ya asoma 18 px a la derecha.

### Para el integrador (ninguna linea de codigo nueva)

- P-H1..P-H5 ya aplicados en r2; la llamada `build_anillo_horizonte(root_col, terreno=T, seed=42)` recoge sola la
  configuracion r3. Esperar en `integrar_escena.log`: `horizonte: 22 objetos HORIZ_, 197690 tris, 14 materiales
  MAT_HORIZ_, 9 cordilleras + 9 lomas + 3 pueblos + 1 faro`.
- P-H6 / `PETICIONES_04_EXPORT.md` P6-horizonte: actualizar 21 -> 22 mallas y 182 890 -> 197 690 tris (texto arriba).
- `kn5_presupuesto` (problema 9 del director): familia HORIZ_ = 197 690 tris; escena de ensayo 4 450 279 -> 4 647 969
  (sin LIB; la candidata r2 tenia +182 890).

## RONDA 4 (05/10 ~00:15) — ACOTACIONES_COORDINADOR_F1.md n.º 2 (KPI re-escrito + 1 loma + picos romos) y director_f1_r3.md n.º 6 (MENOR) y n.º 9 (COSMETICO)

Ficheros mios cambiados: `assets/montanas_fondo_v2.py` (tipo de pico `lomo`, `_cumbres_cresta(suave)`, `build_loma(tipo_largo=)`,
`CFG_ANILLO` r4, loma de dimensiones fijas en `build_anillo_horizonte`), `assets/test_montanas_fondo_v2.py` (seccion 5: 10 lomas,
sin aguja/piramide/cresta, loma fija az 200; TEST_OK 00:05, previews `montanas_v2_horizonte_*` regeneradas), `_rev/_tmp_horizonte/`
(`medir_horizonte.py` con la metrica del director (campos `dir_*`), `banda_director.py` nuevo (solo esa metrica, `--runs` = tramos por
columnas), `construir_horizonte_copia.py` con `--quitar-horiz` y `--sin-anillo`). Ensayo en `_rev/_tmp_horizonte/r4/`:
`escena_sin_anillo_r4.blend` = COPIA de `escena_candidata.blend` (23:10) SIN los 22 HORIZ_ de r3 (es el "antes": mismo terreno r3),
`escena_horiz_r4.blend` = la misma + anillo r4; `ab/{antes,antes_ac,despues,despues_ac}` (10 tomas: 54/57/13/21/61/63/55/56/58/01,
camaras congeladas de `_base_antes`), `AB_*.png`, `AB_ac_*.png`, hojas, `medidas_horizonte{,_ac}.json`, `medidas_director{,_ac}.json`,
`medidas{,_ac}.json`, `cmp_r3_r4b_*.png` (recortes r3 arriba / r4 abajo de 55, 21, 57, 13, 54, 63, 61), `r4a/` = primer intento
(loma 120 m, con mesetas, islotes 110-150: descartado, cifras abajo), `test_kit.log`, `copia.log`. La mezcla de color NO se toca
(`mejorar_materiales.horizonte()` manda, igual que en r3; `copia.log`: 14 materiales, bruma del propietario materiales).

### Que cambia en el anillo (todo en `CFG_ANILLO` + 1 tipo de pico nuevo; la llamada del integrador NO cambia)

1. **Picos romos (director n.º 9, agujas en 55/57/13/21)**: tipo nuevo `lomo` = cresta ROMA (perfil convexo del domo, linea de
   cumbres suave con 1-3 lomas anchas y collados someros H >= 0.70, casquete `domo`, sin corona dentada ni espolones claros). Se da de
   alta DESPUES de `TIPOS` a proposito: no entra en el sorteo de `_elegir_tipo` (el acantilado del tunel de `integrar_escena` l.3076
   sigue igual) ni en las secciones 1-4 del test. Cordilleras: `tipos=("domo","lomo","domo","lomo","domo","lomo")` (sin cresta ni
   piramide, que eran los triangulos de canto; tampoco meseta: a 3-4.5 km sus paredes verticales y la cima plana se leian como
   losas apiladas en 21 y 55) y `ensanche=1.7` (r3 1.5). Lomas (costa, ventana, islotes): tipo `lomo` y SIN el penasco-torre de
   la cima (`lomas_pena=False`: a 2.5 km era una torre/bloque en 54, 57, 63, 55); misma huella y mismos sorteos que en r3.
   `islote_alto` 110-150 -> 110-140 (227.5: 125 -> 121 m; 212.5: 148 -> 138 m; los otros dos casi igual): con la cima redonda la
   cumbre ocupa mas columnas y desde 54 superaba los 60 px de la regla del director (ver cifras). El faro sigue en el islote 227.5.
2. **1 loma mas en la ventana de 54 (acotacion n.º 2)**: `lomas_ventana_fijas=((32.5, 2650.0, 100.0, 230.0, 600.0),)` = loma
   `HORIZ_loma.009` (clase `ventana`) en horiz_az 200 (= a_fin + 32.5; la "brujula 190-215" del director es `horiz_az`), 2 650 m,
   100 m de alto, radio 230, largo 600, construida la ULTIMA (dimensiones fijas, sin sorteo: no mueve las 9 lomas aprobadas en r3).
   Desde 57 rellena el hueco de mar entre la loma ventana 208 y la roca del lazo (x 611-734 en `despues_ac/57`); desde 13 el hueco de
   la izquierda (x 193-365); desde 54 queda DETRAS de la pared del lazo (x >= 860): 54 no pierde mar abierto (acotacion: >= 50 %);
   desde 63 fuera del cuadro (tras los arboles de la derecha). r4a con 120 m: desde 13 (z 120, lente 30 = 24 px/grado) la silueta
   media 66 px y la regla "<= 60 px" del director la descartaba en el centro; con 100 m mide ~55 px (y 41 px desde 57).
3. **Metrica del director implementada** (`medir_horizonte.py` campos `dir_*` y `banda_director.py`): sobre el 'despues' solo, por
   columna, ULTIMO px de cielo (H 196-216, S < 0.19, V >= 0.93) y PRIMER tramo de >= 3 px de mar (H 184-214, S >= 0.19, V >= 0.88);
   linea visible si estan a <= 60 px; silueta si entre ambos hay >= 2 px HORIZ_ (H 212-236, S 0.19-0.56, V 0.42-0.93). Calibrada
   sobre `renders/ab/f1_r3/despues_ac` frente a las cifras del director r3: 54 41.2 (el 43.2), 57 25.6 (28.4), 13 14.7 (15.6), 58 5.9
   (8.5), 56 7.3 (1.7); r2: 54 33.6 (34.8), 57 3.0 (3.4), 63 8.6 (6.5). Consecuencia de esa regla: NO cuenta ninguna silueta mas alta
   que 60 px (cordilleras a 3-4.5 km, cumbres de islote, torres, faro) ni columnas con terreno cercano; en 21 solo deja 1-33 columnas
   (el director dio 100 % de 86: su implementacion no es exactamente esta).

### Cifras (modo AC; "antes" = copia de la candidata sin anillo; r3 = `f1_r3/despues_ac` medido con el MISMO antes y las MISMAS metricas)

| toma | director (gap 60 px): silueta / mar abierto r3 -> r4 | mia (A/B, umbral 14): silueta / mar abierto r3 -> r4 |
|---|---|---|
| 54_piloto_s4150 | 41.2 / 58.8 (337/817) -> **39.2 / 60.8** (305/779) | 38.3 / 61.7 -> **41.6 / 58.4** |
| 57_postal_viaducto | 25.6 / 74.4 (216/845) -> **44.2 / 55.8** (367/831) | 41.9 / 58.1 -> **51.5 / 48.5** |
| 13_puente_alto | 14.7 / 85.3 (116/788) -> **33.6 / 66.4** (226/673) | 52.2 / 47.8 -> **51.8 / 48.2** |
| 21_montana_dentro_del_lazo | 78.8 (26/33 col; director r3: 100 % de 86) -> n/a (1 col) | 95.4 -> **100.0** |
| 61_orilla_piloto_s150 | 14.8 (199/1343) -> **10.8** (142/1320) | 19.5 -> **21.1** |
| 63_horizonte_piloto_s2200 | 23.4 / 76.6 -> **27.8 / 72.2** | 19.4 / 80.6 -> **23.3 / 76.7** (alt. max 36 -> 22 px) |
| 56 / 58 / 55 (informativas) | 7.3 / 5.9 / 0 -> 9.1 / 0 / 0 | 2.6 / 10.6 / 0 -> 0.6 / 0 / 0 (58: el islote 279.5 queda bajo la linea sin la torre) |

- KPI acotacion n.º 2, **mi metrica**: media 54/57/13/21/61 = 49.5 (r3) -> **53.2 %** (>= 50 OK); mar abierto 54 **58.4 %** y 63
  **76.7 %** (>= 50 OK). Modo normal: 54 44.7 / 55.3, 57 51.7, 13 51.8, 21 100, 61 31.4, 63 23.3 / 76.7 (media 55.9).
- KPI con la **metrica del director** (reconstruida): media 54/57/13/61 = 24.1 (r3) -> **32.0 %**; con el 100 % de 21 que dio el
  director: 39.3 -> **45.6 %** (< 50). Mar abierto 54 **60.8 %**, 63 **72.2 %** (OK). r4a (loma 120 m, mesetas, islotes 110-150):
  54 37.6, 57 44.2, 13 29.7, 61 10.6. Lo que falta no esta en mis manos sin romper la acotacion: la regla descarta toda silueta de
  mas de 60 px y 61 tiene 1 320 columnas de linea sobre el agua del puerto con 3 islotes de 52-65 px; subir 54 exigiria poner silueta
  en su mar abierto (prohibido: >= 50 %).
- `medir_capturas` (A/B, 10 tomas, 2 modos): `bandas_blancas` 0 nuevas en todas; `pct_azul` +4.9 (13), +5.9 (21), +3.0 (57), 54 -1.6
  (AC; +1.0 normal), resto +-0.9; `riqueza` +0.09..+0.26 en 13/21/57; `pared_lisa`/`pct_cesped`/`siluetas_20_120` sin cambio.
- Presupuesto: anillo 23 mallas, **210 778 tris** (r3 22 / 197 690; <= 250 k; +2 808 de la loma nueva, el resto el cordal de las
  cordilleras mas anchas), 14 materiales (escena 498 -> 512), construccion 2.3 s; copia 4 485 074 -> 4 695 852 tris (sin LIB).
  Test del kit TEST_OK: cobertura angular 98.5 %, fila cerca 91.5 % bosque, lejos 43.4 % cumbre, d_min al centro 2 254 m, 0 vertices
  en la rejilla ni bajo z -8, 2 lomas 'ventana' (208 y 200), 9 cordilleras solo domo/lomo.
- Mirado en imagen (`cmp_r3_r4b_*.png`, `AB_ac_*`): 55 sin agujas ni losa (domos + loma redonda a la izquierda); 21 toda la fila de
  cordilleras redonda; 57 islotes sin torres, loma nueva entre la ventana 208 y el lazo, fondo sin picos; 13 loma nueva a la
  izquierda y fondo redondo; 54 dos islas redondas (el faro sigue), nada nuevo en su mar; 63 tres islas redondas con faro; 56 igual.

### Para el integrador (ninguna linea de codigo nueva)

- La llamada `build_anillo_horizonte(root_col, terreno=T, seed=42)` recoge sola la configuracion r4. Esperar en
  `integrar_escena.log`: `horizonte: 23 objetos HORIZ_, 210778 tris, 14 materiales MAT_HORIZ_, 9 cordilleras + 10 lomas + 3 pueblos
  + 1 faro` y en `mejorar_materiales`: `HORIZONTE: 14 materiales mezclados`.
- P-H6 / `PETICIONES_04_EXPORT.md` P6-horizonte: 22 -> 23 mallas y 197 690 -> 210 778 tris. `kn5_presupuesto` familia HORIZ_ =
  210 778 tris.
- Al medir la candidata: `python 03_blender/_rev/_tmp_horizonte/banda_director.py renders/ab/f1_r4/despues_ac
  renders/ab/_base_antes/camaras.json --tomas 54,57,13,21,61,63 --runs` (metrica del director) y `medir_horizonte.py <antes>
  <despues> <camaras.json>` (las dos a la vez; el antes del A/B oficial es `_base_antes`, que en modo AC clasifica la caliza al sol
  como azul en 54/61: vale la fila de modo Blender o el antes sin anillo de `_tmp_horizonte/r4/ab/antes_ac`).
