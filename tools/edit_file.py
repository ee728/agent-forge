import os
import re
from .base import BaseTool, ToolExecutionResult


class EditFileTool(BaseTool):
	"""Read, search, write, or edit files with line-level precision.

	Usage guidance for LLM:
	- First use ``read`` without line range to preview the first 50 lines.
	- Use ``search`` with a keyword to find relevant sections.
	- Read specific line ranges with ``read`` + line_start/line_end.
	- This avoids reading entire large files into context.
	"""
	name = "edit_file"
	description = (
		"Read, search, write, or edit files. "
		"To avoid context overflow, first read a small range or search for keywords, "
		"then read specific sections."
	)
	parameters = {
		"type": "object",
		"properties": {
			"action": {
				"type": "string",
				"enum": ["read", "search", "write", "edit"],
				"description": (
					"read: view file content (optionally a line range, defaults to lines 1-50) | "
					"search: find lines matching a pattern with context | "
					"write: create or overwrite a file | "
					"edit: replace a specific line range"
				),
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
				"description": "Start line (1-indexed, inclusive). For 'read' (optional, defaults to 1), for 'edit' (required).",
			},
			"line_end": {
				"type": "integer",
				"description": "End line (1-indexed, inclusive). For 'read' (optional, defaults to 50), for 'edit' (required).",
			},
			"pattern": {
				"type": "string",
				"description": "Python regex pattern to search for. Required for 'search'.",
			},
			"context": {
				"type": "integer",
				"description": "Lines of context before/after each match. Optional, defaults to 2. For 'search' only.",
			},
		},
		"required": ["action", "file_path"],
	}

	MAX_READ_SIZE = 100 * 1024
	PREVIEW_LINES = 50

	def _read(self, file_path: str, line_start: int = None, line_end: int = None) -> str:
		if not os.path.isfile(file_path):
			raise ValueError(f"file not found: {file_path}")

		size = os.path.getsize(file_path)
		if size > self.MAX_READ_SIZE:
			raise ValueError(
				f"file too large ({size} bytes), max allowed: {self.MAX_READ_SIZE} bytes. "
				f"Use search with a keyword pattern to find relevant sections."
			)

		with open(file_path, "r", encoding="utf-8", errors="replace") as f:
			lines = f.readlines()

		total = len(lines)
		if line_start is None:
			line_start = 1
		if line_end is None:
			line_end = min(self.PREVIEW_LINES, total)

		line_start = max(1, line_start)
		line_end = min(total, line_end)

		if line_start > line_end:
			raise ValueError(f"line_start ({line_start}) > line_end ({line_end})")

		selected = lines[line_start - 1: line_end]
		output = "".join(selected)
		if not output.endswith("\n"):
			output += "\n"
		return f"--- {file_path} (lines {line_start}-{line_end}/{total}) ---\n{output}"

	def _search(self, file_path: str, pattern: str, context: int = 2) -> str:
		if not os.path.isfile(file_path):
			raise ValueError(f"file not found: {file_path}")

		size = os.path.getsize(file_path)
		if size > self.MAX_READ_SIZE:
			raise ValueError(
				f"file too large ({size} bytes), max allowed: {self.MAX_READ_SIZE} bytes"
			)

		with open(file_path, "r", encoding="utf-8", errors="replace") as f:
			lines = f.readlines()

		compiled = re.compile(pattern)
		total = len(lines)
		matches = []
		shown_lines = set()

		for i, line in enumerate(lines):
			if compiled.search(line):
				start = max(0, i - context)
				end = min(total, i + context + 1)
				for j in range(start, end):
					if j not in shown_lines:
						prefix = ">" if j == i else " "
						matches.append(f"  {prefix} {j + 1:>6}: {lines[j].rstrip()}")
						shown_lines.add(j)

		if not matches:
			return f"No matches for pattern {pattern!r} in {file_path}"

		header = f"--- {file_path} ({len(matches)} context lines, {len(shown_lines)} unique) ---"
		return header + "\n" + "\n".join(matches)

	def _write(self, file_path: str, content: str) -> str:
		os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
		with open(file_path, "w", encoding="utf-8") as f:
			f.write(content)
		return f"Written {len(content)} bytes to {file_path}"

	def _edit(self, file_path: str, line_start: int, line_end: int, content: str) -> str:
		if not os.path.isfile(file_path):
			raise ValueError(f"file not found: {file_path}")

		with open(file_path, "r", encoding="utf-8", errors="replace") as f:
			lines = f.readlines()

		total = len(lines)
		line_start = max(1, line_start)
		line_end = min(total, line_end)

		if line_start > line_end:
			raise ValueError(f"line_start ({line_start}) > line_end ({line_end})")

		replacement = content.splitlines(keepends=True)
		before = lines[:line_start - 1]
		after = lines[line_end:]

		new_lines = before + replacement + after
		with open(file_path, "w", encoding="utf-8") as f:
			f.writelines(new_lines)

		return (
			f"Replaced lines {line_start}-{line_end} in {file_path} "
			f"({len(lines)} lines -> {len(new_lines)} lines)"
		)

	def execute(self, arguments: dict) -> ToolExecutionResult:
		action = arguments.get("action")
		file_path = arguments.get("file_path")

		if not file_path:
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="error", result=None, error_message="file_path is required"
			)

		try:
			if action == "read":
				output = self._read(
					file_path,
					arguments.get("line_start"),
					arguments.get("line_end"),
				)
			elif action == "search":
				pattern = arguments.get("pattern")
				if not pattern:
					return ToolExecutionResult(
						tool_name=self.name, parameters=arguments,
						status="error", result=None,
						error_message="search action requires 'pattern'",
					)
				output = self._search(
					file_path, pattern,
					arguments.get("context", 2),
				)
			elif action == "write":
				content = arguments.get("content")
				if content is None:
					return ToolExecutionResult(
						tool_name=self.name, parameters=arguments,
						status="error", result=None,
						error_message="write action requires 'content'",
					)
				output = self._write(file_path, content)
			elif action == "edit":
				content = arguments.get("content")
				ls = arguments.get("line_start")
				le = arguments.get("line_end")
				if content is None or ls is None or le is None:
					return ToolExecutionResult(
						tool_name=self.name, parameters=arguments,
						status="error", result=None,
						error_message="edit action requires 'content', 'line_start', and 'line_end'",
					)
				output = self._edit(file_path, ls, le, content)
			else:
				return ToolExecutionResult(
					tool_name=self.name, parameters=arguments,
					status="error", result=None,
					error_message=f"unknown action: {action}",
				)

			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="success", result=output, error_message=None,
			)
		except Exception as e:
			return ToolExecutionResult(
				tool_name=self.name, parameters=arguments,
				status="error", result=None, error_message=str(e),
			)
