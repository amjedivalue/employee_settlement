
from datetime import date

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, get_first_day, relativedelta


# =========================================================
# SECTION 1: دوال مساعدة للتواريخ
# =========================================================

def get_inclusive_days(start_date, end_date) -> int:
    """
    ترجع عدد الأيام بين تاريخين بشكل شامل
    يعني لو البداية والنهاية نفس اليوم ترجع 1
    """
    if not start_date:
        return 0

    if not end_date:
        return 0

    start_value = getdate(start_date)
    end_value = getdate(end_date)

    if end_value < start_value:
        return 0

    return (end_value - start_value).days + 1


def get_month_first_day(any_date) -> date:
    """
    ترجع أول يوم من نفس الشهر
    """
    current_date = getdate(any_date)
    return date(current_date.year, current_date.month, 1)


def get_month_last_day(any_date) -> date:
    """
    ترجع آخر يوم من نفس الشهر
    """
    current_date = getdate(any_date)

    if current_date.month == 12:
        next_month_first_day = date(current_date.year + 1, 1, 1)
    else:
        next_month_first_day = date(current_date.year, current_date.month + 1, 1)

    return next_month_first_day - relativedelta(days=1)


def get_days_in_month(any_date) -> int:
    """
    ترجع عدد أيام الشهر
    """
    month_start = get_month_first_day(any_date)
    month_end = get_month_last_day(any_date)
    return (month_end - month_start).days + 1


def get_overlap_inclusive_days(first_start, first_end, second_start, second_end) -> int:
    """
    ترجع عدد الأيام المشتركة بين فترتين
    """
    overlap_start = max(getdate(first_start), getdate(second_start))
    overlap_end = min(getdate(first_end), getdate(second_end))
    return get_inclusive_days(overlap_start, overlap_end)


def is_date_in_same_month(target_date, reference_date) -> bool:
    """
    تفحص هل تاريخين في نفس السنة ونفس الشهر
    """
    if not target_date:
        return False

    if not reference_date:
        return False

    target_value = getdate(target_date)
    reference_value = getdate(reference_date)

    if target_value.year != reference_value.year:
        return False

    if target_value.month != reference_value.month:
        return False

    return True


# =========================================================
# SECTION 2: جلب البيانات الأساسية
# =========================================================

def get_employee_basic_data(employee_id: str) -> dict:
    """
    جلب البيانات الأساسية للموظف
    """
    employee_data = frappe.db.get_value(
        "Employee",
        employee_id,
        [
            "name",
            "employee_name",
            "company",
            "department",
            "designation",
            "date_of_joining",
            "relieving_date",
        ],
        as_dict=True,
    )

    if not employee_data:
        return {}

    return employee_data


def get_company_currency(company: str) -> str | None:
    """
    جلب عملة الشركة
    """
    if not company:
        return None

    return frappe.db.get_value("Company", company, "default_currency")


def get_company_default_payable_account(company: str) -> str | None:
    """
    جلب الحساب الافتراضي الذي سنستخدمه مؤقتًا للمستحقات
    """
    if not company:
        return None

    company_doc = frappe.get_cached_doc("Company", company)

    candidate_fields = [
        "default_payroll_payable_account",
        "payroll_payable_account",
        "default_payable_account",
    ]

    for field_name in candidate_fields:
        if hasattr(company_doc, field_name):
            field_value = getattr(company_doc, field_name)
            if field_value:
                return field_value

    return None


def get_company_employee_advance_account(company: str) -> str | None:
    """
    جلب حساب السلف من الشركة
    """
    if not company:
        return None

    return frappe.db.get_value("Company", company, "default_employee_advance_account")


def get_company_letter_head(company: str) -> str | None:
    """
    جلب الترويسة الافتراضية للشركة
    """
    if not company:
        return None

    return frappe.db.get_value("Company", company, "default_letter_head")


# =========================================================
# SECTION 3: مدة الخدمة
# =========================================================

