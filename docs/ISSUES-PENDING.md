# Staged issues — mu2edaq-runlog-db

Findings from the September 2026 DAQ mega-review (`mu2e-sept-mega-review`),
2026-10-06.

**Why these are staged.** `Mu2e/mu2edaq-runlog-db` is **public** with issues
enabled. Under CONTRACT.md §9.1 no GitHub write is attempted from a package
agent. Each finding below is in the §6 body format, ready to file unchanged.

**Dedup.** `gh issue list -R Mu2e/mu2edaq-runlog-db --state all` returned two
closed issues: #1 (standardise start/stop script names) and #2 (add
mu2edaq-discovery support). Neither overlaps a finding below; RL-010 relates
to the code #2 added.

**Verification method.** Findings marked "verified" were checked on
2026-10-06 against a `git archive HEAD` export in a scratch directory, using
the package's own on-disk `.venv` (Django 4.2.30, django-allauth 0.61.1) as an
interpreter only, with the SQLite backend and Django's test client. No running
service and no PostgreSQL database were touched. Findings about the production
PostgreSQL tables rest on the committed column dump `db-schema.txt` and on
`otsdaq-mu2e/otsdaq-mu2e/RunInfoPlugins/DBRunInfo_runInfo.cc`; they were not
run against the live database.

**Fingerprints** are `sha1("Mu2e/mu2edaq-runlog-db:<path>:<rule_id>")[:8]`;
the inputs are tabulated at the end.

13 findings: 1 × S1, 5 × S2, 5 × S3, 2 × S4.

---

## RL-001

**Title:** `[auth] open allauth signup lets anyone who reaches :8000 create an account with read and write access to the run log`

**Severity:** S1 — data loss, security exposure, or wrong physics
**Category:** bug
**Location:** `runlogdb/settings.py:187`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
With `auth.enabled: true` (the production overlay) every run-log view is
`@login_required`, but django-allauth's local signup is left open: there is no
`ACCOUNT_ADAPTER` overriding `is_open_for_signup()`, `ACCOUNT_EMAIL_REQUIRED`
is `False`, and email verification is `optional`. The login and signup
templates show only the SSO buttons, but `/accounts/signup/` still accepts a
username/password POST, creates the user and logs them in. There is no
authorisation layer after that, so the new account can use the insert forms.
Any Google account is also admitted (`SOCIALACCOUNT_AUTO_SIGNUP = True`, no
domain check).

## Evidence
```
$ sed -n 187,189p runlogdb/settings.py
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_USERNAME_REQUIRED = False
SOCIALACCOUNT_AUTO_SIGNUP = True

# verified: scratch copy, DJANGO_ENV=production, RUNLOGDB_DB_BACKEND=sqlite,
# Django test client with enforce_csrf_checks=True and a self-chosen csrftoken cookie
signup open: True                                   # get_adapter().is_open_for_signup()
anon /runs/ -> 302 /accounts/login/?next=/runs/
signup with self-chosen CSRF cookie -> 302 /runs/
/runs/ after signup -> 200
entry_run POST -> 302 /runs/999999/subruns/          # row inserted into `run`
```
`ALLOWED_HOSTS` does not help: the client chooses the `Host` header, and
`Host: localhost` is accepted. The Docker image binds `0.0.0.0`
(`Dockerfile:24`).

## Why it matters
Anyone with network reach to a production instance can create an account and
insert `run`, `run_end_info` and `subrun` rows into the production run log.
Bogus subrun EWT ranges mislead the EWT lookup used to locate data, and a
bogus run number breaks a later DAQ run start (RL-003). Not torn with S2: the
path is verified end-to-end, needs no credentials, and the shipped Docker
configuration exposes it.

## Suggested fix
Add an `ACCOUNT_ADAPTER` whose `is_open_for_signup` returns `False`, and a
`SOCIALACCOUNT_ADAPTER` that admits only an allow-list (Fermilab domain or a
named group). Remove `allauth.urls` signup from `urlpatterns` if local
accounts are not wanted. Gate the entry forms behind a permission
(`@permission_required("runs.add_run")`) rather than `@login_required`.

## Related
- RL-002 (development mode has no authentication at all), RL-003, RL-009

<!-- mega-review-fingerprint: fc08916c -->

---

## RL-002

**Title:** `[config] the start script forces DJANGO_ENV=development ahead of .env, so control-room launches run with no auth, an auto-login superuser and an empty SQLite`

