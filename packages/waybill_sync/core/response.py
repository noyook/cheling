"""Standardized API response format"""
from dataclasses import dataclass
from typing import Any


@dataclass
class ApiResponse:
    """Unified API response."""
    success: bool
    data: Any = None
    error: str = ""
    code: int = 0

    @classmethod
    def ok(cls, data: Any = None) -> "ApiResponse":
        """Create a success response."""
        return cls(success=True, data=data, code=0)

    @classmethod
    def fail(cls, error: str, code: int = 1) -> "ApiResponse":
        """Create a failure response."""
        return cls(success=False, error=error, code=code)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "code": self.code,
        }
