# Ariyan Voice Bot — Railway Deployment

This project is a Telegram bot that generates voice messages using Fish Audio TTS. It supports local polling and webhook mode for Railway deployment.

## Requirements

- Python 3.11+
- Telegram bot token
- Fish Audio API key

## Configuration

Set these environment variables in Railway (Variables):

- `TELEGRAM_BOT_TOKEN` — your bot token
- `FISH_AUDIO_API_KEY` — Fish Audio key
- `ADMIN_IDS` — comma-separated Telegram user IDs allowed as admins (optional)
- `MAX_TTS_CHARS` — default `200`
- `FISH_AUDIO_BASE_URL` — default `https://api.fish.audio`
- `FISH_AUDIO_BACKEND` — default `s1`

Webhook / Railway:
- `USE_WEBHOOK=true`
- `WEBHOOK_BASE_URL=https://<your-railway-domain>` (no trailing slash)
- `PORT` — provided automatically by Railway

Persistence (recommended):
- `DB_PATH=/data/file.db`
- `VOICES_DIR=/data/voices`

Attach a Railway Volume and mount at `/data` to persist database and generated audio files.

## Start Command

The project includes a `Procfile`:

```
web: python main.py
```

Alternatively, set the service Start Command in Railway to `python main.py`.

## What Happens on Railway

- The bot starts a small Flask server and sets Telegram webhook to `WEBHOOK_BASE_URL/<TELEGRAM_BOT_TOKEN>`.
- Flask listens on `0.0.0.0:$PORT`.
- Telegram sends updates to your Railway URL; the bot processes them.

## Local Development

Keep `USE_WEBHOOK` unset and `WEBHOOK_BASE_URL` empty to run local polling:

```
python main.py
```

## Admin Panel

- `/admin` opens the admin menu.
- Manage credits/validity with per-user inline buttons.
- Download Data sends the SQLite database file (`file.db`) directly.

## Notes

- Webhook requires HTTPS. Ensure Public Networking is enabled on Railway.
- Disk is ephemeral without a volume; attach one for persistence.
- Audio files are saved under `VOICES_DIR` by user ID.