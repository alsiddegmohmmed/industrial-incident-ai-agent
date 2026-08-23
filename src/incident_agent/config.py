from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    model_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    model_timeout_seconds: float = 300.0
    agent_timeout_seconds: float = 300.0
    agent_max_turns: int = 6
    agent_max_tool_calls: int = 12

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_provider=os.getenv("MODEL_PROVIDER", "ollama"),
            ollama_base_url=os.getenv(
                "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
            ).rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            model_timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "300")),
            agent_timeout_seconds=float(os.getenv("AGENT_TIMEOUT_SECONDS", "300")),
            agent_max_turns=int(os.getenv("AGENT_MAX_TURNS", "6")),
            agent_max_tool_calls=int(os.getenv("AGENT_MAX_TOOL_CALLS", "12")),
        )
