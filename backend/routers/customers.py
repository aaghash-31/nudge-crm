from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Customer, Order
from datetime import datetime

router = APIRouter()



@router.get("/customers")
async def list_customers(
    channel: str = Query(None),
    min_days_inactive: int = Query(None),
    max_days_inactive: int = Query(None),
    min_orders: int = Query(None),
    min_spend: float = Query(None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Customer)
    if channel:
        stmt = stmt.where(Customer.channel_preference == channel)

    customers = (await db.execute(stmt.limit(200))).scalars().all()

    result = []
    for c in customers:
        orders_stmt = select(Order).where(Order.customer_id == c.id)
        orders = (await db.execute(orders_stmt)).scalars().all()

        total_spend = sum(o.amount for o in orders)
        last_order = max((o.created_at for o in orders), default=None)
        days_inactive = (datetime.utcnow() - last_order).days if last_order else 999
        total_orders = len(orders)

        # Apply filters
        if min_days_inactive is not None and days_inactive < min_days_inactive:
            continue
        if max_days_inactive is not None and days_inactive > max_days_inactive:
            continue
        if min_orders is not None and total_orders < min_orders:
            continue
        if min_spend is not None and total_spend < min_spend:
            continue

        result.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "channel_preference": c.channel_preference,
            "total_orders": total_orders,
            "total_spend": round(total_spend, 2),
            "days_inactive": days_inactive,
            "last_order_date": last_order.isoformat() if last_order else None,
            "tags": c.tags
        })

        if len(result) >= limit:
            break

    return {"customers": result, "count": len(result)}