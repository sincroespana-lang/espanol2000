# Español 2000 — нагадування в Telegram. Запускається GitHub Actions кожні 15 хв.
# Стан (чати, час нагадувань, offset оновлень) лежить у bot_state.json, який зберігається в кеші Actions.
import json, os, urllib.request, urllib.parse, datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["TG_TOKEN"]
APP = "https://sincroespana-lang.github.io/espanol2000/"
TZ = ZoneInfo("Europe/Madrid")
F = "bot_state.json"

def api(method, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=data, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def btn(text="Відкрити Español 2000", url=APP):
    return {"inline_keyboard": [[{"text": text, "web_app": {"url": url}}]]}

def plural(n, a, b, c):
    n = abs(n) % 100
    if 11 <= n <= 14: return c
    n %= 10
    return a if n == 1 else b if 2 <= n <= 4 else c

def week_report(payload, prev):
    # payload із додатка: w_<нових>_<днів>_<повторів>_<точність>_<серія>_<у навчанні>_<закріплено>_<можу сказати>_<дитина>
    try:
        n, days, r, acc, st, work, learned, can, kid = (int(x) for x in payload.split("_")[1:10])
    except Exception:
        return None
    def d(key, v):
        if not prev or key not in prev: return ""
        x = v - prev[key]
        return f" ({'+' if x >= 0 else ''}{x})"
    lines = ["📊 Мій тиждень в Español 2000", "",
             f"🆕 Нових слів: {n}", f"📅 Днів із заняттям: {days} з 7",
             f"🔥 Серія: {st} {plural(st, 'день', 'дні', 'днів')}",
             f"📚 Слів у навчанні: {work}{d('work', work)} · закріплено {learned}{d('learned', learned)}"]
    if not kid:
        lines.insert(5, f"🎯 Точність повторів: {acc}% ({r} {plural(r, 'повтор', 'повтори', 'повторів')})")
        lines.append(f"💬 Можу сказати: {can} {plural(can, 'фразу', 'фрази', 'фраз')}{d('can', can)}")
    lines += ["", "Чудовий тиждень! ¡Sigue así! 💪" if days >= 5 else "Наступного тижня спробуй хоча б 5 днів — так слова закріплюються найкраще."]
    return "\n".join(lines), {"work": work, "learned": learned, "can": can}

st = json.load(open(F)) if os.path.exists(F) else {"offset": 0, "chats": {}}
# 0) налаштування бота: кнопка «Вчити» біля поля вводу, команди, опис (повторно — раз на добу)
if st.get("setup") != datetime.date.today().isoformat() + "v3":
    me = api("getMe"); print("bot:", me.get("result", {}).get("username"))
    print("menu:", api("setChatMenuButton", menu_button={"type": "web_app", "text": "Вчити", "web_app": {"url": APP}}))
    print("cmds:", api("setMyCommands", commands=[
        {"command": "start", "description": "Відкрити додаток"},
        {"command": "week", "description": "Звіт за тиждень"},
        {"command": "time", "description": "Час нагадування, напр. /time 08:30"},
        {"command": "off", "description": "Вимкнути нагадування"}]))
    api("setMyDescription", description="Español 2000 — 2000 найчастіших іспанських слів за 60 днів: тести з повтором, історії з озвучкою, фрази вголос і щоденні нагадування.")
    api("setMyShortDescription", short_description="Вчи 2000 іспанських слів і почни говорити")
    st["setup"] = datetime.date.today().isoformat() + "v3"

now = datetime.datetime.now(TZ)
today = now.strftime("%Y-%m-%d")

# 1) нові повідомлення боту
upd = api("getUpdates", offset=st["offset"], timeout=0, allowed_updates=["message"])
for u in upd.get("result", []):
    st["offset"] = u["update_id"] + 1
    m = u.get("message") or {}
    text = (m.get("text") or "").strip()
    if not text: continue
    cid = str(m["chat"]["id"]); name = (m.get("from") or {}).get("first_name") or "amigo"
    c = st["chats"].setdefault(cid, {"time": "19:00", "last": ""})
    if text.startswith("/start w_") or text.startswith("/start w"):
        res = week_report(text.split(" ", 1)[1], c.get("rep"))
        if res:
            api("sendMessage", chat_id=cid, text=res[0], reply_markup=btn("Продовжити заняття"))
            c["rep"] = res[1]
        continue
    if text.startswith("/week"):
        api("sendMessage", chat_id=cid, text="📊 Твій звіт за тиждень — у додатку. Відкрий і натисни «Надіслати звіт у чат бота».", reply_markup=btn("Відкрити звіт", APP + "?week=1"))
        continue
    if text.startswith("/start"):
        api("sendMessage", chat_id=cid, reply_markup=btn(), text=(
            f"¡Hola, {name}! 👋\n\nТут ти вчиш 2000 найчастіших іспанських слів і починаєш говорити.\n\n"
            f"• Тисни кнопку нижче або «Вчити» біля поля вводу\n• Нагадування щодня о {c['time'] or '—'}\n"
            "• Змінити час: /time 08:30\n• Вимкнути: /off"))
    elif text.startswith("/time"):
        import re
        mm = re.search(r"(\d{1,2})[:.](\d{2})", text)
        if mm and int(mm.group(1)) < 24 and int(mm.group(2)) < 60:
            c["time"] = f"{int(mm.group(1)):02d}:{mm.group(2)}"; c["last"] = ""
            api("sendMessage", chat_id=cid, text=f"Готово. Нагадуватиму щодня о {c['time']} (час Іспанії).")
        else:
            api("sendMessage", chat_id=cid, text="Напиши час так: /time 08:30")
    elif text.startswith("/off"):
        c["time"] = ""
        api("sendMessage", chat_id=cid, text="Нагадування вимкнено. Увімкнути: /time 19:00")
    else:
        api("sendMessage", chat_id=cid, text="Тисни кнопку, щоб вчитися 👇", reply_markup=btn())

# 2) щоденне нагадування: у вікні 2 години після обраного часу, раз на день
MSGS = [
    "¡Vamos! 🇪🇸 Час для іспанської.\n15 хвилин зараз — і серія днів не перерветься.",
    "¡Hola! 👋 Нові слова на сьогодні вже чекають.\nПочни з тесту — це 10 хвилин.",
    "🔥 Не зривай серію! Відкрий Español 2000 і пройди повтор.",
    "🎧 Сьогодні можна просто послухати історію і повторювати за диктором.",
]
for cid, c in st["chats"].items():
    if not c.get("time") or c.get("last") == today: continue
    h, mi = map(int, c["time"].split(":"))
    start = now.replace(hour=h, minute=mi, second=0, microsecond=0)
    if start <= now < start + datetime.timedelta(hours=2):
        try:
            if now.weekday() == 6:   # неділя — тижневий підсумок
                api("sendMessage", chat_id=cid, reply_markup=btn("📊 Відкрити звіт", APP + "?week=1"),
                    text="📊 Неділя — час підбити тиждень!\nВідкрий звіт: скільки нових слів, точність і серія. Кнопкою «Надіслати звіт у чат» збережеш його тут.")
            else:
                api("sendMessage", chat_id=cid, text=MSGS[now.toordinal() % len(MSGS)], reply_markup=btn("Почати заняття"))
            c["last"] = today
        except Exception as e:
            print("send failed", cid, e)

json.dump(st, open(F, "w"))
print("ok", len(st["chats"]), "chats")
