# Entender las rocas de Porto Corsa: lazo, casino, McLaren y la máscara roca/hierba del terreno

Lector técnico, bloque ROCAS Y McLAREN. Fecha: 04/10/2026. No se ha modificado ningún fichero del proyecto.
Fuentes: código de `03_blender/` (assets y pipeline), logs de `03_blender/_rev/logs_final/`, la geometría congelada
`_rev/geometria_rev.json` (numpy, python del sistema), UNA inspección de solo lectura de `_rev/escena_rev.blend`
(script `scratchpad/insp_rocas.py`, lanzado por `blender_cola.sh`, sin guardar) y las capturas 01, 02, 07, 09, 15, 17,
19, 32, 33, 33b, 34_roca_lazo_general y 36_roca_casino_general de `renders/capturas/`.

Encargo del usuario que afecta a este bloque (`_rev/fase_visual/PLAN_USUARIO.md`, puntos 2 y 3): roca como parte del
terreno por pendiente (> 35-40 grados), caliza cálida con estratos horizontales, afloramientos medio enterrados, piedras
sueltas al pie, matorral en las repisas; roca del lazo = promontorio con paredes verticales, repisas y pinos (opcional
torre/fortín); McLaren petrificado con el MISMO material y estratos que el acantilado, base fundida con el terreno y
escombros, grietas, plantas en las juntas, AO en los huecos, túnel por la rueda con portal de sillería; terreno con
`ksMultilayer_fresnel_nm4` (máscara RGBA por pendiente/altura + 4 texturas de detalle CC0); bisel, AO horneada, VAO.

---

## 0. Resumen ejecutivo

1. Hay TRES generadores de roca distintos, cada uno con su propio campo de forma y su propia paleta: `assets/roca_lazo.py`
   (heightfield de 1 m: suma blanda de domos + corte de la pista), `assets/roca_casino.py` (malla radial de 256 columnas
   con perfil (r, z)) y `assets/montana_mclaren.py` (loft de secciones + cadena Boolean con la carrocería). No comparten
   ni material, ni coordenadas de textura, ni regla de estratos. El terreno (`terreno_montana.py` + `construir_pista.py`)
   es un cuarto sistema con su propio material procedural. `penon_pueblo.py`, `montana_coche*.py`, `penon_cara.py`,
   `penon_topolino.py` y `montanas_fondo*.py` son legado: solo se usan como fallback o como biblioteca de helpers.
2. La máscara roca/hierba del TERRENO vive en TRES sitios que no se ven entre sí: (a) el atributo por vértice `roca`
   (celda de 4 m) que calcula `terreno_montana.construir` (l. 2243-2298) y sube `integrar_escena._poner_celda` (l. 760-773)
   en los desmontes; (b) el material `MAT_terreno` (`construir_pista.mat_terreno`/`_roca_terreno`, l. 92-345), que mezcla
   ese atributo con la pendiente real (nz) y ruido; (c) el exportador (`04_export/color_ac.separar_roca_terreno`,
   l. 476-505), que vuelve a decidir por CARA con umbrales fijos y pinta la roca de AC con un color plano sin textura.
3. Cifras medidas (geometria_rev.json): 102 117 celdas de tierra; el 28 % tiene pendiente > 35 grados, pero solo el 21 % de
   esas celdas lleva `roca` > 0.49; el atributo es 0 en el 95.5 % de los vértices y está en la banda blanda 0.2-0.8 en el
   1.8 % (esa banda, interpolada en triángulos de 4 m, es el "borde difuminado"). El material añade roca solo donde
   nz < 0.50-0.56 (> 56-60 grados). Entre 35 y 56 grados casi todo es hierba con la textura `hierba_d.png` proyectada en
   planta (estirada). Esto explica las capturas 03/05/17/33/49 (hierba estirada), 07/08 (dientes de sierra) y 14/22
   (escalera), y en AC se agrava porque el límite va por aristas de triángulo y la roca es un color plano.
4. Los "desmontes-cantera" (01, 07, 09, 16, 21, 28, 42, 51) son planos analíticos de pendiente constante (regla
   `z <= Zp + 0.4 + (d-6)*1.15` de `terreno_montana`, caja del pit, `explanar` 1:1 hasta 150 m) pintados enteros de un
   mismo tono con estratos de onda de 2.6 m que, muestreados en celdas de 4 m, se leen como curvas de nivel.
5. El McLaren "parece plástico sobre un islote" por geometría y por material. Geometría: en su marco local, TODO lo que
   queda a más de 52 m detrás de la rueda delantera (x < -2R) está sobre el MAR (terreno = -4 m); la zaga (210 m) y el
   macizo de la zaga (hasta 377 m) salen de un pedestal que va de z = -29 m a 109 m con agua en tres lados; el terreno
   solo toca al coche en la franja del túnel (x -2R..+3R, cotas 8-45 m) y el macizo real de 117-122 m está 125 m DELANTE
   del morro, en el lado de tierra. Material: `_mat_piedra` = color plano crema (0.60-0.84 lineal) + un solo ruido de
   17-22 m, sin grano ni relieve, sombreado suave, y `aplicar_texturas` no lo toca (excluido por nombre). Los estratos
   son bandas de color por planos de bisect cada 1.7 m sin relieve en la carrocería ("franjas de pintura").
6. La roca del lazo es una cúpula lisa porque su macizo es una suma de domos `(1-rho^2)^2` (pendiente máxima ~47
   grados), el ruido es de 6.5 m a 55 m de longitud de onda y el desplazamiento rocoso es de ±1.5 m; los estratos y
   cornisas solo existen en la cara CORTADA por la pista (`_perfil_corte`), y en la coronación se desvanecen (v3 N2). Las
   "matas en lunares" son icosaedros `PENON_puente_matas` repartidos por nz 0.6-0.9. El material `MAT_PPUEBLO_roca` es
   un color plano al que `aplicar_roca` añade manchas de 20 m (el "velo de bruma": `world_mist` está apagado).
7. El peñón del casino es un "tambor de tarta" porque su perfil vertical tiene solo 3 vértices por banco de 7-15 m con
   un relieve de ±1 m y cuatro tonos que se alternan por banco (`mat_nat`), y la meseta es `MAT_PPUEBLO_plaza`
   (0.64/0.58/0.45 lineal, casi blanco al sol).
8. En Assetto Corsa nada de lo procedural sobrevive: `kn5_writer_opt.analizar_material` (l. 215-258) toma UNA imagen de
   color (si existe) tintada por `diffuse_color`, y si no hay imagen escribe un PNG plano de 8x8. Todos los materiales
   de roca (`MAT_PPUEBLO_roca*`, `MAT_MCOCHE_*`, `MAT_terreno_roca`) van planos. El plan del usuario (caliza con estratos
   compartida, ksMultilayer, AO) exige por tanto imágenes + UV + cambios en el exportador (equipo de 04_export).
9. Lo que haría falta se detalla en la sección 8: un material/grupo de nodos de caliza común en coordenadas de MUNDO,
   horneado a texturas por objeto para AC; máscara del terreno por pendiente 35-40 grados; afloramientos como kit de
   objetos semienterrados; para el McLaren, faldón de roca hasta la cintura con derrubios, grietas en el macizo, matas
   en las juntas, y terreno (cabo) bajo la zaga; para el lazo, bancos verticales con repisas sobre el macizo natural
   (lo que el registro llama H7) y pinos en las repisas.

---

## 1. Inventario de módulos del bloque

| Fichero | Estado | Quién lo usa | Qué produce |
|---|---|---|---|
| `03_blender/assets/roca_lazo.py` (3577 l.) | ACTIVO | `integrar_escena.zona_rocas_pueblo_lazo` (l. 3894-3928) | raíz `PENON_puente` + `PENON_puente_roca` (175 686 tris en escena) y obra/casas/matas |
| `03_blender/assets/roca_casino.py` (2904 l.) | ACTIVO | `integrar_escena.zona_casino` (l. 2005-2028) | raíz `PENON_cara` + `PENON_roca` (27 162 tris), carretera, parapetos, casas, `VEG_penon_*` |
| `03_blender/assets/montana_mclaren.py` (2297 l.) | ACTIVO | `integrar_escena.zona_tunel` (l. 2859-2882) | `MCOCHE_roca` (en LIB) -> clon `TUNEL_acantilado` (53 453 caras tras el taladro) + `MCOCHE_veg` |
| `03_blender/assets/montana_coche_v2.py` | helpers | `montana_mclaren._cargar_v2` (l. 169-204) | `_mat_piedra`, `_mats_roca`, `_disco_rueda`, `_celda`, `_ridged`, `_pulir`, `_boolean_cadena`... |
| `03_blender/assets/montana_coche.py` | legado | solo si falta `montana_mclaren` (`zona_tunel` l. 2859, 2884-2887) | coche fósil Fiat v1 |
| `03_blender/assets/penon_pueblo.py` (602 l.) | fallback | `zona_casino` si falta `roca_casino` (l. 2029-2035); `zona_rocas_pueblo` si falta `roca_lazo` (l. 3678-3730) | roca-hélice `PPUEBLO_roca` |
| `penon_cara.py`, `penon_topolino.py`, `montana_rueda.py`, `montanas_fondo(_v2).py` | legado | `zona_penon_puente` (solo si `penon_pueblo` es None, l. 3493), `zona_montanas_fondo` (sale en l. 2491-2495 porque hay `cumbres`) | nada en la escena actual |
| `03_blender/terreno_montana.py` (2682 l.) | ACTIVO | `preparar_geometria.py` | `terreno.z[]` + `mascara_roca[]` (celda 4 m) |
| `03_blender/construir_pista.py` l. 92-345, 1448-1474 | ACTIVO | pipeline | `MAT_terreno` y malla `TERRENO` con atributo `roca` |
| `03_blender/integrar_escena.py` | ACTIVO | pipeline | `_poner_celda`/`explanar`/`tallar_*` (suben `roca`), `zona_tunel`, `_taladro`, `_paredes_de_roca`, `ajustar_montanas` |
| `03_blender/aplicar_texturas.py` | ACTIVO | pipeline (después de `mejorar_materiales`) | `aplicar_terreno` (l. 247-342), `aplicar_roca` (l. 359-398) |
| `04_export/color_ac.py`, `04_export/kn5_writer_opt.py` | ACTIVO (no tocar ahora) | exportación | `separar_roca_terreno`, una textura por material |

