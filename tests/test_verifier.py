import copy

import pytest
from slimconfig import build_output, output_schema

from contract import (
    TASKS,
    GradeExamInput,
    GradeQuestionInput,
    GradeReport,
    SaveInput,
    SelectionInput,
    StudentName,
    Task,
    Tool,
)
from plugin.exam import save_report
from verifier import expected, verify_input, verify_output, verify_task
from verifier.data import load, pinned_grades

STUDENT = StudentName.SUY_CHAKRIYA


def saved(tmp_path, selection):
    report = build_output(expected(selection), GradeReport)
    output = save_report(SaveInput(selection, report), tmp_path)
    return output


@pytest.mark.parametrize(
    "task,arguments,number",
    [
        (Task.GRADE_EXAM, GradeExamInput(STUDENT), None),
        (Task.GRADE_QUESTION, GradeQuestionInput(STUDENT, 1), 1),
        (Task.GRADE_QUESTION, GradeQuestionInput(STUDENT, 20), 20),
    ],
)
def test_supported_scopes(tmp_path, task, arguments, number):
    selection = SelectionInput(STUDENT, number)
    output = saved(tmp_path, selection)
    assert verify_task(task, arguments, output, output.report, tmp_path)["valid"]
    assert verify_output(Tool.SAVE_REPORT, SaveInput(selection, output.report), output, tmp_path)["valid"]


def test_task_and_writer_use_the_pinned_snapshot(tmp_path, monkeypatch):
    arguments = GradeQuestionInput(STUDENT, 1)
    selection = SelectionInput(STUDENT, 1)
    output = saved(tmp_path, selection)
    reference = copy.deepcopy(output.report)

    def unavailable(*args):
        raise AssertionError("The grading CSV was read after pinning")

    monkeypatch.setattr("verifier.pinned_grades", unavailable)
    assert verify_output(Tool.SAVE_REPORT, SaveInput(selection, output.report), output, tmp_path)["valid"]
    assert verify_task(Task.GRADE_QUESTION, arguments, output, reference, tmp_path)["valid"]


@pytest.mark.parametrize("name,number", [("unknown", 1), (STUDENT, 0), (STUDENT, 21), (STUDENT, True)])
def test_invalid_selection(name, number):
    report = build_output(expected(SelectionInput(STUDENT, 1)), GradeReport)
    assert not verify_input(Tool.SAVE_REPORT, SaveInput(SelectionInput(name, number), report))["valid"]


def test_save_rejects_report_for_another_student(tmp_path):
    selection = SelectionInput(STUDENT, 1)
    other = SelectionInput(StudentName.UNG_KENG_LONG, 1)
    report = build_output(expected(other), GradeReport)
    given = SaveInput(selection, report)

    assert not verify_input(Tool.SAVE_REPORT, given)["valid"]
    with pytest.raises(ValueError, match="exactly the selected student"):
        save_report(given, tmp_path)
    assert not (tmp_path / "reports").exists()


def test_task_scope_must_match_report(tmp_path):
    single = saved(tmp_path, SelectionInput(STUDENT, 1))
    full = saved(tmp_path, SelectionInput(STUDENT, None))
    assert not verify_task(Task.GRADE_EXAM, GradeExamInput(STUDENT), single, full.report, tmp_path)["valid"]
    assert not verify_task(Task.GRADE_QUESTION, GradeQuestionInput(STUDENT, 1), full, single.report, tmp_path)["valid"]


@pytest.mark.parametrize(
    "mutation,accuracy",
    [
        ("points", 19 / 20),
        ("response", 1.0),
        ("key", 1.0),
        ("name", 0.0),
        ("missing", 19 / 20),
        ("duplicate", 19 / 20),
        ("order", 1.0),
        ("score", 1.0),
        ("total", 1.0),
    ],
)
def test_tampered_grades(tmp_path, mutation, accuracy):
    selection = SelectionInput(STUDENT, None)
    output = saved(tmp_path, selection)
    reference = copy.deepcopy(output.report)
    student = output.report.students[0]
    if mutation == "points":
        student.marks[0].points = 1 - student.marks[0].points
    elif mutation == "response":
        student.marks[0].response = "B"
    elif mutation == "key":
        student.marks[0].correct_answer = "D"
    elif mutation == "name":
        student.name = "Wrong Name"
    elif mutation == "missing":
        student.marks.pop()
    elif mutation == "duplicate":
        student.marks.append(copy.deepcopy(student.marks[0]))
    elif mutation == "order":
        student.marks.reverse()
    elif mutation == "score":
        student.score += 1
    else:
        output.report.total_possible += 1
    verdict = verify_task(Task.GRADE_EXAM, GradeExamInput(STUDENT), output, reference, tmp_path)
    assert verdict["valid"] is False
    assert verdict["score"] == accuracy
    if mutation == "missing":
        assert "Q20 (missing mark)" in verdict["message"]
    elif mutation == "duplicate":
        assert "Q1 (duplicate marks)" in verdict["message"]
    elif mutation == "name":
        assert all(f"Q{mark.question_number} (missing mark)" in verdict["message"] for mark in student.marks)


@pytest.mark.parametrize("content", [None, "{invalid", "{}", "[]", "null"])
def test_missing_malformed_or_incomplete_file(tmp_path, content):
    selection = SelectionInput(STUDENT, None)
    output = saved(tmp_path, selection)
    path = tmp_path / output.path
    if content is None:
        path.unlink()
    else:
        path.write_text(content)
    assert not verify_task(Task.GRADE_EXAM, GradeExamInput(STUDENT), output, output.report, tmp_path)["valid"]


