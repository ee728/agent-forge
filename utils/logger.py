"""
日志系统
=========

日志的作用：
1. 记录 Agent 的思考过程和决策路径（方便调试）
2. 记录所有工具调用和结果（审计追踪）
3. 记录错误和异常（问题排查）
4. 最终可以导出为测试报告

设计要点：
- 分级别：DEBUG / INFO / WARNING / ERROR
- 支持同时输出到控制台和文件
- 给 LLM 的 messages 增加可读性（人也能看懂）
- 日志文件按大小或日期滚动
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

class Logger:
	"""
	一个轻量级的控制台日志打印类，支持颜色和样式自定义。
	"""

	# --- 颜色定义 (ANSI 转义码) ---
	COLORS = {
		'black':   '\033[30m',
		'red':     '\033[31m',
		'green':   '\033[32m',
		'yellow':  '\033[33m',
		'blue':    '\033[34m',
		'magenta': '\033[35m',
		'cyan':    '\033[36m',
		'white':   '\033[37m',
		'reset':   '\033[0m'
	}

	# --- 样式/大小定义 ---
	STYLES = {
		'normal':  '',
		'bold':    '\033[1m',      # 加粗/大号字体
		'dim':     '\033[2m',      # 变暗
		'underline': '\033[4m',    # 下划线
		'blink':   '\033[5m',      # 闪烁
		'reverse': '\033[7m'       # 反显
	}

	# --- 背景色定义 ---
	BACKGROUNDS = {
		'black':   '\033[40m',
		'red':     '\033[41m',
		'green':   '\033[42m',
		'yellow':  '\033[43m',
		'blue':    '\033[44m',
		'magenta': '\033[45m',
		'cyan':    '\033[46m',
		'white':   '\033[47m'
	}

	def __init__(self, default_color='white', default_style='normal', show_time=True):
		"""
		初始化 Logger
		:param default_color: 默认文字颜色
		:param default_style: 默认样式
		:param show_time: 是否自动显示时间戳
		"""
		self.default_color = default_color
		self.default_style = default_style
		self.show_time = show_time

	def _get_code(self, color=None, style=None, bg=None):
		"""内部方法：拼接 ANSI 代码"""
		c = self.COLORS.get(color, self.COLORS[self.default_color])
		s = self.STYLES.get(style, self.STYLES[self.default_style])
		b = self.BACKGROUNDS.get(bg, '') if bg else ''
		
		return f"{s}{b}{c}"

	def log(self, message, color=None, style=None, bg=None, prefix=None, end='\n',to_shell=True)->str:
		"""
		核心打印方法
		:param message: 消息内容
		:param color: 文字颜色 (如 'red', 'green')
		:param style: 样式 (如 'bold', 'underline')
		:param bg: 背景颜色
		:param prefix: 前缀标签 (如 '[INFO]')
		:param end: 结尾字符
		"""
		# 处理时间戳
		timestamp = f"[{datetime.now().strftime('%H:%M:%S')}] " if self.show_time else ""
		
		# 处理前缀
		pf = f"{prefix} " if prefix else ""
		
		# 获取颜色样式代码
		code = self._get_code(color, style, bg)
		reset = self.COLORS['reset']
		
		# 组合输出
		output = f"{timestamp}{code}{pf}{message}{reset}"
		if to_shell:
			print(output, end=end)
		return output

	# --- 快捷方法 (语法糖) ---
	def info(self, msg):
		self.log(msg, color='cyan', style='bold', prefix='[INFO]')

	def success(self, msg):
		self.log(msg, color='green', style='bold', prefix='[SUCCESS]')

	def warning(self, msg):
		self.log(msg, color='yellow', style='bold', prefix='[WARNING]')

	def error(self, msg):
		self.log(msg, color='red', style='bold', prefix='[ERROR]')
		
	def debug(self, msg):
		self.log(msg, color='magenta', style='dim', prefix='[DEBUG]')


