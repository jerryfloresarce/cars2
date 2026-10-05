# -*- coding: utf-8 -*-
"""capturas_ab.py - capturas ANTES/DESPUES desde las MISMAS camaras (congeladas en JSON), modo Blender o "modo AC".

  bash 03_blender/_rev/blender_cola.sh --python 03_blender/_rev/capturas_ab.py -- \
       --blend <escena.blend> --geom <geometria.json> --set <BASE|bloque|bloque+bloque|TODAS|lista,de,prefijos> \
       --out <dir> [--camaras cams.json | --guardar-camaras cams.json [--anadir | --forzar]] [--solo 49,50] [--res 1600x900]
       [--modo-ac] [--sin-base]
Sin --camaras: calcula las tomas con tomas_capturas.construir_tomas (mismas formulas que renderizar_capturas.py), pasa
  por camara_segura UNA sola vez (exentas: piloto, postal, desde_pista, tunel...) y guarda loc/tgt/lens en --guardar-camaras.
Con --camaras: lee loc/tgt/lens TAL CUAL y no mueve nada; si una camara queda dentro de geometria lo avisa en ab.log y
  renderiza igual (regla 16 del plan: toma nueva con otro nombre, nunca mover la vieja).
--guardar-camaras sobre un JSON que YA EXISTE se NIEGA (exit 2, antes de renderizar): las camaras congeladas no se pisan.
  --anadir: renderiza y anade SOLO las tomas que no esten en el JSON (las que ya estan se saltan y se avisa; nunca se reescriben).
  --forzar: sustituye a sabiendas las tomas pedidas (conserva las demas); queda anotado en _meta.actualizaciones.
--modo-ac (aproximacion honesta de AC "a pelo", NO es AC): sin sombras de suelo/vegetacion (castShadows=0 como
  04_export/kn5_writer_opt.py GROUND_PREFIXES/DECO_SIN_SOMBRA tras los renombres de exportar_ac.py), sin AO/raytracing
  de EEVEE, caras de roca de MAT_terreno separadas como hace el writer (color_ac.separar_roca_terreno, solo ejecutado),
  y cada material reducido a lo que escribe el writer (analizar_material + construir_textura: color plano o tile tintado
  de 512 px con mapping Object*escala FLAT/BOX, alfa; sin bump, sin normal, sin procedurales). NO se aplica la
  calibracion color_ac.calibrar_todos() (el writer si, kn5_writer_opt.py l.305): esos colores compensan la luz de AC
  (gamma de Kunos, sol, autoexposicion) y bajo la luz de Blender darian una imagen falsa. RATIFICADO por el coordinador
  (04/10/2026): el modo AC se juzga con los colores SIN calibrar; es determinista (diff 0 entre dos pasadas).
Misma luz, mundo y view transform (Standard, exposicion 0.12) que renderizar_capturas.py. Escribe <out>/<toma>.png,
<out>/ab.log y <out>/arboles.json (posiciones de VEG_/OLI_ para medir_capturas.siluetas_20_120). Nunca guarda el blend.
"""
import argparse
import datetime
import json
import math
import os
import re
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

# ------------------------------------------------------------------ sets de tomas (FASE_VISUAL_PLAN.md secc. 1 y por bloque)
BASE = ['01_aerea_general',
        '49_piloto_s300', '50_piloto_s800', '51_piloto_s1700', '52_piloto_s2900', '53_piloto_s3400', '54_piloto_s4150',
        '55_postal_tunel_salida', '56_postal_cima_bahia', '57_postal_viaducto', '58_postal_loews',
        '59_postal_recta_puerto', '59b_postal_recta_puerto_s5150',
        '07_tierra_subida', '13_puente_alto', '21_montana_dentro_del_lazo', '36_roca_casino_general',
        '60_puerto_llanta_cenital', '61_orilla_piloto_s150', '62_tribuna_piloto_s5100', '63_horizonte_piloto_s2200']
