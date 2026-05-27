# 🤖 Language Learning Bot

Telegram bot wysyłający lekcje angielskiego (B2/C1) i niemieckiego (A1/A2) co ~1–2 godziny, z testem co piątek o 20:00.

**Koszt: ~$2–3/miesiąc z $5 kredytów Perplexity Pro → praktycznie za darmo.**

---

## ⚙️ Konfiguracja — 4 kroki

### Krok 1 — Utwórz bota na Telegramie (5 minut)

1. Otwórz Telegram → wyszukaj **@BotFather**
2. Wyślij `/newbot`
3. Podaj nazwę bota, np. `Mój Bot Językowy`
4. Podaj username, np. `mojbot_jezyk_bot` (musi kończyć się na `_bot`)
5. Skopiuj **TOKEN** który dostaniesz (wygląda tak: `7123456789:AAFxxx...`)

**Pobierz swój CHAT_ID:**
1. Wyślij **dowolną wiadomość** do swojego nowego bota
2. Otwórz w przeglądarce:
   ```
   https://api.telegram.org/bot<TWÓJ_TOKEN>/getUpdates
   ```
3. W odpowiedzi JSON znajdź `"id"` w sekcji `"chat"` — to Twój **CHAT_ID**

---

### Krok 2 — Pobierz klucz Perplexity API

1. Wejdź na **perplexity.ai** → Settings → API
2. Kliknij **Generate** → skopiuj klucz API
3. (Masz $5/miesiąc kredytów jako subskrybent Pro)

---

### Krok 3 — Utwórz repozytorium na GitHub

1. Zaloguj się na **github.com** → kliknij **New repository**
2. Nazwa: `language-bot`, zaznacz **Private**, kliknij Create
3. Wgraj wszystkie pliki z tego projektu do repo (lub użyj GitHub Desktop)
4. Upewnij się że `data/lessons_log.json` zawiera tylko: `[]`

---

### Krok 4 — Dodaj Secrets do GitHub

W repozytorium: **Settings → Secrets and variables → Actions → New repository secret**

Dodaj trzy sekrety:

| Name | Value |
|------|-------|
| `PERPLEXITY_API_KEY` | klucz z kroku 2 |
| `TELEGRAM_TOKEN` | token z kroku 1 |
| `TELEGRAM_CHAT_ID` | chat ID z kroku 1 |

> `GITHUB_TOKEN` jest dodawany automatycznie przez GitHub — nic nie rób.

---

## ✅ Gotowe!

Bot uruchomi się automatycznie. Możesz też przetestować ręcznie:
- **Actions** → `Language Lesson Bot` → **Run workflow**

---

## 📅 Harmonogram

| Co | Kiedy |
|----|-------|
| Lekcja EN lub DE | losowo co 30–60 min, 8:00–20:00 (CEST) |
| Test tygodniowy | każdy piątek o 20:00 (CEST) |

**Proporcje języków:** ~65% angielski, ~35% niemiecki

---

## 💰 Szacowany koszt API

- ~15 lekcji/dzień × 30 dni = ~450 zapytań/miesiąc
- Koszt Sonar model: ~$2.50/miesiąc
- Masz $5/miesiąc z Perplexity Pro → zostaje ~$2.50 zapasu ✅

---

## 🗂️ Struktura projektu

```
language-bot/
├── scripts/
│   ├── daily_lesson.py      # wysyła lekcję
│   └── weekly_test.py       # wysyła piątkowy test
├── .github/
│   └── workflows/
│       ├── lesson.yml       # cron co 30 min
│       └── weekly_test.yml  # cron w piątki 20:00
├── data/
│   └── lessons_log.json     # historia lekcji (auto-update)
└── README.md
```

---

## 🔧 Dostosowanie

W `scripts/daily_lesson.py` możesz zmienić:
- `weights=[65, 35]` → proporcje EN vs DE
- `skip_chance=0.25` → częstotliwość (0.0 = zawsze, 0.5 = połowa razy)

W `.github/workflows/lesson.yml` możesz zmienić godziny (pamiętaj: UTC, nie CEST).
