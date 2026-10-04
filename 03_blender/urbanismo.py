"""urbanismo.py - Trazado urbano por terrazas del pueblo de Porto Corsa (ronda 15, T2, v2).

Python del SISTEMA (3.12: numpy, scipy, shapely, matplotlib). NO usa bpy.
Lee  : 03_blender/geometria_3d.json (o --geom <ruta>): muestras de pista + rejilla 'terreno' de T1
       + 03_blender/urbanismo_spec.json (contrato)
Escribe: 03_blender/urbanismo.json + renders/qa/urbanismo_<sector>.png y urbanismo_detalle_<sector>.png
Uso  : python urbanismo.py [--geom ruta.json] [--salida ruta.json] [--sin-qa]

CONVENCIONES (verificadas en RONDA15_PLAN.md)
  * Muestras de pista cada 2 m: x,y,z,nx,ny,w,lat. n = normal IZQUIERDA de la marcha.
    pos(s, lado, u) = p(s) + lado * n(s) * (w(s)/2 + u)   (u medido desde el BORDE del asfalto)
    lado +1 = izquierda = mar ; lado -1 = derecha = ladera.
  * Seccion transversal = la del contrato (urbanismo_spec.json) y la que talla terreno_montana.py:
    terraza k = banda u in [21k, 21(k+1)) LLANA a cota Z(s)+h_k, h_k = +0.5+6k (ladera: SUBE) o -0.5-6k
    (mar: BAJA); el sentido lo da sentido_terrazas() (id '_mar' baja, el resto sube; NO el lado: en pueblo_alto el
    macizo esta en +1). MURO de contencion en u = 21(k+1). Dentro de la banda, por contrato 15b: bordillo 0..1.5,
    calle u_local 1.5..6 (eje 3.75), fachada 7, solar hasta 18 (fondo <= 11), patio 18..21; la rampa del muro de
    T1 ocupa u_local 18.5..21 (lado de la terraza k) y la terraza k+1 es llana desde 21(k+1) exactamente.
  * TERRENO REAL (novedad v2): se lee la rejilla 'terreno' (bilineal, cell 4 m) y se compara con la
    regla Z(s_sector)+h_k (s_sector = muestra mas cercana DEL SECTOR; T1 mezcla Z en s, asi que en las
    esquinas interiores la regla y el terreno difieren un poco). Con cell=4 la rampa del muro (18.5..21 del
    lado de la terraza k) se difumina ~2 m a cada lado: cada terraza MIDE su banda
    llana real (desvio mediano del terreno por u_local) y, solo si hace falta, desplaza hacia fuera el
    eje de la calle (mar: la calle al pie del muro se enterraria 0.5-1 m en el talud -> queda a ~2 m
    del muro), la fachada (= borde de la calle + 1) y el fondo maximo (trasera sobre terreno llano).
    Despues, TODO se comprueba contra la rejilla: calles/travesias/enlaces se CORTAN donde el terreno
    bajo el eje queda > 0.6 m por encima o > 1.2 m por debajo; los solares se RECHAZAN si alguna
    esquina queda > 1.0 m enterrada o > 0.5 m flotante (T6 informa a +1.2/-0.6); los muros se cortan
    donde el terreno sale de [z_base-0.6, z_top+0.3]; rampas, escaleras y plataformas se descartan
    si el terreno asoma > 0.5 m sobre su superficie. En los extremos de sector (fundido de T1) y en
    los tramos que T1 no aterraza no se coloca nada.
  * COSTURAS: donde el terreno 'por muestra mas cercana' tiene un escalon (bisectriz de una curva
    interior cerrada, fondo de horquilla) la calle se corta; si los dos extremos quedan enfrentados a
    <= 10 m se UNEN con una cuesta de <= 50 % (y se exportan en qa.costuras para que T1 funda Z).
  * NADA SIN DESTINO: la via de servicio lleva un enlace a la pista (12 m + valla) en CADA extremo de
    cada trozo; una travesia de la terraza k < n-1 solo se construye si tiene rampa o escalera a k+1;
    la rampa = pendiente RECTA entre sus dos cotas de empalme (pie = travesia de k, meseta = calle de
    k+1) + codo a nivel que cruza el talud del muro; alcanzabilidad de abajo arriba: una calle de k >= 1
    que ninguna rampa/escalera une a un trozo alcanzable de k-1 es una isla y se quita (con lo suyo).
  * HOLGURAS: fachada a 7.0 del asfalto (contrato 15b; solares a >= 6.0 = ancho_margen_pista); las esquinas de una fachada recta en curva entran
    hasta 0.4 m en el margen. Muros de contencion en 21(k+1) con z_base = cota de la terraza baja
    (queda ~3 m enterrado en el talud difuminado de T1: terreno-z_base mediana 2.7) y z_top = alta.
  * Casa (casas_kit_v2.build_casa): pivote en el CENTRO DE LA FACHADA, fachada mirando +Y local,
    cuerpo hacia -Y. Fachada mirando en (fx,fy): rot_z = atan2(fy,fx) - pi/2 (YA calculado aqui).
  * RONDA 15c (pueblo DENSO): (1) sentido_terrazas lee el campo 'sentido' del spec ('sube'|'baja'; manda sobre la
    regla por id). (2) COTA UNICA: la regla ya no es Z(s mas cercana)+h_k sino terreno_montana.CotaSector (la MISMA
    mezcla con la que T1 talla: en la banda llana terreno - regla = 0.00-0.02 m), precalculada cada PASO_COTA m.
    (3) Calles: eje + DOS BORDES en tolerancia (TOL_BORDE), inclinacion lateral <= INCL_CALLE, pendiente <= PEND_CALLE;
    el eje se desplaza hacia fuera (<= 1.5 m) si el borde interior cae en el difuminado del bordillo/muro.
    (4) Travesias: final buscado en u_hi-1.5..u_hi (k < n-1) y HUELLA COMPLETA a <= TOL_HUELLA. (5) Rampas: 5.0 m
    (calzada 4.0), varias posiciones laterales (ladera: desde u_hi+0.6 hacia dentro; mar: hacia fuera), calzada a
    <= TOL_RELLENO y linea de muretes a <= TOL_MURETE; delante, solares de fondo >= FONDO_MIN_RAMPA (el fondo solo
    se reduce frente a rampas/escaleras CONSTRUIDAS). (6) Solares: intentos mas estrechos (5.5-6.5 m) y de menos
    fondo, huella completa (rejilla 1 m) en TOL_SOLAR y rango <= RANGO_CASA; plazoleta solo en huella llana; plaza
    con fondo de la banda y huella llana. (7) Costuras: el mapa de T1 se reproduce (mapa_costuras) y lo construido
    queda a > DIST_COSTURA_EJE / DIST_COSTURA_SOLAR de sus celdas > COSTURA_MAX. (8) Enlaces desplazados hacia dentro
    (y la calle recortada) si el extremo no admite enlace. (9) Muros de una terraza sin calle viva: no se ponen.
    (10) QA: verificar_huellas (huella completa de travesias/rampas/plazoletas/plazas/bordes de calle/casas,
    terrazas vacias, huecos > 12 m por fila, contorno del penon del casino).

  * RONDA 15 v1 (revision de los tramos A-J): (1) ZONAS EXCLUIDAS del spec (huella del McLaren): nada del plan dentro;
    las calles se cortan MARGEN_EXCL_CALLE antes y las islas que quedan se RESCATAN con otra travesia (rampa si cabe,
    si no escalera). (2) ENLACES con boca PERPENDICULAR a la pista a 0.4 m del borde (antes entraban 2 m en el asfalto).
    (3) El terreno que ASOMA se mide con la malla de construir_pista v1 (envolvente inferior de cada quad); el que falta,
    con la bilineal. (4) Rampas de ladera: delante de su tramo ALTO no hay casas a < GAP_RAMPA_ALTO; las rampas que no
    dan acceso en coche a ninguna calle mas se quitan; cada calle de k >= 1 busca una rampa (coche) y si solo tiene
    escaleras pasa a calle PEATONAL de 2.5 m. (5) Escaleras a >= 1.2 m de las casas, casas a >= 0.9 m de calles y
    travesias. (6) Muros solo donde hay escalon real (>= 0.8 m a +-1.5 m) y alguna calle cerca. (7) En los sectores que
    bajan la calle de k >= 1 arranca a 'calle_desde_muro_baja' del muro. (8) QA: zona_excluida, enlace_asfalto,
    rampa_pared, escalera_solar, calle_solar (todos 0).
  * RONDA 15 v2 (pueblo_terreno, revision r2): (1) escaleras SIN calle de la terraza k+1 al final no se ponen (D2-02) y QA
    escalera_sin_destino = 0. (2) Enlaces: la boca se busca cada 2 m hasta 24 m hacia dentro hasta un desnivel calle ->
    borde <= DZ_BOCA_ENLACE (si no, el menor con <= DZ_BOCA_MAX); cada enlace exporta 'desnivel_boca' (N3-F). (3) Muros:
    en los 40 m finales del sector no se exige calle cerca y se PROLONGAN hasta 30 m fuera del sector mientras el escalon
    real siga (C2-02; 'extension': true). (4) Fondo de casa <= FONDO_MAX_SUBE en los sectores que suben y acera del kit
    (0.8 m, inglete) fuera de las casas (N1-C/C2-14). (5) recortar_colas(): cada calle acaba COLA_CALLE m pasado su ultimo
    destino (B2-08/F2-09/C2-10).
  * RONDA 15 v3 (pueblo_terreno, revision r3): (1) D7 tambien en los sectores que BAJAN: sin casas de la terraza k a <
    GAP_RAMPA_ALTO de la meseta/codo y del tramo cuya calzada queda a < 0.4 m bajo su suelo (pretil >= 0.5 m sobre la planta
    baja), ni de la k+1 donde la rampa va > 0.5 m sobre la suya (plan['altos']); QA rampa_pared con ese criterio en el mar.
    (2) D13: GAP_ESC 1.2 -> 2.4 (la casa del kit vuela ~1.35 m sobre su solar). (3) D12: en los REMATE_MURO m finales de cada
    extremo libre de un muro de contencion la coronacion baja al terreno del lado alto + 0.3, en peldanos (_remate_extremos).

FORMATO DE urbanismo.json  (metros, coordenadas de mundo, z absoluta)
{
 "version": 2, "notas": [...], "spec": {...cifras del contrato + constantes del modulo},
 "sectores": [ {
   "id","s0","s1","lado","n_terrazas",
   "terrazas": [ {"k","altura_rel","ok","u_lo","u_hi","u_hi_casa","u_calle","u_fachada","u_rampa",
                  "fondo_max","desvio_rampa","s_ok":[s_ini,s_fin],"banda":[[x,y],...]} ],   # u absolutos desde el asfalto;
                                                                         # s_ok = tramo que T1 aterraza de verdad
   "calles":   [ {"id","terraza","tipo":"servicio"|"terraza"|"peatonal","ancho":4.5 (peatonal 2.5),"pts":[[x,y,z],...],"s":[...],
                  "costura_idx":[i0,i1]|null} ],                       # i0..i1 = vertices de la cuesta de union de costura
   "enlaces":  [ {"id","extremo","ancho":4.5,"pts":[p1,pq,pb,p0]} ],     # v1: extremo de la calle -> 3 m mas -> giro de 90 grados
                                                                         # -> boca perpendicular a 0.4 m del asfalto
   "vallas":   [ {"x","y","z","rot_z","largo","enlace"} ],              # valla CERRADA cruzando el enlace
   "travesias":[ {"id","s","terraza","ancho":4.5,"pts":[[x,y,z],[x,y,z]]} ],   # plana, de la calle k al borde llano
   "rampas":   [ {"id","s_travesia","de_terraza","a_terraza","ancho":5.5,"ancho_calzada":4.5,"pendiente",
                  "direccion_s","pts":[[x,y,z],...],                    # eje: pts[0] junto a la travesia k, pts[-1] =
                                                                         # final del codo (ladera: eje de la calle k+1;
                                                                         # mar: pie en la calle k+1 desviada); 55 m de
                                                                         # pendiente RECTA + meseta 5 m + CODO a nivel
                  "relleno":[[x,y],...],                                 # huella del relleno (hasta la linea del muro)
                  "muros_rampa":[ {"pts":[[x,y,z_base,z_top],...]} ] } ], # caras libres del relleno (z_base = terreno)
   "escaleras":[ {"id","tipo":"idavuelta"|"recta","ancho":1.6,"de_terraza","a_terraza",
                  "tramos":[{"pts":[[x,y,z],...]},...],      # idavuelta: 2 tramos de 5 m (3 m cada uno) + "descansillo"
                  "descansillo":[[x,y,z]x4]|null,            #   + "pasarela" (tramo a nivel que cruza el talud del muro:
                  "pasarela":[[x,y,z],[x,y,z]]|null} ],      #   ladera: del final de B a la calle k+1; mar: del inicio de A
                                                             #   a la travesia k; en el mar el pie de B queda a ~4 m del borde
                                                             #   de la calle k+1 desviada, sobre terraza llana)
   "muros":    [ {"id","terraza","tipo":"contencion"|"ultimo"|"parapeto","pts":[[x,y,z_base,z_top],...]} ],
   "solares":  [ {"id","terraza","tipo":"casa"|"plazoleta","cx","cy","px","py","ancho","fondo",
                  "rot_z","fx","fy","z_suelo","seed","plantas","s","poligono":[[x,y]x4],
                  "sep_x_neg","sep_x_pos","terreno_esquinas":[d1,d2,d3,d4]} ],   # (px,py) = pivote de fachada
   "plazas":   [ {"id","terraza","cx","cy","z","ancho","fondo","rot_z","fx","fy","fuente":[x,y,z],"poligono"} ],
   "salidas":  [ {"id","x","y","z","dx","dy","s","travesia"} ],
   "stats":    {...}
 } ],
 "qa": {... totales, aserciones, "terreno": estadisticas de desvio por tipo, "costuras": [...]}
}
"""

import json
import math
import os
import random
import sys

import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
import shapely
import shapely.ops
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import terreno_montana as tm      # RONDA 15c: CotaSector (la misma cota base que talla T1) y sentido_terrazas
RUTA_GEOM = os.path.join(AQUI, 'geometria_3d.json')
RUTA_SPEC = os.path.join(AQUI, 'urbanismo_spec.json')
RUTA_SALIDA = os.path.join(AQUI, 'urbanismo.json')
DIR_QA = os.path.join(AQUI, 'renders', 'qa')

MARGEN = 6.0            # holgura minima de los SOLARES al asfalto (asf6) = spec ancho_margen_pista; la calle de servicio va a calle_desde (1.5)
ANCHO_RAMPA = 5.0       # RONDA 15c: calzada 4.0 (un carril, como las calles de pueblo) + dos muretes de 0.5 (antes 4.5 + 2 x 0.5:
                        # delante de cada rampa no cabia ninguna casa)
LARGO_RAMPA = 45.0      # tramo en pendiente (v1: lo fija spec['rampa_largo_m']; antes 55)
MESETA_RAMPA = 5.0      # meseta plana en el extremo alto (= anchura del codo)
ANCHO_ESCALERA = 1.6
LARGO_ESCALERA = 10.0
PASO_POLI = 2.0
HOLGURA_PLIEGUE = 0.6
SALTO_Z = 1.0           # salto de z entre vertices contiguos (2 m) que delata una costura del terreno
DESV_COSTURA = 0.8      # |Z(s mas cercana) - Z(s nominal)| en una cuerda sobre un pliegue: costura
TOL_CALLE = (1.2, 0.6)  # terreno bajo el eje de una calle: (max por debajo, max por encima)
TOL_BORDE = (0.8, 0.6)  # RONDA 15c: terreno bajo los BORDES de calles/enlaces (por debajo, por encima)
TOL_ACERA = 0.6         # v1: terreno (envolvente alta) sobre la calle en la linea de sus aceras/bordillos (+-ancho/2+0.6);
                        #     v2 (revision D2-05): OJO, NADIE limpia hoy esa hierba (construir_pista no lee urbanismo.json; la
                        #     limpieza por triangulos tiene que hacerla integrar_escena antes de despeje_final). Hasta entonces
                        #     la tolerancia no se baja: bajarla quitaria calles y casas en vez de arreglar el terreno
TOL_HUELLA = 0.6        # RONDA 15c: |terreno - superficie| en la huella completa de travesias/plazoletas/plazas
INCL_CALLE = 0.35       # RONDA 15c: diferencia maxima de cota base entre los dos bordes de una calle (m)
PEND_CALLE = 0.18       # RONDA 15c: pendiente longitudinal maxima de una calle entre vertices
TOL_SOLAR = (0.5, 1.0)  # esquinas de solar: (max flotante, max enterrada)
TOL_MURO = (0.6, 0.3)   # terreno fuera de [z_base-0.6, z_top+0.3] -> muro cortado
D_ESCALON_MURO = 1.5    # v1 (revision D12/G6): el escalon de un muro se mide a +-1.5 m de su linea
ESCALON_MIN_MURO = 0.8  # v1: sin escalon de 0.8 m entre los dos lados no hay muro (antes quedaban exentos o enterrados)
LARGO_MIN_MURO = 8.0    # v1: trozos de muro de menos de 8 m no se ponen (cubos sueltos)
TOL_RELLENO = 0.6       # terreno que asoma sobre rampas/escaleras/codos -> descartado (umbral T6)
TOL_BANDA = (0.6, 0.3)  # desvio MEDIANO admisible bajo el eje de una calle (por debajo, por encima)
TOL_BANDA_CASA = (0.5, 1.0)
UNION_MAX = 10.0        # hueco maximo entre dos extremos de calle enfrentados que se unen
PEND_UNION = 0.5        # pendiente maxima de la cuesta de union (costura)
FONDO_MIN = 5.0         # fondo minimo de un solar
FONDO_MIN_RAMPA = 4.0   # RONDA 15c: fondo minimo delante de una rampa (casas de crujia unica, <= 3 plantas)
PASO_COTA = 1.0         # rejilla (m) en la que se precalcula la cota base Zb de cada sector
GAP_RAMPA = 0.65        # RONDA 15c: hueco entre la trasera de un solar y el relleno de una rampa (QA exige 0.6)
GAP_RAMPA_ALTO = 4.0    # v1 (revision D7): ... donde la rampa va > 1 m sobre el suelo de la casa: 3 m libres entre la caja real
                        #     de la casa (cornisas, aleros: +0.5) y la huella de la rampa + 0.5 -> 4.0 m desde el poligono
D_RAMPA_BAJA = 7.0      # v1: primeros m de rampa (desde el pie) a <= 1 m sobre el suelo de las casas de delante (6 m en 45 m)
MARGEN_S_RAMPA = 4.5    # v1: la zona 'alta' sigue 4.5 m mas alla del final de la rampa (meseta y codo de 6-7 m de alto)
FLOTA = 'bil'           # v1: cota con la que se mide lo que FLOTA: 'bil' (bilineal); con 'malla'/'min' (la diagonal fija de la
                        #     malla queda hasta ~0.5 m mas baja junto a muros y bordillos) caen islas y terrazas: 172 casas
PLAZOLETA_CADA = 12     # 1 de cada 12 solares queda de plazoleta/jardin (plan T2: 9; v1: 12, la zona del McLaren y los patios de las rampas ya dejan huecos)
GAP_ESC = 2.4           # v1 (revision C-10/D13): hueco minimo escalera-solar (la malla de la casa vuela ~0.5 m; antes 0.5)
                        # v3 (revision D13): 1.2 -> 2.4: la casa del kit vuela ~1.35 m sobre su solar (acera de 0.8 m + cornisas y
                        #     balcones de 0.55-0.6 m): con ~2.0 m en el plan quedaban 0.62-0.65 m reales entre escalera y balcones;
                        #     ahora >= ~1.05 m (con 2.6 caian 4 casas: 188 < 190)
GAP_ESC_ATRAS = 1.2     # v1 (revision D13): trasera de un solar frente a una escalera de ida y vuelta (antes 0.6)
GAP_CALLE_SOLAR = 0.85  # v1 (revision C-10): solar a >= 0.95 m del borde nominal de calles y travesias (el adoquin lleva acera
                        #     de 0.8 m y la fachada de una curva interior entraba hasta 0.44 m); +0.05 del test = 0.9 m
FRACS_RAMPA = (-0.5, -0.4, -0.2, 0.0, 0.2, 0.4, 0.5)   # lineas de muestreo de la rampa (fraccion de ANCHO_RAMPA): murete, calzada, eje
TOL_MURETE = 0.9        # RONDA 15c: terreno sobre la superficie en la linea de los muretes (0.5 m): lo contiene el murete
COSTURA_MAX = 0.6       # RONDA 15c: escalon de costura (mapa de T1) a partir del cual la celda queda prohibida para lo construido
RANGO_CASA = 1.0        # RONDA 15c: rango maximo del terreno dentro de la huella de una casa (rejilla 1 m; revisor: > 1.0 = defecto)
DESVIO_TRANS = 18.0     # RONDA 15c: transicion (m de s) de la calle desviada alrededor de una rampa (mar); antes 10 (quiebros)
DIST_COSTURA_EJE = 4.8  #   ... el eje de calles/travesias/enlaces a > 4.8 m de su centro (revisor: 4.75)
DIST_COSTURA_SOLAR = 2.6  # ... solares, plazas y rampas a > 2.6 m (revisor: 2.5)
ANCHO_PEATONAL = 2.5    # v1 (revision F-05): calle de terraza a la que solo se llega por escaleras: carruggio peatonal
U_BOCA_ENLACE = 0.4     # v1: la boca del enlace (tramo final perpendicular a la pista) queda a 0.4 m del borde del asfalto
MARGEN_EXCL_CALLE = 6.0  # v1: las calles se cortan a 6 m de una zona excluida (+ su margen): sitio para su enlace o su fondo de saco
FONDO_MAX_SUBE = 9.0    # v2 (revision N1-C (3)/C2-14): fondo maximo de casa en los sectores que SUBEN: trasera en u_local <= 16, a
                        #     >= 1.5 m del pie de la rampa del muro siguiente (la rejilla de 4 m la adelanta a u 16.5-17)
DZ_BOCA_ENLACE = 0.75   # v2 (revision N3-F): desnivel preferido entre la calle (pq) y la boca del enlace en el borde de la pista (p0)
DZ_BOCA_MAX = 0.9       # v2 (N3-F): desnivel maximo admitido si en 24 m no hay sitio con <= DZ_BOCA_ENLACE (contrato: acera alta a
                        #     +-0.5 m mas el peralte del borde; con 0.6 estricto se perdian 6 de 22 enlaces: calles sin acceso)
D_EXT_MURO = 30.0       # v2 (revision C2-02): el muro sigue hasta 30 m mas alla del extremo del sector (fundido de T1) mientras
                        #     el escalon real sea >= ESCALON_MIN_MURO (antes acababa en s0/s1 y la rampa seguia sin muro delante)
D_FIN_MURO = 40.0       # v2 (C2-02): en los 40 m finales del sector no se exige calle a <= 15 m por s para poner muro
REMATE_MURO = 8.0       # v3 (revision D12): metros finales de cada extremo libre de un muro de contencion con la coronacion rebajada
COLA_CALLE = 2.0        # v2 (revision B2-08/F2-09/C2-10): una calle acaba 2 m pasado su ultimo destino (casa, travesia, rampa, ...)
_PISTA = None           # referencia global a la pista

def log(msg):
    print('[urbanismo] ' + str(msg))

def sentido_terrazas(sc):
    """+1: las terrazas SUBEN desde la pista (sector de ladera); -1: BAJAN (sector de mar). Lo fija el spec
    ('sube': true/false) o, si no lo trae, el id del sector ('_mar' baja, el resto sube). NO depende del lado:
    en pueblo_alto el macizo queda a la izquierda (+1). MISMA regla que terreno_montana.sentido_terrazas.
    RONDA 15c: manda el campo 'sentido' ('sube' | 'baja'); si falta, 'sube' (bool) y despues la regla por id."""
    sen = str(sc.get('sentido', '')).strip().lower()
    if sen in ('sube', 'baja'):
        return 1.0 if sen == 'sube' else -1.0
    if 'sube' in sc:
        return 1.0 if sc['sube'] else -1.0
    return -1.0 if str(sc['id']).endswith('_mar') else 1.0

