import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent.agent import CodeExplanationAgent
from agent.llm import AssistantMessage, ToolCall
from agent.memory import ConversationMemory


class FakeLLM:
    """按预设序列返回响应，用于测试 Agent 循环而不调用真实 API。"""

    def __init__(self, sequence):
        self.sequence = sequence
        self.calls = 0

    def chat(self, messages, tools=None):
        step = self.sequence[self.calls % len(self.sequence)]
        self.calls += 1
        return step


class TestAgent(unittest.TestCase):
    def test_tool_then_answer(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "sample.py"
        path.write_text("print('hi')\n", encoding="utf-8")

        fake = FakeLLM([
            AssistantMessage(
                content="",
                tool_calls=[ToolCall(id="c1", name="read_file", arguments={"path": str(path)})],
            ),
            AssistantMessage(content="解释完成", tool_calls=[]),
        ])
        agent = CodeExplanationAgent(llm=fake, memory=ConversationMemory())
        out = agent.run("解释 sample.py")
        self.assertEqual(out, "解释完成")
        roles = [m["role"] for m in agent.memory.messages()]
        self.assertIn("tool", roles)
        self.assertEqual(fake.calls, 2)

    def test_tool_failure_still_answers(self):
        fake = FakeLLM([
            AssistantMessage(
                content="",
                tool_calls=[ToolCall(id="c1", name="read_file", arguments={"path": "/no/such.py"})],
            ),
            AssistantMessage(content="文件打不开，建议检查路径", tool_calls=[]),
        ])
        agent = CodeExplanationAgent(llm=fake, memory=ConversationMemory())
        out = agent.run("解释")
        self.assertEqual(out, "文件打不开，建议检查路径")

    def test_retry_on_transient_error(self):
        class Flaky(FakeLLM):
            def chat(self, messages, tools=None):
                self.calls += 1
                if self.calls == 1:
                    raise TimeoutError("boom")
                return AssistantMessage(content="ok", tool_calls=[])

        agent = CodeExplanationAgent(llm=Flaky([]), memory=ConversationMemory())
        with mock.patch("time.sleep", return_value=None):
            out = agent.run("hi")
        self.assertEqual(out, "ok")
        self.assertEqual(agent.memory.messages()[-1]["content"], "ok")


if __name__ == "__main__":
    unittest.main()
