from tests.check import TestResult
from tools.sub_agent import SubAgentTool
from tools import ToolRegistry
from tools.edit_file import EditFileTool
from tools.shell import LocalShellTool


class FakeLLM:
	def __init__(self):
		self.calls = []
	def chat(self, messages, tools=None):
		self.calls.append((messages, tools))
		from agent.llm import LLMResponse
		return LLMResponse(
			content="Sub-agent response",
			finish_reason="stop",
			usage={},
			model="fake",
			raw_message={"role": "assistant", "content": "Sub-agent response"},
		)


def suite():
	t = TestResult()

	# ---- schema ----
	tool = SubAgentTool()
	t.check(tool.name == "sub_agent", "tool name is sub_agent")
	t.check("sub-agent" in tool.description.lower(),
		"description mentions sub-agent")

	schema = tool.to_openai_schema()
	func = schema["function"]
	t.check(func["name"] == "sub_agent", "schema function name")
	props = func["parameters"]["properties"]
	t.check("role" in props, "schema has role param")
	t.check("task" in props, "schema has task param")
	t.check("system_prompt" in props, "schema has system_prompt param")
	t.check("context" not in props, "schema no longer has context param")
	t.check(
		func["parameters"]["required"] == ["role", "task"],
		"required params are role and task",
	)

	# ---- _default_system_prompt ----
	prompt = tool._default_system_prompt("test engineer")
	t.check("test engineer" in prompt, "default prompt contains role name")
	t.check("specialized AI assistant" in prompt,
		"default prompt contains identity")
	t.check("Chinese" in prompt,
		"default prompt mentions Chinese responses")

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

	# ---- successful sub-agent execution ----
	llm = FakeLLM()
	registry = ToolRegistry()
	registry.register(EditFileTool())
	registry.register(LocalShellTool())
	tool2 = SubAgentTool(llm=llm, main_registry=registry)

	res = tool2.execute({"role": "debugger", "task": "find the bug"})
	t.check(res.status == "success", "sub-agent executes successfully")
	t.check(res.result == "Sub-agent response",
		"sub-agent returns LLM response")
	t.check(len(llm.calls) == 1, "LLM was called once")

	# ---- sub-agent receives filtered tools (no sub_agent) ----
	msgs, tools_schemas = llm.calls[0]
	t.check(len(tools_schemas) == 2, "sub-agent has 2 tools (not sub_agent)")
	tool_names = [s["function"]["name"] for s in tools_schemas]
	t.check("edit_file" in tool_names, "sub-agent has edit_file")
	t.check("local_shell" in tool_names, "sub-agent has local_shell")
	t.check("sub_agent" not in tool_names, "sub-agent does NOT have sub_agent")

	# ---- sub-agent uses default system prompt ----
	system_msg = msgs[0]
	t.check(system_msg["role"] == "system", "first message is system prompt")
	t.check("debugger" in system_msg["content"],
		"default system prompt contains role")

	# ---- sub-agent with custom system prompt ----
	llm2 = FakeLLM()
	tool3 = SubAgentTool(llm=llm2, main_registry=registry)
	res = tool3.execute({
		"role": "coder",
		"task": "write code",
		"system_prompt": "You are a custom coder. Be concise.",
	})
	t.check(res.status == "success", "custom prompt sub-agent succeeds")
	msgs2, _ = llm2.calls[0]
	t.check("custom coder" in msgs2[0]["content"],
		"custom system prompt used instead of default")

	# ---- sub-agent receives task as user message ----
	user_msg = msgs2[1]
	t.check(user_msg["role"] == "user", "second message is user")
	t.check(user_msg["content"] == "write code", "user message is the task")

	return t.summary("tools.sub_agent")
