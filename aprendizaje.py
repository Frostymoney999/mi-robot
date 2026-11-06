"""
El "cerebro". Aprende solo así:

1. WALK-FORWARD: corta la historia en ventanas. En cada una, entrena con el pasado
   (busca la mejor estrategia) y la pone a prueba en el periodo SIGUIENTE que no ha visto.
   Solo cuenta lo que gana fuera de muestra -> así no se engaña con el sobreajuste.
2. BÚSQUEDA EVOLUTIVA: prueba cientos de combinaciones al azar, se queda con las mejores
   y las "muta" varias generaciones.
3. MONTE CARLO: baraja miles de veces los trades fuera de muestra para ver si la
   esperanza positiva aguanta o fue suerte.
4. CAMPEÓN vs RETADOR: guarda en memoria la estrategia vigente. Cada vez que reaprende,
   la nueva solo la sustituye si lo hace mejor en el periodo más reciente.
5. AUTOVIGILANCIA: si las señales reales que ha dado empiezan a fallar más de lo
   esperado, se marca "degradada" y se reaprende sola.
"""
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd

import config
from estrategia import aleatoria, backtest, clave, metricas, mutar, puntuar, valida

MEMORIA = os.path.join(os.path.dirname(__file__), "memoria", "conocimiento.json")
os.makedirs(os.path.dirname(MEMORIA), exist_ok=True)


