# mu2edaq-runlog-db — interfaces

Everything this application exposes or consumes. Line references are to the
`mu2e-sept-mega-review` branch (HEAD `bbbe6a6`, tag `t01.00.00`).

## 1. HTTP (TCP 8000)

Bind address and port come from the shell, not from Django:
`RUNLOGDB_HOST` (default `127.0.0.1`) and `RUNLOGDB_PORT` (default `8000`)
in `start-mu2e-rundb-viewer:42-43`. The control-room wrapper maps
`CRS_PORT_HTTP` onto `RUNLOGDB_PORT` (`start-mu2edaq-runlog-db.sh:14`). The
Docker image sets `RUNLOGDB_HOST=0.0.0.0` (`Dockerfile:24`).

| Method | Path | View | Login | Effect |
|---|---|---|---|---|
| GET | `/` | `RedirectView` | no | 302 → `/runs/` |
| GET | `/runs/?start_time=&end_time=` | `run_list` (`runs/views.py:17`) | yes | `run` rows with `create_time` in range, newest first; nothing is listed until the form validates |
| GET | `/runs/<N>/subruns/` | `run_detail` (`:35`) | yes | one `run`, its `subrun` rows, `SUM(n_events)`, `run_end_info` |
| GET | `/runs/subruns/ewt/?ewt_min=&ewt_max=` | `subrun_ewt` (`:58`) | yes | subruns with `min_ewt ≤ x ≤ max_ewt` (point) or overlapping `[ewt_min, ewt_max]` |
| GET | `/runs/entry/` | `entry_index` (`:85`) | yes | links to the three forms |
| GET, POST | `/runs/entry/run/` | `entry_run` (`:91`) | yes | **INSERT `run`** with an operator-chosen `run_number` |
| GET, POST | `/runs/entry/run-end/` | `entry_run_end` (`:114`) | yes | **INSERT `run_end_info`** |
| GET, POST | `/runs/entry/subrun/` | `entry_subrun` (`:220`) | yes | **INSERT `subrun`** |
| GET, POST | `/runs/bug-report/` | `bug_report` (`:132`) | yes | POST to `api.github.com/repos/<github.repo>/issues` with the server token |
| GET | `/runs/about/` | `about` (`:215`) | **no** | static page |
| * | `/accounts/…` | django-allauth | — | login, logout, **signup**, Google and OIDC flows |
| * | `/admin/` | Django admin | staff | auth/allauth models only; `runs` has no `admin.py` |

POST views are protected by `CsrfViewMiddleware` and every form template
carries `{% csrf_token %}`. CSRF does not stop a direct (non-browser) client,
which can choose its own token; see §2.

There is no JSON API. Output is server-rendered HTML.

## 2. Authentication and authorisation

Mode is set by `auth.enabled` (`runlogdb/settings.py:71`, `:121`, `:154`).

### 2.1 `auth.enabled: false` — development overlay and every scripted launch

`DevBypassMiddleware` (`runlogdb/middleware.py:28-31`) replaces every
anonymous `request.user` with user `dev`, created with `is_staff=True,
is_superuser=True`. Every page, every insert form and `/admin/` are open to
anyone who can connect. `DEBUG` is on and `ALLOWED_HOSTS` is `*`
(`config/development.yaml`).

This is the mode a control-room launch gets: `start-mu2e-rundb-viewer:39`
exports `DJANGO_ENV=development` when unset, nothing in mu2edaq-main sets it,
and `.env` cannot override it (python-dotenv `override=False`). Verified:

```
# scratch copy; .env contains DJANGO_ENV=production; shell has DJANGO_ENV=development
AUTH_ENABLED False DEBUG True DB django.db.backends.sqlite3
```

Exposure is limited by the default bind `127.0.0.1`, so in this mode the
open surface is every local user of the host (control-room machines are
multi-user), or the whole network if `RUNLOGDB_HOST=0.0.0.0` is set.

### 2.2 `auth.enabled: true` — production overlay

