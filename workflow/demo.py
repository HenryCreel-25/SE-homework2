"""无需 API Key 的工作流演示客户端；输出明确标记为模拟。"""

from __future__ import annotations

import json

from agent.llm import AssistantMessage, LLMClient


class DemoWorkflowClient(LLMClient):
    def __init__(self, role: str, source_name: str) -> None:
        self.role = role
        self.source_name = source_name

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> AssistantMessage:
        latest = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        if self.role == "analysis":
            content = (
                f"## 文件用途\n\n[演示模式] 已接收 {self.source_name} 的代码。"
                "此处模拟代码分析；真实分析需要配置 API Key。\n\n"
                "## 公开接口\n\n[演示模式] 未做真实判断。\n\n"
                "## 执行流程\n\n[演示模式] 未做真实判断。\n\n"
                "## 边界情况与风险\n\n[演示模式] 未做真实判断。"
            )
        elif self.role == "documentation":
            analysis = _between(latest, "<analysis>", "</analysis>")
            content = (
                f"# {self.source_name} 使用文档\n\n"
                "> 演示模式模拟生成，以下内容不是对源代码的真实分析。\n\n"
                "## 分析记录\n\n" + analysis + "\n"
            )
        elif self.role == "review":
            draft = _between(latest, "<draft>", "</draft>")
            content = json.dumps(
                {"issues": ["演示模式未进行真实审校"], "final_document": draft},
                ensure_ascii=False,
            )
        else:
            raise ValueError(f"未知演示节点：{self.role}")
        return AssistantMessage(content=content)


def _between(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[-1].split(end, 1)[0].strip()
