"""
ROBOT DE TRADING QUE APRENDE SOLO
=================================
  python robot.py aprender        -> estudia los últimos años y aprende/actualiza estrategias (lento, 1 vez por semana)
  python robot.py informe         -> informe premercado de hoy + señales (rápido, cada mañana)
  python robot.py todo            -> informe, y si toca (memoria vieja o estrategia degradada) reaprende antes
  python robot.py diario [csv]    -> analiza tu historial (de MT5 o de un CSV) y te dice qué errores te cuestan dinero
  python robot.py auto            -> lo que usa la nube cada hora: decide solo si toca informe, revisar señales o reaprender
Añade  --demo  para probarlo con datos sintéticos.
Añade  --resumen  para que el aviso de Telegram mande el resumen completo aunque no haya señales nuevas.
"""
import sys
import webbrowser
from datetime import datetime, timedelta

import pandas as pd

import config
import datos
import estudio
import informe
import notificar
import web
import riesgo
import seguimiento
from aprendizaje import aprender, cargar_memoria, guardar_memoria
from estrategia import describir
from indicadores import preparar

DEMO = "--demo" in sys.argv


def _quitar_vela_abierta(df, tf):
    if df is None or DEMO:
        return df
    ahora = pd.Timestamp.utcnow().tz_localize(None)
    paso = {"D1": pd.Timedelta(days=1), "H4": pd.Timedelta(hours=4), "H1": pd.Timedelta(hours=1)}[tf]
    return df[df.index + paso <= ahora]


def _cargar_todo():
    out = {}
    for activo in config.ACTIVOS:
        for tf in config.TEMPORALIDADES:
            df = _quitar_vela_abierta(datos.cargar(activo, tf, modo_demo=DEMO), tf)
            if df is not None and len(df) > 300:
                out[(activo, tf)] = df
    return out


def cmd_aprender(datos_cargados=None, solo=None):
    print("\n>> Descargando históricos...")
    dd = datos_cargados or _cargar_todo()
    mem = cargar_memoria()
    print("\n>> Aprendiendo (walk-forward + búsqueda evolutiva). Esto puede tardar varios minutos.")
    for (activo, tf), df in dd.items():
        if solo and f"{activo}_{tf}" not in solo:
            continue
        print(f"\n  [{activo} {tf}] {df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}")
        aprender(activo, tf, preparar(df), config.ACTIVOS[activo]["coste"], mem)
        guardar_memoria(mem)
    mem["_huella_ajustes"] = config.huella_ajustes()
    guardar_memoria(mem)
    print("\n>> Memoria guardada en memoria/conocimiento.json")
    return dd


