# Entender el terreno y el relieve de Porto Corsa (bloque TERRENO Y RELIEVE)

Lector técnico, 04/10/2026. Solo lectura: no se ha modificado ningún fichero del proyecto ni se ha lanzado Blender.
Fuentes: `03_blender/preparar_geometria.py` (545 líneas), `03_blender/terreno_montana.py` (2682), `03_blender/construir_pista.py` (1662),
`03_blender/integrar_escena.py` (6713), `03_blender/asentar_objetos.py` (2221), `revisar_*.py`, `_rev/nada_en_pista.py`, `urbanismo.py`,
`geometria_3d.json` (12:57), `urbanismo_spec.json`, `RONDA15_PLAN.md`, `_rev/director_final.md`, las figuras QA `renders/qa/terreno_*.png`
y las capturas 01, 07 y 51. Las cifras "medido" salen de un script numpy del scratchpad sobre `geometria_3d.json` (no se ha escrito nada en el proyecto).

Encargo del usuario (PLAN_USUARIO.md, bloque 1 RELIEVE): macizo alto y escarpado detrás del pueblo con crestas y barrancos, acantilados
tipo Amalfi, erosión hidráulica del heightmap (Hydra o NumPy, con máscara del corredor), más desnivel en el tramo de tierra (12-15 %,
zigzags excavados, pared a un lado y caída al otro) y cinco "momentos postal" desde el coche.

---

## 0. Mapa del bloque en 10 líneas

| Paso del pipeline | Fichero / función | Qué hace con el terreno |
|---|---|---|
| 1 (python del sistema) | `preparar_geometria.py` l.481-510 → `terreno_montana.construir_loews_intacta(...)` | Calcula la rejilla de alturas `z_grid` (517 x 515 celdas de 4 m), `es_mar`, `cumbres` y `mascara_roca`; los escribe en `geometria_3d.json` (l.533-541) |
| 1 bis | `terreno_montana.qa_figuras` l.2471-2658 | `renders/qa/terreno_hillshade.png`, `terreno_perfil.png`, `terreno_secciones.png`, `terreno_zoom.png`, `terreno_costuras.png` |
| 2 (python del sistema) | `urbanismo.py` (`Terreno` l.235-275, `tm.CotaSector` l.641) | Lee el terreno del JSON para comprobar casas enterradas/flotantes y decidir muros; NO lo modifica |
| 3 (Blender) | `construir_pista.py` l.1419-1474 | Malla `TERRENO` triangulada (diagonal fija a→a+nx+1), material `MAT_terreno` (l.92-345), atributo por vértice `roca` (l.1471-1474) |
| 4 (Blender) | `integrar_escena.py` `explanar` l.785, `tallar_circulo` l.897, `tallar_cinta` l.937, `_tallar_sendero` l.1088, `_explanar_circulo` l.5045 | Modifica NODOS de la malla TERRENO (y `T['z']` en memoria) bajo edificios, plazas, calles y senderos; marca `roca` en cortes > 2 m (`_poner_celda` l.760-773) |
| 5 (Blender) | `revisar_flotantes/invasores/coches.py`, `asentar_objetos.py`, `revisar_urbanismo.py`, `_rev/nada_en_pista.py` | Leen la COTA REAL de la malla TERRENO (no la del JSON) con la misma triangulación; `asentar_objetos` además mueve nodos (garantías v3) |
| 6 (Blender) | `mejorar_materiales.py`, `aplicar_texturas.py` (`TEX_llano` l.312) | Multiplican hierba sobre el primer Principled de MAT_terreno; la roca es un BSDF aparte |
| 7 (04_export, otro equipo) | `exportar_ac.py` l.71 (`TERRENO` → `1GRASS_terreno`), `color_ac.separar_roca_terreno`, `cierre_ac.terreno_bajo_asfalto` l.400 | En el KN5 la roca del terreno se separa a `MAT_terreno_roca` por el mismo criterio (nz < 0.50 o atributo > 0.49 y nz < 0.82); `kn5_writer_opt.GROUND_PREFIXES` l.68-69 ('1GRASS' → castShadows = 0; igual `kn5_writer_b.SIN_SOMBRA_TOKENS` l.41): el TERRENO NO proyecta sombras en AC |

Orden obligatorio (RONDA15_PLAN l.24-27): preparar_geometria → urbanismo → construir_pista → integrar_escena → inspectores → asentar →
revisar_urbanismo → materiales. Script: `bash 03_blender/_rev/pipeline_escena.sh <logs>` (regenera todo y congela `_rev/escena_rev.blend`).
Prueba aislada del terreno sin tocar el pipeline: `python 03_blender/terreno_montana.py <qa_dir>` (usa `assets/_geom_snapshot_terreno.json`,
copia del 03/10 15:09, ANTERIOR a la apertura de las horquillas de tierra E5) o `GEOM_OUT=... QA_DIR=... python preparar_geometria.py`.

---

## 1. `geometria_3d.json`: estructura (estado 04/10 12:57)

Claves: `paso_m` 2.0, `n` 2600, `largo_m` 5200, `transform` {cx, cy, m_por_unidad 2.91954}, `muestras`, `curvas`, `pianos`, `loews`, `pit_lane`,
`parrilla`, `miradores`, `terreno`, `cumbres`, `mascara_roca`, `nivel_mar` 0.

- `muestras` (2600 dicts, una cada 2 m): `x, y, z, nx, ny, w, lat, sec`. `nx, ny` = normal IZQUIERDA de la marcha (lado +1 = izquierda = mar en
  la recta de meta; lado -1 = derecha = ladera/boxes). `lat` = peralte (fracción). `sec` ∈ {straight 778, bridge 653, tech 619, dirt 506, norm 44}.
  Tierra: s 1430-2440 (índices 715-1220), z 61.2 → 120.7 (cima en s 1864) → 42.7.
- `curvas` (50): `n, s_idx, x, y` EN METROS (desde la ronda 15c; `terreno_montana.curvas_en_metros` l.406-446 detecta y convierte si llegan en SVG).
  Tierra: C12 s 1472 (z 66.5), C13 1524 (72.2), C14 1560 (77.0), C15 1618 (86.0), C16 1698 (97.8), C17 1836 (117.7), C18 1840 (118.3),
  C19 1874 (120.2), C20 1882 (119.2), C21 1930 (112.7), C22 2010 (101.4), C23 2122 (83.0), C24 2206 (70.4), C25 2294 (63.9), C26 2364 (52.4), C27 2510 (32.8).
- `loews` {x 599.55, y -614.6, radio_calzada 12.6, s_idx 1782 (s 3564)}; `miradores` [{s0 2990, s1 3150, side -1, ancho 15}]; `pit_lane` 121 puntos
  (`x,y,z,nx,ny,w`, de s 5010 a 170 por el lado -1); `parrilla` 20 puestos; `pianos` 25 tramos.
- `terreno` {x0 -932.9, y0 -907.8, cell 4.0, nx 517, ny 515, z [266255], mar [266255]}: fila j, columna i → índice `j*nx+i`, x = x0+i*cell,
  y = y0+j*cell. z de -24.5 a 210.4 m; 61 % de celdas son mar. Rejilla = `rejilla_de()` l.848-853: x0 = X.min-220, x1 = X.max+520, y0 = Y.min-220,
  y1 = Y.max+560 (si el trazado no cambia, la rejilla no cambia: lo exige la referencia congelada de la Loews).
