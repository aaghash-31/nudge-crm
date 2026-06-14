import os
import httpx
import asyncio
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Campaign, Communication, Customer, Order, CampaignPrediction, MessageEvent
from datetime import datetime
from pydantic import BaseModel
from services.ai_agent import generate_confidence_card, interpret_segment_intent

router = APIRouter()

class CreateCampaignRequest(BaseModel):
    intent: str
    channel: str = "WhatsApp"

# State order for the state machine
STATE_ORDER = ["queued", "dispatched", "delivered", "opened", "clicked", "converted"]

async def run_segment_query(segment_query: dict, db: AsyncSession):
    """Run segment rules against all customers and return matching ones."""
    all_customers = (await db.execute(select(Customer))).scalars().all()
    matched = []

    for c in all_customers:
        orders = (await db.execute(
            select(Order).where(Order.customer_id == c.id)
        )).scalars().all()

        total_spend = sum(o.amount for o in orders)
        last_order = max((o.created_at for o in orders), default=None)
        days_inactive = (datetime.utcnow() - last_order).days if last_order else 999
        total_orders = len(orders)

        rules = segment_query.get("rules", [])
        logic = segment_query.get("logic", "AND")

        if not rules:
            matched.append(c)
            continue

        results = []
        for rule in rules:
            field = rule.get("field", "")
            op = rule.get("op", "")
            value = rule.get("value")

            if field == "days_inactive":
                actual = days_inactive
            elif field == "total_orders":
                actual = total_orders
            elif field == "total_spend":
                actual = total_spend
            elif field == "channel_preference":
                actual = c.channel_preference
            else:
                results.append(False)
                continue

            try:
                value = float(value) if field != "channel_preference" else value
            except (TypeError, ValueError):
                results.append(False)
                continue

            if op == "gt":
                results.append(actual > value)
            elif op == "lt":
                results.append(actual < value)
            elif op == "gte":
                results.append(actual >= value)
            elif op == "lte":
                results.append(actual <= value)
            elif op == "eq":
                results.append(str(actual) == str(value))
            else:
                results.append(False)

        if logic == "AND":
            if all(results):
                matched.append(c)
        elif logic == "OR":
            if any(results):
                matched.append(c)

    return matched


@router.post("/campaigns")
async def create_campaign(
    req: CreateCampaignRequest,
    db: AsyncSession = Depends(get_db)
):
    from services.ai_agent import generate_confidence_card, interpret_segment_intent

    # Step 1: AI interprets the intent into a segment query
    segment_query = await interpret_segment_intent(req.intent)

    # Step 2: Run segment to get audience size
    matched_customers = await run_segment_query(segment_query, db)
    audience_size = len(matched_customers)

    # Step 3: Check overlap with active campaigns
    active_campaigns = (await db.execute(
        select(Campaign).where(Campaign.status == "active")
    )).scalars().all()

    overlap_count = 0
    for active in active_campaigns:
        active_matched = await run_segment_query(active.segment_query, db)
        active_ids = {c.id for c in active_matched}
        current_ids = {c.id for c in matched_customers}
        overlap_count += len(active_ids & current_ids)

    # Step 4: AI generates confidence card with full context
    card = await generate_confidence_card(
        intent=req.intent,
        audience_size=audience_size,
        channel=req.channel,
        overlap_count=overlap_count
    )
    

    # Step 5: Add overlap warning if needed
    if overlap_count > 3:
        card["overlap_warning"] = f"{overlap_count} customers are already in an active campaign. Sending now risks message fatigue."
        card["confidence_score"] = max(20, card.get("confidence_score", 50) - 15)

    # Step 6: Get 3 sample customer profiles from matched segment
    sample_profiles = []
    for c in matched_customers[:3]:
        orders = (await db.execute(
            select(Order).where(Order.customer_id == c.id)
            .order_by(Order.created_at.desc())
        )).scalars().all()
        last_order = orders[0] if orders else None
        days_inactive = (datetime.utcnow() - last_order.created_at).days if last_order else 0
        last_product = last_order.items.get("products", ["Unknown"])[0] if last_order else "Unknown"
        sample_profiles.append({
            "name": c.name.split()[0],
            "last_product": last_product,
            "days_inactive": days_inactive,
            "tier": c.tags.get("tier", "bronze")
        })



    # Step 8: Save campaign
    campaign = Campaign(
        name=req.intent[:100],
        intent=req.intent,
        segment_query=segment_query,
        channel=req.channel,
        status="draft",
        confidence_score=float(card.get("confidence_score", 50)),
        predicted_open_rate=float(card.get("predicted_open_rate", 0.3)),
        predicted_click_rate=float(card.get("predicted_click_rate", 0.1)),
        predicted_revenue=float(card.get("predicted_revenue", 10000)),
        confidence_card=card
    )
    db.add(campaign)
    await db.flush()

    # Step 9: Save prediction record
    prediction = CampaignPrediction(
        campaign_id=campaign.id,
        predicted_open_rate=float(card.get("predicted_open_rate", 0.3)),
        predicted_click_rate=float(card.get("predicted_click_rate", 0.1)),
        predicted_revenue=float(card.get("predicted_revenue", 10000))
    )
    db.add(prediction)
    await db.commit()
    await db.refresh(campaign)

    return {
        "campaign": {
            "id": campaign.id,
            "name": req.intent[:100],
            "intent": campaign.intent,
            "channel": campaign.channel,
            "status": campaign.status,
            "audience_size": audience_size,
            "confidence_card": card,
            "sample_profiles": sample_profiles
        }
    }


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()

    if not campaign:
        raise HTTPException(404, "Campaign not found")
    if campaign.status == "active":
        raise HTTPException(400, "Campaign already sent")

    matched = await run_segment_query(campaign.segment_query, db)
    matched = matched[:20]
    channel_stub_url = os.getenv("CHANNEL_STUB_URL", "http://localhost:8001")

    dispatched = 0
    for customer in matched:
        # Get message from confidence card
        variant_a = campaign.confidence_card.get("message_variant_a", {})
        template = variant_a.get("text", "Hi {name}, we have something special for you!")
        message = template.replace("{name}", customer.name.split()[0])

        comm = Communication(
            campaign_id=campaign.id,
            customer_id=customer.id,
            channel=campaign.channel,
            status="dispatched",
            message_text=message,
            sent_at=datetime.utcnow()
        )
        db.add(comm)
        await db.flush()

        # Fire and forget — dispatch to channel stub
        asyncio.create_task(
            dispatch_to_stub(channel_stub_url, comm.id, customer.phone, message, campaign.channel)
        )
        dispatched += 1

    campaign.status = "active"
    await db.commit()

    return {"dispatched": dispatched, "campaign_id": campaign_id}


