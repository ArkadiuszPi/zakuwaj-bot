"""
Zakuwaj Bot v2 — Weekly Test
Sends questions one at a time with A/B/C/D options.
User replies with letter, bot confirms and sends next question.
"""

import os, json, random, requests, base64
from datetime import datetime, timezone, timedelta

GROQ_API_KEY     = os.environ["GROQ_API_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_TOKEN     = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO      = os.environ.get("GITHUB_REPOSITORY", "")

LOG_FILE  = "data/lessons_log.json"
TEST_FILE = "data/test_state.json"

def groq(prompt, max_tokens=800, temperature=0.6):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        },
        timeout=30
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

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
        "message": f"test update {datetime.now(timezone.utc).strftime('%H:%M')}",
        "content": base64.b64encode(json.dumps(data, indent=2, ensure_ascii=False).encode()).decode()
    }
    if sha: body["sha"] = sha
    requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
        json=body, timeout=10
    )

def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
        timeout=10
    )

def get_week_lessons():
    log, _ = read_file(LOG_FILE)
    if not isinstance(log, list): return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    return [l for l in log if datetime.fromisoformat(l["ts"]) > cutoff]

def generate_questions(lessons):
    en = [l for l in lessons if l["lang"] == "EN"]
    de = [l for l in lessons if l["lang"] == "DE"]
    en_ctx = "\n---\n".join(l["content"][:300] for l in en[-8:]) or "General B2/C1 English"
    de_ctx = "\n---\n".join(l["content"][:200] for l in de[-5:]) or "General A1/A2 German"

    prompt = f"""Create 7 quiz questions based on these lessons.
English lessons: {en_ctx}
German lessons: {de_ctx}

Return ONLY a valid JSON array, nothing else:
[
  {{
    "lang": "EN",
    "question": "What does the phrasal verb 'give up' mean?",
    "options": {{"A": "to start something", "B": "to quit/stop trying", "C": "to give a gift", "D": "to wake up early"}},
    "answer": "B",
    "explanation": "Give up = rezygnować, poddawać się. Np. 'Don't give up on your dreams!'"
  }},
  ...
]

Make 4 English questions and 3 German questions.
Base them on the actual lesson content above.
Explanations should be in Polish."""

    raw = groq(prompt, max_tokens=1200, temperature=0.5)

    # Extract JSON
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(raw[start:end])
    return []

def send_first_question():
    """Generate test and send question 1"""
    lessons = get_week_lessons()
    questions = generate_questions(lessons)

    if not questions:
        send("❌ Brak lekcji z tego tygodnia — wróć w przyszłym tygodniu!")
        return

    # Save test state
    test_state = {
        "questions": questions,
        "current": 0,
        "score": 0,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }
    _, sha = read_file(TEST_FILE)
    write_file(TEST_FILE, test_state, sha)

    today = datetime.now().strftime("%d.%m.%Y")
    en_count = len([l for l in lessons if l["lang"] == "EN"])
    de_count = len([l for l in lessons if l["lang"] == "DE"])

    intro = f"""🎯 *PIĄTKOWY TEST JĘZYKOWY*
📅 {today}

📊 *Ten tydzień:* {en_count} lekcji EN + {de_count} lekcji DE

Odpowiadaj literą: *A*, *B*, *C* lub *D*
━━━━━━━━━━━━━━━━━━━━"""
    send(intro)

    # Send question 1
    send_question(questions, 0)

def send_question(questions, idx):
    q = questions[idx]
    flag = "🇬🇧" if q["lang"] == "EN" else "🇩🇪"
    total = len(questions)

    msg = f"""{flag} *Pytanie {idx+1}/{total}*

{q['question']}

A) {q['options']['A']}
B) {q['options']['B']}
C) {q['options']['C']}
D) {q['options']['D']}"""
    send(msg)

def check_answer():
    """Called when user sends answer — check and send next question"""
    answer = os.environ.get("USER_ANSWER", "").upper().strip()

    test_state, sha = read_file(TEST_FILE)
    if not test_state or "questions" not in test_state:
        send("❌ Brak aktywnego testu. Poczekaj do piątku!")
        return

    questions = test_state["questions"]
    idx = test_state["current"]
    score = test_state["score"]

    if idx >= len(questions):
        send("✅ Test już zakończony!")
        return

    q = questions[idx]
    correct = q["answer"]
    is_correct = answer == correct

    if is_correct:
        score += 1
        feedback = f"✅ *Dobrze!* {q['explanation']}"
    else:
        feedback = f"❌ *Błąd!* Poprawna odpowiedź: *{correct}*\n{q['explanation']}"

    send(feedback)

    next_idx = idx + 1
    test_state["current"] = next_idx
    test_state["score"] = score
    write_file(TEST_FILE, test_state, sha)

    if next_idx < len(questions):
        send_question(questions, next_idx)
    else:
        total = len(questions)
        pct = int(score / total * 100)
        if pct >= 80:
            emoji = "🏆"
        elif pct >= 60:
            emoji = "👍"
        else:
            emoji = "💪"

        send(f"""{emoji} *Koniec testu!*

Wynik: *{score}/{total}* ({pct}%)

{"Znakomicie! Tak trzymaj! 🌟" if pct >= 80 else "Dobra robota! Ćwicz dalej! 💪" if pct >= 60 else "Nie poddawaj się! Z każdym dniem lepiej! 🚀"}

Do zobaczenia w przyszłym tygodniu! 📚""")

def main():
    mode = os.environ.get("TEST_MODE", "start")
    if mode == "start":
        send_first_question()
    elif mode == "answer":
        check_answer()

if __name__ == "__main__":
    main()
