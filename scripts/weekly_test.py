"""
Language Learning Bot — weekly test generator
Runs every Friday at 20:00 CEST. Sends a summary + 7-question quiz.
"""

import os
import json
import requests
import base64
from datetime import datetime, timezone, timedelta

PERPLEXITY_API_KEY = os.environ["PERPLEXITY_API_KEY"]
TELEGRAM_TOKEN     = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO        = os.environ.get("GITHUB_REPOSITORY", "")

LOG_FILE = "data/lessons_log.json"


# ─── Fetch this week's lessons ────────────────────────────────────────────────

def get_week_lessons() -> list:
    if not GITHUB_TOKEN:
        return []
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{LOG_FILE}"
    r = requests.get(url, headers=_gh_headers(), timeout=10)
    if r.status_code != 200:
        return []
    data = r.json()
    all_lessons = json.loads(base64.b64decode(data["content"]).decode())
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    return [l for l in all_lessons if datetime.fromisoformat(l["ts"]) > cutoff]


def _gh_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


# ─── Generate test via Perplexity ─────────────────────────────────────────────

def generate_test(lessons: list) -> str:
    en = [l for l in lessons if l["lang"] == "english"]
    de = [l for l in lessons if l["lang"] == "german"]

    # Trim content to avoid token overflow
    en_ctx = "\n---\n".join(l["content"][:250] for l in en[-8:]) or "General B2/C1 English"
    de_ctx = "\n---\n".join(l["content"][:200] for l in de[-5:]) or "General A1/A2 German"

    today = datetime.now().strftime("%d.%m.%Y")

    prompt = f"""You are creating a Friday language test for a Polish adult learner.
This week they had {len(en)} English lessons (B2/C1) and {len(de)} German lessons (A1/A2).

English lesson content this week:
{en_ctx}

German lesson content this week:
{de_ctx}

Generate a test in this EXACT format (Polish interface):

🎯 *PIĄTKOWY TEST JĘZYKOWY*
📅 {today}

━━━━━━━━━━━━━━━━━━━━
📊 *Twój tydzień:*
🇬🇧 Angielski: {len(en)} lekcji
🇩🇪 Niemiecki: {len(de)} lekcji
📚 Łącznie: {len(lessons)} lekcji
━━━━━━━━━━━━━━━━━━━━

🇬🇧 *ANGIELSKI — 4 pytania*

*1.* [question about English content]
A) [option]  B) [option]  C) [option]

*2.* [question]
A) [option]  B) [option]  C) [option]

*3.* [question]
A) [option]  B) [option]  C) [option]

*4.* [question]
A) [option]  B) [option]  C) [option]

━━━━━━━━━━━━━━━━━━━━
🇩🇪 *NIEMIECKI — 3 pytania*

*5.* [question about German content]
A) [option]  B) [option]  C) [option]

*6.* [question]
A) [option]  B) [option]  C) [option]

*7.* [question]
A) [option]  B) [option]  C) [option]

━━━━━━━━━━━━━━━━━━━━
🔑 *Odpowiedzi* ↓↓↓
||1-? 2-? 3-? 4-? 5-? 6-? 7-?||

💪 Dobra robota w tym tygodniu\\! Odpoczywaj w weekend 🎉

Make questions directly based on the lesson content above.
Use || || spoiler tags for answers so they are hidden in Telegram.
Write the answers line as: ||1-B 2-A 3-C 4-A 5-B 6-C 7-A|| (replace with correct letters)"""

    r = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 900,
            "temperature": 0.6,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ─── Telegram ─────────────────────────────────────────────────────────────────

def send_telegram(text: str) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "MarkdownV2",
        },
        timeout=10,
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    lessons = get_week_lessons()
    print(f"📚 Lessons this week: {len(lessons)}")

    test = generate_test(lessons)
    send_telegram(test)
    print("✅ Weekly test sent!")


if __name__ == "__main__":
    main()
