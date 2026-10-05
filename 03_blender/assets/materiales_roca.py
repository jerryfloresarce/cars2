# -*- coding: utf-8 -*-
"""materiales_roca.py - material de CALIZA CALIDA CON ESTRATOS compartido por todas las rocas (bloque 2.1 del plan).

Fase visual F1, propietario 'materiales'. Lo usan roca_lazo._mat, roca_casino._mat, montana_coche_v2._mat_piedra
(McLaren), aplicar_texturas (familia 'caliza') y, por parche del propietario 'mascara', construir_pista._roca_terreno.

  ng_caliza_estratos(nombre='NG_caliza_estratos') -> bpy.types.ShaderNodeTree (reutiliza si ya existe; si el grupo
      guardado es de una version anterior (ng['cal_version'] < CAL_VERSION) lo RECONSTRUYE en sitio sin tocar los
      enlaces de los materiales que lo usan: solo cambian los nodos de dentro y se anaden las entradas nuevas).
      Entradas: tono_base (Color), tono_junta (Color), periodo_m (3.0), bump (0.45), mojado (1.0), fase (0.0),
                contraste_bancos (0.12), grano (1.0), manchas (1.0),
                tono_pared (Color, v2) y pared (1.0, v2): TRES TONOS de la paleta v2 (director F1 r1, problema 7):
                  repisas y superficies horizontales = tono_base (caliza_ocre, la clara); PAREDES (nz <= 0.45, > 63
                  grados) = tono_pared (caliza_gris_calido, la media; nunca mas clara que tono_base: min por canal);
                  juntas y mojado = tono_junta (caliza_sombra, la oscura). pared = 0 recupera el comportamiento v1.
      Salidas:  Color, Normal, AO
      Todo en coordenadas de MUNDO (Geometry.Position): TUNEL_acantilado y PENON_* no estan en el origen y asi el
      patron empalma con el terreno. Estratos por z (Wave BANDS Z, periodo periodo_m, distorsion) con la JUNTA
      hundida (bump) y oscura (tono_junta) y una cornisa algo mas clara encima; bancos de 8-14 m con tono alterno
      (+-contraste_bancos, fase por ruido 2D de ~70 m); grano de 0.3-1 m; manchas de ~20 m de +-10 % (NO +-50 %: es lo que
      se leia como bruma en 13/19/45); mojado (mas oscuro) bajo z = 1 con mojado = 1.
  actualizar_grupo() -> True si habia un grupo de version anterior y se ha reconstruido (lo llama aplicar_texturas).
  crear_nodos(nt, loc=(0,0), **kw) -> (nodo_grupo, salida Color, salida Normal, salida AO)
      Pone el grupo en un arbol existente SIN tocar nada mas: es lo que enchufa construir_pista._roca_terreno en la
      rama de roca (mixr.inputs[7]) conservando el nodo 'Math.002'/'ROCA_mascara'.
  aplicar_a(material, tono_base=None, tono_junta=None, imagen='caliza_d.png', tile_m=6.0, factor=0.5, **kw) -> nodo_grupo
      Material de un kit (Principled plano o con rampa): Base Color <- grupo.Color x caliza_d.png (TEX_imagen BOX,
      TEX_mapping 1/tile_m, TEX_ganancia, TEX_multiplicar: el contrato de 04_export/kn5_writer_opt.analizar_material,
      que exporta HOY el tile tintado por diffuse_color); Normal <- grupo.Normal; diffuse_color = MEDIA lineal del
      material (lo que lee el writer; con frac_pared = 0.5 por defecto: mitad repisa, mitad pared). NO toca
      'ROCA_mascara'/'Math.002' si existen (terreno). Idempotente: marcador NodeFrame 'CALIZA_ESTRATOS' (+ 'TEXTURIZADO'
      para que aplicar_texturas no vuelva a texturizar). Custom props ac_shader/ac_props/ac_samplers/ac_tex_max/
      ac_alpha_test/ac_raw con valor = comportamiento actual del writer.
  tiene_caliza(material) -> bool
  media_lineal(tono_base, contraste_bancos, mojado, tono_junta, tono_pared, frac_pared) -> (r, g, b): la media que se
      escribe en diffuse_color.
  color_roca_terreno_ac(ao=None) -> (r, g, b): media lineal de una PARED de caliza (frac_pared = 1) x AO media del terreno
      (terreno_mask_stats.json, 0.757): el valor que deberia tomar 04_export/color_ac.ROCA_COLOR (P1, [W]) para que
      MAT_terreno_roca en AC sea la caliza media de la paleta con su sombra media, y no un literal.
  roca_caras_mascara(ob, umbral=0.5, nz_extra=0.35, ruta_mask=None) -> bool por poligono (solo caras con MAT_terreno):
      canal A de texturas/terreno_mask.png (= pendiente > 35-40 grados + mascara_roca + cortes, con bordes de ruido de
      10-30 m) muestreado en el centro de cada cara por su UV planar (uv_layers[0] o la del nodo TERRENO_uv_planar),
      mas las caras con nz < nz_extra. Es la alternativa a color_ac.roca_caras (nz < 0.50 por cara = poligonos de 4 m
      con borde en sierra, director F1 r1 problema 8) para separar_roca_terreno (P1, [W]) y para --modo-ac.
  v3 (F1 r3, director r2 problemas 3/5/6): (1) SIN RETICULA: la ondulacion de los estratos la ponen dos ruidos 2D propios
      (40 m +-0.8 m, 6 m +-0.2 m) y el Wave lleva Distortion 0.6 (antes 5.0 = ruido a la escala del Wave, ~9.5 m: las
      'celdas' de 10-15 m / 'red de pesca'); (2) junta, cornisa, relieve y grano ATENUADOS con la distancia a la camara
      (Camera Data: 1 a <= fade_cerca_m 80, FADE_MIN 0.25 a >= fade_lejos_m 260; <= 0 desactiva: hornear); (3) ao_pared
      (0.72): la pared = tono_pared x ao_pared (sombra propia de los estratos: la caliza media al sol deja de salir blanca y
      se separa de la tierra); (4) ajustar_bsdf(material): Roughness 1 y Specular IOR Level 0 (sin Fresnel del cielo = sin
      velo gris-cian a vista rasante; ksPerPixel tampoco lo tiene); aplicar_a lo llama y actualizar_grupo lo aplica a
      todo lo que lleva el grupo (terreno incluido) y re-escribe diffuse_color de los kits con ao_pared; (5) reaplicar
      (material, **kw): rehace la pasada con otros tile_m/factor/tonos (McLaren: tile 12 m, factor 0.4).
  v4 (F1 r4, director r3 problemas 4/5; atribucion en _rev/_tmp_materiales/r4/diag_*: con la junta a 0 desaparecen las
      lineas oblicuas de la 'red' de 36 y las horizontales de 51/07; con pared = 0 no): (1) ESTRATOS EN PARCHES: la junta
      y la cornisa van multiplicadas por un ruido 3D de ~30 m (CAL_parches, 0.15..1): ya no hay una familia de lineas
      rectas continuas que cruce aristas y laderas planas (lo que, sobre las estrias del tile planar del terreno, se leia
      como celdas de 10-15 m); (2) ondulacion mayor (40 m +-1.2 m, 14 m +-0.5 m, 6 m +-0.2 m): los contornos dejan de ser
      rectos; (3) la rampa de orientacion (nz) lleva ruido 3D +-0.06 a ~3 m (CAL_nz_ruido) y es mas ancha (0.92..0.55):
      sin bandas de Mach en las facetas de 4 m; (4) fade mas agresivo (60 m -> 0.12 a 260 m); (5) media_material(): la
      media que se escribe en diffuse_color incluye el TINTE del tile de Blender (tile x ganancia escalar de
      aplicar_texturas no tiene media 1 por canal: caliza_d x 1.78 = (1.08, 1.00, 0.77)), que el writer/--modo-ac
      neutralizan por canal: asi el KN5 sale con la misma media calida que se ve en Blender (S 0.23 -> ~0.28);
      (6) aplicar_a admite imagen='caliza_grande_d.png' (24 m, McLaren) con respaldo caliza_d.png.
Colores por defecto = paleta.json (caliza_ocre / caliza_gris_calido / caliza_sombra); nada de literales RGB aqui.
Paleta v2 (usuario 04/10): caliza_ocre = caliza CLARA #D8CCB0 (alias caliza_clara), caliza_gris_calido = MEDIA
#B3A68A (alias caliza_media), caliza_sombra = roca OSCURA #7F766A (alias roca_oscura); sin gris azulado.
Sin bpy.ops. Metros. Blender 5.1 (API node_tree.interface de 4.0+).
"""
import os
import sys

