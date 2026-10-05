# Acotaciones del coordinador para la ronda 4 de F1 (04/10/2026 23:30)

Tras 3 rondas (director: `director_f1_r3.md`; hojas en `renders/ab/f1_r3/`): las 6 vistas de piloto MEJORAN en
modo AC y normal, 0 regresiones de piloto, pct_cesped 0 %, riqueza x2.2, roca por pendiente 81.7 %, horizonte
y plan de vegetacion OK. Quedan 2 REAL (puerta ok:false; KPI del relieve) y varios MENOR. Decisiones:

1. **KPI "pared Y caida a 25 m" (bloque 1)**: se ACOTA para F1 a **>= 30 % a 25 m y >= 20 % a 50 m** (hoy 33.6 /
   23.3). Razon: con la geometria actual de la pista el tope es ~34-35 %; el resto viene del macizo/espolon de F2.
   CONDICION: la cima de la postal 56 debe ser una CUPULA (pendiente <= 30 grados en los 20 m superiores) y el
   A/B de 56 no debe tener los "dientes" de roca (fila de 6 por cara) ni la arista recta. El "mar >= 25 % en 56"
   pasa a F2 (despeje de vista con el relieve nuevo), por escrito aqui.
2. **KPI horizonte**: se RE-ESCRIBE como media de cobertura de la linea mar/cielo en 54/57/13/21/61 >= 50 % Y mar
   abierto >= 50 % en 54 y 63 (49/52 no tienen mar en el cuadro: no cuentan). Anadir 1 loma a 2.4-2.8 km en la
   ventana de 54 (brujula 190-215) y redondear los picos de aguja (55, 57, 13, 21). No tocar la mezcla de color.
3. **Puerta (integrador)**: el RNG de integrar_escena debe ser DETERMINISTA POR ZONA (semilla derivada del nombre
   de la zona + semilla global) para que la comparacion con la base mida cambios reales y no sorteos. Con eso,
   corregir lo atribuible a F1: recorte 0.3 -> 1.0 m en prop_camino (ITAL_fuente.005 junto al arranque del
   sendero CIMA), re-asentar OLI_olivo.160, VEG_cipres.282, VEG_pino.186, CAMINO_tierra.003 y el muro perdido de
   URB_travesias_0_1. Criterio de promocion: puerta.json ok:true; si tras el RNG determinista quedan fallos de
   revisar_urbanismo que ya estaban en la base (misma casa, mismo tipo), se documentan como "heredados" en
   PROMOCIONES.md y no bloquean (maximo: la cifra de la base, 23). Ejecutar ademas el presupuesto de tris y el
   grep de RGB fuera de paleta.json (pendiente desde r1): ambos obligatorios en la entrega.
4. **Roca por cara de 4 m con borde en sierra (modo AC)**: es [W] (P1 del writer, bloque X) y NO bloquea F1.
   Mitigacion interina en F1: ruido del atributo roca 0.08 -> 0.20, subdivision a 2 m del TERRENO en una banda
   de 20 m junto a la pista (vertices +40-50 k maximo), umbral nz < 0.62 en la cima de 56 y laderas a < 150 m de
   51/07. Propietario: 'mascara' (construir_pista) con los umbrales de 'terreno' (terreno_montana).
5. **Materiales (MENOR, se arreglan en r4)**: McLaren en el proxy AC gris azulado con tile de 3 m (10.5);
   saturacion de la roca en el proxy AC acorde a caliza media #B3A68A (S ~0.23); reticula de NG_caliza_estratos
   (celdas 10-15 m y lineas de estrato cruzando la arista) en modo normal (10.3/10.4): estratos por z de MUNDO
   continuos y ruido no alineado a la rejilla.
