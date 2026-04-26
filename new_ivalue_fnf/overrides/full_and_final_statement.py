# import frappe
# from frappe import _
# from frappe.utils import flt

# from hrms.hr.doctype.full_and_final_statement.full_and_final_statement import (
#     FullandFinalStatement,
# )

# from new_ivalue_fnf.api.full_and_final.core_data import (
#     get_default_cost_center,
#     get_company_default_payable_account,
#     get_company_employee_advance_account,
# )


# class CustomFullandFinalStatement(FullandFinalStatement):

#     @frappe.whitelist()
#     def create_journal_entry(self):
#         """
#         تعديل زر Create Journal Entry القياسي.

#         ماذا نعمل؟
#         - تعبئة Cost Center
#         - تعبئة Reference Number / Reference Date في رأس القيد
#         - تعبئة الحساب المفقود في السطر الموازن
#         - تعبئة Party Type / Party فقط على حسابات ذمة الموظف
#         - تعبئة User Remark فقط للسطور اليدوية
#         """
#         journal_entry = super().create_journal_entry()

#         self.apply_journal_entry_header(journal_entry)
#         self.apply_journal_entry_rows(journal_entry)

#         return journal_entry

#     def apply_journal_entry_header(self, journal_entry):
#         """
#         تعبئة بيانات رأس Journal Entry.
#         """
#         journal_entry.company = self.company

#         posting_date = self.transaction_date or journal_entry.posting_date

#         if posting_date:
#             journal_entry.posting_date = posting_date

#         # ERPNext يعرض هذه الحقول باسم:
#         # Reference Number / Reference Date
#         if journal_entry.meta.has_field("cheque_no"):
#             journal_entry.cheque_no = self.name

#         if journal_entry.meta.has_field("cheque_date"):
#             journal_entry.cheque_date = posting_date

#         # احتياط إذا عندك Custom Fields بهذه الأسماء
#         if journal_entry.meta.has_field("reference_number"):
#             journal_entry.reference_number = self.name

#         if journal_entry.meta.has_field("reference_date"):
#             journal_entry.reference_date = posting_date

#         journal_entry.user_remark = "Full and Final Settlement for {0}".format(
#             self.employee_name or self.employee
#         )

#     def apply_journal_entry_rows(self, journal_entry):
#         """
#         تعديل سطور Journal Entry.
#         """
#         cost_center = get_default_cost_center(self.company)

#         if not cost_center:
#             frappe.throw(
#                 _("Please set Default Cost Center in Full and Final Settings for company {0}.").format(
#                     self.company
#                 )
#             )

#         source_rows = self.get_full_and_final_source_rows()
#         used_source_indexes = set()

#         for row in journal_entry.accounts:
#             self.fill_missing_journal_account(row)

#             row.cost_center = cost_center

#             self.apply_employee_party_if_needed(row)

#             matched_source = self.get_matching_source_row(
#                 journal_row=row,
#                 source_rows=source_rows,
#                 used_source_indexes=used_source_indexes,
#             )

#             if matched_source:
#                 used_source_indexes.add(matched_source["index"])
#                 self.apply_manual_row_remark_only(row, matched_source["row"])

#     def fill_missing_journal_account(self, journal_row):
#         """
#         إذا طلع السطر الموازن بدون Account نعطيه حساب مناسب.
#         """
#         if journal_row.account:
#             return

#         debit_amount = self.get_journal_row_debit_amount(journal_row)
#         credit_amount = self.get_journal_row_credit_amount(journal_row)

#         account = None

#         if credit_amount > 0:
#             account = get_company_default_payable_account(self.company)

#         if debit_amount > 0:
#             account = get_company_employee_advance_account(self.company)

#         if not account:
#             account = get_company_default_payable_account(self.company)

#         if not account:
#             frappe.throw(
#                 _("Could not find a settlement account for company {0}.").format(
#                     self.company
#                 )
#             )

#         journal_row.account = account

#     def apply_employee_party_if_needed(self, journal_row):
#         """
#         تعبئة Party Type / Party فقط إذا الحساب يمثل ذمة موظف.

#         نعبيها على:
#         - Payroll Payable
#         - Employee Advance
#         - Employee Payable
#         - Employee Receivable
#         - أي Account نوعه Payable أو Receivable

