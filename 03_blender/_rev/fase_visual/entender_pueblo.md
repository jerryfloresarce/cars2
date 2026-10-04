# Entender el PUEBLO y el URBANISMO de Porto Corsa (lectura técnica para la fase visual)

Fecha: 04/10/2026. Lector: bloque "pueblo y urbanismo". No se ha modificado ningún fichero del proyecto; Blender no se ha lanzado. Para obtener los motivos de rechazo de solares (solo salen por log) se ejecutó `python urbanismo.py --salida <scratchpad> --sin-qa` (python del sistema, salida al scratchpad, sin tocar `urbanismo.json` ni `renders/qa`).

Rutas relativas a `E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender/`. Las líneas son las del estado del 04/10 (urbanismo.py 12:44, urbanismo_escena.py 12:23, revisar_urbanismo.py 12:17, urbanismo.json 12:58).

---

## 0. Resumen en diez líneas

1. El pueblo es un **plan urbano por terrazas** calculado fuera de Blender (`urbanismo.py`, shapely) a partir de un **contrato numérico único** (`urbanismo_spec.json`) que también usa `terreno_montana.py` para tallar el terreno: bandas llanas de 21 m paralelas a la pista, con calle, fachada, solar, patio y muro de contención en cotas fijas respecto a la calzada.
2. `urbanismo.json` (193 casas, 207 solares, 7 sectores) es el único contrato entre el plan y la escena: `urbanismo_escena.py` lo instancia (calles del `caminos_kit`, casas del `casas_kit_v2`, muros, rampas, escaleras, plazas), lo llama `integrar_escena.zona_pueblo_urbanismo()`, y lo leen también `construir_pista.py` (bocas de enlace, acera alta) y `revisar_urbanismo.py` (ejes del plan).
3. Las casas son **rectángulos de 5.5-11 x 4-11 m separados 1.0-1.6 m**, una por intento a lo largo de la línea de fachada, con el césped del terreno entre ellas, delante (1 m entre acera y fachada) y detrás (patio hasta el muro). Esa separación es la causa directa del "césped entre casas" que señala el usuario.
4. La variedad actual es: 5 colores de estuco, 3-6 plantas (pesos 3/4/3/1), tejado a dos aguas 72 % o plano, puerta + escaparates con toldo (70 %), balcones (75 % de las plantas), contraventanas abiertas/cerradas. Todo con **materiales planos sin UV**: un atlas exige dar UVs a la malla del kit y apartar esos materiales del pase de texturas tileables.
5. Las terrazas vacías de `pueblo_subida_ladera` (capturas 05/06/39/40/50) no son un fallo del terreno sino del **presupuesto de restricciones del plan**: zona excluida del McLaren (calles cortadas 6 m antes), patio libre de 4 m delante del tramo alto de cada rampa (278 intentos rechazados), calles que se quedan sin acceso en coche (3 de 8 pasan a peatonales), fachadas a > 4 m de calle (808) y terreno no llano en s 920-1000 (248). Solapes rechazados: 2149.
6. Los "muros como aletas" vienen de combinar la rejilla de terreno de 4 m (la transición del muro, 2.5-3 m, se difumina ±2 m) con muros de **altura constante por tramo** (`muro3d` usa la mediana) que la coronación no sigue; está apuntado como N2/F-06 "no arreglado" en `RONDA15_PLAN.md`.
7. QA: el plan exige 0 fallos propios (25 controles, `assert` en `urbanismo.py:2841`) y la escena pasa por `asentar_objetos.py` (casas no se mueven; informa flotante/enterrada) y `revisar_urbanismo.py` (casa_casa, casa_calle, casa_muro, casa_pista, flotantes, fondos de saco, losas, senderos). Hoy: 23 fallos en la escena, 4 del pueblo (CASAS_casa.066 + CAMINO_muro.132, .146 flotante, losa_hierba de dos plazas).
8. Para **densificar** hace falta tocar el plan (solares pegados en manzanas, medianeras exportadas, aceras y patios como losas del plan) y el kit (parámetro `laterales` ya existe; soportales, plantas trapezoidales), y actualizar tres controles de QA (solar_solar, calle_solar, casa_casa) sin cambiar claves del JSON.
9. Para el **atlas** hace falta: UVs en `_MB` del kit, nuevo prefijo de material excluido de `aplicar_texturas`/`mejorar_materiales`, alpha test en `kn5_writer_opt` para decals (ropa, macetas), y piezas nuevas en `calle_kit` (tendedero, bolardo, alcantarilla).
10. Nada de esto cambia el contrato de 21 m: se puede hacer sin volver a tallar el terreno; lo que SÍ depende del bloque de relieve es la coronación de los muros y el césped de los patios (una pasada de "escarpa" sobre los nodos del TERRENO).

---

## 1. Mapa de ficheros y orden en el pipeline

| Paso | Fichero | Ejecuta | Lee | Escribe |
|---|---|---|---|---|
| 1 | `preparar_geometria.py` + `terreno_montana.py` | python sistema | svg/curvas, `urbanismo_spec.json` | `geometria_3d.json` (muestras + rejilla `terreno` cell 4 m) |
| 2 | `urbanismo.py` | python sistema (numpy/scipy/shapely) | `geometria_3d.json`, `urbanismo_spec.json` | `urbanismo.json`, `renders/qa/urbanismo_<sector>.png`, `urbanismo_detalle_<sector>.png` |
| 3 | `construir_pista.py` | Blender | geometria + `urbanismo.json` (`_BOCAS`, acera alta D2-10) | `porto_corsa.blend` (PISTA, TERRENO, ACERA_, BORDILLO_) |
| 4 | `integrar_escena.py` → `zona_pueblo_urbanismo()` (l.1605) → `urbanismo_escena.construir()` | Blender | `urbanismo.json` | objetos CAMINO_*, CASAS_casa, CASAS_zocalo, CALLE_plaza*, ITAL_fuente, VEG_plazoleta |
| 5 | `asentar_objetos.py` | Blender | escena | `renders/qa/asentar.json` |
| 6 | `revisar_urbanismo.py` (+ `revisar_urbanismo_plot.py`) | Blender (+python) | escena, `urbanismo.json` (env `URBANISMO`), `asentar.json` | `renders/qa/urbanismo_informe.json`, `huellas.json`, `urbanismo_mapa_*.png` |
| 7 | `mejorar_materiales.py`, `aplicar_texturas.py` | Blender | materiales MAT_CASAS_* | blend |
| 8 | `04_export/exportar_ac.py` + `kn5_writer_opt.py` | Blender | escena | kn5 (NO tocar: otro equipo cierra v1.1) |

