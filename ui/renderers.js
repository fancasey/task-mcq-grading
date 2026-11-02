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
    { summary: `${student.name} (${student.student_id}): ${student.score} / ${student.possible}` },
    h("table", {}, h("thead", {}, header), h("tbody", {}, rows)),
  );
}

export default {
  SavedReportOutput: ({ path, report }) => h("div", { class: "grades" },
    h("p", { text: `Saved: ${path}` }),
    h("p", { text: `Total: ${report.total_score} / ${report.total_possible}` }),
    report.students.map(studentResult),
  ),
};