Materiales presentes en `escena_rev.blend` (inspección): `MAT_MCOCHE_caliza / _caliza_clara / _caliza_oscura / _hueco /
_hueso / _cristal_pulido / _caliza_grieta / _caliza_monte / _veg / _veg_clara / _tronco`; `MAT_PPUEBLO_roca / _roca_clara /
_roca_oscura / _repisa / _muro / _plaza / _plaza_dibujo / _borde / _carretera / _piedra_*`; `MAT_PENON_balaustrada /
_poste / _farol / _muelle / _bolardo`; `MAT_terreno`; `MAT_VEG_roca`. NO existen `MAT_MONT_*` ni `MAT_PENON_caliza*`:
`integrar_escena.ajustar_montanas` (l. 6436-6495) recolorea nombres que ya no están en la escena (código muerto) y
`aplicar_texturas.familia_de` l. 87-90 incluye prefijos (`mat_mont_roca`, `mat_penon_caliza`, `mat_mrueda_caliza`) sin
ningún material detrás. El integrador llama a `MAT_PENON_*` en `_paredes_de_roca` solo por la subcadena `roca`.

---

## 2. La máscara roca/hierba del terreno

### 2.1 Cadena completa (quién decide qué)

1. `terreno_montana.construir` (l. 915-2439). Tras construir el campo de alturas calcula `mascara_roca` (l. 2243-2298):
   - roca NATURAL (`_nat_r`, l. 2261-2266): pendiente suavizada 2.5 celdas > 1.0 + 0.1·ruido(30 m), fuera de acantilados
     y desmontes, apertura 3x3 y sin manchas < 12 celdas (solo afloramientos "grandes y continuos");
   - ACANTILADOS de costa (`_acg`): pendiente > 0.85 ± 0.1; CUMBRES: z > 185 m y pendiente > 0.5 (l. 2267);
   - desenfoque gaussiano de 1 celda (2 en aristas con pendiente > 1.5), reescalado `(x-0.2)/0.4` (l. 2270-2271);
   - CORTES de la pista (`_corte`, l. 2272-2274): profundidad del corte `(z_land - z - 1)/3` × pendiente > 0.75 ± 0.1,
     desenfocado 1.5 celdas × 1.25; `max()` con lo anterior;
   - dilatación en el mar (l. 2281), pie de acantilado = 1 (l. 2287-2290), escalón de la garganta = 1 (l. 2293-2296),
     Loews congelada con la máscara v2 (l. 2297-2298). Sale en `extras['mascara_roca']` (l. 2434) y a `geometria_3d.json`.
2. `construir_pista.py` l. 1469-1474: `terreno.data.attributes.new('roca', 'FLOAT', 'POINT')` con esos valores, uno por
   vértice de la rejilla (517 x 515, celda 4 m: 266 255 vértices, 530 448 triángulos con diagonal fija a->a+nx+1).
3. `integrar_escena._poner_celda` (l. 760-773): cada explanada/tallado (`explanar` l. 785-833, `tallar_circulo` l. 897,
   `tallar_cinta` l. 937, `_tallar_sendero` l. 1088 con `roca` solo si corte > 2.5 m) sube el atributo a
   `min(1, (z - z_new - 1)/2)` en los vértices rebajados más de 2 m. Es un valor POR VÉRTICE sin desenfoque: un vértice a
   1.0 junto a otro a 0.0 a 4 m produce la rampa de 4 m que, con el umbral del material, da "dientes de sierra".
4. `construir_pista.mat_terreno` + `_roca_terreno` (l. 92-345), material `MAT_terreno`, un solo material para todo el
   terreno (slot 0; el slot 1 `M_FONDO` es el mismo material):
   - rama HIERBA: ColorRamp por cota z (l. 107-117: fondo marino -4, arena 0, hierba baja, monte, cumbres a 170 m) ×
     parches de 200 m (l. 119-134) y, encima, `aplicar_texturas.aplicar_terreno` multiplica `hierba_d.png` (tile 7 m,
     proyección PLANA = coordenadas XY de objeto, ganancia 1.85, factor 0.85) solo entre z 0.5-150 y donde nz > 0.60-0.78
     (`TEX_llano`, l. 311-318);
   - máscara `ROCA_mascara` (nodo `Math.002`, l. 173-177, 202-251) = `max( smoothstep(nz + ruido ±0.04, 0.50->0.56),
     smoothstep(atributo + ruido ±0.15 (2.5 m) ±0.18 (11 m), 0.47->0.51) × (1 - smoothstep(nz, 0.78->0.86)) )`;
   - rama ROCA (l. 252-331): rampa de caliza `0.30/0.235/0.15 -> 0.46/0.37/0.245` por ruido de 20 m, × estratos
     `TexWave BANDS Z` de periodo 2.6 m con distorsión 6 (junta 30 % más oscura en el 7 % de la onda), × grano de 2 m,
     × manchas de meteorización de 7 m; bump 0.40 con las juntas talladas;
   - `ROCA_mezcla` (Mix Shader, l. 338-345) entre el BSDF de hierba y un BSDF propio de roca (rugosidad 0.92).
   `m.diffuse_color = (0.32, 0.45, 0.2)` (l. 181) es lo que lee el exportador.
5. `04_export/color_ac.py` l. 401-505 (`mascara_roca`, `datos_caras`, `separar_roca_terreno`): por CARA, roca si
   `nz < 0.50` o (`atributo medio > 0.49` y `nz < 0.82`); esas caras pasan al material nuevo `MAT_terreno_roca` con
   `diffuse_color = ROCA_COLOR (0.34, 0.27, 0.18)` y SIN imagen -> en el KN5 un PNG plano 8x8 (`kn5_writer_opt.
   construir_textura`, l. 261-283). El resto del terreno lleva `hierba_d.png` tintada por `(0.32, 0.45, 0.2)`.

### 2.2 Cifras (geometria_rev.json y escena congelada)

- Vértices del TERRENO: 266 255. Atributo `roca`: media 0.029; = 0 en el 95.5 %; = 1.0 en el 1.6-1.7 %; > 0.49 en el
  2.6-2.8 %; en la banda 0.2-0.8 el 1.8 % (es decir, el 40 % de la roca está en el borde blando).
- Celdas de tierra (z > 0.5): 102 117. Pendiente > 0.7 (35 grados): 28.4 %; > 0.85: 13.1 %; > 1.0 (45 grados): 5.0 %.
  De las celdas con pendiente > 35 grados solo el 21.2 % tiene `roca` > 0.49. Caras de tierra con nz < 0.5 (> 60
  grados): 1.9 %. Es decir: la regla del plan ("roca a partir de 35-40 grados") NO está implementada en ninguna de las
  tres capas; la natural pide 45 grados suavizados y el material 56-60 grados.
- `preparar_geometria.log` l. 73: pared de roca (> z_pista + 8 a 25 m) en algún lado en el 29.7 % de la pista en tierra.

### 2.3 Por qué las laderas cortadas parecen canteras (01, 07, 09, 16, 21, 28, 30, 42, 51, 05/06/39)

- FORMA: los desmontes son PLANOS de pendiente constante. Regla dura de `terreno_montana` (cabecera l. 21-24): fuera del
  corredor `z <= Zp + 0.4 + (d-6)·1.15` (49 grados) y `z >= Zp - 0.6 - (d-6)·0.55`; detrás de la última terraza 1.15
  (l. 1456-1458; 2.0 = 63 grados en el espolón del coche, `PEND_DESMONTE_COCHE` l. 193); caja del pit (28 m llanos + 22 %
  hasta 100-130 m y luego 0.8-1.15, con limitador al 92 %: la "pared de 25-45 m tras el paddock" de la 28/30/42);
  `integrar_escena.explanar` (l. 785-833) con desmonte 1:1 que "sigue hasta la ladera natural (como mucho 150 m)". Solo
  hay dos fuentes de relieve en esas caras: las "costillas de erosión" (v2 B2-09) y el ruido de 30 m del umbral de la
  máscara. A 4 m de celda, un plano de 40 m de alto con 1-2 m de rizo es una cantera.
