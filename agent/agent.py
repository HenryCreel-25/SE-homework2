"""Agent 核心循环：输入 → 推理 → 工具调用 → 输出。"""
from __future__ import annotations

import time

from .config import config
from .llm import AssistantMessage, ConfigurationError, LLMClient, tool_call_to_api
from .memory import ConversationMemory
from .tools import TOOL_SCHEMAS, execute_tool


class CodeExplanationAgent:
    """带工具调用、上下文记忆与重试机制的解释型 Agent。"""

    def __init__(
        self, llm: LLMClient, memory: ConversationMemory | None = None, *, strict: bool = False
    ) -> None:
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.max_iterations = config.max_iterations
        self.strict = strict

    def run(self, user_input: str) -> str:
        """处理一次用户输入，返回最终回答文本。"""
        self.memory.add_user(user_input)

        for _ in range(self.max_iterations):
            self.memory.trim()
            response = self._chat_with_retry(self.memory.messages())

            # 模型直接给出回答：结束循环
            if not response.wants_tool:
                final = (response.content or "").strip()
                if self.strict and not final:
                    raise RuntimeError("模型未返回内容")
                self.memory.add_assistant(content=final)
                return final or "（模型未返回内容）"

            # 模型请求工具：先记录 assistant 消息（含 tool_calls），再逐个执行工具
            tool_calls_api = [tool_call_to_api(tc) for tc in response.tool_calls]
            self.memory.add_assistant(content=response.content, tool_calls_api=tool_calls_api)

            for tc, tc_api in zip(response.tool_calls, tool_calls_api):
                result = execute_tool(tc.name, tc.arguments)
                content = result["result"] if result.get("ok") else f"[工具执行失败] {result.get('error')}"
                self.memory.add_tool_result(tc_api["id"], tc.name, content)

        if self.strict:
            raise RuntimeError("达到最大推理步数，仍未得到最终回答")
        return "达到最大推理步数，仍未得到最终回答。请简化问题后重试。"

    def _chat_with_retry(self, messages: list[dict], retries: int = 3) -> AssistantMessage:
        """带重试的 LLM 调用：处理网络、限流等瞬时错误；配置错误直接抛出。"""
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return self.llm.chat(messages, TOOL_SCHEMAS)
            except ConfigurationError:
                raise
            except Exception as exc:  # noqa: BLE001 - 网络/限流等瞬时错误统一兜底重试
                last_exc = exc
                if attempt < retries:
                    time.sleep(1.5 * attempt)  # 线性退避
        raise RuntimeError(f"LLM 调用失败（已重试 {retries} 次）：{last_exc}")
