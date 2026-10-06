# mu2edaq-runlog-db

Django web viewer and manual-entry tool for the Mu2e DAQ run-log database.
It lists runs by time window, shows the subruns of a run with event totals,
and finds the subrun that contains a given Event Window Tag (EWT). It reads
the PostgreSQL tables that the otsdaq `DBRunInfo` plugin (otsdaq-mu2e)
writes at run transitions, or a local SQLite database for development.

> **Security and data-integrity warnings (September 2026 review).**
> Production mode admits anyone who can reach the port: the allauth signup
> endpoint is open and grants write access (RL-001). Every scripted launch,
> including `crs-app start runlog-db`, runs development mode (no login,
> superuser for every visitor, local SQLite) unless `DJANGO_ENV=production`
> is exported in the shell; `.env` cannot set it (RL-002). Do not use the
> entry forms, `seed_db` or `purge_db` against the production database
> (RL-003, RL-005). Details: [docs/ISSUES-PENDING.md](docs/ISSUES-PENDING.md).

## Requirements

- Python 3.9 or later, with `venv`
- Network access to PyPI on every start (the start script upgrades packages)
- For production: a PostgreSQL role on the run-log database with `SELECT`,
  `CREATE` (Django's own tables) and, for the entry forms, `INSERT`
- Optional: `mu2edaq-discovery` from the sibling checkout, for service
  announcement

Python dependencies (`requirements.txt`): Django 4.2.x, django-allauth
0.61.x, PyYAML, python-dotenv, psycopg2-binary, gunicorn.

## Quick start (development, local SQLite)

```bash
cd ~/mu2edaq-main/mu2edaq-runlog-db
./start-mu2e-rundb-viewer                        # creates .venv, migrates, runserver on 127.0.0.1:8000
.venv/bin/python manage.py seed_db --runs 10     # fake data
open http://localhost:8000/                      # no login in development mode
./stop-mu2e-rundb-viewer
```

## Production

Export the settings in the shell; do not rely on `.env` for `DJANGO_ENV`:

```bash
export DJANGO_ENV=production
export RUNLOGDB_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
export RUNLOGDB_DB_HOST=<host> RUNLOGDB_DB_NAME=<db> RUNLOGDB_DB_USER=<role> RUNLOGDB_DB_PASSWORD=<pw>
export RUNLOGDB_FERMILAB_CLIENT_ID=... RUNLOGDB_FERMILAB_CLIENT_SECRET=...
./start-mu2e-rundb-viewer                        # gunicorn, 4 workers, daemonised
```

Before deploying, edit `config/production.yaml` to set `app.allowed_hosts`
and `auth.providers.fermilab_cilogon.oidc_endpoint`. Neither has an
environment override, and the default endpoint is a development Keycloak
realm.

Docker:

```bash
docker build -t mu2e-runlog-viewer .
docker run -d -p 8000:8000 --env-file production.env --name mu2e-runlog mu2e-runlog-viewer
```

The image sets `DJANGO_ENV=production` and binds `0.0.0.0`, which exposes
the open signup endpoint (RL-001) to the network.

## Control room

`crs-app start runlog-db` runs `start-mu2edaq-runlog-db.sh`, which maps
`CRS_PORT_HTTP` to `RUNLOGDB_PORT` and `exec`s `start-mu2e-rundb-viewer`.
`stop-mu2edaq-runlog-db.sh` `exec`s `stop-mu2e-rundb-viewer`. The two pairs
are regular files (wrappers), not symlinks or copies.

## Configuration

Layered, later wins: `.env` (cannot override variables already set) →
`config/default.yaml` → `config/<DJANGO_ENV>.yaml` → `RUNLOGDB_*`
environment variables. Full reference: `man 5 ./man/man5/mu2edaq-runlog-db.yaml.5`.

| Variable | Purpose |
|---|---|
| `DJANGO_ENV` | `development` (default) or `production` |
| `RUNLOGDB_HOST`, `RUNLOGDB_PORT` | bind address (default `127.0.0.1`) and port (default `8000`); read by the start script |
| `RUNLOGDB_SECRET_KEY` | Django secret key; **must** be set in production |
| `RUNLOGDB_DEBUG`, `RUNLOGDB_AUTH_ENABLED` | booleans |
| `RUNLOGDB_DB_BACKEND`, `RUNLOGDB_DB_{HOST,PORT,NAME,USER,PASSWORD}` | database |
| `RUNLOGDB_FERMILAB_CLIENT_{ID,SECRET}`, `RUNLOGDB_GOOGLE_CLIENT_{ID,SECRET}` | SSO |
| `RUNLOGDB_GITHUB_TOKEN`, `RUNLOGDB_GITHUB_REPO` | bug-report page |

## Web interface

| URL | Purpose |
|---|---|
| `/runs/` | runs by UTC time range |
| `/runs/<N>/subruns/` | subruns of run N, total events, end comment |
| `/runs/subruns/ewt/` | subrun(s) containing an EWT or overlapping an EWT range |
| `/runs/entry/` | manual entry of runs, run-end comments, subruns |
| `/runs/bug-report/` | file a GitHub issue |
| `/runs/about/` | about page |

## Documentation

| Document | Content |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | design, data source, configuration layers, review verdicts |
| [docs/INTERFACES.md](docs/INTERFACES.md) | HTTP routes, authentication, database contract, discovery |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | start/stop, files, health checks, symptoms |
| [docs/ISSUES-PENDING.md](docs/ISSUES-PENDING.md) | review findings staged for filing |
| [Getting-Started.md](Getting-Started.md), [Instructions.md](Instructions.md) | the original setup guides |
| [db-schema.md](db-schema.md), `db-schema.txt` | production schema diagram and column dump |
| `man/` | `start-`/`stop-mu2edaq-runlog-db.sh(1)`, `start-`/`stop-`/`bootstrap-mu2e-rundb-viewer(1)`, `manage.py(1)`, `mu2edaq-runlog-db.yaml(5)`, `mu2edaq-runlog-db(7)` |

Read a man page in place: `man ./man/man7/mu2edaq-runlog-db.7`.

## Tests

None. See RL-011.

## License

MIT; see `LICENSE`.
