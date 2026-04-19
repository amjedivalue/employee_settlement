import frappe
from frappe.utils import flt


# =========================================================
# SECTION 1: دوال مساعدة بسيطة للنصوص
# =========================================================

def convert_value_to_text(value) -> str:
    """
    تحويل أي قيمة إلى نص بشكل آمن
    """
    if value is None:
        return ""

    return str(value).strip()


def get_money_text(value) -> str:
    """
    تحويل الرقم لنص واضح
    """
    return str(flt(value, 2))


def add_line(summary_lines: list, text: str):
    """
    إضافة سطر إذا كان فيه نص
    """
    text_value = convert_value_to_text(text)

    if not text_value:
        return

    summary_lines.append(text_value)


# =========================================================
# SECTION 2: قراءة بيانات الرأس من Full and Final
# =========================================================

def get_document_header_lines(doc) -> list[str]:
    """
    تجهيز مقدمة الملخص
    """
    lines = []

    employee = convert_value_to_text(getattr(doc, "employee", ""))
    employee_name = convert_value_to_text(getattr(doc, "employee_name", ""))
    company = convert_value_to_text(getattr(doc, "company", ""))
    joining_date = convert_value_to_text(getattr(doc, "date_of_joining", ""))
    relieving_date = convert_value_to_text(getattr(doc, "relieving_date", ""))
    employment_type = convert_value_to_text(getattr(doc, "custom_employment_type", ""))
    reason_of_leaving = convert_value_to_text(getattr(doc, "custom_reason_of_leaving", ""))

   

    if employee and employee_name:
        add_line(lines, f"Employee: {employee} - {employee_name}")
    elif employee:
        add_line(lines, f"Employee: {employee}")
    elif employee_name:
        add_line(lines, f"Employee Name: {employee_name}")

    add_line(lines, f"Company: {company}")
    add_line(lines, f"Joining Date: {joining_date}")
    add_line(lines, f"Relieving Date: {relieving_date}")
    add_line(lines, f"Employment Type: {employment_type}")
    add_line(lines, f"Reason of Leaving: {reason_of_leaving}")

    return lines


def get_salary_basis_lines(doc) -> list[str]:
    """
    تجهيز سطور توضح أساس الراتب المستخدم
    """
    lines = []

    basic_salary = flt(getattr(doc, "custom_basic_salary", 0), 2)
    housing = flt(getattr(doc, "custom_housing", 0), 2)
    transportation = flt(getattr(doc, "custom_transportation", 0), 2)
    other_allowances = flt(getattr(doc, "custom_other_allowances", 0), 2)
    monthly_gross_salary = flt(getattr(doc, "custom_monthly_gross_salary", 0), 2)
    worked_days = flt(getattr(doc, "custom_work_days", 0), 2)

    lines.append("")
    add_line(lines, "Salary Basis:")
    add_line(lines, f"- Basic Salary: {get_money_text(basic_salary)}")
    add_line(lines, f"- Housing: {get_money_text(housing)}")
    add_line(lines, f"- Transportation: {get_money_text(transportation)}")
    add_line(lines, f"- Other Allowances: {get_money_text(other_allowances)}")
    add_line(lines, f"- Monthly Gross Salary: {get_money_text(monthly_gross_salary)}")
    add_line(lines, f"- Worked Days In Relieving Month: {worked_days}")

    return lines


def get_service_period_lines(doc) -> list[str]:
    """
    تجهيز سطور مدة الخدمة
    """
    lines = []

    service_years = flt(getattr(doc, "custom_service_years", 0), 2)
    service_months = flt(getattr(doc, "custom_service_month", 0), 2)
    service_days = flt(getattr(doc, "custom_service_days", 0), 2)
    total_years = flt(getattr(doc, "custom_total_of_years", 0), 6)

    lines.append("")
    add_line(lines, "Service Period:")
    add_line(lines, f"- Years: {service_years}")
    add_line(lines, f"- Months: {service_months}")
    add_line(lines, f"- Days: {service_days}")
    add_line(lines, f"- Total Years: {total_years}")

    return lines


