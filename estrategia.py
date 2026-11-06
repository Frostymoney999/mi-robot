"""
Estrategias parametrizadas con reglas 100 % objetivas (nada discrecional) y backtest en R.

Una estrategia = una FAMILIA (cómo entra) + filtros + gestión:
  ema       -> media que define la tendencia (precio > EMA = solo compras; < EMA = solo ventas)
  entrada   -> familia: cruce | apoyo | ruptura | rsi | bollinger | macd | inside | orb  (ver config.FAMILIAS)
  adx_min   -> fuerza mínima de tendencia (0 = sin filtro)
  sl_atr    -> stop loss = sl_atr x ATR
  tp_r      -> take profit en múltiplos de R
  sentido   -> ambos | largos | cortos
  max_velas -> cierre por tiempo
  franja    -> operar solo en tus horarios (solo H1)
"""
import numpy as np

import config

BASE_ESPACIO = {
    "ema": [20, 50, 100, 200],
    "adx_min": [0, 15, 20, 25, 30],
    "sl_atr": [1.0, 1.5, 2.0, 2.5, 3.0],
    "tp_r": [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
    "sentido": ["ambos", "largos", "cortos"],
    "ruptura_n": [10, 20, 55],
    "rsi_nivel": [25, 30, 35, 40],
    "orb_hora": [9, 15],
    "max_velas": [10, 20, 50, 100],
    "franja": [True, False],
}


def espacio(intradia):
    fams = [f for f in config.AJUSTES["familias"] if intradia or f != "orb"] or ["cruce"]
    e = dict(BASE_ESPACIO)
    e["entrada"] = fams
    if not intradia:
        e["franja"] = [False]
    return e


def aleatoria(rng, intradia):
    e = espacio(intradia)
    return {k: v[rng.integers(len(v))] for k, v in e.items()}


def mutar(p, rng, intradia, prob=0.3):
    e = espacio(intradia)
    q = dict(p)
    for k, v in e.items():
        if rng.random() < prob or q.get(k) not in v:
            if isinstance(v[0], (str, bool)) or q.get(k) not in v:
                q[k] = v[rng.integers(len(v))]
            else:
                i = v.index(q[k])
                q[k] = v[int(np.clip(i + rng.choice([-1, 1]), 0, len(v) - 1))]
    return q


def valida(p, intradia):
    e = espacio(intradia)
    return all(p.get(k) in v for k, v in e.items())


def clave(p):
    return tuple(sorted(p.items()))


def _cruza_arriba(a, b):
    return np.r_[False, (a[1:] > b[1:]) & (a[:-1] <= b[:-1])]


def senales(f, p, intradia):
    """Arrays booleanos de señal larga/corta al CIERRE de cada vela."""
    c, o, l, h = f["c"], f["o"], f["l"], f["h"]
    e = f[f"ema{p['ema']}"]
    arriba, abajo = c > e, c < e
    fam = p["entrada"]
    with np.errstate(invalid="ignore"):
        if fam == "cruce":
            lg, ct = _cruza_arriba(c, e), _cruza_arriba(e, c)
        elif fam == "apoyo":
            lg = arriba & (l <= e) & (c > o)
            ct = abajo & (h >= e) & (c < o)
        elif fam == "ruptura":
            n = p["ruptura_n"]
            lg, ct = arriba & (c > f[f"hh{n}"]), abajo & (c < f[f"ll{n}"])
        elif fam == "rsi":
            r, nv = f["rsi"], p["rsi_nivel"]
            lg = arriba & _cruza_arriba(r, np.full_like(r, nv))
            ct = abajo & _cruza_arriba(np.full_like(r, 100 - nv), r)
        elif fam == "bollinger":
            lg = arriba & _cruza_arriba(c, f["bb_inf"])
            ct = abajo & _cruza_arriba(f["bb_sup"], c)
        elif fam == "macd":
            lg = arriba & _cruza_arriba(f["macd"], f["macd_sig"])
            ct = abajo & _cruza_arriba(f["macd_sig"], f["macd"])
        elif fam == "inside":
            hp, lp = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
            lg = arriba & f["inside_prev"] & (c > hp)
            ct = abajo & f["inside_prev"] & (c < lp)
        elif fam == "orb" and intradia:
            hh = p["orb_hora"]
            rh, rl = f[f"orb_h{hh}"], f[f"orb_l{hh}"]
            lg = arriba & _cruza_arriba(c, np.nan_to_num(rh, nan=np.inf))
            ct = abajo & _cruza_arriba(np.nan_to_num(rl, nan=-np.inf), c)
        else:
            lg = ct = np.zeros(len(c), bool)
    fuerza = f["adx"] >= p["adx_min"]
    lg, ct = lg & fuerza, ct & fuerza
    if intradia and p["franja"] and config.FRANJAS:
        ok = np.zeros(len(c), bool)
        for a, b in config.FRANJAS:
            ok |= (f["hora"] >= a) & (f["hora"] < b)
        lg, ct = lg & ok, ct & ok
    if p["sentido"] == "largos":
        ct = np.zeros_like(ct)
    elif p["sentido"] == "cortos":
        lg = np.zeros_like(lg)
    lg[:210] = False
    ct[:210] = False
    return lg, ct


def backtest(f, p, coste, intradia, desde=0, hasta=None):
    """Simula operación a operación. Devuelve lista de trades con resultado en R.
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
            if j > i + 1:
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
        "n": int(len(r)), "esperanza": float(r.mean()), "acierto": float(len(g) / len(r)),
        "gana_med": float(g.mean()) if len(g) else 0.0, "pierde_med": float(p.mean()) if len(p) else 0.0,
        "pf": float(min(g.sum() / -p.sum(), 99.0)) if p.sum() < 0 else 99.0, "max_dd": dd,
        "sqn": float(r.mean() / sd * np.sqrt(min(len(r), 100))) if sd > 0 else 0.0, "total_R": float(r.sum()),
    }


def puntuar(m, min_trades):
    if m["n"] < min_trades or m["pf"] < 1.0 or m["acierto"] < config.ACIERTO_MIN:
        return -9.0
    return m["sqn"] - 0.02 * m["max_dd"]


def describir(p, intradia):
    e = f"EMA{p['ema']}"
    ent = {
        "cruce": f"cruce del precio con la {e}",
        "apoyo": f"rebote en la {e} con cierre a favor",
        "ruptura": f"ruptura del máximo/mínimo de {p['ruptura_n']} velas a favor de la {e}",
        "rsi": f"RSI sale de {p['rsi_nivel']} (o {100 - p['rsi_nivel']}) a favor de la {e}",
        "bollinger": f"vuelta dentro de la banda de Bollinger a favor de la {e}",
        "macd": f"cruce del MACD a favor de la {e}",
        "inside": f"ruptura de inside bar a favor de la {e}",
        "orb": f"ruptura del rango de la vela de las {p['orb_hora']}h (Madrid) a favor de la {e}",
    }[p["entrada"]]
    txt = f"{p['sentido'].capitalize()}: {ent}"
    if p["adx_min"]:
        txt += f", solo si ADX ≥ {p['adx_min']}"
    txt += f". SL {p['sl_atr']}×ATR, TP {p['tp_r']}R, cierre a las {p['max_velas']} velas"
    if intradia and p["franja"] and config.FRANJAS:
        txt += ", solo en tus horarios (" + ", ".join(f"{a}-{b}h" for a, b in config.FRANJAS) + ")"
    return txt + "."
