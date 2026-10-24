import unittest

from agent.memory import ConversationMemory


class TestMemory(unittest.TestCase):
    def test_add_and_order(self):
        m = ConversationMemory(max_messages=10)
        m.add_user("hi")
        m.add_assistant("hello")
        msgs = m.messages()
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["role"], "user")
        self.assertEqual(msgs[2]["role"], "assistant")

    def test_trim_keeps_system_and_recent(self):
        m = ConversationMemory(max_messages=3)
        for i in range(10):
            m.add_user(f"u{i}")
        m.trim()
        msgs = m.messages()
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(len(msgs), 4)  # system + 最近 3 条
        self.assertEqual(msgs[-1]["content"], "u9")

    def test_clear(self):
        m = ConversationMemory()
        m.add_user("hi")
        m.clear()
        self.assertEqual(len(m.messages()), 1)


if __name__ == "__main__":
    unittest.main()
