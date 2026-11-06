"""
Estrategias parametrizadas con reglas 100 % objetivas (nada discrecional) y backtest en R.

Una estrategia = combinación de:
  ema       -> periodo de la media que define la tendencia (precio > EMA = alcista)
  entrada   -> 'cruce'    : el precio cruza la EMA
               'apoyo'    : en tendencia, el precio toca la EMA y cierra a favor
                            ("se apoya en la media y no la rompe" — ejemplo del vídeo)
               'ruptura'  : en tendencia, cierra por encima del máximo de N velas
  adx_min   -> fuerza mínima de tendencia (0 = sin filtro)
  sl_atr    -> stop loss = sl_atr x ATR
  tp_r      -> take profit en múltiplos de R (riesgo)
  sentido   -> 'ambos' | 'largos' | 'cortos'
  ruptura_n -> velas para la ruptura
  max_velas -> cierre por tiempo
  franja    -> usar o no tu franja horaria (solo intradía)
"""
import numpy as np

import config

ESPACIO = {
    "ema": [20, 50, 100, 200],
    "entrada": ["cruce", "apoyo", "ruptura"],
    "adx_min": [0, 15, 20, 25, 30],
    "sl_atr": [1.0, 1.5, 2.0, 2.5, 3.0],
    "tp_r": [1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
    "sentido": ["ambos", "largos", "cortos"],
    "ruptura_n": [10, 20, 55],
    "max_velas": [10, 20, 50, 100],
    "franja": [True, False],
}


def aleatoria(rng):
    return {k: v[rng.integers(len(v))] for k, v in ESPACIO.items()}


def mutar(p, rng, prob=0.3):
    q = dict(p)
    for k, v in ESPACIO.items():
        if rng.random() < prob:
            i = v.index(q[k]) if q[k] in v else 0
            q[k] = v[int(np.clip(i + rng.choice([-1, 1]), 0, len(v) - 1))] if not isinstance(v[0], (str, bool)) \
                else v[rng.integers(len(v))]
    return q


def clave(p):
    return tuple(sorted(p.items()))


def senales(f, p, intradia):
    """Devuelve arrays booleanos de señal larga/corta al CIERRE de cada vela."""
    c, o, l, h = f["c"], f["o"], f["l"], f["h"]
    e = f[f"ema{p['ema']}"]
    arriba, abajo = c > e, c < e
    fuerza = f["adx"] >= p["adx_min"]
    if p["entrada"] == "cruce":
        prev = np.r_[False, arriba[:-1]]
        prev_ab = np.r_[False, abajo[:-1]]
        lg, ct = arriba & ~prev, abajo & ~prev_ab
    elif p["entrada"] == "apoyo":
        lg = arriba & (l <= e) & (c > o)
        ct = abajo & (h >= e) & (c < o)
    else:
        n = p["ruptura_n"]
        lg = arriba & (c > f[f"hh{n}"])
        ct = abajo & (c < f[f"ll{n}"])
    lg, ct = lg & fuerza, ct & fuerza
    if intradia and p["franja"] and config.FRANJA_UTC:
        a, b = config.FRANJA_UTC
        hora_ok = (f["hora"] >= a) & (f["hora"] < b)
        lg, ct = lg & hora_ok, ct & hora_ok
    if p["sentido"] == "largos":
        ct = np.zeros_like(ct)
    elif p["sentido"] == "cortos":
        lg = np.zeros_like(lg)
    calentamiento = 210
    lg[:calentamiento] = False
    ct[:calentamiento] = False
    return lg, ct


def backtest(f, p, coste, intradia, desde=0, hasta=None):
    """Simula operación a operación. Devuelve lista de trades (dict) con resultado en R.
    Entrada a la apertura de la vela siguiente. Si SL y TP caen en la misma vela -> se asume SL."""
    hasta = len(f["c"]) if hasta is None else hasta
    lg, ct = senales(f, p, intradia)
    idx = np.flatnonzero((lg | ct)[desde:hasta - 1]) + desde
    o, h, l, c, a = f["o"], f["h"], f["l"], f["c"], f["atr"]
    trades, libre_desde = [], desde
    for i in idx:
        if i < libre_desde:
            continue
        d = 1 if lg[i] else -1
        ent = o[i + 1]
        dist = p["sl_atr"] * a[i]
        if not dist > 0:
            continue
        sl, tp = ent - d * dist, ent + d * p["tp_r"] * dist
        fin = min(i + 1 + p["max_velas"], hasta)
        r, j = None, i + 1
        for j in range(i + 1, fin):
            if j > i + 1:  # hueco en la apertura
                if (d == 1 and o[j] <= sl) or (d == -1 and o[j] >= sl):
                    r = d * (o[j] - ent) / dist; break
                if (d == 1 and o[j] >= tp) or (d == -1 and o[j] <= tp):
                    r = d * (o[j] - ent) / dist; break
            toca_sl = l[j] <= sl if d == 1 else h[j] >= sl
            toca_tp = h[j] >= tp if d == 1 else l[j] <= tp
            if toca_sl:
                r = -1.0; break
            if toca_tp:
                r = p["tp_r"]; break
        if r is None:
            r = d * (c[j] - ent) / dist
        r -= coste / dist
        trades.append({"i": int(i), "salida": int(j), "dir": d, "R": float(r),
                       "entrada": float(ent), "sl": float(sl), "tp": float(tp)})
        libre_desde = j + 1
    return trades


def metricas(trades):
    if not trades:
        return {"n": 0, "esperanza": 0.0, "acierto": 0.0, "gana_med": 0.0, "pierde_med": 0.0,
                "pf": 0.0, "max_dd": 0.0, "sqn": -9.0, "total_R": 0.0}
    r = np.array([t["R"] for t in trades])
    g, p = r[r > 0], r[r <= 0]
    eq = np.cumsum(r)
    dd = float(np.max(np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]))
    sd = r.std(ddof=1) if len(r) > 1 else 1
    return {
        "n": int(len(r)),
        "esperanza": float(r.mean()),                     # R medio por trade (la "esperanza" del vídeo)
        "acierto": float(len(g) / len(r)),
        "gana_med": float(g.mean()) if len(g) else 0.0,
        "pierde_med": float(p.mean()) if len(p) else 0.0,
        "pf": float(g.sum() / -p.sum()) if p.sum() < 0 else 99.0,
        "max_dd": dd,
        "sqn": float(r.mean() / sd * np.sqrt(min(len(r), 100))) if sd > 0 else 0.0,
        "total_R": float(r.sum()),
    }


def puntuar(m, min_trades):
    """Nota para el aprendizaje: calidad del sistema penalizando drawdowns y pocas operaciones."""
    if m["n"] < min_trades or m["pf"] < 1.0:
        return -9.0
    return m["sqn"] - 0.02 * m["max_dd"]


def describir(p, intradia):
    ent = {"cruce": f"cruce del precio con la EMA{p['ema']}",
           "apoyo": f"apoyo en la EMA{p['ema']} con cierre a favor",
           "ruptura": f"ruptura del máximo/mínimo de {p['ruptura_n']} velas a favor de la EMA{p['ema']}"}[p["entrada"]]
    txt = f"{p['sentido'].capitalize()}: {ent}"
    if p["adx_min"]:
        txt += f", solo si ADX ≥ {p['adx_min']}"
    txt += f". SL {p['sl_atr']}×ATR, TP {p['tp_r']}R, cierre a las {p['max_velas']} velas"
    if intradia and p["franja"] and config.FRANJA_UTC:
        txt += f", solo en tu franja {config.FRANJA_UTC[0]}-{config.FRANJA_UTC[1]}h UTC"
    return txt + "."
