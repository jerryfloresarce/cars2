# -*- coding: utf-8 -*-
"""color_ac.py (v3) - recalibra los colores y los parametros de shader de Porto Corsa para Assetto Corsa.

PROBLEMA: en AC el circuito sale casi blanco, lavado y plano. Causas (03_blender/_rev/color_ac/, fuentes en
investigacion.md):
  1. AC sin CSP (y CSP con estilos gamma: Pure Gamma, Sol) sombrea en ESPACIO GAMMA: escena = textura_sRGB *
     (ksAmbient*AMBIENTE + ksDiffuse*SOL*N.L), tiempo 3_clear (SOL 13.3/12.5/11.0, AMBIENTE 4.53), autoexposicion
     limitada a [0.2, 0.5] y curva Yebis + gamma 1.2. Con nuestras texturas pastel la exposicion se queda en su
     minimo 0.2 y lo iluminado cae en el hombro de la curva: blanco y sin saturacion.
  2. El writer solo ve el diffuse_color de los materiales procedurales (MAT_terreno exporta un verde pastel 3-5
     veces mas claro que la hierba del render, y sus laderas de roca salian del mismo verde).
  3. La luz de nuestro render de Blender es AZULADA (cielo muy fuerte) y la de AC calida (sol 170,160,140).
  4. Con tiempos nublados o estilos de WeatherFX con mucho ambiente (la captura del amigo encaja con eso, ver
     ajuste_captura.py y tiempos_captura.py) el ambiente pesa mas que el sol: con ksAmbient alto todo sale plano.

SOLUCION (sin tocar la geometria salvo el reparto hierba / roca del terreno):
  * calibrar_todos(infos): para cada material, la textura que hace que AC muestre en pantalla lo mismo que nuestro
    render de Blender, CANAL A CANAL, en caras de referencia (suelo al sol, pared al sol, sombras), con el aspecto
    MEDIDO de cada material en 7 vistas de Blender (color_ac_objetivos.json) o albedo x luz si no se ve. Compromiso
    entre modos de sombreado (PESO_MODOS): GAMMA (sin CSP / estilos gamma, 0.6) y LINEAL (CSP con LCS: curva ACES y
    sRGB + Yebis, 0.2 cada una; en el ajuste solo deciden colores y brillos relativos, EXPO_LCS_AJUSTE), con techo de
    croma, techo para blancos, suelo para negros y GUARDA DE REGRESION (ningun material peor que con el KN5 de antes
    en ningun modo, en las caras de referencia).
  * FAMILIAS: ksAmbient 0.45 / ksDiffuse 0.60 en todas (rejilla_ks.py con la configuracion estimada del amigo en el
    coste) y ksSpecular/ksSpecularEXP por familia.
  * separar_roca_terreno(): en el writer, las caras de roca de MAT_terreno pasan a MAT_terreno_roca.
  * generar_ext_config(ruta) / copiar_ext_config(destino): extension/ext_config.ini para CSP (sin CSP no se lee);
    nunca machaca un ext_config.ini ya ajustado a mano.
  * informe(infos): antes/despues por familia (modo gamma; los demas se comparan en las vistas).
Funciona igual dentro de Blender (kn5_writer_opt.py) y con el Python del sistema (pruebas, numpy).
"""
import json
import math
import os
import shutil

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
VERSION = 'color_ac v3 (2026-10-04)'

# ============================================================================= modelo de AC en espacio GAMMA
# content/weather/3_clear (SDK de AC; tabla de newksEditor src/lighting.js): cada componente HDR = RGB*intensidad/255
# (ksNet.dll GraphicsManager::loadLightingSettings). HIGH = sol alto (mezcla pow(1-sol.y, 3.4) ~ 0 con sol a 56 grados).
SOL_AC = np.array([170.0, 160.0, 140.0]) * 20.0 / 255.0          # (13.33, 12.55, 10.98) calido
AMB_AC = np.array([105.0, 105.0, 105.0]) * 11.0 / 255.0          # 4.53 gris neutro
CIELO_AC = np.array([30.0, 73.0, 167.0]) * 3.0 / 255.0            # SKY HIGH
HORIZONTE_AC = np.array([150.0, 170.0, 220.0]) * 3.5 / 255.0      # HORIZON HIGH
NIEBLA_AC = (np.array([1.8, 2.37, 3.42]), 0.85, 9000.0)           # FOG color, blend, distancia (3_clear)
# system/cfg/ppfilters/default.ini: AUTO_EXPOSURE MIN 0.2 MAX 0.5 TARGET 0.32 (media de luminancia de la escena
# HDR), TONEMAPPING GAMMA 1.2 FUNCTION -1 (curva Yebis), COLOR SATURATION 0.95 (antes de la curva).
EXPO_MIN, EXPO_MAX, EXPO_OBJETIVO = 0.2, 0.5, 0.32
TM_A, TM_B, TM_GAMMA, PP_SAT = 2.6581413746, 0.6653175950, 1.2, 0.95
EXPO_DISENO = 0.2        # la autoexposicion se queda en 0.2 en las 9 vistas simuladas, antes y despues
ELEV_SOL = math.radians(56.0)        # sol de escena_rev.blend (hacia_sol.z = 0.829)
COS_SUELO = math.sin(ELEV_SOL)       # N.L de una cara horizontal (0.83)
COS_PARED = 0.43                      # N.L mediano de las paredes al sol en las vistas (0.33-0.54)


def _curva_tiempo(ag, bajo, alto):
    """colorCurves.ini v3: RGB*intensidad/255, mezcla HIGH->LOW con pow(1 - sol.y, ANGLE_GAMMA) (newksEditor)."""
    m = (1.0 - math.sin(ELEV_SOL)) ** ag
    b, a = np.array(bajo[:3]) * bajo[3] / 255.0, np.array(alto[:3]) * alto[3] / 255.0
    return a + (b - a) * m


# Tiempos de Kunos (sdk/editor/content/weather, tabla de newksEditor src/lighting.js): (SOL, AMBIENTE, NIEBLA) con el sol
# de la escena (56 grados). Solo para comprobar que el resultado aguanta otros tiempos (simular_vistas.py); el ajuste
# usa 3_clear. 5_light_clouds es el tiempo con el que arranca el editor; con nubes el ambiente pesa el doble que el sol.
TIEMPOS_AC = {
    '3_clear': (_curva_tiempo(3.4, (229.5, 140, 70, 40), (170, 160, 140, 20)),
                _curva_tiempo(3.4, (124, 124, 124, 18), (105, 105, 105, 11)), (np.array([1.8, 2.37, 3.42]), 0.85, 9000.0)),
    '5_light_clouds': (_curva_tiempo(1.8, (229.5, 168.3, 86.7, 6), (170, 170, 160, 6)),
                       _curva_tiempo(1.8, (135, 120, 118, 11), (124, 134, 145, 15)), (np.array([1.5, 2.25, 3.5]), 0.8, 12000.0)),
    '2_light_fog': (_curva_tiempo(1.8, (200.5, 110.3, 46.7, 9), (170, 165, 160, 8)),
                    _curva_tiempo(1.8, (130, 120, 105, 10), (130, 135, 140, 10)), (np.array([4.15, 4.15, 4.15]), 0.85, 2700.0)),
}

# Configuracion ESTIMADA del amigo (03_blender/_rev/color_ac/ajuste_captura.py -> config_captura.json: 4 parametros
# ajustados a UNA captura; no es un dato): estilo gamma con sol blanco de WeatherFX, ambiente x4.4, brillo x0.5 (la
# autoexposicion en su minimo 0.2 -> 0.1), saturacion 1.0 y bruma a 400 m (la bruma no cabe en las caras de referencia:
# solo en las vistas). Modo 'cap' del ajuste. CAP_BRILLO_DEFECTO: la misma con el brillo por defecto ("antes era peor").
CAP_AMBIENTE, CAP_BRILLO, CAP_SAT, CAP_BRILLO_DEFECTO = 4.4, 0.5, 1.0, 1.0

# ============================================================================= modelo de CSP en espacio LINEAL
# Wiki de CSP 'Linear color space': los estilos LCS pasan el producto textura*parametro por toLinearColorSpace()
# y la conversion que cita es pow(x, 2.2). El estilo es fisico (como Blender): sol y cielo se toman con la luz
# MEDIDA de nuestro render (K_BLENDER), sin oclusion ni rebote fino; ks = 0.5 equivale a 'sin cambio' (CSP pide
# ksAmbient/ksDiffuse ~0.4-0.6). Exposicion automatica (media logaritmica de la luminancia -> 0.18) y dos curvas
# posibles (la de cada estilo no esta documentada): ACES (pantalla_lcs) o sRGB + Yebis (pantalla_lcs_yebis).
LCS_GAMMA = 2.2
LCS_KS_REF = 0.5
LCS_MEDIA = 0.18        # clave de la autoexposicion (media logaritmica)

