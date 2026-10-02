# Genera trazado_v02.json a partir de los puntos digitalizados del mapa en alta
# resolucion (687x753 px) y calcula la escala para que la vuelta mida 5200 m.
import json, math, os

# x, y, curva (o None), seccion, nota
# secciones: straight (rojo), tech (azul), dirt (amarillo), norm (negro)
P = [
    (275, 380, None, 'straight', 'META - bandera a cuadros, sentido hacia curva 01 (noroeste)'),
    (240, 362, None, 'straight', None),
    (207, 341, 1,    'straight', 'kink en la diagonal de meta'),
    (172, 295, None, 'straight', None),
    (150, 262, None, 'straight', None),
    (135, 240, 2,    'straight', 'kink: la diagonal pasa a rumbo oeste'),
    (100, 234, None, 'straight', None),
    (55,  232, None, 'straight', None),
    (10,  232, 3,    'tech', 'horquilla del extremo izquierdo'),
    (30,  196, None, 'tech', None),
    (52,  172, None, 'tech', None),
    (75,  156, 4,    'tech', None),
    (100, 168, None, 'tech', None),
    (122, 172, 5,    'tech', None),
    (124, 145, None, 'tech', None),
    (122, 118, 6,    'tech', None),
    (145, 112, None, 'tech', None),
    (172, 115, 7,    'tech', None),
    (198, 124, None, 'tech', None),
    (222, 140, 8,    'tech', None),
    (240, 185, None, 'tech', None),
    (262, 240, 9,    'tech', None),
    (285, 225, None, 'tech', None),
    (307, 212, 10,   'tech', None),
    (312, 240, None, 'tech', None),
    (312, 274, 11,   'norm', None),
    (330, 260, 12,   'norm', 'posicion aproximada (etiqueta poco legible)'),
    (344, 250, 13,   'norm', 'posicion aproximada (etiqueta poco legible)'),
    (352, 240, 14,   'dirt', 'entrada a la seccion de tierra'),
    (380, 238, None, 'dirt', None),
    (406, 242, 15,   'dirt', 'zigzag de subida - posicion aproximada'),
    (382, 225, None, 'dirt', None),
    (355, 214, 16,   'dirt', None),
    (348, 175, None, 'dirt', None),
    (352, 135, 17,   'dirt', 'subida por la ladera'),
    (338, 105, None, 'dirt', None),
    (322, 82,  18,   'dirt', 'horquilla superior (punto mas alto)'),
    (330, 62,  None, 'dirt', None),
    (355, 55,  None, 'dirt', None),
    (380, 62,  None, 'dirt', None),
    (398, 85,  None, 'dirt', None),
    (420, 118, 19,   'dirt', None),
    (420, 143, 20,   'dirt', None),
    (424, 167, 21,   'dirt', None),
    (424, 201, 22,   'dirt', None),
    (440, 222, None, 'dirt', None),
    (452, 243, 23,   'dirt', 'posicion aproximada'),
    (432, 268, None, 'dirt', None),
    (415, 286, 24,   'dirt', None),
    (408, 305, None, 'dirt', None),
    (404, 322, 25,   'dirt', None),
    (372, 310, None, 'dirt', None),
    (342, 292, 26,   'dirt', 'salida de la seccion de tierra'),
    (358, 325, None, 'norm', None),
    (375, 350, None, 'norm', None),
    (390, 368, 27,   'norm', None),
    (400, 396, 28,   'norm', None),
    (406, 425, None, 'norm', None),
    (408, 452, 29,   'norm', 'horquilla izquierda antes de la recta'),
    (425, 432, None, 'norm', None),
    (445, 408, 30,   'straight', 'entrada a la recta rapida'),
    (495, 468, None, 'straight', None),
    (545, 530, None, 'straight', None),
    (592, 592, 31,   'tech', 'final de recta - complejo tecnico inferior'),
    (570, 615, None, 'tech', None),
    (552, 630, 32,   'tech', None),
    (568, 650, None, 'tech', None),
    (585, 662, 33,   'tech', None),
    (602, 650, None, 'tech', None),
    (608, 630, 34,   'tech', 'posicion aproximada (etiqueta poco legible)'),
    (612, 608, 35,   'tech', None),
    (630, 612, None, 'tech', None),
    (645, 628, 36,   'tech', None),
    (658, 648, None, 'tech', None),
    (665, 672, 37,   'tech', 'posicion aproximada (etiqueta poco legible)'),
    (675, 695, None, 'tech', None),
    (675, 718, 38,   'tech', 'esquina inferior derecha'),
    (650, 700, None, 'tech', None),
    (630, 688, None, 'tech', None),
    (612, 678, 39,   'tech', None),
    (605, 698, None, 'tech', None),
    (612, 718, 40,   'tech', None),
    (585, 722, None, 'tech', None),
    (558, 718, 41,   'tech', None),
    (505, 680, None, 'norm', None),
    (460, 650, 42,   'norm', None),
    (430, 672, None, 'norm', None),
    (400, 710, None, 'norm', None),
    (372, 745, 43,   'norm', 'horquilla inferior'),
    (390, 700, None, 'norm', None),
    (405, 648, None, 'norm', None),
    (415, 595, 44,   'norm', None),
    (418, 560, None, 'norm', None),
    (420, 524, 45,   'norm', None),
    (408, 498, None, 'norm', None),
    (395, 478, 46,   'norm', None),
    (372, 486, None, 'norm', None),
    (355, 498, 47,   'norm', None),
    (340, 482, None, 'norm', None),
    (338, 464, 48,   'norm', None),
    (362, 458, None, 'norm', None),
    (385, 455, 49,   'norm', None),
    (372, 420, None, 'norm', None),
    (357, 380, 50,   'straight', 'se incorpora a la diagonal de meta'),
    (315, 381, None, 'straight', None),
]

