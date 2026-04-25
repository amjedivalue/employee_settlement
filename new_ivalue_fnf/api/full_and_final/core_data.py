from datetime import date

import frappe
from frappe import _
from frappe.utils import flt, getdate, relativedelta


def log_trace(message: str, data=None):
    print(f"[FNF core_data] {message} | {data}")


def get_inclusive_days(start_date, end_date) -> int:
    if not start_date or not end_date:
        return 0

    start_value = getdate(start_date)
    end_value = getdate(end_date)

    if end_value < start_value:
        return 0

    return (end_value - start_value).days + 1


def get_month_first_day(any_date) -> date:
    current_date = getdate(any_date)
    return date(current_date.year, current_date.month, 1)


def get_month_last_day(any_date) -> date:
    current_date = getdate(any_date)

    if current_date.month == 12:
        next_month_first_day = date(current_date.year + 1, 1, 1)
    else:
        next_month_first_day = date(current_date.year, current_date.month + 1, 1)

    return next_month_first_day - relativedelta(days=1)


def get_days_in_month(any_date) -> int:
    month_start = get_month_first_day(any_date)
    month_end = get_month_last_day(any_date)
    return (month_end - month_start).days + 1


def get_settings_doc(company: str):
    if not company:
        return None

    settings_name = frappe.db.get_value(
        "Full and Final Settings",
        {"company": company},
        "name",
    )

    if not settings_name:
        return None

    log_trace("settings found", settings_name)
    return frappe.get_doc("Full and Final Settings", settings_name)


def validate_full_and_final_settings_exists(company: str):
    if not company:
        frappe.throw(_("Company is required to continue."))

    settings_name = frappe.db.get_value(
        "Full and Final Settings",
        {"company": company},
        "name",
    )

    if not settings_name:
        frappe.throw(
            _("Please create Full and Final Settings first for company: {0}").format(company)
        )


def get_component_setting_for_company(company: str, component_key: str):
    if not company or not component_key:
        return None

    settings_doc = get_settings_doc(company)

    if not settings_doc:
        return None

    for row in settings_doc.components:
        if row.component_key == component_key:
            return row

    return None


def get_employee_basic_data(employee: str) -> dict:
    if not employee:
        return {}

    employee_data = frappe.db.get_value(
        "Employee",
        employee,
        [
            "name",
            "employee_name",
            "company",
            "department",
            "designation",
            "date_of_joining",
            "relieving_date",
            "employment_type",
            "custom_reason_of_leaving",
        ],
        as_dict=True,
    ) or {}

    log_trace("employee data loaded", employee_data.get("name"))
    return employee_data


def get_company_currency(company: str) -> str | None:
    if not company:
        return None

    return frappe.db.get_value("Company", company, "default_currency")


def get_company_letter_head(company: str) -> str | None:
    if not company:
        return None

    return frappe.db.get_value("Company", company, "default_letter_head")

def is_valid_company_account(account: str | None, company: str) -> bool:
    """
    التأكد أن الحساب تابع لنفس الشركة وليس Group.
    """
    if not account:
        return False

    account_data = frappe.db.get_value(
        "Account",
        account,
        ["company", "is_group"],
        as_dict=True,
    )

    if not account_data:
        return False

    if account_data.company != company:
        return False

    if account_data.is_group:
        return False

    return True
def get_company_default_payable_account(company: str) -> str | None:
    if not company:
        return None

    company_doc = frappe.get_cached_doc("Company", company)

    for field_name in [
        "default_payroll_payable_account",
        "payroll_payable_account",
        "default_payable_account",
    ]:
        if hasattr(company_doc, field_name):
            field_value = getattr(company_doc, field_name)
            if field_value:
                return field_value

    return None


def get_company_employee_advance_account(company: str) -> str | None:
    if not company:
        return None

    company_doc = frappe.get_cached_doc("Company", company)

    for field_name in [
        "default_employee_advance_account",
        "default_receivable_account",
        "default_payable_account",
    ]:
        if hasattr(company_doc, field_name):
            field_value = getattr(company_doc, field_name)
            if field_value:
                return field_value

    return None


def get_latest_salary_structure_assignment(employee: str, as_of_date):
    assignment_name = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": employee,
            "docstatus": 1,
            "from_date": ("<=", as_of_date),
        },
        "name",
        order_by="from_date desc",
    )
    if not assignment_name:
        frappe.throw(
        _("No active Salary Structure Assignment found for employee {0}. Please create and submit a Salary Structure Assignment before creating the Full and Final Statement.").format(employee)
    )
    
    

    log_trace("salary assignment found", assignment_name)
    return frappe.get_doc("Salary Structure Assignment", assignment_name)


def get_salary_currency_from_assignment(assignment):
    if not assignment:
        return None

    if getattr(assignment, "currency", None):
        return assignment.currency

    salary_structure = getattr(assignment, "salary_structure", None)
    if not salary_structure:
        return None

    return frappe.db.get_value("Salary Structure", salary_structure, "currency")


def get_salary_breakdown(assignment) -> dict:
    if not assignment:
        return {
            "basic": 0,
            "housing": 0,
            "transportation": 0,
            "other": 0,
            "monthly_total": 0,
        }

    basic_salary = flt(getattr(assignment, "base", 0))
    housing = flt(getattr(assignment, "custom_housing", 0))
    transportation = flt(getattr(assignment, "custom_travelling", 0))
    other = flt(getattr(assignment, "custom_other_allowance", 0))

    return {
        "basic": basic_salary,
        "housing": housing,
        "transportation": transportation,
        "other": other,
        "monthly_total": flt(basic_salary + housing + transportation + other, 2),
    }
    
def get_settings_field_value(company: str, fieldname: str, default_value: str = "") -> str:
    settings_doc = get_settings_doc(company)

    if not settings_doc:
        return default_value

    value = getattr(settings_doc, fieldname, None)

    if value is None:
        return default_value

    return str(value).strip()
def get_default_cost_center(company: str) -> str | None:
    """
    جلب Cost Center الافتراضي من Full and Final Settings.
    إذا لم يكن موجودًا، نحاول جلب Cost Center من Company.
    """
    if not company:
        return None

    settings_doc = get_settings_doc(company)

    if settings_doc and getattr(settings_doc, "custom_default_cost_center", None):
        return settings_doc.custom_default_cost_center

    return frappe.db.get_value("Company", company, "cost_center")