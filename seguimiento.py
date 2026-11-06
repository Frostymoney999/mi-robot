"""Registra cada señal que da el robot y, días después, comprueba cómo acabó.
Si la realidad va peor de lo que prometía el backtest, marca la estrategia como degradada."""
import json
import os

import numpy as np

from estrategia import backtest, clave, senales

RUTA = os.path.join(os.path.dirname(__file__), "memoria", "senales.json")


def _cargar():
    if os.path.exists(RUTA):
        with open(RUTA, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def _guardar(s):
    with open(RUTA, "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2, ensure_ascii=False, default=str)


def senal_actual(f, p, intradia):
    lg, ct = senales(f, p, intradia)
    i = len(f["c"]) - 1
    if not (lg[i] or ct[i]):
        return None
    d = 1 if lg[i] else -1
    ent = f["c"][i]
    dist = p["sl_atr"] * f["atr"][i]
    return {"vela": str(f["t"][i]), "dir": "LARGO" if d == 1 else "CORTO", "entrada": ent,
            "sl": ent - d * dist, "tp": ent + d * p["tp_r"] * dist, "dist_sl": dist}


def registrar(activo, tf, p, s):
    todas = _cargar()
    if any(x["activo"] == activo and x["tf"] == tf and x["vela"] == s["vela"] for x in todas):
        return False
    todas.append({"activo": activo, "tf": tf, "params": p, "clave": str(clave(p)),
                  "estado": "abierta", **{k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in s.items()}})
    _guardar(todas)
    return True


def resolver(activo, tf, f, coste):
    """Cierra las señales abiertas cuyo resultado ya se conoce."""
    todas, cambios = _cargar(), 0
    for s in todas:
        if s["activo"] != activo or s["tf"] != tf or s["estado"] != "abierta":
            continue
        i = f["t"].searchsorted(np.datetime64(s["vela"]))
        if i >= len(f["c"]) or str(f["t"][i])[:16] != s["vela"][:16]:
            continue
        tr = backtest(f, s["params"], coste, tf == "H1", desde=i, hasta=len(f["c"]))
        if tr and tr[0]["i"] == i and tr[0]["salida"] < len(f["c"]) - 1:
            s["estado"], s["R"] = "cerrada", round(tr[0]["R"], 3)
            cambios += 1
    if cambios:
        _guardar(todas)
    return todas


def revisar_degradacion(activo, tf, registro):
    """Compara resultados reales con lo esperado. Devuelve True si hay que reaprender."""
    reales = [s["R"] for s in _cargar() if s["activo"] == activo and s["tf"] == tf
              and s["estado"] == "cerrada" and s["clave"] == str(clave(registro["params"]))]
    registro["reales"] = {"n": len(reales), "esperanza": round(float(np.mean(reales)), 3) if reales else None}
    if len(reales) < 10:
        return False
    esperado = registro["fuera_de_muestra"]["esperanza"]
    ee = np.std(reales, ddof=1) / np.sqrt(len(reales))
    degradada = np.mean(reales) < 0 and np.mean(reales) < esperado - 2 * ee
    registro["degradada"] = bool(degradada)
    return bool(degradada)


def historial():
    return _cargar()
