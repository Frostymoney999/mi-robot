"""
Analiza TU historial de operaciones y separa PÉRDIDAS (parte del juego) de ERRORES
(trades que no debieron existir). Es el ejemplo del vídeo: -6 % -> +4 % solo quitando errores.

Acepta:
  · Exportación de MT5 desde la propia terminal (se lee con la librería MetaTrader5), o
  · un CSV con columnas: apertura, cierre, simbolo, tipo, volumen, precio_entrada, sl, precio_salida, beneficio
    (fechas tipo 2026-11-03 14:35)
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config


def desde_mt5(dias=180):
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("No se pudo conectar con MT5")
    deals = mt5.history_deals_get(datetime.now() - timedelta(days=dias), datetime.now())
    if not deals:
        return pd.DataFrame()
    d = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    d["time"] = pd.to_datetime(d["time"], unit="s") - pd.Timedelta(hours=config.DESFASE_BROKER_UTC)
    filas = []
    for pid, g in d[d["position_id"] > 0].groupby("position_id"):
        ent, sal = g[g["entry"] == 0], g[g["entry"] == 1]
        if ent.empty or sal.empty:
            continue
        e, s = ent.iloc[0], sal.iloc[-1]
        orden = mt5.history_orders_get(position=int(pid))
        sl = orden[0].sl if orden else 0.0
        filas.append({"apertura": e["time"], "cierre": s["time"], "simbolo": e["symbol"],
                      "tipo": "buy" if e["type"] == 0 else "sell", "volumen": e["volume"],
                      "precio_entrada": e["price"], "sl": sl, "precio_salida": s["price"],
                      "beneficio": g["profit"].sum() + g["commission"].sum() + g["swap"].sum()})
    return pd.DataFrame(filas)


def desde_csv(ruta):
    df = pd.read_csv(ruta)
    df.columns = [c.strip().lower() for c in df.columns]
    df["apertura"] = pd.to_datetime(df["apertura"])
    df["cierre"] = pd.to_datetime(df["cierre"])
    return df


def analizar(df):
    df = df.sort_values("apertura").reset_index(drop=True)
    riesgo = config.BALANCE * config.RIESGO_POR_TRADE
    vol_med = df["volumen"].median()
    errores = [[] for _ in range(len(df))]

    for i, t in df.iterrows():
        # 1) fuera de tu franja
        if config.FRANJA_UTC:
            a, b = config.FRANJA_UTC
            if not (a <= t["apertura"].hour < b):
                errores[i].append("fuera de horario")
        # 2) sin stop loss
        if not t.get("sl") or t["sl"] == 0:
            errores[i].append("sin stop loss")
        # 3) tamaño excesivo
        if t["volumen"] > 1.5 * vol_med:
            errores[i].append("tamaño de más")
        # 4) pérdida mayor que 1R (stop movido / sin respetar)
        if t["beneficio"] < -1.5 * riesgo:
            errores[i].append("pérdida > 1,5R (¿stop movido?)")
        # 5) trade de venganza: abierto <30 min tras cerrar una pérdida
        prev = df[(df["cierre"] <= t["apertura"]) & (df["cierre"] > t["apertura"] - pd.Timedelta(minutes=30))
                  & (df["beneficio"] < 0)]
        if len(prev):
            errores[i].append("venganza (<30 min tras pérdida)")
        # 6) sobreoperar: superó límites del día
        mismo_dia = df[(df["apertura"].dt.date == t["apertura"].date()) & (df["apertura"] < t["apertura"])]
        if len(mismo_dia) >= config.MAX_TRADES_DIA:
            errores[i].append("sobreoperar (límite de trades)")
        elif (mismo_dia["beneficio"] < 0).sum() >= config.MAX_PERDIDAS_DIA:
            errores[i].append("siguió tras el stop diario")

    df["errores"] = [", ".join(e) for e in errores]
    df["es_error"] = df["errores"] != ""
    df["R"] = df["beneficio"] / riesgo

    def res(x):
        return {"trades": len(x), "beneficio": round(x["beneficio"].sum(), 2),
                "esperanza_R": round(x["R"].mean(), 3) if len(x) else 0.0,
                "acierto_%": round((x["beneficio"] > 0).mean() * 100, 1) if len(x) else 0.0}

    tipos = pd.Series([e for lst in errores for e in lst]).value_counts()
    coste_err = {}
    for tipo in tipos.index:
        sub = df[df["errores"].str.contains(tipo, regex=False)]
        coste_err[tipo] = {"veces": int(tipos[tipo]), "resultado": round(sub["beneficio"].sum(), 2)}

    por_hora = df.groupby(df["apertura"].dt.hour)["R"].agg(["count", "mean", "sum"]).round(2)
    por_dia = df.groupby(df["apertura"].dt.day_name())["R"].agg(["count", "mean", "sum"]).round(2)
    por_simbolo = df.groupby("simbolo")["R"].agg(["count", "mean", "sum"]).round(2)
    # racha: ¿empeoras después de ganar o de perder?
    df["prev"] = df["beneficio"].shift()
    tras_ganar = df[df["prev"] > 0]["R"].mean()
    tras_perder = df[df["prev"] < 0]["R"].mean()

    return {
        "todo": res(df), "sin_errores": res(df[~df["es_error"]]), "solo_errores": res(df[df["es_error"]]),
        "errores": coste_err, "por_hora": por_hora, "por_dia": por_dia, "por_simbolo": por_simbolo,
        "tras_ganar_R": round(float(tras_ganar), 3) if not np.isnan(tras_ganar) else None,
        "tras_perder_R": round(float(tras_perder), 3) if not np.isnan(tras_perder) else None,
        "tabla": df,
    }


def imprimir(a):
    print("\n=== TU DIARIO ===")
    for k, n in [("todo", "Todas las operaciones"), ("sin_errores", "Quitando los errores"), ("solo_errores", "Solo los errores")]:
        r = a[k]
        print(f"  {n:<24} {r['trades']:>4} trades · {r['beneficio']:>10.2f} · {r['esperanza_R']:+.3f}R/trade · acierto {r['acierto_%']}%")
    print("\n  Lo que te cuestan tus errores:")
    for t, v in sorted(a["errores"].items(), key=lambda x: x[1]["resultado"]):
        print(f"    - {t:<34} {v['veces']:>3} veces  -> {v['resultado']:>9.2f}")
    if a["tras_ganar_R"] is not None:
        print(f"\n  Después de ganar rindes {a['tras_ganar_R']:+.2f}R/trade; después de perder {a['tras_perder_R']:+.2f}R/trade")
