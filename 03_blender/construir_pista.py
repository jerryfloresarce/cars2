# Ensambla el circuito en Blender 5.1 desde geometria_3d.json:
# pista (asfalto/tierra/puente), pianos, faldones y pilas de puente, terreno,
# mar, linea de salida, sol y camaras; guarda .blend y renderiza 4 vistas.
# Ejecutar:
#   blender --background --factory-startup --python construir_pista.py
import json
import math
import os
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Vector

BASE = r'E:\Escritorio\claude-pc\arnau-aseto-corsa'
G = json.load(open(os.environ.get('GEOM', BASE + r'\03_blender\geometria_3d.json'), encoding='utf-8'))
# BLEND_OUT / RENDERS_OUT: solo para PRUEBAS sobre una copia (fase visual: nunca se guarda sobre porto_corsa.blend desde un agente)
OUT_BLEND = os.environ.get('BLEND_OUT', BASE + r'\03_blender\porto_corsa.blend')
OUT_R = os.environ.get('RENDERS_OUT', BASE + r'\03_blender\renders')
os.makedirs(OUT_R, exist_ok=True)
DIR_TEX = BASE + r'\03_blender\texturas'
# MASCARA_DIR: solo para PRUEBAS sobre copia (fase visual F1 r2): carpeta con terreno_mask/base/ao.png de una geometria de ensayo
# sin pisar texturas/ (que escribe mascara_terreno.py en el pipeline). Sin la variable = texturas/ (lo de siempre).
DIR_MASCARA = os.environ.get('MASCARA_DIR', DIR_TEX)
# fase visual (plan decision 0.5): paleta.json es la UNICA fuente de color; mascara_terreno.py (python del sistema) da los
# umbrales de la mascara y el sol de la escena (aqui solo se leen sus constantes: sin scipy no ejecuta nada)
if BASE + r'\03_blender' not in sys.path:
    sys.path.insert(0, BASE + r'\03_blender')
import paleta  # noqa: E402
try:
    import mascara_terreno as _mt  # noqa: E402
except Exception as _e_mt:  # pragma: no cover
    print('AVISO: mascara_terreno no importable (%s): constantes por defecto' % _e_mt)
    _mt = None

S = G['muestras']
N = G['n']

# --- limpieza de escena ---
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

col = bpy.context.scene.collection

