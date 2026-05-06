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
            update_workfow_status(custody.name ,zoho_status['zoho_status'])


def update_workfow_status(name, zoho_status):
    doc = frappe.get_doc('Full and Final Statement', name)
    
    if zoho_status == "completed":
        frappe.db.set_value('Full and Final Statement', name, 'workflow_state', 'Signed')
        frappe.db.commit()
        return "completed"
    elif zoho_status == "declined":
        frappe.db.set_value('Full and Final Statement', name, 'workflow_state', 'Pending Supporting Services Director')
        frappe.db.set_value('Full and Final Statement', name, 'zoho_id', '')
        frappe.db.set_value('Full and Final Statement', name, 'docstatus', 0)
        frappe.db.commit() 
        return "declined"