import json
from typing import Dict, Any, Optional
from attr import dataclass
from utils import Logger


@dataclass
class ToolExecutionResult():
	tool_name: str
	parameters: Dict[str, Any]
	status: str
	result: Any
	error_message: Optional[str]

	@property
	def result_to_str(self) -> str:
		d = {}
		d["tool_name"] = self.tool_name
		d["parameters"] = self.parameters
		d["status"] = self.status
		d["result"] = self.result
		d["error_message"] = self.error_message
		return json.dumps(d, ensure_ascii=False, indent=2)


class BaseTool:
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
	def __init__(self):
		self._tools: dict[str, BaseTool] = {}
		self.log_executor = Logger(default_color='white', default_style='normal', show_time=False)

	def register(self, tool: BaseTool):
		self._tools[tool.name] = tool

	def get_schemas(self) -> list:
		return [tool.to_openai_schema() for tool in self._tools.values()]

	def execute(self, name: str, arguments: dict) -> ToolExecutionResult:
		tool = self._tools.get(name)
		if not tool:
			return ToolExecutionResult(
				tool_name=name,
				parameters=arguments,
				status="error",
				result=None,
				error_message=f"tool '{name}' not found"
			)
		try:
			exe_result = tool.execute(arguments)
			print(exe_result)
			return exe_result
		except Exception as e:
			self.log_executor.log(f"Tool execution failed: {str(e)}", color='red')
			return ToolExecutionResult(
				tool_name=name,
				parameters=arguments,
				status="error",
				result=None,
				error_message=str(e)
			)

	def list_tools(self) -> list[str]:
		return list(self._tools.keys())

	def get_tool(self, name: str) -> Optional[BaseTool]:
		return self._tools.get(name)
