"""
SubAgent Tool
=============

Delegates tasks to a child Agent that shares the same LLM and tools
(except sub_agent itself, to prevent infinite recursion).

The sub-agent runs a full ReAct loop: it can read files, run shell
commands, and use any other registered tool. The main agent controls
what task to assign and optionally provides a custom system prompt.
"""

from .base import BaseTool, ToolExecutionResult
from tools import ToolRegistry
from agent import Agent


class SubAgentTool(BaseTool):
	name = "sub_agent"
	description = (
		"Create a sub-agent to work on a task. "
		"The sub-agent has access to all tools except sub_agent itself. "
		"You can optionally set a custom system prompt for it."
	)
	parameters = {
		"type": "object",
		"properties": {
			"role": {
				"type": "string",
				"description": "The role/persona for the sub-agent. Examples: 'Python code reviewer', 'test engineer'",
			},
			"task": {
				"type": "string",
				"description": "The specific task for the sub-agent to execute",
			},
			"system_prompt": {
				"type": "string",
				"description": "Optional custom system prompt. If omitted, a default prompt based on the role is used.",
			},
		},
		"required": ["role", "task"],
	}

	def __init__(self, llm=None, main_registry=None):
		self._llm = llm
		self._main_registry = main_registry

	@staticmethod
	def _default_system_prompt(role: str) -> str:
		return (
			f"You are a specialized AI assistant acting as: {role}. "
			f"Focus on your assigned role and complete the task. "
			f"Respond with thorough, high-quality work. "
			f"Use Chinese for your final responses."
		)

	def execute(self, arguments: dict) -> ToolExecutionResult:
		role = arguments.get("role")
		task = arguments.get("task")
		system_prompt = arguments.get("system_prompt")

		if not role:
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="error", result=None,
				error_message="'role' is required",
			)
		if not task:
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="error", result=None,
				error_message="'task' is required",
			)

		if not system_prompt:
			system_prompt = self._default_system_prompt(role)

		try:
			# Build a filtered registry (no sub_agent to prevent recursion)
			sub_registry = ToolRegistry()
			for name, tool in self._main_registry._tools.items():
				if name != "sub_agent":
					sub_registry.register(tool)

			sub = Agent(self._llm, sub_registry, system_prompt)
			result = sub._process(task)

			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="success", result=result,
				error_message=None,
			)
		except Exception as e:
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="error", result=None,
				error_message=f"SubAgent error: {type(e).__name__}: {e}",
			)
