import json
from copy import deepcopy
from pathlib import Path

import pytest
from slimconfig import build_output
from yaml import safe_load

from contract import TASKS, TOOLS, Task, Tool
from verifier import verify_output, verify_task

STUDENT = "Suy chakriya"
REPORT_PATH = "reports/grades.json"

# Fixed model output. Nothing here computes grades from tool results or imports the verifier's oracle.
EXAM_MARKS = [
    {"question_number": q, "response": response, "correct_answer": key, "points": int(points)}
    for q, (response, key, points) in enumerate(
        zip("DCBABBBDDDBCBCBCBCBC", "BCACBAACABBCBCBCBCBB", "01001000001111111110", strict=True),
        start=1,
    )
]
QUESTION_MARKS = [{"question_number": 20, "response": "C", "correct_answer": "B", "points": 0}]


def report_for(marks, score, student=STUDENT):
    return {
        "students": [{"name": student, "marks": marks, "score": score, "possible": len(marks)}],
        "total_score": score,
        "total_possible": len(marks),
    }


@pytest.fixture
def task_configs():
    manifest = Path(__file__).resolve().parents[1] / "nanoagent.yaml"
    return safe_load(manifest.read_text(encoding="utf-8"))[
        "tasks > dict[contract.Task, nanoagent.plugin.v0001.TaskConfig]"
    ]


@pytest.fixture
def replay_task(mcp_session, task_configs, tmp_path):
    async def replay(task, arguments, script):
        """Feed real tool responses back into a scripted model and verify its submission."""
        input_type, output_type = TASKS[task]
        given = build_output(arguments, input_type)
        config = task_configs[task.value]
        assert config["runner"] == "agent"
        reference_tool = Tool(config["reference"])
        reference_input, reference_output = TOOLS[reference_tool]
        assert reference_input is input_type
        assert reference_tool.value not in config["tools"]

        pinned = await mcp_session.call_tool(reference_tool.value, arguments)
        assert not pinned.isError, pinned.content
        reference = build_output(pinned.structuredContent, reference_output)
        assert verify_output(reference_tool, given, reference, tmp_path)["valid"]
        assert not (tmp_path / REPORT_PATH).exists()

        async def call(tool, payload):
            assert tool in config["tools"], f"{tool} is unavailable to {task.value}"
            result = await mcp_session.call_tool(tool, payload)
            assert not result.isError, result.content
            if tool == "save_report":
                assert result.structuredContent == {"path": REPORT_PATH, "report": payload["report"]}
            return result.structuredContent

        submission = await script(call)
        return verify_task(task, given, build_output(submission, output_type), reference, tmp_path)

    return replay


def fixed_script(calls, submission):
    async def script(call):
        for tool, arguments in calls:
            await call(tool, arguments)
        return submission

    return script


@pytest.mark.anyio
async def test_list_exam_task(mcp_session, task_configs, tmp_path):
    task = Task.LIST_EXAM
    input_type, output_type = TASKS[task]
    config = task_configs[task.value]
    assert config["runner"] == "tool"
    assert config["tools"] == [Tool.LIST_EXAM.value]
    assert config["reference"] is None
    assert TASKS[task] == TOOLS[Tool.LIST_EXAM]

    response = await mcp_session.call_tool(config["tools"][0], {})
    assert not response.isError, response.content
    output = build_output(response.structuredContent, output_type)
    arguments = build_output({}, input_type)
    assert verify_task(task, arguments, output, None, tmp_path)["valid"]
    assert not (tmp_path / REPORT_PATH).exists()

    output.student_names.pop()
    assert not verify_task(task, arguments, output, None, tmp_path)["valid"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "task,number,key_tool,key_args,report",
    [
        (Task.GRADE_EXAM, None, "get_document", {"document": "answerkey.txt"}, report_for(EXAM_MARKS, 11)),
        (Task.GRADE_QUESTION, 20, "get_answer_key", {"question_number": 20}, report_for(QUESTION_MARKS, 0)),
    ],
    ids=["full-exam", "single-question"],
)
async def test_scripted_grading_task(replay_task, tmp_path, task, number, key_tool, key_args, report):
    arguments = {"student_name": STUDENT}
    if number is not None:
        arguments["question_number"] = number
    selection = {"student_name": STUDENT, "question_number": number}
    calls = [
        ("get_responses", selection),
        (key_tool, key_args),
        ("save_report", {"selection": selection, "report": report}),
    ]
    submission = {"path": REPORT_PATH, "report": report}
    verdict = await replay_task(task, arguments, fixed_script(calls, submission))

    assert verdict["valid"] is True, verdict["message"]
    assert verdict["score"] == 1.0
    assert json.loads((tmp_path / REPORT_PATH).read_text(encoding="utf-8")) == report


@pytest.mark.anyio
@pytest.mark.parametrize(
    "scenario,reason",
    [
        ("skipped-save", "No such file"),
        ("wrong-grades", "Grades, coverage, ordering or totals differ"),
        ("saved-different-report", "Saved report differs"),
    ],
)
async def test_scripted_grading_rejects_invalid_outcomes(replay_task, tmp_path, scenario, reason):
    selection = {"student_name": STUDENT, "question_number": 20}
    report = report_for(QUESTION_MARKS, 0)
    wrong_marks = deepcopy(QUESTION_MARKS)
    wrong_marks[0]["points"] = 1
    wrong_report = report_for(wrong_marks, 1)

    calls = []
    if scenario != "skipped-save":
        calls.append(("save_report", {"selection": selection, "report": wrong_report}))

    submitted_report = wrong_report if scenario == "wrong-grades" else report
    submission = {"path": REPORT_PATH, "report": submitted_report}
    verdict = await replay_task(Task.GRADE_QUESTION, selection, fixed_script(calls, submission))

    assert verdict["valid"] is False
    assert verdict["score"] == 0.0
    assert reason in verdict["message"]
    if scenario != "skipped-save":
        assert json.loads((tmp_path / REPORT_PATH).read_text(encoding="utf-8")) == wrong_report


@pytest.mark.anyio
@pytest.mark.parametrize(
    "number,expected_response,expected_key,expected_points",
    [(17, "FALSE", "B", 1), (13, "", "B", 0)],
    ids=["written-option", "blank"],
)
async def test_scripted_grader_uses_tool_results(
    replay_task, tmp_path, number, expected_response, expected_key, expected_points
):
    student = "Synthetic Student 01"
    selection = {"student_name": student, "question_number": number}

    async def script(call):
        responses = await call("get_responses", selection)
        [response] = responses["responses"]
        question = {"question_number": response["question_number"]}
        key = (await call("get_answer_key", question))["correct_answer"]
        answer = response["response"]
        points = int(answer == key)
        if len(answer) > 1:
            statement = (await call("get_question", question))["statement"]
            option = next(
                line.removeprefix(f"{key}. ") for line in statement.splitlines() if line.startswith(f"{key}. ")
            )
            points = int(answer.casefold().split() == option.casefold().split())
        mark = {**response, "correct_answer": key, "points": points}
        return await call(
            "save_report", {"selection": selection, "report": report_for([mark], points, responses["name"])}
        )

    verdict = await replay_task(Task.GRADE_QUESTION, selection, script)
    assert verdict["valid"] is True, verdict["message"]
    assert verdict["score"] == 1.0
    mark = {
        "question_number": number,
        "response": expected_response,
        "correct_answer": expected_key,
        "points": expected_points,
    }
    assert json.loads((tmp_path / REPORT_PATH).read_text(encoding="utf-8")) == report_for(
        [mark], expected_points, student
    )
