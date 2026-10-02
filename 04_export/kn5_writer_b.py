# -*- coding: utf-8 -*-
"""
kn5_writer_b.py -- Escritor KN5 (version 5) INDEPENDIENTE ("B") para el circuito Porto Corsa (Assetto Corsa).

Uso (Blender 5.1 headless):
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python kn5_writer_b.py

Fuente de verdad del formato: el lector/escritor C# de AcTools (gro-ove/actools, rama master, commit
e5e5c94b8dee7511def0b670bfd5dbb233831c11 del 2026-06-17), clonado en 04_export/kn5_refs/actools_b/.
En los comentarios las rutas se abrevian como AcTools/... y AcTools.Render/... (relativas a esa carpeta).
  AcTools/Kn5File/Kn5Writer.cs            orden exacto de campos: cabecera, texturas, materiales, nodos
  AcTools/Kn5File/Kn5Basic.cs             SaveInner (orden de secciones), Kn5Reader (tipos leidos), export Collada
  AcTools/Kn5File/Kn5Node.cs              Kn5NodeClass, tipos de los campos (ushort[] Indices, uint MaterialId/Layer)
  AcTools/Kn5File/Kn5Material.cs          ShaderProperty (A float, B vec2, C vec3, D vec4) y TextureMapping
  AcTools/Kn5File/Kn5MaterialBlendMode.cs, Kn5MaterialDepthMode.cs, Kn5Header.cs, Kn5Texture.cs
  AcTools/ExtendedBinaryWriter.cs         Write(string) = int32 longitud + UTF-8; Write(Mat4x4) = M11..M44
  AcTools/ReadAheadBinaryReader.cs        ReadString / ReadMatrix (confirmacion del layout)
  AcTools/Numerics/Mat4x4.cs              Translation = (M41, M42, M43)
  AcTools/CommonAcConsts.cs               Kn5ActualVersion = 5
  AcTools.Render/...                      como se INTERPRETAN los datos (camara RH, ToIndicesFixX, dummies, flags)
  kn5_refs/kn5-converter/kn5 converter/Program.cs (RaduMC): segunda confirmacion independiente de ejes y UV.
NO se ha leido kn5_writer.py (escritor A) ni el addon blender-assetto-corsa-tools: la independencia es el valor.
"""
import bpy
import struct
import os
import sys
import json
import time
import math
import numpy as np
from mathutils import Matrix

BLEND_PATH = "E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/porto_corsa_export.blend"
OUT_DIR = "E:/Escritorio/claude-pc/arnau-aseto-corsa/04_export/kn5"
OUT_KN5 = OUT_DIR + "/porto_corsa_b.kn5"
OUT_JSON = OUT_DIR + "/resumen_writer_b.json"
TEX_DIR = OUT_DIR + "/texturas_b"            # PNG planos generados y copias PNG de imagenes empaquetadas o no-PNG
MAX_VERTS = 65000                            # por encima se parte en '<nombre>_pN' (indices uint16: Kn5Node.cs:26)
EXCLUIR_COLECCIONES = ("LIB",)               # coleccion LIB (y sub-colecciones cuyo nombre empiece por LIB)
SIN_SOMBRA_TOKENS = ("TERRENO", "AGUA")      # castShadows = 0 si el nombre del objeto o de su material lo contiene
TEXTURA_BUSCAR_UPSTREAM = False              # False = solo Image Texture conectada DIRECTAMENTE a Base Color
NOMBRE_RAIZ = "porto_corsa_b"
MAT_FALLBACK = "__sin_material"              # objetos sin material: KN5 exige un materialId valido (Kn5Basic.cs:838-840)

# =====================================================================================================
# 1. FORMATO BINARIO (little-endian, .NET BinaryWriter)
#    Cabecera : "sc6969" (Kn5Writer.cs:6,10) + int32 version = 5 (Kn5Writer.cs:25-29; CommonAcConsts.cs:5).
#               El int32 'Extra' solo existe si version > 5 (Kn5Writer.cs:27-29; Kn5Header.cs:3) -> NO se escribe.
#    Orden    : cabecera, int32 nTexturas + texturas, int32 nMateriales + materiales, arbol de nodos en pre-orden
#               (Kn5Basic.cs:1098-1127 SaveInner; Save_Node Kn5Basic.cs:1089-1094 escribe el nodo y luego sus hijos).
#    Textura  : int32 active(1) + string nombre + int32 longitud + bytes (Kn5Writer.cs:32-36; Kn5Basic.cs:1107-1110;
#               el lector lee la longitud como UInt32: Kn5Basic.cs:1256-1258).
#    String   : int32 numero de bytes + UTF-8 sin terminador (ExtendedBinaryWriter.cs:65-69; ReadAheadBinaryReader.cs:216-221).
#    Material : string nombre, string shader, BYTE blendMode (Kn5Writer.cs:13-15; Kn5MaterialBlendMode.cs: Opaque=0,
#               AlphaBlend=1, AlphaToCoverage=2), BOOL de 1 byte alphaTested (Kn5Writer.cs:42; Kn5Material.cs:15; leido
#               con ReadBoolean en Kn5Basic.cs:1269), INT32 depthMode (Kn5Writer.cs:17-19; Kn5MaterialDepthMode.cs:
#               DepthNormal=0, DepthNoWrite=1, DepthOff=2), int32 nProps + [string nombre, float A, vec2 B, vec3 C, vec4 D]
#               (Kn5Writer.cs:45-53; Kn5Material.cs:39-44; 40 bytes de valores por propiedad: Kn5Basic.cs:1304),
#               int32 nMappings + [string nombre, int32 slot, string textura] (Kn5Writer.cs:55-61; Kn5Material.cs:80-82).
#    Nodo     : int32 clase (Kn5Writer.cs:21-23; Kn5Node.cs:116-125: Base/dummy=1, Mesh=2, SkinnedMesh=3), string nombre,
#               int32 nHijos, bool active (Kn5Writer.cs:65-68).
#      dummy  : 16 floats M11,M12,M13,M14,M21,...,M44 (Kn5Writer.cs:71-73 -> ExtendedBinaryWriter.cs:42-59).
#      mesh   : bool castShadows, bool isVisible, bool isTransparent (Kn5Writer.cs:76-78); int32 nVerts; por vertice
#               pos(3f) normal(3f) uv(2f) tangente(3f) = 44 bytes (Kn5Writer.cs:80-87; Kn5Basic.cs:1340-1346);
#               int32 nIndices + uint16[] (Kn5Writer.cs:89-92; Kn5Node.cs:26 'ushort[] Indices'); uint32 materialId,
#               uint32 layer (Kn5Writer.cs:94-95; Kn5Node.cs:27); float lodIn, float lodOut (Kn5Writer.cs:97-98);
#               vec3 centro de la esfera + float radio (Kn5Writer.cs:100-101); bool isRenderable (Kn5Writer.cs:103).
#    materialId = indice 0-based del material en el orden en que se escribio la seccion de materiales
#               (Kn5Basic.cs:48-50 GetMaterial -> Materials.Values.ElementAtOrDefault((int)id); idem Kn5Basic.cs:838-840).
# =====================================================================================================