def get_service_period_data(join_date, relieving_date) -> dict:
    """
    حساب مدة خدمة الموظف
    """
    start_date = getdate(join_date)
    end_date = getdate(relieving_date)

    difference = relativedelta(end_date + relativedelta(days=1), start_date)
    total_days = (end_date - start_date).days + 1

    service_data = {
        "years": difference.years,
        "months": difference.months,
        "days": difference.days,
        "total_years": flt(total_days / 365, 3),
    }

    return service_data


# =========================================================
# SECTION 4: الراتب الأساسي وآخر راتب
# =========================================================

def get_latest_salary_structure_assignment(employee: str, as_of_date):
    """
    جلب آخر Salary Structure Assignment فعال للموظف
    """
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
        return None

    return frappe.get_doc("Salary Structure Assignment", assignment_name)


def get_salary_currency_from_assignment(assignment):
    """
    جلب العملة من Assignment أو من Salary Structure
    """
    if not assignment:
        return None

    assignment_currency = getattr(assignment, "currency", None)
    if assignment_currency:
        return assignment_currency

    salary_structure_name = getattr(assignment, "salary_structure", None)
    if salary_structure_name:
        structure_currency = frappe.db.get_value(
            "Salary Structure",
            salary_structure_name,
            "currency"
        )
        if structure_currency:
            return structure_currency

    return None


def get_salary_breakdown(assignment) -> dict:
    """
    جلب تفاصيل الراتب الشهري من الحقول الموجودة في Assignment
    """
    if not assignment:
        return {
            "basic": 0,
            "housing": 0,
            "transportation": 0,
            "other": 0,
            "monthly_total": 0,
        }

    basic_salary = flt(getattr(assignment, "base", 0))
    housing_amount = flt(getattr(assignment, "custom_housing", 0))
    transportation_amount = flt(getattr(assignment, "custom_travelling", 0))
    other_amount = flt(getattr(assignment, "custom_other_allowance", 0))

    monthly_total = basic_salary + housing_amount + transportation_amount + other_amount

    salary_breakdown = {
        "basic": basic_salary,
        "housing": housing_amount,
        "transportation": transportation_amount,
        "other": other_amount,
        "monthly_total": flt(monthly_total, 2),
    }

    return salary_breakdown


def calculate_salary_days_row_data(employee: str, join_date, relieving_date) -> dict:
    """
    حساب أجر أيام العمل في آخر شهر
    """
    assignment = get_latest_salary_structure_assignment(employee, relieving_date)

    if not assignment:
        frappe.throw(
            _(
                "No Salary Structure Assignment found for this employee. "
                "Please create one first."
            )
        )

    salary_breakdown = get_salary_breakdown(assignment)
    monthly_total = flt(salary_breakdown.get("monthly_total"))
    salary_currency = get_salary_currency_from_assignment(assignment)

    period_start = get_month_first_day(relieving_date)
    month_days = get_days_in_month(relieving_date)

    if join_date:
        join_date_value = getdate(join_date)
        if join_date_value > period_start:
            period_start = join_date_value

    worked_days = get_inclusive_days(period_start, relieving_date)
    daily_rate = flt(monthly_total / 30, 2)

    if worked_days >= month_days:
        final_amount = flt(monthly_total, 2)
    else:
        final_amount = flt(worked_days * daily_rate, 2)

    return {
        "assignment_name": assignment.name,
        "currency": salary_currency,
        "worked_days": flt(worked_days, 2),
        "daily_rate": flt(daily_rate, 2),
        "amount": flt(final_amount, 2),
        "breakdown": salary_breakdown,
    }


# =========================================================
# SECTION 5: الإجازات القابلة للصرف
# =========================================================

