# 📄 Auto Repeat Task Scheduling – Technical Document

## Objective

Implement a system in ERPNext to auto-generate **Task** documents based on an **Auto Repeat** schedule (Daily, Weekly, Monthly, etc.), while:

* Cloning original task data (fields, assignments, child tables)
* Overriding only specific fields:

  * `custom_reference_task` → set to original Task (reference document)
  * `exp_end_date` → set to Auto Repeat’s next scheduled date
* Creating new Tasks only when conditions are met (no duplicates, valid dates)
* Clearing the `auto_repeat` field in new tasks to avoid recursion

---

## Customization Summary

| Component         | Action                                                        |
| ----------------- | ------------------------------------------------------------- |
| **Doctype Used**  | `Task` (ERPNext core)                                         |
| **Custom App**    | `task_scheduler`                                              |
| **Custom Fields** | `custom_reference_task` (Link → Task)                         |
| **Hook Added**    | `on_update` on Auto Repeat                                    |
| **Core Logic**    | Implemented in `create_tasks_from_schedule(doc, method)`      |
| **Trigger**       | Frappe’s built-in `Auto Repeat` → triggers our hook on update |

---

## 🔧 Field Mapping in Task

| Label               | Fieldname               | Type        | Source                                    |
| ------------------- | ----------------------- | ----------- | ----------------------------------------- |
| Expected Start Date | `exp_start_date`        | Date        | From reference task (or adjusted logic)   |
| Expected End Date   | `exp_end_date`          | Date        | From schedule row (`next_scheduled_date`) |
| Reference Task      | `custom_reference_task` | Link (Task) | From schedule row (`reference_document`)  |

---

## 🔄 Auto Repeat Behavior by Frequency

### Daily → Next day, keep duration from original

### Weekly → Next matching weekday, keep duration

### Monthly → Add 1 month, keep duration

### Quarterly → Add 3 months, keep duration

### Half-Yearly → Add 6 months, keep duration

### Yearly → Add 12 months, keep duration

The **next scheduled date** is always compared against the reference task’s `exp_start_date` to ensure:

✅ New task is only created if `next_scheduled_date > exp_start_date`

---

## 🧠 What the Hook Function Does

**Path:** `task_scheduler/api/task.py`

### Core Responsibilities:

* Fetch schedule rows via `get_auto_repeat_schedule()`
* For each row:

  * Check if Task already exists for `(custom_reference_task, exp_end_date)` → **skip if exists**
  * Check if `next_scheduled_date > exp_start_date` → **skip if not valid**
  * Copy the reference Task with `frappe.copy_doc()`
  * Override fields (`custom_reference_task`, `exp_end_date`)
  * Reset `auto_repeat` to `None`
  * Insert new Task

### Sample Snippet:

```python
if not frappe.db.exists("Task", {
    "custom_reference_task": reference_docname,
    "exp_end_date": next_date
}):
    new_task = frappe.copy_doc(ref_task)
    new_task.custom_reference_task = reference_docname
    new_task.exp_end_date = next_date
    new_task.auto_repeat = None
    new_task.insert(ignore_permissions=True)
```

---

## 🚀 Testing the System

### Test Steps:

1. **Create base Task**

   * Fill `exp_start_date`, `exp_end_date`

2. **Create Auto Repeat**

   * Set frequency, link to Task, define start date

3. **Save Auto Repeat**

   * Triggers `on_update` hook automatically

4. **Verify**

   * A new Task is created only if conditions are met
   * Fields cloned from reference Task
   * `custom_reference_task` and `exp_end_date` overridden

---

## 📌 Notes

* Hook runs on `on_update` of Auto Repeat.
* Ensures **no duplicate tasks** for the same `(reference, date)`.
* Only generates valid tasks (`next_date > exp_start_date`).
* Assignments, child tables, and most fields are copied from the reference Task.
* Auto Repeat link is cleared on the new Task to avoid infinite loops.
