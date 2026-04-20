# Copyright (c) 2026, Amjad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class FullandFinalSettings(Document):
    def validate(self):
        self.validate_company_is_not_duplicated()
        self.add_default_components_if_missing()
        self.validate_gratuity_for_saudi_only()

    def validate_company_is_not_duplicated(self):
        """
        منع وجود أكثر من سجل إعدادات لنفس الشركة
        """
        if not self.company:
            return

        existing_name = frappe.db.get_value(
            "Full and Final Settings",
            {
                "company": self.company,
                "name": ["!=", self.name],
            },
            "name",
        )

        if existing_name:
            frappe.throw(
                _("Full and Final Settings already exists for company: {0}").format(self.company)
            )

    def add_default_components_if_missing(self):
        """
        إذا كان جدول العناصر فارغًا نضيف السطور الافتراضية
        """
        if self.components:
            return

        default_payable_account = self.get_company_default_payable_account(self.company)
        default_employee_advance_account = self.get_company_employee_advance_account(self.company)

        default_rows = [
            {
                "component_key": "Salary Days",
                "display_name": "Salary Days",
                "account": default_payable_account,
                "is_enabled": 0,
            },
            {
                "component_key": "Leaves",
                "display_name": "Leaves",
                "account": default_payable_account,
                "is_enabled": 0,
            },
            {
                "component_key": "Expense Claim",
                "display_name": "Expense Claim",
                "account": default_payable_account,
                "is_enabled": 0,
            },
            {
                "component_key": "Employee Advance",
                "display_name": "Employee Advance",
                "account": default_employee_advance_account,
                "is_enabled": 0,
            },
         
            {
                "component_key": "Additional Salary Earning",
                "display_name": "Addition",
                "account": default_payable_account,
                "is_enabled": 0,
            },
            {
                "component_key": "Additional Salary Deduction",
                "display_name": "Deduction",
                "account": default_payable_account,
                "is_enabled": 0,
            },
            
        ]
        company_country = frappe.db.get_value("Company", self.company, "country")
        # فقط إذا الشركة سعودية نضيف سطر المكافأة
        if company_country == "Saudi Arabia":
            default_rows.append({
                "component_key": "Gratuity",
                "display_name": "Gratuity",
                "account": default_payable_account,
                "is_enabled": 0,
            })

        for row_data in default_rows:
            self.append("components", row_data)

    def get_company_default_payable_account(self, company: str) -> str | None:
        """
        جلب الحساب الافتراضي الذي سنستخدمه للمستحقات
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

    def get_company_employee_advance_account(self, company: str) -> str | None:
        """
        جلب حساب السلف من الشركة
        """
        if not company:
            return None

        company_doc = frappe.get_cached_doc("Company", company)

        candidate_fields = [
            "default_employee_advance_account",
            "default_receivable_account",
            "default_payable_account",
        ]

        for field_name in candidate_fields:
            if hasattr(company_doc, field_name):
                field_value = getattr(company_doc, field_name)
                if field_value:
                    return field_value

        return None

    def validate_gratuity_for_saudi_only(self):
            """
            منع تفعيل خيار المكافأة إذا لم تكن الشركة في السعودية
            """
            for row in self.components:
                # نتحقق إذا كان السطر يخص المكافأة ومفعل
                if row.component_key == "Gratuity" and row.is_enabled:
                    # جلب بلد الشركة
                    company_country = frappe.db.get_value("Company", self.company, "country")
                    
                    if company_country != "Saudi Arabia":
                        frappe.throw(
                            _("Gratuity component can only be enabled for companies located in Saudi Arabia. Current company country is {0}").format(company_country)
                        )