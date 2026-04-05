import frappe
from custody.employee_custody.ZOHO.Zoho_api import Zoho_api







@frappe.whitelist()
def cancel_zoho_doc(name):
    doc = frappe.get_doc('Full and Final Statement', name)
    zoho = Zoho_api(doctype = 'Full and Final Statement', name = doc.name, status_child_table_name = "Custody Status", zoho_id = doc.zoho_id)
    zoho_remove = zoho.remove_custody()
    if zoho_remove['status'] == 200:
        cancel_doc_type(name)
        return {'status': 201 , 'message': "recoreds has been deleted successfully"}
    else:
        return{'status': zoho_remove['status'], 'message': zoho_remove['message']} 



@frappe.whitelist()
def fetch_zoho_doc(name):
    doc = frappe.get_doc('Full and Final Statement', name)

    zoho = Zoho_api(doctype = 'Full and Final Statement', name = doc.name, status_child_table_name = "Custody Status", zoho_id = doc.zoho_id)
    zoho_status = zoho.fetch_zoho_status()
    if zoho_status['status'] == 200:
        update_workfow_status(name)
        return {'status': 200, 'message': "status has been updated successfully"}



def cancel_doc_type(name):
    update_workflow_status = frappe.db.set_value('Full and Final Statement', name, 'workflow_state', 'Cancel')
    frappe.db.commit()

def update_workfow_status(name):
    update_workflow_status = frappe.db.set_value('Full and Final Statement', name, 'workflow_state', 'Signed')
    frappe.db.commit()

@frappe.whitelist()
def upload_on_zoho(name):
    doc = frappe.get_doc("Full and Final Statement", name)

    # user_id, employee_full_name, company = frappe.db.get_value('Employee', employee, ["user_id", "employee_name", "company"])
    copmany_cuontry = ""
    if not doc.custom_user_id:
        frappe.throw('please fill add user id to the employee')
    actions = [
        {
                    "recipient_name": f'{doc.employee_name}',
                    "recipient_email": f"{doc.custom_user_id}",
                    "action_type": "SIGN",
                    "signing_order": 0,
        } 
    ]
    match doc.company:
        case "iValueJOR":
            copmany_cuontry = "JOR"
        case "iValue KSA":
            copmany_cuontry = "KSA"
        case "iValueUAE":
            copmany_cuontry = "UAE"
    
    zoho_documnt_name = f"Full and final statmet - {doc.employee_name} - {doc.name}"
    child_table = "custom_zoho_status"
    zoho = Zoho_api(doctype = 'Full and Final Statement', name = doc.name, print_foramt_name = "Custom Full and Final Statement", actions = actions, zoho_doc_name = zoho_documnt_name, company = doc.company, status_child_table_name = child_table)
    upload_zoho_doc = zoho.create_zoho_documnt()
    if upload_zoho_doc['status'] == 201:
        return {'status': 201, 'message': "Zoho documnt has been uploaded successfully"}
    else:
         frappe.throw(upload_zoho_doc['message'])
