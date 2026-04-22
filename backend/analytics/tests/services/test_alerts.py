from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User
from core.models import Clinic, UserProfile, Doctor, Patient
from analytics.models import Disease, Appointment
from inventory.models import DrugMaster
from analytics.services.alert_engine import AlertEngineService

class AlertEngineTestCase(TestCase):
    """Feature 8: Real-Time Alert Engine tests."""

    def setUp(self):
        self.clinic = Clinic.objects.create(clinic_name="Alert Clinic")
        self.user = User.objects.create_superuser(username="alert_admin", password="pw")
        UserProfile.objects.create(user=self.user, role="ADMIN")
        self.disease = Disease.objects.create(name="Fever", severity=3)
        self.doc = Doctor.objects.create(first_name="DrA", clinic=self.clinic)
        self.pat = Patient.objects.create(first_name="PatA", dob="2000-01-01", clinic=self.clinic)

    def test_alert_prioritization(self):
        # 1. Outbreak Spike (Increasing trend over 3 days)
        from datetime import timedelta
        base = timezone.now() - timedelta(days=3)
        for d in range(4):
            count = (d + 1) * 5 # 5, 10, 15, 20
            for i in range(count):
                Appointment.objects.create(
                    appointment_datetime=base + timedelta(days=d),
                    disease=self.disease, clinic=self.clinic, doctor=self.doc, patient=self.pat,
                    op_number=f"A-{d}-{i}"
                )

        
        # 2. Stock Issue (Impact 90)
        DrugMaster.objects.create(drug_name="O-Stock", current_stock=0, clinic=self.clinic)
        
        engine = AlertEngineService()
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        alerts = engine.get_unified_alerts(days=7, request=request)
        # Outbreak should be first
        self.assertEqual(alerts[0]['type'], 'outbreak')
        self.assertGreater(alerts[0]['impact_score'], 90) # Should be higher than stock alert (90)

