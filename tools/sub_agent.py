"""
SubAgent 工具
==============

让主 Agent（BOSS）创建指定角色的子 Agent 来分派任务。

设计原则：
- 子 Agent 是独立的 LLM 调用，拥有自己的角色身份
- 每个子 Agent 是无状态的，每次调用独立
- 主 Agent 可以串行地分派任务给多个子 Agent
- 子 Agent 没有工具访问权限，专注思考和内容生成

用法（主 Agent 视角）：
  1. 决定需要什么角色
  2. 调用 sub_agent(role="...", task="...")
  3. 获取返回结果，继续下一步
"""

import json
import os
import requests
from .base import BaseTool, ToolExecutionResult


CONFIG_PATH = os.path.join(
	os.path.dirname(os.path.dirname(__file__)),
	"config", "llm_config.json"
)

class SubAgentTool(BaseTool):
	name = "sub_agent"
	description = (
		"Create a sub-agent with a specific role to work on a task. "
		"You are the boss agent \u2014 delegate work to specialized sub-agents "
		"and get their results back."
	)
	parameters = {
		"type": "object",
		"properties": {
			"role": {
				"type": "string",
				"description": (
					"The role/persona for the sub-agent. "
					"Examples: 'Python code reviewer', 'test engineer', "
					"'documentation writer', 'data analyst'"
				),
			},
			"task": {
				"type": "string",
				"description": "The specific task description for the sub-agent to work on",
			},
			"context": {
				"type": "string",
				"description": "Optional context or background information",
			},
		},
		"required": ["role", "task"],
	}


	@staticmethod
	def _load_config() -> dict:
		"""从配置文件读取 LLM 配置"""
		if not os.path.isfile(CONFIG_PATH):
			raise FileNotFoundError(
				f"LLM config not found: {CONFIG_PATH}"
			)
		with open(CONFIG_PATH, "r", encoding="utf-8") as f:
			config = json.load(f)
		return config["llm"]

	@staticmethod
	def _build_system_prompt(role: str) -> str:
		"""根据角色构建子 Agent 的系统提示词"""
		return (
			f"You are a specialized AI assistant acting as: {role}. "
			f"Focus on your assigned role and complete the task. "
			f"Respond with thorough, high-quality work. "
			f"Use Chinese for your final responses."
		)

	def _call_llm(
		self, role: str, task: str, context: str = ""
	) -> str:
		"""调用 LLM API 让子 Agent 执行任务"""
		cfg = self._load_config()
		messages = [
			{"role": "system",
			 "content": self._build_system_prompt(role)},
		]
		if context:
			messages.append({
				"role": "user",
				"content": f"[Background Context]\n{context}"
			})
		messages.append({"role": "user", "content": task})

		payload = {
			"model": cfg["model"],
			"messages": messages,
			"temperature": cfg.get("temperature", 0.7),
			"max_tokens": cfg.get("max_tokens", 4096),
		}
		resp = requests.post(
			f"{cfg['base_url'].rstrip('/')}/v1/chat/completions",
			headers={
				"Authorization": f"Bearer {cfg['api_key']}",
				"Content-Type": "application/json",
			},
			json=payload,
			timeout=120,
		)
		resp.raise_for_status()
		data = resp.json()
		content = data["choices"][0]["message"].get("content", "")


	def execute(self, arguments: dict) -> ToolExecutionResult:
		"""执行子 Agent 任务"""
		role = arguments.get("role")
		task = arguments.get("task")
		context = arguments.get("context", "")

		if not role:
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="error", result=None,
				error_message="'role' is required"
			)
		if not task:
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="error", result=None,
				error_message="'task' is required"
			)
		try:
			content = self._call_llm(role, task, context)
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="success", result=content,
				error_message=None
			)
		except Exception as e:
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="error", result=None,
				error_message=f"SubAgent error: "
				             f"{type(e).__name__}: {e}"
			)
