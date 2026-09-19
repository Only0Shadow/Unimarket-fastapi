"""
Tests for the payment flow, exercised end-to-end against the mock gateway
(PAYMENT_GATEWAY defaults to "mock" in tests -- no network, no live keys).
"""
from app.orders.models import Order, OrderStatus
from app.payments.gateways.mock import MockGateway
from app.payments.models import Payment, PaymentStatus
from tests.test_cart_and_orders import make_product, register


def _place_order(client, db_session, username="payer1", email=None):
    product = make_product(db_session, quantity=10, price=1000.0, name=f"Product for {username}")
    register(client, username, email or f"{username}@test.com")
    client.post("/cart/add", data={"product_id": product.id, "quantity": 2})
    client.post("/checkout", data={
        "recipient_name": "Payer", "phone_number": "08000000000",
        "university": "UniLag", "hostel": "Hall C",
    })
    return db_session.query(Order).order_by(Order.id.desc()).first()


def test_order_gets_a_pending_payment_record(client, db_session):
    order = _place_order(client, db_session, "payer1")
    payment = db_session.query(Payment).filter(Payment.order_id == order.id).first()
    assert payment is not None
    assert payment.status == PaymentStatus.NOT_STARTED
    assert payment.amount == order.total


def test_starting_payment_redirects_to_gateway_checkout(client, db_session):
    order = _place_order(client, db_session, "payer2")
    response = client.get(f"/payments/orders/{order.id}/pay", follow_redirects=False)
    assert response.status_code == 303
    assert "/payments/mock-checkout/" in response.headers["location"]

    db_session.refresh(order)
    payment = db_session.query(Payment).filter(Payment.order_id == order.id).first()
    assert payment.status == PaymentStatus.PENDING
    assert payment.gateway == "mock"
    assert payment.gateway_reference is not None


def test_successful_mock_payment_marks_order_confirmed(client, db_session):
    order = _place_order(client, db_session, "payer3")
    client.get(f"/payments/orders/{order.id}/pay", follow_redirects=False)
    payment = db_session.query(Payment).filter(Payment.order_id == order.id).first()

    response = client.post(
        f"/payments/mock-checkout/{payment.gateway_reference}/resolve",
        data={"outcome": "success"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/payments/verify/{payment.gateway_reference}"

    verify_response = client.get(f"/payments/verify/{payment.gateway_reference}", follow_redirects=False)
    assert f"/orders/{order.id}" in verify_response.headers["location"]
    assert "paid=1" in verify_response.headers["location"]

    db_session.refresh(order)
    db_session.refresh(payment)
    assert payment.status == PaymentStatus.PAID
    assert payment.verified_at is not None
    assert order.status == OrderStatus.CONFIRMED


def test_failed_mock_payment_does_not_confirm_order(client, db_session):
    order = _place_order(client, db_session, "payer4")
    client.get(f"/payments/orders/{order.id}/pay", follow_redirects=False)
    payment = db_session.query(Payment).filter(Payment.order_id == order.id).first()

    client.post(f"/payments/mock-checkout/{payment.gateway_reference}/resolve", data={"outcome": "failed"})
    verify_response = client.get(f"/payments/verify/{payment.gateway_reference}", follow_redirects=False)
    assert "payment_failed=1" in verify_response.headers["location"]

    db_session.refresh(order)
    db_session.refresh(payment)
    assert payment.status == PaymentStatus.FAILED
    assert order.status == OrderStatus.PENDING


def test_payment_status_endpoint_requires_ownership(client, db_session):
    order = _place_order(client, db_session, "payer5")
    client.post("/logout")
    register(client, "intruder", "intruder@test.com")

    response = client.get(f"/payments/orders/{order.id}/status")
    assert response.status_code == 404


def test_already_paid_order_cannot_be_paid_again(client, db_session):
    order = _place_order(client, db_session, "payer6")
    client.get(f"/payments/orders/{order.id}/pay", follow_redirects=False)
    payment = db_session.query(Payment).filter(Payment.order_id == order.id).first()
    MockGateway.resolve(payment.gateway_reference, "success")
    client.get(f"/payments/verify/{payment.gateway_reference}")

    response = client.get(f"/payments/orders/{order.id}/pay", follow_redirects=False)
    assert response.status_code == 303
    assert "payment_error" in response.headers["location"]
