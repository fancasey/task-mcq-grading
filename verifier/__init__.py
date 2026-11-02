"""Deterministic checks against bundled source data and saved reports. Never writes."""

import json
from dataclasses import asdict
from pathlib import Path

from contract import Task, Tool

from .data import DOCUMENTS, document, load, question, selection


def result(valid, message):
    return {"valid": valid, "score": float(valid), "message": message, "details": {}}


def expected(value):
    ids, numbers = selection(value)
    key, roster = load()
    students = []
    for sid in ids:
        name, responses = roster[sid]
        marks = [
            {
                "question_number": q,
                "response": responses[q],
                "correct_answer": key[q],
                "points": int(responses[q] == key[q]),
            }
            for q in numbers
        ]
        students.append(
            {
                "student_id": sid,
                "name": name,
                "marks": marks,
                "score": sum(m["points"] for m in marks),
                "possible": len(numbers),
            }
        )
    return {
        "students": students,
        "total_score": sum(s["score"] for s in students),
        "total_possible": len(ids) * len(numbers),
    }


def check_saved(value, output, workspace):
    if output.path != "reports/grades.json":
        raise ValueError("Unexpected report path")
    root = Path(workspace).resolve()
    path = (root / output.path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Report escapes workspace")
    truth = expected(value)
    if asdict(output.report) != truth:
        raise ValueError("Grades, coverage, ordering or totals differ from source data")
    if json.loads(path.read_text(encoding="utf-8")) != truth:
        raise ValueError("Saved report differs from verified grades")


def verify_input(tool, value):
    try:
        tool = Tool(tool)
        _, students = load()
        if tool in (Tool.GET_QUESTION, Tool.GET_ANSWER_KEY, Tool.GET_RESPONSE):
            question(value.question_number)
        if tool == Tool.GET_RESPONSE and value.student_id not in students:
            raise ValueError("Unknown student ID")
        if tool == Tool.GET_DOCUMENT:
            document(value.document)
        if tool == Tool.SAVE_REPORT:
            selection(value.selection)
        return result(True, "Valid input")
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        return result(False, str(e))


def verify_output(tool, input_value, output_value, workspace):
    try:
        tool = Tool(tool)
        if not verify_input(tool, input_value)["valid"]:
            raise ValueError("Invalid input")
        key, students = load()
        if tool == Tool.SAVE_REPORT:
            check_saved(input_value.selection, output_value, workspace)
            if asdict(output_value.report) != asdict(input_value.report):
                raise ValueError("Tool changed submitted report")
        else:
            if tool == Tool.LIST_EXAM:
                truth = {
                    "students": [{"student_id": s, "name": students[s][0]} for s in sorted(students)],
                    "question_numbers": sorted(key),
                    "documents": list(DOCUMENTS),
                }
            elif tool == Tool.GET_DOCUMENT:
                truth = {"document": input_value.document, "content": document(input_value.document)}
            elif tool == Tool.GET_QUESTION:
                truth = {
                    "question_number": input_value.question_number,
                    "statement": question(input_value.question_number),
                }
            elif tool == Tool.GET_ANSWER_KEY:
                truth = {
                    "question_number": input_value.question_number,
                    "correct_answer": key[input_value.question_number],
                }
            else:
                sid, q = input_value.student_id, input_value.question_number
                truth = {
                    "student_id": sid,
                    "name": students[sid][0],
                    "question_number": q,
                    "response": students[sid][1][q],
                }
            if asdict(output_value) != truth:
                raise ValueError("Output differs from source document")
        return result(True, "Output matches source data")
    except (ValueError, TypeError, AttributeError, KeyError, OSError) as e:
        return result(False, str(e))


def verify_task(task, arguments, output, reference, workspace):
    try:
        Task(task)
        check_saved(arguments, output, workspace)
        return result(True, "All selected grades and the saved report are correct")
    except (ValueError, TypeError, AttributeError, KeyError, OSError) as e:
        return result(False, str(e))
