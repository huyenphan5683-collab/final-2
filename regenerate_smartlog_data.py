import os
import random
from pathlib import Path
import numpy as np
import pandas as pd

INPUT_FILE = os.getenv('INPUT_FILE', 'smartlog_service_master_2023_2025.xlsx')
OUTPUT_FILE = os.getenv('OUTPUT_FILE', 'smartlog_service_master_2023_2025_regenerated.xlsx')
SEED = int(os.getenv('SEED', '42'))

# Mức SLA mục tiêu: đủ tốt để thấy có cải thiện, nhưng vẫn còn gap rõ để viết khóa luận
YEAR_OVERALL_SLA_TARGET = {
    2023: 0.54,
    2024: 0.60,
    2025: 0.66,
}

# Tỷ lệ đạt overall SLA theo nhóm ticket và năm
BUCKET_YEAR_SLA_TARGET = {
    'easy': {
        2023: 0.68,
        2024: 0.74,
        2025: 0.80,
    },
    'medium': {
        2023: 0.50,
        2024: 0.57,
        2025: 0.63,
    },
    'hard_feature': {
        2023: 0.26,
        2024: 0.33,
        2025: 0.40,
    },
}

EASY_CATEGORIES = {'User Access', 'Master Data', 'Configuration', 'Report/BI'}
MEDIUM_CATEGORIES = {'System Bug', 'Integration Issue', 'Performance', 'Workflow', 'Carrier/3PL Sync'}
HARD_CATEGORIES = {'Feature Request', 'Enhancement', 'Customization', 'New Requirement'}

PRIORITY_TO_TARGET = {
    'P1': {'response': 15, 'resolution': 240},
    'P2': {'response': 30, 'resolution': 480},
    'P3': {'response': 60, 'resolution': 1440},
    'P4': {'response': 120, 'resolution': 2880},
}
SEVERITY_TO_PRIORITY = {'Critical': 'P1', 'High': 'P2', 'Medium': 'P3', 'Low': 'P4'}

NEGATIVE_COMMENTS = [
    'The issue remained unresolved longer than expected and required repeated follow-up.',
    'Support response was delayed and affected operations more than expected.',
    'The team had to coordinate across functions, which prolonged the resolution time.',
    'The issue was not handled as quickly as expected for business operations.',
    'The customer needed urgent support but the case took longer than expected to close.'
]
NEUTRAL_COMMENTS = [
    'Support met expectations overall, with slight room for improvement.',
    'The issue was resolved with acceptable handling time.',
    'The case was handled adequately and communication was clear.',
    'The support process was generally satisfactory.',
    'The service experience was acceptable for this type of issue.'
]
POSITIVE_COMMENTS = [
    'The issue was resolved quickly and the support team communicated clearly.',
    'Support was timely and the problem was fixed efficiently.',
    'The team responded fast and handled the case professionally.',
    'The service experience was smooth and met expectations well.',
    'The issue was closed promptly with effective support.'
]


def choose_ticket_bucket(category, severity, priority):
    category = str(category).strip()
    severity = str(severity).strip()
    priority = str(priority).strip()

    if category in HARD_CATEGORIES:
        return 'hard_feature'
    if category in EASY_CATEGORIES:
        return 'easy'
    if category in MEDIUM_CATEGORIES:
        if severity in {'Critical', 'High'} and random.random() < 0.16:
            return 'hard_feature'
        return 'medium'
    if priority == 'P4' or severity == 'Low':
        return 'easy'
    if severity in {'Critical', 'High'}:
        return 'medium'
    return 'medium'


def get_sla_target(bucket, year):
    return BUCKET_YEAR_SLA_TARGET.get(bucket, {}).get(year, YEAR_OVERALL_SLA_TARGET.get(year, 0.60))


