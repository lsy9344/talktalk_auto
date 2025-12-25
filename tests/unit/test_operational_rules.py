"""Unit tests for operational_rules module

Reference: docs/stories/5.3.story.md AC 4
Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
"""
from src.functions.worker.operational_rules import compute_action_taken


class TestComputeActionTaken:
    """Test compute_action_taken function"""

    def test_test_mode_global_always_not_sent(self):
        """TEST mode (global_mode=TEST) should always return NOT_SENT"""
        # Arrange
        global_mode = "TEST"
        channel_mode = "PROD"
        send_to_user = True
        send_success = True

        # Act
        result = compute_action_taken(global_mode, channel_mode, send_to_user, send_success)

        # Assert
        assert result == "NOT_SENT"

    def test_test_mode_channel_always_not_sent(self):
        """TEST mode (channel_mode=TEST) should always return NOT_SENT"""
        # Arrange
        global_mode = "PROD"
        channel_mode = "TEST"
        send_to_user = True
        send_success = True

        # Act
        result = compute_action_taken(global_mode, channel_mode, send_to_user, send_success)

        # Assert
        assert result == "NOT_SENT"

    def test_prod_mode_send_to_user_false_returns_not_sent(self):
        """PROD mode with send_to_user=False should return NOT_SENT"""
        # Arrange
        global_mode = "PROD"
        channel_mode = "PROD"
        send_to_user = False
        send_success = None

        # Act
        result = compute_action_taken(global_mode, channel_mode, send_to_user, send_success)

        # Assert
        assert result == "NOT_SENT"

    def test_prod_mode_send_success_true_returns_sent(self):
        """PROD mode with send_success=True should return SENT"""
        # Arrange
        global_mode = "PROD"
        channel_mode = "PROD"
        send_to_user = True
        send_success = True

        # Act
        result = compute_action_taken(global_mode, channel_mode, send_to_user, send_success)

        # Assert
        assert result == "SENT"

    def test_prod_mode_send_success_false_returns_failed(self):
        """PROD mode with send_success=False should return FAILED"""
        # Arrange
        global_mode = "PROD"
        channel_mode = "PROD"
        send_to_user = True
        send_success = False

        # Act
        result = compute_action_taken(global_mode, channel_mode, send_to_user, send_success)

        # Assert
        assert result == "FAILED"

    def test_prod_mode_send_success_none_returns_not_sent(self):
        """PROD mode with send_success=None (not attempted) should return NOT_SENT"""
        # Arrange
        global_mode = "PROD"
        channel_mode = "PROD"
        send_to_user = True
        send_success = None

        # Act
        result = compute_action_taken(global_mode, channel_mode, send_to_user, send_success)

        # Assert
        assert result == "NOT_SENT"

    def test_disabled_channel_mode_with_prod_global(self):
        """DISABLED channel_mode with PROD global_mode should work correctly"""
        # Arrange
        global_mode = "PROD"
        channel_mode = "DISABLED"
        send_to_user = False
        send_success = None

        # Act
        result = compute_action_taken(global_mode, channel_mode, send_to_user, send_success)

        # Assert
        assert result == "NOT_SENT"
