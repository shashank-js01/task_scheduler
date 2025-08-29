import frappe
from frappe.sessions import datetime
from frappe.utils import add_days, add_months, add_years, getdate

def handle_auto_repeat_task(doc, method):
    # Only run for tasks created via auto repeat
    if not doc.auto_repeat:
        return

    # Get Auto Repeat config
    auto_repeat = frappe.get_doc("Auto Repeat", doc.auto_repeat)
    reference_doc = frappe.get_doc(auto_repeat.reference_doctype, auto_repeat.reference_document)

    if reference_doc.doctype != "Task":
        return  # Only apply this logic for Task

    # Store reference to original task
    doc.reference_task = reference_doc.name

    # Calculate original duration
    duration = (getdate(reference_doc.exp_end_date) - getdate(reference_doc.exp_start_date)).days

    # Today's date
    today = getdate()

    # Set new expected_start_date based on frequency
    frequency = auto_repeat.frequency
    new_start = None

    if frequency == "Daily":
        new_start = add_days(today, 1)

    elif frequency == "Weekly":
        repeat_days = auto_repeat.get("repeat_on_days") or []
        repeat_days = [day.strip() for day in repeat_days]

        for i in range(1, 8):
            future_day = add_days(today, i)
            if future_day.strftime("%A") in repeat_days:
                new_start = future_day
                break

    elif frequency == "Monthly":
        new_start = add_months(reference_doc.expected_start_date, 1)

    elif frequency == "Quarterly":
        new_start = add_months(reference_doc.expected_start_date, 3)

    elif frequency == "Half-Yearly":
        new_start = add_months(reference_doc.expected_start_date, 6)

    elif frequency == "Yearly":
        new_start = add_years(reference_doc.expected_start_date, 1)

    if new_start:
        doc.expected_start_date = new_start
        doc.expected_end_date = add_days(new_start, duration)

    # Reset task status and progress
    doc.status = "Open"
    doc.progress = 0
    doc.completed_on = None
    doc.actual_time = 0

    # Copy assignments from reference task
    copy_assignments(reference_doc.name, doc)

def copy_assignments(from_task_name, to_task_doc):
    """Copy ToDo assignments from the original task to the new one"""
    assignments = frappe.get_all("ToDo", filters={"reference_name": from_task_name, "reference_type": "Task"}, fields=["owner", "description"])

    for a in assignments:
        todo = frappe.get_doc({
            "doctype": "ToDo",
            "owner": a.owner,
            "description": a.description,
            "reference_type": "Task",
            "reference_name": to_task_doc.name,
            "allocated_to": a.owner
        })
        todo.insert(ignore_permissions=True)

def create_tasks_from_schedule(doc, method=None):
    """
    Triggered when Auto Repeat is updated.
    Creates Task only if not already created for that schedule.
    """

    schedule_list = doc.get_auto_repeat_schedule()

    for row in schedule_list:
        reference_doc = row.get("reference_document")
        next_date = row.get("next_scheduled_date")

        # check if a task already exists for this reference + date
        exists = frappe.db.exists(
            "Task",
            {
                "custom_reference_task": reference_doc,
                "exp_end_date": next_date
            }
        )
        # get the reference Task (master document)
        ref_task = frappe.get_doc("Task", reference_doc)

        # ensure next_date is a date (not datetime)
        if isinstance(next_date, datetime):
            next_date = next_date.date()

        # ensure exp_start_date is also a date
        exp_start = ref_task.exp_start_date
        if isinstance(exp_start, datetime):
            exp_start = exp_start.date()

        if type(exp_start) is None or type(next_date) is None:
            continue
            
        if exists or next_date <= exp_start:
           continue


        # copy all values
        new_task = frappe.copy_doc(ref_task)

        # override required fields
        new_task.custom_reference_task = reference_doc
        new_task.exp_end_date = next_date

        # clear auto repeat link if it exists in Task (to avoid recursion)
        if hasattr(new_task, "auto_repeat"):
            new_task.auto_repeat = None

        # insert as new doc
        new_task.insert(ignore_permissions=True)
    frappe.db.commit()
