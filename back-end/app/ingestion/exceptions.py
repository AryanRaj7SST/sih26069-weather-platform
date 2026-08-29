class IngestionError(Exception):
    """Base exception for all ingestion subsystem failures."""

    def __init__(self, message: str, source_code: str = "UNKNOWN") -> None:
        super().__init__(message)
        self.message = message
        self.source_code = source_code


class NormalizationError(IngestionError):
    """Raised when an incoming raw payload fails schema or geographic/temporal validation."""

    def __init__(self, message: str, source_code: str = "UNKNOWN", field: str = "unknown") -> None:
        super().__init__(f"Normalization failed for '{field}': {message}", source_code)
        self.field = field


class AdapterFetchError(IngestionError):
    """Raised when an ingestion adapter fails to fetch data from an external feed."""

    def __init__(self, message: str, source_code: str = "UNKNOWN") -> None:
        super().__init__(f"Adapter fetch error: {message}", source_code)
