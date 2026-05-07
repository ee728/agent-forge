"""
工具系统基类
=============

工具是 Agent 能力的延伸。Agent 本身不做具体事情，而是通过"工具"来执行操作。
LLM 决定 "什么时候调用哪个工具、传什么参数"。

工具 = 一个可以被 LLM 调用的函数 / API

设计思路：
1. 每个工具都是一个类，继承 BaseTool
2. 工具需要提供 schema 描述（告诉 LLM 这个工具是做什么的、需要什么参数）
3. 工具需要实现 execute 方法（实际的执行逻辑）
4. ToolRegistry 管理所有注册的工具

LLM 调用工具的流程：
   LLM: "我需要调用 tool_a，参数是 {...}"
   Agent: 执行 tool_a.execute(**params)
   Agent: 把结果返回给 LLM
   LLM: "好的，根据结果我..."
"""

import json
from typing import Dict, Any, Optional
from unittest import result
from attr import dataclass
from typing_extensions import TypedDict
from utils import Logger

@dataclass
class ToolExecutionResult():
	tool_name:str
	parameters:Dict[str,Any]
	status:str
	result:Any
	error_message:Optional[str]

	@property
	def result_to_str(self) -> str:
		dict = {}
		dict["tool_name"]=self.tool_name
		dict["parameters"]=self.parameters
		dict["status"]=self.status
		dict["result"]=self.result
		dict["error_message"]=self.error_message
		return json.dumps(dict, ensure_ascii=False, indent=2)


class BaseTool:
	"""
	所有工具的基类。

	子类需要定义：
	- name: 工具名称（LLM 通过这个名字来调用）
	- description: 工具描述（LLM 根据这个决定是否使用该工具）
	- parameters: 参数 JSON Schema（告诉 LLM 需要传什么参数）

	子类需要实现：
	- execute(**kwargs): 工具的实际逻辑
	"""

	name: str = ""
	description: str = ""
	parameters: dict = {}
	exe_result = ToolExecutionResult

	def to_openai_schema(self) -> dict:

		return {
			"type": "function",
			"function": {
				"name": self.name,
				"description": self.description,
				"parameters": self.parameters,
			},
		}

	def execute(self, **kwargs) -> ToolExecutionResult:
		raise NotImplementedError


class ToolRegistry:
	"""
	工具注册中心，管理所有可用的工具。

	职责：
	1. 注册工具
	2. 根据名称查找工具
	3. 生成所有工具的 schema 列表（发给 LLM）
	4. 执行工具调用
	"""

	def __init__(self):
		self._tools: dict[str, BaseTool] = {}
		self.log_executor = Logger(default_color='white', default_style='normal', show_time=False)

	def register(self, tool: BaseTool):
		self._tools[tool.name] = tool

	def get_schemas(self) -> list:
		return [tool.to_openai_schema() for tool in self._tools.values()]

	def execute(self, name: str, arguments: dict) -> ToolExecutionResult:
		tool = self._tools[name]
		if tool:
			try:
				exe_result = tool.execute(arguments)
				# return tool.execute(arguments)
				print(exe_result)
				return exe_result
			except Exception as e:
					self.log_executor.log(f"工具执行失败: {str(e)}", color='red')
					return ToolExecutionResult(
					tool_name=name,
					parameters=arguments,
					status="error",
					result=None,
					error_message=str(e)
				)
		else:
			return ToolExecutionResult(
				tool_name=name,
				parameters=arguments,
				status="error",
				result=None,
				error_message=f"tool '{name}' not found"
			)

	def list_tools(self) -> list[str]:
		return list(self._tools.keys())
