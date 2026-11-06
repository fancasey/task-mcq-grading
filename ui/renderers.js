import { disclosure, h, icon } from "./kit/components.js";

function studentResult(student) {
  const header = h("tr", {}, ["Question", "Response", "Key", "Points"].map(
    (text) => h("th", { scope: "col", text }),
  ));
  const rows = student.marks.map((mark) => h("tr", {},
    [mark.question_number, mark.response || "Blank", mark.correct_answer, mark.points].map(
      (text) => h("td", { text: String(text) }),
    ),
  ));
  return h("div", { class: "grade-student" },
    h("div", { class: "grade-summary" },
      h("h4", { text: student.name }),
      h("p", { class: "grade-score", text: `${student.score} / ${student.possible}` }),
    ),
    disclosure(
      { summary: "Per-question marks" },
      h("table", {}, h("thead", {}, header), h("tbody", {}, rows)),
    ),
  );
}

export default {
  ExamOutput: ({ student_names, question_numbers, documents }) => h("div", {},
    h("h3", { text: `Students available to grade (${student_names.length})` }),
    h("ul", {}, student_names.map((name) => h("li", { text: name }))),
    h("p", { text: `MCQs: ${question_numbers.join(", ")}` }),
    h("p", { text: `Exam documents: ${documents.join(", ")}` }),
  ),
  SavedReportOutput: ({ path, report }) => h("div", { class: "grades" },
    report.students.map(studentResult),
    report.students.length !== 1
      ? h("p", { text: `Total: ${report.total_score} / ${report.total_possible}` })
      : null,
    h("p", { class: "grade-path" }, icon("file", { size: 16 }), "Saved to ", h("code", { text: path })),
  ),
};