6. **Paleta v2 es DEFINITIVA** (`paleta.json` version 2, crema_calido #E6D4B0): nada de literales nuevos.
7. **Costuras** (= base, 2.03 m): no bloquea (criterio "no peor que la base"); objetivo < 0.6 pasa a F2.
8. **Vegetacion**: siluetas en 50/63 bajaron por el despeje final; no es regresion contra la base; F3 recupera
   las masas del lado derecho de 50 a 20-120 m. Sin accion en r4.

Ronda 4 = ultima de F1: si el director aprueba (0 REAL, 0 regresiones de piloto, puerta ok), se promueve y se
hace el zip v1.2 "paleta y fondo" + mini-pista F del pueblo/puerto. Lo MENOR que quede va al registro para F2.

## Nota de reanudacion (05/10 00:10)
La ronda 4 se corto a las ~00:05 por el limite de uso del modelo (no por un fallo del trabajo). Terminaron y
quedan en cache: 'mascara', 'materiales' y 'horizonte'. Se cortaron: 'terreno' e 'integrador'.
- Para 'terreno': NO empieces de cero. Tu trabajo de la ronda 4 esta en terreno_montana.py (00:04, compila; copia
  de la version r3 en _rev/_tmp_terreno/r4/terreno_montana_r3_backup.py) y tus pruebas en _rev/_tmp_terreno/r4/
  (qa_v43..v46, sonda56.py, vista_sintetica.py, vs56_base/r3/v43..v46.png). Mira vs56_v46.png y el ultimo qa
  para saber donde ibas (cupula de la cima de 56 sin dientes), termina, verifica y entrega.
- Para el 'integrador': nada empezado (no se lanzo el pipeline de la ronda 4).
- Sobre el punto 18.1 de 'materiales' (ambiente gris del proxy AC): el proxy NO se toca en F1 (es una
  herramienta de juicio, no el juego); se anota como limitacion conocida del modo AC en el registro.

## Decisiones del coordinador sobre las entregas de la ronda 4 (05/10 00:20)
Se relanza como "ronda 4b": solo termina 'terreno'; 'mascara', 'materiales' y 'horizonte' ya entregaron
(resumenes en f1r4_entregas_cache.json; parches en PARCHES_F1_*.md, secciones 'ronda 4').
9. **Horizonte, metrica**: el KPI se juzga con DOS metricas y basta una: media 54/57/13/21/61 >= 45 % con la
   banda de 60 px del director (banda_director.py) O >= 50 % con medir_horizonte.py del propietario; y en ambas
   mar abierto >= 50 % en 54 y 63. (La banda de 60 px descarta siluetas altas a 3-4.5 km, que son justo las
   pedidas; por eso el umbral baja a 45 % con esa metrica.)
10. **Materiales 18.1 (luz gris del proxy AC)**: NO se aplica. El modo AC es una herramienta de juicio; ajustar su
   luz para que las cifras salgan mejor seria hacerse trampas. El KPI "McLaren y roca con caliza calida" se juzga
   en MODO NORMAL (tono y saturacion) y en modo AC solo se exige que no sean gris azulado frio (H fuera de
   180-240). La saturacion baja del proxy AC queda como limitacion conocida en el registro.
11. **Materiales 18.2 (tile de detalle A del terreno en BOX/Object en vez de planar, estrias de 51/07)**: lo
   aplica el INTEGRADOR en construir_pista.py si es un cambio de <= 15 lineas, documentado en el registro como
   "cambio del integrador en fichero de 'mascara' por cierre de F1"; si es mayor, pasa a F2.
12. **Mascara A8 (banda de 2 m junto a la pista)**: la aplica el integrador tal como dice PARCHES_F1_mascara.md
   (R4.4): copiar _rev/_tmp_mascara/r4/banda_terreno_2m.py a _rev/ y las 3 lineas del pipeline. Medir vertices
   del TERRENO antes/despues (tope +50 k) y que revisar_fisica no se ve afectado (es [W]; solo anotarlo).

## Nota de reanudacion 2 (05/10 00:25)
El usuario apago el PC a las ~00:25 con 'terreno' (ronda 4b) en curso: iba por _rev/_tmp_terreno/r4/qa_v47;
terreno_montana.py compila (copia: _rev/_tmp_terreno/r4/terreno_montana_r4_0024.py). Al reanudar: continua
desde qa_v47 y vs56_v46.png (cupula de la cima de 56 sin dientes), NO empieces de cero.

## Nota de reanudacion 3 (05/10 08:05)
Reanudado tras el apagado. Estado: terreno_montana.py 00:25 (compila). Ultimas pruebas del terreno en
_rev/_tmp_terreno/r4/: qa_v47 + vs56_v47.png + medir_v47.json (completas) y qa_v48 + preparar_v48.log (00:25,
probablemente a medias: comprueba si preparar_v48.log termino). Continua desde ahi, no empieces de cero.

## Cierre de F1 (05/10 10:45) - decisiones tras director_f1_r4.md
Veredicto r4: 0 regresiones de piloto (AC y normal), cupula de 56 OK, KPIs acotados OK (PyC 32.4/23.3, horizonte
45.6 % director / 56.8 % propietario, tris 4.75 M); UNICO REAL = puerta por arboles_quitados 4 > 3 (sorteo).
13. **arboles_quitados**: se regenera UNA vez con el filtro de pendiente de zona_casino (ya en el codigo). Si aun
   asi da 4 (o <= 5) y los quitados estan en cantiles/laderas con terreno identico a la base, se ACEPTA: tolerancia
   escrita en linea_base.json (lista de objetos) y en PROMOCIONES.md, y se promueve. No hay mas rondas de F1.
14. **Paleta**: antes del zip v1.2 los 3 literales NUEVOS de F1 pasan a paleta: MAT_VEG_cipres_b -> cipres_pino_oscuro,
   MAT_VEG_retama -> salvia, MAT_fondo_marino -> arena/mar_orilla de paleta.json. Los otros 30 (base 57 -> 33) a F2.
15. **Pasan a F2** (registro): McLaren en modo normal oliva oscuro (#6A6D62 -> caliza calida), roca del lazo fria en
   normal, celosia del tile de 4 m en modo normal (segundo tile girado/escalado mezclado por ruido 20-40 m), estratos
   como aranazos en 54, siluetas de 50 (F3 planta >= 3 copas a 20-120 m), islote en la ventana de 61, costuras.
16. **04_export SE ABRE** (v1.1 publicado): el zip v1.2 necesita que el writer exporte bien el TERRENO nuevo (UV 0..1
   de la mascara: con el writer de hoy el tile de 512 se estiraria sobre 2 km), cierre/fisica re-ejecutados sobre el
   terreno nuevo (0 fallos) y una vista "como AC" leida del propio KN5. Lo hace un equipo de export dedicado.
