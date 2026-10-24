"""上下文记忆：维护对话历史，支持多轮对话与超长自动裁剪。"""
from __future__ import annotations

from .config import config
from .prompts import SYSTEM_PROMPT


class ConversationMemory:
    """以 OpenAI messages 列表形式维护对话上下文（system + user/assistant/tool）。"""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT, max_messages: int | None = None) -> None:
        self.system_prompt = system_prompt
        self.max_messages = max_messages or config.max_history_messages
        self._messages: list[dict] = [{"role": "system", "content": system_prompt}]

    def add_user(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})

    def add_assistant(self, content: str, tool_calls_api: list | None = None) -> None:
        msg: dict = {"role": "assistant", "content": content or ""}
        if tool_calls_api:
            msg["tool_calls"] = tool_calls_api
        self._messages.append(msg)

    def add_tool_result(self, tool_call_id: str, name: str, content: str) -> None:
        self._messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "name": name, "content": content}
        )

    def messages(self) -> list[dict]:
        return list(self._messages)

    def trim(self) -> None:
        """只保留 system + 最近 max_messages 条，避免上下文无限增长。"""
        if len(self._messages) <= self.max_messages + 1:
            return
        self._messages = [self._messages[0]] + self._messages[-self.max_messages:]

    def clear(self) -> None:
        self._messages = [{"role": "system", "content": self.system_prompt}]
