# PARCHES F1 — propietario `materiales` (bloque 3 puntos 1, 2, 3, 7 + bloque 2.1 + 7.1 horizonte)

Fecha: 04/10/2026, tarde. Lo que hay que tocar en ficheros AJENOS para que lo mío quede enganchado. Cada parche
lleva fichero, función, bloque exacto y cómo probarlo. Lo que ya está hecho por otro propietario se dice y no se repite.

## 0. Estado: qué consumidores de la paleta YA están hechos y cuáles no

| Consumidor (plan 3.1 / entender_materiales §3.a) | Fichero | Estado |
|---|---|---|
| tiles PIL con tinte de paleta + tiles nuevos | `texturas/generar_texturas.py` | HECHO (mío) |
| CC0 recoloreado, misma API | `texturas/recolorear_cc0.py` (nuevo), `texturas/CREDITS.txt`, `texturas/medias.json` | HECHO (mío) |
| familias seca/matorral/cesped/caliza, hierba BOX, manchas ±10 %, MAT_terreno_matorral | `aplicar_texturas.py` | HECHO (mío) |
| caliza compartida `NG_caliza_estratos` | `assets/materiales_roca.py` (nuevo) + `test_materiales_roca.py` + previews | HECHO (mío) |
| fachadas 8 tonos Riviera + teja terracota | `assets/casas_kit_v2.py` (`PALETA_FACHADA`, `COL_TEJA`) | HECHO (mío) |
| roca del lazo / peñón: misma caliza + grupo | `assets/roca_lazo.py` `_PALETA`/`_mat`, `assets/roca_casino.py` `_PALETA`/`_mat` | HECHO (mío) |
| McLaren: caliza de paleta + grupo, hueso 0.58 | `assets/montana_coche_v2.py` `_mat_piedra`/`_mats_roca` | HECHO (mío) |
| copas oliva/salvia | `assets/vegetacion_kit_v2.py` `_PALETA` | HECHO (mío) |
| bisel barato + horizonte() | `mejorar_materiales.py` | HECHO (mío); el pipeline ya lo llama (`pipeline_escena.sh` l.69) |
| rampa/roca/diffuse del terreno, tierra, arcén, acera, bordillo, muro | `construir_pista.py` | **YA HECHO por el propietario `mascara`** (l.27 `import paleta`, l.102, 478, 584, 1202-1203, 1564, 1681, 1920): comprobado a las 16:35, nada que parchear |
| enganche de la caliza en `_roca_terreno` | `construir_pista._enganche_materiales_roca` l.268-296 | **YA HECHO por `mascara`** con la API de §1 (comprobada: coincide) |
| `MAT_MCOCHE_cristal_pulido` rugosidad, `_TONO_GRIETA`/`_TONO_MONTE`, `_mat_hierba` | `assets/montana_mclaren.py` (propietario Rocas, F2) | **PARCHE §2** |
| `color_ac._REGLAS` (matorral/seca/cesped/caliza) y re-medir | `04_export/color_ac.py` [W] | `PETICIONES_04_EXPORT.md` P11 |

## 1. API de `assets/materiales_roca.py` (para `mascara` en `construir_pista._roca_terreno` y para `Rocas`)

```python
import materiales_roca                       # sys.path: 03_blender/assets (o importlib desde la ruta)
ng = materiales_roca.ng_caliza_estratos()    # bpy.types.ShaderNodeTree 'NG_caliza_estratos' (una vez por .blend)
# entradas: tono_base (Color), tono_junta (Color), periodo_m (3.0), bump (0.45), mojado (1.0), fase (0.0),
#           contraste_bancos (0.12), grano (1.0), manchas (1.0);  salidas: 'Color', 'Normal', 'AO'
# TODO en coordenadas de MUNDO (Geometry.Position): TUNEL_acantilado / PENON_* empalman con el terreno.
grp, color_out, normal_out, ao_out = materiales_roca.crear_nodos(
    nt, loc=(-900, -1500), tono_base=paleta.rgb('caliza_ocre'), tono_junta=paleta.rgb('caliza_sombra'),
    periodo_m=3.0, bump=0.45, mojado=1.0, fase=0.0, contraste_bancos=0.12, nombre_nodo='ROCA_grupo_caliza')
# crear_nodos NO enlaza nada ni toca 'Math.002'/'ROCA_mascara' ni el Principled: el llamador enlaza color_out
# a su rama de roca (mixr.inputs[7] / ROCA_color_grupo) y normal_out al Normal del BSDF de roca.
materiales_roca.aplicar_a(material, tono_base=None, tono_junta=None, imagen='caliza_d.png', tile_m=6.0, factor=0.5, **kw)
# para materiales de KIT (Principled plano o con rampa): Base Color <- grupo.Color x caliza_d.png con la cadena
# del writer (TEX_coord/TEX_mapping/TEX_imagen BOX/TEX_ganancia/TEX_multiplicar), Normal <- grupo.Normal,
# diffuse_color = media lineal (materiales_roca.media_lineal), custom props ac_* por defecto, marcadores
# 'CALIZA_ESTRATOS' + 'TEXTURIZADO' (aplicar_texturas no lo vuelve a texturizar). Idempotente.
materiales_roca.tiene_caliza(material) -> bool
```
Comprobado en `construir_pista._enganche_materiales_roca` (l.268-296): usa `crear_nodos(nt, loc, nombre_nodo=...)[0]`
y `grp.outputs['Color'/'Normal']`: coincide con esta API. `test_materiales_roca.py` comprueba que un nodo `Math.002`
etiquetado `ROCA_mascara` queda intacto.

## 2. PARCHE `assets/montana_mclaren.py` (propietario Rocas; bloque 2.1 / 3.1) — 3 bloques

**2.a** `_mats_mc()` (l.263): cristal pulido con rugosidad 0.5 (hoy 0.26 = brillo de plástico, entender_rocas §8.4):
```python
    cristal = _mat("MAT_MCOCHE_cristal_pulido", (0.050, 0.062, 0.080), 0.50, 0.60)
```
**2.b** tonos de grieta y monte desde la paleta (l.232-237; hoy literales copiados de la roca del terreno v1). Añadir
tras los imports (junto a `_V2 = ...`), con el mismo patrón que `montana_coche_v2.py` l.88-92:
```python
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import paleta as _paleta  # noqa: E402
```
y sustituir
```python
_TONO_GRIETA = ((0.522, 0.426, 0.287), (0.644, 0.566, 0.426))   # caliza -13 % (v3, B13; v1: -30 %)
_TONO_MONTE = ((0.34, 0.28, 0.19), (0.46, 0.385, 0.27))
```
por
```python
# fase visual F1: caliza_ocre -13 % para la grieta; el monte = caliza gris calida (la misma que mixr.inputs[7] del terreno)
_TONO_GRIETA = (_paleta.variante('caliza_ocre', 0.87), _paleta.variante('caliza_ocre', 0.98))
_TONO_MONTE = (_paleta.rgb('caliza_gris_calido'), _paleta.variante('caliza_gris_calido', 1.15))
```
(`_mat_piedra` de `montana_coche_v2` ya enchufa el grupo de caliza: `_retintar()` sigue funcionando: solo toca
`diffuse_color`, Base Color sin enlazar y rampas VALTORGB, que con el grupo ya no existen.)
**2.c** `_mat_hierba()` (l.229): el verde césped del test pasa a hierba seca:
```python
    return _V2._mat_piedra("MAT_MCOCHE_hierba", _paleta.rgb('hierba_seca'), _paleta.variante('hierba_seca', 1.12),
                           0.97, 0.035, 0.15, caliza=False)
```
Prueba: `bash 03_blender/_rev/blender_cola.sh --python 03_blender/assets/test_montana_mclaren.py` -> TEST_OK, y en
`previews/` la carrocería sale caliza_ocre con juntas (no crema) y los bujes/aros no deslumbran.

## 3. Propietario `horizonte` (bloque 7.1): cómo usar `mejorar_materiales.horizonte()`

Contrato `mezcla(rgb_lineal, dist_m) -> rgb_lineal` de `PARCHES_F1_horizonte.md` (l.48, `mezcla = getattr(_mm, 'horizonte')`):
**cumplido**. `mejorar_materiales.horizonte(rgb, dist_m)` con un RGB y un número actúa como función pura
(= `mezcla_horizonte(rgb, dist_m, color_cielo=None)`): color de paleta mezclado con el horizonte del world `CIELO`
(`color_cielo_world()`: primer elemento de su ColorRamp = (0.70, 0.84, 0.98)) al 35 % a 2400 m .. 55 % a 4500 m
(`factor_horizonte`). Probado (`_rev/_tmp_materiales/check_horizonte.py`): `horizonte((0.2, 0.3, 0.15), 4500) = (0.475,
0.597, 0.607)`. El pase de escena lee `mat['horiz_base_rgb']` y `mat['horiz_dist_m']` si el kit los anotó (si no,
guarda `horiz_color_base` y usa la distancia media de los objetos) y es idempotente: relanzarlo tras cambiar el cielo
recalcula todos los `MAT_HORIZ_*` desde el color base.

