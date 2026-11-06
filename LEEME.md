# Robot de trading que aprende solo

Basado en las reglas del vídeo de Alex Ruiz ("operar como un idiota"): condiciones objetivas,
horario fijo, límite de pérdidas **y** de ganancias por esperanza en R, eliminar errores y analizar tu historial.

**No ejecuta operaciones.** Estudia, aprende, te da señales con entrada/SL/TP/lotes y tú decides.

## Instalación (Windows, una vez)
1. Instala Python 3.11+ desde python.org (marca "Add Python to PATH").
2. Doble clic en `instalar.bat`.
3. Deja **MetaTrader 5 abierto y con sesión iniciada** (XM o FundedNext). El robot coge de ahí los
   históricos y el tamaño de lote exacto. Sin MT5, intenta Yahoo Finance.
4. Abre `config.py` y revisa: nombres de símbolos de tu broker (GOLD, US100Cash…), tu balance, riesgo y franja horaria.

## Uso
| Qué | Cómo | Cuándo |
|---|---|---|
| Aprender (estudia años de historia) | `aprender.bat` o `python robot.py aprender` | 1 vez por semana (lo hace solo si hace falta) |
| Informe premercado + señales | `informe.bat` o `python robot.py todo` | cada mañana antes de tu franja |
| Analizar tu diario | `python robot.py diario` (lee MT5) o `python robot.py diario historial.csv` | cada domingo |
| Probar sin datos reales | añade `--demo` | — |

Para que se ejecute solo cada mañana: Programador de tareas de Windows → Crear tarea básica → Diaria →
Programa: `informe.bat` (dentro de esta carpeta).

## Cómo aprende
1. **Walk-forward**: entrena con un tramo del pasado y lo examina en el tramo siguiente que no ha visto. Solo vale lo de fuera de muestra.
2. **Búsqueda evolutiva** entre miles de combinaciones de reglas objetivas (EMA 20/50/100/200, cruce/apoyo/ruptura, filtro ADX, SL por ATR, TP en R, sentido, franja).
3. **Monte Carlo** sobre los trades fuera de muestra: si en el peor 5 % de los casos la esperanza no sigue siendo positiva, no se aprueba.
4. **Campeón vs retador**: guarda en `memoria/conocimiento.json` la estrategia vigente; una nueva solo la sustituye si lo hace mejor en lo más reciente.
5. **Autovigilancia**: registra cada señal (`memoria/senales.json`), comprueba cómo acabó y, si en ≥10 señales reales va claramente peor de lo esperado, la marca como degradada y reaprende.

Estados: **APROBADA** (ventaja demostrada fuera de muestra) · **EN OBSERVACIÓN** (solo para seguir en demo).

## Diario (CSV propio)
Columnas: `apertura, cierre, simbolo, tipo, volumen, precio_entrada, sl, precio_salida, beneficio`
(fechas en hora UTC, ej. `2026-11-03 12:35`). Detecta: fuera de horario, sin SL, tamaño de más, pérdida >1,5R,
venganza (<30 min tras una pérdida), sobreoperar y seguir tras el stop diario. Te enseña cuánto ganarías sin esos errores.

> Herramienta de estudio. Los resultados simulados y pasados no garantizan resultados futuros.

## 📱 En el móvil
Lee **GUIA_MOVIL.md**: en 15 minutos lo tienes funcionando solo en la nube (GitHub, gratis), con
app en la pantalla de inicio del iPhone y avisos por Telegram. En el PC también puedes abrir `docs/index.html`
con doble clic después de ejecutar el robot.
