import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, relativedelta
from new_ivalue_fnf.api.full_and_final.monthly_items import (
    build_monthly_additional_salary_rows,
)
from new_ivalue_fnf.api.full_and_final.core_data import (
    get_company_letter_head,
    get_employee_basic_data,
    get_latest_salary_structure_assignment,
    get_salary_breakdown,
    validate_full_and_final_settings_exists,
)
from new_ivalue_fnf.api.full_and_final.gratuity import build_gratuity_payable
from new_ivalue_fnf.api.full_and_final.settlement_builders import (
    apply_document_header,
    apply_salary_snapshot,
    build_salary_days_payable,
)
from new_ivalue_fnf.api.full_and_final.outstanding_items import (
    build_employee_advance_rows,
    build_expense_claim_rows,
)
from new_ivalue_fnf.api.full_and_final.leave_items import build_leave_encashment_rows
from new_ivalue_fnf.api.full_and_final.rebuild_helpers import (
    clear_auto_rows_keep_manual,
)
from new_ivalue_fnf.api.full_and_final.manual_rows import (
    cancel_deleted_manual_additional_salary_rows,
    sync_manual_rows_to_additional_salary,
)


def log_trace(message: str, data=None):
    print(f"[FNF service] {message} | {data}")


def set_transaction_date(doc, method=None):
    if not doc.transaction_date:
        doc.transaction_date = nowdate()

    log_trace("transaction date set", doc.transaction_date)


def clear_auto_tables(doc):
    clear_auto_rows_keep_manual(doc)
    log_trace("auto rows cleared and manual rows preserved", doc.name)


def validate_required_values(doc):
    if not doc.employee:
        log_trace("skip build because employee is empty")
        return False

    if not doc.relieving_date:
        log_trace("skip build because relieving_date is empty")
        return False

    return True


def apply_service_period(doc):
    if not doc.date_of_joining or not doc.relieving_date:
        return

    start_date = getdate(doc.date_of_joining)
    end_date = getdate(doc.relieving_date)

    if end_date < start_date:
        frappe.throw("Relieving Date cannot be before Date of Joining.")

    difference = relativedelta(end_date + relativedelta(days=1), start_date)
    total_days = (end_date - start_date).days + 1

    doc.custom_service_years = difference.years
    doc.custom_service_month = difference.months
    doc.custom_service_days = difference.days
    doc.custom_total_of_years = flt(total_days / 365, 6)

    log_trace(
        "service period applied",
        {
            "years": doc.custom_service_years,
            "months": doc.custom_service_month,
            "days": doc.custom_service_days,
        },
    )


def get_closed_workflow_states():
    return ["Cancel", "Signed"]


def warn_if_another_fnf_exists(doc):
    existing_doc = frappe.db.get_value(
        "Full and Final Statement",
        {
            "employee": doc.employee,
            "name": ["!=", doc.name or ""],
            "docstatus": ["!=", 2],
        },
        ["name", "workflow_state"],
        as_dict=True,
    )

    if not existing_doc:
        print(f"[FNF service] no other fnf found | employee={doc.employee}")
        return

    print(
        f"[FNF service] warning other fnf exists | "
        f"name={existing_doc.name} state={existing_doc.workflow_state}"
    )

    frappe.msgprint(
        msg=_(
            "Another Full and Final Statement already exists for this employee: {0}. Current state: {1}."
        ).format(existing_doc.name, existing_doc.workflow_state),
        title=_("Existing Full and Final Statement"),
        indicator="orange",
    )


def load_base_document_data(doc):
    employee_data = get_employee_basic_data(doc.employee)

    if not employee_data:
        frappe.throw("Employee data not found.")

    apply_document_header(doc, employee_data)
    validate_full_and_final_settings_exists(doc.company)

    doc.custom_letter_head = get_company_letter_head(doc.company)
    doc.company_country = frappe.db.get_value("Company", doc.company, "country")
    doc.custom_employment_type = doc.custom_employment_type or employee_data.get(
        "employment_type"
    )
    doc.custom_reason_of_leaving = doc.custom_reason_of_leaving or employee_data.get(
        "custom_reason_of_leaving"
    )

    assignment = get_latest_salary_structure_assignment(
        doc.employee, doc.relieving_date
    )
    if assignment:
        salary_data = get_salary_breakdown(assignment)
        apply_salary_snapshot(doc, assignment, salary_data)

    apply_service_period(doc)
    return employee_data


def populate_full_and_final_doc(doc, method=None):
    log_trace("populate started", {"doc": doc.name, "employee": doc.employee})

    if not validate_required_values(doc):
        return

    warn_if_another_fnf_exists(doc)
    load_base_document_data(doc)
    clear_auto_tables(doc)

    build_salary_days_payable(doc)
    build_gratuity_payable(doc)
    build_monthly_additional_salary_rows(doc)
    build_employee_advance_rows(doc)
    build_leave_encashment_rows(doc)

    sync_manual_rows_to_additional_salary(doc)

    apply_totals(doc)

    log_trace(
        "populate finished",
        {
            "payables": len(doc.payables or []),
            "receivables": len(doc.receivables or []),
            "total_payable_amount": doc.total_payable_amount,
            "total_receivable_amount": doc.total_receivable_amount,
        },
    )


def enqueue_rebuild_after_first_insert(doc, method=None):
    """
    بعد أول حفظ، نطلب من النظام يعمل إعادة بناء في الخلفية.

    هذا يمنع ضغط السيرفر أثناء عملية الحفظ الأصلية.
    """
    frappe.enqueue(
        method="new_ivalue_fnf.api.full_and_final.service.rebuild_saved_full_and_final_statement",
        queue="short",
        timeout=300,
        enqueue_after_commit=True,
        docname=doc.name,
    )

    log_trace("queued rebuild after first insert", doc.name)


def rebuild_saved_full_and_final_statement(docname: str):
    """
    إعادة بناء Full and Final Statement بعد أول حفظ.
    تستخدم لضمان اكتمال بيانات المستند بعد insert.
    """
    doc = frappe.get_doc("Full and Final Statement", docname)

    doc.flags.skip_duplicate_fnf_warning = True

    populate_full_and_final_doc(doc)

    doc.save(ignore_permissions=True)

    frappe.db.commit()

    log_trace("background rebuild finished", doc.name)
def apply_totals(doc):
    """
    تحديث إجماليات Payables و Receivables بدون Summary.

    السبب:
    تم إلغاء summary.py، لكن ما زلنا نحتاج تحديث الإجماليات.
    """
    total_payables = 0
    total_receivables = 0

    for row in doc.payables or []:
        total_payables += flt(row.amount)

    for row in doc.receivables or []:
        total_receivables += flt(row.amount)

    doc.total_payable_amount = flt(total_payables, 2)
    doc.total_receivable_amount = flt(total_receivables, 2)