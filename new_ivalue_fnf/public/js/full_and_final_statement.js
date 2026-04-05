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
  },

  employee(frm) {
    clear_placeholder_rows(frm);
  },

  relieving_date(frm) {
    clear_placeholder_rows(frm);
  },

  validate(frm) {
    clear_placeholder_rows(frm);
  },
  after_workflow_action:async function(frm){
    if(frm.doc.workflow_state === "Employee Sigen"){
      upload_on_zoho(frm)
    }
  },
  before_cancel:function(frm){
    remove_custody(frm)
  }
});


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
  const payablePlaceholders = new Set([
    "Gratuity",
    "Expense Claim",
    "Bonus",
    "Leave Encashment"
  ]);

  const receivablePlaceholders = new Set([
    "Employee Advance"
  ]);

  frm.doc.payables = (frm.doc.payables || []).filter((row) => {
    const isPlaceholder =
      payablePlaceholders.has(row.component) &&
      !row.reference_document &&
      Number(row.amount || 0) === 0;

    return !isPlaceholder;
  });

  frm.doc.receivables = (frm.doc.receivables || []).filter((row) => {
    const isPlaceholder =
      receivablePlaceholders.has(row.component) &&
      !row.reference_document &&
      Number(row.amount || 0) === 0;

    return !isPlaceholder;
  });

  frm.refresh_field("payables");
  frm.refresh_field("receivables");
}