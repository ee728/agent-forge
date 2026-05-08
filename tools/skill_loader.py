import os
import glob
from .base import BaseTool
from .base import ToolExecutionResult


SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")


class LoadSkillTool(BaseTool):
	name = "load_skill"
	description = "List available skills or load a skill for specialized task guidance"
	parameters = {
		"type": "object",
		"properties": {
			"action": {
				"type": "string",
				"enum": ["list", "load"],
				"description": "list: show all available skills | load: load a specific skill by name",
			},
			"name": {
				"type": "string",
				"description": "Skill name (from the name field in skill front matter). Required for 'load'.",
			},
		},
		"required": ["action"],
	}

	def _parse_front_matter(self, content: str) -> dict:
		meta = {"name": "", "description": ""}
		if content.startswith("---"):
			parts = content.split("---", 2)
			if len(parts) >= 3:
				for line in parts[1].strip().split("\n"):
					if ":" in line:
						key, val = line.split(":", 1)
						meta[key.strip()] = val.strip()
		return meta

	def _strip_front_matter(self, content: str) -> str:
		if content.startswith("---"):
			parts = content.split("---", 2)
			if len(parts) >= 3:
				return parts[2].strip()
		return content

	def _list_skills(self) -> str:
		files = glob.glob(os.path.join(SKILLS_DIR, "*.md"))
		if not files:
			return "No skills available."

		result = []
		for f in sorted(files):
			with open(f, "r", encoding="utf-8") as fh:
				content = fh.read()
			meta = self._parse_front_matter(content)
			name = meta.get("name") or os.path.splitext(os.path.basename(f))[0]
			desc = meta.get("description") or "No description"
			result.append(f"  - {name}: {desc}")

		return "Available skills:\n" + "\n".join(result)

	def _load_skill(self, name: str) -> str:
		files = glob.glob(os.path.join(SKILLS_DIR, "*.md"))
		for f in files:
			with open(f, "r", encoding="utf-8") as fh:
				content = fh.read()
			meta = self._parse_front_matter(content)
			skill_name = meta.get("name") or os.path.splitext(os.path.basename(f))[0]
			if skill_name == name:
				return self._strip_front_matter(content)
		return f"Error: skill '{name}' not found."

	def execute(self, arguments: dict) -> ToolExecutionResult:
		self.exe_result = ToolExecutionResult(None, None, None, None, None)
		self.exe_result.tool_name = self.name
		self.exe_result.parameters = arguments

		action = arguments.get("action")

		try:
			if action == "list":
				output = self._list_skills()

			elif action == "load":
				name = arguments.get("name")
				if not name:
					raise ValueError("load action requires 'name'")
				output = self._load_skill(name)

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
