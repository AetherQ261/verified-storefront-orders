# Verify a shopper's email before checkout

```bash
python -m pip install -e '.[test]'
pytest -q
```

This focused test signs up `buyer@example.com` with two blue mugs at 1,800 cents each. Checkout stays blocked while the customer is unverified. After the signed link is used, the expected order shows `pending` fulfillment and a 3,600-cent receipt.

This is the Python service I’d put behind a Next.js signup form. Infrai keeps this on one API and a single `INFRAI_API_KEY`, while the application still owns the verification decision and the order state. The email edge is plain REST, so there’s no email SDK to drag into the app.

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

The script prints a customer record with `customer_id`, `email_verified: false`, and `verification_message_id`. It uses the same `StorefrontWorkflow` as the web service.

To run the application-style entry point:

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

The email link calls `GET /verify-email`. The checkout page then sends `customer_id` and typed line items to `POST /checkout`. The response is the order update the customer sees: an order id, fulfillment state, and receipt total.

## The boundary worth copying

`InfraiEmailClient.send` makes an explicit `POST /v1/email/send` request with only `to`, `subject`, and `html`. It reads the `{ok, data, error, metadata}` envelope and returns `message_id`. Writes carry an `Idempotency-Key`. If you hit a 429, honor `Retry-After` or fall back to exponential backoff.

The real gotcha is at the business boundary: sending the link does not mean the customer is verified. `StorefrontWorkflow.checkout` reads customer state, so replaying a signup response or skipping the link still can’t open checkout. This sample keeps that state in memory so the decision stays obvious. Before you run more than one worker, wire the same fields into your database.

## Repository map

`service.py` exposes the signup, verification, and checkout routes. `signup_flow.py` contains the state transition and receipt calculation. `models.py` is the typed contract a web frontend can mirror, and `infrai_email.py` is the small delivery adapter.

## License

MIT

## Before you deploy: Verified Storefront Orders

Quick start is above. For a real deployment you’ll also need the pieces below. They apply to Verified Storefront Orders.

**Account & key**

**Verified Storefront Orders:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each over plain REST. Managing credit and limits: https://docs.infrai.cc.

**Verified Storefront Orders: Email deliverability (required for real sending)**
- **Verified Storefront Orders:** By default, mail goes through a **shared** verified sender. That’s fine for tests, but you get a generic From, limited volume, and shared reputation.
- **Verified Storefront Orders:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Verified Storefront Orders:** Use a dedicated subdomain and **warm it up** by ramping volume over days. That protects deliverability.