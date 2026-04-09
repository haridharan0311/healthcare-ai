"""
Optimized Query Builders for Analytics

Provides pre-built querysets with optimal select_related and prefetch_related
to minimize database queries. Use these in your views instead of manually
constructing querysets.

Layer: Utils (Utilities)
Usage:
    from analytics.utils.query_optimization import (
        get_appointments_optimized, get_prescription_lines_optimized
    )
    
    # Instead of:
    appointments = Appointment.objects.filter(...)
    
    # Use:
    appointments = get_appointments_optimized().filter(...)
"""

from typing import Any
from django.db.models import QuerySet, Prefetch, F
from django.db.models.functions import TruncDate

from analytics.models import Appointment, Disease
from inventory.models import Prescription, PrescriptionLine, DrugMaster
from core.models import Clinic, Doctor, Patient


def get_appointments_optimized() -> QuerySet:
    """
    ═══════════════════════════════════════════════════════════════════════════
    OPTIMIZATION: Optimized Appointment QuerySet
    ═══════════════════════════════════════════════════════════════════════════
    
    Returns an Appointment queryset with all necessary relationships pre-loaded.
    Reduces N+1 queries by joining related tables efficiently.
    
    Optimizations:
    - select_related: disease, clinic, doctor, patient (direct ForeignKeys)
    - prefetch_related: None (already covered by select_related)
    
    For new users:
        Use this instead of manual queryset construction to get automatic
        query optimization. Guarantees efficient loading of related data.
    
    Example:
        # Efficient - loads disease, clinic, doctor, patient in single query
        appts = get_appointments_optimized().filter(
            appointment_datetime__date__range=(start, end)
        )
        
        # Bad - causes N+1 queries
        # DON'T: appts = Appointment.objects.filter(...)
        
    Returns:
        QuerySet with all relationships optimized
    """
    return (
        Appointment.objects
        .select_related('disease')          # FK to Disease
        .select_related('clinic')           # FK to Clinic
        .select_related('doctor')           # FK to Doctor
        .select_related('patient')          # FK to Patient
    )


def get_appointments_with_prescriptions() -> QuerySet:
    """
    ═══════════════════════════════════════════════════════════════════════════
    OPTIMIZATION: Appointments with Related Prescriptions
    ═══════════════════════════════════════════════════════════════════════════
    
    Returns Appointment queryset with prescription data pre-loaded.
    Optimizes queries when you need to access prescription details from
    appointments.
    
    Optimizations:
    - select_related: appointment related objects
    - prefetch_related: Prescription (reverse relationship)
    
    For new users:
        Use when you iterate over appointments and need prescription data.
        Prevents N+1 queries from accessing appointment.prescriptions.
    
    Example:
        appts = get_appointments_with_prescriptions()
        for appt in appts:
            prescriptions = Prescription.objects.filter(
                appointment=appt
            )  # Already loaded from prefetch
    
    Returns:
        QuerySet with prescriptions pre-loaded
    """
    prescriptions_prefetch = Prefetch(
        'prescription_set',
        Prescription.objects.select_related(
            'clinic', 'doctor', 'patient'
        ).prefetch_related('lines')
    )
    
    return (
        get_appointments_optimized()
        .prefetch_related(prescriptions_prefetch)
    )


def get_prescription_lines_optimized() -> QuerySet:
    """
    ═══════════════════════════════════════════════════════════════════════════
    OPTIMIZATION: Optimized PrescriptionLine QuerySet
    ═══════════════════════════════════════════════════════════════════════════
    
    Returns PrescriptionLine queryset with all necessary relationships.
    Reduces queries when fetching prescription line items with their
    medications, diseases, and prescription details.
    
    Optimizations:
    - select_related: prescription (main FK)
    - select_related: disease, drug (medicine details)
    - select_related: clinic, doctor, patient (via prescription)
    
    For new users:
        Use when querying medicine inventory usage, drug consumption,
        or prescription analysis.
    
    Example:
        # Efficient - single query with all relationships
        lines = get_prescription_lines_optimized().filter(
            prescription__prescription_date__range=(start, end)
        )
        
        for line in lines:
            drug_name = line.drug.drug_name       # No extra query
            disease_name = line.disease.name      # No extra query
            clinic_name = line.prescription.clinic.clinic_name  # No extra query
    
    Returns:
        QuerySet with all medicine and prescription data optimized
    """
    return (
        PrescriptionLine.objects
        .select_related('prescription')           # FK to Prescription
        .select_related('prescription__clinic')   # Via prescription to Clinic
        .select_related('prescription__doctor')   # Via prescription to Doctor
        .select_related('prescription__patient')  # Via prescription to Patient
        .select_related('disease')                # FK to Disease
        .select_related('drug')                   # FK to DrugMaster
        .select_related('drug__clinic')           # Via drug to Clinic
    )