- `cumbres` [[x,y,z]] = máximos locales (`_cumbres` l.504-523: ventana 150 m, prominencia 20 m, z > 95, una por 100 m):
  (-44.9, 764.2, 210.4) Monte Porto Corsa; (283.1, 688.2, 185.4); (655.1, -447.8, 155.1) promontorio del casino; (-380.9, 432.2, 126.4) espolón del
  coche; (371.1, -51.8, 107.2) lomas de la recta.
- `mascara_roca` [266255] 0..1 por celda (media 0.029; > 0.5 en el 2.6 % de las celdas; por bandas de distancia a la pista: 0-25 m 4.1 %,
  25-60 m 10.1 %, 60-150 m 9.5 %, 150-400 m 5.1 %).

Medido sobre esta rejilla: laderas naturales (> 100 m de la pista, z > 20): pendiente mediana 0.65, p90 0.88, p99 1.79, 3 % > 100 %.
Orilla (celdas de tierra pegadas al mar): z media 4.6 m, solo el 7.5 % con z > 10 y el 4.8 % con z > 25: HOY CASI NO HAY ACANTILADOS AL MAR.

---

## 2. Cómo se genera el heightmap: `terreno_montana.construir()` (l.915-2445), etapa por etapa

Entrada (desde `preparar_geometria.py` l.501-503): X, Y, Z, sec, Wd, nx, ny de las 2600 muestras, paso, L, curvas en metros, `pit_pts`,
`loews_centro`, `urbanismo_spec.json` (sectores de terrazas), MIRADORES, cell = 4.0, qa_dir, `lat` (peralte). Salida: dict
`x0, y0, cell, nx, ny, z_grid, es_mar, extras{cumbres, mascara_roca, checks, protegido, coastF, terrazas, acantilado, desmonte, obra, techo, suelo, ...}` (l.2433-2439).
`construir_loews_intacta` (l.886-912) envuelve a `construir` con `congelar = assets/_loews_terreno.npz` (referencia FIJA del 03/10 a < 73 m de la Loews).

### 2.1 Rejilla, distancias y máscaras de zona (l.927-1076)
- `gpts` = centros de celda; `peso_fuera_zonas` l.340-351 → `_w_mcl` (0 en la huella del McLaren + 25 m, 1 a +40) y `_w_mcl_c` (+10/+20 m).
- KD-trees: `tree_land` (muestras no bridge), `tree_bridge`; por celda `d_land` (distancia al eje más cercano en tierra), `i_land`, `d_bri`, `d_all`.
  `half_c = Wd/2` de la muestra; `dedge0 = d_land - half_c` (l.1291) = distancia al BORDE del asfalto.
- Lado del mar (`side`, l.965-973). TIERRA PROTEGIDA (l.978-980): unión exacta de discos de radio `r_prot = 30 + 1.7*(z_j - 4)` alrededor de
  cada muestra en tierra (`union_discos` l.354-367) ∪ (d_land ≤ 30). Es lo que decide hasta dónde llega la tierra bajo la pista: cuanto más alta
  va la pista, más ancha la franja de tierra que la rodea (de ahí que las "costas bajo la pista" sean rampas de 60 % y no acantilados).
- Estribos/garganta del viaducto (`ESTRIBO_M` 60, `mar_forzado` l.984 y canal con radio 40-14·ruido l.1011-1016); PEÑÓN DEL CASINO: `elipse_casino`
  l.449-464 (misma elipse que `integrar_escena.zona_casino`: 118 x 78 m, giro 0.5 rad, centro a 190 m del baricentro de C36-38), `casino_zona` (r < 2.2),
  `casino_mar` (núcleo r < 0.9 y bahía -130..40°) l.994-1005; calas lejos de la pista (`_quita`, l.1021-1027).
- `zona_coche` / `w_coche` (l.1030-1039): celdas a < 170 m del túnel (s 380-640) en su lado -1; ahí el desmonte tras las terrazas pasa de 1.15 a `PEND_DESMONTE_COCHE` 2.0.
- `fac_valle` (l.1041-1049): 0 en las bandas de terrazas (+25 m), 1 a 60 m más allá (los valles no excavan tras los patios).
- `es_mar` (l.1052-1076): mar si (lado del mar y > 45 m) o (< 90 m del viaducto) o (> `R_ISLA` 460 m ± 15 % ruido de la pista) o borde de la rejilla
  (70-130 m), salvo protegido; aleta del canal y lagunas interiores eliminadas.

### 2.2 Macizo natural M (l.1079-1165)
- `macizo_base` (l.373-403): `LANDFORMS` (l.135-175) = cordales (polilíneas x, y, h) con perfil cóncavo `h·(1-d/R)^p`, R = h/s_foot (`s_foot` =
  pendiente media al pie: 0.36-0.47; `p` 1.25-1.4), distancia modulada con ruido (`mod`, 150/70 m, l.382-383) → crestas y vaguadas radiales;
  fusión por soft-max (`smax` k 0.12). Landforms: Monte Porto Corsa (cumbre 220 nominal), espolones SO/S/SE/NE/N1/N2/O, **Espolón del coche**
  ((-600,462,110)-(-480,460,150)-(-380,430,150)-(-300,350,118)-(-245,275,80), s_foot 0.47), Lomas de la recta, Promontorio del casino (bajo, G1/G4).
  Después ruido 'ridged' multi-octava 340/170/85/42 m (`ruido_ridged` l.242-248) con amplitud `4 + 24·clip(M/200)` (l.394) y `VALLES` (l.197-216,
  9 canales gaussianos, profundidad `prof · min(M, 80) · fac_valle`). Suelo mínimo 1.2 m.
- TIRÓN A LA RASANTE `_idw_pull` (l.477-501, llamada l.1084): corrección C(x,y) = media gaussiana (σ 100 m, muestras cada 8 m) de (Z_pista - M)
  evaluada en rejilla de 16 m. `peso` = 0.3 en s 200-640 (túnel), 1.0 en el resto (l.1083). Es lo que hace que el macizo PASE por la pista; también
  lo que APLANA la pendiente transversal (ver §6). Decaimiento del tirón positivo solo junto al peñón (l.1091-1099). Suelo de drenaje
  `1.2 + 0.035·dist_mar` lejos de la pista (l.1102-1105); `gaussian_filter(M, 1.0)` (l.1107); borde de la rejilla ≤ 2 m (l.1109-1110).
- Fundido J1 (l.1115-1120): a > 150 m de la pista y > 350 m del peñón el macizo BAJA con smoothstep hasta la costa en sus últimos 170 m (`_wf`).
  Es la regla "costa N/NE en ladera, no en pared": anti-acantilado a propósito.
- `limitar_pendiente(M, cell, PEND_NATURAL_MAX=0.8)` (l.283-306, llamada l.1123): erosión morfológica con cono: ninguna celda del macizo natural
  queda > 80 % respecto a sus 8 vecinas (solo REBAJA). Deja caras planas (conos octogonales) → ridged de 8 m (120/60/30) después (l.1126-1127).
