"""LLM 调用层。

- `LLMClient`：抽象接口，统一 `chat()` 返回 `AssistantMessage`。
- `DeepSeekClient`：真实实现，走 DeepSeek 的 OpenAI 兼容接口（含函数调用）。
- `DemoClient`：无 Key 演示实现，用于离线查看 Agent 循环流程。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .config import config


class ConfigurationError(RuntimeError):
    """配置缺失（如未提供 API Key），不应重试。"""


@dataclass
class ToolCall:
    """一次工具调用的结构化描述。"""

    id: str
    name: str
    arguments: dict


@dataclass
class AssistantMessage:
    """LLM 返回的一条 assistant 消息。"""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tool(self) -> bool:
        return bool(self.tool_calls)


def tool_call_to_api(tc: ToolCall) -> dict:
    """把内部 ToolCall 转成 OpenAI 接口所需的 tool_calls 元素。"""
    return {
        "id": tc.id,
        "type": "function",
        "function": {
            "name": tc.name,
            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
        },
    }


class LLMClient:
    """LLM 客户端抽象接口。"""

    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> AssistantMessage:
        raise NotImplementedError


class DeepSeekClient(LLMClient):
    """基于 DeepSeek 官方（OpenAI 兼容）接口的客户端。"""

    def __init__(self) -> None:
        if not config.api_key:
            raise ConfigurationError(
                "未检测到 DEEPSEEK_API_KEY。请在项目根目录创建 .env 文件并填入你的 Key，"
                "或设置环境变量 DEEPSEEK_API_KEY。"
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ConfigurationError("缺少依赖 openai，请先执行：pip install -r requirements.txt") from exc
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> AssistantMessage:
        kwargs: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=_safe_json_loads(tc.function.arguments),
                    )
                )
        return AssistantMessage(content=msg.content or "", tool_calls=tool_calls)


def _safe_json_loads(raw: str) -> dict:
    try:
        return json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        return {}


class DemoClient(LLMClient):
    """离线演示客户端：模拟「先读文件、再回答」的两步循环，便于无 Key 查看流程。"""

    def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> AssistantMessage:
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break

        tool_content = None
        for m in messages:
            if m.get("role") == "tool":
                tool_content = m.get("content", "")
                break

        if tool_content is None:
            path = _guess_file_path(last_user)
            if path:
                return AssistantMessage(
                    content="演示模式：读取指定文件。",
                    tool_calls=[ToolCall(id="demo-1", name="read_file", arguments={"path": path})],
                )

        if tool_content:
            preview = tool_content[:200].rstrip()
            answer = (
                "演示模式已读取代码。以下内容仅用于检查调用流程：\n\n"
                "```\n" + preview + "\n```\n\n"
                "本模式不分析代码。实际分析需配置 DEEPSEEK_API_KEY，并在运行时去掉 --demo。"
            )
        else:
            answer = (
                "演示模式已收到请求。本模式不分析代码。"
                "实际分析需配置 DEEPSEEK_API_KEY，并在运行时去掉 --demo。"
            )
        return AssistantMessage(content=answer, tool_calls=[])


def _guess_file_path(text: str) -> Optional[str]:
    """从用户输入中粗略识别一个本地文件路径（仅演示用）。"""
    for token in text.replace("\n", " ").split():
        token = token.strip('`"\'()[]{}，。；;:,')
        p = Path(token)
        if p.is_file():
            return str(p)
    return None
