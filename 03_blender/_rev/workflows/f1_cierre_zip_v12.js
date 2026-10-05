export const meta = {
  name: 'f1-cierre-zip-v12',
  description: 'Cierre de F1 (regeneracion final, puerta, promocion) en paralelo con el equipo de export (writer para el terreno nuevo, vista "como AC" leida del KN5, fisica sobre el terreno nuevo, mini-pista F del pueblo/puerto); export final de la escena promovida, verificador independiente, una ronda de correccion y paquete zip v1.2 (sin publicar)',
  phases: [
    { title: 'Cierre F1', detail: 'regeneracion final + 3 literales de paleta + puerta + A/B corto + promocion' },
    { title: 'Export dev', detail: 'writer/terreno, kn5_vista, mini-pista F, sobre la candidata r4' },
    { title: 'Export final', detail: 'export de la escena promovida, fisica, kn5_check, vistas como AC, zip v1.2' },
    { title: 'Verificar', detail: 'verificador independiente + correccion' },
  ],
}
const BASE = 'E:/Escritorio/claude-pc/arnau-aseto-corsa'
const B3 = BASE + '/03_blender'
const B4 = BASE + '/04_export'
const FV = B3 + '/_rev/fase_visual'
const COMUN = `
REGLAS COMUNES (Porto Corsa, mod de Assetto Corsa; Blender 5.1 + Python; AC NO esta instalado en este PC):
- Proyecto ${BASE}. Escribe en espanol. Lee ${FV}/ACOTACIONES_COORDINADOR_F1.md (decisiones 13-16 mandan), ${FV}/DECISIONES_USUARIO.md, ${B3}/FASE_VISUAL_PLAN.md (secciones 0, 12 y 15) y ${FV}/director_f1_r4.md.
- Blender SOLO por la cola: bash 03_blender/_rev/blender_cola.sh --python <script> [-- args]; max 2 Blender tuyos a la vez; nunca guardes sobre 03_blender/porto_corsa.blend ni _rev/escena_rev.blend salvo via promover.sh.
- NO publiques nada (ni GitHub ni releases), NO commits, NO instalaciones. Descargas: solo si son imprescindibles y CC0/MIT, anotadas. Write/Edit para codigo con backslashes (los heredocs de bash se comen las barras). Rutas absolutas en bash (el cd al inicio de un comando compuesto a veces no se aplica).
- Cada afirmacion con cifra o fichero que la demuestre. Entrega final (<= 40 lineas): hecho, ficheros, pruebas con cifras, pendiente honesto.
`
const RES = { type: 'object', properties: { ok: { type: 'boolean' }, ficheros: { type: 'array', items: { type: 'string' } }, resumen: { type: 'string' }, pendiente: { type: 'string' } }, required: ['ok', 'ficheros', 'resumen', 'pendiente'] }
const VER = { type: 'object', properties: { aprobado: { type: 'boolean' }, problemas: { type: 'array', items: { type: 'string' } }, informe: { type: 'string' } }, required: ['aprobado', 'problemas', 'informe'] }

const cierre = () => agent(`Eres el INTEGRADOR de la fase F1 y la CIERRAS. Ficheros tuyos: integrar_escena.py, preparar_geometria.py, asentar_objetos.py, revisar_*.py, eliminar_sumergidos.py, _rev/nada_en_pista.py, _rev/pipeline_escena.sh, _rev/linea_base.json, _rev/PROMOCIONES.md, RONDA15_PLAN.md (registro); y, SOLO para la decision 14, las lineas de color de assets/vegetacion_kit_v2.py (MAT_VEG_cipres_b, MAT_VEG_retama) y de construir_pista.py (MAT_fondo_marino), siempre via paleta.py.
TAREA:
1) Decision 14: los 3 literales a paleta (cipres_pino_oscuro, salvia, arena/mar_orilla). py_compile + test del kit de vegetacion por la cola.
2) Comprueba que el filtro de pendiente de zona_casino (jardines en cantiles) esta activo en integrar_escena.py (lo anadiste en r4 pero no llego a la candidata).
3) Regeneracion UNICA: bash ${B3}/_rev/pipeline_escena.sh ${B3}/_rev/logs_f1_final (run_in_background y espera; comprueba el eco final 'PIPELINE rc=0').
4) Puerta: python ${B3}/_rev/puerta_calidad.py (puerta_README.md) -> puerta.json. Si da ok:true, bien. Si el UNICO motivo es arboles_quitados <= 5 en cantiles/laderas con terreno identico a la base, aplica la decision 13: tolerancia escrita en linea_base.json (lista exacta de objetos y motivo) y en PROMOCIONES.md, y vuelve a ejecutar la puerta hasta ok:true. Cualquier otro motivo: NO promuevas y explica.
5) A/B corto contra la base y contra renders/ab/f1_r4 (capturas_ab.py con renders/ab/_base_antes/camaras.json, NUNCA --guardar-camaras): tomas 49-54, 36, 50, 56, 58, 59, 62 en normal y --modo-ac -> renders/ab/f1_final/; montaje + medir_capturas. Criterio: 0 regresiones de piloto contra la base y nada peor que r4 salvo diferencias de sorteo documentadas. Mira las hojas (Read).
6) Promocion: bash ${B3}/_rev/promover.sh "F1 cierre (bloques 3, 2.1, 2.2, 1.1-1.2, 7.1, 4.1)" "renders/ab/f1_final" "director r4 + decision 13/14". Anota 4 lineas 'fase visual F1 cierre:' en el registro. Devuelve el md5 de la escena promovida (_rev/escena_rev.blend) y de _rev/geometria_rev.json.
${COMUN}`, { label: 'cierre:f1', phase: 'Cierre F1', schema: RES })

