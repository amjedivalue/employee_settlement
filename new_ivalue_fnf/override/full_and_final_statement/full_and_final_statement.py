import frappe
from custody.employee_custody.ZOHO.Zoho_api import Zoho_api

# =====================================================
#  amjed  tamimi  extention after  khaled Jallad
# =====================================================
from frappe.utils.file_manager import save_file

EMPLOYEE_SEPARATION_PRINT_FORMAT = "custom print ES"
# ================amjed  tamimi=====================================


# check on the separation if it is submited
@frappe.whitelist()
def check_if_separation_is_submited(name):
    doc = frappe.get_doc("Full and Final Statement", name)

    if not frappe.db.exists("Employee Separation", doc.custom_employee_separation):
        return {"status": 404, "message": "separation not found"}

    spearation_docStatus = frappe.db.get_value(
        "Employee Separation", doc.custom_employee_separation, "docstatus"
    )

    return {
        "status": 200,
        "message": "data fetched successfully",
        "data": spearation_docStatus,
    }


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
    return {"status": 201, "message": "to do has been added successfully"}


@frappe.whitelist()
def cancel_zoho_doc(name):
    doc = frappe.get_doc("Full and Final Statement", name)
    zoho = Zoho_api(
        doctype="Full and Final Statement",
        name=doc.name,
        status_child_table_name="Custody Status",
        zoho_id=doc.zoho_id,
    )
    zoho_remove = zoho.remove_custody()
    if zoho_remove["status"] == 200:
        cancel_doc_type(name)
        return {"status": 201, "message": "recoreds has been deleted successfully"}
    else:
        return {"status": zoho_remove["status"], "message": zoho_remove["message"]}


@frappe.whitelist()
def fetch_zoho_doc(name):
    doc = frappe.get_doc("Full and Final Statement", name)

    zoho = Zoho_api(
        doctype="Full and Final Statement",
        name=doc.name,
        status_child_table_name="Custody Status",
        zoho_id=doc.zoho_id,
    )
    zoho_status = zoho.fetch_zoho_status()
    if zoho_status["status"] == 200:
        update_workfow_status(doc, zoho_status["zoho_status"])
        return {"status": 200, "message": "status has been updated successfully"}


def cancel_doc_type(name):
    update_workflow_status = frappe.db.set_value(
        "Full and Final Statement", name, "workflow_state", "Cancel"
    )
    frappe.db.commit()


def update_workfow_status(doc, zoho_status):
    if zoho_status == "completed":
        frappe.db.set_value(
            "Full and Final Statement", doc.name, "workflow_state", "Signed"
        )
        frappe.db.commit()
        return "completed"
    elif zoho_status == "declined":
        frappe.db.set_value(
            "Full and Final Statement",
            doc.name,
            "workflow_state",
            "Pending Supporting Services Director",
        )
        frappe.db.set_value("Full and Final Statement", doc.name, "zoho_id", "")
        frappe.db.set_value("Full and Final Statement", doc.name, "docstatus", 0)
        frappe.db.commit()
        return "declined"


