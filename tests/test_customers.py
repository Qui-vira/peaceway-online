from sqlalchemy import select

from app.models import CustomerContactEvent, CustomerPreferences
from app.services.customers import (
    HIGH_VALUE_SOURCES,
    get_or_create_customer,
    is_valid_email,
    remove_email,
    save_email,
)


def test_email_validation():
    assert is_valid_email("name@example.com") is True
    assert is_valid_email("a.b+c@sub.example.co") is True
    assert is_valid_email("not-an-email") is False
    assert is_valid_email("missing@domain") is False
    assert is_valid_email("@nodomain.com") is False
    assert is_valid_email("spaces in@example.com") is False


async def test_get_or_create_customer_creates_preferences(session):
    customer = await get_or_create_customer(session, 12345, "Ada")
    await session.flush()
    prefs = await session.get(CustomerPreferences, customer.id)
    assert prefs is not None
    # Transactional updates default ON, promotions/community default OFF.
    assert prefs.receive_order_updates is True
    assert prefs.receive_promotions is False
    assert prefs.receive_community_updates is False


async def test_get_or_create_is_idempotent(session):
    c1 = await get_or_create_customer(session, 999, "First")
    await session.flush()
    c2 = await get_or_create_customer(session, 999, "Second call")
    await session.flush()
    assert c1.id == c2.id


async def test_save_email_records_contact_event(session):
    customer = await get_or_create_customer(session, 222, "Bob")
    await session.flush()
    await save_email(session, customer, "bob@example.com", "order", 222)
    await session.flush()

    assert customer.email == "bob@example.com"
    assert customer.email_verified is False
    assert customer.email_source == "order"
    assert customer.email_collected_at is not None

    events = (
        await session.execute(
            select(CustomerContactEvent).where(CustomerContactEvent.customer_id == customer.id)
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "added"
    assert events[0].new_email == "bob@example.com"


async def test_updating_email_records_updated_event(session):
    customer = await get_or_create_customer(session, 333, "Cee")
    await session.flush()
    await save_email(session, customer, "first@example.com", "order", 333)
    await session.flush()
    await save_email(session, customer, "second@example.com", "profile", 333)
    await session.flush()

    events = (
        await session.execute(
            select(CustomerContactEvent)
            .where(CustomerContactEvent.customer_id == customer.id)
            .order_by(CustomerContactEvent.created_at)
        )
    ).scalars().all()
    assert [e.event_type for e in events] == ["added", "updated"]
    assert events[1].old_email == "first@example.com"
    assert events[1].new_email == "second@example.com"


async def test_remove_email_clears_field_and_logs_event(session):
    customer = await get_or_create_customer(session, 444, "Dee")
    await session.flush()
    await save_email(session, customer, "dee@example.com", "order", 444)
    await session.flush()
    await remove_email(session, customer, 444)
    await session.flush()

    assert customer.email is None
    events = (
        await session.execute(
            select(CustomerContactEvent).where(CustomerContactEvent.customer_id == customer.id)
        )
    ).scalars().all()
    assert events[-1].event_type == "removed"
    assert events[-1].old_email == "dee@example.com"
    assert events[-1].new_email is None


def test_high_value_sources_match_spec():
    assert HIGH_VALUE_SOURCES == {"payment", "product_request", "pharmacist", "follow_up"}
