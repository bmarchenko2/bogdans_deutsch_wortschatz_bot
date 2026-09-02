# Daily German (B1) Vocabulary → Telegram

Sends a few new German words plus a few due-for-review ones to everyone who
has messaged the bot, via a GitHub Actions cron job. No server needed.

## 1. Create a Telegram bot

1. Open Telegram, message **@BotFather**, send `/newbot`, follow the prompts.
2. Copy the token it gives you (looks like `123456789:AA...`).
3. Anyone who wants daily words should send any message (e.g. "hi") to the bot.
   The bot remembers every chat in `telegram_chats.json`.

## 2. Push this repo to GitHub

Create a new repo and push these files, keeping the `.github/workflows/`
folder structure intact.

## 3. Add your secrets

In the repo: **Settings → Secrets and variables → Actions → New repository
secret**, add:

- `TELEGRAM_BOT_TOKEN`

Everyone gets the same words; progress is tracked once in `vocab_b1_de_uk.json`.

## 4. Done

The workflow (`.github/workflows/daily-vocab.yml`) runs once a day, sends
new + review words, and commits the updated progress back to
`vocab_b1_de_uk.json` so the next run knows what's already been sent.

You can also trigger it manually any time from the **Actions** tab
("Run workflow" button), useful for testing.

## How the spaced repetition works

Each word has a `box` (0–6). The first time a word is sent it moves to box 1
and comes back for review after 1 day; each successful re-send bumps it to
the next box with a longer gap (1 → 3 → 7 → 14 → 30 → 60 → 120 days), until
it's marked `mastered`. It's a one-way push (no reply tracking), so it just
assumes "seen it" counts as a review.

## Adjusting the daily amount

Set these as extra env vars in the workflow step if you want more or fewer
per day (defaults: 3 new, 5 review):

```yaml
env:
  NUM_NEW: "4"
  NUM_REVIEW: "6"
```

## Adding more vocabulary

Just add more entries to `vocab_b1_de_uk.json` in the same shape:

```json
{"word": "die Ahnung", "translation": "уявлення", "example": "Ich habe keine Ahnung.", "type": "word", "status": "new", "box": 0, "next_due": null}
```
