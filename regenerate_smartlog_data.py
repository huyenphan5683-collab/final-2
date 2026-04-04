import os
import random
from pathlib import Path
import numpy as np
import pandas as pd

INPUT_FILE = os.getenv("INPUT_FILE", "smartlog_service_master_2023_2025.xlsx")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "smartlog_service_master_2023_2025_regenerated.xlsx")
SEED = int(os.getenv("SEED", "42"))

# Mục tiêu overall SLA theo năm: dễ phân tích, tăng dần
YEAR_OVERALL_SLA_TARGET = {
    2023: 0.56,
    2024: 0.63,
    2025: 0.69,
}

# Tỷ lệ đạt SLA theo bucket và năm
# Logic: easy cao nhất, medium trung bình, hard thấp hơn nhưng vẫn cải thiện theo năm
BUCKET_YEAR_SLA_TARGET = {
    "easy": {
        2023: 0.72,
        2024: 0.79,
        2025: 0.85,
    },
    "medium": {
        2023: 0.52,
        2024: 0.60,
        2025: 0.67,
    },
    "hard_feature": {
        2023: 0.31,
        2024: 0.39,
        2025: 0.47,
    }
}

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
    if category in EASY_CATEGORIES:
        return "easy"
    if category in MEDIUM_CATEGORIES:
        if severity in {"Critical", "High"} and random.random() < 0.18:
            return "hard_feature"
        return "medium"
    if priority == "P4" or severity == "Low":
        return "easy"
    if severity in {"Critical", "High"}:
        return "medium"
    return "medium"

def get_sla_target(bucket, year):
    return BUCKET_YEAR_SLA_TARGET.get(bucket, {}).get(year, YEAR_OVERALL_SLA_TARGET.get(year, 0.60))

def gen_minutes_near_target(target, met=True, mode="resolution", bucket="medium"):
    # Sinh thời gian quanh ngưỡng target để data nhìn thật hơn
    if mode == "response":
        if met:
            if bucket == "easy":
                return round(float(np.random.uniform(max(1, target * 0.10), max(2, target * 0.65))), 2)
            if bucket == "medium":
                return round(float(np.random.uniform(max(1, target * 0.25), max(3, target * 0.90))), 2)
            return round(float(np.random.uniform(max(1, target * 0.35), max(4, target * 0.98))), 2)
        else:
            if bucket == "easy":
                return round(float(np.random.uniform(target * 1.02, target * 1.80)), 2)
            if bucket == "medium":
                return round(float(np.random.uniform(target * 1.05, target * 2.60)), 2)
            return round(float(np.random.uniform(target * 1.10, target * 3.20)), 2)

    # resolution
    if met:
        if bucket == "easy":
            # easy vẫn nhanh, thường < 30 phút, nhưng vẫn tương thích SLA
            upper = min(target * 0.50, 30)
            return round(float(np.random.triangular(5, 15, max(16, upper))), 2)
        if bucket == "medium":
            # medium nhìn thực tế hơn để còn đạt SLA đáng kể
            low = min(target * 0.25, target - 5)
            modev = min(target * 0.65, target - 3)
            high = min(target * 0.95, target - 1)
            return round(float(np.random.triangular(max(30, low), max(60, modev), max(90, high))), 2)
        # hard_feature met: vẫn sát ngưỡng, không quá xa
        low = max(120, target * 0.45)
        modev = max(180, target * 0.78)
        high = max(200, target * 0.98)
        return round(float(np.random.triangular(low, modev, high)), 2)
    else:
        if bucket == "easy":
            return round(float(np.random.uniform(max(31, target * 1.03), max(45, target * 1.80))), 2)
        if bucket == "medium":
            return round(float(np.random.uniform(target * 1.05, target * 2.40)), 2)
        # hard_feature fail: 3–5 tuần cho phần khó / yêu cầu tính năng
        return round(float(np.random.uniform(30240, 50400)), 2)

def gen_waiting_customer_minutes(bucket, met_overall):
    if bucket == "easy":
        return round(float(np.random.uniform(0, 15 if met_overall else 45)), 2)
    if bucket == "medium":
        return round(float(np.random.uniform(0, 180 if met_overall else 960)), 2)
    return round(float(np.random.uniform(30, 720 if met_overall else 4320)), 2)

