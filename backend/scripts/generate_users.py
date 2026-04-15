import csv
import random
from datetime import datetime, timedelta

def generate_users():
    admin_hash = "pbkdf2_sha256$1200000$YLwu3X3jcSsc2jADLORgN0$b9L8TS1T44pHQRxbtjL+bmLcb8lcW3eXLgv+Av+WMww="
    clinic_hash = "pbkdf2_sha256$1200000$1Ty5G44vSlOVnj5kNdzwhW$SzGaDdPEDZQsJM37Jh1HxWxlMx6LXm5KJ3OV1xdRQjs="
    
    users = []
    
    # 1. Super Admin
    now = datetime.now()
    created = now - timedelta(days=random.randint(100, 800)) # ~2.2 years
    last_login = now - timedelta(days=random.randint(0, 30))
    
    users.append({
        'id': 1,
        'username': 'super_admin',
        'email': 'admin@healthcare.ai',
        'password': admin_hash,
        'role': 'ADMIN',
        'clinic_id': '',
        'date_joined': created.strftime('%Y-%m-%d %H:%M:%S'),
        'last_login': last_login.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # 2. Clinic Users (25)
    for i in range(1, 26):
        created = now - timedelta(days=random.randint(100, 800))
        last_login = now - timedelta(days=random.randint(0, 30))
        
        users.append({
            'id': i + 1,
            'username': f'clinic_{i:03d}',
            'email': f'clinic{i}@healthcare.ai',
            'password': clinic_hash,
            'role': 'CLINIC_USER',
            'clinic_id': i,
            'date_joined': created.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': last_login.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    with open('../data/users.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'username', 'email', 'password', 'role', 'clinic_id', 'date_joined', 'last_login'])
        writer.writeheader()
        writer.writerows(users)
    
    print("Generated data/users.csv successfully.")

if __name__ == "__main__":
    generate_users()
