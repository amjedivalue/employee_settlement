
import frappe
from frappe.utils import getdate, flt, nowdate

from . import employee_data
from . import service_time
from . import receivables
from . import payables
from . import leaves
from . import salary


def set_transaction_date(doc, method=None):
    if not doc.transaction_date:
        doc.transaction_date = nowdate()


def has_only_default_placeholder_rows(doc) -> bool:
    placeholder_payables = {"Gratuity", "Expense Claim", "Bonus", "Leave Encashment"}
    placeholder_receivables = {"Employee Advance"}

    payables_rows = doc.get("payables") or []
    receivables_rows = doc.get("receivables") or []

    if not payables_rows and not receivables_rows:
        return False

    def is_placeholder_row(row, allowed_components):
        return (
            row.get("component") in allowed_components
            and not row.get("reference_document")
            and flt(row.get("amount")) == 0
        )

    payables_ok = all(
        is_placeholder_row(row, placeholder_payables) for row in payables_rows
    ) if payables_rows else True

    receivables_ok = all(
        is_placeholder_row(row, placeholder_receivables) for row in receivables_rows
    ) if receivables_rows else True

    return payables_ok and receivables_ok


def should_rebuild_fnf(doc) -> bool:
    if doc.docstatus != 0:
        return False

    if not doc.employee or not doc.relieving_date:
        return False

    old_doc = doc.get_doc_before_save()

    # أول حفظ لمستند جديد
    if not old_doc:
        return True

    # إذا السطور الحالية فقط default placeholder rows
    if has_only_default_placeholder_rows(doc):
        return True

    # إذا تغيّر الموظف
    if old_doc.employee != doc.employee:
        return True

    # إذا تغيّر relieving_date
    if str(old_doc.relieving_date) != str(doc.relieving_date):
        return True

    return False


@frappe.whitelist()
def get_full_and_final_data(employee: str, relieving_date=None):
    emp = employee_data.fetch_employee_snapshot(employee)
    if not emp:
        frappe.throw("Employee not found.")

    letter_head = frappe.db.get_value(
        "Company",
        emp.get("company"),
        "default_letter_head"
    )

    join_date = emp.get("date_of_joining")
    final_date = getdate(relieving_date or emp.get("relieving_date"))

    if not join_date:
        frappe.throw("Employee Date of Joining is missing.")

    if not final_date:
        frappe.throw("Relieving Date is required.")

    salary_info = salary.compute_last_month_prorated_salary(
        employee,
        join_date,
        final_date
    )
    #cureency symbol
    currency = salary_info.get("currency")

    if not currency:
        currency = employee_data.fetch_company_currency(emp.get("company"))

    if not currency:
        frappe.throw("Salary Currency is missing in Salary Structure Assignment, Salary Structure, and Company.")
    
    payable_account = employee_data.fetch_company_payable_account(emp.get("company"))

    leave_rows = leaves.compute_carry_forward_leave_rows(employee, join_date, final_date)
    service = service_time.compute_service_period(join_date, final_date)

    payables_rows, total_payables = payables.build_payables_rows(
        salary_info,
        leave_rows,
        payable_account
    )

    receivables_rows, total_receivables = receivables.build_receivables_from_employee_advances(employee)

    # assets مش مطلوبة
    assets_rows = []
    total_assets_cost = 0.0

    leaves_balance = 0.0
    for row in leave_rows:
        leaves_balance += flt(row.get("balance"))

    leave_amount = flt(leaves_balance * salary_info["daily_rate"], 2)

    return {
        "ok": True,
        "company_currency": currency,
        "letter_head": letter_head,
        "employee": emp,
        "salary": {
            "basic_salary": flt(salary_info["breakdown"]["basic"], 2),
            "housing": flt(salary_info["breakdown"]["housing"], 2),
            "transportation": flt(salary_info["breakdown"]["traveling"], 2),
            "other_allowance": flt(salary_info["breakdown"]["other"], 2),
            "monthly_gross_salary": flt(salary_info["breakdown"]["monthly_total"], 2),
            "daily_rate": flt(salary_info["daily_rate"], 6),
            "worked_days": flt(salary_info["worked_days"], 1),
            "prorated_amount": flt(salary_info["amount"], 2),
        },
        "relieving_month_days": flt(salary_info["worked_days"]),
        "service": {
            "years": service["years"],
            "months": service["months"],
            "days": service["days"],
            "total_years": service["total_years"],
        },
        "payables": payables_rows,
        "receivables": receivables_rows,
        "assets_allocated": assets_rows,
        "carry_forward_leaves": leave_rows,
        "totals": {
            "total_payable_amount": flt(total_payables, 2),
            "total_receivable_amount": flt(total_receivables, 2),
            "total_asset_recovery_cost": flt(total_assets_cost, 2),
        },
        "leaves_balanced": flt(leaves_balance, 2),
        "leaves_amount": flt(leave_amount, 2),
    }