def gen_reopened_count(bucket, met_overall):
    if bucket == "easy":
        return int(np.random.choice([0, 1], p=[0.95, 0.05] if met_overall else [0.80, 0.20]))
    if bucket == "medium":
        return int(np.random.choice([0, 1, 2, 3], p=[0.72, 0.18, 0.07, 0.03] if met_overall else [0.45, 0.28, 0.17, 0.10]))
    return int(np.random.choice([0, 1, 2, 3, 4], p=[0.40, 0.25, 0.18, 0.10, 0.07] if met_overall else [0.18, 0.22, 0.24, 0.20, 0.16]))

def gen_escalated(bucket, met_overall):
    if bucket == "easy":
        return bool(np.random.choice([False, True], p=[0.95, 0.05] if met_overall else [0.82, 0.18]))
    if bucket == "medium":
        return bool(np.random.choice([False, True], p=[0.78, 0.22] if met_overall else [0.54, 0.46]))
    return bool(np.random.choice([False, True], p=[0.52, 0.48] if met_overall else [0.28, 0.72]))

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

def gen_csat(bucket, overall_met, year):
    # cải thiện nhẹ theo năm để dễ phân tích
    uplift = {2023: 0.00, 2024: 0.10, 2025: 0.20}.get(year, 0.0)

    if overall_met:
        if bucket == "easy":
            probs = np.array([0.00, 0.04, 0.16, 0.42, 0.38 + uplift])
        elif bucket == "medium":
            probs = np.array([0.02, 0.08, 0.20, 0.43, 0.27 + uplift])
        else:
            probs = np.array([0.04, 0.12, 0.26, 0.36, 0.22 + uplift])
    else:
        if bucket == "easy":
            probs = np.array([0.05, 0.18, 0.43, 0.25, 0.09])
        elif bucket == "medium":
            probs = np.array([0.10, 0.28, 0.38, 0.18, 0.06])
        else:
            probs = np.array([0.18, 0.34, 0.30, 0.13, 0.05])

    probs = probs / probs.sum()
    return int(np.random.choice([1, 2, 3, 4, 5], p=probs))

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

def assign_target_outcome(df):
    # Gán outcome theo bucket + year target để SLA tăng dần theo năm
    outcome = []
    for bucket, year in df[["ticket_bucket", "year"]].itertuples(index=False, name=None):
        p = get_sla_target(bucket, year)
        outcome.append(bool(np.random.random() < p))
    return outcome

