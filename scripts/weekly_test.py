import os, json, requests, base64
from datetime import datetime, timezone, timedelta

GROQ_API_KEY    = os.environ["GROQ_API_KEY"]
TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID= os.environ["TELEGRAM_CHAT_ID"]
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO     = os.environ.get("GITHUB_REPOSITORY", "")
LOG_FILE        = "data/lessons_log.json"

def get_week_lessons():
    if not GITHUB_TOKEN: return []
    r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{LOG_FILE}",
        headers={"Authorization":f"token {GITHUB_TOKEN}","Accept":"application/vnd.github.v3+json"}, timeout=10)
    if r.status_code != 200: return []
    all_lessons = json.loads(base64.b64decode(r.json()["content"]).decode())
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    return [l for l in all_lessons if datetime.fromisoformat(l["ts"]) > cutoff]

def generate_test(lessons):
    en = [l for l in lessons if l["lang"]=="english"]
    de = [l for l in lessons if l["lang"]=="german"]
    en_ctx = "\n---\n".join(l["content"][:250] for l in en[-8:]) or "General B2/C1 English"
    de_ctx = "\n---\n".join(l["content"][:200] for l in de[-5:]) or "General A1/A2 German"
    today = datetime.now().strftime("%d.%m.%Y")

    prompt = f"""Create a Friday language test for a Polish adult learner.
This week: {len(en)} English lessons (B2/C1), {len(de)} German lessons (A1/A2).

English content: {en_ctx}
German content: {de_ctx}

Format EXACTLY:

🎯 *PIĄTKOWY TEST JĘZYKOWY*
📅 {today}

━━━━━━━━━━━━━━━━━━━━
📊 *Twój tydzień:*
🇬🇧 Angielski: {len(en)} lekcji
🇩🇪 Niemiecki: {len(de)} lekcji
📚 Łącznie: {len(lessons)} lekcji
━━━━━━━━━━━━━━━━━━━━

🇬🇧 *ANGIELSKI — 4 pytania*

*1.* [question]
A) [opt]  B) [opt]  C) [opt]

*2.* [question]
A) [opt]  B) [opt]  C) [opt]

*3.* [question]
A) [opt]  B) [opt]  C) [opt]

*4.* [question]
A) [opt]  B) [opt]  C) [opt]

━━━━━━━━━━━━━━━━━━━━
🇩🇪 *NIEMIECKI — 3 pytania*

*5.* [question]
A) [opt]  B) [opt]  C) [opt]

*6.* [question]
A) [opt]  B) [opt]  C) [opt]

*7.* [question]
A) [opt]  B) [opt]  C) [opt]

━━━━━━━━━━━━━━━━━━━━
✅ *Odpowiedzi:* 1-? 2-? 3-? 4-? 5-? 6-? 7-?

💪 Dobra robota w tym tygodniu! Do następnego poniedziałku!"""

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role":"user","content":prompt}], "max_tokens":900, "temperature":0.6},
        timeout=30
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def send_telegram(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)

def main():
    lessons = get_week_lessons()
    print(f"Lessons this week: {len(lessons)}")
    test = generate_test(lessons)
    send_telegram(test)
    print("✅ Weekly test sent!")

if __name__ == "__main__":
    main()
