frappe.ui.form.on("Full and Final Settings", {
   
   
    
   
    refresh: function (frm) {
        hide_add_row_button(frm);
        lock_component_key_column(frm);
        set_account_query_for_company(frm);
            add_back_to_full_and_final_button(frm);
                    toggle_saudi_labor_field(frm);


     
        
    },
  

    company: function (frm) {
        set_account_query_for_company(frm);
    }
    ,
     company_country: function (frm) {
        toggle_saudi_labor_field(frm);
    }
     
  

    
});

// Listener for the Child Table components
frappe.ui.form.on("Full and Final Settings Component", {
    
    is_enabled: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Check if the enabled component is "Gratuity"
        if (row.component_key === "Gratuity" && row.is_enabled) {
            
            if (!frm.doc.company) {
                frappe.model.set_value(cdt, cdn, "is_enabled", 0);
                frappe.msgprint(__("Please select a company first."));
                return;
            }
frappe.dom.freeze(__("building setting page"));

            // Fetch company country to validate
            frappe.db.get_value("Company", frm.doc.company, "country", (r) => {
                    frappe.dom.unfreeze();

                if (r && r.country !== "Saudi Arabia") {
                    
                    // Revert the checkbox
                    frappe.model.set_value(cdt, cdn, "is_enabled", 0);
                    
                    // Show English alert
                    frappe.msgprint({
                        title: __('System Restriction'),
                        indicator: 'orange',
                        message: __('Gratuity component is only applicable for companies located in Saudi Arabia.')
                    });
                }
            });
        }
    }
});

// --- Your original helper functions ---

function hide_add_row_button(frm) {
    if (frm.fields_dict.components && frm.fields_dict.components.grid) {
        frm.fields_dict.components.grid.cannot_add_rows = true;
        frm.fields_dict.components.grid.wrapper.find(".grid-add-row").hide();
        frm.fields_dict.components.grid.wrapper.find(".grid-remove-rows").hide();
    }
}

function lock_component_key_column(frm) {
    if (frm.fields_dict.components && frm.fields_dict.components.grid) {
        frm.fields_dict.components.grid.update_docfield_property("component_key", "read_only", 1);
    }
}

function set_account_query_for_company(frm) {
    if (frm.fields_dict.components && frm.fields_dict.components.grid) {
        frm.fields_dict.components.grid.get_field("account").get_query = function (doc) {
            if (!doc.company) return {};
            return {
                filters: {
                    company: doc.company,
                    is_group: 0
                }
            };
        };
    }
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
