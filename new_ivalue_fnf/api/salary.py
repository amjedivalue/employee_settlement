from frappe import _
import frappe
from frappe.utils import flt, getdate
from new_ivalue_fnf.api import date_utils

#ss
def fetch_latest_salary_assignment(employee: str, as_of_date):
    name = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": employee,
            "docstatus": 1,
            "from_date": ("<=", as_of_date),
        },
        "name",
        order_by="from_date desc",
    )
    return frappe.get_doc("Salary Structure Assignment", name) if name else None

def get_salary_assignment_currency(assignment):
    if not assignment:
        return None

    # إذا العملة موجودة مباشرة على SSA
    currency = getattr(assignment, "currency", None)
    if currency:
        return currency

    # fallback من Salary Structure
    salary_structure = getattr(assignment, "salary_structure", None)
    if salary_structure:
        currency = frappe.db.get_value("Salary Structure", salary_structure, "currency")
        if currency:
            return currency

    return None
def build_salary_breakdown(assignment) -> dict:
    if not assignment:
        return {
            "basic": 0,
            "housing": 0,
            "traveling": 0,
            "other": 0,
            "monthly_total": 0,
        }

    basic = flt(getattr(assignment, "base", 0))
    housing = flt(getattr(assignment, "custom_housing", 0))
    traveling = flt(getattr(assignment, "custom_travelling", 0))
    other = flt(getattr(assignment, "custom_other_allowance", 0))

    return {
        "basic": basic,
        "housing": housing,
        "traveling": traveling,
        "other": other,
        "monthly_total": flt(basic + housing + traveling + other),
    }


def compute_last_month_prorated_salary(employee: str, join_date, relieving_date) -> dict:
    assignment = fetch_latest_salary_assignment(employee, relieving_date)
    if not assignment:
        frappe.throw(
    _("No Salary Structure Assignment found for this employee. Please go to Salary Structure Assignment and create one.")
)
    breakdown = build_salary_breakdown(assignment)
    monthly_total = flt(breakdown["monthly_total"])
    currency = get_salary_assignment_currency(assignment)

    period_start = date_utils.month_first_day(relieving_date)
    month_days = date_utils.days_in_month(relieving_date)

    if join_date and getdate(join_date) > period_start:
        period_start = getdate(join_date)

    worked_days = date_utils.inclusive_days(period_start, relieving_date)
   
    # dim = date_utils.days_in_month(relieving_date)
    daily_rate = flt(monthly_total / 30, 2)

  
    if worked_days >= month_days:
        amount = flt(monthly_total, 2)
    else:
        amount = flt(worked_days * daily_rate, 2)

    return {
        "assignment_name": assignment.name,
        "currency": currency,
        "worked_days": flt(worked_days, 2),
        "daily_rate": flt(daily_rate, 2),
        "amount": amount,
        "breakdown": breakdown,
    }