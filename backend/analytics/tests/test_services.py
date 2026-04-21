from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from analytics.services.forecasting import ForecastingService
from analytics.services.restock_service import RestockService
from analytics.services.aggregation import get_disease_type, compare_disease_trends
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster, Prescription, PrescriptionLine
from core.models import Clinic, Doctor, Patient, UserProfile

class InternalServicesTestCase(TestCase):
    """
    Detailed integration tests for internal business services.
    Validates forecasting models, restock algorithms, and data multi-aggregation logic.
    """

    def setUp(self):
        # Base setup for all service tests
        self.clinic = Clinic.objects.create(clinic_name="Alpha", clinic_address_1="Central")
        self.doctor = Doctor.objects.create(first_name="D", gender="M", qualification="MD", clinic=self.clinic)
        self.patient = Patient.objects.create(first_name="P", last_name="1", gender="M", dob="1990-01-01", clinic=self.clinic)
        self.disease = Disease.objects.create(name="Fever", season="ALL", severity=2, created_at=timezone.now())
        
        # Initialize Services
        self.forecast_service = ForecastingService()
        self.restock_service = RestockService()
        
        # Shared dependency for some tests
        self.appointment = Appointment.objects.create(
            appointment_datetime=timezone.now(), appointment_status="C",
            disease=self.disease, clinic=self.clinic, doctor=self.doctor, 
            patient=self.patient, op_number="SETUP-1"
        )
        
        # System User for filtered services
        self.user_admin = User.objects.create_user(username="testadmin", password="pw", is_staff=True)
        UserProfile.objects.create(user=self.user_admin, role="ADMIN")

    # ── Forecasting Service Tests ───────────────────────────────────

    def test_forecast_insufficient_data(self):
        """Test that forecasting service correctly identifies low data volume."""
        # Create only 1 appointment (need 3 for MA + ES blended model)
        Appointment.objects.create(
            appointment_datetime=timezone.now(), appointment_status="C",
            disease=self.disease, clinic=self.clinic, doctor=self.doctor, 
            patient=self.patient, op_number="X1"
        )
        res = self.forecast_service.forecast_next_period("Fever")
        self.assertEqual(res['status'], 'insufficient_data')
        self.assertEqual(res['forecast_value'], 0)

    def test_forecast_confidence_intervals(self):
        """Test that confidence intervals are generated for data-rich sequences."""
        # Seed 10 days of consistent data
        now = timezone.now()
        for i in range(10):
            Appointment.objects.create(
                appointment_datetime=now - timedelta(days=i), 
                appointment_status="C", disease=self.disease, clinic=self.clinic, 
                doctor=self.doctor, patient=self.patient, op_number=f"F{i}"
            )
        
        res = self.forecast_service.forecast_next_period("Fever", days_ahead=7)
        self.assertIn('confidence_lower', res)
        self.assertIn('confidence_upper', res)
        self.assertGreaterEqual(res['confidence_upper'], res['forecast_value'])

    def test_trend_scoring_logic(self):
        """Validate trend classification based on period ratios."""
        # Worsening: more recent cases
        res_worsening = self.forecast_service.calculate_trend_score(recent_cases=50, older_cases=10)
        self.assertEqual(res_worsening['direction'], 'worsening')
        
        # Improving: fewer recent cases
        res_improving = self.forecast_service.calculate_trend_score(recent_cases=5, older_cases=20)
        self.assertEqual(res_improving['direction'], 'improving')


    # ── Restock Service Tests ───────────────────────────────────────

    def test_adaptive_buffer_calculation(self):
        """Test that safety buffer increases during regional spikes."""
        # Baseline buffer is 1.2. If spikes exist, it should go up.
        # We simulate a spike by passing daily counts manually or letting it query.
        now = date.today()
        daily_by_disease = {
            'Flu': {
                now - timedelta(days=6): 10,
                now - timedelta(days=5): 10,
                now - timedelta(days=4): 10,
                now - timedelta(days=3): 10, 
                now - timedelta(days=2): 10,
                now - timedelta(days=1): 10,
                now: 100 # Spike on the target day
            }
        }
        res = self.restock_service.calculate_adaptive_buffer(
            start_date=now - timedelta(days=7),
            end_date=now,
            daily_by_disease=daily_by_disease
        )
        self.assertGreater(res['adaptive_buffer'], 1.2)
        self.assertEqual(res['interpretation'], 'high_risk')

    def test_restock_suggestion_prioritization(self):
        """Verify that critical stock issues are prioritized in suggestions."""
        # Drug A: Out of stock (Zero)
        DrugMaster.objects.create(drug_name="DrugA", current_stock=0, clinic=self.clinic)
        # Drug B: High stock
        DrugMaster.objects.create(drug_name="DrugB", current_stock=500, clinic=self.clinic)
        
        # Need at least 3 appointments for a valid forecast/demand
        for i in range(3):
            appt = Appointment.objects.create(
                appointment_datetime=timezone.now() - timedelta(days=i), 
                appointment_status="C", disease=self.disease, clinic=self.clinic, 
                doctor=self.doctor, patient=self.patient, op_number=f"RS-{i}"
            )
            rx = Prescription.objects.create(
                prescription_date=date.today(), appointment=appt, 
                clinic=self.clinic, doctor=self.doctor, patient=self.patient
            )
            PrescriptionLine.objects.create(
                prescription=rx, drug=DrugMaster.objects.get(drug_name="DrugA"), 
                quantity=50, disease=self.disease
            )

        res = self.restock_service.calculate_restock_suggestions(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
            request=self.user_admin
        )
        
        # DrugA should be 'critical' or 'low' and appear at the top
        self.assertGreater(len(res), 0)
        self.assertEqual(res[0]['drug_name'], "DrugA")
        self.assertIn(res[0]['status'], ['critical', 'low'])


    # ── Aggregation Logic Tests ────────────────────────────────────

    def test_disease_type_regex(self):
        """Test cleaning of trailing version/variant numbers from disease names."""
        self.assertEqual(get_disease_type("Influenza 001"), "Influenza")
        self.assertEqual(get_disease_type("Flu B Variant"), "Flu B Variant")


    def test_trend_comparison_delta(self):
        """Test calculation of percentage change between two periods."""
        # Use a fresh disease to avoid setup interference
        new_disease = Disease.objects.create(name="DeltaFlu", season="ALL", created_at=timezone.now())
        # Period 1: 10 cases
        for i in range(10): Appointment.objects.create(
            appointment_datetime=timezone.now() - timedelta(days=20),
            appointment_status="C", disease=new_disease, clinic=self.clinic, 
            doctor=self.doctor, patient=self.patient, op_number=f"PD1-{i}"
        )
        # Period 2: 20 cases (Exactly 100% increase)
        for i in range(20): Appointment.objects.create(
            appointment_datetime=timezone.now() - timedelta(days=5),
            appointment_status="C", disease=new_disease, clinic=self.clinic, 
            doctor=self.doctor, patient=self.patient, op_number=f"PD2-{i}"
        )
        
        res = compare_disease_trends(
            period1_start=date.today() - timedelta(days=25), period1_end=date.today() - timedelta(days=15),
            period2_start=date.today() - timedelta(days=10), period2_end=date.today()
        )
        
        fever_comp = next(r for r in res if r['disease_name'] == 'DeltaFlu')
        self.assertEqual(fever_comp['pct_change'], 100.0)
        self.assertEqual(fever_comp['direction'], 'up')
