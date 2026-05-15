# Mu2e DAQ Run Log Viewer — Instructions

A web application for querying and manually entering data in the Mu2e DAQ run-log
database. Supports SQLite (development) and PostgreSQL (production) backends.

---

## Quick start (development)

```bash
git clone git@github.com:Mu2e/mu2edaq-runlog-db.git
cd mu2edaq-runlog-db
cp .env.example .env
./start-mu2e-rundb-viewer
```

Open `http://localhost:8000` in your browser.  
No login is required in development mode.

To stop:
```bash
./stop-mu2e-rundb-viewer
```

---

## Scripts

| Script | Purpose |
|---|---|
| `./bootstrap-mu2e-rundb-viewer` | Create/update the Python virtual environment and install all packages |
| `./start-mu2e-rundb-viewer` | Run bootstrap, apply migrations, start the server |
| `./stop-mu2e-rundb-viewer` | Stop the running server |

The start script automatically:
- Creates `.venv/` if it does not exist
- Upgrades all packages to the latest allowed versions
- Runs `manage.py migrate` before starting

### Environment variables for the start script

| Variable | Default | Description |
|---|---|---|
| `DJANGO_ENV` | `development` | Config overlay (`development` or `production`) |
| `RUNLOGDB_HOST` | `127.0.0.1` | Bind address |
| `RUNLOGDB_PORT` | `8000` | Bind port |

---

## Configuration

Settings are loaded in this order (later values win):

1. `.env` file in the project root
2. `config/default.yaml`
3. `config/<DJANGO_ENV>.yaml` (e.g. `config/development.yaml`)
4. `RUNLOGDB_*` environment variables

### Environment overlays

| File | Database | Login required | Debug |
|---|---|---|---|
| `config/development.yaml` | SQLite | No | Yes |
| `config/production.yaml` | PostgreSQL | Yes | No |

### Key environment variables

| Variable | Description |
|---|---|
| `RUNLOGDB_SECRET_KEY` | Django secret key (required in production) |
| `RUNLOGDB_DB_BACKEND` | `sqlite` or `postgres` |
| `RUNLOGDB_DB_HOST` | PostgreSQL host |
| `RUNLOGDB_DB_PORT` | PostgreSQL port (default 5432) |
| `RUNLOGDB_DB_NAME` | PostgreSQL database name |
| `RUNLOGDB_DB_USER` | PostgreSQL username |
| `RUNLOGDB_DB_PASSWORD` | PostgreSQL password |
| `RUNLOGDB_AUTH_ENABLED` | `true` / `false` — enable/disable SSO login |
| `RUNLOGDB_FERMILAB_CLIENT_ID` | Fermilab CILogon OIDC client ID |
| `RUNLOGDB_FERMILAB_CLIENT_SECRET` | Fermilab CILogon OIDC client secret |
| `RUNLOGDB_GOOGLE_CLIENT_ID` | Google OAuth2 client ID |
| `RUNLOGDB_GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret |

---

## Web interface

| URL | Description |
|---|---|
| `/runs/` | Search for runs by time period |
| `/runs/<N>/subruns/` | List subruns for run N; shows total event count |
| `/runs/subruns/ewt/` | Find subruns by Event Window Tag (single or range) |
| `/runs/entry/` | Manual data entry menu |
| `/runs/entry/run/` | Add a new run |
| `/runs/entry/run-end/` | Record end info for an existing run |
| `/runs/entry/subrun/` | Add a subrun with event counts and EWT range |

---

## Production setup

### 1 — Configure PostgreSQL connection

```dotenv
# .env
DJANGO_ENV=production
RUNLOGDB_SECRET_KEY=a-long-random-string
RUNLOGDB_DB_HOST=your-db-host
RUNLOGDB_DB_NAME=your-db-name
RUNLOGDB_DB_USER=your-db-user
RUNLOGDB_DB_PASSWORD=your-db-password
```

### 2 — Register SSO callback URIs

**Fermilab SSO (Keycloak)** — register a client in the `myrealm` realm at
`https://kc.apps.okddev.fnal.gov`

- OIDC discovery: `https://kc.apps.okddev.fnal.gov/realms/myrealm/.well-known/openid-configuration`
- Callback URI: `https://<your-host>/accounts/oidc/fermilab/login/callback/`

```dotenv
RUNLOGDB_FERMILAB_CLIENT_ID=...
RUNLOGDB_FERMILAB_CLIENT_SECRET=...
```

**Google OAuth2** — register at [console.cloud.google.com](https://console.cloud.google.com)

- Authorized redirect URI: `https://<your-host>/accounts/google/login/callback/`

```dotenv
RUNLOGDB_GOOGLE_CLIENT_ID=...
RUNLOGDB_GOOGLE_CLIENT_SECRET=...
```

### 3 — Start

```bash
DJANGO_ENV=production ./start-mu2e-rundb-viewer
```

The server runs as gunicorn with 4 workers. The run-log tables already exist
in Postgres and are **never modified** by Django migrations. Only Django's
internal tables (auth, sessions, etc.) are created on first run.

---

## Docker

Build and run the container:

```bash
docker build -t mu2e-runlog-viewer .

docker run -d \
  -p 8000:8000 \
  -e DJANGO_ENV=production \
  -e RUNLOGDB_SECRET_KEY=your-secret-key \
  -e RUNLOGDB_DB_HOST=your-db-host \
  -e RUNLOGDB_DB_NAME=your-db-name \
  -e RUNLOGDB_DB_USER=your-db-user \
  -e RUNLOGDB_DB_PASSWORD=your-db-password \
  -e RUNLOGDB_FERMILAB_CLIENT_ID=... \
  -e RUNLOGDB_FERMILAB_CLIENT_SECRET=... \
  --name mu2e-runlog \
  mu2e-runlog-viewer
```

The container runs `start-mu2e-rundb-viewer`, which detects Docker and keeps
gunicorn in the foreground. No `.env` file is needed inside the container —
pass secrets via `-e` flags or an env file:

```bash
docker run -d --env-file /path/to/production.env -p 8000:8000 mu2e-runlog-viewer
```

---

## Development utilities

### Populate the database with test data

```bash
.venv/bin/python manage.py seed_db          # default: 10 runs, 5 subruns each
.venv/bin/python manage.py seed_db --runs 50 --subruns-per-run 20
```

### Purge all run-log data

```bash
.venv/bin/python manage.py purge_db
.venv/bin/python manage.py purge_db --confirm  # skip the confirmation prompt
```

### Django shell

```bash
DJANGO_ENV=development .venv/bin/python manage.py shell
```

---

## Project layout

```
mu2edaq-runlog-db/
├── bootstrap-mu2e-rundb-viewer   # Install/update venv and packages
├── start-mu2e-rundb-viewer       # Start the application
├── stop-mu2e-rundb-viewer        # Stop the application
├── manage.py
├── requirements.txt
├── Dockerfile
├── .env.example                  # Copy to .env and fill in values
├── config/
│   ├── default.yaml
│   ├── development.yaml
│   └── production.yaml
├── runlogdb/                     # Django project package
│   ├── settings.py               # Config loader
│   ├── urls.py
│   ├── db_router.py              # Prevents Django from touching Postgres run-log tables
│   └── middleware.py             # Dev auth bypass (no login when AUTH_ENABLED=false)
└── runs/                         # Query and entry app
    ├── models.py                 # ORM models for all active tables
    ├── views.py
    ├── forms.py
    ├── urls.py
    └── management/commands/
        ├── seed_db.py            # Populate test data
        └── purge_db.py           # Purge all run-log data
```