import bpy

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import paleta  # noqa: E402

NOMBRE_GRUPO = 'NG_caliza_estratos'
MARCA = 'CALIZA_ESTRATOS'
CAL_VERSION = 4            # v2 (F1 r2): tono_pared / pared; v3 (F1 r3): fade por distancia, ao_pared; v4 (F1 r4): parches, nz con ruido
DIR_TEX = os.path.join(_RAIZ, 'texturas')
IMAGEN_RESPALDO = 'caliza_d.png'
# v3 (director F1 r2, problemas 3/5/6): la roca y el terreno NO reflejan el cielo. Con Specular IOR Level 0.5 (defecto) el
# Fresnel de EEVEE a vista rasante (n.v 0.07-0.3 en las lomas de 51/07/36) devolvia el cielo (0.70,0.84,0.98): el 'velo'
# gris-cian y la caliza desaturada (S 0.12). ksPerPixel en AC no tiene Fresnel: con 0.0 el preview se parece mas a AC.
RUGOSIDAD_ROCA = 1.0
ESPECULAR_ROCA = 0.0
# AO de pared: la caliza media (0.45 lineal) de cara al sol (irradiancia ~2.0) salia a V 0.90-0.93 ('pared de hielo' de
# 51); x0.72 en la pared (sombra propia de los estratos) la deja en V <= 0.86 y a la vez es la diferencia pared/tierra
# que pedia el director. Entra en media_lineal (diffuse_color para el writer) y en el AO de salida.
AO_PARED = 0.72
# atenuacion con la distancia a la camara de junta/cornisa/relieve (1 a <= 60 m, FADE_MIN a >= 260 m): a > 100 m las juntas
# de 3 m se leian como moire/reticula (36, 07, 51 fondo). fade_lejos_m <= 0 = sin atenuacion (hornear 2.8, previews).
# v4: 80 -> 60 m y 0.25 -> 0.12: con 0.25 las juntas de 36 (250-400 m) seguian siendo lineas oscuras continuas
FADE_CERCA_M, FADE_LEJOS_M, FADE_MIN = 60.0, 260.0, 0.12
# fraccion de la altura del estrato que es junta (~6 %) y cuanto oscurece: entra en media_lineal()
_JUNTA_FRAC, _JUNTA_OSC = 0.06, 0.55
# v4: estratos EN PARCHES: junta y cornisa x ruido 3D de ~PARCHES_M (CAL_parches), de PARCHES_MIN a 1 (media ~PARCHES_MEDIA):
# la familia de lineas rectas continuas de 36/51/07 (contornos de la onda Z sobre laderas planas) se rompe en tramos
PARCHES_M, PARCHES_MIN, PARCHES_MEDIA = 30.0, 0.15, 0.6
_WAVE_K = 0.31416          # periodo en m de un Wave BANDS = _WAVE_K / Scale  (sin(20 * z * scale))
# f_pared por la normal de mundo: 0 con nz >= 0.92 (repisa, suelo, lomo: < 23 grados), 1 con nz <= 0.55 (pared > 57 grados).
# La roca del terreno solo aparece donde la pendiente pasa de 35-40 grados (nz < 0.77-0.82): asi toda esa roca va al tono
# medio y solo las repisas/mesetas quedan en el claro (tres tonos: claro arriba, medio en la ladera, oscuro en la junta).
# v4: rampa mas ancha (0.90..0.60 -> 0.92..0.55) y nz con ruido 3D +-NZ_RUIDO a ~3 m: la normal interpolada por triangulo
# de 4 m del TERRENO ya no dibuja bandas de Mach (facetas) en el tono
PARED_NZ = (0.92, 0.55)
NZ_RUIDO = 0.06
# AO media del terreno (renders/qa/terreno_mask_stats.json['ao']['media_tierra'] si existe): el writer/--modo-ac no tienen
# AO, asi que el color plano de MAT_terreno_roca lleva la AO media que en Blender pone terreno_base.png
AO_MEDIA_TERRENO = 0.757
# entradas del grupo: (nombre, tipo, defecto (o callable), min, max); el orden es el de la interfaz
_ENTRADAS = (
    ('tono_base', 'NodeSocketColor', lambda: paleta.rgba('caliza_ocre'), None, None),
    ('tono_junta', 'NodeSocketColor', lambda: paleta.rgba('caliza_sombra'), None, None),
    ('periodo_m', 'NodeSocketFloat', 3.0, 0.5, 20.0),
    ('bump', 'NodeSocketFloat', 0.45, 0.0, 2.0),
    ('mojado', 'NodeSocketFloat', 1.0, 0.0, 1.0),
    ('fase', 'NodeSocketFloat', 0.0, None, None),
    ('contraste_bancos', 'NodeSocketFloat', 0.12, 0.0, 0.5),
    ('grano', 'NodeSocketFloat', 1.0, 0.0, 2.0),
    ('manchas', 'NodeSocketFloat', 1.0, 0.0, 2.0),
    ('tono_pared', 'NodeSocketColor', lambda: paleta.rgba('caliza_gris_calido'), None, None),
    ('pared', 'NodeSocketFloat', 1.0, 0.0, 1.0),
    ('ao_pared', 'NodeSocketFloat', AO_PARED, 0.0, 1.0),              # v3
    ('fade_cerca_m', 'NodeSocketFloat', FADE_CERCA_M, 0.0, 5000.0),   # v3
    ('fade_lejos_m', 'NodeSocketFloat', FADE_LEJOS_M, 0.0, 10000.0),  # v3 (<= 0: sin atenuacion)
)
_SALIDAS = (('Color', 'NodeSocketColor'), ('Normal', 'NodeSocketVector'), ('AO', 'NodeSocketFloat'))


def _socket_in(ng, nombre, tipo, valor=None, vmin=None, vmax=None):
    s = ng.interface.new_socket(name=nombre, in_out='INPUT', socket_type=tipo)
    if valor is not None:
        s.default_value = valor() if callable(valor) else valor
    if vmin is not None and hasattr(s, 'min_value'):
        s.min_value = vmin
    if vmax is not None and hasattr(s, 'max_value'):
        s.max_value = vmax
    return s


def _math(nodes, links, op, a, b=None, c=None, nombre=None, loc=(0, 0)):
    n = nodes.new('ShaderNodeMath')
    n.operation = op
    n.location = loc
    if nombre:
        n.name = n.label = nombre
    for i, v in enumerate((a, b, c)):
        if v is None:
            continue
        if hasattr(v, 'is_output'):            # socket
            links.new(v, n.inputs[i])
        else:
            n.inputs[i].default_value = float(v)
    return n


def _map(nodes, links, entrada, de, a, nombre=None, loc=(0, 0), suave=False):
    n = nodes.new('ShaderNodeMapRange')
    n.clamp = True
    if suave:
        n.interpolation_type = 'SMOOTHSTEP'
    n.location = loc
    if nombre:
        n.name = n.label = nombre
    n.inputs['From Min'].default_value, n.inputs['From Max'].default_value = de
    n.inputs['To Min'].default_value, n.inputs['To Max'].default_value = a
    links.new(entrada, n.inputs['Value'])
    return n


def _mix_rgb(nodes, links, tipo, fac, a, b, nombre=None, loc=(0, 0)):
    n = nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    n.blend_type = tipo
    n.clamp_result = False
    n.location = loc
    if nombre:
        n.name = n.label = nombre
    ins = [s for s in n.inputs if s.type == 'RGBA']
    if hasattr(fac, 'is_output'):
        links.new(fac, n.inputs[0])
    else:
        n.inputs[0].default_value = float(fac)
    for s, v in ((ins[0], a), (ins[1], b)):
        if hasattr(v, 'is_output'):
            links.new(v, s)
        else:
            s.default_value = tuple(v) + (1.0,) if len(v) == 3 else tuple(v)
    return n, [s for s in n.outputs if s.type == 'RGBA'][0]


def _sockets_interfaz(ng, in_out):
    return [s for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == in_out]


def _asegurar_interfaz(ng):
    """Crea las entradas/salidas que falten (un grupo v1 guardado gana tono_pared/pared sin perder sus enlaces).
    Devuelve los nombres anadidos."""
    tengo_in = set(s.name for s in _sockets_interfaz(ng, 'INPUT'))
    tengo_out = set(s.name for s in _sockets_interfaz(ng, 'OUTPUT'))
    nuevos = []
    for nombre, tipo, valor, vmin, vmax in _ENTRADAS:
        if nombre not in tengo_in:
            _socket_in(ng, nombre, tipo, valor, vmin, vmax)
            nuevos.append(nombre)
    for nombre, tipo in _SALIDAS:
        if nombre not in tengo_out:
            ng.interface.new_socket(name=nombre, in_out='OUTPUT', socket_type=tipo)
            nuevos.append(nombre)
    return nuevos


