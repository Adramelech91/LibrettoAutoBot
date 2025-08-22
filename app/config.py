
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    db_path: str = os.getenv("DB_PATH", "./data/bot.db")
    tz: str = os.getenv("TZ", "Europe/Rome")

config = Config()
if not config.bot_token:
    raise RuntimeError("BOT_TOKEN mancante. Impostalo in .env")