| Mechanism | Behaviour | Evidence |
|---|---|---|
| Fermilab OIDC | allauth `openid_connect` server `fermilab`, labelled "Fermilab CILogon", endpoint `https://kc.apps.okddev.fnal.gov/realms/myrealm` (a development Keycloak realm; no env override) | `settings.py:194-206`, `config/default.yaml:18` |
| Google | any Google account; `SOCIALACCOUNT_AUTO_SIGNUP = True`; no domain restriction | `settings.py:189`, `:208-214` |
| Local username/password | **open signup.** No `ACCOUNT_ADAPTER` override, so `is_open_for_signup()` is true; `ACCOUNT_EMAIL_REQUIRED = False`, email verification `optional`, authentication method `username`. The login and signup templates show only SSO buttons, but `/accounts/signup/` still accepts a POST and logs the new user in | `settings.py:187-189`; `templates/account/signup.html` |
| Authorisation | none beyond "is authenticated"; every user may use the insert forms and the bug-report page | `runs/views.py` decorators |
| Sessions | database-backed (`django.contrib.sessions.backends.db`, Django default) | `settings.py` sets no `SESSION_ENGINE` |
| Transport | plain HTTP; no `SECURE_*`, `SESSION_COOKIE_SECURE` or `CSRF_COOKIE_SECURE`; `manage.py check --deploy` reports W004, W008, W009, W012, W016 | run 2026-10-06 in a scratch copy |

Verified end-to-end on 2026-10-06 against a `git archive HEAD` copy in a
scratch directory, production overlay with `RUNLOGDB_DB_BACKEND=sqlite`,
Django test client with CSRF enforcement on and a self-chosen CSRF cookie:

```
anon /runs/ -> 302 /accounts/login/?next=/runs/
signup with self-chosen CSRF cookie -> 302 /runs/
/runs/ after signup -> 200
entry_run POST -> 302 /runs/999999/subruns/      # row inserted into `run`
admin -> 302                                    # not staff
```

`ALLOWED_HOSTS` (`localhost`, `127.0.0.1`) is not a barrier: the `Host`
header is chosen by the client. A request with `Host: mu2e-daq-01.fnal.gov`
gets 400; the same request with `Host: localhost` is served.

**Verdict:** the run log is open to anyone who reaches :8000, in both modes.
Finding RL-001 (production) and RL-002 (development).

## 3. Database

### 3.1 Connection

| Backend | Settings | Source |
|---|---|---|
| SQLite | `BASE_DIR / database.sqlite.path` (default `db.sqlite3`) | `settings.py:105-111` |
| PostgreSQL | `database.postgres.{host,port,name,user,password}`, defaults `localhost:5432/runlogdb`, user `runlog`, empty password | `settings.py:94-104`, `config/default.yaml:5-10` |

No `OPTIONS`, so no `search_path` or SSL mode is set.

### 3.2 Tables read and written

| Table | Model | PK assumed by Django | PK/columns in the production dump | Read | Written by this app |
|---|---|---|---|---|---|
| `run` | `Run` | `run_number` | `run_number` bigint, default `nextval('production.run_configuration_run_number_seq')` | yes | `entry_run`, `seed_db`, `purge_db` |
| `run_end_info` | `RunEndInfo` | `run_number` | `run_number` integer | yes | `entry_run_end`, `seed_db`, `purge_db` |
| `subrun` | `Subrun` | **`id`** (implicit) | no `id` column; `(run, subrun)` | yes | `entry_subrun`, `seed_db`, `purge_db` |
| `run_type` | `RunType` | `id` | `id` | yes | `seed_db`, `purge_db` |
| `run_transition` | `RunTransition` | **`id`** (implicit) | no `id` column | no | `seed_db`, `purge_db` |
| `run_transition_type`, `run_transition_cause` | … | `id` | `id` | no | `seed_db`, `purge_db` |
| `config` | `Config` | **`id`** (implicit) | no `id` column; `(run_number, subsystem)` | no | `seed_db`, `purge_db` |
| `artdaq_fcl` | `ArtdaqFcl` | **`id`** (implicit) | no `id` column; `(run_number, name)` | no | `purge_db` |
| `view_run_summary` and four other views | — | — | — | no | no |

The SQL Django generates for a subrun query selects the missing column:

```
SELECT "subrun"."id", "subrun"."run", "subrun"."subrun", "subrun"."n_events", ...
```

On the production tables this fails with `column subrun.id does not exist`,
so `run_detail`, `subrun_ewt` and `entry_subrun` cannot work there (RL-004).
This was established from the generated SQL and the column dump; it was not
run against the live database.

Inserts also pass explicit `NULL` for `subrun.created_at` and
`run_end_info.create_time`, bypassing the database defaults `now()` and
`CURRENT_TIMESTAMP` (`runs/models.py:69`, `:119`).

### 3.3 Who else writes these tables

