import random
import sqlite3
from datetime import datetime
from faker import Faker

fake = Faker()

PRODUCTS = [
    "Premium Subscription",
    "Basic Plan",
    "Enterprise License",
    "Cloud Storage Add-on",
    "Support Ticket Pack",
    "Developer API Key",
]
conn = sqlite3.connect("report.db")
cursor = conn.cursor()

print("🌱 Seeding database with ~200 random orders...")

# Generate 200 items
orders_to_insert = []
for _ in range(200):
    customer = fake.name()  # Generates realistic names like "John Doe"

    # Select from your 5-6 products
    product = random.choice(PRODUCTS)

    # Random amount between 5 and 200, rounded to 2 decimal places
    amount = round(random.uniform(5.00, 200.00), 2)

    # Generates a random datetime object within the last 30 days
    random_date_obj = fake.date_time_between(start_date="-30d", end_date="now")
    created_at = random_date_obj.strftime("%Y-%m-%d %H:%M:%S")

    orders_to_insert.append((customer, product, amount, created_at))

# Efficiently batch insert all 200 records at once
cursor.executemany(
    """
    INSERT INTO orders (customer, product, amount, created_at)
    VALUES (?, ?, ?, ?)
""",
    orders_to_insert,
)

conn.commit()
conn.close()

print("✅ Successfully seeded 200 random orders into 'report.db'!")
