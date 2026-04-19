frappe.ui.form.on("Full and Final Statement", {
  onload(frm) {

    
    if (!frm.doc.transaction_date) {
      frm.set_value("transaction_date", frappe.datetime.get_today());
    }
    if(frm.doc.workflow_state === "Employee Sigen"){
      fetch_zoho_doc(frm)  
    }

    clear_placeholder_rows(frm);
   
  },

  refresh(frm) {
    clear_placeholder_rows(frm);
     add_full_and_final_settings_button(frm);
  },

employee(frm) {
    if (!frm.doc.employee) {
        clear_employee_related_data(frm);
        return;
    }

    frappe.dom.freeze(__("Loading employee details..."));

    setTimeout(() => {
        clear_placeholder_rows(frm);
        frappe.dom.unfreeze();
    }, 1200);
},

  relieving_date(frm) {
    clear_placeholder_rows(frm);
  },

validate(frm) {
    clear_placeholder_rows(frm);

    if (frm.doc.employee) {

        if (!frm.doc.custom_user_id || !frm.doc.relieving_date) {

            frappe.msgprint({
                title: __("Please Wait"),
                message: __("Employee data is still loading. Please save again in one second."),
                indicator: "orange"
            });

            frappe.validated = false;
            return;
        }
    }
},
  after_workflow_action:async function(frm){
    if(frm.doc.workflow_state === "Employee Sigen"){
      upload_on_zoho(frm)
    }
  },
  before_cancel:function(frm){
    remove_custody(frm)
  },
  after_workflow_action:function(frm){
       if (frm.doc.workflow_state !== "Employee Sigen" && frm.doc.workflow_state !== "HR User" ){
            add_to_do(frm)
        }
  }
});

function clear_employee_related_data(frm) {
  // Parent fields
  frm.set_value("employee_name", "");
  frm.set_value("company", "");
  frm.set_value("department", "");
  frm.set_value("designation", "");
  frm.set_value("date_of_joining", "");
  frm.set_value("relieving_date", "");
  frm.set_value("transaction_date", "");

  // Salary / summary fields
  frm.set_value("custom_company_currency", "");
  frm.set_value("custom_letter_head", "");
  frm.set_value("custom_basic_salary", 0);
  frm.set_value("custom_housing", 0);
  frm.set_value("custom_transportation", 0);
  frm.set_value("custom_other_allowances", 0);
  frm.set_value("custom_monthly_gross_salary", 0);

  // Service fields
  frm.set_value("custom_service_years", 0);
  frm.set_value("custom_service_month", 0);
  frm.set_value("custom_service_days", 0);
  frm.set_value("custom_total_of_years", 0);

  // Totals
  frm.set_value("total_payable_amount", 0);
  frm.set_value("total_receivable_amount", 0);
  frm.set_value("total_asset_recovery_cost", 0);


  // Child tables
  frm.clear_table("payables");
  frm.clear_table("receivables");
  frm.clear_table("assets_allocated");

  if (frm.fields_dict.custom_carry_forward_leaves) {
    frm.clear_table("custom_carry_forward_leaves");
    frm.refresh_field("custom_carry_forward_leaves");
  }

  frm.refresh_field("payables");
  frm.refresh_field("receivables");
  frm.refresh_field("assets_allocated");
}
function add_to_do(frm){
    frappe.call({
        method:"new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.add_assigened_to",
        args:{name:frm.doc.name, workflow_state:frm.doc.workflow_state},
        freeze:true,
        freeze_message: __("Add to do..."),
        callback:function(response){
            if(response.message.status === 201){
                 frappe.show_alert({
                    message: __("To do has been added successfully"),
                    indicator: "green"
                });
                frm.reload_doc();
            }
        }
    })
}

function remove_custody(frm){
  frappe.call({
    method:"new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.cancel_zoho_doc",
    args:{name:frm.doc.name},
    freeze: true,
    freeze_message:("cancel zoho doc..."),
    callback:function(response){
      if(response.message.status === 200){
         frappe.show_alert({
                    message: __(response.message.message),
                    indicator: "green"
          });
          frm.reload_doc();
      }
    }
  })
}


function upload_on_zoho(frm){
  frappe.call({
    method:"new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.upload_on_zoho",
    args:{name:frm.doc.name},
    freeze: true,
    freeze_message:("Upload on zoho..."),
    callback:function(response){
      if(response.message.status === 201){
         frappe.show_alert({
                    message: __(response.message.message),
                    indicator: "green"
          });
          frm.reload_doc();
      }
    }
  })
}

function fetch_zoho_doc(frm){
  frappe.call({
    method:"new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.fetch_zoho_doc",
    args:{name:frm.doc.name},
    freeze: true,
    freeze_message:("fetch zoho doc..."),
    callback:function(response){
      if(response.message.status === 200){
         frappe.show_alert({
                    message: __(response.message.message),
                    indicator: "green"
          });
      }
  }
})
}


function clear_placeholder_rows(frm) {
  frm.doc.payables = (frm.doc.payables || []).filter((row) => {
    const isPlaceholder =
      !row.reference_document &&
      Number(row.amount || 0) === 0;

    return !isPlaceholder;
  });

  frm.doc.receivables = (frm.doc.receivables || []).filter((row) => {
    const isPlaceholder =
      !row.reference_document &&
      Number(row.amount || 0) === 0;

    return !isPlaceholder;
  });

  frm.refresh_field("payables");
  frm.refresh_field("receivables");
}



// زر الاعدادات 
function add_full_and_final_settings_button(frm) {
    let button_label = "Full and Final Settings";

    if (frm.custom_buttons && frm.custom_buttons[button_label]) {
        return;
    }

    frm.add_custom_button(button_label, function () {
        open_full_and_final_settings(frm);
    });
}
function open_full_and_final_settings(frm) {
    frappe.set_route("List", "Full and Final Settings");
}
