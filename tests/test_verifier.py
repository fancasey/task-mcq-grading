import copy

import pytest
from slimconfig import build_output

from contract import GradeInput, GradeReport, SaveInput, Task, Tool
from plugin.exam import save_report
from verifier import expected, verify_input, verify_output, verify_task
from verifier.data import load

SID = "1101901107"


def saved(tmp_path, selection):
    report = build_output(expected(selection), GradeReport)
    output = save_report(SaveInput(selection, report), tmp_path)
    return output


@pytest.mark.parametrize(
    "ids,questions", [([SID], [1]), ([SID], [1, 2]), ([SID], []), ([SID, "1101901111"], [1]), ([], [1, 2]), ([], [])]
)
def test_supported_scopes(tmp_path, ids, questions):
    selection = GradeInput(ids, questions)
    output = saved(tmp_path, selection)
    assert verify_task(Task.GRADE_EXAM, selection, output, None, tmp_path)["valid"]
    assert verify_output(Tool.SAVE_REPORT, SaveInput(selection, output.report), output, tmp_path)["valid"]


def test_known_grades(tmp_path):
    selection = GradeInput([SID], [1, 2, 5])
    output = saved(tmp_path, selection)
    student = output.report.students[0]
    assert [m.points for m in student.marks] == [0, 1, 1]
    assert student.score == 2 and student.possible == 3
    assert (output.report.total_score, output.report.total_possible) == (2, 3)


@pytest.mark.parametrize(
    "ids,questions",
    [(["unknown"], [1]), ([SID, SID], [1]), ([SID], [1, 1]), ([SID], [0]), ([SID], [21]), ([SID], [True])],
)
def test_invalid_selection(tmp_path, ids, questions):
    assert not verify_input(Tool.SAVE_REPORT, SaveInput(GradeInput(ids, questions), GradeReport([], 0, 0)))["valid"]


@pytest.mark.parametrize("mutation", ["points", "response", "key", "name", "missing", "duplicate", "score", "total"])
def test_tampered_grades(tmp_path, mutation):
    selection = GradeInput([SID], [1, 2])
    output = saved(tmp_path, selection)
    student = output.report.students[0]
    if mutation == "points":
        student.marks[0].points = 1
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
    elif mutation == "score":
        student.score += 1
    else:
        output.report.total_possible += 1
    verdict = verify_task(Task.GRADE_EXAM, selection, output, None, tmp_path)
    assert verdict["valid"] is False and verdict["score"] == 0.0


@pytest.mark.parametrize("content", [None, "{invalid", "{}", "[]", "null"])
def test_missing_malformed_or_incomplete_file(tmp_path, content):
    selection = GradeInput([SID], [1])
    output = saved(tmp_path, selection)
    path = tmp_path / output.path
    if content is None:
        path.unlink()
    else:
        path.write_text(content)
    assert not verify_task(Task.GRADE_EXAM, selection, output, None, tmp_path)["valid"]


def test_wrong_output_and_path(tmp_path):
    selection = GradeInput([SID], [1])
    assert not verify_task(Task.GRADE_EXAM, selection, None, None, tmp_path)["valid"]
    output = saved(tmp_path, selection)
    output.path = "../grades.json"
    assert not verify_task(Task.GRADE_EXAM, selection, output, None, tmp_path)["valid"]


def test_symlink_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "reports").symlink_to(outside, target_is_directory=True)
    selection = GradeInput([SID], [1])
    with pytest.raises(ValueError):
        save_report(SaveInput(selection, build_output(expected(selection), GradeReport)), workspace)


def test_data_integrity():
    key, roster = load()
    assert len(roster) == 50
    assert sorted(key) == list(range(1, 21))
    assert all(set(responses) == set(key) for _, responses in roster.values())


def test_blank_invalid_and_normalized_responses(tmp_path, monkeypatch):
    from verifier import data

    original = data.document

    def amended(name):
        text = original(name)
        if name == "Student_MCQ.csv":
            text = text.replace("1101901107,Suy chakriya,D,C,B,A,B", "1101901107,Suy chakriya,,INVALID, a , c , b ")
        return text

    monkeypatch.setattr(data, "document", amended)
    selection = GradeInput([SID], [1, 2, 3, 4, 5])
    output = saved(tmp_path, selection)
    marks = output.report.students[0].marks
    assert [m.response for m in marks] == ["", "INVALID", "A", "C", "B"]
    assert [m.points for m in marks] == [0, 0, 1, 1, 1]
    assert verify_task(Task.GRADE_EXAM, selection, output, None, tmp_path)["valid"]


def test_csv_parser_matches_standard_library():
    import csv
    import io

    from verifier.data import DOCUMENTS, csv_rows, document

    for name in DOCUMENTS[1:]:
        text = document(name)
        assert csv_rows(text) == list(csv.reader(io.StringIO(text)))
    text = 'id,name,value\r\n1,"Last, First","a""b"\r\n'
    assert csv_rows(text) == list(csv.reader(io.StringIO(text)))
