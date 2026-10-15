"""Streaming Groq/Ollama client sharing conversation and local tool behavior."""
import json
from config import settings
from ai.prompts import get_system_prompt
from ai.streaming import SentenceBuffer


class GroqClient:
    # Keep the public class name for existing integrations.
    def __init__(self, state, tool_registry):
        self.state = state
        self.tool_registry = tool_registry
        self.before_tool = lambda: None
        self.backend = settings.LLM_BACKEND
        self.conversation = [{"role": "system", "content": get_system_prompt()}]
        if self.backend == "groq":
            from groq import Groq
            if not settings.GROQ_API_KEY:
                raise ValueError("Set GROQ_API_KEY, or use LLM_BACKEND=ollama")
            self.client = Groq(api_key=settings.GROQ_API_KEY, timeout=60, max_retries=1)
        elif self.backend != "ollama":
            raise ValueError("LLM_BACKEND must be groq or ollama")

    def _events(self):
        tools = self.tool_registry.get_tools()
        if self.backend == "groq":
            stream = self.client.chat.completions.create(model=settings.GROQ_MODEL,
                messages=[{k: v for k, v in m.items() if k != "tool_name"}
                          for m in self.conversation], tools=tools, tool_choice="auto",
                temperature=0.6, max_tokens=300, stream=True)
            try:
                for chunk in stream:
                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        yield delta.content or "", [call.model_dump(exclude_none=True)
                                                      for call in delta.tool_calls or []]
            finally:
                stream.close()
        else:
            import requests
            # Ollama accepts parsed tool arguments, unlike Groq's JSON strings.
            messages = []
            for message in self.conversation:
                copied = dict(message)
                if "tool_calls" in copied:
                    copied["tool_calls"] = [{"function": {
                        "name": call["function"]["name"],
                        "arguments": json.loads(call["function"]["arguments"]),
                    }} for call in copied["tool_calls"]]
                if copied.get("role") == "tool":
                    copied.pop("tool_call_id", None)
                messages.append(copied)
            with requests.post(settings.OLLAMA_BASE_URL.rstrip("/") + "/api/chat",
                    json={"model": settings.OLLAMA_MODEL, "messages": messages,
                          "tools": tools, "stream": True, "think": False,
                          "options": {"temperature": 0.6, "num_predict": 300}},
                    stream=True, timeout=(10, 120)) as response:
                response.raise_for_status()
                call_index = 0
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get("error"):
                        raise RuntimeError(event["error"])
                    message = event.get("message", {})
                    calls = []
                    for call in message.get("tool_calls", []):
                        calls.append({"index": call_index, "function": call["function"]})
                        call_index += 1
                    yield message.get("content", ""), calls
                    if event.get("done"):
                        break

    def ask(self, user_text):
        return " ".join(self.ask_stream(user_text))

    def ask_stream(self, user_text):
        self.state.set_status("thinking")
        if self.conversation and self.conversation[0].get('role') == 'system':
            self.conversation[0]['content'] = get_system_prompt()
        self.conversation.append({"role": "user", "content": user_text})
        for round_index in range(settings.MAX_TOOL_ROUNDS):
            text = ""
            calls = {}
            sentences = SentenceBuffer()
            events = self._events()
            try:
                for content, deltas in events:
                    if self.state.is_stopped():
                        return
                    text += content
                    for delta in deltas:
                        index = delta.get("index", 0)
                        call = calls.setdefault(index, {"id": f"ev_{round_index}_{index}",
                            "type": "function", "function": {"name": "", "arguments": ""}})
                        if delta.get("id"):
                            call["id"] = delta["id"]
                        function = delta.get("function", {})
                        call["function"]["name"] += function.get("name") or ""
                        arguments = function.get("arguments")
                        if isinstance(arguments, dict):
                            call["function"]["arguments"] = json.dumps(arguments)
                        else:
                            call["function"]["arguments"] += arguments or ""
                    yield from sentences.feed(content)
            finally:
                events.close()
            yield from sentences.finish()
            message = {"role": "assistant", "content": text}
            if calls:
                message["tool_calls"] = [calls[index] for index in sorted(calls)]
            self.conversation.append(message)
            if not calls:
                if not text.strip():
                    message["content"] = "I couldn't generate a reply. Please try again."
                    yield message["content"]
                return
            # Finish any spoken preamble before a tool asks for voice confirmation.
            self.before_tool()
            for call in message["tool_calls"]:
                name = call["function"]["name"]
                try:
                    arguments = json.loads(call["function"]["arguments"] or "{}")
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be an object")
                    if self.state.is_stopped():
                        result = "Cancelled because E.V. is stopping."
                    elif round_index == settings.MAX_TOOL_ROUNDS - 1:
                        result = "Tool round limit reached; ask the user to try again."
                    else:
                        self.state.log(f"Executing tool: {name}")
                        result = self.tool_registry.execute(name, arguments)
                except Exception as error:
                    self.state.log(f"Tool '{name}' failed: {error}")
                    result = f"Tool '{name}' failed: {error}"
                self.conversation.append({"role": "tool", "tool_call_id": call["id"],
                                          "tool_name": name, "content": str(result)})
        reply = "I've reached the tool limit for this request. Please try again."
        self.conversation.append({"role": "assistant", "content": reply})
        yield reply
