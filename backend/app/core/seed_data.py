"""
Seed data for Ytili platform
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.donation import MedicationCatalog
from ..models.user import User, UserType, UserStatus, UserPoints
from ..core.security import get_password_hash


async def create_sample_medications(db: AsyncSession):
    """Create sample medication catalog entries"""
    
    # Check if medications already exist
    result = await db.execute(select(MedicationCatalog))
    if result.scalars().first():
        print("Medications already exist, skipping seed data")
        return
    
    sample_medications = [
        {
            "name": "Paracetamol",
            "generic_name": "Acetaminophen",
            "brand_names": ["Tylenol", "Panadol", "Efferalgan"],
            "category": "medication",
            "subcategory": "analgesic",
            "therapeutic_class": "Non-opioid analgesic",
            "registration_number": "VN-001-2023",
            "is_prescription_required": False,
            "is_controlled_substance": False,
            "dosage_form": "tablet",
            "strength": "500mg",
            "packaging": "box of 20 tablets",
            "indications": "Pain relief, fever reduction",
            "contraindications": "Severe liver disease",
            "side_effects": "Rare: liver damage with overdose",
            "storage_conditions": "Store below 25°C, dry place",
            "min_expiry_months": 12,
            "is_donation_allowed": True,
            "donation_notes": "Commonly needed medication"
        },
        {
            "name": "Amoxicillin",
            "generic_name": "Amoxicillin",
            "brand_names": ["Augmentin", "Amoxil"],
            "category": "medication",
            "subcategory": "antibiotic",
            "therapeutic_class": "Penicillin antibiotic",
            "registration_number": "VN-002-2023",
            "is_prescription_required": True,
            "is_controlled_substance": False,
            "dosage_form": "capsule",
            "strength": "250mg",
            "packaging": "box of 21 capsules",
            "indications": "Bacterial infections",
            "contraindications": "Penicillin allergy",
            "side_effects": "Nausea, diarrhea, allergic reactions",
            "storage_conditions": "Store below 25°C, dry place",
            "min_expiry_months": 18,
            "is_donation_allowed": True,
            "donation_notes": "Prescription required"
        },
        {
            "name": "Ibuprofen",
            "generic_name": "Ibuprofen",
            "brand_names": ["Advil", "Brufen", "Nurofen"],
            "category": "medication",
            "subcategory": "anti-inflammatory",
            "therapeutic_class": "NSAID",
            "registration_number": "VN-003-2023",
            "is_prescription_required": False,
            "is_controlled_substance": False,
            "dosage_form": "tablet",
            "strength": "400mg",
            "packaging": "box of 30 tablets",
            "indications": "Pain, inflammation, fever",
            "contraindications": "Stomach ulcers, kidney disease",
            "side_effects": "Stomach upset, dizziness",
            "storage_conditions": "Store below 25°C, dry place",
            "min_expiry_months": 24,
            "is_donation_allowed": True,
            "donation_notes": "Anti-inflammatory medication"
        },
        {
            "name": "Surgical Mask",
            "generic_name": None,
            "brand_names": ["3M", "Kimberly-Clark"],
            "category": "medical_supply",
            "subcategory": "protective_equipment",
            "therapeutic_class": None,
            "registration_number": "VN-MS-001-2023",
            "is_prescription_required": False,
            "is_controlled_substance": False,
            "dosage_form": None,
            "strength": None,
            "packaging": "box of 50 masks",
            "indications": "Infection prevention",
            "contraindications": None,
            "side_effects": None,
            "storage_conditions": "Store in dry place",
            "min_expiry_months": 36,
            "is_donation_allowed": True,
            "donation_notes": "Essential protective equipment"
        },
        {
            "name": "Vitamin C",
            "generic_name": "Ascorbic Acid",
            "brand_names": ["Redoxon", "Cebion"],
            "category": "food",
            "subcategory": "vitamin",
            "therapeutic_class": "Vitamin supplement",
            "registration_number": "VN-004-2023",
            "is_prescription_required": False,
            "is_controlled_substance": False,
            "dosage_form": "tablet",
            "strength": "1000mg",
            "packaging": "bottle of 60 tablets",
            "indications": "Vitamin C deficiency, immune support",
            "contraindications": "Kidney stones history",
            "side_effects": "Stomach upset with high doses",
            "storage_conditions": "Store below 25°C, dry place",
            "min_expiry_months": 24,
            "is_donation_allowed": True,
            "donation_notes": "Nutritional supplement"
        },
        {
            "name": "Insulin",
            "generic_name": "Human Insulin",
            "brand_names": ["Humulin", "Novolin"],
            "category": "medication",
            "subcategory": "hormone",
            "therapeutic_class": "Antidiabetic",
            "registration_number": "VN-005-2023",
            "is_prescription_required": True,
            "is_controlled_substance": False,
            "dosage_form": "injection",
            "strength": "100 IU/ml",
            "packaging": "vial 10ml",
            "indications": "Diabetes mellitus",
            "contraindications": "Hypoglycemia",
            "side_effects": "Hypoglycemia, injection site reactions",
            "storage_conditions": "Refrigerate 2-8°C",
            "min_expiry_months": 6,
            "is_donation_allowed": True,
            "donation_notes": "Requires cold storage, critical medication"
        }
    ]
    
    for med_data in sample_medications:
        medication = MedicationCatalog(**med_data)
        db.add(medication)
    
    await db.commit()
    print(f"Created {len(sample_medications)} sample medications")


async def create_admin_user(db: AsyncSession):
    """Create default admin user"""
    
    # Check if admin user already exists
    result = await db.execute(
        select(User).where(User.email == "admin@ytili.com")
    )
    if result.scalar_one_or_none():
        print("Admin user already exists")
        return
    
    # Create admin user
    admin_user = User(
        email="admin@ytili.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Ytili Administrator",
        user_type=UserType.GOVERNMENT,
        status=UserStatus.VERIFIED,
        is_email_verified=True,
        is_kyc_verified=True,
        organization_name="Ytili Platform",
        city="Ho Chi Minh City",
        province="Ho Chi Minh",
        country="Vietnam"
    )
    
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    
    # Create user points record
    user_points = UserPoints(user_id=admin_user.id, tier_level="Platinum")
    db.add(user_points)
    await db.commit()
    
    print("Created admin user: admin@ytili.com / admin123")


async def seed_database(db: AsyncSession):
    """Seed the database with initial data"""
    print("Seeding database...")
    
    await create_admin_user(db)
    await create_sample_medications(db)
    
    print("Database seeding completed!")
