import csv
import random
import os
from datetime import datetime, timedelta

# --- Configuration (Balanced) ---
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2026, 4, 14)
NUM_CLINICS = 25
NUM_DISEASES = 100
NUM_DRUGS = 400
NUM_DOCTORS = 75
NUM_PATIENTS = 750 
OUTPUT_DIR = "../data/"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- LOGIC MAPPING: DRUGS & DOSAGES ---
DRUG_LOGIC = {
    "Paracetamol": ["Tablet", "Syrup", "Injection", "Drops"],
    "Amoxicillin": ["Capsule", "Tablet", "Syrup"],
    "Metformin": ["Tablet"],
    "Pantoprazole": ["Tablet", "Injection"],
    "Cetirizine": ["Tablet", "Syrup"],
    "Diclofenac": ["Tablet", "Gel", "Injection"],
    "Azithromycin": ["Tablet", "Syrup"],
    "Amlodipine": ["Tablet"],
    "Atorvastatin": ["Tablet"],
    "Losartan": ["Tablet"],
    "Omeprazole": ["Capsule"],
    "Furosemide": ["Tablet", "Injection"],
    "Ranitidine": ["Tablet", "Injection"],
    "Dextromethorphan": ["Syrup"],
    "Ciprofloxacin": ["Tablet", "Drops", "Injection"],
    "Insulin": ["Injection"],
    "Povidone-Iodine": ["Ointment", "Drops"],
    "Salbutamol": ["Syrup", "Inhaler"],
    "Metronidazole": ["Tablet", "Syrup", "Injection"],
    "Iron & Folic Acid": ["Tablet", "Syrup"],
    "Vitamin B-Complex": ["Tablet", "Capsule", "Injection"],
    "Calcium & Vit D3": ["Tablet", "Syrup"],
    "Telmisartan": ["Tablet"],
    "Gliclazide": ["Tablet"],
    "Clopidogrel": ["Tablet"],
    "Levoceterizine": ["Tablet", "Syrup"],
    "Montelukast": ["Tablet"],
    "Prednisolone": ["Tablet", "Drops"],
    "Oral Rehydration Salts": ["Drops"], # Replaced Dosage Type with Sachet later
    "Ofloxacin": ["Tablet", "Drops"]
}

DOSAGE_MAP = {
    "Tablet": ["500mg", "650mg", "250mg", "100mg", "50mg", "20mg", "10mg", "5mg"],
    "Capsule": ["500mg", "250mg", "40mg", "20mg"],
    "Syrup": ["60ml", "100ml", "200ml", "5ml/500mg"],
    "Injection": ["2ml", "5ml", "10ml", "1gm"],
    "Gel": ["30g", "50g"],
    "Ointment": ["15g", "20g"],
    "Drops": ["5ml", "10ml"],
    "Inhaler": ["200 MDI", "100 MDI"]
}

# --- LOGIC MAPPING: DISEASES & DRUGS ---
DISEASE_DRUG_LOGIC = {
    "Fever": ["Paracetamol", "Vitamin B-Complex"],
    "Flu": ["Paracetamol", "Cetirizine", "Vitamin B-Complex"],
    "Infection": ["Amoxicillin", "Azithromycin", "Ciprofloxacin", "Ofloxacin"],
    "Diabetes": ["Metformin", "Gliclazide", "Insulin"],
    "Hypertension": ["Amlodipine", "Losartan", "Telmisartan", "Hydrochlorothiazide"],
    "Gastritis": ["Pantoprazole", "Omeprazole", "Ranitidine"],
    "Pain": ["Diclofenac", "Paracetamol"],
    "Asthma": ["Salbutamol", "Montelukast", "Prednisolone"],
    "Skin Issues": ["Povidone-Iodine", "Diclofenac"], # Gel for Pain
    "General": ["Vitamin B-Complex", "Calcium & Vit D3", "Iron & Folic Acid"]
}

