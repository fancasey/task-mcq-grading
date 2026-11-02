"""Read-only exam data and selection rules; standard library only."""

import re
from pathlib import Path

MATERIALS = Path(__file__).resolve().parents[1] / "src" / "plugin" / "materials"
DOCUMENTS = ("Question.txt", "answerkey.txt", "Student_MCQ.csv")


def document(name):
    if name not in DOCUMENTS:
        raise ValueError("Unknown document; choose one of " + ", ".join(DOCUMENTS))
    return (MATERIALS / name).read_text(encoding="utf-8")


def csv_rows(text):
    """Parse CSV without non-allowlisted imports in the verifier sandbox."""
    rows, row, field = [], [], []
    quoted = False
    i = 0
    while i < len(text):
        char = text[i]
        if char == '"':
            if quoted and i + 1 < len(text) and text[i + 1] == '"':
                field.append('"')
                i += 1
            else:
                quoted = not quoted
        elif char == "," and not quoted:
            row.append("".join(field))
            field = []
        elif char == "\n" and not quoted:
            rows.append(row + ["".join(field).rstrip("\r")])
            row, field = [], []
        else:
            field.append(char)
        i += 1
    if quoted:
        raise ValueError("Unclosed CSV quote")
    if field or row:
        rows.append(row + ["".join(field).rstrip("\r")])
    return rows


def load():
    key = {int(r[0]): r[2].strip().upper() for r in csv_rows(document("answerkey.txt"))[1:] if r[1] == "MCQ"}
    rows = csv_rows(document("Student_MCQ.csv"))
    students = {}
    for row in rows[1:]:
        if len(row) != len(rows[0]) or row[0] in students:
            raise ValueError("Malformed or duplicate student row")
        students[row[0]] = (row[1], dict(zip(map(int, rows[0][2:]), (s.strip().upper() for s in row[2:]))))
    return key, students


def question(number):
    key, _ = load()
    if type(number) is not int or number not in key:
        raise ValueError("Unknown MCQ question number")
    text = document("Question.txt").split("Part II:")[0]
    sections = {int(n): s.strip() for n, s in re.findall(r"(?ms)^(\d+)\. (.*?)(?=^\d+\. |\Z)", text)}
    return sections[number]


def selection(value):
    key, students = load()
    if any(type(s) is not str or s not in students for s in value.student_ids):
        raise ValueError("Unknown student ID; use list_exam")
    if any(type(q) is not int or q not in key for q in value.question_numbers):
        raise ValueError("Unknown MCQ question number")
    if len(set(value.student_ids)) != len(value.student_ids) or len(set(value.question_numbers)) != len(
        value.question_numbers
    ):
        raise ValueError("Selections must be distinct")
    return sorted(value.student_ids or students), sorted(value.question_numbers or key)
