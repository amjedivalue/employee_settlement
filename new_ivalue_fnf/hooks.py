
app_name = "new_ivalue_fnf"
app_title = "iValue FnF new "
app_publisher = "Amjad"
app_description = "this is a new build for FNF"
app_email = "Amjad.altamimi@ivalueconsult.com"
app_license = "mit"


doc_events = {
    "Full and Final Statement": {
       "before_insert": "new_ivalue_fnf.api.full_and_final.set_transaction_date",
        "validate": "new_ivalue_fnf.api.full_and_final.populate_full_and_final_doc",
        #"before_submit": "new_ivalue_fnf.api.fnf_fix.clean_receivables"

    }
}
 
doctype_js = {
    "Full and Final Statement": "public/js/full_and_final_statement.js",
    # "Full and Final Statement": "public/js/fnf_tracking.js",
}

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "in", ["Full and Final Statement", "Full and Final Outstanding Statement", "Company"]]
        ]
    },
    {
        "dt": "Print Format",
        "filters": [
            ["name", "=", "Custom Full and Final Statement"]
        ]
    },
    {
        "dt": "Workflow",
        "filters": [["name", "in", ["Full and final Statement"]]]
    },
    {
        "dt": "Workflow State",
        "filters": [["workflow_state_name", "in", ["HR User", "HR Manager", "Pending Finance Director", "Pending Supporting Services Director", "Employee Sigen", "Signed", "Cancel"]]]
    },
]   



# app_name = "new_ivalue_fnf"
# app_title = "iValue FnF new "
# app_publisher = "Amjad"
# app_description = "this is a new build for FNF"
# app_email = "Amjad.altamimi@ivalueconsult.com"
# app_license = "mit"

# # Apps
# # ------------------


# fixtures = [
#     {
#         "dt": "Custom Field",
#         "filters": [
#             ["dt", "in", ["Full and Final Statement", "Full and Final Outstanding Statement", "Company"]]
#         ]
#     },
#     {
#         "dt": "Print Format",
#         "filters": [
#             ["name", "=", "Custom Full and Final Statement"]
#         ]
#     }
# ]   


# # required_apps = []

# # Each item in the list will be shown as an app in the apps page
# # add_to_apps_screen = [
# # 	{
# # 		"name": "new_ivalue_fnf",
# # 		"logo": "/assets/new_ivalue_fnf/logo.png",
# # 		"title": "iValue FnF new ",
# # 		"route": "/new_ivalue_fnf",
# # 		"has_permission": "new_ivalue_fnf.api.permission.has_app_permission"
# # 	}
# # ]

# # Includes in <head>
# # ------------------

# # include js, css files in header of desk.html
# # app_include_css = "/assets/new_ivalue_fnf/css/new_ivalue_fnf.css"
# # app_include_js = "/assets/new_ivalue_fnf/js/new_ivalue_fnf.js"

# # include js, css files in header of web template
# # web_include_css = "/assets/new_ivalue_fnf/css/new_ivalue_fnf.css"
# # web_include_js = "/assets/new_ivalue_fnf/js/new_ivalue_fnf.js"

# # include custom scss in every website theme (without file extension ".scss")
# # website_theme_scss = "new_ivalue_fnf/public/scss/website"

# # include js, css files in header of web form
# # webform_include_js = {"doctype": "public/js/doctype.js"}
# # webform_include_css = {"doctype": "public/css/doctype.css"}

# # include js in page
# # page_js = {"page" : "public/js/file.js"}

# # include js in doctype views
# doctype_js = {"Full and Final Statement" : "public/js/full_and_final_statement.js"}
# # doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# # doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# # doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# # Svg Icons
# # ------------------
# # include app icons in desk
# # app_include_icons = "new_ivalue_fnf/public/icons.svg"

# # Home Pages
# # ----------

# # application home page (will override Website Settings)
# # home_page = "login"

# # website user home page (by Role)
# # role_home_page = {
# # 	"Role": "home_page"
# # }

# # Generators
# # ----------

# # automatically create page for each record of this doctype
# # website_generators = ["Web Page"]

# # Jinja
# # ----------

# # add methods and filters to jinja environment
# # jinja = {
# # 	"methods": "new_ivalue_fnf.utils.jinja_methods",
# # 	"filters": "new_ivalue_fnf.utils.jinja_filters"
# # }