def _construir(ng):
    """Nodos de dentro del grupo (la interfaz ya existe). Se puede llamar sobre un grupo viejo: borra y rehace.
    v3 (F1 r3): estratos SIN reticula (ondulacion propia de 40 m / 6 m en vez de Distortion 5 del Wave, que era un
    ruido de ~periodo_m x 3 = 9.5 m: las 'celdas' de 10-15 m), junta/cornisa/relieve/grano atenuados con la DISTANCIA a
    la camara (Camera Data: 1 a <= fade_cerca_m, FADE_MIN a >= fade_lejos_m; fade_lejos_m <= 0 lo desactiva, p. ej. para
    hornear) y AO de pared (Color x ao_pared en las paredes: la caliza media al sol deja de recortarse a blanco)."""
    nodes, links = ng.nodes, ng.links
    nodes.clear()
    gi = nodes.new('NodeGroupInput')
    gi.location = (-2100, 0)
    go = nodes.new('NodeGroupOutput')
    go.location = (1500, 0)

    # --- coordenadas de MUNDO (no de objeto) + fase en z
    geo = nodes.new('ShaderNodeNewGeometry')
    geo.name = geo.label = 'CAL_geometria'
    geo.location = (-1900, 400)
    fase_v = nodes.new('ShaderNodeCombineXYZ')
    fase_v.location = (-1900, 150)
    links.new(gi.outputs['fase'], fase_v.inputs['Z'])
    pos = nodes.new('ShaderNodeVectorMath')
    pos.operation = 'ADD'
    pos.name = pos.label = 'CAL_pos_mundo'
    pos.location = (-1700, 300)
    links.new(geo.outputs['Position'], pos.inputs[0])
    links.new(fase_v.outputs['Vector'], pos.inputs[1])
    sep = nodes.new('ShaderNodeSeparateXYZ')
    sep.location = (-1500, 300)
    links.new(pos.outputs['Vector'], sep.inputs['Vector'])
    z = sep.outputs['Z']

    # --- v3/v4: ondulacion de los estratos (dominio): z' = z + 1.2 m x ruido 2D de ~40 m + 0.5 m x ruido 2D de ~14 m
    #     + 0.2 m x ruido 2D de ~6 m. Antes (v2) la ondulacion la ponia Distortion 5 del Wave = ruido a la escala del propio
    #     Wave (periodo_m x 3 ~ 9.5 m): a > 100 m se leia como RETICULA de celdas de 10-15 m ('red de pesca', director F1 r2
    #     problema 5). v4: amplitudes mayores + 14 m: los contornos de la onda Z sobre una ladera plana (36) ya no son rectos
    on1 = nodes.new('ShaderNodeTexNoise')
    on1.name = on1.label = 'CAL_ondula_40m'
    on1.noise_dimensions = '2D'
    on1.location = (-1500, 900)
    on1.inputs['Scale'].default_value = 0.025
    on1.inputs['Detail'].default_value = 1.0
    links.new(pos.outputs['Vector'], on1.inputs['Vector'])
    on2 = nodes.new('ShaderNodeTexNoise')
    on2.name = on2.label = 'CAL_ondula_6m'
    on2.noise_dimensions = '2D'
    on2.location = (-1500, 1150)
    on2.inputs['Scale'].default_value = 0.17
    on2.inputs['Detail'].default_value = 2.0
    links.new(pos.outputs['Vector'], on2.inputs['Vector'])
    on3 = nodes.new('ShaderNodeTexNoise')
    on3.name = on3.label = 'CAL_ondula_14m'
    on3.noise_dimensions = '2D'
    on3.location = (-1500, 1400)
    on3.inputs['Scale'].default_value = 0.07
    on3.inputs['Detail'].default_value = 1.5
    links.new(pos.outputs['Vector'], on3.inputs['Vector'])
    dz1 = _math(nodes, links, 'MULTIPLY_ADD', on1.outputs['Fac'], 2.4, -1.2, loc=(-1300, 900))       # -1.2 .. +1.2 m
    dz2 = _math(nodes, links, 'MULTIPLY_ADD', on2.outputs['Fac'], 0.4, -0.2, loc=(-1300, 1150))      # -0.2 .. +0.2 m
    dz3 = _math(nodes, links, 'MULTIPLY_ADD', on3.outputs['Fac'], 1.0, -0.5, loc=(-1300, 1400))      # -0.5 .. +0.5 m
    dz12 = _math(nodes, links, 'ADD', dz1.outputs['Value'], dz2.outputs['Value'], loc=(-1150, 1000))
    dz = _math(nodes, links, 'ADD', dz12.outputs['Value'], dz3.outputs['Value'], loc=(-1100, 1250))
    zw = _math(nodes, links, 'ADD', z, dz.outputs['Value'], nombre='CAL_z_ondulada', loc=(-1000, 1000))

    # --- v4: PARCHES: ruido 3D de ~PARCHES_M -> PARCHES_MIN..1 (smoothstep): multiplica junta y cornisa. Los estratos solo
    #     se marcan por tramos (bancos meteorizados / lisos), nunca como lineas rectas continuas de ladera a ladera
    npa = nodes.new('ShaderNodeTexNoise')
    npa.name = npa.label = 'CAL_ruido_parches'
    npa.location = (-1700, -1000)
    npa.inputs['Scale'].default_value = 1.0 / PARCHES_M
    npa.inputs['Detail'].default_value = 1.5
    npa.inputs['Roughness'].default_value = 0.5
    links.new(pos.outputs['Vector'], npa.inputs['Vector'])
    parches = _map(nodes, links, npa.outputs['Fac'], (0.38, 0.62), (PARCHES_MIN, 1.0), nombre='CAL_parches',
                   loc=(-1500, -1000), suave=True)
    parches_v = parches.outputs['Result']
    posw = nodes.new('ShaderNodeCombineXYZ')
    posw.name = posw.label = 'CAL_pos_ondulada'
    posw.location = (-850, 1000)
    links.new(sep.outputs['X'], posw.inputs['X'])
    links.new(sep.outputs['Y'], posw.inputs['Y'])
    links.new(zw.outputs['Value'], posw.inputs['Z'])

    # --- v3: atenuacion con la distancia a la camara (junta, cornisa, relieve, grano): 1 a <= fade_cerca_m,
    #     FADE_MIN a >= fade_lejos_m. fade_lejos_m <= 0 => 1 siempre (hornear, previews sin camara)
    cam = nodes.new('ShaderNodeCameraData')
    cam.name = cam.label = 'CAL_camara'
    cam.location = (-1900, -1400)
    fd = _map(nodes, links, cam.outputs['View Distance'], (FADE_CERCA_M, FADE_LEJOS_M), (1.0, FADE_MIN), nombre='CAL_fade_dist',
              loc=(-1700, -1400), suave=True)
    links.new(gi.outputs['fade_cerca_m'], fd.inputs['From Min'])
    links.new(gi.outputs['fade_lejos_m'], fd.inputs['From Max'])
    fd_on = _math(nodes, links, 'GREATER_THAN', gi.outputs['fade_lejos_m'], 0.0, loc=(-1700, -1600))
    fd_m1 = _math(nodes, links, 'SUBTRACT', fd.outputs['Result'], 1.0, loc=(-1500, -1500))
    fade = _math(nodes, links, 'MULTIPLY_ADD', fd_on.outputs['Value'], fd_m1.outputs['Value'], 1.0, nombre='CAL_fade',
                 loc=(-1300, -1500))                                                   # on ? fade : 1
    fade_v = fade.outputs['Value']

    # --- v2: tono por ORIENTACION. nz de la normal de mundo (antes del bump): repisa (nz >= 0.90) = tono_base,
    #     pared (nz <= 0.60) = tono_pared (nunca mas clara que tono_base: minimo por canal), transicion suave
    sepn = nodes.new('ShaderNodeSeparateXYZ')
    sepn.name = sepn.label = 'CAL_normal_xyz'
    sepn.location = (-1700, 650)
    links.new(geo.outputs['Normal'], sepn.inputs['Vector'])
    # v4: nz + ruido 3D +-NZ_RUIDO (~3 m): la rampa no sigue las facetas de 4 m del TERRENO (bandas de Mach en el tono)
    nnz = nodes.new('ShaderNodeTexNoise')
    nnz.name = nnz.label = 'CAL_nz_ruido'
    nnz.location = (-1900, 650)
    nnz.inputs['Scale'].default_value = 0.33
    nnz.inputs['Detail'].default_value = 2.0
    links.new(pos.outputs['Vector'], nnz.inputs['Vector'])
    nz_r = _math(nodes, links, 'MULTIPLY_ADD', nnz.outputs['Fac'], 2.0 * NZ_RUIDO, -NZ_RUIDO, loc=(-1700, 500))
    nz_d = _math(nodes, links, 'ADD', sepn.outputs['Z'], nz_r.outputs['Value'], nombre='CAL_nz_dither', loc=(-1600, 560))
    f_par = _map(nodes, links, nz_d.outputs['Value'], (PARED_NZ[0], PARED_NZ[1]), (0.0, 1.0), nombre='CAL_pared_f',
                 loc=(-1500, 650), suave=True)
    f_par2 = _math(nodes, links, 'MULTIPLY', f_par.outputs['Result'], gi.outputs['pared'], nombre='CAL_pared_peso',
                   loc=(-1300, 650))
    tp_min = nodes.new('ShaderNodeVectorMath')
    tp_min.operation = 'MINIMUM'
    tp_min.name = tp_min.label = 'CAL_pared_min'
    tp_min.location = (-1300, 850)
    links.new(gi.outputs['tono_base'], tp_min.inputs[0])
    links.new(gi.outputs['tono_pared'], tp_min.inputs[1])
    base_or, base_or_out = _mix_rgb(nodes, links, 'MIX', f_par2.outputs['Value'], gi.outputs['tono_base'],
                                    tp_min.outputs['Vector'], nombre='CAL_tono_orientacion', loc=(-1050, 750))
    # v3: AO de pared: x ao_pared donde es pared (sombra propia de los estratos; la caliza media al sol ya no sale blanca)
    aop_m1 = _math(nodes, links, 'SUBTRACT', gi.outputs['ao_pared'], 1.0, loc=(-1050, 550))
    ao_par_t = _math(nodes, links, 'MULTIPLY_ADD', f_par2.outputs['Value'], aop_m1.outputs['Value'], 1.0,
                     nombre='CAL_ao_pared_tono', loc=(-850, 550))

    # --- estratos: Wave BANDS en Z sobre la posicion ONDULADA, periodo = periodo_m, distorsion minima
    esc = _math(nodes, links, 'DIVIDE', _WAVE_K, gi.outputs['periodo_m'], nombre='CAL_escala_wave', loc=(-1100, 0))
    wv = nodes.new('ShaderNodeTexWave')
    wv.name = wv.label = 'CAL_estratos'
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'Z'
    wv.wave_profile = 'SIN'
    wv.location = (-900, 0)
    wv.inputs['Distortion'].default_value = 0.6
    wv.inputs['Detail'].default_value = 1.0
    wv.inputs['Detail Scale'].default_value = 1.0
    if 'Detail Roughness' in wv.inputs:
        wv.inputs['Detail Roughness'].default_value = 0.5
    links.new(posw.outputs['Vector'], wv.inputs['Vector'])
    links.new(esc.outputs['Value'], wv.inputs['Scale'])
    # junta = fondo de la onda (Fac < umbral): mascara 1 en la junta, 0 fuera, borde suave. El umbral varia a lo
    # largo (ruido de ~4 m, 0.03..0.11): tramos de junta casi cerrada y tramos abiertos, no una raya uniforme
    nj = nodes.new('ShaderNodeTexNoise')
    nj.name = nj.label = 'CAL_ruido_junta'
    nj.location = (-900, 250)
    nj.inputs['Scale'].default_value = 0.25
    nj.inputs['Detail'].default_value = 2.0
    links.new(pos.outputs['Vector'], nj.inputs['Vector'])
    umb_j = _math(nodes, links, 'MULTIPLY_ADD', nj.outputs['Fac'], 0.08, 0.03, nombre='CAL_umbral_junta', loc=(-800, 150))
    junta0 = _map(nodes, links, wv.outputs['Fac'], (0.0, 0.075), (1.0, 0.0), nombre='CAL_junta_raw', loc=(-650, 0), suave=True)
    links.new(umb_j.outputs['Value'], junta0.inputs['From Max'])
    # v4: fade x parches (estratos por tramos) antes de multiplicar la junta y la cornisa
    fade_p = _math(nodes, links, 'MULTIPLY', fade_v, parches_v, nombre='CAL_fade_parches', loc=(-650, -90))
    junta = _math(nodes, links, 'MULTIPLY', junta0.outputs['Result'], fade_p.outputs['Value'], nombre='CAL_junta', loc=(-500, 0))
    # cornisa: franja justo encima de la junta (Fac 0.08-0.22) algo mas clara
    corn0 = _map(nodes, links, wv.outputs['Fac'], (0.08, 0.22), (1.0, 0.0), nombre='CAL_cornisa_raw', loc=(-650, -180), suave=True)
    corn = _math(nodes, links, 'MULTIPLY', corn0.outputs['Result'], fade_p.outputs['Value'], nombre='CAL_cornisa', loc=(-500, -180))
    corn_t = _math(nodes, links, 'MULTIPLY_ADD', corn.outputs['Value'], 0.06, 1.0, nombre='CAL_cornisa_tono', loc=(-350, -180))

    # --- bancos de 8-14 m con tono alterno: hb = 11 + 3*(ruido 2D 70 m), indice = floor((z' + fase_b)/hb) mod 2
    nb = nodes.new('ShaderNodeTexNoise')
    nb.name = nb.label = 'CAL_ruido_bancos'
    nb.location = (-1100, -450)
    nb.noise_dimensions = '2D'
    nb.inputs['Scale'].default_value = 0.014       # ~70 m
    nb.inputs['Detail'].default_value = 1.0
    links.new(pos.outputs['Vector'], nb.inputs['Vector'])
    hb = _math(nodes, links, 'MULTIPLY_ADD', nb.outputs['Fac'], 6.0, 8.0, nombre='CAL_hb', loc=(-900, -450))      # 8..14
    fase_b = _math(nodes, links, 'MULTIPLY_ADD', nb.outputs['Fac'], 9.0, 0.0, nombre='CAL_fase_bancos', loc=(-900, -600))
    zb = _math(nodes, links, 'ADD', zw.outputs['Value'], fase_b.outputs['Value'], nombre='CAL_z_bancos', loc=(-700, -500))
    idx = _math(nodes, links, 'DIVIDE', zb.outputs['Value'], hb.outputs['Value'], loc=(-550, -500))
    fl = _math(nodes, links, 'FLOOR', idx.outputs['Value'], loc=(-400, -500))
    par = _math(nodes, links, 'MODULO', fl.outputs['Value'], 2.0, nombre='CAL_banco_par', loc=(-250, -500))
    par_abs = _math(nodes, links, 'ABSOLUTE', par.outputs['Value'], loc=(-100, -500))
    # tono banco = 1 + contraste * (2*par - 1)
    pm = _math(nodes, links, 'MULTIPLY_ADD', par_abs.outputs['Value'], 2.0, -1.0, loc=(50, -500))
    banco_t = _math(nodes, links, 'MULTIPLY_ADD', pm.outputs['Value'], gi.outputs['contraste_bancos'], 1.0,
                    nombre='CAL_banco_tono', loc=(200, -500))

    # --- grano 0.3-1 m (a lo lejos se queda a la mitad: no chisporrotea) y manchas ~20 m (+-10 %)
    ngr = nodes.new('ShaderNodeTexNoise')
    ngr.name = ngr.label = 'CAL_grano'
    ngr.location = (-1100, -800)
    ngr.inputs['Scale'].default_value = 1.6        # ~0.6 m, con detalle hasta ~0.3 m
    ngr.inputs['Detail'].default_value = 5.0
    ngr.inputs['Roughness'].default_value = 0.6
    links.new(pos.outputs['Vector'], ngr.inputs['Vector'])
    gr_c = _math(nodes, links, 'SUBTRACT', ngr.outputs['Fac'], 0.5, loc=(-900, -800))                 # -0.5..0.5
    gr_f = _math(nodes, links, 'MULTIPLY_ADD', fade_v, 0.5, 0.5, loc=(-900, -950))                     # 0.5 + 0.5 fade
    gr_c2 = _math(nodes, links, 'MULTIPLY', gr_c.outputs['Value'], gr_f.outputs['Value'], loc=(-750, -950))
    gr_k = _math(nodes, links, 'MULTIPLY', gr_c2.outputs['Value'], gi.outputs['grano'], loc=(-750, -800))
    grano_t = _math(nodes, links, 'MULTIPLY_ADD', gr_k.outputs['Value'], 0.16, 1.0, nombre='CAL_grano_tono', loc=(-600, -800))
    nma = nodes.new('ShaderNodeTexNoise')
    nma.name = nma.label = 'CAL_manchas'
    nma.location = (-1100, -1050)
    nma.inputs['Scale'].default_value = 0.05       # ~20 m
    nma.inputs['Detail'].default_value = 4.0
    nma.inputs['Roughness'].default_value = 0.55
    links.new(pos.outputs['Vector'], nma.inputs['Vector'])
    ma_c = _math(nodes, links, 'SUBTRACT', nma.outputs['Fac'], 0.5, loc=(-900, -1050))
    ma_k = _math(nodes, links, 'MULTIPLY', ma_c.outputs['Value'], gi.outputs['manchas'], loc=(-750, -1050))
    manchas_t = _math(nodes, links, 'MULTIPLY_ADD', ma_k.outputs['Value'], 0.20, 1.0, nombre='CAL_manchas_tono', loc=(-600, -1050))   # +-10 %

    # --- mojado bajo z = 1 (0 a z >= 1.6, 1 a z <= 0.6) x entrada mojado
    moj_z = _map(nodes, links, z, (0.6, 1.6), (1.0, 0.0), nombre='CAL_mojado_z', loc=(-650, 300), suave=True)
    moj = _math(nodes, links, 'MULTIPLY', moj_z.outputs['Result'], gi.outputs['mojado'], nombre='CAL_mojado', loc=(-450, 300))
    moj_t = _math(nodes, links, 'MULTIPLY_ADD', moj.outputs['Value'], -0.45, 1.0, nombre='CAL_mojado_tono', loc=(-250, 300))

    # --- color: tono (base/pared segun orientacion) x banco x cornisa x grano x manchas x mojado x AO de pared,
    #     hacia tono_junta en la junta
    tono1 = _math(nodes, links, 'MULTIPLY', banco_t.outputs['Value'], corn_t.outputs['Value'], loc=(350, -300))
    tono2 = _math(nodes, links, 'MULTIPLY', tono1.outputs['Value'], grano_t.outputs['Value'], loc=(500, -300))
    tono3 = _math(nodes, links, 'MULTIPLY', tono2.outputs['Value'], manchas_t.outputs['Value'], loc=(650, -300))
    tono4 = _math(nodes, links, 'MULTIPLY', tono3.outputs['Value'], moj_t.outputs['Value'], loc=(800, -300))
    tono5 = _math(nodes, links, 'MULTIPLY', tono4.outputs['Value'], ao_par_t.outputs['Value'], nombre='CAL_tono', loc=(950, -300))
    base_mix, base_out = _mix_rgb(nodes, links, 'MIX', junta.outputs['Value'], base_or_out, gi.outputs['tono_junta'],
                                  nombre='CAL_color_junta', loc=(800, 100))
    col_mix, col_out = _mix_rgb(nodes, links, 'MULTIPLY', 1.0, base_out, (1.0, 1.0, 1.0), nombre='CAL_color', loc=(1150, 100))
    # el multiplicador escalar entra como color gris por los 3 canales
    tono_rgb = nodes.new('ShaderNodeCombineColor')
    tono_rgb.location = (1100, -300)
    for k in ('Red', 'Green', 'Blue'):
        links.new(tono5.outputs['Value'], tono_rgb.inputs[k])
    links.new(tono_rgb.outputs['Color'], [s for s in col_mix.inputs if s.type == 'RGBA'][1])
    links.new(col_out, go.inputs['Color'])

    # --- relieve: junta hundida (-1), grano (+0.3), cornisa (+0.15); todo ya atenuado con la distancia
    h1 = _math(nodes, links, 'MULTIPLY_ADD', junta.outputs['Value'], -1.0, 0.0, loc=(350, -900))
    h2 = _math(nodes, links, 'MULTIPLY_ADD', gr_c2.outputs['Value'], 0.6, 0.0, loc=(350, -1050))
    h3 = _math(nodes, links, 'MULTIPLY_ADD', corn.outputs['Value'], 0.15, 0.0, loc=(350, -1200))
    h12 = _math(nodes, links, 'ADD', h1.outputs['Value'], h2.outputs['Value'], loc=(550, -950))
    alt = _math(nodes, links, 'ADD', h12.outputs['Value'], h3.outputs['Value'], nombre='CAL_altura', loc=(700, -950))
    bmp = nodes.new('ShaderNodeBump')
    bmp.name = bmp.label = 'CAL_bump'
    bmp.location = (1050, -900)
    if 'Distance' in bmp.inputs:
        bmp.inputs['Distance'].default_value = 0.35
    links.new(gi.outputs['bump'], bmp.inputs['Strength'])
    links.new(alt.outputs['Value'], bmp.inputs['Height'])
    links.new(bmp.outputs['Normal'], go.inputs['Normal'])

    # --- AO: junta oscura (x0.55 en la junta), un poco en el mojado, y la AO de pared
    ao1 = _math(nodes, links, 'MULTIPLY_ADD', junta.outputs['Value'], -0.45, 1.0, loc=(800, -1350))
    ao2 = _math(nodes, links, 'MULTIPLY_ADD', moj.outputs['Value'], -0.15, 1.0, loc=(800, -1500))
    ao12 = _math(nodes, links, 'MULTIPLY', ao1.outputs['Value'], ao2.outputs['Value'], loc=(950, -1400))
    ao = _math(nodes, links, 'MULTIPLY', ao12.outputs['Value'], ao_par_t.outputs['Value'], nombre='CAL_ao', loc=(1100, -1400))
    links.new(ao.outputs['Value'], go.inputs['AO'])
    ng['cal_version'] = CAL_VERSION


