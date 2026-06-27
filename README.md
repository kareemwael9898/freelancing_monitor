# Freelance Projects Monitor (Nafezly & Mostaql)

A lightweight automated monitor that scrapes the Nafezly and Mostaql projects lists every 30 minutes, filters by mobile/app/IoT development keywords, and sends notifications directly to your Telegram chat.

## Features
- **Auto-run**: Runs every 30 minutes via GitHub Actions.
- **State persistence**: Keeps track of processed project IDs from both platforms using `state.json` to prevent duplicate alerts.
- **Filter-matching**: Filters projects by keywords (e.g. Flutter, Android, iOS, mobile apps, IoT, smart devices) in both English and Arabic.
- **Telegram Notifications**: Formatted HTML alerts sent to your Telegram chat with project title, budget, duration, platform source, and direct link.

---

## Setup Instructions

### 1. Create a Telegram Bot
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the instructions to get your **Bot API Token** (looks like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).
3. Search for `@userinfobot` or `@GetMyChatID_Bot` and send a message to get your **Chat ID** (looks like `987654321` or a negative number for group chats).
4. Send a test message or click "Start" on your bot to initialize the chat session.

### 2. Configure GitHub Secrets
Push this repository to GitHub, and go to:
**Settings > Secrets and variables > Actions > New repository secret**

Add the following two secrets:
- `TELEGRAM_BOT_TOKEN`: The API token from `@BotFather`.
- `TELEGRAM_CHAT_ID`: Your chat ID.

### 3. Local Dry Run
To test the script locally without triggering Telegram messages (or if you want to see what matches on the front page right now):
```bash
python3 monitor.py --dry-run
```

---

## Modifying Keywords
You can edit the `KEYWORDS` list directly inside `monitor.py` to add or remove terms you want to monitor.
```python
KEYWORDS = [
    # English keywords
    'app', 'flutter', 'mobile', 'android', 'ios', 'swift', 'kotlin', ...
    # Arabic keywords
    'فلاتر', 'تطبيق', 'تطبيقات', ...
]
```
