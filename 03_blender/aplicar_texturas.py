"""Pase de texturizado tileable de Porto Corsa (Cars 2).

Abre porto_corsa.blend, aplica las texturas tileables de 03_blender/texturas/
a los materiales por familias y guarda el blend en la MISMA ruta.

Idempotente: cada arbol de nodos tocado se marca con un nodo name='TEXTURIZADO'
y se salta en pasadas posteriores (--rehacer [familias] quita la pasada previa y
vuelve a texturizar: para cambiar de tile sin regenerar la escena).

Mapeado por coordenadas de OBJETO (las mallas no tienen UVs):
Texture Coordinate->Object + Mapping con escala por familia. Los suelos planos
(asfalto, tierra, cesped de jardin) usan proyeccion plana; TODO lo que puede ser
ladera o pared (hierba del terreno, matorral, caliza, fachadas, tejados, piedra)
usa proyeccion BOX para no estirar en las caras verticales (fase visual F1:
'hierba' pasa de FLAT a BOX; era la 'hierba estirada' de 03/05/17/33/40/48/49).

FASE VISUAL F1 (bloque 3 punto 3, propietario 'materiales'). Familias:
  MAT_asfalto*                       -> asfalto_d multiplicada + bump suave (tile 8 m)
  MAT_tierra*, MAT_terreno_tierra    -> tierra_d multiplicada (tile 6 m)
  *teja* / *tejado* / *roof*         -> teja_d multiplicada + bump (tile 2 m)
  MAT_PUENTES*                       -> piedra_d suave (viaducto: ya trae hiladas)
  *piedra* / *stone* / *MUROC*       -> piedra_d multiplicada + bump (tile 3 m)
  MAT_cesped*, MAT_LOEWS_*, MAT_URB_jardin*, MAT_terreno_cesped   -> cesped_d (3 m): SOLO jardines y rotondas
  MAT_terreno_matorral, MAT_MONT_bosque*   -> matorral_d BOX (6 m)
  MAT_terreno_seca / _hierba_seca, MAT_arcen*  -> hierba_seca_d BOX (3 m)
  MAT_terreno                        -> hierba_seca_d (BOX, 3 m) multiplicada sobre su rampa, solo llano
                                        (hasta que el propietario 'mascara' lo sustituya por la mascara por texel:
                                        entonces MAT_terreno llega ya con marcador TEXTURIZADO y no se toca)
  *roca* / *caliza* / MAT_PPUEBLO_roca* / MAT_PPUEBLO_repisa / MAT_MCOCHE_caliza*  -> familia 'caliza':
                                        assets/materiales_roca.aplicar_a (grupo NG_caliza_estratos x caliza_d.png);
                                        si el material ya trae el grupo (marcador CALIZA_ESTRATOS) no se toca;
                                        si materiales_roca no se puede importar: caliza_d.png + manchas +-10 % (aplicar_roca)
  (F1 r2) al abrir el blend, actualizar_caliza(): un NG_caliza_estratos guardado de version anterior se reconstruye
  en sitio (v2 = tres tonos por orientacion: repisa caliza_ocre / pared caliza_gris_calido / junta caliza_sombra)
  sin tocar los enlaces de MAT_terreno ni de los kits; se guarda aunque no haya nada mas que texturizar.
  (F1 r3) MAT_MCOCHE_caliza* -> familia 'caliza_grande' (r4: caliza_grande_d.png 24 m, factor 0.3: el coche mide ~80 m
  y caliza_d a 12 m aun se leia repetido en 49 AC); --rehacer caliza,caliza_grande re-aplica el grupo con el tile/factor de la familia
  (F1 r4) materiales_roca v4 (estratos en parches, nz con ruido) y diffuse_color = media x tinte del tile (materiales_roca.
  media_material): el writer neutraliza el tile por canal, asi que la media exportada lleva el calor que el tile da en Blender
  (materiales_roca.reaplicar; nunca el terreno). Pasada rugosidad_mate(): Roughness 1 / Specular IOR Level 0 en las
  familias de terreno y roca y en todo lo que lleva el grupo (terreno incluido): sin Fresnel del cielo (el velo
  gris-cian de las lomas vistas rasantes y la caliza desaturada de 51; ksPerPixel tampoco lo tiene); y
  MAT_MCOCHE_cristal_pulido Roughness 0.5 (AJUSTES_BSDF). El grupo v3 (sin reticula, atenuado con la distancia,
  ao_pared) entra por actualizar_caliza() en una escena ya construida.
  MAT_agua                           -> agua_h como bump de olas (tile 40 m)
Nombres: el material de matorral del terreno se llama MAT_terreno_matorral (NO MAT_matorral:
color_ac.familia() lo clasificaria como 'pintado').

Cada textura de color va con ganancia 1/media_lineal para que el multiply aporte variacion SIN
oscurecer ni desaturar el color base (estilo Cars 2). La ganancia se lee de texturas/medias.json
(la escriben generar_texturas.py y recolorear_cc0.py: da igual si el tile es PIL o CC0); FAMILIAS
lleva el valor de respaldo medido el 04/10 (CC0 ya aplicado).
Image Texture siempre con ruta ABSOLUTA; color en sRGB, alturas/bump Non-Color.
Nodos TEX_ganancia / TEX_multiplicar / TEX_mapping / TEX_imagen = contrato con 04_export/kn5_writer_opt.py.

Ejecutar:
  blender --background --python aplicar_texturas.py             (blend real)
  blender --background --python aplicar_texturas.py -- <ruta>   (otro blend)
  ... -- <ruta> --rehacer                 quita la pasada previa de TODAS las familias y texturiza de nuevo
  ... -- <ruta> --rehacer terreno,hierba,caliza   solo esas familias
"""
import json
import os
import sys

