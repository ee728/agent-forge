import subprocess
from .base import BaseTool
from .base import ToolExecutionResult
from utils import Logger
import json

class LocalShellTool(BaseTool):
	"""
	Execute a shell command on the local development machine.
	"""

	name = "local_shell"
	description = "Execute a shell command on the local development machine"
	parameters = {
		"type": "object",
		"properties": {
			"command": {"type": "string", "description": "Shell command to execute"},
			"timeout": {
				"type": "integer",
				"description": "Command timeout in seconds, default 60",
				"default": 60,
			},
			"workdir": {
				"type": "string",
				"description": "Working directory (optional, defaults to current dir)",
			},
		},
		"required": ["command"],
	}

	def execute(self, arguments:dict) -> ToolExecutionResult:
		self.exe_result = ToolExecutionResult(None,None,None,None,None)
		self.exe_result.tool_name = self.name
		self.exe_result.parameters = arguments
		try:
			command = arguments["command"]
			timeout = arguments.get("timeout",60)
			workdir = arguments.get("workdir",'.')
			result = subprocess.run(
				command,shell=True,capture_output=True,text=True,timeout=timeout,cwd=workdir
			)
			output_str = (result.stdout or result.stderr).strip()
			if result.returncode == 0:
				self.exe_result.status = "success"
				self.exe_result.result = output_str
				self.exe_result.error_message = None
			else:
				self.exe_result.status = "error"
				self.exe_result.result = None
				self.exe_result.error_message = output_str
		except Exception as e:
			output_str = f"Error:{e}"
			self.exe_result.status = "error"
			self.exe_result.result = None
			self.exe_result.error_message = output_str
		return self.exe_result