LARGO_OBJETIVO_M = 5200.0

def catmull_rom_length(pts, samples_per_seg=40):
    n = len(pts)
    total = 0.0
    for i in range(n):
        p0 = pts[(i - 1) % n]; p1 = pts[i]
        p2 = pts[(i + 1) % n]; p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0)
        prev = p1
        for s in range(1, samples_per_seg + 1):
            t = s / samples_per_seg
            mt = 1 - t
            x = mt**3 * p1[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * p2[0]
            y = mt**3 * p1[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * p2[1]
            total += math.hypot(x - prev[0], y - prev[1])
            prev = (x, y)
    return total

xy = [(p[0], p[1]) for p in P]
largo_px = catmull_rom_length(xy)
m_por_px = LARGO_OBJETIVO_M / largo_px

data = {
    'version': '0.2',
    'descripcion': ('Trazado de Porto Corsa (Cars 2) digitalizado desde el mapa en alta resolucion '
                    '(687x753 px). Numeracion corregida: meta entre curvas 50 y 01, sentido noroeste.'),
    'imagen_referencia': {'ancho_px': 687, 'alto_px': 753},
    'largo_objetivo_m': LARGO_OBJETIVO_M,
    'largo_trazado_px': round(largo_px, 1),
    'metros_por_px': round(m_por_px, 4),
    'sentido': 'desde meta hacia el noroeste (curvas 01, 02, 03...)',
    'meta': {'x': 275, 'y': 380},
    'secciones': {
        'straight': 'Recta rapida (rojo): diagonal de meta (50->03) y recta 30->31',
        'tech': 'Curvas tecnicas (azul): 03-10 arriba-izquierda y 31-41 abajo-derecha',
        'dirt': 'Seccion de tierra (amarillo): 14-26, subida en zigzag por la ladera',
        'norm': 'Asfalto normal (negro)',
    },
    'zonas_dudosas': [
        'Curvas 12-16: etiquetas poco legibles en la zona de enlace con la tierra',
        'Curva 23 y el tramo 22->24',
        'Curvas 34 y 37 en el complejo inferior derecho',
    ],
    'puntos': [
        {'x': x, 'y': y, 'curva': c, 'seccion': s, **({'nota': n} if n else {})}
        for (x, y, c, s, n) in P
    ],
}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trazado_v02.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Largo del trazado: {largo_px:.0f} px')
print(f'Escala para {LARGO_OBJETIVO_M:.0f} m: {m_por_px:.4f} m/px')
print(f'Ancho de pista sugerido 12 m = {12 / m_por_px:.1f} px en el mapa')
print(f'Guardado: {out}')
