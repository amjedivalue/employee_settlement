import frappe
from frappe.utils import flt, getdate

from new_ivalue_fnf.api.full_and_final.core_data import (
    get_component_setting_for_company,
    get_company_currency,
    get_company_default_payable_account,
    get_days_in_month,
    get_inclusive_days,
    get_latest_salary_structure_assignment,
    get_month_first_day,
    get_salary_breakdown,
    get_salary_currency_from_assignment,
)


def log_trace(message: str, data=None):
    print(f"[FNF settlement_builders] {message} | {data}")


def get_component_label(company: str, component_key: str, fallback_label: str) -> str:
    setting_row = get_component_setting_for_company(company, component_key)

    if setting_row and setting_row.display_name:
        return setting_row.display_name

    return fallback_label


def get_component_account(company: str, component_key: str, fallback_account: str | None = None) -> str | None:
    setting_row = get_component_setting_for_company(company, component_key)

    if setting_row and setting_row.account:
        return setting_row.account

    if fallback_account:
        return fallback_account

    return get_company_default_payable_account(company)


def append_row(
    doc,
    table_field: str,
    component: str,
    amount: float,
    account: str | None = None,
    reference_document_type: str | None = None,
    reference_document: str | None = None,
    custom_number_of_days: float = 0,
):
    if flt(amount) <= 0:
        log_trace("skip zero row", {"component": component, "amount": amount})
        return

    row = doc.append(table_field, {})
    row.component = component
    row.amount = flt(amount, 2)
    row.account = account
    row.status = "Settled"
    row.reference_document_type = reference_document_type
    row.reference_document = reference_document

    if hasattr(row, "custom_number_of_days"):
        row.custom_number_of_days = flt(custom_number_of_days, 2)
    if hasattr(row, "is_manual_row"):
        row.is_manual_row = 0
    log_trace("row appended", {
        "table": table_field,
        "component": component,
        "amount": row.amount,
    })


def apply_document_header(doc, employee_data: dict):
    doc.employee_name = employee_data.get("employee_name")
    doc.company = employee_data.get("company")
    doc.department = employee_data.get("department")
    doc.designation = employee_data.get("designation")

    if not doc.date_of_joining:
        doc.date_of_joining = employee_data.get("date_of_joining")

    if not doc.relieving_date:
        doc.relieving_date = employee_data.get("relieving_date")


def apply_salary_snapshot(doc, assignment, salary_data: dict):
    doc.custom_company_currency = (
        get_salary_currency_from_assignment(assignment)
        or get_company_currency(doc.company)
    )
    doc.custom_basic_salary = flt(salary_data.get("basic"), 2)
    doc.custom_housing = flt(salary_data.get("housing"), 2)
    doc.custom_transportation = flt(salary_data.get("transportation"), 2)
    doc.custom_other_allowances = flt(salary_data.get("other"), 2)
    doc.custom_monthly_gross_salary = flt(salary_data.get("monthly_total"), 2)


def build_salary_days_payable(doc):
    salary_days_setting = get_component_setting_for_company(doc.company, "Salary Days")

    if not salary_days_setting:
        log_trace("salary days skipped because setting is missing")
        return

    if not salary_days_setting.is_enabled:
        log_trace("salary days skipped because disabled in settings")
        return

    assignment = get_latest_salary_structure_assignment(doc.employee, doc.relieving_date)

    if not assignment:
        frappe.throw("No Salary Structure Assignment found for this employee.")

    salary_data = get_salary_breakdown(assignment)
    apply_salary_snapshot(doc, assignment, salary_data)

    monthly_total = flt(salary_data.get("monthly_total"))
    month_start = get_month_first_day(doc.relieving_date)
    month_days = get_days_in_month(doc.relieving_date)

    if doc.date_of_joining and getdate(doc.date_of_joining) > month_start:
        month_start = getdate(doc.date_of_joining)

    worked_days = get_inclusive_days(month_start, doc.relieving_date)
    daily_rate = flt(monthly_total / 30, 2)

    if worked_days >= month_days:
        final_amount = flt(monthly_total, 2)
    else:
        final_amount = flt(daily_rate * worked_days, 2)

    if hasattr(doc, "custom_work_days"):
        doc.custom_work_days = flt(worked_days, 2)

    component = salary_days_setting.display_name or "Salary Days"
    account = salary_days_setting.account or get_company_default_payable_account(doc.company)

    append_row(
        doc=doc,
        table_field="payables",
        component=component,
        amount=final_amount,
        account=account,
        reference_document_type="Salary Structure Assignment",
        reference_document=assignment.name,
        custom_number_of_days=worked_days,
    )

    log_trace("salary days built", {
        "assignment": assignment.name,
        "worked_days": worked_days,
        "amount": final_amount,
    })