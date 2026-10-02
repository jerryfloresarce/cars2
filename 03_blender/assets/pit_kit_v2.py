"""pit_kit_v2.py — Complejo de boxes de Porto Corsa (Cars 2) para Blender 5.1.

VERSION 2: misma API publica y mismos nombres de raiz que pit_kit.py, con
mucho mas estilo: materiales con RELIEVE y REFLEJOS (nodos procedurales
ShaderNodeTexNoise + ShaderNodeBump, vidrio con Coat, metal, techo azul
brillante, hormigon con grano, pintura de coche con laca), geometria con
sombras propias (pilastras de 0.20 m de relieve, marquesina volada de 1.2 m
con mensulas sobre los portones, cornisas, persianas con lamas en relieve,
balaustrada con balaustres en la galeria, cantos en las terrazas, focos bajo el
techo, banderas onduladas en malla), pancartas de patrocinio con texto 3D
(MONDIALE GP, ALLINOL, REVIOLI, CARBONARA, FORZA) en el peto de la grada y en
el muro trasero, interior de los boxes equipado (elevador, carro de
herramientas, pilas de ruedas con perfil de hombro y llantas cromadas, un
par de ruedas tumbadas de lado con la llanta a la vista, monitores y
luminarias emisivas, suelo con banda de equipo y numero pintado grande), muro
de boxes
con sombrillas de equipo, extintores, bidones, pila de ruedas y valla de tubos
cromados, y la NUEVA pieza PIT_marcas (marcas viales del pit lane).

Convenciones (CONTRATO.md): metros, origen en el centro de la base, z=0 en el
suelo, FACHADA PRINCIPAL A +Y (los portones miran a +Y = pit lane / pista).
Mallas por codigo (from_pydata), Principled BSDF de color plano + nodos
procedurales (SIN imagenes), materiales MAT_PIT_<clave> reutilizados por
nombre, objetos con prefijo PIT_. Cada malla solo lleva los slots de material
que usa de verdad (_MG.obj compacta los indices) y todo lo que va en color de
equipo (8 colores) se agrupa en una malla propia por pieza para ahorrar draw
calls al exportar a AC. Capas pintadas / textos separados >= 0.03 m de la
superficie de debajo (sin z-fighting lejano).

Piezas (API identica a pit_kit.py + build_marcas_pit_lane):
- build_boxes_tribuna(parent, n=20, ancho_box=6.0, seed=0, **params)
    Edificio completo. Huella: x en [-n*ancho_box/2, n*ancho_box/2],
    y en [-6.5, 6.5] (+0.3 m de vuelo del techo por detras y por los lados;
    por delante la marquesina vuela 1.2 m + placas 0.06 + numeros 0.03:
    bbox y -6.8..7.79), altura 17.58 (imposta del techo). Portones abiertos
    (persiana enrollada, faldon metalico de lamas de 0.6 m) en y=+6.5. Raiz:
    Empty 'PIT_boxes'. Hijos:
    PIT_boxes_edificio, PIT_boxes_grada, PIT_boxes_techo, PIT_boxes_publico,
    PIT_boxes_numeros (los n numeros de la marquesina en una malla),
    PIT_boxes_rotulo (si L >= 40) y NUEVOS: PIT_boxes_utillaje (interior de los
    garajes + luminarias y focos emisivos), PIT_boxes_equipos (TODO lo que va
    en color de equipo: dintel, marco y lamas de la persiana, placa de la
    marquesina, banda del fondo, banda y numero pintados en el suelo, armario
    y carro del garaje, bandas de las pancartas traseras; 8 materiales),
    PIT_boxes_banderas (banderas onduladas, doble cara) y PIT_boxes_pancartas
    (textos de patrocinio del peto y del muro trasero).
    Grada: `filas` terrazas de 1.15 m de subida, la primera pegada al peto
    delantero (0.65 m); publico a tresbolillo, paso 1.55 m.
    params: filas=7, ocupacion=0.97, max_tris=90000, banderas=True,
    pancartas=True.
- plazas_boxes(n=20, ancho_box=6.0) -> [(x, y, rot_z), ...]
    Plaza de cada box (coords locales del edificio): centro a 3 m del porton
    hacia dentro (y = 3.5), morro hacia -Y (rot_z = pi).
- build_muro_boxes(parent, largo=12.0, seed=0, tapa_x0=False, tapa_x1=False,
    equipo=True): tramo de muro de boxes a lo largo de X: podio de hormigon
    de 1.1 m (y en [-2.0, 0.2]) con valla de captura de tubos cromados al lado
    de pista (+Y); encima, puestos de equipo techados (pupitre con monitores
    emisivos, pit board, sombrilla de equipo, extintor, bidones, pila de
    ruedas, plataforma para el equipo, parapeto hacia el pit lane). Huella y en
    [-2.05, 0.30] (el pit lane es -Y). Periodo = largo; tapa_x0/tapa_x1
    cierran los extremos. Devuelve la malla PIT_muro_boxes (hijo
    PIT_muro_boxes_equipo con 1-2 coches-mecanico por puesto, 58 tris c/u).
- build_torre_control(parent, alto=16.0, seed=0): torre redonda (fuste con
    ventanas, puerta a pie de calle hacia +Y con portal, marco blanco, doble
    hoja azul con ventanucos y marquesina con luz, tambor de vidrio con Coat,
    balcon anular con balaustres, focos, parabolica, remate y antena). Raiz
    Empty PIT_torre. Radio maximo 3.9 m.
- build_pasarela(parent, luz=22.0, alto=7.0, seed=0): pasarela cubierta sobre
    la pista (pasillo de longitud `luz` a lo largo de X a altura `alto`, entre
    dos torres de celosia con rampas en zigzag), bandas de patrocinio
    tricolor con texto WORLD GRAND PRIX en ambos costados y luminarias.
    Extension total en X = luz + 14.8. Raiz Empty PIT_pasarela.
- build_marcas_pit_lane(parent, largo, ancho_pit=7.5, n=20, ancho_box=6.0,
    seed=0, sentido=-1, z=0.03, numeros='garajes'): NUEVA. Malla plana
    'PIT_marcas' (a z = 0.03 sobre el asfalto, >= 3 cm contra el z-fighting)
    con las marcas del pit lane: origen en el centro del tramo, X a lo largo
    del pit lane, +Y = lado de los garajes (el asfalto del pit lane ocupa y en
    [-ancho_pit/2, ancho_pit/2]). Linea blanca continua en ambos bordes,
    linea amarilla de velocidad limitada (separa el carril rapido del carril
    de trabajo, a 4.2 m del borde de los garajes), caja amarilla de cada box
    (rectangulo de 5.2 x 3.65 con el numero) delante de cada porton y franjas
    de speed limit "60" al principio y al final. `sentido` = sentido de la
    marcha a lo largo de X local (-1 por defecto: girada 180 grados respecto
    al edificio, +Y de la marca = -Y del edificio, el box 1 queda bajo el box
    1 del edificio); los numeros crecen en el sentido de la marcha.
    `numeros` = orientacion de los numeros de las cajas: 'garajes' (legibles
    desde los garajes y en cenital) o 'piloto' (legibles por el piloto que
    circula por el pit lane en el sentido de la marcha, como los "60").
- build(parent, seed=0, **params): escaparate (boxes + pit lane con marcas +
    muro + torres en (+-(L/2+18), 3) + pasarela de 40 m en x = L/2+25, sobre
    asfalto; ni torres ni patas de la pasarela invaden el pit lane ni la
    pista). Raiz Empty PIT_kit.
"""

import math
import random

import bpy

PRE = 'PIT'

# ------------------------------------------------------------------ materiales
# clave: (color, roughness, metallic, color_emision | None, fuerza_emision,
#         efecto). Efectos procedurales (nodos, sin imagenes):
#   'estuco'   ruido fino en relieve (bump) + variacion de rugosidad
#   'hormigon' grano grueso en relieve + variacion de rugosidad
#   'asfalto'  grano muy fino
#   'epoxi'    suelo pintado: grano leve + laca (Coat)
#   'brillo'   pintura brillante (Coat 0.25)
#   'techo'    chapa lacada del techo: sin especular de base (Specular IOR
#              Level 0, que lavaba el azul con el cielo en angulos rasantes) y
#              laca leve (Coat 0.12, IOR 1.25): azul saturado con brillo suave
#   'pintura'  pintura de coche: metalizado leve + laca
#   'vidrio'   Roughness 0.05, Coat 1.0, reflejo alto
#   'metal'    metalico (Metallic/Roughness ya en la tupla)
_PALETA = {
    'crema':        ((0.93, 0.85, 0.64), 0.62, 0.0, None, 0.0, 'estuco'),
    'blanco':       ((0.92, 0.91, 0.88), 0.50, 0.0, None, 0.0, 'estuco'),
    'ocre':         ((0.86, 0.56, 0.22), 0.65, 0.0, None, 0.0, 'estuco'),
    'hormigon':     ((0.62, 0.62, 0.60), 0.85, 0.0, None, 0.0, 'hormigon'),
    'piedra_clara': ((0.60, 0.54, 0.42), 0.85, 0.0, None, 0.0, 'hormigon'),
    'suelo_box':    ((0.40, 0.43, 0.48), 0.30, 0.0, None, 0.0, 'epoxi'),
    'gris_oscuro':  ((0.10, 0.10, 0.11), 0.50, 0.0, None, 0.0, None),
    'gris_acero':   ((0.55, 0.57, 0.60), 0.20, 0.9, None, 0.0, 'metal'),
    'cromo':        ((0.88, 0.89, 0.90), 0.08, 1.0, None, 0.0, 'metal'),
    'negro':        ((0.02, 0.02, 0.02), 0.55, 0.0, None, 0.0, None),
    'goma':         ((0.03, 0.03, 0.03), 0.70, 0.0, None, 0.0, 'hormigon'),
    'asfalto':      ((0.13, 0.13, 0.14), 0.88, 0.0, None, 0.0, 'asfalto'),
    'marca_blanca': ((0.93, 0.93, 0.90), 0.55, 0.0, None, 0.0, 'asfalto'),
    'marca_amarilla': ((0.96, 0.78, 0.08), 0.55, 0.0, None, 0.0, 'asfalto'),
    'azul_techo':   ((0.02, 0.10, 0.55), 0.40, 0.0, None, 0.0, 'techo'),
    'azul_claro':   ((0.42, 0.66, 0.92), 0.40, 0.0, None, 0.0, 'brillo'),
    'azul_oscuro':  ((0.03, 0.08, 0.30), 0.40, 0.0, None, 0.0, 'brillo'),
    'rojo':         ((0.80, 0.08, 0.06), 0.40, 0.0, None, 0.0, 'brillo'),
    'verde_wgp':    ((0.04, 0.58, 0.18), 0.40, 0.0, None, 0.0, 'brillo'),
    'amarillo':     ((0.96, 0.78, 0.08), 0.40, 0.0, None, 0.0, 'brillo'),
    'cristal':      ((0.20, 0.36, 0.50), 0.05, 0.25, None, 0.0, 'vidrio'),
    'pantalla_luz': ((0.04, 0.12, 0.40), 0.10, 0.0, (0.25, 0.55, 1.0), 2.5, 'vidrio'),
    'luz_blanca':   ((0.95, 0.95, 0.90), 0.30, 0.0, (1.0, 0.97, 0.88), 6.0, None),
    'rojo_luz':     ((0.85, 0.04, 0.02), 0.40, 0.0, (1.0, 0.04, 0.02), 6.0, None),
    'pub_rojo':     ((0.80, 0.08, 0.06), 0.35, 0.0, None, 0.0, 'pintura'),
    'pub_azul':     ((0.08, 0.22, 0.78), 0.35, 0.0, None, 0.0, 'pintura'),
    'pub_amarillo': ((0.95, 0.72, 0.08), 0.35, 0.0, None, 0.0, 'pintura'),
    'pub_verde':    ((0.10, 0.58, 0.16), 0.35, 0.0, None, 0.0, 'pintura'),
    'pub_naranja':  ((0.90, 0.36, 0.04), 0.35, 0.0, None, 0.0, 'pintura'),
    'pub_morado':   ((0.42, 0.09, 0.58), 0.35, 0.0, None, 0.0, 'pintura'),
    'pub_cian':     ((0.08, 0.62, 0.68), 0.35, 0.0, None, 0.0, 'pintura'),
    'pub_blanco':   ((0.90, 0.90, 0.88), 0.35, 0.0, None, 0.0, 'pintura'),
    'pub_cristal':  ((0.20, 0.33, 0.45), 0.10, 0.2, None, 0.0, 'vidrio'),
}

_PUBLICO = ('pub_rojo', 'pub_azul', 'pub_amarillo', 'pub_verde',
            'pub_naranja', 'pub_morado', 'pub_cian', 'pub_blanco')
# colores de equipo de los boxes (marquesina, lintel, persiana, suelo, puestos)
_EQUIPOS = ('pub_rojo', 'pub_azul', 'pub_amarillo', 'pub_verde',
            'pub_naranja', 'pub_morado', 'pub_cian', 'verde_wgp')
# pancartas de patrocinio: (texto, clave de la banda, clave del texto)
_PATROCINIOS = (('MONDIALE GP', 'azul_oscuro', 'blanco'),
                ('ALLINOL', 'verde_wgp', 'blanco'),
                ('REVIOLI', 'rojo', 'blanco'),
                ('CARBONARA', 'amarillo', 'gris_oscuro'),
                ('FORZA', 'pub_naranja', 'blanco'))
# parametros de relieve por efecto: (escala del ruido 1/m, detalle,
#                                    fuerza del bump, distancia, +-rugosidad)
_RELIEVE = {
    'estuco':   (9.0, 4.0, 0.30, 0.015, 0.08),
    'hormigon': (18.0, 5.0, 0.45, 0.025, 0.12),
    'asfalto':  (35.0, 6.0, 0.35, 0.012, 0.08),
    'epoxi':    (6.0, 3.0, 0.12, 0.010, 0.06),
}


def _set(entradas, nombre, valor):
    """Asigna `valor` al socket `nombre` si existe (API tolerante)."""
    if nombre in entradas:
        try:
            entradas[nombre].default_value = valor
            return True
        except (TypeError, ValueError):
            return False
    return False

def _bsdf_de(m):
    """Devuelve el Principled BSDF del material (lo crea si falta). En Blender
    5.x los materiales nuevos ya traen node_tree; `use_nodes` (deprecado,
    desaparece en 6.0) solo se toca si falta el arbol."""
    nt = getattr(m, 'node_tree', None)
    if nt is None:
        try:
            m.use_nodes = True
        except AttributeError:
            pass
        nt = getattr(m, 'node_tree', None)
    if nt is None:
        return None, None
    bsdf = None
    for nd in nt.nodes:
        if nd.type == 'BSDF_PRINCIPLED':
            bsdf = nd
            break
    if bsdf is None:
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        salida = None
        for nd in nt.nodes:
            if nd.type == 'OUTPUT_MATERIAL':
                salida = nd
                break
        if salida is None:
            salida = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bsdf.outputs['BSDF'], salida.inputs['Surface'])
    return nt, bsdf


