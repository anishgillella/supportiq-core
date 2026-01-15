"""
Script to seed 20 test users into the SupportIQ database
Run with: python -m scripts.seed_users
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_supabase_admin
from app.core.security import get_password_hash
import random
from datetime import datetime, timedelta

# Sample data for generating realistic users
FIRST_NAMES = [
    "James", "Emma", "Michael", "Olivia", "William", "Sophia", "Alexander", "Isabella",
    "Daniel", "Mia", "David", "Charlotte", "Joseph", "Amelia", "Matthew", "Harper",
    "Andrew", "Evelyn", "Benjamin", "Abigail"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin"
]

COMPANIES = [
    "TechCorp", "DataFlow", "CloudNine", "InnovateTech", "DigitalDynamics",
    "SmartSolutions", "NextGen Systems", "CyberWave", "AlphaLogic", "BetaSoft"
]

CITIES = [
    ("New York", "NY", "10001"),
    ("Los Angeles", "CA", "90001"),
    ("Chicago", "IL", "60601"),
    ("Houston", "TX", "77001"),
    ("Phoenix", "AZ", "85001"),
    ("Philadelphia", "PA", "19101"),
    ("San Antonio", "TX", "78201"),
    ("San Diego", "CA", "92101"),
    ("Dallas", "TX", "75201"),
    ("Austin", "TX", "78701"),
]

STREETS = [
    "Main Street", "Oak Avenue", "Maple Drive", "Cedar Lane", "Pine Road",
    "Elm Street", "Park Boulevard", "Lake View", "Highland Avenue", "River Road"
]

ABOUT_ME_TEMPLATES = [
    "Product manager with {} years of experience in {}",
    "Software engineer passionate about {} and {}",
    "Marketing specialist focusing on {} strategies",
    "Customer success manager helping teams with {}",
    "Data analyst working on {} optimization",
    "UX designer creating intuitive {} experiences",
    "Sales representative in the {} industry",
    "Operations manager streamlining {} processes",
    "Business analyst specializing in {} solutions",
    "Technical writer documenting {} systems"
]

INTERESTS = [
    "AI/ML", "cloud computing", "mobile apps", "e-commerce", "fintech",
    "healthcare tech", "SaaS", "automation", "analytics", "cybersecurity"
]


def generate_random_date(start_year=1970, end_year=2000):
    """Generate a random birthdate"""
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    days_between = (end_date - start_date).days
    random_days = random.randint(0, days_between)
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")


def seed_users():
    """Create 20 test users with profiles"""
    supabase = get_supabase_admin()

    print("Starting to seed 20 test users...")

    created_count = 0

    for i in range(20):
        first_name = FIRST_NAMES[i]
        last_name = LAST_NAMES[i]
        email = f"{first_name.lower()}.{last_name.lower()}@example.com"

        # Check if user already exists
        existing = supabase.table("supportiq_users").select("id").eq("email", email).execute()
        if existing.data:
            print(f"  User {email} already exists, skipping...")
            continue

        # Create user
        password_hash = get_password_hash("password123")
        company = random.choice(COMPANIES)

        # Random step completion (1-3) and whether onboarding is complete
        current_step = random.randint(1, 3)
        onboarding_completed = current_step == 3 and random.choice([True, False])
        if onboarding_completed:
            current_step = 3

        user_record = {
            "email": email,
            "password_hash": password_hash,
            "company_name": company,
            "company_website": f"https://www.{company.lower().replace(' ', '')}.com",
            "current_step": current_step,
            "onboarding_completed": onboarding_completed,
        }

        result = supabase.table("supportiq_users").insert(user_record).execute()

        if not result.data:
            print(f"  Failed to create user {email}")
            continue

        user = result.data[0]
        user_id = user["id"]

        # Create profile with realistic data
        city, state, zip_code = random.choice(CITIES)
        street_num = random.randint(100, 9999)
        street = random.choice(STREETS)

        about_template = random.choice(ABOUT_ME_TEMPLATES)
        years = random.randint(2, 15)
        interest1 = random.choice(INTERESTS)
        interest2 = random.choice([i for i in INTERESTS if i != interest1])

        try:
            about_me = about_template.format(years, interest1, interest2)
        except IndexError:
            about_me = about_template.format(years, interest1)

        profile_record = {
            "user_id": user_id,
            "about_me": about_me if current_step >= 2 else None,
            "street_address": f"{street_num} {street}" if current_step >= 2 else None,
            "city": city if current_step >= 2 else None,
            "state": state if current_step >= 2 else None,
            "zip_code": zip_code if current_step >= 2 else None,
            "birthdate": generate_random_date() if current_step >= 3 else None,
        }

        supabase.table("supportiq_user_profiles").insert(profile_record).execute()

        status = "completed" if onboarding_completed else f"step {current_step}"
        print(f"  Created user: {email} ({status})")
        created_count += 1

    print(f"\nDone! Created {created_count} new users.")


if __name__ == "__main__":
    seed_users()
