#!/usr/bin/env python3
"""Smoke test script for Google Sheets append functionality

This script verifies that the system can successfully append rows to Google Sheets.
It tests:
1. Configuration is properly set (GOOGLE_SHEETS_SPREADSHEET_ID)
2. Service Account has the correct permissions
3. The inbox_log sheet exists and is writable

Usage:
    python3 scripts/smoke_test_google_sheets_append.py

Prerequisites:
    - GOOGLE_SHEETS_SPREADSHEET_ID environment variable or .env file
    - GOOGLE_SA_JSON secret in AWS Secrets Manager
    - Service Account has Editor permissions on the spreadsheet
    - inbox_log sheet/tab exists in the spreadsheet

Reference: Story 5.1 AC4 - Simple verification method for Sheets connectivity
Reference: docs/architecture.md#google-sheets-api
"""
import os
import sys

# Add shared layer to Python path for local testing
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../src/layers/shared/python")
)

from dotenv import load_dotenv  # noqa: E402

from talktalk_shared.clients.google_sheets_client import (  # noqa: E402
    GoogleSheetsClient,
    GoogleSheetsError,
)
from talktalk_shared.config import (  # noqa: E402
    GOOGLE_SHEETS_INBOX_LOG_TAB,
    get_google_sheets_spreadsheet_id,
)
from talktalk_shared.models.sheets_log_row import SheetsLogRow  # noqa: E402


def test_google_sheets_append() -> None:
    """
    Test Google Sheets append functionality

    This function:
    1. Loads environment variables
    2. Validates configuration
    3. Creates GoogleSheetsClient
    4. Appends a test row to inbox_log
    5. Reports success or failure
    """
    print("=" * 80)
    print("Google Sheets Append - Smoke Test")
    print("=" * 80)
    print()

    # Step 1: Load environment variables
    print("Step 1: Loading environment variables...")
    load_dotenv()
    print("✅ Environment variables loaded")
    print()

    # Step 2: Validate configuration
    print("Step 2: Validating configuration...")
    try:
        spreadsheet_id = get_google_sheets_spreadsheet_id()
        print(f"✅ GOOGLE_SHEETS_SPREADSHEET_ID: {spreadsheet_id}")
    except ValueError as e:
        print(f"❌ Configuration error: {str(e)}")
        print()
        print("Please set GOOGLE_SHEETS_SPREADSHEET_ID in your .env file or environment")
        print("Example: GOOGLE_SHEETS_SPREADSHEET_ID=1ABC-xyz_spreadsheet_id")
        sys.exit(1)

    print(f"✅ Sheet tab name: {GOOGLE_SHEETS_INBOX_LOG_TAB}")
    print()

    # Step 3: Create GoogleSheetsClient
    print("Step 3: Initializing Google Sheets client...")
    try:
        client = GoogleSheetsClient()
        print("✅ GoogleSheetsClient initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {str(e)}")
        sys.exit(1)
    print()

    # Step 4: Append test row using SheetsLogRow schema
    print("Step 4: Creating test log row using SheetsLogRow schema...")
    row_id = SheetsLogRow.generate_row_id()
    created_at = SheetsLogRow.format_created_at_kst()

    # Create a test SheetsLogRow with all 23 columns
    log_row = SheetsLogRow(
        row_id=row_id,
        created_at_kst=created_at,
        channel_id="test_channel_smoke",
        channel_name="Smoke Test Channel",
        user_id="test_user_smoke",
        event="send",
        aggregation_id="-",
        message_count=1,
        question_raw="This is a smoke test from smoke_test_google_sheets_append.py",
        question_masked="This is a smoke test from smoke_test_google_sheets_append.py",
        kb_used="-",
        draft_answer="This is a test answer",
        confidence=0.95,
        risk_level="LOW",
        send_to_user=False,
        global_mode="TEST",
        channel_mode="TEST",
        action_taken="NOT_SENT",
        talktalk_send_result="-",
        telegram_alert_sent=False,
        telegram_reason="Smoke test",
        latency_ms_total=100,
        error_summary="-",
    )
    print(f"✅ SheetsLogRow created with row_id: {row_id}")
    print()

    print("Step 5: Appending test row to inbox_log...")
    try:
        result = client.append_log_row(log_row)
        print("✅ Successfully appended test row")
        print(f"   - Spreadsheet ID: {result.get('spreadsheetId')}")
        print(f"   - Table Range: {result.get('tableRange')}")
        updates = result.get('updates', {})
        print(f"   - Updated Cells: {updates.get('updatedCells', 0)}")
        print(f"   - Updated Rows: {updates.get('updatedRows', 0)}")
    except GoogleSheetsError as e:
        print(f"❌ Failed to append row (E005): {str(e)}")
        print()
        print("Troubleshooting:")
        print("1. Verify Service Account has Editor permissions on the spreadsheet")
        print("2. Verify inbox_log sheet/tab exists in the spreadsheet")
        print("3. Check AWS Secrets Manager contains valid GOOGLE_SA_JSON")
        print("4. Verify network connectivity to Google Sheets API")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)

    print()
    print("=" * 80)
    print("✅ Smoke test PASSED - Google Sheets append is working correctly")
    print("=" * 80)
    print()
    print("Next steps:")
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"1. Open the spreadsheet: {url}")
    print(f"2. Navigate to the '{GOOGLE_SHEETS_INBOX_LOG_TAB}' tab")
    print(f"3. Verify the test row with row_id: {row_id}")
    print("4. Verify all 23 columns are populated correctly")
    print()


def main() -> None:
    """Main entry point"""
    try:
        test_google_sheets_append()
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
