from datetime import date

import frappe
from frappe import _
from frappe.utils import cint, flt, get_first_day, getdate, nowdate, relativedelta

# ============================================================
# SECTION 1: Logging Helpers
# ============================================================


def log_trace(message: str, data=None):
    print(f"[FNF combined] {message} | {data}")


# ============================================================
# SECTION 2: Date Helpers
# ============================================================


def get_inclusive_days(start_date, end_date) -> int:
    if not start_date or not end_date:
        return 0

    start_value = getdate(start_date)
    end_value = getdate(end_date)

    if end_value < start_value:
        return 0

    return (end_value - start_value).days + 1


def get_month_first_day(any_date) -> date:
    current_date = getdate(any_date)
    return date(current_date.year, current_date.month, 1)


def get_month_last_day(any_date) -> date:
    current_date = getdate(any_date)

    if current_date.month == 12:
        next_month_first_day = date(current_date.year + 1, 1, 1)
    else:
        next_month_first_day = date(current_date.year, current_date.month + 1, 1)

    return next_month_first_day - relativedelta(days=1)


def get_days_in_month(any_date) -> int:
    month_start = get_month_first_day(any_date)
    month_end = get_month_last_day(any_date)
    return (month_end - month_start).days + 1


def get_overlap_days(app_from_date, app_to_date, range_start, range_end) -> int:
    overlap_start = max(getdate(app_from_date), getdate(range_start))
    overlap_end = min(getdate(app_to_date), getdate(range_end))

    if overlap_end < overlap_start:
        return 0

    return (overlap_end - overlap_start).days + 1


def get_total_days(from_date, to_date) -> int:
    start_date = getdate(from_date)
    end_date = getdate(to_date)

    if end_date < start_date:
        return 0

    return (end_date - start_date).days + 1


# ============================================================
# SECTION 3: Settings Helpers
# ============================================================


def get_settings_doc(company: str):
    if not company:
        return None

    settings_name = frappe.db.get_value(
        "Full and Final Settings",
        {"company": company},
        "name",
    )

    if not settings_name:
        return None

    log_trace("settings found", settings_name)
    return frappe.get_doc("Full and Final Settings", settings_name)


def validate_full_and_final_settings_exists(company: str):
    if not company:
        frappe.throw(_("Company is required to continue."))

    settings_name = frappe.db.get_value(
        "Full and Final Settings",
        {"company": company},
        "name",
    )

    if not settings_name:
        frappe.throw(
            _("Please create Full and Final Settings first for company: {0}").format(
                company
            )
        )


def get_component_setting_for_company(company: str, component_key: str):
    if not company or not component_key:
        return None

    settings_doc = get_settings_doc(company)

    if not settings_doc:
        return None

    for row in settings_doc.components:
        if row.component_key == component_key:
            return row

    return None


def get_settings_field_value(
    company: str, fieldname: str, default_value: str = ""
) -> str:
    settings_doc = get_settings_doc(company)

    if not settings_doc:
        return default_value

    value = getattr(settings_doc, fieldname, None)

    if value is None:
        return default_value

    return str(value).strip()


def get_component_label(company: str, component_key: str, fallback_label: str) -> str:
    setting_row = get_component_setting_for_company(company, component_key)

    if setting_row and setting_row.display_name:
        return setting_row.display_name

    return fallback_label


def get_component_account(
    company: str, component_key: str, fallback_account: str | None = None
) -> str | None:
    setting_row = get_component_setting_for_company(company, component_key)

    if setting_row and setting_row.account:
        return setting_row.account

    if fallback_account:
        return fallback_account

    return get_company_default_payable_account(company)


def get_component_data(
    company: str, component_key: str, fallback_account: str | None = None
) -> dict:
    setting_row = get_component_setting_for_company(company, component_key)

    if not setting_row:
        return {
            "is_enabled": 0,
            "display_name": component_key,
            "account": fallback_account,
        }

    return {
        "is_enabled": setting_row.is_enabled,
        "display_name": setting_row.display_name or component_key,
        "account": setting_row.account or fallback_account,
    }


def get_component_display_and_account(company: str, salary_type: str):
    component_key = "Additional Salary Earning"

    if salary_type == "Deduction":
        component_key = "Additional Salary Deduction"

    setting_row = get_component_setting_for_company(company, component_key)

    if not setting_row:
        return {
            "display_name": component_key,
            "account": None,
            "is_enabled": 0,
        }

    return {
        "display_name": setting_row.display_name or component_key,
        "account": setting_row.account,
        "is_enabled": setting_row.is_enabled,
    }


# ============================================================
# SECTION 4: Company / Account Helpers
# ============================================================


def get_company_currency(company: str) -> str | None:
    if not company:
        return None

    return frappe.db.get_value("Company", company, "default_currency")


def get_company_letter_head(company: str) -> str | None:
    if not company:
        return None

    return frappe.db.get_value("Company", company, "default_letter_head")


def is_valid_company_account(account: str | None, company: str) -> bool:
    """
    التأكد أن الحساب تابع لنفس الشركة وليس Group.
    """
    if not account:
        return False

    account_data = frappe.db.get_value(
        "Account",
        account,
        ["company", "is_group"],
        as_dict=True,
    )

    if not account_data:
        return False

    if account_data.company != company:
        return False

    if account_data.is_group:
        return False

    return True


def get_company_default_payable_account(company: str) -> str | None:
    if not company:
        return None

    company_doc = frappe.get_cached_doc("Company", company)

    for field_name in [
        "default_payroll_payable_account",
        "payroll_payable_account",
        "default_payable_account",
    ]:
        if hasattr(company_doc, field_name):
            field_value = getattr(company_doc, field_name)
            if field_value:
                return field_value

    return None


def get_company_employee_advance_account(company: str) -> str | None:
    if not company:
        return None

    company_doc = frappe.get_cached_doc("Company", company)

    for field_name in [
        "default_employee_advance_account",
        "default_receivable_account",
        "default_payable_account",
    ]:
        if hasattr(company_doc, field_name):
            field_value = getattr(company_doc, field_name)
            if field_value:
                return field_value

    return None


def is_valid_company_cost_center(cost_center: str | None, company: str) -> bool:
    """
    التأكد أن مركز التكلفة تابع لنفس الشركة وليس Group.
    """
    if not cost_center:
        return False

    cost_center_data = frappe.db.get_value(
        "Cost Center",
        cost_center,
        ["company", "is_group"],
        as_dict=True,
    )

    if not cost_center_data:
        return False

    if cost_center_data.company != company:
        return False

    if cost_center_data.is_group:
        return False

    return True


def get_default_cost_center(company: str) -> str | None:
    """
    جلب Default Cost Center من Full and Final Settings.
    Fieldname الحقيقي هو cost_center.
    """
    if not company:
        return None

    settings_doc = get_settings_doc(company)

    if settings_doc and getattr(settings_doc, "cost_center", None):
        settings_cost_center = settings_doc.cost_center

        if is_valid_company_cost_center(settings_cost_center, company):
            return settings_cost_center

        frappe.throw(
            _(
                "Default Cost Center {0} does not belong to Company {1}. Please update Full and Final Settings."
            ).format(
                settings_cost_center,
                company,
            )
        )

    company_cost_center = frappe.db.get_value("Company", company, "cost_center")

    if company_cost_center and is_valid_company_cost_center(
        company_cost_center, company
    ):
        return company_cost_center

    return None


# ============================================================
# SECTION 5: Employee / Salary Helpers
# ============================================================


def get_employee_basic_data(employee: str) -> dict:
    if not employee:
        return {}

    employee_data = (
        frappe.db.get_value(
            "Employee",
            employee,
            [
                "name",
                "employee_name",
                "company",
                "department",
                "designation",
                "date_of_joining",
                "relieving_date",
                "employment_type",
                "user_id",
                "custom_reason_of_leaving",
            ],
            as_dict=True,
        )
        or {}
    )

    log_trace("employee data loaded", employee_data.get("name"))
    return employee_data


