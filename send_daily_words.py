#!/usr/bin/env python3
"""
Daily German (B1) vocabulary -> Telegram, with simple Leitner-style spaced repetition.

Each run:
  1. Finds every chat that has messaged the bot.
  2. Picks a few brand-new words/connectors.
  3. Picks a few previously-seen ones that are "due" for review today.
  4. Sends them all in one Telegram message to every chat.
  5. Advances each sent word's box/next_due date and writes the file back.

Env vars required:
  TELEGRAM_BOT_TOKEN  - token from @BotFather

Optional env vars:
  VOCAB_FILE   - path to the vocab JSON (default: vocab_b1_de_uk.json)
  CHATS_FILE   - path to known chat ids JSON (default: telegram_chats.json)
  NUM_NEW      - how many new words per day (default: 3)
  NUM_REVIEW   - how many review words per day (default: 5)
"""

import json
import os
import sys
from datetime import date, timedelta

import requests

VOCAB_FILE = os.environ.get("VOCAB_FILE", "vocab_b1_de_uk.json")
CHATS_FILE = os.environ.get("CHATS_FILE", "telegram_chats.json")
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


def load_chat_ids(path):
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {str(chat_id) for chat_id in data}


def save_chat_ids(path, chat_ids):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(chat_ids, key=int), f, indent=2)
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


def chat_from_update(update):
    if "message" in update:
        return update["message"].get("chat")
    if "my_chat_member" in update:
        return update["my_chat_member"].get("chat")
    if "callback_query" in update:
        return update["callback_query"].get("message", {}).get("chat")
    return None


def sync_chat_ids(token, known_chat_ids):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    updates = resp.json().get("result", [])

    for update in updates:
        chat = chat_from_update(update)
        if chat and chat.get("id") is not None:
            known_chat_ids.add(str(chat["id"]))

    if updates:
        last_update_id = updates[-1]["update_id"]
        requests.get(url, params={"offset": last_update_id + 1}, timeout=15)

    return known_chat_ids


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Missing TELEGRAM_BOT_TOKEN", file=sys.stderr)
        sys.exit(1)

    chat_ids = sync_chat_ids(token, load_chat_ids(CHATS_FILE))
    if not chat_ids:
        print("No chats yet. Have someone message the bot first.", file=sys.stderr)
        sys.exit(1)

    save_chat_ids(CHATS_FILE, chat_ids)

    today = date.today()
    today_str = today.isoformat()

    vocab = load_vocab(VOCAB_FILE)
    new_words, due_words = pick_words(vocab, today_str)

    if not new_words and not due_words:
        print("Nothing new or due today - skipping send.")
        return

    message = format_message(new_words, due_words)
    for chat_id in sorted(chat_ids, key=int):
        send_telegram_message(token, chat_id, message)
        print(f"Message sent to chat {chat_id}.")

    for w in new_words + due_words:
        advance_word(w, today)

    save_vocab(VOCAB_FILE, vocab)
    print("Vocab file updated.")


if __name__ == "__main__":
    main()