Kits del pueblo (todos en `assets/`, procedurales, sin UV, materiales Principled de color plano):
- `casas_kit_v2.py` (casa de estuco; `build_casa`, `build_manzana`).
- `edificios_civicos_v2.py` (`build_ayuntamiento` l.432, `build_campanile` l.551, `build_hotel` l.619, `build_boxes` l.780). `integrar_escena.load_mod` (l.40-43) carga `<nombre>_v2.py` si existe, así que `M['edificios_civicos']` es la v2; `edificios_civicos.py` es la v1 (misma API, muros ciegos).
- `caminos_kit.py` (`build_camino` l.553: asfalto/tierra/adoquin/muelle; `build_valla_cierre` l.744; `build_cartel` l.826; `build_muro_contencion` l.886).
- `calle_kit.py` (`build_farola` l.251, `build_guirnalda` l.295, `build_maceta` l.340, `build_toldo_mercado` l.380). No hay bolardo, alcantarilla ni tendedero.
- `italiano_kit.py` (`build_fuente` l.899, `build_pergola` l.1105, `build_bancal` l.957, `build_ermita` l.713, `build_capitella` l.811, `build_hito` l.863, cipreses/olivos).

---

## 2. El contrato de terrazas y sectores

### 2.1 Sección transversal (urbanismo_spec.json l.3-14, 73-75; terreno_montana.perfil_terrazas l.652-666)

`u` = metros desde el BORDE del asfalto hacia el lado del sector; `z` relativa a la cota de la calzada `Z(s)`; `k` = índice de terraza (0 = pegada a la pista).

| u (m) | Qué hay | Cota |
|---|---|---|
| 0..1.0 | bordillo/arcén: terreno a Z-0.4 | -0.4 |
| 1.0..1.5 | rampa del bordillo (`bordillo_hasta` 1.5) | hasta h_0 |
| 1.5..6.0 | **calle** de 4.5 m (`calle_desde` 1.5, `ancho_calle` 4.5; eje en 3.75) | h_k |
| 6.0 | `ancho_margen_pista`: nada de solar más cerca del asfalto | |
| 7.0 | **fachada** (`fachada_desde`) | h_k |
| 7..18 | **solar** (`fondo_max_casa` 11; `FONDO_MAX_SUBE` = 9 en sectores que suben, urbanismo.py l.204, 866-867) | h_k |
| 18..21 | **patio** (`patio_hasta` 21) | h_k |
| 18.5..21 | transición del muro del lado de la terraza BAJA (`transicion_muro` 3.0 en el spec, l.1368 de terreno_montana; defecto 2.5 de `perfil_terrazas`) | h_k → h_k+1 |
| 21(k+1) | **muro de contención**; la terraza k+1 es llana desde ahí exactamente | h_k+1 |

Alturas: `h_k = sg * (0.5 + 6.0 k)` (`altura_terraza_1` 0.5, `altura_terraza` 6.0), `sg` = +1 sube / -1 baja (`sentido_terrazas`, urbanismo.py l.219-229 = terreno_montana l.531: manda el campo `sentido` del spec; si falta, los `_mar` bajan). Sectores que bajan: la calle de k >= 1 arranca a `calle_desde_muro_baja` 4.5 m del muro (l.604-606, 813). Travesías cada `travesia_cada_m` 150; rampas de `rampa_largo_m` 45 (13 %), 5 m de ancho (calzada 4 + dos muretes de 0.5, l.147-150); escaleras de 1.6 m (l.151-152). Zona excluida: huella del McLaren con `margen` 4 (l.76-803).

**Cota base única** (`terreno_montana.CotaSector` l.611-650, `mezcla_cota` l.572-609): la terraza k está a `Zb(x,y) + h_k` donde `Zb` es una mezcla ponderada de la Z suavizada (gauss 7.5 m) de las muestras del sector que ven el punto por su lado, con talud entre ramas enfrentadas (horquillas). `urbanismo.py` la precalcula en una rejilla de 1 m (`preparar_cota` l.639-657) y la usa para TODO (`zxy` l.719, `zf` l.730). Regla de oro del spec (`_doc`): "Nadie cambia estos números sin cambiar los dos" (terreno y plan).

### 2.2 Sectores (spec l.15-72) y resultado actual (urbanismo.json)

| id | s0-s1 | lado | n | sentido | casas | plazoletas | calles | rampas | escaleras | muros | rechazos terreno |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pueblo_subida_ladera | 660-1085 | -1 | 3 | sube | 41 | 3 | 8 (3 peatonales) | 2 | 4 | 23 | 248 |
| pueblo_subida_mar | 830-1080 | +1 | 2 | baja | 51 | 4 | 2 | 2 | 2 | 11 | 113 |
| pueblo_alto_ladera | 1285-1525 | +1 | 3 | sube | 30 | 2 | 3 | 2 | 3 | 8 | 15 |
| pueblo_alto_mar | 1300-1500 | -1 | 2 | baja | 28 | 2 | 2 | 1 | 1 | 7 | 31 |
| bajada_ladera | 2620-2735 | -1 | 2 | baja | 17 | 1 | 2 (1 peatonal) | 0 | 1 | 8 | 4 |
| casino_ladera | 3195-3445 | +1 | 1 | sube | 12 | 1 | 2 | 0 | 0 | 4 | 129 |
| casino_mar | 3195-3445 | -1 | 1 | baja | 14 | 1 | 2 | 0 | 0 | 0 | 553 |

Convención de lado (RONDA15_PLAN l.39-41): `pos(s, lado, u) = p + lado*n*(w/2+u)`, n = normal IZQUIERDA; lado +1 = izquierda de la marcha (mar en la recta de meta). "ladera"/"mar" en el id NO coincide siempre con el lado (pueblo_alto está intercambiado por la geografía real).

Banda llana medida (`terrazas[k]` en el JSON): en los sectores que suben la banda real es u 1.25..16.75 (casas hasta 17.75) y el fondo máximo 9 m; en los que bajan u 0..17.5 y 10-11 m. El plan desplaza eje de calle/fachada hacia fuera solo si el terreno medido lo obliga (`medir_bandas` l.806-883).

---

## 3. urbanismo.py: cómo se decide el plan

