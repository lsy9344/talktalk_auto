"""Google Sheets API client with circuit breaker and retry logic

Reference: Story 5.1 - Google Sheets logging setup
Reference: docs/architecture.md#google-sheets-api
"""
import json
from typing import Any, Dict, List, Optional, cast

from google.oauth2 import service_account  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from talktalk_shared.config import (
    GOOGLE_SHEETS_INBOX_LOG_TAB,
    get_google_sheets_spreadsheet_id,
)
from talktalk_shared.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)
from talktalk_shared.utils.logger import get_logger
from talktalk_shared.utils.secrets import get_secret

logger = get_logger(__name__)


class GoogleSheetsError(Exception):
    """Base exception for Google Sheets API errors (E005)"""

    pass


class GoogleSheetsClient:
    """Google Sheets API client for logging

    Reference: Story 5.1 AC3, AC4 - Sheets append with retry
    Reference: docs/architecture.md#google-sheets-api
    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    MAX_RETRIES = 2
    TIMEOUT_SECONDS = 30

    def __init__(self) -> None:
        """Initialize Google Sheets API client with service account credentials"""
        self.circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                timeout_seconds=60,
                success_threshold=1,
            )
        )
        self._service: Optional[Any] = None

    def _get_service(self) -> Any:
        """
        Get or create Google Sheets API service

        Returns:
            Google Sheets API service instance

        Raises:
            GoogleSheetsError: If service initialization fails
        """
        if self._service is None:
            try:
                # Get service account credentials from Secrets Manager
                sa_json_str = get_secret("GOOGLE_SA_JSON")
                sa_dict = json.loads(sa_json_str)

                credentials = service_account.Credentials.from_service_account_info(
                    sa_dict, scopes=self.SCOPES
                )

                self._service = build("sheets", "v4", credentials=credentials)
                logger.info("Google Sheets API service initialized")

            except Exception as e:
                logger.error(
                    "Failed to initialize Google Sheets API service",
                    extra={"error": str(e), "error_type": type(e).__name__},
                )
                raise GoogleSheetsError(
                    f"Failed to initialize Google Sheets service: {str(e)}"
                ) from e

        return self._service

    def append_row(
        self,
        values: List[List[Any]],
        sheet_name: str = GOOGLE_SHEETS_INBOX_LOG_TAB,
        value_input_option: str = "USER_ENTERED",
    ) -> Dict[str, Any]:
        """
        Append rows to Google Sheets with retry logic

        Args:
            values: List of rows to append (each row is a list of values)
            sheet_name: Sheet tab name (default: inbox_log)
            value_input_option: How to interpret values (default: USER_ENTERED)

        Returns:
            Response dict from Sheets API containing:
            - spreadsheetId: str
            - tableRange: str
            - updates: dict with updatedCells, updatedRows, etc.

        Raises:
            GoogleSheetsError: If append fails after retries (E005)
            CircuitBreakerOpenError: If circuit breaker is open

        Reference: Story 5.1 AC4 - Append with 2 retries
        Reference: docs/architecture.md#google-sheets-api
        """
        if not self.circuit_breaker.allow_request():
            logger.error("Circuit breaker is open - request blocked")
            raise CircuitBreakerOpenError("Google Sheets API circuit breaker is open")

        spreadsheet_id = get_google_sheets_spreadsheet_id()
        range_name = f"{sheet_name}!A:Z"

        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                service = self._get_service()
                result = cast(
                    Dict[str, Any],
                    service.spreadsheets()
                    .values()
                    .append(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption=value_input_option,
                        body={"values": values},
                    )
                    .execute(),
                )

                self.circuit_breaker.record_success()
                logger.info(
                    "Successfully appended rows to Google Sheets",
                    extra={
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_name": sheet_name,
                        "row_count": len(values),
                        "updated_cells": result.get("updates", {}).get(
                            "updatedCells", 0
                        ),
                        "attempt": attempt + 1,
                    },
                )
                return result

            except HttpError as e:
                last_error = e
                logger.warning(
                    "Failed to append to Google Sheets (HttpError)",
                    extra={
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_name": sheet_name,
                        "attempt": attempt + 1,
                        "max_retries": self.MAX_RETRIES + 1,
                        "error": str(e),
                        "status_code": e.resp.status if hasattr(e, "resp") else None,
                    },
                )

                if attempt == self.MAX_RETRIES:
                    self.circuit_breaker.record_failure()
                    break

            except Exception as e:
                last_error = e
                logger.warning(
                    "Failed to append to Google Sheets (unexpected error)",
                    extra={
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_name": sheet_name,
                        "attempt": attempt + 1,
                        "max_retries": self.MAX_RETRIES + 1,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                if attempt == self.MAX_RETRIES:
                    self.circuit_breaker.record_failure()
                    break

        # All retries exhausted
        logger.error(
            "Failed to append to Google Sheets after all retries (E005)",
            extra={
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "max_retries": self.MAX_RETRIES + 1,
                "error": str(last_error),
            },
        )
        raise GoogleSheetsError(
            f"Failed to append to Google Sheets after "
            f"{self.MAX_RETRIES + 1} attempts: {str(last_error)}"
        ) from last_error

    def append_log_row(self, log_row: Any) -> Dict[str, Any]:
        """
        Append a single SheetsLogRow to inbox_log

        Args:
            log_row: SheetsLogRow instance

        Returns:
            Response dict from Sheets API

        Raises:
            GoogleSheetsError: If append fails after retries
            CircuitBreakerOpenError: If circuit breaker is open

        Reference: Story 5.2 Task 2 - Optional helper for SheetsLogRow
        """
        values = [log_row.to_sheets_values()]
        return self.append_row(values=values, sheet_name=GOOGLE_SHEETS_INBOX_LOG_TAB)
