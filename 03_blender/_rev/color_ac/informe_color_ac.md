# Informe color_ac v3: antes / despues

Generado por `informe_vistas.py` a partir de la simulacion (`render_ac.py` sobre `escena_color.blend` -> `simular_vistas.py`). deltaE = diferencia CIE76 en Lab frente al render de Blender (media por pixel, sin cielo); croma y contraste (desviacion de luminancia) como cociente frente a Blender (1 = igual).

Vistas de AJUSTE (con ellas se eligio todo): meta_tunel, captura, pueblo, tierra, casino, piloto_s300, meta_puerto. Vistas de CONTROL (no se usaron para nada): bajada, puente, piloto_s2900.

Valores elegidos: ksAmbient 0.45 / ksDiffuse 0.60 en todas las familias; caras de roca del terreno -> MAT_terreno_roca; exposicion de los modos lineales en el ajuste {'lcs': 0.69, 'lcsy': 1.01} (autoexposicion real de las vistas: antes 0.54, despues 0.69).

## 1. Resumen por modo de sombreado

| modo | grupo | deltaE antes -> despues | croma/Blender antes -> despues | contraste/Blender antes -> despues |
|---|---|---|---|---|
| AC sin CSP / CSP gamma (3_clear) | ajuste | 25.6 -> 14.2 | 0.73 -> 0.89 | 1.44 -> 1.13 |
| AC sin CSP / CSP gamma (3_clear) | control | 24.4 -> 13.7 | 0.88 -> 0.93 | 1.16 -> 1.10 |
| CSP lineal, curva ACES | ajuste | 19.5 -> 12.7 | 0.93 -> 1.18 | 1.25 -> 1.17 |
| CSP lineal, curva ACES | control | 17.8 -> 12.3 | 1.02 -> 1.12 | 1.15 -> 1.18 |
| CSP lineal, sRGB + Yebis | ajuste | 20.2 -> 14.8 | 0.71 -> 0.86 | 0.96 -> 0.91 |
| CSP lineal, sRGB + Yebis | control | 19.8 -> 17.6 | 0.77 -> 0.89 | 0.88 -> 0.90 |
| config. estimada del amigo (brillo x0.5) | ajuste | 28.1 -> 19.2 | 0.50 -> 0.58 | 0.77 -> 0.92 |
| config. estimada del amigo (brillo x0.5) | control | 27.6 -> 19.9 | 0.43 -> 0.47 | 0.69 -> 0.83 |
| la misma con el brillo por defecto | ajuste | 46.5 -> 41.4 | 0.23 -> 0.29 | 0.38 -> 0.50 |
| la misma con el brillo por defecto | control | 45.7 -> 41.0 | 0.17 -> 0.20 | 0.29 -> 0.44 |
| AC sin CSP, 5_light_clouds | ajuste | 16.7 -> 12.9 | 0.71 -> 0.81 | 0.93 -> 0.97 |
| AC sin CSP, 5_light_clouds | control | 16.5 -> 13.1 | 0.80 -> 0.88 | 0.82 -> 0.87 |
| 5_light_clouds, brillo x1.4, sat 0.7 (2a hipotesis) | ajuste | 26.5 -> 16.0 | 0.49 -> 0.62 | 0.92 -> 1.02 |
| 5_light_clouds, brillo x1.4, sat 0.7 (2a hipotesis) | control | 25.5 -> 15.3 | 0.56 -> 0.63 | 0.78 -> 0.90 |

## 2. deltaE por vista (antes -> despues)