def get_personal_leave_days_grouped_by_type(employee: str, end_date) -> dict:
    """
    جلب ساعات Personal Leave وتحويلها لأيام وتجميعها حسب نوع الإجازة
    """
    month_start = get_first_day(getdate(end_date))

    personal_leave_rows = frappe.get_all(
        "Personal Leave",
        filters={
            "employee": employee,
            "date": ["between", [month_start, end_date]],
            "docstatus": 1,
        },
        fields=["leave_type", "hours"],
    )

    leave_totals = {}

    for row in personal_leave_rows:
        leave_type = row.get("leave_type")

        if not leave_type:
            continue

        leave_hours = flt(row.get("hours"))
        leave_days = flt(leave_hours / 8, 2)

        if leave_type not in leave_totals:
            leave_totals[leave_type] = 0.0

        leave_totals[leave_type] = flt(leave_totals[leave_type] + leave_days, 2)

    return leave_totals


def get_leave_encashment_rows(employee: str, end_date) -> list[dict]:
    """
    جلب أرصدة الإجازات القابلة للترحيل والصرف
    """
    final_rows = []

    personal_leave_days = get_personal_leave_days_grouped_by_type(employee, end_date)

    carry_forward_leave_types = frappe.get_all(
        "Leave Type",
        filters={"is_carry_forward": 1},
        pluck="name",
    )

    for leave_type in carry_forward_leave_types:
        allocation_list = frappe.get_all(
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
                "extra_days"
            ],
            order_by="from_date desc, to_date desc, modified desc",
            limit=1,
        )

        if not allocation_list:
            continue

        allocation = allocation_list[0]

        allocation_start = allocation.get("from_date")
        allocation_reference = allocation.get("name")
        earned_days = flt(allocation.get("total_leaves_allocated")) + flt(allocation.get("extra_days"))

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

        taken_days = 0.0

        for application in leave_applications:
            overlap_days = get_overlap_inclusive_days(
                application.get("from_date"),
                application.get("to_date"),
                allocation_start,
                end_date,
            )

            application_total_days = get_inclusive_days(
                application.get("from_date"),
                application.get("to_date"),
            )

            if application_total_days > 0:
                proportional_days = flt(application.get("total_leave_days")) * (
                    flt(overlap_days) / flt(application_total_days)
                )
                taken_days = flt(taken_days + proportional_days, 2)

        personal_leave_taken = flt(personal_leave_days.get(leave_type, 0))
        taken_days = flt(taken_days + personal_leave_taken, 2)

        balance_days = flt(earned_days - taken_days, 2)

        if balance_days <= 0:
            continue

        row = {
            "leave_type": leave_type,
            "earned": flt(earned_days, 2),
            "taken": flt(taken_days, 2),
            "balance": flt(balance_days, 2),
            "allocation_ref": allocation_reference,
        }

        final_rows.append(row)

    return final_rows


def build_leave_encashment_payable_rows(
    leave_rows: list[dict],
    daily_rate: float,
    account: str
) -> tuple[list[dict], float]:
    """
    تحويل أرصدة الإجازات إلى سطور مستحقات
    """
    payable_rows = []
    total_amount = 0.0

    for leave_row in leave_rows:
        leave_balance = flt(leave_row.get("balance"), 2)
        leave_amount = flt(leave_balance * flt(daily_rate), 2)

        if leave_balance <= 0:
            continue

        if leave_amount <= 0:
            continue

        row = {
            "component_key": "leave_encashment",
            "component": leave_row.get("leave_type"),
            "reference_document_type": "Leave Allocation",
            "reference_document": leave_row.get("allocation_ref"),
            "account": account,
            "amount": leave_amount,
            "status": "Settled",
            "custom_number_of_days": leave_balance,
        }

        payable_rows.append(row)
        total_amount = flt(total_amount + leave_amount, 2)

    return payable_rows, flt(total_amount, 2)


# =========================================================
# SECTION 6: أجر أيام العمل
# =========================================================

