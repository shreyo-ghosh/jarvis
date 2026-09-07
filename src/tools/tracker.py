"""
Revenue and task tracker — DynamoDB backed (replaces local JSON files).
Keys used in DynamoDB:
  revenue        → list of revenue entries
  tasks          → list of task entries
"""

import json
from datetime import datetime
from tools.dynamo import DynamoStore

_db = DynamoStore()


# ── Revenue ──────────────────────────────────────────────────────────────────

def log_revenue(amount: float, source: str, description: str, date: str = "") -> str:
    records = _db.get_list("revenue")
    entry = {
        "id": len(records) + 1,
        "amount": float(amount),
        "source": source,
        "description": description,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "logged_at": datetime.now().isoformat()
    }
    records.append(entry)
    _db.put("revenue", records)

    total = sum(r["amount"] for r in records)
    return (
        f"✅ *Revenue logged!*\n"
        f"💰 ₹{amount:,.0f} from *{source}*\n"
        f"📝 {description}\n\n"
        f"_Running total: ₹{total:,.0f}_"
    )


def get_summary() -> str:
    records = _db.get_list("revenue")
    if not records:
        return "📊 No revenue logged yet.\n_Try: 'log revenue: ₹5000 from LaunchLayer client ABC'_"

    total = sum(r["amount"] for r in records)
    this_month = datetime.now().strftime("%Y-%m")
    month_total = sum(r["amount"] for r in records if r.get("date", "").startswith(this_month))

    by_source: dict = {}
    for r in records:
        by_source[r["source"]] = by_source.get(r["source"], 0) + r["amount"]

    lines = [
        "📊 *Revenue Summary*\n",
        f"💰 *All Time:* ₹{total:,.0f}",
        f"📅 *This Month:* ₹{month_total:,.0f}\n",
        "*By Source:*"
    ]
    for src, amt in sorted(by_source.items(), key=lambda x: -x[1]):
        lines.append(f"  • {src}: ₹{amt:,.0f}")

    lines.append("\n*Recent 5 entries:*")
    for r in sorted(records, key=lambda x: x.get("date", ""), reverse=True)[:5]:
        lines.append(f"  • ₹{r['amount']:,.0f} — {r['description']} ({r.get('date','')})")

    return "\n".join(lines)


# ── Tasks ─────────────────────────────────────────────────────────────────────

def log_task(task: str, priority: str = "medium", due_date: str = "") -> str:
    tasks = _db.get_list("tasks")
    entry = {
        "id": len(tasks) + 1,
        "task": task,
        "priority": priority,
        "due_date": due_date,
        "status": "pending",
        "logged_at": datetime.now().isoformat()
    }
    tasks.append(entry)
    _db.put("tasks", tasks)

    icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
    return (
        f"✅ Task #{entry['id']} logged\n"
        f"{icon} [{priority.upper()}] {task}"
        + (f"\n📅 Due: {due_date}" if due_date else "")
    )


def get_tasks() -> str:
    tasks = _db.get_list("tasks")
    pending = [t for t in tasks if t.get("status") == "pending"]
    if not pending:
        return "✅ No pending tasks. You're clear."

    order = {"high": 0, "medium": 1, "low": 2}
    pending.sort(key=lambda t: (order.get(t.get("priority", "medium"), 1), t.get("logged_at", "")))

    icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    lines = [f"📋 *Pending Tasks ({len(pending)}):*\n"]
    for t in pending:
        due = f" — due {t['due_date']}" if t.get("due_date") else ""
        lines.append(f"{icon.get(t.get('priority','medium'),'🟡')} #{t['id']}: {t['task']}{due}")
    lines.append("\n_To complete: 'mark task #N as done'_")
    return "\n".join(lines)


def mark_done(task_id: int) -> str:
    tasks = _db.get_list("tasks")
    for t in tasks:
        if t.get("id") == task_id:
            t["status"] = "done"
            t["completed_at"] = datetime.now().isoformat()
            _db.put("tasks", tasks)
            return f"✅ Done: _{t['task']}_"
    return f"Task #{task_id} not found."
