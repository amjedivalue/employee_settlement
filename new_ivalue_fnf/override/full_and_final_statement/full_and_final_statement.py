import frappe
from custody.employee_custody.ZOHO.Zoho_api import Zoho_api







# check on the separation if it is submited
@frappe.whitelist()
def check_if_separation_is_submited(name):
    doc = frappe.get_doc("Full and Final Statement", name)

    if not frappe.db.exists("Employee Separation", doc.custom_employee_separation):
        return {'status': 404, "message":"separation not found"}

    spearation_docStatus = frappe.db.get_value("Employee Separation", doc.custom_employee_separation, "docstatus")
    
    return {'status': 200, "message":"data fetched successfully", "data": spearation_docStatus}

        






@frappe.whitelist()
def add_assigened_to(name, workflow_state):
    status = ""
    match (workflow_state):
        case "Pending Finance Director":
            status = "Accounts Manager"
        case "Pending Supporting Services Directorr":
            status = "Supporting Services Director"
        case "HR Manager":
            status = "HR Manager"



	 # Get all users who have this role
    users = frappe.db.sql(
        """
        SELECT DISTINCT hr.parent AS user_id
        FROM `tabHas Role` hr
        JOIN `tabUser` u ON u.name = hr.parent
        WHERE hr.role = %s
        AND hr.parenttype = 'User'
        AND u.enabled = 1
        AND u.user_type = 'System User'
        AND u.name != 'Administrator'
        """,
        (status,),
        as_dict=True,
    )
    status = ["Open", "Pending"]

    for item in users:
        user_id = item["user_id"]
        
        # Check if ToDo already exists and is still open/pending
        exists = frappe.db.exists(
            "ToDo",
            {
                "reference_type": "Full and Final Statement",
                "reference_name": name,
                "allocated_to": user_id,
                "status": ("in", status),
            },
        )

        if not exists:
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "allocated_to": user_id,
                    "reference_type": "Full and Final Statement",
                    "reference_name": name,
                    "description": f"Please Approve Full and Final  {name}",
                    "priority": "High",
                    "status": "Open",
                    "date": frappe.utils.today(),
                }
            )
            todo.insert(ignore_permissions=True)
            # frappe.share.add(
            #     "Self Service",
            #     name,
            #     user_id,
            #     read=1,
            #     write=1,
            #     submit = 1,
            #     share=1,
            # )
    return{'status': 201, 'message': "to do has been added successfully"}





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
        update_workfow_status(doc)
        return {'status': 200, 'message': "status has been updated successfully"}



def cancel_doc_type(name):
    update_workflow_status = frappe.db.set_value('Full and Final Statement', name, 'workflow_state', 'Cancel')
    frappe.db.commit()

def update_workfow_status(doc):
    count_all_sign = len([row for row in doc.custom_zoho_status if row.action_type == "SIGN"])
    get_all_siged_doc = len([row for row in doc.custom_zoho_status if row.action_type == "SIGNED"])
    if count_all_sign == get_all_siged_doc and count_all_sign != 0 and doc.status == "Received":
        frappe.db.set_value('Full and Final Statement', name, 'workflow_state', 'Signed')
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