def get_latest_salary_structure_assignment(employee: str, as_of_date):
    assignment_name = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": employee,
            "docstatus": 1,
            "from_date": ("<=", as_of_date),
        },
        "name",
        order_by="from_date desc",
    )

    if not assignment_name:
        frappe.throw(
            _(
                "No active Salary Structure Assignment found for employee {0}. Please create and submit a Salary Structure Assignment before creating the Full and Final Statement."
            ).format(employee)
        )

    log_trace("salary assignment found", assignment_name)
    return frappe.get_doc("Salary Structure Assignment", assignment_name)


def get_salary_currency_from_assignment(assignment):
    if not assignment:
        return None

    if getattr(assignment, "currency", None):
        return assignment.currency

    salary_structure = getattr(assignment, "salary_structure", None)
    if not salary_structure:
        return None

    return frappe.db.get_value("Salary Structure", salary_structure, "currency")


def get_salary_breakdown(assignment) -> dict:
    if not assignment:
        return {
            "basic": 0,
            "housing": 0,
            "transportation": 0,
            "other": 0,
            "monthly_total": 0,
        }

    basic_salary = flt(getattr(assignment, "base", 0))
    housing = flt(getattr(assignment, "custom_housing", 0))
    transportation = flt(getattr(assignment, "custom_travelling", 0))
    other = flt(getattr(assignment, "custom_other_allowance", 0))

    return {
        "basic": basic_salary,
        "housing": housing,
        "transportation": transportation,
        "other": other,
        "monthly_total": flt(basic_salary + housing + transportation + other, 2),
    }


# ============================================================
# SECTION 6: Row Builder Helpers
# ============================================================


def append_row(
    doc,
    table_field: str,
    component: str,
    amount: float,
    account: str | None = None,
    reference_document_type: str | None = None,
    reference_document: str | None = None,
    custom_number_of_days: float = 0,
    paid_via_salary_slip: int = 0,
):
    if flt(amount) <= 0:
        log_trace("skip zero row", {"component": component, "amount": amount})
        return

    row = doc.append(table_field, {})
    row.component = component
    row.amount = flt(amount, 2)
    row.account = account
    row.status = "Settled"
    row.reference_document_type = reference_document_type
    row.reference_document = reference_document
    if hasattr(row, "paid_via_salary_slip"):
        saved_paid_via_salary_slip = 0

        paid_via_salary_slip_map = getattr(doc, "_paid_via_salary_slip_map", {}) or {}

        if reference_document_type and reference_document:
            saved_paid_via_salary_slip = cint(
                paid_via_salary_slip_map.get(
                    (reference_document_type, reference_document),
                    paid_via_salary_slip,
                )
            )

        row.paid_via_salary_slip = saved_paid_via_salary_slip

    if hasattr(row, "custom_number_of_days"):
        row.custom_number_of_days = flt(custom_number_of_days, 2)

    if hasattr(row, "custom_is_manual_row"):
        row.custom_is_manual_row = 0

    if hasattr(row, "cost_center"):
        if (
            hasattr(doc, "custom_default_cost_center")
            and doc.custom_default_cost_center
        ):
            row.cost_center = doc.custom_default_cost_center
        else:
            row.cost_center = frappe.db.get_value("Company", doc.company, "cost_center")
    log_trace(
        "row appended",
        {
            "table": table_field,
            "component": component,
            "amount": row.amount,
        },
    )


def apply_document_header(doc, employee_data: dict):
    doc.employee_name = employee_data.get("employee_name")
    doc.company = employee_data.get("company")
    doc.department = employee_data.get("department")
    doc.designation = employee_data.get("designation")
    if hasattr(doc, "custom_user_id"):
        doc.custom_user_id = employee_data.get("user_id")

    if not doc.date_of_joining:
        doc.date_of_joining = employee_data.get("date_of_joining")

    if not doc.relieving_date:
        doc.relieving_date = employee_data.get("relieving_date")


def apply_salary_snapshot(doc, assignment, salary_data: dict):
    doc.custom_company_currency = get_salary_currency_from_assignment(
        assignment
    ) or get_company_currency(doc.company)
    doc.custom_basic_salary = flt(salary_data.get("basic"), 2)
    doc.custom_housing = flt(salary_data.get("housing"), 2)
    doc.custom_transportation = flt(salary_data.get("transportation"), 2)
    doc.custom_other_allowances = flt(salary_data.get("other"), 2)
    doc.custom_monthly_gross_salary = flt(salary_data.get("monthly_total"), 2)


# ============================================================
# SECTION 7: Rebuild Helpers
# ============================================================


def get_existing_manual_rows(doc, table_field: str) -> list[dict]:
    rows = getattr(doc, table_field, []) or []
    manual_rows = []

    for row in rows:
        is_marked_manual = getattr(row, "custom_is_manual_row", 0)

        reference_document_type = str(
            getattr(row, "reference_document_type", "") or ""
        ).strip()
        reference_document = str(getattr(row, "reference_document", "") or "").strip()

        has_pending_manual_values = (
            getattr(row, "component", None)
            and flt(getattr(row, "amount", 0)) > 0
            and not reference_document_type
            and not reference_document
        )

        if not is_marked_manual and not has_pending_manual_values:
            continue

        manual_rows.append(
            {
                "component": row.component,
                "amount": row.amount,
                "account": row.account,
                "status": row.status,
                "reference_document_type": reference_document_type,
                "reference_document": reference_document,
                "remarks": getattr(row, "remarks", ""),
                "custom_number_of_days": getattr(row, "custom_number_of_days", 0),
                "cost_center": getattr(row, "cost_center", None),
                "paid_via_salary_slip": cint(getattr(row, "paid_via_salary_slip", 0)),
                "custom_is_manual_row": 1,
            }
        )

    log_trace(
        "manual rows collected",
        {
            "table": table_field,
            "count": len(manual_rows),
        },
    )

    return manual_rows


def rebuild_table_keep_manual_only(doc, table_field: str):
    manual_rows = get_existing_manual_rows(doc, table_field)

    doc.set(table_field, [])

    for row_data in manual_rows:
        row = doc.append(table_field, {})

        for key, value in row_data.items():
            if hasattr(row, key):
                setattr(row, key, value)

    log_trace(
        "table rebuilt with manual rows only",
        {
            "table": table_field,
            "count": len(manual_rows),
        },
    )


def clear_auto_rows_keep_manual(doc):
    rebuild_table_keep_manual_only(doc, "payables")
    rebuild_table_keep_manual_only(doc, "receivables")

    if hasattr(doc, "custom_carry_forward_leaves"):
        doc.set("custom_carry_forward_leaves", [])

    log_trace("auto rows cleared and manual rows preserved", doc.name)


def clear_auto_tables(doc):
    clear_auto_rows_keep_manual(doc)
    log_trace("auto rows cleared and manual rows preserved", doc.name)


# ============================================================
# SECTION 8: Salary Days Builder
# ============================================================


