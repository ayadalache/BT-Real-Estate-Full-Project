# BT Real Estate — Backend

Django + DRF backend for the BT Real Estate listings platform.

## Feature 1: Authentication ✅
## Feature 2: Listings ✅
## Feature 3: Inquiries + Dashboard + Realtor Profile ✅ (this delivery)

Custom User model with RBAC roles, JWT auth (access/refresh), email
verification, password reset, change password, account lockout on
repeated failed logins, and a "remember me" extended session option.

Listings with normalized Amenity (M2M) and ListingImage models, public
search/filter (city, state, min bedrooms, max price, listing type, free-text
keyword search across title/description/amenities), Admin/Staff-only CRUD
with per-owner object permissions, and secure image upload/gallery
management.

Public "Make An Inquiry" submissions (guests or logged-in users), a
realtor/Admin inbox for triaging leads, a user Dashboard showing "listings
you've inquired about" (matches `dashboard.html` exactly), and a realtor
profile (bio + photo) so the "Property Realtor" card on `listing.html` is
fully populated.

## Local setup (SQLite, fastest way to try it)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DATABASE_URL=sqlite:///db.sqlite3 for local trial
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API docs: http://localhost:8000/api/docs/
Admin: http://localhost:8000/admin/

## Docker (Postgres, production-like)

```bash
cp .env.example .env   # fill in real values, including POSTGRES_PASSWORD
docker compose up --build
```

