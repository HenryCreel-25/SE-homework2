"""分析、写文档、审校三个 Agent 的顺序编排与状态记录。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

from agent.agent import CodeExplanationAgent
from agent.llm import LLMClient
from agent.memory import ConversationMemory
from agent.tools import read_file

from .prompts import ANALYST_PROMPT, REVIEWER_PROMPT, WRITER_PROMPT

MAX_SOURCE_CHARS = 20_000


class WorkflowError(RuntimeError):
    def __init__(self, message: str, state_path: Path | None = None) -> None:
        super().__init__(message)
        self.state_path = state_path


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _review_data(raw: str) -> dict:
    content = raw.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            content = "\n".join(lines[1:-1]).strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("审校 Agent 未返回有效 JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("审校结果必须是 JSON 对象")
    issues = data.get("issues")
    final = data.get("final_document")
    if not isinstance(issues, list) or not all(isinstance(item, str) for item in issues):
        raise ValueError("审校结果的 issues 必须是字符串数组")
    if not isinstance(final, str) or not final.strip():
        raise ValueError("审校结果缺少非空的 final_document")
    return {"issues": issues, "final_document": final.strip()}


class DocumentationWorkflow:
    """为一次运行创建三个独立 Agent，并持久化每次交接。"""

    def __init__(self, llm_factory: Callable[[str, str], LLMClient]) -> None:
        self.llm_factory = llm_factory

    def run(self, source_file: str | Path, output_root: str | Path = "runs") -> Path:
        source = Path(source_file).expanduser().resolve()
        read_result = read_file(str(source))
        if not read_result["ok"]:
            raise WorkflowError(read_result["error"])
        code = read_result["result"]
        if not code.strip():
            raise WorkflowError("输入文件为空")
        if len(code) > MAX_SOURCE_CHARS:
            raise WorkflowError(f"输入代码超过 {MAX_SOURCE_CHARS} 字符，请选择较小文件")

        run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
        run_dir = Path(output_root).expanduser().resolve() / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        state_path = run_dir / "state.json"
        state = {
            "run_id": run_id,
            "source_file": str(source),
            "status": "running",
            "current_node": None,
            "started_at": _now(),
            "finished_at": None,
            "steps": {
                "analysis": {"status": "pending", "input_from": ["source_file"]},
                "documentation": {"status": "pending", "input_from": ["source_file", "analysis"]},
                "review": {"status": "pending", "input_from": ["source_file", "analysis", "draft"]},
            },
            "error": None,
        }
        self._save_state(state_path, state)

        try:
            analysis = self._step(
                state, state_path, "analysis", ANALYST_PROMPT,
                f"请分析文件 {source.name}。\n<source_code>\n{code}\n</source_code>",
                run_dir / "analysis.md",
            )
            draft = self._step(
                state, state_path, "documentation", WRITER_PROMPT,
                f"文件：{source.name}\n<source_code>\n{code}\n</source_code>\n"
                f"<analysis>\n{analysis}\n</analysis>",
                run_dir / "draft.md",
            )
            raw_review = self._step(
                state, state_path, "review", REVIEWER_PROMPT,
                f"文件：{source.name}\n<source_code>\n{code}\n</source_code>\n"
                f"<analysis>\n{analysis}\n</analysis>\n<draft>\n{draft}\n</draft>",
                run_dir / "review.json",
                review=True,
            )
            review = _review_data(raw_review)
            (run_dir / "final.md").write_text(review["final_document"] + "\n", encoding="utf-8")
            state["steps"]["review"]["final_output"] = "final.md"
            state["status"] = "completed"
            state["current_node"] = None
            state["finished_at"] = _now()
            self._save_state(state_path, state)
            return run_dir
        except Exception as exc:
            state["status"] = "failed"
            state["finished_at"] = _now()
            state["error"] = str(exc)
            current = state["current_node"]
            if current:
                state["steps"][current]["status"] = "failed"
                state["steps"][current]["finished_at"] = _now()
                state["steps"][current]["error"] = str(exc)
            self._save_state(state_path, state)
            raise WorkflowError(str(exc), state_path) from exc

    def _step(
        self, state: dict, state_path: Path, role: str, prompt: str,
        user_input: str, output_path: Path, *, review: bool = False,
    ) -> str:
        step = state["steps"][role]
        state["current_node"] = role
        step["status"] = "running"
        step["started_at"] = _now()
        self._save_state(state_path, state)

        agent = CodeExplanationAgent(
            llm=self.llm_factory(role, Path(state["source_file"]).name),
            memory=ConversationMemory(system_prompt=prompt),
            strict=True,
        )
        result = agent.run(user_input).strip()
        if review:
            try:
                parsed = _review_data(result)
            except ValueError:
                result = agent.run("上一次输出格式无效。请只重新输出符合要求的 JSON 对象。")
                parsed = _review_data(result)
            output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            output_path.write_text(result + "\n", encoding="utf-8")
        step["status"] = "completed"
        step["finished_at"] = _now()
        step["output"] = output_path.name
        self._save_state(state_path, state)
        return result

    @staticmethod
    def _save_state(path: Path, state: dict) -> None:
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