def build_salary_days_payable_row(salary_data: dict, account: str) -> tuple[list[dict], float]:
    """
    بناء سطر أجر أيام العمل
    """
    payable_rows = []
    total_amount = 0.0

    salary_amount = flt(salary_data.get("amount"))
    worked_days = flt(salary_data.get("worked_days"), 2)

    if salary_amount > 0:
        row = {
            "component_key": "salary_days",
            "component": "Salary days",
            "reference_document_type": "Salary Structure Assignment",
            "reference_document": salary_data.get("assignment_name"),
            "account": account,
            "amount": salary_amount,
            "status": "Settled",
            "custom_number_of_days": worked_days,
        }

        payable_rows.append(row)
        total_amount = flt(total_amount + salary_amount, 2)

    return payable_rows, flt(total_amount, 2)


# =========================================================
# SECTION 7: السلف
# =========================================================

def build_employee_advance_receivable_rows(employee: str) -> tuple[list[dict], float]:
    """
    جلب السلف المتبقية على الموظف ووضعها في الاستقطاعات
    """
    receivable_rows = []
    total_amount = 0.0

    employee_data = get_employee_basic_data(employee)

    if not employee_data:
        frappe.throw(_("Employee not found."))

    company = employee_data.get("company")
    advance_account = get_company_employee_advance_account(company)

    employee_advances = frappe.get_all(
        "Employee Advance",
        filters={
            "employee": employee,
            "docstatus": 1,
        },
        fields=[
            "name",
            "advance_amount",
            "paid_amount",
            "claimed_amount",
        ],
        order_by="posting_date desc",
    )

    for advance in employee_advances:
        advance_amount = flt(advance.get("advance_amount"))
        paid_amount = flt(advance.get("paid_amount"))
        claimed_amount = flt(advance.get("claimed_amount"))

        outstanding_amount = flt(advance_amount - paid_amount - claimed_amount, 2)

        if outstanding_amount <= 0:
            continue

        if not advance.get("name"):
            continue

        row = {
            "component_key": "employee_advance",
            "component": "Employee Advance",
            "reference_document_type": "Employee Advance",
            "reference_document": advance.get("name"),
            "account": advance_account,
            "amount": outstanding_amount,
            "status": "Settled",
            "custom_number_of_days": 0,
        }

        receivable_rows.append(row)
        total_amount = flt(total_amount + outstanding_amount, 2)

    return receivable_rows, flt(total_amount, 2)


# =========================================================
# SECTION 8: المطالبات المالية Expense Claim
# =========================================================

def build_expense_claim_rows(employee: str, company: str) -> tuple[list[dict], list[dict], float, float]:
    """
    جلب المطالبات المالية غير المسددة

    المنطق هنا:
    - إذا المتبقي موجب => الشركة بدها تدفع للموظف => مستحقات
    - إذا المتبقي سالب => الموظف عليه للشركة => استقطاعات
    """
    payable_rows = []
    receivable_rows = []
    total_payable = 0.0
    total_receivable = 0.0

    default_account = get_company_default_payable_account(company)

    expense_claims = frappe.get_all(
        "Expense Claim",
        filters={
            "employee": employee,
            "docstatus": 1,
        },
        fields=[
            "name",
            "total_sanctioned_amount",
            "total_claimed_amount",
            "total_amount_reimbursed",
            "status",
            "posting_date",
        ],
        order_by="posting_date desc, modified desc",
    )

    for expense_claim in expense_claims:
        sanctioned_amount = flt(expense_claim.get("total_sanctioned_amount"))
        claimed_amount = flt(expense_claim.get("total_claimed_amount"))
        reimbursed_amount = flt(expense_claim.get("total_amount_reimbursed"))

        base_amount = sanctioned_amount

        if base_amount <= 0:
            base_amount = claimed_amount

        outstanding_amount = flt(base_amount - reimbursed_amount, 2)

        if outstanding_amount == 0:
            continue

        if outstanding_amount > 0:
            payable_row = {
                "component_key": "expense_claim",
                "component": "Expense Claim",
                "reference_document_type": "Expense Claim",
                "reference_document": expense_claim.get("name"),
                "account": default_account,
                "amount": outstanding_amount,
                "status": "Settled",
                "custom_number_of_days": 0,
            }

            payable_rows.append(payable_row)
            total_payable = flt(total_payable + outstanding_amount, 2)
            continue

        if outstanding_amount < 0:
            receivable_row = {
                "component_key": "expense_claim",
                "component": "Expense Claim",
                "reference_document_type": "Expense Claim",
                "reference_document": expense_claim.get("name"),
                "account": default_account,
                "amount": abs(outstanding_amount),
                "status": "Settled",
                "custom_number_of_days": 0,
            }

            receivable_rows.append(receivable_row)
            total_receivable = flt(total_receivable + abs(outstanding_amount), 2)

    return (
        payable_rows,
        receivable_rows,
        flt(total_payable, 2),
        flt(total_receivable, 2),
    )


