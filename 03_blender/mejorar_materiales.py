"""Pase de enriquecimiento de materiales de Porto Corsa (Cars 2).

Abre porto_corsa.blend, inyecta variacion sutil procedural (patina, desgaste,
hiladas de tejas, despiece de piedra) en los materiales de arquitectura y
guarda el blend en la MISMA ruta.

Idempotente: cada arbol de nodos tocado se marca con un nodo name='MEJORADO'
y se salta en pasadas posteriores.

FASE VISUAL F1 (bloque 3 punto 7 y 7.1; propietario 'materiales'), dos pasadas mas, tambien idempotentes:
  bisel_barato(objs=None, angulo=35)
      "Bisel" sin geometria: shade_smooth + auto smooth por angulo (atributo sharp_edge en las aristas cuya
      cara-cara supera `angulo` grados) en las mallas de los kits que hoy van en shade_flat (CASAS_, muros y
      pretiles, bancales, civicos, PIT_, PUERTO_: BISEL_PREFIJOS). El writer exporta corner_normals, asi que el
      canto redondeado llega a AC. NUNCA en TERRENO, agua, pista, vegetacion ni mallas con normales
      personalizadas; nada de modificador Bevel (vertices x2). Marca: mesh['bisel_auto_smooth'] = angulo.
  horizonte(objs=None, color_cielo=None, d_cerca=2400, d_lejos=4500, f_cerca=0.35, f_lejos=0.55)
      Perspectiva atmosferica HORNEADA en el color: los materiales de los objetos HORIZ_* (anillo de fondo del
      propietario 'horizonte', bloque 7.1) se mezclan con la BRUMA al 35-55 % segun la distancia del objeto al centro
      del circuito (en AC a pelo no hay niebla fiable). Parte de mat['horiz_base_rgb'] (kit) o mat['horiz_color_base']
      (este pase) y es idempotente. Tambien vale como funcion pura horizonte(rgb_lineal, dist_m) -> rgb_lineal =
      mezcla_horizonte(): el contrato 'mezcla' de montanas_fondo_v2.build_anillo_horizonte(mezcla=mejorar_materiales.horizonte).
      F1 r2 (director r1, problema 4 "icebergs"): la bruma NO es el color del cielo tal cual. El cielo del world es
      EMISIVO (se ve a su valor: 0.70, 0.84, 0.98 -> #BAE0FE junto al horizonte) pero un material es ALBEDO y lo
      ilumina el sol (x1.6-2.5 en estas escenas: la hierba seca 0.55/0.45/0.20 sale #F4EDBC): mezclar hacia el cielo
      daba albedos 0.77-0.86 que al sol se recortan a BLANCO (#F0FFFF-#FFFFFF en 13/21/55/57, mas claras que el cielo).
      Ahora: bruma = cielo x HORIZ_CIELO_ATENUACION (0.42) x HORIZ_TINTE (algo violacea), mezcla LINEAL base/bruma,
      canal maximo del albedo acotado a HORIZ_ALBEDO_MAX (0.36 lineal = sRGB 0.63) y saturacion sRGB minima
      HORIZ_S_MIN (0.15) empujando hacia la bruma: la silueta queda ALGO mas oscura y mas violacea que el cielo, nunca
      mas clara; diffuse_color resultante con V (sRGB) <= HORIZ_V_MAX (0.85) y S >= 0.15 en todos los MAT_HORIZ_*
      (lo comprueba y lo imprime). Constantes anulables desde paleta.json['horizonte'] (misma clave en minusculas).

Ejecutar:
  blender --background --python mejorar_materiales.py            (blend real)
  blender --background --python mejorar_materiales.py -- <ruta>  (otro blend)
  ... -- <ruta> --sin-bisel        salta el bisel (depuracion)

Estilo Cars 2: saturado y limpio; la variacion es MUY sutil (multiply
0.12-0.18, bump 0.25-0.3 con Distance corto), nada de ruido fuerte.
"""
import json
import math
import os
import random
import sys

import bpy

BLEND_REAL = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\porto_corsa.blend"
AQUI = os.path.dirname(os.path.abspath(__file__))
PALETA_JSON = os.path.join(AQUI, 'paleta.json')

