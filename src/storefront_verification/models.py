from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=80)


class SignupResult(BaseModel):
    customer_id: str
    email: EmailStr
    email_verified: bool
    verification_message_id: str


class VerificationResult(BaseModel):
    customer_id: str
    email_verified: bool


class CheckoutLine(BaseModel):
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)


class CheckoutRequest(BaseModel):
    customer_id: str
    lines: list[CheckoutLine] = Field(min_length=1)


class FulfillmentStatus(StrEnum):
    pending = "pending"
    preparing = "preparing"
    shipped = "shipped"


class Receipt(BaseModel):
    receipt_id: str
    total_cents: int


class CustomerOrderUpdate(BaseModel):
    order_id: str
    customer_id: str
    fulfillment: FulfillmentStatus
    receipt: Receipt

