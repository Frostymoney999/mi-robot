"""Descarga y cachea históricos. Orden: MetaTrader 5 -> Yahoo Finance -> CSV en cache."""
import os
import zlib
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import config

CARPETA = os.path.join(os.path.dirname(__file__), "datos")
os.makedirs(CARPETA, exist_ok=True)


def _ruta(activo, tf):
    return os.path.join(CARPETA, f"{activo}_{tf}.csv")


def _desde_mt5(simbolo, tf, anios):
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None
    if not mt5.initialize():
        return None
    mapa = {"D1": mt5.TIMEFRAME_D1, "H4": mt5.TIMEFRAME_H4, "H1": mt5.TIMEFRAME_H1}
    mt5.symbol_select(simbolo, True)
    hasta = datetime.now(timezone.utc)
    desde = hasta - timedelta(days=365 * anios)
    r = mt5.copy_rates_range(simbolo, mapa[tf], desde, hasta)
    if r is None or len(r) == 0:
        return None
    df = pd.DataFrame(r)
    df["time"] = pd.to_datetime(df["time"], unit="s") - pd.Timedelta(hours=config.DESFASE_BROKER_UTC)
    df = df.rename(columns={"tick_volume": "volume"}).set_index("time")
    return df[["open", "high", "low", "close", "volume"]]


def _desde_yahoo(ticker, tf, anios):
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        if tf == "D1":
            df = yf.download(ticker, period=f"{anios}y", interval="1d", progress=False, auto_adjust=False)
        else:
            df = yf.download(ticker, period="729d", interval="1h", progress=False, auto_adjust=False)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    df = df.dropna()
    if tf == "H4":
        df = a_h4(df)
    return df


def a_h4(df):
    """Agrupa velas de 1 hora en velas de 4 horas."""
    return df.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def demo(activo, tf, anios):
    """Serie sintética con regímenes (tendencia / rango / volatilidad) para probar el robot."""
    rng = np.random.default_rng(zlib.crc32(f"{activo}{tf}".encode()))
    por_dia = {"D1": 1, "H4": 6, "H1": 24}[tf]
    n = (252 if tf == "D1" else 260 * por_dia) * anios
    precio0 = {"EURUSD": 1.1, "GBPUSD": 1.3, "XAUUSD": 1900, "NDX100": 15000, "BTCUSD": 40000, "USDJPY": 150}.get(activo, 100)
    vol = 0.006 / por_dia ** 0.5
    deriva = np.zeros(n)
    i = 0
    while i < n:
        largo = rng.integers(40, 300)
        deriva[i:i + largo] = rng.choice([-1, 0, 0, 1]) * vol * rng.uniform(0.05, 0.25)
        i += largo
    sig = vol * np.exp(np.cumsum(rng.normal(0, 0.02, n)) * 0.5).clip(0.5, 2.5)
    r = deriva + sig * rng.standard_t(4, n) / 1.4
    close = precio0 * np.exp(np.cumsum(r))
    open_ = np.r_[precio0, close[:-1]]
    rango = np.abs(rng.normal(0, sig, n)) * close
    high = np.maximum(open_, close) + rango * 0.6
    low = np.minimum(open_, close) - rango * 0.6
    freq = {"D1": "B", "H4": "4h", "H1": "h"}[tf]
    idx = pd.date_range(end=pd.Timestamp.utcnow().floor("D").tz_localize(None), periods=n, freq=freq)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(100, 1000, n)}, index=idx)


def cargar(activo, tf, modo_demo=False, refrescar=True):
    """Devuelve un DataFrame OHLCV con índice en UTC."""
    info = config.CATALOGO[activo]
    anios = config.TEMPORALIDADES[tf]["anios"]
    if modo_demo:
        return demo(activo, tf, anios)
    df = None
    if refrescar:
        df = _desde_mt5(info["mt5"], tf, anios)
        fuente = "MT5"
        if df is None:
            df = _desde_yahoo(info["yahoo"], tf, anios)
            fuente = "Yahoo"
        if df is not None and len(df) > 100:
            df.to_csv(_ruta(activo, tf))
            print(f"  · {activo} {tf}: {len(df)} velas desde {fuente}")
            return df
    if os.path.exists(_ruta(activo, tf)):
        df = pd.read_csv(_ruta(activo, tf), index_col=0, parse_dates=True)
        print(f"  · {activo} {tf}: {len(df)} velas desde cache")
        return df
    print(f"  ! {activo} {tf}: sin datos (abre MT5 o revisa el símbolo en config.py)")
    return None