import bpy

BLEND_REAL = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\porto_corsa.blend"
AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_TEX = os.path.join(AQUI, 'texturas')
MEDIAS_JSON = os.path.join(DIR_TEX, 'medias.json')
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

# ganancia = 1/media_lineal de cada png (texturas/medias.json; estos son los valores de respaldo medidos el
# 04/10 tras recolorear_cc0.py y re-medidos ~19:45 con la paleta v2: teja 4.87, piedra 1.99, caliza 1.78),
# para conservar el brillo medio
FAMILIAS = {
    # tex, tile en m (escala mapping = 1/tile), factor multiply, ganancia,
    # proyeccion, bump=(strength, distance) o None
    'asfalto':  dict(tex='asfalto_d.png', escala=1.0 / 8, factor=1.0,
                     ganancia=5.59, proy='FLAT', bump=(0.3, 0.015)),
    'tierra':   dict(tex='tierra_d.png', escala=1.0 / 6, factor=0.7,
                     ganancia=2.57, proy='BOX', bump=None),
    'teja':     dict(tex='teja_d.png', escala=1.0 / 2, factor=0.8,
                     ganancia=4.87, proy='BOX', bump=(0.35, 0.02)),
    'piedra':   dict(tex='piedra_d.png', escala=1.0 / 3, factor=0.75,
                     ganancia=1.99, proy='BOX', bump=(0.3, 0.02)),
    'piedra_suave': dict(tex='piedra_d.png', escala=1.0 / 3, factor=0.28,
                         ganancia=1.99, proy='BOX', bump=None),   # viaducto: ya trae hiladas propias
    'estuco':   dict(tex='estuco_d.png', escala=1.0 / 4, factor=0.72,
                     ganancia=1.25, proy='BOX', bump=None),
    # terreno (F1): hierba seca BOX en vez del cesped FLAT
    'hierba':   dict(tex='hierba_seca_d.png', escala=1.0 / 3, factor=0.85,
                     ganancia=2.21, proy='BOX', bump=None),
    'seca':     dict(tex='hierba_seca_d.png', escala=1.0 / 3, factor=0.85,
                     ganancia=2.21, proy='BOX', bump=None),
    'matorral': dict(tex='matorral_d.png', escala=1.0 / 6, factor=0.85,
                     ganancia=5.47, proy='BOX', bump=None),
    'cesped':   dict(tex='cesped_d.png', escala=1.0 / 3, factor=0.85,
                     ganancia=2.40, proy='BOX', bump=None),
    'bosque':   dict(tex='matorral_d.png', escala=1.0 / 6, factor=0.8,
                     ganancia=5.47, proy='BOX', bump=None),
    # caliza: tile de 6 m (a 3 m el CC0 rock_06 repetia en rejilla visible); los estratos los pone el grupo
    'caliza':   dict(tex='caliza_d.png', escala=1.0 / 6, factor=0.5,
                     ganancia=1.78, proy='BOX', bump=(0.3, 0.03)),
    # F1 r3/r4: McLaren (MAT_MCOCHE_caliza*): el coche mide ~80 m; con caliza_d a 12 m (r3) el tile seguia leyendose
    # repetido en 49 AC (manchas claras cada ~95 px = 12 m; director r3 n.4). r4: tile DERIVADO caliza_grande_d.png (24 m,
    # dos escalas + ruido de baja frecuencia, contraste 60 %: saliencia a 24 px 0.022 frente a 0.075) y factor 0.3
    # (= montana_coche_v2.TILE_CALIZA_M / FACTOR_CALIZA / IMAGEN_CALIZA)
    'caliza_grande': dict(tex='caliza_grande_d.png', escala=1.0 / 24, factor=0.5,
                          ganancia=1.63, proy='BOX', bump=(0.3, 0.03)),
    'agua':     dict(tex='agua_h.png', escala=1.0 / 40, factor=0.0,
                     ganancia=1.0, proy='FLAT', bump=(1.0, 0.4)),
}

