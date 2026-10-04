# -*- coding: utf-8 -*-
"""hacer_parches.py (v3) - crea COPIAS parcheadas de kn5_writer_opt.py y empaquetar.py (los originales no se tocan)
para probar color_ac.py, y los diff unificados exactos que van a CAMBIO_KN5_WRITER.md.
  python 04_export/_color_ac_prueba/hacer_parches.py
Salidas (en esta carpeta): kn5_writer_opt_color.py, empaquetar_color.py, kn5_writer_opt.diff, empaquetar.diff"""
import difflib
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(AQUI)
BASE_LINEA = "BASE = r'E:" + chr(92) + "Escritorio" + chr(92) + "claude-pc" + chr(92) + "arnau-aseto-corsa'\n"

WRITER = [
    ("import struct\nimport time\nimport zlib\n", "import struct\nimport sys\nimport time\nimport zlib\n"),
    (BASE_LINEA,
     BASE_LINEA
     + "# color_ac.py: recalibra color y props de shader para AC (antes el circuito salia casi blanco en el juego);\n"
       "# env COLOR_AC=0 lo desactiva (colores y SHADER_PROPS de siempre, para comparar)\n"
       "sys.path.insert(0, os.path.join(BASE, '04_export'))\n"
       "import color_ac  # noqa: E402\n"
       "USAR_COLOR_AC = os.environ.get('COLOR_AC', '1') != '0'\n"),
    ("                  'gain': 1.0, 'factor': 1.0, 'scale': 1.0, 'proj': 'FLAT'})\n    return infos\n",
     "                  'gain': 1.0, 'factor': 1.0, 'scale': 1.0, 'proj': 'FLAT'})\n"
     "    if USAR_COLOR_AC:       # color para AC (aspecto medido en Blender + modelos de luz de AC) y props por familia\n"
     "        infos = color_ac.calibrar_todos(infos)\n"
     "    return infos\n"),
    ("        w.i32(len(SHADER_PROPS))\n        for pname, val in SHADER_PROPS:\n",
     "        props = info.get('props_ac', SHADER_PROPS)   # por familia de material (color_ac.FAMILIAS)\n"
     "        w.i32(len(props))\n        for pname, val in props:\n"),
    ("    os.makedirs(os.path.dirname(OUT_KN5), exist_ok=True)\n    objs = objetos_exportables()\n",
     "    os.makedirs(os.path.dirname(OUT_KN5), exist_ok=True)\n"
     "    # color_ac: las caras de roca de MAT_terreno (mismo criterio que el nodo de Blender) pasan a MAT_terreno_roca,\n"
     "    # solo en memoria (el .blend no se guarda)\n"
     "    roca_ac = color_ac.separar_roca_terreno() if USAR_COLOR_AC else {}\n"
     "    print('color_ac: %d caras de roca -> %s %s' % (sum(roca_ac.values()), color_ac.ROCA_MAT, roca_ac))\n"
     "    objs = objetos_exportables()\n"),
    ("        'segundos': round(time.time() - t0, 1),\n    }\n",
     "        'segundos': round(time.time() - t0, 1),\n"
     "        'color_ac': color_ac.informe(infos) if USAR_COLOR_AC else 'desactivado (COLOR_AC=0)',\n"
     "        'color_ac_roca_terreno': roca_ac,\n    }\n"),
]
EMPAQ = [
    ("# instrucciones al zip\n",
     "# ---------- extension/ext_config.ini (Custom Shaders Patch) ----------\n"
     "# se copia TAL CUAL 04_export/extension/ext_config.ini (se puede editar a mano; color_ac solo lo genera si no\n"
     "# existe) a content/tracks/porto_corsa/extension/, donde lo busca CSP (sin CSP la carpeta se ignora)\n"
     "import sys  # noqa: E402\n"
     "sys.path.insert(0, os.path.join(BASE, '04_export'))\n"
     "import color_ac  # noqa: E402\n"
     "print('ext_config.ini (CSP) ->', color_ac.copiar_ext_config(TRACK))\n\n"
     "# instrucciones al zip\n"),
]


def parchear(nombre, cambios, salida):
    orig = open(os.path.join(EXP, nombre), encoding='utf-8', newline='').read()
    nuevo = orig
    fin = '\r\n' if '\r\n' in orig else '\n'          # se respetan los finales de linea del original
    for viejo, bueno in cambios:
        viejo, bueno = viejo.replace('\n', fin), bueno.replace('\n', fin)
        n = nuevo.count(viejo)
        if n != 1:
            raise SystemExit('%s: el fragmento aparece %d veces (debe ser 1): %r' % (nombre, n, viejo[:70]))
        nuevo = nuevo.replace(viejo, bueno)
    open(os.path.join(AQUI, salida), 'w', encoding='utf-8', newline='').write(nuevo)
    d = difflib.unified_diff(orig.splitlines(True), nuevo.splitlines(True),
                             'a/04_export/' + nombre, 'b/04_export/' + nombre, n=3)
    txt = ''.join(d)
    open(os.path.join(AQUI, nombre.replace('.py', '.diff')), 'w', encoding='utf-8', newline='').write(txt)
    print('%s: %d cambios -> %s (%d lineas de diff)' % (nombre, len(cambios), salida, txt.count('\n')))


parchear('kn5_writer_opt.py', WRITER, 'kn5_writer_opt_color.py')
parchear('empaquetar.py', EMPAQ, 'empaquetar_color.py')
