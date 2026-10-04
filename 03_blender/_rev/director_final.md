**Veredicto de dirección de arte, Porto Corsa (57 capturas de `03_blender/renders/capturas/`, renderizadas el 04/10 a las 13:01)**

No he editado nada. Las coordenadas son píxeles (x, y) sobre la imagen de 1600x900. Además de las capturas he consultado `03_blender/renders/qa/urbanismo_informe.json` (13:00, 23 fallos).

**Captura por captura**

- **01_aerea_general**: defectos.
  - El McLaren parece un coche apoyado encima de un islote de roca en la costa (260-470, 290-500). La roca de la zaga queda más baja que el coche, así que no sale de una montaña (MCOCHE_roca / zona_tunel alto_montana).
  - Los desmontes se ven como manchas grises planas con bordes difuminados (590-760, 280-340; 1100-1500, 540-650).
  - El macizo es un cono verde uniforme, sin roca ni vaguadas que se lean.
- **02_meta_y_puerto**: defectos.
  - El McLaren descansa sobre una repisa horizontal plana encima de la pista, con los bajos rectos (300-1000, 330-360): parece una escultura en pedestal o un puente.
  - La zaga se mete en un montón escalonado tipo vóxel con rayas blancas horizontales (0-560, 150-430).
  - El color crema parece plástico, no piedra.
  - Hay un desmonte gris liso enorme junto al hotel (1420-1600, 60-250).
  - Boxes y tribunas: ok.
- **03_tunel_entrada**: defectos.
  - El portal (TUNEL_portal_galeria) es una caja pequeña de sillares bajo la rueda. Por encima se ven el disco oscuro y los radios, así que la pista no "entra por la rueda".
  - Bajo la carrocería hay una repisa gris plana con una franja oscura (0-780, 450-580).
  - En el talud derecho la hierba está estirada en vertical (1200-1450, 50-500).
- **04_tunel_salida**: ok con reservas. El interior está desnudo: bóveda lisa sin juntas ni luces.
- **05_pueblo_subida**: defectos.
  - Las terrazas de la derecha no son llanas: la ladera sigue continua y los muros asoman de la hierba como aletas, con un velo blanquecino debajo (640-1000, 450-800). Es urbanismo_escena más la rejilla de 4 m (N2/F-06, sin arreglar).
  - La terraza intermedia está vacía.
  - Hay un pilar de muro suelto (1215, 385-460).
  - El gran cono beige con rayas onduladas parece una duna, no roca (1380-1600, 90-560; mascara_roca).
  - La cumbre del fondo queda en bruma.
- **06_pueblo_calle**: defectos.
  - Una rampa con muro alto de sillares sube a una terraza vacía (870-1150, 570-800).
  - Hierba estirada sobre los muros (780-860, 510-580).
  - El mismo cono beige (1330-1600, 60-330).
  - Calle izquierda: ok.
- **07_tierra_subida**: defectos.
  - Los desmontes son parches grises pintados en la ladera (570-760, 330-420; 840-1000, 375-445; 1130-1230, 430-490; cumbre 380-540, 210-270).
  - Banda blanquecina en dientes de sierra en la ladera derecha (1160-1530, 330-420).
  - La pista va por lomas suaves: no se lee tallada en la ladera (pared a un lado, caída al otro).
  - El bancal parece una caja suelta en la loma (480-560, 410-430).
- **08_tierra_cima**: defectos.
  - Dos bandas blancas en dientes de sierra a lo largo de una línea fina de sendero (300-1100, 40-260). Es el atributo 'roca' por vértice del TERRENO (tallar_sendero/explanar) interpolado en triángulos de 4 m.
  - El borde hierba/roca del primer plano está borroso y las rayas parecen curvas de nivel.
- **09_bajada_recta**: defectos.
  - Desmonte enorme y liso tipo cantera a la izquierda (0-740, 330-590), con borde de hierba difuso.
  - Más parches grises (1290-1600, 330-530).
  - Casas: ok.