def new_mesh_obj(name, verts, faces, mats=None, face_mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if mats:
        for m in mats:
            ob.data.materials.append(m)
        if face_mat:
            for p, mi in zip(me.polygons, face_mat):
                p.material_index = mi
    return ob

def mat(name, rgba, rough=0.8, metal=0.0, emit=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit:
        bsdf.inputs['Emission Color'].default_value = rgba
        bsdf.inputs['Emission Strength'].default_value = emit
    m.diffuse_color = rgba
    return m

def mat_con_ruido(nombre, c1, c2, escala, rough=0.95, bump=0.35):
    """Material con moteado procedural sutil (dos tonos + relieve)."""
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = rough
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = escala
    noise.inputs['Detail'].default_value = 6.0
    mixc = nt.nodes.new('ShaderNodeMix')
    mixc.data_type = 'RGBA'
    mixc.inputs[6].default_value = c1
    mixc.inputs[7].default_value = c2
    nt.links.new(noise.outputs['Fac'], mixc.inputs['Factor'])
    nt.links.new(mixc.outputs[2], bsdf.inputs['Base Color'])
    bmp = nt.nodes.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = bump
    nt.links.new(noise.outputs['Fac'], bmp.inputs['Height'])
    nt.links.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    m.diffuse_color = c1
    return m

M_ASF = mat_con_ruido('MAT_asfalto', (0.105, 0.102, 0.108, 1), (0.075, 0.073, 0.080, 1),
                      140.0, rough=0.85, bump=0.25)
# fase visual: tierra de paleta.json (segundo tono = la misma al 80 % de luminancia, nada de literales)
M_TIE = mat_con_ruido('MAT_tierra', paleta.rgba('tierra'), paleta.variante('tierra', 0.80) + (1.0,), 60.0, rough=1.0, bump=0.5)
M_PUE = mat('MAT_puente_tablero', (0.09, 0.09, 0.10, 1), 0.85)
M_PIE = mat('MAT_piedra', (0.78, 0.72, 0.60, 1), 0.9)
M_KR = mat('MAT_piano_rojo', (0.75, 0.05, 0.05, 1), 0.6)
M_KB = mat('MAT_piano_blanco', (0.9, 0.9, 0.9, 1), 0.6)
# ======================================================================================================================
# >>> MATERIAL TERRENO v2 (fase visual F1, FASE_VISUAL_PLAN.md 3.4-3.5). Bloque IMPORTABLE: solo define constantes y
#     funciones y depende de bpy, math, os, np, G, BASE, DIR_TEX, DIR_MASCARA, paleta, _mt, mat y mat_con_ruido. Los A/B sobre una copia
#     de la escena lo exec()utan sin regenerar (_rev/_tmp_mascara/aplicar_v2_a_copia.py). No mover el marcador '<<<'.
TILES_TERRENO = {   # canal: (tile preferido en texturas/ (lo genera 'materiales'), tile en m, respaldo CC0 tal cual del manifest)
    'R': ('matorral_d.png', 6.0, r'cc0\matorral\aerial_grass_rock_diff_1k.jpg'),
    'G': ('hierba_seca_d.png', 3.0, r'cc0\hierba_seca\withered_grass_diff_1k.jpg'),
    'B': ('tierra_d.png', 6.0, r'cc0\tierra\Ground105_1K-JPG_Color.jpg'),
    'A': ('caliza_d.png', 3.0, r'cc0\roca_caliza\rock_06_diff_1k.jpg'),
}
NORMAL_TERRENO = ('caliza_n.png', r'cc0\roca_caliza\rock_06_nor_gl_1k.jpg', 3.0)   # txDetailNM (OpenGL, Y+ arriba)
TILE_CESPED = ('cesped_d.png', 3.0, 'hierba_d.png')                              # MAT_cesped: solo jardines y rotondas
FACTOR_DETALLE = 0.85          # color = base x (1 - f + f x detalle normalizado), como TEX_multiplicar de aplicar_texturas
MASCARA_FICHEROS = (_mt.FICHEROS if _mt is not None
                    else {'mask': 'terreno_mask.png', 'base': 'terreno_base.png', 'ao': 'terreno_ao.png'})


def _ruta_tex(preferido, respaldo=None):
    for f in (preferido, respaldo):
        if f:
            r = os.path.join(DIR_TEX, f)
            if os.path.exists(r):
                return r
    return None


def _imagen(ruta, no_color=False):
    """Image con ruta ABSOLUTA y colorspace fijo (un datablock = un colorspace); reutiliza si ya esta cargada."""
    espacio = 'Non-Color' if no_color else 'sRGB'
    for img in bpy.data.images:
        try:
            if img.filepath and os.path.normcase(bpy.path.abspath(img.filepath)) == os.path.normcase(ruta) \
                    and img.colorspace_settings.name == espacio:
                return img
        except Exception:
            pass
    img = bpy.data.images.load(ruta, check_existing=False)
    img.filepath = ruta
    img.colorspace_settings.name = espacio
    if no_color:
        img.name = os.path.splitext(os.path.basename(ruta))[0] + '_nc'
    return img


def _media_lineal(img):
    """Media LINEAL por canal del tile (el nodo Image sale en lineal; el PNG/JPG es sRGB). ganancia = 1/media, como
    TEX_ganancia: el tile solo aporta PATRON (media 1) y el color lo pone terreno_base.png (= paleta)."""
    try:
        n = len(img.pixels)
        w, h = img.size
        buf = np.empty(n, np.float32)
        img.pixels.foreach_get(buf)
        rgb = buf.reshape(h, w, -1)[::3, ::3, :3]
        if img.colorspace_settings.name != 'Non-Color':
            rgb = np.where(rgb <= 0.04045, rgb / 12.92, np.power((rgb + 0.055) / 1.055, 2.4))
        m = rgb.reshape(-1, 3).mean(axis=0)
        return tuple(float(max(v, 1e-3)) for v in m)
    except Exception as e:
        print('AVISO: media de %s no legible (%s): ganancia 1' % (img.name, e))
        return (1.0, 1.0, 1.0)


def _ac_props(m, shader='ksPerPixel', samplers=None, props=None, tex_max=None, raw=0, alpha_test=0):
    """Plan decision 5: custom props ac_* en todo material nuevo; por defecto = lo que hace hoy kn5_writer_opt
    (ksPerPixel, txDiffuse tintado a 512, SHADER_PROPS). Cuando abra 04_export (P3/P10) el writer las lee tal cual."""
    m['ac_shader'] = shader
    m['ac_samplers'] = dict(samplers or {})
    m['ac_props'] = dict(props or {})
    m['ac_tex_max'] = dict(tex_max or {})
    m['ac_raw'] = int(raw)
    m['ac_alpha_test'] = int(alpha_test)


def _marcar_texturizado(nt, loc=(-2200, 900)):
    """Marcador que respeta aplicar_texturas.py (idempotencia por nodo 'TEXTURIZADO'): no debe pisar este material."""
    fr = nt.nodes.new('NodeFrame')
    fr.name = 'TEXTURIZADO'
    fr.label = 'TEXTURIZADO (construir_pista v2: aplicar_texturas no lo toca)'
    fr.location = loc
    return fr


def _uv_planar(ob):
    """UV planar del TERRENO: u = (x - x0) / (nx cell), v = (y - y0) / (ny cell) (la de mascara_terreno.py y del multicapa).
    En TERRENO y en las mallas que comparten MAT_terreno (arcenes). El writer exporta uv_layers[0] tal cual."""
    T_ = G['terreno']
    me = ob.data
    if me.uv_layers or len(me.loops) == 0:
        return
    uv = me.uv_layers.new(name='UVMap')
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', vi)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    Lx, Ly = T_['nx'] * T_['cell'], T_['ny'] * T_['cell']
    u = (co[vi, 0] - T_['x0']) / Lx
    v = (co[vi, 1] - T_['y0']) / Ly
    arr = np.ascontiguousarray(np.c_[u, v], dtype=np.float32).ravel()
    try:
        uv.data.foreach_set('uv', arr)
    except Exception:
        uv.uv.foreach_set('vector', arr)


def _mascara_ficheros():
    """Rutas de terreno_mask/base/ao; si faltan, las genera con el python del sistema (mascara_terreno.py, ~5 s).
    El pipeline debe llamar a mascara_terreno.py tras urbanismo.py (parche al integrador); esto es la red de seguridad."""
    rutas = {k: os.path.join(DIR_MASCARA, MASCARA_FICHEROS[k]) for k in ('mask', 'base', 'ao')}
    if not all(os.path.exists(r) for r in rutas.values()):
        geom = os.environ.get('GEOM', BASE + r'\03_blender\geometria_3d.json')
        urb = os.environ.get('URBANISMO', BASE + r'\03_blender\urbanismo.json')
        print('AVISO: faltan PNG de la mascara del terreno en %s: se generan ahora con mascara_terreno.py (el pipeline deberia '
              'haberlo hecho tras urbanismo.py)' % DIR_MASCARA)
        try:
            cp = subprocess.run(['python', os.path.join(BASE, '03_blender', 'mascara_terreno.py'), '--geom', geom, '--urb', urb,
                                 '--out', DIR_MASCARA, '--qa', os.path.join(BASE, '03_blender', 'renders', 'qa')],
                                capture_output=True, text=True, timeout=900)
            print((cp.stdout or '')[-600:])
            if cp.returncode:
                print('mascara_terreno.py fallo (%d): %s' % (cp.returncode, (cp.stderr or '')[-600:]))
        except Exception as e:
            print('mascara_terreno.py no se pudo lanzar: %s' % e)
    return {k: (r if os.path.exists(r) else None) for k, r in rutas.items()}


def _canal_a_en_vertices(ob, ruta_mask):
    """Canal A (roca) de terreno_mask.png muestreado BILINEALMENTE en cada vertice de ob con la UV planar de mundo
    (u = (x - x0) / Lx, v = (y - y0) / Ly; en el buffer de Blender la fila 0 es v = 0 = y minimo, como en el nodo Image).
    Devuelve np.float32 (n_vertices,) o None si la imagen no se puede leer."""
    try:
        img = _imagen(ruta_mask, no_color=True)
        w, h = img.size
        n = len(img.pixels)
        if not (w and h and n == w * h * 4):
            return None
        buf = np.empty(n, np.float32)
        img.pixels.foreach_get(buf)
        A = buf.reshape(h, w, 4)[:, :, 3]
    except Exception as e:
        print('AVISO: canal A de %s no legible (%s)' % (ruta_mask, e))
        return None
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).astype(np.float64)
    M = np.array(ob.matrix_world, np.float64)
    xyw = co @ M[:3, :3].T + M[:3, 3]
    return _canal_a_en_xy(A, xyw)


def _canal_a_en_xy(A, xyw):
    """Canal A (array (h, w), fila 0 = y minimo) muestreado bilinealmente en puntos de MUNDO xyw (n, >= 2) con la UV planar."""
    h, w = A.shape
    T_ = G['terreno']
    Lx, Ly = T_['nx'] * T_['cell'], T_['ny'] * T_['cell']
    u = (xyw[:, 0] - T_['x0']) / Lx
    v = (xyw[:, 1] - T_['y0']) / Ly
    fx = np.clip(u * w - 0.5, 0.0, w - 1.0)
    fy = np.clip(v * h - 0.5, 0.0, h - 1.0)
    ix = np.floor(fx).astype(np.int64)
    iy = np.floor(fy).astype(np.int64)
    ix1 = np.minimum(ix + 1, w - 1)
    iy1 = np.minimum(iy + 1, h - 1)
    tx = (fx - ix).astype(np.float32)
    ty = (fy - iy).astype(np.float32)
    a = (A[iy, ix] * (1 - tx) * (1 - ty) + A[iy, ix1] * tx * (1 - ty) + A[iy1, ix] * (1 - tx) * ty + A[iy1, ix1] * tx * ty)
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def roca_atributo_terreno(ob, mascara_roca=None):
    """Atributo FLOAT POINT 'roca' del TERRENO = canal A de terreno_mask.png en cada vertice (fase visual F1 r3, director_f1_r2.md
    problema 8): la mascara por texel es la UNICA verdad del material, tambien para quien NO la lee. Si el PNG no se puede leer,
    G['mascara_roca'] (v1, como hasta r2).
    Quien lo lee: 04_export/color_ac.separar_roca_terreno (writer de hoy, kn5_writer_opt l.753, y capturas_ab --modo-ac): cara de
    roca si nz < 0.50 o (media del atributo en sus vertices > 0.49 y nz < 0.82). Con mascara_roca (v1) la pared del desmonte del
    63 % de la toma 07 (16, 354) salia en AC como un CUADRADO gris de 8 m (solo los 4 triangulos con nz 0.46-0.47; el atributo
    ahi vale 0) mientras la mascara pintaba de roca los 28 m de la pared. Con el canal A la clasificacion por cara de AC sigue la
    mascara (borde de ruido de 10-30 m, resolucion de cara 4 m): coincidencia con el criterio P1 'A > 0.5 en el centro de la cara
    o nz < 0.35' 96.6 % (antes 95.0 %), y el pie de derrubios (mascara_roca = 0.5, que NO es roca: PETICIONES P1) deja de ser
    roca en AC. En Blender el nodo 'Math.002'/'ROCA_mascara' = max(canal A, atributo con ruido y sin llano, talud) no cambia de
    contrato; integrar_escena._poner_celda sigue subiendo el atributo en los cortes > 2 m. Devuelve (origen, valores) o (None, None)."""
    me = ob.data
    n = len(me.vertices)
    fich = _mascara_ficheros()
    vals, origen = None, None
    if fich.get('mask'):
        vals = _canal_a_en_vertices(ob, fich['mask'])
        if vals is not None and len(vals) == n:
            origen = 'canal A de ' + fich['mask']
        else:
            vals = None
    if vals is None and mascara_roca and len(mascara_roca) == n:
        vals = np.asarray(mascara_roca, np.float32)
        origen = 'mascara_roca de geometria_3d.json (v1: sin PNG legible de la mascara)'
    if vals is None and mascara_roca and len(mascara_roca) < n and _padres_banda(ob) is not None:
        # r4: TERRENO ya subdividido en la banda (puntos medios al final): v1 en la rejilla, media de los padres en los medios
        p0, p1 = _padres_banda(ob)
        mr = np.asarray(mascara_roca, np.float32)
        vals = np.zeros(n, np.float32)
        vals[:len(mr)] = mr
        medio = p0 >= 0
        vals[medio] = 0.5 * (vals[p0[medio]] + vals[p1[medio]])
        origen = 'mascara_roca de geometria_3d.json (v1, interpolada en la banda de 2 m)'
    if vals is None:
        return None, None
    at = me.attributes.get('roca')
    if at is None:
        at = me.attributes.new('roca', 'FLOAT', 'POINT')
    at.data.foreach_set('value', np.ascontiguousarray(vals, dtype=np.float32))
    return origen, vals


def _nodo_math(nodes, links, op, a, b=None, nombre=None, c=None):
    n_ = nodes.new('ShaderNodeMath')
    n_.operation = op
    if nombre:
        n_.name = nombre
    for k, v in ((0, a), (1, b), (2, c)):
        if v is None:
            continue
        if hasattr(v, 'is_linked'):
            links.new(v, n_.inputs[k])
        else:
            n_.inputs[k].default_value = float(v)
    return n_


def _nodo_vec(nodes, links, op, a, b=None, nombre=None, escala=None, c=None):
    n_ = nodes.new('ShaderNodeVectorMath')
    n_.operation = op
    if nombre:
        n_.name = nombre
    for k, v in ((0, a), (1, b), (2, c)):
        if v is None:
            continue
        if hasattr(v, 'is_linked'):
            links.new(v, n_.inputs[k])
        else:
            n_.inputs[k].default_value = tuple(v)
    if escala is not None:
        if hasattr(escala, 'is_linked'):
            links.new(escala, n_.inputs['Scale'])
        else:
            n_.inputs['Scale'].default_value = float(escala)
    return n_


def _enganche_materiales_roca(nt, wA):
    """Bloque 2.1: cuando exista assets/materiales_roca.ng_caliza_estratos() (grupo con salidas Color/Normal en coordenadas
    de MUNDO) la capa de roca lo usa como color y normal. Interfaz esperada en PARCHES_F1_mascara.md. None = caliza propia."""
    try:
        if BASE + r'\03_blender\assets' not in sys.path:
            sys.path.insert(0, BASE + r'\03_blender\assets')
        import materiales_roca  # noqa: F401
    except Exception:
        return None
    if not hasattr(materiales_roca, 'ng_caliza_estratos'):
        return None
    try:
        if hasattr(materiales_roca, 'crear_nodos'):
            grp = materiales_roca.crear_nodos(nt, loc=(-900, -1500), nombre_nodo='ROCA_grupo_caliza')[0]
        else:
            grp = nt.nodes.new('ShaderNodeGroup')
            grp.node_tree = materiales_roca.ng_caliza_estratos()
            grp.name = 'ROCA_grupo_caliza'
            for nombre, val in (('tono_base', paleta.rgba('caliza_ocre')), ('tono_junta', paleta.rgba('caliza_sombra'))):
                if nombre in grp.inputs:
                    grp.inputs[nombre].default_value = val
        grp.label = 'caliza compartida (materiales_roca)'
        if 'Color' in grp.outputs:
            print('MAT_terreno: capa de roca con materiales_roca.ng_caliza_estratos')
            return grp
    except Exception as e:
        print('materiales_roca: enganche fallo (%s): caliza procedural propia' % e)
    return None


def mat_terreno():
    """MAT_terreno v2 (fase visual, bloque 3.5): mascara por TEXEL en vez de rampa por altura + atributo por vertice.
    - UV planar por posicion de mundo (Geometry.Position -> u = (x - x0) / Lx, v = (y - y0) / Ly): identica a la UV real del
      TERRENO; funciona en cualquier cara con este material (arcenes, falda del McLaren) aunque no tenga capa UV.
    - terreno_mask.png (RGBA 2048, Non-Color): pesos R matorral / G hierba seca / B tierra / A roca (mascara_terreno.py).
    - 4 tiles de detalle (UV x Lx/tile_m) normalizados a media 1 (ganancia 1/media): solo PATRON; el color (= paleta.json)
      y la AO vienen en terreno_base.png (txDiffuse del multicapa). color = base x (1 - f + f x sum(peso_k x detalle_k)).
    - ROCA: peso final = max(canal A, atributo 'roca' con ruido y sin llano, talud por normal real) = nodo 'Math.002' con
      etiqueta 'ROCA_mascara' (CONTRATO: lo leen _rev/color_ac/render_ac.py, los revisores, aplicar_texturas y color_ac).
      Los dos ultimos siguen porque el integrador sube el atributo en cortes > 2 m DESPUES de calcular la mascara. Sobre la
      roca, el tono de estratos/grano/meteorizacion de v1 (o assets/materiales_roca cuando exista) y bump + normal de caliza.
    - El writer de hoy (ksPerPixel): diffuse_color = hierba_seca (zona dominante junto a la pista) y la PRIMERA Image sRGB
      enlazada es el tile de hierba seca; 'TEX_mapping' (sin enlazar, 1/3 m) da la escala a --modo-ac y a las mallas sin UV.
    - Custom props ac_*: ksMultilayer_fresnel_nm vanilla (nunca _nm4 en el KN5) con txDiffuse/txMask/txDetailR..A/txDetailNM.
    - Marcador TEXTURIZADO: aplicar_texturas.aplicar_terreno() no lo pisa."""
    m = bpy.data.materials.get('MAT_terreno')
    if m:
        return m
    m = bpy.data.materials.new('MAT_terreno')
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = 1.0
    T_ = G['terreno']
    Lx, Ly = T_['nx'] * T_['cell'], T_['ny'] * T_['cell']
    fich = _mascara_ficheros()
    # --- coordenadas: UV planar por posicion de mundo + Object para los ruidos procedurales (como v1) ---
    geo = nodes.new('ShaderNodeNewGeometry')
    geo.name = 'TERRENO_geometria'
    geo.location = (-2200, 0)
    uv01 = _nodo_vec(nodes, links, 'MULTIPLY_ADD', geo.outputs['Position'], (1.0 / Lx, 1.0 / Ly, 0.0), 'TERRENO_uv_planar',
                     c=(-T_['x0'] / Lx, -T_['y0'] / Ly, 0.0))
    uv01.location = (-2000, 0)
    texm = nodes.new('ShaderNodeTexCoord')
    texm.name = 'TERRENO_texcoord'
    texm.location = (-2200, -600)
    # --- tiles de detalle: G PRIMERO (la primera Image sRGB enlazada es lo que exporta hoy el writer y pinta --modo-ac) ---
    det, samplers, props, tex_max = {}, {}, {}, {}
    for k_, k in enumerate(('G', 'R', 'B', 'A')):
        pref, tile_m, resp = TILES_TERRENO[k]
        ruta = _ruta_tex(pref, resp)
        if ruta is None:
            print('AVISO: sin tile para el canal %s (%s ni %s): sin detalle en ese canal' % (k, pref, resp))
            continue
        img = _imagen(ruta)
        # cambio del INTEGRADOR en fichero de 'mascara' por cierre de F1 (ACOTACIONES 11, PARCHES_F1_materiales.md 18.2): el
        # detalle A (roca) en BOX/Object y no en planta: en planta se estiraba 1/cos(pendiente) = 2-3x en las paredes (estrias
        # de 51/07). Es lo que ya hacen el writer y el proxy AC con TEX_mapping. R/G/B (< 40 grados) siguen en planta.
        if k == 'A':
            esc = _nodo_vec(nodes, links, 'SCALE', texm.outputs['Object'], nombre='TERRENO_obj_A', escala=1.0 / tile_m)
        else:
            esc = _nodo_vec(nodes, links, 'SCALE', uv01.outputs['Vector'], nombre='TERRENO_uv_' + k, escala=Lx / tile_m)
        esc.location = (-1800, 300 - 260 * k_)
        tx = nodes.new('ShaderNodeTexImage')
        tx.name = 'TEX_detalle_' + k
        tx.label = 'detalle %s: %s (%g m)' % (k, os.path.basename(ruta), tile_m)
        tx.image = img
        tx.extension = 'REPEAT'
        tx.interpolation = 'Linear'
        tx.projection = 'BOX' if k == 'A' else 'FLAT'
        tx.projection_blend = 0.3 if k == 'A' else 0.0
        tx.location = (-1600, 300 - 260 * k_)
        links.new(esc.outputs['Vector'], tx.inputs['Vector'])
        gan = _nodo_vec(nodes, links, 'MULTIPLY', tx.outputs['Color'], tuple(1.0 / c for c in _media_lineal(img)),
                        'TERRENO_ganancia_' + k)
        gan.location = (-1300, 300 - 260 * k_)
        det[k] = gan.outputs['Vector']
        samplers['txDetail' + k] = ruta
        props['mult' + k] = round(Lx / tile_m, 2)
        tex_max['txDetail' + k] = 1024
    # 'TEX_mapping' sin enlazar: escala Object para el writer en mallas SIN UV y para capturas_ab --modo-ac (tile de 3 m)
    mp = nodes.new('ShaderNodeMapping')
    mp.name = 'TEX_mapping'
    mp.label = 'solo writer / modo AC (sin UV): Object x 1/3 m'
    mp.inputs['Scale'].default_value = (1.0 / TILES_TERRENO['G'][1],) * 3
    mp.location = (-1800, -800)
    # --- mascara por texel y base ---
    if fich['mask']:
        mk = nodes.new('ShaderNodeTexImage')
        mk.name = 'TERRENO_mascara'
        mk.label = 'terreno_mask.png (RGBA: R matorral, G hierba seca, B tierra, A roca)'
        mk.image = _imagen(fich['mask'], no_color=True)
        mk.extension = 'EXTEND'
        mk.interpolation = 'Cubic'
        mk.location = (-1600, 800)
        links.new(uv01.outputs['Vector'], mk.inputs['Vector'])
        sepm = nodes.new('ShaderNodeSeparateColor')
        sepm.name = 'TERRENO_mascara_RGB'
        sepm.location = (-1300, 800)
        links.new(mk.outputs['Color'], sepm.inputs['Color'])
        pes = {'R': sepm.outputs['Red'], 'G': sepm.outputs['Green'], 'B': sepm.outputs['Blue'], 'A': mk.outputs['Alpha']}
    else:
        print('AVISO: MAT_terreno sin terreno_mask.png: todo hierba seca salvo la roca por atributo/pendiente')
        pes = {'R': 0.0, 'G': 1.0, 'B': 0.0, 'A': 0.0}
    if fich['base']:
        bs = nodes.new('ShaderNodeTexImage')
        bs.name = 'TERRENO_base'
        bs.label = 'terreno_base.png (paleta x parches x AO: txDiffuse)'
        bs.image = _imagen(fich['base'])
        bs.extension = 'EXTEND'
        bs.interpolation = 'Cubic'
        bs.location = (-1600, 1100)
        links.new(uv01.outputs['Vector'], bs.inputs['Vector'])
        base_out = bs.outputs['Color']
    else:
        base_out = None
    # --- ROCA: talud por normal real + atributo 'roca' (v1, con ruido y sin llano) + canal A -> 'Math.002' / 'ROCA_mascara' ---
    sepn = nodes.new('ShaderNodeSeparateXYZ')
    sepn.name = 'ROCA_normal_xyz'
    sepn.location = (-2000, -300)
    links.new(geo.outputs['Normal'], sepn.inputs['Vector'])
    nf = nodes.new('ShaderNodeTexNoise')
    nf.name = 'ROCA_ruido_borde'
    nf.inputs['Scale'].default_value = 0.4       # ~2.5 m
    nf.inputs['Detail'].default_value = 3.0
    nf.location = (-2000, -600)
    links.new(texm.outputs['Object'], nf.inputs['Vector'])
    ng_ = nodes.new('ShaderNodeTexNoise')
    ng_.name = 'ROCA_ruido_borde_grueso'
    ng_.inputs['Scale'].default_value = 0.09     # ~11 m
    ng_.inputs['Detail'].default_value = 2.0
    ng_.location = (-2000, -850)
    links.new(texm.outputs['Object'], ng_.inputs['Vector'])
    r_t = _nodo_math(nodes, links, 'MULTIPLY_ADD', nf.outputs['Fac'], 0.08, 'ROCA_ruido_talud', c=-0.04)
    s_t = _nodo_math(nodes, links, 'ADD', sepn.outputs['Z'], r_t.outputs['Value'], 'ROCA_nz_ruido')
    talud = nodes.new('ShaderNodeMapRange')
    talud.name = 'ROCA_talud'
    talud.clamp = True
    talud.interpolation_type = 'SMOOTHSTEP'
    talud.inputs['From Min'].default_value = 0.50
    talud.inputs['From Max'].default_value = 0.56
    talud.inputs['To Min'].default_value = 1.0
    talud.inputs['To Max'].default_value = 0.0
    links.new(s_t.outputs['Value'], talud.inputs['Value'])
    atr = nodes.new('ShaderNodeAttribute')
    atr.name = 'ROCA_atributo'
    atr.attribute_name = 'roca'
    atr.location = (-2000, -1100)
    r_a = _nodo_math(nodes, links, 'MULTIPLY_ADD', nf.outputs['Fac'], 0.30, 'ROCA_ruido_atributo', c=-0.15)
    r_g = _nodo_math(nodes, links, 'MULTIPLY_ADD', ng_.outputs['Fac'], 0.36, 'ROCA_ruido_atributo_grueso', c=-0.18)
    r_ag = _nodo_math(nodes, links, 'ADD', r_a.outputs['Value'], r_g.outputs['Value'], 'ROCA_ruido_atributo_total')
    s_a = _nodo_math(nodes, links, 'ADD', atr.outputs['Fac'], r_ag.outputs['Value'], 'ROCA_atributo_ruido')
    umb = nodes.new('ShaderNodeMapRange')
    umb.name = 'ROCA_umbral_atributo'
    umb.clamp = True
    umb.interpolation_type = 'SMOOTHSTEP'
    umb.inputs['From Min'].default_value = 0.47
    umb.inputs['From Max'].default_value = 0.51
    links.new(s_a.outputs['Value'], umb.inputs['Value'])
    llano = nodes.new('ShaderNodeMapRange')
    llano.name = 'ROCA_llano_hierba'
    llano.clamp = True
    llano.interpolation_type = 'SMOOTHSTEP'
    llano.inputs['From Min'].default_value = 0.78
    llano.inputs['From Max'].default_value = 0.86
    llano.inputs['To Min'].default_value = 1.0
    llano.inputs['To Max'].default_value = 0.0
    links.new(sepn.outputs['Z'], llano.inputs['Value'])
    u_l = _nodo_math(nodes, links, 'MULTIPLY', umb.outputs['Result'], llano.outputs['Result'], 'ROCA_atributo_sin_llano')
    tex_a = _nodo_math(nodes, links, 'MAXIMUM', pes['A'], u_l.outputs['Value'], 'ROCA_mascara_texel')
    mx_r = _nodo_math(nodes, links, 'MAXIMUM', talud.outputs['Result'], tex_a.outputs['Value'], 'Math.002')
    mx_r.label = 'ROCA_mascara'
    mx_r.location = (-900, -300)
    if mx_r.name != 'Math.002':
        print('AVISO: el nodo de la mascara de roca no se llama Math.002 (%s): revisar los lectores' % mx_r.name)
    wA = mx_r.outputs['Value']
    # --- pesos: R, G, B reparten (1 - roca); A = roca ---
    resto = _nodo_math(nodes, links, 'SUBTRACT', 1.0, wA, 'TERRENO_resto')
    s_rg = _nodo_math(nodes, links, 'ADD', pes['R'], pes['G'], 'TERRENO_suma_RG')
    s_rgb = _nodo_math(nodes, links, 'ADD', s_rg.outputs['Value'], pes['B'], 'TERRENO_suma_RGB')
    s_rgb = _nodo_math(nodes, links, 'MAXIMUM', s_rgb.outputs['Value'], 1e-4, 'TERRENO_suma_RGB_min')
    norm = _nodo_math(nodes, links, 'DIVIDE', resto.outputs['Value'], s_rgb.outputs['Value'], 'TERRENO_norma')
    pesos = {}
    for k in ('R', 'G', 'B'):
        pesos[k] = _nodo_math(nodes, links, 'MULTIPLY', pes[k], norm.outputs['Value'], 'TERRENO_peso_' + k).outputs['Value']
    pesos['A'] = wA
    # --- mezcla de detalle por canal y color = base x detalle ---
    mezcla = None
    for k in ('G', 'R', 'B', 'A'):
        if k not in det:
            continue
        pk = _nodo_vec(nodes, links, 'SCALE', det[k], nombre='TERRENO_detalle_' + k, escala=pesos[k])
        mezcla = pk if mezcla is None else _nodo_vec(nodes, links, 'ADD', mezcla.outputs['Vector'], pk.outputs['Vector'],
                                                       'TERRENO_detalle_suma_' + k)
    if base_out is None:
        # sin terreno_base.png: color plano por canal (paleta) ponderado
        cols = {'R': paleta.rgb('oliva_oscuro'), 'G': paleta.rgb('hierba_seca'), 'B': paleta.rgb('tierra'), 'A': paleta.rgb('caliza_ocre')}
        acc = None
        for k in ('G', 'R', 'B', 'A'):
            ck = _nodo_vec(nodes, links, 'SCALE', cols[k], nombre='TERRENO_color_' + k, escala=pesos[k])
            acc = ck if acc is None else _nodo_vec(nodes, links, 'ADD', acc.outputs['Vector'], ck.outputs['Vector'], 'TERRENO_color_suma_' + k)
        base_out = acc.outputs['Vector']
    if mezcla is not None:
        f = FACTOR_DETALLE
        detf = _nodo_vec(nodes, links, 'MULTIPLY_ADD', mezcla.outputs['Vector'], (f, f, f), 'TERRENO_detalle', c=(1 - f, 1 - f, 1 - f))
        color = nodes.new('ShaderNodeMix')
        color.name = 'TERRENO_color'
        color.data_type = 'RGBA'
        color.blend_type = 'MULTIPLY'
        color.inputs['Factor'].default_value = 1.0
        links.new(base_out, color.inputs[6])
        links.new(detf.outputs['Vector'], color.inputs[7])
        color.location = (-300, 300)
        color_out = color.outputs[2]
    else:
        color_out = base_out
    # --- normal de caliza (txDetailNM del multicapa): el sampler se registra siempre; en Blender solo se usa sin el grupo ---
    ruta_n = _ruta_tex(NORMAL_TERRENO[0], NORMAL_TERRENO[1])
    if ruta_n:
        samplers['txDetailNM'] = ruta_n
        props['detailNMMult'] = round(Lx / NORMAL_TERRENO[2], 2)
        tex_max['txDetailNM'] = 1024
    # --- capa de roca: tono procedural (estratos/grano/meteorizacion de v1 o materiales_roca) + relieve, solo donde wA ---
    grp = _enganche_materiales_roca(nt, wA)
    if grp is not None:
        col_grp = grp.outputs['Color']
        if 'A' in det:
            # el grupo da el tono (estratos, bancos, juntas); el tile caliza_d da el grano fino, como en AC (txDetailA)
            f = FACTOR_DETALLE
            detA = _nodo_vec(nodes, links, 'MULTIPLY_ADD', det['A'], (f, f, f), 'ROCA_detalle_A', c=(1 - f, 1 - f, 1 - f))
            mulg = nodes.new('ShaderNodeMix')
            mulg.name = 'ROCA_color_grupo_detalle'
            mulg.data_type = 'RGBA'
            mulg.blend_type = 'MULTIPLY'
            mulg.inputs['Factor'].default_value = 1.0
            links.new(col_grp, mulg.inputs[6])
            links.new(detA.outputs['Vector'], mulg.inputs[7])
            col_grp = mulg.outputs[2]
        mixc = nodes.new('ShaderNodeMix')
        mixc.name = 'ROCA_color_grupo'
        mixc.data_type = 'RGBA'
        mixc.blend_type = 'MIX'
        links.new(wA, mixc.inputs['Factor'])
        links.new(color_out, mixc.inputs[6])
        links.new(col_grp, mixc.inputs[7])
        color_out = mixc.outputs[2]
        if 'Normal' in grp.outputs:
            mixn = nodes.new('ShaderNodeMix')
            mixn.name = 'ROCA_normal_grupo'
            mixn.data_type = 'VECTOR'
            links.new(wA, mixn.inputs['Factor'])
            links.new(geo.outputs['Normal'], mixn.inputs[4])
            links.new(grp.outputs['Normal'], mixn.inputs[5])
            nrm = _nodo_vec(nodes, links, 'NORMALIZE', mixn.outputs[1], nombre='ROCA_normal_final')
            links.new(nrm.outputs['Vector'], bsdf.inputs['Normal'])
    else:
        tono, altura = _roca_terreno(nt, texm)
        tono_w = nodes.new('ShaderNodeMix')
        tono_w.name = 'ROCA_tono_pesado'
        tono_w.data_type = 'RGBA'
        tono_w.blend_type = 'MIX'
        tono_w.inputs[6].default_value = (1.0, 1.0, 1.0, 1.0)
        links.new(wA, tono_w.inputs['Factor'])
        links.new(tono, tono_w.inputs[7])
        mixc = nodes.new('ShaderNodeMix')
        mixc.name = 'ROCA_color'
        mixc.data_type = 'RGBA'
        mixc.blend_type = 'MULTIPLY'
        mixc.inputs['Factor'].default_value = 1.0
        links.new(color_out, mixc.inputs[6])
        links.new(tono_w.outputs[2], mixc.inputs[7])
        mixc.location = (-100, 300)
        color_out = mixc.outputs[2]
        # relieve: normal de caliza (CC0 / caliza_n.png, OpenGL) x roca + bump de juntas
        nrm_in = None
        if ruta_n:
            esc_n = _nodo_vec(nodes, links, 'SCALE', uv01.outputs['Vector'], nombre='TERRENO_uv_NM', escala=Lx / NORMAL_TERRENO[2])
            txn = nodes.new('ShaderNodeTexImage')
            txn.name = 'TEX_detalle_NM'
            txn.image = _imagen(ruta_n, no_color=True)
            txn.extension = 'REPEAT'
            txn.location = (-1600, -1300)
            links.new(esc_n.outputs['Vector'], txn.inputs['Vector'])
            nm = nodes.new('ShaderNodeNormalMap')
            nm.name = 'ROCA_normal_map'
            nm.space = 'WORLD'       # sin tangentes fiables en una UV planar: la normal de un suelo en espacio de mundo
            links.new(txn.outputs['Color'], nm.inputs['Color'])
            fuerza = _nodo_math(nodes, links, 'MULTIPLY', wA, 0.6, 'ROCA_normal_fuerza')
            links.new(fuerza.outputs['Value'], nm.inputs['Strength'])
            nrm_in = nm.outputs['Normal']
        alt_w = _nodo_math(nodes, links, 'MULTIPLY', altura, wA, 'ROCA_altura_pesada')
        bmp = nodes.new('ShaderNodeBump')
        bmp.name = 'ROCA_bump'
        bmp.inputs['Strength'].default_value = 0.40
        if 'Distance' in bmp.inputs:
            bmp.inputs['Distance'].default_value = 0.5
        links.new(alt_w.outputs['Value'], bmp.inputs['Height'])
        if nrm_in is not None:
            links.new(nrm_in, bmp.inputs['Normal'])
        links.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    links.new(color_out, bsdf.inputs['Base Color'])
    # --- lo que lee el writer de hoy y las props del multicapa (P3/P10) ---
    m.diffuse_color = paleta.rgba('hierba_seca')
    samplers = dict({'txDiffuse': fich['base'] or '', 'txMask': fich['mask'] or ''}, **samplers)
    props.update({'fresnelC': 0.02, 'fresnelEXP': 3.0, 'fresnelMaxLevel': 0.1, 'ksAmbient': 0.45, 'ksDiffuse': 0.55,
                  'ksSpecular': 0.08, 'ksSpecularEXP': 10.0, 'ksEmissive': 0.0, 'ksAlphaRef': 0.0, 'magicMult': 1.0})
    tex_max.update({'txMask': 2048, 'txDiffuse': 2048})
    _ac_props(m, 'ksMultilayer_fresnel_nm', samplers, props, tex_max, raw=1)
    m['ac_ao'] = fich['ao'] or ''
    _marcar_texturizado(nt)
    print('MAT_terreno v2: mascara %s, base %s, tiles %s, normal %s' % (
        os.path.basename(fich['mask'] or '-'), os.path.basename(fich['base'] or '-'),
        {k: os.path.basename(v) for k, v in samplers.items() if k.startswith('txDetail') and k != 'txDetailNM'},
        os.path.basename(samplers.get('txDetailNM', '-'))))
    return m


def _roca_terreno(nt, texm):
    """Tono y relieve de la caliza del terreno (v2 pista E2-11/C2-13, conservado en v2 del material): juntas de estrato finas
    y onduladas cada ~2.6 m (Wave BANDS en Z), grano de ~2 m y meteorizacion de ~7 m. El COLOR base de la roca ya no sale de
    aqui (ROCA_rampa): lo pone terreno_base.png (caliza_ocre / caliza_gris_calido de paleta.json). Devuelve (tono RGBA, altura)."""
    nodes, links = nt.nodes, nt.links
    wv = nodes.new('ShaderNodeTexWave')
    wv.name = 'ROCA_estratos'
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = 0.12          # periodo 0.314/0.12 = 2.6 m en z
    wv.inputs['Distortion'].default_value = 6.0
    wv.inputs['Detail'].default_value = 4.0
    wv.inputs['Detail Scale'].default_value = 0.5
    if 'Detail Roughness' in wv.inputs:
        wv.inputs['Detail Roughness'].default_value = 0.6
    wv.location = (-2000, -1500)
    links.new(texm.outputs['Object'], wv.inputs['Vector'])
    ne = nodes.new('ShaderNodeMapRange')
    ne.name = 'ROCA_estratos_tono'
    ne.clamp = True
    ne.inputs['From Min'].default_value = 0.0
    ne.inputs['From Max'].default_value = 0.07
    ne.inputs['To Min'].default_value = 0.70         # junta (fondo de la onda): 30 % mas oscura
    ne.inputs['To Max'].default_value = 1.0
    links.new(wv.outputs['Fac'], ne.inputs['Value'])
    n2 = nodes.new('ShaderNodeTexNoise')
    n2.name = 'ROCA_ruido_grano'
    n2.inputs['Scale'].default_value = 0.5
    n2.inputs['Detail'].default_value = 8.0
    n2.inputs['Roughness'].default_value = 0.65
    n2.location = (-2000, -1800)
    links.new(texm.outputs['Object'], n2.inputs['Vector'])
    ng = nodes.new('ShaderNodeMapRange')
    ng.name = 'ROCA_grano_tono'
    ng.clamp = True
    ng.inputs['From Min'].default_value = 0.3
    ng.inputs['From Max'].default_value = 0.7
    ng.inputs['To Min'].default_value = 0.90
    ng.inputs['To Max'].default_value = 1.05
    links.new(n2.outputs['Fac'], ng.inputs['Value'])
    n3 = nodes.new('ShaderNodeTexNoise')
    n3.name = 'ROCA_ruido_meteo'
    n3.inputs['Scale'].default_value = 0.15
    n3.inputs['Detail'].default_value = 4.0
    n3.location = (-2000, -2100)
    links.new(texm.outputs['Object'], n3.inputs['Vector'])
    nm3 = nodes.new('ShaderNodeMapRange')
    nm3.name = 'ROCA_meteo_tono'
    nm3.clamp = True
    nm3.inputs['From Min'].default_value = 0.40
    nm3.inputs['From Max'].default_value = 0.65
    nm3.inputs['To Min'].default_value = 0.86
    nm3.inputs['To Max'].default_value = 1.0
    links.new(n3.outputs['Fac'], nm3.inputs['Value'])
    tono0 = _nodo_math(nodes, links, 'MULTIPLY', ne.outputs['Result'], ng.outputs['Result'], 'ROCA_tono_a')
    tono = _nodo_math(nodes, links, 'MULTIPLY', tono0.outputs['Value'], nm3.outputs['Result'], 'ROCA_tono')
    rgb = nodes.new('ShaderNodeCombineColor')
    rgb.name = 'ROCA_tono_rgb'
    for k in ('Red', 'Green', 'Blue'):
        links.new(tono.outputs['Value'], rgb.inputs[k])
    alt = _nodo_math(nodes, links, 'MULTIPLY_ADD', ne.outputs['Result'], 1.5, 'ROCA_altura_juntas', c=0.0)
    alt = _nodo_math(nodes, links, 'ADD', alt.outputs['Value'], n2.outputs['Fac'], 'ROCA_altura')
    return rgb.outputs['Color'], alt.outputs['Value']


def mat_cesped():
    """MAT_cesped (plan 3.5): cesped SOLO en jardines y rotondas (parterre Loews, jardines del casino, plazoletas/patios,
    rotonda de la palmera); paleta cesped_jardin, tile de 3 m (cesped_d.png de 'materiales'; mientras, hierba_d.png).
    Cadena TEX_mapping / TEX_ganancia / TEX_multiplicar = contrato del writer (tile tintado). Es el UNICO material que
    listara GrassFX (ac_grassfx, bloque 9). Se crea con fake user: lo asignan integrar_escena / kits (parche)."""
    m = bpy.data.materials.get('MAT_cesped')
    if m:
        return m
    m = bpy.data.materials.new('MAT_cesped')
    m.use_nodes = True
    m.use_fake_user = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = 0.95
    col = paleta.rgba('cesped_jardin')
    bsdf.inputs['Base Color'].default_value = col
    m.diffuse_color = col
    ruta = _ruta_tex(TILE_CESPED[0], TILE_CESPED[2])
    samplers = {}
    if ruta:
        img = _imagen(ruta)
        tco = nodes.new('ShaderNodeTexCoord')
        tco.location = (-1000, 0)
        mp = nodes.new('ShaderNodeMapping')
        mp.name = 'TEX_mapping'
        mp.inputs['Scale'].default_value = (1.0 / TILE_CESPED[1],) * 3
        mp.location = (-800, 0)
        links.new(tco.outputs['Object'], mp.inputs['Vector'])
        tx = nodes.new('ShaderNodeTexImage')
        tx.name = 'TEX_cesped'
        tx.image = img
        tx.extension = 'REPEAT'
        tx.projection = 'FLAT'
        tx.location = (-600, 0)
        links.new(mp.outputs['Vector'], tx.inputs['Vector'])
        g = 1.0 / float(np.mean(_media_lineal(img)))
        gan = nodes.new('ShaderNodeMix')
        gan.name = 'TEX_ganancia'
        gan.data_type = 'RGBA'
        gan.blend_type = 'MULTIPLY'
        gan.clamp_result = False
        gan.inputs['Factor'].default_value = 1.0
        gan.inputs[7].default_value = (g, g, g, 1.0)
        gan.location = (-300, 0)
        links.new(tx.outputs['Color'], gan.inputs[6])
        mul = nodes.new('ShaderNodeMix')
        mul.name = 'TEX_multiplicar'
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = FACTOR_DETALLE
        mul.inputs[6].default_value = col
        mul.location = (-100, 0)
        links.new(gan.outputs[2], mul.inputs[7])
        links.new(mul.outputs[2], bsdf.inputs['Base Color'])
        samplers['txDiffuse'] = ruta
    _ac_props(m, 'ksPerPixel', samplers, {'ksAmbient': 0.45, 'ksDiffuse': 0.55, 'ksSpecular': 0.15, 'ksSpecularEXP': 24.0,
                                           'ksEmissive': 0.0, 'ksAlphaRef': 0.0}, {'txDiffuse': 1024})
    m['ac_grassfx'] = 1
    _marcar_texturizado(nt, (-1200, 400))
    return m


def mat_fondo_marino():
    """AGUA_fondo (plan 3.5): material propio en vez de MAT_terreno. Arena apagada mezclada con mar_orilla (paleta); el
    degradado de batimetria turquesa -> profundo es del bloque 6."""
    # F1 cierre (decision 14): los dos tonos son colores de paleta.json (antes c1 = mezcla 0.55 arena + 0.45 mar_orilla,
    # #C2DECF, fuera de paleta): c1 (= diffuse_color, lo que lee el writer) = mar_orilla; c2 = arena al 65 % (paleta.variante)
    c1 = paleta.rgba('mar_orilla')
    c2 = paleta.variante('arena', 0.65) + (1.0,)
    m = mat_con_ruido('MAT_fondo_marino', c1, c2, 0.004, rough=0.95, bump=0.15)
    _ac_props(m, 'ksPerPixel', {}, {'ksAmbient': 0.45, 'ksDiffuse': 0.55, 'ksSpecular': 0.15, 'ksSpecularEXP': 24.0,
                                     'ksEmissive': 0.0, 'ksAlphaRef': 0.0}, {'txDiffuse': 512})
    return m


# ----------------------------------------------------------------------------------------------------------------------
# F1 r4 (ACOTACIONES_COORDINADOR_F1.md 4, director_f1_r3.md n.º 3): mitigacion interina de la 'roca por cara de 4 m con borde
# en sierra' del modo AC (= lo que lee el writer de hoy: 04_export/color_ac.separar_roca_terreno; P1 [W] la quita de verdad):
#   (1) roca_zonas_nz(): en la cima de la postal 56 y en las laderas a < 150 m de las camaras 51 y 07 (mascara_terreno.UMBRALES
#       ['ROCA_NZ_ZONAS'], loc de renders/ab/_base_antes/camaras.json) la roca POR CARA exige nz < ROCA_NZ_ZONA (0.62, 52 grados)
#       en vez del nz < 0.82 general y se limpian los triangulos aislados / huecos (< ROCA_ZONA_MIN_CARAS caras): el atributo
#       'roca' del TERRENO pasa a ser, dentro de la zona, la fraccion de caras de roca incidentes en cada vertice (f_v), que el
#       criterio de color_ac (media de los 3 vertices > 0.49) reproduce sin dientes. Fuera de las zonas el atributo sigue
#       siendo el canal A de la mascara (R3.2); la mascara por texel (modo normal, P1) NO cambia.
#   (2) subdividir_banda_terreno(): triangulos del TERRENO a 2 m (4 por triangulo, puntos medios SOBRE el plano del padre: la
#       superficie no cambia, la clasificacion por cara de AC pasa a 2 m) en la banda de BANDA_2M_M (20 m) junto al asfalto.
#       Se llama al FINAL del pipeline (_rev/banda_terreno_2m.py, parche r4 de PARCHES_F1_mascara.md), nunca aqui: hasta
#       entonces el TERRENO es la rejilla nx*ny que integrar_escena / asentar_objetos / revisar_* editan y leen por j*nx+i
#       (plan 15.7: cell unico). Los vertices nuevos van al FINAL (los nx*ny primeros no cambian de indice) con los atributos
#       INT 'banda_p0'/'banda_p1' (sus dos padres; -1 en la rejilla) para poder re-sincronizarlos si hiciera falta.
# Los umbrales viven en mascara_terreno.UMBRALES (un solo sitio); el nz general de 'terreno' (terreno_montana.umbrales_roca()
# -> geometria_3d.json['extras']['umbrales_roca']['nz'], 0.804) solo se imprime como referencia.
_UMB_R4 = dict(_mt.UMBRALES) if _mt is not None and hasattr(_mt, 'UMBRALES') else {}
ROCA_NZ_ZONA = float(_UMB_R4.get('ROCA_NZ_ZONA', 0.62))
ROCA_ZONA_MIN_CARAS = int(_UMB_R4.get('ROCA_ZONA_MIN_CARAS', 6))
ROCA_ZONA_FUNDIDO_M = float(_UMB_R4.get('ROCA_ZONA_FUNDIDO_M', 30.0))
ROCA_NZ_ZONAS = dict(_UMB_R4.get('ROCA_NZ_ZONAS', {'56_postal_cima_bahia': (47.972, 567.543, 150.0),
                                                    '51_piloto_s1700': (15.023, 426.256, 150.0),
                                                    '07_tierra_subida': (-12.016, 294.887, 150.0)}))
BANDA_2M_M = float(_UMB_R4.get('BANDA_2M_M', 20.0))
# criterio de 04_export/color_ac.separar_roca_terreno COPIADO (solo lectura; 04_export no se toca): cara de roca de MAT_terreno
# si nz < ROCA_NZ o (media del atributo 'roca' de sus vertices > ROCA_ATR y nz < ROCA_NZ_LLANO)
AC_ROCA_NZ, AC_ROCA_ATR, AC_ROCA_NZ_LLANO = 0.50, 0.49, 0.82


def _malla_np(ob):
    """(V mundo (n, 3), tri (nf, 3), material_index (nf,), nz de cara (nf,)) de una malla TRIANGULADA; None si no lo esta."""
    me = ob.data
    n, nf = len(me.vertices), len(me.polygons)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    M = np.array(ob.matrix_world, np.float64)
    V = co.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
    if nf == 0:
        return V, np.zeros((0, 3), np.int64), np.zeros(0, np.int32), np.zeros(0)
    lt = np.empty(nf, np.int32)
    me.polygons.foreach_get('loop_total', lt)
    if not (lt == 3).all():
        return None
    ls = np.empty(nf, np.int32)
    me.polygons.foreach_get('loop_start', ls)
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    tri = lv[np.c_[ls, ls + 1, ls + 2]].astype(np.int64)
    pm = np.empty(nf, np.int32)
    me.polygons.foreach_get('material_index', pm)
    nrm = np.cross(V[tri[:, 1]] - V[tri[:, 0]], V[tri[:, 2]] - V[tri[:, 0]])
    nz = nrm[:, 2] / np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)
    return V, tri, pm, nz