Orden de `Sector.construir()` (l.2024-2060): `preparar_cota` → `medir_bandas` → `mapa_costuras` (l.659) → `construir_bandas` (l.1143) → `posiciones_travesias` (l.751, cada 150 m centradas) → `planificar_rampas` (l.929) → `construir_calles` (l.1100) → `construir_enlaces` (l.1205) → geometrías de travesías (`_travesia_geom` l.1308) → `construir_rampas` (l.1428-1655) → `rescatar_islas` ×2 (l.2153) → `quitar_huerfanas` (l.2232, calle sin rampa → peatonal 2.5 m) → `podar_rampas` (l.2204) → `construir_travesias` (l.1359) → `construir_muros` (l.1656) → `construir_plaza` (l.1832) → `construir_solares` (l.1875) → `recortar_colas` (l.2093) → `separaciones` (l.2001). Después `verificar()` (l.2516) y `main()` escribe el JSON (l.2825-2830) y aborta si hay un fallo (l.2841).

Todo se construye como polilíneas offset de la pista sin pliegues (`curva_offset` l.460) y se valida contra la rejilla de terreno de dos maneras (`Terreno` l.235-275): lo que **asoma** (enterrado) se mide con la malla triangulada igual que el render (`zs_malla` l.262), lo que **flota** con la bilineal (`FLOTA='bil'`, l.184). Las piezas se recortan donde el terreno discrepa (`TOL_CALLE` 1.2/0.6, `TOL_BORDE` 0.8/0.6, `TOL_SOLAR` 0.5/1.0, `TOL_MURO`, `TOL_RELLENO` 0.6, l.157-171) y donde hay costuras del terreno (l.196-200).

### 3.1 Calles, enlaces, travesías, rampas, escaleras, muros (lo que no son casas)

- Calle k: eje en `u_calle` (3.75 + 21k; 4.5 m del muro en los que bajan), trozos ≥ 25 m, z = Zb + h_k + 0.05 (l.1100-1140). k = 0 → `tipo 'servicio'` (asfalto), k ≥ 1 → `'terraza'` (adoquín) o `'peatonal'` 2.5 m.
- Enlace: en cada extremo de cada trozo de la calle de servicio; prolonga 3 m, gira 90° y entra perpendicular hasta 0.4 m del asfalto (`U_BOCA_ENLACE`), con valla CERRADA a u 2.6 (l.1205-1305). `construir_pista._BOCAS` abre la acera alta en esas 22 bocas.
- Travesía: calle transversal de k a k+1 solo si tiene rampa o escalera; en la última terraza llega 6 m más allá de la calle y genera una `salida` para los senderos del integrador (l.1345-1356).
- Rampa: relleno de 45 m al 13 % entre muros verticales (`muros_rampa` con z_base = terreno, z_top = calzada) + meseta 5 m + codo a nivel (l.1428-1655); delante de su tramo alto no hay casas a < `GAP_RAMPA_ALTO` 4.0 m (l.180, 1178-1189).
- Escalera: ida y vuelta (2 tramos de 5 m + descansillo 1.6×3.2) o recta, con pasarela a nivel que cruza el talud del muro (`_planificar_escalera` l.1032-1074); casas a ≥ `GAP_ESC` 2.4 m (l.187).
- Muro: en u = 21(k+1), tipo `contencion` (z_base = terraza baja, z_top = alta), `ultimo` (sube: hasta terreno de atrás + 0.3) o `parapeto` (baja), solo donde el escalón real a ±1.5 m es ≥ 0.8 m y hay calle a ≤ 15 m, trozos ≥ 8 m, cortado en travesías/codos/pasarelas, remate escalonado en los 8 m finales (l.1656-1734, 1780-1823) y prolongado hasta 30 m fuera del sector (l.1736).

### 3.2 Cómo se colocan las casas (`linea_fachada` l.1152-1196, `construir_solares` l.1875-1998)

1. Línea de fachada = offset de la pista a `u_fachada` (7.0 + 21k, o más fuera si la banda lo exige); en los sectores que bajan se desvía alrededor de las rampas (`desvio_rampa`). Atributos por vértice: `fmax` (fondo máximo local, reducido frente a rampas/escaleras construidas: l.1177-1193) y `uf`.
2. Recorrido en t desde 1.0 m hasta `largo-5`: se sortea ancho `a0 ∈ {6.5, 7, 7.5, 8, 8.5, 9, 9, 10, 10, 11}` y fondo `f0 ∈ {8, 9, 10, 10, 11, 12, 12}` (l.1899-1900) y se prueban hasta 9 variantes decrecientes `(a0,f0) … (6.5,7) (6,6) (5.5,6) (6.5,4.5) (5.5,4)` (l.1914-1915).
3. Rectángulo `rect_fachada(p, T, (fx,fy), a, f)` (l.518): pivote `p` en el centro de la fachada, fachada mirando `(fx,fy) = -lado * normal_izquierda(T)` (hacia la calle), cuerpo hacia atrás.
4. Rechazos en orden (l.1922-1962; contadores `motivos`): `fondo` (fmax < 5, o < 4 frente a rampa), `lejos_calle` (centro de fachada a > 4 m de un trozo de calle de su terraza), `rampa_alta` (patio libre de la rampa), `solape` con `Fp` = propio (travesías, rampas +0.65, escaleras +2.4, muros +1.0/0.5, enlaces +0.8, plaza +1.0) ∪ calles +`GAP_CALLE_SOLAR` 0.85 ∪ aceras del kit 0.8 m a inglete ∪ zona excluida ∪ asfalto +5.6 ∪ pit +8 ∪ costuras +2.6; `fuera_banda`; `pliegue`; `vecino` (buffer 1.02 m del solar anterior, l.1987); `terreno` (`esquinas_ok` l.1825 + huella completa a 1 m: flotante > 0.5, enterrada > 1.0, rango > `RANGO_CASA` 1.0).
5. Si cabe: `contador += 1`; 1 de cada `PLAZOLETA_CADA` 12 solares con huella llana pasa a plazoleta (l.1970-1975); plantas `choices([3,4,5,6],[3,4,3,1])`, ≤ 3 si fondo ≤ 6.5 (l.1976-1978); `seed = (base_seed + k*1000 + contador) % 100000`; `z_suelo = Zb + h_k` (sin +0.05). Avance `t += a + U(1.0, 1.6)` (l.1988).
6. `separaciones()` (l.2001-2022) exporta `sep_x_neg`/`sep_x_pos` (distancia al vecino por cada lado en ejes locales de la casa; 99 = libre). Hoy nadie los consume.