| vista | AC sin CSP / CSP gamma (3_clear) | CSP lineal, curva ACES | CSP lineal, sRGB + Yebis | config. estimada del amigo (brillo x0.5) | la misma con el brillo por defecto | AC sin CSP, 5_light_clouds | 5_light_clouds, brillo x1.4, sat 0.7 (2a hipotesis) |
|---|---|---|---|---|---|---|---|
| meta_tunel | 23.9 -> 17.4 | 16.8 -> 10.7 | 12.4 -> 10.9 | 22.2 -> 16.5 | 43.1 -> 39.4 | 10.8 -> 13.8 (peor) | 20.5 -> 15.5 |
| captura | 25.1 -> 15.6 | 16.8 -> 11.5 | 11.5 -> 6.4 | 24.8 -> 15.2 | 46.6 -> 39.8 | 11.1 -> 12.7 (peor) | 23.0 -> 12.8 |
| pueblo | 23.4 -> 12.6 | 21.7 -> 14.1 | 25.2 -> 19.0 | 29.8 -> 24.2 | 46.1 -> 43.9 | 19.8 -> 13.0 | 27.9 -> 17.9 |
| tierra | 36.3 -> 11.0 | 26.2 -> 14.4 | 33.8 -> 20.3 | 43.9 -> 24.5 | 59.2 -> 48.8 | 29.7 -> 12.0 | 43.3 -> 18.2 |
| casino | 23.2 -> 12.1 | 22.3 -> 15.9 | 27.0 -> 22.5 | 27.0 -> 18.9 | 44.9 -> 41.0 | 19.1 -> 12.9 | 26.6 -> 17.5 |
| piloto_s300 | 24.0 -> 14.9 | 15.2 -> 9.5 | 12.4 -> 8.4 | 22.4 -> 13.4 | 43.6 -> 36.9 | 10.3 -> 12.1 (peor) | 21.0 -> 12.7 |
| meta_puerto | 23.4 -> 15.9 | 17.8 -> 13.0 | 18.9 -> 16.2 | 26.3 -> 22.0 | 41.9 -> 40.2 | 16.3 -> 13.8 | 23.3 -> 17.6 |
| bajada (control) | 24.4 -> 11.0 | 23.8 -> 16.0 | 29.1 -> 24.0 | 28.3 -> 22.4 | 44.8 -> 42.3 | 21.0 -> 14.6 | 27.6 -> 18.6 |
| puente (control) | 19.1 -> 15.3 | 16.0 -> 12.6 | 17.3 -> 17.3 | 27.0 -> 24.4 | 41.5 -> 40.6 | 15.4 -> 12.6 | 21.9 -> 15.7 |
| piloto_s2900 (control) | 29.7 -> 14.9 | 13.5 -> 8.4 | 13.0 -> 11.6 | 27.4 -> 12.8 | 50.9 -> 40.2 | 13.2 -> 12.1 | 26.9 -> 11.7 |

## 3. Luminancia, croma, contraste y saturacion por vista, modo gamma (Blender / antes / despues)

| vista | lum media | croma media | contraste (std lum) | saturacion media |
|---|---|---|---|---|
| meta_tunel | 122 / 125 / 110 | 14.4 / 10.5 / 9.8 | 39.4 / 49.4 / 34.7 | 0.23 / 0.21 / 0.18 |
| captura | 118 / 143 / 117 | 12.9 / 9.1 / 10.7 | 34.0 / 44.1 / 31.0 | 0.20 / 0.15 / 0.16 |
| pueblo | 148 / 161 / 145 | 30.2 / 20.8 / 28.5 | 41.3 / 58.6 / 50.4 | 0.34 / 0.27 / 0.32 |
| tierra | 144 / 203 / 157 | 47.8 / 22.6 / 50.7 | 17.1 / 35.2 / 28.4 | 0.47 / 0.21 / 0.48 |
| casino | 154 / 172 / 158 | 32.2 / 23.2 / 30.0 | 41.4 / 53.8 / 47.0 | 0.35 / 0.29 / 0.33 |
| piloto_s300 | 127 / 138 / 115 | 10.0 / 10.7 / 9.8 | 31.5 / 45.9 / 31.8 | 0.14 / 0.17 / 0.14 |
| meta_puerto | 144 / 132 / 123 | 18.2 / 13.5 / 14.2 | 45.2 / 57.8 / 50.1 | 0.25 / 0.21 / 0.20 |
| bajada | 160 / 181 / 166 | 36.0 / 28.1 / 33.4 | 39.7 / 45.5 / 38.0 | 0.37 / 0.32 / 0.34 |
| puente | 147 / 136 / 128 | 12.7 / 16.8 / 12.5 | 41.4 / 51.3 / 55.7 | 0.21 / 0.28 / 0.22 |
| piloto_s2900 | 118 / 170 / 135 | 19.4 / 10.4 / 16.9 | 32.5 / 36.0 / 32.9 | 0.24 / 0.13 / 0.19 |

## 4. Materiales clave al sol (color mediano en pantalla, sRGB)