def build_salary_days_payable(doc):
    salary_days_setting = get_component_setting_for_company(doc.company, "Salary Days")

    if not salary_days_setting:
        log_trace("salary days skipped because setting is missing")
        return

    if not salary_days_setting.is_enabled:
        log_trace("salary days skipped because disabled in settings")
        return

    assignment = get_latest_salary_structure_assignment(
        doc.employee, doc.relieving_date
    )

    if not assignment:
        frappe.throw("No Salary Structure Assignment found for this employee.")

    salary_data = get_salary_breakdown(assignment)
    apply_salary_snapshot(doc, assignment, salary_data)

    monthly_total = flt(salary_data.get("monthly_total"))
    month_start = get_month_first_day(doc.relieving_date)
    month_days = get_days_in_month(doc.relieving_date)

    if doc.date_of_joining and getdate(doc.date_of_joining) > month_start:
        month_start = getdate(doc.date_of_joining)

    worked_days = get_inclusive_days(month_start, doc.relieving_date)
    daily_rate = flt(monthly_total / 30, 2)

    if worked_days >= month_days:
        final_amount = flt(monthly_total, 2)
    else:
        final_amount = flt(daily_rate * worked_days, 2)

    if hasattr(doc, "custom_work_days"):
        doc.custom_work_days = flt(worked_days, 2)

    component = salary_days_setting.display_name or "Salary Days"
    account = salary_days_setting.account or get_company_default_payable_account(
        doc.company
    )

    append_row(
        doc=doc,
        table_field="payables",
        component=component,
        amount=final_amount,
        account=account,
        reference_document_type="Salary Structure Assignment",
        reference_document=assignment.name,
        custom_number_of_days=worked_days,
    )

    log_trace(
        "salary days built",
        {
            "assignment": assignment.name,
            "worked_days": worked_days,
            "amount": final_amount,
        },
    )


# ============================================================
# SECTION 9: Leave Encashment Builder
# ============================================================


def get_personal_leave_days_by_type(employee: str, end_date) -> dict:
    if not employee or not end_date:
        return {}

    month_start = get_first_day(getdate(end_date))

    personal_leaves = frappe.get_all(
        "Personal Leave",
        filters={
            "employee": employee,
            "date": ["between", [month_start, end_date]],
            "docstatus": 1,
        },
        fields=["leave_type", "hours"],
    )

    leave_days_by_type = {}

    for row in personal_leaves:
        leave_type = row.get("leave_type")
        if not leave_type:
            continue

        days = flt(flt(row.get("hours")) / 8, 2)

        if leave_type not in leave_days_by_type:
            leave_days_by_type[leave_type] = 0.0

        leave_days_by_type[leave_type] = flt(leave_days_by_type[leave_type] + days, 2)

    log_trace("personal leave types counted", leave_days_by_type)
    return leave_days_by_type


def get_carry_forward_leave_types():
    return frappe.get_all(
        "Leave Type",
        filters={"is_carry_forward": 1},
        pluck="name",
    )


def get_latest_leave_allocation(employee: str, leave_type: str, end_date):
    rows = frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": employee,
            "leave_type": leave_type,
            "docstatus": 1,
            "from_date": ("<=", end_date),
        },
        fields=[
            "name",
            "from_date",
            "to_date",
            "total_leaves_allocated",
            "extra_days",
        ],
        order_by="from_date desc, to_date desc, modified desc",
        limit=1,
    )

    if not rows:
        return None

    return rows[0]


def get_leave_taken_days(
    employee: str,
    leave_type: str,
    allocation_start,
    end_date,
    personal_leave_days_by_type: dict,
) -> float:
    leave_applications = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee,
            "leave_type": leave_type,
            "docstatus": 1,
            "status": "Approved",
            "from_date": ("<=", end_date),
            "to_date": (">=", allocation_start),
        },
        fields=["from_date", "to_date", "total_leave_days"],
    )

    taken = 0.0

    for app in leave_applications:
        overlap_days = get_overlap_days(
            app.from_date,
            app.to_date,
            allocation_start,
            end_date,
        )
        total_days = get_total_days(app.from_date, app.to_date)

        if total_days > 0 and overlap_days > 0:
            taken += flt(app.total_leave_days) * (flt(overlap_days) / flt(total_days))

    taken += flt(personal_leave_days_by_type.get(leave_type, 0))
    return flt(taken, 2)


def build_leave_encashment_rows(doc):
    setting_row = get_component_setting_for_company(doc.company, "Leaves")

    if not setting_row or not setting_row.is_enabled:
        log_trace("leave encashment skipped because disabled")
        return

    personal_leave_days_by_type = get_personal_leave_days_by_type(
        doc.employee, doc.relieving_date
    )
    carry_forward_leave_types = get_carry_forward_leave_types()
    daily_rate = flt(flt(doc.custom_monthly_gross_salary) / 30, 2)

    for leave_type in carry_forward_leave_types:
        allocation = get_latest_leave_allocation(
            doc.employee, leave_type, doc.relieving_date
        )

        if not allocation:
            continue

        earned = flt(allocation.total_leaves_allocated) + flt(allocation.extra_days)
        taken = get_leave_taken_days(
            doc.employee,
            leave_type,
            allocation.from_date,
            doc.relieving_date,
            personal_leave_days_by_type,
        )
        balance = flt(earned - taken, 2)

        if balance <= 0:
            continue

        amount = flt(balance * daily_rate, 2)
        component_label = setting_row.display_name or "Leaves"
        leave_format = get_settings_field_value(doc.company, "leave_format", "New Name")

        if leave_format == "Leave Type- New Name":
            component_label = f"{leave_type} - {component_label}"
        elif leave_format == "New Name - Leave Type":
            component_label = f"{component_label} - {leave_type}"

        append_row(
            doc=doc,
            table_field="payables",
            component=component_label,
            amount=amount,
            account=setting_row.account,
            reference_document_type="Leave Allocation",
            reference_document=allocation.name,
            custom_number_of_days=balance,
        )

        if hasattr(doc, "custom_carry_forward_leaves"):
            leave_row = doc.append("custom_carry_forward_leaves", {})
            leave_row.leave_type = leave_type
            leave_row.earned_leaves = flt(earned, 2)
            leave_row.taken_leaves = flt(taken, 2)
            leave_row.remaining_leaves = flt(balance, 2)

        log_trace(
            "leave encashment row added",
            {
                "leave_type": leave_type,
                "balance": balance,
                "amount": amount,
            },
        )


# ============================================================
# SECTION 10: Gratuity Builder
# ============================================================


def normalize_text(value) -> str:
    """
    توحيد النص قبل المقارنة.
    """
    if not value:
        return ""

    return str(value).strip()


def is_saudi_gratuity_allowed(
    company_country: str, employment_type: str, reason_of_leaving: str
) -> bool:
    """
    تحديد هل الموظف مؤهل لحساب مكافأة نهاية الخدمة حسب القاعدة الحالية.

    هذه نسخة مؤقتة Hardcoded.

    الشروط:
    - الشركة في السعودية
    - نوع التوظيف Permanent
    - سبب المغادرة ضمن الأسباب المعتمدة
    """
    if normalize_text(company_country) != "Saudi Arabia":
        return False

    if normalize_text(employment_type) != "Permanent":
        return False

    if normalize_text(reason_of_leaving) not in [
        "End of contract",
        "Termination",
        "Resignation",
    ]:
        return False

    return True


def calculate_base_gratuity(service_years: float, monthly_salary: float) -> float:
    """
    حساب المكافأة الأساسية حسب قاعدة السعودية الحالية.

    أول 5 سنوات:
    نصف راتب شهري عن كل سنة.

    بعد 5 سنوات:
    راتب شهري كامل عن كل سنة إضافية.
    """
    if service_years <= 0:
        return 0

    if monthly_salary <= 0:
        return 0

    if service_years <= 5:
        return flt(service_years * (monthly_salary / 2), 2)

    first_five_years_amount = flt(5 * (monthly_salary / 2), 2)
    remaining_years_amount = flt((service_years - 5) * monthly_salary, 2)

    return flt(first_five_years_amount + remaining_years_amount, 2)


def apply_resignation_rule(
    amount: float, service_years: float, reason_of_leaving: str
) -> float:
    """
    تطبيق تخفيض الاستقالة.

    إذا السبب ليس Resignation:
    يرجع المبلغ كامل.

    إذا السبب Resignation:
    - أقل من سنتين: لا يستحق
    - من 2 إلى أقل من 5: ثلث المكافأة
    - من 5 إلى أقل من 10: ثلثين المكافأة
    - 10 سنوات فأكثر: كامل المكافأة
    """
    if normalize_text(reason_of_leaving) != "Resignation":
        return flt(amount, 2)

    if service_years < 2:
        return 0

    if service_years < 5:
        return flt(amount / 3, 2)

    if service_years < 10:
        return flt((amount * 2) / 3, 2)

    return flt(amount, 2)


