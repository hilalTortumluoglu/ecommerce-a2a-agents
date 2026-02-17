"""Centralized configuration using pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── LLM ──────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key")
    llm_model: str = Field(default="gpt-4o-mini-2024-07-18", description="LLM model name")
    llm_temperature: float = Field(default=0.1)
    llm_max_tokens: int = Field(default=4096)

    # ── Tavily Web Search ─────────────────────────────────────────────────────
    tavily_api_key: str = Field(default="", description="Tavily API key for web search")

    # ── MCP Server ────────────────────────────────────────────────────────────
    mcp_server_host: str = Field(default="0.0.0.0")
    mcp_server_port: int = Field(default=8090)
    mcp_server_url: str = Field(default="http://mcp-server:8090")

    # ── Agent Ports ───────────────────────────────────────────────────────────
    product_agent_port: int = Field(default=8006)
    order_agent_port: int = Field(default=8005)
    search_agent_port: int = Field(default=8004)
    orchestrator_port: int = Field(default=8000)

    # ── Agent URLs (used by orchestrator to discover agents) ──────────────────
    product_agent_url: str = Field(default="http://product-agent:8006")
    order_agent_url: str = Field(default="http://order-agent:8005")
    search_agent_url: str = Field(default="http://search-agent:8004")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(default="sqlite+aiosqlite:///./data/ecommerce.db")

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: Optional[str] = Field(default=None)

    # ── App ───────────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")
    api_secret_key: str = Field(default="change-me-in-production-32-chars!!")

    # ── LangChain ─────────────────────────────────────────────────────────────
    langchain_tracing_v2: bool = Field(default=True)
    langchain_api_key: str = Field(default="")
    langchain_project: str = Field(default="ecommerce-a2a")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
