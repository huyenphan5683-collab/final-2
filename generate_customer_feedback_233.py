import os
import random
from pathlib import Path
import numpy as np
import pandas as pd

INPUT_FILE = os.getenv("INPUT_FILE", "smartlog_service_master_2023_2025.xlsx")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "smartlog_service_master_2023_2025_feedback.xlsx")
SEED = int(os.getenv("SEED", "42"))

THEMES = [
    "response speed",
    "communication clarity",
    "issue resolution",
    "follow-up",
    "system stability/support quality",
]

POSITIVE_COMMENTS = {
    "response speed": [
        "Support responded quickly and helped us continue operations.",
        "The response was timely and reduced disruption to our workflow.",
        "The team acknowledged the issue fast and gave immediate support.",
    ],
    "communication clarity": [
        "The explanation was clear and easy for the operations team to follow.",
        "Updates were understandable and helped us track the issue.",
        "The support team communicated clearly throughout the process.",
    ],
    "issue resolution": [
        "The issue was resolved effectively and did not recur afterwards.",
        "The team fixed the problem properly and the system worked again.",
        "Resolution was effective and matched our operational needs.",
    ],
    "follow-up": [
        "Follow-up was proactive and the team kept us informed.",
        "The case was followed through properly until closure.",
        "Support checked back after resolution, which improved the experience.",
    ],
    "system stability/support quality": [
        "System performance was stable after support intervention.",
        "The support quality was good and system behavior improved afterwards.",
        "The team handled the system issue professionally and effectively.",
    ],
}

NEGATIVE_COMMENTS = {
    "response speed": [
        "Response was slower than expected and affected operations.",
        "We needed urgent support but the first response was delayed.",
        "The waiting time for initial support was too long for a live operation.",
    ],
    "communication clarity": [
        "The explanation was unclear and the user still did not understand the issue.",
        "Updates were too technical and not easy for end users to follow.",
        "Communication lacked clarity and made the process harder to understand.",
    ],
    "issue resolution": [
        "The issue was closed but not fully resolved and later reappeared.",
        "Resolution did not address the root cause and the problem persisted.",
        "The problem affected operations longer than expected because the fix was incomplete.",
    ],
    "follow-up": [
        "The team did not follow up consistently after the initial response.",
        "We had to ask several times for progress updates.",
        "Follow-up was limited and the customer had to chase the case repeatedly.",
    ],
    "system stability/support quality": [
        "System instability continued and affected service quality.",
        "The integration issue disrupted operations and took too long to stabilize.",
        "Support quality was reduced by recurring system or sync problems.",
    ],
}

def clean_bool_series(s):
    if s.dtype == bool:
        return s.fillna(False)
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])

def detect_primary_theme(row):
    breach_reason = str(row.get("breach_reason", "")).lower()
    category = str(row.get("category", "")).lower()
    comment = str(row.get("feedback_comment", "")).lower()
    reopened = row.get("reopened_count", 0)
    escalated = bool(row.get("escalated", False))

    if "priorit" in breach_reason or "response" in breach_reason:
        return "response speed"
    if "waiting for customer" in breach_reason or "follow" in comment:
        return "follow-up"
    if reopened and reopened > 0:
        return "issue resolution"
    if "environment" in breach_reason or "product team" in breach_reason or "root cause" in breach_reason:
        return "system stability/support quality"
    if category in ["user access", "configuration", "master data", "report/bi"]:
        return "communication clarity"
    if escalated:
        return "issue resolution"
    return "system stability/support quality"

def detect_secondary_theme(primary, row):
    options = [t for t in THEMES if t != primary]
    breach_reason = str(row.get("breach_reason", "")).lower()
    if primary != "follow-up" and "waiting for customer" in breach_reason:
        return "follow-up"
    if primary != "communication clarity" and str(row.get("category","")).lower() in ["user access","configuration","master data","report/bi"]:
        return "communication clarity"
    if primary != "issue resolution" and row.get("reopened_count", 0) > 0:
        return "issue resolution"
    return random.choice(options)

def infer_sentiment_and_score(row):
    overall = str(row.get("overall_sla_status", "Breached"))
    resp_met = bool(row.get("response_sla_met", False))
    res_met = bool(row.get("resolution_sla_met", False))
    escalated = bool(row.get("escalated", False))
    reopened = int(row.get("reopened_count", 0) or 0)
    csat = row.get("csat_score", np.nan)

    if pd.notna(csat):
        csat = int(csat)
        if csat >= 4:
            sentiment = "Positive"
        elif csat == 3:
            sentiment = "Neutral"
        else:
            sentiment = "Negative"
        return sentiment, csat

    if overall == "Met" and resp_met and res_met and not escalated and reopened == 0:
        score = int(np.random.choice([4, 5], p=[0.35, 0.65]))
    elif overall == "Met":
        score = int(np.random.choice([3, 4, 5], p=[0.25, 0.50, 0.25]))
    elif reopened > 0 or escalated:
        score = int(np.random.choice([1, 2, 3], p=[0.25, 0.45, 0.30]))
    else:
        score = int(np.random.choice([2, 3, 4], p=[0.30, 0.45, 0.25]))

    sentiment = "Positive" if score >= 4 else ("Neutral" if score == 3 else "Negative")
    return sentiment, score

