# Django Custom Commands

The `data_loader` app provides powerful utility commands to manage the database, seed data, and simulate realistic scenarios.

**Usage:** Navigate to your backend directory (`cd backend`) and run:  
`python manage.py <command_name>`

## Available Commands

| Command | Description |
|---|---|
| `import_data` | Imports core initial data from the `data/` CSV files into the DB. |
| `export_data` | Exports current database state back to CSV format. |
| `generate_daily_data` | Generates realistic appointments and prescriptions for a given time window. |
| `inject_spike` | Artificially injects a disease spike for testing outbreak alert triggers. |
| `optimize_db` | Cleans up and optimizes database indexes. |
| `redistribute_stock` | Balances inventory stock across clinics based on spatial demand. |
| `regenerate_prescription_lines` | Regenerates missing or corrupted prescription lines. |
| `reset_drug_master` | Resets the DrugMaster inventory completely back to base CSV states. |
| `update_clinic_addresses` | Standardizes and normalizes clinic address fields. |
