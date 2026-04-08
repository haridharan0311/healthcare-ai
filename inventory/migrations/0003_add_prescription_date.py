from django.db import migrations, models
from django.db.models import OuterRef, Subquery


def populate_prescription_date(apps, schema_editor):
    PrescriptionLine = apps.get_model('inventory', 'PrescriptionLine')
    Prescription = apps.get_model('inventory', 'Prescription')
    
    # Get prescription dates using a subquery
    prescription_dates = Prescription.objects.filter(
        pk=OuterRef('prescription_id')
    ).values('prescription_date')[:1]
    
    # Update PrescriptionLine with the subquery
    PrescriptionLine.objects.filter(prescription_date__isnull=True).update(
        prescription_date=Subquery(prescription_dates)
    )


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_add_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='prescriptionline',
            name='prescription_date',
            field=models.DateField(
                null=True,
                db_index=True,
                help_text='Denormalized copy of prescription.prescription_date for faster range filtering',
            ),
        ),
        migrations.RunPython(populate_prescription_date, migrations.RunPython.noop),
    ]
