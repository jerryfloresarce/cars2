# Texturas CC0 (1K JPG) para la fase visual

- **Qué hay**: 14 texturas CC0 (12 de Poly Haven + 2 de ambientCG), una carpeta por textura con sus mapas 1K JPG (diffuse, normal, roughness, AO, displacement); 72 ficheros, 50,5 MB. Lista final de `03_blender/_rev/fase_visual/web_texturas_cc0.md` (sección 5), descargada el 2026-10-04.
- **Inventario**: `manifest.json` (por textura: id, sitio, URL, licencia verificada, dimensiones en m, mapas, convención de la normal, bytes y sha256). Créditos en `CREDITS.txt`; licencia en `LICENSE_CC0.txt`.
- **Normales**: Poly Haven solo `nor_gl` (OpenGL); ambientCG trae `NormalGL` y `NormalDX` (usar una sola; comprobar primero qué convención espera el shader de AC).
- **Aviso**: `adoquin/` (PavingStones150) es 1024x512 de origen; el resto 1024x1024.
- **Cómo se usará**: `recolorear_cc0.py` (bloque 3 del plan) lee estas carpetas, normaliza la media lineal del diffuse, lo tinta con el color base de la paleta Porto Corsa y escribe las `<nombre>_d.png` de 512/1024 px que consume `aplicar_texturas.py` y el escritor KN5 (`TEX_MAX = 1024`). Escala de tileado = 1 / lado_m del manifest.
- **No tocar a mano**: estos JPG son material de origen; lo que se edita es la salida de `recolorear_cc0.py`.
- **NUNCA** subir al repo imágenes 2K/4K/8K de estas texturas (cuadruplican el zip y el escritor las reduce a 1024 igualmente). Solo 1K.
- **Ficheros descartados del zip de ambientCG**: .usdc, .blend, .mtlx, .tres y la vista previa .png (no son mapas); se regeneran bajando el zip cuya URL y sha256 están en el manifest.
