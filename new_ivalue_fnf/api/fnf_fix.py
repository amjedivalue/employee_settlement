import frappe
from frappe.utils import flt

def clean_receivables(doc, method):
    # تنظيف Receivables
    cleaned = []
    for row in doc.receivables or []:
        if (
            row
            and row.reference_document
            and row.reference_document_type
            and flt(row.amount) > 0
        ):
            cleaned.append(row)

    doc.receivables = cleaned

    # تنظيف Payables (اختياري بس مهم)
    cleaned_payables = []
    for row in doc.payables or []:
        if (
            row
            and row.reference_document
            and row.reference_document_type
            and flt(row.amount) > 0
        ):
            cleaned_payables.append(row)

    doc.payables = cleaned_payables