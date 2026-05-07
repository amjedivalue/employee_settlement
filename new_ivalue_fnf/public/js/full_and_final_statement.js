// ================================================================
// SECTION 1: Full and Final Statement Form Events
// ================================================================

frappe.ui.form.on("Full and Final Statement", {
    // Runs once when the form is initialized and sets query filters.
    setup: function (frm) {
        frm.set_query("employee", function () {
            return {
                filters: [
                    ["Employee", "relieving_date", "is", "set"]
                ]
            };
        });

        set_child_table_account_filters(frm);
    },

    // Runs when the form is loaded and prepares default values.
    onload: function (frm) {
        if (!frm.doc.transaction_date) {
            frm.set_value("transaction_date", frappe.datetime.get_today());
        }

        if (frm.doc.workflow_state === "Employee Sigen") {
            fetch_zoho_doc(frm);
        }

        clear_placeholder_rows(frm);
    },

    // Runs every time the form is refreshed.
    refresh: function (frm) {
        clear_placeholder_rows(frm);

        // add_full_and_final_settings_button(frm);
        // add_review_settlement_button(frm);

        add_explain_selected_row_button(frm);
        add_test_employee_separation_pdf_sync_button(frm);
    },

    // Runs when the employee is selected and validates related documents.
    employee: async function (frm) {
        if (!frm.doc.employee) {
            clear_employee_related_data(frm);
            return;
        }

        let existing_doc = await check_existing_full_and_final(frm);

        if (existing_doc) {
            show_existing_full_and_final_dialog(frm, existing_doc);
            return;
        }

        let employee_separation = await check_employee_separation(frm);

        if (!employee_separation) {
            show_missing_employee_separation_message(frm);
            return;
        }

        await frm.set_value("custom_employee_separation", employee_separation.name);

        await load_employee_basic_data(frm);
        await ensure_employee_relieving_date(frm);

        frm.refresh_field("custom_employee_separation");
        frm.refresh_field("relieving_date");
        frm.refresh_field("custom_user_id");
    },

    // Runs when the company is changed and resets child table filters.
    company: function (frm) {
        set_child_table_account_filters(frm);
        clear_invalid_child_accounts(frm);
    },

    // Runs when the relieving date is changed.
    relieving_date: function (frm) {
        clear_placeholder_rows(frm);
    },

    // Runs before saving the document and validates required employee data.
    validate: async function (frm) {
        clear_placeholder_rows(frm);

        if (frm.doc.employee) {
            let employee_separation = await check_employee_separation(frm);

            if (!employee_separation) {
                frappe.msgprint({
                    title: __("Employee Separation Required"),
                    message: __(
                        "Please create Employee Separation before saving this Full and Final Statement."
                    ),
                    indicator: "orange"
                });

                frappe.validated = false;
                return;
            }

            await frm.set_value("custom_employee_separation", employee_separation.name);

            if (!frm.doc.custom_user_id || !frm.doc.relieving_date) {
                await load_employee_basic_data(frm);
            }

            if (!frm.doc.employee) {
                return;
            }

            let employee_response = await frappe.db.get_value(
                "Employee",
                frm.doc.employee,
                [
                    "relieving_date",
                    "user_id"
                ]
            );

            if (!employee_response || !employee_response.message) {
                frappe.msgprint({
                    title: __("Employee Not Found"),
                    message: __("Could not load employee details. Please select the employee again."),
                    indicator: "red"
                });

                frappe.validated = false;
                return;
            }

            let employee = employee_response.message;

            if (!frm.doc.relieving_date && employee.relieving_date) {
                await frm.set_value("relieving_date", employee.relieving_date);
            }

            if (!frm.doc.custom_user_id && employee.user_id) {
                await frm.set_value("custom_user_id", employee.user_id);
            }


            await ensure_employee_relieving_date(frm);


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

    before_workflow_action: async function (frm) {
        if (frm.doc.workflow_state === "Pending Supporting Services Director") {
            if (frm.selected_workflow_action === "Approve") {
                await check_if_separatoin_has_been_submited(frm)
            }
        }
    },

    // Runs before cancelling the document and cancels the Zoho document.
    before_cancel: function (frm) {
        remove_custody(frm);
    },

    // Runs after a workflow action and creates ToDo for non-HR User states.
    after_workflow_action: function (frm) {
        if (frm.doc.workflow_state !== "Employee Sigen" && frm.doc.workflow_state !== "HR User") {
            add_to_do(frm);
        } else if (frm.doc.workflow_state === "Employee Sigen") {
            upload_on_zoho(frm);
        }
    }
});



// khaled Jallad was here
// this code prevent the workflow from workin if the separation is not submited
async function check_if_separatoin_has_been_submited(frm) {
    const response = await frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.check_if_separation_is_submited",
        args: { name: frm.doc.name },
    })

    if (response.message.status === 200) {
        if (response.message.data === 0) {
            frappe.dom.unfreeze();
            frappe.throw("Employee separation must be submited before proceed with Action")
        } else if (response.message.data === 2) {
            frappe.dom.unfreeze();
            frappe.throw("Employee separation has been canceled please create new one before proceed with action")

        }
    } else {
        frappe.dom.unfreeze();
        frappe.throw("Employee separation not exist")

    }

}





