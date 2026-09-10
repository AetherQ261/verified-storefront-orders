import hashlib
import hmac
import secrets
from dataclasses import dataclass
from html import escape

from .infrai_email import InfraiEmailClient
from .models import (
    CheckoutRequest,
    CustomerOrderUpdate,
    FulfillmentStatus,
    Receipt,
    SignupRequest,
    SignupResult,
    VerificationResult,
)


@dataclass
class Customer:
    customer_id: str
    email: str
    email_verified: bool = False


class StorefrontWorkflow:
    def __init__(self, email_client: InfraiEmailClient, signing_secret: str) -> None:
        self.email_client = email_client
        self.signing_secret = signing_secret.encode("utf-8")
        self.customers: dict[str, Customer] = {}
        self.orders: dict[str, CustomerOrderUpdate] = {}

    def signup(self, signup: SignupRequest, public_base_url: str) -> SignupResult:
        customer_id = secrets.token_urlsafe(12)
        customer = Customer(customer_id=customer_id, email=str(signup.email))
        self.customers[customer_id] = customer
        token = self._token(customer_id)
        verification_url = f"{public_base_url}/verify-email?customer_id={customer_id}&token={token}"
        sent = self.email_client.send(
            to=customer.email,
            subject="Verify your email for Northwind Shop",
            html=(
                f"<p>Hi {escape(signup.display_name)},</p>"
                f'<p><a href="{escape(verification_url)}">Verify your email</a> to continue to checkout.</p>'
            ),
            idempotency_key=f"signup-verification:{customer_id}",
        )
        return SignupResult(
            customer_id=customer_id,
            email=customer.email,
            email_verified=False,
            verification_message_id=sent.message_id,
        )

    def verify_email(self, customer_id: str, token: str) -> VerificationResult:
        customer = self._customer(customer_id)
        if not hmac.compare_digest(token, self._token(customer_id)):
            raise ValueError("Invalid verification token")
        customer.email_verified = True
        return VerificationResult(customer_id=customer_id, email_verified=True)

    def checkout(self, checkout: CheckoutRequest) -> CustomerOrderUpdate:
        customer = self._customer(checkout.customer_id)
        if not customer.email_verified:
            raise PermissionError("Verify the customer email before checkout")
        order_id = secrets.token_urlsafe(10)
        total = sum(line.quantity * line.unit_price_cents for line in checkout.lines)
        update = CustomerOrderUpdate(
            order_id=order_id,
            customer_id=customer.customer_id,
            fulfillment=FulfillmentStatus.pending,
            receipt=Receipt(receipt_id=f"receipt-{order_id}", total_cents=total),
        )
        self.orders[order_id] = update
        return update

    def _token(self, customer_id: str) -> str:
        return hmac.new(self.signing_secret, customer_id.encode("utf-8"), hashlib.sha256).hexdigest()

    def _customer(self, customer_id: str) -> Customer:
        try:
            return self.customers[customer_id]
        except KeyError as exc:
            raise LookupError("Customer not found") from exc

