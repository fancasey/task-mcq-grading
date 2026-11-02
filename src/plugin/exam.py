"""Local retrieval tools and a report writer; grading belongs to the agent."""

import json
from dataclasses import asdict
from pathlib import Path

from contract import (
    AnswerOutput,
    DocumentOutput,
    ExamOutput,
    QuestionOutput,
    ResponseOutput,
    SavedReportOutput,
    Student,
)
from verifier.data import DOCUMENTS, document, load, question, selection


def list_exam(given, workspace):
    key, students = load()
    return ExamOutput([Student(s, students[s][0]) for s in sorted(students)], sorted(key), list(DOCUMENTS))


def get_question(given, workspace):
    return QuestionOutput(given.question_number, question(given.question_number))


def get_answer_key(given, workspace):
    question(given.question_number)
    return AnswerOutput(given.question_number, load()[0][given.question_number])


def get_response(given, workspace):
    question(given.question_number)
    roster = load()[1]
    if given.student_id not in roster:
        raise ValueError("Unknown student ID")
    name, responses = roster[given.student_id]
    return ResponseOutput(given.student_id, name, given.question_number, responses[given.question_number])


def get_document(given, workspace):
    return DocumentOutput(given.document, document(given.document))


def save_report(given, workspace):
    selection(given.selection)
    root = Path(workspace).resolve()
    folder = root / "reports"
    path = folder / "grades.json"
    if not path.resolve().is_relative_to(root):
        raise ValueError("Report escapes workspace")
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(given.report), indent=2) + "\n", encoding="utf-8")
    return SavedReportOutput("reports/grades.json", given.report)
