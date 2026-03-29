import os
import time
import threading
from datetime import datetime
from config import VOICES_DIR


def _expiry_cleanup_worker(db, bot, interval_seconds: int):
    while True:
        try:
            users = db.list_users(limit=10000)
            now = datetime.utcnow()
            for u in users:
                exp = u.get("validity_expire_at")
                if not exp:
                    continue
                try:
                    if datetime.fromisoformat(exp) <= now:
                        user_id = int(u["id"])
                        voices = db.list_user_voices(user_id)
                        for v in voices:
                            try:
                                if os.path.exists(v["file_path"]):
                                    os.remove(v["file_path"])
                            except Exception:
                                pass
                        db.delete_user_voices(user_id)
                        db.update_user_fields(user_id, {"is_premium": 0, "credits": 0, "validity_expire_at": None})
                        try:
                            bot.send_message(user_id, "Your validity expired. All voices have been removed.")
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(interval_seconds)


def start_expiry_cleanup_thread(db, bot, interval_seconds: int = 3600):
    t = threading.Thread(target=_expiry_cleanup_worker, args=(db, bot, interval_seconds), daemon=True)
    t.start()