**Severity:** S2 — production breakage or silent wrong behaviour; workaround exists
**Category:** bug
**Location:** `start-mu2e-rundb-viewer:39`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
`start-mu2e-rundb-viewer` exports `DJANGO_ENV=development` when the variable
is unset. `settings.py` then calls `load_dotenv()`, whose default
`override=False` leaves the already-set variable alone, so a
`DJANGO_ENV=production` line in `.env` (as `Getting-Started.md` instructs) is
ignored. Nothing in mu2edaq-main sets `DJANGO_ENV`, so `crs-app start
runlog-db` → `start-mu2edaq-runlog-db.sh` always yields development mode:
`DevBypassMiddleware` logs every request in as superuser `dev` (including
`/admin/`), `DEBUG` is on, `ALLOWED_HOSTS` is `*`, and the database is a local
`db.sqlite3`, not the run log. `RUNLOGDB_HOST`/`RUNLOGDB_PORT` in `.env` are
likewise ignored by the shell that binds the server.

## Evidence
```
$ sed -n 39p start-mu2e-rundb-viewer
export DJANGO_ENV="${DJANGO_ENV:-development}"
$ sed -n 17p runlogdb/settings.py
load_dotenv(BASE_DIR / ".env")
$ grep -rn DJANGO_ENV .. --include='*.sh' --include='*.py' --include='*.yaml' | grep -v '^../mu2edaq-runlog-db/'
(no output)

# verified: scratch copy, .env = "DJANGO_ENV=production", shell DJANGO_ENV=development
AUTH_ENABLED False DEBUG True DB django.db.backends.sqlite3
```

## Why it matters
The control-room instance silently shows an empty or seeded SQLite database
instead of the run log, and any local user of the host (or the network, if
`RUNLOGDB_HOST=0.0.0.0`) gets superuser access. An operator who followed the
documented `.env` route believes the instance is in production mode.
Workaround: export `DJANGO_ENV=production` in the launching shell.

## Suggested fix
Do not default `DJANGO_ENV` in the shell; let `settings.py` read it after
`load_dotenv()`. Have the shell source `.env` (or call a small Python helper)
before resolving `RUNLOGDB_HOST`/`RUNLOGDB_PORT`. Refuse to start with
`auth.enabled: false` unless the bind is loopback. Set the intended mode in the
control-room `apps.yaml` entry.

## Related
- RL-001, RL-013 (docs that rely on `.env`)

<!-- mega-review-fingerprint: 980c743f -->

---

## RL-003

**Title:** `[db] manual run entry and seed_db insert explicit run numbers behind the DAQ's sequence, so a later DAQ run start can fail on a duplicate key`

**Severity:** S2 — production breakage or silent wrong behaviour; workaround exists
**Category:** bug
**Location:** `runs/views.py:99`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
On PostgreSQL the `run.run_number` column takes its value from a sequence, and
the DAQ's run-info plugin relies on it: `DBRunInfo` inserts without a run
number and reads it back with `RETURNING run_number`. The viewer's
`entry_run` form, and `seed_db` (runs 1001+ by default), insert rows with an
operator-chosen `run_number`, which does not advance the sequence.
`ProductionRouter` only blocks migrations; it does not stop writes, although
its docstring says the run-log tables "must not be touched by Django".

## Evidence
```
$ sed -n 99,105p runs/views.py
            Run.objects.create(
                run_number=d["run_number"],
                ...
$ grep -n '^|run  ' db-schema.txt | head -1
44:|run                          |run_number          |bigint                     |NO         |nextval('production.run_configuration_run_number_seq'::regclass)|

# otsdaq-mu2e/otsdaq-mu2e/RunInfoPlugins/DBRunInfo_runInfo.cc
902:  queryStream << "INSERT INTO " << dbSchema_ << ".run ("
903-910:  comment, run_type_id, create_time ... " RETURNING run_number;"

$ sed -n 10,16p runlogdb/db_router.py     # only allow_migrate; no db_for_write
```

## Why it matters
If someone enters run N greater than the sequence's current value, the DAQ
runs normally until `nextval` reaches N; that run start's INSERT then fails
with a duplicate-key error and the run cannot start. Combined with RL-001,
anyone can plant such a row. Workaround: delete the row or `setval` the
sequence past it.

## Suggested fix
Make the viewer read-only against the production backend: drop or disable
the entry views and `seed_db` when `database.backend == postgres`, and use a
PostgreSQL role with `SELECT` only. If manual run creation is genuinely
required, insert without `run_number` and let the sequence assign it.

## Related
- RL-001, RL-005, RL-007

