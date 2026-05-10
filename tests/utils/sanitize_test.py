from tests.check import TestResult
from utils.sanitize import sanitize


def suite():
	t = TestResult()

	t.check(sanitize("hello") == "hello", "ascii passes through")
	t.check(sanitize("") == "", "empty string unchanged")
	t.check(sanitize("中文测试") == "中文测试", "chinese passes through")
	t.check(sanitize("hello\ud800world") == "helloworld", "lone surrogate removed")
	t.check(sanitize("a\ud83d\ude00b") == "ab", "surrogate pair chars removed")
	t.check(sanitize(" \ud800 ") == "  ", "surrogate with surrounding spaces")
	t.check(sanitize("✅") == "✅", "emoji passes through")

	return t.summary("utils.sanitize")
