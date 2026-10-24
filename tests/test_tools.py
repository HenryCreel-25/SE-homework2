import tempfile
import unittest
from pathlib import Path

from agent.tools import execute_tool, list_files, read_file


class TestReadFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name: str, content: str) -> Path:
        p = self.dir / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_read_full(self):
        p = self._write("a.py", "print(1)\nprint(2)\n")
        r = read_file(str(p))
        self.assertTrue(r["ok"])
        self.assertIn("print(1)", r["result"])

    def test_read_line_range(self):
        p = self._write("a.py", "l1\nl2\nl3\nl4\n")
        r = read_file(str(p), start_line=2, end_line=3)
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"], "l2\nl3")

    def test_missing_file(self):
        r = read_file(str(self.dir / "nope.py"))
        self.assertFalse(r["ok"])
        self.assertIn("不存在", r["error"])

    def test_bad_extension(self):
        p = self._write("a.exe", "x")
        r = read_file(str(p))
        self.assertFalse(r["ok"])
        self.assertIn("类型", r["error"])

    def test_execute_unknown_tool(self):
        r = execute_tool("no_such_tool", {})
        self.assertFalse(r["ok"])

    def test_list_files(self):
        self._write("x.py", "1")
        self._write("y.py", "2")
        r = list_files(str(self.dir))
        self.assertTrue(r["ok"])
        self.assertIn("x.py", r["result"])
        self.assertIn("y.py", r["result"])


if __name__ == "__main__":
    unittest.main()
