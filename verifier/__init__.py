"""Deterministic checks against bundled source data and saved reports. Never writes."""

import json
from dataclasses import asdict
from pathlib import Path

from contract import GradeReport, SelectionInput, Task, Tool

from .data import DOCUMENTS, document, load, pinned_grades, question, selected_questions, student_record


def result(valid, message, *, score=None):
    return {"valid": valid, "score": float(valid) if score is None else score, "message": message, "details": {}}


def expected(value):
    key, roster = load()
    name, responses = student_record(roster, value.student_name)
    numbers = selected_questions(key, value.question_number)
    points = pinned_grades(key, roster)[name]
    marks = [
        {
            "question_number": q,
            "response": responses[q],
            "correct_answer": key[q],
            "points": points[q],
        }
        for q in numbers
    ]
    score = sum(mark["points"] for mark in marks)
    return {
        "students": [{"name": name, "marks": marks, "score": score, "possible": len(numbers)}],
        "total_score": score,
        "total_possible": len(numbers),
    }


def check_saved(truth, output, workspace):
    if output.path != "reports/grades.json":
        raise ValueError("Unexpected report path")
    root = Path(workspace).resolve()
    path = (root / output.path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Report escapes workspace")
    if asdict(output.report) != truth:
        raise ValueError("Grades, coverage, ordering or totals differ from source data")
    if json.loads(path.read_text(encoding="utf-8")) != truth:
        raise ValueError("Saved report differs from verified grades")


def verify_input(tool, value):
    try:
        tool = Tool(tool)
        if tool in (Tool.GET_QUESTION, Tool.GET_ANSWER_KEY):
            question(value.question_number)
        if tool == Tool.GET_DOCUMENT:
            document(value.document)
        if tool in (Tool.GET_RESPONSES, Tool.SAVE_REPORT):
            key, students = load()
            selection = value.selection if tool == Tool.SAVE_REPORT else value
            name, _ = student_record(students, selection.student_name)
            selected_questions(key, selection.question_number)
            if tool == Tool.SAVE_REPORT and [student.name for student in value.report.students] != [name]:
                raise ValueError("The report must contain exactly the selected student")
        if tool in (Tool.PIN_EXAM_GRADES, Tool.PIN_QUESTION_GRADE):
            key, students = load()
            student_record(students, value.student_name)
            if tool == Tool.PIN_QUESTION_GRADE:
                if value.question_number is None:
                    raise ValueError("A question number is required")
                selected_questions(key, value.question_number)
        return result(True, "Valid input")
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        return result(False, str(e))


def verify_output(tool, input_value, output_value, workspace):
    try:
        tool = Tool(tool)
        if not verify_input(tool, input_value)["valid"]:
            raise ValueError("Invalid input")
        if tool == Tool.SAVE_REPORT:
            check_saved(asdict(input_value.report), output_value, workspace)
        elif tool in (Tool.PIN_EXAM_GRADES, Tool.PIN_QUESTION_GRADE):
            selection = SelectionInput(input_value.student_name, None) if tool == Tool.PIN_EXAM_GRADES else input_value
            if asdict(output_value) != expected(selection):
                raise ValueError("Reference report differs from source data")
        else:
            key, students = load()
            if tool == Tool.LIST_EXAM:
                truth = {
                    "student_names": sorted(students, key=str.casefold),
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
                name, responses = student_record(students, input_value.student_name)
                truth = {
                    "name": name,
                    "responses": [
                        {"question_number": q, "response": responses[q]}
                        for q in selected_questions(key, input_value.question_number)
                    ],
                }
            if asdict(output_value) != truth:
                raise ValueError("Output differs from source document")
        return result(True, "Output matches source data")
    except (ValueError, TypeError, AttributeError, KeyError, OSError) as e:
        return result(False, str(e))


def grading_accuracy(reference_student, submitted_report):
    expected_marks = reference_student.marks
    if not expected_marks:
        raise ValueError("Pinned report contains no grades")
    students = submitted_report.students if submitted_report is not None else []
    submitted_points = {}
    if [student.name for student in students] == [reference_student.name]:
        for mark in students[0].marks:
            submitted_points.setdefault(mark.question_number, []).append(mark.points)

    issues = []
    for mark in expected_marks:
        points = submitted_points.get(mark.question_number, [])
        if not points:
            issues.append(f"Q{mark.question_number} (missing mark)")
        elif len(points) > 1:
            issues.append(f"Q{mark.question_number} (duplicate marks)")
        elif points[0] != mark.points:
            issues.append(f"Q{mark.question_number} (awarded {points[0]}, expected {mark.points})")
    correct = len(expected_marks) - len(issues)
    return correct / len(expected_marks), issues


def verify_task(task, arguments, output, reference, workspace):
    score = 0.0
    try:
        task = Task(task)
        if task == Task.LIST_EXAM:
            return verify_output(Tool.LIST_EXAM, arguments, output, workspace)
        number = arguments.question_number if task == Task.GRADE_QUESTION else None
        if task == Task.GRADE_QUESTION and number is None:
            raise ValueError("A question number is required")
        if not isinstance(reference, GradeReport):
            raise TypeError("A pinned grade report is required")
        if [student.name for student in reference.students] != [arguments.student_name]:
            raise ValueError("Pinned report does not match the selected student")
        if number is not None and [mark.question_number for mark in reference.students[0].marks] != [number]:
            raise ValueError("Pinned report does not match the selected question")
        score, issues = grading_accuracy(reference.students[0], getattr(output, "report", None))
        if issues:
            message = "A perfect grading score is required. Questions to fix: "
            return result(False, message + ", ".join(issues) + ".", score=score)
        check_saved(asdict(reference), output, workspace)
        return result(True, "The student's grades and saved report are correct", score=score)
    except (ValueError, TypeError, AttributeError, KeyError, OSError) as e:
        return result(False, str(e), score=score)