@frappe.whitelist()
def upload_on_zoho(name):
    doc = frappe.get_doc("Full and Final Statement", name)

    # user_id, employee_full_name, company = frappe.db.get_value('Employee', employee, ["user_id", "employee_name", "company"])
    copmany_cuontry = ""
    if not doc.custom_user_id:
        frappe.throw("please fill add user id to the employee")
    actions = [
        {
            "recipient_name": f"{doc.employee_name}",
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
    zoho = Zoho_api(
        doctype="Full and Final Statement",
        name=doc.name,
        print_foramt_name="Custom Full and Final Statement",
        actions=actions,
        zoho_doc_name=zoho_documnt_name,
        company=doc.company,
        status_child_table_name=child_table,
    )
    upload_zoho_doc = zoho.create_zoho_documnt()
    if upload_zoho_doc["status"] == 201:
        return {"status": 201, "message": "Zoho documnt has been uploaded successfully"}
    else:
        frappe.throw(upload_zoho_doc["message"])


# =====================================================
#  amjed  tamimi  extention after  khaled Jallad
# =====================================================


def get_submitted_employee_separation_for_full_and_final(full_and_final_doc):
    # Find and validate the submitted Employee Separation linked to this Full and Final Statement.

    if not full_and_final_doc.employee:
        frappe.throw("Employee is required before syncing Employee Separation PDF")

    if full_and_final_doc.custom_employee_separation:
        separation_name = full_and_final_doc.custom_employee_separation

        if not frappe.db.exists("Employee Separation", separation_name):
            frappe.throw("Linked Employee Separation does not exist")

        separation_employee, separation_docstatus = frappe.db.get_value(
            "Employee Separation", separation_name, ["employee", "docstatus"]
        )

        if separation_employee != full_and_final_doc.employee:
            frappe.throw("Linked Employee Separation belongs to a different employee")

        if separation_docstatus != 1:
            frappe.throw(
                "Employee Separation must be submitted before syncing the clearance PDF"
            )

        return separation_name

    separation_name = frappe.db.get_value(
        "Employee Separation",
        {"employee": full_and_final_doc.employee, "docstatus": 1},
        "name",
        order_by="modified desc",
    )

    if not separation_name:
        frappe.throw("No submitted Employee Separation found for this employee")

    full_and_final_doc.db_set(
        "custom_employee_separation", separation_name, update_modified=False
    )

    return separation_name


@frappe.whitelist()
def sync_employee_separation_attachments_to_full_and_final(name):
    # Temporary connection test only.
    # Real PDF generation logic will be added step by step.
    if not name:
        frappe.throw("Full and Final Statement name is required")

    doc = frappe.get_doc("Full and Final Statement", name)
    employee_separation = get_submitted_employee_separation_for_full_and_final(doc)
    file_name = build_employee_separation_pdf_file_name(employee_separation)

    existing_file = get_existing_employee_separation_pdf_file(doc.name, file_name)
    if existing_file:
        return {
            "status": 200,
            "message": f"Employee Separation PDF already exists: {file_name}",
            "full_and_final": doc.name,
            "employee": doc.employee,
            "employee_separation": employee_separation,
            "file_name": file_name,
            "file": existing_file,
        }
    created_file = generate_and_attach_employee_separation_pdf(
    doc,
    employee_separation,
    file_name
)
    return {
        "status": 201,
        "message": f"Employee Separation PDF attached successfully: {file_name}",
        "full_and_final": doc.name,
        "employee": doc.employee,
        "employee_separation": employee_separation,
        "file_name": file_name,
        "file": created_file,
    }


def build_employee_separation_pdf_file_name(employee_separation_name):
    # Build a stable file name to prevent duplicate PDF attachments.
    return f"Employee-Separation-{employee_separation_name}.pdf"


def get_existing_employee_separation_pdf_file(full_and_final_name, file_name):
    # Check if the Employee Separation PDF is already attached to this Full and Final Statement.
    # Frappe may append a small hash before the file extension when saving files.

    file_base_name = file_name.replace(".pdf", "")

    attached_files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Full and Final Statement",
            "attached_to_name": full_and_final_name,
        },
        fields=[
            "name",
            "file_name",
            "file_url"
        ],
        order_by="creation asc"
    )

    for attached_file in attached_files:
        current_file_name = attached_file.get("file_name") or ""
        current_file_url = attached_file.get("file_url") or ""

        if current_file_name == file_name:
            return attached_file.name

        if current_file_url.endswith("/" + file_name) or current_file_url.endswith(file_name):
            return attached_file.name

        if current_file_name.startswith(file_base_name) and current_file_name.endswith(".pdf"):
            return attached_file.name

        if current_file_url.endswith(".pdf") and file_base_name in current_file_url:
            return attached_file.name

    return None
def generate_and_attach_employee_separation_pdf(
    full_and_final_doc, employee_separation_name, file_name
):
    # Generate Employee Separation clearance PDF and attach it to Full and Final Statement.

    pdf_content = frappe.get_print(
        "Employee Separation",
        employee_separation_name,
        print_format=EMPLOYEE_SEPARATION_PRINT_FORMAT,
        as_pdf=True,
    )

    saved_file = save_file(
        fname=file_name,
        content=pdf_content,
        dt="Full and Final Statement",
        dn=full_and_final_doc.name,
        is_private=1,
    )

    return saved_file.name
    # ================amjed  tamimi=====================================