Formato exportado por solar (docstring l.112-114): `cx,cy` (centro), `px,py` (pivote de fachada), `ancho, fondo, rot_z = atan2(fy,fx) - pi/2, fx, fy, z_suelo, seed, plantas, s, poligono[4], sep_x_neg, sep_x_pos, terreno_esquinas[4]`.

Límites de fondo: `fondo_max = min(spec 11, u_hi_casa - u_fachada, 9 si sube)` (l.865-867), menos lo que quitan rampas (`f_r`, `f_alto`) y escaleras (`f_e`), por tramo de s (l.1184-1196). Zócalo: lo decide la escena, no el plan (ver 4).

### 3.3 QA propia del plan (verificar l.2516-2622, verificar_huellas l.2319-2420, verificar_v1 l.2423-2513)

25 contadores que deben ser 0: `solar_solar` (otro solar dentro de buffer 0.98 m), `solar_elemento`, `solar_fuera_banda`, `calle_cerca_pista`, `elemento_cerca_pista`, `solar_terreno` (-0.6/+1.2), `calle_terreno`, `muro_terreno`, `relleno_asoma`, `salto_z_calle`, `salto_z_costura`, `travesia_huella`, `rampa_huella`, `plazoleta_huella`, `plaza_huella`, `calle_borde`, `solar_huella`, `terraza_vacia`, `casino_contorno`, `zona_excluida`, `enlace_asfalto`, `rampa_pared`, `escalera_solar`, `calle_solar` (≥ 0.85), `escalera_sin_destino`. Además informativos: `huecos` > 12 m entre solares de una fila (hoy 515 m, objetivo < 300), `separacion_min_solares` (1.02), `calle_cola`, `enlace_desnivel`. PNG de QA por sector (`dibujar` l.2720, `dibujar_detalle` l.2746; ejemplo `renders/qa/urbanismo_detalle_pueblo_subida_ladera.png`: solares con desvío de esquinas, muros con z_base/z_top, rampas naranja, escaleras moradas).

### 3.4 Por qué hay huecos (datos del log de la ejecución al scratchpad)

`pueblo_subida_ladera`: rechazos `solape 2149, lejos_calle 808, rampa_alta 278, terreno 248 (s 920-1000, desvío hasta -2.0 m), fuera_banda 196, fondo 181, vecino 63`. Descartes: rampa t953/t951/t946 k0 (terreno asoma 0.4-1.0 m sobre la calzada), travesía 1 "no cabe", rampa trav. 2 y 4 "sin calle superior al final del codo", calles 1_0, 1_2, 2_1 "sin rampa posible → peatonal". Huecos de fila: T0 695-759 (57 m) y 816-935 (95 m), T1 701-811 (90 m) y 821-970 (45 m), T2 858-990 (54 m). Son exactamente los prados de la captura 39 (terrazas 1-2 con calles de grava, rampas y una plaza con fuente sin casas) y 50 (muros que asoman de la ladera a la derecha).
`casino_mar`: `terreno 553` (s 3320-3440, desvío hasta ±4.5 m: la banda de T1 no es llana ahí); `casino_ladera`: `terreno 129` en s 3320 → prado vacío de la captura 10.
`pueblo_subida_mar`: `rampa_alta 257` (patios de las rampas en el lado mar).

---

## 4. urbanismo_escena.py: instanciación en Blender (`construir(ctx, ruta)` l.64-634)

`ctx` lo da el integrador (l.1626-1628): `clone, root_col, LIB, M, lib, log, z_terreno, rnd, zocalo_global (= integrar._zocalo_global l.106-140), mat_simple, dist_pista`.

| Elemento del JSON | Función | Objeto creado | Material |
|---|---|---|---|
| calles `servicio` | `camino3d` l.147 → `caminos_kit.build_camino(tipo='asfalto', lineas=False)` | `CAMINO_calle` | `MAT_CAMINO_asfalto_calle` (copia aclarada, l.120-145) + bordillo 0.25 |
| calles `terraza`/`peatonal`, travesías | `build_camino(tipo='adoquin')` | `CAMINO_calle` / `CAMINO_travesia` | adoquín Voronoi + **acera de 0.8 m y 0.15 de alto** a cada lado (caminos_kit l.600-612) |
| enlaces + vallas | `camino3d` asfalto + `valla_enlace` l.347 → `build_valla_cierre` 4.6 m | `CAMINO_enlace`, `CAMINO_valla` | |
| rampas | asfalto sin líneas + `muro_rampa_sillares` l.215-281 (piezas de 4 m de `build_muro_contencion`, pretil 0.9) | `CAMINO_rampa`, `CAMINO_muro_rampa` | sillares |
| escaleras | `escalera` l.292-319: peldaños de 0.17 m, fábrica maciza hasta terreno-0.3 | `CAMINO_escalera` | `MAT_URB_escalera` |
| muros | `muro3d` l.171-191 → `build_muro_contencion(alto = mediana(z_top-z_base) ∈ [0.6, 7.5])`; cortados en discos de fondos de saco/salidas (`_cortar_muro` l.374-403, l.625-629) | `CAMINO_muro` | sillares del kit |
| solares `casa` | `casa_var` l.407-413 (caché por `(plantas, ancho/0.5, fondo/0.5, seed % 3)` → `hk.build_casa(LIB, plantas, ancho, fondo, seed)`, **sin `laterales` ni `lod`**) + `clone` en `(px, py, z_suelo+0.02)` con `rot_z`; `zocalo_global` si `min(terreno_esquinas) < -0.3` (l.564-575) | `CASAS_casa` (+ hijo `CASAS_zocalo`) | MAT_CASAS_* |
| solares `plazoleta` | `poligono('CALLE_plazoleta', canto hasta terreno)` + 2 árboles `VEG_plazoleta` + pérgola cada 2 (l.576-594) | `CALLE_plazoleta`, `ITAL_pergola` | adoquín plaza |
| plazas | `poligono('CALLE_plaza')` + `ITAL_fuente` (l.595-608) | | |
| extremos sin destino | `fondos_de_saco` l.431-534: disco r 4.5-6.5 `CALLE_plaza_fondo` + fuente o 2 cipreses; o unión entre dos extremos | | |