# (b) filtro de materiales objetivo
PREFIJOS = ("MAT_CASAS_", "MAT_CASINO_", "MAT_PUENTES_", "MAT_EDIF",
            "MAT_HOTEL", "MAT_AYTO", "MAT_CAMPANILE", "MAT_piedra")
EXCLUIR = ("vidrio", "cristal", "glass", "luz", "emis", "persiana")
CLAVES_TEJADO = ("teja", "tejado", "roof")
CLAVES_PIEDRA = ("piedra", "stone", "dovela")

# --- bisel barato (F1): objetos por prefijo de nombre (los kits que van en shade_flat) ---
BISEL_PREFIJOS = ('CASAS_', 'CAMINO_muro', 'MUROC', 'CARRERA_muro', 'ITAL_bancal', 'ITAL_fuente', 'ITAL_ermita',
                  'ITAL_capitella', 'ITAL_pergola', 'CIVICO_', 'AYTO_', 'HOTEL_', 'CAMPANILE_', 'CASINO_',
                  'PIT_', 'PUERTO_', 'CARRERA_tribuna', 'CARRERA_boxes', 'MIRADOR_parking', 'MIRADOR_pasarela',
                  'CALLE_plaza', 'CALLE_plazoleta', 'ACERA_', 'BORDILLO_', 'EDIF', 'TUNEL_portal', 'CARRERA_portico')
# nunca: terreno, agua, pista y fisica, vegetacion, rocas (traen sus normales), suelos de pit/puerto (fisica)
BISEL_NUNCA = ('TERRENO', 'AGUA', 'PISTA', 'PIANOS', 'PIT_LANE', 'PIT_marcas', 'PIT_suelo', 'PUERTO_dique_malla',
               'VEG_', 'OLI_', 'PENON_', 'MCOCHE_', 'TUNEL_acantilado', 'ARCEN', 'LINEA', 'MARCA', 'LOEWS', 'AC_',
               '1WALL_', '1ROAD_', '1GRASS_', '2GRASS_', '1DIRT_', '1KERB_', 'cierre')
BISEL_ANGULO = 35.0
HORIZ_PREFIJO = 'HORIZ_'
COLOR_CIELO = (0.70, 0.84, 0.98)
# --- horizonte (F1 r2): bruma = cielo x atenuacion x tinte; albedo acotado; saturacion minima (ver docstring) ---
HORIZ_CIELO_ATENUACION = 0.42      # el cielo es emisivo, el albedo se ilumina x1.6-2.5: bruma = cielo x 0.42
HORIZ_TINTE = (1.00, 0.90, 1.06)   # algo violacea (G abajo, B arriba: H ~232, S ~0.15): "mas violacea que el cielo", no cian
HORIZ_ALBEDO_MAX = 0.36            # canal maximo lineal del diffuse_color final (sRGB 0.63): al sol el azul no se recorta
HORIZ_V_MAX = 0.85                 # comprobacion del director: V (sRGB) del diffuse_color <= 0.85
HORIZ_S_MIN = 0.15                 # ... y S (sRGB) >= 0.15 (empuja hacia la bruma hasta cumplirlo)


def _cfg_horizonte():
    """Constantes del horizonte, anulables desde paleta.json['horizonte'] (claves en minusculas sin 'horiz_')."""
    cfg = {'cielo_atenuacion': HORIZ_CIELO_ATENUACION, 'tinte': HORIZ_TINTE, 'albedo_max': HORIZ_ALBEDO_MAX,
           'v_max': HORIZ_V_MAX, 's_min': HORIZ_S_MIN}
    try:
        with open(PALETA_JSON, encoding='utf-8') as fh:
            h = json.load(fh).get('horizonte', {})
        for k in cfg:
            if k in h and not str(k).startswith('_'):
                cfg[k] = tuple(h[k]) if isinstance(h[k], (list, tuple)) else float(h[k])
    except Exception:
        pass
    return cfg


def lin_a_srgb(c):
    c = min(1.0, max(0.0, float(c)))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1.0 / 2.4) - 0.055


def hsv_srgb(rgb_lin):
    """(H grados, S, V) en sRGB del color lineal dado (la V y la S que mide el director sobre el hex)."""
    import colorsys
    r, g, b = (lin_a_srgb(c) for c in tuple(rgb_lin)[:3])
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360.0, s, v