def actualizar_grupo(nombre=NOMBRE_GRUPO):
    """Si el .blend trae un NG_caliza_estratos de una version anterior, lo reconstruye EN SITIO (misma interfaz +
    entradas nuevas; los nodos de grupo de los materiales conservan sus enlaces). Devuelve True si lo ha rehecho."""
    ng = bpy.data.node_groups.get(nombre)
    if ng is None:
        return False
    v_antes = int(ng.get('cal_version', 1))
    if v_antes >= CAL_VERSION:
        return False
    nuevos = _asegurar_interfaz(ng)
    _construir(ng)
    # los nodos de grupo que ya existen reciben las entradas nuevas con el valor por defecto de la interfaz (Blender no
    # copia el default_value que se fija despues de crear el socket): se pone a mano en cada material que use el grupo
    defectos = {n: (v() if callable(v) else v) for n, _t, v, _a, _b in _ENTRADAS if n in nuevos}
    usados, retintados, mates = 0, 0, 0
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        g = None
        for n in m.node_tree.nodes:
            if n.type == 'GROUP' and n.node_tree is ng:
                usados += 1
                g = n
                for nombre_s, val in defectos.items():
                    if nombre_s in n.inputs and not n.inputs[nombre_s].is_linked:
                        n.inputs[nombre_s].default_value = val
        if g is None:
            continue
        # v3: el BSDF de todo lo que lleva el grupo (terreno incluido) pasa a mate sin Fresnel; y los materiales de kit
        # (no el terreno: su diffuse_color es hierba_seca, del propietario mascara) re-escriben diffuse_color = media con ao_pared
        if ajustar_bsdf(m):
            mates += 1
        if not es_terreno(m) and m.node_tree.nodes.get(MARCA):
            imagen, factor = _tile_de(m)
            med = media_material(tuple(g.inputs['tono_base'].default_value[:3]), imagen=imagen, factor=factor,
                                 contraste_bancos=float(g.inputs['contraste_bancos'].default_value),
                                 mojado=float(g.inputs['mojado'].default_value), tono_junta=tuple(g.inputs['tono_junta'].default_value[:3]),
                                 tono_pared=tuple(g.inputs['tono_pared'].default_value[:3]),
                                 frac_pared=float(m.get('cal_frac_pared', 0.5)), pared=float(g.inputs['pared'].default_value),
                                 ao_pared=float(g.inputs['ao_pared'].default_value))
            m.diffuse_color = tuple(med) + (1.0,)
            retintados += 1
    print('materiales_roca: %s v%d -> v%d reconstruido en sitio (entradas nuevas: %s; %d nodos de grupo en materiales; '
          '%d BSDF a mate; %d diffuse_color re-escritos con ao_pared)'
          % (nombre, v_antes, CAL_VERSION, nuevos or 'ninguna', usados, mates, retintados))
    return True