# =========================================================
# SECTION 3: بناء شرح كل سطر
# =========================================================

def build_salary_days_explanation(row) -> str:
    """
    شرح سطر Salary Days
    """
    amount = get_money_text(getattr(row, "amount", 0))
    number_of_days = flt(getattr(row, "custom_number_of_days", 0), 2)
    reference_document_type = convert_value_to_text(getattr(row, "reference_document_type", ""))
    reference_document = convert_value_to_text(getattr(row, "reference_document", ""))

    text = f"Salary Days was added with amount {amount}"

    if number_of_days:
        text += f" based on {number_of_days} worked days"

    if reference_document_type or reference_document:
        text += f". Reference: {reference_document_type} {reference_document}"

    text += "."

    return text


def build_leaves_explanation(row) -> str:
    """
    شرح سطر الإجازات
    """
    component = convert_value_to_text(getattr(row, "component", "Leaves"))
    amount = get_money_text(getattr(row, "amount", 0))
    number_of_days = flt(getattr(row, "custom_number_of_days", 0), 2)
    reference_document_type = convert_value_to_text(getattr(row, "reference_document_type", ""))
    reference_document = convert_value_to_text(getattr(row, "reference_document", ""))

    text = f"{component} was added with amount {amount}"

    if number_of_days:
        text += f" for {number_of_days} leave days"

    if reference_document_type or reference_document:
        text += f". Reference: {reference_document_type} {reference_document}"

    text += "."

    return text


def build_expense_claim_explanation(row) -> str:
    """
    شرح سطر Expense Claim
    """
    amount = get_money_text(getattr(row, "amount", 0))
    reference_document = convert_value_to_text(getattr(row, "reference_document", ""))

    text = f"Expense Claim was added with amount {amount}"

    if reference_document:
        text += f" based on approved claim {reference_document}"

    text += "."

    return text


def build_employee_advance_explanation(row) -> str:
    """
    شرح سطر Employee Advance
    """
    amount = get_money_text(getattr(row, "amount", 0))
    reference_document = convert_value_to_text(getattr(row, "reference_document", ""))

    text = f"Employee Advance was added under receivables with amount {amount}"

    if reference_document:
        text += f" based on outstanding balance from advance {reference_document}"

    text += "."

    return text


def build_gratuity_explanation(row, doc) -> str:
    """
    شرح سطر مكافأة نهاية الخدمة
    """
    amount = get_money_text(getattr(row, "amount", 0))
    total_years = flt(getattr(doc, "custom_total_of_years", 0), 6)
    monthly_gross_salary = get_money_text(getattr(doc, "custom_monthly_gross_salary", 0))
    company = convert_value_to_text(getattr(doc, "company", ""))
    employment_type = convert_value_to_text(getattr(doc, "custom_employment_type", ""))
    reason_of_leaving = convert_value_to_text(getattr(doc, "custom_reason_of_leaving", ""))

    text = (
        f"Gratuity was added with amount {amount}. "
        f"It was calculated using company {company}, employment type {employment_type}, "
        f"reason of leaving {reason_of_leaving}, total service years {total_years}, "
        f"and salary basis {monthly_gross_salary}."
    )

    return text


def build_additional_salary_explanation(row) -> str:
    """
    شرح سطر Additional Salary
    """
    component = convert_value_to_text(getattr(row, "component", "Additional Salary"))
    amount = get_money_text(getattr(row, "amount", 0))
    reference_document = convert_value_to_text(getattr(row, "reference_document", ""))

    text = f"{component} was added with amount {amount}"

    if reference_document:
        text += f". Reference: {reference_document}"

    text += "."

    return text


