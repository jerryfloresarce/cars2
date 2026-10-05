# terreno_montana.py - RONDA 15 (T1): el terreno es un MACIZO DE MONTANA.
# Sustituye la seccion 'rejilla de terreno' de preparar_geometria.py.
#
#   construir(X, Y, Z, sec, Wd, nx, ny, paso, L, curvas, pit_pts, loews_centro,
#             spec_urb, miradores, cell=4.0, qa_dir=None)
#       -> dict(x0, y0, cell, nx, ny, z_grid, es_mar, extras)
#   extras = {'cumbres': [(x,y,z)...], 'mascara_roca': array (0..1 por celda),
#             'protegido': array bool, 'coastF': array, 'checks': dict}
#
# Diseno (numpy/scipy, python del sistema):
#   1. Macizo base M(x,y) = soft-max de LANDFORMS (cordales con perfil concavo
#      h*(1-d/R)^p, contornos modulados con ruido -> crestas y vaguadas radiales)
#      + ruido 'ridged' multi-octava (340/170/85/42 m) proporcional a la cota
#      - canales de drenaje (valles, profundidad acotada a 0.3 x min(M, 80)).
#      Despues un LIMITADOR DE PENDIENTE (erosion con cono, 80 %) sobre el
#      campo natural: ninguna ladera natural pasa del 80 %; los unicos > 100 %
#      son acantilados al mar y caras de desmonte.
#   2. La superficie se 'tira' hacia la rasante de la pista (nucleo gaussiano
#      de 100 m) para que la pista quede SOBRE la ladera (pendiente transversal
#      conservada): pared de roca a un lado, caida al otro.
#   3. Reglas duras (sin suavizar despues): corredor (d < w/2+6 -> z_pista-0.5),
#      desmonte z <= Zp+0.4+(d-6)*1.15 y terraplen z >= Zp-0.6-(d-6)*0.55. La
#      regla del PROPIO ramal usa la muestra mas cercana (en una subida las
#      muestras de atras NO imponen su techo); contra OTROS ramales (a < 180 m,
#      la pista vuelve sobre si misma) manda el minimo/maximo (horquillas,
#      lazos, esquinas). Terrazas del pueblo desde urbanismo_spec.json (RONDA
#      15b, perfil_terrazas(): bordillo u<1.0 a -0.4, rampa a +-0.5 en 1.5,
#      bandas LLANAS de 21 m en todo s0..s1 a 0.5/6.5/12.5, rampa del muro en
#      u_local 18.5..21 (lado de la terraza k) y la k+1 llana desde 21(k+1);
#      sentido sube/baja por sentido_terrazas() (id '_mar' baja), NO por el
#      lado; detras de la ultima terraza desmonte 1.15 / terraplen 0.55
#      referidos a su cota, minimo/maximo entre las ramas del sector; fundido
#      de 30 m SOLO fuera del sector; cota = MEZCLA ponderada de Z en s (peso
#      gaussiano en d_j - d_min con anchura 0.5*o: campo C0 sin escalones en el
#      eje medial de las curvas cerradas) hasta 180 m; donde otro ramal esta
#      mas cerca mandan su corredor y su terraplen, y fuera del corredor un
#      muro al 300 %),
#      estribos del viaducto, caja del pit (28 m llanos + 22 % hasta 100 m,
#      luego 1.15; NUNCA por debajo del corredor/terraplen de otra calzada ni
#      de una terraza (version 'muro' a 49 grados); desde el borde del pit lane
#      el terreno sube como mucho al 300 % = muro de contencion), miradores
#      (banco Z-10 SOLO si ese lado mira al mar), garganta de mar bajo el
#      viaducto, costa continua (union exacta de discos de proteccion + mascara
#      gaussiana 12 m; lagunas eliminadas), la isla se cierra con mar a ~460 m
#      de la pista (radio modulado con ruido) y el borde de la rejilla cae a
#      <= 2 m. Garantia final: corredor a Z-0.5 en d < w/2+1.0 (en los sectores
#      con terraza el bordillo arranca ahi; fuera de sectores, corredor de 6 m).
#   QA 15b (impresa y en checks): costuras (|dz| entre celdas vecinas de la
#      misma terraza fuera de rampas, objetivo < 0.6 m), cobertura s0..s1 por
#      sector con la causa de cada tramo no aterrazado, y geografia (el sentido
#      sube/baja frente al terreno natural; aviso de 'bastion').
#   RONDA 15c (revision): (1) entre dos ramas ENFRENTADAS del sector (horquilla)
#      la cota se mezcla con una smoothstep desde u = fachada (7 m) de cada rama:
#      talud continuo en vez de escalon; se informa aparte como 'talud entre
#      ramas' (no es costura). (2) Los valles no excavan en las bandas de terrazas
#      (+25 m, fundido 60 m) y detras de la ultima terraza el foso se rellena
#      (cierre morfologico 84 m: si la montana vuelve a subir, el suelo no baja
#      de la cota de la terraza; sube al 30 % en los sectores de ladera).
#      (3) Penon del casino: la elipse de zona_casino() es mar en su nucleo y en
#      la bahia seaward, el interior cae al 400 % bajo la roca y la ladera N
#      queda <= 121 m; el cordal del promontorio acaba a > 100 m de la entrada.
#      (4) Espolon del coche: desmonte al 200 % detras de las terrazas de la
#      tecnica que miran al tunel (el punto a 120 m detras del coche cae DENTRO
#      de esas terrazas para s >= 460: ahi la clausula es incompatible con el
#      spec). (5) QA: foso tras la ultima terraza, contorno del penon, titulos
#      de terreno_costuras.png por sector.
#   RONDA 15c (densidad del pueblo): (6) sentido_terrazas lee el campo 'sentido'
#      del spec ('sube'|'baja', manda sobre la regla por id). (7) curvas_en_metros:
#      si las curvas llegan en unidades del SVG se pasan a metros (la elipse del
#      penon salia 1.2 km al NE). (8) FOSOS: tras las terrazas, relleno (terraplen)
#      hasta el nivel de 'agua atrapada' del perfil normal de cada muestra
#      (perfiles_tras_terraza + nivel_agua, cortado en corredores de otros ramales,
#      mar y terrazas ajenas), con bordes al 55 % y pasadas hasta converger; la QA
#      mide la profundidad de agua atrapada (objetivo <= 1.5 m) y el criterio
#      antiguo. (9) el desmonte del espolon del coche usa un peso continuo (antes
#      booleano: escalones de 20-30 m en la ladera de la C6). (10) mezcla_cota /
#      CotaSector: la cota base de las terrazas es UNA funcion que usan construir()
#      y urbanismo.py (calles, casas, muros a la cota exacta que se talla).
#   4. extras: cumbres (maximos locales del campo final) y mascara_roca
#      (v1: pendiente > 85 % o cumbre > 185 m con pendiente > 50 %, desmontes de la pista = roca entera).
#   RONDA 15 v1 (revision de los tramos A-J; cada cambio lleva su comentario 'v1 (revision X)'):
#      Promontorio del casino bajo (G1/G4) con el terreno de la rotonda Loews CONGELADO (construir_loews_intacta);
#      la regla de costa solo se anula dentro del contorno del penon (G4/G10) y la bahia llega a r 2.6 (G11);
#      estribos del viaducto sin zanja (I1) y lungomare llano en la llegada (I3); caja del pit sin la doble rampa
#      detras del hotel (J4/B10) y sin actuar detras de otra calzada (F-12); cono de s 320-402 aplanado (B8); banco
#      del mirador fuera del paseo (F-01/G12); distancia al mar con precision de subcelda (A-09/H3); costa natural
#      con orilla continua (J6/B12), costa N/NE en ladera y no en pared (J1, ruido tras el limitador), costa de la
#      bahia al 130 % lejos del viaducto (F-07), aleta del canal del viaducto a mar (H2), borde O en mar (J5),
#      vega con drenaje (J8), mascara de roca (C-15/D14/E8/J12/I4).
#   RONDA 15 v2 (pueblo_terreno, revision r2; comentarios 'v2 (revision X)'): referencia FIJA de la Loews en
#      assets/_loews_terreno.npz (J-N2); garantia POR TRIANGULO de hierba sobre el asfalto con el peralte (bajar_bajo_asfalto,
#      C2-01/D2-01/G2-03/E2-01/F2-11); techo de desmonte C1 (B2-05/D2-11); tiron local junto al penon (J2-01/J2-03),
#      distancia al mar sin el mar forzado del penon (J2-02), fundido doble de la pendiente de costa (J2-04/H2-3), costa N sin
#      codo (J2-06), drenaje de la vega desde 60 m (J2-10), costa irregular lejos de la pista (I-R2-02), paseo-mirador sin
#      hierba (F2-03) y extremos del banco en acuerdo (F2-07), vaguada bajo el arranque del viaducto (G2-04), lungomare hasta
#      s 5200 (N2-A), pared de la caja del pit irregular (A-r2-07), costillas de erosion en las caras de desmonte (B2-09/C2-11/
#      E2-07/F2-01), minimo suave entre ramas (E2-07), mascara de roca por profundidad de corte (A-r2-12/A-r2-07), pozos de la
#      orilla rellenos (J2-09), suelo en el interior de las horquillas (E2-08).
#   RONDA 15 v3 (pueblo_terreno, revision r3; comentarios 'v3 (revision X)'): canal del viaducto con mar forzado de radio
#      variable, coronacion por minimo suave k 10 y costillas de 30/15 m (H2/H3); modulacion de costa tambien en los
#      acantilados a > 25-45 m de la pista (bahia, recta 30-31, gancho S, canal) con pie de derrubios y repisas (J1/I4); tope
#      1.5 del termino del macizo lejos del viaducto (F-07); orilla continua junto a la pista (J6/B12); barrancos que siguen las
#      lineas de agua en el macizo lejos de la pista (N1); mascara de roca natural por pendiente suavizada > 1.0, sin manchas
#      sueltas (N1/C-15), arista con desenfoque de 2 celdas (H3), pie y escalon de la garganta en roca (I4/G10); bancales en la
#      cara tras la ultima terraza de los sectores de pueblo y coronacion suave (C-02); picos convexos suavizados (G4); pared de
#      la caja del pit con limitador al 92 % (B10); banco del mirador fuera de los 6 m extremos del paseo (F-01); nodos del
#      tunel bajo la rasante (B5). Nada de eso toca la Loews (< R_LOEWS_INTACTA, tambien la mascara), el entorno del penon
#      (r < 1.9), la huella del McLaren (zonas_excluidas + 10/25 m) ni el corredor de la pista.
#   FASE VISUAL F1 (propietario 'terreno', 04/10; comentarios 'F1 (bloque X)'; plan FASE_VISUAL_PLAN.md secc. 5 y 4):
#      (1.1) TIERRA TALLADA en s 1540-2440 (TIERRA_TALLADA_S; 1430-1540 son las terrazas de pueblo_alto): por muestra se
#      elige el LADO ALTO (donde el terreno natural z_land es mas alto a 40 m; si empata, el interior de la curva) y por
#      celda: en el lado alto el desmonte C1 pasa de 1.15 a TIERRA_PEND_INT (63 grados) y hay una LADERA MINIMA (suelo)
#      al 85 % hasta +TIERRA_PARED_H (pared de roca tambien donde el tiron a la rasante aplanaba la ladera); en el lado
#      bajo berma llana TIERRA_BERMA (7.5 m > w/2+6.75 del cierre_ac), terraplen hasta TIERRA_SFL_EXT y una CAIDA
#      MINIMA (techo) al 45 % hasta -TIERRA_CAIDA_H. Todo acotado por techo/suelo de TODOS los ramales (nunca bajo el
#      corredor de otra rama), apagado a < 25-40 m de otra rama (islas de horquilla), donde el natural exterior sube
#      (pie del macizo) y con fundidos en s y en distancia. El peso del tiron en tierra es TIERRA_PESO_TIRON (relativo).
#      (1.1 v2, sesion 2) BANCO DE HORQUILLA: donde una rama plegada (rumbo opuesto, > 40 m por la pista y < 80 % en recta, a
#      < 45 m de la celda) esta >= TIERRA_BANCO_DZ mas alta que la muestra, la isla sube de la rama baja a la alta (lomo con la
#      altura de la rama alta, sin el apagado de 'otra rama', solo entre las dos ramas) y queda fuera de la caja del pit y de su
#      limitador B10; el tramo de terrazas usa como base el natural + lomo - vaguada (antes recalculaba desde z_land a 180 m
#      de pueblo_alto_mar y borraba el banco); fac_sect a 21n + 45 m (perfil de la QA de fosos); caida 0.45 -> 0.55.
#      Umbrales de roca importados de mascara_terreno.UMBRALES (PARCHES_F1_mascara A2); medidas en _rev/medir_relieve.py.
#      (1.2) BERMA de 15-25 m (ruido 60 m) entre el patio de la ultima terraza y el arranque de la cara, bancales
#      BANCO_H 11.5 / BANCO_A 1.65 (= 0.9*H/2pi: amplitud maxima sin invertir la pendiente) y costillas hasta 4 m en
#      caras > 20 m; solo en sectores pueblo_* fuera del espolon del coche (la berma retrasa la cara 20 m: rebajaria
#      37 m el espolon a 120 m del tunel) y del McLaren.
#      (2.2) ROCA POR PENDIENTE: umbral natural ROCA_UMBRAL_PEND +- ROCA_UMBRAL_RUIDO (35-40 grados) con apertura 3x3 y
#      manchas >= ROCA_MIN_CELDAS; PIE DE DERRUBIOS (ROCA_PIE_VALOR) a ROCA_PIE_M bajo cada afloramiento. Constantes
#      exportadas (umbrales_roca()) para mascara_terreno.py y color_ac.
#      (1.6) CAPAS para la mascara por texel: extras['capas'] = {matorral, hierba_seca, tierra, roca} (0..1, suma 1)
#      por celda (pendiente, z, dist_mar, dedge0, acantilado, desmonte, sectores, cumbres); mascara_roca se mantiene.
#      QA: checks pared_y_caida_25m_pct, pct_pista_con_pared_roca_tierra, celdas_35_roca_pct, erosion_corredor_dz_max
#      (0.000: la erosion es F4) y figura terreno_capas.png. Medidas independientes: _rev/medir_relieve.py.
#   FASE VISUAL F1 RONDA 2 (director_f1_r1.md problemas 2, 3, 9 y 12; comentarios 'F1 r2'):
#      - El lomo de la tierra es una LOMA redondeada (subida 1-(1-u)^2.5 en 20 m, cresta 18 m, bajada con acuerdo, cresta
#        que serpentea +-4 m) con costillas tambien en su cara (relleno > 2 m, a < 20 m del borde): la 'piramide facetada'
#        de la postal 56 era la tienda lineal con meseta plana y caras planas. Vaguada con arranque parabolico (2 m) y
#        fondo redondeado; caida 0.55 -> 0.60 y ruido 0.9-1.2 (el KPI de 25 m se perdia por ruido en s 1670/1690/2000).
#      - Lomo y vaguada a 0 en el corredor (< 4.5 m del borde de asfalto MAS CERCANO, propio u otro ramal) y el peso del
#        tiron de la tierra solo cambia z_land dentro de la tierra (< 100 m de una muestra dirt, fundido a 160) y fuera del
#        corredor: celdas con |dz| > 0.5 respecto a la base 13 522 -> 6 872, McLaren + 10 m 0.000.
#      - Lo nuevo de F1 cerca del McLaren (bancales en el espolon, berma, costillas de 4 m) con margen +30 m (_w_mcl_f1).
#      - Berma tras la ultima terraza: acuerdo parabolico de 3 m con la cara, cara x1.8 (2.07) y bancales en fase cero al
#        final de la berma (A (1 - cos)): terreno a 120 m tras pueblo_subida_ladera 78.1 -> 83.0 m (= base) y fosos 0.
#      - Banda de los perfiles de la QA de fosos (o_fin-3..+40 por la normal de cada muestra del sector) sin lomo/vaguada.
#      - Capas: el canal B (tierra) de los cortes someros es continuo con ruido de 15 m en pendiente y profundidad (toma 36).
#      - Probado y DESACTIVADO: lomo minimo de 10 m (TIERRA_PARED_H_MIN): +0.2 % de PyC por 131 celdas levantadas. El KPI
#        'pared Y caida a 25 m' se queda en 25.5 % (obj 40) por geometria: las ramas del zigzag van a ~50 m con 10-14 m de
#        desnivel y a 25 m solo UNA de cada par puede tener pared y caida (a 20 m: 27.3 %, a 15 m: 11.3 %); ver PARCHES r2.
#   Prueba aislada: python terreno_montana.py [qa_dir]  (usa la copia
#   assets/_geom_snapshot_terreno.json). debug_xy=[(x,y),...] imprime el valor
#   de cada etapa en esas celdas.
import math
import os as _osp

import numpy as np
from scipy.ndimage import (zoom as _zoom, gaussian_filter, gaussian_filter1d, distance_transform_edt,
                           label as _label, maximum_filter, map_coordinates, binary_dilation, grey_closing,
                           grey_dilation, binary_opening, maximum_filter1d)
from scipy.spatial import cKDTree

NIVEL_MAR = 0.0
Z_FONDO_MAR = -4.0
R_ISLA = 460.0          # mas alla de esta distancia de la pista (modulada +-15 % con ruido) todo es mar
PEND_NATURAL_MAX = 0.8  # limitador de pendiente del macizo natural
MISMO_RAMAL = 0.7       # dos muestras a <= 40 m por la pista son el mismo ramal si la distancia recta es >= 70 % de la de pista
ESTRIBO_M = 60.0        # primeros/ultimos metros del viaducto sin garganta de mar (el tablero sale del acantilado)
DS_PROPIO = 12.0        # un punto esta en la normal 'propia' de una muestra si su muestra mas cercana esta a <= 12 m por la pista

# ---------------------------------------------------------------------------
# LANDFORMS: cordales (x, y, h) + pendiente media al pie (s_foot) + exponente p
# Coordenadas REALES de geometria_3d.json (meta (-176,112), tunel (-605,356),
# cima del lazo de tierra (47,569), casino C36-C38 (555..565,-476..-530),
# rotonda Loews (600,-615)).
# ---------------------------------------------------------------------------
LANDFORMS = [
    # (a) Monte Porto Corsa: cordal E-O al norte del lazo de tierra; cumbre 235 m
    dict(nombre='Monte Porto Corsa', s_foot=0.36, p=1.4,
         pts=[(-330, 900, 160), (-150, 830, 194), (-40, 775, 220), (120, 760, 190),
              (300, 720, 196), (480, 640, 150), (650, 560, 100), (820, 480, 70)]),
    # espolones (crestas secundarias) que bajan del cordal: entre ellos van los barrancos
    dict(nombre='espolon SO (hacia el pueblo alto)', s_foot=0.43, p=1.25,
         pts=[(-40, 775, 220), (-120, 680, 178), (-170, 590, 135), (-205, 500, 92)]),
    dict(nombre='espolon S (el lazo de tierra lo sube)', s_foot=0.43, p=1.25,
         pts=[(-40, 775, 220), (0, 660, 180), (30, 580, 132), (40, 470, 104)]),
    dict(nombre='espolon SE', s_foot=0.43, p=1.25,
         pts=[(120, 760, 198), (185, 640, 160), (205, 530, 118), (175, 430, 92)]),
    dict(nombre='espolon NE', s_foot=0.42, p=1.25,
         pts=[(300, 720, 205), (420, 620, 150), (520, 520, 100)]),
    dict(nombre='espolon N1', s_foot=0.42, p=1.25,
         pts=[(-40, 775, 220), (-70, 900, 168), (-90, 1020, 108)]),
    dict(nombre='espolon N2', s_foot=0.42, p=1.25,
         pts=[(300, 720, 205), (330, 870, 150), (360, 1000, 95)]),
    dict(nombre='espolon O (hacia la vega norte)', s_foot=0.40, p=1.25,
         pts=[(-330, 900, 160), (-440, 800, 115), (-530, 720, 75)]),
    # espolon del coche: el interior de la gran U tunel -> C3 -> tecnica -> C9-C11.
    # Detras del McLaren el macizo sube; la seccion tecnica va por su flanco N.
    # (se disena ALTO a proposito: los desmontes de la tecnica y del tunel lo
    # recortan a 49 grados -> espolon rocoso con caras talladas)
    dict(nombre='Espolon del coche', s_foot=0.47, p=1.3,
         pts=[(-600, 462, 110), (-480, 460, 150), (-380, 430, 150), (-300, 350, 118),
              (-245, 275, 80)]),
    # (c) lomas entre la bajada y la recta 30-31 (al NE del arranque de la recta;
    # NO llegan a la zona del mirador, s 2990-3150, donde el terreno baja)
    dict(nombre='Lomas de la recta', s_foot=0.36, p=1.3,
         pts=[(190, 160, 70), (280, 60, 100), (370, -50, 90), (420, -130, 70)]),
    # (b) promontorio del casino: cordal que acaba en una cumbre de ~170 m al N del
    # penon (RONDA 15c: antes terminaba en (690,-600), DENTRO de la elipse del penon,
    # y lo enterraba; ahora acaba a ~100 m de la entrada del penon y el perfil es
    # concavo (p 1.3) para que la ladera N del penon quede <= CASINO_Z_LADERA)
    # v1 (revision G1/G4, probado por el revisor): el cordal acababa en (665,-470,170) y con el tiron a la rasante dejaba una
    # piramide de 192 m con caras del 112 % que enterraba 11 m la carretera de acceso al penon; ahora es un lomo bajo que
    # se va al E (cumbre ~161 m en (683,-452), detras del penon visto desde la cresta) y el terreno queda bajo esa carretera
    dict(nombre='Promontorio del casino', s_foot=0.40, p=1.3,
         pts=[(560, -300, 80), (660, -380, 95), (770, -430, 100)]),
]

# PENON DEL CASINO (RONDA 15c): misma elipse que integrar_escena.zona_casino() (centro =
# baricentro de las curvas 36-38 desplazado CASINO_DIST hacia fuera del circuito, semiejes
# 118 x 78, giro 0.5 rad). Dentro de la elipse va la roca del penon (assets/roca_casino.py):
# el terreno NO debe asomar por ella -> el interior baja al 400 % desde el contorno hasta el
# mar (y el nucleo r_n < 0.9 es mar), la bahia seaward (angulos CASINO_BAHIA) es mar hasta la
# costa actual, y la ladera N (tierra, por donde entra la carretera) queda <= CASINO_Z_LADERA
# en el contorno subiendo al 80 % hacia la cumbre. El corredor de la pista (rotonda) manda.
CASINO_DIST = 190.0
CASINO_A, CASINO_B, CASINO_ANG = 118.0, 78.0, 0.5
CASINO_Z_LADERA = 121.0      # cota maxima del terreno sobre el contorno (lado tierra)
CASINO_BAHIA = (-130.0, 40.0)  # angulos (grados, desde el centro) del arco de contorno que es mar
CASINO_R_MAR = 0.9           # r normalizado por debajo del cual el interior es mar
CASINO_PEND_INT = 4.0        # caida del terreno hacia dentro del contorno (400 %, bajo la roca)
R_LOEWS_CONG = (40.0, 65.0)  # v1: radio (m) del terreno congelado alrededor de la Loews y del fundido
R_LOEWS_INTACTA = 90.0       # v1: radio alrededor de la rotonda Loews donde los cambios de costa del penon (G4/G10/G11) no actuan
ZONA_COCHE_D = 170.0         # celdas a < 170 m del tunel (s 380-640) y en su lado -1: espolon del coche
PEND_DESMONTE_COCHE = 2.0    # desmonte (63 grados) detras de las terrazas que miran al coche (plan: >= 90 m a 120 m)

# ---------------------------------------------------------------------------
# FASE VISUAL F1 (bloque 1.1): TIERRA TALLADA (s 1430-2440; las reglas actuan desde 1540, pasado pueblo_alto)
# ---------------------------------------------------------------------------
TIERRA_S = (1430.0, 2440.0)          # tramo de tierra (sec == 'dirt')
TIERRA_TALLADA_S = (1540.0, 2440.0)  # donde actuan la ladera interior y la caida exterior (fundido 30 m en los extremos)
TIERRA_PESO_TIRON = 0.5              # peso (relativo) de las muestras de tierra en el tiron a la rasante (_idw_pull)
TIERRA_TIRON_ALCANCE = (60.0, 110.0) # F1 r3: el peso 0.5 solo actua a < 60 m de una muestra de tierra (fundido a 110; r2: 100-160)
TIERRA_PEND_INT = 2.0                # desmonte C1 en el lado ALTO (63 grados; 1.15 en el resto)
TIERRA_PARED_PEND = 0.85             # ladera minima en el lado alto (40 grados) desde 4.5 m del borde...
TIERRA_PARED_H = 14.0                # ... hasta esta altura sobre la rasante (pared tambien donde el natural no llega)
# F1 r2: el lomo es una LOMA REDONDEADA, no una tienda (director r1, postal 56: 'piramide facetada'): subida 1-(1-u)^2.5 en
# TIERRA_LOMO_SUBIDA m desde 4.5 m del borde (arranque 2.5h/L = 1.75 bajo el techo de 2.0, cresta con pendiente 0), cresta de
# TIERRA_LOMO_CRESTA m y bajada al 50 % con acuerdo parabolico de TIERRA_LOMO_T m; la cresta serpentea (ruido de 50 m en la
# distancia, +-TIERRA_LOMO_SERP m) y la altura varia entre 0.9 y 1.2 (ruido de 30 m, antes 0.8-1.2: con 0.8 la pared se quedaba
# en 7-8 m y el KPI de 25 m fallaba por el ruido)
TIERRA_LOMO_SUBIDA = 20.0            # m del pie (4.5 m del borde) a la cresta: la cresta esta a 24.5 m (el KPI se mide a 25 m)
TIERRA_LOMO_CRESTA = 18.0            # m de cresta (redondeada) antes de bajar al natural
TIERRA_LOMO_T = 12.0                 # acuerdo parabolico de la bajada (m)
TIERRA_LOMO_SERP = 4.0               # +- m de serpenteo de la cresta (ruido de 50 m)
# F1 r2: LOMO MINIMO. Donde el natural sube >= 3 m a 60-80 m (hay ladera que acercar) el lomo mide al menos TIERRA_PARED_H_MIN
# (fundido 3-6 m de subida natural): la meseta del interior del lazo (s 1880-1960) y la salida de la C26 daban paredes de 3-7 m,
# no de 8. NO en las islas de horquilla (interior de curvas R < 25) ni a < TIERRA_SIN_MIN_APEX m del apex de una horquilla
# (R < 15: C18-19 y C26): la isla de la cima es lo que ve la postal 56 (frozen) y no debe crecer mas
TIERRA_PARED_H_MIN = 0.0             # DESACTIVADO (0): probado con 10 m (10 x 0.9 de ruido - 0.5 = 8.5 m > 8 a 25 m): 131 celdas levantadas
                                     # 1.2 m de media (s 2000-2200) por solo +0.2 % de PyC: donde faltaba pared manda el techo de la rama
                                     # de al lado (isla B-C de la cima: natural +14, techo de la rama baja +5), no la altura del lomo
TIERRA_SIN_MIN_APEX = 50.0
# F1 r3 (director r2, problema 2): CAIDA LIBRE por muestra. La vaguada de una muestra solo se excava si su punto de medida
# (25 m del borde, lado bajo) NO esta en la ZONA DE PARED de otra rama (celdas a < TIERRA_CAIDA_LIBRE_D del borde de una
# muestra que tiene ese punto en su lado ALTO y cuya pared es real: natural >= z + TIERRA_PARED_REAL o lomo natural >= 7.5)
# ni a < TIERRA_CAIDA_LIBRE_ASF del asfalto de otra rama. Antes la vaguada de la horquilla de la cima (B, s 1770-1860, lado
# bajo = isla) abria una ZANJA de 13-14 m en la isla natural (+13..+15) que es la pared de la rama C (s 1880-1960, lado alto):
# C se quedaba sin pared a 25 m (0 % de PyC en 1830-1960) y B no ganaba caida (su punto de 25 m sigue sobre el lomo de C);
# la zanja era ademas la 'piramide facetada de dos picos' de la postal 56. Con el lado bajo bloqueado ese lado es un CORTE
# (ambas caras de la isla a TIERRA_PEND_INT), no un relleno.
TIERRA_CAIDA_LIBRE_D = 27.0          # zona de pared de otra rama: hasta 27 m de su borde (el KPI se mide a 25 m + 2 de margen)
TIERRA_CAIDA_LIBRE_ASF = 12.0        # ... o asfalto de otra rama a < 12 m del punto de medida: no hay sitio para una vaguada
TIERRA_PARED_REAL = 7.0              # pared 'real' de la otra rama: natural >= z + 7 m en el punto (o lomo natural >= 7.5)
TIERRA_BLOQ_APEX = 30.0              # a < 30 m (por la pista) de un apex de horquilla el lado bajo bloqueado conserva el cono de 1.15
                                     # (la isla de la cima que mira la postal 56 no crece: horizonte de terreno en la fila 25, no 18)
TIERRA_LOMO_H_NAT = (3.0, 5.0)       # lomo solo donde el natural sube >= 3 m a 60-80 m (pleno a 5). r3: probado (6, 8): -5 puntos de PyC
                                     # a 50 m (s 2320-2350) y sin ganancia a 25 m; se queda como en r2
# F1 r3: ZONA DE PARED y COLA del lomo. El lomo manda (apaga la vaguada de cualquier otra rama) solo en su zona de pared
# (dedge <= TIERRA_LOMO_CORE: subida + cresta); su COLA (meseta final y bajada, hasta 70 m del borde) ya no apaga vaguadas y,
# donde una rama de enfrente excava su vaguada, se recorta al techo de esa vaguada con un fundido de TIERRA_LOMO_COLA_T m
# (pendiente <= ~0.7). Antes la cola del lomo de 14 m de la rama baja (meseta a la cota de la rama alta) dejaba a la rama
# alta un hombro llano a 25 m en vez de la caida (s 1600-1690 contra 2150-2220 y el collado de s 1588): 'gana el lomo' sigue
# valiendo dentro de la zona de pared (ramas a < 57 m), y a >= 60 m la rama alta recupera su caida (zanja entre el lomo y ella)
TIERRA_LOMO_CORE = 32.0
TIERRA_LOMO_COLA_T = 1e9             # recorte de la cola al techo de la vaguada de enfrente: DESACTIVADO (1e9). Probado con 15 m (v35):
                                     # PyC 34.6 % pero zanja en V de 10-16 m entre el lomo de la rama baja y la rama alta (s 1610-1620 /
                                     # 2140-2180) y hoyo cerrado en el collado: 'formas suaves' manda; se deja el mecanismo por si F2 lo usa
TIERRA_LOMO_GAP = 60.0               # hueco entre ramas (dedge + distancia a la otra rama) por debajo del cual el lomo manda entero
TIERRA_BERMA = 7.5                   # berma llana en el lado BAJO (arcen + pacas + cierre invisible a w/2+6.75)
TIERRA_SFL_EXT = 1.3                 # terraplen maximo en el lado bajo (antes 0.55)
TIERRA_CAIDA_PEND = 0.60             # caida minima tras la berma (techo; r2: 0.55 -> 0.60 y ruido 0.9-1.2: 0.6 x 17.5 x 0.9 = -9.4 m a 25 m,
                                     # antes 0.55 x 17.5 x 0.8 = -7.7: en s 1670/1690/2000 la caida se quedaba en -6.4..-7.6 por el ruido)...
TIERRA_CAIDA_H = 16.0                # ... hasta esta profundidad bajo la rasante (fondo redondeado: minimo suave de TIERRA_CAIDA_K m)
TIERRA_CAIDA_T = 2.0                 # acuerdo parabolico del arranque de la caida tras la berma (m; con 6 la caida a 25 m se quedaba en
                                     # -8.7 x ruido y PyC perdia 1 punto)
TIERRA_CAIDA_K = 2.0                 # suavidad (m) del fondo de la vaguada
TIERRA_SIN_CORREDOR = (4.5, 8.0)     # lomo y vaguada a 0 hasta 4.5 m del borde (fundido a 8): el corredor (z0-0.5 .. z0-0.6) no cambia ni 1 cm
TIERRA_MCL_MARGEN = (30.0, 15.0)     # F1 r2: lo nuevo de F1 (bancales en el espolon, costillas de 4 m) a 0 hasta +30 m de la huella del
                                     # McLaren (fundido 15): la EDT de la huella y la de medir_relieve difieren 2-4 m (r1: 0.68 m a 22.6 m)
TIERRA_BANCO_DZ = 4.0                # banco de horquilla: si la OTRA rama esta >= 4 m mas alta, la isla sube de la rama baja a la alta
TIERRA_LOMO_EXTRA = 0.0              # m que la cresta del corte puede sobresalir del natural a 60-80 m donde hay ladera ('labio'; probado
                                     # con 3.0: pared en algun lado 39 -> 44 % pero el lomo apaga la vaguada vecina (PyC 21.7 -> 20.9) y
                                     # abre un foso de 1.68 m tras pueblo_alto_ladera: se deja a 0)
TIERRA_LADO_SONDA = 60.0             # distancias (m, y +20) a las que se compara el natural de ambos lados para elegir el lado alto
TIERRA_OTRA_RAMA = (10.0, 25.0)      # lomo y vaguada se apagan a < 10 m del borde de OTRA rama (1 a 25 m; otra rama = muestra
                                     # a > 100 m por la pista): islas de horquilla y espina entre ramas paralelas
TIERRA_OTRA_RAMA_DS = 100.0          # (m por la pista) a partir de los que una muestra cuenta como OTRA rama para ese apagado
TIERRA_LON_M = 16.0                  # una muestra solo talla las celdas que tiene en su normal (desfase |lon| < 16 m, fundido 8 m)

# FASE VISUAL F1 (bloque 1.2): berma + bancales + costillas tras la ultima terraza (sectores pueblo_*)
BERMA_TERRAZA = (15.0, 25.0)         # berma (ruido de 60 m) entre el patio de la ultima terraza y el arranque de la cara
BERMA_TERRAZA_PEND = 0.25            # la berma sube suave (14 grados, pradera/olivar): ni mesa de agua ni otra terraza llana
BERMA_ACUERDO_T = 3.0                # F1 r2: acuerdo parabolico (m) entre la berma y la cara (antes quiebro seco 0.25 -> 1.15-2.2: los
                                     # olivos/pinos del integrador en ese quiebro salian 'enterrados > 0.6' al asentarlos). Con 10 m la cara
                                     # retrocedia 5 m (terreno a 120 m -3 m) y el escalon a la rama vecina abria 2.1 m de agua atrapada en s 950
BERMA_CARA_FACTOR = 1.8              # F1 r2: la cara tras la berma es x1.8 mas empinada (1.15 -> 2.07, 64 grados; en el espolon del coche
                                     # sigue a 2.0) para que el terreno a 120 m tras pueblo_subida_ladera no quede por debajo de la base
                                     # (83.0 m; con berma y 1.15 bajaba a 78.1; medido con acuerdo 3 m: x1.5 82.6, x1.75 82.9, x1.8 83.0; con x1.75 y acuerdo 2 m un
                                     # foso de 1.52 m en s 960): los bancales
                                     # (repisa 0.1x / cara 1.9x), la berma de 15-25 m y las costillas de 4 m la leen como monte con pie, no como tajo
BANCOS_EN_COCHE = True               # bancales tambien en el espolon del coche (w_coche): probado el 04/10 (v22), checks['coche_120m_*']
                                     # no bajan (min 27 / max 110 / >= 90 m en 17 %, fuera de terrazas 57 %) y los fosos no cambian
COSTILLA_TOPE = (2.0, 4.0)           # costillas de erosion: 2 m en caras someras, 4 m en caras > 20 m (> 0.8 de pendiente)

# FASE VISUAL F1 r4 (acotacion 1 del coordinador; director r3 n.º 2): CUPULA de la ISLA DE LA CIMA (postal 56). La isla es el
# interior de la horquilla C18-19 (eje de la pista s_apex +- CUPULA_DS, cerrado; apex = cota maxima del tramo de tierra, s 1864).
# En r3 era el natural (129 m) cortado por los conos rectos del desmonte (W 1.7-1.8 = 60 grados, E 1.0-1.3): 'cono de arista
# recta' visto de frente desde la camara 56 (que esta EN el apex mirando al S por el eje de la isla) + roca por cara con dientes.
# r4: la isla es un TECHO propio que se IMPONE (rellena y rebaja: el corte r3 de 52-60 grados al pie de la rama baja desaparece;
# el corredor < 4.5 m del asfalto no cambia, fundido 4.5-6 m), hecho con dos familias de perfiles por muestra (solo las que tienen
# la celda en su normal, |lon| < CUPULA_LON_M), minimo por familia y SMOOTH-MIN entre familias (cresta redondeada de radio
# ~CUPULA_K_CRESTA, nunca arista), + suavizado CUPULA_SUAVE_M:
#  - rama BAJA (la que SUBE a la cima, s < apex; 2.4-4.7 m por debajo de la otra en cada seccion): flanco a CUPULA_PEND_B
#    (49 grados) con acuerdo parabolico de CUPULA_T_B m al pie. Mira al OESTE: desde la camara 56 (x 48) es cara trasera (solo se ve
#    su cresta). ES LA PARED del KPI de las filas de la rama alta s 1926-1976: a 25 m del borde de la rama alta (x 41-43, 15-16 m mas
#    alla del corredor de la baja) hace falta z >= Z_alta + 8 = Z_baja + 12.1..13.2 (media >= 37 grados desde el corredor): con <= 30
#    grados en ese flanco se pierden 6-9 filas (PyC 31 -> 25 %, exp_cupula.py; ver PARCHES_F1_terreno.md r4).
#  - rama ALTA (s > apex): CUPULA convexa h (1 - (1 - u)^CUPULA_P_C), u = q / CUPULA_L_C: pendiente p h / L al pie (1.5 x 12.5 / 33
#    = 0.57 = 29.6 grados) que baja a 0 en la cumbre; es la cara que ve la camara 56 (r4b: todas sus caras a < 20 m de la cumbre
#    <= 30 grados; con p = 2 y L 27 el pie iba a 38-40 grados y era lo unico que pasaba de 30 en lo que ve 56).
#  - NARIZ (s de la rama alta < CUPULA_S_NARIZ, los 30-50 m de isla delante de la camara 56): techo absoluto Z_apex + CUPULA_NARIZ_DZ
#    (smooth-min) que sube CUPULA_NARIZ_PEND por metro de s hacia el sur: la cima queda POR DEBAJO del ojo de la camara (121.9) y
#    no hay silueta de cono contra el cielo; ahi el KPI no se juega (filas de pared a ambos lados o ya sin pared en r3).
#  - en los ultimos CUPULA_FUNDIDO_S m de cada media rama el techo se funde con el terreno de fuera (en r4-v46 el cierre recto del
#    poligono dejaba un escalon de 4-5 m en y 460-470).
#  - la CUPULA NO lleva roca (mascara_roca, capas.roca), ni 'tierra' de corte en las capas, ni costillas: sin frontera de material
#    sobre el flanco no hay fila de dientes por cara (color_ac.roca_caras: nz < 0.50 o atributo > 0.49 por cara de 4 m). r4b: salvo
#    el flanco oculto de la rama baja hasta CUPULA_ROCA_B_S (roca al fondo de la recta de 51) y la loma sur (CUPULA_SUR_T), que es r3.
CUPULA_DS = 150.0                    # medias ramas de la horquilla que forman la isla (m por la pista a cada lado del apex; los 30 ultimos son fundido)
CUPULA_FUNDIDO_S = 30.0              # fundido del techo con el terreno de fuera en el extremo sur de la isla (m de s)
CUPULA_LON_M = 6.0                   # una muestra solo acota las celdas de su normal (|lon| < 6 m: con 24 m las muestras de 24 m
                                     # atras, 3.4 m mas bajas en una rampa del 14 %, acotaban la cresta 3 m por debajo)
CUPULA_PEND_B = 1.15                 # flanco de la rama baja (pared del KPI, cara trasera desde 56): 49 grados
CUPULA_T_B = 2.0                     # acuerdo parabolico (m) del pie del flanco de la rama baja
CUPULA_BASE_B = 0.5                  # m sobre z-0.5 en que arranca el flanco de la rama baja (= cota del corredor a 4.5 m)
CUPULA_H_C = 12.5                    # altura de la cupula convexa sobre la rama alta (m)
CUPULA_L_C = 33.0                    # anchura de la cupula (m desde 4.5 m del borde de la rama alta hasta su cumbre)
CUPULA_P_C = 1.5                     # exponente del perfil (pendiente al pie p H/L = 0.57, 0 en la cumbre; 2 = parabola)
CUPULA_K_CRESTA = 0.6                # smooth-min (m) entre familias y con el techo de la nariz: cresta redondeada
CUPULA_NARIZ_DZ = 0.3                # techo de la nariz = Z_apex + 0.3 m ...
CUPULA_S_NARIZ = 1909.0              # ... hasta s 1909 de la rama alta (por la isla) y despues sube CUPULA_NARIZ_PEND por m de s
CUPULA_NARIZ_PEND = 0.15
CUPULA_RUIDO = (0.03, 0.06)          # +- ruido (50 m) en la pendiente del flanco B y en la altura/anchura de la cupula C
CUPULA_SUAVE_M = 1.5                 # sigma (m) del suavizado final del techo
CUPULA_D_MIN = (4.5, 6.0)            # el techo se impone a > 6 m del borde del asfalto (fundido desde 4.5): el corredor no cambia
# r4b (05/10): la LOMA SUR de la isla (s de la rama baja <= ~1760, la alta >= ~1960) lleva la pared derecha de roca de la toma de PILOTO 51
# (la mejora mas grande de F1 segun el director r3) y la que ve la 07; desde 56 es cara trasera (el flanco de la rama baja mira al O y la
# camara esta al E de la cresta; el de la rama alta, a > 40 grados, tampoco se ve). En r4-v48 la cupula llegaba hasta ahi: el flanco de 43
# grados sin roca bajaba la pared 3-8 m y la dejaba en hierba (vista sintetica de 51: pared de roca -> ladera dorada). Ahora la cupula
# (familias B y C + nariz) manda a < CUPULA_SUR_T[0] m del apex por la isla y el terreno de r3 a > CUPULA_SUR_T[1] (transicion smoothstep);
# la loma sur la acota la LINEA DE VISTA del ojo de 56 (apex + CUPULA_VIS_DZ, CUPULA_VIS_GRADOS sobre la horizontal).
CUPULA_SUR_T = (70.0, 95.0)          # m por la isla desde el apex: cupula hasta, terreno de r3 desde
CUPULA_VIS_DZ = 1.2                  # ojo de la camara 56 sobre la rasante del apex (121.9 - 120.7)
CUPULA_VIS_GRADOS = 0.0              # angulo maximo de la cresta de la loma sur desde el ojo (queda a -0.2..-0.6; la cumbre de la cupula a +0.4..+0.5)
CUPULA_K_VIS = 1.0                   # smooth-min (m) del recorte de la loma sur por la linea de vista
CUPULA_LADO_M = 16.0                 # transicion (m) entre el lado de la rama baja y el de la alta alrededor de la linea media de la isla
CUPULA_ROCA_B_S = (1815.0, 1830.0)   # el flanco de la rama baja de la cupula conserva la roca hasta s 1815 (fundido hasta 1830)


# FASE VISUAL F1 (bloque 2.2): ROCA POR PENDIENTE. UN SOLO SITIO de verdad para los umbrales: mascara_terreno.UMBRALES
# (propietario 'mascara', PARCHES_F1_mascara.md A2); de ahi salen estas constantes, que a su vez exportan umbrales_roca() y
# ROCA_UMBRAL_NZ para color_ac (P1) y los revisores. Si mascara_terreno no se puede importar (p. ej. una copia suelta del
# modulo) valen los defectos de abajo, que son los mismos numeros.
try:
    from mascara_terreno import UMBRALES as _UMB_MASCARA    # importable sin scipy; lee paleta.json (python del sistema)
except Exception:                                           # noqa: BLE001
    _UMB_MASCARA = None


def _umb(clave, defecto):
    return defecto if (_UMB_MASCARA is None or clave not in _UMB_MASCARA) else _UMB_MASCARA[clave]


_P_ROCA = tuple(_umb('PEND_ROCA', (0.70, 0.84)))
ROCA_UMBRAL_PEND = round(0.5 * (_P_ROCA[0] + _P_ROCA[1]), 3)   # 0.77: pendiente (tan) suavizada a partir de la que una ladera natural es roca
ROCA_UMBRAL_RUIDO = round(0.5 * (_P_ROCA[1] - _P_ROCA[0]), 3)  # +-0.07 con ruido de 30 m: 0.70-0.84 (35-40 grados, plan 2.2)
ROCA_UMBRAL_NZ = round(1.0 / math.sqrt(1.0 + ROCA_UMBRAL_PEND ** 2), 3)   # el mismo umbral como nz de la cara (0.792)
# F1 r4 (acotacion 4 del coordinador; propietario 'mascara'): umbral nz de la roca POR CARA (proxy AC / writer) en la cima de 56 y
# en las laderas a < 150 m de las tomas 51/07 (0.62 en vez de 0.82: sin dientes aislados) y ruido del atributo roca 0.08 -> 0.20.
# VIVEN en mascara_terreno.UMBRALES (ROCA_NZ_ZONA, ROCA_NZ_ZONAS, ROCA_ATR_RUIDO; los aplica construir_pista.roca_zonas_nz): aqui
# solo se LEEN y se exportan en umbrales_roca() -> geometria_3d.json extras.umbrales_roca para los revisores y color_ac (P1).
ROCA_NZ_ZONA = float(_umb('ROCA_NZ_ZONA', 0.62))
ROCA_ATR_RUIDO = float(_umb('ROCA_ATR_RUIDO', 0.20))
ROCA_NZ_ZONAS = {k: tuple(v) for k, v in dict(_umb('ROCA_NZ_ZONAS', {'56_postal_cima_bahia': (47.972, 567.543, 150.0),
                                                                     '51_piloto_s1700': (15.023, 426.256, 150.0),
                                                                     '07_tierra_subida': (-12.016, 294.887, 150.0)})).items()}
ROCA_SIGMA_M = float(_umb('PEND_SUAVIZADO_M', 10.0))   # suavizado de la pendiente (m; /cell = celdas) antes del umbral (anti 'camuflaje' v3 N1)
ROCA_MIN_CELDAS = int(_umb('ROCA_MIN_CELDAS', 12))     # manchas naturales mas pequenas se quitan (apertura 3x3 + tamano minimo)
ROCA_PIE_M = tuple(_umb('PIE_M', (6.0, 10.0)))         # pie de derrubios: banda de 6-10 m ladera ABAJO de cada afloramiento...
ROCA_PIE_VALOR = 0.5                 # ... con este valor en mascara_roca (plan 2.2; 'tierra' en las capas)
ROCA_CORTE_PEND = 0.75               # umbral (+- ruido) de la pendiente en los cortes (_corte), como v2

# FASE VISUAL F1 (bloque 1.6): CAPAS de la mascara por texel (R matorral, G hierba seca, B tierra, A roca); mismos umbrales
CAPAS_LLANO_PEND = float(_umb('LLANO_PEND', 0.35))       # hierba seca en llanos (pendiente < 0.35)...
CAPAS_HIERBA_D_PISTA = float(_umb('LLANO_DIST_M', 60.0))  # ... a < 60 m de la pista...
CAPAS_HIERBA_Z = float(_umb('LLANO_Z', 60.0))            # ... y z < 60 m (y en las terrazas del pueblo y la vega baja)
CAPAS_DIRT_BORDE_M = float(_umb('DIRT_BORDE_M', 8.0))    # 'tierra' a < 8 m del borde del asfalto en el tramo de tierra
CAPAS_MATORRAL_Z = 150.0             # por encima no hay hierba seca (matorral y roca)
CAPAS_RUIDO_M = 20.0                 # ruido de los bordes entre capas (m)
# F1 r4 (probado y APAGADO en r4b): el pie de derrubios (mascara_roca 0.5) fuera del canal A ('tierra' en las capas). Con True:
# banda de tierra de 6-10 m al pie de cada roca en modo normal (51, 07: pie de la pared en marron), roca en la tierra 27.5 -> 24.6 %,
# tierra 5.2 -> 8.1 %, y en AC NO quita dientes (rejilla 4 m tras las zonas de 'mascara': 1265 -> 1314, +4 %; caras de roca 46 235 ->
# 44 911). Sin beneficio medido y con cambio visible en una toma de piloto: False = el pie como en r1-r3 (0.5 en capas.roca)
CAPAS_PIE_FUERA_DE_A = False


def umbrales_roca():
    """F1 (bloque 2.2): umbrales compartidos con mascara_terreno.py (propietario 'mascara') y color_ac (P1): un solo sitio."""
    return dict(pend=ROCA_UMBRAL_PEND, ruido=ROCA_UMBRAL_RUIDO, pend_rango=list(_P_ROCA), nz=ROCA_UMBRAL_NZ, sigma_m=ROCA_SIGMA_M,
                min_celdas=ROCA_MIN_CELDAS, pie_m=list(ROCA_PIE_M), pie_valor=ROCA_PIE_VALOR, corte_pend=ROCA_CORTE_PEND,
                # F1 r4 (acotacion 4): umbral nz por cara en la cima de 56 / laderas de 51 y 07 y ruido del atributo (de mascara_terreno)
                nz_zona=ROCA_NZ_ZONA, nz_zonas={k: list(v) for k, v in ROCA_NZ_ZONAS.items()}, atr_ruido=ROCA_ATR_RUIDO,
                origen='mascara_terreno.UMBRALES' if _UMB_MASCARA is not None else 'defectos de terreno_montana',
                capas=dict(llano_pend=CAPAS_LLANO_PEND, hierba_d_pista=CAPAS_HIERBA_D_PISTA, hierba_z=CAPAS_HIERBA_Z,
                           matorral_z=CAPAS_MATORRAL_Z, ruido_m=CAPAS_RUIDO_M, dirt_borde_m=CAPAS_DIRT_BORDE_M))

# valles de drenaje: polilineas (x, y) de arriba a abajo; anchura base y
# profundidad relativa (fraccion de la cota local, acotada: prof x min(M, 80))
VALLES = [
    dict(nombre='valle norte (vega al O)', w=65.0, prof=0.34,
         pts=[(-240, 820), (-300, 700), (-420, 640), (-620, 600), (-900, 560)]),
    dict(nombre='barranco del pueblo alto', w=45.0, prof=0.30,
         pts=[(-70, 690), (-110, 580), (-130, 470), (-100, 390), (-70, 335)]),
    dict(nombre='barranco E del lazo', w=42.0, prof=0.26,
         pts=[(60, 690), (110, 560), (125, 470), (150, 380), (120, 280), (90, 200)]),
    dict(nombre='valle este (al puerto)', w=60.0, prof=0.32,
         pts=[(330, 620), (310, 470), (260, 330), (220, 200), (180, 120), (80, 110), (-60, 60)]),
    dict(nombre='barranco norte 1', w=50.0, prof=0.30,
         pts=[(70, 880), (120, 1000), (150, 1190)]),
    dict(nombre='barranco norte 2', w=50.0, prof=0.30,
         pts=[(-200, 900), (-230, 1050), (-250, 1190)]),
    dict(nombre='barranco NE', w=50.0, prof=0.28,
         pts=[(400, 720), (470, 850), (520, 1000), (560, 1190)]),
    dict(nombre='barranco NO', w=50.0, prof=0.28,
         pts=[(-380, 960), (-460, 1060), (-520, 1190)]),
    dict(nombre='barranco del promontorio (al E)', w=45.0, prof=0.22,
         pts=[(640, -350), (720, -330), (820, -320)]),
]


# ---------------------------------------------------------------------------
# utilidades de campo
# ---------------------------------------------------------------------------
def _zoom_a(g, ny, nx):
    """zoom de una rejilla gruesa a exactamente (ny, nx) (orden 3, recortado/relleno)."""
    up = _zoom(g, (ny / float(g.shape[0]), nx / float(g.shape[1])), order=3)
    out = np.zeros((ny, nx))
    h = min(ny, up.shape[0]); w = min(nx, up.shape[1])
    out[:h, :w] = up[:h, :w]
    if h < ny:
        out[h:, :] = out[h - 1:h, :]
    if w < nx:
        out[:, w:] = out[:, w - 1:w]
    return out


def ruido_valor(rng, ny, nx, cell, lam):
    """ruido de valor suave en [-1, 1] con longitud de onda ~lam (m)."""
    ncx = max(4, int(round(nx * cell / lam)) + 2)
    ncy = max(4, int(round(ny * cell / lam)) + 2)
    return _zoom_a(rng.uniform(-1.0, 1.0, (ncy, ncx)), ny, nx)


def ruido_ridged(rng, ny, nx, cell, octavas=((340.0, 1.0), (170.0, 0.5), (85.0, 0.25), (42.0, 0.12))):
    """ruido 'ridged' (crestas) multi-octava, ~0..1."""
    H = np.zeros((ny, nx))
    for lam, amp in octavas:
        H += amp * (1.0 - np.abs(ruido_valor(rng, ny, nx, cell, lam)))
    H = H / sum(a for _, a in octavas)
    return np.clip(H, 0.0, 1.0) ** 1.7


def dist_polilinea(px, py, pts):
    """distancia de cada punto (px,py) a la polilinea pts y parametro t (0..1) global
    + valor interpolado del tercer campo si pts lo tiene. Devuelve (d, t, h)."""
    P = np.array([(p[0], p[1]) for p in pts], dtype=float)
    H = np.array([p[2] if len(p) > 2 else 0.0 for p in pts], dtype=float)
    seg = np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1]))
    sacc = np.concatenate([[0.0], np.cumsum(seg)])
    best_d = np.full(px.shape, np.inf)
    best_t = np.zeros(px.shape)
    best_h = np.zeros(px.shape)
    for k in range(len(P) - 1):
        ax, ay = P[k]; bx, by = P[k + 1]
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy
        if l2 < 1e-9:
            continue
        u = np.clip(((px - ax) * vx + (py - ay) * vy) / l2, 0.0, 1.0)
        d = np.hypot(px - (ax + u * vx), py - (ay + u * vy))
        m = d < best_d
        best_d = np.where(m, d, best_d)
        best_t = np.where(m, (sacc[k] + u * seg[k]) / max(sacc[-1], 1e-9), best_t)
        best_h = np.where(m, H[k] + (H[k + 1] - H[k]) * u, best_h)
    return best_d, best_t, best_h


def smax(campos, k=0.1):
    """soft-max de una lista de campos (fusion suave de landforms)."""
    A = np.stack(campos, 0)
    m = A.max(0)
    return m + np.log(np.exp(k * (A - m)).sum(0)) / k


def limitar_pendiente(M, cell, smax_=PEND_NATURAL_MAX, max_iter=400):
    """REBAJA (nunca sube) las celdas hasta que ninguna pendiente entre vecinas
    8-conexas supere smax_: z_i <= z_j + smax_*d_ij (erosion morfologica con un
    cono; converge en unas decenas de iteraciones). Devuelve (M', iteraciones,
    rebaje maximo)."""
    d4 = smax_ * cell
    d8 = smax_ * cell * math.sqrt(2.0)
    Mc = np.asarray(M, float).copy()
    it = 0
    for it in range(1, max_iter + 1):
        Mn = Mc.copy()
        Mn[1:, :] = np.minimum(Mn[1:, :], Mc[:-1, :] + d4)
        Mn[:-1, :] = np.minimum(Mn[:-1, :], Mc[1:, :] + d4)
        Mn[:, 1:] = np.minimum(Mn[:, 1:], Mc[:, :-1] + d4)
        Mn[:, :-1] = np.minimum(Mn[:, :-1], Mc[:, 1:] + d4)
        Mn[1:, 1:] = np.minimum(Mn[1:, 1:], Mc[:-1, :-1] + d8)
        Mn[1:, :-1] = np.minimum(Mn[1:, :-1], Mc[:-1, 1:] + d8)
        Mn[:-1, 1:] = np.minimum(Mn[:-1, 1:], Mc[1:, :-1] + d8)
        Mn[:-1, :-1] = np.minimum(Mn[:-1, :-1], Mc[1:, 1:] + d8)
        delta = float(np.abs(Mn - Mc).max())
        Mc = Mn
        if delta < 0.01:
            break
    return Mc, it, float((np.asarray(M) - Mc).max())


def limitar_pendiente_mascara(Z2, cell, smax_, mov, max_iter=200):
    """v3 (revision B10): como limitar_pendiente pero SOLO rebaja las celdas de 'mov' (bool, misma forma); las demas son fijas
    (hacen de apoyo). Devuelve (Z', rebaje maximo)."""
    d4 = smax_ * cell; d8 = smax_ * cell * math.sqrt(2.0)
    Zc = np.asarray(Z2, float).copy(); Z0 = Zc.copy()
    for _ in range(max_iter):
        Zn = Zc.copy()
        Zn[1:, :] = np.minimum(Zn[1:, :], Zc[:-1, :] + d4); Zn[:-1, :] = np.minimum(Zn[:-1, :], Zc[1:, :] + d4)
        Zn[:, 1:] = np.minimum(Zn[:, 1:], Zc[:, :-1] + d4); Zn[:, :-1] = np.minimum(Zn[:, :-1], Zc[:, 1:] + d4)
        Zn[1:, 1:] = np.minimum(Zn[1:, 1:], Zc[:-1, :-1] + d8); Zn[1:, :-1] = np.minimum(Zn[1:, :-1], Zc[:-1, 1:] + d8)
        Zn[:-1, 1:] = np.minimum(Zn[:-1, 1:], Zc[1:, :-1] + d8); Zn[:-1, :-1] = np.minimum(Zn[:-1, :-1], Zc[1:, 1:] + d8)
        Zn = np.where(mov, Zn, Zc)
        if float(np.abs(Zn - Zc).max()) < 0.01:
            Zc = Zn
            break
        Zc = Zn
    return Zc, float((Z0 - Zc).max())


def en_poligono(px, py, P):
    """v3: punto en poligono (par/impar, numpy; sin shapely: este modulo tambien lo importan herramientas sin el)."""
    px = np.asarray(px, float); py = np.asarray(py, float); P = np.asarray(P, float)
    dentro = np.zeros(px.shape, bool)
    xj, yj = P[-1]
    for xi, yi in P:
        cruza = ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / ((yj - yi) if yj != yi else 1e-12) + xi)
        dentro ^= cruza
        xj, yj = xi, yi
    return dentro


def peso_fuera_zonas(gpts, nxg, nyg, cell, spec_urb, margen=25.0, fundido=15.0):
    """v3: 0 dentro de las zonas_excluidas del spec (huella del McLaren) y a < margen m de ellas, 1 a margen + fundido m:
    los cambios v3 de costa, crestas y bancales no tocan el terreno sobre el que se apoya el McLaren."""
    w = np.ones(len(gpts))
    for z_ in spec_urb.get('zonas_excluidas', []) if spec_urb else []:
        P = z_.get('poligono', [])
        if len(P) < 3:
            continue
        d_ = en_poligono(gpts[:, 0], gpts[:, 1], P).reshape(nyg, nxg)
        dist = distance_transform_edt(~d_) * cell
        w = np.minimum(w, np.clip((dist.ravel() - margen) / fundido, 0.0, 1.0))
    return w


def union_discos(nxg, nyg, gx0, gy0, cell, cx, cy, r):
    """union EXACTA de discos (cx, cy, r) rasterizada en la rejilla -> bool (ny*nx)."""
    prot = np.zeros((nyg, nxg), bool)
    for x, y, rr in zip(cx, cy, r):
        rc = int(rr / cell) + 1
        ic = int(round((x - gx0) / cell)); jc = int(round((y - gy0) / cell))
        i0, i1 = max(0, ic - rc), min(nxg, ic + rc + 1)
        j0, j1 = max(0, jc - rc), min(nyg, jc + rc + 1)
        if i1 <= i0 or j1 <= j0:
            continue
        xx = gx0 + np.arange(i0, i1) * cell - x
        yy = gy0 + np.arange(j0, j1) * cell - y
        prot[j0:j1, i0:i1] |= (xx[None, :] ** 2 + yy[:, None] ** 2) <= rr * rr
    return prot.ravel()


# ---------------------------------------------------------------------------
# macizo base
# ---------------------------------------------------------------------------
def macizo_base(GX, GY, cell, seed=15, fac_valle=None, landforms=None):
    """campo de alturas natural M (sin pista): landforms + ruido + valles.
    fac_valle (ny x nx, 0..1): factor de la profundidad de los valles por celda (RONDA
    15c: 0 en las bandas de terrazas de los sectores + 25 m y fundido a 1 en 60 m mas; antes
    el 'barranco del pueblo alto' y el 'valle norte' pasaban a 0 m del borde exterior de
    las terrazas y dejaban un foso de 2-14 m detras de los patios)."""
    ny, nx = GX.shape
    rng = np.random.default_rng(seed)
    # modulacion de los contornos (crestas/vaguadas radiales): d' = d*(1+a*n)
    mod = (0.20 * ruido_valor(rng, ny, nx, cell, 150.0)
           + 0.11 * ruido_valor(rng, ny, nx, cell, 70.0))
    campos = [np.full((ny, nx), 1.5)]          # llanura costera
    for lf in (LANDFORMS if landforms is None else landforms):
        d, t, h = dist_polilinea(GX, GY, lf['pts'])
        dmod = d * (1.0 + mod)
        R = np.maximum(h, 1.0) / lf['s_foot']
        u = np.clip(dmod / R, 0.0, 1.0)
        campos.append(h * (1.0 - u) ** lf['p'])
    M = smax(campos, k=0.12)
    # ruido ridged: mas amplitud cuanto mas alto (crestas naturales), ~0 en la costa
    rid = ruido_ridged(rng, ny, nx, cell)
    amp = 4.0 + 24.0 * np.clip(M / 200.0, 0.0, 1.0)
    M = M + amp * (rid - 0.4)
    # valles de drenaje: canal gaussiano; profundidad = prof x min(M, 80) (antes
    # prof x M: gargantas de 50 m con paredes > 100 %)
    fv = np.ones((ny, nx)) if fac_valle is None else np.asarray(fac_valle, float).reshape(ny, nx)
    for v in VALLES:
        d, t, _ = dist_polilinea(GX, GY, v['pts'])
        w = v['w'] * (1.0 + 0.8 * t)
        M = M - fv * v['prof'] * np.clip(M, 0.0, 80.0) * np.exp(-(d / w) ** 2)
    return np.maximum(M, 1.2)


def curvas_en_metros(curvas, X, Y):
    """RONDA 15c: preparar_geometria.py pasa data['curvas'] con x, y en unidades del SVG
    (trazado_v1.json) y la copia de geometria_3d.json las trae en METROS: la elipse del penon
    salia 1.2 km al NE del casino en el pipeline (bahia de mar en el Monte Porto Corsa y el
    penon sin proteger). Si la mediana de la distancia de cada curva a su muestra s_idx es
    > 120 m, se convierten como preparar_geometria (x - cx) * m_u, (cy - y) * m_u con cx, cy =
    media de las muestras del trazado y m_u = m_por_unidad (leidos de 02_trazado); si ese
    fichero no esta, ajuste por minimos cuadrados contra las muestras s_idx. Devuelve una lista
    de dicts NUEVOS (no toca la entrada)."""
    cs = [dict(c) for c in curvas if 'n' in c]
    N = len(X)
    con_idx = [c for c in cs if 's_idx' in c and 0 <= int(c['s_idx']) < N]
    if not con_idx:
        return cs
    def mediana_d(lst):
        return float(np.median([math.hypot(c['x'] - X[int(c['s_idx'])], c['y'] - Y[int(c['s_idx'])]) for c in lst]))
    d0 = mediana_d(con_idx)
    if d0 <= 120.0:
        return cs
    import json, os
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '02_trazado', 'trazado_v1.json')
    conv = None
    try:
        tr = json.load(open(ruta, encoding='utf-8'))
        xs = np.array([p['x'] for p in tr['muestras']]); ys = np.array([p['y'] for p in tr['muestras']])
        cx, cy, mu = float(xs.mean()), float(ys.mean()), float(tr['m_por_unidad'])
        conv = lambda x, y: ((x - cx) * mu, (cy - y) * mu)
        modo = 'trazado_v1.json (cx %.2f cy %.2f m_u %.5f)' % (cx, cy, mu)
    except Exception:
        A = []; bx = []; by = []
        for c in con_idx:
            A.append([c['x'], 1.0]); bx.append(X[int(c['s_idx'])])
        A = np.array(A); sx = np.linalg.lstsq(A, np.array(bx), rcond=None)[0]
        Ay = np.array([[-c['y'], 1.0] for c in con_idx]); sy = np.linalg.lstsq(Ay, np.array([Y[int(c['s_idx'])] for c in con_idx]), rcond=None)[0]
        conv = lambda x, y: (sx[0] * x + sx[1], -sy[0] * y + sy[1])
        modo = 'ajuste por minimos cuadrados'
    for c in cs:
        c['x'], c['y'] = conv(float(c['x']), float(c['y']))
    print('  curvas en unidades del SVG (mediana a su muestra %.0f m): convertidas a metros con %s -> mediana %.1f m'
          % (d0, modo, mediana_d([c for c in cs if 's_idx' in c and 0 <= int(c['s_idx']) < N])))
    return cs


def elipse_casino(X, Y, curvas):
    """Centro, semiejes y giro de la elipse del penon del casino, calculados EXACTAMENTE
    como integrar_escena.zona_casino(): baricentro de las curvas 36-38 desplazado
    CASINO_DIST m en la direccion que lo aleja del centro del trazado. Devuelve
    (cx, cy, a, b, ang) o None si faltan las curvas. Las curvas deben venir en METROS
    (curvas_en_metros)."""
    cv = {int(c['n']): c for c in curvas if 'n' in c}
    if not all(n in cv for n in (36, 37, 38)):
        return None
    cxc = sum(cv[n]['x'] for n in (36, 37, 38)) / 3.0
    cyc = sum(cv[n]['y'] for n in (36, 37, 38)) / 3.0
    N = len(X)
    mx = float(np.mean(X[0:N:20])); my = float(np.mean(Y[0:N:20]))
    dx, dy = cxc - mx, cyc - my
    dl = math.hypot(dx, dy) or 1.0
    return (cxc + dx / dl * CASINO_DIST, cyc + dy / dl * CASINO_DIST, CASINO_A, CASINO_B, CASINO_ANG)


def coords_casino(px, py, el):
    """r normalizado (1 = contorno), angulo (grados) y distancia al centro de cada punto."""
    cx, cy, a, b, ang = el
    vx = px - cx; vy = py - cy
    ca, sa = math.cos(ang), math.sin(ang)
    xl = vx * ca + vy * sa; yl = -vx * sa + vy * ca
    r_n = np.hypot(xl / a, yl / b)
    return r_n, np.degrees(np.arctan2(vy, vx)), np.hypot(vx, vy)


def _idw_pull(GX, GY, M, cell, X, Y, Z, sigma=100.0, cada=8.0, paso=2.0, peso=None):
    """correccion suave C(x,y) para que M pase por la rasante de la pista:
    media ponderada (gaussiana sigma) de (Z_j - M(x_j,y_j)); se evalua en una
    rejilla gruesa (16 m) y se interpola. peso: factor por muestra (0..1)."""
    ny, nx = GX.shape
    k = max(1, int(round(cada / paso)))
    cx, cy, cz = X[::k], Y[::k], Z[::k]
    pj = np.ones(len(cx)) if peso is None else np.asarray(peso, float)[::k]
    fi = (cx - GX[0, 0]) / cell
    fj = (cy - GY[0, 0]) / cell
    mj = map_coordinates(M, [fj, fi], order=1, mode='nearest')
    dz = cz - mj
    f = 4
    gx = GX[0, ::f]; gy = GY[::f, 0]
    CX, CY = np.meshgrid(gx, gy)
    P = np.column_stack([CX.ravel(), CY.ravel()])
    C = np.zeros(len(P))
    for a in range(0, len(P), 4000):
        Q = P[a:a + 4000]
        d2 = (Q[:, 0:1] - cx[None, :]) ** 2 + (Q[:, 1:2] - cy[None, :]) ** 2
        w = np.exp(-d2 / (sigma * sigma)) * pj[None, :]
        sw = w.sum(1)
        C[a:a + 4000] = (w * dz[None, :]).sum(1) / np.maximum(sw, 1e-9) * np.clip(sw / 1.0, 0.0, 1.0)
    C = C.reshape(CY.shape)
    return _zoom_a(C, ny, nx)


def _cumbres(zg, GX, GY, cell, z_min=95.0, radio=150.0, prom=20.0):
    """maximos locales del campo final (ventana radio) con prominencia minima."""
    r = int(radio / cell)
    mx = maximum_filter(zg, size=2 * r + 1, mode='nearest')
    cand = (zg >= mx - 1e-6) & (zg > z_min)
    jj, ii = np.where(cand)
    out = []
    for j, i in zip(jj, ii):
        j0, j1 = max(0, j - r), min(zg.shape[0], j + r + 1)
        i0, i1 = max(0, i - r), min(zg.shape[1], i + r + 1)
        if zg[j, i] - zg[j0:j1, i0:i1].min() < prom:
            continue
        out.append((round(float(GX[j, i]), 1), round(float(GY[j, i]), 1), round(float(zg[j, i]), 1)))
    out.sort(key=lambda c: -c[2])
    # una cumbre por maximo (en una cima plana salen celdas vecinas repetidas)
    unicas = []
    for c in out:
        if all(math.hypot(c[0] - u[0], c[1] - u[1]) > 100.0 for u in unicas):
            unicas.append(c)
    return unicas


def _pendiente(zg, cell):
    gy, gx = np.gradient(zg, cell)
    return np.hypot(gx, gy)


def sentido_terrazas(sc):
    """+1: las terrazas SUBEN desde la pista (sector de ladera); -1: BAJAN (sector de mar).
    RONDA 15c: manda el campo 'sentido' del spec ('sube' | 'baja'); si falta, el antiguo
    'sube' (bool) y si tampoco, la regla por id ('_mar' baja, el resto sube). NO depende del
    lado. urbanismo.py lleva la MISMA regla (misma funcion)."""
    sen = str(sc.get('sentido', '')).strip().lower()
    if sen in ('sube', 'baja'):
        return 1.0 if sen == 'sube' else -1.0
    if 'sube' in sc:
        return 1.0 if sc['sube'] else -1.0
    return -1.0 if str(sc['id']).endswith('_mar') else 1.0


def extension_sector(idx_land, s_land, X, Y, s0, s1, ext, nx=None, ny=None, ratio=MISMO_RAMAL, ang_max=60.0):
    """Indices (de pista) del sector s0..s1 mas una extension de hasta `ext` m por cada
    lado que se PARA donde la pista deja de ser la continuacion del sector: la distancia
    recta a la muestra extrema cae por debajo de ratio x la distancia por la pista (se
    pliega) o la tangente ha girado mas de ang_max grados respecto a la de la muestra
    extrema (U del coche antes de pueblo_subida, codo R=11 tras pueblo_alto). Solo se usa
    para sbar (fundido); la Z se mezcla con las muestras del sector."""
    en_in = (s_land >= s0) & (s_land <= s1)
    js = list(idx_land[en_in])
    if not js:
        return np.array([], dtype=int)
    cos_max = math.cos(math.radians(ang_max))
    for extremo, sentido in ((js[0], -1), (js[-1], 1)):
        s_e = s_land[idx_land == extremo][0]
        cand = idx_land[((s_land < s0) & (s_land >= s0 - ext)) if sentido < 0 else ((s_land > s1) & (s_land <= s1 + ext))]
        cand = cand[::-1] if sentido < 0 else cand
        for j in cand:
            ds = abs(s_land[idx_land == j][0] - s_e)
            if np.hypot(X[j] - X[extremo], Y[j] - Y[extremo]) < ratio * ds:
                break
            if nx is not None and (nx[j] * nx[extremo] + ny[j] * ny[extremo]) < cos_max:
                break
            js.append(j)
    return np.array(sorted(js), dtype=int)


def mezcla_cota(qx, qy, d0, g0, o, X, Y, nx, ny, Wd, js_in, Zs_in, tree_s, lado, N, paso, AT, u_flat,
                h_mezcla=0.25, k_mezcla=96, rmax=210.0):
    """RONDA 15c: COTA BASE Zb de las terrazas de un sector en los puntos (qx, qy) (la terraza k esta a
    Zb + h_k). La usan construir() para tallar y urbanismo.py para poner calles/casas/muros: UNA sola
    cota para los dos. d0/g0/o = distancia, muestra (indice global) mas cercana del sector y offset al
    borde del asfalto. Mezcla ponderada de Zs_in (Z suavizada en s) de las muestras del sector que ven el
    punto en el lado del sector, peso exp(-((d_j - d0)/h)^2), h = max(h_mezcla * o, 1.5); entre ramas
    ENFRENTADAS (horquilla: > 50 m por la pista, distancia recta < 70 %) cada rama conserva su cota hasta
    u_flat y despues smoothstep (talud continuo). Devuelve (Zb, tt) con tt = peso de la otra rama."""
    qx = np.asarray(qx, float); qy = np.asarray(qy, float)
    oc = np.asarray(o, float)
    h = np.maximum(h_mezcla * oc, 1.5)[:, None]
    d0 = np.asarray(d0, float)[:, None]
    dk, ik = tree_s.query(np.column_stack([qx, qy]), k=k_mezcla, distance_upper_bound=rmax)
    valid = np.isfinite(dk)
    ikc = np.where(valid, ik, 0)
    gk = js_in[ikc]
    dkz = np.where(valid, dk, 0.0)
    # solo pesan las muestras que ven el punto en el lado del sector (en una S el punto es interior de
    # una rama y exterior de la siguiente: esa no debe mezclar su Z)
    mismo_lado = ((qx[:, None] - X[gk]) * nx[gk] + (qy[:, None] - Y[gk]) * ny[gk] > 0) == (lado > 0)
    ok_s = valid & mismo_lado
    g0 = np.asarray(g0, int)[:, None]
    dl = np.abs(gk - g0); dl = np.minimum(dl, N - dl) * paso
    dij = np.hypot(X[gk] - X[g0], Y[gk] - Y[g0])
    otra = ok_s & (dl > 50.0) & (dij < MISMO_RAMAL * dl)
    w = np.where(ok_s & ~otra, np.exp(-((dkz - d0) / h) ** 2), 0.0)
    z_same = (w * Zs_in[ikc]).sum(1) / np.maximum(w.sum(1), 1e-9)
    d_oth = np.where(otra, dk, 1e9).min(1)
    i_oth = np.argmin(np.where(otra, dk, 1e9), axis=1)
    o_oth = d_oth - Wd[gk[np.arange(len(qx)), i_oth]] / 2.0
    w = np.where(otra, np.exp(-((dkz - d_oth[:, None]) / h) ** 2), 0.0)
    z_oth = (w * Zs_in[ikc]).sum(1) / np.maximum(w.sum(1), 1e-9)
    tt = np.clip((oc - u_flat) / np.maximum(oc + o_oth - 2.0 * u_flat, 1e-6), 0.0, 1.0)
    tt = np.where(otra.any(1) & (o_oth < 2.0 * AT + 6.0) & (oc > u_flat), tt * tt * (3.0 - 2.0 * tt), 0.0)
    return z_same * (1.0 - tt) + z_oth * tt, tt


class CotaSector:
    """RONDA 15c: la cota base Zb de un sector (la misma de construir) para urbanismo.py. Se construye con
    las muestras de pista (arrays) y el dict del sector del spec; zb(xs, ys) devuelve (Zb, o, valido)
    (valido = punto en el lado del sector y a < rmax). Constantes = las de construir()."""
    def __init__(self, X, Y, Z, nx, ny, Wd, paso, sec, spec_urb, sec_bridge=None):
        self.X = np.asarray(X, float); self.Y = np.asarray(Y, float); Z = np.asarray(Z, float)
        self.nx = np.asarray(nx, float); self.ny = np.asarray(ny, float); self.Wd = np.asarray(Wd, float)
        self.N = len(self.X); self.paso = float(paso)
        idx = np.arange(self.N)
        if sec_bridge is not None:
            idx = idx[np.asarray(sec_bridge) != 'bridge']
        s = idx * self.paso
        self.js_in = idx[(s >= float(sec['s0'])) & (s <= float(sec['s1']))]
        self.lado = int(sec['lado'])
        self.AT = float(spec_urb.get('ancho_terraza', 21.0)); self.u_flat = float(spec_urb.get('fachada_desde', 7.0))
        self.Zs_in = gaussian_filter1d(Z[self.js_in], 7.5 / self.paso, mode='nearest')
        self.tree_s = cKDTree(np.column_stack([self.X[self.js_in], self.Y[self.js_in]]))

    def zb(self, xs, ys, rmax=210.0):
        zb, o, ok, _, _ = self.zb_info(xs, ys, rmax)
        return zb, o, ok

    def zb_info(self, xs, ys, rmax=210.0):
        """Como zb() y ademas tt (peso de la otra rama: talud entre ramas) y g (muestra mas cercana del sector)."""
        xs = np.atleast_1d(np.asarray(xs, float)); ys = np.atleast_1d(np.asarray(ys, float))
        d, k = self.tree_s.query(np.column_stack([xs, ys]), distance_upper_bound=rmax)
        ok = np.isfinite(d)
        g = self.js_in[np.where(ok, k, 0)]
        lat = (xs - self.X[g]) * self.nx[g] + (ys - self.Y[g]) * self.ny[g]
        o = np.where(ok, d, 0.0) - self.Wd[g] / 2.0
        ok &= (np.where(lat > 0, 1, -1) == self.lado)
        zb = np.full(len(xs), np.nan); tt = np.zeros(len(xs))
        for a in range(0, len(xs), 8000):
            sl = slice(a, a + 8000)
            m = ok[sl]
            if not m.any():
                continue
            ii = np.where(m)[0] + a
            zz, t_ = mezcla_cota(xs[ii], ys[ii], d[ii], g[ii], np.maximum(o[ii], 0.0), self.X, self.Y, self.nx, self.ny, self.Wd,
                                 self.js_in, self.Zs_in, self.tree_s, self.lado, self.N, self.paso, self.AT, self.u_flat)
            zb[ii] = zz; tt[ii] = t_
        return zb, o, ok, tt, g


def perfil_terrazas(nt, sg, AT=21.0, H1=0.5, HT=6.0, BORD=1.5, TR=2.5):
    """Perfil transversal del contrato 15b (u = metros desde el borde del asfalto ->
    z relativa a Z(s)): bordillo u < 1.0 a -0.4 (bajo el borde del asfalto), rampa
    hasta sg*H1 en u = BORD (1.5); terraza k LLANA hasta AT(k+1)-TR (18.5), rampa del
    muro en el lado de la terraza k (la BAJA en ladera; en el mar queda en el patio de
    la alta para que la calle de k+1, al pie del muro, apoye entera) hasta AT(k+1), y
    la terraza k+1 llana desde AT(k+1) exactamente. Devuelve (xp, fp, hs)."""
    hs = [sg * (H1 + HT * k) for k in range(nt)]
    xp = [0.0, 1.0, BORD]
    fp = [-0.4, -0.4, hs[0]]
    for k in range(nt):
        xp.append(AT * (k + 1) - TR); fp.append(hs[k])
        xp.append(AT * (k + 1)); fp.append(hs[k + 1] if k < nt - 1 else hs[k])
    return xp, fp, hs


def perfiles_tras_terraza(zg, gx0, gy0, cell, X, Y, Wd, nx, ny, js, lado, o_fin, H, tree_land, idx_land, N, paso,
                          half_land, tierra_g, terr_mask, terr_sec, terr_g, i_sc, paso_o=1.0):
    """RONDA 15c: perfil del terreno detras de la ULTIMA terraza a lo largo de la normal de cada
    muestra js (o_fin-3 .. o_fin+H cada paso_o). El perfil se CORTA (el resto ya es terreno de otro
    elemento, no un foso) donde el punto: es mar; entra en el CORREDOR de otro ramal de la pista
    (< 6 m de su asfalto, muestra a > 40 m por la pista); o entra en terrazas LLANAS que no son las
    de su normal (otro sector, u otra rama / pliegue del mismo: muestra a > DS_PROPIO por la pista).
    Las laderas entre ramales SI cuentan (ahi el valle es un foso que se rellena).
    Devuelve (oo, zz, valido) con zz (len(js) x len(oo)) y valido = mascara del prefijo util."""
    oo = np.arange(o_fin - 3.0, o_fin + H + 1e-6, paso_o)
    js = np.asarray(js, dtype=int)
    d = Wd[js][:, None] / 2.0 + oo[None, :]
    px = X[js][:, None] + lado * nx[js][:, None] * d
    py = Y[js][:, None] + lado * ny[js][:, None] * d
    fy = (py.ravel() - gy0) / cell; fx = (px.ravel() - gx0) / cell
    zz = map_coordinates(zg, [fy, fx], order=1, mode='nearest').reshape(px.shape)
    dk, il = tree_land.query(np.column_stack([px.ravel(), py.ravel()]))
    gl = idx_land[il].reshape(px.shape)
    dl = np.abs(gl - js[:, None]); dl = np.minimum(dl, N - dl) * paso
    corredor = ((dk - half_land[il]).reshape(px.shape) < 6.0) & (dl > 40.0)
    ny_, nx_ = zg.shape
    ci = (np.clip(np.round(fy).astype(int), 0, ny_ - 1) * nx_ + np.clip(np.round(fx).astype(int), 0, nx_ - 1)).reshape(px.shape)
    tg = terr_g[ci]
    dg = np.abs(tg - js[:, None]); dg = np.minimum(dg, N - dg) * paso
    llana_ajena = terr_mask[ci] & ((terr_sec[ci] != i_sc) | (dg > DS_PROPIO))
    malo = ~tierra_g[ci] | corredor | llana_ajena
    malo[:, :4] = False                       # el arranque (patio de la ultima terraza) siempre cuenta
    valido = np.cumsum(malo, axis=1) == 0
    return oo, zz, valido


def nivel_agua(zz, valido, cap=None):
    """Perfil relleno hasta el nivel de 'agua atrapada' (prefijo valido): min(max a la izquierda,
    max a la derecha). Con cap (cota de la ultima terraza - 0.6) el patio de arranque cuenta como
    cap: justo detras del muro el terraplen queda 0.6 bajo la terraza. Devuelve (relleno, prof)
    con prof = profundidad del foso (nivel - z, 0 donde no hay agua)."""
    zv = np.where(valido, zz, -1e9)
    zl = zv.copy()
    if cap is not None:
        zl[:, :4] = np.minimum(zl[:, :4], cap[:, None])
    lm = np.maximum.accumulate(zl, axis=1)
    rm = np.maximum.accumulate(zv[:, ::-1], axis=1)[:, ::-1]
    lv = np.minimum(lm, rm)
    prof = np.where(valido, np.maximum(lv - zz, 0.0), 0.0)
    return np.where(valido, np.maximum(lv, zz), zz), prof


BRI_FUNDIDO = (40.0, 20.0)   # v2 (J2-04/H2-3): fundido de pend 3.0 -> 1.3 de d_bri 40 a 60 m (a > 60 m del viaducto F-07 no cambia)
CAS_FUNDIDO = 60.0           # v2 (J2-04/H2-3): ... y de dc_cas 350 a 410 m
T_DESMONTE_C1 = 10.0     # v2 (B2-05/D2-11): longitud (m) del acuerdo parabolico entre el corredor y la cara de desmonte


def techo_desmonte_c1(z0, dedge, T=T_DESMONTE_C1, d_llano=4.5, pend=1.15):
    """v2 (revision B2-05/D2-11): techo de desmonte C1 a distancia dedge del borde del asfalto: z0-0.5 hasta d_llano y
    despues z0 - 0.5 + pend*(t^2/(2T) si t < T, si no t - T/2), t = dedge - d_llano. Sin escalon ni quiebro."""
    t = np.maximum(np.asarray(dedge, float) - d_llano, 0.0)
    return z0 - 0.5 + pend * np.where(t < T, t * t / (2.0 * T), t - 0.5 * T)


BANCO_H = 11.5           # v3 (revision C-02): cada BANCO_H m de cota la cara tras la ultima terraza tiene una repisa (fascia)
                         # F1 (bloque 1.2): 16 -> 11.5 (2-4 repisas en una cara de 25-50 m)
BANCO_CONTRASTE = 0.9    # F1: fraccion de la amplitud maxima sin invertir la pendiente (repisa 0.1x, cara 1.9x)
BANCO_A = round(BANCO_CONTRASTE * BANCO_H / (2.0 * math.pi), 2)   # 1.65 m (con 2.5 y H 11.5 la cara se invertia: fosos)


def techo_tras_terraza(rise, p_desm, w_banco, berma=0.0):
    """v3 (revision C-02): techo detras de la ultima terraza a 'rise' m del pie (o - o_fin - TM/2). Antes una cara UNICA de
    p_desm (1.15) de hasta 50-55 m (tajo plano de cantera pintado entero de roca detras de pueblo_subida_ladera). Ahora la
    misma pendiente MEDIA (no se rebaja el espolon del coche: plan T1, >= 90 m a 120 m del tunel) pero en BANCALES ligures:
    la cota del corte c = rise*p_desm se modula c - A*(1 + sin(2*pi*c/H)): repisas casi llanas cada H m de cota (hierba)
    y caras mas empinadas entre ellas (roca); continua, monotona, solo baja (como mucho 2A) y nula en los
    primeros 3 m (el patio de la terraza no cambia). w_banco (0..1): peso (0 en el espolon del coche y fuera del pueblo).
    F1 (bloque 1.2): 'berma' (m, escalar o array por celda) = franja casi llana (BERMA_TERRAZA_PEND) entre el patio y el
    arranque de la cara; la cara empieza 'berma' m mas lejos. Con berma 0 es exactamente la v3.
    F1 r2: tras la berma, acuerdo parabolico de BERMA_ACUERDO_T m (escalado por la berma: con berma 0 no hay acuerdo) y cara
    x BERMA_CARA_FACTOR (solo donde hay berma; en el espolon del coche, sin berma, sigue p_desm)."""
    r = np.maximum(rise, 0.0)
    _wb = np.clip(np.asarray(berma, float) / 10.0, 0.0, 1.0)
    _T = np.maximum(BERMA_ACUERDO_T * _wb, 1e-3)
    x = np.maximum(r - berma, 0.0)
    q = np.where(_wb > 0.0, np.where(x < _T, x * x / (2.0 * _T), x - 0.5 * _T), x)   # (sin berma: q = x exacto, v3)
    c = BERMA_TERRAZA_PEND * np.minimum(r, berma) + q * p_desm * (1.0 + (BERMA_CARA_FACTOR - 1.0) * _wb)
    # bancales: v3 = c - A (1 + sin(2 pi c / H)) con rampa desde c = 3. Con berma (r2) la modulacion arranca en FASE CERO al final
    # de la berma (c0 = 0.25 x berma): A (1 - cos(2 pi (c - c0) / H)), nula y con derivada nula en c0 (la rampa de la v3 sobre
    # el seno abria un diente de 1-2 m justo tras la berma: 'agua atrapada' de 2.04 m en pueblo_alto_ladera); pendiente >= 0.1x
    c0 = BERMA_TERRAZA_PEND * np.asarray(berma, float)
    mod_v3 = np.clip((c - 3.0) / 3.0, 0.0, 1.0) * BANCO_A * (1.0 + np.sin(2.0 * np.pi * c / BANCO_H))
    mod_r2 = np.where(c > c0, BANCO_A * (1.0 - np.cos(2.0 * np.pi * np.maximum(c - c0, 0.0) / BANCO_H)), 0.0)
    return c - w_banco * ((1.0 - _wb) * mod_v3 + _wb * mod_r2)


def tri_malla(zg, gx0, gy0, cell, nxg, nyg, px, py):
    """v2: triangulo de la malla de construir_pista ((a,a+1,a+nx+1) si u >= v, si no (a,a+nx+1,a+nx); a = j*nx+i) que
    contiene cada punto: (vertices (n,3), pesos baricentricos (n,3)). Es la MISMA superficie que render, kn5 e inspectores."""
    fx = (np.asarray(px, float) - gx0) / cell; fy = (np.asarray(py, float) - gy0) / cell
    i = np.clip(np.floor(fx).astype(int), 0, nxg - 2); j = np.clip(np.floor(fy).astype(int), 0, nyg - 2)
    u = np.clip(fx - i, 0.0, 1.0); v = np.clip(fy - j, 0.0, 1.0)
    a = j * nxg + i
    sup = u >= v
    vt = np.where(sup[:, None], np.c_[a, a + 1, a + nxg + 1], np.c_[a, a + nxg + 1, a + nxg])
    wt = np.where(sup[:, None], np.c_[1.0 - u, u - v, v], np.c_[1.0 - v, u, v - u])
    return vt, wt


def bajar_bajo_asfalto(z_grid, gx0, gy0, cell, nxg, nyg, X, Y, Z, nx, ny, Wd, lat, sec, fijo=None, margen=0.05,
                       paso_l=0.5, max_pasadas=12, tope_in=3.0, tope_fuera=0.5, d_fuera=1.0):
    """v2 (revision C2-01/D2-01/G2-03/E2-01/E2-08/F2-11): GARANTIA POR TRIANGULO de que la hierba no asoma sobre el asfalto.
    Las reglas de pista acotan los VERTICES (corredor a Z-0.5 bajo la calzada), pero con celdas de 4 m y la diagonal fija
    un triangulo entre un vertice bajo la calzada y otro de fuera (bordillo de las terrazas a +0.5, desmonte, cuna de una
    horquilla) cruza la cota del asfalto DENTRO de la calzada (hasta +0.41 m en 223 puntos; el peralte lo empeora en el
    lado bajo). Puntos de control cada 1 m en s y cada paso_l m a lo ancho (muestras en tierra), con la cota del plano
    peraltado z = Z - lat*l (la de construir_pista). Donde el plano del triangulo pasa de z - margen se bajan SOLO lo
    justo (correccion de norma minima dz_v = exceso*b_v/sum(b^2)) los vertices de ese triangulo que estan BAJO la calzada
    (los tapa el asfalto: no abre huecos fuera); si su peso es < 0.35, tambien los de fuera a < d_fuera m del borde (bajo
    el arcen/bordillo) con un tope de tope_fuera m. Nunca sube nada ni toca los vertices 'fijo' (rotonda Loews).
    Devuelve (z_nuevo, info)."""
    z = np.asarray(z_grid, float).ravel().copy()
    X = np.asarray(X, float); Y = np.asarray(Y, float); Z = np.asarray(Z, float)
    nx = np.asarray(nx, float); ny = np.asarray(ny, float); Wd = np.asarray(Wd, float)
    lat = np.zeros(len(X)) if lat is None else np.asarray(lat, float)
    N = len(X)
    tierra_s = np.array([s != 'bridge' for s in sec])
    ii = np.where(tierra_s & tierra_s[(np.arange(N) + 1) % N])[0]
    jj = (ii + 1) % N
    PX = []; PY = []; PZ = []
    for t in (0.0, 0.5):
        x = X[ii] * (1 - t) + X[jj] * t; y = Y[ii] * (1 - t) + Y[jj] * t; zz = Z[ii] * (1 - t) + Z[jj] * t
        vx = nx[ii] * (1 - t) + nx[jj] * t; vy = ny[ii] * (1 - t) + ny[jj] * t
        nn = np.hypot(vx, vy); vx = vx / nn; vy = vy / nn
        w = Wd[ii] * (1 - t) + Wd[jj] * t; la = lat[ii] * (1 - t) + lat[jj] * t
        nl = int(math.ceil(float(w.max()) / paso_l)) + 1
        for f in np.linspace(-0.5, 0.5, nl):
            l = f * (w - 0.06)
            PX.append(x + vx * l); PY.append(y + vy * l); PZ.append(zz - la * l)
    PX = np.concatenate(PX); PY = np.concatenate(PY); PZ = np.concatenate(PZ)
    vt, wt = tri_malla(z, gx0, gy0, cell, nxg, nyg, PX, PY)
    # offset de cada vertice al borde del asfalto (negativo = bajo la calzada)
    nv = nxg * nyg
    usados = np.unique(vt)
    gxv = gx0 + (usados % nxg) * cell; gyv = gy0 + (usados // nxg) * cell
    tr = cKDTree(np.column_stack([X[tierra_s], Y[tierra_s]]))
    dv, kv = tr.query(np.column_stack([gxv, gyv]))
    o_v = np.full(nv, 1e9); o_v[usados] = dv - Wd[tierra_s][kv] / 2.0
    fijo = np.zeros(nv, bool) if fijo is None else np.asarray(fijo, bool).ravel()
    bajado = np.zeros(nv)
    exc0 = (z[vt] * wt).sum(1) - PZ
    info = dict(puntos=int(len(PX)), antes_gt_2cm=int((exc0 > 0.02).sum()), antes_max=round(float(exc0.max()), 3))
    for it in range(max_pasadas):
        exc = (z[vt] * wt).sum(1) - (PZ - margen)
        m = exc > 0.002
        if not m.any():
            break
        v_m = vt[m]; w_m = wt[m]; e_m = exc[m]
        dentro = (o_v[v_m] < 0.0) & ~fijo[v_m] & (bajado[v_m] < tope_in - 1e-3)
        b_in = w_m * dentro
        s1 = b_in.sum(1)
        cerca = (o_v[v_m] < d_fuera) & ~fijo[v_m] & np.where(o_v[v_m] < 0.0, bajado[v_m] < tope_in - 1e-3, bajado[v_m] < tope_fuera - 1e-3)
        b = np.where((s1 >= 0.35)[:, None], b_in, w_m * cerca)
        s2 = (b * b).sum(1)
        ok = s2 > 1e-9
        need = np.zeros(nv)
        dz = np.where(ok[:, None], (e_m + 0.003)[:, None] * b / np.maximum(s2, 1e-9)[:, None], 0.0)
        np.maximum.at(need, v_m.ravel(), dz.ravel())
        tope = np.where(o_v < 0.0, tope_in, tope_fuera)
        need = np.minimum(need, np.maximum(tope - bajado, 0.0))
        if need.max() < 1e-4:
            break
        z -= need
        bajado += need
    exc = (z[vt] * wt).sum(1) - PZ
    info.update(despues_gt_2cm=int((exc > 0.02).sum()), despues_max=round(float(exc.max()), 3), pasadas=it + 1,
                vertices_bajados=int((bajado > 1e-3).sum()), bajada_max=round(float(bajado.max()), 2),
                fuera_bajados=int(((bajado > 1e-3) & (o_v >= 0.0)).sum()),
                fuera_bajada_max=round(float(np.where(o_v >= 0.0, bajado, 0.0).max()), 2),
                residuo_en_fijo=int(((exc > 0.02) & fijo[vt].any(1)).sum()))
    return z, info


# ---------------------------------------------------------------------------
# construir
# ---------------------------------------------------------------------------
def landforms_loews():
    """v1: los LANDFORMS con el Promontorio del casino ANTERIOR a la revision G1/G4 (cumbre de 170 m en (665,-470)). Solo
    para congelar el terreno alrededor de la rotonda Loews (construir_loews_intacta)."""
    out = []
    for lf in LANDFORMS:
        if lf['nombre'] == 'Promontorio del casino':
            lf = dict(lf, s_foot=0.55, pts=[(560, -300, 95), (620, -390, 140), (665, -470, 170)])
        out.append(lf)
    return out


# v2 (revision J-N2): terreno de REFERENCIA FIJO de la rotonda Loews (volcado una vez del terreno entregado, 03/10)
LOEWS_REF = _osp.path.join(_osp.path.dirname(_osp.path.abspath(__file__)), 'assets', '_loews_terreno.npz')
R_LOEWS_REF = R_LOEWS_CONG[1] + 8.0          # radio guardado (cubre el fundido entero)


def rejilla_de(X, Y, cell=4.0):
    """(gx0, gy0, nxg, nyg) de la rejilla de construir() para estas muestras (MISMAS formulas)."""
    X = np.asarray(X, float); Y = np.asarray(Y, float)
    gx0 = X.min() - 220.0; gx1 = X.max() + 520.0
    gy0 = Y.min() - 220.0; gy1 = Y.max() + 560.0
    return gx0, gy0, int((gx1 - gx0) / cell) + 1, int((gy1 - gy0) / cell) + 1


def guardar_loews_ref(geom_json, spec_json, ruta=LOEWS_REF, radio=R_LOEWS_REF):
    """v2 (J-N2): referencia FIJA de la Loews a partir de un geometria_3d.json ENTREGADO (y el urbanismo_spec.json con el
    que se hizo). Se hace UNA vez, con el codigo que genero ese terreno. a < R_LOEWS_CONG[0]: z y es_mar entregados
    (exactos); de R_LOEWS_CONG[0] a radio: el terreno 'viejo' (promontorio antiguo) con el que se fundio, para que el
    fundido reproduzca el terreno entregado mientras el codigo de esa zona no cambie."""
    import json, io, contextlib
    G = json.load(open(geom_json, encoding='utf-8'))
    spec = json.load(open(spec_json, encoding='utf-8'))
    t = G['terreno']
    Mu = G['muestras']
    arr = lambda k: np.array([m[k] for m in Mu], float)
    with contextlib.redirect_stdout(io.StringIO()):
        viejo = construir(arr('x'), arr('y'), arr('z'), [m['sec'] for m in Mu], arr('w'), arr('nx'), arr('ny'), G['paso_m'],
                          G['largo_m'], G['curvas'], G['pit_lane'], (G['loews']['x'], G['loews']['y']), spec,
                          [(m['s0'], m['s1'], m['side'], m['ancho']) for m in G.get('miradores', [])],
                          cell=float(t['cell']), qa_dir=None, landforms=landforms_loews())
    gx = t['x0'] + np.arange(t['nx']) * t['cell']; gy = t['y0'] + np.arange(t['ny']) * t['cell']
    GX, GY = np.meshgrid(gx, gy)
    d = np.hypot(GX.ravel() - G['loews']['x'], GY.ravel() - G['loews']['y'])
    idx = np.where(d < radio)[0]
    z_ent = np.asarray(t['z'], float)[idx]
    z_v = np.asarray(viejo['z_grid'], float).ravel()[idx]
    print('  referencia de la Loews: |entregado - viejo| a < %.0f m: %.3f m' % (R_LOEWS_CONG[0], float(np.abs(z_ent - z_v)[d[idx] < R_LOEWS_CONG[0]].max())))
    np.savez(ruta, idx=idx, z=np.where(d[idx] < R_LOEWS_CONG[0], z_ent, z_v), mar=np.asarray(t['mar'], bool)[idx],
             x0=float(t['x0']), y0=float(t['y0']), cell=float(t['cell']), nx=int(t['nx']), ny=int(t['ny']),
             cx=float(G['loews']['x']), cy=float(G['loews']['y']), radio=float(radio))
    print('referencia de la Loews: %d celdas (r < %.0f m) -> %s' % (len(idx), radio, ruta))
    return ruta


def construir_loews_intacta(*args, **kw):
    """v1 (peticion del usuario: 'la rotonda Loews se queda EXACTAMENTE como esta'): el cambio del Promontorio (G1/G4)
    movia hasta 10 m el terreno a < 30 m del centro de la rotonda. El terreno definitivo toma tal cual el de referencia a
    < R_LOEWS_CONG[0] del centro de la Loews y funde hasta R_LOEWS_CONG[1].
    v2 (revision J-N2): la referencia es FIJA: assets/_loews_terreno.npz (volcado del terreno entregado). Antes se
    reconstruia con el codigo ACTUAL y el promontorio antiguo, asi que cualquier cambio del tiron o de la costa movia
    tambien la 'referencia' (hasta 17.5 m a < 40 m) y el log seguia diciendo 'intacta'. Si el fichero no esta o la rejilla
    no coincide, se vuelve al metodo antiguo (con aviso)."""
    import io, contextlib
    cell = float(kw.get('cell', 4.0))
    gx0, gy0, nxg, nyg = rejilla_de(args[0], args[1], cell)
    if _osp.path.exists(LOEWS_REF):
        ref = np.load(LOEWS_REF)
        if (abs(float(ref['x0']) - gx0) < 0.06 and abs(float(ref['y0']) - gy0) < 0.06 and int(ref['nx']) == nxg
                and int(ref['ny']) == nyg and abs(float(ref['cell']) - cell) < 1e-6):
            kw['congelar'] = dict(idx=np.asarray(ref['idx'], int), z=np.asarray(ref['z'], float),
                                  mar=np.asarray(ref['mar'], bool), fijo=True)
            return construir(*args, **kw)
        print('  AVISO: %s no coincide con la rejilla (%.1f, %.1f, %d x %d): referencia reconstruida (metodo v1)'
              % (LOEWS_REF, gx0, gy0, nxg, nyg))
    else:
        print('  AVISO: falta %s: referencia de la Loews reconstruida (metodo v1)' % LOEWS_REF)
    kw0 = dict(kw); kw0['qa_dir'] = None
    with contextlib.redirect_stdout(io.StringIO()):
        viejo = construir(*args, landforms=landforms_loews(), **kw0)
    kw['congelar'] = dict(z_grid=viejo['z_grid'], es_mar=viejo['es_mar'])
    return construir(*args, **kw)


def construir(X, Y, Z, sec, Wd, nx, ny, paso, L, curvas, pit_pts, loews_centro,
              spec_urb, miradores, cell=4.0, qa_dir=None, seed=15, debug_xy=None, landforms=None, congelar=None, lat=None):
    X = np.asarray(X, float); Y = np.asarray(Y, float); Z = np.asarray(Z, float)
    Wd = np.asarray(Wd, float); nx = np.asarray(nx, float); ny = np.asarray(ny, float)
    peralte = None if lat is None else np.asarray(lat, float)       # v2 ('lat' se reutiliza abajo como lateral de las celdas)
    N = len(X)
    if isinstance(curvas, dict):
        curvas = list(curvas.values())
    curvas = curvas_en_metros(curvas, X, Y)
    checks = {}
    # --- rejilla: margen 220 al O y al S (mar), 560 al N y 520 al E; la isla se
    # cierra con mar a ~R_ISLA de la pista, asi que el borde N/E queda en el agua ---
    gx0 = X.min() - 220.0; gx1 = X.max() + 520.0
    gy0 = Y.min() - 220.0; gy1 = Y.max() + 560.0
    nxg = int((gx1 - gx0) / cell) + 1
    nyg = int((gy1 - gy0) / cell) + 1
    gx = gx0 + np.arange(nxg) * cell
    gy = gy0 + np.arange(nyg) * cell
    GX, GY = np.meshgrid(gx, gy)
    gpts = np.column_stack([GX.ravel(), GY.ravel()])
    ncel = len(gpts)
    _dbg_idx = []
    _w_mcl = peso_fuera_zonas(gpts, nxg, nyg, cell, spec_urb)      # v3: 0 en la huella del McLaren (+25 m)
    _w_mcl_c = peso_fuera_zonas(gpts, nxg, nyg, cell, spec_urb, margen=10.0, fundido=10.0)   # ... (+10 m: orilla J6)
    # F1 r2: lo NUEVO de F1 (bancales en el espolon del coche, costillas de 4 m) a 0 hasta +30 m (fundido 15): medir_relieve
    # (EDT de la huella con otra rasterizacion) media 0.68 m a 22.6 m con el margen de 25; el encaje del coche exige 0.000 a < 25 m
    _w_mcl_f1 = peso_fuera_zonas(gpts, nxg, nyg, cell, spec_urb, margen=TIERRA_MCL_MARGEN[0], fundido=TIERRA_MCL_MARGEN[1])
    if debug_xy:
        for (qx, qy) in debug_xy:
            _dbg_idx.append(int(round((qy - gy0) / cell)) * nxg + int(round((qx - gx0) / cell)))

    def dbg(nombre, arr):
        if _dbg_idx:
            a = np.asarray(arr).ravel()
            print('    [dbg] %-14s %s' % (nombre, ' '.join('%8.2f' % a[k] for k in _dbg_idx)))

    sec = list(sec)
    no_bridge = np.array([s != 'bridge' for s in sec])
    bridge_flag = ~no_bridge
    tree_all = cKDTree(np.column_stack([X, Y]))
    tree_land = cKDTree(np.column_stack([X[no_bridge], Y[no_bridge]]))
    tree_bridge = cKDTree(np.column_stack([X[~no_bridge], Y[~no_bridge]])) if bridge_flag.any() else None
    Z_land = Z[no_bridge]
    half_land = Wd[no_bridge] / 2.0
    idx_land = np.where(no_bridge)[0]
    d_all, i_all = tree_all.query(gpts)
    d_land, i_land = tree_land.query(gpts)
    if tree_bridge is not None:
        d_bri, i_bri = tree_bridge.query(gpts)
    else:
        d_bri, i_bri = np.full(ncel, 1e9), np.zeros(ncel, dtype=int)

    # --- lado del mar respecto a la recta de meta (como antes) ---
    tx0 = -ny[0]; ty0 = nx[0]            # tangente = rotacion de la normal izquierda
    p0 = np.array([X[0], Y[0]])
    v = gpts - p0
    side = tx0 * v[:, 1] - ty0 * v[:, 0]  # >0 = izquierda de la marcha
    v_tr = np.column_stack([X, Y]) - p0
    side_tr = tx0 * v_tr[:, 1] - ty0 * v_tr[:, 0]
    if np.mean(side_tr > 0) > 0.5:
        side = -side
        print('orientacion del mar invertida')

    # --- TIERRA PROTEGIDA alrededor de la pista en tierra: radio CONTINUO con la
    # cota de cada muestra, r_j = 30 + 1.7*(z_j - 4); union EXACTA de discos
    # (rasterizada; antes k=96 vecinos: fragil con muchas muestras altas) ---
    r_prot = 30.0 + 1.7 * np.maximum(Z_land - 4.0, 0.0)
    protegido = union_discos(nxg, nyg, gx0, gy0, cell, X[no_bridge], Y[no_bridge], r_prot)
    protegido = protegido | (d_land <= 30.0)
    cerca_de_puente = bridge_flag[i_all] & (d_all <= 18)
    nb = int(bridge_flag.sum())
    estribo = (i_bri * paso < ESTRIBO_M) | ((nb - 1 - i_bri) * paso < ESTRIBO_M)
    mar_forzado = (d_bri <= 40.0) & bridge_flag[i_all] & ~estribo & (d_land > 85.0)
    s_land = idx_land * paso
    half_c = half_land[i_land]
    # --- PENON DEL CASINO (RONDA 15c): la elipse de zona_casino() es el solar de la roca.
    # Nucleo (r_n < CASINO_R_MAR) y bahia seaward (arco CASINO_BAHIA, hasta r_n 1.8) = MAR
    # forzado (salvo a < w/2+30 del asfalto: el corredor de la rotonda y su caida al 400 %
    # se quedan en tierra para que el difuminado de la costa no los toque) ---
    # v1: distancia al centro de la rotonda Loews (peticion del usuario: la rotonda se queda EXACTAMENTE como esta)
    d_loews = (np.hypot(gpts[:, 0] - float(loews_centro[0]), gpts[:, 1] - float(loews_centro[1]))
               if loews_centro is not None else np.full(ncel, 1e9))
    el_casino = elipse_casino(X, Y, curvas)
    casino_zona = np.zeros(ncel, bool); casino_mar = np.zeros(ncel, bool); r_cas = np.full(ncel, 9.0)
    if el_casino is not None:
        r_cas, ang_cas, dc_cas = coords_casino(gpts[:, 0], gpts[:, 1], el_casino)
        casino_zona = r_cas < 2.2
        # v1 (revision G11): la bahia llega hasta r 2.6 (antes 1.8: quedaba una lengua de tierra con la cara N vertical)
        # (la rotonda Loews se queda EXACTAMENTE como esta: a < R_LOEWS_INTACTA de su centro la bahia no cambia)
        en_bahia = (ang_cas >= CASINO_BAHIA[0]) & (ang_cas <= CASINO_BAHIA[1]) & ((r_cas < 1.8) | ((r_cas < 2.6) & (d_loews > R_LOEWS_INTACTA)))
        casino_mar = ((r_cas < CASINO_R_MAR) | en_bahia) & (d_land > half_c + 30.0)
        protegido = protegido & ~casino_mar
        mar_forzado = mar_forzado | casino_mar
        checks['casino_elipse'] = [round(v, 2) for v in el_casino]
    # v3 (revision H2 (1)): el canal del viaducto (s 3640-3930) era un mar forzado de ANCHO FIJO (d_bri <= 40): la muralla N
    # (y el lobulo SO del promontorio) era la paralela exacta del tablero. El radio pasa a 40 - 14*n (n = ruido de 140 m en
    # 0..1): solo ESTRECHA el canal (minimo 26 m; el tablero tiene 6 m de semiancho), asi que la coronacion nunca retrocede
    # hacia las terrazas de casino_*. Fuera del penon y de su entorno (r < 1.9, lo que lee roca_casino) y a > R_LOEWS_INTACTA
    # de la Loews (fundidos 0.3 y 20 m)
    _sb_g = (np.where(bridge_flag)[0][i_bri] * paso) if tree_bridge is not None else np.full(ncel, -1e9)
    _wcan = (np.clip((_sb_g - 3630.0) / 20.0, 0.0, 1.0) * np.clip((3940.0 - _sb_g) / 20.0, 0.0, 1.0)
             * np.clip((d_loews - R_LOEWS_INTACTA) / 20.0, 0.0, 1.0) * np.clip((r_cas - 1.9) / 0.3, 0.0, 1.0))
    _r_mf = 40.0 - 14.0 * np.clip(ruido_valor(np.random.default_rng(seed + 47), nyg, nxg, cell, 140.0).ravel(), 0.0, 1.0) * _wcan
    mar_forzado = ((d_bri <= _r_mf) & bridge_flag[i_all] & ~estribo & (d_land > 85.0)) | casino_mar
    checks['canal_viaducto_radio_min'] = round(float(_r_mf[_wcan > 0.99].min()), 1) if (_wcan > 0.99).any() else 40.0
    # v2 (revision I-R2-02 (e)): la ORILLA era el borde de la union de discos de proteccion; los discos que crecen con la cota
    # a lo largo de una recta tienen por envolvente otra recta (orilla recta de 300 m frente al viaducto). Lejos de la pista
    # (> 80 m) se QUITA proteccion (nunca se anade) en manchas de ruido de 70 m fuera de unos discos interiores mas
    # pequenos (1.36 en vez de 1.7 por metro de cota): calas de 20-37 m, nada cambia a < 80 m de la pista
    _r_in = 30.0 + 1.36 * np.maximum(Z_land - 4.0, 0.0)
    _p_in = union_discos(nxg, nyg, gx0, gy0, cell, X[no_bridge], Y[no_bridge], _r_in)
    _nc = ruido_valor(np.random.default_rng(seed + 31), nyg, nxg, cell, 70.0).ravel()
    _quita = (d_all > 80.0) & ~_p_in & (_nc < 0.0)
    if el_casino is not None:
        _quita &= dc_cas > 400.0                   # el penon y su promontorio no se tocan
    protegido = protegido & ~_quita
    # --- zona del coche-montana: celdas a < ZONA_COCHE_D del tunel (s 380-640) en su lado -1;
    # ahi el desmonte detras de las terrazas de pueblo_subida_ladera es mas empinado ---
    ii_car = idx_land[(s_land >= 380.0) & (s_land <= 640.0)]
    zona_coche = np.zeros(ncel, bool); w_coche = np.zeros(ncel)
    if len(ii_car):
        d_car, k_car = cKDTree(np.column_stack([X[ii_car], Y[ii_car]])).query(gpts)
        gcar = ii_car[k_car]
        lat_car = (gpts[:, 0] - X[gcar]) * nx[gcar] + (gpts[:, 1] - Y[gcar]) * ny[gcar]
        # RONDA 15c: peso CONTINUO (antes booleano: en el borde de la zona el desmonte saltaba de 1.15 a
        # 2.0 entre celdas vecinas y dejaba escalones de 20-30 m en la ladera detras de la C6)
        w_coche = np.clip((ZONA_COCHE_D - d_car) / 50.0, 0.0, 1.0) * np.clip(-lat_car / 25.0, 0.0, 1.0)
        zona_coche = w_coche > 0.5
    # --- factor de los valles: 0 en las bandas de terrazas (+25 m), 1 a 60 m mas alla ---
    AT_v = float(spec_urb.get('ancho_terraza', 21.0))
    fac_valle = np.ones(ncel)
    for sc in spec_urb.get('sectores', []):
        jj = idx_land[(s_land >= float(sc['s0'])) & (s_land <= float(sc['s1']))]
        if len(jj) == 0 or int(sc['n_terrazas']) < 1:
            continue
        d_sc, k_sc = cKDTree(np.column_stack([X[jj], Y[jj]])).query(gpts, distance_upper_bound=400.0)
        d_sc = np.where(np.isfinite(d_sc), d_sc, 1e9) - Wd[jj[np.where(np.isfinite(d_sc), k_sc, 0)]] / 2.0
        fac_valle = np.minimum(fac_valle, np.clip((d_sc - (AT_v * int(sc['n_terrazas']) + 25.0)) / 60.0, 0.0, 1.0))
    # la isla se cierra: mar a mas de ~R_ISLA de la pista (radio modulado con
    # ruido de 260 m para que la costa N/E no sea un offset uniforme del trazado)
    r_isla = R_ISLA * (1.0 + 0.15 * ruido_valor(np.random.default_rng(seed + 7), nyg, nxg, cell, 260.0).ravel())
    es_mar = ((((side > 0) & (d_all > 45))
               | ((d_bri < 90) & (bridge_flag[i_all] | (side > 0)))
               | cerca_de_puente | (d_all > r_isla)) & ~protegido) | mar_forzado
    # v1 (revision J5): el borde O de la rejilla (gx0 = X.min() - 220 < R_ISLA) quedaba en TIERRA a 2 m con la malla abierta:
    # mar a < 70-130 m (ruido de 200 m) de cualquier borde, salvo tierra protegida
    _db = np.minimum(np.minimum(gpts[:, 0] - gx0, gx1 - gpts[:, 0]), np.minimum(gpts[:, 1] - gy0, gy1 - gpts[:, 1]))
    _nb = 0.5 * (1.0 + ruido_valor(np.random.default_rng(seed + 11), nyg, nxg, cell, 200.0).ravel())
    es_mar = es_mar | ((_db < 70.0 + 60.0 * _nb) & ~protegido)
    # v1 (revision H2, parte 1): la ALETA de tierra de 20-35 m de ancho y 50-64 m de alto que dejaba el canal del viaducto
    # (arco de los discos de proteccion de s 3600-3630 cortado por la garganta) pasa a mar: tierra que no contiene un
    # disco de 45 m (apertura morfologica), a < 160 m del viaducto y a > 60 m de la pista en tierra
    _rr = int(round(45.0 / cell)); _yy, _xx = np.ogrid[-_rr:_rr + 1, -_rr:_rr + 1]; _disco = (_xx * _xx + _yy * _yy) <= _rr * _rr
    _tg = (~es_mar).reshape(nyg, nxg)
    _fina = (_tg & ~binary_opening(_tg, structure=_disco)).ravel() & (d_bri < 160.0) & (d_land > 60.0)
    checks['aleta_viaducto_celdas'] = int(_fina.sum())
    es_mar = es_mar | _fina; protegido = protegido & ~_fina
    # lagunas interiores (mar sin conexion con el borde de la rejilla) -> tierra
    lab, nlab = _label(es_mar.reshape(nyg, nxg))
    borde = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])))
    borde.discard(0)
    keep = np.isin(lab, list(borde))
    n_lagunas = int((es_mar.reshape(nyg, nxg) & ~keep).sum())
    es_mar = (es_mar.reshape(nyg, nxg) & keep).ravel()
    checks['lagunas_eliminadas_celdas'] = n_lagunas

    # --- macizo natural + tirar hacia la rasante de la pista ---
    M = macizo_base(GX, GY, cell, seed=seed, fac_valle=fac_valle, landforms=landforms)
    dbg('M_base', M)
    # la recta del tunel (s 200-640) tira poco: sus dos flancos son desmonte
    # (espolon del coche) y acantilado al mar, no una ladera que seguir
    peso = np.where((s_land >= 200.0) & (s_land <= 640.0), 0.3, 1.0)
    # F1 (bloque 1.1): las muestras de tierra pesan TIERRA_PESO_TIRON (es un peso RELATIVO dentro de la media gaussiana: solo
    # cambia algo donde conviven con muestras de asfalto, en los dos extremos del tramo; en medio del lazo la media es la misma)
    _dirt_s = np.array([s_ == 'dirt' for s_ in sec])
    peso0 = peso
    peso = np.where(_dirt_s[no_bridge], TIERRA_PESO_TIRON, peso)
    C = _idw_pull(GX, GY, M, cell, X[no_bridge], Y[no_bridge], Z_land, sigma=100.0, cada=8.0, paso=paso, peso=peso)
    # F1 r2: el peso de la tierra solo cambia el tiron DENTRO del tramo de tierra (celdas a < 100 m de una muestra 'dirt',
    # fundido a 160 m) y FUERA del corredor (< 4.5 m del borde, fundido a 8 m): en el resto z_land es el de antes de F1. La
    # media gaussiana (sigma 100 m) cambiaba 0.01-0.11 m a 300 m de la tierra (McLaren + 14-23 m: 'dz 0.11 a < 25 m') y en el
    # corredor volteaba el clip z0-0.6 / z0-0.5 (dz 0.10 en 224 celdas): los dos deben ser 0.000
    if _dirt_s[no_bridge].any():
        C0 = _idw_pull(GX, GY, M, cell, X[no_bridge], Y[no_bridge], Z_land, sigma=100.0, cada=8.0, paso=paso, peso=peso0)
        _dd_dirt, _ = cKDTree(np.column_stack([X[no_bridge][_dirt_s[no_bridge]], Y[no_bridge][_dirt_s[no_bridge]]])).query(gpts)
        # F1 r3: alcance 100-160 -> TIERRA_TIRON_ALCANCE (60-110): a 85-110 m de la tierra (ermita y cipreses del sendero ERMITA tras
        # pueblo_alto_ladera) el peso 0.5 bajaba el natural 0.6-1.5 m sin cambiar nada del KPI (que se mide a 25 m)
        _w_dirt = (np.clip((TIERRA_TIRON_ALCANCE[1] - _dd_dirt) / (TIERRA_TIRON_ALCANCE[1] - TIERRA_TIRON_ALCANCE[0]), 0.0, 1.0)
                   * np.clip((d_land - half_c - TIERRA_SIN_CORREDOR[0]) / (TIERRA_SIN_CORREDOR[1] - TIERRA_SIN_CORREDOR[0]), 0.0, 1.0))
        C = C0 + (C - C0) * _w_dirt.reshape(C.shape)
    # v2 (revision J2-01/J2-03, probado por el revisor): el tiron NORMALIZADO actua entero hasta ~170 m de la pista (sw >> 1
    # con muestras cada 8 m): al S de la salida del viaducto dejaba una MESA a 109 m (cota de la rasante sobre un macizo
    # de 18 m) con paredes de 60-105 m al mar, y al E del penon una cara plana de 156 m. Solo ahi el tiron POSITIVO decae
    # con la distancia a la pista (smoothstep 50-160 m en s 3540-3760, sector angular S/SO del penon; 100-220 m en s
    # 3380-3590). Fuera de R_LOEWS_CONG[1] de la Loews: la rotonda no cambia. (El decaimiento GLOBAL rompia la geografia
    # de casino_ladera.)
    _sn = (i_all * paso).reshape(nyg, nxg)
    _dl2 = d_land.reshape(nyg, nxg)
    for (_s0, _s1, _da, _db, _ang) in ((3540.0, 3760.0, 50.0, 160.0, True), (3380.0, 3590.0, 100.0, 220.0, False)):
        _loc = (_sn >= _s0) & (_sn <= _s1) & (d_loews.reshape(nyg, nxg) > R_LOEWS_CONG[1])
        if _ang and el_casino is not None:
            _a = ang_cas.reshape(nyg, nxg); _loc &= (_a <= -110.0) | (_a >= 150.0)
        _loc = gaussian_filter(_loc.astype(float), 3.0)
        _t = np.clip((_dl2 - _da) / (_db - _da), 0.0, 1.0); _dec = 1.0 - _t * _t * (3.0 - 2.0 * _t)
        C = np.where(C > 0, C * (1.0 - _loc + _loc * _dec), C)
    # v1 (revision J8, probado): el tiron de la pista (hasta -41 m a 170 m) aplanaba a 1.2 m una vega de 3.4 ha a 320 m del
    # mar; lejos de la pista (> 120 m, fundido 80 m) el suelo sube al 3.5 % desde la costa (drenaje natural)
    _dm1 = distance_transform_edt(~es_mar.reshape(nyg, nxg)) * cell
    # v2 (revision J2-10, probado): el suelo de drenaje empieza a 60 m (antes 120 m: vega a 2.2-3.8 m con arena en el prado)
    _w8 = np.clip((d_land.reshape(nyg, nxg) - 60.0) / 60.0, 0.0, 1.0)
    M = np.maximum(M + C, 1.2 + 0.035 * _dm1 * _w8)
    dbg('pull_C', C); dbg('M_pull', M)
    M = gaussian_filter(M, 1.0)
    # el borde de la rejilla cae a <= 2 m (nada de macizo cortado a cuchillo)
    d_borde = np.minimum(np.minimum(GX - gx0, gx1 - GX), np.minimum(GY - gy0, gy1 - GY))
    M = np.minimum(M, 2.0 + np.maximum(d_borde, 0.0) * PEND_NATURAL_MAX)
    # v1 (revision J1, probado por el revisor con 230 m; aqui 170 m para conservar las cumbres 210/183 m): la costa N y NE
    # era una pared gris de 70-130 m (los espolones llegan a la orilla). Lejos de la pista (> 150 m, fundido 100 m) y del
    # penon del casino (> 350 m) el macizo baja con una smoothstep hasta la costa en sus ultimos 170 m. A < 40 m de la
    # pista el cambio es 0.00 m
    _dm0 = distance_transform_edt(~es_mar.reshape(nyg, nxg)) * cell
    _tt = np.clip(_dm0 / 170.0, 0.0, 1.0); _ss = _tt * _tt * (3.0 - 2.0 * _tt)
    _wf = np.clip((d_all.reshape(nyg, nxg) - 150.0) / 100.0, 0.0, 1.0)
    if el_casino is not None:
        _wf = _wf * np.clip((dc_cas.reshape(nyg, nxg) - 350.0) / 100.0, 0.0, 1.0)
    M = 1.2 + (M - 1.2) * (1.0 - _wf * (1.0 - _ss))
    # LIMITADOR DE PENDIENTE del macizo natural (80 %): se aplica ANTES de los
    # acantilados y de los desmontes, que son las unicas caras > 100 % admitidas
    M, n_it_lim, rebaje_lim = limitar_pendiente(M, cell, PEND_NATURAL_MAX)
    # v1 (J1/G4): el limitador deja CARAS PLANAS al 80 % (conos octogonales) en las laderas que ahora bajan al mar: ruido
    # 'ridged' de 8 m (120/60/30 m) DESPUES del limitador, solo lejos de la pista y del penon (mismo peso que el fundido J1)
    _rid2 = ruido_ridged(np.random.default_rng(seed + 17), nyg, nxg, cell, octavas=((120.0, 1.0), (60.0, 0.5), (30.0, 0.25)))
    M = M + _wf * np.clip(M / 40.0, 0.0, 1.0) * 8.0 * (_rid2 - 0.35)
    # v3 (revision N1 (2)): las laderas del macizo seguian siendo planos al 75-88 % (conos del limitador) y la cara N se leia
    # como una piramide lisa. BARRANCOS que bajan como el agua: cada celda se sigue ladera ARRIBA (gradiente del macizo
    # suavizado 20 m, pasos de 4 m) hasta la curva de nivel 'cresta - 30 m' (maximo en 250 m - 30); el ruido (55 m) leido en
    # ese punto es constante a lo largo de cada linea de agua, y sus ceros son los ejes de las vaguadas: anchura constante
    # (~32 m, distancia al eje = |n|/|grad n|) y hondo creciente ladera abajo (0 a 20 m del punto de partida, 9 m a 120 m).
    # Solo donde M > 40 (nada en la costa J1) y con el peso _wf (> 150 m de la pista, > 350 m del penon: a < 40 m de la pista
    # no cambia nada); despues limitador al 85 % en las paredes de las vaguadas (solo baja)
    _Ms = gaussian_filter(M, 20.0 / cell); _gyM, _gxM = np.gradient(_Ms, cell)
    _zref = maximum_filter(_Ms, size=2 * int(250.0 / cell) + 1) - 30.0
    _selg = (M > 40.0) & (_Ms < _zref) & (_wf > 0.0)
    _gul = np.zeros((nyg, nxg))
    if _selg.any():
        _jj, _ii = np.nonzero(_selg)
        _fy = _jj.astype(float); _fx = _ii.astype(float); _zr = _zref[_selg]; _tr = np.zeros(len(_fy)); _act = np.ones(len(_fy), bool)
        for _ in range(120):
            _vx = map_coordinates(_gxM, [_fy, _fx], order=1, mode='nearest'); _vy = map_coordinates(_gyM, [_fy, _fx], order=1, mode='nearest')
            _mg = np.hypot(_vx, _vy)
            _act &= (map_coordinates(_Ms, [_fy, _fx], order=1, mode='nearest') < _zr) & (_mg > 0.05)
            if not _act.any():
                break
            _st = np.where(_act, 4.0, 0.0) / np.maximum(_mg, 1e-9)
            _fx += _st * _vx / cell; _fy += _st * _vy / cell; _tr += np.where(_act, 4.0, 0.0)
        _nzg = ruido_valor(np.random.default_rng(seed + 61), nyg, nxg, cell, 55.0)
        _nf = np.zeros((nyg, nxg)); _nf[_selg] = map_coordinates(_nzg, [_fy, _fx], order=1, mode='nearest')
        _trg = np.zeros((nyg, nxg)); _trg[_selg] = _tr
        _gyn, _gxn = np.gradient(_nf, cell)
        _dln = np.abs(_nf) / np.maximum(np.hypot(_gxn, _gyn), 1e-6)
        _gul = np.clip(1.0 - _dln / 16.0, 0.0, 1.0) ** 2 * np.clip((_trg - 20.0) / 100.0, 0.0, 1.0) * _selg
    _dg = _wf * np.clip((M - 40.0) / 50.0, 0.0, 1.0) * 9.0 * _gul
    M = M - _dg
    # limitador al 85 % SOLO en las paredes de las vaguadas (+2 celdas): uno global tambien rebajaba el ruido ridged de las
    # cumbres en cascada (hasta 60 m en la cima del Monte Porto Corsa)
    M, _ = limitar_pendiente_mascara(M, cell, 0.85, binary_dilation(_dg > 0.05, iterations=2))
    checks['barrancos_celdas_gt_3m'] = int((_dg > 3.0).sum())
    checks['limitador_iteraciones'] = int(n_it_lim)
    checks['limitador_rebaje_max'] = round(rebaje_lim, 1)
    checks['pendiente_max_M_limitado'] = round(float(_pendiente(M, cell).max()), 2)
    dbg('M_limitado', M)

    # --- costa como campo continuo (gaussiana sigma 12 m) ---
    coast = gaussian_filter(es_mar.astype(float).reshape(nyg, nxg), 12.0 / cell)
    coastF = np.clip((coast.ravel() - 0.35) / 0.3, 0.0, 1.0)      # 0 tierra, 1 mar
    # nunca mar en tierra protegida... salvo la GARGANTA bajo el viaducto: el
    # tablero sale del acantilado y vuela sobre el agua aunque la montana del
    # casino 'proteja' esa tierra (antes se anulaba y el tablero volaba sobre
    # una zanja de tierra con paredes verticales a 15 m del eje)
    garganta = (d_bri <= 60.0) & bridge_flag[i_all] & ~estribo
    prot_mar = protegido & (coastF > 0.5) & ~garganta
    if prot_mar.any():
        # tope 0.49 (no 0): la orilla sigue siendo continua donde el limite de la
        # proteccion cruza la costa (con 0 quedaba un escalon de una celda)
        coastF[protegido & ~garganta] = np.minimum(coastF[protegido & ~garganta], 0.49)
    checks['protegido_bajo_mar_antes'] = int(prot_mar.sum())
    # v1 (revision A-09/H3): distancia al mar con precision de SUBCELDA: coastF interpolada en una rejilla x4 (nodos
    # originales incluidos), EDT a 1 m y vuelta a los nodos. Antes la EDT de la mascara binaria crecia en escalera de
    # 4 m y, con pendientes de costa del 300 %, cada escalon era un diente de 12 m en los acantilados
    _jj, _ii = np.mgrid[0:4 * (nyg - 1) + 1, 0:4 * (nxg - 1) + 1]
    # v2 (revision J2-02, probado): la EDT no cuenta como mar el nucleo forzado bajo la roca del penon (r < 1.05, fuera de la
    # bahia y de la Loews): justo fuera del contorno dist_mar valia 4-12 m y la regla de costa tallaba una garganta de 50-75 m
    # entre el penon y el promontorio. coastF, tierra y es_mar no cambian
    _cfd = coastF.copy()
    if el_casino is not None:
        _cfd[(r_cas < 1.05) & ~en_bahia & (d_loews > R_LOEWS_CONG[1])] = 0.0
    _cf4 = map_coordinates(_cfd.reshape(nyg, nxg), [_jj / 4.0, _ii / 4.0], order=1, mode='nearest')
    dist_mar = (distance_transform_edt(_cf4 < 0.5)[::4, ::4] * (cell / 4.0)).ravel()
    del _jj, _ii, _cf4
    # pendiente maxima hacia el mar: 60 % en costa baja; ACANTILADOS donde el
    # macizo natural llega alto a la orilla (promontorio del casino: 220 %),
    # junto al viaducto (300 %) y bajo el acantilado del tunel (120 %)
    pend = 0.60 + 2.40 * np.clip((200.0 - d_bri) / 120.0, 0.0, 1.0)
    # v1 (revision F-07): el termino del viaducto (radio 200 m) llegaba a la costa de la bahia bajo bajada_ladera (puente
    # bajo a 87-114 m): paredes de 25 m al 230-300 %. A > 60 m del viaducto la costa se queda en el 130 % como mucho;
    # no a < 350 m del penon (bajar alli la costa del canal abria fosos detras de casino_mar: revision I4)
    # v2 (revision J2-04/H2-3, probado): el corte DURO (d_bri = 60, dc_cas = 350) hacia saltar pend de 3.0 a 1.3 entre celdas
    # vecinas: falla en dientes de sierra al N del viaducto (28 pares > 15 m) y pared de 30-45 m en x ~373. Fundido doble
    _wb = np.clip((d_bri - BRI_FUNDIDO[0]) / BRI_FUNDIDO[1], 0.0, 1.0)
    if el_casino is not None:
        _wb = _wb * np.clip((dc_cas - 350.0) / CAS_FUNDIDO, 0.0, 1.0)
    pend = pend * (1.0 - _wb) + np.minimum(pend, 1.3) * _wb
    M_reg = gaussian_filter(M, 25.0 / cell).ravel()      # cota 'regional' (sin barrancos)
    # v3 (revision F-07): el termino del macizo (hasta 2.2 donde M_reg > 100) volvia a subir la pendiente POR ENCIMA del tope
    # de F-07 (1.3): la costa de la bahia seguia al 150-320 %. Lejos del viaducto (_wb) ese termino se acota a 1.5
    _pm = 0.60 + 1.60 * np.clip((M_reg - 50.0) / 70.0, 0.0, 1.0)
    _pm = _pm * (1.0 - _wb) + np.minimum(_pm, 1.5) * _wb
    pend = np.maximum(pend, _pm)
    i_tun = (s_land[i_land] >= 230.0) & (s_land[i_land] <= 640.0)
    pend = np.maximum(pend, np.where(i_tun & (d_land < 160.0), 1.2, 0.0))
    # en el solar del penon del casino la regla de costa no actua (la roca ES el acantilado)
    # v1 (revision G4/G10): solo dentro del contorno (r < 1.05); antes en todo r < 2.2 y el macizo caia al mar en una celda
    # (paredes de 57-97 m en la garganta del viaducto y al NE del penon)
    pend = np.where(casino_zona & ((r_cas < 1.05) | (d_loews <= R_LOEWS_INTACTA)), 50.0, pend)
    # v2 (revision I-R2-02/J2-05/F2-08 (a)-(c)): lejos de la pista (peso _lej: 0 a < 60 m de la pista y del viaducto y a
    # < 350 m del penon, 1 a > 100 m) la costa deja de ser un plano de pendiente constante sobre una orilla recta: pendiente
    # modulada x0.7..x1.1 con ruido ridged de 90/45 m (cabos y calas), distancia al mar con ruido de 25 m (+-5 m, nulo en la
    # orilla) y coronacion redondeada (minimo suave con la meseta, k = 5 m). La pista y su corredor no cambian ni 0.01 m
    _lej = np.clip((d_all - 60.0) / 40.0, 0.0, 1.0) * (d_bri >= 60.0)
    if el_casino is not None:
        _lej = _lej * np.clip((dc_cas - 350.0) / 60.0, 0.0, 1.0)
    # v3 (revision J1/I4/H2): esa modulacion valia 0 a < 60 m de CUALQUIER pista y a < 350 m del penon, justo donde estan los
    # acantilados que se ven (bajo la recta 30-31, bahia frente al viaducto, gancho S, canal del viaducto): planos lisos de
    # 20-100 m con la arista recta. Peso _acant: 0 a < 25 m del borde del asfalto (1 a 45 m), a < 20 m del viaducto, a
    # < R_LOEWS_INTACTA de la Loews, en el penon y sus alrededores (r < 1.9: el entorno que lee roca_casino, cala de la bajada
    # incluida), en la huella del McLaren (+25 m) y en la recta de meta/puerto (s < 300, > L-300);
    # ahi _lej >= 0.8 * _acant. Ademas (abajo) pie de derrubios y repisas
    _sg_all = i_all * paso
    _acant = (np.clip((d_land - half_c - 25.0) / 20.0, 0.0, 1.0) * np.clip((d_bri - 20.0) / 10.0, 0.0, 1.0)
              * np.clip((d_loews - R_LOEWS_INTACTA) / 20.0, 0.0, 1.0)
              * np.clip((_sg_all - 300.0) / 40.0, 0.0, 1.0) * np.clip((L - 300.0 - _sg_all) / 40.0, 0.0, 1.0))
    if el_casino is not None:
        _acant = _acant * np.clip((r_cas - 1.9) / 0.3, 0.0, 1.0)
    _acant = _acant * _w_mcl
    _lej = np.maximum(_lej, 0.8 * _acant)
    _rc = ruido_ridged(np.random.default_rng(seed + 23), nyg, nxg, cell, octavas=((90.0, 1.0), (45.0, 0.5))).ravel()
    _nd = ruido_valor(np.random.default_rng(seed + 29), nyg, nxg, cell, 25.0).ravel()
    pend_c = pend * (1.0 + _lej * (0.4 * _rc - 0.3))
    dist_c = np.maximum(dist_mar + _lej * 5.0 * _nd * np.clip(dist_mar / 8.0, 0.0, 1.0), 0.0)
    z_reg = 1.0 + dist_c * pend_c
    # v3 (revision J1 (3)): PIE DE DERRUBIOS: los primeros 6 m desde la orilla al 35 % y despues la cara (solo baja)
    _zpie = 1.0 + 0.35 * np.minimum(dist_c, 6.0) + np.maximum(dist_c - 6.0, 0.0) * pend_c
    z_reg = z_reg * (1.0 - _acant) + np.minimum(z_reg, _zpie) * _acant
    # v3 (revision J1 (2)): REPISAS de estrato en las caras > 120 %: la pendiente oscila 0.4x..1.6x con periodo de 11 m de
    # cota (cornisa / banco), continua y solo bajando (hasta 2.1 m)
    _wrp = _acant * np.clip((pend_c - 1.2) / 0.3, 0.0, 1.0) * np.clip((z_reg - 3.0) / 3.0, 0.0, 1.0)
    z_reg = z_reg - _wrp * 1.05 * (1.0 + np.sin(2.0 * np.pi * z_reg / 11.0))
    # v3 (revision H2 (2)): peso de la banda del canal del viaducto (coronacion por minimo suave, abajo)
    _wcr = _wcan * np.clip((120.0 - d_bri) / 20.0, 0.0, 1.0) * (1.0 - _lej)
    dbg('pend_c', pend_c); dbg('dist_c', dist_c); dbg('acant', _acant); dbg('z_reg', z_reg)
    _smin = -5.0 * np.logaddexp(-M.ravel() / 5.0, -z_reg / 5.0)
    z_land = np.minimum(M.ravel(), z_reg) * (1.0 - _lej) + np.minimum(_smin, M.ravel()) * _lej
    # v3 (revision H2 (2)/H3): en la banda del canal del viaducto (d_bri < 120, fundido 20 m) la coronacion de la muralla era
    # el pliegue vivo min(M, z_reg) de una cara al 300 %: arista recta que la rejilla de 4 m (canal oblicuo, rumbo 159
    # grados) muestreaba en almenas de 4-8 m. Ahi minimo SUAVE con k = 10 m (el redondeo abarca ~2 celdas en planta en una cara
    # al 300 %; solo baja: como mucho 6.9 m en la arista)
    _smin_c = -10.0 * np.logaddexp(-M.ravel() / 10.0, -z_reg / 10.0)
    z_land = z_land * (1.0 - _wcr) + np.minimum(np.minimum(_smin_c, M.ravel()), z_land) * _wcr
    # v2 (revision J2-06, probado): donde actua el fundido J1 (costa N/NE en ladera) el tope de costa no hace falta y su codo
    # (pend 0.6 bajo M_reg 50) dejaba un escalon horizontal a ~50 m (banda gris) en la ladera N
    z_land = np.where(_wf.ravel() > 0.5, M.ravel(), z_land)
    acantilado = z_reg < M.ravel() - 0.5      # donde manda la regla de costa
    if el_casino is not None:
        # tope del penon: <= CASINO_Z_LADERA en el contorno, +80 % hacia fuera (la cumbre del
        # promontorio queda a > 100 m de la entrada) y -400 % hacia dentro (bajo la roca)
        d_fuera = np.maximum(r_cas - 1.0, 0.0) * dc_cas / np.maximum(r_cas, 1e-3)
        d_dentro = np.maximum(1.0 - r_cas, 0.0) * dc_cas / np.maximum(r_cas, 1e-3)
        cap_cas = np.where(r_cas >= 1.0, CASINO_Z_LADERA + PEND_NATURAL_MAX * d_fuera,
                           CASINO_Z_LADERA - CASINO_PEND_INT * d_dentro)
        z_land = np.where(casino_zona, np.minimum(z_land, cap_cas), z_land)
        acantilado = acantilado | (casino_zona & (r_cas < 1.0))
    dbg('z_land', z_land)

    # --- reglas de pista: corredor + desmonte (1.15) / terraplen (0.55) ---
    # PROPIO ramal: la muestra mas cercana (techo Zp-0.5 en el corredor, luego
    # +0.4+(d-6)*1.15; suelo Zp-0.6-(d-6)*0.55). Las muestras de atras del mismo
    # ramal NO cuentan (en una subida del 14 % hundian el corredor 1.5-3 m).
    # OTROS ramales (la pista vuelve sobre si misma a < 180 m): minimo de techos
    # y maximo de suelos -> manda el ramal mas bajo, sin escalones en los ejes
    # mediales. 'Mismo ramal' = a <= 40 m por la pista y sin plegarse (la
    # distancia en linea recta es >= 70 % de la distancia por la pista). En la
    # rotonda Loews los dos ramales estan a 12.8 m (16 m de pista) y 2 m de cota:
    # tratarlos como 'otro' dejaba el ramal alto en el aire (-3 m bajo su borde);
    # como 'mismo', cada asfalto se apoya en su cota y entre ambos queda un banco.
    R_REG = 180.0
    g_near = idx_land[i_land]
    dedge0 = d_land - half_land[i_land]
    z0 = Z_land[i_land]
    # v2 (revision B2-05/D2-11/A-r2-12): techo CONTINUO (C1). Antes z0-0.5 hasta 6 m y z0+0.4+(d-6)*1.15 despues: un salto
    # de 0.9 m mas un quiebro en d = 6 que, muestreado con celdas de 4 m en diagonal, hacia el pie del desmonte en diente
    # de sierra (1.0-1.5 m) y la muesca de s 1662. Ahora llano a z0-0.5 hasta 4.5 m y acuerdo parabolico de T m hasta la
    # pendiente 1.15 (solo BAJA el terreno: la cara retrocede 1.15*(T/2-0.72) m)
    _lat0 = (gpts[:, 0] - X[g_near]) * nx[g_near] + (gpts[:, 1] - Y[g_near]) * ny[g_near]
    _sg0 = g_near * paso
    # curvatura con signo de la pista (> 0 = gira a la izquierda; antes se calculaba abajo, para la isla de las horquillas)
    _tx = ny; _ty = -nx
    _hd = np.unwrap(np.arctan2(_ty, _tx))
    _kap = gaussian_filter1d(np.gradient(_hd) / paso, 2.0, mode='wrap')
    # --- F1 (bloque 1.1): TIERRA TALLADA. Por MUESTRA de la tierra (s en TIERRA_TALLADA_S, fundido 30 m): lado ALTO = el lado
    # donde el terreno natural (z_land, antes de las reglas de pista) es mas alto a TIERRA_LADO_SONDA m; si la diferencia es
    # < 3 m, el interior de la curva (signo de la curvatura suavizada 10 m) y si no hay curva, 0. Se suaviza a lo largo de s
    # (16 m) para que el lado no salte entre muestras. w_lado in [-1, 1] (+1 = el lado alto es el +1). La CAIDA del lado bajo
    # solo donde el natural a 50 m de ese lado no sube (pie del macizo en la postal de la cima: ahi no se excava nada)
    _s_all = np.arange(N) * paso
    _w_st = (np.clip((_s_all - TIERRA_TALLADA_S[0]) / 30.0, 0.0, 1.0) * np.clip((TIERRA_TALLADA_S[1] - _s_all) / 30.0, 0.0, 1.0)
             * _dirt_s)
    _zl2 = z_land.reshape(nyg, nxg)

    def _zl_en(off_lat):
        return map_coordinates(_zl2, [(Y + ny * off_lat - gy0) / cell, (X + nx * off_lat - gx0) / cell], order=1, mode='nearest')
    _zl_p = 0.5 * (_zl_en(Wd / 2.0 + TIERRA_LADO_SONDA) + _zl_en(Wd / 2.0 + TIERRA_LADO_SONDA + 20.0))
    _zl_m = 0.5 * (_zl_en(-(Wd / 2.0 + TIERRA_LADO_SONDA)) + _zl_en(-(Wd / 2.0 + TIERRA_LADO_SONDA + 20.0)))
    _dz_lado = _zl_p - _zl_m
    _kap_s = gaussian_filter1d(_kap, 5.0, mode='wrap')
    _lado_raw = np.where(np.abs(_dz_lado) >= 3.0, np.sign(_dz_lado), np.where(np.abs(_kap_s) > 1.0 / 80.0, np.sign(_kap_s), 0.0))
    # (suavizado de 10 m: en un zigzag el lado alto cambia en CADA curva (cada 60-150 m) y el cambio debe caer en el apex,
    # donde el interior de la curva es el lado alto de las dos ramas; con 40 m se apagaban legs enteros)
    w_lado = np.clip(2.0 * gaussian_filter1d(_lado_raw * _w_st, 5.0, mode='wrap'), -1.0, 1.0) * _w_st
    _zl_p50 = _zl_en(Wd / 2.0 + 50.0); _zl_m50 = _zl_en(-(Wd / 2.0 + 50.0))
    _zl_bajo = np.where(w_lado >= 0.0, _zl_m50, _zl_p50)                       # natural a 50 m del lado BAJO
    # altura del lomo por muestra = lo que SUBE el natural a 60-80 m en el lado alto (tope TIERRA_PARED_H): el lomo acerca
    # la ladera a la pista (corte), nunca levanta un dique de 14 m sobre terreno llano (s 2250: 'levee' artificial)
    _zl_alto = np.where(w_lado >= 0.0, _zl_p, _zl_m)
    _h_lomo = np.clip(gaussian_filter1d(_zl_alto - Z, 5.0, mode='wrap'), 0.0, TIERRA_PARED_H)
    _caida_ok = gaussian_filter1d(np.clip((Z + 6.0 - _zl_bajo) / 10.0, 0.0, 1.0), 4.0, mode='wrap')
    # F1 r3: CAIDA LIBRE (ver cabecera, TIERRA_CAIDA_LIBRE_*): el punto de medida de la caida (25 m del borde, lado bajo) no
    # puede caer en la zona de pared de OTRA rama (|ds| > TIERRA_OTRA_RAMA_DS) ni a < 12 m de su asfalto. Por muestra, suavizado
    # 6 m a lo largo de s; entra en _caida_ok (vaguada, voto y w_out_c)
    _sgb = -np.sign(w_lado)
    _px25 = X + nx * _sgb * (Wd / 2.0 + 25.0); _py25 = Y + ny * _sgb * (Wd / 2.0 + 25.0)
    _zl25 = map_coordinates(_zl2, [(_py25 - gy0) / cell, (_px25 - gx0) / cell], order=1, mode='nearest')
    _dk25, _ik25 = tree_land.query(np.column_stack([_px25, _py25]), k=12)
    _gk25 = idx_land[_ik25]
    _ds25 = np.abs(_gk25 - np.arange(N)[:, None]); _ds25 = np.minimum(_ds25, N - _ds25) * paso
    _otra25 = _ds25 > TIERRA_OTRA_RAMA_DS
    _dedge25 = np.where(_otra25, _dk25 - Wd[_gk25] / 2.0, 1e9)
    _lat25 = (_px25[:, None] - X[_gk25]) * nx[_gk25] + (_py25[:, None] - Y[_gk25]) * ny[_gk25]
    _alto25 = np.sign(_lat25) * w_lado[_gk25] > 0.3
    _pared25 = _alto25 & ((_zl25[:, None] >= Z[_gk25] + TIERRA_PARED_REAL) | (_h_lomo[_gk25] >= 7.5))
    _bloq25 = (((_dedge25 <= TIERRA_CAIDA_LIBRE_D) & _pared25) | (_dedge25 <= TIERRA_CAIDA_LIBRE_ASF)).any(1) & (np.abs(w_lado) > 0.3)
    _caida_libre = 1.0 - np.clip(gaussian_filter1d(_bloq25.astype(float), 2.0, mode='wrap') * 1.5, 0.0, 1.0)
    checks['tierra_caida_bloqueada_muestras'] = int((_bloq25 & (_w_st > 0.5)).sum())
    _caida_ok = _caida_ok * _caida_libre
    # r3: junto a los apex de horquilla (R < 15 m, +- TIERRA_BLOQ_APEX) el lado bajo bloqueado conserva el cono de 1.15: la isla
    # de la cima que mira la postal 56 no debe crecer (con 2.0 el horizonte de terreno subia de la fila 25 a la 18 del cuadro)
    _horq_apex = maximum_filter1d((np.abs(_kap) > 1.0 / 15.0).astype(float), size=int(2 * TIERRA_BLOQ_APEX / paso) + 1, mode='wrap')
    _bloq_pend = (1.0 - _caida_libre) * (1.0 - _horq_apex)
    checks['tierra_tallada_muestras'] = int((np.abs(w_lado) > 0.5).sum())
    checks['tierra_tallada_lado_mas1_pct'] = round(100.0 * float((w_lado[_w_st > 0.5] > 0.0).mean()), 1) if (_w_st > 0.5).any() else 0.0
    # por CELDA (muestra mas cercana g_near): peso del lado alto (w_in) y del lado bajo (w_out, sin el factor 'otra rama', abajo)
    _lsg = np.sign(_lat0)
    # islas de horquilla: interior de las curvas cerradas (R < 25 m): sin vaguada y (r2) sin lomo minimo
    _isla_t = (1.0 / np.maximum(np.abs(_kap[g_near]), 1e-6) < 25.0) & (np.sign(_lat0) == np.sign(_kap[g_near]))
    w_in_c = np.clip(w_lado[g_near] * _lsg, 0.0, 1.0)
    w_out_c = np.clip(-w_lado[g_near] * _lsg, 0.0, 1.0) * _caida_ok[g_near]
    # desmonte C1 con pendiente por celda: TIERRA_PEND_INT (63 grados) en el lado alto de la tierra, 1.15 en el resto
    # F1 r3: ... y tambien en el lado bajo cuya caida esta BLOQUEADA por la pared de otra rama (isla entre B y C de la cima:
    # las dos caras de la isla son cortes; con 1.15 el techo de B recortaba la pared natural de C a +0..+7 a 25 m)
    _w_bloq_c = np.clip(-w_lado[g_near] * _lsg, 0.0, 1.0) * _bloq_pend[g_near]
    # (r3: a < TIERRA_BLOQ_APEX de un apex de horquilla tambien el lado alto se queda en 1.15: la isla de la cima no crece)
    pend_c1 = 1.15 + (TIERRA_PEND_INT - 1.15) * np.maximum(w_in_c * (1.0 - _horq_apex[g_near]), _w_bloq_c)
    techo = techo_desmonte_c1(z0, dedge0, pend=pend_c1)
    # v1 (revision B8): en el lado +1 de s 320-402 (entre la pista y el pedestal del McLaren) el macizo dejaba una loma conica
    # de +7.6 m: explanada a cota de pista (+1 m) hasta 30 m y despues al 25 % (el pedestal cubre lo que quede debajo)
    _cono = (_sg0 >= 320.0) & (_sg0 <= 402.0) & (_lat0 > 0.0) & (dedge0 < 45.0) & (dedge0 >= 6.0)
    techo = np.where(_cono, np.minimum(techo, z0 + 1.0 + np.maximum(0.0, dedge0 - 30.0) * 0.25), techo)
    # terraplen 0.55... salvo en la garganta del viaducto, donde la pista sale de
    # un ACANTILADO (300 %): con el 0.55 el borde de la garganta era vertical
    s_fl = 0.55 + 2.45 * np.clip((80.0 - d_bri) / 40.0, 0.0, 1.0)      # 0.55 lejos, 3.0 a < 40 m del viaducto
    # ... y 400 % dentro del contorno del penon del casino (la rotonda esta en su borde O: el
    # terreno cae bajo la roca hasta el mar)
    s_fl = np.where(casino_zona & (r_cas < 1.05), np.maximum(s_fl, CASINO_PEND_INT), s_fl)
    # F1 (bloque 1.1): en el lado bajo de la tierra el terraplen puede caer hasta TIERRA_SFL_EXT tras una berma llana de
    # TIERRA_BERMA m (antes 6 m al 0.55); el acuerdo con el 0.55 del resto va con w_out_c
    s_fl = np.maximum(s_fl, 0.55 + (TIERRA_SFL_EXT - 0.55) * w_out_c)
    d_llano_fl = 6.0 + (TIERRA_BERMA - 6.0) * w_out_c
    suelo = z0 - 0.6 - np.maximum(dedge0 - d_llano_fl, 0.0) * s_fl
    # LADERA del lado alto (lomo: sube a TIERRA_PARED_PEND hasta +TIERRA_PARED_H, meseta de 14 m y vuelve al natural al 50 %)
    # y CAIDA del lado bajo (vaguada: baja a TIERRA_CAIDA_PEND tras la berma hasta -TIERRA_CAIDA_H, 10 m de fondo y vuelve al
    # 50 %): 'tiendas' CONTINUAS en la distancia al borde de CADA muestra; en el bucle de ramales se toma el maximo del
    # levantamiento y del rebaje sobre TODAS las muestras a < R_REG (no solo la mas cercana: sin crestas finas ni escalones
    # donde cambia la muestra mas cercana). Altura con ruido de 30 m (+-20 %): ni el lomo ni la vaguada son rectos
    # (r2: 0.9-1.2, antes 0.8-1.2: con 0.8 el lomo de 10 m daba 7.5 m de pared y la caida -7.7: el KPI de 25 m se perdia por ruido)
    _nh_tierra = 1.05 + 0.15 * ruido_valor(np.random.default_rng(seed + 97), nyg, nxg, cell, 30.0).ravel()
    # F1 r2: serpenteo de la cresta del lomo (+- TIERRA_LOMO_SERP m, ruido de 50 m) y lomo minimo por muestra (ver cabecera)
    _ns_tierra = TIERRA_LOMO_SUBIDA + TIERRA_LOMO_SERP * ruido_valor(np.random.default_rng(seed + 101), nyg, nxg, cell, 50.0).ravel()
    _horq = maximum_filter1d((np.abs(_kap) > 1.0 / 15.0).astype(float), size=int(2 * TIERRA_SIN_MIN_APEX / paso) + 1, mode='wrap') > 0.5
    _h_lomo_min = np.where(_horq, _h_lomo, _h_lomo + np.maximum(TIERRA_PARED_H_MIN - _h_lomo, 0.0) * np.clip((_h_lomo - 3.0) / 3.0, 0.0, 1.0))
    _d2_out = TIERRA_BERMA + TIERRA_CAIDA_H / TIERRA_CAIDA_PEND + 10.0

    def _tienda_in(d, h, L=TIERRA_LOMO_SUBIDA):
        """F1 r2: LOMA redondeada: sube h en L m desde 4.5 m del borde (1-(1-u)^2.5: arranque empinado, cresta a pendiente 0),
        cresta de TIERRA_LOMO_CRESTA m y bajada al 50 % con acuerdo parabolico de TIERRA_LOMO_T m. h y L pueden ser arrays."""
        u = np.clip((d - 4.5) / L, 0.0, 1.0)
        sube = h * (1.0 - (1.0 - u) ** 2.5)
        x = np.maximum(d - (4.5 + L + TIERRA_LOMO_CRESTA), 0.0)
        T = TIERRA_LOMO_T
        return sube - 0.5 * np.where(x < T, x * x / (2.0 * T), x - 0.5 * T)

    def _tienda_out(d, nh=1.0):
        """F1 r2: VAGUADA redondeada: tras la berma baja a TIERRA_CAIDA_PEND con acuerdo parabolico de TIERRA_CAIDA_T m hasta
        TIERRA_CAIDA_H x nh (fondo = minimo suave de TIERRA_CAIDA_K m) y vuelve al natural al 50 %."""
        x = np.maximum(d - TIERRA_BERMA, 0.0)
        T = TIERRA_CAIDA_T
        q = TIERRA_CAIDA_PEND * np.where(x < T, x * x / (2.0 * T), x - 0.5 * T)
        K = TIERRA_CAIDA_K
        fondo = -K * np.logaddexp(-q / K, -(TIERRA_CAIDA_H * nh) / K)
        return fondo - 0.5 * np.maximum(d - _d2_out, 0.0)
    raise_max = np.zeros(ncel); lower_max = np.zeros(ncel); voto_in = np.zeros(ncel); voto_out = np.zeros(ncel)
    raise_min = np.zeros(ncel)                # r2: levantamiento con el lomo minimo (se aplica donde no hay vaguada vecina)
    raise_who = np.full(ncel, -1, dtype=int); lower_who = np.full(ncel, -1, dtype=int)   # r3: muestra que manda en cada celda (QA)
    raise_core = np.zeros(ncel)               # r3: lomo dentro de su ZONA DE PARED (dedge <= TIERRA_LOMO_CORE): solo este apaga vaguadas
    raise_dedge = np.full(ncel, 1e9)          # r3: distancia al borde de la muestra que manda en el lomo
    lower_ceil = np.full(ncel, 1e9)           # r3: techo de la vaguada mas exigente (w_out > 0.5) en la celda
    d_otro_edge = np.full(ncel, 1e9)          # distancia al borde del asfalto de OTRO ramal (se rellena en el bucle)
    near = np.where(d_land < R_REG)[0]
    n_dobles = 0
    for a in range(0, len(near), 10000):
        sub = near[a:a + 10000]
        dk, ik = tree_land.query(gpts[sub], k=192, distance_upper_bound=R_REG)
        valid = np.isfinite(dk)
        ikc = np.where(valid, ik, 0)
        gj = idx_land[ikc]
        g0 = g_near[sub][:, None]
        dl = np.abs(gj - g0)
        dl = np.minimum(dl, N - dl) * paso
        dij = np.hypot(X[gj] - X[g0], Y[gj] - Y[g0])
        mismo = (dl <= 40.0) & (dij >= MISMO_RAMAL * dl)
        otro = valid & ~mismo
        zj = Z_land[ikc]
        dedge = np.where(valid, dk, 1e6) - half_land[ikc]
        # v2 (B2-05/D2-11): mismo techo continuo... salvo junto al asfalto PROPIO (dedge0 < 4 m, fundido hasta 10 m), donde
        # el techo de OTRO ramal sigue siendo el de v1: con el C1 la rama baja de una horquilla (cara 4-5 m mas baja) cortaba
        # el apoyo del borde de la rama alta (terreno 1.3-1.5 m bajo el borde interior en s 2346-2350)
        _w_own = np.clip((dedge0[sub][:, None] - 4.0) / 6.0, 0.0, 1.0)
        # F1 r3: el cono (techo) de cada muestra j es TIERRA_PEND_INT en su lado alto y en su lado bajo bloqueado (caida no
        # libre), como el techo propio (pend_c1): la isla de la cima entre B y C queda acotada por el cono de B a 1.15 (49
        # grados) y la pared natural de C (+13 a 25 m) se recortaba a +0..+5 en s 1880-1900
        _pend_j = 1.15
        if (_w_st > 0.0).any():
            _lat_j = (gpts[sub, 0][:, None] - X[gj]) * nx[gj] + (gpts[sub, 1][:, None] - Y[gj]) * ny[gj]
            _sg_j = np.sign(_lat_j)
            _wl_j = w_lado[gj]
            _pend_j = 1.15 + (TIERRA_PEND_INT - 1.15) * np.clip(np.maximum(_wl_j * _sg_j * (1.0 - _horq_apex[gj]), -_wl_j * _sg_j * _bloq_pend[gj]), 0.0, 1.0)
        ceil_j = (np.where(dedge < 6.0, zj - 0.5, zj + 0.4 + (dedge - 6.0) * _pend_j) * (1.0 - _w_own)
                  + techo_desmonte_c1(zj, dedge, pend=_pend_j) * _w_own)
        floor_j = zj - 0.6 - np.maximum(dedge - 6.0, 0.0) * s_fl[sub][:, None]
        _c_otro = np.where(otro, ceil_j, 1e9).min(1)
        # v2 (revision E2-07 (1)): a > 8 m del borde (de las dos ramas), donde OTRO ramal limita la celda, minimo SUAVE
        # (k = 1.5 m; solo baja, como mucho 1.04 m) en vez del duro: la espina entre dos desmontes paralelos ya no es una
        # cresta recta de dos planos (dique)
        _k_sm = 1.5
        _sm = -_k_sm * np.logaddexp(-techo[sub] / _k_sm, -_c_otro / _k_sm)
        _suave = (dedge0[sub] > 8.0) & (_c_otro < 1e8) & (np.where(otro, dedge, 1e9).min(1) > 8.0)
        techo[sub] = np.where(_suave, np.minimum(techo[sub], _sm), np.minimum(techo[sub], _c_otro))
        suelo[sub] = np.maximum(suelo[sub], np.where(otro, floor_j, -1e9).max(1))
        _d_ot = np.where(otro, dedge, 1e9).min(1)
        d_otro_edge[sub] = _d_ot
        n_dobles += int(((dedge0[sub] < 4.0) & (techo[sub] < z0[sub] - 0.8)).sum())
        # F1 (bloque 1.1): TIERRA TALLADA. Para cada muestra j a < R_REG: si la celda esta en su lado ALTO, el lomo
        # floor_in_j (nunca sobre el techo de ningun ramal: se acota abajo); si esta en su lado BAJO, la vaguada ceil_out_j
        # (nunca bajo el suelo de ningun ramal). Peso de cada muestra: lado (w_lado, con el fundido en s), caida solo donde el
        # natural exterior no sube (_caida_ok), y 0 a < TIERRA_OTRA_RAMA[0] m del borde de OTRA rama (islas de horquilla,
        # espina entre ramas paralelas: ahi manda el terreno natural). Se guarda el MAXIMO levantamiento/rebaje por celda
        if (_w_st > 0.0).any():
            # (_lat_j, _sg_j, _wl_j: calculados arriba, antes de ceil_j)
            _d_ot2 = np.where(valid & (dl > TIERRA_OTRA_RAMA_DS), dedge, 1e9).min(1)       # otra rama de verdad (no la propia curva)
            _fac_j = np.where(dl <= TIERRA_OTRA_RAMA_DS, _d_ot2[:, None], dedge0[sub][:, None])
            _fac_j = np.clip((_fac_j - TIERRA_OTRA_RAMA[0]) / (TIERRA_OTRA_RAMA[1] - TIERRA_OTRA_RAMA[0]), 0.0, 1.0) * valid
            # solo las muestras que tienen la celda EN SU NORMAL (desfase a lo largo de la pista |lon| < TIERRA_LON_M): las
            # muestras de una curva 60-90 m atras veian la espina entre las dos ramas paralelas como su 'lado bajo'
            _lon_j = np.abs((gpts[sub, 0][:, None] - X[gj]) * ny[gj] - (gpts[sub, 1][:, None] - Y[gj]) * nx[gj])
            _w_lon_j = np.clip((TIERRA_LON_M - _lon_j) / 8.0, 0.0, 1.0)
            _fac_j = _fac_j * _w_lon_j
            # F1 (bloque 1.1, v2): BANCO DE HORQUILLA. Si la otra rama mas cercana a la celda esta >= TIERRA_BANCO_DZ m MAS ALTA
            # que la muestra j (rama baja de una horquilla o de dos ramas paralelas: C26 s 2300-2360 sobre 2380-2440), la isla
            # entre las dos es una ladera que SUBE de la rama baja a la alta: el lomo de la rama baja no se apaga junto a la
            # rama alta (sigue acotado por el techo/suelo de todos los ramales: el corredor y el hombro de la rama alta no
            # cambian). La vaguada si se apaga (nunca se excava hacia la rama de abajo: _fac_j)
            # rama 'plegada' cerca de la celda: muestras a > 40 m por la pista pero a < 80 % de esa distancia en linea recta
            # (horquilla abierta de la C26: ramas a 55 m en recta por 72 m de pista; una subida recta o una curva de R 50 m
            # no cuentan: > 90 %) y a < 45 m de la celda; la rama ALTA junto a la celda es la mas alta de esas o la propia
            # muestra mas cercana (z0: celdas que ya estan mas cerca de la rama alta)
            # ... y con rumbo OPUESTO al de la muestra mas cercana a la celda (producto de las normales < -0.3: > 107 grados; la
            # propia curva C14 de s 1500-1620, con el mismo rumbo tras el giro, no es una rama plegada y no hace banco)
            _g0s = g_near[sub][:, None]
            _dot_j = nx[gj] * nx[_g0s] + ny[gj] * ny[_g0s]
            _m_ot = valid & (dl > 40.0) & (dij < 0.8 * dl) & (dedge < 45.0) & (_dot_j < -0.3)
            _z_ot_max = np.where(_m_ot, zj, -1e9).max(1)
            # rama ALTA por par (celda, j): la plegada mas alta cerca de la celda o, si j misma es de rumbo opuesto a la muestra
            # mas cercana (la celda ya esta mas cerca de la rama alta), esa muestra mas cercana (z0)
            _z_hi_j = np.maximum(_z_ot_max[:, None], np.where(_dot_j < -0.3, z0[sub][:, None], -1e9))
            # muestra de la rama ALTA (la plegada mas alta o la propia mas cercana) y lado de la celda y de cada muestra j
            # respecto a ella: el banco solo sube las celdas que estan ENTRE la rama baja y la alta (mismo lado que j), nunca
            # las del otro lado de la rama alta (el lomo de la rama baja cruzaba la rama alta y le tapaba su caida exterior)
            _kh = np.where(_z_ot_max > z0[sub], gj[np.arange(len(sub)), np.argmax(np.where(_m_ot, zj, -1e9), axis=1)], g_near[sub])
            _lat_c_h = (gpts[sub, 0] - X[_kh]) * nx[_kh] + (gpts[sub, 1] - Y[_kh]) * ny[_kh]
            _lat_j_h = (X[gj] - X[_kh][:, None]) * nx[_kh][:, None] + (Y[gj] - Y[_kh][:, None]) * ny[_kh][:, None]
            _mismo_lado_h = (np.sign(_lat_c_h)[:, None] == np.sign(_lat_j_h)) | (np.abs(_lat_j_h) < 1.0)
            _banco_j = (_m_ot.any(1)[:, None] | (_dot_j < -0.3)) & (_z_hi_j > zj + TIERRA_BANCO_DZ) & _mismo_lado_h
            _z_hi = _z_hi_j
            _fac_in_j = np.where(_banco_j, valid * _w_lon_j, _fac_j)
            _nh = _nh_tierra[sub][:, None]
            # altura del lomo NATURAL (lo que sube el natural a 60-80 m) y, r2, con el LOMO MINIMO (TIERRA_PARED_H_MIN) donde hay
            # ladera, salvo en las islas de horquilla (_isla_t) y junto a los apex (_horq). Se calculan los dos levantamientos: el
            # minimo solo se aplica (tras el bucle) donde no mata una vaguada vecina, y solo cerca de la pista (cresta a < 35 m;
            # a > 45 m la cresta baja a la altura natural: la cola del lomo es la de r1)
            _h_nat = _h_lomo[gj] * _nh
            _h_min = np.where(_isla_t[sub][:, None], _h_lomo[gj], _h_lomo_min[gj]) * _nh
            # (en el banco la 'ladera' que mide _h_lomo a 60-80 m cae ya al otro lado de la rama alta: la altura del lomo es
            # la de la rama alta sobre la baja, tope TIERRA_PARED_H)
            _h_banco = np.minimum(_z_hi - zj, TIERRA_PARED_H) * _nh
            _h_nat = np.where(_banco_j, np.maximum(_h_nat, _h_banco), _h_nat)
            _h_min = np.where(_banco_j, np.maximum(_h_min, _h_banco), _h_min)
            # lomo solo si hay ladera NATURAL. F1 r3: (3, 5) -> TIERRA_LOMO_H_NAT (6, 8): un lomo de 3-6 m no da pared (KPI >= 8)
            # y su cola (hasta 70 m) mataba la vaguada de la rama de enfrente (s 2070-2100: lomo de 14 m del collado de
            # s 1640-1660 sobre su lado bajo; 1660 +1)
            _w_lad_j = np.clip((_h_nat - TIERRA_LOMO_H_NAT[0]) / (TIERRA_LOMO_H_NAT[1] - TIERRA_LOMO_H_NAT[0]), 0.0, 1.0)
            _w_in_j = np.clip(_wl_j * _sg_j, 0.0, 1.0) * _fac_in_j * _w_lad_j
            _w_out_j = np.clip(-_wl_j * _sg_j, 0.0, 1.0) * _caida_ok[gj] * _fac_j
            # altura efectiva del lomo: el natural a 60-80 m (+ TIERRA_LOMO_EXTRA donde hay ladera), tope TIERRA_PARED_H
            _h_e = np.minimum(_h_nat + TIERRA_LOMO_EXTRA * _w_lad_j, TIERRA_PARED_H)
            _h_e2 = np.minimum(_h_min + TIERRA_LOMO_EXTRA * _w_lad_j, TIERRA_PARED_H)
            _h_e2 = _h_e + (_h_e2 - _h_e) * np.clip((45.0 - dedge) / 10.0, 0.0, 1.0)
            _L_j = _ns_tierra[sub][:, None]
            _floor_in_j = zj - 0.5 + _tienda_in(dedge, _h_e, _L_j)
            _floor_in_j2 = zj - 0.5 + _tienda_in(dedge, _h_e2, _L_j)
            _ceil_out_j = zj - 0.6 - _tienda_out(dedge, _nh)
            # el levantamiento/rebaje es una MODIFICACION del natural junto a la pista, no una cota absoluta: tope de
            # TIERRA_PARED_H / TIERRA_CAIDA_H (x ruido) hasta 50 m del borde y 0 a 85/95 m (la cola de la tienda no
            # levanta un valle ni rebaja una loma a 60-90 m de la muestra). r2: y 0 en el corredor (< 4.5 m del borde, fundido
            # a 8 m): el corredor va de z0-0.6 (suelo) a z0-0.5 (techo) y el lomo/vaguada lo movia 0.10 m
            # (la distancia es la de la celda al borde de asfalto MAS CERCANO, propio u otro ramal: el lomo de la rama de al lado
            # (banco de la C26) levantaba 0.10 m el corredor de la rama baja a traves de su propio 'dedge' de 30 m)
            _w_corr = np.clip((np.minimum(dedge0[sub], _d_ot)[:, None] - TIERRA_SIN_CORREDOR[0])
                              / (TIERRA_SIN_CORREDOR[1] - TIERRA_SIN_CORREDOR[0]), 0.0, 1.0)
            _w_lejos = np.clip((85.0 - dedge) / 35.0, 0.0, 1.0) * _w_corr
            _cap_out = TIERRA_CAIDA_H * _nh * np.clip((95.0 - dedge) / 45.0, 0.0, 1.0) * _w_corr
            _zl_s = z_land[sub][:, None]
            _rt = _w_in_j * np.minimum(np.maximum(_floor_in_j - _zl_s, 0.0), _h_e * _w_lejos)
            raise_max[sub] = _rt.max(1)
            _am = _rt.argmax(1); _ar = np.arange(len(sub))
            raise_who[sub] = np.where(raise_max[sub] > 0.0, gj[_ar, _am], -1)   # r3: muestra del lomo (QA)
            raise_dedge[sub] = np.where(raise_max[sub] > 0.0, dedge[_ar, _am], 1e9)
            # (y todo el lomo si la celda esta en un HUECO de < TIERRA_LOMO_GAP entre su rama y otra: isla de horquilla D/E, pares
            # a < 60 m: ahi sigue 'gana el lomo' entero, sin hoyo en medio de la isla)
            raise_core[sub] = (_rt * ((dedge <= TIERRA_LOMO_CORE) | (dedge + _d_ot2[:, None] < TIERRA_LOMO_GAP))).max(1)
            lower_ceil[sub] = np.where(_w_out_j > 0.5, _ceil_out_j, 1e9).min(1)
            raise_min[sub] = (_w_in_j * np.minimum(np.maximum(_floor_in_j2 - _zl_s, 0.0), _h_e2 * _w_lejos)).max(1)
            _lt = _w_out_j * np.minimum(np.maximum(_zl_s - _ceil_out_j, 0.0), _cap_out)
            lower_max[sub] = _lt.max(1)
            lower_who[sub] = np.where(lower_max[sub] > 0.0, gj[np.arange(len(sub)), _lt.argmax(1)], -1)   # r3: muestra de la vaguada (QA)
            # VOTO por proximidad (continuo) solo para apagar la vaguada donde una muestra MAS CERCANA ve la celda como su
            # lado alto (la espina entre la subida y la bajada del lazo: las muestras del apex de la cima, 45 m al N, la
            # veian como su lado bajo y la rebajaban 16 m); el lado alto cuenta aunque no haya ladera para el lomo
            _kp = 1.0 / (dedge + 6.0) ** 2
            voto_in[sub] = (np.clip(_wl_j * _sg_j, 0.0, 1.0) * _fac_j * _kp).sum(1); voto_out[sub] = (_w_out_j * _kp).sum(1)
    tierra = coastF < 0.5
    z_gen = np.where(tierra, np.minimum(np.maximum(z_land, suelo), techo), z_land)
    # F1 (bloque 1.1): el terreno natural + lomo - vaguada, acotado por el suelo (terraplen de todos los ramales) y el techo
    # (corredor/desmonte de todos los ramales): el corredor de la pista y el de las otras ramas no cambian
    # Nada en el HINTERLAND de los sectores de terrazas: celdas en el lado del sector, cuya pista mas cercana es la del
    # sector, a < 21*n + 30 m del borde (fundido 15 m): es el perfil de la QA de fosos (o_fin + 40) y la cara tras la ultima
    # terraza (con la vaguada de la curva C13-C14 asomaban fosos de 4 m detras de pueblo_alto_ladera). fac_valle no sirve:
    # apaga por distancia a las muestras del sector sin mirar el lado ni la pista mas cercana (dejaba a 0 la cresta de s 2200)
    fac_sect = np.ones(ncel)
    _AT_s = float(spec_urb.get('ancho_terraza', 21.0))
    for sc in spec_urb.get('sectores', []):
        _jj = idx_land[(s_land >= float(sc['s0'])) & (s_land <= float(sc['s1']))]
        if len(_jj) == 0 or int(sc['n_terrazas']) < 1:
            continue
        _ds, _ks = cKDTree(np.column_stack([X[_jj], Y[_jj]])).query(gpts, distance_upper_bound=300.0)
        _ok = np.isfinite(_ds); _gk = _jj[np.where(_ok, _ks, 0)]
        _lado_c = np.where((gpts[:, 0] - X[_gk]) * nx[_gk] + (gpts[:, 1] - Y[_gk]) * ny[_gk] > 0, 1, -1)
        _o_c = np.where(_ok, _ds, 1e9) - Wd[_gk] / 2.0
        _zona = _ok & (_lado_c == int(sc['lado'])) & (d_land >= np.where(_ok, _ds, 0.0) - 2.0)
        # (margen 45 m: el perfil de la QA de fosos llega a o_fin + 40 y con 30 m el lomo de s 1540-1600 asomaba a o_fin + 32-40
        # tras pueblo_alto_ladera y dejaba 'agua atrapada' de 1.6 m en s 1494)
        fac_sect = np.minimum(fac_sect, np.where(_zona, np.clip((_o_c - (_AT_s * int(sc['n_terrazas']) + 45.0)) / 15.0, 0.0, 1.0), 1.0))
    # r2: ... ni en la BANDA de los perfiles de la QA de fosos (o_fin-3 .. o_fin+40 por la normal de CADA muestra del sector, en
    # su lado; a < 3 m de esos puntos, fundido a 9 m). fac_sect no protege los puntos del perfil cuya pista mas cercana es la
    # de una muestra de fuera del sector (la curva C13-C14 tras pueblo_alto_ladera: la cresta del lomo de s 1540-1600, ahora
    # redondeada y mas corta, asomaba a o_fin+15-20 y dejaba 2.0 m de agua atrapada en s 1494)
    _pts_b = []
    for sc in spec_urb.get('sectores', []):
        _nt = int(sc['n_terrazas'])
        _jj = idx_land[(s_land >= float(sc['s0'])) & (s_land <= float(sc['s1']))]
        if _nt < 1 or len(_jj) == 0:
            continue
        _offs = _AT_s * _nt + np.arange(-3.0, 40.01, 2.0)
        _off2 = int(sc['lado']) * (Wd[_jj][:, None] / 2.0 + _offs[None, :])
        _pts_b.append(np.column_stack([(X[_jj][:, None] + nx[_jj][:, None] * _off2).ravel(),
                                       (Y[_jj][:, None] + ny[_jj][:, None] * _off2).ravel()]))
    if _pts_b:
        _d_b, _ = cKDTree(np.concatenate(_pts_b)).query(gpts, distance_upper_bound=12.0)
        fac_sect = np.minimum(fac_sect, np.clip((np.where(np.isfinite(_d_b), _d_b, 1e9) - 3.0) / 6.0, 0.0, 1.0))
    # ... ni vaguada en el interior de las curvas cerradas (R < 25 m: islas de horquilla, _isla_t de arriba; el lomo si,
    # acotado por el techo de la otra rama)
    raise_max = raise_max * fac_sect; raise_min = raise_min * fac_sect; lower_max = np.where(_isla_t, 0.0, lower_max * fac_sect)
    # donde chocan el lomo de la rama de abajo y la vaguada de la de arriba (ramas a 35-50 m: s 1600/2200, 2100/2140) gana
    # el LOMO (la de abajo esta tallada en la ladera: pared; la de arriba se queda con un hombro llano en vez de la
    # caida; un voto por proximidad dejaba una zanja en V entre las dos)
    _V = (voto_in - voto_out) / np.maximum(voto_in + voto_out, 1e-12)
    # F1 r3: solo el lomo DENTRO de su zona de pared (raise_core) apaga la vaguada; la cola (raise_max - raise_core) no, y donde
    # una rama de enfrente excava (lower_ceil), la cola se recorta al techo de esa vaguada con fundido de TIERRA_LOMO_COLA_T m
    # a partir de TIERRA_LOMO_CORE (ver cabecera): la rama alta de un par a >= 60 m recupera su caida sin escalon
    raise_core = raise_core * fac_sect
    lower_max = lower_max * (1.0 - np.clip(raise_core / 3.0, 0.0, 1.0)) * np.clip(1.0 - 2.0 * np.maximum(_V, 0.0), 0.0, 1.0)
    _t_cola = np.clip((raise_dedge - TIERRA_LOMO_CORE) / TIERRA_LOMO_COLA_T, 0.0, 1.0) * (lower_ceil < 1e8) * (lower_max > 0.0)
    _raise_cap = np.maximum(lower_ceil - z_land, 0.0)
    raise_max = raise_max * (1.0 - _t_cola) + np.minimum(raise_max, _raise_cap) * _t_cola
    checks['tierra_tallada_celdas_cola_recortada'] = int((tierra & (_t_cola > 0.5) & (_raise_cap < raise_max + 0.5)).sum())
    # r2: el LOMO MINIMO solo donde no hay vaguada (de otra rama) en la celda: el lomo natural de 1600-1620 subido a 10 m
    # apagaba la caida de 1670-1690 (interior comun de la curva del collado)
    _add_min = np.maximum(raise_min - raise_max, 0.0) * (1.0 - np.clip(lower_max / 2.0, 0.0, 1.0))
    raise_max = raise_max + _add_min
    checks['tierra_tallada_celdas_lomo_minimo'] = int((tierra & (_add_min > 0.5)).sum())
    _z_tall = np.minimum(np.maximum(z_land + raise_max - lower_max, suelo), techo)
    checks['tierra_tallada_celdas_ladera'] = int((tierra & (raise_max > 0.5)).sum())
    checks['tierra_tallada_celdas_caida'] = int((tierra & (lower_max > 0.5)).sum())
    checks['tierra_tallada_ladera_max_m'] = round(float(raise_max[tierra].max()), 1) if tierra.any() else 0.0
    checks['tierra_tallada_caida_max_m'] = round(float(lower_max[tierra].max()), 1) if tierra.any() else 0.0
    z_gen = np.where(tierra, _z_tall, z_land)
    dbg('techo', techo); dbg('suelo', suelo); dbg('z_gen', z_gen)

    # --- TERRAZAS DEL PUEBLO desde urbanismo_spec.json (RONDA 15b) ---
    # Perfil transversal: perfil_terrazas() (bordillo -0.4 hasta u = 1.0, rampa a +-0.5
    # en 1.5, bandas LLANAS, rampa del muro en los 2.5 m ANTES de 21(k+1) y la terraza
    # k+1 llana desde 21(k+1) exactamente). Cota = Zb + perfil(o), con
    #   o  = distancia a la polilinea del sector - w/2 (CONTINUA en toda la rejilla) y
    #   Zb = MEZCLA ponderada de Z (suavizada 30 m a lo largo de s) sobre las muestras
    #        del sector: peso exp(-((d_j - d_min)/h)^2), h = H_MEZCLA*o (minimo 1.5 m).
    # Junto a la pista manda la muestra mas cercana (la calle de servicio queda a su
    # cota aunque otra rama del sector pase a 20 m: fondo de las horquillas del casino) y
    # al alejarse la mezcla se ensancha: en el eje medial de las curvas cerradas (esquina
    # interior de la C9/C10 del pueblo con 3 terrazas) la cota ya NO salta entre celdas
    # vecinas (antes: asignacion a la muestra mas cercana -> escalones de 4-8 m).
    # Dentro de s0..s1 las bandas son llanas (w_s = 1); el fundido de 30 m queda FUERA del
    # sector (s0-30..s0, s1..s1+30) con sbar = s medio ponderado; las muestras se
    # extienden EXT_S mas alla de s0/s1 solo para que la mezcla no se sesgue en los
    # extremos. Donde otro ramal de la pista esta mas cerca que la del sector, su
    # corredor/terraplen acotan la terraza (fuera de su corredor, muro al 300 %).
    AT = float(spec_urb.get('ancho_terraza', 21.0))
    H1 = float(spec_urb.get('altura_terraza_1', 0.5))
    HT = float(spec_urb.get('altura_terraza', 6.0))
    TM = float(spec_urb.get('transicion_muro', 3.0))
    BORD = float(spec_urb.get('bordillo_hasta', 1.5))
    TR = 2.5                                   # rampa del muro: u_local 18.5..21 (contrato 15b)
    LF = 30.0                                  # fundido en s fuera del sector
    EXT_S = 130.0                              # muestras extra mas alla de s0/s1 (solo para la mezcla: >= LF + K/2 muestras)
    SIG_S = 7.5 / paso                         # filtro gaussiano de Z a lo largo de s (+-2 sigma = 30 m)
    H_MEZCLA = 0.25                            # anchura de la mezcla = H_MEZCLA * o (minimo 1.5 m; 0.5 sesgaba 2-3 m las terrazas 1-2)
    K_MEZCLA = 96
    U_FLAT = float(spec_urb.get('fachada_desde', 7.0))   # entre dos ramas enfrentadas del sector (horquilla) cada una conserva llano hasta aqui
    # RONDA 15c: cierre morfologico del terreno natural (ventana 84 m) para rellenar los fosos
    # detras de la ultima terraza (el terraplen bajaba al 55 % hasta un valle y la montana
    # volvia a subir: foso en V de 2-14 m detras de los patios)
    z_land_cl = grey_closing(z_land.reshape(nyg, nxg), size=(21, 21)).ravel()
    z_grid = z_gen.copy()
    terr_mix = np.zeros(ncel, bool)            # celda en el talud entre dos ramas enfrentadas (fuera del mapa de costuras)
    n_foso_rell = 0
    n_terr = 0
    terr_mask = np.zeros(ncel, bool)
    terr_val = np.full(ncel, np.nan)           # cota llana asignada (conflictos entre sectores)
    terr_k = np.full(ncel, -1, dtype=int)      # indice de terraza de cada celda llana
    terr_rampa = np.zeros(ncel, bool)          # celda en una rampa (bordillo o muro): fuera del mapa de costuras
    terr_sec = np.full(ncel, -1, dtype=int)    # indice del sector de cada celda llana
    terr_otro = np.zeros(ncel, bool)           # celda del sector acotada por otro ramal de la pista
    terr_g = np.full(ncel, -1, dtype=int)      # muestra del sector mas cercana a cada celda llana (mapa de costuras)
    n_conf = 0
    suelo_terr = np.full(ncel, -1e9)          # piso de las terrazas (y su terraplen) para la caja del pit
    R_TERR = 180.0
    # F1 (bloque 1.2): anchura de la berma tras la ultima terraza por celda (ruido de 60 m entre BERMA_TERRAZA[0] y [1])
    _berma_c = BERMA_TERRAZA[0] + (BERMA_TERRAZA[1] - BERMA_TERRAZA[0]) * 0.5 * (
        1.0 + ruido_valor(np.random.default_rng(seed + 71), nyg, nxg, cell, 60.0).ravel())
    sectores = [sc for sc in spec_urb.get('sectores', []) if int(sc['n_terrazas']) >= 1]
    for i_sc, sc in enumerate(sectores):
        s0, s1, lado, nt = float(sc['s0']), float(sc['s1']), int(sc['lado']), int(sc['n_terrazas'])
        sg = sentido_terrazas(sc)
        xp, fp, hs = perfil_terrazas(nt, sg, AT, H1, HT, BORD, TR)
        o_fin = AT * nt
        js_in = idx_land[(s_land >= s0) & (s_land <= s1)]
        if len(js_in) == 0:
            continue
        # muestras DEL SECTOR (js_in): cota, offset o, lado y 'otro ramal'. Muestras EXTENDIDAS
        # (js_ext, hasta EXT_S mas alla de s0/s1 mientras la pista no se pliegue): SOLO para
        # sbar, el s medio ponderado que gobierna el fundido (con la ventana truncada en s0/s1
        # el fundido no arrancaba y la terraza seguia 40 m mas alla del sector con un escalon
        # de 13 m al acabar). La Z NO se mezcla con la extension: en el arranque de
        # pueblo_subida la recta del tunel (plegada, 8 m mas baja) tiraba 8 m de la terraza 1;
        # esa rama es 'otro ramal' y manda su corredor, como en los sectores sin extension.
        js_ext = extension_sector(idx_land, s_land, X, Y, s0, s1, EXT_S, nx, ny)
        s_ext = js_ext * paso
        Zs_in = gaussian_filter1d(Z[js_in], SIG_S, mode='nearest')
        tree_s = cKDTree(np.column_stack([X[js_in], Y[js_in]]))
        tree_e = cKDTree(np.column_stack([X[js_ext], Y[js_ext]]))
        d_s, k_s = tree_s.query(gpts, distance_upper_bound=R_TERR + LF)
        ok = np.isfinite(d_s)
        gj = js_in[np.where(ok, k_s, 0)]
        vx = gpts[:, 0] - X[gj]; vy = gpts[:, 1] - Y[gj]
        lat = vx * nx[gj] + vy * ny[gj]
        lado_j = np.where(lat > 0, 1, -1)
        o_all = d_s - Wd[gj] / 2                   # distancia al borde del asfalto del sector (continua)
        en_s = ok & (lado_j == lado) & tierra & (d_bri > 30.0) & (o_all >= 0.0) & (o_all < R_TERR)
        if not en_s.any():
            continue
        sel = np.where(en_s)[0]
        o = o_all[sel]
        terr_otro[sel] |= d_land[sel] < d_s[sel] - 2.0        # otro ramal de la pista mas cerca que el del sector
        # mezcla ponderada de Z (muestras del sector) y de s (muestras extendidas)
        Zb = np.zeros(len(sel)); sbar = np.zeros(len(sel)); tmix = np.zeros(len(sel))
        for a in range(0, len(sel), 8000):
            cj = sel[a:a + 8000]
            oc = o[a:a + 8000]
            h = np.maximum(H_MEZCLA * oc, 1.5)[:, None]
            zb_c, tt_c = mezcla_cota(gpts[cj, 0], gpts[cj, 1], d_s[cj], gj[cj], oc, X, Y, nx, ny, Wd, js_in, Zs_in, tree_s,
                                     lado, N, paso, AT, U_FLAT, H_MEZCLA, K_MEZCLA, R_TERR + LF)
            Zb[a:a + 8000] = zb_c
            tmix[a:a + 8000] = tt_c
            dk, ik = tree_e.query(gpts[cj], k=K_MEZCLA, distance_upper_bound=R_TERR + LF)
            valid = np.isfinite(dk)
            ikc = np.where(valid, ik, 0)
            dmin = np.where(valid, dk, 1e9).min(1)[:, None]
            w = np.where(valid, np.exp(-((np.where(valid, dk, 0.0) - dmin) / h) ** 2), 0.0)
            sbar[a:a + 8000] = (w * s_ext[ikc]).sum(1) / np.maximum(w.sum(1), 1e-9)
        fuera = np.maximum(np.maximum(s0 - sbar, sbar - s1), 0.0)
        w_s = np.clip(1.0 - fuera / LF, 0.0, 1.0)
        # celdas ya LLANAS de un sector anterior: intocables (antes el fundido de pueblo_alto,
        # 160 m mas alla y acotado por 'otro ramal', levantaba 3-4 m la terraza 0 de pueblo_subida)
        ajena = terr_mask[sel] & (w_s < 0.999)
        n_conf += int(ajena.sum())
        keep = (w_s > 0.0) & ~ajena
        sel = sel[keep]; o = o[keep]; Zb = Zb[keep]; w_s = w_s[keep]; tmix = tmix[keep]
        gjs = gj[sel]
        zt_flat = Zb + np.interp(o, xp, fp)
        z_ult = Zb + hs[-1]
        # desmonte detras de la ultima terraza: 1.15 (49 grados) salvo en el espolon del coche
        # (PEND_DESMONTE_COCHE, 63 grados: el macizo debe subir detras del McLaren)
        p_desm = 1.15 + (PEND_DESMONTE_COCHE - 1.15) * w_coche[sel]
        # v3 (revision C-02): en los sectores de pueblo, fuera del espolon del coche, la cara va en bancales (techo_tras_terraza)
        # (r2: con _w_mcl_f1, +30 m de la huella del McLaren, para que la berma de F1 no mueva nada a < 25 m del coche)
        w_tope = (1.0 - w_coche[sel]) * _w_mcl_f1[sel] * (1.0 if str(sc['id']).startswith('pueblo') else 0.0)
        # F1 (bloque 1.2): berma de 15-25 m entre el patio y la cara (solo pueblo_*, fuera del espolon del coche y del
        # McLaren: w_tope); bancales tambien en el espolon del coche si BANCOS_EN_COCHE (solo bajan <= 2*BANCO_A = 3.3 m)
        berma_sel = _berma_c[sel] * w_tope
        # (r2: en el espolon del coche con _w_mcl_f1, +30 m de la huella: el encaje del McLaren a < 25 m queda en 0.000)
        w_banco_sel = ((1.0 if str(sc['id']).startswith('pueblo') else 0.0)
                       * (_w_mcl_f1[sel] if BANCOS_EN_COCHE else _w_mcl[sel] * (1.0 - w_coche[sel])))
        techo_t = z_ult + 0.4 + techo_tras_terraza(o - o_fin - TM / 2, p_desm, w_banco_sel, berma=berma_sel)
        suelo_t = z_ult - 0.6 - np.maximum(o - o_fin, 0.0) * s_fl[sel]     # 0.55 (hasta 3.0 en la garganta)
        # RONDA 15c: RELLENO del foso. Donde el terreno natural cerrado (84 m) vuelve a estar
        # a < 6 m bajo la ultima terraza, el suelo detras del patio no baja de la cota de la
        # terraza (sube: +30 % hacia la montana; baja: llano) en vez de caer al 55 % a un valle
        # y volver a subir. Fundido en o_fin+80..+120.
        rel = np.maximum(o - o_fin, 0.0)
        z_cl = z_land_cl[sel]
        nivel = z_ult - 0.6 + (0.3 if sg > 0 else 0.0) * rel
        relleno = np.minimum(nivel, np.maximum(z_cl, z_ult - 0.6))
        w_fill = np.clip((o_fin + 120.0 - o) / 40.0, 0.0, 1.0)
        fill_ok = (o >= o_fin) & (z_cl >= z_ult - 6.0) & (relleno > z_land[sel])
        z_use = np.where(fill_ok, z_land[sel] + (relleno - z_land[sel]) * w_fill, z_land[sel])
        n_foso_rell += int((fill_ok & (relleno - z_land[sel] > 1.5) & (w_s > 0.999)).sum())
        # F1 (bloque 1.1): la base fuera de las bandas es el natural (+ relleno) MAS el lomo y MENOS la vaguada de la tierra
        # tallada (raise_max/lower_max ya van a 0 en el hinterland de cada sector por fac_sect): a 180 m de pueblo_alto_mar
        # (s 1500) la isla de la C26 se recalculaba desde z_land y perdia el banco de horquilla. La vaguada no toca el relleno
        z_use = np.maximum(z_use, z_land[sel] + raise_max[sel]) - np.where(fill_ok, 0.0, lower_max[sel])
        # detras de la ultima terraza, donde el sector tiene varias ramas (la
        # tecnica dobla alrededor del espolon), la cara de desmonte/terraplen es
        # el minimo/maximo contra las OTRAS ramas del sector que tienen la celda
        # en su lado (como la regla general): sin escalones en el eje medial
        lejos = np.where(o >= o_fin)[0]
        for a in range(0, len(lejos), 10000):
            lj = lejos[a:a + 10000]
            cj = sel[lj]
            dk, ik = tree_s.query(gpts[cj], k=96, distance_upper_bound=R_TERR)
            valid = np.isfinite(dk)
            gk = js_in[np.where(valid, ik, 0)]
            g0 = gjs[lj][:, None]
            dl = np.abs(gk - g0)
            dl = np.minimum(dl, N - dl) * paso
            dij = np.hypot(X[gk] - X[g0], Y[gk] - Y[g0])
            otra = valid & ~((dl <= 40.0) & (dij >= MISMO_RAMAL * dl))
            vxk = gpts[cj, 0][:, None] - X[gk]; vyk = gpts[cj, 1][:, None] - Y[gk]
            otra &= np.where(vxk * nx[gk] + vyk * ny[gk] > 0, 1, -1) == lado
            ok_ = np.where(valid, dk, 1e6) - Wd[gk] / 2
            face_k = Z[gk] + hs[-1] + 0.4 + techo_tras_terraza(ok_ - o_fin - TM / 2, p_desm[lj][:, None], w_banco_sel[lj][:, None],
                                                                berma=berma_sel[lj][:, None])
            floor_k = Z[gk] + hs[-1] - 0.6 - np.maximum(ok_ - o_fin, 0.0) * s_fl[cj][:, None]
            techo_t[lj] = np.minimum(techo_t[lj], np.where(otra, face_k, 1e9).min(1))
            suelo_t[lj] = np.maximum(suelo_t[lj], np.where(otra, floor_k, -1e9).max(1))
        zt_fuera = np.minimum(np.maximum(z_use, suelo_t), techo_t)
        # v3 (revision C-02): en la coronacion del corte (donde el techo encuentra la ladera natural) minimo SUAVE (k = 4 m, solo
        # baja, como mucho 2.8 m): sin la arista recta de la 'meseta de hierba' sobre el tajo
        _zc_t = np.maximum(z_use, suelo_t)
        _sm_t = np.maximum(-4.0 * np.logaddexp(-techo_t / 4.0, -_zc_t / 4.0), suelo_t)
        zt_fuera = zt_fuera * (1.0 - w_tope) + np.minimum(zt_fuera, _sm_t) * w_tope
        z_t = np.where(o < o_fin, zt_flat, zt_fuera)
        # otro ramal mas cerca que la pista del sector: su corredor y su terraplen
        # mandan; fuera de su corredor, en vez de su desmonte (49 grados) la
        # terraza puede sostenerse con un MURO de contencion (300 %)
        otro = d_land[sel] < d_s[sel] - 2.0
        i0s = i_land[sel]
        de0 = d_land[sel] - half_land[i0s]
        techo_muro = np.where(de0 < 6.0, techo[sel], Z_land[i0s] - 0.5 + (de0 - 6.0) * 3.0)
        z_t = np.where(otro, np.minimum(np.maximum(z_t, suelo[sel]), techo_muro), z_t)
        z_grid[sel] = z_grid[sel] * (1.0 - w_s) + z_t * w_s
        # piso que la caja del pit no puede rebajar: las bandas llanas y, detras de
        # la ultima terraza, una cara a 49 grados (1.15) en vez del terraplen de 0.55
        piso_t = np.where(o < o_fin, zt_flat, z_ult - 0.6 - np.maximum(o - o_fin, 0.0) * 1.15)
        piso_t = np.where(otro, np.minimum(np.maximum(piso_t, suelo[sel]), techo_muro), piso_t)
        suelo_terr[sel] = np.maximum(suelo_terr[sel], suelo[sel] * (1.0 - w_s) + piso_t * w_s)
        if _dbg_idx:
            pos = {int(c): k for k, c in enumerate(sel)}
            for c in _dbg_idx:
                if c in pos:
                    k = pos[c]
                    print('    [dbg] terraza %s celda %d: s_j %.0f o %.1f w_s %.2f Zb %.2f z_t %.2f otro %s (d_land %.1f d_s %.1f)'
                          % (sc['id'], c, gjs[k] * paso, o[k], w_s[k], Zb[k], z_t[k], bool(otro[k]), d_land[c], d_s[c]))
        flat = (o < o_fin) & ~otro & (w_s > 0.999)
        terr_mix[sel[flat & (tmix > 0.02)]] = True
        prev = terr_val[sel[flat]]
        n_conf += int((np.isfinite(prev) & (np.abs(prev - zt_flat[flat]) > 0.5)).sum())
        terr_val[sel[flat]] = zt_flat[flat]
        n_terr += int(flat.sum())
        terr_mask[sel[flat]] = True
        terr_sec[sel[flat]] = i_sc
        terr_g[sel[flat]] = gjs[flat]
        kk = np.clip(np.floor(o / AT).astype(int), 0, nt - 1)
        terr_k[sel[flat]] = kk[flat]
        ol = o - AT * kk                           # u local dentro de la banda
        rampa = (o < BORD + 0.5) | (ol > AT - TR - 0.5) | ((kk > 0) & (ol < 0.5)) | (o > o_fin - 0.5)
        terr_rampa[sel[flat]] = rampa[flat]
    checks['terrazas_celdas'] = n_terr
    checks['terrazas_conflicto_sectores'] = n_conf
    dbg('z_terrazas', z_grid)
    # --- RONDA 15c: FOSOS detras de la ultima terraza: RELLENO (terraplen) hasta el nivel de 'agua
    # atrapada' del perfil normal de cada muestra (o_fin .. o_fin+HF, cortado en la zona de otro
    # ramal / otra rama / mar / terrazas de otro sector): donde el terreno baja y vuelve a subir, el
    # suelo queda a la cota de la terraza - 0.6 (o a la del rebote si es menor) hasta encontrar el
    # terreno natural; donde solo baja (talud 0.55 hacia el mar) no se toca. Nunca por encima del
    # techo de la pista (corredor/desmonte de cualquier ramal). Despues actuan viaducto, pit y mirador.
    HF = 44.0
    zg_tmp = z_grid.reshape(nyg, nxg)
    z_pre_foso = z_grid.copy()
    no_llana = tierra & ~terr_mask
    PEND_TERRAPLEN = 0.55
    reg_foso = []                              # por sector: (js_in, celdas candidatas, indice de muestra mas cercana)
    for i_sc, sc in enumerate(sectores):
        s0, s1, lado, nt = float(sc['s0']), float(sc['s1']), int(sc['lado']), int(sc['n_terrazas'])
        js_in = idx_land[(s_land >= s0) & (s_land <= s1)]
        if len(js_in) < 3:
            reg_foso.append(None); continue
        o_fin = AT * nt
        d_f, k_f = cKDTree(np.column_stack([X[js_in], Y[js_in]])).query(gpts, distance_upper_bound=o_fin + HF + 20.0)
        cand = np.where(np.isfinite(d_f) & no_llana)[0]
        reg_foso.append((js_in, cand, k_f[cand]))
    for it_f in range(16):                    # 12 pasadas relleno + terraplen y 4 finales solo de relleno (residuos del talud)
        target = np.full(ncel, -1e9)
        for i_sc, sc in enumerate(sectores):
            if reg_foso[i_sc] is None:
                continue
            js_in, cand, kf = reg_foso[i_sc]
            lado, nt = int(sc['lado']), int(sc['n_terrazas'])
            o_fin = AT * nt
            oo, zz, val = perfiles_tras_terraza(zg_tmp, gx0, gy0, cell, X, Y, Wd, nx, ny, js_in, lado, o_fin, HF,
                                                tree_land, idx_land, N, paso, half_land, tierra, terr_mask, terr_sec, terr_g, i_sc)
            rell, _ = nivel_agua(zz, val, zz[:, 0] - 0.6)
            # (a) cada celda toma el MAXIMO nivel de los rayos de su muestra mas cercana y de las 2 vecinas a
            # cada lado que pasan a <= 3 m de ella (relleno sin escalones laterales entre rayos)
            for dk_ in (-2, -1, 0, 1, 2):
                kk_ = np.clip(kf + dk_, 0, len(js_in) - 1); g = js_in[kk_]
                vx = gpts[cand, 0] - X[g]; vy = gpts[cand, 1] - Y[g]
                o_c = lado * (vx * nx[g] + vy * ny[g]) - Wd[g] / 2.0
                lon = np.abs(vx * ny[g] - vy * nx[g])
                fj = (o_c - oo[0]) / (oo[1] - oo[0]); j0 = np.floor(fj).astype(int); fr = fj - j0
                j0c = np.clip(j0, 0, len(oo) - 2)
                ok = (lon <= 3.0) & (o_c >= o_fin) & (j0 >= 0) & (j0 < len(oo) - 1) & val[kk_, j0c] & val[kk_, j0c + 1]
                lv = rell[kk_, j0c] * (1.0 - fr) + rell[kk_, j0c + 1] * fr
                np.maximum.at(target, cand[ok], lv[ok])
            # (b) cada punto del rayo que hay que levantar sube la celda en la que cae (rayos que cruzan
            # celdas cuya muestra mas cercana es de otra rama: horquillas del casino)
            m = val & (oo[None, :] >= o_fin) & (rell > zz + 0.02)
            if m.any():
                rr, jj = np.where(m)
                d = Wd[js_in[rr]] / 2.0 + oo[jj]
                qx = X[js_in[rr]] + lado * nx[js_in[rr]] * d; qy = Y[js_in[rr]] + lado * ny[js_in[rr]] * d
                ci = (np.clip(np.round((qy - gy0) / cell).astype(int), 0, nyg - 1) * nxg
                      + np.clip(np.round((qx - gx0) / cell).astype(int), 0, nxg - 1))
                np.maximum.at(target, ci, rell[rr, jj])
        dbg('foso_tgt%d' % it_f, target)
        sube_m = no_llana & (target > z_grid + 0.02)
        if not sube_m.any():
            break
        c_in = np.where(sube_m)[0]
        con_talud = it_f < 12
        z_grid[c_in] = np.minimum(target[c_in], np.maximum(z_grid[c_in], techo[c_in]))
        # (c) TERRAPLEN: los bordes del relleno bajan al 55 % hasta el terreno natural (sin paredes laterales
        # donde un rayo se rellena y el vecino no); solo se rebajan celdas levantadas, nunca bajo su cota previa
        lev = (z_grid - z_pre_foso).reshape(nyg, nxg) > 0.05
        if con_talud and lev.any():
            zc = z_grid.reshape(nyg, nxg).copy(); zp = z_pre_foso.reshape(nyg, nxg)
            d4 = PEND_TERRAPLEN * cell; d8 = d4 * math.sqrt(2.0)
            for _ in range(30):
                zn = zc.copy()
                zn[1:, :] = np.minimum(zn[1:, :], zc[:-1, :] + d4); zn[:-1, :] = np.minimum(zn[:-1, :], zc[1:, :] + d4)
                zn[:, 1:] = np.minimum(zn[:, 1:], zc[:, :-1] + d4); zn[:, :-1] = np.minimum(zn[:, :-1], zc[:, 1:] + d4)
                zn[1:, 1:] = np.minimum(zn[1:, 1:], zc[:-1, :-1] + d8); zn[:-1, :-1] = np.minimum(zn[:-1, :-1], zc[1:, 1:] + d8)
                zn[1:, :-1] = np.minimum(zn[1:, :-1], zc[:-1, 1:] + d8); zn[:-1, 1:] = np.minimum(zn[:-1, 1:], zc[1:, :-1] + d8)
                zn = np.where(lev, np.maximum(zn, zp), zc)
                if float(np.abs(zn - zc).max()) < 0.01:
                    zc = zn; break
                zc = zn
            z_grid[:] = zc.ravel()
        zg_tmp = z_grid.reshape(nyg, nxg)
    sube_ = z_grid - z_pre_foso
    n_foso_cel = int((sube_ > 1.5).sum()); foso_rell_max = float(sube_.max())
    checks['foso_relleno_pasadas'] = it_f + 1
    print('  relleno de fosos: %d pasadas, %d celdas levantadas > 1.5 m (max %.1f m)' % (it_f + 1, n_foso_cel, foso_rell_max))
    checks['foso_relleno_celdas_gt_1p5'] = n_foso_cel
    checks['foso_relleno_max_m'] = round(foso_rell_max, 2)
    dbg('z_fosos', z_grid)

    # --- el terreno no toca el tablero del viaducto donde arranca en tierra ---
    # (a < 15 m del eje: 3 m bajo el tablero; mas lejos sube al 1.15 -> sin
    # paredes verticales en los estribos)
    if tree_bridge is not None:
        techo_b = Z[~no_bridge][i_bri] - 3.0 + np.maximum(d_bri - 15.0, 0.0) * 1.15
        # v2 (revision G2-04, opcion A probada por el revisor): en s 3632-3684 el viaducto iba metido en una zanja de 3 m
        # (laderas +6..+10 m sobre el tablero a w/2+20). Con un fundido de 20 m desde el arranque el terreno baja a 12 m bajo
        # el tablero y la vaguada desagua en la garganta de s 3684: el puente cruza algo. Fuera de la Loews
        _sb = np.where(bridge_flag)[0][i_bri] * paso
        _wv = np.clip((_sb - 3632.0) / 20.0, 0.0, 1.0) * ((_sb >= 3632.0) & (_sb <= 3684.0)) * (d_loews > R_LOEWS_CONG[1])
        techo_v = Z[~no_bridge][i_bri] - (3.0 + 9.0 * _wv) + np.maximum(d_bri - (15.0 - 5.0 * _wv), 0.0) * (1.15 - 0.15 * _wv)
        techo_b = np.where(_wv > 0.0, np.minimum(techo_b, techo_v), techo_b)
        # v1 (revision I1, probado): en los ESTRIBOS el techo solo manda bajo el tablero: donde la pista en tierra esta mas
        # cerca que el puente, sube al 1.15 desde 2 m antes del final del viaducto (el corredor de tierra conserva z0-0.5 y
        # el escalon queda dentro del cuerpo del ultimo tramo; antes zanja de 3 m bajo la pista en s 4936-4952)
        techo_b = techo_b + np.where(estribo, np.maximum(d_bri - d_land + 2.0, 0.0) * 1.15, 0.0)
        z_grid = np.where((d_bri < 120.0) & tierra, np.minimum(z_grid, techo_b), z_grid)
    # --- caja del pit: explanada llana de 28 m y ladera suave (22 %) hasta 100 m ---
    n_terr_pit = 0
    explanada = []
    pit_cut = np.zeros(ncel, bool)             # celdas rebajadas por la caja/corredor del pit (QA de cobertura)
    if pit_pts:
        pxy = np.array([[q['x'], q['y']] for q in pit_pts])
        pz = np.array([q['z'] for q in pit_pts])
        pw = np.array([q['w'] for q in pit_pts])
        dp, ip = cKDTree(pxy).query(gpts)
        # mas alla de los EXTREMOS del pit lane la caja no sigue como un disco:
        # el techo sube con la pendiente de desmonte (1.15) segun lo que la celda
        # sobrepasa el extremo
        sobre_e = []
        for ke, kv in ((0, 1), (len(pxy) - 1, len(pxy) - 2)):
            tdir = pxy[ke] - pxy[kv]; tdir = tdir / max(np.hypot(*tdir), 1e-9)
            s_ext = (gpts[:, 0] - pxy[ke, 0]) * tdir[0] + (gpts[:, 1] - pxy[ke, 1]) * tdir[1]
            sobre_e.append(np.maximum(s_ext - 10.0, 0.0))
        sobre = np.maximum(sobre_e[0], sobre_e[1])
        s_no = sobre_e[1]                       # extremo de SALIDA (s 170, NO, detras del hotel)
        dpe = dp - pw[ip] / 2
        # v1 (revision F-12): la caja no actua en celdas que tienen OTRA calzada entre ellas y el pit lane (la bajada s
        # 2440-2600 pasa a 90-115 m: su pared del 115 % y el terraplen de la carretera hacian una V de 6-11 m paralela a la
        # pista). Solo para calzadas fuera de la recta de meta (s 300..L-300): el puerto y los boxes no cambian
        _g = idx_land[i_land]; _sg = _g * paso
        _lc = np.sign((gpts[:, 0] - X[_g]) * nx[_g] + (gpts[:, 1] - Y[_g]) * ny[_g])
        _lp = np.sign((pxy[ip, 0] - X[_g]) * nx[_g] + (pxy[ip, 1] - Y[_g]) * ny[_g])
        _otra = (d_land < dpe - 10.0) & (_lc != _lp) & (_sg > 300.0) & (_sg < L - 300.0)
        checks['caja_pit_otra_calzada_celdas'] = int((_otra & (dpe < 260.0) & tierra).sum())
        caja = (dpe < 260.0) & tierra & ~_otra
        # F1 (bloque 1.1): la isla de la horquilla C26 (banco de horquilla, a 125-190 m del extremo NE del pit lane) tiene como
        # muestra mas cercana el apex (rumbo O), para la que el pit cae en su mismo lado: _otra no la exime y el techo de la caja
        # (explanada 22 % + 115 %) la rebajaba 5 m. Las celdas con lomo o vaguada de la tierra tallada quedan fuera de la caja
        caja &= (raise_max < 0.5) & (lower_max < 0.5)
        # v1 (revision J4/B10, probado): mas alla del extremo NO las dos rampas del 115 % (alejarse del pit y pasar su
        # extremo) se SUMABAN: pared de cantera del 241 % detras del hotel. Ahora una sola distancia (hypot) con pendiente
        # 1.15 -> 0.80 segun lo que se pasa del extremo; el extremo SE (entrada, junto al viaducto) queda igual que antes
        # v2 (revision A-r2-07): la pared de la caja era un desplazamiento EXACTO de la polilinea del pit lane (empezaba a
        # 100 m fijos con un quiebro 0.22 -> 1.15): tajo gris de bordes rectos detras del hotel. Ahora el pie va a 100-130 m
        # (ruido suave de 60 m; nunca antes de 100 m: el hotel, a 87 m, no cambia) y arranca con un acuerdo parabolico de
        # 15 m; en la coronacion, minimo suave con la ladera (k = 3 m). Solo baja el terreno
        _n01 = 0.5 * (1.0 + ruido_valor(np.random.default_rng(seed + 37), nyg, nxg, cell, 60.0).ravel())
        dpe0 = 100.0 + 30.0 * _n01
        _rr = np.hypot(np.maximum(dpe - dpe0, 0.0), s_no)
        _rr = np.where(_rr < 15.0, _rr * _rr / 30.0, _rr - 7.5)
        techo_p = (pz[ip] - 0.6 + np.clip(dpe - 28.0, 0.0, dpe0 - 28.0) * 0.22
                   + _rr * (1.15 - 0.35 * np.clip(s_no / 20.0, 0.0, 1.0))
                   + sobre_e[0] * 1.15)
        _kp = 3.0
        techo_p = np.where(dpe > dpe0, np.minimum(techo_p, -_kp * np.logaddexp(-techo_p / _kp, -z_grid / _kp)), techo_p)
        # la caja NUNCA baja del corredor/terraplen (0.55) de otra calzada ni del
        # piso de una terraza: SIN fundido (antes un fundido de 110 m dejaba la
        # bajada 3-24 m en el aire y las terrazas de bajada_ladera 24-36 m bajo
        # cota). Donde la bajada esta a < 90 m del pit lane la explanada se
        # estrecha y lo que queda entre ambas es el muro de contencion.
        techo_p = np.maximum(techo_p, np.maximum(suelo, suelo_terr))
        # ... pero el corredor del pit lane es intocable: desde su borde (6 m) el
        # terreno sube como mucho al 300 % (muro de contencion del pit)
        techo_p = np.minimum(techo_p, pz[ip] - 0.6 + np.maximum(dpe - 6.0, 0.0) * 3.0)
        n_terr_pit = int((caja & terr_mask & (z_grid > techo_p + 0.3)).sum())
        pit_cut = caja & (techo_p < z_grid - 0.3)
        dbg('caja_otra', _otra.astype(float)); dbg('caja_dpe', dpe); dbg('caja_s_no', s_no); dbg('caja_techo_p', np.where(caja, techo_p, 1e9))
        z_grid = np.where(caja, np.minimum(z_grid, techo_p), z_grid)
        # v3 (revision B10): la pared de la caja detras del hotel seguia al 137-149 % (ruido de 60 m, arranque parabolico y
        # coronacion suave de v2, sin limitador despues): limitador al 92 % (gradiente <= ~1.0) SOLO en la pared (caja, desde 40 m
        # del pit lane hasta el pie + 80 m, a > 12 m de cualquier asfalto, fuera de terrazas); explanada, muro del pit y corredor fijos
        # (F1 bloque 1.1: tampoco en las celdas de la tierra tallada (lomo/vaguada): la isla de la C26 esta a 130-190 m del
        # extremo NE del pit lane y el limitador al 92 % rebajaba 5 m el banco de horquilla; la pared tras el hotel no cambia)
        _mov_b = (caja & (dpe > 40.0) & (dpe < dpe0 + 80.0) & tierra & (dedge0 > 12.0) & ~terr_mask
                  & (raise_max < 0.5) & (lower_max < 0.5)).reshape(nyg, nxg)
        if _mov_b.any():
            _zb2, _reb_b = limitar_pendiente_mascara(z_grid.reshape(nyg, nxg), cell, 0.92, _mov_b)
            z_grid = _zb2.ravel()
            checks['caja_pit_pared_rebaje_max'] = round(_reb_b, 2)
        # anchura de la explanada llana (z <= pz+0.5) detras del pit lane, cada 10 puntos
        zg_tmp = z_grid.reshape(nyg, nxg)
        for kq in range(0, len(pxy), 10):
            ka, kb = max(kq - 1, 0), min(kq + 1, len(pxy) - 1)
            tdir = pxy[kb] - pxy[ka]; tdir = tdir / max(np.hypot(*tdir), 1e-9)
            nrm = np.array([-tdir[1], tdir[0]])
            if tree_all.query(pxy[kq] + nrm * 20.0)[0] < tree_all.query(pxy[kq] - nrm * 20.0)[0]:
                nrm = -nrm                      # hacia el lado contrario a la pista
            dd = np.arange(2.0, 120.0, 2.0)
            qx = pxy[kq, 0] + nrm[0] * (pw[kq] / 2 + dd); qy = pxy[kq, 1] + nrm[1] * (pw[kq] / 2 + dd)
            zq = map_coordinates(zg_tmp, [(qy - gy0) / cell, (qx - gx0) / cell], order=1, mode='nearest')
            alto = np.where(zq > pz[kq] + 0.5)[0]
            explanada.append((int(kq), float(dd[alto[0]]) if len(alto) else float(dd[-1])))
    checks['terrazas_recortadas_por_pit'] = n_terr_pit
    # v1 (revision I3, probado): LUNGOMARE de la llegada: entre el estribo N del viaducto y el pit lane, lado +1 (mar), el
    # macizo (~11 m tras el tiron a la rasante) quedaba como una cuchilla de 40 x 10 m entre la pista y el agua que tapaba
    # el puerto. Techo = rasante - 0.5 (cota del corredor y de la caja del pit) hasta 40 m del borde y +60 % mas alla.
    # v2 (revision N2-A): ampliado a s 4930-5200 (antes 5030): de s 5040 a 5200, entre las tribunas del mar y el agua, quedaba
    # la cresta original del macizo (+1.4..+3.2 m sobre la pista a 20-30 m) cayendo al 100-160 % hasta el fondo en 6-8 m, con
    # la orilla en dientes de sierra justo donde atraca la marina VIP. Techo = rasante - 0.5 hasta la orilla (mas alla de
    # 40 m ya es mar en todo el tramo) y orilla continua al 67 % (abajo, _lungo). En s 0-140 el terreno ya esta bajo la pista
    LUNGO_S = (4930.0, 5200.0)
    ii_l = idx_land[(s_land >= LUNGO_S[0]) & (s_land <= LUNGO_S[1])]
    _lungo = np.zeros(ncel, bool)
    if len(ii_l):
        d_l, k_l = cKDTree(np.column_stack([X[ii_l], Y[ii_l]])).query(gpts, distance_upper_bound=90.0)
        ok_l = np.isfinite(d_l)
        g_l = ii_l[np.where(ok_l, k_l, 0)]
        lat_l = (gpts[:, 0] - X[g_l]) * nx[g_l] + (gpts[:, 1] - Y[g_l]) * ny[g_l]
        o_l = lat_l - Wd[g_l] / 2.0
        zona_l = ok_l & tierra & (o_l > 0.0) & (d_land >= np.where(ok_l, d_l, 0.0) - 0.5)
        techo_l = Z[g_l] - 0.5 + np.maximum(o_l - 40.0, 0.0) * np.where(g_l * paso <= 5030.0, 0.6, 0.0)
        checks['lungomare_celdas'] = int((zona_l & (z_grid > techo_l + 0.3)).sum())
        z_grid = np.where(zona_l, np.minimum(z_grid, techo_l), z_grid)
        _lungo = ok_l & (o_l > 0.0) & (d_land >= np.where(ok_l, d_l, 0.0) - 0.5) & (g_l * paso >= 5030.0)
    checks['explanada_pit_m'] = explanada
    dbg('z_pit', z_grid)
    # --- miradores: el terreno baja 10 m del lado del MAR a partir de su borde.
    # Se comprueba la geografia: si el lado del spec mira tierra adentro, el
    # banco se OMITE (antes tallaba un rectangulo de 130x160 m en las lomas) ---
    dist_mar_g = dist_mar.reshape(nyg, nxg)
    mir_ok = []
    mir_cut = np.zeros(ncel, bool)
    for (s0m, s1m, sd, an) in miradores:
        qs = np.arange(int(s0m / paso), int(s1m / paso) + 1, 5) % N
        dm = {}
        for sdx in (1, -1):
            vals = []
            for off in (40.0, 80.0, 120.0, 160.0):
                qx = X[qs] + sdx * nx[qs] * (Wd[qs] / 2 + off); qy = Y[qs] + sdx * ny[qs] * (Wd[qs] / 2 + off)
                vals.append(map_coordinates(dist_mar_g, [(qy - gy0) / cell, (qx - gx0) / cell], order=1, mode='nearest'))
            dm[sdx] = float(np.mean(vals))
        if dm[sd] > dm[-sd] + 20.0:
            print('  mirador s %.0f-%.0f: el lado %+d mira TIERRA ADENTRO (mar a %.0f m frente a %.0f m en el lado %+d): banco Z-10 OMITIDO'
                  % (s0m, s1m, sd, dm[sd], dm[-sd], -sd))
            mir_ok.append((s0m, s1m, sd, False, round(dm[sd]), round(dm[-sd])))
            continue
        mir_ok.append((s0m, s1m, sd, True, round(dm[sd]), round(dm[-sd])))
        idx_m = np.arange(max(0, int((s0m - 90.0) / paso)), min(N, int((s1m + 90.0) / paso) + 1))
        im = idx_m[cKDTree(np.column_stack([X[idx_m], Y[idx_m]])).query(gpts)[1]]
        s_m = im * paso
        fuera_s = np.maximum(np.maximum(s0m - s_m, s_m - s1m), 0.0)
        latg = (gpts[:, 0] - X[im]) * nx[im] + (gpts[:, 1] - Y[im]) * ny[im]
        dl = sd * latg - Wd[im] / 2
        # v1 (revision F-01/G12): fuera del tramo del paseo (fuera_s > 0) el banco empieza pasado el ancho del paseo y nunca
        # baja del terraplen normal de la pista (antes tallaba Z-10 desde 8 m en los 90 m de cada extremo: zanjas en V de
        # 3-8 m sin forjado ni barrera en s 2984-2988 y 3150-3158)
        # v3 (revision F-01 (1)): tampoco en los 6 primeros/ultimos metros del paseo (la transicion de la rejilla de 4 m quedaba
        # fuera del forjado: cuneta en V de 4-7 m bajo los testeros en s 2988 y 3150)
        en_borde_m = (s_m < s0m + 6.0) | (s_m > s1m - 6.0)
        dl_min = np.where((fuera_s > 0.0) | en_borde_m, an + 1.0, 8.0)
        zona = (fuera_s < 90.0) & (dl > dl_min) & (dl < 260.0) & tierra
        # v2 (revision F2-07): en los extremos el banco volvia al 115 % en 9 m (cortes transversales de 9-10 m al 100-180 % en
        # la malla): acuerdo parabolico de 20 m (1.15*f^2/40, el corte de 10 m ocupa ~19 m, pendiente media ~55 %) y despues
        # 1.15. (La rampa de 40 m que propone el revisor tallaba 30-50 m mas alla del paseo y dejaba un foso de 3 m detras
        # de la terraza de casino_mar, s 3196: probado.) Dentro de s0..s1 el banco sigue llano hasta an+45 (pie de las arcadas,
        # palazzo y su explanada) y se funde con smoothstep con el terreno hasta an+95
        _tf = np.where(fuera_s < 20.0, fuera_s * fuera_s / 40.0, fuera_s - 10.0)
        techo_m = np.maximum(Z[im] - 10.0 - (np.minimum(dl, 130.0) - 8.0) * 0.05
                             + np.maximum(dl - 130.0, 0.0) * 1.15 + _tf * 1.15, 1.0)
        techo_m = np.where(fuera_s > 0.0, np.maximum(techo_m, np.maximum(suelo, suelo_terr)), techo_m)
        _tl = np.clip((dl - (an + 45.0)) / 50.0, 0.0, 1.0); _wl = _tl * _tl * (3.0 - 2.0 * _tl)
        techo_m = techo_m * (1.0 - _wl) + np.maximum(z_grid, techo_m) * _wl
        mir_cut |= zona & (techo_m < z_grid - 0.3)
        z_grid = np.where(zona, np.minimum(z_grid, techo_m), z_grid)
        # v2 (revision F2-03): dentro del paseo (0 < dl <= an+0.5, hasta 6 m pasados sus extremos) mandaba la regla de pista
        # (desmonte a +2.7 m en 6-8 m) y la hierba atravesaba el pavimento (+0.95 m), y el paseo acababa en un monticulo:
        # techo = cota del borde - 0.25 (solo baja; el banco Z-10 bajo dl > 8 no cambia)
        _per = np.zeros(N) if peralte is None else peralte
        _zbm = Z[im] - _per[im] * sd * Wd[im] / 2.0
        paseo = (fuera_s <= 6.0) & (dl > 0.0) & (dl <= an + 0.5) & tierra
        checks.setdefault('paseo_celdas_rebajadas', 0)
        checks['paseo_celdas_rebajadas'] += int((paseo & (z_grid > _zbm - 0.25 + 0.01)).sum())
        z_grid = np.where(paseo, np.minimum(z_grid, _zbm - 0.25), z_grid)
    checks['miradores'] = mir_ok
    # --- F1 r4: CUPULA de la isla de la cima (ver cabecera CUPULA_*). Se IMPONE dentro de la isla (rellena y rebaja); fuera nada ---
    _isla56 = np.zeros(ncel, bool)
    _P56 = []; _ceil56 = None; _ceil_raw = None; _w56 = np.zeros(ncel); _wdome56 = np.zeros(ncel); _wroca56 = np.zeros(ncel)
    if CUPULA_DS > 0.0 and _dirt_s.any():
        _s56 = np.arange(N) * paso
        _en56 = (_s56 >= TIERRA_S[0]) & (_s56 <= TIERRA_S[1])
        _ia56 = int(np.where(_en56)[0][np.argmax(Z[_en56])])                  # apex = cota maxima de la tierra (s 1864)
        _sa56 = _ia56 * paso
        _j056 = max(0, int((_sa56 - CUPULA_DS) / paso)); _j156 = min(N - 1, int((_sa56 + CUPULA_DS) / paso))
        _P56 = [(float(X[k]), float(Y[k])) for k in range(_j056, _j156 + 1)]
        _isla56 = en_poligono(gpts[:, 0], gpts[:, 1], _P56) & tierra
        # techo por celda en la isla dilatada 3 celdas (para suavizar con apoyo fuera de la isla)
        _dil56 = binary_dilation(_isla56.reshape(nyg, nxg), iterations=3).ravel() & tierra
        _ci = np.where(_dil56)[0]
        _js = np.arange(max(0, _j056 - 3), min(N, _j156 + 4))
        _dx = gpts[_ci, 0][:, None] - X[_js][None, :]; _dy = gpts[_ci, 1][:, None] - Y[_js][None, :]
        _dist = np.hypot(_dx, _dy)
        _dd = _dist - Wd[_js][None, :] / 2.0
        _lon = np.abs(_dx * ny[_js][None, :] - _dy * nx[_js][None, :])
        _baja = (_js < _ia56)[None, :]                                        # rama que sube a la cima (la baja): pared
        _nB = 1.0 + CUPULA_RUIDO[0] * ruido_valor(np.random.default_rng(seed + 113), nyg, nxg, cell, 50.0).ravel()[_ci][:, None]
        _nC = 1.0 + CUPULA_RUIDO[1] * ruido_valor(np.random.default_rng(seed + 127), nyg, nxg, cell, 50.0).ravel()[_ci][:, None]
        _q = np.maximum(_dd - 4.5, 0.0)
        _prof_b = CUPULA_BASE_B + CUPULA_PEND_B * _nB * np.where(_q < CUPULA_T_B, _q * _q / (2.0 * CUPULA_T_B), _q - 0.5 * CUPULA_T_B)
        _hC = CUPULA_H_C * _nC; _LC = CUPULA_L_C * _nC
        _u = np.clip(_q / _LC, 0.0, 1.0)
        _prof_c = _hC * (1.0 - (1.0 - _u) ** CUPULA_P_C)                       # convexa (p 1.5): pendiente al pie p H/L, 0 en la cumbre
        _vale = _lon < CUPULA_LON_M
        _famB = np.where(_vale & _baja, Z[_js][None, :] - 0.5 + _prof_b, 1e9).min(1)
        _famC = np.where(_vale & ~_baja, Z[_js][None, :] - 0.5 + _prof_c, 1e9).min(1)

        def _smin(a_, b_, k_):
            return np.minimum(a_, b_) - k_ * np.log1p(np.exp(-np.abs(a_ - b_) / k_))
        _T = _smin(_famB, _famC, CUPULA_K_CRESTA)                              # cresta redondeada entre las dos familias
        # coordenada a lo largo de la isla: m de s desde el apex (media de la muestra mas cercana de cada rama)
        _sB = _js[np.argmin(np.where(_baja, _dist, 1e9), 1)] * paso
        _sC = _js[np.argmin(np.where(~_baja, _dist, 1e9), 1)] * paso
        _t56 = 0.5 * ((_sa56 - _sB) + (_sC - _sa56))
        _zcap = Z[_ia56] + CUPULA_NARIZ_DZ + CUPULA_NARIZ_PEND * np.maximum(_t56 - (CUPULA_S_NARIZ - _sa56), 0.0)
        _T = _smin(_T, _zcap, CUPULA_K_CRESTA)                                # nariz por debajo del ojo de la camara 56
        # F1 r4b: LOMA SUR = terreno de r3 (ver cabecera CUPULA_SUR_T): a mas de CUPULA_SUR_T[1] m del apex (por la isla) el techo es el
        # terreno de antes (pared de 63 grados de la rama baja con su roca, la de la toma 51; flanco de la rama alta), con transicion
        # desde CUPULA_SUR_T[0]; solo lo acota la linea de vista de 56 (abajo)
        # La loma sur la acota la LINEA DE VISTA de 56: su cresta no sube desde el ojo (apex + CUPULA_VIS_DZ) mas de CUPULA_VIS_GRADOS
        # (<= 0: queda por debajo de la cumbre de la cupula y no asoma detras como un segundo pico ni como arista contra el cielo);
        # smooth-min de radio CUPULA_K_VIS: la cresta recortada es redondeada
        _tS = np.clip((_t56 - CUPULA_SUR_T[0]) / (CUPULA_SUR_T[1] - CUPULA_SUR_T[0]), 0.0, 1.0)
        _wsur = _tS * _tS * (3.0 - 2.0 * _tS)
        _dap = np.hypot(gpts[_ci, 0] - X[_ia56], gpts[_ci, 1] - Y[_ia56])
        _zvis = Z[_ia56] + CUPULA_VIS_DZ + _dap * math.tan(math.radians(CUPULA_VIS_GRADOS))
        _Tsur = _smin(z_grid[_ci], _zvis, CUPULA_K_VIS)
        _T = np.where(_T < 1e8, _T + (_Tsur - _T) * _wsur, np.where(_wsur > 0.999, _Tsur, 1e9))
        _ceil_raw = np.full(ncel, np.nan); _ceil_raw[_ci] = np.where(_T < 1e8, _T, np.nan)
        _c2 = _ceil_raw.reshape(nyg, nxg)
        _ok2 = np.isfinite(_c2)
        _c2f = np.where(_ok2, _c2, 0.0)
        _num = gaussian_filter(_c2f, CUPULA_SUAVE_M / cell); _den = gaussian_filter(_ok2.astype(float), CUPULA_SUAVE_M / cell)
        _ceil56 = np.where(_den > 1e-3, _num / np.maximum(_den, 1e-3), np.nan).ravel()
        # pesos: corredor (4.5 -> 6 m del borde, smoothstep) x fundido en el extremo sur de cada media rama x isla
        _te = np.clip((dedge0 - CUPULA_D_MIN[0]) / (CUPULA_D_MIN[1] - CUPULA_D_MIN[0]), 0.0, 1.0)
        _ws = np.zeros(ncel)
        _fB = np.clip((_sB - (_sa56 - CUPULA_DS)) / CUPULA_FUNDIDO_S, 0.0, 1.0)
        _fC = np.clip(((_sa56 + CUPULA_DS) - _sC) / CUPULA_FUNDIDO_S, 0.0, 1.0)
        _ws[_ci] = (_fB * _fB * (3.0 - 2.0 * _fB)) * (_fC * _fC * (3.0 - 2.0 * _fC))
        _w56 = (_te * _te * (3.0 - 2.0 * _te)) * _ws * _isla56 * np.isfinite(_ceil56)
        _z56 = np.where(_w56 > 0.0, z_grid + (np.nan_to_num(_ceil56) - z_grid) * _w56, z_grid)
        # r4b: peso de CUPULA propiamente dicha (sin la loma sur de r3): ahi no hay costillas; y peso SIN ROCA ('tierra' de corte
        # tampoco) = cupula salvo el flanco de la rama baja con s <= CUPULA_ROCA_B_S (43 grados, mira al O: cara trasera para 56 y
        # roca al fondo de la recta de 51); la nariz (s de la rama baja > CUPULA_ROCA_B_S[1], mira al N, a la camara 56) sin roca
        _dB = np.where(_baja, _dd, 1e9).min(1); _dC = np.where(~_baja, _dd, 1e9).min(1)
        _tL = np.clip(0.5 + (_dC - _dB) / CUPULA_LADO_M, 0.0, 1.0)
        _tR = np.clip((CUPULA_ROCA_B_S[1] - _sB) / (CUPULA_ROCA_B_S[1] - CUPULA_ROCA_B_S[0]), 0.0, 1.0)
        _wdome56[_ci] = 1.0 - _wsur
        _wdome56 = _wdome56 * _w56
        _wroca56[_ci] = (1.0 - _wsur) * (1.0 - (_tL * _tL * (3.0 - 2.0 * _tL)) * (_tR * _tR * (3.0 - 2.0 * _tR)))
        _wroca56 = _wroca56 * _w56
        checks['cupula'] = {'apex_s': int(_sa56), 'celdas_isla': int(_isla56.sum()), 'celdas_rebajadas': int((_z56 < z_grid - 0.05).sum()),
                            'celdas_loma_sur_r3': int(((_w56 > 0.3) & (_wdome56 <= 0.3)).sum()), 'celdas_cupula': int((_wdome56 > 0.3).sum()),
                            'celdas_sin_roca': int((_wroca56 > 0.3).sum()),
                            'celdas_rellenadas': int((_z56 > z_grid + 0.05).sum()),
                            'rebaje_max_m': round(float((z_grid - _z56).max()), 1), 'relleno_max_m': round(float((_z56 - z_grid).max()), 1),
                            'cumbre_z_antes': round(float(z_grid[_isla56].max()), 1),
                            'cumbre_z': round(float(_z56[_isla56].max()), 1), 'z_apex_pista': round(float(Z[_ia56]), 1)}
        z_grid = _z56
    # v2 (revision B2-09/C2-11/E2-07 (3)/F2-01 (3)/A-r2-07): las caras de desmonte eran planos perfectos (pendiente constante
    # paralela a la pista: 'losa gris', 'corte recto'). COSTILLAS de erosion: ruido ridged de 24/12 m RESTADO (solo baja,
    # hasta 2 m) en las caras de corte real (terreno natural > 1-4 m por encima), a > 8 m del borde del asfalto (fundido en
    # 6 m) y con pendiente > 0.5. Nunca en terrazas, banco del mirador, lungomare, explanada del pit, viaducto ni Loews:
    # el corredor de la pista no cambia
    _pz0 = _pendiente(z_grid.reshape(nyg, nxg), cell).ravel()
    _rid_e = ruido_ridged(np.random.default_rng(seed + 41), nyg, nxg, cell, octavas=((24.0, 1.0), (12.0, 0.5))).ravel()
    # F1 r2: tambien en la CARA del lomo de la tierra tallada (relleno de > 2 m sobre el natural, solo en 'dirt' y a < 20 m del
    # borde: la cresta, donde se mide el KPI de 25 m, no se toca): sin esto las dos caras del lomo eran planos perfectos
    # ('piramide facetada' en la postal 56)
    _we_fill = np.clip((z_grid - z_land - 2.0) / 3.0, 0.0, 1.0) * np.clip((20.0 - dedge0) / 5.0, 0.0, 1.0) * _dirt_s[g_near]
    _we = (np.clip((dedge0 - 8.0) / 6.0, 0.0, 1.0) * np.maximum(np.clip((z_land - z_grid - 1.0) / 3.0, 0.0, 1.0), _we_fill)
           * np.clip((_pz0 - 0.5) / 0.3, 0.0, 1.0))
    # (F1 r4: ni en la CUPULA de la isla de la cima: no lleva costillas; en r3 las costillas ridged de 24/12 m hacian serpentear la
    # frontera roca/hierba por el flanco y cada cruce daba un diente por cara de 4 m en la postal 56. r4b: la pared sur de la rama
    # baja (la loma sur, CUPULA_SUR_T: la pared de la toma 51) SI las conserva, como en r3)
    _no_e = terr_mask | mir_cut | _lungo | (d_loews < R_LOEWS_CONG[1] + 10.0) | (d_bri < 30.0) | ~tierra | (_wdome56 > 0.3)
    if pit_pts:
        _no_e |= caja & (dpe < dpe0 + 3.0)
    if el_casino is not None:
        _no_e |= r_cas < 1.1
    _we = np.where(_no_e, 0.0, _we)
    checks['costillas_celdas'] = int((_we * _rid_e > 0.25).sum())
    checks['costillas_relleno_celdas'] = int(((_we_fill > 0.5) & (_we * _rid_e > 0.25)).sum())   # r2: en las caras del lomo de la tierra
    # F1 (bloque 1.2): tope 2 m -> COSTILLA_TOPE[1] (4 m) en las caras de corte de > 20 m (fundido hasta 35 m) con pendiente > 0.8;
    # a < 60 m de una terraza, solo a > 10 m sobre el patio mas cercano (con 4 m al pie de la cara se abrian pozos de 2 m
    # en la QA de fosos: agua atrapada > 1.5 m en pueblo_subida/alto_ladera)
    _f_alt_e = np.ones(ncel)
    if terr_mask.any():
        _edt_t, _idx_t = distance_transform_edt(~terr_mask.reshape(nyg, nxg), return_indices=True)
        _z_patio = z_grid.reshape(nyg, nxg)[_idx_t[0], _idx_t[1]].ravel()
        _f_alt_e = np.where(_edt_t.ravel() * cell < 60.0, np.clip((z_grid - _z_patio - 10.0) / 8.0, 0.0, 1.0), 1.0)
    # (y 2 m como antes en la huella del McLaren + 30 m (r2: _w_mcl_f1, fundido a 45): el encaje del coche no cambia ni 1 cm)
    _amp_e = COSTILLA_TOPE[0] + (COSTILLA_TOPE[1] - COSTILLA_TOPE[0]) * (np.clip((z_land - z_grid - 20.0) / 15.0, 0.0, 1.0)
                                                                        * np.clip((_pz0 - 0.8) / 0.2, 0.0, 1.0) * _f_alt_e * _w_mcl_f1)
    checks['costillas_celdas_gt_2m'] = int((_amp_e * _we * _rid_e > 2.0).sum())
    z_grid = z_grid - _amp_e * _we * _rid_e
    # v3 (revision H2 (3)/H3): la cara de la muralla del canal (y del lobulo SO) era un plano al 300 % con estrias regulares
    # de la rejilla: costillas ridged de 30/15 m RESTADAS (solo baja, hasta 4 m) en las caras de acantilado de tierra con
    # z > 8, a 28-120 m del viaducto, a > 25 m del asfalto y fuera de terrazas (+16 m), penon, Loews, mirador y pit
    _terr_d = binary_dilation(terr_mask.reshape(nyg, nxg), iterations=4).ravel()
    _rid_c = ruido_ridged(np.random.default_rng(seed + 53), nyg, nxg, cell, octavas=((30.0, 1.0), (15.0, 0.5))).ravel()
    _wcf = (_wcan * np.clip((d_bri - 28.0) / 8.0, 0.0, 1.0) * np.clip((120.0 - d_bri) / 20.0, 0.0, 1.0)
            * np.clip((z_grid - 8.0) / 4.0, 0.0, 1.0) * np.clip((dedge0 - 25.0) / 10.0, 0.0, 1.0))
    _wcf = np.where(acantilado & ~_terr_d & ~_no_e, _wcf, 0.0)
    checks['canal_costillas_celdas'] = int((_wcf * _rid_c > 0.25).sum())
    z_grid = z_grid - 4.0 * _wcf * _rid_c
    _baja_nat = 4.0 * _wcf * _rid_c         # v3: rebaje 'natural' (costillas del canal, picos G4): no es desmonte para la mascara
    # --- garantia final: nada atraviesa el asfalto (todas las ramas) ---
    dbg('z_mirador', z_grid)
    asf = d_land < half_c + 1.0
    z_grid = np.where(asf & tierra, np.minimum(z_grid, techo), z_grid)
    # --- mar: fondo a -4 con costa continua ---
    z_grid = np.where(tierra, z_grid, np.minimum(z_grid, 1.0))
    # v1 (revision J6/B12, probado por el revisor; aqui solo lejos de la pista, del puerto y del penon): el umbral duro
    # coastF > 0.5 -> z <= -3 dejaba un escalon de ~5 m en la orilla (92 % de los pares tierra/mar > 3 m) que seguia la
    # escalera de 4 m de la mascara: dientes de arena. En costa NATURAL (a > 80 m de la pista y > 100 m del viaducto,
    # fuera del penon y de la tierra protegida) la cota sigue la distancia firmada a la costa suave (exacta para la
    # gaussiana de 12 m): playa al 40 % y fondo al 35 % hasta -4. El resto, como antes.
    from scipy.special import ndtri as _ndtri
    _cg = np.clip(coast.ravel(), 1e-6, 1.0 - 1e-6)
    _sdf = -12.0 * _ndtri(_cg)
    _nat = (coast.ravel() < 0.5) & ~protegido & ~casino_zona & (d_land > 80.0) & (d_bri > 100.0)
    _nat_m = (coast.ravel() >= 0.5) & ~casino_zona & (d_land > 80.0) & (d_bri > 100.0)
    # v2 (revision N2-A): en el lungomare ampliado (s 5030-5200, lado +1) tambien orilla continua, con talud al 67 %
    _nat = _nat | (_lungo & (coastF < 0.5)); _nat_m = _nat_m | (_lungo & (coastF >= 0.5))
    _tal = np.where(_lungo, 0.67, 0.40)
    _land = coastF < 0.5
    _orig = z_grid * (1.0 - coastF) + Z_FONDO_MAR * coastF
    _zl = np.where(_sdf <= 8.0, np.minimum(z_grid, 0.15 + _tal * np.maximum(_sdf, 0.0)), _orig)
    _os = np.minimum(_orig, -3.0)
    _zs = np.where(_os < Z_FONDO_MAR - 0.5, _os, np.maximum(Z_FONDO_MAR, np.minimum(np.minimum(z_grid, 1.0), 0.35 * np.minimum(_sdf, -0.3))))
    _z_old = np.where(_land, np.where(_nat, _zl, _orig), np.where(_nat_m, _zs, np.where(coastF > 0.5, np.minimum(_orig, -3.0), _orig)))
    # v3 (revision J6/B12): junto a la pista (< 80 m) y al viaducto la orilla seguia el umbral DURO coastF > 0.5 -> z <= -3: escalon
    # de 3-7 m en escalera de 4 m (71 % de los pares tierra/agua > 3 m; s 400-650 y 3500-4500). Ahi tambien orilla continua por la
    # distancia firmada, con peso fundido (0 a < 15 m del borde del asfalto y a < 25 m del viaducto, 1 diez metros mas alla; solo
    # a < 90-110 m de la pista y a < 20-30 m de la orilla: mas lejos la distancia firmada de la gaussiana satura en ~57 m) y
    # tambien en tierra protegida: playa/derrubios al 40 % en los 8 m de la orilla y despues tope al 300 % (los acantilados
    # conservan su cara; sin escalon en sdf = 8), fondo al 35 % hasta -4. Nunca en la Loews, el penon (r < 1.9), la huella del
    # McLaren (+10 m) ni la darsena del puerto (s > 4980 o < 240); donde ya actua la orilla natural (v1/v2) no cambia nada
    _wj6 = (np.clip((dedge0 - 15.0) / 10.0, 0.0, 1.0) * np.clip((d_bri - 25.0) / 10.0, 0.0, 1.0)
            * np.clip((d_loews - R_LOEWS_INTACTA) / 20.0, 0.0, 1.0) * ((_sg_all <= 4980.0) & (_sg_all >= 240.0))
            * np.clip((110.0 - d_all) / 20.0, 0.0, 1.0) * np.clip((30.0 - _sdf) / 10.0, 0.0, 1.0))
    if el_casino is not None:
        _wj6 = _wj6 * np.clip((r_cas - 1.9) / 0.3, 0.0, 1.0)
    _wj6 = _wj6 * _w_mcl_c
    _wj6 = np.where(np.where(_land, _nat, _nat_m) | _lungo, 0.0, _wj6)
    _cap6 = 0.15 + 0.40 * np.clip(_sdf, 0.0, 8.0) + np.maximum(_sdf - 8.0, 0.0) * 3.0
    _zs6 = np.where(_os < Z_FONDO_MAR - 0.5, _os, np.maximum(Z_FONDO_MAR, np.minimum(np.minimum(z_grid, 1.0), 0.35 * np.minimum(_sdf, -0.3))))
    z_grid = _z_old * (1.0 - _wj6) + np.where(_land, np.minimum(z_grid, _cap6), _zs6) * _wj6
    z_grid = np.where(_land & (_wj6 > 0.0), np.maximum(z_grid, 0.15 * _wj6), z_grid)    # la tierra de la orilla nunca bajo el agua
    checks['orilla_continua_pista_celdas'] = int((_wj6 > 0.5).sum())
    # v2 (revision J2-09 (1)): la orilla natural J6 rebajaba celdas SUELTAS donde la costa suavizada hace un pico (muesca de
    # 10-12 m a 2.2 m entre celdas de 11-15 m en la raiz del brazo E): cierre morfologico 5x5 solo en tierra de costa natural
    # a < 14 m del mar (rellena pozos de 1-3 celdas, nunca sube mas de 12 m; una rampa de playa no cambia)
    _zc = grey_closing(z_grid.reshape(nyg, nxg), size=(5, 5)).ravel()
    _poz = _land & (_nat | (_wj6 > 0.5)) & ~_lungo & (_sdf < 14.0)      # v3 (J6): tambien en la orilla continua junto a la pista
    checks['orilla_pozos_rellenos'] = int((_poz & (_zc > z_grid + 0.5)).sum())
    z_grid = np.where(_poz, np.maximum(z_grid, np.minimum(_zc, z_grid + 12.0)), z_grid)
    es_mar_out = coastF > 0.5
    # tierra protegida (salvo la garganta del viaducto): nunca bajo el agua
    prot_tierra = protegido & ~mar_forzado & (d_bri > 60.0)
    # v3 (revision J6 (2)): en la orilla continua junto a la pista la playa de los primeros 1.5 m queda bajo 0.3 (sin escalon)
    z_grid = np.where(prot_tierra, np.maximum(z_grid, np.where((_wj6 > 0.0) & (_sdf <= 1.5), 0.15, 0.3)), z_grid)
    dbg('z_final', z_grid)
    if congelar is not None:
        # v1: terreno de la rotonda Loews intacto (ver construir_loews_intacta)
        w_c = np.clip((R_LOEWS_CONG[1] - d_loews) / (R_LOEWS_CONG[1] - R_LOEWS_CONG[0]), 0.0, 1.0)
        w_c = w_c * w_c * (3.0 - 2.0 * w_c)
        if 'idx' in congelar:
            # v2 (revision J-N2): referencia FIJA (assets/_loews_terreno.npz, terreno entregado) solo en sus celdas
            _ic = np.asarray(congelar['idx'], int)
            z_old = z_grid.copy(); z_old[_ic] = np.asarray(congelar['z'], float)
            mar_old = es_mar_out.copy(); mar_old[_ic] = np.asarray(congelar['mar'], bool)
            _en = np.zeros(ncel, bool); _en[_ic] = True
            w_c = np.where(_en, w_c, 0.0)
        else:
            z_old = np.asarray(congelar['z_grid'], float).ravel()
            mar_old = np.asarray(congelar['es_mar'], bool).ravel()
        checks['loews_congelada_dz_max'] = round(float(np.abs(z_grid - z_old)[d_loews < R_LOEWS_CONG[0]].max()), 2)
        z_grid = z_grid * (1.0 - w_c) + z_old * w_c
        es_mar_out = np.where(w_c > 0.5, mar_old, es_mar_out)
        checks['loews_ref_fija'] = bool(congelar.get('fijo', False))
        checks['loews_ref_dz_max'] = round(float(np.abs(z_grid - z_old)[d_loews < R_LOEWS_CONG[0]].max()), 3)
        print('  rotonda Loews intacta: terreno de referencia %s a < %.0f m de su centro (fundido hasta %.0f m; diferencia que se '
              'evita: %.2f m; |z - referencia| a < %.0f m: %.3f m)'
              % ('FIJA (assets/_loews_terreno.npz)' if checks['loews_ref_fija'] else 'RECONSTRUIDA (v1)', R_LOEWS_CONG[0],
                 R_LOEWS_CONG[1], checks['loews_congelada_dz_max'], R_LOEWS_CONG[0], checks['loews_ref_dz_max']))
    w_cong = (np.clip((R_LOEWS_CONG[1] - d_loews) / (R_LOEWS_CONG[1] - R_LOEWS_CONG[0]), 0.0, 1.0) > 0.0) if congelar is not None \
        else np.zeros(ncel, bool)
    # v2 (revision C2-01/D2-01/G2-03/E2-01/E2-08/F2-11): garantia POR TRIANGULO (no solo por vertice): ningun triangulo del
    # TERRENO asoma sobre el plano peraltado de la calzada (lat = peralte de cada muestra; la rotonda Loews no se toca)
    # v2 (revision E2-08/E2-01, opcional del revisor): en el INTERIOR de las horquillas cerradas (R < 15 m) la isla toma el
    # techo de la rama que baja (min de los dos ramales; con el techo C1 aun mas bajo): queda 0.6-1.5 m bajo el borde del
    # asfalto (astilla gris, pliegue del arcen). Suelo = cota del borde interior - 0.6 a < 8 m del borde (nunca en la Loews;
    # la garantia de hierba de debajo baja lo que asome)
    # (_kap, la curvatura con signo, se calcula arriba, antes de las reglas de pista: F1 tierra tallada)
    _per = np.zeros(N) if peralte is None else peralte
    _sgi = np.sign(_kap[g_near])
    _isla = (tierra & (1.0 / np.maximum(np.abs(_kap[g_near]), 1e-6) < 15.0) & (np.sign(_lat0) == _sgi) & (dedge0 > 0.0)
             & (dedge0 < 8.0) & ~w_cong & (d_bri > 30.0))
    _zbi = Z[g_near] - _per[g_near] * _sgi * Wd[g_near] / 2.0 - 0.6
    checks['horquilla_isla_celdas'] = int((_isla & (z_grid < _zbi - 0.05)).sum())
    z_grid = np.where(_isla, np.maximum(z_grid, _zbi), z_grid)
    # v3 (revision G4/H3): las crestas que cruzan la rejilla en oblicuo salian en dientes de sierra (46 nodos con
    # |z - media de 4 vecinos| > 1.5 m en el promontorio, almenas de 4-8 m en la muralla del canal): 3 pasadas que SOLO bajan
    # los picos convexos (z -= 0.5*lap si lap > 0.8 m), a > 25 m del asfalto y fuera de terrazas, penon (r < 1.9), huella del
    # McLaren, Loews, miradores, lungomare, viaducto, mar y orilla (a < 10 m del agua o z < 4: el pie no baja del nivel del mar)
    _mov_g4 = (tierra & (dedge0 > 25.0) & ~binary_dilation(terr_mask.reshape(nyg, nxg), iterations=2).ravel() & (r_cas > 1.9)
               & (_w_mcl > 0.99)
               & (d_loews > R_LOEWS_INTACTA) & ~mir_cut & ~_lungo & (d_bri > 30.0) & (_sdf > 10.0) & (z_grid > 4.0)).reshape(nyg, nxg)
    _zg4 = z_grid.reshape(nyg, nxg).copy()
    for _ in range(3):
        _lap = _zg4.copy()
        _lap[1:-1, 1:-1] = _zg4[1:-1, 1:-1] - 0.25 * (_zg4[:-2, 1:-1] + _zg4[2:, 1:-1] + _zg4[1:-1, :-2] + _zg4[1:-1, 2:])
        _lap[0, :] = 0.0; _lap[-1, :] = 0.0; _lap[:, 0] = 0.0; _lap[:, -1] = 0.0
        _zg4 = np.where(_mov_g4 & (_lap > 0.8), _zg4 - 0.5 * _lap, _zg4)
    checks['picos_suavizados_celdas'] = int((np.abs(_zg4.ravel() - z_grid) > 0.05).sum())
    _baja_nat = _baja_nat + np.maximum(z_grid - _zg4.ravel(), 0.0)
    dbg('z_isla', z_grid)
    z_grid = _zg4.ravel()
    dbg('z_picos', z_grid)
    # v3 (revision B5 (2)): dentro del tunel (s 410-536; las caras estan en 404/540) los nodos de 4-9.5 m del borde, bajo 33-39 m
    # de roca, quedaban hasta +9 m sobre la rasante y los triangulos hacia el corredor cortaban la linea de la pared (4 m) por
    # encima de TUNEL_suelo (picos verdes de 0.4-0.8 m): bajan a la cota del borde - 0.6 (no se ven: estan bajo la roca)
    _sgn = g_near * paso
    _per_t = np.zeros(N) if peralte is None else peralte
    _zbt = Z[g_near] - _per_t[g_near] * np.sign(_lat0) * Wd[g_near] / 2.0 - 0.6
    # (solo los nodos a <= 10 m sobre la calzada y, en las bandas de terrazas + 25-40 m, como mucho 1.5 m: la ladera de
    # pueblo_subida_ladera pasa junto al tunel y, rebajada entera, la QA de fosos tras la ultima terraza veia un pozo de 2 m)
    _tun = (tierra & (_sgn >= 410.0) & (_sgn <= 536.0) & (dedge0 > 4.0) & (dedge0 < 9.5) & ~w_cong
            & (z_grid < _zbt + 10.6))
    _zbt = np.where(fac_valle > 0.5, _zbt, np.maximum(_zbt, z_grid - 1.5))   # junto a las terrazas, como mucho 1.5 m
    checks['tunel_nodos_bajados'] = int((_tun & (z_grid > _zbt + 0.01)).sum())
    z_grid = np.where(_tun, np.minimum(z_grid, _zbt), z_grid)
    dbg('z_tunel', z_grid)
    z_pre_h = z_grid.copy()
    z_grid, info_h = bajar_bajo_asfalto(z_grid, gx0, gy0, cell, nxg, nyg, X, Y, Z, nx, ny, Wd, peralte, sec, fijo=w_cong)
    checks['hierba_asfalto'] = info_h
    print('  hierba sobre el asfalto (triangulos de la malla, cada 1 m x 0.5 m%s): %d puntos > 2 cm (max %.2f m) -> %d (max %.2f m); '
          '%d vertices bajados (max %.2f m; fuera de la calzada %d, max %.2f m); en la Loews sin tocar: %d'
          % ('' if peralte is not None else ', SIN peralte', info_h['antes_gt_2cm'], info_h['antes_max'], info_h['despues_gt_2cm'],
             info_h['despues_max'], info_h['vertices_bajados'], info_h['bajada_max'], info_h['fuera_bajados'],
             info_h['fuera_bajada_max'], info_h['residuo_en_fijo']))
    # v3: sin contar el rebaje 'natural' v3 (costillas del canal y picos G4): con el, la cara del canal pasaba a 'desmonte' de
    # poca profundidad y la mascara la pintaba de hierba
    desmonte = tierra & (z_grid + _baja_nat < z_land - 0.3)     # rebajado por una regla dura (pista, terrazas, pit, mirador)
    obra = tierra & (np.abs(z_grid + _baja_nat - z_land) > 0.3)  # rebajado o levantado por una regla dura
    obra = binary_dilation(obra.reshape(nyg, nxg), iterations=1).ravel()
    zg = z_grid.reshape(nyg, nxg)

    # --- RONDA 15b: QA de terrazas ---
    def z_en(xq, yq):
        return map_coordinates(zg, [(np.asarray(yq) - gy0) / cell, (np.asarray(xq) - gx0) / cell], order=1, mode='nearest')

    def celda_de(xq, yq):
        return (np.clip(np.round((np.asarray(yq) - gy0) / cell).astype(int), 0, nyg - 1) * nxg
                + np.clip(np.round((np.asarray(xq) - gx0) / cell).astype(int), 0, nxg - 1))
    # (c) COSTURAS: escalon entre celdas vecinas (4-conexas) de la MISMA terraza del MISMO
    # sector, fuera de las rampas (bordillo, muro, borde exterior), DESCONTANDO la rasante
    # (la terraza sigue Z(s): en el casino, al 13.5 %, dos celdas vecinas a lo largo de la
    # calle difieren 0.54 m sin ser costura): residuo = |dz - (Z(g_a) - Z(g_b))| cuando las
    # muestras mas cercanas g_a, g_b estan a <= 20 m por la pista; si no, |dz| entero (eje
    # medial). Objetivo < 0.6 m (C0: sin escalones)
    # RONDA 15c: los pares cuyas muestras mas cercanas estan a > 60 m por la pista (ramas
    # enfrentadas de una horquilla) o que caen en el talud de mezcla (terr_mix) NO son costuras:
    # son el TALUD ENTRE RAMAS (continuo por diseno) y se informan aparte con su pendiente.
    tmx = terr_mix.reshape(nyg, nxg)
    tm = (terr_mask & ~terr_rampa).reshape(nyg, nxg)
    tk = terr_k.reshape(nyg, nxg); ts = terr_sec.reshape(nyg, nxg); tg = terr_g.reshape(nyg, nxg)
    dz_map = np.zeros((nyg, nxg)); tal_map = np.zeros((nyg, nxg))
    for sa, sb in ((((slice(None), slice(0, -1)), (slice(None), slice(1, None)))),
                   (((slice(0, -1), slice(None)), (slice(1, None), slice(None))))):
        par = tm[sa] & tm[sb] & (tk[sa] == tk[sb]) & (ts[sa] == ts[sb])
        ga = np.where(par, tg[sa], 0); gb = np.where(par, tg[sb], 0)
        dsab = np.abs(ga - gb) * paso
        misma_rama = dsab <= 20.0
        rama_lejana = (dsab > 60.0) | tmx[sa] | tmx[sb]
        dzv = np.where(misma_rama, np.abs((zg[sa] - zg[sb]) - (Z[ga] - Z[gb])), np.abs(zg[sa] - zg[sb]))
        dz = np.where(par & ~rama_lejana, dzv, 0.0)
        tal = np.where(par & rama_lejana, np.abs(zg[sa] - zg[sb]), 0.0)
        dz_map[sa] = np.maximum(dz_map[sa], dz); dz_map[sb] = np.maximum(dz_map[sb], dz)
        tal_map[sa] = np.maximum(tal_map[sa], tal); tal_map[sb] = np.maximum(tal_map[sb], tal)
    checks['costuras_dz_max'] = round(float(dz_map.max()), 2)
    checks['costuras_celdas_gt_0p3'] = int((dz_map > 0.3).sum())
    checks['costuras_celdas_gt_0p6'] = int((dz_map > 0.6).sum())
    checks['talud_ramas_celdas'] = int((tal_map > 0.0).sum())
    checks['talud_ramas_dz_max'] = round(float(tal_map.max()), 2)
    checks['talud_ramas_pendiente_max'] = round(float(tal_map.max()) / cell, 2)
    cost_sec = []
    for i_sc, sc in enumerate(sectores):
        m = (ts == i_sc) & tm
        if not m.any():
            continue
        dzs = np.where(m, dz_map, 0.0); tals = np.where(m, tal_map, 0.0)
        j, i = np.unravel_index(int(np.argmax(dzs)), dzs.shape)
        cost_sec.append((sc['id'], round(float(dzs.max()), 2), int((dzs > 0.6).sum()), int((dzs > 0.3).sum()),
                         round(float(GX[j, i])), round(float(GY[j, i])), int(tk[j, i]),
                         int((tals > 0.0).sum()), round(float(tals.max()), 2)))
    checks['costuras_por_sector'] = cost_sec
    # costuras ENTRE sectores (celdas llanas vecinas de sectores distintos, p.ej. ladera/mar de
    # ramas contiguas de una S): se informan aparte, son escalones entre dos sistemas de terrazas
    tm2 = terr_mask.reshape(nyg, nxg) & ~terr_rampa.reshape(nyg, nxg)
    dz_inter = np.zeros((nyg, nxg))
    for sa, sb in ((((slice(None), slice(0, -1)), (slice(None), slice(1, None)))),
                   (((slice(0, -1), slice(None)), (slice(1, None), slice(None))))):
        par = tm2[sa] & tm2[sb] & (ts[sa] != ts[sb])
        dz = np.where(par, np.abs(zg[sa] - zg[sb]), 0.0)
        dz_inter[sa] = np.maximum(dz_inter[sa], dz); dz_inter[sb] = np.maximum(dz_inter[sb], dz)
    checks['costuras_entre_sectores_max'] = round(float(dz_inter.max()), 2)
    checks['costuras_entre_sectores_celdas_gt_0p6'] = int((dz_inter > 0.6).sum())
    if dz_inter.max() > 0.0:
        j, i = np.unravel_index(int(np.argmax(dz_inter)), dz_inter.shape)
        print('  costuras ENTRE sectores (celdas llanas vecinas de sectores distintos): max %.2f m, %d celdas > 0.6 (peor en (%d, %d))'
              % (dz_inter.max(), int((dz_inter > 0.6).sum()), round(float(GX[j, i])), round(float(GY[j, i]))))
    print('  COSTURAS (escalon entre celdas vecinas de la misma terraza y rama, fuera de rampas, descontada la rasante): max %.2f m; celdas > 0.3: %d, > 0.6: %d'
          % (checks['costuras_dz_max'], checks['costuras_celdas_gt_0p3'], checks['costuras_celdas_gt_0p6']))
    print('  TALUD ENTRE RAMAS enfrentadas (eje medial de horquillas, mezcla smoothstep desde u %.0f): %d celdas, dz max %.2f m por celda (pendiente %.0f %%)'
          % (U_FLAT, checks['talud_ramas_celdas'], checks['talud_ramas_dz_max'], 100.0 * checks['talud_ramas_pendiente_max']))
    for c in cost_sec:
        print('    %-22s costuras max %.2f m (> 0.6: %d celdas, > 0.3: %d) en (%d, %d) terraza %d | talud entre ramas: %d celdas, dz max %.2f' % c)
    # (d) COBERTURA: toda la longitud s0..s1 de cada sector debe quedar aterrazada; para cada
    # muestra y terraza se mide el terreno en el eje de la calle (u 3.75) y en el centro de la
    # banda (u 10) y se compara con Z(s)+h_k. Los puntos donde la banda se PLIEGA (curva
    # interior con radio < u: la distancia real a la pista del sector es menor que u, la
    # banda no existe ahi y urbanismo.py limpia ese bucle) no cuentan. Los tramos que fallan
    # se imprimen con su causa.
    cobertura = []
    for i_sc, sc in enumerate(sectores):
        s0, s1, lado, nt = float(sc['s0']), float(sc['s1']), int(sc['lado']), int(sc['n_terrazas'])
        sg = sentido_terrazas(sc)
        hs = [sg * (H1 + HT * k) for k in range(nt)]
        ii = idx_land[(s_land >= s0) & (s_land <= s1)]
        if len(ii) == 0:
            continue
        js_ext = ii
        tree_s = cKDTree(np.column_stack([X[js_ext], Y[js_ext]]))
        tramos = []
        n_ok_tot = 0; n_tot = 0; n_pliegue = 0
        for k in range(nt):
            u_c = AT * k + 10.0
            pts = {}
            for nombre, u in (('calle', AT * k + BORD + 2.25), ('centro', u_c)):
                px = X[ii] + lado * nx[ii] * (Wd[ii] / 2 + u); py = Y[ii] + lado * ny[ii] * (Wd[ii] / 2 + u)
                dv = z_en(px, py) - (Z[ii] + hs[k])
                d_real = tree_s.query(np.column_stack([px, py]))[0]
                pts[nombre] = (px, py, dv, d_real < u + Wd[ii] / 2 - 2.0)
            px, py, dv, pl = pts['centro']
            pliegue = pl | pts['calle'][3]
            malo = ((np.abs(pts['calle'][2]) > 0.6) | (np.abs(dv) > 0.6)) & ~pliegue
            dev_c = np.where(np.abs(pts['calle'][2]) > np.abs(dv), pts['calle'][2], dv)
            n_tot += int((~pliegue).sum()); n_ok_tot += int((~malo & ~pliegue).sum()); n_pliegue += int(pliegue.sum())
            if not malo.any():
                continue
            cel = celda_de(px, py)
            d_otro_ramal = tree_land.query(np.column_stack([px, py]))[0]
            # otra RAMA del sector al lado del punto: distancia lateral (|lat| - w/2) a las muestras
            # con |ds| > 60 m que tienen el punto a su costado (|lon| <= 3 m)
            dk, ik = tree_s.query(np.column_stack([px, py]), k=96, distance_upper_bound=200.0)
            valid = np.isfinite(dk)
            gk = js_ext[np.where(valid, ik, 0)]
            dl = np.abs(gk - ii[:, None]) * paso
            vxk = px[:, None] - X[gk]; vyk = py[:, None] - Y[gk]
            latk = np.abs(vxk * nx[gk] + vyk * ny[gk]) - Wd[gk] / 2
            lonk = np.abs(vxk * ny[gk] - vyk * nx[gk])
            al_lado = valid & (dl > 60.0) & (lonk <= 3.0)
            d_rama = np.where(al_lado, latk, 1e9).min(1)
            dz_rama = np.where(al_lado, np.abs(Z[gk] - Z[ii][:, None]), 0.0).max(1)
            # muestras de otro tramo (|ds| > 40) que PESAN en la mezcla (d - dmin < h) con otra cota
            dmin = np.where(valid, dk, 1e9).min(1)[:, None]
            h_k = max(H_MEZCLA * u_c, 1.5)
            pesa = valid & (dl > 40.0) & (dk - dmin < h_k) & (np.abs(Z[gk] - Z[ii][:, None]) > 1.0)
            s_mez = np.where(pesa, gk * paso, -1).max(1)
            dz_mez = np.where(pesa, np.abs(Z[gk] - Z[ii][:, None]), 0.0).max(1)
            a = 0
            while a < len(ii):
                if not malo[a]:
                    a += 1; continue
                b = a
                while b + 1 < len(ii) and malo[b + 1]:
                    b += 1
                if (b - a + 1) * paso >= 6.0:
                    m = a + int(np.argmax(np.abs(dev_c[a:b + 1])))
                    c = int(cel[m])
                    if not tierra[c]:
                        por = 'mar'
                    elif d_bri[c] <= 30.0:
                        por = 'viaducto'
                    elif terr_otro[c]:
                        por = 'otro ramal de la pista a %.0f m (corredor/muro 300 %%)' % d_otro_ramal[m]
                    elif pit_cut[c]:
                        por = 'corredor del pit lane (muro 300 %)'
                    elif mir_cut[c]:
                        por = 'banco del mirador'
                    elif d_rama[m] < AT * nt + 6.0:
                        por = 'otra rama del sector a %.0f m (< 21n+6 = %.0f m; dZ entre ramas %.1f m): cota mezclada' % (d_rama[m], AT * nt + 6.0, dz_rama[m])
                    elif s_mez[m] >= 0:
                        por = 'eje medial de curva interior: cota mezclada con s~%.0f (dZ %.1f m)' % (s_mez[m], dz_mez[m])
                    else:
                        por = 'sin causa clara'
                    tramos.append((k, int(ii[a] * paso), int(ii[b] * paso), round(float(dev_c[a:b + 1][np.argmax(np.abs(dev_c[a:b + 1]))]), 2), por))
                a = b + 1
        pct = 100.0 * n_ok_tot / max(n_tot, 1)
        cobertura.append(dict(id=sc['id'], pct_ok=round(pct, 1), puntos_pliegue=n_pliegue, tramos=tramos))
        print('  cobertura %-22s %5.1f%% de (muestra x terraza) aterrazado (%d puntos en pliegues de curva interior, no cuentan)%s'
              % (sc['id'], pct, n_pliegue, '' if not tramos else ':'))
        for (k, sa, sb, dv, por) in tramos:
            print('    terraza %d s %4d-%4d (%3d m) desvio %+.2f m: %s' % (k, sa, sb, sb - sa + int(paso), dv, por))
    checks['cobertura_sectores'] = cobertura
    # (e) GEOGRAFIA: el sentido de las terrazas (sube/baja) debe coincidir con el terreno natural
    # (z_land, antes de las reglas de pista) a 60 y 100 m del borde en el lado del sector
    geo = []
    for sc in sectores:
        s0, s1, lado, nt = float(sc['s0']), float(sc['s1']), int(sc['lado']), int(sc['n_terrazas'])
        sg = sentido_terrazas(sc)
        ii = idx_land[(s_land >= s0) & (s_land <= s1)]
        zl = z_land.reshape(nyg, nxg)
        med = {}
        for sd in (lado, -lado):
            for off in (60.0, 100.0):
                px = X[ii] + sd * nx[ii] * (Wd[ii] / 2 + off); py = Y[ii] + sd * ny[ii] * (Wd[ii] / 2 + off)
                med[(sd, off)] = float(np.median(map_coordinates(zl, [(py - gy0) / cell, (px - gx0) / cell], order=1, mode='nearest') - Z[ii]))
        natural_sube = med[(lado, 100.0)] > 3.0 and med[(lado, 100.0)] >= med[(lado, 60.0)] - 1.0
        natural_baja = med[(lado, 100.0)] < -3.0
        coherente = (sg > 0 and natural_sube) or (sg < 0 and natural_baja) or (not natural_sube and not natural_baja)
        # 'bastion': detras de la ultima terraza (que sube) el terreno CAE con una cara > 100 %
        # (desmonte a 49 grados al reves); el terraplen normal al 29 % no lo es
        o_b = AT * nt
        pa = [X[ii] + lado * nx[ii] * (Wd[ii] / 2 + o_b + 3.0), Y[ii] + lado * ny[ii] * (Wd[ii] / 2 + o_b + 3.0)]
        pb = [X[ii] + lado * nx[ii] * (Wd[ii] / 2 + o_b + 13.0), Y[ii] + lado * ny[ii] * (Wd[ii] / 2 + o_b + 13.0)]
        caida = (z_en(pa[0], pa[1]) - z_en(pb[0], pb[1])) / 10.0
        pct_bastion = 100.0 * float((caida > 1.0).mean()) if sg > 0 else 0.0
        # zigzag: el lado alto natural alterna entre ramas (horquillas del casino)
        px = X[ii] + lado * nx[ii] * (Wd[ii] / 2 + 60.0); py = Y[ii] + lado * ny[ii] * (Wd[ii] / 2 + 60.0)
        dz60 = map_coordinates(zl, [(py - gy0) / cell, (px - gx0) / cell], order=1, mode='nearest') - Z[ii]
        f_sube = 100.0 * float((dz60 > 3.0).mean()); f_baja = 100.0 * float((dz60 < -3.0).mean())
        zigzag = f_sube > 25.0 and f_baja > 25.0
        geo.append(dict(id=sc['id'], lado=lado, sube=sg > 0, natural_60=round(med[(lado, 60.0)], 1), natural_100=round(med[(lado, 100.0)], 1),
                        otro_lado_100=round(med[(-lado, 100.0)], 1), coherente=bool(coherente), zigzag=bool(zigzag), pct_bastion=round(pct_bastion, 1)))
        print('  geografia %-22s lado %+d %s | terreno natural - Z a 60/100 m: %+.0f/%+.0f (otro lado a 100 m: %+.0f) -> %s%s%s'
              % (sc['id'], lado, 'SUBE' if sg > 0 else 'BAJA', med[(lado, 60.0)], med[(lado, 100.0)], med[(-lado, 100.0)],
                 'coherente' if coherente else 'AVISO: el sentido NO coincide con la geografia',
                 ' (zigzag: el lado alto alterna entre ramas, %.0f%% sube / %.0f%% baja a 60 m)' % (f_sube, f_baja) if zigzag else '',
                 '' if pct_bastion < 10.0 else ' | AVISO bastion: cara > 100 %% detras de la ultima terraza en %.0f%% del sector' % pct_bastion))
    checks['geografia_sectores'] = geo
    # (f) FOSO detras de la ultima terraza (RONDA 15c): perfil o_fin-4..o_fin+40 cada 2 m de s;
    # foso = minimo < -1.5 m bajo la cota de la ultima terraza que luego rebota >= 2 m
    # RONDA 15c: profundidad de AGUA ATRAPADA en el perfil normal o_fin-3 .. o_fin+40 (cortado en la
    # zona de otro ramal / otra rama / mar / terrazas de otro sector, como el relleno): objetivo <= 1.5 m
    # en todas las muestras. Se informa tambien el criterio antiguo (minimo < -1.5 y rebote > 2).
    fosos = []
    for i_sc, sc in enumerate(sectores):
        s0, s1, lado, nt = float(sc['s0']), float(sc['s1']), int(sc['lado']), int(sc['n_terrazas'])
        o_fin = AT * nt
        ii = idx_land[(s_land >= s0) & (s_land <= s1)]
        if len(ii) == 0:
            continue
        oo, zz, val = perfiles_tras_terraza(zg, gx0, gy0, cell, X, Y, Wd, nx, ny, ii, lado, o_fin, 40.0,
                                            tree_land, idx_land, N, paso, half_land, ~es_mar_out, terr_mask, terr_sec, terr_g, i_sc)
        _, prof = nivel_agua(zz, val, None)
        pm = prof.max(1)
        con = pm > 1.5
        zr = zz - zz[:, :1]
        imin = np.argmin(np.where(val, zr, 1e9), axis=1)
        zmin = zr[np.arange(len(ii)), imin]
        reb = np.array([np.where(val[r, imin[r]:], zr[r, imin[r]:], -1e9).max() - zmin[r] for r in range(len(ii))])
        con_viejo = (zmin < -1.5) & (reb > 2.0)
        peor = int(np.argmax(pm))
        fosos.append(dict(id=sc['id'], muestras=int(len(ii)), con_foso=int(con.sum()), prof_max=round(float(pm.max()), 2),
                          s_peor=int(ii[peor] * paso), o_peor=round(float(oo[int(np.argmax(prof[peor]))] - o_fin), 1),
                          criterio_antiguo=int(con_viejo.sum()), largo_perfil_medio=round(float(val.sum(1).mean()), 1)))
        print('  foso tras la ultima terraza %-22s %3d de %3d muestras > 1.5 m (agua atrapada max %.2f m en s %d, o_fin%+.0f; '
              'criterio antiguo %d; perfil util medio %.0f m)'
              % (sc['id'], int(con.sum()), len(ii), pm.max(), fosos[-1]['s_peor'], fosos[-1]['o_peor'],
                 int(con_viejo.sum()), fosos[-1]['largo_perfil_medio']))
    checks['foso_sectores'] = fosos
    checks['foso_celdas_rellenadas'] = n_foso_rell
    # (g) PENON DEL CASINO (RONDA 15c): terreno sobre el contorno de zona_casino()
    if el_casino is not None:
        cxe, cye, a_e, b_e, ang_e = el_casino
        kk = np.arange(64)
        a_ = 2 * np.pi * kk / 64
        ex_, ey_ = a_e * np.cos(a_), b_e * np.sin(a_)
        pcx = cxe + ex_ * math.cos(ang_e) - ey_ * math.sin(ang_e); pcy = cye + ex_ * math.sin(ang_e) + ey_ * math.cos(ang_e)
        zc = z_en(pcx, pcy)
        angc = np.degrees(np.arctan2(pcy - cye, pcx - cxe))
        en_bah = (angc >= CASINO_BAHIA[0]) & (angc <= CASINO_BAHIA[1])
        cv = {int(c['n']): c for c in curvas if 'n' in c}
        q37 = int(cv[36]['s_idx']) if 36 in cv and 's_idx' in cv[36] else None
        ent = None; z_ent = None; d_cumbre = None
        if q37 is not None:
            ke = int(np.argmin((pcx - X[q37]) ** 2 + (pcy - Y[q37]) ** 2))
            ent = (round(float(pcx[ke]), 1), round(float(pcy[ke]), 1))
            z_ent = round(float(zc[ke]), 1)
            if cumbres_tmp := _cumbres(zg, GX, GY, cell):
                d_cumbre = round(min(math.hypot(c[0] - ent[0], c[1] - ent[1]) for c in cumbres_tmp), 0)
        checks['casino'] = dict(centro=(round(cxe, 1), round(cye, 1)), contorno_z_min=round(float(zc.min()), 1),
                                contorno_z_max=round(float(zc.max()), 1), contorno_en_mar=int((zc < 0.5).sum()),
                                bahia_puntos=int(en_bah.sum()), bahia_en_mar=int((zc[en_bah] < 0.5).sum()),
                                ladera_z_max=round(float(zc[~en_bah].max()), 1), entrada=ent, z_terreno_entrada=z_ent,
                                z_pista_entrada=round(float(Z[q37]), 1) if q37 is not None else None, cumbre_mas_cercana_m=d_cumbre)
        print('  PENON DEL CASINO: contorno z %.1f..%.1f, %d/64 puntos en el mar (bahia: %d/%d), ladera (tierra) max %.1f (tope %.0f); '
              'entrada %s terreno %s (pista C37 %s); cumbre mas cercana a %s m'
              % (zc.min(), zc.max(), int((zc < 0.5).sum()), int((zc[en_bah] < 0.5).sum()), int(en_bah.sum()), zc[~en_bah].max(),
                 CASINO_Z_LADERA, ent, z_ent, checks['casino']['z_pista_entrada'], d_cumbre))
        # RONDA 15c: ninguna celda DENTRO del contorno por encima del tope bajo la roca (el relleno de fosos y las
        # terrazas no pueden levantar el solar del penon); el corredor de la rotonda (a < w/2+30 del asfalto) no cuenta
        dentro = (r_cas < 1.0) & (d_land > half_c + 30.0)
        sobre = dentro & (z_grid > np.maximum(cap_cas, 0.0) + 0.1)      # (el fondo del mar a -4 no cuenta)
        checks['casino']['celdas_dentro_sobre_tope'] = int(sobre.sum())
        print('    contorno del penon: %d celdas dentro de la elipse (fuera del corredor) por encima del tope bajo la roca%s'
              % (int(sobre.sum()), (' (p.ej. ' + ', '.join('(%.0f, %.0f) z %.1f tope %.1f' % (gpts[c_, 0], gpts[c_, 1], z_grid[c_], cap_cas[c_])
                                                            for c_ in np.where(sobre)[0][::max(1, int(sobre.sum()) // 4)][:4]) + ')') if sobre.any() else ''))

    # --- extras: mascara de roca y cumbres ---
    pendiente = _pendiente(zg, cell)
    # v1 (revision C-15/D14/E8/J12/I4): la mascara marcaba roca en laderas naturales de hierba (> 50 %) y toda la cupula
    # > 165 m, con un desenfoque de 6 m: velo gris borroso ('montana que no se distingue'). Ahora roca = desmontes y
    # acantilados (> 85 %) y cumbres > 185 m con pendiente > 50 %, desenfoque de 1 celda; los desmontes de la pista (rebajados
    # por una regla dura a < 25 m del asfalto y > 80 %) son roca entera; al pie de los acantilados la roca se prolonga una
    # celda en el agua (antes 0 en el mar: dientes de hierba a ras del agua)
    # v2 (revision A-r2-12/A-r2-07): en los CORTES (desmonte) la roca ya no es el booleano 'pendiente > 0.8 a < 25 m' (rombos
    # sueltos de 1.0 entre 0.05 en la cuneta, tajo gris entero detras del hotel) sino la PROFUNDIDAD del corte (1 -> 4 m) por
    # la pendiente (umbral 0.75 +- 0.1 con ruido de 30 m), desenfocada 1.5 celdas: afloramientos irregulares, hierba en el
    # pie y en las costillas. Fuera de los cortes (acantilados y laderas naturales), la regla v1 con el mismo umbral ruidoso
    _nr = ruido_valor(np.random.default_rng(seed + 43), nyg, nxg, cell, 30.0)
    _dsm = desmonte.reshape(nyg, nxg)
    # v3 (revision N1 (1)/C-15): en las laderas NATURALES (ni acantilado de costa ni corte) el umbral puntual 0.85 +- 0.1 caia
    # justo en la pendiente de las caras del limitador (80-88 %): manchas grises de 30-80 m al azar (22 % de la cara N,
    # 'camuflaje'). Ahi la roca sale de la pendiente SUAVIZADA (2.5 celdas) > 1.0 + 0.1*ruido, con apertura 3x3 y sin manchas
    # de menos de 12 celdas: solo afloramientos grandes y continuos. Acantilados de costa y cumbres > 185 m, como en v1
    _acg = acantilado.reshape(nyg, nxg)
    # F1 (bloque 2.2): umbral natural 1.0 +- 0.1 -> ROCA_UMBRAL_PEND +- ROCA_UMBRAL_RUIDO (34-39 grados; plan: roca a partir de
    # 35-40 grados), suavizado ROCA_SIGMA_CELDAS, misma apertura 3x3 y tamano minimo ROCA_MIN_CELDAS (sin 'camuflaje')
    _pend_s = gaussian_filter(pendiente, ROCA_SIGMA_M / cell)
    _nat_r = (_pend_s > ROCA_UMBRAL_PEND + ROCA_UMBRAL_RUIDO * _nr) & ~_acg & ~_dsm
    _nat_r = binary_opening(_nat_r, structure=np.ones((3, 3), bool))
    _lab_r, _n_r = _label(_nat_r)
    if _n_r:
        _tam_r = np.bincount(_lab_r.ravel()); _peq = _tam_r < ROCA_MIN_CELDAS; _peq[0] = False
        _nat_r &= ~_peq[_lab_r]
    roca = ((_nat_r | ((pendiente > 0.85 + 0.1 * _nr) & _acg) | ((zg > 185.0) & (pendiente > 0.5))) & ~_dsm).astype(float)
    # v3 (revision H3): en la arista de los acantilados (pendiente > 1.5 a < 8 m) el limite hierba/roca colgaba en triangulos
    # verdes por la cara: ahi el desenfoque es de 2 celdas (isolinea 0.5 mas suave); en el resto, 1 como antes
    _cerca_ar = binary_dilation(pendiente > 1.5, iterations=2)
    roca = np.clip((np.where(_cerca_ar, gaussian_filter(roca, 2.0), gaussian_filter(roca, 1.0)) - 0.2) / 0.4, 0.0, 1.0)
    _corte = (np.clip((z_land.reshape(nyg, nxg) - zg - 1.0) / 3.0, 0.0, 1.0)
              * np.clip((pendiente - (ROCA_CORTE_PEND + 0.1 * _nr)) / 0.3, 0.0, 1.0) * _dsm)
    roca = np.maximum(roca, np.clip(gaussian_filter(_corte, 1.5) * 1.25, 0.0, 1.0))
    # (la mascara v2, para dejar EXACTAMENTE como estaba el material de la rotonda Loews: a < R_LOEWS_INTACTA de su centro)
    _roca_v2 = (((pendiente > 0.85 + 0.1 * _nr) | ((zg > 185.0) & (pendiente > 0.5))) & ~_dsm).astype(float)
    _roca_v2 = np.maximum(np.clip((gaussian_filter(_roca_v2, 1.0) - 0.2) / 0.4, 0.0, 1.0),
                          np.clip(gaussian_filter(_corte, 1.5) * 1.25, 0.0, 1.0))
    _mar2 = es_mar_out.reshape(nyg, nxg)
    # (N2-A: en el lungomare la roca no se prolonga en el agua: la orilla es de hierba/arena)
    roca = np.where(_mar2 & ~_lungo.reshape(nyg, nxg), grey_dilation(roca, size=(3, 3)), roca)
    roca[_mar2 & (zg < -3.5)] = 0.0
    _roca_v2 = np.where(_mar2 & ~_lungo.reshape(nyg, nxg), grey_dilation(_roca_v2, size=(3, 3)), _roca_v2)
    _roca_v2[_mar2 & (zg < -3.5)] = 0.0
    # v3 (revision I4 (b)): al pie de los acantilados las celdas de TIERRA a ras de agua (z < 3) tenian atributo 0.39-0.67 y, con
    # el ruido del material, salia una fila de dientes verdes (uno por celda): pie de derrubios = roca entera
    _pie = (~_mar2 & (zg < 3.0) & binary_dilation(_mar2, structure=np.ones((3, 3), bool), iterations=2)
            & (grey_dilation((pendiente > 0.85).astype(float), size=(5, 5)) > 0) & ~_lungo.reshape(nyg, nxg))
    checks['pie_acantilado_celdas'] = int(_pie.sum())
    roca[_pie] = 1.0
    # v3 (revision G10): en la orilla de la garganta del viaducto (d_bri < 60) el ultimo escalon tierra -> mar (8-16 m) se pintaba
    # de hierba: las celdas de tierra junto al agua con z > 8 m son roca
    _g10 = (~_mar2 & binary_dilation(_mar2, structure=np.ones((3, 3), bool)) & (zg > 8.0)
            & (d_bri.reshape(nyg, nxg) < 60.0) & (d_loews.reshape(nyg, nxg) > R_LOEWS_CONG[1]))
    checks['garganta_escalon_roca_celdas'] = int(_g10.sum())
    roca[_g10] = 1.0
    # F1 (bloque 2.2): PIE DE DERRUBIOS: banda de ROCA_PIE_M[0]..[1] m ladera ABAJO de cada afloramiento (celdas de tierra a
    # < 10 m de roca > 0.5 que estan por debajo de esa roca y no son roca) a ROCA_PIE_VALOR en la mascara (y 'tierra' en las capas)
    _r_alta = roca > 0.5
    _n_pie = int(round(ROCA_PIE_M[1] / cell))
    _zr = np.where(_r_alta, zg, -1e9)
    _zr_max = maximum_filter(_zr, size=2 * _n_pie + 1)
    _pie_d = ~_r_alta & ~_mar2 & (_zr_max > -1e8) & (zg < _zr_max - 1.0) & (roca < ROCA_PIE_VALOR) & ~_lungo.reshape(nyg, nxg)
    checks['roca_pie_derrubios_celdas'] = int(_pie_d.sum())
    roca = np.where(_pie_d, ROCA_PIE_VALOR, roca)
    _lo2 = (d_loews < R_LOEWS_INTACTA).reshape(nyg, nxg)
    roca = np.where(_lo2, _roca_v2, roca)
    # F1 r4: la isla de la cima (cupula) no lleva roca: sin frontera de material sobre el flanco no hay dientes por cara (postal 56)
    # (la isla con techo impuesto, sin el anillo de fundido del extremo sur; r4b: y sin la pared sur de la rama baja, que es la de r3
    # con su roca: la ve la toma 51 a la derecha y desde 56 es cara trasera)
    _isla56_2 = (_wroca56 > 0.3).reshape(nyg, nxg)
    checks['cupula_roca_quitada_celdas'] = int((_isla56_2 & (roca > 0.49)).sum())
    roca = np.where(_isla56_2, 0.0, roca)
    cumbres = _cumbres(zg, GX, GY, cell)
    # F1 (bloque 1.6): CAPAS para la mascara por texel (R matorral, G hierba seca, B tierra, A roca), 0..1 y suma 1 por celda.
    # roca = mascara_roca o pendiente suavizada > umbral; tierra = pie de derrubios, bermas de la tierra (< 8 m del borde en
    # 'dirt'), caras de corte someras (cortes < umbral de roca) y la orilla (playa < 8 m, z < 3); hierba seca = llanos
    # (pendiente < CAPAS_LLANO_PEND) a < CAPAS_HIERBA_D_PISTA de la pista y z < CAPAS_HIERBA_Z, terrazas del pueblo y la vega
    # baja (z < 25); matorral = el resto (laderas, macizo, cumbres). Bordes con ruido de CAPAS_RUIDO_M (nunca por celda)
    _nc2 = ruido_valor(np.random.default_rng(seed + 83), nyg, nxg, cell, CAPAS_RUIDO_M)
    _nc3 = ruido_valor(np.random.default_rng(seed + 89), nyg, nxg, cell, 3.0 * CAPAS_RUIDO_M)
    _d_pista = d_land.reshape(nyg, nxg); _dedge2 = dedge0.reshape(nyg, nxg)
    # F1 r4: con CAPAS_PIE_FUERA_DE_A el PIE DE DERRUBIOS (mascara_roca = ROCA_PIE_VALOR 0.5) no entra en el canal A (r4b: apagado,
    # ver la constante). Nunca roca en la cupula de la isla de la cima (_isla56_2)
    _cap_roca = np.maximum(np.where((_pie_d & CAPAS_PIE_FUERA_DE_A) | _isla56_2, 0.0, roca),
                           np.clip((_pend_s - (ROCA_UMBRAL_PEND + ROCA_UMBRAL_RUIDO * _nr)) / 0.12, 0.0, 1.0) * ~_mar2 * ~_isla56_2)
    _cap_roca = np.clip(_cap_roca, 0.0, 1.0)
    _dirt_c = _dirt_s[g_near].reshape(nyg, nxg)
    _berma_t = _dirt_c & (_dedge2 < CAPAS_DIRT_BORDE_M) & ~_mar2
    # F1 r2 (director r1, toma 36: la ladera del penon partida en dos tonos con frontera dura en la cresta): el corte somero (canal B)
    # ya no es un booleano (_dsm & pendiente > 0.35) sino un peso continuo con ruido de 10-30 m en la pendiente (+-0.08) y en la
    # profundidad del corte (umbral 0.5-2.5 m): la frontera dorado/tierra serpentea y se funde en 2-3 celdas
    _nc4 = ruido_valor(np.random.default_rng(seed + 107), nyg, nxg, cell, 0.75 * CAPAS_RUIDO_M)
    _prof_corte = (z_land.reshape(nyg, nxg) - zg)
    _corte_suave = (np.clip((pendiente - (0.35 + 0.08 * _nc4)) / 0.15, 0.0, 1.0)
                    * np.clip((_prof_corte - (1.5 + 1.0 * _nc4)) / 1.5, 0.0, 1.0) * np.clip((0.5 - _cap_roca) / 0.3, 0.0, 1.0)
                    * ~_isla56_2)        # F1 r4: la cupula de la cima es hierba seca/matorral, no 'tierra' de corte
    _playa = (~_mar2 & (_sdf.reshape(nyg, nxg) < 8.0) & (zg < 3.0))
    _cap_tierra = np.clip(np.maximum.reduce([np.where(_pie_d, 0.85, 0.0), np.where(_berma_t, 0.9, 0.0),
                                             0.6 * _corte_suave, np.where(_playa, 0.7, 0.0)])
                          + 0.15 * _nc2, 0.0, 1.0) * (1.0 - _cap_roca)
    _w_llano = np.clip((CAPAS_LLANO_PEND + 0.1 + 0.08 * _nc3 - _pend_s) / 0.2, 0.0, 1.0)
    _w_cerca = np.clip((CAPAS_HIERBA_D_PISTA + 20.0 + 15.0 * _nc3 - _d_pista) / 40.0, 0.0, 1.0)
    _w_bajo = np.clip((CAPAS_HIERBA_Z + 15.0 + 10.0 * _nc3 - zg) / 30.0, 0.0, 1.0)
    _w_vega = np.clip((25.0 - zg) / 15.0, 0.0, 1.0) * _w_llano
    _w_alto = np.clip((CAPAS_MATORRAL_Z - zg) / 30.0, 0.0, 1.0)
    _cap_hierba = np.clip(np.maximum.reduce([_w_llano * _w_cerca * _w_bajo, _w_vega * 0.8,
                                             terr_mask.reshape(nyg, nxg).astype(float)]) + 0.1 * _nc2, 0.0, 1.0)
    _cap_hierba = _cap_hierba * _w_alto * (1.0 - _cap_roca) * (1.0 - _cap_tierra)
    _cap_mat = np.clip(1.0 - _cap_roca - _cap_tierra - _cap_hierba, 0.0, 1.0)
    _suma = np.maximum(_cap_roca + _cap_tierra + _cap_hierba + _cap_mat, 1e-6)
    capas = {'matorral': (_cap_mat / _suma).ravel(), 'hierba_seca': (_cap_hierba / _suma).ravel(),
             'tierra': (_cap_tierra / _suma).ravel(), 'roca': (_cap_roca / _suma).ravel()}
    _tierra_c = (~_mar2 & (zg > 0.5))
    checks['capas_media_pct'] = {k: round(100.0 * float(v.reshape(nyg, nxg)[_tierra_c].mean()), 1) for k, v in capas.items()}

    # --- verificaciones ---
    def z_en(xq, yq):
        return map_coordinates(zg, [(np.asarray(yq) - gy0) / cell, (np.asarray(xq) - gx0) / cell], order=1, mode='nearest')
    li = idx_land
    zp = z_en(X[li] + nx[li] * (Wd[li] / 2 + 25.0), Y[li] + ny[li] * (Wd[li] / 2 + 25.0))
    zm = z_en(X[li] - nx[li] * (Wd[li] / 2 + 25.0), Y[li] - ny[li] * (Wd[li] / 2 + 25.0))
    pared = (zp > Z[li] + 8.0) | (zm > Z[li] + 8.0)
    checks['pct_pista_con_pared_roca'] = round(100.0 * float(pared.mean()), 1)
    # F1 (bloque 1.1/2.2): KPIs del tramo de tierra y de la roca por pendiente (los mide tambien _rev/medir_relieve.py)
    _en_tierra = (s_land >= TIERRA_S[0]) & (s_land <= TIERRA_S[1])
    zp50 = z_en(X[li] + nx[li] * (Wd[li] / 2 + 50.0), Y[li] + ny[li] * (Wd[li] / 2 + 50.0))
    zm50 = z_en(X[li] - nx[li] * (Wd[li] / 2 + 50.0), Y[li] - ny[li] * (Wd[li] / 2 + 50.0))
    _pyc25 = ((zp > Z[li] + 8.0) & (zm < Z[li] - 8.0)) | ((zm > Z[li] + 8.0) & (zp < Z[li] - 8.0))
    _pyc50 = ((zp50 > Z[li] + 8.0) & (zm50 < Z[li] - 8.0)) | ((zm50 > Z[li] + 8.0) & (zp50 < Z[li] - 8.0))
    if _en_tierra.any():
        checks['pared_y_caida_25m_pct'] = round(100.0 * float(_pyc25[_en_tierra].mean()), 1)
        checks['pared_y_caida_50m_pct'] = round(100.0 * float(_pyc50[_en_tierra].mean()), 1)
        checks['pct_pista_con_pared_roca_tierra'] = round(100.0 * float(pared[_en_tierra].mean()), 1)
        checks['caida_25m_pct_tierra'] = round(100.0 * float(((zp < Z[li] - 8.0) | (zm < Z[li] - 8.0))[_en_tierra].mean()), 1)
    _t35 = _tierra_c & (pendiente > 0.70)
    checks['celdas_35_roca_pct'] = round(100.0 * float((roca[_t35] > 0.49).mean()), 1) if _t35.any() else 0.0
    checks['celdas_35_pct_tierra'] = round(100.0 * float(_t35.sum() / max(int(_tierra_c.sum()), 1)), 1)
    checks['erosion_corredor_dz_max'] = 0.0          # la erosion hidraulica es F4 (erosion.py): hoy no mueve nada
    en_terr = np.zeros(len(li), bool)
    for sc in spec_urb.get('sectores', []):
        en_terr |= (s_land >= float(sc['s0']) - 10) & (s_land <= float(sc['s1']) + 10)
    checks['pct_pared_fuera_terrazas'] = round(100.0 * float(pared[~en_terr].mean()), 1) if (~en_terr).any() else 0.0
    checks['pct_pared_lado_mas1'] = round(100.0 * float((zp > Z[li] + 8.0).mean()), 1)
    checks['pct_pared_lado_menos1'] = round(100.0 * float((zm > Z[li] + 8.0).mean()), 1)
    # terreno bajo el eje y bajo los bordes del asfalto (muestras en tierra, fuera
    # de los 40 m de cada estribo): nunca mas de 1.2 m por debajo de la rasante
    if tree_bridge is not None:
        d_est = tree_bridge.query(np.column_stack([X[li], Y[li]]))[0]
    else:
        d_est = np.full(len(li), 1e9)
    lejos_est = d_est > 4.0          # v1 (I1): antes 40 m: la QA no veia la zanja de 3 m de los estribos
    z_eje = z_en(X[li], Y[li])
    z_b1 = z_en(X[li] + nx[li] * Wd[li] / 2, Y[li] + ny[li] * Wd[li] / 2)
    z_b2 = z_en(X[li] - nx[li] * Wd[li] / 2, Y[li] - ny[li] * Wd[li] / 2)
    hueco = np.minimum(np.minimum(z_eje, z_b1), z_b2) - Z[li]
    checks['muestras_terreno_bajo_eje_1p2'] = int(((z_eje < Z[li] - 1.2) & lejos_est).sum())
    # v2: cuantas salen solo por la garantia de hierba (vertices BAJO la calzada, tapados por el asfalto: no son un hueco)
    _zph = z_pre_h.reshape(nyg, nxg)
    _zeh = map_coordinates(_zph, [(Y[li] - gy0) / cell, (X[li] - gx0) / cell], order=1, mode='nearest')
    checks['muestras_bajo_eje_por_garantia_hierba'] = int(((z_eje < Z[li] - 1.2) & (_zeh >= Z[li] - 1.2) & lejos_est).sum())
    checks['muestras_terreno_bajo_bordes_1p2'] = int((((z_b1 < Z[li] - 1.2) | (z_b2 < Z[li] - 1.2)) & lejos_est).sum())
    checks['hueco_bajo_pista_min'] = round(float(hueco[lejos_est].min()), 2)
    checks['hueco_bajo_pista_s_peor'] = int(li[lejos_est][int(np.argmin(hueco[lejos_est]))] * paso)
    checks['pendiente_max'] = round(float(pendiente.max()), 2)
    # 'natural' = tierra lejos de la pista (> 80 m), del mar (> 40 m) y del
    # viaducto, SIN las caras de acantilado ni de desmonte (unicas > 100 % admitidas)
    # v2: la QA usa la distancia al mar REAL (con el mar forzado bajo la roca del penon; la regla de costa usa la de J2-02)
    _dmq = distance_transform_edt(coastF.reshape(nyg, nxg) < 0.5).ravel() * cell
    nat = ((d_land > 80.0) & (_dmq > 40.0) & (d_bri > 120.0) & tierra & ~acantilado & ~obra).reshape(nyg, nxg)
    pn = pendiente[nat]
    checks['pendiente_max_natural'] = round(float(pn.max()), 2) if pn.size else 0.0
    if pn.size:
        _kn = np.where(nat.ravel())[0][int(np.argmax(pn))]
        checks['pendiente_max_natural_xy'] = (round(float(gpts[_kn, 0]), 1), round(float(gpts[_kn, 1]), 1))
    checks['pendiente_p95_natural'] = round(float(np.percentile(pn, 95)), 2) if pn.size else 0.0
    checks['pct_natural_25_60'] = round(100.0 * float(((pn >= 0.25) & (pn <= 0.6)).mean()), 1) if pn.size else 0.0
    checks['pct_natural_gt_100'] = round(100.0 * float((pn > 1.0).mean()), 2) if pn.size else 0.0
    # criterio del revisor (incluye cimas de acantilado y desmontes lejanos)
    mac = ((d_land > 80.0) & (dist_mar > 40.0) & tierra).reshape(nyg, nxg) & (zg > 40.0)
    pm = pendiente[mac]
    checks['macizo_mediana'] = round(float(np.median(pm)), 2) if pm.size else 0.0
    checks['macizo_pct_60_100'] = round(100.0 * float(((pm > 0.6) & (pm <= 1.0)).mean()), 1) if pm.size else 0.0
    checks['macizo_pct_gt_100'] = round(100.0 * float((pm > 1.0).mean()), 2) if pm.size else 0.0
    bajo_asf = tierra & (d_land < half_c)
    checks['celdas_invaden_pista'] = int((bajo_asf & (z_grid > Z_land[i_land] - 0.3)).sum())
    if tree_bridge is not None:
        hb = Wd[~no_bridge][i_bri] / 2
        checks['celdas_invaden_viaducto'] = int((tierra & (d_bri < hb) & (d_bri <= d_land) & (z_grid > Z[~no_bridge][i_bri] - 1.0)).sum())
    checks['corredor_celdas_dos_ramales'] = n_dobles
    checks['protegido_bajo_mar'] = int((protegido & es_mar_out & ~mar_forzado & ~garganta).sum())
    checks['protegido_bajo_cero'] = int((prot_tierra & (z_grid < 0.0)).sum())
    if checks['protegido_bajo_cero']:
        checks['protegido_bajo_cero_xy'] = [(round(float(gpts[c_, 0])), round(float(gpts[c_, 1])), round(float(z_grid[c_]), 2))
                                            for c_ in np.where(prot_tierra & (z_grid < 0.0))[0][:6]]
        print('  (protegida bajo cota 0 en %s)' % checks['protegido_bajo_cero_xy'])
    checks['tierra_bajo_cero'] = int((tierra & (z_grid < 0.0)).sum())
    # borde de la rejilla: mar o cota <= 2 m
    bz = np.concatenate([zg[0, :], zg[-1, :], zg[:, 0], zg[:, -1]])
    bm = np.concatenate([es_mar_out.reshape(nyg, nxg)[0, :], es_mar_out.reshape(nyg, nxg)[-1, :],
                         es_mar_out.reshape(nyg, nxg)[:, 0], es_mar_out.reshape(nyg, nxg)[:, -1]])
    checks['borde_pct_mar'] = round(100.0 * float(bm.mean()), 1)
    checks['borde_z_max_tierra'] = round(float(bz[~bm].max()), 2) if (~bm).any() else -4.0
    ss = np.arange(400.0, 621.0, 10.0)
    ii = (ss / paso).astype(int) % N
    pcx = X[ii] - nx[ii] * (Wd[ii] / 2 + 120.0); pcy = Y[ii] - ny[ii] * (Wd[ii] / 2 + 120.0)
    zc = z_en(pcx, pcy)
    zc90 = z_en(X[ii] - nx[ii] * (Wd[ii] / 2 + 90.0), Y[ii] - ny[ii] * (Wd[ii] / 2 + 90.0))
    checks['coche_120m_min'] = round(float(zc.min()), 1)
    checks['coche_120m_max'] = round(float(zc.max()), 1)
    checks['coche_120m_pct_ge_90'] = round(100.0 * float((zc >= 90.0).mean()), 1)
    checks['coche_120m_s_ge_90'] = [int(s) for s, zz in zip(ss, zc) if zz >= 90.0]
    checks['coche_90m_pct_ge_90'] = round(100.0 * float((zc90 >= 90.0).mean()), 1)
    # RONDA 15c: el punto a 120 m cae DENTRO de la banda de terrazas de pueblo_subida_ladera
    # (la tecnica vuelve a pasar a 100-130 m detras del tunel): ahi la clausula del plan es
    # incompatible con el spec (s0 = 660) y no se puede cumplir
    en_banda = np.zeros(len(ii), bool)
    for sc in spec_urb.get('sectores', []):
        jj = idx_land[(s_land >= float(sc['s0'])) & (s_land <= float(sc['s1']))]
        if len(jj) == 0:
            continue
        d_b, k_b = cKDTree(np.column_stack([X[jj], Y[jj]])).query(np.column_stack([pcx, pcy]))
        en_banda |= (d_b - Wd[jj[k_b]] / 2) < AT * int(sc['n_terrazas']) + TM
    checks['coche_120m_puntos_en_terrazas'] = [int(s) for s, b in zip(ss, en_banda) if b]
    checks['coche_120m_pct_ge_90_fuera_terrazas'] = round(100.0 * float((zc[~en_banda] >= 90.0).mean()), 1) if (~en_banda).any() else 0.0
    checks['z_max'] = round(float(zg.max()), 1)
    checks['mar_pct'] = round(100.0 * float(es_mar_out.mean()), 1)
    checks['cumbres'] = cumbres
    checks['rejilla'] = (nxg, nyg, cell)
    print('terreno (macizo): %dx%d celdas de %.0f m | mar %.0f%% | z max %.1f m | cumbres: %s'
          % (nxg, nyg, cell, checks['mar_pct'], checks['z_max'],
             ', '.join('(%.0f,%.0f) %.0f m' % c for c in cumbres[:8])))
    print('  pared de roca (> z_pista+8 a 25 m) en algun lado: %.1f%% de la pista en tierra (lado +1 %.1f%%, lado -1 %.1f%%; '
          'fuera de los sectores de terrazas %.1f%%)'
          % (checks['pct_pista_con_pared_roca'], checks['pct_pared_lado_mas1'], checks['pct_pared_lado_menos1'],
             checks['pct_pared_fuera_terrazas']))
    print('  F1 tierra tallada (s %.0f-%.0f): pared Y caida a 25 m %.1f%% (a 50 m %.1f%%), pared en algun lado %.1f%%, caida en algun '
          'lado %.1f%%; muestras con lado alto definido %d (lado +1 en %.0f%%); celdas levantadas (ladera) %d (max %.1f m), '
          'rebajadas (caida) %d (max %.1f m), lomo minimo %d celdas, costillas en la cara del lomo %d celdas | roca: %.1f%% de las '
          'celdas de tierra > 35 grados (%.1f%% de la tierra) llevan roca; pie de derrubios %d celdas | capas (media %% en tierra): %s'
          % (TIERRA_S[0], TIERRA_S[1], checks.get('pared_y_caida_25m_pct', 0.0), checks.get('pared_y_caida_50m_pct', 0.0),
             checks.get('pct_pista_con_pared_roca_tierra', 0.0), checks.get('caida_25m_pct_tierra', 0.0),
             checks['tierra_tallada_muestras'], checks['tierra_tallada_lado_mas1_pct'], checks['tierra_tallada_celdas_ladera'],
             checks['tierra_tallada_ladera_max_m'], checks['tierra_tallada_celdas_caida'], checks['tierra_tallada_caida_max_m'],
             checks.get('tierra_tallada_celdas_lomo_minimo', 0), checks.get('costillas_relleno_celdas', 0),
             checks['celdas_35_roca_pct'], checks['celdas_35_pct_tierra'], checks['roca_pie_derrubios_celdas'],
             checks['capas_media_pct']))
    if checks.get('cupula'):
        _cu = checks['cupula']
        _pi56 = pendiente[_isla56_2 & (dedge0.reshape(nyg, nxg) > 6.0)]
        print('  F1 r4 cupula de la cima (apex s %d, rasante %.1f): isla %d celdas, rebajadas %d (max %.1f m), rellenadas %d (max %.1f m), '
              'cumbre %.1f -> %.1f m; pendiente en la isla max %.2f, > 30 grados %.0f%%, > 42 grados %.0f%%, > 45 grados %.0f%%; '
              'roca quitada en la isla %d celdas | r4b: cupula %d celdas, loma sur = r3 %d, sin roca %d'
              % (_cu['apex_s'], _cu['z_apex_pista'], _cu['celdas_isla'], _cu['celdas_rebajadas'], _cu['rebaje_max_m'], _cu['celdas_rellenadas'],
                 _cu['relleno_max_m'], _cu['cumbre_z_antes'], _cu['cumbre_z'], float(_pi56.max()) if _pi56.size else 0.0,
                 100.0 * float((_pi56 > 0.577).mean()) if _pi56.size else 0.0, 100.0 * float((_pi56 > 0.90).mean()) if _pi56.size else 0.0,
                 100.0 * float((_pi56 > 1.0).mean()) if _pi56.size else 0.0, checks['cupula_roca_quitada_celdas'],
                 _cu.get('celdas_cupula', 0), _cu.get('celdas_loma_sur_r3', 0), _cu.get('celdas_sin_roca', 0)))
    print('  pendiente max: %.2f (natural lejos de pista/costa: max %.2f en %s, p95 %.2f, %.0f%% entre 25 y 60%%, %.2f%% > 100%%; '
          'macizo z>40: mediana %.2f, %.0f%% en 60-100%%, %.2f%% > 100%%) | limitador: %d it, rebaje max %.1f m'
          % (checks['pendiente_max'], checks['pendiente_max_natural'], checks.get('pendiente_max_natural_xy'), checks['pendiente_p95_natural'],
             checks['pct_natural_25_60'], checks['pct_natural_gt_100'], checks['macizo_mediana'],
             checks['macizo_pct_60_100'], checks['macizo_pct_gt_100'], checks['limitador_iteraciones'],
             checks['limitador_rebaje_max']))
    print('  celdas que invaden la pista: %d (viaducto: %s) | corredor: %d celdas al minimo de dos ramales'
          % (checks['celdas_invaden_pista'], checks.get('celdas_invaden_viaducto', 'n/a'), n_dobles))
    print('  terreno bajo la rasante (muestras en tierra lejos de estribos): eje < Z-1.2: %d (%d solo por la garantia de hierba, bajo el '
          'asfalto), bordes < Z-1.2: %d, hueco min %.2f m en s %d'
          % (checks['muestras_terreno_bajo_eje_1p2'], checks['muestras_bajo_eje_por_garantia_hierba'], checks['muestras_terreno_bajo_bordes_1p2'],
             checks['hueco_bajo_pista_min'], checks['hueco_bajo_pista_s_peor']))
    print('  terrazas: %d celdas llanas (llanas de un sector protegidas del fundido de otro: %d; recortadas por la caja del pit: %d; talud entre ramas: %d) | '
          'foso rellenado tras la ultima terraza: %d celdas (> 1.5 m) | lagunas eliminadas: %d'
          % (n_terr, n_conf, n_terr_pit, int(terr_mix.sum()), n_foso_rell, n_lagunas))
    print('  explanada llana tras el pit lane (punto, m): %s'
          % ', '.join('%d:%.0f' % e for e in explanada))
    print('  miradores (s0, s1, lado, banco aplicado, mar a ese lado m, mar al otro lado m): %s' % mir_ok)
    print('  tierra protegida bajo el mar: %d | protegida bajo cota 0: %d | tierra (no mar) bajo cota 0: %d | borde: %.0f%% mar, z max en tierra %.1f'
          % (checks['protegido_bajo_mar'], checks['protegido_bajo_cero'], checks['tierra_bajo_cero'],
             checks['borde_pct_mar'], checks['borde_z_max_tierra']))
    print('  macizo a 120 m detras del coche (s 400-620, lado -1): min %.0f max %.0f m, >= 90 m en %.0f%% (s: %s); a 90 m >= 90 en %.0f%%'
          % (checks['coche_120m_min'], checks['coche_120m_max'], checks['coche_120m_pct_ge_90'], checks['coche_120m_s_ge_90'],
             checks['coche_90m_pct_ge_90']))
    print('    el punto a 120 m cae dentro de la banda de terrazas de la tecnica (incompatible con el spec) en s: %s; fuera de ellas >= 90 m en %.0f%%'
          % (checks['coche_120m_puntos_en_terrazas'], checks['coche_120m_pct_ge_90_fuera_terrazas']))

    res = dict(x0=gx0, y0=gy0, cell=cell, nx=nxg, ny=nyg, z_grid=z_grid, es_mar=es_mar_out,
               extras={'cumbres': cumbres, 'mascara_roca': roca.ravel(), 'checks': checks,
                       'protegido': protegido, 'coastF': coastF, 'terrazas': terr_mask,
                       'acantilado': acantilado, 'desmonte': desmonte, 'obra': obra, 'techo': techo, 'suelo': suelo,
                       'costuras_dz': dz_map.ravel(), 'talud_ramas_dz': tal_map.ravel(), 'terrazas_k': terr_k, 'terrazas_sec': terr_sec,
                       'terrazas_rampa': terr_rampa, 'terrazas_mix': terr_mix, 'casino': checks.get('casino'),
                       'casino_elipse': el_casino, 'zona_coche': zona_coche,
                       # F1: capas de la mascara por texel (preparar_geometria las escribe en geometria_3d.json), terreno
                       # natural antes de las reglas de pista y pendiente final (QA y medir_relieve)
                       'capas': capas, 'z_land': z_land, 'pendiente': pendiente.ravel(), 'umbrales_roca': umbrales_roca(),
                       # F1 r4: poligono (x, y) de la isla de la cima (cupula) para 'mascara' (sin roca dura ahi) y medir_relieve
                       'cupula_isla': _P56, 'cupula_mascara': _isla56, 'cupula_techo': _ceil56, 'cupula_techo_raw': _ceil_raw,
                       'cupula_peso_domo': _wdome56, 'cupula_peso_sin_roca': _wroca56,
                       'tierra_raise': raise_max, 'tierra_lower': lower_max, 'tierra_w_lado': w_lado, 'tierra_caida_ok': _caida_ok,
                       'tierra_raise_who': raise_who, 'tierra_lower_who': lower_who, 'tierra_caida_libre': _caida_libre,
                       'tierra_h_lomo': _h_lomo, 'tierra_h_lomo_min': _h_lomo_min, 'tierra_horq': _horq, 'tierra_add_min': _add_min,
                       'fac_valle': fac_valle, 'fac_sect': fac_sect,
                       'z_gen': z_gen})
    if qa_dir:
        try:
            qa_figuras(res, X, Y, Z, sec, Wd, nx, ny, paso, pit_pts, spec_urb, qa_dir)
        except Exception as e:                    # la QA nunca tumba el pipeline
            print('  [qa] no se pudieron generar las figuras:', repr(e))
    return res


# ---------------------------------------------------------------------------
# QA: hillshade + perfil + secciones + zooms
# ---------------------------------------------------------------------------
def _hillshade_rgb(res, plt):
    from matplotlib.colors import LightSource
    nxg, nyg, cell = res['nx'], res['ny'], res['cell']
    zg = np.asarray(res['z_grid']).reshape(nyg, nxg)
    mar = np.asarray(res['es_mar']).reshape(nyg, nxg)
    roca = np.asarray(res['extras']['mascara_roca']).reshape(nyg, nxg)
    terr = np.asarray(res['extras']['terrazas']).reshape(nyg, nxg)
    ls = LightSource(azdeg=315, altdeg=42)
    zs = np.where(mar, -2.0, zg)
    rgb = ls.shade(zs, cmap=plt.get_cmap('gist_earth'), vert_exag=1.0, dx=cell, dy=cell,
                   vmin=-20.0, vmax=260.0, blend_mode='soft')
    rgb = rgb[:, :, :3].copy()
    rk = np.clip(roca, 0, 1)[:, :, None]
    rgb = rgb * (1 - 0.55 * rk) + np.array([0.62, 0.36, 0.22])[None, None, :] * 0.55 * rk
    tk = terr[:, :, None].astype(float)
    rgb = rgb * (1 - 0.45 * tk) + np.array([1.0, 0.75, 0.1])[None, None, :] * 0.45 * tk
    rgb[mar] = [0.16, 0.36, 0.62]
    return rgb


def qa_figuras(res, X, Y, Z, sec, Wd, nx, ny, paso, pit_pts, spec_urb, qa_dir):
    import os
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    os.makedirs(qa_dir, exist_ok=True)
    nxg, nyg, cell = res['nx'], res['ny'], res['cell']
    gx0, gy0 = res['x0'], res['y0']
    zg = np.asarray(res['z_grid']).reshape(nyg, nxg)
    mar = np.asarray(res['es_mar']).reshape(nyg, nxg)
    coastF = np.asarray(res['extras']['coastF']).reshape(nyg, nxg)
    cumbres = res['extras']['cumbres']
    gx = gx0 + np.arange(nxg) * cell; gy = gy0 + np.arange(nyg) * cell
    ext = [gx[0] - cell / 2, gx[-1] + cell / 2, gy[0] - cell / 2, gy[-1] + cell / 2]
    sec = list(sec)
    land = np.array([s != 'bridge' for s in sec])
    rgb = _hillshade_rgb(res, plt)

    def dibujar_mapa(ax, con_textos=True):
        ax.imshow(rgb, origin='lower', extent=ext, interpolation='nearest')
        ax.contour(gx, gy, np.where(mar, -5, zg), levels=np.arange(25, 260, 25), colors='k', linewidths=0.25, alpha=0.5)
        ax.contour(gx, gy, coastF, levels=[0.5], colors='#08306b', linewidths=1.3)
        Xp = np.where(land, X, np.nan); Yp = np.where(land, Y, np.nan)
        ax.plot(Xp, Yp, 'k-', lw=1.6)
        Xb = np.where(~land, X, np.nan); Yb = np.where(~land, Y, np.nan)
        ax.plot(Xb, Yb, '-', color='#f2f2f2', lw=1.6, dashes=(4, 3))
        if pit_pts:
            ax.plot([q['x'] for q in pit_pts], [q['y'] for q in pit_pts], '-', color='cyan', lw=0.9)
        el = res['extras'].get('casino_elipse')
        if el is not None:
            a_ = np.linspace(0, 2 * np.pi, 97)
            ex_, ey_ = el[2] * np.cos(a_), el[3] * np.sin(a_)
            ax.plot(el[0] + ex_ * math.cos(el[4]) - ey_ * math.sin(el[4]), el[1] + ex_ * math.sin(el[4]) + ey_ * math.cos(el[4]),
                    '--', color='magenta', lw=1.0)
        if con_textos:
            for s_m in range(0, int(len(X) * paso), 200):
                i = int(s_m / paso) % len(X)
                ax.text(X[i], Y[i], str(s_m), fontsize=5.5, color='#ffff99', ha='center', va='center')
            for (cx, cy, cz) in cumbres:
                ax.plot(cx, cy, '^', color='red', ms=7, mec='k')
                ax.text(cx + 12, cy + 12, '%.0f m' % cz, fontsize=7.5, color='red', weight='bold')
            for sc in spec_urb.get('sectores', []):
                i0, i1 = int(sc['s0'] / paso), int(sc['s1'] / paso)
                im = (i0 + i1) // 2
                ax.text(X[im] + sc['lado'] * nx[im] * 45, Y[im] + sc['lado'] * ny[im] * 45,
                        sc['id'], fontsize=6, color='orange', ha='center')
        ax.set_aspect('equal')

    # --- hillshade general ---
    fig, ax = plt.subplots(figsize=(13.0, 13.0 * (ext[3] - ext[2]) / (ext[1] - ext[0])))
    dibujar_mapa(ax)
    ax.set_xticks(np.arange(-1000, 1200, 200)); ax.set_yticks(np.arange(-1000, 1300, 200))
    ax.grid(alpha=0.25, lw=0.4); ax.tick_params(labelsize=7)
    ax.set_title('Terreno: hillshade (NO), pista (negro; viaducto blanco), costa (azul), cumbres (rojo), roca (marron), terrazas (ambar)', fontsize=9)
    plt.tight_layout()
    fig.savefig(os.path.join(qa_dir, 'terreno_hillshade.png'), dpi=110)
    plt.close(fig)
    # --- F1 (bloque 1.6): capas de la mascara por texel (matorral oliva, hierba seca dorada, tierra ocre, roca gris calido) ---
    capas = res['extras'].get('capas')
    if capas is not None:
        from matplotlib.colors import LightSource
        from matplotlib.patches import Patch
        cols_c = {'matorral': (0.33, 0.40, 0.20), 'hierba_seca': (0.80, 0.68, 0.36), 'tierra': (0.52, 0.38, 0.24), 'roca': (0.60, 0.57, 0.50)}
        rgb_c = np.zeros((nyg, nxg, 3))
        for k_, col_ in cols_c.items():
            rgb_c += np.asarray(capas[k_]).reshape(nyg, nxg)[:, :, None] * np.array(col_)[None, None, :]
        inten = LightSource(azdeg=315, altdeg=42).hillshade(np.where(mar, -2.0, zg), vert_exag=1.0, dx=cell, dy=cell)
        rgb_c = np.clip(rgb_c * (0.45 + 0.75 * inten[:, :, None]), 0.0, 1.0)
        rgb_c[mar] = [0.16, 0.36, 0.62]
        fig, ax = plt.subplots(figsize=(13.0, 13.0 * (ext[3] - ext[2]) / (ext[1] - ext[0])))
        ax.imshow(rgb_c, origin='lower', extent=ext, interpolation='nearest')
        ax.contour(gx, gy, coastF, levels=[0.5], colors='#08306b', linewidths=1.0)
        ax.plot(np.where(land, X, np.nan), np.where(land, Y, np.nan), 'k-', lw=1.4)
        for s_m in range(0, int(len(X) * paso), 200):
            i = int(s_m / paso) % len(X)
            ax.text(X[i], Y[i], str(s_m), fontsize=5.5, color='#ffff99', ha='center', va='center')
        med = res['extras'].get('checks', {}).get('capas_media_pct', {})
        ax.legend(handles=[Patch(color=c_, label='%s (%.0f %%)' % (k_, med.get(k_, 0.0))) for k_, c_ in cols_c.items()],
                  loc='lower left', fontsize=8)
        ax.set_aspect('equal'); ax.tick_params(labelsize=7)
        ax.set_title('Capas de la mascara por texel (extras[capas]): R matorral, G hierba seca, B tierra, A roca; umbral de roca %.2f +- %.2f'
                     % (ROCA_UMBRAL_PEND, ROCA_UMBRAL_RUIDO), fontsize=9)
        plt.tight_layout()
        fig.savefig(os.path.join(qa_dir, 'terreno_capas.png'), dpi=110)
        plt.close(fig)
    # --- zooms: pueblo subida, pit+bajada, mirador, casino ---
    zonas = [('pueblo subida (s 620-1120)', 620, 1120, 170), ('pueblo alto (s 1250-1560)', 1250, 1560, 170),
             ('pit lane + bajada (s 2380-2760)', 2380, 2760, 150),
             ('mirador (s 2960-3180)', 2960, 3180, 230), ('casino (s 3170-3480)', 3170, 3480, 170),
             ('tunel + coche (s 380-660)', 380, 660, 200),
             ('penon del casino + rotonda (s 3440-3640; elipse magenta = roca_casino)', 3440, 3640, 230)]
    fig, axs = plt.subplots(2, 4, figsize=(28, 14))
    axs.ravel()[-1].axis('off')
    for ax, (tit, sa, sb, mg) in zip(axs.ravel(), zonas):
        ia, ib = int(sa / paso), int(sb / paso)
        xs = X[ia:ib]; ys = Y[ia:ib]
        if tit.startswith('pit') and pit_pts:
            xs = np.concatenate([xs, [q['x'] for q in pit_pts[:50]]]); ys = np.concatenate([ys, [q['y'] for q in pit_pts[:50]]])
        dibujar_mapa(ax, con_textos=False)
        for s_m in range(int(sa), int(sb) + 1, 40):
            i = int(s_m / paso) % len(X)
            ax.text(X[i], Y[i], str(s_m), fontsize=6, color='#ffff99', ha='center', va='center')
        ax.set_xlim(xs.min() - mg, xs.max() + mg); ax.set_ylim(ys.min() - mg, ys.max() + mg)
        ax.set_title(tit, fontsize=9); ax.tick_params(labelsize=6)
    plt.tight_layout()
    fig.savefig(os.path.join(qa_dir, 'terreno_zoom.png'), dpi=100)
    plt.close(fig)
    # --- perfil: Z(s) y terreno a +-40 m ---
    def z_en(xq, yq):
        return map_coordinates(zg, [(np.asarray(yq) - gy0) / cell, (np.asarray(xq) - gx0) / cell], order=1, mode='nearest')
    s = np.arange(len(X)) * paso
    zp = z_en(X + nx * (Wd / 2 + 40.0), Y + ny * (Wd / 2 + 40.0))
    zm = z_en(X - nx * (Wd / 2 + 40.0), Y - ny * (Wd / 2 + 40.0))
    z_eje = z_en(X, Y)
    fig, ax = plt.subplots(figsize=(18, 6.5))
    cur = sec[0]; a = 0
    cols = {'dirt': '#e8d8b0', 'bridge': '#d9d9d9', 'tech': '#eef3ff', 'straight': 'white', 'norm': 'white'}
    for i in range(1, len(sec) + 1):
        if i == len(sec) or sec[i] != cur:
            ax.axvspan(a * paso, i * paso, color=cols.get(cur, 'white'), alpha=0.6, lw=0)
            if i < len(sec):
                cur = sec[i]; a = i
    for sc in spec_urb.get('sectores', []):
        ax.axvspan(sc['s0'], sc['s1'], ymin=0.0, ymax=0.03, color='orange', lw=0)
    ax.fill_between(s, Z + 8.0, zp, where=zp > Z + 8.0, color='#d97b4a', alpha=0.35, lw=0, label='pared lado +1')
    ax.fill_between(s, Z + 8.0, zm, where=zm > Z + 8.0, color='#8b4a2b', alpha=0.35, lw=0, label='pared lado -1')
    ax.plot(s, zp, color='#1f77b4', lw=0.9, label='terreno a +40 m (lado +1 = izquierda / mar en meta)')
    ax.plot(s, zm, color='#7a3e1e', lw=0.9, label='terreno a -40 m (lado -1 = derecha / ladera, boxes)')
    ax.plot(s, np.where(land, z_eje, np.nan), color='#2ca02c', lw=0.8, label='terreno bajo el eje (tierra)')
    ax.plot(s, Z, 'k-', lw=1.6, label='Z(s) pista')
    ax.axhline(0.0, color='#08306b', lw=0.6, ls='--')
    ax.set_xlim(0, s[-1]); ax.set_xlabel('s (m)'); ax.set_ylabel('z (m)')
    ax.set_xticks(np.arange(0, s[-1] + 1, 200)); ax.tick_params(labelsize=7); ax.grid(alpha=0.3)
    ax.legend(loc='upper left', fontsize=8)
    ax.set_title('Perfil: rasante de la pista y cota del terreno a 40 m del borde a cada lado (fondo: tierra beige, viaducto gris, tecnica azul; naranja = sectores de terrazas)', fontsize=9)
    plt.tight_layout()
    fig.savefig(os.path.join(qa_dir, 'terreno_perfil.png'), dpi=110)
    plt.close(fig)
    # --- secciones transversales: terreno a lo largo de la normal (-150..+150 m) ---
    AT = float(spec_urb.get('ancho_terraza', 21.0))
    H1 = float(spec_urb.get('altura_terraza_1', 0.5)); HT = float(spec_urb.get('altura_terraza', 6.0))
    ss_sec = [450, 700, 800, 910, 1000, 1054, 1400, 1480, 1850, 2680, 3050, 3300, 3420]
    fig, axs = plt.subplots(4, 4, figsize=(20, 14.5))
    lat = np.arange(-150.0, 150.1, 1.0)
    for ax in axs.ravel()[len(ss_sec):]:
        ax.axis('off')
    for ax, s_m in zip(axs.ravel(), ss_sec):
        i = int(s_m / paso) % len(X)
        xq = X[i] + nx[i] * lat; yq = Y[i] + ny[i] * lat
        zq = z_en(xq, yq)
        ax.fill_between(lat, -6, zq, color='#c9b58f', alpha=0.6, lw=0)
        ax.plot(lat, zq, color='#6b4a1e', lw=1.2)
        ax.plot([-Wd[i] / 2, Wd[i] / 2], [Z[i], Z[i]], 'k-', lw=3.5)
        ax.axhline(0.0, color='#08306b', lw=0.6, ls='--')
        for sc in spec_urb.get('sectores', []):
            if not (sc['s0'] <= s_m <= sc['s1']):
                continue
            xp, fp, hs = perfil_terrazas(int(sc['n_terrazas']), sentido_terrazas(sc), AT, H1, HT,
                                         float(spec_urb.get('bordillo_hasta', 1.5)), 2.5)
            lp = sc['lado'] * (Wd[i] / 2 + np.array(xp)); zp_ = Z[i] + np.array(fp)
            ax.plot(lp, zp_, '--', color='red', lw=1.0)
        ax.set_xlim(-150, 150)
        lo = min(float(zq.min()), Z[i]) - 5; hi = max(float(zq.max()), Z[i]) + 5
        if any(sc['s0'] <= s_m <= sc['s1'] for sc in spec_urb.get('sectores', [])):
            ax.set_xlim(-90, 90); hi = min(hi, Z[i] + 40.0); lo = max(lo, Z[i] - 40.0)
        ax.set_ylim(lo, hi)
        ax.set_title('s = %d (%s)  Z = %.1f   lado +1 a la derecha' % (s_m, sec[i], Z[i]), fontsize=8)
        ax.grid(alpha=0.3); ax.tick_params(labelsize=7)
    plt.tight_layout()
    fig.savefig(os.path.join(qa_dir, 'terreno_secciones.png'), dpi=100)
    plt.close(fig)
    # --- costuras: |dz| entre celdas vecinas de la misma terraza, por sector ---
    dz_map = res['extras'].get('costuras_dz')
    sectores = [sc for sc in spec_urb.get('sectores', []) if int(sc['n_terrazas']) >= 1]
    if dz_map is not None and sectores:
        dzm = np.asarray(dz_map).reshape(nyg, nxg)
        talm = np.asarray(res['extras'].get('talud_ramas_dz', np.zeros(nyg * nxg))).reshape(nyg, nxg)
        terr = np.asarray(res['extras']['terrazas']).reshape(nyg, nxg)
        tsec = np.asarray(res['extras'].get('terrazas_sec', np.full(nyg * nxg, -1))).reshape(nyg, nxg)
        ncol = 4; nfil = (len(sectores) + ncol - 1) // ncol
        fig, axs = plt.subplots(nfil, ncol, figsize=(5.2 * ncol, 5.2 * nfil))
        axs = np.atleast_1d(axs).ravel()
        for ax, sc in zip(axs, sectores):
            ia, ib = int(sc['s0'] / paso), int(sc['s1'] / paso)
            xs = X[ia:ib]; ys = Y[ia:ib]
            lado = int(sc['lado'])
            cx = float(np.mean(xs + lado * nx[ia:ib] * 40.0)); cy = float(np.mean(ys + lado * ny[ia:ib] * 40.0))
            R = max(float(np.hypot(xs - cx, ys - cy).max()) + 90.0, 150.0)
            # RONDA 15c: cada panel pinta SOLO las celdas de su sector (antes las de todos: las x rojas de la C6 de
            # pueblo_subida_ladera salian tambien en el panel de pueblo_subida_mar)
            ts_ = terr & (tsec == sectores.index(sc))
            ax.imshow(np.where(terr, 0.0, np.nan), origin='lower', extent=ext, cmap='Greys', vmin=-1, vmax=1, alpha=0.25, interpolation='nearest')
            ax.imshow(np.where(ts_ & (talm > 0.0), talm, np.nan), origin='lower', extent=ext, cmap='Blues', vmin=0.0, vmax=3.0, alpha=0.8, interpolation='nearest')
            im = ax.imshow(np.where(ts_ & (dzm > 0.0), dzm, np.nan), origin='lower', extent=ext, cmap='magma_r', vmin=0.0, vmax=1.2, interpolation='nearest')
            ax.plot(xs, ys, 'k-', lw=1.5)
            jj, ii = np.where(ts_ & (dzm > 0.6))
            if len(jj):
                ax.plot(gx[ii], gy[jj], 'x', color='red', ms=4, mew=0.8)
            for s_m in range(int(sc['s0']), int(sc['s1']) + 1, 40):
                i = int(s_m / paso) % len(X)
                ax.text(X[i], Y[i], str(s_m), fontsize=6, color='#1f77b4', ha='center', va='center')
            ax.set_xlim(cx - R, cx + R); ax.set_ylim(cy - R, cy + R); ax.set_aspect('equal')
            # cifras DEL SECTOR (RONDA 15c: antes el titulo repetia las globales en los 7 paneles)
            i_sc = sectores.index(sc)
            m = terr & (dzm > 0.0) & (tsec == i_sc); mt = terr & (talm > 0.0) & (tsec == i_sc)
            ax.set_title('%s (lado %+d, %d terr., %s)\ncosturas max %.2f m, > 0.6: %d celdas\ntalud entre ramas (azul): %d celdas, max %.2f m' %
                         (sc['id'], lado, int(sc['n_terrazas']), 'sube' if sentido_terrazas(sc) > 0 else 'baja',
                          float(dzm[m].max()) if m.any() else 0.0, int((dzm[m] > 0.6).sum()) if m.any() else 0,
                          int(mt.sum()), float(talm[mt].max()) if mt.any() else 0.0), fontsize=8)
            ax.tick_params(labelsize=6)
        for ax in axs[len(sectores):]:
            ax.axis('off')
        fig.colorbar(im, ax=list(axs), shrink=0.5, label='escalon entre celdas vecinas de la misma terraza, descontada la rasante (m); x rojas: > 0.6')
        fig.savefig(os.path.join(qa_dir, 'terreno_costuras.png'), dpi=100)
        plt.close(fig)
    print('  QA ->', os.path.join(qa_dir, 'terreno_hillshade.png'), 'terreno_perfil.png, terreno_secciones.png, terreno_zoom.png, terreno_costuras.png, terreno_capas.png')


if __name__ == '__main__':
    # prueba aislada sobre la copia de geometria_3d.json (no toca el pipeline)
    import json, os, sys, time
    base = os.path.dirname(os.path.abspath(__file__))
    snap = os.path.join(base, 'assets', '_geom_snapshot_terreno.json')
    d = json.load(open(snap, encoding='utf-8'))
    Mu = d['muestras']
    X = np.array([m['x'] for m in Mu]); Y = np.array([m['y'] for m in Mu]); Z = np.array([m['z'] for m in Mu])
    nx = np.array([m['nx'] for m in Mu]); ny = np.array([m['ny'] for m in Mu]); Wd = np.array([m['w'] for m in Mu])
    sec = [m['sec'] for m in Mu]
    spec = json.load(open(os.path.join(base, 'urbanismo_spec.json'), encoding='utf-8'))
    # el lado del mirador se toma de preparar_geometria (MIRADORES); la copia
    # antigua del JSON puede traer el lado viejo (+1): construir() lo comprueba
    mir = [(m['s0'], m['s1'], m['side'], m['ancho']) for m in d.get('miradores', [])]
    if '--mirador-mar' in sys.argv:
        mir = [(2990.0, 3150.0, -1, 15.0)]
    qa = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(base, 'renders', 'qa')
    t0 = time.time()
    res = construir_loews_intacta(X, Y, Z, sec, Wd, nx, ny, d['paso_m'], d['largo_m'], d['curvas'], d['pit_lane'],
                                  (d['loews']['x'], d['loews']['y']), spec, mir, cell=4.0, qa_dir=qa,
                                  lat=np.array([m.get('lat', 0.0) for m in Mu]))
    print('tiempo: %.1f s' % (time.time() - t0))
