import os
from dotenv import load_dotenv

load_dotenv()

# -------------------------
# FIXED ADMIN IDS (Do not overwrite)
# -------------------------
ADMIN_IDS = [1800295558]   # <-- আপনার Telegram numeric ID

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN", "")
FISH_AUDIO_API_KEY = os.getenv("VOICE_API_KEY", "")
FISH_AUDIO_BASE_URL = os.getenv("FISH_AUDIO_BASE_URL", "https://api.fish.audio")
FISH_AUDIO_BACKEND = os.getenv("FISH_AUDIO_BACKEND", "s1")
FISH_AUDIO_MP3_BITRATE = int(os.getenv("FISH_AUDIO_MP3_BITRATE", "128"))

ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "x")
WEBSITE_URL   = os.getenv("WEBSITE_URL", "x")

# REMOVE OLD ADMIN_IDS OVERRIDE ❌
# ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

DB_PATH = os.getenv("DB_PATH", "file.db")
VOICES_DIR = os.getenv("VOICES_DIR", "voices")

COST_PER_VOICE = 1
REQUIRE_VALIDITY_FOR_TTS = False
MAX_TTS_CHARS = int(os.getenv("MAX_TTS_CHARS", "200"))

DEFAULT_MODELS = [
    {"id": "a5e5bbe15fb6465fb113c1bab4de8b2e", "name": "Marie"},
    {"id": "89caeb03934840e791f7d13e9c03b6ef", "name": "Daisy"},
    {"id": "e3fbe8fdb0ea40d8a15d527ab854b8af", "name": "Ayesha"},
    {"id": "b8daf8f8981a484abb8cc9520641b5dc", "name": "Anna"},
    {"id": "29913697e157485c941c737314c27819", "name": "Ruby"},
    {"id": "d75c78da679a4d8480e4bcfb6c60bdc6", "name": "Nora"},
    {"id": "d39b35734b49454784d2dbcc17cd45b9", "name": "Denica"},
    {"id": "c5e4c4c57a084a0f9b5b277d36546ef0", "name": "Even"},
    {"id": "2fe69a0850b54119ad97af8246e2f6a0", "name": "Freya"},
    {"id": "60de84651feb4ac7a0bbc23c45c089e1", "name": "Gia"},
    {"id": "8a7f5c27e2e04596b079e78a475d852b", "name": "Lacy"},
]

USE_CONFIG_MODELS_ONLY = True

PLANS = [
    {"name": "Starter", "credits": 50, "price": "$5", "validity_days": 30},
    {"name": "Pro", "credits": 200, "price": "$15", "validity_days": 30},
    {"name": "Unlimited-Day", "credits": 400, "price": "$30", "validity_days": 30},
]

USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")
PORT = int(os.getenv("PORT", "8000"))