def build_generic_row_explanation(row, table_label: str) -> str:
    """
    شرح عام إذا لم نعرف نوع السطر
    """
    component = convert_value_to_text(getattr(row, "component", "Unknown Component"))
    amount = get_money_text(getattr(row, "amount", 0))
    reference_document_type = convert_value_to_text(getattr(row, "reference_document_type", ""))
    reference_document = convert_value_to_text(getattr(row, "reference_document", ""))
    number_of_days = flt(getattr(row, "custom_number_of_days", 0), 2)

    text = f"{table_label} row {component} was added with amount {amount}"

    if number_of_days:
        text += f" and number of days {number_of_days}"

    if reference_document_type or reference_document:
        text += f". Reference: {reference_document_type} {reference_document}"

    text += "."

    return text


def get_row_explanation(row, doc, table_label: str) -> str:
    """
    تحديد نوع السطر ثم بناء الملخص المناسب
    """
    component = convert_value_to_text(getattr(row, "component", "")).lower()

    if "salary days" in component:
        return build_salary_days_explanation(row)

    if "leave" in component:
        return build_leaves_explanation(row)

    if "expense claim" in component:
        return build_expense_claim_explanation(row)

    if "employee advance" in component:
        return build_employee_advance_explanation(row)

    if "gratuity" in component:
        return build_gratuity_explanation(row, doc)

    if "additional salary" in component:
        return build_additional_salary_explanation(row)

    return build_generic_row_explanation(row, table_label)


# =========================================================
# SECTION 4: قراءة الجداول وبناء النص النهائي
# =========================================================

def get_payables_summary_lines(doc) -> list[str]:
    """
    بناء شرح جدول المستحقات
    """
    lines = []
    payables = getattr(doc, "payables", []) or []

    lines.append("")
    add_line(lines, "Payables:")

    if not payables:
        add_line(lines, "- No payable rows were generated.")
        return lines

    for row in payables:
        row_text = get_row_explanation(row, doc, "Payable")
        add_line(lines, f"- {row_text}")

    return lines


def get_receivables_summary_lines(doc) -> list[str]:
    """
    بناء شرح جدول المستردات
    """
    lines = []
    receivables = getattr(doc, "receivables", []) or []

    lines.append("")
    add_line(lines, "Receivables:")

    if not receivables:
        add_line(lines, "- No receivable rows were generated.")
        return lines

    for row in receivables:
        row_text = get_row_explanation(row, doc, "Receivable")
        add_line(lines, f"- {row_text}")

    return lines


def get_totals_summary_lines(doc) -> list[str]:
    """
    بناء سطور التوتال النهائي
    """
    lines = []

    total_payable_amount = flt(getattr(doc, "total_payable_amount", 0), 2)
    total_receivable_amount = flt(getattr(doc, "total_receivable_amount", 0), 2)
    net_amount = flt(total_payable_amount - total_receivable_amount, 2)

    lines.append("")
    add_line(lines, "Final Totals:")
    add_line(lines, f"- Total Payable Amount: {get_money_text(total_payable_amount)}")
    add_line(lines, f"- Total Receivable Amount: {get_money_text(total_receivable_amount)}")

    if net_amount > 0:
        add_line(lines, f"- Net Result: {get_money_text(net_amount)} payable to the employee.")
    elif net_amount < 0:
        add_line(lines, f"- Net Result: {get_money_text(abs(net_amount))} receivable from the employee.")
    else:
        add_line(lines, "- Net Result: settlement is balanced.")

    return lines


def build_full_and_final_summary(doc) -> str:
    """
    الدالة الرئيسية لبناء الملخص الكامل
    """
    summary_lines = []

    summary_lines.extend(get_document_header_lines(doc))
    summary_lines.extend(get_salary_basis_lines(doc))
    summary_lines.extend(get_service_period_lines(doc))
    summary_lines.extend(get_payables_summary_lines(doc))
    summary_lines.extend(get_receivables_summary_lines(doc))
    summary_lines.extend(get_totals_summary_lines(doc))

    return "\n".join(summary_lines).strip()