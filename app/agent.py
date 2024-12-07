from telethon import TelegramClient, events
from scrapybara import Scrapybara
from scrapybara.models.instance import Instance
from anthropic import Anthropic
from anthropic.types.beta import BetaToolResultBlockParam, BetaMessageParam
from scrapybara.anthropic import BashTool, ComputerTool, EditTool, ToolResult
from utils import SYSTEM_PROMPT, ToolCollection, make_tool_result
from typing import Callable, Optional, Awaitable


async def run_agent(
    prompt: str,
    update_message_callback,
    instance: Instance,
    anthropic_client: Anthropic,
    should_stop: Optional[Callable[[], Awaitable[bool]]] = None
):
    try:
        # Initialize tools
        tools = ToolCollection(
            ComputerTool(instance), BashTool(instance), EditTool(instance)
        )

        messages = []
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        })

        while True:
            # Check if we should stop before each iteration
            if should_stop and await should_stop():
                await update_message_callback("Agent execution stopped by user.")
                break

            response = anthropic_client.beta.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=messages,
                system=[{"type": "text", "text": SYSTEM_PROMPT}],
                tools=tools.to_params(),
                betas=["computer-use-2024-10-22"]
            )

            tool_results = []
            for content in response.content:
                if content.type == "text":
                    await update_message_callback(f"{content.text}")
                elif content.type == "tool_use":
                    tool_result = await tools.run(
                        name=content.name,
                        tool_input=content.input  # type: ignore
                    )

                    if content.name == "bash" and not tool_result:
                        tool_result = await tools.run(
                            name="computer",
                            tool_input={"action": "screenshot"}
                        )

                    if tool_result:
                        result = make_tool_result(tool_result, content.id)
                        tool_results.append(result)

                        if tool_result.output or tool_result.error:
                            await update_message_callback(f"_{str(result)}_")

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

    except Exception as e:
        await update_message_callback(f"Error: {str(e)}")
