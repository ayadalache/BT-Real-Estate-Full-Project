# BT Real Estate — Full Project

This zip contains both halves of the site:

- `backend/` — Django + DRF API (see `backend/README.md` for full details)
- `frontend/` — your original static HTML/CSS/JS, now wired up to call the API

## Running it locally

**1. Start the backend** (in one terminal):

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DATABASE_URL=sqlite:///db.sqlite3 for a quick local trial
python manage.py migrate
python manage.py createsuperuser   # create yourself an Admin account to add listings
python manage.py runserver
```

The API is now at `http://localhost:8000/api/v1/`. Swagger docs: `http://localhost:8000/api/docs/`.

**2. Start the frontend** (in another terminal):

```bash
cd frontend
python3 -m http.server 8080
```

Open `http://localhost:8080` in your browser.

The frontend's `assets/js/config.js` points at `http://localhost:8000/api/v1` by
default — change that one line if your backend runs somewhere else.

## What's wired up

- **Register / Login / Logout** — real JWT auth, tokens stored in
  `localStorage`, auto-refreshed on expiry.
- **Nav bar** — automatically swaps Register/Login for your name + Logout
  (and an "Inbox" link if you're Staff/Admin) once you're signed in.
- **Homepage search** and **Browse Listings / Search page** — call the real
  search/filter API and render live results with pagination.
- **Listing detail page** — loads real listing data, image gallery, and lets
  visitors (logged in or not) submit an inquiry to the realtor.
- **Dashboard** — shows the listings you've personally inquired about.
- **Inbox** (new page) — for Staff/Admin: shows inquiries received on your
  own listings, with a status dropdown (New/Contacted/Closed).

## Adding your first listings

The frontend has no "create listing" UI (that wasn't part of the original
pages) — add listings either through the Django admin
(`http://localhost:8000/admin/`) or directly via the API
(`POST /api/v1/listings/` as an Admin/Staff user — see `backend/README.md`
for the exact fields).

## Known limitations

- Never tested against real Postgres/Docker in this environment — the
  config is correct but run `docker compose up --build` yourself to confirm
  in your own setup.
- No image upload UI on the frontend yet (the API supports it —
  `POST /api/v1/listings/{id}/images/` — but no page calls it).
- 2FA was intentionally left out (optional in the original spec).