<!-- mega-review-fingerprint: 8d389ab2 -->

---

## RL-004

**Title:** `[db] Subrun, RunTransition, Config and ArtdaqFcl models assume an id column the production tables do not have`

**Severity:** S2 — production breakage or silent wrong behaviour; workaround exists
**Category:** bug
**Location:** `runs/models.py:102`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
These four models declare no primary key, so Django adds an implicit
`id BigAutoField` and selects it in every query. The production column dump
shows none of the four tables has an `id` column (`subrun` is keyed by
`(run, subrun)`, `config` by `(run_number, subsystem)`, `artdaq_fcl` by
`(run_number, name)`, `run_transition` has no key). The `runs` migrations are
skipped on PostgreSQL, so nothing creates the column. The models also make
Django insert explicit `NULL` into `subrun.created_at` and
`run_end_info.create_time`, overriding their database defaults.

## Evidence
```
# Django-generated SQL (scratch copy):
SELECT "subrun"."id", "subrun"."run", "subrun"."subrun", "subrun"."n_events", ...
subrun pk column: id
run_transition pk column: id
config pk column: id
artdaq_fcl pk column: id

$ grep -c '^|subrun  *|id ' db-schema.txt
0
```

## Why it matters
Against the production database `run_detail`, `subrun_ewt` and
`entry_subrun` fail with `column subrun.id does not exist`. These are the
pages that justify the application. Development on SQLite hides it because
migration `0001_initial` creates the `id` column there. Not verified against
a live PostgreSQL instance.

## Suggested fix
Declare the real key: on Django 4.2 mark one column `primary_key=True` and
keep `unique_together`, or move to Django 5.2's `CompositePrimaryKey`. Set
`managed = False` on all run-log models so the SQLite migration cannot drift
from production. Add `db_default` (Django 5) or omit the timestamp fields on
insert.

## Related
- RL-007

<!-- mega-review-fingerprint: e1723201 -->

---

## RL-005

**Title:** `[ops] purge_db and seed_db run against the production PostgreSQL with no backend guard`

**Severity:** S2 — production breakage or silent wrong behaviour; workaround exists
**Category:** bug
**Location:** `runs/management/commands/purge_db.py:69`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
`purge_db` deletes every row of `artdaq_fcl`, `config`, `run_transition`,
`subrun`, `run_end_info`, `run`, `run_type`, `run_transition_type` and
`run_transition_cause` in one transaction. It asks for `yes`, and `--confirm`
skips that. Neither it nor `seed_db` checks which backend it is pointed at,
and `Instructions.md` lists both as "development utilities" with no warning.

## Evidence
```
$ sed -n 69,73p runs/management/commands/purge_db.py
        with transaction.atomic():
            for model in _MODELS_IN_ORDER:
                count, _ = model.objects.all().delete()
$ grep -n 'backend\|postgres\|DJANGO_ENV' runs/management/commands/*.py
(no output)
```

## Why it matters
With `DJANGO_ENV=production` exported (the documented way to reach the
production database), one command deletes the DAQ's entire run history:
every run, transition, configuration snapshot and FCL document written by
`DBRunInfo`. Torn between S1 and S2: it is a full delete of production data,
but it needs a deliberate operator command and a typed `yes`, and the
database role may lack `DELETE`. Picked S2.

## Suggested fix
Refuse to run when `settings.DATABASES["default"]["ENGINE"]` is PostgreSQL
unless an explicit `--i-mean-production` flag is given, and print the
target host and database name in the prompt. Run the production role
without `DELETE`.

## Related
- RL-003

<!-- mega-review-fingerprint: aa887f8b -->

---

## RL-006

**Title:** `[config] production inherits a committed SECRET_KEY, localhost-only ALLOWED_HOSTS with no override, no HTTPS settings and a development Keycloak realm`

**Severity:** S2 — production breakage or silent wrong behaviour; workaround exists
**Category:** bug
**Location:** `config/production.yaml:1`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
`config/production.yaml` overrides only backend, auth and debug. It inherits:
`secret_key: "change-me-before-deploying"` (used unless `RUNLOGDB_SECRET_KEY`
is set; nothing checks); `allowed_hosts: [localhost, 127.0.0.1]` with no
environment override; and the Fermilab OIDC endpoint
`https://kc.apps.okddev.fnal.gov/realms/myrealm`, a development Keycloak
realm labelled "Fermilab CILogon", also with no environment override. No
`SECURE_*`, `SESSION_COOKIE_SECURE` or `CSRF_COOKIE_SECURE` is set, while the
docs register `https://` callback URIs.

