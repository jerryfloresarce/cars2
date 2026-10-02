"""Pase de texturizado tileable de Porto Corsa (Cars 2).

Abre porto_corsa.blend, aplica las texturas tileables de 03_blender/texturas/
a los materiales por familias y guarda el blend en la MISMA ruta.

Idempotente: cada arbol de nodos tocado se marca con un nodo name='TEXTURIZADO'
y se salta en pasadas posteriores.

Mapeado por coordenadas de OBJETO (las mallas no tienen UVs):
Texture Coordinate->Object + Mapping con escala por familia. Los suelos usan
proyeccion plana (superior implicita); fachadas/tejados/piedra usan proyeccion
BOX para no estirar en las caras verticales.

Familias:
  MAT_asfalto*                       -> asfalto_d multiplicada + bump suave (tile 8 m)
  MAT_tierra                         -> tierra_d multiplicada (tile 6 m)
  *teja* / *tejado* / *roof*         -> teja_d multiplicada + bump (tile 2 m)
  *piedra* / *stone* / *MUROC* /
  MAT_PUENTES*                       -> piedra_d multiplicada + bump (tile 3 m)
  MAT_CASAS_/MAT_CASINO_/MAT_CIVICO_/
  MAT_HOTEL_ (sin vidrio/cristal/
  persiana/luz/emis)                 -> estuco_d multiplicada, factor moderado
  MAT_terreno                        -> hierba_d multiplicada solo entre z=0.5 y 80,
                                        sobre el resultado de su ColorRamp (factor 0.5)
  MAT_agua                           -> agua_h como bump de olas (tile 40 m)

Cada textura de color va con ganancia 1/media_lineal para que el multiply
aporte variacion SIN oscurecer ni desaturar el color base (estilo Cars 2).
Image Texture siempre con ruta ABSOLUTA; color en sRGB, alturas/bump Non-Color.

Ejecutar:
  blender --background --python aplicar_texturas.py             (blend real)
  blender --background --python aplicar_texturas.py -- <ruta>   (otro blend)
"""
import os
import sys

import bpy

BLEND_REAL = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\porto_corsa.blend"
DIR_TEX = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\texturas"

# ganancia = 1/media_lineal de cada png (medida), para conservar el brillo medio
FAMILIAS = {
    # tex, tile en m (escala mapping = 1/tile), factor multiply, ganancia,
    # proyeccion, bump=(strength, distance) o None
    'asfalto': dict(tex='asfalto_d.png', escala=1.0 / 8, factor=1.0,
                    ganancia=2.19, proy='FLAT', bump=(0.3, 0.015)),
    'tierra':  dict(tex='tierra_d.png', escala=1.0 / 6, factor=0.7,
                    ganancia=1.62, proy='FLAT', bump=None),
    'teja':    dict(tex='teja_d.png', escala=1.0 / 2, factor=0.8,
                    ganancia=2.39, proy='BOX', bump=(0.35, 0.02)),
    'piedra':  dict(tex='piedra_d.png', escala=1.0 / 3, factor=0.75,
                    ganancia=1.35, proy='BOX', bump=(0.3, 0.02)),
    'piedra_suave': dict(tex='piedra_d.png', escala=1.0 / 3, factor=0.28,
                         ganancia=1.35, proy='BOX', bump=None),   # viaducto: ya trae hiladas propias
    'estuco':  dict(tex='estuco_d.png', escala=1.0 / 4, factor=0.72,
                    ganancia=1.06, proy='BOX', bump=None),
    'hierba':  dict(tex='hierba_d.png', escala=1.0 / 7, factor=0.85,
                    ganancia=1.85, proy='FLAT', bump=None),
    'bosque':  dict(tex='hierba_d.png', escala=1.0 / 7, factor=0.8,
                    ganancia=1.85, proy='BOX', bump=None),
    'agua':    dict(tex='agua_h.png', escala=1.0 / 40, factor=0.0,
                    ganancia=1.0, proy='FLAT', bump=(1.0, 0.4)),
}

EXCLUIR_FACHADA = ('vidrio', 'cristal', 'persiana', 'luz', 'emis')
PREFIJOS_FACHADA = ('MAT_CASAS_', 'MAT_CASINO_', 'MAT_CIVICO_', 'MAT_HOTEL_')
CLAVES_TEJA = ('teja', 'tejado', 'roof')
CLAVES_PIEDRA = ('piedra', 'stone', 'muroc')


def familia_de(mat):
    """Clasifica el material; None si no se texturiza."""
    n = mat.name
    low = n.lower()
    if low.startswith('mat_asfalto'):
        return 'asfalto'
    if low.startswith('mat_tierra'):
        return 'tierra'
    if any(k in low for k in CLAVES_TEJA):
        return 'teja'
    if low.startswith('mat_puentes'):
        return 'piedra_suave'
    if any(k in low for k in CLAVES_PIEDRA):
        return 'piedra'
    if low.startswith('mat_mont_roca'):
        return 'roca'
    if low.startswith(('mat_penon_caliza', 'mat_penon_meseta', 'mat_ppueblo_roca', 'mat_ppueblo_repisa', 'mat_mrueda_caliza')):
        return 'roca'
    if low.startswith('mat_mont_bosque'):
        return 'bosque'
    if low.startswith('mat_terreno'):
        return 'terreno'
    if low.startswith('mat_arcen'):
        return 'hierba'
    if low.startswith('mat_agua'):
        return 'agua'
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
    """Multiply de color (+bump opcional) para asfalto/tierra/teja/piedra/estuco."""
    nt = mat.node_tree
    principled = buscar_principled(nt)
    if principled is None:
        return False
    px, py = principled.location
    tex, mapping = crear_cadena_textura(nt, cfg, (px - 700, py + 150))
    multiplicar_base_color(nt, principled, tex.outputs['Color'],
                           cfg['factor'], cfg['ganancia'], (px - 380, py + 150))
    if cfg['bump']:
        tex_nc, _ = crear_cadena_textura(nt, cfg, (px - 700, py - 450),
                                         no_color=True, mapping=mapping)
        anadir_bump(nt, principled, tex_nc.outputs['Color'],
                    cfg['bump'][0], cfg['bump'][1], (px - 380, py - 450))
    marcar(nt, (px - 900, py + 420))
    return True


