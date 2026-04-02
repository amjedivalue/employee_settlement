
# =========================================================
# ASSETS ALLOCATED
# =========================================================

import frappe
from frappe.utils import flt


def build_assets_allocated(employee: str):
    rows = []
    total_cost = 0.0

    assets = frappe.get_all(
        "Asset",
        filters={"custodian": employee, "docstatus": 1},
        fields=["name", "asset_name", "item_name", "gross_purchase_amount", "purchase_amount", "status"],
        order_by="modified desc",
    )

    for a in assets:
        cost = flt(a.gross_purchase_amount or a.purchase_amount or 0, 2)
        title = a.asset_name or a.item_name or a.name

        rows.append({
            "reference": a.name,
            "asset_name": title,
            "cost": cost,
            "account": None,
            "action": None,
            "status": a.status or "",
        })
        total_cost += cost

    return rows, flt(total_cost, 2)