# ============================================================================= referencia: luz de Blender
# Render de capturas_avance: EEVEE (GI + rayos), vista Standard, sol 4.6 (1, .96, .88), exposicion +0.12, cielo azul.
# K = pantalla_lineal / albedo POR CANAL, mediana de las 6 vistas de ajuste de la v2 (render_ac.py: pase 'ref' / pase
# 'alb' en materiales difusos sin recortar; simular_vistas.py -> luz_escena.json). El cielo rellena mucho y tine de azul.
# Con la escena congelada de la v3 y sus 7 vistas sale casi lo mismo (1.67/1.80/2.39, 1.08/1.19/1.40, 0.34/0.47/0.63,
# 0.23/0.41/0.70: menos de un 7 % de diferencia); se dejan estos para no mover el ajuste. Solo se usan donde un material
# no tiene aspecto medido y para la luz de los modos lineales.
K_BLENDER = {'suelo_sol': (1.65, 1.82, 2.30), 'pared_sol': (1.15, 1.27, 1.42),
             'sombra_pared': (0.36, 0.49, 0.65), 'sombra_suelo': (0.23, 0.41, 0.65)}
HOMBRO_INICIO = 0.80                  # hombro suave en lugar del recorte duro de la vista Standard


# ============================================================================= utilidades de color
def srgb_a_lineal(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, np.power((np.maximum(c, 0) + 0.055) / 1.055, 2.4))


def lineal_a_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055)


def luminancia(c):
    c = np.asarray(c, dtype=np.float64)
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


def saturar(c, s):
    """Mezcla con la luminancia (Rec.709) como el filtro COLOR SATURATION de AC: s<1 desatura."""
    c = np.asarray(c, dtype=np.float64)
    l = luminancia(c)[..., None]
    return l + (c - l) * s


_M_XYZ = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
_BLANCO = np.array([0.95047, 1.0, 1.08883])


def lab(srgb):
    """sRGB 0..1 -> CIE L*a*b* (D65). Para medir diferencias (deltaE) y croma como el revisor."""
    xyz = srgb_a_lineal(srgb) @ _M_XYZ.T / _BLANCO
    f = np.where(xyz > 0.008856, np.cbrt(np.maximum(xyz, 0)), 7.787 * xyz + 16.0 / 116.0)
    return np.stack([116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])], -1)


def croma(srgb):
    l = lab(srgb)
    return np.hypot(l[..., 1], l[..., 2])


def tonemap_ac(x):
    """Curva de AC (Yebis FUNCTION=-1 + gamma 1.2): x = escena * exposicion -> pantalla 0..1 (sRGB)."""
    x = np.maximum(np.asarray(x, dtype=np.float64), 2.0 ** -14)
    q = np.exp(-x * TM_A)
    y = np.clip((1.0 - q) * (1.0 - q * TM_B) ** 2, 0.0, 1.0)
    return np.power(np.minimum(1.0, y + 2.0 ** -22), 1.0 / TM_GAMMA)


def aces(x):
    """Curva ACES (ajuste de Narkowicz): lineal -> lineal de pantalla 0..1."""
    x = np.maximum(np.asarray(x, dtype=np.float64), 0.0)
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0)


_TM_X = np.concatenate([np.linspace(0.0, 1.0, 4001)[:-1], np.linspace(1.0, 12.0, 4401)])
_TM_Y = tonemap_ac(_TM_X)
_ACES_Y = aces(_TM_X)


def tonemap_ac_inv(d):
    """Inversa numerica de tonemap_ac (monotona): pantalla -> x."""
    return np.interp(np.clip(np.asarray(d, dtype=np.float64), 0.0, float(_TM_Y[-1])), _TM_Y, _TM_X)


def aces_inv(y):
    return np.interp(np.clip(np.asarray(y, dtype=np.float64), 0.0, float(_ACES_Y[-1])), _ACES_Y, _TM_X)


def autoexposicion_ac(lum_media):
    """Autoexposicion de ppfilters/default.ini: TARGET / luminancia media, limitada a [MIN, MAX]."""
    return float(np.clip(EXPO_OBJETIVO / max(float(lum_media), 1e-4), EXPO_MIN, EXPO_MAX))


def hombro(v, inicio=HOMBRO_INICIO):
    """Recorte suave: lineal hasta `inicio`, despues se acerca a 1 sin llegar (nada quemado)."""
    v = np.asarray(v, dtype=np.float64)
    r = 1.0 - inicio
    return np.where(v <= inicio, v, inicio + r * (1.0 - np.exp(-(v - inicio) / r)))


def pantalla_blender(albedo_lin, k_luz, suave=True):
    """Lo que muestra nuestro render de Blender para un albedo lineal en una cara con luz medida k_luz (por canal):
    sRGB(albedo * K), con hombro suave en vez del recorte duro de la vista Standard."""
    v = np.asarray(albedo_lin, dtype=np.float64) * np.asarray(k_luz, dtype=np.float64)
    return lineal_a_srgb(hombro(v) if suave else np.clip(v, 0.0, 1.0))


# ============================================================================= sombreado de los dos modos
def _col(v):
    """Escalar o array (...,) -> array (..., 1) para multiplicar por colores (..., 3)."""
    v = np.asarray(v, dtype=np.float64)
    return v[..., None] if v.ndim else v


def escena_ac(tx, ks_amb, ks_dif, n_l, ks_spec=0.0, spec_exp=1.0, n_h=0.0, ks_emis=0.0,
              sol=SOL_AC, amb=AMB_AC, distancia=None, niebla=NIEBLA_AC):
    """Valor HDR de AC en espacio GAMMA (ksPerPixel, como DarkMaterial.Lighting.Simple.fx de AcTools):
    tx*(ksAmbient*AMB + ksDiffuse*SOL*N.L*sombra + ksEmissive) + ksSpecular*N.H^EXP*SOL*N.L*sombra, con la niebla
    de Kunos lerp(color, FOG, blend*(1-exp(-d/dist))). tx = textura sRGB 0..1 tal cual. n_l ya incluye la sombra."""
    tx = np.asarray(tx, dtype=np.float64)
    luz_sol = np.asarray(sol, dtype=np.float64) * _col(np.maximum(n_l, 0.0))
    esc = tx * (_col(ks_amb) * np.asarray(amb, dtype=np.float64) + _col(ks_dif) * luz_sol + _col(ks_emis))
    esp = _col(ks_spec) * np.power(_col(np.maximum(n_h, 0.0)), _col(spec_exp))
    esc = esc + esp * luz_sol
    if distancia is not None and niebla is not None:
        col, blend, dist = niebla
        f = _col(blend * (1.0 - np.exp(-np.asarray(distancia, dtype=np.float64) / dist)))
        esc = esc * (1 - f) + np.asarray(col, dtype=np.float64) * f
    return esc


def pantalla_ac(escena, exposicion=EXPO_DISENO, sat=PP_SAT):
    """Escena HDR de AC -> pantalla sRGB 0..1 (saturacion del filtro + curva Yebis)."""
    return tonemap_ac(saturar(escena, sat) * exposicion)


_LCS_SOL = (np.asarray(K_BLENDER['suelo_sol']) - np.asarray(K_BLENDER['sombra_suelo'])) / COS_SUELO


def ambiente_lcs(nz):
    """Luz ambiente del modo lineal segun la normal: cielo (sombra de suelo) arriba, pared en sombra en vertical
    (cielo + rebote del suelo), mitad hacia abajo. Valores de K_BLENDER."""
    nz = _col(nz)
    pared, suelo = np.asarray(K_BLENDER['sombra_pared']), np.asarray(K_BLENDER['sombra_suelo'])
    return np.where(nz >= 0, pared + (suelo - pared) * nz, pared * (1.0 + 0.5 * nz))


def escena_lcs(tx, ks_amb, ks_dif, n_l, nz, ks_spec=0.0, spec_exp=1.0, n_h=0.0, ks_emis=0.0):
    """Valor lineal de CSP con espacio de color LINEAL: toLinear(tx*ks) = (tx*ks/0.5)^2.2 por termino, sol y cielo
    fisicos (los de Blender). Sin niebla (los estilos LCS la ponen a su gusto: ver el modo 'captura')."""
    tx = np.asarray(tx, dtype=np.float64)
    g, r = LCS_GAMMA, LCS_KS_REF
    alb_d = np.power(np.clip(tx * _col(ks_dif) / r, 0, None), g)
    alb_a = np.power(np.clip(tx * _col(ks_amb) / r, 0, None), g)
    luz = _LCS_SOL * _col(np.maximum(n_l, 0.0))
    lin = alb_d * luz + alb_a * ambiente_lcs(nz)
    esp = np.power(np.clip(_col(ks_spec), 0, None), g) * np.power(_col(np.maximum(n_h, 0.0)), _col(spec_exp))
    return lin + esp * luz + np.power(np.clip(tx * _col(ks_emis), 0, None), g) * 0.5


def pantalla_lcs(lin, exposicion):
    """Lineal -> pantalla sRGB 0..1 con ACES (aprox. de la conversion de los estilos LCS)."""
    return lineal_a_srgb(aces(np.asarray(lin, dtype=np.float64) * exposicion))


