import json

from groq import Groq

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
                "WARNING: GROQ_API_KEY environment "
                "variable not found."
            )

        self.client = Groq(
            api_key=GROQ_API_KEY
        )

        self.conversation = [
            {
                "role": "system",
                "content": get_system_prompt()
            }
        ]

    def ask(self, user_text):

        self.state.set_status("thinking")

        self.conversation.append(
            {
                "role": "user",
                "content": user_text
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

            if (
                "tool_use_failed" in error_text
                or "not in request.tools" in error_text
            ):

                self.state.log(
                    "Model tried an unsupported tool. Retrying with "
                    "a stricter reminder about available local tools."
                )

                self.conversation.append(
                    {
                        "role": "system",
                        "content": (
                            "Only use the local tools provided by the app. "
                            "Do not call web search, browser, or internet "
                            "tools. If no listed tool fits, answer directly "
                            "without inventing one."
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

                except Exception:

                    return (
                        "I couldn't complete that request without a "
                        "supported local tool."
                    )

            else:

                raise

        message = response.choices[0].message

        # =========================
        # TOOL CALL
        # =========================

        if message.tool_calls:

            self.conversation.append(message)

            for call in message.tool_calls:

                function_name = call.function.name

                arguments = json.loads(
                    call.function.arguments
                )

                result = self.tool_registry.execute(
                    function_name,
                    arguments
                )

                self.conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": str(result)
                    }
                )

            # Ask Groq for the final natural response
            follow_up = (
                self.client
                .chat
                .completions
                .create(
                    model=GROQ_MODEL,
                    messages=self.conversation,
                    temperature=0.6,
                    max_tokens=300,
                )
            )

            reply = (
                follow_up
                .choices[0]
                .message
                .content
                .strip()
            )

            self.conversation.append(
                {
                    "role": "assistant",
                    "content": reply
                }
            )

            return reply

        # =========================
        # NORMAL RESPONSE
        # =========================

        reply = message.content.strip()

        self.conversation.append(
            {
                "role": "assistant",
                "content": reply
            }
        )

        return reply