| vista | material | Blender | AC antes | AC despues | ACES despues | Yebis despues | amigo antes -> despues |
|---|---|---|---|---|---|---|---|
| captura | MAT_asfalto | [98, 102, 112] | [169, 162, 153] | [125, 122, 113] | [108, 116, 133] | [95, 100, 111] | [157, 155, 159] -> [113, 116, 118] |
| captura | MAT_terreno | [98, 168, 83] | [194, 205, 159] | [99, 166, 79] | [101, 200, 103] | [93, 168, 94] | [204, 216, 189] -> [133, 193, 131] |
| captura | MAT_terreno_roca | [155, 154, 144] | [160, 175, 127] | [142, 147, 125] | [177, 193, 189] | [147, 160, 157] | [203, 213, 202] -> [195, 202, 201] |
| captura | MAT_MCOCHE_caliza | [204, 202, 189] | [208, 196, 170] | [213, 203, 189] | [234, 232, 234] | [214, 211, 214] | [217, 217, 215] -> [220, 220, 220] |
| meta_tunel | MAT_asfalto | [100, 104, 114] | [167, 160, 151] | [123, 121, 112] | [92, 100, 116] | [85, 89, 100] | [156, 155, 158] -> [112, 115, 117] |
| meta_tunel | MAT_terreno | [118, 203, 96] | [216, 226, 182] | [131, 200, 105] | [105, 204, 108] | [96, 172, 98] | [209, 223, 189] -> [122, 195, 112] |
| meta_tunel | MAT_MCOCHE_caliza | [201, 196, 183] | [206, 194, 169] | [213, 204, 190] | [227, 225, 227] | [203, 200, 203] | [217, 218, 218] -> [219, 220, 222] |
| meta_puerto | MAT_asfalto | [100, 104, 113] | [168, 161, 152] | [124, 122, 113] | [70, 76, 90] | [69, 73, 82] | [164, 164, 168] -> [127, 131, 133] |
| meta_puerto | MAT_terreno | [124, 203, 100] | [216, 226, 184] | [129, 200, 106] | [80, 183, 84] | [79, 151, 81] | [209, 223, 196] -> [142, 200, 138] |
| meta_puerto | MAT_terreno_roca | [155, 155, 144] | [160, 175, 128] | [141, 146, 124] | [133, 151, 146] | [112, 125, 122] | [206, 215, 210] -> [201, 208, 209] |
| meta_puerto | MAT_agua | [154, 212, 248] | [124, 225, 227] | [169, 216, 240] | [126, 202, 241] | [111, 171, 226] | [156, 221, 229] -> [178, 213, 238] |
| meta_puerto | MAT_MCOCHE_caliza | [209, 207, 195] | [210, 198, 173] | [216, 207, 193] | [215, 212, 215] | [186, 182, 186] | [217, 219, 218] -> [219, 221, 222] |
| pueblo | MAT_asfalto | [92, 96, 105] | [162, 155, 147] | [118, 116, 108] | [58, 63, 76] | [61, 65, 73] | [166, 167, 171] -> [133, 137, 141] |
| pueblo | MAT_terreno | [101, 174, 80] | [214, 224, 182] | [128, 197, 106] | [67, 167, 69] | [70, 137, 71] | [212, 221, 207] -> [180, 207, 189] |
| pueblo | MAT_terreno_roca | [199, 190, 164] | [232, 238, 204] | [215, 218, 195] | [172, 185, 179] | [142, 153, 148] | [217, 228, 208] -> [205, 211, 204] |
| pueblo | MAT_CASAS_fachada_amarillo | [215, 180, 67] | [208, 182, 56] | [210, 196, 76] | [206, 198, 53] | [175, 166, 64] | [224, 213, 143] -> [224, 219, 155] |
| pueblo | MAT_CASAS_teja | [230, 94, 85] | [233, 128, 53] | [238, 108, 91] | [210, 48, 50] | [177, 55, 57] | [223, 130, 69] -> [227, 110, 104] |
| tierra | MAT_terreno | [96, 166, 79] | [212, 221, 179] | [116, 186, 94] | [57, 153, 59] | [63, 125, 64] | [210, 221, 198] -> [142, 198, 138] |
| tierra | MAT_terreno_roca | [147, 168, 130] | [214, 222, 184] | [182, 185, 161] | [141, 157, 150] | [118, 129, 124] | [212, 221, 210] -> [203, 210, 208] |
| piloto_s300 | MAT_asfalto | [101, 106, 115] | [164, 157, 149] | [121, 118, 109] | [100, 107, 124] | [89, 94, 105] | [153, 152, 155] -> [109, 112, 114] |
| piloto_s300 | MAT_terreno | [105, 184, 87] | [211, 221, 177] | [116, 186, 93] | [105, 205, 108] | [96, 173, 98] | [206, 220, 187] -> [119, 189, 110] |
| piloto_s300 | MAT_terreno_roca | [158, 157, 147] | [166, 179, 129] | [146, 150, 126] | [173, 188, 184] | [143, 156, 152] | [191, 206, 175] -> [174, 182, 171] |
| piloto_s300 | MAT_MCOCHE_caliza | [200, 205, 204] | [187, 173, 145] | [198, 187, 171] | [224, 222, 225] | [198, 196, 200] | [213, 208, 198] -> [218, 215, 212] |
| puente | MAT_asfalto | [97, 102, 112] | [167, 161, 153] | [124, 122, 114] | [68, 73, 87] | [68, 71, 80] | [169, 169, 173] -> [135, 140, 143] |
| puente | MAT_terreno | [102, 171, 87] | [191, 204, 161] | [107, 173, 95] | [63, 162, 66] | [67, 133, 69] | [214, 221, 223] -> [212, 219, 222] |
| puente | MAT_terreno_roca | [155, 158, 141] | [163, 178, 132] | [145, 150, 130] | [130, 148, 143] | [110, 123, 119] | [199, 211, 193] -> [188, 196, 191] |
| puente | MAT_agua | [137, 209, 249] | [123, 223, 226] | [166, 214, 239] | [120, 197, 239] | [106, 165, 222] | [206, 221, 226] -> [209, 219, 229] |
| puente | MAT_MCOCHE_caliza | [209, 209, 198] | [204, 193, 172] | [211, 203, 191] | [211, 208, 211] | [180, 177, 181] | [216, 221, 224] -> [216, 221, 225] |

