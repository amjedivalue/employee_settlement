def log_trace(message: str, data=None):
    print(f"[FNF rebuild_helpers] {message} | {data}")


def get_existing_manual_rows(doc, table_field: str) -> list[dict]:
    rows = getattr(doc, table_field, []) or []
    manual_rows = []

    for row in rows:
        if not getattr(row, "is_manual_row", 0):
            continue

        manual_rows.append({
            "component": row.component,
            "amount": row.amount,
            "account": row.account,
            "status": row.status,
            "reference_document_type": row.reference_document_type,
            "reference_document": row.reference_document,
            "remarks": getattr(row, "remarks", ""),
            "custom_number_of_days": getattr(row, "custom_number_of_days", 0),
            "is_manual_row": 1,
        })

    log_trace("manual rows collected", {
        "table": table_field,
        "count": len(manual_rows),
    })
    return manual_rows


def rebuild_table_keep_manual_only(doc, table_field: str):
    manual_rows = get_existing_manual_rows(doc, table_field)

    doc.set(table_field, [])

    for row_data in manual_rows:
        row = doc.append(table_field, {})

        for key, value in row_data.items():
            if hasattr(row, key):
                setattr(row, key, value)

    log_trace("table rebuilt with manual rows only", {
        "table": table_field,
        "count": len(manual_rows),
    })


def clear_auto_rows_keep_manual(doc):
    rebuild_table_keep_manual_only(doc, "payables")
    rebuild_table_keep_manual_only(doc, "receivables")

    if hasattr(doc, "custom_carry_forward_leaves"):
        doc.set("custom_carry_forward_leaves", [])

    log_trace("auto rows cleared and manual rows preserved", doc.name)