- **10_casino_sector**: ok. Las casas tienen su calle de servicio. Lo menor: un prado vacío con una palmera suelta y la cara del peñón lisa y facetada (850-1440, 415-500).
- **11_bajada_rotonda**: ok. La Loews está intacta y la bajada del peñón se ve, con farolas. Lo menor:
  - Una mata pegada en la pared vertical del peñón (740, 293).
  - Zigzag amarillo en la calzada.
- **12_rotonda_loews**: defectos.
  - Tres hoyos triangulares oscuros en la hierba bajo el cartel MONDIALE GP (240-620, 825-870): nodos del TERRENO hundidos.
  - El cartel GP está clavado en el borde del acantilado, medio dentro de la roca (1005-1045, 410-490).
  - La Loews en sí: ok.
- **13_puente_alto**: defectos.
  - El lóbulo central de la roca del lazo es una cúpula gris lisa velada por bruma, sin estratos (820-1250, 230-900).
  - El acantilado derecho tiene rayas tipo mapa topográfico (1050-1600, 330-900).
  - El McLaren aparece al fondo sobre un islote (1050-1500, 130-270).
  - Viaducto y contacto con la roca: ok.
- **14_puente_mar**: defectos.
  - El límite hierba/roca va en escalera (almenas) por la cara del acantilado (1100-1600, 430-650).
  - La última pila acaba en punta contra la roca (840-900, 560-720).
- **15_final_puente_roca**: captura inútil. La cámara (tras curva 43) mira a pocos metros de la roca del lazo y solo se ve roca gris borrosa, más una mata plana pegada en vertical (125-175, 435-495).
- **16_retorno_chicane**: defectos.
  - Desmonte enorme con borde difuso a la derecha (930-1600, 380-660).
  - Parches grises en la ladera media (480-700, 180-330).
  - La playa es una banda blanquecina difusa.
- **17_tunel_salida_exterior**: defectos.
  - Hierba estirada en la pared izquierda (540-640, 260-520).
  - Roca en escalones pixelados (1380-1600, 540-700) con una mancha verde borrosa. Es el pedestal del MCOCHE, la celda dura de la zona del túnel.
  - Portal pequeño delante de la rueda.
- **19_penon_casino_foto**: parcial. La bajada visible cumple.
  - La roca es un tambor con estratos regulares, como una tarta, y está velada por bruma.
  - Un plano blanco liso sin material sale del borde superior junto al casino (630-690, 275-330).
  - A la derecha, la ladera es una cara cortada con una capa verde encima (1100-1600, 260-900).
- **20_penon_casino_cerca**: parcial. La meseta es blanca, lisa y vacía; la roca es un tambor; hay matas sueltas en la cara vertical. La bajada sí se ve.
- **21_montana_dentro_del_lazo**: defectos.
  - Bandas grises de desmonte con bordes difusos (0-320, 330-400; 770-990, 430-510; 1020-1600, 420-580; 1110-1480, 300-360).
  - Macizo verde uniforme.
  - La subida de tierra sí se ve: ok.
- **22_viaducto_arcos_altos**: defectos. La hierba baja en una lengua dentada por el acantilado hasta la línea de agua, con manchas verdes al pie (1050-1600, 340-740).
- **23_zigzag_y_pianos**: ok, pero es casi un duplicado de la 11.
- **24_horquilla_cenital**: ok. Lo menor: el cartel GP de canto y el ALLINOL quedan en el borde del acantilado (1005-1020, 420-560; 660-830, 760-860).
- **25_paseo_mirador_desde_pista**: ok. Lo menor:
  - Cúpula beige lisa, sin detalle (1420-1600, 390-660).
  - Muro diagonal largo en el prado (1100-1600, 560-820).
- **26_paseo_y_parking_desde_abajo**: defectos.
  - La plaza del palazzo está en mitad del prado sin camino de acceso (930-1300, 525-585; F-04).
  - El primer plano tiene desmonte borroso y un velo verde porque la cámara está pegada al terreno.
- **27_coche_camara_0**: defectos.
  - La torre está sobre una losa en el prado, sin camino, y la losa asoma como una caja (630-990, 530-595).
  - Un muro trepa la loma como una muralla (1000-1600, 130-430).
  - Loma beige con rayas (830-1600, 0-350).
