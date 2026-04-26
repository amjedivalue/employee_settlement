import frappe
from frappe.utils import flt, getdate

from new_ivalue_fnf.api.full_and_final.settlement_builders import append_row
from new_ivalue_fnf.api.full_and_final.core_data import (
    get_component_setting_for_company,
    get_month_last_day,
    get_settings_field_value,
)

def log_trace(message: str, data=None):
    print(f"[FNF monthly_items] {message} | {data}")


def get_additional_salary_rows(employee: str, relieving_date):
    if not employee or not relieving_date:
        return []

    relieving_date_value = getdate(relieving_date)
    month_start = relieving_date_value.replace(day=1)
    month_end = get_month_last_day(relieving_date_value)

    rows = frappe.get_all(
        "Additional Salary",
        filters={
            "employee": employee,
            "docstatus": 1,
            "payroll_date": ["between", [month_start, month_end]],
        },
        fields=[
            "name",
            "salary_component",
            "payroll_date",
            "amount",
            "type",
        ],
    )

    filtered_rows = []

    for row in rows:
        if flt(row.amount) <= 0:
            continue

        if frappe.db.has_column("Additional Salary", "custom_created_from_fnf"):
            created_from_fnf = frappe.db.get_value(
                "Additional Salary",
                row.name,
                "custom_created_from_fnf",
            )

            if created_from_fnf:
                continue

        filtered_rows.append(row)

    log_trace("monthly additional salary rows", len(filtered_rows))
    return filtered_rows
def get_component_display_and_account(company: str, salary_type: str):
    component_key = "Additional Salary Earning"

    if salary_type == "Deduction":
        component_key = "Additional Salary Deduction"

    setting_row = get_component_setting_for_company(company, component_key)

    if not setting_row:
        return {
            "display_name": component_key,
            "account": None,
            "is_enabled": 0,
        }

    return {
        "display_name": setting_row.display_name or component_key,
        "account": setting_row.account,
        "is_enabled": setting_row.is_enabled,
    }


def build_monthly_additional_salary_rows(doc):
    rows = get_additional_salary_rows(doc.employee, doc.relieving_date)

    for row in rows:
        setting_data = get_component_display_and_account(doc.company, row.type)

        if not setting_data["is_enabled"]:
            log_trace("skip disabled setting", {
                "type": row.type,
                "salary_component": row.salary_component,
            })
            continue

        component_label = setting_data["display_name"]
        additional_salary_format = get_settings_field_value(doc.company, "additional_salary_format", "Component")

        if row.salary_component:
            if additional_salary_format == "Component - New Name":
                component_label = f"{row.salary_component} - {component_label}"
            elif additional_salary_format == "New Name -Component":
                component_label = f"{component_label} - {row.salary_component}"
            else:
                component_label = row.salary_component

        target_table = "payables"
        if row.type == "Deduction":
            target_table = "receivables"

        append_row(
            doc=doc,
            table_field=target_table,
            component=component_label,
            amount=row.amount,
            account=setting_data["account"],
            reference_document_type="Additional Salary",
            reference_document=row.name,
        )

        log_trace("monthly additional salary row added", {
            "table": target_table,
            "name": row.name,
            "amount": row.amount,
        })