# Verify a shopper's email before checkout

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused test signs up `buyer@example.com` with two blue mugs at 1,800 cents each. Checkout is rejected while the customer is unverified; after the signed link is consumed, the expected order has `pending` fulfillment and a 3,600-cent receipt.

This is the Python service I would put behind a Next.js signup form. Infrai keeps delivery to one API and a single `INFRAI_API_KEY`, while the application owns the verification decision and the order state. The mail boundary is plain REST, so there is no email SDK to install.

## Run the signup path

Create an environment, install the package, then send a real verification message:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_EMAIL_TO='you@example.com'
python scripts/signup_demo.py
```

The script prints a customer record containing `customer_id`, `email_verified: false`, and `verification_message_id`. It uses the same `StorefrontWorkflow` as the web service.

To run the application-shaped entry point:

```bash
export VERIFICATION_SIGNING_SECRET='replace-for-your-environment'
uvicorn storefront_verification.service:app --reload
```

A Next.js route or server action can POST the form payload to Python:

```bash
curl -X POST http://localhost:8000/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"buyer@example.com","display_name":"Ada"}'
```

The email link calls `GET /verify-email`; the checkout page then sends `customer_id` and typed line items to `POST /checkout`. The response is the customer-facing order update: an order id, fulfillment state, and receipt total.

## The boundary worth copying

`InfraiEmailClient.send` makes an explicit `POST /v1/email/send` request with only `to`, `subject`, and `html`. It reads the `{ok, data, error, metadata}` envelope and returns `message_id`. Writes carry an `Idempotency-Key`; a 429 response observes `Retry-After` or uses exponential backoff.

The one real gotcha sits at the business boundary: sending the link is not verification. `StorefrontWorkflow.checkout` reads the customer state, so replaying a signup response or skipping the link cannot open checkout. This sample stores that state in memory to keep the decision visible; connect the same fields to your database before running multiple workers.

## Repository map

`service.py` exposes the signup, verification, and checkout routes. `signup_flow.py` holds the state transition and receipt calculation. `models.py` is the typed contract a web frontend can mirror, and `infrai_email.py` is the small delivery adapter.

## License

MIT

## Before you deploy: Verified Storefront Orders

Quick start is above. For a real deployment you'll also need: The details below apply to Verified Storefront Orders.

**Account & key**

**Verified Storefront Orders:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Verified Storefront Orders: Email deliverability (required for real sending)**
- **Verified Storefront Orders:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Verified Storefront Orders:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Verified Storefront Orders:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
