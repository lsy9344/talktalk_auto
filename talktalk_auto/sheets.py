from __future__ import annotations

from googleapiclient.discovery import build

from .google_auth import get_google_credentials


_SHEETS_SERVICE = None


def _get_service():
    global _SHEETS_SERVICE
    if _SHEETS_SERVICE is None:
        creds = get_google_credentials()
        _SHEETS_SERVICE = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return _SHEETS_SERVICE


def append_row(sheet_id: str, sheet_tab: str, values: list[str | int | float]) -> None:
    if not sheet_id:
        raise ValueError("sheet_id is required")
    service = _get_service()
    range_name = f"{sheet_tab}!A1"
    body = {"values": [values]}
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
