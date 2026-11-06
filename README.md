# MCQ Exam Grading

A NanoAgent task for grading the bundled Data Science exam's 20 multiple-choice
questions for one student at a time from a 55-entry roster. The agent compares responses with the supplied answer
key and saves per-question marks and totals; a deterministic verifier checks
both the submitted result and the actual workspace report.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_exam` | Discover roster names, MCQ numbers and available exam documents |
| `get_question` | Retrieve a question's full statement and options |
| `get_answer_key` | Retrieve the authoritative answer for one MCQ |
| `get_responses` | Retrieve one named student's responses to one MCQ or the full exam |
| `get_document` | Read the question paper or answer key by its exact filename |
| `save_report` | Save the agent's judgments as `reports/grades.json` in the run workspace |

| Task | Scope | Example input |
| --- | --- | --- |
| `list-exam` | List students available to grade, MCQ numbers and exam documents | `{}` |
| `grade-exam` | All 20 MCQs for one student | `{"student_name":"Suy chakriya"}` |
| `grade-question` | One MCQ for one student | `{"student_name":"Suy chakriya","question_number":1}` |

The chat agent matches the requested name against the roster in the grading
tasks' student input. It ignores capitalization and extra spaces, then passes the
canonical spelling to the task. It asks for confirmation of a likely typo,
asks the user to choose when there are several plausible matches, and asks for
a roster name when there is no match. Requests for multiple students require
the user to choose one. Both grading tasks require an exact roster name.

Each response earns 1 point for the correct letter or the written-out correct
option. Option text is matched without regard to case or spacing. A small typo
earns credit when the intended choice is unambiguous and its meaning is
preserved. An exact match to a listed option takes precedence over a possible
typo match. Incorrect choices, off-option text, ambiguous matches, invalid
letters and blanks earn 0. Marks are ordered by question number. The supplied
key is authoritative. Only MCQs 1–20 are graded.

The final `SavedReportOutput` contains `path` and `report`. The report contains
one student entry with the exact name, marks, score and possible points.
`total_score` and `total_possible` mirror that student's totals. Each mark
includes the question number, normalized response, correct answer and points.
The writer saves judgments without computing them. One call replaces the
workspace's previous grading report.

Before each grading run, NanoAgent calls the task's private reference tool
(`pin_exam_grades` or `pin_question_grade`) to pin the expected report. The tool
reads points from `src/plugin/materials/Expected_MCQ_Grades.csv` and fills in the
responses, keyed answers and totals for the selected scope. The task verifier
compares both the submission and the saved report with that snapshot. Review
the CSV whenever the responses, questions or key change.

The verification score is the fraction of requested questions for which the
submission gives the selected student exactly one mark with the expected points.
Missing and duplicate marks earn zero credit for that question. The verifier
rejects any score below 100% and lists the questions that lost credit. Passing
also requires an exact match in both reports, including responses, answer keys,
ordering and totals.

## Dataset citation

The bundled examination materials are sourced from:

K P, Dinesh (2026), “A Dataset of Digitized Student Examination Papers, Answer Keys, and Manual Evaluations for Automated Grading Research”, Mendeley Data, V1, doi: [10.17632/sf3kvjwknt.1](https://doi.org/10.17632/sf3kvjwknt.1).

The response CSV contains 50 original student records from the cited dataset and
five interspersed synthetic records for testing, named `Synthetic Student 01`
through `Synthetic Student 05`.
They include ordinary option letters, written-out correct and incorrect options,
minor typos in correct choices, free-text answers outside the choices, invalid
option letters, and blank cells.

The synthetic profiles include a perfect score (`Synthetic Student 02`), a score
below 50% (`Synthetic Student 03`), mostly written-out answers
(`Synthetic Student 04`), and mostly blank answers (`Synthetic Student 05`).

## Layout

- `nanoagent.yaml`: tool permissions and grading-task instructions
- `contract.py`: typed task, tool and report schemas
- `src/plugin/`: MCP server and local retrieval/report tools
- `src/plugin/materials/`: bundled questions, answer key and student responses
- `verifier/`: read-only data parsing and deterministic outcome checks
- `tests/`: tool, contract, scope, data integrity and verifier tests
- `ui/`: expandable student scores and per-question marks
- `product/`: catalog description and icon

## Develop and run

Requires Python 3.12+ and uv. No API keys or network services are needed by the
plugin. NanoAgent provides `NANOAGENT_WORKSPACE` for reports.

```bash
uv sync --extra dev --frozen
uv run pytest -q
uv run ruff check .
```

The test suite replays scripted grading calls through MCP without a model
service. With NanoAgent installed in the same Python environment, run
`python -m pytest -q tests/test_nanoagent.py` to also exercise its task runner,
including submission handling and enforcement of the task's tool allowlist.

NanoAgent launches the MCP server with `uv run --frozen python -m plugin`.
Install the plugin folder in NanoAgent/RUSH Lab and ask, for example,
“Who can I grade?”, “Grade the MCQ exam for Suy chakriya” or
“Grade question 2 for Suy chakriya.”
Reports belong in the run workspace.

When updating the bundled roster, update `StudentName` in `contract.py`.