def pantalla_lcs_yebis(lin, exposicion):
    """Variante del modo lineal: lineal -> sRGB (pow 1/2.2) y despues la curva Yebis del filtro (saturacion
    0.95 + curva + gamma 1.2), como cuando CSP convierte a sRGB y pasa la imagen a YEBIS (wiki 'Linear color
    space': "By default CSP would do that step for you before sending image to YEBIS"). KY_LCS: gris -> gris."""
    x = np.power(np.maximum(np.asarray(lin, dtype=np.float64) * exposicion, 0.0), 1.0 / LCS_GAMMA) * KY_LCS
    return tonemap_ac(saturar(x, PP_SAT))


def autoexposicion_lcs(lum):
    """Autoexposicion del modo lineal: clave 0.18 sobre la media LOGARITMICA de la luminancia (la habitual en los
    motores con espacio lineal; el cielo pesa menos que con la media aritmetica)."""
    lum = np.asarray(lum, dtype=np.float64)
    return LCS_MEDIA / max(float(np.exp(np.mean(np.log(lum + 1e-4)))), 1e-6)


# variante Yebis del modo lineal: KY_LCS lleva un gris 0.18 a su sRGB; con E = 1 un gris de Blender sale igual
KY_LCS = float(tonemap_ac_inv(lineal_a_srgb(0.18))) / 0.18 ** (1.0 / LCS_GAMMA)
EXPO_LCSY_DISENO = 1.0
# exposicion de diseno del modo lineal: ACES(E * x) ~ sRGB de Blender en los medios tonos (x = 0.2 -> 0.19);
# las 9 vistas simuladas con autoexposicion dan 0.55-0.80 (simular_vistas.py)
EXPO_LCS_DISENO = 0.68
# v3: exposicion de los modos lineales EN EL AJUSTE. En los estilos lineales la autoexposicion del juego fija el nivel
# global (un factor comun de todas las texturas se compensa solo), asi que esos modos deberian decidir sobre todo
# colores y brillos relativos. La exposicion que hace eso del todo (nivel medio L* de las vistas lineales = el de
# Blender con las texturas calibradas, 03_blender/_rev/color_ac/expo_lcs.py) sube a medida que el ajuste oscurece las
# texturas: 0.69/1.01 en el primer paso y 0.91/1.33 en el punto fijo, donde el gamma mejora pero el Yebis y el tiempo
# nublado empeoran. Se usa la del primer paso, elegida con la simulacion de vistas (decisiones_v3.md: coste 18.37,
# frente a 18.47 en el punto fijo, 18.81 con la autoexposicion real 0.66 y 18.60 con lo que suponia la v2, 0.59/0.92,
# que dejaba el Yebis mas oscuro de lo previsto). _ANTES: la misma medida con el KN5 de antes (guarda de regresion).
EXPO_LCS_AJUSTE = {'lcs': 0.69, 'lcsy': 1.01}
EXPO_LCS_AJUSTE_ANTES = {'lcs': 0.54, 'lcsy': 0.80}

# ============================================================================= familias de material
# (ksAmbient, ksDiffuse, ksSpecular, ksSpecularEXP, ksEmissive). ksAmbient/ksDiffuse elegidos con
# 03_blender/_rev/color_ac/rejilla_ks.py (rejilla_ks.md, v3): para cada combinacion se recalibran TODAS las texturas y
# se simulan las 7 vistas de ajuste (y aparte las 3 de control) en cuatro modos: gamma de Kunos, lineal ACES, lineal
# sRGB + Yebis y la configuracion ESTIMADA del amigo (la unica anclada a su captura; pesos del coste 0.3/0.2/0.2/0.3).
#   * El minimo es plano y esta en cociente ksA/ksD < 1: 0.42/0.60 coste 18.34, 0.45/0.60 18.37, 0.48/0.60 18.47,
#     0.60/0.60 19.13, 0.50/0.50 19.71; cociente 1.25 (v2) 20.5-20.8. Con ambiente fuerte (la captura, tiempos nublados)
#     un ksAmbient bajo es lo que da volumen; el modo gamma de Kunos prefiere algo mas de ambiente (13.3 con 0.60/0.60
#     frente a 14.2 con 0.45/0.60).
#   * 0.45 / 0.60: dentro del 0.4-0.6 que pide CSP, cociente 0.75 ("keep them similar"), entre el 0.4/0.6 por defecto
#     de AcTools/ksEditor y el 0.45 de ambiente que ya llevaba el KN5; el brillo lo llevan las texturas.
# ksSpecular solo donde Blender muestra brillo (agua, cristal, metal, pintura; asfalto un brillo suave).
# 'techo' (textura sRGB maxima): roca 0.85 (con 0.90 la caliza de la montana-coche, casi siempre en sombra, subia hasta
# 230 para aclarar las sombras y con la bruma de la configuracion estimada del amigo empeoraba de 22.3 a 24.6; con 0.85
# queda 23.6 ahi y mejora en ACES: 12.7 -> 11.7).
# 'pesos' y 'margen' (solo asfalto): con los pesos generales el asfalto quedaba en gamma a 125-132 y calido (Blender
# 90-101 y frio) porque el modelo Yebis, donde el asfalto de antes ya salia bien (deltaE 5.1), no dejaba oscurecerlo.
# Con gamma 0.8 y 2.0 de margen en la guarda: gamma 16.1 -> 14.5 en sus pixeles (118,116,106), configuracion estimada
# 10.0 -> 8.3, Yebis 6.2 -> 7.3 (ANTES 5.1: +2.2, por debajo de una diferencia apenas perceptible). decisiones_v3.md.
# 'croma_lineal' (solo agua): el mar de Blender es casi
# todo reflejo del cielo, que ksPerPixel no tiene. Con el techo de croma lineal general (1.2) los modos lineales no
# dejaban oscurecer el rojo y el modo gamma lo dejaba palido (182,222,241 frente a 155,212,248 en la vista meta_puerto);
# con 1.4 se admite un mar algo mas saturado que en Blender en los lineales y en gamma sale 170,217,241
# (decisiones_v3.md: probados tambien pesos de modo 0.7 y 0.8 para el agua: el Yebis empeoraba 2.6-4 de deltaE).
FAMILIAS = {
    'asfalto':      {'props': (0.45, 0.60, 0.08, 20.0, 0.0), 'suelo': True, 'techo': 0.80,
                     'pesos': {'ac': 0.8, 'cap': 0.0, 'lcs': 0.1, 'lcsy': 0.1}, 'margen': 2.0},
    'pintura_vial': {'props': (0.45, 0.60, 0.06, 20.0, 0.0), 'suelo': True, 'techo': 0.92},
    'terreno':      {'props': (0.45, 0.60, 0.00, 1.0, 0.0), 'suelo': True, 'techo': 0.88},
    'agua':         {'props': (0.45, 0.60, 0.80, 250.0, 0.0), 'suelo': True, 'techo': 0.90,
                     'croma_lineal': 1.4},
    'roca':         {'props': (0.45, 0.60, 0.02, 8.0, 0.0), 'suelo': False, 'techo': 0.85},
    'edificio':     {'props': (0.45, 0.60, 0.03, 12.0, 0.0), 'suelo': False, 'techo': 0.92},
    'pintado':      {'props': (0.45, 0.60, 0.12, 40.0, 0.0), 'suelo': False, 'techo': 0.92},
    'metal':        {'props': (0.45, 0.60, 0.40, 60.0, 0.0), 'suelo': False, 'techo': 0.92},
    'cristal':      {'props': (0.45, 0.60, 0.60, 150.0, 0.0), 'suelo': False, 'techo': 0.85},
    'vegetacion':   {'props': (0.45, 0.60, 0.00, 1.0, 0.0), 'suelo': False, 'techo': 0.88},
    'luz':          {'props': (0.45, 0.60, 0.10, 40.0, 1.2), 'suelo': False, 'techo': 0.95},
}
SHADER_PROPS_ANTES = (('ksAmbient', 0.45), ('ksDiffuse', 0.55), ('ksSpecular', 0.15),
                      ('ksSpecularEXP', 24.0), ('ksEmissive', 0.0), ('ksAlphaRef', 0.0))
# caras de referencia del ajuste: (nombre, N.L*sombra, N.z)
GEOMETRIAS = (('suelo_sol', COS_SUELO, 1.0), ('pared_sol', COS_PARED, 0.0),
              ('sombra_pared', 0.0, 0.0), ('sombra_suelo', 0.0, 1.0))
