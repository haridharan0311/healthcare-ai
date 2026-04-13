#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Check database connectivity before starting
    if 'runserver' in sys.argv:
        try:
            import pymysql
            from decouple import config
            # Django 6.0 requires mysqlclient 2.2.1+
            # We spoof the version if pymysql is used
            pymysql.version_info = (2, 2, 1, 'final', 0)
            pymysql.install_as_MySQLdb()
            
            # Use high-level health check
            conn = pymysql.connect(
                host=config('DB_HOST', default='localhost'),
                port=int(config('DB_PORT', default=3306)),
                user=config('DB_USER'),
                password=config('DB_PASSWORD'),
                database=config('DB_NAME'),
                connect_timeout=5
            )
            conn.close()
        except Exception:
            print("\n" + "="*60)
            print("ERROR: Database connection failed!")
            print(f"Host: {config('DB_HOST', default='localhost')}:{config('DB_PORT', default=3306)}")
            print("Please ensure your MySQL server is running.")
            print("="*60 + "\n")
            sys.exit(1)

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
