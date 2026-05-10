import json
import os
import re
from datetime import datetime

from agent import BaseLLM
from agent.llm import LLMResponse, ToolCall
from tools import ToolRegistry
from tools import ToolExecutionResult
from utils import Logger, sanitize
import sys


HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history")


class Agent:
	def __init__(self, llm_client: BaseLLM, tool_registry: ToolRegistry, system_prompt: str):
		self.llm = llm_client
		self.tools = tool_registry
		self.system_prompt = system_prompt

		# Message layers: system | summary | skills | conversation
		self.system_layer = [{"role": "system", "content": system_prompt}]
		self.summary_layer = []
		self.skills_layer = []
		self.conversation = []

		# Session tracking
		self._session_path = None

		# Token stats
		self.tokens_info = {
			"prompt_tokens": 0,
			"completion_tokens": 0,
			"total_tokens": 0,
			"prompt_cache_hit_tokens": 0,
			"prompt_cache_miss_tokens": 0,
		}

		# Loggers
		self.log_model = Logger(default_color='cyan', default_style='bold', show_time=False)
		self.log_tokens = Logger(default_color='black', default_style='dim', show_time=False)
		self.log_reasoning = Logger(default_color='yellow', default_style='normal', show_time=False)
		self.log_content = Logger(default_color='green', default_style='bold', show_time=False)
		self.log_tool = Logger(default_color='magenta', default_style='bold', show_time=False)
		self.log_input = Logger(default_color='blue', default_style='bold', show_time=False)
		self.log_executor = Logger(default_color='yellow', default_style='normal', show_time=False)

		# Context engineering state
		self._has_todo = None
		self._rounds_since_todo_update = 0
		self._first_user_input = ""

	# ---- helpers ----

	@property
	def _messages(self):
		"""Assemble all layers into a single message list for the LLM."""
		return self.system_layer + self.summary_layer + self.skills_layer + self.conversation

	@staticmethod
	def _clean_surrogates(obj):
		if isinstance(obj, str):
			return re.sub(r"[\uD800-\uDFFF]", "\ufffd", obj)
		elif isinstance(obj, list):
			return [Agent._clean_surrogates(item) for item in obj]
		elif isinstance(obj, dict):
			return {k: Agent._clean_surrogates(v) for k, v in obj.items()}
		return obj

	# ---- token tracking ----

	def __token_info_update(self, usage: dict):
		for key in usage:
			if key in self.tokens_info:
				self.tokens_info[key] += usage[key]

	# ---- display ----

	def __resp_info_show(self, resp: LLMResponse):
		self.log_model.log(
			f"Model: {resp.model or 'Unknown'} | Finish: {resp.finish_reason}",
			prefix="[模型响应]"
		)

		if self.tokens_info["total_tokens"] > 0:
			t = self.tokens_info
			msg = (
				f"Total: {t['total_tokens']} "
				f"(Prompt: {t['prompt_tokens']}, "
				f"Completion: {t['completion_tokens']}, "
				f"CacheHit: {t['prompt_cache_hit_tokens']}, "
				f"CacheMiss: {t['prompt_cache_miss_tokens']})"
			)
			self.log_tokens.log(msg, prefix="[Tokens]", color='white')

		reasoning = resp.raw_message.get('reasoning_content')
		if reasoning:
			self.log_reasoning.log("[深度思考] (Reasoning):", style='bold', prefix="")
			self.log_reasoning.log(reasoning)

		if resp.content:
			self.log_content.log("[最终回复] (Content):", prefix="")
			self.log_content.log(resp.content, color='green', style='normal')

		if resp.has_tool_calls:
			self.log_tool.log("[工具调用] (Tool Calls):", prefix="")
			for tool in resp.tool_calls:
				self.log_tool.log(f"- {tool.name}: {tool.arguments}", style='normal')
		print("-" * 50)

	def __exe_result_info_show(self, result: ToolExecutionResult):
		name = result.tool_name
		status = result.status
		params = result.parameters
		data = result.result
		error_msg = result.error_message

		is_success = status == 'success'
		header_color = 'green' if is_success else 'red'
		status_icon = '✅' if is_success else '❌'

		self.log_executor.log(
			f"{status_icon} {name}",
			color=header_color,
			style='bold',
			prefix="[工具响应]"
		)
		print("-" * 50)
		self.log_executor.log("⚙️ 调用参数:", color='blue', style='bold')
		if isinstance(params, (dict, list)):
			print(json.dumps(params, indent=2, ensure_ascii=False))
		else:
			print(params)

		if is_success:
			self.log_executor.log("📝 执行结果:", color='green', style='bold')
			if isinstance(data, (dict, list)):
				print(json.dumps(data, indent=2, ensure_ascii=False))
			else:
				print(data)
		else:
			self.log_executor.log("⚠️ 错误详情:", color='red', style='bold')
			error_content = error_msg if error_msg else str(data)
			print(error_content)
		print("-" * 50)

	# ---- context engineering ----

	def __context_engineering(self):
		if self._has_todo is None:
			self._has_todo = "todo" in self.tools.list_tools()
		if not self._has_todo:
			return

		if self._rounds_since_todo_update >= 3:
			self.conversation.append({
				"role": "user",
				"content": "[Reminder] You have not updated the todo list for several rounds. Please use the todo tool to review and update task status."
			})
			self._rounds_since_todo_update = 0

	def _is_todo_update(self, tool_call: ToolCall) -> bool:
		if tool_call.name != "todo":
			return False
		return tool_call.arguments.get("action") == "update"

	# ---- skill injection ----

	def _inject_skill(self, name: str, content: str):
		self.skills_layer.append({
			"role": "system",
			"content": f"[Loaded skill: {name}]\n{content}"
		})

	# ---- session persistence ----

	def _save_session(self):
		os.makedirs(HISTORY_DIR, exist_ok=True)

		data = {
			"system_prompt": self.system_prompt,
			"summary": self.summary_layer[0]["content"] if self.summary_layer else "",
			"skills": [m["content"] for m in self.skills_layer],
			"conversation": self._clean_surrogates(self.conversation),
		}

		if self._session_path:
			path = self._session_path
		else:
			prefix = self._first_user_input[:8] if self._first_user_input else "empty"
			safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in prefix)
			ts = datetime.now().strftime("%Y%m%d_%H%M%S")
			name = f"{safe}_{ts}.json"
			path = os.path.join(HISTORY_DIR, name)

		json_str = json.dumps(data, ensure_ascii=True, indent=2)
		with open(path, "w", encoding="utf-8") as f:
			f.write(json_str)
		self.log_input.log(f"Session saved: {os.path.basename(path)}", color="green")

	def _load_session(self, name: str) -> bool:
		path = os.path.join(HISTORY_DIR, name)
		if not os.path.isfile(path):
			self.log_input.log(f"Session file not found: {name}", color="red")
			return False
		try:
			with open(path, "r", encoding="utf-8") as f:
				data = json.load(f)

			self.system_prompt = data.get("system_prompt", self.system_prompt)
			self.system_layer = [{"role": "system", "content": self.system_prompt}]

			summary = data.get("summary", "")
			self.summary_layer = [{"role": "system", "content": f"[Session Summary]\n{summary}"}] if summary else []

			self.skills_layer = [{"role": "system", "content": s} for s in data.get("skills", [])]
			self.conversation = data.get("conversation", [])

			self._session_path = path
			self._has_todo = None
			self._rounds_since_todo_update = 0

			for msg in self.conversation:
				if msg.get("role") == "user":
					self._first_user_input = msg["content"]
					break

			self.log_input.log(f"Session loaded: {name} ({len(self.conversation)} messages)", color="green")
			return True
		except Exception as e:
			self.log_input.log(f"Load failed: {e}", color="red")
			return False

	def _list_history(self) -> list[str]:
		os.makedirs(HISTORY_DIR, exist_ok=True)
		return sorted(os.listdir(HISTORY_DIR))

	def _load_prompt(self, path: str):
		if not os.path.isfile(path):
			self.log_input.log(f"Prompt file not found: {path}", color="red")
			return
		with open(path, "r", encoding="utf-8") as f:
			self.system_prompt = f.read()
		if self.system_layer:
			self.system_layer[0]["content"] = self.system_prompt
		else:
			self.system_layer.append({"role": "system", "content": self.system_prompt})
		self.log_input.log(f"Prompt loaded: {path}", color="green")

	# ---- main processing ----

	def _process(self, user_input: str):
		self.conversation = self._clean_surrogates(self.conversation)
		self.conversation.append({"role": "user", "content": sanitize(user_input)})
		self._rounds_since_todo_update += 1

		while True:
			self.__context_engineering()

			resp = self.llm.chat(self._messages, tools=self.tools.get_schemas())
			self.__token_info_update(resp.usage)
			self.__resp_info_show(resp=resp)

			if resp.finish_reason == "length":
				self.conversation.append({
					"role": "user",
					"content": "Your previous response was cut off. You can split the output into several conversations.",
				})
				continue

			if resp.finish_reason == "error":
				break

			self.conversation.append(resp.raw_message)

			if resp.has_tool_calls:
				for tool_call in resp.tool_calls:
					if self._is_todo_update(tool_call):
						self._rounds_since_todo_update = 0

					tool_result = self.tools.execute(tool_call.name, tool_call.arguments)
					self.__exe_result_info_show(tool_result)

					self.conversation.append({
						"role": "tool",
						"tool_call_id": tool_call.id,
						"content": tool_result.result_to_str,
					})

					if tool_call.name == "load_skill" and tool_call.arguments.get("action") == "load" and tool_result.status == "success":
						self._inject_skill(tool_call.arguments.get("name"), tool_result.result)

					if tool_call.name == "compress_context" and tool_result.status == "success":
						self.summary_layer = [{"role": "system", "content": f"[Session Summary]\n{tool_result.result}"}]
						self.conversation = []

			elif resp.finish_reason == "stop":
				break

	def _get_user_input(self) -> str:
		try:
			raw_input = input("\n👤 \033[1;34mUser\033[0m => ")
			cleaned_input = sanitize(raw_input.strip())
			if not cleaned_input:
				return ""
			return cleaned_input
		except (KeyboardInterrupt, EOFError):
			print("\n")
			self.log_input.log("👋 Goodbye!", color='yellow')
			sys.exit(0)

	def run(self):
		self.log_input.log("Agent ready. Commands: /exit /save /load /history /prompt /tools", color='green')

		while True:
			user_input = self._get_user_input()
			if not user_input:
				continue

			if user_input == "/exit":
				self._save_session()
				self.log_input.log("Exiting...", color='yellow')
				break

			elif user_input == "/tools":
				print("\n \033[1;35mTools:\033[0m")
				print(self.tools.list_tools())
				print("-" * 50)
				continue

			elif user_input == "/save":
				self._save_session()
				continue

			elif user_input == "/history":
				files = self._list_history()
				if not files:
					self.log_input.log("No saved sessions.", color='yellow')
				else:
					print("\n \033[1;35mSaved sessions:\033[0m")
					for f in files:
						print(f"  {f}")
					print("-" * 50)
				continue

			elif user_input.startswith("/load"):
				name = user_input[6:].strip() if len(user_input) > 6 else ""
				if not name:
					self.log_input.log("Usage: /load <filename>", color='yellow')
					self.log_input.log("Use /history to list saved sessions.", color='yellow')
					continue
				self._load_session(name)
				continue

			elif user_input.startswith("/prompt"):
				path = user_input[8:].strip() if len(user_input) > 8 else ""
				if not path:
					self.log_input.log("Usage: /prompt <filepath>", color='yellow')
					continue
				self._load_prompt(path)
				continue

			elif user_input.startswith("/"):
				self.log_input.log(f"Unknown command: {user_input}", color='red')
				self.log_input.log("Available: /exit /save /load /history /prompt /tools", color='yellow')
				continue

			else:
				if not self._first_user_input:
					self._first_user_input = user_input
				self._process(user_input)
