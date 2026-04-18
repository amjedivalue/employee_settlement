import frappe
from frappe.utils import flt


# =========================================================
# SECTION 1: دوال مساعدة لقراءة شروط المكافأة
# =========================================================

def get_company_country(company: str) -> str | None:
    """
    جلب بلد الشركة
    """
    if not company:
        return None

    return frappe.db.get_value("Company", company, "country")


def normalize_text_value(value) -> str:
    """
    توحيد النص للتقليل من مشاكل المسافات أو الفراغات
    """
    if not value:
        return ""

    return str(value).strip()


def is_saudi_company(company: str) -> bool:
    """
    فحص هل الشركة في السعودية
    """
    company_country = normalize_text_value(get_company_country(company))

    if company_country == "Saudi Arabia":
        return True

    return False


def is_permanent_employment(employment_type: str) -> bool:
    """
    فحص هل نوع التوظيف دائم
    """
    employment_type_value = normalize_text_value(employment_type)

    if employment_type_value == "Permanent":
        return True

    return False


def is_valid_reason_for_gratuity(reason_of_leaving: str) -> bool:
    """
    فحص هل سبب المغادرة من الأسباب المسموحة للمكافأة
    """
    reason_value = normalize_text_value(reason_of_leaving)

    allowed_reasons = [
        "End of contract",
        "Termination",
        "Resignation",
    ]

    if reason_value in allowed_reasons:
        return True

    return False


# =========================================================
# SECTION 2: حساب أصل المكافأة حسب النظام السعودي
# =========================================================

def calculate_base_saudi_gratuity(service_years: float, last_salary: float) -> float:
    """
    حساب أصل المكافأة قبل تطبيق قاعدة الاستقالة
    """
    if service_years <= 0:
        return 0

    if last_salary <= 0:
        return 0

    if service_years <= 5:
        return flt(service_years * (last_salary / 2), 2)

    first_five_years_amount = flt(5 * (last_salary / 2), 2)
    remaining_years = flt(service_years - 5, 6)
    remaining_years_amount = flt(remaining_years * last_salary, 2)

    return flt(first_five_years_amount + remaining_years_amount, 2)


# =========================================================
# SECTION 3: تطبيق قاعدة الاستقالة
# =========================================================

def apply_resignation_rule_on_saudi_gratuity(
    base_gratuity_amount: float,
    service_years: float,
    reason_of_leaving: str,
) -> float:
    """
    تطبيق قاعدة الاستقالة حسب النظام السعودي
    """
    reason_value = normalize_text_value(reason_of_leaving)

    if base_gratuity_amount <= 0:
        return 0

    if reason_value != "Resignation":
        return flt(base_gratuity_amount, 2)

    if service_years < 2:
        return 0

    if service_years >= 2 and service_years <= 5:
        return flt(base_gratuity_amount / 3, 2)

    if service_years > 5 and service_years < 10:
        return flt((base_gratuity_amount * 2) / 3, 2)

    return flt(base_gratuity_amount, 2)


# =========================================================
# SECTION 4: الحساب النهائي للمكافأة
# =========================================================

def calculate_saudi_gratuity_amount(
    company: str,
    employment_type: str,
    reason_of_leaving: str,
    service_years: float,
    last_salary: float,
) -> float:
    """
    حساب المكافأة النهائية بعد تطبيق كل الشروط
    """
    if not is_saudi_company(company):
        return 0

    if not is_permanent_employment(employment_type):
        return 0

    if not is_valid_reason_for_gratuity(reason_of_leaving):
        return 0

    base_gratuity_amount = calculate_base_saudi_gratuity(service_years, last_salary)

    final_gratuity_amount = apply_resignation_rule_on_saudi_gratuity(
        base_gratuity_amount=base_gratuity_amount,
        service_years=service_years,
        reason_of_leaving=reason_of_leaving,
    )

    return flt(final_gratuity_amount, 2)

# =========================================================
# الاعدات والتحكم بالظهور 
# =========================================================

def get_component_setting_for_company(company: str, component_key: str):
    """
    جلب إعداد عنصر محدد من شاشة Full and Final Settings لنفس الشركة
    """
    if not company:
        return None

    if not component_key:
        return None

    settings_name = frappe.db.get_value(
        "Full and Final Settings",
        {"company": company},
        "name",
    )

    if not settings_name:
        return None

    settings_doc = frappe.get_doc("Full and Final Settings", settings_name)

    for row in settings_doc.components:
        if row.component_key == component_key:
            return row

    return None


# =========================================================
# SECTION 5: بناء سطر المكافأة لجدول المستحقات
# =========================================================

def build_gratuity_payable_row(
    employee: str,
    company: str,
    employment_type: str,
    reason_of_leaving: str,
    service_data: dict,
    salary_data: dict,
    account: str,
) -> tuple[list[dict], float]:
    """
    بناء سطر مكافأة نهاية الخدمة
    """
    payable_rows = []
    total_amount = 0.0
    component_setting = get_component_setting_for_company(company, "Gratuity")

    if not component_setting:
        return payable_rows, total_amount

    if not component_setting.is_enabled:
        return payable_rows, total_amount

    total_years = flt(service_data.get("total_years"), 6)
    last_salary = flt(salary_data.get("breakdown", {}).get("monthly_total"), 2)

    gratuity_amount = calculate_saudi_gratuity_amount(
        company=company,
        employment_type=employment_type,
        reason_of_leaving=reason_of_leaving,
        service_years=total_years,
        last_salary=last_salary,
    )

    if gratuity_amount <= 0:
        return payable_rows, total_amount

    row = {
        "component_key": "Gratuity",
        "component": component_setting.display_name or "Gratuity",
        "reference_document_type": "Employee",
        "reference_document": employee,
        "account": component_setting.account or account,
        "amount": gratuity_amount,
        "status": "Settled",
        "custom_number_of_days": 0,
    }

    payable_rows.append(row)
    total_amount = gratuity_amount

    return payable_rows, flt(total_amount, 2)