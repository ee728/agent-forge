"""
Ask User Tool
=============

Used when the agent needs user confirmation or additional input.
"""

from .base import BaseTool
from .base import ToolExecutionResult
from utils import Logger, sanitize
import json

class AskUserTool(BaseTool):
	"""
	Pause execution and prompt the user for input.
	"""

	name = "ask_user"
	description = "Pause and ask the user for confirmation or input, then wait for their response"
	parameters = {
		"type": "object",
		"properties": {
			"request": {
				"type": "string", 
				"description": "Question or request to show the user — be explicit about what you need (confirmation / file path / value)"
			},
			"expected_response": {
				"type": "string",
				"description": "Expected response type (e.g. 'yes/no', 'file_path', 'any')",
				"default": "any"
			}
		},
		"required": ["request"]
	}

	def _get_user_input(self) -> str:
		try:
			raw_input = input("\n👤 \033[1;34mUser\033[0m => ")
			cleaned_input = sanitize(raw_input.strip())
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