No hay nada que parchear: `mejorar_blend()` ya llama a `bisel_barato()` y a `horizonte()` en cada regeneración.
Solo hace falta que las mallas del anillo se llamen `HORIZ_*` (prefijo `HORIZ_PREFIJO`) y lleven materiales
`MAT_HORIZ_*` (Principled de color plano; `diffuse_color` = el color base): `horizonte()` guarda el color original
en `mat['horiz_color_base']` y pone `diffuse_color`/Base Color = base·(1-f) + cielo·f con f = 0.35 a 2400 m del
centro del circuito (bbox del TERRENO) y 0.55 a 4500 m (lineal, recortado). Cielo por defecto (0.70, 0.84, 0.98) =
el horizonte del gradiente de `construir_pista` l.1585-1606. Relanzar `mejorar_materiales.py` recalcula desde el
original (idempotente). Un material compartido por dos lomas a distinta distancia usa la media de sus distancias:
si se quiere f distinto, materiales distintos (`MAT_HORIZ_fila1_*`, `MAT_HORIZ_fila2_*`). Llamada directa:
`mejorar_materiales.horizonte(objs=None, color_cielo=(0.70, 0.84, 0.98), d_cerca=2400, d_lejos=4500, f_cerca=0.35, f_lejos=0.55)`.
`MAT_HORIZ_*` no entran en `PREFIJOS` (sin pátina) ni en `aplicar_texturas.familia_de` (sin tile): color plano.

## 4. Bisel barato: prefijos y exclusiones (para quien añada kits nuevos)

`mejorar_materiales.BISEL_PREFIJOS` = CASAS_, CAMINO_muro, MUROC, CARRERA_muro, ITAL_bancal/fuente/ermita/capitella/
pergola, CIVICO_, AYTO_, HOTEL_, CAMPANILE_, CASINO_, PIT_, PUERTO_, CARRERA_tribuna/boxes/portico, MIRADOR_parking/
pasarela, CALLE_plaza/plazoleta, ACERA_, BORDILLO_, EDIF, TUNEL_portal. `BISEL_NUNCA` = TERRENO, AGUA, PISTA, PIANOS,
PIT_LANE/marcas/suelo, PUERTO_dique_malla, VEG_/OLI_, PENON_/MCOCHE_/TUNEL_acantilado (traen sus normales), ARCEN,
LINEA, MARCA, LOEWS, AC_, 1WALL_/1ROAD_/1GRASS_/2GRASS_/1DIRT_/1KERB_, cierre. Mallas con `has_custom_normals` se
saltan. Marca por malla `mesh['bisel_auto_smooth']`. Medido sobre la copia de escena_rev (04/10): 642 mallas,
752 k aristas vivas a 35°. Un kit nuevo con prefijo propio (AFLOR_, ESCOLLERA_, VILLA_, COSTA_...) solo tiene que
pedir su alta en `BISEL_PREFIJOS` (o traer `shade_smooth` + `sharp_edge` él mismo).

## 5. Pipeline / texturas (integrador): orden y qué NO cambia

- Las texturas son ficheros estáticos de `03_blender/texturas/`: el pipeline no las regenera. Si alguien relanza
  `python texturas/generar_texturas.py` debe lanzar DESPUÉS `python texturas/recolorear_cc0.py` (el CC0 pisa con el
  mismo nombre; orden "PIL primero, CC0 después"). Ambos actualizan `texturas/medias.json`, que `aplicar_texturas`
  lee (ganancia 1/media); si falta, usa `FAMILIAS.ganancia` (valores medidos el 04/10 con el CC0 ya aplicado).
- `aplicar_texturas.py -- <blend> --rehacer [familias]` quita la pasada previa y vuelve a texturizar (para cambiar
  de tile sin regenerar la escena). Sin `--rehacer` sigue siendo idempotente (marcador TEXTURIZADO).
- Materiales nuevos de tiles que NO consume nadie todavía (listos para los bloques 5/6/7): `adoquin_d.png`,
  `piedra_seca_d.png`, `escollera_d.png`, `fondo_marino_d.png`, `pista_tierra_d.png`, `afloramiento_d.png`,
  `acantilado_d.png` (+ normales `_n.png` de las 4 capas del terreno: caliza, hierba_seca, tierra, matorral).
- Nombres de material de fachada: ahora `MAT_CASAS_fachada_<ocre_portofino|rosa_antico|amarillo_napoles|rojo_pompeya|
  blanco_roto|salmon|crema|amarillo>` (antes ocre/salmon/amarillo/crema/rosa). `_rev/color_ac/informe_vistas.py` l.19 y
  `simular_vistas.py` l.47 citan `MAT_CASAS_fachada_amarillo` (sigue existiendo). Las medidas de `color_ac_objetivos.json`
  de los nombres viejos caducan (R1 del plan: re-medir en F4).
- Presupuesto: los 10 materiales de roca (`MAT_PPUEBLO_roca*`, `MAT_MCOCHE_caliza*`, `MAT_VEG_roca`) pasan de PNG plano
  8x8 a tile tintado de 512 px: +10 texturas de ~0.3 MB (+3 MB) en el KN5; sin cambio de tris ni de mallas.

## 6. Checklist para el integrador tras la regeneración

1. `aplicar_texturas` log: `MAT_terreno` NO debe aparecer en "tocados" si `construir_pista` ya le puso el marcador
   (mascara por texel); sí deben aparecer `MAT_PPUEBLO_roca*` -> caliza SOLO si los kits no las enchufaron (si
   los kits ya llevan el grupo salen como "saltados").
2. `mejorar_materiales` log: `BISEL BARATO: N mallas ...` y `HORIZONTE: n materiales` (0 hasta que exista HORIZ_).
3. Capturas A/B set `paleta` + BASE en modo normal y AC: `pct_cesped` en piloto (objetivo < 8 %), 0 RGB fuera de
   paleta en terreno/roca/teja/vegetación (grep de literales en los kits: solo quedan en materiales secundarios:
   troncos, flores, hierro, barcas).

---

# RONDA 2 (04/10 noche) — arreglos de `director_f1_r1.md` que tocan a `materiales` (problemas 7 y 8, y la parte "materiales" del 4)

## 7. Qué he cambiado en MIS ficheros (resumen; detalle en los docstrings)

| Fichero | Cambio r2 |
|---|---|
| `assets/materiales_roca.py` | **v2 del grupo `NG_caliza_estratos`** (`CAL_VERSION = 2`): entradas nuevas `tono_pared` (Color, defecto `caliza_gris_calido`) y `pared` (0..1, defecto 1): TRES TONOS por orientación de la normal de mundo: repisas/mesetas (nz >= 0.90) = `tono_base` (caliza clara), laderas y paredes (nz <= 0.60, transición suave) = `tono_pared` (caliza media; nunca más clara que la base: mínimo por canal), juntas/mojado = `tono_junta` (roca oscura). `actualizar_grupo()`: un grupo v1 guardado en el .blend se reconstruye EN SITIO (misma interfaz + entradas nuevas; los enlaces de `MAT_terreno` y de los kits se conservan; los nodos de grupo existentes reciben el defecto de `tono_pared`). `media_lineal(..., tono_pared, frac_pared=0.5)` y `aplicar_a(..., tono_pared, pared, frac_pared)`: `diffuse_color` = media con la mitad de superficie en pared. `color_roca_terreno_ac(ao=None)` + `ao_media_terreno()` (P1). `roca_caras_mascara(ob, umbral=0.5, nz_extra=0.35, ruta_mask=None)` (P1 / problema 8). |
| `aplicar_texturas.py` | `actualizar_caliza()` al abrir el blend (llama a `materiales_roca.actualizar_grupo()`; guarda si lo rehízo aunque no haya nada que texturizar; log `caliza_vactualizada` / `caliza_val_dia`). Familias, idempotencia y `--rehacer` como en r1. |
| `mejorar_materiales.py` | `horizonte()` / `mezcla_horizonte()` v2: mezcla hacia la **bruma** (`bruma_horizonte` = cielo del world x `HORIZ_CIELO_ATENUACION` 0.42 x `HORIZ_TINTE` (1.00, 0.90, 1.06)), albedo acotado (`acotar_horizonte`: canal máximo `HORIZ_ALBEDO_MAX` 0.36 lineal, S sRGB >= `HORIZ_S_MIN` 0.15), log por material con hex/H/S/V y comprobación V <= 0.85 / S >= 0.15; constantes anulables desde `paleta.json['horizonte']` (claves `cielo_atenuacion`, `tinte`, `albedo_max`, `v_max`, `s_min`; sección opcional, no creada). El contrato puro `horizonte(rgb, dist_m)` sigue igual. |
| `assets/test_materiales_roca.py` | secciones 6-8 (v2, grupo versionado, media/pared, render de orientación `previews/materiales_roca_orientacion.png`, `roca_caras_mascara` sobre máscara sintética con y sin UV). TEST_OK 04/10 noche. |
| `_rev/_tmp_materiales/r2/` | `preparar_r2.py` (copia de la candidata con rutas absolutas + r2 aplicado + diagnóstico -> `preparar_r2.json`), `capturas_ac_p1.py` (simulación de P1 sobre `capturas_ab --modo-ac` sin tocar `color_ac`), renders `despues/`, `despues_ac/`, `despues_ac_p1/`, `rutas/` (candidata con SOLO rutas absolutas = referencia "antes de r2"), `antes_ac/` (= `despues_ac` del director), `AB_*`, `medidas_ac.json`, `medidas_r2.json`, `medidas_ac_p1.json`. |

## 8. Diagnóstico con cifras del problema 7 ("crema sobre crema" en 51, modo AC): qué es y qué no es de materiales

Medido sobre la candidata (`preparar_r2.json`, rayo desde la cámara congelada de 51 al píxel del director):

