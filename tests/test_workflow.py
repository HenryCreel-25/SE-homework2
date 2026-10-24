import json
import tempfile
import unittest
from pathlib import Path

from agent.llm import AssistantMessage, ConfigurationError, LLMClient
from workflow import DocumentationWorkflow, WorkflowError


class ScriptedClient(LLMClient):
    def __init__(self, role, replies, received):
        self.role = role
        self.replies = replies
        self.received = received

    def chat(self, messages, tools=None):
        self.received.setdefault(self.role, []).append(messages[-1]["content"])
        reply = self.replies[self.role].pop(0)
        if isinstance(reply, Exception):
            raise reply
        return AssistantMessage(content=reply)


class TestDocumentationWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "sample.py"
        self.source.write_text("def greet(name):\n    return f'Hi {name}'\n", encoding="utf-8")
        self.received = {}

    def workflow(self, replies):
        def factory(role, source_name):
            self.assertEqual(source_name, "sample.py")
            return ScriptedClient(role, replies, self.received)
        return DocumentationWorkflow(factory)

    def test_three_agents_handoff_and_outputs(self):
        replies = {
            "analysis": ["分析：greet 返回问候语"],
            "documentation": ["# 草稿\n\n用法说明"],
            "review": [json.dumps({"issues": ["补充参数说明"], "final_document": "# 终稿\n\n参数 name"})],
        }
        run_dir = self.workflow(replies).run(self.source, self.root / "runs")
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "completed")
        self.assertEqual([state["steps"][key]["status"] for key in ("analysis", "documentation", "review")], ["completed"] * 3)
        self.assertIn("分析：greet", self.received["documentation"][0])
        self.assertIn("# 草稿", self.received["review"][0])
        self.assertIn("def greet", self.received["review"][0])
        self.assertIn("参数 name", (run_dir / "final.md").read_text(encoding="utf-8"))

    def test_failure_stops_flow_and_records_node(self):
        replies = {
            "analysis": ["分析完成"],
            "documentation": [ConfigurationError("测试用配置错误")],
            "review": ["不应调用"],
        }
        with self.assertRaises(WorkflowError) as caught:
            self.workflow(replies).run(self.source, self.root / "runs")
        state = json.loads(caught.exception.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["current_node"], "documentation")
        self.assertEqual(state["steps"]["documentation"]["status"], "failed")
        self.assertEqual(state["steps"]["review"]["status"], "pending")

    def test_review_format_gets_one_repair_attempt(self):
        replies = {
            "analysis": ["分析"],
            "documentation": ["# 草稿"],
            "review": ["格式错误", '{"issues": [], "final_document": "# 终稿"}'],
        }
        run_dir = self.workflow(replies).run(self.source, self.root / "runs")
        self.assertEqual(len(self.received["review"]), 2)
        self.assertEqual((run_dir / "final.md").read_text(encoding="utf-8"), "# 终稿\n")


if __name__ == "__main__":
    unittest.main()
