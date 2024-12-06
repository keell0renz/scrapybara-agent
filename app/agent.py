from anthropic import Anthropic
from anthropic.types.beta import BetaToolResultBlockParam, BetaMessageParam

from scrapybara import Scrapybara
from scrapybara.anthropic import BashTool, ComputerTool, EditTool, ToolResult

from typing import Optional
import os

from utils import SYSTEM_PROMPT, ToolCollection, make_tool_result

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SCRAPYBARA_API_KEY = os.getenv("SCRAPYBARA_API_KEY")

async def run_agent(user_message, telegram_client, event):

    # Initialize Scrapybara VM
    s = Scrapybara(api_key=SCRAPYBARA_API_KEY) # type: ignore
    instance = s.start(instance_type="medium")
    await telegram_client.send_message(event.chat_id, f"Started Scrapybara instance: {instance.id}")

    # Initialize tools
    tools = ToolCollection(
        ComputerTool(instance),
        BashTool(instance),
        EditTool(instance)
    )

    # Initialize chat with Claude
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    messages = []

    messages.append({
        "role": "user",
        "content": [{"type": "text", "text": user_message}],
    })

    while True:
        # Get Claude's response
        response = client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=messages,
            system=[{"type": "text", "text": SYSTEM_PROMPT}],
            tools=tools.to_params(),
            betas=["computer-use-2024-10-22"]
        )

        # Process tool usage
        tool_results = []
        for content in response.content:
            if content.type == "text":
                await telegram_client.send_message(event.chat_id, f"\nAssistant: {content.text}")
            elif content.type == "tool_use":
                await telegram_client.send_message(event.chat_id, f"\nTool Use: {content.name}")
                result = await tools.run(
                    name=content.name,
                    tool_input=content.input # type: ignore
                )
                
                if content.name == "bash" and not result:
                    result = await tools.run(
                        name="computer",
                        tool_input={"action": "screenshot"}
                    )
                
                if result:
                    tool_result = make_tool_result(result, content.id)
                    tool_results.append(tool_result)
                    
                    if result.output:
                        await telegram_client.send_message(event.chat_id, f"Tool Output: {result.output}")
                    if result.error:
                        await telegram_client.send_message(event.chat_id, f"Tool Error: {result.error}")

        # Add assistant's response and tool results to messages
        messages.append({
            "role": "assistant",
            "content": [c.model_dump() for c in response.content]
        })

        if tool_results:
            messages.append({
                "role": "user",
                "content": tool_results
            })
        else:
            break

    instance.stop()