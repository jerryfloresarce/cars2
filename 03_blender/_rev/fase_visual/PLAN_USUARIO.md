# Plan del usuario para la FASE VISUAL de Porto Corsa (recibido el 04/10/2026 tras ver las 57 capturas)

Texto literal del usuario (es el encargo; los agentes lo interpretan, no lo discuten):

---

MEJORA VISUAL DE PORTO CORSA: prioridades, herramientas y criterios

Criterio: el aspecto Pixar son formas exageradas y suaves + superficies ricas
(textura, variación de color, oclusión ambiental). Ahora las formas son tímidas
y las superficies planas. No añadas objetos sin más: primero relieve,
integración, paleta y densidad.
Método: al cerrar cada bloque, capturas antes/después desde las mismas cámaras
(aéreas y de piloto en s300, s800, s1700, s2900, s3400, s4150). Juzga sobre
todo desde la cámara del coche.

1. RELIEVE
- Macizo alto y escarpado detrás del pueblo, con crestas y barrancos (puede
  ser fondo no conducible). Terreno tipo Amalfi: acantilados que caen al mar.
- Erosión hidráulica del heightmap con Hydra (github.com/ozikazina/Hydra) o un
  script NumPy basado en dandrino/terrain-erosion-3-ways. Proteger el corredor
  de la pista con una máscara.
- Tramo de tierra: más desnivel (máximo 12-15 % de pendiente), zigzags
  excavados en la ladera, pared de roca a un lado y caída al otro.
- Cinco "momentos postal" encuadrados a propósito desde el coche: salida del
  túnel del McLaren, cima del tramo de tierra (bahía entera abajo), puente del
  casino, bajada a la horquilla de la fuente y recta del puerto.

2. ROCA INTEGRADA
- Roca como parte del terreno según pendiente (más de 35-40 grados), caliza
  cálida con estratos horizontales. Afloramientos medio enterrados, piedras
  sueltas al pie, matorral en las repisas.
- Roca del lazo: promontorio con paredes verticales, repisas y pinos;
  opcional, una torre o fortín.
- McLaren petrificado: mismo material y estratos que el acantilado, base
  fundida con el terreno y escombros, grietas, plantas en las juntas, oclusión
  ambiental en los huecos. Mantener el túnel por la rueda con portal de sillería.

3. PALETA, TEXTURAS Y LUZ
- Fuera el verde césped uniforme: oliva y salvia oscuros (matorral, pinar),
  hierba seca dorada, caliza ocre y gris cálido, terracota. Césped solo en
  jardines y rotondas.
- Terreno con ksMultilayer_fresnel_nm4: máscara RGBA por pendiente y altura
  (matorral, hierba seca, tierra, roca) + 4 texturas de detalle CC0 de
  Poly Haven o ambientCG, recoloreadas a la paleta.
- Bisel en las aristas, oclusión ambiental horneada y, en Assetto Corsa, VAO
  con acc-bakeryoptix.

4. VEGETACIÓN CON TREEFX DE CSP (wiki "Tracks – Trees")
- Especies: pino piñonero, ciprés, palmera, olivo, encina y arbustos con flor.
  FBX con 2-3 niveles de detalle, pivote en la base, textura difusa con alfa +
  normal; convertir con Content Manager > Creator tools > tree converter a .bin.
- Script que genere extension/trees/trees.txt desde Blender: zonas por máscara
  (pendiente, altura, cercanía al mar y al pueblo), árboles agrupados en masas
  (no reparto uniforme), variaciones de tamaño, ángulo y color. Convertir los
  ejes de Blender a los de Assetto Corsa y validar primero con 3 árboles.
- Quitar los árboles actuales en forma de piruleta. Grass FX solo en céspedes.

5. PUEBLO
- Densificar: fachadas pegadas sin césped entre casas, alturas y anchos
  variados, campanarios, cúpulas, soportales con tiendas y toldos, escaleras y
  muros de contención en terrazas que trepen la ladera.
- Atlas de fachadas con variación (colores de la Riviera, contraventanas,
  balcones, macetas, ropa tendida). Tramos de adoquín, alcantarillas, bolardos
  y farolas.

6. AGUA Y COSTA
- [Material_Water] Type = SEA y [BOUNCED_LIGHT] CAUSTICS = 1
  (wiki "Tracks – Water shader").
- Fondo marino con degradado (turquesa en la orilla, azul profundo mar
  adentro). Escolleras de bloques en la costa y el dique; puerto deportivo con
  forma de llanta. Veleros, yates de varios tamaños y lanchas.

7. PÚBLICO Y RELLENO
- 10-12 tipos de coche espectador (carrocerías, colores, ojos y banderas
  distintos), con variación de escala y giro. También en balcones, yates,
  terraza del casino y ladera (autocaravanas, tiendas de campaña).
- Rellenar las praderas vacías: bancales de olivos con muros de piedra seca,
  viñedos, villas con piscina, aparcamientos llenos, carpas de hospitality,
  torres costeras y un faro.
- Horizonte: anillo de fondo con costa y montañas lejanas.

8. CARIFICACIÓN
- Chimeneas en forma de tubo de escape, estatuas de coche en las esquinas del
  casino, rejillas y faros en las fachadas nobles, peñón del casino con
  silueta de Fiat Topolino vista desde el mar y el aire.
- Monumentos un 30-50 % más grandes que la escala real. Sin logotipos de
  marcas reales.

9. CSP Y AMBIENTE
- Objetos animados: rotor del helicóptero, dirigible genérico, barcos.
- Pantallas: las dos pantallas gigantes de la recta con cámara en directo.
- Luces nocturnas en el casino, el paseo y el puerto (wiki "Tracks – Lights").
- Probar con Pure y con Sol. Vigilar los FPS con 12 coches; si caen,
  niveles de detalle y agrupar mallas por material.

---

Restricciones vigentes del proyecto (del coordinador):
- Assetto Corsa NO esta instalado en este PC (esta en el del amigo): todo se valida con capturas de
  Blender, con los inspectores y con kn5_check.py. No hay forma de medir FPS reales aqui.
- No se sabe aun si el amigo usa Custom Shaders Patch (CSP): lo que dependa de CSP debe ser un extra
  que no rompa nada si no esta; lo esencial debe verse en AC "a pelo".
- Descargar ficheros (texturas CC0, addons) necesita permiso explicito del usuario: en esta fase de
  analisis SOLO se listan (URL, licencia, tamano); no se descarga nada.
- Blender SOLO por la cola 03_blender/_rev/blender_cola.sh (max 6 a la vez en todo el equipo).
- Sin logotipos de marcas reales ni imagenes de la pelicula en el repo publico.
