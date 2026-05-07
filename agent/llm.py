# ===========
# LLM 封装层
# ===========

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Optional
import json
import requests


@dataclass
class ToolCall:
	id: str
	name: str
	arguments: dict[str, object] = field(default_factory=dict)

	def __str__(self):
		args_str = json.dumps(self.arguments, ensure_ascii=False)
		return f"ToolCall(name={self.name}, args={args_str})"


@dataclass
class LLMResponse:
	content: Optional[str] = None
	tool_calls: Optional[list[ToolCall]] = None
	finish_reason: str = "stop"
	usage: dict = field(default_factory=dict)
	model: str = ""
	raw_message: dict = field(default_factory=dict)

	@property
	def has_tool_calls(self) -> bool:
		return bool(self.tool_calls)


class BaseLLM(ABC):
	@abstractmethod
	def chat(self, messages: list, tools: Optional[list] = None) -> LLMResponse:
		pass



class OpenAICompatibleLLM(BaseLLM):
	def __init__(self, model: str, api_key: str, base_url: str,
				 temperature=0.7, max_tokens=4096):
		self.model = model
		self.api_key = api_key
		self.base_url = base_url.rstrip("/")
		self.temperature = temperature
		self.max_tokens = max_tokens
		self.type = "openai"

	def __str__(self):
		return f"LLM Model: {self.model}\nType: {self.type}\n"

	def resp_data_process(self, resp: dict) -> LLMResponse:
		resp_message = resp["choices"][0]["message"]
		content = resp_message.get("content")
		usage = resp.get("usage", {})
		raw_tool_calls = resp_message.get("tool_calls", [])
		parsed_tool_calls = []

		if raw_tool_calls:
			for tc in raw_tool_calls:
				call_id = tc["id"]
				func_info = tc["function"]
				name = func_info["name"]
				args_str = func_info["arguments"]
				try:
					arguments = json.loads(args_str)
				except json.JSONDecodeError:
					arguments = {}
				parsed_tool_calls.append(ToolCall(id=call_id, name=name, arguments=arguments))

		return LLMResponse(
			content=content,
			tool_calls=parsed_tool_calls if parsed_tool_calls else None,
			finish_reason=resp["choices"][0]["finish_reason"],
			usage=usage,
			raw_message=resp_message,
		)

	def chat(self, messages: list, tools: Optional[list] = None) -> LLMResponse:
		payload = {
			"model": self.model,
			"messages": messages,
			"temperature": self.temperature,
			"max_tokens": self.max_tokens,
		}
		if tools:
			payload["tools"] = tools

		resp = requests.post(
			f"{self.base_url}/v1/chat/completions",
			headers={
				"Authorization": f"Bearer {self.api_key}",
				"Content-Type": "application/json",
			},
			json=payload,
			timeout=60,
		)
		resp.raise_for_status()
		return self.resp_data_process(resp.json())


class LLMFactory:
	@staticmethod
	def create(path: str = "config/llm_config.json") -> BaseLLM:
		with open(path, 'r', encoding='utf-8') as f:
			config = json.load(f)
		llm_cfg = config["llm"]
		if llm_cfg["type"] == "openai":
			return OpenAICompatibleLLM(
				model=llm_cfg["model"],
				api_key=llm_cfg["api_key"],
				base_url=llm_cfg["base_url"],
				temperature=llm_cfg.get("temperature", 0.7),
				max_tokens=llm_cfg.get("max_tokens", 4096),
			)
		else:
			raise ValueError(f"Unsupported LLM type: {llm_cfg['type']}")
