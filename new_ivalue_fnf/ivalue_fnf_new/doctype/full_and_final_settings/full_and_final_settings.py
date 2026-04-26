import frappe
from frappe.model.document import Document
from frappe import _


class FullandFinalSettings(Document):
    def validate(self):
        self.validate_company_is_not_duplicated()
        self.add_default_components_if_missing()
        self.validate_gratuity_for_saudi_only()
        self.add_default_manual_row_settings_if_missing()

    def validate_company_is_not_duplicated(self):
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
                _("Full and Final Settings already exists for company: {0}").format(
                    self.company
                )
            )

    def add_default_components_if_missing(self):
        default_expense_account = self.get_company_default_expense_account(self.company)
        default_employee_advance_account = self.get_company_employee_advance_account(
            self.company
        )

        default_rows = [
            {
                "component_key": "Salary Days",
                "display_name": "Salary Days",
                "account": default_expense_account,
                "is_enabled": 0,
            },
            {
                "component_key": "Leaves",
                "display_name": "Leaves",
                "account": default_expense_account,
                "is_enabled": 0,
            },
            # {
            #     "component_key": "Expense Claim",
            #     "display_name": "Expense Claim",
            #     "account": default_expense_account,
            #     "is_enabled": 0,
            # },
            {
                "component_key": "Employee Advance",
                "display_name": "Employee Advance",
                "account": default_employee_advance_account,
                "is_enabled": 0,
            },
            {
                "component_key": "Additional Salary Earning",
                "display_name": "Additional Salary Earning",
                "account": default_expense_account,
                "is_enabled": 0,
            },
            {
                "component_key": "Additional Salary Deduction",
                "display_name": "Additional Salary Deduction",
                "account": default_employee_advance_account,
                "is_enabled": 0,
            },
        ]

        company_country = frappe.db.get_value("Company", self.company, "country")

        if company_country == "Saudi Arabia":
            default_rows.append(
                {
                    "component_key": "Gratuity",
                    "display_name": "Gratuity",
                    "account": default_expense_account,
                    "is_enabled": 0,
                }
            )

        existing_component_keys = []

        for row in self.components or []:
            if row.component_key:
                existing_component_keys.append(row.component_key)

        for row_data in default_rows:
            if row_data["component_key"] in existing_component_keys:
                continue

            self.append("components", row_data)

    def add_default_manual_row_settings_if_missing(self):
        default_expense_account = self.get_company_default_expense_account(self.company)
        default_employee_advance_account = self.get_company_employee_advance_account(
            self.company
        )

        default_rows = [
        {
            "row_type": "Payables Manual Row",
            "salary_component": "Other Earning",
            "account": default_expense_account,
            "is_enabled": 1,
        },
        {
            "row_type": "Receivables Manual Row",
            "salary_component": "Other Deduction",
            "account": default_employee_advance_account,
            "is_enabled": 1,
        },
    ]

        existing_row_types = []

        for row in self.manual_row_settings or []:
            if row.row_type:
                existing_row_types.append(row.row_type)

        for row_data in default_rows:
            if row_data["row_type"] in existing_row_types:
                continue

            self.append("manual_row_settings", row_data)

    def validate_gratuity_for_saudi_only(self):
        for row in self.components or []:
            if row.component_key != "Gratuity":
                continue

            if not row.is_enabled:
                continue

            company_country = frappe.db.get_value("Company", self.company, "country")

            if company_country != "Saudi Arabia":
                frappe.throw(
                    _(
                        "Gratuity component can only be enabled for companies located in Saudi Arabia. Current company country is {0}"
                    ).format(company_country)
                )

    def get_company_default_payable_account(self, company: str) -> str | None:
        if not company:
            return None

        company_doc = frappe.get_cached_doc("Company", company)

        candidate_fields = [
            "default_payroll_payable_account",
            "payroll_payable_account",
            "default_payable_account",
        ]

        for field_name in candidate_fields:
            if not hasattr(company_doc, field_name):
                continue

            account = getattr(company_doc, field_name)

            if self.is_valid_company_account(account, company):
                return account

        return None

    def get_company_employee_advance_account(self, company: str) -> str | None:
        if not company:
            return None

        company_doc = frappe.get_cached_doc("Company", company)

        candidate_fields = [
            "default_employee_advance_account",
            "default_receivable_account",
        ]

        for field_name in candidate_fields:
            if not hasattr(company_doc, field_name):
                continue

            account = getattr(company_doc, field_name)

            if self.is_valid_company_account(account, company):
                return account

        account = self.get_first_account_by_keywords(
            company=company,
            keywords=[
                "employee advance",
                "employee advances",
                "employee receivable",
                "staff advance",
                "advance",
            ],
            root_types=["Asset"],
        )

        if account:
            return account

        return None

   
    def get_company_default_expense_account(self, company: str) -> str | None:
        if not company:
            return None

        company_doc = frappe.get_cached_doc("Company", company)

        candidate_fields = [
            "default_expense_account",
            "default_operating_cost_account",
        ]

        for field_name in candidate_fields:
            if not hasattr(company_doc, field_name):
                continue

            account = getattr(company_doc, field_name)

            if self.is_valid_company_expense_account(account, company):
                return account

        account = self.get_first_account_by_keywords(
            company=company,
            keywords=[
                "salary expense",
                "salaries",
                "payroll expense",
                "payroll expenses",
                "employee benefit",
                "employee benefits",
                "staff cost",
                "staff costs",
                "administrative expense",
                "administrative expenses",
                "end of service",
                "gratuity expense",
                "settlement expense",
            ],
            root_types=["Expense"],
        )

        if account:
            return account

        return self.get_first_non_cogs_expense_account(company)
    def is_valid_company_expense_account(self, account: str | None, company: str) -> bool:
        if not self.is_valid_company_account(account, company):
            return False

        account_data = frappe.db.get_value(
            "Account",
            account,
            ["root_type"],
            as_dict=True,
        )

        if not account_data:
            return False

        if account_data.root_type != "Expense":
            return False

        account_name = str(account).lower()

        blocked_keywords = [
            "cost of goods sold",
            "cogs",
            "stock",
            "inventory",
            "raw material",
        ]

        for keyword in blocked_keywords:
            if keyword in account_name:
                return False

        return True


    def get_first_non_cogs_expense_account(self, company: str) -> str | None:
        if not company:
            return None

        accounts = frappe.get_all(
            "Account",
            filters={
                "company": company,
                "is_group": 0,
                "root_type": "Expense",
            },
            fields=["name"],
            order_by="lft asc",
        )

        blocked_keywords = [
            "cost of goods sold",
            "cogs",
            "stock",
            "inventory",
            "raw material",
        ]

        for account in accounts:
            account_name = str(account.name).lower()
            is_blocked = False

            for keyword in blocked_keywords:
                if keyword in account_name:
                    is_blocked = True
                    break

            if not is_blocked:
                return account.name

        return None
    def get_first_account_by_keywords(
        self,
        company: str,
        keywords: list[str],
        root_types: list[str] | None = None,
    ) -> str | None:
        if not company:
            return None

        if not keywords:
            return None

        filters = {
            "company": company,
            "is_group": 0,
        }

        if root_types:
            filters["root_type"] = ["in", root_types]

        accounts = frappe.get_all(
            "Account",
            filters=filters,
            fields=["name"],
            order_by="lft asc",
        )

        for account in accounts:
            account_name = str(account.name).lower()

            for keyword in keywords:
                if keyword.lower() in account_name:
                    return account.name

        return None

    def is_valid_company_account(self, account: str | None, company: str) -> bool:
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