# =========================================================
# SECTION 9: Additional Salary
# =========================================================

def get_salary_component_type(salary_component: str) -> str | None:
    """
    جلب نوع Salary Component
    عادة يكون Earning أو Deduction
    """
    if not salary_component:
        return None

    return frappe.db.get_value("Salary Component", salary_component, "type")


def build_additional_salary_rows(
    employee: str,
    company: str,
    relieving_date,
) -> tuple[list[dict], list[dict], float, float]:
    """
    جلب Additional Salary لنفس شهر المخالصة فقط

    إذا نوع الـ component = Earning
    => يذهب إلى المستحقات

    إذا نوع الـ component = Deduction
    => يذهب إلى الاستقطاعات
    """
    payable_rows = []
    receivable_rows = []
    total_payable = 0.0
    total_receivable = 0.0

    default_account = get_company_default_payable_account(company)

    month_start = get_month_first_day(relieving_date)
    month_end = get_month_last_day(relieving_date)

    additional_salary_rows = frappe.get_all(
        "Additional Salary",
        filters={
            "employee": employee,
            "docstatus": 1,
            "payroll_date": ["between", [month_start, month_end]],
        },
        fields=[
            "name",
            "salary_component",
            "amount",
            "payroll_date",
            "company",
        ],
        order_by="payroll_date desc, modified desc",
    )

    for additional_salary in additional_salary_rows:
        payroll_date = additional_salary.get("payroll_date")

        if not is_date_in_same_month(payroll_date, relieving_date):
            continue

        amount = flt(additional_salary.get("amount"), 2)

        if amount <= 0:
            continue

        salary_component = additional_salary.get("salary_component")
        component_type = get_salary_component_type(salary_component)

        row_data = {
            "component_key": "additional_salary",
            "component": salary_component or "Additional Salary",
            "reference_document_type": "Additional Salary",
            "reference_document": additional_salary.get("name"),
            "account": default_account,
            "amount": amount,
            "status": "Settled",
            "custom_number_of_days": 0,
        }

        if component_type == "Earning":
            payable_rows.append(row_data)
            total_payable = flt(total_payable + amount, 2)
            continue

        if component_type == "Deduction":
            receivable_rows.append(row_data)
            total_receivable = flt(total_receivable + amount, 2)
            continue

    return (
        payable_rows,
        receivable_rows,
        flt(total_payable, 2),
        flt(total_receivable, 2),
    )


# =========================================================
# SECTION 10: دوال تجميع المجاميع
# =========================================================

def calculate_total_leave_balance(leave_rows: list[dict]) -> float:
    """
    جمع مجموع أرصدة الإجازات
    """
    total_balance = 0.0

    for row in leave_rows:
        balance_value = flt(row.get("balance"))
        total_balance = flt(total_balance + balance_value, 2)

    return flt(total_balance, 2)


# =========================================================
# SECTION 11: API الرئيسية
# =========================================================

