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

## Deploying to Render, with mzansi-link.co.za

`render.yaml` in this repo is a Render Blueprint — it provisions the
web service and a free Postgres database together, with most of the
env vars already wired up.

1. Push this repo to GitHub (see the git setup below if it isn't
   already a repo).
2. On [render.com](https://render.com), **New +** -> **Blueprint**,
   and point it at the GitHub repo. Render reads `render.yaml` and
   shows you the services it's about to create.
3. It will prompt you for three secrets it deliberately doesn't
   store in git: `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`,
   `PAYFAST_PASSPHRASE` — use your **live** PayFast merchant details
   here, not the sandbox ones from `.env.example` (see the PayFast
   section below). `SECRET_KEY` is generated for you automatically.
4. Click **Apply**. First deploy takes a few minutes — it runs
   `collectstatic` and `migrate` as part of the build.
5. Once it's live at the `*.onrender.com` URL Render gives you, go to
   the web service's **Settings -> Custom Domains** and add
   `mzansi-link.co.za` (and `www.mzansi-link.co.za` if you want both).
   Render shows you a CNAME (or A record) to add.
6. At your domain registrar (wherever `mzansi-link.co.za` is
   registered), add that exact record. DNS can take anywhere from a
   few minutes to a few hours to propagate — Render's dashboard shows
   the domain going from "pending" to "verified" once it has.
7. Once verified, Render issues the HTTPS certificate for it
   automatically — nothing else to configure.

**A disk for uploaded photos**: Render's filesystem is wiped on every
redeploy, so profile photos uploaded by members won't survive a
redeploy unless the service has a persistent disk attached. Free-tier
services can't attach one — if you're on free, uploaded photos will
be lost on the next deploy (fine for a demo/pilot, not for anything
with real users). Upgrade the web service to a paid instance type,
then uncomment the `disk:` block in `render.yaml` and redeploy. A
longer-term fix (object storage like S3) is out of scope for the MVP.

**ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS**: `render.yaml` already sets
these to `mzansi-link.co.za` — if you rename the domain or add
another one, update both env vars in the Render dashboard (under the
web service's **Environment** tab) to match, or logins and signups
from that domain will be rejected.

### Deploying elsewhere (or without the Blueprint)

Local dev uses SQLite. Set these in your environment and Django
switches to Postgres automatically — `render.yaml` already does this
for Render, but it's the same for any other host:

```
DEBUG=0
ALLOWED_HOSTS=your-domain.co.za,www.your-domain.co.za
CSRF_TRUSTED_ORIGINS=https://your-domain.co.za,https://www.your-domain.co.za
USE_POSTGRES=1
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
```

Build/start commands (what `render.yaml`'s `buildCommand`/
`startCommand` run):

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application
```

## PayFast

`.env.example` ships PayFast's public **sandbox** credentials, so a
full once-off payment can be tested locally without a real merchant
account. The ITN webhook (`/payments/itn/`) is the only thing that
unlocks a user — not the page the browser lands on — so it must be
reachable from the internet for testing (use ngrok or similar
locally).

In production on `mzansi-link.co.za`, swap these for the client's
**live** PayFast merchant ID/key (from their real PayFast account,
not the sandbox ones) and set `PAYFAST_MODE=live` — `render.yaml`
already prompts for these three as secrets rather than storing them
in git. Until live credentials are entered, payments will hit
PayFast's sandbox even on the real domain.

## What's deliberately left out of the MVP

Forgot password, interests/smoking/drinking fields, province-wide
filters, and auto-updating chat — per the client's simplified scope.