SETS = {
    'paleta': ['05_pueblo_subida', '06_pueblo_calle', '09_bajada_recta', '14_puente_mar', '16_retorno_chicane',
               '21_montana_dentro_del_lazo', '22_viaducto_arcos_altos', '39_pueblo_calles_aerea'],
    'roca': ['02_meta_y_puerto', '13_puente_alto', '17_tunel_salida_exterior', '19_penon_casino_foto', '20_penon_casino_cerca',
             '32_montana_coche_lado', '33_montana_coche_desde_pista', '33b_montana_coche_34', '34_roca_lazo_general',
             '36_roca_casino_general', '45_roca_lazo_puente', '46_roca_lazo_muelle'],
    'relieve': ['05_pueblo_subida', '07_tierra_subida', '08_tierra_cima', '09_bajada_recta', '14_puente_mar', '16_retorno_chicane',
                '21_montana_dentro_del_lazo', '22_viaducto_arcos_altos', '39_pueblo_calles_aerea', '42_paddock_hotel'],
    'pueblo': ['05_pueblo_subida', '06_pueblo_calle', '10_casino_sector', '39_pueblo_calles_aerea', '40_pueblo_travesia'],
    'vegetacion': ['01_aerea_general', '07_tierra_subida', '10_casino_sector', '21_montana_dentro_del_lazo', '34_roca_lazo_general'],
    'agua_costa': ['02_meta_y_puerto', '14_puente_mar', '16_retorno_chicane', '22_viaducto_arcos_altos', '36_roca_casino_general',
                   '46_roca_lazo_muelle', '47_yates_vip', '47b_yates_desde_pista', '60_puerto_llanta_cenital', '61_orilla_piloto_s150'],
    'publico': ['02_meta_y_puerto', '29_boxes_desde_pista', '30_boxes_tribuna_aerea', '47_yates_vip', '27_coche_camara_0',
                '27_coche_camara_1', '27_coche_camara_2', '28_helicoptero_camara', '12_rotonda_loews',
                '25_paseo_mirador_desde_pista', '62_tribuna_piloto_s5100'],
    'relleno': ['09_bajada_recta', '21_montana_dentro_del_lazo', '26_paseo_y_parking_desde_abajo', '42_paddock_hotel',
                '48_ermita_sendero', '10_casino_sector', '39_pueblo_calles_aerea'],
    'horizonte': ['14_puente_mar', '16_retorno_chicane', '13_puente_alto', '08_tierra_cima', '19_penon_casino_foto',
                  '63_horizonte_piloto_s2200'],
    'carificacion': ['10_casino_sector', '19_penon_casino_foto', '20_penon_casino_cerca', '36_roca_casino_general',
                     '53_piloto_s3400', '58_postal_loews', '02_meta_y_puerto', '29_boxes_desde_pista'],   # plan secc. 10: 53, 58, 02/29
    'csp': ['02_meta_y_puerto', '29_boxes_desde_pista', '12_rotonda_loews', '28_helicoptero_camara', '53_piloto_s3400'],
}
# camara_segura NO se aplica a estas (ademas de su propia lista NO_TOCAR): las postales son vistas desde el coche
SIN_CAMARA_SEGURA = ('postal',)

# ------------------------------------------------------------------ reglas de AC (copiadas, no importadas: 04_export esta cerrado)
# kn5_writer_opt.py l.69 (TEX_SIZE), l.75 (GROUND_PREFIXES), l.80-81 (DECO_SIN_SOMBRA, DECO_MAT_SIN_SOMBRA); comprobado 04/10 tarde
GROUND_PREFIXES = ('1ROAD', '1DIRT', '1KERB', '1GRASS', '2GRASS', '1PIT', 'AGUA', 'MARCA', 'linea')
DECO_SIN_SOMBRA = ('VEG_', 'OLI_')
DECO_MAT_SIN_SOMBRA = ('MAT_VEG_', 'MAT_OLI_')
TEX_SIZE = 512
# exportar_ac.py l.61 (1ROAD_pista), l.69-71 (RENOMBRAR) y l.92-149 (1ROAD_/1DIRT_/2GRASS_/BORDILLO_): renombres que
# convierten un objeto de la escena en SUELO (castShadows = 0)
RENOMBRAR = {'PIT_LANE': '1PIT_pit', 'PIANOS': '1KERB_pianos', 'TERRENO': '1GRASS_terreno',
             'LINEA_SALIDA': 'linea_salida_visual', 'PISTA': '1ROAD_pista'}
A_1ROAD = ('MIRADOR_pasarela', 'MIRADOR_parking_cubierta', 'TUNEL_suelo', 'PUERTO_dique_malla', 'CAMINO_asfalto', 'CAMINO_adoquin',
           'CAMINO_muelle', 'CAMINO_marcas', 'CAMINO_calle', 'CAMINO_enlace', 'CAMINO_travesia', 'CAMINO_rampa', 'CAMINO_union',
           'ACERA_', 'PPUEBLO_carretera', 'PPUEBLO_plaza', 'PENON_carretera', 'PENON_plazas', 'CALLE_plaza')
A_1DIRT = ('CAMINO_tierra',)
A_2GRASS = ('ARCEN',)


