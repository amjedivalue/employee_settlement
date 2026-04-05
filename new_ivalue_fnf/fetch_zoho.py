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
                                                ON f.attached_to_name = ec.name 
                                                WHERE 
                                                    fnf.`zoho_id` IS NOT NULL
                                                    AND fnf.`docstatus` = 1
                                                    AND f.name is NULL
                                            ''', (), as_dict=True)
    if get_all_sigend_custody:
        for custody in get_all_sigend_custody:
            zoho = Zoho_api(doctype = 'Full and Final Statement', name = custody.name, status_child_table_name = "Custody Status", zoho_id = custody.zoho_id)
            zoho_status = zoho.fetch_zoho_status()