## Evidence
```
$ cat config/production.yaml
database:
  backend: postgres
auth:
  enabled: true
app:
  debug: false
$ sed -n 18p config/default.yaml; sed -n 29,32p config/default.yaml
      oidc_endpoint: "https://kc.apps.okddev.fnal.gov/realms/myrealm"
  secret_key: "change-me-before-deploying"
  allowed_hosts:
    - "localhost"
    - "127.0.0.1"

# verified, production overlay: manage.py check --deploy
security.W004, W008, W009 (SECRET_KEY), W012, W016
# Host: mu2e-daq-01.fnal.gov -> 400
```

## Why it matters
Deployed as shipped (Docker, `0.0.0.0`), the site returns 400 for every
real hostname and Fermilab sign-in goes to a development realm, so
production use requires editing committed YAML. The known secret key lets
anyone forge Django-signed values (allauth email-confirmation keys, the
messages cookie). Sessions are database-backed, so it does not by itself
mint a login; that and RL-001 already being open keep this at S2, by
analogy with the rubric's "insecure default shipped" anchor.

## Suggested fix
Fail start-up in production if the secret key is the placeholder. Add
`RUNLOGDB_ALLOWED_HOSTS` and `RUNLOGDB_FERMILAB_OIDC_ENDPOINT` overrides, put
the production values in `production.yaml`, and add the HTTPS settings when
served behind TLS.

## Related
- RL-001

<!-- mega-review-fingerprint: 77df07e5 -->

---

## RL-007

**Title:** `[db] the viewer keeps its auth and session tables in the production run-log database, migrates on every start, and has no schema setting`

**Severity:** S3 — correctness or maintainability risk, no current outage
**Category:** enhancement
**Location:** `runlogdb/db_router.py:10`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
There is one `DATABASES["default"]`. On PostgreSQL the router skips only the
`runs` app, so `migrate`, which the start script runs on every launch,
creates `auth_*`, `django_session`, `django_site`, `django_admin_log`,
`account_*` and `socialaccount_*` in the run-log database. The role
therefore needs `CREATE` there. The viewer also has no schema or
`search_path` setting, while `DBRunInfo` schema-qualifies every table with
`OTSDAQ_RUNINFO_DATABASE_SCHEMA` (default `test`; the dump shows
`production` and `test_sc`), and the default database names differ
(`runlogdb` here, `run_info` in `DBRunInfo`).

## Evidence
```
$ sed -n 51p start-mu2e-rundb-viewer
"$PYTHON" manage.py migrate 2>&1 | sed 's/^/          /'
$ sed -n 14,15p runlogdb/db_router.py
        if "postgresql" in engine and app_label == "runs":
            return False  # run-log tables pre-exist; never migrate them
# otsdaq-mu2e DBRunInfo_runInfo.cc:20-22 default dbname "run_info"; :35-37 default schema "test"
```

## Why it matters
The DAQ's system-of-record database must grant DDL and write rights to a web
application, and its contents now mix run data with web accounts and
sessions. Whether the viewer sees the DAQ's tables at all depends on an
unrecorded role `search_path`.

## Suggested fix
Use a second database alias (SQLite or a separate PostgreSQL database) for
Django's own tables and route `runs` reads to a read-only alias. Add a
`database.postgres.schema` key applied through `OPTIONS: {"options":
"-c search_path=<schema>"}`. Run `migrate` from the bootstrap step, not from
every start.

## Related
- RL-003, RL-004

<!-- mega-review-fingerprint: 39e61f43 -->

---

## RL-008

**Title:** `[ops] every start runs pip install --upgrade against PyPI under set -e`

**Severity:** S3 — correctness or maintainability risk, no current outage
**Category:** bug
**Location:** `bootstrap-mu2e-rundb-viewer:25`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
`start-mu2e-rundb-viewer:24` calls the bootstrap on every start, and the
bootstrap runs `pip install --upgrade pip` and `pip install -r
requirements.txt --upgrade`. Both scripts use `set -euo pipefail`.

## Evidence
```
$ sed -n 24,25p bootstrap-mu2e-rundb-viewer
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$REQUIREMENTS" --upgrade --quiet
$ sed -n 24p start-mu2e-rundb-viewer
"$SCRIPT_DIR/bootstrap-mu2e-rundb-viewer"
```

## Why it matters
A control-room host without PyPI access cannot start the viewer at all, and
every restart can silently move Django, allauth or psycopg2 to a different
version within the ranges, so two restarts of the same checkout can behave
differently.