def get_drugs_optimized(clinic_id: int = None) -> QuerySet:
    """
    ═══════════════════════════════════════════════════════════════════════════
    OPTIMIZATION: Optimized Drug Master QuerySet
    ═══════════════════════════════════════════════════════════════════════════
    
    Returns DrugMaster queryset with clinic data pre-loaded.
    Suitable for inventory views and restock analysis.
    
    Optimizations:
    - select_related: clinic (FK to Clinic)
    
    For new users:
        Use when accessing drug inventory with clinic information.
        Prevents N+1 queries from accessing drug.clinic_name.
    
    Args:
        clinic_id: Optional filter to single clinic
    
    Returns:
        QuerySet with clinic details optimized
    """
    qs = DrugMaster.objects.select_related('clinic')
    
    if clinic_id:
        qs = qs.filter(clinic_id=clinic_id)
    
    return qs


def get_diseases_optimized() -> QuerySet:
    """
    ═══════════════════════════════════════════════════════════════════════════
    OPTIMIZATION: Optimized Disease QuerySet
    ═══════════════════════════════════════════════════════════════════════════
    
    Returns Disease queryset (minimal relationships, mostly used for reference).
    Add select_related/prefetch_related if you need related appointments.
    
    Optimizations:
    - Basic query (diseases don't have heavy relationships)
    - Indexed fields: season, is_active
    
    For new users:
        Use for disease filtering and grouping. Diseases are mostly reference
        data with few relationships.
    
    Returns:
        QuerySet of active diseases
    """
    return Disease.objects.filter(is_active=True).select_related()


def count_queries_in_operation(operation_func):
    """
    ═══════════════════════════════════════════════════════════════════════════
    DEBUG: Query Counter for Development
    ═══════════════════════════════════════════════════════════════════════════
    
    Utility to count total database queries in an operation.
    Use during development to verify optimization effectiveness.
    
    For new users:
        Use in Python shell to measure query count improvements:
        
        from analytics.utils.query_optimization import count_queries_in_operation
        
        def my_operation():
            appts = get_appointments_optimized().filter(...)
            return list(appts)
        
        count = count_queries_in_operation(my_operation)
        print(f"Total queries: {count}")
    
    Args:
        operation_func: Function to measure queries for
    
    Returns:
        Number of database queries executed
    """
    from django.db import connection, reset_queries
    from django.conf import settings
    
    if not settings.DEBUG:
        return 0
    
    reset_queries()
    operation_func()
    return len(connection.queries)


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDED USAGE PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

"""
Pattern 1: Disease Trends (Appointment-based)
─────────────────────────────────────────────
    appts = get_appointments_optimized().filter(
        appointment_datetime__date__range=(start, end),
        disease__isnull=False
    ).values('disease__name').annotate(Count('id'))
    
    Expected queries: 1 (from appointment to disease via select_related)

Pattern 2: Medicine Usage (PrescriptionLine-based)
─────────────────────────────────────────────────
    lines = get_prescription_lines_optimized().filter(
        prescription__prescription_date__range=(start, end)
    )
    
    for line in lines:
        drug = line.drug.drug_name
        disease = line.disease.name
        clinic = line.prescription.clinic.clinic_name
    
    Expected queries: 1 (all relationships pre-loaded)

Pattern 3: Inventory Analysis (Drug-based)
──────────────────────────────────────────
    drugs = get_drugs_optimized().filter(clinic_id=clinic_id)
    
    for drug in drugs:
        stock = drug.current_stock
        clinic_name = drug.clinic.clinic_name  # No extra query
    
    Expected queries: 1

Pattern 4: Detailed Prescription Analysis (Appointment → Prescriptions)
───────────────────────────────────────────────────────────────────────
    appts = get_appointments_with_prescriptions().filter(
        appointment_datetime__date__range=(start, end)
    )
    
    for appt in appts:
        prescriptions = appt.prescription_set.all()  # Pre-loaded
        for prescription in prescriptions:
            lines = prescription.lines.all()  # Pre-loaded via prefetch
    
    Expected queries: 1
"""