# ---------------------------------------------------------------------------
# Terreno: rejilla de T1 (z[j*nx+i], x = x0+i*cell, y = y0+j*cell), interpolacion bilineal
# (la misma que construir_pista.py / integrar_escena.py)
# ---------------------------------------------------------------------------
class Terreno:
    def __init__(self, t):
        self.x0 = float(t['x0']); self.y0 = float(t['y0']); self.cell = float(t['cell'])
        self.nx = int(t['nx']); self.ny = int(t['ny'])
        self.Z = np.asarray(t['z'], dtype=float).reshape(self.ny, self.nx)

    def z(self, x, y):
        fx = (x - self.x0) / self.cell; fy = (y - self.y0) / self.cell
        i = min(max(int(math.floor(fx)), 0), self.nx - 2); j = min(max(int(math.floor(fy)), 0), self.ny - 2)
        a = min(max(fx - i, 0.0), 1.0); b = min(max(fy - j, 0.0), 1.0)
        Z = self.Z
        return float(Z[j, i] * (1 - a) * (1 - b) + Z[j, i + 1] * a * (1 - b)
                     + Z[j + 1, i] * (1 - a) * b + Z[j + 1, i + 1] * a * b)

    def zs(self, xs, ys):
        xs = np.asarray(xs, dtype=float); ys = np.asarray(ys, dtype=float)
        return map_coordinates(self.Z, [(ys - self.y0) / self.cell, (xs - self.x0) / self.cell], order=1, mode='nearest')

    # RONDA 15 v1 (revision N2/C-14): la malla TERRENO de construir_pista (v1 pista) va TRIANGULADA con una diagonal FIJA
    # por celda, (i,j)-(i+1,j+1) (la a-c que usaban el render y el kn5); antes eran quads y aqui solo se miraba la
    # bilineal, que en celdas con rampa (bordillo, muro) se separa 0.5-1.3 m de la malla: el plan aprobaba casas y calles
    # que en la malla quedaban mas enterradas. Ahora:
    #   * 'el terreno ASOMA sobre X' (casas enterradas, hierba sobre calles, rampas, escaleras, muros) se mide con la
    #     MALLA (zs_malla, la misma superficie que el render, el kn5 y los inspectores);
    #   * 'X FLOTA / hueco bajo X' se sigue midiendo con la bilineal (FLOTA): con la malla, la diagonal fija deja el
    #     terreno hasta ~0.5 m mas bajo junto a muros y bordillos y caen calles, rampas y terrazas enteras; ese hueco lo
    #     tapan el canto de las calles (0.35), los zocalos y, si hace falta, construir_pista (no_arreglados).
    def zs_malla(self, xs, ys):
        """cota de la malla TERRENO de construir_pista v1: triangulos (00,10,11) y (00,11,01) de cada celda."""
        xs = np.asarray(xs, dtype=float); sh = xs.shape
        xs = np.atleast_1d(xs).ravel(); ys = np.atleast_1d(np.asarray(ys, dtype=float)).ravel()
        fx = (xs - self.x0) / self.cell; fy = (ys - self.y0) / self.cell
        i = np.clip(np.floor(fx).astype(int), 0, self.nx - 2); j = np.clip(np.floor(fy).astype(int), 0, self.ny - 2)
        a = np.clip(fx - i, 0.0, 1.0); b = np.clip(fy - j, 0.0, 1.0)
        Z = self.Z
        z00 = Z[j, i]; z10 = Z[j, i + 1]; z01 = Z[j + 1, i]; z11 = Z[j + 1, i + 1]
        t1 = np.where(a >= b, z00 + a * (z10 - z00) + b * (z11 - z10), z00 + b * (z01 - z00) + a * (z11 - z01))
        return t1.reshape(sh) if sh else float(t1[0])

    def z_malla(self, x, y):
        return float(self.zs_malla(np.array([x]), np.array([y]))[0])


# ---------------------------------------------------------------------------
# Pista: muestras, interpolacion, posiciones laterales, distancia minima (KD-tree)
# ---------------------------------------------------------------------------
class Pista:
    def __init__(self, g):
        m = g['muestras']
        self.paso = float(g['paso_m'])
        self.n = len(m)
        self.L = float(g['largo_m'])
        self.X = np.array([q['x'] for q in m]); self.Y = np.array([q['y'] for q in m])
        self.Z = np.array([q['z'] for q in m]); self.W = np.array([q['w'] for q in m])
        self.NX = np.array([q['nx'] for q in m]); self.NY = np.array([q['ny'] for q in m])
        self.LAT = np.array([q.get('lat', 0.0) for q in m])
        self.kd = cKDTree(np.c_[self.X, self.Y])
        tx = np.gradient(self.X); ty = np.gradient(self.Y)
        nn = np.hypot(tx, ty); nn[nn == 0] = 1.0
        self.TX = tx / nn; self.TY = ty / nn
        self.pit = g.get('pit_lane', [])

    def _ij(self, s):
        f = (s / self.paso) % self.n
        i = int(math.floor(f)); j = (i + 1) % self.n
        return i, j, f - i

    def interp(self, arr, s):
        i, j, fr = self._ij(s)
        return float(arr[i] * (1.0 - fr) + arr[j] * fr)

    def z(self, s):
        return self.interp(self.Z, s)

    def frame(self, s):
        i, j, fr = self._ij(s)
        nx = self.NX[i] * (1 - fr) + self.NX[j] * fr; ny = self.NY[i] * (1 - fr) + self.NY[j] * fr
        nn = math.hypot(nx, ny) or 1.0
        return dict(x=self.interp(self.X, s), y=self.interp(self.Y, s), z=self.interp(self.Z, s),
                    nx=nx / nn, ny=ny / nn, w=self.interp(self.W, s), lat=self.interp(self.LAT, s),
                    tx=self.interp(self.TX, s), ty=self.interp(self.TY, s))

    def pos(self, s, lado, u):
        p = self.frame(s)
        d = p['w'] / 2.0 + u
        return (p['x'] + lado * p['nx'] * d, p['y'] + lado * p['ny'] * d)

    def z_borde(self, s, lado):
        p = self.frame(s)
        return p['z'] - p['lat'] * lado * (p['w'] / 2.0)

    def dist_min(self, x, y):
        d, _ = self.kd.query([x, y])
        return float(d)

    def s_proy(self, x, y, i, i_min=0, i_max=None):
        # abscisa s del punto mas cercano a (x,y) en los dos segmentos adyacentes a la muestra i
        i_max = self.n - 1 if i_max is None else i_max
        mejor = (1e18, i * self.paso)
        for a in (i - 1, i):
            b = a + 1
            if a < i_min or b > i_max:
                continue
            ax, ay = self.X[a], self.Y[a]; bx, by = self.X[b] - ax, self.Y[b] - ay
            L2 = bx * bx + by * by
            f = 0.0 if L2 == 0 else min(1.0, max(0.0, ((x - ax) * bx + (y - ay) * by) / L2))
            d2 = (ax + bx * f - x) ** 2 + (ay + by * f - y) ** 2
            if d2 < mejor[0]:
                mejor = (d2, (a + f) * self.paso)
        return mejor[1]

    def s_cercana(self, x, y):
        _, i = self.kd.query([x, y])
        return self.s_proy(x, y, int(i))

    def ds(self, a, b):
        d = abs(a - b) % self.L
        return min(d, self.L - d)

    def valido(self, x, y, s, u, holgura=1.0, tol_s=40.0):
        # el punto esta a la distancia esperada de SU tramo de pista (no es un pliegue ni esta mas cerca
        # de otro tramo) y la muestra mas cercana es la suya
        d_esp = self.interp(self.W, s) / 2.0 + u
        if self.dist_min(x, y) < d_esp - holgura:
            return False
        return self.ds(self.s_cercana(x, y), s) <= tol_s

    def _quads(self, X, Y, NX, NY, W):
        quads = []
        for i in range(len(X) - 1):
            j = i + 1
            a = W[i] / 2.0; b = W[j] / 2.0
            quads.append(Polygon([(X[i] + NX[i] * a, Y[i] + NY[i] * a), (X[j] + NX[j] * b, Y[j] + NY[j] * b),
                                  (X[j] - NX[j] * b, Y[j] - NY[j] * b), (X[i] - NX[i] * a, Y[i] - NY[i] * a)]).buffer(0))
        return unary_union(quads) if quads else Polygon()

    def poligono_asfalto(self):
        return self._quads(self.X, self.Y, self.NX, self.NY, self.W)

    def poligono_pit(self):
        if not self.pit:
            return Polygon()
        p = self.pit
        return self._quads([q['x'] for q in p], [q['y'] for q in p], [q['nx'] for q in p], [q['ny'] for q in p], [q['w'] for q in p])

# ---------------------------------------------------------------------------
# Polilinea con parametro de arco (t) y abscisa de pista (s) en cada vertice
# ---------------------------------------------------------------------------
class Poli:
    def __init__(self, xy, s, attr=None):
        self.xy = np.asarray(xy, dtype=float).reshape(-1, 2)
        self.s = np.asarray(s, dtype=float)
        seg = np.hypot(np.diff(self.xy[:, 0]), np.diff(self.xy[:, 1]))
        self.cum = np.concatenate([[0.0], np.cumsum(seg)])
        self.attr = attr if attr is not None else {}
        self.line = LineString(self.xy) if len(self.xy) >= 2 else None

    @property
    def largo(self):
        return float(self.cum[-1]) if len(self.cum) else 0.0

    def punto(self, t):
        t = min(max(t, 0.0), self.largo)
        return (float(np.interp(t, self.cum, self.xy[:, 0])), float(np.interp(t, self.cum, self.xy[:, 1])))

    def s_de_t(self, t):
        return float(np.interp(min(max(t, 0.0), self.largo), self.cum, self.s))

    def t_de_s(self, s):
        return float(np.interp(s, self.s, self.cum))

    def t_de_xy(self, x, y):
        return float(self.line.project(Point(x, y)))

    def tangente(self, t):
        a = self.punto(max(t - 1.0, 0.0)); b = self.punto(min(t + 1.0, self.largo))
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        return (dx / n, dy / n)

    def valor(self, nombre, t, defecto=None):
        v = self.attr.get(nombre)
        if v is None:
            return defecto
        return v[int(np.argmin(np.abs(self.cum - t)))]

    def tramo(self, ta, tb, paso=PASO_POLI):
        # sub-polilinea [ta,tb] remuestreada cada ~paso m (conserva s y atributos; 'z' se interpola)
        ta = max(0.0, min(ta, tb)); tb = min(self.largo, max(ta, tb))
        if tb - ta < 0.5:
            return None
        n = max(2, int(round((tb - ta) / paso)) + 1)
        ts = np.linspace(ta, tb, n)
        xy = np.c_[np.interp(ts, self.cum, self.xy[:, 0]), np.interp(ts, self.cum, self.xy[:, 1])]
        s = np.interp(ts, self.cum, self.s)
        attr = {}
        for k, v in self.attr.items():
            if k == 'z':
                attr[k] = np.interp(ts, self.cum, np.asarray(v, dtype=float))
            else:
                attr[k] = np.asarray(v)[[int(np.argmin(np.abs(self.cum - t))) for t in ts]]
        return Poli(xy, s, attr)

    def recortar(self, prohibido, min_largo=25.0):
        # trozos de la polilinea fuera de 'prohibido' (poligono), cada uno como Poli nuevo
        if self.line is None:
            return []
        if prohibido is None or prohibido.is_empty:
            return [self] if self.largo >= min_largo else []
        resto = self.line.difference(prohibido)
        piezas = []
        for gm in (list(resto.geoms) if hasattr(resto, 'geoms') else [resto]):
            if gm.is_empty or gm.length < min_largo:
                continue
            cs = list(gm.coords)
            ta = self.t_de_xy(*cs[0][:2]); tb = self.t_de_xy(*cs[-1][:2])
            tr = self.tramo(min(ta, tb), max(ta, tb))
            if tr is not None and tr.largo >= min_largo:
                piezas.append(tr)
        piezas.sort(key=lambda p: p.s[0])
        return piezas

    def pts3(self, z):
        return [[round(float(x), 3), round(float(y), 3), round(float(zz), 3)] for (x, y), zz in zip(self.xy, z)]

def curva_offset(pista, s0, s1, lado, u, holgura=HOLGURA_PLIEGUE, paso=PASO_POLI):
    """Offset de la pista a u m del borde del asfalto entre s0 y s1, SIN pliegues.

    Se conserva una muestra desplazada solo si su distancia minima a la pista es ~ la esperada
    (w/2+u); los puntos de un bucle interior (o cerca de otro tramo) se eliminan y el hueco se
    puentea en recta. Despues se eliminan retrocesos y se remuestrea cada 'paso' m.
    """
    i0 = int(round(s0 / pista.paso)); i1 = int(round(s1 / pista.paso))
    kept = []
    for i in range(i0, i1 + 1):
        d = pista.W[i] / 2.0 + u
        x = pista.X[i] + lado * pista.NX[i] * d; y = pista.Y[i] + lado * pista.NY[i] * d
        if pista.valido(x, y, i * pista.paso, u, holgura):
            kept.append([x, y, i * pista.paso, pista.TX[i], pista.TY[i]])
    cambio = True
    while cambio and len(kept) > 2:
        cambio = False
        out = [kept[0]]
        for q in kept[1:]:
            p = out[-1]
            if (q[0] - p[0]) * q[3] + (q[1] - p[1]) * q[4] <= 0.0:
                cambio = True
                continue
            out.append(q)
        kept = out
    if len(kept) < 2:
        return None
    base = Poli([(q[0], q[1]) for q in kept], [q[2] for q in kept])
    po = base.tramo(0.0, base.largo, paso)
    po.attr['coh'] = np.array([1.0 if pista.valido(x, y, s, u, holgura + 1.0) else 0.0
                               for (x, y), s in zip(po.xy, po.s)])
    return po


def componer_por_s(tramos, paso=PASO_POLI, atributos=None):
    """Une trozos [(Poli, s_ini, s_fin, dict_attr_const), ...] tomando de cada Poli los vertices con
    s en su intervalo; los huecos entre trozos se unen en recta (transiciones)."""
    xy = []; ss = []; at = {k: [] for k in (atributos or [])}
    for (po, sa, sb, consts) in tramos:
        if po is None:
            continue
        for (x, y), s in zip(po.xy, po.s):
            if sa <= s <= sb:
                xy.append((x, y)); ss.append(s)
                for k in at:
                    at[k].append(consts.get(k))
    if len(xy) < 2:
        return None
    orden = np.argsort(ss, kind='stable')
    xy = [xy[i] for i in orden]; ss = [ss[i] for i in orden]
    for k in at:
        at[k] = [at[k][i] for i in orden]
    po = Poli(xy, ss, {k: np.array(v, dtype=float) for k, v in at.items()})
    return po.tramo(0.0, po.largo, paso)

# ---------------------------------------------------------------------------
# Utilidades geometricas
# ---------------------------------------------------------------------------
def rect_fachada(p, T, f, ancho, fondo):
    # p = centro de fachada, T = tangente de la linea de fachada, f = direccion de la fachada (hacia
    # la calle); el cuerpo del solar se extiende hacia -f
    ax, ay = T[0] * ancho / 2.0, T[1] * ancho / 2.0
    bx, by = -f[0] * fondo, -f[1] * fondo
    return Polygon([(p[0] - ax, p[1] - ay), (p[0] + ax, p[1] + ay),
                    (p[0] + ax + bx, p[1] + ay + by), (p[0] - ax + bx, p[1] - ay + by)])

def franja(poli, ancho):
    if poli is None or poli.line is None:
        return Polygon()
    return poli.line.buffer(ancho / 2.0, cap_style='flat')

def union(polys):
    polys = [p for p in polys if p is not None and not p.is_empty]
    return unary_union(polys) if polys else Polygon()

def dist_a_piezas(piezas, x, y):
    pt = Point(x, y)
    return min([pz.line.distance(pt) for pz in piezas if pz.line is not None] or [1e9])

def r3(v):
    return round(float(v), 3)

def trocear(poli, ok, cortes_entre, min_largo):
    """Trozos maximos de 'poli' formados por vertices ok[i] True y sin corte entre i e i+1
    (cortes_entre[i] True = corte entre los vertices i e i+1). Cada trozo >= min_largo."""
    out = []; a = None
    n = len(poli.xy)
    for i in range(n):
        if ok[i] and a is None:
            a = i
        fin = (not ok[i]) or i == n - 1 or (i < n - 1 and cortes_entre[i])
        if a is not None and fin:
            b = i if ok[i] else i - 1
            if b - a >= 1:
                tr = poli.tramo(float(poli.cum[a]), float(poli.cum[b]))
                if tr is not None and tr.largo >= min_largo:
                    out.append(tr)
            a = None
    return out

def unir_enfrentados(piezas, max_hueco=UNION_MAX, pend=PEND_UNION):
    """Une dos trozos consecutivos (ordenados por s) cuyos extremos se enfrentan a <= max_hueco m.
    La z del tramo de union (y de los vertices vecinos necesarios para que la cuesta no supere
    'pend') se interpola linealmente: attr 'z' y attr 'puente' (1 en los vertices reinterpolados).
    Devuelve (piezas, uniones) con uniones = [(xa, ya, xb, yb, hueco, dz)]."""
    piezas = sorted(piezas, key=lambda p: p.s[0])
    uniones = []
    i = 0
    while i < len(piezas) - 1:
        a, b = piezas[i], piezas[i + 1]
        hueco = float(math.hypot(a.xy[-1][0] - b.xy[0][0], a.xy[-1][1] - b.xy[0][1]))
        if hueco > max_hueco or 'z' not in a.attr or 'z' not in b.attr:
            i += 1
            continue
        dz = float(b.attr['z'][0] - a.attr['z'][-1])
        # largo de cuesta necesario (minimo el hueco) para no superar 'pend'
        Lc = max(hueco, abs(dz) / pend)
        extra = max(0.0, (Lc - hueco) / 2.0)
        xy = np.vstack([a.xy, b.xy]); s = np.concatenate([a.s, b.s])
        z = np.concatenate([a.attr['z'], b.attr['z']])
        pu = np.concatenate([a.attr.get('puente', np.zeros(len(a.xy))), b.attr.get('puente', np.zeros(len(b.xy)))])
        nuevo = Poli(xy, s, {'z': z, 'puente': pu})
        t_a = float(nuevo.cum[len(a.xy) - 1]); t_b = float(nuevo.cum[len(a.xy)])
        t0 = max(0.0, t_a - extra); t1 = min(nuevo.largo, t_b + extra)
        z0 = float(np.interp(t0, nuevo.cum, z)); z1 = float(np.interp(t1, nuevo.cum, z))
        sel = (nuevo.cum >= t0 - 1e-6) & (nuevo.cum <= t1 + 1e-6)
        z[sel] = z0 + (z1 - z0) * (nuevo.cum[sel] - t0) / max(t1 - t0, 1e-6)
        pu[sel] = 1.0
        nuevo = Poli(xy, s, {'z': z, 'puente': pu})
        uniones.append((r3(a.xy[-1][0]), r3(a.xy[-1][1]), r3(b.xy[0][0]), r3(b.xy[0][1]), r3(hueco), r3(dz)))
        piezas[i:i + 2] = [nuevo]
    return piezas, uniones

