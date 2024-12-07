from telethon import TelegramClient, events
from scrapybara import Scrapybara
from scrapybara.models.instance import Instance
from anthropic import Anthropic
from anthropic.types.beta import BetaToolResultBlockParam, BetaMessageParam
from scrapybara.anthropic import BashTool, ComputerTool, EditTool, ToolResult
from utils import SYSTEM_PROMPT, ToolCollection, make_tool_result
from typing import Callable


async def run_agent(
    message: str,
    update_message: Callable,
    instance: Instance,
    anthropic_client: Anthropic,
) -> None:
    # Initialize tools
    tools = ToolCollection(
        ComputerTool(instance), BashTool(instance), EditTool(instance)
    )

    messages = []
    messages.append(
        {
            "role": "user",
            "content": [{"type": "text", "text": message}],
        }
    )

    full_response = ""  # Track the complete response

    while True:
        response = anthropic_client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=messages,
            system=[{"type": "text", "text": SYSTEM_PROMPT}],
            tools=tools.to_params(),
            betas=["computer-use-2024-10-22"],
        )

        tool_results = []
        for content in response.content:
            if content.type == "text":
                full_response += f"\n{content.text}"
                await update_message(full_response)
            elif content.type == "tool_use":
                tool_result = await tools.run(
                    name=content.name, tool_input=content.input  # type: ignore
                )

                if content.name == "bash" and not tool_result:
                    tool_result = await tools.run(
                        name="computer", tool_input={"action": "screenshot"}
                    )

                if tool_result:
                    result = make_tool_result(tool_result, content.id)
                    tool_results.append(result)

                    if tool_result.output or tool_result.error:
                        full_response += f"\n_{str(result)}_"
                        await update_message(full_response)

        messages.append(
            {"role": "assistant", "content": [c.model_dump() for c in response.content]}
        )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            break