- BARRANCOS N1 (l.1135-1161): cada celda con M > 40 se sigue ladera arriba por el gradiente de M suavizado 20 m hasta "cresta - 30 m"; el ruido de
  55 m leído allí es constante por línea de agua y sus ceros son los ejes: vaguadas de ~32 m de ancho y hasta 9 m de hondo (`_dg`), solo con
  peso `_wf` (lejos de pista y peñón); limitador 85 % solo en sus paredes (`limitar_pendiente_mascara` l.309-325). ES la "erosión" actual: no hay
  simulación hidráulica.

### 2.3 Costa y acantilados (l.1168-1276)
- `coast` = gaussiana σ 12 m de `es_mar`; `coastF` = clip((coast-0.35)/0.3) (0 tierra, 1 mar); tierra protegida nunca pasa de 0.49 (l.1179).
- `dist_mar` con precisión de subcelda (EDT en rejilla x4, l.1184-1192; sin contar el mar forzado bajo la roca del peñón).
- Pendiente de la costa `pend` (l.1197-1218): 0.6 base; 0.6→3.0 a < 200 m del viaducto; fundido doble `_wb` que la ACOTA a 1.3 a > 60 m del viaducto
  (F-07); `_pm = 0.6 + 1.6·clip((M_reg-50)/70)` (más alta donde el macizo regional es alto, acotada a 1.5 lejos del viaducto); 1.2 bajo el túnel
  (s 230-640, < 160 m); 50 (sin regla) dentro del peñón.
- Lejos de la pista (`_lej`, l.1223) y en los acantilados visibles (`_acant`, l.1233-1239: 0 a < 25 m del asfalto, 1 a 45 m; no viaducto < 20 m, Loews < 90,
  peñón r < 1.9, McLaren, meta/puerto): pendiente modulada x0.7..1.1 con ridged 90/45 m (`_rc`), distancia al mar con ruido 25 m (`_nd`),
  `z_reg = 1 + dist_c·pend_c` (l.1244), PIE DE DERRUBIOS (6 m al 35 %, l.1246-1247) y REPISAS de estrato cada 11 m de cota (l.1250-1251).
- `z_land = min(M, z_reg)` (mínimo suave k 5 lejos; k 10 en el canal del viaducto) l.1255-1262; `acantilado = z_reg < M - 0.5` (l.1266) = celdas
  donde manda la costa (se usan en la máscara de roca). Tope del peñón `cap_cas` (≤ 121 m en el contorno, +80 % hacia fuera, -400 % hacia dentro) l.1267-1275.

### 2.4 Reglas duras de pista: corredor, desmonte, terraplén (l.1289-1346)
- `techo = techo_desmonte_c1(z0, dedge0)` (l.720-724, l.1297): llano a `z0 - 0.5` hasta 4.5 m del borde, acuerdo parabólico de T = 10 m y después
  pendiente **1.15** (49°). Cono de s 320-402 aplanado (l.1300-1303).
- `suelo = z0 - 0.6 - max(dedge0 - 6, 0)·s_fl` (l.1310), `s_fl` = **0.55** (29°) lejos, 3.0 a < 40 m del viaducto, 4.0 dentro del peñón.
  Esto FIJA la "caída" máxima junto a la pista: nada puede bajar más deprisa que un 55 % a partir de 6 m del borde (ver §6 y §7).
- Otros ramales (l.1311-1343): mismo ramal = Δs ≤ 40 m y distancia recta ≥ 0.7·Δs (`MISMO_RAMAL`); contra OTROS ramales a < `R_REG` 180 m manda
  el mínimo de techos (mínimo suave k 1.5 a > 8 m, E2-07) y el máximo de suelos. `z_gen = clip(z_land, suelo, techo)` en tierra (l.1345).

### 2.5 Terrazas del pueblo (l.1365-1542) y fosos (l.1549-1628)
- Para cada sector de `urbanismo_spec.json` (`pueblo_subida_ladera` s 660-1085 lado -1 3 terrazas sube; `pueblo_subida_mar` 830-1080 +1 2 baja;
  `pueblo_alto_ladera` 1285-1525 +1 3 sube; `pueblo_alto_mar` 1300-1500 -1 2 baja; `bajada_ladera` 2620-2735 -1 2 baja; `casino_ladera` 3195-3445 +1 1 sube;
  `casino_mar` 3195-3445 -1 1 baja): cota base `Zb` = `mezcla_cota` (l.570-605; la misma que usa urbanismo.py vía `CotaSector` l.608-649),
  perfil `perfil_terrazas` (l.652-665: bordillo -0.4 hasta u 1.0, rampa a ±0.5 en 1.5, bandas LLANAS de 21 m a 0.5/6.5/12.5, rampa del muro en 18.5..21).
- Detrás de la última terraza (o_fin = 21·n): `techo_t = z_ult + 0.4 + techo_tras_terraza(o - o_fin - 1.5, p_desm, w_tope)` (l.1458-1461) con
  `p_desm = 1.15 + 0.85·w_coche` y bancales ligures (`techo_tras_terraza` l.731-739: repisas cada `BANCO_H` 16 m, amplitud `BANCO_A` 1.6) SOLO en
  sectores 'pueblo_*' y FUERA del espolón del coche (`w_tope`, l.1460). Es la cara que el director llama "tajo de cantera" (defecto 3).
  Relleno del foso (`z_land_cl` = cierre morfológico 84 m, l.1380, l.1467-1474) y FOSOS por nivel de agua atrapada (`perfiles_tras_terraza` l.668,
  `nivel_agua` l.699, bucle l.1564-1621, terraplén 55 %).
- `suelo_terr` (l.1516-1518): piso que la caja del pit no puede rebajar.

### 2.6 Resto de reglas duras, en este orden (l.1633-1977)
viaducto `techo_b` (l.1633-1646) → CAJA DEL PIT (l.1651-1725: explanada 28 m llanos a pz-0.6, 22 % hasta `dpe0` = 100-130 m con ruido, luego 1.15
(0.8 pasado el extremo NO), limitador 92 % solo en la pared B10) → LUNGOMARE s 4930-5200 (l.1733-1746) → MIRADORES banco Z-10 solo si el lado mira al mar
(l.1752-1806) → COSTILLAS de erosión en caras de corte (ridged 24/12 m, hasta 2 m, l.1812-1823) y en la muralla del canal (30/15 m, hasta 4 m, l.1827-1834)
→ garantía `z ≤ techo` a < w/2+1 (l.1837-1838) → MAR: fondo -4, orilla continua por distancia firmada (playa 8 m al 40 %, tope 300 %) natural (l.1846-1859)
y junto a la pista (`_wj6`, l.1867-1877), pozos rellenos (l.1882-1885), protegida ≥ 0.3 (l.1890) → LOEWS congelada (l.1892-1916: `w_c` smoothstep 40→65 m)
→ isla de horquillas R < 15 m (l.1923-1932) → picos convexos G4 (l.1937-1950) → nodos del túnel s 410-536 (l.1954-1963) → `bajar_bajo_asfalto`
(l.755-826, llamada l.1966: garantía POR TRIÁNGULO con el plano peraltado, baja solo vértices bajo la calzada) → `desmonte`/`obra` (l.1975-1977).