def hex_srgb(rgb_lin):
    return '#' + ''.join('%02X' % int(round(lin_a_srgb(c) * 255)) for c in tuple(rgb_lin)[:3])


def _luminancia(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def bruma_horizonte(color_cielo, cfg=None):
    """Albedo de la bruma: el cielo del horizonte atenuado y ligeramente violaceo (RGB lineal)."""
    cfg = cfg or _cfg_horizonte()
    return tuple(min(1.0, float(s) * cfg['cielo_atenuacion'] * t) for s, t in zip(tuple(color_cielo)[:3], cfg['tinte']))


def acotar_horizonte(rgb, bruma, cfg=None):
    """Acota un albedo de horizonte: canal maximo <= albedo_max (escala, conserva el tono) y S (sRGB) >= s_min
    (mezcla hacia la bruma a igual luminancia). Devuelve el RGB lineal acotado."""
    cfg = cfg or _cfg_horizonte()
    col = [max(0.0, float(c)) for c in tuple(rgb)[:3]]
    lb = max(_luminancia(bruma), 1e-6)

    def _tope(c):
        m = max(c)
        return [x * cfg['albedo_max'] / m for x in c] if m > cfg['albedo_max'] > 0 else c

    col = _tope(col)
    for _ in range(24):
        if hsv_srgb(col)[1] >= cfg['s_min'] - 0.002:
            break
        lc = _luminancia(col)
        br = [b * lc / lb for b in bruma]            # bruma a la luminancia del color: solo cambia el tono
        col = _tope([c * 0.7 + b * 0.3 for c, b in zip(col, br)])
    return tuple(min(1.0, c) for c in col)


def es_objetivo(mat):
    low = mat.name.lower()
    return (mat.name.startswith(PREFIJOS)
            and not any(e in low for e in EXCLUIR))


def buscar_principled(nt):
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


def nuevo_mix_color(nodes):
    """Crea un nodo de mezcla de color MULTIPLY y devuelve
    (nodo, socket_fac, socket_a, socket_b, socket_out)."""
    try:
        n = nodes.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.blend_type = 'MULTIPLY'
        n.clamp_result = True
        ins = [s for s in n.inputs if s.type == 'RGBA']
        outs = [s for s in n.outputs if s.type == 'RGBA']
        return n, n.inputs[0], ins[0], ins[1], outs[0]
    except RuntimeError:
        n = nodes.new('ShaderNodeMixRGB')  # fallback API antigua
        n.blend_type = 'MULTIPLY'
        return n, n.inputs['Fac'], n.inputs['Color1'], n.inputs['Color2'], n.outputs['Color']


def mejorar_material(mat):
    """Inyecta la variacion en un material. Devuelve True si lo toco."""
    if not mat.use_nodes or not mat.node_tree:
        return False
    nt = mat.node_tree
    # (a) idempotencia
    if nt.nodes.get('MEJORADO'):
        return False
    principled = buscar_principled(nt)
    if principled is None:
        return False

    nodes, links = nt.nodes, nt.links
    rnd = random.Random(mat.name)  # determinista por material
    low = mat.name.lower()
    px, py = principled.location

    # marca de idempotencia
    marca = nodes.new('NodeFrame')
    marca.name = 'MEJORADO'
    marca.label = 'MEJORADO'
    marca.location = (px - 900, py + 300)

    # ---- (c) patina sutil antes del Base Color -------------------------
    ent_base = principled.inputs['Base Color']
    color_base = tuple(ent_base.default_value[:])
    enlace_previo = ent_base.links[0].from_socket if ent_base.links else None

    noise = nodes.new('ShaderNodeTexNoise')
    noise.name = 'MEJ_noise_color'
    noise.location = (px - 860, py - 40)
    noise.inputs['Scale'].default_value = rnd.uniform(3.0, 6.5)
    noise.inputs['Detail'].default_value = 3.0
    noise.inputs['Roughness'].default_value = 0.45

    rampa = nodes.new('ShaderNodeValToRGB')
    rampa.name = 'MEJ_rampa_patina'
    rampa.location = (px - 660, py - 40)
    rampa.color_ramp.interpolation = 'EASE'
    e0, e1 = rampa.color_ramp.elements[0], rampa.color_ramp.elements[1]
    e0.position = 0.25
    e0.color = (0.48, 0.43, 0.38, 1.0)  # mancha calida suave
    e1.position = 0.62
    e1.color = (1.0, 1.0, 1.0, 1.0)

    mix, s_fac, s_a, s_b, s_out = nuevo_mix_color(nodes)
    mix.name = 'MEJ_mix_patina'
    mix.location = (px - 320, py - 20)
    s_fac.default_value = rnd.uniform(0.12, 0.18)
    s_a.default_value = color_base
    s_b.default_value = (1.0, 1.0, 1.0, 1.0)

    links.new(rampa.outputs['Color'], s_b)
    if enlace_previo is not None:
        links.new(enlace_previo, s_a)
    links.new(noise.outputs['Fac'], rampa.inputs['Fac'])
    links.new(s_out, ent_base)

    # ---- (c) variacion de Roughness +-0.1 ------------------------------
    ent_rough = principled.inputs['Roughness']
    if not ent_rough.links:
        rough_base = float(ent_rough.default_value)
        noise_r = nodes.new('ShaderNodeTexNoise')
        noise_r.name = 'MEJ_noise_rough'
        noise_r.location = (px - 860, py - 340)
        noise_r.inputs['Scale'].default_value = rnd.uniform(4.0, 9.0)
        noise_r.inputs['Detail'].default_value = 2.0

        mapr = nodes.new('ShaderNodeMapRange')
        mapr.name = 'MEJ_map_rough'
        mapr.location = (px - 660, py - 340)
        mapr.clamp = True
        mapr.inputs['From Min'].default_value = 0.0
        mapr.inputs['From Max'].default_value = 1.0
        mapr.inputs['To Min'].default_value = max(0.02, rough_base - 0.1)
        mapr.inputs['To Max'].default_value = min(1.0, rough_base + 0.1)

        links.new(noise_r.outputs['Fac'], mapr.inputs['Value'])
        links.new(mapr.outputs['Result'], ent_rough)

    # ---- (d)/(e) bump segun tipo ---------------------------------------
    es_tejado = any(k in low for k in CLAVES_TEJADO)
    es_piedra = any(k in low for k in CLAVES_PIEDRA)
    ent_normal = principled.inputs['Normal']
    if not ent_normal.links and (es_tejado or es_piedra):
        bump = nodes.new('ShaderNodeBump')
        bump.name = 'MEJ_bump'
        bump.location = (px - 320, py - 560)
        if es_tejado:
            # (d) hiladas de tejas: bandas horizontales
            wave = nodes.new('ShaderNodeTexWave')
            wave.name = 'MEJ_wave_tejas'
            wave.location = (px - 660, py - 560)
            wave.wave_type = 'BANDS'
            # hiladas paralelas a la cumbrera (fachada +Y => cumbrera en X):
            # las bandas avanzan a lo largo de Y y se ven desde arriba
            if hasattr(wave, 'bands_direction'):
                wave.bands_direction = 'Y'
            wave.wave_profile = 'SIN'
            wave.inputs['Scale'].default_value = 40.0
            wave.inputs['Distortion'].default_value = 1.0
            wave.inputs['Detail'].default_value = 1.0
            bump.inputs['Strength'].default_value = 0.3
            # el Distance por defecto (1 mm) es invisible a escala de edificio;
            # 0.025 marca las hiladas sin convertirlas en chapa ondulada
            if 'Distance' in bump.inputs:
                bump.inputs['Distance'].default_value = 0.025
            links.new(wave.outputs['Fac'], bump.inputs['Height'])
        else:
            # (e) despiece de sillares. El patron de Brick vive en el plano XY
            # del vector: rotamos 90 grados en X para proyectarlo sobre los
            # muros verticales (fachada +Y del contrato).
            tco = nodes.new('ShaderNodeTexCoord')
            tco.name = 'MEJ_texcoord'
            tco.location = (px - 1060, py - 560)
            mapping = nodes.new('ShaderNodeMapping')
            mapping.name = 'MEJ_mapping'
            mapping.location = (px - 880, py - 560)
            mapping.inputs['Rotation'].default_value = (1.5707964, 0.0, 0.0)
            links.new(tco.outputs['Generated'], mapping.inputs['Vector'])

            brick = nodes.new('ShaderNodeTexBrick')
            brick.name = 'MEJ_brick_despiece'
            brick.location = (px - 660, py - 560)
            brick.offset = 0.5
            # filas visibles = escala / alto de fila (0.25): ~6-10 hiladas
            brick.inputs['Scale'].default_value = rnd.uniform(1.6, 2.4)
            brick.inputs['Mortar Size'].default_value = 0.02
            brick.inputs['Mortar Smooth'].default_value = 0.5
            links.new(mapping.outputs['Vector'], brick.inputs['Vector'])
            brick.inputs['Color1'].default_value = (1.0, 1.0, 1.0, 1.0)
            brick.inputs['Color2'].default_value = (1.0, 1.0, 1.0, 1.0)
            brick.inputs['Mortar'].default_value = (0.0, 0.0, 0.0, 1.0)
            bump.inputs['Strength'].default_value = 0.25
            if 'Distance' in bump.inputs:
                bump.inputs['Distance'].default_value = 0.03
            bump.invert = True  # juntas hundidas
            links.new(brick.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], ent_normal)

    return True