def get_gratuity_setting(company: str):
    """
    جلب سطر Gratuity من Auto Rows Settings.

    نستخدمه فقط من أجل:
    - هل Gratuity مفعلة؟
    - الاسم الظاهر في Payables
    - الحساب المستخدم
    """
    return get_component_setting_for_company(company, "Gratuity")


def build_gratuity_payable(doc):
    """
    بناء سطر مكافأة نهاية الخدمة داخل Payables مباشرة.

    هذه النسخة لا تنشئ Standard Gratuity Document.
    هذه النسخة لا تستخدم Gratuity Rule.
    هذه النسخة تعتمد على:
    - company_country
    - custom_employment_type
    - custom_reason_of_leaving
    - custom_total_of_years
    - custom_monthly_gross_salary
    - Gratuity row في Auto Rows Settings
    """
    company_country = getattr(doc, "company_country", None)
    employment_type = getattr(doc, "custom_employment_type", None)
    reason_of_leaving = getattr(doc, "custom_reason_of_leaving", None)
    service_years = flt(getattr(doc, "custom_total_of_years", 0))
    monthly_salary = flt(getattr(doc, "custom_monthly_gross_salary", 0))

    if not is_saudi_gratuity_allowed(
        company_country, employment_type, reason_of_leaving
    ):
        log_trace(
            "gratuity skipped by policy",
            {
                "company_country": company_country,
                "employment_type": employment_type,
                "reason_of_leaving": reason_of_leaving,
            },
        )
        return

    gratuity_setting = get_gratuity_setting(doc.company)

    if not gratuity_setting:
        log_trace("gratuity skipped because setting row is missing")
        return

    if not gratuity_setting.is_enabled:
        log_trace("gratuity skipped because disabled in settings")
        return

    base_amount = calculate_base_gratuity(
        service_years=service_years,
        monthly_salary=monthly_salary,
    )

    final_amount = apply_resignation_rule(
        amount=base_amount,
        service_years=service_years,
        reason_of_leaving=reason_of_leaving,
    )

    if flt(final_amount) <= 0:
        log_trace(
            "gratuity amount is zero",
            {
                "service_years": service_years,
                "monthly_salary": monthly_salary,
                "reason_of_leaving": reason_of_leaving,
            },
        )
        return

    append_row(
        doc=doc,
        table_field="payables",
        component=gratuity_setting.display_name or "Gratuity",
        amount=final_amount,
        account=gratuity_setting.account,
        reference_document_type="Employee",
        reference_document=doc.employee,
    )

    log_trace(
        "gratuity row added",
        {
            "amount": final_amount,
            "service_years": service_years,
            "monthly_salary": monthly_salary,
            "reason_of_leaving": reason_of_leaving,
        },
    )


# ============================================================
# SECTION 11: Monthly Additional Salary Builder
# ============================================================


def get_additional_salary_rows(employee: str, relieving_date):
    if not employee or not relieving_date:
        return []

    relieving_date_value = getdate(relieving_date)
    month_start = relieving_date_value.replace(day=1)
    month_end = get_month_last_day(relieving_date_value)

    rows = frappe.get_all(
        "Additional Salary",
        filters={
            "employee": employee,
            "docstatus": 1,
            "payroll_date": ["between", [month_start, month_end]],
        },
        fields=[
            "name",
            "salary_component",
            "payroll_date",
            "amount",
            "type",
        ],
    )

    filtered_rows = []

    for row in rows:
        if flt(row.amount) <= 0:
            continue

        if frappe.db.has_column("Additional Salary", "custom_created_from_fnf"):
            created_from_fnf = frappe.db.get_value(
                "Additional Salary",
                row.name,
                "custom_created_from_fnf",
            )

            if created_from_fnf:
                continue

        filtered_rows.append(row)

    log_trace("monthly additional salary rows", len(filtered_rows))
    return filtered_rows


def build_monthly_additional_salary_rows(doc):
    rows = get_additional_salary_rows(doc.employee, doc.relieving_date)

    for row in rows:
        setting_data = get_component_display_and_account(doc.company, row.type)

        if not setting_data["is_enabled"]:
            log_trace(
                "skip disabled setting",
                {
                    "type": row.type,
                    "salary_component": row.salary_component,
                },
            )
            continue

        component_label = setting_data["display_name"]
        additional_salary_format = get_settings_field_value(
            doc.company, "additional_salary_format", "Component"
        )

        if row.salary_component:
            if additional_salary_format == "Component - New Name":
                component_label = f"{row.salary_component} - {component_label}"
            elif additional_salary_format == "New Name -Component":
                component_label = f"{component_label} - {row.salary_component}"
            else:
                component_label = row.salary_component

        target_table = "payables"
        if row.type == "Deduction":
            target_table = "receivables"

        append_row(
            doc=doc,
            table_field=target_table,
            component=component_label,
            amount=row.amount,
            account=setting_data["account"],
            reference_document_type="Additional Salary",
            reference_document=row.name,
        )

        log_trace(
            "monthly additional salary row added",
            {
                "table": target_table,
                "name": row.name,
                "amount": row.amount,
            },
        )


# ============================================================
# SECTION 12: Outstanding Items Builders
# ============================================================


def get_open_employee_advances(employee: str):
    if not employee:
        return []

    fields = [
        "name",
        "purpose",
        "advance_amount",
        "paid_amount",
        "claimed_amount",
        "status",
    ]

    if frappe.db.has_column("Employee Advance", "returned_amount"):
        fields.append("returned_amount")

    rows = frappe.get_all(
        "Employee Advance",
        filters={
            "employee": employee,
            "docstatus": 1,
            "paid_amount": [">", 0],
            "status": [
                "not in",
                ["Claimed", "Returned", "Partly Claimed and Returned", "Cancelled"],
            ],
        },
        fields=fields,
    )

    log_trace("employee advances found", len(rows))
    return rows


def get_open_expense_claims(employee: str):
    if not employee:
        return []

    rows = frappe.get_all(
        "Expense Claim",
        filters={
            "employee": employee,
            "docstatus": 1,
            "approval_status": "Approved",
        },
        fields=[
            "name",
            "total_claimed_amount",
            "total_sanctioned_amount",
            "grand_total",
            "total_amount_reimbursed",
            "approval_status",
        ],
    )

    log_trace("expense claims found", len(rows))
    return rows


def build_employee_advance_rows(doc):
    component_data = get_component_data(
        company=doc.company,
        component_key="Employee Advance",
        fallback_account=get_company_employee_advance_account(doc.company),
    )

    if not component_data["is_enabled"]:
        log_trace("employee advance skipped because disabled")
        return

    rows = get_open_employee_advances(doc.employee)

    for row in rows:
        returned_amount = flt(getattr(row, "returned_amount", 0))

        outstanding_amount = (
            flt(row.paid_amount) - flt(row.claimed_amount) - returned_amount
        )

        if flt(outstanding_amount) <= 0:
            continue

        component_label = component_data["display_name"]
        advance_format = get_settings_field_value(
            doc.company, "employee_advnace_format", "New Name"
        )

        if row.purpose:
            if advance_format == "Purpose - New Name":
                component_label = f"{row.purpose} - {component_label}"
            elif advance_format == "New Name - Purpose":
                component_label = f"{component_label} - {row.purpose}"

        append_row(
            doc=doc,
            table_field="receivables",
            component=component_label,
            amount=outstanding_amount,
            account=component_data["account"],
            reference_document_type="Employee Advance",
            reference_document=row.name,
        )

        log_trace(
            "employee advance row added",
            {
                "name": row.name,
                "amount": outstanding_amount,
            },
        )