PESOS = {True: (0.9, 0.03, 0.02, 0.05), False: (0.35, 0.35, 0.25, 0.05)}     # suelos (casi siempre al sol) / resto
# peso de cada modo de sombreado en el compromiso de la textura (gamma: AC sin CSP, Pure Gamma, Sol; lineal: LCS)
PESO_MODOS = {'ac': 0.6, 'cap': 0.0, 'lcs': 0.2, 'lcsy': 0.2}
MODOS_AJUSTE = ('ac', 'cap', 'lcs', 'lcsy')
# modos que no deciden el color (peso 0) pero si la guarda de regresion: la configuracion estimada del amigo no debe
# empeorar ningun material (la caliza de la montana-coche, sobre todo en sombra, subia de 22.3 a 24.7 en sus vistas)
GUARDA_SOLO = {'cap': 0.2}
PESO_REGRESION = 16.0    # guarda de regresion: peso (x el del modo) del deltaE que pase del de antes + MARGEN
MARGEN_REGRESION = 0.5
LCS_F_CROMA = 0.6        # exposicion relativa a la que tambien se comprueba la croma del modo lineal
PESO_TECHO_CROMA = 8.0    # peso del exceso de croma en el ajuste (casi un limite duro)
CROMA_MAX = 1.08         # croma en pantalla <= 1.08 x la de Blender (+2) en las caras con peso, modo gamma
CROMA_MAX_LINEAL = 1.20  # en los modos lineales: la curva ACES ya satura por si sola (ANTES, sin el terreno, 1.18 x
                         # Blender); con 1.08 el modo gamma y el lineal Yebis salian menos saturados que Blender
                         # (prueba en informe_color_ac.md: con 1.20 mejoran gamma y Yebis, ACES queda en 1.3)
# suelo de croma opcional: en las caras con peso, la croma en pantalla de cada modo no baja de CROMA_MIN x la de
# Blender. Probado en las vistas (03_blender/_rev/color_ac/rejilla_ks.md, nota): 0.85 sube la croma media a 0.95 x
# Blender pero empeora el deltaE gamma 1.4 y el ACES 1.0, asi que va desactivado (0). Lo del mar se arregla en su
# familia ('pesos' y 'croma_lineal').
CROMA_MIN = 0.0
PESO_SUELO_CROMA = 3.0
SUELO_TX = 0.03          # nada por debajo de sRGB 8: los negros no se aplastan

_REGLAS = (   # (familia, subcadenas del nombre en minusculas), en este orden
    ('vegetacion', ('mat_veg_tronco', 'mat_veg_pino', 'mat_veg_cip', 'mat_veg_enc', 'mat_veg_ol', 'mat_veg_pal',
                    'mat_veg_ad', 'mat_veg_fl', 'mat_veg_lav', 'mat_veg_ret', 'mat_veg_rom', 'mat_veg_pla',
                    'mat_veg_dat', 'mat_oli_', 'mcoche_veg', 'mcoche_tronco', 'ital_cipres', 'ital_olivo',
                    'ital_parra', 'ital_hierba_mata', 'ital_tronco', 'ital_uva', 'loews_palma', 'loews_seto',
                    'loews_flor', 'loews_coco', 'loews_tronco', 'calle_hojas', 'calle_flor', 'ital_flor',
                    'ppueblo_mata', 'yate_hoja')),
    ('luz', ('_luz', 'pantalla', 'tally')),
    ('agua', ('mat_agua', 'ital_agua', 'agua_piscina')),
    ('cristal', ('vidrio', 'cristal', 'ventana', 'lente', 'optica')),
    ('metal', ('cromo', 'acero', 'metal', 'hierro', 'forja', 'bronce', '_oro', 'dorado', 'cobre', 'chapa',
               'guardarrail', 'mastil', 'farol', 'poste', 'llanta', 'disco', 'rotor', 'noray', 'bolardo')),
    ('pintura_vial', ('marca', 'linea', 'piano', 'zigzag')),
    ('asfalto', ('asfalto', 'tunel_suelo', 'carretera', 'hormigon', 'suelo_box')),
    ('terreno', ('terreno', 'hierba', 'tierra', 'terraplen', 'paja')),
    ('roca', ('roca', 'caliza', 'mcoche_hueso', 'mcoche_hueco')),
    ('edificio', ('piedra', 'sillar', 'fachada', 'estuco', 'teja', 'cumbrera', 'albardilla', 'moldura',
                  'balaustr', 'dovela', 'clave', 'intrados', 'zocalo', 'muro', 'bordillo', 'acera', 'adoquin',
                  'mortero', 'escalera', 'plaza', 'repisa', 'borde', 'calzada', 'paseo', 'terraza', 'cupula',
                  'tejado', 'azotea', 'reloj', 'mat_casas_', 'mat_civico_', 'mat_casino_', 'mat_hotel_',
                  'mat_ayto_', 'mat_campanile_', 'mat_ital_', 'mat_mirador_', 'mat_puentes_', 'mat_ppueblo_',
                  'mat_acueducto', 'mat_penon_', 'mat_urb_')),
)


def familia(nombre):
    """Familia de un material por su nombre (ver _REGLAS); 'pintado' si no encaja en ninguna."""
    n = nombre.lower()
    if n.startswith('mat_casas_') and any(k in n for k in ('madera', 'persiana', 'toldo')):
        return 'pintado'
    for fam, claves in _REGLAS:
        if any(k in n for k in claves):
            return fam
    return 'pintado'


# ============================================================================= albedo real medido
# Muchos materiales se pintan en Blender con rampas/ruidos o texturas: su diffuse_color (lo unico que lee
# analizar_material) no es su color medio real. color_ac_albedo.json = media medida
# (03_blender/_rev/color_ac/medir_albedo.py) + el diffuse_color con el que se midio: si el material cambia despues
# en Blender la medida se ignora (nunca una obsoleta).
ALBEDO_JSON = os.path.join(AQUI, 'color_ac_albedo.json')
# albedo EFECTIVO de superficies cuyo aspecto en Blender es sobre todo reflejo del cielo (Fresnel), que
# ksPerPixel no tiene: asfalto (95-113 en los renders con albedo 0.035; ademas tiene objetivo medido en las vistas)
# y mar: sRGB^-1(155, 209, 242) (mar de capturas_avance) / K_BLENDER['suelo_sol'] por canal.
ALBEDO_EFECTIVO = {'MAT_asfalto': (0.070, 0.071, 0.076), 'MAT_agua': (0.199, 0.350, 0.386)}
_albedo_cache = {}


def _tabla_albedo():
    if 'tabla' not in _albedo_cache:
        try:
            with open(ALBEDO_JSON, encoding='utf-8') as f:
                _albedo_cache['tabla'] = json.load(f)
        except (OSError, ValueError):
            _albedo_cache['tabla'] = {'albedo': {}, 'diffuse_color': {}}
    return _albedo_cache['tabla']


def albedo_real(info):
    """(albedo lineal, fuente) del material: efectivo > medido (si sigue vigente) > color del writer."""
    nombre, color = info['name'], np.asarray(info['color'], dtype=np.float64)
    if nombre in ALBEDO_EFECTIVO:
        return np.array(ALBEDO_EFECTIVO[nombre], dtype=np.float64), 'efectivo (reflejo del cielo)'
    t = _tabla_albedo()
    if nombre in t.get('albedo', {}):
        ref = np.asarray(t.get('diffuse_color', {}).get(nombre, color), dtype=np.float64)
        if np.abs(ref - color).max() <= 0.02:
            return np.asarray(t['albedo'][nombre], dtype=np.float64), 'medido en Blender'
        return color, 'diffuse (medida obsoleta: el material cambio)'
    return color, 'color del material'


# aspecto REAL de cada material en las vistas de ajuste de Blender (03_blender/_rev/color_ac/medir_objetivos.py):
# color en pantalla por clase de cara. Igual que el albedo medido, se ignora si el color del material cambio.
OBJETIVOS_JSON = os.path.join(AQUI, 'color_ac_objetivos.json')


def objetivo_medido(info):
    """({clase: {'rgb', 'nl', 'nz', 'pixeles'}}, albedo en la escena) del material, o (None, None)."""
    if 'objetivos' not in _albedo_cache:
        try:
            with open(OBJETIVOS_JSON, encoding='utf-8') as f:
                _albedo_cache['objetivos'] = json.load(f).get('materiales', {})
        except (OSError, ValueError):
            _albedo_cache['objetivos'] = {}
    o = _albedo_cache['objetivos'].get(info['name'])
    if not o or np.abs(np.asarray(o['color_writer']) - np.asarray(info['color'], dtype=np.float64)).max() > 0.02:
        return None, None
    return o['clases'], o.get('albedo_escena')


# ============================================================================= roca del terreno
# En Blender MAT_terreno pinta ROCA donde la ladera es muy empinada o donde el atributo de vertice 'roca' (mascara del
# macizo, terreno_montana.py) lo pide, y HIERBA en el resto (construir_pista.py: mat_terreno() + _roca_terreno():
# talud = smoothstep(N.z + ruido, 0.50 -> 0.56), atributo = smoothstep('roca' + ruido, 0.47 -> 0.51) x
# (1 - smoothstep(N.z, 0.78 -> 0.86)), mascara = max de los dos). El KN5 lleva UN color por material: sin separar,
# las laderas de roca salian del verde de la hierba. separar_roca_terreno() (writer, dentro de Blender) pasa esas caras
# a un material propio MAT_terreno_roca con el mismo criterio (umbral en la mitad de cada smoothstep, sin el ruido),
# y calibrar_todos() le da el color de la roca de Blender. La escena .blend no se guarda: solo cambia el KN5.
ROCA_BASE = 'MAT_terreno'
ROCA_MAT = 'MAT_terreno_roca'
ROCA_NZ = 0.50            # talud (smoothstep 0.50..0.56 + ruido): 0.50 es el umbral que mejor reproduce la mascara
                          # de Blender en las 9 vistas (96.5 % de los pixeles de terreno iguales)
