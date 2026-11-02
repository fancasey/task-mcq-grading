import asyncio

import pytest
from slimconfig import build_output, output_schema, plain_output

from contract import TOOLS, AnswerOutput, DocumentInput, EmptyInput, QuestionInput, ResponseInput, Tool
from plugin.__main__ import IMPLEMENTATIONS, call_tool, list_tools
from verifier import verify_input, verify_output


@pytest.mark.parametrize(
    "tool,arguments",
    [
        (Tool.LIST_EXAM, EmptyInput()),
        (Tool.GET_QUESTION, QuestionInput(1)),
        (Tool.GET_QUESTION, QuestionInput(20)),
        (Tool.GET_ANSWER_KEY, QuestionInput(1)),
        (Tool.GET_RESPONSE, ResponseInput("1101901107", 1)),
        (Tool.GET_DOCUMENT, DocumentInput("Question.txt")),
        (Tool.GET_DOCUMENT, DocumentInput("answerkey.txt")),
        (Tool.GET_DOCUMENT, DocumentInput("Student_MCQ.csv")),
    ],
)
def test_tools(tmp_path, tool, arguments):
    output = IMPLEMENTATIONS[tool](arguments, tmp_path)
    assert verify_input(tool, arguments)["valid"]
    assert verify_output(tool, arguments, output, tmp_path)["valid"]
    assert build_output(plain_output(output), TOOLS[tool][1]) == output


@pytest.mark.parametrize("name", ["../contract.py", "/etc/passwd", "unknown.txt"])
def test_document_allowlist(tmp_path, name):
    args = DocumentInput(name)
    assert not verify_input(Tool.GET_DOCUMENT, args)["valid"]
    with pytest.raises(ValueError):
        IMPLEMENTATIONS[Tool.GET_DOCUMENT](args, tmp_path)


def test_false_retrieval(tmp_path):
    assert not verify_output(Tool.GET_ANSWER_KEY, QuestionInput(1), AnswerOutput(1, "A"), tmp_path)["valid"]


def test_mcp_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("NANOAGENT_WORKSPACE", str(tmp_path))
    exposed = asyncio.run(list_tools())
    assert {t.name for t in exposed} == {t.value for t in Tool}
    for given, made in TOOLS.values():
        assert output_schema(given) and output_schema(made)
    assert asyncio.run(call_tool("get_answer_key", {"question_number": 20})) == {
        "question_number": 20,
        "correct_answer": "B",
    }
