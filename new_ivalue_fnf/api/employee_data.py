# =========================================================
# MASTER DATA
# =========================================================

import frappe


def fetch_employee_snapshot(employee_id: str) -> dict:
    emp = frappe.db.get_value(
        "Employee",
        employee_id,
        [
            "name",
            "employee_name",
            "company",
            "department",
            "designation",
            "date_of_joining",
            "relieving_date",
        ],
        as_dict=True,
    )
    return emp or {}


def fetch_company_currency(company: str) -> str | None:
    if not company:
        return None
    return frappe.db.get_value("Company", company, "default_currency")


def fetch_employee_salary_currency(employee: str) -> str | None:
    return frappe.db.get_value("Employee", employee, "salary_currency")


def fetch_company_payable_account(company: str) -> str | None:
    if not company:
        return None

    doc = frappe.get_cached_doc("Company", company)
    candidate_fields = [
        "default_payroll_payable_account",
        "payroll_payable_account",
        "default_payable_account",
    ]
    for f in candidate_fields:
        if hasattr(doc, f) and getattr(doc, f):
            return getattr(doc, f)
    return None
