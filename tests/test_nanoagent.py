"""Offline task-runner integration tests for environments with NanoAgent installed."""

import json
from pathlib import Path

import pytest
from test_tasks import QUESTION_MARKS, REPORT_PATH, STUDENT, report_for


@pytest.mark.anyio
@pytest.mark.parametrize("scenario", ["submitted", "missing-submit", "unavailable-tool"])
async def test_nanoagent_runs_scripted_model(tmp_path, monkeypatch, scenario):
    pytest.importorskip("nanoagent", reason="Install NanoAgent to run the host integration tests")
    from nanoagent.core.agent import Agent, Reply, ToolCall
    from nanoagent.plugin import runtime
    from nanoagent.plugin.manifest import load_manifest
    from nanoagent.plugin.tasks import run_task

    root = Path(__file__).resolve().parents[1]
    # Exercise the manifest's real launch command using the synced environment.
    plugin_env = runtime.plugin_env

    def offline_env(manifest, workspace):
        return {**plugin_env(manifest, workspace), "UV_OFFLINE": "1", "UV_NO_SYNC": "1", "UV_NO_CACHE": "1"}

    monkeypatch.setattr(runtime, "plugin_env", offline_env)
    manifest = load_manifest(root)
    task = manifest.task("grade-question")
    selection = {"student_name": STUDENT, "question_number": 20}
    report = report_for(QUESTION_MARKS, 0)
    submission = {"path": REPORT_PATH, "report": report}
    calls = [
        ("get_responses", selection),
        ("get_answer_key", {"question_number": 20}),
        ("save_report", {"selection": selection, "report": report}),
    ]
    if scenario == "submitted":
        calls.append(("submit", submission))
    elif scenario == "unavailable-tool":
        calls = [("pin_question_grade", selection), ("get_responses", selection)]

    # A mixed batch lets the agent surface the refused call alongside the allowed result.
    turns = iter([calls] if scenario == "unavailable-tool" else [[call] for call in calls])

    class ScriptedModel:
        async def query(self, messages, tools, **kwargs):
            assert {tool["function"]["name"] for tool in tools} == {
                "get_responses",
                "get_answer_key",
                "get_question",
                "save_report",
                "submit",
            }
            turn = next(turns, None)
            if turn is None:
                return Reply(content="Done.")
            return Reply(
                content=None,
                tool_calls=[ToolCall(f"call-{name}", name, json.dumps(arguments)) for name, arguments in turn],
            )

    events = []

    async def run():
        return await run_task(
            manifest,
            task,
            selection,
            tmp_path,
            make_agent=lambda system: Agent(ScriptedModel(), [], system_prompt=system, max_steps=len(calls) + 1),
            make_decider=None,
            timeout=10,
            on_event=lambda kind, data: events.append((kind, data)),
            stage=lambda folder: None,
        )

    if scenario == "submitted":
        outcome = await run()
        assert outcome.reference == report
        assert outcome.output == submission
        assert outcome.verdict.valid and outcome.verdict.score == 1.0, outcome.verdict.message
    else:
        with pytest.raises(RuntimeError, match="without calling submit"):
            await run()

    tool_events = [data for kind, data in events if kind == "task.tool"]
    assert [event["name"] for event in tool_events] == [name for name, _ in calls]
    if scenario == "unavailable-tool":
        refused, allowed = tool_events
        assert refused["isError"] and "unknown tool" in refused["output"]
        assert not allowed["isError"]
        assert not (tmp_path / REPORT_PATH).exists()
    else:
        assert not any(event["isError"] for event in tool_events)
        assert json.loads((tmp_path / REPORT_PATH).read_text(encoding="utf-8")) == report
