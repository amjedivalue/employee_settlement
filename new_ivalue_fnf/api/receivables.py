# import frappe
# from frappe.utils import flt
# from . import employee_data


# def build_receivables_from_employee_advances(employee: str, doc):
#     rows = []
#     total = 0.0
#     advances = frappe.get_all(
#         "Employee Advance",
#         filters={"employee": employee, "docstatus": 1},
#         fields=["name", "purpose", "advance_amount", "paid_amount", "claimed_amount", "status"],
#         order_by="posting_date desc",
#     )

#     emp = employee_data.fetch_employee_snapshot(employee)
#     if not emp:
#         frappe.throw("Employee not found.")

#     company = emp.get("company")
#     account = frappe.get_value("Company", company, "default_employee_advance_account")

    


#     for adv in advances:
#         advance_amount = flt(adv.advance_amount)
#         paid_amount = flt(adv.paid_amount)
#         claimed_amount = flt(adv.claimed_amount)

#         outstanding = flt(advance_amount - paid_amount - claimed_amount, 2)
#         if outstanding <= 0:
#             continue

#         if not adv.name:
#             continue

#         doc.append("receivables" ,{
#             "component": "Employee Advance",
#             "reference_document_type": "Employee Advance",
#             "reference_document": adv.name,
#             "account": account,
#             "amount": outstanding,
#             "status": "Settled",
#             "custom_number_of_days": 0,
#         })
#         total += outstanding

#     return rows, flt(total, 2)  


import frappe
from frappe.utils import flt
from . import employee_data


def build_receivables_from_employee_advances(employee: str):
    rows = []
    total = 0.0

    advances = frappe.get_all(
        "Employee Advance",
        filters={"employee": employee, "docstatus": 1},
        fields=["name", "purpose", "advance_amount", "paid_amount", "claimed_amount", "status"],
        order_by="posting_date desc",
    )

    emp = employee_data.fetch_employee_snapshot(employee)
    if not emp:
        frappe.throw("Employee not found.")

    company = emp.get("company")
    account = frappe.get_value("Company", company, "default_employee_advance_account")

    for adv in advances:
        advance_amount = flt(adv.advance_amount)
        paid_amount = flt(adv.paid_amount)
        claimed_amount = flt(adv.claimed_amount)

        outstanding = flt(advance_amount - paid_amount - claimed_amount, 2)
        if outstanding <= 0:
            continue

        if not adv.name:
            continue

        rows.append({
            "component": "Employee Advance" or adv.nam,
            "reference_document_type": "Employee Advance",
            "reference_document": adv.name,
            "account": account,
            "amount":  flt(advance_amount),
            "status": "Settled",
            "custom_number_of_days":0,
        })
        total += outstanding

    return rows, flt(total, 2)  