class EscritorBinario:
    """Equivalente minimo de ExtendedBinaryWriter (little-endian, como .NET BinaryWriter)."""

    def __init__(self, f):
        self.f = f

    def u8(self, v):
        self.f.write(struct.pack("<B", v))

    def booleano(self, v):
        # BinaryWriter.Write(bool) = 1 byte 0/1 (Kn5Writer.cs:42,68,76-78,103; ReadBoolean en Kn5Basic.cs:1269,1322)
        self.f.write(b"\x01" if v else b"\x00")

    def i32(self, v):
        self.f.write(struct.pack("<i", v))

    def u32(self, v):
        self.f.write(struct.pack("<I", v))

    def f32(self, v):
        self.f.write(struct.pack("<f", v))

    def floats(self, vals):
        self.f.write(struct.pack("<%df" % len(vals), *vals))

    def cadena(self, s):
        # ExtendedBinaryWriter.cs:65-69: int32 numero de bytes + bytes UTF-8, sin terminador nulo
        b = s.encode("utf-8")
        self.i32(len(b))
        self.f.write(b)

    def crudo(self, b):
        self.f.write(b)


# =====================================================================================================
# 2. CONVENCIONES GEOMETRICAS (deducidas de como AcTools lee, exporta y renderiza el KN5)
#  2a. Matriz del dummy. AcTools escribe M11,M12,M13,M14,M21,...,M44 (ExtendedBinaryWriter.cs:42-59) y la traslacion
#      es (M41, M42, M43) (Mat4x4.cs:39-45; AcTools.Render/Base/Utils/SlimDxExtension.cs:194-196 GetTranslationVector).
#      Es la convencion DirectX/SharpDX de VECTOR-FILA (p' = p * M): la matriz guardada es la TRANSPUESTA de la matriz
#      columna-vector de Blender (mathutils: traslacion en m[0][3], m[1][3], m[2][3]). Prueba: al exportar a Collada
#      (matrices columna-vector escritas fila a fila) AcTools emite M11 M21 M31 M41 / M12 M22 M32 M42 / ..., o sea la
#      transpuesta (AcTools/Kn5File/XmlWriterExtension.cs:62-95 MatrixToCollada). Por tanto los 16 floats del KN5 son
#      la matriz AC recorrida por COLUMNAS: [m[0][0], m[1][0], m[2][0], m[3][0], m[0][1], ...]. Es "row-major" solo
#      en el sentido DirectX (vector-fila); respecto a la matriz matematica columna-vector es column-major.
#  2b. La matriz del nodo es LOCAL respecto a su padre: AcTools.Render construye el arbol con
#      RenderableList(node.Name, node.Transform.ToMatrix(), hijos) (AcTools.Render/Kn5Specific/Objects/Kn5RenderableList.cs:20)
#      y compone Matrix = _localMatrix * _parentMatrix (AcTools.Render/Base/Objects/RenderableList.cs:71).
#      Aqui todos los dummies son hijos directos de la raiz (identidad) -> local == matrix_world de Blender convertida.
#  2c. Ejes. AcTools exporta el KN5 a Collada con <up_axis>Y_UP</up_axis> (Kn5Basic.cs:281) copiando posiciones y normales
#      SIN cambios (Kn5Basic.cs:678-690 Vec3ToString; 709 posiciones; 732 normales), y kn5-converter escribe FBX con
#      UpAxis=1 (Y), FrontAxis=2 (Z), CoordAxis=0 (X) y posiciones sin cambios (Program.cs:814-819 y 945-946).
#      Luego las coordenadas KN5 son las de un FBX/Collada Y-arriba de mano derecha. Blender es Z-arriba, asi que
#      se aplica la rotacion de -90 grados en X:  AC(x, y, z) = (bl.x, bl.z, -bl.y).  det(C) = +1 (no es reflexion).
#  2d. Winding. AcTools pasa los indices al Collada (CCW = cara frontal, mano derecha) SIN reordenar (Kn5Basic.cs:826-827).
#      En el visor, AcTools.Render usa camara de mano derecha (CameraBase.cs:8 'RhMode = true'; CameraBase.cs:114
#      PerspectiveFovRH), copia las posiciones tal cual (AcTools.Render/Base/Structs/InputLayouts.cs:209-230) e
#      INTERCAMBIA los indices 1 y 2 de cada triangulo (SlimDxExtension.cs:253-261 ToIndicesFixX, usado en
#      Kn5RenderableObject.cs:38) porque D3D11 considera frontal el sentido HORARIO por defecto
#      (IsFrontCounterclockwise = false, p.ej. CommonStates.cs:182,198,207). Con camara RH + CW-frontal hay que
#      invertir para pintar bien, luego el orden guardado en el KN5 es CCW-frontal en el sistema Y-arriba de mano
#      derecha: exactamente el orden de los loops de Blender tras aplicar C (det +1). NO SE INVIERTE EL WINDING.
#      (Decision documentada a proposito: si el escritor A invierte, la validacion cruzada lo destapara.)
#  2e. UV. Al exportar a Collada (V hacia arriba, como Blender) AcTools escribe (u, -v) (Kn5Basic.cs:755) y kn5-converter
#      escribe v_fbx = 1 - v_kn5 (Program.cs:373,421). DirectX tiene el origen de textura arriba-izquierda, asi que
#      v_kn5 = 1 - v_blender (equivalente a -v modulo 1 con wrap).
#  2f. Tangente: AcTools la copia tal cual al vertex buffer (InputLayouts.cs:223-225). Se calcula con Mesh.calc_tangents
#      (MikkTSpace) cuando hay UV y se rota con C; sin UV se usa un vector perpendicular a la normal.
#  2g. AC_START_* / AC_PIT_* / AC_TIME_* / AC_HOTLAP_START_*: AcTools busca el DUMMY por nombre y lee la traslacion de su
#      matriz: RootNode.GetDummyByName("AC_START_0") y node.Matrix.GetTranslationVector()
#      (AcTools.Render/Kn5SpecificSpecial/TrackMapRenderer.cs:174-175; GetDummyByName solo devuelve Kn5RenderableList,
#      es decir nodos de clase Base/dummy: RenderableListExtension.cs:59-61). Por eso CADA objeto de Blender se escribe
#      como un dummy (clase 1) con su matriz convertida y su malla como hijo (clase 2) en coordenadas locales.
# =====================================================================================================

