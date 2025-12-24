"""Repository modules for data access"""
from talktalk_shared.repositories.aggregation import AggregationRepository
from talktalk_shared.repositories.channel_config import ChannelConfigRepository
from talktalk_shared.repositories.common_doc_ids import CommonDocIdsRepository
from talktalk_shared.repositories.deduplication import DeduplicationRepository
from talktalk_shared.repositories.vector_index_metadata import VectorIndexMetadataRepository

__all__ = [
    "ChannelConfigRepository",
    "DeduplicationRepository",
    "AggregationRepository",
    "CommonDocIdsRepository",
    "VectorIndexMetadataRepository",
]