EXCLUIR_FACHADA = ('vidrio', 'cristal', 'persiana', 'luz', 'emis')
PREFIJOS_FACHADA = ('MAT_CASAS_', 'MAT_CASINO_', 'MAT_CIVICO_', 'MAT_HOTEL_')
CLAVES_TEJA = ('teja', 'tejado', 'roof')
CLAVES_PIEDRA = ('piedra', 'stone', 'muroc')
PREFIJOS_CESPED = ('mat_cesped', 'mat_loews_', 'mat_urb_jardin', 'mat_terreno_cesped')
# cesped de jardin: en la Loews solo los materiales de hierba/seto (no la piedra, flores, tronco...)
CLAVES_CESPED_LOEWS = ('cesped', 'hierba', 'seto', 'jardin')
PREFIJOS_CALIZA = ('mat_ppueblo_roca', 'mat_ppueblo_repisa', 'mat_mcoche_caliza', 'mat_mont_roca',
                   'mat_penon_caliza', 'mat_penon_meseta', 'mat_mrueda_caliza', 'mat_terreno_roca', 'mat_terreno_caliza')
CLAVES_CALIZA = ('roca', 'caliza')
NO_CALIZA = ('mascara',)   # subcadenas que NO son roca aunque lleven 'roca'

_medias = None


def ganancia_de(cfg):
    """1/media lineal del tile: texturas/medias.json si existe (PIL o CC0, da igual), si no FAMILIAS."""
    global _medias
    if _medias is None:
        _medias = {}
        try:
            with open(MEDIAS_JSON, encoding='utf-8') as fh:
                _medias = json.load(fh)
        except Exception as e:  # noqa
            print('AVISO: sin texturas/medias.json (%s): ganancias de respaldo de FAMILIAS' % e)
    e = _medias.get(cfg['tex'])
    if e and e.get('ganancia'):
        return float(e['ganancia'])
    return float(cfg['ganancia'])


def familia_de(mat):
    """Clasifica el material; None si no se texturiza."""
    n = mat.name
    low = n.lower()
    if low.startswith('mat_asfalto'):
        return 'asfalto'
    if low.startswith('mat_tierra') or low.startswith('mat_terreno_tierra'):
        return 'tierra'
    if any(k in low for k in CLAVES_TEJA):
        return 'teja'
    if low.startswith('mat_puentes'):
        return 'piedra_suave'
    if low.startswith(PREFIJOS_CESPED):
        if low.startswith('mat_loews_') and not any(k in low for k in CLAVES_CESPED_LOEWS):
            return None
        return 'cesped'
    if low.startswith('mat_mcoche_caliza'):
        return 'caliza_grande'
    if low.startswith(PREFIJOS_CALIZA):
        return 'caliza'
    if any(k in low for k in CLAVES_PIEDRA):
        return 'piedra'
    if low.startswith('mat_terreno_matorral') or low.startswith('mat_mont_bosque'):
        return 'matorral' if low.startswith('mat_terreno') else 'bosque'
    if low.startswith(('mat_terreno_seca', 'mat_terreno_hierba_seca', 'mat_arcen')):
        return 'seca'
    if low.startswith('mat_terreno'):
        return 'terreno'
    if low.startswith('mat_agua'):
        return 'agua'
    if any(k in low for k in CLAVES_CALIZA) and not any(k in low for k in NO_CALIZA):
        return 'caliza'
    if n.startswith(PREFIJOS_FACHADA) and not any(e in low for e in EXCLUIR_FACHADA):
        return 'estuco'
    return None


def cargar_imagen(fichero, no_color=False):
    """Imagen con ruta ABSOLUTA y colorspace correcto; reutiliza si ya existe.

    Un datablock de imagen tiene UN colorspace, asi que los usos de bump
    cargan su propia copia Non-Color.
    """
    ruta = os.path.join(DIR_TEX, fichero)
    espacio = 'Non-Color' if no_color else 'sRGB'
    for img in bpy.data.images:
        if (os.path.normcase(bpy.path.abspath(img.filepath)) == os.path.normcase(ruta)
                and img.colorspace_settings.name == espacio):
            return img
    img = bpy.data.images.load(ruta, check_existing=False)
    img.filepath = ruta  # absoluta, sin '//'
    img.colorspace_settings.name = espacio
    if no_color:
        img.name = os.path.splitext(fichero)[0] + '_nc'
    return img


def buscar_principled(nt):
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


