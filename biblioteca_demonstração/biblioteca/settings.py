import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key
from django.core.exceptions import ImproperlyConfigured
from .banco import configurar_banco

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if os.environ.get("DJANGO_DEBUG", "1") != "1":
        raise ImproperlyConfigured("Configure DJANGO_SECRET_KEY antes de desativar DEBUG.")
    secret_file = BASE_DIR / ".local-secret"
    try:
        SECRET_KEY = secret_file.read_text().strip()
    except FileNotFoundError:
        SECRET_KEY = get_random_secret_key()
        try:
            with secret_file.open("x") as file:
                file.write(SECRET_KEY)
        except FileExistsError:
            SECRET_KEY = secret_file.read_text().strip()

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth",
    "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
    "usuarios.apps.UsuariosConfig", "livro.apps.LivroConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "biblioteca.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "biblioteca.wsgi.application"
DATABASES = {"default": configurar_banco(os.environ, BASE_DIR)}
SQL_CONNECT_ATIVO = os.environ.get("SQL_CONNECT_ATIVO", "0") == "1"
SQL_CONNECT_PROJECT = os.environ.get("SQL_CONNECT_PROJECT", "")
SQL_CONNECT_LOCATION = os.environ.get("SQL_CONNECT_LOCATION", "")
SQL_CONNECT_SERVICE = os.environ.get("SQL_CONNECT_SERVICE", "")
SQL_CONNECT_CONNECTOR = os.environ.get("SQL_CONNECT_CONNECTOR", "biblioteca")
if SQL_CONNECT_ATIVO and DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("SQL Connect exige o mesmo PostgreSQL usado pelo Django. Configure BIBLIOTECA_BANCO=firebase.")
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_NAME = "biblioteca_perfis_session"
CSRF_COOKIE_NAME = "biblioteca_perfis_csrf"

# Provedor explícito; instalar uma chave não muda o destino das mensagens.
IA_HOSPEDADA = os.environ.get("VERCEL") == "1"
IA_PROVEDOR = os.environ.get("IA_PROVEDOR", "gemini" if IA_HOSPEDADA or not DEBUG else "ollama").strip().lower()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_TIMEOUT = 20  # Por chamada; um pedido pode fazer até duas chamadas.
IA_PEDIDOS_POR_HORA = 20
IA_INTERVALO_SEGUNDOS = 5
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
