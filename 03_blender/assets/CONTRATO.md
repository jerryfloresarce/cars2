# Contrato de módulos de assets — Porto Corsa (Blender 5.1)

Cada módulo genera PROCEDURALMENTE (solo código, sin archivos externos) un
asset o kit de assets del circuito Porto Corsa de Cars 2, estilo la película:
colores saturados, limpio, ligeramente caricaturesco pero creíble.

## Reglas del módulo `03_blender/assets/<nombre>.py`
- Python para el bpy de **Blender 5.1** (¡API actual! sin `bpy.ops` salvo
  imprescindible; construir mallas con `bpy.data.meshes.new()` +
  `from_pydata()` o `bmesh`).
- Debe definir `def build(parent_collection, seed=0, **params)` que crea los
  objetos, los linka a `parent_collection` y devuelve el objeto raíz
  (un Empty con hijos, o una malla única).
- Kits: además `def build_<pieza>(parent_collection, **params)` por pieza
  (documentadas en el docstring del módulo).
- Unidades: **metros**. Origen del asset en el centro de su base, z=0 en el
  suelo, fachada principal mirando a **+Y**.
- Nombres de objetos y materiales con prefijo del asset
  (p. ej. `CASINO_cupula`, `MAT_CASINO_fachada`).
- Materiales: Principled BSDF con colores planos (nada de texturas de imagen);
  reutilizar material si ya existe (`bpy.data.materials.get(...)`).
- Polycount de videojuego: héroe ≤ 25k tris, pieza de kit ≤ 5k, vegetación ≤ 2k.
- Sin dependencias externas (solo stdlib + bpy + mathutils + math/random).

## Test obligatorio `03_blender/assets/test_<nombre>.py`
- Carga el módulo por ruta (importlib), escena vacía (`--factory-startup`),
  llama a `build()`, encuadra cámara con luz sol + cielo uniforme, y:
  - renderiza `03_blender/assets/previews/<nombre>.png` (EEVEE, 960x720)
  - guarda `03_blender/assets/blend/<nombre>.blend`
- Ejecutar REALMENTE con:
  `& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --factory-startup --python "E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\assets\test_<nombre>.py"`
- Iterar hasta exit limpio y PNG generado. MIRAR el PNG renderizado y mejorar
  el asset al menos una vez (forma, proporciones, colores) antes de dar por
  bueno el resultado.

## Referencia visual
Leer `01_referencias/investigacion.md` (secciones de entorno) para los
detalles de cada asset. Estilo Riviera italiana de Cars 2: fachadas ocre,
salmón, amarillo y crema con persianas verdes, tejados de terracota, piedra
clara en puentes, mar turquesa, mundo "car-ificado" (sin humanos: los
espectadores son coches; escaleras = rampas).
