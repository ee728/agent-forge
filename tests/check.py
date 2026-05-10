import os
import sys
import tempfile
import shutil


class TestResult:
	def __init__(self):
		self.passed = 0
		self.failed = 0
		self._failures = []

	def check(self, condition, name, detail=""):
		if condition:
			self.passed += 1
			print(f"  \u2705 {name}")
		else:
			self.failed += 1
			self._failures.append((name, detail))
			print(f"  \u274c {name}  {detail}")

	def summary(self, suite_name):
		print()
		print(f"{'=' * 40}")
		if self.failed:
			print(f"[{suite_name}] {self.passed} passed, {self.failed} FAILED")
			for name, detail in self._failures:
				print(f"  \u274c {name}")
			print()
			return False
		else:
			print(f"[{suite_name}] {self.passed} all passed \u2705")
			print()
			return True


class TempHistory:
	def __init__(self):
		self.tmpdir = tempfile.mkdtemp()

	def __enter__(self):
		return self.tmpdir

	def __exit__(self, *args):
		shutil.rmtree(self.tmpdir)
