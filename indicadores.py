"""Condiciones OBJETIVAS: EMA, ADX, ATR (las del vídeo) + RSI, Bollinger, MACD, inside bar y rango de apertura."""
import numpy as np
import pandas as pd

import config


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def atr(df, n=14):
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def adx(df, n=14):
    up = df["high"].diff()
    dn = -df["low"].diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * pd.Series(pdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    ndi = 100 * pd.Series(ndm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean().fillna(0)


def rsi(s, n=14):
    d = s.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    p = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + g / p.replace(0, np.nan))).fillna(50)


def hora_local(index):
    return pd.DatetimeIndex(index).tz_localize("UTC").tz_convert(config.ZONA)


EMAS = (20, 50, 100, 200)
RUPTURAS = (10, 20, 55)
HORAS_ORB = (9, 15)   # apertura de Londres (9h) y de Nueva York (15h, la vela de las 15:30) en hora de Madrid


def preparar(df):
    """Precalcula todo una vez para que el aprendizaje vaya rápido."""
    c = df["close"]
    loc = hora_local(df.index)
    f = {
        "o": df["open"].values, "h": df["high"].values, "l": df["low"].values, "c": c.values,
        "atr": atr(df).values, "adx": adx(df).values, "rsi": rsi(c).values,
        "hora": loc.hour.values, "t": df.index,
    }
    for n in EMAS:
        f[f"ema{n}"] = ema(c, n).values
    for n in RUPTURAS:
        f[f"hh{n}"] = df["high"].rolling(n).max().shift().values
        f[f"ll{n}"] = df["low"].rolling(n).min().shift().values
    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    f["bb_sup"], f["bb_inf"] = (mid + 2 * sd).values, (mid - 2 * sd).values
    macd = ema(c, 12) - ema(c, 26)
    f["macd"], f["macd_sig"] = macd.values, ema(macd, 9).values
    h, l = df["high"], df["low"]
    f["inside_prev"] = ((h.shift(1) < h.shift(2)) & (l.shift(1) > l.shift(2))).values
    # Rango de apertura (solo tiene sentido en H1)
    fecha = pd.Series(loc.date, index=df.index)
    for hh in HORAS_ORB:
        es = loc.hour == hh
        alto = pd.Series(np.where(es, h, np.nan), index=df.index).groupby(fecha.values).transform("max")
        bajo = pd.Series(np.where(es, l, np.nan), index=df.index).groupby(fecha.values).transform("min")
        despues = loc.hour > hh
        f[f"orb_h{hh}"] = np.where(despues, alto.values, np.nan)
        f[f"orb_l{hh}"] = np.where(despues, bajo.values, np.nan)
    return f