@frappe.whitelist()
def get_full_and_final_data(employee: str, relieving_date=None):
    """
    هذه هي دالة الـ API الرئيسية
    نحافظ على اسمها كما طلبت
    """
    employee_data = get_employee_basic_data(employee)

    if not employee_data:
        frappe.throw(_("Employee not found."))

    company = employee_data.get("company")
    joining_date = employee_data.get("date_of_joining")
    final_date = getdate(relieving_date or employee_data.get("relieving_date"))

    if not joining_date:
        frappe.throw(_("Employee Date of Joining is missing."))

    if not final_date:
        frappe.throw(_("Relieving Date is required."))

    company_letter_head = get_company_letter_head(company)

    salary_data = calculate_salary_days_row_data(employee, joining_date, final_date)
    company_currency = salary_data.get("currency")

    if not company_currency:
        company_currency = get_company_currency(company)

    if not company_currency:
        frappe.throw(
            _(
                "Salary Currency is missing in Salary Structure Assignment, "
                "Salary Structure, and Company."
            )
        )

    default_payable_account = get_company_default_payable_account(company)

    service_data = get_service_period_data(joining_date, final_date)
    leave_balance_rows = get_leave_encashment_rows(employee, final_date)

    salary_days_rows, salary_days_total = build_salary_days_payable_row(
        salary_data,
        default_payable_account,
    )

    leave_encashment_rows, leave_encashment_total = build_leave_encashment_payable_rows(
        leave_balance_rows,
        salary_data.get("daily_rate"),
        default_payable_account,
    )

    employee_advance_rows, employee_advance_total = build_employee_advance_receivable_rows(employee)

    expense_claim_payables, expense_claim_receivables, expense_claim_payable_total, expense_claim_receivable_total = build_expense_claim_rows(
        employee,
        company,
    )

    additional_salary_payables, additional_salary_receivables, additional_salary_payable_total, additional_salary_receivable_total = build_additional_salary_rows(
        employee,
        company,
        final_date,
    )

    all_payables = []
    all_payables.extend(salary_days_rows)
    all_payables.extend(leave_encashment_rows)
    all_payables.extend(expense_claim_payables)
    all_payables.extend(additional_salary_payables)

    all_receivables = []
    all_receivables.extend(employee_advance_rows)
    all_receivables.extend(expense_claim_receivables)
    all_receivables.extend(additional_salary_receivables)

    total_payables = flt(
        salary_days_total
        + leave_encashment_total
        + expense_claim_payable_total
        + additional_salary_payable_total,
        2,
    )

    total_receivables = flt(
        employee_advance_total
        + expense_claim_receivable_total
        + additional_salary_receivable_total,
        2,
    )

    total_leave_balance = calculate_total_leave_balance(leave_balance_rows)
    total_leave_amount = flt(total_leave_balance * flt(salary_data.get("daily_rate")), 2)

    return {
        "ok": True,
        "company_currency": company_currency,
        "letter_head": company_letter_head,
        "employee": employee_data,
        "salary": {
            "basic_salary": flt(salary_data["breakdown"]["basic"], 2),
            "housing": flt(salary_data["breakdown"]["housing"], 2),
            "transportation": flt(salary_data["breakdown"]["transportation"], 2),
            "other_allowance": flt(salary_data["breakdown"]["other"], 2),
            "monthly_gross_salary": flt(salary_data["breakdown"]["monthly_total"], 2),
            "daily_rate": flt(salary_data["daily_rate"], 6),
            "worked_days": flt(salary_data["worked_days"], 1),
            "prorated_amount": flt(salary_data["amount"], 2),
        },
        "service": {
            "years": service_data.get("years", 0),
            "months": service_data.get("months", 0),
            "days": service_data.get("days", 0),
            "total_years": service_data.get("total_years", 0),
        },
        "payables": all_payables,
        "receivables": all_receivables,
        "assets_allocated": [],
        "carry_forward_leaves": leave_balance_rows,
        "totals": {
            "total_payable_amount": flt(total_payables, 2),
            "total_receivable_amount": flt(total_receivables, 2),
            "total_asset_recovery_cost": 0.0,
        },
        "leaves_balanced": flt(total_leave_balance, 2),
        "leaves_amount": flt(total_leave_amount, 2),
    }


# =========================================================
# SECTION 12: إعادة البناء التلقائي للوثيقة
# =========================================================

