"""
CONFIGURACIÓN DEL ROBOT — edita aquí tus activos, riesgo y horario.
Todo lo demás se aprende solo.
"""

# ---------------------------------------------------------------------------
# ACTIVOS A ESTUDIAR
#   mt5    -> nombre del símbolo en tu MetaTrader 5 (XM/FundedNext pueden variar:
#             "GOLD" o "XAUUSD", "US100Cash" o "NDX100"... mira tu Market Watch)
#   yahoo  -> ticker de respaldo si no hay MT5 abierto
#   coste  -> spread + comisión aproximados, en unidades de PRECIO
#   valor_lote -> $ que gana/pierde 1 lote si el precio se mueve 1,0 (tamaño de contrato).
#             Compruébalo en MT5: clic derecho en el símbolo > Especificación > Tamaño del contrato
# ---------------------------------------------------------------------------
ACTIVOS = {
    "EURUSD": {"mt5": "EURUSD",  "yahoo": "EURUSD=X", "coste": 0.00012, "valor_lote": 100000},
    "GBPUSD": {"mt5": "GBPUSD",  "yahoo": "GBPUSD=X", "coste": 0.00018, "valor_lote": 100000},
    "XAUUSD": {"mt5": "GOLD",    "yahoo": "GC=F",     "coste": 0.35, "valor_lote": 100},
    "NDX100": {"mt5": "US100Cash", "yahoo": "^NDX",   "coste": 1.5, "valor_lote": 1},
    "BTCUSD": {"mt5": "BTCUSD",  "yahoo": "BTC-USD",  "coste": 30.0, "valor_lote": 1},
}

# Temporalidades que estudia. D1 = varios años; H1 = últimos ~2 años.
TEMPORALIDADES = {
    "D1": {"anios": 10, "entreno_dias": 3 * 365, "prueba_dias": 365},
    "H1": {"anios": 2,  "entreno_dias": 270,     "prueba_dias": 90},
}

# ---------------------------------------------------------------------------
# TU HORARIO (regla del vídeo: elige UNA franja que encaje en tu rutina)
# En hora UTC. El vídeo recomienda 14:30-16:30 UTC+2  ->  12:30-14:30 UTC.
# Pon None para no filtrar por hora.
# ---------------------------------------------------------------------------
FRANJA_UTC = (12, 15)          # opera señales H1 solo entre 12:00 y 15:00 UTC
DESFASE_BROKER_UTC = 2          # XM/FundedNext suelen ir en GMT+2 (GMT+3 en verano)

# ---------------------------------------------------------------------------
# RIESGO (regla del vídeo: limitar pérdidas Y ganancias)
# ---------------------------------------------------------------------------
import os
BALANCE = float(os.environ.get("BALANCE", 10_000))   # tu cuenta (en la nube se pone como secreto)
RIESGO_POR_TRADE = 0.01         # 1 % = 1R
MAX_PERDIDAS_DIA = 2            # tras 2 stops en el día, se acabó
MAX_TRADES_DIA = 3
# Objetivo de ganancias: se para el día que ganes lo que la estrategia
# espera ganar en UNA SEMANA (esperanza x trades/semana). Se calcula solo.

# ---------------------------------------------------------------------------
# APRENDIZAJE
# ---------------------------------------------------------------------------
CANDIDATOS_ALEATORIOS = 250     # estrategias que prueba en cada ventana
GENERACIONES = 3                # rondas de mutación de las mejores
MIN_TRADES_ENTRENO = 30
UMBRAL_APROBACION_R = 0.05      # esperanza fuera de muestra mínima para "aprobar"
SEMILLA = 7

# ---------------------------------------------------------------------------
# MÓVIL: avisos por Telegram y web (se rellenan como "secretos" en GitHub,
# o como variables de entorno en tu PC). Ver GUIA_MOVIL.md
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
URL_WEB = os.environ.get("URL_WEB", "")
