"""Pase de enriquecimiento de materiales de Porto Corsa (Cars 2).

Abre porto_corsa.blend, inyecta variacion sutil procedural (patina, desgaste,
hiladas de tejas, despiece de piedra) en los materiales de arquitectura y
guarda el blend en la MISMA ruta.

Idempotente: cada arbol de nodos tocado se marca con un nodo name='MEJORADO'
y se salta en pasadas posteriores.

Ejecutar:
  blender --background --python mejorar_materiales.py            (blend real)
  blender --background --python mejorar_materiales.py -- <ruta>  (otro blend)

Estilo Cars 2: saturado y limpio; la variacion es MUY sutil (multiply
0.12-0.18, bump 0.25-0.3 con Distance corto), nada de ruido fuerte.
"""
import bpy
import random
import sys

BLEND_REAL = r"E:\Escritorio\claude-pc\arnau-aseto-corsa\03_blender\porto_corsa.blend"

# (b) filtro de materiales objetivo
PREFIJOS = ("MAT_CASAS_", "MAT_CASINO_", "MAT_PUENTES_", "MAT_EDIF",
            "MAT_HOTEL", "MAT_AYTO", "MAT_CAMPANILE", "MAT_piedra")
EXCLUIR = ("vidrio", "cristal", "glass", "luz", "emis", "persiana")
CLAVES_TEJADO = ("teja", "tejado", "roof")
CLAVES_PIEDRA = ("piedra", "stone", "dovela")


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


def mejorar_blend(ruta):
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
    bpy.ops.wm.save_as_mainfile(filepath=ruta)   # (la pintura de coches se guarda aunque no haya otros cambios)
    print("MEJORAR_MATERIALES: tocados=%d saltados=%d" % (len(tocados), saltados))
    for n in tocados:
        print("  +", n)
    print("Guardado:", ruta)
    return tocados


if __name__ == '__main__':
    argv = sys.argv
    ruta = BLEND_REAL
    if '--' in argv:
        extra = argv[argv.index('--') + 1:]
        if extra:
            ruta = extra[0]
    mejorar_blend(ruta)
