import random
from django.core.management.base import BaseCommand
from core.models import Clinic


# ── Tamil Nadu — all 38 districts with towns, areas, streets ──────────

TN_DISTRICTS = {
    "Chennai": {
        "pincode_range": (600001, 600119),
        "towns": ["Chennai", "Adyar", "Anna Nagar", "Velachery", "Tambaram",
                  "Ambattur", "Avadi", "Porur", "Chromepet", "Perambur",
                  "Kodambakkam", "Nungambakkam", "T.Nagar", "Mylapore", "Royapettah"],
        "areas": ["1st Main Road", "2nd Cross Street", "Gandhi Nagar",
                  "Nehru Street", "Anna Salai", "Mount Road", "Poonamallee High Road",
                  "GST Road", "Old Mahabalipuram Road", "Rajiv Gandhi Salai"],
        "phone_prefix": ["044"],
    },
    "Coimbatore": {
        "pincode_range": (641001, 641114),
        "towns": ["Coimbatore", "Peelamedu", "Gandhipuram", "RS Puram",
                  "Saibaba Colony", "Singanallur", "Mettupalayam", "Pollachi",
                  "Tirupur", "Annur", "Sulur", "Kinathukadavu"],
        "areas": ["DB Road", "Avinashi Road", "Trichy Road", "Sathyamangalam Road",
                  "Race Course Road", "Nehru Street", "Big Bazaar Street",
                  "Oppanakara Street", "Cross Cut Road", "Maruthamalai Road"],
        "phone_prefix": ["0422"],
    },
    "Madurai": {
        "pincode_range": (625001, 625022),
        "towns": ["Madurai", "Anna Nagar", "KK Nagar", "Thirumangalam",
                  "Melur", "Usilampatti", "Vadipatti", "Paravai", "Arapalayam"],
        "areas": ["Kamaraj Salai", "North Veli Street", "South Veli Street",
                  "Bypass Road", "Mattuthavani Road", "Kalavasal",
                  "Alagar Kovil Road", "Periyar Bus Stand Road"],
        "phone_prefix": ["0452"],
    },
    "Salem": {
        "pincode_range": (636001, 636016),
        "towns": ["Salem", "Fairlands", "Suramangalam", "Kondalampatti",
                  "Attur", "Omalur", "Mettur", "Namakkal", "Rasipuram"],
        "areas": ["Omalur Road", "Junction Main Road", "Cherry Road",
                  "Saradha College Road", "Perumal Koil Street",
                  "Five Roads", "Shevapet", "Ammapet"],
        "phone_prefix": ["0427"],
    },
    "Tiruchirappalli": {
        "pincode_range": (620001, 620024),
        "towns": ["Trichy", "Srirangam", "Woraiyur", "Ariyamangalam",
                  "Thillai Nagar", "KK Nagar", "Lalgudi", "Manachanallur",
                  "Musiri", "Kulithalai", "Perambalur"],
        "areas": ["Bharathidasan Road", "Rockfort Road", "Salai Road",
                  "Williams Road", "Promenade Road", "Mettu Street",
                  "Chinthamani Road", "Palpannai"],
        "phone_prefix": ["0431"],
    },
    "Tirunelveli": {
        "pincode_range": (627001, 627013),
        "towns": ["Tirunelveli", "Palayamkottai", "Nanguneri", "Tenkasi",
                  "Ambasamudram", "Sankarankovil", "Cheranmahadevi"],
        "areas": ["High Ground Road", "Junction Road", "Bye Pass Road",
                  "NGO Colony", "Vannarpettai", "Melapalayam"],
        "phone_prefix": ["0462"],
    },
    "Vellore": {
        "pincode_range": (632001, 632014),
        "towns": ["Vellore", "Katpadi", "Ambur", "Vaniyambadi",
                  "Ranipet", "Arcot", "Wallajah", "Gudiyatham"],
        "areas": ["Arcot Road", "Officers Line", "Gandhi Nagar",
                  "Sainathapuram", "Kagithapuram", "VIT Road"],
        "phone_prefix": ["0416"],
    },
    "Erode": {
        "pincode_range": (638001, 638011),
        "towns": ["Erode", "Bhavani", "Gobichettipalayam", "Sathyamangalam",
                  "Perundurai", "Kangeyam", "Dharapuram"],
        "areas": ["Perundurai Road", "Brough Road", "VOC Road",
                  "Cauvery Road", "Gandhiji Road", "Nethaji Road"],
        "phone_prefix": ["0424"],
    },
    "Thanjavur": {
        "pincode_range": (613001, 613010),
        "towns": ["Thanjavur", "Kumbakonam", "Papanasam", "Pattukottai",
                  "Thiruvaiyaru", "Budalur", "Orathanadu"],
        "areas": ["Medical College Road", "Nanjikottai Road", "Hospital Road",
                  "Raja Street", "Ayyasamy Road", "Trichy Road"],
        "phone_prefix": ["04362"],
    },
    "Tiruppur": {
        "pincode_range": (641601, 641688),
        "towns": ["Tiruppur", "Avinashi", "Uthukuli", "Palladam",
                  "Dharapuram", "Kangeyam", "Udumalpet"],
        "areas": ["Kumaran Road", "Kamaraj Road", "Old Trunk Road",
                  "Kangeyam Road", "Palladam Road", "Mill Street"],
        "phone_prefix": ["0421"],
    },
    "Kancheepuram": {
        "pincode_range": (631501, 631562),
        "towns": ["Kancheepuram", "Chengalpet", "Madurantakam",
                  "Uthiramerur", "Sriperumbudur", "Tambaram"],
        "areas": ["Gandhi Road", "Pillayar Koil Street", "Ekambaranatha Kovil Street",
                  "Salai Road", "Bypass Road", "Station Road"],
        "phone_prefix": ["044"],
    },
    "Dindigul": {
        "pincode_range": (624001, 624710),
        "towns": ["Dindigul", "Palani", "Kodaikanal", "Oddanchatram",
                  "Vedasandur", "Natham", "Nilakottai"],
        "areas": ["Trichy Road", "Palani Road", "Bypass Road",
                  "Old Bus Stand Road", "Railway Station Road"],
        "phone_prefix": ["0451"],
    },
    "Villupuram": {
        "pincode_range": (605001, 605602),
        "towns": ["Villupuram", "Tindivanam", "Kallakurichi", "Gingee",
                  "Vikravandi", "Ulundurpet"],
        "areas": ["Salem Road", "Cuddalore Road", "Station Road",
                  "Gandhi Street", "Bazaar Street"],
        "phone_prefix": ["04146"],
    },
    "Cuddalore": {
        "pincode_range": (607001, 607803),
        "towns": ["Cuddalore", "Chidambaram", "Panruti", "Virudhachalam",
                  "Neyveli", "Bhuvanagiri"],
        "areas": ["Beach Road", "Hospital Road", "Netaji Street",
                  "Thiruvalluvar Salai", "Subash Road"],
        "phone_prefix": ["04142"],
    },
    "Nagapattinam": {
        "pincode_range": (611001, 611108),
        "towns": ["Nagapattinam", "Mayiladuthurai", "Sirkazhi",
                  "Vedaranyam", "Tharangambadi", "Kilvelur"],
        "areas": ["Beach Road", "Hospital Street", "Gandhi Road",
                  "Collector Office Road", "East Car Street"],
        "phone_prefix": ["04365"],
    },
    "Pudukottai": {
        "pincode_range": (622001, 622506),
        "towns": ["Pudukkottai", "Aranthangi", "Karambakudi",
                  "Thirumayam", "Gandarvakottai"],
        "areas": ["Trichy Road", "Madurai Road", "Hospital Road",
                  "Gandhi Nagar", "Collectorate Road"],
        "phone_prefix": ["04322"],
    },
    "Ramanathapuram": {
        "pincode_range": (623501, 623807),
        "towns": ["Ramanathapuram", "Rameswaram", "Paramakudi",
                  "Mandapam", "Kamuthi"],
        "areas": ["Bay View Road", "Beach Road", "Market Street",
                  "Kalam Road", "Muniaandi Street"],
        "phone_prefix": ["04567"],
    },
    "Thoothukudi": {
        "pincode_range": (628001, 628908),
        "towns": ["Thoothukudi", "Kovilpatti", "Tiruchendur",
                  "Kayalpattinam", "Ottapidaram"],
        "areas": ["Harbour Road", "VOC Road", "Beach Road",
                  "Millerpuram Road", "Palayamkottai Road"],
        "phone_prefix": ["0461"],
    },
    "Virudhunagar": {
        "pincode_range": (626001, 626190),
        "towns": ["Virudhunagar", "Sivakasi", "Sattur", "Aruppukkottai",
                  "Rajapalayam", "Srivilliputhur"],
        "areas": ["Madurai Road", "Tenkasi Road", "Hospital Road",
                  "Gandhi Street", "Market Road"],
        "phone_prefix": ["04562"],
    },
    "Sivaganga": {
        "pincode_range": (630001, 630702),
        "towns": ["Sivaganga", "Karaikudi", "Devakottai",
                  "Manamadurai", "Tiruppattur"],
        "areas": ["Madurai Road", "Trichy Road", "Anna Salai",
                  "Market Street", "Hospital Road"],
        "phone_prefix": ["04575"],
    },
    "Theni": {
        "pincode_range": (625501, 625579),
        "towns": ["Theni", "Bodinayakanur", "Periyakulam",
                  "Uthamapalayam", "Andipatti"],
        "areas": ["Madurai Road", "Cumbum Road", "Bypass Road",
                  "Mundy Street", "Gandhi Road"],
        "phone_prefix": ["04546"],
    },
    "Krishnagiri": {
        "pincode_range": (635001, 635126),
        "towns": ["Krishnagiri", "Hosur", "Denkanikottai",
                  "Uthangarai", "Bargur"],
        "areas": ["Bangalore Road", "Salem Road", "SIPCOT Road",
                  "Mathur Road", "Old Bus Stand Road"],
        "phone_prefix": ["04343"],
    },
    "Dharmapuri": {
        "pincode_range": (636701, 636810),
        "towns": ["Dharmapuri", "Harur", "Pappireddipatti",
                  "Pennagaram", "Nallampalli"],
        "areas": ["Salem Road", "Krishnagiri Road", "Bypass Road",
                  "Market Street", "Hospital Road"],
        "phone_prefix": ["04342"],
    },
    "Tiruvannamalai": {
        "pincode_range": (606001, 606906),
        "towns": ["Tiruvannamalai", "Polur", "Cheyyar",
                  "Vandavasi", "Arni"],
        "areas": ["Girivalam Road", "Chennai Road", "Vellore Road",
                  "Bypass Road", "Kilnathur Road"],
        "phone_prefix": ["04175"],
    },
    "Namakkal": {
        "pincode_range": (637001, 637408),
        "towns": ["Namakkal", "Rasipuram", "Tiruchengode",
                  "Paramathi", "Kumarapalayam"],
        "areas": ["Salem Road", "Trichy Road", "Erode Road",
                  "Sankari Road", "Market Street"],
        "phone_prefix": ["04286"],
    },
    "Nilgiris": {
        "pincode_range": (643001, 643253),
        "towns": ["Ooty", "Coonoor", "Kotagiri", "Gudalur",
                  "Pandalur", "Udhagamandalam"],
        "areas": ["Charing Cross Road", "Commercial Road", "Hospital Road",
                  "Club Road", "Mysore Road"],
        "phone_prefix": ["0423"],
    },
    "Karur": {
        "pincode_range": (639001, 639136),
        "towns": ["Karur", "Kulithalai", "Aravakurichi",
                  "Krishnarayapuram", "Kadavur"],
        "areas": ["Trichy Road", "Erode Road", "Bypass Road",
                  "Old Bus Stand Road", "Market Road"],
        "phone_prefix": ["04324"],
    },
    "Ariyalur": {
        "pincode_range": (621701, 621730),
        "towns": ["Ariyalur", "Andimadam", "Sendurai",
                  "Udayarpalayam", "Jayankondam"],
        "areas": ["Trichy Road", "Perambalur Road", "Market Street",
                  "Hospital Road", "Gandhi Nagar"],
        "phone_prefix": ["04329"],
    },
    "Perambalur": {
        "pincode_range": (621101, 621220),
        "towns": ["Perambalur", "Kunnam", "Veppanthattai",
                  "Alathur", "Kurumbalur"],
        "areas": ["Salem Road", "Trichy Road", "Old Town Road",
                  "Market Street", "Bypass Road"],
        "phone_prefix": ["04328"],
    },
    "Tiruvarur": {
        "pincode_range": (610001, 614905),
        "towns": ["Tiruvarur", "Papanasam", "Valangaiman",
                  "Nannilam", "Kodavasal"],
        "areas": ["Kumbakonam Road", "Mannargudi Road", "Hospital Street",
                  "East Car Street", "West Car Street"],
        "phone_prefix": ["04366"],
    },
    "Kallakurichi": {
        "pincode_range": (606202, 606213),
        "towns": ["Kallakurichi", "Sankarapuram", "Ulundurpet",
                  "Tirukoilur", "Chinnasalem"],
        "areas": ["Salem Road", "Villupuram Road", "Market Street",
                  "Station Road", "Bypass Road"],
        "phone_prefix": ["04151"],
    },
    "Tenkasi": {
        "pincode_range": (627811, 627861),
        "towns": ["Tenkasi", "Sankarankovil", "Kadayanallur",
                  "Alangulam", "Sivagiri"],
        "areas": ["Tirunelveli Road", "Courtallam Road", "Market Street",
                  "Bypass Road", "Hospital Road"],
        "phone_prefix": ["04633"],
    },
    "Ranipet": {
        "pincode_range": (632401, 632519),
        "towns": ["Ranipet", "Arcot", "Walajah", "Sholinghur",
                  "Nemili", "Arakkonam"],
        "areas": ["Vellore Road", "Chennai Road", "Market Street",
                  "SIPCOT Road", "Bypass Road"],
        "phone_prefix": ["04172"],
    },
    "Chengalpet": {
        "pincode_range": (603001, 603211),
        "towns": ["Chengalpet", "Madurantakam", "Cheyyur",
                  "Thirukalukundram", "Pondicherry Border"],
        "areas": ["GST Road", "OMR Road", "ECR Road",
                  "Bypass Road", "Market Street"],
        "phone_prefix": ["044"],
    },
    "Mayiladuthurai": {
        "pincode_range": (609001, 609811),
        "towns": ["Mayiladuthurai", "Sirkazhi", "Poompuhar",
                  "Kollidam", "Sembanarkoil"],
        "areas": ["Kumbakonam Road", "Nagapattinam Road", "Market Street",
                  "Car Street", "Hospital Road"],
        "phone_prefix": ["04364"],
    },
    "Tirupathur": {
        "pincode_range": (635601, 635854),
        "towns": ["Tirupathur", "Ambur", "Vaniyambadi",
                  "Jolarpettai", "Natrampalli"],
        "areas": ["Vellore Road", "Krishnagiri Road", "Market Street",
                  "Station Road", "Hospital Road"],
        "phone_prefix": ["04179"],
    },
}