## 5. Materiales protagonistas (los 14 con mas pixeles en las 10 vistas): deltaE antes -> despues

| material | pixeles | AC sin CSP / CSP gamma (3_clear) | CSP lineal, curva ACES | CSP lineal, sRGB + Yebis | config. estimada del amigo (brillo x0.5) | AC sin CSP, 5_light_clouds | 5_light_clouds, brillo x1.4, sat 0.7 (2a hipotesis) |
|---|---|---|---|---|---|---|---|
| MAT_asfalto | 1039203 | 25.6 -> 14.5 | 11.3 -> 8.0 | 5.1 -> 7.2 (peor) | 21.7 -> 8.3 | 5.3 -> 12.5 (peor) | 19.7 -> 6.0 |
| MAT_terreno | 821900 | 39.4 -> 10.2 | 31.9 -> 13.5 | 36.3 -> 20.1 | 48.0 -> 27.9 | 33.8 -> 14.0 | 47.3 -> 20.2 |
| MAT_terreno_roca | 267984 | 22.3 -> 15.5 | 22.3 -> 17.4 | 18.9 -> 18.1 | 26.3 -> 20.3 | 19.8 -> 12.8 | 24.3 -> 14.7 |
| MAT_MCOCHE_caliza | 169188 | 21.3 -> 17.1 | 10.5 -> 12.1 (peor) | 15.7 -> 10.7 | 22.3 -> 23.6 (peor) | 9.5 -> 9.9 | 18.3 -> 21.5 (peor) |
| MAT_agua | 135796 | 23.6 -> 13.5 | 21.2 -> 12.4 | 22.2 -> 23.1 (peor) | 21.9 -> 20.7 | 20.8 -> 19.3 | 17.8 -> 11.9 |
| MAT_CASAS_piedra | 123172 | 8.6 -> 9.1 | 14.3 -> 12.3 | 21.8 -> 19.1 | 16.5 -> 14.9 | 12.6 -> 11.8 | 19.1 -> 17.5 |
| MAT_PPUEBLO_roca | 110201 | 13.3 -> 15.5 (peor) | 9.2 -> 9.8 (peor) | 13.8 -> 14.0 | 27.6 -> 26.1 | 10.9 -> 9.5 | 22.9 -> 19.0 |
| MAT_CASAS_fachada_crema | 101310 | 14.3 -> 12.9 | 19.4 -> 14.3 | 30.1 -> 24.1 | 13.2 -> 13.0 | 13.2 -> 12.5 | 19.4 -> 19.2 |
| MAT_CARRERA_blanco | 92023 | 19.6 -> 20.1 | 12.3 -> 12.7 | 16.2 -> 14.0 | 17.8 -> 17.3 | 15.2 -> 15.0 | 17.5 -> 16.9 |
| MAT_CASAS_teja | 85692 | 29.2 -> 11.6 | 23.4 -> 16.6 | 27.9 -> 21.3 | 27.9 -> 17.2 | 21.9 -> 14.5 | 27.5 -> 20.4 |
| MAT_CASAS_persiana | 56027 | 17.5 -> 11.1 | 25.5 -> 16.2 | 24.6 -> 21.4 | 17.2 -> 16.4 | 15.0 -> 11.4 | 11.0 -> 15.8 (peor) |
| MAT_PIT_blanco | 48796 | 26.3 -> 27.4 (peor) | 10.0 -> 10.3 | 16.6 -> 15.1 | 22.0 -> 20.8 | 12.9 -> 12.1 | 21.7 -> 20.3 |
| MAT_CARRERA_verde_wgp | 46275 | 25.5 -> 20.8 | 24.9 -> 17.8 | 27.0 -> 19.0 | 14.9 -> 17.9 (peor) | 11.9 -> 11.3 | 14.2 -> 19.3 (peor) |
| MAT_PIT_hormigon | 41693 | 22.3 -> 22.2 | 8.0 -> 8.9 (peor) | 12.9 -> 9.6 | 25.4 -> 24.7 | 13.5 -> 12.7 | 25.4 -> 24.8 |