def _set(ins, nombre, valor):
    if nombre in ins:
        try:
            ins[nombre].default_value = valor
            return True
        except Exception:
            return False
    return False


def pintura_coches():
    """Pintura METALIZADA con laca en los coches (carroceria/techo/labio) y cromados
    y vidrios reflectantes: los reflejos los da el trazado de rayos de EEVEE."""
    n = 0
    for mat in bpy.data.materials:
        nm = mat.name
        if not (nm.startswith('MAT_COCHE_') or nm.startswith('MAT_CAMARA_') or nm.startswith('MAT_PIT_coche')):
            continue
        if not mat.use_nodes or mat.node_tree is None:
            continue
        bsdf = buscar_principled(mat.node_tree)
        if bsdf is None:
            continue
        ins = bsdf.inputs
        low = nm.lower()
        if any(k in low for k in ('cuerpo', 'techo', 'labio', 'carroceria', 'body', 'franja', 'librea')):
            _set(ins, 'Metallic', 0.22)
            _set(ins, 'Roughness', 0.30)
            _set(ins, 'Coat Weight', 0.7)
            _set(ins, 'Coat Roughness', 0.08)
            _set(ins, 'Specular IOR Level', 0.6)
            n += 1
        elif any(k in low for k in ('cromo', 'chrome', 'llanta', 'tapacubo', 'aro', 'parachoques')):
            _set(ins, 'Metallic', 0.95)
            _set(ins, 'Roughness', 0.18)
            n += 1
        elif any(k in low for k in ('vidrio', 'cristal', 'glass', 'parabrisas', 'lente', 'ojo_brillo')):
            _set(ins, 'Metallic', 0.0)
            _set(ins, 'Roughness', 0.06)
            _set(ins, 'Specular IOR Level', 0.9)
            _set(ins, 'Coat Weight', 1.0)
            _set(ins, 'Coat Roughness', 0.03)
            n += 1
    # reflejos en pantalla (EEVEE Next): trazado de rayos
    sc = bpy.context.scene
    for attr, val in (('use_raytracing', True),):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    try:
        sc.eevee.ray_tracing_options.resolution_scale = '2'
        sc.eevee.ray_tracing_options.screen_trace_quality = 0.5
    except Exception:
        pass
    print('PINTURA COCHES: %d materiales metalizados/cromados/vidrio; raytracing EEVEE activado' % n)
    return n


