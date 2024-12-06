from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY") or ""
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID") or "0"
TELEGRAM_API_ID = int(TELEGRAM_API_ID)
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH") or ""
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SCRAPYBARA_API_KEY = os.getenv("SCRAPYBARA_API_KEY")