async function ensure_employee_relieving_date(frm) {
    if (!frm.doc.employee) {
        return;
    }

    let response = await frappe.call({
        method: "new_ivalue_fnf.api.full_and_final.service.ensure_employee_relieving_date",
        args: {
            employee: frm.doc.employee,
            relieving_date: frm.doc.relieving_date || ""
        }
    });

    if (response.message && response.message.relieving_date) {
        await frm.set_value("relieving_date", response.message.relieving_date);
        frm.refresh_field("relieving_date");
    }
}
// ================================================================
// SECTION 2: Full and Final Outstanding Statement Child Table Events
// ================================================================

frappe.ui.form.on("Full and Final Outstanding Statement", {
    // Runs when the component is changed and applies manual row defaults.
    component: function (frm, cdt, cdn) {
        apply_manual_row_defaults(frm, cdt, cdn);
    },

    // Runs when the amount is changed and applies manual row defaults.
    amount: function (frm, cdt, cdn) {
        apply_manual_row_defaults(frm, cdt, cdn);
    },

    // Runs when Paid via Salary Slip is changed and blocks it for Receivables.
    paid_via_salary_slip: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row) {
            return;
        }

        if (row.parentfield === "receivables" && row.paid_via_salary_slip) {
            frappe.model.set_value(cdt, cdn, "paid_via_salary_slip", 0);

            frappe.msgprint({
                title: __("Not Allowed"),
                message: __(
                    "Paid via Salary Slip can only be used for Payable rows. Receivable rows are still included by the standard Journal Entry creation."
                ),
                indicator: "orange"
            });
        }
    }
});


// ================================================================
// SECTION 3: Duplicate Full and Final Validation
// ================================================================

// Checks if another Full and Final Statement already exists for the selected employee.
async function check_existing_full_and_final(frm) {
    let response = await frappe.call({
        method: "new_ivalue_fnf.api.full_and_final.service.get_existing_full_and_final_for_employee",
        args: {
            employee: frm.doc.employee,
            current_docname: frm.doc.name || ""
        }
    });

    if (!response.message) {
        return null;
    }

    return response.message;
}


// Shows a message when a Full and Final Statement already exists for the employee.
function show_existing_full_and_final_dialog(frm, existing_doc) {
    let employee = frm.doc.employee;

    frappe.msgprint({
        title: __("Full and Final Already Exists"),
        indicator: "orange",
        message: __(
            "A Full and Final Statement already exists for this employee.<br><br>" +
            "<b>Employee:</b> {0}<br>" +
            "<b>Document ID:</b> {1}<br>" +
            "<b>Workflow State:</b> {2}<br><br>" +
            "Please open the existing document instead of creating a new one."
        ).format(
            employee,
            existing_doc.name,
            existing_doc.workflow_state || "-"
        ),
        primary_action: {
            label: __("Open Existing Document"),
            action: function () {
                frappe.set_route("Form", "Full and Final Statement", existing_doc.name);
            }
        }
    });

    frm.set_value("employee", "");
    clear_employee_related_data(frm);
}


// ================================================================
// SECTION 4: Employee Separation Validation
// ================================================================

// Checks if the selected employee has a Draft or Submitted Employee Separation.
async function check_employee_separation(frm) {
    let response = await frappe.call({
        method: "new_ivalue_fnf.api.full_and_final.service.get_employee_separation_for_full_and_final",
        args: {
            employee: frm.doc.employee
        }
    });

    if (!response.message) {
        return null;
    }

    return response.message;
}


// Shows a message when the selected employee has no Employee Separation document.
function show_missing_employee_separation_message(frm) {
    let selected_employee = frm.doc.employee;

    frappe.msgprint({
        title: __("Employee Separation Required"),
        indicator: "orange",
        message: __(
            "This employee does not have a Draft or Submitted Employee Separation.<br><br>" +
            "<b>Employee:</b> {0}<br><br>" +
            "Please create Employee Separation first, then come back and continue the Full and Final Statement."
        ).format(selected_employee),
        primary_action: {
            label: __("Create Employee Separation"),
            action: function () {
                frappe.set_route("Form", "Employee Separation", "new-employee-separation");
            }
        }
    });

    frm.set_value("employee", "");
    clear_employee_related_data(frm);
}