def gen_response_minutes(target, met=True, bucket='medium'):
    if met:
        if bucket == 'easy':
            return round(float(np.random.uniform(max(1, target * 0.10), max(2, target * 0.60))), 2)
        if bucket == 'medium':
            return round(float(np.random.uniform(max(1, target * 0.20), max(3, target * 0.88))), 2)
        return round(float(np.random.uniform(max(1, target * 0.30), max(4, target * 0.96))), 2)
    else:
        if bucket == 'easy':
            return round(float(np.random.uniform(target * 1.02, target * 1.70)), 2)
        if bucket == 'medium':
            return round(float(np.random.uniform(target * 1.05, target * 2.40)), 2)
        return round(float(np.random.uniform(target * 1.08, target * 3.00)), 2)


def gen_resolution_minutes(target, met=True, bucket='medium'):
    # easy: trung bình dưới 30 phút
    if met:
        if bucket == 'easy':
            upper = min(max(22, target * 0.45), 30)
            return round(float(np.random.triangular(5, 14, upper)), 2)
        if bucket == 'medium':
            # medium đạt SLA: vẫn nằm dưới target để overall nhìn hợp lý
            low = max(60, target * 0.20)
            modev = max(180, target * 0.55)
            high = max(240, target * 0.92)
            return round(float(np.random.triangular(low, modev, high)), 2)
        # hard_feature đạt SLA: sát ngưỡng, thường tốn thời gian hơn
        low = max(180, target * 0.45)
        modev = max(240, target * 0.78)
        high = max(300, target * 0.98)
        return round(float(np.random.triangular(low, modev, high)), 2)
    else:
        if bucket == 'easy':
            return round(float(np.random.uniform(max(31, target * 1.02), max(45, target * 1.70))), 2)
        if bucket == 'medium':
            # medium fail: 2-7 ngày
            return round(float(np.random.uniform(2880, 10080)), 2)
        # hard/feature fail: 3-5 tuần
        return round(float(np.random.uniform(30240, 50400)), 2)


def gen_waiting_customer_minutes(bucket, overall_met):
    if bucket == 'easy':
        return round(float(np.random.uniform(0, 10 if overall_met else 40)), 2)
    if bucket == 'medium':
        return round(float(np.random.uniform(0, 180 if overall_met else 960)), 2)
    return round(float(np.random.uniform(20, 720 if overall_met else 4320)), 2)


def gen_reopened_count(bucket, overall_met):
    if bucket == 'easy':
        return int(np.random.choice([0, 1], p=[0.95, 0.05] if overall_met else [0.82, 0.18]))
    if bucket == 'medium':
        return int(np.random.choice([0, 1, 2, 3], p=[0.70, 0.19, 0.08, 0.03] if overall_met else [0.42, 0.28, 0.18, 0.12]))
    return int(np.random.choice([0, 1, 2, 3, 4], p=[0.38, 0.26, 0.18, 0.11, 0.07] if overall_met else [0.15, 0.22, 0.25, 0.21, 0.17]))


def gen_escalated(bucket, overall_met):
    if bucket == 'easy':
        return bool(np.random.choice([False, True], p=[0.95, 0.05] if overall_met else [0.83, 0.17]))
    if bucket == 'medium':
        return bool(np.random.choice([False, True], p=[0.77, 0.23] if overall_met else [0.52, 0.48]))
    return bool(np.random.choice([False, True], p=[0.50, 0.50] if overall_met else [0.26, 0.74]))


def gen_breach_reason(response_met, resolution_met, escalated, waiting_customer_min):
    if response_met and resolution_met:
        return 'No breach'
    reasons, weights = [], []
    if waiting_customer_min > 120:
        reasons += ['Waiting for customer']
        weights += [4]
    if escalated:
        reasons += ['Dependency on product team', 'Complex root cause analysis', 'Internal delay']
        weights += [3, 4, 2]
    else:
        reasons += ['Internal delay', 'Incorrect prioritization', 'Environment/data issue']
        weights += [3, 2, 3]
    if not response_met:
        reasons += ['Incorrect prioritization', 'Internal delay']
        weights += [3, 2]
    if not resolution_met:
        reasons += ['Complex root cause analysis', 'Environment/data issue', 'Dependency on product team']
        weights += [4, 3, 3]
    return random.choices(reasons, weights=weights, k=1)[0]