ROCA_ATR = 0.49           # atributo 'roca' > 0.49 (mitad de 0.47..0.51) ...
ROCA_NZ_LLANO = 0.82      # ... salvo en lo llano (mitad de 0.78..0.86), donde manda la hierba
ROCA_COLOR = (0.34, 0.27, 0.18)   # albedo lineal medio de la rama de roca (ROCA_rampa x tono); el objetivo real
                                  # de calibrar_todos es el aspecto medido de esas caras en las vistas
# objetos de suelo cuyas caras hacia abajo voltea exportar_ac.py (N.z < -0.05: cintas de arcen, aceras...): aqui se
# miran ya volteadas, asi el criterio da lo mismo sobre la escena de Blender que sobre la de export
SUELO_VOLTEADO = ("1ROAD", "1DIRT", "1KERB", "1GRASS", "2GRASS", "1PIT", "MARCA", "ACERA", "BORDILLO",
                  "LINEA", "ARCEN", "PIT", "TUNEL_suelo", "AGUA")


def mascara_roca(nz, roca=None):
    """Caras de roca (bool) por N.z mundo de la cara y media del atributo 'roca' de sus vertices (o None)."""
    nz = np.asarray(nz, dtype=np.float64)
    m = nz < ROCA_NZ
    if roca is not None:
        m = m | ((np.asarray(roca, dtype=np.float64) > ROCA_ATR) & (nz < ROCA_NZ_LLANO))
    return m


def datos_caras(ob):
    """Por poligono de un objeto de Blender: (con MAT_terreno, N.z mundo de la cara, media del atributo 'roca' de sus
    vertices o None)."""
    me = ob.data
    n = len(me.polygons)
    if n == 0:
        return np.zeros(0, bool), np.zeros(0), None
    pn = np.empty(n * 3, np.float32)
    me.polygons.foreach_get('normal', pn)
    m3 = np.array(ob.matrix_world.to_3x3(), dtype=np.float64)
    try:
        nw = pn.reshape(-1, 3).astype(np.float64) @ np.linalg.inv(m3)          # normales: inversa traspuesta (fila-vector)
    except np.linalg.LinAlgError:
        nw = pn.reshape(-1, 3).astype(np.float64) @ m3.T
    nz = nw[:, 2] / np.maximum(np.linalg.norm(nw, axis=1), 1e-12)
    if ob.name.startswith(SUELO_VOLTEADO):
        nz = np.where(nz < -0.05, -nz, nz)
    roca = None
    at = me.attributes.get('roca')
    if at is not None and at.domain == 'POINT' and at.data_type == 'FLOAT' and len(at.data) == len(me.vertices):
        v = np.empty(len(me.vertices), np.float32)
        at.data.foreach_get('value', v)
        lv = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get('vertex_index', lv)
        ls = np.empty(n, np.int32)
        lt = np.empty(n, np.int32)
        me.polygons.foreach_get('loop_start', ls)
        me.polygons.foreach_get('loop_total', lt)
        orden = np.argsort(ls)
        suma = np.zeros(n)
        suma[orden] = np.add.reduceat(v[lv].astype(np.float64), ls[orden])
        roca = suma / np.maximum(lt, 1)
    pm = np.empty(n, np.int32)
    me.polygons.foreach_get('material_index', pm)
    slots = [k for k, m in enumerate(me.materials) if m is not None and m.name == ROCA_BASE]
    return np.isin(pm, slots), nz, roca


def roca_caras(ob):
    """Mascara de roca por poligono de un objeto de Blender (solo caras con el material MAT_terreno)."""
    es_ter, nz, roca = datos_caras(ob)
    return es_ter & mascara_roca(nz, roca)


def separar_roca_terreno(objetos=None):
    """SOLO dentro de Blender (writer, antes de recopilar_materiales): crea MAT_terreno_roca (copia de MAT_terreno con
    diffuse_color = ROCA_COLOR) y le pasa las caras de roca de cada malla con MAT_terreno. No guarda el .blend.
    Devuelve {objeto: caras de roca}."""
    import bpy
    base = bpy.data.materials.get(ROCA_BASE)
    if base is None:
        return {}
    nuevo = bpy.data.materials.get(ROCA_MAT)
    if nuevo is None:
        nuevo = base.copy()
        nuevo.name = ROCA_MAT
    nuevo.diffuse_color = (ROCA_COLOR[0], ROCA_COLOR[1], ROCA_COLOR[2], 1.0)
    obs = objetos if objetos is not None else [o for o in bpy.data.objects if o.type == 'MESH' and any(
        m is not None and m.name == ROCA_BASE for m in o.data.materials)]
    out, hechas = {}, set()
    for ob in obs:
        me = ob.data
        if me.name in hechas or me.library is not None:
            continue
        mask = roca_caras(ob)
        if not mask.any():
            continue
        hechas.add(me.name)
        if not any(m is not None and m.name == ROCA_MAT for m in me.materials):
            me.materials.append(nuevo)
        k = next(i for i, m in enumerate(me.materials) if m is not None and m.name == ROCA_MAT)
        pm = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get('material_index', pm)
        pm[mask] = k
        me.polygons.foreach_set('material_index', pm)
        me.update()
        out[ob.name] = int(mask.sum())
    return out


# ============================================================================= calibracion
_NL_G = np.array([g[1] for g in GEOMETRIAS])
_NZ_G = np.array([g[2] for g in GEOMETRIAS])
_AMB_LCS_G = ambiente_lcs(_NZ_G)                                    # (4, 3)
_K_G = np.array([K_BLENDER[g[0]] for g in GEOMETRIAS])             # (4, 3)
# modo 'cap' (configuracion estimada del amigo): gamma, sol blanco de la luminancia del de 3_clear, ambiente x4.4,
# exposicion 0.2 x brillo 0.5, saturacion 1.0
SOL_CAP = np.full(3, float(luminancia(SOL_AC)))
AMB_CAP = AMB_AC * CAP_AMBIENTE
EXPO_CAP = EXPO_MIN * CAP_BRILLO
MODOS_GAMMA = ('ac', 'cap')          # exposicion fija (la autoexposicion se queda en su minimo): sin escala_lcs


def _ideal_gamma(objetivo, ka, kd, nl, kem, sol, amb, expo, sat):
    """Textura sRGB que da EXACTAMENTE `objetivo` (pantalla, por canal) en un modo gamma de exposicion fija."""
    esc = saturar(tonemap_ac_inv(objetivo), 1.0 / sat) / expo
    return esc / (ka * amb + kd * sol * nl + kem)


def _ideal_ac(objetivo, ka, kd, nl, kem=0.0):
    return _ideal_gamma(objetivo, ka, kd, nl, kem, SOL_AC, AMB_AC, EXPO_DISENO, PP_SAT)


def _lin_a_tx(lin, ka, kd, nl, amb):
    """Modo lineal: (tx*kd/0.5)^2.2*SOL*N.L + (tx*ka/0.5)^2.2*AMB = lin  ->  tx."""
    g, r = LCS_GAMMA, LCS_KS_REF
    den = (kd / r) ** g * _LCS_SOL * nl + (ka / r) ** g * amb
    return np.power(np.maximum(lin / den, 1e-9), 1.0 / g)


def _ideales(objetivo, ka, kd, nl, amb, kem=0.0):
    """Textura exacta por canal en cada modo: {'ac', 'cap', 'lcs', 'lcsy'} (sin escalar; ksEmissive en gamma)."""
    x_y = np.maximum(saturar(tonemap_ac_inv(objetivo), 1.0 / PP_SAT), 0.0) / KY_LCS
    return {'ac': _ideal_ac(objetivo, ka, kd, nl, kem),
            'cap': _ideal_gamma(objetivo, ka, kd, nl, kem, SOL_CAP, AMB_CAP, EXPO_CAP, CAP_SAT),
            'lcs': _lin_a_tx(aces_inv(srgb_a_lineal(objetivo)) / EXPO_LCS_DISENO, ka, kd, nl, amb),
            'lcsy': _lin_a_tx(np.power(x_y, LCS_GAMMA) / EXPO_LCSY_DISENO, ka, kd, nl, amb)}


_escalas = {}


def escala_lcs(ka, kd, expo=None):
    """Factor por modo lineal tal que su exposicion en el ajuste (EXPO_*_DISENO / f^2.2) sea `expo`[modo] (por defecto
    EXPO_LCS_AJUSTE; EXPO_LCS_AJUSTE_ANTES para el KN5 de antes). Los modos gamma: 1.
    {'ac': 1, 'cap': 1, 'lcs': f, 'lcsy': f'}. (ka, kd: se conservan por compatibilidad; ya no influyen.)"""
    expo = EXPO_LCS_AJUSTE if expo is None else expo
    clave = (ka, kd, tuple(sorted(expo.items())))
    if clave not in _escalas:
        dis = {'lcs': EXPO_LCS_DISENO, 'lcsy': EXPO_LCSY_DISENO}
        _escalas[clave] = {m: (1.0 if m in MODOS_GAMMA else float((dis[m] / expo[m]) ** (1.0 / LCS_GAMMA)))
                           for m in MODOS_AJUSTE}
    return _escalas[clave]