// ================================================================
// SECTION 5: Employee Data Loading and Clearing
// ================================================================

// Clears all employee-related fields and child tables from the form.
function clear_employee_related_data(frm) {
    frm.set_value("employee_name", "");
    frm.set_value("company", "");
    frm.set_value("department", "");
    frm.set_value("designation", "");
    frm.set_value("date_of_joining", "");
    frm.set_value("relieving_date", "");
    frm.set_value("transaction_date", "");

    frm.set_value("custom_company_currency", "");
    frm.set_value("custom_letter_head", "");
    frm.set_value("custom_basic_salary", 0);
    frm.set_value("custom_housing", 0);
    frm.set_value("custom_transportation", 0);
    frm.set_value("custom_other_allowances", 0);
    frm.set_value("custom_monthly_gross_salary", 0);

    frm.set_value("custom_service_years", 0);
    frm.set_value("custom_service_month", 0);
    frm.set_value("custom_service_days", 0);
    frm.set_value("custom_total_of_years", 0);

    frm.set_value("total_payable_amount", 0);
    frm.set_value("total_receivable_amount", 0);
    frm.set_value("total_asset_recovery_cost", 0);

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


// Loads basic employee data from Employee into the Full and Final Statement form.
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


// ================================================================
// SECTION 6: Zoho and Workflow Actions
// ================================================================

// Creates a ToDo assignment based on the current workflow state.
function add_to_do(frm) {
    frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.add_assigened_to",
        args: {
            name: frm.doc.name,
            workflow_state: frm.doc.workflow_state
        },
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
    });
}


// Cancels the related Zoho document when the Full and Final Statement is cancelled.
function remove_custody(frm) {
    frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.cancel_zoho_doc",
        args: {
            name: frm.doc.name
        },
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
    });
}


// Uploads the Full and Final Statement document to Zoho.
function upload_on_zoho(frm) {
    frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.upload_on_zoho",
        args: {
            name: frm.doc.name
        },
        freeze: true,
        freeze_message: ("Upload on zoho..."),
        callback: function (response) {
            if (response.message.status === 201) {
                frappe.show_alert({
                    message: __(response.message.message),
                    indicator: "green"
                });
                sync_employee_separation_pdf_to_full_and_final(frm, false);
                frm.reload_doc();
            }
        }
    });
}


// Fetches the related Zoho document data when needed.
function fetch_zoho_doc(frm) {
    frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.fetch_zoho_doc",
        args: {
            name: frm.doc.name
        },
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
    });
}






// ================================================================
// SECTION 7: Child Table Cleanup Helpers
// ================================================================

// Removes empty placeholder rows from Payables and Receivables tables.
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


// ================================================================
// SECTION 8: Account and Cost Center Filters
// ================================================================

// Applies account and cost center filters to Payables and Receivables child tables.
function set_child_table_account_filters(frm) {
    set_account_filter_for_table(frm, "payables");
    set_account_filter_for_table(frm, "receivables");

    set_cost_center_filter_for_table(frm, "payables");
    set_cost_center_filter_for_table(frm, "receivables");
}


// Sets the account query filter for a child table based on the selected company.
function set_account_filter_for_table(frm, table_field) {
    if (!frm.fields_dict[table_field] || !frm.fields_dict[table_field].grid) {
        return;
    }

    let account_field = frm.fields_dict[table_field].grid.get_field("account");

    if (!account_field) {
        return;
    }

    account_field.get_query = function () {
        if (!frm.doc.company) {
            return {
                filters: {
                    is_group: 0
                }
            };
        }

        return {
            filters: {
                company: frm.doc.company,
                is_group: 0
            }
        };
    };
}


// Sets the cost center query filter for a child table based on the selected company.
function set_cost_center_filter_for_table(frm, table_field) {
    if (!frm.fields_dict[table_field] || !frm.fields_dict[table_field].grid) {
        return;
    }

    let cost_center_field = frm.fields_dict[table_field].grid.get_field("cost_center");

    if (!cost_center_field) {
        return;
    }

    cost_center_field.get_query = function () {
        if (!frm.doc.company) {
            return {
                filters: {
                    is_group: 0
                }
            };
        }

        return {
            filters: {
                company: frm.doc.company,
                is_group: 0
            }
        };
    };
}