`info` devuelto (l.113-115) alimenta `PUEBLO_INFO` y `PLAZAS_POLY` del integrador (l.1630-1634): `salidas` (arranque de senderos), `ejes`/`huellas` (despeje final: ningún árbol dentro de casas, plazas ni a < 3.5 m de una fuente), `fuentes`, `sin_destino`.

Lo que el integrador añade al pueblo fuera del plan: plaza del ayuntamiento + campanile en s 1160/1130 lado +1 con losa `CALLE_plaza_ayto` 26 m explanada (l.1635-1686), calle adoquinada desde el final de la calle de servicio de `pueblo_subida_mar` (v3 N1 s 1120, con muro de sillares donde el relleno > 0.3 m), edícolas en salidas (`zona_edicolas` l.1224), farolas/macetas/guirnaldas SOLO en la acera de la pista en `TRAMOS = (630,1090),(1270,1550),(2490,2750),(3190,3450)` (`zona_calle` l.2545-2600; no en las calles del plan), árboles de `enriquecer_vegetacion` (l.6498) podados por `despeje_final` (l.6537). `zona_pueblo()` (l.1493-1598, `fila()`) es la versión antigua y solo se usa si falta `urbanismo.json`.

---

## 5. casas_kit_v2.py: la casa

- API `build_casa(parent, plantas=4, ancho=10, fondo=12, color=None, seed=0, tejado='auto', name=None, **params)` (l.996-1038). Pivote en el centro de la fachada, fachada en y=0 mirando +Y, cuerpo hacia -Y, base z=0. `params['laterales']=(izq,der)` (medianera lisa de un quad si False, l.846-851), `params['lod']` (1 = fachada plana ~600-1100 tris), `params['auditoria']`. Presupuesto: ≤ 5000 tris por degradación de carpintería `NIVELES` (l.149-151, 1021-1032). `build_manzana` (l.1041-1073) ya hace casas **pegadas** con `laterales=(i==0, i==n-1)` en línea recta.
- Geometría (`_generar` l.748-989): columnas de huecos `_columnas(ancho, 2.5)` (l.330-339: deja 0.7 m por lado; 4.5 m de frente → 1 columna); planta baja = porton `_puerta` (l.599) + escaparates `_escaparate` (l.628) + toldo a rayas 70 % (`_toldo` l.563, colores rojo/verde/azul); plantas altas = ventanas con marco de piedra en anillo, vidrio rehundido 6 cm y contraventanas abiertas/cerradas (`_ventana` l.446-522, `_elegir_cerradas` l.723), balcón de forja 75 % de las plantas (`_balcon` l.535-560); laterales y trasera con el mismo ritmo; zócalo 1 m (`D_ZOCALO` 0.12), pilastras en L 0.32, bandas de forjado, cornisa; tejado dos aguas 72 % (hastial con óculo) o plano con peto y terraza; 1-2 chimeneas "tubo de escape" (l.709). Cotas: planta baja 3.8, plantas 3.0, porton 2.9 (escala coche).
- Materiales (l.87-112, `_materiales` l.170): `PALETA_FACHADA` = ocre, salmón, amarillo, crema, rosa (5 tonos); teja, persiana verde, piedra, forja, vidrio, madera, carpintería, terraza, toldos. Todos Principled de color plano reutilizados por nombre `MAT_CASAS_*`. **La malla no tiene UVs**: `_MB` (l.204-302) solo acumula `verts/faces/fmats` y `to_object` (l.291) hace `from_pydata` sin `uv_layers`.

---

## 6. Lo que el resto del pipeline espera de una casa ("sin romper los inspectores")

| Quién | Qué mira | Dónde |
|---|---|---|
| `asentar_objetos.py` | `EDIFICIO_PREF` incluye `CASAS_` (l.184): **no se mueven**; huella = vértices con z local < 0.6 sin `CASAS_zocalo` (l.2016-2043); por 4 esquinas: enterrada si terreno > base+1.2, flotante si terreno < base-0.6 sin zócalo (con zócalo: bajo su fondo-0.3). `OBST_RAICES` (l.176): árboles con tronco dentro se apartan. Losas de apoyo `SOPORTE_PREF` (l.132) y `LOSA_PLAN` (l.1230): `CALLE_plaza*`, `CALLE_plazoleta`, `CAMINO_calle/enlace/travesia/rampa/escalera`. `garantia_losas_terreno` rebaja el terreno bajo `CALLE_plaza*/plazoleta`. | |
| `revisar_urbanismo.py` | `CASA_PREF = ('CASAS_','PENON_casa','PUEBLO_')` (l.65): fachada fiable = +Y local (l.298-302), rectángulo de la huella (l.180-221). Fallos: `casa_casa` (SAT > 0.3 m, l.574-583), `casa_calle`/`casa_camino` (cinta del kit entra > 0.1 m, l.584-597), `casa_pista` (< 3 m; aviso < 6), `casa_pitlane`, `casa_muro` (`MURO_PREF` l.75: `CAMINO_muro`, `MUROC_`, … a < 1 m delante de la fachada, aviso < 3), `muro_atraviesa_casa`, `arbol_casa`, `prop_casa` (props `CALLE_`, `COCHE_`, `CARRERA_*` con SAT > 0.3, l.660-668), `prop_calle` (prop que entra > 0.3 m en una cinta), `camino_sin_destino` (extremo a > 6 m de todo, l.685-708), `losa_tambor/volada/hierba`, `plaza_muro`, y los de `asentar.json` (l.712-782). | |
| `04_export/exportar_ac.py` | `CASAS_zocalo` → `1WALL_` (l.159-161); por cada `CASAS_casa` una caja de colisión `1WALL_casas_colision` desde `bound_box` (x ± 0.6 m, y desde `min+0.6` hasta -0.45; exige fachada en y=0: `max(ys) ≤ 2`, `min(ys) ≤ -3`, l.222-231). El resto de la casa es DECO. | |
| `04_export/kn5_writer_opt.py` | DECO se fusiona por material (`categoria` l.606; `acumular_fusion`), trozos ≤ 65000 vértices (l.65). Material = `diffuse_color` + `txDiffuse` de la primera imagen de color del árbol (`analizar_material` l.212-258), shader fijo `ksPerPixel` (l.324). UV: `uv_layers[0]` si existe (l.367-374); si no, las genera en coordenadas locales FLAT/BOX según el `Mapping` del material (`loops_grupo` l.388-408). | |
| `aplicar_texturas.py` | `MAT_CASAS_*` (salvo vidrio/persiana/luz) → `estuco_d.png` multiply BOX 1/4 m (l.57, 68, 98-99); `*teja*` → teja; `*piedra*` → piedra. | |
| `mejorar_materiales.py` | `MAT_CASAS_` (l.24): multiply sutil + bump de hiladas (teja) o despiece (piedra). | |

