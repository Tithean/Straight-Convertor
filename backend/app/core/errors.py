class ConversionError(Exception):
    """A safe, actionable message that can be shown directly to the user."""

    def __init__(
        self, message: str, status_code: int = 422, code: str = "conversion_failed"
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