// Clears invalid child table accounts when they do not belong to the selected company.
function clear_invalid_child_accounts(frm) {
    ["payables", "receivables"].forEach(function (table_field) {
        (frm.doc[table_field] || []).forEach(function (row) {
            if (!row.account) {
                return;
            }

            frappe.db.get_value(
                "Account",
                row.account,
                [
                    "company",
                    "is_group"
                ]
            ).then(function (response) {
                if (!response.message) {
                    return;
                }

                if (
                    response.message.company !== frm.doc.company ||
                    response.message.is_group
                ) {
                    frappe.model.set_value(row.doctype, row.name, "account", "");
                }
            });
        });

        frm.refresh_field(table_field);
    });
}


// ================================================================
// SECTION 9: Settings Navigation
// ================================================================

// Adds a button to open Full and Final Settings from the form.
function add_full_and_final_settings_button(frm) {
    let button_label = "Full and Final Settings";

    if (frm.custom_buttons && frm.custom_buttons[button_label]) {
        return;
    }

    frm.add_custom_button(button_label, function () {
        open_full_and_final_settings(frm);
    });
}


// Opens the Full and Final Settings list view.
function open_full_and_final_settings(frm) {
    frappe.set_route("List", "Full and Final Settings");
}


// ================================================================
// SECTION 10: Manual Row Defaults
// ================================================================

// Applies default values to manual Payables and Receivables rows.
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

    if (row.custom_is_manual_row && row.reference_document) {
        return;
    }

    frappe.model.set_value(cdt, cdn, "custom_is_manual_row", 1);
    frappe.model.set_value(cdt, cdn, "status", "Settled");

    let table_name = "Payables";

    if (row.parentfield === "receivables") {
        table_name = "Receivables";
    }

    frappe.call({
        method: "new_ivalue_fnf.api.full_and_final.service.get_manual_row_defaults",
        args: {
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

            frappe.model.set_value(cdt, cdn, "status", data.status);
            frappe.model.set_value(cdt, cdn, "custom_is_manual_row", data.custom_is_manual_row);
        },
        error: function () {
            frappe.model.set_value(cdt, cdn, "status", "");
            frappe.model.set_value(cdt, cdn, "custom_is_manual_row", 0);
        }
    });
}


// ================================================================
// SECTION 11: Explain Row Button
// ================================================================

// Adds Explain Row buttons beside Add Row in Payables and Receivables tables.
function add_explain_selected_row_button(frm) {
    add_explain_button_to_grid(frm, "payables", "Explain Row");
    add_explain_button_to_grid(frm, "receivables", "Explain Row");
}


// Adds an Explain Row button to a specific child table grid.
function add_explain_button_to_grid(frm, table_field, button_label) {
    if (!frm.fields_dict[table_field] || !frm.fields_dict[table_field].grid) {
        return;
    }

    let grid = frm.fields_dict[table_field].grid;
    let button_class = "fnf-explain-row-button-" + table_field;

    if (grid.wrapper.find("." + button_class).length) {
        return;
    }

    let button = $(
        `<button class="btn btn-xs btn-default ${button_class}" type="button">
            ${__(button_label)}
        </button>`
    );

    button.on("click", function () {
        explain_selected_settlement_row(frm, table_field);
    });

    let add_row_button = grid.wrapper.find(".grid-add-row");

    if (add_row_button.length) {
        add_row_button.after(button);
    } else {
        grid.wrapper.find(".grid-buttons").append(button);
    }
}


// Reads the selected row and requests explanation details from the server.
function explain_selected_settlement_row(frm, target_table_field) {
    let selected_rows = frm.get_selected();

    let table_field = target_table_field || "";

    if (!table_field) {
        let selected_payables = selected_rows.payables || [];
        let selected_receivables = selected_rows.receivables || [];

        let total_selected = selected_payables.length + selected_receivables.length;

        if (total_selected === 0) {
            frappe.msgprint(__("Please select one row from Payables or Receivables first."));
            return;
        }

        if (total_selected > 1) {
            frappe.msgprint(__("Please select only one row."));
            return;
        }

        table_field = "payables";

        if (selected_receivables.length > 0) {
            table_field = "receivables";
        }
    }

    let selected_names = selected_rows[table_field] || [];

    if (selected_names.length === 0) {
        frappe.msgprint(__("Please select one row from this table first."));
        return;
    }

    if (selected_names.length > 1) {
        frappe.msgprint(__("Please select only one row from this table."));
        return;
    }

    let row_name = selected_names[0];

    let row = (frm.doc[table_field] || []).find(function (item) {
        return item.name === row_name;
    });

    if (!row) {
        frappe.msgprint(__("Could not find the selected row. Please refresh and try again."));
        return;
    }

    if (!frm.doc.employee) {
        frappe.msgprint(__("Please select an Employee first."));
        return;
    }

    if (!frm.doc.relieving_date) {
        frappe.msgprint(__("Please set Relieving Date first."));
        return;
    }

    frappe.call({
        method: "new_ivalue_fnf.api.full_and_final.service.explain_settlement_amount",
        args: {
            doc_json: JSON.stringify(frm.doc),
            row_json: JSON.stringify(row),
            table_field: table_field
        },
        freeze: true,
        freeze_message: __("Explaining amount..."),
        callback: function (response) {
            if (!response.message) {
                return;
            }

            show_amount_explanation_dialog(response.message);
        }
    });
}


