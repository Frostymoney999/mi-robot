"""Avisos al móvil por Telegram. Sin dependencias extra (usa urllib)."""
import json
import urllib.parse
import urllib.request

import config
import riesgo


def _mandar(texto):
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    datos = {"chat_id": config.TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "HTML",
             "disable_web_page_preview": "true"}
    if config.URL_WEB:
        datos["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "📱 Abrir mi robot", "url": config.URL_WEB}]]})
    try:
        urllib.request.urlopen(url, data=urllib.parse.urlencode(datos).encode(), timeout=20)
        return True
    except Exception as e:
        print(f"  ! Telegram: {e}")
        return False


def _num(x):
    return f"{x:,.5g}" if abs(x) < 100 else f"{x:,.2f}"


def _senal(s):
    flecha = "🟢 COMPRA" if s["dir"] == "LARGO" else "🔴 VENTA"
    aviso = "" if s["estado"] == "APROBADA" else "\n⚠️ <i>En observación: solo para seguir en demo</i>"
    lotes = f"\nLotes (1R = {riesgo.valor_R():,.0f}$): <b>{s['lotes']}</b>" if s.get("lotes") else ""
    return (f"{flecha} <b>{s['activo']}</b> · {s['tf']}\n"
            f"Entrada ≈ <b>{_num(s['entrada'])}</b>\nStop: {_num(s['sl'])}\nTake profit: {_num(s['tp'])}{lotes}"
            f"\n<i>{s['regla']}</i>{aviso}")


def enviar(ctx, resumen=False):
    obs = config.AJUSTES.get("avisos_observacion")
    validas = [s for s in ctx["senales"] if obs or s["estado"] == "APROBADA"]
    nuevas = [s for s in validas if s.get("nueva")]
    if not resumen and not nuevas:
        print("  · Telegram: sin señales nuevas, no se envía nada")
        return
    p = ctx["plan"]
    partes = []
    if resumen:
        lineas = ["☀️ <b>Informe premercado</b>"]
        for a in ctx["activos"]:
            e = a.get("estado")
            if e:
                lineas.append(f"{a['nombre']}: {e['tendencia_ema50'].lower()} · ADX {e['adx']} · {e['cambio_5d_%']:+.2f}% 5d")
        lineas.append(f"\n🛑 Paras si pierdes {config.MAX_PERDIDAS_DIA} trades ({config.MAX_PERDIDAS_DIA * riesgo.valor_R():,.0f}$)")
        if p["objetivo_R"] > 0:
            lineas.append(f"🎯 Paras si ganas {p['objetivo_R']}R ({p['objetivo_R'] * riesgo.valor_R():,.0f}$)")
        lineas.append(f"\n{'📣 ' + str(len(validas)) + ' señal(es) hoy' if validas else '😴 Sin señales aprobadas: no operar también es operar'}")
        partes.append("\n".join(lineas))
    for s in (validas if resumen else nuevas):
        partes.append(_senal(s))
    if ctx.get("demo"):
        partes[0] = "🧪 <b>MODO DEMO</b> (datos inventados)\n\n" + partes[0]
    ok = _mandar("\n\n".join(partes))
    print("  · Telegram: enviado" if ok else "  · Telegram: no configurado (ver GUIA_MOVIL.md)")
