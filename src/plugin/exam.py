"""Local retrieval tools and a report writer; grading belongs to the agent."""

import json
from dataclasses import asdict
from pathlib import Path

from slimconfig import build_output

from contract import (
    AnswerOutput,
    DocumentOutput,
    ExamOutput,
    GradeReport,
    QuestionOutput,
    Response,
    ResponsesOutput,
    SavedReportOutput,
    SelectionInput,
)
from verifier import expected
from verifier.data import DOCUMENTS, document, load, question, selected_questions, student_record


def list_exam(given, workspace):
    key, students = load()
    return ExamOutput(sorted(students, key=str.casefold), sorted(key), list(DOCUMENTS))


def get_question(given, workspace):
    return QuestionOutput(given.question_number, question(given.question_number))


def get_answer_key(given, workspace):
    question(given.question_number)
    return AnswerOutput(given.question_number, load()[0][given.question_number])


def get_responses(given, workspace):
    key, roster = load()
    name, responses = student_record(roster, given.student_name)
    numbers = selected_questions(key, given.question_number)
    return ResponsesOutput(name, [Response(q, responses[q]) for q in numbers])


def get_document(given, workspace):
    return DocumentOutput(given.document, document(given.document))


def pin_exam_grades(given, workspace):
    return build_output(expected(SelectionInput(given.student_name, None)), GradeReport)


def pin_question_grade(given, workspace):
    return build_output(expected(given), GradeReport)


def save_report(given, workspace):
    key, roster = load()
    name, _ = student_record(roster, given.selection.student_name)
    selected_questions(key, given.selection.question_number)
    if [student.name for student in given.report.students] != [name]:
        raise ValueError("The report must contain exactly the selected student")
    root = Path(workspace).resolve()
    folder = root / "reports"
    path = folder / "grades.json"
    if not path.resolve().is_relative_to(root):
        raise ValueError("Report escapes workspace")
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(given.report), indent=2) + "\n", encoding="utf-8")
    return SavedReportOutput("reports/grades.json", given.report)
