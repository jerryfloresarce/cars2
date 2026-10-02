"""caminos_kit.py — Kit procedural de CARRETERAS SECUNDARIAS y CAMINOS de
Porto Corsa (Cars 2) para Blender 5.1: cintas de calzada que siguen una
polilinea 3D en coordenadas de MUNDO, valla de cierre de empalmes, cartel
direccional italiano, muro de contencion de piedra y puentecillo de un arco.
Sirve para que el mapa sea una "mini ciudad funcional": los caminos llevan a
algun sitio y, si empalman con la carretera principal, se cierran con valla.

Convenciones
- Unidades en metros. Sin bpy.ops; mallas por from_pydata; materiales
  Principled BSDF de color plano reutilizados por nombre (MAT_CAMINO_*). Los
  de adoquin, tierra y piedra llevan un ruido PROCEDURAL de nodos (Noise /
  Voronoi en coordenadas de objeto = mundo), sin imagenes.
- build_camino / build_muro_contencion reciben `puntos` [(x, y, z), ...] YA
  en mundo (la z viene del terreno). La malla se crea con transform identidad
  y NO se reinterpola la z: solo se suaviza la planta si params['suavizar'].
- Las piezas sueltas (valla, cartel, puente) tienen origen en el centro de su
  base, z=0 en el suelo; el que las coloca fija location/rotation del Empty.

API
- build_camino(parent, puntos, ancho=5.0, tipo='asfalto', seed=0, **params)
    -> malla 'CAMINO_<tipo>' (vertices en mundo, normales hacia arriba).
    Cinta con bombeo del 2% hacia el centro y tapas verticales de `canto`
    (0.35 m; muelle 1.0) en los extremos y faldones laterales hasta z-canto.
    tipo='asfalto': asfalto gris + bordillo de piedra clara 0.25 m a cada
      lado + hija 'CAMINO_marcas' (linea central discontinua blanca).
    tipo='tierra': tierra ocre, bordes irregulares (ruido), arcenes de tierra
      oscura con hierba y piedras sueltas, sin bordillo; bermas a +`berma`
      (0.05 m por defecto) sobre el eje.
    tipo='adoquin': calle de pueblo adoquinada gris-rosada (Voronoi) con
      aceras de 0.8 m a cada lado (0.15 m de alto).
    tipo='muelle': calzada de losas de piedra gris oscura (Voronoi ~0.65 m,
      MAT_CAMINO_piedra_muelle) sobre el agua con pretil bajo de piedra crema
      (piedra_c, 0.35 x 0.55 m) a ambos lados, faldon de piedra con ruido
      (piedra_puente), norays de hierro y, si se pasa `nivel_agua` (z de
      mundo del agua), banda oscura de linea de agua (muelle_agua) en el
      faldon hasta nivel_agua + `banda_agua` (0.35).
    NOTA terreno: por el bombeo los bordes quedan ancho/2*0.02 por debajo
    de la z del eje; el terreno bajo la cinta debe ir >= 0.15 m por debajo
    de los puntos para no asomar (los faldones de `canto` tapan el hueco).
    params: suavizar (int pasadas | True=2), canto (m), lineas (bool, marcas
      del asfalto), bombeo (0.02), rebajes (vados: el bordillo/acera baja a
      ras, con rampa de 1.5 m, en [(s_ini, s_fin)] de arco (s < 0 cuenta
      desde el final: (-3, 0) = los ultimos 3 m; los DOS lados) o en
      [(x, y, r)] de mundo: se mide desde el BORDE de cada lado (P +- n*h),
      asi solo baja el bordillo del lado donde empalma el lateral; con
      (x, y, r, lado) se fuerza el lado (+1 = izquierdo/+n, -1 = derecho).
      Usarlo en la carretera principal donde empalma un lateral, con el
      punto (x, y) en el borde de la calzada y r ~ semiancho del lateral + 2.
      tierra: transicion_ini / transicion_fin (m): el ruido de anchura y las
      bermas se anulan en ese tramo para empalmar a tope con otro tipo de
      la misma anchura; berma (m, 0.05): altura de las bermas sobre el eje
      (0.10 si el camino va cerrado con valla y se quiere un labio marcado).
      muelle: nivel_agua (z mundo | None), banda_agua (0.35).
- build_valla_cierre(parent, ancho=6.0, seed=0, texto='CERRADO')
    -> Empty 'CAMINO_valla': barreras rojiblancas de obra (2-3 modulos con
    pies en A), conos naranjas y senal redonda de prohibido (rojo + barra
    blanca) con placa de texto (ancho segun el texto) en un poste. X = a lo
    largo de la valla, +Y = hacia el camino lateral cerrado (la senal y los
    conos miran a -Y, hacia la carretera principal). Los pies ocupan
    ancho + 0.16 m: para un camino de calzada libre L entre bordillos o
    pretiles usar ancho <= L - 0.2. Hijos: CAMINO_valla_cuerpo, _texto.
- build_cartel(parent, texto='CASINO', seed=0, flecha=1)
    -> Empty 'CAMINO_cartel': senal direccional italiana (panel blanco con
    borde azul, texto 3D azul y flecha) sobre poste gris (enterrado 0.4 m
    para laderas), panel mirando a +Y (se lee desde +Y). flecha=1 apunta a
    la DERECHA del que la lee, -1 a su izquierda, 0 recto (arriba). `texto`
    puede ser lista: paneles apilados. Hijos: CAMINO_cartel_cuerpo, _texto.
- build_muro_contencion(parent, puntos, alto=1.5, seed=0, grosor=0.5,
    relieve='ambos'|'izq'|'der'|'no') -> malla 'CAMINO_muro': muro de piedra
    (mortero + bloques en relieve escalonados + albardilla) siguiendo la
    polilinea de mundo; enterrado 0.35 m bajo cada punto.
- build_puentecillo(parent, largo=12.0, ancho=5.0, seed=0)
    -> Empty 'CAMINO_puente': puentecillo de piedra de un arco, X a lo
    largo, origen en el centro, tablero (adoquin) con la cara superior
    EXACTAMENTE en z=0 y calzada libre `ancho` entre pretiles (0.35 m) con
    pilastras-contrafuerte de 0.60 en las esquinas (cara interior a ras del
    pretil, fuera de la calzada), dovelas en relieve. Los caminos que
    empalman deben tener la misma `ancho` y llegar a z=0 en x = +-largo/2.
    Hijo: CAMINO_puente_cuerpo.
- build(parent, seed=0): escaparate (carretera principal ficticia + empalmes
    cerrados con valla, carteles, tramo de cada tipo, muro y puente) sobre el
    terreno analitico `z_demo(x, y)` que el test usa para dibujar el suelo.
"""

import bisect
import math
import random

import bpy
from mathutils import Euler, Vector

PRE = 'CAMINO'