def populate_full_and_final_doc(doc, method=None):
    if not should_rebuild_fnf(doc):
        return

    data = get_full_and_final_data(
        employee=doc.employee,
        relieving_date=doc.relieving_date
    )

    if not data or not data.get("ok"):
        return

    employee_snapshot = data.get("employee") or {}
    salary_data = data.get("salary") or {}
    service_data = data.get("service") or {}
    totals_data = data.get("totals") or {}

    # parent standard fields
    if hasattr(doc, "employee_name"):
        doc.employee_name = employee_snapshot.get("employee_name")

    if hasattr(doc, "company"):
        doc.company = employee_snapshot.get("company")

    if hasattr(doc, "department"):
        doc.department = employee_snapshot.get("department")

    if hasattr(doc, "designation"):
        doc.designation = employee_snapshot.get("designation")

    if hasattr(doc, "date_of_joining"):
        doc.date_of_joining = employee_snapshot.get("date_of_joining")

    # custom summary fields
    if hasattr(doc, "custom_company_currency"):
        doc.custom_company_currency = data.get("company_currency")

    if hasattr(doc, "custom_letter_head"):
        doc.custom_letter_head = data.get("letter_head")

    if hasattr(doc, "custom_basic_salary"):
        doc.custom_basic_salary = salary_data.get("basic_salary", 0)

    if hasattr(doc, "custom_housing"):
        doc.custom_housing = salary_data.get("housing", 0)

    if hasattr(doc, "custom_transportation"):
        doc.custom_transportation = salary_data.get("transportation", 0)

    if hasattr(doc, "custom_other_allowances"):
        doc.custom_other_allowances = salary_data.get("other_allowance", 0)

    if hasattr(doc, "custom_monthly_gross_salary"):
        doc.custom_monthly_gross_salary = salary_data.get("monthly_gross_salary", 0)

    if hasattr(doc, "custom_work_days"):
        doc.custom_work_days = data.get("relieving_month_days", 0)

    if hasattr(doc, "custom_leaves_balanced"):
        doc.custom_leaves_balanced = data.get("leaves_balanced", 0)

    if hasattr(doc, "custom_leaves_amount"):
        doc.custom_leaves_amount = data.get("leaves_amount", 0)

    # service fields
    if hasattr(doc, "custom_service_years"):
        doc.custom_service_years = service_data.get("years", 0)

    if hasattr(doc, "custom_service_month"):
        doc.custom_service_month = service_data.get("months", 0)

    if hasattr(doc, "custom_service_days"):
        doc.custom_service_days = service_data.get("days", 0)

    if hasattr(doc, "custom_total_of_years"):
        doc.custom_total_of_years = service_data.get("total_years", 0)

    # clear tables
    doc.set("payables", [])
    doc.set("receivables", [])
    doc.set("assets_allocated", [])

    if hasattr(doc, "custom_carry_forward_leaves"):
        doc.set("custom_carry_forward_leaves", [])

    # fill payables
    for row in data.get("payables") or []:
        amount = flt(row.get("amount"))

        if amount <= 0:
            continue
        doc.append("payables", {
            "component": row.get("component"),
            "reference_document_type": row.get("reference_document_type"),
            "reference_document": row.get("reference_document"),
            "account": row.get("account"),
            "amount": row.get("amount"),
            "status": row.get("status") or "Settled",
            "custom_number_of_days": (
                row.get("custom_number_of_days")
                or row.get("days")
                or row.get("day_count")
                or 0
            ),
        })

    # fill receivables
    for row in data.get("receivables") or []:
        amount = flt(row.get("amount"))

        if amount <= 0:
            continue
        doc.append("receivables", {
            "component": row.get("component"),
            "reference_document_type": row.get("reference_document_type"),
            "reference_document": row.get("reference_document"),
            "account": row.get("account"),
            "amount": row.get("amount"),
            "status": row.get("status") or "Settled",
            "custom_number_of_days": (
                row.get("custom_number_of_days")
               
            ),
        })

    # carry forward leaves
    if hasattr(doc, "custom_carry_forward_leaves"):
        for row in data.get("carry_forward_leaves") or []:
            doc.append("custom_carry_forward_leaves", {
                "leave_type": row.get("leave_type"),
                "earned": row.get("earned"),
                "taken": row.get("taken"),
                "balance": row.get("balance"),
                "allocation_ref": row.get("allocation_ref"),
            })

    # totals
    if hasattr(doc, "total_payable_amount"):
        doc.total_payable_amount = totals_data.get("total_payable_amount", 0)

    if hasattr(doc, "total_receivable_amount"):
        doc.total_receivable_amount = totals_data.get("total_receivable_amount", 0)

    if hasattr(doc, "total_asset_recovery_cost"):
        doc.total_asset_recovery_cost = totals_data.get("total_asset_recovery_cost", 0)

    # force status
    for row in doc.payables or []:
        row.status = "Settled"

    for row in doc.receivables or []:
        row.status = "Settled"