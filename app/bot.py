from telethon import TelegramClient, events
from env import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_API_KEY,
    ANTHROPIC_API_KEY,
    SCRAPYBARA_API_KEY,
)
from agent import run_agent
from scrapybara import Scrapybara
from scrapybara.models.instance import Instance
from anthropic import Anthropic
from typing import Dict, Optional

client = TelegramClient("bot_session", TELEGRAM_API_ID, TELEGRAM_API_HASH).start(
    bot_token=TELEGRAM_API_KEY
)
s = Scrapybara(api_key=SCRAPYBARA_API_KEY)  # type: ignore

# Global variables for instance management
instances: Dict[int, Instance] = {}  # Maps instance number to instance
preferred_instance: Optional[int] = None  # Stores the number of preferred instance
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def get_next_instance_number() -> int:
    return max(instances.keys(), default=0) + 1


async def ensure_instance_exists():
    global preferred_instance
    if not instances:
        s = Scrapybara(api_key=SCRAPYBARA_API_KEY)  # type: ignore
        instance = s.start(instance_type="small")
        instance_number = get_next_instance_number()
        instances[instance_number] = instance
        preferred_instance = instance_number
        return instance_number
    return preferred_instance


@client.on(events.NewMessage(pattern="/start"))
async def start_command(event):
    await event.reply(
        "Hello! I'm an AI assistant bot. Available commands:\n"
        "/create [small|medium|large] - Create new instance with optional size\n"
        "/list - List all instances\n"
        "/select <number> - Select preferred instance\n"
        "/delete <number> - Delete specific instance\n"
        "/deleteall - Delete all instances\n"
        "Send any other message to interact with the AI!"
    )


@client.on(events.NewMessage(pattern="/create"))
async def create_instance(event):
    try:
        # Default to medium if no size specified
        size = "small"
        parts = event.message.text.split()
        if len(parts) > 1 and parts[1].lower() in ["small", "medium", "large"]:
            size = parts[1].lower()

        instance = s.start(instance_type=size)
        instance_number = get_next_instance_number()
        instances[instance_number] = instance

        global preferred_instance
        if preferred_instance is None:
            # Set preferred to instance with lowest number if none set
            preferred_instance = min(instances.keys())

        await event.reply(f"Created new {size} instance #{instance_number}")
    except Exception as e:
        await event.reply(f"Error creating instance: {str(e)}")


@client.on(events.NewMessage(pattern="/list"))
async def list_instances(event):
    if not instances:
        await event.reply("No active instances.")
        return

    response = "Active instances:\n"
    for num, instance in instances.items():
        prefix = "→" if num == preferred_instance else " "
        response += f"{prefix} #{num}: {instance.id} {instance.get_status()} {instance.get_stream_url()}\n"
    await event.reply(response)


@client.on(events.NewMessage(pattern="/select"))
async def select_instance(event):
    try:
        number = int(event.message.text.split()[1])
        if number not in instances:
            await event.reply(f"Instance #{number} does not exist.")
            return

        global preferred_instance
        preferred_instance = number
        await event.reply(f"Selected instance #{number} as preferred.")
    except (IndexError, ValueError):
        await event.reply("Please provide a valid instance number: /select <number>")


@client.on(events.NewMessage(pattern="/delete"))
async def delete_instance(event):
    try:
        number = int(event.message.text.split()[1])
        if number not in instances:
            await event.reply(f"Instance #{number} does not exist.")
            return

        instance = instances[number]
        instance.stop()
        del instances[number]

        global preferred_instance
        if preferred_instance == number:
            preferred_instance = None

        await event.reply(f"Deleted instance #{number}")
    except (IndexError, ValueError):
        await event.reply("Please provide a valid instance number: /delete <number>")


@client.on(events.NewMessage(pattern="/deleteall"))
async def delete_all_instances(event):
    global preferred_instance
    for instance in instances.values():
        instance.stop()
    instances.clear()
    preferred_instance = None
    await event.reply("All instances have been deleted.")


@client.on(events.NewMessage())
async def handle_message(event):
    if event.message.text and not event.message.text.startswith("/"):
        instance_number = await ensure_instance_exists()
        if instance_number is None:
            await event.reply("No active instance. Creating one...")
            instance_number = await ensure_instance_exists()

        if instance_number is None:
            await event.reply("Failed to create instance")
            return

        instance = instances[instance_number]
        
        # Send initial message and store it
        progress_message = await client.send_message(event.chat_id, f"noVNC: {instance.get_stream_url()}")
        
        # Define the callback function for updating the message
        async def update_message(text: str):
            nonlocal progress_message
            await client.edit_message(event.chat_id, progress_message.id, text) # type: ignore
            
        # Pass the callback instead of client and chat_id
        await run_agent(
            event.message.text,
            update_message,
            instance,
            anthropic_client
        )


def start_bot():
    client.run_until_disconnected()


if __name__ == "__main__":
    start_bot()
