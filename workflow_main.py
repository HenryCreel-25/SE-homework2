"""代码文档工作流的命令行入口。"""

from __future__ import annotations

import argparse
import sys

from agent.llm import DeepSeekClient
from workflow import DocumentationWorkflow, WorkflowError
from workflow.demo import DemoWorkflowClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="分析代码、生成文档并审校的三 Agent Workflow")
    parser.add_argument("--file", required=True, help="待处理的单个源代码文件")
    parser.add_argument("--output-dir", default="runs", help="运行产物根目录，默认 runs")
    parser.add_argument("--demo", action="store_true", help="离线演示编排；输出为模拟内容")
    args = parser.parse_args(argv)

    if args.demo:
        factory = lambda role, source_name: DemoWorkflowClient(role, source_name)
    else:
        factory = lambda role, source_name: DeepSeekClient()

    try:
        run_dir = DocumentationWorkflow(factory).run(args.file, args.output_dir)
    except WorkflowError as exc:
        print(f"工作流失败：{exc}", file=sys.stderr)
        if exc.state_path:
            print(f"运行状态：{exc.state_path}", file=sys.stderr)
        return 1
    print(f"工作流完成：{run_dir}")
    print(f"最终文档：{run_dir / 'final.md'}")
    print(f"运行状态：{run_dir / 'state.json'}")
    if args.demo:
        print("注意：演示模式仅验证编排，文档内容为模拟输出。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
