#!/usr/bin/env python3
"""
Test runner for AgentForge.

Discovers all *_test.py files under tests/, calls their suite() function,
and reports results. Returns exit code 0 if all tests pass, 1 otherwise.
"""

import os
import sys
import importlib.util


def discover_tests(root):
	"""Yield (module_path, module_name) for every *_test.py under root."""
	for dirpath, dirnames, filenames in os.walk(root):
		rel = os.path.relpath(dirpath, root)
		if rel == ".":
			rel = ""
		for f in filenames:
			if f.endswith("_test.py"):
				mod_name = f[:-3]
				full_path = os.path.join(dirpath, f)
				yield full_path, mod_name


def load_suite(path):
	"""Import a test module and call its suite(), return (passed, total)."""
	module_name = os.path.splitext(os.path.basename(path))[0]
	spec = importlib.util.spec_from_file_location(module_name, path)
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod.suite()


def main():
	root = os.path.dirname(os.path.abspath(__file__))
	sys.path.insert(0, os.path.dirname(root))

	total_passed = 0
	total_failed = 0
	failures = []

	print("=" * 50)
	print("  AgentForge Test Suite")
	print("=" * 50)
	print()

	for path, name in discover_tests(root):
		print(f"\n\u2501\u2501\u2501 [{name}] \u2501\u2501\u2501")
		try:
			ok = load_suite(path)
			if ok:
				total_passed += 1
			else:
				total_failed += 1
				failures.append(name)
		except Exception as e:
			total_failed += 1
			failures.append(name)
			print(f"  \u274c SUITE ERROR: {e}")

	print("=" * 50)
	if failures:
		print(f"Failed suites: {', '.join(failures)}")
		print(f"Result: {total_passed} passed, {total_failed} FAILED")
		sys.exit(1)
	else:
		print(f"Result: {total_passed} all passed \u2705")
		sys.exit(0)


if __name__ == "__main__":
	main()