# # Installation
# # ------------

# # before_install = "new_ivalue_fnf.install.before_install"
# # after_install = "new_ivalue_fnf.install.after_install"

# # Uninstallation
# # ------------

# # before_uninstall = "new_ivalue_fnf.uninstall.before_uninstall"
# # after_uninstall = "new_ivalue_fnf.uninstall.after_uninstall"

# # Integration Setup
# # ------------------
# # To set up dependencies/integrations with other apps
# # Name of the app being installed is passed as an argument

# # before_app_install = "new_ivalue_fnf.utils.before_app_install"
# # after_app_install = "new_ivalue_fnf.utils.after_app_install"

# # Integration Cleanup
# # -------------------
# # To clean up dependencies/integrations with other apps
# # Name of the app being uninstalled is passed as an argument

# # before_app_uninstall = "new_ivalue_fnf.utils.before_app_uninstall"
# # after_app_uninstall = "new_ivalue_fnf.utils.after_app_uninstall"

# # Desk Notifications
# # ------------------
# # See frappe.core.notifications.get_notification_config

# # notification_config = "new_ivalue_fnf.notifications.get_notification_config"

# # Permissions
# # -----------
# # Permissions evaluated in scripted ways

# # permission_query_conditions = {
# # 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# # }
# #
# # has_permission = {
# # 	"Event": "frappe.desk.doctype.event.event.has_permission",
# # }

# # DocType Class
# # ---------------
# # Override standard doctype classes

# # override_doctype_class = {
# # 	"ToDo": "custom_app.overrides.CustomToDo"
# # }

# # Document Events
# # ---------------
# # Hook on document methods and events

# doc_events = {
#     "Full and Final Statement": {
#         "before_insert": "new_ivalue_fnf.api.full_and_final.set_transaction_date",
#         "validate": "new_ivalue_fnf.api.full_and_final.populate_full_and_final_doc",
#     }
# }

# # Scheduled Tasks
# # ---------------

scheduler_events = {
	"cron": {
        "0 */2 * * *": [
            "new_ivalue_fnf.fetch_zoho.fetch_zoho_doc",
        ]
    }
}

# # Testing
# # -------

# # before_tests = "new_ivalue_fnf.install.before_tests"

# # Overriding Methods
# # ------------------------------
# #
# # override_whitelisted_methods = {
# # 	"frappe.desk.doctype.event.event.get_events": "new_ivalue_fnf.event.get_events"
# # }
# #
# # each overriding function accepts a `data` argument;
# # generated from the base implementation of the doctype dashboard,
# # along with any modifications made in other Frappe apps
# # override_doctype_dashboards = {
# # 	"Task": "new_ivalue_fnf.task.get_dashboard_data"
# # }

# # exempt linked doctypes from being automatically cancelled
# #
# # auto_cancel_exempted_doctypes = ["Auto Repeat"]

# # Ignore links to specified DocTypes when deleting documents
# # -----------------------------------------------------------

# # ignore_links_on_delete = ["Communication", "ToDo"]

# # Request Events
# # ----------------
# # before_request = ["new_ivalue_fnf.utils.before_request"]
# # after_request = ["new_ivalue_fnf.utils.after_request"]

# # Job Events
# # ----------
# # before_job = ["new_ivalue_fnf.utils.before_job"]
# # after_job = ["new_ivalue_fnf.utils.after_job"]

# # User Data Protection
# # --------------------

# # user_data_fields = [
# # 	{
# # 		"doctype": "{doctype_1}",
# # 		"filter_by": "{filter_by}",
# # 		"redact_fields": ["{field_1}", "{field_2}"],
# # 		"partial": 1,
# # 	},
# # 	{
# # 		"doctype": "{doctype_2}",
# # 		"filter_by": "{filter_by}",
# # 		"partial": 1,
# # 	},
# # 	{
# # 		"doctype": "{doctype_3}",
# # 		"strict": False,
# # 	},
# # 	{
# # 		"doctype": "{doctype_4}"
# # 	}
# # ]

# # Authentication and authorization
# # --------------------------------

# # auth_hooks = [
# # 	"new_ivalue_fnf.auth.validate"
# # ]

# # Automatically update python controller files with type annotations for this app.
# # export_python_type_annotations = True

# # default_log_clearing_doctypes = {
# # 	"Logging DocType Name": 30  # days to retain logs
# # }

