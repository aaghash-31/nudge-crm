import asyncio
import random
import os
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# Import models after env loaded
from database import engine, AsyncSessionLocal, Base
from models import Customer, Order

fake = Faker("en_IN")

PRODUCTS = [
    "Face Wash", "Moisturiser", "Serum", "Lipstick",
    "Kajal", "Sunscreen", "Foundation", "Toner",
    "Eye Cream", "Sheet Mask", "Night Cream", "BB Cream"
]

CHANNELS = [
    "WhatsApp", "WhatsApp", "WhatsApp",
    "Email", "Email",
    "SMS"
]

TIERS = ["bronze", "silver", "gold"]

async def seed():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables ready.")

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select, func
        count_result = await db.execute(select(func.count()).select_from(Customer))
        existing = count_result.scalar()
        if existing > 0:
            print(f"Database already has {existing} customers. Skipping seed.")
            print("To re-seed, drop the customers table first.")
            return

        print("Seeding 500 customers...")
        customers = []
        for i in range(500):
            c = Customer(
                name=fake.name(),
                phone=f"+91{random.randint(7000000000, 9999999999)}",
                email=fake.email(),
                channel_preference=random.choice(CHANNELS),
                tags={
                    "tier": random.choice(TIERS),
                    "city": fake.city(),
                    "age_group": random.choice(["18-24", "25-34", "35-44", "45+"])
                }
            )
            db.add(c)
            customers.append(c)

        await db.flush()
        print(f"Customers created. Seeding 2000 orders...")

        for j in range(2000):
            customer = random.choice(customers)

            # Realistic recency distribution
            r = random.random()
            if r < 0.30:
                days_ago = random.randint(1, 30)      # recent
            elif r < 0.70:
                days_ago = random.randint(31, 90)     # mid
            else:
                days_ago = random.randint(91, 365)    # dormant

            order_date = datetime.utcnow() - timedelta(days=days_ago)
            num_products = random.randint(1, 3)
            products = random.sample(PRODUCTS, num_products)
            amount = round(random.uniform(299, 4999), 2)

            o = Order(
                customer_id=customer.id,
                amount=amount,
                items={
                    "products": products,
                    "count": num_products,
                    "category": "beauty"
                },
                created_at=order_date
            )
            db.add(o)

            if (j + 1) % 500 == 0:
                print(f"  {j + 1} orders created...")

        await db.commit()
        print("Seed complete! 500 customers and 2000 orders ready.")

if __name__ == "__main__":
    asyncio.run(seed())