#         لا نعبيها على:
#         - Expense
#         - Asset عام
#         - Bank
#         - Cash
#         - Capital Equipment
#         """
#         if not journal_row.account:
#             return

#         if not self.employee:
#             return

#         # نفرغها أولًا حتى لا تبقى معبأة على حساب غير مناسب
#         journal_row.party_type = None
#         journal_row.party = None

#         if not self.is_employee_balance_account(journal_row.account):
#             return

#         journal_row.party_type = "Employee"
#         journal_row.party = self.employee

#     def is_employee_balance_account(self, account: str) -> bool:
#         """
#         تحديد هل الحساب يمثل ذمة موظف أم لا.
#         """
#         if not account:
#             return False

#         account_data = frappe.db.get_value(
#             "Account",
#             account,
#             ["account_type", "root_type"],
#             as_dict=True,
#         ) or {}

#         account_type = account_data.get("account_type")

#         if account_type in ["Payable", "Receivable"]:
#             return True

#         account_name = str(account).lower()

#         employee_balance_keywords = [
#             "payroll payable",
#             "employee payable",
#             "employee receivable",
#             "employee advance",
#             "advance employee",
#         ]

#         for keyword in employee_balance_keywords:
#             if keyword in account_name:
#                 return True

#         return False

#     def get_full_and_final_source_rows(self):
#         """
#         تجهيز سطور Full and Final حتى نعرف إذا السطر Manual Row.
#         """
#         source_rows = []

#         for table_field in ["payables", "receivables"]:
#             rows = getattr(self, table_field, []) or []

#             for row in rows:
#                 source_rows.append({
#                     "table_field": table_field,
#                     "component": row.component,
#                     "amount": flt(row.amount, 2),
#                     "account": row.account,
#                     "reference_document_type": row.reference_document_type,
#                     "reference_document": row.reference_document,
#                     "is_manual_row": getattr(row, "is_manual_row", 0),
#                 })

#         return source_rows

#     def get_matching_source_row(self, journal_row, source_rows, used_source_indexes):
#         """
#         ربط Journal Entry Row مع السطر الأصلي حسب Account + Amount.
#         """
#         journal_amount = self.get_journal_row_amount(journal_row)

#         for index, source_row in enumerate(source_rows):
#             if index in used_source_indexes:
#                 continue

#             if source_row.get("account") != journal_row.account:
#                 continue

#             if flt(source_row.get("amount"), 2) != journal_amount:
#                 continue

#             return {
#                 "index": index,
#                 "row": source_row,
#             }

#         return None

#     def apply_manual_row_remark_only(self, journal_row, source_row):
#         """
#         نعبّي User Remark فقط للسطور اليدوية.

#         السطور الأوتوماتيك لا تحتاج Remark لأن مصدرها محفوظ داخل Full and Final.
#         """
#         if not source_row.get("is_manual_row"):
#             return

#         if not journal_row.meta.has_field("user_remark"):
#             return

#         remark = "Full and Final Manual Row: {0}".format(
#             source_row.get("component") or "-"
#         )

#         if source_row.get("reference_document"):
#             remark = "{0} | Source: Full and Final Statement {1}".format(
#                 remark,
#                 source_row.get("reference_document"),
#             )

#         journal_row.user_remark = remark

#     def get_journal_row_amount(self, journal_row):
#         """
#         جلب قيمة السطر سواء Debit أو Credit.
#         """
#         debit_amount = self.get_journal_row_debit_amount(journal_row)

#         if debit_amount > 0:
#             return flt(debit_amount, 2)

#         credit_amount = self.get_journal_row_credit_amount(journal_row)
#         return flt(credit_amount, 2)

#     def get_journal_row_debit_amount(self, journal_row):
#         """
#         جلب Debit من الحقل المناسب.
#         """
#         if hasattr(journal_row, "debit_in_account_currency"):
#             return flt(journal_row.debit_in_account_currency)

#         return flt(journal_row.debit)

#     def get_journal_row_credit_amount(self, journal_row):
#         """
#         جلب Credit من الحقل المناسب.
#         """
#         if hasattr(journal_row, "credit_in_account_currency"):
#             return flt(journal_row.credit_in_account_currency)

#         return flt(journal_row.credit)