def test_wrong_output_and_path(tmp_path):
    selection = SelectionInput(STUDENT, None)
    output = saved(tmp_path, selection)
    assert not verify_task(Task.GRADE_EXAM, GradeExamInput(STUDENT), None, output.report, tmp_path)["valid"]
    assert not verify_task(Task.GRADE_EXAM, GradeExamInput(STUDENT), output, None, tmp_path)["valid"]
    output.path = "../grades.json"
    assert not verify_task(Task.GRADE_EXAM, GradeExamInput(STUDENT), output, output.report, tmp_path)["valid"]


def test_symlink_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "reports").symlink_to(outside, target_is_directory=True)
    selection = SelectionInput(STUDENT, None)
    with pytest.raises(ValueError):
        save_report(SaveInput(selection, build_output(expected(selection), GradeReport)), workspace)


def test_data_integrity():
    key, roster = load()
    assert len(roster) == 55
    assert sorted(key) == list(range(1, 21))
    assert all(set(responses) == set(key) for responses in roster.values())
    assert pinned_grades(key, roster).keys() == roster.keys()


def test_duplicate_roster_name_is_reported(tmp_path, monkeypatch):
    from verifier import data

    responses = (data.MATERIALS / data.RESPONSES_FILE).read_text(encoding="utf-8")
    first_student = responses.splitlines()[1]
    duplicate = first_student.replace("Suy chakriya", "SUY  CHAKRIYA", 1)
    (tmp_path / data.RESPONSES_FILE).write_text(responses + duplicate + "\n", encoding="utf-8")
    (tmp_path / "answerkey.txt").write_text(data.document("answerkey.txt"), encoding="utf-8")
    monkeypatch.setattr(data, "MATERIALS", tmp_path)

    with pytest.raises(ValueError, match="Duplicate student name.*SUY  CHAKRIYA"):
        load()


def test_grading_task_schemas_cover_roster():
    _, roster = load()
    names = sorted(roster)
    for task in (Task.GRADE_EXAM, Task.GRADE_QUESTION):
        given, _ = TASKS[task]
        allowed_names = output_schema(given)["properties"]["student_name"]["enum"]
        assert sorted(allowed_names) == names


@pytest.mark.parametrize("task", [Task.GRADE_EXAM, Task.GRADE_QUESTION])
@pytest.mark.parametrize("name", ["Suy chakria", "1101901107", ["Suy chakriya", "Ung Keng long"], ""])
def test_task_input_rejects_invalid_names(task, name):
    arguments = {"student_name": name}
    if task == Task.GRADE_QUESTION:
        arguments["question_number"] = 1
    with pytest.raises(ValueError, match="student_name"):
        build_output(arguments, TASKS[task][0])


def test_blank_invalid_and_normalized_responses(tmp_path, monkeypatch):
    from verifier import data

    materials = tmp_path / "materials"
    materials.mkdir()
    for path in data.MATERIALS.iterdir():
        text = path.read_text(encoding="utf-8")
        if path.name == "Student_MCQ.csv":
            text = text.replace("Suy chakriya,D,C,B,A,B", "Suy chakriya,, c ,INVALID, d , b ")
        (materials / path.name).write_text(text, encoding="utf-8")

    monkeypatch.setattr(data, "MATERIALS", materials)
    selection = SelectionInput(STUDENT, None)
    output = saved(tmp_path, selection)
    marks = output.report.students[0].marks[:5]
    assert [m.response for m in marks] == ["", "C", "INVALID", "D", "B"]
    assert [m.points for m in marks] == [0, 1, 0, 0, 1]
    assert verify_task(Task.GRADE_EXAM, GradeExamInput(STUDENT), output, output.report, tmp_path)["valid"]


@pytest.mark.parametrize(
    "student,number,response,key,points",
    [
        (StudentName.SYNTHETIC_STUDENT_01, 1, "LITTLE OR NO AUTOCORELATION", "B", 1),
        (StudentName.SYNTHETIC_STUDENT_03, 3, "HAMIMNG DISTANCE", "A", 1),
        (StudentName.SYNTHETIC_STUDENT_01, 17, "FALSE", "B", 1),
        (StudentName.SYNTHETIC_STUDENT_05, 19, "TP / (TP + FN)", "B", 0),
        (StudentName.SYNTHETIC_STUDENT_01, 6, "STACKING", "A", 0),
        (StudentName.SYNTHETIC_STUDENT_01, 8, "E", "C", 0),
        (StudentName.SYNTHETIC_STUDENT_01, 13, "", "B", 0),
    ],
)
def test_pinned_grading_cases(tmp_path, student, number, response, key, points):
    selection = SelectionInput(student, number)
    arguments = GradeQuestionInput(student, number)
    reference = build_output(expected(selection), GradeReport)
    for submitted_points in (points, 1 - points):
        report = build_output(
            {
                "students": [
                    {
                        "name": student.value,
                        "marks": [
                            {
                                "question_number": number,
                                "response": response,
                                "correct_answer": key,
                                "points": submitted_points,
                            }
                        ],
                        "score": submitted_points,
                        "possible": 1,
                    }
                ],
                "total_score": submitted_points,
                "total_possible": 1,
            },
            GradeReport,
        )
        output = save_report(SaveInput(selection, report), tmp_path)
        assert verify_task(Task.GRADE_QUESTION, arguments, output, reference, tmp_path)["valid"] == (
            submitted_points == points
        )


def test_csv_parser_matches_standard_library():
    import csv
    import io

    from verifier.data import DOCUMENTS, MATERIALS, csv_rows

    for name in (*DOCUMENTS[1:], "Student_MCQ.csv"):
        text = (MATERIALS / name).read_text(encoding="utf-8")
        assert csv_rows(text) == list(csv.reader(io.StringIO(text)))
    text = 'id,name,value\r\n1,"Last, First","a""b"\r\n'
    assert csv_rows(text) == list(csv.reader(io.StringIO(text)))
