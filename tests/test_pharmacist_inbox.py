from app.models import Customer
from app.services.pharmacist_inbox import add_customer_message, add_pharmacist_reply, get_thread


async def _customer(session, tid=555):
    c = Customer(telegram_id=tid, full_name="Test Customer")
    session.add(c)
    await session.flush()
    return c


async def test_first_message_creates_ticket(session):
    c = await _customer(session)
    ticket, created = await add_customer_message(session, c.id, c.telegram_id, "Is this safe?")
    await session.flush()
    assert created is True
    assert ticket.question == "Is this safe?"
    assert ticket.is_answered is False
    thread = await get_thread(session, ticket.id)
    assert len(thread) == 1
    assert thread[0].sender == "customer"


async def test_followup_appends_to_open_ticket_not_new_one(session):
    c = await _customer(session)
    ticket1, created1 = await add_customer_message(session, c.id, c.telegram_id, "First question")
    await session.flush()
    ticket2, created2 = await add_customer_message(session, c.id, c.telegram_id, "Follow-up question")
    await session.flush()

    assert created1 is True
    assert created2 is False
    assert ticket1.id == ticket2.id
    thread = await get_thread(session, ticket1.id)
    assert len(thread) == 2
    assert [m.body for m in thread] == ["First question", "Follow-up question"]


async def test_reply_marks_answered_and_appends_thread(session):
    c = await _customer(session)
    ticket, _ = await add_customer_message(session, c.id, c.telegram_id, "Question")
    await session.flush()
    await add_pharmacist_reply(session, ticket, 999, "Here's the answer", "lead_pharmacist:999")
    await session.flush()

    assert ticket.is_answered is True
    assert ticket.answer == "Here's the answer"
    thread = await get_thread(session, ticket.id)
    assert len(thread) == 2
    assert thread[-1].sender == "pharmacist"


async def test_new_ticket_after_answered_one(session):
    """Once a ticket is answered, the next message should open a fresh ticket."""
    c = await _customer(session)
    ticket1, _ = await add_customer_message(session, c.id, c.telegram_id, "Q1")
    await session.flush()
    await add_pharmacist_reply(session, ticket1, 999, "A1", "lead_pharmacist:999")
    await session.flush()

    ticket2, created = await add_customer_message(session, c.id, c.telegram_id, "Q2")
    await session.flush()
    assert created is True
    assert ticket2.id != ticket1.id