# ----------------------------------------------------------------------------------- bisel barato (F1)
def _marcar_aristas_vivas(me, angulo):
    """Atributo sharp_edge = True en las aristas cuyas dos caras forman mas de `angulo` grados (y en las no
    manifold); el resto suave. numpy sobre loops (polygon index por loop + edge_index). Devuelve n aristas vivas."""
    import numpy as np
    npoly, nloop, nedge = len(me.polygons), len(me.loops), len(me.edges)
    if npoly == 0 or nedge == 0:
        return 0
    pn = np.empty(npoly * 3, np.float32)
    me.polygons.foreach_get('normal', pn)
    pn = pn.reshape(-1, 3)
    ls = np.empty(npoly, np.int32)
    me.polygons.foreach_get('loop_start', ls)
    le = np.empty(nloop, np.int32)
    me.loops.foreach_get('edge_index', le)
    # poligono de cada loop: los loops van contiguos por poligono en orden de loop_start
    marca = np.zeros(nloop, np.int32)
    marca[ls[1:]] = 1
    lp = np.cumsum(marca)
    orden = np.argsort(le, kind='stable')
    le_s, lp_s = le[orden], lp[orden]
    # inicio de cada grupo de aristas iguales
    ini = np.flatnonzero(np.r_[True, le_s[1:] != le_s[:-1]])
    cnt = np.diff(np.r_[ini, len(le_s)])
    sharp = np.zeros(nedge, bool)
    # exactamente 2 caras: angulo entre normales
    dos = ini[cnt == 2]
    if len(dos):
        a, b = lp_s[dos], lp_s[dos + 1]
        dot = np.einsum('ij,ij->i', pn[a], pn[b])
        sharp[le_s[dos]] = dot < math.cos(math.radians(angulo))
    # > 2 caras (no manifold): viva
    mas = ini[cnt > 2]
    if len(mas):
        sharp[le_s[mas]] = True
    attr = me.attributes.get('sharp_edge')
    if attr is None or attr.domain != 'EDGE' or attr.data_type != 'BOOLEAN':
        if attr is not None:
            me.attributes.remove(attr)
        attr = me.attributes.new('sharp_edge', 'BOOLEAN', 'EDGE')
    attr.data.foreach_set('value', sharp)
    return int(sharp.sum())


