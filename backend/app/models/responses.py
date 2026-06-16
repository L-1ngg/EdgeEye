from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class ApiResponse(BaseModel, Generic[DataT]):
    model_config = ConfigDict(extra="forbid")

    success: bool = True
    data: DataT
    message: str = "ok"
    timestamp: datetime


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = False
    error: ErrorPayload
    timestamp: datetime
