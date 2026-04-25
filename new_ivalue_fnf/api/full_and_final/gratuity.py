from frappe.utils import flt

from new_ivalue_fnf.api.full_and_final.core_data import get_component_setting_for_company
from new_ivalue_fnf.api.full_and_final.settlement_builders import append_row


def log_trace(message: str, data=None):
    print(f"[FNF gratuity] {message} | {data}")


def normalize_text(value) -> str:
    """
    توحيد النص قبل المقارنة.
    """
    if not value:
        return ""

    return str(value).strip()


def is_saudi_gratuity_allowed(company_country: str, employment_type: str, reason_of_leaving: str) -> bool:
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

    if normalize_text(reason_of_leaving) not in ["End of contract", "Termination", "Resignation"]:
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


def apply_resignation_rule(amount: float, service_years: float, reason_of_leaving: str) -> float:
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

    if not is_saudi_gratuity_allowed(company_country, employment_type, reason_of_leaving):
        log_trace("gratuity skipped by policy", {
            "company_country": company_country,
            "employment_type": employment_type,
            "reason_of_leaving": reason_of_leaving,
        })
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
        log_trace("gratuity amount is zero", {
            "service_years": service_years,
            "monthly_salary": monthly_salary,
            "reason_of_leaving": reason_of_leaving,
        })
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

    log_trace("gratuity row added", {
        "amount": final_amount,
        "service_years": service_years,
        "monthly_salary": monthly_salary,
        "reason_of_leaving": reason_of_leaving,
    })