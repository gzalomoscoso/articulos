#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nube_vigia.py -- arma swing_top.json desde barras.json, sin Yahoo. 16-sep-2026.

POR QUE EXISTE
La cadena normal corre en la Mac de Gonzalo porque Yahoo bloquea las IPs de
centro de datos. Si la Mac esta apagada (viaje), ApexTrade se queda sin lista.

Este es el respaldo: corre en la nube, lee barras.json del repo -- que publica
la Mac cada noche -- y reconstruye la lista con la misma aritmetica. No pide
nada a Yahoo.

QUE PIERDE RESPECTO A LA CADENA COMPLETA
  universo      31 tickers (los que la Mac publico) en vez de 510
  fundamental   no hay: las revisiones de analistas salen de Yahoo
  vetos         no hay veto de earnings ni de revisiones negativas
  ATR           congelado en la fecha de barras.json

Por eso sale marcado modo="nube" y con vida util de 3 sesiones: pasadas esas,
el ATR ya no describe la volatilidad actual y la escalera deja de ser fiable.

Uso:  python3 nube_vigia.py barras.json [precios.json] > swing_top.json
      precios.json opcional: {"TK": cierre} para refrescar si las barras
      tienen mas de un dia.
"""

import datetime
import json
import math
import sys

# --- los mismos umbrales del carril FUERZA -------------------------------
EXT_MIN, EXT_MAX = 3.0, 20.0
ATR_MIN, ATR_MAX = 2.0, 6.0
TOL_ATR, TOL_CRUCE = 0.05, 0.03
CRUCE_MIN = -3.0
ESC_ATR, BANDA_ATR = 0.5, 0.25
STOP_PCT, OBJ_PCT = 6.0, 4.0
PESOS = {"fuerza_rel_60d": 0.40, "calidad_r2": 0.30, "recorrido_pct": 0.30}
VIDA_UTIL = 3

# Tabla de probabilidades a 9 sesiones: 380 celdas "stop_atr|obj_atr" -> [P_obj, P_stop].
# Va incrustada, no en un archivo aparte: es estatica, se midio una vez, y una
# dependencia menos es un 404 menos en una tarea que corre sola de madrugada.
TABLA_CARRERA = json.loads('{"0.4|0.2":[62.6,37.4],"0.4|0.4":[50.7,49.3],"0.4|0.6":[42.7,57.3],"0.4|0.8":[36.9,63.1],"0.4|1.0":[32.6,67.4],"0.4|1.2":[29.2,70.7],"0.4|1.4":[26.4,73.2],"0.4|1.6":[23.9,75.1],"0.4|1.8":[21.6,76.5],"0.4|2.0":[19.3,77.6],"0.4|2.2":[17.3,78.2],"0.4|2.4":[15.3,78.7],"0.4|2.6":[13.4,79.0],"0.4|2.8":[11.6,79.1],"0.4|3.0":[10.1,79.2],"0.4|3.2":[8.6,79.3],"0.4|3.4":[7.3,79.3],"0.4|3.6":[6.1,79.4],"0.4|3.8":[5.1,79.4],"0.4|4.0":[4.2,79.4],"0.6|0.2":[70.1,29.9],"0.6|0.4":[59.0,41.0],"0.6|0.6":[51.1,48.9],"0.6|0.8":[45.2,54.8],"0.6|1.0":[40.4,59.5],"0.6|1.2":[36.4,63.0],"0.6|1.4":[33.0,65.7],"0.6|1.6":[29.8,67.6],"0.6|1.8":[26.9,69.1],"0.6|2.0":[24.0,70.0],"0.6|2.2":[21.3,70.6],"0.6|2.4":[18.7,71.1],"0.6|2.6":[16.3,71.3],"0.6|2.8":[14.1,71.5],"0.6|3.0":[12.2,71.5],"0.6|3.2":[10.3,71.6],"0.6|3.4":[8.7,71.6],"0.6|3.6":[7.3,71.6],"0.6|3.8":[6.1,71.6],"0.6|4.0":[5.0,71.6],"0.8|0.2":[75.2,24.8],"0.8|0.4":[65.0,35.0],"0.8|0.6":[57.4,42.6],"0.8|0.8":[51.4,48.4],"0.8|1.0":[46.3,53.1],"0.8|1.2":[42.0,56.6],"0.8|1.4":[38.0,59.1],"0.8|1.6":[34.3,61.0],"0.8|1.8":[30.7,62.2],"0.8|2.0":[27.3,63.1],"0.8|2.2":[24.2,63.6],"0.8|2.4":[21.1,64.0],"0.8|2.6":[18.3,64.2],"0.8|2.8":[15.7,64.3],"0.8|3.0":[13.5,64.3],"0.8|3.2":[11.4,64.4],"0.8|3.4":[9.6,64.4],"0.8|3.6":[8.0,64.4],"0.8|3.8":[6.6,64.4],"0.8|4.0":[5.4,64.4],"1.0|0.2":[78.8,21.2],"1.0|0.4":[69.4,30.5],"1.0|0.6":[62.1,37.7],"1.0|0.8":[56.2,43.2],"1.0|1.0":[51.0,47.5],"1.0|1.2":[46.2,50.7],"1.0|1.4":[41.8,53.0],"1.0|1.6":[37.5,54.6],"1.0|1.8":[33.5,55.7],"1.0|2.0":[29.7,56.4],"1.0|2.2":[26.1,56.8],"1.0|2.4":[22.7,57.1],"1.0|2.6":[19.6,57.2],"1.0|2.8":[16.8,57.3],"1.0|3.0":[14.3,57.4],"1.0|3.2":[12.0,57.4],"1.0|3.4":[10.1,57.4],"1.0|3.6":[8.4,57.4],"1.0|3.8":[6.9,57.4],"1.0|4.0":[5.6,57.4],"1.2|0.2":[81.5,18.5],"1.2|0.4":[72.9,26.9],"1.2|0.6":[65.9,33.5],"1.2|0.8":[60.0,38.5],"1.2|1.0":[54.5,42.4],"1.2|1.2":[49.3,45.2],"1.2|1.4":[44.5,47.1],"1.2|1.6":[39.9,48.4],"1.2|1.8":[35.5,49.3],"1.2|2.0":[31.3,49.9],"1.2|2.2":[27.4,50.3],"1.2|2.4":[23.8,50.5],"1.2|2.6":[20.5,50.6],"1.2|2.8":[17.4,50.6],"1.2|3.0":[14.9,50.7],"1.2|3.2":[12.4,50.7],"1.2|3.4":[10.4,50.7],"1.2|3.6":[8.6,50.7],"1.2|3.8":[7.1,50.7],"1.2|4.0":[5.8,50.7],"1.4|0.2":[83.7,16.3],"1.4|0.4":[75.6,23.9],"1.4|0.6":[68.8,29.8],"1.4|0.8":[62.8,34.3],"1.4|1.0":[57.0,37.8],"1.4|1.2":[51.6,40.2],"1.4|1.4":[46.4,41.8],"1.4|1.6":[41.4,42.9],"1.4|1.8":[36.8,43.6],"1.4|2.0":[32.4,44.1],"1.4|2.2":[28.3,44.3],"1.4|2.4":[24.4,44.5],"1.4|2.6":[21.0,44.6],"1.4|2.8":[17.8,44.6],"1.4|3.0":[15.2,44.6],"1.4|3.2":[12.7,44.6],"1.4|3.4":[10.6,44.7],"1.4|3.6":[8.7,44.7],"1.4|3.8":[7.2,44.7],"1.4|4.0":[5.8,44.7],"1.6|0.2":[85.3,14.4],"1.6|0.4":[77.6,21.3],"1.6|0.6":[70.9,26.6],"1.6|0.8":[64.8,30.6],"1.6|1.0":[58.8,33.5],"1.6|1.2":[53.1,35.5],"1.6|1.4":[47.6,36.9],"1.6|1.6":[42.4,37.8],"1.6|1.8":[37.6,38.4],"1.6|2.0":[33.0,38.7],"1.6|2.2":[28.8,38.9],"1.6|2.4":[24.8,39.0],"1.6|2.6":[21.3,39.1],"1.6|2.8":[18.1,39.1],"1.6|3.0":[15.3,39.1],"1.6|3.2":[12.8,39.1],"1.6|3.4":[10.7,39.1],"1.6|3.6":[8.8,39.1],"1.6|3.8":[7.2,39.1],"1.6|4.0":[5.9,39.1],"1.8|0.2":[86.5,12.9],"1.8|0.4":[79.1,19.0],"1.8|0.6":[72.4,23.6],"1.8|0.8":[66.1,27.1],"1.8|1.0":[59.9,29.5],"1.8|1.2":[54.0,31.2],"1.8|1.4":[48.4,32.3],"1.8|1.6":[43.1,33.0],"1.8|1.8":[38.1,33.4],"1.8|2.0":[33.4,33.7],"1.8|2.2":[29.1,33.9],"1.8|2.4":[25.1,33.9],"1.8|2.6":[21.5,34.0],"1.8|2.8":[18.2,34.0],"1.8|3.0":[15.4,34.0],"1.8|3.2":[12.9,34.0],"1.8|3.4":[10.7,34.0],"1.8|3.6":[8.8,34.0],"1.8|3.8":[7.3,34.0],"1.8|4.0":[5.9,34.0],"2.0|0.2":[87.4,11.4],"2.0|0.4":[80.1,16.8],"2.0|0.6":[73.4,20.8],"2.0|0.8":[67.1,23.7],"2.0|1.0":[60.8,25.7],"2.0|1.2":[54.7,27.1],"2.0|1.4":[48.9,27.9],"2.0|1.6":[43.5,28.5],"2.0|1.8":[38.4,28.8],"2.0|2.0":[33.6,29.0],"2.0|2.2":[29.3,29.1],"2.0|2.4":[25.2,29.2],"2.0|2.6":[21.6,29.2],"2.0|2.8":[18.3,29.2],"2.0|3.0":[15.5,29.3],"2.0|3.2":[12.9,29.3],"2.0|3.4":[10.8,29.3],"2.0|3.6":[8.9,29.3],"2.0|3.8":[7.3,29.3],"2.0|4.0":[5.9,29.3],"2.2|0.2":[88.0,10.1],"2.2|0.4":[80.8,14.8],"2.2|0.6":[74.1,18.2],"2.2|0.8":[67.6,20.6],"2.2|1.0":[61.2,22.3],"2.2|1.2":[55.0,23.4],"2.2|1.4":[49.2,24.0],"2.2|1.6":[43.7,24.5],"2.2|1.8":[38.5,24.7],"2.2|2.0":[33.7,24.9],"2.2|2.2":[29.4,25.0],"2.2|2.4":[25.3,25.0],"2.2|2.6":[21.6,25.0],"2.2|2.8":[18.3,25.0],"2.2|3.0":[15.5,25.0],"2.2|3.2":[12.9,25.0],"2.2|3.4":[10.8,25.0],"2.2|3.6":[8.9,25.0],"2.2|3.8":[7.3,25.0],"2.2|4.0":[5.9,25.0],"2.4|0.2":[88.4,8.9],"2.4|0.4":[81.3,12.9],"2.4|0.6":[74.5,15.8],"2.4|0.8":[68.0,17.8],"2.4|1.0":[61.5,19.1],"2.4|1.2":[55.3,20.0],"2.4|1.4":[49.4,20.5],"2.4|1.6":[43.8,20.8],"2.4|1.8":[38.6,21.0],"2.4|2.0":[33.8,21.1],"2.4|2.2":[29.4,21.2],"2.4|2.4":[25.3,21.2],"2.4|2.6":[21.6,21.2],"2.4|2.8":[18.3,21.2],"2.4|3.0":[15.5,21.3],"2.4|3.2":[13.0,21.3],"2.4|3.4":[10.8,21.3],"2.4|3.6":[8.9,21.3],"2.4|3.8":[7.3,21.3],"2.4|4.0":[5.9,21.3],"2.6|0.2":[88.7,7.7],"2.6|0.4":[81.6,11.2],"2.6|0.6":[74.8,13.5],"2.6|0.8":[68.2,15.2],"2.6|1.0":[61.7,16.2],"2.6|1.2":[55.4,16.9],"2.6|1.4":[49.5,17.3],"2.6|1.6":[43.9,17.6],"2.6|1.8":[38.7,17.7],"2.6|2.0":[33.8,17.8],"2.6|2.2":[29.5,17.9],"2.6|2.4":[25.3,17.9],"2.6|2.6":[21.7,17.9],"2.6|2.8":[18.3,17.9],"2.6|3.0":[15.5,17.9],"2.6|3.2":[13.0,17.9],"2.6|3.4":[10.8,17.9],"2.6|3.6":[8.9,17.9],"2.6|3.8":[7.3,17.9],"2.6|4.0":[5.9,17.9],"2.8|0.2":[88.9,6.6],"2.8|0.4":[81.8,9.5],"2.8|0.6":[75.0,11.5],"2.8|0.8":[68.3,12.9],"2.8|1.0":[61.8,13.7],"2.8|1.2":[55.5,14.2],"2.8|1.4":[49.5,14.5],"2.8|1.6":[43.9,14.7],"2.8|1.8":[38.7,14.8],"2.8|2.0":[33.9,14.9],"2.8|2.2":[29.5,14.9],"2.8|2.4":[25.3,14.9],"2.8|2.6":[21.7,14.9],"2.8|2.8":[18.3,14.9],"2.8|3.0":[15.5,14.9],"2.8|3.2":[13.0,14.9],"2.8|3.4":[10.8,14.9],"2.8|3.6":[8.9,14.9],"2.8|3.8":[7.3,14.9],"2.8|4.0":[5.9,14.9],"3.0|0.2":[89.0,5.6],"3.0|0.4":[81.9,8.1],"3.0|0.6":[75.0,9.7],"3.0|0.8":[68.4,10.8],"3.0|1.0":[61.8,11.4],"3.0|1.2":[55.5,11.8],"3.0|1.4":[49.6,12.1],"3.0|1.6":[43.9,12.2],"3.0|1.8":[38.7,12.3],"3.0|2.0":[33.9,12.3],"3.0|2.2":[29.5,12.4],"3.0|2.4":[25.4,12.4],"3.0|2.6":[21.7,12.4],"3.0|2.8":[18.3,12.4],"3.0|3.0":[15.5,12.4],"3.0|3.2":[13.0,12.4],"3.0|3.4":[10.8,12.4],"3.0|3.6":[8.9,12.4],"3.0|3.8":[7.3,12.4],"3.0|4.0":[5.9,12.4],"3.2|0.2":[89.0,4.8],"3.2|0.4":[81.9,6.8],"3.2|0.6":[75.1,8.1],"3.2|0.8":[68.4,9.0],"3.2|1.0":[61.9,9.6],"3.2|1.2":[55.5,9.9],"3.2|1.4":[49.6,10.0],"3.2|1.6":[44.0,10.2],"3.2|1.8":[38.7,10.2],"3.2|2.0":[33.9,10.2],"3.2|2.2":[29.5,10.3],"3.2|2.4":[25.4,10.3],"3.2|2.6":[21.7,10.3],"3.2|2.8":[18.3,10.3],"3.2|3.0":[15.5,10.3],"3.2|3.2":[13.0,10.3],"3.2|3.4":[10.8,10.3],"3.2|3.6":[8.9,10.3],"3.2|3.8":[7.3,10.3],"3.2|4.0":[5.9,10.3],"3.4|0.2":[89.1,4.0],"3.4|0.4":[82.0,5.7],"3.4|0.6":[75.1,6.7],"3.4|0.8":[68.4,7.5],"3.4|1.0":[61.9,7.9],"3.4|1.2":[55.5,8.1],"3.4|1.4":[49.6,8.2],"3.4|1.6":[44.0,8.3],"3.4|1.8":[38.7,8.3],"3.4|2.0":[33.9,8.4],"3.4|2.2":[29.5,8.4],"3.4|2.4":[25.4,8.4],"3.4|2.6":[21.7,8.4],"3.4|2.8":[18.3,8.4],"3.4|3.0":[15.5,8.4],"3.4|3.2":[13.0,8.4],"3.4|3.4":[10.8,8.4],"3.4|3.6":[8.9,8.4],"3.4|3.8":[7.3,8.4],"3.4|4.0":[5.9,8.4],"3.6|0.2":[89.1,3.4],"3.6|0.4":[82.0,4.8],"3.6|0.6":[75.1,5.6],"3.6|0.8":[68.5,6.1],"3.6|1.0":[61.9,6.5],"3.6|1.2":[55.5,6.6],"3.6|1.4":[49.6,6.7],"3.6|1.6":[44.0,6.8],"3.6|1.8":[38.7,6.8],"3.6|2.0":[33.9,6.8],"3.6|2.2":[29.5,6.8],"3.6|2.4":[25.4,6.8],"3.6|2.6":[21.7,6.8],"3.6|2.8":[18.3,6.8],"3.6|3.0":[15.5,6.8],"3.6|3.2":[13.0,6.8],"3.6|3.4":[10.8,6.8],"3.6|3.6":[8.9,6.8],"3.6|3.8":[7.3,6.8],"3.6|4.0":[5.9,6.8],"3.8|0.2":[89.1,2.8],"3.8|0.4":[82.0,3.9],"3.8|0.6":[75.1,4.5],"3.8|0.8":[68.5,5.0],"3.8|1.0":[61.9,5.2],"3.8|1.2":[55.5,5.3],"3.8|1.4":[49.6,5.4],"3.8|1.6":[44.0,5.4],"3.8|1.8":[38.7,5.5],"3.8|2.0":[33.9,5.5],"3.8|2.2":[29.5,5.5],"3.8|2.4":[25.4,5.5],"3.8|2.6":[21.7,5.5],"3.8|2.8":[18.3,5.5],"3.8|3.0":[15.5,5.5],"3.8|3.2":[13.0,5.5],"3.8|3.4":[10.8,5.5],"3.8|3.6":[8.9,5.5],"3.8|3.8":[7.3,5.5],"3.8|4.0":[5.9,5.5],"4.0|0.2":[89.1,2.3],"4.0|0.4":[82.0,3.2],"4.0|0.6":[75.1,3.7],"4.0|0.8":[68.5,4.0],"4.0|1.0":[61.9,4.2],"4.0|1.2":[55.5,4.3],"4.0|1.4":[49.6,4.3],"4.0|1.6":[44.0,4.3],"4.0|1.8":[38.7,4.4],"4.0|2.0":[33.9,4.4],"4.0|2.2":[29.5,4.4],"4.0|2.4":[25.4,4.4],"4.0|2.6":[21.7,4.4],"4.0|2.8":[18.3,4.4],"4.0|3.0":[15.5,4.4],"4.0|3.2":[13.0,4.4],"4.0|3.4":[10.8,4.4],"4.0|3.6":[8.9,4.4],"4.0|3.8":[7.3,4.4],"4.0|4.0":[5.9,4.4]}')

FESTIVOS = {"2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25",
            "2026-06-19","2026-07-03","2026-09-07","2026-11-26","2026-12-25",
            "2027-01-01","2027-01-18","2027-02-15","2027-03-26","2027-05-31",
            "2027-06-18","2027-07-05","2027-09-06","2027-11-25","2027-12-24"}


def es_sesion(d):
    return d.weekday() < 5 and d.isoformat() not in FESTIVOS


def siguiente_sesion(d):
    d += datetime.timedelta(days=1)
    while not es_sesion(d):
        d += datetime.timedelta(days=1)
    return d


def sesiones_entre(a, b):
    n, d = 0, a
    while d < b:
        d += datetime.timedelta(days=1)
        if es_sesion(d):
            n += 1
    return n


def indicadores(b, px_fresco=None):
    """b = [[fecha,o,h,l,c,v], ...]. px_fresco extiende la serie de CIERRES.

    El ATR no se extiende: necesita maximo y minimo del dia, y el precio suelto
    no los trae. Se queda con el de la ultima barra real.
    """
    c = [r[4] for r in b]
    h = [r[2] for r in b]
    l = [r[3] for r in b]
    trs = [max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])) for i in range(1, len(c))]
    atr = sum(trs[:14]) / 14.0
    for x in trs[14:]:
        atr = (atr * 13 + x) / 14.0
    if px_fresco:
        c = c + [float(px_fresco)]
    px = c[-1]
    sma50 = sum(c[-50:]) / 50.0
    sma150 = sum(c[-150:]) / 150.0
    w = c[-252:] if len(c) >= 252 else c
    lo, hi = min(w), max(w)
    # R2 de la regresion del log-precio a 60 dias, con el signo de la pendiente
    ys = [math.log(x) for x in c[-60:] if x > 0]
    r2 = None
    if len(ys) == 60:
        n = 60
        xs = list(range(n))
        mx, my = sum(xs)/n, sum(ys)/n
        sxy = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
        sxx = sum((x-mx)**2 for x in xs)
        syy = sum((y-my)**2 for y in ys)
        if sxx > 0 and syy > 0:
            r2 = (sxy*sxy)/(sxx*syy) * (1 if sxy > 0 else -1)
    fr = None
    if len(c) >= 66 and c[-66] > 0:
        fr = (c[-6]/c[-66] - 1) * 100
    return {"precio": px, "sma_50": sma50, "sma_150": sma150, "atr_14": atr,
            "atr_pct": atr/px*100, "ext": (px/sma150-1)*100,
            "cruce": (sma50-sma150)/px*100,
            "pos52": (px-lo)/(hi-lo)*100 if hi > lo else 50.0,
            "calidad_r2": r2, "fuerza_rel_60d": fr,
            "recorrido_pct": max(0.0, (sma150*(1+EXT_MAX/100)/px - 1)*100)}


def pasa_fuerza(d):
    """Mismas reglas y mismo perdon: una falta de banda, ninguna de estructura."""
    estruct, banda = [], []
    if d["precio"] <= d["sma_150"]:
        estruct.append("SMA150")
    elif d["ext"] < EXT_MIN or d["ext"] > EXT_MAX:
        banda.append("extension")
    if d["precio"] <= d["sma_50"]:
        estruct.append("SMA50")
    if not (ATR_MIN - TOL_ATR <= d["atr_pct"] <= ATR_MAX + TOL_ATR):
        banda.append("ATR")
    if d["cruce"] < CRUCE_MIN - TOL_CRUCE:
        estruct.append("cruce")
    return (not estruct) and len(banda) <= 1, estruct + banda


def prob(tabla, sa, oa):
    q = lambda v: min(4.0, max(0.4, round(v/0.2)*0.2))
    p = tabla.get("%.1f|%.1f" % (q(sa), q(oa)))
    return (p[0], p[1]) if p else (None, None)


def percentiles(vals):
    """Empates promediados: los iguales reciben el mismo percentil."""
    ut = [(i, v) for i, v in enumerate(vals) if v is not None]
    out = [0.5]*len(vals)
    if len(ut) < 2:
        return out
    ut.sort(key=lambda t: t[1])
    n = len(ut)-1
    j = 0
    while j < len(ut):
        k = j
        while k+1 < len(ut) and ut[k+1][1] == ut[j][1]:
            k += 1
        p = ((j+k)/2.0)/n
        for m in range(j, k+1):
            out[ut[m][0]] = p
        j = k+1
    return out


def main():
    B = json.load(open(sys.argv[1], encoding="utf-8"))
    precios = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else {}
    tabla = TABLA_CARRERA

    cierre_barras = datetime.date(*map(int, B["cierre"].split("-")))
    hoy = datetime.date.today()
    base = hoy if es_sesion(hoy) else hoy
    # la sesion a operar es la siguiente al cierre mas reciente que tengamos
    cierre_efectivo = cierre_barras
    if precios:
        cierre_efectivo = max(cierre_barras, hoy - datetime.timedelta(days=1))
    antiguedad = sesiones_entre(cierre_barras, hoy)

    filas = []
    for tk, b in B["barras"].items():
        if len(b) < 160:
            continue
        d = indicadores(b, precios.get(tk))
        ok, fallas = pasa_fuerza(d)
        if not ok:
            continue
        esc = d["precio"] + ESC_ATR*d["atr_14"]
        obj = min(esc*(1+OBJ_PCT/100), d["sma_150"]*(1+EXT_MAX/100))
        stop = esc*(1-STOP_PCT/100)
        if obj <= esc:
            continue
        sa, oa = (esc-stop)/d["atr_14"], (obj-esc)/d["atr_14"]
        po, ps = prob(tabla, sa, oa)
        ev = None
        if po is not None:
            ev = po/100*((obj/esc-1)*100) - ps/100*STOP_PCT
            if ev <= 0:
                continue
        filas.append({"ticker": tk, "precio": round(d["precio"], 2),
                      "entrada": round(esc, 2), "stop": round(stop, 2),
                      "objetivo": round(obj, 2),
                      "atr_14": round(d["atr_14"], 2),
                      "atr_pct": round(d["atr_pct"], 2),
                      "sma_150": round(d["sma_150"], 2),
                      "perdida_pct": STOP_PCT,
                      "fuerza_rel_60d": round(d["fuerza_rel_60d"], 2) if d["fuerza_rel_60d"] is not None else None,
                      "calidad_r2": round(d["calidad_r2"], 3) if d["calidad_r2"] is not None else None,
                      "recorrido_pct": round(d["recorrido_pct"], 2),
                      "p_obj": po, "p_stop": ps,
                      "ev": round(ev, 3) if ev is not None else None,
                      "carril": "FUERZA"})

    if filas:
        pct = {k: percentiles([f.get(k) for f in filas]) for k in PESOS}
        for i, f in enumerate(filas):
            f["score"] = round(sum(PESOS[k]*pct[k][i] for k in PESOS), 4)
            f["score_fundamental"] = None      # no hay Yahoo en la nube
            f["score_final"] = f["score"]
        filas.sort(key=lambda f: (-f["score_final"], -(f.get("ev") or 0), f["ticker"]))
        for i, f in enumerate(filas, 1):
            f["rank_final"] = i

    doc = {
        "generado": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cierre": cierre_efectivo.isoformat(),
        "para_sesion": siguiente_sesion(cierre_efectivo).isoformat(),
        "modo": "nube",
        "barras_de": B["cierre"],
        "antiguedad_sesiones": antiguedad,
        "fiable": antiguedad <= VIDA_UTIL,
        "aviso": (None if antiguedad <= VIDA_UTIL else
                  "Las barras tienen %d sesiones. El ATR esta congelado y la "
                  "escalera ya no es fiable." % antiguedad),
        "analizadas": len(B["barras"]),
        "pasaron_carril": len(filas),
        "evaluar": [f["ticker"] for f in filas],
        "candidatas": filas,
        "vetadas": [],
        "riesgo_pct": 1.0,
        "sesiones_max": 9,
        "formula_acc": "patrimonio * riesgo_pct/100 / (perdida_pct/100 * entrada)",
        "limitaciones": ["universo reducido a las %d que publico la Mac" % len(B["barras"]),
                         "sin capa fundamental: revisiones de analistas y veto de earnings",
                         "ATR congelado en %s" % B["cierre"]],
    }
    json.dump(doc, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