const TAREA_EXPORT = `Eres el PROPIETARIO del EXPORT (04_export) para el zip v1.2 "paleta y fondo" (decision 16: 04_export SE ABRE). Ficheros tuyos: ${B4}/kn5_writer_opt.py, exportar_ac.py, color_ac.py, cierre_ac.py, revisar_fisica_ac.py, empaquetar.py, hacer_zip.sh, INSTRUCCIONES.md, extension/ext_config.ini, y nuevos en 04_export/ (p.ej. kn5_vista.py, ensayo_f_pueblo.py). kn5_check.py solo para ANADIR comprobaciones. No toques 03_blender salvo leer (y _rev/ para tus salidas de prueba en ${B4}/_v12_dev/).
CONTEXTO IMPRESCINDIBLE: ${FV}/PETICIONES_04_EXPORT.md (P1-P10, X3, X7), ${FV}/PARCHES_F1_mascara.md (nota A5/P10: el TERRENO tiene ahora uv_layers[0] = UV planar 0..1 sobre toda la rejilla para la mascara 2048; con el writer de hoy el tile de 512 de MAT_terreno se estiraria sobre ~2 km), ${FV}/web_multilayer_vao_erosion.md y web_treefx.md (shaders y samplers verificados), ${B3}/_rev/kn5_ensayo.py (sabe escribir ksMultilayer_fresnel_nm, ksPerPixelAT, PNG 2048), ${B4}/kn5_refs/ (actools, kn5-converter: listas de shaders/samplers de Kunos), 03_blender/mascara_terreno.py (texturas/terreno_base.png = color de paleta por texel x AO, 2048, 1 m/texel; terreno_mask.png RGBA) y la decision 10 (no tocar la luz del proxy AC). El amigo AUN no ha mandado las fotos de las 5 mini-pistas: no sabemos si su AC carga ksMultilayer ni PNG 2048 con mipmaps.
OBJETIVO: que en Assetto Corsa (sin CSP y con CSP) el circuito se vea como el modo AC de las capturas (renders/ab/f1_r4/despues_ac/), sin romper nada de lo validado en v1.1 (fisica 0 fallos, kn5_check 8/8, color_ac).
TAREA (desarrollo sobre la candidata r4: ${B3}/_rev/escena_candidata.blend + geometria_candidata.json, COPIADAS a ${B4}/_v12_dev/; el export final sobre la escena promovida lo hara otra etapa con tu codigo):
1) TERRENO en el KN5 con el camino MAS SEGURO que se vea bien: elige y justifica con pruebas entre (a) ksPerPixel con txDiffuse = terreno_base.png 2048 sobre la UV 0..1 (bordes suaves por texel, AO, paleta; sin detalle cercano), (b) (a) + detalle con ksPerPixelMultiMap/txDetail SOLO si el nombre del shader, sus samplers y propiedades (detailUVMultiplier, useDetail...) estan VERIFICADOS en kn5_refs/actools o en pistas Kunos documentadas, (c) reparto por cara en 4-6 materiales con tiles y UV de mundo en metros (detalle, pero bordes en sierra de 2-4 m). El multicapa (ksMultilayer_fresnel_nm) NO en v1.2 (pendiente de la foto del ensayo A). MAT_terreno_roca/separar_roca_terreno de color_ac debe quedar coherente con la opcion elegida (sin duplicar ni contradecir). Mipmaps: si el PNG 2048 necesita mipmaps propios para no parpadear de lejos, escribelo como DDS con mipmaps (formato verificado en kn5_ensayo.py ensayo D) o explica por que no hace falta.
2) Resto de materiales nuevos de F1 (MAT_cesped, MAT_HORIZ_*, MAT_fondo_marino, caliza_grande_d, tiles CC0 recoloreados): que el writer los exporte con sus props ac_* por defecto = comportamiento actual; HORIZ_ sin sombra (P6); TEX_MAX/TEX_SIZE segun P2 si cabe en el presupuesto (texturas del KN5 <= 80 MB, KN5 <= 450 MB). color_ac: si las medidas de objetivos caducan por el cambio de materiales, que caiga al modelo albedo x luz sin romperse (verificalo con prueba_color_ac.py; no re-midas todo).
3) kn5_vista.py (NUEVO, bpy por la cola): lee un KN5 (formato de kn5_check.py; puedes partir de 04_export/_fisica_rev2/rev2_kn5_a_blend.py, que solo lee geometria) con UV, texturas embebidas, materiales (shader, ksAmbient/ksDiffuse, isRenderable, castShadows) y monta una escena Blender que imita AC sin CSP lo mejor posible (sol + ambiente con los pesos ksAmbient/ksDiffuse del shader, sin GI, sombras solo de lo que castShadows=1), y renderiza con las camaras de ${B3}/renders/ab/_base_antes/camaras.json (convierte coordenadas) las tomas 01, 49-54, 56, 59 -> imagenes "como AC" leidas DEL PROPIO KN5. Es la prueba de verdad del writer.
4) Fisica: exportar_ac.py (con cierre_ac) sobre la candidata + revisar_fisica_ac.py: los mismos 0 fallos que v1.1 (huecos, barreras falsas, garajes, atajos, escapes, caidas en escapatoria, invisibles sobre visible). El terreno ha cambiado (bermas, banda de 2 m, roca): si el cierre o el inspector fallan, corrigelo en cierre_ac/revisar_fisica_ac.
5) Mini-pista F (decision del usuario: validar la paleta del pueblo junto al puerto con Pure): ensayo_f_pueblo.py -> pista minima content/tracks/ensayo_f_pueblo/ con SOLO los objetos del pueblo junto al puerto y su tramo de pista (bbox alrededor de s 650-1000 + puerto; elige el bbox con las camaras 50/40/06), con 1ROAD_ para conducir, AC_START_0/AC_PIT_0/AC_HOTLAP_START_0/AC_TIME_* como en kn5_ensayo, muro de cierre alrededor, ui_track.json, surfaces.ini, map.png; LEEME de 6 lineas para el amigo (entrar, poner Pure, hora 17:00-18:00, fotos de las fachadas desde el coche). kn5_check 8/8 (o explica por que una comprobacion no aplica a una pista minima).
6) hacer_zip.sh: parametrizable para v1.2 (escena de origen por env/arg; por defecto la escena promovida copiada a 04_export/_zip_src/escena_v12.blend + geometria_v12.json), version 1.2 en ui_track.json, INSTRUCCIONES.md con una seccion "Novedades v1.2" en lenguaje llano (paleta mediterranea, terreno por zonas, horizonte, tierra tallada) y el aviso de que con CSP se ve mejor; el zip incluye tambien la mini-pista F (o va como zip aparte ensayo_f_pueblo.zip: decide y documenta).
NO ejecutes todavia la cadena final sobre la escena promovida: entrega el codigo probado sobre la candidata r4, con las imagenes de kn5_vista de la candidata y el informe de fisica.`

