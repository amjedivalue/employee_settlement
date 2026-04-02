import frappe
from frappe.utils import flt, get_first_day, getdate
from new_ivalue_fnf.api import date_utils
def get_personal_leave_days_by_type(employee: str, end_date) -> dict:
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

        hours = flt(row.get("hours"))
        days = flt(hours / 8, 2)

        if leave_type not in leave_days_by_type:
            leave_days_by_type[leave_type] = 0.0

        leave_days_by_type[leave_type] += days

    return leave_days_by_type

def compute_carry_forward_leave_rows(employee: str, start_date, end_date) -> list[dict]:
    rows = []
    personal_leave_days_by_type = get_personal_leave_days_by_type(employee, end_date)
    carry_forward_leave_types = frappe.get_all(
        "Leave Type",
        filters={"is_carry_forward": 1},
        pluck="name"
    )

    for leave_type in carry_forward_leave_types:
        latest_allocation = frappe.get_all(
            "Leave Allocation",
            filters={
                "employee": employee,
                "leave_type": leave_type,
                "docstatus": 1,
                "from_date": ("<=", end_date),
              
            },
            fields=["name", "from_date", "to_date", "total_leaves_allocated", "extra_days"],
             order_by="from_date desc, to_date desc, modified desc",
    limit=1,
        )

        if not latest_allocation:
            continue

        alloc = latest_allocation[0]
        earned = flt(alloc.get("total_leaves_allocated")) + flt(alloc.get("extra_days"))
        allocation_ref = alloc.get("name")
        allocation_start = alloc.get("from_date")
        

        leave_applications = frappe.get_all(
            "Leave Application",
            filters={
                "employee": employee,
                "leave_type": leave_type,
                "docstatus": 1,
                "status": "Approved",
                "from_date": ("<=", end_date),
                "to_date": (">=", allocation_start),            },
            fields=["from_date", "to_date", "total_leave_days"],
        )

        taken = 0.0
        for app in leave_applications:
            overlap_days = date_utils.overlap_inclusive_days(
            app.from_date, app.to_date, allocation_start, end_date
            )
            total_days = date_utils.inclusive_days(app.from_date, app.to_date)

            if total_days > 0:
                taken += flt(app.total_leave_days) * (flt(overlap_days) / flt(total_days))
        # from personal leave
        taken += flt(personal_leave_days_by_type.get(leave_type, 0))

        balance = flt(earned - taken, 2)
        if balance <= 0:
            continue
        rows.append({
            "leave_type": leave_type,
            "earned": flt(earned, 2),
            "taken": flt(taken, 2),
            "balance": flt(balance,2),
            "allocation_ref": allocation_ref,
        })
        

    return rows