# ------------------------------------------------------------------ materiales
# clave: (color, roughness, metallic, ruido | None)
# ruido = (tipo 'noise'|'voronoi'|'adoquin', color2, escala 1/m)
#   'adoquin': celdas Voronoi con tono por piedra entre color y color2 y
#   juntas oscuras estrechas ('Distance to Edge' con rampa estrecha).
_PALETA = {
    'asfalto':       ((0.11, 0.11, 0.12), 0.85, 0.0, ('noise', (0.09, 0.09, 0.10), 0.9)),
    'marca':         ((0.93, 0.93, 0.88), 0.50, 0.0, None),
    'bordillo':      ((0.60, 0.55, 0.43), 0.80, 0.0, None),
    'tierra':        ((0.46, 0.30, 0.13), 0.95, 0.0, ('noise', (0.34, 0.21, 0.09), 0.45)),
    'tierra_borde':  ((0.17, 0.17, 0.06), 0.95, 0.0, ('noise', (0.12, 0.20, 0.06), 0.7)),
    'adoquin':       ((0.40, 0.33, 0.32), 0.75, 0.0, ('adoquin', (0.57, 0.47, 0.45), 4.2)),
    'acera':         ((0.62, 0.57, 0.45), 0.80, 0.0, None),
    # muelle: losas grandes gris-pardo oscuro (Voronoi ~0.65 m con juntas)
    'piedra_muelle': ((0.36, 0.33, 0.27), 0.85, 0.0, ('adoquin', (0.26, 0.23, 0.18), 1.5)),
    'pretil':        ((0.54, 0.47, 0.35), 0.80, 0.0, None),
    'muelle_agua':   ((0.19, 0.22, 0.18), 0.55, 0.0, ('noise', (0.11, 0.14, 0.12), 1.3)),
    'noray':         ((0.05, 0.05, 0.06), 0.40, 0.6, None),
    'rojo':          ((0.80, 0.06, 0.05), 0.45, 0.0, None),
    'blanco':        ((0.93, 0.92, 0.88), 0.45, 0.0, None),
    'naranja':       ((0.95, 0.36, 0.04), 0.50, 0.0, None),
    'negro':         ((0.03, 0.03, 0.03), 0.70, 0.0, None),
    'gris_metal':    ((0.50, 0.52, 0.54), 0.40, 0.7, None),
    'azul_senal':    ((0.04, 0.22, 0.62), 0.40, 0.0, None),
    'mortero':       ((0.25, 0.22, 0.17), 0.95, 0.0, None),
    'piedra_a':      ((0.50, 0.42, 0.30), 0.85, 0.0, None),
    'piedra_b':      ((0.38, 0.32, 0.23), 0.85, 0.0, None),
    'piedra_c':      ((0.60, 0.52, 0.38), 0.85, 0.0, None),
    'piedra_puente': ((0.52, 0.46, 0.35), 0.85, 0.0, ('noise', (0.40, 0.35, 0.26), 0.7)),
    'hierba':        ((0.16, 0.32, 0.09), 0.90, 0.0, None),
}


