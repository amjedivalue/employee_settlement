// kahled
frappe.ui.form.on("Full and Final Statement", {
  onload(frm) {
    if (!frm.doc.transaction_date) {
      frm.set_value("transaction_date", frappe.datetime.get_today());
    }

    clear_placeholder_rows(frm);
  },

  refresh(frm) {
    clear_placeholder_rows(frm);
  },

  employee(frm) {
    clear_placeholder_rows(frm);
  },

  relieving_date(frm) {
    clear_placeholder_rows(frm);
  },

  validate(frm) {
    clear_placeholder_rows(frm);
  }
});

function clear_placeholder_rows(frm) {
  const payablePlaceholders = new Set([
    "Gratuity",
    "Expense Claim",
    "Bonus",
    "Leave Encashment"
  ]);

  const receivablePlaceholders = new Set([
    "Employee Advance"
  ]);

  frm.doc.payables = (frm.doc.payables || []).filter((row) => {
    const isPlaceholder =
      payablePlaceholders.has(row.component) &&
      !row.reference_document &&
      Number(row.amount || 0) === 0;

    return !isPlaceholder;
  });

  frm.doc.receivables = (frm.doc.receivables || []).filter((row) => {
    const isPlaceholder =
      receivablePlaceholders.has(row.component) &&
      !row.reference_document &&
      Number(row.amount || 0) === 0;

    return !isPlaceholder;
  });

  frm.refresh_field("payables");
  frm.refresh_field("receivables");
}