def nuevo_mix_color(nodes, blend='MULTIPLY', clamp=True):
    """Nodo de mezcla de color; devuelve (nodo, fac, a, b, out)."""
    try:
        n = nodes.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.blend_type = blend
        n.clamp_result = clamp
        ins = [s for s in n.inputs if s.type == 'RGBA']
        outs = [s for s in n.outputs if s.type == 'RGBA']
        return n, n.inputs[0], ins[0], ins[1], outs[0]
    except RuntimeError:
        n = nodes.new('ShaderNodeMixRGB')  # fallback API antigua
        n.blend_type = blend
        n.use_clamp = clamp
        return n, n.inputs['Fac'], n.inputs['Color1'], n.inputs['Color2'], n.outputs['Color']


def crear_cadena_textura(nt, cfg, loc, no_color=False, mapping=None):
    """TexCoord(Object)->Mapping(escala)->Image Texture. Devuelve (tex, mapping)."""
    nodes, links = nt.nodes, nt.links
    x, y = loc
    if mapping is None:
        tco = nodes.new('ShaderNodeTexCoord')
        tco.name = 'TEX_coord'
        tco.location = (x - 400, y)
        mapping = nodes.new('ShaderNodeMapping')
        mapping.name = 'TEX_mapping'
        mapping.location = (x - 200, y)
        s = cfg['escala']
        mapping.inputs['Scale'].default_value = (s, s, s)
        links.new(tco.outputs['Object'], mapping.inputs['Vector'])
    tex = nodes.new('ShaderNodeTexImage')
    tex.name = 'TEX_imagen' + ('_nc' if no_color else '')
    tex.location = (x, y)
    tex.image = cargar_imagen(cfg['tex'], no_color=no_color)
    tex.projection = cfg['proy']
    if cfg['proy'] == 'BOX':
        tex.projection_blend = 0.3
    tex.extension = 'REPEAT'
    tex.interpolation = 'Linear'
    links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
    return tex, mapping


def multiplicar_base_color(nt, principled, salida_tex, factor, ganancia, loc):
    """Inserta (BaseColor previo) * (tex*ganancia) con el factor dado."""
    nodes, links = nt.nodes, nt.links
    x, y = loc

    gan, _f, g_a, g_b, g_out = nuevo_mix_color(nodes, clamp=False)
    gan.name = 'TEX_ganancia'
    gan.location = (x, y)
    _f.default_value = 1.0
    g_b.default_value = (ganancia, ganancia, ganancia, 1.0)
    links.new(salida_tex, g_a)

    ent_base = principled.inputs['Base Color']
    previo = ent_base.links[0].from_socket if ent_base.links else None
    color_previo = tuple(ent_base.default_value[:])

    mix, s_fac, s_a, s_b, s_out = nuevo_mix_color(nodes, clamp=True)
    mix.name = 'TEX_multiplicar'
    mix.location = (x + 220, y + 60)
    s_fac.default_value = factor
    s_a.default_value = color_previo
    if previo is not None:
        links.new(previo, s_a)
    links.new(g_out, s_b)
    links.new(s_out, ent_base)
    return mix


def anadir_bump(nt, principled, salida_altura, strength, distance, loc):
    """Bump nuevo al final de la cadena de Normal (encadena si ya habia)."""
    nodes, links = nt.nodes, nt.links
    bump = nodes.new('ShaderNodeBump')
    bump.name = 'TEX_bump'
    bump.location = loc
    bump.inputs['Strength'].default_value = strength
    if 'Distance' in bump.inputs:
        bump.inputs['Distance'].default_value = distance
    links.new(salida_altura, bump.inputs['Height'])
    ent_normal = principled.inputs['Normal']
    if ent_normal.links:
        previo = ent_normal.links[0].from_socket
        links.new(previo, bump.inputs['Normal'])  # encadena bump existente
    links.new(bump.outputs['Normal'], ent_normal)
    return bump


def marcar(nt, loc):
    marca = nt.nodes.new('NodeFrame')
    marca.name = 'TEXTURIZADO'
    marca.label = 'TEXTURIZADO'
    marca.location = loc


def aplicar_generico(mat, cfg):
    """Multiply de color (+bump opcional) para asfalto/tierra/teja/piedra/estuco/seca/matorral/cesped."""
    nt = mat.node_tree
    principled = buscar_principled(nt)
    if principled is None:
        return False
    px, py = principled.location
    tex, mapping = crear_cadena_textura(nt, cfg, (px - 700, py + 150))
    multiplicar_base_color(nt, principled, tex.outputs['Color'],
                           cfg['factor'], ganancia_de(cfg), (px - 380, py + 150))
    if cfg['bump']:
        tex_nc, _ = crear_cadena_textura(nt, cfg, (px - 700, py - 450),
                                         no_color=True, mapping=mapping)
        anadir_bump(nt, principled, tex_nc.outputs['Color'],
                    cfg['bump'][0], cfg['bump'][1], (px - 380, py - 450))
    marcar(nt, (px - 900, py + 420))
    return True


