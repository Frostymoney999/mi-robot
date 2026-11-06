"""Genera el informe premercado en HTML (se abre con doble clic en cualquier navegador)."""
import html
import os
from datetime import datetime

import config
from estrategia import describir

CARPETA = os.path.join(os.path.dirname(__file__), "informes")
os.makedirs(CARPETA, exist_ok=True)

CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0e1014;color:#e6e6e6;margin:0;padding:28px;line-height:1.45}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:34px 0 10px;border-bottom:1px solid #2a2f3a;padding-bottom:6px}
h3{font-size:15px;margin:18px 0 6px;color:#b9c2d0}.sub{color:#8a93a3;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0 14px}th,td{padding:6px 9px;border-bottom:1px solid #222733;text-align:left}
th{color:#8a93a3;font-weight:600;background:#151922}.ok{color:#4cd38a}.ko{color:#ff6b6b}.warn{color:#f5c04a}
.card{background:#151922;border:1px solid #232a36;border-radius:10px;padding:14px 16px;margin:10px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.big{font-size:22px;font-weight:700}.tag{display:inline-block;padding:2px 8px;border-radius:20px;font-size:12px;font-weight:600}
.tag.ok{background:#173a28}.tag.warn{background:#3a3216}.tag.ko{background:#3a1717}
pre{background:#151922;border:1px solid #232a36;border-radius:8px;padding:12px;white-space:pre-wrap;font-size:12.5px}
"""


def _fmt(x, nd=5):
    if isinstance(x, float):
        return f"{x:,.{nd}f}" if abs(x) < 50 else f"{x:,.2f}"
    return html.escape(str(x))


def _tabla(df):
    return df.to_html(index=False, border=0, escape=True)


def generar(ctx):
    """ctx: dict con 'activos' (lista), 'plan', 'senales', 'seguimiento', 'demo'."""
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    p = ctx["plan"]
    h = [f"<html><head><meta charset='utf-8'><title>Robot trading · {hoy}</title><style>{CSS}</style></head><body>"]
    h.append(f"<h1>Informe premercado</h1><div class='sub'>{hoy} · generado por tu robot"
             + (" · <b class='warn'>MODO DEMO (datos sintéticos, no operar)</b>" if ctx["demo"] else "") + "</div>")

    # --- Resumen 20 segundos
    n_ap = sum(1 for a in ctx["activos"] for r in a["registros"].values() if r and r["estado"] == "APROBADA")
    h.append("<h2>Resumen en 20 segundos</h2><div class='grid'>")
    h.append(f"<div class='card'><div class='sub'>Señales hoy</div><div class='big'>{len(ctx['senales'])}</div></div>")
    h.append(f"<div class='card'><div class='sub'>Estrategias aprobadas</div><div class='big'>{n_ap}</div></div>")
    h.append(f"<div class='card'><div class='sub'>1R</div><div class='big'>{p['R_dinero']:,.0f} $</div></div>")
    h.append(f"<div class='card'><div class='sub'>Para si pierdes</div><div class='big ko'>-{p['stop_dia_dinero']:,.0f} $</div>"
             f"<div class='sub'>{p['max_perdidas_dia']} stops o {p['max_trades_dia']} trades</div></div>")
    obj = f"+{p['objetivo_dinero']:,.0f} $" if p["objetivo_dinero"] > 0 else "—"
    h.append(f"<div class='card'><div class='sub'>Para si ganas (1 semana de esperanza)</div><div class='big ok'>{obj}</div>"
             f"<div class='sub'>{p['esperanza_media']:+.2f}R × {p['trades_semana']} trades/sem</div></div></div>")

    # --- Señales
    h.append("<h2>Señales de hoy</h2>")
    if ctx["senales"]:
        h.append("<table><tr><th>Activo</th><th>TF</th><th>Dirección</th><th>Entrada aprox.</th><th>Stop</th><th>Take profit</th><th>Lotes (1R)</th><th>Estado</th><th>Regla</th></tr>")
        for s in ctx["senales"]:
            cls = "ok" if s["dir"] == "LARGO" else "ko"
            est = "ok" if s["estado"] == "APROBADA" else "warn"
            h.append(f"<tr><td>{s['activo']}</td><td>{s['tf']}</td><td class='{cls}'><b>{s['dir']}</b></td><td>{_fmt(s['entrada'])}</td>"
                     f"<td>{_fmt(s['sl'])}</td><td>{_fmt(s['tp'])}</td><td>{s['lotes'] or 'abre MT5'}</td>"
                     f"<td><span class='tag {est}'>{s['estado']}</span></td><td class='sub'>{html.escape(s['regla'])}</td></tr>")
        h.append("</table><div class='sub'>Las señales EN OBSERVACIÓN aún no han demostrado ventaja fuera de muestra: solo para seguir en demo.</div>")
    else:
        h.append("<div class='card'>Ninguna estrategia da entrada en la última vela cerrada. <b>No operar también es operar.</b></div>")

    # --- Activos
    for a in ctx["activos"]:
        h.append(f"<h2>{a['nombre']}</h2>")
        e = a.get("estado")
        if e:
            t50 = "ok" if e["tendencia_ema50"] == "ALCISTA" else "ko"
            h.append("<div class='grid'>"
                     f"<div class='card'><div class='sub'>Cierre anterior</div><div class='big'>{_fmt(e['cierre'])}</div><div class='sub'>{e['cambio_5d_%']:+.2f}% en 5 días</div></div>"
                     f"<div class='card'><div class='sub'>Tendencia EMA50 / EMA200</div><div class='big {t50}'>{e['tendencia_ema50']}</div><div class='sub'>EMA200: {e['tendencia_ema200']}</div></div>"
                     f"<div class='card'><div class='sub'>¿Hay tendencia? (ADX)</div><div class='big'>{e['adx']}</div><div class='sub'>{e['hay_tendencia']}</div></div>"
                     f"<div class='card'><div class='sub'>Niveles</div>Máx/mín ayer: {_fmt(e['max_anterior'])} / {_fmt(e['min_anterior'])}<br>"
                     f"Máx/mín semana: {_fmt(e['max_semana'])} / {_fmt(e['min_semana'])}<br>ATR diario: {_fmt(e['atr'])}</div></div>")
        for tf, r in a["registros"].items():
            if not r:
                continue
            est = "ok" if r["estado"] == "APROBADA" else "warn"
            o, mc = r["fuera_de_muestra"], r["monte_carlo"]
            h.append(f"<h3>Estrategia aprendida · {tf} <span class='tag {est}'>{r['estado']}</span></h3>")
            h.append(f"<div class='card'>{html.escape(describir(r['params'], tf != 'D1'))}<br><span class='sub'>Actualizada {r['actualizado']} · {html.escape(r['motivo'])}</span></div>")
            h.append("<table><tr><th></th><th>Trades</th><th>Esperanza</th><th>Acierto</th><th>Gana medio</th><th>Pierde medio</th><th>Profit factor</th><th>Máx. DD</th></tr>")
            for nom, m in [("Fuera de muestra (lo que cuenta)", o), ("Histórico completo", r["historico_completo"])]:
                h.append(f"<tr><td>{nom}</td><td>{m['n']}</td><td class='{'ok' if m['esperanza'] > 0 else 'ko'}'>{m['esperanza']:+.3f}R</td>"
                         f"<td>{m['acierto']:.0%}</td><td>{m['gana_med']:+.2f}R</td><td>{m['pierde_med']:+.2f}R</td><td>{m['pf']:.2f}</td><td>{m['max_dd']:.1f}R</td></tr>")
            h.append("</table>")
            reales = r.get("reales") or {}
            h.append(f"<div class='sub'>Monte Carlo: probabilidad de esperanza positiva {mc['prob_positiva']:.0%} · peor 5 %: {mc['p5_esperanza']:+.3f}R · "
                     f"{r['trades_por_semana']} trades/semana · señales reales cerradas: {reales.get('n', 0)}"
                     + (f" ({reales['esperanza']:+.3f}R)" if reales.get("esperanza") is not None else "") + "</div>")
        if a.get("anual") is not None and len(a["anual"]):
            h.append("<h3>Cómo se ha comportado año a año</h3>" + _tabla(a["anual"]))
        if a.get("horas") is not None:
            top = a["horas"].sort_values(ascending=False).head(4)
            h.append("<div class='sub'>Horas con más movimiento (UTC, 1 = media): " +
                     " · ".join(f"<b>{hh}h</b> {v}" for hh, v in top.items()) + "</div>")

    # --- Seguimiento
    seg = [s for s in ctx["seguimiento"]][-20:]
    if seg:
        h.append("<h2>Seguimiento de señales anteriores</h2><table><tr><th>Vela</th><th>Activo</th><th>TF</th><th>Dir.</th><th>Estado</th><th>Resultado</th></tr>")
        for s in reversed(seg):
            res = f"{s['R']:+.2f}R" if s.get("R") is not None else "—"
            cls = "ok" if (s.get("R") or 0) > 0 else ("ko" if s.get("R") is not None else "")
            h.append(f"<tr><td>{s['vela'][:16]}</td><td>{s['activo']}</td><td>{s['tf']}</td><td>{s['dir']}</td><td>{s['estado']}</td><td class='{cls}'>{res}</td></tr>")
        h.append("</table>")

    # --- Prompt premercado (idea del vídeo)
    activos = ", ".join(a["nombre"] for a in ctx["activos"])
    h.append("<h2>Prompt premercado para Claude (noticias y calendario)</h2>")
    h.append("<pre>" + html.escape(
        f"Actúa como mi analista premercado. Opero {activos}, intradía/swing, franja "
        f"{config.FRANJA_UTC[0] if config.FRANJA_UTC else ''}-{config.FRANJA_UTC[1] if config.FRANJA_UTC else ''}h UTC, riesgo {config.RIESGO_POR_TRADE:.0%} por trade.\n"
        "Dame: 1) noticias de las últimas 12 h que muevan estos activos, 2) calendario económico de hoy con impacto "
        "(alto/medio) y hora, 3) qué eventos de hoy deberían hacerme NO operar en ciertas horas, 4) sesgo "
        "fundamental por activo en una línea. Sé breve, en tabla.") + "</pre>")

    h.append("<h2>Recordatorios (reglas del vídeo)</h2><div class='card'>"
             "1. Opera solo en tu franja. 2. Una pérdida que cumple el plan es parte del juego; un error no. "
             "3. Al llegar al stop diario o al objetivo de ganancias, se cierra la plataforma. "
             "4. Solo condiciones objetivas: si la regla no se cumple, no hay trade. "
             "5. Registra todo: el robot analiza tu diario con <code>python robot.py diario</code>.</div>")
    h.append("<p class='sub'>Herramienta de estudio. Resultados pasados y simulados no garantizan resultados futuros; "
             "tú decides y ejecutas cada operación.</p></body></html>")

    ruta = os.path.join(CARPETA, f"informe_{datetime.now():%Y-%m-%d}.html")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("".join(h))
    with open(os.path.join(CARPETA, "ultimo.html"), "w", encoding="utf-8") as fh:
        fh.write("".join(h))
    return ruta