# ---------------------------------------------------------------------------
# Sector de pueblo: terrazas (banda llana medida), calles, travesias, rampas, escaleras, muros, solares
# ---------------------------------------------------------------------------
class Sector:
    def __init__(self, sec, pista, terreno, spec, ctx):
        self.id = sec['id']; self.s0 = float(sec['s0']); self.s1 = float(sec['s1'])
        self.lado = int(sec['lado']); self.n = int(sec['n_terrazas'])
        self.pista = pista; self.terreno = terreno; self.spec = spec; self.ctx = ctx
        self.AT = float(spec['ancho_terraza']); self.AC = float(spec['ancho_calle'])
        self.u_c0 = float(spec['calle_desde']) + self.AC / 2.0          # 3.75 eje de calle (contrato 15b: calle 1.5..6)
        self.u_f0 = float(spec['fachada_desde'])                        # 7.0 fachada (contrato 15b)
        # v1 (revision C-08/F-06): en los sectores que BAJAN la calle de la terraza k >= 1 queda al pie del muro y la rejilla
        # de 4 m derrama la rampa del muro sobre ella (hierba +0.8 m): arranca a 'calle_desde_muro_baja' (4.5) del muro
        self.u_c0_baja = float(spec.get('calle_desde_muro_baja', spec['calle_desde'])) + self.AC / 2.0
        self.fondo_max = float(spec['fondo_max_casa'])                  # 11 (contrato 15b)
        self.dh = float(spec['altura_terraza']); h1 = float(spec['altura_terraza_1'])
        self.sg = sentido_terrazas(sec)                                 # +1 ladera (sube), -1 mar (baja); NO depende del lado
        self.sube = self.sg > 0
        self.h = [self.sg * (h1 + self.dh * k) for k in range(self.n + 1)]
        self.rng = random.Random(1000 + sum(ord(c) for c in self.id))
        # muestras del sector (s0-10..s1+10): T1 asigna cada celda a la muestra mas cercana DEL SECTOR
        self.i_lo = max(0, int(round((self.s0 - 10.0) / pista.paso)))
        self.i_hi = min(pista.n - 1, int(round((self.s1 + 10.0) / pista.paso)))
        self.kd_s = cKDTree(np.c_[pista.X[self.i_lo:self.i_hi + 1], pista.Y[self.i_lo:self.i_hi + 1]])
        self._curvas = {}
        self.calles = []; self.enlaces = []; self.vallas = []; self.travesias = []
        self.rampas = []; self.escaleras = []; self.muros = []; self.solares = []
        self.plazas = []; self.salidas = []; self.uniones = []
        self.piezas = {}            # k -> [Poli] trozos de calle k (attr 'z')
        self.F_propio = []          # poligonos propios (para solares)
        self.F_calles = {}          # id de calle -> franja (aparte: las calles huerfanas se quitan)
        self.cortes = {k: [] for k in range(self.n)}   # poligonos que cortan el muro k
        self.desvios = {k: [] for k in range(self.n)}  # mar: tramos (sa,sb) de calle k desviada
        self.zonas_rampa = {k: [] for k in range(self.n)}  # ladera: (sa,sb) con fondo reducido
        self.planes = []            # rampas planificadas
        self.terr_stats = {}        # desvios del terreno por tipo de elemento
        self.descartes = []         # motivos de descarte (QA)

    # ----- cotas (RONDA 15c): la MISMA cota base Zb con la que T1 talla las terrazas (terreno_montana.CotaSector:
    #       mezcla ponderada de Z(s) del sector + talud entre ramas enfrentadas), precalculada en una rejilla de
    #       PASO_COTA m sobre la banda del sector e interpolada bilineal. Fuera de la rejilla (o en el lado
    #       contrario) se usa la regla antigua Z(s de la muestra mas cercana del sector). -----
    def s_cerc(self, x, y):
        _, i = self.kd_s.query([x, y])
        return self.pista.s_proy(x, y, self.i_lo + int(i), self.i_lo, self.i_hi)

    def preparar_cota(self):
        p = self.pista
        self.cota = tm.CotaSector(p.X, p.Y, p.Z, p.NX, p.NY, p.W, p.paso,
                                  dict(s0=self.s0, s1=self.s1, lado=self.lado), self.spec)
        js = self.cota.js_in
        o_max = self.AT * self.n + 16.0
        mx = float(p.W[js].max()) / 2.0 + o_max + 4.0
        x0 = float(p.X[js].min()) - mx; x1 = float(p.X[js].max()) + mx
        y0 = float(p.Y[js].min()) - mx; y1 = float(p.Y[js].max()) + mx
        gx = np.arange(x0, x1 + PASO_COTA, PASO_COTA); gy = np.arange(y0, y1 + PASO_COTA, PASO_COTA)
        GX, GY = np.meshgrid(gx, gy)
        d, _ = self.cota.tree_s.query(np.c_[GX.ravel(), GY.ravel()], distance_upper_bound=o_max + 12.0)
        cerca = np.isfinite(d)
        zb = np.full(GX.size, np.nan)
        if cerca.any():
            zz, o, ok = self.cota.zb(GX.ravel()[cerca], GY.ravel()[cerca])
            zz[~ok] = np.nan
            zb[np.where(cerca)[0]] = zz
        self.cz = dict(x0=x0, y0=y0, nx=len(gx), ny=len(gy), Z=zb.reshape(GX.shape))

    def mapa_costuras(self):
        """RONDA 15c: el MISMO mapa de costuras que imprime T1 (terreno_montana, 'COSTURAS'): escalon entre celdas
        vecinas de la rejilla de la misma terraza, fuera de las rampas (bordillo, muro, borde exterior) y del talud
        entre ramas, descontando la rasante Z(s) de sus muestras mas cercanas si estan a <= 20 m por la pista (si no,
        |dz| entero). Las celdas > COSTURA_MAX quedan PROHIBIDAS para lo construido: el eje de calles/travesias/
        enlaces a > DIST_COSTURA_EJE y solares/plazas/rampas a > DIST_COSTURA_SOLAR (criterio del revisor)."""
        t = self.terreno; c = t.cell; cz = self.cz
        o_fin = self.AT * self.n
        i0 = max(0, int(math.ceil((cz['x0'] - t.x0) / c))); i1 = min(t.nx - 1, int((cz['x0'] + (cz['nx'] - 1) * PASO_COTA - t.x0) / c))
        j0 = max(0, int(math.ceil((cz['y0'] - t.y0) / c))); j1 = min(t.ny - 1, int((cz['y0'] + (cz['ny'] - 1) * PASO_COTA - t.y0) / c))
        self.costura_pts = []
        if i1 <= i0 or j1 <= j0:
            return
        I, J = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
        CX = t.x0 + I * c; CY = t.y0 + J * c
        zb, o, ok, tt, g = self.cota.zb_info(CX.ravel(), CY.ravel())
        zt = t.Z[J, I].ravel()
        kk = np.clip(np.floor(np.maximum(o, 0.0) / self.AT).astype(int), 0, self.n - 1)
        ol = o - self.AT * kk
        hk = np.array(self.h[:self.n])[kk]
        llano = (ok & (o >= 2.0) & (o <= o_fin - 0.5) & (ol <= self.AT - 3.0) & ~((kk > 0) & (ol < 0.5))
                 & (np.abs(zt - zb - hk) < 1.0) & (tt <= 0.02))
        sh = CX.shape
        LL = llano.reshape(sh); KK = kk.reshape(sh); ZT = zt.reshape(sh); GG = g.reshape(sh); ZN = self.pista.Z[g].reshape(sh)
        marca = np.zeros(sh, bool); dz_max = 0.0
        for sa, sb in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))),
                       ((slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
            par = LL[sa] & LL[sb] & (KK[sa] == KK[sb])
            ds = np.abs(GG[sa] - GG[sb]) * self.pista.paso
            dz = np.where(ds <= 20.0, np.abs((ZT[sa] - ZT[sb]) - (ZN[sa] - ZN[sb])), np.abs(ZT[sa] - ZT[sb]))
            mal = par & (ds <= 60.0) & (dz > COSTURA_MAX)
            if mal.any():
                dz_max = max(dz_max, float(dz[mal].max()))
            marca[sa] |= mal; marca[sb] |= mal
        jj, ii = np.where(marca)
        self.costura_pts = [(float(CX[j, i]), float(CY[j, i])) for j, i in zip(jj, ii)]
        self.costura_dz_max = dz_max
        log('  mapa de costuras (como T1, > %.1f m): %d celdas%s' % (COSTURA_MAX, len(self.costura_pts),
                                                                    (' (max %.2f m): zona prohibida para lo construido' % dz_max) if self.costura_pts else ''))

    def zona_costura(self, dist):
        """poligono prohibido: celdas de costura engordadas 'dist' m (vacio si no hay)."""
        if not self.costura_pts:
            return Polygon()
        key = round(dist, 2)
        cache = self.__dict__.setdefault('_zc', {})
        if key not in cache:
            cache[key] = union([Point(p).buffer(dist, 8) for p in self.costura_pts])
        return cache[key]

    def zxys(self, xs, ys):
        """Zb vectorizado (NaN -> regla antigua)."""
        xs = np.atleast_1d(np.asarray(xs, dtype=float)); ys = np.atleast_1d(np.asarray(ys, dtype=float))
        c = self.cz
        z = map_coordinates(c['Z'], [(ys - c['y0']) / PASO_COTA, (xs - c['x0']) / PASO_COTA], order=1, mode='constant', cval=np.nan)
        malo = ~np.isfinite(z)
        for i in np.where(malo)[0]:
            z[i] = self.pista.z(self.s_cerc(xs[i], ys[i]))
        return z

    def zxy(self, x, y):
        c = self.cz
        fx = (x - c['x0']) / PASO_COTA; fy = (y - c['y0']) / PASO_COTA
        i = int(math.floor(fx)); j = int(math.floor(fy))
        if 0 <= i < c['nx'] - 1 and 0 <= j < c['ny'] - 1:
            a = fx - i; b = fy - j; Z = c['Z']
            v = Z[j, i] * (1 - a) * (1 - b) + Z[j, i + 1] * a * (1 - b) + Z[j + 1, i] * (1 - a) * b + Z[j + 1, i + 1] * a * b
            if v == v:
                return float(v)
        return self.pista.z(self.s_cerc(x, y))

    def zf(self, k, dz=0.05):
        h = self.h[k]
        return lambda x, y: self.zxy(x, y) + h + dz

    def u_base(self, k):
        return self.AT * k

    def curva(self, u):
        key = round(u, 3)
        if key not in self._curvas:
            self._curvas[key] = curva_offset(self.pista, self.s0, self.s1, self.lado, u)
        return self._curvas[key]

    def incoherencia(self, poli):
        if poli is None or 'coh' not in poli.attr:
            return Polygon()
        return union([Point(x, y).buffer(3.0) for (x, y), c in zip(poli.xy, poli.attr['coh']) if c < 0.5])

    def desviada(self, k, s):
        return any(sa <= s <= sb for (sa, sb) in self.desvios[k])

    def posiciones_travesias(self):
        Ls = self.s1 - self.s0
        nt = max(1, int(round(Ls / float(self.spec['travesia_cada_m']))))
        return [self.s0 + Ls * (i + 0.5) / nt for i in range(nt)]

    # ----- desvio del terreno real respecto a la regla, en puntos (x,y) de la terraza k -----
    def desvio(self, k, xs, ys, dz=0.0):
        xs = np.asarray(xs, dtype=float); ys = np.asarray(ys, dtype=float)
        zr = self.zxys(xs, ys) + self.h[k] + dz
        return self.terreno.zs(xs, ys) - zr

    def _dev_huella(self, pts, z, ancho, z_de_t=None, paso=1.0, fracs=(-0.5, -0.25, 0.0, 0.25, 0.5), modo='bil'):
        """RONDA 15c: terreno - superficie en la HUELLA COMPLETA de un elemento lineal (eje y lineas a +-ancho/4 y
        +-ancho/2 cada 'paso' m). z = cota constante o z_de_t(t) a lo largo del eje.
        v1: modo 'bil' (bilineal), 'malla' (malla TERRENO) o 'ambos' -> (bilineal, malla)."""
        ln = LineString([tuple(p[:2]) for p in pts])
        L = ln.length
        if L < 1e-6:
            return (np.zeros(1), np.zeros(1)) if modo == 'ambos' else np.zeros(1)
        ts = np.linspace(0.0, L, max(2, int(math.ceil(L / paso)) + 1))
        xs = []; ys = []; zz = []
        for t in ts:
            a = ln.interpolate(max(t - 0.5, 0.0)); b = ln.interpolate(min(t + 0.5, L)); c = ln.interpolate(t)
            tx, ty = b.x - a.x, b.y - a.y; n_ = math.hypot(tx, ty) or 1.0
            nx_, ny_ = -ty / n_, tx / n_
            zt = z_de_t(t) if z_de_t is not None else z
            for f in fracs:
                xs.append(c.x + nx_ * f * ancho); ys.append(c.y + ny_ * f * ancho); zz.append(zt)
        zz = np.asarray(zz, dtype=float)
        return self._dev_modo(xs, ys, zz, modo)

    def _dev_modo(self, xs, ys, z, modo):
        if modo == 'malla':
            return self.terreno.zs_malla(xs, ys) - z
        if modo == 'ambos':
            zm = self.terreno.zs_malla(xs, ys)
            zb = self.terreno.zs(xs, ys)
            zf = np.minimum(zb, zm) if FLOTA == 'min' else (zm if FLOTA == 'malla' else zb)
            return zf - z, zm - z
        return self.terreno.zs(xs, ys) - z

    def _dev_poligono(self, poly, z, paso=1.0, modo='bil'):
        """RONDA 15c: terreno - z en una rejilla de 'paso' m dentro del poligono + sus vertices (v1: modo como _dev_huella)."""
        minx, miny, maxx, maxy = poly.bounds
        GX, GY = np.meshgrid(np.arange(minx + paso / 2.0, maxx, paso), np.arange(miny + paso / 2.0, maxy, paso))
        dentro = shapely.contains_xy(poly, GX.ravel(), GY.ravel())
        xs = np.concatenate([[q[0] for q in list(poly.exterior.coords)[:-1]], GX.ravel()[dentro]])
        ys = np.concatenate([[q[1] for q in list(poly.exterior.coords)[:-1]], GY.ravel()[dentro]])
        return self._dev_modo(xs, ys, z, modo)

    def anota(self, tipo, dev):
        d = self.terr_stats.setdefault(tipo, [])
        d.extend([float(v) for v in np.atleast_1d(dev)])

    # ----- banda llana real de cada terraza (desvio mediano del terreno por u_local) -----
    def medir_bandas(self):
        self.b = {}
        us = np.arange(0.0, self.AT + 0.001, 0.25)
        marg = 30.0 if self.s1 - self.s0 >= 100.0 else 10.0
        ss = np.arange(self.s0 + marg, self.s1 - marg + 1e-6, 4.0)
        for k in range(self.n):
            ub = self.u_base(k)
            u_c0 = self.u_c0_baja if (not self.sube and k >= 1) else self.u_c0
            dev = np.zeros((len(us), len(ss)))
            for j, s in enumerate(ss):
                fr = self.pista.frame(s)
                d = fr['w'] / 2.0 + ub + us
                xs = fr['x'] + self.lado * fr['nx'] * d; ys = fr['y'] + self.lado * fr['ny'] * d
                dev[:, j] = self.terreno.zs(xs, ys) - (self.zxys(xs, ys) + self.h[k])
            i_mid = int(round((self.AT / 2.0) / 0.25))
            col_ok = np.abs(dev[i_mid]) <= 0.6                 # columnas (s) donde la terraza existe
            info = dict(k=k, altura_rel=self.h[k], ok=False, u_lo=None, u_hi=None, u_hi_casa=None,
                        u_calle=ub + u_c0, u_fachada=ub + max(self.u_f0, u_c0 + self.AC / 2.0 + 1.0), u_rampa=None,
                        fondo_max=self.fondo_max, desvio_rampa=0.0, s_ok=[])
            if col_ok.sum() < 5:
                self.b[k] = info
                log('  terraza %d: el terreno de T1 no la aterraza (%d/%d columnas): sin calle ni casas' % (k, int(col_ok.sum()), len(ss)))
                continue
            med = np.median(dev[:, col_ok], axis=1)
            ok_c = (med >= -TOL_BANDA[0]) & (med <= TOL_BANDA[1])
            ok_h = (med >= -TOL_BANDA_CASA[0]) & (med <= TOL_BANDA_CASA[1])
            if not ok_c[i_mid]:
                self.b[k] = info
                log('  terraza %d: centro de banda fuera de tolerancia (mediana %.2f): sin calle' % (k, med[i_mid]))
                continue
            lo = i_mid
            while lo > 0 and ok_c[lo - 1]:
                lo -= 1
            hi = i_mid
            while hi < len(us) - 1 and ok_c[hi + 1]:
                hi += 1
            hc = i_mid
            while hc < len(us) - 1 and ok_h[hc + 1]:
                hc += 1
            u_lo, u_hi, u_hc = float(us[lo]), float(us[hi]), float(us[hc])
            # eje de la calle: el del contrato si su desvio mediano es admisible; si no, el primer u
            # hacia fuera que lo sea (mar: la calle al pie del muro se enterraria en el talud)
            # RONDA 15c: ademas el BORDE interior de la calle (u - 2.25) debe quedar en TOL_BORDE en el 90 % de las
            # columnas (con cell 4 el bordillo / la rampa del muro de T1 se difumina ~2 m dentro de la banda)
            p10 = np.percentile(dev[:, col_ok], 10, axis=1); p90 = np.percentile(dev[:, col_ok], 90, axis=1)
            borde_ok = (p10 >= -TOL_BORDE[0]) & (p90 <= TOL_BORDE[1])
            uc = u_c0
            i_c = int(round(uc / 0.25))
            def _borde(i):
                ib = int(round((us[i] - self.AC / 2.0) / 0.25))
                return 0 <= ib < len(us) and borde_ok[ib]
            while i_c < len(us) - 1 and not (ok_c[i_c] and _borde(i_c)) and us[i_c] < u_c0 + 1.5:
                i_c += 1
            if not (ok_c[i_c] and _borde(i_c)):
                i_c = int(round(u_c0 / 0.25))
                while i_c < len(us) and not ok_c[i_c]:
                    i_c += 1
            uc = max(u_c0, float(us[min(i_c, len(us) - 1)]))
            uf = max(self.u_f0, uc + self.AC / 2.0 + 1.0)
            fmax_ = min(self.fondo_max, ub + u_hc - (ub + uf))
            if self.sube:
                fmax_ = min(fmax_, FONDO_MAX_SUBE)      # v2 (N1-C (3)/C2-14)
            info.update(ok=True, u_lo=ub + u_lo, u_hi=ub + u_hi, u_hi_casa=ub + u_hc, u_calle=ub + uc,
                        u_fachada=ub + uf, fondo_max=fmax_,
                        s_ok=[r3(ss[col_ok][0]), r3(ss[col_ok][-1])],
                        med=[r3(v) for v in med])
            # rampa: ladera -> pegada al borde llano exterior (u_hi); mar -> pegada al borde llano interior (u_lo)
            if self.sube:
                # RONDA 15c: el borde exterior de la rampa sobre el arranque difuminado del muro (u_hi + 0.6: el terreno
                # alli sube < 0.6 m y la rampa ya va subiendo) -> delante queda un solar de >= 4 m de fondo
                info['u_rampa'] = ub + u_hi + 0.6 - ANCHO_RAMPA / 2.0
            else:
                info['u_rampa'] = ub + u_lo + 0.3 + ANCHO_RAMPA / 2.0
                info['desvio_rampa'] = max(0.0, info['u_rampa'] + ANCHO_RAMPA / 2.0 + 0.5 + self.AC / 2.0 - info['u_calle'])
            self.b[k] = info
            log('  terraza %d: banda llana u %.2f..%.2f (casas hasta %.2f), eje calle %.2f, fachada %.2f, fondo max %.1f, s %.0f-%.0f'
                % (k, info['u_lo'], info['u_hi'], info['u_hi_casa'], info['u_calle'], info['u_fachada'], info['fondo_max'],
                   info['s_ok'][0], info['s_ok'][1]))

    # ----- superficie de una rampa (relleno): z por vertice; None si el terreno asoma o hay costura -----
    def z_rampa(self, k, ramp, dr, anotar=False, z_ends=None):
        """Superficie de la rampa (relleno): PENDIENTE RECTA entre sus dos cotas de empalme (pie = calle/travesia
        de la terraza baja, meseta = calle/travesia de la terraza alta), meseta de 5 m a nivel en el extremo alto.
        Devuelve (zr, z_top, z_foot) o None si hay costura o el terreno asoma por encima de la superficie."""
        hk, hk1 = self.h[k], self.h[k + 1]
        d_r = ramp.cum if dr == 1 else (ramp.largo - ramp.cum)      # distancia desde el extremo de la travesia k
        Zr = np.array([self.zxy(x, y) for (x, y) in ramp.xy])
        if np.abs(np.diff(Zr)).max() > SALTO_Z:
            return None
        t_d = (lambda d: d) if dr == 1 else (lambda d: ramp.largo - d)
        if self.sube:
            z_foot = self.zxy(*ramp.punto(t_d(0.0))) + hk + 0.05
            z_top = self.zxy(*ramp.punto(t_d(LARGO_RAMPA + MESETA_RAMPA / 2.0))) + hk1 + 0.05
        else:
            z_top = self.zxy(*ramp.punto(t_d(MESETA_RAMPA / 2.0))) + hk + 0.05
            z_foot = self.zxy(*ramp.punto(t_d(LARGO_RAMPA + MESETA_RAMPA))) + hk1 + 0.05
        if z_ends is not None:
            # cotas EXACTAS de empalme (travesia de la terraza k / calle de la terraza k+1) al construir
            z_top = z_ends[0] if z_ends[0] is not None else z_top
            z_foot = z_ends[1] if z_ends[1] is not None else z_foot
        if self.sube:
            zr = z_foot + (z_top - z_foot) * np.clip(d_r / LARGO_RAMPA, 0.0, 1.0)
        else:
            zr = z_top - (z_top - z_foot) * np.clip((d_r - MESETA_RAMPA) / LARGO_RAMPA, 0.0, 1.0)
        # el terreno no puede asomar por encima de la superficie (eje y dos bordes)
        # RONDA 15c: huella completa cada 1 m (eje, +-ancho/4, +-ancho/2), igual que la QA
        # (calzada: eje, +-1 m y bordes +-2 m <= TOL_RELLENO; linea de los muretes +-2.5 m <= TOL_MURETE)
        dev = self._dev_huella(ramp.xy, None, ANCHO_RAMPA, z_de_t=lambda t: float(np.interp(t, ramp.cum, zr)), fracs=FRACS_RAMPA, modo='malla')
        dd = dev.reshape(-1, len(FRACS_RAMPA))
        peor = float(dd[:, 1:-1].max()); peor_m = float(dd[:, [0, -1]].max())
        if anotar:
            self.anota('rampa', dd[:, 1:-1].ravel())
        if peor > TOL_RELLENO - 0.05 or peor_m > TOL_MURETE - 0.05:
            self.descartes.append('%s rampa t%d k%d: terreno asoma %.2f m (calzada) / %.2f m (muretes)' % (self.id, int(ramp.s[0]), k, peor, peor_m))
            return None
        return zr, z_top, z_foot

    # ----- planificacion de rampas y escaleras (antes de las calles: el lado mar desvia la calle) -----
    # La rampa corre PARALELA a la calle sobre la banda llana de la terraza BAJA (ladera: terraza k,
    # borde exterior; mar: terraza k+1, borde interior) y su pendiente absoluta = (6 +- desnivel de
    # Z(s) en su tramo)/55; se orienta para que la pendiente de la pista RESTE y se descarta si supera
    # el 16 %. En el extremo alto, la meseta (5 m) se prolonga con un CODO a nivel que cruza el talud
    # del muro hasta la calle superior (ladera) o hasta la travesia superior (mar).
    def planificar_rampas(self, s_travs, it0=0, k_solo=None, evitar=None, solo_rampa=False):
        """v1: it0 = indice de la primera travesia; k_solo = solo esa terraza; evitar = poligono a evitar (lo ya
        construido del sector, para el rescate de islas). Devuelve los planes nuevos."""
        total = LARGO_RAMPA + MESETA_RAMPA
        nuevos = []
        evitar = evitar if (evitar is not None and not evitar.is_empty) else None
        for it_, st in enumerate(s_travs):
            it = it0 + it_
            dZ = self.pista.z(st + 30.0) - self.pista.z(st - 30.0)
            dr_pref = (-1 if dZ > 0 else 1) if self.sube else (1 if dZ > 0 else -1)
            for k in range(self.n - 1):
                if k_solo is not None and k != k_solo:
                    continue
                bk, bk1 = self.b[k], self.b[k + 1]
                if not (bk['ok'] and bk1['ok']):
                    continue
                # RONDA 15c: varias posiciones laterales de la rampa (ladera: del arranque del muro hacia dentro; mar:
                # del borde interior hacia fuera) hasta que el terreno no asome; la primera deja casas delante
                u_r0 = bk['u_rampa'] if self.sube else bk1['u_rampa']
                cand_u = [u_r0 + d for d in ((0.0, -0.25, -0.6, -0.9) if self.sube else (0.0, 0.3, 0.6, 1.0))]
                plan = None
                for u_r in cand_u:
                    if plan is not None:
                        break
                    cr = self.curva(u_r)
                    if cr is None:
                        continue
                    tt = cr.t_de_s(st)
                    px, py = cr.punto(tt)
                    if not self.pista.valido(px, py, st, u_r, 1.0):
                        continue
                    for dr in (dr_pref, -dr_pref):
                        if dr == 1 and tt + 2.75 + total > cr.largo - 3.0:
                            continue
                        if dr == -1 and tt - 2.75 - total < 3.0:
                            continue
                        if self.sube:
                            ta, tb = tt + dr * 2.25, tt + dr * (2.25 + total)
                            v0 = tt - dr * 2.25
                        else:
                            ta, tb = tt - dr * 2.75, tt + dr * (2.25 + LARGO_RAMPA)
                            v0 = tt - dr * (2.75 + 0.9)
                        ramp = cr.tramo(min(ta, tb), max(ta, tb))
                        if ramp is None:
                            continue
                        s_near = cr.s_de_t(ta); s_far = cr.s_de_t(tb)
                        desnivel = self.dh + (self.pista.z(s_far) - self.pista.z(s_near)) * self.sg
                        if abs(desnivel) / LARGO_RAMPA > 0.16 or desnivel < 0.5:
                            continue
                        # la terraza destino debe existir (terreno aterrazado) donde la rampa llega a ella
                        s_dest = s_far if self.sube else s_far
                        if bk1['s_ok'] and not (bk1['s_ok'][0] + 8.0 <= s_dest <= bk1['s_ok'][1] - 8.0):
                            continue
                        ok = all(self.pista.valido(x, y, s, u_r, 2.0) for (x, y), s in zip(ramp.xy, ramp.s))
                        pol = franja(ramp, ANCHO_RAMPA)
                        if not ok or pol.intersects(self.ctx['asf6']) or pol.intersects(self.ctx['otros']) or pol.intersects(self.zona_costura(DIST_COSTURA_SOLAR)):
                            continue
                        if evitar is not None and pol.buffer(0.5).intersects(evitar):
                            continue
                        zz = self.z_rampa(k, ramp, dr)
                        if zz is None:
                            continue
                        desnivel = zz[1] - zz[2]
                        esc = self._planificar_escalera(k, dr, v0, cr)
                        if esc is not None:
                            pe = esc['poligono']
                            if pe.intersects(self.ctx['asf6']) or pe.intersects(self.ctx['otros']) or pe.intersection(pol).area > 0.05:
                                esc = None
                            elif evitar is not None and pe.buffer(0.5).intersects(evitar):
                                esc = None
                        s_lo = [float(ramp.s.min())] + ([esc['s_min']] if esc else [])
                        s_hi = [float(ramp.s.max())] + ([esc['s_max']] if esc else [])
                        plan = dict(it=it, st=st, k=k, dr=dr, tt=tt, ramp=ramp, u_r=u_r, desnivel=desnivel, esc=esc,
                                    s_min=min(s_lo), s_max=max(s_hi), ok=False)
                        break
                if plan is None and not solo_rampa:
                    # sin rampa posible: al menos una escalera (la travesia necesita destino)
                    u_r = u_r0; cr = self.curva(u_r)
                    if cr is None:
                        continue
                    tt = cr.t_de_s(st)
                    for dr in (dr_pref, -dr_pref):
                        v0 = tt - dr * (2.25 if self.sube else 3.65)
                        esc = self._planificar_escalera(k, dr, v0, cr)
                        if esc is not None and not (esc['poligono'].intersects(self.ctx['asf6']) or esc['poligono'].intersects(self.ctx['otros'])
                                                    or (evitar is not None and esc['poligono'].buffer(0.5).intersects(evitar))):
                            plan = dict(it=it, st=st, k=k, dr=dr, tt=tt, ramp=None, u_r=u_r, desnivel=0.0, esc=esc,
                                        s_min=esc['s_min'], s_max=esc['s_max'], ok=False)
                            break
                if plan is None:
                    continue
                self.planes.append(plan)
                nuevos.append(plan)
                if self.sube:
                    self.zonas_rampa[k].append((plan['s_min'] - 2.0, plan['s_max'] + 2.0))
                else:
                    self.desvios[k + 1].append((plan['s_min'] - 1.5, plan['s_max'] + 1.5))
                    if plan['ramp'] is not None:
                        # la calle de k+1 se desvia lo que pida la rampa mas exterior de la terraza
                        dv = plan['u_r'] + ANCHO_RAMPA / 2.0 + 0.5 + self.AC / 2.0 - bk1['u_calle']
                        bk1['desvio_rampa'] = max(bk1['desvio_rampa'], dv)
        return nuevos

    def _planificar_escalera(self, k, dr, v0, cr):
        """Escalera junto a la travesia (lado -dr), sobre la banda llana de la terraza baja. Ida y vuelta
        (2 x 5 m) + pasarela a nivel que cruza el talud del muro; si la pista la empina (|dZ| > 1.0 m
        en 5 m), recta perpendicular (solo ladera). Devuelve dict o None."""
        L5 = LARGO_ESCALERA / 2.0; AE = ANCHO_ESCALERA
        bk, bk1 = self.b[k], self.b[k + 1]
        s_v0 = cr.s_de_t(v0)
        if self.sube:
            u_A = bk['u_hi'] - 1.5 * AE; u_B = bk['u_hi'] - 0.5 * AE     # A tramo bajo, B tramo alto (exterior)
            u_pas = (u_B, bk1['u_calle'] - self.AC / 2.0)                 # pasarela: de B al borde de la calle superior
        else:
            u_A = bk1['u_lo'] + 0.5 * AE; u_B = bk1['u_lo'] + 1.5 * AE   # A tramo alto (interior), B tramo bajo
            u_pas = (u_A, bk['u_hi'])                                     # pasarela: de A al final de la travesia k
        cA = self.curva(u_A); cB = self.curva(u_B)
        if cA is not None and cB is not None:
            tA = cA.t_de_s(s_v0); tB = cB.t_de_s(s_v0)
            A = cA.tramo(min(tA, tA - dr * L5), max(tA, tA - dr * L5))
            Bp = cB.tramo(min(tB, tB - dr * L5), max(tB, tB - dr * L5))
            if A is not None and Bp is not None:
                sA0 = cA.s_de_t(tA); sA1 = cA.s_de_t(tA - dr * L5); sA2 = cA.s_de_t(tA - dr * (L5 + AE))
                empina = abs(self.pista.z(sA1) - self.pista.z(sA0))
                u_lo = min(u_A, u_B) - AE / 2.0; u_hi = max(u_A, u_B) + AE / 2.0
                desc = Polygon([self.pista.pos(sA1, self.lado, u_lo), self.pista.pos(sA1, self.lado, u_hi),
                                self.pista.pos(sA2, self.lado, u_hi), self.pista.pos(sA2, self.lado, u_lo)])
                pas = Poli([self.pista.pos(s_v0, self.lado, u_pas[0]), self.pista.pos(s_v0, self.lado, u_pas[1])], [s_v0, s_v0])
                ok = all(self.pista.valido(x, y, s, u_A, 2.0) for (x, y), s in zip(A.xy, A.s))
                ok = ok and all(self.pista.valido(x, y, s, u_B, 2.0) for (x, y), s in zip(Bp.xy, Bp.s))
                if ok and empina <= 1.0:
                    return dict(tipo='idavuelta', A=A, B=Bp, desc=desc, pas=pas, sA0=sA0, sA1=sA1, s_desc=(sA1 + sA2) / 2.0,
                                poligono=union([franja(A, AE), franja(Bp, AE), desc, franja(pas, AE)]),
                                s_min=min(sA0, sA2), s_max=max(sA0, sA2))
        if self.sube:
            # recta perpendicular: 10 m hasta el borde de la calle superior, pegada a la travesia
            s_p = cr.s_de_t(v0 - dr * (AE / 2.0 + 0.3))
            u_in = bk1['u_calle'] - self.AC / 2.0
            pa = self.pista.pos(s_p, self.lado, u_in - LARGO_ESCALERA)
            pb = self.pista.pos(s_p, self.lado, u_in)
            if self.pista.valido(pa[0], pa[1], s_p, u_in - LARGO_ESCALERA, 2.0):
                P = Poli([pa, pb], [s_p, s_p])
                return dict(tipo='recta', P=P, s_p=s_p, poligono=franja(P, AE), s_min=s_p - 1.0, s_max=s_p + 1.0)
        return None

    # ----- z de una calle por vertice (regla) + marcas de corte por terreno real y costuras -----
    def z_calle(self, k, poli):
        # RONDA 15c: z = Zb (la cota de T1) + h_k; el vertice vale si el terreno bajo el EJE y bajo los dos BORDES
        # (+-ancho/2) esta en tolerancia y la calle no se inclina de lado mas de INCL_CALLE; corte entre vertices
        # si la pendiente longitudinal supera PEND_CALLE (talud entre ramas, pliegue)
        z = self.zxys(poli.xy[:, 0], poli.xy[:, 1]) + self.h[k] + 0.05
        dev, dev_m = self._dev_modo(poli.xy[:, 0], poli.xy[:, 1], z, 'ambos')
        ok = (dev >= -TOL_CALLE[0]) & (dev_m <= TOL_CALLE[1])
        # v1: los bordes se miran a +-(ancho/2) y a +-(ancho/2 + 0.6) (bordillo/acera del kit de caminos: el adoquin
        # lleva aceras de 0.8 m y la hierba asomaba en ellas al pie de los muros, revision C-08/F-06)
        for off in (-self.AC / 2.0, self.AC / 2.0, -self.AC / 2.0 - 0.6, self.AC / 2.0 + 0.6):
            ex, ey = [], []
            for i in range(len(poli.xy)):
                T = poli.tangente(float(poli.cum[i]))
                ex.append(poli.xy[i][0] + T[1] * off); ey.append(poli.xy[i][1] - T[0] * off)
            zb_b = self.zxys(ex, ey) + self.h[k] + 0.05
            dv_b, dv_bm = self._dev_modo(ex, ey, z, 'ambos')
            if abs(off) <= self.AC / 2.0 + 1e-6:
                ok &= (dv_b >= -TOL_BORDE[0]) & (dv_bm <= TOL_BORDE[1]) & (np.abs(zb_b - z) <= INCL_CALLE)
            else:
                ok &= dv_bm <= TOL_ACERA
        seg = np.hypot(np.diff(poli.xy[:, 0]), np.diff(poli.xy[:, 1]))
        cortes = np.abs(np.diff(z)) > PEND_CALLE * np.maximum(seg, 0.5)
        return z, ok, cortes, dev

    # ----- calles por terraza (lado mar: desviadas alrededor de las rampas) -----
    def construir_calles(self):
        prohib_base = union([self.ctx['asf_calle'], self.ctx['otros_calles'], self.zona_costura(DIST_COSTURA_EJE)])
        for k in range(self.n):
            bk = self.b[k]
            self.piezas[k] = []
            if not bk['ok']:
                continue
            c1 = self.curva(bk['u_calle'])
            if c1 is None:
                continue
            if self.desvios[k]:
                c2 = self.curva(bk['u_calle'] + bk['desvio_rampa'])
                tramos = []; s_prev = self.s0 - 1
                for (sa, sb) in sorted(self.desvios[k]):
                    tramos.append((c1, s_prev, sa - DESVIO_TRANS, {})); tramos.append((c2, sa, sb, {}))
                    s_prev = sb + DESVIO_TRANS
                tramos.append((c1, s_prev, self.s1 + 1, {}))
                calle = componer_por_s(tramos)
            else:
                calle = c1
            if calle is None:
                continue
            piezas = []
            for pz in calle.recortar(union([prohib_base, self.incoherencia(c1)]), 10.0):
                z, ok, cortes, dev = self.z_calle(k, pz)
                pz.attr['z'] = z; pz.attr['puente'] = np.zeros(len(z))
                self.anota('calle', dev[ok])
                piezas.extend(trocear(pz, ok, cortes, 10.0))
            piezas, uniones = unir_enfrentados(piezas)
            for (xa, ya, xb, yb, hueco, dz) in uniones:
                self.uniones.append(dict(sector=self.id, terraza=k, a=[xa, ya], b=[xb, yb], hueco=hueco, dz=dz))
            piezas = [p for p in piezas if p.largo >= 25.0]
            self.piezas[k] = piezas
            for i, pz in enumerate(piezas):
                self.calles.append(dict(id='%s_calle%d_%d' % (self.id, k, i), terraza=k,
                                        tipo='servicio' if k == 0 else 'terraza', ancho=self.AC,
                                        pts=pz.pts3(pz.attr['z']), s=[r3(v) for v in pz.s],
                                        costura_idx=([int(np.where(pz.attr['puente'] > 0.5)[0][0]), int(np.where(pz.attr['puente'] > 0.5)[0][-1])]
                                                     if (pz.attr['puente'] > 0.5).any() else None)))
                pz.cid = self.calles[-1]['id']
                self.F_calles[pz.cid] = franja(pz, self.AC)

    # ----- bandas de terraza (entre las curvas limpias u_base(k) y u_base(k)+21) -----
    def construir_bandas(self):
        self.bandas = {}
        for k in range(self.n):
            a = self.curva(self.u_base(k)); b = self.curva(self.u_base(k) + self.AT)
            if a is None or b is None:
                self.bandas[k] = Polygon(); continue
            self.bandas[k] = Polygon([tuple(p) for p in a.xy] + [tuple(p) for p in b.xy][::-1]).buffer(0)

    # ----- linea de fachada de la terraza k, con atributos fmax (fondo maximo) y uf (u de la fachada) -----
    def linea_fachada(self, k):
        bk = self.b[k]
        if not bk['ok']:
            return None
        c1 = self.curva(bk['u_fachada'])
        if c1 is None:
            return None
        if (not self.sube) and self.desvios[k]:
            dv = bk['desvio_rampa']
            c2 = self.curva(bk['u_fachada'] + dv)
            normal = {'fmax': bk['fondo_max'], 'uf': bk['u_fachada']}
            desv = {'fmax': min(bk['fondo_max'], bk['u_hi_casa'] - (bk['u_fachada'] + dv)), 'uf': bk['u_fachada'] + dv}
            tramos = []; s_prev = self.s0 - 1
            for (sa, sb) in sorted(self.desvios[k]):
                tramos.append((c1, s_prev, sa - DESVIO_TRANS, normal)); tramos.append((c2, sa, sb, desv))
                s_prev = sb + DESVIO_TRANS
            tramos.append((c1, s_prev, self.s1 + 1, normal))
            return componer_por_s(tramos, atributos=['fmax', 'uf'])
        # RONDA 15c: el fondo solo se reduce frente a lo CONSTRUIDO (antes tambien frente a rampas planificadas y
        # descartadas: tramos de 60 m sin casas): rampa -> hasta su relleno (+0.65); escalera -> hasta su tramo interior
        zonas = []
        for plan in self.planes:
            # (solo ladera: en el mar la rampa y la escalera van sobre la terraza k+1 y su calle se desvia)
            if not self.sube or plan['k'] != k or not plan.get('ids'):
                continue
            if plan.get('ok') and plan.get('ramp') is not None:
                # v1 (D7): tramo BAJO (pie, <= 1 m sobre las casas de delante) con el hueco de siempre; tramo ALTO (resto,
                # meseta y codo) a GAP_RAMPA_ALTO: delante no cabe ninguna casa (queda el patio libre)
                ramp, dr = plan['ramp'], plan['dr']
                t_d = (lambda d, r=ramp, dr=dr: d if dr == 1 else r.largo - d)
                s_pie = ramp.s_de_t(t_d(0.0)); s_baja = ramp.s_de_t(t_d(D_RAMPA_BAJA)); s_fin = ramp.s_de_t(t_d(ramp.largo))
                sg_ = 1.0 if s_fin >= s_pie else -1.0
                f_r = plan['u_r'] - ANCHO_RAMPA / 2.0 - GAP_RAMPA - bk['u_fachada']
                f_alto = plan['u_r'] - ANCHO_RAMPA / 2.0 - GAP_RAMPA_ALTO - bk['u_fachada']
                a_, b_ = s_pie - 3.0 * sg_, s_baja
                zonas.append((min(a_, b_), max(a_, b_), f_r))
                a_, b_ = s_baja, s_fin + MARGEN_S_RAMPA * sg_
                zonas.append((min(a_, b_), max(a_, b_), f_alto))
            if plan.get('esc') is not None:
                e = plan['esc']
                f_e = (bk['u_hi'] - 2.0 * ANCHO_ESCALERA) - GAP_ESC_ATRAS - bk['u_fachada']
                zonas.append((e['s_min'] - 2.0, e['s_max'] + 2.0, f_e))
        fmax = np.array([min([bk['fondo_max']] + [f for (sa, sb, f) in zonas if sa <= s <= sb]) for s in c1.s])
        return Poli(c1.xy, c1.s, {'fmax': fmax, 'uf': np.full(len(c1.s), bk['u_fachada']), 'zr': np.array(
            [1.0 if any(sa <= s <= sb for (sa, sb, f) in zonas) else 0.0 for s in c1.s])})

    def plan_de(self, it, k):
        for p in self.planes:
            if p['it'] == it and p['k'] == k:
                return p
        return None

    # ----- enlaces de la via de servicio con la pista + valla cerrada -----
    def construir_enlaces(self):
        """Enlace (+ valla cerrada) entre la pista y CADA extremo de cada trozo de la via de servicio. RONDA 15c: si en el
        extremo no cabe (costura del terreno, otro elemento, terreno), se prueba 4..24 m hacia dentro y la calle se RECORTA.
        v1 (revision B4/C-01/D1/F-02/G5): antes el eje iba de la calle (6 m dentro) a pista.pos(s_p, 0.3) casi PARALELO a la
        pista y la cinta (4.5 m + bordillos) entraba 1.8-2.2 m en el asfalto, hasta +0.5 m sobre la calzada. Ahora el enlace
        PROLONGA la calle 3 m mas alla de su extremo y gira 90 grados: tramo final PERPENDICULAR al borde (boca recta).
        Eje = [p1 extremo de la calle (su cota), pq (s_p, eje de la calle, cota de la calle), pb (s_p, u = bordillo_hasta,
        cota de la calle: empalma con la acera alta de construir_pista), p0 (s_p, u >= U_BOCA_ENLACE, z_borde + 0.03)].
        La franja con los bordillos del kit (ancho/2 + 0.25) queda a >= 0.25 m del asfalto (QA 'enlace_asfalto') y nada
        se solapa con la calle (sin z-fighting)."""
        piezas = self.piezas.get(0, [])
        if not piezas:
            return
        asf = self.ctx['asfalto']
        BORD = float(self.spec.get('bordillo_hasta', 1.5))
        h_med = self.AC / 2.0 + 0.25                  # semiancho real del kit de caminos (asfalto: bordillo de 0.25)
        for i, pz in enumerate(list(piezas)):
            for lado_e in ('inicio', 'fin'):
                extremo = (lado_e if (i == 0 and lado_e == 'inicio') or (i == len(piezas) - 1 and lado_e == 'fin')
                           else '%s%d' % (lado_e, i))
                hecho = None; reserva = None
                sg_s = 1.0 if pz.s[-1] > pz.s[0] else -1.0
                for d in np.arange(0.0, 24.01, 2.0):          # v2 (N3-F): cada 2 m (antes 4): la calle se recorta lo minimo
                    if pz.largo < 25.0 + d:
                        break
                    t_e = d if lado_e == 'inicio' else pz.largo - d
                    s_e = pz.s_de_t(t_e)
                    s_p = s_e - 3.0 * sg_s if lado_e == 'inicio' else s_e + 3.0 * sg_s
                    p1 = pz.punto(t_e)
                    fr = self.pista.frame(s_e)
                    u_e = self.lado * ((p1[0] - fr['x']) * fr['nx'] + (p1[1] - fr['y']) * fr['ny']) - fr['w'] / 2.0
                    z1 = float(np.interp(t_e, pz.cum, pz.attr['z']))
                    pq = self.pista.pos(s_p, self.lado, u_e); zq = self.zxy(*pq) + self.h[0] + 0.05
                    pb = self.pista.pos(s_p, self.lado, BORD)
                    z0 = self.pista.z_borde(s_p, self.lado) + 0.03
                    # v2 (revision N3-F): en 12 de 22 enlaces la boca subia/bajaba 0.6-1.3 m en 1.1 m (rampas del 92-120 %: por
                    # ahi no entra ningun coche) porque en los extremos del sector la terraza se aparta de Z(s): se prueba mas
                    # hacia dentro (4..24 m) hasta que el desnivel calle -> borde de la pista sea <= DZ_BOCA_ENLACE; si no hay
                    # ninguno, el de menor desnivel con <= DZ_BOCA_MAX
                    if abs(zq - z0) > DZ_BOCA_MAX:
                        continue
                    u0 = U_BOCA_ENLACE
                    for _ in range(3):
                        p0 = self.pista.pos(s_p, self.lado, u0)
                        pts = [p1, pq, pb, p0]
                        poly = LineString(pts).buffer(h_med, cap_style='flat', join_style='mitre')
                        dist = poly.distance(asf)
                        if dist >= 0.25:
                            break
                        u0 += 0.25 - dist + 0.05
                    if dist < 0.2 or u0 > BORD - 0.4:
                        continue
                    if poly.intersects(self.ctx['otros']) or LineString(pts).intersects(self.zona_costura(DIST_COSTURA_EJE)):
                        continue
                    # terreno: tramo a la cota de la calle (p1 -> pq -> pb) dentro de tolerancia (envolventes de la malla)
                    qs = [((p1[0] + pq[0]) / 2.0, (p1[1] + pq[1]) / 2.0), pq, ((pq[0] + pb[0]) / 2.0, (pq[1] + pb[1]) / 2.0)]
                    zz = np.array([(z1 + zq) / 2.0, zq, zq])
                    dv_, dv_m = self._dev_modo([q[0] for q in qs], [q[1] for q in qs], zz, 'ambos')
                    if dv_.min() < -TOL_CALLE[0] or dv_m.max() > TOL_CALLE[1]:
                        continue
                    cand = (d, t_e, s_p, [p1, pq, pb, p0], [z1, zq, zq, z0], poly, float(dv_m.max()))
                    if abs(zq - z0) <= DZ_BOCA_ENLACE:
                        hecho = cand
                        break
                    if reserva is None or abs(zq - z0) < abs(reserva[4][1] - reserva[4][3]):
                        reserva = cand
                if hecho is None and reserva is not None:
                    hecho = reserva
                    self.descartes.append('%s enlace %s: desnivel de boca %.2f m (ninguna posicion con <= %.2f m en 24 m)'
                                          % (self.id, extremo, reserva[4][1] - reserva[4][3], DZ_BOCA_ENLACE))
                if hecho is None:
                    self.descartes.append('%s enlace %s: no cabe en 24 m desde el extremo con desnivel de boca <= %.1f m (fondo de saco)'
                                          % (self.id, extremo, DZ_BOCA_MAX))
                    continue
                d, t_e, s_p, pts, zs, poly, dev_m = hecho
                if d > 0.0:
                    nueva = pz.tramo(t_e, pz.largo) if lado_e == 'inicio' else pz.tramo(0.0, t_e)
                    if nueva is not None:
                        nueva.cid = pz.cid
                        for c in self.calles:
                            if c['id'] == pz.cid:
                                c['pts'] = nueva.pts3(nueva.attr['z']); c['s'] = [r3(v) for v in nueva.s]
                                pu = nueva.attr.get('puente')
                                c['costura_idx'] = ([int(np.where(pu > 0.5)[0][0]), int(np.where(pu > 0.5)[0][-1])]
                                                    if pu is not None and (pu > 0.5).any() else None)
                        self.F_calles[pz.cid] = franja(nueva, self.AC)
                        piezas[piezas.index(pz)] = nueva
                        pz = nueva
                        self.descartes.append('%s enlace %s: desplazado %.0f m hacia dentro (calle recortada)' % (self.id, extremo, float(d)))
                self.anota('enlace', [dev_m])
                eid = '%s_enlace_%s' % (self.id, extremo)
                self.enlaces.append(dict(id=eid, extremo=extremo, ancho=self.AC, desnivel_boca=r3(zs[1] - zs[3]),
                                         pts=[[r3(p[0]), r3(p[1]), r3(z)] for p, z in zip(pts, zs)]))
                p1, pq, pb, p0 = pts
                ux, uy = pq[0] - p0[0], pq[1] - p0[1]; L = math.hypot(ux, uy) or 1.0
                ux, uy = ux / L, uy / L
                pv = self.pista.pos(s_p, self.lado, 2.6)
                self.vallas.append(dict(x=r3(pv[0]), y=r3(pv[1]), z=r3(zs[1]), rot_z=r3(math.atan2(uy, ux) + math.pi / 2),
                                        largo=5.0, enlace=eid))
                self.F_propio.append(poly.buffer(0.8))
        self.piezas[0] = piezas

    # ----- travesias: geometria sin efectos (calle k -> borde llano de la terraza) -----
    def _travesia_geom(self, it, st, k, ultima):
        bk = self.b[k]
        if not bk['ok']:
            return None
        fr = self.pista.frame(st)
        n_out = (self.lado * fr['nx'], self.lado * fr['ny'])
        ua = bk['u_calle'] + (bk['desvio_rampa'] if self.desviada(k, st) else 0.0)
        pa = self.pista.pos(st, self.lado, ua)
        if not self.pista.valido(pa[0], pa[1], st, ua, 1.5):
            return None
        if dist_a_piezas(self.piezas.get(k, []), pa[0], pa[1]) > 4.0:
            return None
        z = self.zxy(pa[0], pa[1]) + self.h[k] + 0.05
        # RONDA 15c: el final de la travesia se busca hacia dentro desde el borde llano medido u_hi (k < n-1: como
        # mucho 1.5 m, ahi arranca la rampa/escalera; ultima terraza: hasta 6 m de la calle) y la HUELLA COMPLETA
        # (eje y dos bordes cada 1 m) debe quedar a <= TOL_HUELLA del terreno; si no, se acorta o no se construye
        ub = None; dev = None
        u_min = (bk['u_hi'] - 1.5) if not ultima else (ua + 6.0)
        for u in np.arange(bk['u_hi'], u_min - 1e-6, -0.25):
            q = self.pista.pos(st, self.lado, u)
            if not self.pista.valido(q[0], q[1], st, u, 1.5):
                continue
            d_h, d_hm = self._dev_huella([pa, q], z, self.AC, modo='ambos')
            if d_h.min() >= -TOL_HUELLA and d_hm.max() <= TOL_HUELLA:
                ub = float(u); dev = np.where(d_hm > 0.0, d_hm, d_h); break
        if ub is None:
            self.descartes.append('%s travesia s %.0f terraza %d: la huella no cabe sobre el terreno (u %.1f..%.1f)' % (self.id, st, k, u_min, bk['u_hi']))
            return None
        pb = self.pista.pos(st, self.lado, ub)
        ln = LineString([pa, pb]); pol = ln.buffer(self.AC / 2.0, cap_style='flat')
        if pol.intersects(self.ctx['asf_calle']) or pol.intersects(self.ctx['otros']):
            return None
        if ln.intersects(self.zona_costura(DIST_COSTURA_EJE)):
            self.descartes.append('%s travesia s %.0f terraza %d: costura del terreno a < %.1f m del eje' % (self.id, st, k, DIST_COSTURA_EJE))
            return None
        return dict(pa=pa, pb=pb, ua=ua, ub=ub, pol=pol, z=z, n_out=n_out, dev=dev, st=st)

    def _poner_travesia(self, it, k, g, ultima):
        st = g['st']; pa = g['pa']; pb = g['pb']; z = g['z']
        self.travesias.append(dict(id='%s_trav%d_t%d' % (self.id, it, k), s=r3(st), terraza=k, ancho=self.AC,
                                   pts=[[r3(pa[0]), r3(pa[1]), r3(z)], [r3(pb[0]), r3(pb[1]), r3(z)]]))
        self.anota('travesia', g['dev'])
        self.F_propio.append(g['pol'].buffer(GAP_CALLE_SOLAR))
        if ultima:
            pc = self.pista.pos(st, self.lado, self.u_base(k) + self.AT)
            self.cortes[k].append(LineString([pb, pc]).buffer(self.AC / 2.0 + 0.5))
            ps = self.pista.pos(st, self.lado, g['ub'] - 1.5)
            self.salidas.append(dict(id='%s_salida%d' % (self.id, it), x=r3(ps[0]), y=r3(ps[1]), z=r3(z),
                                     dx=r3(g['n_out'][0]), dy=r3(g['n_out'][1]), s=r3(st), travesia=it))

    # Una travesia de la terraza k < n-1 solo se construye si tiene destino: rampa o escalera a k+1.
    def construir_travesias(self, s_travs, geoms):
        for it, st in enumerate(s_travs):
            for k in range(self.n):
                ultima = (k == self.n - 1)
                if not ultima:
                    g = geoms.get((it, k))
                    if g is None:
                        continue
                    plan = self.plan_de(it, k)
                    con_rampa = plan is not None and plan.get('ok')
                    con_esc = any(e['id'] == '%s_esc%d_t%d' % (self.id, it, k) for e in self.escaleras)
                    if not (con_rampa or con_esc):
                        self.descartes.append('%s travesia %d terraza %d: sin rampa ni escalera (no se construye)' % (self.id, it, k))
                        continue
                    self._poner_travesia(it, k, g, False)
                    continue
                for ds in (0, 8, -8, 16, -16, 24, -24, 32, -32, 40, -40):
                    if it in self.it_rescate:
                        break
                    g = self._travesia_geom(it, st + ds, k, True)
                    if g is None:
                        continue
                    estructuras = [LineString([q[:2] for q in e['pts']]).buffer(e['ancho'] / 2.0 + 1.0)
                                   for e in self.travesias + self.rampas + self.enlaces]
                    if estructuras and g['pol'].intersects(union(estructuras)):
                        continue
                    self._poner_travesia(it, k, g, True)
                    break

    # ----- caras libres de un relleno: polilinea con z_base = terreno, z_top = superficie -----
    def _cara(self, pts_xy, sup):
        out = []
        for (x, y) in pts_xy:
            zb = self.terreno.z_malla(x, y); zt = sup(x, y)
            out.append([r3(x), r3(y), r3(min(zb, zt)), r3(zt)])
        return dict(pts=out)

    def _linea_u(self, s_a, s_b, u, paso=2.0):
        n = max(2, int(abs(s_b - s_a) / paso) + 1)
        return [self.pista.pos(s, self.lado, u) for s in np.linspace(s_a, s_b, n)]

    def _linea_s(self, s, u_a, u_b, paso=2.0):
        n = max(2, int(abs(u_b - u_a) / paso) + 1)
        return [self.pista.pos(s, self.lado, u) for u in np.linspace(u_a, u_b, n)]

    def _relleno_ok(self, poly, z_top, tipo):
        # el terreno bajo un relleno a nivel (codo, pasarela, descansillo) no puede asomar
        xs = []; ys = []
        minx, miny, maxx, maxy = poly.bounds
        for x in np.arange(minx, maxx + 0.5, 1.0):
            for y in np.arange(miny, maxy + 0.5, 1.0):
                if poly.contains(Point(x, y)):
                    xs.append(x); ys.append(y)
        if not xs:
            c = poly.centroid; xs = [c.x]; ys = [c.y]
        dev = self.terreno.zs_malla(xs, ys) - z_top
        self.anota(tipo, dev)
        return float(dev.max()) <= TOL_RELLENO

    def _z_en_piezas(self, piezas, p):
        mejor = (1e9, None)
        for pz in piezas:
            d = pz.line.distance(Point(p))
            if d < mejor[0]:
                mejor = (d, float(np.interp(pz.t_de_xy(p[0], p[1]), pz.cum, pz.attr['z'])))
        return mejor[1]

    # ----- rampas (relleno sobre la banda llana de la terraza baja + codo a nivel hasta la calle o la
    #       travesia superior) y escaleras de ida y vuelta (+ pasarela) o rectas -----
    def construir_rampas(self, geoms, planes=None):
        for plan in (self.planes if planes is None else planes):
            it, k, dr = plan['it'], plan['k'], plan['dr']
            plan['ok'] = False
            g = geoms.get((it, k))
            if g is None:
                self.descartes.append('%s rampa/escalera travesia %d terraza %d: la travesia no cabe' % (self.id, it, k))
                continue
            bk, bk1 = self.b[k], self.b[k + 1]
            hk, hk1 = self.h[k], self.h[k + 1]
            u_muro = self.u_base(k) + self.AT
            plan['F'] = []; plan['cortes'] = []; plan['ids'] = []; plan['p_k'] = []
            ramp = plan['ramp']
            if ramp is not None:
                u_r = plan['u_r']
                # cotas de empalme: ladera pie = travesia k, meseta = calle k+1 en el final del codo; mar meseta = travesia k,
                # pie = calle k+1 (desviada) frente al pie
                d_top0 = LARGO_RAMPA + MESETA_RAMPA / 2.0 if self.sube else MESETA_RAMPA / 2.0
                t_d0 = (lambda d: d) if dr == 1 else (lambda d: ramp.largo - d)
                s_top0 = ramp.s_de_t(t_d0(d_top0))
                if self.sube:
                    p_fin0 = self.pista.pos(s_top0, self.lado, bk1['u_calle'])
                    z_ends = (self._z_en_piezas(self.piezas.get(k + 1, []), p_fin0), g['z'])
                else:
                    s_foot0 = ramp.s_de_t(t_d0(LARGO_RAMPA + MESETA_RAMPA))
                    pc0 = self.pista.pos(s_foot0, self.lado, bk1['u_calle'] + bk1['desvio_rampa'])
                    z_ends = (g['z'], self._z_en_piezas(self.piezas.get(k + 1, []), pc0))
                zz = self.z_rampa(k, ramp, dr, anotar=True, z_ends=z_ends)
                zr = zz[0] if zz is not None else None
                d_r = ramp.cum if dr == 1 else (ramp.largo - ramp.cum)
                t_d = (lambda d: d) if dr == 1 else (lambda d: ramp.largo - d)
                d_top = LARGO_RAMPA + MESETA_RAMPA / 2.0 if self.sube else MESETA_RAMPA / 2.0
                i_top = int(np.argmin(np.abs(d_r - d_top)))
                s_top = ramp.s_de_t(t_d(d_top)); z_top = zz[1] if zz is not None else None
                p_top = ramp.punto(t_d(d_top))
                if self.sube:
                    u_fin = bk1['u_calle']; u_in = bk1['u_calle'] - self.AC / 2.0
                else:
                    u_fin = g['ub']; u_in = g['ub']
                p_fin = self.pista.pos(s_top, self.lado, u_fin)
                pol_codo = LineString([p_top, p_fin]).buffer(MESETA_RAMPA / 2.0, cap_style='flat')
                motivo = None
                if zr is None:
                    motivo = 'terreno asoma sobre la rampa'
                elif self.sube:
                    pz_sup = self.piezas.get(k + 1, [])
                    if dist_a_piezas(pz_sup, p_fin[0], p_fin[1]) > 3.0:
                        motivo = 'sin calle superior al final del codo'
                    elif abs(self._z_en_piezas(pz_sup, p_fin) - z_top) > 0.4:
                        motivo = 'cota de la calle superior no coincide con la meseta'
                else:
                    s_foot = ramp.s_de_t(t_d(LARGO_RAMPA + MESETA_RAMPA))
                    pc = self.pista.pos(s_foot, self.lado, bk1['u_calle'] + bk1['desvio_rampa'])
                    plan['pc_mar'] = pc
                    if abs(g['z'] - z_top) > 0.4:
                        motivo = 'cota de la travesia superior no coincide con la meseta'
                    elif dist_a_piezas(self.piezas.get(k + 1, []), pc[0], pc[1]) > 4.5:
                        motivo = 'sin calle inferior al pie'
                if motivo is None:
                    z_foot = zz[2]
                    z_ref = g['z'] if self.sube else self._z_en_piezas(self.piezas.get(k + 1, []), plan['pc_mar'])
                    if z_ref is None or abs(z_ref - z_foot) > 0.4:
                        motivo = 'cota del pie (%.2f) no coincide con la calle/travesia de llegada (%s)' % (z_foot, z_ref)
                if motivo is None and not self._relleno_ok(pol_codo, z_top, 'codo'):
                    motivo = 'terreno asoma bajo el codo'
                if motivo is not None:
                    self.descartes.append('%s rampa travesia %d terraza %d: %s' % (self.id, it, k, motivo))
                    ramp = None
            if ramp is not None:
                plan['ok'] = True
                s_a, s_b = float(ramp.s.min()), float(ramp.s.max())
                u_w0, u_w1 = (u_r + ANCHO_RAMPA / 2.0, u_muro) if self.sube else (u_muro, u_r - ANCHO_RAMPA / 2.0)
                hueco = Polygon(self._linea_u(s_a, s_b, u_w0) + self._linea_u(s_b, s_a, u_w1)).buffer(0)
                relleno = union([franja(ramp, ANCHO_RAMPA), hueco, pol_codo]).buffer(0)
                if relleno.intersects(self.ctx['otros']):
                    self.descartes.append('%s rampa travesia %d terraza %d: el relleno o el codo entran en otro elemento / zona excluida' % (self.id, it, k))
                    plan['ok'] = False
                    ramp = None
            if ramp is not None:
                # v1 (D7): tramo ALTO del relleno (> 1 m sobre la terraza baja): todo salvo los primeros D_RAMPA_BAJA m desde
                # el pie (con su hueco hasta el muro); construir_solares no pone casas de la terraza k a < GAP_RAMPA_ALTO
                if self.sube:
                    t_pie = t_d(0.0); t_b = t_d(D_RAMPA_BAJA)
                    pie = ramp.tramo(min(t_pie, t_b), max(t_pie, t_b))
                    ancho_pie = 2.0 * abs(u_muro - u_r) + 2.0
                    plan['alto'] = relleno.difference(franja(pie, ancho_pie)) if pie is not None else relleno
                    plan['altos'] = [(k, plan['alto'])]
                else:
                    # v3 (revision D7): en los sectores que BAJAN la regla no existia: el muro de la rampa (con su pretil de
                    # 0.9 m) pasaba a 1.4-1.5 m del costado de casas de la terraza k, 0.5-1.1 m por encima de su planta baja.
                    # Tramo ALTO para las casas de la terraza k: meseta y codo y los vertices cuya calzada queda a menos de
                    # 0.4 m bajo su suelo (pretil >= 0.5 m sobre el); para las de la terraza k+1: todo lo que va > 0.5 m sobre
                    # su suelo. Delante no se ponen casas a < GAP_RAMPA_ALTO (construir_solares)
                    zb_v = np.array([self.zxy(x, y) for (x, y) in ramp.xy])
                    ancho_seg = 2.0 * abs(u_muro - u_r) + 2.0 * ANCHO_RAMPA
                    def _seg(m, ramp=ramp, relleno=relleno, ancho_seg=ancho_seg):
                        if not m.any():
                            return Polygon()
                        tr_ = ramp.tramo(float(ramp.cum[m].min()), float(ramp.cum[m].max()))
                        return relleno.intersection(franja(tr_, ancho_seg)) if tr_ is not None else Polygon()
                    alto_k = union([_seg(np.asarray(zr) > zb_v + hk - 0.4), pol_codo.intersection(relleno.buffer(0.5))])
                    alto_k1 = _seg(np.asarray(zr) > zb_v + hk1 + 0.5)
                    plan['alto'] = union([alto_k, alto_k1])
                    plan['altos'] = [(k, alto_k), (k + 1, alto_k1)]
                def sup(x, y, ramp=ramp, zr=zr):
                    return float(np.interp(ramp.t_de_xy(x, y), ramp.cum, zr))
                caras = []
                if self.sube:
                    s_foot = ramp.s_de_t(t_d(0.0)); s55 = ramp.s_de_t(t_d(LARGO_RAMPA)); s60 = ramp.s_de_t(t_d(LARGO_RAMPA + MESETA_RAMPA))
                    ci = self.curva(u_r - ANCHO_RAMPA / 2.0)
                    lat = ci.tramo(min(ci.t_de_s(s_foot), ci.t_de_s(s60)), max(ci.t_de_s(s_foot), ci.t_de_s(s60))) if ci is not None else None
                    if lat is not None:
                        caras.append(self._cara([tuple(p) for p in lat.xy], sup))
                    caras.append(self._cara(self._linea_s(s60, u_r - ANCHO_RAMPA / 2.0, u_in), sup))
                    caras.append(self._cara(self._linea_s(s55, u_r + ANCHO_RAMPA / 2.0, u_in), sup))
                else:
                    s0_ = ramp.s_de_t(t_d(0.0)); s5 = ramp.s_de_t(t_d(MESETA_RAMPA)); s_foot = ramp.s_de_t(t_d(LARGO_RAMPA + MESETA_RAMPA))
                    co = self.curva(u_r + ANCHO_RAMPA / 2.0)
                    lat = co.tramo(min(co.t_de_s(s0_), co.t_de_s(s_foot)), max(co.t_de_s(s0_), co.t_de_s(s_foot))) if co is not None else None
                    if lat is not None:
                        caras.append(self._cara([tuple(p) for p in lat.xy], sup))
                    caras.append(self._cara(self._linea_s(s0_, u_in, u_r + ANCHO_RAMPA / 2.0), sup))
                    caras.append(self._cara(self._linea_s(s5, u_in, u_muro), sup))
                orden = np.argsort(d_r)
                eje = [[r3(ramp.xy[i][0]), r3(ramp.xy[i][1]), r3(zr[i])] for i in orden if d_r[i] <= d_top + 1e-6] if self.sube \
                    else [[r3(ramp.xy[i][0]), r3(ramp.xy[i][1]), r3(zr[i])] for i in orden if d_r[i] >= d_top - 1e-6]
                codo = [r3(p_fin[0]), r3(p_fin[1]), r3(z_top)]
                eje = eje + [codo] if self.sube else [codo] + eje
                rid = '%s_rampa%d_t%d' % (self.id, it, k)
                self.rampas.append(dict(id=rid, s_travesia=r3(plan['st']), de_terraza=k, a_terraza=k + 1, ancho=ANCHO_RAMPA,
                                        ancho_calzada=ANCHO_RAMPA - 1.0, pendiente=r3((z_top - zz[2]) / LARGO_RAMPA), direccion_s=dr,
                                        pts=eje, relleno=[[r3(x), r3(y)] for x, y in list(relleno.exterior.coords)] if hasattr(relleno, 'exterior') else [],
                                        muros_rampa=caras))
                plan['F'].append(relleno.buffer(0.6)); plan['cortes'].append(pol_codo.buffer(0.5)); plan['ids'].append(rid)
                # punto del lado de la terraza k+1: ladera = final del codo (eje de la calle superior); mar = punto de la
                # calle inferior desviada frente al pie de la rampa
                plan['p_k'].append(eje[-1][:2] if self.sube else plan['pc_mar'])
                self.F_propio.append(plan['F'][-1])
                self.cortes[k].append(plan['cortes'][-1])
            # escaleras: ida y vuelta (A junto a la travesia sube/baja 3 m al descansillo, B vuelve y llega al otro
            # nivel) + pasarela a nivel que cruza el talud del muro; o recta perpendicular (ladera)
            esc = plan['esc']
            if esc is None:
                continue
            L5 = LARGO_ESCALERA / 2.0; AE = ANCHO_ESCALERA; sg = self.sg
            if esc['tipo'] == 'idavuelta':
                A = esc['A']; Bp = esc['B']
                dA = (A.largo - A.cum) if dr == 1 else A.cum
                dB = (Bp.largo - Bp.cum) if dr == 1 else Bp.cum
                ZA = np.array([self.zxy(x, y) for (x, y) in A.xy]); ZB = np.array([self.zxy(x, y) for (x, y) in Bp.xy])
                # cotas de empalme EXACTAS: lado de la travesia k (z_trav) y lado de la calle k+1 (z_far)
                pas = esc['pas']
                z_trav = g['z']
                if self.sube:
                    z_far = self._z_en_piezas(self.piezas.get(k + 1, []), tuple(pas.xy[-1]))
                else:
                    i_fin = int(np.argmax(dB)); pb_ = Bp.xy[i_fin]
                    z_far = self._z_en_piezas(self.piezas.get(k + 1, []), self.pista.pos(self.s_cerc(pb_[0], pb_[1]), self.lado, bk1['u_calle'] + bk1['desvio_rampa']))
                # v2 (revision D2-02): la escalera solo vale si al final de la pasarela (ladera) o al pie del tramo B (mar) hay
                # calle de la terraza k+1 (antes, sin calle, se inventaba z_trav + dh y quedaba una escalera blanca a ninguna parte)
                if self.sube:
                    d_dest = dist_a_piezas(self.piezas.get(k + 1, []), *tuple(pas.xy[-1])) - self.AC / 2.0
                else:
                    d_dest = dist_a_piezas(self.piezas.get(k + 1, []), *self.pista.pos(self.s_cerc(pb_[0], pb_[1]), self.lado, bk1['u_calle'] + bk1['desvio_rampa']))
                if z_far is None or d_dest > 1.0:
                    self.descartes.append('%s escalera travesia %d terraza %d: sin calle de la terraza %d al final (a %.1f m): no se pone'
                                          % (self.id, it, k, k + 1, d_dest))
                    plan['esc'] = None
                    continue
                if abs((z_far - z_trav) - sg * self.dh) > 1.5:
                    z_far = z_trav + sg * self.dh
                zA = z_trav + (z_far - z_trav) * 0.5 * np.clip(dA / L5, 0.0, 1.0)
                zB = z_trav + (z_far - z_trav) * (0.5 + 0.5 * np.clip(1.0 - dB / L5, 0.0, 1.0))
                z_desc = z_trav + 0.5 * (z_far - z_trav)
                desc_poly = esc['desc']
                desc = [[r3(x), r3(y), r3(z_desc)] for x, y in list(desc_poly.exterior.coords)[:4]]
                def orden(po, zz, desde_travesia):
                    pts = [[r3(x), r3(y), r3(z)] for (x, y), z in zip(po.xy, zz)]
                    d = (po.largo - po.cum) if dr == 1 else po.cum
                    return pts if (d[0] < d[-1]) == desde_travesia else pts[::-1]
                tramos = [dict(pts=orden(A, zA, True)), dict(pts=orden(Bp, zB, False))]
                z_pas = z_far if self.sube else z_trav
                pasarela = [[r3(x), r3(y), r3(z_pas)] for (x, y) in pas.xy]
                dev_A = self.terreno.zs_malla(A.xy[:, 0], A.xy[:, 1]) - zA; dev_B = self.terreno.zs_malla(Bp.xy[:, 0], Bp.xy[:, 1]) - zB
                self.anota('escalera', np.concatenate([dev_A, dev_B]))
                ok = dev_A.max() <= TOL_RELLENO and dev_B.max() <= TOL_RELLENO
                ok = ok and self._relleno_ok(desc_poly, z_desc, 'escalera') and self._relleno_ok(franja(pas, AE), z_pas, 'pasarela')
                if ok and abs(np.ptp(np.concatenate([ZA, ZB]))) > SALTO_Z + 1.0:
                    ok = False
                corte = franja(pas, AE).buffer(0.5)
            else:
                P = esc['P']
                z0 = g['z']
                z1 = self._z_en_piezas(self.piezas.get(k + 1, []), tuple(P.xy[1]))
                d_dest = dist_a_piezas(self.piezas.get(k + 1, []), *tuple(P.xy[1])) - self.AC / 2.0
                if z1 is None or d_dest > 1.0:          # v2 (D2-02): sin calle superior al final, no hay escalera
                    self.descartes.append('%s escalera recta travesia %d terraza %d: sin calle de la terraza %d al final (a %.1f m): no se pone'
                                          % (self.id, it, k, k + 1, d_dest))
                    plan['esc'] = None
                    continue
                if abs((z1 - z0) - self.dh) > 1.5:
                    z1 = z0 + self.dh
                tramos = [dict(pts=[[r3(P.xy[0][0]), r3(P.xy[0][1]), r3(z0)], [r3(P.xy[1][0]), r3(P.xy[1][1]), r3(z1)]])]
                desc = None; pasarela = None
                fs = np.linspace(0.0, 1.0, 8)
                xs = P.xy[0][0] + (P.xy[1][0] - P.xy[0][0]) * fs; ys = P.xy[0][1] + (P.xy[1][1] - P.xy[0][1]) * fs
                dev = self.terreno.zs_malla(xs, ys) - (z0 + (z1 - z0) * fs)
                self.anota('escalera', dev)
                ok = dev.max() <= TOL_RELLENO
                corte = Point(P.xy[1][0], P.xy[1][1]).buffer(1.8)
            if not ok:
                self.descartes.append('%s escalera travesia %d terraza %d: el terreno asoma' % (self.id, it, k))
                plan['esc'] = None
                continue
            eid = '%s_esc%d_t%d' % (self.id, it, k)
            self.escaleras.append(dict(id=eid, tipo=esc['tipo'], ancho=AE,
                                       de_terraza=k, a_terraza=k + 1, tramos=tramos, descansillo=desc, pasarela=pasarela))
            plan['F'].append(esc['poligono'].buffer(GAP_ESC)); plan['cortes'].append(corte); plan['ids'].append(eid)
            if self.sube:
                plan['p_k'].append(pasarela[-1][:2] if pasarela else tramos[-1]['pts'][-1][:2])
            else:
                pb_ = tramos[-1]['pts'][-1]
                plan['p_k'].append(self.pista.pos(self.s_cerc(pb_[0], pb_[1]), self.lado, bk1['u_calle'] + bk1['desvio_rampa']))
            self.F_propio.append(plan['F'][-1])
            self.cortes[k].append(plan['cortes'][-1])

    # ----- muros de contencion en u = 21(k+1), cortados en travesias/codos/pasarelas y donde el terreno
    #       real no corresponde (fundido de extremos, tramos sin aterrazar, costuras) -----
    def construir_muros(self):
        for k in range(self.n):
            cm = self.curva(self.u_base(k) + self.AT)
            if cm is None or not self.b[k]['ok']:
                continue
            ultima = (k == self.n - 1)
            # RONDA 15c: los muros de una terraza sin calle viva (vacia) no se ponen: ni el suyo ni el que la separa
            # de la de abajo (antes quedaba un anden de 21 m entre dos muros sin uso)
            if not self.piezas.get(k) or (not ultima and not self.piezas.get(k + 1)):
                self.descartes.append('%s muro %d: terraza sin calle viva a un lado; no se pone' % (self.id, k))
                continue
            if self.sube:
                hb = self.h[k]; ht = (self.h[k] + 3.0) if ultima else self.h[k + 1]
                tipo = 'ultimo' if ultima else 'contencion'
            elif ultima:
                hb = self.h[k] - 1.5; ht = self.h[k] + 1.0
                tipo = 'parapeto'
            else:
                hb = self.h[k + 1]; ht = self.h[k]
                tipo = 'contencion'
            prohib = union([self.ctx['asf6'], self.ctx['otros'], self.incoherencia(cm)] + self.cortes[k])
            n_m = 0
            s_hechos = []
            u_m = self.u_base(k) + self.AT
            for pz in cm.recortar(prohib, 3.0):
                Zb = np.array([self.zxy(x, y) for (x, y) in pz.xy])
                terr = self.terreno.zs(pz.xy[:, 0], pz.xy[:, 1]); terr_m = self.terreno.zs_malla(pz.xy[:, 0], pz.xy[:, 1])
                ok = (terr >= Zb + hb - TOL_MURO[0]) & (terr_m <= Zb + ht + TOL_MURO[1])
                # v1 (revision D12/G6): ESCALON real a los dos lados del muro (terreno a u_muro -+ D_ESCALON_MURO por la normal
                # de la pista): solo hay muro donde el lado alto queda >= ESCALON_MIN_MURO sobre el bajo; el 'ultimo' (sube)
                # sube como mucho hasta el terreno de detras + 0.3 y el 'parapeto' (baja) baja hasta el terreno de detras - 0.3
                t_in = np.array([self.terreno.z(*self.pista.pos(s, self.lado, u_m - D_ESCALON_MURO)) for s in pz.s])
                t_out = np.array([self.terreno.z(*self.pista.pos(s, self.lado, u_m + D_ESCALON_MURO)) for s in pz.s])
                if self.sube:
                    alto_, bajo_ = t_out, t_in
                else:
                    alto_, bajo_ = t_in, t_out
                ok &= (alto_ - bajo_) >= ESCALON_MIN_MURO
                # v1 (revision propia): solo hay muro donde alguna de las dos terrazas que separa tiene calle a <= 15 m por s
                # (junto a la zona excluida del McLaren quedaban muros largos en bandas vacias)
                rangos = [(float(min(q.s)) - 15.0, float(max(q.s)) + 15.0)
                          for kk in ((k, k + 1) if not ultima else (k,)) for q in self.piezas.get(kk, [])]
                # v2 (revision C2-02): en los D_FIN_MURO m finales del sector el escalon de T1 sigue aunque la calle ya haya
                # acabado: ahi no se exige calle cerca (si hay alguna calle en la terraza)
                if rangos:
                    rangos += [(self.s0 - 1.0, self.s0 + D_FIN_MURO), (self.s1 - D_FIN_MURO, self.s1 + 1.0)]
                ok &= np.array([any(a_ <= s_ <= b_ for (a_, b_) in rangos) for s_ in pz.s], dtype=bool)
                cortes = np.abs(np.diff(Zb)) > SALTO_Z
                self.anota('muro', (terr - (Zb + hb))[ok])
                for tr in trocear(pz, ok, cortes, LARGO_MIN_MURO):
                    zb_ = np.array([self.zxy(x, y) for (x, y) in tr.xy])
                    zbase = zb_ + hb; ztop = zb_ + ht
                    if tipo in ('ultimo', 'parapeto'):
                        a_t = np.array([self.terreno.z(*self.pista.pos(s, self.lado, u_m + D_ESCALON_MURO)) for s in tr.s])
                        if tipo == 'ultimo':
                            ztop = np.clip(a_t + 0.3, zbase + 0.6, ztop)
                        else:
                            zbase = np.minimum(zbase, a_t - 0.3)
                    if tipo == 'contencion':
                        # v3 (revision D12): el muro acababa con la altura entera (6 m) y la cabeza cortada en vertical aunque el
                        # escalon real del extremo fuera de ~2 m (2.5 m de testero a la vista). En los REMATE_MURO m finales de
                        # cada extremo libre (no cortado por otro elemento: travesia, codo, pasarela, zona excluida) la coronacion
                        # baja hasta el terreno del lado alto + 0.3 (minimo 0.6 m de muro), en piezas cortas: escalonada
                        a_hi = np.array([self.terreno.z(*self.pista.pos(s, self.lado, u_m + (D_ESCALON_MURO if self.sube else -D_ESCALON_MURO)))
                                         for s in tr.s])
                        ztop = self._remate_extremos(tr, zbase, ztop, a_hi, prohib)
                        trozos = self._trozos_muro(tr, ztop - zbase, min_ext=2)
                    else:
                        trozos = self._trozos_muro(tr, ztop - zbase) if tipo in ('ultimo', 'parapeto') else [(0, len(tr.xy) - 1, 1.0)]
                    for (i0, i1, fac) in trozos:
                        pts = [[r3(tr.xy[i][0]), r3(tr.xy[i][1]), r3(zbase[i]), r3(zbase[i] + max(0.6, (ztop[i] - zbase[i]) * fac))]
                               for i in range(i0, i1 + 1)]
                        if len(pts) < 2:
                            continue
                        self.muros.append(dict(id='%s_muro%d_%d' % (self.id, k, n_m), terraza=k, tipo=tipo, pts=pts))
                        n_m += 1
                    self.F_propio.append(tr.line.buffer(1.0 if tipo == 'contencion' else 0.5))   # parapeto/ultimo: muro bajo detras del patio
                    s_hechos.append((float(min(tr.s)), float(max(tr.s))))
            n_m = self._extender_muro(k, u_m, tipo, prohib, s_hechos, n_m)

    def _extender_muro(self, k, u_m, tipo, prohib, s_hechos, n_m):
        """v2 (revision C2-02): T1 funde las terrazas en los 30 m de fuera del sector y la rampa del muro (escalon de hasta 6 m)
        seguia ahi sin muro delante: piramides de hierba de 3-5 m al final de pueblo_subida_ladera. Si el muro llega al extremo
        del sector, se PROLONGA hasta D_EXT_MURO m mas alla mientras el escalon real del terreno (a +-D_ESCALON_MURO por la
        normal) sea >= ESCALON_MIN_MURO, con la base 0.3 m bajo el terreno del lado bajo y la coronacion a la cota del lado
        alto (trozos de altura casi constante: urbanismo_escena levanta cada uno con su mediana)."""
        for (s_ext0, s_ext1, s_lim) in ((self.s1, self.s1 + D_EXT_MURO, self.s1), (self.s0 - D_EXT_MURO, self.s0, self.s0)):
            if not any(a_ - 4.0 <= s_lim <= b_ + 4.0 for (a_, b_) in s_hechos):
                continue
            ce = curva_offset(self.pista, s_ext0, s_ext1, self.lado, u_m)
            if ce is None or len(ce.xy) < 3:
                continue
            orden = np.argsort(np.abs(np.asarray(ce.s) - s_lim))
            pp = prep(prohib) if prohib is not None and not prohib.is_empty else None
            idx = []
            for i in orden:
                x, y = ce.xy[i]; s_ = float(ce.s[i])
                if pp is not None and pp.contains(Point(x, y)):
                    break
                t_in = self.terreno.z(*self.pista.pos(s_, self.lado, u_m - D_ESCALON_MURO))
                t_out = self.terreno.z(*self.pista.pos(s_, self.lado, u_m + D_ESCALON_MURO))
                alto_, bajo_ = (t_out, t_in) if self.sube else (t_in, t_out)
                if alto_ - bajo_ < ESCALON_MIN_MURO:
                    break
                idx.append((i, bajo_ - 0.3, alto_))
            if len(idx) < 2:
                continue
            idx.sort(key=lambda q: q[0])
            ii = [q[0] for q in idx]
            tr = Poli(np.asarray(ce.xy)[ii], np.asarray(ce.s)[ii])
            if tr.line is None or tr.largo < LARGO_MIN_MURO:
                continue
            zbase = np.array([q[1] for q in idx]); ztop = np.array([q[2] for q in idx])
            for (i0, i1, fac) in self._trozos_muro(tr, ztop - zbase):
                pts = [[r3(tr.xy[i][0]), r3(tr.xy[i][1]), r3(zbase[i]), r3(max(zbase[i] + 0.6, ztop[i]))] for i in range(i0, i1 + 1)]
                if len(pts) < 2:
                    continue
                self.muros.append(dict(id='%s_muro%d_%d' % (self.id, k, n_m), terraza=k, tipo=tipo, pts=pts, extension=True))
                n_m += 1
            self.F_propio.append(tr.line.buffer(1.0 if tipo == 'contencion' else 0.5))
            self.descartes.append('%s muro %d: prolongado %.0f m fuera del sector (s %.0f-%.0f, escalon real >= %.1f m)'
                                  % (self.id, k, tr.largo, float(min(tr.s)), float(max(tr.s)), ESCALON_MIN_MURO))
        return n_m

    def _remate_extremos(self, tr, zbase, ztop, a_hi, prohib):
        """v3 (revision D12): coronacion de un muro de contencion en sus REMATE_MURO m finales: min(ztop, terreno del lado alto
        + 0.3), nunca menos de zbase + 0.6. Solo en los extremos LIBRES (a > 3 m de 'prohib': si el muro acaba contra una
        travesia, un codo o una pasarela, sigue entero hasta ella)."""
        ztop = np.array(ztop, float).copy()
        cum = tr.cum
        pp = prep(prohib) if prohib is not None and not prohib.is_empty else None
        for extremo in (0, len(tr.xy) - 1):
            x, y = tr.xy[extremo]
            if pp is not None and pp.intersects(Point(x, y).buffer(3.0)):
                continue
            d_ext = cum if extremo == 0 else (cum[-1] - cum)
            m = d_ext <= REMATE_MURO
            ztop[m] = np.maximum(zbase[m] + 0.6, np.minimum(ztop[m], a_hi[m] + 0.3))
        return ztop

    def _trozos_muro(self, tr, alto, min_ext=3):
        """indices (i0, i1, factor) de los trozos de un muro de altura variable ('ultimo', 'parapeto'): se parte donde la
        altura se aleja > 0.8 m de la mediana del trozo (urbanismo_escena levanta cada muro con su altura MEDIANA).
        v3 (D12): min_ext = vertices minimos de un trozo de EXTREMO (2: peldanos de la coronacion escalonada del remate)."""
        n = len(tr.xy)
        out = []
        a = 0
        while a < n - 1:
            b = a + 1
            while b < n - 1 and abs(alto[b + 1] - np.median(alto[a:b + 2])) <= 0.8:
                b += 1
            out.append((a, b, 1.0))
            a = b
        # trozos de menos de 3 vertices (4 m) se unen al anterior (v3 D12: con min_ext = 2, no en el remate de los extremos:
        # ahi cada trozo corto es un peldano de la coronacion escalonada)
        d_end = np.minimum(tr.cum, tr.cum[-1] - tr.cum)
        def _remate(a, b):
            return min_ext < 3 and min(d_end[a], d_end[b]) <= REMATE_MURO + 0.5
        res = []
        for (a, b, f) in out:
            if res and b - a < 2 and not _remate(a, b):
                res[-1] = (res[-1][0], b, 1.0)
            else:
                res.append((a, b, f))
        if len(res) > 1 and res[0][1] - res[0][0] < 2 and not _remate(res[0][0], res[0][1]):
            res[1] = (res[0][0], res[1][1], 1.0); res = res[1:]
        return res

    # ----- esquinas de un solar/plaza contra el terreno: (ok, desvios) -----
    def esquinas_ok(self, poly, z_suelo):
        cs = list(poly.exterior.coords)[:4]
        c = poly.centroid
        dev, dev_m = self._dev_modo([q[0] for q in cs] + [c.x], [q[1] for q in cs] + [c.y], z_suelo, 'ambos')
        return (dev.min() >= -TOL_SOLAR[0] and dev_m.max() <= TOL_SOLAR[1]), np.where(dev_m > 0.0, dev_m, dev)[:4]

    # ----- plaza (1 por sector grande): hueco de 2 solares con fuente, en la terraza 0 -----
    def construir_plaza(self):
        if self.s1 - self.s0 < 240.0:
            return
        # RONDA 15c: antes exigia fmax >= fondo_max del spec (11) y la banda medida da 10.8: nunca habia plaza. Ahora
        # fondo = el de la banda (>= 8 m), se prueba cada 6 m desde el centro y en todas las terrazas, y la HUELLA
        # COMPLETA debe quedar a <= TOL_HUELLA del suelo
        F = union(self.F_propio + list(self.F_calles.values()) + [self.ctx['otros'], self.ctx['asf_casa'], self.ctx['pit8'],
                                                                  self.zona_costura(DIST_COSTURA_SOLAR)])
        for k in range(self.n):
            fach = self.linea_fachada(k)
            if fach is None or not self.piezas.get(k):
                continue
            banda = self.bandas[k].buffer(0.3)
            offs = [0.0]
            for d in np.arange(6.0, fach.largo / 2.0 - 14.0, 6.0):
                offs += [d, -d]
            for off in offs:
                t = fach.largo / 2.0 + off
                fondo = min(self.b[k]['fondo_max'], fach.valor('fmax', t, self.fondo_max))
                if fondo < 8.0 or (fach.valor('zr', t, 0.0) or 0.0) > 0.5:
                    continue
                p = fach.punto(t); T = fach.tangente(t)
                fx, fy = self.lado * T[1], -self.lado * T[0]       # -lado * normal_izquierda(T)
                poly = rect_fachada(p, T, (fx, fy), 24.0, fondo)
                if poly.intersects(F) or not banda.contains(poly):
                    continue
                if dist_a_piezas(self.piezas[k], p[0], p[1]) > 4.0:
                    continue
                c = poly.centroid; z = self.zxy(p[0], p[1]) + self.h[k]
                dev_b, dev_m = self._dev_poligono(poly, z, 1.0, modo='ambos')
                if dev_b.min() < -(TOL_HUELLA - 0.05) or dev_m.max() > TOL_HUELLA - 0.05:
                    continue
                dev = np.where(dev_m > 0.0, dev_m, dev_b)
                self.anota('plaza', dev)
                self.plazas.append(dict(id='%s_plaza' % self.id, terraza=k, cx=r3(c.x), cy=r3(c.y), z=r3(z), ancho=24.0,
                                        fondo=r3(fondo), rot_z=r3(math.atan2(fy, fx) - math.pi / 2), fx=r3(fx), fy=r3(fy),
                                        fuente=[r3(c.x), r3(c.y), r3(z)], poligono=[[r3(x), r3(y)] for x, y in list(poly.exterior.coords)[:4]]))
                self.F_propio.append(poly.buffer(1.0))
                return
        self.descartes.append('%s plaza: ningun hueco de 24 m llano a <= %.1f m' % (self.id, TOL_HUELLA))

    # ----- solares: recorrido denso por la linea de fachada; shapely rechaza cualquier solape y el
    #       terreno real rechaza esquinas enterradas (> 1.0) o flotantes (> 0.5) -----
    def construir_solares(self):
        # v2 (revision C2-14): ademas, la acera del kit de caminos (0.8 m) con juntas a INGLETE en los quiebros de la calle: en
        # las curvas el bordillo exterior de CAMINO_calle.009 cortaba la esquina de dos casas (hasta 0.6 m)
        aceras = []
        for cid, F in self.F_calles.items():
            pz_ = next((q for k_ in self.piezas for q in self.piezas[k_] if getattr(q, 'cid', None) == cid), None)
            c_ = next((c for c in self.calles if c['id'] == cid), None)
            if pz_ is not None and pz_.line is not None and c_ is not None:
                aceras.append(pz_.line.buffer(c_['ancho'] / 2.0 + 0.8 + 0.05, cap_style='flat', join_style='mitre', mitre_limit=3.0))
        Fp = prep(union(self.F_propio + [f.buffer(GAP_CALLE_SOLAR) for f in self.F_calles.values()] + aceras
                        + [self.ctx['otros'], self.ctx['asf_casa'], self.ctx['pit8'], self.zona_costura(DIST_COSTURA_SOLAR)]))
        bufs = []; tangs = []
        contador = 0; rechazo_terreno = 0; self.rechazos_s = []; self.rech_xy = []; plaz_pend = False
        motivos = dict(fondo=0, lejos_calle=0, solape=0, fuera_banda=0, pliegue=0, vecino=0, terreno=0, rampa_alta=0)
        altos = {}
        for plan in self.planes:
            if plan.get('ok') and plan.get('alto') is not None and not plan['alto'].is_empty:
                # v3 (D7): (terraza, poligono) por rampa; en el mar, uno para la terraza k y otro para la k+1
                for k_a, pol_a in plan.get('altos', [(plan['k'], plan['alto'])]):
                    if pol_a is not None and not pol_a.is_empty:
                        altos.setdefault(k_a, []).append(pol_a.buffer(GAP_RAMPA_ALTO))
        Fa = {k_: prep(union(v)) for k_, v in altos.items()}
        # v1: frentes algo mas estrechos (casas ligures altas y estrechas) y separacion 1.0-1.6 m: recupera la densidad que
        # cuestan la zona excluida del McLaren y el patio libre delante de las rampas (D7)
        anchos = [6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.0, 10.0, 10.0, 11.0]
        fondos = [8.0, 9.0, 10.0, 10.0, 11.0, 12.0, 12.0]
        base_seed = sum(ord(ch) for ch in self.id) * 97
        for k in range(self.n):
            fach = self.linea_fachada(k); piezas = self.piezas.get(k, [])
            if fach is None or not piezas:
                continue
            banda = prep(self.bandas[k].buffer(0.3))
            t = 1.0
            while t < fach.largo - 5.0:
                a0 = self.rng.choice(anchos); f0 = self.rng.choice(fondos)
                puesto = None
                # RONDA 15c: intentos de mas estrecho/menos fondo: en curvas (5.5-6.5 m de frente) y frente a rampas
                # (fondo >= FONDO_MIN_RAMPA) caben casas donde antes quedaba hueco
                intentos = []
                for af in ((a0, f0), (a0, min(f0, 8.0)), (max(6.5, a0 - 2.0), min(f0, 9.0)), (max(6.5, a0 - 2.0), 6.0),
                           (6.5, 7.0), (6.0, 6.0), (5.5, 6.0), (6.5, 4.5), (5.5, 4.0)):
                    if af not in intentos:
                        intentos.append(af)
                for (a, f) in intentos:
                    tc = t + a / 2.0
                    p = fach.punto(tc); T = fach.tangente(tc)
                    fx, fy = self.lado * T[1], -self.lado * T[0]
                    fmax_t = fach.valor('fmax', tc, self.fondo_max); uf = fach.valor('uf', tc, self.u_f0)
                    f_min = FONDO_MIN_RAMPA if (fach.valor('zr', tc, 0.0) or 0.0) > 0.5 else FONDO_MIN
                    if fmax_t < f_min:
                        motivos['fondo'] += 1; self.rech_xy.append((p[0], p[1], 'fondo'))
                        break
                    f = min(f, fmax_t)
                    if f < f_min:
                        continue
                    if dist_a_piezas(piezas, p[0], p[1]) > 4.0:
                        motivos['lejos_calle'] += 1; self.rech_xy.append((p[0], p[1], 'lejos_calle'))
                        break
                    poly = rect_fachada(p, T, (fx, fy), a, f)
                    if k in Fa and Fa[k].intersects(poly):
                        motivos['rampa_alta'] += 1; self.rech_xy.append((p[0], p[1], 'solape'))
                        continue
                    if Fp.intersects(poly.buffer(0.05)):
                        motivos['solape'] += 1; self.rech_xy.append((p[0], p[1], 'solape'))
                        continue
                    if not banda.contains(poly):
                        motivos['fuera_banda'] += 1; self.rech_xy.append((p[0], p[1], 'fuera_banda'))
                        continue
                    s = fach.s_de_t(tc)
                    cs = list(poly.exterior.coords)[:4]; us = [uf, uf, uf + f, uf + f]
                    if not all(self.pista.valido(x, y, s, u, 2.0) for (x, y), u in zip(cs, us)):
                        motivos['pliegue'] += 1; self.rech_xy.append((p[0], p[1], 'pliegue'))
                        continue
                    if bufs and shapely.intersects(np.array(bufs, dtype=object), poly).any():
                        motivos['vecino'] += 1; self.rech_xy.append((p[0], p[1], 'vecino'))
                        continue
                    z_suelo = self.zxy(p[0], p[1]) + self.h[k]
                    ok, dev = self.esquinas_ok(poly, z_suelo)
                    if ok:
                        # RONDA 15c: huella completa (rejilla 1.5 m), no solo las esquinas
                        dev_hb, dev_hm = self._dev_poligono(poly, z_suelo, 1.0, modo='ambos')
                        ok = (dev_hb.min() >= -TOL_SOLAR[0] and dev_hm.max() <= TOL_SOLAR[1]
                              and float(dev_hm.max() - dev_hb.min()) <= RANGO_CASA)
                        dev_h = np.where(dev_hm > 0.0, dev_hm, dev_hb)
                    if not ok:
                        rechazo_terreno += 1; motivos['terreno'] += 1; self.rech_xy.append((p[0], p[1], 'terreno'))
                        self.rechazos_s.append((s, float(dev.min()), float(dev.max())))
                        continue
                    puesto = (a, f, p, T, (fx, fy), poly, s, z_suelo, dev, float(np.abs(dev_h).max()))
                    break
                if puesto is None:
                    t += 0.5
                    continue
                a, f, p, T, (fx, fy), poly, s, z_suelo, dev, dev_max = puesto
                contador += 1
                if contador % PLAZOLETA_CADA == 0:
                    plaz_pend = True
                # plazoleta (jardin, 1 de cada 9): solo en un solar cuya huella completa este a <= TOL_HUELLA del suelo
                tipo = 'plazoleta' if (plaz_pend and dev_max <= TOL_HUELLA and f >= 6.0) else 'casa'
                if tipo == 'plazoleta':
                    plaz_pend = False
                plantas = 0 if tipo == 'plazoleta' else self.rng.choices([3, 4, 5, 6], [3, 4, 3, 1])[0]
                if f <= 6.5:
                    plantas = min(plantas, 3)          # casas de poco fondo: nada de torres
                c = poly.centroid
                self.anota('solar', dev)
                self.solares.append(dict(id='%s_solar%03d' % (self.id, contador), terraza=k, tipo=tipo,
                                         cx=r3(c.x), cy=r3(c.y), px=r3(p[0]), py=r3(p[1]), ancho=a, fondo=f,
                                         rot_z=r3(math.atan2(fy, fx) - math.pi / 2), fx=r3(fx), fy=r3(fy),
                                         z_suelo=r3(z_suelo), seed=(base_seed + k * 1000 + contador) % 100000,
                                         plantas=plantas, s=r3(s), poligono=[[r3(x), r3(y)] for x, y in list(poly.exterior.coords)[:4]],
                                         sep_x_neg=None, sep_x_pos=None, terreno_esquinas=[r3(v) for v in dev]))
                bufs.append(poly.buffer(1.02)); tangs.append(T)
                t += a + self.rng.uniform(1.0, 1.6)
        self._tangs = tangs
        self.rechazo_terreno = rechazo_terreno
        self.motivos_solares = motivos
        log('  intentos de solar rechazados por motivo: ' + json.dumps(motivos))
        if self.rechazos_s:
            bins = {}
            for (s, dmin, dmax) in self.rechazos_s:
                b = int(s // 40) * 40
                v = bins.setdefault(b, [0, 0.0, 0.0]); v[0] += 1; v[1] = min(v[1], dmin); v[2] = max(v[2], dmax)
            log('  rechazos por terreno (s: intentos/min/max): ' + ', '.join('%d: %d/%.1f/%.1f' % (b, v[0], v[1], v[2]) for b, v in sorted(bins.items())))

    # ----- separacion con los vecinos de la misma terraza, en ejes locales de la casa (-X / +X) -----
    def separaciones(self):
        polys = [Polygon(s['poligono']) for s in self.solares]
        for i, sol in enumerate(self.solares):
            T = self._tangs[i]; ci = polys[i].centroid
            prev_d = 99.0; next_d = 99.0
            for j, otro in enumerate(self.solares):
                if j == i or otro['terraza'] != sol['terraza']:
                    continue
                cj = polys[j].centroid
                dot = (cj.x - ci.x) * T[0] + (cj.y - ci.y) * T[1]
                d = polys[i].distance(polys[j])
                if d > 30.0:
                    continue
                if dot < 0:
                    prev_d = min(prev_d, d)
                else:
                    next_d = min(next_d, d)
            # local +X = (fy, -fx): lado +1 -> +X apunta a -T (vecino previo); lado -1 -> +X apunta a +T
            if self.lado == 1:
                sol['sep_x_pos'], sol['sep_x_neg'] = r3(prev_d), r3(next_d)
            else:
                sol['sep_x_pos'], sol['sep_x_neg'] = r3(next_d), r3(prev_d)

    def construir(self):
        log('sector %s (s %d-%d, lado %+d, %d terrazas, %s)' % (self.id, self.s0, self.s1, self.lado, self.n, 'SUBE' if self.sube else 'BAJA'))
        self.preparar_cota()
        self.medir_bandas()
        self.mapa_costuras()
        self.construir_bandas()
        s_travs = self.posiciones_travesias()
        self.s_travs = list(s_travs); self.it_rescate = set()
        self.planificar_rampas(s_travs)
        self.construir_calles()
        self.construir_enlaces()
        geoms = {}
        for it, st in enumerate(s_travs):
            for k in range(self.n - 1):
                geoms[(it, k)] = self._travesia_geom(it, st, k, False)
        self.construir_rampas(geoms)
        self.rescatar_islas(geoms, solo_rampa=True)
        self.rescatar_islas(geoms)
        self.quitar_huerfanas(geoms)
        self.podar_rampas(geoms)
        self.construir_travesias(self.s_travs, geoms)
        self.construir_muros()
        self.construir_plaza()
        self.construir_solares()
        self.recortar_colas()
        self.separaciones()
        casas = sum(1 for s in self.solares if s['tipo'] == 'casa')
        self.stats = dict(casas=casas, plazoletas=len(self.solares) - casas, calles=len(self.calles),
                          largo_calles=r3(sum(LineString([p[:2] for p in c['pts']]).length for c in self.calles)),
                          travesias=len(self.travesias), rampas=len(self.rampas), escaleras=len(self.escaleras),
                          muros=len(self.muros), enlaces=len(self.enlaces), plazas=len(self.plazas), salidas=len(self.salidas),
                          uniones_costura=len(self.uniones), solares_rechazados_terreno=self.rechazo_terreno)
        log('  casas %d, plazoletas %d, calles %d (%.0f m), travesias %d, rampas %d, escaleras %d, muros %d, enlaces %d, salidas %d, uniones %d, rechazos terreno %d'
            % (casas, self.stats['plazoletas'], len(self.calles), self.stats['largo_calles'], len(self.travesias),
               len(self.rampas), len(self.escaleras), len(self.muros), len(self.enlaces), len(self.salidas), len(self.uniones), self.rechazo_terreno))
        for d in self.descartes:
            log('  descarte: ' + d)

    def _anclas_calle(self, pz):
        """v2 (B2-08/F2-09/C2-10): parametros t (a lo largo de la calle pz) de todo lo que le da DESTINO: casas y plazoletas
        que dan a ella, travesias, rampas, escaleras, enlaces, plazas, salidas y uniones que la tocan."""
        ln = pz.line
        ts = []
        def mete(xy, tol):
            for q in xy:
                pt = Point(q[0], q[1])
                if ln.distance(pt) <= tol:
                    ts.append(float(ln.project(pt)))
        for so in self.solares:
            P = Polygon(so['poligono'])
            if P.distance(ln) <= self.AC / 2.0 + 3.0:
                mete(list(P.exterior.coords), 1e9)
        tol = self.AC / 2.0 + 1.5
        for tv in self.travesias:
            mete([p[:2] for p in tv['pts']], tol)
        for r in self.rampas:
            mete([p[:2] for p in r['pts']], tol)
        for e in self.escaleras:
            for tr in e['tramos'] + ([dict(pts=e['pasarela'])] if e['pasarela'] else []):
                mete([p[:2] for p in tr['pts']], tol)
        for e in self.enlaces:
            mete([p[:2] for p in e['pts']], tol)
        for pl in self.plazas:
            mete(pl['poligono'], self.AC / 2.0 + 3.0)
        mete([(sa['x'], sa['y']) for sa in self.salidas], self.AC / 2.0 + 3.0)
        for u in self.uniones:
            mete([u['a'], u['b']], 3.0)
        return ts

    def recortar_colas(self):
        """v2 (revision B2-08/F2-09/C2-10): cada calle se trazaba de punta a punta del sector (o hasta la zona excluida del
        McLaren) y sus extremos seguian 7-18 m mas alla del ultimo acceso o de la ultima casa, muriendo en el cesped, en el
        borde de un tajo o contra la roca (camino_sin_destino en la QA). Ahora cada extremo se recorta a COLA_CALLE m pasado su
        ultimo destino (_anclas_calle); los empalmes con travesias, rampas, escaleras y enlaces quedan dentro. Asi el extremo
        queda junto a una casa (urbanismo_escena lo da por destino) y no hace falta plazoleta en una ladera."""
        for k in range(self.n):
            nuevas = []
            for pz in self.piezas.get(k, []):
                ts = self._anclas_calle(pz) if pz.line is not None else []
                if not ts:
                    nuevas.append(pz); continue
                t_lo = max(0.0, min(ts) - COLA_CALLE); t_hi = min(pz.largo, max(ts) + COLA_CALLE)
                if t_lo < 3.0 and t_hi > pz.largo - 3.0:
                    nuevas.append(pz); continue
                nueva = pz.tramo(t_lo, t_hi)
                if nueva is None or nueva.largo < 10.0:
                    nuevas.append(pz); continue
                nueva.cid = pz.cid
                for c in self.calles:
                    if c['id'] == pz.cid:
                        c['pts'] = nueva.pts3(nueva.attr['z']); c['s'] = [r3(v) for v in nueva.s]
                        pu = nueva.attr.get('puente')
                        c['costura_idx'] = ([int(np.where(pu > 0.5)[0][0]), int(np.where(pu > 0.5)[0][-1])]
                                            if pu is not None and (pu > 0.5).any() else None)
                        ancho_c = c['ancho']
                        self.F_calles[pz.cid] = franja(nueva, ancho_c)
                self.descartes.append('%s calle %s: recortada %.0f m al principio y %.0f m al final (acaba a %.0f m de su ultimo destino)'
                                      % (self.id, pz.cid, t_lo, pz.largo - t_hi, COLA_CALLE))
                nuevas.append(nueva)
            self.piezas[k] = nuevas

    def _une(self, plan, geoms, piezas_baja, pz, solo_rampa=False):
        """el plan (rampa/escalera construida) une un trozo de piezas_baja (terraza k) con el trozo pz (k+1)."""
        if not plan.get('ids'):
            return False
        g = geoms.get((plan['it'], plan['k']))
        if g is None or dist_a_piezas(piezas_baja, g['pa'][0], g['pa'][1]) > 4.0:
            return False
        return any(pz.line.distance(Point(p)) <= 4.5 for i_, p in zip(plan['ids'], plan['p_k'])
                   if (not solo_rampa) or '_rampa' in i_)

    def _alcanzables(self, geoms, solo_rampa=False):
        vivas = {0: list(self.piezas.get(0, []))}
        for k in range(1, self.n):
            vivas[k] = [pz for pz in self.piezas.get(k, [])
                        if any(self._une(pl, geoms, vivas[k - 1], pz, solo_rampa) for pl in self.planes if pl['k'] == k - 1)]
        return vivas

    def _deshacer_plan(self, plan):
        self.rampas = [r for r in self.rampas if r['id'] not in plan.get('ids', [])]
        self.escaleras = [e for e in self.escaleras if e['id'] not in plan.get('ids', [])]
        for F in plan.get('F', []):
            if F in self.F_propio:
                self.F_propio.remove(F)
        for c in plan.get('cortes', []):
            if c in self.cortes[plan['k']]:
                self.cortes[plan['k']].remove(c)
        plan['ok'] = False; plan['esc'] = None; plan['ids'] = []

    def rescatar_islas(self, geoms, solo_rampa=False):
        """v1 (revision B2/C-03): una calle de la terraza k >= 1 sin rampa ni escalera que la una a un trozo alcanzable de
        k-1 (p.ej. porque su travesia caia en la zona excluida del McLaren) ya no se quita sin mas: se busca otra travesia
        (cada 6 m a lo largo del tramo comun, desde el centro) con su rampa o, si no cabe, su escalera, evitando lo ya
        construido del sector. Solo en sectores que SUBEN (en los que bajan la rampa desvia la calle: se planifica antes).
        solo_rampa (revision F-05, 'un coche podria ir a todos los sitios'): primero se busca una RAMPA para cada calle a
        la que no se llega en coche (desde un trozo de k-1 al que si se llega en coche)."""
        if not self.sube or self.n < 2:
            return
        for k in range(1, self.n):
            vivas = self._alcanzables(geoms, solo_rampa=solo_rampa)
            for pz in self.piezas.get(k, []):
                if any(pz is v for v in vivas[k]) or not vivas[k - 1]:
                    continue
                s_a, s_b = float(min(pz.s)), float(max(pz.s))
                tramos = [(max(s_a, float(min(q.s))), min(s_b, float(max(q.s)))) for q in vivas[k - 1]]
                tramos = [(a, b) for (a, b) in tramos if b - a > 20.0]
                cands = []
                for (a, b) in tramos:
                    cands += [float(s) for s in np.arange(a + 10.0, b - 10.0 + 1e-6, 6.0)]
                m_ = 0.5 * (s_a + s_b)
                cands.sort(key=lambda s: abs(s - m_))
                hecho = False
                for st in cands[:40]:
                    it = len(self.s_travs)
                    n_zr = len(self.zonas_rampa[k - 1])
                    nuevos = self.planificar_rampas([st], it0=it, k_solo=k - 1, evitar=union(self.F_propio), solo_rampa=solo_rampa)
                    if not nuevos:
                        continue
                    plan = nuevos[0]
                    g = self._travesia_geom(it, st, k - 1, False)
                    if g is not None and g['pol'].buffer(0.3).intersects(union(self.F_propio)):
                        g = None
                    if g is not None:
                        geoms[(it, k - 1)] = g
                        self.construir_rampas(geoms, [plan])
                        if self._une(plan, geoms, vivas[k - 1], pz, solo_rampa=solo_rampa):
                            self.s_travs.append(st); self.it_rescate.add(it)
                            self.descartes.append('%s calle %s: %s con %s (travesia nueva en s %.0f)'
                                                  % (self.id, pz.cid, 'acceso en coche' if solo_rampa else 'isla rescatada',
                                                     '+'.join(plan['ids']), st))
                            hecho = True
                            break
                        self._deshacer_plan(plan)
                        geoms.pop((it, k - 1), None)
                    self.planes.remove(plan)
                    del self.zonas_rampa[k - 1][n_zr:]
                if not hecho:
                    self.descartes.append('%s calle %s: %s' % (self.id, pz.cid, 'sin rampa posible desde una calle con coche'
                                                               if solo_rampa else 'isla sin rescate posible'))

    def podar_rampas(self, geoms):
        """v1 (revision D7): en los sectores que SUBEN cada rampa deja sin casas los ~50 m de patio que tiene delante
        (tramo alto a GAP_RAMPA_ALTO). Una rampa que no hace falta para llegar EN COCHE a ninguna calle (otra rampa ya une
        los mismos trozos) se quita, de la mas empinada a la menos; su escalera (si la tiene) se queda."""
        if not self.sube:
            return
        objetivo = {k: set(id(p) for p in v) for k, v in self._alcanzables(geoms, solo_rampa=True).items()}
        pend = {r['id']: abs(r['pendiente']) for r in self.rampas}
        cands = [pl for pl in self.planes if pl.get('ids') and any('_rampa' in i for i in pl['ids'])]
        cands.sort(key=lambda pl: -max(pend.get(i, 0.0) for i in pl['ids']))
        for pl in cands:
            rid = next(i for i in pl['ids'] if '_rampa' in i)
            j = pl['ids'].index(rid)
            ids0, pk0 = list(pl['ids']), list(pl['p_k'])
            pl['ids'] = [i for i in ids0 if i != rid]; pl['p_k'] = [q for n_, q in enumerate(pk0) if n_ != j]
            coche = self._alcanzables(geoms, solo_rampa=True)
            if all(set(id(p) for p in coche.get(k, [])) >= v for k, v in objetivo.items()):
                F_r = pl['F'].pop(j); C_r = pl['cortes'].pop(j)
                if F_r in self.F_propio:
                    self.F_propio.remove(F_r)
                if C_r in self.cortes[pl['k']]:
                    self.cortes[pl['k']].remove(C_r)
                self.rampas = [r for r in self.rampas if r['id'] != rid]
                pl['ok'] = False
                self.descartes.append('%s %s: rampa que no da acceso en coche a ninguna calle mas; se quita (queda su escalera si la tiene)' % (self.id, rid))
            else:
                pl['ids'], pl['p_k'] = ids0, pk0

    def quitar_huerfanas(self, geoms):
        """Alcanzabilidad de abajo arriba: la via de servicio (terraza 0) siempre (enlaces a la pista); un trozo
        de calle de la terraza k >= 1 solo si una rampa o escalera construida lo une a un trozo ALCANZABLE de
        k-1. Las calles no alcanzables (islas) se quitan con sus rampas/escaleras: nada 'sin destino'.
        v1 (revision F-05): un trozo al que solo se llega por ESCALERAS (ningun camino de rampas desde la pista) pasa a
        calle PEATONAL (carruggio de ANCHO_PEATONAL m, tipo 'peatonal'): un coche no puede llegar y no lo parece."""
        vivas = {0: list(self.piezas.get(0, []))}
        for k in range(1, self.n):
            vivas[k] = []
            for pz in self.piezas.get(k, []):
                ok = any(self._une(pl, geoms, vivas[k - 1], pz) for pl in self.planes if pl['k'] == k - 1)
                if ok:
                    vivas[k].append(pz)
                else:
                    self.descartes.append('%s calle %s: isla (ninguna rampa/escalera la une a la terraza %d); se quita' % (self.id, pz.cid, k - 1))
                    self.calles = [c for c in self.calles if c['id'] != pz.cid]
                    self.F_calles.pop(pz.cid, None)
            self.piezas[k] = vivas[k]
        # rampas/escaleras que arrancan de un trozo no alcanzable o que ya no llegan a ninguna calle viva
        for plan in self.planes:
            if not plan.get('ids'):
                continue
            k = plan['k']; g = geoms.get((plan['it'], k))
            baja_ok = g is not None and dist_a_piezas(vivas[k], g['pa'][0], g['pa'][1]) <= 4.0
            alta_ok = any(dist_a_piezas(vivas[k + 1], p[0], p[1]) <= 4.5 for p in plan['p_k'])
            if baja_ok and alta_ok:
                continue
            self.descartes.append('%s %s: rampa/escalera sin calle viva en un extremo; se quita' % (self.id, '+'.join(plan['ids'])))
            self.rampas = [r for r in self.rampas if r['id'] not in plan['ids']]
            self.escaleras = [e for e in self.escaleras if e['id'] not in plan['ids']]
            for F in plan['F']:
                if F in self.F_propio:
                    self.F_propio.remove(F)
            for c in plan['cortes']:
                if c in self.cortes[k]:
                    self.cortes[k].remove(c)
            plan['ok'] = False; plan['esc'] = None; plan['ids'] = []
        # F-05: alcanzables en coche (solo rampas) -> el resto de calles de k >= 1 son peatonales
        coche = self._alcanzables(geoms, solo_rampa=True)
        for k in range(1, self.n):
            for pz in self.piezas.get(k, []):
                if any(pz is v for v in coche[k]):
                    continue
                for c in self.calles:
                    if c['id'] == pz.cid:
                        c['tipo'] = 'peatonal'; c['ancho'] = ANCHO_PEATONAL
                self.F_calles[pz.cid] = franja(pz, ANCHO_PEATONAL)
                self.descartes.append('%s calle %s: sin rampa desde la pista (solo escaleras): calle peatonal de %.1f m'
                                      % (self.id, pz.cid, ANCHO_PEATONAL))

    def exportar(self):
        terr = []
        for k in range(self.n):
            b = self.bandas.get(k, Polygon())
            geoms = list(b.geoms) if hasattr(b, 'geoms') else [b]
            banda = [[[r3(x), r3(y)] for x, y in gm.exterior.coords] for gm in geoms if not gm.is_empty]
            info = {kk: vv for kk, vv in self.b[k].items() if kk != 'med'}
            info['banda'] = banda
            terr.append(info)
        return dict(id=self.id, s0=self.s0, s1=self.s1, lado=self.lado, n_terrazas=self.n, terrazas=terr,
                    calles=self.calles, enlaces=self.enlaces, vallas=self.vallas, travesias=self.travesias,
                    rampas=self.rampas, escaleras=self.escaleras, muros=self.muros, solares=self.solares,
                    plazas=self.plazas, salidas=self.salidas, stats=self.stats, descartes=self.descartes)


# ---------------------------------------------------------------------------
# QA: aserciones globales (geometria 2D + terreno real, recomputado desde lo exportado)
# ---------------------------------------------------------------------------
def _elipse_casino(g):
    """Contorno del penon del casino EXACTAMENTE como integrar_escena.zona_casino() (curvas 36-38 en metros)."""
    cv = {int(c['n']): c for c in g.get('curvas', []) if 'n' in c}
    if not all(n in cv for n in (36, 37, 38)):
        return None
    M = g['muestras']; N = len(M)
    cxc = sum(cv[n]['x'] for n in (36, 37, 38)) / 3.0; cyc = sum(cv[n]['y'] for n in (36, 37, 38)) / 3.0
    ii = range(0, N, 20)
    mx = sum(M[i]['x'] for i in ii) / len(ii); my = sum(M[i]['y'] for i in ii) / len(ii)
    dx, dy = cxc - mx, cyc - my; dl = math.hypot(dx, dy) or 1.0
    cx, cy = cxc + dx / dl * 190.0, cyc + dy / dl * 190.0
    pts = []
    for k in range(64):
        a = 2 * math.pi * k / 64
        ex, ey = 118.0 * math.cos(a), 78.0 * math.sin(a)
        pts.append((cx + ex * math.cos(0.5) - ey * math.sin(0.5), cy + ex * math.sin(0.5) + ey * math.cos(0.5)))
    return Polygon(pts)


def verificar_huellas(sectores, ctx, terreno, fallos):
    """RONDA 15c: QA de HUELLA COMPLETA (no solo el eje): travesias (|terreno - superficie| <= TOL_HUELLA en eje y
    bordes), rampas (el terreno no asoma > TOL_RELLENO en eje y bordes), plazoletas y plazas (|dev| <= TOL_HUELLA en una
    rejilla de 1 m), bordes de calles (TOL_BORDE) y casas (rejilla de 1 m: criterio T6 -0.6/+1.2 y rango <= 1.5);
    terrazas vacias (talladas por T1 sin calle o sin casas); huecos > 12 m entre solares consecutivos de una fila (sin
    contar lo que ocupan travesias/rampas/escaleras/plazas); elementos dentro del contorno del penon del casino."""
    for kf in ('travesia_huella', 'rampa_huella', 'plazoleta_huella', 'plaza_huella', 'calle_borde', 'solar_huella',
               'terraza_vacia', 'casino_contorno'):
        fallos.setdefault(kf, 0)
    peor = dict(travesia=0.0, rampa=-9.0, plazoleta=0.0, plaza=0.0, calle_borde=[0.0, 0.0], solar=[0.0, 0.0], solar_rango=0.0)
    el = ctx.get('elipse_casino')
    huecos_tot = 0.0; huecos = []; vacias = []
    for S in sectores:
        for tv in S.travesias:
            db, dm = S._dev_huella([p[:2] for p in tv['pts']], tv['pts'][0][2], tv['ancho'], modo='ambos')
            m_ = max(-float(db.min()), float(dm.max()))
            peor['travesia'] = max(peor['travesia'], m_)
            fallos['travesia_huella'] += int(m_ > TOL_HUELLA + 1e-6)
        for r in S.rampas:
            ln = LineString([p[:2] for p in r['pts']])
            cum = [ln.project(Point(p[:2])) for p in r['pts']]; zr = [p[2] for p in r['pts']]
            d = S._dev_huella([p[:2] for p in r['pts']], None, r['ancho'],
                              z_de_t=lambda t, c=cum, z=zr: float(np.interp(t, c, z)), fracs=FRACS_RAMPA, modo='malla').reshape(-1, len(FRACS_RAMPA))
            peor['rampa'] = max(peor['rampa'], float(d[:, 1:-1].max()))
            peor['rampa_murete'] = max(peor.get('rampa_murete', -9.0), float(d[:, [0, -1]].max()))
            fallos['rampa_huella'] += int(d[:, 1:-1].max() > TOL_RELLENO + 1e-6 or d[:, [0, -1]].max() > TOL_MURETE + 1e-6)
        for s in S.solares:
            db, dm = S._dev_poligono(Polygon(s['poligono']), s['z_suelo'], 1.0, modo='ambos')
            if s['tipo'] == 'plazoleta':
                m_ = max(-float(db.min()), float(dm.max()))
                peor['plazoleta'] = max(peor['plazoleta'], m_)
                fallos['plazoleta_huella'] += int(m_ > TOL_HUELLA + 1e-6)
            else:
                rg = float(dm.max() - db.min())
                peor['solar'] = [min(peor['solar'][0], float(db.min())), max(peor['solar'][1], float(dm.max()))]
                peor['solar_rango'] = max(peor['solar_rango'], rg)
                fallos['solar_huella'] += int(db.min() < -0.6 or dm.max() > 1.2 or rg > RANGO_CASA + 1e-6)
        for p in S.plazas:
            db, dm = S._dev_poligono(Polygon(p['poligono']), p['z'], 1.0, modo='ambos')
            m_ = max(-float(db.min()), float(dm.max()))
            peor['plaza'] = max(peor['plaza'], m_)
            fallos['plaza_huella'] += int(m_ > TOL_HUELLA + 1e-6)
        for c in S.calles:
            pts = c['pts']; ci = c.get('costura_idx')
            for i in range(len(pts)):
                if ci and ci[0] <= i <= ci[1]:
                    continue
                a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
                tx, ty = b[0] - a[0], b[1] - a[1]; n_ = math.hypot(tx, ty) or 1.0
                for sg in (-1.0, 1.0):
                    x = pts[i][0] - ty / n_ * sg * c['ancho'] / 2.0; y = pts[i][1] + tx / n_ * sg * c['ancho'] / 2.0
                    dv = terreno.z(x, y) - pts[i][2]; dvm = terreno.z_malla(x, y) - pts[i][2]
                    peor['calle_borde'] = [min(peor['calle_borde'][0], dv), max(peor['calle_borde'][1], dvm)]
                    fallos['calle_borde'] += int(dv < -TOL_BORDE[0] - 1e-6 or dvm > TOL_BORDE[1] + 1e-6)
        if el is not None:
            elp = prep(el.buffer(2.0))
            geoms = [Polygon(s['poligono']) for s in S.solares]
            geoms += [LineString([q[:2] for q in c['pts']]) for c in S.calles + S.travesias + S.enlaces]
            fallos['casino_contorno'] += sum(1 for gm in geoms if elp.intersects(gm))
        # terrazas vacias y huecos por fila
        exc = []
        for tv in S.travesias:
            exc.append(LineString([q[:2] for q in tv['pts']]).buffer(tv['ancho'] / 2.0 + 1.5))
        for r in S.rampas:
            exc.append(LineString([q[:2] for q in r['pts']]).buffer(r['ancho'] / 2.0 + 1.5))
            # v1 (D7): el patio libre delante del tramo alto de la rampa (sin casas a < GAP_RAMPA_ALTO) no es un hueco
            if S.sube and len(r['relleno']) >= 4:
                exc.append(Polygon(r['relleno']).buffer(GAP_RAMPA_ALTO + 3.0))
        for e in S.escaleras:
            for tr in e['tramos'] + ([dict(pts=e['pasarela'])] if e['pasarela'] else []):
                exc.append(LineString([q[:2] for q in tr['pts']]).buffer(1.5))
        for p in S.plazas:
            exc.append(Polygon(p['poligono']).buffer(1.0))
        EX = union(exc)
        for k in range(S.n):
            tallada = bool(S.b[k].get('s_ok'))
            nc = sum(1 for c in S.calles if c['terraza'] == k)
            sols = sorted([s for s in S.solares if s['terraza'] == k], key=lambda s: s['s'])
            ncasas = sum(1 for s in sols if s['tipo'] == 'casa')
            if tallada and (nc == 0 or ncasas == 0):
                vacias.append('%s t%d (calles %d, casas %d)' % (S.id, k, nc, ncasas))
                fallos['terraza_vacia'] += 1
            for a, b in zip(sols[:-1], sols[1:]):
                d = Polygon(a['poligono']).distance(Polygon(b['poligono']))
                if d <= 12.0:
                    continue
                ln = LineString([(a['px'], a['py']), (b['px'], b['py'])])
                libre = ln.difference(EX).length - (ln.length - d)
                if libre > 12.0:
                    huecos.append((S.id, k, r3(a['s']), r3(b['s']), r3(libre)))
                    huecos_tot += libre
    log('QA huellas: peor |dev| travesia %.2f, terreno sobre rampa %.2f (muretes %.2f), plazoleta %.2f, plaza %.2f, bordes de calle %.2f..%+.2f, '
        'casas %.2f..%+.2f (rango max %.2f)' % (peor['travesia'], peor['rampa'], peor.get('rampa_murete', 0.0), peor['plazoleta'], peor['plaza'],
                                               peor['calle_borde'][0], peor['calle_borde'][1], peor['solar'][0],
                                               peor['solar'][1], peor['solar_rango']))
    log('QA terrazas vacias (talladas por T1 sin calle o sin casas): %d %s' % (len(vacias), vacias))
    log('QA huecos > 12 m entre solares consecutivos de una fila (descontando travesias/rampas/escaleras/plazas): %d, suma %.0f m'
        % (len(huecos), huecos_tot))
    for h in huecos:
        log('    hueco %s t%d s %.0f-%.0f: %.0f m libres' % h)
    return dict(peor_huella={k: (r3(v) if not isinstance(v, list) else [r3(x) for x in v]) for k, v in peor.items()},
                terrazas_vacias=vacias, huecos=huecos, huecos_suma_m=r3(huecos_tot))


def verificar_v1(sectores, ctx, fallos):
    """v1: controles de la revision de la ronda 15 (todos deben dar 0):
      zona_excluida  (B2/C-03)  nada del plan dentro de spec['zonas_excluidas'] + margen;
      enlace_asfalto (D1/F-02)  la franja del enlace con sus bordillos (ancho/2 + 0.25) a >= 0.2 m del asfalto;
      rampa_pared    (D7)       ninguna casa a < GAP_RAMPA_ALTO - 0.1 de una rampa que pase > 1 m sobre su suelo (v3: en los
                                sectores que bajan, cuya calzada quede a menos de 0.4 m bajo su suelo);
      escalera_solar (C-10/D13) ninguna casa a < GAP_ESC - 0.1 de una escalera (tramos, descansillo, pasarela);
      calle_solar    (C-10)     ninguna casa a < GAP_CALLE_SOLAR del borde nominal de una calle o travesia.
    v2 (revision D2-02/N3-F/B2-08):
      escalera_sin_destino      los dos extremos de cada escalera (arranque y final de la pasarela o del tramo B) a <= 1 m de
                                una calle, travesia o plaza del sector (antes una pasarela acababa en el prado a 9.3 m);
      (info) enlace_desnivel    desnivel maximo calle -> boca del enlace (objetivo <= DZ_BOCA_ENLACE; la rampa de 1.1 m de la
                                boca la tiene que tallar integrar);
      (info) calle_cola         distancia maxima del extremo de una calle a su ultimo destino (objetivo <= COLA_CALLE)."""
    for kf in ('zona_excluida', 'enlace_asfalto', 'rampa_pared', 'escalera_solar', 'calle_solar', 'escalera_sin_destino'):
        fallos.setdefault(kf, 0)
    excl = ctx.get('excluida')
    exp = prep(excl) if excl is not None and not excl.is_empty else None
    asf = ctx['asfalto']
    peor = dict(enlace_asfalto=99.0, rampa_pared=99.0, escalera_solar=99.0, calle_solar=99.0, escalera_destino=0.0,
                enlace_desnivel=0.0, calle_cola=0.0)
    for S in sectores:
        vias = [LineString([q[:2] for q in c['pts']]).buffer(c['ancho'] / 2.0, cap_style='flat') for c in S.calles + S.travesias]
        vias += [Polygon(pl['poligono']) for pl in S.plazas]
        for e in S.escaleras:
            # ladera: arranque del tramo A (travesia k) y final de la pasarela (calle k+1), a <= 1 m; mar: final de la pasarela
            # (travesia k, <= 2 m) y pie del tramo B (calle k+1 desviada, al otro lado del parterre de 4.5 m: <= 4 m)
            if S.sube:
                ext = [(e['tramos'][0]['pts'][0], 1.05), ((e['pasarela'] or e['tramos'][-1]['pts'])[-1], 1.05)]
            else:
                ext = [((e['pasarela'] or e['tramos'][0]['pts'])[-1], 2.0), (e['tramos'][-1]['pts'][-1], 4.0)]
            for q, tol_e in ext:
                d = min([v.distance(Point(q[0], q[1])) for v in vias] or [99.0])
                peor['escalera_destino'] = max(peor['escalera_destino'], d - tol_e)
                fallos['escalera_sin_destino'] += int(d > tol_e)
        for e in S.enlaces:
            peor['enlace_desnivel'] = max(peor['enlace_desnivel'], abs(float(e.get('desnivel_boca', 0.0))))
        for k in range(S.n):
            for pz in S.piezas.get(k, []):
                ts = S._anclas_calle(pz)
                if ts and pz.line is not None:
                    peor['calle_cola'] = max(peor['calle_cola'], min(ts), pz.largo - max(ts))
        casas = [(Polygon(s['poligono']), s) for s in S.solares if s['tipo'] == 'casa']
        geoms = [Polygon(s['poligono']) for s in S.solares]
        geoms += [LineString([q[:2] for q in c['pts']]).buffer(c['ancho'] / 2.0, cap_style='flat') for c in S.calles + S.travesias + S.enlaces]
        geoms += [Polygon(r['relleno']) for r in S.rampas if len(r['relleno']) >= 4]
        esc_pol = []
        for e in S.escaleras:
            for tr in e['tramos'] + ([dict(pts=e['pasarela'])] if e['pasarela'] else []):
                esc_pol.append(LineString([q[:2] for q in tr['pts']]).buffer(e['ancho'] / 2.0, cap_style='flat'))
            if e['descansillo']:
                esc_pol.append(Polygon([q[:2] for q in e['descansillo']]))
        geoms += esc_pol
        geoms += [LineString([q[:2] for q in m['pts']]) for m in S.muros]
        geoms += [Polygon(pl['poligono']) for pl in S.plazas]
        geoms += [Point(sa['x'], sa['y']) for sa in S.salidas]
        if exp is not None:
            fallos['zona_excluida'] += sum(1 for gm in geoms if exp.intersects(gm))
        for e in S.enlaces:
            d = LineString([q[:2] for q in e['pts']]).buffer(e['ancho'] / 2.0 + 0.25, cap_style='flat', join_style='mitre').distance(asf)
            peor['enlace_asfalto'] = min(peor['enlace_asfalto'], d)
            fallos['enlace_asfalto'] += int(d < 0.2)
        for r in S.rampas:
            if len(r['relleno']) < 4:
                continue
            rel = Polygon(r['relleno']).buffer(0)
            eje = LineString([q[:2] for q in r['pts']]); cum = [eje.project(Point(q[:2])) for q in r['pts']]; zr = [q[2] for q in r['pts']]
            for P, s in casas:
                d = P.distance(rel)
                if d >= GAP_RAMPA_ALTO - 0.1:
                    continue
                q_ = shapely.ops.nearest_points(P, rel)[1]
                z_ = float(np.interp(eje.project(q_), cum, zr))
                # v3 (revision D7): en los sectores que BAJAN cuenta tambien la calzada a < 0.4 m bajo el suelo de la casa (su
                # pretil de 0.9 m queda >= 0.5 m sobre la planta baja)
                if z_ > s['z_suelo'] + (1.0 if S.sube else -0.4):
                    peor['rampa_pared'] = min(peor['rampa_pared'], d)
                    fallos['rampa_pared'] += 1
        for P, s in casas:
            for ep in esc_pol:
                d = P.distance(ep)
                peor['escalera_solar'] = min(peor['escalera_solar'], d)
                fallos['escalera_solar'] += int(d < GAP_ESC - 0.1)
            for c in S.calles + S.travesias:
                d = P.distance(LineString([q[:2] for q in c['pts']]).buffer(c['ancho'] / 2.0, cap_style='flat'))
                peor['calle_solar'] = min(peor['calle_solar'], d)
                fallos['calle_solar'] += int(d < GAP_CALLE_SOLAR - 1e-3)
    log('QA v1/v2: ' + json.dumps({k: fallos[k] for k in ('zona_excluida', 'enlace_asfalto', 'rampa_pared', 'escalera_solar', 'calle_solar',
                                                       'escalera_sin_destino')})
        + ' | minimos: ' + json.dumps({k: r3(v) for k, v in peor.items()}))
    return {k: r3(v) for k, v in peor.items()}


def verificar(sectores, ctx, terreno):
    from shapely.strtree import STRtree
    lots = []; info = []
    for S in sectores:
        for s in S.solares:
            lots.append(Polygon(s['poligono'])); info.append((S, s))
    fallos = dict(solar_solar=0, solar_elemento=0, solar_fuera_banda=0, calle_cerca_pista=0, elemento_cerca_pista=0,
                  solar_terreno=0, calle_terreno=0, muro_terreno=0, relleno_asoma=0, salto_z_calle=0, salto_z_costura=0)
    tree = STRtree(lots) if lots else None
    sep_min = 99.0
    for i, lot in enumerate(lots):
        if tree is None:
            break
        for j in tree.query(lot.buffer(0.98)):
            if j != i and lots[j].intersects(lot.buffer(0.98)):
                fallos['solar_solar'] += 1
        for j in tree.query(lot.buffer(3.0)):
            if j != i:
                sep_min = min(sep_min, lot.distance(lots[j]))
    elementos = []
    for S in sectores:
        for c in S.calles + S.travesias + S.enlaces:
            elementos.append(LineString([p[:2] for p in c['pts']]).buffer(c['ancho'] / 2.0, cap_style='flat'))
        for r in S.rampas:
            elementos.append(Polygon(r['relleno']).buffer(0.6) if len(r['relleno']) >= 4 else LineString([p[:2] for p in r['pts']]).buffer(r['ancho'] / 2.0 + 0.6))
        for e in S.escaleras:
            for tr in e['tramos']:
                elementos.append(LineString([p[:2] for p in tr['pts']]).buffer(e['ancho'] / 2.0, cap_style='flat'))
            if e['descansillo']:
                elementos.append(Polygon([p[:2] for p in e['descansillo']]))
            if e['pasarela']:
                elementos.append(LineString([p[:2] for p in e['pasarela']]).buffer(e['ancho'] / 2.0, cap_style='flat'))
        for m in S.muros:
            elementos.append(LineString([p[:2] for p in m['pts']]).buffer(1.0 if m['tipo'] == 'contencion' else 0.5))
        for p in S.plazas:
            elementos.append(Polygon(p['poligono']))
    bp = prep(union(elementos + [ctx['asf_casa'], ctx['pit8']]))
    peor = dict(solar=[0.0, 0.0], calle=[0.0, 0.0])
    for (S, s), lot in zip(info, lots):
        if bp.intersects(lot):
            fallos['solar_elemento'] += 1
        if not S.bandas[s['terraza']].buffer(0.3).contains(lot):
            fallos['solar_fuera_banda'] += 1
        cs = list(lot.exterior.coords)[:4]
        dev = terreno.zs([q[0] for q in cs], [q[1] for q in cs]) - s['z_suelo']
        dev_m = terreno.zs_malla([q[0] for q in cs], [q[1] for q in cs]) - s['z_suelo']
        peor['solar'] = [min(peor['solar'][0], float(dev.min())), max(peor['solar'][1], float(dev_m.max()))]
        if dev.min() < -0.6 or dev_m.max() > 1.2:           # criterio T6 (asentar_objetos.py); enterrada: con la MALLA
            fallos['solar_terreno'] += 1
    d_calle_min = 999.0; costuras_dev = []
    for S in sectores:
        for c in S.calles + S.travesias:
            ln = LineString([p[:2] for p in c['pts']])
            d = ctx['asfalto'].distance(ln)
            d_calle_min = min(d_calle_min, d)
            if d < float(S.spec['calle_desde']) + S.AC / 2.0 - 0.3:   # 0.3 (antes 0.15): la cuerda de una union de costura en curva entra hasta 0.25 m (casino_mar)
                fallos['calle_cerca_pista'] += 1
            xs = [p[0] for p in c['pts']]; ys = [p[1] for p in c['pts']]; zs = np.array([p[2] for p in c['pts']])
            dev = terreno.zs(xs, ys) - zs; dev_m = terreno.zs_malla(xs, ys) - zs
            libre = np.ones(len(zs), bool)
            ci = c.get('costura_idx')
            if ci:
                libre[ci[0]:ci[1] + 1] = False          # cuesta de union de costura: se informa en qa.costuras
                costuras_dev.append(dict(calle=c['id'], dev_max=r3(float(np.abs(dev[~libre]).max()))))
            peor['calle'] = [min(peor['calle'][0], float(dev[libre].min())), max(peor['calle'][1], float(dev_m[libre].max()))]
            fallos['calle_terreno'] += int(((dev[libre] < -TOL_CALLE[0]) | (dev_m[libre] > TOL_CALLE[1])).sum())
            if len(zs) > 1:
                seg = np.hypot(np.diff(xs), np.diff(ys)); seg[seg < 0.5] = 0.5
                pend = np.abs(np.diff(zs)) / seg
                fallos['salto_z_calle'] += int((pend[libre[:-1] & libre[1:]] > 0.5).sum())
                fallos['salto_z_costura'] += int((pend > PEND_UNION + 0.15).sum())
        for e in S.enlaces:
            p1 = e['pts'][0]; pm = e['pts'][1]
            dev = terreno.zs([p1[0], pm[0]], [p1[1], pm[1]]) - np.array([p1[2], pm[2]])
            fallos['calle_terreno'] += int(((dev < -TOL_CALLE[0]) | (dev > TOL_CALLE[1])).sum())
        for r in S.rampas:
            d = ctx['asfalto'].distance(LineString([p[:2] for p in r['pts']])) - r['ancho'] / 2.0
            if d < MARGEN - 0.05:
                fallos['elemento_cerca_pista'] += 1
            dev = terreno.zs_malla([p[0] for p in r['pts']], [p[1] for p in r['pts']]) - np.array([p[2] for p in r['pts']])
            fallos['relleno_asoma'] += int((dev > TOL_RELLENO).sum())
        for e in S.escaleras:
            for tr in e['tramos'] + ([dict(pts=e['pasarela'])] if e['pasarela'] else []):
                d = ctx['asfalto'].distance(LineString([p[:2] for p in tr['pts']])) - e['ancho'] / 2.0
                if d < MARGEN - 0.05:
                    fallos['elemento_cerca_pista'] += 1
                dev = terreno.zs_malla([p[0] for p in tr['pts']], [p[1] for p in tr['pts']]) - np.array([p[2] for p in tr['pts']])
                fallos['relleno_asoma'] += int((dev > TOL_RELLENO).sum())
        for m in S.muros:
            xs = [p[0] for p in m['pts']]; ys = [p[1] for p in m['pts']]
            terr = terreno.zs(xs, ys); terr_m = terreno.zs_malla(xs, ys)
            zb = np.array([p[2] for p in m['pts']]); zt = np.array([p[3] for p in m['pts']])
            fallos['muro_terreno'] += int(((terr < zb - TOL_MURO[0]) | (terr_m > zt + TOL_MURO[1])).sum())
    stats = {}
    for S in sectores:
        for tipo, vals in S.terr_stats.items():
            stats.setdefault(tipo, []).extend(vals)
    stats = {t: dict(n=len(v), min=r3(min(v)), mediana=r3(float(np.median(v))), max=r3(max(v))) for t, v in stats.items() if v}
    huellas = verificar_huellas(sectores, ctx, terreno, fallos)
    huellas['minimos_v1'] = verificar_v1(sectores, ctx, fallos)
    casas = sum(1 for (S, s) in info if s['tipo'] == 'casa')
    res = dict(casas_total=casas, solares_total=len(lots), separacion_min_solares=r3(sep_min), **huellas,
               dist_min_eje_calle_asfalto=r3(d_calle_min), fallos=fallos, peor_desvio_terreno=peor,
               terreno=stats, costuras=[u for S in sectores for u in S.uniones], costuras_desvio_terreno=costuras_dev,
               descartes=[d for S in sectores for d in S.descartes])
    log('QA: ' + json.dumps(dict(res, descartes=len(res['descartes']), costuras=len(res['costuras']))))
    return res

# ---------------------------------------------------------------------------
# QA: dibujo por sector
# ---------------------------------------------------------------------------
def _pinta(ax, geom, MPoly, **kw):
    geoms = list(geom.geoms) if hasattr(geom, 'geoms') else [geom]
    for gm in geoms:
        if gm.is_empty or not hasattr(gm, 'exterior'):
            continue
        ax.add_patch(MPoly(list(gm.exterior.coords), closed=True, **kw))

def _banda_llana(S, k):
    b = S.b[k]
    if not b['ok']:
        return Polygon()
    a = S.curva(b['u_lo']); c = S.curva(b['u_hi_casa'])
    if a is None or c is None:
        return Polygon()
    return Polygon([tuple(p) for p in a.xy] + [tuple(p) for p in c.xy][::-1]).buffer(0)

def _dibujar_elementos(S, ctx, ax, caja, MPoly, cotas=False, dentro=None):
    dentro = dentro or (lambda p: True)
    _pinta(ax, ctx['asf6'].intersection(caja), MPoly, fc='#d8d8d8', ec='none')
    _pinta(ax, ctx['asfalto'].intersection(caja), MPoly, fc='#6e6e6e', ec='none')
    if not ctx['pit8'].is_empty:
        _pinta(ax, ctx['pit8'].intersection(caja), MPoly, fc='#e8d8d8', ec='none', alpha=0.6)
    for k in range(S.n):
        _pinta(ax, _banda_llana(S, k).intersection(caja), MPoly, fc='#e6f2d8', ec='none')
    for k, b in S.bandas.items():
        _pinta(ax, b, MPoly, fc='none', ec='#b0a080', ls='--', lw=0.6)
    for r in S.rampas:
        if len(r['relleno']) >= 4:
            _pinta(ax, Polygon(r['relleno']), MPoly, fc='#f6d7b0', ec='#b06a20', lw=0.5)
    for m in S.muros:
        ax.plot([p[0] for p in m['pts']], [p[1] for p in m['pts']], color='#7a3b10', lw=2.0 if m['tipo'] == 'contencion' else 1.0)
        if cotas:
            for p in m['pts'][::6]:
                if dentro(p):
                    ax.text(p[0], p[1], '%.0f/%.0f' % (p[2], p[3]), fontsize=6, color='#7a3b10')
    for c in S.calles + S.travesias:
        _pinta(ax, LineString([p[:2] for p in c['pts']]).buffer(c['ancho'] / 2.0, cap_style='flat'), MPoly, fc='#4f86c6', ec='none')
        if cotas:
            for p in c['pts'][::5]:
                if dentro(p):
                    ax.text(p[0], p[1], '%.1f' % p[2], fontsize=6, color='navy')
    for e in S.enlaces:
        _pinta(ax, LineString([p[:2] for p in e['pts']]).buffer(e['ancho'] / 2.0, cap_style='flat'), MPoly, fc='#2a5fa8', ec='none')
    for r in S.rampas:
        _pinta(ax, LineString([p[:2] for p in r['pts']]).buffer(r['ancho'] / 2.0, cap_style='flat'), MPoly, fc='#f08c2e', ec='#8a4a10', lw=0.5)
        n_ = len(r['pts']); pa, pb = r['pts'][int(n_ * 0.3)], r['pts'][int(n_ * 0.7)]
        if pa[2] > pb[2]:
            pa, pb = pb, pa
        ax.annotate('', xy=(pb[0], pb[1]), xytext=(pa[0], pa[1]), arrowprops=dict(arrowstyle='-|>', color='#5a2a00', lw=1.4))
        if cotas:
            for p in r['pts'][::4]:
                if dentro(p):
                    ax.text(p[0], p[1], '%.1f' % p[2], fontsize=6, color='#5a2a00')
            for mu in r['muros_rampa']:
                ax.plot([p[0] for p in mu['pts']], [p[1] for p in mu['pts']], color='#b01010', lw=1.5)
    for e in S.escaleras:
        for tr in e['tramos']:
            _pinta(ax, LineString([p[:2] for p in tr['pts']]).buffer(e['ancho'] / 2.0, cap_style='flat'), MPoly, fc='#9b59b6', ec='none')
            if cotas:
                for p in (tr['pts'][0], tr['pts'][-1]):
                    if dentro(p):
                        ax.text(p[0], p[1], '%.1f' % p[2], fontsize=6, color='purple')
        if e['descansillo']:
            _pinta(ax, Polygon([p[:2] for p in e['descansillo']]), MPoly, fc='#c39bd3', ec='#6c3483', lw=0.5)
        if e['pasarela']:
            _pinta(ax, LineString([p[:2] for p in e['pasarela']]).buffer(e['ancho'] / 2.0, cap_style='flat'), MPoly, fc='#d7bde2', ec='#6c3483', lw=0.5)
    for p in S.plazas:
        _pinta(ax, Polygon(p['poligono']), MPoly, fc='#f5d76e', ec='#8a6d00', lw=0.8)
        ax.plot(p['fuente'][0], p['fuente'][1], 'o', color='#1f6fd0', ms=4)
    for s in S.solares:
        col = '#a8d08d' if s['tipo'] == 'plazoleta' else '#e9c9a0'
        _pinta(ax, Polygon(s['poligono']), MPoly, fc=col, ec='#333333', lw=0.5)
        if s['tipo'] == 'casa':
            L = min(s['fondo'], 6.0)
            ax.annotate('', xy=(s['px'] + s['fx'] * 1.5, s['py'] + s['fy'] * 1.5), xytext=(s['px'] - s['fx'] * (L - 1.5), s['py'] - s['fy'] * (L - 1.5)),
                        arrowprops=dict(arrowstyle='->', color='#b00000', lw=0.9))
        if cotas and dentro((s['cx'], s['cy'])):
            te = s['terreno_esquinas']
            ax.text(s['cx'], s['cy'], '%dx%d %dp z%.0f\n%+.1f %+.1f' % (s['ancho'], s['fondo'], s['plantas'], s['z_suelo'], min(te), max(te)),
                    fontsize=5.5, ha='center', va='center')
    for v in S.vallas:
        dx, dy = math.cos(v['rot_z']) * v['largo'] / 2, math.sin(v['rot_z']) * v['largo'] / 2
        ax.plot([v['x'] - dx, v['x'] + dx], [v['y'] - dy, v['y'] + dy], color='#d01010', lw=2.5)
    for sal in S.salidas:
        ax.plot(sal['x'], sal['y'], marker='^', color='k', ms=8)
        ax.annotate('', xy=(sal['x'] + sal['dx'] * 12, sal['y'] + sal['dy'] * 12), xytext=(sal['x'], sal['y']),
                    arrowprops=dict(arrowstyle='->', color='k', lw=1.2))
    for u in S.uniones:
        if not dentro(u['a']):
            continue
        ax.plot([u['a'][0], u['b'][0]], [u['a'][1], u['b'][1]], color='#ff00aa', lw=3.0)
        ax.text(u['a'][0], u['a'][1], 'costura dz %.1f' % u['dz'], fontsize=6, color='#ff00aa')

def dibujar(S, ctx, ruta):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly
    todo = union([b for b in S.bandas.values()] + [Polygon(s['poligono']) for s in S.solares])
    x0, y0, x1, y1 = todo.bounds
    x0 -= 40; y0 -= 40; x1 += 40; y1 += 40
    esc = 1.0 / 32.0
    fig, ax = plt.subplots(figsize=(max(8, (x1 - x0) * esc), max(6, (y1 - y0) * esc)), dpi=110)
    caja = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    _dibujar_elementos(S, ctx, ax, caja, MPoly)
    if os.environ.get('URB_DEBUG') and getattr(S, 'rech_xy', None):
        cols = dict(fondo='magenta', lejos_calle='cyan', solape='orange', fuera_banda='green', pliegue='black', vecino='grey', terreno='red')
        for mot, col in cols.items():
            pts = [(x, y) for (x, y, m) in S.rech_xy if m == mot]
            if pts:
                ax.plot([q[0] for q in pts], [q[1] for q in pts], '.', color=col, ms=2.5, label=mot)
        ax.legend(fontsize=6, loc='upper right')
    st = S.stats
    ax.set_title('%s  lado %+d  %d terrazas | casas %d plazoletas %d | calles %d (%.0f m) travesias %d rampas %d escaleras %d muros %d enlaces %d salidas %d plazas %d | verde = banda llana real'
                 % (S.id, S.lado, S.n, st['casas'], st['plazoletas'], st['calles'], st['largo_calles'], st['travesias'], st['rampas'],
                    st['escaleras'], st['muros'], st['enlaces'], st['salidas'], st['plazas']), fontsize=8)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(True, lw=0.3, alpha=0.5)
    fig.tight_layout(); fig.savefig(ruta); plt.close(fig)

def dibujar_detalle(S, ctx, ruta, R=60.0):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly
    if S.travesias:
        its = sorted(set(int(tv['id'].split('_trav')[1].split('_')[0]) for tv in S.travesias))
        it = next((p['it'] for p in S.planes if p.get('ok')), its[0])
        tr = [tv for tv in S.travesias if tv['id'].split('_trav')[1].split('_')[0] == str(it)]
        cx = float(np.mean([p[0] for tv in tr for p in tv['pts']])); cy = float(np.mean([p[1] for tv in tr for p in tv['pts']]))
    elif S.calles:
        it = -1
        c = max(S.calles, key=lambda c: len(c['pts']))['pts']
        cx, cy = c[len(c) // 2][0], c[len(c) // 2][1]
    else:
        return
    dentro = lambda p: abs(p[0] - cx) < R and abs(p[1] - cy) < R
    fig, ax = plt.subplots(figsize=(11, 11), dpi=100)
    caja = Polygon([(cx - R, cy - R), (cx + R, cy - R), (cx + R, cy + R), (cx - R, cy + R)])
    _dibujar_elementos(S, ctx, ax, caja, MPoly, cotas=True, dentro=dentro)
    ax.set_xlim(cx - R, cx + R); ax.set_ylim(cy - R, cy + R); ax.set_aspect('equal'); ax.grid(True, lw=0.3)
    ax.set_title('%s travesia %d (zoom; cotas z: azul calles, naranja rampa, morado escaleras; muros z_base/z_top; casas: desvio terreno esquinas min/max)' % (S.id, it), fontsize=7)
    fig.savefig(ruta, bbox_inches='tight'); plt.close(fig)

# ---------------------------------------------------------------------------
def main(argv):
    ruta_geom, salida, con_qa = RUTA_GEOM, RUTA_SALIDA, True
    i = 0
    while i < len(argv):
        if argv[i] == '--geom':
            ruta_geom = argv[i + 1]; i += 1
        elif argv[i] == '--salida':
            salida = argv[i + 1]; i += 1
        elif argv[i] == '--sin-qa':
            con_qa = False
        i += 1
    g = json.load(open(ruta_geom, encoding='utf-8')); spec = json.load(open(RUTA_SPEC, encoding='utf-8'))
    global LARGO_RAMPA
    LARGO_RAMPA = float(spec.get('rampa_largo_m', LARGO_RAMPA))      # v1: el largo de la rampa sale del contrato (45 m)
    if 'terreno' not in g or 'z' not in g['terreno']:
        raise SystemExit('geometria_3d.json sin rejilla terreno: ejecutar antes preparar_geometria.py (T1)')
    pista = Pista(g)
    terreno = Terreno(g['terreno'])
    log('terreno: rejilla %dx%d cell %.1f m' % (terreno.nx, terreno.ny, terreno.cell))
    global _PISTA
    _PISTA = pista
    asf = pista.poligono_asfalto(); pit = pista.poligono_pit()
    # asf_casa: la fachada va a MARGEN (6.0) del asfalto; en curvas cerradas las esquinas de la fachada recta
    # entran hasta 0.4 m en el margen (cuerda), de ahi la holgura
    ctx = dict(asfalto=asf, asf6=asf.buffer(MARGEN), asf_casa=asf.buffer(MARGEN - 0.4),
               asf_calle=asf.buffer(float(spec['calle_desde']) + float(spec['ancho_calle']) / 2.0 - 0.05),
               pit8=(pit.buffer(8.0) if not pit.is_empty else Polygon()), otros=Polygon(), elipse_casino=_elipse_casino(g))
    # v1 (revision B2/C-03/C-12): ZONAS EXCLUIDAS del spec (huella del McLaren + margen): NADA del plan dentro. Entran en
    # 'otros' (lo evitan rampas, escaleras, enlaces, travesias, muros, plazas y solares) y, engordadas MARGEN_EXCL_CALLE,
    # en 'otros_calles' (las calles se cortan antes: el trozo que queda acaba en su enlace o en su fondo de saco)
    excl = union([Polygon(z_['poligono']).buffer(float(z_.get('margen', 4.0))) for z_ in spec.get('zonas_excluidas', [])
                  if len(z_.get('poligono', [])) >= 3])
    ctx['excluida'] = excl
    ctx['otros'] = excl.buffer(0.2) if not excl.is_empty else excl
    excl_calles = excl.buffer(MARGEN_EXCL_CALLE) if not excl.is_empty else Polygon()
    ctx['otros_calles'] = excl_calles
    if not excl.is_empty:
        log('zonas excluidas: %d (%.1f ha con margen); las calles se cortan a %.0f m mas' % (len(spec.get('zonas_excluidas', [])), excl.area / 1e4, MARGEN_EXCL_CALLE))
    sectores = []
    for sec in spec['sectores']:
        S = Sector(sec, pista, terreno, spec, ctx)
        S.construir()
        sectores.append(S)
        ctx['otros'] = union([ctx['otros']] + [p.buffer(1.0) for p in S.F_propio + list(S.F_calles.values())] + [Polygon(s['poligono']).buffer(1.0) for s in S.solares])
        ctx['otros_calles'] = union([ctx['otros'], excl_calles])
    qa = verificar(sectores, ctx, terreno)
    notas = ['RONDA 15c: z = Zb + altura_rel, Zb = terreno_montana.CotaSector (la MISMA cota base con la que T1 talla las terrazas; '
             'fuera de la banda, Z de la muestra mas cercana del sector); +0.05 en calles/travesias/rampas/escaleras; z_suelo de solares sin +0.05',
             'terrazas[k]: u_lo/u_hi/u_hi_casa = banda llana REAL medida en la rejilla terreno; u_calle/u_fachada/fondo_max = lo usado (contrato salvo que el terreno obligue a desplazar hacia fuera)',
             'calles cortadas donde el terreno discrepa (> %.1f por encima / > %.1f por debajo del eje) o hay costura; extremos enfrentados a <= %.0f m unidos con cuesta <= %.0f %% (qa.costuras)' % (TOL_CALLE[1], TOL_CALLE[0], UNION_MAX, PEND_UNION * 100),
             'solar: (px,py) = centro de fachada = pivote de casas_kit_v2.build_casa; rot_z = atan2(fy,fx) - pi/2; cuerpo hacia -(fx,fy); terreno_esquinas = terreno - z_suelo en las 4 esquinas',
             'rampa: relleno sobre la banda llana de la terraza baja (huella "relleno" hasta la linea del muro) + codo a nivel en la meseta hasta la calle superior (ladera) o la travesia superior (mar); muros_rampa = caras libres (z_base terreno, z_top superficie)',
             'escalera idavuelta: tramos[0] arranca junto a la travesia, tramos[1] vuelve; descansillo 1.6 x 3.2 m; pasarela = tramo a nivel que cruza el talud del muro',
             'muros: z_base/z_top por vertice; cortados en travesias/codos/pasarelas y donde el terreno real sale de [z_base-0.6, z_top+0.3]']
    datos = dict(version=2, notas=notas,
                 spec=dict(spec, margen_pista=MARGEN, ancho_rampa=ANCHO_RAMPA, largo_rampa=LARGO_RAMPA,
                           meseta_rampa=MESETA_RAMPA, ancho_escalera=ANCHO_ESCALERA, largo_escalera=LARGO_ESCALERA,
                           tol_calle=list(TOL_CALLE), tol_solar=list(TOL_SOLAR), tol_muro=list(TOL_MURO), tol_relleno=TOL_RELLENO),
                 sectores=[S.exportar() for S in sectores], qa=qa)
    json.dump(datos, open(salida, 'w', encoding='utf-8'), separators=(',', ':'))
    log('escrito %s (%.1f MB)' % (salida, os.path.getsize(salida) / 1e6))
    if con_qa:
        os.makedirs(DIR_QA, exist_ok=True)
        for S in sectores:
            ruta = os.path.join(DIR_QA, 'urbanismo_%s.png' % S.id)
            dibujar(S, ctx, ruta); log('QA png ' + ruta)
            dibujar_detalle(S, ctx, os.path.join(DIR_QA, 'urbanismo_detalle_%s.png' % S.id))
    total = sum(S.stats['casas'] for S in sectores)
    log('TOTAL casas %d (objetivo >= 190) | huecos > 12 m entre solares de una fila: %.0f m (objetivo < 300) | terrazas vacias: %d'
        % (total, qa['huecos_suma_m'], len(qa['terrazas_vacias'])))
    assert sum(qa['fallos'].values()) == 0, 'QA con fallos: %s' % qa['fallos']
    return datos

if __name__ == '__main__':
    main(sys.argv[1:])