def ng_caliza_estratos(nombre=NOMBRE_GRUPO):
    """Grupo de nodos de la caliza compartida (se crea una vez por .blend; uno viejo se actualiza a CAL_VERSION)."""
    ng = bpy.data.node_groups.get(nombre)
    if ng is not None:
        actualizar_grupo(nombre)
        return ng
    ng = bpy.data.node_groups.new(nombre, 'ShaderNodeTree')
    _asegurar_interfaz(ng)
    _construir(ng)
    return ng


def media_lineal(tono_base, contraste_bancos=0.12, mojado=1.0, tono_junta=None, tono_pared=None, frac_pared=0.5, pared=1.0,
                 ao_pared=AO_PARED):
    """Media lineal aproximada del color del grupo: tono (base en repisas, pared x ao_pared en paredes, segun frac_pared)
    x (1 - junta) + tono_junta x junta, con el grano y las manchas centrados en 1 y los bancos alternos (media 1). La
    escribe aplicar_a en diffuse_color. frac_pared = fraccion de superficie que es pared (0.5 por defecto; 1.0 = solo pared)."""
    tb = tuple(float(c) for c in tono_base[:3])
    tj = tuple(tono_junta) if tono_junta is not None else paleta.rgb('caliza_sombra')
    tp = tuple(tono_pared) if tono_pared is not None else paleta.rgb('caliza_gris_calido')
    tp = tuple(min(a, float(b)) for a, b in zip(tb, tp[:3]))             # la pared nunca mas clara que la base
    fp = max(0.0, min(1.0, float(frac_pared) * float(pared)))
    aop = max(0.0, min(1.0, float(ao_pared)))
    tono = tuple((1 - fp) * a + fp * b * aop for a, b in zip(tb, tp))
    f = _JUNTA_FRAC * PARCHES_MEDIA                 # v4: la junta solo esta en los parches (media ~0.6 de la superficie)
    return tuple(min(1.0, max(0.0, (1 - f) * t * 1.005 + f * float(j))) for t, j in zip(tono, tj[:3]))