async def dispatch_to_stub(stub_url, comm_id, recipient, message, channel):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{stub_url}/send",
                json={
                    "communication_id": comm_id,
                    "recipient": recipient,
                    "message": message,
                    "channel": channel
                },
                timeout=10
            )
        except Exception as e:
            print(f"Channel stub dispatch error for {comm_id}: {e}")


@router.get("/campaigns")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    stmt = select(Campaign).order_by(Campaign.created_at.desc())
    campaigns = (await db.execute(stmt)).scalars().all()

    result = []
    for c in campaigns:
        comms = (await db.execute(
            select(Communication).where(Communication.campaign_id == c.id)
        )).scalars().all()

        total = len(comms)
        delivered = sum(1 for x in comms if x.status in ["delivered", "opened", "clicked", "converted"])
        converted = sum(1 for x in comms if x.status == "converted")

        result.append({
            "id": c.id,
            "name": c.name,
            "intent": c.intent,
            "channel": c.channel,
            "status": c.status,
            "confidence_score": c.confidence_score,
            "total_sent": total,
            "delivered": delivered,
            "converted": converted,
            "created_at": c.created_at.isoformat()
        })

    return {"campaigns": result}


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    comms = (await db.execute(
        select(Communication).where(Communication.campaign_id == campaign_id)
    )).scalars().all()

    total = len(comms)
    delivered = sum(1 for c in comms if c.status in ["delivered", "opened", "clicked", "converted"])
    opened = sum(1 for c in comms if c.status in ["opened", "clicked", "converted"])
    clicked = sum(1 for c in comms if c.status in ["clicked", "converted"])
    converted = sum(1 for c in comms if c.status == "converted")
    revenue = sum(c.revenue_attributed for c in comms)

    return {
        "id": campaign.id,
        "intent": campaign.intent,
        "channel": campaign.channel,
        "status": campaign.status,
        "confidence_score": campaign.confidence_score,
        "confidence_card": campaign.confidence_card,
        "predicted_open_rate": campaign.predicted_open_rate,
        "predicted_click_rate": campaign.predicted_click_rate,
        "predicted_revenue": campaign.predicted_revenue,
        "stats": {
            "total": total,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked,
            "converted": converted,
            "revenue": round(revenue, 2),
            "open_rate": round(opened / total, 3) if total else 0,
            "click_rate": round(clicked / total, 3) if total else 0
        }
    }


