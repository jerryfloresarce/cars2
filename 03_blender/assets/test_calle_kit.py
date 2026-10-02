"""test_calle_kit.py — construye el muestrario del kit de calle, renderiza
previews/calle_kit.png (EEVEE, 960x720) y guarda blend/calle_kit.blend.
Comprueba ademas que cada pieza queda por debajo de 1500 tris.

Ejecutar:
& "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background
  --factory-startup --python ".../03_blender/assets/test_calle_kit.py"
"""

import importlib.util
import math
import os
import traceback

import bpy
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    # escena totalmente vacia
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    ruta = os.path.join(BASE, 'calle_kit.py')
    spec = importlib.util.spec_from_file_location('calle_kit', ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    escena = bpy.context.scene
    col = bpy.data.collections.new('CALLE_ASSET')
    escena.collection.children.link(col)

    raiz = mod.build(col, seed=7)
    assert raiz is not None, 'build() no devolvio raiz'

    # presupuesto: <=1500 tris por pieza (agrupado por raiz de cada pieza)
    def tope(ob):
        t = ob
        while t.parent is not None and t.parent.name != raiz.name:
            t = t.parent
        return t.name

    grupos = {}
    total = 0
    for ob in col.all_objects:
        if ob.type != 'MESH':
            continue
        ob.data.calc_loop_triangles()
        n = len(ob.data.loop_triangles)
        total += n
        grupos[tope(ob)] = grupos.get(tope(ob), 0) + n
    for nombre in sorted(grupos):
        print('  pieza %-28s %5d tris' % (nombre, grupos[nombre]))
        assert grupos[nombre] <= 1500, \
            'pieza %s supera 1500 tris (%d)' % (nombre, grupos[nombre])

    # camara
    cam_d = bpy.data.cameras.new('CAM_preview')
    cam_d.lens = 30
    cam = bpy.data.objects.new('CAM_preview', cam_d)
    escena.collection.objects.link(cam)
    cam.location = Vector((8.8, 12.6, 5.0))
    mira = Vector((-0.2, 0.2, 2.1))
    cam.rotation_euler = (mira - cam.location).to_track_quat('-Z', 'Y').to_euler()
    escena.camera = cam

    # sol mediterraneo
    sol_d = bpy.data.lights.new('SOL', type='SUN')
    sol_d.energy = 3.2
    sol_d.color = (1.0, 0.96, 0.90)
    try:
        sol_d.angle = math.radians(1.5)
    except AttributeError:
        pass
    sol = bpy.data.objects.new('SOL', sol_d)
    escena.collection.objects.link(sol)
    sol.rotation_euler = (math.radians(-52), 0.0, math.radians(-35))

    # cielo uniforme
    mundo = bpy.data.worlds.new('CIELO')
    try:
        mundo.use_nodes = True
    except AttributeError:
        pass
    fondo = None
    if getattr(mundo, 'node_tree', None):
        for n in mundo.node_tree.nodes:
            if n.type == 'BACKGROUND':
                fondo = n
                break
    if fondo is not None:
        fondo.inputs[0].default_value = (0.40, 0.66, 0.95, 1.0)
        fondo.inputs[1].default_value = 1.1
    else:
        mundo.color = (0.40, 0.66, 0.95)
    escena.world = mundo

    # render EEVEE 960x720
    for motor in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            escena.render.engine = motor
            break
        except TypeError:
            continue
    escena.render.resolution_x = 960
    escena.render.resolution_y = 720
    escena.render.resolution_percentage = 100
    try:
        escena.view_settings.view_transform = 'Standard'
    except TypeError:
        pass

    dir_prev = os.path.join(BASE, 'previews')
    os.makedirs(dir_prev, exist_ok=True)
    png = os.path.join(dir_prev, 'calle_kit.png')
    escena.render.filepath = png
    escena.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    assert os.path.isfile(png), 'no se genero el PNG'

    dir_blend = os.path.join(BASE, 'blend')
    os.makedirs(dir_blend, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(dir_blend, 'calle_kit.blend'))

    mallas = sum(1 for ob in col.all_objects if ob.type == 'MESH')
    print('== TEST OK == mallas: %d, tris totales: %d' % (mallas, total))


try:
    main()
except Exception:
    traceback.print_exc()
    os._exit(1)
