frappe.ui.form.on("Full and Final Settings", {
    refresh: function (frm) {
        hide_add_row_button(frm);
        lock_component_key_column(frm);
        set_account_query_for_company(frm);
        make_grid_clean_for_hr(frm);
    },

    company: function (frm) {
        set_account_query_for_company(frm);
    }
});


function hide_add_row_button(frm) {
    if (!frm.fields_dict.components) {
        return;
    }

    if (!frm.fields_dict.components.grid) {
        return;
    }

    frm.fields_dict.components.grid.cannot_add_rows = true;
    frm.fields_dict.components.grid.wrapper.find(".grid-add-row").hide();
    frm.fields_dict.components.grid.wrapper.find(".grid-remove-rows").hide();
}


function lock_component_key_column(frm) {
    if (!frm.fields_dict.components) {
        return;
    }

    if (!frm.fields_dict.components.grid) {
        return;
    }

    let grid = frm.fields_dict.components.grid;

    if (!grid.update_docfield_property) {
        return;
    }

    grid.update_docfield_property("component_key", "read_only", 1);
}


function set_account_query_for_company(frm) {
    if (!frm.fields_dict.components) {
        return;
    }

    if (!frm.fields_dict.components.grid) {
        return;
    }

    frm.fields_dict.components.grid.get_field("account").get_query = function (doc) {
        if (!doc.company) {
            return {};
        }

        return {
            filters: {
                company: doc.company,
                is_group: 0
            }
        };
    };
}


function make_grid_clean_for_hr(frm) {
    if (!frm.fields_dict.components) {
        return;
    }

    if (!frm.fields_dict.components.grid) {
        return;
    }

    frm.fields_dict.components.grid.refresh();
}