def nombre_ac(ob):
    """Nombre que tendria el objeto en la escena de export (solo los renombres que llevan a prefijo de suelo)."""
    n = ob.name
    if n in RENOMBRAR:
        return RENOMBRAR[n]
    if n.startswith(A_2GRASS):
        return '2GRASS_' + n.lower()
    if n.startswith(A_1DIRT):
        return '1DIRT_' + n.lower()
    if n.startswith(A_1ROAD):
        return '1ROAD_' + n.lower()
    if n.startswith('BORDILLO_') and ob.type == 'MESH':
        ver = sum(1 for f in ob.data.polygons if abs(f.normal.z) < 0.5)
        return ('1WALL_' if ver > 0.5 * max(1, len(ob.data.polygons)) else '1KERB_') + n.lower()
    return n


def categoria_sombra(ob):
    """'suelo' | 'veg' | 'mat_veg' | 'mixto' | None segun las reglas del writer (castShadows = 0 en los 3 primeros)."""
    if nombre_ac(ob).startswith(GROUND_PREFIXES):
        return 'suelo'
    if ob.name.startswith(DECO_SIN_SOMBRA):
        return 'veg'
    mats = [m for m in ob.data.materials if m is not None] if ob.type == 'MESH' else []
    if mats:
        ss = [m.name.startswith(DECO_MAT_SIN_SOMBRA) for m in mats]
        if all(ss):
            return 'mat_veg'
        if any(ss):
            return 'mixto'
    return None


# --- copia fiel de kn5_writer_opt.py: srgb_to_lin / lin_to_srgb (l.139-148), imagen_lineal (l.191-213),
#     analizar_material (l.221-266), construir_textura (l.267-291)   [lineas comprobadas con grep el 04/10 tarde]
def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, np.power((c + 0.055) / 1.055, 2.4)).astype(np.float32)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float32), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055).astype(np.float32)


_img_cache = {}


