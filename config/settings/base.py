"""Paramètres communs à tous les environnements."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parents[2]


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ImproperlyConfigured(f"Variable d'environnement manquante : {name}")
    return value


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.tenancy",
    "apps.accounts",
    "apps.audit",
    "apps.crm",
    "apps.ledger",
    "apps.cases",
    "apps.payments",
    "apps.quotes",
    "apps.concierge",
    "apps.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "apps.web.middleware.PermissionsPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tenancy.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.web.context.shell",
            ],
        },
    },
]

# Le rôle de connexion d'exécution ne possède aucune table et ne contourne pas la RLS.
# Les migrations s'exécutent avec le rôle propriétaire (voir docs/architecture.md).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "travora"),
        "USER": env("DB_USER", "travora_app"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "ATOMIC_REQUESTS": False,
    }
}

AUTH_USER_MODEL = "accounts.User"
# Ralentissement des devinettes : au-delà de LOGIN_MAX_FAILURES échecs en LOGIN_LOCK_MINUTES
# minutes pour un identifiant, la connexion est refusée sans même vérifier le mot de passe.
# Une limite par adresse se règle au niveau du reverse proxy (hébergement non décidé).
LOGIN_MAX_FAILURES = 5
LOGIN_LOCK_MINUTES = 15
SESSION_COOKIE_AGE = 60 * 60 * 8  # une journée de travail, renouvelée à chaque requête
SESSION_SAVE_EVERY_REQUEST = True
LOGIN_URL = "web:login"
LOGIN_REDIRECT_URL = "web:today"
LOGOUT_REDIRECT_URL = "web:login"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("en", "English")]
TIME_ZONE = "Africa/Douala"

# Fenêtre de rétroactivité des écritures comptables (jours). Décision métier à confirmer.
LEDGER_RETROACTIVITY_DAYS = 90
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}

OVERDUE_DAYS = int(env("TRAVORA_OVERDUE_DAYS", "14"))
UPCOMING_DEPARTURE_DAYS = int(env("TRAVORA_UPCOMING_DEPARTURE_DAYS", "7"))


# Politique de sécurité du contenu : rien n'est chargé hors de l'application elle-même, aucun
# script ni style en ligne. Toute future dépendance externe devra être ajoutée ici, à dessein.
SECURE_CSP = {
    "default-src": [CSP.NONE],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "form-action": [CSP.SELF],
    "base-uri": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
    "object-src": [CSP.NONE],
}
SECURE_REFERRER_POLICY = "same-origin"
