"""Gestión del riesgo del vídeo: R fijo, límite de pérdidas y límite de GANANCIAS por esperanza."""
import config


def valor_R():
    return config.BALANCE * config.RIESGO_POR_TRADE


def objetivo_parada(esperanza_R, trades_semana):
    """El día que ganes lo que tu estrategia espera ganar en una semana -> paras.
    Ej. del vídeo: 0,20R x 15 trades/semana = 3R; con R=10$ -> 30$."""
    obj_R = max(esperanza_R, 0) * max(trades_semana, 0)
    return round(obj_R, 2), round(obj_R * valor_R(), 2)


def valor_lote(activo, precio, usdjpy=None):
    """$ por lote y por 1,0 de movimiento, corrigiendo pares que no cotizan en dólares."""
    info = config.CATALOGO[activo]
    v = info["valor_lote"]
    if info.get("cotiza") == "propio" and precio:
        return v / precio
    if info.get("cotiza") == "USDJPY":
        return v / (usdjpy or 150.0)
    return v


def lotaje(simbolo_mt5, distancia_sl, valor_lote=None):
    """Tamaño de posición para arriesgar exactamente 1R. Usa MT5 si está abierto; si no, el tamaño de contrato de config."""
    lt = _lotaje_mt5(simbolo_mt5, distancia_sl)
    if lt is None and valor_lote and distancia_sl > 0:
        lt = max(0.01, round(valor_R() / (distancia_sl * valor_lote), 2))
    return lt


def _lotaje_mt5(simbolo_mt5, distancia_sl):
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return None
        info = mt5.symbol_info(simbolo_mt5)
        if info is None or info.trade_tick_size == 0:
            return None
        perdida_por_lote = distancia_sl / info.trade_tick_size * info.trade_tick_value
        lotes = valor_R() / perdida_por_lote
        paso = info.volume_step or 0.01
        return max(info.volume_min, round(int(lotes / paso) * paso, 2))
    except Exception:
        return None


def plan_del_dia(registros):
    """Reglas del día según las estrategias aprobadas."""
    esp, tps = [], 0.0
    for r in registros:
        if r["estado"] == "APROBADA":
            esp.append(r["fuera_de_muestra"]["esperanza"])
            tps += r["trades_por_semana"]
    esperanza = sum(esp) / len(esp) if esp else 0.0
    obj_R, obj_dinero = objetivo_parada(esperanza, tps)
    return {
        "R_dinero": valor_R(),
        "max_perdidas_dia": config.MAX_PERDIDAS_DIA,
        "stop_dia_dinero": round(config.MAX_PERDIDAS_DIA * valor_R(), 2),
        "max_trades_dia": config.MAX_TRADES_DIA,
        "objetivo_R": obj_R, "objetivo_dinero": obj_dinero,
        "esperanza_media": round(esperanza, 3), "trades_semana": round(tps, 1),
    }
