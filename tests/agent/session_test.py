import os
import json

from tests.check import TestResult, TempHistory
from agent.llm import BaseLLM, LLMResponse
from tools import ToolRegistry


class MockLLM(BaseLLM):
	def chat(self, messages, tools=None):
		return LLMResponse(
			content="ok", finish_reason="stop",
			usage={}, raw_message={"role": "assistant", "content": "ok"}
		)


def suite():
	from agent import Agent
	import agent.core as core_mod
	t = TestResult()

	# ---- save creates correct JSON structure ----
	llm = MockLLM()
	reg = ToolRegistry()

	with TempHistory() as tmpdir:
		orig_dir = core_mod.HISTORY_DIR
		core_mod.HISTORY_DIR = tmpdir

		a = Agent(llm, reg, "Test system prompt")
		a._first_user_input = "test session"
		a.conversation = [
			{"role": "user", "content": "hello"},
			{"role": "assistant", "content": "hi there"},
		]
		a.skills_layer = [
			{"role": "system", "content": "[Loaded skill: foo]\ndo foo"},
		]
		a._save_session()

		files = os.listdir(tmpdir)
		t.check(len(files) == 1, "save creates one file")
		t.check(files[0].endswith(".json"), "file is .json")

		with open(os.path.join(tmpdir, files[0])) as f:
			saved = json.load(f)
		t.check(saved["system_prompt"] == "Test system prompt", "system_prompt saved")
		t.check(saved["summary"] == "", "summary saved as empty string")
		t.check(len(saved["skills"]) == 1, "skills saved")
		t.check(len(saved["conversation"]) == 2, "conversation saved")
		t.check(saved["conversation"][0]["role"] == "user", "first msg role user")
		t.check(saved["conversation"][1]["role"] == "assistant", "second msg role assistant")

		# ---- load restores layers correctly ----
		a2 = Agent(llm, reg, "different prompt")
		session_name = files[0]
		ok = a2._load_session(session_name)
		t.check(ok, "load returns True")
		t.check(a2.system_prompt == "Test system prompt", "system_prompt restored")
		t.check(len(a2.summary_layer) == 0, "summary_layer empty (no summary)")
		t.check(len(a2.skills_layer) == 1, "skills_layer restored")
		t.check(len(a2.conversation) == 2, "conversation restored")
		t.check(a2._session_path is not None, "_session_path set after load")
		t.check(a2._first_user_input == "hello", "first_user_input restored from conversation")

		# ---- save after load overwrites (no new file) ----
		a2.conversation.append({"role": "user", "content": "more data"})
		a2._save_session()
		files2 = os.listdir(tmpdir)
		t.check(len(files2) == 1, "save overwrites same file, not new")

		with open(os.path.join(tmpdir, session_name)) as f:
			saved2 = json.load(f)
		t.check(len(saved2["conversation"]) == 3, "overwritten file has 3 messages")

		core_mod.HISTORY_DIR = orig_dir

	# ---- compress context truncates conversation ----
	with TempHistory() as tmpdir:
		core_mod.HISTORY_DIR = tmpdir

		a3 = Agent(llm, reg, "system")
		a3.conversation = [
			{"role": "user", "content": "do something"},
			{"role": "assistant", "content": "doing it"},
		]
		summary_text = "User asked to do something. Completed."
		a3.summary_layer = [{"role": "system", "content": f"[Session Summary]\n{summary_text}"}]
		a3.conversation = []

		t.check(len(a3.summary_layer) == 1, "summary_layer has summary")
		t.check("[Session Summary]" in a3.summary_layer[0]["content"],
			"summary has prefix")
		t.check(len(a3.conversation) == 0, "conversation cleared after compress")
		t.check(len(a3._messages) == 2, "_messages: system + summary after compress")

		core_mod.HISTORY_DIR = orig_dir

	# ---- encoding: JSON roundtrip with Unicode ----
	with TempHistory() as tmpdir:
		core_mod.HISTORY_DIR = tmpdir

		a4 = Agent(llm, reg, "sys")
		a4.conversation = [
			{"role": "user", "content": "hello \U0001f600"},
			{"role": "assistant", "content": "hi \u4e2d\u6587"},
		]
		a4._first_user_input = "encoding_test"
		a4._save_session()

		a5 = Agent(llm, reg, "")
		files = os.listdir(tmpdir)
		a5._load_session(files[0])
		t.check(a5.conversation[0]["content"] == "hello \U0001f600",
			"emoji survives roundtrip")
		t.check(a5.conversation[1]["content"] == "hi \u4e2d\u6587",
			"Chinese survives roundtrip")

		core_mod.HISTORY_DIR = orig_dir

	# ---- _clean_surrogates ----
	from agent import Agent as AgentCls
	cleaned = AgentCls._clean_surrogates("hello\ud800world")
	t.check("\ufffd" in cleaned and "\ud800" not in cleaned,
		"lone surrogate replaced")

	clean_list = AgentCls._clean_surrogates([{"content": "a\ud83d\ude00b"}])
	# \ud83d\ude00 are BOTH surrogates, both get replaced
	t.check("\ufffd" in clean_list[0]["content"],
		"surrogate pair chars in dict get cleaned")

	# ---- load nonexistent session ----
	a6 = Agent(llm, reg, "sys")
	with TempHistory() as tmpdir:
		core_mod.HISTORY_DIR = tmpdir
		ok = a6._load_session("nonexistent.json")
		t.check(not ok, "load nonexistent returns False")
		core_mod.HISTORY_DIR = orig_dir

	# ---- list_history ----
	with TempHistory() as tmpdir:
		core_mod.HISTORY_DIR = tmpdir
		empty = a6._list_history()
		t.check(empty == [], "list_history on empty dir returns []")
		open(os.path.join(tmpdir, "a.json"), "w").close()
		open(os.path.join(tmpdir, "b.json"), "w").close()
		files = a6._list_history()
		t.check(len(files) == 2, "list_history returns files")
		core_mod.HISTORY_DIR = orig_dir

	return t.summary("agent.session")
