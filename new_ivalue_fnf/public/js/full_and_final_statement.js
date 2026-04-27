frappe.ui.form.on("Full and Final Statement", {
    setup: function(frm) {
        frm.set_query("employee", function() {
            return {
                filters: [
                    ["Employee", "relieving_date", "is", "set"]
                ]
            };
        });
    },
    onload(frm) {


        if (!frm.doc.transaction_date) {
            frm.set_value("transaction_date", frappe.datetime.get_today());
        }
        if (frm.doc.workflow_state === "Employee Sigen") {
            fetch_zoho_doc(frm)
        }

        clear_placeholder_rows(frm);

    },

    refresh(frm) {
        clear_placeholder_rows(frm);
        //  add_full_and_final_settings_button(frm);
        // add_review_settlement_button(frm);
        // add_explain_selected_row_button(frm);
    },

    employee: async function (frm) {
        if (!frm.doc.employee) {
            clear_employee_related_data(frm);
            return;
        }

        await load_employee_basic_data(frm);
    },

    relieving_date(frm) {
        clear_placeholder_rows(frm);
    },

    
   
   validate: async function (frm) {
    clear_placeholder_rows(frm);

    if (frm.doc.employee) {

        if (!frm.doc.custom_user_id || !frm.doc.relieving_date) {
            await load_employee_basic_data(frm);
        }

      if (!frm.doc.relieving_date) {
    frappe.msgprint({
        title: __("Missing Relieving Date"),
        message: __("This employee does not have a Relieving Date. Please set the Relieving Date on the Employee record, then reselect the employee."),
        indicator: "orange"
    });

    frappe.validated = false;
    return;
}

if (!frm.doc.custom_user_id) {
    frappe.msgprint({
        title: __("Missing User ID"),
        message: __("This employee is not linked to a User. Please set the User ID on the Employee record, then reselect the employee."),
        indicator: "orange"
    });

    frappe.validated = false;
    return;
}
    }
},
    after_workflow_action: async function (frm) {
        if (frm.doc.workflow_state === "Employee Sigen") {
            upload_on_zoho(frm)
        }
    },
    before_cancel: function (frm) {
        remove_custody(frm)
    },
    after_workflow_action: function (frm) {
        if (frm.doc.workflow_state !== "Employee Sigen" && frm.doc.workflow_state !== "HR User") {
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
function add_to_do(frm) {
    frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.add_assigened_to",
        args: { name: frm.doc.name, workflow_state: frm.doc.workflow_state },
        freeze: true,
        freeze_message: __("Add to do..."),
        callback: function (response) {
            if (response.message.status === 201) {
                frappe.show_alert({
                    message: __("To do has been added successfully"),
                    indicator: "green"
                });
                frm.reload_doc();
            }
        }
    })
}

function remove_custody(frm) {
    frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.cancel_zoho_doc",
        args: { name: frm.doc.name },
        freeze: true,
        freeze_message: ("cancel zoho doc..."),
        callback: function (response) {
            if (response.message.status === 200) {
                frappe.show_alert({
                    message: __(response.message.message),
                    indicator: "green"
                });
                frm.reload_doc();
            }
        }
    })
}


function upload_on_zoho(frm) {
    frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.upload_on_zoho",
        args: { name: frm.doc.name },
        freeze: true,
        freeze_message: ("Upload on zoho..."),
        callback: function (response) {
            if (response.message.status === 201) {
                frappe.show_alert({
                    message: __(response.message.message),
                    indicator: "green"
                });
                frm.reload_doc();
            }
        }
    })
}