### 2.7 Máscara de roca y cumbres (l.2244-2299)
`pendiente = |∇z|` (l.2244). `roca` = laderas NATURALES con pendiente suavizada (2.5 celdas) > 1.0 ± 0.1 ruido (apertura 3x3, manchas ≥ 12 celdas)
∪ (acantilado y pendiente > 0.85 ± 0.1) ∪ (z > 185 y pendiente > 0.5), sin desmontes; desenfoque 1 celda (2 en aristas > 1.5); en CORTES
`_corte = clip((z_land - z - 1)/3) · clip((pend - 0.75 ± 0.1)/0.3)` desenfocado 1.5 celdas x 1.25 (l.2272-2274); dilatada una celda en el mar; pie de
acantilado a ras de agua = 1 (l.2287-2290); escalón de la garganta = 1 (l.2293-2296); a < 90 m de la Loews la máscara v2 exacta. `cumbres = _cumbres(zg)` (l.2299).

### 2.8 QA impresa y `checks` (l.1980-2431)
Costuras por terraza (objetivo < 0.6 m), cobertura s0..s1 por sector con causa, geografía sube/baja + aviso 'bastión', foso tras la última terraza
(agua atrapada ≤ 1.5 m), contorno del peñón, `pct_pista_con_pared_roca` (terreno > Z+8 a 25 m), `muestras_terreno_bajo_eje_1p2`, `pendiente_max_natural`,
`pct_natural_gt_100`, `celdas_invaden_pista` (debe ser 0), `celdas_invaden_viaducto`, `protegido_bajo_cero`, `borde_pct_mar`, `coche_120m_pct_ge_90`
(macizo ≥ 90 m a 120 m detrás del túnel), `loews_ref_dz_max`, `hierba_asfalto`. Figuras: `qa_figuras` (hillshade con roca marrón y terrazas ámbar,
perfil Z(s) con terreno a ±40 m, 13 secciones transversales, zooms, costuras).

---

## 3. `construir_pista.py`: malla TERRENO, atributo `roca` y nodos del material

- Rebaje bajo el pit lane (l.1424-1447): vértices a < semiancho+0.6 de la cinta del pit bajan a `min(zin, zout) - 0.12`.
- Malla (l.1448-1468): un vértice por celda (`j*nx+i`), dos triángulos por celda `(a, a+1, a+nx+1)` y `(a, a+nx+1, a+nx)` con DIAGONAL FIJA
  a→a+nx+1 (N2: render, kn5, asentar e inspectores ven la misma superficie); `shade_smooth`; materiales `[M_TER, M_FONDO]` (los dos = `MAT_terreno`).
  Sin UV (`new_mesh_obj` l.28-41 no crea capas UV: el material usa `TexCoord.Object`). 266 255 vértices / ~530 k triángulos.
- Atributo `roca` FLOAT POINT = `G['mascara_roca']` (l.1471-1474). `_poner_celda` del integrador lo sube en cortes > 2 m (`(z - z_new - 1)/2`).
- `mat_terreno()` (l.92-183): color por altura (`ShaderNodeMapRange` -4..170 → rampa fondo marino / arena / hierba baja / monte / cumbres) x parches
  de pradera (ruido 0.005); ROCA por pendiente: `talud` = smoothstep(N.z + ruido ±0.04, 0.50→0.56) (nodo `ROCA_nz_ruido`), por atributo
  `umb` = smoothstep(roca + ruido fino ±0.15 + grueso ±0.18, 0.47→0.51) x (1 - smoothstep(N.z, 0.78→0.86)) (`ROCA_llano_hierba`: en lo llano
  manda la hierba aunque el atributo diga roca); `mx_r` = 'Math.002' = MAXIMUM(talud, atributo), etiqueta `ROCA_mascara`: ES la máscara que leen
  los revisores, `aplicar_texturas` y `04_export/color_ac.py` (umbral 0.50 / 0.49 / 0.82).
- `_roca_terreno()` (l.185-345): caliza cálida procedural (`ROCA_ruido_manchas` 0.045, `ROCA_rampa` 0.30/0.235/0.15 → 0.46/0.37/0.245), estratos
  `ROCA_estratos` (TexWave BANDS Z, escala 0.12 = periodo 2.6 m, distorsión 6), grano, meteorización; `ROCA_bump` (0.40); BSDF propio `ROCA_bsdf`
  mezclado con el de hierba por `ROCA_mezcla` (MixShader, factor = Math.002). `aplicar_texturas.py` (l.306-324, `TEX_llano` 0.60→0.78) multiplica la
  textura de hierba solo sobre el primer Principled y solo en lo llano: no vela la roca.
- Consecuencia para el plan 3 del usuario (ksMultilayer_fresnel_nm4): la "máscara RGBA por pendiente y altura" NO existe aún como imagen ni como
  capa UV; hoy hay un solo escalar por vértice (`roca`) y una mezcla procedural en Blender que el KN5 reduce a DOS materiales planos
  (`MAT_terreno` / `MAT_terreno_roca`, `color_ac.py` l.410-420). Dónde nacería: `terreno_montana.construir` l.2244-2298 ya calcula `pendiente`,
  `zg`, `dist_mar`, `dedge0`, `acantilado`, `desmonte`: ahí se pueden sacar 4 canales (matorral / hierba seca / tierra / roca) como arrays
  más de `extras` → `geometria_3d.json` → atributos o vertex colors en `construir_pista` → imagen por proyección XY (bloque materiales/export).

---

## 4. `integrar_escena.py`: explanadas y tallados sobre la malla TERRENO

Todas escriben a la vez en `T['z']` (copia en memoria del JSON) y en `TERRENO.data.vertices[k].co.z` vía `_poner_celda` (l.760-773); `_proteger_pista`
(l.746-758) impide rellenar a < 3 m del borde y excavar bajo `z_eje - 0.6 - max(d-6, 0)·0.55` a < 12 m (misma ley que `suelo` de §2.4). `z_terreno`
(l.145-155) es BILINEAL sobre `T['z']`; `_z_tri` (l.990-1002) usa la triangulación real.

| Función | Líneas | Qué talla | Quién la llama |
|---|---|---|---|
| `explanar(ob, margen 3, alcance 28, desmonte 1.0, terraplen 0.6, zb, roca)` | 785-833 | Rectángulo local del objeto + margen a `zb`; desmonte 1:1 hasta la ladera natural (`_zmax_alrededor`, tope 150 m); terraplén 0.6 solo hasta 0.6·alcance; marca `roca` si corta > 2 m | `explanar_edificios` 849-874 (tribunas, HOTEL con 1.2), `zona_torres_pit` 886, ayuntamiento/campanile 1646-1649, losa `CALLE_plaza_ayto` 1676, paseo-mirador 4127/4151, caminos 5208 (ermita, sin roca), 5632 |
| `tallar_circulo(cx, cy, r, zb, desmonte 1, alcance 18)` | 897-935 | Plazuela circular; talud 1:2 de 18 a 45 m; devuelve -1 (no talla) si el último anillo exige > 0.3 m | `zona_edicolas` 1290 (se descarta si `pendiente_terreno` > 0.8) |
| `tallar_cinta(pts3, semiancho, desmonte 1, terraplen 0.7, alcance 6, dz -0.15, evitar, roca, modo)` | 937-988 | Banqueta por polilínea 3D (cada celda toma el tramo más cercano); `terraplen=None` = solo rebaja | paseo 4071, calzadas con rasante propia 4608 (desmonte 3.0 si muros), subida al hotel, espolón del casino 5891 |
| `_tallar_sendero` (modo='sendero') | 1088-1222 | Varias ramas, taludes según la ladera (`desm = clip(g+0.5, 1, 2)`, `terr = clip(g+0.4, 0.7, 1.4)`, alcance 25), roca solo en cortes > 2.5 m, garantía sobre `_z_tri` | `_construir_sendero` 5217 (CIMA, ERMITA) |
| `_explanar_circulo(cx, cy, r, zb, alcance_t 12)` | 5045-5078 | Corta Y rellena (mirador del sendero), nunca roca | 5153 |
| `_garantia_losa`, `_garantia_cinta` | 1014-1039, 1041-1086 | Bajan los 3 nodos del triángulo real si asoma hierba sobre una losa/calzada | edicolas 1295, plazas 1677/4152, `_camino` 4611, 5892 |

