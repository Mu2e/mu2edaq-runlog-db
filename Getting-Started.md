# Getting Started — Mu2e DAQ Run Log Viewer

For the concise quick-reference, see **[Instructions.md](Instructions.md)**.

This document covers the full technical details: configuration system, database
routing, SSO setup, Docker packaging, and how to extend the application.

---

## Prerequisites

- Python 3.9 or later (`python3` / `pip3` on macOS where `python` is 2.7)
- Git

A Python virtual environment is created automatically by the bootstrap script.
You do not need to install anything manually before running the start script.

---

## First-time setup

```bash
git clone git@github.com:Mu2e/mu2edaq-runlog-db.git
cd mu2edaq-runlog-db
cp .env.example .env          # edit .env to set DJANGO_ENV and any overrides
./start-mu2e-rundb-viewer     # bootstraps venv, migrates, starts server
```

Open `http://localhost:8000`.

---

## Scripts

### `bootstrap-mu2e-rundb-viewer`

Creates `.venv/` (if absent) and runs `pip install --upgrade` against
`requirements.txt`. Safe to run at any time — it is idempotent.

```bash
./bootstrap-mu2e-rundb-viewer
```

### `start-mu2e-rundb-viewer`

1. Calls `bootstrap-mu2e-rundb-viewer` to ensure packages are current
2. Checks for a stale PID file and warns if the server is already running
3. Runs `python manage.py migrate`
4. Starts the server:
   - **development** → Django's `runserver` in background, logs to `.runserver.log`
   - **production** → gunicorn with 4 workers in background (or foreground inside Docker)

```bash
DJANGO_ENV=development ./start-mu2e-rundb-viewer
DJANGO_ENV=production  ./start-mu2e-rundb-viewer
```

The PID is written to `.runserver.pid`.

### `stop-mu2e-rundb-viewer`

Sends SIGTERM to the PID in `.runserver.pid`, waits up to 10 s for a clean
exit, then falls back to SIGKILL.

```bash
./stop-mu2e-rundb-viewer
```

---

## Configuration

### Load order

Settings are composed in this order (later values override earlier ones):

1. `.env` file loaded by `python-dotenv`
2. `config/default.yaml`
3. `config/<DJANGO_ENV>.yaml` (determined by `DJANGO_ENV` env var, default: `development`)
4. Individual `RUNLOGDB_*` environment variables

### Config overlays

| File | Backend | Auth | Debug |
|---|---|---|---|
| `config/development.yaml` | SQLite | disabled | on |
| `config/production.yaml` | PostgreSQL | enabled | off |

### Environment variable reference

| Variable | Config key | Notes |
|---|---|---|
| `DJANGO_ENV` | — | Selects config overlay file |
| `RUNLOGDB_SECRET_KEY` | `app.secret_key` | Required in production |
| `RUNLOGDB_DEBUG` | `app.debug` | `true` / `false` |
| `RUNLOGDB_DB_BACKEND` | `database.backend` | `sqlite` or `postgres` |
| `RUNLOGDB_DB_HOST` | `database.postgres.host` | |
| `RUNLOGDB_DB_PORT` | `database.postgres.port` | |
| `RUNLOGDB_DB_NAME` | `database.postgres.name` | |
| `RUNLOGDB_DB_USER` | `database.postgres.user` | |
| `RUNLOGDB_DB_PASSWORD` | `database.postgres.password` | |
| `RUNLOGDB_AUTH_ENABLED` | `auth.enabled` | |
| `RUNLOGDB_FERMILAB_CLIENT_ID` | `auth.providers.fermilab_cilogon.client_id` | |
| `RUNLOGDB_FERMILAB_CLIENT_SECRET` | `auth.providers.fermilab_cilogon.client_secret` | |
| `RUNLOGDB_GOOGLE_CLIENT_ID` | `auth.providers.google.client_id` | |
| `RUNLOGDB_GOOGLE_CLIENT_SECRET` | `auth.providers.google.client_secret` | |

