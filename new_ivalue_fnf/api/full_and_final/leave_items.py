import frappe
from frappe.utils import flt, get_first_day, getdate

from new_ivalue_fnf.api.full_and_final.settlement_builders import append_row

from new_ivalue_fnf.api.full_and_final.core_data import (
    get_component_setting_for_company,
    get_settings_field_value,
)
def log_trace(message: str, data=None):
    print(f"[FNF leave_items] {message} | {data}")


def get_personal_leave_days_by_type(employee: str, end_date) -> dict:
    if not employee or not end_date:
        return {}

    month_start = get_first_day(getdate(end_date))

    personal_leaves = frappe.get_all(
        "Personal Leave",
        filters={
            "employee": employee,
            "date": ["between", [month_start, end_date]],
            "docstatus": 1,
        },
        fields=["leave_type", "hours"],
    )

    leave_days_by_type = {}

    for row in personal_leaves:
        leave_type = row.get("leave_type")
        if not leave_type:
            continue

        days = flt(flt(row.get("hours")) / 8, 2)

        if leave_type not in leave_days_by_type:
            leave_days_by_type[leave_type] = 0.0

        leave_days_by_type[leave_type] = flt(leave_days_by_type[leave_type] + days, 2)

    log_trace("personal leave types counted", leave_days_by_type)
    return leave_days_by_type


def get_carry_forward_leave_types():
    return frappe.get_all(
        "Leave Type",
        filters={"is_carry_forward": 1},
        pluck="name",
    )


def get_latest_leave_allocation(employee: str, leave_type: str, end_date):
    rows = frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": employee,
            "leave_type": leave_type,
            "docstatus": 1,
            "from_date": ("<=", end_date),
        },
        fields=[
            "name",
            "from_date",
            "to_date",
            "total_leaves_allocated",
            "extra_days",
        ],
        order_by="from_date desc, to_date desc, modified desc",
        limit=1,
    )

    if not rows:
        return None

    return rows[0]


def get_overlap_days(app_from_date, app_to_date, range_start, range_end) -> int:
    overlap_start = max(getdate(app_from_date), getdate(range_start))
    overlap_end = min(getdate(app_to_date), getdate(range_end))

    if overlap_end < overlap_start:
        return 0

    return (overlap_end - overlap_start).days + 1


def get_total_days(from_date, to_date) -> int:
    start_date = getdate(from_date)
    end_date = getdate(to_date)

    if end_date < start_date:
        return 0

    return (end_date - start_date).days + 1


def get_leave_taken_days(employee: str, leave_type: str, allocation_start, end_date, personal_leave_days_by_type: dict) -> float:
    leave_applications = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee,
            "leave_type": leave_type,
            "docstatus": 1,
            "status": "Approved",
            "from_date": ("<=", end_date),
            "to_date": (">=", allocation_start),
        },
        fields=["from_date", "to_date", "total_leave_days"],
    )

    taken = 0.0

    for app in leave_applications:
        overlap_days = get_overlap_days(
            app.from_date,
            app.to_date,
            allocation_start,
            end_date,
        )
        total_days = get_total_days(app.from_date, app.to_date)

        if total_days > 0 and overlap_days > 0:
            taken += flt(app.total_leave_days) * (flt(overlap_days) / flt(total_days))

    taken += flt(personal_leave_days_by_type.get(leave_type, 0))
    return flt(taken, 2)


def build_leave_encashment_rows(doc):
    setting_row = get_component_setting_for_company(doc.company, "Leaves")

    if not setting_row or not setting_row.is_enabled:
        log_trace("leave encashment skipped because disabled")
        return

    personal_leave_days_by_type = get_personal_leave_days_by_type(doc.employee, doc.relieving_date)
    carry_forward_leave_types = get_carry_forward_leave_types()
    daily_rate = flt(flt(doc.custom_monthly_gross_salary) / 30, 2)

    for leave_type in carry_forward_leave_types:
        allocation = get_latest_leave_allocation(doc.employee, leave_type, doc.relieving_date)

        if not allocation:
            continue

        earned = flt(allocation.total_leaves_allocated) + flt(allocation.extra_days)
        taken = get_leave_taken_days(
            doc.employee,
            leave_type,
            allocation.from_date,
            doc.relieving_date,
            personal_leave_days_by_type,
        )
        balance = flt(earned - taken, 2)

        if balance <= 0:
            continue

        amount = flt(balance * daily_rate, 2)
        component_label = setting_row.display_name or "Leaves"
        leave_format = get_settings_field_value(doc.company, "leave_format", "New Name")

        if leave_format == "Leave Type- New Name":
            component_label = f"{leave_type} - {component_label}"
        elif leave_format == "New Name - Leave Type":
            component_label = f"{component_label} - {leave_type}"

        append_row(
            doc=doc,
            table_field="payables",
            component=component_label,
            amount=amount,
            account=setting_row.account,
            reference_document_type="Leave Allocation",
            reference_document=allocation.name,
            custom_number_of_days=balance,
        )

        if hasattr(doc, "custom_carry_forward_leaves"):
            leave_row = doc.append("custom_carry_forward_leaves", {})
            leave_row.leave_type = leave_type
            leave_row.earned_leaves = flt(earned, 2)
            leave_row.taken_leaves = flt(taken, 2)
            leave_row.remaining_leaves = flt(balance, 2)

        log_trace("leave encashment row added", {
            "leave_type": leave_type,
            "balance": balance,
            "amount": amount,
        })