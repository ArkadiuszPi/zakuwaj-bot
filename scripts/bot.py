"""
Zakuwaj Bot v2
- Sentence of the day (EN + DE) repeated randomly all day
- 2x grammar/vocabulary lessons per day
- Interactive Friday test (one question at a time, A/B/C/D)
- /wylosuj command to get new sentence
"""

import os, json, random, requests, base64
from datetime import datetime, timezone, timedelta

GROQ_API_KEY     = os.environ["GROQ_API_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_TOKEN     = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO      = os.environ.get("GITHUB_REPOSITORY", "")
MODE             = os.environ.get("MODE", "repeat")
# MODE options:
#   "morning"  — generate new sentence of the day (runs at 8:00)
#   "repeat"   — resend today's sentence (runs randomly during day)
#   "lesson"   — send grammar/vocabulary lesson (runs 2x per day)
#   "new_sentence" — generate new sentence (triggered by /wylosuj)

DATA_FILE    = "data/state.json"
LOG_FILE     = "data/lessons_log.json"

# ─── Groq API ────────────────────────────────────────────────────────────────

def groq(prompt, max_tokens=500, temperature=0.9):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        },
        timeout=25
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

# ─── GitHub state storage ─────────────────────────────────────────────────────

def read_file(path):
    if not GITHUB_TOKEN: return {}, None
    r = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
        timeout=10
    )
    if r.status_code == 200:
        d = r.json()
        return json.loads(base64.b64decode(d["content"]).decode()), d["sha"]
    return {}, None

def write_file(path, data, sha):
    if not GITHUB_TOKEN: return
    body = {
        "message": f"update {path} {datetime.now(timezone.utc).strftime('%H:%M')}",
        "content": base64.b64encode(json.dumps(data, indent=2, ensure_ascii=False).encode()).decode()
    }
    if sha: body["sha"] = sha
    requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
        json=body, timeout=10
    )

# ─── Telegram ────────────────────────────────────────────────────────────────

def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
        timeout=10
    )

# ─── Generate sentence of the day ────────────────────────────────────────────

def generate_sentence(lang, exclude=""):
    if lang == "EN":
        prompt = f"""Generate ONE practical English sentence at B2/C1 level for a Polish speaker.
Requirements:
- Useful in real life (work, travel, social situations)
- Contains an interesting grammar structure or idiom worth learning
- NOT a simple sentence
- Different from: {exclude[:200] if exclude else 'nothing'}

Format EXACTLY:
🇬🇧 *ZDANIE DNIA*

*Zdanie:* [the English sentence]

🇵🇱 *Tłumaczenie:* [Polish translation]

📐 *Konstrukcja:* [grammar tense/structure name in Polish, e.g. "Present Perfect Continuous"]
💡 *Dlaczego warto:* [one sentence why this is useful]

_Napisz /wylosuj\\_EN żeby wylosować inne zdanie_"""

    else:
        prompt = f"""Generate ONE practical German sentence at A1/A2 level for a Polish speaker.
Requirements:
- Simple, everyday situation (shopping, greeting, restaurant, transport)
- Contains basic but useful vocabulary
- Different from: {exclude[:200] if exclude else 'nothing'}

Format EXACTLY:
🇩🇪 *ZDANIE DNIA*

*Zdanie:* [the German sentence]

🇵🇱 *Tłumaczenie:* [Polish translation]

📐 *Konstrukcja:* [grammar note in Polish, simple]
💡 *Dlaczego warto:* [one sentence why this is useful]

_Napisz /wylosuj\\_DE żeby wylosować inne zdanie_"""

    return groq(prompt, max_tokens=300, temperature=0.95)

# ─── Generate grammar/vocabulary lesson ──────────────────────────────────────

EN_LESSON_TOPICS = [
    "Present Perfect vs Past Simple — kiedy używać którego",
    "Phrasal verb z przykładem w zdaniu",
    "Idiom związany z pracą lub emocjami",
    "Różnica między dwoma podobnymi słowami (np. say/tell, make/do)",
    "Conditionals — 2nd lub 3rd conditional",
    "Passive voice w praktycznym zdaniu",
    "Słownictwo biznesowe B2/C1",
    "Reported speech — przykład praktyczny",
]

DE_LESSON_TOPICS = [
    "Podstawowy przypadek (Nominativ/Akkusativ) na przykładzie",
    "Rodzajniki der/die/das — praktyczna wskazówka",
    "Liczba mnoga rzeczowników — zasada",
    "Modalne: kann/muss/will w zdaniu",
    "Podstawowe słownictwo tematyczne (jedzenie/transport/praca)",
    "Separable verbs (aufstehen, anrufen) — jak używać",
    "Negacja: nicht vs kein",
]

