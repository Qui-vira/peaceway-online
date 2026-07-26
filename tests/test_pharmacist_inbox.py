from app.models import Customer
from app.services.pharmacist_inbox import add_customer_message, add_pharmacist_reply, get_thread


async def _customer(db_session, tid=555):
    c = Customer(telegram_id=tid, full_name="Test Customer")
    db_session.add(c)
    await db_session.flush()
    return c


async def test_first_message_creates_ticket(db_session):
    c = await _customer(db_session)
    ticket, created = await add_customer_message(db_session, c.id, c.telegram_id, "Is this safe?")
    await db_session.flush()
    assert created is True
    assert ticket.question == "Is this safe?"
    assert ticket.is_answered is False
    thread = await get_thread(db_session, ticket.id)
    assert len(thread) == 1
    assert thread[0].sender == "customer"


async def test_followup_appends_to_open_ticket_not_new_one(db_session):
    c = await _customer(db_session)
    ticket1, created1 = await add_customer_message(db_session, c.id, c.telegram_id, "First question")
    await db_session.flush()
    ticket2, created2 = await add_customer_message(db_session, c.id, c.telegram_id, "Follow-up question")
    await db_session.flush()

    assert created1 is True
    assert created2 is False
    assert ticket1.id == ticket2.id
    thread = await get_thread(db_session, ticket1.id)
    assert len(thread) == 2
    assert [m.body for m in thread] == ["First question", "Follow-up question"]


async def test_reply_marks_answered_and_appends_thread(db_session):
    c = await _customer(db_session)
    ticket, _ = await add_customer_message(db_session, c.id, c.telegram_id, "Question")
    await db_session.flush()
    await add_pharmacist_reply(db_session, ticket, 999, "Here's the answer", "lead_pharmacist:999")
    await db_session.flush()

    assert ticket.is_answered is True
    assert ticket.answer == "Here's the answer"
    thread = await get_thread(db_session, ticket.id)
    assert len(thread) == 2
    assert thread[-1].sender == "pharmacist"


async def test_new_ticket_after_answered_one(db_session):
    """Once a ticket is answered, the next message should open a fresh ticket."""
    c = await _customer(db_session)
    ticket1, _ = await add_customer_message(db_session, c.id, c.telegram_id, "Q1")
    await db_session.flush()
    await add_pharmacist_reply(db_session, ticket1, 999, "A1", "lead_pharmacist:999")
    await db_session.flush()

    ticket2, created = await add_customer_message(db_session, c.id, c.telegram_id, "Q2")
    await db_session.flush()
    assert created is True
    assert ticket2.id != ticket1.id
