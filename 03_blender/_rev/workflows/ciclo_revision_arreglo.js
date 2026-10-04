export const meta = {
  name: 'ronda15-ciclo-revision-arreglo',
  description: 'Ciclo automatico hasta 3 vueltas: generar escena -> 10 revisores por tramo -> verificador por tramo -> equipos de arreglo por grupo de ficheros (sin pisarse) -> repetir; al final capturas y revision de director de arte',
  phases: [
    { title: 'Escena', detail: 'genera el circuito completo y congela una copia' },
    { title: 'Revisar', detail: '10 revisores por tramo' },
    { title: 'Verificar', detail: 'verificador independiente por tramo' },
    { title: 'Arreglar', detail: 'un equipo por grupo de ficheros' },
    { title: 'Capturas', detail: 'capturas finales y director de arte' },
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

const EXTRA_R1 = {
  pueblo_terreno: `TAREA ESPECIAL (vuelta 1): (a) aplica en urbanismo.py la clave nueva 'zonas_excluidas' de urbanismo_spec.json (poligono de la huella del McLaren + margen): NADA del plan dentro (calles, enlaces, travesias, rampas, escaleras, muros, solares, plazas, salidas); los trozos de calle que queden se cierran con su enlace/fondo de saco segun las reglas que ya tiene el modulo; hoy el integrador borra 18 casas de pueblo_subida_ladera bajo el morro del McLaren y sus calles quedan metidas bajo la roca. (b) la revision independiente de tu entrega anterior (216 casas, terrazas llenas, fosos, huellas completas; ver la entrega en 03_blender/_rev/pueblo_entrega_previa.json) quedo sin hacer: revisa tu propio trabajo con ojo critico (mapas urbanismo_detalle_*.png) y corrige lo que veas. (c) escaleras del plan que entran 0.0-0.3 m en casas (casa_calle en la auditoria): separalas >= 0.5 m.`,
  casino: `TAREA ESPECIAL (vuelta 1): un agente anterior estaba rematando assets/roca_casino.py y se corto (ultima escritura 17:25). Estado medido en la escena: base z=120 -> meseta z=132 (radio 54), bajada 1020 m con 2 horquillas, pendiente max 11.2 % (el maximo permitido era 11 %). Lee 03_blender/assets/_casino_revision.txt (la revision que rechazo la primera version) y el codigo; ejecuta el test; comprueba y termina TODOS los requisitos: roca natural (nada de parking de 7 plantas), una sola bajada visible <= 11 %, sin voladizos ni quiebros ni quads cruzados, farolas sobre el parapeto, matas apoyadas, 0 casas en roca, roca que llega al terreno/mar en todo el perimetro, meseta llana >= 34 m de radio, cala o plazoleta al pie con su conexion. Mira las vistas del tramo G de los revisores.`,
}

async function vuelta(r, auditoria) {
  const base = `${RAIZ}/03_blender/_rev/r${r}`
  const rev = await pipeline(
    TRAMOS,
    t => agent(COMUN + `\nERES REVISOR DE DETALLE (vuelta ${r}) del tramo ${t.key}: ${t.desc}\nSOLO LECTURA del proyecto: escribe solo en ${base}/${t.key}/. Escena congelada: 03_blender/_rev/escena_rev.blend + _rev/geometria_rev.json + _rev/urbanismo_rev.json. Render (unos 4 s por vista): ${BLENDER} ${RAIZ}/03_blender/_rev/render_vistas.py -- <vistas.json> <carpeta_absoluta>  (lee su docstring: modos piloto, piloto_atras, dron, lateral, cenital o loc/target libres; 20-40 vistas por llamada). Para saber que objeto hay en un sitio escribe tu script de Blender que abra escena_rev.blend SIN guardar. Prefijos -> generador: CASAS_/CAMINO_calle|enlace|travesia|rampa|escalera|muro|union/CALLE_plaza*/plazoleta = urbanismo.py+urbanismo_escena.py; CAMINO_* fuera del pueblo, ITAL_*, CAMINO_valla/cartel = integrar_escena.zona_caminos/zona_edicolas; VEG_/OLI_ = zona_montana/zona_tierra/enriquecer_vegetacion + asentar_objetos.py; CALLE_farola|guirnalda|poste|maceta|toldo = zona_calle; CARRERA_ = zona_meta/zona_vallas; PIT_ = zona_pit + assets/pit_kit_v2.py; PUERTO_ = zona_puerto; YATE_ = zona_yates; TUNEL_acantilado = McLaren (assets/montana_mclaren.py) + zona_tunel; PENON_puente* = assets/roca_lazo.py; PENON_cara/PENON_* = assets/roca_casino.py; CASINO_ = casino_v2.py; LOEWS_ = zona_loews; MIRADOR_ = zona_paseo_mirador; CAMARA_ = zona_camaras; COCHE_ = zona_coches; AYTO_/CAMPANILE_ = zona_pueblo_urbanismo; HOTEL_ = zona_meta; TERRENO/ARCEN_/ACERA_/BORDILLO_/PISTA/PIANOS/GUARDARRAIL/MUROC = construir_pista.py + terreno_montana.py. Auditoria automatica de esta escena: ${auditoria}. Detalle en 03_blender/_rev/urbanismo_informe_rev.json (filtra los de tu tramo por x,y).
LISTA DE CONTROL (evidencia en PNG para todo): 1) flotando/enterrado/atravesado (arbol en casa, casa en calle o roca, muro delante de ventanas, rampa por una casa); 2) caminos sin destino, mal empalmados, sin valla junto a la pista, flotando/hundidos, escalones o pendientes imposibles; 3) terreno: picos o agujeros en asfalto/tunel, hierba asomando en la calzada, paredes de hierba verticales, cortes rectos, costa en escalera, bordes de mapa, montanas no naturales; 4) juego (Assetto Corsa): nada sobre el asfalto, muros/rocas que invadan la calzada, sitios sin barrera donde caerse, saltos bruscos de cota, visibilidad; 5) sentido y ambiente italiano/Cars, escala; 6) positivos (lo que esta bien, para no romperlo). Los materiales/colores son provisionales (la fase de texturas va despues): no los reportes salvo que algo se lea mal.
Genera unas 45 vistas en 2-3 llamadas (piloto en ambos sentidos cada ~40 m, dron cada ~100 m, laterales a los dos lados, cenitales y vistas libres de cerca) y MIRA cada PNG con Read. Por hallazgo: severidad (alta = visible en piloto/dron o rompe el juego), descripcion concreta, s, x, y, z, objetos (consultados), PNG, causa probable, FICHERO responsable y arreglo concreto. No inventes nada que no hayas visto o medido.`,
      { label: `r${r}-revisar:${t.key}`, phase: 'Revisar', schema: HALL }),
    (h, t) => h ? agent(COMUN + `\nERES EL VERIFICADOR INDEPENDIENTE (vuelta ${r}) del tramo ${t.key}: ${t.desc}\nEscena congelada 03_blender/_rev/escena_rev.blend; render con ${RAIZ}/03_blender/_rev/render_vistas.py (docstring); escribe en ${base}/${t.key}/verif/. Hallazgos del revisor:\n${JSON.stringify(h)}\nPara CADA uno: mira sus PNG, genera 1-3 vistas nuevas mas cercanas/otro angulo y mide con un script si hace falta; intenta REFUTARLO (falso positivo, efecto de camara o de materiales provisionales, algo con sentido). Veredicto, severidad ajustada, causa REAL en el codigo (lee la funcion), FICHERO exacto y arreglo concreto y seguro. Anade como hallazgos nuevos (id 'N1', 'N2'...) los fallos graves que el revisor no vio.`,
      { label: `r${r}-verificar:${t.key}`, phase: 'Verificar', schema: VERIF }).then(v => ({ tramo: t.key, h, v })) : null,
  )
  const conf = rev.filter(Boolean).flatMap(x => (x.v ? x.v.hallazgos : []).filter(hh => hh.veredicto !== 'refutado').map(hh => ({ tramo: x.tramo, ...hh })))
  const positivos = rev.filter(Boolean).flatMap(x => x.h ? x.h.positivos.map(p => x.tramo + ': ' + p) : [])
  return { conf, positivos }
}

const historial = []
let auditoria = 'casa_camino 2, casa_calle 5, arbol_calle 2, prop_pista 18 (PIT_muro, conocido), camino_sin_destino 2, casa_enterrada 2, casa_flotante 1 (LOEWS, falso positivo de caja), objeto_salto_grande 1'
for (let r = 1; r <= 3; r++) {
  if (r > 1) {
    const esc = await agent(COMUN + `\nVuelta ${r}: genera la escena completa con: bash ${RAIZ}/03_blender/_rev/pipeline_escena.sh ${RAIZ}/03_blender/_rev/logs_r${r}  (tarda 3-5 min; si falla un paso, lee su log en esa carpeta, arregla SOLO el error de ejecucion evidente en el fichero que lo causa (o, si no es evidente, deshaz el ultimo cambio de ese fichero segun el REGISTRO DE ARREGLOS) y repite). Devuelve ok, la linea AUDITORIA y un resumen de las lineas finales.`,
      { label: `r${r}-escena`, phase: 'Escena', schema: ESCENA })
    if (!esc || !esc.ok) { log('vuelta ' + r + ': la escena no se pudo generar'); break }
    auditoria = esc.auditoria || esc.resumen
  }
  const { conf, positivos } = await vuelta(r, auditoria)
  const graves = conf.filter(h => h.severidad !== 'baja')
  log(`vuelta ${r}: ${conf.length} hallazgos confirmados (${conf.filter(h => h.severidad === 'alta').length} altos, ${conf.filter(h => h.severidad === 'media').length} medios)`)
  historial.push({ vuelta: r, hallazgos: conf, positivos: positivos.slice(0, 60) })
  if (r > 1 && graves.length === 0) break
  const porGrupo = {}
  for (const h of conf) { const g = grupoDe(h); (porGrupo[g] = porGrupo[g] || []).push(h) }
  if (r === 1) { for (const g of Object.keys(EXTRA_R1)) porGrupo[g] = porGrupo[g] || [] }
  const fixes = await parallel(GRUPOS.filter(g => porGrupo[g.key] && (porGrupo[g.key].length || (r === 1 && EXTRA_R1[g.key]))).map(g => () =>
    agent(COMUN + `\nERES EL EQUIPO DE ARREGLO '${g.key}' (vuelta ${r}). Solo puedes editar: ${g.ficheros}. Otros equipos editan otros ficheros a la vez: NO toques nada fuera de tu lista (si un arreglo necesita otro fichero, ponlo en no_arreglados con la explicacion exacta para ese equipo). NO ejecutes el pipeline completo ni abras/guardes 03_blender/porto_corsa.blend salvo que tu prueba lo requiera (la siguiente vuelta lo regenera). Antes de editar, lee la funcion entera; manten contratos y garantias (RONDA15_PLAN.md, urbanismo_spec.json) y lo que los revisores marcaron como positivo:\n${positivos.slice(0, 40).join('\n')}\n` +
      (r === 1 && EXTRA_R1[g.key] ? EXTRA_R1[g.key] + '\n' : '') +
      `HALLAZGOS CONFIRMADOS asignados a tu grupo (arregla de mas grave a menos; los 'baja' solo si son baratos y seguros):\n${JSON.stringify(porGrupo[g.key] || [])}\nPrueba: ${g.test}. Anade 1-3 lineas por arreglo al final de 03_blender/RONDA15_PLAN.md (seccion REGISTRO DE ARREGLOS, empieza cada linea con 'v${r} ${g.key}:'). Devuelve grupo, ok, arreglados (ids), no_arreglados (id + motivo), ficheros y resumen.`,
      { label: `r${r}-arreglar:${g.key}`, phase: 'Arreglar', schema: FIX })))
  historial[historial.length - 1].arreglos = fixes.filter(Boolean)
}

// final: escena + capturas + director de arte
const escF = await agent(COMUN + `\nFINAL: genera la escena con bash ${RAIZ}/03_blender/_rev/pipeline_escena.sh ${RAIZ}/03_blender/_rev/logs_final (si falla, arregla solo el error de ejecucion evidente). Despues renderiza TODAS las capturas de revision: cd ${RAIZ}/03_blender && ${BLENDER} renderizar_capturas.py (deja PNG en 03_blender/renders/capturas; tarda 5-15 min; ejecutalo en segundo plano si tu herramienta lo permite y espera a que termine). Devuelve ok, la linea AUDITORIA y la lista de capturas generadas en resumen.`,
  { label: 'final-escena-capturas', phase: 'Capturas', schema: ESCENA })
const dir = escF && escF.ok ? await agent(COMUN + `\nERES EL DIRECTOR DE ARTE FINAL. Mira con Read TODAS las capturas de ${RAIZ}/03_blender/renders/capturas/ (las 01-54) y juzga, captura por captura, si cumple lo que pidio el usuario. Para cada una: 'ok' o la lista de defectos visibles concretos (que, donde en la imagen, objeto probable). Termina con un veredicto global y los 10 defectos mas importantes que quedan. No edites nada.`,
  { label: 'final-director', phase: 'Capturas' }) : null
return { historial, final: escF, director: dir }