Otras zonas que LEEN terreno y cambian con él: `zona_tunel` (l.2849-2882: `montana_mclaren.build(... z_fondo=-(pf.z+8), enterrado='ambos',
alto_montana=(83.2, 65.0), talud_deg=(38, 52))`; con `terreno='auto'` J10 la caliza a < 3-7 m del TERRENO pasa a hierba/roca del monte y
`encaje_mclaren.evaluar()` mide el enterrado); `zona_tierra` (l.1711-1757: árboles cada 52 m y 10 rocas por `_sitio_lejos_pista`, pacas de la C26);
`pacas_tierra()` (E6: fila continua donde el terreno cae > 2.5/3.5/6 m a 10/15/25 m: MÁS caídas = más filas de pacas); `_senderos_montana`
(A* evita laderas > 100 %, rasante ≤ 15 %, desmonte/terraplén ≤ 2.5 m: con otro relieve los senderos CIMA/ERMITA se replanifican solos);
`zona_camaras` (peanas sobre TERRENO); `zona_coches` (`asentar_coche` quita filas con desnivel > 0.8 m o roca encima); `_muros_relleno`
(muro de mampostería donde la calzada va > 1 m sobre su apoyo); `zona_montanas_fondo` (l.2486-2495: DESACTIVADA cuando el JSON trae `cumbres`:
el anillo de horizonte del plan 7 no existe hoy); `zona_casino` → `roca_casino` lee el terreno (`_preparar_relleno`, `_foso_tierra`, GEOM) y
`roca_lazo` no (está en el mar).

---

## 5. Inspectores y herramientas que reaccionan a un cambio de terreno

| Script | Cómo lee el terreno | Qué detecta / hace si el relieve cambia |
|---|---|---|
| `terreno_montana.construir` (QA propia) | el propio `z_grid` | `checks` de §2.8; `celdas_invaden_pista` ≠ 0, `hierba_asfalto`, `pendiente_max_natural`, fosos > 1.5 m, costuras > 0.6, `loews_ref_dz_max` > 0, bastión, cobertura < 100 % |
| `urbanismo.py` | `Terreno.zs_malla` (l.262-272, triangulación real) para "asoma", bilineal para "flota"; `CotaSector` para la cota de calles/casas; `construir_muros` pone muro donde el terreno a ±1.5 m tiene escalón ≥ 0.8 m | QA 'casa_enterrada', 'hierba sobre calle', muros nuevos/desaparecidos; HAY QUE RE-EJECUTARLO tras cualquier cambio de terreno (lee `geometria_3d.json`) |
| `construir_pista.py` | `T['z']` del JSON | arcén exterior a `min(ez-1.6, zt-0.35)` (`_zt_arcen` l.1171), pretiles `MUROC_*` con pie hasta `min(ze-2.5, zt-1.5)`, rebaje bajo el pit lane; aceras altas en sectores de terrazas |
| `revisar_flotantes.py` / `revisar_invasores.py` / `revisar_coches.py` | `z_terreno` con los vértices REALES de la malla TERRENO y la diagonal a→a+nx+1 (flotantes l.18-42) | objetos flotando/enterrados, vegetación asentada en ladera, coches con desnivel |
| `asentar_objetos.py` | `T['z']` sustituido por las coordenadas de la malla (l.205-212); `TER_OK` exige nx·ny vértices y matriz identidad (l.432-436); BVH `loop_triangles` (l.264-312) | MUEVE nodos: `garantia_senderos` l.916 (±2.5 m, nunca a < 6 m del asfalto), `garantia_losas_terreno` l.680, `subir_plazoletas` l.743, `ajustar_bancales` l.775, `ajustar_losas` l.356; asienta árboles (`apoyo_arbol` l.1266, 5 rayos, desnivel > 1.6 m → se quita), coches (`asentar_coche` l.1545), props; informe `renders/qa/asentar.json` (`terreno_v3`) |
| `revisar_urbanismo.py` | `z_ter_tri` l.786 (triángulos del render) | 'casa_enterrada/flotante', 'losa_tambor/volada/hierba', 'sendero_volado/enterrado' (aire > 0.25), 'bancal_mal_asentado', 'ermita_desnivel', 'cipres_flotando'; objetivo 0 fallos (hoy 23, `director_final` defecto 10) |
| `revisar_tunel.py` | NO mira el TERRENO: 9 rayos contra `TUNEL_acantilado` | Un terreno que asome dentro de la galería (s 410-536) no lo vería: lo cubre `tunel_nodos_bajados` de terreno_montana (l.1954-1963) |
| `_rev/nada_en_pista.py` | `TERRENO` está en `PERMITIDOS` (l.34) | No marca el terreno; los "hoyos" del terreno junto al asfalto los mide `04_export/revisar_fisica_ac.py` (190 hoyos de 0.65 m, ronda 4) |
| `renderizar_capturas.py` + `_rev/camara_segura.py` | ray-cast de escena | Recoloca cámaras aéreas que caen dentro de un macizo más alto (NO toca piloto/desde_pista/túnel); las 6 vistas de piloto están en s 300, 800, 1700, 2900, 3400, 4150 (l.283-288) |
| `04_export` (otro equipo, no tocar) | `TERRENO` → `1GRASS_terreno`; `color_ac.separar_roca_terreno` (nz < 0.50 ∨ roca > 0.49 ∧ nz < 0.82); `cierre_ac.terreno_bajo_asfalto`; `kn5_writer_opt.GROUND_PREFIXES` l.68-69 ('1GRASS_terreno' → castShadows = 0) | Más caras de roca → más triángulos en `MAT_terreno_roca`; un macizo que da sombra a la pista no la dará en AC mientras el terreno sea prefijo de suelo sin sombra (dependencia a avisar a 04_export) |

Ficheros de referencia que condicionan cambios: `assets/_loews_terreno.npz` (referencia fija; si la rejilla cambia, `construir_loews_intacta`
avisa y reconstruye por el método v1), `assets/_geom_snapshot_terreno.json` (test aislado, desactualizado respecto a E5), `urbanismo_spec.json`
(`zonas_excluidas` = huella del McLaren: nada del plan ni de las reglas v3 dentro de ella + 25 m).

---

## 6. Dónde aplicar la erosión hidráulica NumPy con máscara del corredor

