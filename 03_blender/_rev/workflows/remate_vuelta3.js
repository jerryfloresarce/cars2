export const meta = {
  name: 'ronda15-remate-vuelta3',
  description: 'Continuacion del ciclo: arreglos de la vuelta 3 (77 hallazgos confirmados) + remate (muro del pit dentro de la recta, nada encima de la pista), escena final, capturas y director de arte',
  phases: [
    { title: 'Arreglar', detail: 'un equipo por grupo de ficheros' },
    { title: 'Capturas', detail: 'escena final, capturas y director de arte' },
  ],
}
const RAIZ = 'E:/Escritorio/claude-pc/arnau-aseto-corsa'
const BLENDER = 'bash E:/Escritorio/claude-pc/arnau-aseto-corsa/03_blender/_rev/blender_cola.sh --python'
const COMUN = `Proyecto: ${RAIZ} = circuito Porto Corsa (Cars 2) para Assetto Corsa, generado 100 % por codigo con Blender 5.1 (Python del sistema 3.12 con numpy/scipy/shapely/matplotlib/PIL; Blender NO tiene shapely). Idioma del codigo y comentarios: espanol sin tildes.
LEE PRIMERO 03_blender/RONDA15_PLAN.md entero (al principio: lo que pidio el usuario, "piensa como un arquitecto de Cars, sin fallos"; al final: estado actual y REGISTRO DE ARREGLOS) y 03_blender/urbanismo_spec.json.
PETICION DEL USUARIO (resumen fiel): montana REAL con la pista tallada en la ladera (salida -> tunel -> tecnica -> tierra SUBIENDO, luego bajada, subida al casino, y desde la rotonda de la palmera bajada a tope hasta la meta); nada sin sentido; nada flotando ni enterrado (arboles, casas, props); casas que NO pisan calles, ni roca, ni muros delante de ventanas; rampas que no atraviesan casas; caminos distinguibles de la pista, bien hechos, con destino y con VALLAS donde tocan la pista; ambiente italiano/Cars; roca del lazo con la pista PEGADA a la roca y completa por todos lados; penon del casino con una carretera de BAJADA visible; McLaren de piedra integrado en la montana (no suelto); mini ciudad funcional (un coche podria ir a todos los sitios); la rotonda Loews se queda EXACTAMENTE como esta (solo sin hundirse).
Blender: lanza Blender SIEMPRE y SOLO con ${BLENDER} <script> [-- args]  (es una COLA: como mucho 6 Blender a la vez en todo el equipo; cada Blender con la escena entera usa ~5 GB y 10 a la vez colgaron Windows; NUNCA llames a blender.exe directamente, tampoco para consultas). Si esperas turno veras '[cola] esperado N s'. Agrupa el trabajo para abrir Blender pocas veces (muchas vistas por llamada; consultas en un solo script). timeout 15 min.
Escritura de ficheros: trozos de <= 180 lineas; para cambios en ficheros existentes usa Edit. Sin bpy.ops salvo abrir/guardar/render.`

