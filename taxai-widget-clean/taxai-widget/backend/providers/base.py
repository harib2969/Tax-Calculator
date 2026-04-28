"""providers/base.py — Abstract interfaces. All adapters must implement these."""

from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    @abstractmethod
    def extract(self, user_query: str) -> dict:
        """
        Extract tax-relevant fields from natural language.
        Must always return a dict with these keys:
          sale_amount, state, product_type, is_use_tax,
          business_type, has_physical_presence, notes
        Missing fields should be None.
        """

    @abstractmethod
    def summarize(self, result: dict) -> str:
        """Generate a plain-English 2–3 sentence summary of a tax result."""


class StorageAdapter(ABC):
    @abstractmethod
    def save_query(self, query: str, extracted: dict, result: dict) -> None:
        """Persist a query + result pair."""

    @abstractmethod
    def load_history(self, limit: int = 10) -> list[dict]:
        """Return the most recent N queries, newest first."""