def _peso_zonas(xy):
    """Peso 0..1 de ROCA_NZ_ZONAS en puntos (n, >= 2): 1 dentro, fundido smoothstep en los ultimos ROCA_ZONA_FUNDIDO_M m."""
    wz = np.zeros(len(xy), np.float64)
    for (cx, cy, r) in ROCA_NZ_ZONAS.values():
        t = np.clip((float(r) - np.hypot(xy[:, 0] - cx, xy[:, 1] - cy)) / max(ROCA_ZONA_FUNDIDO_M, 1e-6), 0.0, 1.0)
        wz = np.maximum(wz, t * t * (3.0 - 2.0 * t))
    return wz


def _vecinas_por_arista(tri):
    """Pares (f0, f1) de triangulos que comparten una arista."""
    nf = len(tri)
    e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]).astype(np.int64)
    e.sort(axis=1)
    f = np.tile(np.arange(nf, dtype=np.int64), 3)
    key = e[:, 0] * (int(tri.max()) + 1) + e[:, 1]
    o = np.argsort(key, kind='stable')
    key, f = key[o], f[o]
    igual = key[1:] == key[:-1]
    return np.c_[f[:-1][igual], f[1:][igual]]


def _componentes(nf, pares, sel):
    """Etiqueta (indice minimo) de la componente conexa por aristas de cada cara con sel True; -1 fuera de sel."""
    lab = np.where(sel, np.arange(nf, dtype=np.int64), -1)
    p = pares[sel[pares[:, 0]] & sel[pares[:, 1]]]
    idx = np.flatnonzero(sel)
    if len(p) == 0 or len(idx) == 0:
        return lab
    for _ in range(500):
        prev = lab.copy()
        m = np.minimum(lab[p[:, 0]], lab[p[:, 1]])
        np.minimum.at(lab, p[:, 0], m)
        np.minimum.at(lab, p[:, 1], m)
        lab[idx] = lab[lab[idx]]          # salto de puntero (lab >= 0 en sel)
        lab[idx] = lab[lab[idx]]
        if np.array_equal(lab, prev):
            break
    return lab


def _padres_banda(ob):
    """(p0, p1) int (n,) de los atributos 'banda_p0'/'banda_p1' (-1 en la rejilla) o None si el TERRENO no esta subdividido."""
    me = ob.data
    a0, a1 = me.attributes.get('banda_p0'), me.attributes.get('banda_p1')
    if a0 is None or a1 is None or len(a0.data) != len(me.vertices):
        return None
    p0 = np.empty(len(me.vertices), np.int32)
    p1 = np.empty(len(me.vertices), np.int32)
    a0.data.foreach_get('value', p0)
    a1.data.foreach_get('value', p1)
    return p0, p1


def roca_zonas_nz(ob, atributo='roca'):
    """Aplica (1): dentro de ROCA_NZ_ZONAS, roca por cara solo con nz < ROCA_NZ_ZONA y sin triangulos aislados ni huecos de menos
    de ROCA_ZONA_MIN_CARAS caras; el atributo se funde con el de fuera por el peso de zona. Devuelve dict con cifras (None si no
    hay atributo o la malla no es de triangulos). Idempotente a efectos practicos (segunda pasada: cambios ~0)."""
    me = ob.data
    at = me.attributes.get(atributo)
    if at is None or not ROCA_NZ_ZONAS or at.domain != 'POINT' or at.data_type != 'FLOAT':
        return None
    datos = _malla_np(ob)
    if datos is None:
        print('AVISO roca_zonas_nz: %s no es una malla de triangulos: sin cambios' % ob.name)
        return None
    V, tri, pm, nz = datos
    n, nf = len(V), len(tri)
    a_v = np.empty(n, np.float32)
    at.data.foreach_get('value', a_v)
    a_v = a_v.astype(np.float64)
    es_ter = np.isin(pm, [k for k, m in enumerate(me.materials) if m is not None and m.name == 'MAT_terreno'])
    cf = V[tri].mean(axis=1)
    wz_f = _peso_zonas(cf)
    wz_v = _peso_zonas(V)
    en_zona = wz_f > 0.0
    pares = _vecinas_por_arista(tri)

    def clasificar(av):
        af = av[tri].mean(axis=1)
        return es_ter & ((nz < AC_ROCA_NZ) | ((af > AC_ROCA_ATR) & (nz < AC_ROCA_NZ_LLANO)))

    def dientes(rf):
        nrv = np.zeros(nf, np.int64)
        np.add.at(nrv, pares[:, 0], rf[pares[:, 1]].astype(np.int64))
        np.add.at(nrv, pares[:, 1], rf[pares[:, 0]].astype(np.int64))
        return (rf & (nrv <= 1)), ((~rf) & es_ter & (nrv >= 3))

    r0 = clasificar(a_v)
    # objetivo: fuera de zona lo de hoy; dentro, ademas nz < ROCA_NZ_ZONA (las caras con nz < 0.50 son roca pase lo que pase)
    obj = r0 & (~en_zona | (nz < ROCA_NZ_ZONA))
    for _ in range(2):
        lab = _componentes(nf, pares, obj)
        tam = np.bincount(lab[lab >= 0], minlength=nf)
        en_z = np.bincount(lab[lab >= 0], weights=en_zona[lab >= 0], minlength=nf)
        l_ = np.maximum(lab, 0)
        peq = (lab >= 0) & (tam[l_] < ROCA_ZONA_MIN_CARAS) & (en_z[l_] >= tam[l_] - 0.5) & (nz >= AC_ROCA_NZ)
        obj = obj & ~peq
        lab = _componentes(nf, pares, (~obj) & es_ter)
        tam = np.bincount(lab[lab >= 0], minlength=nf)
        en_z = np.bincount(lab[lab >= 0], weights=en_zona[lab >= 0], minlength=nf)
        l_ = np.maximum(lab, 0)
        hueco = (lab >= 0) & (tam[l_] < ROCA_ZONA_MIN_CARAS) & (en_z[l_] >= tam[l_] - 0.5)
        obj = obj | hueco
    # valores por vertice que reproducen 'obj' con el criterio de color_ac (media de los 3 vertices > 0.49): 1 si TODAS sus
    # caras incidentes son roca, 0 si ninguna, 0.5 si mezcla (las tiras de 1 cara de ancho, p. ej. el desmonte, se conservan:
    # (0.5, 0.5, 0.5) = 0.5 > 0.49). Las caras de hierba con los 3 vertices en la frontera saldrian roca (0.5): se baja a 0.45
    # cualquier vertice suyo cuyas caras de roca incidentes tengan todas un vertice interior (1.0), que es lo normal.
    cnt = np.zeros(n)
    np.add.at(cnt, tri.ravel(), 1.0)
    rs = np.zeros(n)
    np.add.at(rs, tri.ravel(), np.repeat(obj.astype(np.float64), 3))
    t_v = np.where(rs >= cnt - 0.5, 1.0, np.where(rs > 0.0, 0.5, 0.0))
    t_v = np.where(cnt > 0, t_v, 0.0)
    r1 = clasificar(t_v)
    over = r1 & ~obj & (wz_f > 0.999)
    if over.any():
        tiene_int = (t_v[tri] >= 0.999).any(axis=1)
        mal_v = np.zeros(n, bool)
        np.logical_or.at(mal_v, tri[obj & ~tiene_int].ravel(), True)
        cand = np.unique(tri[over].ravel())
        cand = cand[(~mal_v[cand]) & (t_v[cand] == 0.5)]
        t_v[cand] = 0.45
    a_new = a_v * (1.0 - wz_v) + t_v * wz_v
    at.data.foreach_set('value', np.ascontiguousarray(a_new, dtype=np.float32))
    r1 = clasificar(a_new)
    d0, h0 = dientes(r0)
    d1, h1 = dientes(r1)
    talud = nz < AC_ROCA_NZ                       # roca por talud (color_ac): no depende del atributo
    out = {'nz_zona': ROCA_NZ_ZONA, 'min_caras': ROCA_ZONA_MIN_CARAS, 'vertices': int(n), 'caras': int(nf),
           'vertices_en_zona': int((wz_v > 0).sum()), 'vertices_cambiados_0_49': int(((a_v > AC_ROCA_ATR) != (a_new > AC_ROCA_ATR)).sum()),
           'global': {'roca_antes': int(r0.sum()), 'roca_despues': int(r1.sum()), 'dientes_antes': int(d0.sum()), 'dientes_despues': int(d1.sum()),
                      'huecos_antes': int(h0.sum()), 'huecos_despues': int(h1.sum())}, 'zonas': {}}
    for nombre, (cx, cy, r) in ROCA_NZ_ZONAS.items():
        sel = np.hypot(cf[:, 0] - cx, cf[:, 1] - cy) < float(r)
        out['zonas'][nombre] = {'caras_tierra': int((sel & es_ter).sum()), 'roca_antes': int((sel & r0).sum()), 'roca_despues': int((sel & r1).sum()),
                                'roca_talud': int((sel & talud & es_ter).sum()),
                                'dientes_antes': int((sel & d0).sum()), 'dientes_despues': int((sel & d1).sum()),
                                'dientes_despues_talud': int((sel & d1 & talud).sum()),
                                'dientes_despues_anillo': int((sel & d1 & (wz_f > 0.0) & (wz_f < 0.999)).sum()),
                                'huecos_antes': int((sel & h0).sum()), 'huecos_despues': int((sel & h1).sum()),
                                'desacuerdo_objetivo': int((sel & (r1 != obj)).sum())}
    return out


