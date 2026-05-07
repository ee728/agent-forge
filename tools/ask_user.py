"""
询问用户 工具
================

当agent遇到权限不足或者需要用户确认时，使用此工具与用户交互。

"""

from .base import BaseTool
from .base import ToolExecutionResult
from utils import Logger
import json

class AskUserTool(BaseTool):
	"""
	向用户发起询问，等待用户输入响应。

	参数:
		request: 对用户的请求

	"""

	name = "ask_user"
	description = "当需要用户确认或输入时调用此工具，会暂停执行等待用户响应"
	parameters = {
        "type": "object",
        "properties": {
		"request": {
			"type": "string", 
			"description": "向用户展示的请求内容，应明确说明需要用户做什么（如确认/输入信息）"
			},
		"expected_response": {
			"type": "string",
			"description": "期望的用户响应类型（如'yes/no'、'file_path'等）",
			"default": "any"
			}
		},
		"required": ["request"]
	}

	def _get_user_input(self) -> str:
		try:
			raw_input = input("\n👤 \033[1;34mUser\033[0m => ")
			cleaned_input = raw_input.strip()
			if not cleaned_input:
				return "" 
			return cleaned_input
		except (KeyboardInterrupt, EOFError):
			return ""

	def execute(self, arguments:dict) -> ToolExecutionResult:
		self.exe_result = ToolExecutionResult(None,None,None,None,None)
		self.exe_result.tool_name = self.name
		self.exe_result.parameters = arguments
		try:
			output_str = self._get_user_input()
			self.exe_result.status = "success"
			self.exe_result.result = output_str
			self.exe_result.error_message = None
		except Exception as e:
			output_str = f"Error:{e}"
			self.exe_result.status = "error"
			self.exe_result.result = None
			self.exe_result.error_message = output_str
		return self.exe_result


