from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User

from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster
from analytics.services.restock_service import RestockService
from analytics.services.alert_engine import AlertEngineService

class AlertAndRestockServiceTestCase(TestCase):
    """Tests for Alert Engine and Restock logic (Features 5, 8)."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Alert Clinic")
        self.admin = User.objects.create_superuser(username="admin_alert", password="pw")
        UserProfile.objects.create(user=self.admin, role="ADMIN")
        
        self.disease = Disease.objects.create(name="Malaria", severity=3)
        self.doctor = Doctor.objects.create(first_name="DrA", clinic=self.clinic)
        self.patient = Patient.objects.create(first_name="PatA", dob="1990-01-01", clinic=self.clinic)

    def test_adaptive_safety_buffer(self):
        """Feature 5: Test Adaptive Safety Buffer with Volatility."""
        service = RestockService()
        today = date.today()
        # Stable usage
        daily = {"Malaria": {today: 10, today - timedelta(days=1): 10}}
        res = service.calculate_adaptive_buffer(daily_by_disease=daily)
        self.assertEqual(res['adaptive_buffer'], 1.2) # BASE_SAFETY_BUFFER

    def test_unified_alert_engine(self):
        """Feature 8: Test Real-Time Alert Engine scoring."""
        engine = AlertEngineService()
        
        # 1. Critical Stock (Impact 90)
        DrugMaster.objects.create(drug_name="CritMed", current_stock=0, clinic=self.clinic)
        
        # 2. Disease Spike (Strictly Increasing for Feature 2/8)
        # 4 days of growth: 5, 10, 15, 20
        base = timezone.now() - timedelta(days=4)
        for d in range(4):
            for i in range((d+1)*5):
                Appointment.objects.create(
                    appointment_datetime=base + timedelta(days=d),
                    disease=self.disease, clinic=self.clinic, doctor=self.doctor, patient=self.patient,
                    op_number=f"SPIKE-{d}-{i}"
                )
             
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.admin
        
        alerts = engine.get_unified_alerts(days=7, request=request)
        types = [a['type'] for a in alerts]
        self.assertIn('outbreak', types)
        self.assertIn('stock', types)
        
        # Outbreak should be higher priority (Impact depends on growth score)
        self.assertEqual(alerts[0]['type'], 'outbreak')