def cmd_informe(dd=None, auto_reaprender=False):
    dd = dd or _cargar_todo()
    mem = cargar_memoria()

    # ¿Hay que reaprender algo? (memoria vacía, vieja o estrategia degradada)
    if auto_reaprender:
        pendientes = []
        for (activo, tf), df in dd.items():
            k = f"{activo}_{tf}"
            r = mem.get(k)
            f = preparar(df)
            seguimiento.resolver(activo, tf, f, config.ACTIVOS[activo]["coste"])
            vieja = (not r or datetime.fromisoformat(r["actualizado"]) < datetime.now() - timedelta(days=7)
                     or mem.get("_huella_ajustes") != config.huella_ajustes())
            if vieja or (r and seguimiento.revisar_degradacion(activo, tf, r)):
                pendientes.append(k)
        if pendientes:
            print(f"\n>> Reaprendiendo automáticamente: {', '.join(pendientes)}")
            cmd_aprender(dd, solo=pendientes)
            mem = cargar_memoria()

    activos, senales_hoy, registros = [], [], []
    usdjpy = None
    if ("USDJPY", "D1") in dd:
        usdjpy = float(dd[("USDJPY", "D1")]["close"].iloc[-1])
    for activo in config.ACTIVOS:
        bloque = {"nombre": activo, "registros": {}}
        ultimo = next((dd[(activo, t)]["close"].iloc[-1] for t in config.TEMPORALIDADES if (activo, t) in dd), None)
        bloque["valor_lote"] = riesgo.valor_lote(activo, ultimo, usdjpy)
        for tf in config.TEMPORALIDADES:
            df = dd.get((activo, tf))
            r = mem.get(f"{activo}_{tf}")
            if df is None:
                continue
            f = preparar(df)
            if tf == "D1" or ("estado" not in bloque and "D1" not in config.TEMPORALIDADES):
                bloque["estado"] = estudio.estado_actual(df)
                bloque["anual"] = estudio.por_anio(df)
                bloque["precio"] = web.serie_precio(df)
            if tf == "H1":
                bloque["horas"] = estudio.por_hora(df)
            if not r:
                continue
            seguimiento.resolver(activo, tf, f, config.ACTIVOS[activo]["coste"])
            seguimiento.revisar_degradacion(activo, tf, r)
            bloque["registros"][tf] = r
            r["curva"] = web.curva(f, r["params"], config.ACTIVOS[activo]["coste"], tf == "H1")
            registros.append(r)
            s = seguimiento.senal_actual(f, r["params"], tf == "H1")
            if s:
                nueva = seguimiento.registrar(activo, tf, r["params"], s)
                s.update(activo=activo, tf=tf, estado=r["estado"], regla=describir(r["params"], tf == "H1"), nueva=nueva,
                         lotes=riesgo.lotaje(config.ACTIVOS[activo]["mt5"], s["dist_sl"], bloque["valor_lote"]))
                senales_hoy.append(s)
        activos.append(bloque)
    guardar_memoria(mem)

    plan = riesgo.plan_del_dia(registros)
    ruta = informe.generar({"activos": activos, "plan": plan, "senales": senales_hoy,
                            "seguimiento": seguimiento.historial(), "demo": DEMO})
    ctx = {"activos": activos, "plan": plan, "senales": senales_hoy, "seguimiento": seguimiento.historial(), "demo": DEMO}
    print(f"\n>> App móvil: {web.exportar(ctx)}")
    notificar.enviar(ctx, resumen=("--resumen" in sys.argv))
    print(f"\n>> Informe: {ruta}")
    for s in senales_hoy:
        print(f"   SEÑAL {s['activo']} {s['tf']} {s['dir']}  entrada≈{s['entrada']:.5g}  SL {s['sl']:.5g}  TP {s['tp']:.5g}  [{s['estado']}]")
    if not senales_hoy:
        print("   Sin señales hoy.")
    if "--sin-abrir" not in sys.argv:
        try:
            webbrowser.open("file://" + ruta)
        except Exception:
            pass
    return ruta


def cmd_diario():
    import diario
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    df = diario.desde_csv(args[0]) if args else diario.desde_mt5()
    if df.empty:
        print("No hay operaciones en el historial.")
        return
    a = diario.analizar(df)
    diario.imprimir(a)
    salida = "informes/diario_analizado.csv"
    a["tabla"].drop(columns=["prev"]).to_csv(salida, index=False)
    print(f"\n  Detalle trade a trade en {salida}")


def cmd_auto():
    """Llamado cada hora desde GitHub. Decide qué toca según tus ajustes (hora de Madrid)."""
    from zoneinfo import ZoneInfo
    ahora = datetime.now(ZoneInfo(config.ZONA))
    a = config.AJUSTES
    mem = cargar_memoria()
    cambio = mem.get("_huella_ajustes") != config.huella_ajustes()
    dia_ok = ahora.isoweekday() in a["dias"]
    if cambio:
        print(">> Has cambiado tus ajustes: reaprendo todo")
        sys.argv.append("--resumen")
        cmd_informe(cmd_aprender())
    elif dia_ok and ahora.hour == a["hora_informe"]:
        print(">> Hora del informe premercado")
        sys.argv.append("--resumen")
        cmd_informe(auto_reaprender=True)
    elif dia_ok and config.en_franja(ahora.hour) and "H1" in config.TEMPORALIDADES:
        print(">> Dentro de tu horario: reviso señales")
        cmd_informe(auto_reaprender=False)
    else:
        print(f">> {ahora:%a %H:%M} Madrid: fuera de tu horario, nada que hacer")


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if orden == "aprender":
        cmd_informe(cmd_aprender())
    elif orden == "informe":
        cmd_informe()
    elif orden == "todo":
        cmd_informe(auto_reaprender=True)
    elif orden == "diario":
        cmd_diario()
    elif orden == "auto":
        cmd_auto()
    else:
        print(__doc__)
