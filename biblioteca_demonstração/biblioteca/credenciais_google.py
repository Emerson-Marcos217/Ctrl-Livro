"""Identidade do servidor: segredo da hospedagem ou login local do Google."""

import json
import os

import google.auth
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def obter_credenciais_google():
    conteudo = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if conteudo:
        try:
            info = json.loads(conteudo)
            if not isinstance(info, dict) or info.get("type") != "service_account":
                raise ValueError
            return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        except (ValueError, TypeError, KeyError):
            raise GoogleAuthError("Revise GOOGLE_CREDENTIALS_JSON nas configurações do servidor.") from None
    if os.environ.get("VERCEL") == "1":
        raise GoogleAuthError("Configure GOOGLE_CREDENTIALS_JSON na hospedagem.")
    credenciais, _ = google.auth.default(scopes=SCOPES)
    return credenciais