def _candidato_bisel(ob):
    if ob.type != 'MESH' or ob.data is None:
        return False
    n = ob.name
    if n.startswith(BISEL_NUNCA):
        return False
    if not n.startswith(BISEL_PREFIJOS):
        return False
    if any(m.type == 'BEVEL' for m in ob.modifiers):
        return False
    return True


def bisel_barato(objs=None, angulo=BISEL_ANGULO):
    """shade_smooth + auto smooth por angulo (sharp_edge) en las mallas de BISEL_PREFIJOS. Idempotente por malla
    (mesh['bisel_auto_smooth']). Devuelve (mallas tocadas, mallas saltadas, aristas vivas)."""
    objs = list(objs) if objs is not None else list(bpy.data.objects)
    vistas, tocadas, saltadas, vivas = set(), 0, 0, 0
    for ob in objs:
        if not _candidato_bisel(ob):
            continue
        me = ob.data
        if me.name in vistas:
            continue
        vistas.add(me.name)
        if me.get('bisel_auto_smooth') is not None:
            saltadas += 1
            continue
        if getattr(me, 'has_custom_normals', False):
            saltadas += 1
            continue
        if len(me.polygons) == 0:
            continue
        try:
            me.shade_smooth()
        except AttributeError:
            import numpy as np
            me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), bool))
        vivas += _marcar_aristas_vivas(me, angulo)
        me['bisel_auto_smooth'] = float(angulo)
        me.update()
        tocadas += 1
    print('BISEL BARATO: %d mallas suavizadas (auto smooth %.0f grados, %d aristas vivas), %d ya hechas/saltadas'
          % (tocadas, angulo, vivas, saltadas))
    return tocadas, saltadas, vivas


# ----------------------------------------------------------------------------------- horizonte (F1, 7.1)
def _centro_circuito():
    t = bpy.data.objects.get('TERRENO')
    if t is not None and t.type == 'MESH':
        bb = [t.matrix_world @ __import__('mathutils').Vector(c) for c in t.bound_box]
        return (sum(v.x for v in bb) / 8.0, sum(v.y for v in bb) / 8.0)
    return (0.0, 0.0)


