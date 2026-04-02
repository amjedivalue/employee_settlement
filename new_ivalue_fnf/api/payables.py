from frappe.utils import flt


def build_payables_rows(salary_info, leave_rows, payable_account):
    rows = []
    total = 0

    salary_amount = flt(salary_info["amount"])
    worked_days = flt(salary_info["worked_days"], 2)

    if salary_amount > 0:
        rows.append({
            "component": "Salary days",
            "reference_document_type": "Salary Structure Assignment",
            "reference_document": salary_info["assignment_name"],
            "account": payable_account,
            "amount": salary_amount,
            "status": "Settled",
            "custom_number_of_days": flt(worked_days, 2),
        })
        total += salary_amount

    daily_rate = flt(salary_info["daily_rate"])

    for leave_row in leave_rows:
        leave_days = flt(leave_row.get("balance"), 2)
        leave_amount = flt(leave_days * daily_rate, 2)

        if leave_days <= 0 or leave_amount <= 0:
            continue

        rows.append({
            "component": leave_row["leave_type"],
            "reference_document_type": "Leave Allocation",
            "reference_document": leave_row["allocation_ref"],
            "account": payable_account,
            "amount": leave_amount,
            "status": "Settled",
            "custom_number_of_days": flt(leave_days, 2),
        })
        total += leave_amount

    return rows, flt(total, 2)