def _pantallas_lote(tx, ka, kd, e, nl=None, amb=None, f_expo=1.0, kem=None):
    """Pantallas sRGB (M, 4, 3) en las 4 caras de referencia y cada modo {'ac', 'cap', 'lcs', 'lcsy'}. tx (M,3);
    ka, kd (M,); e {modo: (M,)} (escala_lcs); nl (M,4) y amb (M,4,3) si las caras son las medidas."""
    t = np.asarray(tx, dtype=np.float64)[:, None, :]
    A, D = ka[:, None, None], kd[:, None, None]
    E = 0.0 if kem is None else kem[:, None, None]
    nl = _NL_G[None, :, None] if nl is None else nl[..., None]
    amb = _AMB_LCS_G[None] if amb is None else amb
    g, r = LCS_GAMMA, LCS_KS_REF
    lin = np.power(t * D / r, g) * _LCS_SOL * nl + np.power(t * A / r, g) * amb + np.power(t * E, g) * 0.5
    return {'ac': tonemap_ac(saturar(t * (A * AMB_AC + D * SOL_AC * nl + E), PP_SAT) * EXPO_DISENO),
            'cap': tonemap_ac(saturar(t * (A * AMB_CAP + D * SOL_CAP * nl + E), CAP_SAT) * EXPO_CAP),
            'lcs': pantalla_lcs(lin, f_expo * EXPO_LCS_DISENO / e['lcs'][:, None, None] ** g),
            'lcsy': pantalla_lcs_yebis(lin, f_expo * EXPO_LCSY_DISENO / e['lcsy'][:, None, None] ** g)}


def _de_caras(pan, l_obj, wg):
    """deltaE Lab medio (ponderado por cara) frente al objetivo: (M,)."""
    return (np.linalg.norm(lab(pan) - l_obj, axis=-1) * wg).sum(-1)


def pesos_modos(fams):
    """Peso de cada modo por material {modo: (M,)}: PESO_MODOS o el de su familia (FAMILIAS[f]['pesos'])."""
    return {m: np.array([FAMILIAS[f].get('pesos', PESO_MODOS).get(m, 0.0) for f in fams], dtype=np.float64)
            for m in MODOS_AJUSTE}


def _residuos(u, ka, kd, e, l_obj, wg, c_lim, techo, nl, amb, kem, de_antes, c_min=None, pm=None, c_lim_lin=None):
    """Residuos del ajuste (M, K): deltaE Lab ponderado frente a Blender en cada cara y modo, exceso de croma en
    la cara al sol principal (techo de croma; en los modos lineales tambien con LCS_F_CROMA de exposicion, porque
    su autoexposicion varia por vista), GUARDA DE REGRESION (en ningun modo el material puede quedar peor que con el
    KN5 de antes, `de_antes`, mas MARGEN_REGRESION) y penalizaciones de techo/suelo de la textura."""
    tx = np.exp(u)
    pan = _pantallas_lote(tx, ka, kd, e, nl, amb, kem=kem)
    osc = _pantallas_lote(tx, ka, kd, e, nl, amb, LCS_F_CROMA, kem)
    res = []
    for m in MODOS_AJUSTE:
        wm = pm[m] if pm is not None else np.full(len(tx), PESO_MODOS.get(m, 0.0))
        if not (wm > 0).any():
            if m in GUARDA_SOLO and de_antes is not None and PESO_REGRESION > 0:   # no decide el color, solo la guarda
                exceso = np.maximum(_de_caras(pan[m], l_obj, wg) - de_antes[m] - MARGEN_REGRESION, 0.0)
                res.append((np.sqrt(PESO_REGRESION * GUARDA_SOLO[m]) * exceso)[:, None])
            continue
        c = croma(pan[m]) if m in MODOS_GAMMA else np.maximum(croma(pan[m]), croma(osc[m]))
        d = (lab(pan[m]) - l_obj) * np.sqrt(wm[:, None] * wg)[..., None]
        lim = c_lim if m in MODOS_GAMMA else (c_lim * (CROMA_MAX_LINEAL / CROMA_MAX) if c_lim_lin is None else c_lim_lin)
        res += [d.reshape(len(tx), -1), np.maximum(c - lim, 0.0) * PESO_TECHO_CROMA * (wm > 0)[:, None]]
        if c_min is not None:      # suelo de croma: nada sale mas lavado que CROMA_MIN x Blender (en la pantalla normal)
            res.append(np.maximum(c_min - croma(pan[m]), 0.0) * np.sqrt(wm)[:, None] * PESO_SUELO_CROMA)
        if de_antes is not None and PESO_REGRESION > 0:
            exceso = np.maximum(_de_caras(pan[m], l_obj, wg) - de_antes[m] - MARGEN_REGRESION, 0.0)
            res.append((np.sqrt(PESO_REGRESION * wm) * exceso)[:, None])
    res.append(30.0 * np.maximum(tx.max(-1) - techo, 0.0)[:, None] * 255)
    res.append(30.0 * np.maximum(SUELO_TX - tx, 0.0) * 255)
    return np.concatenate(res, -1)


def ajustar_texturas(albedos, fams, medidos=None, iteraciones=25, con_objetivo=False, antes=None):
    """Texturas sRGB 0..1 (M, 3) para albedos lineales de Blender (M, 3) y sus familias (lote: todos a la vez).
    `medidos` (opcional, por material): {clase: {'rgb', 'nl', 'nz', 'pixeles'}} = aspecto REAL del material en las
    vistas de Blender (color_ac_objetivos.json); las clases que faltan se calculan con albedo x luz de Blender.
    `antes` (opcional, (M, 3)): textura sRGB del KN5 de antes, para la guarda de regresion.
    1. Por cada cara de referencia y modo, la textura EXACTA por canal (la que da en pantalla lo mismo que Blender,
       con la luz de AC por canal); media geometrica ponderada = punto de partida.
    2. Levenberg-Marquardt en log(textura) minimizando el deltaE Lab ponderado (caras x modos, PESO_MODOS) con
       techo de croma (en la cara al sol principal la croma no pasa de CROMA_MAX x la de Blender (+2) en ningun
       modo: nada sale mas saturado que el render ni cambia de tono) y guarda de regresion por modo.
    3. Techo de la familia (escalando los 3 canales: conserva el tono) y suelo SUELO_TX.
    Con `con_objetivo` devuelve tambien el objetivo (M, 4, 3) y el N.L (M, 4) de cada cara (para el informe)."""
    a = np.asarray(albedos, dtype=np.float64).reshape(-1, 3)
    M = len(a)
    pr = np.array([FAMILIAS[f]['props'] for f in fams], dtype=np.float64).reshape(M, 5)
    ka, kd, kem = pr[:, 0], pr[:, 1], pr[:, 4]
    esc = [escala_lcs(float(x), float(y)) for x, y in zip(ka, kd)]
    e = {m: np.array([s[m] for s in esc]) for m in MODOS_AJUSTE}
    techo = np.array([FAMILIAS[f]['techo'] for f in fams], dtype=np.float64)
    wg = np.array([PESOS[FAMILIAS[f]['suelo']] for f in fams], dtype=np.float64)
    wg = wg / wg.sum(-1, keepdims=True)
    obj = pantalla_blender(a[:, None, :], _K_G[None])                 # (M, 4, 3)
    nl_m, nz_m = np.tile(_NL_G, (M, 1)), np.tile(_NZ_G, (M, 1))
    frac = np.zeros((M, len(GEOMETRIAS)))
    for k, med in enumerate(medidos or ()):
        for j, (g, _, _) in enumerate(GEOMETRIAS):
            if med and g in med:
                obj[k, j] = med[g]['rgb']
                nl_m[k, j], nz_m[k, j], frac[k, j] = med[g]['nl'], med[g]['nz'], med[g]['pixeles']
    hay = frac.sum(-1) > 0
    wg[hay] = 0.5 * wg[hay] + 0.5 * frac[hay] / frac[hay].sum(-1, keepdims=True)
    amb = ambiente_lcs(nz_m)                                         # (M, 4, 3)
    l_obj = lab(obj)
    # techo de croma en la cara al sol PRINCIPAL y en las caras con peso >= 0.15 (las sombras incluidas: con poca
    # luz la curva ACES del modo lineal satura mas); no en caras de poco peso: en el terreno, p. ej., la 'pared al
    # sol' es roca gris y la textura (verde) no debe desaturarse por ella
    c_lim = CROMA_MAX * croma(obj) + 2.0
    activa = wg >= 0.15
    activa[np.arange(M), np.argmax(wg[:, :2], -1)] = True
    c_lim_lin = np.array([FAMILIAS[f].get('croma_lineal', CROMA_MAX_LINEAL) for f in fams])[:, None] * croma(obj) + 2.0
    c_lim[~activa] = 1e9
    c_lim_lin[~activa] = 1e9
    c_min = np.where(activa, CROMA_MIN * croma(obj), 0.0)
    de_antes = None
    if antes is not None:      # deltaE de cada modo con la textura y las props del KN5 de antes
        p0 = dict(SHADER_PROPS_ANTES)
        ka0, kd0 = np.full(M, p0['ksAmbient']), np.full(M, p0['ksDiffuse'])
        e0 = escala_lcs(p0['ksAmbient'], p0['ksDiffuse'], EXPO_LCS_AJUSTE_ANTES)
        pan0 = _pantallas_lote(np.asarray(antes, dtype=np.float64).reshape(M, 3), ka0, kd0,
                               {m: np.full(M, e0[m]) for m in MODOS_AJUSTE}, nl_m, amb, kem=np.zeros(M))
        extra = np.array([FAMILIAS[f].get('margen', MARGEN_REGRESION) - MARGEN_REGRESION for f in fams])   # por familia
        de_antes = {m: _de_caras(pan0[m], l_obj, wg) + extra for m in MODOS_AJUSTE}
    ide = _ideales(obj, ka[:, None, None], kd[:, None, None], nl_m[..., None], amb, kem[:, None, None])
    pm = pesos_modos(fams)
    usados = [m for m in MODOS_AJUSTE if (pm[m] > 0).any()]
    logs = np.concatenate([np.log(np.maximum(ide[m] * e[m][:, None, None], 1e-5)) for m in usados], 1)
    w = np.concatenate([pm[m][:, None] * wg for m in usados], -1)[..., None]
    u = (logs * w).sum(1) / np.maximum(w.sum(1), 1e-9)
    u = np.clip(u, np.log(SUELO_TX), np.log(techo)[:, None])
    args = (ka, kd, e, l_obj, wg, c_lim, techo, nl_m, amb, kem, de_antes, c_min, pm, c_lim_lin)
    R = _residuos(u, *args)
    coste = (R ** 2).sum(-1)
    lam = np.full(M, 1e-2)
    h = 1e-4
    for _ in range(iteraciones):
        J = np.stack([(_residuos(u + h * np.eye(3)[k], *args) - R) / h for k in range(3)], -1)
        jtj = np.einsum('mki,mkj->mij', J, J)
        gr = np.einsum('mki,mk->mi', J, R)
        diag = np.einsum('mii->mi', jtj)
        Amat = jtj + (lam[:, None] * (diag + 1e-3))[:, :, None] * np.eye(3)[None]
        du = np.clip(-np.linalg.solve(Amat, gr[..., None])[..., 0], -0.5, 0.5)
        Rn = _residuos(u + du, *args)
        cn = (Rn ** 2).sum(-1)
        mejor = cn < coste
        u = np.where(mejor[:, None], u + du, u)
        R = np.where(mejor[:, None], Rn, R)
        coste = np.where(mejor, cn, coste)
        lam = np.where(mejor, lam * 0.3, lam * 4.0)
    tx = np.exp(u)
    m = tx.max(-1)
    tx = np.maximum(tx * np.minimum(1.0, techo / np.maximum(m, 1e-9))[:, None], SUELO_TX)
    return (tx, obj, nl_m) if con_objetivo else tx

