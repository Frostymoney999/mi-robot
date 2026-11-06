"""Exporta todo a docs/datos.json para la app móvil (docs/index.html).
La carpeta docs/ es la que GitHub Pages publica como web."""
import json
import math
import os
import shutil
from datetime import datetime, timezone

import numpy as np

import config
from estrategia import backtest, describir
from indicadores import ema

BASE = os.path.dirname(__file__)
DOCS = os.path.join(BASE, "docs")
os.makedirs(DOCS, exist_ok=True)


def serie_precio(df, n=160):
    d = df.iloc[-n:]
    e = ema(df["close"], 50).iloc[-n:]
    return {"t": [str(x)[:10] for x in d.index], "c": [float(x) for x in d["close"]], "ema50": [float(x) for x in e]}


def curva(f, p, coste, intradia, puntos=150):
    tr = backtest(f, p, coste, intradia)
    if not tr:
        return {"t": [], "R": []}
    eq = np.cumsum([t["R"] for t in tr])
    idx = np.linspace(0, len(eq) - 1, min(puntos, len(eq))).astype(int)
    return {"t": [str(f["t"][tr[i]["salida"]])[:10] for i in idx], "R": [round(float(eq[i]), 2) for i in idx]}


def _limpio(o):
    if isinstance(o, dict):
        return {str(k): _limpio(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_limpio(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if math.isnan(o) or math.isinf(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def exportar(ctx):
    activos = []
    for a in ctx["activos"]:
        info = config.ACTIVOS[a["nombre"]]
        estr = []
        for tf, r in a["registros"].items():
            estr.append({
                "tf": tf, "estado": r["estado"], "regla": describir(r["params"], tf == "H1"),
                "actualizado": r["actualizado"], "motivo": r["motivo"],
                "oos": r["fuera_de_muestra"], "hist": r["historico_completo"], "mc": r["monte_carlo"],
                "trades_semana": r["trades_por_semana"], "ventanas": r["ventanas"],
                "reales": r.get("reales", {}), "curva": r.get("curva", {}), "degradada": r.get("degradada", False),
                "laboratorio": r.get("laboratorio", {}), "familia": r["params"]["entrada"],
            })
        activos.append({
            "nombre": a["nombre"], "titulo": info["nombre"], "cat": info["cat"],
            "valor_lote": a.get("valor_lote", info["valor_lote"]), "simbolo": info["mt5"],
            "estado": a.get("estado"), "precio": a.get("precio"),
            "anual": a["anual"].to_dict("records") if a.get("anual") is not None else [],
            "horas": {int(k): float(v) for k, v in a["horas"].items()} if a.get("horas") is not None else {},
            "estrategias": estr,
        })
    senales = [{k: s[k] for k in ("activo", "tf", "dir", "entrada", "sl", "tp", "dist_sl", "estado", "regla", "vela")}
               for s in ctx["senales"]]
    datos = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "demo": ctx["demo"],
        "config": {"riesgo": config.RIESGO_POR_TRADE, "max_perdidas_dia": config.MAX_PERDIDAS_DIA,
                   "max_trades_dia": config.MAX_TRADES_DIA, "franjas": config.FRANJAS},
        "ajustes": config.AJUSTES,
        "catalogo": {k: {"cat": v["cat"], "nombre": v["nombre"]} for k, v in config.CATALOGO.items()},
        "temporalidades": {k: v["nombre"] for k, v in config.TEMPORALIDADES_TODAS.items()},
        "familias": config.FAMILIAS,
        "plan": {k: ctx["plan"][k] for k in ("objetivo_R", "esperanza_media", "trades_semana")},
        "senales": senales,
        "activos": activos,
        "seguimiento": [{k: s.get(k) for k in ("vela", "activo", "tf", "dir", "estado", "R")} for s in ctx["seguimiento"][-40:]],
    }
    ruta = os.path.join(DOCS, "datos.json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(_limpio(datos), fh, ensure_ascii=False)
    # copia como .js para que la app también funcione abriéndola con doble clic en el PC
    with open(os.path.join(DOCS, "datos.js"), "w", encoding="utf-8") as fh:
        fh.write("window.DATOS = " + json.dumps(_limpio(datos), ensure_ascii=False) + ";")
    app = os.path.join(BASE, "app", "index.html")
    if os.path.exists(app):
        shutil.copy(app, os.path.join(DOCS, "index.html"))
    return os.path.join(DOCS, "index.html")
