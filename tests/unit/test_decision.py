"""Unit tests for decision logic"""
import sys
from pathlib import Path

# Add worker to path for imports
worker_path = Path(__file__).parent.parent.parent / "src" / "functions" / "worker"
sys.path.insert(0, str(worker_path))

from decision import make_send_decision  # noqa: E402


class TestMakeSendDecision:
    """Tests for make_send_decision function"""

    def test_global_mode_test_blocks_send(self):
        """Test: GlobalMode=TEST always blocks sending"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "TEST"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is False
        assert result["reason"] == "GLOBAL_MODE_TEST"
        assert result["action"] == "LOG_AND_ALERT"

    def test_channel_mode_test_blocks_send(self):
        """Test: Channel mode=TEST blocks sending even if GlobalMode=PROD"""
        # Arrange
        channel_config = {
            "channel_mode": "TEST",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is False
        assert result["reason"] == "CHANNEL_MODE_TEST"
        assert result["action"] == "LOG_AND_ALERT"

    def test_high_risk_blocks_send(self):
        """Test: HIGH risk_level blocks sending"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "HIGH",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is False
        assert result["reason"] == "HIGH_RISK"
        assert result["action"] == "LOG_AND_ALERT"

    def test_low_confidence_blocks_send(self):
        """Test: Low confidence blocks sending"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.42,
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is False
        assert result["reason"] == "LOW_CONFIDENCE_0.42"
        assert result["action"] == "LOG_AND_ALERT"

    def test_llm_declined_blocks_send(self):
        """Test: LLM send_to_user=false blocks sending"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": False,
            "confidence": 0.95,
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is False
        assert result["reason"] == "LLM_DECLINED"
        assert result["action"] == "LOG_AND_ALERT"

    def test_all_gates_passed_allows_send(self):
        """Test: All gates pass -> send allowed with no alert"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is True
        assert result["reason"] == "ALL_GATES_PASSED"
        assert result["action"] == "SEND_LOG_NO_ALERT"

    def test_confidence_at_exact_threshold_allows_send(self):
        """Test: Confidence exactly at threshold allows send"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.80,  # Exactly at threshold
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is True
        assert result["reason"] == "ALL_GATES_PASSED"
        assert result["action"] == "SEND_LOG_NO_ALERT"

    def test_medium_risk_allows_send(self):
        """Test: MEDIUM risk_level allows send (only HIGH blocks)"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "MEDIUM",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is True
        assert result["reason"] == "ALL_GATES_PASSED"
        assert result["action"] == "SEND_LOG_NO_ALERT"

    def test_needs_operator_blocks_send(self):
        """Test: needs_operator=true blocks send even if all other conditions pass"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "LOW",
            "needs_operator": True,  # Requires operator intervention
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is False
        assert result["reason"] == "NEEDS_OPERATOR"
        assert result["action"] == "LOG_AND_ALERT"

    def test_policy_flags_present_blocks_send(self):
        """Test: policy_flags with any value blocks send"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "LOW",
            "policy_flags": ["SOME_FLAG"],  # Any policy flag present
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is False
        assert result["reason"] == "POLICY_FLAGS_PRESENT"
        assert result["action"] == "LOG_AND_ALERT"

    def test_empty_policy_flags_allows_send(self):
        """Test: Empty policy_flags list allows send"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "LOW",
            "policy_flags": [],  # Empty list - no violations
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is True
        assert result["reason"] == "ALL_GATES_PASSED"
        assert result["action"] == "SEND_LOG_NO_ALERT"

    def test_missing_policy_flags_allows_send(self):
        """Test: Missing policy_flags key allows send"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.80,
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.95,
            "risk_level": "LOW",
            # No policy_flags key - field is optional
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert
        assert result["send_to_user"] is True
        assert result["reason"] == "ALL_GATES_PASSED"
        assert result["action"] == "SEND_LOG_NO_ALERT"

    def test_missing_threshold_defaults_to_085(self):
        """Test: Story 7.2 AC1 - Missing threshold defaults to 0.85 for safety"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            # No confidence_threshold key - should default to 0.85
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.83,  # Below 0.85 default
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert - Should block because 0.83 < 0.85
        assert result["send_to_user"] is False
        assert result["reason"] == "LOW_CONFIDENCE_0.83"
        assert result["action"] == "LOG_AND_ALERT"

    def test_missing_threshold_allows_send_above_085(self):
        """Test: Story 7.2 AC1 - Missing threshold allows send if confidence >= 0.85"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            # No confidence_threshold key - should default to 0.85
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.86,  # Above 0.85 default
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert - Should allow because 0.86 >= 0.85
        assert result["send_to_user"] is True
        assert result["reason"] == "ALL_GATES_PASSED"
        assert result["action"] == "SEND_LOG_NO_ALERT"

    def test_explicit_threshold_overrides_default(self):
        """Test: Story 7.2 AC1 - Explicit threshold value is respected (tuning allowed)"""
        # Arrange
        channel_config = {
            "channel_mode": "PROD",
            "confidence_threshold": 0.70,  # Explicit lower threshold for tuning
        }
        global_mode = "PROD"
        llm_response = {
            "send_to_user": True,
            "confidence": 0.75,  # Above explicit 0.70, but below default 0.85
            "risk_level": "LOW",
        }

        # Act
        result = make_send_decision(channel_config, global_mode, llm_response)

        # Assert - Should allow because 0.75 >= 0.70 (explicit threshold)
        assert result["send_to_user"] is True
        assert result["reason"] == "ALL_GATES_PASSED"
        assert result["action"] == "SEND_LOG_NO_ALERT"
