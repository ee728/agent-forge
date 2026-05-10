"""
错误重试机制
=============

为什么需要重试？
1. LLM API 可能暂时不可用（503）或超时
2. PLC 的 SSH 连接可能因网络波动断开
3. 串口通信可能因为干扰丢包
4. 这些都是临时性故障，重试往往就能解决

策略：指数退避 + 抖动 (Exponential Backoff + Jitter)

指数退避：
  第一次失败后等 1s，第二次 2s，第三次 4s，第四次 8s...
  公式: delay = base_delay * (2 ^ attempt)

抖动 (Jitter)：
  在退避时间上加入随机性，避免多个客户端同时重试造成"雪崩"
  公式: delay = delay * (0.5 + random() * 0.5)  ← 乘 0.5~1.0 之间的随机数

最大延迟上限：
  delay = min(delay, max_delay)
"""

import time
import random
from functools import wraps


def retry(max_retries: int = 3, base_delay: float = 1.0,
		  max_delay: float = 60.0, exceptions: tuple = (Exception,)):
	"""
	重试装饰器，带指数退避和抖动。

	用法:
		@retry(max_retries=3, base_delay=1.0)
		def ssh_connect():
			...

	参数:
		max_retries: 最大重试次数（不包括首次）
		base_delay: 初始等待时间（秒），每次翻倍
		max_delay: 最大等待时间（秒）
		exceptions: 哪些异常触发重试，默认所有异常

	实现要点:
	1. 捕获指定的异常
	2. 计算等待时间: delay = min(base_delay * (2 ^ attempt), max_delay)
	3. 加入抖动: delay = delay * (0.5 + random() * 0.5)
	4. time.sleep(delay)
	5. 重试
	6. 如果达到 max_retries 仍然失败，抛出最后一次的异常

	TODO: 实现重试装饰器

	扩展思考:
	- 是否要记录每次重试的日志？
	- 是否区分"可重试"和"不可重试"的异常？
	  比如 401 认证失败不应该重试，但 503 服务不可用应该重试
	"""
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			pass  # TODO
		return wrapper
	return decorator


class RetryHandler:
	"""
	面向对象的重试处理器，适合需要在循环中手动控制重试的场景。

	相比装饰器，这种方式的优势是：
	- 可以在重试间执行清理操作（如关闭旧连接）
	- 可以记录更详细的错误信息
	- 更灵活的控制流程

	用法:
		handler = RetryHandler(max_retries=3)
		while handler.should_retry():
			try:
				result = ssh_connect()
				handler.on_success()
				break
			except Exception as e:
				handler.on_failure(e)
				if handler.should_retry():
					handler.wait()
				else:
					raise
	"""

	def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
				 max_delay: float = 60.0):
		self.max_retries = max_retries
		self.base_delay = base_delay
		self.max_delay = max_delay
		self.attempt = 0
		self.last_exception = None

	def should_retry(self) -> bool:
		"""是否应该继续重试？"""
		pass

	def on_failure(self, exception: Exception):
		"""记录失败信息"""
		pass

	def on_success(self):
		"""重置状态（成功无需重试）"""
		pass

	def wait(self):
		"""
		计算等待时间并休眠。

		公式:
			delay = min(base_delay * (2 ^ attempt), max_delay)
			jitter = delay * (0.5 + random() * 0.5)
			time.sleep(jitter)
		"""
		pass