def _media_tile(fichero):
    """Media lineal (r, g, b) del tile (texturas/medias.json) o None."""
    try:
        import json
        with open(os.path.join(DIR_TEX, 'medias.json'), encoding='utf-8') as fh:
            d = json.load(fh)
        return tuple(float(c) for c in d[fichero]['media_lineal'][:3])
    except Exception:
        return None


def tinte_tile(imagen, factor, ganancia=None):
    """v4: factor (r, g, b) con el que el tile de Blender (TEX_imagen x TEX_ganancia ESCALAR, mezclado con `factor`) altera la
    media del color del grupo: (1 - factor) + factor x media_tile x ganancia, por canal. caliza_d x 1.78 = (1.08, 1.00, 0.77):
    con factor 0.5 -> (1.04, 1.00, 0.88). El writer y --modo-ac normalizan el tile POR CANAL (media = diffuse_color), asi que
    sin esto el KN5 salia mas neutro que Blender (director r3 n.4: S 0.05-0.08 en el proxy). (1, 1, 1) si no hay tile."""
    if not imagen:
        return (1.0, 1.0, 1.0)
    med = _media_tile(imagen)
    if med is None:
        return (1.0, 1.0, 1.0)
    gan = float(ganancia) if ganancia is not None else _ganancia(imagen)
    f = max(0.0, min(1.0, float(factor)))
    return tuple((1.0 - f) + f * c * gan for c in med)


def media_material(tono_base, imagen='caliza_d.png', factor=0.5, ganancia=None, **kw):
    """v4: la media lineal que se escribe en diffuse_color = media_lineal(tono_base, **kw) x tinte_tile(imagen, factor):
    lo que de verdad se ve en Blender (grupo x tile con ganancia escalar). Es lo que lee el writer (analizar_material)."""
    med = media_lineal(tono_base, **kw)
    t = tinte_tile(imagen, factor, ganancia)
    return tuple(min(1.0, max(0.0, m * k)) for m, k in zip(med, t))


def ao_media_terreno():
    """AO media del terreno medida por mascara_terreno (renders/qa/terreno_mask_stats.json); si no, AO_MEDIA_TERRENO."""
    try:
        import json
        with open(os.path.join(_RAIZ, 'renders', 'qa', 'terreno_mask_stats.json'), encoding='utf-8') as fh:
            return float(json.load(fh)['ao']['media_tierra'])
    except Exception:
        return AO_MEDIA_TERRENO


def color_roca_terreno_ac(ao=None):
    """Media lineal de una PARED de caliza (repisas aparte; con la AO de pared v3) x la AO media del terreno: lo que
    deberia valer color_ac.ROCA_COLOR (P1) para que las caras de roca del terreno en AC a pelo sean la caliza media de la
    paleta con su sombra media (y no el literal (0.34, 0.27, 0.18)). Con la paleta v2, ao_pared 0.72 y AO 0.757 sale
    (0.239, 0.202, 0.135) = #887A66: al sol de AC se ve como la caliza media #B3A68A (V ~0.75) y se separa de la tierra."""
    ao = float(ao) if ao is not None else ao_media_terreno()
    return tuple(c * ao for c in media_lineal(paleta.rgb('caliza_ocre'), frac_pared=1.0))


def _principled(nt):
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


def tiene_caliza(material):
    nt = material.node_tree
    return bool(nt and nt.nodes.get(MARCA))


def _tile_de(material):
    """(imagen, factor) del tile que lleva un material con la caliza aplicada: custom props cal_* (v3+) o, si no, la cadena
    TEX_imagen / TEX_multiplicar. ('', 1.0) si no hay tile."""
    nt = material.node_tree
    imagen = material.get('cal_imagen')
    factor = material.get('cal_factor')
    if imagen is None and nt is not None:
        tex = nt.nodes.get('TEX_imagen')
        imagen = os.path.basename(bpy.path.abspath(tex.image.filepath)) if (tex is not None and tex.image) else ''
    if factor is None and nt is not None:
        mul = nt.nodes.get('TEX_multiplicar')
        sf = next((s for s in mul.inputs if s.identifier == 'Factor_Float'), None) if mul is not None else None
        factor = float(sf.default_value) if sf is not None else 1.0
    return (str(imagen or ''), float(factor if factor is not None else 1.0))


def crear_nodos(nt, loc=(0, 0), tono_base=None, tono_junta=None, periodo_m=3.0, bump=0.45, mojado=1.0, fase=0.0,
                contraste_bancos=0.12, grano=1.0, manchas=1.0, tono_pared=None, pared=1.0, nombre_nodo='CAL_grupo',
                ao_pared=None, fade_cerca_m=None, fade_lejos_m=None):
    """Anade el grupo al arbol `nt` sin enlazar nada mas. Devuelve (nodo, Color, Normal, AO).
    v3: ao_pared / fade_cerca_m / fade_lejos_m = None toman el defecto de la interfaz (AO_PARED, FADE_*)."""
    ng = ng_caliza_estratos()
    g = nt.nodes.new('ShaderNodeGroup')
    g.node_tree = ng
    g.name = g.label = nombre_nodo
    g.location = loc
    tb = tuple(tono_base) if tono_base is not None else paleta.rgb('caliza_ocre')
    tj = tuple(tono_junta) if tono_junta is not None else paleta.rgb('caliza_sombra')
    tp = tuple(tono_pared) if tono_pared is not None else paleta.rgb('caliza_gris_calido')
    g.inputs['tono_base'].default_value = tuple(tb[:3]) + (1.0,)
    g.inputs['tono_junta'].default_value = tuple(tj[:3]) + (1.0,)
    g.inputs['tono_pared'].default_value = tuple(tp[:3]) + (1.0,)
    g.inputs['periodo_m'].default_value = float(periodo_m)
    g.inputs['bump'].default_value = float(bump)
    g.inputs['mojado'].default_value = float(mojado)
    g.inputs['fase'].default_value = float(fase)
    g.inputs['contraste_bancos'].default_value = float(contraste_bancos)
    g.inputs['grano'].default_value = float(grano)
    g.inputs['manchas'].default_value = float(manchas)
    g.inputs['pared'].default_value = float(pared)
    for nombre_s, val in (('ao_pared', ao_pared), ('fade_cerca_m', fade_cerca_m), ('fade_lejos_m', fade_lejos_m)):
        if val is not None and nombre_s in g.inputs:
            g.inputs[nombre_s].default_value = float(val)
    return g, g.outputs['Color'], g.outputs['Normal'], g.outputs['AO']