## Suggested fix
Run the bootstrap only when `.venv` is missing or `requirements.txt` is newer
than a stamp file; pin exact versions in a lock file.

## Related
- none

<!-- mega-review-fingerprint: 4f6f8d5a -->

---

## RL-009

**Title:** `[web] any logged-in user can file GitHub issues with the server's repo-scope token; no request timeout`

**Severity:** S3 — correctness or maintainability risk, no current outage
**Category:** bug
**Location:** `runs/views.py:187`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
`bug_report` lets every authenticated user, including self-registered ones
(RL-001) and the development-mode `dev` user, create issues in
`github.repo` using `RUNLOGDB_GITHUB_TOKEN`; `.env.example` asks for a token
with `repo` scope. `urlopen` has no timeout. In the `HTTPError` handler,
`json.loads(e.read())` raises on a non-JSON body, which turns the error into
an unhandled 500.

## Evidence
```
$ sed -n 25,26p .env.example
# GitHub personal access token for creating bug-report issues
# Needs "repo" scope (or "public_repo" for public repos)
$ sed -n 205,210p runs/views.py
        with urllib.request.urlopen(req) as resp:
        ...
    except urllib.error.HTTPError as e:
        detail = json.loads(e.read()).get("message", str(e))
```

## Why it matters
Anyone who can reach the site can spam the public repository under the
server's identity, and a `repo`-scope classic token stored on a web host
grants write access to every repository its owner can write. A hung GitHub
call ties up a worker for gunicorn's 30 s timeout.

## Suggested fix
Use a fine-grained token limited to Issues: write on this one repository,
restrict the view to staff, add `timeout=10`, and guard the JSON parse.

## Related
- RL-001

<!-- mega-review-fingerprint: eb17188c -->

---

## RL-010

**Title:** `[discovery] the responder advertises the host FQDN while the server binds 127.0.0.1, and gunicorn starts one responder per worker`

**Severity:** S3 — correctness or maintainability risk, no current outage
**Category:** bug
**Location:** `runs/apps.py:27`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
`RunsConfig.ready()` builds `Responder(name="Run Log Database",
app="runlog-db", port=RUNLOGDB_PORT, scheme="http")` with no `host`, so the
announcement carries `socket.getfqdn()`. The server's default bind is
`127.0.0.1`, so a scan advertises a URL that no other host can open. Under
gunicorn, `ready()` runs in each of the four workers (no `--preload`); each
`Responder` has its own `uuid4` instance id and binds 28999 with
`SO_REUSEPORT`, so one server can answer a scan four times under four ids.
`meta` is not passed, so the CONTRACT §9.5 string-only rule is satisfied.

## Evidence
```
$ sed -n 27,29p runs/apps.py
            self._discovery_responder = Responder(
                name="Run Log Database", app="runlog-db",
                port=port, scheme="http")
$ sed -n 42p start-mu2e-rundb-viewer
HOST="${RUNLOGDB_HOST:-127.0.0.1}"
# mu2edaq-discovery/src/mu2edaq_discovery/responder.py
37:        self.instance_id = str(uuid.uuid4())
67-70:     SO_REUSEADDR, SO_REUSEPORT
```
The per-worker duplication is inferred from code; it was not observed on a
live scan.

## Why it matters
The control-room discovery browser offers a link that does not work, and
lists the service several times in production.

## Suggested fix
Do not start the responder when bound to loopback (pass the bind address
through an environment variable), pass `host=` explicitly, and start a single
responder from gunicorn's `when_ready` hook instead of `AppConfig.ready()`.

## Related
- Mu2e/mu2edaq-runlog-db#2 (closed; added the responder)

<!-- mega-review-fingerprint: 4c1344f8 -->

---

## RL-011

**Title:** `[tests] no tests and no CI for an application that writes to the production run log`

**Severity:** S3 — correctness or maintainability risk, no current outage
**Category:** enhancement
**Location:** `.github/workflows`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
No `tests.py`, no `tests/` directory, no `.github/workflows`.

## Evidence
```
$ git ls-files | grep -i -E 'test|\.github'
(no output)
```

## Why it matters
RL-001 and RL-002 are each one Django test-client assertion away from being
caught; RL-004 needs a test against a schema built from `db-schema.txt`.

## Suggested fix
Add pytest-django tests for: anonymous access redirects, signup disabled,
settings in each overlay, entry views refused on PostgreSQL, and model SQL
against a PostgreSQL service container loaded with the production DDL. Run
them in a GitHub Actions workflow on Python 3.9.