def set_transaction_date(doc, method=None):
    """
    إذا ما فيه transaction_date نحطه تاريخ اليوم
    """
    if not doc.transaction_date:
        doc.transaction_date = nowdate()


def has_only_default_placeholder_rows(doc) -> bool:
    """
    فحص هل الجداول الحالية مجرد صفوف Placeholder فقط
    """
    allowed_payable_components = {"Gratuity", "Expense Claim", "Bonus", "Leave Encashment"}
    allowed_receivable_components = {"Employee Advance", "Loan"}

    payables_rows = doc.get("payables") or []
    receivables_rows = doc.get("receivables") or []

    if not payables_rows and not receivables_rows:
        return False

    def is_placeholder_row(row, allowed_components):
        if row.get("component") not in allowed_components:
            return False

        if row.get("reference_document"):
            return False

        if flt(row.get("amount")) != 0:
            return False

        return True

    all_payables_are_placeholders = True

    for row in payables_rows:
        if not is_placeholder_row(row, allowed_payable_components):
            all_payables_are_placeholders = False
            break

    all_receivables_are_placeholders = True

    for row in receivables_rows:
        if not is_placeholder_row(row, allowed_receivable_components):
            all_receivables_are_placeholders = False
            break

    if all_payables_are_placeholders and all_receivables_are_placeholders:
        return True

    return False


def should_rebuild_full_and_final_document(doc) -> bool:
    """
    تحديد هل نعيد تعبئة الوثيقة أم لا
    """
    if doc.docstatus != 0:
        return False

    if not doc.employee:
        return False

    if not doc.relieving_date:
        return False

    old_doc = doc.get_doc_before_save()

    if not old_doc:
        return True

    if has_only_default_placeholder_rows(doc):
        return True

    if old_doc.employee != doc.employee:
        return True

    if str(old_doc.relieving_date) != str(doc.relieving_date):
        return True

    return False


# =========================================================
# SECTION 13: تعبئة الحقول الرئيسية
# =========================================================

def fill_parent_fields_from_data(doc, data: dict):
    """
    تعبئة الحقول الرئيسية في Full and Final Statement
    """
    employee_data = data.get("employee") or {}
    salary_data = data.get("salary") or {}
    service_data = data.get("service") or {}
    totals_data = data.get("totals") or {}

    if hasattr(doc, "employee_name"):
        doc.employee_name = employee_data.get("employee_name")

    if hasattr(doc, "company"):
        doc.company = employee_data.get("company")

    if hasattr(doc, "department"):
        doc.department = employee_data.get("department")

    if hasattr(doc, "designation"):
        doc.designation = employee_data.get("designation")

    if hasattr(doc, "date_of_joining"):
        doc.date_of_joining = employee_data.get("date_of_joining")

    if hasattr(doc, "custom_company_currency"):
        doc.custom_company_currency = data.get("company_currency")

    if hasattr(doc, "custom_letter_head"):
        doc.custom_letter_head = data.get("letter_head")

    if hasattr(doc, "custom_basic_salary"):
        doc.custom_basic_salary = salary_data.get("basic_salary", 0)

    if hasattr(doc, "custom_housing"):
        doc.custom_housing = salary_data.get("housing", 0)

    if hasattr(doc, "custom_transportation"):
        doc.custom_transportation = salary_data.get("transportation", 0)

    if hasattr(doc, "custom_other_allowances"):
        doc.custom_other_allowances = salary_data.get("other_allowance", 0)

    if hasattr(doc, "custom_monthly_gross_salary"):
        doc.custom_monthly_gross_salary = salary_data.get("monthly_gross_salary", 0)

    if hasattr(doc, "custom_work_days"):
        doc.custom_work_days = salary_data.get("worked_days", 0)

    if hasattr(doc, "custom_leaves_balanced"):
        doc.custom_leaves_balanced = data.get("leaves_balanced", 0)

    if hasattr(doc, "custom_leaves_amount"):
        doc.custom_leaves_amount = data.get("leaves_amount", 0)

    if hasattr(doc, "custom_service_years"):
        doc.custom_service_years = service_data.get("years", 0)

    if hasattr(doc, "custom_service_month"):
        doc.custom_service_month = service_data.get("months", 0)

    if hasattr(doc, "custom_service_days"):
        doc.custom_service_days = service_data.get("days", 0)

    if hasattr(doc, "custom_total_of_years"):
        doc.custom_total_of_years = service_data.get("total_years", 0)

    if hasattr(doc, "total_payable_amount"):
        doc.total_payable_amount = totals_data.get("total_payable_amount", 0)

    if hasattr(doc, "total_receivable_amount"):
        doc.total_receivable_amount = totals_data.get("total_receivable_amount", 0)

    if hasattr(doc, "total_asset_recovery_cost"):
        doc.total_asset_recovery_cost = totals_data.get("total_asset_recovery_cost", 0)


