from django.db import migrations, models


def populate_prescription_date(apps, schema_editor):
    PrescriptionLine = apps.get_model('inventory', 'PrescriptionLine')
    PrescriptionLine.objects.filter(prescription_date__isnull=True).update(
        prescription_date=models.F('prescription__prescription_date')
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