Fallos actuales del pueblo en `renders/qa/urbanismo_informe.json` (13:00, 23 en total): `casa_muro` CASAS_casa.066 ↔ CAMINO_muro.132 a 0.2 m (-337, 563) y el mismo muro cruza `CALLE_plaza_ayto` (`plaza_muro`): el plan tiene 0 `solar_elemento`, así que ese muro no es del plan; por posición (final de `pueblo_subida_mar`, s ≈ 1080-1120, lado +1) es con toda probabilidad el muro de sillares de la calle del ayuntamiento del integrador (v3 N1 s 1120: `_camino(h_min_relleno)`), que no conoce los solares. `casa_flotante` .066 (0.8 m) y .146 (1.0 m): el plan admite 0.5 m flotante por bilineal y la escena mide sobre la malla con diagonal fija (discrepancia conocida N2/C-14, "con la malla caen 22 casas"); `losa_hierba` CALLE_plaza (-510,487) 0.05 y CALLE_plaza_ayto 0.27 (frenada por el pasillo de la pista).

---

## 7. Lo que dicen las capturas y su causa en el código

| Captura | Defecto (director) | Causa en el código |
|---|---|---|
| 05, 06, 39, 40, 50 | terrazas no llanas, muros como aletas con velo blanquecino | Rejilla de terreno de 4 m: la transición de 2.5-3 m del perfil (`perfil_terrazas` l.652) se difumina ±2 m (`urbanismo.py` l.21-23); `construir_muros` solo pone muro si el escalón real ≥ 0.8 m, pero `muro3d` (l.171-191) construye un muro de **altura constante** (mediana) con canto 0.35 bajo cada punto: donde el terreno es rampa suave, el muro sale de la hierba por arriba y queda tapado por abajo. El velo = atributo 'roca'/hierba estirada del TERRENO en la rampa. N2/F-06 "no arreglado" (RONDA15 l.436: hace falta la escarpa/coronación en `urbanismo_escena`). |
| 39, 40, 50 | terrazas 1-2 casi vacías, plaza sin casas, rampa a terraza vacía | §3.4: zona excluida + `GAP_RAMPA_ALTO` + calles peatonales + `lejos_calle` + terreno no llano en s 920-1000. La plaza (`construir_plaza`, 24 m) se pone antes que los solares y consume el único hueco llano. |
| 40 | casa rosa con la puerta en la coronación del muro | casa de la terraza k+1 cuya fachada queda sobre el muro de k (patio 18-21 + muro en 21: la fachada de k+1 está a 7 m del muro, pero el muro tiene 6 m de alto y la cámara mira de abajo). No es un fallo de QA; es la lectura visual de un muro de 6 m sin escalonado. |
| 10 | prado vacío con palmera suelta | `casino_mar` 553 rechazos por terreno (banda no llana en s 3320-3440). |
| 06, 50 (lado izquierdo ok) | casas correctas, pero separadas, césped entre ellas y delante | `t += a + U(1.0,1.6)`, buffer 1.02 (l.1987-1988); franja acera-fachada de 1 m sin pavimentar; `laterales` por defecto (True, True): zócalo y pilastras en los cuatro lados. |

---

## 8. Qué haría falta para el plan del usuario

Objetivo (PLAN_USUARIO §5): densificar (fachadas pegadas sin césped, alturas/anchos variados, campanarios/cúpulas, soportales con tiendas y toldos, escaleras y muros de contención que trepen la ladera) y atlas de fachadas con variación (colores Riviera, contraventanas, balcones, macetas, ropa tendida) + suelo urbano (adoquín, alcantarillas, bolardos, farolas). Todo debe verse en AC "a pelo" (sin CSP) y pasar los inspectores con 0 fallos.

### 8.1 Densificar: manzanas de fachadas pegadas (plan + escena + kit)

**Cambios en `urbanismo.py`**
1. `construir_solares` (l.1875-1998): recorrer por **manzanas** de 3-7 casas: dentro de la manzana `t += a` (separación 0) y `bufs.append(poly)` sin el buffer 1.02; entre manzanas un hueco de 1.5-2.5 m (carruggio/escalera) o 0 si la fila es continua. Anchos más estrechos y variados: `anchos = [4.5, 5, 5.5, 6, 6.5, 7, 8, 9]` (ligures), `plantas` por regla "no dos vecinas iguales" en lugar del sorteo independiente. Exportar por solar `medianera_izq/der` (bool) además de `sep_x_neg/pos` (ya existen, l.2001-2022; convención local +X = `(fy,-fx)`), y `manzana` (id) para que la escena y la QA sepan que el contacto es intencionado.
2. Fachada en curva: dos rectángulos tangentes a una línea curva se cruzan por detrás (cuña de ~0.3-0.6 m con R 60-100 m y fondo 9 m). Opción A: solares **trapezoidales** (poligono de 4 puntos con los lados radiales) y casas con `params['inglete']=(ang_izq, ang_der)` en el kit (`_Pared` l.305 admite un origen y una normal por pared: basta girar las paredes laterales). Opción B: aceptar el solape trasero ≤ 0.6 m con medianeras ciegas (no se ve) y relajar la QA solo entre miembros de la misma manzana.
3. `verificar()` l.2529-2531 (`solar_solar`: buffer 0.98) → "intersección de interiores > 0.05 m² salvo misma manzana"; `verificar_v1` `calle_solar` (l.2506-2509) se mantiene; `huecos` (l.2401-2409) pasa a medir huecos entre manzanas.
4. Césped delante: nuevo elemento del plan `aceras` (polígono por manzana entre el borde de la calle `u_calle+2.25` y la línea de fachada, z = calle + 0.15) y `patios` (polígono trasero fachada+fondo → `u_hi_casa`, z = suelo, con `muro_patio` de 1.2 m en el fondo). Son losas: `urbanismo_escena.poligono(...)` (l.321-339) ya sabe hacerlas con canto hasta el terreno.
5. Más suelo: en los sectores que suben `FONDO_MAX_SUBE` 9 (l.204) limita por la rampa del muro de T1; con cell 4 no se puede subir sin que la trasera se entierre; mantener 9 y ganar densidad por el ancho, no por el fondo.
6. Huecos por rampas: `GAP_RAMPA_ALTO` 4.0 + `MARGEN_S_RAMPA` 4.5 dejan ~50 m de patio por rampa; alternativa que no rompe D7: permitir casas de **espaldas** a la rampa (fachada a la calle, medianera ciega al muro de la rampa) cuando `plan['alto']` queda detrás de la casa y no delante; exige que el muro de la rampa cuente como medianera (no como `casa_muro`: ese control solo mira delante de la fachada, l.611-628, así que no dispara).