def choose_feedback_source(score, primary_theme):
    if primary_theme in ["response speed", "follow-up"]:
        return random.choice(["chat", "email", "survey"])
    if score <= 2:
        return random.choice(["complaint record", "email", "account interview"])
    return random.choice(["survey", "email", "chat", "account interview"])

def build_comment(sentiment, theme):
    if sentiment == "Positive":
        return random.choice(POSITIVE_COMMENTS[theme])
    if sentiment == "Negative":
        return random.choice(NEGATIVE_COMMENTS[theme])
    templates = {
        "response speed": "Response time was acceptable, although there is still room for faster support in peak periods.",
        "communication clarity": "Communication was adequate overall, but some explanations could be clearer for end users.",
        "issue resolution": "The issue was handled at an acceptable level, although the resolution process could be more consistent.",
        "follow-up": "Follow-up was acceptable overall, but progress updates could be more proactive.",
        "system stability/support quality": "Support quality was acceptable, although system stability should be improved further.",
    }
    return templates[theme]

def main():
    random.seed(SEED)
    np.random.seed(SEED)

    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    xls = pd.ExcelFile(input_path)
    sheets = {name: pd.read_excel(input_path, sheet_name=name) for name in xls.sheet_names}

    if "ticket_raw" not in sheets:
        raise ValueError("Workbook must contain sheet 'ticket_raw'.")

    df = sheets["ticket_raw"].copy()

    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        if "year" not in df.columns:
            df["year"] = df["created_at"].dt.year
        if "month" not in df.columns:
            df["month"] = df["created_at"].dt.month
        if "quarter" not in df.columns:
            df["quarter"] = df["created_at"].dt.to_period("Q").astype(str)
    else:
        raise ValueError("ticket_raw thiếu cột created_at.")

    for col in ["response_sla_met", "resolution_sla_met", "escalated"]:
        if col in df.columns:
            df[col] = clean_bool_series(df[col])
        else:
            df[col] = False

    if "reopened_count" not in df.columns:
        df["reopened_count"] = 0
    if "overall_sla_status" not in df.columns:
        df["overall_sla_status"] = np.where(df["response_sla_met"] & df["resolution_sla_met"], "Met", "Breached")
    if "severity" not in df.columns:
        df["severity"] = "Medium"
    if "category" not in df.columns:
        df["category"] = "System Bug"
    if "breach_reason" not in df.columns:
        df["breach_reason"] = np.where(df["overall_sla_status"].eq("Met"), "No breach", "Internal delay")

    sample_prob = np.where(df["overall_sla_status"].eq("Breached"), 0.42, 0.26)
    sample_prob = np.where(df["escalated"], sample_prob + 0.08, sample_prob)
    sample_prob = np.where(df["reopened_count"] > 0, sample_prob + 0.06, sample_prob)
    sample_prob = np.clip(sample_prob, 0.15, 0.72)

    df["feedback_received"] = np.random.random(len(df)) < sample_prob
    feedback = df.loc[df["feedback_received"]].copy()

    sentiments = []
    scores = []
    primary_themes = []
    secondary_themes = []
    comments = []
    sources = []
    labels = []
    complaint_flag = []

    for _, row in feedback.iterrows():
        sentiment, score = infer_sentiment_and_score(row)
        primary = detect_primary_theme(row)
        secondary = detect_secondary_theme(primary, row)
        source = choose_feedback_source(score, primary)
        comment = build_comment(sentiment, primary)

        sentiments.append(sentiment)
        scores.append(score)
        primary_themes.append(primary)
        secondary_themes.append(secondary)
        comments.append(comment)
        sources.append(source)
        labels.append("Satisfied" if score >= 4 else ("Neutral" if score == 3 else "Dissatisfied"))
        complaint_flag.append(source == "complaint record" or score <= 2)

    feedback["feedback_sentiment"] = sentiments
    feedback["satisfaction_score"] = scores
    feedback["satisfaction_label"] = labels
    feedback["feedback_source"] = sources
    feedback["feedback_comment_generated"] = comments
    feedback["theme_primary"] = primary_themes
    feedback["theme_secondary"] = secondary_themes
    feedback["complaint_flag"] = complaint_flag

    feedback_raw = feedback[[
        c for c in [
            "ticket_id", "created_at", "year", "month", "quarter", "customer_name", "severity", "priority",
            "category", "overall_sla_status", "response_sla_met", "resolution_sla_met", "escalated",
            "reopened_count", "csat_score", "feedback_source", "feedback_sentiment", "satisfaction_score",
            "satisfaction_label", "theme_primary", "theme_secondary", "feedback_comment_generated",
            "breach_reason", "complaint_flag"
        ] if c in feedback.columns
    ]].copy()

    if "ticket_id" not in feedback_raw.columns:
        feedback_raw.insert(0, "ticket_id", range(1, len(feedback_raw) + 1))

    summary = pd.DataFrame([{
        "total_tickets": len(df),
        "tickets_with_feedback": len(feedback_raw),
        "feedback_rate_pct": round(len(feedback_raw) / len(df) * 100, 2),
        "avg_satisfaction_score": round(feedback_raw["satisfaction_score"].mean(), 2),
        "satisfied_pct": round((feedback_raw["satisfaction_score"] >= 4).mean() * 100, 2),
        "neutral_pct": round((feedback_raw["satisfaction_score"] == 3).mean() * 100, 2),
        "dissatisfied_pct": round((feedback_raw["satisfaction_score"] <= 2).mean() * 100, 2),
        "positive_feedback_pct": round((feedback_raw["feedback_sentiment"] == "Positive").mean() * 100, 2),
        "negative_feedback_pct": round((feedback_raw["feedback_sentiment"] == "Negative").mean() * 100, 2),
        "complaint_record_count": int(feedback_raw["complaint_flag"].sum()),
    }])

    by_year = (
        feedback_raw.groupby("year")
        .agg(
            feedback_count=("ticket_id", "count"),
            avg_satisfaction_score=("satisfaction_score", lambda s: round(s.mean(), 2)),
            satisfied_pct=("satisfaction_score", lambda s: round((s >= 4).mean() * 100, 2)),
            dissatisfied_pct=("satisfaction_score", lambda s: round((s <= 2).mean() * 100, 2)),
            positive_pct=("feedback_sentiment", lambda s: round((s == "Positive").mean() * 100, 2)),
            negative_pct=("feedback_sentiment", lambda s: round((s == "Negative").mean() * 100, 2)),
        )
        .reset_index()
    )

    by_theme = (
        feedback_raw.groupby("theme_primary")
        .agg(
            feedback_count=("ticket_id", "count"),
            avg_satisfaction_score=("satisfaction_score", lambda s: round(s.mean(), 2)),
            negative_pct=("feedback_sentiment", lambda s: round((s == "Negative").mean() * 100, 2)),
        )
        .reset_index()
        .sort_values("feedback_count", ascending=False)
    )

    theme_by_year = (
        feedback_raw.groupby(["year", "theme_primary"])
        .size()
        .reset_index(name="feedback_count")
        .sort_values(["year", "feedback_count"], ascending=[True, False])
    )

    by_source = (
        feedback_raw.groupby("feedback_source")
        .agg(
            feedback_count=("ticket_id", "count"),
            avg_satisfaction_score=("satisfaction_score", lambda s: round(s.mean(), 2)),
        )
        .reset_index()
        .sort_values("feedback_count", ascending=False)
    )

    by_severity = (
        feedback_raw.groupby("severity")
        .agg(
            feedback_count=("ticket_id", "count"),
            avg_satisfaction_score=("satisfaction_score", lambda s: round(s.mean(), 2)),
            dissatisfied_pct=("satisfaction_score", lambda s: round((s <= 2).mean() * 100, 2)),
        )
        .reset_index()
    )

    complaint_records = feedback_raw.loc[feedback_raw["complaint_flag"]].copy()
    complaint_records = complaint_records.sort_values(["year", "satisfaction_score"]).head(5000)

    feedback_topics = (
        pd.concat([
            feedback_raw["theme_primary"].rename("theme"),
            feedback_raw["theme_secondary"].rename("theme")
        ])
        .value_counts()
        .reset_index()
    )
    feedback_topics.columns = ["theme", "mentions"]

    sheets["feedback_summary"] = summary
    sheets["feedback_by_year"] = by_year
    sheets["feedback_by_theme"] = by_theme
    sheets["feedback_theme_by_year"] = theme_by_year
    sheets["feedback_by_source"] = by_source
    sheets["feedback_by_severity"] = by_severity
    sheets["feedback_topics"] = feedback_topics
    sheets["customer_feedback_raw"] = feedback_raw
    sheets["complaint_records"] = complaint_records

    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        for name, sdf in sheets.items():
            sdf.to_excel(writer, sheet_name=name[:31], index=False)

    print(f"Done. Output written to {OUTPUT_FILE}")
    print(summary.to_string(index=False))

if __name__ == "__main__":
    main()
