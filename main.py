import logging
import os
import time
import telebot
from telebot.types import BotCommand
from config import (
    TELEGRAM_BOT_TOKEN,
    DB_PATH,
    VOICES_DIR,
    ADMIN_IDS,
    USE_WEBHOOK,
    WEBHOOK_BASE_URL,
    PORT,
)
from db import Database
from admin_panel import register_admin_handlers
from user_panel import register_user_handlers
from scheduler import start_expiry_cleanup_thread


def set_commands(bot: telebot.TeleBot):
    commands = [
        BotCommand("start", "Start"),
        BotCommand("admin", "Admin panel"),
    ]
    try:
        bot.set_my_commands(commands)
    except Exception:
        pass


def notify_admin_online(bot: telebot.TeleBot):
    try:
        me = bot.get_me()
        msg = f"Bot @{me.username} is online."
    except Exception:
        msg = "Bot is online."

    for aid in (ADMIN_IDS[:1] if ADMIN_IDS else []):
        try:
            bot.send_message(aid, msg)
        except Exception:
            pass


def main():
    logging.basicConfig(level=logging.INFO)
    try:
        telebot.logger.setLevel(logging.DEBUG)
    except Exception:
        pass

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    os.makedirs(VOICES_DIR, exist_ok=True)

    db = Database(DB_PATH)
    # ensure fixed admins exist in DB
    for aid in ADMIN_IDS:
        try:
            db.add_admin(int(aid))
        except Exception:
            pass

    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

    # ✅ IMPORTANT: admin first, then user
    register_admin_handlers(bot, db)
    register_user_handlers(bot, db)

    set_commands(bot)
    start_expiry_cleanup_thread(db, bot)

    allowed_updates = ['message', 'callback_query']

    # -------------------------
    # WEBHOOK MODE
    # -------------------------
    if USE_WEBHOOK and WEBHOOK_BASE_URL:
        try:
            from flask import Flask, request
        except Exception as e:
            logging.error(f"Flask not installed; falling back to polling: {e}")
            try:
                bot.remove_webhook()
            except Exception:
                pass
            notify_admin_online(bot)
            bot.infinity_polling(skip_pending=True, allowed_updates=allowed_updates)
            return

        app = Flask(__name__)

        @app.get("/health")
        def health():
            return "OK", 200

        @app.post(f"/{TELEGRAM_BOT_TOKEN}")
        def telegram_webhook():
            try:
                json_str = request.get_data().decode("utf-8")
                update = telebot.types.Update.de_json(json_str)
                bot.process_new_updates([update])
            except Exception as e:
                logging.exception(f"Webhook processing error: {e}")
                return "ERROR", 500
            return "OK", 200

        webhook_url = WEBHOOK_BASE_URL.rstrip("/") + f"/{TELEGRAM_BOT_TOKEN}"

        # always clear old webhook first
        try:
            bot.remove_webhook()
        except Exception:
            pass

        # retries to avoid 429
        for attempt in range(3):
            try:
                bot.set_webhook(url=webhook_url)
                break
            except Exception as e:
                logging.warning(f"set_webhook failed (attempt {attempt+1}): {e}")
                time.sleep(1 + attempt)
        else:
            bot.set_webhook(url=webhook_url)

        try:
            me = bot.get_me()
            logging.info(f"Bot started webhook as @{me.username} -> {webhook_url}")
        except Exception:
            logging.info(f"Bot started webhook -> {webhook_url}")

        notify_admin_online(bot)

        app.run(host="0.0.0.0", port=int(PORT))

    # -------------------------
    # POLLING MODE
    # -------------------------
    else:
        try:
            bot.remove_webhook()
        except Exception:
            pass

        try:
            me = bot.get_me()
            logging.info(f"Bot started polling as @{me.username}")
        except Exception:
            logging.info("Bot started polling")

        notify_admin_online(bot)
        bot.infinity_polling(skip_pending=True, allowed_updates=allowed_updates)


if __name__ == "__main__":
    main()