---

## Database backends

### SQLite (development)

The default. Django creates the database file at `db.sqlite3` when you first
run migrations. The database file is excluded from git (`.gitignore`).

### PostgreSQL (production)

The run-log schema (`run`, `subrun`, `run_transition`, etc.) already exists in
the production database and is **never modified by Django migrations**. This is
enforced by `runlogdb/db_router.py`, which returns `allow_migrate=False` for
the `runs` app on any PostgreSQL connection.

Django's own internal tables (`auth_*`, `django_session`, `account_*`, etc.)
are still created by `migrate` on a fresh Postgres instance.

If Django's internal tables already exist (e.g., from a previous deployment),
run with `--fake-initial` to skip re-creation:

```bash
DJANGO_ENV=production .venv/bin/python manage.py migrate --fake-initial
```

---

## SSO / authentication

Authentication uses `django-allauth`. It can be disabled entirely for
development via `auth.enabled: false` (set in `config/development.yaml` by
default).

When disabled, `runlogdb/middleware.py` (`DevBypassMiddleware`) automatically
authenticates every request as a local `dev` user so that `@login_required`
views work without a login flow.

### Registering SSO applications

#### Fermilab SSO (Keycloak OIDC)

1. Register a client in the `myrealm` realm at `https://kc.apps.okddev.fnal.gov`
2. OIDC discovery document: `https://kc.apps.okddev.fnal.gov/realms/myrealm/.well-known/openid-configuration`
3. Callback URIs to register:
   - Dev: `http://localhost:8000/accounts/oidc/fermilab/login/callback/`
   - Prod: `https://<your-host>/accounts/oidc/fermilab/login/callback/`

#### Google OAuth2

1. Create a Web Application credential at [console.cloud.google.com](https://console.cloud.google.com)
2. Authorized redirect URIs to register:
   - Dev: `http://localhost:8000/accounts/google/login/callback/`
   - Prod: `https://<your-host>/accounts/google/login/callback/`

---

## Docker

The `Dockerfile` uses `python:3.9-slim`. The virtual environment is built into
the image at `/app/.venv` during the build step, so no internet access is
required at runtime.

```bash
# Build
docker build -t mu2e-runlog-viewer .

# Run (production)
docker run -d \
  -p 8000:8000 \
  --env-file /path/to/production.env \
  --name mu2e-runlog \
  mu2e-runlog-viewer
```

Inside Docker, `start-mu2e-rundb-viewer` detects `/.dockerenv` and runs
gunicorn in the foreground (no daemonisation needed).

---

## Adding new queries

1. Add a form to `runs/forms.py`
2. Add a view with `@login_required` to `runs/views.py`
3. Add a URL to `runs/urls.py`
4. Add a template under `runs/templates/runs/`
5. Add a nav link in `templates/base.html`

---

## Project structure

```
mu2edaq-runlog-db/
├── bootstrap-mu2e-rundb-viewer
├── start-mu2e-rundb-viewer
├── stop-mu2e-rundb-viewer
├── manage.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env.example
├── config/
│   ├── default.yaml
│   ├── development.yaml
│   └── production.yaml
├── runlogdb/
│   ├── settings.py        ← YAML + env-var config loader
│   ├── urls.py
│   ├── wsgi.py
│   ├── db_router.py       ← skips runs app migrations on Postgres
│   └── middleware.py      ← dev auth bypass
└── runs/
    ├── models.py           ← 9 ORM models
    ├── views.py            ← query + data-entry views
    ├── forms.py            ← query + data-entry forms (Tailwind-styled)
    ├── urls.py
    ├── management/commands/
    │   ├── seed_db.py
    │   └── purge_db.py
    └── templates/runs/
        ├── run_list.html
        ├── run_detail.html
        ├── subrun_ewt.html
        ├── entry_index.html
        ├── entry_run.html
        ├── entry_run_end.html
        └── entry_subrun.html
```
