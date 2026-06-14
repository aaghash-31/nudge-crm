import os
import hmac
import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import get_db
from models import Communication, MessageEvent
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

STATE_ORDER = ["queued", "dispatched", "delivered", "opened", "clicked", "converted"]

class ReceiptPayload(BaseModel):
    communication_id: str
    event_type: str
    event_id: str
    payload: dict = {}

@router.post("/receipt")
@router.post("/receipt")
async def receive_callback(
    body: ReceiptPayload,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Idempotency check — this is the critical engineering piece
    existing = (await db.execute(
        select(MessageEvent).where(MessageEvent.event_id == body.event_id)
    )).scalar_one_or_none()

    if existing:
        return {"status": "duplicate", "message": "Event already processed"}

    # Insert event record
    event = MessageEvent(
        communication_id=body.communication_id,
        event_type=body.event_type,
        event_id=body.event_id,
        payload=body.payload,
        received_at=datetime.utcnow()
    )

    try:
        db.add(event)
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"status": "duplicate", "message": "Race condition handled"}

    # State machine — only advance forward
    comm = (await db.execute(
        select(Communication).where(Communication.id == body.communication_id)
    )).scalar_one_or_none()

    if comm:
        current_idx = STATE_ORDER.index(comm.status) if comm.status in STATE_ORDER else 0
        new_state = body.event_type
        now = datetime.utcnow()

        if new_state in STATE_ORDER:
            new_idx = STATE_ORDER.index(new_state)
            if new_idx > current_idx:
                comm.status = new_state
                if new_state == "delivered":
                    comm.delivered_at = now
                elif new_state == "opened":
                    comm.opened_at = now
                elif new_state == "clicked":
                    comm.clicked_at = now
                elif new_state == "converted":
                    comm.converted_at = now
                    order_val = float(body.payload.get("order_value", 0))
                    print(f"CONVERTED: communication {body.communication_id} — order value ₹{order_val}")
                    comm.revenue_attributed = order_val
        elif new_state == "failed" and comm.status == "dispatched":
            comm.status = "failed"

    await db.commit()
    return {"status": "ok"}