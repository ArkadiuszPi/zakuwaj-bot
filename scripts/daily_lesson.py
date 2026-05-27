"""
Language Learning Bot — daily lesson sender
Sends English (B2/C1) and German (A1/A2) lessons via Telegram.
"""

import os
import json
import random
import requests
import base64
from datetime import datetime, timezone, timedelta

PERPLEXITY_API_KEY = os.environ["PERPLEXITY_API_KEY"]
TELEGRAM_TOKEN     = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO        = os.environ.get("GITHUB_REPOSITORY", "")

LOG_FILE = "data/lessons_log.json"

# ─── Lesson topic pools ───────────────────────────────────────────────────────

EN_TOPICS = [
    "a useful B2/C1 idiom related to work, daily life, or emotions",
    "an advanced vocabulary word (C1 level) with nuance between similar words",
    "a common grammar mistake Polish speakers make in English — and how to fix it",
    "a phrasal verb used in everyday conversation",
    "a business/professional English expression",
    "a collocations pair (verb+noun or adjective+noun) at C1 level",
    "a confusing word pair (e.g. affect/effect, lie/lay) explained clearly",
    "an American vs British English difference worth knowing",
]

DE_TOPICS = [
    "a basic everyday German phrase for shopping or transport (A1/A2)",
    "German numbers, time or date expressions",
    "a simple German greeting or polite social expression",
    "basic German vocabulary for food or household items",
    "a beginner German sentence structure tip (A1/A2)",
    "a false friend between German and Polish or English",
    "German modal verb (kann/muss/will) in a simple sentence",
]

# ─── Perplexity API call ──────────────────────────────────────────────────────

def get_lesson() -> tuple[str, str]:
    lang = random.choices(["english", "german"], weights=[65, 35])[0]
    topic = random.choice(EN_TOPICS if lang == "english" else DE_TOPICS)

    if lang == "english":
        prompt = f"""You are an engaging English teacher. Your student is Polish, level B2/C1.
Create a short practical lesson about: {topic}

Use EXACTLY this format:

🇬🇧 *LEKCJA ANGIELSKIEGO*

📖 *{topic.title()[:40]}*

[main explanation — clear, direct, max 2 sentences]

✏️ *Przykład:*
➜ [example sentence in English]
🇵🇱 [Polish translation]

💡 *Tip:* [one memorable practical tip]

#english #b2 #c1"""

    else:
        prompt = f"""You are an encouraging German teacher. Your student is Polish, complete beginner (A1/A2).
Create a short practical lesson about: {topic}

Use EXACTLY this format:

🇩🇪 *LEKCJA NIEMIECKIEGO*

📖 *{topic.title()[:40]}*

[main explanation — simple, clear, max 2 sentences]

✏️ *Przykład:*
➜ [example sentence in German]
🇵🇱 [Polish translation]

💡 *Zapamiętaj:* [simple memory trick or grammar note]

#deutsch #a1 #a2"""

    r = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 400,
            "temperature": 0.92,
        },
        timeout=20,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return content, lang


# ─── Telegram ────────────────────────────────────────────────────────────────

def send_telegram(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    return r.status_code == 200


# ─── Lesson log (stored as JSON in repo via GitHub API) ──────────────────────

def read_log() -> tuple[list, str | None]:
    if not GITHUB_TOKEN:
        return [], None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{LOG_FILE}"
    r = requests.get(url, headers=_gh_headers(), timeout=10)
    if r.status_code == 200:
        data = r.json()
        lessons = json.loads(base64.b64decode(data["content"]).decode())
        return lessons, data["sha"]
    return [], None


def write_log(lessons: list, sha: str | None) -> None:
    if not GITHUB_TOKEN:
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{LOG_FILE}"
    # Keep only last 60 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    lessons = [l for l in lessons if datetime.fromisoformat(l["ts"]) > cutoff]
    body = {
        "message": f"lesson log {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
        "content": base64.b64encode(
            json.dumps(lessons, indent=2, ensure_ascii=False).encode()
        ).decode(),
    }
    if sha:
        body["sha"] = sha
    requests.put(url, headers=_gh_headers(), json=body, timeout=10)


def _gh_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Each run fires every 30 min. Random skip keeps average ~1–2 msg/hour.
    # skip_chance=0.25 → ~1.5 lessons/hour on average
    if random.random() < 0.25:
        print("⏭️  Skipped this run (random throttle)")
        return

    lesson, lang = get_lesson()

    lessons, sha = read_log()
    lessons.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "lang": lang,
        "content": lesson,
    })
    write_log(lessons, sha)

    ok = send_telegram(lesson)
    flag = "🇬🇧" if lang == "english" else "🇩🇪"
    print(f"{'✅' if ok else '❌'} {flag}  {lang} lesson sent")


if __name__ == "__main__":
    main()