# Matriz C de cambio de base Blender -> AC (columnas = imagenes de los ejes de Blender):
#   x_bl -> x_ac ; y_bl -> -z_ac ; z_bl -> y_ac   (rotacion de -90 grados alrededor de X)
C_BL2AC = Matrix(((1.0, 0.0, 0.0, 0.0),
                  (0.0, 0.0, 1.0, 0.0),
                  (0.0, -1.0, 0.0, 0.0),
                  (0.0, 0.0, 0.0, 1.0)))
C_AC2BL = C_BL2AC.transposed()   # ortonormal -> la inversa es la transpuesta


def matriz_mundo_ac(mw):
    """matrix_world de Blender (columna-vector) -> misma transformacion expresada en ejes AC (columna-vector).
    p_ac = C p_bl y p_local_ac = C p_local_bl  =>  M_ac = C M_bl C^-1 (asi la malla hija puede ir en locales AC)."""
    return C_BL2AC @ mw @ C_AC2BL


def matriz_a_kn5(m):
    """16 floats en el orden M11,M12,M13,M14,M21,...,M44 de AcTools (ExtendedBinaryWriter.cs:42-59).
    KN5/SharpDX es vector-fila con la traslacion en M41..M43 (Mat4x4.cs:39-45), es decir la TRANSPUESTA de la matriz
    columna-vector de mathutils (traslacion en m[0][3], m[1][3], m[2][3]): se recorre m por columnas (ver 2a)."""
    return [float(m[r][c]) for c in range(4) for r in range(4)]


def vectores_a_ac(a):
    """Array (N,3) en ejes de Blender -> ejes AC: (x, y, z) -> (x, z, -y). Posiciones, normales y tangentes (2c)."""
    out = np.empty_like(a)
    out[:, 0] = a[:, 0]
    out[:, 1] = a[:, 2]
    out[:, 2] = -a[:, 1]
    return out


# =====================================================================================================
# 3. MATERIALES Y TEXTURAS
#    Shader 'ksPerPixel' (AcTools.Render lo acepta en MaterialsProviderSimple.cs:47) con propiedades
#    ksAmbient / ksDiffuse / ksSpecular / ksSpecularEXP en ValueA y ksEmissive en ValueC, que es como las lee
#    AcTools.Render (Kn5SpecificForward/Materials/Kn5MaterialSimple.cs:30-34: GetPropertyValueAByName y
#    GetPropertyValueCByName), y ksAlphaRef en ValueA (Kn5SpecificSpecial/ShadowsRendererBase.cs:279).
#    ksSpecularEXP por defecto 50, el valor que asume AcTools al exportar materiales (Kn5Basic.cs:416).
#    Un unico sampler 'txDiffuse' en el slot 0 (Kn5MaterialSimple.cs:28 GetTexture("txDiffuse")).
# =====================================================================================================

_ORIGEN_TEX = {}   # nombre de textura KN5 -> clave de origen (ruta absoluta o nombre de imagen) para evitar colisiones


def nodo_principled(mat):
    """Principled BSDF 'activo' (el conectado a Surface del Material Output activo) o, si no, el primero del arbol."""
    nt = mat.node_tree
    if nt is None:   # (Material.use_nodes esta obsoleto en 5.x y se retira en 6.0: basta con node_tree)
        return None
    salida = None
    for n in nt.nodes:
        if n.bl_idname == "ShaderNodeOutputMaterial" and (salida is None or n.is_active_output):
            salida = n
    if salida is not None:
        s = salida.inputs.get("Surface")
        if s is not None and s.is_linked and s.links[0].from_node.bl_idname == "ShaderNodeBsdfPrincipled":
            return s.links[0].from_node
    for n in nt.nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            return n
    return None


def color_base_y_alpha(mat):
    """(r, g, b) lineal del socket Base Color y alpha del Principled; sin nodos se usa diffuse_color."""
    pb = nodo_principled(mat)
    if pb is None:
        c = mat.diffuse_color
        return (float(c[0]), float(c[1]), float(c[2])), 1.0
    bc = pb.inputs.get("Base Color")
    al = pb.inputs.get("Alpha")
    rgb = tuple(float(x) for x in bc.default_value[:3]) if bc is not None else (0.8, 0.8, 0.8)
    alpha = float(al.default_value) if (al is not None and not al.is_linked) else 1.0
    return rgb, alpha


def imagen_base_color(mat):
    """Imagen del nodo Image Texture conectado a Base Color. Regla pedida: conexion DIRECTA. Con
    TEXTURA_BUSCAR_UPSTREAM=True se sigue la cadena (Mix, ColorRamp, ...) hasta 4 niveles aguas arriba."""
    pb = nodo_principled(mat)
    if pb is None:
        return None
    bc = pb.inputs.get("Base Color")
    if bc is None or not bc.is_linked:
        return None
    origen = bc.links[0].from_node
    if origen.bl_idname == "ShaderNodeTexImage":
        return origen.image
    if not TEXTURA_BUSCAR_UPSTREAM:
        return None
    frontera, vistos = [origen], set()
    for _ in range(4):
        siguiente = []
        for n in frontera:
            for ent in n.inputs:
                for enlace in ent.links:
                    fn = enlace.from_node
                    if fn.name in vistos:
                        continue
                    vistos.add(fn.name)
                    if fn.bl_idname == "ShaderNodeTexImage" and fn.image is not None:
                        return fn.image
                    siguiente.append(fn)
        frontera = siguiente
    return None


