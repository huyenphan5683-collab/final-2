import os
import random
from pathlib import Path
import numpy as np
import pandas as pd

INPUT_FILE = os.getenv("INPUT_FILE", "smartlog_service_master_2023_2025.xlsx")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "smartlog_service_master_2023_2025_regenerated.xlsx")
SEED = int(os.getenv("SEED", "42"))

EASY_CATEGORIES = {"User Access", "Master Data", "Configuration", "Report/BI"}
MEDIUM_CATEGORIES = {"System Bug", "Integration Issue", "Performance", "Workflow", "Carrier/3PL Sync"}
HARD_CATEGORIES = {"Feature Request", "Enhancement", "Customization", "New Requirement"}

PRIORITY_TO_TARGET = {
    "P1": {"response": 15, "resolution": 240},
    "P2": {"response": 30, "resolution": 480},
    "P3": {"response": 60, "resolution": 1440},
    "P4": {"response": 120, "resolution": 2880},
}
SEVERITY_TO_PRIORITY = {"Critical": "P1", "High": "P2", "Medium": "P3", "Low": "P4"}

NEGATIVE_COMMENTS = [
    "The issue remained unresolved longer than expected and required repeated follow-up.",
    "Support response was delayed and affected operations more than expected.",
    "The team had to coordinate across functions, which prolonged the resolution time.",
    "The issue was not handled as quickly as expected for business operations.",
    "The customer needed urgent support but the case took longer than expected to close."
]
NEUTRAL_COMMENTS = [
    "Support met expectations overall, with slight room for improvement.",
    "The issue was resolved with acceptable handling time.",
    "The case was handled adequately and communication was clear.",
    "The support process was generally satisfactory.",
    "The service experience was acceptable for this type of issue."
]
POSITIVE_COMMENTS = [
    "The issue was resolved quickly and the support team communicated clearly.",
    "Support was timely and the problem was fixed efficiently.",
    "The team responded fast and handled the case professionally.",
    "The service experience was smooth and met expectations well.",
    "The issue was closed promptly with effective support."
]

def choose_ticket_bucket(category, severity, priority):
    category = str(category).strip()
    severity = str(severity).strip()
    priority = str(priority).strip()
    if category in HARD_CATEGORIES:
        return "hard_feature"
    if severity in {"Critical", "High"} and category in {"System Bug", "Integration Issue", "Workflow"}:
        return "hard_feature" if random.random() < 0.18 else "medium"
    if category in EASY_CATEGORIES:
        return "easy"
    if category in MEDIUM_CATEGORIES:
        return "medium"
    if priority == "P4" or severity == "Low":
        return "easy"
    return "medium"

def gen_response_minutes(bucket, priority):
    target = PRIORITY_TO_TARGET.get(priority, {"response": 60})["response"]
    if bucket == "easy":
        value = np.random.triangular(2, max(3, target * 0.35), max(8, target * 1.2))
    elif bucket == "medium":
        value = np.random.triangular(5, max(10, target * 0.8), max(20, target * 2.5))
    else:
        value = np.random.triangular(10, max(20, target * 1.2), max(30, target * 4.0))
    return round(float(max(1, value)), 2)

def gen_resolution_minutes(bucket):
    if bucket == "easy":
        return round(float(np.random.triangular(5, 20, 45)), 2)   # avg < 30p
    if bucket == "medium":
        return round(float(np.random.uniform(2880, 10080)), 2)    # 2-7 ngày
    return round(float(np.random.uniform(30240, 50400)), 2)       # 3-5 tuần

def gen_waiting_customer_minutes(bucket):
    if bucket == "easy":
        return round(float(np.random.uniform(0, 10)), 2)
    if bucket == "medium":
        return round(float(np.random.uniform(0, 480)), 2)
    return round(float(np.random.uniform(0, 4320)), 2)

def gen_reopened_count(bucket):
    if bucket == "easy":
        return int(np.random.choice([0, 1], p=[0.93, 0.07]))
    if bucket == "medium":
        return int(np.random.choice([0, 1, 2, 3], p=[0.62, 0.23, 0.10, 0.05]))
    return int(np.random.choice([0, 1, 2, 3, 4], p=[0.28, 0.27, 0.22, 0.15, 0.08]))

def gen_escalated(bucket):
    if bucket == "easy":
        return bool(np.random.choice([False, True], p=[0.92, 0.08]))
    if bucket == "medium":
        return bool(np.random.choice([False, True], p=[0.70, 0.30]))
    return bool(np.random.choice([False, True], p=[0.28, 0.72]))

def gen_breach_reason(response_met, resolution_met, escalated, waiting_customer_min):
    if response_met and resolution_met:
        return "No breach"
    reasons, weights = [], []
    if waiting_customer_min > 120:
        reasons += ["Waiting for customer"]
        weights += [4]
    if escalated:
        reasons += ["Dependency on product team", "Complex root cause analysis", "Internal delay"]
        weights += [3, 4, 2]
    else:
        reasons += ["Internal delay", "Incorrect prioritization", "Environment/data issue"]
        weights += [3, 2, 3]
    if not response_met:
        reasons += ["Incorrect prioritization", "Internal delay"]
        weights += [3, 2]
    if not resolution_met:
        reasons += ["Complex root cause analysis", "Environment/data issue", "Dependency on product team"]
        weights += [4, 3, 3]
    return random.choices(reasons, weights=weights, k=1)[0]