def aplicar_terreno(mat, cfg):
    """hierba_d multiplicada sobre el resultado del ColorRamp existente,
    solo donde 0.5 < z < 80, con factor 0.5 (no rompe la rampa)."""
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
    g_b.default_value = (cfg['ganancia'],) * 3 + (1.0,)
    links.new(tex.outputs['Color'], g_a)

    # mascara de altura: sube en z=0.5..3, baja en z=72..80
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

    # ... y solo donde el terreno es LLANO: en los taludes manda la roca
    sepn = nodes.new('ShaderNodeSeparateXYZ')
    sepn.name = 'TEX_sep_normal'
    sepn.location = (px - 970, py + 900)
    links.new(geo.outputs['Normal'], sepn.inputs['Vector'])
    llano = nodes.new('ShaderNodeMapRange')
    llano.name = 'TEX_llano'
    llano.location = (px - 790, py + 900)
    llano.clamp = True
    llano.interpolation_type = 'SMOOTHSTEP'
    llano.inputs['From Min'].default_value = 0.60
    llano.inputs['From Max'].default_value = 0.78
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
    fac.inputs[1].default_value = cfg['factor']  # 0.5
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


def aplicar_roca(mat):
    """Caliza procedural (sin ladrillos): ruido grande de color + ruido fino
    como bump, en coordenadas de objeto."""
    nt = mat.node_tree
    principled = buscar_principled(nt)
    if principled is None:
        return False
    nodes, links = nt.nodes, nt.links
    px, py = principled.location
    tco = nodes.new('ShaderNodeTexCoord')
    tco.name = 'TEX_coord'
    tco.location = (px - 1000, py + 100)
    n1 = nodes.new('ShaderNodeTexNoise')
    n1.name = 'TEX_ruido_color'
    n1.location = (px - 800, py + 200)
    n1.inputs['Scale'].default_value = 0.045   # manchas de ~20 m
    n1.inputs['Detail'].default_value = 8.0
    n1.inputs['Roughness'].default_value = 0.62
    links.new(tco.outputs['Object'], n1.inputs['Vector'])
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.name = 'TEX_rampa'
    ramp.location = (px - 600, py + 200)
    e = ramp.color_ramp.elements
    e[0].position = 0.32
    e[0].color = (0.45, 0.44, 0.42, 1)
    e[1].position = 0.70
    e[1].color = (1.0, 0.98, 0.94, 1)
    links.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    multiplicar_base_color(nt, principled, ramp.outputs['Color'], 0.9, 1.15,
                           (px - 380, py + 150))
    n2 = nodes.new('ShaderNodeTexNoise')
    n2.name = 'TEX_ruido_bump'
    n2.location = (px - 800, py - 350)
    n2.inputs['Scale'].default_value = 0.35    # grano de ~3 m
    n2.inputs['Detail'].default_value = 10.0
    n2.inputs['Roughness'].default_value = 0.7
    links.new(tco.outputs['Object'], n2.inputs['Vector'])
    anadir_bump(nt, principled, n2.outputs['Fac'], 0.55, 0.35, (px - 380, py - 350))
    marcar(nt, (px - 1100, py + 420))
    return True


def aplicar_material(mat):
    """Devuelve (familia, True si lo toco)."""
    fam = familia_de(mat)
    if fam is None:
        return None, False
    if not mat.node_tree:
        return fam, False
    if mat.node_tree.nodes.get('TEXTURIZADO'):
        return fam, False  # idempotencia
    if fam == 'terreno':
        return fam, aplicar_terreno(mat, FAMILIAS['hierba'])
    if fam == 'agua':
        return fam, aplicar_agua(mat, FAMILIAS['agua'])
    if fam == 'roca':
        return fam, aplicar_roca(mat)
    return fam, aplicar_generico(mat, FAMILIAS[fam])


def aplicar_blend(ruta):
    bpy.ops.wm.open_mainfile(filepath=ruta)
    tocados, saltados = [], 0
    for mat in sorted(bpy.data.materials, key=lambda m: m.name):
        fam, toco = aplicar_material(mat)
        if fam is None:
            continue
        if toco:
            tocados.append((mat.name, fam))
        else:
            saltados += 1
    if tocados:
        bpy.ops.wm.save_as_mainfile(filepath=ruta)
    print('APLICAR_TEXTURAS: tocados=%d saltados=%d' % (len(tocados), saltados))
    for nombre, fam in tocados:
        print('  + %-38s -> %s' % (nombre, fam))
    print('Guardado:', ruta)
    return tocados


if __name__ == '__main__':
    argv = sys.argv
    ruta = BLEND_REAL
    if '--' in argv:
        extra = argv[argv.index('--') + 1:]
        if extra:
            ruta = extra[0]
    aplicar_blend(ruta)
