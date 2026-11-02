"""Typed MCQ retrieval, reporting and grading contracts."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    LIST_EXAM = "list_exam"
    GET_QUESTION = "get_question"
    GET_ANSWER_KEY = "get_answer_key"
    GET_RESPONSE = "get_response"
    GET_DOCUMENT = "get_document"
    SAVE_REPORT = "save_report"


class Task(Enum):
    GRADE_EXAM = "grade-exam"


@dataclass
class EmptyInput(Output):
    pass


@dataclass
class Student(Output):
    student_id: str
    name: str


@dataclass
class ExamOutput(Output):
    students: list[Student]
    question_numbers: list[int]
    documents: list[str]


@dataclass
class QuestionInput(Output):
    question_number: int


@dataclass
class QuestionOutput(Output):
    question_number: int
    statement: str


@dataclass
class AnswerOutput(Output):
    question_number: int
    correct_answer: str


@dataclass
class ResponseInput(Output):
    student_id: str
    question_number: int


@dataclass
class ResponseOutput(Output):
    student_id: str
    name: str
    question_number: int
    response: str


@dataclass
class DocumentInput(Output):
    document: Annotated[str, "Exactly Question.txt, answerkey.txt or Student_MCQ.csv"]


@dataclass
class DocumentOutput(Output):
    document: str
    content: str


@dataclass
class GradeInput(Output):
    student_ids: Annotated[list[str], "Distinct student IDs; [] means all students"]
    question_numbers: Annotated[list[int], "Distinct MCQ numbers; [] means all MCQs (1-20)"]


@dataclass
class Mark(Output):
    question_number: int
    response: str
    correct_answer: str
    points: Annotated[int, "1 for an exact match after trimming and uppercasing, otherwise 0"]


@dataclass
class StudentGrade(Output):
    student_id: str
    name: str
    marks: list[Mark]
    score: int
    possible: int


@dataclass
class GradeReport(Output):
    students: list[StudentGrade]
    total_score: int
    total_possible: int


@dataclass
class SaveInput(Output):
    selection: GradeInput
    report: GradeReport


@dataclass
class SavedReportOutput(Output):
    path: str
    report: GradeReport


TOOLS = {
    Tool.LIST_EXAM: (EmptyInput, ExamOutput),
    Tool.GET_QUESTION: (QuestionInput, QuestionOutput),
    Tool.GET_ANSWER_KEY: (QuestionInput, AnswerOutput),
    Tool.GET_RESPONSE: (ResponseInput, ResponseOutput),
    Tool.GET_DOCUMENT: (DocumentInput, DocumentOutput),
    Tool.SAVE_REPORT: (SaveInput, SavedReportOutput),
}
TASKS = {Task.GRADE_EXAM: (GradeInput, SavedReportOutput)}
