frappe.ui.form.on("Full and Final Settings", {
    refresh: function (frm) {
        hide_add_row_button(frm);
        lock_component_key_column(frm);
        set_account_query_for_company(frm);

        hide_manual_row_settings_buttons(frm);
        lock_manual_row_type_column(frm);
        set_manual_row_account_query_for_company(frm);

        set_cost_center_query_for_company(frm);
        add_back_to_full_and_final_button(frm);
    },

    company: function (frm) {
        set_account_query_for_company(frm);
        set_manual_row_account_query_for_company(frm);
        set_cost_center_query_for_company(frm);
    }
});


frappe.ui.form.on("Full and Final Settings Component", {
    is_enabled: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.component_key === "Gratuity" && row.is_enabled) {
            if (!frm.doc.company) {
                frappe.model.set_value(cdt, cdn, "is_enabled", 0);
                frappe.msgprint(__("Please select a company first."));
                return;
            }

            frappe.dom.freeze(__("Checking company settings..."));

            frappe.db.get_value("Company", frm.doc.company, "country", (r) => {
                frappe.dom.unfreeze();

                if (r && r.country !== "Saudi Arabia") {
                    frappe.model.set_value(cdt, cdn, "is_enabled", 0);

                    frappe.msgprint({
                        title: __("Not Allowed"),
                        indicator: "orange",
                        message: __("Gratuity can only be enabled for companies located in Saudi Arabia.")
                    });
                }
            });
        }
    }
});


function hide_add_row_button(frm) {
    if (!frm.fields_dict.components || !frm.fields_dict.components.grid) {
        return;
    }

    frm.fields_dict.components.grid.cannot_add_rows = true;
    frm.fields_dict.components.grid.cannot_delete_rows = true;

    frm.fields_dict.components.grid.wrapper.find(".grid-add-row").hide();
    frm.fields_dict.components.grid.wrapper.find(".grid-remove-rows").hide();
}


function lock_component_key_column(frm) {
    if (!frm.fields_dict.components || !frm.fields_dict.components.grid) {
        return;
    }

    frm.fields_dict.components.grid.update_docfield_property("component_key", "read_only", 1);
}


function set_account_query_for_company(frm) {
    if (!frm.fields_dict.components || !frm.fields_dict.components.grid) {
        return;
    }

    frm.fields_dict.components.grid.get_field("account").get_query = function (doc) {
        if (!doc.company) {
            return {
                filters: {
                    name: ["=", ""]
                }
            };
        }

        return {
            filters: {
                company: doc.company,
                is_group: 0
            }
        };
    };
}


function add_back_to_full_and_final_button(frm) {
    let button_label = "Back to Full and Final";

    if (frm.custom_buttons && frm.custom_buttons[button_label]) {
        return;
    }

    frm.add_custom_button(button_label, function () {
        frappe.set_route("List", "Full and Final Statement");
    });
}


function hide_manual_row_settings_buttons(frm) {
    if (!frm.fields_dict.manual_row_settings || !frm.fields_dict.manual_row_settings.grid) {
        return;
    }

    frm.fields_dict.manual_row_settings.grid.cannot_add_rows = true;
    frm.fields_dict.manual_row_settings.grid.cannot_delete_rows = true;

    frm.fields_dict.manual_row_settings.grid.wrapper.find(".grid-add-row").hide();
    frm.fields_dict.manual_row_settings.grid.wrapper.find(".grid-remove-rows").hide();
}


function lock_manual_row_type_column(frm) {
    if (!frm.fields_dict.manual_row_settings || !frm.fields_dict.manual_row_settings.grid) {
        return;
    }

    frm.fields_dict.manual_row_settings.grid.update_docfield_property("row_type", "read_only", 1);
}


function set_manual_row_account_query_for_company(frm) {
    if (!frm.fields_dict.manual_row_settings || !frm.fields_dict.manual_row_settings.grid) {
        return;
    }

    frm.fields_dict.manual_row_settings.grid.get_field("account").get_query = function (doc) {
        if (!doc.company) {
            return {
                filters: {
                    name: ["=", ""]
                }
            };
        }

        return {
            filters: {
                company: doc.company,
                is_group: 0
            }
        };
    };
}


function set_cost_center_query_for_company(frm) {
    frm.set_query("custom_default_cost_center", function () {
        if (!frm.doc.company) {
            return {
                filters: {
                    name: ["=", ""]
                }
            };
        }

        return {
            filters: {
                company: frm.doc.company,
                is_group: 0
            }
        };
    });
}