def _banda_celdas(T_, S_, banda_m):
    """Celdas (ny-1, nx-1) con el centro a d_borde en [-cell, banda_m] del asfalto (d_borde = d al eje de la muestra mas cercana
    - w/2) y sin mar en ninguna esquina. Sin scipy: minimo por bloques alrededor de cada muestra (2600 x ~15x15 celdas)."""
    nx_, ny_, c_ = int(T_['nx']), int(T_['ny']), float(T_['cell'])
    x0_, y0_ = float(T_['x0']), float(T_['y0'])
    d = np.full((ny_ - 1, nx_ - 1), np.inf)
    for q in S_:
        r = 0.5 * float(q['w']) + banda_m + 1.5 * c_
        i0 = max(0, int((q['x'] - r - x0_) / c_ - 0.5)); i1 = min(nx_ - 2, int((q['x'] + r - x0_) / c_ + 0.5))
        j0 = max(0, int((q['y'] - r - y0_) / c_ - 0.5)); j1 = min(ny_ - 2, int((q['y'] + r - y0_) / c_ + 0.5))
        if i1 < i0 or j1 < j0:
            continue
        cx = x0_ + (np.arange(i0, i1 + 1) + 0.5) * c_
        cy = y0_ + (np.arange(j0, j1 + 1) + 0.5) * c_
        dd = np.hypot(cx[None, :] - q['x'], cy[:, None] - q['y']) - 0.5 * float(q['w'])
        np.minimum(d[j0:j1 + 1, i0:i1 + 1], dd, out=d[j0:j1 + 1, i0:i1 + 1])
    mar = np.asarray(T_.get('mar') or np.zeros(nx_ * ny_), np.float32).reshape(ny_, nx_) > 0.5
    mar_c = mar[:-1, :-1] | mar[1:, :-1] | mar[1:, 1:] | mar[:-1, 1:]
    return (d >= -c_) & (d <= banda_m) & ~mar_c


def estimar_banda_terreno(T_=None, S_=None, banda_m=None):
    """Recuento previo (sin tocar la malla): celdas de la banda y vertices que anadiria subdividir_banda_terreno."""
    T_ = T_ or G['terreno']; S_ = S_ or G['muestras']
    banda_m = BANDA_2M_M if banda_m is None else float(banda_m)
    cel = _banda_celdas(T_, S_, banda_m)
    nx_ = int(T_['nx'])
    jj, ii = np.nonzero(cel)
    a = jj * nx_ + ii
    lados = np.concatenate([np.c_[a, a + 1], np.c_[a + 1, a + nx_ + 1], np.c_[a + nx_, a + nx_ + 1], np.c_[a, a + nx_]])
    n_lados = len(np.unique(lados[:, 0] * (nx_ * int(T_['ny']) + 1) + lados[:, 1]))
    return {'banda_m': banda_m, 'celdas': int(cel.sum()), 'vertices_nuevos': int(cel.sum()) + n_lados, 'tris_nuevos': 6 * int(cel.sum())}


