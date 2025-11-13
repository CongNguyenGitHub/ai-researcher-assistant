"""
Configuration module for Context-Aware Research Assistant
Loads and validates environment variables for all services
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid"""
    pass


@dataclass
class GeminiConfig:
    """Google Gemini API configuration"""
    api_key: str
    model: str = "gemini-2.0-flash"

    def __post_init__(self):
        if not self.api_key:
            raise ConfigError("GEMINI_API_KEY is required")


@dataclass
class MilvusConfig:
    """Milvus Vector Database configuration"""
    host: str = "localhost"
    port: int = 19530
    alias: str = "default"

    def __post_init__(self):
        if not self.host:
            raise ConfigError("MILVUS_HOST is required")


@dataclass
class FirecrawlConfig:
    """Firecrawl Web Search API configuration"""
    api_key: str

    def __post_init__(self):
        if not self.api_key:
            raise ConfigError("FIRECRAWL_API_KEY is required")


@dataclass
class ZepConfig:
    """Zep Memory Service configuration"""
    api_key: str
    api_url: str = "https://api.getzep.com"

    def __post_init__(self):
        if not self.api_key:
            raise ConfigError("ZEP_API_KEY is required")
        if not self.api_url:
            raise ConfigError("ZEP_API_URL is required")


@dataclass
class ArxivConfig:
    """Arxiv API configuration (no key needed - public API)"""
    timeout: int = 7


@dataclass
class ApplicationConfig:
    """Application-level configuration"""
    log_level: str = "INFO"
    quality_threshold: float = 0.5
    response_timeout: int = 30
    retrieval_timeout: int = 15
    evaluation_timeout: int = 5
    synthesis_timeout: int = 8
    memory_timeout: int = 2


@dataclass
class Config:
    """Main configuration class aggregating all service configs"""
    gemini: GeminiConfig
    milvus: MilvusConfig
    firecrawl: FirecrawlConfig
    zep: ZepConfig
    arxiv: ArxivConfig
    app: ApplicationConfig

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables (.env file)"""
        # Load .env file
        load_dotenv()

        # Validate and load required configurations
        try:
            gemini = GeminiConfig(
                api_key=os.getenv("GEMINI_API_KEY", ""),
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            )
        except ConfigError as e:
            raise ConfigError(f"Gemini configuration error: {e}")

        try:
            firecrawl = FirecrawlConfig(
                api_key=os.getenv("FIRECRAWL_API_KEY", "")
            )
        except ConfigError as e:
            raise ConfigError(f"Firecrawl configuration error: {e}")

        try:
            zep = ZepConfig(
                api_key=os.getenv("ZEP_API_KEY", ""),
                api_url=os.getenv("ZEP_API_URL", "https://api.getzep.com")
            )
        except ConfigError as e:
            raise ConfigError(f"Zep configuration error: {e}")

        milvus = MilvusConfig(
            host=os.getenv("MILVUS_HOST", "localhost"),
            port=int(os.getenv("MILVUS_PORT", "19530")),
            alias=os.getenv("MILVUS_ALIAS", "default")
        )

        arxiv = ArxivConfig(
            timeout=int(os.getenv("ARXIV_TIMEOUT", "7"))
        )

        app = ApplicationConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            quality_threshold=float(os.getenv("QUALITY_THRESHOLD", "0.5")),
            response_timeout=int(os.getenv("RESPONSE_TIMEOUT", "30")),
            retrieval_timeout=int(os.getenv("RETRIEVAL_TIMEOUT", "15")),
            evaluation_timeout=int(os.getenv("EVALUATION_TIMEOUT", "5")),
            synthesis_timeout=int(os.getenv("SYNTHESIS_TIMEOUT", "8")),
            memory_timeout=int(os.getenv("MEMORY_TIMEOUT", "2"))
        )

        return cls(
            gemini=gemini,
            milvus=milvus,
            firecrawl=firecrawl,
            zep=zep,
            arxiv=arxiv,
            app=app
        )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def init_config():
    """Initialize configuration from environment"""
    global _config
    _config = Config.from_env()


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = Config.from_env()
        print("✅ Configuration loaded successfully")
        print(f"  - Gemini Model: {config.gemini.model}")
        print(f"  - Milvus: {config.milvus.host}:{config.milvus.port}")
        print(f"  - Firecrawl API Key: {config.firecrawl.api_key[:10]}...")
        print(f"  - Zep URL: {config.zep.api_url}")
        print(f"  - Quality Threshold: {config.app.quality_threshold}")
    except ConfigError as e:
        print(f"❌ Configuration error: {e}")
        exit(1)
