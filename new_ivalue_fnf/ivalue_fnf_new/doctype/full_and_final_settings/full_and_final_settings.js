frappe.ui.form.on("Full and Final Settings", {
    refresh: function (frm) {
        hide_add_row_button(frm);
        lock_component_key_column(frm);
        make_grid_clean_for_hr(frm);
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


function make_grid_clean_for_hr(frm) {
    if (!frm.fields_dict.components) {
        return;
    }

    if (!frm.fields_dict.components.grid) {
        return;
    }

    frm.fields_dict.components.grid.refresh();
}