const TRAMOS = [
  { key: 'A_meta_puerto', desc: 'recta de meta y retorno final (s 4900..5200 y 0..200): parrilla, portico, pit lane y 20 boxes con tribuna, paddock, subida y aparcamiento del hotel, tribunas, puerto (dique, pantalanes, faro), yates VIP, carretera/espigon del puerto.' },
  { key: 'B_tunel_mclaren', desc: 's 150..680: subida desde la meta, McLaren de piedra (TUNEL_acantilado) con el tunel por sus ruedas delanteras (s 402-542), su penon de la zaga en el mar y el afloramiento del morro, portales e interior del tunel, como se ve el coche desde la pista y desde lejos (tiene que reconocerse un McLaren integrado en la montana).' },
  { key: 'C_tecnica_pueblo_bajo', desc: 's 600..1300: seccion tecnica que sube por el pueblo bajo (pueblo_subida_*), plaza del ayuntamiento y mercado (s ~1130-1175, lado -1), acceso con valla, sendero de la ERMITA, edicolas, union del pueblo con el McLaren.' },
  { key: 'D_pueblo_alto', desc: 's 1250..1700: pueblo alto (pueblo_alto_*), salida hacia la tierra, cruces con otros ramales.' },
  { key: 'E_tierra', desc: 's 1650..2480: seccion de TIERRA con el lazo y la cima (s ~1900), pacas, camaras-grua, helicoptero, sendero de la CIMA con ermita y cipreses, arboles flotando (queja del usuario), la montana alrededor.' },
  { key: 'F_bajada_recta', desc: 's 2450..3200: bajada hacia el puerto (bajada_ladera), recta 30-31 que sube al casino, paseo-mirador con arcadas y palazzo-parking (s 2990-3150), entrada al pit.' },
  { key: 'G_casino_rotonda', desc: 's 3150..3750: sector del casino en zigzag (casino_*), cresta 36-38, PENON DEL CASINO con su carretera de bajada visible y la cala o plazoleta al pie, el casino arriba, bajada RECTA a la rotonda (desde la camara-grua amarilla no se ve lo que hay tras la cresta), rotonda Loews (no tocar su forma), espolon y camino del pie.' },
  { key: 'H_viaducto_lazo', desc: 's 3700..4500: viaducto de arcos, U de la roca del lazo (curvas 42-44) con la calzada pegada a la roca, terrazas y casas, cumbre con plaza y campanile, cala con muelle y barcas, puertas con valla en el parapeto.' },
  { key: 'I_retorno', desc: 's 4450..4950: viaducto bajo sobre el mar, chicane 46-49, llegada a la meta, yates, costa.' },
  { key: 'J_global', desc: 'VISTA GLOBAL de la isla: 8 aereas desde los puntos cardinales (600-1200 m, 250-500 m de alto), 4 cenitales por cuadrantes y 6 a ras del mar: UNA montana natural con el circuito subiendo y bajando por ella, costa, bordes del mapa, cumbres, rocas, estilo Cars 2 (Riviera italiana).' },
]

const GRUPOS = [
  { key: 'integrador', ficheros: '03_blender/integrar_escena.py, 03_blender/urbanismo_escena.py, 03_blender/renderizar_capturas.py, 04_export/exportar_ac.py', test: 'python -m py_compile de cada fichero tocado; la escena entera la genera la siguiente vuelta' },
  { key: 'pueblo_terreno', ficheros: '03_blender/urbanismo.py, 03_blender/terreno_montana.py, 03_blender/preparar_geometria.py, 03_blender/urbanismo_spec.json', test: "'python 03_blender/preparar_geometria.py' y 'python 03_blender/urbanismo.py' sin errores y con la QA de urbanismo a 0 fallos y >= 190 casas" },
  { key: 'pista', ficheros: '03_blender/construir_pista.py', test: 'construir_pista.py corre sin errores (puedes ejecutarlo: escribe porto_corsa.blend, que la siguiente vuelta regenera)' },
  { key: 'roca_lazo', ficheros: '03_blender/assets/roca_lazo.py (y su test)', test: 'assets/test_roca_lazo.py con todos sus checks a 0 y previews mirados' },
  { key: 'casino', ficheros: '03_blender/assets/roca_casino.py, 03_blender/assets/test_roca_casino.py, 03_blender/assets/casino_v2.py', test: 'assets/test_roca_casino.py con datos iguales a integrar_escena.zona_casino y previews mirados' },
  { key: 'mclaren', ficheros: '03_blender/assets/montana_mclaren.py, 03_blender/assets/encaje_mclaren.py', test: 'assets/test_montana_mclaren.py (malla cerrada, no-manifold 0) y previews' },
  { key: 'assets_varios', ficheros: 'los demas 03_blender/assets/*.py (casas_kit_v2, caminos_kit, vegetacion_kit_v2, italiano_kit, pit_kit_v2, yates_kit, viaducto_curvo_v2, edificios_civicos_v2, mirador_kit, calle_kit, carrera_kit_v2, puerto_kit...)', test: 'el test_<modulo>.py del kit tocado y sus previews' },
  { key: 'inspectores', ficheros: '03_blender/asentar_objetos.py, 03_blender/revisar_*.py, 03_blender/eliminar_sumergidos.py', test: 'py_compile; los ejecuta la siguiente vuelta' },
]
function grupoDe(h) {
  const f = ((h.fichero || '') + ' ' + (h.arreglo || '') + ' ' + (h.causa || '')).toLowerCase()
  if (/roca_lazo/.test(f)) return 'roca_lazo'
  if (/roca_casino|casino_v2/.test(f)) return 'casino'
  if (/montana_mclaren|encaje_mclaren/.test(f)) return 'mclaren'
  if (/urbanismo\.py|terreno_montana|preparar_geometria|urbanismo_spec/.test(f)) return 'pueblo_terreno'
  if (/construir_pista/.test(f)) return 'pista'
  if (/asentar_objetos|revisar_|eliminar_sumergidos/.test(f)) return 'inspectores'
  if (/integrar_escena|urbanismo_escena|renderizar_capturas|exportar_ac/.test(f)) return 'integrador'
  if (/assets\//.test(f)) return 'assets_varios'
  return 'integrador'
}

const ESCENA = { type: 'object', properties: { ok: { type: 'boolean' }, auditoria: { type: 'string' }, resumen: { type: 'string' } }, required: ['ok', 'resumen'] }
const HALL = { type: 'object', properties: {
  tramo: { type: 'string' }, vistas: { type: 'number' },
  hallazgos: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, severidad: { type: 'string', enum: ['alta', 'media', 'baja'] }, tipo: { type: 'string' }, descripcion: { type: 'string' },
    s: { type: 'number' }, x: { type: 'number' }, y: { type: 'number' }, z: { type: 'number' }, objetos: { type: 'array', items: { type: 'string' } },
    evidencia: { type: 'array', items: { type: 'string' } }, causa_probable: { type: 'string' }, fichero: { type: 'string' }, arreglo_propuesto: { type: 'string' },
  }, required: ['id', 'severidad', 'descripcion', 'evidencia', 'arreglo_propuesto'] } },
  positivos: { type: 'array', items: { type: 'string' } } }, required: ['tramo', 'hallazgos', 'positivos'] }