## 6. Lo que se sabe de la configuracion del amigo

Captura (zona de juego sin coche ni HUD): {'lum_media': 182.884, 'saturacion_media': 0.084, 'asfalto': [155.7, 154.0, 156.9], 'cielo': [215.5, 220.9, 225.1], 'contraste_lum_std': 34.283}.

- Configuracion estimada (ajuste_captura.py, Estimacion): ambiente x4.4, brillo x0.50, bruma a 400 m, saturacion 1.00; reproduce lum 177, sat 0.072, asfalto [156.4, 155.1, 158.6]. Con el brillo por defecto daria lum 236 (casi blanco): encaja con "antes era peor".
- Tiempos de Kunos (tiempos_captura.py, coste del ajuste a la captura; la estimada da 1.5):
  - 3_clear: por defecto lum 140, sat 0.160, asfalto [170, 163, 155] (coste 75); mejor con brillo x1.0 y saturacion 0.50 (coste 58.4)
  - 5_light_clouds: por defecto lum 134, sat 0.148, asfalto [110, 113, 118] (coste 224); mejor con brillo x1.4 y saturacion 0.70 (coste 3.8)
  - 2_light_fog: por defecto lum 113, sat 0.126, asfalto [104, 101, 103] (coste 371); mejor con brillo x1.4 y saturacion 0.70 (coste 43.8)
  - 1_heavy_fog: por defecto lum 96, sat 0.164, asfalto [52, 55, 58] (coste 1069); mejor con brillo x2.8 y saturacion 0.95 (coste 19.5)
  - 6_mid_clouds: por defecto lum 95, sat 0.139, asfalto [57, 56, 58] (coste 1027); mejor con brillo x2.8 y saturacion 0.95 (coste 26.8)
  - 7_heavy_clouds: por defecto lum 95, sat 0.138, asfalto [57, 56, 58] (coste 1027); mejor con brillo x2.8 y saturacion 0.95 (coste 26.8)

Lo que veria el amigo con el KN5 nuevo y sus ajustes de ahora (vista de la captura): estimada 148 / 0.09 / 40, 2a hipotesis 141 / 0.11 / 42; con el brillo por defecto 218 / 0.04 / 23 (Blender 118 / 0.20 / 34). Formato: lum / sat / contraste.

## 7. Palanca de ext_config.ini (solo CSP), media de las vistas de ajuste

| ks | ac | lcs | lcsy | captura | captura1 | nubes2 |
|---|---|---|---|---|---|---|
| KN5 (0.45/0.60) | 14.2 | 12.8 | 14.8 | 19.2 | 41.4 | 16.1 |
| palanca 0.30/0.55 (la del ext_config) | 17.3 | 14.3 | 16.1 | 16.8 | 35.6 | 14.1 |
| palanca 0.25/0.50 | 19.4 | 15.5 | 17.1 | 18.1 | 32.5 | 16.6 |

## 8. Por familia (modo gamma, caras de referencia; color_ac --informe)

Origen del objetivo de cada material: aspecto medido en las vistas de Blender 149, color del material 217, medido en Blender 92, efectivo (reflejo del cielo) 2.