def _relieve(nt, bsdf, efecto, rough):
    """Ruido procedural (coordenadas de objeto, escala en 1/m) -> Bump en la
    normal + variacion de rugosidad. Sin imagenes."""
    escala, detalle, fuerza, dist, var = _RELIEVE[efecto]
    px, py = bsdf.location
    tc = nt.nodes.new('ShaderNodeTexCoord')
    tc.name = 'PIT_coord'
    tc.location = (px - 900, py - 300)
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.name = 'PIT_ruido'
    nz.location = (px - 680, py - 300)
    _set(nz.inputs, 'Scale', escala)
    _set(nz.inputs, 'Detail', detalle)
    _set(nz.inputs, 'Roughness', 0.55)
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.name = 'PIT_bump'
    bump.location = (px - 300, py - 420)
    _set(bump.inputs, 'Strength', fuerza)
    _set(bump.inputs, 'Distance', dist)
    nt.links.new(nz.outputs[0], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    if var > 0.0:
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.name = 'PIT_rugosidad'
        mr.location = (px - 300, py - 150)
        _set(mr.inputs, 'From Min', 0.0)
        _set(mr.inputs, 'From Max', 1.0)
        _set(mr.inputs, 'To Min', max(0.02, rough - var))
        _set(mr.inputs, 'To Max', min(1.0, rough + var))
        nt.links.new(nz.outputs[0], mr.inputs['Value'])
        nt.links.new(mr.outputs['Result'], bsdf.inputs['Roughness'])


def _mat(clave):
    """Crea (o reutiliza) el material MAT_PIT_<clave> de la paleta, con su
    efecto procedural (relieve, laca, vidrio, metal)."""
    nombre = 'MAT_%s_%s' % (PRE, clave)
    m = bpy.data.materials.get(nombre)
    if m is not None:
        return m
    color, rough, metal, emision, fuerza, efecto = _PALETA[clave]
    m = bpy.data.materials.new(nombre)
    nt, bsdf = _bsdf_de(m)
    if bsdf is not None:
        ins = bsdf.inputs
        _set(ins, 'Base Color', (*color, 1.0))
        _set(ins, 'Roughness', rough)
        _set(ins, 'Metallic', metal)
        if emision is not None:
            _set(ins, 'Emission Color', (*emision, 1.0))
            _set(ins, 'Emission Strength', fuerza)
        if efecto in _RELIEVE:
            _relieve(nt, bsdf, efecto, rough)
        if efecto == 'epoxi':
            _set(ins, 'Coat Weight', 0.5)
            _set(ins, 'Coat Roughness', 0.08)
        elif efecto == 'brillo':
            _set(ins, 'Coat Weight', 0.25)
            _set(ins, 'Coat Roughness', 0.12)
            _set(ins, 'Coat IOR', 1.3)
        elif efecto == 'techo':
            _set(ins, 'Specular IOR Level', 0.0)
            _set(ins, 'Coat Weight', 0.12)
            _set(ins, 'Coat Roughness', 0.08)
            _set(ins, 'Coat IOR', 1.25)
        elif efecto == 'pintura':
            _set(ins, 'Metallic', 0.20)
            _set(ins, 'Coat Weight', 0.8)
            _set(ins, 'Coat Roughness', 0.06)
            _set(ins, 'Specular IOR Level', 0.6)
        elif efecto == 'vidrio':
            _set(ins, 'Roughness', 0.05)
            _set(ins, 'Coat Weight', 1.0)
            _set(ins, 'Coat Roughness', 0.03)
            _set(ins, 'Specular IOR Level', 0.8)
        elif efecto == 'metal':
            _set(ins, 'Specular IOR Level', 0.7)
    m.diffuse_color = (*color, 1.0)
    m.roughness = rough
    m.metallic = metal
    return m


# ------------------------------------------------------------ utilidades malla

def _normal_newell(pts):
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1, z1 = pts[i]
        x2, y2, z2 = pts[(i + 1) % n]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return nx, ny, nz


class _MG:
    """Malla generica: poligonos arbitrarios con material y sombreado por cara.
    Cada cara se orienta segun `ref` (normal deseada) o `centro` (punto
    interior del solido)."""

    def __init__(self):
        self.v = []
        self.f = []
        self.fm = []
        self.fs = []

    def verts(self, pts):
        i0 = len(self.v)
        self.v.extend(pts)
        return i0

    def cara(self, ids, mat=0, suave=False, ref=None, centro=None):
        ids = list(ids)
        pts = [self.v[i] for i in ids]
        if ref is None and centro is not None:
            n = float(len(pts))
            ref = (sum(p[0] for p in pts) / n - centro[0],
                   sum(p[1] for p in pts) / n - centro[1],
                   sum(p[2] for p in pts) / n - centro[2])
        if ref is not None:
            nx, ny, nz = _normal_newell(pts)
            if nx * ref[0] + ny * ref[1] + nz * ref[2] < 0.0:
                ids.reverse()
        self.f.append(tuple(ids))
        self.fm.append(mat)
        self.fs.append(bool(suave))

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def obj(self, nombre, claves_mat, col, separar=False):
        """Crea la malla. Solo se anaden los slots de material USADOS por
        alguna cara (en el orden de `claves_mat`; los indices se remapean):
        menos draw calls al exportar y ninguna ranura vacia. Localizar un
        material por nombre (me.materials.find('MAT_PIT_x')), no por indice."""
        v, f = self.v, self.f
        if separar:
            v, f = [], []
            for cara in self.f:
                i0 = len(v)
                v.extend(self.v[i] for i in cara)
                f.append(tuple(range(i0, i0 + len(cara))))
        usados = sorted(set(self.fm))
        remap = {mi: k for k, mi in enumerate(usados)}
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(v, [], f)
        for mi in usados:
            me.materials.append(_mat(claves_mat[mi]))
        for p, mi, su in zip(me.polygons, self.fm, self.fs):
            p.material_index = remap[mi]
            p.use_smooth = su
        me.validate()
        me.update()
        ob = bpy.data.objects.new(nombre, me)
        col.objects.link(ob)
        return ob

def _prisma_x(mg, x0, x1, perfil, mat, omitir=(), mats=None, tf=None):
    """Extruye a lo largo de X el poligono CONVEXO `perfil` = [(y, z), ...].
    Caras: 'x0', 'x1' (tapas) + una por arista k (perfil[k] -> perfil[k+1])."""
    n = len(perfil)
    cy = sum(p[0] for p in perfil) / float(n)
    cz = sum(p[1] for p in perfil) / float(n)
    centro = (0.5 * (x0 + x1), cy, cz)
    pts = [(x0, p[0], p[1]) for p in perfil] + [(x1, p[0], p[1]) for p in perfil]
    if tf is not None:
        pts = [tf(p) for p in pts]
        centro = tf(centro)
    i0 = mg.verts(pts)
    mats = mats or {}
    if 'x0' not in omitir:
        mg.cara([i0 + k for k in range(n)], mats.get('x0', mat), centro=centro)
    if 'x1' not in omitir:
        mg.cara([i0 + n + k for k in range(n)], mats.get('x1', mat), centro=centro)
    for k in range(n):
        if k in omitir:
            continue
        k2 = (k + 1) % n
        mg.cara([i0 + k, i0 + k2, i0 + n + k2, i0 + n + k], mats.get(k, mat),
                centro=centro)


def _caja_g(mg, x0, x1, y0, y1, z0, z1, mat, omitir=(), mats=None, tf=None):
    """Caja alineada a ejes. Aristas: 0 = suelo (z0), 1 = cara +Y (y1),
    2 = techo (z1), 3 = cara -Y (y0); tapas 'x0' / 'x1'."""
    _prisma_x(mg, x0, x1, [(y0, z0), (y1, z0), (y1, z1), (y0, z1)], mat,
              omitir=omitir, mats=mats, tf=tf)


def _quad(mg, pts, mat, ref):
    i = mg.verts(pts)
    mg.cara((i, i + 1, i + 2, i + 3), mat, False, ref=ref)


def _cilindro(mg, cx, cy, z0, z1, r0, mat, r1=None, seg=16, tapa0=False,
              tapa1=True, suave=True, mat_tapas=None, fase=0.0, mat_alt=None):
    """Tronco de cono vertical (radio r0 abajo, r1 arriba) de `seg` lados.
    mat_alt: material de los lados impares (franjas alternas)."""
    r1 = r0 if r1 is None else r1
    a = [fase + 2.0 * math.pi * k / seg for k in range(seg)]
    i0 = mg.verts([(cx + r0 * math.cos(t), cy + r0 * math.sin(t), z0) for t in a])
    i1 = mg.verts([(cx + r1 * math.cos(t), cy + r1 * math.sin(t), z1) for t in a])
    c = (cx, cy, 0.5 * (z0 + z1))
    mt = mat if mat_tapas is None else mat_tapas
    for k in range(seg):
        k2 = (k + 1) % seg
        m = mat if (mat_alt is None or k % 2 == 0) else mat_alt
        mg.cara((i0 + k, i0 + k2, i1 + k2, i1 + k), m, suave, centro=c)
    if tapa0:
        mg.cara(range(i0, i0 + seg), mt, False, ref=(0, 0, -1))
    if tapa1:
        mg.cara(range(i1, i1 + seg), mt, False, ref=(0, 0, 1))


def _cono(mg, cx, cy, z0, z1, r, mat, seg=16, suave=True, mat_alt=None, fase=0.0):
    a = [fase + 2.0 * math.pi * k / seg for k in range(seg)]
    i0 = mg.verts([(cx + r * math.cos(t), cy + r * math.sin(t), z0) for t in a])
    ip = mg.verts([(cx, cy, z1)])
    c = (cx, cy, z0 - 0.5)
    for k in range(seg):
        m = mat if (mat_alt is None or k % 2 == 0) else mat_alt
        mg.cara((i0 + k, i0 + (k + 1) % seg, ip), m, suave, centro=c)


def _anillo(mg, cx, cy, z, r_ext, r_int, mat, seg=12, ref=(0, 0, 1)):
    """Corona circular plana (r_int < r_ext) a la altura z."""
    a = [2.0 * math.pi * k / seg for k in range(seg)]
    ie = mg.verts([(cx + r_ext * math.cos(t), cy + r_ext * math.sin(t), z) for t in a])
    ii = mg.verts([(cx + r_int * math.cos(t), cy + r_int * math.sin(t), z) for t in a])
    for k in range(seg):
        k2 = (k + 1) % seg
        mg.cara((ie + k, ie + k2, ii + k2, ii + k), mat, False, ref=ref)


def _disco(mg, cx, cy, z, r, mat, seg=12, ref=(0, 0, 1), fase=0.0):
    a = [fase + 2.0 * math.pi * k / seg for k in range(seg)]
    i0 = mg.verts([(cx + r * math.cos(t), cy + r * math.sin(t), z) for t in a])
    mg.cara(range(i0, i0 + seg), mat, False, ref=ref)


def _rueda(mg, cx, cy, z0, alto, r, m_goma, m_llanta, seg=12, tapa=True, suave=True,
           fondo=False, tf=None, fase=0.0, m_oscuro=None):
    """Neumatico con PERFIL DE HOMBRO (banda de rodadura de radio r entre
    0.22 y 0.78 del alto, hombros que cierran a 0.90 r arriba y abajo: en una
    pila cada rueda se lee por su ranura) y llanta cromada hundida 2 cm en el
    flanco superior (`tapa`) y/o inferior (`fondo`). Con `m_oscuro` la llanta
    de la tapa es de 5 radios cromados con buje sobre fondo oscuro (se lee
    como llanta y no como agujero); el fondo lleva solo el disco cromado.
    Eje vertical con la base en z0; `tf` transforma los puntos (p. ej. rueda
    tumbada de lado, ver _tf_rueda_lado) y se aplica tambien a la orientacion
    de las caras."""
    T = tf if tf is not None else (lambda p: p)
    rh, ri = 0.90 * r, 0.60 * r
    perfil = [(rh, z0), (r, z0 + 0.22 * alto), (r, z0 + 0.78 * alto), (rh, z0 + alto)]
    a = [fase + 2.0 * math.pi * k / seg for k in range(seg)]
    anillos = [mg.verts([T((cx + rr * math.cos(t), cy + rr * math.sin(t), zz)) for t in a])
               for rr, zz in perfil]
    c = T((cx, cy, z0 + 0.5 * alto))
    for j in range(len(perfil) - 1):
        i0, i1 = anillos[j], anillos[j + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            mg.cara((i0 + k, i0 + k2, i1 + k2, i1 + k), m_goma, suave, centro=c)
    for hacer, zz, i_ext, sgn in ((tapa, z0 + alto, anillos[-1], 1.0),
                                  (fondo, z0, anillos[0], -1.0)):
        if not hacer:
            continue
        p0, p1 = T((cx, cy, zz)), T((cx, cy, zz + sgn))
        ref = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        i_int = mg.verts([T((cx + ri * math.cos(t), cy + ri * math.sin(t), zz)) for t in a])
        for k in range(seg):
            k2 = (k + 1) % seg
            mg.cara((i_ext + k, i_ext + k2, i_int + k2, i_int + k), m_goma, False, ref=ref)
        zl = zz - sgn * 0.02
        con_radios = m_oscuro is not None and sgn > 0.0
        i_ll = mg.verts([T((cx + ri * math.cos(t), cy + ri * math.sin(t), zl)) for t in a])
        mg.cara(range(i_ll, i_ll + seg), m_oscuro if con_radios else m_llanta, False, ref=ref)
        if not con_radios:
            continue
        zr_ = zl + sgn * 0.008
        for k in range(5):
            t = fase + 2.0 * math.pi * k / 5.0
            ct, st = math.cos(t), math.sin(t)
            hw_ = 0.075 * r
            pts = [(cx + 0.16 * r * ct - hw_ * st, cy + 0.16 * r * st + hw_ * ct, zr_),
                   (cx + 0.57 * r * ct - hw_ * st, cy + 0.57 * r * st + hw_ * ct, zr_),
                   (cx + 0.57 * r * ct + hw_ * st, cy + 0.57 * r * st - hw_ * ct, zr_),
                   (cx + 0.16 * r * ct + hw_ * st, cy + 0.16 * r * st - hw_ * ct, zr_)]
            i_r = mg.verts([T(p) for p in pts])
            mg.cara((i_r, i_r + 1, i_r + 2, i_r + 3), m_llanta, False, ref=ref)
        zh_ = zl + sgn * 0.012
        i_h = mg.verts([T((cx + 0.19 * r * math.cos(t), cy + 0.19 * r * math.sin(t), zh_))
                        for t in a[::2]])
        mg.cara(range(i_h, i_h + len(a[::2])), m_llanta, False, ref=ref)


def _tf_rueda_lado(cx, cy, z0, r, hacia=1.0):
    """Transformacion para una rueda TUMBADA DE LADO (eje horizontal a lo largo
    de Y) apoyada en el suelo en (cx, cy, z0): el eje local Z de _rueda pasa a
    +Y (hacia=1: la llanta de la tapa mira a +Y) o a -Y. Llamar a _rueda con
    cx=cy=z0=0 y este tf."""
    def tf(p):
        return (cx + p[0], cy + hacia * p[2], z0 + r + p[1])
    return tf


def _losa(mg, x0, x1, y0, y1, za, zb, esp, mat, omitir=()):
    """Losa inclinada a lo largo de X: cara superior de z=za (en x0) a z=zb
    (en x1), espesor `esp`. Caras: 0 suelo, 1 +Y, 2 arriba, 3 -Y, 'x0', 'x1'."""
    p = [(x0, y0, za - esp), (x1, y0, zb - esp), (x1, y1, zb - esp), (x0, y1, za - esp),
         (x0, y0, za), (x1, y0, zb), (x1, y1, zb), (x0, y1, za)]
    i = mg.verts(p)
    c = (0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (za + zb) - 0.5 * esp)
    caras = {0: (0, 1, 2, 3), 1: (3, 2, 6, 7), 2: (4, 5, 6, 7), 3: (0, 1, 5, 4),
             'x0': (0, 3, 7, 4), 'x1': (1, 2, 6, 5)}
    for k, q in caras.items():
        if k in omitir:
            continue
        mg.cara([i + j for j in q], mat, False, centro=c)


def _bandera(mg, xp, yp, z0, z1, largo, mats, fase, nx=6, nz=2, amp=0.09):
    """Bandera ondulada (malla de nx x nz quads, doble cara) colgada del
    mastil en x=xp hacia +X, entre z0 y z1. mats = un material por tercio
    (bandas verticales verde/blanco/rojo)."""
    ondas = 1.6 * math.pi / max(largo, 1e-6)
    filas = []
    for j in range(nz + 1):
        fila = []
        for i in range(nx + 1):
            u = i / float(nx)
            x = xp + u * largo
            y = yp + amp * u * math.sin(ondas * u * largo + fase + 0.8 * j)
            z = z1 - (z1 - z0) * j / float(nz)
            fila.append((x, y, z))
        filas.append(fila)
    for j in range(nz):
        for i in range(nx):
            m = mats[min(len(mats) - 1, (i * len(mats)) // nx)]
            pts = [filas[j][i], filas[j][i + 1], filas[j + 1][i + 1], filas[j + 1][i]]
            ia = mg.verts(pts)
            mg.cara((ia, ia + 1, ia + 2, ia + 3), m, False, ref=(0.0, -1.0, 0.0))
            ib = mg.verts(pts)
            mg.cara((ib, ib + 1, ib + 2, ib + 3), m, False, ref=(0.0, 1.0, 0.0))


def _raiz(nombre, col):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_size = 0.5
    col.objects.link(e)
    return e

def _textos_multi(nombre, items, col, extrude=0.0, plano=False, resolucion=1):
    """Varios textos 3D en UNA malla `nombre` con varios materiales:
    items = [(texto, tam, (x, y, z), rot_z, clave_mat[, plano]), ...]. Cada
    texto se centra en (x, y, z) (el 6o elemento opcional fija plano/de pie
    por item):
    - plano=False: de pie y legible desde +Y (rot_z = 0) o girado rot_z sobre Z
      (pi: legible desde -Y).
    - plano=True: tumbado en el plano XY (normal +Z), legible desde -Y mirando
      hacia +Y con rot_z = 0 (orientacion normal visto desde arriba); rot_z
      gira el texto sobre Z.
    La curva FONT se convierte con meshes.new_from_object sobre un objeto
    temporal sin enlazar (no toca el depsgraph); las transformaciones se
    hornean en los vertices (objeto con transform identidad). extrude=0 da
    solo la cara frontal (texto pintado / placa), orientada hacia el lector."""
    claves = []
    for it in items:
        if it[4] not in claves:
            claves.append(it[4])
    vs, fs, fm, fn = [], [], [], []
    for it in items:
        texto, tam, (x, y, z), rot_z, clave = it[:5]
        plano_it = bool(it[5]) if len(it) > 5 else plano
        cu = bpy.data.curves.new(nombre + '_cu', type='FONT')
        cu.body = texto
        cu.size = tam
        cu.extrude = extrude
        cu.align_x = 'CENTER'
        cu.align_y = 'CENTER'
        cu.resolution_u = resolucion
        tmp = bpy.data.objects.new(nombre + '_tmp', cu)
        me_t = bpy.data.meshes.new_from_object(tmp)
        bpy.data.objects.remove(tmp)
        bpy.data.curves.remove(cu)
        i0 = len(vs)
        if plano_it:
            co, si = math.cos(rot_z), math.sin(rot_z)
            for v in me_t.vertices:
                px, py, pz = v.co.x, v.co.y, v.co.z
                vs.append((x + px * co - py * si, y + px * si + py * co, z + pz))
            deseada = (0.0, 0.0, 1.0)
        else:
            # Rx(90): (x, y, z) -> (x, -z, y); luego Rz(pi + rot_z) y traslacion
            co, si = math.cos(math.pi + rot_z), math.sin(math.pi + rot_z)
            for v in me_t.vertices:
                px, py, pz = v.co.x, -v.co.z, v.co.y
                vs.append((x + px * co - py * si, y + px * si + py * co, z + pz))
            deseada = (-math.sin(rot_z), math.cos(rot_z), 0.0)
        mi = claves.index(clave)
        for p in me_t.polygons:
            fs.append(tuple(i0 + i for i in p.vertices))
            fm.append(mi)
            fn.append(deseada)
        bpy.data.meshes.remove(me_t)
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(vs, [], fs)
    for clave in claves:
        me.materials.append(_mat(clave))
    for p, mi in zip(me.polygons, fm):
        p.material_index = mi
    me.validate()
    me.update()
    if extrude <= 0.0 and len(me.polygons) == len(fn):
        # cara unica por letra: que mire hacia el lector
        for p, d in zip(me.polygons, fn):
            n = p.normal
            if n.x * d[0] + n.y * d[1] + n.z * d[2] < 0.0:
                p.flip()
        me.update()
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    return ob


def _textos_malla(nombre, items, clave_mat, col, extrude=0.05, plano=False,
                  resolucion=2):
    """Varios textos con un solo material: items = [(texto, tam, (x, y, z),
    rot_z), ...] (ver _textos_multi)."""
    return _textos_multi(nombre, [(t, s, p, r, clave_mat) for t, s, p, r in items],
                         col, extrude=extrude, plano=plano, resolucion=resolucion)


def _texto_3d(nombre, texto, tam, clave_mat, col, extrude=0.05, pos=(0.0, 0.0, 0.0),
              rot_z=0.0, plano=False, resolucion=2):
    """Texto 3D suelto (malla `nombre`), centrado en `pos`, de pie y legible
    desde +Y (rot_z = pi: desde -Y) o tumbado (plano=True)."""
    return _textos_multi(nombre, [(texto, tam, pos, rot_z, clave_mat)], col,
                         extrude=extrude, plano=plano, resolucion=resolucion)

# ------------------------------------------------ coches-espectador (publico)

_PUB_MATS = ('pub_cristal',) + _PUBLICO + ('negro', 'crema')
_PM_CRISTAL = 0
_PM_PILOTO = 1 + _PUBLICO.index('pub_rojo')
_PM_OJO = 1 + _PUBLICO.index('pub_blanco')
_PM_NEGRO = 1 + len(_PUBLICO)
_PM_FARO = 2 + len(_PUBLICO)
_PUB_TRIS = 58          # triangulos exactos por coche-espectador (<= 60)
_PUB_PESOS_COLOR = (5, 4, 4, 3, 3, 2, 2, 3)
_ANG6 = tuple(k * math.pi / 3.0 for k in range(6))
_ANG4 = tuple(math.pi / 4.0 + k * math.pi / 2.0 for k in range(4))


def _pub_coche(mg, pos, rz, W, L, e, mi, mirada, boca_abierta, tipo=0):
    """Coche-espectador de 58 tris con el morro a +Y local: carroceria en
    tronco octogonal (faros/pilotos en los chaflanes), cabina con parabrisas y
    luneta mates, dos ojos con pupila, boca y dos ejes de ruedas.
    pos = (x, y, z suelo); mirada = (du, dv) en [-1, 1] (pupilas)."""
    x, y, z = pos
    co, si = math.cos(rz), math.sin(rz)
    # tipo 0 berlina, 1 deportivo (bajo), 2 furgoneta (alta)
    H = (1.00, 0.86, 1.18)[tipo] * e
    yb_f, yt_f = (0.20, 0.13, 0.33)[tipo] * L, (0.03, -0.08, 0.24)[tipo] * L
    yt_r, yb_r = (-0.30, -0.30, -0.40)[tipo] * L, (-0.43, -0.44, -0.45)[tipo] * L
    zc_f, zc_r = (0.52, 0.47, 0.56)[tipo] * e, (0.58, 0.55, 0.60)[tipo] * e

    def T(p):
        return (x + p[0] * co - p[1] * si, y + p[0] * si + p[1] * co, z + p[2])

    def R(v):
        return (v[0] * co - v[1] * si, v[0] * si + v[1] * co, v[2])

    def anillo(hw, yf, yr, ch, zf, zr):
        plan = ((hw, yf - ch), (hw - ch, yf), (-(hw - ch), yf), (-hw, yf - ch),
                (-hw, yr + ch), (-(hw - ch), yr), (hw - ch, yr), (hw, yr + ch))
        return [(px, py, zr + (zf - zr) * (py - yr) / (yf - yr)) for px, py in plan]

    # carroceria: faldon -> borde del capo (8 quads) + capo/maletero plano
    r0 = anillo(0.45 * W, 0.46 * L, -0.46 * L, 0.12 * W, 0.13 * e, 0.13 * e)
    r1 = anillo(0.50 * W, 0.50 * L, -0.50 * L, 0.17 * W, zc_f, zc_r)
    i0 = mg.verts([T(p) for p in r0 + r1])
    cb = T((0.0, 0.0, 0.30 * e))
    for j in range(8):
        j2 = (j + 1) % 8
        m = mi
        if j in (0, 2):
            m = _PM_FARO
        elif j in (4, 6):
            m = _PM_PILOTO
        mg.cara((i0 + j, i0 + j2, i0 + 8 + j2, i0 + 8 + j), m, True, centro=cb)
    mg.cara([i0 + 8 + j for j in range(8)], mi, False, ref=(0.0, 0.0, 1.0))

    # cabina (hundida 4 cm en el capo)
    z_cb = min(zc_f, zc_r) - 0.04 * e
    hb, ht = 0.41 * W, 0.31 * W
    cab = [(hb, yb_f, z_cb), (-hb, yb_f, z_cb), (-hb, yb_r, z_cb), (hb, yb_r, z_cb),
           (ht, yt_f, H), (-ht, yt_f, H), (-ht, yt_r, H), (ht, yt_r, H)]
    i1 = mg.verts([T(p) for p in cab])
    cc = T((0.0, 0.5 * (yb_f + yb_r), 0.5 * (z_cb + H)))
    for a, b, m in ((0, 1, _PM_CRISTAL), (1, 2, mi), (2, 3, _PM_CRISTAL), (3, 0, mi)):
        mg.cara((i1 + a, i1 + b, i1 + 4 + b, i1 + 4 + a), m, False, centro=cc)
    mg.cara((i1 + 4, i1 + 5, i1 + 6, i1 + 7), mi, False, ref=(0.0, 0.0, 1.0))

    # ojos sobre el parabrisas (hexagono blanco + pupila cuadrada)
    ty, tz = yt_f - yb_f, H - z_cb
    sl = math.hypot(ty, tz)
    ty, tz = ty / sl, tz / sl
    nl = (0.0, tz, -ty)
    nw = R(nl)
    v_c = 0.56 * sl
    hw_v = hb + (ht - hb) * 0.56
    u_c = 0.5 * (hw_v - 0.01)
    ru = min(0.21 * e, u_c - 0.015)
    rv = min(0.21 * e, 0.36 * sl)
    rp = 0.46 * min(ru, rv)

    def P(u, v, off):
        return T((u, yb_f + ty * v + nl[1] * off, z_cb + tz * v + nl[2] * off))

    du = max(-1.0, min(1.0, mirada[0]))
    dv = max(-1.0, min(1.0, mirada[1]))
    for sx in (-1.0, 1.0):
        ue = sx * u_c
        ie = mg.verts([P(ue + ru * math.cos(a), v_c + rv * math.sin(a), 0.04)
                       for a in _ANG6])
        mg.cara(range(ie, ie + 6), _PM_OJO, False, ref=nw)
        pu = ue + du * (ru - rp - 0.012)
        pv = v_c + dv * (rv - rp - 0.012)
        ip = mg.verts([P(pu + rp * math.cos(a), pv + rp * math.sin(a), 0.07)
                       for a in _ANG4])
        mg.cara(range(ip, ip + 4), _PM_NEGRO, False, ref=nw)

    # boca sobre el morro (cara frontal del tronco), 4 cm por delante
    ym0, zm0 = 0.46 * L, 0.13 * e
    ym1, zm1 = 0.50 * L, zc_f
    ml = math.hypot(ym1 - ym0, zm1 - zm0)
    nb = ((zm1 - zm0) / ml, -(ym1 - ym0) / ml)

    def B(u, w):
        return T((u, ym0 + (ym1 - ym0) * w + nb[0] * 0.04,
                  zm0 + (zm1 - zm0) * w + nb[1] * 0.04))

    m_ = 0.27 * W
    if boca_abierta:
        pts = [B(-m_, 0.80), B(m_, 0.80), B(0.55 * m_, 0.35), B(-0.55 * m_, 0.35)]
    else:
        pts = [B(-m_, 0.72), B(m_, 0.72), B(0.75 * m_, 0.55), B(-0.75 * m_, 0.55)]
    ib = mg.verts(pts)
    mg.cara(range(ib, ib + 4), _PM_NEGRO, False, ref=R((0.0, 1.0, 0.0)))

    # ruedas: dos ejes-caja bajo el faldon (costados + cara exterior del eje)
    hwr = 0.5 * W + 0.03
    rr = 0.17 * e
    zr_ = 0.32 * e
    for ya, delante in ((0.28 * L, True), (-0.28 * L, False)):
        ia = mg.verts([T(p) for p in (
            (-hwr, ya - rr, 0.0), (hwr, ya - rr, 0.0), (hwr, ya + rr, 0.0),
            (-hwr, ya + rr, 0.0), (-hwr, ya - rr, zr_), (hwr, ya - rr, zr_),
            (hwr, ya + rr, zr_), (-hwr, ya + rr, zr_))])
        mg.cara((ia, ia + 3, ia + 7, ia + 4), _PM_NEGRO, False, ref=R((-1.0, 0.0, 0.0)))
        mg.cara((ia + 1, ia + 2, ia + 6, ia + 5), _PM_NEGRO, False, ref=R((1.0, 0.0, 0.0)))
        if delante:
            mg.cara((ia + 3, ia + 2, ia + 6, ia + 7), _PM_NEGRO, False,
                    ref=R((0.0, 1.0, 0.0)))
        else:
            mg.cara((ia, ia + 1, ia + 5, ia + 4), _PM_NEGRO, False,
                    ref=R((0.0, -1.0, 0.0)))


# ------------------------------------------------------------- geometria comun

_FONDO = 13.0        # fondo total del edificio (y en [-6.5, 6.5])
_H_GARAJE = 4.5      # altura libre de los garajes
_Z_GALERIA = 5.0     # suelo de la planta de servicio (galeria)
_Z_GRADA = 8.4       # suelo de la grada (cara superior de su losa)
_Z_TECHO = 17.2      # cara inferior del techo azul (vigas de 0.35 por debajo)
_RISE = 1.15         # subida por terraza (grada empinada: el publico asoma
                     # sobre el peto desde la pista a la altura de un piloto)
_H_PETO = 0.65       # altura del peto delantero de la grada
_PASO_PUB = 1.55     # paso del publico en X (coches pegados, a tresbolillo)


def plazas_boxes(n=20, ancho_box=6.0):
    """Plazas de aparcamiento de los n boxes en coordenadas locales del
    edificio: lista de (x, y, rot_z). Centro a 3 m del porton (y = 6.5 - 3.0),
    morro hacia -Y (rot_z = pi para un coche que sin girar mira a +Y)."""
    n = max(1, int(n))
    w = float(ancho_box)
    a2 = 0.5 * n * w
    y = 0.5 * _FONDO - 3.0
    return [(-a2 + (i + 0.5) * w, y, math.pi) for i in range(n)]


# ---------------------------------------------------------- edificio de boxes

_Z_MARQ = 4.42       # cara inferior de la marquesina (su cara superior = z_gal)
_V_MARQ = 1.20       # vuelo de la marquesina sobre los portones


def build_boxes_tribuna(parent_collection, n=20, ancho_box=6.0, seed=0, **params):
    """Edificio de boxes con grada encima (ver docstring del modulo).
    params: filas=7, ocupacion=0.97, max_tris=90000, banderas=True,
    pancartas=True."""
    col = parent_collection
    raiz = _raiz('%s_boxes' % PRE, col)
    rng = random.Random(seed)

    n = max(1, int(n))
    w = float(ancho_box)
    L = n * w
    a2 = L / 2.0
    filas = max(1, int(params.get('filas', 7)))
    ocupacion = float(params.get('ocupacion', 0.97))
    max_tris = int(params.get('max_tris', 90000))
    banderas = bool(params.get('banderas', True))
    pancartas = bool(params.get('pancartas', True))

    y_f = 0.5 * _FONDO            # fachada de los portones (+Y)
    y_b = -0.5 * _FONDO           # fachada trasera (paddock)
    y_g = y_f - 6.0               # cara interior del fondo de los garajes
    y_s = 5.0                     # fachada de la planta de servicio (galeria)
    y_w = y_b + 0.4               # cara interior del muro trasero de la grada
    e_m = 0.3                     # espesor de muros
    z_g = _H_GARAJE               # techo libre garaje
    z_gal = _Z_GALERIA
    z_l0 = _Z_GRADA - 0.4         # cara inferior de la losa de la grada
    z_gr = _Z_GRADA
    z_r = _Z_TECHO
    z_mq = _Z_MARQ
    j_w = min(0.6, 0.12 * w)      # semiancho de la jamba (pilastra) del porton
    h_p = 4.0                     # altura del hueco del porton
    xs_b = [-a2 + i * w for i in range(n + 1)]     # limites de los boxes
    cxs = [-a2 + (i + 0.5) * w for i in range(n)]
    hw = 0.5 * w

    # ============================================================ edificio
    (E_CREMA, E_BLANCO, E_OSCURO, E_SUELO, E_ROJO, E_CRISTAL, E_ACERO,
     E_HORM, E_OCRE) = range(9)
    me = _MG()
    # utillaje interior + luminarias (malla aparte, con cilindros suaves)
    (U_ACERO, U_OSCURO, U_GOMA, U_CROMO, U_PANT, U_LUZ, U_AMAR, U_NEGRO) = range(8)
    mu = _MG()
    # todo lo que va en color de equipo, en una malla aparte con 8 slots
    # (indice = equipo) en vez de 8 slots mas en cada malla: menos draw calls
    mE = _MG()
    textos_panc = []              # (texto, tam, pos, rot_z, clave) -> pancartas
    xi0, xi1 = -a2 + e_m, a2 - e_m           # interior entre muros de testero

    # --- garajes: suelo epoxi, techo, fondo, tabiques
    _quad(me, [(xi0, y_g, 0.02), (xi1, y_g, 0.02), (xi1, y_f, 0.02), (xi0, y_f, 0.02)],
          E_SUELO, (0, 0, 1))
    _quad(me, [(xi0, y_g, z_g), (xi1, y_g, z_g), (xi1, y_f - e_m, z_g), (xi0, y_f - e_m, z_g)],
          E_HORM, (0, 0, -1))
    _quad(me, [(xi0, y_g, 0.0), (xi1, y_g, 0.0), (xi1, y_g, z_g), (xi0, y_g, z_g)],
          E_HORM, (0, 1, 0))
    for i in range(1, n):
        xb = xs_b[i]
        _caja_g(me, xb - 0.15, xb + 0.15, y_g, y_f - e_m, 0.0, z_g, E_HORM,
                omitir=(0, 1, 2, 3))
    yd = y_f - e_m - 0.30         # eje del tambor de la persiana
    for i in range(n):
        cx = cxs[i]
        i_eq = i % len(_EQUIPOS)
        xa, xb = xs_b[i] + j_w, xs_b[i + 1] - j_w         # hueco del porton
        # suelo pintado: banda de equipo, plaza marcada y numero grande. Capas
        # separadas >= 3 cm (suelo 0.02, pintura 0.05, numero 0.08): sin
        # z-fighting lejano en AC
        _quad(mE, [(cx - hw + 0.6, y_g + 0.15, 0.05), (cx + hw - 0.6, y_g + 0.15, 0.05),
                   (cx + hw - 0.6, y_g + 0.55, 0.05), (cx - hw + 0.6, y_g + 0.55, 0.05)],
              i_eq, (0, 0, 1))
        for (px0, px1, py0, py1) in ((cx - 1.45, cx - 1.37, 1.2, 5.8), (cx + 1.37, cx + 1.45, 1.2, 5.8),
                                     (cx - 1.37, cx + 1.37, 1.2, 1.28), (cx - 1.37, cx + 1.37, 5.72, 5.8)):
            _quad(me, [(px0, py0, 0.05), (px1, py0, 0.05), (px1, py1, 0.05), (px0, py1, 0.05)],
                  E_BLANCO, (0, 0, 1))
        _texto_en_mg(mE, str(i + 1), 1.5, (cx, 4.5, 0.08), math.pi, i_eq, plano=True,
                     resolucion=4)
        # banda de color de equipo en el fondo del garaje
        _caja_g(mE, cx - hw + 0.5, cx + hw - 0.5, y_g, y_g + 0.03, 2.0, 2.5, i_eq, omitir=(3,))
        # persiana enrollable metalica: tambor tras el dintel + faldon de
        # acero con lamas en relieve (color de equipo) por ambas caras
        _prisma_x(me, xa, xb, [(yd + 0.26 * math.cos(t), h_p + 0.24 + 0.26 * math.sin(t))
                               for t in (k * math.pi / 4.0 for k in range(8))], E_ACERO,
                  omitir=('x0', 'x1'))
        _caja_g(me, xa + 0.02, xb - 0.02, yd - 0.03, yd + 0.03, h_p - 0.60, h_p + 0.05,
                E_ACERO, omitir=(2,))
        for k in range(4):
            zl = h_p - 0.57 + k * 0.14
            _caja_g(mE, xa + 0.03, xb - 0.03, yd + 0.03, yd + 0.06, zl, zl + 0.10, i_eq,
                    omitir=(3,))
            _caja_g(mE, xa + 0.03, xb - 0.03, yd - 0.06, yd - 0.03, zl, zl + 0.10, i_eq,
                    omitir=(1,))
        # marco del porton en color de equipo (guias sobre las mochetas)
        _caja_g(mE, xa, xa + 0.04, y_f - 0.26, y_f - 0.04, 0.6, h_p - 0.05, i_eq, omitir=('x0',))
        _caja_g(mE, xb - 0.04, xb, y_f - 0.26, y_f - 0.04, 0.6, h_p - 0.05, i_eq, omitir=('x1',))
        # dintel en relieve (color de equipo) y placa de la marquesina
        _caja_g(mE, xa + 0.02, xb - 0.02, y_f, y_f + 0.18, h_p, h_p + 0.30, i_eq, omitir=(3,))
        _caja_g(mE, xs_b[i] + 0.05, xs_b[i + 1] - 0.05, y_f + _V_MARQ, y_f + _V_MARQ + 0.03,
                z_mq + 0.05, z_gal - 0.05, i_eq, omitir=(3,))
        _caja_g(me, cx - 0.75, cx + 0.75, y_f + _V_MARQ + 0.03, y_f + _V_MARQ + 0.06,
                z_mq + 0.08, z_gal - 0.08, E_BLANCO, omitir=(3,))
        # --- utillaje: banco de trabajo (fondo izquierda) con cajones cromados
        _caja_g(mu, cx - hw + 0.4, cx - hw + 2.1, y_g + 0.05, y_g + 0.75, 0.10, 0.90,
                U_OSCURO, omitir=(0, 2, 3))
        _caja_g(mu, cx - hw + 0.35, cx - hw + 2.15, y_g + 0.03, y_g + 0.80, 0.90, 0.96,
                U_ACERO, omitir=(3,))
        for k in range(2):
            xk = cx - hw + 0.65 + k * 0.8
            _caja_g(mu, xk, xk + 0.5, y_g + 0.75, y_g + 0.77, 0.45, 0.48, U_CROMO, omitir=(3,))
        # armario de herramientas (color de equipo) en el fondo derecha
        _caja_g(mE, cx + hw - 1.9, cx + hw - 0.5, y_g + 0.03, y_g + 0.70, 0.0, 1.95,
                i_eq, omitir=(0, 3))
        for k in range(3):
            zk = 0.35 + k * 0.5
            _caja_g(mu, cx + hw - 1.55, cx + hw - 0.85, y_g + 0.70, y_g + 0.72, zk, zk + 0.03,
                    U_CROMO, omitir=(3,))
        # pilas de ruedas con llantas cromadas (izquierda, 4 + 2): perfil con
        # hombro, 2 cm de hueco entre ruedas y pequeno desfase x/y por rueda;
        # la rueda de encima ensena tambien su llanta por abajo (fondo)
        for (ty_, n_r) in ((2.2, 4), (3.45, 2)):
            tx_ = cx - hw + 1.05
            for k in range(n_r):
                dx_, dy_ = rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03)
                _rueda(mu, tx_ + dx_, ty_ + dy_, k * 0.30, 0.28, 0.34, U_GOMA, U_CROMO,
                       seg=10, tapa=(k == n_r - 1), fondo=(k > 0),
                       fase=rng.uniform(0.0, 0.6), m_oscuro=U_OSCURO)
        # par de ruedas tumbadas de lado junto a la puerta, llanta cromada a la
        # vista desde el pit lane (+Y)
        for k in range(2):
            _rueda(mu, 0.0, 0.0, 0.0, 0.28, 0.34, U_GOMA, U_CROMO, seg=10, tapa=(k == 1),
                   fondo=(k == 0), m_oscuro=U_OSCURO,
                   tf=_tf_rueda_lado(cx - hw + 1.05, 4.55 + k * 0.30, 0.0, 0.34))
        # carro de herramientas (derecha, color de equipo, ruedas y tiradores)
        cxc, cyc = cx + hw - 0.95, 3.0
        _caja_g(mE, cxc - 0.28, cxc + 0.28, cyc - 0.45, cyc + 0.45, 0.12, 0.95, i_eq)
        for k in range(3):
            zk = 0.25 + k * 0.22
            _caja_g(mu, cxc - 0.30, cxc - 0.28, cyc - 0.30, cyc + 0.30, zk, zk + 0.03,
                    U_CROMO, omitir=('x1',))
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                _caja_g(mu, cxc + sx * 0.2 - 0.05, cxc + sx * 0.2 + 0.05,
                        cyc + sy * 0.35 - 0.05, cyc + sy * 0.35 + 0.05, 0.0, 0.12, U_NEGRO,
                        omitir=(2,))
        # elevador rapido (gato amarillo) junto a la plaza, hacia la puerta
        _caja_g(mu, cx + 1.25, cx + 1.55, 4.3, 5.1, 0.05, 0.28, U_AMAR)
        _prisma_x(mu, cx + 1.37, cx + 1.43, [(5.1, 0.22), (5.9, 0.80), (5.9, 0.86), (5.1, 0.28)],
                  U_ACERO, omitir=(3,))
        for yy in (4.45, 4.95):
            _caja_g(mu, cx + 1.20, cx + 1.60, yy - 0.06, yy + 0.06, 0.0, 0.12, U_NEGRO,
                    omitir=(2,))
        # monitores en el fondo (pantallas emisivas) y luminarias del techo
        for xm in (cx - 0.9, cx + 0.1):
            _caja_g(mu, xm, xm + 0.8, y_g + 0.03, y_g + 0.10, 2.7, 3.2, U_OSCURO, omitir=(3,))
            _caja_g(mu, xm + 0.04, xm + 0.76, y_g + 0.10, y_g + 0.12, 2.74, 3.16, U_PANT,
                    omitir=(3,))
        for yl in (2.0, 4.3):
            _caja_g(mu, cx - 1.2, cx + 1.2, yl - 0.08, yl + 0.08, z_g - 0.08, z_g, U_LUZ,
                    omitir=(2,))
        # foco empotrado bajo la marquesina
        _caja_g(mu, cx - 0.3, cx + 0.3, y_f + 0.55, y_f + 0.85, z_mq - 0.10, z_mq, U_LUZ,
                omitir=(2,))
    # --- fachada: pilastras en relieve (0.20 m) sobre zocalo de hormigon,
    # mochetas, mensulas y marquesina volada (sombra sobre los portones)
    for i in range(n + 1):
        xb = xs_b[i]
        x0m, x1m = max(-a2 + e_m, xb - j_w), min(a2 - e_m, xb + j_w)
        x0p, x1p = (-a2 if i == 0 else xb - j_w), (a2 if i == n else xb + j_w)
        om_m = [0, 1, 2] + (['x0'] if i == 0 else []) + (['x1'] if i == n else [])
        _caja_g(me, x0m, x1m, y_f - e_m, y_f, 0.0, h_p, E_OCRE, omitir=tuple(om_m))
        _caja_g(me, x0p, x1p, y_f, y_f + 0.20, 0.6, z_mq, E_OCRE, omitir=(0, 2, 3))
        _caja_g(me, x0p - 0.02, x1p + 0.02, y_f, y_f + 0.26, 0.0, 0.6, E_HORM, omitir=(0, 3))
        # mensula triangular bajo la marquesina (sin cara trasera ni superior)
        _prisma_x(me, x0p + 0.12, x1p - 0.12,
                  [(y_f + 0.20, z_mq - 0.40), (y_f + 1.05, z_mq), (y_f + 0.20, z_mq)],
                  E_BLANCO, omitir=(1, 2))
    _caja_g(me, -a2 + e_m, a2 - e_m, y_f - e_m, y_f, h_p, z_gal, E_CREMA,
            omitir=(2, 'x0', 'x1'))
    # marquesina: losa volada de 1.2 m con fascia (placas de los numeros)
    _caja_g(me, -a2, a2, y_f, y_f + _V_MARQ, z_mq, z_gal, E_BLANCO, omitir=(3,))
    _caja_g(me, -a2, a2, y_f + _V_MARQ, y_f + _V_MARQ + 0.02, z_gal - 0.045, z_gal - 0.005,
            E_ROJO, omitir=(3,))

    # --- planta de servicio: galeria con columnas, balaustrada y ventanales
    _quad(me, [(xi0, y_s, z_gal), (xi1, y_s, z_gal), (xi1, y_f - 0.15, z_gal),
               (xi0, y_f - 0.15, z_gal)], E_HORM, (0, 0, 1))
    _quad(me, [(xi0, y_s, z_l0), (xi1, y_s, z_l0), (xi1, y_f, z_l0), (xi0, y_f, z_l0)],
          E_BLANCO, (0, 0, -1))
    for i in range(1, n):          # columnas (en los extremos: el testero)
        xb = xs_b[i]
        _caja_g(me, xb - 0.15, xb + 0.15, y_f - e_m, y_f, z_gal, z_l0, E_CREMA,
                omitir=(0, 2))
    for i in range(n):
        xa = xi0 if i == 0 else xs_b[i] + 0.15
        xb = xi1 if i == n - 1 else xs_b[i + 1] - 0.15
        om = [0] + (['x0'] if i > 0 else []) + (['x1'] if i < n - 1 else [])
        _caja_g(me, xa, xb, y_f - 0.15, y_f, z_gal, z_gal + 0.42, E_BLANCO, omitir=tuple(om))
        _caja_g(me, xa, xb, y_f, y_f + 0.03, z_gal + 0.14, z_gal + 0.30, E_ROJO, omitir=(3,))
        nb = max(2, int((xb - xa) / 0.55))
        for k in range(nb):
            xk = xa + (k + 0.5) * (xb - xa) / nb
            _caja_g(me, xk - 0.035, xk + 0.035, y_f - 0.11, y_f - 0.04, z_gal + 0.42,
                    z_gal + 0.92, E_BLANCO, omitir=(0, 2))
        om_h = (['x0'] if i > 0 else []) + (['x1'] if i < n - 1 else [])
        _caja_g(me, xa, xb, y_f - 0.19, y_f + 0.02, z_gal + 0.92, z_gal + 1.0, E_ACERO,
                omitir=tuple(om_h))
    # pared del fondo de la galeria con grandes ventanales (vidrio con Coat)
    _caja_g(me, xi0, xi1, y_s - 0.15, y_s, z_gal, z_l0, E_CREMA,
            omitir=(0, 2, 3, 'x0', 'x1'))
    for i, cx in enumerate(cxs):
        hv = min(2.2, 0.5 * w - 0.8)
        xv0, xv1 = cx - hv, cx + hv
        if i % 3 == 1 and w >= 5.0:       # puerta (para coches) a la izquierda
            _caja_g(me, xv0, xv0 + 1.3, y_s, y_s + 0.04, z_gal, z_gal + 2.4, E_OSCURO,
                    omitir=(0, 3))
            xv0 += 1.6
        _caja_g(me, xv0, xv1, y_s, y_s + 0.06, z_gal + 0.9, z_gal + 2.4, E_BLANCO, omitir=(3,))
        _caja_g(me, xv0 + 0.08, xv1 - 0.08, y_s + 0.06, y_s + 0.09, z_gal + 0.98,
                z_gal + 2.32, E_CRISTAL, omitir=(3,))
        for xm in (xv0 + (xv1 - xv0) / 3.0, xv0 + 2.0 * (xv1 - xv0) / 3.0):
            _caja_g(me, xm - 0.03, xm + 0.03, y_s + 0.09, y_s + 0.11, z_gal + 0.98,
                    z_gal + 2.32, E_BLANCO, omitir=(3,))

    # --- losa de la grada (fascia con cornisa y banda roja) y muros de testero
    _caja_g(me, -a2, a2, y_w, y_f, z_l0, z_gr, E_BLANCO, omitir=(0, 3, 2))
    _caja_g(me, -a2, a2, y_f, y_f + 0.18, z_l0 - 0.12, z_l0 + 0.04, E_BLANCO, omitir=(3,))
    _caja_g(me, -a2, a2, y_f, y_f + 0.05, z_l0 + 0.09, z_gr - 0.05, E_ROJO, omitir=(3,))
    for sx in (-1.0, 1.0):
        x0, x1 = (-a2, -a2 + e_m) if sx < 0 else (a2 - e_m, a2)
        om = (0, 'x1' if sx < 0 else 'x0')
        _caja_g(me, x0, x1, y_b, y_f, 0.0, z_l0, E_CREMA, omitir=om)
        xi = x1 if sx < 0 else x0
        _quad(me, [(xi, y_g, 0.0), (xi, y_f - e_m, 0.0), (xi, y_f - e_m, z_g),
                   (xi, y_g, z_g)], E_HORM, (-sx, 0, 0))
        _quad(me, [(xi, y_s, z_gal), (xi, y_f - e_m, z_gal), (xi, y_f - e_m, z_l0),
                   (xi, y_s, z_l0)], E_CREMA, (-sx, 0, 0))
        _caja_g(me, x0, x1, y_b, y_w, z_l0, z_r, E_CREMA, omitir=om)
        # porton de servicio (rampa interior) en el testero, sobre el zocalo
        xo = x0 - 0.05 if sx < 0 else x1
        _caja_g(me, xo, xo + 0.05, -2.0, 2.0, 0.6, 3.6, E_OSCURO, omitir=om)
        _caja_g(me, xo - 0.02 if sx < 0 else xo, (xo + 0.05) if sx < 0 else xo + 0.07,
                -5.5, 5.5, 0.0, 0.6, E_HORM, omitir=om)
    # --- muro trasero (paddock) hasta el techo: zocalo, portones, ventanas,
    # pilastras, bandas y pancartas de patrocinio
    _caja_g(me, -a2 + e_m, a2 - e_m, y_b, y_w, 0.0, z_r, E_CREMA,
            omitir=(0, 1, 2, 'x0', 'x1'))
    _caja_g(me, -a2, a2, y_b - 0.05, y_b, 0.0, 0.6, E_HORM, omitir=(0, 1))
    _caja_g(me, -a2, a2, y_b - 0.10, y_b, z_l0, z_l0 + 0.3, E_BLANCO, omitir=(1,))
    _caja_g(me, -a2, a2, y_b - 0.10, y_b, z_r - 0.5, z_r, E_BLANCO, omitir=(1, 2))
    for i in range(n):
        cx = cxs[i]
        if i % 4 == 1:
            _caja_g(me, cx - 2.2, cx + 2.2, y_b - 0.05, y_b, 0.6, 3.8, E_OSCURO,
                    omitir=(0, 1))
        hv = min(1.5, 0.5 * w - 0.7)
        _caja_g(me, cx - hv, cx + hv, y_b - 0.04, y_b, z_gal + 0.9, z_gal + 2.3,
                E_BLANCO, omitir=(1,))
        _caja_g(me, cx - hv + 0.1, cx + hv - 0.1, y_b - 0.06, y_b - 0.04,
                z_gal + 1.0, z_gal + 2.2, E_CRISTAL, omitir=(1,))
    tam_rot = 2.0 if L >= 40.0 else 0.0
    semi_rot = 0.5 * 11 * tam_rot * 0.62 + 1.5
    for i in range(0, n + 1, 2):
        xb = xs_b[i]
        if abs(xb) < semi_rot or abs(xb) > a2 - 0.6:
            continue
        _caja_g(me, xb - 0.25, xb + 0.25, y_b - 0.12, y_b, 0.6, z_r - 0.5, E_BLANCO,
                omitir=(0, 1, 2))
    _caja_g(me, -a2, a2, y_b - 0.06, y_b, z_l0 + 4.0, z_l0 + 4.5, E_BLANCO, omitir=(1,))
    if pancartas:
        k_p = 0
        for i in range(0, n - 1, 2):
            xa, xb = xs_b[i] + 0.9, xs_b[i + 2] - 0.9
            if xb - xa < 4.0 or (xa < semi_rot and xb > -semi_rot):
                continue
            texto, banda, tinta = _PATROCINIOS[k_p % len(_PATROCINIOS)]
            k_p += 1
            # banda en la malla de equipos (pintura del color mas parecido)
            mb_ = _EQUIPOS.index({'azul_oscuro': 'pub_azul', 'verde_wgp': 'verde_wgp',
                                  'rojo': 'pub_rojo', 'amarillo': 'pub_amarillo',
                                  'pub_naranja': 'pub_naranja'}[banda])
            _caja_g(mE, xa, xb, y_b - 0.05, y_b, z_l0 + 1.6, z_l0 + 2.8, mb_, omitir=(1,))
            textos_panc.append((texto, 0.8, (0.5 * (xa + xb), y_b - 0.08, z_l0 + 2.2),
                                math.pi, tinta))
    edificio = me.obj('%s_boxes_edificio' % PRE,
                      ('crema', 'blanco', 'gris_oscuro', 'suelo_box', 'rojo', 'cristal',
                       'gris_acero', 'hormigon', 'ocre'), col, separar=True)
    edificio.parent = raiz
    utillaje = mu.obj('%s_boxes_utillaje' % PRE,
                      ('gris_acero', 'gris_oscuro', 'goma', 'cromo', 'pantalla_luz',
                       'luz_blanca', 'amarillo', 'negro'), col)
    utillaje.parent = raiz
    equipos = mE.obj('%s_boxes_equipos' % PRE, _EQUIPOS, col, separar=True)
    equipos.parent = raiz

    # numeros de los boxes en las placas de la marquesina (una sola malla, a
    # 3 cm de la placa blanca)
    numeros = _textos_malla('%s_boxes_numeros' % PRE,
                            [(str(i + 1), 0.42, (cxs[i], y_f + _V_MARQ + 0.09,
                                                 0.5 * (z_mq + z_gal)), 0.0)
                             for i in range(n)], 'gris_oscuro', col, extrude=0.0)
    numeros.parent = raiz
    # rotulo PORTO CORSA en la fachada trasera (legible desde -Y)
    if tam_rot > 0.0:
        rot = _texto_3d('%s_boxes_rotulo' % PRE, 'PORTO CORSA', tam_rot, 'azul_techo',
                        col, extrude=0.04, pos=(0.0, y_b - 0.09, z_l0 + 5.9),
                        rot_z=math.pi)
        rot.parent = raiz

    # ============================================================== grada
    # 0 crema, 1 blanco, 2 verde_wgp, 3 piedra_clara, 4 gris_oscuro, 5 rojo,
    # 6 pub_azul, 7 amarillo, 8 pub_naranja
    (G_CREMA, G_BLANCO, G_VERDE, G_PIEDRA, G_OSCURO, G_ROJO, G_AZUL, G_AMAR,
     G_NARANJA) = range(9)
    mg = _MG()
    y_par0, y_par1 = y_f - 0.3, y_f             # peto delantero (0.65 m)
    y_t0 = y_par0                                # primera terraza pegada al peto
    prof = (y_t0 - y_w) / filas                  # ~1.76 m con 7 filas
    z_top = z_gr + (filas - 1) * _RISE
    h_peto = _H_PETO

    # reparto en X: muros laterales, rampas y bloques
    g_lat, g_div, w_rampa, w_pas = e_m, 0.22, 2.3, 2.4
    hay_rampas = L >= 16.0
    bloques, calles = [], []
    if hay_rampas:
        n_bl = max(1, int(round(L / 30.0)))
        x_in = a2 - g_lat - w_rampa - g_div
        wb = (2.0 * x_in - (n_bl - 1) * (w_pas + 2.0 * g_div)) / n_bl
        calles.append((-a2 + g_lat, -a2 + g_lat + w_rampa))
        for k in range(n_bl):
            xa = -x_in + k * (wb + w_pas + 2.0 * g_div)
            bloques.append((xa, xa + wb))
            if k < n_bl - 1:
                calles.append((xa + wb + g_div, xa + wb + g_div + w_pas))
        calles.append((a2 - g_lat - w_rampa, a2 - g_lat))
    else:
        bloques.append((-a2 + g_lat, a2 - g_lat))

    # peto delantero bajo (blanco): la primera terraza arranca justo detras,
    # sin pasillo, para que el publico asome por encima. Sobre su cara
    # delantera, pancartas de patrocinio y ribete rojo superior.
    _caja_g(mg, -a2 + g_lat, a2 - g_lat, y_par0, y_par1, z_gr, z_gr + h_peto, G_BLANCO,
            omitir=(0, 'x0', 'x1'))
    _caja_g(mg, -a2, a2, y_par1, y_par1 + 0.03, z_gr + h_peto - 0.07, z_gr + h_peto - 0.02,
            G_ROJO, omitir=(3,))
    if pancartas:
        lb, gap = 9.0, 3.0
        nb_ = max(1, int((L - 1.0 + gap) / (lb + gap)))
        total = nb_ * lb + (nb_ - 1) * gap
        x_ini = -0.5 * total
        for k in range(nb_):
            xa = x_ini + k * (lb + gap)
            texto, banda, tinta = _PATROCINIOS[k % len(_PATROCINIOS)]
            mb_ = {'azul_oscuro': G_AZUL, 'verde_wgp': G_VERDE, 'rojo': G_ROJO,
                   'amarillo': G_AMAR, 'pub_naranja': G_NARANJA}[banda]
            _caja_g(mg, xa, xa + lb, y_par1, y_par1 + 0.04, z_gr + 0.06, z_gr + h_peto - 0.11,
                    mb_, omitir=(3,))
            textos_panc.append((texto, 0.46, (xa + 0.5 * lb, y_par1 + 0.07,
                                              z_gr + 0.5 * (0.06 + h_peto - 0.11)), 0.0, tinta))
    else:
        _caja_g(mg, -a2, a2, y_par1, y_par1 + 0.03, z_gr + 0.25, z_gr + 0.45, G_ROJO,
                omitir=(3,))
    # terrazas (huella crema + contrahuella blanca + canto oscuro en la nariz)
    ext = g_div if hay_rampas else 0.05
    for xa, xb in bloques:
        x0, x1 = xa - ext, xb + ext
        for i in range(filas):
            zf = z_gr + i * _RISE
            yf = y_t0 - i * prof
            yr = yf - prof
            _quad(mg, [(x0, yr, zf), (x1, yr, zf), (x1, yf, zf), (x0, yf, zf)],
                  G_CREMA, (0, 0, 1))
            if i > 0:
                _quad(mg, [(x0, yf, zf - _RISE), (x1, yf, zf - _RISE), (x1, yf, zf),
                           (x0, yf, zf)], G_BLANCO, (0, 1, 0))
                _caja_g(mg, x0, x1, yf - 0.10, yf, zf, zf + 0.05, G_OSCURO, omitir=(0,))
    # pasillos-rampa
    yc0 = y_t0 - 0.5 * prof
    ycl = y_w + 0.5 * prof
    for k, (xa, xb) in enumerate(calles):
        x0 = xa - 0.05 if k == 0 else xa
        x1 = xb + 0.05 if k == len(calles) - 1 else xb
        tramos = [((y_t0, z_gr), (yc0, z_gr))]
        if filas > 1:
            tramos.append(((yc0, z_gr), (ycl, z_top)))
        tramos.append(((ycl, z_top), (y_w, z_top)))
        for (ya_, za_), (yb_, zb_) in tramos:
            _quad(mg, [(x0, ya_, za_), (x1, ya_, za_), (x1, yb_, zb_), (x0, yb_, zb_)],
                  G_PIEDRA, (0, 0, 1))
        _caja_g(mg, xa + 0.25, xb - 0.25, y_w - 0.05, y_w + 0.14, z_top - 0.05,
                min(z_top + 1.6, z_r - 0.45), G_BLANCO, omitir=(0, 3), mats={1: G_OSCURO})
    if hay_rampas and filas > 1:
        for xa, xb in bloques:
            for xj, sg in ((xa - g_div, -1.0), (xb + g_div, 1.0)):
                for i in range(filas):
                    zf = z_gr + i * _RISE
                    yf = y_t0 - i * prof
                    yr = yf - prof
                    ym = 0.5 * (yf + yr)
                    if i > 0:
                        iv = mg.verts([(xj, yf, zf - 0.5 * _RISE), (xj, yf, zf), (xj, ym, zf)])
                        mg.cara((iv, iv + 1, iv + 2), G_VERDE, False, ref=(sg, 0.0, 0.0))
                    if i < filas - 1:
                        iv = mg.verts([(xj, ym, zf), (xj, yr, zf + 0.5 * _RISE), (xj, yr, zf)])
                        mg.cara((iv, iv + 1, iv + 2), G_VERDE, False, ref=(-sg, 0.0, 0.0))
    # muros laterales (siguen la pendiente, coronacion 1.15 m sobre la nariz de
    # las terrazas; recortada en horizontal 0.45 m bajo el techo) con
    # albardilla verde
    pend = _RISE / prof if filas > 1 else 0.0
    c_ext, cop = 1.15, 0.12
    y_d0 = y_f
    z_cap = z_r - 0.45 - cop

    def z_linea(yy):
        return min(z_cap, z_gr + c_ext + (y_t0 - yy) * pend)

    zf, zb = z_linea(y_d0), z_linea(y_w)
    perfil_cor = [(y_d0, zf)]                    # coronacion de delante atras
    if zb >= z_cap - 1e-6 and pend > 1e-9:
        y_k = y_t0 - (z_cap - z_gr - c_ext) / pend
        if y_w + 0.05 < y_k < y_d0 - 0.05:
            perfil_cor.append((y_k, z_cap))
    perfil_cor.append((y_w, zb))
    for x0, x1 in ((-a2, -a2 + g_lat), (a2 - g_lat, a2)):
        _prisma_x(mg, x0, x1, [(y_w, z_gr), (y_d0, z_gr)] + perfil_cor,
                  G_BLANCO, omitir=(0,) + tuple(range(2, 2 + len(perfil_cor))))
        for k in range(len(perfil_cor) - 1):
            (ya_, za_), (yb_, zb_) = perfil_cor[k], perfil_cor[k + 1]
            om = (0, 1) if k == 0 else (0, 1, 3)
            _prisma_x(mg, x0, x1, [(ya_, za_), (yb_, zb_), (yb_, zb_ + cop), (ya_, za_ + cop)],
                      G_VERDE, omitir=om)
    # cara interior del muro trasero sobre la grada + banda verde bajo el techo
    _caja_g(mg, -a2 + e_m, a2 - e_m, y_w - 0.1, y_w, z_gr, z_r, G_BLANCO,
            omitir=(0, 2, 3, 'x0', 'x1'))
    _caja_g(mg, -a2 + e_m + 0.4, a2 - e_m - 0.4, y_w, y_w + 0.08, z_r - 1.05,
            z_r - 0.5, G_VERDE, omitir=(3,))
    grada = mg.obj('%s_boxes_grada' % PRE,
                   ('crema', 'blanco', 'verde_wgp', 'piedra_clara', 'gris_oscuro',
                    'rojo', 'pub_azul', 'amarillo', 'pub_naranja'), col, separar=True)
    grada.parent = raiz

    # ============================================================== techo
    # 0 azul_techo, 1 azul_claro, 2 gris_acero (postes y vigas metalicas),
    # 3 gris_oscuro, 4 luz_blanca
    T_AZUL, T_CLARO, T_ACERO, T_OSCURO, T_LUZ = range(5)
    mt = _MG()
    v = 0.3
    y_r1 = y_t0 - 0.2                     # borde delantero del techo
    _caja_g(mt, -a2 - v, a2 + v, y_b - v, y_r1, z_r, z_r + 0.3, T_AZUL, omitir=(1,))
    # imposta clara en el borde delantero
    _caja_g(mt, -a2 - v, a2 + v, y_r1, y_r1 + 0.08, z_r - 0.35, z_r + 0.38, T_CLARO,
            omitir=(3,))
    # postes finos metalicos (en la 2a terraza y sobre los muros laterales) que
    # suben hasta la cara inferior de las vigas; vigas transversales (canto
    # 0.35, bajo la losa) EXACTAMENTE en la x de cada poste, con vigas
    # intermedias cada <= 7 m
    i_col = min(filas - 1, 1)
    y_col = y_t0 - (i_col + 0.5) * prof - 0.35
    z_c0 = z_gr + i_col * _RISE
    pies_ext = [-a2 + 0.5 * g_lat, a2 - 0.5 * g_lat]
    pies = []
    for xa, xb in bloques:
        pies += [xa + 0.45, xb - 0.45]
        if xb - xa > 14.0:
            pies.append(0.5 * (xa + xb))
    z_vig = z_r - 0.35
    for xc_ in pies_ext + pies:
        zc_ = z_linea(y_col) + cop if xc_ in pies_ext else z_c0
        _caja_g(mt, xc_ - 0.11, xc_ + 0.11, y_col - 0.11, y_col + 0.11, zc_,
                z_vig, T_ACERO, omitir=(0, 2))
    xs_p = sorted(pies_ext + pies)
    xs_v = [xs_p[0]]
    for xa_, xb_ in zip(xs_p, xs_p[1:]):
        k_ = max(1, int(round((xb_ - xa_) / 7.0)))
        xs_v += [xa_ + (xb_ - xa_) * j / k_ for j in range(1, k_ + 1)]
    y_fo = y_t0 - 2.8                     # focos sobre la 2a terraza
    for xv in xs_v:
        # viga metalica (Metallic 0.9 / Roughness 0.2, como los postes)
        _caja_g(mt, xv - 0.12, xv + 0.12, y_w, y_r1 - 0.1, z_vig, z_r, T_ACERO,
                omitir=(2, 3))
        # foco doble colgado de la viga: soporte + carcasa con caras emisivas
        _caja_g(mt, xv - 0.03, xv + 0.03, y_fo - 0.03, y_fo + 0.03, z_vig - 0.30, z_vig,
                T_ACERO, omitir=(0, 2))
        _caja_g(mt, xv - 0.30, xv + 0.30, y_fo - 0.14, y_fo + 0.14, z_vig - 0.62,
                z_vig - 0.30, T_OSCURO, mats={1: T_LUZ, 3: T_LUZ})
    techo = mt.obj('%s_boxes_techo' % PRE,
                   ('azul_techo', 'azul_claro', 'gris_acero', 'gris_oscuro', 'luz_blanca'),
                   col, separar=True)
    techo.parent = raiz

    # ============================================= banderas onduladas (malla)
    mb = _MG()          # 0 gris_acero, 1 verde_wgp, 2 blanco, 3 rojo
    if banderas:
        for i in range(n):
            xp = cxs[i] - 0.72
            yp = y_par0 + 0.15
            zp, zt = z_gr + h_peto, z_gr + h_peto + 2.4
            _caja_g(mb, xp - 0.035, xp + 0.035, yp - 0.035, yp + 0.035, zp, zt, 0,
                    omitir=(0,))
            _cilindro(mb, xp, yp, zt, zt + 0.08, 0.06, 0, seg=6, tapa1=True, suave=False)
            _bandera(mb, xp + 0.04, yp, zt - 0.95, zt - 0.05, 1.32, (1, 2, 3),
                     rng.uniform(0.0, 2.0 * math.pi))
        if mb.f:
            band = mb.obj('%s_boxes_banderas' % PRE,
                          ('gris_acero', 'verde_wgp', 'blanco', 'rojo'), col)
            band.parent = raiz

    # ==================================== pancartas y numeros pintados (texto)
    if textos_panc:
        # de pie (pancartas) o planos (numeros del suelo) segun el 6o campo
        panc = _textos_multi('%s_boxes_pancartas' % PRE, textos_panc, col, extrude=0.0,
                             plano=False, resolucion=4)
        panc.parent = raiz
    t_textos = sum(len(p.vertices) - 2 for p in panc.data.polygons) if textos_panc else 0

    # ============================================================ publico
    mp = _MG()
    paso = _PASO_PUB          # coches pegados (ancho max 1.46 con ruedas)
    l_max = prof - 0.14
    plazas = []
    for xa, xb in bloques:
        k = int((xb - xa - 0.45) // paso)
        if k < 1:
            continue
        x_ini = 0.5 * (xa + xb) - (k - 1) * paso / 2.0
        for i in range(filas):
            des = 0.5 * paso if (i % 2 == 1 and k > 1) else 0.0
            k_i = k - 1 if des > 0.0 else k
            for p in range(k_i):
                xp_ = x_ini + des + p * paso
                if i == i_col and any(abs(xp_ - xq) < 0.95 for xq in pies):
                    continue
                plazas.append((i, xp_))
    ocupadas = [pl for pl in plazas if rng.random() < ocupacion]
    usados = (me.tris() + mg.tris() + mt.tris() + mu.tris() + mE.tris() + mb.tris()
              + t_textos + 60 * n + 1200)
    n_max = max(0, (max_tris - usados) // _PUB_TRIS)
    if len(ocupadas) > n_max:
        rng.shuffle(ocupadas)
        ocupadas = sorted(ocupadas[:n_max])
    obj_x = rng.uniform(-0.4, 0.4) * L
    obj_y = y_f + 18.0
    mi_prev = -1
    for i, xc in ocupadas:
        tipo = rng.choices((0, 1, 2), weights=(5, 3, 2))[0]
        e = rng.uniform(0.90, 1.06)
        W = 1.28 * e * rng.uniform(0.96, 1.03)      # <= 1.40 (+0.06 ruedas)
        Lc = min(1.50 * e, l_max)
        mi = 1 + rng.choices(range(len(_PUBLICO)), weights=_PUB_PESOS_COLOR)[0]
        if mi == mi_prev:
            mi = 1 + rng.choices(range(len(_PUBLICO)), weights=_PUB_PESOS_COLOR)[0]
        mi_prev = mi
        x = xc + rng.uniform(-0.03, 0.03)
        z = z_gr + i * _RISE
        y = y_t0 - (i + 0.5) * prof + rng.uniform(-0.03, 0.03)
        ddx, ddy = obj_x - x, obj_y - y
        dd = math.hypot(ddx, ddy)
        if rng.random() < 0.12:
            mirada = (rng.uniform(-1.0, 1.0), rng.uniform(-0.5, 0.6))
        else:
            mirada = (1.9 * ddx / dd + rng.uniform(-0.12, 0.12),
                      -0.35 + rng.uniform(-0.15, 0.15))
        rz = rng.uniform(-0.06, 0.06) - 0.05 * max(-1.0, min(1.0, mirada[0]))
        _pub_coche(mp, (x, y, z), rz, W, Lc, e, mi, mirada, rng.random() < 0.45, tipo)
    publico = mp.obj('%s_boxes_publico' % PRE, _PUB_MATS, col)
    publico.parent = raiz
    return raiz


# -------------------------------------------------------------- muro de boxes

def build_muro_boxes(parent_collection, largo=12.0, seed=0, **params):
    """Tramo de muro de boxes a lo largo de X (repetible, periodo = largo):
    podio macizo de hormigon de 1.1 m de alto y 2.2 m de fondo con remate
    blanco, valla de captura de tubos cromados al lado de la pista (+Y) y
    puestos de equipo techados (pupitre con monitores emisivos y pit board
    hacia la pista, sitio para 1-2 coches-mecanico, parapeto hacia el pit
    lane, extintor), con sombrilla de equipo, pila de ruedas y bidones en los
    huecos entre puestos. Huella y en [-2.05, 0.30].
    params: tapa_x0 / tapa_x1 = False (cierran los extremos del podio, para el
    primer y el ultimo tramo), equipo = True (coches-mecanico en la malla hija
    PIT_muro_boxes_equipo). Devuelve la malla PIT_muro_boxes."""
    col = parent_collection
    rng = random.Random(seed)
    largo = float(largo)
    a2 = largo / 2.0
    tapas = tuple(t for t, quiere in (('x0', params.get('tapa_x0', False)),
                                      ('x1', params.get('tapa_x1', False))) if not quiere)
    con_equipo = bool(params.get('equipo', True))
    # 0 hormigon, 1 blanco, 2 gris_acero, 3 gris_oscuro, 4 pantalla_luz,
    # 5 negro, 6 verde_wgp, 7 cromo, 8 goma, 9 rojo, 10 amarillo,
    # 11 azul_techo, 12.. equipos
    (M_HORM, M_BLANCO, M_ACERO, M_OSCURO, M_PANT, M_NEGRO, M_VERDE, M_CROMO,
     M_GOMA, M_ROJO, M_AMAR, M_AZUL) = range(12)
    M_EQ0 = 12
    mg = _MG()
    h_m = 1.1
    y_pl = -2.0                # borde del podio hacia el pit lane
    # podio macizo con remate blanco. Tapas x0/x1 omitidas salvo tapa_x0/x1.
    _caja_g(mg, -a2, a2, y_pl, 0.2, 0.0, h_m - 0.12, M_HORM, omitir=(0, 2) + tapas)
    _caja_g(mg, -a2, a2, y_pl - 0.05, 0.22, h_m - 0.12, h_m, M_BLANCO, omitir=tapas)
    # banda verde WGP a lo largo del lado del pit lane
    _caja_g(mg, -a2, a2, y_pl - 0.02, y_pl, 0.35, 0.65, M_VERDE, omitir=(1,) + tapas)
    # valla de captura: postes cada 2 m, 4 tubos cromados y varillas verticales
    n_p = max(1, int(round(largo / 2.0)))
    for k in range(n_p):
        x = -a2 + (k + 0.5) * largo / n_p
        _caja_g(mg, x - 0.04, x + 0.04, 0.10, 0.18, h_m, h_m + 1.3, M_ACERO, omitir=(0,))
    for z in (h_m + 0.35, h_m + 0.65, h_m + 0.95, h_m + 1.25):
        _caja_g(mg, -a2, a2, 0.185, 0.215, z - 0.02, z + 0.02, M_CROMO, omitir=tapas)
    n_v = max(1, int(round(largo / 1.0)))
    for k in range(n_v):
        x = -a2 + (k + 0.5) * largo / n_v
        _caja_g(mg, x - 0.008, x + 0.008, 0.192, 0.208, h_m + 0.10, h_m + 1.23, M_ACERO,
                omitir=(0, 2))
    # puestos de equipo sobre la plataforma: uno cada ~6 m, 4.2 m de ancho
    n_b = max(1, int(round(largo / 6.0)))
    wb = min(4.2, largo / n_b - 1.2)
    z_p = h_m
    mq = _MG()                 # coches-mecanico (materiales del publico)
    y_par = y_pl + 0.12        # cara interior del parapeto trasero
    i_eq_prev = -1
    for k in range(n_b):
        cx = -a2 + (k + 0.5) * largo / n_b
        i_eq = rng.randrange(len(_EQUIPOS))
        if i_eq == i_eq_prev:
            i_eq = (i_eq + 3) % len(_EQUIPOS)
        i_eq_prev = i_eq
        eq = M_EQ0 + i_eq
        x0, x1 = cx - 0.5 * wb, cx + 0.5 * wb
        # pupitre bajo (0.7 m, frente a la pista) con monitores y pit board
        _caja_g(mg, x0 + 0.1, x1 - 0.1, -0.15, 0.2, z_p, z_p + 0.70, M_OSCURO, omitir=(0, 2))
        _caja_g(mg, x0 + 0.08, x1 - 0.08, -0.17, 0.22, z_p + 0.70, z_p + 0.80, eq, omitir=(0,))
        _caja_g(mg, x0 + 0.08, x1 - 0.08, 0.22, 0.24, z_p + 0.74, z_p + 0.77, M_CROMO,
                omitir=(3,))
        nm = max(1, int(wb / 1.2))
        for j in range(nm):
            xm = x0 + 0.1 + (j + 0.5) * (wb - 0.2) / nm
            _caja_g(mg, xm - 0.36, xm + 0.36, -0.10, -0.06, z_p + 0.80, z_p + 1.25,
                    M_OSCURO, omitir=(0,))
            _caja_g(mg, xm - 0.32, xm + 0.32, -0.12, -0.10, z_p + 0.84, z_p + 1.21,
                    M_PANT, omitir=(1,))
        # pit board volado sobre el frente del pupitre (panel blanco + banda)
        _caja_g(mg, x1 - 0.95, x1 - 0.15, 0.22, 0.26, z_p + 0.80, z_p + 1.60, M_BLANCO)
        _caja_g(mg, x1 - 0.9, x1 - 0.2, 0.26, 0.28, z_p + 1.20, z_p + 1.50, eq, omitir=(3,))
        _caja_g(mg, x1 - 0.9, x1 - 0.2, 0.26, 0.28, z_p + 0.88, z_p + 1.12, M_AMAR, omitir=(3,))
        # techo del puesto (color de equipo) sobre 4 postes metalicos
        for xp in (x0 + 0.08, x1 - 0.08):
            for yp in (y_par + 0.06, 0.05):
                _caja_g(mg, xp - 0.04, xp + 0.04, yp - 0.04, yp + 0.04, z_p, z_p + 2.45,
                        M_ACERO, omitir=(0, 2))
        _caja_g(mg, x0 - 0.05, x1 + 0.05, y_pl - 0.03, 0.15, z_p + 2.45, z_p + 2.55, eq)
        _caja_g(mg, x0 - 0.05, x1 + 0.05, 0.15, 0.18, z_p + 2.30, z_p + 2.60, M_BLANCO,
                omitir=(3,))
        # parapeto trasero bajo (0.5 m, hacia el pit lane) con banda verde
        _caja_g(mg, x0 + 0.08, x1 - 0.08, y_pl + 0.05, y_par, z_p, z_p + 0.5, M_BLANCO,
                omitir=(0,))
        _caja_g(mg, x0 + 0.08, x1 - 0.08, y_pl + 0.04, y_pl + 0.05, z_p + 0.18, z_p + 0.36,
                M_VERDE, omitir=(1,))
        # tarima del equipo entre el parapeto y el pupitre
        z_tar = z_p + 0.35
        _caja_g(mg, x0 + 0.15, x1 - 0.15, y_par + 0.02, -0.22, z_p, z_tar, M_HORM,
                omitir=(0,))
        # extintor rojo junto al poste trasero izquierdo
        ex, ey = x0 + 0.38, y_par + 0.28
        _cilindro(mg, ex, ey, z_tar, z_tar + 0.50, 0.09, M_ROJO, seg=8, tapa1=True)
        _cilindro(mg, ex, ey, z_tar + 0.50, z_tar + 0.60, 0.045, M_NEGRO, seg=6, tapa1=True,
                  suave=False)
        _caja_g(mg, ex - 0.03, ex + 0.12, ey - 0.02, ey + 0.02, z_tar + 0.52, z_tar + 0.56,
                M_NEGRO)
        # 1-2 coches-mecanico del equipo mirando a la pista (+Y) sobre la
        # tarima, con hueco libre para los postes del techo
        if con_equipo:
            n_c = 2 if (wb >= 3.6 and rng.random() < 0.7) else 1
            y_c = 0.5 * ((y_par + 0.12) + (-0.22 - 0.1))
            for j in range(n_c):
                xc_ = cx + (0.0 if n_c == 1 else (j - 0.5) * 1.75) + rng.uniform(-0.06, 0.06)
                e = rng.uniform(0.92, 1.02)
                mi = 1 + _PUBLICO.index(_EQUIPOS[i_eq]) if _EQUIPOS[i_eq] in _PUBLICO \
                    else 1 + _PUBLICO.index('pub_verde')
                mirada = (rng.uniform(-0.5, 0.5), rng.uniform(0.2, 0.7))
                _pub_coche(mq, (xc_, y_c + rng.uniform(-0.04, 0.04), z_tar),
                           rng.uniform(-0.08, 0.08), 1.28 * e, min(1.48 * e, 1.5), e, mi,
                           mirada, rng.random() < 0.4, rng.choice((0, 0, 1)))
        # sombrilla de equipo en el hueco tras el puesto (solo si cabe dentro
        # del tramo): mastil + cono a franjas equipo/blanco + cara inferior
        xs_ = cx + 0.5 * largo / n_b
        if xs_ + 1.0 < a2:
            _caja_g(mg, xs_ - 0.025, xs_ + 0.025, -1.15 - 0.025, -1.15 + 0.025, z_p,
                    z_p + 2.45, M_ACERO, omitir=(0,))
            _cono(mg, xs_, -1.15, z_p + 2.05, z_p + 2.45, 0.95, eq, seg=10, suave=False,
                  mat_alt=M_BLANCO)
            _disco(mg, xs_, -1.15, z_p + 2.05, 0.95, M_BLANCO, seg=10, ref=(0, 0, -1))
            # pila de 3 ruedas (perfil con hombro, 2 cm de hueco, desfase)
            for j in range(3):
                _rueda(mg, xs_ + rng.uniform(-0.03, 0.03), -0.40 + rng.uniform(-0.03, 0.03),
                       z_p + j * 0.29, 0.27, 0.33, M_GOMA, M_CROMO, seg=12, tapa=(j == 2),
                       fondo=(j > 0), fase=rng.uniform(0.0, 0.5), m_oscuro=M_OSCURO)
    # huecos de los extremos (se completan con el tramo vecino): bidones y
    # una pila de ruedas
    xe = a2 - 0.45
    for (xb_, yb_, mb_) in ((-xe, -0.55, M_AZUL), (-xe, -1.30, M_ROJO), (xe, -1.30, M_AMAR)):
        _cilindro(mg, xb_, yb_, z_p, z_p + 0.85, 0.28, mb_, seg=10, tapa1=True)
        _cilindro(mg, xb_, yb_, z_p + 0.85, z_p + 0.88, 0.22, M_OSCURO, seg=10, tapa1=True,
                  suave=False)
    for j in range(2):
        _rueda(mg, xe + rng.uniform(-0.03, 0.03), -0.50 + rng.uniform(-0.03, 0.03),
               z_p + j * 0.29, 0.27, 0.33, M_GOMA, M_CROMO, seg=12, tapa=(j == 1),
               fondo=(j > 0), fase=rng.uniform(0.0, 0.5), m_oscuro=M_OSCURO)
    # una rueda tumbada de lado en el hueco entre puestos, junto al borde del
    # pit lane, con la llanta cromada mirando al pit lane (-Y)
    if n_b >= 2:
        xg = -a2 + largo / n_b + 0.55
        _rueda(mg, 0.0, 0.0, 0.0, 0.27, 0.33, M_GOMA, M_CROMO, seg=12, tapa=True, fondo=False,
               m_oscuro=M_OSCURO, tf=_tf_rueda_lado(xg, y_pl + 0.27, z_p, 0.33, hacia=-1.0))
    ob = mg.obj('%s_muro_boxes' % PRE,
                ('hormigon', 'blanco', 'gris_acero', 'gris_oscuro', 'pantalla_luz',
                 'negro', 'verde_wgp', 'cromo', 'goma', 'rojo', 'amarillo', 'azul_techo')
                + _EQUIPOS, col, separar=True)
    if con_equipo and mq.f:
        equipo = mq.obj('%s_muro_boxes_equipo' % PRE, _PUB_MATS, col)
        equipo.parent = ob
    return ob


# ------------------------------------------------------------ torre de control

def _rz(t):
    """Transformacion: giro de t radianes sobre Z (para cajas radiales)."""
    co, si = math.cos(t), math.sin(t)
    return lambda p: (p[0] * co - p[1] * si, p[0] * si + p[1] * co, p[2])


def build_torre_control(parent_collection, alto=16.0, seed=0, **params):
    """Torre redonda de control / TV: plinto, fuste cilindrico de estuco con
    bandas de piedra y ventanas, balcon anular con balaustres y tubo cromado,
    tambor de vidrio (Coat) con columnillas y banda verde WGP, focos bajo el
    alero, remate conico azul, parabolica y antena con baliza. `alto` = altura
    del alero del tambor. Raiz PIT_torre (malla PIT_torre_cuerpo)."""
    col = parent_collection
    raiz = _raiz('%s_torre' % PRE, col)
    alto = max(8.0, float(alto))
    # 0 piedra_clara, 1 blanco, 2 cristal, 3 gris_acero, 4 azul_techo,
    # 5 gris_oscuro, 6 rojo_luz, 7 crema, 8 cromo, 9 verde_wgp, 10 luz_blanca
    (K_PIEDRA, K_BLANCO, K_CRISTAL, K_ACERO, K_AZUL, K_OSCURO, K_LUZ, K_CREMA,
     K_CROMO, K_VERDE, K_FOCO) = range(11)
    mg = _MG()
    seg = 20
    r_f = 2.0
    z_b = alto - 3.8                 # suelo del balcon / base del tambor
    _cilindro(mg, 0, 0, 0.0, 0.5, 2.7, K_PIEDRA, seg=seg, suave=False, tapa1=True)
    _cilindro(mg, 0, 0, 0.5, z_b - 0.35, r_f, K_CREMA, seg=seg, tapa1=False)
    # bandas de piedra en el fuste y puerta a pie de calle (mirando a +Y) con
    # marquesina pequena
    zb1, zb2 = 0.5 + (z_b - 1.0) / 3.0, 0.5 + 2.0 * (z_b - 1.0) / 3.0
    for zz in (zb1, zb2):
        _cilindro(mg, 0, 0, zz, zz + 0.3, r_f + 0.12, K_PIEDRA, seg=seg, tapa0=True,
                  tapa1=True, suave=False)
    # puerta a pie de calle (mirando a +Y): portal de estuco empotrado en el
    # fuste (jambas + dintel), marco blanco de 0.10 m, hueco en sombra con
    # doble hoja azul (ventanuco de cristal y tirador cromado en cada hoja),
    # marquesina blanca con luz
    # (el fuste es un cilindro de radio r_f: el portal sobresale hasta
    # y = r_f + 0.40 para que las hojas, a y = r_f + 0.06, queden delante de
    # la curva del muro y dentro de un hueco en sombra de 0.38 m)
    y_p0, y_p1 = r_f - 0.5, r_f + 0.40
    for xa_, xb_ in ((-1.30, -1.05), (1.05, 1.30)):
        _caja_g(mg, xa_, xb_, y_p0, y_p1, 0.5, 3.3, K_CREMA, omitir=(0, 2, 3))
    _caja_g(mg, -1.30, 1.30, y_p0, y_p1, 3.3, 3.6, K_CREMA, omitir=(2, 3))
    for xa_, xb_ in ((-1.15, -1.05), (1.05, 1.15)):
        _caja_g(mg, xa_, xb_, y_p1, y_p1 + 0.10, 0.5, 3.3, K_BLANCO, omitir=(0, 2, 3))
    _caja_g(mg, -1.15, 1.15, y_p1, y_p1 + 0.10, 3.3, 3.4, K_BLANCO, omitir=(3,))
    _quad(mg, [(-1.05, r_f + 0.02, 0.5), (1.05, r_f + 0.02, 0.5), (1.05, r_f + 0.02, 3.3),
               (-1.05, r_f + 0.02, 3.3)], K_OSCURO, (0, 1, 0))
    y_h = r_f + 0.06
    for xa_, xb_ in ((-1.02, -0.03), (0.03, 1.02)):
        _caja_g(mg, xa_, xb_, y_h, y_h + 0.06, 0.52, 3.26, K_AZUL)
        xm0, xm1 = (xa_ + 0.16, xb_ - 0.14) if xa_ < 0 else (xa_ + 0.14, xb_ - 0.16)
        _caja_g(mg, xm0, xm1, y_h + 0.06, y_h + 0.07, 1.86, 2.94, K_BLANCO, omitir=(3,))
        _caja_g(mg, xm0 + 0.04, xm1 - 0.04, y_h + 0.07, y_h + 0.09, 1.90, 2.90, K_CRISTAL,
                omitir=(3,))
        xt0, xt1 = (xb_ - 0.55, xb_ - 0.10) if xa_ < 0 else (xa_ + 0.10, xa_ + 0.55)
        _caja_g(mg, xt0, xt1, y_h + 0.06, y_h + 0.12, 1.50, 1.55, K_CROMO, omitir=(3,))
    _caja_g(mg, -1.4, 1.4, y_p0, y_p1 + 0.9, 3.6, 3.75, K_BLANCO, omitir=(3,))
    _caja_g(mg, -0.25, 0.25, y_p1 + 0.25, y_p1 + 0.55, 3.52, 3.6, K_FOCO, omitir=(2,))
    # ventanas (marco blanco + vidrio) en dos plantas, 6 por planta
    for zz in (zb1 + 0.9, zb2 + 0.9):
        for k in range(6):
            t = math.pi / 2.0 + (k + 0.5) * 2.0 * math.pi / 6.0
            tfk = _rz(t - math.pi / 2.0)
            _caja_g(mg, -0.42, 0.42, r_f - 0.02, r_f + 0.03, zz, zz + 1.1, K_BLANCO,
                    omitir=(3,), tf=tfk)
            _caja_g(mg, -0.35, 0.35, r_f + 0.03, r_f + 0.05, zz + 0.07, zz + 1.03,
                    K_CRISTAL, omitir=(3,), tf=tfk)
    # balcon anular con balaustres y doble tubo cromado
    _cilindro(mg, 0, 0, z_b - 0.35, z_b, 3.9, K_BLANCO, seg=seg, tapa0=True, tapa1=True,
              suave=False)
    for k in range(seg):
        t = 2.0 * math.pi * (k + 0.5) / seg
        xq, yq = 3.72 * math.cos(t), 3.72 * math.sin(t)
        _caja_g(mg, xq - 0.035, xq + 0.035, yq - 0.035, yq + 0.035, z_b, z_b + 1.0,
                K_ACERO, omitir=(0,))
    for zz in (z_b + 0.50, z_b + 0.96):
        _cilindro(mg, 0, 0, zz, zz + 0.06, 3.78, K_CROMO, seg=seg, tapa0=True,
                  tapa1=True, suave=False)
    # tambor: antepecho blanco con banda verde, cristalera A RAS con
    # columnillas cromadas por fuera, dintel, alero con focos y remate
    r_t = 3.0
    _cilindro(mg, 0, 0, z_b, z_b + 0.9, r_t, K_BLANCO, seg=seg, tapa1=False)
    _cilindro(mg, 0, 0, z_b + 0.30, z_b + 0.62, r_t + 0.03, K_VERDE, seg=seg, tapa0=True,
              tapa1=True, suave=False)
    _cilindro(mg, 0, 0, z_b + 0.9, z_b + 2.9, r_t, K_CRISTAL, seg=seg, tapa1=False)
    for k in range(seg):
        t = 2.0 * math.pi * k / seg
        xq, yq = (r_t + 0.03) * math.cos(t), (r_t + 0.03) * math.sin(t)
        _cilindro(mg, xq, yq, z_b + 0.9, z_b + 2.9, 0.06, K_CROMO, seg=4, tapa1=False,
                  suave=False, fase=t)
    _cilindro(mg, 0, 0, z_b + 2.9, alto, r_t, K_BLANCO, seg=seg, tapa1=False)
    _cilindro(mg, 0, 0, alto, alto + 0.25, r_t + 0.35, K_AZUL, seg=seg, tapa0=True,
              tapa1=False, suave=False)
    _cono(mg, 0, 0, alto + 0.25, alto + 1.6, r_t + 0.35, K_AZUL, seg=seg)
    for k in range(4):
        tfk = _rz(math.pi / 4.0 + k * math.pi / 2.0)
        _caja_g(mg, -0.16, 0.16, r_t - 0.02, r_t + 0.34, alto - 0.42, alto - 0.24, K_OSCURO,
                omitir=(3,), mats={0: K_FOCO}, tf=tfk)
    # parabolica sobre el balcon (poste + plato) y antena con baliza roja
    tfp = _rz(math.radians(200.0))
    _caja_g(mg, -0.04, 0.04, 3.30, 3.38, z_b, z_b + 1.6, K_ACERO, omitir=(0, 2), tf=tfp)
    px_, py_ = tfp((0.0, 3.34, 0.0))[:2]
    _cilindro(mg, px_, py_, z_b + 1.6, z_b + 1.95, 0.12, K_BLANCO, r1=0.62, seg=12,
              tapa0=True, tapa1=True, suave=False)
    _caja_g(mg, -0.06, 0.06, -0.06, 0.06, alto + 1.4, alto + 5.0, K_ACERO, omitir=(0,))
    _caja_g(mg, -0.12, 0.12, -0.12, 0.12, alto + 5.0, alto + 5.25, K_LUZ)
    for zz in (alto + 3.0, alto + 4.0):
        _caja_g(mg, -0.5, 0.5, -0.02, 0.02, zz, zz + 0.04, K_ACERO)
    ob = mg.obj('%s_torre_cuerpo' % PRE,
                ('piedra_clara', 'blanco', 'cristal', 'gris_acero', 'azul_techo',
                 'gris_oscuro', 'rojo_luz', 'crema', 'cromo', 'verde_wgp', 'luz_blanca'),
                col)
    ob.parent = raiz
    # rotulo WGP (texto plano) sobre la banda verde del antepecho, 4 caras
    items = []
    for k in range(4):
        t = math.pi / 2.0 + k * math.pi / 2.0
        items.append(('WGP', 0.30, ((r_t + 0.06) * math.cos(t), (r_t + 0.06) * math.sin(t),
                                    z_b + 0.46), t - math.pi / 2.0))
    txt = _textos_malla('%s_torre_texto' % PRE, items, 'blanco', col, extrude=0.0,
                        resolucion=2)
    txt.parent = raiz
    return raiz


# -------------------------------------------------------------------- pasarela

def build_pasarela(parent_collection, luz=22.0, alto=7.0, seed=0, **params):
    """Pasarela cubierta sobre la pista: pasillo de longitud `luz` (a lo largo
    de X, x en [-luz/2, luz/2]) a altura `alto`, entre dos torres de celosia
    metalica de 7.2 x 3.4 m con rampas en zigzag (4 tramos con peto exterior y
    pasamanos cromado; sin escaleras; losas cerradas por debajo). Bandas de
    patrocinio tricolor 'WORLD GRAND PRIX' en ambos costados, luminaria bajo
    el techo y banderas onduladas en las esquinas (malla hija
    PIT_pasarela_banderas). Extension en X: +-(luz/2 + 7.4). Raiz PIT_pasarela."""
    col = parent_collection
    raiz = _raiz('%s_pasarela' % PRE, col)
    luz = max(6.0, float(luz))
    alto = max(4.0, float(alto))
    rng = random.Random(seed)
    a2 = luz / 2.0
    # 0 gris_acero, 1 blanco, 2 azul_oscuro, 3 piedra_clara, 4 azul_techo,
    # 5 gris_oscuro, 6 verde_wgp, 7 cromo, 8 rojo, 9 luz_blanca
    (P_ACERO, P_BLANCO, P_AZUL, P_RAMPA, P_TECHO, P_OSCURO, P_VERDE, P_CROMO,
     P_ROJO, P_LUZ) = range(10)
    mg = _MG()
    wt, dt = 7.2, 3.4               # torre: largo (X) y fondo (Y)
    h_t = alto + 3.3                # coronacion de la torre
    n_r = 4                         # tramos de rampa
    for sx in (-1.0, 1.0):
        xc = sx * (a2 + 0.5 * wt)
        x0, x1 = xc - 0.5 * wt, xc + 0.5 * wt
        for xp in (x0 + 0.15, x1 - 0.15):
            for yp in (-0.5 * dt + 0.15, 0.5 * dt - 0.15):
                _caja_g(mg, xp - 0.15, xp + 0.15, yp - 0.15, yp + 0.15, 0.0, h_t, P_ACERO,
                        omitir=(0, 2))
        niveles = [alto * k / n_r for k in range(1, n_r + 1)] + [h_t - 0.15]
        for zn in niveles:
            for yp in (-0.5 * dt + 0.15, 0.5 * dt - 0.15):
                _caja_g(mg, x0 + 0.3, x1 - 0.3, yp - 0.06, yp + 0.06, zn - 0.12, zn,
                        P_ACERO, omitir=('x0', 'x1'))
            if abs(zn - alto) < 1e-6:
                continue
            for xp in (x0 + 0.15, x1 - 0.15):
                _caja_g(mg, xp - 0.06, xp + 0.06, -0.5 * dt + 0.3, 0.5 * dt - 0.3,
                        zn - 0.30, zn - 0.18, P_ACERO, omitir=(1, 3))
        z_prev = 0.0
        for k, zn in enumerate(niveles):
            for yp in (-0.5 * dt + 0.15, 0.5 * dt - 0.15):
                xa, xb = (x0 + 0.3, x1 - 0.3) if k % 2 == 0 else (x1 - 0.3, x0 + 0.3)
                za_, zb_ = z_prev + 0.15, zn - 0.12 - 0.15
                dx, dz = xb - xa, zb_ - za_
                ln = math.hypot(dx, dz)
                ux, uz = dx / ln, dz / ln
                px, pz = -uz * 0.05, ux * 0.05
                pts = [(xa + px, yp - 0.04, za_ + pz), (xb + px, yp - 0.04, zb_ + pz),
                       (xb - px, yp - 0.04, zb_ - pz), (xa - px, yp - 0.04, za_ - pz)]
                pts2 = [(p[0], yp + 0.04, p[2]) for p in pts]
                i = mg.verts(pts + pts2)
                c = (0.5 * (xa + xb), yp, 0.5 * (z_prev + zn))
                for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6)):
                    mg.cara([i + j for j in q], P_ACERO, False, centro=c)
            z_prev = zn - 0.12
        # rampas en zigzag con peto exterior y pasamanos cromado
        lr = wt - 1.6
        for k in range(n_r):
            za, zb = alto * k / n_r, alto * (k + 1) / n_r
            lane = -1.0 if k % 2 == 0 else 1.0
            y0r, y1r = (lane * 0.5 * dt - lane * 0.35, lane * 0.1)
            y0r, y1r = min(y0r, y1r), max(y0r, y1r)
            sube_x = (k % 2 == 0) == (sx > 0)
            xa, xb = (x0 + 0.8, x0 + 0.8 + lr) if sube_x else (x1 - 0.8 - lr, x1 - 0.8)
            zA, zB = (za, zb) if sube_x else (zb, za)
            _losa(mg, xa, xb, y0r, y1r, zA, zB, 0.12, P_RAMPA, omitir=('x0', 'x1'))
            yp0, yp1 = (y0r, y0r + 0.06) if lane < 0 else (y1r - 0.06, y1r)
            dz_ = 0.02 * (zB - zA) / (xb - xa)
            _losa(mg, xa + 0.02, xb - 0.02, yp0, yp1, zA + 0.55 + dz_, zB + 0.55 - dz_,
                  0.55, P_BLANCO, omitir=(0,))
            _losa(mg, xa + 0.02, xb - 0.02, yp0 - 0.01, yp1 + 0.01, zA + 0.62 + dz_,
                  zB + 0.62 - dz_, 0.05, P_CROMO)
            if k == n_r - 1:
                continue
            xl0, xl1 = (xb, xb + 0.8) if sube_x else (xa - 0.8, xa)
            _losa(mg, xl0, xl1, -0.5 * dt + 0.35, 0.5 * dt - 0.35, zb, zb, 0.12, P_RAMPA)
            xe0, xe1 = (xl1 - 0.06, xl1) if sube_x else (xl0, xl0 + 0.06)
            _caja_g(mg, xe0, xe1, -0.5 * dt + 0.35, 0.5 * dt - 0.35, zb, zb + 0.55,
                    P_BLANCO, omitir=(0,))
        xl0, xl1 = (x1 - 0.8, x1 + 0.8) if sx < 0 else (x0 - 0.8, x0 + 0.8)
        _caja_g(mg, xl0, xl1, -0.5 * dt + 0.35, 0.5 * dt - 0.35, 0.0, 0.05, P_RAMPA,
                omitir=(0,))
        _caja_g(mg, x0 - 0.2, x1 + 0.2, -0.5 * dt - 0.2, 0.5 * dt + 0.2, h_t, h_t + 0.2,
                P_TECHO)
    # pasillo: losa, petos, postes, techo con luminaria
    y0p, y1p = -1.35, 1.35
    _caja_g(mg, -a2 - 0.8, a2 + 0.8, y0p, y1p, alto - 0.3, alto, P_BLANCO)
    for yp0, yp1 in ((y0p, y0p + 0.1), (y1p - 0.1, y1p)):
        _caja_g(mg, -a2 - 0.8, a2 + 0.8, yp0, yp1, alto, alto + 1.05, P_BLANCO, omitir=(0,))
    n_pp = max(2, int(round(luz / 3.6)) + 1)
    for k in range(n_pp):
        xp = -a2 + k * luz / (n_pp - 1)
        for yp in (y0p + 0.08, y1p - 0.08):
            _caja_g(mg, xp - 0.06, xp + 0.06, yp - 0.06, yp + 0.06, alto + 1.05, alto + 2.9,
                    P_ACERO, omitir=(0,))
    _caja_g(mg, -a2 - 0.9, a2 + 0.9, y0p - 0.15, y1p + 0.15, alto + 2.9, alto + 3.05, P_TECHO)
    _caja_g(mg, -a2 + 0.5, a2 - 0.5, -0.25, 0.25, alto + 2.82, alto + 2.9, P_LUZ, omitir=(2,))
    # bandas de patrocinio tricolor a ambos costados (verde / azul / rojo con
    # ribete blanco)
    for sy in (-1.0, 1.0):
        yb0 = y1p + 0.12 if sy > 0 else y0p - 0.12
        yb1 = yb0 + 0.06 * sy
        ya, yb = min(yb0, yb1), max(yb0, yb1)
        om = (3 if sy > 0 else 1,)
        _caja_g(mg, -a2 + 0.3, a2 - 0.3, ya, yb, alto + 1.25, alto + 2.55, P_BLANCO, omitir=om)
        ya2, yb2 = (yb, yb + 0.03) if sy > 0 else (ya - 0.03, ya)
        for xa_, xb_, mcol, omx in ((-a2 + 0.4, -a2 + 1.5, P_VERDE, ('x1',)),
                                    (-a2 + 1.5, a2 - 1.5, P_AZUL, ('x0', 'x1')),
                                    (a2 - 1.5, a2 - 0.4, P_ROJO, ('x0',))):
            _caja_g(mg, xa_, xb_, ya2, yb2, alto + 1.35, alto + 2.45, mcol, omitir=om + omx)
    ob = mg.obj('%s_pasarela_cuerpo' % PRE,
                ('gris_acero', 'blanco', 'azul_oscuro', 'piedra_clara', 'azul_techo',
                 'gris_oscuro', 'verde_wgp', 'cromo', 'rojo', 'luz_blanca'), col, separar=True)
    ob.parent = raiz
    # banderas onduladas en las esquinas del techo (malla aparte, doble cara)
    mb = _MG()
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            xq, yq = sx * (a2 + 0.6), sy * 1.3
            _caja_g(mb, xq - 0.03, xq + 0.03, yq - 0.03, yq + 0.03, alto + 3.05,
                    alto + 4.5, 0, omitir=(0,))
            _bandera(mb, xq + 0.03, yq, alto + 3.75, alto + 4.42, 1.0, (1, 2, 3),
                     rng.uniform(0.0, 6.28), nx=4, amp=0.07)
    band = mb.obj('%s_pasarela_banderas' % PRE, ('gris_acero', 'verde_wgp', 'blanco', 'rojo'),
                  col)
    band.parent = raiz
    tam = min(0.8, (luz - 5.0) / 16.0 / 0.62)
    y_txt = y1p + 0.12 + 0.06 + 0.03 + 0.03      # texto a 3 cm de la banda
    tx = _texto_3d('%s_pasarela_texto' % PRE, 'WORLD GRAND PRIX', tam, 'blanco', col,
                   extrude=0.0, pos=(0.0, y_txt, alto + 1.9))
    tx.parent = raiz
    tx2 = _texto_3d('%s_pasarela_texto_dorso' % PRE, 'WORLD GRAND PRIX', tam, 'blanco',
                    col, extrude=0.0, pos=(0.0, -y_txt, alto + 1.9), rot_z=math.pi)
    tx2.parent = raiz
    return raiz


# ------------------------------------------------------- marcas del pit lane

def _texto_en_mg(mg, texto, tam, pos, rot_z, mat, plano=True, resolucion=1):
    """Anade a la malla generica `mg` las caras (sin extrusion) de un texto
    centrado en `pos`: plano (normal +Z, legible desde -Y con rot_z = 0) o de
    pie (legible desde +Y con rot_z = 0)."""
    cu = bpy.data.curves.new('PIT_txt_cu', type='FONT')
    cu.body = texto
    cu.size = tam
    cu.extrude = 0.0
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.resolution_u = resolucion
    tmp = bpy.data.objects.new('PIT_txt_tmp', cu)
    me_t = bpy.data.meshes.new_from_object(tmp)
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    x, y, z = pos
    pts = []
    if plano:
        co, si = math.cos(rot_z), math.sin(rot_z)
        for v in me_t.vertices:
            px, py, pz = v.co.x, v.co.y, v.co.z
            pts.append((x + px * co - py * si, y + px * si + py * co, z + pz))
        deseada = (0.0, 0.0, 1.0)
    else:
        co, si = math.cos(math.pi + rot_z), math.sin(math.pi + rot_z)
        for v in me_t.vertices:
            px, py, pz = v.co.x, -v.co.z, v.co.y
            pts.append((x + px * co - py * si, y + px * si + py * co, z + pz))
        deseada = (-math.sin(rot_z), math.cos(rot_z), 0.0)
    i0 = mg.verts(pts)
    for p in me_t.polygons:
        mg.cara([i0 + i for i in p.vertices], mat, False, ref=deseada)
    bpy.data.meshes.remove(me_t)


def build_marcas_pit_lane(parent_collection, largo, ancho_pit=7.5, n=20, ancho_box=6.0,
                          seed=0, sentido=-1, z=0.03, numeros='garajes', **params):
    """Marcas viales del pit lane en UNA malla plana 'PIT_marcas' (z = 0.03
    sobre el asfalto: >= 3 cm para que no haya z-fighting de lejos en AC):
    origen en el centro del tramo, X a lo largo del pit lane, +Y = lado de los
    garajes; el asfalto del pit lane ocupa y en [-ancho_pit/2, ancho_pit/2].
    - linea blanca continua de borde a ambos lados;
    - linea amarilla continua (zona de velocidad limitada) que separa el
      carril rapido (lado pista) del carril de trabajo de 4.2 m (lado boxes);
    - caja amarilla (5.2 x 3.65 m) con el numero delante de cada porton; los
      boxes van centrados en x = sentido * (-n*ancho_box/2 + (i + 0.5) *
      ancho_box), numeracion creciente en el sentido de la marcha;
    - franja blanca transversal y "60" pintado (legible por el piloto) al
      principio y al final del tramo.
    `sentido` = sentido de la marcha a lo largo de X local (-1 por defecto:
    la malla se coloca girada 180 grados respecto al edificio de boxes).
    `numeros` = orientacion de los numeros de las cajas: 'garajes' (legibles
    desde los garajes, mirando hacia -Y, y en cenital) o 'piloto' (legibles
    por el piloto que circula en el sentido de la marcha, como los "60")."""
    col = parent_collection
    largo = float(largo)
    a2 = largo / 2.0
    hp = 0.5 * float(ancho_pit)
    s = -1.0 if sentido < 0 else 1.0
    n = max(1, int(n))
    w = float(ancho_box)
    rot_num = -s * math.pi / 2.0 if str(numeros).lower() == 'piloto' else math.pi
    M_BL, M_AM = 0, 1
    mg = _MG()

    def franja_x(x0, x1, y0, y1, mat):
        _quad(mg, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], mat, (0, 0, 1))

    # bordes blancos y linea amarilla de velocidad limitada
    franja_x(-a2, a2, hp - 0.175, hp - 0.025, M_BL)
    franja_x(-a2, a2, -hp + 0.025, -hp + 0.175, M_BL)
    y_am = hp - 4.2
    franja_x(-a2, a2, y_am - 0.06, y_am + 0.06, M_AM)
    # franjas transversales de speed limit y "60" al principio y al final
    for xe, sgn in ((-a2 + 2.5, 1.0), (a2 - 2.5, -1.0)):
        franja_x(xe - 0.2, xe + 0.2, -hp + 0.25, y_am - 0.10, M_BL)
        franja_x(xe - 0.2, xe + 0.2, y_am + 0.10, hp - 0.25, M_BL)
        _texto_en_mg(mg, '60', 2.6, (xe + sgn * 3.0, -hp + 0.5 * (y_am + hp), z + 0.002),
                     -s * math.pi / 2.0, M_BL, plano=True, resolucion=4)
    # cajas de los boxes con su numero
    ya, yb = hp - 4.0, hp - 0.35
    e = 0.12
    for i in range(n):
        xi = s * (-0.5 * n * w + (i + 0.5) * w)
        if abs(xi) + 2.6 > a2:
            continue
        franja_x(xi - 2.6, xi - 2.6 + e, ya, yb, M_AM)
        franja_x(xi + 2.6 - e, xi + 2.6, ya, yb, M_AM)
        franja_x(xi - 2.6 + e, xi + 2.6 - e, ya, ya + e, M_AM)
        franja_x(xi - 2.6 + e, xi + 2.6 - e, yb - e, yb, M_AM)
        _texto_en_mg(mg, str(i + 1), 1.4, (xi, 0.5 * (ya + yb), z + 0.002), rot_num, M_AM,
                     plano=True, resolucion=3)
    ob = mg.obj('%s_marcas' % PRE, ('marca_blanca', 'marca_amarilla'), col)
    return ob


# ------------------------------------------------------------------ escaparate

def build(parent_collection, seed=0, **params):
    """Escaparate del complejo: edificio de boxes (n=20) en el origen, pit
    lane de 12 m delante con sus marcas (PIT_marcas de largo L+24, girada 180
    grados), muro de boxes (tramos con tapas en los extremos), pista de 16 m,
    torres de control en (+-(L/2 + 18), 3.0) (lado de los garajes, fuera del
    pit lane, junto a su entrada y su salida) y pasarela de 40 m cruzando la
    pista en x = L/2 + 25 con las patas fuera del pit lane y de la pista.
    Todo sobre asfalto."""
    col = parent_collection
    raiz = _raiz('%s_kit' % PRE, col)
    n = int(params.get('n', 20))
    w = float(params.get('ancho_box', 6.0))
    L = n * w
    y_f = 0.5 * _FONDO
    y_muro = y_f + 12.0
    y_pista0, y_pista1 = y_muro + 0.5, y_muro + 16.5

    mg = _MG()   # 0 asfalto, 1 marca_blanca, 2 piedra_clara, 3 hormigon
    y_fin = y_pista1 + 24.0
    _quad(mg, [(-L / 2 - 34, -20, -0.02), (L / 2 + 34, -20, -0.02),
               (L / 2 + 34, y_fin, -0.02), (-L / 2 - 34, y_fin, -0.02)],
          0, (0, 0, 1))
    _quad(mg, [(-L / 2 - 34, y_pista1, 0.0), (L / 2 + 34, y_pista1, 0.0),
               (L / 2 + 34, y_fin, 0.0), (-L / 2 - 34, y_fin, 0.0)],
          2, (0, 0, 1))
    # acera de 1.6 m entre la fachada y el pit lane
    _quad(mg, [(-L / 2 - 4, y_f, 0.0), (L / 2 + 4, y_f, 0.0),
               (L / 2 + 4, y_f + 1.6, 0.0), (-L / 2 - 4, y_f + 1.6, 0.0)], 3, (0, 0, 1))
    for yy in (y_pista0 + 0.4, y_pista1 - 0.4):
        _quad(mg, [(-L / 2 - 20, yy - 0.08, 0.005), (L / 2 + 20, yy - 0.08, 0.005),
                   (L / 2 + 20, yy + 0.08, 0.005), (-L / 2 - 20, yy + 0.08, 0.005)],
              1, (0, 0, 1))
    suelo = mg.obj('%s_suelo' % PRE, ('asfalto', 'marca_blanca', 'piedra_clara', 'hormigon'),
                   col)
    suelo.parent = raiz

    boxes = build_boxes_tribuna(col, n=n, ancho_box=w, seed=seed)
    boxes.parent = raiz

    marcas = build_marcas_pit_lane(col, largo=L + 24.0, ancho_pit=7.5, n=n, ancho_box=w,
                                   seed=seed, sentido=-1)
    marcas.location = (0.0, y_f + 1.6 + 3.75, 0.0)
    marcas.rotation_euler = (0.0, 0.0, math.pi)
    marcas.parent = raiz

    n_m = max(1, int(round(L / 12.0)))
    for k in range(n_m):
        muro = build_muro_boxes(col, largo=12.0, seed=seed + k, tapa_x0=(k == 0),
                                tapa_x1=(k == n_m - 1))
        muro.location = (-L / 2 + (k + 0.5) * 12.0, y_muro, 0.0)
        muro.parent = raiz

    # torres de control FUERA del pit lane: en el lado de los garajes, mas
    # alla de los testeros del edificio (x = +-(L/2 + 18), y = 3.0: plinto
    # r=2.7 y balcon r=3.9 quedan en y <= 6.9, bajo el borde del pit lane en
    # y = 8.1, y mas alla de x = +-74 > +-72 de PIT_marcas), con la puerta
    # mirando al pit lane. No tapan la franja de speed limit ni los '60' y
    # un coche puede entrar y salir del pit lane sin encontrarselas.
    x_torre = L / 2 + 18.0
    for sx in (-1.0, 1.0):
        torre = build_torre_control(col, alto=16.0, seed=seed)
        torre.location = (sx * x_torre, 3.0, 0.0)
        torre.parent = raiz

    # pasarela cruzando la pista en x = L/2 + 25 (celosias de 3.8 m de fondo
    # en x): pasillo de 40 m centrado en la pista, de modo que la pata de
    # este lado (y -0.4..7.0) queda en el paddock, fuera del pit lane, y la
    # del otro lado (y 47..54.4) mas alla de la pista
    luz_p = 40.0
    pasarela = build_pasarela(col, luz=luz_p, alto=7.0, seed=seed)
    pasarela.location = (L / 2 + 25.0, 0.5 * (y_pista0 + y_pista1), 0.0)
    pasarela.rotation_euler = (0.0, 0.0, math.pi / 2)
    pasarela.parent = raiz
    return raiz
