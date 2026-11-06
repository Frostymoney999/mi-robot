# Tu robot en el móvil (sin tener el PC encendido) — 15 minutos, gratis

Resultado final:
- 📱 Una **app web** en tu iPhone (icono en la pantalla de inicio) con 4 pestañas: Hoy, Mercados, Robot y Mi día.
- 🔔 **Avisos por Telegram**: resumen cada mañana a las 07:15 y aviso al momento si sale una señal en tu franja.
- ☁️ El robot corre solo en los servidores de GitHub: estudia el mercado, reaprende cada domingo y actualiza la app.

---

## 1. Crea tu bot de Telegram (3 min)
1. En Telegram busca **@BotFather** → escribe `/newbot` → ponle un nombre (ej. "Mi Robot Trading").
2. Te da un **token** tipo `7123456789:AAH...`. Guárdalo.
3. Abre tu bot nuevo y escríbele cualquier cosa ("hola"). **Importante**, si no, no te puede escribir.
4. Busca **@userinfobot**, dale a Iniciar y te dice tu **Id** (un número). Ese es tu `TELEGRAM_CHAT_ID`.

## 2. Sube el robot a GitHub (5 min)
1. Crea cuenta en **github.com** (gratis).
2. Arriba a la derecha **+ → New repository** → nombre `mi-robot` → **Public** → Create.
3. Pulsa **"uploading an existing file"** y arrastra **todo el contenido** de la carpeta `robot_trading`
   (archivos y carpetas, también `.github`). → **Commit changes**.
   - Si la carpeta `.github` no se sube (en Windows a veces está oculta): **Add file → Create new file**,
     escribe como nombre `.github/workflows/robot.yml` y pega dentro el contenido de ese archivo.

## 3. Mete tus claves (2 min)
En tu repositorio: **Settings → Secrets and variables → Actions**
- Pestaña **Secrets → New repository secret**:
  - `TELEGRAM_TOKEN` = el token del paso 1
  - `TELEGRAM_CHAT_ID` = tu Id del paso 1
  - `BALANCE` = el tamaño de tu cuenta, ej. `10000`
- Pestaña **Variables → New repository variable**:
  - `URL_WEB` = `https://TU-USUARIO.github.io/mi-robot/` (cambia TU-USUARIO)

Los secretos no los ve nadie. La web es pública, pero no muestra tu balance: el tamaño de cuenta de la app
se guarda solo en tu móvil.

## 4. Activa la web (1 min)
**Settings → Pages** → Source: *Deploy from a branch* → Branch: `main` y carpeta `/docs` → **Save**.

## 5. Primer arranque (5 min de espera)
**Actions** → si pide permiso, "I understand… enable" → **Robot de trading** → **Run workflow**.
La primera vez estudia todos los años y aprende (unos minutos). Al acabar te llega el primer Telegram.

## 6. Ponlo como app en el iPhone
Abre `https://TU-USUARIO.github.io/mi-robot/` en **Safari** → botón **Compartir** → **Añadir a pantalla de inicio**.

---

## Cuándo trabaja solo
El robot se despierta cada hora y decide qué toca según lo que elijas en **⚙️ Ajustes** de la app:
| Cuándo | Qué hace |
|---|---|
| A tu hora de informe (por defecto 8:00) en tus días | Informe premercado + señales → Telegram + app |
| Dentro de tus horarios (por defecto 14-17h) | Revisa señales H1 → Telegram **solo si hay señal nueva aprobada** |
| Al guardar ajustes nuevos desde la app | Reaprende todo con tu nueva configuración |
| Domingo 19:00 | Reaprende con la semana nueva |

## Cómo usar la app
- **Hoy**: señales con entrada, stop, take profit y **lotes calculados para tu 1R**. Stop del día y objetivo de ganancias.
  El prompt de noticias se copia con un toque y lo pegas en Claude.
- **Mercados**: tendencia, ADX, niveles, gráfico con EMA50, a qué horas se mueve cada activo y cómo se ha comportado cada año.
- **Robot**: qué estrategia ha aprendido, sus exámenes fuera de muestra, la curva y cómo han acabado sus señales reales.
- **⚙️ Ajustes**: elige mercados (forex, oro, plata, petróleo, índices, cripto), temporalidades (D1/H4/H1), tus horarios,
  la hora del informe, qué estrategias aprende (escuela de 8 estilos), acierto mínimo y riesgo. Pulsa *Guardar y reentrenar*.
  La primera vez te pide una llave de GitHub (las instrucciones salen en la propia pantalla).
- **Mi día**: apunta cada trade en R (y si fue un error). Bloquea el día al llegar al stop o al objetivo,
  checklist antes de entrar, calculadora de lotes y cuánto te cuestan tus errores.

## Notas
- En la nube los datos vienen de Yahoo Finance (el oro es el futuro GC=F, con un precio un poco distinto al GOLD de tu broker).
  Antes de entrar, mira siempre el precio real en tu MT5.
- En `config.py` revisa `valor_lote` de cada activo (MT5 → clic derecho en el símbolo → Especificación → Tamaño del contrato).
  Si cambias algo, edítalo en GitHub (icono del lápiz) y se aplica en la siguiente ejecución.
- El robot **no opera por ti**. Te avisa y tú decides.
