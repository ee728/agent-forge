#!/usr/bin/env python3
"""
AI Agent 入口
==============

启动顺序:
1. 加载 system prompt
2. 初始化 LLM 客户端
3. 创建工具注册中心并注册工具
4. 创建 Agent 实例
5. 启动交互循环
"""

from agent import Agent, LLMFactory
from tools import ToolRegistry
from tools.shell import LocalShellTool
from tools.ask_user import AskUserTool
from tools.todo_task import AgentTodoTool
from tools.skill_loader import LoadSkillTool
from tools.edit_file import EditFileTool
from tools.compress_context import CompressContextTool
from tools.sub_agent import SubAgentTool


def main():
	system_prompt = open("prompts/system.md").read()

	llm = LLMFactory.create()
	registry = ToolRegistry()
	registry.register(LocalShellTool())
	registry.register(AskUserTool())
	registry.register( AgentTodoTool())
	registry.register( LoadSkillTool())
	registry.register( EditFileTool())
	registry.register( CompressContextTool())
	registry.register( SubAgentTool(llm=llm, main_registry=registry))

	skill_tool = registry.get_tool("load_skill")
	if skill_tool:
		skill_list = skill_tool.list_skills()
		system_prompt += "\n\n# Available Skills\nYou can load any of these with load_skill:\n" + skill_list

	agent = Agent(llm, registry, system_prompt)
	agent.run()


if __name__ == "__main__":
	main()