def lineal_a_srgb(c):
    c = min(max(float(c), 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055


def nombre_fichero_seguro(s):
    return "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in s)


def png_plano(nombre_tex, rgb, alpha):
    """PNG 8x8 RGBA del Base Color. Image.pixels de una imagen de 8 bits son los bytes crudos / 255 (comprobado en
    Blender 5.1: pixel 0.5 -> byte 128 en el PNG), asi que el color lineal se codifica a sRGB AQUI antes de asignarlo.
    El alpha del material va al canal A (lo necesita ksPerPixel para alpha blend / alpha test)."""
    img = bpy.data.images.new("tmp_" + nombre_tex, 8, 8, alpha=True)
    pix = np.tile(np.array([lineal_a_srgb(rgb[0]), lineal_a_srgb(rgb[1]), lineal_a_srgb(rgb[2]),
                            min(max(float(alpha), 0.0), 1.0)], dtype=np.float32), 64)
    img.pixels.foreach_set(pix)
    ruta = os.path.join(TEX_DIR, nombre_fichero_seguro(nombre_tex))
    img.filepath_raw = ruta
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    with open(ruta, "rb") as fh:
        return fh.read()


def bytes_imagen_png(img, nombre_tex):
    """Bytes PNG de una imagen de Blender: el fichero .png tal cual; si esta empaquetada (y no es PNG) o el fichero no
    es PNG, se guarda una copia PNG en TEX_DIR y se leen sus bytes."""
    firma = b"\x89PNG\r\n\x1a\n"
    if img.packed_file is not None:
        datos = bytes(img.packed_file.data)
        if datos[:8] == firma:
            return datos
    else:
        ruta = bpy.path.abspath(img.filepath, library=img.library)
        if os.path.isfile(ruta):
            with open(ruta, "rb") as fh:
                datos = fh.read()
            if datos[:8] == firma:
                return datos
    copia = img.copy()
    try:
        copia.filepath_raw = os.path.join(TEX_DIR, nombre_fichero_seguro(nombre_tex))
        copia.file_format = "PNG"
        copia.save()
        with open(copia.filepath_raw, "rb") as fh:
            return fh.read()
    finally:
        bpy.data.images.remove(copia)


def nombre_textura_unico(base, clave_origen):
    """Mismo nombre de fichero desde rutas distintas -> sufijo _2, _3... La misma ruta reutiliza la textura."""
    raiz, ext = os.path.splitext(base)
    nombre, n = base, 1
    while nombre in _ORIGEN_TEX and _ORIGEN_TEX[nombre] != clave_origen:
        n += 1
        nombre = "%s_%d%s" % (raiz, n, ext)
    _ORIGEN_TEX[nombre] = clave_origen
    return nombre


def material_transparente(mat):
    """Alpha blend si Blender lo renderiza 'BLENDED' (EEVEE Next, 4.2+) o blend_method 'BLEND' (legado)."""
    return getattr(mat, "surface_render_method", None) == "BLENDED" or getattr(mat, "blend_method", None) == "BLEND"


def construir_material(mat, registro_texturas):
    """Material KN5 (dict) a partir de un material de Blender (None -> material de respaldo gris).
    registro_texturas: dict nombre_textura -> bytes PNG, que se rellena aqui."""
    if mat is None:
        nombre, rgb, alpha, img, blended = MAT_FALLBACK, (0.6, 0.6, 0.6), 1.0, None, False
    else:
        nombre = mat.name
        rgb, alpha = color_base_y_alpha(mat)
        img = imagen_base_color(mat)
        blended = material_transparente(mat)
    tex_nombre = None
    if img is not None:
        base = os.path.basename(img.filepath) if img.filepath else img.name
        if not base.lower().endswith(".png"):
            base = os.path.splitext(base)[0] + ".png"
        clave = bpy.path.abspath(img.filepath, library=img.library) if (img.filepath and img.packed_file is None) else img.name
        tex_nombre = nombre_textura_unico(base, clave)
        if tex_nombre not in registro_texturas:
            try:
                registro_texturas[tex_nombre] = bytes_imagen_png(img, tex_nombre)
            except Exception as e:
                print("  [aviso] imagen %s no exportable (%s); se usa color plano" % (img.name, e))
                tex_nombre = None
    if tex_nombre is None:
        tex_nombre = "flat_%s.png" % nombre
        if tex_nombre not in registro_texturas:
            registro_texturas[tex_nombre] = png_plano(tex_nombre, rgb, alpha)
    alpha_test = (not blended) and alpha < 0.999
    return {
        "nombre": nombre,
        "shader": "ksPerPixel",
        "blend": 1 if blended else 0,          # byte: Opaque=0 / AlphaBlend=1 (Kn5MaterialBlendMode.cs:6-9; Kn5Writer.cs:13-15)
        "alpha_tested": alpha_test,            # bool de 1 byte (Kn5Writer.cs:42; Kn5Material.cs:15)
        "depth": 0,                            # int32 DepthNormal=0 (Kn5MaterialDepthMode.cs:6; Kn5Writer.cs:17-19)
        "props": [
            ("ksAmbient", 0.45),
            ("ksDiffuse", 0.45),
            ("ksSpecular", 0.4 if blended else 0.1),
            ("ksSpecularEXP", 50.0),           # valor por defecto de AcTools (Kn5Basic.cs:416)
            ("ksEmissive", (0.0, 0.0, 0.0)),   # vec3 -> ValueC (Kn5MaterialSimple.cs:34 GetPropertyValueCByName)
            ("ksAlphaRef", 0.5 if alpha_test else 0.0),
        ],
        "textura": tex_nombre,
        "transparente": blended,
    }


def escribir_material(w, m):
    """Orden exacto de Kn5Writer.cs:38-62."""
    w.cadena(m["nombre"])                      # Kn5Writer.cs:39
    w.cadena(m["shader"])                      # Kn5Writer.cs:40
    w.u8(m["blend"])                           # Kn5Writer.cs:41 -> :13-15 (byte)
    w.booleano(m["alpha_tested"])              # Kn5Writer.cs:42 (bool, 1 byte)
    w.i32(m["depth"])                          # Kn5Writer.cs:43 -> :17-19 (int32)
    w.i32(len(m["props"]))                     # Kn5Writer.cs:45
    for nombre, valor in m["props"]:           # Kn5Writer.cs:46-53: nombre, A(float), B(vec2), C(vec3), D(vec4)
        w.cadena(nombre)
        if isinstance(valor, tuple):           # vec3 -> ValueC (ksEmissive)
            w.f32(0.0)
            w.floats((0.0, 0.0))
            w.floats(valor)
            w.floats((0.0, 0.0, 0.0, 0.0))
        else:                                  # escalar -> ValueA
            w.f32(float(valor))
            w.floats((0.0, 0.0))
            w.floats((0.0, 0.0, 0.0))
            w.floats((0.0, 0.0, 0.0, 0.0))
    w.i32(1)                                   # Kn5Writer.cs:55 nMappings
    w.cadena("txDiffuse")                      # Kn5Writer.cs:58 Name
    w.i32(0)                                   # Kn5Writer.cs:59 Slot
    w.cadena(m["textura"])                     # Kn5Writer.cs:60 Texture (nombre de la textura embebida)


def escribir_textura(w, nombre, datos):
    """Kn5Writer.cs:32-36 + Kn5Basic.cs:1107-1110: int32 active=1, string nombre, int32 longitud, bytes."""
    w.i32(1)
    w.cadena(nombre)
    w.i32(len(datos))
    w.crudo(datos)


# =====================================================================================================
# 4. GEOMETRIA (numpy; se trabaja por esquina/loop para respetar normales partidas y costuras UV)
# =====================================================================================================

def tangente_fallback(normales):
    """Vector unitario perpendicular a cada normal (mallas sin UV; AC solo lo usa en shaders con normal map)."""
    n = normales
    up = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (len(n), 1))
    up[np.abs(n[:, 2]) > 0.99] = (1.0, 0.0, 0.0)
    t = np.cross(n, up)
    norma = np.linalg.norm(t, axis=1)
    norma[norma == 0] = 1.0
    return (t / norma[:, None]).astype(np.float32)


def extraer_malla(ob, depsgraph):
    """Datos por esquina (loop) de la malla, ya en ejes AC y con la V invertida. None si no hay triangulos.
    Claves: pos (V,3) locales, loop_vert (L,), nrm (L,3), uv (L,2), tan (L,3), tris (T,3) loops, tri_mat (T,) slot."""
    usar_eval = len(ob.modifiers) > 0
    ob_eval = ob.evaluated_get(depsgraph) if usar_eval else None
    me = ob_eval.to_mesh() if usar_eval else ob.data
    try:
        me.calc_loop_triangles()
        n_loops, n_tris = len(me.loops), len(me.loop_triangles)
        if n_tris == 0 or n_loops == 0:
            return None
        pos = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", pos)
        loop_vert = np.empty(n_loops, dtype=np.int32)
        me.loops.foreach_get("vertex_index", loop_vert)
        nrm = np.empty(n_loops * 3, dtype=np.float32)
        me.corner_normals.foreach_get("vector", nrm)       # normales partidas por esquina (Blender >= 4.1)
        tris = np.empty(n_tris * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("loops", tris)
        tri_poly = np.empty(n_tris, dtype=np.int32)
        me.loop_triangles.foreach_get("polygon_index", tri_poly)
        poly_mat = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", poly_mat)
        uv = np.zeros((n_loops, 2), dtype=np.float32)
        tan = None
        if len(me.uv_layers) > 0:
            capa = me.uv_layers.active or me.uv_layers[0]
            buf = np.empty(n_loops * 2, dtype=np.float32)
            try:
                capa.uv.foreach_get("vector", buf)
            except Exception:
                capa.data.foreach_get("uv", buf)
            uv = buf.reshape(-1, 2).copy()
            try:
                me.calc_tangents(uvmap=capa.name)          # MikkTSpace; si falla (n-gonos raros) -> fallback
                tan = np.empty(n_loops * 3, dtype=np.float32)
                me.loops.foreach_get("tangent", tan)
                tan = tan.reshape(-1, 3)
            except Exception:
                tan = None
        nrm = vectores_a_ac(nrm.reshape(-1, 3))
        tan = tangente_fallback(nrm) if tan is None else vectores_a_ac(tan)
        uv[:, 1] = 1.0 - uv[:, 1]                           # convencion 2e
        return {
            "pos": vectores_a_ac(pos.reshape(-1, 3)),      # convencion 2c, coordenadas LOCALES del objeto
            "loop_vert": loop_vert, "nrm": nrm, "uv": uv, "tan": tan,
            "tris": tris.reshape(-1, 3),                    # orden de loops de Blender: NO se invierte (2d)
            "tri_mat": poly_mat[tri_poly],
        }
    finally:
        if usar_eval:
            ob_eval.to_mesh_clear()


def submalla_por_material(datos, slot):
    """Vertices unicos (M,11 float32: pos3 nrm3 uv2 tan3) e indices (3T,) de los triangulos del slot indicado."""
    sel = datos["tris"][datos["tri_mat"] == slot]           # (T,3) loops, en el orden de Blender
    esquinas = sel.reshape(-1)
    filas = np.concatenate([
        datos["pos"][datos["loop_vert"][esquinas]],
        datos["nrm"][esquinas], datos["uv"][esquinas], datos["tan"][esquinas]], axis=1).astype(np.float32)
    unicos, inversa = np.unique(filas, axis=0, return_inverse=True)
    return unicos, np.asarray(inversa).reshape(-1).astype(np.int64)


def partir_submalla(verts, idx, maximo=MAX_VERTS):
    """Divide (verts, idx) en trozos de <= maximo vertices, por triangulos consecutivos (remapeando indices)."""
    if len(verts) <= maximo:
        return [(verts, idx)]
    trozos, mapa, locales, nuevos = [], {}, [], []
    for t in range(0, len(idx), 3):
        tri = [int(v) for v in idx[t:t + 3]]
        faltan = len(set(v for v in tri if v not in mapa))
        if len(mapa) + faltan > maximo:
            trozos.append((verts[locales], np.array(nuevos, dtype=np.int64)))
            mapa, locales, nuevos = {}, [], []
        for v in tri:
            if v not in mapa:
                mapa[v] = len(locales)
                locales.append(v)
            nuevos.append(mapa[v])
    if nuevos:
        trozos.append((verts[locales], np.array(nuevos, dtype=np.int64)))
    return trozos


def esfera_envolvente(verts):
    """Centro = centro de la caja local, radio = distancia maxima (coordenadas locales de la malla, como el vertice)."""
    p = verts[:, 0:3]
    c = (p.min(axis=0) + p.max(axis=0)) * 0.5
    r = float(np.sqrt(((p - c) ** 2).sum(axis=1).max())) if len(p) else 0.0
    return (float(c[0]), float(c[1]), float(c[2])), r


def trozos_del_objeto(ob, depsgraph, cache):
    """{slot: [(verts, idx), ...]} del objeto. Se cachea por malla (ob.data) cuando no hay modificadores, porque
    miles de objetos (vegetacion) comparten la misma malla y la geometria local es identica."""
    clave = None if len(ob.modifiers) > 0 else ob.data.name
    if clave is not None and clave in cache:
        return cache[clave]
    datos = extraer_malla(ob, depsgraph)
    res = None
    if datos is not None:
        res = {}
        for k in sorted(set(int(x) for x in np.unique(datos["tri_mat"]))):
            verts, idx = submalla_por_material(datos, k)
            res[k] = partir_submalla(verts, idx)
    if clave is not None:
        cache[clave] = res
    return res


# =====================================================================================================
# 5. NODOS
# =====================================================================================================

def escribir_cabecera_nodo(w, clase, nombre, n_hijos, activo=True):
    """Kn5Writer.cs:65-68: int32 clase, string nombre, int32 nHijos, bool active."""
    w.i32(clase)
    w.cadena(nombre)
    w.i32(n_hijos)
    w.booleano(activo)      # Active=false desactiva el nodo en AcTools (Kn5RenderableObject.cs:42)


def escribir_dummy(w, nombre, m_ac, n_hijos):
    """Nodo clase Base=1 (Kn5Node.cs:118) con la matriz 4x4 (Kn5Writer.cs:71-73; convencion 2a/2b)."""
    escribir_cabecera_nodo(w, 1, nombre, n_hijos)
    w.floats(matriz_a_kn5(m_ac))


def escribir_malla(w, nombre, verts, idx, material_id, sombras, transparente, renderable):
    """Nodo clase Mesh=2 (Kn5Node.cs:121); campos en el orden de Kn5Writer.cs:75-104."""
    escribir_cabecera_nodo(w, 2, nombre, 0)
    w.booleano(sombras)            # castShadows   (Kn5Writer.cs:76; AcTools: IsCastingShadows, Kn5RenderableObject.cs:40)
    w.booleano(True)               # isVisible     (Kn5Writer.cs:77)
    w.booleano(transparente)       # isTransparent (Kn5Writer.cs:78; pase transparente: Kn5RenderableObject.cs:46-50)
    w.i32(len(verts))              # Kn5Writer.cs:80 (el lector lo lee como UInt32: Kn5Basic.cs:1339)
    w.crudo(np.ascontiguousarray(verts, dtype="<f4").tobytes())   # pos3 nrm3 uv2 tan3 = 44 bytes (Kn5Basic.cs:1340-1346)
    w.i32(len(idx))                # Kn5Writer.cs:89
    w.crudo(np.ascontiguousarray(idx, dtype="<u2").tobytes())     # ushort[] (Kn5Node.cs:26; Kn5Writer.cs:90-92)
    w.u32(material_id)             # Kn5Writer.cs:94 (uint, Kn5Node.cs:27)
    w.u32(0)                       # layer (Kn5Writer.cs:95); AcTools solo trata especial Layer==1 (Kn5RenderableObject.cs:46)
    w.f32(0.0)                     # lodIn  } 0/0 = sin limite de distancia (Kn5RenderableObject.cs:52-55)
    w.f32(0.0)                     # lodOut }
    centro, radio = esfera_envolvente(verts)
    w.floats(centro)               # Kn5Writer.cs:100 BoundingSphereCenter
    w.f32(radio)                   # Kn5Writer.cs:101 BoundingSphereRadius
    w.booleano(renderable)         # Kn5Writer.cs:103 (false -> AcTools desactiva la malla: Kn5RenderableObject.cs:42)


def objeto_exportable(ob):
    """MESH visible en la vista actual y fuera de las colecciones excluidas (LIB*)."""
    if ob.type != "MESH" or not ob.visible_get():
        return False
    for c in ob.users_collection:
        if any(c.name == e or c.name.startswith(e) for e in EXCLUIR_COLECCIONES):
            return False
    return True


def sin_sombra(nombre_obj, nombre_mat):
    s = (nombre_obj + "|" + (nombre_mat or "")).upper()
    return any(tok in s for tok in SIN_SOMBRA_TOKENS)


def recorrer_objetos(t0):
    """Primera pasada: escribe los nodos (dummies + mallas) a un fichero temporal 'cuerpo' y va registrando los
    materiales (en orden de primer uso = materialId) y sus texturas. La raiz se escribe al ensamblar."""
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TEX_DIR, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
    escena = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objetos = sorted((ob for ob in escena.objects if objeto_exportable(ob)), key=lambda o: o.name)
    omitidos = sorted(ob.name for ob in escena.objects if ob.type == "MESH" and not objeto_exportable(ob))
    print("Blender %s | objetos MESH exportables: %d | MESH omitidos: %d" % (bpy.app.version_string, len(objetos), len(omitidos)))
    sys.stdout.flush()

    materiales, id_material, texturas, cache = [], {}, {}, {}
    stats = {"dummies": 0, "mallas": 0, "vertices": 0, "triangulos": 0, "trozos_partidos": 0,
             "objetos_sin_triangulos": [], "objetos_sin_uv": 0, "objetos_multimaterial": 0}
    bbox_min = np.array([np.inf, np.inf, np.inf])
    bbox_max = np.array([-np.inf, -np.inf, -np.inf])
    nodos_ac = []
    cuerpo_path = OUT_KN5 + ".cuerpo.tmp"

    def id_de(mat):
        clave = mat.name if mat is not None else MAT_FALLBACK
        if clave not in id_material:
            id_material[clave] = len(materiales)
            materiales.append(construir_material(mat, texturas))
        return id_material[clave]

    with open(cuerpo_path, "wb") as fc:
        w = EscritorBinario(fc)
        for i, ob in enumerate(objetos):
            if i % 250 == 0:
                print("  [%5d/%d] %6.0fs  %s" % (i, len(objetos), time.time() - t0, ob.name))
                sys.stdout.flush()
            por_slot = trozos_del_objeto(ob, depsgraph, cache)
            if not por_slot:
                stats["objetos_sin_triangulos"].append(ob.name)
                continue
            if len(ob.data.uv_layers) == 0:
                stats["objetos_sin_uv"] += 1
            if len(por_slot) > 1:
                stats["objetos_multimaterial"] += 1
            m_ac = matriz_mundo_ac(ob.matrix_world)
            slots = [s.material for s in ob.material_slots]
            es_ac = ob.name.startswith("AC_")
            # Hijos del dummy: una malla por material usado. Con varios materiales se nombran '<nombre>_SUBk',
            # convencion que AcTools reconoce como multi-material (Kn5Basic.cs:843-847). Si un trozo supera
            # MAX_VERTS se parte en '<base>_pN' (N desde 0). Las mallas de los AC_* no se renderizan (renderable=0,
            # Kn5RenderableObject.cs:42): la posicion la da el dummy (2g) y asi los cubitos no se ven en pista.
            hijos = []
            for k, trozos in por_slot.items():
                mat = slots[k] if k < len(slots) else None
                base = ob.name if len(por_slot) == 1 else "%s_SUB%d" % (ob.name, k)
                if len(trozos) > 1:
                    stats["trozos_partidos"] += len(trozos)
                for n, (v, ix) in enumerate(trozos):
                    nombre = base if len(trozos) == 1 else "%s_p%d" % (base, n)
                    hijos.append((nombre, v, ix, id_de(mat),
                                  not sin_sombra(ob.name, mat.name if mat is not None else None),
                                  mat is not None and material_transparente(mat),
                                  not es_ac))
            escribir_dummy(w, ob.name, m_ac, len(hijos))
            stats["dummies"] += 1
            M = np.array([[float(m_ac[r][c]) for c in range(4)] for r in range(4)], dtype=np.float64)
            for (nombre, v, ix, mid, sombras, transp, rend) in hijos:
                escribir_malla(w, nombre, v, ix, mid, sombras, transp, rend)
                stats["mallas"] += 1
                stats["vertices"] += len(v)
                stats["triangulos"] += len(ix) // 3
                pw = v[:, 0:3].astype(np.float64) @ M[:3, :3].T + M[:3, 3]   # a mundo AC para el bbox global
                bbox_min = np.minimum(bbox_min, pw.min(axis=0))
                bbox_max = np.maximum(bbox_max, pw.max(axis=0))
            if es_ac:
                nodos_ac.append({
                    "nombre": ob.name,
                    "pos_kn5_M41_M42_M43": [round(float(m_ac[r][3]), 4) for r in range(3)],
                    "pos_blender": [round(float(x), 4) for x in ob.matrix_world.translation],
                    "rot_z_blender_grados": round(math.degrees(ob.matrix_world.to_euler().z), 3),
                    "hijos": [h[0] for h in hijos],
                })
    print("  pasada de geometria terminada en %.0fs; materiales usados: %d, texturas: %d"
          % (time.time() - t0, len(materiales), len(texturas)))
    sys.stdout.flush()
    return {"cuerpo_path": cuerpo_path, "materiales": materiales, "texturas": texturas, "stats": stats,
            "bbox": (bbox_min, bbox_max), "nodos_ac": nodos_ac, "omitidos": omitidos,
            "n_objetos": len(objetos), "mallas_unicas": len(cache)}


def ensamblar(res):
    """Fichero final en el orden de SaveInner (Kn5Basic.cs:1098-1127): cabecera, texturas, materiales, raiz + cuerpo."""
    with open(OUT_KN5, "wb") as f:
        w = EscritorBinario(f)
        w.crudo(b"sc6969")                            # Kn5Writer.cs:6,10
        w.i32(5)                                      # version (Kn5Writer.cs:25-29; CommonAcConsts.cs:5); sin 'Extra'
        w.i32(len(res["texturas"]))                   # Kn5Basic.cs:1105
        for nombre, datos in res["texturas"].items():
            escribir_textura(w, nombre, datos)        # Kn5Basic.cs:1107-1110
        w.i32(len(res["materiales"]))                 # Kn5Basic.cs:1122
        for m in res["materiales"]:
            escribir_material(w, m)                   # Kn5Basic.cs:1124
        # Raiz: dummy con identidad, como Kn5Node.CreateBaseNode (Kn5Node.cs:100-108; Kn5Basic.cs:1575)
        escribir_dummy(w, NOMBRE_RAIZ, Matrix.Identity(4), res["stats"]["dummies"])
        with open(res["cuerpo_path"], "rb") as fc:    # Kn5Basic.cs:1127 Save_Node(RootNode) -> hijos en pre-orden
            while True:
                b = fc.read(1 << 24)
                if not b:
                    break
                f.write(b)
    os.remove(res["cuerpo_path"])
    return os.path.getsize(OUT_KN5)


def verificar_kn5(ruta):
    """Lector minimo que reproduce Kn5Reader (Kn5Basic.cs:1200-1365: ReadHeader, ReadTexture, ReadMaterial, ReadNode)
    para comprobar que el fichero se recorre entero y termina EXACTAMENTE en EOF. Devuelve contadores."""
    with open(ruta, "rb") as f:
        datos = f.read()
    pos = [0]

    def leer(fmt):
        v = struct.unpack_from("<" + fmt, datos, pos[0])
        pos[0] += struct.calcsize("<" + fmt)
        return v

    def cadena():
        n = leer("i")[0]
        s = datos[pos[0]:pos[0] + n].decode("utf-8")
        pos[0] += n
        return s

    assert datos[:6] == b"sc6969", "firma incorrecta"
    pos[0] = 6
    version = leer("i")[0]
    assert version == 5, "version %d" % version
    n_tex = leer("i")[0]
    tex = {}
    for _ in range(n_tex):
        activo = leer("i")[0]
        nombre = cadena()
        ln = leer("I")[0]
        tex[nombre] = (activo, datos[pos[0]:pos[0] + 8])
        pos[0] += ln
    n_mat = leer("i")[0]
    mats = []
    for _ in range(n_mat):
        nombre, shader = cadena(), cadena()
        blend, alpha_t, depth, n_props = leer("B?ii")
        props = {}
        for _ in range(n_props):
            pn = cadena()
            props[pn] = leer("10f")
        n_maps = leer("i")[0]
        maps = [(cadena(), leer("i")[0], cadena()) for _ in range(n_maps)]
        mats.append((nombre, shader, blend, alpha_t, depth, props, maps))
    cont = {"dummies": 0, "mallas": 0, "vertices": 0, "triangulos": 0, "indices_ok": True, "material_ids_ok": True,
            "max_verts_malla": 0, "nodos_AC_dummy": []}

    def nodo():
        clase = leer("i")[0]
        nombre = cadena()
        hijos = leer("i")[0]
        leer("?")
        if clase == 1:
            m = leer("16f")
            cont["dummies"] += 1
            if nombre.startswith("AC_"):
                cont["nodos_AC_dummy"].append([nombre, [round(x, 3) for x in m[12:15]]])   # M41,M42,M43
        elif clase == 2:
            leer("???")
            nv = leer("I")[0]
            pos[0] += 44 * nv
            ni = leer("I")[0]
            idx = np.frombuffer(datos, dtype="<u2", count=ni, offset=pos[0])
            pos[0] += 2 * ni
            if ni and int(idx.max()) >= nv:
                cont["indices_ok"] = False
            mid, _layer = leer("II")
            leer("ff3ff?")
            if mid >= n_mat:
                cont["material_ids_ok"] = False
            cont["mallas"] += 1
            cont["vertices"] += nv
            cont["triangulos"] += ni // 3
            cont["max_verts_malla"] = max(cont["max_verts_malla"], nv)
        else:
            raise ValueError("clase de nodo inesperada %d en '%s'" % (clase, nombre))
        for _ in range(hijos):
            nodo()

    nodo()
    cont["eof_exacto"] = (pos[0] == len(datos))
    cont["bytes"] = len(datos)
    cont["n_texturas"] = n_tex
    cont["n_materiales"] = n_mat
    cont["texturas_referenciadas_ok"] = all(m[6] and m[6][0][2] in tex for m in mats)
    cont["todas_png"] = all(v[1] == b"\x89PNG\r\n\x1a\n" for v in tex.values())
    cont["shaders"] = sorted(set(m[1] for m in mats))
    cont["ok"] = bool(cont["eof_exacto"] and cont["indices_ok"] and cont["material_ids_ok"]
                      and cont["texturas_referenciadas_ok"] and cont["todas_png"] and cont["max_verts_malla"] <= 65535)
    return cont


def main():
    t0 = time.time()
    res = recorrer_objetos(t0)
    tam = ensamblar(res)
    print("KN5 escrito: %s (%d bytes, %.1f MB) en %.0fs; verificando relectura..." % (OUT_KN5, tam, tam / 1e6, time.time() - t0))
    sys.stdout.flush()
    ver = verificar_kn5(OUT_KN5)
    st = res["stats"]
    bmin, bmax = res["bbox"]
    resumen = {
        "kn5": OUT_KN5, "bytes": tam, "version_kn5": 5, "blend": BLEND_PATH, "blender": bpy.app.version_string,
        "segundos": round(time.time() - t0, 1), "actools_commit": "e5e5c94b8dee7511def0b670bfd5dbb233831c11",
        "n_texturas": len(res["texturas"]), "n_materiales": len(res["materiales"]),
        "n_materiales_con_imagen": sum(1 for m in res["materiales"] if not m["textura"].startswith("flat_")),
        "materiales_alpha_blend": [m["nombre"] for m in res["materiales"] if m["blend"] == 1],
        "n_objetos_exportados": res["n_objetos"], "n_mallas_blender_unicas": res["mallas_unicas"],
        "n_dummies": st["dummies"], "n_mallas": st["mallas"], "n_vertices": st["vertices"], "n_triangulos": st["triangulos"],
        "n_trozos_partidos": st["trozos_partidos"], "n_objetos_multimaterial": st["objetos_multimaterial"],
        "n_objetos_sin_uv": st["objetos_sin_uv"], "objetos_sin_triangulos": st["objetos_sin_triangulos"],
        "objetos_omitidos": res["omitidos"],
        "nodos_AC": res["nodos_ac"],
        "bbox_global_kn5": {"min": [round(float(x), 3) for x in bmin], "max": [round(float(x), 3) for x in bmax]},
        "convenciones": {
            "ejes": "AC(x,y,z) = (bl.x, bl.z, -bl.y); rotacion -90 grados en X, det +1",
            "matriz": "16 floats M11..M44 vector-fila (traslacion en M41..M43) = matriz columna-vector recorrida por columnas; LOCAL al padre (raiz identidad)",
            "winding": "orden de loops de Blender sin invertir (CCW-frontal en mano derecha; AcTools.Render RH + ToIndicesFixX)",
            "uv": "v_kn5 = 1 - v_blender",
            "estructura": "dummy '<objeto>' con matriz + hijo(s) mesh '<objeto>' | '<objeto>_SUBk' | '..._pN' en locales",
            "materiales": "ksPerPixel; blend 1 solo si BLENDED/BLEND; depth 0; txDiffuse slot 0",
            "renderable": "1 salvo mallas hijas de AC_* (0)", "castShadows": "0 si nombre contiene TERRENO/AGUA",
        },
        "verificacion_relectura": ver,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, indent=1, ensure_ascii=False)
    breve = {k: v for k, v in resumen.items() if k not in ("nodos_AC", "objetos_omitidos", "convenciones", "objetos_sin_triangulos")}
    print(json.dumps(breve, indent=1, ensure_ascii=False))
    print("Nodos AC_* (%d): %s" % (len(resumen["nodos_AC"]), ", ".join(n["nombre"] for n in resumen["nodos_AC"])))
    print("Resumen JSON: %s" % OUT_JSON)
    print("KN5_B_OK" if ver["ok"] else "KN5_B_FALLO")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
