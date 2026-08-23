from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    model_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    model_timeout_seconds: float = 300.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_provider=os.getenv("MODEL_PROVIDER", "ollama"),
            ollama_base_url=os.getenv(
                "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
            ).rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            model_timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "300")),
        )
