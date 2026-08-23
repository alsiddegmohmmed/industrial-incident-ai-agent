from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from incident_agent.config import Settings
from incident_agent.errors import DeviceNotFoundError, ModelProviderError
from incident_agent.models import (
    HealthResponse,
    InvestigationRequest,
    InvestigationResponse,
)
from incident_agent.providers.base import ModelProvider
from incident_agent.providers.ollama import OllamaModelProvider
from incident_agent.repository import FixtureRepository
from incident_agent.service import InvestigationService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_provider(settings: Settings) -> ModelProvider:
    if settings.model_provider != "ollama":
        raise ValueError(f"Unsupported model provider: {settings.model_provider}")
    return OllamaModelProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.model_timeout_seconds,
    )


def create_app(provider: ModelProvider | None = None) -> FastAPI:
    settings = Settings.from_env()
    service = InvestigationService(
        repository=FixtureRepository(PROJECT_ROOT / "data" / "incidents"),
        provider=provider or build_provider(settings),
    )
    app = FastAPI(title="Industrial Incident AI Agent", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post(
        "/v1/investigations",
        response_model=InvestigationResponse,
        status_code=status.HTTP_200_OK,
    )
    async def investigate(request: InvestigationRequest) -> InvestigationResponse:
        try:
            return await service.investigate(request)
        except DeviceNotFoundError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ModelProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

    return app


app = create_app()
