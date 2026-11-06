"""Estudia cómo se ha comportado cada mercado año a año y hora a hora."""
import numpy as np
import pandas as pd

from indicadores import adx, atr, ema


def ratio_varianza(r, k=5):
    """>1 = el mercado tiende a seguir (tendencial); <1 = tiende a revertir (rango)."""
    r = r.dropna()
    if len(r) < k * 10:
        return np.nan
    rk = r.rolling(k).sum().dropna()
    return float(rk.var() / (k * r.var()))


def por_anio(df):
    """Tabla anual con datos diarios."""
    d = df.copy()
    d["ret"] = np.log(d["close"]).diff()
    d["adx"] = adx(d)
    d["atrp"] = atr(d) / d["close"] * 100
    d["sobre200"] = d["close"] > ema(d["close"], 200)
    filas = []
    for anio, g in d.groupby(d.index.year):
        if len(g) < 60:
            continue
        eq = g["close"] / g["close"].cummax() - 1
        vr = ratio_varianza(g["ret"])
        filas.append({
            "Año": anio,
            "Rentab. %": round((g["close"].iloc[-1] / g["close"].iloc[0] - 1) * 100, 1),
            "Volat. anual %": round(g["ret"].std() * np.sqrt(252) * 100, 1),
            "ATR medio %": round(g["atrp"].mean(), 2),
            "Días en tendencia (ADX>25) %": round((g["adx"] > 25).mean() * 100),
            "Días sobre EMA200 %": round(g["sobre200"].mean() * 100),
            "Caída máx. %": round(eq.min() * 100, 1),
            "Carácter": "tendencial" if vr > 1.08 else ("de rango" if vr < 0.92 else "mixto"),
        })
    return pd.DataFrame(filas)


def por_hora(df_h1):
    """Rango medio de la vela por hora UTC (relativo a la media) -> cuándo se mueve de verdad."""
    rng = (df_h1["high"] - df_h1["low"]) / df_h1["close"]
    s = rng.groupby(df_h1.index.hour).mean()
    return (s / s.mean()).round(2)


def estado_actual(df):
    """Foto de hoy con condiciones objetivas."""
    c = df["close"]
    e50, e200 = ema(c, 50).iloc[-1], ema(c, 200).iloc[-1]
    a, ax = atr(df).iloc[-1], adx(df).iloc[-1]
    ult = df.iloc[-1]
    sem = df.iloc[-5:]
    return {
        "cierre": float(ult["close"]),
        "tendencia_ema50": "ALCISTA" if ult["close"] > e50 else "BAJISTA",
        "tendencia_ema200": "ALCISTA" if ult["close"] > e200 else "BAJISTA",
        "adx": round(float(ax), 1),
        "hay_tendencia": "Sí" if ax >= 25 else ("Débil" if ax >= 20 else "No (rango)"),
        "atr": float(a),
        "max_anterior": float(ult["high"]), "min_anterior": float(ult["low"]),
        "max_semana": float(sem["high"].max()), "min_semana": float(sem["low"].min()),
        "cambio_5d_%": round(float((c.iloc[-1] / c.iloc[-6] - 1) * 100), 2) if len(c) > 6 else 0.0,
    }