const VERIF = { type: 'object', properties: {
  tramo: { type: 'string' },
  hallazgos: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, veredicto: { type: 'string', enum: ['confirmado', 'refutado', 'parcial'] }, severidad: { type: 'string', enum: ['alta', 'media', 'baja'] },
    descripcion: { type: 'string' }, s: { type: 'number' }, x: { type: 'number' }, y: { type: 'number' }, objetos: { type: 'array', items: { type: 'string' } },
    evidencia: { type: 'array', items: { type: 'string' } }, causa: { type: 'string' }, fichero: { type: 'string' }, arreglo: { type: 'string' }, motivo: { type: 'string' },
  }, required: ['id', 'veredicto', 'severidad', 'descripcion', 'fichero', 'arreglo', 'motivo'] } } }, required: ['tramo', 'hallazgos'] }
const FIX = { type: 'object', properties: {
  grupo: { type: 'string' }, ok: { type: 'boolean' },
  arreglados: { type: 'array', items: { type: 'string' } }, no_arreglados: { type: 'array', items: { type: 'string' } },
  ficheros: { type: 'array', items: { type: 'string' } }, resumen: { type: 'string' } }, required: ['grupo', 'ok', 'arreglados', 'no_arreglados', 'resumen'] }


const CUENTAS = { pueblo_terreno: 34, integrador: 22, pista: 6, mclaren: 5, casino: 4, inspectores: 4, roca_lazo: 2 }
const EXTRA = {
  integrador: `TAREA ESPECIAL DEL REMATE (prioridad alta, peticion del usuario: "es super importante que no haya NADA encima del circuito"): (1) PIT_muro (zona_pit en integrar_escena.py): el muro de boxes ocupa lat 7.0-9.3 m del eje y la recta de meta mide 16 m (borde a 8.0): invade 1 m de calzada en s 5066-90. Entre el borde de la pista y el borde interior del pit lane (13.5 - w_pit/2 = 9.75) solo hay 1.75 m: estrecha el muro (escala local en su eje transversal o parametro de pit_kit si lo hay) y colocalo entre borde+0.3 y pit-0.15, sin que ninguna pieza (podio, valla de captura, pupitres, sombrillas) toque el asfalto ni el pit lane. (2) CARRERA_muro_valla.071/.072 y su zocalo en s 4936 (final del viaducto) asoman en el borde del asfalto: apartalos >= 0.3 m. (3) 1WALL/CAMINO_muro.108 (muro de la subida al hotel) se mete 1.5 m dentro del pit lane en s 5048-5062: que el muro de la subida no entre nunca en el pit lane (+0.5 m). (4) MIRADOR_paseo en s 2990 roza el borde: comprueba. Verifica con: bash ${RAIZ}/03_blender/_rev/blender_cola.sh --python ${RAIZ}/03_blender/_rev/nada_en_pista.py -- <blend> <geometria> <salida.json> sobre una escena que generes en una COPIA (no sobre porto_corsa.blend si otro equipo la esta usando; si necesitas la escena entera, genera con pipeline_escena.sh al final, despues de tus cambios) y explica en el resumen lo que queda (solo deben quedar elementos aereos > 4 m como farolas y guirnaldas).`,
  roca_lazo: `TAREA ESPECIAL DEL REMATE: PENON_puente_vallas y PENON_puente_plaza_rellano en s ~4548 asoman sobre el borde del tablero del viaducto (nada_en_pista.py los marca): retranquealos >= 0.3 m del asfalto.`,
}
log('vuelta 3: 77 hallazgos confirmados en 7 grupos (ficheros 03_blender/_rev/r3_grupo_<grupo>.json)')
const fixes = await parallel(GRUPOS.filter(g => CUENTAS[g.key] || EXTRA[g.key]).map(g => () =>
  agent(COMUN + `\nERES EL EQUIPO DE ARREGLO '${g.key}' (vuelta 3, la ultima). Solo puedes editar: ${g.ficheros}. Otros equipos editan otros ficheros a la vez (y un equipo de FISICA del juego trabaja en 04_export/exportar_ac.py, cierre_ac.py y kn5_writer_opt.py: NO toques esos tres). NO toques nada fuera de tu lista (si un arreglo necesita otro fichero, ponlo en no_arreglados con la explicacion exacta). NO ejecutes el pipeline completo ni guardes 03_blender/porto_corsa.blend salvo que tu prueba lo requiera. Antes de editar, lee la funcion entera; manten contratos y garantias (RONDA15_PLAN.md, urbanismo_spec.json) y lo que los revisores marcaron como positivo (lista 'positivos' del fichero de hallazgos de abajo).\n` +
    (EXTRA[g.key] ? EXTRA[g.key] + '\n' : '') +
    `HALLAZGOS CONFIRMADOS asignados a tu grupo: LEE ${RAIZ}/03_blender/_rev/r3_grupo_${g.key}.json (${CUENTAS[g.key] || 0} hallazgos con descripcion, objetos, evidencia PNG, causa, fichero y arreglo; arregla de mas grave a menos; los 'baja' solo si son baratos y seguros). Si ese fichero no existe, solo tienes la tarea especial.\nPrueba: ${g.test}. Anade 1-3 lineas por arreglo al final de 03_blender/RONDA15_PLAN.md (REGISTRO DE ARREGLOS, empieza cada linea con 'v3 ${g.key}:'). Devuelve grupo, ok, arreglados (ids), no_arreglados (id + motivo), ficheros y resumen.`,
    { label: `r3-arreglar:${g.key}`, phase: 'Arreglar', schema: FIX })))

