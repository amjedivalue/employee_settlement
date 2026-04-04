import frappe

def execute():
    frappe.make_property_setter({
        "doctype": "Full and Final Statement",
        "fieldname": "total_payable_amount",
        "property": "options",
        "value": "custom_company_currency",
        "property_type": "Data",
    })

    frappe.make_property_setter({
        "doctype": "Full and Final Statement",
        "fieldname": "total_receivable_amount",
        "property": "options",
        "value": "custom_company_currency",
        "property_type": "Data",
    })
    frappe.make_property_setter({
        "doctype": "Full and Final Outstanding Statement",
        "fieldname": "amount",
        "property": "options",
        "value": "custom_company_currency",
        "property_type": "Data",
    })


    frappe.db.commit()