`DBRunInfo` in otsdaq-mu2e (`RunInfoPlugins/DBRunInfo_runInfo.cc`) writes
`run` (`:902-910`, number from the sequence via `RETURNING run_number`),
`run_transition` (`:1077`), `run_end_info` (`:1115`) and `config` (`:491`),
each prefixed with `OTSDAQ_RUNINFO_DATABASE_SCHEMA` (default `test`), in
database `OTSDAQ_RUNINFO_DATABASE` (default `run_info`) (`:20-37`). A run
number inserted by hand above the sequence's current value will later be
returned by `nextval`, and the DAQ's INSERT then fails with a duplicate key
(RL-003).

### 3.4 Django's own tables

`migrate` runs on every start (`start-mu2e-rundb-viewer:51`). On PostgreSQL
`ProductionRouter` skips only the `runs` app, so `auth_*`, `django_session`,
`django_site`, `django_admin_log`, `account_*` and `socialaccount_*` are
created **in the run-log database**. The database role therefore needs
`CREATE` there, as well as `INSERT`/`DELETE` on the run-log tables for the
entry forms (RL-007).

## 4. Outbound HTTPS — GitHub issues

`_create_github_issue` (`runs/views.py:187-212`) POSTs
`{"title","body","labels"}` to `https://api.github.com/repos/<github.repo>/issues`
with `Authorization: token <github.token>`. Title is
`[<SEVERITY>] <title>`, labels `bug` and the severity, body includes
`Reported by: <username>`. `.env.example:26` asks for a token with `repo`
scope. `urlopen` has no timeout. A non-JSON error body raises inside the
`HTTPError` handler and becomes a 500 (RL-009).

## 5. Discovery (UDP 28999)

`RunsConfig.ready()` (`runs/apps.py:14-32`) runs only when `runserver` is
in `argv` or `argv[0]` starts with `gunicorn`. It constructs

```python
Responder(name="Run Log Database", app="runlog-db", port=int(RUNLOGDB_PORT or 8000), scheme="http")
```

and starts it, logging a warning if `mu2edaq_discovery` is absent.
`requirements.txt:7-17` deliberately omits the package; install it from
`../mu2edaq-discovery`. Protocol and responder behaviour:
`mu2edaq-discovery/doc/INTERFACES.md`.

- **`meta` (CONTRACT §9.5):** none passed, so the string-only rule cannot be
  violated.
- **Advertised host:** `Responder` defaults `host` to `socket.getfqdn()`, so
  scans show `http://<fqdn>:8000` even though the default bind is
  `127.0.0.1` (RL-010).
- **One responder per gunicorn worker:** gunicorn imports the app in each of
  the 4 workers (no `--preload`), each `Responder` takes a fresh `uuid4`
  instance id (`mu2edaq-discovery/src/mu2edaq_discovery/responder.py:37`),
  and the socket uses `SO_REUSEPORT` (`:67-70`), so one server can answer a
  scan four times under four ids. Inferred from code, not observed.
- **Port source:** `RUNLOGDB_PORT` from the process environment. A value set
  only in `.env` reaches the responder (dotenv loads it into `os.environ`)
  but not the server, which the shell already bound.

## 6. Command-line

| Command | Man page |
|---|---|
| `start-mu2edaq-runlog-db.sh`, `stop-mu2edaq-runlog-db.sh` | `man/man1/start-mu2edaq-runlog-db.sh.1`, `…/stop-mu2edaq-runlog-db.sh.1` |
| `start-mu2e-rundb-viewer`, `stop-mu2e-rundb-viewer`, `bootstrap-mu2e-rundb-viewer` | `man/man1/<name>.1` |
| `manage.py seed_db`, `manage.py purge_db` | `man/man1/manage.py.1` |
| configuration | `man/man5/mu2edaq-runlog-db.yaml.5` |
| overview, routes | `man/man7/mu2edaq-runlog-db.7` |

## 7. Control-room integration

`mu2edaq-controlroom-setup/config/apps.yaml:97-105`: id `runlog-db`, start
`start-mu2edaq-runlog-db.sh`, stop `stop-mu2edaq-runlog-db.sh`,
`install_path: ~/mu2edaq-main/mu2edaq-runlog-db`, `ports: {http: 8000}`,
session `shift-aux`, `terminal: false`. The same entry, without `sessions`,
is in `mu2edaq-desktop/config/apps.yaml:98-105`.
