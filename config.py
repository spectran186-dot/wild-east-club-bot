from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    owner_id: int
    database_name: str


config = Config(
    bot_token=os.getenv("BOT_TOKEN", ""),
    owner_id=int(os.getenv("OWNER_ID", "0")),
    database_name=os.getenv("DATABASE_NAME", "data/bot.db"),
)