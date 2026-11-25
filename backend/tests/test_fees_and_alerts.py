"""Fees & billing, trainer alerts (absence / overdue fees), notifications and the trainer dashboard."""
import uuid
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.config import settings as app_settings
from app.core.timezone import today_gym
from app.models.billing import FeeRecord, FeeStatus
from app.models.notification import Notification
from app.models.trainer import Trainer
from app.services.alerts import format_money, whatsapp_link
from app.services.billing import add_months, billing_period, compute_fee_status
from app.services.jobs import run_daily_jobs
from app.services.trainer_settings import get_or_create_settings

DEFAULT_PREFS = {
    "absence_streak_threshold": 3,
    "absence_monthly_threshold": 6,
    "fee_grace_days": 5,
    "fee_reminder_days": 3,
}


# ------------------------------------------------------------------ helpers

def _create_client(client, headers, name=None, phone="+91 98765 43210"):
    res = client.post(
        "/api/clients",
        json={
            "name": name or f"Fee Client {uuid.uuid4().hex[:4]}",
            "email": f"fees_{uuid.uuid4().hex[:10]}@example.com",
            "phone": phone,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _create_plan(client, headers, price="1500.00", months=1):
    res = client.post(
        "/api/fees/plans",
        json={"name": f"Plan {uuid.uuid4().hex[:6]}", "price": price, "duration_months": months},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _register_trainer(client):
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Isolated Trainer",
            "email": f"trainer_{uuid.uuid4().hex[:10]}@example.com",
            "password": "TrainerPass123!",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return body["trainer_id"], {"Authorization": f"Bearer {body['access_token']}"}


def _trainer(client, db_session, headers):
    trainer_id = client.get("/api/auth/me", headers=headers).json()["trainer_id"]
    return db_session.query(Trainer).filter(Trainer.id == trainer_id).one()


@contextmanager
def _prefs(db_session, trainer_id, **overrides):
    """Tunes the trainer's alert/billing settings directly (no settings API), then restores defaults."""
    row = get_or_create_settings(db_session, trainer_id)
    for key, value in overrides.items():
        setattr(row, key, value)
    db_session.commit()
    try:
        yield row
    finally:
        db_session.rollback()
        row = get_or_create_settings(db_session, trainer_id)
        for key, value in DEFAULT_PREFS.items():
            setattr(row, key, value)
        db_session.commit()


def _notifications(client, headers, ntype=None):
    params = {"page_size": 100}
    if ntype:
        params["type"] = ntype
    res = client.get("/api/notifications", params=params, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def _mark(client, headers, client_id, d, st):
    res = client.post("/api/attendance", json={"client_id": client_id, "date": d.isoformat(), "status": st}, headers=headers)
    assert res.status_code == 200, res.text


def _assert_trainer_only(db_session, client_id, trainer):
    """Every alert about this client belongs to the trainer: no client copies."""
    db_session.expire_all()
    rows = db_session.query(Notification).filter(Notification.client_id == client_id).all()
    assert rows, "expected at least one alert"
    assert {r.user_id for r in rows} == {trainer.user_id}
    return rows


# ------------------------------------------------------------------ pure billing logic

def test_add_months_clamps_end_of_month():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
    assert add_months(date(2026, 11, 15), 2) == date(2027, 1, 15)
    assert add_months(date(2026, 3, 31), -1) == date(2026, 2, 28)


def test_billing_periods_do_not_drift():
    anchor = date(2026, 1, 31)
    assert billing_period(anchor, 1, 0) == (date(2026, 1, 31), date(2026, 2, 27))
    assert billing_period(anchor, 1, 1) == (date(2026, 2, 28), date(2026, 3, 30))
    # Third period returns to the 31st instead of drifting to the 28th
    assert billing_period(anchor, 1, 2) == (date(2026, 3, 31), date(2026, 4, 29))
    assert billing_period(date(2026, 1, 1), 3, 1) == (date(2026, 4, 1), date(2026, 6, 30))


def test_compute_fee_status_rules():
    today = date(2026, 11, 21)

    def fee(due, paid, due_date, waived=False):
        return FeeRecord(amount_due=Decimal(due), amount_paid=Decimal(paid), due_date=due_date, is_waived=waived)

    assert compute_fee_status(fee("1000", "1000", today), today, 5) == FeeStatus.PAID
    assert compute_fee_status(fee("1000", "0", today, waived=True), today, 5) == FeeStatus.WAIVED
    assert compute_fee_status(fee("1000", "0", today - timedelta(days=6)), today, 5) == FeeStatus.OVERDUE
    assert compute_fee_status(fee("1000", "0", today - timedelta(days=5)), today, 5) == FeeStatus.PENDING
    assert compute_fee_status(fee("1000", "400", today - timedelta(days=2)), today, 5) == FeeStatus.PARTIAL
    assert compute_fee_status(fee("1000", "400", today - timedelta(days=30)), today, 5) == FeeStatus.OVERDUE
    assert compute_fee_status(fee("1000", "0", today + timedelta(days=2)), today, 5) == FeeStatus.UPCOMING


def test_whatsapp_link_and_money_formatting():
    link = whatsapp_link("98765 43210", "Hi there")
    assert link == "https://wa.me/919876543210?text=Hi%20there"
    assert whatsapp_link("+1 (555) 010-0200", "x").startswith("https://wa.me/15550100200")
    assert whatsapp_link("123", "x") is None
    assert whatsapp_link(None, "x") is None
    assert format_money(Decimal("1500"), "INR") == "₹1,500"
    assert format_money(Decimal("99.5"), "USD") == "$99.50"
    assert format_money(Decimal("10"), "AED") == "AED 10"


# ------------------------------------------------------------------ plans

def test_plan_crud_and_validation(client, trainer_auth_headers):
    plan = _create_plan(client, trainer_auth_headers, price="2000", months=3)
    assert plan["price"] == 2000.0 and plan["duration_months"] == 3 and plan["is_active"]

    dup = client.post(
        "/api/fees/plans",
        json={"name": plan["name"].upper(), "price": "100", "duration_months": 1},
        headers=trainer_auth_headers,
    )
    assert dup.status_code == 409

    for bad in ({"name": "Bad", "price": "0"}, {"name": "Bad", "price": "10", "duration_months": 0},
                {"name": "  ", "price": "10"}, {"name": "Bad", "price": "10.123"}):
        assert client.post("/api/fees/plans", json=bad, headers=trainer_auth_headers).status_code == 422

    res = client.put(f"/api/fees/plans/{plan['id']}", json={"price": "2100.50", "is_active": False}, headers=trainer_auth_headers)
    assert res.status_code == 200
    assert res.json()["price"] == 2100.5 and res.json()["is_active"] is False

    assert client.delete(f"/api/fees/plans/{plan['id']}", headers=trainer_auth_headers).status_code == 200
    assert client.delete(f"/api/fees/plans/{plan['id']}", headers=trainer_auth_headers).status_code == 404


def test_plan_in_use_cannot_be_deleted(client, trainer_auth_headers):
    plan = _create_plan(client, trainer_auth_headers)
    client_id = _create_client(client, trainer_auth_headers)
    res = client.put(f"/api/fees/clients/{client_id}/membership", json={"plan_id": plan["id"]}, headers=trainer_auth_headers)
    assert res.status_code == 200
    assert client.delete(f"/api/fees/plans/{plan['id']}", headers=trainer_auth_headers).status_code == 409


# ------------------------------------------------------------------ dues, payments, status

def test_membership_generates_dues_and_payments_flow(client, trainer_auth_headers, db_session):
    today = today_gym()
    plan = _create_plan(client, trainer_auth_headers, price="1500")
    client_id = _create_client(client, trainer_auth_headers)

    start = add_months(today, -2)
    res = client.put(
        f"/api/fees/clients/{client_id}/membership",
        json={"plan_id": plan["id"], "fee_amount": "1200", "billing_start_date": start.isoformat()},
        headers=trainer_auth_headers,
    )
    assert res.status_code == 200, res.text
    account = res.json()
    assert account["membership"]["fee_amount"] == 1200.0
    fees = sorted(account["fees"], key=lambda f: f["due_date"])
    assert [f["due_date"] for f in fees] == [start.isoformat(), add_months(start, 1).isoformat(), add_months(start, 2).isoformat()]
    assert all(f["amount_due"] == 1200.0 for f in fees)
    oldest = fees[0]
    assert oldest["status"] == "OVERDUE" and oldest["days_overdue"] > 0
    assert oldest["reminder_whatsapp_link"].startswith("https://wa.me/919876543210")
    assert account["membership"]["outstanding_amount"] == 3600.0

    # Regenerating dues is idempotent: a second daily run creates nothing new
    run_daily_jobs(db_session)
    second = run_daily_jobs(db_session)
    assert set(second) == {"dues_created", "absence_alerts", "fee_alerts", "storage_alerts"}
    assert second["dues_created"] == 0
    db_session.expire_all()
    assert db_session.query(FeeRecord).filter(FeeRecord.client_id == client_id).count() == 3

    fid = oldest["id"]
    bad = [
        {"amount": "1200.01"},
        {"amount": "0"},
        {"amount": "100", "paid_on": (today + timedelta(days=1)).isoformat()},
        {"amount": "100", "method": "BITCOIN"},
    ]
    assert client.post(f"/api/fees/{fid}/payments", json=bad[0], headers=trainer_auth_headers).status_code == 400
    assert client.post(f"/api/fees/{fid}/payments", json=bad[1], headers=trainer_auth_headers).status_code == 422
    assert client.post(f"/api/fees/{fid}/payments", json=bad[2], headers=trainer_auth_headers).status_code == 400
    assert client.post(f"/api/fees/{fid}/payments", json=bad[3], headers=trainer_auth_headers).status_code == 422

    res = client.post(f"/api/fees/{fid}/payments", json={"amount": "500", "method": "UPI", "reference": "UPI123"}, headers=trainer_auth_headers)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["amount_paid"] == 500.0 and body["balance"] == 700.0 and body["status"] == "OVERDUE"
    assert body["payments"][0]["method"] == "UPI" and body["payments"][0]["reference"] == "UPI123"

    res = client.post(f"/api/fees/{fid}/payments", json={"amount": "700"}, headers=trainer_auth_headers)
    assert res.json()["status"] == "PAID" and res.json()["balance"] == 0.0
    assert client.post(f"/api/fees/{fid}/payments", json={"amount": "1"}, headers=trainer_auth_headers).status_code == 400

    # Deleting a payment reopens the balance
    payment_id = res.json()["payments"][0]["id"]
    res = client.delete(f"/api/fees/payments/{payment_id}", headers=trainer_auth_headers)
    assert res.status_code == 200 and res.json()["amount_paid"] == 500.0 and res.json()["status"] == "OVERDUE"

    # Fee with payments cannot be deleted; waive instead
    assert client.delete(f"/api/fees/{fid}", headers=trainer_auth_headers).status_code == 409
    res = client.patch(f"/api/fees/{fees[1]['id']}", json={"is_waived": True, "notes": "Injury break"}, headers=trainer_auth_headers)
    assert res.json()["status"] == "WAIVED" and res.json()["balance"] == 0.0
    assert client.post(f"/api/fees/{fees[1]['id']}/payments", json={"amount": "10"}, headers=trainer_auth_headers).status_code == 400

    # Cannot lower amount below what is already paid
    assert client.patch(f"/api/fees/{fid}", json={"amount_due": "400"}, headers=trainer_auth_headers).status_code == 400

    # Filters
    res = client.get("/api/fees", params={"client_id": client_id, "status": "OVERDUE"}, headers=trainer_auth_headers)
    assert [f["id"] for f in res.json()["items"]] == [fid]
    res = client.get("/api/fees", params={"client_id": client_id, "status": "WAIVED"}, headers=trainer_auth_headers)
    assert res.json()["total"] == 1
    res = client.get("/api/fees", params={"client_id": client_id, "unpaid_only": True}, headers=trainer_auth_headers)
    assert res.json()["total"] == 2
    assert client.get("/api/fees", params={"month": "2026-13"}, headers=trainer_auth_headers).status_code == 400
    assert client.get("/api/fees", params={"status": "NOPE"}, headers=trainer_auth_headers).status_code == 422


def test_scheduler_generates_next_period_and_stop_membership(client, trainer_auth_headers, db_session):
    today = today_gym()
    plan = _create_plan(client, trainer_auth_headers, price="999", months=1)
    client_id = _create_client(client, trainer_auth_headers)
    client.put(
        f"/api/fees/clients/{client_id}/membership",
        json={"plan_id": plan["id"], "billing_start_date": today.isoformat()},
        headers=trainer_auth_headers,
    )
    assert db_session.query(FeeRecord).filter(FeeRecord.client_id == client_id).count() == 1

    run_daily_jobs(db_session, today=add_months(today, 1))
    db_session.expire_all()
    assert db_session.query(FeeRecord).filter(FeeRecord.client_id == client_id).count() == 2

    res = client.delete(f"/api/fees/clients/{client_id}/membership", headers=trainer_auth_headers)
    assert res.status_code == 200 and res.json()["membership"]["plan_id"] is None
    run_daily_jobs(db_session, today=add_months(today, 3))
    db_session.expire_all()
    assert db_session.query(FeeRecord).filter(FeeRecord.client_id == client_id).count() == 2


def test_fee_summary_reflects_payments(client, trainer_auth_headers):
    today = today_gym()
    month = today.strftime("%Y-%m")
    before = client.get("/api/fees/summary", params={"month": month}, headers=trainer_auth_headers).json()

    plan = _create_plan(client, trainer_auth_headers, price="1000")
    client_id = _create_client(client, trainer_auth_headers)
    fees = client.put(
        f"/api/fees/clients/{client_id}/membership",
        json={"plan_id": plan["id"], "billing_start_date": today.replace(day=1).isoformat()},
        headers=trainer_auth_headers,
    ).json()["fees"]
    client.post(f"/api/fees/{fees[0]['id']}/payments", json={"amount": "250"}, headers=trainer_auth_headers)

    after = client.get("/api/fees/summary", params={"month": month}, headers=trainer_auth_headers).json()
    assert after["billed_amount"] == pytest.approx(before["billed_amount"] + 1000)
    assert after["collected_amount"] == pytest.approx(before["collected_amount"] + 250)
    assert after["fees_due_count"] == before["fees_due_count"] + 1
    assert after["outstanding_total"] == pytest.approx(before["outstanding_total"] + 750)
    assert 0 <= after["collection_rate"] <= 100
    assert client.get("/api/fees/summary", params={"month": "bad"}, headers=trainer_auth_headers).status_code == 400


# ------------------------------------------------------------------ absence alerts

def test_absence_streak_alerts_trainer_once_per_streak(client, trainer_auth_headers, db_session):
    trainer = _trainer(client, db_session, trainer_auth_headers)
    with _prefs(db_session, trainer.id, absence_streak_threshold=3, absence_monthly_threshold=31):
        client_id = _create_client(client, trainer_auth_headers, name="Streak Tester")
        base = today_gym() - timedelta(days=20)

        def streak_alerts():
            return [n for n in _notifications(client, trainer_auth_headers, "ABSENCE_STREAK")["items"] if n["client_id"] == client_id]

        _mark(client, trainer_auth_headers, client_id, base, "ABSENT")
        _mark(client, trainer_auth_headers, client_id, base + timedelta(days=1), "ABSENT")
        assert streak_alerts() == []

        _mark(client, trainer_auth_headers, client_id, base + timedelta(days=2), "ABSENT")
        alerts = streak_alerts()
        assert len(alerts) == 1
        assert "Streak Tester" in alerts[0]["title"] and alerts[0]["severity"] == "WARNING"
        assert alerts[0]["link"] == f"/clients/{client_id}"
        assert alerts[0]["client_name"] == "Streak Tester"
        assert alerts[0]["whatsapp_link"].startswith("https://wa.me/919876543210?text=")
        assert "email_status" not in alerts[0]

        # Same streak growing does not re-alert
        _mark(client, trainer_auth_headers, client_id, base + timedelta(days=3), "ABSENT")
        assert len(streak_alerts()) == 1

        # Streak broken, then a new streak alerts again
        _mark(client, trainer_auth_headers, client_id, base + timedelta(days=4), "PRESENT")
        for i in range(5, 8):
            _mark(client, trainer_auth_headers, client_id, base + timedelta(days=i), "ABSENT")
        assert len(streak_alerts()) == 2

        # Alerts exist only for the trainer
        rows = _assert_trainer_only(db_session, client_id, trainer)
        assert len(rows) == 2


def test_monthly_absence_alert(client, trainer_auth_headers, db_session):
    trainer = _trainer(client, db_session, trainer_auth_headers)
    with _prefs(db_session, trainer.id, absence_streak_threshold=30, absence_monthly_threshold=2):
        client_id = _create_client(client, trainer_auth_headers)
        today = today_gym()
        first = today.replace(day=1)
        _mark(client, trainer_auth_headers, client_id, first, "ABSENT")
        # Re-marking the same day does not double count
        _mark(client, trainer_auth_headers, client_id, first, "ABSENT")
        items = [n for n in _notifications(client, trainer_auth_headers, "ABSENCE_MONTHLY")["items"] if n["client_id"] == client_id]
        assert items == []
        second = first + timedelta(days=1) if today.day > 1 else first
        if second != first:
            _mark(client, trainer_auth_headers, client_id, second, "PRESENT")
            _mark(client, trainer_auth_headers, client_id, second, "ABSENT")
            items = [n for n in _notifications(client, trainer_auth_headers, "ABSENCE_MONTHLY")["items"] if n["client_id"] == client_id]
            assert len(items) == 1
            assert items[0]["severity"] == "WARNING"
            rows = _assert_trainer_only(db_session, client_id, trainer)
            assert [r.type for r in rows] == ["ABSENCE_MONTHLY"]


# ------------------------------------------------------------------ fee alerts

def test_fee_overdue_alerts_trainer_only_and_idempotent(client, trainer_auth_headers, db_session):
    today = today_gym()
    trainer = _trainer(client, db_session, trainer_auth_headers)
    plan = _create_plan(client, trainer_auth_headers)
    client_id = _create_client(client, trainer_auth_headers, name="Late Payer")
    res = client.put(
        f"/api/fees/clients/{client_id}/membership",
        json={"plan_id": plan["id"], "billing_start_date": add_months(today, -1).isoformat()},
        headers=trainer_auth_headers,
    )
    assert res.status_code == 200
    # One overdue period and one current period (due now, within grace)
    statuses = sorted(f["status"] for f in res.json()["fees"])
    assert len(statuses) == 2 and "OVERDUE" in statuses

    first = run_daily_jobs(db_session)
    assert set(first) == {"dues_created", "absence_alerts", "fee_alerts", "storage_alerts"}
    assert first["fee_alerts"] >= 1
    trainer_overdue = [n for n in _notifications(client, trainer_auth_headers, "FEE_OVERDUE")["items"] if n["client_id"] == client_id]
    assert len(trainer_overdue) == 1
    assert trainer_overdue[0]["severity"] == "CRITICAL"
    assert trainer_overdue[0]["link"] == "/fees"
    assert "Late Payer" in trainer_overdue[0]["title"]
    assert trainer_overdue[0]["fee_id"] is not None

    # Only the trainer is alerted, and only about the overdue fee (no "due soon" reminders)
    rows = _assert_trainer_only(db_session, client_id, trainer)
    assert [r.type for r in rows] == ["FEE_OVERDUE"]

    second = run_daily_jobs(db_session)
    assert second["fee_alerts"] == 0
    again = [n for n in _notifications(client, trainer_auth_headers, "FEE_OVERDUE")["items"] if n["client_id"] == client_id]
    assert len(again) == 1


# ------------------------------------------------------------------ notification read state

def test_notification_read_state_and_isolation(client, trainer_auth_headers):
    client_id = _create_client(client, trainer_auth_headers)
    base = today_gym() - timedelta(days=40)
    for i in range(3):
        _mark(client, trainer_auth_headers, client_id, base + timedelta(days=i), "ABSENT")

    trainer_list = _notifications(client, trainer_auth_headers)
    target = next(n for n in trainer_list["items"] if n["client_id"] == client_id)
    assert target["is_read"] is False
    unread_before = client.get("/api/notifications/unread-count", headers=trainer_auth_headers).json()["count"]
    assert unread_before >= 1
    assert trainer_list["unread_count"] == unread_before

    # Another trainer can neither see nor read this trainer's notification
    _, other_headers = _register_trainer(client)
    other_list = _notifications(client, other_headers)
    assert other_list["total"] == 0 and other_list["items"] == []
    assert client.post(f"/api/notifications/{target['id']}/read", headers=other_headers).status_code == 404
    assert client.post("/api/notifications/read-all", headers=other_headers).json()["count"] == 0
    assert client.get("/api/notifications/unread-count", headers=other_headers).json()["count"] == 0
    # ...and the other trainer's read-all did not touch ours
    assert client.get("/api/notifications/unread-count", headers=trainer_auth_headers).json()["count"] == unread_before

    res = client.post(f"/api/notifications/{target['id']}/read", headers=trainer_auth_headers)
    assert res.status_code == 200 and res.json()["is_read"] is True and res.json()["read_at"]
    assert client.get("/api/notifications/unread-count", headers=trainer_auth_headers).json()["count"] == unread_before - 1
    unread_ids = [n["id"] for n in client.get("/api/notifications", params={"unread_only": True, "page_size": 100}, headers=trainer_auth_headers).json()["items"]]
    assert target["id"] not in unread_ids

    # Read-all clears the rest
    assert client.post("/api/notifications/read-all", headers=trainer_auth_headers).json()["count"] == 0
    assert client.get("/api/notifications/unread-count", headers=trainer_auth_headers).json()["count"] == 0
    assert client.post("/api/notifications/999999/read", headers=trainer_auth_headers).status_code == 404


# ------------------------------------------------------------------ dashboard

def test_dashboard_counts_attendance_billing_and_upcoming_dues(client, db_session):
    today = today_gym()
    trainer_id, headers = _register_trainer(client)

    empty = client.get("/api/dashboard/trainer", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["total_clients"] == 0 and empty.json()["upcoming_dues"] == []

    c1 = _create_client(client, headers, name="Dash Payer")
    c2 = _create_client(client, headers, name="Dash Absent")
    c3 = _create_client(client, headers, name="Dash Archived")
    c4 = _create_client(client, headers, name="Dash Inactive")
    assert client.post(f"/api/clients/{c3}/archive", headers=headers).status_code == 200
    assert client.delete(f"/api/clients/{c4}", headers=headers).status_code == 200

    _mark(client, headers, c1, today, "PRESENT")
    _mark(client, headers, c2, today, "ABSENT")

    plan = _create_plan(client, headers, price="1000")
    account = client.put(
        f"/api/fees/clients/{c1}/membership",
        json={"plan_id": plan["id"], "billing_start_date": add_months(today, -1).isoformat()},
        headers=headers,
    )
    assert account.status_code == 200
    fees = account.json()["fees"]
    overdue_fee = next(f for f in fees if f["status"] == "OVERDUE")
    current_fee = next(f for f in fees if f["id"] != overdue_fee["id"])
    paid = client.post(f"/api/fees/{current_fee['id']}/payments", json={"amount": "300"}, headers=headers)
    assert paid.status_code == 201

    # The daily job raises exactly one (unread) overdue alert for this trainer
    assert run_daily_jobs(db_session, trainer_id=trainer_id)["fee_alerts"] == 1

    res = client.get("/api/dashboard/trainer", headers=headers)
    assert res.status_code == 200
    dash = res.json()
    assert dash["total_clients"] == 4
    assert dash["active_clients"] == 2
    # Roster is clients currently training: c1 present, c2 absent; archived c3 and inactive c4 are left out
    assert dash["today_attendance"] == {"present": 1, "absent": 1, "late": 0, "unmarked": 0}

    billing = dash["billing"]
    assert billing["currency"] == app_settings.DEFAULT_CURRENCY[:3].upper()
    assert billing["outstanding_total"] == pytest.approx(1700.0)
    assert billing["overdue_total"] == pytest.approx(1000.0)
    assert billing["overdue_count"] == 1
    assert billing["collected_this_month"] == pytest.approx(300.0)
    assert billing["unread_alerts"] == 1

    assert dash["upcoming_dues"] == [
        {
            "fee_id": current_fee["id"],
            "client_id": c1,
            "client_name": "Dash Payer",
            "due_date": current_fee["due_date"],
            "balance": 700.0,
            "status": "PARTIAL",
        }
    ]
    assert {c["name"] for c in dash["recent_clients"]} == {"Dash Payer", "Dash Absent", "Dash Archived", "Dash Inactive"}
