"""Environnement de développement local."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "dev-only-secret-key-not-for-production")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_PASSWORD", "travora_app")  # rôle d'exécution local (infra/postgres)

from .base import *

DEBUG = True
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
