from tests.check import TestResult
from tools.compress_context import CompressContextTool


def suite():
	tool = CompressContextTool()
	t = TestResult()

	# description mentions English
	t.check("English" in tool.description, "tool description mentions English")
	t.check("English" in tool.parameters["properties"]["summary"]["description"],
		"summary param description mentions English")

	# success
	res = tool.execute({"summary": "User asked for help. Completed the task."})
	t.check(res.status == "success", "compress with summary succeeds")
	t.check(res.result == "User asked for help. Completed the task.",
		"summary returned as result")

	# missing summary
	res = tool.execute({})
	t.check(res.status == "error", "empty args returns error")
	t.check("summary" in res.error_message, "error mentions required summary")

	res = tool.execute({"summary": ""})
	t.check(res.status == "error", "empty summary returns error")

	return t.summary("tools.compress")
