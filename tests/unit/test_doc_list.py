"""Unit tests for document list utilities"""
from talktalk_shared.utils.doc_list import build_final_doc_list


class TestBuildFinalDocList:
    """Tests for build_final_doc_list function (Story 3.1 AC3, AC4)"""

    def test_channel_docs_only_common_disabled(self):
        """Test with only channel docs when common_doc_enabled=False"""
        # Arrange
        channel_config = {
            "channel_id": "wc123",
            "doc_ids": ["doc1", "doc2", "doc3"],
            "common_doc_enabled": False,
        }
        common_doc_ids = ["common1", "common2"]

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == ["doc1", "doc2", "doc3"]

    def test_channel_docs_with_common_enabled(self):
        """Test with channel docs and common docs when common_doc_enabled=True"""
        # Arrange
        channel_config = {
            "channel_id": "wc123",
            "doc_ids": ["doc1", "doc2"],
            "common_doc_enabled": True,
        }
        common_doc_ids = ["common1", "common2"]

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == ["doc1", "doc2", "common1", "common2"]

    def test_duplicate_removal_keeps_first_occurrence(self):
        """Test that duplicate doc_ids are removed and first occurrence is kept"""
        # Arrange
        channel_config = {
            "channel_id": "wc123",
            "doc_ids": ["doc1", "doc2", "duplicate"],
            "common_doc_enabled": True,
        }
        common_doc_ids = ["duplicate", "common1"]  # duplicate exists in channel docs

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        # duplicate should appear only once at position 2 (from channel docs)
        assert result == ["doc1", "doc2", "duplicate", "common1"]

    def test_order_preserved_channel_first_then_common(self):
        """Test that order is preserved: channel docs first, then common docs"""
        # Arrange
        channel_config = {
            "channel_id": "wc123",
            "doc_ids": ["ch1", "ch2", "ch3"],
            "common_doc_enabled": True,
        }
        common_doc_ids = ["cm1", "cm2"]

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == ["ch1", "ch2", "ch3", "cm1", "cm2"]
        # Verify channel docs come before common docs
        assert result.index("ch1") < result.index("cm1")
        assert result.index("ch3") < result.index("cm1")

    def test_empty_channel_doc_ids_with_common_enabled(self):
        """Test with empty channel doc_ids but common docs enabled"""
        # Arrange
        channel_config = {"channel_id": "wc123", "doc_ids": [], "common_doc_enabled": True}
        common_doc_ids = ["common1", "common2"]

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == ["common1", "common2"]

    def test_empty_common_doc_ids(self):
        """Test with empty common doc IDs (safe handling per AC4)"""
        # Arrange
        channel_config = {
            "channel_id": "wc123",
            "doc_ids": ["doc1", "doc2"],
            "common_doc_enabled": True,
        }
        common_doc_ids = []

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == ["doc1", "doc2"]

    def test_missing_doc_ids_defaults_to_empty_list(self):
        """Test that missing doc_ids attribute defaults to empty list"""
        # Arrange
        channel_config = {"channel_id": "wc123", "common_doc_enabled": True}
        common_doc_ids = ["common1"]

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == ["common1"]

    def test_missing_common_doc_enabled_defaults_to_true(self):
        """Test that missing common_doc_enabled defaults to True"""
        # Arrange
        channel_config = {"channel_id": "wc123", "doc_ids": ["doc1"]}
        common_doc_ids = ["common1"]

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == ["doc1", "common1"]

    def test_invalid_doc_ids_type_defaults_to_empty_list(self):
        """Test that invalid doc_ids type (not a list) defaults to empty list"""
        # Arrange
        channel_config = {
            "channel_id": "wc123",
            "doc_ids": "not-a-list",  # Invalid type
            "common_doc_enabled": True,
        }
        common_doc_ids = ["common1"]

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == ["common1"]

    def test_both_empty_returns_empty_list(self):
        """Test that both empty channel and common docs returns empty list"""
        # Arrange
        channel_config = {"channel_id": "wc123", "doc_ids": [], "common_doc_enabled": True}
        common_doc_ids = []

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        assert result == []

    def test_multiple_duplicates_across_channel_and_common(self):
        """Test multiple duplicates are properly removed"""
        # Arrange
        channel_config = {
            "channel_id": "wc123",
            "doc_ids": ["doc1", "doc2", "dup1", "dup2"],
            "common_doc_enabled": True,
        }
        common_doc_ids = ["dup1", "common1", "dup2", "common2"]

        # Act
        result = build_final_doc_list(channel_config, common_doc_ids)

        # Assert
        # dup1 and dup2 should only appear once (from channel docs)
        assert result == ["doc1", "doc2", "dup1", "dup2", "common1", "common2"]
        assert result.count("dup1") == 1
        assert result.count("dup2") == 1