def _nodos_adoquin(nt, bsdf, color, color2, escala):
    """Adoquinado procedural: dos Voronoi con la misma celda (Object coords =
    mundo): uno F1 da un tono por piedra (Color -> rampa color..color2) y otro
    'Distance to Edge' con rampa estrecha oscurece las juntas; se multiplican
    (VectorMath MULTIPLY) y van a Base Color."""
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vor_e = nt.nodes.new('ShaderNodeTexVoronoi')
    vor_e.feature = 'DISTANCE_TO_EDGE'
    vor_e.inputs['Scale'].default_value = escala
    if 'Randomness' in vor_e.inputs:
        vor_e.inputs['Randomness'].default_value = 0.62  # adoquines algo regulares
    nt.links.new(tc.outputs['Object'], vor_e.inputs['Vector'])
    juntas = nt.nodes.new('ShaderNodeValToRGB')
    el = juntas.color_ramp.elements
    el[0].position, el[1].position = 0.02, 0.075
    el[0].color = (0.42, 0.40, 0.40, 1.0)   # factor en la junta (mortero oscuro)
    el[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(vor_e.outputs['Distance'], juntas.inputs['Fac'])
    vor_c = nt.nodes.new('ShaderNodeTexVoronoi')
    vor_c.feature = 'F1'
    vor_c.inputs['Scale'].default_value = escala
    if 'Randomness' in vor_c.inputs:
        vor_c.inputs['Randomness'].default_value = 0.62
    nt.links.new(tc.outputs['Object'], vor_c.inputs['Vector'])
    tono = nt.nodes.new('ShaderNodeValToRGB')
    el2 = tono.color_ramp.elements
    el2[0].position, el2[1].position = 0.15, 0.85
    el2[0].color = (*color, 1.0)
    el2[1].color = (*color2, 1.0)
    nt.links.new(vor_c.outputs['Color'], tono.inputs['Fac'])
    mul = nt.nodes.new('ShaderNodeVectorMath')
    mul.operation = 'MULTIPLY'
    nt.links.new(tono.outputs['Color'], mul.inputs[0])
    nt.links.new(juntas.outputs['Color'], mul.inputs[1])
    nt.links.new(mul.outputs['Vector'], bsdf.inputs['Base Color'])


def _mat(clave):
    """Crea (o reutiliza) el material MAT_CAMINO_<clave> de la paleta."""
    nombre = 'MAT_%s_%s' % (PRE, clave)
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough, metal, ruido = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    try:
        if not m.use_nodes:
            m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    bsdf = None
    if nt is not None:
        bsdf = next((nd for nd in nt.nodes if nd.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
            sal = next((nd for nd in nt.nodes if nd.type == 'OUTPUT_MATERIAL'), None)
            if sal is None:
                sal = nt.nodes.new('ShaderNodeOutputMaterial')
            nt.links.new(bsdf.outputs['BSDF'], sal.inputs['Surface'])
    if bsdf is not None:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = rough
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metal
        if ruido is not None and ruido[0] == 'adoquin':
            try:
                _nodos_adoquin(nt, bsdf, color, ruido[1], ruido[2])
            except Exception as ex:  # nunca debe tumbar el build
                print('caminos_kit: sin juntas en %s (%s)' % (nombre, ex))
        elif ruido is not None:
            try:
                tipo, color2, escala = ruido
                tc = nt.nodes.new('ShaderNodeTexCoord')
                if tipo == 'voronoi':
                    tex = nt.nodes.new('ShaderNodeTexVoronoi')
                    sal_tex = tex.outputs['Distance']
                    posiciones = (0.50, 0.82)
                else:
                    tex = nt.nodes.new('ShaderNodeTexNoise')
                    sal_tex = tex.outputs['Fac']
                    posiciones = (0.35, 0.65)
                tex.inputs['Scale'].default_value = escala
                nt.links.new(tc.outputs['Object'], tex.inputs['Vector'])
                rampa = nt.nodes.new('ShaderNodeValToRGB')
                el = rampa.color_ramp.elements
                el[0].position, el[1].position = posiciones
                el[0].color = (*color, 1.0)
                el[1].color = (*color2, 1.0)
                nt.links.new(sal_tex, rampa.inputs['Fac'])
                nt.links.new(rampa.outputs['Color'], bsdf.inputs['Base Color'])
            except Exception as ex:  # nunca debe tumbar el build
                print('caminos_kit: sin ruido en %s (%s)' % (nombre, ex))
    m.diffuse_color = (*color, 1.0)
    return m


# ------------------------------------------------------------ utilidades malla

class _MB:
    """Acumulador de primitivas que produce una unica malla multi-material."""

    def __init__(self):
        self.v = []
        self.f = []
        self.fm = []

    def caja(self, centro, dim, mat=0, rot=(0.0, 0.0, 0.0)):
        """Caja centrada en `centro` con rotacion Euler XYZ `rot`."""
        cx, cy, cz = centro
        hx, hy, hz = dim[0] / 2.0, dim[1] / 2.0, dim[2] / 2.0
        R = Euler(rot, 'XYZ').to_matrix()
        base = len(self.v)
        for dx, dy, dz in ((-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz),
                           (-hx, hy, -hz), (-hx, -hy, hz), (hx, -hy, hz),
                           (hx, hy, hz), (-hx, hy, hz)):
            p = R @ Vector((dx, dy, dz))
            self.v.append((cx + p.x, cy + p.y, cz + p.z))
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f.append((base + q[0], base + q[1], base + q[2], base + q[3]))
            self.fm.append(mat)

    def cilindro(self, base_c, r_abajo, r_arriba, alto, mat=0, n=8, tapas=True):
        """Cono truncado vertical; base_c es el centro de la base inferior."""
        cx, cy, cz = base_c
        b = len(self.v)
        for j in range(n):
            th = 2.0 * math.pi * j / n
            self.v.append((cx + r_abajo * math.cos(th), cy + r_abajo * math.sin(th), cz))
        for j in range(n):
            th = 2.0 * math.pi * j / n
            self.v.append((cx + r_arriba * math.cos(th), cy + r_arriba * math.sin(th), cz + alto))
        for j in range(n):
            j2 = (j + 1) % n
            self.f.append((b + j, b + j2, b + n + j2, b + n + j))
            self.fm.append(mat)
        if tapas is True:
            self.f.append(tuple(b + j for j in reversed(range(n))))
            self.fm.append(mat)
        if tapas:
            self.f.append(tuple(b + n + j for j in range(n)))
            self.fm.append(mat)

    def prisma_y(self, poli, y0, y1, mat=0, mat_lados=None):
        """Prisma entre y0 < y1 a partir de un poligono (x, z) en sentido
        antihorario visto desde -Y (x a la derecha, z arriba). Normales hacia
        fuera; el poligono puede ser concavo (ngon)."""
        b = len(self.v)
        k = len(poli)
        for x, z in poli:
            self.v.append((x, y0, z))
        for x, z in poli:
            self.v.append((x, y1, z))
        self.f.append(tuple(b + j for j in range(k)))
        self.fm.append(mat)
        self.f.append(tuple(b + k + j for j in reversed(range(k))))
        self.fm.append(mat)
        ml = mat if mat_lados is None else mat_lados
        for j in range(k):
            j2 = (j + 1) % k
            self.f.append((b + j, b + k + j, b + k + j2, b + j2))
            self.fm.append(ml)

    def bloque(self, centro, derecha, fuera, largo, alto, saliente, inset, mat=0):
        """Bloque de piedra en relieve sobre una cara vertical: tronco de
        piramide (tapa + 4 lados, sin base). `centro` en la cara, `derecha` =
        direccion +largo vista desde fuera, `fuera` = normal de la cara."""
        c = Vector(centro)
        d = Vector(derecha)
        f = Vector(fuera)
        up = Vector((0.0, 0.0, 1.0))
        hl, hh = largo / 2.0, alto / 2.0
        il, ih = max(0.02, hl - inset), max(0.02, hh - inset)
        b = len(self.v)
        for p in (c - d * hl - up * hh, c + d * hl - up * hh, c + d * hl + up * hh, c - d * hl + up * hh,
                  c - d * il - up * ih + f * saliente, c + d * il - up * ih + f * saliente,
                  c + d * il + up * ih + f * saliente, c - d * il + up * ih + f * saliente):
            self.v.append((p.x, p.y, p.z))
        for q in ((4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.f.append(tuple(b + i for i in q))
            self.fm.append(mat)

    def esfera_baja(self, centro, r, mat=0, rz=0.0, n=5):
        """Piedra suelta: anillo irregular en la base, anillo alto y apice
        (n quads + n tris). Base en z del centro."""
        cx, cy, cz = centro
        b = len(self.v)
        for j in range(n):
            th = rz + 2.0 * math.pi * j / n
            rr = r * (1.0 + 0.22 * math.sin(3.0 * th + rz))
            self.v.append((cx + rr * math.cos(th), cy + rr * math.sin(th), cz - 0.05))
        for j in range(n):
            th = rz + 2.0 * math.pi * (j + 0.5) / n
            self.v.append((cx + 0.55 * r * math.cos(th), cy + 0.55 * r * math.sin(th), cz + 0.62 * r))
        self.v.append((cx + 0.1 * r, cy, cz + 0.85 * r))
        ap = b + 2 * n
        for j in range(n):
            j2 = (j + 1) % n
            self.f.append((b + j, b + j2, b + n + j2, b + n + j))
            self.fm.append(mat)
            self.f.append((b + n + j, b + n + j2, ap))
            self.fm.append(mat)

    def mata(self, centro, r, mat=0, rz=0.0, n=5):
        """Mata baja de hierba: cono irregular de n lados (n tris)."""
        cx, cy, cz = centro
        b = len(self.v)
        for j in range(n):
            th = rz + 2.0 * math.pi * j / n
            rr = r * (1.0 + 0.3 * math.sin(2.0 * th + rz))
            self.v.append((cx + rr * math.cos(th), cy + rr * math.sin(th), cz - 0.05))
        self.v.append((cx, cy, cz + 0.55 * r))
        for j in range(n):
            j2 = (j + 1) % n
            self.f.append((b + j, b + j2, b + n))
            self.fm.append(mat)

    def obj(self, nombre, claves_mat, col):
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(self.v, [], self.f)
        for clave in claves_mat:
            me.materials.append(_mat(clave))
        for p, mi in zip(me.polygons, self.fm):
            p.material_index = mi
        me.validate()
        me.update()
        ob = bpy.data.objects.new(nombre, me)
        col.objects.link(ob)
        return ob


def _raiz(nombre, col):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_size = 0.5
    col.objects.link(e)
    return e


def _clip_x(poli, xmin, xmax):
    """Recorta un poligono convexo (x, z) a la franja xmin <= x <= xmax
    (Sutherland-Hodgman). Devuelve [] si queda vacio."""
    def corte(pts, dentro, inter):
        sal = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            da, db = dentro(a), dentro(b)
            if da:
                sal.append(a)
            if da != db:
                sal.append(inter(a, b))
        return sal

    def inter_en(x0):
        def f(a, b):
            t = (x0 - a[0]) / (b[0] - a[0])
            return (x0, a[1] + (b[1] - a[1]) * t)
        return f

    p = corte(poli, lambda q: q[0] >= xmin - 1e-9, inter_en(xmin))
    if len(p) < 3:
        return []
    p = corte(p, lambda q: q[0] <= xmax + 1e-9, inter_en(xmax))
    return p if len(p) >= 3 else []


# ------------------------------------------------------------------ texto 3D

def _texto_datos(texto, tam, extrude=0.0):
    """Malla de un texto (curva FONT -> malla sin tocar el depsgraph) en su
    espacio propio: x a la derecha, y arriba, centrado. Devuelve
    (verts, caras, ancho, alto)."""
    cu = bpy.data.curves.new('CAMINO_txt_cu', type='FONT')
    cu.body = texto
    cu.size = tam
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.resolution_u = 3  # 2 daba O/C/S octogonales de cerca
    try:
        cu.fill_mode = 'FRONT' if extrude <= 0.0 else 'BOTH'
    except Exception:
        pass
    tmp = bpy.data.objects.new('CAMINO_txt_tmp', cu)
    me_t = bpy.data.meshes.new_from_object(tmp)
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    vs = [(v.co.x, v.co.y, v.co.z) for v in me_t.vertices]
    fs = [tuple(p.vertices) for p in me_t.polygons]
    bpy.data.meshes.remove(me_t)
    if vs:
        xs = [v[0] for v in vs]
        ys = [v[1] for v in vs]
        ancho, alto = max(xs) - min(xs), max(ys) - min(ys)
        cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
        vs = [(x - cx, y - cy, z) for x, y, z in vs]
    else:
        ancho = alto = 0.0
    return vs, fs, ancho, alto


def _texto_colocar(mb, datos, pos, rot_z, mat):
    """Anade a `mb` el texto de `_texto_datos` de pie, centrado en `pos`,
    legible desde +Y (rot_z=0) o desde -Y (rot_z=pi); el relieve sale hacia
    el lector."""
    vs, fs = datos[0], datos[1]
    x, y, z = pos
    co, si = math.cos(math.pi + rot_z), math.sin(math.pi + rot_z)
    b = len(mb.v)
    for vx, vy, vz in vs:
        px, py, pz = vx, -vz, vy
        mb.v.append((x + px * co - py * si, y + px * si + py * co, z + pz))
    for f in fs:
        mb.f.append(tuple(b + i for i in f))
        mb.fm.append(mat)


# ------------------------------------------------------------ polilineas 3D

def _frames(puntos, suavizar=0):
    """[(P Vector3, t Vector2 unit, n Vector2 unit izquierda, s arco)] a partir
    de puntos de mundo. Quita repetidos en planta y suaviza la planta (nunca
    la z) con `suavizar` pasadas de media ponderada (los extremos fijos)."""
    pts = [Vector((float(p[0]), float(p[1]), float(p[2]))) for p in puntos]
    limp = [pts[0]]
    for p in pts[1:]:
        if (p.xy - limp[-1].xy).length > 0.05:
            limp.append(p)
    pts = limp
    if len(pts) < 2:
        raise ValueError('caminos_kit: hacen falta al menos 2 puntos distintos')
    pasadas = 2 if suavizar is True else int(suavizar or 0)
    for _ in range(pasadas):
        if len(pts) < 3:
            break
        nuevo = [pts[0]]
        for i in range(1, len(pts) - 1):
            xy = (pts[i - 1].xy + pts[i].xy * 2.0 + pts[i + 1].xy) / 4.0
            nuevo.append(Vector((xy.x, xy.y, pts[i].z)))
        nuevo.append(pts[-1])
        pts = nuevo
    frames = []
    s = 0.0
    m = len(pts)
    for i in range(m):
        if i == 0:
            d = pts[1].xy - pts[0].xy
        elif i == m - 1:
            d = pts[-1].xy - pts[-2].xy
        else:
            d = pts[i + 1].xy - pts[i - 1].xy
        if d.length < 1e-6:
            d = Vector((1.0, 0.0))
        d.normalize()
        if i > 0:
            s += (pts[i].xy - pts[i - 1].xy).length
        frames.append((pts[i], d, Vector((-d.y, d.x)), s))
    return frames


def _pos_en(frames, arcos, s):
    """(P Vector3, t, n) interpolados en la abscisa de arco s."""
    s = max(arcos[0], min(arcos[-1], s))
    i = bisect.bisect_right(arcos, s) - 1
    i = max(0, min(len(frames) - 2, i))
    P0, t0, n0, s0 = frames[i]
    P1, t1, n1, s1 = frames[i + 1]
    u = 0.0 if s1 - s0 < 1e-9 else (s - s0) / (s1 - s0)
    P = P0.lerp(P1, u)
    t = (t0 * (1.0 - u) + t1 * u)
    if t.length < 1e-6:
        t = t0.copy()
    t.normalize()
    return P, t, Vector((-t.y, t.x))


def _sobre_polilinea(puntos, s, dz=0.0):
    """Pose para apoyar una pieza sobre la polilinea de mundo `puntos` en la
    abscisa s: (location, rotation_euler) con +Y local = sentido de avance,
    inclinada segun la pendiente local (no rueda en peralte)."""
    fr = _frames(puntos)
    arcos = [f[3] for f in fr]
    P, t, n = _pos_en(fr, arcos, s)
    P0, _, _ = _pos_en(fr, arcos, s - 1.0)
    P1, _, _ = _pos_en(fr, arcos, s + 1.0)
    ds = max(1e-6, (P1.xy - P0.xy).length)
    pend = math.atan2(P1.z - P0.z, ds)
    return ((P.x, P.y, P.z + dz), (pend, 0.0, math.atan2(-t.x, t.y)))


def _cinta(mb, frames, perfil_fn, mat_tapa, tapas=True):
    """Cinta a lo largo de `frames`. perfil_fn(i, frame) -> lista de
    (offset lateral, dz, mat) ordenada de derecha (offset < 0) a izquierda
    (offset > 0) recorriendo el contorno del solido: mat es el del tramo que
    EMPIEZA en ese punto. Quads con normales hacia fuera/arriba; tapas
    (ngons verticales) en los dos extremos."""
    anillos = []
    perfiles = []
    for i, fr in enumerate(frames):
        P, t, n, s = fr
        prof = perfil_fn(i, fr)
        anillos.append(len(mb.v))
        for off, dz, mat in prof:
            mb.v.append((P.x + n.x * off, P.y + n.y * off, P.z + dz))
        perfiles.append(prof)
    k = len(perfiles[0])
    for i in range(len(frames) - 1):
        a, b = anillos[i], anillos[i + 1]
        for j in range(k - 1):
            mb.f.append((a + j, b + j, b + j + 1, a + j + 1))
            mb.fm.append(perfiles[i][j][2])
    if tapas:
        mb.f.append(tuple(anillos[0] + j for j in range(k)))
        mb.fm.append(mat_tapa)
        mb.f.append(tuple(anillos[-1] + j for j in reversed(range(k))))
        mb.fm.append(mat_tapa)


def _ruido1(s, f1, f2, ph1, ph2, a1, a2):
    return a1 * math.sin(s * f1 + ph1) + a2 * math.sin(s * f2 + ph2)


# ------------------------------------------------------------------ caminos

def build_camino(parent_collection, puntos, ancho=5.0, tipo='asfalto', seed=0, **params):
    """Cinta de calzada de tipo 'asfalto' | 'tierra' | 'adoquin' | 'muelle'
    siguiendo la polilinea de mundo `puntos` (ver docstring del modulo).
    Devuelve la malla 'CAMINO_<tipo>' (con hija 'CAMINO_marcas' si asfalto)."""
    col = parent_collection
    rng = random.Random(seed)
    if tipo not in ('asfalto', 'tierra', 'adoquin', 'muelle'):
        raise ValueError('caminos_kit: tipo desconocido %r' % tipo)
    frames = _frames(puntos, params.get('suavizar', 0))
    arcos = [fr[3] for fr in frames]
    largo = arcos[-1]
    bomb = float(params.get('bombeo', 0.02))
    canto = float(params.get('canto', 1.0 if tipo == 'muelle' else 0.35))
    h = ancho / 2.0
    mb = _MB()
    rebajes = list(params.get('rebajes', ()))

    RAMPA = 1.5  # m de transicion del bordillo entero al vado

    def rebaje(fr):
        """[der, izq] en 0..1: 1 = el bordillo/acera de ese lado queda a ras
        (vado). rebajes: [(s_ini, s_fin)] en arco (s < 0 desde el final; los
        dos lados) o [(x, y, radio[, lado])] en mundo, medido desde el BORDE
        de cada lado (P +- n*h) para que solo baje el lado que empalma."""
        P, t, n, s = fr
        sal = [0.0, 0.0]
        for r in rebajes:
            if len(r) == 2:
                s0, s1 = float(r[0]), float(r[1])
                if s0 < 0.0:
                    s0 += largo
                if s1 <= 0.0 and r[0] < 0.0:
                    s1 += largo
                v = min(1.0, max(0.0, 1.0 + min(s - s0, s1 - s) / RAMPA))
                sal[0] = max(sal[0], v)
                sal[1] = max(sal[1], v)
            elif len(r) >= 3:
                fuerza = float(r[3]) if len(r) > 3 else 0.0
                for j, lado in enumerate((-1.0, 1.0)):
                    if fuerza * lado < 0.0:
                        continue
                    E = P.xy + n * (h * lado)
                    d = math.hypot(E.x - r[0], E.y - r[1])
                    v = min(1.0, max(0.0, (float(r[2]) + RAMPA - d) / RAMPA))
                    sal[j] = max(sal[j], v)
        return sal

    if tipo in ('asfalto', 'adoquin'):
        if tipo == 'asfalto':
            claves = ('asfalto', 'bordillo')
            k, hk0 = 0.25, 0.12
        else:
            claves = ('adoquin', 'acera')
            k, hk0 = 0.8, 0.15
        A, B = 0, 1
        ce = -bomb * h

        def perfil(i, fr):
            rd, ri = rebaje(fr)
            hd, hi = hk0 * (1.0 - rd), hk0 * (1.0 - ri)
            # (h, ce, B): la cara interior del bordillo izquierdo es de bordillo
            return [(-h - k, -canto, B), (-h - k, ce + hd, B), (-h, ce + hd, B), (-h, ce, A),
                    (-h * 0.5, ce * 0.5, A), (0.0, 0.0, A), (h * 0.5, ce * 0.5, A), (h, ce, B),
                    (h, ce + hi, B), (h + k, ce + hi, B), (h + k, -canto, B)]
        _cinta(mb, frames, perfil, B)

    elif tipo == 'muelle':
        # A calzada de losas oscuras, B pretil crema, N norays, F faldon de
        # piedra con ruido, AG banda oscura de linea de agua (si nivel_agua)
        claves = ('piedra_muelle', 'piedra_c', 'noray', 'piedra_puente', 'muelle_agua')
        A, B, N, F, AG = 0, 1, 2, 3, 4
        pt, hp = 0.35, 0.55
        ce = -bomb * h
        nivel_agua = params.get('nivel_agua', None)
        banda = float(params.get('banda_agua', 0.35))

        def perfil(i, fr):
            P = fr[0]
            fondo = AG if nivel_agua is not None else F
            prof = [(-h - pt, -canto, fondo)]
            if nivel_agua is not None:
                zb = float(nivel_agua) + banda - P.z          # cima de la banda (relativa)
                zb = max(-canto + 0.05, min(ce - 0.15, zb))
                prof.append((-h - pt, zb, F))
            prof += [(-h - pt, ce + hp, B), (-h - pt + 0.05, ce + hp + 0.05, B),
                     (-h - 0.05, ce + hp + 0.05, B), (-h, ce + hp, B), (-h, ce, A),
                     (-h * 0.5, ce * 0.5, A), (0.0, 0.0, A), (h * 0.5, ce * 0.5, A), (h, ce, B),
                     (h, ce + hp, B), (h + 0.05, ce + hp + 0.05, B), (h + pt - 0.05, ce + hp + 0.05, B),
                     (h + pt, ce + hp, F)]
            if nivel_agua is not None:
                prof.append((h + pt, zb, AG))
            prof.append((h + pt, -canto, fondo))
            return prof
        _cinta(mb, frames, perfil, F)
        # norays de hierro alternando lados cada ~14 m
        s = 7.0
        lado = 1.0
        while s < largo - 4.0:
            P, t, n = _pos_en(frames, arcos, s)
            off = lado * (h - 0.45)
            base = (P.x + n.x * off, P.y + n.y * off, P.z - bomb * abs(off) - 0.02)
            mb.cilindro(base, 0.16, 0.13, 0.32, mat=N, n=6, tapas=False)
            mb.cilindro((base[0], base[1], base[2] + 0.32), 0.19, 0.12, 0.12, mat=N, n=6, tapas='arriba')
            s += rng.uniform(12.0, 16.0)
            lado = -lado

    else:  # tierra
        claves = ('tierra', 'tierra_borde', 'piedra_b', 'hierba')
        A, B, PB, HI = 0, 1, 2, 3
        fs = [rng.uniform(0, 6.28) for _ in range(6)]
        tr_i = float(params.get('transicion_ini', 0.0))
        tr_f = float(params.get('transicion_fin', 0.0))
        berma = float(params.get('berma', 0.05))  # altura de las bermas sobre el eje

        def taper(s):
            """0 en un empalme (anchura exacta, sin bermas) -> 1 a tr m."""
            f = 1.0
            if tr_i > 0.0:
                f = min(f, s / tr_i)
            if tr_f > 0.0:
                f = min(f, (largo - s) / tr_f)
            return max(0.0, min(1.0, f))

        def perfil(i, fr):
            s = fr[3]
            tp = taper(s)
            wl = h * (1.0 + tp * _ruido1(s, 0.37, 1.10, fs[0], fs[1], 0.13, 0.06))
            wr = h * (1.0 + tp * _ruido1(s, 0.29, 0.90, fs[2], fs[3], 0.13, 0.06))
            bl = tp * (0.75 + 0.35 * math.sin(s * 0.5 + fs[4]))
            br = tp * (0.75 + 0.35 * math.sin(s * 0.45 + fs[5]))
            zl = -bomb * wl + tp * (berma + bomb * wl)  # berma: del ras del borde a +berma
            zr = -bomb * wr + tp * (berma + bomb * wr)
            return [(-wr - br, -canto, B), (-wr - br, zr, B), (-wr - br * 0.5, zr + 0.01 * tp, B),
                    (-wr, -bomb * wr, A), (-wr * 0.5, -bomb * wr * 0.5, A), (0.0, 0.0, A),
                    (wl * 0.5, -bomb * wl * 0.5, A), (wl, -bomb * wl, A),
                    (wl + bl * 0.5, zl + 0.01 * tp, B), (wl + bl, zl, B), (wl + bl, -canto, B)]
        _cinta(mb, frames, perfil, B)
        # piedras sueltas y matas de hierba en los arcenes (fuera de las transiciones)
        s = max(2.0, tr_i)
        while s < largo - max(2.0, tr_f):
            P, t, n = _pos_en(frames, arcos, s)
            lado = rng.choice((-1.0, 1.0))
            off = lado * (h * 1.08 + rng.uniform(0.25, 0.7))
            c = Vector((P.x + n.x * off, P.y + n.y * off, P.z + berma + 0.03))
            if rng.random() < 0.55:
                r = rng.uniform(0.12, 0.26)
                mb.esfera_baja(c, r, mat=PB, rz=rng.uniform(0, 3.14))
            else:
                mb.mata(c, rng.uniform(0.25, 0.45), mat=HI, rz=rng.uniform(0, 3.14))
            s += rng.uniform(3.5, 7.0)

    ob = mb.obj('%s_%s' % (PRE, tipo), claves, col)

    if tipo == 'asfalto' and params.get('lineas', True):
        mm = _MB()
        dash, gap, wl = 3.0, 6.0, 0.12
        s0 = 1.5
        while s0 + dash < largo - 1.0:
            s1 = s0 + dash
            muestras = [s0] + [a for a in arcos if s0 < a < s1] + [s1]
            b = len(mm.v)
            for sm in muestras:
                P, t, n = _pos_en(frames, arcos, sm)
                mm.v.append((P.x - n.x * wl, P.y - n.y * wl, P.z + 0.012))
                mm.v.append((P.x + n.x * wl, P.y + n.y * wl, P.z + 0.012))
            for j in range(len(muestras) - 1):
                mm.f.append((b + 2 * j, b + 2 * j + 2, b + 2 * j + 3, b + 2 * j + 1))
                mm.fm.append(0)
            s0 += dash + gap
        marcas = mm.obj('%s_marcas' % PRE, ('marca',), col)
        marcas.parent = ob
    return ob


# ------------------------------------------------------------ valla de cierre

def _tablon_rayado(mb, x0, x1, z0, z1, esp, rng, paso=0.28):
    """Tablon de obra entre x0..x1 y z0..z1 (grosor `esp` centrado en y=0)
    hecho de franjas diagonales rojas y blancas alternas (prismas)."""
    h = z1 - z0
    x = x0 - h - rng.uniform(0.0, paso)
    color = rng.randrange(2)
    while x < x1:
        poli = [(x, z0), (x + paso, z0), (x + paso + h, z1), (x + h, z1)]
        rec = _clip_x(poli, x0, x1)
        if rec:
            mb.prisma_y(rec, -esp / 2.0, esp / 2.0, mat=color)
        x += paso
        color = 1 - color


def build_valla_cierre(parent_collection, ancho=6.0, seed=0, texto='CERRADO', **params):
    """Valla de cierre de un empalme: barreras rojiblancas de obra con pies en
    A, conos naranjas delante (lado -Y, carretera principal) y senal redonda
    de prohibido el paso con placa de texto en un poste. X a lo largo de la
    valla, +Y hacia el camino lateral que se cierra. Devuelve el Empty
    'CAMINO_valla' (hijos: _cuerpo, _texto)."""
    col = parent_collection
    rng = random.Random(seed)
    raiz = _raiz('%s_valla' % PRE, col)
    mb = _MB()  # 0 rojo, 1 blanco, 2 gris_metal, 3 naranja, 4 negro
    R, W, G, O, K = 0, 1, 2, 3, 4
    n_mod = 2 if ancho <= 5.0 else 3
    lmod = ancho / n_mod
    x_ini = -ancho / 2.0
    # pies en A en cada frontera de modulo
    ang = 0.28
    for m in range(n_mod + 1):
        xf = x_ini + m * lmod
        for signo in (1.0, -1.0):
            mb.caja((xf, signo * 0.17, 0.60), (0.05, 0.05, 1.25), mat=G, rot=(signo * ang, 0.0, 0.0))
            mb.caja((xf, signo * 0.30, 0.02), (0.16, 0.16, 0.04), mat=G)
        mb.caja((xf, 0.0, 0.33), (0.04, 0.60, 0.04), mat=G)
        mb.caja((xf, 0.0, 1.22), (0.06, 0.10, 0.06), mat=G)
    # tablones rayados (uno alto ancho y otro bajo estrecho) por modulo
    for m in range(n_mod):
        x0 = x_ini + m * lmod + 0.06
        x1 = x_ini + (m + 1) * lmod - 0.06
        _tablon_rayado(mb, x0, x1, 0.86, 1.12, 0.04, rng)
        _tablon_rayado(mb, x0, x1, 0.44, 0.56, 0.04, rng, paso=0.22)
    # conos delante (hacia -Y), ligeramente desordenados
    n_conos = n_mod + 1
    for c in range(n_conos):
        u = (c + 0.5) / n_conos
        cx = x_ini + u * ancho + rng.uniform(-0.25, 0.25)
        cy = -1.05 + rng.uniform(-0.25, 0.2)
        rz = rng.uniform(0.0, 1.5)
        mb.caja((cx, cy, 0.015), (0.36, 0.36, 0.03), mat=K, rot=(0.0, 0.0, rz))
        mb.cilindro((cx, cy, 0.03), 0.17, 0.045, 0.50, mat=O, n=8, tapas='arriba')  # base negra debajo
        mb.cilindro((cx, cy, 0.03 + 0.26), 0.122, 0.102, 0.08, mat=W, n=8, tapas=False)
    # poste y senal de prohibido (mira a -Y) detras de la valla
    px, py = 0.0, 0.55
    mb.cilindro((px, py, 0.0), 0.035, 0.035, 2.08, mat=G, n=6)
    def disco(r, y0, y1, zc, mat, n=20):
        poli = [(px + r * math.cos(2 * math.pi * j / n), zc + r * math.sin(2 * math.pi * j / n))
                for j in range(n)]
        mb.prisma_y(poli, y0, y1, mat=mat)
    disco(0.345, py - 0.045, py - 0.02, 1.76, W)
    disco(0.31, py - 0.075, py - 0.04, 1.76, R)
    mb.caja((px, py - 0.085, 1.76), (0.40, 0.02, 0.09), mat=W)
    # placa de texto bajo la senal, dimensionada segun el ancho del texto
    datos = _texto_datos(str(texto), 0.11, extrude=0.0)
    wp = max(0.40, datos[2] + 0.16)
    mb.caja((px, py - 0.045, 1.30), (wp, 0.02, 0.19), mat=W)
    mb.caja((px, py - 0.052, 1.30), (wp + 0.02, 0.006, 0.21), mat=K)
    mb.caja((px, py - 0.056, 1.30), (wp - 0.02, 0.006, 0.17), mat=W)
    cuerpo = mb.obj('%s_valla_cuerpo' % PRE, ('rojo', 'blanco', 'gris_metal', 'naranja', 'negro'), col)
    cuerpo.parent = raiz
    mt = _MB()
    _texto_colocar(mt, datos, (px, py - 0.062, 1.30), math.pi, 0)
    txt = mt.obj('%s_valla_texto' % PRE, ('negro',), col)
    txt.parent = raiz
    return raiz


# ---------------------------------------------------------------- cartel

def _flecha_poli(direccion):
    """Poligonos (fuste, punta) de una flecha de 0.7 m en el plano (x, z),
    CCW vistos desde -Y. direccion: (1, 0) punta a +X, (-1, 0) a -X,
    (0, 1) hacia arriba."""
    fuste = [(-0.35, -0.075), (0.08, -0.075), (0.08, 0.075), (-0.35, 0.075)]
    punta = [(0.06, -0.20), (0.35, 0.0), (0.06, 0.20)]
    dx, dz = direccion
    if dx < 0:
        fuste = [(-x, z) for x, z in reversed(fuste)]
        punta = [(-x, z) for x, z in reversed(punta)]
    elif dz > 0:
        fuste = [(-z, x) for x, z in fuste]
        punta = [(-z, x) for x, z in punta]
    return fuste, punta


def build_cartel(parent_collection, texto='CASINO', seed=0, flecha=1, **params):
    """Senal direccional italiana: uno o varios paneles blancos apilados con
    borde azul, texto 3D azul y flecha, sobre poste gris. El panel mira a +Y
    (se lee desde +Y). flecha=1 apunta a la derecha del lector, -1 a su
    izquierda, 0 recto (arriba); `flecha` puede ser lista (una por linea).
    Devuelve el Empty 'CAMINO_cartel' (hijos: _cuerpo, _texto)."""
    col = parent_collection
    rng = random.Random(seed)
    raiz = _raiz('%s_cartel' % PRE, col)
    lineas = list(texto) if isinstance(texto, (list, tuple)) else [str(texto)]
    flechas = list(flecha) if isinstance(flecha, (list, tuple)) else [flecha] * len(lineas)
    while len(flechas) < len(lineas):
        flechas.append(flechas[-1] if flechas else 1)
    tam = float(params.get('tam_texto', 0.30))
    datos = [_texto_datos(l, tam, extrude=0.0) for l in lineas]
    W = max(1.35 + d[2] for d in datos)
    W = max(W, 1.8)
    H = 0.56
    gap = 0.06
    z_top = float(params.get('alto', 2.45))
    mb = _MB()  # 0 blanco, 1 azul_senal, 2 gris_metal
    B, A, G = 0, 1, 2
    # enterrado 0.4 m; la cima queda 2 cm por debajo del canto superior del panel
    mb.cilindro((0.0, -0.09, -0.4), 0.045, 0.040, z_top + 0.40 - 0.02, mat=G, n=8)
    mt = _MB()
    for i, (d, fl) in enumerate(zip(datos, flechas)):
        zc = z_top - H / 2.0 - i * (H + gap)
        mb.caja((0.0, -0.025, zc), (W, 0.05, H), mat=B)
        mb.caja((0.0, -0.075, zc), (0.20, 0.06, 0.16), mat=G)
        # borde azul en la cara +Y
        e = 0.035
        mb.caja((0.0, 0.006, zc + H / 2.0 - e / 2.0), (W, 0.012, e), mat=A)
        mb.caja((0.0, 0.006, zc - H / 2.0 + e / 2.0), (W, 0.012, e), mat=A)
        mb.caja((-W / 2.0 + e / 2.0, 0.006, zc), (e, 0.012, H), mat=A)
        mb.caja((W / 2.0 - e / 2.0, 0.006, zc), (e, 0.012, H), mat=A)
        # el lector esta en +Y mirando a -Y: su derecha es -X
        if fl > 0:
            sgn, dirn = -1.0, (-1, 0)
        elif fl < 0:
            sgn, dirn = 1.0, (1, 0)
        else:
            sgn, dirn = 1.0, (0, 1)
        xa = sgn * (W / 2.0 - 0.20 - 0.35)
        fuste, punta = _flecha_poli(dirn)
        mb.prisma_y([(x + xa, z + zc) for x, z in fuste], 0.006, 0.018, mat=A)
        mb.prisma_y([(x + xa, z + zc) for x, z in punta], 0.006, 0.018, mat=A)
        # texto centrado en el espacio libre entre el margen y la flecha
        libre0 = -sgn * (W / 2.0 - 0.20)
        libre1 = sgn * (W / 2.0 - 0.20 - 0.70 - 0.20)
        xt = (libre0 + libre1) / 2.0
        _texto_colocar(mt, d, (xt, 0.014, zc - 0.02), 0.0, 0)
    cuerpo = mb.obj('%s_cartel_cuerpo' % PRE, ('blanco', 'azul_senal', 'gris_metal'), col)
    cuerpo.parent = raiz
    txt = mt.obj('%s_cartel_texto' % PRE, ('azul_senal',), col)
    txt.parent = raiz
    return raiz


# ------------------------------------------------------------ muro de piedra

def build_muro_contencion(parent_collection, puntos, alto=1.5, seed=0, **params):
    """Muro de contencion de piedra siguiendo la polilinea de mundo `puntos`:
    cuerpo de mortero enterrado `canto` (0.35) bajo cada punto, albardilla de
    piedra clara con vuelo y bloques en relieve escalonados en las caras
    (relieve='ambos'|'izq'|'der'|'no'; izq = lado +n, a la izquierda del
    sentido de la polilinea). grosor=0.5. Devuelve la malla 'CAMINO_muro'."""
    col = parent_collection
    rng = random.Random(seed)
    grosor = float(params.get('grosor', 0.5))
    relieve = params.get('relieve', 'ambos')
    canto = float(params.get('canto', 0.35))
    frames = _frames(puntos, params.get('suavizar', 0))
    g = grosor / 2.0
    ha, vo = 0.12, 0.06
    mb = _MB()  # 0 mortero, 1 piedra_c (albardilla), 2 piedra_a, 3 piedra_b, 4 piedra_c

    def perfil(i, fr):
        return [(-g, -canto, 0), (-g, alto - ha, 0), (-g - vo, alto - ha, 1), (-g - vo, alto, 1),
                (g + vo, alto, 1), (g + vo, alto - ha, 1), (g, alto - ha, 0), (g, -canto, 0)]
    _cinta(mb, frames, perfil, 0)
    caras = []
    if relieve in ('ambos', 'der'):
        caras.append(-1.0)
    if relieve in ('ambos', 'izq'):
        caras.append(1.0)
    nc = max(1, int(round((alto - ha) / 0.40)))
    hc = (alto - ha) / nc
    for i in range(len(frames) - 1):
        P0, P1 = frames[i][0], frames[i + 1][0]
        d = P1.xy - P0.xy
        Ls = d.length
        if Ls < 0.3:
            continue
        t = d / Ls
        n = Vector((-t.y, t.x))
        nb = max(1, int(round(Ls / 1.0)))
        Lb = Ls / nb
        for c in range(nc):
            zc = (c + 0.5) * hc
            if c % 2 == 0:
                sitios = [((k + 0.5) * Lb, Lb) for k in range(nb)]
            else:
                sitios = [(Lb * 0.25, Lb / 2.0)] + [(k * Lb, Lb) for k in range(1, nb)] + [(Ls - Lb * 0.25, Lb / 2.0)]
            for u, L in sitios:
                z = P0.z + (P1.z - P0.z) * (u / Ls) + zc
                for lado in caras:
                    cen = (P0.x + t.x * u + n.x * g * lado, P0.y + t.y * u + n.y * g * lado, z)
                    mb.bloque(cen, (-t.x * lado, -t.y * lado, 0.0), (n.x * lado, n.y * lado, 0.0),
                              L - 0.07, hc - 0.07, rng.uniform(0.03, 0.05), 0.035, mat=rng.choice((2, 3, 4, 2)))
    return mb.obj('%s_muro' % PRE, ('mortero', 'piedra_c', 'piedra_a', 'piedra_b', 'piedra_c'), col)


# ------------------------------------------------------------ puentecillo

def build_puentecillo(parent_collection, largo=12.0, ancho=5.0, seed=0, **params):
    """Puentecillo de piedra de un arco: X a lo largo, origen en el centro,
    tablero adoquinado a z=0 (ancho `ancho`), pretiles de piedra con
    pilastras fuera de la calzada, arco elíptico con dovelas en relieve y
    cimientos hasta z = -(0.55 + flecha + 1.2). Devuelve el Empty
    'CAMINO_puente' (hijo: _cuerpo)."""
    col = parent_collection
    rng = random.Random(seed)
    raiz = _raiz('%s_puente' % PRE, col)
    L = float(largo)
    pt = 0.35
    W = ancho + 2.0 * pt
    luz = float(params.get('luz', L * 0.62))
    fle = float(params.get('flecha', luz * 0.42))
    z_cl = -0.55
    z_arr = z_cl - fle
    zb = z_arr - float(params.get('cimiento', 1.2))
    mb = _MB()  # 0 piedra_puente, 1 pretil, 2 adoquin, 3 piedra_a, 4 piedra_b, 5 piedra_c
    na = 14
    arco = [(luz / 2.0 * math.cos(math.pi * k / na), z_arr + fle * math.sin(math.pi * k / na))
            for k in range(na + 1)]  # k=0 arranque derecho (+X) ... k=na arranque izquierdo
    # el prisma del cuerpo llega a -0.04: la calzada (caja de 0.04) lo tapa
    # con su cara superior EXACTAMENTE en z=0 (los caminos empalman a ras)
    z_cuerpo = -0.04
    poli = [(-L / 2.0, zb), (-luz / 2.0, zb)] + list(reversed(arco)) + \
           [(luz / 2.0, zb), (L / 2.0, zb), (L / 2.0, z_cuerpo), (-L / 2.0, z_cuerpo)]
    mb.prisma_y(poli, -W / 2.0, W / 2.0, mat=0)
    # calzada, pretiles, albardillas y pilastras
    mb.caja((0.0, 0.0, z_cuerpo / 2.0), (L, ancho, -z_cuerpo), mat=2)
    for sy in (-1.0, 1.0):
        yc = sy * (ancho / 2.0 + pt / 2.0)
        mb.caja((0.0, yc, (0.72 + z_cuerpo) / 2.0), (L - 1.2, pt, 0.72 - z_cuerpo), mat=1)
        mb.caja((0.0, yc, 0.76), (L - 1.2, pt + 0.10, 0.08), mat=5)
        mb.caja((0.0, sy * (W / 2.0 + 0.03), -0.10), (L, 0.06, 0.14), mat=4)  # imposta
        # pilastras de 0.60 con la cara interior a ras del pretil (fuera de la
        # calzada) y prolongadas hasta el cimiento como contrafuertes de esquina
        yp = sy * (ancho / 2.0 + 0.30)
        for sx in (-1.0, 1.0):
            mb.caja((sx * (L / 2.0 - 0.30), yp, (1.0 + zb) / 2.0), (0.60, 0.60, 1.0 - zb), mat=4)
            mb.caja((sx * (L / 2.0 - 0.30), yp, 1.04), (0.70, 0.70, 0.08), mat=5)
            mb.caja((sx * (L / 2.0 - 0.30), yp, 1.16), (0.36, 0.36, 0.16), mat=3)
    # dovelas en relieve en ambas caras
    kx, kz = 1.0 + 0.38 / (luz / 2.0), 1.0 + 0.38 / fle
    for k in range(na):
        i0, i1 = arco[k], arco[k + 1]
        o0 = (i0[0] * kx, z_arr + (i0[1] - z_arr) * kz)
        o1 = (i1[0] * kx, z_arr + (i1[1] - z_arr) * kz)
        q = [i1, i0, o0, o1]
        m = 5 if k % 2 == 0 else 4
        mb.prisma_y(q, -W / 2.0 - 0.06, -W / 2.0 + 0.02, mat=m)
        mb.prisma_y(q, W / 2.0 - 0.02, W / 2.0 + 0.06, mat=m)
    # sillares sueltos en relieve en timpanos y estribos
    def solido(x, z):
        if abs(x) > L / 2.0 - 0.55 or z > -0.30 or z < zb + 0.35:
            return False
        if z > z_arr:
            return (x / (luz / 2.0 + 0.75)) ** 2 + ((z - z_arr) / (fle + 0.75)) ** 2 > 1.0
        return abs(x) > luz / 2.0 + 0.75
    for sy in (-1.0, 1.0):
        puestos = 0
        intentos = 0
        while puestos < 16 and intentos < 400:
            intentos += 1
            x = rng.uniform(-L / 2.0, L / 2.0)
            z = rng.uniform(zb, 0.0)
            if not solido(x, z):
                continue
            mb.bloque((x, sy * W / 2.0, z), (-sy, 0.0, 0.0), (0.0, sy, 0.0),
                      rng.uniform(0.55, 0.95), rng.uniform(0.28, 0.40), 0.04, 0.03, mat=rng.choice((3, 4, 5)))
            puestos += 1
    cuerpo = mb.obj('%s_puente_cuerpo' % PRE,
                    ('piedra_puente', 'pretil', 'adoquin', 'piedra_a', 'piedra_b', 'piedra_c'), col)
    cuerpo.parent = raiz
    return raiz


# ------------------------------------------------------------ escaparate

def z_demo(x, y):
    """Terreno analitico del escaparate: llano en la carretera principal,
    ladera al 11% hacia +Y con una loma, un torrente (hondonada) en x=46 y
    playa que baja al mar hacia -Y."""
    z = 0.0
    if y > 6.0:
        z += 0.11 * (y - 6.0)
    z += 1.5 * math.exp(-((x - 30.0) ** 2 + (y - 40.0) ** 2) / 900.0)
    if y > 20.0:
        f = min(1.0, (y - 20.0) / 15.0)
        z -= 5.0 * f * math.exp(-((x - 46.0) / 4.2) ** 2)
    if y < -10.0:
        z -= 0.25 * (-10.0 - y)
    return z


def _bezier(p0, p1, p2, paso=3.0):
    """Puntos (x, y) cada ~paso m sobre una Bezier cuadratica."""
    fino = []
    for k in range(201):
        u = k / 200.0
        fino.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
                     (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]))
    acum = [0.0]
    for a, b in zip(fino, fino[1:]):
        acum.append(acum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    n = max(2, int(round(acum[-1] / paso)))
    sal = []
    for k in range(n + 1):
        s = acum[-1] * k / n
        i = min(len(acum) - 2, bisect.bisect_right(acum, s) - 1)
        u = 0.0 if acum[i + 1] - acum[i] < 1e-9 else (s - acum[i]) / (acum[i + 1] - acum[i])
        sal.append((fino[i][0] + (fino[i + 1][0] - fino[i][0]) * u,
                    fino[i][1] + (fino[i + 1][1] - fino[i][1]) * u))
    return sal


def _con_z(xy, dz=0.0):
    return [(x, y, z_demo(x, y) + dz) for x, y in xy]


# (nombre, puntos, semiancho a aplanar en el terreno del test); lo rellena build()
DEMO_TRAZADOS = []


def build(parent_collection, seed=0, **params):
    """Escaparate: carretera principal ficticia (asfalto 10 m) con tres
    empalmes cerrados con valla (lateral de asfalto, calle adoquinada y
    muelle), carteles direccionales, camino de tierra en ladera con muro de
    contencion que salva un torrente por un puentecillo. Todo sobre z_demo."""
    col = parent_collection
    del DEMO_TRAZADOS[:]
    raiz = _raiz('%s_escaparate' % PRE, col)
    hijos = []

    def registrar(nombre, pts, semi):
        DEMO_TRAZADOS.append((nombre, [tuple(p) for p in pts], semi))

    # 1) carretera principal (ficticia): 10 m, bordillos en |y| 5.0..5.25;
    #    vados SOLO en el lado donde empalma cada lateral (punto en el borde)
    ppal = [(x, 0.0, z_demo(x, 0.0)) for x in range(-75, 76, 3)]
    hijos.append(build_camino(col, ppal, ancho=10.0, tipo='asfalto', seed=seed,
                              rebajes=[(-35.0, 5.0, 4.5), (18.0, 5.0, 5.0), (30.0, -5.0, 4.5)]))

    def z_borde_en(x):
        """Cota real del borde de la calzada principal en x (eje - bombeo*5)."""
        return z_demo(x, 0.0) - 0.02 * 5.0

    def arranque(pts, z0):
        """Los dos primeros puntos pasan de z0 (borde de la principal) al terreno."""
        pts[0] = (pts[0][0], pts[0][1], z0)
        pts[1] = (pts[1][0], pts[1][1], (pts[1][2] + z0) / 2.0)
        return pts

    def posar(ob, pts, s, dz=-0.04):
        """Apoya una valla sobre la polilinea en la abscisa s (dz: bombeo)."""
        ob.location, ob.rotation_euler = _sobre_polilinea(pts, s, dz)
    Y0 = 5.2  # los laterales arrancan 5 cm DENTRO del bordillo (sin ranura)
    registrar('principal', ppal, 5.3)
    # 2) lateral de asfalto que sube la ladera, cerrado con valla + cartel;
    #    al final sus bordillos bajan a ras para empalmar con el camino de tierra
    lat = arranque(_con_z(_bezier((-35.0, Y0), (-35.0, 30.0), (-12.0, 46.0))), z_borde_en(-35.0))
    hijos.append(build_camino(col, lat, ancho=5.0, tipo='asfalto', seed=seed + 1, suavizar=1,
                              rebajes=[(-12.0, 46.0, 3.0)]))
    registrar('lateral', lat, 2.8)
    v1 = build_valla_cierre(col, ancho=4.8, seed=seed, texto='CHIUSO')  # calzada libre 5.0
    posar(v1, lat, 2.8)
    c1 = build_cartel(col, texto='CASINO', seed=seed, flecha=1)
    c1.location = (-41.5, 6.6, z_demo(-41.5, 6.6))
    c1.rotation_euler = (0.0, 0.0, math.pi)
    hijos += [v1, c1]
    # 3) camino de tierra en ladera hasta el torrente, muro en el lado de arriba;
    #    misma anchura que el lateral y transicion de 6 m (sin ruido ni bermas)
    z_puente = (z_demo(40.0, 64.0) + z_demo(52.0, 64.0)) / 2.0
    t1 = _con_z(_bezier((-12.0, 46.0), (12.0, 54.0), (40.0, 64.0)))
    t1[-1] = (t1[-1][0], t1[-1][1], z_puente)
    t1[-2] = (t1[-2][0], t1[-2][1], (t1[-2][2] + z_puente) / 2.0)
    hijos.append(build_camino(col, t1, ancho=5.0, tipo='tierra', seed=seed + 2,
                              transicion_ini=6.0, transicion_fin=6.0))
    registrar('tierra1', t1, 3.2)
    fr = _frames(t1)
    muro = [(P.x + n.x * 3.6, P.y + n.y * 3.6, P.z) for P, t, n, s in fr[1:-1]]
    hijos.append(build_muro_contencion(col, muro, alto=1.6, seed=seed + 3, relieve='der'))
    registrar('muro', muro, 1.2)
    # 4) puentecillo sobre el torrente (misma anchura 5.0 que los caminos de
    #    tierra, que llegan y salen con transicion de 6 m) y camino que sigue
    #    monte arriba
    pu = build_puentecillo(col, largo=12.0, ancho=5.0, seed=seed)
    pu.location = (46.0, 64.0, z_puente)
    hijos.append(pu)
    t2 = _con_z(_bezier((52.0, 64.0), (66.0, 70.0), (78.0, 84.0)))
    t2[0] = (t2[0][0], t2[0][1], z_puente)
    t2[1] = (t2[1][0], t2[1][1], (t2[1][2] + z_puente) / 2.0)
    hijos.append(build_camino(col, t2, ancho=5.0, tipo='tierra', seed=seed + 4, transicion_ini=6.0))
    registrar('tierra2', t2, 3.2)
    # 5) calle adoquinada del pueblo, cerrada con valla, cartel de dos lineas
    ad = arranque(_con_z(_bezier((18.0, Y0), (17.0, 22.0), (24.0, 42.0))), z_borde_en(18.0))
    hijos.append(build_camino(col, ad, ancho=4.5, tipo='adoquin', seed=seed + 5, suavizar=1))
    registrar('adoquin', ad, 3.3)
    v2 = build_valla_cierre(col, ancho=4.3, seed=seed + 1, texto='CERRADO')  # calzada libre 4.5
    posar(v2, ad, 2.8)
    c2 = build_cartel(col, texto=['CENTRO', 'STAZIONE'], seed=seed, flecha=[-1, 0])
    c2.location = (25.5, 6.6, z_demo(25.5, 6.6))
    c2.rotation_euler = (0.0, 0.0, math.pi)
    hijos += [v2, c2]
    # 6) muelle de piedra que sale al mar: arranca en la cota del borde de la
    #    principal y sube en rampa suave hasta +0.6 m
    mu_xy = _bezier((30.0, -Y0), (30.0, -22.0), (75.0, -34.0))
    zb = z_borde_en(30.0)
    mu = []
    s = 0.0
    for k, (x, y) in enumerate(mu_xy):
        if k > 0:
            s += math.hypot(x - mu_xy[k - 1][0], y - mu_xy[k - 1][1])
        mu.append((x, y, zb + (0.6 - zb) * min(1.0, s / 14.0)))
    hijos.append(build_camino(col, mu, ancho=5.0, tipo='muelle', seed=seed + 6, canto=2.4,
                              nivel_agua=-0.4))  # el mar del test esta a z=-0.4
    registrar('muelle', mu, 0.0)
    # valla de 2 modulos (4.8 m) entre los pretiles (calzada libre 5.0 m)
    v3 = build_valla_cierre(col, ancho=4.8, seed=seed + 2, texto='MOLO CHIUSO')
    posar(v3, mu, 3.0)
    hijos.append(v3)
    for h in hijos:
        h.parent = raiz
    return raiz
