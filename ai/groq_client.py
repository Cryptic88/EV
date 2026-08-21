import json
from typing import Any

from groq import Groq
from groq.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
)

from config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL,
)

from ai.prompts import get_system_prompt


class GroqClient:

    def __init__(self, state, tool_registry):
        self.state = state
        self.tool_registry = tool_registry

        if not GROQ_API_KEY:
            self.state.log(
                "WARNING: GROQ_API_KEY environment variable not found."
            )

        self.client = Groq(
            api_key=GROQ_API_KEY
        )

        self.conversation: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": get_system_prompt(),
            }
        ]

    def ask(self, user_text: str) -> str:
        self.state.set_status("thinking")

        self.conversation.append(
            {
                "role": "user",
                "content": user_text,
            }
        )

        tools = self.tool_registry.get_tools()

        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=self.conversation,
                tools=tools,
                tool_choice="auto",
                temperature=0.6,
                max_tokens=300,
            )

        except Exception as error:
            error_text = str(error)

            self.state.log(
                f"Groq request failed: {error}"
            )

            if (
                "tool_use_failed" in error_text
                or "not in request.tools" in error_text
            ):
                self.state.log(
                    "Model tried an unsupported tool. "
                    "Retrying with a stricter reminder "
                    "about available local tools."
                )

                self.conversation.append(
                    {
                        "role": "system",
                        "content": (
                            "Only use tools provided by the application. "
                            "Do not invent tools. "
                            "Available tools may include search_web "
                            "and read_webpage. "
                            "If no available tool matches the request, "
                            "answer directly."
                        ),
                    }
                )

                try:
                    response = self.client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=self.conversation,
                        tools=tools,
                        tool_choice="auto",
                        temperature=0.4,
                        max_tokens=300,
                    )

                except Exception as retry_error:
                    self.state.log(
                        f"Groq retry failed: {retry_error}"
                    )

                    return (
                        "I couldn't complete that request "
                        "with the available tools."
                    )

            else:
                return (
                    "I'm having trouble connecting to my AI service "
                    "right now."
                )

        message = response.choices[0].message

        # ============================================================
        # TOOL CALL
        # ============================================================

        if message.tool_calls:

            assistant_message: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in message.tool_calls
                ],
            }

            self.conversation.append(
                assistant_message
            )

            # Execute each requested tool.
            #
            # We execute them sequentially because this keeps
            # the tool system predictable and works well with
            # the current EV architecture.

            for call in message.tool_calls:

                function_name = call.function.name

                try:
                    arguments: dict[str, Any] = json.loads(
                        call.function.arguments
                    )

                except (
                    json.JSONDecodeError,
                    TypeError,
                ):
                    arguments = {}

                self.state.log(
                    f"Executing tool: {function_name}"
                )

                try:
                    result = self.tool_registry.execute(
                        function_name,
                        arguments,
                    )

                except Exception as error:
                    self.state.log(
                        f"Tool '{function_name}' failed: {error}"
                    )

                    result = (
                        f"Tool '{function_name}' failed: "
                        f"{error}"
                    )

                tool_message: ChatCompletionToolMessageParam = {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                }

                self.conversation.append(
                    tool_message
                )

            # ========================================================
            # FINAL AI RESPONSE AFTER TOOL EXECUTION
            # ========================================================

            try:
                follow_up = (
                    self.client
                    .chat
                    .completions
                    .create(
                        model=GROQ_MODEL,
                        messages=self.conversation,
                        tools=self.tool_registry.get_tools(),
                        tool_choice="auto",
                        temperature=0.6,
                        max_tokens=300,
                    )
                )

                follow_up_message = (
                    follow_up.choices[0].message
                )

                reply = (
                    follow_up_message.content or ""
                ).strip()

            except Exception as error:
                self.state.log(
                    f"Groq follow-up failed: {error}"
                )

                reply = ""

            if not reply:
                reply = "Done."

            self.conversation.append(
                {
                    "role": "assistant",
                    "content": reply,
                }
            )

            return reply

        # ============================================================
        # NORMAL RESPONSE
        # ============================================================

        reply = (
            message.content or ""
        ).strip()

        if not reply:
            reply = (
                "I heard you, but I'm not sure how to "
                "respond to that."
            )

        self.conversation.append(
            {
                "role": "assistant",
                "content": reply,
            }
        )

        return reply