def imagen_lineal(img, size):
    if img.name in _img_cache:
        return _img_cache[img.name]
    res = None
    try:
        n = len(img.pixels)
        w, h = img.size
        if n and w and h:
            buf = np.empty(n, np.float32)
            img.pixels.foreach_get(buf)
            rgb = buf.reshape(h, w, -1)[::-1, :, :3]          # Blender guarda la fila 0 abajo
            lin = srgb_to_lin(rgb)
            while lin.shape[0] > size and lin.shape[0] % 2 == 0 and lin.shape[1] % 2 == 0:
                lin = lin.reshape(lin.shape[0] // 2, 2, lin.shape[1] // 2, 2, 3).mean(axis=(1, 3))
            res = lin.astype(np.float32)
    except Exception as e:  # noqa
        print('AVISO: no se pudo leer la imagen', img.name, e)
    _img_cache[img.name] = res
    return res


def _socket(node, identifier):
    for s in node.inputs:
        if s.identifier == identifier:
            return s
    return None


def analizar_material(m):
    info = {'name': m.name, 'color': tuple(float(c) for c in m.diffuse_color[:3]), 'alpha': 1.0,
            'img': None, 'gain': 1.0, 'factor': 1.0, 'scale': 1.0, 'proj': 'FLAT'}
    nt = m.node_tree
    if not nt:
        return info
    principled = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if principled:
        a = principled.inputs['Alpha']
        if not a.is_linked:
            info['alpha'] = float(a.default_value)
        bc = principled.inputs['Base Color']
        if not bc.is_linked:
            info['color'] = tuple(float(c) for c in bc.default_value[:3])
    tex = None
    for n in nt.nodes:
        if (n.bl_idname == 'ShaderNodeTexImage' and n.image
                and n.image.colorspace_settings.name != 'Non-Color' and n.outputs['Color'].is_linked):
            tex = n
            break
    if tex is None:
        return info
    info['img'] = tex.image
    info['proj'] = tex.projection
    gan = nt.nodes.get('TEX_ganancia')
    if gan and gan.bl_idname == 'ShaderNodeMix':
        sb = _socket(gan, 'B_Color')
        if sb is not None and not sb.is_linked:
            info['gain'] = float(sb.default_value[0])
    mul = nt.nodes.get('TEX_multiplicar')
    if mul and mul.bl_idname == 'ShaderNodeMix':
        sf = _socket(mul, 'Factor_Float')
        info['factor'] = float(sf.default_value) if (sf is not None and not sf.is_linked) else 0.6
    mp = nt.nodes.get('TEX_mapping')
    if not (mp and mp.bl_idname == 'ShaderNodeMapping'):
        vin = tex.inputs['Vector']
        if vin.is_linked and vin.links[0].from_node.bl_idname == 'ShaderNodeMapping':
            mp = vin.links[0].from_node
    if mp and mp.bl_idname == 'ShaderNodeMapping':
        info['scale'] = float(mp.inputs['Scale'].default_value[0])
    return info


def textura_tintada(info):
    """Pixeles sRGB (H, W, 3) float 0-1 del tile tintado de 512 px, igual que construir_textura; None = color plano."""
    lin = imagen_lineal(info['img'], TEX_SIZE) if info['img'] is not None else None
    if lin is None:
        return None
    color = np.array(info['color'], np.float32).reshape(1, 1, 3)
    f = info['factor']
    gain = (1.0 / np.maximum(lin.mean(axis=(0, 1)), 1e-4)).astype(np.float32).reshape(1, 1, 3)
    rgb = lin_to_srgb(color * (1.0 - f + f * lin * gain))
    return ((rgb * 255.0 + 0.5).astype(np.uint8)).astype(np.float32) / 255.0     # cuantizado a 8 bits como el PNG


# ------------------------------------------------------------------ modo AC
def aplicar_modo_ac(sc, log):
    """Reduce la escena a lo que llega al KN5 (ver docstring). Devuelve un dict con las cifras para ab.log."""
    t0 = time.time()
    st = {'sombras': {'suelo': 0, 'veg': 0, 'mat_veg': 0, 'mixto': 0}, 'mixtos': [], 'materiales': {'plano': 0, 'tile': 0, 'alfa': 0, 'sin_imagen_legible': 0},
          'eevee': {}, 'uv_propias_con_imagen': 0, 'roca_terreno': None}
    lib = bpy.data.collections.get('LIB')
    en_lib = set(o.name for o in lib.all_objects) if lib else set()
    # 0) como el writer (kn5_writer_opt.py l.753): las caras de roca de MAT_terreno pasan a MAT_terreno_roca
    #    (color_ac.separar_roca_terreno l.517: copia del material con diffuse_color = ROCA_COLOR). Solo se EJECUTA color_ac
    #    (04_export esta cerrado); NO se aplica calibrar_todos() (writer l.305): esos colores estan pre-compensados para la
    #    luz de AC (gamma, sol 170/160/140, autoexposicion) y con la luz de Blender darian una imagen falsa.
    #    RATIFICADO por el coordinador (04/10): el modo AC se juzga con colores sin calibrar.
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(AQUI)), '04_export'))
        import color_ac
        roca = color_ac.separar_roca_terreno()
        st['roca_terreno'] = {'caras': int(sum(roca.values())), 'objetos': len(roca), 'material': color_ac.ROCA_MAT}
        # F1 r3 (PARCHES_F1_materiales.md 10.2 = decision del director r2 n.3): la pared del desmonte en el proxy AC = caliza
        # media con su sombra propia (materiales_roca.color_roca_terreno_ac = caliza_gris_calido x ao_pared x AO media) + tile
        # de caliza a 3 m, lo mismo que pide P1 al writer (PETICIONES_04_EXPORT.md). roca_caras SIGUE siendo la del writer de
        # hoy (nz < 0.5 / atributo 'roca'): la mitad "caras por el canal A" de P1 queda [W]. El proxy se ADELANTA al writer solo
        # en color + imagen de MAT_terreno_roca; mientras P1 no se aplique, el KN5 real sale con ROCA_COLOR literal + tile de
        # hierba (anotado en PETICIONES P1 y en ab.log).
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(AQUI), 'assets'))
            import materiales_roca
            m_r = bpy.data.materials.get(color_ac.ROCA_MAT)
            if m_r is not None and m_r.node_tree:
                m_r.diffuse_color = tuple(materiales_roca.color_roca_terreno_ac()) + (1.0,)
                tex = next((n for n in m_r.node_tree.nodes if n.bl_idname == 'ShaderNodeTexImage' and n.image
                            and n.image.colorspace_settings.name != 'Non-Color' and n.outputs['Color'].is_linked), None)
                ruta = os.path.join(os.path.dirname(AQUI), 'texturas', 'caliza_d.png')
                if tex is not None and os.path.exists(ruta):
                    tex.image = bpy.data.images.load(ruta, check_existing=True)
                    tex.image.colorspace_settings.name = 'sRGB'
                    mp = m_r.node_tree.nodes.get('TEX_mapping')
                    if mp is not None:
                        mp.inputs['Scale'].default_value = (1.0 / 3.0,) * 3
                log('modo AC: MAT_terreno_roca = materiales_roca.color_roca_terreno_ac %s + caliza_d 3 m (proxy adelantado a P1 '
                    'en color+imagen; caras por nz/atributo como el writer de hoy)' % (tuple(round(c, 3) for c in m_r.diffuse_color[:3]),))
                st['roca_terreno']['color_p1'] = [round(float(c), 3) for c in m_r.diffuse_color[:3]]
        except Exception as e:  # noqa
            log('modo AC: materiales_roca no disponible (%s): ROCA_COLOR literal' % e)
    except Exception as e:  # noqa
        st['roca_terreno'] = 'ERR %s' % e
    # 1) sombras: castShadows = 0 -> el objeto no proyecta sombra
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.name in en_lib:
            continue
        cat = categoria_sombra(ob)
        if cat is None:
            continue
        if cat == 'mixto':
            # el writer lo partiria por material; aqui no se parte: solo se quita la sombra si la mayoria de los
            # slots son MAT_VEG_/MAT_OLI_ (hoy: 0 mallas mixtas en la escena; se deja constancia)
            ss = [m.name.startswith(DECO_MAT_SIN_SOMBRA) for m in ob.data.materials if m is not None]
            st['mixtos'].append(ob.name)
            if sum(ss) * 2 <= len(ss):
                continue
        ob.visible_shadow = False
        st['sombras'][cat] += 1
    # 2) materiales: color plano (8x8 en el KN5) o tile tintado de 512 con mapping Object*escala FLAT/BOX
    mats_con_uv = set(x.name for me in bpy.data.meshes if me.uv_layers and me.users for x in me.materials if x)
    for m in bpy.data.materials:
        if not m.users or not m.node_tree:
            continue
        info = analizar_material(m)
        tile = textura_tintada(info)
        if info['img'] is not None and tile is None:
            st['materiales']['sin_imagen_legible'] += 1
        if tile is not None and m.name in mats_con_uv:
            st['uv_propias_con_imagen'] += 1       # el writer usaria las UV de la malla; aqui mapping Object (aviso)
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        out.location = (300, 0)
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        # ksPerPixel: ksAmbient 0.45, ksDiffuse 0.55, ksSpecular 0.15, ksSpecularEXP 24 -> brillo bajo y ancho
        # F1 r3 (PARCHES_F1_materiales.md 10.1): ksPerPixel (ksSpecular 0.15, exp 24) no tiene Fresnel; con 0.3 las caras a vista
        # rasante (McLaren en 49, roca del lazo en 13) devolvian el cielo = un cian que AC no tendra
        for nombre, val in (('Roughness', 0.9), ('Specular IOR Level', 0.0), ('Metallic', 0.0), ('Coat Weight', 0.0),
                            ('Emission Strength', 0.0), ('Alpha', info['alpha'])):
            if nombre in bsdf.inputs:
                bsdf.inputs[nombre].default_value = val
        if tile is None:
            bsdf.inputs['Base Color'].default_value = (*info['color'], 1.0)
            st['materiales']['plano'] += 1
        else:
            h, w = tile.shape[:2]
            img = bpy.data.images.new('AC_tex_' + m.name, w, h, alpha=False, float_buffer=False)
            img.colorspace_settings.name = 'sRGB'
            rgba = np.concatenate([tile[::-1], np.ones((h, w, 1), np.float32)], axis=2)   # fila 0 abajo en Blender
            img.pixels.foreach_set(rgba.ravel())
            img.update()
            tco = nt.nodes.new('ShaderNodeTexCoord'); tco.location = (-800, 0)
            mp = nt.nodes.new('ShaderNodeMapping'); mp.location = (-600, 0)
            mp.inputs['Scale'].default_value = (info['scale'], info['scale'], info['scale'])
            tex = nt.nodes.new('ShaderNodeTexImage'); tex.location = (-350, 0)
            tex.image = img
            tex.projection = info['proj']
            if info['proj'] == 'BOX':
                tex.projection_blend = 0.0            # el writer elige UN eje por cara (argmax |n|), sin mezcla
            tex.extension = 'REPEAT'
            tex.interpolation = 'Linear'
            nt.links.new(tco.outputs['Object'], mp.inputs['Vector'])
            nt.links.new(mp.outputs['Vector'], tex.inputs['Vector'])
            nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
            st['materiales']['tile'] += 1
        if info['alpha'] < 0.999:
            try:
                m.surface_render_method = 'BLENDED'
            except Exception:
                m.blend_method = 'BLEND'
            st['materiales']['alfa'] += 1
    # 3) sin AO ni reflejos de pantalla (en Blender 5.1 no existe use_gtao: el AO de EEVEE es use_raytracing/use_fast_gi)
    for attr, val in (('use_raytracing', False), ('use_fast_gi', False), ('use_gtao', False)):
        if hasattr(sc.eevee, attr):
            antes = getattr(sc.eevee, attr)
            try:
                setattr(sc.eevee, attr, val)
                st['eevee'][attr] = '%s -> %s' % (antes, val)
            except Exception as e:
                st['eevee'][attr] = 'ERR %s' % e
    st['segundos'] = round(time.time() - t0, 1)
    log('MODO AC: roca de terreno %s; sombras quitadas %s; mallas mixtas (aprox.) %d; materiales %s; uv propias con imagen %d; '
        'eevee %s; %.1fs' % (json.dumps(st['roca_terreno']), json.dumps(st['sombras']), len(st['mixtos']), json.dumps(st['materiales']),
                             st['uv_propias_con_imagen'], json.dumps(st['eevee']), st['segundos']))
    return st