- **27_coche_camara_1**: defectos.
  - Torre sin acceso.
  - Una acera ancha muere en rampa contra la hierba (410-640, 750-860).
- **27_coche_camara_2**: defectos.
  - Un murete corto acaba de golpe en el prado (1045, 510-580).
  - Torre sin acceso.
  - Desmonte gris enorme al fondo (570-1300, 0-200).
- **28_helicoptero_camara**: defectos. Tras el paddock hay una pared lisa tipo cantera de 25-45 m (caja del pit), con el pueblo encaramado al borde (0-1390, 120-340).
- **29_boxes_desde_pista**: ok.
- **30_boxes_tribuna_aerea**: ok con reservas. La misma cantera (0-730, 70-260) y hangares-caja genéricos.
- **31_boxes_pit_lane**: defectos.
  - El McLaren parece aparcado en una plataforma sobre la meta, con la zaga en roca vóxel (0-200, 200-300).
  - Los PIT_amortiguador son cilindros negros lisos (515-650, 715-860).
  - El QA marca PIT_muro_morro "4.3 m dentro del asfalto".
- **32_montana_coche_lado**: defectos.
  - Coche crema brillante, con estratos como franjas de pintura: no parece piedra.
  - No se ve ningún macizo detrás.
  - Matas diminutas en la línea de cintura (580, 385; 690, 395; MCOCHE_veg).
  - Hierba estirada a la derecha (1400-1600, 600-900).
- **33_montana_coche_desde_pista**: defectos.
  - Hierba estirada en el desmonte (930-1350, 200-650).
  - Repisa plana bajo la carrocería (0-500, 580-650).
  - Portal pequeño.
- **33b_montana_coche_34**: defectos.
  - La zaga apoya en un espolón bajo de roca escalonada en bloques (0-500, 100-700): el coche está encima, no sale de la montaña.
  - El alerón parece un tablón sobre postes (190-550, 200-260).
- **34_roca_lazo_desde_pista**: captura inútil. La cámara mira de frente la cara de la roca a pocos metros y todo el cuadro es roca gris.
- **34_roca_lazo_general**: parcial.
  - La roca es una cúpula lisa con matas en lunares regulares, sin estratos ni cornisas visibles.
  - El pueblo de la cumbre es diminuto.
  - Desmontes difusos en la costa del fondo (0-1000, 250-440).
  - La pista pegada a la roca: ok.
- **36_roca_casino_desde_pista**: defectos. La torre de cámara está sobre una losa gruesa en la ladera, sin acceso (255-870, 400-630). El espolón con valla y la señal CASINO: ok.
- **36_roca_casino_general**: parcial.
  - La meseta es una losa blanca vacía con aspecto de nieve (750-1520, 210-380).
  - La cala-marina es una losa rectangular blanca flotando en el mar, unida por un espigón recto (55-360, 535-650).
  - Bajada y espolón: ok.
- **38_rotonda_lateral**: ok. La Loews está intacta. Lo menor:
  - Matas pegadas en la pared (1085-1110, 130-150).
  - Bloque beige suelto al pie (1300-1360, 390-490).
- **39_pueblo_calles_aerea**: defectos.
  - En pueblo_subida_ladera las terrazas 1-2 están casi vacías: calles de grava, rampas y una plaza con fuente sin casas (690-1130, 220-830).
  - Los muros quedan como aletas sueltas (770, 250-380; 935, 220-420; 1120, 260-560).
  - Ladera beige con rayas, tipo duna (1100-1600, 20-900).
  - El lado izquierdo: ok.
- **40_pueblo_travesia**: defectos.
  - La vista no informa: un muro ciego de sillares (820-1600, 185-690) y un prado vacío; la travesía no se ve.
  - Una casa rosa tiene la puerta en la coronación del muro (1130-1340, 0-185).
  - Velo de hierba sobre los muros (0-830, 190-330).
