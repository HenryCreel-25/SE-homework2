"""工具层：Agent 可调用的工具，当前提供「读取文件」与「列出目录」两个工具。

工具统一返回 {"ok": bool, "result": str, "error": str}，保证无论成功失败
都能把结构化结果回传给 LLM，让 Agent 能据此继续推理。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import config

# 传给 LLM 的工具描述（OpenAI function-calling 格式）
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "读取本地源代码文件的内容。传入文件路径，可指定行号范围（从 1 开始）。"
                "适合在回答代码问题前先查看文件内容。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要读取的文件路径（绝对或相对路径）"},
                    "start_line": {"type": "integer", "description": "起始行号（从 1 开始，可选）"},
                    "end_line": {"type": "integer", "description": "结束行号（包含，可选）"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出指定目录下的文件与子目录（非递归），用于定位需要阅读的源代码文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径，默认当前目录"},
                },
                "required": [],
            },
        },
    },
]


def _resolve(path: str) -> Path:
    return Path(path).expanduser()


def read_file(path: str, start_line: int | None = None, end_line: int | None = None) -> dict:
    """读取文件内容，支持行号范围。"""
    p = _resolve(path)
    try:
        if not p.exists():
            return {"ok": False, "result": "", "error": f"文件不存在：{p}"}
        if not p.is_file():
            return {"ok": False, "result": "", "error": f"不是文件：{p}"}
        if p.suffix.lower() not in config.allowed_extensions:
            return {"ok": False, "result": "", "error": f"不支持的文件类型：{p.suffix or '(无扩展名)'}"}

        size = p.stat().st_size
        if size > config.max_file_bytes:
            return {"ok": False, "result": "", "error": f"文件过大（{size} 字节），超过上限 {config.max_file_bytes} 字节"}

        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        if start_line is None and end_line is None:
            return {"ok": True, "result": text, "error": ""}

        start = (start_line or 1) - 1
        end = end_line or len(lines)
        if start < 0 or start >= len(lines):
            return {"ok": False, "result": "", "error": f"起始行号越界：文件共 {len(lines)} 行"}
        selected = lines[start:end]
        return {"ok": True, "result": "\n".join(selected), "error": ""}
    except UnicodeError as exc:
        return {"ok": False, "result": "", "error": f"无法以 UTF-8 读取文件：{exc}"}
    except OSError as exc:
        return {"ok": False, "result": "", "error": f"读取失败：{exc}"}


def list_files(path: str = ".") -> dict:
    """列出指定目录下的文件与子目录（非递归）。"""
    p = _resolve(path)
    try:
        if not p.exists() or not p.is_dir():
            return {"ok": False, "result": "", "error": f"目录不存在：{p}"}
        entries = sorted(
            e.name + ("/" if e.is_dir() else "")
            for e in p.iterdir()
            if not e.name.startswith(".")
        )
        return {"ok": True, "result": "\n".join(entries) or "(空目录)", "error": ""}
    except OSError as exc:
        return {"ok": False, "result": "", "error": f"列出目录失败：{exc}"}


TOOL_REGISTRY: dict[str, Any] = {
    "read_file": read_file,
    "list_files": list_files,
}


def execute_tool(name: str, arguments: dict) -> dict:
    """根据名字和参数执行工具，统一返回结果字典。"""
    if name not in TOOL_REGISTRY:
        return {"ok": False, "result": "", "error": f"未知工具：{name}"}
    try:
        return TOOL_REGISTRY[name](**arguments)
    except TypeError as exc:
        return {"ok": False, "result": "", "error": f"工具参数错误：{exc}"}