**Hydra (github.com/ozikazina/Hydra)** es un addon de Blender (GPU, ModernGL) que erosiona un heightmap de imagen u objeto DENTRO de Blender.
No está instalado (descargar/instalar exige permiso del usuario) y el terreno de este pipeline se genera en python del sistema y se regenera
en cada pasada: una erosión manual en Blender no sería reproducible y además TODAS las reglas de §2.4-2.6 tendrían que volver a aplicarse
después. Útil como mucho para un experimento visual sobre `_rev/escena_rev.blend`. **Recomendación: NumPy dentro de `terreno_montana.py`**, con el
esquema de `dandrino/terrain-erosion-3-ways/simulation.py` (erosión hidráulica en rejilla: lluvia → agua que fluye por el gradiente → capacidad de
sedimento → disolución/depósito → evaporación, más "slippage" de talud; todo con `numpy` + `scipy.ndimage`, que ya importa el módulo).

**Punto de inserción**: `construir()`, sobre el campo NATURAL `M`, entre el limitador de pendiente + ridged (l.1123-1127) y el bloque de barrancos N1
(l.1135-1161), es decir ANTES de la regla de costa (l.1168) y de todas las reglas duras. Razones:
1. Todo lo que viene después (`z_land = min(M, z_reg)`, `techo`/`suelo`, terrazas, fosos, pit, mirador, Loews, `bajar_bajo_asfalto`) se calcula a
   partir de `M` y RESTAURA por construcción el corredor, las bandas llanas y las zonas protegidas: la erosión no puede dejar hierba sobre el
   asfalto ni romper una terraza aunque la máscara falle.
2. `desmonte = tierra & (z_grid + _baja_nat < z_land - 0.3)` (l.1975) compara contra `z_land`, que ya incluiría la erosión: las vaguadas erosionadas
   NO se pintan como "corte de la pista" en la máscara de roca (si se erosionara después, habría que sumarlas a `_baja_nat`, l.1834/1947).
3. El bloque N1 de barrancos (l.1135-1161) es el sustituto actual de la erosión: con la simulación, se quita o se deja con `_dg` reducido (si no, dobles canales).

**Máscara `w_eros`** (0 = no se toca, 1 = erosión completa), con arrays que YA existen en ese punto:
`clip((dedge_land - 30)/50)` con `dedge_land = d_land - half_c` (l.986/1291) → 0 a < 30 m del borde del asfalto, 1 a 80 m
× `clip((d_bri - 60)/40)` (viaducto) × `clip((d_loews - 90)/20)` (`R_LOEWS_INTACTA`) × `_w_mcl` (McLaren) × `clip((r_cas - 1.9)/0.3)` (peñón)
× `fac_valle` (0 en las bandas de terrazas + 25 m, l.1041-1049) × `(~es_mar)` × `clip((_dm1 - 15)/15)` (`_dm1` = distancia al mar, l.1102)
× `clip((d_pit - 150)/50)` (distancia a `pit_pts`, calcular con `cKDTree(pxy)` como en l.1655) × `_wf`-like opcional para intensidad creciente lejos.
Aplicación: `E = erosion_hidraulica(M, cell, w_eros, rng, iters)`; `M = M·(1-w) + E·w`; después `limitar_pendiente_mascara(M, cell, 0.85-1.0, w > 0.05)`
(l.309) para que las paredes de los canales no pasen del tope deseado (hoy 0.85 en barrancos) y `gaussian_filter` 0.5 celdas opcional.
Dentro de la simulación, las celdas con w = 0 se tratan como lecho fijo (sin erosionar ni depositar, agua que pasa).
Resolución: 4 m (517x515, ~0.27 M celdas) → cada iteración es barata (decenas de ms); rasgos ≥ 12-16 m, suficiente para el "look" Pixar. Si se
quiere más fino, simular en una rejilla x2 (`_zoom_a` l.222) y volver a 4 m con `map_coordinates`; la malla TERRENO sigue a 4 m (`cell` es único
en todo el pipeline: `T['cell']`, `rejilla_de`, Loews .npz, inspectores).

**Verificación**: `checks['pendiente_max_natural']`, `pct_natural_gt_100` (hoy 0.28 %), `coche_120m_pct_ge_90`, costuras/fosos/cobertura
(no deberían cambiar con `fac_valle`), `loews_ref_dz_max` (= 0.000), `terreno_hillshade.png` (vaguadas visibles en el macizo N y en las
laderas del lazo), `terreno_perfil.png` (Z(s) y ±40 m sin cambios dentro de 30 m). Riesgo propio: el depósito al pie de las laderas puede subir
celdas de la vega/orilla: la máscara de mar/orilla y `np.minimum` con la z previa en `_dm1 < 40` lo evitan.

---

## 7. Macizo alto y escarpado detrás del pueblo y acantilados al mar sin romper pista/pueblo/rocas

### 7.1 Qué hay hoy detrás del pueblo
Medido (lado -1, ladera): `pueblo_subida_ladera` (s 660-1090, Z pista media 43): terreno a 60 m media 55 (máx 67), a 120 m media 83 (máx 123),
a 200 m 51, a 300 m 17 → el "Espolón del coche" (cumbre 126 m en (-381, 432)) es una loma estrecha que CAE detrás; el valle 'barranco del pueblo
alto' (l.200-201) pasa justo detrás. `pueblo_alto` (s 1100-1430, Z 59): a 60 m 74, a 120 m 63, a 200 m 32 → también baja. El Monte Porto Corsa
(210 m, (-45, 764)) está a 350-450 m al NNE de ambos pueblos: desde el piloto en s 800 queda lejos y en bruma (capturas 05/39: "cono beige").
Las laderas naturales no pasan del 80 % por `PEND_NATURAL_MAX` (l.124/1123), y donde superan 100 % la máscara de roca ya las pinta de caliza.

### 7.2 Palancas y dónde están
1. **Formas**: `LANDFORMS` l.135-175: subir `h` de 'Espolón del coche' (150 → 190-220) y de 'espolón SO' (178/135/92 → +40), acercar su cresta a
   60-90 m detrás de la última terraza (o_fin = 63 m en pueblo_subida_ladera), `s_foot` 0.47 → 0.65-0.8 (pie más empinado), `p` 1.3 → 1.6 (perfil
   más cóncavo = crestas afiladas). Más crestas: amplitud ridged l.394 (`4 + 24·clip(M/200)` → `6 + 40·...`), octavas l.242.
2. **Escarpado**: `PEND_NATURAL_MAX` 0.8 global. Para crestas y barrancos > 100 % sin tocar el resto: sustituir la llamada de l.1123 por un limitador
   con `smax` POR CELDA (p. ej. 0.8 a < 150 m de la pista, 1.3-1.6 en la máscara del macizo trasero, usando `limitar_pendiente_mascara` dos veces o una
   versión con `d4 = smax_cell·cell`). La máscara de roca (l.2261: pendiente suavizada > 1.0) lo pintará de caliza sola.
3. **La cara detrás de las terrazas** (`techo_tras_terraza` l.731-739 + `p_desm` l.1458): un macizo más alto hace esa cara MÁS ALTA (tajo de 60-100 m al
   49-63 °): es exactamente el defecto 3 del director. Opciones: (a) activar los bancales también en el espolón del coche (`w_tope` l.1460 excluye
   `w_coche`) y subir `BANCO_A`/bajar `BANCO_H` (repisas más marcadas), (b) subir el tope de las costillas de 2 m (l.1823) a 4-6 m en caras > 20 m,
   (c) interponer una berma de 15-25 m entre el patio (o_fin + 1.5) y el arranque de la cara (cambiar `o - o_fin - TM/2` por `o - o_fin - BERMA`),
   de modo que el macizo se lea como montaña con pie, no como pared de cantera; (d) mantener `PEND_DESMONTE_COCHE` (plan T1: ≥ 90 m a 120 m del túnel,
   `checks['coche_120m_*']`).
