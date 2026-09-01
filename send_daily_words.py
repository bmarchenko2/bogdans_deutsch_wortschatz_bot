#!/usr/bin/env python3
"""
Daily German (B1) vocabulary -> Telegram, with simple Leitner-style spaced repetition.

Each run:
  1. Picks a few brand-new words/connectors.
  2. Picks a few previously-seen ones that are "due" for review today.
  3. Sends them all in one Telegram message.
  4. Advances each sent word's box/next_due date and writes the file back.

Env vars required:
  TELEGRAM_BOT_TOKEN  - token from @BotFather
  TELEGRAM_CHAT_ID    - your personal chat id (see README)

Optional env vars:
  VOCAB_FILE   - path to the vocab JSON (default: vocab_b1_de_uk.json)
  NUM_NEW      - how many new words per day (default: 3)
  NUM_REVIEW   - how many review words per day (default: 5)
"""

import json
import os
import sys
from datetime import date, timedelta

import requests

VOCAB_FILE = os.environ.get("VOCAB_FILE", "vocab_b1_de_uk.json")
NUM_NEW = int(os.environ.get("NUM_NEW", "3"))
NUM_REVIEW = int(os.environ.get("NUM_REVIEW", "5"))

# Days until the next review, indexed by box number (Leitner-style).
INTERVALS = [1, 3, 7, 14, 30, 60, 120]
MAX_BOX = len(INTERVALS) - 1


def load_vocab(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_vocab(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def pick_words(vocab, today_str):
    new_words = [w for w in vocab if w["status"] == "new"][:NUM_NEW]

    due_words = [
        w for w in vocab
        if w["status"] != "new" and (w["next_due"] is None or w["next_due"] <= today_str)
    ]
    due_words.sort(key=lambda w: w["next_due"] or "")
    due_words = due_words[:NUM_REVIEW]

    return new_words, due_words


def advance_word(word, today):
    if word["status"] == "new":
        word["status"] = "learning"
        word["box"] = 1
    else:
        word["box"] = min(word["box"] + 1, MAX_BOX)
        word["status"] = "mastered" if word["box"] >= MAX_BOX else "learning"

    word["next_due"] = (today + timedelta(days=INTERVALS[word["box"]])).isoformat()


def format_message(new_words, due_words):
    lines = []
    if new_words:
        lines.append("🆕 *Нові слова*")
        for w in new_words:
            lines.append(f"*{w['word']}* — {w['translation']}\n_{w['example']}_")
        lines.append("")
    if due_words:
        lines.append("🔁 *Повторення*")
        for w in due_words:
            lines.append(f"*{w['word']}* — {w['translation']}\n_{w['example']}_")
    return "\n\n".join(lines).strip()


def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID", file=sys.stderr)
        sys.exit(1)

    today = date.today()
    today_str = today.isoformat()

    vocab = load_vocab(VOCAB_FILE)
    new_words, due_words = pick_words(vocab, today_str)

    if not new_words and not due_words:
        print("Nothing new or due today - skipping send.")
        return

    message = format_message(new_words, due_words)
    send_telegram_message(token, chat_id, message)
    print("Message sent.")

    for w in new_words + due_words:
        advance_word(w, today)

    save_vocab(VOCAB_FILE, vocab)
    print("Vocab file updated.")


if __name__ == "__main__":
    main()