- COLOR: toda la cara del corte entra en la máscara con `_corte` (profundidad × pendiente, desenfoque 1.5 celdas): un
  tono uniforme de la rampa (beige-gris 0.30-0.46 lineal) sin tierra, sin derrubios, sin franjas de hierba.
- "RAYAS ONDULADAS TIPO CURVA DE NIVEL" (05, 06, 39, 27): son los estratos `TexWave` de 2.6 m con distorsión 6
  (l. 266-284) sobre caras casi lisas: a la distancia de la cámara solo se lee la onda de baja frecuencia.
- BORDE DIFUMINADO (01, 09, 16, 21, 51): el atributo se interpola linealmente en triángulos de 4 m y además lleva
  ±0.33 de ruido y un desenfoque de 1-2 celdas en origen: la transición hierba/roca mide 4-8 m. En AC desaparece el
  degradado pero el límite sigue las aristas de los triángulos (almenas de la 14/22, por `separar_roca_terreno`).
- DIENTES DE SIERRA EN EL SENDERO (07, 08): `_tallar_sendero` marca `roca` por vértice solo donde el corte pasa de 2.5 m;
  a lo largo de una cinta de 2-4 m de ancho eso enciende vértices sueltos cada 4 m -> con el umbral 0.47-0.51 cada
  vértice encendido se convierte en un rombo blanco.
- HIERBA ESTIRADA (03, 05, 17, 33, 40, 48, 49): entre 35 y 56 grados la máscara da hierba; `hierba_d.png` va en
  proyección plana (`FAMILIAS['hierba'] proy='FLAT'`, l. 59-60), así que en una cara de 50 grados el tile de 7 m se
  estira ×1.6 y en una de 70 grados ×3. El "velo" es la zona intermedia del Mix Shader (0.2-0.8) donde ambos BSDF se
  suman a medias.
- SIN SOMBRA PROPIA: motor `BLENDER_EEVEE`, `view_transform Standard`, sin niebla de mundo (`use_mist` False). No hay
  AO horneada ni bisel; el bump de 0.4 de la roca no se aprecia a la escala de las capturas.

---

## 3. Roca del lazo (`assets/roca_lazo.py`)

### 3.1 Cómo se construye (orden de `build`, l. 3461-3577)

1. `_preparar(muestras, contexto)` (l. 1785): borde interior del tablero `B`, cotas `Zb`, centro `C`, lado de la roca
   (`side` = -1 en la escena; `integrar_escena.log` l. 90: 331 muestras, centro (79, -567), cumbre S0 (95, -549)).
2. `_disenar_macizo` (l. 1834-1864): el macizo `M` es una `_Macizo` (l. 363-379) = norma-8 de DOMOS `(1 - rho^a)^b · z`:
   cumbre S0 (24 m hacia la abertura, z_c 106, R 150, a = b = 2), dos domos de hombro K1/K2 (+36/+24 m sobre el tablero,
   R 95/78), tres domos decrecientes hacia dentro, K5 y un domo cada 18 muestras a 30 m del borde (+34/+26 m, R 54-56).
   Un domo `(1-rho^2)^2` de 106 m y R 150 tiene pendiente máxima ~1.09 (47 grados) y es suave en la cumbre: de ahí la
   "cúpula". Después (l. 3482-3490): + 6.5 m de fbm a 55 m + 2.4 m a 22 m - 1.2 (solo `lejos`: o > 14 m y M > 30 m) +
   1 m a 9 m; cuenco de la cala (-9 m); pie bajo el fondo del mar.
3. `_disenar_rasgos` (l. 1867-1931): plaza irregular (r 17-23.5 m) a z_c - 9, dos terrazas por curva de nivel
   (`_terraza_nivel`, z_c - 50 y z_c - 78, repisa >= 14 m), escaleras en zigzag; `_disenar_accesos`, `_disenar_cala`,
   `_disenar_carretera_cala` (dos carreteras de 4 m, H2-5). Cada rasgo es un `_Rasgo` (l. 412-434): dentro del polígono
   la cota es fija y fuera "la roca no puede subir más de 75 grados" (`TAN75 · d`): ese es el único sitio con paredones
   fuera de la cara de la pista.
4. `_campo_borde` (l. 316-359): distancia con signo `o` al borde interior del tablero, `zt`, `rampa`.
5. `_perfil_corte` (l. 454-471) + `_bancos` (l. 438-451): la cara que mira a la pista: bajo el tablero talud
   `tan_bajo` (80 grados en el integrador, l. 3912), berma de 0.6 a `o_b` (= 1.2 + 2.2·cell = 3.4 m) que sube 0.9 m, cara
   a 75 grados durante 7 m y después BANCOS de `hs = 12·(1 + 0.25·ns)` m (talud 78 grados + rizo senoidal ±0.14·hs).
   v3 N2 (l. 546-552): el rizo se desvanece donde el macizo queda a < 6 m sobre la cara lisa (`D_RIZO`); el log dice que
   el 36.5 % del corte va con rizo reducido; la coronación es un mínimo suave de k 2.5 m.
6. `_campo_alturas` (l. 520-608): `H = min(M, corte)` + rasgos; vértices pegados al contacto (o = 0.6, z = zt - 0.3);
   DESPLAZAMIENTO rocoso (l. 571-583) = `1.1·vnoise3(9 m) + 0.45·vnoise3(3.5 m)` (aprox. ±1.5 m) solo a o > o_b + 1..7 m,
   fuera de lo llano y modulado por nz; relleno de cuencas cerradas (l. 585-598).
7. `_malla_roca` (l. 785-931): triangula la rejilla de 1 m, parte los triángulos por isolíneas (marching triangles) y da
   material POR CARA: `roca_oscura` bajo z_mar - 0.4; en la cara de corte, por COTA `kz = (H0 - zt - 7.6)/hs`:
   `repisa` a ±0.042 de cada entero, `roca`/`roca_clara` alternas por banco (`_clave_estrato`, l. 615-627); fuera del
   corte, `roca_clara` donde nz >= 0.75 y manchas de 26 m > 0.2, si no `roca` (l. 831, 900). Normales suaves de la
   rejilla sin partir como normales personalizadas (`_fijar_normales`). Resultado en escena: 88 627 vértices, 175 686
   triángulos (121 459 roca, 22 574 roca_clara, 7 417 roca_oscura, 24 236 repisa), z -6..107.7, cumbre 108, plaza 97.
8. `_construir_obra` (muros, escaleras, vallas, campanile, muelle, carreteras) y `_poblar` (l. 2757): 17 casas, pinos y
   palmeras por ray-cast, y MATAS (`_mata_verts` l. 1176: icosaedros de 12 vértices; `_matas` l. 1197) en nz 0.6-0.9,
   medio enterradas, en `PENON_puente_matas` con `MAT_PPUEBLO_mata/_mata_clara`.
9. `_comprobar` (l. 3134): rayos sobre el tablero (0 impactos), contacto < 0.8 m, casas, matas, orientación, carreteras.

Materiales: `_PALETA` l. 151-174 (`roca` 0.46/0.39/0.28, `roca_clara` 0.62/0.55/0.42, `roca_oscura` 0.29/0.24/0.17,
`repisa` 0.42/0.37/0.27; rugosidad 0.95) creados por `_mat` (l. 180-193) como Principled de color plano. En la escena
`roca_casino._PALETA` (l. 98-113) crea los MISMOS nombres con OTROS valores (`MAT_PPUEBLO_roca` 0.55/0.47/0.36,
`roca_clara` 0.63/0.56/0.44, `roca_oscura` 0.46/0.39/0.30): quien llega primero fija el color, y gana `roca_casino`
porque `zona_casino` (l. 2120) corre antes que `zona_rocas_pueblo` (l. 3928); la inspección lo confirma (0.55/0.47/0.36).
`aplicar_texturas.aplicar_roca` (l. 359-398) añade después un ruido de color de 20 m (rampa 0.45 -> 1.0, ×0.9, ganancia
1.15) y un bump de 3 m (sin imagen).

### 3.2 Por qué se ve como se ve (13, 15, 34, 45, 46, 54)

- Cúpula gris lisa: domos suaves + ruido de 55 m + ±1.5 m de desplazamiento; sin bancos fuera del corte. La pendiente
  del macizo natural no pasa de ~50 grados, así que no hay paredes verticales ni repisas más que en la cara del tablero
  y en los paredones de 75 grados de plaza/terrazas (`_Rasgo`).
- "Sin estratos": en la cara del corte sí los hay (bancos de 12 m con cornisa de ±1.7 m y color `repisa`), pero la
  coronación v3 los apaga en el 36 % del corte y el resto queda tapado por la propia pista desde casi todas las cámaras.
  Fuera del corte el color es uniforme en lo empinado (`roca`) y con manchas en lo tendido (`roca_clara`).
- "Velado por bruma": no hay niebla (`world.mist_settings.use_mist` = False en la escena). Es `aplicar_roca`:
  `TEX_ruido_color` escala 0.045 (manchas de ~20 m, detalle 8) con rampa 0.45 -> 1.0 multiplicada por 1.15: manchas
  blancas y grises de 20 m sin ningún detalle fino ni normal; a 200-400 m de la cámara eso se lee como bruma.
