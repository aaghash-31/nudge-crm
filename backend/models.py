import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

def new_uuid():
    return str(uuid.uuid4())

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=new_uuid
    )
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(200))
    channel_preference: Mapped[str] = mapped_column(String(20), default="WhatsApp")
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")
    communications: Mapped[list["Communication"]] = relationship(
        "Communication", back_populates="customer"
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=new_uuid
    )
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("customers.id", ondelete="CASCADE")
    )
    amount: Mapped[float] = mapped_column(Float)
    items: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=new_uuid
    )
    name: Mapped[str] = mapped_column(String(300))
    intent: Mapped[str] = mapped_column(Text)
    segment_query: Mapped[dict] = mapped_column(JSONB, default=dict)
    channel: Mapped[str] = mapped_column(String(20), default="WhatsApp")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    confidence_score: Mapped[float] = mapped_column(Float, default=0)
    predicted_open_rate: Mapped[float] = mapped_column(Float, default=0)
    predicted_click_rate: Mapped[float] = mapped_column(Float, default=0)
    predicted_revenue: Mapped[float] = mapped_column(Float, default=0)
    confidence_card: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    communications: Mapped[list["Communication"]] = relationship(
        "Communication", back_populates="campaign"
    )
    prediction: Mapped["CampaignPrediction"] = relationship(
        "CampaignPrediction", back_populates="campaign", uselist=False
    )


class Communication(Base):
    __tablename__ = "communications"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=new_uuid
    )
    campaign_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("customers.id", ondelete="CASCADE")
    )
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    message_text: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    clicked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    converted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    revenue_attributed: Mapped[float] = mapped_column(Float, default=0)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="communications")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="communications")
    events: Mapped[list["MessageEvent"]] = relationship(
        "MessageEvent", back_populates="communication"
    )


class MessageEvent(Base):
    __tablename__ = "message_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_event_id"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=new_uuid
    )
    communication_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("communications.id", ondelete="CASCADE")
    )
    event_type: Mapped[str] = mapped_column(String(30))
    event_id: Mapped[str] = mapped_column(String(200), unique=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    communication: Mapped["Communication"] = relationship(
        "Communication", back_populates="events"
    )


class CampaignPrediction(Base):
    __tablename__ = "campaign_predictions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=new_uuid
    )
    campaign_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("campaigns.id", ondelete="CASCADE"), unique=True
    )
    predicted_open_rate: Mapped[float] = mapped_column(Float, default=0)
    predicted_click_rate: Mapped[float] = mapped_column(Float, default=0)
    predicted_revenue: Mapped[float] = mapped_column(Float, default=0)
    actual_open_rate: Mapped[float] = mapped_column(Float, default=0)
    actual_click_rate: Mapped[float] = mapped_column(Float, default=0)
    actual_revenue: Mapped[float] = mapped_column(Float, default=0)
    post_mortem_text: Mapped[str] = mapped_column(Text, default="")

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="prediction")