import os, json, random, requests, base64
from datetime import datetime, timezone, timedelta

GROQ_API_KEY    = os.environ["GROQ_API_KEY"]
TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID= os.environ["TELEGRAM_CHAT_ID"]
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO     = os.environ.get("GITHUB_REPOSITORY", "")
LOG_FILE        = "data/lessons_log.json"

EN_TOPICS = [
    "a useful B2/C1 idiom related to work or emotions",
    "an advanced vocabulary word (C1) with nuance",
    "a common grammar mistake Polish speakers make in English",
    "a phrasal verb used in everyday conversation",
    "a business English expression",
    "a confusing word pair (e.g. affect/effect) explained",
]
DE_TOPICS = [
    "a basic everyday German phrase for shopping or transport (A1/A2)",
    "German numbers, time or date expressions",
    "a simple German greeting or social expression",
    "basic German vocabulary for food or household items",
    "a false friend between German and Polish or English",
]

def get_lesson():
    lang = random.choices(["english","german"], weights=[65,35])[0]
    topic = random.choice(EN_TOPICS if lang=="english" else DE_TOPICS)
    if lang == "english":
        prompt = f"""You are an English teacher. Student is Polish, level B2/C1.
Lesson about: {topic}

Format EXACTLY:
🇬🇧 *LEKCJA ANGIELSKIEGO*

📖 *Temat:* [topic]
[explanation, max 2 sentences]

✏️ *Przykład:*
➜ [English sentence]
🇵🇱 [Polish translation]

💡 *Tip:* [one practical tip]

#english #b2 #c1"""
    else:
        prompt = f"""You are a German teacher. Student is Polish, beginner A1/A2.
Lesson about: {topic}

Format EXACTLY:
🇩🇪 *LEKCJA NIEMIECKIEGO*

📖 *Temat:* [topic]
[explanation, max 2 sentences]

✏️ *Przykład:*
➜ [German sentence]
🇵🇱 [Polish translation]

💡 *Zapamiętaj:* [memory tip]

#deutsch #a1 #a2"""

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role":"user","content":prompt}], "max_tokens":400, "temperature":0.9},
        timeout=20
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"], lang

def send_telegram(text):
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    return r.status_code == 200

def read_log():
    if not GITHUB_TOKEN: return [], None
    r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{LOG_FILE}",
        headers={"Authorization":f"token {GITHUB_TOKEN}","Accept":"application/vnd.github.v3+json"}, timeout=10)
    if r.status_code == 200:
        d = r.json()
        return json.loads(base64.b64decode(d["content"]).decode()), d["sha"]
    return [], None

def write_log(lessons, sha):
    if not GITHUB_TOKEN: return
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    lessons = [l for l in lessons if datetime.fromisoformat(l["ts"]) > cutoff]
    body = {"message": f"log {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            "content": base64.b64encode(json.dumps(lessons, indent=2, ensure_ascii=False).encode()).decode()}
    if sha: body["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{LOG_FILE}",
        headers={"Authorization":f"token {GITHUB_TOKEN}","Accept":"application/vnd.github.v3+json"},
        json=body, timeout=10)

def main():
    if random.random() < 0.25:
        print("Skipped"); return
    lesson, lang = get_lesson()
    lessons, sha = read_log()
    lessons.append({"ts": datetime.now(timezone.utc).isoformat(), "lang": lang, "content": lesson})
    write_log(lessons, sha)
    ok = send_telegram(lesson)
    print(f"{'✅' if ok else '❌'} {'🇬🇧' if lang=='english' else '🇩🇪'} sent")

if __name__ == "__main__":
    main()
