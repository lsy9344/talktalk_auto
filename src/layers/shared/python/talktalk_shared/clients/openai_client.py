"""OpenAI API client with circuit breaker and retry logic"""
from typing import List, Optional

from openai import OpenAI, OpenAIError

from talktalk_shared.config import get_openai_api_key
from talktalk_shared.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """OpenAI API client for embeddings"""

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSION = 1536

    def __init__(self) -> None:
        """Initialize OpenAI client"""
        self.circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                timeout_seconds=60,
                success_threshold=1,
            )
        )
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        """
        Get or create OpenAI client

        Returns:
            OpenAI client instance
        """
        if self._client is None:
            api_key = get_openai_api_key()
            self._client = OpenAI(api_key=api_key, timeout=30.0, max_retries=2)
            logger.info("OpenAI client initialized")

        assert self._client is not None
        return self._client

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for text chunks

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each vector is a list of floats)

        Reference: Story 3.2 AC4 - Create OpenAI embeddings for document chunks
        """
        if not texts:
            logger.warning("Empty text list provided for embeddings")
            return []

        if not self.circuit_breaker.allow_request():
            logger.error("Circuit breaker is open - request blocked")
            raise CircuitBreakerOpenError("OpenAI API circuit breaker is open")

        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=texts,
            )
        except OpenAIError as e:
            self.circuit_breaker.record_failure()
            logger.error(
                "Failed to create embeddings",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            raise
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(
                "Unexpected error creating embeddings",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            raise

        self.circuit_breaker.record_success()
        embeddings = [item.embedding for item in response.data]
        logger.info(
            "Created embeddings",
            extra={
                "model": self.EMBEDDING_MODEL,
                "chunk_count": len(texts),
                "dimension": len(embeddings[0]) if embeddings else 0,
            },
        )
        return embeddings
