# PORTO CORSA (Cars 2) — Instalación del circuito en Assetto Corsa

Mod fan sin ánimo de lucro del circuito de Porto Corsa de Cars 2.
5,2 km · 50 curvas · sección de TIERRA real · rotonda Loews · viaducto y rocas-pueblo ·
20 boxes con tribuna · coche-fósil gigante con túnel · yates VIP.

## Qué hay en este zip
- `content/tracks/porto_corsa/` → la carpeta del circuito COMPLETA, con el modelo
  `porto_corsa.kn5` ya generado (no hace falta ksEditor), config, mapa, UI e IA.
- `FUENTES/texturas/` → las texturas sueltas, por si alguien quiere retocar.
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
- **Se atraviesan las vallas finas** → tienen colisión los muros, guardarraíles,
  barreras de los caminos y rocas; las vallas publicitarias son decorativas.
- **Rendimiento** → es un circuito grande; con CSP activado va mejor.

## Créditos
Trazado extraído del mapa oficial del Porto Corsa Grand Prix (wiki de Pixar
Cars). Hecho con Blender 5.1 por Arnau & Claude. Cars 2 © Disney/Pixar —
mod de fans, no oficial, no distribuir con ánimo de lucro.
