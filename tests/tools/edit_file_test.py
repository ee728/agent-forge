import os
import tempfile

from tests.check import TestResult
from tools.edit_file import EditFileTool
from tools.base import ToolExecutionResult


def _assert(t, condition, name, detail=""):
	t.check(condition, name, detail)


def suite():
	tool = EditFileTool()
	t = TestResult()
	tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
	tmp.close()

	def r(args):
		return tool.execute({**args, "file_path": tmp.name})

	# ---- write ----
	res = r({"action": "write", "content": "line1\nline2\nline3\n"})
	t.check(res.status == "success", "write succeeds")
	t.check("Written" in res.result, "write result mentions bytes")
	t.check(os.path.isfile(tmp.name), "write created file")

	# ---- read ----
	res = r({"action": "read"})
	t.check(res.status == "success", "read succeeds")
	t.check("line2" in res.result, "read returns content")

	# ---- read with range ----
	res = r({"action": "read", "line_start": 2, "line_end": 2})
	t.check(res.status == "success", "read range succeeds")
	t.check("line2" in res.result, "read returns line 2")
	t.check("line1" not in res.result, "read range excludes line 1")

	# ---- edit ----
	res = r({"action": "edit", "line_start": 2, "line_end": 2,
			"content": "REPLACED\n"})
	t.check(res.status == "success", "edit succeeds")
	t.check("Replaced lines 2-2" in res.result, "edit result mentions range")

	res = r({"action": "read"})
	t.check("REPLACED" in res.result, "edit content verified")
	t.check("line2" not in res.result, "edit removed original line")

	# ---- error: missing file ----
	res = tool.execute({"action": "read", "file_path": "/tmp/_nonexistent_test_file_xyz"})
	t.check(res.status == "error", "read nonexistent returns error")

	res = tool.execute({"action": "edit", "file_path": "/tmp/_nonexistent_test_file_xyz",
			"line_start": 1, "line_end": 1, "content": "x"})
	t.check(res.status == "error", "edit nonexistent returns error")

	# ---- error: missing required params ----
	res = tool.execute({"action": "write", "file_path": tmp.name})
	t.check(res.status == "error", "write without content returns error")

	res = tool.execute({"action": "edit", "file_path": tmp.name,
			"line_start": 1, "content": "x"})
	t.check(res.status == "error", "edit without line_end returns error")

	# ---- error: unknown action ----
	res = tool.execute({"action": "bad_action", "file_path": tmp.name})
	t.check(res.status == "error", "unknown action returns error")

	# ---- error: missing file_path ----
	res = tool.execute({"action": "read"})
	t.check(res.status == "error", "missing file_path returns error")

	# ---- error: empty args ----
	res = tool.execute({})
	t.check(res.status == "error", "empty args returns error")

	os.unlink(tmp.name)
	return t.summary("tools.edit_file")