def gen_csat(bucket, overall_met):
    if bucket == "easy" and overall_met:
        return int(np.random.choice([4, 5], p=[0.35, 0.65]))
    if bucket == "easy" and not overall_met:
        return int(np.random.choice([2, 3, 4], p=[0.20, 0.55, 0.25]))
    if bucket == "medium" and overall_met:
        return int(np.random.choice([3, 4, 5], p=[0.15, 0.50, 0.35]))
    if bucket == "medium" and not overall_met:
        return int(np.random.choice([1, 2, 3, 4], p=[0.10, 0.28, 0.42, 0.20]))
    if overall_met:
        return int(np.random.choice([3, 4, 5], p=[0.20, 0.45, 0.35]))
    return int(np.random.choice([1, 2, 3], p=[0.28, 0.42, 0.30]))

def gen_feedback_comment(csat, overall_met):
    if csat >= 4 and overall_met:
        return random.choice(POSITIVE_COMMENTS)
    if csat <= 2 or not overall_met:
        return random.choice(NEGATIVE_COMMENTS)
    return random.choice(NEUTRAL_COMMENTS)

def gen_feedback_type(csat):
    if csat <= 2:
        return random.choice(["Support follow-up", "Account review note"])
    return random.choice(["Post-ticket survey", "Support follow-up", "Account review note"])

def main():
    random.seed(SEED)
    np.random.seed(SEED)

    if not Path(INPUT_FILE).exists():
        raise FileNotFoundError(f"Không tìm thấy file input: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE, sheet_name="ticket_raw")
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["priority"] = df["severity"].map(SEVERITY_TO_PRIORITY).fillna(df["priority"])
    df["response_sla_target_min"] = df["priority"].map(lambda p: PRIORITY_TO_TARGET.get(p, {"response": 60})["response"])
    df["resolution_sla_target_min"] = df["priority"].map(lambda p: PRIORITY_TO_TARGET.get(p, {"resolution": 1440})["resolution"])

    buckets = []
    actual_response = []
    actual_resolution = []
    first_response_at = []
    resolved_at = []
    response_met_vals = []
    resolution_met_vals = []
    overall_vals = []
    escalated_vals = []
    reopened_vals = []
    waiting_vals = []
    breach_vals = []
    csat_vals = []
    comment_vals = []
    ftype_vals = []

    for category, severity, priority, created_at, response_target, resolution_target in df[
        ["category", "severity", "priority", "created_at", "response_sla_target_min", "resolution_sla_target_min"]
    ].itertuples(index=False, name=None):
        bucket = choose_ticket_bucket(category, severity, priority)
        resp_min = gen_response_minutes(bucket, priority)
        res_min = max(gen_resolution_minutes(bucket), resp_min + np.random.uniform(1, 15))
        wait_min = gen_waiting_customer_minutes(bucket)
        escalated = gen_escalated(bucket)
        reopened = gen_reopened_count(bucket)
        resp_met = bool(resp_min <= response_target)
        res_met = bool(res_min <= resolution_target)
        overall = "Met" if (resp_met and res_met) else "Breached"
        breach_reason = gen_breach_reason(resp_met, res_met, escalated, wait_min)
        csat = gen_csat(bucket, overall == "Met")
        comment = gen_feedback_comment(csat, overall == "Met")
        ftype = gen_feedback_type(csat)

        buckets.append(bucket)
        actual_response.append(round(resp_min, 2))
        actual_resolution.append(round(res_min, 2))
        first_response_at.append(created_at + pd.to_timedelta(resp_min, unit="m"))
        resolved_at.append(created_at + pd.to_timedelta(res_min, unit="m"))
        response_met_vals.append(resp_met)
        resolution_met_vals.append(res_met)
        overall_vals.append(overall)
        escalated_vals.append(escalated)
        reopened_vals.append(reopened)
        waiting_vals.append(round(wait_min, 2))
        breach_vals.append(breach_reason)
        csat_vals.append(csat)
        comment_vals.append(comment)
        ftype_vals.append(ftype)

    df["ticket_bucket"] = buckets
    df["first_response_at"] = first_response_at
    df["resolved_at"] = resolved_at
    df["actual_response_min"] = actual_response
    df["actual_resolution_min"] = actual_resolution
    df["response_sla_met"] = response_met_vals
    df["resolution_sla_met"] = resolution_met_vals
    df["overall_sla_status"] = overall_vals
    df["escalated"] = escalated_vals
    df["reopened_count"] = reopened_vals
    df["waiting_customer_min"] = waiting_vals
    df["breach_reason"] = breach_vals
    df["csat_score"] = csat_vals
    df["feedback_comment"] = comment_vals
    df["feedback_type"] = ftype_vals
    df["year"] = df["created_at"].dt.year
    df["month"] = df["created_at"].dt.month

    summary_check = pd.DataFrame([
        {
            "metric": "easy_avg_resolution_min",
            "value": round(df.loc[df["ticket_bucket"] == "easy", "actual_resolution_min"].mean(), 2),
        },
        {
            "metric": "medium_avg_resolution_days",
            "value": round(df.loc[df["ticket_bucket"] == "medium", "actual_resolution_min"].mean() / 1440, 2),
        },
        {
            "metric": "hard_feature_avg_resolution_weeks",
            "value": round(df.loc[df["ticket_bucket"] == "hard_feature", "actual_resolution_min"].mean() / 10080, 2),
        },
        {
            "metric": "overall_sla_met_pct",
            "value": round((df["overall_sla_status"] == "Met").mean() * 100, 2),
        },
        {
            "metric": "total_tickets",
            "value": len(df),
        },
    ])

    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="ticket_raw", index=False)
        summary_check.to_excel(writer, sheet_name="summary_check", index=False)

    print(f"Done. Output: {OUTPUT_FILE}")
    print(summary_check.to_string(index=False))

if __name__ == "__main__":
    main()
