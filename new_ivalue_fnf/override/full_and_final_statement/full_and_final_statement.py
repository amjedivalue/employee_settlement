import frappe
from hrms.hr.doctype.full_and_final_statement.full_and_final_statement import FullandFinalStatement

class CustomFullandFinalStatement(FullandFinalStatement):
    def validate(self):
        frappe.throw('sssss')