def subdividir_banda_terreno(ob, banda_m=None, T_=None, S_=None):
    """Aplica (2) sobre el TERRENO (malla de triangulos con la rejilla nx*ny en los primeros vertices). Devuelve dict con cifras;
    None si ya estaba subdividido (idempotente) o no procede. Reconstruye el datablock de malla (vertices originales + puntos
    medios al final; 4 tris por tri de la banda; material por cara heredado; atributos FLOAT POINT interpolados, 'roca' ademas
    re-muestreado del canal A en el punto medio (max con la interpolacion: no se pierden las subidas de integrar_escena);
    'banda_p0'/'banda_p1' INT POINT; UV planar nueva; smooth)."""
    T_ = T_ or G['terreno']; S_ = S_ or G['muestras']
    banda_m = BANDA_2M_M if banda_m is None else float(banda_m)
    me = ob.data
    if _padres_banda(ob) is not None or 'banda_2m' in ob:
        print('banda 2 m: %s ya subdividido (%s): sin cambios' % (ob.name, dict(ob.get('banda_2m', {}))))
        return None
    nx_, ny_ = int(T_['nx']), int(T_['ny'])
    datos = _malla_np(ob)
    if datos is None or len(me.vertices) < nx_ * ny_:
        print('AVISO banda 2 m: %s no es la rejilla triangulada del terreno: sin cambios' % ob.name)
        return None
    V, tri, pm, nz = datos
    n0, nf0 = len(V), len(tri)
    co = np.empty(n0 * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).astype(np.float64)                      # LOCAL (la UV y el canal A usan mundo: matrix_world)
    cel = _banda_celdas(T_, S_, banda_m)
    cf = V[tri].mean(axis=1)
    ci = np.clip(np.floor((cf[:, 0] - float(T_['x0'])) / float(T_['cell'])).astype(np.int64), 0, nx_ - 2)
    cj = np.clip(np.floor((cf[:, 1] - float(T_['y0'])) / float(T_['cell'])).astype(np.int64), 0, ny_ - 2)
    en_banda = cel[cj, ci]
    fb = np.flatnonzero(en_banda)
    if len(fb) == 0:
        print('banda 2 m: ninguna cara en la banda: sin cambios')
        return None
    # puntos medios unicos de las aristas de los triangulos de la banda
    tb = tri[fb]
    e = np.concatenate([tb[:, [0, 1]], tb[:, [1, 2]], tb[:, [0, 2]]])
    e.sort(axis=1)
    key = e[:, 0] * (n0 + 1) + e[:, 1]
    ukey, inv = np.unique(key, return_inverse=True)
    p0 = (ukey // (n0 + 1)).astype(np.int64)
    p1 = (ukey % (n0 + 1)).astype(np.int64)
    n_m = len(ukey)
    m_ab, m_bc, m_ac = (n0 + inv[:len(fb)], n0 + inv[len(fb):2 * len(fb)], n0 + inv[2 * len(fb):])
    a_, b_, c_ = tb[:, 0], tb[:, 1], tb[:, 2]
    sub = np.concatenate([np.c_[a_, m_ab, m_ac], np.c_[m_ab, b_, m_bc], np.c_[m_ac, m_bc, c_], np.c_[m_ab, m_bc, m_ac]])
    sub_pm = np.tile(pm[fb], 4)
    keep = np.flatnonzero(~en_banda)
    tri_new = np.vstack([tri[keep], sub])
    pm_new = np.concatenate([pm[keep], sub_pm])
    co_new = np.vstack([co, 0.5 * (co[p0] + co[p1])])
    # atributos FLOAT POINT: media de los padres; 'roca': max(media, canal A en el punto medio)
    attrs = {}
    for at in list(me.attributes):
        if at.domain == 'POINT' and at.data_type == 'FLOAT' and len(at.data) == n0 and not at.name.startswith('.'):
            v = np.empty(n0, np.float32)
            at.data.foreach_get('value', v)
            attrs[at.name] = np.concatenate([v, 0.5 * (v[p0] + v[p1])]).astype(np.float32)
    canal_a_ok = False
    if 'roca' in attrs:
        fich = _mascara_ficheros()
        if fich.get('mask'):
            try:
                img = _imagen(fich['mask'], no_color=True)
                w_, h_ = img.size
                buf = np.empty(len(img.pixels), np.float32)
                img.pixels.foreach_get(buf)
                A = buf.reshape(h_, w_, 4)[:, :, 3]
                M = np.array(ob.matrix_world, np.float64)
                xyw = co_new[n0:] @ M[:3, :3].T + M[:3, 3]
                a_m = _canal_a_en_xy(A, xyw)
                attrs['roca'][n0:] = np.maximum(attrs['roca'][n0:], a_m)
                canal_a_ok = True
            except Exception as e_:
                print('AVISO banda 2 m: canal A no legible en los puntos medios (%s): atributo interpolado' % e_)
    mats = [m for m in me.materials]
    nombre_me = me.name
    me.name = nombre_me + '_rejilla'
    me2 = bpy.data.meshes.new(nombre_me)
    me2.from_pydata([tuple(v) for v in co_new], [], [tuple(int(k) for k in t) for t in tri_new])
    me2.update()
    for m in mats:
        me2.materials.append(m)
    me2.polygons.foreach_set('material_index', np.ascontiguousarray(pm_new, dtype=np.int32))
    for nombre, v in attrs.items():
        at2 = me2.attributes.new(nombre, 'FLOAT', 'POINT')
        at2.data.foreach_set('value', np.ascontiguousarray(v, dtype=np.float32))
    pad0 = np.concatenate([np.full(n0, -1, np.int32), p0.astype(np.int32)])
    pad1 = np.concatenate([np.full(n0, -1, np.int32), p1.astype(np.int32)])
    for nombre, v in (('banda_p0', pad0), ('banda_p1', pad1)):
        at2 = me2.attributes.new(nombre, 'INT', 'POINT')
        at2.data.foreach_set('value', np.ascontiguousarray(v, dtype=np.int32))
    for k in me.keys():
        try:
            me2[k] = me[k]
        except Exception:
            pass
    ob.data = me2
    me2.shade_smooth()
    _uv_planar(ob)
    if me.users == 0:
        bpy.data.meshes.remove(me)
    out = {'banda_m': banda_m, 'celdas': int(cel.sum()), 'caras_banda': int(len(fb)), 'vertices_antes': int(n0), 'vertices_despues': int(len(co_new)),
           'vertices_nuevos': int(n_m), 'tris_antes': int(nf0), 'tris_despues': int(len(tri_new)), 'canal_a_en_medios': canal_a_ok,
           'atributos': sorted(attrs)}
    ob['banda_2m'] = {k: v for k, v in out.items() if not isinstance(v, list)}
    return out


def sincronizar_banda_terreno(ob):
    """Re-coloca los puntos medios de la banda (co = media de los dos padres) y su atributo 'roca' (max con la media de los padres)
    tras mover vertices de la rejilla. No la usa el pipeline (la banda se hace al final); queda por si algun paso posterior
    moviera la rejilla. Devuelve el numero de puntos medios o None."""
    pad = _padres_banda(ob)
    if pad is None:
        return None
    p0, p1 = pad
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    medio = p0 >= 0
    co[medio] = 0.5 * (co[p0[medio]] + co[p1[medio]])
    me.vertices.foreach_set('co', np.ascontiguousarray(co).ravel())
    at = me.attributes.get('roca')
    if at is not None and len(at.data) == n:
        v = np.empty(n, np.float32)
        at.data.foreach_get('value', v)
        v[medio] = np.maximum(v[medio], 0.5 * (v[p0[medio]] + v[p1[medio]]))
        at.data.foreach_set('value', np.ascontiguousarray(v))
    me.update()
    return int(medio.sum())
# <<< MATERIAL TERRENO v2
# ======================================================================================================================

M_TER = mat_terreno()
M_FONDO = M_TER
M_CESPED = mat_cesped()
M_FONDO_MAR = mat_fondo_marino()
M_AGUA = mat('MAT_agua', (0.05, 0.42, 0.55, 1), 0.15)
M_LINEA = mat('MAT_linea_salida', (0.95, 0.95, 0.95, 1), 0.5)

MAT_IDX = {'straight': 0, 'tech': 0, 'norm': 0, 'dirt': 1, 'bridge': 0}   # pavimento NORMALIZADO: el mismo asfalto en todo el circuito (tambien en el viaducto)

# --- pista ---
def edge_pts(i):
    p = S[i]
    half = p['w'] / 2.0
    dzl = -p['lat'] * half
    L_ = (p['x'] + p['nx'] * half, p['y'] + p['ny'] * half, p['z'] + dzl)
    R_ = (p['x'] - p['nx'] * half, p['y'] - p['ny'] * half, p['z'] - dzl)
    return L_, R_

verts = []
for i in range(N):
    L_, R_ = edge_pts(i)
    verts.extend([L_, R_])
faces = []
fmat = []
for i in range(N):
    j = (i + 1) % N
    faces.append((2 * i, 2 * i + 1, 2 * j + 1, 2 * j))
    fmat.append(MAT_IDX[S[i]['sec']])
pista = new_mesh_obj('PISTA', verts, faces, [M_ASF, M_TIE, M_PUE], fmat)
pista.data.shade_smooth()

# --- utilidades de interpolacion a lo largo de la pista ---
def muestra_s(s_m):
    """Muestra interpolada en la abscisa s_m (m)."""
    f = (s_m / G['paso_m']) % N
    i = int(f)
    t = f - i
    pa, pb = S[i % N], S[(i + 1) % N]
    q = {k: pa[k] * (1 - t) + pb[k] * t for k in ('x', 'y', 'z', 'nx', 'ny', 'w', 'lat')}
    ln = math.hypot(q['nx'], q['ny']) or 1.0
    q['nx'] /= ln
    q['ny'] /= ln
    return q

def punto_s(s_m, lateral, dz):
    q = muestra_s(s_m)
    return (q['x'] + q['nx'] * lateral, q['y'] + q['ny'] * lateral,
            q['z'] - q['lat'] * lateral + dz)

_lw = G.get('loews') or {}
S_LOEWS = (_lw.get('s_idx') or 0) * G['paso_m']
# radio real de la isleta (mismo calculo que zona_loews en integrar): distancia del
# centro al borde interior del asfalto menos la acera
_R_ISLA = 6.0
if S_LOEWS:
    _ilw = int(_lw['s_idx'])
    _R_ISLA = min(math.hypot(S[j % N]['x'] - _lw['x'], S[j % N]['y'] - _lw['y']) - S[j % N]['w'] / 2
                  for j in range(_ilw - 45, _ilw + 46)) - 0.6

def _curv(i, d=3):
    pa, pb = S[(i - d) % N], S[(i + d) % N]
    return math.atan2(pa['ny'] * pb['nx'] - pa['nx'] * pb['ny'],
                      pa['nx'] * pb['nx'] + pa['ny'] * pb['ny']) / (2 * d * G['paso_m'])

# --- pianos (rojo/blanco) PLANOS y POR DENTRO de la calzada, como en la peli:
# banda de 1.3 m cuyo borde exterior es el borde del asfalto; bloques de 1.3 m ---
PIANO_ANCHO = 1.3
PIANO_BLOQUE = 1.3
kv, kf, kfm = [], [], []
def _piano(s0, s1, sgn):
    """Banda de piano entre las abscisas s0..s1 (m) en el lado sgn (+1 izq, -1 der)."""
    n_b = max(2, int(round((s1 - s0) / PIANO_BLOQUE)))
    base = len(kv)
    for k in range(n_b + 1):
        s_k = s0 + (s1 - s0) * k / n_b
        q = muestra_s(s_k)
        half = q['w'] / 2.0
        kv.append(punto_s(s_k, sgn * (half - 0.04), 0.06))
        kv.append(punto_s(s_k, sgn * (half - 0.04 - PIANO_ANCHO), 0.05))
    for k in range(n_b):
        o = base + 2 * k
        kf.append((o, o + 1, o + 3, o + 2) if sgn < 0 else (o + 1, o, o + 2, o + 3))
        kfm.append(k % 2)

ZONAS_PIANO = []   # (s0, s1, sgn) para que el zigzag sepa donde empiezan
for strip in G['pianos']:
    a_, b_, lado = strip['a'], strip['b'], strip['lado']
    sgn = 1 if lado == 'izq' else -1
    if any(S[i % N]['sec'] == 'dirt' for i in range(a_, b_ + 1)):
        continue
    s0, s1 = a_ * G['paso_m'], b_ * G['paso_m']
    if S_LOEWS and abs((s0 + s1) / 2 - S_LOEWS) < 70:
        continue            # la horquilla lleva su propio juego completo (abajo)
    ZONAS_PIANO.append((s0, s1, sgn))
if S_LOEWS:
    # horquilla de la rotonda: anillo interior completo + exterior en entrada y salida
    _pl = S[int(S_LOEWS / G['paso_m']) % N]
    _ia = int(S_LOEWS / G['paso_m'])
    _in = 1 if _curv(_ia, 4) < 0 else -1       # interior por GEOMETRIA (_curv<0 = curva a izquierdas)
    ZONAS_PIANO.append((S_LOEWS - 56.0, S_LOEWS + 58.0, _in))
    ZONAS_PIANO.append((S_LOEWS - 56.0, S_LOEWS + 58.0, -_in))
for (s0, s1, sgn) in ZONAS_PIANO:
    _piano(s0, s1, sgn)
if kv:
    pianos = new_mesh_obj('PIANOS', kv, kf, [M_KR, M_KB], kfm)

# zonas de ZIGZAG (frenadas casi rectas antes de un piano): se calculan aqui para
# que las lineas de borde sepan donde NO pintarse
ZONAS_ZZ = []        # (s_fin, largo, nombre)
if S_LOEWS:
    ZONAS_ZZ.append((S_LOEWS - 57.0, 34.0, 'horquilla'))
_vistos = []
for (s0, s1, sgn) in ZONAS_PIANO:
    if S_LOEWS and abs(s0 - (S_LOEWS - 56.0)) < 1.0:
        continue
    if not ((3150.0 < s0 < 4350.0) or (4700.0 < s0 < 5050.0)):
        continue
    if any(abs(s0 - v) < 60.0 for v in _vistos):
        continue
    i_a = int((s0 - 30.0) / G['paso_m'])
    if max(abs(_curv(i)) for i in range(i_a - 6, i_a + 12)) > 0.010:
        continue        # la frenada tiene que ser casi recta
    if any(S[i % N]['sec'] == 'dirt' for i in range(i_a - 6, i_a + 16)):
        continue
    ZONAS_ZZ.append((s0 - 1.0, 21.0, 'c%d' % int(s0)))
    _vistos.append(s0)

def sin_linea_de_borde(i, sgn):
    """True donde el borde lo ocupa un piano (de ese lado) o un zigzag (ambos)."""
    s_i = i * G['paso_m']
    for (s0, s1, sg) in ZONAS_PIANO:
        if sg == sgn and s0 - 0.5 <= s_i <= s1 + 0.5:
            return True
    for (s_fin_, largo_, _n) in ZONAS_ZZ:
        if s_fin_ - largo_ - 3.0 <= s_i <= s_fin_ + 0.5:
            return True
    return False

# --- puentes: faldones y pilas ---
bv, bf = [], []
piers = []
run = []
for i in range(N + 1):
    is_b = S[i % N]['sec'] == 'bridge'
    if is_b:
        run.append(i % N)
    if (not is_b or i == N) and run:
        if len(run) > 4:
            for k, idx in enumerate(run):
                L_, R_ = edge_pts(idx)
                for P in (L_, R_):
                    bv.append(P)
                    bv.append((P[0], P[1], P[2] - 3.2))
            off = len(bv) - 4 * len(run)
            for k in range(len(run) - 1):
                o = off + 4 * k
                bf.append((o, o + 1, o + 5, o + 4))          # faldon izq
                bf.append((o + 2, o + 3, o + 7, o + 6))      # faldon der
            for k in range(0, len(run), 8):                  # pila cada ~16 m
                p = S[run[k]]
                piers.append((p['x'], p['y'], p['z']))
        run = []
if bv:
    new_mesh_obj('PUENTE_FALDONES', bv, bf, [M_PIE], [0] * len(bf))
pv, pf = [], []
for (px, py, pz) in piers:
    w = 2.6
    z0, z1 = -4.5, pz - 0.6
    base = len(pv)
    for (dx, dy) in ((-w, -w), (w, -w), (w, w), (-w, w)):
        pv.append((px + dx, py + dy, z0))
        pv.append((px + dx, py + dy, z1))
    for k in range(4):
        a0, a1 = base + 2 * k, base + 2 * ((k + 1) % 4)
        pf.append((a0, a0 + 1, a1 + 1, a1))
if pv:
    new_mesh_obj('PUENTE_PILAS', pv, pf, [M_PIE], [0] * len(pf))

# --- marcas viales (como en la pelicula) ---
M_MB = mat('MAT_marca_blanca', (0.88, 0.88, 0.86, 1), 0.55)
M_MA = mat('MAT_marca_amarilla', (0.95, 0.78, 0.05, 1), 0.55)

def _mp(i):
    """Muestra i (indice) o muestra ya interpolada (dict de muestra_s: extremos de las aceras en las bocas, v3 B4)."""
    return i if isinstance(i, dict) else S[i % N]

def punto_lateral(i, lateral, dz):
    p = _mp(i)
    # OJO: la calzada va PERALTADA; todo lo que se apoya en ella sigue su plano
    return (p['x'] + p['nx'] * lateral, p['y'] + p['ny'] * lateral,
            p['z'] - p['lat'] * lateral + dz)

def ribbon(indices, lateral_fn, width, material, dz=0.035, name='MARCA'):
    vs, fs = [], []
    for k, i in enumerate(indices):
        lat_c = lateral_fn(k, i)
        a = punto_lateral(i, lat_c - width / 2, dz)
        b = punto_lateral(i, lat_c + width / 2, dz)
        vs.extend([a, b])
    for k in range(len(indices) - 1):
        o = 2 * k
        fs.append((o, o + 1, o + 3, o + 2))
    if fs:
        new_mesh_obj(name, vs, fs, [material], [0] * len(fs))

# lineas de borde continuas (no en tierra)
for sgn in (1, -1):
    run = []
    tramo = 0
    for i in range(N + 1):
        ok = S[i % N]['sec'] != 'dirt' and not sin_linea_de_borde(i % N, sgn)
        if ok:
            run.append(i % N)
        if (not ok or i == N) and run:
            if len(run) > 3:
                ribbon(run, lambda k, i2, s=sgn: s * (S[i2]['w'] / 2 - 0.45),
                       0.14, M_MB, name='MARCA_BORDE_%d_%d' % (sgn, tramo))
                tramo += 1
            run = []

# linea central: CONTINUA en el sector del casino (como en la pelicula), a trazos
# cortos dentro de la horquilla y discontinua normal en el resto
_bi = [i for i in range(N) if S[i]['sec'] == 'bridge']
S_CAS0 = 3180.0
S_CAS1 = (min(_bi) * G['paso_m'] + 160.0) if _bi else 3700.0
def _cinta_s(s0, s1, lat_fn, ancho, material, dz, nombre, paso_s=1.0):
    n_ = max(1, int(round((s1 - s0) / paso_s)))
    vs, fs = [], []
    for k in range(n_ + 1):
        s_k = s0 + (s1 - s0) * k / n_
        l_ = lat_fn(k, s_k)
        vs.append(punto_s(s_k, l_ + ancho / 2, dz))
        vs.append(punto_s(s_k, l_ - ancho / 2, dz))
    for k in range(n_):
        o = 2 * k
        fs.append((o, o + 1, o + 3, o + 2))
    new_mesh_obj(nombre, vs, fs, [material], [0] * len(fs))

i = 25
while i < N - 25:
    s_i = i * G['paso_m']
    if S[i]['sec'] != 'dirt' and not (S_CAS0 - 12 < s_i < S_CAS1 + 12):
        ribbon(list(range(i, i + 3)), lambda k, i2: 0.0, 0.16, M_MB,
               name='MARCA_CENTRO_%d' % i)
    i += 6
if S_LOEWS:
    _cinta_s(S_CAS0, S_LOEWS - 40.0, lambda k, s_k: 0.0, 0.20, M_MB, 0.04, 'MARCA_CENTRO_continua_a')
    _cinta_s(S_LOEWS + 40.0, S_CAS1, lambda k, s_k: 0.0, 0.20, M_MB, 0.04, 'MARCA_CENTRO_continua_b')
    s_t = S_LOEWS - 40.0
    k_t = 0
    while s_t < S_LOEWS + 40.0 - 0.8:
        _cinta_s(s_t, s_t + 0.8, lambda k, s_k: 0.0, 0.20, M_MB, 0.04,
                 'MARCA_CENTRO_horquilla_%d' % k_t, paso_s=0.4)
        s_t += 1.6
        k_t += 1

# ZIGZAG amarillo limon: una linea pegada a CADA borde, onda triangular simetrica,
# solo en la frenada previa a las curvas cerradas; termina donde empieza el piano
M_MA_Z = mat('MAT_marca_zigzag', (0.89, 0.74, 0.05, 1), 0.6)
ZZ_IN, ZZ_OUT, ZZ_PER, ZZ_W = 0.30, 1.45, 2.6, 0.14   # mas pequeno (el usuario: 'no son tan grandes')
def _zigzag(s_fin, largo, nombre):
    """Dos zigzags (izq y der) en los 'largo' m anteriores a s_fin."""
    n_per = max(3, int(largo / ZZ_PER))
    s_ini = s_fin - n_per * ZZ_PER
    for sgn in (1, -1):
        vs, fs = [], []
        for k in range(2 * n_per + 1):            # un vertice cada medio periodo
            s_k = s_ini + k * ZZ_PER / 2
            half = muestra_s(s_k)['w'] / 2.0
            d_b = ZZ_IN if k % 2 == 0 else ZZ_OUT   # empieza y acaba pegado al borde
            c = sgn * (half - d_b)
            # trazo de grosor constante: desplazamos el vertice a lo largo de la bisectriz
            vs.append(punto_s(s_k - ZZ_W * 0.72, c, 0.05))
            vs.append(punto_s(s_k + ZZ_W * 0.72, c, 0.05))
        for k in range(2 * n_per):
            o = 2 * k
            fs.append((o, o + 1, o + 3, o + 2))
        new_mesh_obj('MARCA_ZIGZAG_%s_%s' % (nombre, 'IZQ' if sgn > 0 else 'DER'), vs, fs,
                     [M_MA_Z], [0] * len(fs))

n_zz = 0
for (s_fin_, largo_, nombre_) in ZONAS_ZZ:
    _zigzag(s_fin_, largo_, nombre_)
    n_zz += 1
print('zigzags pintados:', n_zz, '| zonas de piano:', len(ZONAS_PIANO))

# --- v3 pista (B4): bocas de los enlaces del plan urbano (urbanismo.json) ---
# (s, lado, semiancho del corte, u de la boca, z de la boca). pts[3] es la boca (u ~0.4 del borde, z_borde + 0.03) y
# pts[2] el final del tramo perpendicular (u 1.5, cota de la calle). La acera (alta o baja) pasaba ENTERA por delante:
# en las 22 bocas quedaba ACERA_ 0.3-1.2 m por encima de CAMINO_enlace (sectores que suben: enlace a +0.1..+0.4 bajo la
# acera a +0.5; que bajan: a -0.04..-0.9 bajo ella), donde no hay acera el ARCEN llano (1.8 m) tapaba el enlace que
# baja y en el casino el guardarrail cerraba las 7 bocas. Ahora en el ancho de cada boca no hay acera, bordillo ni
# rail (la valla CERRADO de urbanismo_escena, a 3.5 m, cierra el enlace) y el arcen se mete bajo el enlace.
_BOCAS = []
MARGEN_BOCA = 0.35        # mas alla del ancho del enlace (sus bordes caen a +-ancho/2: medido en la escena)
RAMPA_BOCA = 1.0          # la acera alta baja de +0.5 a +0.06 en >= 1 m hasta el canto de la boca (vado)
def _s_lat(x, y):
    ib = min(range(N), key=lambda i: (S[i]['x'] - x) ** 2 + (S[i]['y'] - y) ** 2)
    p = S[ib]
    t = (x - p['x']) * p['ny'] - (y - p['y']) * p['nx']
    l_ = (x - p['x']) * p['nx'] + (y - p['y']) * p['ny']
    return ib * G['paso_m'] + max(-G['paso_m'], min(G['paso_m'], t)), l_, p['w'] / 2.0
try:
    for sec_ in json.load(open(os.environ.get('URBANISMO', BASE + r'\03_blender\urbanismo.json'),
                               encoding='utf-8')).get('sectores', []):
        for e_ in sec_.get('enlaces', []):
            pts_ = e_.get('pts') or []
            if len(pts_) < 4:
                continue
            sb_, lb_, hb_ = _s_lat(pts_[3][0], pts_[3][1])
            _BOCAS.append((sb_, 1 if lb_ > 0 else -1, float(e_.get('ancho', 4.5)) / 2.0 + MARGEN_BOCA,
                           max(0.0, abs(lb_) - hb_), float(pts_[3][2])))
except Exception as _e:
    print('sin urbanismo.json: sin bocas de enlaces (aceras y rails continuos):', _e)
print('bocas de enlaces (acera, bordillo y rail cortados; arcen bajo el enlace):',
      [(round(b_[0], 1), b_[1]) for b_ in _BOCAS])
def _boca_en(s_, sgn, extra=0.0):
    for b_ in _BOCAS:
        if b_[1] == sgn and abs(s_ - b_[0]) <= b_[2] + extra:
            return b_
    return None

def _tramos_sin_bocas(s0, s1, sgn, minimo=4.0):
    """[(a, b)] de [s0, s1] sin el ancho de las bocas del lado sgn; descarta los trozos < minimo."""
    out, lo = [], s0
    for (c0, c1) in sorted((b_[0] - b_[2], b_[0] + b_[2]) for b_ in _BOCAS if b_[1] == sgn):
        if c1 <= lo or c0 >= s1:
            continue
        if c0 - lo >= minimo:
            out.append((lo, c0))
        lo = max(lo, c1)
    if s1 - lo >= minimo:
        out.append((lo, s1))
    return out

# --- GUARDARRAIL de acero (Armco) a ambos lados en el sector del casino ---
M_GR = mat('MAT_guardarrail', (0.30, 0.26, 0.20, 1), 0.45, 0.7)
def _guardarrail(s0, s1, sgn, nombre, poste_fin=False, sin_postes_extremos=False):
    """poste_fin: poste tambien en s1 (si no cae en la serie de 4 m); sin_postes_extremos: sin los
    postes de s0 y s1 (tramo que empalma con otros dos que ya los ponen)."""
    vs, fs = [], []
    n_ = int((s1 - s0) / 2.0)
    for k in range(n_ + 1):
        s_k = s0 + (s1 - s0) * k / n_
        half = muestra_s(s_k)['w'] / 2.0
        l0, l1 = sgn * (half + 0.10), sgn * (half + 0.20)
        ze = -muestra_s(s_k)['lat'] * sgn * half      # cota del borde respecto al eje
        for (l_, dz_) in ((l0, 0.42), (l0, 0.62), (l0 + sgn * 0.05, 0.72), (l0, 0.82),
                          (l1, 0.82), (l1, 0.42)):
            q = muestra_s(s_k)
            vs.append((q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, q['z'] + ze + dz_))
    for k in range(n_):
        o = 6 * k
        for j in range(6):
            a0, a1 = o + j, o + (j + 1) % 6
            fs.append((a0, a1, a1 + 6, a0 + 6))
    # postes cada 4 m
    ks_p = list(range(0, n_ + 1, 2))
    if poste_fin and ks_p[-1] != n_:
        ks_p.append(n_)
    if sin_postes_extremos:
        ks_p = [k for k in ks_p if 0 < k < n_]
    for k in ks_p:
        s_k = s0 + (s1 - s0) * k / n_
        q = muestra_s(s_k)
        half = q['w'] / 2.0
        ze = -q['lat'] * sgn * half
        cx_ = q['x'] + q['nx'] * sgn * (half + 0.27)
        cy_ = q['y'] + q['ny'] * sgn * (half + 0.27)
        b0 = len(vs)
        for (dx, dy) in ((-0.06, -0.06), (0.06, -0.06), (0.06, 0.06), (-0.06, 0.06)):
            vs.append((cx_ + dx, cy_ + dy, q['z'] + ze - 0.4))
            vs.append((cx_ + dx, cy_ + dy, q['z'] + ze + 0.78))
        for j in range(4):
            a0, a1 = b0 + 2 * j, b0 + 2 * ((j + 1) % 4)
            fs.append((a0, a0 + 1, a1 + 1, a1))
    new_mesh_obj(nombre, vs, fs, [M_GR], [0] * len(fs))
if S_LOEWS and _bi:
    _in_gr = 1 if _curv(int(S_LOEWS / G['paso_m']), 4) < 0 else -1
    for sgn in (1, -1):
        # v1 pista (H1): el rail entra 1 m en el primer tramo de balaustrada del viaducto (s 3632):
        # antes acababa 2 m antes y quedaba un hueco entre la barrera y el pretil
        _fin = min(_bi) * G['paso_m'] + 1.0
        # v3 pista (B4): el rail del casino se abre en las 7 bocas de los enlaces de casino_ladera / casino_mar
        # (_tramos_sin_bocas): el primer trozo conserva el nombre y los siguientes llevan _2, _3...
        if sgn == _in_gr:
            # por el interior de la horquilla el rail se amontonaba en el apice: alli
            # ya esta el murete de la isleta
            _tr_gr = [(a_, b_, '_a', S_LOEWS - 30.0) for (a_, b_) in _tramos_sin_bocas(S_CAS0 + 20.0, S_LOEWS - 30.0, sgn)]
            if _fin - (S_LOEWS + 30.0) > 8.0:
                _tr_gr += [(a_, b_, '_b', _fin) for (a_, b_) in _tramos_sin_bocas(S_LOEWS + 30.0, _fin, sgn)]
        else:
            _tr_gr = [(a_, b_, '', _fin) for (a_, b_) in _tramos_sin_bocas(S_CAS0 + 20.0, _fin, sgn)]
        _n_gr = {}
        for (a_, b_, suf_, fin_) in _tr_gr:
            _n_gr[suf_] = _n_gr.get(suf_, 0) + 1
            _guardarrail(a_, b_, sgn, 'GUARDARRAIL_%s%s%s' % ('IZQ' if sgn > 0 else 'DER', suf_,
                                                             '' if _n_gr[suf_] == 1 else '_%d' % _n_gr[suf_]),
                         poste_fin=(b_ < fin_ - 1e-6))       # poste en el canto de cada boca
# v1 pista (B6, F-03): barrera tambien donde la calzada va en alto sobre el mar sin acera ni muro
# (lado +1 = mar): la subida al tunel (tras el muro+valla de meta, que acaba en s 174) y la
# salida del tunel hasta la acera del pueblo (s 620, alli sigue el pretil de piedra de abajo);
# y en el lado -1 delante del paseo-mirador (antes solo un bordillo de 0.16 m y coches a 5 m).
# v3 pista (B6): sin hueco antes y despues del tunel: la subida llega hasta el portal de entrada (s 402, cara del
# arco en 402.2-405.7) por la explanada de B8 (s 335-402, cornisa al mar a 35 m) y la horquilla arranca en el portal
# de salida (arco en 538.4-541.6) en vez de en s 560. Ninguno entra en el arco ni en la galeria.
for (_s0g, _s1g, _sgg, _nomg) in ((170.0, 402.0, 1, 'GUARDARRAIL_IZQ_subida'),
                                   (542.0, 620.0, 1, 'GUARDARRAIL_IZQ_horquilla')):
    _guardarrail(_s0g, _s1g, _sgg, _nomg)
# v2 pista (F2-05): el rail del mirador cerraba TODO el frente del paseo (sin entrada desde fuera,
# con 21 coches dentro). Se parte en tres piezas que empalman sin junta: _a (2984-2990, con poste en
# 2990), _boca (2990-2998, solo el poste central) y el resto (2998-3156). Mientras el integrador no
# ponga la boca del paseo, la barrera sigue continua (sin regresion); al ponerla (valla CERRADO a 2 m
# del borde en s 2990-2998, como las bocas de las calles) BORRA 'GUARDARRAIL_DER_mirador_boca'.
# v3 pista (F-03): el integrador no lo hizo nunca (el paseo y sus 20 coches seguian sin entrada). La boca la pone
# ahora construir_pista: hueco de 8 m entre los postes de s 2990 y 2998 (sin pieza _boca), VALLA CERRADO de
# caminos_kit a 2 m del borde sobre el pavimento del paseo (cota del borde + 0.10 = la de integrar.zona_paseo_mirador,
# que arranca a ras del borde en s0 = 2990 con un bordillo de 0.16 m: sin rampa; asentar la deja sobre MIRADOR_paseo)
# y cartel BELVEDERE / PARCHEGGIO en la berma antes de la boca. Si el kit falla o no hay mirador en s0 = 2990, el
# rail sigue continuo como en la v2 (sin regresion). N1: el rail _a arranca en s 2970 delante del final del pretil
# de la recta (MUROC_pretil_recta_mar, hasta s 2976): barrera continua desde la curva 30.
def _boca_mirador(s_b, side):
    """Valla de cierre + cartel en la boca del paseo-mirador. True si los ha puesto."""
    try:
        import sys as _sys
        _ad = BASE + r'\03_blender\assets'
        if _ad not in _sys.path:
            _sys.path.insert(0, _ad)
        import caminos_kit as _ck
        q = muestra_s(s_b)
        half = q['w'] / 2.0
        ze = q['z'] - q['lat'] * side * half
        l_ = side * (half + 2.0)
        v = _ck.build_valla_cierre(col, ancho=6.0, seed=29)
        v.location = (q['x'] + q['nx'] * l_, q['y'] + q['ny'] * l_, ze + 0.10)
        v.rotation_euler = (0.0, 0.0, math.atan2(side * q['ny'], side * q['nx']) - math.pi / 2)   # +Y = hacia el paseo
        v.name = 'CAMINO_valla_mirador'
        try:
            qc = muestra_s(s_b - 7.0)
            hc = qc['w'] / 2.0
            lc = side * (hc + 1.6)
            c = _ck.build_cartel(col, texto=['BELVEDERE', 'PARCHEGGIO'], seed=31, flecha=side)   # flecha hacia la boca
            c.location = (qc['x'] + qc['nx'] * lc, qc['y'] + qc['ny'] * lc, qc['z'] - qc['lat'] * side * hc - 0.05)
            c.rotation_euler = (0.0, 0.0, math.atan2(-side * qc['ny'], -side * qc['nx']) - math.pi / 2)  # se lee desde la pista
            c.name = 'CAMINO_cartel_mirador'
        except Exception as e_:
            print('boca del mirador: cartel fallo (%s)' % e_)
        return True
    except Exception as e_:
        print('boca del mirador: valla fallo (%s): el rail sigue continuo' % e_)
        return False

_MIR_F03 = next((m_ for m_ in (G.get('miradores') or [])
                 if int(m_['side']) == -1 and abs(float(m_['s0']) - 2990.0) < 1.0), None)
_guardarrail(2970.0, 2990.0, -1, 'GUARDARRAIL_DER_mirador_a', poste_fin=True)
if _MIR_F03 is None or not _boca_mirador(2994.0, -1):
    _guardarrail(2990.0, 2998.0, -1, 'GUARDARRAIL_DER_mirador_boca', sin_postes_extremos=True)
else:
    print('boca del paseo-mirador abierta en s 2990-2998 (valla CERRADO a 2 m y cartel)')
_guardarrail(2998.0, 3156.0, -1, 'GUARDARRAIL_DER_mirador')

# --- aceras con bordillo en los tramos urbanos ---
M_ACERA = mat('MAT_acera_piedra', paleta.rgba('caliza_gris_calido'), 0.95)   # fase visual: paleta (antes gris piedra literal)
M_BORDILLO = mat('MAT_bordillo_piedra', paleta.variante('caliza_gris_calido', 1.15) + (1.0,), 0.9)
# v1 pista (D11): el tramo alto empieza en el primer enlace/casa (s 1284), no en el prado de 1260
TRAMOS_URBANOS = [(620, 1100), (1284, 1560), (2480, 2760), (4560, 4930)]
# RONDA 15: en los sectores de terrazas del plan urbano (urbanismo_spec.json) junto a la
# pista va un BORDILLO ALTO (+0.5 m, franja 0.06..1.5) y encima arranca la calle de
# servicio del plan; fuera de ellos sigue la acera baja de siempre
_SPEC_U = {}
try:
    _SPEC_U = json.load(open(BASE + r'\03_blender\urbanismo_spec.json', encoding='utf-8'))
except Exception as _e:
    print('sin urbanismo_spec.json:', _e)
_SECT_U = [(float(s_['s0']), float(s_['s1']), int(s_['lado'])) for s_ in _SPEC_U.get('sectores', [])]
_BORD_U = float(_SPEC_U.get('bordillo_hasta', 1.5))
def _en_terraza(i, sgn):
    s_ = i * G['paso_m']
    return any(a_ <= s_ <= b_ and sgn == l_ for (a_, b_, l_) in _SECT_U)
for (a_, b_, l_) in _SECT_U:
    if not any(a0 <= a_ and b_ <= b0 for (a0, b0) in TRAMOS_URBANOS):
        # v1 pista (F-13): sin el margen de +-10 m, que dejaba retales de acera baja de 10 m
        # (s 3185-3195 y 3445-3455) con un escalon de 0.44 m contra la acera alta
        TRAMOS_URBANOS.append((int(a_), int(b_)))

# v2 pista (D2-10): por la TIERRA la acera alta solo sigue en los sectores que SUBEN (calle de servicio a
# +0.5, la misma regla que urbanismo.sentido_terrazas) y solo entre las bocas de sus enlaces (urbanismo.json):
# en los que bajan la calle va a Z-0.5 (la acera quedaria 1 m por encima) y mas alla del ultimo enlace
# acabaria en el prado (en pueblo_alto_ladera la calle acaba en s 1504 y el sector en 1525).
def _sube_u(sec_):
    sen_ = str(sec_.get('sentido', '')).strip().lower()
    if sen_ in ('sube', 'baja'):
        return sen_ == 'sube'
    if 'sube' in sec_:
        return bool(sec_['sube'])
    return not str(sec_['id']).endswith('_mar')

def _s_cerca(x, y):
    ib = min(range(N), key=lambda i: (S[i]['x'] - x) ** 2 + (S[i]['y'] - y) ** 2)
    p = S[ib]
    t = (x - p['x']) * p['ny'] - (y - p['y']) * p['nx']      # tangente de la marcha = (ny, -nx)
    return ib * G['paso_m'] + max(-G['paso_m'], min(G['paso_m'], t))

_URB_ENL = {}
try:
    for sec_ in json.load(open(os.environ.get('URBANISMO', BASE + r'\03_blender\urbanismo.json'),
                               encoding='utf-8')).get('sectores', []):
        ss_ = [(_s_cerca(q_[0], q_[1]), float(e_.get('ancho', 4.5)))
               for e_ in sec_.get('enlaces', []) for q_ in e_.get('pts', [])]
        if ss_:
            _URB_ENL[str(sec_['id'])] = (min(s_ - a_ / 2 - 1.0 for s_, a_ in ss_), max(s_ + a_ / 2 + 1.0 for s_, a_ in ss_))
except Exception as _e:
    print('sin urbanismo.json (la acera alta sigue por la tierra en todo el sector que sube):', _e)
_TIERRA_U = []
for s_ in _SPEC_U.get('sectores', []):
    if _sube_u(s_):
        a_, b_ = _URB_ENL.get(str(s_['id']), (float(s_['s0']), float(s_['s1'])))
        _TIERRA_U.append((max(a_, float(s_['s0'])), min(b_, float(s_['s1'])), int(s_['lado'])))
print('acera alta por la tierra en:', [(round(a_, 1), round(b_, 1), l_) for (a_, b_, l_) in _TIERRA_U])
def _acera_en_tierra(i, sgn):
    s_ = i * G['paso_m']
    return any(a_ <= s_ <= b_ and sgn == l_ for (a_, b_, l_) in _TIERRA_U)

def _faja_vertical(idxs, lateral, z0_rel, z1_rel, material, name):
    """Cara vertical (bordillo alto) a `lateral` del eje, entre z+z0_rel y z+z1_rel
    (z1_rel puede ser una funcion (k) -> cota relativa, para las rampas de los extremos)."""
    vs, fs = [], []
    for k, i2 in enumerate(idxs):
        p = _mp(i2)
        lat = lateral(k, i2)
        x_ = p['x'] + p['nx'] * lat
        y_ = p['y'] + p['ny'] * lat
        zb = p['z'] - p['lat'] * lat
        vs.append((x_, y_, zb + z0_rel))
        vs.append((x_, y_, zb + (z1_rel(k) if callable(z1_rel) else z1_rel)))
    for k in range(len(idxs) - 1):
        o = 2 * k
        fs.append((o, o + 2, o + 3, o + 1))
        fs.append((o + 1, o + 3, o + 2, o))   # doble cara: se ve desde la pista y desde la calle
    if fs:
        new_mesh_obj(name, vs, fs, [material], [0] * len(fs))

def _cinta_dz(indices, lateral_fn, width, dz_fn, material, name):
    """Como ribbon() pero con altura dz_fn(k) por muestra (rampas en los extremos)."""
    vs, fs = [], []
    for k, i2 in enumerate(indices):
        lat_c = lateral_fn(k, i2)
        vs.append(punto_lateral(i2, lat_c - width / 2, dz_fn(k)))
        vs.append(punto_lateral(i2, lat_c + width / 2, dz_fn(k)))
    for k in range(len(indices) - 1):
        o = 2 * k
        fs.append((o, o + 1, o + 3, o + 2))
    if fs:
        new_mesh_obj(name, vs, fs, [material], [0] * len(fs))

ACERA_ALTA_MIN = 8.0      # v3 (B4): un trozo de acera alta mas corto (entre una boca y el final) va entero a +0.06
ACERA_BAJA_MIN = 6.0      # y uno de acera baja mas corto no se pone (retal, como en F-13)
def _s_de(p):
    return p['s'] if isinstance(p, dict) else p * G['paso_m']

def _partir_bocas(idxs, sgn, alta):
    """v3 pista (B4): trozos de una acera sin las bocas de los enlaces (_BOCAS). Cada trozo es una lista de puntos:
    indices de muestra o muestras interpoladas (dict) justo en el canto de la boca. En la acera alta se quitan las
    muestras a < RAMPA_BOCA del canto (rampa de +0.5 a +0.06 de >= 1 m); en ninguna queda un tramo < 0.3 m."""
    paso = G['paso_m']
    s_a, s_b = idxs[0] * paso, idxs[-1] * paso
    cortes = sorted((b_[0] - b_[2], b_[0] + b_[2]) for b_ in _BOCAS
                    if b_[1] == sgn and b_[0] + b_[2] > s_a and b_[0] - b_[2] < s_b)
    if not cortes:
        return [list(idxs)]
    libres, lo, lo_c = [], s_a, False
    for (c0, c1) in cortes:
        if c0 > lo:
            libres.append((lo, lo_c, c0, True))
        if c1 > lo:
            lo, lo_c = c1, True
    if lo < s_b:
        libres.append((lo, lo_c, s_b, False))
    hueco = max(RAMPA_BOCA if alta else 0.0, 0.3)
    out = []
    for (a_, a_c, b_, b_c) in libres:
        pts = [i for i in idxs if a_ + (hueco if a_c else 0.0) <= i * paso <= b_ - (hueco if b_c else 0.0)]
        for (s_c, cortado, pos) in ((a_, a_c, 0), (b_, b_c, None)):
            if cortado:
                q_ = muestra_s(s_c)
                q_['s'] = s_c
                if pos == 0:
                    pts.insert(0, q_)
                else:
                    pts.append(q_)
        if len(pts) >= 2 and _s_de(pts[-1]) - _s_de(pts[0]) >= 0.5:
            out.append(pts)
    return out

N_BOCAS_CORTADAS = 0
for (s0u, s1u) in TRAMOS_URBANOS:
    i0u = int(s0u / G['paso_m'])
    i1u = int(s1u / G['paso_m'])
    for sgn in (1, -1):
        # v2 pista (D2-10): en los sectores de TERRAZA que suben la acera alta sigue tambien por la tierra
        # hasta la boca del ultimo enlace (_acera_en_tierra). pueblo_alto_ladera sigue hasta s 1525 pero la
        # acera acababa en s 1428 (donde empieza la tierra): la calle de servicio quedaba sobre la franja a
        # Z-0.4 con el faldon blanco del kit a la vista y rendijas bajo ella. Fuera de eso, sin acera en tierra.
        idxs_all = [i for i in range(i0u, i1u)
                    if S[i]['sec'] != 'bridge' and (S[i]['sec'] != 'dirt' or _acera_en_tierra(i, sgn))]
        trozos = []      # trozos consecutivos de un mismo tipo (terraza / urbano normal)
        for i in idxs_all:
            t_ = _en_terraza(i, sgn)
            if trozos and trozos[-1][0] == t_ and i == trozos[-1][1][-1] + 1:
                trozos[-1][1].append(i)
            else:
                trozos.append((t_, [i]))
        def _pegado_a_terraza(n_t):
            a_i, b_i = trozos[n_t][1][0], trozos[n_t][1][-1]
            return ((n_t > 0 and trozos[n_t - 1][0] and trozos[n_t - 1][1][-1] + 1 == a_i)
                    or (n_t + 1 < len(trozos) and trozos[n_t + 1][0] and trozos[n_t + 1][1][0] == b_i + 1))
        for n_t, (t_, idxs_u) in enumerate(trozos):
            # v1 pista (F-13/D11): nada de retales (< 12 m) ni de acera baja corta (<= 24 m)
            # pegada a una terraza: era acera en el prado, sin casas, acabando en la hierba
            if len(idxs_u) < 6 or (not t_ and len(idxs_u) < 13 and _pegado_a_terraza(n_t)):
                continue
            # v3 pista (B4): la acera se corta en el ancho de cada boca de enlace (+-ancho/2 + MARGEN_BOCA): el
            # primer trozo conserva el nombre de siempre y los siguientes llevan sufijo b, c...
            partes_u = _partir_bocas(idxs_u, sgn, t_)
            if len(partes_u) != 1 or len(partes_u[0]) != len(idxs_u):
                N_BOCAS_CORTADAS += 1
            for j_p, pts_u in enumerate(partes_u):
                suf = '' if j_p == 0 else chr(ord('a') + j_p)
                largo_p = _s_de(pts_u[-1]) - _s_de(pts_u[0])
                if t_:
                    # v1 pista (D11): los extremos de la acera alta bajan en rampa (2 m) a la cota de
                    # la acera baja en vez de acabar en un bloque cortado de 0.5 m (v3: tambien en el canto
                    # de cada boca, rampa >= 1 m = vado; un trozo < ACERA_ALTA_MIN va entero a +0.06)
                    _nk = len(pts_u)
                    _alto = 0.50 if largo_p >= ACERA_ALTA_MIN else 0.06
                    _dzf = lambda k, n_=_nk, a_=_alto: 0.06 if k in (0, n_ - 1) else a_
                    _cinta_dz(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 0.06 + _BORD_U / 2),
                              _BORD_U - 0.12, _dzf, M_ACERA, 'ACERA_%d_%d_%d%s' % (s0u, sgn, n_t, suf))
                    _faja_vertical(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 0.06), -0.05, _dzf, M_BORDILLO,
                                   'BORDILLO_%d_%d_%d%s' % (s0u, sgn, n_t, suf))
                else:
                    if j_p > 0 or len(partes_u) > 1:
                        if largo_p < ACERA_BAJA_MIN:
                            continue
                    ribbon(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 1.35),
                           2.3, M_ACERA, dz=0.055, name='ACERA_%d_%d_%d%s' % (s0u, sgn, n_t, suf))
                    ribbon(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 0.12),
                           0.24, M_BORDILLO, dz=0.07, name='BORDILLO_%d_%d_%d%s' % (s0u, sgn, n_t, suf))
                    # v1 pista (F-13): cantos de la acera baja: el exterior baja 0.35 m (no queda al
                    # aire sobre el talud del arcen) y el frente cierra la rendija bajo el bordillo
                    _faja_vertical(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 2.5), -0.30, 0.055, M_BORDILLO,
                                   'ACERA_%d_%d_%d%s_canto' % (s0u, sgn, n_t, suf))
                    _faja_vertical(pts_u, lambda k, i2, s=sgn: s * (_mp(i2)['w'] / 2 + 0.005), -0.03, 0.07, M_BORDILLO,
                                   'BORDILLO_%d_%d_%d%s_frente' % (s0u, sgn, n_t, suf))