## Related
- RL-001, RL-002, RL-004

<!-- mega-review-fingerprint: e4b69e3d -->

---

## RL-012

**Title:** `[ui] Tailwind is loaded from cdn.tailwindcss.com at runtime`

**Severity:** S4 — cosmetic, stale, hygiene
**Category:** enhancement
**Location:** `templates/base.html:7`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
Every page loads `<script src="https://cdn.tailwindcss.com"></script>`, the
Tailwind Play CDN, which compiles CSS in the browser.

## Evidence
```
$ sed -n 7p templates/base.html
  <script src="https://cdn.tailwindcss.com"></script>
```

## Why it matters
On a control-room browser without internet access the pages render
unstyled. A third-party script runs with the page's privileges. Tailwind
documents the Play CDN as not for production.

## Suggested fix
Build the CSS once with the Tailwind CLI and serve it as a static file.

## Related
- none

<!-- mega-review-fingerprint: 3da86965 -->

---

## RL-013

**Title:** `[docs] duplicate schema dump, and setup docs that rely on .env for DJANGO_ENV`

**Severity:** S4 — cosmetic, stale, hygiene
**Category:** documentation
**Location:** `columns_202605151137.txt:1`
**Found by:** mega-review (`mu2e-sept-mega-review`), 2026-10-06

## What
`columns_202605151137.txt` and `db-schema.txt` are byte-identical.
`Getting-Started.md` says "edit .env to set DJANGO_ENV", and `Instructions.md`
puts `DJANGO_ENV=production` in its `.env` example; neither works (RL-002).
Both guides call the Fermilab provider "CILogon" while configuring a
Keycloak development realm. `Instructions.md` lists `purge_db` under
"Development utilities" without saying it acts on whatever backend is
configured. There was no `README.md` (added on the review branch).

## Evidence
```
$ cmp columns_202605151137.txt db-schema.txt && echo IDENTICAL
IDENTICAL
$ grep -n 'edit .env to set DJANGO_ENV' Getting-Started.md
25:cp .env.example .env          # edit .env to set DJANGO_ENV and any overrides
```

## Why it matters
Operators following the guides get development mode while believing they
configured production.

## Suggested fix
Delete one dump; correct the two guides after fixing RL-002; add a warning to
`purge_db`/`seed_db`.

## Related
- RL-002, RL-005

<!-- mega-review-fingerprint: b0a37983 -->

---

## Fingerprint inputs

| ID | Input to `sha1(...)[:8]` | Fingerprint |
|---|---|---|
| RL-001 | `Mu2e/mu2edaq-runlog-db:runlogdb/settings.py:open-self-signup` | fc08916c |
| RL-002 | `Mu2e/mu2edaq-runlog-db:start-mu2e-rundb-viewer:django-env-forced-development` | 980c743f |
| RL-003 | `Mu2e/mu2edaq-runlog-db:runs/views.py:manual-run-number-sequence-collision` | 8d389ab2 |
| RL-004 | `Mu2e/mu2edaq-runlog-db:runs/models.py:implicit-id-pk-missing-column` | e1723201 |
| RL-005 | `Mu2e/mu2edaq-runlog-db:runs/management/commands/purge_db.py:no-production-guard` | aa887f8b |
| RL-006 | `Mu2e/mu2edaq-runlog-db:config/production.yaml:production-hardening` | 77df07e5 |
| RL-007 | `Mu2e/mu2edaq-runlog-db:runlogdb/db_router.py:django-tables-in-runlog-db` | 39e61f43 |
| RL-008 | `Mu2e/mu2edaq-runlog-db:bootstrap-mu2e-rundb-viewer:pip-upgrade-every-start` | 4f6f8d5a |
| RL-009 | `Mu2e/mu2edaq-runlog-db:runs/views.py:bug-report-token-abuse` | eb17188c |
| RL-010 | `Mu2e/mu2edaq-runlog-db:runs/apps.py:discovery-advertise-mismatch` | 4c1344f8 |
| RL-011 | `Mu2e/mu2edaq-runlog-db:.github/workflows:no-tests-no-ci` | e4b69e3d |
| RL-012 | `Mu2e/mu2edaq-runlog-db:templates/base.html:tailwind-cdn-runtime` | 3da86965 |
| RL-013 | `Mu2e/mu2edaq-runlog-db:columns_202605151137.txt:docs-duplicate-and-env-claims` | b0a37983 |
