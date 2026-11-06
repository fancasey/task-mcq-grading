import { disclosure, h } from "./kit/components.js";

function studentResult(student) {
  const header = h("tr", {}, ["Question", "Response", "Key", "Points"].map(
    (text) => h("th", { text }),
  ));
  const rows = student.marks.map((mark) => h("tr", {},
    [mark.question_number, mark.response || "Blank", mark.correct_answer, mark.points].map(
      (text) => h("td", { text: String(text) }),
    ),
  ));
  return disclosure(
    { summary: `${student.name}: ${student.score} / ${student.possible}` },
    h("table", {}, h("thead", {}, header), h("tbody", {}, rows)),
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
    h("p", { text: `Saved: ${path}` }),
    h("p", { text: `Total: ${report.total_score} / ${report.total_possible}` }),
    report.students.map(studentResult),
  ),
};
