"""
CONFIGURACIÓN DEL ROBOT
Lo que eliges desde la app (mercados, horarios, estrategias, riesgo) se guarda en ajustes.json
y se carga aquí encima de estos valores por defecto. Normalmente no hace falta tocar este archivo.
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# CATÁLOGO DE MERCADOS
#   mt5        -> nombre en MetaTrader 5 (puede variar según broker)
#   yahoo      -> ticker de datos en la nube
#   coste      -> spread + comisión aproximados, en unidades de precio
#   valor_lote -> $ que gana/pierde 1 lote si el precio se mueve 1,0
#   cotiza     -> "USD" (valor fijo) | "propio" (dividir por su precio, ej. USDJPY) | "USDJPY" (cruces con yen)
# ---------------------------------------------------------------------------
CATALOGO = {
    # Forex
    "EURUSD": {"cat": "Forex", "nombre": "Euro / Dólar", "mt5": "EURUSD", "yahoo": "EURUSD=X", "coste": 0.00012, "valor_lote": 100000, "cotiza": "USD"},
    "GBPUSD": {"cat": "Forex", "nombre": "Libra / Dólar", "mt5": "GBPUSD", "yahoo": "GBPUSD=X", "coste": 0.00018, "valor_lote": 100000, "cotiza": "USD"},
    "AUDUSD": {"cat": "Forex", "nombre": "Australiano / Dólar", "mt5": "AUDUSD", "yahoo": "AUDUSD=X", "coste": 0.00015, "valor_lote": 100000, "cotiza": "USD"},
    "NZDUSD": {"cat": "Forex", "nombre": "Neozelandés / Dólar", "mt5": "NZDUSD", "yahoo": "NZDUSD=X", "coste": 0.0002, "valor_lote": 100000, "cotiza": "USD"},
    "USDJPY": {"cat": "Forex", "nombre": "Dólar / Yen", "mt5": "USDJPY", "yahoo": "JPY=X", "coste": 0.015, "valor_lote": 100000, "cotiza": "propio"},
    "USDCAD": {"cat": "Forex", "nombre": "Dólar / Canadiense", "mt5": "USDCAD", "yahoo": "CAD=X", "coste": 0.0002, "valor_lote": 100000, "cotiza": "propio"},
    "USDCHF": {"cat": "Forex", "nombre": "Dólar / Franco", "mt5": "USDCHF", "yahoo": "CHF=X", "coste": 0.0002, "valor_lote": 100000, "cotiza": "propio"},
    "EURJPY": {"cat": "Forex", "nombre": "Euro / Yen", "mt5": "EURJPY", "yahoo": "EURJPY=X", "coste": 0.02, "valor_lote": 100000, "cotiza": "USDJPY"},
    "GBPJPY": {"cat": "Forex", "nombre": "Libra / Yen", "mt5": "GBPJPY", "yahoo": "GBPJPY=X", "coste": 0.03, "valor_lote": 100000, "cotiza": "USDJPY"},
    # Metales y energía
    "XAUUSD": {"cat": "Materias primas", "nombre": "Oro", "mt5": "GOLD", "yahoo": "GC=F", "coste": 0.35, "valor_lote": 100, "cotiza": "USD"},
    "XAGUSD": {"cat": "Materias primas", "nombre": "Plata", "mt5": "SILVER", "yahoo": "SI=F", "coste": 0.03, "valor_lote": 5000, "cotiza": "USD"},
    "WTI":    {"cat": "Materias primas", "nombre": "Petróleo WTI", "mt5": "OILCash", "yahoo": "CL=F", "coste": 0.04, "valor_lote": 100, "cotiza": "USD"},
    # Índices
    "NDX100": {"cat": "Índices", "nombre": "Nasdaq 100", "mt5": "US100Cash", "yahoo": "^NDX", "coste": 1.5, "valor_lote": 1, "cotiza": "USD"},
    "SP500":  {"cat": "Índices", "nombre": "S&P 500", "mt5": "US500Cash", "yahoo": "^GSPC", "coste": 0.5, "valor_lote": 1, "cotiza": "USD"},
    "DJ30":   {"cat": "Índices", "nombre": "Dow Jones 30", "mt5": "US30Cash", "yahoo": "^DJI", "coste": 2.5, "valor_lote": 1, "cotiza": "USD"},
    "DAX40":  {"cat": "Índices", "nombre": "DAX 40 (Alemania)", "mt5": "GER40Cash", "yahoo": "^GDAXI", "coste": 1.5, "valor_lote": 1.1, "cotiza": "USD"},
    "IBEX35": {"cat": "Índices", "nombre": "IBEX 35 (España)", "mt5": "SPA35Cash", "yahoo": "^IBEX", "coste": 5.0, "valor_lote": 1.1, "cotiza": "USD"},
    # Cripto
    "BTCUSD": {"cat": "Cripto", "nombre": "Bitcoin", "mt5": "BTCUSD", "yahoo": "BTC-USD", "coste": 30.0, "valor_lote": 1, "cotiza": "USD"},
    "ETHUSD": {"cat": "Cripto", "nombre": "Ethereum", "mt5": "ETHUSD", "yahoo": "ETH-USD", "coste": 2.0, "valor_lote": 1, "cotiza": "USD"},
    "SOLUSD": {"cat": "Cripto", "nombre": "Solana", "mt5": "SOLUSD", "yahoo": "SOL-USD", "coste": 0.15, "valor_lote": 1, "cotiza": "USD"},
    "XRPUSD": {"cat": "Cripto", "nombre": "XRP", "mt5": "XRPUSD", "yahoo": "XRP-USD", "coste": 0.003, "valor_lote": 1, "cotiza": "USD"},
}

# Temporalidades disponibles (H4 se construye a partir de H1 si no hay MT5)
TEMPORALIDADES_TODAS = {
    "D1": {"nombre": "Diario (swing, varios días)", "anios": 10, "entreno_dias": 3 * 365, "prueba_dias": 365},
    "H4": {"nombre": "4 horas (1-3 días)", "anios": 2, "entreno_dias": 300, "prueba_dias": 90},
    "H1": {"nombre": "1 hora (intradía)", "anios": 2, "entreno_dias": 270, "prueba_dias": 90},
}

# Familias de estrategias que el robot sabe usar (la "escuela")
FAMILIAS = {
    "cruce":     {"nombre": "Cruce de media", "txt": "Entra cuando el precio cruza la media móvil (EMA). La idea del vídeo: precio encima de la EMA = alcista."},
    "apoyo":     {"nombre": "Rebote en la media", "txt": "En tendencia, el precio vuelve a tocar la EMA, no la rompe y cierra a favor. Entrada en el retroceso."},
    "ruptura":   {"nombre": "Ruptura de máximos", "txt": "A favor de la tendencia, cierra por encima del máximo (o por debajo del mínimo) de las últimas N velas."},
    "rsi":       {"nombre": "RSI en retroceso", "txt": "Tendencia a favor y el RSI sale de sobreventa (o sobrecompra). Compra barato dentro de una subida."},
    "bollinger": {"nombre": "Vuelta a Bollinger", "txt": "El precio se sale de la banda de Bollinger y vuelve a entrar: reversión hacia la media a favor de la tendencia."},
    "macd":      {"nombre": "Cruce MACD", "txt": "El MACD cruza su señal a favor de la tendencia de la EMA. Detecta cambios de impulso."},
    "inside":    {"nombre": "Inside bar", "txt": "Una vela queda dentro de la anterior (compresión) y luego el precio rompe a favor de la tendencia."},
    "orb":       {"nombre": "Ruptura de apertura (ORB)", "txt": "Solo intradía: marca el rango de la primera hora de Londres o Nueva York y entra cuando se rompe."},
}

# ---------------------------------------------------------------------------
# VALORES POR DEFECTO (la app los sobrescribe con ajustes.json)
# Horas en HORA DE MADRID.
# ---------------------------------------------------------------------------
AJUSTES_DEFECTO = {
    "activos": ["EURUSD", "GBPUSD", "XAUUSD", "NDX100", "BTCUSD"],
    "temporalidades": ["D1", "H1"],
    "familias": list(FAMILIAS),
    "franjas": [[14, 17]],          # ventanas [desde, hasta) en hora de Madrid
    "hora_informe": 8,              # hora (Madrid) del informe premercado
    "dias": [1, 2, 3, 4, 5],        # 1 = lunes ... 7 = domingo
    "riesgo": 1.0,                  # % por trade
    "max_perdidas_dia": 2,
    "max_trades_dia": 3,
    "avisos_observacion": False,    # ¿avisar por Telegram de estrategias EN OBSERVACIÓN?
    "intensidad": "normal",         # rapida | normal | profunda (cuántas estrategias prueba)
    "acierto_min": 0,               # % mínimo de operaciones ganadoras exigido (0 = sin mínimo)
}

RUTA_AJUSTES = os.path.join(BASE, "ajustes.json")


def _cargar_ajustes():
    a = dict(AJUSTES_DEFECTO)
    if os.path.exists(RUTA_AJUSTES):
        try:
            with open(RUTA_AJUSTES, encoding="utf-8") as fh:
                a.update(json.load(fh))
        except Exception as e:
            print(f"  ! ajustes.json no válido ({e}), uso valores por defecto")
    a["activos"] = [x for x in a["activos"] if x in CATALOGO] or AJUSTES_DEFECTO["activos"]
    a["temporalidades"] = [x for x in a["temporalidades"] if x in TEMPORALIDADES_TODAS] or ["D1"]
    a["familias"] = [x for x in a["familias"] if x in FAMILIAS] or list(FAMILIAS)
    return a


AJUSTES = _cargar_ajustes()

ACTIVOS = {k: CATALOGO[k] for k in AJUSTES["activos"]}
TEMPORALIDADES = {k: TEMPORALIDADES_TODAS[k] for k in TEMPORALIDADES_TODAS if k in AJUSTES["temporalidades"]}
FRANJAS = [tuple(f) for f in AJUSTES["franjas"]]   # hora de Madrid
ZONA = "Europe/Madrid"
DESFASE_BROKER_UTC = 2          # XM/FundedNext suelen ir en GMT+2 (GMT+3 en verano)

BALANCE = float(os.environ.get("BALANCE") or 10_000)
RIESGO_POR_TRADE = AJUSTES["riesgo"] / 100
MAX_PERDIDAS_DIA = AJUSTES["max_perdidas_dia"]
MAX_TRADES_DIA = AJUSTES["max_trades_dia"]

_INT = {"rapida": (120, 2), "normal": (250, 3), "profunda": (500, 4)}[AJUSTES.get("intensidad", "normal")]
CANDIDATOS_ALEATORIOS, GENERACIONES = _INT
MIN_TRADES_ENTRENO = 30
ACIERTO_MIN = float(AJUSTES.get("acierto_min", 0)) / 100
UMBRAL_APROBACION_R = 0.05
SEMILLA = 7

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
URL_WEB = os.environ.get("URL_WEB", "")


def en_franja(hora_local):
    return any(a <= hora_local < b for a, b in FRANJAS)


def huella_ajustes():
    """Cambia cuando cambias algo que obliga a reaprender."""
    import hashlib
    clave = {k: AJUSTES.get(k) for k in ("activos", "temporalidades", "familias", "franjas", "intensidad", "acierto_min")}
    return hashlib.md5(json.dumps(clave, sort_keys=True).encode()).hexdigest()[:10]
