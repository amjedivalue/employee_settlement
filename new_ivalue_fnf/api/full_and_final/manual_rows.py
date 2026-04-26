import frappe
from frappe import _
from frappe.utils import flt, cint

from new_ivalue_fnf.api.full_and_final.core_data import get_settings_doc


def get_manual_row_type_from_table_name(table_name: str) -> str | None:
    if table_name == "Payables":
        return "Payables Manual Row"

    if table_name == "Receivables":
        return "Receivables Manual Row"

    return None


def get_manual_row_setting(company: str, row_type: str):
    settings_doc = get_settings_doc(company)

    if not settings_doc:
        return None

    manual_row_settings = getattr(settings_doc, "manual_row_settings", []) or []

    for row in manual_row_settings:
        if row.row_type == row_type:
            return row

    return None


def get_expected_salary_component_type(table_name: str) -> str | None:
    if table_name == "Payables":
        return "Earning"

    if table_name == "Receivables":
        return "Deduction"

    return None


def validate_salary_component_type(salary_component: str, expected_type: str):
    if not salary_component:
        frappe.throw(_("Salary Component is required in Full and Final Settings."))

    salary_component_type = frappe.db.get_value(
        "Salary Component",
        salary_component,
        "type",
    )

    if not salary_component_type:
        frappe.throw(_("Salary Component {0} does not exist.").format(salary_component))

    if salary_component_type != expected_type:
        frappe.throw(
            _("Salary Component {0} must be type {1}. Current type is {2}.").format(
                salary_component,
                expected_type,
                salary_component_type,
            )
        )


@frappe.whitelist()
def get_manual_row_defaults(
    company: str,
    table_name: str,
    component: str = None,
    amount: float = 0,
    document_name: str = None,
):
    if not company:
        frappe.throw(_("Company is required."))

    if not table_name:
        frappe.throw(_("Table name is required."))

    row_type = get_manual_row_type_from_table_name(table_name)

    if not row_type:
        frappe.throw(_("Invalid manual row table."))

    setting_row = get_manual_row_setting(company, row_type)

    if not setting_row:
        frappe.throw(_("Manual row settings are not configured for {0}.").format(row_type))

    if not setting_row.is_enabled:
        frappe.throw(_("{0} is disabled in Full and Final Settings.").format(row_type))

    if not setting_row.account:
        frappe.throw(_("Please set an account for {0} in Full and Final Settings.").format(row_type))

    salary_component = getattr(setting_row, "salary_component", None)
    expected_type = get_expected_salary_component_type(table_name)

    validate_salary_component_type(salary_component, expected_type)

    return {
    "account": setting_row.account,
    "status": "Settled",
    "is_manual_row": 1,
    }


def is_manual_additional_salary_row(row) -> bool:
    if not cint(getattr(row, "is_manual_row", 0)):
        return False

    amount = flt(getattr(row, "amount", 0))

    if amount <= 0:
        return False

    return True


def create_manual_additional_salary(
    employee: str,
    company: str,
    payroll_date,
    salary_component: str,
    expected_type: str,
    amount: float,
):
    validate_salary_component_type(salary_component, expected_type)

    additional_salary_doc = frappe.new_doc("Additional Salary")
    additional_salary_doc.employee = employee
    additional_salary_doc.company = company
    additional_salary_doc.payroll_date = payroll_date
    additional_salary_doc.salary_component = salary_component
    additional_salary_doc.amount = flt(amount, 2)
    additional_salary_doc.overwrite_salary_structure_amount = 0

    if hasattr(additional_salary_doc, "custom_created_from_fnf"):
        additional_salary_doc.custom_created_from_fnf = 1

    additional_salary_doc.insert(ignore_permissions=True)
    additional_salary_doc.submit()

    return additional_salary_doc


def cancel_additional_salary_if_needed(additional_salary_name: str):
    if not additional_salary_name:
        return

    additional_salary_doc = frappe.get_doc("Additional Salary", additional_salary_name)

    if hasattr(additional_salary_doc, "custom_created_from_fnf"):
        if not additional_salary_doc.custom_created_from_fnf:
            return

    if additional_salary_doc.docstatus == 1:
        additional_salary_doc.cancel()


def sync_manual_rows_for_table(doc, table_field: str, table_name: str):
    row_type = get_manual_row_type_from_table_name(table_name)
    expected_type = get_expected_salary_component_type(table_name)

    setting_row = get_manual_row_setting(doc.company, row_type)

    if not setting_row:
        return

    if not setting_row.is_enabled:
        return

    salary_component = getattr(setting_row, "salary_component", None)

    validate_salary_component_type(salary_component, expected_type)

    for row in getattr(doc, table_field, []) or []:
        if not is_manual_additional_salary_row(row):
            continue

        old_reference_type = str(getattr(row, "reference_document_type", "") or "").strip()
        old_reference_name = str(getattr(row, "reference_document", "") or "").strip()

        row.account = setting_row.account
        row.status = "Settled"

        if old_reference_type == "Additional Salary" and old_reference_name:
            additional_salary_amount = frappe.db.get_value(
                "Additional Salary",
                old_reference_name,
                "amount",
            )

            additional_salary_component = frappe.db.get_value(
                "Additional Salary",
                old_reference_name,
                "salary_component",
            )

            if (
                flt(additional_salary_amount, 2) == flt(row.amount, 2)
                and additional_salary_component == salary_component
            ):
                continue

            cancel_additional_salary_if_needed(old_reference_name)

        additional_salary_doc = create_manual_additional_salary(
            employee=doc.employee,
            company=doc.company,
            payroll_date=doc.relieving_date,
            salary_component=salary_component,
            expected_type=expected_type,
            amount=row.amount,
        )

        row.reference_document_type = "Additional Salary"
        row.reference_document = additional_salary_doc.name
        row.is_manual_row = 1


def sync_manual_rows_to_additional_salary(doc):
    sync_manual_rows_for_table(
        doc=doc,
        table_field="payables",
        table_name="Payables",
    )

    sync_manual_rows_for_table(
        doc=doc,
        table_field="receivables",
        table_name="Receivables",
    )


def cancel_deleted_manual_additional_salary_rows(doc):
    old_doc = doc.get_doc_before_save()

    if not old_doc:
        return

    current_references = set()

    for row in (doc.payables or []) + (doc.receivables or []):
        reference_document_type = str(getattr(row, "reference_document_type", "") or "").strip()
        reference_document = str(getattr(row, "reference_document", "") or "").strip()

        if reference_document_type == "Additional Salary" and reference_document:
            current_references.add(reference_document)

    for row in (old_doc.payables or []) + (old_doc.receivables or []):
        if not cint(getattr(row, "is_manual_row", 0)):
            continue

        reference_document_type = str(getattr(row, "reference_document_type", "") or "").strip()
        reference_document = str(getattr(row, "reference_document", "") or "").strip()

        if reference_document_type != "Additional Salary":
            continue

        if not reference_document:
            continue

        if reference_document in current_references:
            continue

        cancel_additional_salary_if_needed(reference_document)