# ------------------------------------------------------------------ utilidades
def dentro_de_geometria(sc, dg, p):
    """True si p esta bajo una superficie (rayo hacia arriba que choca con una cara vista por delante)."""
    ok, loc, nrm, idx, ob, mw = sc.ray_cast(dg, Vector(p), Vector((0, 0, 1)), distance=3000.0)
    if ok and nrm.z < 0.0:
        return False, None            # techo (puente, alero, boveda del tunel): no estamos dentro
    return ok, (ob.name if ok and ob is not None else None)


def exportar_arboles(ruta):
    lib = bpy.data.collections.get('LIB')
    en_lib = set(o.name for o in lib.all_objects) if lib else set()
    out = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.name in en_lib:
            continue
        es_veg = ob.name.startswith(DECO_SIN_SOMBRA)
        if not es_veg:
            mats = [m for m in ob.data.materials if m is not None]
            es_veg = bool(mats) and all(m.name.startswith(DECO_MAT_SIN_SOMBRA) for m in mats)
        if es_veg:
            t = ob.matrix_world.translation
            out.append({'n': ob.name, 'tipo': re.sub(r'[\.\d]+$', '', ob.name), 'xyz': [round(t.x, 2), round(t.y, 2), round(t.z, 2)]})
    json.dump(out, open(ruta, 'w', encoding='utf-8'))
    return len(out)


