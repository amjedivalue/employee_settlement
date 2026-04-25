import frappe
from frappe import _

from hrms.hr.doctype.full_and_final_statement.full_and_final_statement import (
    FullandFinalStatement,
)

from new_ivalue_fnf.api.full_and_final.core_data import get_default_cost_center


class CustomFullandFinalStatement(FullandFinalStatement):
    def create_journal_entry(self):
        """
        Override للزر القياسي Create Journal Entry.

        الزر القياسي يبقى كما هو.
        لكن نعدل نتيجة Journal Entry قبل فتحها للمستخدم.
        """
        journal_entry = super().create_journal_entry()

        cost_center = get_default_cost_center(self.company)

        if not cost_center:
            frappe.throw(
                _("Please set Default Cost Center in Full and Final Settings for company {0}.").format(self.company)
            )

        for row in journal_entry.accounts:
            row.cost_center = cost_center

            if row.account:
                row.party_type = "Employee"
                row.party = self.employee

        journal_entry.company = self.company

        if self.transaction_date:
            journal_entry.posting_date = self.transaction_date
            journal_entry.reference_date = self.transaction_date

        journal_entry.reference_number = self.name
        journal_entry.user_remark = "Full and Final Settlement for {0}".format(
            self.employee_name or self.employee
        )

        return journal_entry