def aplicar_terreno(mat, cfg):
    """Tile del terreno (hierba_seca_d, BOX) multiplicado sobre el resultado del ColorRamp existente,
    solo donde 0.5 < z < 150-168 y el terreno es llano, con factor cfg['factor'] (no rompe la rampa).
    Si el propietario 'mascara' ya ha puesto su material por texel, llega con TEXTURIZADO y no entra aqui."""
    nt = mat.node_tree
    principled = buscar_principled(nt)
    if principled is None:
        return False
    ent_base = principled.inputs['Base Color']
    if not ent_base.links:
        return False
    previo = ent_base.links[0].from_socket  # salida del ColorRamp actual
    nodes, links = nt.nodes, nt.links
    px, py = principled.location

    tex, _ = crear_cadena_textura(nt, cfg, (px - 900, py + 300))

    gan, _f, g_a, g_b, g_out = nuevo_mix_color(nodes, clamp=False)
    gan.name = 'TEX_ganancia'
    gan.location = (px - 620, py + 300)
    _f.default_value = 1.0
    g_b.default_value = (ganancia_de(cfg),) * 3 + (1.0,)
    links.new(tex.outputs['Color'], g_a)

    # mascara de altura: sube en z=0.5..3, baja en z=150..168
    geo = nodes.new('ShaderNodeNewGeometry')
    geo.name = 'TEX_geometria'
    geo.location = (px - 1150, py + 620)
    sep = nodes.new('ShaderNodeSeparateXYZ')
    sep.name = 'TEX_sep_z'
    sep.location = (px - 970, py + 620)
    links.new(geo.outputs['Position'], sep.inputs['Vector'])

    sube = nodes.new('ShaderNodeMapRange')
    sube.name = 'TEX_altura_min'
    sube.location = (px - 790, py + 700)
    sube.clamp = True
    sube.interpolation_type = 'SMOOTHSTEP'
    sube.inputs['From Min'].default_value = 0.5
    sube.inputs['From Max'].default_value = 3.0
    links.new(sep.outputs['Z'], sube.inputs['Value'])

    baja = nodes.new('ShaderNodeMapRange')
    baja.name = 'TEX_altura_max'
    baja.location = (px - 790, py + 480)
    baja.clamp = True
    baja.interpolation_type = 'SMOOTHSTEP'
    baja.inputs['From Min'].default_value = 150.0
    baja.inputs['From Max'].default_value = 168.0
    baja.inputs['To Min'].default_value = 1.0
    baja.inputs['To Max'].default_value = 0.0
    links.new(sep.outputs['Z'], baja.inputs['Value'])

    banda = nodes.new('ShaderNodeMath')
    banda.name = 'TEX_banda'
    banda.operation = 'MULTIPLY'
    banda.location = (px - 600, py + 620)
    links.new(sube.outputs['Result'], banda.inputs[0])
    links.new(baja.outputs['Result'], banda.inputs[1])

    # ... y solo donde el terreno es LLANO: en los taludes manda la roca. Con proyeccion BOX el tile
    # ya no se estira en las laderas, asi que la banda llega mas abajo (nz 0.45-0.65; antes 0.60-0.78)
    sepn = nodes.new('ShaderNodeSeparateXYZ')
    sepn.name = 'TEX_sep_normal'
    sepn.location = (px - 970, py + 900)
    links.new(geo.outputs['Normal'], sepn.inputs['Vector'])
    llano = nodes.new('ShaderNodeMapRange')
    llano.name = 'TEX_llano'
    llano.location = (px - 790, py + 900)
    llano.clamp = True
    llano.interpolation_type = 'SMOOTHSTEP'
    llano.inputs['From Min'].default_value = 0.45
    llano.inputs['From Max'].default_value = 0.65
    links.new(sepn.outputs['Z'], llano.inputs['Value'])
    banda2 = nodes.new('ShaderNodeMath')
    banda2.name = 'TEX_banda_llano'
    banda2.operation = 'MULTIPLY'
    banda2.location = (px - 520, py + 760)
    links.new(banda.outputs['Value'], banda2.inputs[0])
    links.new(llano.outputs['Result'], banda2.inputs[1])

    fac = nodes.new('ShaderNodeMath')
    fac.name = 'TEX_factor'
    fac.operation = 'MULTIPLY'
    fac.location = (px - 430, py + 620)
    fac.inputs[1].default_value = cfg['factor']
    links.new(banda2.outputs['Value'], fac.inputs[0])

    mix, s_fac, s_a, s_b, s_out = nuevo_mix_color(nodes, clamp=True)
    mix.name = 'TEX_multiplicar'
    mix.location = (px - 340, py + 300)
    links.new(fac.outputs['Value'], s_fac)
    links.new(previo, s_a)   # resultado final de la rampa, intacto
    links.new(g_out, s_b)
    links.new(s_out, ent_base)

    marcar(nt, (px - 1150, py + 860))
    return True