def build_expense_claim_rows(doc):
    component_data = get_component_data(
        company=doc.company,
        component_key="Expense Claim",
        fallback_account=get_company_default_payable_account(doc.company),
    )

    if not component_data["is_enabled"]:
        log_trace("expense claim skipped because disabled")
        return

    rows = get_open_expense_claims(doc.employee)

    for row in rows:
        approved_amount = (
            flt(row.total_sanctioned_amount)
            or flt(row.total_claimed_amount)
            or flt(row.grand_total)
        )

        reimbursed_amount = flt(row.total_amount_reimbursed)
        outstanding_amount = flt(approved_amount - reimbursed_amount, 2)

        if outstanding_amount <= 0:
            continue

        append_row(
            doc=doc,
            table_field="payables",
            component=component_data["display_name"],
            amount=outstanding_amount,
            account=component_data["account"],
            reference_document_type="Expense Claim",
            reference_document=row.name,
        )

        log_trace(
            "expense claim row added",
            {
                "name": row.name,
                "amount": outstanding_amount,
            },
        )


# ============================================================
# SECTION 13: Manual Rows / Additional Salary Sync
# ============================================================


def get_manual_row_type_from_table_name(table_name: str) -> str | None:
    if table_name == "Payables":
        return "Payables Manual Row"

    if table_name == "Receivables":
        return "Receivables Manual Row"

    return None


def get_manual_row_setting(company: str, row_type: str):
    settings_doc = get_settings_doc(company)

    if not settings_doc:
        return None

    manual_row_settings = getattr(settings_doc, "manual_row_settings", []) or []

    for row in manual_row_settings:
        if row.row_type == row_type:
            return row

    return None


def get_expected_salary_component_type(table_name: str) -> str | None:
    if table_name == "Payables":
        return "Earning"

    if table_name == "Receivables":
        return "Deduction"

    return None


def validate_salary_component_type(salary_component: str, expected_type: str):
    if not salary_component:
        frappe.throw(_("Salary Component is required in Full and Final Settings."))

    salary_component_type = frappe.db.get_value(
        "Salary Component",
        salary_component,
        "type",
    )

    if not salary_component_type:
        frappe.throw(_("Salary Component {0} does not exist.").format(salary_component))

    if salary_component_type != expected_type:
        frappe.throw(
            _("Salary Component {0} must be type {1}. Current type is {2}.").format(
                salary_component,
                expected_type,
                salary_component_type,
            )
        )


@frappe.whitelist()
def get_manual_row_defaults(
    company: str,
    table_name: str,
    component: str = None,
    amount: float = 0,
    document_name: str = None,
):
    if not company:
        frappe.throw(_("Company is required."))

    if not table_name:
        frappe.throw(_("Table name is required."))

    row_type = get_manual_row_type_from_table_name(table_name)

    if not row_type:
        frappe.throw(_("Invalid manual row table."))

    setting_row = get_manual_row_setting(company, row_type)

    if not setting_row:
        frappe.throw(
            _("Manual row settings are not configured for {0}.").format(row_type)
        )

    if not setting_row.is_enabled:
        frappe.throw(_("{0} is disabled in Full and Final Settings.").format(row_type))

    salary_component = getattr(setting_row, "salary_component", None)
    expected_type = get_expected_salary_component_type(table_name)

    validate_salary_component_type(salary_component, expected_type)

    return {
        "status": "Settled",
        "custom_is_manual_row": 1,
    }


def is_manual_additional_salary_row(row) -> bool:
    if not cint(getattr(row, "custom_is_manual_row", 0)):
        return False

    amount = flt(getattr(row, "amount", 0))

    if amount <= 0:
        return False

    return True


def create_manual_additional_salary(
    employee: str,
    company: str,
    payroll_date,
    salary_component: str,
    expected_type: str,
    amount: float,
):
    validate_salary_component_type(salary_component, expected_type)

    additional_salary_doc = frappe.new_doc("Additional Salary")
    additional_salary_doc.employee = employee
    additional_salary_doc.company = company
    additional_salary_doc.payroll_date = payroll_date
    additional_salary_doc.salary_component = salary_component
    additional_salary_doc.amount = flt(amount, 2)
    additional_salary_doc.overwrite_salary_structure_amount = 0

    if hasattr(additional_salary_doc, "custom_created_from_fnf"):
        additional_salary_doc.custom_created_from_fnf = 1

    additional_salary_doc.insert(ignore_permissions=True)
    additional_salary_doc.submit()

    return additional_salary_doc


def cancel_additional_salary_if_needed(additional_salary_name: str):
    if not additional_salary_name:
        return

    additional_salary_doc = frappe.get_doc("Additional Salary", additional_salary_name)

    if hasattr(additional_salary_doc, "custom_created_from_fnf"):
        if not additional_salary_doc.custom_created_from_fnf:
            return

    if additional_salary_doc.docstatus == 1:
        additional_salary_doc.cancel()


def sync_manual_rows_for_table(doc, table_field: str, table_name: str):
    row_type = get_manual_row_type_from_table_name(table_name)
    expected_type = get_expected_salary_component_type(table_name)

    setting_row = get_manual_row_setting(doc.company, row_type)

    if not setting_row:
        return

    if not setting_row.is_enabled:
        return

    salary_component = getattr(setting_row, "salary_component", None)

    validate_salary_component_type(salary_component, expected_type)

    for row in getattr(doc, table_field, []) or []:
        if not is_manual_additional_salary_row(row):
            continue

        old_reference_type = str(
            getattr(row, "reference_document_type", "") or ""
        ).strip()
        old_reference_name = str(getattr(row, "reference_document", "") or "").strip()

        row.status = "Settled"

        if old_reference_type == "Additional Salary" and old_reference_name:
            additional_salary_amount = frappe.db.get_value(
                "Additional Salary",
                old_reference_name,
                "amount",
            )

            additional_salary_component = frappe.db.get_value(
                "Additional Salary",
                old_reference_name,
                "salary_component",
            )

            if (
                flt(additional_salary_amount, 2) == flt(row.amount, 2)
                and additional_salary_component == salary_component
            ):
                continue

            cancel_additional_salary_if_needed(old_reference_name)

        additional_salary_doc = create_manual_additional_salary(
            employee=doc.employee,
            company=doc.company,
            payroll_date=doc.relieving_date,
            salary_component=salary_component,
            expected_type=expected_type,
            amount=row.amount,
        )

        row.reference_document_type = "Additional Salary"
        row.reference_document = additional_salary_doc.name
        row.custom_is_manual_row = 1


def sync_manual_rows_to_additional_salary(doc):
    sync_manual_rows_for_table(
        doc=doc,
        table_field="payables",
        table_name="Payables",
    )

    sync_manual_rows_for_table(
        doc=doc,
        table_field="receivables",
        table_name="Receivables",
    )


def cancel_deleted_manual_additional_salary_rows(doc):
    old_doc = doc.get_doc_before_save()

    if not old_doc:
        return

    current_references = set()

    for row in (doc.payables or []) + (doc.receivables or []):
        reference_document_type = str(
            getattr(row, "reference_document_type", "") or ""
        ).strip()
        reference_document = str(getattr(row, "reference_document", "") or "").strip()

        if reference_document_type == "Additional Salary" and reference_document:
            current_references.add(reference_document)

    for row in (old_doc.payables or []) + (old_doc.receivables or []):
        if not cint(getattr(row, "custom_is_manual_row", 0)):
            continue

        reference_document_type = str(
            getattr(row, "reference_document_type", "") or ""
        ).strip()
        reference_document = str(getattr(row, "reference_document", "") or "").strip()

        if reference_document_type != "Additional Salary":
            continue

        if not reference_document:
            continue

        if reference_document in current_references:
            continue

        cancel_additional_salary_if_needed(reference_document)