- **41_espolon_casino**: parcial. El espolón con valla: ok.
  - Una repisa de roca beige con árboles cuelga sobre el prado (640-990, 280-420).
  - Hoyos triangulares en la hierba junto a la pista (800-930, 800-900).
  - Torre WGP sin acceso (200-310, 530-680) y un trozo de muro suelto (0-60, 595-615).
  - Mancha oscura difusa (290-370, 330-560), probablemente la sombra del helicóptero.
- **42_paddock_hotel**: defectos. Desmontes gigantes tipo cantera (320-520, 110-280; 550-1500, 0-420). La subida al hotel: ok.
- **43_bajada_desde_grua**: captura rota.
  - Una banda horizontal azul/gris tapa media imagen (0-1600, 130-245). Lo más probable es que sea la propia CAMARA_tierra, porque la cámara se coloca en su posición +4 m.
  - Una señal se ve sin texto, por detrás (1270-1450, 570-900).
- **44_bajada_recta_lateral**: ok. Lo menor: el zigzag amarillo es continuo.
- **45_roca_lazo_puente**: parcial. La pista pegada a la roca: ok. La roca es un muro beige liso y velado, con los estratos casi invisibles.
- **46_roca_lazo_muelle**: ok. Lo menor: la roca es lisa y sin detalle.
- **47_yates_vip**: ok. Lo menor: desmonte gris tras la tribuna (1120-1560, 100-340).
- **47b_yates_desde_pista**: captura mal colocada. La cámara (+8 m hacia el mar, +5 m de altura) cae dentro de la tribuna y solo se ven coches espectadores.
- **48_ermita_sendero**: defectos.
  - Toda la imagen está velada por bruma.
  - La plaza es un disco blanco perfecto sin bordillo (440-785, 520-680).
  - El bancal parece una bandeja suelta (220-250, 350-425).
  - Hierba estirada (130-250, 480-620).
  - Ermita, fuente y cipreses: ok.
- **49_piloto_s300**: ok con reservas. Hierba estirada en el talud derecho (930-1100, 200-470) y portal pequeño.
- **50_piloto_s800**: defectos. Las terrazas de la derecha están vacías, solo hierba y muros que asoman de una ladera continua (1000-1600, 280-560). El lado izquierdo y los enlaces cerrados: ok.
- **51_piloto_s1700**: defectos.
  - El desmonte junto a la pista es una mancha gris con borde difuso, con un árbol y una roca apoyados en la cara (970-1600, 160-450).
  - Bancal-caja suelto (225-375, 385-430).
  - No se lee la subida tallada en la montaña.
- **52_piloto_s2900**: ok, aunque anodina; la subida apenas se percibe.
- **53_piloto_s3400**: ok.
- **54_piloto_s4150**: ok. La pista va pegada a la roca del lazo; lo único es que la roca no tiene textura.

**Veredicto global: no cumple todavía con "sin fallos".**

Lo que sí cumple:
- La Loews está intacta.
- La bajada del peñón del casino se ve, y el espolón tiene valla.
- La pista va pegada a la roca del lazo y la roca está completa.
- Los enlaces del pueblo tienen vallas.
- El ambiente italiano/Cars funciona en meta, boxes, pueblo y casino.

Lo que no cumple:
- El McLaren no está integrado en la montaña.
- La montaña no se lee como una montaña con la pista tallada.
- El pueblo de la ladera tiene terrazas vacías y no llanas.
- Los materiales de terreno y roca son pobres, borrosos y con artefactos.
- Cinco capturas no sirven para juzgar.

Unas 15 capturas están ok o con defectos menores; el resto tiene defectos visibles.

**Los 10 defectos más importantes**