def resolver_set(nombre_set, todas, sin_base):
    """Lista de nombres de toma a partir de 'BASE', 'bloque', 'a+b', 'TODAS' o prefijos separados por comas."""
    nombres = [t[0] for t in todas]
    if nombre_set is None:
        return list(nombres), []
    quiero = [] if sin_base else list(BASE)
    avisos = []
    for tok in re.split(r'[+,]', nombre_set):
        tok = tok.strip()
        if not tok:
            continue
        low = tok.lower()
        if low == 'base':
            quiero = quiero or list(BASE)
            continue
        if low == 'todas':
            quiero = list(nombres)
            continue
        if low in SETS:
            quiero.extend(SETS[low])
            continue
        hits = [n for n in nombres if n.startswith(tok)]
        if not hits:
            avisos.append('prefijo "%s" no corresponde a ninguna toma' % tok)
        quiero.extend(hits)
    vistos = set()
    orden = []
    for n in quiero:
        if n not in vistos:
            vistos.add(n)
            orden.append(n)
    faltan = [n for n in orden if n not in nombres]
    if faltan:
        avisos.append('tomas del set que no existen en esta escena: %s' % faltan)
    return [n for n in orden if n in nombres], avisos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--blend', required=True)
    ap.add_argument('--geom', required=True)
    ap.add_argument('--set', default=None, help='BASE (defecto sin --camaras) | bloque | a+b | TODAS | prefijos')
    ap.add_argument('--out', required=True)
    ap.add_argument('--camaras')
    ap.add_argument('--guardar-camaras')
    ap.add_argument('--solo', default='')
    ap.add_argument('--res', default='1600x900')
    ap.add_argument('--modo-ac', action='store_true')
    ap.add_argument('--sin-base', action='store_true')
    ap.add_argument('--anadir', action='store_true', help='con --guardar-camaras existente: anade solo las tomas que falten')
    ap.add_argument('--forzar', action='store_true', help='con --guardar-camaras existente: sustituye las tomas pedidas (a sabiendas)')
    A = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if A.camaras and A.guardar_camaras:
        sys.exit('ERROR: --camaras y --guardar-camaras son excluyentes')
    if A.anadir and A.forzar:
        sys.exit('ERROR: --anadir y --forzar son excluyentes')
    if (A.anadir or A.forzar) and not A.guardar_camaras:
        sys.exit('ERROR: --anadir/--forzar solo tienen sentido con --guardar-camaras')
    rx, ry = (int(v) for v in A.res.lower().replace(',', 'x').split('x'))
    A.out = os.path.abspath(A.out)          # Blender resuelve render.filepath relativo al .blend, no al cwd
    t0 = time.time()
    os.makedirs(A.out, exist_ok=True)
    flog = open(os.path.join(A.out, 'ab.log'), 'a', encoding='utf-8')

    def log(msg):
        print(msg)
        flog.write(msg + '\n')
        flog.flush()
    log('== %s | blend %s | geom %s | set %s | res %dx%d | modo %s | camaras %s%s' % (
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), A.blend, A.geom, A.set, rx, ry,
        'AC' if A.modo_ac else 'normal', A.camaras or ('(calcular -> %s)' % A.guardar_camaras),
        ' [--anadir]' if A.anadir else (' [--forzar]' if A.forzar else '')))
    # camaras congeladas: un JSON existente NO se pisa (regla 16 del plan). Se decide ANTES de abrir el blend y renderizar.
    existentes = {}
    if A.guardar_camaras and os.path.exists(A.guardar_camaras):
        existentes = {k: v for k, v in json.load(open(A.guardar_camaras, encoding='utf-8')).items() if not k.startswith('_')}
        if not (A.anadir or A.forzar):
            log('ERROR: %s ya existe (%d tomas congeladas) y --guardar-camaras lo reescribiria. Las camaras congeladas no se pisan: '
                'usa --camaras %s para renderizar con ellas (el "despues"), --anadir para anadir SOLO las tomas que falten, '
                'o --forzar para sustituir las pedidas a sabiendas.' % (A.guardar_camaras, len(existentes), A.guardar_camaras))
            flog.close()
            sys.exit(2)
    G = json.load(open(A.geom, encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(A.blend))
    sc = bpy.context.scene
    # mismos ajustes que renderizar_capturas.py / construir_pista.py (plan secc. 3.6: capturas_ab fuerza los mismos)
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.12
    sol = bpy.data.objects.get('SOL')
    log('escena: motor %s, muestras %s, sol %s, mundo %s, abierta en %.1fs' % (
        sc.render.engine, getattr(sc.eevee, 'taa_render_samples', '?'),
        ('E=%.2f rot=(%.0f,%.0f,%.0f)' % (sol.data.energy, *[math.degrees(v) for v in sol.rotation_euler])) if sol else 'SIN SOL',
        sc.world.name if sc.world else None, time.time() - t0))

    import tomas_capturas
    desc = tomas_capturas.TOMAS_NUEVAS
    if A.camaras:
        cams = json.load(open(A.camaras, encoding='utf-8'))
        tomas = [(n, tuple(c['loc']), tuple(c['tgt']), float(c['lens'])) for n, c in cams.items() if not n.startswith('_')]
        quiero, avisos = (resolver_set(A.set, tomas, A.sin_base) if A.set else ([t[0] for t in tomas], []))
        movidas = {}
    else:
        import camara_segura
        calc = tomas_capturas.construir_tomas(G, bpy)
        quiero, avisos = resolver_set(A.set or 'BASE', calc, A.sin_base)
        tomas, movidas = [], {}
        for n, l, t, k in calc:
            if n not in quiero:
                continue
            if any(p in n for p in SIN_CAMARA_SEGURA):
                l2, t2 = l, t
            else:
                l2, t2 = camara_segura.asegurar(n, l, t)
            # redondeo a 0.1 mm ANTES de renderizar: lo que se renderiza es exactamente lo que guarda camaras.json
            # (asegurar devuelve Vector float32: sin tolerancia todo pareceria "movido")
            l2 = tuple(round(float(v), 4) for v in l2); t2 = tuple(round(float(v), 4) for v in t2)
            if any(abs(a - b) > 1e-3 for a, b in zip(l2 + t2, l + t)):
                movidas[n] = {'loc_original': [round(v, 4) for v in l], 'tgt_original': [round(v, 4) for v in t]}
            tomas.append((n, l2, t2, k))
    for a in avisos:
        log('AVISO set: ' + a)
    solo = [p for p in A.solo.split(',') if p]
    if solo:
        quiero = [n for n in quiero if n.startswith(tuple(solo))]
    tomas = [t for t in tomas if t[0] in quiero]
    if existentes:
        repetidas = sorted(t[0] for t in tomas if t[0] in existentes)
        if A.anadir:
            if repetidas:
                log('--anadir: se saltan %d tomas ya congeladas en %s (nunca se reescriben): %s' % (len(repetidas), A.guardar_camaras, repetidas))
            tomas = [t for t in tomas if t[0] not in existentes]
            if not tomas:
                log('ERROR: --anadir sin nada nuevo: todas las tomas pedidas ya estan congeladas en %s' % A.guardar_camaras)
                sys.exit(2)
        elif repetidas:
            log('FORZADO (--forzar): se SUSTITUYEN %d tomas congeladas en %s: %s' % (len(repetidas), A.guardar_camaras, repetidas))
        movidas = {k: v for k, v in movidas.items() if k in set(t[0] for t in tomas)}
    if not tomas:
        log('ERROR: ninguna toma seleccionada')
        sys.exit(2)
    if A.modo_ac:
        aplicar_modo_ac(sc, log)
    n_arb = exportar_arboles(os.path.join(A.out, 'arboles.json'))
    log('arboles.json: %d objetos de vegetacion' % n_arb)

    dg = bpy.context.evaluated_depsgraph_get()
    guardar = {}
    t_ren = 0.0
    for nombre, loc, tgt, lens in tomas:
        dentro, ob_dentro = dentro_de_geometria(sc, dg, loc)
        if dentro:
            log('AVISO %s: camara DENTRO de geometria (%s); no se mueve, se renderiza igual' % (nombre, ob_dentro))
        cd = bpy.data.cameras.new('AB_' + nombre)
        cd.lens = lens
        cd.clip_end = 12000
        c = bpy.data.objects.new('AB_' + nombre, cd)
        c.location = Vector(loc)
        c.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        sc.collection.objects.link(c)
        sc.camera = c
        sc.render.filepath = os.path.join(A.out, nombre + '.png')
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t1
        t_ren += dt
        log('%s %.1fs loc=(%.1f, %.1f, %.1f) tgt=(%.1f, %.1f, %.1f) lente %g%s%s' % (
            nombre, dt, *loc, *tgt, lens, ' [camara_segura la movio]' if nombre in movidas else '',
            ' [DENTRO]' if dentro else ''))
        guardar[nombre] = {'loc': list(loc), 'tgt': list(tgt), 'lens': lens}
        if nombre in movidas:
            guardar[nombre]['camara_segura'] = movidas[nombre]
        if nombre in desc:
            guardar[nombre]['desc'] = desc[nombre]
    if A.guardar_camaras:
        ahora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        meta = {'fecha': ahora, 'blend': os.path.abspath(A.blend), 'geom': os.path.abspath(A.geom), 'set': A.set or 'BASE',
                'res': [rx, ry], 'camara_segura': 'aplicada UNA vez al congelar (exentas: %s + NO_TOCAR/LIGERO de camara_segura.py); '
                'el "despues" lee loc/tgt/lens tal cual' % list(SIN_CAMARA_SEGURA), 'movidas_por_camara_segura': sorted(movidas)}
        out = {'_meta': meta}
        # si el fichero ya existe (solo se llega aqui con --anadir o --forzar) se conservan todas sus tomas: con --anadir solo
        # entran las nuevas (las repetidas se filtraron antes de renderizar); con --forzar se sustituyen las pedidas (anotado)
        if os.path.exists(A.guardar_camaras):
            viejo = json.load(open(A.guardar_camaras, encoding='utf-8'))
            out = {'_meta': dict(viejo.get('_meta', {}))}
            out.update({k: v for k, v in viejo.items() if not k.startswith('_')})
            sustituidas = sorted(k for k in guardar if k in out and not k.startswith('_'))
            out['_meta'].setdefault('actualizaciones', []).append({
                'fecha': ahora, 'modo': 'anadir' if A.anadir else 'forzar', 'tomas': sorted(guardar), 'set': A.set or 'BASE',
                'sustituidas': sustituidas})
            out['_meta']['movidas_por_camara_segura'] = sorted(set(out['_meta'].get('movidas_por_camara_segura', [])) | set(movidas))
        out.update(guardar)
        out['_meta']['n'] = len([k for k in out if not k.startswith('_')])
        os.makedirs(os.path.dirname(os.path.abspath(A.guardar_camaras)), exist_ok=True)
        json.dump(out, open(A.guardar_camaras, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        log('camaras congeladas -> %s (%d en el fichero, %d de esta pasada; movidas por camara_segura: %s)' % (
            A.guardar_camaras, out['_meta']['n'], len(guardar), sorted(movidas) or 'ninguna'))
    log('OK capturas_ab: %d tomas -> %s | render %.0fs | total %.0fs' % (len(tomas), A.out, t_ren, time.time() - t0))
    flog.close()


main()
