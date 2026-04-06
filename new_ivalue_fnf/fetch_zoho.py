import frappe 
from custody.employee_custody.ZOHO.Zoho_api import Zoho_api


def fetch_zoho_doc():
    get_all_sigend_fnf  = frappe.db.sql(''' 
                                                SELECT 
                                                    fnf.`name`,
                                                    fnf.zoho_id
                                                FROM `tabFull and Final Statement` AS fnf
                                                LEFT JOIN `tabCustody Status` AS cs
                                                    ON cs.parent = fnf.name
                                                LEFT JOIN `tabFile` as f
                                                ON f.attached_to_name = fnf.name 
                                                WHERE 
                                                    fnf.`zoho_id` IS NOT NULL
                                                    AND fnf.`docstatus` = 1
                                                    AND f.name is NULL
                                            ''', (), as_dict=True)
    if get_all_sigend_fnf:
        for custody in get_all_sigend_fnf:
            zoho = Zoho_api(doctype = 'Full and Final Statement', name = custody.name, status_child_table_name = "Custody Status", zoho_id = custody.zoho_id)
            zoho_status = zoho.fetch_zoho_status()


def update_workfow_status(doc):
    doc = frappe.get_doc('Full and Final Statement', name)
    count_all_sign = len([row for row in doc.custom_zoho_status if row.action_type == "SIGN"])
    get_all_siged_doc = len([row for row in doc.custom_zoho_status if row.action_type == "SIGNED"])
    if count_all_sign == get_all_siged_doc and count_all_sign != 0 and doc.status == "Received":
        frappe.db.set_value('Full and Final Statement', name, 'workflow_state', 'Signed')
        frappe.db.commit()