# PORTO CORSA (Cars 2) — Instalación del circuito en Assetto Corsa

Mod fan sin ánimo de lucro del circuito de Porto Corsa de Cars 2.
5,2 km · 50 curvas · sección de TIERRA real · rotonda Loews · viaducto y rocas-pueblo ·
20 boxes con tribuna · coche-fósil gigante con túnel · yates VIP.

## Novedades de la versión 1.2 ("paleta y fondo")
- **Colores del Mediterráneo**: las casas llevan ahora la paleta de la Riviera (azafrán, ocre, siena, rojo
  pompeyano, crema), tejados de terracota anaranjada, cúpulas de verdín y contraventanas verdes. El césped
  verde vivo solo queda en jardines y rotondas.
- **El monte por zonas**: la ladera ya no es un verde liso. Tiene matorral, hierba seca dorada, tierra y
  roca caliza donde la pendiente es fuerte, con los bordes suaves y sombreado en las hondonadas. De cerca
  lleva grano, para que no parezca plástico.
- **Horizonte**: hay montes y lomas lejanas detrás del circuito, así que el mar ya no acaba en el vacío.
- **Tierra tallada**: en la subida de tierra hay pared de roca a un lado y caída al otro, y la cima es
  una loma redonda.
- La física sigue las mismas reglas que en la 1.1 (vallas y barreras sólidas, muros invisibles para no
  salirse ni atajar, boxes sin saltos), recalculada para el terreno nuevo: 0 fallos en todas las pruebas.
  En la subida de tierra algunos muros invisibles quedan un poco más cerca o más lejos que antes.
- **Con Custom Shaders Patch (CSP) se ve mejor** (luz, sombras y colores más ricos). Sin CSP también
  funciona, pero si lo tienes, actívalo en Content Manager.
- Aparte va **`ensayo_f_pueblo.zip`**: una pista de prueba muy pequeña con solo el pueblo de la subida, para
  comprobar los colores de las fachadas con el filtro Pure (las instrucciones van en su `LEEME.txt`).
  Se instala igual que el circuito y se puede borrar después.
- Si con esta versión el **suelo del monte** se viera negro, a cuadros o muy raro, avísanos con una captura:
  tenemos preparada una variante más sencilla del terreno.

## Qué hay en este zip
- `content/tracks/porto_corsa/` → la carpeta del circuito COMPLETA, con el modelo
  `porto_corsa.kn5` ya generado (no hace falta ksEditor), config, mapa, UI e IA.
- `FUENTES/texturas/` → algunas texturas sueltas (las pequeñas y los mapas del terreno), por si alguien quiere retocar.
- Este archivo.

## INSTALAR (1 minuto)
**Con Content Manager (recomendado):** arrastra el zip `porto_corsa_mod.zip`
encima de la ventana de Content Manager → "Install" → Aceptar. Luego
*Drive → Track → Porto Corsa → Go*.

**A mano:** copia la carpeta `content` del zip encima de tu instalación de
Assetto Corsa (normalmente
`C:/Program Files (x86)/Steam/steamapps/common/assettocorsa/`).
Debe quedar `assettocorsa/content/tracks/porto_corsa/porto_corsa.kn5`.

Si ya tenías una versión anterior de `porto_corsa`, borra esa carpeta antes
(o deja que Content Manager la sobrescriba).

## Si el juego dijera "TRACK NOT FOUND"
Significa que falta el `porto_corsa.kn5` dentro de
`content/tracks/porto_corsa/`. Comprueba que la carpeta se copió entera
(el kn5 pesa bastante). Alternativa manual (solo si hiciera falta): abrir
`assettocorsa/sdk/editor/ksEditor.exe`, *File → Import FBX* con un FBX del
circuito y *File → Save KN5* como `porto_corsa.kn5` en esa carpeta.

## Content Manager (recomendado, gratis)
https://assettocorsa.club/content-manager.html — el launcher que usa todo el
mundo para mods. Con él, instalar/gestionar circuitos y coches es arrastrar
y soltar, y su modo "Custom Shaders Patch + Sol" hace que todo se vea mejor.

## La IA (coches rivales)
El zip incluye una `ai/fast_lane.ai` PROVISIONAL (sigue el centro de la
pista): los bots funcionarán, pero frenan raro y no apuran las curvas.
Para una IA fina (10 minutos):
1. En Content Manager activa la app **AI Line Helper** (o usa el grabador de
   trazada de CSP).
2. Entra en Practice con un coche tranquilo, activa "Record new AI line",
   da 1-2 vueltas LIMPIAS por la trazada ideal (¡pasa por la tierra por el
   centro!), y guarda: se sobreescribe `ai/fast_lane.ai`.

## Problemas típicos
- **El circuito no aparece o TRACK NOT FOUND** → falta el `porto_corsa.kn5`
  o la carpeta no está en `content/tracks/porto_corsa`.
- **En Práctica el coche arranca DENTRO de su garaje**, mirando al pit lane:
  sal despacio por la rampa de la puerta. En el pit lane y los boxes actúa el
  limitador de velocidad de AC (es la superficie PIT); se quita solo al pisar la pista.
- **Los coches salen mirando al revés en parrilla o en boxes** → avísanos y
  lo corregimos en origen (es un dato del modelo; en esta versión ya está orientado).
- **¿Se atraviesan las vallas?** → no: barreras, muros, guardarraíles, vallas
  (también las publicitarias), farolas, maceteros y rocas son sólidos. Además hay
  muros invisibles al final de la escapatoria, junto a los boxes y por dentro de
  las horquillas de tierra (y de las curvas más cerradas), para que no se pueda
  salir del circuito ni atajar por la hierba de un tramo a otro. Si chocas contra "nada" en la hierba, es uno
  de esos muros: vuelve a la pista.
- **Se ve todo muy blanco / lavado** → desde la versión 1.1 los colores y el
  brillo de todos los materiales están recalibrados para Assetto Corsa (antes el
  circuito salía casi blanco). Pruébalo primero con los ajustes de gráficos y de
  tiempo POR DEFECTO (sin tocar brillo, saturación ni filtros): si bajaste cosas
  para la versión anterior, vuelve a dejarlas como estaban. Si con CSP aún se ve
  plano, abre `content/tracks/porto_corsa/extension/ext_config.ini` con el bloc
  de notas y cambia `ACTIVE = 0` por `ACTIVE = 1` en `[MATERIAL_ADJUSTMENT_0]`
  (baja un poco el brillo de todo el circuito; solo funciona con CSP).
  Nos ayuda mucho: dos capturas en el mismo sitio (por ejemplo la recta de meta),
  una con tus ajustes de ahora y otra con los de por defecto, y decirnos qué
  tiempo (weather) y qué filtro (PP filter / Pure / Sol) usas.
- **Rendimiento** → es un circuito grande; con CSP activado va mejor.

## Créditos
Trazado extraído del mapa oficial del Porto Corsa Grand Prix (wiki de Pixar
Cars). Hecho con Blender 5.1 por Arnau & Claude. Cars 2 © Disney/Pixar —
mod de fans, no oficial, no distribuir con ánimo de lucro.
