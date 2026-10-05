# Parches del propietario `vegetacion_plan` (F1, bloque 4.1) para el integrador

Fichero mío: `03_blender/vegetacion.py` (nuevo) -> `03_blender/vegetacion_plan.json` + `renders/qa/vegetacion_mapa.png`.
Detalles y cifras en `vegetacion_README.md`. Líneas citadas = `integrar_escena.py` tal como está el 04/10 (comprobar).

## A. F1 — AHORA (lo único que se aplica en esta fase: el JSON se genera, nadie lo consume)

### A1. `03_blender/_rev/pipeline_escena.sh`: paso `vegetacion.py` tras `urbanismo.py` (y tras `mascara_terreno.py` cuando exista)

Insertar DESPUÉS de la línea 56 (`grep -E "QA:|TOTAL casas" "$LOGS/urbanismo.log" ...`) y antes del bucle de Blender:

```bash
# fase visual F1 (bloque 4.1): plan de vegetacion por mascaras (python del sistema, ~5 s). Orden del plan secc. 13:
# preparar_geometria -> urbanismo -> mascara_terreno -> generar_mar -> vegetacion -> construir_pista. Si mascara_terreno
# todavia no esta en el pipeline, va aqui mismo; cuando entre, este paso se mueve justo detras de el.
python vegetacion.py > "$LOGS/vegetacion.log" 2>&1 || { echo "FALLO vegetacion"; tail -20 "$LOGS/vegetacion.log"; exit 1; }
grep -E "TOTAL|VERIFICACION" "$LOGS/vegetacion.log" | cut -c1-300
```
`vegetacion.py` devuelve 1 (y el pipeline para) solo si su verificación final encuentra un punto a < w/2 + 12 m del eje,
dentro de un solar/edificio o en el mar; sin `huellas.json`/`camaras.json` sigue con aviso.

Opcional (recomendado, 2 líneas) en `copiar_candidata()` l.23-26: añadir `&& cp vegetacion_plan.json "$REV/vegetacion_candidata.json"`
a la cadena de `cp` y la clave `'vegetacion': rev + '/vegetacion_candidata.json'` al manifiesto `man` (l.32-35), para que
`promover.sh` congele el plan con la escena.

Prueba: `cd 03_blender && python vegetacion.py` (5 s) -> log `TOTAL 23792 plantas: 7752 arboles ... 16040 matas` (con
`texturas/terreno_mask.png` de las 16:28; cada versión de la máscara cambia las cifras; sin ella 32694),
`VERIFICACION {"pista_lt_w2_mas_12": 0, "dentro_de_solar_o_edificio": 0, "en_mar": 0}`; segunda ejecución -> `cmp` idéntico.

### A2. `RONDA15_PLAN.md` REGISTRO: líneas añadidas por mí (hecho).

### A3. Nota para el propietario de `mascara_terreno.py` (no es un parche a fichero ajeno; es el contrato de lectura)

`generar(..., veg_plan='03_blender/vegetacion_plan.json')`: `d = json.load(...)`; `d['plantas']` con `d['especies'][p['especie']]['clase'] == 'arbol'`;
radio de sombra `1.2 x d['especies'][e]['radio_copa_m'] x p['escala_xy']` (versión rápida: `d['masas']` con cx, cy, r).
El plan lee a su vez los canales A (roca) y B (tierra) de `terreno_mask.png` (no la base), así que el orden
`mascara_terreno -> vegetacion` no es circular; si la "sombra de bosque" debe salir de la MISMA pasada, ejecutar
`python vegetacion.py` también antes de `mascara_terreno.py` (5 s; mismo resultado si A/B no cambian).

## B. F3 — integración (NO aplicar en F1; exige el kit v3 `sin_alfa`: con v2 las 8.9 k + 17.9 k piezas serían ~5 M tris, prohibido por el plan 15.8)

### B1. `integrar_escena.py` `clone()` l.90-104: escala no uniforme

Sustituir
```python
    if scale != 1.0:
        nr.scale = (scale, scale, scale)
```
por
```python
    if isinstance(scale, (tuple, list)):
        nr.scale = tuple(float(s_) for s_ in scale)
    elif scale != 1.0:
        nr.scale = (scale, scale, scale)
```

### B2. `integrar_escena.py` `build_library()` l.255-311: piezas v3 por (especie, variante, tono)

