class IncidentAgentError(Exception):
    """Base error for expected application failures."""


class DeviceNotFoundError(IncidentAgentError):
    """Raised when a request does not identify a known simulated device."""


class FixtureConfigurationError(IncidentAgentError):
    """Raised when trusted synthetic incident data is malformed or ambiguous."""


class ModelProviderError(IncidentAgentError):
    """Raised when a model provider fails or returns an invalid response."""


class ToolCallRejected(IncidentAgentError):
    """Raised when a model requests a tool with invalid or unauthorized arguments."""


class AgentLoopError(IncidentAgentError):
    """Raised when the bounded agent loop cannot complete safely."""
