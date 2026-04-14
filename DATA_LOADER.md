# Django Custom Commands

The `data_loader` app provides powerful utility commands to manage the database and seed data.

**Usage:** Navigate to your backend directory (`cd backend`) and run:  
`python manage.py <command_name>`

## Available Commands

| Command | Description |
|---|---|
| `import_data` | Imports core initial data from the `data/` CSV files into the DB. |
| `export_data` | Exports current database state back to CSV format. |