def ajustar_textura(albedo, fam, medido=None):
    return ajustar_texturas([albedo], [fam], [medido])[0]


def props_familia(fam):
    ka, kd, ks, ke, kem = FAMILIAS[fam]['props']
    return (('ksAmbient', ka), ('ksDiffuse', kd), ('ksSpecular', ks), ('ksSpecularEXP', ke),
            ('ksEmissive', kem), ('ksAlphaRef', 0.0))


def _aplicar(info, a, fuente, fam, tx, obj=None, nl=None):
    info['color_original'] = tuple(float(c) for c in info['color'])
    info['albedo_ac'] = tuple(float(c) for c in a)
    info['albedo_fuente'] = fuente
    info['familia'] = fam
    info['tx_ac'] = tuple(float(c) for c in tx)
    info['color'] = tuple(float(c) for c in srgb_a_lineal(tx))
    info['props_ac'] = props_familia(fam)
    if obj is not None:
        info['objetivo_ac'] = [[round(float(c), 4) for c in f] for f in obj]
        info['nl_ac'] = [round(float(v), 3) for v in nl]
    info['color_ac'] = VERSION
    return info


def calibrar_todos(infos):
    """Recalibra para AC una lista de infos de kn5_writer_opt.analizar_material() (todos a la vez, rapido;
    idempotente). Cambia info['color'] (lineal: el writer lo pasa a sRGB y, si hay imagen, tinta el patron para
    que su media lineal sea este color) y anade 'props_ac' (lista para escribir como SHADER_PROPS), 'familia',
    'albedo_ac', 'albedo_fuente', 'color_original' y 'tx_ac' (textura sRGB media resultante). Devuelve la lista."""
    pend = [i for i in infos if not i.get('color_ac')]
    if pend:
        datos = [albedo_real(i) for i in pend]
        meds = [objetivo_medido(i) for i in pend]
        datos = [(np.asarray(m[1]), 'aspecto medido en las vistas de Blender')
                 if m[0] and m[1] is not None and not fu.startswith('efectivo') else (a, fu)
                 for (a, fu), m in zip(datos, meds)]
        fams = [familia(i['name']) for i in pend]
        # textura del KN5 de antes (guarda de regresion): MAT_terreno_roca no existia, sus caras eran MAT_terreno
        base = next((i['color'] for i in infos if i['name'] == ROCA_BASE), None)
        antes = [lineal_a_srgb(base if (i['name'] == ROCA_MAT and base is not None) else i['color']) for i in pend]
        txs, objs, nls = ajustar_texturas([d[0] for d in datos], fams, [m[0] for m in meds], con_objetivo=True,
                                          antes=antes)
        for i, (a, fuente), fam, tx, ob, nl in zip(pend, datos, fams, txs, objs, nls):
            _aplicar(i, a, fuente, fam, tx, ob, nl)
    return infos


def calibrar(info):
    """Un solo material (mismo resultado que calibrar_todos)."""
    return calibrar_todos([info])[0]


# ============================================================================= informe
def _sat(c):
    c = np.asarray(c, dtype=np.float64)
    return float((c.max() - c.min()) / max(c.max(), 1e-6))


def simular_material(info):
    """Pantalla (0..255) en las 4 caras de referencia: Blender (objetivo: el aspecto medido en las vistas o albedo x
    luz) y AC gamma antes / despues (exposicion 0.2). Los modos lineales se comparan en las vistas
    (03_blender/_rev/color_ac/simular_vistas.py), porque su autoexposicion depende de toda la escena."""
    tx_a = lineal_a_srgb(info.get('color_original', info['color']))
    a = np.asarray(info.get('albedo_ac', info['color']), dtype=np.float64)
    tx_d = np.asarray(info.get('tx_ac', tx_a), dtype=np.float64)
    obj = np.asarray(info['objetivo_ac']) if 'objetivo_ac' in info else pantalla_blender(a[None], _K_G)
    nl = np.asarray(info.get('nl_ac', _NL_G), dtype=np.float64)[None]
    out = {'blender': obj * 255.0}
    pd = dict(info.get('props_ac', SHADER_PROPS_ANTES))
    for et, tx, pp in (('antes', tx_a, dict(SHADER_PROPS_ANTES)), ('despues', tx_d, pd)):
        ka, kd, kem = np.array([pp['ksAmbient']]), np.array([pp['ksDiffuse']]), np.array([pp['ksEmissive']])
        e = {m: np.ones(1) for m in MODOS_AJUSTE}
        out['ac_' + et] = _pantallas_lote(tx[None], ka, kd, e, nl, kem=kem)['ac'][0] * 255.0
    return out


def informe(infos, pesos=None):
    """Antes/despues por familia: textura media (sRGB 0-255), su luminancia y saturacion, lo que muestra AC
    (modelo gamma) en suelo al sol / pared al sol / pared en sombra frente al render de Blender, y el deltaE Lab
    medio frente a Blender. `pesos` opcional {material: caras} (media por superficie). Los modos lineales se
    comparan en las vistas (simular_vistas.py)."""
    fams = {}
    for i in infos:
        if 'familia' in i:
            fams.setdefault(i['familia'], []).append(i)
    rep = {'version': VERSION, 'exposicion_diseno': EXPO_DISENO, 'peso_modos': PESO_MODOS, 'familias': {},
           'fuentes': {}}
    for i in infos:          # de donde sale el objetivo de cada material (medido en las vistas, albedo, etc.)
        if 'albedo_fuente' in i:
            rep['fuentes'][i['albedo_fuente']] = rep['fuentes'].get(i['albedo_fuente'], 0) + 1
    for fam, lst in sorted(fams.items()):
        w = np.array([float((pesos or {}).get(i['name'], 1.0)) for i in lst])
        w = w / w.sum()
        tx_a = np.array([lineal_a_srgb(i['color_original']) for i in lst])
        tx_d = np.array([i['tx_ac'] for i in lst])
        sims = [simular_material(i) for i in lst]
        f = {'n': len(lst), 'props': dict(props_familia(fam)),
             'textura_antes': (w @ tx_a * 255).round().astype(int).tolist(),
             'textura_despues': (w @ tx_d * 255).round().astype(int).tolist(),
             'lum_textura_antes': round(float(w @ luminancia(tx_a)) * 255, 1),
             'lum_textura_despues': round(float(w @ luminancia(tx_d)) * 255, 1),
             'sat_antes': round(float(w @ np.array([_sat(t) for t in tx_a])), 3),
             'sat_despues': round(float(w @ np.array([_sat(t) for t in tx_d])), 3)}
        for k, g in enumerate(('suelo_sol', 'pared_sol', 'sombra_pared')):
            for et in ('blender', 'ac_antes', 'ac_despues'):
                f['%s_%s' % (g, et)] = (w @ np.array([s[et][k] for s in sims])).round().astype(int).tolist()
        for et in ('ac_antes', 'ac_despues'):
            de = [float(np.mean(np.linalg.norm(lab(s[et] / 255) - lab(s['blender'] / 255), axis=-1))) for s in sims]
            f['deltaE_' + et] = round(float(w @ np.array(de)), 1)
        rep['familias'][fam] = f
    return rep


