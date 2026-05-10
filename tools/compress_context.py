from .base import BaseTool
from .base import ToolExecutionResult


class CompressContextTool(BaseTool):
	name = "compress_context"
	description = "Summarize the conversation history to free up context. Call this when the conversation is getting long or before saving."
	parameters = {
		"type": "object",
		"properties": {
			"summary": {
				"type": "string",
				"description": "Concise summary covering: what was accomplished, key decisions, current state, and any pending issues.",
			},
		},
		"required": ["summary"],
	}

	def execute(self, arguments: dict) -> ToolExecutionResult:
		self.exe_result = ToolExecutionResult(None, None, None, None, None)
		self.exe_result.tool_name = self.name
		self.exe_result.parameters = arguments
		summary = arguments.get("summary", "")

		if not summary:
			self.exe_result.status = "error"
			self.exe_result.error_message = "summary is required"
		else:
			self.exe_result.status = "success"
			self.exe_result.result = summary
			self.exe_result.error_message = None

		return self.exe_result
