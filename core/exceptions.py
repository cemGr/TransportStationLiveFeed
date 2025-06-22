from __future__ import annotations
from enum import Enum


class ErrorCode(str, Enum):
    OK = "OK"
    NO_CREDITS = "NO_CREDITS"
    NO_BIKE_STATION = "NO_BIKE_STATION"
    NO_DOCK_STATION = "NO_DOCK_STATION"
    ROUTING_FAILED = "ROUTING_FAILED"
    INTERNAL = "INTERNAL"


class RoutePlannerError(Exception):
    """Base class for all route-planner related errors."""

    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code: ErrorCode = code
        self.message: str = message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code.value}, msg={self.message})"


class NoCreditsLeftError(RoutePlannerError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.NO_CREDITS, "No ORS credits left")


class NoBikeStationError(RoutePlannerError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.NO_BIKE_STATION, "No nearby station with available bikes")


class NoDockStationError(RoutePlannerError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.NO_DOCK_STATION, "No nearby station with free docks")


class RoutingFailedError(RoutePlannerError):
    def __init__(self, msg: str):
        super().__init__(ErrorCode.ROUTING_FAILED, msg)