const exportDev = () => agent(`${TAREA_EXPORT}
${COMUN}`, { label: 'export:dev', phase: 'Export dev', schema: RES })

const exportFinal = (cier, dev) => agent(`Eres el PROPIETARIO del EXPORT y ejecutas la CADENA FINAL del zip v1.2 sobre la escena PROMOVIDA de F1.
CIERRE DE F1: ${JSON.stringify(cier).slice(0, 2500)}
TU ENTREGA DE DESARROLLO: ${JSON.stringify(dev).slice(0, 3500)}
TAREA: 1) comprueba que _rev/escena_rev.blend es la promovida (md5 del cierre) y copiala con geometria_rev.json a ${B4}/_zip_src/escena_v12.blend / geometria_v12.json; 2) bash ${B4}/hacer_zip.sh con esa escena (logs en ${B4}/_zip_logs_v12/): export -> kn5 -> kn5_check -> revisar_fisica_ac -> empaquetar; el zip.lock lo crea hacer_zip.sh; 3) kn5_vista.py sobre el KN5 final: tomas 01, 49-54, 56, 59 -> ${B3}/renders/ab/v12_como_ac/ y una hoja comparando "modo AC de Blender (renders/ab/f1_final/despues_ac)" vs "como AC leido del KN5"; mira las imagenes (Read) y describe diferencias; 4) mini-pista F final; 5) presupuesto: KN5 <= 450 MB, texturas <= 80 MB, tris, zip <= 250 MB; 6) NO publiques. Si algo falla, arreglalo en tus ficheros y repite (max 3 intentos).
${TAREA_EXPORT.split('TAREA (desarrollo')[0]}
${COMUN}`, { label: 'export:final', phase: 'Export final', schema: RES })

