import os
from .base import BaseTool
from .base import ToolExecutionResult


class EditFileTool(BaseTool):
	name = "edit_file"
	description = "Read, write, or edit files on the local filesystem with line-level precision"
	parameters = {
		"type": "object",
		"properties": {
			"action": {
				"type": "string",
				"enum": ["read", "write", "edit"],
				"description": "read: view file content (optionally a line range) | write: create or overwrite a file | edit: replace a specific line range",
			},
			"file_path": {
				"type": "string",
				"description": "Absolute or relative path to the target file",
			},
			"content": {
				"type": "string",
				"description": "Text content. Required for 'write' and 'edit'.",
			},
			"line_start": {
				"type": "integer",
				"description": "Start line (1-indexed, inclusive). For 'read' (optional), for 'edit' (required).",
			},
			"line_end": {
				"type": "integer",
				"description": "End line (1-indexed, inclusive). For 'read' (optional), for 'edit' (required).",
			},
		},
		"required": ["action", "file_path"],
	}

	MAX_READ_SIZE = 100 * 1024

	def _read(self, file_path: str, line_start: int = None, line_end: int = None) -> str:
		if not os.path.isfile(file_path):
			return f"Error: file not found: {file_path}"

		size = os.path.getsize(file_path)
		if size > self.MAX_READ_SIZE:
			return f"Error: file too large ({size} bytes). Max allowed: {self.MAX_READ_SIZE} bytes."

		with open(file_path, "r", encoding="utf-8", errors="replace") as f:
			lines = f.readlines()

		total = len(lines)
		if line_start is None:
			line_start = 1
		if line_end is None:
			line_end = total

		line_start = max(1, line_start)
		line_end = min(total, line_end)

		if line_start > line_end:
			return f"Error: line_start ({line_start}) > line_end ({line_end})"

		selected = lines[line_start - 1 : line_end]
		output = "".join(selected)
		header = f"--- {file_path} (lines {line_start}-{line_end}/{total}) ---\n"
		return header + output

	def _write(self, file_path: str, content: str) -> str:
		os.makedirs(os.path.dirname(os.path.abspath(file_path)) or ".", exist_ok=True)
		with open(file_path, "w", encoding="utf-8") as f:
			f.write(content)
		return f"Written {len(content)} bytes to {file_path}"

	def _edit(self, file_path: str, line_start: int, line_end: int, content: str) -> str:
		if not os.path.isfile(file_path):
			return f"Error: file not found: {file_path}"

		with open(file_path, "r", encoding="utf-8", errors="replace") as f:
			lines = f.readlines()

		total = len(lines)
		line_start = max(1, line_start)
		line_end = min(total, line_end)

		if line_start > line_end:
			return f"Error: line_start ({line_start}) > line_end ({line_end})"

		replacement = content.splitlines(keepends=True)
		before = lines[: line_start - 1]
		after = lines[line_end:]

		new_lines = before + replacement + after
		with open(file_path, "w", encoding="utf-8") as f:
			f.writelines(new_lines)

		return f"Replaced lines {line_start}-{line_end} in {file_path} ({len(lines)} lines → {len(new_lines)} lines)"

	def execute(self, arguments: dict) -> ToolExecutionResult:
		self.exe_result = ToolExecutionResult(None, None, None, None, None)
		self.exe_result.tool_name = self.name
		self.exe_result.parameters = arguments

		action = arguments.get("action")
		file_path = arguments.get("file_path")

		if not file_path:
			return self._error(arguments, "file_path is required")

		try:
			if action == "read":
				output = self._read(file_path, arguments.get("line_start"), arguments.get("line_end"))
			elif action == "write":
				content = arguments.get("content")
				if content is None:
					return self._error(arguments, "write action requires 'content'")
				output = self._write(file_path, content)
			elif action == "edit":
				content = arguments.get("content")
				ls = arguments.get("line_start")
				le = arguments.get("line_end")
				if content is None or ls is None or le is None:
					return self._error(arguments, "edit action requires 'content', 'line_start', and 'line_end'")
				output = self._edit(file_path, ls, le, content)
			else:
				return self._error(arguments, f"unknown action: {action}")

			self.exe_result.status = "success"
			self.exe_result.result = output
			self.exe_result.error_message = None

		except Exception as e:
			self.exe_result.status = "error"
			self.exe_result.result = None
			self.exe_result.error_message = str(e)

		return self.exe_result

	def _error(self, params: dict, msg: str) -> ToolExecutionResult:
		self.exe_result.status = "error"
		self.exe_result.result = None
		self.exe_result.error_message = msg
		self.exe_result.parameters = params
		return self.exe_result
