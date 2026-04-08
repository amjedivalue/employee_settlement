import frappe

def execute():
    # Full and Final Statement
    frappe.db.delete("Property Setter", {
        "doc_type": "Full and Final Statement",
        "field_name": ["in", ["total_payable_amount", "total_receivable_amount"]],
        "property": "options",
    })

    # Child Table
    frappe.db.delete("Property Setter", {
        "doc_type": "Full and Final Outstanding Statement",
        "field_name": "amount",
        "property": "options",
    })

    frappe.db.commit()