def aplicar_agua(mat, cfg):
    """agua_h (Non-Color) como bump de olas a gran escala."""
    nt = mat.node_tree
    principled = buscar_principled(nt)
    if principled is None:
        return False
    px, py = principled.location
    tex_nc, _ = crear_cadena_textura(nt, cfg, (px - 700, py - 500), no_color=True)
    anadir_bump(nt, principled, tex_nc.outputs['Color'],
                cfg['bump'][0], cfg['bump'][1], (px - 380, py - 500))
    marcar(nt, (px - 900, py - 200))
    return True


def aplicar_roca(mat, cfg=None):
    """Respaldo de la familia 'caliza' sin materiales_roca: caliza_d.png (BOX, 3 m) multiplicada + manchas
    de ~20 m de +-10 % (F1: antes +-50 %, el 'velo de bruma' de 13/19/45) + grano fino como bump."""
    nt = mat.node_tree
    principled = buscar_principled(nt)
    if principled is None:
        return False
    nodes, links = nt.nodes, nt.links
    px, py = principled.location
    cfg = cfg or FAMILIAS['caliza']
    tex, mapping = crear_cadena_textura(nt, cfg, (px - 700, py + 150))
    multiplicar_base_color(nt, principled, tex.outputs['Color'],
                           cfg['factor'], ganancia_de(cfg), (px - 380, py + 150))
    tco = nodes.new('ShaderNodeTexCoord')
    tco.name = 'TEX_coord_roca'
    tco.location = (px - 1000, py + 500)
    n1 = nodes.new('ShaderNodeTexNoise')
    n1.name = 'TEX_ruido_color'
    n1.location = (px - 800, py + 600)
    n1.inputs['Scale'].default_value = 0.045   # manchas de ~20 m
    n1.inputs['Detail'].default_value = 6.0
    n1.inputs['Roughness'].default_value = 0.6
    links.new(tco.outputs['Object'], n1.inputs['Vector'])
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.name = 'TEX_rampa'
    ramp.location = (px - 600, py + 600)
    e = ramp.color_ramp.elements
    e[0].position = 0.32
    e[0].color = (0.90, 0.90, 0.90, 1)         # +-10 %: ya no es bruma
    e[1].position = 0.70
    e[1].color = (1.10, 1.09, 1.08, 1)
    links.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    # el multiply de las manchas va DESPUES del de la imagen (sobre el Base Color ya texturizado)
    gan2, _f2, g2_a, g2_b, g2_out = nuevo_mix_color(nodes, clamp=False)
    gan2.name = 'TEX_manchas'
    gan2.location = (px - 380, py + 600)
    _f2.default_value = 1.0
    ent_base = principled.inputs['Base Color']
    previo = ent_base.links[0].from_socket
    links.new(previo, g2_a)
    links.new(ramp.outputs['Color'], g2_b)
    links.new(g2_out, ent_base)
    n2 = nodes.new('ShaderNodeTexNoise')
    n2.name = 'TEX_ruido_bump'
    n2.location = (px - 800, py - 350)
    n2.inputs['Scale'].default_value = 0.35    # grano de ~3 m
    n2.inputs['Detail'].default_value = 10.0
    n2.inputs['Roughness'].default_value = 0.7
    links.new(tco.outputs['Object'], n2.inputs['Vector'])
    anadir_bump(nt, principled, n2.outputs['Fac'], 0.35, 0.35, (px - 380, py - 350))
    marcar(nt, (px - 1100, py + 420))
    return True


def _materiales_roca():
    """Modulo assets/materiales_roca (grupo NG_caliza_estratos) o None si no se puede importar."""
    try:
        import importlib.util
        ruta = os.path.join(AQUI, 'assets', 'materiales_roca.py')
        if 'materiales_roca' in sys.modules:
            return sys.modules['materiales_roca']
        spec = importlib.util.spec_from_file_location('materiales_roca', ruta)
        mod = importlib.util.module_from_spec(spec)
        sys.modules['materiales_roca'] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:  # noqa
        print('AVISO: assets/materiales_roca.py no disponible (%s): familia caliza con caliza_d.png + manchas' % e)
        return None