def gen_csat(bucket, overall_met, year):
    uplift = {2023: 0.00, 2024: 0.08, 2025: 0.16}.get(year, 0.0)
    if overall_met:
        if bucket == 'easy':
            probs = np.array([0.00, 0.05, 0.18, 0.43, 0.34 + uplift])
        elif bucket == 'medium':
            probs = np.array([0.03, 0.10, 0.24, 0.40, 0.23 + uplift])
        else:
            probs = np.array([0.05, 0.14, 0.28, 0.33, 0.20 + uplift])
    else:
        if bucket == 'easy':
            probs = np.array([0.06, 0.20, 0.42, 0.24, 0.08])
        elif bucket == 'medium':
            probs = np.array([0.12, 0.30, 0.36, 0.17, 0.05])
        else:
            probs = np.array([0.20, 0.34, 0.28, 0.13, 0.05])
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
        return random.choice(['Support follow-up', 'Account review note'])
    return random.choice(['Post-ticket survey', 'Support follow-up', 'Account review note'])


def assign_target_outcome(df):
    outcome = []
    for bucket, year in df[['ticket_bucket', 'year']].itertuples(index=False, name=None):
        p = get_sla_target(bucket, year)
        outcome.append(bool(np.random.random() < p))
    return outcome


def main():
    random.seed(SEED)
    np.random.seed(SEED)

    if not Path(INPUT_FILE).exists():
        raise FileNotFoundError(f'Không tìm thấy file input: {INPUT_FILE}')

    df = pd.read_excel(INPUT_FILE, sheet_name='ticket_raw')
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['year'] = df['created_at'].dt.year
    df['month'] = df['created_at'].dt.month

    if 'severity' not in df.columns:
        raise ValueError("File ticket_raw thiếu cột 'severity'.")
    if 'priority' not in df.columns:
        df['priority'] = df['severity'].map(SEVERITY_TO_PRIORITY)

    df['priority'] = df['priority'].fillna(df['severity'].map(SEVERITY_TO_PRIORITY))
    df['response_sla_target_min'] = df['priority'].map(lambda p: PRIORITY_TO_TARGET.get(p, {'response': 60})['response'])
    df['resolution_sla_target_min'] = df['priority'].map(lambda p: PRIORITY_TO_TARGET.get(p, {'resolution': 1440})['resolution'])

    df['ticket_bucket'] = [
        choose_ticket_bucket(category, severity, priority)
        for category, severity, priority in df[['category', 'severity', 'priority']].itertuples(index=False, name=None)
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

        if want_overall_met:
            response_met = True
            resolution_met = True
        else:
            fail_pattern = random.choices(
                ['resolution_only', 'response_only', 'both'],
                weights=[0.66, 0.14, 0.20],
                k=1
            )[0]
            if fail_pattern == 'resolution_only':
                response_met = True
                resolution_met = False
            elif fail_pattern == 'response_only':
                response_met = False
                resolution_met = True
            else:
                response_met = False
                resolution_met = False

        resp_min = gen_response_minutes(response_target, met=response_met, bucket=bucket)
        res_min = gen_resolution_minutes(resolution_target, met=resolution_met, bucket=bucket)

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
        first_response_at.append(created_at + pd.to_timedelta(resp_min, unit='m'))
        resolved_at.append(created_at + pd.to_timedelta(res_min, unit='m'))
        response_met_vals.append(response_met)
        resolution_met_vals.append(resolution_met)
        overall_vals.append('Met' if overall_met else 'Breached')
        escalated_vals.append(escalated)
        reopened_vals.append(reopened)
        waiting_vals.append(wait_min)
        breach_vals.append(breach_reason)
        csat_vals.append(csat)
        comment_vals.append(comment)
        ftype_vals.append(ftype)

    df['first_response_at'] = first_response_at
    df['resolved_at'] = resolved_at
    df['actual_response_min'] = actual_response
    df['actual_resolution_min'] = actual_resolution
    df['response_sla_met'] = response_met_vals
    df['resolution_sla_met'] = resolution_met_vals
    df['overall_sla_status'] = overall_vals
    df['escalated'] = escalated_vals
    df['reopened_count'] = reopened_vals
    df['waiting_customer_min'] = waiting_vals
    df['breach_reason'] = breach_vals
    df['csat_score'] = csat_vals
    df['feedback_comment'] = comment_vals
    df['feedback_type'] = ftype_vals

    summary_check = pd.DataFrame([
        {'metric': 'easy_avg_resolution_min', 'value': round(df.loc[df['ticket_bucket'] == 'easy', 'actual_resolution_min'].mean(), 2)},
        {'metric': 'medium_breached_avg_resolution_days', 'value': round(df.loc[(df['ticket_bucket'] == 'medium') & (df['overall_sla_status'] == 'Breached'), 'actual_resolution_min'].mean() / 1440, 2)},
        {'metric': 'hard_breached_avg_resolution_weeks', 'value': round(df.loc[(df['ticket_bucket'] == 'hard_feature') & (df['overall_sla_status'] == 'Breached'), 'actual_resolution_min'].mean() / 10080, 2)},
        {'metric': 'overall_sla_2023_pct', 'value': round(((df['year'] == 2023) & (df['overall_sla_status'] == 'Met')).sum() / max((df['year'] == 2023).sum(), 1) * 100, 2)},
        {'metric': 'overall_sla_2024_pct', 'value': round(((df['year'] == 2024) & (df['overall_sla_status'] == 'Met')).sum() / max((df['year'] == 2024).sum(), 1) * 100, 2)},
        {'metric': 'overall_sla_2025_pct', 'value': round(((df['year'] == 2025) & (df['overall_sla_status'] == 'Met')).sum() / max((df['year'] == 2025).sum(), 1) * 100, 2)},
        {'metric': 'overall_sla_all_pct', 'value': round((df['overall_sla_status'] == 'Met').mean() * 100, 2)},
        {'metric': 'total_tickets', 'value': len(df)},
    ])

    summary_by_year = (
        df.groupby('year')
        .agg(
            total_tickets=('overall_sla_status', 'size'),
            response_sla_met_pct=('response_sla_met', lambda s: round(s.mean() * 100, 2)),
            resolution_sla_met_pct=('resolution_sla_met', lambda s: round(s.mean() * 100, 2)),
            overall_sla_met_pct=('overall_sla_status', lambda s: round((s.eq('Met')).mean() * 100, 2)),
            avg_response_min=('actual_response_min', lambda s: round(s.mean(), 2)),
            avg_resolution_hours=('actual_resolution_min', lambda s: round(s.mean() / 60, 2)),
            avg_csat=('csat_score', lambda s: round(s.mean(), 2)),
        )
        .reset_index()
    )

    summary_by_bucket = (
        df.groupby(['year', 'ticket_bucket'])
        .agg(
            total_tickets=('overall_sla_status', 'size'),
            overall_sla_met_pct=('overall_sla_status', lambda s: round((s.eq('Met')).mean() * 100, 2)),
            avg_resolution_hours=('actual_resolution_min', lambda s: round(s.mean() / 60, 2)),
            escalated_pct=('escalated', lambda s: round(s.mean() * 100, 2)),
            reopened_avg=('reopened_count', lambda s: round(s.mean(), 2)),
            avg_csat=('csat_score', lambda s: round(s.mean(), 2)),
        )
        .reset_index()
    )

    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='ticket_raw', index=False)
        summary_check.to_excel(writer, sheet_name='summary_check', index=False)
        summary_by_year.to_excel(writer, sheet_name='summary_by_year', index=False)
        summary_by_bucket.to_excel(writer, sheet_name='summary_by_bucket', index=False)

    print(f'Done. Output: {OUTPUT_FILE}')
    print(summary_check.to_string(index=False))


if __name__ == '__main__':
    main()