Contrato con el kit v3 (`assets/vegetacion_kit_v3.py`, mismo API que v2 + `tono`): `build_<especie>(parent, alto, seed,
variante, tono='a', sin_alfa=True) -> VEG_<especie>` con `ob['VEG_variante']`, `ob['VEG_alto'] = alto`, `ob['VEG_copa'] = radio`
y material `MAT_VEG_<especie>_<tono>` (color = `paleta.variante(especies[e].paleta, especies[e].tonos[tono])`, que es
`diffuse_color`/Base Color sin enlazar). Añadir al final de `build_library()` (tras `log('vegetacion v2: ...')`):
```python
    # fase visual F3 (4.2): piezas del plan de vegetacion, una por (especie, variante, tono) del JSON
    if getattr(vk, 'VERSION', 2) >= 3 and os.path.isfile(RUTA_VEG_PLAN):
        import json as _json
        esp = _json.load(open(RUTA_VEG_PLAN, encoding='utf-8'))['especies']
        n_v3 = 0
        for e, E in sorted(esp.items()):
            fn = getattr(vk, 'build_' + e, None)
            if fn is None:
                continue
            for k_, v in enumerate(E['variantes']):
                for t in sorted(E['tonos']):
                    lib['%s|%s|%s' % (e, v, t)] = fn(LIB, alto=E['alto_nominal_m'], seed=100 + 7 * k_, variante=v, tono=t)
                    n_v3 += 1
        log('vegetacion v3: %d piezas del plan' % n_v3)
```
(8 especies x 2-4 variantes x 3 tonos = ~70 piezas de <= 250 tris en LIB; el writer las fusiona por material igual que hoy.)
`RUTA_VEG_PLAN` arriba, junto a las rutas (l.20-30):
`RUTA_VEG_PLAN = os.environ.get('VEG_PLAN') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vegetacion_plan.json')`.
Mover a `build_library()` las dos líneas de `zona_montana` l.2226-2229 (`lib['olivo'] = M['olivos'].build_olivo(...)`,
`lib['matorral'] = ...`) para que sigan existiendo como piezas de reserva.

### B3. `integrar_escena.py`: nueva `zona_vegetacion_plan()` en el sitio de `zona_montana` (l.2223-2318 se borran enteras)

`safe('zona_montana', zona_montana)` l.2318 pasa a `safe('zona_vegetacion_plan', zona_vegetacion_plan)` (misma posición:
tras `zona_horquillas`, antes de `zona_montanas_fondo`/`zona_horizonte`).
```python
# ============ VEGETACION DEL PLAN (fase visual 4.1/4.2: vegetacion.py -> vegetacion_plan.json) ============
SALTAR_LOD2 = False   # True si kn5_presupuesto.py se pasa: los ~1.3 k 'lod' 2 (> 400 m de la pista) no se clonan

def _pieza_plan(especie, variante, tono):
    """Pieza de LIB para una planta del plan: v3 '<e>|<v>|<t>'; si no, cualquier tono de esa variante; si no, la base."""
    for k in ('%s|%s|%s' % (especie, variante, tono), '%s|%s|a' % (especie, variante)):
        if k in lib:
            return lib[k]
    for k, ob in lib.items():   # v2: por ob['VEG_variante'] (nunca con 8.9 k arboles: solo para pruebas con --cfg reducido)
        if (k == especie or k.startswith(especie + '_v')) and str(ob.get('VEG_variante', '')) == str(variante):
            return ob
    return lib.get({'arbusto': 'arbusto_v0', 'encina': 'encina_v0', 'olivo': 'olivo_v0' if 'olivo_v0' in lib else 'olivo'}.get(especie, especie))

def zona_vegetacion_plan():
    import json as _json
    if not os.path.isfile(RUTA_VEG_PLAN):
        log('vegetacion: falta %s (ejecutar python vegetacion.py antes de construir_pista); zona vacia' % RUTA_VEG_PLAN)
        return
    d = _json.load(open(RUTA_VEG_PLAN, encoding='utf-8'))
    plantas = d['plantas'] if isinstance(d, dict) else d
    esp = d.get('especies', {}) if isinstance(d, dict) else {}
    n = {'ok': 0, 'sin_pieza': 0, 'lod2': 0}
    por_esp = {}
    for i, p in enumerate(plantas):
        if SALTAR_LOD2 and p['lod'] >= 2:
            n['lod2'] += 1
            continue
        ob0 = _pieza_plan(p['especie'], p['variante'], p['tono'])
        if ob0 is None:
            n['sin_pieza'] += 1
            continue
        alto_nom = float(esp.get(p['especie'], {}).get('alto_nominal_m', 1.0))
        alto_pieza = float(ob0.get('VEG_alto', 0.0) or ob0.dimensions.z or alto_nom)
        f = alto_nom / max(alto_pieza, 0.1)                     # escala_* del plan son relativas a alto_nominal
        sxy, sz = p['escala_xy'] * f, p['escala_z'] * f
        ob = clone(ob0, (p['x'], p['y'], p['z'] - 0.15), p['rot'], scale=(sxy, sxy, sz))   # -0.15 como hoy (asentar lo apoya)
        ob.name = 'VEG_' + p['especie']                        # VEG_pino / VEG_encina / ... / VEG_matorral: prefijo ya dado de alta
        ob['VEG_plan'] = i; ob['VEG_variante'] = p['variante']; ob['VEG_tono'] = p['tono']
        ob['VEG_masa'] = int(p['masa_id']); ob['ac_lod'] = int(p['lod'])   # ac_lod -> lodIn/lodOut del writer (peticion P4)
        if 'VEG_copa' in ob0:
            ob['VEG_copa'] = float(ob0['VEG_copa']) * sxy      # radio real de copa para asentar.copa_calzada (4.3)
        _libre(p['x'], p['y'], r=0.5)                           # reserva el sitio para las zonas posteriores
        n['ok'] += 1
        por_esp[p['especie']] = por_esp.get(p['especie'], 0) + 1
    log('vegetacion del plan: %d clones (sin pieza %d, lod2 saltados %d) de %d | %s'
        % (n['ok'], n['sin_pieza'], n['lod2'], len(plantas), ' '.join('%s %d' % kv for kv in sorted(por_esp.items()))))
safe('zona_vegetacion_plan', zona_vegetacion_plan)
```
Las 124 rocas `VEG_roca` que ponía `zona_montana` (tipos `roca`/`roca2`) NO están en el plan: recomendación = dejar que
los afloramientos y pedruscos del bloque 2.5 (F2) las sustituyan. Si se quieren mantener en F3 antes de 2.5: función
`zona_rocas_sueltas()` con `random.Random(4242)` propio (no el `rnd` global: así el plan sigue siendo determinista)
que copie SOLO el bucle de semillas de la pasada 1 (l.2236-2270) filtrando `t in ('roca', 'roca2')` y `_libre`.