- "Matas en lunares regulares": icosaedros oscuros de 1-2 m sobre una superficie clara y lisa, sin pinos ni matorral
  agrupado (los pinos del lazo van en plaza/terrazas/cala, no en la ladera).
- En AC: `MAT_PPUEBLO_roca*` no tienen imagen (en la inspección: marcador TEXTURIZADO presente, `imagenes = []`), luego
  en el KN5 son 4 colores planos (+ `repisa`): la cúpula será todavía más lisa que en Blender.

---

## 4. Peñón del casino (`assets/roca_casino.py`)

### 4.1 Cómo se construye (`_Penon`, l. 240 y siguientes; `build` l. 2824)

- Entrada: `integrar_escena.zona_casino` (l. 1985-2028): elipse de 118 x 78 m girada 0.5 rad a 190 m del lóbulo 36-38,
  recortada por `_contorno_libre(pts, 8)`, `z_base_c` = terreno máximo del contorno + 0.3 (118 según el log),
  `z_top_c = max(z_plaza + 12.2, z_base + 8)` (132), entrada = punto más cercano a la curva 37, `terreno_fn = z_terreno`.
- `_terreno_columnas` (l. 327-388): 256 columnas radiales (`dphi` = 1.4 grados; a R 60-120 m son 1.5-3 m de arco); por
  columna el terreno cada metro, columnas "de tierra", muescas junto a la pista y tope radial `R_cap` (+2.5 m junto a la
  pista, +18 m en tierra, 1.65·Rc al mar).
- `_meseta` (l. 454-482) y `_forma` (l. 484-521): radio de la meseta (`R_top` ~ 0.66·Rc + irregularidad de baja
  frecuencia), radio del pie `R_bot` (1.30·Rc con 3 senos) y forma del talud `a` por columna (hombro arriba y
  acantilado abajo, o al revés).
- `_estratos` (l. 523-530): bordes de banco cada 7-15 m al azar desde z_fondo - 30 hasta z_top + 30, amplitud 0.35-1.0 m,
  fase ±3 m por columna; `estrato(i, z)` (l. 532-547) devuelve el banco y un desplazamiento radial: labio arriba (+0.9a),
  entrante abajo (-0.8a).
- `F_libre` (l. 550-566): radio suave entre `R_top` y `R_bot` con la forma `a`, contrafuertes de las horquillas y tope.
  `empotrado` (l. 568-579): mete la roca 1.5 m en el terreno. `F_malla` (l. 1716-1739): `F_libre` + `textura(i, z)`
  (l. 598-608: bultos de 2 escalas + costillas + estrato; amplitud total <= ~5 m), que se desvanece 4 m bajo cada
  repisa, más talud 1.2:1 bajo las repisas junto a tierra.
- `trazar()` y el apilado: carretera de 5 m (repisa 6.2) con entrada, subida y bajada <= 11 %, horquillas con
  plataforma, espigón o cala al pie; cada repisa es un "cruce" por columna (log: bajada 1460 m, 11.0 %, 2 horquillas).
- `_perfil(i)` (l. 1757-1850): la columna i de abajo arriba: `roca_oscura` bajo z_mar - 0.5; `alturas` = por banco SOLO
  3 cotas (b0 + 0.4, mitad, b1 - 0.45 con etiqueta `labio`) (l. 1781-1786); material `mat_nat` = `('roca', 'roca_clara',
  'roca', 'roca_oscura')[k % 4]` (l. 1777-1780); bastiones bajo la calzada en roca con estratos; `repisa` en la repisa;
  `plaza` en la meseta. `malla_roca` (l. 1870-1906) cose columnas vecinas con `_cremallera`. Resultado: 13 583 vértices,
  27 162 tris (11 452 roca, 4 862 roca_clara, 9 570 roca_oscura, 974 repisa, 48 muro, 256 plaza), z -26..132.
- `vegetacion` (l. 2529-2659): 28 palmeras/cipreses en el borde de la meseta, pino en cada isla de horquilla, <= 22
  pinos en caras con nz > 0.82 y <= 70 arbustos en los `labios`.

### 4.2 Por qué se ve como se ve (19, 20, 36, 10)

- "Tambor con estratos regulares como una tarta": 3 vértices por banco de 7-15 m con relieve <= 1 m -> facetas
  verticales de 5-7 m, y cuatro tonos que se alternan banco a banco sin variación lateral (la fase ±3 m solo desplaza la
  banda). Las "rayas blancas horizontales" son `roca_clara` (0.63/0.56/0.44 lineal ~ 0.8 sRGB) y los bastiones/`muro`.
- "Meseta blanca lisa y vacía" (20, 36): `MAT_PPUEBLO_plaza` (0.64/0.58/0.45) y `MAT_PPUEBLO_borde` (0.86/0.83/0.74) sin
  textura (no son familia roca ni piedra en `familia_de`); la cala-marina es `MAT_PENON_muelle`/`plaza`: la "losa blanca
  flotante" de la 36.
- "Cara lisa y facetada" (10): 256 columnas × 3 puntos por banco en una roca de 120 m de alto, ~27 000 triángulos en
  total (el lazo tiene 175 000 para un volumen parecido).
- "Velo de bruma": el mismo `aplicar_roca` que en el lazo (manchas de 20 m).
- "Plano blanco liso sin material" (19, px 630-690): probablemente la cara `plaza` que `_perfil` emite entre
  `c['R_out']` y `R_top` cuando la carretera entra en la meseta (l. 1835-1838) o un testero de `malla_pavimentos`;
  habría que confirmarlo con una vista aislada (`test_roca_casino.py`, vistas `roca_casino_v3_*`); queda fuera de este
  informe.

---

## 5. McLaren de piedra (`assets/montana_mclaren.py` + `integrar_escena.zona_tunel`)

### 5.1 Construcción (`build`, l. 2105-2297)

1. `_roca` (l. 698-873): LOFT cerrado de secciones YZ cada 0.1R (2.6 m) a lo largo de X, 84 vértices por anillo:
   - PEDESTAL bajo el coche (l. 773-779): semiancho `w_ped = flanco - 0.05R` hasta `z_pt = umbral + 0.35R`, sección en
     domo (q 2.6), falda a 70 grados (`_K_FALDA` 0.36) SOLO fuera de la zona del túnel (`flare` = 0 en x entre -1.3R y
     1.5R, l. 760) y clamp duro `|y| <= W/2 + 2.3` en esa zona (l. 846-847): ahí la pared del pedestal es VERTICAL.
   - MACIZO(S) (l. 780-784): con `enterrado='ambos'` dos macizos (`_macizos`, l. 672-686) con perfil `_ZM_ZAGA/_WP_ZAGA`
     y `_ZM_MORRO/_WP_MORRO` (l. 330-341) reescalados a `largo_macizo` (14.5R zaga = 377 m desde el origen; 4.8R morro)
     y `alto_montana` (83.2 m zaga, 65 m morro); sección de MESETA plana (q 6) con laderas en talud `talud_deg` (38 grados
     lado -Y / 52 lado +Y). El macizo "lame" el flanco del coche a `zm(x)`.
   - RELIEVE (l. 794-822): `amp` (0.6 junto al coche, 1.8 en la falda, ×2.4 en laderas libres) × (`_ridged` + bloques
     `_celda_suave` de 0.30R x 0.45R = 7.8 x 11.7 m) + `tanh(2.5·_onda_estrato(z, band_h))` con `band_h` = 0.13R =
     3.4 m, limitado a 6.5-9 m. Los ESCALONES de la 33b/17 son esa onda de estrato de 3.4 m sumada a los bloques de
     7.8 x 11.7 m (en la zona del túnel se conserva la `_celda` dura de la v1 por los Boolean, l. 813-818).
   - ESTRATOS de color (l. 848-869): `bisect_plane` cada `band_h/2` = 1.7 m desde `z_agua + 1` y material por cara:
     `_mat_estrato_mc` (l. 635-646) = `caliza_clara` cada 8 medias bandas (13.5 m), `caliza_oscura` en ~45 % de las
     medias bandas impares, `caliza` el resto; `caliza_oscura` bajo `z_moja` (agua + 1 m). Son BANDAS DE COLOR PLANO sin
     relieve asociado en la carrocería: las "franjas de pintura" de la 32.
   - `_hierba_y_monte` (l. 876-910): a > 0.6R de la carrocería, techo de la meseta con `tapa >= 0.94` -> material 7
     (`MAT_terreno` de la escena) y caliza base a > 0.6-2.8R -> `caliza_monte` (8).
2. `_bloques` (l. 1562-1584): 7 posiciones × 2 lados por macizo de `_pedrusco` facetados (r 0.08-0.11R = 2-3 m) hundidos
   un 30 %: los únicos "escombros", 28 piezas en 500 m de roca.
