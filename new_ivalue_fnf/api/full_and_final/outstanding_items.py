import frappe
from frappe.utils import flt

from new_ivalue_fnf.api.full_and_final.core_data import (
    get_component_setting_for_company,
    get_company_default_payable_account,
    get_company_employee_advance_account,
    get_settings_field_value,
)
from new_ivalue_fnf.api.full_and_final.settlement_builders import append_row


def log_trace(message: str, data=None):
    print(f"[FNF outstanding_items] {message} | {data}")


def get_component_data(company: str, component_key: str, fallback_account: str | None = None) -> dict:
    setting_row = get_component_setting_for_company(company, component_key)

    if not setting_row:
        return {
            "is_enabled": 0,
            "display_name": component_key,
            "account": fallback_account,
        }

    return {
        "is_enabled": setting_row.is_enabled,
        "display_name": setting_row.display_name or component_key,
        "account": setting_row.account or fallback_account,
    }


def get_open_employee_advances(employee: str):
    if not employee:
        return []

    rows = frappe.get_all(
        "Employee Advance",
        filters={
            "employee": employee,
            "docstatus": 1,
            "status": ["not in", ["Claimed", "Paid", "Cancelled"]],
        },
        fields=[
            "name",
            "purpose",
            "advance_amount",
            "paid_amount",
            "claimed_amount",
            "status",
        ],
    )

    log_trace("employee advances found", len(rows))
    return rows

def get_open_expense_claims(employee: str):
    if not employee:
        return []

    rows = frappe.get_all(
        "Expense Claim",
        filters={
            "employee": employee,
            "docstatus": 1,
            "approval_status": "Approved",
        },
        fields=[
            "name",
            "total_claimed_amount",
            "total_sanctioned_amount",
            "grand_total",
            "total_amount_reimbursed",
            "approval_status",
        ],
    )

    log_trace("expense claims found", len(rows))
    return rows

def build_employee_advance_rows(doc):
    component_data = get_component_data(
        company=doc.company,
        component_key="Employee Advance",
        fallback_account=get_company_employee_advance_account(doc.company),
    )

    if not component_data["is_enabled"]:
        log_trace("employee advance skipped because disabled")
        return

    rows = get_open_employee_advances(doc.employee)

    for row in rows:
        outstanding_amount = (
            flt(row.advance_amount)
            - flt(row.paid_amount)
            - flt(row.claimed_amount)
        )

        if flt(outstanding_amount) <= 0:
            continue

        # component_label = component_data["display_name"]
        component_label = component_data["display_name"]
        advance_format = get_settings_field_value(doc.company, "employee_advnace_format", "New Name")

        if row.purpose:
            if advance_format == "Purpose - New Name":
                component_label = f"{row.purpose} - {component_label}"
            elif advance_format == "New Name - Purpose":
                component_label = f"{component_label} - {row.purpose}"
        
        append_row(
            doc=doc,
            table_field="receivables",
            component=component_label,
            amount=outstanding_amount,
            account=component_data["account"],
            reference_document_type="Employee Advance",
            reference_document=row.name,
        )

        log_trace("employee advance row added", {
            "name": row.name,
            "amount": outstanding_amount,
        })

def build_expense_claim_rows(doc):
    component_data = get_component_data(
        company=doc.company,
        component_key="Expense Claim",
        fallback_account=get_company_default_payable_account(doc.company),
    )

    if not component_data["is_enabled"]:
        log_trace("expense claim skipped because disabled")
        return

    rows = get_open_expense_claims(doc.employee)

    for row in rows:
        approved_amount = flt(row.total_sanctioned_amount) or flt(row.total_claimed_amount) or flt(row.grand_total)

        reimbursed_amount = flt(row.total_amount_reimbursed)
        outstanding_amount = flt(approved_amount - reimbursed_amount, 2)

        if outstanding_amount <= 0:
            continue

        append_row(
            doc=doc,
            table_field="payables",
            component=component_data["display_name"],
            amount=outstanding_amount,
            account=component_data["account"],
            reference_document_type="Expense Claim",
            reference_document=row.name,
        )

        log_trace("expense claim row added", {
            "name": row.name,
            "amount": outstanding_amount,
        })