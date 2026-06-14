import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import database as db

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with db.engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.create_all)
    print("Database tables created successfully")

    # Auto-seed if empty
    try:
        async with db.AsyncSessionLocal() as session:
            from sqlalchemy import select, func
            from models import Customer
            count = (await session.execute(
                select(func.count()).select_from(Customer)
            )).scalar()

            if count == 0:
                print("Database empty — running seed...")
                from seed import seed
                await seed()
                print("Auto-seed complete!")
            else:
                print(f"Database has {count} customers — skipping seed")
    except Exception as e:
        print(f"Seed check failed: {e}")

    yield
    await db.engine.dispose()

app = FastAPI(title="Nudge CRM", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "nudge-crm"}

from routers import customers, campaigns, communications
app.include_router(customers.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(communications.router, prefix="/api")