3. Carrocería, cabina, pasa-ruedas, discos de 10 radios, detalles, cristales, cortes (grietas `_GRIETAS` l. 1339,
   `_GRIETA_ANCHO` 0.10-0.15R = 2.6-3.9 m, fondo 0.045R, bisel; desconchones) y luces; cadena Boolean (l. 2199-2204)
   `roca U bloques U carrocería U cabina - pasa-ruedas U ruedas U detalles - cristales - cortes - ramas U luces`
   (MANIFOLD, con EXACT y "sin grietas" como red de seguridad). `_pulir`: sombreado suave, aristas > 30 grados vivas.
4. `_contacto_terreno` (l. 978-1072) con `terreno='auto'` (`encaje_mclaren.sitio_de_build` + `TerrenoMalla`): cambia
   SOLO materiales tras la cadena: roca a < 3-7 m sobre el terreno -> `MAT_terreno` (5 943 caras = 11 % del objeto);
   caliza base a < 16-34 m -> `caliza_monte` (357); caliza del macizo a > 1.6-2.4R del coche -> `caliza_monte` (1 975);
   falda del pedestal bajo umbral - 0.25R -> `caliza_monte` (78); cuencas oscuras medio enterradas -> caliza (2 cuencas,
   223 caras). Nunca en la carrocería, ruedas, roca mojada ni zona del túnel.
5. `_vegetacion` (l. 1662 y siguientes): cojines (`_blob`) sobre apoyo franco nz >= 0.6, pinos y matas sobre las caras
   de hierba, presupuesto 3400 + 1400 tris: 66 islas (registro v3 B15), malla aparte `MCOCHE_veg`.

Materiales (`_mats_mc`, l. 255-269; base `montana_coche_v2._mats_roca` l. 161-176 y `_mat_piedra` l. 131-158): color
plano + UN `TexNoise` (escala 0.045-0.06 = 17-22 m, detalle 3) en coordenadas de OBJETO por una rampa 0.38 -> 0.66:
`caliza` 0.60/0.49/0.33 -> 0.74/0.65/0.49; `caliza_clara` 0.74/0.66/0.50 -> 0.84/0.77/0.61; `caliza_oscura`
0.40/0.31/0.20; `hueso` 0.80/0.75/0.62; `cristal_pulido` 0.05/0.062/0.08 con rugosidad 0.26; `caliza_grieta` = caliza
-13 %; `caliza_monte` 0.34/0.28/0.19 -> 0.46/0.385/0.27. Rugosidad 0.95 pero `spec` 0.25 (`_mat`). Ningún nombre lleva
"roca" ni "piedra" a propósito (cabecera l. 147-149) para que `_paredes_de_roca` y `aplicar_texturas` no los toquen; en
consecuencia NO reciben el bump de 3 m ni las manchas de `aplicar_roca`, y en el KN5 van como colores planos.

### 5.2 El sitio y el túnel (`integrar_escena.zona_tunel`, l. 2849-3352)

- Colocación (l. 2869-2895): R = 26, vía 135; `s_face = s_mid - 0.42·135` (= 471, log l. 78); origen = `p - n·0.65R`
  (17 m a la derecha de la calzada), `ang_c = atan2(-ny, -nx)` (+X local = -n: morro tierra adentro, zaga al mar),
  z = `pf.z - 1.4` = 19.8; `z_fondo = -(pf.z + 8)` = -29.2; `enterrado='ambos'`, `alto_montana=(83.2, 65.0)`,
  `largo_macizo=(14.5, 4.8)`, `talud_deg=(38, 52)`, seed 11. El clon se llama `TUNEL_acantilado` (bbox x -811..-361,
  y -52..523, z -9.4..109; 56 142 vértices, 53 453 caras). El original `MCOCHE_roca` queda en LIB sin render.
- Limpieza de la huella real (l. 2911-3016): 102 objetos retirados (casas, árboles, losas, coches).
- Taladro (l. 3077-3081): `_taladro(i0t, i1t, 10.5, 9.5)` (definido en l. 2661) entre `s_face ± (W/2 + 25)` = 185 m,
  sección de arco 21 x 9.5 m (en `_taladro`, FUERA de una galería el tubo se abre a 34 x 110 m: corte a cielo abierto;
  aquí `gal` es None, así que toda la longitud es arco). Solver EXACT derrumba la malla (489 vértices, log l. 79) y se
  descarta; MANIFOLD la deja en 56 142 (l. 80), 0 rayos bloqueados (`_tunel_abierto`, l. 2701-2719). `_paredes_de_roca`
  (l. 2721-2764) pasa 503 caras de pared a `caliza_grieta` (289 en el original -> 792 en el clon). Galerías de sillería
  `TUNEL_portal_galeria` (`_galeria` l. 2800, `MAT_piedra`) en s 404-420 y 528-540, sección cerrada 416-532, portales
  `_portal` (l. 2766) en 404 y 540, `TUNEL_suelo` (l. 3280-3309). La falda remetida (l. 3143) y la falda con
  `MAT_terreno` (l. 3172-3184) NO se aplican al McLaren (`es_mclaren`): "trae su propio pedestal y bajos".
- Por qué "la pista no entra por la rueda" (03, 17, 33): el buje está en `z = R - AB` = 14 m local = 33.8 m de mundo y
  la pista en s 471 va a ~21 m: el tubo (21 x 9.5 m, techo a pista + 8) atraviesa el tercio inferior de la llanta, por
  debajo del buje; el disco y los radios quedan a la vista por encima del arco de 10.5 m y el portal se ve "pequeño".
  Para que el túnel pase por el centro de la rueda haría falta hundir la rueda ~8 m más (`alto_base` 12 -> ~20, con el
  test del túnel `test_montana_mclaren.py`) o subir el coche 8 m (y entonces crece el pedestal-repisa).

### 5.3 Por qué parece plástico sobre un islote (01, 02, 13, 31, 32, 33, 33b)

Perfil del terreno REAL en el marco local del coche (`encaje_mclaren.Sitio.terreno`, sobre `geometria_rev.json`;
x en radios R, z en metros de mundo; M = mar):

| x local | y = 0 | y = +W/2 + 10 | y = -W/2 + 10 (lado tierra) | lectura |
|---|---|---|---|---|
| -14.5R .. -2R (de -377 a -52 m) | -4 M | -4 M | -4 M | TODO el macizo de la zaga y la zaga del coche están sobre el MAR |
| 0 (rueda delantera) | 26 | 45 | 20 | el terreno llega 1-6 m por encima de la rasante local del coche |
| +1.5R (39 m) | 54 | 42 | 60 | ladera que entierra el capó |
| +2.9R (morro, 75 m) | 76 | 38 | 84 | el morro (capó a ~66 m de mundo) queda 10-18 m bajo tierra |
| +4.8R (125 m) | 50 | 39 | 117-122 | el macizo real ("Espolón del coche") está DELANTE del morro, en el lado -Y |