4. **Acantilados al mar (Amalfi)**: hoy la orilla es baja (§1) porque (i) `r_prot = 30 + 1.7·(z-4)` (l.978) empuja la costa lejos de una pista alta,
   (ii) `pend` de costa 0.6 base y ACOTADA a 1.3 (`_wb`, F-07) / 1.5 (`_pm`) lejos del viaducto, (iii) el fundido J1 (l.1115-1120) baja el macizo a la
   costa en 170 m, (iv) `suelo` 0.55 (l.1310) impide una caída > 29 ° a partir de 6 m del borde. Cambios: en tramos elegidos (p. ej. lado +1 de s 170-402
   y s 616-820 bajo el pretil, lado -1 de la recta 2770-2976 y bajo bajada_ladera, costa N/NE) reducir `r_prot` (p. ej. 20 + 0.8·(z-4)), subir `pend` a
   2.5-4.0 y quitar/aflojar los topes F-07 (`_wb` l.1203-1206) y `_pm` (l.1210-1211), reducir el alcance del fundido J1 (170 → 60 m o `_wf` = 0 en
   sectores), extender las costillas `_wcf` (l.1829-1831, hoy solo en el canal) a todo `acantilado & _acant`, y dar un `s_fl` por celda ≥ 1.5-3.0 en
   el lado del mar manteniendo una berma de 6-8 m (`d_llano`) para arcén + guardarraíl + cierre físico. El pie de derrubios y las repisas (l.1246-1251)
   ya existen y mejoran la lectura; `acantilado` → roca automática (l.2267).

### 7.3 Protecciones que ya existen (no romper)
- Pista: corredor `techo`/`suelo` (§2.4), garantías `z ≤ techo` a < w/2+1 (l.1837) y `bajar_bajo_asfalto` (l.1966): cualquier macizo queda tallado.
- Pueblo: bandas llanas a `Zb + h_k` independientes de `M` (l.1454); las casas están en u ≤ 18 < o_fin; `fac_valle` protege +25 m; fosos rellenos.
  Pero `urbanismo.py` (`construir_muros`, QA 'casa_enterrada' con `zs_malla`) y `revisar_urbanismo.py` DEBEN volver a pasarse.
- McLaren: `_w_mcl` (huella + 25 m), `zonas_excluidas`, `checks['coche_120m_*']`; `montana_mclaren` lee el terreno real (J10) → verificar con
  `assets/encaje_mclaren.evaluar()` (enterrado/holgura) tras cambiar el macizo cerca de (-600, 350).
- Rocas: peñón `r_cas < 1.9` fuera de todas las modulaciones v3 (`cap_cas` l.1272, `pend` 50 l.1218); Loews `d_loews < 90` + referencia .npz; roca del lazo en el mar.
- Viaducto: `techo_b` l.1633-1646, `mar_forzado` del canal, estribos.

---

## 8. Más desnivel en el tramo de tierra

### 8.1 Perfil Z(s): dónde se decide y límites
`preparar_geometria.py`: `Z_CTRL` l.332-350 (cotas por curva), `EXTRA_CTRL` l.352-358 (2445 → 43 "escalón de la bajada"), anclas de la cima
`s_fix` l.362-365 (C17 = s_cima-110, C18 = s_cima, C19 = +90, C20 = +150, con `s_cima` = muestra más al norte del lazo), fusión de controles a < 16 m
(l.370-375), `PchipInterpolator` (l.381), `smooth_closed(Z, 25)` (l.384), **limitador `MAXG = 0.165·paso` (16.5 %, 4 pasadas adelante/atrás, l.386-392)**,
`smooth_closed(Z, 15)` (l.393). Tierra: `sec == 'dirt'` viene de `02_trazado/trazado_v1.json` (458 muestras) + relleno de huecos < 120 m (l.42-58) → s 1430-2440.
Ancho 10 m (`W_SEC` l.417), peralte x0.6 (l.400), horquillas abiertas a R ≥ 12.5 (`HORQ_TRAMOS` l.246-247: s 1800-1940 y 2300-2440, E5).

Medido hoy: subida s 1500-1800 al 13-15 % (máx 16.5 %), cima 120.7 m en s 1864, bajada s 1900-2300 al 13-16 % (tramos al tope 16.5 %), 2300-2500 al 14-15 %.
**El perfil ya está POR ENCIMA del máximo 12-15 % que pide el usuario**: con `MAXG = 0.15·paso` la cima apenas cambia (~120 m) porque el suavizado
ya la recorta; con 12 % bajaría a ~105 m. "Más desnivel" NO puede venir de la rasante: con 434 m de subida al 15 % el máximo teórico es
61 + 65 = 126 m, y el inicio (C12, 66.5 m) lo fija `pueblo_alto` (s 1285-1525). Alternativas de rasante: bajar `EXTRA_CTRL(2445)` y C27 para alargar
la bajada; o hacer 'dirt' s 1300-1430 (conflicto con aceras/bordillos de pueblo_alto en `construir_pista`). En las horquillas (C18-19 cima, C26) la
rasante debe quedar ≤ 8-10 % (fisica: borde interior colapsado en s 2365 al 16.5 %): poner controles a ±40 m de cada apex.

### 8.2 El desnivel que se VE es del terreno, no de la rasante (director, defecto 6)
Medido a 25 m del borde en tierra: pared > +8 m en algún lado 23 %, caída < -8 m 48 %, pared en un lado Y caída en el otro **5 %** (a 50 m: 22 %).
Por tramos (medias a 25 m, lado +1 / -1): 1400 +6.6/-6.5, 1500 +2/-8, 1600 -1/+3, 1700 -1/+14, 1800 +6/+1, 1900 -11/+7, 2000 -7/-6, 2100 -5/-4,
2300 -4/-2, 2400 0/-11. Causas en el código: (1) el tirón `_idw_pull` con peso 1.0 (l.1083) arrastra el macizo a la rasante y aplana la
pendiente transversal del espolón S que el lazo sube; (2) `techo` al 1.15 desde 4.5 m: pared de 49 ° pero solo si el macizo natural es más
alto; (3) `suelo` 0.55: la caída está limitada a 29 ° a partir de 6 m; (4) entre ramales (R_REG 180) manda el ramal más bajo.

Cambios concretos (todos en `construir`, por celda según `s` de la muestra más cercana `g_near·paso` ∈ [1430, 2440]):
- `peso` del tirón (l.1083): 0.5 en tierra (como 0.3 en el túnel) para conservar la ladera natural.
- `techo_desmonte_c1(z0, dedge0, pend=...)`: `pend` como ARRAY (hoy escalar 1.15): 1.8-2.0 en tierra en el lado INTERIOR de cada curva
  (signo de `_kap[g_near]`, l.1924-1927; `_lat0` l.1300) = pared de roca; la máscara `_corte` (l.2272) la pinta de caliza con estratos.
