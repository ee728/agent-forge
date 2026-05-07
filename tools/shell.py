"""
本地 Shell 工具
================

在本地（你的开发机）上执行命令。
主要用于：
- 编译测试代码
- 运行本地测试脚本
- 文件操作
- 调用 git 等版本控制工具

安全考虑：
- 限制可执行命令的范围（避免 rm -rf / 这种事）
- 设置命令超时
- 记录所有执行的命令供审计
"""
from ast import arg
import subprocess
from .base import BaseTool
from .base import ToolExecutionResult
from utils import Logger
import json

class LocalShellTool(BaseTool):
	"""
	在本地执行 shell 命令。

	参数:
		command: 要执行的命令
		timeout: 超时秒数（默认 60）
		workdir: 工作目录（可选）

	实现提示:
	- 使用 subprocess 模块
	- 捕获 stdout 和 stderr
	- 设置合理的超时，超时时 kill 子进程
	- 返回命令的完整输出
	"""

	name = "local_shell"
	description = "在本地开发机上执行 shell 命令"
	parameters = {
		"type": "object",
		"properties": {
			"command": {"type": "string", "description": "要执行的命令"},
			"timeout": {
				"type": "integer",
				"description": "超时秒数，默认 60",
				"default": 60,
			},
			"workdir": {
				"type": "string",
				"description": "工作目录（可选，默认当前目录）",
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
