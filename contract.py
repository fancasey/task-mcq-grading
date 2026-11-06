"""Typed MCQ retrieval, reporting and grading contracts."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    LIST_EXAM = "list_exam"
    GET_QUESTION = "get_question"
    GET_ANSWER_KEY = "get_answer_key"
    GET_RESPONSES = "get_responses"
    GET_DOCUMENT = "get_document"
    SAVE_REPORT = "save_report"
    PIN_EXAM_GRADES = "pin_exam_grades"
    PIN_QUESTION_GRADE = "pin_question_grade"


class Task(Enum):
    LIST_EXAM = "list-exam"
    GRADE_EXAM = "grade-exam"
    GRADE_QUESTION = "grade-question"


class StudentName(str, Enum):
    CHAV_BUNNA = "Chav Bunna"
    CHEA_CHANRAKSMEG = "Chea Chanraksmeg"
    CHEA_CHANSINEATH = "Chea Chansineath"
    CHHIV_BUNCHHEAN = "chhiv Bunchhean"
    CHHOUR_THABAI = "chhour Thabai"
    CHY_KIMTONY = "Chy Kimtony"
    DEFH_SRET_LEAK = "Defh Sret leak"
    DOUNG_RATANAKSAM_BAT = "Doung RatanakSam bat"
    E_SOKMEAN = "E Sokmean"
    HAK_VINCHET = "Hak Vinchet"
    HENG_KEVIN = "Heng Kevin"
    HNY_DARAPICHCHAN = "Hny DaraPichchan"
    KAO_KANHCHANA = "Kao Kanhchana"
    KONG_SOVANKIRY = "Kong Sovankiry"
    KREEN_RATHANA = "Kreen Rathana"
    KUNG_LEAKHANA = "Kung Leakhana"
    LAY_CHIVAAN_VINLO = "Lay Chivaan Vinlo"
    LAY_SOPHANN = "Lay Sophann"
    LIM_HUAMENG = "Lim Huameng"
    LY_KIMLONG = "Ly Kimlong"
    LY_SREYPOV = "Ly Sreypov"
    NARIN_COLIN = "Narin Colin"
    NEY_SENRITH = "Ney Senrith"
    NOL_MONO = "NOL Mono"
    NYSOPHEAKTRA = "NySopheaktra"
    ONG_SOPHIN = "Ong Sophin"
    OU_DAUID = "Ou Dauid"
    PAK_MANETH = "Pak Maneth"
    PHALLA_BORORMEY = "phalla Borormey"
    PHEAK_CHANCHIVY = "PHEAK CHANCHIVY"
    REASEY_SEREI_NOATY = "Reasey Serei Noaty"
    RETH_SAKMETA = "Reth Sakmeta"
    SAK_LYSEM = "Sak Lysem"
    SAMBATH_VATANA = "Sambath Vatana"
    SAN_THORNEN = "San Thornen"
    SEAB_NAVIN = "Seab Navin"
    SENG_SOPHAL = "Seng Sophal"
    SOR_PANHA_RITH = "Sor Panha Rith"
    SOTH_SAMBATH = "Soth Sambath"
    SROENN_DAUNGCHAN = "Sroenn Daungchan"
    SUY_CHAKRIYA = "Suy chakriya"
    SYNTHETIC_STUDENT_01 = "Synthetic Student 01"
    SYNTHETIC_STUDENT_02 = "Synthetic Student 02"
    SYNTHETIC_STUDENT_03 = "Synthetic Student 03"
    SYNTHETIC_STUDENT_04 = "Synthetic Student 04"
    SYNTHETIC_STUDENT_05 = "Synthetic Student 05"
    TAK_VANNAK = "Tak Vannak"
    THARN_LAYSIM = "Tharn Laysim"
    THORN_THEANLAY = "Thorn Theanlay"
    THY_SAONAN = "Thy Saonan"
    UNG_KENG_LONG = "Ung Keng long"
    VEAN_SOVANVATHANA = "Vean Sovanvathana"
    VEN_CHANNA = "Ven Channa"
    YEAK_YEANMAO = "Yeak Yeanmao"
    YIN_CHANTHA = "Yin Chantha"


@dataclass
class EmptyInput(Output):
    pass


@dataclass
class ExamOutput(Output):
    student_names: list[str]
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
class GradeExamInput(Output):
    student_name: Annotated[
        StudentName,
        "Use the exact name from the allowed roster values for one student. Match names ignoring capitalization "
        "and extra spaces. If a partial name or possible typo matches several students, list the matching full "
        "names and wait for the user to choose. For example, 'synthetic student' matches Synthetic Student 01 "
        "through Synthetic Student 05. Confirm a single likely typo before grading. If no name matches, ask "
        "for a full roster name. For multiple students or the whole class, ask the user to choose one student "
        "and wait before calling a grading task.",
    ]


@dataclass
class GradeQuestionInput(GradeExamInput):
    question_number: Annotated[int, "The MCQ number, from 1 to 20. Ask if the user has not specified one question."]


@dataclass
class SelectionInput(GradeExamInput):
    question_number: Annotated[int | None, "One MCQ number, or null for all 20 MCQs"]


@dataclass
class Response(Output):
    question_number: int
    response: str


@dataclass
class ResponsesOutput(Output):
    name: str
    responses: list[Response]


@dataclass
class DocumentInput(Output):
    document: Annotated[str, "Exactly Question.txt or answerkey.txt"]


@dataclass
class DocumentOutput(Output):
    document: str
    content: str


@dataclass
class Mark(Output):
    question_number: int
    response: str
    correct_answer: str
    points: Annotated[int, "1 for the correct letter or identifiable correct option text, otherwise 0"]


@dataclass
class StudentGrade(Output):
    name: str
    marks: list[Mark]
    score: int
    possible: int


@dataclass
class GradeReportOutput(Output):
    students: list[StudentGrade]
    total_score: int
    total_possible: int


GradeReport = GradeReportOutput


@dataclass
class SaveInput(Output):
    selection: SelectionInput
    report: GradeReport


@dataclass
class SavedReportOutput(Output):
    path: str
    report: GradeReport


TOOLS = {
    Tool.LIST_EXAM: (EmptyInput, ExamOutput),
    Tool.GET_QUESTION: (QuestionInput, QuestionOutput),
    Tool.GET_ANSWER_KEY: (QuestionInput, AnswerOutput),
    Tool.GET_RESPONSES: (SelectionInput, ResponsesOutput),
    Tool.GET_DOCUMENT: (DocumentInput, DocumentOutput),
    Tool.SAVE_REPORT: (SaveInput, SavedReportOutput),
    Tool.PIN_EXAM_GRADES: (GradeExamInput, GradeReportOutput),
    Tool.PIN_QUESTION_GRADE: (GradeQuestionInput, GradeReportOutput),
}
TASKS = {
    Task.LIST_EXAM: (EmptyInput, ExamOutput),
    Task.GRADE_EXAM: (GradeExamInput, SavedReportOutput),
    Task.GRADE_QUESTION: (GradeQuestionInput, SavedReportOutput),
}
