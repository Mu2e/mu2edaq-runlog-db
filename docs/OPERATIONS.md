# mu2edaq-runlog-db — operations

## Read this first

1. **Know which mode you are in.** Every scripted launch runs **development**
   mode unless `DJANGO_ENV=production` is exported in the shell that starts
   it. Development mode means: no login, every visitor is a superuser, DEBUG
   pages, and a local `db.sqlite3` instead of the real run log. Putting
   `DJANGO_ENV=production` in `.env` does **not** work (RL-002).
2. **Production mode is not access-controlled.** Anyone who can reach the
   port can self-register at `/accounts/signup/` and then insert runs and
   subruns (RL-001). Keep the bind on `127.0.0.1` or behind a proxy that
   authenticates, until RL-001 is fixed.
3. **Do not enter runs by hand on the production database.** A hand-entered
   run number above the DAQ's sequence will later collide with a real run
   start (RL-003).
4. **Never run `manage.py purge_db` or `seed_db` with
   `DJANGO_ENV=production`.** Neither checks the backend (RL-005).

## Start and stop

Control room:

```bash
crs-app start runlog-db        # runs start-mu2edaq-runlog-db.sh
crs-app stop runlog-db
```

By hand, production:

```bash
cd ~/mu2edaq-main/mu2edaq-runlog-db
export DJANGO_ENV=production
export RUNLOGDB_SECRET_KEY='<50+ random characters>'
export RUNLOGDB_DB_HOST=<host> RUNLOGDB_DB_NAME=<db> RUNLOGDB_DB_USER=<role> RUNLOGDB_DB_PASSWORD=<pw>
./start-mu2e-rundb-viewer      # bootstrap (needs PyPI), migrate, gunicorn x4 --daemon
./stop-mu2e-rundb-viewer       # SIGTERM, 10 s, SIGKILL
```

What `start` does each time (`start-mu2e-rundb-viewer`):

| Step | Line | Consequence |
|---|---|---|
| `bootstrap-mu2e-rundb-viewer` → `pip install --upgrade` | `:24` | needs PyPI; fails the start under `set -e` if unreachable (RL-008); may upgrade Django/allauth within the pinned ranges |
| PID check on `.runserver.pid` | `:27-36` | already running → exit 0 |
| `DJANGO_ENV` default `development` | `:39` | see "Read this first" |
| `manage.py migrate` | `:51` | creates Django's tables in the target database, including the production run-log DB (RL-007) |
| gunicorn `--daemon --workers 4 --pid .runserver.pid` | `:67-71` | no log file is configured; daemon stderr is discarded |
| or `runserver --noreload &` | `:82-84` | output in `.runserver.log` |

## Files and state

| Path | Content | Notes |
|---|---|---|
| `.venv/` | virtual environment | git-ignored |
| `.runserver.pid` | gunicorn master or runserver PID | removed by stop |
| `.runserver.log` | runserver output (development) | grows without rotation |
| `db.sqlite3` | development database | git-ignored |
| `.env` | local overrides | git-ignored; cannot set `DJANGO_ENV`, `RUNLOGDB_HOST` or the server's `RUNLOGDB_PORT` |

## Health checks

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: localhost' http://127.0.0.1:8000/runs/about/   # 200
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: localhost' http://127.0.0.1:8000/runs/         # 302 in production, 200 in development
mu2edaq-discover --filter app=runlog-db   # needs mu2edaq-discovery installed
```

A 302 from `/runs/` to `/accounts/login/` is how to tell production mode from
development mode on a running instance.

## Symptoms

| Symptom | Cause |
|---|---|
| Page lists no runs at all, or only runs 1001+ with comments "Seeded … run" | development mode on a local SQLite (RL-002); check `DJANGO_ENV` in the start environment |
| `400 Bad Request` when browsing by hostname | production `ALLOWED_HOSTS` is `localhost, 127.0.0.1` with no override (RL-006) |
| Run detail or EWT lookup returns 500 on PostgreSQL | models expect an `id` column that `subrun` lacks (RL-004) |
| DAQ run start fails with `duplicate key value violates unique constraint` on `run` | a hand-entered or seeded run number caught up with the sequence (RL-003); `SELECT setval('<schema>.run_configuration_run_number_seq', (SELECT max(run_number) FROM <schema>.run));` after confirming with the run coordinator |
| Start fails during "Installing/updating packages" | no PyPI access (RL-008) |
| Unstyled pages | `cdn.tailwindcss.com` unreachable (RL-012) |
| Fermilab sign-in fails | OIDC endpoint is a development Keycloak realm (RL-006) |
| Scan shows the viewer several times | one discovery responder per gunicorn worker (RL-010) |

## Backups and data ownership

The production run-log tables belong to the DAQ (`DBRunInfo`); this viewer
is not the system of record and keeps no copy. Django's session, user and
social-account rows live in the same database (RL-007), so a run-log restore
also restores or drops web accounts.