print('aceras cortadas en las bocas de los enlaces (v3 B4): %d trozos' % N_BOCAS_CORTADAS)

# --- RONDA 15 (v1 pista, A-04/A-05/F-14): datos del PIT LANE por fila, ANTES de los arcenes.
# Antes la cinta del pit iba plana a la cota del EJE de la pista: en la entrada quedaba
# 0.06-0.24 m bajo el asfalto peraltado (y tapada por el ARCEN_DER, hierba con fisica en AC)
# y en la salida 0.3 m POR ENCIMA del asfalto (repisa). Ahora, en las bifurcaciones, la cinta
# sigue el plano de la calzada (prolongado llano fuera del borde) y funde a su cota propia en
# 30 m; dentro del asfalto va siempre 1.2 cm por debajo (la pista manda en render y fisica). ---
PIT = G.get('pit_lane') or []
L_PISTA = N * G['paso_m']
NL_PIT = 7            # vertices por fila: la seccion sigue el quiebro del borde del asfalto
PITD = []
_PIT_K0 = int(0.18 * (len(PIT) - 1)) if PIT else 0   # tramo a ancho completo = integrar.zona_pit
_PIT_K1 = int(0.82 * (len(PIT) - 1)) if PIT else 0

def _smooth01(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)

def _s_proy(x, y):
    """Abscisa s (m) de la proyeccion de (x, y) sobre el eje de la pista."""
    ib = min(range(N), key=lambda i: (S[i]['x'] - x) ** 2 + (S[i]['y'] - y) ** 2)
    p = S[ib]
    t = (x - p['x']) * p['ny'] - (y - p['y']) * p['nx']      # tangente de la marcha = (ny, -nx)
    return (ib * G['paso_m'] + max(-G['paso_m'], min(G['paso_m'], t))) % L_PISTA

def _z_pit(d, x, y):
    """Cota de la superficie del pit lane en (x, y) para la fila d."""
    m = d['m']
    l = (x - m['x']) * m['nx'] + (y - m['y']) * m['ny']
    half = d['half']
    z_t = m['z'] - m['lat'] * max(-half, min(half, l))      # plano de la calzada, llano fuera
    z = d['peso'] * z_t + (1.0 - d['peso']) * d['zp']
    if abs(l) < half - 0.01:
        z = min(z, m['z'] - m['lat'] * l - 0.012)           # bajo el asfalto, nunca encima
    return z

if PIT:
    _cum = 0.0
    for k, q in enumerate(PIT):
        if k:
            _cum += math.hypot(q['x'] - PIT[k - 1]['x'], q['y'] - PIT[k - 1]['y'])
        s_k = _s_proy(q['x'], q['y'])
        m = muestra_s(s_k)
        hw = q['w'] / 2.0
        ln = math.hypot(q['nx'], q['ny']) or 1.0
        A = (q['x'] + q['nx'] / ln * hw, q['y'] + q['ny'] / ln * hw)    # borde +n (orden de siempre)
        B = (q['x'] - q['nx'] / ln * hw, q['y'] - q['ny'] / ln * hw)
        lA = (A[0] - m['x']) * m['nx'] + (A[1] - m['y']) * m['ny']
        lB = (B[0] - m['x']) * m['nx'] + (B[1] - m['y']) * m['ny']
        lc = (q['x'] - m['x']) * m['nx'] + (q['y'] - m['y']) * m['ny']
        PITD.append(dict(k=k, s=s_k, m=m, half=m['w'] / 2.0, cum=_cum, A=A, B=B,
                         a_int=abs(lA) < abs(lB), sgn=(1 if lc > 0 else -1),
                         d_in=min(abs(lA), abs(lB)), d_out=max(abs(lA), abs(lB)),
                         hueco=min(abs(lA), abs(lB)) - m['w'] / 2.0, zp=q['z'] - 0.015, peso=0.0))
    # peso 1 = sigue la calzada (bifurcacion), 0 = cota propia; fundido de 30 m desde donde el
    # borde interior del pit sale del asfalto (entrada) o vuelve a entrar (salida)
    _ke = PITD[0]['cum']
    for k in range(1, max(2, _PIT_K0)):
        h0, h1 = PITD[k - 1]['hueco'], PITD[k]['hueco']
        if h0 <= 0.0 < h1:
            _ke = PITD[k - 1]['cum'] + (-h0 / (h1 - h0)) * (PITD[k]['cum'] - PITD[k - 1]['cum'])
            break
    _kx = PITD[-1]['cum']
    for k in range(len(PITD) - 1, _PIT_K1, -1):
        h0, h1 = PITD[k]['hueco'], PITD[k - 1]['hueco']
        if h0 <= 0.0 < h1:
            _kx = PITD[k]['cum'] - (-h0 / (h1 - h0)) * (PITD[k]['cum'] - PITD[k - 1]['cum'])
            break
    _de = max(6.0, min(30.0, PITD[_PIT_K0]['cum'] - _ke - 3.0))
    _dx = max(6.0, min(30.0, _kx - PITD[_PIT_K1]['cum'] - 3.0))
    for d in PITD:
        if d['k'] <= _PIT_K0:
            d['peso'] = 1.0 - _smooth01((d['cum'] - _ke) / _de)
        elif d['k'] >= _PIT_K1:
            d['peso'] = 1.0 - _smooth01((_kx - d['cum']) / _dx)
        # borde interior efectivo: donde se separa del asfalto la cinta arranca pegada al borde
        # y abre una cuna en punta (sin rendijas de 0.1-0.5 m entre pista y pit lane)
        h = d['hueco']
        en_bif = d['k'] <= _PIT_K0 or d['k'] >= _PIT_K1
        d_eff = d['half'] - 0.05 + (h + 0.05) * _smooth01(h / 1.5) if (en_bif and 0.0 < h < 1.5) else d['d_in']
        d['gore'] = d_eff - d['half']
        P_in, P_out = (d['A'], d['B']) if d['a_int'] else (d['B'], d['A'])
        ux, uy = P_in[0] - P_out[0], P_in[1] - P_out[1]
        lu = math.hypot(ux, uy) or 1.0
        ux, uy = ux / lu, uy / lu
        mv = d['d_in'] - d_eff
        d['P_in'] = (P_in[0] + ux * mv, P_in[1] + uy * mv)
        d['P_out'] = P_out
        d['u_out'] = (-ux, -uy)
        d['zin'] = _z_pit(d, *d['P_in'])
        d['zout'] = _z_pit(d, *d['P_out'])
    print('pit lane: bifurcaciones en cum %.1f / %.1f m, fundido %.0f / %.0f m, peso fila 0 %.2f, ultima %.2f'
          % (_ke, _kx, _de, _dx, PITD[0]['peso'], PITD[-1]['peso']))

_PIT_S0 = PITD[0]['s'] if PITD else 0.0
def _s_unw(s_):
    return s_ if s_ >= _PIT_S0 - 1.0 else s_ + L_PISTA
_PIT_SU = [_s_unw(d['s']) for d in PITD]

def _pit_en_s(s_):
    """(k, f) fila fraccional del pit lane a la altura de la abscisa s de la pista, o None."""
    if not PITD:
        return None
    su = _s_unw(s_)
    if su < _PIT_SU[0] or su > _PIT_SU[-1]:
        return None
    for k in range(len(PITD) - 1):
        if _PIT_SU[k] <= su <= _PIT_SU[k + 1]:
            ds = _PIT_SU[k + 1] - _PIT_SU[k]
            return k, ((su - _PIT_SU[k]) / ds if ds > 1e-6 else 0.0)
    return None

def _arcen_pit(idx, sgn, half, ez):
    """(e1, e2, z_e, z_m, z_o) del arcen de la pista en las bifurcaciones del pit, o None.
    Pit pegado al borde: arcen ESCONDIDO bajo la cinta (no tapa el carril). Cuna: hierba
    desde el borde del asfalto hasta justo bajo el bordillo interior del pit lane."""
    if not PITD or sgn != PITD[0]['sgn']:
        return None
    r = _pit_en_s(idx * G['paso_m'])
    if r is None:
        return None
    k, f = r
    if not (k + f <= _PIT_K0 - 3 or k + f >= _PIT_K1 + 2):
        return None                 # tramo del muro de boxes: arcen de siempre (el muro apoya en el)
    d0, d1 = PITD[k], PITD[min(k + 1, len(PITD) - 1)]
    g = d0['gore'] * (1 - f) + d1['gore'] * f
    d_out = d0['d_out'] * (1 - f) + d1['d_out'] * f
    zin = d0['zin'] * (1 - f) + d1['zin'] * f
    if g <= 0.04:
        if d_out - half < 0.3:
            return None
        return 0.05, max(0.12, min(6.5, d_out - half - 0.3)), ez - 0.07, ez - 0.30, ez - 0.80
    if g < 6.5:
        e2 = g + 0.02               # se mete 2 cm bajo el borde del pit (8 cm mas bajo): sin rendija
        z_o = zin - 0.08
        return e2 * 0.5, e2, ez - 0.01, 0.5 * (ez - 0.01) + 0.5 * z_o - 0.01, z_o
    return None

