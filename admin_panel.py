from typing import Dict
import json
import re
from datetime import datetime

import telebot
from telebot import types

from config import DB_PATH, DEFAULT_MODELS


# -----------------------
# HELPERS
# -----------------------
def parse_int(text: str) -> int:
    nums = re.findall(r"\d+", text or "")
    if not nums:
        raise ValueError("No number found")
    return int(nums[0])


def pretty_date(iso: str) -> str:
    if not iso:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%A, %d %b %Y")
    except Exception:
        return iso


def _get_models_from_db(db):
    raw = db.get_setting("models_json", "")
    if raw:
        try:
            models = json.loads(raw)
            if isinstance(models, list) and models:
                out = []
                for m in models:
                    if isinstance(m, dict) and m.get("id"):
                        out.append({
                            "id": str(m["id"]).strip(),
                            "name": str(m.get("name") or m["id"]).strip(),
                        })
                if out:
                    return out
        except Exception:
            pass
    return DEFAULT_MODELS


def _set_models_to_db(db, models):
    db.set_setting("models_json", json.dumps(models, ensure_ascii=False))


def _get_default_voice_id(db, models=None):
    models = models or _get_models_from_db(db)
    default_id = (db.get_setting("default_voice_id", "") or "").strip()
    valid_ids = {(m.get("id") or "").strip() for m in models}
    if default_id in valid_ids:
        return default_id
    fallback = (models[0].get("id") or DEFAULT_MODELS[0]["id"]).strip()
    db.set_setting("default_voice_id", fallback)
    return fallback


def _short_id(voice_id: str, size: int = 10) -> str:
    voice_id = (voice_id or "").strip()
    if len(voice_id) <= size:
        return voice_id
    return f"{voice_id[:size]}..."


def _voice_summary_text(db, models):
    default_id = _get_default_voice_id(db, models)
    lines = ["🎛 <b>Manage Voices</b>"]
    for idx, m in enumerate(models, start=1):
        name = m.get("name") or "Voice"
        vid = (m.get("id") or "").strip()
        marker = " ✅ DEFAULT" if vid == default_id else ""
        lines.append(f"{idx}. {name} - <code>{_short_id(vid, 16)}</code>{marker}")
    lines.append("")
    lines.append("Select a voice button below to exchange ID or rename it.")
    return "\n".join(lines)


# -----------------------
# KEYBOARDS
# -----------------------
def build_admin_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Manage Credits", callback_data="admin:credits"))
    kb.add(types.InlineKeyboardButton("Manage Validity", callback_data="admin:validity"))
    kb.add(types.InlineKeyboardButton("List Users", callback_data="admin:list_users"))
    kb.add(types.InlineKeyboardButton("List Premium Users", callback_data="admin:list_premium"))
    kb.add(types.InlineKeyboardButton("Broadcast", callback_data="admin:broadcast"))
    kb.add(types.InlineKeyboardButton("Set Default Voice ID", callback_data="admin:default_voice"))
    kb.add(types.InlineKeyboardButton("Manage Voices", callback_data="admin:voices"))
    kb.add(types.InlineKeyboardButton("Download Data", callback_data="admin:download"))
    kb.add(types.InlineKeyboardButton("Manage Admins", callback_data="admin:admins"))
    return kb