def color_cielo_world(defecto=COLOR_CIELO):
    """Color del horizonte del world 'CIELO' de construir_pista (primer elemento de su ColorRamp); si no, el defecto."""
    w = bpy.data.worlds.get('CIELO') or bpy.context.scene.world
    try:
        if w is not None and w.node_tree:
            for n in w.node_tree.nodes:
                if n.type == 'VALTORGB' and len(n.color_ramp.elements) >= 2:
                    return tuple(float(c) for c in n.color_ramp.elements[0].color[:3])
    except Exception:
        pass
    return tuple(defecto)


def factor_horizonte(dist_m, d_cerca=2400.0, d_lejos=4500.0, f_cerca=0.35, f_lejos=0.55):
    t = 0.0 if d_lejos <= d_cerca else min(1.0, max(0.0, (float(dist_m) - d_cerca) / (d_lejos - d_cerca)))
    return f_cerca + (f_lejos - f_cerca) * t


def mezcla_horizonte(rgb, dist_m, color_cielo=None, d_cerca=2400.0, d_lejos=4500.0, f_cerca=0.35, f_lejos=0.55, cfg=None):
    """Contrato del propietario 'horizonte' (montanas_fondo_v2.build_anillo_horizonte(mezcla=...)):
    mezcla(rgb_lineal, dist_m) -> rgb_lineal: el color de paleta mezclado LINEALMENTE con la BRUMA (cielo atenuado y
    violaceo, bruma_horizonte) al 35 % (2.4 km) .. 55 % (4.5 km), y acotado (acotar_horizonte): albedo maximo 0.42 y
    S >= 0.15, para que al sol la silueta quede algo mas oscura y violacea que el cielo (F1 r2)."""
    cfg = cfg or _cfg_horizonte()
    cielo = tuple(color_cielo) if color_cielo is not None else color_cielo_world()
    bruma = bruma_horizonte(cielo, cfg)
    f = factor_horizonte(dist_m, d_cerca, d_lejos, f_cerca, f_lejos)
    col = tuple(float(b) * (1.0 - f) + float(s) * f for b, s in zip(tuple(rgb)[:3], bruma))
    return acotar_horizonte(col, bruma, cfg)


