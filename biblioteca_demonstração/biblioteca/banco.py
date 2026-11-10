"""Configuração explícita: desenvolvimento local ou PostgreSQL do SQL Connect."""

from django.core.exceptions import ImproperlyConfigured


def configurar_banco(env, base_dir):
    modo = env.get("BIBLIOTECA_BANCO", "sqlite")
    hospedado = env.get("VERCEL") == "1"
    if hospedado and modo != "firebase":
        raise ImproperlyConfigured("Na Vercel, configure BIBLIOTECA_BANCO=firebase. SQLite é apenas local.")
    if modo == "sqlite":
        return {
            "ENGINE": "django.db.backends.sqlite3", "NAME": base_dir / "db.sqlite3",
            "TEST": {"NAME": base_dir / ".test.sqlite3"},
            "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
        }
    if modo != "firebase":
        raise ImproperlyConfigured("BIBLIOTECA_BANCO deve ser sqlite ou firebase.")
    conexao = env.get("BIBLIOTECA_CONEXAO", "connector" if hospedado else "proxy")
    if conexao not in {"proxy", "connector"}:
        raise ImproperlyConfigured("BIBLIOTECA_CONEXAO deve ser proxy ou connector.")
    if hospedado and conexao != "connector":
        raise ImproperlyConfigured("Na Vercel, use BIBLIOTECA_CONEXAO=connector, sem o proxy do computador.")
    obrigatorias = ("PGDATABASE", "PGUSER", "PGPASSWORD") + (
        ("CLOUD_SQL_CONNECTION_NAME",) if conexao == "connector" else ("PGHOST",)
    )
    faltando = [nome for nome in obrigatorias if not env.get(nome)]
    if faltando:
        raise ImproperlyConfigured("Configure o PostgreSQL do SQL Connect: " + ", ".join(faltando))
    banco = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env["PGDATABASE"], "USER": env["PGUSER"],
        "PASSWORD": env["PGPASSWORD"], "HOST": env.get("PGHOST", ""),
        "PORT": env.get("PGPORT", "5432"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 10, "sslmode": env.get("PGSSLMODE", "require")},
    }
    if conexao == "connector":
        banco.update(ENGINE="biblioteca.backends.cloudsql", HOST="", PORT="")
        banco["OPTIONS"] = {"cloudsql_instance": env["CLOUD_SQL_CONNECTION_NAME"],
                            "connect_timeout": 10}
    return banco