def aplicar_caliza(mat, cfg, rehacer=False):
    """Familia caliza: grupo NG_caliza_estratos x caliza_d.png (materiales_roca.aplicar_a); respaldo aplicar_roca.
    rehacer=True (--rehacer caliza): un material que ya lleva el grupo se re-aplica con el tile/factor de cfg
    (materiales_roca.reaplicar; nunca el terreno)."""
    mr = _materiales_roca()
    if mr is not None:
        if mr.tiene_caliza(mat):
            if rehacer and hasattr(mr, 'reaplicar') and not mr.es_terreno(mat):
                mr.reaplicar(mat, imagen=cfg['tex'], tile_m=1.0 / cfg['escala'], factor=cfg['factor'])
                return True
            return False
        mr.aplicar_a(mat, imagen=cfg['tex'], tile_m=1.0 / cfg['escala'], factor=cfg['factor'])
        return True
    return aplicar_roca(mat, cfg)


# familias cuyo BSDF debe ser MATE (sin Fresnel del cielo): terreno y rocas. F1 r3 (director r2 n.5/6): con el
# Specular IOR Level por defecto (0.5) las lomas vistas rasantes desde el coche (n.v 0.07-0.3) reflejaban el cielo
# (0.70,0.84,0.98) = velo gris-cian y caliza desaturada (51 pared S 0.12); ksPerPixel en AC no tiene Fresnel.
FAMILIAS_MATE = ('terreno', 'hierba', 'seca', 'matorral', 'cesped', 'bosque', 'tierra', 'caliza', 'caliza_grande')
RUGOSIDAD_MATE = {'terreno': 1.0, 'hierba': 1.0, 'seca': 1.0, 'matorral': 1.0, 'cesped': 0.95, 'bosque': 1.0, 'tierra': 1.0,
                  'caliza': 1.0, 'caliza_grande': 1.0}
# McLaren (bloque 2.1 / director r2 n.6): el cristal pulido deja de ser plastico brillante (0.26 -> 0.5); es un ajuste de
# material (el kit montana_mclaren es de otro propietario: PARCHES_F1_materiales.md 2.a sigue pendiente alli)
AJUSTES_BSDF = {'MAT_MCOCHE_cristal_pulido': {'Roughness': 0.5, 'Specular IOR Level': 0.3}}


def rugosidad_mate(mats=None):
    """Pasada idempotente: Roughness/Specular IOR Level de las familias FAMILIAS_MATE (y de todo lo que lleve el grupo
    NG_caliza_estratos, terreno incluido) + AJUSTES_BSDF por nombre. Solo entradas sin enlazar. Devuelve [(nombre, que)]."""
    mr = _materiales_roca()
    tocados = []
    for mat in (mats if mats is not None else bpy.data.materials):
        nt = mat.node_tree
        if not nt:
            continue
        bsdf = buscar_principled(nt)
        if bsdf is None:
            continue
        fam = familia_de(mat)
        con_grupo = mr is not None and hasattr(mr, 'NOMBRE_GRUPO') and any(
            n.type == 'GROUP' and n.node_tree and n.node_tree.name == mr.NOMBRE_GRUPO for n in nt.nodes)
        valores = {}
        if fam in FAMILIAS_MATE or con_grupo:
            valores = {'Roughness': RUGOSIDAD_MATE.get(fam, 1.0), 'Specular IOR Level': 0.0}
        valores.update(AJUSTES_BSDF.get(mat.name, {}))
        cambios = []
        for nombre_s, val in valores.items():
            s = bsdf.inputs.get(nombre_s)
            if s is None or s.is_linked:
                continue
            if abs(float(s.default_value) - float(val)) > 1e-6:
                s.default_value = float(val)
                cambios.append('%s %.2f' % (nombre_s, val))
        if cambios:
            tocados.append((mat.name, ', '.join(cambios)))
    return tocados


def destexturizar(mat):
    """Quita la pasada previa (nodos TEX_* y el marcador) devolviendo Base Color y Normal a lo que habia.
    No toca el grupo de caliza (CALIZA_ESTRATOS) ni los nodos ROCA_*/Math.002 del terreno. Devuelve True si quito algo."""
    nt = mat.node_tree
    if not nt or not nt.nodes.get('TEXTURIZADO'):
        return False
    nodes, links = nt.nodes, nt.links
    principled = buscar_principled(nt)
    if principled is not None:
        mul = nodes.get('TEX_multiplicar')
        ent_base = principled.inputs['Base Color']
        if mul is not None:
            s_a = next((s for s in mul.inputs if s.type == 'RGBA'), None)
            # lo que entraba por A era el Base Color original (enlace o color plano)
            if s_a is not None and s_a.links:
                origen = s_a.links[0].from_socket
                if origen.node.name.startswith('TEX_') or origen.node.name == 'CAL_grupo':
                    origen = None
                for l in list(ent_base.links):
                    links.remove(l)
                if origen is not None:
                    links.new(origen, ent_base)
            elif s_a is not None:
                for l in list(ent_base.links):
                    links.remove(l)
                ent_base.default_value = s_a.default_value
        ent_n = principled.inputs['Normal']
        bump = nodes.get('TEX_bump')
        if bump is not None:
            prev = bump.inputs['Normal'].links[0].from_socket if bump.inputs['Normal'].links else None
            for l in list(ent_n.links):
                links.remove(l)
            if prev is not None and not prev.node.name.startswith('TEX_'):
                links.new(prev, ent_n)
    for n in list(nodes):
        if n.name.startswith('TEX_') or n.name == 'TEXTURIZADO':
            nodes.remove(n)
    return True