# v1 pista (C-13): pretil de piedra del lado del mar en la tecnica del pueblo bajo, detras de la
# acera (las macetas y postes de guirnalda llegan a 3.45 m del borde): (s0, s1, lado, cara a, nombre, pie)
# v2 pista (F2-02): y en el lado -1 de la bajada (s 2440-2618), que no tenia NINGUNA barrera: terraplen de
# 0.55 y debajo el desmonte de CARRERA_tribuna.004 (17-29 m de caida sobre su tejado o la recta de meta).
# Cara a 3.70 m, detras de farolas (hasta 1.56), macetas (hasta 3.41) y postes de guirnalda (su caja llega a
# 3.63 en s 2596): ninguno lo toca. Acaba en s 2618, antes de la boca de CAMINO_enlace.012 (desde s 2619.6;
# entre 2614 y 2618 el arcen quedaba 0.4-0.5 m al aire a 4 m del borde). pie = None: cara
# exterior hasta min(ze-0.6, zt-0.4) y arcen llano
# hasta 3.75 que baja hasta 7 m (C-13, sin cambios). pie = (dz_borde, dz_terreno): cara exterior hasta
# min(ze-dz_borde, zt-dz_terreno) (el integrador rebaja el terreno al pie con el desmonte de la tribuna) y
# el arcen acaba DENTRO del pretil: detras no asoma ninguna lamina de hierba al aire (s 2570-2610).
# v3 pista (F-08): el mismo pretil en el lado +1 de la frenada (s 2440-2636; talud del 40 %, hasta -6.9 m a 20 m),
# detras de la acera baja, farolas (1.3), macetas (2.8) y postes de guirnalda (3.5): en esa banda no hay ninguna boca
# ni ramal (CAMARA_tierra.001/.002 son gruas a 16-24 m, sin camino). N1: y en el lado -1 (mar) de la recta 30-31 que
# sube al casino (s 2770-2976, terraplen de -6.8 m a 20 m), detras de las vallas CARRERA_valla_pub (u 2.6-3.35); acaba
# 6 m despues de donde arranca GUARDARRAIL_DER_mirador_a (s 2970), que sigue hasta la boca del paseo.
PRETILES = [(616.0, 820.0, 1, 3.62, 'MUROC_pretil_mar_616', None),
            (2440.0, 2618.0, -1, 3.70, 'MUROC_pretil_bajada_2440', (2.5, 1.5)),
            (2440.0, 2636.0, 1, 3.70, 'MUROC_pretil_bajada_izq_2440', (2.5, 1.5)),
            (2770.0, 2976.0, -1, 3.70, 'MUROC_pretil_recta_mar', (2.5, 1.5))]
PRETIL_GRUESO, PRETIL_ALTO = 0.40, 0.90
def _pretil_de(idx, sgn):
    s_ = idx * G['paso_m']
    for pr_ in PRETILES:
        if pr_[0] <= s_ <= pr_[1] and sgn == pr_[2]:
            return pr_
    return None
def _en_pretil(idx, sgn):
    return _pretil_de(idx, sgn) is not None

# --- arcenes de hierba (tapan la union pista-terreno), salvo en puentes ---
M_ARCEN = mat('MAT_arcen', paleta.rgba('hierba_seca'), 1.0)     # fase visual: hierba seca (antes verde cesped); los arcenes van con M_TER
_TA = G['terreno']
def _zt_arcen(x, y):
    fx = (x - _TA['x0']) / _TA['cell']
    fy = (y - _TA['y0']) / _TA['cell']
    i0 = max(0, min(_TA['nx'] - 2, int(fx)))
    j0 = max(0, min(_TA['ny'] - 2, int(fy)))
    tx = min(max(fx - i0, 0), 1)
    ty = min(max(fy - j0, 0), 1)
    zz = lambda i, j: _TA['z'][j * _TA['nx'] + i]
    return ((zz(i0, j0) * (1 - tx) + zz(i0 + 1, j0) * tx) * (1 - ty)
            + (zz(i0, j0 + 1) * (1 - tx) + zz(i0 + 1, j0 + 1) * tx) * ty)
for sgn in (1, -1):
    av_, af_ = [], []
    run = []
    for i in range(N + 1):
        ok = S[i % N]['sec'] != 'bridge'
        if ok:
            run.append(i % N)
        if (not ok or i == N) and run:
            if len(run) > 2:
                base = len(av_)
                for idx in run:
                    p = S[idx]
                    half = p['w'] / 2.0
                    dz = -p['lat'] * half * sgn
                    ex = p['x'] + sgn * p['nx'] * half
                    ey = p['y'] + sgn * p['ny'] * half
                    ez = p['z'] + dz
                    # el arcen nunca cruza el centro de la horquilla ni pisa el otro
                    # ramal (era la 'cuna verde' que atravesaba el asfalto)
                    e1, e2 = 1.8, 6.5
                    if _en_terraza(idx, sgn):
                        e1, e2 = 0.3, 0.8      # ronda 15: bajo el bordillo alto de la calle de servicio
                    if S_LOEWS:
                        dc = math.hypot(ex - _lw['x'], ey - _lw['y'])
                        if dc < 30.0:
                            hacia_c = ((_lw['x'] - ex) * sgn * p['nx'] + (_lw['y'] - ey) * sgn * p['ny']) > 0
                            if hacia_c:
                                # RONDA 13: el arcen tampoco tapa la ISLETA (su rueda de flores
                                # quedaba bajo el cesped): se queda a 0.5 m de su radio
                                e2 = max(0.4, min(6.5, dc - (_R_ISLA + 0.5)))
                                e1 = min(1.8, e2 * 0.5)
                    pr_ = _pretil_de(idx, sgn)
                    if pr_ is not None:
                        e1, e2 = 3.75, 7.0     # v1 (C-13): llano bajo la acera hasta el pie del pretil
                        if pr_[5] is not None:
                            e2 = pr_[3] + PRETIL_GRUESO - 0.05   # v2 (F2-02): acaba dentro del pretil
                    z_e, z_m, zo = ez - 0.01, ez - 0.05, None
                    # v3 pista (B4): en la boca de un enlace el arcen va llano solo hasta la boca (u ~0.35) y no
                    # sube por encima de ella (la boca es horizontal y la pista tiene pendiente: en la mitad de
                    # arriba queda bajo el borde); despues se mete bajo el enlace (el llano de 1.8 m tapaba los
                    # que bajan, p. ej. casino_mar_enlace_fin y pueblo_subida_mar_enlace_fin). Una muestra mas a cada
                    # lado (paso_m) para que el cuadrilatero de transicion no deje una lengua de hierba sobre el canto.
                    bo_ = _boca_en(idx * G['paso_m'], sgn, G['paso_m']) if pr_ is None else None
                    if bo_ is not None:
                        e1 = min(e1, max(0.05, bo_[3] - 0.05))
                        e2 = min(e2, max(e1 + 0.3, 0.8))
                        if abs(idx * G['paso_m'] - bo_[0]) <= bo_[2]:
                            z_m = min(z_m, bo_[4] - 0.04)
                    ap = _arcen_pit(idx, sgn, half, ez)
                    if ap is not None:
                        e1, e2, z_e, z_m, zo = ap      # v1 (A-05/F-14): bifurcaciones del pit lane
                    mx_ = p['x'] + sgn * p['nx'] * (half + e1)
                    my_ = p['y'] + sgn * p['ny'] * (half + e1)
                    ox = p['x'] + sgn * p['nx'] * (half + e2)
                    oy = p['y'] + sgn * p['ny'] * (half + e2)
                    # plano 1.8 m y luego baja; el borde exterior SIEMPRE queda
                    # bajo el terreno (nada de repisas al aire)
                    if zo is None:
                        zo = min(ez - 1.6, _zt_arcen(ox, oy) - 0.35)
                    av_.append((ex, ey, z_e))
                    av_.append((mx_, my_, z_m))
                    av_.append((ox, oy, zo))
                for k in range(len(run) - 1):
                    o = base + 3 * k
                    af_.append((o, o + 1, o + 4, o + 3))
                    af_.append((o + 1, o + 2, o + 5, o + 4))
            run = []
    if av_:
        arc = new_mesh_obj('ARCEN_%s' % ('IZQ' if sgn > 0 else 'DER'),
                           av_, af_, [M_TER], [0] * len(af_))  # mismo material que el terreno: union invisible
        arc.data.shade_smooth()
        _uv_planar(arc)      # fase visual: misma UV planar que el TERRENO (mascara por texel continua en el arcen)