# ============================================================
# SECTION 14: Main Service / Hook Methods
# ============================================================


def set_transaction_date(doc, method=None):
    if not doc.transaction_date:
        doc.transaction_date = nowdate()

    log_trace("transaction date set", doc.transaction_date)


def validate_required_values(doc):
    if not doc.employee:
        log_trace("skip build because employee is empty")
        return False

    if not doc.relieving_date:
        log_trace("skip build because relieving_date is empty")
        return False

    return True


def apply_service_period(doc):
    if not doc.date_of_joining or not doc.relieving_date:
        return

    start_date = getdate(doc.date_of_joining)
    end_date = getdate(doc.relieving_date)

    if end_date < start_date:
        frappe.throw("Relieving Date cannot be before Date of Joining.")

    difference = relativedelta(end_date + relativedelta(days=1), start_date)
    total_days = (end_date - start_date).days + 1

    doc.custom_service_years = difference.years
    doc.custom_service_month = difference.months
    doc.custom_service_days = difference.days
    doc.custom_total_of_years = flt(total_days / 365, 6)

    log_trace(
        "service period applied",
        {
            "years": doc.custom_service_years,
            "months": doc.custom_service_month,
            "days": doc.custom_service_days,
        },
    )


def get_closed_workflow_states():
    return ["Cancel", "Signed"]


def warn_if_another_fnf_exists(doc):
    existing_doc = frappe.db.get_value(
        "Full and Final Statement",
        {
            "employee": doc.employee,
            "name": ["!=", doc.name or ""],
            "docstatus": ["!=", 2],
        },
        ["name", "workflow_state"],
        as_dict=True,
    )

    if not existing_doc:
        print(f"[FNF service] no other fnf found | employee={doc.employee}")
        return

    print(
        f"[FNF service] warning other fnf exists | "
        f"name={existing_doc.name} state={existing_doc.workflow_state}"
    )

    frappe.msgprint(
        msg=_(
            "Another Full and Final Statement already exists for this employee: {0}. Current state: {1}."
        ).format(existing_doc.name, existing_doc.workflow_state),
        title=_("Existing Full and Final Statement"),
        indicator="orange",
    )


def load_base_document_data(doc):
    employee_data = get_employee_basic_data(doc.employee)

    if not employee_data:
        frappe.throw("Employee data not found.")

    apply_document_header(doc, employee_data)
    validate_full_and_final_settings_exists(doc.company)

    doc.custom_letter_head = get_company_letter_head(doc.company)
    doc.company_country = frappe.db.get_value("Company", doc.company, "country")

    if hasattr(doc, "custom_default_cost_center"):
        doc.custom_default_cost_center = frappe.db.get_value(
            "Company", doc.company, "cost_center"
        )

    doc.custom_employment_type = doc.custom_employment_type or employee_data.get(
        "employment_type"
    )
    doc.custom_reason_of_leaving = doc.custom_reason_of_leaving or employee_data.get(
        "custom_reason_of_leaving"
    )

    assignment = get_latest_salary_structure_assignment(
        doc.employee, doc.relieving_date
    )

    if assignment:
        salary_data = get_salary_breakdown(assignment)
        apply_salary_snapshot(doc, assignment, salary_data)

    apply_service_period(doc)
    return employee_data


def populate_full_and_final_doc(doc, method=None):
    log_trace("populate started", {"doc": doc.name, "employee": doc.employee})

    if not validate_required_values(doc):
        return
    cancel_deleted_manual_additional_salary_rows(doc)

    warn_if_another_fnf_exists(doc)
    load_base_document_data(doc)
    paid_via_salary_slip_map = {}

    for row in (doc.payables or []) + (doc.receivables or []):
        reference_document_type = str(
            getattr(row, "reference_document_type", "") or ""
        ).strip()
        reference_document = str(getattr(row, "reference_document", "") or "").strip()

        if reference_document_type and reference_document:
            paid_via_salary_slip_map[(reference_document_type, reference_document)] = (
                cint(getattr(row, "paid_via_salary_slip", 0))
            )

    doc._paid_via_salary_slip_map = paid_via_salary_slip_map
    clear_auto_tables(doc)

    build_salary_days_payable(doc)
    build_gratuity_payable(doc)
    build_monthly_additional_salary_rows(doc)
    build_employee_advance_rows(doc)
    build_leave_encashment_rows(doc)

    sync_manual_rows_to_additional_salary(doc)

    apply_totals(doc)

    log_trace(
        "populate finished",
        {
            "payables": len(doc.payables or []),
            "receivables": len(doc.receivables or []),
            "total_payable_amount": doc.total_payable_amount,
            "total_receivable_amount": doc.total_receivable_amount,
        },
    )


def enqueue_rebuild_after_first_insert(doc, method=None):
    """
    بعد أول حفظ، نطلب من النظام يعمل إعادة بناء في الخلفية.

    هذا يمنع ضغط السيرفر أثناء عملية الحفظ الأصلية.
    """
    frappe.enqueue(
        method="new_ivalue_fnf.api.full_and_final.service.rebuild_saved_full_and_final_statement",
        queue="short",
        timeout=300,
        enqueue_after_commit=True,
        docname=doc.name,
    )

    log_trace("queued rebuild after first insert", doc.name)


def rebuild_saved_full_and_final_statement(docname: str):
    """
    إعادة بناء Full and Final Statement بعد أول حفظ.
    تستخدم لضمان اكتمال بيانات المستند بعد insert.
    """
    doc = frappe.get_doc("Full and Final Statement", docname)

    doc.flags.skip_duplicate_fnf_warning = True

    populate_full_and_final_doc(doc)

    doc.save(ignore_permissions=True)

    frappe.db.commit()

    log_trace("background rebuild finished", doc.name)

def apply_totals(doc):
    total_payables = 0
    total_receivables = 0

    for row in doc.payables or []:
        if cint(getattr(row, "paid_via_salary_slip", 0)):
            continue

        total_payables += flt(row.amount)

    for row in doc.receivables or []:
        total_receivables += flt(row.amount)

    doc.total_payable_amount = flt(total_payables, 2)
    doc.total_receivable_amount = flt(total_receivables, 2)
@frappe.whitelist()
def explain_settlement_amount(doc_json: str, row_json: str, table_field: str):
    if not doc_json:
        frappe.throw(_("Document data is required."))

    if not row_json:
        frappe.throw(_("Row data is required."))

    doc_data = frappe.parse_json(doc_json)
    row_data = frappe.parse_json(row_json)

    doc = frappe.get_doc(doc_data)

    reference_document_type = str(row_data.get("reference_document_type") or "").strip()
    reference_document = str(row_data.get("reference_document") or "").strip()
    component = str(row_data.get("component") or "").strip()
    amount = flt(row_data.get("amount"), 2)
    custom_number_of_days = flt(row_data.get("custom_number_of_days"), 2)
    custom_is_manual_row = cint(row_data.get("custom_is_manual_row"))

    if custom_is_manual_row:
        return explain_manual_row(
            doc=doc,
            row_data=row_data,
            table_field=table_field,
        )

    if reference_document_type == "Salary Structure Assignment":
        return explain_salary_days_amount(
            doc=doc,
            component=component,
            amount=amount,
            custom_number_of_days=custom_number_of_days,
            reference_document=reference_document,
        )

    if reference_document_type == "Leave Allocation":
        return explain_leave_amount(
            doc=doc,
            component=component,
            amount=amount,
            custom_number_of_days=custom_number_of_days,
            reference_document=reference_document,
        )

    if reference_document_type == "Additional Salary":
        return explain_additional_salary_amount(
            component=component,
            amount=amount,
            reference_document=reference_document,
            table_field=table_field,
        )

    if reference_document_type == "Employee Advance":
        return explain_employee_advance_amount(
            component=component,
            amount=amount,
            reference_document=reference_document,
        )

    if reference_document_type == "Employee":
        return explain_gratuity_amount(
            doc=doc,
            component=component,
            amount=amount,
        )

    return {
        "title": component or "Settlement Row",
        "summary": "This amount is available on the row, but no detailed explanation rule was found for its source.",
        "lines": [
            {
                "label": "Component",
                "value": component or "-",
            },
            {
                "label": "Amount",
                "value": amount,
            },
            {
                "label": "Source",
                "value": "{0} {1}".format(
                    reference_document_type or "-", reference_document or ""
                ),
            },
        ],
    }


