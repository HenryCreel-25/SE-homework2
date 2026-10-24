"""命令行入口：交互式代码解释 Agent。

用法：
    python main.py                 # 交互式对话（需要 DEEPSEEK_API_KEY）
    python main.py --demo          # 无 Key 演示模式，查看 Agent 循环流程
    python main.py --once "问题"   # 单次问答后退出
"""
from __future__ import annotations

import argparse
import sys

# 当输出被重定向/管道（非交互终端）时，强制使用 UTF-8，避免中文乱码；
# 交互终端保持默认（Windows 控制台走 Unicode API，中文显示正常）。
if not sys.stdout.isatty():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 兼容不支持 reconfigure 的环境
        pass

from agent.agent import CodeExplanationAgent
from agent.llm import DeepSeekClient, DemoClient
from agent.memory import ConversationMemory

BANNER = """
==========================================================
  代码解释 Agent (Code Explanation Agent)
  输入代码、文件路径或问题，Agent 会解释代码逻辑 / 生成注释
  命令：/help 帮助 | /clear 清空对话 | /exit 退出
==========================================================
"""


def build_agent(use_demo: bool) -> CodeExplanationAgent:
    llm = DemoClient() if use_demo else DeepSeekClient()
    return CodeExplanationAgent(llm=llm, memory=ConversationMemory())


def repl(agent: CodeExplanationAgent) -> None:
    print(BANNER)
    while True:
        try:
            raw = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not raw:
            continue
        if raw in ("/exit", "/quit", "退出"):
            print("再见！")
            break
        if raw in ("/help", "帮助"):
            print("直接输入代码、文件路径或问题即可。可用命令：/clear 清空对话 | /exit 退出。")
            continue
        if raw in ("/clear", "清空"):
            agent.memory.clear()
            print("已清空对话上下文。")
            continue

        print("\nAgent 思考中…")
        try:
            answer = agent.run(raw)
        except Exception as exc:  # noqa: BLE001 - 打印给用户，保持 REPL 不退出
            print(f"\n[错误] {exc}")
            continue
        print(f"\nAgent > {answer}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="代码解释 Agent（基于 DeepSeek）")
    parser.add_argument("--demo", action="store_true", help="使用内置演示客户端（无需 API Key，用于查看流程）")
    parser.add_argument("--once", metavar="TEXT", help="单次问答后退出（方便脚本调用）")
    args = parser.parse_args(argv)

    agent = build_agent(use_demo=args.demo)

    if args.once:
        print(agent.run(args.once))
        return 0

    repl(agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