const verificar = (fin, n) => agent(`Eres el VERIFICADOR INDEPENDIENTE del zip v1.2 de Porto Corsa (intento ${n}). Intenta REFUTAR que este listo para el amigo.
ENTREGA DEL EXPORT: ${JSON.stringify(fin).slice(0, 5000)}
Comprueba de verdad (ejecuta): python 04_export/kn5_check.py sobre el KN5 del paquete (8/8); abre el zip y revisa contenido (kn5, data/surfaces.ini con DIRT 0.98, ui_track.json version 1.2, extension/ext_config.ini, ai/fast_lane.ai, INSTRUCCIONES.md con novedades v1.2, mini-pista F); el informe de revisar_fisica_ac del export final (0 en huecos, barreras falsas, garajes, atajos, escapes, caidas, invisibles sobre visible; compara con 04_export/informe_fisica_final.json de v1.1); las imagenes de kn5_vista (renders/ab/v12_como_ac/): mira TODAS con Read: textura del terreno estirada o pixelada, materiales blancos/negros/rosa, objetos que faltan, horizonte, mar, casas con la paleta v2; ejecuta tu mismo kn5_vista sobre 2 tomas para reproducirlas; el TERRENO en el KN5: shader, samplers, tamano y formato de su textura, UV (rango y continuidad: lee la malla del KN5 con un script tuyo); presupuestos; que kn5_writer_opt con COLOR_AC=0 sigue funcionando; que la mini-pista F pasa kn5_check y tiene AC_START/PIT/TIME. Clasifica REAL / MENOR / COSMETICO con la orden que lo demuestra; aprobado solo sin REAL. Escribe ${B4}/_zip_logs_v12/verificacion_${n}.md. No modificas nada del proyecto.
${COMUN}`, { label: `verificar:v12:${n}`, phase: 'Verificar', schema: VER, effort: 'high' })

const corregir = (fin, ver) => agent(`Eres el PROPIETARIO del EXPORT y CORRIGES lo que el verificador encontro en el zip v1.2. Tu entrega: ${JSON.stringify(fin).slice(0, 3000)}
PROBLEMAS: ${ver.problemas.map((p, i) => (i + 1) + '. ' + p).join('\n')}
Informe: ${ver.informe.slice(0, 3000)}
Arregla todos los REAL (y los MENOR que puedas), repite la cadena final (hacer_zip.sh sobre 04_export/_zip_src/escena_v12.blend) y las vistas kn5_vista. NO publiques.
${TAREA_EXPORT.split('TAREA (desarrollo')[0]}
${COMUN}`, { label: 'export:corregir', phase: 'Verificar', schema: RES })

log('Cierre de F1 y desarrollo del export en paralelo')
const [cier, dev] = await parallel([cierre, exportDev])
if (!cier || !cier.ok) { log('el cierre de F1 no promovio: se detiene antes del export final'); return { cierre: cier, dev, final: null } }
if (!dev) { log('el desarrollo del export no entrego'); return { cierre: cier, dev: null, final: null } }
let fin = await exportFinal(cier, dev)
let ver = fin ? await verificar(fin, 1) : null
if (ver && !ver.aprobado && fin) {
  const fix = await corregir(fin, ver)
  fin = fix || fin
  ver = await verificar(fin, 2)
}
return { cierre: { ok: cier.ok, resumen: cier.resumen.slice(0, 1500), pendiente: cier.pendiente.slice(0, 600) }, dev: { ok: dev.ok, pendiente: dev.pendiente.slice(0, 600) }, final: fin ? { ok: fin.ok, resumen: fin.resumen.slice(0, 2500), pendiente: fin.pendiente.slice(0, 800) } : null, verificacion: ver }