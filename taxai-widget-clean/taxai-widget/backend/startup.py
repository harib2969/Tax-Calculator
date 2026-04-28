"""
startup.py — auto-detects which LLM and storage providers are available.
Priority: Azure OpenAI → rule-based fallback | MongoDB → in-memory fallback
Just fill in .env values and this picks the right adapter automatically.
"""

import os
import logging

log = logging.getLogger(__name__)


def get_llm_adapter():
    """Returns best available LLM adapter based on environment variables."""

    if os.environ.get("AZURE_OPENAI_KEY") and os.environ.get("AZURE_OPENAI_ENDPOINT"):
        try:
            from providers.llm.azure_openai_adapter import AzureOpenAIAdapter
            adapter = AzureOpenAIAdapter()
            log.info("✓ LLM provider : Azure OpenAI (GPT-4.5)")
            return adapter
        except Exception as e:
            log.warning(f"⚠ Azure OpenAI init failed: {e} — falling back to rules")

    from providers.llm.rule_based_adapter import RuleBasedAdapter
    log.info("✓ LLM provider : Rule-based NLP (no API key found)")
    return RuleBasedAdapter()


def get_storage_adapter():
    """Returns best available storage adapter based on environment variables."""

    if os.environ.get("MONGODB_URI"):
        try:
            from providers.storage.mongodb_adapter import MongoDBAdapter
            adapter = MongoDBAdapter()
            log.info("✓ Storage      : MongoDB Atlas")
            return adapter
        except Exception as e:
            log.warning(f"⚠ MongoDB init failed: {e} — falling back to in-memory")

    from providers.storage.memory_adapter import InMemoryAdapter
    log.info("✓ Storage      : In-memory (no MONGODB_URI set)")
    return InMemoryAdapter()