def horizonte(objs=None, color_cielo=None, d_cerca=2400.0, d_lejos=4500.0, f_cerca=0.35, f_lejos=0.55):
    """Dos usos:
      horizonte(rgb_lineal, dist_m) -> rgb_lineal            (contrato 'mezcla' del kit montanas_fondo_v2: puro, sin escena)
      horizonte() / horizonte(objs=[...]) -> n materiales     (pase de escena: mezcla el color de los materiales de los
          objetos HORIZ_* con el cielo al f_cerca..f_lejos segun su distancia al centro del circuito; perspectiva
          atmosferica horneada). Idempotente: parte de mat['horiz_base_rgb'] (lo escribe el kit) o de
          mat['horiz_color_base'] (lo guarda este pase la primera vez); distancia = mat['horiz_dist_m'] si el kit la
          anoto, si no la media de las distancias de los objetos que usan el material.
    color_cielo None = el horizonte del world 'CIELO' (0.70, 0.84, 0.98 en construir_pista)."""
    from mathutils import Vector
    if objs is not None and not hasattr(objs, '__iter__') or (
            objs is not None and len(tuple(objs)) == 3 and all(isinstance(c, (int, float)) for c in tuple(objs))
            and isinstance(color_cielo, (int, float))):
        return mezcla_horizonte(objs, color_cielo, None, d_cerca, d_lejos, f_cerca, f_lejos)
    cielo = tuple(color_cielo) if color_cielo is not None else color_cielo_world()
    cfg = _cfg_horizonte()
    bruma = bruma_horizonte(cielo, cfg)
    objs = [o for o in (objs if objs is not None else bpy.data.objects)
            if o.type == 'MESH' and o.name.startswith(HORIZ_PREFIJO)]
    if not objs:
        return 0
    cx, cy = _centro_circuito()
    dist = {}
    for o in objs:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        c = (sum(v.x for v in bb) / 8.0, sum(v.y for v in bb) / 8.0)
        d = math.hypot(c[0] - cx, c[1] - cy)
        for m in o.data.materials:
            if m is not None:
                dist.setdefault(m.name, []).append(d)
    n = 0
    fuera = []
    v_max_vis, s_min_vis = 0.0, 1.0
    for nombre, ds in sorted(dist.items()):
        m = bpy.data.materials.get(nombre)
        if m is None:
            continue
        d = float(m['horiz_dist_m']) if m.get('horiz_dist_m') is not None else sum(ds) / len(ds)
        f = factor_horizonte(d, d_cerca, d_lejos, f_cerca, f_lejos)
        base = m.get('horiz_base_rgb')
        if base is None:
            base = m.get('horiz_color_base')
        if base is None:
            bs = buscar_principled(m.node_tree) if m.node_tree else None
            if bs is not None and not bs.inputs['Base Color'].is_linked:
                base = list(bs.inputs['Base Color'].default_value[:3])
            else:
                base = list(m.diffuse_color[:3])
            m['horiz_color_base'] = [float(c) for c in base]
        col = tuple(float(b) * (1.0 - f) + float(s) * f for b, s in zip(tuple(base)[:3], bruma))
        col = acotar_horizonte(col, bruma, cfg)
        h_, s_, v_ = hsv_srgb(col)
        v_max_vis, s_min_vis = max(v_max_vis, v_), min(s_min_vis, s_)
        if v_ > cfg['v_max'] + 0.005 or s_ < cfg['s_min'] - 0.005:
            fuera.append('%s %s V %.2f S %.2f' % (nombre, hex_srgb(col), v_, s_))
        print('  HORIZ %-32s base %s  d %5.0f m  f %.2f  -> %s  H %3.0f S %.2f V %.2f' % (
            nombre, hex_srgb(base), d, f, hex_srgb(col), h_, s_, v_))
        m.diffuse_color = col + (1.0,)
        if m.node_tree:
            bs = buscar_principled(m.node_tree)
            if bs is not None:
                if not bs.inputs['Base Color'].is_linked:
                    bs.inputs['Base Color'].default_value = col + (1.0,)
                else:
                    mix = m.node_tree.nodes.get('MEJ_mix_patina')
                    if mix is not None:
                        s_a = next((s for s in mix.inputs if s.type == 'RGBA'), None)
                        if s_a is not None and not s_a.is_linked:
                            s_a.default_value = col + (1.0,)
        m['horiz_mezcla'] = round(f, 3)
        m['horiz_distancia_m'] = round(d, 1)
        m['horiz_bruma_rgb'] = [round(float(c), 4) for c in bruma]
        n += 1
    print('HORIZONTE: %d materiales mezclados con la bruma %s (cielo %s x %.2f x tinte) al %.0f-%.0f %% entre %.0f y %.0f m; '
          'albedo max %.2f; V max %.2f (<= %.2f), S min %.2f (>= %.2f): %s' % (
              n, hex_srgb(bruma), hex_srgb(cielo), cfg['cielo_atenuacion'], f_cerca * 100, f_lejos * 100, d_cerca, d_lejos,
              cfg['albedo_max'], v_max_vis, cfg['v_max'], s_min_vis, cfg['s_min'],
              'OK' if not fuera else 'FUERA DE RANGO %s' % fuera))
    return n


def mejorar_blend(ruta, bisel=True):
    bpy.ops.wm.open_mainfile(filepath=ruta)
    tocados, saltados = [], 0
    pintura_coches()
    for mat in sorted(bpy.data.materials, key=lambda m: m.name):
        if not es_objetivo(mat):
            continue
        if mejorar_material(mat):
            tocados.append(mat.name)
        else:
            saltados += 1
    if bisel:
        bisel_barato()
    horizonte()
    bpy.ops.wm.save_as_mainfile(filepath=ruta)   # (la pintura de coches se guarda aunque no haya otros cambios)
    print("MEJORAR_MATERIALES: tocados=%d saltados=%d" % (len(tocados), saltados))
    for n in tocados:
        print("  +", n)
    print("Guardado:", ruta)
    return tocados


if __name__ == '__main__':
    argv = sys.argv
    ruta = BLEND_REAL
    bisel = True
    if '--' in argv:
        extra = argv[argv.index('--') + 1:]
        bisel = '--sin-bisel' not in extra
        pos = [a for a in extra if not a.startswith('--')]
        if pos:
            ruta = pos[0]
    mejorar_blend(ruta, bisel=bisel)