def explain_salary_days_amount(
    doc,
    component: str,
    amount: float,
    custom_number_of_days: float,
    reference_document: str,
):
    monthly_salary = flt(getattr(doc, "custom_monthly_gross_salary", 0), 2)
    daily_rate = flt(monthly_salary / 30, 2)

    return {
        "title": component or "Salary Days",
        "summary": "This amount is calculated from the employee monthly gross salary and worked days until the relieving date.",
        "lines": [
            {
                "label": "Salary Structure Assignment",
                "value": reference_document or "-",
            },
            {
                "label": "Monthly Gross Salary",
                "value": monthly_salary,
            },
            {
                "label": "Daily Rate",
                "value": "{0} / 30 = {1}".format(monthly_salary, daily_rate),
            },
            {
                "label": "Worked Days",
                "value": custom_number_of_days,
            },
            {
                "label": "Formula",
                "value": "{0} × {1} = {2}".format(
                    daily_rate, custom_number_of_days, amount
                ),
            },
            {
                "label": "Final Amount",
                "value": amount,
            },
        ],
    }


def format_leave_days_as_days_and_hours(days_value: float) -> str:
    days_value = flt(days_value, 2)

    if days_value <= 0:
        return ""

    total_hours = round(days_value * 8)
    days = total_hours // 8
    hours = total_hours % 8

    parts = []

    if days == 1:
        parts.append("1 day")
    elif days > 1:
        parts.append("{0} days".format(days))

    if hours == 1:
        parts.append("1 hour")
    elif hours > 1:
        parts.append("{0} hours".format(hours))

    if not parts:
        return "{0} hours".format(total_hours)

    return "{0} ({1} days)".format(" and ".join(parts), days_value)


def explain_leave_amount(
    doc,
    component: str,
    amount: float,
    custom_number_of_days: float,
    reference_document: str,
):
    monthly_salary = flt(getattr(doc, "custom_monthly_gross_salary", 0), 2)
    daily_rate = flt(monthly_salary / 30, 2)

    if not reference_document:
        return {
            "title": component or "Leave Encashment",
            "summary": "This row is related to leave encashment, but no Leave Allocation reference was found.",
            "lines": [
                {
                    "label": "Monthly Gross Salary",
                    "value": monthly_salary,
                },
                {
                    "label": "Daily Rate",
                    "value": "{0} / 30 = {1}".format(monthly_salary, daily_rate),
                },
                {
                    "label": "Remaining Leave Days",
                    "value": custom_number_of_days,
                },
                {
                    "label": "Final Amount",
                    "value": amount,
                },
            ],
        }

    allocation = frappe.db.get_value(
        "Leave Allocation",
        reference_document,
        [
            "leave_type",
            "from_date",
            "to_date",
            "total_leaves_allocated",
            "extra_days",
        ],
        as_dict=True,
    )

    if not allocation:
        return {
            "title": component or "Leave Encashment",
            "summary": "This row is linked to a Leave Allocation document, but the source document was not found.",
            "lines": [
                {
                    "label": "Leave Allocation",
                    "value": reference_document,
                },
                {
                    "label": "Final Amount",
                    "value": amount,
                },
            ],
        }

    earned_leaves = flt(allocation.total_leaves_allocated) + flt(allocation.extra_days)

    personal_leave_days_by_type = get_personal_leave_days_by_type(
        doc.employee,
        doc.relieving_date,
    )

    personal_leave_days = flt(
        personal_leave_days_by_type.get(allocation.leave_type, 0),
        2,
    )

    taken_leaves = get_leave_taken_days(
        employee=doc.employee,
        leave_type=allocation.leave_type,
        allocation_start=allocation.from_date,
        end_date=doc.relieving_date,
        personal_leave_days_by_type=personal_leave_days_by_type,
    )

    regular_leave_taken = flt(taken_leaves - personal_leave_days, 2)
    remaining_leaves = flt(earned_leaves - taken_leaves, 2)

    return {
        "title": component or "Leave Encashment",
        "summary": "This amount is calculated from carry-forward leave balance after deducting approved leave applications and personal leave.",
        "lines": [
            {
                "label": "Leave Allocation",
                "value": reference_document,
            },
            {
                "label": "Leave Type",
                "value": allocation.leave_type or "-",
            },
            {
                "label": "Allocation Period",
                "value": "{0} to {1}".format(
                    allocation.from_date,
                    allocation.to_date,
                ),
            },
            {
                "label": "Allocated Leaves",
                "value": flt(allocation.total_leaves_allocated, 2),
            },
            {
                "label": "Extra Days",
                "value": flt(allocation.extra_days, 2),
            },
            {
                "label": "Total Earned Leaves",
                "value": earned_leaves,
            },
            {
                "label": "Taken From Leave Applications",
                "value": regular_leave_taken,
            },
            {
                "label": "Personal Leave",
                "value": format_leave_days_as_days_and_hours(personal_leave_days),
            },
            {
                "label": "Total Taken Leaves",
                "value": format_leave_days_as_days_and_hours(taken_leaves),
            },
            {
                "label": "Remaining Leave Balance",
                "value": format_leave_days_as_days_and_hours(remaining_leaves),
            },
            {
                "label": "Monthly Gross Salary",
                "value": monthly_salary,
            },
            {
                "label": "Daily Rate",
                "value": "{0} / 30 = {1}".format(monthly_salary, daily_rate),
            },
            {
                "label": "Formula",
                "value": "{0} × {1} = {2}".format(
                    daily_rate,
                    remaining_leaves,
                    amount,
                ),
            },
            {
                "label": "Final Amount",
                "value": amount,
            },
        ],
    }


def explain_additional_salary_amount(
    component: str, amount: float, reference_document: str, table_field: str
):
    additional_salary = None

    if reference_document:
        additional_salary = frappe.db.get_value(
            "Additional Salary",
            reference_document,
            [
                "salary_component",
                "payroll_date",
                "type",
                "amount",
                "custom_created_from_fnf",
            ],
            as_dict=True,
        )

    direction = "Payable"

    if table_field == "receivables":
        direction = "Receivable"

    if not additional_salary:
        return {
            "title": component or "Additional Salary",
            "summary": "This row is linked to an Additional Salary document, but the source document was not found.",
            "lines": [
                {
                    "label": "Additional Salary",
                    "value": reference_document or "-",
                },
                {
                    "label": "Amount",
                    "value": amount,
                },
            ],
        }

    created_from_fnf = (
        "Yes" if cint(additional_salary.custom_created_from_fnf) else "No"
    )

    return {
        "title": component or additional_salary.salary_component or "Additional Salary",
        "summary": "This amount comes from a submitted Additional Salary document in the relieving month.",
        "lines": [
            {
                "label": "Direction",
                "value": direction,
            },
            {
                "label": "Additional Salary",
                "value": reference_document,
            },
            {
                "label": "Salary Component",
                "value": additional_salary.salary_component,
            },
            {
                "label": "Type",
                "value": additional_salary.type,
            },
            {
                "label": "Payroll Date",
                "value": additional_salary.payroll_date,
            },
            {
                "label": "Created From Full and Final Manual Row",
                "value": created_from_fnf,
            },
            {
                "label": "Final Amount",
                "value": amount,
            },
        ],
    }


