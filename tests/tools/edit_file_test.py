import os
import tempfile

from tests.check import TestResult
from tools.edit_file import EditFileTool


def suite():
	tool = EditFileTool()
	t = TestResult()

	# ---- write ----
	tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
	tmp.close()

	def r(args):
		return tool.execute({**args, "file_path": tmp.name})

	res = r({"action": "write", "content": "line1\nline2\nline3\nline4\nline5\n"})
	t.check(res.status == "success", "write succeeds")
	t.check("bytes" in res.result, "write result mentions bytes")
	t.check(os.path.isfile(tmp.name), "write created file")

	# ---- read defaults to first 50 lines ----
	res = r({"action": "read"})
	t.check(res.status == "success", "read without range succeeds")
	t.check("(lines 1-5/5)" in res.result, "read shows correct range")

	# ---- read with explicit range ----
	res = r({"action": "read", "line_start": 2, "line_end": 3})
	t.check(res.status == "success", "read range succeeds")
	t.check("line2" in res.result, "read returns line 2")
	t.check("line3" in res.result, "read returns line 3")
	t.check("line1" not in res.result, "read range excludes line 1")

	# ---- search ----
	res = r({"action": "search", "pattern": "line3"})
	t.check(res.status == "success", "search succeeds")
	t.check("line3" in res.result, "search finds matching line")

	# search no match
	res = r({"action": "search", "pattern": "zzzznotfound"})
	t.check(res.status == "success", "search no-match succeeds")
	t.check("No matches" in res.result, "search reports no matches")

	# search with context
	res = r({"action": "search", "pattern": "line3", "context": 1})
	t.check(res.status == "success", "search with context succeeds")
	t.check("line2" in res.result, "search context includes adjacent line")

	# search without pattern
	res = tool.execute({"action": "search", "file_path": tmp.name})
	t.check(res.status == "error", "search without pattern returns error")

	# ---- edit ----
	res = r({"action": "edit", "line_start": 2, "line_end": 2,
			"content": "REPLACED\n"})
	t.check(res.status == "success", "edit succeeds")
	t.check("Replaced lines 2-2" in res.result, "edit result mentions range")

	res = r({"action": "read"})
	t.check("REPLACED" in res.result, "edit content verified")
	t.check("line2" not in res.result, "edit removed original line")

	# ---- error: missing file ----
	res = tool.execute({"action": "read", "file_path": "/tmp/_nonexistent_xyz"})
	t.check(res.status == "error", "read nonexistent returns error")

	res = tool.execute({"action": "search", "file_path": "/tmp/_nonexistent_xyz",
			"pattern": "foo"})
	t.check(res.status == "error", "search nonexistent returns error")

	res = tool.execute({"action": "edit", "file_path": "/tmp/_nonexistent_xyz",
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

	res = tool.execute({})
	t.check(res.status == "error", "empty args returns error")

	# ---- large write works without artificial limit ----
	big = "x" * 5000
	res = r({"action": "write", "content": big})
	t.check(res.status == "success", "write 5000 chars works (no limit)")

	# ---- search with regex ----
	r({"action": "write", "content": "abc123\ndef456\nghi789\n"})
	res = r({"action": "search", "pattern": r"\d{3}"})
	t.check(res.status == "success", "search with regex pattern succeeds")
	t.check("abc123" in res.result, "regex search matches first line")

	os.unlink(tmp.name)

	# ---- read of huge file blocked ----
	huge = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
	huge.close()
	with open(huge.name, "w") as f:
		f.seek(200 * 1024)
		f.write("x")
	res = tool.execute({"action": "read", "file_path": huge.name})
	t.check(res.status == "error", "huge file read blocked")
	t.check("too large" in res.error_message, "huge file error mentions size")
	os.unlink(huge.name)

	return t.summary("tools.edit_file")