def _imagen(fichero, dir_tex=DIR_TEX):
    ruta = os.path.join(dir_tex, fichero)
    for img in bpy.data.images:
        try:
            if (os.path.normcase(bpy.path.abspath(img.filepath)) == os.path.normcase(ruta)
                    and img.colorspace_settings.name == 'sRGB'):
                return img
        except Exception:
            continue
    if not os.path.exists(ruta):
        return None
    img = bpy.data.images.load(ruta, check_existing=False)
    img.filepath = ruta
    img.colorspace_settings.name = 'sRGB'
    return img


def _ganancia(fichero):
    """1/media lineal del tile (texturas/medias.json si existe; si no 1.0: el writer recalcula la suya)."""
    try:
        import json
        with open(os.path.join(DIR_TEX, 'medias.json'), encoding='utf-8') as fh:
            d = json.load(fh)
        return float(d[fichero]['ganancia'])
    except Exception:
        return 1.0


def _props_ac(material, imagen):
    """Custom props ac_* (plan decision 5) con valor = comportamiento actual del writer, sin pisar las que ya haya."""
    defectos = {'ac_shader': 'ksPerPixel', 'ac_props': {}, 'ac_samplers': {'txDiffuse': imagen or ''},
                'ac_tex_max': 1024, 'ac_alpha_test': 0, 'ac_raw': 0}
    for k, v in defectos.items():
        if k not in material:
            material[k] = v


def ajustar_bsdf(material, rugosidad=RUGOSIDAD_ROCA, especular=ESPECULAR_ROCA):
    """v3: Principled de roca/terreno MATE: Roughness = rugosidad y 'Specular IOR Level' = especular (0 = sin Fresnel del
    cielo, como ksPerPixel). Solo entradas sin enlazar. Idempotente. Devuelve True si ha cambiado algo. Vale para
    MAT_terreno (no toca nodos ni enlaces: solo dos valores del BSDF)."""
    nt = material.node_tree
    bsdf = _principled(nt) if nt else None
    if bsdf is None:
        return False
    cambiado = False
    for nombre_s, val in (('Roughness', rugosidad), ('Specular IOR Level', especular)):
        s = bsdf.inputs.get(nombre_s)
        if s is None or s.is_linked:
            continue
        if abs(float(s.default_value) - float(val)) > 1e-6:
            s.default_value = float(val)
            cambiado = True
    return cambiado


def es_terreno(material):
    """True si es el material del TERRENO (lleva el nodo 'Math.002'/'ROCA_mascara' del contrato): nunca se re-aplica."""
    nt = material.node_tree
    return bool(nt and (nt.nodes.get('Math.002') is not None or material.name == 'MAT_terreno'))


def reaplicar(material, **kw):
    """v3: quita la pasada previa de aplicar_a (grupo, cadena TEX_* y marcadores) y vuelve a aplicar con los parametros
    nuevos (p. ej. otro tile_m/factor para el McLaren, u otro tono). Conserva tono_base/tono_junta/tono_pared/contraste/
    bump/mojado/pared/fase del nodo de grupo existente salvo que vengan en kw. Nunca sobre el terreno (es_terreno).
    Devuelve el nodo de grupo nuevo, o el existente si no habia nada que rehacer."""
    nt = material.node_tree
    if nt is None or es_terreno(material):
        return None
    g = next((n for n in nt.nodes if n.type == 'GROUP' and n.node_tree and n.node_tree.name == NOMBRE_GRUPO), None)
    if g is None or not nt.nodes.get(MARCA):
        return aplicar_a(material, **kw)
    previos = {}
    for k in ('tono_base', 'tono_junta', 'tono_pared'):
        previos[k] = tuple(g.inputs[k].default_value[:3])
    for k in ('contraste_bancos', 'bump', 'mojado', 'pared', 'fase', 'grano', 'manchas', 'ao_pared', 'fade_cerca_m', 'fade_lejos_m'):
        if k in g.inputs:
            previos[k] = float(g.inputs[k].default_value)
    for k in ('imagen', 'tile_m', 'factor', 'frac_pared'):
        if material.get('cal_' + k) is not None:
            previos[k] = material['cal_' + k]
    previos.update(kw)
    bsdf = _principled(nt)
    if bsdf is not None:
        for s in (bsdf.inputs['Base Color'], bsdf.inputs['Normal']):
            for l in list(s.links):
                nt.links.remove(l)
        bsdf.inputs['Base Color'].default_value = tuple(previos['tono_base'][:3]) + (1.0,)
    # por NOMBRE: tras nodes.remove() las referencias a otros nodos de bpy dejan de ser fiables ('n is g' fallaba)
    quitar = [n.name for n in nt.nodes if n.name.startswith('TEX_') or n.name in (MARCA, 'TEXTURIZADO')
              or (n.type == 'GROUP' and n.node_tree is not None and n.node_tree.name == NOMBRE_GRUPO)]
    for nombre_n in quitar:
        nd = nt.nodes.get(nombre_n)
        if nd is not None:
            nt.nodes.remove(nd)
    return aplicar_a(material, **previos)


def aplicar_a(material, tono_base=None, tono_junta=None, imagen='caliza_d.png', tile_m=6.0, factor=0.5, ganancia=None,
              marcar_texturizado=True, tono_pared=None, pared=1.0, frac_pared=0.5, ao_pared=None, **kw):
    """Enchufa la caliza compartida en un material de kit. Ver docstring del modulo. Devuelve el nodo del grupo
    (o el existente si ya estaba aplicada). v3: ademas deja el BSDF mate (ajustar_bsdf) y guarda los parametros en
    custom props cal_* para que reaplicar() pueda rehacerlo con otros."""
    nt = material.node_tree
    if nt is None:
        material.use_nodes = True
        nt = material.node_tree
    if nt.nodes.get(MARCA):
        ajustar_bsdf(material)
        return next((n for n in nt.nodes if n.type == 'GROUP' and n.node_tree and n.node_tree.name == NOMBRE_GRUPO), None)
    bsdf = _principled(nt)
    if bsdf is None:
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    nodes, links = nt.nodes, nt.links
    px, py = bsdf.location
    ent_base = bsdf.inputs['Base Color']
    if tono_base is None:
        tono_base = tuple(ent_base.default_value[:3]) if not ent_base.links else tuple(material.diffuse_color[:3])
    tono_base = tuple(float(c) for c in tono_base[:3])
    if tono_junta is None:
        tono_junta = paleta.rgb('caliza_sombra')
    if tono_pared is None:
        tono_pared = paleta.rgb('caliza_gris_calido')
    # quita el enlace previo al Base Color (rampa de moteado de _mat_piedra, etc.); los nodos viejos se quedan sueltos
    for l in list(ent_base.links):
        links.remove(l)
    g, c_out, n_out, _ao = crear_nodos(nt, loc=(px - 900, py + 250), tono_base=tono_base, tono_junta=tono_junta,
                                       tono_pared=tono_pared, pared=pared, ao_pared=ao_pared, **kw)
    aop = float(g.inputs['ao_pared'].default_value) if 'ao_pared' in g.inputs else AO_PARED

    # cadena de imagen (contrato del writer): TEX_coord(Object) -> TEX_mapping -> TEX_imagen(BOX) -> TEX_ganancia -> TEX_multiplicar
    img = _imagen(imagen) if imagen else None
    if imagen and img is None and imagen != IMAGEN_RESPALDO:
        print('materiales_roca: AVISO falta texturas/%s: se usa %s' % (imagen, IMAGEN_RESPALDO))
        imagen = IMAGEN_RESPALDO
        img = _imagen(imagen)
    gan = None
    if img is not None:
        tco = nodes.new('ShaderNodeTexCoord')
        tco.name = 'TEX_coord'
        tco.location = (px - 1300, py - 150)
        mp = nodes.new('ShaderNodeMapping')
        mp.name = 'TEX_mapping'
        mp.location = (px - 1100, py - 150)
        s = 1.0 / float(tile_m)
        mp.inputs['Scale'].default_value = (s, s, s)
        links.new(tco.outputs['Object'], mp.inputs['Vector'])
        tex = nodes.new('ShaderNodeTexImage')
        tex.name = 'TEX_imagen'
        tex.location = (px - 900, py - 150)
        tex.image = img
        tex.projection = 'BOX'
        tex.projection_blend = 0.3
        tex.extension = 'REPEAT'
        tex.interpolation = 'Linear'
        links.new(mp.outputs['Vector'], tex.inputs['Vector'])
        gan = ganancia if ganancia is not None else _ganancia(imagen)
        g_mix, g_out = _mix_rgb(nodes, links, 'MULTIPLY', 1.0, tex.outputs['Color'], (gan, gan, gan), nombre='TEX_ganancia',
                                loc=(px - 600, py - 150))
        g_mix.label = 'TEX_ganancia'
        m_mix, m_out = _mix_rgb(nodes, links, 'MULTIPLY', float(factor), c_out, g_out, nombre='TEX_multiplicar',
                                loc=(px - 350, py + 60))
        m_mix.clamp_result = True
        links.new(m_out, ent_base)
    else:
        links.new(c_out, ent_base)
    # normal del grupo (sustituye un bump previo si lo habia)
    ent_n = bsdf.inputs['Normal']
    for l in list(ent_n.links):
        links.remove(l)
    links.new(n_out, ent_n)
    ajustar_bsdf(material)                       # v3: mate, sin Fresnel del cielo
    # media lineal para el writer (v4: x tinte del tile de Blender, que el writer neutraliza por canal)
    med = media_material(tono_base, imagen=imagen if img is not None else '', factor=factor, ganancia=gan,
                         contraste_bancos=kw.get('contraste_bancos', 0.12), mojado=kw.get('mojado', 1.0), tono_junta=tono_junta,
                         tono_pared=tono_pared, frac_pared=frac_pared, pared=pared, ao_pared=aop)
    material.diffuse_color = tuple(med) + (1.0,)
    material['cal_frac_pared'] = float(frac_pared)
    material['cal_tono_base'] = tuple(tono_base)
    material['cal_imagen'] = imagen or ''
    material['cal_tile_m'] = float(tile_m)
    material['cal_factor'] = float(factor)
    _props_ac(material, imagen if img is not None else None)
    marca = nodes.new('NodeFrame')
    marca.name = marca.label = MARCA
    marca.location = (px - 1300, py + 500)
    if marcar_texturizado and not nodes.get('TEXTURIZADO'):
        m2 = nodes.new('NodeFrame')
        m2.name = m2.label = 'TEXTURIZADO'
        m2.location = (px - 1300, py + 420)
    return g


