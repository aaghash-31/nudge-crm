import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import database as db

load_dotenv()

app = FastAPI(title="Nudge CRM")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    try:
        async with db.engine.begin() as conn:
            await conn.run_sync(db.Base.metadata.create_all)
        print("Database tables created successfully")
    except Exception as exc:
        print("DB startup skipped because the configured database is unavailable:", exc)

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "nudge-crm"}

from routers import customers, campaigns, communications
app.include_router(customers.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(communications.router, prefix="/api")