| familia | n | ksA/ksD/ksS/exp | textura antes -> despues (sRGB) | AC suelo al sol antes / despues / Blender | AC pared al sol antes / despues / Blender | AC pared en sombra antes / despues / Blender | dE gamma antes -> despues |
|---|---|---|---|---|---|---|---|
| agua | 3 | 0.45/0.60/0.80/250 | [80, 188, 206] -> [50, 193, 230] | [151, 231, 231] / [109, 237, 241] / [102, 242, 254] | [98, 190, 192] / [66, 199, 208] / [86, 209, 239] | [33, 85, 94] / [20, 88, 105] / [47, 136, 170] | 20.7 -> 15.5 |
| asfalto | 10 | 0.45/0.60/0.08/20 | [120, 118, 119] -> [95, 98, 99] | [188, 182, 172] / [165, 163, 154] / [144, 149, 160] | [137, 131, 123] / [114, 114, 107] / [121, 126, 133] | [51, 50, 50] / [39, 40, 41] / [69, 80, 92] | 15.9 -> 16.0 |
| cristal | 18 | 0.45/0.60/0.60/150 | [58, 87, 102] -> [83, 96, 106] | [102, 142, 151] / [151, 164, 164] / [117, 139, 161] | [68, 100, 108] / [105, 117, 118] / [86, 113, 131] | [22, 35, 42] / [33, 39, 44] / [61, 81, 99] | 16.8 -> 17.3 |
| edificio | 121 | 0.45/0.60/0.03/12 | [200, 184, 157] -> [175, 165, 141] | [235, 226, 204] / [229, 221, 198] / [219, 208, 187] | [209, 197, 170] / [199, 189, 162] / [196, 185, 156] | [91, 84, 70] / [79, 74, 62] / [102, 106, 99] | 10.9 -> 10.6 |
| luz | 8 | 0.45/0.60/0.10/40 | [152, 147, 178] -> [140, 135, 162] | [176, 186, 205] / [192, 184, 208] / [162, 169, 225] | [143, 144, 166] / [160, 152, 179] / [155, 157, 200] | [68, 65, 80] / [97, 93, 114] / [116, 122, 158] | 23.8 -> 17.7 |
| metal | 41 | 0.45/0.60/0.40/60 | [154, 153, 146] -> [162, 164, 153] | [183, 181, 171] / [207, 208, 192] / [194, 197, 188] | [148, 145, 133] / [163, 163, 147] / [160, 169, 163] | [69, 68, 65] / [72, 73, 68] / [110, 124, 130] | 19.9 -> 15.9 |
| pintado | 146 | 0.45/0.60/0.12/40 | [138, 133, 117] -> [140, 136, 126] | [167, 170, 144] / [182, 182, 164] / [168, 168, 161] | [132, 131, 108] / [143, 141, 123] / [148, 150, 141] | [61, 58, 51] / [62, 60, 55] / [92, 100, 103] | 17.7 -> 15.3 |
| pintura_vial | 10 | 0.45/0.60/0.06/20 | [241, 225, 204] -> [231, 214, 199] | [246, 233, 214] / [246, 233, 217] / [255, 243, 230] | [220, 204, 182] / [220, 203, 184] / [237, 230, 216] | [111, 104, 94] / [107, 98, 91] / [142, 153, 159] | 17.5 -> 18.0 |
| roca | 11 | 0.45/0.60/0.02/8 | [194, 181, 159] -> [182, 170, 152] | [232, 224, 205] / [232, 224, 206] / [223, 214, 198] | [208, 197, 175] / [207, 196, 175] / [198, 190, 173] | [89, 82, 71] / [82, 77, 68] / [113, 121, 120] | 12.6 -> 12.0 |
| terreno | 13 | 0.45/0.60/0.00/1 | [155, 177, 122] -> [73, 129, 63] | [216, 223, 178] / [135, 199, 106] / [113, 181, 91] | [170, 182, 130] / [90, 149, 70] / [135, 172, 142] | [69, 80, 53] / [29, 55, 24] / [56, 104, 47] | 24.5 -> 20.7 |
| vegetacion | 79 | 0.45/0.60/0.00/1 | [131, 155, 107] -> [120, 156, 101] | [190, 209, 156] / [186, 215, 156] / [158, 194, 136] | [144, 164, 111] / [140, 170, 110] / [136, 168, 111] | [57, 69, 45] / [52, 69, 42] / [79, 110, 77] | 14.4 -> 12.9 |
