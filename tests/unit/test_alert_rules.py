"""Unit tests for alert_rules.py

Reference: docs/architecture/coding-standards.md#test-strategy-and-standards
Reference: docs/stories/2.3.story.md AC 6
"""
from src.functions.worker.alert_rules import evaluate_alert_triggers


class TestEvaluateAlertTriggers:
    """Test evaluate_alert_triggers function"""

    def test_test_mode_global_always_alerts(self):
        """TEST global mode should always trigger alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "Normal question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW", "confidence": 0.9}
        send_decision = {"action": "SEND_LOG_NO_ALERT", "reason": "ALL_GATES_PASSED"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="TEST",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "TEST_MODE" in result["reasons"]

    def test_test_mode_channel_always_alerts(self):
        """TEST channel mode should always trigger alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "Normal question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = {"action": "SEND_LOG_NO_ALERT", "reason": "ALL_GATES_PASSED"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="TEST",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "TEST_MODE" in result["reasons"]

    def test_prod_mode_no_triggers_no_alert(self):
        """PROD mode with no triggers should not alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "Normal question here"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = {"action": "SEND_LOG_NO_ALERT", "reason": "ALL_GATES_PASSED"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is False
        assert len(result["reasons"]) == 0

    def test_empty_rag_chunks_triggers_alert(self):
        """Empty RAG chunks should trigger alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "Question"}}
        retrieved_chunks = []
        llm_response = {"risk_level": "LOW"}
        send_decision = None

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "RAG_INSUFFICIENT_EVIDENCE" in result["reasons"]

    def test_high_risk_level_triggers_alert(self):
        """HIGH risk level should trigger alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "Question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "HIGH"}
        send_decision = None

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "RISK_LEVEL_HIGH" in result["reasons"]

    def test_image_without_text_triggers_alert(self):
        """Image content without text should trigger alert"""
        # Arrange
        webhook_event = {
            "imageContent": {"imageUrl": "https://example.com/image.jpg"},
            "textContent": {"text": ""},
        }
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = None

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "IMAGE_OR_COMPOSITE_WITHOUT_TEXT" in result["reasons"]

    def test_composite_without_text_triggers_alert(self):
        """Composite content without text should trigger alert"""
        # Arrange
        webhook_event = {
            "compositeContent": {"composites": []},
            "textContent": None,
        }
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = None

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "IMAGE_OR_COMPOSITE_WITHOUT_TEXT" in result["reasons"]

    def test_short_question_length_triggers_alert(self):
        """Question with <= 3 characters should trigger alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "ㅇㅇ"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = None

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "QUESTION_TOO_SHORT" in result["reasons"]

    def test_short_question_pattern_triggers_alert(self):
        """Specific short patterns should trigger alert"""
        # Arrange - test each pattern
        patterns = ["?", "ㅇㅇ", "문의요", "ㅎㅇ", "안녕"]

        for pattern in patterns:
            webhook_event = {"textContent": {"text": pattern}}
            retrieved_chunks = [{"chunk": "data"}]
            llm_response = {"risk_level": "LOW"}
            send_decision = None

            # Act
            result = evaluate_alert_triggers(
                global_mode="PROD",
                channel_mode="PROD",
                webhook_event=webhook_event,
                retrieved_chunks=retrieved_chunks,
                llm_response=llm_response,
                send_decision=send_decision,
            )

            # Assert
            assert result["should_alert"] is True, f"Pattern '{pattern}' should trigger alert"
            assert "QUESTION_TOO_SHORT" in result["reasons"]

    def test_external_api_failure_triggers_alert(self):
        """External API failures (E004/E005/E006) should trigger alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "Question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = None

        # Test each error code
        for error_code in ["E004", "E005", "E006"]:
            # Act
            result = evaluate_alert_triggers(
                global_mode="PROD",
                channel_mode="PROD",
                webhook_event=webhook_event,
                retrieved_chunks=retrieved_chunks,
                llm_response=llm_response,
                send_decision=send_decision,
                error_code=error_code,
            )

            # Assert
            assert result["should_alert"] is True
            assert f"EXTERNAL_API_FAILURE_{error_code}" in result["reasons"]

    def test_llm_validation_failed_triggers_alert(self):
        """LLM parsing/validation failure should trigger alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "Question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = None  # Simulate JSON parse / schema validation failure
        send_decision = None

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "LLM_VALIDATION_FAILED" in result["reasons"]

    def test_send_decision_log_and_alert_triggers_alert(self):
        """Send decision with LOG_AND_ALERT should trigger alert"""
        # Arrange
        webhook_event = {"textContent": {"text": "Question"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "LOW"}
        send_decision = {"action": "LOG_AND_ALERT", "reason": "GLOBAL_MODE_TEST"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert
        assert result["should_alert"] is True
        assert "SEND_BLOCKED_GLOBAL_MODE_TEST" in result["reasons"]

    def test_multiple_triggers_all_included(self):
        """Multiple triggers should all be included in reasons"""
        # Arrange
        webhook_event = {"textContent": {"text": "?"}}  # Short question
        retrieved_chunks = []  # Empty RAG
        llm_response = {"risk_level": "HIGH"}  # High risk
        send_decision = {"action": "LOG_AND_ALERT", "reason": "HIGH_RISK"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
            error_code="E004",
        )

        # Assert
        assert result["should_alert"] is True
        assert "RAG_INSUFFICIENT_EVIDENCE" in result["reasons"]
        assert "RISK_LEVEL_HIGH" in result["reasons"]
        assert "QUESTION_TOO_SHORT" in result["reasons"]
        assert "SEND_BLOCKED_HIGH_RISK" in result["reasons"]
        assert "EXTERNAL_API_FAILURE_E004" in result["reasons"]
        assert len(result["reasons"]) == 5

    def test_high_risk_always_alerts_in_prod_mode(self):
        """Story 7.2 AC2 - HIGH risk always triggers alert even in PROD mode"""
        # Arrange
        webhook_event = {"textContent": {"text": "Valid question here"}}
        retrieved_chunks = [{"chunk": "data"}]
        llm_response = {"risk_level": "HIGH", "confidence": 0.95}  # High confidence but HIGH risk
        send_decision = {"action": "LOG_AND_ALERT", "reason": "HIGH_RISK"}

        # Act
        result = evaluate_alert_triggers(
            global_mode="PROD",
            channel_mode="PROD",
            webhook_event=webhook_event,
            retrieved_chunks=retrieved_chunks,
            llm_response=llm_response,
            send_decision=send_decision,
        )

        # Assert - Must alert because of HIGH risk
        assert result["should_alert"] is True
        assert "RISK_LEVEL_HIGH" in result["reasons"]
        assert "SEND_BLOCKED_HIGH_RISK" in result["reasons"]
