from .base import BaseTool
from .base import ToolExecutionResult
from utils import Logger
import json


class AgentTodoTool(BaseTool):
	name = "todo"
	description = (
		"Manage task checklists. "
		"For any multi-step task (>=2 tool calls), you MUST use this tool to "
		"break it down into tracked steps before executing them."
	)
	parameters = {
		"type": "object",
		"properties": {
			"action": {
				"type": "string",
				"enum": ["create", "list", "update", "delete", "clear"],
				"description": "create: add a new task | list: view all tasks | update: change task status | delete: remove a task | clear: remove completed/failed tasks",
			},
			"task_id": {
				"type": "string",
				"description": "Task ID (format t-001). Not needed for 'create', required for all other actions.",
			},
			"description": {
				"type": "string",
				"description": "Task description. Required for 'create'.",
			},
			"status": {
				"type": "string",
				"enum": ["pending", "in_progress", "completed", "failed"],
				"description": "Task status. Required for 'update'.",
			},
			"result": {
				"type": "string",
				"description": "Execution result summary. Optional, used with 'update'.",
			},
		},
		"required": ["action"],
	}

	_tasks: list[dict] = []
	_next_id: int = 1

	_renderer = Logger(default_color="white", default_style="normal", show_time=False)

	def _generate_id(self) -> str:
		task_id = f"t-{self._next_id:03d}"
		self.__class__._next_id += 1
		return task_id

	def __render(self, tasks: list[dict]) -> str:
		if not tasks:
			return "No tasks yet."

		lines = []
		status_style = {
			"pending": ("yellow", "⏳"),
			"in_progress": ("blue", "🔄"),
			"completed": ("green", "✅"),
			"failed": ("red", "❌"),
		}

		lines.append(self._renderer.log("=" * 50, color="cyan", style="bold", to_shell=False))
		lines.append(self._renderer.log("              📋 TASK BOARD", color="cyan", style="bold", to_shell=False))
		lines.append(self._renderer.log("=" * 50, color="cyan", style="bold", to_shell=False))

		for task in tasks:
			color, icon = status_style.get(task["status"], ("white", "❓"))
			line = f"  {task['id']}  {icon}  | {task['description']}"
			lines.append(self._renderer.log(line, color=color, to_shell=False))
			if task["result"]:
				lines.append(self._renderer.log(f"       └─ {task['result']}", color="white", style="dim", to_shell=False))

		lines.append(self._renderer.log("=" * 50, color="cyan", style="bold", to_shell=False))

		summary = {s: len([t for t in tasks if t["status"] == s]) for s in ["pending", "in_progress", "completed", "failed"]}
		lines.append(self._renderer.log(f"  📊 Total: {len(tasks)} | ⏳ {summary['pending']}  🔄 {summary['in_progress']}  ✅ {summary['completed']}  ❌ {summary['failed']}", color="white", style="bold", to_shell=False))
		lines.append(self._renderer.log("=" * 50, color="cyan", style="bold", to_shell=False))

		return "\n".join(lines)

	def _create(self, description: str) -> str:
		task = {
			"id": self._generate_id(),
			"description": description,
			"status": "pending",
			"result": "",
		}
		self.__class__._tasks.append(task)
		return json.dumps({"status": "ok", "task_id": task["id"]}, ensure_ascii=False)

	def _list(self, filter_status: str = None) -> str:
		tasks = self._tasks
		if filter_status:
			tasks = [t for t in tasks if t["status"] == filter_status]
		return self.__render(tasks)

	def _update(self, task_id: str, status: str, result: str = None) -> str:
		for task in self._tasks:
			if task["id"] == task_id:
				task["status"] = status
				if result is not None:
					task["result"] = result
				return json.dumps({"status": "ok", "task_id": task_id}, ensure_ascii=False)
		return json.dumps({"status": "error", "message": f"task {task_id} not found"}, ensure_ascii=False)

	def _delete(self, task_id: str) -> str:
		for i, task in enumerate(self._tasks):
			if task["id"] == task_id:
				self.__class__._tasks.pop(i)
				return json.dumps({"status": "ok", "task_id": task_id}, ensure_ascii=False)
		return json.dumps({"status": "error", "message": f"task {task_id} not found"}, ensure_ascii=False)

	def _clear(self) -> str:
		before = len(self._tasks)
		self.__class__._tasks = [t for t in self._tasks if t["status"] == "pending"]
		after = len(self._tasks)
		cleared = before - after
		return json.dumps({"status": "ok", "cleared": cleared, "remaining": after}, ensure_ascii=False)

	def execute(self, arguments: dict) -> ToolExecutionResult:
		self.exe_result = ToolExecutionResult(None, None, None, None, None)
		self.exe_result.tool_name = self.name
		self.exe_result.parameters = arguments

		action = arguments.get("action")

		try:
			if action == "create":
				desc = arguments.get("description")
				if not desc:
					raise ValueError("create action requires 'description'")
				output = self._create(desc)

			elif action == "list":
				output = self._list(arguments.get("status"))

			elif action == "update":
				task_id = arguments.get("task_id")
				status = arguments.get("status")
				if not task_id or not status:
					raise ValueError("update action requires 'task_id' and 'status'")
				output = self._update(task_id, status, arguments.get("result"))

			elif action == "delete":
				task_id = arguments.get("task_id")
				if not task_id:
					raise ValueError("delete action requires 'task_id'")
				output = self._delete(task_id)

			elif action == "clear":
				output = self._clear()

			else:
				raise ValueError(f"unknown action: {action}")

			self.exe_result.status = "success"
			self.exe_result.result = output
			self.exe_result.error_message = None

		except Exception as e:
			self.exe_result.status = "error"
			self.exe_result.result = None
			self.exe_result.error_message = str(e)

		return self.exe_result
