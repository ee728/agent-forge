import json

from agent import BaseLLM
from agent.llm import LLMResponse, ToolCall
from tools import ToolRegistry
from tools import ToolExecutionResult
from utils import Logger
import sys


class Agent:
	def __init__(self, llm_client: BaseLLM, tool_registry: ToolRegistry, system_prompt: str):
		self.llm = llm_client
		self.tools = tool_registry
		self.messages = []
		self.system_prompt = system_prompt

		# tokens统计信息
		self.tokens_info = {
			"prompt_tokens":0,
			"completion_tokens":0,
			"total_tokens":0,
			"prompt_cache_hit_tokens":0,
			"prompt_cache_miss_tokens":0
		}

		# 输出信息配置
		self.log_model = Logger(default_color='cyan', default_style='bold', show_time=False) 
		self.log_tokens = Logger(default_color='black', default_style='dim', show_time=False)
		self.log_reasoning = Logger(default_color='yellow', default_style='normal', show_time=False)  
		self.log_content = Logger(default_color='green', default_style='bold', show_time=False)
		self.log_tool = Logger(default_color='magenta', default_style='bold', show_time=False)
		self.log_input = Logger(default_color='blue', default_style='bold', show_time=False)
		self.log_executor = Logger(default_color='yellow', default_style='normal', show_time=False)

		# 上下文工程状态
		self._has_todo = None
		self._rounds_since_todo_update = 0

	def __token_info_update(self,usage:dict):
		for info in usage.keys():
			if info not in self.tokens_info:
				continue
			self.tokens_info[info] = self.tokens_info.get(info,0) + usage.get(info,0)

	def __resp_info_show(self, resp: LLMResponse):

		self.log_model.log(
			f"Model: {resp.model or 'Unknown'} | Finish: {resp.finish_reason}", 
			prefix="[模型响应]"
		)

		if resp.usage:
			total = resp.usage.get('total_tokens', 0)
			prompt = resp.usage.get('prompt_tokens', 0)
			completion = resp.usage.get('completion_tokens', 0)
			prompt_cache_hit_tokens = resp.usage.get('prompt_cache_hit_tokens', 0)
			prompt_cache_miss_tokens = resp.usage.get('prompt_cache_miss_tokens', 0)
			msg = f"Total: {total} (Prompt: {prompt}, Completion: {completion}, CacheHit: {prompt_cache_hit_tokens}, CacheMiss: {prompt_cache_miss_tokens})"
			self.log_tokens.log(msg, prefix="[Tokens]", color='white') # 临时设为白色以便看清数字

		reasoning = resp.raw_message.get('reasoning_content')
		if reasoning:
			self.log_reasoning.log("[深度思考] (Reasoning):", style='bold', prefix="") # 标题加粗
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
        
		print("-" * 50) # 分割线

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

	def __context_engineering(self,resp=LLMResponse):
		if self._has_todo is None:
			self._has_todo = "todo" in self.tools.list_tools()
		if not self._has_todo:
			return

		if self._rounds_since_todo_update >= 3:
			last = self.messages[-1]
			reminder = "[Reminder] 你已有多轮对话没有更新 todo 任务进度了，请使用 todo 工具查看并更新状态。\n"
			if isinstance(last.get("content"), str):
				last["content"] = reminder + last["content"]
			self._rounds_since_todo_update = 0

	def _is_todo_update(self, tool_call:ToolCall) -> bool:
		if tool_call.name != "todo":
			return False
		return tool_call.arguments.get("action") == "update"

	def _inject_skill(self, name: str, content: str):
		for msg in self.messages:
			if msg["role"] == "system":
				msg["content"] += f"\n\n[Loaded skill: {name}]\n" + content
				break

	def _process(self, user_input: str):
		self.messages.append({"role": "user", "content": user_input})
		self._rounds_since_todo_update += 1

		while True:
			self.__context_engineering()

			resp = self.llm.chat(self.messages, tools=self.tools.get_schemas())
			self.__token_info_update(resp.usage)
			self.__resp_info_show(resp=resp)

			if resp.finish_reason == "length":
				self.messages.append({
					"role": "user",
					"content": "Your previous response was cut off. You can split the output into several conversations.",
				})
				continue

			self.messages.append(resp.raw_message)

			if resp.has_tool_calls:
				for tool_call in resp.tool_calls:
					if self._is_todo_update(tool_call):
						self._rounds_since_todo_update = 0

					tool_result = self.tools.execute(tool_call.name, tool_call.arguments)
					self.__exe_result_info_show(tool_result)

					self.messages.append({
						"role": "tool",
						"tool_call_id": tool_call.id,
						"content": tool_result.result_to_str,
					})

					if tool_call.name == "load_skill" and tool_call.arguments.get("action") == "load" and tool_result.status == "success":
						self._inject_skill(tool_call.arguments.get("name"), tool_result.result)

			elif resp.finish_reason == "stop":
				break

	def _get_user_input(self) -> str:
		try:
			raw_input = input("\n👤 \033[1;34mUser\033[0m => ")
			cleaned_input = raw_input.strip()
			if not cleaned_input:
				return "" 
			return cleaned_input
		except (KeyboardInterrupt, EOFError):
			print("\n")
			self.log_input.log("👋 再见！", color='yellow')
			sys.exit(0)

	def __history_save(self):
		pass

	def run(self):
		# 初始化系统提示词（注意：通常 system prompt 只在会话开始时添加一次，或者作为上下文常量）
		# 如果这是长对话 Agent，建议不要把 system prompt 每次都 append 到 messages 里，否则会重复计费
		self.messages.append({"role": "system", "content": self.system_prompt})
		

		self.log_input.log("🚀 Agent 已就绪，请输入指令 (输入 /exit 退出)", color='green')
        
		while True:
			# --- 使用封装好的输入函数 ---
			user_input = self._get_user_input()

			# 空输入处理（用户只按了回车）
			if not user_input:
				continue
                
			# 指令处理
			if user_input == "/exit":
				self.log_input.log("👋 正在退出...", color='yellow')
				break
			elif user_input == "/tools":
				print("\n🛠️ \033[1;35m可用工具列表:\033[0m")
				print(self.tools.list_tools())
				print("-" * 50)
				continue
			else:
				# 正常业务逻辑
				self._process(user_input)
