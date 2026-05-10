import os
from tests.check import TestResult
from tools.sub_agent import SubAgentTool, CONFIG_PATH

def suite():
	tool = SubAgentTool()
	t = TestResult()

	# ---- basic structure ----
	t.check(tool.name == "sub_agent", "tool name is sub_agent")
	t.check("sub-agent" in tool.description.lower(),
		"description mentions sub-agent")

	# ---- schema ----
	schema = tool.to_openai_schema()
	func = schema["function"]
	t.check(func["name"] == "sub_agent", "schema function name")
	props = func["parameters"]["properties"]
	t.check("role" in props, "schema has role param")
	t.check("task" in props, "schema has task param")
	t.check("context" in props, "schema has context param")
	t.check(
		func["parameters"]["required"] == ["role", "task"],
		"required params are role and task"
	)

	# ---- _build_system_prompt ----
	prompt = tool._build_system_prompt("test engineer")
	t.check("test engineer" in prompt, "prompt contains role name")
	t.check("specialized AI assistant" in prompt,
		"prompt contains identity")

	# ---- error: missing role ----
	res = tool.execute({"task": "do something"})
	t.check(res.status == "error", "missing role returns error")
	t.check("role" in (res.error_message or "").lower(),
		"error mentions role")

	# ---- error: missing task ----
	res = tool.execute({"role": "coder"})
	t.check(res.status == "error", "missing task returns error")
	t.check("task" in (res.error_message or "").lower(),
		"error mentions task")

	# ---- error: empty role ----
	res = tool.execute({"role": "", "task": "work"})
	t.check(res.status == "error", "empty role returns error")

	# ---- error: empty task ----
	res = tool.execute({"role": "coder", "task": ""})
	t.check(res.status == "error", "empty task returns error")

	# ---- error: both missing ----
	res = tool.execute({})
	t.check(res.status == "error", "both missing returns error")

	# ---- _load_config reads real config ----
	try:
		cfg = tool._load_config()
		t.check("model" in cfg, "config has model")
		t.check("api_key" in cfg, "config has api_key")
		t.check("base_url" in cfg, "config has base_url")
	except Exception as e:
		t.check(False, f"load config failed: {e}")

	# ---- config not found error ----
	orig = None
	try:
		if os.path.isfile(CONFIG_PATH):
			orig = CONFIG_PATH
			os.rename(CONFIG_PATH, CONFIG_PATH + ".bak")
			tool._load_config()
			t.check(False, "should have raised")
	except FileNotFoundError:
		t.check(True, "missing config raises error")
	except Exception as e:
		t.check(False, f"unexpected error: {e}")
	finally:
		if orig:
			os.rename(orig + ".bak", orig)

	return t.summary("tools.sub_agent")