# --- DATA BANKS: TAMIL NADU ---
CITY_LOCALITIES = {
    "Chennai": ["T-Nagar", "Adyar", "Anna Nagar", "Velachery", "Mylapore", "Tambaram", "Guindy"],
    "Coimbatore": ["RS Puram", "Peelamedu", "Gandhipuram", "Saravanampatti", "Race Course"],
    "Madurai": ["Anna Nagar", "K.K. Nagar", "Simmakkal", "Tallakulam", "Sellur"],
    "Trichy": ["Thillai Nagar", "Woraiyur", "Srirangam", "Cantonment", "BHEL"],
    "Salem": ["Fairlands", "Hasthampatti", "Shevapet", "Suramangalam"],
    "Tirunelveli": ["Palayamkottai", "Junction", "Pettai", "Town"],
    "Vellore": ["Sathuvachari", "Katpadi", "Thorapadi", "Bagayam"],
    "Erode": ["Perundurai", "Saty", "Bhavani"],
    "Thoothukudi": ["Millerpuram", "Chidambara Nagar", "Muthiapuram"],
    "Nagercoil": ["Vadasery", "Kottar", "Ramavarmapuram"]
}
# Default cities if above runs out
TN_CITIES_EXTRA = ["Thanjavur", "Dindigul", "Ranipet", "Sivakasi", "Karur", "Ooty", "Hosur", "Ambur", "Karaikudi", "Neyveli", "Kumbakonam", "Nagapattinam", "Pudukkottai", "Viluppuram", "Rajapalayam"]

TAMIL_FIRST_NAMES_MALE = ["Arul", "Balaji", "Chandran", "Dhinesh", "Elangovan", "Ganesh", "Hari", "Iniyan", "Jegan", "Karthik", "Logesh", "Mani", "Naveen", "Palani", "Rajesh", "Suresh", "Thirumalai", "Uthayan", "Varun", "Yogesh", "Senthil", "Murugan", "Vijay", "Ajith", "Surya", "Vikram", "Dhanush", "Siva", "Kavin", "Prabhu"]
TAMIL_FIRST_NAMES_FEMALE = ["Anjali", "Banu", "Chitra", "Deepa", "Ezhil", "Gayathri", "Harini", "Indhu", "Janani", "Kavitha", "Lakshmi", "Meena", "Nivetha", "Pavithra", "Ramya", "Sangeetha", "Thivya", "Uma", "Vidhya", "Yamini", "Keerthi", "Nandhini", "Priya", "Sandhiya", "Abirami", "Aswini", "Divya", "Ishwarya", "Kausalya", "Sona"]
TAMIL_LAST_NAMES = ["Mani", "Raj", "Kumar", "Selvam", "Pandian", "Pillai", "Iyer", "Mudaliar", "Gounder", "Chettiar", "Nathan", "Desigan", "Moorthy", "Balan", "Sekar", "Rajan", "Vel", "Gunasekaran", "Perumal", "Samy"]

DISEASE_NAMES = [
    ("Dengue", "Fever"), ("Typhoid", "Fever"), ("Viral Fever", "Fever"), ("Malaria", "Fever"),
    ("COVID-19", "Flu"), ("Common Cold", "Flu"), ("Influenza", "Flu"),
    ("Diabetes Type 2", "Diabetes"), ("Diabetes Type 1", "Diabetes"),
    ("Hypertension", "Hypertension"), ("Low Blood Pressure", "Hypertension"),
    ("Gastritis", "Gastritis"), ("Peptic Ulcer", "Gastritis"), ("GERD", "Gastritis"),
    ("Pneumonia", "Infection"), ("Tuberculosis", "Infection"), ("Urinary Tract Infection", "Infection"), ("Cholera", "Infection"),
    ("Body Pain", "Pain"), ("Migraine", "Pain"), ("Back Pain", "Pain"), ("Osteoarthritis", "Pain"),
    ("Asthma", "Asthma"), ("COPD", "Asthma"), ("Bronchitis", "Asthma"),
    ("Skin Rash", "Skin Issues"), ("Eczema", "Skin Issues"), ("Psoriasis", "Skin Issues"), ("Athlete's Foot", "Skin Issues"),
    ("Anemia", "General"), ("Vitamin Deficiency", "General"), ("Gastroenteritis", "Infection")
] # To be expanded to 100 below