**Cambios en `urbanismo_escena.py`**
7. `casa_var` (l.407-413): clave `(plantas, ancho, fondo, seed%3, laterales)` y `hk.build_casa(..., laterales=(not medianera_izq, not medianera_der))`. Ojo: dos medianeras ciegas coplanares (casas de la misma altura) hacen z-fighting; retranquear 1-2 cm la de la casa más baja (el kit ya evita cornisa y alero sobre el vecino, l.894-902).
8. Instanciar `aceras`/`patios` con `poligono('CALLE_acera', …)` y `poligono('CALLE_patio', …)`. Para no romper nada: registrar los prefijos nuevos en `asentar_objetos.SOPORTE_PREF`/`LOSA_PLAN` (l.132, 1230) y en `revisar_urbanismo.LOSA_PREF_QA`/`PROP_NO` (l.83, 120), o reutilizar `CALLE_plazoleta` (ya apoyo, ya losa maciza, ya excluido de props).
9. Farolas y bolardos en las calles del plan: tras cada `camino3d` de tipo adoquín, farola cada ~18 m alternando lado en la acera (u = ancho/2 + 0.4) con `calle_kit.build_farola` y bolardos en bocas de carruggi/plazoletas (pieza nueva). Son `CALLE_*` → `prop_calle` solo salta si entran > 0.3 m en la calzada nominal (`SEGS h = ancho/2`), y `exportar_ac` ya los hace `1WALL_` (l.159).

**Cambios en `casas_kit_v2.py`**
10. `laterales` ya existe (nada que hacer para la medianera). `soportal`: nuevo `params['soportal']` que retranquea la planta baja 2.5 m (`pa_f` baja a d = -2.5 para z < 3.8), pone pilares/arcos en la línea y=0 cada columna y techo; escaparates y toldos dentro. Coste ~80-120 tris por arco; cabe en el presupuesto porque una medianera ciega ahorra 400-800 tris. `huella_local` (z < 0.6) seguirá viendo los pilares en y=0 → fachada y colisión siguen en la línea (la caja de colisión de `exportar_ac` llega a y = -0.45: el coche no entra en el soportal, correcto).
11. Variedad vertical: `plantas` 2-7 (hoy 3-6), `tejado` plano con pérgola/terraza en el 40 % de los sectores de mar, torreón de esquina (+1 planta en la casa de cabecera de manzana). Campanarios/cúpulas: `edificios_civicos_v2.build_campanile` existe (uno en s 1130); añadir `build_iglesia` (cúpula + campanile) como pieza cívica y reservarle un solar de 2 anchos en `construir_plaza` (l.1832-1871: hoy 1 plaza por sector ≥ 240 m; permitir una por terraza y que la plaza lleve edificio cívico en el fondo en vez de solo la fuente).

**Escaleras y muros que trepan la ladera**
12. Ya existen (escaleras, rampas, carruggi peatonales, muros de contención). Lo que falta es verlo bien: (a) `muro3d` → altura por vértice (`muro_variable` l.193-213 ya lo hace liso; `muro_rampa_sillares` l.215-281 ya lo hace con sillares en piezas de 4 m): usar esta última para los muros del plan, con coronación = `z_top` del JSON; (b) **escarpa del terreno**: nodos del TERRENO a < 2.5 m del muro: lado alto a z_top-0.1, lado bajo a z_base+0.1 (pasada tipo `garantia_losas_terreno` en `asentar_objetos` o en `integrar` tras construir los muros; respeta `_proteger_pista`). Esto es lo que RONDA15 apunta como N2/F-06 pendiente. (c) Más escaleras: `travesia_cada_m` 150 → 75 y una escalera corta entre calle k y k+1 en el hueco entre manzanas aunque haya rampa (elemento `escalera_corta`, 1.6 m, sin pasarela: solo si el patio es llano por la banda medida). (d) Muros de patio y de parcela (1.0-1.5 m, piedra seca) sobre la línea `u_hi_casa`: visualmente "muros que trepan".

### 8.2 Atlas de fachadas con variación

13. **UVs en el kit**: `_MB.cara/box/pbox` (l.223-272) deben guardar un (u,v) por vértice (pared: u = a/escala, v = z/escala; tejado: por faldón) y `to_object` (l.291-302) crear `mesh.uv_layers.new()` y escribirlas. `kn5_writer_opt` ya lee `uv_layers[0]` (l.367-374), así que el exportador no cambia.
14. **Material de atlas**: `MAT_CASAS_atlas_<tono>` con Image Texture del atlas en Base Color (sin Mapping/Object). Hay que excluirlo de `aplicar_texturas.familia_de` (l.98-99: hoy cualquier `MAT_CASAS_` sin vidrio/persiana recibe `estuco_d` por BOX, que pisaría el atlas) y de `mejorar_materiales.PREFIJOS` (l.24) o aceptar su multiply sutil. `analizar_material` (kn5) coge "la primera imagen de color enlazada": con un solo Image Texture va bien.
15. **Contenido del atlas** (2048² o 4096², CC0 recoloreado a la paleta): 8-10 tonos de estuco Riviera (ocre, siena, rosa antico, giallo Portofino, salvia, azul polvo, rojo pompeyano, crema) con manchas de humedad y desconchones en la base; zócalo de piedra; cornisa; teja; contraventanas verde/azul/marrón abiertas y cerradas; persiana enrollable; balcón de forja (alpha); macetas con geranios (alpha); ropa tendida (alpha, 3-4 variantes); alcantarilla/rejilla; cartel de tienda. Candidatas CC0 a listar (no descargar): Poly Haven `plastered_wall`, `painted_plaster_wall`, `rough_plaster`, `roof_tiles`; ambientCG `PaintedPlaster017`, `Plaster001`, `RoofingTiles012`, `Fabric0xx`. Tamaños típicos 2K: 10-25 MB por set.
16. **Decals con alpha** (ropa tendida entre balcones, macetas en alféizares, carteles, manchas): `kn5_writer_opt` escribe shader fijo `ksPerPixel` (l.324) sin alpha test → hace falta `ksPerPixelAT` + `alphaTested=1` para materiales con alpha (cambio en el writer, equipo 04_export: **después del cierre de v1.1**). Hasta entonces, macetas y ropa como geometría low-poly (esferas/quads opacos, ~40-120 tris).
17. **Ropa tendida**: pieza nueva `calle_kit.build_tendedero(luz, seed)` copiando `build_guirnalda` (l.295, catenaria entre dos puntos) con prendas; colgada entre balcones de casas enfrentadas en carruggi peatonales (urbanismo exporta pares de solares enfrentados a < 6 m) o entre dos ventanas de la misma fachada (dentro del kit, sin objeto nuevo). Como objeto `CALLE_` cuenta como prop: `prop_casa` (SAT > 0.3) dispararía si cruza una casa → nombrarlo con prefijo no listado en `PROP_PREF` (p. ej. `DECO_tendedero`) o construirlo dentro de la malla de la casa.
18. **Macetas en alféizares y balcones**: dentro de la malla de la casa (param `macetas=0.3`), no como `CALLE_maceta` (prop que solaparía con la casa).
19. **Contraventanas/balcones variados**: ya son procedurales; añadir colores de persiana (verde, azul, marrón, gris) por casa y persianas a medio cerrar (una lama más) cuesta 0 tris extra; el atlas aporta el acabado (vetas, desconchones).

