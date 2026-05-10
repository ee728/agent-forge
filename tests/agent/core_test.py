from tests.check import TestResult
from agent.llm import BaseLLM, LLMResponse, ToolCall
from tools import ToolRegistry
from tools.todo_task import AgentTodoTool


class MockLLM(BaseLLM):
	def __init__(self):
		self.call_count = 0
	def chat(self, messages, tools=None):
		self.call_count += 1
		return LLMResponse(
			content="Mock response",
			finish_reason="stop",
			usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
			model="mock",
			raw_message={"role": "assistant", "content": "Mock response"}
		)


def suite():
	from agent import Agent
	t = TestResult()

	# ---- 4-layer message structure ----
	registry = ToolRegistry()
	llm = MockLLM()
	agent = Agent(llm, registry, "Hello system")

	t.check(len(agent.system_layer) == 1, "system_layer starts with 1 message")
	t.check(agent.system_layer[0]["role"] == "system", "system_layer role is system")
	t.check(agent.system_layer[0]["content"] == "Hello system", "system_layer content matches")
	t.check(agent.summary_layer == [], "summary_layer starts empty")
	t.check(agent.skills_layer == [], "skills_layer starts empty")
	t.check(agent.conversation == [], "conversation starts empty")

	# _messages property assembles all layers
	msgs = agent._messages
	t.check(len(msgs) == 1, "_messages assembles layers")
	t.check(msgs[0]["role"] == "system", "_messages[0] is system")

	# ---- Skill injection ----
	agent._inject_skill("test_skill", "content")
	t.check(len(agent.skills_layer) == 1, "skill injection adds to skills_layer")
	t.check("Loaded skill: test_skill" in agent.skills_layer[0]["content"],
		"skill message has correct prefix")
	t.check(len(agent._messages) == 2, "_messages grows with skill")
	t.check(len(agent.system_layer) == 1, "system_layer unchanged by skill")

	agent._inject_skill("skill2", "more")
	t.check(len(agent.skills_layer) == 2, "multiple skills accumulate")
	t.check(len(agent._messages) == 3, "_messages reflects all layers")

	# ---- Context engineering ----
	registry2 = ToolRegistry()
	registry2.register(AgentTodoTool())
	agent2 = Agent(llm, registry2, "system")
	agent2._rounds_since_todo_update = 3
	agent2.conversation.append({"role": "user", "content": "hello"})
	agent2._Agent__context_engineering()

	t.check(len(agent2.conversation) == 2, "reminder appended after 3 rounds")
	t.check(agent2.conversation[-1]["role"] == "user", "reminder has user role")
	t.check("Reminder" in agent2.conversation[-1]["content"],
		"reminder contains Reminder text")
	t.check(agent2._rounds_since_todo_update == 0, "rounds reset after reminder")

	# without todo tool registered
	registry3 = ToolRegistry()
	agent3 = Agent(llm, registry3, "system")
	agent3._rounds_since_todo_update = 5
	agent3._Agent__context_engineering()
	t.check(len(agent3.conversation) == 0,
		"no reminder without todo tool")

	# ---- is_todo_update ----
	t.check(agent._is_todo_update(ToolCall(id="1", name="todo", arguments={"action": "update"})),
		"todo update detected")
	t.check(not agent._is_todo_update(ToolCall(id="2", name="todo", arguments={"action": "list"})),
		"todo list not treated as update")
	t.check(not agent._is_todo_update(ToolCall(id="3", name="edit_file", arguments={})),
		"non-todo tool not treated as update")

	# ---- compress command generates correct instruction ----
	compress_input = (
		"(System instruction) Compress this conversation using the compress_context "
		"tool. Write a concise English summary covering: what was accomplished, key "
		"decisions, current state, and any pending issues. Then confirm completion "
		"with a brief message."
	)
	t.check("compress_context" in compress_input, "compress instruction mentions tool")
	t.check("English summary" in compress_input, "compress instruction demands English")
	t.check("key decisions" in compress_input, "compress instruction covers key decisions")

	return t.summary("agent.core")