- Cotas del propio objeto (mundo): techo de la cabina 95.2 m; cresta del macizo de la zaga 109.0 m (36 m DETRÁS de la
  cola, no encima); afloramiento del morro 91.5; base del pedestal -29.2; línea de agua 0.0. Máximo del terreno en los
  120 m detrás de la cola: -4 m (mar). `preparar_geometria.log` l. 81 lo confirma desde el lado del terreno: "macizo a
  120 m detrás del coche >= 90 m en 17 %; a 90 m, 0 %" (esa QA mide el lado -n de la PISTA, no la cola del coche).
  Conclusión: por diseño (`montana_mclaren` cabecera l. 39-48: "la zaga sale de un PEÑÓN en el mar, 62 % de la huella
  sobre el agua") el coche NO sale de una montaña: sale de un pedestal de 113 m de alto plantado en el mar, y la única
  parte enterrada es el morro. Desde el mar y la meta (01, 02, 13, 31) eso es un islote con un coche encima; desde la
  pista (33, 17) la pared vertical del pedestal en la zona del túnel (clamp `y_lim`, l. 846) con el umbral del coche a
  2.3 m local (`_ZF` -0.45R) es la "repisa plana con los bajos rectos" 1-5 m sobre la calzada.
- "Zaga en montón escalonado tipo vóxel" (02, 31, 33b): bloques `_celda_suave` de 7.8 x 11.7 m + escalón `tanh` de la
  onda de estrato de 3.4 m con amplitud ×2.4 en las laderas libres (l. 807-809, 820) y, bajo agua + 1 m, todo
  `caliza_oscura` (11 056 caras = 21 % del objeto: la franja oscura de la 02/33b).
- "Crema brillante, plástico" (32, 02): colores lineales 0.60-0.84 (sRGB 0.80-0.93) con `hueso` 0.80/0.75/0.62 en bujes,
  aros, marcos y barra LED; ruido de 20 m sin grano; `spec` 0.25 en Eevee con sombreado suave sobre un loft continuo;
  sin bump ni AO; sin ninguna textura; grietas = 289 caras de 53 000 (0.5 %) solo en la carrocería (`_GRIETAS`),
  desconchones de casquete; "matas diminutas en la cintura" = cojines `_blob` de 42 tris en las repisas de la
  carrocería (`_vegetacion`), que a 200 m son puntos verdes.
- "No se ve ningún macizo detrás" (32): la cámara (`renderizar_capturas.py` l. 167: 200 m a -Y, 70 m a -X, +25 m) mira
  al flanco; el macizo de la zaga queda a la izquierda y más bajo que la cabina en perspectiva; detrás del coche solo
  hay mar.

---

## 6. Qué llega a Assetto Corsa de todo esto

- `04_export/kn5_writer_opt.analizar_material` (l. 215-258): por material toma `diffuse_color` (o el Base Color si no
  está enlazado) y la PRIMERA `ShaderNodeTexImage` de color enlazada, con su `TEX_ganancia`/`TEX_multiplicar`/mapping.
  `construir_textura` (l. 261-283): con imagen, una textura tintada de 512 px (`color · (1 - f + f · img · gain)`); sin
  imagen, un PNG plano de 8x8 del color base. `escribir_texturas_y_materiales` (l. 303-343): todo es `ksPerPixel` con
  un único `txDiffuse` y las `SHADER_PROPS` por familia de `color_ac.FAMILIAS` (l. 279-290: roca ksSpecular 0.02,
  exp 8). No hay UV de usuario: la proyección sale de `proj` (FLAT/BOX) y `scale` del mapping.
- Consecuencias para este bloque: `MAT_MCOCHE_*` (sin imagen) = 9 colores planos; `MAT_PPUEBLO_roca*` (ruido
  procedural de `aplicar_roca`, sin imagen) = colores planos; `MAT_terreno` = `hierba_d.png` tintada de verde + la copia
  `MAT_terreno_roca` plana (0.34/0.27/0.18) por cara según `color_ac.mascara_roca` (nz < 0.50 o atributo > 0.49 con
  nz < 0.82). Es decir: en AC "a pelo" no hay ni estratos, ni grano, ni bump, ni AO, ni transición en ninguna roca, y la
  frontera hierba/roca del terreno es poligonal. Todo lo que pide el plan (caliza con estratos compartida, máscara
  multicapa, AO) pasa por IMÁGENES + UV + cambios en el exportador, que hoy está cerrado por el equipo de 04_export (v1.1).
- Lo que NO depende de CSP y se vería en AC vanilla: texturas difusas horneadas por objeto, `ksMultilayer_fresnel_nm4`
  (shader vanilla de Kunos: txDiffuse + txMask + 4 txDetail + txDetailNM con `multR/G/B/A` y `detailNMMult`; lo usan
  pistas oficiales), normal maps (`ksPerPixelNM`), AO en el canal difuso o por vértice. Lo que sí depende de CSP: VAO
  (`acc-bakeryoptix`, además necesita AC instalado), grass FX, materiales extendidos.

---

## 7. Capturas, cámaras y comprobaciones útiles para el antes/después

- Cámaras existentes en `renderizar_capturas.py`: `02_meta_y_puerto` (l. 55, `tras(0, 80, 14)`), `07_tierra_subida`
  (l. 61), `15_final_puente_roca` (l. 73 y la corrección de l. 299), `19_penon_casino_foto` (l. 88),
  `32_montana_coche_lado` (l. 167), `33_montana_coche_desde_pista` (l. 170), `33b_montana_coche_34` (l. 171),
  `34_roca_lazo_*` y `36_roca_casino_*` (bucle l. 181), más `49-54_piloto_s*`. Según el director, 15 y
  34_roca_lazo_desde_pista están mal colocadas; para juzgar roca desde el coche sirven 33, 49 (s300: salida del túnel),
  54 (s4150: pegado a la roca del lazo) y 51/52 (tierra).
- Comprobaciones automáticas que ya existen y hay que mantener verdes al cambiar geometría: `roca_lazo._comprobar`
  (checks `ok`), `test_roca_lazo.py`, `test_roca_casino.py`, `test_montana_mclaren.py` (manifold, EXACT del túnel,
  presupuesto de tris, A_* sin colisiones), `encaje_mclaren.Sitio.evaluar/holgura` (pista bajo huella, holgura >= 4 m),
  `revisar_tunel.py`, `asentar_objetos.py`, `_rev/nada_en_pista.py`, `kn5_check.py`.
- Para medir sin render: `scratchpad/insp_rocas.py` (este informe) saca por objeto caras por material, bbox y el
  histograma del atributo `roca`; `scratchpad` del python del sistema + `encaje_mclaren` da el perfil del terreno en el
  marco del coche sin abrir Blender.

---

## 8. Qué haría falta para el plan del usuario

Orden propuesto (cada paso con lo que toca, riesgos y de quién depende). Los puntos 8.1-8.3 son el cimiento; 8.4-8.6
son los tres objetos; 8.7 es el exportador, sin el cual nada de esto se ve en AC.

### 8.1 Un solo material de caliza cálida con estratos horizontales, compartido (Blender)

- Crear un node group `NG_caliza_estratos` en un módulo nuevo `03_blender/assets/materiales_roca.py` (python del
  sistema no sirve: nodos) con entradas (tono base, tono junta, periodo de estrato, fuerza de bump, mojado) y salida
  Color/Normal/AO, en coordenadas de MUNDO (`TexCoord.Object` solo coincide con mundo en TERRENO, que está en el origen;
  en `TUNEL_acantilado`, `PENON_roca` y `PENON_puente_roca` el patrón iría en el marco del objeto y no empalmaría con el
  terreno: usar `Geometry.Position`). Contenido: estratos por z de mundo (`TexWave BANDS Z`, periodo 2.5-4 m, distorsión
  3-6, junta oscura y HUNDIDA en el bump, cornisa clara), bancos de 8-14 m con tono alterno (ruido 1D en z), grano
  0.3-1 m, manchas de 15-25 m de baja amplitud (hoy ±50 %, pasar a ±10 %: es lo que se lee como bruma), líquenes/mojado
  bajo z = 1, paleta del usuario (ocre 0.46/0.37/0.24, gris cálido 0.34/0.31/0.26, sombra 0.25/0.20/0.14 lineal).
- Enchufarlo en: `construir_pista._roca_terreno` (sustituye `ROCA_rampa..ROCA_bump`, l. 252-337, manteniendo el nodo
  `Math.002`/`ROCA_mascara` que leen revisores y `color_ac`), `roca_lazo._mat` y `roca_casino._mat` (los 4
  `MAT_PPUEBLO_roca*`: mismo nombre, Base Color enlazado al grupo; dejar `diffuse_color` como color medio para el
  writer), `montana_coche_v2._mat_piedra` para `MAT_MCOCHE_caliza/_clara/_oscura/_monte/_grieta` y `hueso`. Unificar
  paletas: `roca_lazo._PALETA` y `roca_casino._PALETA` definen los mismos nombres con valores distintos (l. 151-155 vs
  98-102); `montana_mclaren._TONO_MONTE` ya copia el tono del terreno (l. 233-237): hacer lo mismo con la caliza base.
- `aplicar_texturas.aplicar_roca` (l. 359-398) y `familia_de` (l. 87-90): o se quita la familia `roca` (el grupo ya
  trae grano/bump) o se extiende a `mat_mcoche_caliza*` y se le baja la amplitud de las manchas. Ojo con
  `integrar_escena._paredes_de_roca` (l. 2727-2730): elige por subcadenas `roca_oscura`/`roca`/`caliza_grieta`/`caliza`.
- Riesgo bajo en Blender (solo materiales; la geometría y los checks no cambian). Verificación: capturas 32/33/19/34/54
  antes/después y las vistas `verif_mc`/`roca_lazo_piloto_*` de los tests.

### 8.2 Llevar la caliza a AC: hornear texturas por objeto (vanilla) y preparar ksMultilayer para el terreno

- Las tres rocas no tienen UV. Opción A (recomendada, AC vanilla): en un paso nuevo del pipeline (`hornear_rocas.py`,
  Cycles, por la cola) hacer `Smart UV Project` (o UV por proyección BOX/triplanar horneada) de `TUNEL_acantilado`,
  `PENON_puente_roca`, `PENON_roca` y las mallas de obra con `MAT_PPUEBLO_*`, hornear Diffuse (+ AO multiplicada, +
  Normal si se pasa a `ksPerPixelNM`) a 4096/4096/2048 px, y asignar un material por objeto `MAT_ROCA_<obj>` con la
  imagen como Base Color (el writer ya la coge: `analizar_material` l. 230-258) y `diffuse_color` blanco (la ganancia
  por canal del writer tintará por el color base: con blanco queda la imagen tal cual; comprobar `gain`/`factor` en
  `construir_textura` l. 270-279 para que no desature). Coste: ~3 texturas de 1-4 MB en el KN5 (`TEX_MAX` 1024 en el
  writer limita a 1024 px: harán falta 2-4 atlas por objeto o subir `TEX_MAX`, decisión de 04_export). Dependencia:
  04_export acepta UV de usuario (`arrays_malla` lee "UV del primer uv_layer (o None)": parece que sí; confirmar con
  el equipo de export que el modo FLAT/BOX no las pisa).
- Opción B (más fiel al plan): `ksMultilayer_fresnel_nm4` para el TERRENO: `txDiffuse` (base), `txMask` RGBA
  (matorral, hierba seca, tierra, roca), `txDetailR/G/B/A` tileables CC0 recoloreadas, `txDetailNM`, `multR..A`,
  `detailNMMult`. Exige: (1) máscara RGBA generada desde `terreno_montana` (pendiente, altura, `mascara_roca`, distancia
  al mar, sectores) a 2048-4096 px con ruido de borde, escrita como PNG en `texturas/`; (2) UV planar del terreno
  (XY normalizadas a la rejilla: trivial en `construir_pista`, 1 capa UV); (3) el writer debe escribir varios slots de
  textura y las propiedades del shader (hoy solo `txDiffuse` + `ksPerPixel`, l. 324-338): cambio en `kn5_writer_opt`,
  `color_ac` y `kn5_check` = equipo de 04_export, después del cierre de v1.1. Hasta entonces, la roca del terreno en AC
  seguirá siendo el plano `MAT_terreno_roca`; al menos se puede darle una imagen (la misma caliza horneada en
  proyección BOX) en `color_ac.separar_roca_terreno` (l. 476-505, hoy `diffuse_color` plano sin imagen).
- Texturas CC0 candidatas (solo listadas, NO descargadas; comprobar nombre exacto y tamaño en la web, licencia CC0):
  Poly Haven `rock_face_03`, `cliff_side`, `rock_wall_08`, `rocky_terrain_02`, `dry_grass`/`brown_mud_leaves_01`;
  ambientCG serie `Rock0xx` (caras estratificadas), `Ground0xx` (tierra seca), `Grass0xx`. 2K JPG/PNG: 2-8 MB cada juego
  (difuso + normal). Se necesita permiso explícito del usuario para bajarlas.

### 8.3 Roca por pendiente (35-40 grados), afloramientos semienterrados y piedras sueltas al pie

- Máscara: en `terreno_montana.construir` l. 2261-2274 bajar el umbral natural de `pendiente suavizada > 1.0` a
  `> 0.70-0.84` (35-40 grados) con transición por ruido, mantener apertura 3x3 y tamaño mínimo (si no vuelven las manchas
  "camuflaje" que quitó la v3 N1), y añadir una banda de "pie de derrubios" (0.5) 6-10 m bajo cada afloramiento. En
  `construir_pista._roca_terreno` (l. 203-206) bajar `talud` de 0.50-0.56 (nz) a 0.70-0.78 para que la propia malla a
  > 38-45 grados sea roca aunque el atributo no llegue, y quitar la excepción `ROCA_llano_hierba` donde el atributo = 1
  (desmontes). Alinear `color_ac.ROCA_NZ` (0.50) y `ROCA_ATR` (0.49) con los nuevos umbrales (04_export). Riesgo:
  el 28 % de las celdas de tierra pasa a candidata: las laderas de 35-45 grados detrás del pueblo y de la tierra se
  volverán roca de golpe; hay que acompañarlo con la paleta (hierba seca/matorral) para que no sea "todo gris".
- Hierba estirada: cambiar `FAMILIAS['hierba'].proy` de `FLAT` a `BOX` en `aplicar_texturas` (l. 59-60) para
  `MAT_terreno` (en Blender) y, en AC, es justo lo que resuelve la máscara multicapa (8.2 B).
- Desmontes-cantera: en `terreno_montana` las caras de corte (`_corte` > 0.3) deberían llevar (a) ESCALONES: bancos de
  6-10 m con berma de 1.5-2.5 m (como `_perfil_corte` del lazo, l. 454-471, pero sobre el campo de 4 m: se puede
  cuantizar `z` en bancos solo donde `_dsm` y pendiente > 0.75, con ruido de fase por xy), (b) `mascara_roca` = 1 solo en
  la cara del banco y 0.3-0.5 en las bermas (hierba seca), (c) ruido ridged de 10-20 m en la pared, y en `integrar.
  explanar` (l. 785-833) sustituir el desmonte 1:1 liso por el mismo perfil en bancos (hoy la pared de 25-45 m tras el
  paddock es un plano). Celda de 4 m: un banco de 6 m es 1.5 celdas, suficiente para que se lea en aéreas; desde el
  coche harán falta además objetos (siguiente punto).
- Afloramientos semienterrados y piedras sueltas (objetos, no terreno): kit nuevo `assets/afloramiento_kit.py` con
  `build_afloramiento(largo 8-40 m, alto 2-8 m, estratos horizontales, seed)` (losa de caliza con 2-4 bancos,
  cornisas y pie en talud, material `NG_caliza_estratos`, ~300-900 tris) y `build_pedrusco(r 0.6-3 m)` (ya existe
  `montana_coche_v2._pedrusco` y `vegetacion_kit.build_roca`, l. 459, `MAT_VEG_roca`: reutilizables). Zona nueva en
  `integrar_escena` (`zona_afloramientos`, después de `zona_tierra`): candidatos donde `pendiente_terreno` (l. 173)
  está entre 0.5 y 1.0, siguiendo la curva de nivel (rotación por el gradiente), base 1-2 m bajo el terreno (medio
  enterrados), 150-300 piezas agrupadas en "cinturones" (no uniforme), 3-6 pedruscos al pie, matas (`vegetacion_kit.
  build_arbusto`) en la repisa superior; exclusiones: pista > 12 m (`_sitio_lejos_pista`, E2-05), casas/calles/caminos
  (`_libre`, `zonas_excluidas`), rocas de los tres generadores (rayo), Loews. Asentar con `asentar_objetos` (prefijo
  nuevo en `SOPORTE_PREF`/`ASENTAR_NO`) y comprobar con `revisar_urbanismo`. En el KN5 son decorado (sin prefijo
  1WALL salvo los que queden a < 6 m del borde). Presupuesto: 300 x 600 tris = 180 k tris, aceptable.

### 8.4 McLaren petrificado: base fundida, escombros, grietas, plantas en juntas, AO, túnel por la rueda

- Terreno bajo la zaga (lo que hace el "islote"): hoy el macizo de la zaga y 210 m de coche están sobre el mar
  (sección 5.3). Dos vías compatibles:
  (a) `terreno_montana.LANDFORMS` (l. 135-190): añadir un CABO que salga del "Espolón del coche" por el lado +n de
  s 400-620 y se prolongue bajo la zaga unos 300-350 m (cordal 60-100 m de alto, s_foot 0.4, acantilado al mar en la
  punta), con la regla de costa anulada dentro de su huella (como se hace con el peñón, l. 1215-1229) y `mascara_roca`
  = 1 en su cresta y en 25 m alrededor de la huella del McLaren (`zonas_excluidas` del spec). Riesgos: el puerto y el
  dique de la meta están a 150-250 m al E (captura 01: el islote toca la dársena): hay que medir la distancia al
  `PUERTO_dique` y a la rotonda de s 300-400 (`B8` cono aplanado); cambia la costa y la QA de orilla (J6/B12); vuelve a
  tocar el encaje (`encaje_mclaren.evaluar`: "pista bajo huella" debe seguir en 0 y la holgura >= 4 m).
  (b) En `montana_mclaren._roca`: convertir la falda del pedestal en un FALDÓN de ladera (talud 30-40 grados en vez de
  70, `_K_FALDA` 0.36 -> 1.2-1.7 fuera de la zona del túnel) que suba hasta la CINTURA del coche (`+0.72R` sobre el
  buje) en los flancos y hasta el techo del capó en el morro, con bloques caídos; en la zona del túnel (x entre -1.3R
  y 1.5R) mantener la pared vertical SOLO en el ancho del portal (21 m + 2 m de sillería) y rellenar el resto. La
  "repisa plana" desaparece porque el umbral del coche queda enterrado; el portal de sillería (`_galeria`/`_portal`)
  pasa a ser la única boca. Riesgos: la cadena Boolean (MANIFOLD) con una falda más ancha (probar con `test_montana_
  mclaren` seeds 0/3/7/11), `pista bajo huella` en s 718-728 (pie del afloramiento del morro, ya al límite: 5.6 m de
  holgura) y los solares de `pueblo_subida_ladera` (`zonas_excluidas` + margen tendrán que crecer 20-40 m: toca
  `urbanismo_spec.json` y vuelve a correr `urbanismo.py`).
- Escombros: ampliar `_bloques` (l. 1562-1584, 28 piezas) a 80-150 `_pedrusco` de 1-6 m repartidos por la falda
  (densidad por altura: máxima en los 15 m sobre `z_agua` y en el contacto con el terreno `ft`), hundidos 30-50 %,
  alineados con la pendiente, + 2-3 bloques grandes (8-15 m) "desprendidos" del macizo con una grieta madre encima.
  Coste ~40 caras por pedrusco: < 6 k tris.
- Grietas: hoy `_GRIETAS` (l. 1339) solo en la carrocería (0.5 % de caras). Añadir una familia de grietas en el MACIZO y
  el faldón (siguiendo los planos de estrato: grietas horizontales en las juntas + 3-5 verticales por bloque de
  `_celda_suave`), con el mismo prisma en V (`_grieta_v`), y rebajar en la carrocería las bandas claras `_bandas_finas`
  (las "franjas de pintura") a surcos de junta con bump del material compartido. Riesgo: cada operando Boolean extra
  es tiempo y un posible derrumbe de EXACT (ya hay red de seguridad, l. 2217-2241); contar tris (`_VEG_TRIS_MAX` no
  aplica a la roca, pero el kn5 trocea a 65 k).
- Plantas en las juntas: en `_vegetacion` (l. 1662 y siguientes) añadir el tipo "junta": puntos sobre los planos de
  bisect (`planos`, l. 853-859) donde la onda `tanh` deja repisa (nz del punto >= 0.6 y nz 0.6 m por encima < 0.3: hay
  pared detrás), matas pequeñas (0.6-1.2 m) y hierba seca colgando; mantener `podar_vegetacion` y `_podar_islas`.
  Presupuesto: subir `_VEG_TRIS_MAX` 3400 -> 8000 (la escena tiene 4.6 M tris; es marginal).
- AO en los huecos: en Blender, hornear AO (Cycles) a atributo de color por vértice de `TUNEL_acantilado`,
  `PENON_puente_roca` y `PENON_roca` y multiplicarlo en `NG_caliza_estratos` (sin UV); en AC va dentro del difuso
  horneado (8.2 A) o por VAO (CSP + AC instalado: no se puede hacer aquí).
- Túnel por la rueda: hundir la rueda delantera (`alto_base` 12 -> ~19-20 m) para que el buje baje a pista + 5 y el arco
  de 21 x 9.5 m quede centrado en la llanta, o hacer el tubo con el perfil de la llanta (arco de radio ~11 m con el
  buje como clave). Toca `zona_tunel` l. 2881 (parámetros), `encaje_mclaren` (z0), y hay que repetir `revisar_tunel.py`
  y la prueba de sección (l. 3205-3250). El portal de sillería (`_portal`/`_galeria`) ya existe; convendría que su
  arco llegase a los radios (sillares más altos, 11-12 m) para que la pista "entre por la rueda".
- Materiales: ver 8.1; además bajar `hueso` (bujes, aros, barra LED) de 0.80 a ~0.55-0.60 lineal y `cristal_pulido`
  a rugosidad 0.5 (hoy 0.26: brillo de plástico).

### 8.5 Roca del lazo: promontorio con paredes verticales, repisas y pinos

- La raíz es el macizo de domos (`_disenar_macizo`, l. 1834-1864) y el registro ya lo apunta (H7, v3: "necesita
  espolones diseñados en `_disenar_macizo`; cambia terrazas y carreteras"). Propuesta concreta en `roca_lazo`:
  1. Después de `M = mac.eval(...)` + ruido (l. 3481-3490), aplicar `M = _bancos_naturales(M, G, seed)`: cuantización en
     bancos de `hb` 8-14 m (fase por ruido 2D de 40-80 m para que los bancos no sean anillos perfectos) con cara a
     80-88 grados y repisa de 2.5-6 m (fracción 0.25-0.4 del banco), restringida a `o > o_b + 8` (fuera del corte y de
     la berma, que ya tienen su perfil) y fuera de los polígonos de rasgos dilatados 6-10 m (plaza, terrazas,
     escaleras, carreteras, cala). Los `_Rasgo` se aplican después y siguen tallando sus paredones de 75 grados.
  2. 2-3 ESPOLONES (`_Macizo.domo` con `a` 3-4 y `b` 0.6-0.9: domos de lados empinados) en el lado NE/N (abierto) y una
     aguja en la cumbre (torre natural de 15-25 m, o un fortín de `italiano_kit`/`edificios_civicos_v2` si se quiere
     el opcional: pieza nueva de ~2 k tris, sin logos).
  3. Repisas = material `repisa` (ya existe) y en `_poblar`: pinos (`vegetacion_kit.build_pino`) en repisas con nz > 0.9
     y ancho >= 3 m (rayo), 1 cada 6-10 m, agrupados; matas en las juntas de banco (nz 0.6-0.9 ya).
  4. Dependencias: `_terraza_nivel`/`_disenar_rasgos` y `_disenar_carretera_cala` leen `M` por `pol.r_donde` para
     trazar frentes y curvas de nivel: deben leer el `M` ya escalonado; después `_campo_alturas` (coronación, cuencas:
     un banco mal cerrado crea una cuenca y `_rellenar_cuencas` la tapa; comprobar `n2['celdas_rellenas']`); todos
     los `checks` (casas vs roca, 0 roca sobre carreteras, matas, contacto, orientación) tienen que seguir en `ok`.
     Rejilla de 1 m: suficiente para repisas de 3 m. Tris: hoy 175 k; con bancos partidos por isolínea subirán un
     20-40 %: vigilar el troceo del kn5 (65 k vértices por malla) y `_VEG`.
  5. Riesgo: H7 se intentó con un ridged isótropo y "represaba cuencas y dejaba pliegues" (registro v3 roca_lazo):
     la cuantización en bancos monótona (solo baja: `M' <= M`) no crea cuencas nuevas por construcción si la repisa es
     horizontal y el drenaje se deja en la fase por ruido; evitar sumar relieve, solo restar.
- Material: 8.1 (los estratos del grupo deben coincidir con los bancos geométricos: usar el mismo `hb` y fase).

### 8.6 Peñón del casino (de paso, mismo criterio)

- `_perfil` (l. 1781-1786): pasar de 3 cotas por banco a cada 1.5-2 m (más vértices por columna: 27 k -> ~80 k tris,
  asumible) y dar a `estrato()` cornisas reales (labio 1.5-3 m, no 0.35-1 m) con una segunda escala de bancos finos;
  `textura()` con ruido a 2-5 m además de los bultos de 14-30 m. Meseta (`plaza`, `borde`, `muelle`): texturizar
  (familia piedra o el grupo de caliza) y oscurecer un 25 %. `vegetacion`: pinos en los labios anchos (hoy solo en
  nz > 0.82 y 22 como máximo).

### 8.7 Orden, dependencias y riesgos globales

1. Terreno (`terreno_montana`: umbrales de máscara 35-40 grados, bancos en desmontes, cabo bajo la zaga) ->
   `preparar_geometria` -> `urbanismo` (si cambia la huella del McLaren) -> `construir_pista` (material, UV planar,
   atributo) -> `integrar_escena` (zona_tunel con nuevos parámetros, zona_afloramientos, `_paredes_de_roca`) ->
   assets (`materiales_roca`, `montana_mclaren`, `roca_lazo`, `roca_casino`, `afloramiento_kit`) -> `aplicar_texturas`
   (familias) -> `hornear_rocas` (nuevo, Cycles) -> inspectores/QA -> capturas (mismas cámaras) -> 04_export (UV, varias
   texturas, ksMultilayer, `color_ac` umbrales) -> `kn5_check`.
2. Nada de lo anterior se ve en AC sin el paso del exportador; conviene cerrar primero en Blender (capturas antes/después)
   y entregar al equipo de 04_export una lista corta: UV de usuario, `TEX_MAX` > 1024 o atlas, slots de textura
   adicionales y propiedades de shader por material, `separar_roca_terreno` con imagen.
3. Riesgos transversales: tiempo de Blender (cada regeneración completa ~1 h con la cola de 6; el bake de 3 objetos a
   4 k en Cycles puede ser otra hora), memoria (5 GB por Blender), presupuesto de triángulos del KN5 (4.6 M hoy; +0.5 M
   estimados), y la regla del proyecto de que `integrar_escena.py`/`preparar_geometria.py` solo los edita el coordinador.
4. Lo que NO hay que tocar para esto: la Loews (terreno congelado, `construir_loews_intacta`), el entorno del peñón
   (r < 1.9) salvo 8.6, el viaducto y el corredor de la pista.

---

## Anexo: cifras de la inspección de `_rev/escena_rev.blend` (04/10, solo lectura)

- `TUNEL_acantilado` (McLaren colocado y taladrado): 56 142 v / 53 453 caras; bbox x -811..-361, y -52..523, z -9..109.
  Caras por material: caliza 16 262 (30 %), caliza_oscura 11 056 (21 %), caliza_monte 6 022 (11 %), MAT_terreno 5 943
  (11 %), hueso 5 485 (10 %), caliza_clara 4 735 (9 %), hueco 2 371, caliza_grieta 792, cristal_pulido 787.
- `PENON_puente_roca` (lazo): 88 627 v / 175 686 tris; roca 121 459, roca_clara 22 574, repisa 24 236, roca_oscura 7 417;
  z -6..107.7. Obra aparte (`PENON_puente_*`, `CASAS_lazo_*`, `VEG_*`, `PENON_carretera_lazo`).
- `PENON_roca` (casino): 13 583 v / 27 162 tris; roca 11 452, roca_oscura 9 570, roca_clara 4 862, repisa 974, plaza 256,
  muro 48; z -26..132.
- `TERRENO`: 266 255 v / 530 448 tris, 1 material (`MAT_terreno`, con `hierba_d.png`); atributo `roca`: 95.5 % = 0,
  1.7 % = 1, 2.8 % > 0.49, 1.8 % en 0.2-0.8; 1.9 % de las caras de tierra con nz < 0.5.
- Render: `BLENDER_EEVEE`, `view_transform Standard`, niebla de mundo apagada. Sin `MAT_MONT_*` ni `MAT_PENON_caliza*`.
- JSON completo: `C:/Users/arcej/AppData/Local/Temp/claude/E--Escritorio-claude-pc-arnau-aseto-corsa/1a7b6c0c-72d8-44ab-af11-95e782d87886/scratchpad/insp_rocas.json`.
