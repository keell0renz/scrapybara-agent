from telethon import TelegramClient, events
from dotenv import load_dotenv

from .agent import run_agent
import os

load_dotenv()

TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
if TELEGRAM_API_KEY is None:
    raise ValueError("TELEGRAM_API_KEY environment variable is not set")

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
if TELEGRAM_API_ID is None:
    raise ValueError("TELEGRAM_API_ID environment variable is not set")
TELEGRAM_API_ID = int(TELEGRAM_API_ID)

TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
if TELEGRAM_API_HASH is None:
    raise ValueError("TELEGRAM_API_HASH environment variable is not set")

client = TelegramClient('bot_session', TELEGRAM_API_ID, TELEGRAM_API_HASH).start(bot_token=TELEGRAM_API_KEY)

@client.on(events.NewMessage())
async def handle_message(event):
    if event.message.text:
        async def send_message(text: str):
            await client.send_message(event.chat_id, text)
            
        await run_agent(event.message.text, send_message)

def start_bot():
    client.run_until_disconnected()
    
if __name__ == "__main__":
    start_bot()