def material_caliza(nombre, tono_base=None, rough=0.92, **kw):
    """Crea (o devuelve) un material Principled con la caliza aplicada: util para kits nuevos y tests."""
    m = bpy.data.materials.get(nombre)
    if m is not None:
        if not tiene_caliza(m):
            aplicar_a(m, tono_base=tono_base, **kw)
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bs = _principled(m.node_tree)
    tb = tuple(tono_base) if tono_base is not None else paleta.rgb('caliza_ocre')
    if bs is not None:
        bs.inputs['Base Color'].default_value = tuple(tb[:3]) + (1.0,)
        bs.inputs['Roughness'].default_value = rough
    m.diffuse_color = tuple(tb[:3]) + (1.0,)
    aplicar_a(m, tono_base=tb, **kw)
    return m


# ------------------------------------------------------------------------------ roca del terreno por cara (P1, [W])
ROCA_BASE = 'MAT_terreno'
_MASK_CACHE = {}


def _canal_a_mascara(ruta):
    """Canal A (roca) de terreno_mask.png como array (h, w) float 0..1 con la fila 0 ABAJO (= convencion UV de Blender).
    Reutiliza el datablock si la escena ya lo tiene cargado; si no, lo carga y lo descarga."""
    import numpy as np
    clave = os.path.normcase(os.path.abspath(ruta))
    if clave in _MASK_CACHE:
        return _MASK_CACHE[clave]
    img = None
    for im in bpy.data.images:
        try:
            if im.filepath and os.path.normcase(os.path.abspath(bpy.path.abspath(im.filepath))) == clave:
                img = im
                break
        except Exception:
            continue
    nuevo = img is None
    if nuevo:
        if not os.path.exists(ruta):
            return None
        img = bpy.data.images.load(ruta, check_existing=False)
    w, h = img.size
    ch = int(img.channels)
    buf = np.empty(w * h * ch, np.float32)
    img.pixels.foreach_get(buf)
    buf = buf.reshape(h, w, ch)
    A = np.ascontiguousarray(buf[..., 3] if ch >= 4 else buf[..., 0])
    if nuevo:
        bpy.data.images.remove(img)
    _MASK_CACHE[clave] = A
    return A


def _ruta_mascara(mat):
    try:
        s = mat.get('ac_samplers')
        r = s.get('txMask') if s is not None else None
        if r and os.path.exists(str(r)):
            return str(r)
    except Exception:
        pass
    r = os.path.join(DIR_TEX, 'terreno_mask.png')
    return r if os.path.exists(r) else None


def _uv_caras(ob, mat):
    """(u, v) del centro de cada poligono: media de uv_layers[0] o, sin UV, la planar del nodo TERRENO_uv_planar
    (u = x * sx + ox, v = y * sy + oy). None si no hay forma de saberlo."""
    import numpy as np
    me = ob.data
    n = len(me.polygons)
    ls = np.empty(n, np.int32)
    lt = np.empty(n, np.int32)
    me.polygons.foreach_get('loop_start', ls)
    me.polygons.foreach_get('loop_total', lt)
    orden = np.argsort(ls)
    if me.uv_layers:
        uvl = me.uv_layers[0]
        arr = np.empty(len(me.loops) * 2, np.float32)
        try:
            uvl.data.foreach_get('uv', arr)
        except Exception:
            uvl.uv.foreach_get('vector', arr)
        arr = arr.reshape(-1, 2).astype(np.float64)
        u = np.zeros(n)
        v = np.zeros(n)
        u[orden] = np.add.reduceat(arr[:, 0], ls[orden])
        v[orden] = np.add.reduceat(arr[:, 1], ls[orden])
        return u / np.maximum(lt, 1), v / np.maximum(lt, 1)
    nodo = mat.node_tree.nodes.get('TERRENO_uv_planar') if mat.node_tree else None
    if nodo is None:
        return None
    sx, sy = float(nodo.inputs[1].default_value[0]), float(nodo.inputs[1].default_value[1])
    ox, oy = float(nodo.inputs[2].default_value[0]), float(nodo.inputs[2].default_value[1])
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).astype(np.float64)
    mw = np.array(ob.matrix_world, dtype=np.float64)
    cw = co @ mw[:3, :3].T + mw[:3, 3]
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    x = np.zeros(n)
    y = np.zeros(n)
    x[orden] = np.add.reduceat(cw[lv, 0], ls[orden])
    y[orden] = np.add.reduceat(cw[lv, 1], ls[orden])
    x /= np.maximum(lt, 1)
    y /= np.maximum(lt, 1)
    return x * sx + ox, y * sy + oy


def roca_caras_mascara(ob, umbral=0.5, nz_extra=0.35, ruta_mask=None, voltear=True):
    """Caras de roca del terreno por el canal A de la mascara por texel (bool por poligono; solo caras con MAT_terreno).
    roca = A(centro de la cara) > umbral  o  nz < nz_extra (paredes casi verticales que la mascara de 1 m no resuelve).
    Mismo contrato que color_ac.roca_caras(ob). Si no hay mascara ni UV posible, devuelve solo el criterio nz."""
    import numpy as np
    me = ob.data
    n = len(me.polygons)
    if n == 0:
        return np.zeros(0, bool)
    pm = np.empty(n, np.int32)
    me.polygons.foreach_get('material_index', pm)
    slots = [k for k, m in enumerate(me.materials) if m is not None and m.name == ROCA_BASE]
    es_ter = np.isin(pm, slots)
    if not es_ter.any():
        return es_ter
    mat = bpy.data.materials.get(ROCA_BASE)
    pn = np.empty(n * 3, np.float32)
    me.polygons.foreach_get('normal', pn)
    m3 = np.array(ob.matrix_world.to_3x3(), dtype=np.float64)
    try:
        nw = pn.reshape(-1, 3).astype(np.float64) @ np.linalg.inv(m3)
    except np.linalg.LinAlgError:
        nw = pn.reshape(-1, 3).astype(np.float64) @ m3.T
    nz = nw[:, 2] / np.maximum(np.linalg.norm(nw, axis=1), 1e-12)
    if voltear:
        nz = np.where(nz < -0.05, -nz, nz)
    roca = nz < float(nz_extra)
    ruta = ruta_mask or (_ruta_mascara(mat) if mat is not None else None)
    A = _canal_a_mascara(ruta) if ruta else None
    uv = _uv_caras(ob, mat) if (A is not None and mat is not None) else None
    if A is not None and uv is not None:
        h, w = A.shape
        u, v = uv
        ix = np.clip(np.floor(u * w).astype(np.int64), 0, w - 1)
        iy = np.clip(np.floor(v * h).astype(np.int64), 0, h - 1)
        roca = roca | (A[iy, ix] > float(umbral))
    return es_ter & roca