- `s_fl` (l.1306): 1.2-1.5 en tierra en el lado EXTERIOR, con `d_llano`/berma de 6-8 m (arcén + pacas `pacas_tierra` + cierre `cierre_ac`).
- Zigzags excavados: ya hay dos horquillas (18-19 en la cima, 26 abajo) y las curvas 21-25; entre dos ramas a distinta cota el `min(techo)`/`max(suelo)`
  entre ramales (l.1331-1342) deja una pared de 49 ° (mínimo suave k 1.5) y la isla `_isla` (l.1928-1932) un suelo a borde interior -0.6: con
  `pend` 2.0 esa pared sube a 63 °. Si se quiere un espolón entre ramas que SUPERE el techo de la rama alta, hay que exceptuar `R_REG` para
  ese par (hoy imposible por diseño).
- Visibilidad desde la cima (postal 2: "bahía entera abajo"): comprobar con `_sitio_lejos_pista`/`zona_tierra` que árboles y pacas no cierren la vista
  en s 1840-1900 lado +1 (hacia el S/SE la bahía está a 400-600 m: ver hillshade).

### 8.3 Lo que se rompe si se toca la rasante de tierra
`urbanismo.py`/terrazas no (no hay sectores en 1525-2620); `pacas_tierra`, `CARRERA_paca_tierra` de la C26, cámaras de tierra, senderos CIMA
(arranque en `salidas` del plan, A* ≤ 15 %), `HORQ_TRAMOS`, el estribo de nada; `04_export/cierre_ac.chaflan_horquilla` y `revisar_fisica_ac`
(cambios de pendiente > 8 %/m) sí reaccionan.

---

## 9. Momentos postal (cámaras existentes y lo que falta)
`renderizar_capturas.py` l.283-288: piloto a 1.4 m en s 300, 800, 1700, 2900, 3400, 4150 (`49..54_piloto_s*`). Para los cinco encuadres del usuario:
salida del túnel del McLaren → cámara nueva en s 545-600 (boca de salida s 540; la 49 está ANTES del túnel); cima de la tierra → s 1860-1880 mirando
hacia S/SE; puente del casino → viaducto s 3632-4936 (la 54 en s 4150 ya sirve); bajada a la horquilla de la fuente → confirmar con el usuario si es
la rotonda Loews (s 3564) o la horquilla C26 (s 2364); recta del puerto → s 0-170 / 5050-5200 (vista de la 02/29). Todas pasan por `camara_segura`
salvo las de piloto.

---

## 10. Qué haría falta para el plan del usuario (bloque RELIEVE): cambios concretos, riesgos y dependencias

| # | Cambio | Fichero / líneas | Riesgo | Dependencias / verificación |
|---|---|---|---|---|
| 1 | `erosion_hidraulica(M, cell, w, rng, iters)` NumPy (dandrino simulation.py) + máscara `w_eros` (§6) entre l.1127 y l.1135; retirar/atenuar barrancos N1 | `terreno_montana.py` | Depósito en la vega/orilla; doble canal con N1; coste ~10-30 s por pasada | `python terreno_montana.py <qa>` con `assets/_geom_snapshot_terreno.json` (actualizar la copia a la geometría actual primero: es anterior a E5); `checks` de §2.8; hillshade |
| 2 | Macizo trasero: LANDFORMS (Espolón del coche, espolón SO) más altos y empinados; limitador por celda (0.8 cerca / 1.3-1.6 en el macizo); ridged más fuerte | `terreno_montana.py` l.135-175, 394, 1123 | Tajo de cantera tras las terrazas (defecto 3) si no se hace la berma/bancales de §7.2.3; McLaren más enterrado (B11); bruma lejana (render) | `checks['coche_120m_*']`, `foso_*`, `pct_natural_gt_100`; `encaje_mclaren.evaluar()`; re-ejecutar `urbanismo.py` (muros, casas) y `revisar_urbanismo` |
| 3 | Berma + bancales + costillas de 4-6 m en la cara tras la última terraza (también en el espolón del coche) | `techo_tras_terraza` l.731-739, l.1458-1461, l.1812-1823 | Fosos tras la terraza (QA ≤ 1.5 m); `bastion` | QA de fosos/costuras/cobertura; capturas 05/06/39/50 antes/después |
| 4 | Acantilados: `r_prot` menor, `pend` 2.5-4, quitar topes F-07/`_pm`, J1 a 60 m, costillas en todo acantilado, `s_fl` por celda en el lado del mar con berma | l.978, 1197-1218, 1115-1120, 1829-1831, 1306-1310 | Pretiles/guardarraíles con pie al aire (construir_pista `_pretil` pie min(ze-2.5, zt-1.5)); pares tierra/mar > 3 m (J6); cámaras aéreas dentro de roca; `revisar_fisica_ac` caídas en la escapatoria (cierre_ac ya cierra a w/2+6.75) | `checks['pendiente_max']`, orilla continua; `kn5` más caras en `MAT_terreno_roca`; avisar a 04_export (TERRENO sin sombras: `GROUND_PREFIXES` de kn5_writer_opt) |
| 5 | Tierra: `MAXG` por muestra (0.15 en dirt, ≤ 0.10 en ±40 m de los apex); peso del tirón 0.5 en dirt; `pend` de desmonte 1.8-2.0 interior; `s_fl` 1.2-1.5 exterior con berma 6-8 m | `preparar_geometria.py` l.386-392; `terreno_montana.py` l.1083, 720-724/1297, 1306-1310 | Cima no sube (§8.1); más pacas (`pacas_tierra`), coches/cámaras quitados por desnivel; senderos replanificados | `terreno_perfil.png` (pared ±40 m), medida "pared un lado Y caída otro" (hoy 5 % a 25 m) como KPI; capturas 07/08/21/51 |
| 6 | Máscara de 4 capas (matorral/hierba seca/tierra/roca) exportada como `extras['capas']` → JSON → atributos en TERRENO | `terreno_montana.py` l.2244-2298; `construir_pista.py` l.1471-1474; `preparar_geometria.py` l.539-541 | Ninguno en geometría; el shader y el KN5 (ksMultilayer, UV planar, imagen) son del bloque materiales/export | `color_ac.mascara_roca` debe seguir leyendo `roca` |
| 7 | Cámaras postal nuevas (túnel salida, cima) | `renderizar_capturas.py` l.283-288 | — | capturas antes/después desde las mismas cámaras (método del usuario) |

Orden recomendado: 5 (rasante y reglas de tierra, sin erosión) → 2+3 (macizo + cara tras terrazas) → 4 (costa) → 1 (erosión, al final, con todo lo
anterior estable) → 6. Tras cada paso: `python preparar_geometria.py` (QA_DIR a una carpeta de prueba), `python urbanismo.py`, y solo cuando la QA
esté limpia `bash _rev/pipeline_escena.sh` (Blender por la cola) + `renderizar_capturas.py`. Nada de esto toca `04_export`.
Dependencias con otros bloques: ROCA INTEGRADA (material de caliza/estratos y afloramientos: hoy procedural en `_roca_terreno`), McLAREN
(`montana_mclaren` lee el terreno), VEGETACIÓN (treeFX usará las mismas máscaras de pendiente/altura), PUEBLO (urbanismo re-ejecutado), EXPORT
(sombras del TERRENO, `MAT_terreno_roca`, hoyos junto al asfalto).
