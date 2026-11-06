"""Condiciones OBJETIVAS del vídeo: EMA (tendencia), ADX (¿hay tendencia?), ATR (volatilidad/SL/TP)."""
import numpy as np
import pandas as pd


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


EMAS = (20, 50, 100, 200)
RUPTURAS = (10, 20, 55)


def preparar(df):
    """Precalcula todo una vez para que el aprendizaje vaya rápido."""
    f = {
        "o": df["open"].values, "h": df["high"].values, "l": df["low"].values, "c": df["close"].values,
        "atr": atr(df).values, "adx": adx(df).values,
        "hora": df.index.hour.values, "t": df.index,
    }
    for n in EMAS:
        f[f"ema{n}"] = ema(df["close"], n).values
    for n in RUPTURAS:
        f[f"hh{n}"] = df["high"].rolling(n).max().shift().values
        f[f"ll{n}"] = df["low"].rolling(n).min().shift().values
    return f
