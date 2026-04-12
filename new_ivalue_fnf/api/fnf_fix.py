import frappe
from frappe.utils import flt
def clean_rows(doc, method=None):
    def is_valid(row):
        return flt(row.amount) > 0

    doc.set("receivables", [r for r in doc.get("receivables") or [] if is_valid(r)])
    doc.set("payables", [r for r in doc.get("payables") or [] if is_valid(r)])