STREET_TYPES = [
    "Main Road", "Cross Street", "1st Street", "2nd Street", "3rd Street",
    "North Street", "South Street", "East Street", "West Street",
    "Anna Street", "Gandhi Road", "Nehru Street", "Ambedkar Road",
    "Kamaraj Road", "Periyar Street", "Hospital Road", "Market Street",
    "Raja Street", "Kovil Street", "Tank Street", "Big Street",
    "New Street", "Old Street", "Bazaar Street", "School Road",
]

STREET_NAMES = [
    "Murugan", "Vinayagar", "Mariamman", "Perumal", "Shiva",
    "Ambedkar", "Gandhi", "Nehru", "Kamaraj", "MGR",
    "Periyar", "Anna", "Rajaji", "Bharathiar", "Vivekananda",
    "Subash", "Patel", "Indira", "Rajiv", "APJ Kalam",
]


def generate_tn_address(district_name, district_data):
    """Generate one realistic Tamil Nadu address."""
    house_no   = random.randint(1, 999)
    house_suffix = random.choice(['', '/A', '/B', '/1', '/2', ''])
    street_no  = random.randint(1, 50)
    street_name = random.choice(STREET_NAMES)
    street_type = random.choice(STREET_TYPES)
    area       = random.choice(district_data["areas"])
    town       = random.choice(district_data["towns"])
    pincode    = random.randint(*district_data["pincode_range"])
    phone_prefix = random.choice(district_data["phone_prefix"])
    phone_num  = random.randint(2000000, 9999999)
    phone      = f"{phone_prefix}-{phone_num}"

    address = (
        f"No.{house_no}{house_suffix}, "
        f"{street_no}, {street_name} {street_type}, "
        f"{area}, "
        f"{town}, "
        f"{district_name}, "
        f"Tamil Nadu - {pincode}. "
        f"Ph: {phone}"
    )
    return address, district_name


