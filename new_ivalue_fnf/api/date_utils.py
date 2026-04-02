
# =========================================================
# DATE UTILITIES
# =========================================================

from datetime import date

from frappe.utils import getdate


def inclusive_days(start_date, end_date) -> int:
    if not start_date or not end_date:
        return 0
    start = getdate(start_date)
    end = getdate(end_date)
    if end < start:
        return 0
    return (end - start).days + 1


def month_first_day(any_date) -> date:
    d = getdate(any_date)
    return date(d.year, d.month, 1)


def days_in_month(any_date) -> int:
    d = getdate(any_date)
    first = date(d.year, d.month, 1)
    if d.month == 12:
        next_first = date(d.year + 1, 1, 1)
    else:
        next_first = date(d.year, d.month + 1, 1)
    return (next_first - first).days


def overlap_inclusive_days(a_start, a_end, b_start, b_end) -> int:
    start = max(getdate(a_start), getdate(b_start))
    end = min(getdate(a_end), getdate(b_end))
    return inclusive_days(start, end)