def informe_texto(rep):
    """Tabla markdown del informe."""
    filas = ['| familia | n | ksA/ksD/ksS/exp | textura antes -> despues (sRGB) | AC suelo al sol antes / despues / '
             'Blender | AC pared al sol antes / despues / Blender | AC pared en sombra antes / despues / Blender | '
             'dE gamma antes -> despues |', '|' + '---|' * 8]
    for fam, f in rep['familias'].items():
        p = f['props']
        filas.append('| %s | %d | %.2f/%.2f/%.2f/%g | %s -> %s | %s / %s / %s | %s / %s / %s | %s / %s / %s | '
                     '%.1f -> %.1f |' % (
                         fam, f['n'], p['ksAmbient'], p['ksDiffuse'], p['ksSpecular'], p['ksSpecularEXP'],
                         f['textura_antes'], f['textura_despues'],
                         f['suelo_sol_ac_antes'], f['suelo_sol_ac_despues'], f['suelo_sol_blender'],
                         f['pared_sol_ac_antes'], f['pared_sol_ac_despues'], f['pared_sol_blender'],
                         f['sombra_pared_ac_antes'], f['sombra_pared_ac_despues'], f['sombra_pared_blender'],
                         f['deltaE_ac_antes'], f['deltaE_ac_despues']))
    return '\n'.join(filas)


# ============================================================================= CSP: extension/ext_config.ini
EXT_ORIGEN = os.path.join(AQUI, 'extension', 'ext_config.ini')
EXT_CONFIG = """; extension/ext_config.ini - Porto Corsa. Generado por 04_export/color_ac.py (%(version)s).
; Solo lo lee Custom Shaders Patch (CSP): sin CSP, AC ignora la carpeta extension/ y nada cambia.
; Los colores y ksAmbient/ksDiffuse ya van calibrados dentro del KN5 (validos con y sin CSP); aqui solo va
; lo que es propio de CSP. Claves: wiki de CSP 'Tracks - General options'. Se puede editar a mano:
; empaquetar.py copia este fichero tal cual y solo lo genera si no existe.

[ABOUT]
AUTHOR = Arnau & Claude
VERSION = 1.1
DATE_RELEASE = 2026-10-04
NOTES = Porto Corsa (Cars 2). Iluminacion de pista para CSP.

[BASIC]
; 0 (valor de la wiki): si CSP trae otra configuracion para esta pista tambien se aplica
IGNORE_OTHER_CONFIGS = 0
SUPPORTS_WIND = 1

[LIGHTING]
; luces dinamicas (faros, luces de CSP) sobre la pista y sobre los coches: 1 = sin cambio
LIT_MULT = 1
CAR_LIGHTS_LIT_MULT = 1
; brillo especular de la pista: 1 = sin cambio (los ksSpecular del KN5 ya son bajos, ver color_ac.FAMILIAS)
SPECULAR_MULT = 1
; TRACK_AMBIENT_GROUND_MULT no se define a proposito: la wiki dice "only define it if needed!" y en la
; simulacion de la v1 un 0.35 dejaba las caras en sombra muy por debajo de Blender.
%(agua)s
; PALANCA (%(estado)s): si con CSP el circuito se sigue viendo plano y claro (estilos de WeatherFX o tiempos con mucho
; ambiente, como parece en la captura del amigo), ACTIVE = 1 baja el ambiente de todo el circuito sin regenerar el
; KN5 (el KN5 lleva ksAmbient 0.45 / ksDiffuse 0.60). Simulacion (03_blender/_rev/color_ac/palanca_csp.json): con la
; configuracion estimada del amigo deltaE 19.2 -> 16.8 y con la otra hipotesis (nubes) 16.1 -> 14.1, pero con un estilo
; lineal 12.8 -> 14.3. Sin CSP no cambia nada.
[MATERIAL_ADJUSTMENT_0]
ACTIVE = %(activa)d
MATERIALS = MAT_?
KEY_0 = ksDiffuse
VALUE_0 = 0.55
KEY_1 = ksAmbient
VALUE_1 = 0.30
DESCRIPTION = palanca de ambiente para CSP
"""
EXT_AGUA = """
; agua de CSP (reflejos y olas) en el mar; sin CSP sigue el ksPerPixel calibrado del KN5
[INCLUDE: common/materials_track.ini]

[Material_Water]
Materials = %s
Type = SEA
"""
# Por defecto NO se activa: el shader de agua de CSP toma sus normales de olas por las UV de la malla
# (materials_track.ini: UseRecommendedTextures) y nuestra malla AGUA es un quad de 4 vertices y ~20 km con UV 0..1:
# las olas saldrian estiradas (no comprobado en el juego). Se activa con --agua cuando la malla tenga UV en metros.
EXT_SIN_AGUA = """
; agua de CSP desactivada a proposito: su shader toma las olas de las UV de la malla y el mar (malla AGUA) es un quad
; de ~20 km con UV 0..1. Para probarla: python 04_export/color_ac.py --ext-config <ruta> --sobrescribir --agua
"""


def generar_ext_config(ruta=EXT_ORIGEN, agua=False, materiales_agua=('MAT_agua',), palanca=False,
                       sobrescribir=False):
    """Escribe extension/ext_config.ini para CSP en `ruta` (crea la carpeta) y devuelve el texto.
    Si el fichero ya existe y no se pide `sobrescribir`, NO lo toca (puede estar ajustado a mano) y devuelve
    el texto que tiene."""
    if os.path.exists(ruta) and not sobrescribir:
        with open(ruta, encoding='utf-8') as f:
            return f.read()
    txt = EXT_CONFIG % {'version': VERSION, 'activa': 1 if palanca else 0,
                        'estado': 'activada' if palanca else 'desactivada',
                        'agua': (EXT_AGUA % ', '.join(materiales_agua)) if agua else EXT_SIN_AGUA}
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(txt)
    return txt


def copiar_ext_config(dir_pista, origen=EXT_ORIGEN):
    """Para empaquetar.py: copia `origen` (04_export/extension/ext_config.ini) a <dir_pista>/extension/ TAL CUAL.
    Solo si `origen` no existe lo genera con los valores por defecto. Devuelve la ruta copiada."""
    if not os.path.exists(origen):
        generar_ext_config(origen)
    dst = os.path.join(dir_pista, 'extension', 'ext_config.ini')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(origen, dst)
    return dst


# ============================================================================= linea de ordenes
def _infos_de_volcado(ruta_json):
    """infos minimos (como analizar_material) desde materiales.json de volcar_materiales.py."""
    d = json.load(open(ruta_json, encoding='utf-8'))
    infos = [{'name': m['name'], 'color': tuple(m['color']), 'alpha': m.get('alpha', 1.0), 'img': m.get('img')}
             for m in d['materiales']]
    caras = {m['name']: m.get('caras', 1) for m in d['materiales']}
    if ROCA_BASE in caras and ROCA_MAT not in caras:     # el material que crea separar_roca_terreno() en el writer
        infos.append({'name': ROCA_MAT, 'color': ROCA_COLOR, 'alpha': 1.0, 'img': None})
        caras[ROCA_MAT] = max(1, int(0.04 * caras[ROCA_BASE]))   # ~4 % de las caras del terreno son roca
    infos.append({'name': 'MAT_default', 'color': (0.5, 0.5, 0.5), 'alpha': 1.0, 'img': None})
    return infos, caras


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == '--ext-config':
        generar_ext_config(args[1], agua='--agua' in args, palanca='--palanca' in args,
                           sobrescribir='--sobrescribir' in args)
        print('OK ext_config ->', args[1])
    elif len(args) >= 2 and args[0] == '--informe':
        infos, caras = _infos_de_volcado(args[1])
        calibrar_todos(infos)
        rep = informe(infos, caras)
        print(informe_texto(rep))
        if len(args) >= 3:
            json.dump({'informe': rep, 'materiales': [{k: v for k, v in i.items() if k != 'img'} for i in infos]},
                      open(args[2], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    else:
        print('uso: python color_ac.py --ext-config <ruta.ini> [--sobrescribir] [--agua] [--palanca]\n'
              '       python color_ac.py --informe <materiales.json> [salida.json]')