# =========================================================
# SECTION 14: تنظيف الجداول
# =========================================================

def clear_child_tables(doc):
    """
    تنظيف الجداول قبل إعادة التعبئة
    """
    doc.set("payables", [])
    doc.set("receivables", [])
    doc.set("assets_allocated", [])

    if hasattr(doc, "custom_carry_forward_leaves"):
        doc.set("custom_carry_forward_leaves", [])


# =========================================================
# SECTION 15: تعبئة الجداول
# =========================================================

def append_payables_rows(doc, rows: list[dict]):
    """
    تعبئة جدول المستحقات
    """
    for row in rows:
        amount_value = flt(row.get("amount"))

        if amount_value <= 0:
            continue

        doc.append("payables", {
            "component": row.get("component"),
            "reference_document_type": row.get("reference_document_type"),
            "reference_document": row.get("reference_document"),
            "account": row.get("account"),
            "amount": amount_value,
            "status": row.get("status") or "Settled",
            "custom_number_of_days": row.get("custom_number_of_days"),
        })


def append_receivables_rows(doc, rows: list[dict]):
    """
    تعبئة جدول الاستقطاعات
    """
    for row in rows:
        amount_value = flt(row.get("amount"))

        if amount_value <= 0:
            continue

        doc.append("receivables", {
            "component": row.get("component"),
            "reference_document_type": row.get("reference_document_type"),
            "reference_document": row.get("reference_document"),
            "account": row.get("account"),
            "amount": amount_value,
            "status": row.get("status") or "Settled",
            "custom_number_of_days": row.get("custom_number_of_days"),
        })


def append_carry_forward_leave_rows(doc, rows: list[dict]):
    """
    تعبئة جدول تفاصيل الإجازات إذا كان موجود
    """
    if not hasattr(doc, "custom_carry_forward_leaves"):
        return

    for row in rows:
        doc.append("custom_carry_forward_leaves", {
            "leave_type": row.get("leave_type"),
            "earned": row.get("earned"),
            "taken": row.get("taken"),
            "balance": row.get("balance"),
            "allocation_ref": row.get("allocation_ref"),
        })


def force_rows_status_as_settled(doc):
    """
    تثبيت حالة كل السطور على Settled
    """
    for row in doc.payables or []:
        row.status = "Settled"

    for row in doc.receivables or []:
        row.status = "Settled"


# =========================================================
# SECTION 16: الدالة الرئيسية التي تعبّي الدوكمنت
# =========================================================

def populate_full_and_final_doc(doc, method=None):
    """
    هذه الدالة تستخدم في hook لتعبئة المستند تلقائيًا
    """
    if not should_rebuild_full_and_final_document(doc):
        return

    data = get_full_and_final_data(
        employee=doc.employee,
        relieving_date=doc.relieving_date,
    )

    if not data:
        return

    if not data.get("ok"):
        return

    fill_parent_fields_from_data(doc, data)
    clear_child_tables(doc)
    append_payables_rows(doc, data.get("payables") or [])
    append_receivables_rows(doc, data.get("receivables") or [])
    append_carry_forward_leave_rows(doc, data.get("carry_forward_leaves") or [])
    force_rows_status_as_settled(doc)