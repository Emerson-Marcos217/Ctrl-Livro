"""Configuração explícita: desenvolvimento local ou PostgreSQL do SQL Connect."""

from django.core.exceptions import ImproperlyConfigured


def configurar_banco(env, base_dir):
    modo = env.get("BIBLIOTECA_BANCO", "sqlite")
    if modo == "sqlite":
        return {
            "ENGINE": "django.db.backends.sqlite3", "NAME": base_dir / "db.sqlite3",
            "TEST": {"NAME": base_dir / ".test.sqlite3"},
            "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
        }
    if modo != "firebase":
        raise ImproperlyConfigured("BIBLIOTECA_BANCO deve ser sqlite ou firebase.")
    obrigatorias = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")
    faltando = [nome for nome in obrigatorias if not env.get(nome)]
    if faltando:
        raise ImproperlyConfigured("Configure o PostgreSQL do SQL Connect: " + ", ".join(faltando))
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env["PGDATABASE"], "USER": env["PGUSER"],
        "PASSWORD": env["PGPASSWORD"], "HOST": env["PGHOST"],
        "PORT": env.get("PGPORT", "5432"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 10, "sslmode": env.get("PGSSLMODE", "require")},
    }