def explain_employee_advance_amount(
    component: str, amount: float, reference_document: str
):
    advance = None

    if reference_document:
        advance = frappe.db.get_value(
            "Employee Advance",
            reference_document,
            [
                "purpose",
                "advance_amount",
                "paid_amount",
                "claimed_amount",
                "status",
            ],
            as_dict=True,
        )

    if not advance:
        return {
            "title": component or "Employee Advance",
            "summary": "This row is linked to an Employee Advance document, but the source document was not found.",
            "lines": [
                {
                    "label": "Employee Advance",
                    "value": reference_document or "-",
                },
                {
                    "label": "Amount",
                    "value": amount,
                },
            ],
        }

    advance_amount = flt(advance.advance_amount, 2)
    paid_amount = flt(advance.paid_amount, 2)
    claimed_amount = flt(advance.claimed_amount, 2)
    returned_amount = flt(getattr(advance, "returned_amount", 0), 2)

    outstanding_amount = flt(paid_amount - claimed_amount - returned_amount, 2)

    return {
        "title": component or "Employee Advance",
        "summary": "This amount is the remaining outstanding employee advance balance.",
        "lines": [
            {
                "label": "Employee Advance",
                "value": reference_document,
            },
            {
                "label": "Purpose",
                "value": advance.purpose or "-",
            },
            {
                "label": "Advance Amount",
                "value": advance_amount,
            },
            {
                "label": "Paid Amount",
                "value": paid_amount,
            },
            {
                "label": "Claimed Amount",
                "value": claimed_amount,
            },
            {
                "label": "Formula",
                "value": "{0} - {1} - {2} = {3}".format(
                    paid_amount,
                    claimed_amount,
                    returned_amount,
                    outstanding_amount,
                ),
            },
            {
                "label": "Final Amount",
                "value": amount,
            },
            {
                "label": "Status",
                "value": advance.status or "-",
            },
        ],
    }


def explain_gratuity_amount(doc, component: str, amount: float):
    company_country = getattr(doc, "company_country", None)

    if not company_country and getattr(doc, "company", None):
        company_country = frappe.db.get_value("Company", doc.company, "country")

    employment_type = getattr(doc, "custom_employment_type", None)

    if not employment_type and getattr(doc, "employee", None):
        employment_type = frappe.db.get_value(
            "Employee", doc.employee, "employment_type"
        )

    reason_of_leaving = getattr(doc, "custom_reason_of_leaving", None)

    if not reason_of_leaving and getattr(doc, "employee", None):
        reason_of_leaving = frappe.db.get_value(
            "Employee",
            doc.employee,
            "custom_reason_of_leaving",
        )

    service_years = flt(getattr(doc, "custom_total_of_years", 0), 6)
    service_years_count = cint(getattr(doc, "custom_service_years", 0))
    service_months_count = cint(getattr(doc, "custom_service_month", 0))
    service_days_count = cint(getattr(doc, "custom_service_days", 0))

    service_period_text = "{0} years, {1} months, {2} days".format(
        service_years_count,
        service_months_count,
        service_days_count,
    )
    monthly_salary = flt(getattr(doc, "custom_monthly_gross_salary", 0), 2)

    first_five_years_amount = 0
    remaining_years_amount = 0

    if service_years <= 5:
        first_five_years_amount = flt(service_years * (monthly_salary / 2), 2)
    else:
        first_five_years_amount = flt(5 * (monthly_salary / 2), 2)
        remaining_years_amount = flt((service_years - 5) * monthly_salary, 2)

    base_amount = calculate_base_gratuity(
        service_years=service_years,
        monthly_salary=monthly_salary,
    )

    resignation_multiplier = get_resignation_multiplier(
        service_years=service_years,
        reason_of_leaving=reason_of_leaving,
    )

    final_amount = apply_resignation_rule(
        amount=base_amount,
        service_years=service_years,
        reason_of_leaving=reason_of_leaving,
    )

    return {
        "title": component or "Gratuity",
        "summary": "This amount is calculated based on Saudi gratuity rules using service years, monthly gross salary, and reason of leaving.",
        "lines": [
            {
                "label": "Company Country",
                "value": company_country or "-",
            },
            {
                "label": "Employment Type",
                "value": employment_type or "-",
            },
            {
                "label": "Reason of Leaving",
                "value": reason_of_leaving or "-",
            },
            {
                "label": "Service Period",
                "value": service_period_text,
            },
            {
                "label": "Service Years Used in Calculation",
                "value": service_years,
            },
            {
                "label": "Monthly Gross Salary",
                "value": monthly_salary,
            },
            {
                "label": "First 5 Years Formula",
                "value": "{0} × ({1} / 2) = {2}".format(
                    min(service_years, 5),
                    monthly_salary,
                    first_five_years_amount,
                ),
            },
            {
                "label": "After 5 Years Formula",
                "value": (
                    "({0} - 5) × {1} = {2}".format(
                        service_years,
                        monthly_salary,
                        remaining_years_amount,
                    )
                    if service_years > 5
                    else "Not applicable"
                ),
            },
            {
                "label": "Base Gratuity Formula",
                "value": "{0} + {1} = {2}".format(
                    first_five_years_amount,
                    remaining_years_amount,
                    base_amount,
                ),
            },
            {
                "label": "Resignation Rule",
                "value": get_resignation_rule_text(
                    service_years=service_years,
                    reason_of_leaving=reason_of_leaving,
                ),
            },
            {
                "label": "Final Formula",
                "value": "{0} × {1} = {2}".format(
                    base_amount,
                    resignation_multiplier,
                    final_amount,
                ),
            },
            {
                "label": "Final Amount",
                "value": final_amount or amount,
            },
        ],
    }


def get_resignation_multiplier(service_years: float, reason_of_leaving: str) -> float:
    if normalize_text(reason_of_leaving) != "Resignation":
        return 1

    if service_years < 2:
        return 0

    if service_years < 5:
        return flt(1 / 3, 4)

    if service_years < 10:
        return flt(2 / 3, 4)

    return 1


def get_resignation_rule_text(service_years: float, reason_of_leaving: str) -> str:
    if normalize_text(reason_of_leaving) != "Resignation":
        return "Full gratuity because reason of leaving is not Resignation."

    if service_years < 2:
        return (
            "Resignation with less than 2 years of service: employee is not eligible."
        )

    if service_years < 5:
        return "Resignation from 2 to less than 5 years: employee gets one third of gratuity."

    if service_years < 10:
        return "Resignation from 5 to less than 10 years: employee gets two thirds of gratuity."

    return "Resignation with 10 years or more: employee gets full gratuity."


def explain_manual_row(doc, row_data: dict, table_field: str):
    component = str(row_data.get("component") or "").strip()
    amount = flt(row_data.get("amount"), 2)
    reference_document = str(row_data.get("reference_document") or "").strip()

    row_type = "Payables Manual Row"

    if table_field == "receivables":
        row_type = "Receivables Manual Row"

    setting_row = get_manual_row_setting(doc.company, row_type)
    salary_component = (
        getattr(setting_row, "salary_component", None) if setting_row else None
    )

    summary = "This is a manual settlement row. On save, it is synced with a submitted Additional Salary document."

    if reference_document:
        summary = "This manual row is already synced with a submitted Additional Salary document."

    return {
        "title": component or "Manual Row",
        "summary": summary,
        "lines": [
            {
                "label": "Manual Row Type",
                "value": row_type,
            },
            {
                "label": "Displayed Component Name",
                "value": component or "-",
            },
            {
                "label": "Salary Component Used for Additional Salary",
                "value": salary_component or "-",
            },
            {
                "label": "Additional Salary",
                "value": reference_document or "Will be created on save",
            },
            {
                "label": "Final Amount",
                "value": amount,
            },
        ],
    }
