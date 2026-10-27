# Mzansi Link — MVP (plain Django)

Single Django project — server-rendered templates, session login, no
separate frontend, no API layer. Matches the MVP scope: signup with a
21+ block and a free-text town field (open to all of South Africa,
not one region), server-side photo blur, R99 PayFast unlock valid for
12 months, basic chat (page refresh, no auto-update), admin approval.

## Setup

```powershell
cd mzansi-link
cp .env.example .env
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000. Uses SQLite by default — no database
server, no password, nothing else to install.

Admin approval panel: http://localhost:8000/admin/ — approve a member
from the Users list and they can log in and appear on the grid.

## Load sample data

```powershell
python manage.py seed_demo_data
```

Creates 10 test accounts (password `demo1234` for all), including
free and paid men, approved and pending members, and one sample
conversation. See the app for the full list of usernames. Safe to
re-run; add `--reset` to wipe and reload.

## Deploying to Postgres later

Local dev uses SQLite. When you deploy (e.g. to Render), set these in
your environment and Django switches automatically:

```
USE_POSTGRES=1
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
```

## PayFast

`.env.example` ships PayFast's public sandbox credentials, so a full
once-off payment can be tested without a real merchant account. The
ITN webhook (`/payments/itn/`) is the only thing that unlocks a
user — not the page the browser lands on — so it must be reachable
from the internet for testing (use ngrok or similar locally).

## What's deliberately left out of the MVP

Forgot password, interests/smoking/drinking fields, province-wide
filters, and auto-updating chat — per the client's simplified scope.