def aplicar_material(mat, rehacer_caliza=False):
    """Devuelve (familia, True si lo toco)."""
    fam = familia_de(mat)
    if fam is None:
        return None, False
    if not mat.node_tree:
        return fam, False
    if fam in ('caliza', 'caliza_grande') and rehacer_caliza:
        return fam, aplicar_caliza(mat, FAMILIAS[fam], rehacer=True)
    if mat.node_tree.nodes.get('TEXTURIZADO'):
        return fam, False  # idempotencia
    if fam == 'terreno':
        return fam, aplicar_terreno(mat, FAMILIAS['hierba'])
    if fam == 'agua':
        return fam, aplicar_agua(mat, FAMILIAS['agua'])
    if fam in ('caliza', 'caliza_grande'):
        return fam, aplicar_caliza(mat, FAMILIAS[fam])
    return fam, aplicar_generico(mat, FAMILIAS[fam])


def actualizar_caliza():
    """F1 r2: si el .blend trae un NG_caliza_estratos de una version anterior (sin tono_pared), materiales_roca lo
    reconstruye en sitio (los enlaces de MAT_terreno/kits se conservan). Devuelve True si lo ha rehecho."""
    mr = _materiales_roca()
    if mr is None or not hasattr(mr, 'actualizar_grupo'):
        return False
    try:
        return bool(mr.actualizar_grupo())
    except Exception as e:  # noqa
        print('AVISO: materiales_roca.actualizar_grupo fallo (%s)' % e)
        return False


def aplicar_blend(ruta, rehacer=None):
    """rehacer: None (idempotente), 'todas' o lista de familias cuya pasada previa se quita antes de texturizar."""
    bpy.ops.wm.open_mainfile(filepath=ruta)
    caliza_rehecha = actualizar_caliza()
    tocados, saltados, rehechos = [], 0, 0
    for mat in sorted(bpy.data.materials, key=lambda m: m.name):
        fam = familia_de(mat)
        if fam is None:
            continue
        rehacer_esta = bool(rehacer and (rehacer == 'todas' or fam in rehacer))
        rehacer_caliza = False
        if rehacer_esta:
            mr = _materiales_roca()
            if mr is not None and mr.tiene_caliza(mat):
                rehacer_caliza = fam in ('caliza', 'caliza_grande')   # v3: reaplicar con el tile/factor de la familia
            elif destexturizar(mat):
                rehechos += 1
        fam, toco = aplicar_material(mat, rehacer_caliza=rehacer_caliza)
        if toco:
            tocados.append((mat.name, fam))
            if rehacer_caliza:
                rehechos += 1
        else:
            saltados += 1
    mates = rugosidad_mate()           # v3: terreno y rocas sin Fresnel del cielo; cristal pulido del McLaren 0.5
    if tocados or rehechos or caliza_rehecha or mates:
        bpy.ops.wm.save_as_mainfile(filepath=ruta)
    print('APLICAR_TEXTURAS: tocados=%d saltados=%d rehechos=%d caliza_v%s mates=%d' % (
        len(tocados), saltados, rehechos, 'actualizada' if caliza_rehecha else 'al_dia', len(mates)))
    for nombre, fam in tocados:
        print('  + %-38s -> %s' % (nombre, fam))
    for nombre, que in mates:
        print('  mate %-35s %s' % (nombre, que))
    print('Guardado:', ruta)
    return tocados


if __name__ == '__main__':
    argv = sys.argv
    ruta = BLEND_REAL
    rehacer = None
    if '--' in argv:
        extra = argv[argv.index('--') + 1:]
        pos = [a for a in extra if not a.startswith('--')]
        if '--rehacer' in extra:
            rehacer = 'todas'
            i = extra.index('--rehacer')
            # lista de familias opcional justo despues (no es una ruta .blend ni otra opcion)
            if i + 1 < len(extra) and not extra[i + 1].startswith('--') and not extra[i + 1].lower().endswith('.blend'):
                rehacer = [f.strip() for f in extra[i + 1].split(',') if f.strip()]
                pos = [a for a in pos if a != extra[i + 1]]
        if pos:
            ruta = pos[0]
    aplicar_blend(ruta, rehacer)
