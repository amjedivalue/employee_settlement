
# =========================================================
# SERVICE
# =========================================================
from frappe.utils import flt, getdate, relativedelta


def compute_service_period(join_date, relieving_date) -> dict:
    start = getdate(join_date)
    end = getdate(relieving_date)
    diff = relativedelta(end + relativedelta(days=1), start)
    total_days = (end - start).days + 1
    return {
        "years": diff.years,
        "months": diff.months,
        "days": diff.days,
        "total_years": flt(total_days / 365, 3),
    }