def main():
    random.seed(SEED)
    np.random.seed(SEED)

    if not Path(INPUT_FILE).exists():
        raise FileNotFoundError(f"Không tìm thấy file input: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE, sheet_name="ticket_raw")
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["year"] = df["created_at"].dt.year
    df["month"] = df["created_at"].dt.month

    if "severity" not in df.columns:
        raise ValueError("File ticket_raw thiếu cột 'severity'.")
    if "priority" not in df.columns:
        df["priority"] = df["severity"].map(SEVERITY_TO_PRIORITY)

    df["priority"] = df["priority"].fillna(df["severity"].map(SEVERITY_TO_PRIORITY))
    df["response_sla_target_min"] = df["priority"].map(lambda p: PRIORITY_TO_TARGET.get(p, {"response": 60})["response"])
    df["resolution_sla_target_min"] = df["priority"].map(lambda p: PRIORITY_TO_TARGET.get(p, {"resolution": 1440})["resolution"])

    df["ticket_bucket"] = [
        choose_ticket_bucket(category, severity, priority)
        for category, severity, priority in df[["category", "severity", "priority"]].itertuples(index=False, name=None)
    ]

    overall_target_met = assign_target_outcome(df)

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

    for row, want_overall_met in zip(df.itertuples(index=False), overall_target_met):
        bucket = row.ticket_bucket
        year = row.year
        response_target = row.response_sla_target_min
        resolution_target = row.resolution_sla_target_min
        created_at = row.created_at

        # Để data tự nhiên hơn: 1 phần fail chỉ fail response, 1 phần fail resolution, phần lớn fail resolution
        if want_overall_met:
            response_met = True
            resolution_met = True
        else:
            fail_pattern = random.choices(
                ["resolution_only", "response_only", "both"],
                weights=[0.62, 0.18, 0.20],
                k=1
            )[0]
            if fail_pattern == "resolution_only":
                response_met = True
                resolution_met = False
            elif fail_pattern == "response_only":
                response_met = False
                resolution_met = True
            else:
                response_met = False
                resolution_met = False

        resp_min = gen_minutes_near_target(response_target, met=response_met, mode="response", bucket=bucket)
        res_min = gen_minutes_near_target(resolution_target, met=resolution_met, mode="resolution", bucket=bucket)

        if res_min <= resp_min:
            res_min = round(resp_min + np.random.uniform(5, 60), 2)

        overall_met = response_met and resolution_met
        wait_min = gen_waiting_customer_minutes(bucket, overall_met)
        escalated = gen_escalated(bucket, overall_met)
        reopened = gen_reopened_count(bucket, overall_met)
        breach_reason = gen_breach_reason(response_met, resolution_met, escalated, wait_min)
        csat = gen_csat(bucket, overall_met, year)
        comment = gen_feedback_comment(csat, overall_met)
        ftype = gen_feedback_type(csat)

        actual_response.append(resp_min)
        actual_resolution.append(res_min)
        first_response_at.append(created_at + pd.to_timedelta(resp_min, unit="m"))
        resolved_at.append(created_at + pd.to_timedelta(res_min, unit="m"))
        response_met_vals.append(response_met)
        resolution_met_vals.append(resolution_met)
        overall_vals.append("Met" if overall_met else "Breached")
        escalated_vals.append(escalated)
        reopened_vals.append(reopened)
        waiting_vals.append(wait_min)
        breach_vals.append(breach_reason)
        csat_vals.append(csat)
        comment_vals.append(comment)
        ftype_vals.append(ftype)

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
            "metric": "overall_sla_2023_pct",
            "value": round(((df["year"] == 2023) & (df["overall_sla_status"] == "Met")).sum() / max((df["year"] == 2023).sum(), 1) * 100, 2),
        },
        {
            "metric": "overall_sla_2024_pct",
            "value": round(((df["year"] == 2024) & (df["overall_sla_status"] == "Met")).sum() / max((df["year"] == 2024).sum(), 1) * 100, 2),
        },
        {
            "metric": "overall_sla_2025_pct",
            "value": round(((df["year"] == 2025) & (df["overall_sla_status"] == "Met")).sum() / max((df["year"] == 2025).sum(), 1) * 100, 2),
        },
        {
            "metric": "overall_sla_all_pct",
            "value": round((df["overall_sla_status"] == "Met").mean() * 100, 2),
        },
        {
            "metric": "total_tickets",
            "value": len(df),
        },
    ])

    summary_by_year = (
        df.groupby("year")
        .agg(
            total_tickets=("overall_sla_status", "size"),
            response_sla_met_pct=("response_sla_met", lambda s: round(s.mean() * 100, 2)),
            resolution_sla_met_pct=("resolution_sla_met", lambda s: round(s.mean() * 100, 2)),
            overall_sla_met_pct=("overall_sla_status", lambda s: round((s.eq("Met")).mean() * 100, 2)),
            avg_response_min=("actual_response_min", lambda s: round(s.mean(), 2)),
            avg_resolution_hours=("actual_resolution_min", lambda s: round(s.mean() / 60, 2)),
            avg_csat=("csat_score", lambda s: round(s.mean(), 2)),
        )
        .reset_index()
    )

    summary_by_bucket = (
        df.groupby(["year", "ticket_bucket"])
        .agg(
            total_tickets=("overall_sla_status", "size"),
            overall_sla_met_pct=("overall_sla_status", lambda s: round((s.eq("Met")).mean() * 100, 2)),
            avg_resolution_hours=("actual_resolution_min", lambda s: round(s.mean() / 60, 2)),
            escalated_pct=("escalated", lambda s: round(s.mean() * 100, 2)),
            avg_csat=("csat_score", lambda s: round(s.mean(), 2)),
        )
        .reset_index()
    )

    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="ticket_raw", index=False)
        summary_check.to_excel(writer, sheet_name="summary_check", index=False)
        summary_by_year.to_excel(writer, sheet_name="summary_by_year", index=False)
        summary_by_bucket.to_excel(writer, sheet_name="summary_by_bucket", index=False)

    print(f"Done. Output: {OUTPUT_FILE}")
    print(summary_check.to_string(index=False))

if __name__ == "__main__":
    main()
