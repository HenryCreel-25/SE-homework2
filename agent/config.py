"""全局配置：集中管理连接参数与运行选项，支持 .env 与环境变量覆盖。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# 尽早加载 .env（若存在），使配置项可从文件读取；没有 python-dotenv 时退化为读真实环境变量
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


@dataclass
class Config:
    # LLM 连接
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    temperature: float = 0.7

    # Agent 循环
    max_iterations: int = 8
    max_history_messages: int = 20

    # 工具限制
    max_file_bytes: int = 200_000  # 单文件读取上限（约 200KB）
    allowed_extensions: tuple = (
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h", ".cpp", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".php", ".sql", ".sh", ".bat", ".ps1",
        ".html", ".css", ".json", ".yaml", ".yml", ".md", ".txt", ".toml", ".ini", ".xml",
    )


config = Config()