const escF = await agent(COMUN + `\nFINAL: genera la escena con bash ${RAIZ}/03_blender/_rev/pipeline_escena.sh ${RAIZ}/03_blender/_rev/logs_final (si falla, arregla solo el error de ejecucion evidente en el fichero que lo causa). Comprueba la linea NADA_EN_PISTA (renders/qa/nada_en_pista.json): solo pueden quedar elementos aereos (farolas, guirnaldas a > 4 m); cualquier otra cosa sobre el asfalto o la tierra es un fallo que debes arreglar en su origen y regenerar. Despues renderiza TODAS las capturas: cd ${RAIZ}/03_blender && ${BLENDER} renderizar_capturas.py (deja PNG en 03_blender/renders/capturas; tarda 5-15 min). Devuelve ok, la linea AUDITORIA, la linea NADA_EN_PISTA y la lista de capturas generadas en resumen.`,
  { label: 'final-escena-capturas', phase: 'Capturas', schema: ESCENA })
const dir = escF && escF.ok ? await agent(COMUN + `\nERES EL DIRECTOR DE ARTE FINAL. Mira con Read TODAS las capturas de ${RAIZ}/03_blender/renders/capturas/ (01-54) y juzga, captura por captura, si cumple lo que pidio el usuario. Para cada una: 'ok' o la lista de defectos visibles concretos (que, donde, objeto probable). Termina con un veredicto global y los 10 defectos mas importantes que quedan. No edites nada.`,
  { label: 'final-director', phase: 'Capturas' }) : null
return { arreglos: fixes.filter(Boolean), final: escF, director: dir }