def cargar_memoria():
    if os.path.exists(MEMORIA):
        with open(MEMORIA, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def guardar_memoria(m):
    with open(MEMORIA, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, ensure_ascii=False, default=str)


def _buscar(f, coste, intradia, desde, hasta, rng, semillas=()):
    """Búsqueda evolutiva dentro de [desde, hasta). Devuelve lista ordenada (nota, params, métricas).
    Garantiza que cada familia de estrategia recibe su parte de candidatos."""
    semillas = [dict(s) for s in semillas if s and valida(s, intradia)]
    pob = semillas + [aleatoria(rng, intradia) for _ in range(config.CANDIDATOS_ALEATORIOS)]
    vistos = {}
    for gen in range(config.GENERACIONES + 1):
        for p in pob:
            k = clave(p)
            if k in vistos:
                continue
            m = metricas(backtest(f, p, coste, intradia, desde, hasta))
            vistos[k] = (puntuar(m, config.MIN_TRADES_ENTRENO), p, m)
        orden = sorted(vistos.values(), key=lambda x: -x[0])
        top = orden[:12]
        # además, las 2 mejores de cada familia para que ninguna se quede sin explorar
        por_fam = {}
        for x in orden:
            por_fam.setdefault(x[1]["entrada"], []).append(x)
        top += [x for lst in por_fam.values() for x in lst[:2]]
        pob = [mutar(p, rng, intradia) for _, p, _ in top for _ in range(4)]
    return sorted(vistos.values(), key=lambda x: -x[0])


def _ventanas(t, tf):
    cfg = config.TEMPORALIDADES[tf]
    ent, pru = pd.Timedelta(days=cfg["entreno_dias"]), pd.Timedelta(days=cfg["prueba_dias"])
    t = pd.DatetimeIndex(t)
    ini, out = t[0], []
    while ini + ent + pru <= t[-1] + pd.Timedelta(days=1):
        a = t.searchsorted(ini)
        b = t.searchsorted(ini + ent)
        c = t.searchsorted(ini + ent + pru)
        out.append((a, b, min(c, len(t))))
        ini += pru
    return out


def monte_carlo(rs, n=3000, rng=None):
    rng = rng or np.random.default_rng(0)
    rs = np.asarray(rs)
    if len(rs) < 5:
        return {"p5_esperanza": 0.0, "prob_positiva": 0.0}
    medias = rng.choice(rs, (n, len(rs)), replace=True).mean(axis=1)
    return {"p5_esperanza": float(np.percentile(medias, 5)), "prob_positiva": float((medias > 0).mean())}


def aprender(activo, tf, f, coste, memoria, log=print):
    intradia = tf == "H1"
    rng = np.random.default_rng(config.SEMILLA)
    clave_m = f"{activo}_{tf}"
    previo = memoria.get(clave_m, {})
    campeon = previo.get("params")
    if campeon and not valida(campeon, intradia):
        campeon = None   # usa una familia que has desactivado o es de una versión anterior

    ventanas = _ventanas(f["t"], tf)
    if len(ventanas) < 2:
        log(f"    {clave_m}: historia insuficiente para walk-forward")
        return None

    oos, detalle, semillas = [], [], ([campeon] if campeon else [])
    lab = {}   # laboratorio: resultado fuera de muestra de la MEJOR estrategia de cada familia
    for k, (a, b, c) in enumerate(ventanas):
        ranking = _buscar(f, coste, intradia, a, b, rng, semillas)
        nota, mejor, m_ent = ranking[0]
        vistas = set()
        for nt, p, _ in ranking:
            fam = p["entrada"]
            if fam in vistas or nt <= -9:
                continue
            vistas.add(fam)
            lab.setdefault(fam, []).extend(t["R"] for t in backtest(f, p, coste, intradia, b, c))
        tr = backtest(f, mejor, coste, intradia, b, c)
        m_oos = metricas(tr)
        oos += [t["R"] for t in tr]
        detalle.append({"entreno_hasta": str(f["t"][b - 1])[:10], "prueba_hasta": str(f["t"][c - 1])[:10],
                        "esperanza_entreno": round(m_ent["esperanza"], 3), "esperanza_prueba": round(m_oos["esperanza"], 3),
                        "trades_prueba": m_oos["n"]})
        semillas = [p for _, p, _ in ranking[:5]]
        log(f"    ventana {k + 1}/{len(ventanas)}  entreno {m_ent['esperanza']:+.2f}R  ->  prueba {m_oos['esperanza']:+.2f}R ({m_oos['n']} trades)")

    # Retador: el mejor entrenado con la ventana más reciente (para operar mañana)
    a_ult = _ventanas(f["t"], tf)[-1][1]
    entreno_desde = max(0, f["t"].searchsorted(f["t"][a_ult - 1] - pd.Timedelta(days=config.TEMPORALIDADES[tf]["entreno_dias"])))
    ranking = _buscar(f, coste, intradia, entreno_desde, len(f["c"]), rng, semillas)
    retador = ranking[0][1]

    # Campeón vs retador en el último periodo de prueba
    a, b, c = ventanas[-1]
    elegido, motivo = retador, "nueva estrategia"
    if campeon:
        n_camp = puntuar(metricas(backtest(f, campeon, coste, intradia, b, c)), 10)
        n_ret = puntuar(metricas(backtest(f, retador, coste, intradia, b, c)), 10)
        if n_camp >= n_ret and not previo.get("degradada"):
            elegido, motivo = campeon, "el campeón anterior sigue siendo mejor"
        else:
            motivo = "el retador supera al campeón anterior" if not previo.get("degradada") else "la anterior estaba degradada"

    m_oos = metricas([{"R": r} for r in oos])
    mc = monte_carlo(oos)
    hist = metricas(backtest(f, elegido, coste, intradia))
    anios = (f["t"][-1] - f["t"][0]).days / 365
    aprobada = (m_oos["esperanza"] >= config.UMBRAL_APROBACION_R and mc["p5_esperanza"] > 0 and m_oos["n"] >= 20
                and m_oos["acierto"] >= config.ACIERTO_MIN - 0.05)

    registro = {
        "actualizado": datetime.now().isoformat(timespec="minutes"),
        "params": elegido,
        "motivo": motivo,
        "estado": "APROBADA" if aprobada else "EN OBSERVACIÓN",
        "fuera_de_muestra": {k: round(v, 3) for k, v in m_oos.items()},
        "monte_carlo": {k: round(v, 3) for k, v in mc.items()},
        "historico_completo": {k: round(v, 3) for k, v in hist.items()},
        "trades_por_semana": round(hist["n"] / max(anios * 52, 1), 2),
        "ventanas": detalle,
        "laboratorio": {fam: {"n": len(rs), "esperanza": round(float(np.mean(rs)), 3) if rs else 0.0,
                              "prob_positiva": round(monte_carlo(rs)["prob_positiva"], 2)}
                        for fam, rs in lab.items()},
        "degradada": False,
        "aprendizajes_previos": (previo.get("aprendizajes_previos", []) + (
            [{"fecha": previo.get("actualizado"), "params": campeon, "estado": previo.get("estado")}] if campeon else []))[-10:],
    }
    memoria[clave_m] = registro
    log(f"    => {registro['estado']}  OOS {m_oos['esperanza']:+.3f}R/trade en {m_oos['n']} trades · "
        f"P(esperanza>0)={mc['prob_positiva']:.0%} · {motivo}")
    return registro