def generate():
    # Helper for unique diseases
    all_diseases_full = []
    base_disease_list = DISEASE_NAMES * 4 # Duplicate to get near 100
    for i in range(100):
        name, category = base_disease_list[i]
        all_diseases_full.append({"name": f"{name} Variant {i//20}" if i > 30 else name, "category": category})

    # 1. CLINICS
    clinics = []
    cities = list(CITY_LOCALITIES.keys()) + TN_CITIES_EXTRA
    for i in range(1, NUM_CLINICS + 1):
        city = cities[i-1]
        clinics.append({
            "id": i,
            "clinic_name": f"{city} Medical Center",
            "clinic_address_1": f"No {random.randint(1, 200)}, Main Road, {city}, Tamil Nadu"
        })

    # 2. DISEASES
    diseases = []
    for i in range(1, NUM_DISEASES + 1):
        d_info = all_diseases_full[i-1]
        season = random.choice(["Monsoon", "Summer", "Winter", "All-Season"])
        if "Dengue" in d_info['name'] or "Malaria" in d_info['name']: season = "Monsoon"
        if "Heat" in d_info['name']: season = "Summer"
        
        diseases.append({
            "id": i, "name": d_info['name'], "season": season, "category": d_info['category'],
            "severity": random.randint(1, 4), "is_active": "True",
            "created_at": (START_DATE - timedelta(days=365)).isoformat()
        })

    # 3. DOCTORS
    doctors = []
    for i in range(1, NUM_DOCTORS + 1):
        gender = random.choice(['M', 'F'])
        first = random.choice(TAMIL_FIRST_NAMES_MALE if gender == 'M' else TAMIL_FIRST_NAMES_FEMALE)
        last = random.choice(TAMIL_LAST_NAMES)
        doctors.append({
            "id": i, "first_name": first, "last_name": last, "gender": gender,
            "qualification": random.choice(["MBBS, MD", "MBBS, MS", "MBBS", "MD"]),
            "clinic_id": (i % NUM_CLINICS) + 1
        })

    # 4. PATIENTS
    patients = []
    for i in range(1, NUM_PATIENTS + 1):
        clinic = clinics[(i % NUM_CLINICS)]
        city = clinic['clinic_name'].split(" ")[0]
        locality = random.choice(CITY_LOCALITIES.get(city, ["Main Road"]))
        gender = random.choice(['M', 'F'])
        first = random.choice(TAMIL_FIRST_NAMES_MALE if gender == 'M' else TAMIL_FIRST_NAMES_FEMALE)
        last = random.choice(TAMIL_LAST_NAMES)
        patients.append({
            "id": i, "first_name": first, "last_name": last, "gender": gender,
            "title": random.choice(["Mr", "Dr"]) if gender == 'M' else random.choice(["Ms", "Mrs", "Dr"]),
            "dob": (START_DATE - timedelta(days=random.randint(365*5, 365*70))).date().isoformat(),
            "mobile_number": f"{random.randint(7, 9)}{random.randint(100000000, 999999999)}",
            "address_line_1": f"{random.randint(1, 100)}, {locality}, {city}, TN",
            "clinic_id": clinic['id'],
            "doctor_id": random.choice([d['id'] for d in doctors if d['clinic_id'] == clinic['id']] or [1])
        })

    # 5. DRUG MASTER (LOGIC DRIVEN)
    drugs = []
    drug_list = list(DRUG_LOGIC.keys())
    for i in range(1, NUM_DRUGS + 1):
        generic = random.choice(drug_list)
        dosage = random.choice(DRUG_LOGIC[generic])
        strength = random.choice(DOSAGE_MAP[dosage])
        clinic_id = (i % NUM_CLINICS) + 1
        
        # Real Brand Names (Approx)
        brands = {
            "Paracetamol": ["Dolo", "Crocin", "Calpol"], "Amoxicillin": ["Augmentin", "Mox"], "Metformin": ["Glycomet"],
            "Pantoprazole": ["Pan", "Pantocid"], "Cetirizine": ["Cetzine", "Okacet"]
        }
        brand_prefix = random.choice(brands.get(generic, [generic]))
        drug_name = f"{brand_prefix} {dosage} {strength}"
        
        drugs.append({
            "id": i, "drug_name": drug_name, "generic_name": generic, "drug_strength": strength,
            "dosage_type": dosage, "current_stock": random.randint(100, 1000), "clinic_id": clinic_id
        })

    # 6, 7, 8. TRANSACTIONS
    appointments, prescriptions, pres_lines = [], [], []
    appt_id, pres_id, line_id = 1, 1, 1
    
    current_date = START_DATE
    while current_date <= END_DATE:
        for clinic in clinics:
            # 3-5 appointments per clinic per day
            for _ in range(random.randint(3, 5)):
                month = current_date.month
                season = "Summer" if month in [3,4,5,6] else "Monsoon" if month in [7,8,9,10] else "Winter"
                
                # Pick disease based on season
                dis = random.choice([d for d in diseases if d['season'] == season or d['season'] == "All-Season"])
                doc = random.choice([d for d in doctors if d['clinic_id'] == clinic['id']] or [doctors[0]])
                pat = random.choice([p for p in patients if p['clinic_id'] == clinic['id']] or [patients[0]])
                
                status = "Completed" if random.random() < 0.9 else "Cancelled"
                appt_dt = current_date.replace(hour=random.randint(9, 17), minute=random.choice([0,15,30,45]))
                
                appointments.append({
                    "id": appt_id, "appointment_datetime": appt_dt.isoformat(), "appointment_status": status,
                    "op_number": f"TN-OP{appt_id:07d}", "clinic_id": clinic['id'], "doctor_id": doc['id'],
                    "patient_id": pat['id'], "disease_id": dis['id']
                })
                
                if status == "Completed":
                    prescriptions.append({
                        "id": pres_id, "prescription_date": appt_dt.date().isoformat(), "appointment_id": appt_id,
                        "clinic_id": clinic['id'], "doctor_id": doc['id'], "patient_id": pat['id']
                    })
                    
                    # Logic: Get Drugs for this Disease Category
                    drug_categories = DISEASE_DRUG_LOGIC.get(dis['category'], ["Vitamin B-Complex"])
                    clinic_drugs = [dr for dr in drugs if dr['clinic_id'] == clinic['id'] and dr['generic_name'] in drug_categories]
                    if not clinic_drugs: # Fallback
                        clinic_drugs = [dr for dr in drugs if dr['clinic_id'] == clinic['id']] or drugs
                    
                    chosen = random.sample(clinic_drugs, min(random.randint(1, 2), len(clinic_drugs)))
                    for dr in chosen:
                        pres_lines.append({
                            "id": line_id, "duration": f"{random.choice([3, 5, 10])} days", "instructions": "After Food",
                            "quantity": random.randint(5, 15), "drug_id": dr['id'], "prescription_id": pres_id,
                            "disease_id": dis['id'], "prescription_date": appt_dt.date().isoformat()
                        })
                        line_id += 1
                    pres_id += 1
                appt_id += 1
        current_date += timedelta(days=1)

    # --- CSV Write ---
    def write_csv(filename, data, fields):
        with open(os.path.join(OUTPUT_DIR, filename), "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()
            csv.DictWriter(f, fieldnames=fields).writerows(data)

    write_csv("Clinic.csv", clinics, ["id", "clinic_name", "clinic_address_1"])
    write_csv("Disease.csv", diseases, ["id", "name", "season", "category", "severity", "is_active", "created_at"])
    write_csv("Doctor.csv", doctors, ["id", "first_name", "last_name", "gender", "qualification", "clinic_id"])
    write_csv("Patient.csv", patients, ["id", "first_name", "last_name", "gender", "title", "dob", "mobile_number", "address_line_1", "clinic_id", "doctor_id"])
    write_csv("DrugMaster.csv", drugs, ["id", "drug_name", "generic_name", "drug_strength", "dosage_type", "current_stock", "clinic_id"])
    write_csv("Appointment.csv", appointments, ["id", "appointment_datetime", "appointment_status", "op_number", "clinic_id", "doctor_id", "patient_id", "disease_id"])
    write_csv("Prescription.csv", prescriptions, ["id", "prescription_date", "appointment_id", "clinic_id", "doctor_id", "patient_id"])
    write_csv("PrescriptionLine.csv", pres_lines, ["id", "duration", "instructions", "quantity", "drug_id", "prescription_id", "disease_id", "prescription_date"])

if __name__ == "__main__":
    generate()
    print("Logical TN Dataset Generated Successfully.")
