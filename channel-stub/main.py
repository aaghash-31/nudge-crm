import os
import hmac
import hashlib
import json
import random
import asyncio
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx

load_dotenv()

app = FastAPI(title="Nudge Channel Stub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RECEIPT_URL = os.getenv("CRM_RECEIPT_URL", "http://localhost:8000/receipt")
HMAC_SECRET = os.getenv("HMAC_SECRET", "nudge-secret-key-2026")

class SendRequest(BaseModel):
    communication_id: str
    recipient: str
    message: str
    channel: str

def sign_payload(payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"))
    return hmac.new(
        HMAC_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

async def post_callback(payload: dict):
    signature = sign_payload(payload)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                RECEIPT_URL,
                json=payload,
                headers={"X-Nudge-Signature": signature},
                timeout=10
            )
            print(f"Callback sent: {payload['event_type']} for {payload['communication_id']} → {response.status_code}")
        except Exception as e:
            print(f"Callback failed: {e}")

async def simulate_delivery(communication_id: str):
    """Simulate the full delivery lifecycle with realistic delays."""
    
    # 8% chance of immediate failure
    if random.random() < 0.08:
        await asyncio.sleep(random.uniform(2, 5))
        await post_callback({
            "communication_id": communication_id,
            "event_type": "failed",
            "event_id": str(uuid.uuid4()),
            "payload": {"reason": "invalid_number"}
        })
        return

    # Step 1: delivered after 1-3 seconds
    await asyncio.sleep(random.uniform(1, 3))
    delivered_event_id = str(uuid.uuid4())
    await post_callback({
        "communication_id": communication_id,
        "event_type": "delivered",
        "event_id": delivered_event_id,
        "payload": {}
    })

    # 5% chance: send duplicate delivered to test idempotency
    if random.random() < 0.05:
        await asyncio.sleep(2)
        await post_callback({
            "communication_id": communication_id,
            "event_type": "delivered",
            "event_id": delivered_event_id,  # same event_id = duplicate
            "payload": {}
        })
        print(f"Sent duplicate callback for {communication_id} — idempotency test")

    # Step 2: opened after 10-40 seconds (35% chance)
    if random.random() < 0.70:
        await asyncio.sleep(random.uniform(3, 8))
        await post_callback({
            "communication_id": communication_id,
            "event_type": "opened",
            "event_id": str(uuid.uuid4()),
            "payload": {}
        })

        # Step 3: clicked after 30-90 seconds (15% chance)
        if random.random() < 0.45:
            await asyncio.sleep(random.uniform(5,12))
            await post_callback({
                "communication_id": communication_id,
                "event_type": "clicked",
                "event_id": str(uuid.uuid4()),
                "payload": {}
            })

            # Step 4: converted after 2-5 minutes (5% chance)
            # Step 4: converted after 8-20 seconds (40% chance for demo)
            # Step 4: converted — guaranteed for demo impact
            if random.random() < 0.80:
                await asyncio.sleep(random.uniform(8, 20))
                order_value = round(random.uniform(1500, 4500), 2)
                await post_callback({
                    "communication_id": communication_id,
                    "event_type": "converted",
                    "event_id": str(uuid.uuid4()),
                    "payload": {"order_value": order_value}
                })

@app.post("/send")
async def receive_send(req: SendRequest):
    """Receive a send request and simulate delivery asynchronously."""
    print(f"Received send: {req.communication_id} via {req.channel} to {req.recipient}")
    asyncio.create_task(simulate_delivery(req.communication_id))
    return {"status": "queued", "communication_id": req.communication_id}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "channel-stub"}