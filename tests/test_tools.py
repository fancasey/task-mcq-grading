from dataclasses import replace

import pytest
from slimconfig import build_output, output_schema, plain_output

from contract import TOOLS, DocumentInput, EmptyInput, QuestionInput, SelectionInput, StudentName, Tool
from plugin.__main__ import IMPLEMENTATIONS
from verifier import verify_input, verify_output


@pytest.mark.parametrize(
    "tool,arguments",
    [
        (Tool.LIST_EXAM, EmptyInput()),
        (Tool.GET_QUESTION, QuestionInput(1)),
        (Tool.GET_QUESTION, QuestionInput(20)),
        (Tool.GET_ANSWER_KEY, QuestionInput(1)),
        (Tool.GET_RESPONSES, SelectionInput(StudentName.SUY_CHAKRIYA, 1)),
        (Tool.GET_RESPONSES, SelectionInput(StudentName.SUY_CHAKRIYA, None)),
        (Tool.GET_DOCUMENT, DocumentInput("Question.txt")),
        (Tool.GET_DOCUMENT, DocumentInput("answerkey.txt")),
    ],
)
def test_tools(tmp_path, tool, arguments):
    output = IMPLEMENTATIONS[tool](arguments, tmp_path)
    assert verify_input(tool, arguments)["valid"]
    assert verify_output(tool, arguments, output, tmp_path)["valid"]
    assert build_output(plain_output(output), TOOLS[tool][1]) == output


@pytest.mark.parametrize("name", ["../contract.py", "/etc/passwd", "unknown.txt", "Student_MCQ.csv"])
def test_document_allowlist(tmp_path, name):
    args = DocumentInput(name)
    assert not verify_input(Tool.GET_DOCUMENT, args)["valid"]
    with pytest.raises(ValueError):
        IMPLEMENTATIONS[Tool.GET_DOCUMENT](args, tmp_path)


@pytest.mark.anyio
async def test_mcp_tool_schemas_and_retrieval(mcp_session, tmp_path):
    exposed = (await mcp_session.list_tools()).tools
    assert {item.name for item in exposed} == {tool.value for tool in Tool}
    cases = {
        Tool.LIST_EXAM: (EmptyInput(), "question_numbers", [1, 20]),
        Tool.GET_QUESTION: (QuestionInput(1), "statement", ""),
        Tool.GET_ANSWER_KEY: (QuestionInput(20), "correct_answer", "A"),
        Tool.GET_RESPONSES: (SelectionInput(StudentName.SUY_CHAKRIYA, 1), "responses", []),
        Tool.GET_DOCUMENT: (DocumentInput("answerkey.txt"), "content", ""),
    }
    for item in exposed:
        tool = Tool(item.name)
        input_type, output_type = TOOLS[tool]
        assert item.inputSchema == output_schema(input_type)
        assert item.outputSchema == output_schema(output_type)
        if tool in cases:
            arguments, field, incorrect = cases[tool]
            result = await mcp_session.call_tool(tool.value, plain_output(arguments))
            assert not result.isError
            output = build_output(result.structuredContent, output_type)
            assert verify_output(tool, arguments, output, tmp_path)["valid"]
            assert not verify_output(tool, arguments, replace(output, **{field: incorrect}), tmp_path)["valid"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "tool,arguments,message",
    [
        ("get_question", {}, "question_number"),
        ("get_question", {"question_number": 21}, "Unknown MCQ question number"),
        ("get_answer_key", {"question_number": 0}, "Unknown MCQ question number"),
        ("get_responses", {"student_name": "missing", "question_number": 1}, "missing"),
        ("get_document", {"document": "Student_MCQ.csv"}, "Unknown document"),
        ("get_document", {"document": "../Question.txt"}, "Unknown document"),
        ("unregistered", {}, "unregistered"),
    ],
)
async def test_mcp_errors(mcp_session, tool, arguments, message):
    result = await mcp_session.call_tool(tool, arguments)
    assert result.isError
    assert result.structuredContent is None
    assert message in result.content[0].text

    # A rejected call must leave the same session usable.
    result = await mcp_session.call_tool("get_answer_key", {"question_number": 20})
    assert not result.isError
    assert result.structuredContent == {"question_number": 20, "correct_answer": "B"}
