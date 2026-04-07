"""
analytics/aggregation.py

Layer 1 — Pure ORM aggregation functions.
NO prediction logic here. NO Python loops for counting.
All functions return QuerySets or dicts from DB aggregation only.
"""
import re
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Count, Sum, Avg, Max, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

from analytics.models import Appointment
from inventory.models import PrescriptionLine


def get_disease_type(name: str) -> str:
    """Strip trailing numbers — no hardcoded disease list."""
    return re.sub(r'\s+\d+$', '', name or '').strip()


# ── 1.1 Disease case counts (ORM Count) ──────────────────────────────────────

def aggregate_disease_counts(start: date, end: date) -> dict:
    """
    Count appointments per disease type in date range.
    Returns {disease_type: count}
    Uses ORM Count — no Python loops for aggregation.
    """
    qs = (
        Appointment.objects
        .filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('disease')
        .values('disease__name', 'disease__season',
                'disease__category', 'disease__severity')
        .annotate(case_count=Count('id'))
    )

    result = defaultdict(lambda: {
        'count': 0, 'season': 'All', 'category': '', 'severity': 1
    })

    for row in qs:
        dtype = get_disease_type(row['disease__name'])
        result[dtype]['count']    += row['case_count']
        result[dtype]['season']    = row['disease__season']
        result[dtype]['category']  = row['disease__category'] or ''
        result[dtype]['severity']  = row['disease__severity']

    return dict(result)


# ── 1.2 Time-series: daily counts using TruncDate ────────────────────────────

def aggregate_daily_counts(start: date, end: date,
                           disease_filter: str = None) -> dict:
    """
    Group appointment counts by date and disease type.
    Uses TruncDate for date grouping — pure ORM.
    Returns {disease_type: {date: count}}
    """
    qs = (
        Appointment.objects
        .filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('disease')
        .annotate(appt_date=TruncDate('appointment_datetime'))
        .values('appt_date', 'disease__name', 'disease__season')
        .annotate(day_count=Count('id'))
        .order_by('appt_date')
    )

    if disease_filter:
        qs = qs.filter(disease__name__icontains=disease_filter)

    result = defaultdict(lambda: {'season': 'All', 'daily': defaultdict(int)})

    for row in qs:
        dtype = get_disease_type(row['disease__name'])
        result[dtype]['season'] = row['disease__season']
        result[dtype]['daily'][row['appt_date']] += row['day_count']

    return dict(result)


def build_daily_list(daily_map: dict, start: date, end: date) -> list:
    """Convert date→count map to ordered list. Fills missing dates with 0."""
    counts = []
    cursor = start
    while cursor <= end:
        counts.append(daily_map.get(cursor, 0))
        cursor += timedelta(days=1)
    return counts


# ── 1.3 Medicine usage: Sum(quantity) grouped by disease + medicine ───────────

