import json
import os

from google.oauth2 import service_account


_SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_google_credentials():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)

    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    if not path:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE is required")

    return service_account.Credentials.from_service_account_file(path, scopes=_SCOPES)