class Command(BaseCommand):
    help = 'Updates all clinic addresses with realistic Tamil Nadu addresses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to update per batch (default: 500)'
        )
        parser.add_argument(
            '--district',
            type=str,
            default=None,
            help='Update only clinics for a specific district (optional)'
        )

    def handle(self, *args, **options):
        batch_size     = options['batch_size']
        filter_district = options['district']

        clinics = list(Clinic.objects.all().order_by('id'))
        total   = len(clinics)

        self.stdout.write(f'\nUpdating {total} clinic addresses with Tamil Nadu data...\n')

        district_names = list(TN_DISTRICTS.keys())

        # Distribute clinics proportionally across all 38 districts
        # Bigger districts get more clinics
        district_weights = {
            "Chennai": 10, "Coimbatore": 15, "Madurai": 8,
            "Salem": 6,    "Tiruchirappalli": 6, "Vellore": 5,
            "Tiruppur": 5, "Erode": 4,  "Thanjavur": 4,
        }
        weights = [district_weights.get(d, 2) for d in district_names]

        updated = 0
        to_update = []
        district_count = {d: 0 for d in district_names}

        for clinic in clinics:
            if filter_district:
                chosen_district = filter_district
                if chosen_district not in TN_DISTRICTS:
                    self.stdout.write(self.style.ERROR(
                        f'District "{chosen_district}" not found. '
                        f'Available: {", ".join(district_names)}'
                    ))
                    return
            else:
                chosen_district = random.choices(district_names, weights=weights, k=1)[0]

            district_data = TN_DISTRICTS[chosen_district]
            address, district = generate_tn_address(chosen_district, district_data)

            clinic.clinic_address_1 = address
            to_update.append(clinic)
            district_count[chosen_district] += 1

            # Batch update
            if len(to_update) >= batch_size:
                Clinic.objects.bulk_update(to_update, ['clinic_address_1'])
                updated += len(to_update)
                to_update = []
                self.stdout.write(f'  Updated {updated}/{total}...')

        # Final batch
        if to_update:
            Clinic.objects.bulk_update(to_update, ['clinic_address_1'])
            updated += len(to_update)

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Done — {updated} clinic addresses updated\n'
        ))
        self.stdout.write('Distribution across districts:')
        for district, count in sorted(district_count.items(), key=lambda x: -x[1]):
            if count > 0:
                bar = '█' * (count // 50)
                self.stdout.write(f'  {district:<20} {count:>5}  {bar}')