- `(1500,300)` y `(1200,400)` de 51 son caras del `TERRENO` con `MAT_terreno`, nz 0.54 / 0.60, atributo `roca` > 0.49 -> en `--modo-ac` pasan a `MAT_terreno_roca` por `color_ac.roca_caras` (también por el canal A). `(1300,550)` (la "hierba seca" #F4EDBC del director) es la berma llana (nz 0.95) y la máscara A también la marca como ROCA (A > 0.5): en modo Blender ya es caliza, no hierba (ver 9.3).
- En el render AC del director `sin_imagen_legible` = 16 (rutas relativas, problema 1 del director): `MAT_terreno` era color PLANO hierba_seca (0.55, 0.45, 0.20) y `MAT_terreno_roca` color PLANO `color_ac.ROCA_COLOR` = (0.34, 0.27, 0.18) = #9E8E76, un literal de `04_export` que no sale de `paleta.json`. Esa pared mira al sol (elevación 48°: recibe cos ~0.95 frente al 0.74 del llano) y por eso un albedo 0.34 sale #DDD2C0 (V 0.87) y el llano con albedo 0.55 sale #F4EDBC (V 0.96): la falta de contraste en el proxy la pone la geometría de la luz, no la paleta. Con el mismo sol, `caliza_gris_calido` (0.45, 0.38, 0.25) en esa pared daría V ~0.98 (peor) y `caliza_ocre` V 1.0.
- Lo que SÍ cambia r2, en Blender (y en el KN5 cuando `color_ac` se re-mida en F4, porque calibra contra el aspecto medido de esas caras): laderas y paredes de roca del terreno y de los kits pasan de `caliza_ocre` a `caliza_gris_calido` (tres tonos reales: claro en repisas, medio en ladera, oscuro en junta). En 51 modo Blender (`rutas/` -> `despues/`, mismas cámaras): pared derecha V media 0.953 -> 0.903 (p10 0.808 -> 0.737), loma izquierda 0.846 -> 0.826, berma 0.884 -> 0.882; `pared_lisa` 51 8.4 -> 7.5 %, 07 14.3 -> 13.5 %. Al sol directo la caliza media sigue recortándose a blanco (albedo 0.45 x luz ~2.1): límite de "paleta = albedo" bajo `Standard` + sol 4.6 (no-hacer 17), igual que en la carta de color.
- Lo que NO puede cambiar r2: el color del proxy `--modo-ac` para `MAT_terreno_roca` (`ROCA_COLOR`, literal de `color_ac`) ni el tile que usa (hereda `hierba_seca_d` de la copia de `MAT_terreno`): es P1 ([W]). Por eso `despues_ac/` repite las cifras de terreno de `antes_ac/` (pared de 51 V 0.862 -> 0.861) salvo lo que arregla la ruta absoluta (tiles legibles: 51 riqueza 0.50 -> 1.94, `pared_lisa` 92.9 -> 28.3 %; 07 81.5 -> 32.6 %; 49 59.9 -> 32.1 %): ese salto es del arreglo n.º 1 del director (propietario `mascara`), no mío; lo dejo escrito para que nadie lo cuente dos veces.
- `color_roca_terreno_ac()` = media de PARED de caliza x AO media del terreno (0.757, `renders/qa/terreno_mask_stats.json`) = (0.332, 0.281, 0.188) = #9C9078: el literal de hoy era, sin saberlo, exactamente esto. P1 debe usar la función (sigue a la paleta y a la máscara) y NO la media sin AO (#B1A489: en el proxy sube la pared de 51 de V 0.85 a 0.91, comprobado con `P1_ROCA_COLOR=paleta|literal`).

## 9. Parches / avisos a otros propietarios (ronda 2)

### 9.1 Integrador: `_rev/capturas_ab.py` `aplicar_modo_ac()` (SOLO junto con P1 en el writer; si no, el proxy deja de ser fiel)

Tras `import color_ac` (l.238) y antes de `roca = color_ac.separar_roca_terreno()`:

```python
        # P1 (PETICIONES_04_EXPORT.md): caras de roca por el canal A de la mascara y ROCA_COLOR de paleta x AO media
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(AQUI), 'assets'))
            import materiales_roca
            color_ac.roca_caras = lambda ob: materiales_roca.roca_caras_mascara(ob)
            color_ac.ROCA_COLOR = tuple(materiales_roca.color_roca_terreno_ac())
        except Exception as e:  # noqa
            log('modo AC: materiales_roca no disponible (%s): roca por nz < 0.5' % e)
```

y, después de `roca = color_ac.separar_roca_terreno()`, el tile de caliza para la copia (lo que P1 pide como `txDiffuse`):

```python
        m_r = bpy.data.materials.get(color_ac.ROCA_MAT)
        if m_r is not None and m_r.node_tree:
            tex = next((n for n in m_r.node_tree.nodes if n.bl_idname == 'ShaderNodeTexImage' and n.image
                        and n.image.colorspace_settings.name != 'Non-Color' and n.outputs['Color'].is_linked), None)
            ruta = os.path.join(os.path.dirname(AQUI), 'texturas', 'caliza_d.png')
            if tex is not None and os.path.exists(ruta):
                tex.image = bpy.data.images.load(ruta, check_existing=True)
                tex.image.colorspace_settings.name = 'sRGB'
                mp = m_r.node_tree.nodes.get('TEX_mapping')
                if mp is not None:
                    mp.inputs['Scale'].default_value = (1.0 / 3.0,) * 3
```

Prueba: `bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/_tmp_materiales/r2/capturas_ac_p1.py -- <args de capturas_ab> --modo-ac` hace exactamente esto sin editar nada (parchea `color_ac` en memoria). Medido (candidata + rutas absolutas, cámaras congeladas, `medidas_ac_p1.json`): `pared_lisa` 07 32.6 -> 16.8 %, 13 55.0 -> 25.2 %, 21 36.3 -> 21.5 %, 49 32.1 -> 27.1 %, 51 28.3 -> 22.2 %; en 07/21 los parches de roca siguen el borde de ruido de la máscara (`AB_ac_07_tierra_subida_p1.png`) en vez de polígonos aislados de 4 m; recuento sobre la candidata: nz < 0.5 = 52 532 caras, máscara A > 0.5 = 53 963, intersección 47 989 (solo nz 4 543, solo máscara 5 974).

### 9.2 Propietario `mascara`: `construir_pista._enganche_materiales_roca` (nada que cambiar; dos avisos)

- `crear_nodos(nt, loc, nombre_nodo='ROCA_grupo_caliza')` sigue valiendo: con el grupo v2 la rama de roca del terreno sale con `tono_pared = caliza_gris_calido` y `pared = 1` (defectos). Para otra pared: `crear_nodos(..., tono_pared=..., pared=...)`. En una escena ya construida `aplicar_texturas` actualiza el grupo solo (no hace falta regenerar para verlo).
- `relative_remap=False` (arreglo n.º 1): comprobado sobre la copia que con rutas absolutas los 7 datablocks (`hierba_seca_d`, `matorral_d`, `tierra_d`, `caliza_d`, `cesped_d`, `terreno_base`, `terreno_mask_nc`) cargan (1024/2048 px) y `--modo-ac` pasa de `sin_imagen_legible` 16 a 0. OJO: `ntpath.basename('//texturas/x.png')` devuelve `''` (lo trata como ruta UNC); quitar el `//` antes (`fp[2:]`).

### 9.3 Propietarios `mascara` / `terreno`: hallazgos sobre la candidata en modo Blender (no son de materiales; con evidencia)

1. **Rejilla de triángulos de 4 m visible en el TERRENO** en 07/21/51 modo Blender (`_rev/_tmp_materiales/r2/crop_07_rutas.png`): está IGUAL en la copia con solo rutas absolutas (`rutas/`), el TERRENO es 100 % `shade_smooth`, sin `sharp_edge`, sin normales personalizadas ni modificadores (`preparar_r2.json['terreno_sombreado']`), y NO aparece en `--modo-ac` (sin sombra del suelo): es la sombra propia del terreno (terminador de sombra de EEVEE sobre triángulos de 4 m con el relieve nuevo y el sol a 48°), no un tile ni la caliza. Lo arregla quien lleva la luz/`construir_pista` (bias/ángulo del SOL o subdividir la banda junto a la pista); los tiles están limpios (borde/interior: hierba_seca 0.99, matorral 0.95, tierra 0.97, caliza 1.03, base 1.04).
2. **La berma junto a la pista en 51 (cara nz 0.95 a 21 m de la cámara) tiene canal A > 0.5**: se pinta caliza en vez de hierba seca al pie del desmonte (regla "pie 6-10 m" / ruido de borde). Es lo que impide leer "roca arriba, tierra al pie, hierba en la berma".
3. En modo Blender el terreno de la candidata sale muy claro (51 pared V media 0.95, llano 0.88): `terreno_base.png` lleva `caliza_ocre` en el canal A y al sol se recorta; con r2 la ladera baja 0.05 de V. Más contraste al sol es decisión de paleta (un `caliza_media` más oscuro, o tratar los rgb de `paleta.json` como color APARENTE y dividir por ~1.8 el albedo de las familias al sol), no de materiales.

### 9.4 Propietario `horizonte`: nada que cambiar en el kit

`mejorar_materiales.horizonte()` recalcula desde `mat['horiz_color_base']` (idempotente: 2.ª pasada = mismos hex) y ahora acota el albedo: los 14 `MAT_HORIZ_*` quedan en V 0.57-0.63, S 0.15, H 229-236 (cumbres #8A8EA2, bosque ~#7B7E92). Renders AC con las cámaras congeladas (`antes_ac` = director -> `despues_ac`): píxeles #FFFFFF en la franja alta (y < 230) 21: 24 126 -> 7, 13: 615 -> 42, 57: 0 -> 0; 21 `(1150,100)` #FFFFFF -> #B6C3EB (V 0.92 < cielo 1.0), 57 `(1400,300)` #B2CBE1 -> #6E82A8 (V 0.66), 13 `(1000,110)` #8EAED4 -> #6177A4; en modo Blender 21: 21 784 -> 253 blancos. `montanas_fondo_v2.mezcla_cielo` (respaldo del kit cuando no se pasa `mezcla`) sigue mezclando con el cielo sin atenuar: solo afecta a sus previews de test, no al pipeline (el pase de escena lo pisa); si quiere que coincidan, `mezcla=mejorar_materiales.mezcla_horizonte`. Lo cosmético (picos de aguja) sigue siendo suyo.

### 9.5 `PETICIONES_04_EXPORT.md`: P1 ampliada (hecho en este turno, sub-viñeta "P1 (código listo, F1 materiales r2)")

`color_ac.separar_roca_terreno` -> `materiales_roca.roca_caras_mascara`, `ROCA_COLOR = materiales_roca.color_roca_terreno_ac()`, `MAT_terreno_roca` con `caliza_d.png` 3 m.

---

# RONDA 3 (04/10 noche, ~22:00-23:30) — arreglos de `director_f1_r2.md` problemas 3, 4, 5 y 6 (propietario `materiales`)

Todo medido sobre `_rev/_tmp_materiales/r3/escena_r3.blend` = COPIA de `_rev/escena_candidata.blend` (md5 39e8a969…, la que juzgó el
director) + `preparar_r3.py` (grupo v2 -> v3, `aplicar_texturas` v3, McLaren re-aplicado), renderizada con las cámaras congeladas
`renders/ab/_base_antes/camaras.json` (`--solo 49_,51_,36_,13_,07_`). "Antes" = `renders/ab/f1_r2/despues*` del director (misma
candidata, sin r3). Pares: `_rev/_tmp_materiales/r3/AB_*.png` (normal), `AB_ac_*.png` (proxy AC oficial), `AB_ac_*_r3.png` (proxy AC
con los parches 10.1 + 10.2); medidas `medidas.json`, `medidas_ac.json`, `medidas_ac_r3.json`; diagnóstico de píxeles `diag_r3.json`.

## 10. Diagnóstico con cifras (qué era cada cosa) — `diag_r3.py` (rayo desde la cámara congelada + rayo de sombra hacia el sol)

| Problema del director | Qué es de verdad | Prueba |
|---|---|---|
| 5. "retícula de celdas de 10-15 m / red de pesca" en la caliza (36, 13, 07, 51 fondo) | DOS cosas. (a) En las ROCAS de kit (peñón, lazo, McLaren) y en la pared cercana del terreno: la **Distortion 5.0 del Wave** del grupo (= ruido a la escala del propio Wave, periodo 3 m × 3 ≈ 9.5 m): celdas de ~10 m. ARREGLADO en el grupo v3. (b) En las LOMAS LEJANAS del terreno (51 fondo a 220-400 m, 07, 36 bajo el peñón): una **celosía de 4 m = la rejilla de triángulos del TERRENO**; NO es del grupo: sigue igual con Wave sin distorsión, con `bump = 0` (`despues_bump0/`), con `TERRENO.visible_shadow = False` (`despues_sin_sombra_terreno/`) y con el sol con `shadow_filter_radius` ×3 + jitter (`despues_filtro/`); nunca sale en `--modo-ac` (raytracing/fast GI apagados). Ver 10.4. | `crop_36_ladera.png` (peñón: las líneas diagonales dentro de los estratos desaparecen), `crop_51_fondo_bump0.png`, `crop_51_fondo_sombra.png`, `crop_07_sombra.png` |
| 5. "tinte frío" 36 ladera #9CCAD7 (H 192, S 0.27) | La región (500-800, 350-450) de 36 es en un 60 % MAR (#55BCED, S 0.64) + base del peñón: los píxeles de roca miden H 43-57, S 0.12-0.24 (`despues/36`: (650,430) #8B8773, (780,440) #B4A989, (700,420) #D7D5B6). No hay roca cian en 36. | muestreo de píxeles en `diag_r3.py` / PIL |
| 5. 13 roca del lazo #859FAA (H 196), 13 monte-coche #909C9A | Las caras que se ven desde 13 miran al lado contrario del sol nuevo (42°, azimut −119): n·sol −0.46 / −0.38 / −0.17 y el rayo de sombra choca con la propia roca: **están a la sombra y las ilumina solo el cielo** (0.70,0.84,0.98 → cénit 0.12,0.34,0.86). Caliza media (0.45,0.38,0.25) × cielo medio (~0.45,0.65,0.93) = (0.20,0.25,0.23) → H ~180: cualquier albedo de la paleta con B/R > 0.52 sale gris-cian a la sombra de este cielo. Es la luz (world), no el material; el usuario lo dio por bueno ("el frío lo pone la sombra"). Con Specular 0 (v3) baja un poco: 13 pared #7D8884 → #737D78. | `diag_r3.json['pixeles']['13_puente_alto 500,350']` (`sombra: true, al_sol: false`) |
| 6. McLaren en 49 AC gris azulado #919E9E (H 184) | Igual: los 3 píxeles del coche (350,90), (450,200), (150,150) tienen n·sol −0.44 / −0.67 / −0.63 y sombra de `TUNEL_acantilado`: el flanco que ve 49 está a la sombra con el sol nuevo (con el sol de antes, 34°/−140, estaba al sol: por eso el "antes" era beige). El tile tintado del proxy es correcto (media #C2B69B, `diag_r3.json['proxy_ac']`). Con el proxy sin Fresnel (10.1) el tono NO cambia (#899595, H 180): no es el specular, es la luz del cielo. **Falso positivo como problema de material**; lo que SÍ era real: el tile de 6 m repetido (ahora 12 m, factor 0.4) y el cristal pulido 0.26. | `crop_49_ac_mclaren.png` (director / r3 oficial / r3 parcheado) |
| 5. 51 pared normal #E7E1CD (V 0.91) "pared de hielo" | Pared de `MAT_terreno` al sol (n·sol 0.905, nz 0.54) con la caliza media SIN sombra propia (la rama de roca del terreno no multiplica por `terreno_ao`): albedo 0.45 × irradiancia ~2.0 = V 0.90-0.93, y `Specular IOR Level 0.5` + vista a n·v 0.21-0.33 desatura (S 0.12). ARREGLADO: `ao_pared` 0.72 + BSDF mate: **#CDC3AB H 43, S 0.16, V 0.80** (y (1150,370): V 0.93 → 0.85, H 44). | `crop_51_pared.png`, medidas abajo |
| 3. 51 AC pared #DBD0BF vs tierra #DCCCB2 (ΔV 0.01) | En el proxy oficial NADA puede cambiar desde `materiales` (`MAT_terreno_roca` = `color_ac.ROCA_COLOR` literal + tile de hierba heredado; es P1 [W]). Con el parche 10.2 (= la "decisión" del director): pared **#ADA692 (H 45, V 0.68)** vs tierra #DAC7A6 (V 0.85) vs berma #F2E8AF (V 0.95): ΔV pared-tierra **0.17** (antes 0.01). | `crop_51_ac_desmonte.png`, `medidas_ac_r3.json` |

## 11. Qué he cambiado en MIS ficheros (r3)

| Fichero | Cambio |
|---|---|
| `assets/materiales_roca.py` | **grupo v3** (`CAL_VERSION = 3`): (1) sin retícula: la ondulación de los estratos la ponen dos ruidos 2D propios (40 m ±0.8 m, 6 m ±0.2 m; nodos `CAL_ondula_40m/6m`, `CAL_pos_ondulada`) y el Wave lleva Distortion 0.6 (antes 5.0); (2) junta, cornisa, relieve y grano atenuados con la **distancia a la cámara** (Camera Data → `CAL_fade`: 1 a ≤ `fade_cerca_m` 80, 0.25 a ≥ `fade_lejos_m` 260; `fade_lejos_m` ≤ 0 lo desactiva: hornear 2.8); (3) **`ao_pared`** 0.72: la pared = `tono_pared` × ao_pared (sombra propia de los estratos), entra en `media_lineal` (diffuse_color del writer) y en la salida AO; (4) `ajustar_bsdf(material)`: Roughness 1 / Specular IOR Level 0 (sin Fresnel del cielo); `aplicar_a` lo llama; (5) `actualizar_grupo()` v2 → v3 en sitio + BSDF mate en todo lo que lleva el grupo (terreno incluido) + re-escribe `diffuse_color` de los kits con ao_pared (NO el del terreno: es `hierba_seca` del propietario mascara); (6) `reaplicar(material, **kw)` (otro tile/factor/tono sin duplicar grupo ni cadena; nunca el terreno: `es_terreno`); props `cal_tono_base/imagen/tile_m/factor`; (7) `color_roca_terreno_ac()` = (0.242, 0.205, 0.138) #877D68. |
| `aplicar_texturas.py` | familia `caliza_grande` (MAT_MCOCHE_caliza*: tile 12 m, factor 0.4); `--rehacer caliza,caliza_grande` re-aplica materiales que ya llevan el grupo (`reaplicar`); pasada **`rugosidad_mate()`** (FAMILIAS_MATE terreno/hierba/seca/matorral/cesped/bosque/tierra/caliza + todo lo que lleva el grupo: Roughness 1 (césped 0.95) / Specular IOR Level 0; `AJUSTES_BSDF`: `MAT_MCOCHE_cristal_pulido` Roughness 0.5 / Specular 0.3) idempotente, en `aplicar_blend` (log `mates=N`). |
| `assets/montana_coche_v2.py` | `_mat_piedra`: `aplicar_a(..., tile_m=TILE_CALIZA_M 12, factor=FACTOR_CALIZA 0.4)` (solo las constantes de material; geometría intacta). |
| `assets/test_materiales_roca.py` | sección 9 (v3): entradas nuevas, Camera Data, Wave ≤ 1, BSDF mate idempotente, media × ao_pared (0.73), P1 #877D68, `reaplicar` (1 grupo, 1/12, 0.4, tono conservado, nunca terreno), v2 → v3 en sitio con re-tintado, render lejano 200 × 40 m a 320 m con/sin fade (std 0.0694 → 0.0541; energía con componente horizontal 0.25 = bandas, no celdas), losa rasante Specular 0 vs 0.5 (S 0.17 vs 0.14), pared al sol H 46 / S 0.21 / V 0.75. Sol del test = elevación de la escena (42°), azimut 0 para que las caras −y estén al sol. Previews `previews/materiales_roca_{pared,detalle,bancos,orientacion,lejos,lejos_sin_fade,rasante,rasante_spec05}.png`. **TEST_OK** (log `_rev/_tmp_materiales/test_materiales_roca_r3.log`). |
| `_rev/_tmp_materiales/r3/` | `diag_r3.py/.json`, `preparar_r3.py/.json`, `capturas_ac_r3.py` (proxy con 10.1 + 10.2 en memoria), `variante_{bump,sombra,gi}.py`, renders `despues*/`, `AB_*`, `crop_*`, medidas. |

## 12. Cifras antes → después (mismas cámaras; "antes" = candidata del director r2)

**Modo Blender** (`despues/`): 51 pared (1400-1600, 250-350) #E6DFCA (H 46, S 0.12, V 0.90) → **#CDC3AB (H 43, S 0.16, V 0.80)**; (1150-1250, 370-430) V 0.93 → 0.85 (H 44); pista de tierra V 0.90 → 0.89 (H 35): pared/tierra ΔV 0.09; berma (1250-1350, 520-580) sin cambio (#E9E4D0, V 0.92: es repisa nz 0.95 con canal A > 0.5 → `tono_base` clara; el canal A en la berma es de `mascara`, r2 §9.3.2). 36 peñón (700-900, 420-480) #B0B099 → #A2A289 (H 60, S 0.16, V 0.63), estratos sin líneas diagonales. 13 roca del lazo (sombra) #7D8884 → #737D78. 07 montículo (n·sol 0.011) #8F9695 → #787E7C. `medir_capturas` piloto (49+51): pct_cesped 0.00 → 0.00, riqueza 2.236 → 2.352, varianza 0.041 → 0.044, pared_lisa 8.85 → 10.35 (49: 11.0 → 15.4 por el talud más uniforme; 51: 6.7 → 5.3); aéreas pared_lisa 6.3 → 5.07, pct_verde 5.35 → 11.4 (07: 8.2 → 16.6, 36: 7.6 → 17.3: el matorral oliva (H ~80) sin el velo del cielo pasa a contar como "verde" (S > 0.25); pct_cesped sigue 0.01).

**Proxy AC oficial** (`despues_ac/`, lo que verá el director sin parches): 51 sin cambio (es P1); 49 McLaren #929E9F → #8A9697 (más oscuro por ao_pared en la media, mismo tono: sombra); tile del coche 12 m (`crop_49_ac_mclaren.png`); 13 #90A3A6 → #8B9DA0. pared_lisa piloto 30.4 → 31.3, riqueza 1.949 → 1.933 (ruido).

**Proxy AC con 10.1 + 10.2** (`despues_ac_r3/`): 51 pared **#ADA692 (H 45, V 0.68)** / tierra #DAC7A6 (V 0.85) / berma #F2E8AF (V 0.95) / loma izq #C0C9B3; pared_lisa 51 28.7 → **18.1**, 49 33.9 → **6.5**, 07 31.0 → 11.6, 13 55.0 → 17.9, 36 40.1 → 19.3; riqueza 51 1.947 → 2.445, 49 1.92 → 2.237, 07 2.018 → 2.173; pct_cesped 0.0 en las 5. McLaren #899595 (H 180): sin cambio de tono (sombra).

## 13. Parches / avisos a otros propietarios (ronda 3)

### 10.1 Integrador: `_rev/capturas_ab.py` `aplicar_modo_ac()`: el proxy sin Fresnel (fidelidad a ksPerPixel)

En el bucle de materiales, la línea
```python
        for nombre, val in (('Roughness', 0.7), ('Specular IOR Level', 0.3), ('Metallic', 0.0), ('Coat Weight', 0.0),
```
pasa a
```python
        # ksPerPixel (ksSpecular 0.15, exp 24) no tiene Fresnel: con 0.3 las caras a vista rasante devolvian el cielo (F1 r3)
        for nombre, val in (('Roughness', 0.9), ('Specular IOR Level', 0.0), ('Metallic', 0.0), ('Coat Weight', 0.0),
```
Efecto medido (pequeño pero en la dirección correcta; el proxy sigue siendo determinista): S de la roca +0.03 (losa rasante del test), 49/13 sin cambio de tono (su gris es la sombra). Prueba: `capturas_ac_r3.py` con `AC_R3_ROCA=0`.

### 10.2 Integrador: `_rev/capturas_ab.py` `aplicar_modo_ac()`: `MAT_terreno_roca` = caliza media con sombra + tile de caliza (decisión del director r2 n.º 3)

Tras `roca = color_ac.separar_roca_terreno()` (sin tocar `color_ac`; `roca_caras` sigue siendo nz < 0.5 hasta P1):
```python
        # F1 r3 (director r2 n.3, decision): la pared del desmonte = caliza media con su sombra propia y tile de caliza,
        # lo mismo que pide P1 al writer (materiales_roca.color_roca_terreno_ac = caliza_gris_calido x ao_pared x AO media)
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(AQUI), 'assets'))
            import materiales_roca
            m_r = bpy.data.materials.get(color_ac.ROCA_MAT)
            if m_r is not None and m_r.node_tree:
                m_r.diffuse_color = tuple(materiales_roca.color_roca_terreno_ac()) + (1.0,)
                tex = next((n for n in m_r.node_tree.nodes if n.bl_idname == 'ShaderNodeTexImage' and n.image
                            and n.image.colorspace_settings.name != 'Non-Color' and n.outputs['Color'].is_linked), None)
                ruta = os.path.join(os.path.dirname(AQUI), 'texturas', 'caliza_d.png')
                if tex is not None and os.path.exists(ruta):
                    tex.image = bpy.data.images.load(ruta, check_existing=True)
                    tex.image.colorspace_settings.name = 'sRGB'
                    mp = m_r.node_tree.nodes.get('TEX_mapping')
                    if mp is not None:
                        mp.inputs['Scale'].default_value = (1.0 / 3.0,) * 3
                log('modo AC: MAT_terreno_roca = materiales_roca.color_roca_terreno_ac %s + caliza_d 3 m' % (
                    tuple(round(c, 3) for c in m_r.diffuse_color[:3]),))
        except Exception as e:  # noqa
            log('modo AC: materiales_roca no disponible (%s): ROCA_COLOR literal' % e)
```
Es la mitad "color + imagen" de P1 (la mitad "caras por el canal A" sigue siendo [W], problema 4 del director). Si el integrador
mantiene que el proxy no debe adelantarse al writer, que lo diga por escrito: entonces el problema 3 del director queda como
"P1 [W]" y la cifra de referencia es la de `despues_ac_r3/` (ΔV pared-tierra 0.17). Prueba:
`bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/_tmp_materiales/r3/capturas_ac_r3.py -- --blend <copia> --geom
03_blender/_rev/geometria_rev.json --camaras 03_blender/renders/ab/_base_antes/camaras.json --solo 51_,49_ --out <dir> --modo-ac`.

### 10.3 Propietario `mascara` (`construir_pista.mat_terreno`): BSDF mate (una línea) y AO en la roca

- l.324 `bsdf.inputs['Roughness'].default_value = 1.0` → añadir `bsdf.inputs['Specular IOR Level'].default_value = 0.0` (hoy 0.5;
  `aplicar_texturas.rugosidad_mate()` ya lo deja así en cada regeneración, pero el material debe nacer bien).
- La rama de roca (`ROCA_color_grupo`) usa el Color del grupo SIN `terreno_base`/AO: por eso la pared de 51 salía a V 0.93. El
  grupo v3 ya lleva `ao_pared` (0.72 en pared), así que no hace falta cambiar el cableado; si algún día se multiplica la rama de
  roca por `terreno_ao.png`, pasar `crear_nodos(..., ao_pared=1.0)` para no contar la sombra dos veces.
- Aviso (no es mío): el canal A > 0.5 en la berma llana de 51 (nz 0.95, 21 m) sigue pintando caliza clara al pie del desmonte
  (r2 §9.3.2): es lo que impide "roca arriba, tierra al pie, hierba en la berma".

### 10.4 Propietario `mascara` (+ integrador): la celosía de 4 m de las lomas (modo Blender; el director la llama "retícula")

Es la rejilla de triángulos del TERRENO (celdas de 4 m con diagonal) dibujada en el COLOR de la roca y del matorral de las lomas
(51 fondo, 07, 36 bajo el peñón). Aparece con F1 (la base `_base_antes/normal/51` no la tiene) y NO sale en `--modo-ac` (el proxy
reconstruye el material: solo quedan las caras facetadas). Descartado con una variante y un render cada una (copias en
`_rev/_tmp_materiales/r3/`, `crop_51_fondo_{bump0,sombra,gi}.png`, `crop_07_{bump0,sombra}.png`):
`NG_caliza_estratos` (sigue con Wave sin distorsión y con `bump = 0`), sombra propia del terreno (`TERRENO.visible_shadow = False`),
filtro de sombra del sol (`shadow_filter_radius` 1.5 → 4.5, jitter, `shadow_maximum_resolution` ×4), `use_fast_gi = False`,
`use_raytracing = False`, `fast_gi_distance` 8 m; y por PIL: `terreno_ao.png`, `terreno_base.png` y los 4 canales de
`terreno_mask.png` no tienen energía en el periodo de 4 px (0.000-0.002, `crop_ao_lomas51.png`, `crop_maskA_lomas51.png`) y los
tiles están limpios (r2 §9.3.1). Queda UN candidato: la rama **por VÉRTICE** del peso de roca de `mat_terreno()` (`Math.002` =
max(canal A, atributo `roca` + `ROCA_ATR_RUIDO` y umbral 0.49-0.51 SMOOTHSTEP, talud)): un valor por vértice que salta a un lado y
otro del umbral se interpola por triángulo = celosía exactamente donde la máscara está en transición (laderas medias: donde se ve).
Prueba en 2 renders de 51 sobre una copia: (a) `Math.002` con solo el canal A (desenlazar el atributo y el talud) → si la celosía
desaparece, es el atributo: ensanchar el SMOOTHSTEP del umbral (0.49-0.51 → 0.35-0.65) o, mejor, dejar de usar el atributo en el
COLOR (el canal A ya lleva la pendiente > 35-40°, `mascara_terreno`) y conservar `Math.002` solo como contrato para los revisores /
`color_ac`; (b) si no, el talud (`ROCA_nz_ruido`: ruido `nf` por Object a escala de celda). No lo toco: `construir_pista.py` es de
`mascara` en F1.

### 10.5 Propietario `Rocas` (`assets/montana_mclaren.py`): sigue pendiente el parche §2 (r1)

`_mats_mc` cristal pulido 0.26 → 0.5 (mientras tanto lo corrige `aplicar_texturas.AJUSTES_BSDF` en cada regeneración),
`_TONO_GRIETA`/`_TONO_MONTE` desde `paleta.py`, `_mat_hierba` hierba seca. Con el grupo v3 `_retintar()` sigue valiendo (solo
toca `diffuse_color`, Base Color sin enlazar y rampas VALTORGB); OJO: `_retintar(monte, *_TONO_MONTE)` pisa el `diffuse_color`
= media del grupo con el literal (0.34, 0.28, 0.19): tras aplicar el parche §2 el material debe terminar con
`materiales_roca.media_lineal(tono_base, ...)` o simplemente no llamar a `_retintar` cuando `materiales_roca.tiene_caliza(m)`.

### 10.6 Coordinador: el "frío" a la sombra es el cielo del world (decisión, no parche)

`CIELO` (construir_pista l.1585-1606): horizonte (0.70, 0.84, 0.98), medio (0.36, 0.60, 0.95), cénit (0.12, 0.34, 0.86): B/R
1.4 → 7. Una cara a la sombra recibe ~(0.45, 0.65, 0.93) × albedo: caliza media → H ~180 (gris-cian), hueso → H ~185. El usuario
aceptó "el frío lo pone la sombra"; si el director quiere sombras cálidas tipo Pixar hay que desaturar el cielo bajo (p. ej.
horizonte (0.78, 0.84, 0.92), medio (0.48, 0.62, 0.88)) o añadir rebote cálido del suelo: es LUZ (no-hacer 17 no lo prohíbe: no es
view transform ni niebla), cambia `color_cielo_world()` del horizonte (se recalcula solo) y hay que re-medir. No lo toco.

## 14. Verificación propia (resumen) y pendiente honesto

- `test_materiales_roca.py`: TEST_OK (58 checks) tras 4 iteraciones (sol del test, región de la pared lejana, losa fuera del mojado,
  `reaplicar` por nombre de nodo: tras `nodes.remove()` las referencias `n is g` de bpy no son fiables).
- Renders: 5 tomas × (normal, AC oficial, AC parcheado) + 5 variantes de diagnóstico (bump 0, sin sombra del terreno, filtro de
  sombra, sin fast GI, sin raytracing, GI corto); todas sobre copias en `_rev/_tmp_materiales/r3/`; nunca se guardó `escena_rev`,
  `escena_candidata` ni `porto_corsa.blend`.
- Pendiente: (a) P1 en el writer [W] (caras por canal A + color + imagen); (b) la celosía de 4 m de las lomas (10.4) no es de
  materiales; (c) el gris-cian a la sombra es el world (10.6); (d) el parche §2 de `montana_mclaren` (Rocas); (e) `pct_verde` sube
  en 07/36 porque el matorral oliva ya no lleva velo (criterio: `pct_cesped` 0.0 se mantiene).
- EFECTO COLATERAL a declarar: `diag_r3.py` (primera versión) importó `04_export/kn5_writer_opt.py` para usar `analizar_material`
  y el módulo EJECUTA el writer al importarse (`main()` sin guarda): reescribió `04_export/kn5/porto_corsa_opt.kn5` (22:11, 290.5 MB)
  desde `04_export/porto_corsa_export.blend` (15:24, sin cambios) con el mismo código: mismo input que `hacer_zip.sh` paso 2.
  No se ha tocado ningún fichero de código de `04_export`. Si el equipo del zip quiere certeza, que compare el md5 con el del zip
  v1.1 o relance el paso 2. El diagnóstico definitivo ejecuta solo el trozo de `capturas_ab.py` entre `TEX_SIZE` y `aplicar_modo_ac`.

---

# RONDA 4 (05/10 madrugada) — director r3 problemas 4 y 5 (acotación 5 del coordinador; propietario `materiales`)

Todo medido sobre `_rev/_tmp_materiales/r4/escena_r4*.blend` = COPIA de `_rev/escena_candidata.blend` (23:10, la que juzgó el director)
+ `preparar_r4.py` (grupo v3 -> v4, `aplicar_texturas`, McLaren re-aplicado); cámaras congeladas `renders/ab/_base_antes/camaras.json`,
`--solo 07_,36_,49_,51_,55_`, modo normal y `--modo-ac`. "Antes" = `renders/ab/f1_r3/despues{,_ac}` del director (misma candidata).
Variantes EN MEMORIA con `variante_ab.py` (handler `load_post` **con `@persistent`**: sin él Blender lo descarta al abrir el .blend y las
tres primeras variantes salieron idénticas; queda avisado para quien reutilice el patrón). Medidas: `medidas{,_ac}.json`
(`medir_capturas`), `hsv_*.json` (`medir_hsv.py`: H/S/V medios de las regiones que cita el director, con máscara de roca).

## 15. Atribución con cifras (qué era cada cosa)

| Problema del director r3 | Qué es de verdad | Prueba |
|---|---|---|
| 5. "retícula de `NG_caliza_estratos`: celdas de 10-15 m y líneas de estrato cruzando la arista" (07, 36, 51, 21, 14, 22, modo normal) | DOS familias de líneas que se cruzan. (a) **Las juntas de los estratos** (Wave BANDS Z, periodo 3 m): sobre una ladera PLANA vista desde arriba (36) son contornos RECTOS y paralelos (oblicuos en la imagen), y en 51/07 horizontales; eran continuas de ladera a ladera y cruzaban las aristas. Con `sin_junta` desaparecen; con `pared=0` NO (no es la rampa de orientación). ARREGLADO en el grupo v4 (juntas en parches + ondulación). (b) **Estrías oblicuas/verticales** que quedan con `sin_junta` en 51 y 07: el tile de detalle A del terreno (`TEX_detalle_A`, `caliza_d` 3 m) proyectado en PLANTA por `TERRENO_uv_A` y estirado 2-3x sobre la pared (propietario `mascara`, parche 18.2). Las "celdas" = (a) x (b). | `_rev/_tmp_materiales/r4/diag_{36,51,07}_r3_pared0_sinjunta.png` (3 columnas: r3 / pared0 / sin_junta), `hoja_r3_vs_r4_crops.png` |
| 4. McLaren en el proxy AC #8A9697 (H 182) gris azulado "con tile de 3 m" | El tile de la candidata era el de r3: **12 m** (`caliza_d` x 0.4; `preparar_r4.json['antes']`), no 3 m: las manchas claras cada ~95 px son las manchas de 1-3 m de rock_06 (saliencia de baja frecuencia 0.075, la mayor de los 5 tiles de roca) repetidas 7 veces en 80 m. ARREGLADO: tile derivado `caliza_grande_d.png` (24 m, §16). El GRIS-CIAN no es del material: `diffuse_color` del coche = #BAAE95 (H 42, S 0.20) en r3 y **#C1AF89 (S 0.26)** en r4; el proxy normaliza el tile POR CANAL (`textura_tintada`: media = `diffuse_color` exacta), así que lo único que ve es ese color. Lo tiñe el **ambiente del proxy = cielo azul saturado de Blender sin oclusión** (`use_fast_gi` False en `--modo-ac`), mientras que en AC a pelo (`color_ac.TIEMPOS_AC['3_clear']`, tabla de Kunos) el AMBIENTE es **gris neutro** (124/124/124 -> 105/105/105) y el sol cálido (170/160/140). Con la luz del mundo gris de la misma luminancia (variante `amb_gris_luz`, el parche 18.1): McLaren **#A49575 H 41 S 0.29** (caliza media #B3A68A es H 41 S 0.23). | `crop_49_ac_r3_r4_r4c.png`, `hsv_amb.json`, `hsv_amb_luz.json` |
| 4. roca del proxy neutra (49 talud S 0.07, 51 S 0.05, 55 S 0.06, 07 S 0.08) | Misma causa: `MAT_terreno_roca` del proxy = `color_roca_terreno_ac()` = **#877D68 H 41 S 0.23** (= S de la caliza media; comprobado en `preparar_r4.json`), y los kits #BAAE95 S 0.20 -> #BEB08E S 0.26 (r4). Con la luz gris: 51 pared S 0.15 -> **0.26**, 07 roca 0.07 -> **0.25**, 55 talud 0.06 -> **0.17**, 49 talud/McLaren 0.06 -> 0.30. Lo que SÍ era de materiales y está corregido: la media exportada ignoraba el TINTE del tile de Blender (`TEX_ganancia` escalar 1.78 sobre una media por canal (0.608, 0.563, 0.431) = (1.08, 1.00, 0.77): Blender se veía más cálido que el KN5). | `hsv_amb_luz.json`; §16 `media_material` |

## 16. Qué he cambiado en MIS ficheros (r4)

| Fichero | Cambio |
|---|---|
| `assets/materiales_roca.py` | **grupo v4** (`CAL_VERSION = 4`, misma interfaz: `actualizar_grupo()` lo rehace en sitio): (1) `CAL_parches`: junta y cornisa x ruido 3D de ~30 m (0.15..1, smoothstep): los estratos se marcan por TRAMOS, nunca como líneas rectas continuas que crucen laderas y aristas; (2) ondulación 40 m ±1.2 m + 14 m ±0.5 m + 6 m ±0.2 m (`CAL_ondula_14m`): contornos no rectos sobre laderas planas; (3) `CAL_nz_ruido`/`CAL_nz_dither`: la rampa de orientación lee nz + ruido 3D ±0.06 (~3 m) y es más ancha (`PARED_NZ` 0.92..0.55): sin bandas de Mach en las facetas de 4 m; (4) `FADE_CERCA_M` 80 -> 60, `FADE_MIN` 0.25 -> 0.12 (en 36 a 250-400 m las juntas seguían siendo líneas oscuras); (5) **`tinte_tile(imagen, factor)` + `media_material(...)`**: `diffuse_color` = `media_lineal` x ((1-f) + f x media_tile x ganancia escalar) por canal (`caliza_d` f 0.5: (1.04, 1.00, 0.88)); lo usan `aplicar_a`, `reaplicar` y el re-tintado de `actualizar_grupo` (`_tile_de()` lee `cal_imagen`/`cal_factor` o la cadena TEX_*). `color_roca_terreno_ac()` NO lleva tinte (el detalle A del terreno se normaliza por canal en `construir_pista`): sigue #877D68; (6) `IMAGEN_RESPALDO`: `aplicar_a(imagen=X)` cae a `caliza_d.png` si X no existe; `media_lineal` cuenta la junta solo en los parches (`_JUNTA_FRAC` x 0.6). |
| `texturas/generar_texturas.py` | **`caliza_grande()` -> `caliza_grande_d.png` (24 m)**, tile DERIVADO para el McLaren (y rocas de > 50 m): capas de `afloramiento_d` (24 m; saliencia de baja frecuencia 0.040, la menor) + `caliza_d` girado 90° a 12 m + `afloramiento` a 8 m (`CALIZA_GRANDE_PESOS`), ruido espectral de baja frecuencia ±6 % (rompe sub-periodos), grano de banda media 0.7/0.26 m (`CALIZA_GRANDE_GRANO`) y **piedras PASO-ALTO de `caliza_d`** (`CALIZA_GRANDE_PIEDRAS` = (sigma 1.5 m, peso 0.8, 1 repetición = estiradas a los 24 m, sin sub-periodo de 12 m): el contenido de 10-50 cm que da varianza local a 100-200 m (`pared_lisa` de 49 vuelve a 7 %: sin esta capa el coche salía LISO, 40-53 %), SIN las manchas > 1.5 m que se repetían). Iteraciones medidas en 49 AC: contraste 60 %/f 0.3 -> 52.9 %; f 0.5 -> 48.1; +grano f 0.6 -> 39.6; +piedras 12 m -> 5.9; +piedras 24 m (definitivo) -> **7.4** (r3 6.3). Media lineal = `caliza_ocre`. `TILE_M`, `GENERADORES`, `ORDEN` (después de `caliza`). Seamless (costura 0.99). 2.4 MB PNG (en el KN5 va a 1024/512: +0.3-1 MB). |
| `texturas/recolorear_cc0.py` | al final de `main()`, si se recolorea `roca_caliza`/`roca_afloramiento`, rehace `caliza_grande_d.png` (orden: PIL, CC0, DERIVADOS). `medias.json` ya lleva la entrada. |
| `aplicar_texturas.py` | `FAMILIAS['caliza_grande']` = `caliza_grande_d.png`, 1/24, factor 0.5 (respaldo ganancia 1.63). `--rehacer caliza_grande` re-aplica (`reaplicar`). Docstring. |
| `assets/montana_coche_v2.py` | `TILE_CALIZA_M` 12 -> 24, `FACTOR_CALIZA` 0.4 -> 0.5, `IMAGEN_CALIZA = 'caliza_grande_d.png'`; `_mat_piedra` pasa `imagen=`. Solo constantes de material; geometría intacta. `test_montana_coche_v2.py`: TEST_OK. |
| `assets/test_materiales_roca.py` | sección 10 (v4): nodos nuevos, parches 0.15..1, fade 0.12, `tinte_tile` (R > 1 > B), `media_material` S 0.257 > `media_lineal` 0.199, P1 sin tinte S 0.23, `caliza_grande_d.png` + mapping 1/24, respaldo de imagen, v3 -> v4 en sitio con re-tintado, `Math.002` intacto; checks de r1-r3 que comparaban `diffuse_color` con `media_lineal` pasan a `media_material`; el ratio con/sin fade a 320 m 0.85 -> 0.95 (con las juntas en parches pesan menos en la std: 0.89 medido). **TEST_OK** (`_rev/_tmp_materiales/test_materiales_roca_r4.log`). |
| `_rev/_tmp_materiales/r4/` | `preparar_r4.py/.json`, `rehacer_mclaren.py`, `variante_ab.py` (pared0 / sin_junta / sin_bancos / amb_neutro / amb_gris / amb_gris_luz), `medir_hsv.py`, renders `antes*/`, `despues*/`, `diag_*/`, `despues_ac_amb_*/`, recortes `crop_*`, `diag_*.png`, `hoja_r3_vs_r4_crops.png`, medidas. Nunca se guardó `escena_rev`, `escena_candidata` ni `porto_corsa.blend`. |

## 17. Cifras antes -> después (mismas cámaras; "antes" = candidata r3 del director)

- **(c) Retícula, modo normal** (`hoja_r3_vs_r4_crops.png`, columnas r3 | r4): 36 ladera: desaparece la familia de líneas oblicuas (quedan parches de junta tenues); 51 pared: desaparecen las horizontales continuas (quedan las estrías oblicuas del tile planar, 18.2); 07: ídem (quedan las estrías verticales). Las medias no se mueven (es lo esperado: cambia la estructura, no el color): `medir_capturas` 07 riqueza 2.50 -> 2.49, pared_lisa 1.3 -> 1.4; 36 2.37 -> 2.36 / 7.1 -> 7.8; 51 2.72 -> 2.70 / 5.2 -> 5.5; 55 1.80 -> 1.79 / 48.3 -> 48.0; pct_cesped 0.00 en todas; bandas_blancas sin cambio. H/S/V de las regiones (normal): 36 ladera #969E87 -> #99A189, 51 pared roca S 0.16 -> 0.16, 07 #8D918D -> #939994: sin cambio de color.
- **(b) Roca en el proxy AC oficial** (`medidas_ac.json`, `hsv_ac.json`): terreno sin cambio por construcción (P1 = #877D68 S 0.23 ya en r3): 51 pared_lisa 17.7 -> 17.7, riqueza 2.46 -> 2.47; 07 10.9 -> 10.8; 55 2.3 -> 2.3. Kits (peñón, 36): diffuse S 0.20 -> 0.26: riqueza 2.14 -> **2.29**, pared_lisa 20.3 -> 19.3. Con el parche 18.1 (luz gris, cámara con cielo azul): 51 pared roca S 0.15 -> **0.26** (#B7A787 H 41), 07 S 0.07 -> **0.25** (#8B8068 H 42), 55 S 0.06 -> **0.17** (#AFA692 H 42), 49 talud+McLaren S 0.06 -> **0.30**; el cielo visible NO cambia ((150,197,255) en el píxel (800,60) de 55 en ambos).
- **(a) McLaren, proxy AC** (`crop_49_ac_r3_r4_r4c.png`): con `caliza_grande` el tile ya no se lee repetido (saliencia de baja frecuencia del tile 0.028 frente a 0.075 de `caliza_d`; 3 repeticiones en 80 m en vez de 7) y el cuerpo sigue teniendo grano. Color: `diffuse_color` #BAAE95 -> #C1AF89 (S 0.20 -> 0.26); en el proxy oficial #8A9697 H 182 -> #8F978B H 98 (menos azul; el resto es la luz, 18.1: #A49575 H 41 S 0.29). Coste que hay que conocer: `pared_lisa` de 49 cuenta el cuerpo del coche como "roca" (99 % de la región): con el primer tile (contraste 60 %, factor 0.3) subió de 6.3 % a 52.9 %; con factor 0.5 48.1; con grano y factor 0.6 39.6; con las piedras paso-alto (tile definitivo) ver 17.c. En modo normal 49: 15.4 -> 24.2 (factor 0.6) por la misma razón.
- **17.c (tile definitivo = el que está en `texturas/`: `caliza_grande` con piedras paso-alto de `caliza_d` estiradas a 24 m (1 repetición), factor 0.5; `escena_r4e.blend`, `despues_ac_e/`, `despues_e/`, `crop_49_ac_r3_r4d_r4e.png`)**: 49 AC `pared_lisa` **6.3 -> 7.4 %** (r3 -> r4e; con 2 repeticiones de 12 m, r4d: 5.9), riqueza 2.24 -> 2.26, varianza 0.040 -> 0.040, pct_cesped 0.0; 49 normal `pared_lisa` **15.4 -> 15.4**, riqueza 2.02 -> 1.97. Es decir: igual de "rugoso" que r3 para `medir_capturas`, sin las manchas claras periódicas (saliencia de baja frecuencia del tile 0.028 frente a 0.075; en el recorte no hay patrón repetido) y con `diffuse_color` #BFAF8C (S 0.25, caliza media/clara cálida). El tono del proxy oficial sigue siendo el de la luz (#8E978E H 121; con 18.1 #A49575 H 41 S 0.29).

## 18. Parches / avisos a otros propietarios (ronda 4)

### 18.1 Integrador: `_rev/capturas_ab.py` `aplicar_modo_ac()`: la LUZ del mundo gris (AC a pelo), la cámara sigue viendo el cielo azul

Tras el bloque 3) (`use_raytracing`/`use_fast_gi` a False), añadir:
```python
    # 4) F1 r4 (PARCHES_F1_materiales.md 18.1): el ambiente de AC a pelo es GRIS (color_ac.TIEMPOS_AC['3_clear']: AMBIENTE 124/124/124
    #    -> 105/105/105, sol 170/160/140), y el proxy usaba como ambiente el cielo azul saturado de Blender SIN oclusion: tenia de
    #    gris-cian todo lo que no mira al sol (McLaren de 49 #8A9697 H 182; roca de 51/07/55 S 0.04-0.07 con diffuse S 0.23).
    #    La CAMARA sigue viendo el cielo (hojas, pct_azul, horizonte): solo cambia la luz (rayos no de camara) via Light Path.
    w = sc.world
    nt_w = w.node_tree if (w and w.use_nodes) else None
    out_w = next((n for n in nt_w.nodes if n.type == 'OUTPUT_WORLD'), None) if nt_w else None
    bg_w = out_w.inputs['Surface'].links[0].from_node if (out_w and out_w.inputs['Surface'].links) else None
    if bg_w is not None and bg_w.type == 'BACKGROUND' and nt_w.nodes.get('AC_mezcla_camara') is None:
        gris = nt_w.nodes.new('ShaderNodeBackground'); gris.name = 'AC_ambiente_gris'
        gris.inputs['Strength'].default_value = float(bg_w.inputs['Strength'].default_value)
        if bg_w.inputs['Color'].links:
            bw = nt_w.nodes.new('ShaderNodeRGBToBW'); bw.name = 'AC_luminancia'
            nt_w.links.new(bg_w.inputs['Color'].links[0].from_socket, bw.inputs['Color'])
            nt_w.links.new(bw.outputs['Val'], gris.inputs['Color'])
        else:
            c = bg_w.inputs['Color'].default_value
            g = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
            gris.inputs['Color'].default_value = (g, g, g, 1.0)
        lp = nt_w.nodes.new('ShaderNodeLightPath'); lp.name = 'AC_light_path'
        mix = nt_w.nodes.new('ShaderNodeMixShader'); mix.name = 'AC_mezcla_camara'
        nt_w.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
        nt_w.links.new(gris.outputs['Background'], mix.inputs[1])      # luz (probe): gris de la misma luminancia
        nt_w.links.new(bg_w.outputs['Background'], mix.inputs[2])      # camara: el cielo azul de siempre
        nt_w.links.new(mix.outputs['Shader'], out_w.inputs['Surface'])
        st['mundo'] = 'luz gris (luminancia del CIELO), camara con cielo azul'
```
Probado tal cual en memoria (`variante_ab.py amb_gris_luz`, `despues_ac_amb_gris_luz/`): 49 McLaren #8D9792 -> **#A49575 (H 41, S 0.29)**,
51 pared roca S 0.15 -> 0.26, 07 0.07 -> 0.25, 55 0.06 -> 0.17; píxel de cielo de 55 (800,60) = (150,197,255) antes y después.
Es un cambio de FIDELIDAD del proxy (no de la escena): afecta a todas las cifras `*_ac` futuras, así que conviene que el
coordinador lo ratifique por escrito y que el A/B de r4 se mida con y sin él (la base `_base_antes/ac` se re-renderiza con
el mismo script: 1 pasada). Alternativa si no se ratifica: el problema 4 del director queda documentado como "ambiente del
proxy" con estas cifras, y los colores del KN5 (que son lo que verá el amigo) quedan como están: caliza media exacta.

### 18.2 Propietario `mascara` (`construir_pista.mat_terreno`, bucle de `TILES_TERRENO` l.~411-430): el detalle A en BOX, no en planta

Las estrías oblicuas/verticales de 51 y 07 (lo que queda de la "retícula" cuando se quitan las juntas: `diag_51_r3_pared0_sinjunta.png`,
columna 3) son `TEX_detalle_A` (`caliza_d` 3 m) muestreado por `TERRENO_uv_A` (planta) y estirado 1/cos(pendiente) = 2-3x sobre las
paredes. Para el canal A (roca = lo que está en pendiente) sustituir la proyección plana por BOX en coordenadas de objeto, que es
además lo que hacen el writer y el proxy con `TEX_mapping` (Object x 1/3, BOX):
```python
        if k == 'A':
            esc = _nodo_vec(nodes, links, 'SCALE', texm.outputs['Object'], nombre='TERRENO_obj_A', escala=1.0 / tile_m)
            tx.projection = 'BOX'
            tx.projection_blend = 0.3
        else:
            esc = _nodo_vec(nodes, links, 'SCALE', uv01.outputs['Vector'], nombre='TERRENO_uv_' + k, escala=Lx / tile_m)
        links.new(esc.outputs['Vector'], tx.inputs['Vector'])
```
(`texm` = `TERRENO_texcoord` ya existe en l.~407; `tx` es el Image Texture del canal. R/G/B en planta siguen bien: < 40° = estirado < 1.3x.)
`samplers['txDetailA']`/`props['multA']` no cambian (en el KN5 el multicapa sigue por UV: es [W]). Prueba: render de 51/07 sobre una
copia con `capturas_ab --solo 51_,07_`: las estrías desaparecen y la caliza de la pared se ve con el mismo grano que la de las repisas.

### 18.3 Coordinador: decisiones y registro para F2

- Ratificar (o no) 18.1 por escrito: es lo único que cambia la saturación de la roca y del McLaren en las CIFRAS del proxy; en el KN5 los
  colores ya son la caliza media (#877D68 el terreno, #BEB08E los kits, #C1AF89 el coche).
- Registro F2: `pared_lisa` de 49 incluye el cuerpo del McLaren (99 % de la región de roca de esa toma); con el tile de 24 m sin manchas
  repetidas el cuerpo es más liso en el proxy (sin AO ni sombra propia) que con rock_06 a 12 m. La cifra de referencia de 49 pasa a ser
  la de 17.c; el KPI "pared_lisa 49 < 30 %" del bloque 2 debería medirse sobre el talud (región (1000-1600, 150-700)) y no sobre el coche,
  o con el faldón de ladera + AO horneada del McLaren (bloque 2.4, F2).
- 10.6 sigue vigente para el modo normal: a la sombra, con este cielo, cualquier caliza sale gris-cian; es luz, no material.

### 18.4 Propietario `Rocas` (`assets/montana_mclaren.py`): parche §2 (10.5) sigue pendiente, pero NO explica el gris

`MAT_MCOCHE_caliza_grieta` / `_monte` miden en la candidata #BFAF92 (S 0.24) / #9E9079 (S 0.23): sus literales son equivalentes a
`caliza_ocre` x 0.87 / `caliza_gris_calido`; el cristal pulido 0.26 lo corrige `aplicar_texturas.AJUSTES_BSDF` en cada regeneración.
Al aplicar §2, usar `imagen=montana_coche_v2.IMAGEN_CALIZA` (lo hace `_V2._mat_piedra` solo) y no llamar a `_retintar` cuando
`materiales_roca.tiene_caliza(m)` (pisaría `media_material`).

## 19. Verificación propia y pendiente honesto

- `test_materiales_roca.py` TEST_OK (sección 10 nueva), `test_montana_coche_v2.py` TEST_OK; `preparar_r4` (v3 -> v4 en sitio, 5 McLaren
  rehechos, 0 tocados: idempotente); renders 5 tomas x (normal, AC) + variantes pared0 / sin_junta / amb_neutro / amb_gris / amb_gris_luz
  + 3 iteraciones del tile del McLaren (r4b/r4c/r4d); todo sobre copias en `_rev/_tmp_materiales/r4/`.
- Pendiente: (a) 18.1 es decisión del coordinador: sin él las cifras `*_ac` de saturación no se mueven (la causa no está en el material);
  (b) las estrías del tile planar del terreno (18.2) son de `mascara`; (c) P1 [W] sigue igual; (d) `pared_lisa` de 49 depende del coche
  (18.3); (e) el parche §2 de `montana_mclaren` (Rocas). (f) `caliza_grande_d.png` es un derivado: si se regenera `caliza_d`/`afloramiento`
  hay que relanzar `python texturas/generar_texturas.py caliza_grande` (o `recolorear_cc0.py`, que lo hace solo).