### 8.3 Suelo urbano

20. Adoquín: ya en calles de terraza y travesías (`caminos_kit` 'adoquin', Voronoi procedural). Para "tramos de adoquín" en la calle de servicio: partir la calle k=0 en tramos (`tipo='servicio_adoquin'` en el centro del sector, asfalto en los 30 m de cada boca para empalmar con la pista) — solo escena, el JSON añade un campo. La acera del adoquín (0.8 m, 0.15 alto) se queda; la franja acera-fachada va pavimentada (§8.1-4).
21. Alcantarillas: decal (atlas, alpha) o rejilla de 0.6×0.4 m de geometría (~30 tris) en el eje cada 25 m, dentro de la malla de la calle (no prop).
22. Bolardos: `calle_kit.build_bolardo` (cilindro 0.25×0.9, ~40 tris, hierro verde + anilla) en bocas de carruggi y bordes de plazoletas; `exportar_ac` l.159 → añadir `CALLE_bolardo` a `1WALL_` para que sean sólidos.
23. Farolas en el pueblo (§8.1-9); también postes de guirnalda entre fachadas enfrentadas (ya hay `build_guirnalda`).

### 8.4 Riesgos y dependencias

- **Presupuesto**: hoy ≤ 5000 tris × 193 casas ≈ ≤ 1 M tris (kn5 total 4.63 M). Medianeras ciegas ahorran; soportales, macetas y tendederos gastan. Mantener el `assert` del test del kit (≤ 5000) y medir el total en `kn5_check`.
- **QA 0 fallos es bloqueante** (`urbanismo.py:2841` aborta el pipeline): cualquier cambio en solares exige actualizar `verificar()`/`verificar_v1()` el mismo día. Ídem `revisar_urbanismo` (casa_casa tolera 0.3 m de solape: dos medianeras con zócalo 0.12 + pilastra 0.10 suman 0.24 → pasa, pero con `laterales=False` el solape es 0).
- **No cambiar claves existentes de `urbanismo.json`**: lo leen `construir_pista` (`_BOCAS`, acera alta) y `revisar_urbanismo` (`_polilineas` l.323-339 lee tolerante `pts`/`ancho`; una lista nueva de polígonos sin `pts` se ignora, bien). Solo añadir campos.
- **Convenciones intocables**: nombre `CASAS_casa`, fachada +Y en y=0 (exportar_ac l.226-227 descarta la casa si `max(ys) > 2` o `min(ys) > -3`), hijo `CASAS_zocalo`, huella por vértices z < 0.6, pivote en el centro de la fachada (`rot_z = atan2(fy,fx) - pi/2`).
- **Dependencia del bloque de relieve**: si cambia el terreno (erosión, macizo) cambian las bandas llanas medidas y el plan se regenera solo; el spec (21 m, 6 m, 0.5 m) debe seguir idéntico para `terreno_montana` y `urbanismo`. La escarpa de los muros (§8.1-12b) toca nodos del TERRENO: coordinar con quien haga `_roca_terreno`/máscara (bloque 2-3), porque el atributo 'roca' por vértice también se interpola ahí.
- **Dependencia del integrador**: la plaza del ayuntamiento y su calle (s 1120-1160, lado +1) están fuera del plan y hoy generan el `casa_muro`/`plaza_muro` de CASAS_casa.066. Solución limpia: exportar su huella al spec como `zonas_reservadas` (como `zonas_excluidas`) o incluir el ayuntamiento como `plaza` con edificio cívico del propio plan.
- **Dependencia de 04_export** (cerrado para v1.1): alpha test (`ksPerPixelAT`) y `CALLE_bolardo` → `1WALL_`. Hasta entonces todo lo nuevo debe ser opaco y, si es sólido, llamarse `CALLE_farola/maceta/poste_guirnalda` o `CASAS_zocalo`.
- **CSP no garantizado**: nada de lo anterior lo necesita (texturas difusas + geometría). Las luces de las farolas (globo emisivo del kit) no se ven en AC a pelo salvo como color.
- **Capturas antes/después**: cámaras del método del usuario (piloto s800 = captura 50, aérea 39, 05, 06, 40, 10). `renderizar_capturas.py` ya tiene esas tomas; no hace falta cámara nueva.

### 8.5 Orden sugerido (cada bloque con capturas antes/después)

1. Muros con altura por vértice + escarpa del terreno (quita las "aletas": 05/06/39/40/50). Solo escena + asentar.
2. Manzanas pegadas con medianeras, aceras y patios pavimentados, anchos/alturas variados (plan + escena + QA). Es el cambio de mayor impacto desde el coche.
3. Farolas, bolardos, guirnaldas y tramos de adoquín en las calles del plan (escena + calle_kit).
4. UVs + atlas de estuco/teja/piedra en el kit de casas (kit + aplicar_texturas), colores Riviera.
5. Soportales con tiendas, iglesia con cúpula, torreones (kit + plaza del plan).
6. Decals alpha (ropa, macetas, alcantarillas) cuando 04_export admita alpha test; mientras, geometría opaca.
