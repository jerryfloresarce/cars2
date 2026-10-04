"""camara_segura.py - recoloca camaras de captura que quedan DENTRO del terreno o de una roca,
o con la vista tapada nada mas salir (el macizo nuevo es mas alto que el terreno con el que
se calcularon las posiciones). Las vistas de piloto, 'desde_pista' y del tunel no se tocan.

    from camara_segura import asegurar
    loc, tgt = asegurar(nombre, loc, tgt)        # (Vector, Vector) -> (Vector, Vector)
"""
import bpy
from mathutils import Vector

NO_TOCAR = ('piloto', 'desde_pista', 'tunel', 'pit_lane', 'travesia', 'yates_desde')


def _hit(sc, dg, a, b):
    d = b - a
    L = d.length
    if L < 1e-6:
        return None
    ok, loc, nrm, idx, ob, mw = sc.ray_cast(dg, a, d.normalized(), distance=L)
    if not ok:
        return None
    return (loc - a).length / L, ob, loc


def _dentro(sc, dg, p):
    """True si p esta bajo una superficie (rayo hacia arriba que choca con la cara de atras
    de algo o vertical que encuentra suelo por encima)."""
    ok, loc, nrm, idx, ob, mw = sc.ray_cast(dg, p, Vector((0, 0, 1)), distance=3000.0)
    if ok and nrm.z < 0.0:
        return False                  # techo de verdad (un puente, un alero): no estamos dentro
    return ok


LIGERO = ('desde_pista', 'travesia', 'yates_desde', 'desde_grua')   # a ras de suelo: solo subir un poco


def _ajuste_ligero(nombre, loc, tgt):
    """Vistas a ras de pista: si algo (roca, tribuna, muro) tapa la vista en el primer 35 %
    del recorrido, sube la camara de 2.5 en 2.5 m (hasta 12.5 m); no la aleja."""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    loc = Vector(loc)
    tgt = Vector(tgt)
    k = 0
    for k in range(6):
        h = _hit(sc, dg, loc, tgt)
        if (h is None or h[0] >= 0.35) and not _dentro(sc, dg, loc):
            break
        loc = loc + Vector((0.0, 0.0, 2.5))
    if k:
        print('camara_segura (ligero): %s subida %.1f m' % (nombre, 2.5 * k))
    return loc, tgt


def asegurar(nombre, loc, tgt, max_subidas=14, paso=12.0):
    if any(k in nombre for k in LIGERO):
        return _ajuste_ligero(nombre, loc, tgt)
    if any(k in nombre for k in NO_TOCAR):
        return loc, tgt
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    loc = Vector(loc)
    tgt = Vector(tgt)
    for k in range(max_subidas):
        dentro = _dentro(sc, dg, loc)
        h = _hit(sc, dg, loc, tgt)
        # tapada solo si lo que corta la vista es el TERRENO (el sujeto de la foto -roca, coche-
        # puede contener al objetivo y entonces siempre 'taparia')
        tapada = h is not None and h[0] < 0.9 and h[1] is not None and h[1].name.startswith('TERRENO') and (h[2] - tgt).length > 25.0
        if not dentro and not tapada:
            break
        loc = loc + Vector((0.0, 0.0, paso))
        # y algo hacia atras (alejandose del objetivo) para abrir la vista
        d = loc - tgt
        d.z = 0.0
        if d.length > 1e-3:
            loc = loc + d.normalized() * (paso * 0.6)
    if k:
        print('camara_segura: %s subida %d pasos -> (%.0f, %.0f, %.0f)' % (nombre, k, loc.x, loc.y, loc.z))
    return loc, tgt