def generate_lesson(lang):
    topic = random.choice(EN_LESSON_TOPICS if lang == "EN" else DE_LESSON_TOPICS)

    if lang == "EN":
        prompt = f"""You are an English teacher for Polish adults at B2/C1 level.
Topic: {topic}

Format EXACTLY:
🇬🇧 *LEKCJA ANGIELSKIEGO*

📖 *Temat:* {topic}

[explanation in Polish, max 3 sentences, clear and practical]

✏️ *Przykład:*
➜ [English sentence using this grammar/vocabulary]
🇵🇱 [Polish translation]

📐 *Czas/konstrukcja:* [grammar structure name + formula, e.g. "Present Perfect: have/has + V3"]

💡 *Zapamiętaj:* [one practical tip in Polish]"""

    else:
        prompt = f"""You are a German teacher for Polish adults at A1/A2 level.
Topic: {topic}

Format EXACTLY:
🇩🇪 *LEKCJA NIEMIECKIEGO*

📖 *Temat:* {topic}

[explanation in Polish, max 3 sentences, very simple]

✏️ *Przykład:*
➜ [German sentence]
🇵🇱 [Polish translation]

📐 *Konstrukcja:* [simple grammar note in Polish]

💡 *Zapamiętaj:* [memory tip in Polish]"""

    return groq(prompt, max_tokens=400, temperature=0.85)

# ─── Morning mode — generate both sentences ──────────────────────────────────

def morning_mode():
    state, sha = read_file(DATA_FILE)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    en_sentence = generate_sentence("EN")
    de_sentence = generate_sentence("DE")

    state["date"] = today
    state["en_sentence"] = en_sentence
    state["de_sentence"] = de_sentence
    state["en_repeats"] = 0
    state["de_repeats"] = 0

    write_file(DATA_FILE, state, sha)

    send(f"☀️ *Dzień dobry! Oto Twoje zdania na dziś:*\n\n{en_sentence}\n\n━━━━━━━━━━━━\n\n{de_sentence}")
    print("✅ Morning sentences sent")

# ─── Repeat mode — resend today's sentence ───────────────────────────────────

def repeat_mode():
    state, sha = read_file(DATA_FILE)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if state.get("date") != today:
        print("No sentence for today yet, skipping")
        return

    # Alternate EN and DE
    en_repeats = state.get("en_repeats", 0)
    de_repeats = state.get("de_repeats", 0)

    if en_repeats <= de_repeats:
        lang = "EN"
        msg = state["en_sentence"]
        state["en_repeats"] = en_repeats + 1
    else:
        lang = "DE"
        msg = state["de_sentence"]
        state["de_repeats"] = de_repeats + 1

    write_file(DATA_FILE, state, sha)
    send(f"🔁 *Powtórka #{en_repeats + de_repeats + 1}*\n\n{msg}")
    print(f"✅ Repeat sent ({lang})")

# ─── Lesson mode — grammar/vocabulary lesson ─────────────────────────────────

def lesson_mode():
    # 50/50 EN or DE
    lang = random.choice(["EN", "DE"])
    lesson = generate_lesson(lang)

    # Log lesson
    log, sha = read_file(LOG_FILE)
    if not isinstance(log, list): log = []
    log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "lang": lang,
        "content": lesson
    })
    # Keep last 60 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    log = [l for l in log if datetime.fromisoformat(l["ts"]) > cutoff]
    write_file(LOG_FILE, log, sha)

    send(lesson)
    print(f"✅ Lesson sent ({lang})")

# ─── New sentence mode — triggered by /wylosuj ───────────────────────────────

def new_sentence_mode():
    lang = os.environ.get("LANG_TARGET", "EN")
    state, sha = read_file(DATA_FILE)

    old = state.get("en_sentence" if lang == "EN" else "de_sentence", "")
    new_sentence = generate_sentence(lang, exclude=old)

    if lang == "EN":
        state["en_sentence"] = new_sentence
        state["en_repeats"] = 0
    else:
        state["de_sentence"] = new_sentence
        state["de_repeats"] = 0

    write_file(DATA_FILE, state, sha)
    send(f"🎲 *Nowe zdanie dnia!*\n\n{new_sentence}")
    print(f"✅ New {lang} sentence generated")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if MODE == "morning":
        morning_mode()
    elif MODE == "repeat":
        repeat_mode()
    elif MODE == "lesson":
        lesson_mode()
    elif MODE == "new_sentence":
        new_sentence_mode()
    else:
        print(f"Unknown mode: {MODE}")

if __name__ == "__main__":
    main()
