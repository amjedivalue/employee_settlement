import frappe
from frappe.utils import flt
from frappe import _
from new_ivalue_fnf.api.full_and_final.core_data import (
    get_company_default_payable_account,
    get_company_employee_advance_account,
    get_settings_doc,
)


def log_trace(message: str, data=None):
    print(f"[FNF manual_rows] {message} | {data}")


def get_default_manual_account(company: str, table_name: str) -> str | None:
    row_type = get_manual_row_type_from_table_name(table_name)

    if not row_type:
        return None

    setting_row = get_manual_row_setting(company, row_type)

    if setting_row and setting_row.account:
        return setting_row.account

    if table_name == "Receivables":
        return get_company_employee_advance_account(company)

    return get_company_default_payable_account(company)



def build_manual_row_data(doc, table_name: str, component: str, amount: float) -> dict:
        if not component:
            frappe.throw(_("Component is required."))
        if flt(amount) <= 0:
            frappe.throw(_("Amount must be greater than zero."))

        row_type = get_manual_row_type_from_table_name(table_name)

        if not row_type:
            frappe.throw(_("Invalid manual row table."))

        setting_row = get_manual_row_setting(doc.company, row_type)

        if not setting_row:
            frappe.throw(_("Manual row settings are not configured for {0}.").format(row_type))

        if not setting_row.is_enabled:
            frappe.throw(_("{0} is disabled in Full and Final Settings.").format(row_type))

        if not setting_row.account:
            frappe.throw(_("Please set an account for {0} in Full and Final Settings.").format(row_type))

        account = setting_row.account
        reference_document_type, reference_document = get_manual_row_reference(doc.name)


        row_data = {
            "component": component,
            "amount": flt(amount, 2),
            "account": account,
            "status": "Settled",
            "reference_document_type": reference_document_type,
            "reference_document": reference_document,
            "is_manual_row": 1,
        }

        log_trace("manual row prepared", row_data)
        return row_data


def add_manual_row(doc, table_name: str, component: str, amount: float):
    table_field = "payables" if table_name == "Payables" else "receivables"

    row_data = build_manual_row_data(doc, table_name, component, amount)

    row = doc.append(table_field, {})

    row.component = row_data["component"]
    row.amount = row_data["amount"]
    row.account = row_data["account"]
    row.status = row_data["status"]
    row.reference_document_type = row_data["reference_document_type"]
    row.reference_document = row_data["reference_document"]

    if hasattr(row, "is_manual_row"):
        row.is_manual_row = 1

    log_trace("manual row added", {
        "table": table_field,
        "component": row.component,
        "amount": row.amount,
    })
@frappe.whitelist()
def get_manual_row_defaults(company: str, table_name: str, component: str = None, amount: float = 0, document_name: str = None):
    """
    ترجع القيم الافتراضية للسطر اليدوي حسب جدول Settings.

    Payables  -> Payables Manual Row
    Receivables -> Receivables Manual Row

    ملاحظة مهمة:
    لا نمنع التكرار هنا.
    لأن البزنس ممكن يحتاج يضيف نفس الاسم ونفس المبلغ أكثر من مرة.
    """
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

    reference_document_type, reference_document = get_manual_row_reference(document_name)

    return {
        "account": setting_row.account,
        "status": "Settled",
        "is_manual_row": 1,
        "reference_document_type": reference_document_type,
        "reference_document": reference_document,
        "remarks": "Manual row created from Full and Final Statement {0}".format(document_name)
            if reference_document else "",
    }

def get_manual_row_type_from_table_name(table_name: str) -> str | None:
    """
    تحويل اسم الجدول القادم من الواجهة إلى row_type الموجود في Settings.
    """
    if table_name == "Payables":
        return "Payables Manual Row"

    if table_name == "Receivables":
        return "Receivables Manual Row"

    return None


def get_manual_row_setting(company: str, row_type: str):
    """
    قراءة إعداد السطر اليدوي من Full and Final Settings.
    """
    settings_doc = get_settings_doc(company)

    if not settings_doc:
        return None

    manual_row_settings = getattr(settings_doc, "manual_row_settings", []) or []

    for row in manual_row_settings:
        if row.row_type == row_type:
            return row

    return None
def is_saved_document_name(document_name: str | None) -> bool:
    """
    نتحقق أن اسم المستند حقيقي وليس New Doc.
    """
    if not document_name:
        return False

    document_name = str(document_name)

    if document_name.startswith("new-"):
        return False

    return True


def get_manual_row_reference(document_name: str | None):
    """
    مصدر السطر اليدوي هو Full and Final Statement نفسه.

    السبب:
    السطر اليدوي لا يوجد خلفه DocType ثاني مثل Leave Allocation أو Employee Advance.
    """
    if not is_saved_document_name(document_name):
        return None, None

    return "Full and Final Statement", document_name


def ensure_manual_row_references(doc):
    """
    تثبيت Reference للسطور اليدوية قبل إنشاء Journal Entry.

    مهم جدًا:
    حتى لو الواجهة ما عبّت المرجع، السيرفر يضمن تعبئته.
    """
    for table_field in ["payables", "receivables"]:
        rows = getattr(doc, table_field, []) or []

        for row in rows:
            if not getattr(row, "is_manual_row", 0):
                continue

            reference_document_type, reference_document = get_manual_row_reference(doc.name)

            if reference_document_type and not row.reference_document_type:
                row.reference_document_type = reference_document_type

            if reference_document and not row.reference_document:
                row.reference_document = reference_document

            if hasattr(row, "remarks") and not row.remarks:
                row.remarks = "Manual row created from Full and Final Statement {0}".format(
                    doc.name
                )