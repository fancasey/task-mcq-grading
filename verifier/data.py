"""Read-only exam data and selection rules; standard library only."""

import re
from pathlib import Path

MATERIALS = Path(__file__).resolve().parents[1] / "src" / "plugin" / "materials"
DOCUMENTS = ("Question.txt", "answerkey.txt")
RESPONSES_FILE = "Student_MCQ.csv"
GRADES_FILE = "Expected_MCQ_Grades.csv"


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
    rows = csv_rows((MATERIALS / RESPONSES_FILE).read_text(encoding="utf-8"))
    questions = sorted(key)
    if not rows or rows[0] != ["student_name", *map(str, questions)]:
        raise ValueError("Responses must cover the exam questions in order")
    students = {}
    normalized_names = set()
    for row in rows[1:]:
        if len(row) != len(rows[0]) or not row[0].strip():
            raise ValueError("Malformed student response row")
        name, *responses = row
        normalized = " ".join(name.casefold().split())
        if normalized in normalized_names:
            raise ValueError(f"Duplicate student name in the roster: {name!r}")
        normalized_names.add(normalized)
        students[name] = dict(zip(questions, (response.strip().upper() for response in responses)))
    return key, students


def question(number):
    key, _ = load()
    if type(number) is not int or number not in key:
        raise ValueError("Unknown MCQ question number")
    text = document("Question.txt").split("Part II:")[0]
    sections = {int(n): s.strip() for n, s in re.findall(r"(?ms)^(\d+)\. (.*?)(?=^\d+\. |\Z)", text)}
    return sections[number]


def pinned_grades(key, students):
    rows = csv_rows((MATERIALS / GRADES_FILE).read_text(encoding="utf-8"))
    questions = sorted(key)
    if not rows or rows[0] != ["student_name", *map(str, questions)]:
        raise ValueError("Pinned grades must cover the exam questions in order")
    grades = {}
    for row in rows[1:]:
        name, *points = row
        if name in grades or len(points) != len(questions) or any(p not in ("0", "1") for p in points):
            raise ValueError("Malformed or duplicate pinned grade row")
        grades[name] = dict(zip(questions, map(int, points)))
    if grades.keys() != students.keys():
        raise ValueError("Pinned grades must cover the response roster")
    return grades


def student_record(students, name):
    if name not in students:
        raise ValueError("Unknown student name. Choose an exact roster name from list_exam.")
    # Slicing converts a string-backed task enum to its plain string value.
    return name[:], students[name]


def selected_questions(key, number):
    if number is None:
        return sorted(key)
    if type(number) is not int or number not in key:
        raise ValueError("Unknown MCQ question number")
    return [number]