def build_credit_action_keyboard(user_id: int):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Add Credits", callback_data=f"admin:credits:add:{user_id}"))
    kb.add(types.InlineKeyboardButton("➖ Remove Credits", callback_data=f"admin:credits:remove:{user_id}"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin:menu"))
    return kb


def build_validity_action_keyboard(user_id: int):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Set Validity", callback_data=f"admin:validity:set:{user_id}"))
    kb.add(types.InlineKeyboardButton("❌ Remove Validity", callback_data=f"admin:validity:remove:{user_id}"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin:menu"))
    return kb


def build_voices_keyboard(models):
    kb = types.InlineKeyboardMarkup()
    for idx, m in enumerate(models):
        name = m.get("name") or "Voice"
        kb.add(types.InlineKeyboardButton(f"🎙 {name}", callback_data=f"admin:voices:edit:{idx}"))
    kb.add(types.InlineKeyboardButton("➕ Add Voice", callback_data="admin:voices:add"))
    kb.add(types.InlineKeyboardButton("♻️ Reset Voices", callback_data="admin:voices:reset"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin:menu"))
    return kb


# -----------------------
# MAIN REGISTER
# -----------------------
def register_admin_handlers(bot: telebot.TeleBot, db):
    admin_steps: Dict[int, Dict] = {}

    def ensure_admin(uid: int):
        return db.is_admin(uid)

    @bot.message_handler(commands=["admin"])
    def admin_cmd(message):
        if not ensure_admin(message.from_user.id):
            return
        bot.send_message(message.chat.id, "⚙️ Admin Panel", reply_markup=build_admin_menu())

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("admin:"))
    def cb(callback):
        uid = callback.from_user.id
        if not ensure_admin(uid):
            return bot.answer_callback_query(callback.id)

        bot.answer_callback_query(callback.id)

        parts = callback.data.split(":")
        section = parts[1]

        if section == "menu":
            return bot.send_message(callback.message.chat.id, "⚙️ Admin Panel", reply_markup=build_admin_menu())

        if section == "credits" and len(parts) == 2:
            admin_steps[uid] = {"action": "credits_pick_user"}
            return bot.send_message(callback.message.chat.id, "Send User ID for credits:")

        if section == "credits" and len(parts) >= 4 and parts[2] in ("add", "remove"):
            action = parts[2]
            user_id = int(parts[3])
            db.ensure_user(user_id, None)
            admin_steps[uid] = {"action": f"credits_{action}_amount", "target": user_id}
            return bot.send_message(callback.message.chat.id, f"Send amount to {action.upper()} for {user_id}:")

        if section == "validity" and len(parts) == 2:
            admin_steps[uid] = {"action": "validity_pick_user"}
            return bot.send_message(callback.message.chat.id, "Send User ID for validity:")

        if section == "validity" and len(parts) >= 4 and parts[2] in ("set", "remove"):
            user_id = int(parts[3])
            db.ensure_user(user_id, None)

            if parts[2] == "remove":
                db.remove_validity(user_id)
                return bot.send_message(callback.message.chat.id, f"✅ Validity removed for {user_id}")

            admin_steps[uid] = {"action": "validity_days", "target": user_id}
            return bot.send_message(callback.message.chat.id, f"Send validity days for {user_id}:")

        if section == "list_users":
            users = db.list_users()
            text = "\n".join(
                [f"{u['id']} @{u.get('username') or 'unknown'} | credits={u.get('credits') or 0}" for u in users]
            )
            return bot.send_message(callback.message.chat.id, text or "No users")

        if section == "list_premium":
            users = db.list_premium_users()
            lines = []
            for u in users:
                lines.append(
                    f"👤 User: {u['id']}\n"
                    f"💳 Credits: {u.get('credits') or 0}\n"
                    f"✅ Start: {pretty_date(u.get('validity_start_at'))}\n"
                    f"⏳ End: {pretty_date(u.get('validity_expire_at'))}\n"
                    f"----------------------"
                )
            return bot.send_message(callback.message.chat.id, "\n".join(lines) or "No premium users")

        if section == "broadcast":
            admin_steps[uid] = {"action": "broadcast"}
            return bot.send_message(callback.message.chat.id, "Send broadcast message:")

        if section == "default_voice":
            models = _get_models_from_db(db)
            default_id = _get_default_voice_id(db, models)
            text = ["🎙 <b>Set Default Voice ID</b>", f"Current default: <code>{default_id}</code>", "", "Send a voice ID from your current voice list."]
            admin_steps[uid] = {"action": "set_default_voice"}
            return bot.send_message(callback.message.chat.id, "\n".join(text))

        if section == "voices" and len(parts) == 2:
            models = _get_models_from_db(db)
            return bot.send_message(
                callback.message.chat.id,
                _voice_summary_text(db, models),
                reply_markup=build_voices_keyboard(models),
            )

        if section == "voices" and len(parts) >= 4 and parts[2] == "edit":
            idx = int(parts[3])
            models = _get_models_from_db(db)
            if idx < 0 or idx >= len(models):
                return bot.send_message(callback.message.chat.id, "❌ Invalid voice")

            v = models[idx]
            admin_steps[uid] = {"action": "voice_edit_apply", "index": idx}
            return bot.send_message(
                callback.message.chat.id,
                "\n".join([
                    f"🎙 Voice Name: {v.get('name')}",
                    f"Current ID: <code>{v.get('id')}</code>",
                    "",
                    "Send only new ID:",
                    "<code>new_voice_id</code>",
                    "",
                    "Or send both ID and name:",
                    "<code>new_voice_id | new_voice_name</code>",
                ])
            )

        if section == "voices" and len(parts) >= 3 and parts[2] == "add":
            admin_steps[uid] = {"action": "voice_add"}
            return bot.send_message(
                callback.message.chat.id,
                "Send new voice like this:\n<code>voice_id | voice_name</code>"
            )

        if section == "voices" and len(parts) >= 3 and parts[2] == "reset":
            _set_models_to_db(db, DEFAULT_MODELS)
            db.set_setting("default_voice_id", DEFAULT_MODELS[0]["id"])
            return bot.send_message(callback.message.chat.id, "✅ Voices reset done!")

        if section == "download":
            try:
                with open(DB_PATH, "rb") as f:
                    return bot.send_document(callback.message.chat.id, f)
            except Exception:
                return bot.send_message(callback.message.chat.id, "DB not found!")

    @bot.message_handler(func=lambda m: m.from_user.id in admin_steps)
    def step_handler(msg):
        uid = msg.from_user.id
        step = admin_steps.pop(uid, None)
        if not step:
            return

        action = step.get("action")

        try:
            if action == "credits_pick_user":
                user_id = parse_int(msg.text)
                db.ensure_user(user_id, None)
                return bot.send_message(
                    msg.chat.id,
                    f"User {user_id}\nChoose credits action:",
                    reply_markup=build_credit_action_keyboard(user_id),
                )

            if action == "credits_add_amount":
                amount = parse_int(msg.text)
                target = int(step.get("target"))
                db.ensure_user(target, None)
                db.add_credits(target, amount)
                return bot.send_message(msg.chat.id, f"✅ Added {amount} credits to {target}")

            if action == "credits_remove_amount":
                amount = parse_int(msg.text)
                target = int(step.get("target"))
                db.ensure_user(target, None)
                db.remove_credits(target, amount)
                return bot.send_message(msg.chat.id, f"✅ Removed {amount} credits from {target}")

            if action == "validity_pick_user":
                user_id = parse_int(msg.text)
                db.ensure_user(user_id, None)
                return bot.send_message(
                    msg.chat.id,
                    f"User {user_id}\nChoose validity action:",
                    reply_markup=build_validity_action_keyboard(user_id),
                )

            if action == "validity_days":
                days = parse_int(msg.text)
                target = int(step.get("target"))
                db.ensure_user(target, None)
                db.set_validity(target, days)
                return bot.send_message(msg.chat.id, f"✅ Validity set: {days} days for {target}")

            if action == "set_default_voice":
                voice_id = (msg.text or "").strip()
                if len(voice_id) < 10:
                    return bot.send_message(msg.chat.id, "❌ Invalid Voice ID")

                models = _get_models_from_db(db)
                valid_ids = {(m.get("id") or "").strip() for m in models}
                if voice_id not in valid_ids:
                    return bot.send_message(msg.chat.id, "❌ Voice ID not found in current voice list. Add it first, then set default.")

                db.set_setting("default_voice_id", voice_id)
                return bot.send_message(msg.chat.id, f"✅ Default voice updated:\n<code>{voice_id}</code>")

            if action == "voice_edit_apply":
                raw = (msg.text or "").strip()
                if not raw:
                    return bot.send_message(msg.chat.id, "❌ Please send a voice ID")

                if "|" in raw:
                    new_id, new_name = [x.strip() for x in raw.split("|", 1)]
                else:
                    new_id, new_name = raw, None

                if len(new_id) < 10:
                    return bot.send_message(msg.chat.id, "❌ Invalid Voice ID")

                idx = int(step.get("index"))
                models = _get_models_from_db(db)
                if idx < 0 or idx >= len(models):
                    return bot.send_message(msg.chat.id, "❌ Invalid voice index")

                old_id = (models[idx].get("id") or "").strip()
                for i, item in enumerate(models):
                    item_id = (item.get("id") or "").strip()
                    if i != idx and item_id == new_id:
                        return bot.send_message(msg.chat.id, "❌ This voice ID already exists in the list")

                models[idx]["id"] = new_id
                if new_name:
                    models[idx]["name"] = new_name
                _set_models_to_db(db, models)

                current_default = (db.get_setting("default_voice_id", "") or "").strip()
                if current_default == old_id:
                    db.set_setting("default_voice_id", new_id)

                return bot.send_message(
                    msg.chat.id,
                    f"✅ Voice updated:\nName: {models[idx].get('name')}\nID: <code>{new_id}</code>"
                )

            if action == "voice_add":
                raw = (msg.text or "").strip()
                if "|" not in raw:
                    return bot.send_message(msg.chat.id, "❌ Use: <voice_id> | <voice_name>")
                vid, vname = [x.strip() for x in raw.split("|", 1)]
                if len(vid) < 10:
                    return bot.send_message(msg.chat.id, "❌ Invalid voice id")

                models = _get_models_from_db(db)
                if vid in {(m.get('id') or '').strip() for m in models}:
                    return bot.send_message(msg.chat.id, "❌ This voice ID already exists")

                models.append({"id": vid, "name": vname or vid})
                _set_models_to_db(db, models)

                if not (db.get_setting("default_voice_id", "") or "").strip():
                    db.set_setting("default_voice_id", vid)

                return bot.send_message(
                    msg.chat.id,
                    f"✅ Voice added successfully!\nName: {vname or vid}\nID: <code>{vid}</code>"
                )

            if action == "broadcast":
                import time

                users = db.list_users(limit=100000)
                sent = 0
                failed = 0
                for u in users:
                    uid2 = u.get("id")
                    if not uid2:
                        continue
                    try:
                        bot.send_message(uid2, msg.text)
                        sent += 1
                        time.sleep(0.05)
                    except Exception:
                        failed += 1
                        time.sleep(0.2)
                return bot.send_message(msg.chat.id, f"📣 Broadcast finished.\n✅ Sent: {sent}\n❌ Failed: {failed}")

        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Error: {e}")