def _orientar_arriba(vs, fs):
    """Da la vuelta a todas las caras si la normal media apunta hacia abajo."""
    nz = 0.0
    for f_ in fs:
        a, b, c = vs[f_[0]], vs[f_[1]], vs[f_[2]]
        nz += (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return fs if nz >= 0 else [tuple(reversed(f_)) for f_ in fs]

def _pretil(s0, s1, sgn, off0, grueso, alto, nombre, pie=None):
    """Pretil de piedra macizo: cara a la pista a off0 m del borde del asfalto, 'grueso' de
    ancho, coronacion a 'alto' sobre la acera; el pie siempre bajo el arcen y el terreno
    (pie = (dz_borde, dz_terreno): hasta min(ze - dz_borde, zt - dz_terreno))."""
    dzb, dzt = pie if pie is not None else (0.6, 0.4)
    vs, fs = [], []
    n_ = max(1, int((s1 - s0) / 2.0))
    for k in range(n_ + 1):
        q = muestra_s(s0 + (s1 - s0) * k / n_)
        half = q['w'] / 2.0
        ze = q['z'] - q['lat'] * sgn * half
        for off in (off0, off0 + grueso):
            x_ = q['x'] + q['nx'] * sgn * (half + off)
            y_ = q['y'] + q['ny'] * sgn * (half + off)
            vs.append((x_, y_, min(ze - dzb, _zt_arcen(x_, y_) - dzt)))
            vs.append((x_, y_, ze + 0.055 + alto))
    for k in range(n_):          # por fila: 0 pie int, 1 cima int, 2 pie ext, 3 cima ext
        o = 4 * k
        fs += [(o, o + 4, o + 5, o + 1), (o + 1, o + 5, o + 7, o + 3), (o + 3, o + 7, o + 6, o + 2)]
    fs += [(0, 1, 3, 2), (4 * n_, 4 * n_ + 2, 4 * n_ + 3, 4 * n_ + 1)]
    if sgn < 0:                  # normales hacia fuera (AC descarta las caras de espaldas)
        fs = [tuple(reversed(f_)) for f_ in fs]
    new_mesh_obj(nombre, vs, fs, [M_MUROC], [0] * len(fs))

M_MUROC = mat('MAT_muro_contencion_piedra', paleta.rgba('caliza_ocre'), 0.95)   # fase visual: paleta (antes literal)
for (_a, _b, _l, _o, _nom, _pie) in PRETILES:
    _pretil(_a, _b, _l, _o, PRETIL_GRUESO, PRETIL_ALTO, _nom, pie=_pie)   # MUROC -> 1WALL en el kn5

# --- linea de salida ---
p0 = S[0]
h0 = p0['w'] / 2 - 0.3
lv = []
for t in (0, 1):
    q = S[t * 2]
    lv.append((q['x'] + q['nx'] * h0, q['y'] + q['ny'] * h0, q['z'] - q['lat'] * h0 + 0.04))
    lv.append((q['x'] - q['nx'] * h0, q['y'] - q['ny'] * h0, q['z'] + q['lat'] * h0 + 0.04))
new_mesh_obj('LINEA_SALIDA', lv, [(0, 1, 3, 2)], [M_LINEA], [0])

# --- pit lane (v1 pista: cota de _z_pit, seccion de NL_PIT vertices, borde interior efectivo) ---
if PITD:
    pvts, pfcs = [], []
    def _fila_pit_virtual(idx, d_ref):
        """Fila extra 2 m antes/despues del pit: la cinta se cierra en punta contra el BORDE del
        asfalto (tapa el triangulo que quedaba entre la pista, el pit y su hombro)."""
        p = S[idx % N]
        half = p['w'] / 2.0
        sg = d_ref['sgn']
        dv = dict(m=p, half=half, peso=1.0, zp=p['z'])
        ancho = d_ref['d_out'] - min(d_ref['d_in'], d_ref['half'] + d_ref['gore'])
        ls = [sg * (half - ancho), sg * half]
        if not d_ref['a_int']:
            ls.reverse()
        fila = []
        for j in range(NL_PIT):
            t = j / (NL_PIT - 1)
            l_ = ls[0] * (1 - t) + ls[1] * t
            x_, y_ = p['x'] + p['nx'] * l_, p['y'] + p['ny'] * l_
            fila.append((x_, y_, _z_pit(dv, x_, y_)))
        return fila
    filas_pit = []
    for d in PITD:
        A_ = d['P_in'] if d['a_int'] else d['A']
        B_ = d['B'] if d['a_int'] else d['P_in']
        fila = []
        for j in range(NL_PIT):
            t = j / (NL_PIT - 1)
            x_, y_ = A_[0] * (1 - t) + B_[0] * t, A_[1] * (1 - t) + B_[1] * t
            fila.append((x_, y_, _z_pit(d, x_, y_)))
        filas_pit.append(fila)
    if PITD[0]['hueco'] < 0.0:
        filas_pit.insert(0, _fila_pit_virtual(int((PITD[0]['s'] - 0.01) / G['paso_m']), PITD[0]))
    if PITD[-1]['hueco'] < 0.0:
        filas_pit.append(_fila_pit_virtual(int(math.ceil((PITD[-1]['s'] + 0.01) / G['paso_m'])), PITD[-1]))
    for fila in filas_pit:
        pvts.extend(fila)
    for k in range(len(filas_pit) - 1):
        o = NL_PIT * k
        for j in range(NL_PIT - 1):
            pfcs.append((o + j, o + j + 1, o + NL_PIT + j + 1, o + NL_PIT + j))
    new_mesh_obj('PIT_LANE', pvts, pfcs, [M_ASF], [0] * len(pfcs))
    _bif = [d for d in PITD if d['k'] <= _PIT_K0 - 2 or d['k'] >= _PIT_K1 + 2]
    _gore = [d for d in _bif if d['gore'] > 0.04]

    def _mayor_tramo(sel):
        """Filas consecutivas (k seguidos) mas largas de la seleccion."""
        tramos = []
        for d in sel:
            if tramos and d['k'] == tramos[-1][-1]['k'] + 1:
                tramos[-1].append(d)
            else:
                tramos.append([d])
        return max(tramos, key=len) if tramos else []
    # bordillo interior en la cuna (tapa la rendija entre la hierba y el borde de la cinta)
    for nombre_, sel in (('entrada', _mayor_tramo([d for d in _gore if d['k'] < _PIT_K0])),
                         ('salida', _mayor_tramo([d for d in _gore if d['k'] > _PIT_K1]))):
        if len(sel) < 2:
            continue
        bv, bf = [], []
        for d in sel:
            bv.append((d['P_in'][0], d['P_in'][1], d['zin'] + 0.005))
            bv.append((d['P_in'][0], d['P_in'][1], d['zin'] - 0.30))
        for m_ in range(len(sel) - 1):
            o = 2 * m_
            bf += [(o, o + 2, o + 3, o + 1), (o + 1, o + 3, o + 2, o)]
        new_mesh_obj('BORDILLO_pit_%s' % nombre_, bv, bf, [M_BORDILLO], [0] * len(bf))
    # linea blanca (MARCA_PIT) en el borde interior desde que los carriles se separan 0.3 m
    # hasta las marcas del pit_kit (filas K0+1 / K1-1)
    for nombre_, sel in (('entrada', _mayor_tramo([d for d in PITD if d['k'] <= _PIT_K0 + 1 and d['gore'] >= 0.3])),
                         ('salida', _mayor_tramo([d for d in PITD if d['k'] >= _PIT_K1 - 1 and d['gore'] >= 0.3]))):
        if len(sel) < 2:
            continue
        mv_, mf_ = [], []
        for d in sel:
            for off in (0.10, 0.25):
                x_ = d['P_in'][0] + d['u_out'][0] * off
                y_ = d['P_in'][1] + d['u_out'][1] * off
                mv_.append((x_, y_, _z_pit(d, x_, y_) + 0.02))
        for m_ in range(len(sel) - 1):
            o = 2 * m_
            mf_.append((o, o + 1, o + 3, o + 2))
        new_mesh_obj('MARCA_PIT_%s' % nombre_, mv_, _orientar_arriba(mv_, mf_), [M_MB], [0] * len(mf_))
    # ARCEN_PIT: hombro de hierba en el borde exterior (la cinta quedaba 0.6 m al aire sobre la
    # caja del terreno y su sombra hacia 'dientes'); no bajo el edificio de boxes (alli va su acera)
    _kc = 0.5 * (_PIT_K0 + _PIT_K1)
    for nombre_, sel in (('entrada', [d for d in PITD if d['k'] < _kc - 22]),
                         ('salida', [d for d in PITD if d['k'] > _kc + 22])):
        if len(sel) < 2:
            continue
        hv, hf = [], []
        filas = []
        for d in sel:
            (px, py), (ux, uy), zo_ = d['P_out'], d['u_out'], d['zout']
            x2, y2 = px + ux * 4.0, py + uy * 4.0
            filas.append([(px, py, zo_ - 0.01), (px + ux * 1.2, py + uy * 1.2, zo_ - 0.06),
                          (x2, y2, min(zo_ - 1.2, _zt_arcen(x2, y2) - 0.35))])
        # donde nace / muere el pit lane el hombro arranca de la ULTIMA fila del arcen normal de la
        # pista (mismos vertices): sin escalon ni cuna entre los dos arcenes
        def _fila_arcen_def(idx, sg):
            p = S[idx % N]
            half = p['w'] / 2.0
            ez = p['z'] - p['lat'] * half * sg
            pt = lambda e: (p['x'] + sg * p['nx'] * (half + e), p['y'] + sg * p['ny'] * (half + e))
            (ex, ey), (mx, my), (ox, oy) = pt(0.0), pt(1.8), pt(6.5)
            return [(ex, ey, ez - 0.01), (mx, my, ez - 0.05), (ox, oy, min(ez - 1.6, _zt_arcen(ox, oy) - 0.35))]
        if sel[0]['k'] == 0:
            filas.insert(0, _fila_arcen_def(int((PITD[0]['s'] - 0.01) / G['paso_m']), PITD[0]['sgn']))
        if sel[-1]['k'] == len(PITD) - 1:
            filas.append(_fila_arcen_def(int(math.ceil((PITD[-1]['s'] + 0.01) / G['paso_m'])), PITD[0]['sgn']))
        for f_ in filas:
            hv.extend(f_)
        for m_ in range(len(filas) - 1):
            o = 3 * m_
            hf += [(o, o + 1, o + 4, o + 3), (o + 1, o + 2, o + 5, o + 4)]
        hp = new_mesh_obj('ARCEN_PIT_%s' % nombre_, hv, _orientar_arriba(hv, hf), [M_TER], [0] * len(hf))
        hp.data.shade_smooth()
        _uv_planar(hp)
    print('pit lane construido: %d filas x %d, cuna en %d filas, peso>0 en %d filas'
          % (len(PITD), NL_PIT, len(_gore), sum(1 for d in PITD if d['peso'] > 0.0)))

# --- terreno ---
T = G['terreno']
nx_, ny_ = T['nx'], T['ny']
tz = T['z']
tmar = T['mar']
# v1 pista (F-14): el terreno nunca asoma por encima de la cinta del pit lane (+0.6 m alrededor);
# solo BAJA vertices (los que quedaban a menos de 0.12 m bajo la cinta)
_n_baj = 0
for k in range(len(PITD) - 1):
    d0, d1 = PITD[k], PITD[k + 1]
    c0 = ((d0['P_in'][0] + d0['P_out'][0]) / 2, (d0['P_in'][1] + d0['P_out'][1]) / 2)
    c1 = ((d1['P_in'][0] + d1['P_out'][0]) / 2, (d1['P_in'][1] + d1['P_out'][1]) / 2)
    hw = max(math.hypot(d['P_in'][0] - d['P_out'][0], d['P_in'][1] - d['P_out'][1]) for d in (d0, d1)) / 2 + 0.6
    zs = min(d0['zin'], d0['zout'], d1['zin'], d1['zout']) - 0.12
    sx, sy = c1[0] - c0[0], c1[1] - c0[1]
    ls2 = sx * sx + sy * sy or 1e-9
    ii0 = max(0, int((min(c0[0], c1[0]) - hw - T['x0']) / T['cell']))
    ii1 = min(nx_ - 1, int((max(c0[0], c1[0]) + hw - T['x0']) / T['cell']) + 1)
    jj0 = max(0, int((min(c0[1], c1[1]) - hw - T['y0']) / T['cell']))
    jj1 = min(ny_ - 1, int((max(c0[1], c1[1]) + hw - T['y0']) / T['cell']) + 1)
    for jj in range(jj0, jj1 + 1):
        for ii in range(ii0, ii1 + 1):
            x_, y_ = T['x0'] + ii * T['cell'], T['y0'] + jj * T['cell']
            t_ = max(0.0, min(1.0, ((x_ - c0[0]) * sx + (y_ - c0[1]) * sy) / ls2))
            if math.hypot(x_ - c0[0] - sx * t_, y_ - c0[1] - sy * t_) <= hw and tz[jj * nx_ + ii] > zs:
                tz[jj * nx_ + ii] = zs
                _n_baj += 1
if PITD:
    print('terreno bajo el pit lane: %d vertices rebajados' % _n_baj)
tv = []
for j in range(ny_):
    for i in range(nx_):
        tv.append((T['x0'] + i * T['cell'], T['y0'] + j * T['cell'], tz[j * nx_ + i]))
tf, tfm = [], []
# RONDA 15 (v1 pista, N2): la malla va YA TRIANGULADA, dos triangulos por celda con diagonal
# FIJA (a-c, la que usaba Blender al triangular estos quads para el render y el kn5). Con quads,
# el BVH de asentar_objetos / inspectores (FromPolygons) cortaba por otra diagonal en el 18 % de
# las celdas (p99 7 m en laderas): arboles 'asentados' que flotaban. Ahora render, kn5, asentar e
# inspectores ven LA MISMA superficie. (La diagonal de envolvente inferior se probo: dientes de
# sierra en la costa y en las coronaciones convexas.) Los vertices no cambian (j*nx+i): las
# explanadas del integrador y la lectura de cota de los inspectores siguen funcionando.
for j in range(ny_ - 1):
    for i in range(nx_ - 1):
        a = j * nx_ + i
        b, c, d = a + 1, a + nx_ + 1, a + nx_
        tf.append((a, b, c))
        tf.append((a, c, d))
        tfm.extend((0, 0))
terreno = new_mesh_obj('TERRENO', tv, tf, [M_TER, M_FONDO], tfm)
terreno.data.shade_smooth()
# fase visual (plan 3.5): UV planar REAL en el TERRENO, u = (x - x0) / (nx cell), v = (y - y0) / (ny cell): es la UV de
# txMask / txDiffuse del multicapa y la que exporta el writer tal cual (uv_layers[0]). El material la recalcula por
# posicion de mundo (vale tambien para caras sin UV que lleven MAT_terreno, p. ej. la falda del McLaren en integrar).
_uv_planar(terreno)
print('terreno: UV planar %s (%d loops)' % (terreno.data.uv_layers[0].name if terreno.data.uv_layers else 'NO', len(terreno.data.loops)))
# RONDA 15: mascara de roca del macizo como atributo por vertice 'roca'; el material la mezcla con la pendiente real.
# Fase visual F1 r3 (director_f1_r2.md problema 8): el atributo es el canal A de texturas/terreno_mask.png en cada vertice
# (respaldo: G['mascara_roca']); es lo que lee color_ac.separar_roca_terreno (writer de hoy y --modo-ac), ver roca_atributo_terreno.
_orig_roca, _vals_roca = roca_atributo_terreno(terreno, G.get('mascara_roca'))
if _vals_roca is None:
    print('terreno: SIN atributo roca (ni mascara legible ni mascara_roca en el JSON)')
else:
    _tierra_v = np.asarray(T.get('mar') or [0] * len(tv), np.float32) < 0.5
    _msg = 'terreno: atributo roca = %s en %d vertices (media %.3f; > 0.49 en el %.1f %% de los vertices de tierra' % (
        _orig_roca, len(tv), float(_vals_roca.mean()), 100.0 * float((_vals_roca[_tierra_v] > 0.49).mean()))
    if G.get('mascara_roca') and len(G['mascara_roca']) == len(tv):
        _mr_v = np.asarray(G['mascara_roca'], np.float32)
        _msg += '; mascara_roca v1 > 0.49: %.1f %%, difieren en el %.2f %%' % (
            100.0 * float((_mr_v[_tierra_v] > 0.49).mean()),
            100.0 * float(((_mr_v[_tierra_v] > 0.49) != (_vals_roca[_tierra_v] > 0.49)).mean()))
    print(_msg + ')')
    # F1 r4 (acotacion 4): roca por cara del modo AC sin dientes en la cima de 56 y a < 150 m de 51/07 (ver roca_zonas_nz)
    _z4 = roca_zonas_nz(terreno)
    if _z4:
        _nz_terreno = ((G.get('extras') or {}).get('umbrales_roca') or {}).get('nz') if isinstance(G.get('extras'), dict) else None
        print('terreno: zonas nz < %.2f (fuera: nz < 0.82 de color_ac; umbral de terreno_montana nz %s) en %d vertices: caras de roca AC '
              '%d -> %d, dientes %d -> %d, huecos %d -> %d; vertices que cambian de clase (0.49): %d'
              % (_z4['nz_zona'], _nz_terreno, _z4['vertices_en_zona'], _z4['global']['roca_antes'], _z4['global']['roca_despues'],
                 _z4['global']['dientes_antes'], _z4['global']['dientes_despues'], _z4['global']['huecos_antes'],
                 _z4['global']['huecos_despues'], _z4['vertices_cambiados_0_49']))
        for _nm, _zz in _z4['zonas'].items():
            print('   zona %-22s caras tierra %5d | roca %4d -> %4d | dientes %3d -> %3d | huecos %2d -> %2d | desacuerdo con el objetivo %d'
                  % (_nm, _zz['caras_tierra'], _zz['roca_antes'], _zz['roca_despues'], _zz['dientes_antes'], _zz['dientes_despues'],
                     _zz['huecos_antes'], _zz['huecos_despues'], _zz['desacuerdo_objetivo']))
        _vr = np.empty(len(terreno.data.vertices), np.float32)
        terreno.data.attributes['roca'].data.foreach_get('value', _vr)
        print('terreno: atributo roca tras las zonas: %d vertices, media %.3f, > 0.49 en el %.1f %% de los vertices de tierra'
              % (len(_vr), float(_vr.mean()), 100.0 * float((_vr[_tierra_v] > 0.49).mean())))
    # F1 r4 (acotacion 4): la banda de 2 m se hace al FINAL del pipeline (_rev/banda_terreno_2m.py); aqui solo el recuento previo
    _b4 = estimar_banda_terreno()
    print('terreno: banda de %.0f m junto al asfalto: %d celdas -> +%d vertices (%d -> %d) y +%d tris al final del pipeline '
          '(subdividir_banda_terreno; TERRENO_BANDA_2M=1 la aplica ya aqui, solo pruebas)'
          % (_b4['banda_m'], _b4['celdas'], _b4['vertices_nuevos'], len(tv), len(tv) + _b4['vertices_nuevos'], _b4['tris_nuevos']))

# --- mar ---
ext = 9000.0  # el mar llega al horizonte tambien en las tomas aereas
av = [(T['x0'] - ext, T['y0'] - ext, 0.0),
      (T['x0'] + nx_ * T['cell'] + ext, T['y0'] - ext, 0.0),
      (T['x0'] + nx_ * T['cell'] + ext, T['y0'] + ny_ * T['cell'] + ext, 0.0),
      (T['x0'] - ext, T['y0'] + ny_ * T['cell'] + ext, 0.0)]
agua = new_mesh_obj('AGUA', av, [(0, 1, 2, 3)], [M_AGUA], [0])
# fondo marino bajo TODO el mar (el agua es translucida: sin fondo se veia el
# borde recto del terreno como un rectangulo claro en el agua)
# fase visual (plan 3.5): material PROPIO MAT_fondo_marino (paleta arena / mar_orilla); ya no comparte MAT_terreno.
# El degradado real de batimetria (turquesa -> azul profundo) es del bloque 6 (agua).
new_mesh_obj('AGUA_fondo', [(x_, y_, -4.05) for (x_, y_, z_) in av], [(0, 1, 2, 3)], [M_FONDO_MAR], [0])
M_AGUA.blend_method = 'BLEND'
bsdf = M_AGUA.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Alpha'].default_value = 0.84
bsdf.inputs['Roughness'].default_value = 0.04
# mar con profundidad: turquesa costero -> azul profundo por parches grandes
ntw0 = M_AGUA.node_tree
txw = ntw0.nodes.new('ShaderNodeTexCoord')
nzw = ntw0.nodes.new('ShaderNodeTexNoise')
nzw.inputs['Scale'].default_value = 0.004
nzw.inputs['Detail'].default_value = 4.0
mixw = ntw0.nodes.new('ShaderNodeMix')
mixw.data_type = 'RGBA'
mixw.inputs[6].default_value = (0.015, 0.28, 0.44, 1)   # profundo
mixw.inputs[7].default_value = (0.04, 0.44, 0.54, 1)    # turquesa
ntw0.links.new(txw.outputs['Object'], nzw.inputs['Vector'])
ntw0.links.new(nzw.outputs['Fac'], mixw.inputs['Factor'])
ntw0.links.new(mixw.outputs[2], bsdf.inputs['Base Color'])
# olas suaves por normal procedural
ntw = M_AGUA.node_tree
tco = ntw.nodes.new('ShaderNodeTexCoord')
nzo = ntw.nodes.new('ShaderNodeTexNoise')
nzo.inputs['Scale'].default_value = 0.02
nzo.inputs['Detail'].default_value = 5.0
bmpw = ntw.nodes.new('ShaderNodeBump')
bmpw.inputs['Strength'].default_value = 0.12
ntw.links.new(tco.outputs['Object'], nzo.inputs['Vector'])
ntw.links.new(nzo.outputs['Fac'], bmpw.inputs['Height'])
ntw.links.new(bmpw.outputs['Normal'], bsdf.inputs['Normal'])

# --- muros de contencion de piedra donde la pista queda en alto ---
M_MUROC = mat('MAT_muro_contencion_piedra', paleta.rgba('caliza_ocre'), 0.95)   # fase visual: paleta (antes literal)

def z_terreno_b(x, y):
    fx = (x - T['x0']) / T['cell']
    fy = (y - T['y0']) / T['cell']
    i0 = max(0, min(nx_ - 2, int(fx)))
    j0 = max(0, min(ny_ - 2, int(fy)))
    tx2 = min(max(fx - i0, 0), 1)
    ty2 = min(max(fy - j0, 0), 1)
    def zz(i, j):
        return tz[j * nx_ + i]
    return ((zz(i0, j0) * (1 - tx2) + zz(i0 + 1, j0) * tx2) * (1 - ty2)
            + (zz(i0, j0 + 1) * (1 - tx2) + zz(i0 + 1, j0 + 1) * tx2) * ty2)

tramo_m = 0
for sgn in (1, -1):
    run = []
    for i in range(N + 1):
        p = S[i % N]
        ok = p['sec'] not in ('dirt', 'bridge')
        if ok:
            half = p['w'] / 2
            tx3 = p['x'] + sgn * p['nx'] * (half + 3.5)
            ty3 = p['y'] + sgn * p['ny'] * (half + 3.5)
            ok = (p['z'] - z_terreno_b(tx3, ty3)) > 3.0
        if ok:
            run.append(i % N)
        if (not ok or i == N) and run:
            if len(run) > 6:
                mv, mf = [], []
                for idx in run:
                    q = S[idx]
                    h2 = q['w'] / 2
                    ax = q['x'] + sgn * q['nx'] * (h2 + 0.05)
                    ay = q['y'] + sgn * q['ny'] * (h2 + 0.05)
                    bx = q['x'] + sgn * q['nx'] * (h2 + 0.75)
                    by = q['y'] + sgn * q['ny'] * (h2 + 0.75)
                    zb = z_terreno_b(bx, by) - 1.5
                    mv.extend([(ax, ay, q['z'] + 0.85), (bx, by, q['z'] + 0.85),
                               (bx, by, zb)])
                for k in range(len(run) - 1):
                    o = 3 * k
                    mf.append((o, o + 1, o + 4, o + 3))       # remate
                    mf.append((o + 1, o + 2, o + 5, o + 4))   # cara exterior
                new_mesh_obj('MUROC_%d_%d' % (sgn, tramo_m), mv, mf,
                             [M_MUROC], [0] * len(mf))
                tramo_m += 1
            run = []
print('muros de contencion:', tramo_m)

# --- sol calido de tarde mediterranea ---
sun_data = bpy.data.lights.new('SOL', 'SUN')
sun_data.energy = 4.6
sun_data.color = (1.0, 0.96, 0.88)
sun_data.angle = math.radians(3.0)
sun = bpy.data.objects.new('SOL', sun_data)
# fase visual (plan 3.6): sol mas bajo (rotacion X 34 -> 42 grados = elevacion 56 -> 48) y azimut rasante a la ladera del
# tramo de tierra (rz -140 -> -119: sol desde 151 grados, la cuesta abajo media de la tierra mira a 241 grados). La misma
# direccion la usa el hillshade de terreno_ao.png: UNA constante, mascara_terreno.SOL.
_ROT_SOL = tuple(_mt.SOL['rot_blender_deg']) if _mt is not None else (42.0, 0.0, -119.0)
sun.rotation_euler = tuple(math.radians(v) for v in _ROT_SOL)
col.objects.link(sun)
print('sol: energia %.1f, rotacion (%.0f, %.0f, %.0f) grados' % (sun_data.energy, *_ROT_SOL))
# el mapa es enorme: sin esto EEVEE agota el buffer de sombras ('Shadow buffer full')
# y deja recuadros oscuros (teselas de sombra rotas) sobre el mar
for _attr, _val in (('shadow_maximum_resolution', 0.12), ('shadow_filter_radius', 1.5)):
    try:
        setattr(sun_data, _attr, _val)
    except Exception:
        pass
try:
    bpy.context.scene.eevee.shadow_pool_size = '1024'
except Exception:
    pass

# --- cielo azul saturado estilo Cars 2 (gradiente cenit -> horizonte) ---
world = bpy.data.worlds.new('CIELO')
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes.get('Background')
tco = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
mapr = nt.nodes.new('ShaderNodeMapRange')
mapr.inputs['From Min'].default_value = -0.05
mapr.inputs['From Max'].default_value = 0.9
rampc = nt.nodes.new('ShaderNodeValToRGB')
ec = rampc.color_ramp.elements
ec[0].position = 0.0; ec[0].color = (0.70, 0.84, 0.98, 1)   # horizonte claro
ec[1].position = 1.0; ec[1].color = (0.12, 0.34, 0.86, 1)   # cenit azul intenso
em = rampc.color_ramp.elements.new(0.3)
em.color = (0.36, 0.60, 0.95, 1)
nt.links.new(tco.outputs['Generated'], sep.inputs['Vector'])
nt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
nt.links.new(mapr.outputs['Result'], rampc.inputs['Fac'])
nt.links.new(rampc.outputs['Color'], bg.inputs['Color'])
bg.inputs[1].default_value = 1.0
bpy.context.scene.world = world

# --- calidad de render (AO y transformacion de vista saturada) ---
# view_transform Standard y exposicion 0.12 NO cambian (referencia de color_ac y de capturas_ab). NO hay niebla de mundo.
# AO: en Blender 5.1 no existe use_gtao/gtao_distance (nunca se aplicaron: setattr fallaba en silencio); el AO de EEVEE es
# use_fast_gi + fast_gi_distance, y fast_gi_distance = 0 significa SIN LIMITE (es lo que renderizaban la carta de color y
# el 'antes' congelado). Se deja explicito: poner 20 m RECORTARIA el AO respecto a hoy.
sc0 = bpy.context.scene
sc0.view_settings.view_transform = 'Standard'
sc0.view_settings.exposure = 0.12
for attr, val in [('use_fast_gi', True), ('fast_gi_distance', 0.0), ('use_shadows', True),
                  ('use_gtao', True), ('gtao_distance', 20.0)]:
    try:
        setattr(sc0.eevee, attr, val)
    except Exception:
        pass
print('eevee: use_fast_gi %s, fast_gi_distance %s (0 = sin limite), use_shadows %s' % (
    getattr(sc0.eevee, 'use_fast_gi', '?'), getattr(sc0.eevee, 'fast_gi_distance', '?'), getattr(sc0.eevee, 'use_shadows', '?')))

# --- camaras ---
def add_cam(name, loc, target, lens=35):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 10000
    cam = bpy.data.objects.new(name, cd)
    cam.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    col.objects.link(cam)
    return cam

xs = [p['x'] for p in S]; ys = [p['y'] for p in S]
cxm, cym = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
i18 = next(c['s_idx'] for c in G['curvas'] if c['n'] == 18)
p18 = S[i18 % N]
i34 = next(c['s_idx'] for c in G['curvas'] if c['n'] == 34)
p34 = S[i34 % N]

cams = [
    ('vista_aerea', (cxm - 300, cym - 1500, 1250), (cxm, cym, 30), 32),
    ('meta_puerto', (p0['x'] - 120, p0['y'] - 160, 55), (p0['x'], p0['y'], p0['z'] + 4), 40),
    ('cima_tierra', (p18['x'] - 220, p18['y'] - 260, p18['z'] + 130), (p18['x'], p18['y'], p18['z']), 45),
    ('bahia_casino', (p34['x'] - 380, p34['y'] - 320, 190), (p34['x'], p34['y'], 10), 40),
]
cam_objs = [add_cam(*c) for c in cams]

# --- render ---
sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
for cam, spec in zip(cam_objs, cams):
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT_R, spec[0] + '.png')
    bpy.ops.render.render(write_still=True)
    print('render:', spec[0])

# fase visual F1 r2 (director_f1_r1.md 1, propietario mascara): este script arranca con --factory-startup (fichero SIN nombre)
# y save_as_mainfile() lleva relative_remap=True por defecto: al guardar por primera vez convertia TODAS las rutas de imagen a
# '//texturas\...' aunque _imagen() las cargue absolutas; la copia _rev/escena_candidata.blend (otra carpeta) no las resolvia y
# el terreno/arcenes/roca salian MAGENTA en modo normal. relative_remap=False deja las rutas ABSOLUTAS (como las tenia
# escena_antes_visual.blend; integrar_escena/aplicar_texturas guardan sobre el mismo fichero y no remapean). Se comprueba
# antes (red: cualquier '//' se hace absoluta respecto a 03_blender/) y despues de guardar; si quedara alguna, exit 1.
# F1 r4: SOLO pruebas sobre copia (BLEND_OUT): TERRENO_BANDA_2M=1 subdivide ya la banda de 2 m (en el pipeline lo hace
# _rev/banda_terreno_2m.py al final, cuando integrar/asentar/revisar_* ya no necesitan la rejilla nx*ny)
if os.environ.get('TERRENO_BANDA_2M') == '1' and os.environ.get('BLEND_OUT'):
    _ter4 = bpy.data.objects.get('TERRENO')
    _s4 = subdividir_banda_terreno(_ter4) if _ter4 is not None else None
    if _s4:
        print('terreno: banda 2 m aplicada (pruebas): celdas %d, vertices %d -> %d (+%d), tris %d -> %d, canal A en los medios %s'
              % (_s4['celdas'], _s4['vertices_antes'], _s4['vertices_despues'], _s4['vertices_nuevos'], _s4['tris_antes'],
                 _s4['tris_despues'], _s4['canal_a_en_medios']))
        _z4b = roca_zonas_nz(_ter4)
        if _z4b:
            print('terreno: zonas tras la banda: caras de roca AC %d -> %d, dientes %d -> %d' % (
                _z4b['global']['roca_antes'], _z4b['global']['roca_despues'], _z4b['global']['dientes_antes'], _z4b['global']['dientes_despues']))
_rel = [im.name for im in bpy.data.images if (im.filepath or '').startswith('//')]
if _rel:
    print('AVISO: %d imagenes con ruta relativa antes de guardar (se hacen absolutas): %s' % (len(_rel), _rel[:8]))
    for im in bpy.data.images:
        if (im.filepath or '').startswith('//'):
            im.filepath = os.path.normpath(os.path.join(BASE, '03_blender', im.filepath[2:]))
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, relative_remap=False)
_rel = [im.name for im in bpy.data.images if (im.filepath or '').startswith('//')]
_abs = sum(1 for im in bpy.data.images if im.filepath and not im.filepath.startswith('//'))
print('rutas de imagen tras guardar: %d absolutas, %d relativas%s' % (_abs, len(_rel), (' ' + str(_rel[:8])) if _rel else ''))
if _rel:
    print('ERROR: quedan imagenes con ruta relativa (//): la escena saldria MAGENTA fuera de 03_blender/ (director_f1_r1.md 1)')
    sys.exit(1)
print('OK blend ->', OUT_BLEND)