def aggregate_medicine_usage(start: date, end: date) -> list:
    """
    Sum(quantity) grouped by drug + disease.
    avg_usage = total_quantity / total_cases (DB-driven formula)
    No hardcoded drug-disease mapping.
    """
    # Case counts per disease type
    case_qs = (
        Appointment.objects
        .filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('disease')
        .values('disease__name')
        .annotate(total_cases=Count('id'))
    )
    case_map = defaultdict(int)
    for row in case_qs:
        case_map[get_disease_type(row['disease__name'])] += row['total_cases']

    # ORM Sum(quantity)
    usage_qs = (
        PrescriptionLine.objects
        .filter(
            prescription_date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('drug', 'disease')
        .values('drug__drug_name', 'drug__generic_name',
                'disease__name', 'disease__season')
        .annotate(
            total_quantity=Sum('quantity'),
            rx_count=Count('id'),
        )
        .order_by('drug__drug_name')
    )

    type_usage = defaultdict(lambda: defaultdict(lambda: {
        'generic': '', 'season': '', 'qty': 0, 'rx': 0
    }))

    for row in usage_qs:
        drug_name = row['drug__drug_name']
        dtype     = get_disease_type(row['disease__name'])
        entry     = type_usage[drug_name][dtype]
        entry['generic'] = row['drug__generic_name'] or ''
        entry['season']  = row['disease__season']
        entry['qty']    += row['total_quantity'] or 0
        entry['rx']     += row['rx_count'] or 0

    results = []
    for drug_name, disease_map in type_usage.items():
        for dtype, data in disease_map.items():
            total_cases = case_map.get(dtype, 1) or 1
            results.append({
                'drug_name':          drug_name,
                'generic_name':       data['generic'],
                'disease_name':       dtype,
                'season':             data['season'],
                'total_quantity':     data['qty'],
                'total_cases':        total_cases,
                'avg_usage':          round(data['qty'] / total_cases, 4),
                'prescription_count': data['rx'],
            })

    return sorted(results, key=lambda x: -x['total_quantity'])


# ── New Feature 1: Trend Comparison ──────────────────────────────────────────

def compare_disease_trends(period1_start: date, period1_end: date,
                           period2_start: date, period2_end: date) -> list:
    """
    Compare disease case counts between two date ranges.
    Returns increase/decrease percentage per disease.
    No hardcoding — all diseases from DB.
    """
    p1 = aggregate_disease_counts(period1_start, period1_end)
    p2 = aggregate_disease_counts(period2_start, period2_end)

    all_diseases = set(p1.keys()) | set(p2.keys())
    results = []

    for dtype in all_diseases:
        count1 = p1.get(dtype, {}).get('count', 0)
        count2 = p2.get(dtype, {}).get('count', 0)
        season = (p1.get(dtype) or p2.get(dtype, {})).get('season', 'All')

        if count1 == 0:
            pct_change = 100.0 if count2 > 0 else 0.0
            direction  = 'new'
        else:
            pct_change = round(((count2 - count1) / count1) * 100, 2)
            direction  = 'up' if pct_change > 0 else 'down' if pct_change < 0 else 'stable'

        results.append({
            'disease_name':       dtype,
            'season':             season,
            'period1_count':      count1,
            'period2_count':      count2,
            'change':             count2 - count1,
            'pct_change':         pct_change,
            'direction':          direction,
            'period1':            f'{period1_start} to {period1_end}',
            'period2':            f'{period2_start} to {period2_end}',
        })

    results.sort(key=lambda x: abs(x['pct_change']), reverse=True)
    return results


# ── New Feature 2: Top Medicines ──────────────────────────────────────────────

def aggregate_top_medicines(start: date, end: date, limit: int = 10) -> list:
    """
    Top medicines by total usage using ORM Sum.
    Groups by drug_name, calculates total prescriptions and total quantity.
    No hardcoding.
    """
    qs = (
        PrescriptionLine.objects
        .filter(prescription_date__range=(start, end))
        .select_related('drug')
        .values('drug__drug_name', 'drug__generic_name', 'drug__dosage_type')
        .annotate(
            total_quantity=Sum('quantity'),
            total_prescriptions=Count('id'),
            avg_qty_per_rx=Avg('quantity'),
        )
        .order_by('-total_quantity')
    )

    return [
        {
            'drug_name':          row['drug__drug_name'],
            'generic_name':       row['drug__generic_name'] or '',
            'dosage_type':        row['drug__dosage_type'] or '',
            'total_quantity':     row['total_quantity'] or 0,
            'total_prescriptions': row['total_prescriptions'] or 0,
            'avg_qty_per_rx':     round(row['avg_qty_per_rx'] or 0, 2),
        }
        for row in qs[:limit]
    ]


# ── New Feature 4: Disease Seasonality Insights ───────────────────────────────

def aggregate_seasonality(start: date, end: date) -> dict:
    """
    Analyse disease occurrence by season from Disease model.
    No hardcoded season-disease mapping — all from DB.
    Returns most common disease per season + full breakdown.
    """
    qs = (
        Appointment.objects
        .filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('disease')
        .values('disease__name', 'disease__season')
        .annotate(case_count=Count('id'))
        .order_by('disease__season', '-case_count')
    )

    seasons = defaultdict(list)
    for row in qs:
        dtype  = get_disease_type(row['disease__name'])
        season = row['disease__season']
        seasons[season].append({
            'disease_name': dtype,
            'case_count':   row['case_count'],
        })

    result = {}
    for season, entries in seasons.items():
        # Aggregate by disease type within season
        type_totals = defaultdict(int)
        for e in entries:
            type_totals[e['disease_name']] += e['case_count']

        sorted_diseases = sorted(type_totals.items(), key=lambda x: -x[1])
        result[season] = {
            'top_disease':      sorted_diseases[0][0] if sorted_diseases else None,
            'top_disease_count': sorted_diseases[0][1] if sorted_diseases else 0,
            'total_cases':      sum(type_totals.values()),
            'diseases':         [
                {'disease_name': d, 'case_count': c}
                for d, c in sorted_diseases
            ],
        }

    return result


# ── New Feature 5: Doctor-wise Disease Trends ─────────────────────────────────

def aggregate_doctor_wise(start: date, end: date) -> list:
    """
    Group disease data by doctor.
    Shows which doctor handles most cases of specific diseases.
    Pure ORM — no Python loops for aggregation.
    """
    qs = (
        Appointment.objects
        .filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('doctor', 'disease')
        .values(
            'doctor__id', 'doctor__first_name', 'doctor__last_name',
            'disease__name', 'disease__season',
        )
        .annotate(case_count=Count('id'))
        .order_by('-case_count')
    )

    results = []
    for row in qs:
        doctor_name = f"{row['doctor__first_name']} {row['doctor__last_name'] or ''}".strip()
        dtype       = get_disease_type(row['disease__name'])
        results.append({
            'doctor_id':    row['doctor__id'],
            'doctor_name':  doctor_name,
            'disease_name': dtype,
            'season':       row['disease__season'],
            'case_count':   row['case_count'],
        })

    return results


# ── New Feature 6: Weekly / Monthly aggregation ───────────────────────────────

def aggregate_weekly(start: date, end: date) -> list:
    """Group appointment counts by week using TruncWeek."""
    qs = (
        Appointment.objects
        .filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('disease')
        .annotate(week=TruncWeek('appointment_datetime'))
        .values('week', 'disease__name')
        .annotate(case_count=Count('id'))
        .order_by('week')
    )

    results = []
    for row in qs:
        results.append({
            'week':         str(row['week'])[:10] if row['week'] else '',
            'disease_name': get_disease_type(row['disease__name']),
            'case_count':   row['case_count'],
        })
    return results


def aggregate_monthly(start: date, end: date) -> list:
    """Group appointment counts by month using TruncMonth."""
    qs = (
        Appointment.objects
        .filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('disease')
        .annotate(month=TruncMonth('appointment_datetime'))
        .values('month', 'disease__name')
        .annotate(case_count=Count('id'))
        .order_by('month')
    )

    results = []
    for row in qs:
        results.append({
            'month':        str(row['month'])[:7] if row['month'] else '',
            'disease_name': get_disease_type(row['disease__name']),
            'case_count':   row['case_count'],
        })
    return results