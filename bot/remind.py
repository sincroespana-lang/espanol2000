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

def btn(text="Відкрити Español 2000"):
    return {"inline_keyboard": [[{"text": text, "web_app": {"url": APP}}]]}

st = json.load(open(F)) if os.path.exists(F) else {"offset": 0, "chats": {}}
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
            api("sendMessage", chat_id=cid, text=MSGS[now.toordinal() % len(MSGS)], reply_markup=btn("Почати заняття"))
            c["last"] = today
        except Exception as e:
            print("send failed", cid, e)

json.dump(st, open(F, "w"))
print("ok", len(st["chats"]), "chats")