function fetch_zoho_doc(frm) {
    frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.fetch_zoho_doc",
        args: { name: frm.doc.name },
        freeze: true,
        freeze_message: ("fetch zoho doc..."),
        callback: function (response) {
            if (response.message.status === 200) {
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
frappe.ui.form.on("Full and Final Outstanding Statement", {
    component: function (frm, cdt, cdn) {
        apply_manual_row_defaults(frm, cdt, cdn);
    },

    amount: function (frm, cdt, cdn) {
        apply_manual_row_defaults(frm, cdt, cdn);
    }
});

function apply_manual_row_defaults(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    if (!row) {
        return;
    }

    if (!frm.doc.company) {
        return;
    }

    if (!row.amount || row.amount <= 0) {
        return;
    }

    if (row.is_manual_row && row.reference_document) {
        return;
    }
    frappe.model.set_value(cdt, cdn, "is_manual_row", 1);
    frappe.model.set_value(cdt, cdn, "status", "Settled");
    let table_name = "Payables";

    if (row.parentfield === "receivables") {
        table_name = "Receivables";
    }

    frappe.call({
method: "new_ivalue_fnf.api.full_and_final.service.get_manual_row_defaults",        args: {
            company: frm.doc.company,
            table_name: table_name,
            component: row.component || "",
            amount: row.amount,
            document_name: frm.doc.name || ""
        },
        callback: function (response) {
            if (!response.message) {
                return;
            }

            let data = response.message;

            frappe.model.set_value(cdt, cdn, "account", data.account);
            frappe.model.set_value(cdt, cdn, "status", data.status);
            frappe.model.set_value(cdt, cdn, "is_manual_row", data.is_manual_row);
        },
        error: function () {
            frappe.model.set_value(cdt, cdn, "account", "");
            frappe.model.set_value(cdt, cdn, "status", "");
            frappe.model.set_value(cdt, cdn, "is_manual_row", 0);
        }
    });
}
async function load_employee_basic_data(frm) {
    frappe.dom.freeze(__("Loading employee details..."));

    try {
        let response = await frappe.db.get_value(
            "Employee",
            frm.doc.employee,
            [
                "employee_name",
                "company",
                "department",
                "designation",
                "date_of_joining",
                "relieving_date",
                "user_id",
                "employment_type"
            ]
        );

        if (!response || !response.message) {
            frappe.msgprint({
                title: __("Employee Not Found"),
                message: __("Could not load employee details. Please select the employee again."),
                indicator: "red"
            });
            return;
        }

        let employee = response.message;

        await frm.set_value("employee_name", employee.employee_name || "");
        await frm.set_value("company", employee.company || "");
        await frm.set_value("department", employee.department || "");
        await frm.set_value("designation", employee.designation || "");
        await frm.set_value("date_of_joining", employee.date_of_joining || "");
        await frm.set_value("relieving_date", employee.relieving_date || "");
        await frm.set_value("custom_user_id", employee.user_id || "");
        await frm.set_value("custom_employment_type", employee.employment_type || "");

        clear_placeholder_rows(frm);
    } catch (error) {
        console.error(error);

        frappe.msgprint({
            title: __("Loading Failed"),
            message: __("Could not load employee details. Please try again."),
            indicator: "red"
        });
    } finally {
        frappe.dom.unfreeze();
    }
}

// // ================================================================
// function add_explain_selected_row_button(frm) {
//     let button_label = "Select Row and Click Me";

//     if (frm.custom_buttons && frm.custom_buttons[button_label]) {
//         return;
//     }

//     frm.add_custom_button(button_label, function () {
//         explain_selected_settlement_row(frm);
//     });
// }


// function explain_selected_settlement_row(frm) {
//     let selected = frm.get_selected();

//     let selected_payables = selected.payables || [];
//     let selected_receivables = selected.receivables || [];

//     let total_selected = selected_payables.length + selected_receivables.length;

//     if (total_selected === 0) {
//         frappe.msgprint(__("Please select one row from Payables or Receivables first."));
//         return;
//     }

//     if (total_selected > 1) {
//         frappe.msgprint(__("Please select only one row to explain."));
//         return;
//     }

//     let table_field = "payables";
//     let row_name = selected_payables[0];

//     if (selected_receivables.length) {
//         table_field = "receivables";
//         row_name = selected_receivables[0];
//     }

//     let row = get_selected_child_row(row_name);

//     if (!row) {
//         frappe.msgprint(__("Could not read the selected row. Please refresh and try again."));
//         return;
//     }

//     if (!frm.doc.employee) {
//         frappe.msgprint(__("Please select an Employee first."));
//         return;
//     }

//     if (!frm.doc.relieving_date) {
//         frappe.msgprint(__("Please set Relieving Date first."));
//         return;
//     }

//     frappe.call({
//         method: "new_ivalue_fnf.api.full_and_final.service.explain_settlement_amount",
//         args: {
//             doc_json: JSON.stringify(frm.doc),
//             row_json: JSON.stringify(row),
//             table_field: table_field
//         },
//         freeze: true,
//         freeze_message: __("Explaining amount..."),
//         callback: function (response) {
//             if (!response.message) {
//                 return;
//             }

//             show_amount_explanation_dialog(response.message);
//         }
//     });
// }



// function add_explain_selected_row_button(frm) {
//     frm.add_custom_button(__("Select Row and Click Me"), function () {
//         explain_selected_settlement_row(frm);
//     });
// }


// function explain_selected_settlement_row(frm) {
//     let selected_rows = frm.get_selected();

//     let selected_payables = selected_rows.payables || [];
//     let selected_receivables = selected_rows.receivables || [];

//     let total_selected = selected_payables.length + selected_receivables.length;

//     if (total_selected === 0) {
//         frappe.msgprint(__("Please select one row from Payables or Receivables first."));
//         return;
//     }

//     if (total_selected > 1) {
//         frappe.msgprint(__("Please select only one row."));
//         return;
//     }

//     let table_field = "payables";
//     let row_name = selected_payables[0];

//     if (selected_receivables.length > 0) {
//         table_field = "receivables";
//         row_name = selected_receivables[0];
//     }

//     let row = null;

//     if (table_field === "payables") {
//         row = (frm.doc.payables || []).find(function (item) {
//             return item.name === row_name;
//         });
//     }

//     if (table_field === "receivables") {
//         row = (frm.doc.receivables || []).find(function (item) {
//             return item.name === row_name;
//         });
//     }

//     if (!row) {
//         frappe.msgprint(__("Could not find the selected row. Please refresh and try again."));
//         return;
//     }

//     if (!frm.doc.employee) {
//         frappe.msgprint(__("Please select an Employee first."));
//         return;
//     }

//     if (!frm.doc.relieving_date) {
//         frappe.msgprint(__("Please set Relieving Date first."));
//         return;
//     }

//     frappe.call({
//         method: "new_ivalue_fnf.api.full_and_final.service.explain_settlement_amount",
//         args: {
//             doc_json: JSON.stringify(frm.doc),
//             row_json: JSON.stringify(row),
//             table_field: table_field
//         },
//         freeze: true,
//         freeze_message: __("Explaining amount..."),
//         callback: function (response) {
//             if (!response.message) {
//                 return;
//             }

//             show_amount_explanation_dialog(response.message);
//         }
//     });
// }


// function show_amount_explanation_dialog(data) {
//     let dialog = new frappe.ui.Dialog({
//         title: __("Explain This Amount"),
//         size: "large",
//         fields: [
//             {
//                 fieldtype: "HTML",
//                 fieldname: "explanation_html"
//             }
//         ]
//     });

//     dialog.fields_dict.explanation_html.$wrapper.html(
//         build_amount_explanation_html(data)
//     );

//     dialog.show();
// }


// function build_amount_explanation_html(data) {
//     let lines = (data.lines || []).filter(function (item) {
//         return has_explanation_value(item ? item.value : null);
//     });

//     let rows_html = lines.map(function (item) {
//         return `
//             <div style="
//                 display: grid;
//                 grid-template-columns: 220px 1fr;
//                 gap: 12px;
//                 padding: 9px 0;
//                 border-bottom: 1px solid var(--border-color);
//             ">
//                 <div style="font-weight: 600; color: var(--text-muted);">
//                     ${fnf_escape_html(item.label || "")}
//                 </div>
//                 <div style="font-weight: 500;">
//                     ${fnf_escape_html(item.value)}
//                 </div>
//             </div>
//         `;
//     }).join("");

//     return `
//         <div style="font-size: 13px;">
//             <div style="
//                 padding: 14px;
//                 border: 1px solid var(--border-color);
//                 border-radius: 10px;
//                 margin-bottom: 14px;
//                 background: var(--fg-color);
//             ">
//                 <div style="font-size: 20px; font-weight: 700; margin-bottom: 4px;">
//                     ${fnf_escape_html(data.title || "Settlement Row")}
//                 </div>
//                 <div style="color: var(--text-muted); line-height: 1.5;">
//                     ${fnf_escape_html(data.summary || "")}
//                 </div>
//             </div>

//             <div style="
//                 border: 1px solid var(--border-color);
//                 border-radius: 10px;
//                 padding: 4px 14px;
//             ">
//                 ${rows_html}
//             </div>
//         </div>
//     `;
// }


// function has_explanation_value(value) {
//     if (value === 0) {
//         return true;
//     }

//     if (value === null || value === undefined) {
//         return false;
//     }

//     let string_value = String(value).trim();

//     if (!string_value) {
//         return false;
//     }

//     if (string_value === "-") {
//         return false;
//     }

//     return true;
// }


// function fnf_escape_html(value) {
//     return String(value || "")
//         .replace(/&/g, "&amp;")
//         .replace(/</g, "&lt;")
//         .replace(/>/g, "&gt;")
//         .replace(/"/g, "&quot;")
//         .replace(/'/g, "&#039;");
// }