### B4. `integrar_escena.py` `zona_tierra()` l.1711-1728: quitar los 16 árboles alternos (los pone el plan)

Borrar l.1712-1723 (`s_m = 1570` ... `k += 1`) y la línea `log('tierra: %d arboles sin sitio ...')` l.1728; dejar las
pacas de la curva 26 y las 10 rocas de cima (l.1752-1756) tal cual.

### B5. `integrar_escena.py` `zona_casino()` l.2097-2119: quitar los 26 "jardines" aleatorios

Borrar desde `gs = [CURVAS[n] for n in (33, 35, 39)]` hasta `log('jardines del casino: %d elementos' % puestos)` y dejar
`log('jardines del casino: del plan de vegetacion (zona jardin_casino)')`. El plan pone 61 elementos en el mismo
cuadrado (adelfa, palmera, ciprés, olivo, arbusto a >= 9 m entre sí y a >= w/2 + 12 m del eje; hoy era 11 m al eje).

### B6. `integrar_escena.py` `enriquecer_vegetacion()` l.6498-6530: el tono viene del plan

Tras `n = m.name` (l.6501) añadir:
```python
        if n.startswith('MAT_VEG_') and n[-2:] in ('_a', '_b', '_c'):
            continue   # fase visual: materiales por tono del plan de vegetacion (kit v3); el color es la media de paleta
```
(los `MAT_VEG_*` de v2 y `MAT_OLI_*` siguen variándose mientras existan).

### B7. Altas de prefijos: NINGUNA nueva

Todas las plantas se llaman `VEG_<especie>` (`VEG_matorral` es nombre nuevo pero prefijo `VEG_`): ya cubiertas por
`asentar_objetos.ARBOL_PREF` l.162, `despeje_final.DESPEJE_ARBOL` l.5949, `eliminar_sumergidos.PREFIJOS` l.9,
`revisar_invasores.REGLAS` l.72, `revisar_flotantes` (no exentas: correcto). `revisar_fisica_ac.NO_OBSTACULO`: sin cambio
(no hay petición nueva en `PETICIONES_04_EXPORT.md`; `ob['ac_lod']` cae en la P4 ya listada).

### B8. Puerta de calidad (opcional, cuando el plan se consuma): `_rev/puerta_calidad.py`

Nueva `valores_vegetacion(plan, v, motivos)`: leer `vegetacion_plan.json` (`stats`): `6000 <= arboles <= 9000`,
`15000 <= matas <= 20000`, `holgura_pista_lt_12_n == 0`, `dentro_core_urbano_n == 0`, `arboles_con_vecino_lt_6m_pct >= 70`,
`arboles_z_gt_80_pct >= 30`; y de `asentar.json` `arboles_quitados < 20` (KPI del bloque 4). Añadir `vegetacion.log`
a la frescura como `urbanismo.log`.

### B9. Prueba de la integración (F3)

1. `python vegetacion.py` (5 s) -> JSON; 2. cadena `construir_pista` + `integrar_escena` sobre COPIAS por la cola (como
hizo el v3 integrador en `scratchpad/integ_v3/run_cadena.sh`), `ERRORES: ninguno`, línea `vegetacion del plan: N clones`
con N = `stats.total` del JSON (23792 hoy; 22482 con `SALTAR_LOD2`); 3. `asentar.json['por_familia']` ~ el `stats.por_especie` del plan y
`arboles_quitados` + `despeje final: quitados` < 20 (si no, revisar márgenes `CFG['margen_*']` o `pend` del encinar);
4. `_rev/kn5_presupuesto.py` sobre el export de prueba: vegetación <= 0.9 M tris (si se pasa: `SALTAR_LOD2 = True`,
`--cfg` con coberturas menores, o piezas más baratas: README §3.6); 5. A/B set `vegetacion` (01, 07, 10, 21, 34_general)
+ piloto 50/51/52 en modo normal y AC; `medir_capturas.siluetas_20_120` x3.