@router.get("/campaigns/{campaign_id}/events")
async def campaign_events(campaign_id: str, db: AsyncSession = Depends(get_db)):
    async def event_stream():
        seen_event_ids = set()

        for _ in range(150):
            await asyncio.sleep(2)

            comms = (await db.execute(
                select(Communication).where(Communication.campaign_id == campaign_id)
            )).scalars().all()

            if not comms:
                yield f"data: {json.dumps({'event_type': 'waiting', 'narrative': 'Waiting for campaign dispatch...'})}\n\n"
                continue

            total = len(comms)
            delivered = sum(1 for c in comms if c.status in ["delivered","opened","clicked","converted"])
            opened = sum(1 for c in comms if c.status in ["opened","clicked","converted"])
            clicked = sum(1 for c in comms if c.status in ["clicked","converted"])
            converted = sum(1 for c in comms if c.status == "converted")
            revenue = sum(c.revenue_attributed for c in comms)

            # Get ALL events, not just new ones — send unseen ones
            events = (await db.execute(
                select(MessageEvent)
                .where(MessageEvent.communication_id.in_([c.id for c in comms]))
                .order_by(MessageEvent.received_at.asc())
            )).scalars().all()

            new_events = [e for e in events if e.id not in seen_event_ids]

            for e in new_events:
                seen_event_ids.add(e.id)
                narrative = build_narrative(
                    e.event_type, delivered, opened, clicked, converted, revenue, total
                )
                data = json.dumps({
                    "event_type": e.event_type,
                    "narrative": narrative,
                    "stats": {
                        "total": total,
                        "delivered": delivered,
                        "opened": opened,
                        "clicked": clicked,
                        "converted": converted,
                        "revenue": round(revenue, 2)
                    }
                })
                yield f"data: {data}\n\n"

            # Send a heartbeat so frontend knows connection is alive
            # Only send heartbeat if stats changed
            yield f"data: {json.dumps({'event_type': 'heartbeat', 'stats': {'total': total, 'delivered': delivered, 'opened': opened, 'clicked': clicked, 'converted': converted, 'revenue': round(revenue, 2)}})}\n\n" 
            # Check completion
            terminal = {"delivered", "opened", "clicked", "converted", "failed"}
            all_done = all(c.status in terminal for c in comms) and total > 0

            if all_done and len(seen_event_ids) > 0:
                yield f"data: {json.dumps({'event_type': 'complete', 'narrative': f'Campaign complete. {converted} conversions, ₹{revenue:,.0f} attributed revenue.', 'stats': {'total': total, 'delivered': delivered, 'opened': opened, 'clicked': clicked, 'converted': converted, 'revenue': round(revenue, 2)}})}\n\n"
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


def build_narrative(event_type, delivered, opened, clicked, converted, revenue, total):
    pct = lambda n: round(n/total*100) if total else 0
    if event_type == "delivered":
        return f"✓ {delivered} of {total} delivered ({pct(delivered)}% delivery rate)"
    elif event_type == "opened":
        return f"👁 {opened} customers opened — {pct(opened)}% open rate"
    elif event_type == "clicked":
        return f"🔗 {clicked} clicked through — {pct(clicked)}% click rate"
    elif event_type == "converted":
        return f"🛒 {converted} orders placed — ₹{revenue:,.0f} revenue attributed"
    elif event_type == "failed":
        failed = total - delivered
        return f"⚠ {failed} messages failed to deliver"
    return f"Event: {event_type}"


@router.get("/campaigns/{campaign_id}/postmortem")
async def get_postmortem(campaign_id: str, db: AsyncSession = Depends(get_db)):
    from services.ai_agent import generate_postmortem

    campaign = (await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )).scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    comms = (await db.execute(
        select(Communication).where(Communication.campaign_id == campaign_id)
    )).scalars().all()

    total = len(comms)
    if total == 0:
        raise HTTPException(400, "No communications found — send the campaign first")
    delivered = sum(1 for c in comms if c.status in ["delivered", "opened", "clicked", "converted", "failed"])
    if delivered == 0:
        raise HTTPException(400, "Callbacks not received yet. Wait 30-60 seconds after sending and try again.")
    opened = sum(1 for c in comms if c.status in ["opened", "clicked", "converted"])
    clicked = sum(1 for c in comms if c.status in ["clicked", "converted"])
    converted = sum(1 for c in comms if c.status == "converted")
    revenue = sum(c.revenue_attributed for c in comms)
    
    actuals = {
        "open_rate": round(opened / total, 3),
        "click_rate": round(clicked / total, 3),
        "revenue": round(revenue, 2),
        "converted": converted,
        "total_sent": total
    }
    predictions = {
        "open_rate": campaign.predicted_open_rate,
        "click_rate": campaign.predicted_click_rate,
        "revenue": campaign.predicted_revenue
    }

    postmortem = await generate_postmortem(campaign.intent, predictions, actuals)

    # Save to DB
    pred = (await db.execute(
        select(CampaignPrediction).where(CampaignPrediction.campaign_id == campaign_id)
    )).scalar_one_or_none()

    if pred:
        pred.actual_open_rate = actuals["open_rate"]
        pred.actual_click_rate = actuals["click_rate"]
        pred.actual_revenue = revenue
        pred.post_mortem_text = json.dumps(postmortem)
        await db.commit()

    return {
        "postmortem": postmortem,
        "predictions": predictions,
        "actuals": actuals
    }