"""PostgreSQL do Django com transporte autenticado pelo Cloud SQL Connector."""

import atexit
from threading import Lock

import psycopg
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql.base import DatabaseWrapper as PostgreSQLWrapper
from google.cloud.sql.connector import Connector

from biblioteca.credenciais_google import obter_credenciais_google

_conector = None
_lock = Lock()


def obter_conector():
    # Só inicia na primeira conexão; collectstatic e imports não acessam o banco.
    global _conector
    with _lock:
        if _conector is None:
            _conector = Connector(credentials=obter_credenciais_google(), refresh_strategy="lazy")
            atexit.register(_conector.close)
        return _conector


class DriverCloudSQL:
    def __getattr__(self, nome):
        return getattr(psycopg, nome)

    def connect(self, **parametros):
        instancia = parametros.pop("cloudsql_instance")
        parametros["db"] = parametros.pop("dbname")
        timeout = parametros.pop("connect_timeout", 10)
        return obter_conector().connect(instancia, "psycopg", ip_type="PUBLIC",
                                       timeout=timeout, **parametros)


class DatabaseWrapper(PostgreSQLWrapper):
    # Mantém os cursores, adaptadores, transações e exceções do backend do Django.
    Database = DriverCloudSQL()

    def get_connection_params(self):
        if self.settings_dict["OPTIONS"].get("pool"):
            raise ImproperlyConfigured("O backend Cloud SQL usa conexões por requisição, sem pool do psycopg.")
        return super().get_connection_params()
