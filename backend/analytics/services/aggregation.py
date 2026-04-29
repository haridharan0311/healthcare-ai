"""
Layer 1 — Pure ORM aggregation functions.
NO prediction logic here. NO Python loops for counting where ORM suffices.
All functions return QuerySets or dicts from DB aggregation only.
"""
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

from django.db.models import Count, Sum, Avg, Q, QuerySet
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

from analytics.models import Appointment, Disease
from inventory.models import PrescriptionLine, DrugMaster
from .constants import (
    VARIANT_FILTERS, 
    DEFAULT_TOP_DRUGS_LIMIT, 
    DEFAULT_TOP_MEDICINES_LIMIT,
    ROUNDING_PRECISION_USAGE,
    ROUNDING_PRECISION_DEFAULT
)

def get_disease_type(name: str) -> str:
    """Strip trailing numbers and 'Variant' suffix to merge data categories."""
    if not name: return "Unknown"
    # Remove 'Variant' (case-insensitive)
    name = re.sub(r'\s+Variant\s*$', '', name, flags=re.IGNORECASE)
    # Remove trailing numbers
    return re.sub(r'\s+\d+\s*$', '', name).strip()


# ── 1.1 Disease case counts (ORM Count) ──────────────────────────────────────

def aggregate_disease_counts(start: date, end: date, queryset: Optional[QuerySet] = None) -> Dict[str, Any]:
    """
    Count appointments per disease type in date range.
    Returns {disease_type: {count, season, category, severity}}
    """
    if queryset is None:
        queryset = Appointment.objects.all()

    qs = (
        queryset
        .filter(
            appointment_datetime__date__range=(start, end),
            disease__isnull=False,
        )
        .select_related('disease')
        .values(
            'disease__name', 'disease__season',
            'disease__category', 'disease__severity'
        )
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

def aggregate_daily_counts(
    start: date, 
    end: date,
    disease_filter: Optional[str] = None,
    queryset: Optional[QuerySet] = None
) -> Dict[str, Any]:
    """
    Group appointment counts by date and disease type.
    """
    if queryset is None:
        queryset = Appointment.objects.all()

    qs = (
        queryset
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


def build_daily_list(daily_map: Dict[date, int], start: date, end: date) -> List[int]:
    """Convert date→count map to ordered list. Fills missing dates with 0."""
    counts = []
    cursor = start
    while cursor <= end:
        counts.append(daily_map.get(cursor, 0))
        cursor += timedelta(days=1)
    return counts


# ── 1.3 Medicine usage: Sum(quantity) grouped by disease + medicine ───────────

def aggregate_medicine_usage(
    start: date, 
    end: date,
    rx_queryset: Optional[QuerySet] = None,
    appt_queryset: Optional[QuerySet] = None
) -> List[Dict[str, Any]]:
    """
    Sum(quantity) grouped by drug + disease.
    Optimized: 2-step process for high performance.
    """
    if rx_queryset is None: rx_queryset = PrescriptionLine.objects.all()
    if appt_queryset is None: appt_queryset = Appointment.objects.all()

    # 1. Identify top medicines first
    top_drugs_qs = (
        rx_queryset
        .filter(prescription_date__range=(start, end))
        .values('drug_id')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:DEFAULT_TOP_DRUGS_LIMIT]
    )
    top_drug_ids = [row['drug_id'] for row in top_drugs_qs]
    
    if not top_drug_ids:
        return []

    # 2. Case counts per disease type
    case_qs = (
        appt_queryset
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

    # 3. Group by medicine + disease
    usage_qs = (
        rx_queryset
        .filter(
            prescription_date__range=(start, end),
            drug_id__in=top_drug_ids,
            disease__isnull=False,
        )
        .values('drug_id', 'disease_id')
        .annotate(
            total_quantity=Sum('quantity'),
            rx_count=Count('id'),
        )
    )

    # Pre-fetch metadata using in_bulk for O(1) lookups
    disease_ids = {row['disease_id'] for row in usage_qs}
    drug_map = DrugMaster.objects.in_bulk(top_drug_ids)
    disease_map = Disease.objects.in_bulk(disease_ids)

    type_usage = defaultdict(lambda: defaultdict(lambda: {
        'generic': '', 'season': '', 'qty': 0, 'rx': 0, 'strength': '', 'dosage': ''
    }))

    for row in usage_qs:
        drug = drug_map.get(row['drug_id'])
        disease = disease_map.get(row['disease_id'])
        
        if not drug or not disease:
            continue
            
        drug_name = drug.drug_name
        dtype     = get_disease_type(disease.name)
        entry     = type_usage[drug_name][dtype]
        
        entry['generic'] = drug.generic_name or ''
        entry['season']  = disease.season
        entry['qty']    += row['total_quantity'] or 0
        entry['rx']     += row['rx_count'] or 0
        entry['strength'] = drug.drug_strength
        entry['dosage']   = drug.dosage_type

    results = []
    for drug_name, disease_map_obj in type_usage.items():
        for dtype, data in disease_map_obj.items():
            total_cases = case_map.get(dtype, 1) or 1
            results.append({
                'drug_name':          drug_name,
                'generic_name':       data['generic'],
                'drug_strength':      data['strength'],
                'dosage_type':        data['dosage'],
                'disease_name':       dtype,
                'season':             data['season'],
                'total_quantity':     data['qty'],
                'total_cases':        total_cases,
                'avg_usage':          round(data['qty'] / total_cases, ROUNDING_PRECISION_USAGE),
                'prescription_count': data['rx'],
            })

    return sorted(results, key=lambda x: -x['total_quantity'])


# ── New Feature 1: Trend Comparison ──────────────────────────────────────────

def compare_disease_trends(
    period1_start: date, period1_end: date,
    period2_start: date, period2_end: date,
    queryset: Optional[QuerySet] = None
) -> List[Dict[str, Any]]:
    """
    Compare disease case counts between two date ranges.
    """
    p1 = aggregate_disease_counts(period1_start, period1_end, queryset=queryset)
    p2 = aggregate_disease_counts(period2_start, period2_end, queryset=queryset)

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
            pct_change = round(((count2 - count1) / count1) * 100, ROUNDING_PRECISION_DEFAULT)
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

def aggregate_top_medicines(
    start: date, 
    end: date, 
    limit: int = DEFAULT_TOP_MEDICINES_LIMIT,
    queryset: Optional[QuerySet] = None
) -> List[Dict[str, Any]]:
    """
    Top medicines by total usage using ORM Sum.
    """
    if queryset is None:
        queryset = PrescriptionLine.objects.all()

    qs = (
        queryset
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
            'avg_qty_per_rx':     round(row['avg_qty_per_rx'] or 0, ROUNDING_PRECISION_DEFAULT),
        }
        for row in qs[:limit]
    ]


def aggregate_top_medicines_with_stock(
    start: date, 
    end: date, 
    limit: int = DEFAULT_TOP_MEDICINES_LIMIT,
    rx_queryset: Optional[QuerySet] = None,
    stock_queryset: Optional[QuerySet] = None
) -> List[Dict[str, Any]]:
    """
    Combines top usage data with live stock levels.
    """
    if rx_queryset is None: rx_queryset = PrescriptionLine.objects.all()
    if stock_queryset is None: stock_queryset = DrugMaster.objects.all()

    # 1. Usage stats
    usage_qs = (
        rx_queryset
        .filter(prescription_date__range=(start, end))
        .values('drug__drug_name')
        .annotate(
            total_quantity=Sum('quantity'),
            prescription_count=Count('id'),
        )
        .order_by('-total_quantity', '-prescription_count')[:limit]
    )
    
    usage_data = list(usage_qs)
    if not usage_data:
        return []

    top_names = [row['drug__drug_name'] for row in usage_data]

    # 2. Live stock for these specific drugs
    stock_qs = (
        stock_queryset
        .filter(drug_name__in=top_names)
        .values('drug_name', 'generic_name', 'dosage_type')
        .annotate(total_stock=Sum('current_stock'))
    )
    stock_map = {row['drug_name']: row for row in stock_qs}

    # 3. Join logic
    results = []
    for row in usage_data:
        name = row['drug__drug_name']
        details = stock_map.get(name, {})
        
        results.append({
            'drug_name':          name,
            'generic_name':       details.get('generic_name') or '',
            'dosage_type':        details.get('dosage_type') or '',
            'current_stock':      details.get('total_stock') or 0,
            'prescription_count': row['prescription_count'] or 0,
            'total_quantity':     row['total_quantity'] or 0,
        })
    
    return results


# ── New Feature 4: Disease Seasonality Insights ───────────────────────────────

def aggregate_seasonality(start: date, end: date, queryset: Optional[QuerySet] = None) -> Dict[str, Any]:
    """
    Analyse disease occurrence by season from Disease model.
    """
    if queryset is None:
        queryset = Appointment.objects.all()

    qs = (
        queryset
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
        type_totals = defaultdict(int)
        for e in entries:
            type_totals[e['disease_name']] += e['case_count']

        total_season_cases = sum(type_totals.values())
        sorted_diseases = sorted(type_totals.items(), key=lambda x: -x[1])
        
        result[season] = {
            'top_disease':      sorted_diseases[0][0] if sorted_diseases else None,
            'top_disease_count': sorted_diseases[0][1] if sorted_diseases else 0,
            'total_cases':      total_season_cases,
            'diseases':         [
                {
                    'disease_name': d, 
                    'case_count': c,
                    'percentage': round((c / total_season_cases) * 100, 1) if total_season_cases > 0 else 0
                }
                for d, c in sorted_diseases[:10] # Limit to top 10 per season for readability
            ],
        }

    return result


# ── New Feature 5: Doctor-wise Disease Trends ─────────────────────────────────

def aggregate_doctor_wise(start: date, end: date, queryset: Optional[QuerySet] = None) -> List[Dict[str, Any]]:
    """
    Group disease data by doctor.
    """
    if queryset is None:
        queryset = Appointment.objects.all()

    qs = (
        queryset
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

def aggregate_weekly(start: date, end: date, queryset: Optional[QuerySet] = None) -> List[Dict[str, Any]]:
    """Group appointment counts by week using TruncWeek."""
    if queryset is None:
        queryset = Appointment.objects.all()

    qs = (
        queryset
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

    return [
        {
            'week':         str(row['week'])[:10] if row['week'] else '',
            'disease_name': get_disease_type(row['disease__name']),
            'case_count':   row['case_count'],
        }
        for row in qs
    ]


def aggregate_monthly(start: date, end: date, queryset: Optional[QuerySet] = None) -> List[Dict[str, Any]]:
    """Group appointment counts by month using TruncMonth."""
    if queryset is None:
        queryset = Appointment.objects.all()

    qs = (
        queryset
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

    return [
        {
            'month':        str(row['month'])[:7] if row['month'] else '',
            'disease_name': get_disease_type(row['disease__name']),
            'case_count':   row['case_count'],
        }
        for row in qs
    ]