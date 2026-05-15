"""
Settings loaded in this order (later values override earlier ones):
  1. .env file (via python-dotenv)
  2. config/default.yaml
  3. config/<DJANGO_ENV>.yaml  (DJANGO_ENV defaults to 'development')
  4. Individual RUNLOGDB_* environment variables
"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# ── 1. Load .env ──────────────────────────────────────────────────────────────
load_dotenv(BASE_DIR / ".env")


# ── 2+3. Load and merge YAML configs ─────────────────────────────────────────
def _deep_merge(base: dict, overlay: dict) -> dict:
    result = base.copy()
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


_env_name = os.environ.get("DJANGO_ENV", "development")
_cfg = _deep_merge(
    _load_yaml(BASE_DIR / "config" / "default.yaml"),
    _load_yaml(BASE_DIR / "config" / f"{_env_name}.yaml"),
)


# ── 4. Environment-variable overrides ────────────────────────────────────────
def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.lower() not in ("0", "false", "no", "off")


_cfg["app"]["secret_key"] = os.environ.get(
    "RUNLOGDB_SECRET_KEY", _cfg["app"]["secret_key"]
)
_cfg["app"]["debug"] = _env_bool("RUNLOGDB_DEBUG", _cfg["app"]["debug"])

_db = _cfg["database"]
_db["backend"] = os.environ.get("RUNLOGDB_DB_BACKEND", _db["backend"])
_db["postgres"]["host"] = os.environ.get("RUNLOGDB_DB_HOST", _db["postgres"]["host"])
_db["postgres"]["port"] = int(
    os.environ.get("RUNLOGDB_DB_PORT", _db["postgres"]["port"])
)
_db["postgres"]["name"] = os.environ.get("RUNLOGDB_DB_NAME", _db["postgres"]["name"])
_db["postgres"]["user"] = os.environ.get("RUNLOGDB_DB_USER", _db["postgres"]["user"])
_db["postgres"]["password"] = os.environ.get(
    "RUNLOGDB_DB_PASSWORD", _db["postgres"]["password"]
)

_auth = _cfg["auth"]
_auth["enabled"] = _env_bool("RUNLOGDB_AUTH_ENABLED", _auth["enabled"])
_auth["providers"]["fermilab_cilogon"]["client_id"] = os.environ.get(
    "RUNLOGDB_FERMILAB_CLIENT_ID",
    _auth["providers"]["fermilab_cilogon"]["client_id"],
)
_auth["providers"]["fermilab_cilogon"]["client_secret"] = os.environ.get(
    "RUNLOGDB_FERMILAB_CLIENT_SECRET",
    _auth["providers"]["fermilab_cilogon"]["client_secret"],
)
_auth["providers"]["google"]["client_id"] = os.environ.get(
    "RUNLOGDB_GOOGLE_CLIENT_ID", _auth["providers"]["google"]["client_id"]
)
_auth["providers"]["google"]["client_secret"] = os.environ.get(
    "RUNLOGDB_GOOGLE_CLIENT_SECRET", _auth["providers"]["google"]["client_secret"]
)


# ── Django core settings ──────────────────────────────────────────────────────
SECRET_KEY = _cfg["app"]["secret_key"]
DEBUG = _cfg["app"]["debug"]
ALLOWED_HOSTS = _cfg["app"].get("allowed_hosts", ["localhost"])

# ── Database ──────────────────────────────────────────────────────────────────
if _db["backend"] == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": _db["postgres"]["host"],
            "PORT": _db["postgres"]["port"],
            "NAME": _db["postgres"]["name"],
            "USER": _db["postgres"]["user"],
            "PASSWORD": _db["postgres"]["password"],
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / _db["sqlite"]["path"],
        }
    }

DATABASE_ROUTERS = ["runlogdb.db_router.ProductionRouter"]

# ── GitHub integration ────────────────────────────────────────────────────────
_gh = _cfg.get("github", {})
GITHUB_TOKEN = os.environ.get("RUNLOGDB_GITHUB_TOKEN", _gh.get("token", ""))
GITHUB_REPO = os.environ.get("RUNLOGDB_GITHUB_REPO", _gh.get("repo", "Mu2e/mu2edaq-runlog-db"))

# ── Auth settings exposed to other modules ───────────────────────────────────
AUTH_ENABLED = _auth["enabled"]

# ── Installed apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.openid_connect",
    "runs",
]

SITE_ID = 1

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

if not AUTH_ENABLED:
    MIDDLEWARE.append("runlogdb.middleware.DevBypassMiddleware")

# ── Templates ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "/static/"

# ── Auth / allauth ────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/runs/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_USERNAME_REQUIRED = False
SOCIALACCOUNT_AUTO_SIGNUP = True

_fermilab = _auth["providers"]["fermilab_cilogon"]
_google = _auth["providers"]["google"]

SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "SERVERS": [
            {
                "id": "fermilab",
                "name": "Fermilab CILogon",
                "server_url": _fermilab["oidc_endpoint"],
                "APP": {
                    "client_id": _fermilab["client_id"],
                    "secret": _fermilab["client_secret"],
                },
            }
        ]
    },
    "google": {
        "APP": {
            "client_id": _google["client_id"],
            "secret": _google["client_secret"],
        },
        "SCOPE": ["profile", "email"],
    },
}

ROOT_URLCONF = "runlogdb.urls"
WSGI_APPLICATION = "runlogdb.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Timezone / i18n ───────────────────────────────────────────────────────────
USE_TZ = True
TIME_ZONE = "UTC"
USE_I18N = True
LANGUAGE_CODE = "en-us"