// Shows the explanation dialog for the selected settlement row.
function show_amount_explanation_dialog(data) {
    let dialog = new frappe.ui.Dialog({
        title: __("Explain This Amount"),
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "explanation_html"
            }
        ]
    });

    dialog.fields_dict.explanation_html.$wrapper.html(
        build_amount_explanation_html(data)
    );

    dialog.show();
}


// Builds the HTML content for the amount explanation dialog.
function build_amount_explanation_html(data) {
    let lines = (data.lines || []).filter(function (item) {
        return has_explanation_value(item ? item.value : null);
    });

    let rows_html = lines.map(function (item) {
        return `
            <div style="
                display: grid;
                grid-template-columns: 240px 1fr;
                gap: 12px;
                padding: 9px 0;
                border-bottom: 1px solid var(--border-color);
            ">
                <div style="font-weight: 600; color: var(--text-muted);">
                    ${fnf_escape_html(item.label || "")}
                </div>
                <div style="font-weight: 500;">
                    ${fnf_escape_html(item.value)}
                </div>
            </div>
        `;
    }).join("");

    return `
        <div style="font-size: 13px;">
            <div style="
                padding: 14px;
                border: 1px solid var(--border-color);
                border-radius: 10px;
                margin-bottom: 14px;
                background: var(--fg-color);
            ">
                <div style="font-size: 20px; font-weight: 700; margin-bottom: 4px;">
                    ${fnf_escape_html(data.title || "Settlement Row")}
                </div>
                <div style="color: var(--text-muted); line-height: 1.5;">
                    ${fnf_escape_html(data.summary || "")}
                </div>
            </div>

            <div style="
                border: 1px solid var(--border-color);
                border-radius: 10px;
                padding: 4px 14px;
            ">
                ${rows_html}
            </div>
        </div>
    `;
}


// Checks whether a value should be shown in the explanation dialog.
function has_explanation_value(value) {
    if (value === 0) {
        return true;
    }

    if (value === null || value === undefined) {
        return false;
    }

    let string_value = String(value).trim();

    if (!string_value) {
        return false;
    }

    if (string_value === "-") {
        return false;
    }

    return true;
}


// Escapes HTML characters before displaying dynamic values in the dialog.
function fnf_escape_html(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
// ===============================================
//  amjed  tamimi  extention after  khaled Jallad
//================================================


// ================================================================
// Button to simulate Zoho locally
// ================================================================

function add_test_employee_separation_pdf_sync_button(frm) {
    if (frm.is_new()) {
        return;
    }

    if (frm.custom_buttons && frm.custom_buttons["Test Separation PDF Sync"]) {
        return;
    }

    frm.add_custom_button(__("Test Separation PDF Sync"), function () {
        sync_employee_separation_pdf_to_full_and_final(frm);
    });
}


function sync_employee_separation_pdf_to_full_and_final(frm, reload_after_sync = true) {
    if (!frm.doc.name) {
        frappe.msgprint(__("Please save the Full and Final Statement before syncing Employee Separation PDF."));
        return;
    }

    return frappe.call({
        method: "new_ivalue_fnf.override.full_and_final_statement.full_and_final_statement.sync_employee_separation_attachments_to_full_and_final",
        args: {
            name: frm.doc.name
        },
        freeze: true,
        freeze_message: __("Syncing Employee Separation PDF..."),
        callback: function (response) {
            if (!response.message) {
                return;
            }

            frappe.show_alert({
                message: __(response.message.message || "Employee Separation PDF sync completed"),
                indicator: response.message.status === 201 ? "green" : "blue"
            });

            if (reload_after_sync) {
                frm.reload_doc();
            }
        }
    });
}

// ================amjed  tamimi=====================================