from telethon import TelegramClient, events
from env import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_API_KEY
from agent import run_agent


client = TelegramClient("bot_session", TELEGRAM_API_ID, TELEGRAM_API_HASH).start(
    bot_token=TELEGRAM_API_KEY
)


@client.on(events.NewMessage(pattern="/start"))
async def start_command(event):
    await event.reply(
        "Hello! I'm an AI assistant bot. Send me any message and I'll help you!"
    )


@client.on(events.NewMessage())
async def handle_message(event):
    if event.message.text and not event.message.text.startswith("/start"):
        await run_agent(event.message.text, client, event)


def start_bot():
    client.run_until_disconnected()


if __name__ == "__main__":
    start_bot()
