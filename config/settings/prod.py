"""Environnement de production."""

from .base import *

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Le préchargement HSTS engage le domaine de façon quasi irréversible : à décider
# explicitement, après le choix du domaine définitif, et non par défaut.
SILENCED_SYSTEM_CHECKS = ["security.W021"]
