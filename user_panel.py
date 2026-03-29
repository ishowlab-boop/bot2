import os
import re
from datetime import datetime
import telebot
from telebot import types
from config import (
    ADMIN_CONTACT,
    WEBSITE_URL,
    COST_PER_VOICE,
    VOICES_DIR,
    REQUIRE_VALIDITY_FOR_TTS,
    MAX_TTS_CHARS,
    DEFAULT_MODELS,  # ✅ NEW
)
from fish_audio import FishAudioClient


def build_user_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.row(types.KeyboardButton("Select Model"), types.KeyboardButton("Plans"))
    kb.row(types.KeyboardButton("Usage"), types.KeyboardButton("Voice Speed"))
    kb.row(types.KeyboardButton("Contact Admin"), types.KeyboardButton("Our Website"))
    return kb


def build_models_keyboard(models):
    kb = types.InlineKeyboardMarkup()
    row = []
    for m in models:
        label = m.get("name") or m.get("id")
        row.append(types.InlineKeyboardButton(text=label, callback_data=f"model:{m.get('id')}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    return kb


def get_model_name(models, voice_id: str) -> str:
    for m in models:
        if (m.get("id") or "") == (voice_id or ""):
            return m.get("name") or voice_id
    return voice_id or "Unknown"


def humanize_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace(", ", ", … ")
    s = s.replace("!", "!\n").replace("?", "?\n").replace(".", ".\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def build_speed_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("⚡ Fast", callback_data="speed:fast"),
        types.InlineKeyboardButton("🙂 Natural", callback_data="speed:natural"),
    )
    kb.row(
        types.InlineKeyboardButton("😐 Normal", callback_data="speed:normal"),
        types.InlineKeyboardButton("🐢 Slow", callback_data="speed:slow"),
    )
    return kb


def speed_to_value(mode: str) -> float:
    mode = (mode or "natural").lower()
    return {
        "fast": 1.08,
        "normal": 1.00,
        "natural": 0.94,
        "slow": 0.88,
    }.get(mode, 0.94)


def speed_to_label(mode: str) -> str:
    mode = (mode or "natural").lower()
    return {"fast": "Fast", "normal": "Normal", "natural": "Natural", "slow": "Slow"}.get(mode, "Natural")


def register_user_handlers(bot: telebot.TeleBot, db):
    client = FishAudioClient()

    @bot.message_handler(commands=["start"])
    def cmd_start(message: types.Message):
        db.ensure_user(message.from_user.id, message.from_user.username)
        bot.send_message(message.chat.id, "Welcome! Use the buttons below.", reply_markup=build_user_keyboard())

    @bot.message_handler(func=lambda m: m.text == "Contact Admin")
    def contact_admin(message: types.Message):
        bot.send_message(message.chat.id, f"Contact admin: {ADMIN_CONTACT}")

    @bot.message_handler(func=lambda m: m.text == "Our Website")
    def website(message: types.Message):
        bot.send_message(message.chat.id, f"Website: {WEBSITE_URL}")

    @bot.message_handler(func=lambda m: m.text == "Plans")
    def plans(message: types.Message):
        from config import PLANS
        lines = ["Available plans:"]
        for p in PLANS:
            lines.append(f"• {p['name']}: {p['credits']} credits, {p['price']}, validity {p['validity_days']} days")
        bot.send_message(message.chat.id, "\n".join(lines))

    @bot.message_handler(func=lambda m: m.text == "Voice Speed")
    def voice_speed_menu(message: types.Message):
        bot.send_message(message.chat.id, "Choose voice speed:", reply_markup=build_speed_keyboard())

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("speed:"))
    def speed_chosen(callback: types.CallbackQuery):
        mode = callback.data.split(":", 1)[1].strip().lower()
        db.update_user_fields(callback.from_user.id, {"tts_speed": mode})
        bot.send_message(callback.message.chat.id, f"✅ Speed set to: <b>{speed_to_label(mode)}</b>")
        bot.answer_callback_query(callback.id)

    @bot.message_handler(func=lambda m: m.text == "Usage")
    def usage(message: types.Message):
        user = db.get_user(message.from_user.id)
        voices = db.list_user_voices(message.from_user.id)
        models = client.list_models()

        selected_id = user.get("selected_model")
        selected_name = get_model_name(models, selected_id) if selected_id else "Not selected"

        # ✅ NEW: default voice id from admin panel (DB settings)
        default_voice_id = db.get_setting("default_voice_id", DEFAULT_MODELS[0]["id"])
        default_voice_name = get_model_name(models, default_voice_id)

        mode = (user.get("tts_speed") or "natural").strip().lower()

        bot.send_message(
            message.chat.id,
            f"Status: {'Premium' if user.get('is_premium') else 'Normal'}\n"
            f"Credits: {user.get('credits') or 0}\n"
            f"Validity: {user.get('validity_expire_at') or 'No validity'}\n"
            f"Selected model: {selected_name}\n"
            f"Default voice: {default_voice_name}\n"
            f"Speed: {speed_to_label(mode)}\n"
            f"Voices saved: {len(voices)}",
        )

    @bot.message_handler(func=lambda m: m.text == "Select Model")
    def select_model(message: types.Message):
        models = client.list_models()
        bot.send_message(message.chat.id, "Choose a model:", reply_markup=build_models_keyboard(models))

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("model:"))
    def model_chosen(callback: types.CallbackQuery):
        voice_id = callback.data.split(":", 1)[1]
        db.update_user_fields(callback.from_user.id, {"selected_model": voice_id})
        model_name = get_model_name(client.list_models(), voice_id)
        bot.send_message(callback.message.chat.id, f"✅ Model selected: <b>{model_name}</b>\nNow send text to generate voice.")
        bot.answer_callback_query(callback.id)

    @bot.message_handler(content_types=["text"])
    def tts_entry(message: types.Message):
        txt = (message.text or "").strip()

        if txt in ("Select Model", "Plans", "Usage", "Contact Admin", "Our Website", "Voice Speed"):
            return

        if len(txt) > MAX_TTS_CHARS:
            bot.send_message(message.chat.id, f"Text too long. Limit: {MAX_TTS_CHARS} characters.")
            return

        user = db.get_user(message.from_user.id)
        credits = user.get("credits") or 0

        if credits <= 0:
            bot.send_message(message.chat.id, "❌ You have no credits.")
            return

        if REQUIRE_VALIDITY_FOR_TTS and not db.is_valid(message.from_user.id):
            bot.send_message(message.chat.id, "❌ Your validity expired.")
            return

        model = user.get("selected_model")

        # ✅ NEW: If user didn't select model, use admin-set default voice id
        if not model:
            model = db.get_setting("default_voice_id", DEFAULT_MODELS[0]["id"])

        mode = (user.get("tts_speed") or "natural").strip().lower()
        spd = speed_to_value(mode)

        txt_natural = humanize_text(txt)

        try:
            audio_bytes = client.synthesize_text(
                txt_natural,
                model,
                language="en",
                format_="opus",
                speed=spd,
                latency="slow",
            )
        except Exception as e:
            bot.send_message(message.chat.id, f"TTS error: {e}")
            return

        user_dir = os.path.join(VOICES_DIR, str(message.from_user.id))
        os.makedirs(user_dir, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ogg_path = os.path.join(user_dir, f"tts_{ts}.ogg")

        with open(ogg_path, "wb") as f:
            f.write(audio_bytes)

        with open(ogg_path, "rb") as vf:
            bot.send_voice(message.chat.id, vf)

        db.store_voice(message.from_user.id, ogg_path)
        db.remove_credits(message.from_user.id, COST_PER_VOICE)

        model_name = get_model_name(client.list_models(), model)
        bot.send_message(
            message.chat.id,
            f"🎙️ Voice generated! (Model: <b>{model_name}</b>, Speed: <b>{speed_to_label(mode)}</b>)\n"
            f"1 credit deducted. Remaining: {credits - 1}"
        )