1. **McLaren suelto, no integrado.** Parece un coche crema de plástico sobre un islote bajo de roca escalonada tipo vóxel y sobre una repisa plana encima de la pista; el macizo de la zaga no sube por encima del coche (01, 02, 13, 31, 32, 33b). Origen probable: `montana_mclaren.py` (macizo, celdas duras, caliza demasiado clara) y `integrar_escena.zona_tunel` (alto_montana / enterrado).
2. **Terrazas de pueblo_subida_ladera no llanas y casi vacías.** Los muros asoman de una ladera continua como aletas, con velo blanco, y hay calles, rampas y una plaza sin casas (05, 06, 39, 40, 50). Origen probable: `urbanismo.py` (la zona excluida y GAP_RAMPA quitan casas), la rejilla de 4 m del terreno (N2/F-06, sin arreglar) y los muros de `urbanismo_escena`.
3. **Desmontes del TERRENO que parecen canteras o parches pintados.** Son beige lisos con rayas onduladas tipo curva de nivel y bordes difuminados: caja del pit tras el paddock, recta, tierra, cono beige del pueblo (01, 07, 09, 16, 21, 28, 30, 42, 51, 05/06/39). Origen probable: `construir_pista._roca_terreno` y `terreno_montana` (mascara_roca, pared de la caja del pit).
4. **Artefactos de la máscara roca/hierba.**
   - Bandas blancas en dientes de sierra a lo largo del sendero (07, 08).
   - Bordes en escalera (14, 22).
   - Hierba estirada en caras casi verticales, con velo (03, 05, 17, 33, 40, 48, 49).

   Origen probable: el atributo 'roca' por vértice, interpolado en triángulos de 4 m (tallar_sendero / explanar), y la proyección de la textura de hierba.
5. **Cinco capturas rotas o inútiles**, justo en zonas que pidió el usuario:
   - 15 y 34_roca_lazo_desde_pista: cámara contra la roca.
   - 43: banda que tapa media imagen.
   - 47b: cámara dentro de la tribuna.
   - 40: muro ciego.

   Se arregla en `renderizar_capturas.py` (tras(curva 43), _tag_desde_pista, posición de la grúa +4 m, 47b con +8 m hacia el mar).
6. **La tierra no se lee como montaña tallada.** Son lomas suaves verdes y uniformes, sin pared de roca a un lado y caída al otro, y la cumbre queda en bruma (01, 05, 07, 21, 51). Origen probable: el macizo y el material de `terreno_montana`.
7. **Roca del lazo y peñón del casino con material pobre.**
   - La roca del lazo son cúpulas lisas veladas con matas en lunares (13, 15, 34_roca_lazo_general, 45).
   - El peñón es un tambor de tarta con meseta blanca vacía y un plano liso sin material (19, 20, 36).
   - La cala del casino es una losa blanca flotante (36_roca_casino_general).

   Origen probable: `roca_lazo.py` (H7 sin arreglar), `roca_casino.py` y MAT_PPUEBLO_roca.
8. **Cosas sin acceso o sin destino.**
   - Torres de cámara sobre losas-caja en el prado, sin camino (27_0/1/2, 36_roca_casino_desde_pista, 41).
   - Plaza del palazzo sin acceso (26).
   - Acera que muere contra la hierba (27_1).
   - Muretes sueltos (27_2, 41).

   Origen probable: `integrar_escena.zona_camaras` (torre fija) y `zona_paseo_mirador` (F-04).
9. **Hoyos triangulares en la hierba junto a la Loews y su acceso** (12, 41). Además, el QA da `LOEWS_rotonda.001` con una esquina a 1.1 m sobre el suelo, cuando la Loews tiene que seguir intacta y bien asentada. Origen probable: nodos del TERRENO hundidos por bajar_bajo_asfalto o por terreno_v3 de asentar_objetos.
10. **Fallos de QA que contradicen lo pedido** (`urbanismo_informe.json`, 13:00, 23 fallos):
    - CASAS_casa.066 tiene CAMINO_muro.132 a 0.2 m delante de la fachada: tapa ventanas.
    - Tres edificios flotan 0.8-1.1 m.
    - CALLE_plaza_ayto tiene hierba 0.27 m por encima y un muro que cruza la losa.
    - El sendero CAMINO_tierra.001 tiene hasta 3.5 m de aire debajo.
    - PIT_muro_morro aparece 4.3 m dentro del asfalto.

Los recortes ampliados que usé para comprobar detalles están en `C:/Users/arcej/AppData/Local/Temp/claude/E--Escritorio-claude-pc-arnau-aseto-corsa/1a7b6c0c-72d8-44ab-af11-95e782d87886/scratchpad/crops/`.