## Running tests

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
# or
pytest
# with coverage:
coverage run --source='apps' manage.py test && coverage report
```

Current coverage: **95%**, 76/76 tests passing.

## Auth endpoints (`/api/v1/auth/`)

| Method | Path                          | Auth required | Purpose |
|---|---|---|---|
| POST | `register/`                  | No  | Create account (sends verification email) |
| POST | `login/`                     | No  | Obtain access/refresh JWT (`remember_me` optional) |
| POST | `refresh/`                   | No  | Exchange refresh token for new access token |
| POST | `logout/`                    | Yes | Blacklist refresh token |
| GET  | `me/`                        | Yes | Current user info |
| POST | `verify-email/`              | No  | Confirm email via signed token |
| POST | `resend-verification/`       | No  | Resend verification email |
| POST | `password-reset/`            | No  | Request password reset email |
| POST | `password-reset/confirm/`    | No  | Set new password via signed token |
| POST | `change-password/`           | Yes | Change password (requires current password) |

## Users endpoints (`/api/v1/users/`)

| Method | Path | Auth required | Purpose |
|---|---|---|---|
| GET/PATCH | `me/` | Yes | View/update own profile (bio, name, phone) |
| POST | `me/photo/` | Yes | Upload/replace profile photo (validated image) |

## Listings endpoints (`/api/v1/listings/`)

| Method | Path | Auth required | Purpose |
|---|---|---|---|
| GET | `` | No | List/search/filter listings (paginated) |
| POST | `` | Admin/Staff | Create a listing (realtor defaults to yourself; only Admins may assign to someone else) |
| GET | `{public_id}/` | No* | Listing detail (*non-active listings only visible to owner/Admin) |
| PATCH/PUT | `{public_id}/` | Owning realtor or Admin | Update a listing |
| DELETE | `{public_id}/` | Owning realtor or Admin | Delete a listing |
| POST | `{public_id}/images/` | Owning realtor or Admin | Upload a gallery image (multipart) |
| DELETE | `{public_id}/images/{image_id}/` | Owning realtor or Admin | Remove a gallery image |

**Search/filter query params**: `search` (keyword, matches title/description/amenity names), `city`, `state`, `min_bedrooms`, `max_price`, `listing_type`, `ordering` (e.g. `price`, `-listing_date`).

## Inquiries endpoints (`/api/v1/inquiries/`)

| Method | Path | Auth required | Purpose |
|---|---|---|---|
| POST | `` | No | Submit "Make An Inquiry" (guest or logged-in; auto-linked to account if logged in) |
| GET | `inbox/` | Admin/Staff | Realtor inbox — inquiries on your own listings (Admins see all) |
| GET | `{id}/` | Owning realtor or Admin | View a single inquiry |
| PATCH | `{id}/` | Owning realtor or Admin | Update inquiry status (NEW/CONTACTED/CLOSED) |
| GET | `dashboard/` | Yes (any role) | "Listings you've inquired about" — matches `dashboard.html` |



## Key design decisions & security notes

- **Roles**: `ADMIN`, `STAFF` (realtors), `USER`. Only Admin/Staff will be
  permitted to manage listings in the next feature — enforced via
  `core/permissions.py` (`IsStaffOrAdmin`, `IsOwnerOrAdmin`, etc.).
- **Stateless signed tokens** (not DB-backed) for email verification /
  password reset — HMAC-signed via `SECRET_KEY`, self-expiring, and
  purpose-scoped (a verification token can't be replayed as a reset token).
- **Account lockout**: 5 failed logins locks the account for 15 minutes.
- **No user enumeration**: registration, password-reset-request, and
  resend-verification all return identical responses whether or not the
  email/username exists.
- **`ATOMIC_REQUESTS` intentionally disabled** — DRF rolls back the whole
  transaction on any 4xx response, which would silently wipe out security
  bookkeeping (e.g. the failed-login counter) written just before an error
  is returned. True atomicity is applied explicitly via `@transaction.atomic`
  in `services.py` where it's actually needed (registration, password
  reset/change).
- **Mass-assignment protection**: `role`, `is_email_verified`, etc. are
  read-only on every user-facing serializer — verified by tests.
- **Rate limiting**: login/register/password-reset are throttled
  (`ScopedRateThrottle`) against brute force.
- **Global exception handler** (`core/exceptions.py`): stack traces are
  never returned to the client; unhandled errors get a logged reference ID.
- **Standard response envelope** on every endpoint:
  `{success, message, data, errors}`.

### Listings-specific notes

- **Object-level ownership**: a Staff (realtor) can only edit/delete their
  own listings; only Admins can edit any listing or reassign a listing's
  realtor — enforced in `IsRealtorOwnerOrAdmin`, verified by tests.
- **Visibility rules**: non-`ACTIVE` listings are excluded from the queryset
  entirely for anyone who isn't the owner/Admin — so an unauthorized lookup
  by ID returns 404, not 403, avoiding confirming the listing's existence.
- **Amenities are normalized** (M2M), not free text, so keyword search is
  precise rather than doing fragile substring matching.
- **Secure image upload** (`validators.py`): extension allow-list + declared
  MIME-type allow-list + 5MB size cap + genuine image verification via
  Pillow (`Image.verify()`), which is what actually catches a disguised
  malicious file (e.g. a script renamed to `.jpg` with a forged
  content-type) — extension/MIME checks alone are trivially spoofed.
- **Random filenames** for all stored images — never derived from
  user-supplied names (blocks path traversal and information leakage).
- Query performance: `select_related("realtor")` +
  `prefetch_related("images", "amenities")` on every listing queryset to
  avoid N+1 queries when serializing lists/details; DB indexes on
  `(city, state)`, `(status, listing_type)`, `price`, and `bedrooms` back
  the exact filters the search form uses.

### Inquiries & Dashboard notes

- **No account required to inquire** (matches the public modal on
  `listing.html`), but an inquiry is auto-linked to the submitter's account
  when they're logged in — this is what powers the dashboard.
- **Can't inquire on a non-active listing** — enforced by scoping the
  `listing` field's queryset to `status=ACTIVE` in the serializer itself, so
  it's a validation error, not just a business-logic afterthought.
- **Inbox isolation**: a realtor only ever sees inquiries for listings they
  own; Admins see everything. Verified by tests.
- **Realtor notification email** sent on every new inquiry (console backend
  in dev, real SMTP in production via `.env`).

### Realtor profile notes

- `bio` and `profile_photo` added to the shared `User` model (not a
  separate table) since every Staff/Admin already *is* a user — avoids an
  unnecessary 1:1 join for something this small.
- Photo upload reuses the same secure image validation as listing images
  (extension + MIME allow-list, size cap, Pillow-verified genuine image),
  now extracted to `core/validators.py` so both apps share one
  implementation instead of duplicating it.
- `profile_photo` is deliberately **read-only** on the general profile
  update endpoint — it can only be changed via the dedicated upload
  endpoint, which is the only code path that actually runs the image
  validation.

## Everything in the original spec is now implemented

Auth, Listings, Inquiries, Dashboard, and Realtor profile cover every page
in the uploaded frontend (`index.html`, `listings.html`, `listing.html`,
`search.html`, `dashboard.html`, `login.html`, `register.html`,
`about.html`). The only originally-listed item intentionally left out is
**2FA**, which was marked optional in the original spec — let me know if
you'd like it added.
